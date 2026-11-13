"""Bambu Lab local MQTT & FTPS client.
Supports Bambu Lab X1/P1/A1 series printers connected in LAN mode.
"""
from dataclasses import dataclass, field
import json
import logging
import ssl
import threading
import time
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("printboard.bambu")


@dataclass
class BambuPrinterState:
    online: bool = False
    gcode_state: str = "IDLE"  # IDLE, RUNNING, PAUSE, FINISH, FAILED
    mc_percent: int = 0
    mc_remaining_time: int = 0  # in minutes
    subtask_name: str = ""
    gcode_file: str = ""
    nozzle_temper: float = 0.0
    nozzle_target_temper: float = 0.0
    bed_temper: float = 0.0
    bed_target_temper: float = 0.0
    chamber_temper: float = 0.0
    fan_gear: int = 0  # cooling fan speed
    heatbreak_fan_speed: int = 0
    speed_level: int = 1  # 1=Standard, 2=Silent, 3=Sport, 4=Ludicrous
    layer_num: int = 0
    total_layer_num: int = 0
    lights_report: List[Dict] = field(default_factory=list)
    ams_status: Dict = field(default_factory=dict)
    ams_tray_now: Optional[int] = None
    spool_id: Optional[int] = None
    last_update: float = 0.0
    raw_payload: Dict = field(default_factory=dict)

    def normalized_state(self) -> str:
        if not self.online:
            return "offline"
        s = (self.gcode_state or "").upper()
        if s in ("RUNNING", "PREPARE"):
            return "printing"
        if s in ("PAUSE", "PAUSED"):
            return "paused"
        if s in ("FINISH", "FINISHED", "SUCCESS"):
            return "complete"
        if s in ("FAILED", "ERROR"):
            return "error"
        if s in ("IDLE", "STANDBY"):
            return "standby"
        return "standby"


class BambuMqttClient:
    """Connects to Bambu printer MQTT on port 8883 (TLS with self-signed cert)."""

    def __init__(self, host: str, serial: str, access_code: str, port: int = 8883):
        self.host = host.strip()
        self.serial = serial.strip()
        self.access_code = access_code.strip()
        self.port = int(port)
        self.state = BambuPrinterState()
        self._client = None
        self._thread = None
        self._running = False
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[BambuPrinterState], None]] = []

    def add_callback(self, cb: Callable[[BambuPrinterState], None]):
        self._callbacks.append(cb)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                pass
        with self._lock:
            self.state.online = False

    def _run_loop(self):
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            logger.error("paho-mqtt not available for Bambu printer integration")
            return

        client_id = f"printboard_{self.serial[:8]}_{int(time.time())}"
        try:
            client = mqtt.Client(client_id=client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        except (AttributeError, TypeError):
            client = mqtt.Client(client_id=client_id)

        client.username_pw_set("bblp", self.access_code)
        # Bambu uses self-signed SSL certs on port 8883
        client.tls_set(cert_reqs=ssl.CERT_NONE)
        client.tls_insecure_set(True)

        def on_connect(c, userdata, flags, rc, *args):
            with self._lock:
                self.state.online = True
            topic = f"device/{self.serial}/report"
            c.subscribe(topic)
            # Request initial push
            push_cmd = {
                "pushing": {
                    "sequence_id": "0",
                    "command": "pushall"
                }
            }
            c.publish(f"device/{self.serial}/request", json.dumps(push_cmd))

        def on_disconnect(c, userdata, *args):
            with self._lock:
                self.state.online = False
            self._notify()

        def on_message(c, userdata, msg):
            try:
                payload = json.loads(msg.payload.decode("utf-8", errors="ignore"))
                self._update_state(payload)
            except Exception as e:
                logger.debug("Failed to parse Bambu MQTT payload: %s", e)

        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        self._client = client

        while self._running:
            try:
                client.connect(self.host, self.port, keepalive=30)
                client.loop_forever(timeout=1.0)
            except Exception as e:
                with self._lock:
                    self.state.online = False
                self._notify()
                time.sleep(4)

    def _update_state(self, payload: Dict):
        print_data = payload.get("print") or payload
        with self._lock:
            self.state.online = True
            self.state.last_update = time.time()
            self.state.raw_payload = print_data

            if "gcode_state" in print_data:
                self.state.gcode_state = str(print_data["gcode_state"])
            if "mc_percent" in print_data:
                self.state.mc_percent = int(print_data["mc_percent"])
            if "mc_remaining_time" in print_data:
                self.state.mc_remaining_time = int(print_data["mc_remaining_time"])
            if "subtask_name" in print_data and print_data["subtask_name"]:
                self.state.subtask_name = str(print_data["subtask_name"])
            if "gcode_file" in print_data and print_data["gcode_file"]:
                self.state.gcode_file = str(print_data["gcode_file"])
            if "nozzle_temper" in print_data:
                self.state.nozzle_temper = float(print_data["nozzle_temper"])
            if "nozzle_target_temper" in print_data:
                self.state.nozzle_target_temper = float(print_data["nozzle_target_temper"])
            if "bed_temper" in print_data:
                self.state.bed_temper = float(print_data["bed_temper"])
            if "bed_target_temper" in print_data:
                self.state.bed_target_temper = float(print_data["bed_target_temper"])
            if "chamber_temper" in print_data:
                self.state.chamber_temper = float(print_data["chamber_temper"])
            if "cooling_fan_speed" in print_data:
                self.state.fan_gear = int(print_data["cooling_fan_speed"])
            if "spd_lvl" in print_data:
                self.state.speed_level = int(print_data["spd_lvl"])
            if "layer_num" in print_data:
                self.state.layer_num = int(print_data["layer_num"])
            if "total_layer_num" in print_data:
                self.state.total_layer_num = int(print_data["total_layer_num"])
            if "ams" in print_data:
                self.state.ams_status = print_data["ams"]
            if "ams_status" in print_data:
                self.state.ams_tray_now = print_data.get("ams_status")
            if "lights_report" in print_data:
                self.state.lights_report = print_data["lights_report"]

        self._notify()

    def _notify(self):
        snap = self.get_snapshot()
        for cb in self._callbacks:
            try:
                cb(snap)
            except Exception:
                pass

    def get_snapshot(self) -> BambuPrinterState:
        with self._lock:
            st = BambuPrinterState(
                online=self.state.online,
                gcode_state=self.state.gcode_state,
                mc_percent=self.state.mc_percent,
                mc_remaining_time=self.state.mc_remaining_time,
                subtask_name=self.state.subtask_name,
                gcode_file=self.state.gcode_file,
                nozzle_temper=self.state.nozzle_temper,
                nozzle_target_temper=self.state.nozzle_target_temper,
                bed_temper=self.state.bed_temper,
                bed_target_temper=self.state.bed_target_temper,
                chamber_temper=self.state.chamber_temper,
                fan_gear=self.state.fan_gear,
                speed_level=self.state.speed_level,
                layer_num=self.state.layer_num,
                total_layer_num=self.state.total_layer_num,
                ams_status=self.state.ams_status,
                ams_tray_now=self.state.ams_tray_now,
                spool_id=self.state.spool_id,
                last_update=self.state.last_update,
            )
            return st

    def send_command(self, cmd_dict: Dict) -> bool:
        if not self._client or not self.state.online:
            return False
        topic = f"device/{self.serial}/request"
        res = self._client.publish(topic, json.dumps(cmd_dict))
        return res.rc == 0

    def pause(self) -> bool:
        return self.send_command({"print": {"sequence_id": "0", "command": "pause"}})

    def resume(self) -> bool:
        return self.send_command({"print": {"sequence_id": "0", "command": "resume"}})

    def stop_print(self) -> bool:
        return self.send_command({"print": {"sequence_id": "0", "command": "stop"}})

    def set_speed_level(self, level: int) -> bool:
        # 1=Standard, 2=Silent, 3=Sport, 4=Ludicrous
        level_map = {1: "1", 2: "2", 3: "3", 4: "4"}
        param = level_map.get(level, "1")
        return self.send_command({"print": {"sequence_id": "0", "command": "print_speed", "param": param}})

    def set_bed_temp(self, temp: float) -> bool:
        return self.send_command({"print": {"sequence_id": "0", "command": "gcode_line", "param": f"M140 S{int(temp)}\n"}})

    def set_nozzle_temp(self, temp: float) -> bool:
        return self.send_command({"print": {"sequence_id": "0", "command": "gcode_line", "param": f"M104 S{int(temp)}\n"}})

    def set_fan(self, speed_pct: int) -> bool:
        val = int(max(0, min(100, speed_pct)) * 2.55)
        return self.send_command({"print": {"sequence_id": "0", "command": "gcode_line", "param": f"M106 P1 S{val}\n"}})

    def set_chamber_light(self, on: bool) -> bool:
        mode = "on" if on else "off"
        return self.send_command({
            "system": {
                "sequence_id": "0",
                "command": "ledctrl",
                "led_node": "chamber_light",
                "led_mode": mode,
                "led_on_time": 500,
                "led_off_time": 500,
                "loop_times": 0,
                "interval_time": 0
            }
        })


_BAMBU_CLIENTS: Dict[str, BambuMqttClient] = {}


def get_or_create_client(p) -> Optional[BambuMqttClient]:
    """Get or instantiate a BambuMqttClient for a printer configured with printer_type='bambu'."""
    if getattr(p, "printer_type", "moonraker") != "bambu":
        return None
    serial = getattr(p, "bambu_serial", "") or getattr(p, "id", "")
    code = getattr(p, "bambu_access_code", "") or getattr(p, "token", "")
    if not p.host or not serial or not code:
        return None

    key = f"{p.host}:{serial}"
    if key not in _BAMBU_CLIENTS:
        client = BambuMqttClient(host=p.host, serial=serial, access_code=code)
        client.start()
        _BAMBU_CLIENTS[key] = client
    return _BAMBU_CLIENTS[key]


def fetch_bambu_status(p) -> Dict:
    """Returns a dict matching api.fetch() return format for seamless UI compatibility."""
    client = get_or_create_client(p)
    if not client:
        return {
            "state": "offline",
            "klipper": "Bambu Lab",
            "filename": "",
            "progress": 0.0,
            "duration": 0.0,
            "remaining": None,
            "temps": [("Düse", 0.0, 0.0), ("Bett", 0.0, 0.0)],
            "heaters": ["extruder", "heater_bed"],
            "homed": "xyz",
            "position": [0.0, 0.0, 0.0],
            "z_offset": 0.0,
            "fan_speed": 0.0,
            "active_spool_id": None,
            "slot_spool_ids": [],
            "active_extruder": "extruder",
            "is_bambu": True,
        }

    st = client.get_snapshot()
    progress = max(0.0, min(1.0, float(st.mc_percent) / 100.0))
    remaining_secs = st.mc_remaining_time * 60.0 if st.mc_remaining_time > 0 else None
    fname = st.subtask_name or st.gcode_file or ""
    fan_speed = max(0.0, min(1.0, float(st.fan_gear) / 100.0))

    temps = [
        ("Düse", st.nozzle_temper, st.nozzle_target_temper),
        ("Bett", st.bed_temper, st.bed_target_temper),
    ]
    if st.chamber_temper > 0:
        temps.append(("Kammer", st.chamber_temper, 0.0))

    slot_spool_ids = []
    # AMS slots
    if isinstance(st.ams_status, dict):
        ams_list = st.ams_status.get("ams") or []
        for ams in ams_list:
            for tray in (ams.get("tray") or []):
                slot_spool_ids.append(tray.get("id"))

    return {
        "state": st.normalized_state(),
        "klipper": "Bambu OS",
        "filename": fname,
        "progress": progress,
        "duration": 0.0,
        "remaining": remaining_secs,
        "temps": temps,
        "heaters": ["extruder", "heater_bed"],
        "homed": "xyz",
        "position": [0.0, 0.0, 0.0],
        "z_offset": 0.0,
        "fan_speed": fan_speed,
        "active_spool_id": None,
        "slot_spool_ids": slot_spool_ids,
        "active_extruder": "extruder",
        "is_bambu": True,
        "speed_level": st.speed_level,
        "layer": st.layer_num,
        "total_layers": st.total_layer_num,
    }
