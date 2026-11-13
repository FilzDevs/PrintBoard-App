"""Complete Spoolman REST API v1 client and Klipper/Moonraker spool synchronization."""
from concurrent.futures import ThreadPoolExecutor
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from . import api

TIMEOUT = 6


def normalize_url(url):
    """Normalize a Spoolman base URL (e.g. 'http://192.168.178.170:7912')."""
    if not url:
        return ""
    u = str(url).strip().rstrip("/")
    if not u:
        return ""
    if not u.startswith(("http://", "https://")):
        u = "http://" + u
    for suffix in ("/api/v1", "/api"):
        if u.endswith(suffix):
            u = u[: -len(suffix)].rstrip("/")
    return u


def _headers(ctype="application/json"):
    h = {"Accept": "application/json", "User-Agent": "PrintBoard/0.4"}
    if ctype:
        h["Content-Type"] = ctype
    return h


def _request(base_url, method, path, data=None, params=None, timeout=TIMEOUT):
    base = normalize_url(base_url)
    if not base:
        raise ValueError("Keine Spoolman Server-URL konfiguriert.")
    url = f"{base}/api/v1{path}"
    if params:
        clean_params = {k: v for k, v in params.items() if v is not None}
        if clean_params:
            url += ("&" if "?" in url else "?") + urlencode(clean_params)
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    req = Request(url, data=body, headers=_headers("application/json" if body is not None else None), method=method)
    try:
        with urlopen(req, timeout=timeout) as r:
            raw = r.read(16 * 1024 * 1024)
            return json.loads(raw.decode("utf-8")) if raw else {}
    except HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")
            err_json = json.loads(err_body)
            msg = err_json.get("message") or err_json.get("detail") or err_body
        except Exception:
            msg = str(e)
        raise RuntimeError(f"Spoolman HTTP {e.code}: {msg}") from e
    except URLError as e:
        raise RuntimeError(f"Spoolman nicht erreichbar ({base}): {e.reason}") from e



def decode_extra(extra):
    """Decode Spoolman 'extra' map of JSON-encoded strings into native Python values."""
    if not isinstance(extra, dict):
        return {}
    out = {}
    for k, v in extra.items():
        if v is None:
            out[k] = ""
            continue
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                out[k] = parsed if parsed is not None else ""
            except Exception:
                out[k] = v.strip('"')
        else:
            out[k] = v
    return out


def encode_extra_value(val):
    """Encode a Python value as a JSON string for Spoolman 'extra' dict (or None to clear)."""
    if val is None or (isinstance(val, str) and not val.strip()):
        return None
    if isinstance(val, str):
        return json.dumps(val.strip())
    return json.dumps(val)


def format_card_uid(raw_uid):
    """Convert Klipper filament_detect CARD_UID (list of ints or hex str) into uppercase hex string."""
    if isinstance(raw_uid, (list, tuple)) and len(raw_uid) >= 4:
        try:
            return "".join(f"{int(b) & 0xFF:02X}" for b in raw_uid)
        except Exception:
            return ""
    if isinstance(raw_uid, str) and raw_uid.strip() and raw_uid.strip() != "0":
        return raw_uid.strip().strip('"').upper()
    return ""


def spool_display_name(spool):
    """Human-readable title for a spool dict."""
    if not spool:
        return "—"
    sid = spool.get("id", "?")
    fil = spool.get("filament") or {}
    vendor = (fil.get("vendor") or {}).get("name") or ""
    fname = fil.get("name") or "?"
    mat = fil.get("material") or ""
    full = f"{vendor} {fname}".strip() if vendor and not fname.lower().startswith(vendor.lower()) else fname
    mat_str = f" [{mat}]" if mat else ""
    return f"#{sid} {full}{mat_str}"


def spool_colors(spool_or_filament):
    """Return list of hex color strings (e.g. ['#FF0000']) for a spool or filament dict."""
    if not spool_or_filament:
        return ["#64748b"]
    fil = spool_or_filament.get("filament", spool_or_filament) if isinstance(spool_or_filament, dict) else {}
    multi = fil.get("multi_color_hexes") or fil.get("color_hexes")
    if multi:
        if isinstance(multi, str):
            parts = [c.strip().lstrip("#") for c in multi.split(",") if c.strip()]
        elif isinstance(multi, list):
            parts = [str(c).strip().lstrip("#") for c in multi if c]
        else:
            parts = []
        if parts:
            return [f"#{p[:6]}" for p in parts]
    chex = (fil.get("color_hex") or "").strip().lstrip("#")
    if len(chex) >= 6:
        return [f"#{chex[:6]}"]
    return ["#64748b"]


def spool_initial_weight(spool):
    """Determine initial net filament weight (g) of a spool for percentage calculation."""
    if not spool:
        return 1000.0
    init_w = spool.get("initial_weight")
    if init_w and init_w > 0:
        return float(init_w)
    fil = spool.get("filament") or {}
    fw = fil.get("weight")
    if fw and fw > 0:
        return float(fw)
    rem = float(spool.get("remaining_weight") or 0.0)
    used = float(spool.get("used_weight") or 0.0)
    if rem + used > 0:
        return rem + used
    return 1000.0


def spool_price(spool):
    """Return effective spool price in EUR (spool.price fallback to filament.price)."""
    if not spool:
        return None
    if spool.get("price") is not None:
        return float(spool["price"])
    fil = spool.get("filament") or {}
    if fil.get("price") is not None:
        return float(fil["price"])
    return None



def probe_spoolman(url, timeout=2.0):
    """Check if url points to a valid Spoolman instance and return its /info dict or None."""
    base = normalize_url(url)
    if not base:
        return None
    try:
        info = _request(base, "GET", "/info", timeout=timeout)
        if isinstance(info, dict) and "version" in info:
            return {"url": base, "version": info.get("version", "?"), "info": info}
    except Exception:
        pass
    return None


def discover_url(printers=None):
    """Discover Spoolman server URL from configured printers (Moonraker /server/config) or local port 7912."""
    candidates = []
    for p in printers or []:
        try:
            cfg = api._get(p, "/server/config", timeout=2.5).get("config", {})
            for section in ("spoolman", "spoollink"):
                srv = (cfg.get(section) or {}).get("server")
                if srv:
                    norm = normalize_url(srv)
                    if norm and norm not in candidates:
                        candidates.append(norm)
        except Exception:
            pass
    for local_candidate in ("http://127.0.0.1:7912", "http://localhost:7912"):
        if local_candidate not in candidates:
            candidates.append(local_candidate)
    for p in printers or []:
        host_cand = f"http://{p.host}:7912"
        if host_cand not in candidates:
            candidates.append(host_cand)

    for cand in candidates:
        res = probe_spoolman(cand, timeout=1.8)
        if res:
            return res["url"]
    return candidates[0] if candidates else ""



def get_info(base_url):
    return _request(base_url, "GET", "/info")


def get_health(base_url):
    return _request(base_url, "GET", "/health")


def trigger_backup(base_url):
    return _request(base_url, "POST", "/backup", data={})


# -- Spools --

def list_spools(base_url, allow_archived=True):
    params = {"allow_archived": "true" if allow_archived else "false"}
    res = _request(base_url, "GET", "/spool", params=params)
    return res if isinstance(res, list) else []


def get_spool(base_url, spool_id):
    return _request(base_url, "GET", f"/spool/{int(spool_id)}")


def create_spool(base_url, data):
    return _request(base_url, "POST", "/spool", data=data)


def update_spool(base_url, spool_id, data):
    return _request(base_url, "PATCH", f"/spool/{int(spool_id)}", data=data)


def delete_spool(base_url, spool_id):
    return _request(base_url, "DELETE", f"/spool/{int(spool_id)}")


def use_spool(base_url, spool_id, use_weight=None, use_length=None):
    payload = {}
    if use_weight is not None:
        payload["use_weight"] = float(use_weight)
    elif use_length is not None:
        payload["use_length"] = float(use_length)
    else:
        raise ValueError("Entweder Gewicht (g) oder Länge (mm) angeben.")
    return _request(base_url, "PUT", f"/spool/{int(spool_id)}/use", data=payload)


def measure_spool(base_url, spool_id, gross_weight):
    return _request(base_url, "PUT", f"/spool/{int(spool_id)}/measure", data={"weight": float(gross_weight)})


# -- Filaments --

def list_filaments(base_url):
    res = _request(base_url, "GET", "/filament")
    return res if isinstance(res, list) else []


def get_filament(base_url, filament_id):
    return _request(base_url, "GET", f"/filament/{int(filament_id)}")


def create_filament(base_url, data):
    return _request(base_url, "POST", "/filament", data=data)


def update_filament(base_url, filament_id, data):
    return _request(base_url, "PATCH", f"/filament/{int(filament_id)}", data=data)


def delete_filament(base_url, filament_id):
    return _request(base_url, "DELETE", f"/filament/{int(filament_id)}")


# -- Vendors --

def list_vendors(base_url):
    res = _request(base_url, "GET", "/vendor")
    return res if isinstance(res, list) else []


def get_vendor(base_url, vendor_id):
    return _request(base_url, "GET", f"/vendor/{int(vendor_id)}")


def create_vendor(base_url, data):
    return _request(base_url, "POST", "/vendor", data=data)


def update_vendor(base_url, vendor_id, data):
    return _request(base_url, "PATCH", f"/vendor/{int(vendor_id)}", data=data)


def delete_vendor(base_url, vendor_id):
    return _request(base_url, "DELETE", f"/vendor/{int(vendor_id)}")


# -- Locations, Materials, Extra Fields --

def list_locations(base_url):
    try:
        res = _request(base_url, "GET", "/location")
        return [str(x) for x in res if x] if isinstance(res, list) else []
    except Exception:
        return []


def rename_location(base_url, old_name, new_name):
    return _request(base_url, "PATCH", f"/location/{quote(str(old_name), safe='')}", data={"name": str(new_name)})


def list_materials(base_url):
    try:
        res = _request(base_url, "GET", "/material")
        return [str(x) for x in res if x] if isinstance(res, list) else []
    except Exception:
        return []


def list_extra_fields(base_url, entity_type="spool"):
    try:
        res = _request(base_url, "GET", f"/field/{quote(entity_type, safe='')}")
        return res if isinstance(res, list) else []
    except Exception:
        return []


# -- External SpoolmanDB Catalog --

def search_external_filaments(base_url, query="", limit=60, offset=0):
    q = (query or "").strip()
    if q:
        try:
            res = _request(
                base_url,
                "GET",
                "/external/filament/search",
                params={"query": q, "limit": min(100, max(1, int(limit))), "offset": max(0, int(offset))},
                timeout=8,
            )
            if isinstance(res, list):
                return res
        except Exception:
            pass
    # Fallback to full external list filtered client-side
    all_ext = _request(base_url, "GET", "/external/filament", timeout=10)
    if not isinstance(all_ext, list):
        return []
    if not q:
        return all_ext[offset : offset + limit]
    terms = q.lower().split()
    matched = []
    for item in all_ext:
        hay = f"{item.get('manufacturer', '')} {item.get('name', '')} {item.get('material', '')}".lower()
        if all(t in hay for t in terms):
            matched.append(item)
            if len(matched) >= offset + limit:
                break
    return matched[offset : offset + limit]


def import_external_filament(base_url, ext_item, vendors=None):
    """Import an external filament (and its vendor if not yet present) into Spoolman."""
    if vendors is None:
        vendors = list_vendors(base_url)
    mfg = (ext_item.get("manufacturer") or "").strip()
    vendor_id = None
    if mfg:
        existing = next((v for v in vendors if (v.get("name") or "").strip().lower() == mfg.lower()), None)
        if existing:
            vendor_id = existing["id"]
        else:
            v_payload = {"name": mfg, "external_id": mfg}
            if ext_item.get("spool_weight") is not None:
                v_payload["empty_spool_weight"] = float(ext_item["spool_weight"])
            created_v = create_vendor(base_url, v_payload)
            vendor_id = created_v.get("id")

    f_payload = {
        "name": ext_item.get("name") or mfg or "Filament",
        "vendor_id": vendor_id,
        "material": ext_item.get("material") or "PLA",
        "density": float(ext_item.get("density") or 1.24),
        "diameter": float(ext_item.get("diameter") or 1.75),
        "external_id": ext_item.get("id"),
    }
    if ext_item.get("weight") and float(ext_item["weight"]) > 0:
        f_payload["weight"] = float(ext_item["weight"])
    if ext_item.get("spool_weight") is not None:
        f_payload["spool_weight"] = float(ext_item["spool_weight"])
    if ext_item.get("extruder_temp") is not None:
        f_payload["settings_extruder_temp"] = int(ext_item["extruder_temp"])
    if ext_item.get("bed_temp") is not None:
        f_payload["settings_bed_temp"] = int(ext_item["bed_temp"])

    c_hexes = ext_item.get("color_hexes")
    if isinstance(c_hexes, list) and len(c_hexes) > 1:
        f_payload["multi_color_hexes"] = ",".join(str(c).lstrip("#") for c in c_hexes if c)
        f_payload["multi_color_direction"] = ext_item.get("multi_color_direction") or "coaxial"
    elif ext_item.get("color_hex"):
        f_payload["color_hex"] = str(ext_item["color_hex"]).lstrip("#")
    elif isinstance(c_hexes, list) and len(c_hexes) == 1:
        f_payload["color_hex"] = str(c_hexes[0]).lstrip("#")

    return create_filament(base_url, f_payload)



def printer_spool_status(p):
    """Query a printer's Moonraker & Klipper state for active Spoolman spool(s), toolhead slots, and NFC tags."""
    out = {
        "printer_id": p.id,
        "printer_name": p.name,
        "online": False,
        "moonraker_spoolman": False,
        "spoolman_connected": False,
        "active_spool_id": None,
        "has_set_spool_macro": False,
        "active_extruder": "extruder",
        "slots": [],  # [{'channel': 0, 'label': 'T0', 'spool_id': 19, 'exist': True, 'active': False, 'type': 'PLA', 'color': '#FFFFFF', 'card_uid': '046F4B3FE22A81'}]
    }
    try:
        objs = api._get(p, "/printer/objects/list", timeout=3).get("objects", [])
        out["online"] = True
    except Exception as e:
        out["error"] = str(e)
        return out

    out["has_set_spool_macro"] = "gcode_macro SET_SPOOL_ID" in objs

    # 1. Check Moonraker /server/spoolman/status or /server/spoolman/spool_id
    try:
        sm = api._get(p, "/server/spoolman/status", timeout=2.5)
        if isinstance(sm, dict):
            out["moonraker_spoolman"] = True
            out["spoolman_connected"] = bool(sm.get("spoolman_connected", True))
            out["active_spool_id"] = sm.get("spool_id")
            out["pending_reports"] = sm.get("pending_reports") or []
    except Exception:
        try:
            sm_id = api._get(p, "/server/spoolman/spool_id", timeout=2.0)
            if isinstance(sm_id, dict):
                out["moonraker_spoolman"] = True
                out["spoolman_connected"] = True
                out["active_spool_id"] = sm_id.get("spool_id")
        except Exception:
            pass

    # 2. Check Klipper toolhead + multi-extruder / NFC objects (e.g. Snapmaker U1 print_task_config & filament_detect)
    query_objs = [o for o in ("toolhead", "print_task_config", "filament_detect") if o in objs]
    if query_objs:
        try:
            q = "&".join(quote(o, safe="") for o in query_objs)
            st = api._get(p, "/printer/objects/query?" + q, timeout=3).get("status", {})
            th = st.get("toolhead") or {}
            active_ext = th.get("extruder") or "extruder"
            out["active_extruder"] = active_ext

            ptc = st.get("print_task_config") or {}
            fdet = (st.get("filament_detect") or {}).get("info") or []
            spool_ids = ptc.get("filament_spool_id") or []
            f_exist = ptc.get("filament_exist") or []
            f_types = ptc.get("filament_type") or []
            f_vendors = ptc.get("filament_vendor") or []
            f_colors = ptc.get("filament_color_rgba") or []

            num_slots = max(len(spool_ids), len(fdet))
            for ch in range(num_slots):
                ext_name = "extruder" if ch == 0 else f"extruder{ch}"
                sid = spool_ids[ch] if ch < len(spool_ids) else 0
                sid = int(sid) if sid and int(sid) > 0 else None
                det_info = fdet[ch] if ch < len(fdet) and isinstance(fdet[ch], dict) else {}
                uid = format_card_uid(det_info.get("CARD_UID"))
                rgba = f_colors[ch] if ch < len(f_colors) and f_colors[ch] else "FFFFFF"
                color_hex = "#" + str(rgba)[:6]
                ftype = f_types[ch] if ch < len(f_types) else det_info.get("MAIN_TYPE", "")
                fvendor = f_vendors[ch] if ch < len(f_vendors) else det_info.get("VENDOR", "")
                exist = bool(f_exist[ch]) if ch < len(f_exist) else bool(uid)
                out["slots"].append({
                    "channel": ch,
                    "label": f"T{ch}",
                    "extruder": ext_name,
                    "spool_id": sid,
                    "exist": exist,
                    "active": active_ext == ext_name,
                    "type": "" if ftype == "NONE" else ftype,
                    "vendor": "" if fvendor == "NONE" else fvendor,
                    "color": color_hex,
                    "card_uid": uid,
                })
        except Exception:
            pass

    return out


def assign_spool_to_printer(p, spool_id, channel=None):
    """Assign a Spoolman spool ID (or None/0 to clear) to a printer or specific toolhead channel."""
    sid = int(spool_id) if spool_id and int(spool_id) > 0 else None
    results = {}

    if channel is not None:
        # Use Klipper macro SET_SPOOL_ID CHANNEL=<ch> SPOOL_ID=<id>
        ch = int(channel)
        macro_sid = sid if sid is not None else 0
        api.gcode(p, f"SET_SPOOL_ID CHANNEL={ch} SPOOL_ID={macro_sid}")
        results["channel"] = ch
        results["spool_id"] = sid
        # Also set Moonraker active spool if this channel is active or default
        try:
            api._post(p, "/server/spoolman/spool_id", {"spool_id": sid})
        except Exception:
            pass
        return results

    # Standard Moonraker endpoint
    try:
        res = api._post(p, "/server/spoolman/spool_id", {"spool_id": sid})
        results["moonraker"] = res
        results["spool_id"] = sid
        return results
    except Exception as e:
        # If printer has SET_SPOOL_ID macro, fallback to channel 0
        try:
            objs = api._get(p, "/printer/objects/list", timeout=2.5).get("objects", [])
            if "gcode_macro SET_SPOOL_ID" in objs:
                api.gcode(p, f"SET_SPOOL_ID CHANNEL=0 SPOOL_ID={sid or 0}")
                results["channel"] = 0
                results["spool_id"] = sid
                return results
        except Exception:
            pass
        raise RuntimeError(f"Moonraker auf {p.name} unterstützt keinen direkten Spoolman-Aufruf ({e}).") from e


def link_nfc_uid_to_spool(base_url, spool, card_uid):
    """Link an NFC tag UID (e.g. '04974B3FE22A81') to a Spoolman spool's extra.card_uids field."""
    uid = format_card_uid(card_uid)
    if not uid:
        raise ValueError("Ungültige NFC Card-UID.")
    extra_dec = decode_extra(spool.get("extra"))
    existing = [u.strip().upper() for u in str(extra_dec.get("card_uids", "")).split(",") if u.strip()]
    if uid not in existing:
        existing.append(uid)
    merged = ",".join(existing)
    return update_spool(base_url, spool["id"], {"extra": {"card_uids": encode_extra_value(merged)}})


def fetch_bundle(base_url, printers=None, allow_archived=True):
    """Fetch complete Spoolman state + printer spool assignments concurrently."""
    base = normalize_url(base_url)
    if not base and printers:
        base = discover_url(printers)
    if not base:
        raise ValueError("Keine Spoolman Server-URL konfiguriert oder im Netzwerk gefunden.")

    info = get_info(base)
    with ThreadPoolExecutor(max_workers=8) as ex:
        f_spools = ex.submit(list_spools, base, allow_archived)
        f_fils = ex.submit(list_filaments, base)
        f_vends = ex.submit(list_vendors, base)
        f_locs = ex.submit(list_locations, base)
        f_mats = ex.submit(list_materials, base)
        f_printers = [ex.submit(printer_spool_status, p) for p in (printers or [])]

        spools = f_spools.result()
        filaments = f_fils.result()
        vendors = f_vends.result()
        locations = f_locs.result()
        materials = f_mats.result()
        p_states = []
        for fp in f_printers:
            try:
                p_states.append(fp.result())
            except Exception:
                pass

    return {
        "url": base,
        "info": info,
        "spools": spools,
        "filaments": filaments,
        "vendors": vendors,
        "locations": locations,
        "materials": materials,
        "printer_states": p_states,
    }
