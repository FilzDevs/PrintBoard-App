"""Moonraker & Bambu Lab unified client (standard library only). Works with any Klipper or Bambu Lab printer."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path, PurePosixPath
import re
import socket
import subprocess
import time
from urllib.parse import quote
from urllib.request import Request, urlopen
import uuid

from .sim import SIM, DEMO_THUMB_BYTES

TIMEOUT = 4
_THUMB_CACHE = {}


def _headers(p, ctype=None):
    h = {"Accept": "application/json", "User-Agent": "PrintBoard/1.0"}
    if ctype:
        h["Content-Type"] = ctype
    if getattr(p, "token", ""):
        h["X-Api-Key"] = p.token
        h["Authorization"] = "Bearer " + p.token
    return h


def _get(p, path, timeout=TIMEOUT):
    with urlopen(Request(p.base + path, headers=_headers(p)), timeout=timeout) as r:
        j = json.loads(r.read(4 * 1024 * 1024))
    if isinstance(j, dict) and "error" in j:
        raise RuntimeError(str(j["error"]))
    return j.get("result", j) if isinstance(j, dict) else j


def _get_bytes(p, path, timeout=TIMEOUT):
    with urlopen(Request(p.base + path, headers=_headers(p)), timeout=timeout) as r:
        return r.read(10 * 1024 * 1024)


def _heaters(objs):
    out = []
    for o in objs:
        if o == "heater_bed" or o.startswith("extruder") or o.startswith("heater_generic "):
            out.append(o)
    return out


def fetch(p):
    """Return a normalised status dict. Queries only objects the printer really has."""
    if SIM.is_sim_printer(getattr(p, "id", "")):
        return SIM.fetch_status(p)

    if getattr(p, "printer_type", "moonraker") == "bambu":
        from . import bambu
        return bambu.fetch_bambu_status(p)

    objs = _get(p, "/printer/objects/list")["objects"]
    heaters = _heaters(objs)
    sensors = [o for o in objs if o.startswith("temperature_sensor ")]
    want = [
        o for o in (
            "print_stats", "display_status", "virtual_sdcard", "toolhead",
            "gcode_move", "fan", "print_task_config", "exclude_object", "bed_mesh"
        ) if o in objs
    ]
    q = "&".join(quote(o, safe="") for o in want + heaters + sensors)
    st = _get(p, "/printer/objects/query?" + q)["status"]
    ps, ds, vs = st.get("print_stats", {}), st.get("display_status", {}), st.get("virtual_sdcard", {})
    th, gm, fn = st.get("toolhead", {}), st.get("gcode_move", {}), st.get("fan", {})
    ptc = st.get("print_task_config", {})
    slot_spool_ids = [int(x) if x and int(x) > 0 else None for x in (ptc.get("filament_spool_id") or [])]
    active_ext = th.get("extruder") or "extruder"
    ext_idx = int(active_ext[8:]) if active_ext.startswith("extruder") and active_ext[8:].isdigit() else 0
    active_spool_id = slot_spool_ids[ext_idx] if ext_idx < len(slot_spool_ids) else None
    prog = ds.get("progress", vs.get("progress", 0)) or 0
    dur = ps.get("print_duration") or 0
    state = ps.get("state", "standby")
    temps = []
    for o in heaters + sensors:
        d = st.get(o, {})
        label = {"heater_bed": "Bett"}.get(o, o.replace("heater_generic ", "").replace("temperature_sensor ", ""))
        if o == "extruder":
            label = "Düse"
        temps.append((label, d.get("temperature"), d.get("target")))
    try:
        klipper = _get(p, "/printer/info").get("state", "ready")
    except Exception:
        klipper = "?"
    pos = th.get("position") or gm.get("gcode_position") or [0.0, 0.0, 0.0, 0.0]
    homing_origin = gm.get("homing_origin") or [0.0, 0.0, 0.0, 0.0]
    remaining = dur * (1 - prog) / prog if state == "printing" and prog > 0.01 else None
    eta_str = ""
    if remaining and remaining > 0:
        eta_str = time.strftime("%H:%M Uhr", time.localtime(time.time() + remaining))

    p_info = ps.get("info") or {}
    layer = int(p_info.get("current_layer") or 0)
    total_layers = int(p_info.get("total_layer") or 0)

    # Parse bed_mesh if present
    bm_raw = st.get("bed_mesh") or {}
    bed_mesh = None
    matrix = bm_raw.get("probed_matrix") or bm_raw.get("mesh_matrix")
    if isinstance(matrix, list) and matrix and isinstance(matrix[0], list):
        flat = [float(v) for row in matrix for v in row if isinstance(v, (int, float))]
        if flat:
            bed_mesh = {
                "profile_name": bm_raw.get("profile_name") or "default",
                "mesh_min": bm_raw.get("mesh_min") or [10, 10],
                "mesh_max": bm_raw.get("mesh_max") or [220, 220],
                "probed_matrix": matrix,
                "mesh_matrix": bm_raw.get("mesh_matrix") or matrix,
                "min_val": round(min(flat), 4),
                "max_val": round(max(flat), 4),
                "variance": round(max(flat) - min(flat), 4),
                "profiles": list((bm_raw.get("profiles") or {}).keys()) if isinstance(bm_raw.get("profiles"), dict) else [],
            }

    # Parse exclude_object if present
    eo_raw = st.get("exclude_object") or {}
    exclude_object = None
    if eo_raw and isinstance(eo_raw.get("objects"), list) and eo_raw.get("objects"):
        exclude_object = {
            "objects": eo_raw.get("objects", []),
            "excluded_objects": eo_raw.get("excluded_objects", []),
            "current_object": eo_raw.get("current_object"),
        }

    return {
        "state": state,
        "klipper": klipper,
        "filename": ps.get("filename") or "",
        "progress": max(0.0, min(1.0, prog)),
        "duration": dur,
        "remaining": remaining,
        "eta": eta_str,
        "temps": temps,
        "heaters": heaters,
        "homed": th.get("homed_axes", ""),
        "position": pos[:3] if len(pos) >= 3 else [0.0, 0.0, 0.0],
        "z_offset": float(homing_origin[2]) if len(homing_origin) >= 3 else 0.0,
        "fan_speed": float(fn.get("speed") or 0.0),
        "speed_factor": float(gm.get("speed_factor") or 1.0),
        "extrude_factor": float(gm.get("extrude_factor") or 1.0),
        "layer": layer,
        "total_layers": total_layers,
        "active_spool_id": active_spool_id,
        "slot_spool_ids": slot_spool_ids,
        "active_extruder": active_ext,
        "bed_mesh": bed_mesh,
        "exclude_object": exclude_object,
    }


def job_thumbnail(p, filename):
    """Fetch and cache the best thumbnail PNG bytes for a G-code file on Moonraker."""
    if not filename:
        return None
    if SIM.is_sim_printer(getattr(p, "id", "")):
        return DEMO_THUMB_BYTES
    key = (getattr(p, "id", p.base), filename)
    if key in _THUMB_CACHE:
        return _THUMB_CACHE[key]
    try:
        meta = _get(p, "/server/files/metadata?filename=" + quote(filename, safe=""))
        thumbs = meta.get("thumbnails") or []
        if not thumbs:
            _THUMB_CACHE[key] = None
            return None
        best = max(thumbs, key=lambda t: (t.get("width", 0) * t.get("height", 0), t.get("size", 0)))
        rel = best.get("relative_path")
        if not rel:
            _THUMB_CACHE[key] = None
            return None
        parent = PurePosixPath(filename).parent
        full_rel = str(parent / rel) if str(parent) != "." else rel
        url_path = "/server/files/gcodes/" + "/".join(quote(part, safe="") for part in full_rel.split("/") if part)
        data = _get_bytes(p, url_path)
        _THUMB_CACHE[key] = data
        return data
    except Exception:
        return None


def webcam_url(p):
    """First webcam stream URL from Moonraker's webcam list (None if not configured)."""
    if SIM.is_sim_printer(getattr(p, "id", "")):
        return None
    for w in _get(p, "/server/webcams/list").get("webcams", []):
        u = w.get("stream_url") or w.get("snapshot_url")
        if u:
            return u if u.startswith("http") else p.base + (u if u.startswith("/") else "/" + u)
    return None


def probe_port(host, port, timeout=0.4):
    """Check if a TCP port is open (e.g. for display server detection)."""
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


def printer_webcams(p):
    """List of all webcams configured on printer p: [{'printer': ..., 'name': ..., 'url': ...}]."""
    if SIM.is_sim_printer(getattr(p, "id", "")):
        return []
    cams = []
    try:
        data = _get(p, "/server/webcams/list", timeout=3)
        wlist = data.get("webcams", []) if isinstance(data, dict) else []
        for w in wlist:
            u = w.get("stream_url") or w.get("snapshot_url")
            if u:
                full_url = u if u.startswith("http") else p.base + (u if u.startswith("/") else "/" + u)
                name = w.get("name") or p.name
                service = w.get("service", "")
                if full_url.endswith("/webrtc"):
                    full_url = full_url[:-6] + "player"
                    service = "iframe"
                cams.append({
                    "printer": p.name,
                    "name": name,
                    "url": full_url,
                    "service": service,
                })
    except Exception:
        pass
    if not cams:
        try:
            u = webcam_url(p)
            if u:
                cams.append({
                    "printer": p.name,
                    "name": "Kamera",
                    "url": u,
                    "service": "mjpeg",
                })
        except Exception:
            pass

    display_url = getattr(p, "display_url", "").strip()
    if not display_url and probe_port(p.host, 18080):
        display_url = f"http://{p.host}:18080/"

    if display_url:
        has_display = any(
            c["url"].rstrip("/").endswith((":18080", "/screen", "/gui"))
            or c["name"].lower() in ("gui", "screen", "display")
            for c in cams
        )
        if not has_display:
            cams.append({
                "printer": p.name,
                "name": "Display",
                "url": display_url,
                "service": "iframe",
            })

    for c in cams:
        name = c["name"]
        if len(cams) > 1 or name != p.name:
            if not name.startswith(f"{p.name} · "):
                c["name"] = f"{p.name} · {name}"

    return cams


def all_webcams(printers):
    """Fetch all webcams for a list of printers concurrently."""
    if not printers:
        return []
    results = []
    with ThreadPoolExecutor(max_workers=min(len(printers), 8)) as ex:
        futs = [ex.submit(printer_webcams, p) for p in printers]
        for f in futs:
            try:
                results.extend(f.result())
            except Exception:
                pass
    return results


def _post(p, path, data=None, raw=None, ctype="application/json", timeout=30):
    body = raw if raw is not None else json.dumps(data or {}).encode()
    with urlopen(Request(p.base + path, data=body, headers=_headers(p, ctype), method="POST"), timeout=timeout) as r:
        return json.loads(r.read(2 * 1024 * 1024) or b"{}")


def _delete(p, path, timeout=15):
    with urlopen(Request(p.base + path, headers=_headers(p), method="DELETE"), timeout=timeout) as r:
        return json.loads(r.read(2 * 1024 * 1024) or b"{}")


def gcode(p, script):
    if SIM.is_sim_printer(getattr(p, "id", "")):
        return SIM.control(p, "gcode", script=script)
    return _post(p, "/printer/gcode/script", {"script": script})


def control(p, action, **kw):
    if SIM.is_sim_printer(getattr(p, "id", "")):
        return SIM.control(p, action, **kw)

    if getattr(p, "printer_type", "moonraker") == "bambu":
        from . import bambu
        client = bambu.get_or_create_client(p)
        if not client:
            raise RuntimeError("Bambu Lab Drucker nicht verbunden.")
        if action == "pause":
            return {"result": client.pause()}
        if action == "resume":
            return {"result": client.resume()}
        if action == "cancel":
            return {"result": client.stop_print()}
        if action == "temp":
            heater = kw.get("heater", "")
            target = float(kw.get("target", 0))
            if "bed" in heater.lower() or "bett" in heater.lower():
                return {"result": client.set_bed_temp(target)}
            return {"result": client.set_nozzle_temp(target)}
        if action == "fan":
            return {"result": client.set_fan(int(kw.get("percent", kw.get("speed", 0))))}
        if action == "speed":
            lvl = int(kw.get("level", 1))
            return {"result": client.set_speed_level(lvl)}
        if action == "chamber_light":
            return {"result": client.set_chamber_light(bool(kw.get("on", True)))}
        raise NotImplementedError(f"Aktion '{action}' wird für geschlossenes Bambu Lab System nicht unterstützt.")

    if action in ("pause", "resume", "cancel"):
        return _post(p, f"/printer/print/{action}")
    if action in ("emergency_stop", "firmware_restart", "restart"):
        return _post(p, f"/printer/{action}")
    if action == "temp":
        name = kw["heater"].replace("heater_generic ", "")
        if not re.fullmatch(r"[A-Za-z0-9_]+", name):
            raise ValueError("invalid heater")
        return gcode(p, f"SET_HEATER_TEMPERATURE HEATER={name} TARGET={float(kw['target']):.0f}")
    if action == "fan":
        pct = float(kw.get("percent", kw.get("speed", 0)))
        return gcode(p, f"M106 S{max(0, min(255, int(pct * 2.55)))}")
    if action == "speed":
        pct = max(10, min(300, int(float(kw.get("percent", 100)))))
        return gcode(p, f"M220 S{pct}")
    if action == "flow":
        pct = max(50, min(200, int(float(kw.get("percent", 100)))))
        return gcode(p, f"M221 S{pct}")
    if action == "macro":
        if not re.fullmatch(r"[A-Za-z0-9_]+", kw["name"]):
            raise ValueError("invalid macro")
        return gcode(p, kw["name"])
    if action == "home":
        axes = kw.get("axes", "").strip().upper()
        if axes and not re.fullmatch(r"[XYZ ]+", axes):
            raise ValueError("invalid axes")
        return gcode(p, f"G28 {axes}".strip())
    if action == "jog":
        axis = str(kw.get("axis", "")).upper()
        if axis not in ("X", "Y", "Z", "E"):
            raise ValueError("invalid axis")
        dist = float(kw["dist"])
        speed = int(kw.get("speed", 600 if axis == "Z" else (300 if axis == "E" else 3000)))
        return gcode(p, f"G91\nG1 {axis}{dist:+.2f} F{speed}\nG90")
    if action == "z_offset":
        if kw.get("reset"):
            return gcode(p, "SET_GCODE_OFFSET Z=0 MOVE=1")
        delta = float(kw["delta"])
        return gcode(p, f"SET_GCODE_OFFSET Z_ADJUST={delta:+.3f} MOVE=1")
    if action == "exclude_object":
        obj_name = str(kw.get("name", "")).strip()
        if not obj_name or not re.fullmatch(r"[A-Za-z0-9_.\-]+", obj_name):
            raise ValueError("invalid object name")
        return gcode(p, f"EXCLUDE_OBJECT NAME={obj_name}")
    if action == "bed_mesh_calibrate":
        return gcode(p, "BED_MESH_CALIBRATE")
    if action == "qgl":
        return gcode(p, "QUAD_GANTRY_LEVEL")
    if action == "z_tilt":
        return gcode(p, "Z_TILT_ADJUST")
    if action == "motors_off":
        return gcode(p, "M84")
    if action == "load_filament":
        return gcode(p, "M83\nG1 E50 F300\nG90")
    if action == "unload_filament":
        return gcode(p, "M83\nG1 E-50 F600\nG90")
    raise ValueError(action)


def set_temp(p, heater, target):
    return control(p, "temp", heater=heater, target=target)


def set_fan(p, percent):
    return control(p, "fan", percent=percent)


def set_speed(p, percent, level=None):
    return control(p, "speed", percent=percent, level=level or 1)


def set_flow(p, percent):
    return control(p, "flow", percent=percent)


def jog(p, dx=0.0, dy=0.0, dz=0.0, de=0.0):
    if dx:
        return control(p, "jog", axis="X", dist=dx)
    if dy:
        return control(p, "jog", axis="Y", dist=dy)
    if dz:
        return control(p, "jog", axis="Z", dist=dz)
    if de:
        return control(p, "jog", axis="E", dist=de, speed=300)
    return {"result": "ok"}


def macros(p):
    if SIM.is_sim_printer(getattr(p, "id", "")):
        return SIM.get_macros(p)
    objs = _get(p, "/printer/objects/list")["objects"]
    return sorted(o[12:] for o in objs if o.startswith("gcode_macro ") and not o[12:].startswith("_"))


def upload(p, path, start=False):
    """Upload a G-code file to the printer's gcodes root (multipart)."""
    f = Path(path)
    if SIM.is_sim_printer(getattr(p, "id", "")):
        if start:
            SIM.control(p, "start_file", filename=f.name)
        return {"result": "ok", "item": {"path": f.name}}
    b = uuid.uuid4().hex
    parts = [
        f'--{b}\r\nContent-Disposition: form-data; name="root"\r\n\r\ngcodes\r\n',
        f'--{b}\r\nContent-Disposition: form-data; name="print"\r\n\r\n{"true" if start else "false"}\r\n',
        f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{f.name}"\r\n'
        'Content-Type: application/octet-stream\r\n\r\n',
    ]
    body = "".join(parts).encode() + f.read_bytes() + f"\r\n--{b}--\r\n".encode()
    return _post(p, "/server/files/upload", raw=body, ctype=f"multipart/form-data; boundary={b}", timeout=60)


def upload_gcode(p, path, start_print=False):
    return upload(p, path, start=start_print)


def remote_files(p):
    """Return list of G-code files stored on the printer."""
    if SIM.is_sim_printer(getattr(p, "id", "")):
        return SIM.get_remote_files(p)
    res = _get(p, "/server/files/list?root=gcodes")
    files = res if isinstance(res, list) else res.get("files", [])
    return sorted(files, key=lambda x: x.get("modified", 0), reverse=True)


def files(p):
    return remote_files(p)


def start_print(p, filename):
    """Start printing a G-code file already on the printer."""
    if SIM.is_sim_printer(getattr(p, "id", "")):
        return SIM.control(p, "start_file", filename=filename)
    return _post(p, "/printer/print/start", {"filename": filename})


def delete_remote_file(p, filename):
    """Delete a G-code file from the printer."""
    if SIM.is_sim_printer(getattr(p, "id", "")):
        return {"result": "deleted"}
    url_path = "/server/files/gcodes/" + "/".join(quote(part, safe="") for part in filename.split("/") if part)
    return _delete(p, url_path)


def download_remote_file(p, filename, dest_dir):
    """Download a G-code file from the printer to dest_dir and return the saved Path."""
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / PurePosixPath(filename).name
    if SIM.is_sim_printer(getattr(p, "id", "")):
        target.write_text(
            f"; generated by OrcaSlicer 2.2.0\n; estimated printing time = 1h 45m\n; total filament used [g] = 42.5\nG28\nG1 X100 Y100 Z0.2 E5.0\n",
            encoding="utf-8",
        )
        return target
    url_path = "/server/files/gcodes/" + "/".join(quote(part, safe="") for part in filename.split("/") if part)
    data = _get_bytes(p, url_path, timeout=60)
    target.write_bytes(data)
    return target


def gcode_store(p, count=100):
    """Fetch recent G-code responses from Moonraker's gcode_store."""
    if SIM.is_sim_printer(getattr(p, "id", "")):
        return SIM.get_console(p)[-int(count):]
    res = _get(p, f"/server/gcode_store?count={int(count)}")
    return res.get("gcode_store", []) if isinstance(res, dict) else []


def history(p, limit=200):
    if SIM.is_sim_printer(getattr(p, "id", "")):
        return SIM.get_history(p)[:int(limit)]
    return _get(p, f"/server/history/list?limit={int(limit)}&order=desc").get("jobs", [])


def spools(p):
    r = _post(p, "/server/spoolman/proxy", {"request_method": "GET", "path": "/v1/spool"})
    return [
        {
            "name": (s.get("filament") or {}).get("name", "?"),
            "material": (s.get("filament") or {}).get("material", ""),
            "remaining": s.get("remaining_weight"),
        }
        for s in r.get("response", [])
    ]


def _probe_moonraker(host, port, timeout=0.6):
    url = f"http://{host}:{port}/printer/info"
    try:
        req = Request(url, headers={"Accept": "application/json", "User-Agent": "PrintBoard/1.0"})
        with urlopen(req, timeout=timeout) as r:
            j = json.loads(r.read(65536))
        res = j.get("result", j) if isinstance(j, dict) else {}
        if isinstance(res, dict) and ("state" in res or "hostname" in res or "software_version" in res):
            return {
                "name": res.get("hostname") or f"Klipper ({host})",
                "host": host,
                "port": port,
                "state": res.get("state", "ready"),
            }
    except Exception:
        pass
    return None


def _local_ipv4_prefixes():
    prefixes = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        if not ip.startswith("127."):
            prefixes.add(".".join(ip.split(".")[:3]))
    except Exception:
        pass
    try:
        out = subprocess.check_output(["ip", "-4", "-o", "addr", "show"], text=True, timeout=2)
        for m in re.finditer(r"inet\s+(\d+\.\d+\.\d+)\.\d+/", out):
            if not m.group(1).startswith("127."):
                prefixes.add(m.group(1))
    except Exception:
        pass
    return list(prefixes)[:2]


def discover_printers(timeout=0.65):
    """Discover Moonraker/Klipper printers via mDNS (avahi-browse) and local subnet scan."""
    found = {}

    for service in ("_moonraker._tcp", "_http._tcp"):
        try:
            out = subprocess.check_output(
                ["avahi-browse", "-tpr", service],
                text=True,
                timeout=2.0,
                stderr=subprocess.DEVNULL,
            )
            for line in out.splitlines():
                if not line.startswith("="):
                    continue
                parts = line.split(";")
                if len(parts) >= 9:
                    host_ip = parts[7]
                    try:
                        port = int(parts[8])
                    except ValueError:
                        continue
                    if ":" in host_ip:
                        continue
                    info = _probe_moonraker(host_ip, port, timeout=timeout)
                    if info:
                        found[(info["host"], info["port"])] = info
        except Exception:
            pass

    candidates = [("127.0.0.1", 7125)]
    for pref in _local_ipv4_prefixes():
        for i in range(1, 255):
            ip = f"{pref}.{i}"
            candidates.append((ip, 7125))
            candidates.append((ip, 80))

    with ThreadPoolExecutor(max_workers=64) as ex:
        futs = [ex.submit(_probe_moonraker, h, p, timeout) for h, p in candidates if (h, p) not in found]
        for fut in as_completed(futs):
            res = fut.result()
            if res:
                found[(res["host"], res["port"])] = res

    return sorted(found.values(), key=lambda x: (x["host"], x["port"]))
