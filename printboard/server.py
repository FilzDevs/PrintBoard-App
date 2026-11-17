"""PrintBoard Central Server, Telemetry Engine, REST API & Native Desktop Bridge.
Powers the standalone desktop application (`printboard`), the central server (`printboard-server`),
and the remote client (`printboard-client`).
"""
import base64
from collections import deque
from dataclasses import asdict
import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
import threading
import time
from urllib.parse import parse_qs, urlparse
import uuid

from . import api, costs, library, model_search, notify, spoolman, store
from .pages import (
    S, models_dir, notify_cfg, set_local_printer_spool, set_spoolman_url,
    slicer_cmd, spoolman_url, local_printer_spool
)
from .sim import DEMO_SPOOLS, SIM
from .ui_theme import DEFAULT_TASKS, load_maint, load_queue, save_maint, save_queue

logger = logging.getLogger("printboard.server")

DRYING_FILE = store.CFG / "drying.json"
CUSTOM_MAINT_FILE = store.CFG / "custom_maint_tasks.json"

DRYING_PRESETS = [
    {"material": "PLA / PLA+", "temp_c": 50, "hours": 4.0, "max_temp_c": 55, "humidity_target": "< 20%", "notes": "Unter Glasübergangstemperatur (55°C) bleiben."},
    {"material": "PETG / PETG-CF", "temp_c": 65, "hours": 6.0, "max_temp_c": 70, "humidity_target": "< 15%", "notes": "Zieht stark Feuchtigkeit (Fädenbildung bei Nässe)."},
    {"material": "ABS / ASA", "temp_c": 80, "hours": 6.0, "max_temp_c": 85, "humidity_target": "< 15%", "notes": "Vor dem Druck trocknen verhindert Bläschen und Warping."},
    {"material": "TPU / TPE (Flex)", "temp_c": 55, "hours": 6.0, "max_temp_c": 65, "humidity_target": "< 12%", "notes": "Sehr hygroskopisch; am besten direkt aus Drybox drucken."},
    {"material": "PA / Nylon / PA-CF", "temp_c": 85, "hours": 12.0, "max_temp_c": 90, "humidity_target": "< 10%", "notes": "Extrem hygroskopisch — zwingend aus beheizter Drybox drucken."},
    {"material": "PC (Polycarbonat)", "temp_c": 85, "hours": 8.0, "max_temp_c": 90, "humidity_target": "< 10%", "notes": "Feuchtigkeit reduziert Schichthaftung drastisch."},
    {"material": "PVA / BVOH (Support)", "temp_c": 55, "hours": 8.0, "max_temp_c": 60, "humidity_target": "< 10%", "notes": "Wasserlöslich — luftdicht mit Silikagel lagern."},
]


def load_drying_timers() -> list:
    try:
        return json.loads(DRYING_FILE.read_text())
    except Exception:
        return []


def save_drying_timers(items: list):
    store.CFG.mkdir(parents=True, exist_ok=True)
    DRYING_FILE.write_text(json.dumps(items, indent=2))


def load_all_maint_tasks() -> list:
    base = [{"key": k, "title": t, "interval_h": h, "builtin": True} for k, t, h in DEFAULT_TASKS]
    try:
        custom = json.loads(CUSTOM_MAINT_FILE.read_text())
        if isinstance(custom, list):
            base.extend(custom)
    except Exception:
        pass
    return base


def save_custom_maint_tasks(custom_list: list):
    store.CFG.mkdir(parents=True, exist_ok=True)
    CUSTOM_MAINT_FILE.write_text(json.dumps(custom_list, indent=2))


class ServerEngine:
    """Manages background polling, state cache, notifications, temp history, and printer operations."""

    def __init__(self, desktop_bridge=None):
        self.lock = threading.Lock()
        self.desktop_bridge = desktop_bridge
        self.printers = store.load()
        self.statuses = {}
        self.temp_history = {}  # pid -> deque of {t, temps}
        self.last_states = {}
        self.printer_hours = {}
        self.spools = []
        self.filaments = []
        self.vendors = []
        self.locations = []
        self.materials = []
        self.spoolman_connected = False
        self.running = True
        self._poll_counter = 0

        # Initial synchronous fast poll for instant startup UI
        self._poll_printers()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def is_sim_enabled(self) -> bool:
        s = S()
        val = s.value("sim_enabled", None)
        if val is None:
            # Enable Demo Fleet automatically if user has no physical printers configured yet
            return len(self.printers) == 0
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("true", "1", "yes")

    def get_effective_printers(self):
        with self.lock:
            real = list(self.printers)
        if self.is_sim_enabled():
            existing_ids = {p.id for p in real}
            for sp in SIM.get_printers():
                if sp.id not in existing_ids:
                    real.append(sp)
        return real

    def reload_printers(self):
        with self.lock:
            self.printers = store.load()
        self._poll_printers()

    def _loop(self):
        while self.running:
            try:
                self._poll_printers()
                if self._poll_counter % 3 == 0:
                    self._poll_spoolman()
                if self._poll_counter % 10 == 0:
                    self._check_auto_dispatch()
                self._poll_counter += 1
            except Exception as e:
                logger.debug("Poll cycle error: %s", e)
            time.sleep(2.2)

    def _poll_printers(self):
        printers_snap = self.get_effective_printers()
        with self.lock:
            eff_spools = list(self.spools) if self.spools else (list(DEMO_SPOOLS) if self.is_sim_enabled() else [])
            spools_map = {int(s["id"]): s for s in eff_spools if "id" in s}

        for p in printers_snap:
            try:
                st = api.fetch(p)
                active_sid = st.get("active_spool_id") or local_printer_spool(p.id)
                st["active_spool"] = spools_map.get(int(active_sid)) if active_sid else None
                st["slot_spools"] = [
                    spools_map.get(int(sid)) if sid else None for sid in (st.get("slot_spool_ids") or [])
                ]

                # Populate flat telemetry fields for React UI compatibility alongside temps list
                temps_list = st.get("temps") or []
                if len(temps_list) >= 1:
                    st.setdefault("nozzle_temp", temps_list[0][1])
                    st.setdefault("nozzle_target", temps_list[0][2])
                if len(temps_list) >= 2:
                    st.setdefault("bed_temp", temps_list[1][1])
                    st.setdefault("bed_target", temps_list[1][2])
                if len(temps_list) >= 3:
                    st.setdefault("chamber_temp", temps_list[2][1])
                st.setdefault("print_duration", st.get("duration"))
                st.setdefault("eta_seconds", st.get("remaining"))
                st.setdefault("current_layer", st.get("layer"))
                st.setdefault("flow_factor", st.get("extrude_factor"))

                # Thumbnail base64
                fname = st.get("filename") or ""
                if fname:
                    raw_thumb = api.job_thumbnail(p, fname)
                    st["thumb_b64"] = (
                        "data:image/png;base64," + base64.b64encode(raw_thumb).decode("ascii")
                        if raw_thumb else None
                    )
                else:
                    st["thumb_b64"] = None

                prev = self.last_states.get(p.id)
                curr = st.get("state")
                if prev and curr and prev != curr:
                    self._check_notification(p, prev, st)
                self.last_states[p.id] = curr

                with self.lock:
                    self.statuses[p.id] = st
                    if p.id not in self.temp_history:
                        self.temp_history[p.id] = deque(maxlen=90)
                    if temps_list:
                        self.temp_history[p.id].append({
                            "t": int(time.time()),
                            "temps": temps_list[:3],
                            "nozzle": temps_list[0][1] if len(temps_list) >= 1 else 0.0,
                            "nozzle_target": temps_list[0][2] if len(temps_list) >= 1 else 0.0,
                            "bed": temps_list[1][1] if len(temps_list) >= 2 else 0.0,
                            "bed_target": temps_list[1][2] if len(temps_list) >= 2 else 0.0,
                        })
            except Exception as e:
                with self.lock:
                    self.statuses[p.id] = {
                        "state": "offline",
                        "error": str(e),
                        "filename": "",
                        "progress": 0.0,
                        "duration": 0.0,
                        "remaining": None,
                        "eta": "",
                        "temps": [],
                        "heaters": [],
                        "position": [0.0, 0.0, 0.0],
                        "z_offset": 0.0,
                        "fan_speed": 0.0,
                        "speed_factor": 1.0,
                        "extrude_factor": 1.0,
                    }

    def _poll_spoolman(self):
        url = spoolman_url()
        if not url and self.printers:
            try:
                real_printers = [p for p in self.printers if not SIM.is_sim_printer(p.id)]
                if real_printers:
                    url = spoolman.discover_url(real_printers)
                    if url:
                        set_spoolman_url(url)
            except Exception:
                pass
        if not url:
            with self.lock:
                self.spoolman_connected = False
            return
        try:
            sp = spoolman.list_spools(url, allow_archived=True)
            fil = spoolman.list_filaments(url)
            ven = spoolman.list_vendors(url)
            loc = spoolman.list_locations(url)
            mat = spoolman.list_materials(url)
            with self.lock:
                self.spools = sp
                self.filaments = fil
                self.vendors = ven
                self.locations = loc
                self.materials = mat
                self.spoolman_connected = True
        except Exception:
            with self.lock:
                self.spoolman_connected = False

    def _check_auto_dispatch(self):
        s = S()
        if not s.value("auto_dispatch", False, type=bool):
            return
        items = load_queue()
        if not items:
            return
        printers = self.get_effective_printers()
        with self.lock:
            statuses = dict(self.statuses)
        for job in list(items):
            pid = job.get("printer_id", "any")
            target_p = None
            if pid != "any":
                cand = next((p for p in printers if p.id == pid), None)
                if cand and statuses.get(cand.id, {}).get("state") == "standby":
                    target_p = cand
            else:
                for p in printers:
                    if statuses.get(p.id, {}).get("state") == "standby":
                        target_p = p
                        break
            if target_p:
                try:
                    fp = job.get("file", "")
                    if Path(fp).is_file():
                        api.upload_gcode(target_p, fp, start_print=True)
                    else:
                        api.start_print(target_p, fp)
                    if job.get("copies", 1) > 1:
                        job["copies"] -= 1
                    else:
                        items = [it for it in items if it.get("id") != job.get("id")]
                    save_queue(items)
                    break
                except Exception:
                    pass

    def _check_notification(self, p, old_state, st):
        new_state = st.get("state")
        fname = st.get("filename") or ""
        msg = None
        if old_state in ("printing", "paused") and new_state in ("complete", "finished"):
            msg = f"Druck abgeschlossen auf {p.name}: {fname}"
        elif new_state == "error":
            msg = f"Fehler bei Drucker {p.name}: {fname}"

        if msg:
            if self.desktop_bridge and hasattr(self.desktop_bridge, "notify_tray"):
                try:
                    self.desktop_bridge.notify_tray(p.name, msg, is_error=(new_state == "error"))
                except Exception:
                    pass
            cfg = notify_cfg()
            if cfg.get("discord") or cfg.get("tg_token"):
                threading.Thread(target=lambda: notify.dispatch(cfg, msg), daemon=True).start()

    def get_state(self):
        s = S()
        sim_on = self.is_sim_enabled()
        eff_printers = self.get_effective_printers()
        with self.lock:
            p_list = [asdict(p) for p in eff_printers]
            for pd in p_list:
                pd["is_sim"] = SIM.is_sim_printer(pd.get("id", ""))
            th = {pid: list(dq) for pid, dq in self.temp_history.items()}
            spools_out = list(self.spools) if self.spools else (list(DEMO_SPOOLS) if sim_on else [])
            filaments_out = list(self.filaments)
            if not filaments_out and sim_on:
                filaments_out = [sp["filament"] for sp in DEMO_SPOOLS if "filament" in sp]
            vendors_out = list(self.vendors)
            if not vendors_out and sim_on:
                vendors_out = [
                    {"id": 101, "name": "Polymaker", "empty_spool_weight": 140.0},
                    {"id": 102, "name": "Bambu Lab", "empty_spool_weight": 250.0},
                    {"id": 103, "name": "Prusa Research", "empty_spool_weight": 200.0},
                    {"id": 104, "name": "eSUN", "empty_spool_weight": 165.0},
                ]
            statuses_out = {pid: st for pid, st in self.statuses.items() if any(p["id"] == pid for p in p_list)}

        detected_slicers = [{"name": lbl, "cmd": cmd[0]} for lbl, cmd in library.detect_slicers()]
        autostart_path = Path.home() / ".config/autostart/printboard.desktop"

        return {
            "mode": str(s.value("ui_mode", "easy")),
            "theme": str(s.value("ui_theme", "obsidian")),
            "controls_enabled": s.value("controls", True, type=bool),
            "sim_enabled": sim_on,
            "auto_dispatch": s.value("auto_dispatch", False, type=bool),
            "autostart": autostart_path.exists(),
            "is_desktop": self.desktop_bridge is not None,
            "printers": p_list,
            "statuses": statuses_out,
            "temp_history": th,
            "spools": spools_out,
            "filaments": filaments_out,
            "vendors": vendors_out,
            "locations": self.locations or ["Drybox A1", "AMS Slot 1", "AMS Slot 2", "Regal B2"],
            "materials": self.materials or ["PLA", "PLA+", "PETG", "ABS", "ASA", "TPU", "PA-CF", "PC"],
            "spoolman_url": spoolman_url(),
            "spoolman_connected": self.spoolman_connected,
            "drying_presets": DRYING_PRESETS,
            "drying_timers": load_drying_timers(),
            "queue": load_queue(),
            "maintenance": load_maint(),
            "maintenance_tasks": load_all_maint_tasks(),
            "printer_hours": dict(self.printer_hours),
            "models_dir": models_dir(),
            "slicer_cmd": slicer_cmd(),
            "detected_slicers": detected_slicers,
            "notify_cfg": notify_cfg(),
            "cost_rates": {
                "eur_kg": float(s.value("eur_kg", 24.0)),
                "kwh": float(s.value("kwh", 0.30)),
                "watts": float(s.value("watts", 150.0)),
                "wear": float(s.value("wear", 0.15)),
                "labor_h": float(s.value("labor_h", 25.0)),
                "margin_pct": float(s.value("margin_pct", 35.0)),
                "fail_pct": float(s.value("fail_pct", 8.0)),
                "vat_pct": float(s.value("vat_pct", 19.0)),
            },
        }


class PrintBoardApiHandler(SimpleHTTPRequestHandler):
    engine: ServerEngine = None

    def log_message(self, format, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        super().end_headers()

    def _send_json(self, data, code=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _find_printer(self, pid):
        for p in self.engine.get_effective_printers():
            if p.id == pid:
                return p
        return None

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path in ("/api/status", "/api/state"):
            return self._send_json(self.engine.get_state())

        if path == "/api/printer/details":
            pid = (qs.get("printer_id") or [""])[0]
            p = self._find_printer(pid)
            if not p:
                return self._send_json({"files": [], "macros": [], "console": []})
            is_bambu = getattr(p, "printer_type", "moonraker") == "bambu" and not SIM.is_sim_printer(p.id)
            files_list, macros_list, console_list = [], [], []
            if not is_bambu:
                try:
                    files_list = api.remote_files(p)
                except Exception:
                    pass
                try:
                    macros_list = api.macros(p)
                except Exception:
                    pass
                try:
                    console_list = api.gcode_store(p, 100)
                except Exception:
                    pass
            return self._send_json({
                "files": files_list,
                "macros": macros_list,
                "console": console_list,
            })

        if path == "/api/files":
            pid = (qs.get("printer_id") or [""])[0]
            p = self._find_printer(pid)
            if not p:
                return self._send_json({"files": []})
            try:
                files_list = api.remote_files(p) if getattr(p, "printer_type", "moonraker") != "bambu" or SIM.is_sim_printer(p.id) else []
                return self._send_json({"files": files_list})
            except Exception as e:
                return self._send_json({"files": [], "error": str(e)})

        if path == "/api/webcams":
            printers = self.engine.get_effective_printers()
            cams = api.all_webcams(printers)
            return self._send_json({"cams": cams})

        if path == "/api/printers/discover":
            try:
                found = api.discover_printers()
                return self._send_json({"found": found})
            except Exception as e:
                return self._send_json({"found": [], "error": str(e)})

        if path == "/api/models/search":
            q = (qs.get("q") or qs.get("query") or [""])[0]
            site = (qs.get("site") or ["all"])[0]
            sort = (qs.get("sort") or ["popular"])[0]
            try:
                res = model_search.search_models(query=q, site=site, sort=sort)
                return self._send_json(res)
            except Exception as e:
                return self._send_json({"ok": False, "error": str(e), "items": []}, 500)

        if path == "/api/library/list":
            q = (qs.get("query") or [""])[0]
            cat = (qs.get("category") or ["all"])[0]
            sub = (qs.get("subfolder") or [""])[0]
            root = models_dir()
            files_out = []
            for f in library.scan(root, q, category=cat, subfolder=sub)[:300]:
                try:
                    det = library.file_details(f)
                    try:
                        rel_dir = str(f.parent.relative_to(root))
                    except ValueError:
                        rel_dir = ""
                    det["subfolder"] = "" if rel_dir == "." else rel_dir
                    det["thumb_b64"] = library.thumbnail_b64(f)
                    files_out.append(det)
                except Exception:
                    pass
            return self._send_json({
                "models_dir": root,
                "subfolders": library.list_subfolders(root),
                "files": files_out,
            })

        if path == "/api/gcode/analyze":
            fp = (qs.get("path") or [""])[0]
            pid = (qs.get("printer_id") or [""])[0]
            fname = (qs.get("filename") or [""])[0]
            if fp and Path(fp).is_file():
                return self._send_json(library.analyze_gcode_layers(fp))
            if pid and fname:
                p = self._find_printer(pid)
                if p and not SIM.is_sim_printer(p.id) and getattr(p, "printer_type", "moonraker") != "bambu":
                    try:
                        dl_path = api.download_remote_file(p, fname, models_dir())
                        return self._send_json(library.analyze_gcode_layers(dl_path))
                    except Exception:
                        pass
                return self._send_json(library.generate_demo_gcode_layers(fname))
            return self._send_json(library.generate_demo_gcode_layers(fname or "Voron_Stealthburner_Mount_Set_ABS.gcode"))

        if path == "/api/history":
            printers = self.engine.get_effective_printers()
            s = S()
            eur_kg = float(s.value("eur_kg", 24.0))
            kwh_price = float(s.value("kwh", 0.30))
            watts = float(s.value("watts", 150.0))
            wear = float(s.value("wear", 0.15))
            all_jobs = []
            by_printer = {}
            for p in printers:
                if getattr(p, "printer_type", "moonraker") == "bambu" and not SIM.is_sim_printer(p.id):
                    continue
                try:
                    jobs = api.history(p, limit=200)
                    st = costs.stats(jobs, eur_kg, kwh_price, watts, wear)
                    self.engine.printer_hours[p.id] = float(st.get("hours") or 0.0)
                    by_printer[p.id] = {"name": p.name, "stats": st, "jobs": jobs[:50]}
                    for j in jobs:
                        jc = dict(j)
                        jc["printer_name"] = p.name
                        jc["printer_id"] = p.id
                        g = costs.mm_to_g(jc.get("filament_used"))
                        sec = jc.get("total_duration") or 0
                        jc["grams"] = round(g, 1)
                        jc["hours"] = round(sec / 3600.0, 2)
                        jc["cost_eur"] = round(costs.job_cost(g, sec, eur_kg, watts, kwh_price, wear), 2)
                        all_jobs.append(jc)
                except Exception:
                    pass
            total_stats = costs.stats(all_jobs, eur_kg, kwh_price, watts, wear)
            return self._send_json({
                "total": total_stats,
                "by_printer": by_printer,
                "jobs": sorted(all_jobs, key=lambda x: x.get("start_time") or 0, reverse=True)[:100],
                "rates": {"eur_kg": eur_kg, "kwh": kwh_price, "watts": watts, "wear": wear},
            })

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(body.decode("utf-8", errors="ignore"))
        except Exception:
            payload = {}

        # 1. UI Mode / Theme / Simulation Toggle
        if path == "/api/mode":
            s = S()
            if "mode" in payload and payload["mode"] in ("easy", "advanced"):
                s.setValue("ui_mode", payload["mode"])
            if "theme" in payload:
                s.setValue("ui_theme", payload["theme"])
            if "sim_enabled" in payload:
                s.setValue("sim_enabled", bool(payload["sim_enabled"]))
                self.engine._poll_printers()
            if "controls_enabled" in payload:
                s.setValue("controls", bool(payload["controls_enabled"]))
            if "auto_dispatch" in payload:
                s.setValue("auto_dispatch", bool(payload["auto_dispatch"]))
            return self._send_json({"ok": True, "state": self.engine.get_state()})

        # 2. Printer Control & Fleet Batch Actions
        if path == "/api/control":
            pid = payload.get("printer_id")
            batch_target = payload.get("batch")  # "all_idle", "all_printing", "all"
            action = payload.get("action")
            params = payload.get("params") or {}

            targets = []
            if batch_target:
                eff = self.engine.get_effective_printers()
                with self.engine.lock:
                    sts = dict(self.engine.statuses)
                for p in eff:
                    st_name = sts.get(p.id, {}).get("state", "offline")
                    if batch_target == "all" and st_name != "offline":
                        targets.append(p)
                    elif batch_target == "all_idle" and st_name in ("standby", "complete", "cancelled"):
                        targets.append(p)
                    elif batch_target == "all_printing" and st_name in ("printing", "paused"):
                        targets.append(p)
            else:
                tp = self._find_printer(pid)
                if tp:
                    targets.append(tp)

            if not targets:
                return self._send_json({"error": "Kein passender Drucker gefunden."}, 404)

            results = []
            errors = []
            for target_printer in targets:
                try:
                    if action == "preheat":
                        nozzle = float(payload.get("nozzle", params.get("nozzle", 0)))
                        bed = float(payload.get("bed", params.get("bed", 0)))
                        api.set_temp(target_printer, "extruder", nozzle)
                        res = api.set_temp(target_printer, "heater_bed", bed)
                    elif action == "gcode":
                        res = api.gcode(target_printer, payload.get("script") or params.get("script", ""))
                    elif action == "temp":
                        res = api.set_temp(
                            target_printer,
                            payload.get("heater") or params.get("heater", "extruder"),
                            float(payload.get("target", params.get("target", 0))),
                        )
                    elif action == "fan":
                        res = api.set_fan(target_printer, int(payload.get("percent", params.get("percent", 0))))
                    elif action == "speed":
                        res = api.set_speed(
                            target_printer,
                            int(payload.get("percent", params.get("percent", 100))),
                            level=payload.get("level", params.get("level")),
                        )
                    elif action == "flow":
                        res = api.set_flow(target_printer, int(payload.get("percent", params.get("percent", 100))))
                    elif action == "jog":
                        if "axis" in payload or "axis" in params:
                            res = api.control(
                                target_printer,
                                "jog",
                                axis=payload.get("axis") or params.get("axis"),
                                dist=float(payload.get("dist", params.get("dist", 0))),
                                speed=int(payload.get("speed", params.get("speed", 3000))),
                            )
                        else:
                            res = api.jog(
                                target_printer,
                                dx=float(payload.get("dx", 0)),
                                dy=float(payload.get("dy", 0)),
                                dz=float(payload.get("dz", 0)),
                                de=float(payload.get("de", 0)),
                            )
                    elif action == "start_file":
                        res = api.start_print(target_printer, payload.get("filename") or params.get("filename", ""))
                    elif action == "delete_file":
                        res = api.delete_remote_file(target_printer, payload.get("filename") or params.get("filename", ""))
                    else:
                        merged_kw = {k: v for k, v in payload.items() if k not in ("printer_id", "batch", "action", "params")}
                        merged_kw.update(params)
                        res = api.control(target_printer, action, **merged_kw)
                    results.append(res)
                except Exception as e:
                    errors.append(f"{target_printer.name}: {e}")

            self.engine._poll_printers()
            if errors and not results:
                return self._send_json({"error": "; ".join(errors)}, 500)
            return self._send_json({"ok": True, "results": results, "errors": errors})

        # 3. Printer CRUD & Connection Test
        if path == "/api/printers/add":
            printers = store.load()
            pid = payload.get("id") or uuid.uuid4().hex[:8]
            host = str(payload.get("host", "")).strip().replace("http://", "").replace("https://", "").rstrip("/")
            if not host:
                return self._send_json({"error": "Bitte IP-Adresse oder Hostname angeben."}, 400)
            p_obj = store.Printer(
                name=str(payload.get("name") or host).strip(),
                host=host,
                port=int(payload.get("port") or (8883 if payload.get("printer_type") == "bambu" else 80)),
                token=str(payload.get("token") or "").strip(),
                tls=bool(payload.get("tls", False)),
                id=pid,
                display_url=str(payload.get("display_url") or "").strip(),
                printer_type=str(payload.get("printer_type") or "moonraker"),
                bambu_serial=str(payload.get("bambu_serial") or "").strip(),
                bambu_access_code=str(payload.get("bambu_access_code") or "").strip(),
            )
            existing_idx = next((i for i, x in enumerate(printers) if x.id == pid), -1)
            if existing_idx >= 0:
                printers[existing_idx] = p_obj
            else:
                printers.append(p_obj)
            store.save(printers)
            self.engine.reload_printers()
            return self._send_json({"ok": True, "printer": asdict(p_obj)})

        if path == "/api/printers/delete":
            pid = payload.get("id")
            printers = [p for p in store.load() if p.id != pid]
            store.save(printers)
            self.engine.reload_printers()
            return self._send_json({"ok": True})

        if path == "/api/printers/test":
            host = str(payload.get("host", "")).strip().replace("http://", "").replace("https://", "").rstrip("/")
            p_obj = store.Printer(
                name=str(payload.get("name") or host).strip(),
                host=host,
                port=int(payload.get("port") or 80),
                token=str(payload.get("token") or "").strip(),
                tls=bool(payload.get("tls", False)),
                printer_type=str(payload.get("printer_type") or "moonraker"),
                bambu_serial=str(payload.get("bambu_serial") or "").strip(),
                bambu_access_code=str(payload.get("bambu_access_code") or "").strip(),
            )
            try:
                st = api.fetch(p_obj)
                if st.get("state") == "offline":
                    return self._send_json({"ok": False, "error": "Drucker antwortet nicht (Offline)."}, 400)
                return self._send_json({
                    "ok": True,
                    "message": f"Verbunden ({st.get('klipper', 'OK')}) — Status: {st.get('state')} — {len(st.get('temps', []))} Sensoren",
                })
            except Exception as e:
                return self._send_json({"ok": False, "error": str(e)}, 400)

        if path == "/api/printers/save":
            printers_data = payload.get("printers", [])
            new_list = []
            for d in printers_data:
                if SIM.is_sim_printer(d.get("id", "")):
                    continue
                p_kwargs = {
                    "name": d.get("name", "Drucker"),
                    "host": d.get("host", ""),
                    "port": int(d.get("port", 80)),
                    "token": d.get("token", ""),
                    "tls": bool(d.get("tls", False)),
                    "id": d.get("id") or uuid.uuid4().hex[:8],
                    "display_url": d.get("display_url", ""),
                    "printer_type": d.get("printer_type", "moonraker"),
                    "bambu_serial": d.get("bambu_serial", ""),
                    "bambu_access_code": d.get("bambu_access_code", ""),
                }
                new_list.append(store.Printer(**p_kwargs))
            store.save(new_list)
            self.engine.reload_printers()
            return self._send_json({"ok": True})

        # 4. 3D Library Actions
        if path == "/api/library/action":
            act = payload.get("action")
            fpath = payload.get("path", "")
            try:
                if act in ("open_slicer", "slice"):
                    used = library.open_in_slicer(fpath, slicer_cmd())
                    return self._send_json({"ok": True, "slicer": used})
                if act == "upload_to_printer":
                    p = self._find_printer(payload.get("printer_id"))
                    if not p:
                        return self._send_json({"error": "Drucker nicht gefunden"}, 404)
                    start_now = bool(payload.get("start", False))
                    api.upload(p, fpath, start=start_now)
                    self.engine._poll_printers()
                    return self._send_json({"ok": True})
                if act == "download_from_printer":
                    p = self._find_printer(payload.get("printer_id"))
                    fname = payload.get("filename", "")
                    if not p or not fname:
                        return self._send_json({"error": "Drucker oder Dateiname fehlt"}, 400)
                    saved = api.download_remote_file(p, fname, models_dir())
                    return self._send_json({"ok": True, "path": str(saved)})
                if act == "unzip":
                    out_dir, extracted = library.extract_zip(fpath)
                    return self._send_json({"ok": True, "folder": out_dir.name, "count": len(extracted)})
                if act == "rename":
                    target = library.rename_file(fpath, payload.get("new_name", ""))
                    return self._send_json({"ok": True, "path": str(target)})
                if act == "duplicate":
                    target = library.duplicate_file(fpath)
                    return self._send_json({"ok": True, "path": str(target)})
                if act == "move":
                    sub = payload.get("subfolder", "").strip()
                    dest = Path(models_dir()) / sub if sub else Path(models_dir())
                    target = library.move_file(fpath, dest)
                    return self._send_json({"ok": True, "path": str(target)})
                if act == "delete":
                    library.delete_file(fpath)
                    return self._send_json({"ok": True})
                if act == "create_subfolder":
                    name = payload.get("name", "").strip().strip("/\\")
                    if not name:
                        return self._send_json({"error": "Ordnername fehlt"}, 400)
                    (Path(models_dir()) / name).mkdir(parents=True, exist_ok=True)
                    return self._send_json({"ok": True})
                return self._send_json({"error": f"Unbekannte Aktion: {act}"}, 400)
            except Exception as e:
                return self._send_json({"error": str(e)}, 500)

        # 5. Print Queue Management & Dispatch
        if path == "/api/queue/add":
            items = load_queue()
            fp = payload.get("file", "").strip()
            if not fp:
                return self._send_json({"error": "Datei erforderlich"}, 400)
            items.append({
                "id": f"q_{int(time.time() * 1000)}",
                "file": fp,
                "name": Path(fp).name,
                "printer_id": payload.get("printer_id") or "any",
                "printer_label": payload.get("printer_label") or "Beliebiger freier Drucker",
                "copies": max(1, int(payload.get("copies") or 1)),
                "material": payload.get("material") or "PLA",
                "priority": payload.get("priority") or "Normal",
                "notes": payload.get("notes") or "",
                "added_at": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
            })
            save_queue(items)
            return self._send_json({"ok": True, "queue": items})

        if path == "/api/queue/remove":
            items = load_queue()
            qid = payload.get("id")
            items = [it for it in items if it.get("id") != qid]
            save_queue(items)
            return self._send_json({"ok": True, "queue": items})

        if path == "/api/queue/move":
            items = load_queue()
            qid = payload.get("id")
            direction = int(payload.get("dir", -1))
            idx = next((i for i, it in enumerate(items) if it.get("id") == qid), -1)
            if 0 <= idx < len(items):
                new_idx = max(0, min(len(items) - 1, idx + direction))
                item = items.pop(idx)
                items.insert(new_idx, item)
                save_queue(items)
            return self._send_json({"ok": True, "queue": items})

        if path == "/api/queue/dispatch":
            items = load_queue()
            qid = payload.get("id")
            job = next((it for it in items if it.get("id") == qid), items[0] if items else None)
            if not job:
                return self._send_json({"error": "Warteschlange ist leer"}, 400)
            printers = self.engine.get_effective_printers()
            with self.engine.lock:
                statuses = dict(self.engine.statuses)
            target_p = None
            pid = payload.get("target_printer_id") or job.get("printer_id", "any")
            if pid != "any":
                target_p = next((p for p in printers if p.id == pid), None)
            if not target_p:
                for p in printers:
                    if statuses.get(p.id, {}).get("state") in ("standby", "complete", "cancelled"):
                        target_p = p
                        break
                if not target_p and printers:
                    target_p = printers[0]
            if not target_p:
                return self._send_json({"error": "Kein freier Drucker verfügbar"}, 400)
            try:
                fp = job.get("file", "")
                if Path(fp).is_file():
                    api.upload_gcode(target_p, fp, start_print=True)
                else:
                    api.start_print(target_p, fp)
                if job.get("copies", 1) > 1:
                    job["copies"] -= 1
                else:
                    items = [it for it in items if it.get("id") != job.get("id")]
                save_queue(items)
                self.engine._poll_printers()
                return self._send_json({"ok": True, "printer": target_p.name, "queue": items})
            except Exception as e:
                return self._send_json({"error": str(e)}, 500)

        # 6. Maintenance Tracker & Custom Intervals
        if path == "/api/maintenance/reset":
            pid = payload.get("printer_id")
            key = payload.get("key")
            hours = float(payload.get("hours") or 0.0)
            data = load_maint()
            if pid not in data:
                data[pid] = {}
            data[pid][key] = {
                "reset_at_hours": hours,
                "last_date": datetime.datetime.now().strftime("%d.%m.%Y"),
                "notes": payload.get("notes", ""),
            }
            save_maint(data)
            return self._send_json({"ok": True, "maintenance": data})

        if path == "/api/maintenance/add_task":
            title = str(payload.get("title", "")).strip()
            interval_h = float(payload.get("interval_h") or 100.0)
            if not title:
                return self._send_json({"error": "Titel erforderlich"}, 400)
            try:
                custom = json.loads(CUSTOM_MAINT_FILE.read_text())
            except Exception:
                custom = []
            custom.append({
                "key": f"custom_{int(time.time() * 1000)}",
                "title": title,
                "interval_h": interval_h,
                "builtin": False,
            })
            save_custom_maint_tasks(custom)
            return self._send_json({"ok": True, "tasks": load_all_maint_tasks()})

        if path == "/api/maintenance/delete_task":
            key = payload.get("key")
            try:
                custom = json.loads(CUSTOM_MAINT_FILE.read_text())
            except Exception:
                custom = []
            custom = [t for t in custom if t.get("key") != key]
            save_custom_maint_tasks(custom)
            return self._send_json({"ok": True, "tasks": load_all_maint_tasks()})

        # 7. Costs & Quote Calculator
        if path == "/api/costs/save":
            s = S()
            for k in ("eur_kg", "kwh", "watts", "wear", "labor_h", "margin_pct", "fail_pct", "vat_pct"):
                if k in payload:
                    s.setValue(k, float(payload[k]))
            return self._send_json({"ok": True})

        if path == "/api/costs/quote":
            res = costs.calculate_quote(
                grams=float(payload.get("grams", 50.0)),
                hours=float(payload.get("hours", 2.0)),
                eur_per_kg=float(payload.get("eur_kg", 24.0)),
                watts=float(payload.get("watts", 150.0)),
                eur_per_kwh=float(payload.get("kwh", 0.30)),
                wear_per_h=float(payload.get("wear", 0.15)),
                prep_mins=float(payload.get("prep_mins", 10.0)),
                labor_eur_h=float(payload.get("labor_h", 25.0)),
                waste_pct=float(payload.get("waste_pct", 5.0)),
                fail_risk_pct=float(payload.get("fail_pct", 8.0)),
                margin_pct=float(payload.get("margin_pct", 35.0)),
                vat_pct=float(payload.get("vat_pct", 19.0)),
                copies=int(payload.get("copies", 1)),
            )
            return self._send_json({
                "ok": True,
                "quote": res,
                **res,
                "base_cost": res["production_cost_eur"],
                "net_price": res["net_price_eur"],
                "gross_price": res["gross_price_eur"],
            })

        # 8. Spoolman & Filament Drying Suite
        if path == "/api/spoolman/save":
            if "url" in payload:
                set_spoolman_url(payload["url"])
                self.engine._poll_spoolman()
            return self._send_json({"ok": True, "spoolman_url": spoolman_url()})

        if path == "/api/spoolman/discover":
            real_p = [p for p in self.engine.printers if not SIM.is_sim_printer(p.id)]
            found_url = spoolman.discover_url(real_p)
            if found_url:
                set_spoolman_url(found_url)
                self.engine._poll_spoolman()
                return self._send_json({"ok": True, "url": found_url})
            return self._send_json({"ok": False, "error": "Kein Spoolman-Server automatisch gefunden."})

        if path == "/api/spoolman/test":
            url = spoolman.normalize_url(payload.get("url") or spoolman_url())
            info = spoolman.probe_spoolman(url)
            if info:
                return self._send_json({"ok": True, "info": info})
            return self._send_json({"ok": False, "error": f"Spoolman unter {url} nicht erreichbar."}, 400)

        if path == "/api/spoolman/assign":
            pid = payload.get("printer_id")
            sid = payload.get("spool_id")
            channel = payload.get("channel")
            sid_int = int(sid) if sid else None
            p = self._find_printer(pid)
            set_local_printer_spool(pid, sid_int)
            if p and SIM.is_sim_printer(p.id):
                with SIM._lock:
                    if p.id in SIM._states:
                        SIM._states[p.id]["active_spool_id"] = sid_int
            elif p and getattr(p, "printer_type", "moonraker") != "bambu":
                try:
                    spoolman.assign_spool_to_printer(p, sid_int, channel=channel)
                except Exception:
                    pass
            self.engine._poll_printers()
            return self._send_json({"ok": True})

        if path == "/api/spoolman/use":
            url = spoolman_url()
            sid = int(payload.get("spool_id"))
            grams = float(payload.get("grams", 0))
            if not url:
                # Update demo spool in memory if using demo mode
                for sp in DEMO_SPOOLS:
                    if sp["id"] == sid:
                        sp["remaining_weight"] = max(0.0, sp["remaining_weight"] - grams)
                        sp["used_weight"] = sp.get("used_weight", 0.0) + grams
                return self._send_json({"ok": True})
            try:
                spoolman.use_spool(url, sid, use_weight=grams)
                self.engine._poll_spoolman()
                return self._send_json({"ok": True})
            except Exception as e:
                return self._send_json({"error": str(e)}, 500)

        if path == "/api/spoolman/measure":
            url = spoolman_url()
            sid = int(payload.get("spool_id"))
            gross_g = float(payload.get("weight", 0))
            if not url:
                for sp in DEMO_SPOOLS:
                    if sp["id"] == sid:
                        tare = float((sp.get("filament") or {}).get("spool_weight") or 200.0)
                        sp["remaining_weight"] = max(0.0, gross_g - tare)
                return self._send_json({"ok": True})
            try:
                spoolman.measure_spool(url, sid, gross_g)
                self.engine._poll_spoolman()
                return self._send_json({"ok": True})
            except Exception as e:
                return self._send_json({"error": str(e)}, 500)

        if path == "/api/spoolman/spool/create":
            url = spoolman_url()
            if not url:
                new_id = max([s["id"] for s in DEMO_SPOOLS] + [900]) + 1
                fil_id = int(payload.get("filament_id") or 501)
                fil_obj = next((s["filament"] for s in DEMO_SPOOLS if s["filament"]["id"] == fil_id), DEMO_SPOOLS[0]["filament"])
                DEMO_SPOOLS.append({
                    "id": new_id,
                    "filament": fil_obj,
                    "price": float(payload.get("price") or 24.90),
                    "initial_weight": float(payload.get("initial_weight") or 1000.0),
                    "remaining_weight": float(payload.get("remaining_weight") or 1000.0),
                    "used_weight": 0.0,
                    "location": payload.get("location") or "Regal",
                    "archived": False,
                    "extra": {},
                })
                return self._send_json({"ok": True})
            try:
                spoolman.create_spool(url, payload)
                self.engine._poll_spoolman()
                return self._send_json({"ok": True})
            except Exception as e:
                return self._send_json({"error": str(e)}, 500)

        if path == "/api/spoolman/spool/delete":
            url = spoolman_url()
            sid = int(payload.get("id"))
            if not url:
                DEMO_SPOOLS[:] = [s for s in DEMO_SPOOLS if s["id"] != sid]
                return self._send_json({"ok": True})
            try:
                spoolman.delete_spool(url, sid)
                self.engine._poll_spoolman()
                return self._send_json({"ok": True})
            except Exception as e:
                return self._send_json({"error": str(e)}, 500)

        if path == "/api/spoolman/filament/create":
            url = spoolman_url()
            if not url:
                new_fid = max([s["filament"]["id"] for s in DEMO_SPOOLS] + [500]) + 1
                new_fil = {
                    "id": new_fid,
                    "name": payload.get("name") or "Custom Filament",
                    "material": payload.get("material") or "PLA",
                    "color_hex": str(payload.get("color_hex") or "06B6D4").lstrip("#"),
                    "weight": float(payload.get("weight") or 1000.0),
                    "spool_weight": float(payload.get("spool_weight") or 200.0),
                    "density": float(payload.get("density") or 1.24),
                    "diameter": float(payload.get("diameter") or 1.75),
                    "price": float(payload.get("price") or 22.0),
                    "settings_extruder_temp": int(payload.get("settings_extruder_temp") or 215),
                    "settings_bed_temp": int(payload.get("settings_bed_temp") or 60),
                    "vendor": {"id": 101, "name": payload.get("vendor_name") or "Hersteller"},
                }
                DEMO_SPOOLS.append({
                    "id": max([s["id"] for s in DEMO_SPOOLS] + [900]) + 1,
                    "filament": new_fil,
                    "price": new_fil["price"],
                    "initial_weight": new_fil["weight"],
                    "remaining_weight": new_fil["weight"],
                    "used_weight": 0.0,
                    "location": "Lager",
                    "archived": False,
                    "extra": {},
                })
                return self._send_json({"ok": True})
            try:
                spoolman.create_filament(url, payload)
                self.engine._poll_spoolman()
                return self._send_json({"ok": True})
            except Exception as e:
                return self._send_json({"error": str(e)}, 500)

        if path == "/api/spoolman/drying/start":
            timers = load_drying_timers()
            timers.append({
                "id": f"dry_{int(time.time() * 1000)}",
                "spool_label": payload.get("spool_label") or "Spule",
                "material": payload.get("material") or "PETG",
                "temp_c": int(payload.get("temp_c") or 65),
                "duration_h": float(payload.get("duration_h") or 6.0),
                "started_at": int(time.time()),
                "ends_at": int(time.time() + float(payload.get("duration_h") or 6.0) * 3600),
            })
            save_drying_timers(timers)
            return self._send_json({"ok": True, "drying_timers": timers})

        if path == "/api/spoolman/drying/stop":
            timers = [t for t in load_drying_timers() if t.get("id") != payload.get("id")]
            save_drying_timers(timers)
            return self._send_json({"ok": True, "drying_timers": timers})

        # 9. Settings & Notifications
        if path == "/api/settings/save":
            s = S()
            if "models_dir" in payload and str(payload["models_dir"]).strip():
                d = str(payload["models_dir"]).strip()
                Path(d).mkdir(parents=True, exist_ok=True)
                s.setValue("models", d)
            if "slicer_cmd" in payload:
                s.setValue("slicer_cmd", str(payload["slicer_cmd"]).strip())
            if "spoolman_url" in payload:
                set_spoolman_url(str(payload["spoolman_url"]).strip())
                self.engine._poll_spoolman()
            if "controls" in payload:
                s.setValue("controls", bool(payload["controls"]))
            if "sim_enabled" in payload:
                s.setValue("sim_enabled", bool(payload["sim_enabled"]))
                self.engine._poll_printers()
            if "autostart" in payload:
                f = Path.home() / ".config/autostart/printboard.desktop"
                if payload["autostart"]:
                    f.parent.mkdir(parents=True, exist_ok=True)
                    f.write_text("[Desktop Entry]\nType=Application\nName=PrintBoard\nExec=printboard\nX-GNOME-Autostart-enabled=true\n")
                elif f.exists():
                    f.unlink()
            if "discord" in payload:
                s.setValue("discord", str(payload["discord"]).strip())
            if "tg_token" in payload:
                s.setValue("tg_token", str(payload["tg_token"]).strip())
            if "tg_chat" in payload:
                s.setValue("tg_chat", str(payload["tg_chat"]).strip())
            return self._send_json({"ok": True})

        if path == "/api/notify/test":
            url = payload.get("discord", "").strip()
            if not url:
                return self._send_json({"error": "Keine Discord Webhook-URL angegeben"}, 400)
            try:
                notify.send_discord(url, "**PrintBoard Studio**: Webhook-Verbindung erfolgreich getestet!")
                return self._send_json({"ok": True})
            except Exception as e:
                return self._send_json({"error": str(e)}, 500)

        if path == "/api/notify/save":
            s = S()
            if "discord" in payload:
                s.setValue("discord", payload["discord"])
            if "tg_token" in payload:
                s.setValue("tg_token", payload["tg_token"])
            if "tg_chat" in payload:
                s.setValue("tg_chat", payload["tg_chat"])
            return self._send_json({"ok": True})

        # 10. Native Desktop Bridge Actions (File Dialogs, Model Browser, Folder Reveal)
        if path == "/api/desktop/action":
            bridge = self.engine.desktop_bridge
            if not bridge:
                return self._send_json({"error": "Nur in der Desktop-Anwendung verfügbar."}, 400)
            act = payload.get("action")
            try:
                if hasattr(bridge, "invoke"):
                    res = bridge.invoke(act, payload)
                else:
                    res = bridge(payload)
                return self._send_json({"ok": True, "result": res})
            except Exception as e:
                return self._send_json({"error": str(e)}, 500)

        self._send_json({"error": "Endpoint not found"}, 404)


def create_http_server(port=8080, host="0.0.0.0", web_dir=None, desktop_bridge=None):
    if web_dir is None:
        web_dir = Path(__file__).parent / "web"
    web_dir.mkdir(parents=True, exist_ok=True)

    engine = ServerEngine(desktop_bridge=desktop_bridge)

    class CustomHandler(PrintBoardApiHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(web_dir), **kwargs)

    CustomHandler.engine = engine
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer((host, int(port)), CustomHandler)
    server.engine = engine
    return server, engine


def run_server(port=8080, host="0.0.0.0", web_dir=None):
    server, engine = create_http_server(port=port, host=host, web_dir=web_dir)
    actual_port = server.server_port
    logger.info("PrintBoard Server listening on http://%s:%d", host, actual_port)
    print(f"PrintBoard Studio Server läuft auf http://{host}:{actual_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        engine.running = False


if __name__ == "__main__":
    run_server()
