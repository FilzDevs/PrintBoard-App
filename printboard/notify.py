"""Telegram and Discord webhook notifications."""
import json
import threading
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def send_discord(
    url,
    text="**PrintBoard Test-Benachrichtigung**\nDie Discord-Webhook-Verbindung funktioniert einwandfrei.",
):
    if not url or not url.strip():
        raise ValueError("Keine Discord-Webhook-URL angegeben.")
    clean_url = url.strip()
    req = Request(
        clean_url,
        data=json.dumps({"content": text}).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "PrintBoard/0.3"},
    )
    with urlopen(req, timeout=10) as resp:
        if resp.status not in (200, 204):
            raise RuntimeError(f"Discord antwortete mit HTTP-Status {resp.status}")
    return True


def _send(cfg, text):
    if cfg.get("tg_token") and cfg.get("tg_chat"):
        urlopen(
            Request(
                f"https://api.telegram.org/bot{cfg['tg_token']}/sendMessage",
                data=urlencode({"chat_id": cfg["tg_chat"], "text": text}).encode(),
            ),
            timeout=10,
        )
    if cfg.get("discord"):
        send_discord(cfg["discord"], text)


def dispatch(cfg, text):
    def run():
        try:
            _send(cfg, text)
        except Exception:
            pass

    threading.Thread(target=run, daemon=True).start()
