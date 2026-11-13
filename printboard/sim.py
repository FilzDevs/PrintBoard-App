"""Interactive Virtual Demo Fleet & Telemetry Simulator for PrintBoard.
Provides realistic simulated Klipper (Voron 2.4, RatRig V-Core 4) and Bambu Lab (X1 Carbon AMS)
printers with live thermal physics, moving toolhead coordinates, 2D/3D bed mesh matrices,
exclude_object build-plate polygons, and G-code console logs when Demo Mode is enabled.
"""
import base64
import math
import threading
import time
from typing import Dict, List

from .store import Printer

# Crisp embedded PNG thumbnail (64x64 stylised 3D model preview)
_DEMO_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAACXBIWXMAAAsTAAALEwEAmpwYAAAA"
    "mklEQVR4nO2WwQ3AIAwD7Z9OJ+vA6sDq6M7o6C5MSJFAIVW6V76T2I7tJ0AgEAgEAoFA8A3g"
    "Ambu3t2Z2VlV1R2AiL4t4JyZ2b26qir3D3h279XdAcx8C2Bm7l5Vldk5gIjuAczMrKrK3O8B"
    "3L2qKrN/W8ATgJk5gH8LeAIws2sLOOc+gJk5M3N2PgE451BVlZm5BwgEAoFAIBAIfokX9l4Y"
    "8W6+0PAAAAAASUVORK5CYII="
)
DEMO_THUMB_BYTES = base64.b64decode(_DEMO_PNG_B64)

DEMO_PRINTERS = [
    Printer(
        name="Voron 2.4 R2 Pro",
        host="voron24.local",
        port=7125,
        id="sim_voron24",
        printer_type="moonraker",
    ),
    Printer(
        name="Bambu Lab X1 Carbon",
        host="192.168.178.201",
        port=8883,
        id="sim_bambux1c",
        printer_type="bambu",
        bambu_serial="00M09A3A010042",
        bambu_access_code="88412099",
    ),
    Printer(
        name="RatRig V-Core 4 400",
        host="vcore4.local",
        port=7125,
        id="sim_vcore4",
        printer_type="moonraker",
    ),
]

DEMO_SPOOLS = [
    {
        "id": 901,
        "filament": {
            "id": 501,
            "name": "PolyLite ABS Jet Black",
            "material": "ABS",
            "color_hex": "1E293B",
            "weight": 1000.0,
            "spool_weight": 140.0,
            "density": 1.04,
            "diameter": 1.75,
            "price": 24.90,
            "settings_extruder_temp": 255,
            "settings_bed_temp": 105,
            "vendor": {"id": 101, "name": "Polymaker"},
        },
        "price": 24.90,
        "initial_weight": 1000.0,
        "remaining_weight": 642.0,
        "used_weight": 358.0,
        "location": "Drybox A1",
        "archived": False,
        "extra": {"card_uids": '"04A19B3FE22A80"'},
    },
    {
        "id": 902,
        "filament": {
            "id": 502,
            "name": "PLA Basic Cyan Tough",
            "material": "PLA",
            "color_hex": "06B6D4",
            "weight": 1000.0,
            "spool_weight": 250.0,
            "density": 1.24,
            "diameter": 1.75,
            "price": 21.99,
            "settings_extruder_temp": 220,
            "settings_bed_temp": 60,
            "vendor": {"id": 102, "name": "Bambu Lab"},
        },
        "price": 21.99,
        "initial_weight": 1000.0,
        "remaining_weight": 785.0,
        "used_weight": 215.0,
        "location": "AMS Slot 1",
        "archived": False,
        "extra": {},
    },
    {
        "id": 903,
        "filament": {
            "id": 503,
            "name": "Prusament PETG Signal Orange",
            "material": "PETG",
            "color_hex": "F97316",
            "weight": 1000.0,
            "spool_weight": 200.0,
            "density": 1.27,
            "diameter": 1.75,
            "price": 29.99,
            "settings_extruder_temp": 240,
            "settings_bed_temp": 80,
            "vendor": {"id": 103, "name": "Prusa Research"},
        },
        "price": 29.99,
        "initial_weight": 1000.0,
        "remaining_weight": 118.0,  # Low filament warning demo!
        "used_weight": 882.0,
        "location": "AMS Slot 2",
        "archived": False,
        "extra": {},
    },
    {
        "id": 904,
        "filament": {
            "id": 504,
            "name": "eSUN PLA+ Silk Dual Violet/Gold",
            "material": "PLA+",
            "color_hex": "8B5CF6",
            "multi_color_hexes": "8B5CF6,F59E0B",
            "weight": 1000.0,
            "spool_weight": 165.0,
            "density": 1.24,
            "diameter": 1.75,
            "price": 23.50,
            "settings_extruder_temp": 215,
            "settings_bed_temp": 60,
            "vendor": {"id": 104, "name": "eSUN"},
        },
        "price": 23.50,
        "initial_weight": 1000.0,
        "remaining_weight": 910.0,
        "used_weight": 90.0,
        "location": "Regal B2",
        "archived": False,
        "extra": {},
    },
]


class SimulationFleet:
    """Thread-safe interactive simulation state for virtual 3D printers."""

    def __init__(self):
        self._lock = threading.Lock()
        self._start_ts = time.time()
        self._states: Dict[str, Dict] = {
            "sim_voron24": {
                "state": "printing",
                "klipper": "ready",
                "filename": "Voron_Stealthburner_Mount_Set_ABS.gcode",
                "progress_base": 0.64,
                "duration_base": 5420.0,
                "total_est": 8400.0,
                "nozzle_cur": 255.0,
                "nozzle_tgt": 255.0,
                "bed_cur": 105.0,
                "bed_tgt": 105.0,
                "chamber_cur": 54.2,
                "fan_speed": 0.45,
                "speed_factor": 1.0,
                "extrude_factor": 0.98,
                "z_offset": -0.015,
                "homed": "xyz",
                "pos": [175.0, 175.0, 28.4],
                "layer": 142,
                "total_layers": 220,
                "active_spool_id": 901,
                "slot_spool_ids": [901],
                "excluded_objects": [],
                "console": [
                    {"time": time.time() - 300, "type": "command", "message": "PRINT_START EXTRUDER=255 BED=105 CHAMBER=50"},
                    {"time": time.time() - 290, "type": "response", "message": "Quad Gantry Leveling completed (tolerance: 0.0042 mm)"},
                    {"time": time.time() - 280, "type": "response", "message": "Bed Mesh profile 'abs_105' loaded."},
                    {"time": time.time() - 120, "type": "response", "message": "Layer 140/220 — Speed 240 mm/s, Accel 8000 mm/s²"},
                ],
            },
            "sim_bambux1c": {
                "state": "printing",
                "klipper": "Bambu OS",
                "filename": "Planetary_Gearbox_Assy_v4.3mf",
                "progress_base": 0.38,
                "duration_base": 2940.0,
                "total_est": 7800.0,
                "nozzle_cur": 220.0,
                "nozzle_tgt": 220.0,
                "bed_cur": 60.0,
                "bed_tgt": 60.0,
                "chamber_cur": 37.8,
                "fan_speed": 0.85,
                "speed_factor": 1.24,
                "extrude_factor": 1.0,
                "speed_level": 3,  # Sport
                "chamber_light": True,
                "z_offset": 0.0,
                "homed": "xyz",
                "pos": [128.0, 128.0, 14.2],
                "layer": 71,
                "total_layers": 186,
                "active_spool_id": 902,
                "slot_spool_ids": [902, 903, 901, 904],
                "excluded_objects": [],
                "console": [
                    {"time": time.time() - 400, "type": "response", "message": "Bambu Lab X1C: First layer LiDAR inspection PASSED"},
                    {"time": time.time() - 180, "type": "response", "message": "AMS Slot 1 (PLA Cyan) active"},
                ],
            },
            "sim_vcore4": {
                "state": "standby",
                "klipper": "ready",
                "filename": "",
                "progress_base": 0.0,
                "duration_base": 0.0,
                "total_est": 3600.0,
                "nozzle_cur": 24.6,
                "nozzle_tgt": 0.0,
                "bed_cur": 23.8,
                "bed_tgt": 0.0,
                "chamber_cur": 24.1,
                "fan_speed": 0.0,
                "speed_factor": 1.0,
                "extrude_factor": 1.0,
                "z_offset": 0.000,
                "homed": "xyz",
                "pos": [200.0, 200.0, 15.0],
                "layer": 0,
                "total_layers": 0,
                "active_spool_id": 904,
                "slot_spool_ids": [904],
                "excluded_objects": [],
                "console": [
                    {"time": time.time() - 600, "type": "response", "message": "Klipper ready — RatOS v2.1 Beacon Contact Ready"},
                ],
            },
        }

    def is_sim_printer(self, pid: str) -> bool:
        return str(pid).startswith("sim_")

    def get_printers(self) -> List[Printer]:
        return list(DEMO_PRINTERS)

    def _generate_bed_mesh(self, pid: str):
        if pid == "sim_vcore4":
            size = 9
            max_coord = 400.0
            amp = 0.045
        else:
            size = 7
            max_coord = 350.0
            amp = 0.068
        matrix = []
        for r in range(size):
            row = []
            ny = (r / (size - 1)) * 2.0 - 1.0
            for c in range(size):
                nx = (c / (size - 1)) * 2.0 - 1.0
                # Realistic saddle/dome contour in mm
                val = amp * (0.6 * (nx * nx - 0.4 * ny * ny) + 0.35 * math.sin(nx * 2.2) * math.cos(ny * 2.2))
                row.append(round(val, 4))
            matrix.append(row)
        flat = [v for row in matrix for v in row]
        return {
            "profile_name": "ratos_beacon" if pid == "sim_vcore4" else "voron_tap_105c",
            "mesh_min": [25.0, 25.0],
            "mesh_max": [max_coord - 25.0, max_coord - 25.0],
            "probed_matrix": matrix,
            "mesh_matrix": matrix,
            "min_val": min(flat),
            "max_val": max(flat),
            "variance": round(max(flat) - min(flat), 4),
            "profiles": ["default", "voron_tap_105c", "pla_60c"],
        }

    def _generate_exclude_objects(self, st: Dict):
        excluded = list(st.get("excluded_objects") or [])
        objs = [
            {
                "name": "Stealthburner_Main_Body",
                "center": [110.0, 120.0],
                "polygon": [[75, 85], [145, 85], [145, 155], [75, 155]],
            },
            {
                "name": "Clockwork2_Extruder_Guidler",
                "center": [235.0, 115.0],
                "polygon": [[200, 90], [270, 90], [270, 140], [200, 140]],
            },
            {
                "name": "Gantry_Motor_Mount_Left",
                "center": [115.0, 235.0],
                "polygon": [[80, 200], [150, 200], [150, 270], [80, 270]],
            },
            {
                "name": "Cable_Chain_Anchor_Mount",
                "center": [235.0, 235.0],
                "polygon": [[210, 210], [260, 210], [260, 260], [210, 260]],
            },
        ]
        active_candidates = [o["name"] for o in objs if o["name"] not in excluded]
        idx = int(time.time() / 6) % len(active_candidates) if active_candidates else 0
        current_obj = active_candidates[idx] if active_candidates else None
        return {
            "objects": objs,
            "excluded_objects": excluded,
            "current_object": current_obj if st.get("state") == "printing" else None,
        }

    def fetch_status(self, p: Printer) -> Dict:
        now = time.time()
        dt = now - self._start_ts
        with self._lock:
            st = self._states.get(p.id)
            if not st:
                return {"state": "offline", "error": "Unknown sim printer"}

            # Thermal physics step toward target
            ambient = 23.6
            n_tgt = st["nozzle_tgt"] if st["nozzle_tgt"] > 0 else ambient
            b_tgt = st["bed_tgt"] if st["bed_tgt"] > 0 else ambient
            st["nozzle_cur"] += (n_tgt - st["nozzle_cur"]) * 0.28 + math.sin(now * 1.7) * 0.12
            st["bed_cur"] += (b_tgt - st["bed_cur"]) * 0.18 + math.cos(now * 1.1) * 0.06

            state = st["state"]
            if state == "printing":
                prog = min(0.99, st["progress_base"] + (dt % 1800) / 18000.0)
                dur = st["duration_base"] + dt
                rem = max(60.0, st["total_est"] * (1.0 - prog) / max(0.5, st["speed_factor"]))
                total_layers = max(1, st["total_layers"] or 200)
                layer = max(1, int(round(prog * total_layers)))
                cx = 175.0 + math.sin(now * 0.9) * 42.0
                cy = 175.0 + math.cos(now * 0.7) * 42.0
                cz = round(layer * 0.2, 2)
                pos = [round(cx, 1), round(cy, 1), cz]
            elif state == "paused":
                prog = st["progress_base"]
                dur = st["duration_base"]
                rem = st["total_est"] * (1.0 - prog)
                layer = st["layer"]
                total_layers = st["total_layers"]
                pos = list(st["pos"])
            else:
                prog = 1.0 if state == "complete" else 0.0
                dur = st["duration_base"] if state == "complete" else 0.0
                rem = None
                layer = st["total_layers"] if state == "complete" else 0
                total_layers = st["total_layers"]
                pos = list(st["pos"])

            eta_str = ""
            if rem and rem > 0:
                eta_dt = time.localtime(now + rem)
                eta_str = time.strftime("%H:%M Uhr", eta_dt)

            temps = [
                ("Düse", round(st["nozzle_cur"], 1), round(st["nozzle_tgt"], 1)),
                ("Bett", round(st["bed_cur"], 1), round(st["bed_tgt"], 1)),
                ("Kammer", round(st["chamber_cur"] + math.sin(now * 0.3) * 0.1, 1), 0.0),
            ]

            is_bambu = p.printer_type == "bambu"
            return {
                "state": state,
                "klipper": st["klipper"],
                "filename": st["filename"],
                "progress": round(prog, 4),
                "duration": round(dur, 1),
                "remaining": round(rem, 1) if rem else None,
                "eta": eta_str,
                "temps": temps,
                "heaters": ["extruder", "heater_bed"],
                "homed": st["homed"],
                "position": pos,
                "z_offset": st["z_offset"],
                "fan_speed": st["fan_speed"],
                "speed_factor": st["speed_factor"],
                "extrude_factor": st["extrude_factor"],
                "speed_level": st.get("speed_level", 1),
                "chamber_light": st.get("chamber_light", True),
                "layer": layer,
                "total_layers": total_layers,
                "active_spool_id": st["active_spool_id"],
                "slot_spool_ids": list(st["slot_spool_ids"]),
                "active_extruder": "extruder",
                "is_bambu": is_bambu,
                "is_sim": True,
                "bed_mesh": None if is_bambu else self._generate_bed_mesh(p.id),
                "exclude_object": self._generate_exclude_objects(st),
            }

    def control(self, p: Printer, action: str, **kw):
        with self._lock:
            st = self._states.get(p.id)
            if not st:
                raise RuntimeError("Sim printer not found")

            def log_cmd(msg: str, kind: str = "command"):
                st["console"].append({"time": time.time(), "type": kind, "message": msg})
                if len(st["console"]) > 120:
                    st["console"] = st["console"][-120:]

            if action == "pause":
                st["state"] = "paused"
                log_cmd("PAUSE")
            elif action == "resume":
                st["state"] = "printing"
                log_cmd("RESUME")
            elif action == "cancel":
                st["state"] = "cancelled"
                st["nozzle_tgt"] = 0.0
                st["bed_tgt"] = 0.0
                st["fan_speed"] = 0.0
                log_cmd("CANCEL_PRINT")
            elif action == "emergency_stop":
                st["state"] = "error"
                st["klipper"] = "shutdown"
                st["nozzle_tgt"] = 0.0
                st["bed_tgt"] = 0.0
                log_cmd("M112 — EMERGENCY STOP TRIGGERED", "response")
            elif action in ("firmware_restart", "restart"):
                st["state"] = "standby"
                st["klipper"] = "ready"
                log_cmd("FIRMWARE_RESTART — Klipper ready", "response")
            elif action == "temp":
                heater = str(kw.get("heater", "extruder")).lower()
                target = float(kw.get("target", 0))
                if "bed" in heater or "bett" in heater:
                    st["bed_tgt"] = target
                    log_cmd(f"SET_HEATER_TEMPERATURE HEATER=heater_bed TARGET={target:.0f}")
                else:
                    st["nozzle_tgt"] = target
                    log_cmd(f"SET_HEATER_TEMPERATURE HEATER=extruder TARGET={target:.0f}")
            elif action == "fan":
                pct = float(kw.get("percent", kw.get("speed", 0)))
                st["fan_speed"] = max(0.0, min(1.0, pct / 100.0))
                log_cmd(f"M106 S{int(st['fan_speed'] * 255)}")
            elif action == "speed":
                pct = float(kw.get("percent", 100))
                st["speed_factor"] = max(0.1, min(3.0, pct / 100.0))
                if "level" in kw:
                    st["speed_level"] = int(kw["level"])
                log_cmd(f"M220 S{int(pct)}")
            elif action == "flow":
                pct = float(kw.get("percent", 100))
                st["extrude_factor"] = max(0.5, min(2.0, pct / 100.0))
                log_cmd(f"M221 S{int(pct)}")
            elif action == "home":
                axes = str(kw.get("axes", "")).strip() or "X Y Z"
                st["homed"] = "xyz"
                st["pos"] = [175.0, 175.0, 10.0]
                log_cmd(f"G28 {axes}")
            elif action == "jog":
                axis = str(kw.get("axis", "")).upper()
                dist = float(kw.get("dist", 0))
                if axis == "X":
                    st["pos"][0] = round(max(0.0, min(400.0, st["pos"][0] + dist)), 1)
                elif axis == "Y":
                    st["pos"][1] = round(max(0.0, min(400.0, st["pos"][1] + dist)), 1)
                elif axis == "Z":
                    st["pos"][2] = round(max(0.0, min(400.0, st["pos"][2] + dist)), 2)
                log_cmd(f"G91 / G1 {axis}{dist:+.1f} / G90")
            elif action == "z_offset":
                if kw.get("reset"):
                    st["z_offset"] = 0.0
                else:
                    st["z_offset"] = round(st["z_offset"] + float(kw.get("delta", 0.0)), 3)
                log_cmd(f"SET_GCODE_OFFSET Z={st['z_offset']:+.3f} MOVE=1")
            elif action == "exclude_object":
                obj_name = str(kw.get("name") or kw.get("object_name") or kw.get("value") or "").strip()
                if obj_name and obj_name not in st["excluded_objects"]:
                    st["excluded_objects"].append(obj_name)
                    log_cmd(f"EXCLUDE_OBJECT NAME={obj_name}")
                    log_cmd(f"Object '{obj_name}' excluded from remaining toolpaths.", "response")
            elif action == "bed_mesh_calibrate":
                log_cmd("BED_MESH_CALIBRATE")
                log_cmd("Probing 49 points... Mesh calibration complete.", "response")
            elif action in ("qgl", "z_tilt"):
                cmd_name = "QUAD_GANTRY_LEVEL" if action == "qgl" else "Z_TILT_ADJUST"
                log_cmd(cmd_name)
                log_cmd(f"{cmd_name} finished within tolerance (0.0035 mm).", "response")
            elif action == "motors_off":
                st["homed"] = ""
                log_cmd("M84 — Motors disabled")
            elif action == "chamber_light":
                st["chamber_light"] = bool(kw.get("on", not st.get("chamber_light", True)))
                log_cmd(f"LED Chamber Light: {'ON' if st['chamber_light'] else 'OFF'}")
            elif action == "start_file":
                fname = str(kw.get("filename", "Print_Job.gcode"))
                st["filename"] = fname
                st["state"] = "printing"
                st["progress_base"] = 0.05
                st["duration_base"] = 60.0
                st["nozzle_tgt"] = 220.0
                st["bed_tgt"] = 60.0
                st["layer"] = 3
                st["total_layers"] = 180
                st["excluded_objects"] = []
                log_cmd(f"SDCARD_PRINT_FILE FILENAME={fname}")
            elif action == "macro":
                mname = str(kw.get("name", "MACRO"))
                log_cmd(mname)
                log_cmd(f"Macro '{mname}' executed.", "response")
            elif action == "gcode":
                script = str(kw.get("script", "")).strip()
                log_cmd(script)
                log_cmd("ok", "response")

            return {"result": "ok"}

    def get_remote_files(self, p: Printer) -> List[Dict]:
        now = int(time.time())
        return [
            {"path": "Voron_Stealthburner_Mount_Set_ABS.gcode", "size": 14820400, "modified": now - 3600},
            {"path": "Planetary_Gearbox_Assy_v4.gcode", "size": 9412000, "modified": now - 18400},
            {"path": "Gridfinity_Bin_2x3_6U_Fast.gcode", "size": 5240100, "modified": now - 86400},
            {"path": "Calibration_Cube_XYZ_20mm.gcode", "size": 842000, "modified": now - 172800},
            {"path": "Benchy_SpeedBoat_14min.gcode", "size": 3190000, "modified": now - 250000},
        ]

    def get_macros(self, p: Printer) -> List[str]:
        if p.printer_type == "bambu":
            return ["CHAMBER_LIGHT_ON", "CHAMBER_LIGHT_OFF", "UNLOAD_FILAMENT"]
        return [
            "PRINT_START",
            "PRINT_END",
            "CLEAN_NOZZLE",
            "LOAD_FILAMENT",
            "UNLOAD_FILAMENT",
            "QUAD_GANTRY_LEVEL",
            "BED_MESH_CALIBRATE",
            "HEATSOAK_CHAMBER",
            "PARK_TOOLHEAD",
            "PID_TUNE_HOTEND",
        ]

    def get_console(self, p: Printer) -> List[Dict]:
        with self._lock:
            st = self._states.get(p.id, {})
            return list(st.get("console", []))

    def get_history(self, p: Printer) -> List[Dict]:
        now = int(time.time())
        return [
            {
                "job_id": f"{p.id}_1",
                "filename": "Voron_Stealthburner_Main_ABS.gcode",
                "status": "completed",
                "start_time": now - 86400 * 1,
                "total_duration": 7820,
                "filament_used": 28400,
            },
            {
                "job_id": f"{p.id}_2",
                "filename": "Gridfinity_Baseplate_4x4_PLA.gcode",
                "status": "completed",
                "start_time": now - 86400 * 3,
                "total_duration": 5400,
                "filament_used": 19500,
            },
            {
                "job_id": f"{p.id}_3",
                "filename": "Cable_Chain_Links_x24_PETG.gcode",
                "status": "completed",
                "start_time": now - 86400 * 8,
                "total_duration": 11200,
                "filament_used": 36200,
            },
            {
                "job_id": f"{p.id}_4",
                "filename": "Prototype_Bracket_v1_ABS.gcode",
                "status": "cancelled",
                "start_time": now - 86400 * 15,
                "total_duration": 1400,
                "filament_used": 4100,
            },
            {
                "job_id": f"{p.id}_5",
                "filename": "Enclosure_Hinge_Heavy_ASA.gcode",
                "status": "completed",
                "start_time": now - 86400 * 35,
                "total_duration": 14800,
                "filament_used": 48900,
            },
        ]


SIM = SimulationFleet()
