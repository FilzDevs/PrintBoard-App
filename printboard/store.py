"""Persistent printer list in ~/.config/printboard/printers.json (mode 600)."""
import json, os, uuid
from dataclasses import dataclass, asdict, field
from pathlib import Path

CFG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "printboard"
FILE = CFG / "printers.json"


@dataclass
class Printer:
    name: str
    host: str
    port: int = 80
    token: str = ""
    tls: bool = False
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    display_url: str = ""
    printer_type: str = "moonraker"  # "moonraker" or "bambu"
    bambu_serial: str = ""
    bambu_access_code: str = ""

    @property
    def base(self):
        return f"{'https' if self.tls else 'http'}://{self.host}:{self.port}"


def load():
    try:
        raw = json.loads(FILE.read_text())
        printers = []
        for d in raw:
            # Tolerant loading if unknown fields or missing fields
            p_kwargs = {
                "name": d.get("name", "Drucker"),
                "host": d.get("host", ""),
                "port": int(d.get("port", 80)),
                "token": d.get("token", ""),
                "tls": bool(d.get("tls", False)),
                "id": d.get("id", uuid.uuid4().hex[:8]),
                "display_url": d.get("display_url", ""),
                "printer_type": d.get("printer_type", "moonraker"),
                "bambu_serial": d.get("bambu_serial", ""),
                "bambu_access_code": d.get("bambu_access_code", ""),
            }
            printers.append(Printer(**p_kwargs))
        return printers
    except (OSError, ValueError, TypeError):
        return []


def save(printers):
    CFG.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps([asdict(p) for p in printers], indent=2))
    os.chmod(FILE, 0o600)
