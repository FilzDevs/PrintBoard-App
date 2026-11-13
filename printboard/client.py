"""PrintBoard Studio 1.0 Remote Client.
Connects to any PrintBoard Studio Server (IP / URL) and loads the full hardware-accelerated
PrintBoard Studio 1.0 interface (Easy & Advanced Mode, G-Code Studio, Bed Mesh 3D, Spoolman, etc.).
"""
from __future__ import annotations

import json
import sys
import threading
import urllib.request
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .pages import S

ICON = Path(__file__).with_name("icon.svg")

CLIENT_QSS = """
QMainWindow, QWidget#login_bg {
    background: #05080F;
    color: #F8FAFC;
    font-family: "Inter", "Segoe UI", sans-serif;
}
QFrame#login_card {
    background: #0E1523;
    border: 1px solid #1E2D48;
    border-radius: 16px;
}
QFrame#conn_bar {
    background: #090E18;
    border-bottom: 1px solid #1E2D48;
}
QLineEdit {
    background: #080D16;
    border: 1px solid #223352;
    border-radius: 9px;
    padding: 10px 14px;
    color: #F8FAFC;
    font-size: 13px;
}
QLineEdit:focus {
    border-color: #00E5FF;
}
QPushButton {
    background: #141F33;
    border: 1px solid #223352;
    color: #F8FAFC;
    border-radius: 9px;
    padding: 9px 16px;
    font-size: 12.5px;
    font-weight: 700;
}
QPushButton:hover {
    background: #1A2842;
    border-color: #00E5FF;
}
QPushButton#primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00E5FF, stop:1 #3B82F6);
    color: #031017;
    border: none;
    font-weight: 800;
}
"""


class ClientSig(QObject):
    connected = Signal(str, dict)
    failed = Signal(str)


class ClientMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PrintBoard Studio 1.0 — Remote Client")
        self.resize(1420, 880)
        self.setStyleSheet(CLIENT_QSS)

        self.sig = ClientSig()
        self.sig.connected.connect(self._on_connected)
        self.sig.failed.connect(self._on_failed)

        self.stack = QStackedWidget(self)
        self.setCentralWidget(self.stack)

        # Page 0: Login Card
        login_wrap = QWidget()
        login_wrap.setObjectName("login_bg")
        ll = QVBoxLayout(login_wrap)
        ll.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("login_card")
        card.setFixedWidth(450)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(34, 34, 34, 34)
        cl.setSpacing(14)

        badge = QLabel("PRINTBOARD STUDIO 1.0  ·  REMOTE CLIENT")
        badge.setStyleSheet("font-size:10.5px;font-weight:800;color:#00E5FF;letter-spacing:1.2px;")
        badge.setAlignment(Qt.AlignCenter)
        cl.addWidget(badge)

        title = QLabel("Mit PrintBoard Server verbinden")
        title.setStyleSheet("font-size:20px;font-weight:900;color:#F8FAFC;")
        title.setAlignment(Qt.AlignCenter)
        cl.addWidget(title)

        sub = QLabel("Gib die Adresse deines PrintBoard Servers im Netzwerk ein:")
        sub.setStyleSheet("font-size:12.5px;color:#94A3B8;")
        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)
        cl.addWidget(sub)

        saved_url = str(S().value("remote_server_url", "http://127.0.0.1:8080"))
        self.ip_input = QLineEdit(saved_url)
        self.ip_input.setPlaceholderText("z.B. http://192.168.178.50:8080")
        self.ip_input.returnPressed.connect(self.do_connect)
        cl.addWidget(self.ip_input)

        self.btn_connect = QPushButton("Verbindung herstellen")
        self.btn_connect.setObjectName("primary")
        self.btn_connect.setCursor(Qt.PointingHandCursor)
        self.btn_connect.clicked.connect(self.do_connect)
        cl.addWidget(self.btn_connect)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("font-size:12px;color:#F43F5E;")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        self.status_lbl.setWordWrap(True)
        cl.addWidget(self.status_lbl)

        ll.addWidget(card)
        self.stack.addWidget(login_wrap)

        # Page 1: Connected Remote Studio View
        remote_wrap = QWidget()
        rl = QVBoxLayout(remote_wrap)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        bar = QFrame()
        bar.setObjectName("conn_bar")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(16, 6, 16, 6)
        self.srv_lbl = QLabel("Verbunden mit PrintBoard Server")
        self.srv_lbl.setStyleSheet("font-size:11.5px;font-weight:700;color:#10B981;")
        btn_disc = QPushButton("Server trennen")
        btn_disc.setCursor(Qt.PointingHandCursor)
        btn_disc.setStyleSheet("padding:4px 12px;font-size:11.5px;")
        btn_disc.clicked.connect(self.disconnect_server)
        bl.addWidget(self.srv_lbl)
        bl.addStretch()
        bl.addWidget(btn_disc)

        self.web = QWebEngineView()
        self.web.page().setBackgroundColor(QColor("#05080F"))
        self.web.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)

        rl.addWidget(bar)
        rl.addWidget(self.web, 1)
        self.stack.addWidget(remote_wrap)

    def do_connect(self):
        url = self.ip_input.text().strip().rstrip("/")
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"http://{url}"
        self.status_lbl.setStyleSheet("font-size:12px;color:#00E5FF;")
        self.status_lbl.setText("Verbinde mit PrintBoard Studio Server …")
        self.btn_connect.setEnabled(False)
        threading.Thread(target=self._probe, args=(url,), daemon=True).start()

    def _probe(self, url: str):
        try:
            req = urllib.request.Request(f"{url}/api/state", headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=4) as r:
                data = json.loads(r.read())
            self.sig.connected.emit(url, data)
        except Exception as e:
            self.sig.failed.emit(str(e))

    def _on_connected(self, url: str, data: dict):
        S().setValue("remote_server_url", url)
        self.btn_connect.setEnabled(True)
        self.status_lbl.setText("")
        p_count = len(data.get("printers") or [])
        self.srv_lbl.setText(f"● Verbunden mit {url}  ·  {p_count} Drucker synchronisiert")
        self.web.load(QUrl(f"{url}/"))
        self.stack.setCurrentIndex(1)

    def _on_failed(self, err: str):
        self.btn_connect.setEnabled(True)
        self.status_lbl.setStyleSheet("font-size:12px;color:#F43F5E;")
        self.status_lbl.setText(f"Verbindung fehlgeschlagen: {err}")

    def disconnect_server(self):
        self.web.setUrl(QUrl("about:blank"))
        self.stack.setCurrentIndex(0)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("printboard-client")
    if ICON.exists():
        app.setWindowIcon(QIcon(str(ICON)))
    w = ClientMainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
