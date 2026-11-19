"""PrintBoard Studio 1.0 — Next-Gen Desktop Application Shell.
Combines a hardware-accelerated QWebEngineView Studio UI (Easy & Advanced Mode,
2D/3D G-Code Layer Studio, Bed Mesh 3D, Exclude Object Map, Spoolman & Quote Calculator)
with a native Qt Desktop Bridge (native OS file/folder dialogs, 1-click Slicer launch,
system tray notifications, and a persistent-cookie multi-tab 3D Model Web Browser).
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QKeySequence, QShortcut
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import library
from .pages import S, models_dir
from .server import create_http_server

def _resolve_icon() -> Path:
    local = Path(__file__).with_name("icon.svg")
    if local.exists():
        return local
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        cand = Path(meipass) / "printboard" / "icon.svg"
        if cand.exists():
            return cand
    return local


ICON = _resolve_icon()

STATE_LABELS = {
    "printing": "Druck läuft",
    "paused": "Pausiert",
    "complete": "Abgeschlossen",
    "error": "Fehler",
    "cancelled": "Abgebrochen",
    "standby": "Bereit",
}

SITES = [
    ("Printables", "https://www.printables.com"),
    ("MakerWorld", "https://makerworld.com"),
    ("Thingiverse", "https://www.thingiverse.com"),
    ("Thangs", "https://thangs.com"),
    ("MyMiniFactory", "https://www.myminifactory.com"),
    ("Cults3D", "https://cults3d.com"),
]

BROWSER_QSS = """
QWidget#browser_root {
    background: #05080F;
    color: #F8FAFC;
    font-family: "Inter", "Segoe UI", sans-serif;
}
QFrame#browser_bar {
    background: #090E18;
    border-bottom: 1px solid #1E2D48;
}
QPushButton {
    background: #141F33;
    border: 1px solid #223352;
    color: #F8FAFC;
    border-radius: 8px;
    padding: 7px 14px;
    font-size: 12.5px;
    font-weight: 700;
}
QPushButton:hover {
    background: #1A2842;
    border-color: #00E5FF;
}
QPushButton#back_studio {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00E5FF, stop:1 #3B82F6);
    color: #031017;
    border: none;
    font-weight: 800;
}
QPushButton#lib_btn {
    background: rgba(16, 185, 129, 0.16);
    color: #10B981;
    border: 1px solid rgba(16, 185, 129, 0.4);
}
QPushButton#lib_btn:hover {
    background: rgba(16, 185, 129, 0.28);
}
QLabel#dl_status {
    color: #94A3B8;
    font-size: 12px;
    font-weight: 600;
}
QTabWidget::pane {
    border: none;
    background: #05080F;
}
QTabBar::tab {
    background: #0E1523;
    color: #94A3B8;
    border: 1px solid #1E2D48;
    border-bottom: none;
    padding: 8px 18px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-size: 12.5px;
    font-weight: 700;
}
QTabBar::tab:selected {
    background: #141F33;
    color: #00E5FF;
    border-color: #00E5FF;
}
"""


class DesktopBridge(QObject):
    """Thread-safe bridge from HTTP server threads to the main Qt GUI thread."""
    invoke_requested = Signal(object)

    def __init__(self, win: "Main"):
        super().__init__(win)
        self.win = win
        self.invoke_requested.connect(self._handle_on_main_thread, Qt.QueuedConnection)

    def invoke(self, action: str, payload: dict | None = None):
        req = dict(payload or {})
        req["action"] = action
        return self.call(req)

    def call(self, payload: dict):
        if threading.current_thread() is threading.main_thread():
            return self._execute(payload)
        box = {"payload": payload, "result": None, "event": threading.Event()}
        self.invoke_requested.emit(box)
        box["event"].wait(timeout=180.0)
        return box["result"]

    def _handle_on_main_thread(self, box: dict):
        try:
            box["result"] = self._execute(box["payload"])
        except Exception as e:
            box["result"] = {"ok": False, "error": str(e)}
        finally:
            box["event"].set()

    def _execute(self, payload: dict):
        action = payload.get("action") or ""
        if action == "pick_gcode":
            start_dir = models_dir()
            path, _ = QFileDialog.getOpenFileName(
                self.win,
                "G-Code oder 3MF Druckdatei auswählen",
                start_dir,
                "Druckdateien (*.gcode *.gco *.g *.3mf);;Alle Dateien (*)",
            )
            return path or ""

        if action == "pick_folder":
            start_dir = models_dir()
            folder = QFileDialog.getExistingDirectory(
                self.win,
                "Modell- & G-Code-Bibliotheksordner wählen",
                start_dir,
            )
            if folder:
                Path(folder).mkdir(parents=True, exist_ok=True)
                S().setValue("models", folder)
                return folder
            return ""

        if action == "open_folder":
            target = payload.get("path") or models_dir()
            p = Path(target)
            folder = p if p.is_dir() else p.parent
            folder.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
            return str(folder)

        if action == "import_files":
            files, _ = QFileDialog.getOpenFileNames(
                self.win,
                "3D-Modelle, Archive oder G-Code in Bibliothek importieren",
                str(Path.home()),
                "3D-Druck Dateien (*.stl *.3mf *.step *.stp *.obj *.gcode *.gco *.zip);;Alle Dateien (*)",
            )
            if files:
                imported = library.import_files(files, models_dir())
                return {"ok": True, "imported": len(imported)}
            return {"ok": False, "imported": 0}

        if action == "open_model_browser":
            url = payload.get("url") or "https://www.printables.com"
            self.win.open_model_browser(url)
            return {"ok": True, "url": url}

        return {"ok": False, "error": f"Unbekannte Desktop-Aktion: {action}"}


class ModelBrowserDock(QWidget):
    """Docked multi-tab 3D model platform browser with persistent cookies and 1-click download capture."""

    def __init__(self, win: "Main"):
        super().__init__(win)
        self.win = win
        self.setObjectName("browser_root")
        self.setStyleSheet(BROWSER_QSS)

        bar = QFrame()
        bar.setObjectName("browser_bar")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(16, 10, 16, 10)
        bl.setSpacing(10)

        btn_studio = QPushButton("← Zurück zu PrintBoard Studio")
        btn_studio.setObjectName("back_studio")
        btn_studio.setCursor(Qt.PointingHandCursor)
        btn_studio.clicked.connect(self.win.show_studio)

        b_back = QPushButton("◀")
        b_fwd = QPushButton("▶")
        b_rel = QPushButton("↻ Neu laden")
        for b in (b_back, b_fwd, b_rel):
            b.setCursor(Qt.PointingHandCursor)
        b_back.clicked.connect(lambda: self.current_view().back() if self.current_view() else None)
        b_fwd.clicked.connect(lambda: self.current_view().forward() if self.current_view() else None)
        b_rel.clicked.connect(lambda: self.current_view().reload() if self.current_view() else None)

        self.dl_status = QLabel(f"Zielordner für 1-Klick-Downloads: {models_dir()}")
        self.dl_status.setObjectName("dl_status")

        btn_lib = QPushButton("Downloads in 3D-Bibliothek öffnen")
        btn_lib.setObjectName("lib_btn")
        btn_lib.setCursor(Qt.PointingHandCursor)
        btn_lib.clicked.connect(self.win.open_library_in_studio)

        bl.addWidget(btn_studio)
        bl.addSpacing(8)
        bl.addWidget(b_back)
        bl.addWidget(b_fwd)
        bl.addWidget(b_rel)
        bl.addSpacing(12)
        bl.addWidget(self.dl_status, 1)
        bl.addWidget(btn_lib)

        app_inst = QApplication.instance()
        self.profile = QWebEngineProfile("printboard_models", app_inst or self)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        self.profile.downloadRequested.connect(self.on_download)

        self.tabs = QTabWidget()
        self._views: list[tuple[QWebEngineView, QWebEnginePage, str]] = []
        self._loaded_tabs: set[int] = set()

        for name, url in SITES:
            page = QWebEnginePage(self.profile, self)
            page.setBackgroundColor(QColor("#05080F"))
            view = QWebEngineView()
            view.setPage(page)
            self._views.append((view, page, url))
            self.tabs.addTab(view, name)

        self.tabs.currentChanged.connect(self._ensure_tab_loaded)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(bar)
        layout.addWidget(self.tabs, 1)

    def _ensure_tab_loaded(self, idx: int):
        if 0 <= idx < len(self._views) and idx not in self._loaded_tabs:
            self._loaded_tabs.add(idx)
            view, _, url = self._views[idx]
            view.load(QUrl(url))

    def open_url(self, target_url: str):
        self.dl_status.setText(f"Zielordner für 1-Klick-Downloads: {models_dir()}")
        target_lower = (target_url or "").lower()
        for idx, (_, _, default_url) in enumerate(self._views):
            domain = default_url.split("//")[-1].split("/")[0].replace("www.", "")
            if domain in target_lower:
                self.tabs.setCurrentIndex(idx)
                self._ensure_tab_loaded(idx)
                if target_url != default_url:
                    self._views[idx][0].load(QUrl(target_url))
                return
        self._ensure_tab_loaded(0)
        self.tabs.setCurrentIndex(0)
        if target_url:
            self._views[0][0].load(QUrl(target_url))

    def current_view(self) -> QWebEngineView | None:
        w = self.tabs.currentWidget()
        return w if isinstance(w, QWebEngineView) else None

    def on_download(self, dl):
        folder = Path(models_dir())
        folder.mkdir(parents=True, exist_ok=True)
        fname = dl.downloadFileName()
        dl.setDownloadDirectory(str(folder))
        dl.accept()
        self.dl_status.setText(f"⬇ Download läuft: {fname} → {folder}")
        dl.isFinishedChanged.connect(lambda: self.on_download_finished(fname, folder))

    def on_download_finished(self, fname: str, folder: Path):
        self.dl_status.setText(f"✓ Gespeichert in 3D-Bibliothek: {fname}")
        if self.win and hasattr(self.win, "tray"):
            self.win.tray.showMessage(
                "3D-Modell heruntergeladen",
                f"{fname} wurde automatisch in deiner 3D-Bibliothek ({folder.name}) gespeichert.",
                QSystemTrayIcon.Information,
                6000,
            )


class _PopupInterceptorPage(QWebEnginePage):
    """Intercepts target='_blank' / window.open() URLs from the 1:1 WebUI."""

    def __init__(self, win: "Main"):
        super().__init__(win)
        self.win = win
        self.urlChanged.connect(self._on_url)

    def _on_url(self, url: QUrl):
        s = url.toString()
        if not s or s == "about:blank":
            return
        low = s.lower()
        if any(dom in low for _, dom in SITES) or any(
            d in low for d in ("printables.com", "makerworld.com", "thingiverse.com", "thangs.com", "myminifactory.com", "cults3d.com")
        ):
            self.win.open_model_browser(s)
        else:
            QDesktopServices.openUrl(url)
        self.deleteLater()


class StudioWebPage(QWebEnginePage):
    """Custom WebEnginePage for the standalone 1:1 WebUI window."""

    def __init__(self, win: "Main"):
        super().__init__(win)
        self.win = win
        self.setBackgroundColor(QColor("#05080F"))

    def createWindow(self, _type):
        return _PopupInterceptorPage(self.win)


class Main(QMainWindow):
    """PrintBoard Studio 1.0 Main Standalone Window (Embedded Server + 1:1 WebUI Client)."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PrintBoard Studio 1.0")
        self.resize(1460, 900)
        self.setMinimumSize(1020, 680)
        self.setStyleSheet("QMainWindow { background: #05080F; }")

        # 1. Start embedded local HTTP/REST telemetry & control server
        self.bridge = DesktopBridge(self)
        self.httpd, self.engine = create_http_server(port=0, host="127.0.0.1", desktop_bridge=self.bridge)
        self.server_port = self.httpd.server_port
        self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.server_thread.start()

        # 2. Central Stacked Widget (Page 0: 1:1 WebUI Client, Page 1: Native 3D Model Browser Dock)
        self.stack = QStackedWidget(self)
        self.setCentralWidget(self.stack)

        self.studio_view = QWebEngineView(self)
        self.studio_page = StudioWebPage(self)
        self.studio_view.setPage(self.studio_page)
        settings = self.studio_view.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, True)
        settings.setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, True)

        self.model_browser = ModelBrowserDock(self)

        self.stack.addWidget(self.studio_view)
        self.stack.addWidget(self.model_browser)

        self.studio_view.load(QUrl(f"http://127.0.0.1:{self.server_port}/"))

        # 3. System Tray & Native Desktop Notifications
        self._last_states: dict[str, str] = {}
        self.tray = QSystemTrayIcon(QIcon(str(ICON)), self)
        self.tray.setToolTip("PrintBoard Studio 1.0")
        self.tray.show()

        self.notify_timer = QTimer(self)
        self.notify_timer.timeout.connect(self._check_printer_notifications)
        self.notify_timer.start(3000)

        # F11 Fullscreen toggle shortcut
        sc_fs = QShortcut(QKeySequence("F11"), self)
        sc_fs.activated.connect(self._toggle_fullscreen)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def open_model_browser(self, url: str = "https://www.printables.com"):
        self.model_browser.open_url(url)
        self.stack.setCurrentWidget(self.model_browser)

    def show_studio(self):
        self.stack.setCurrentWidget(self.studio_view)

    def open_library_in_studio(self):
        self.stack.setCurrentWidget(self.studio_view)
        self.studio_view.page().runJavaScript(
            "if (window.navigatePrintBoard) { window.navigatePrintBoard('library'); }"
        )

    def _check_printer_notifications(self):
        try:
            engine = self.engine
            printers = engine.get_effective_printers()
            with engine.lock:
                statuses = dict(engine.statuses)
            for p in printers:
                r = statuses.get(p.id) or {}
                new_state = None if "error" in r else r.get("state")
                old_state = self._last_states.get(p.id)
                self._last_states[p.id] = new_state
                if not old_state or not new_state or old_state == new_state:
                    continue
                if old_state in ("printing", "paused") and new_state in ("complete", "error", "cancelled"):
                    self.tray.showMessage(
                        p.name,
                        f"{STATE_LABELS.get(new_state, new_state)}: {r.get('filename') or ''}",
                        QSystemTrayIcon.Warning if new_state == "error" else QSystemTrayIcon.Information,
                        8000,
                    )
        except Exception:
            pass

    def closeEvent(self, event):
        try:
            self.notify_timer.stop()
            self.engine.running = False
            self.httpd.shutdown()
            self.httpd.server_close()
        except Exception:
            pass
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("printboard")
    if ICON.exists():
        app.setWindowIcon(QIcon(str(ICON)))
    w = Main()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
