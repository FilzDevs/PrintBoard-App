import os
from pathlib import Path
from PySide6.QtCore import Qt, QObject, QRunnable, QThreadPool, Signal, QSettings, QSize, QUrl, QRectF
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap, QPainter, QColor, QFont, QPen, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox, QTableWidget,
    QTableWidgetItem, QDoubleSpinBox, QFormLayout, QLineEdit, QCheckBox, QListWidget, QListWidgetItem,
    QMessageBox, QInputDialog, QFileDialog, QHeaderView, QFrame, QMenu
)
from . import api, costs, library, notify, spoolman
from .spoolman_ui import SpoolmanPage, make_spool_pixmap
from .ui_theme import DonutRingChart, CHART_PALETTE, make_vector_icon


def S():
    return QSettings("printboard", "printboard")


def spoolman_url():
    return spoolman.normalize_url(S().value("spoolman_url", ""))


def set_spoolman_url(url):
    S().setValue("spoolman_url", spoolman.normalize_url(url))


def local_printer_spool(pid):
    val = S().value(f"printer_spool/{pid}", 0)
    try:
        v = int(val)
        return v if v > 0 else None
    except Exception:
        return None


def set_local_printer_spool(pid, sid):
    S().setValue(f"printer_spool/{pid}", int(sid) if sid else 0)


def models_dir():
    d = str(S().value("models", str(Path.home() / "3D-Models")))
    Path(d).mkdir(parents=True, exist_ok=True)
    return d


def slicer_cmd():
    return str(S().value("slicer_cmd", ""))


class Bus(QObject):
    res = Signal(object)


class Task(QRunnable):
    def __init__(self, fn, bus):
        super().__init__()
        self.fn, self.bus = fn, bus

    def run(self):
        try:
            out = ("ok", self.fn())
        except Exception as e:
            out = ("err", str(e))
        try:
            self.bus.res.emit(out)
        except RuntimeError:
            pass


def run_async(fn, cb):
    bus = Bus()
    bus.res.connect(cb)
    bus._keep = bus
    QThreadPool.globalInstance().start(Task(fn, bus))
    return bus


def h1(t):
    l = QLabel(t)
    l.setObjectName("h1")
    return l


def make_badge_pixmap(ext, size=120):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    colors = {
        ".stl": ("#162a40", "#38bdf8", "STL"),
        ".3mf": ("#152e2b", "#34d399", "3MF"),
        ".gcode": ("#2b2118", "#fb923c", "GCODE"),
        ".step": ("#261c38", "#c084fc", "STEP"),
        ".stp": ("#261c38", "#c084fc", "STEP"),
        ".obj": ("#1e293b", "#94a3b8", "OBJ"),
        ".zip": ("#2d2318", "#facc15", "ZIP"),
    }
    bg, fg, label = colors.get(ext.lower(), ("#162231", "#8198af", ext.upper().lstrip(".")))
    p.setBrush(QBrush(QColor(bg)))
    p.setPen(QPen(QColor(fg), 2))
    p.drawRoundedRect(QRectF(8, 8, size - 16, size - 16), 14, 14)
    p.setPen(QColor(fg))
    f = QFont("Sans Serif", 15 if len(label) <= 4 else 12, QFont.Bold)
    p.setFont(f)
    p.drawText(QRectF(8, 8, size - 16, size - 16), Qt.AlignCenter, label)
    p.end()
    return pm



class MonthlyChart(QFrame):
    """Colored bar chart of monthly print hours."""
    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        self.setMinimumHeight(175)
        self.data = {}

    def set_data(self, per_month):
        self.data = dict(sorted((per_month or {}).items())[-12:])
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        p.setPen(QColor("#94A3B8"))
        p.setFont(QFont("Inter", 9, QFont.Bold))
        p.drawText(14, 21, "DRUCKSTUNDEN PRO MONAT")

        if not self.data:
            p.setPen(QColor("#64748B"))
            p.setFont(QFont("Inter", 10))
            p.drawText(QRectF(0, 30, w, h - 30), Qt.AlignCenter, "Noch keine Monatsdaten verfügbar")
            return

        items = list(self.data.items())
        max_val = max(v for _, v in items) or 1.0
        left, right, top, bottom = 20, 20, 42, 30
        avail_w = max(100, w - left - right)
        avail_h = max(40, h - top - bottom)
        n = len(items)
        slot_w = avail_w / n
        bar_w = min(44.0, max(14.0, slot_w * 0.56))

        p.setPen(QPen(QColor("#1B2638"), 1))
        p.drawLine(left, top + avail_h, w - right, top + avail_h)

        for i, (month, val) in enumerate(items):
            cx = left + (i + 0.5) * slot_w
            bh = max(5.0, (val / max_val) * (avail_h - 18))
            bx = cx - bar_w / 2
            by = top + avail_h - bh

            col = QColor(CHART_PALETTE[i % len(CHART_PALETTE)])
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(col))
            p.drawRoundedRect(QRectF(bx, by, bar_w, bh), 5, 5)

            p.setPen(QColor("#E2E8F0"))
            p.setFont(QFont("Inter", 8.5, QFont.Bold))
            p.drawText(QRectF(cx - slot_w / 2, by - 17, slot_w, 15), Qt.AlignCenter, f"{val:.1f}h")

            p.setPen(QColor("#8799B0"))
            p.setFont(QFont("Inter", 8.5))
            short_m = month[2:] if len(month) == 7 else month
            p.drawText(QRectF(cx - slot_w / 2, top + avail_h + 5, slot_w, 18), Qt.AlignCenter, short_m)


class Stats(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.combo = QComboBox()
        self.combo.setMinimumWidth(190)
        self.combo.currentIndexChanged.connect(self.load)
        go = QPushButton("Aktualisieren")
        go.setIcon(make_vector_icon("refresh", "#8799B0", 14))
        go.clicked.connect(self.load)

        top = QHBoxLayout()
        top.addWidget(h1("Statistik, Auswertung & Kosten"))
        top.addStretch()
        top.addWidget(QLabel("Drucker:"))
        top.addWidget(self.combo)
        top.addWidget(go)

        self.kpi_labels = {}
        kpi_row = QHBoxLayout()
        kpi_colors = {
            "count": "#06B6D4",
            "success": "#10B981",
            "hours": "#8B5CF6",
            "filament": "#F59E0B",
            "cost": "#F43F5E",
        }
        for key, title in (
            ("count", "DRUCKAUFTRÄGE"),
            ("success", "ERFOLGSQUOTE"),
            ("hours", "GESAMTDAUER"),
            ("filament", "FILAMENT"),
            ("cost", "GESAMTKOSTEN"),
        ):
            c = QFrame()
            c.setObjectName("card")
            cl = QVBoxLayout(c)
            cl.setContentsMargins(14, 10, 14, 10)
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("font-size:10px;font-weight:800;color:#8799B0;letter-spacing:0.6px")
            v_lbl = QLabel("—")
            v_lbl.setStyleSheet(f"font-size:19px;font-weight:800;color:{kpi_colors[key]}")
            cl.addWidget(t_lbl)
            cl.addWidget(v_lbl)
            self.kpi_labels[key] = v_lbl
            kpi_row.addWidget(c)

        param_card = QFrame()
        param_card.setObjectName("card")
        param_layout = QHBoxLayout(param_card)
        param_layout.setContentsMargins(14, 10, 14, 10)
        self.fil, self.w, self.kwh, self.wear = (QDoubleSpinBox() for _ in range(4))
        for sp, v, mx, label in (
            (self.fil, 25.0, 500.0, "Filament (€/kg):"),
            (self.w, 150.0, 3000.0, "Leistung (W):"),
            (self.kwh, 0.30, 5.0, "Strom (€/kWh):"),
            (self.wear, 0.10, 50.0, "Verschleiß (€/h):"),
        ):
            sp.setRange(0, mx)
            sp.setValue(v)
            sp.setDecimals(2)
            sp.valueChanged.connect(self.fill)
            param_layout.addWidget(QLabel(label))
            param_layout.addWidget(sp)
        self.spool_combo = QComboBox()
        self.spool_combo.setMinimumWidth(190)
        self.spool_combo.addItem("Manueller Preis", None)
        self.spool_combo.currentIndexChanged.connect(self.on_spool_price_selected)
        param_layout.addWidget(QLabel("Spoolman-Spule:"))
        param_layout.addWidget(self.spool_combo)
        param_layout.addStretch()

        charts_row = QHBoxLayout()
        charts_row.setSpacing(12)
        self.chart = MonthlyChart()
        self.outcome_donut = DonutRingChart("DRUCKSTATUS-VERTEILUNG", height=175)
        self.cost_donut = DonutRingChart("KOSTENAUFTEILUNG (EUR)", height=175)
        charts_row.addWidget(self.chart, 2)
        charts_row.addWidget(self.outcome_donut, 1)
        charts_row.addWidget(self.cost_donut, 1)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Datei", "Status", "Dauer", "Filament", "Kosten"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)

        self.spool = QLabel("Spoolman: —")
        self.spool.setObjectName("dim")

        l = QVBoxLayout(self)
        l.setSpacing(12)
        l.addLayout(top)
        l.addLayout(kpi_row)
        l.addWidget(param_card)
        l.addLayout(charts_row)
        l.addWidget(self.table, 1)
        l.addWidget(self.spool)
        self.jobs = []
        self._sm_spools = []

    def showEvent(self, e):
        self.combo.blockSignals(True)
        self.combo.clear()
        for p in self.win.printers:
            self.combo.addItem(p.name, p.id)
        self.combo.blockSignals(False)
        if self.win.printers:
            self.load()

    def load(self):
        p = next((x for x in self.win.printers if x.id == self.combo.currentData()), None)
        if not p:
            return
        self.kpi_labels["count"].setText("…")
        run_async(lambda: api.history(p), self.got)
        sm_url = spoolman_url()
        run_async(
            lambda: spoolman.list_spools(sm_url or spoolman.discover_url(self.win.printers), allow_archived=False),
            self.got_spools,
        )

    def got(self, r):
        if r[0] == "err":
            self.kpi_labels["count"].setText("Fehler")
            return
        self.jobs = r[1]
        self.fill()

    def got_spools(self, r):
        if r[0] == "ok" and r[1]:
            self._sm_spools = r[1]
            self.spool_combo.blockSignals(True)
            self.spool_combo.clear()
            self.spool_combo.addItem("Manueller Preis", None)
            for s in r[1]:
                pr = spoolman.spool_price(s)
                init_g = spoolman.spool_initial_weight(s)
                eur_kg = (pr / (init_g / 1000.0)) if (pr is not None and init_g > 0) else None
                lbl = f"{spoolman.spool_display_name(s)} ({float(s.get('remaining_weight') or 0):.0f} g)"
                if eur_kg is not None:
                    lbl += f" – {eur_kg:.2f} €/kg"
                self.spool_combo.addItem(lbl, eur_kg)
            self.spool_combo.blockSignals(False)
            self.spool.setText(
                "Spoolman aktiv: "
                + ", ".join(
                    f"{(s.get('filament') or {}).get('name', '?')} ({float(s.get('remaining_weight') or 0):.0f} g)"
                    for s in r[1][:8]
                )
            )
        else:
            self.spool.setText("Spoolman: nicht verbunden")

    def on_spool_price_selected(self):
        eur_kg = self.spool_combo.currentData()
        if eur_kg is not None and eur_kg > 0:
            self.fil.setValue(float(eur_kg))

    def fill(self):
        st = costs.stats(self.jobs, self.fil.value(), self.kwh.value(), self.w.value())
        total = 0.0
        mat_sum = 0.0
        pwr_sum = 0.0
        wear_sum = 0.0
        ok_cnt = 0
        cancel_cnt = 0
        err_cnt = 0
        self.table.setRowCount(len(self.jobs))
        for i, j in enumerate(self.jobs):
            g = costs.mm_to_g(j.get("filament_used"))
            sec = j.get("total_duration") or 0
            h_job = sec / 3600.0
            m_c = (g / 1000.0) * self.fil.value()
            p_c = h_job * (self.w.value() / 1000.0) * self.kwh.value()
            w_c = h_job * self.wear.value()
            c = m_c + p_c + w_c
            total += c
            mat_sum += m_c
            pwr_sum += p_c
            wear_sum += w_c
            st_str = j.get("status", "")
            if st_str == "completed":
                ok_cnt += 1
            elif "cancel" in st_str:
                cancel_cnt += 1
            else:
                err_cnt += 1
            for k, v in enumerate((j.get("filename", ""), st_str, f"{h_job:.1f} h", f"{g:.0f} g", f"{c:.2f} €")):
                self.table.setItem(i, k, QTableWidgetItem(v))
        self.kpi_labels["count"].setText(str(st["count"]))
        self.kpi_labels["success"].setText(f"{st['success']:.0f}%")
        self.kpi_labels["hours"].setText(f"{st['hours']:.1f} h")
        self.kpi_labels["filament"].setText(f"{st['filament_g'] / 1000:.2f} kg")
        self.kpi_labels["cost"].setText(f"{total:.2f} €")
        self.chart.set_data(st.get("per_month", {}))
        self.outcome_donut.set_segments(
            [
                ("Erfolgreich", ok_cnt, "#10B981", str(ok_cnt)),
                ("Abgebrochen", cancel_cnt, "#F59E0B", str(cancel_cnt)),
                ("Fehlgeschlagen", err_cnt, "#F43F5E", str(err_cnt)),
            ],
            f"{st['success']:.0f}%",
            "ERFOLG",
        )
        self.cost_donut.set_segments(
            [
                ("Material", max(0.01, mat_sum), "#06B6D4", f"{mat_sum:.2f} €"),
                ("Strom", max(0.01, pwr_sum), "#8B5CF6", f"{pwr_sum:.2f} €"),
                ("Verschleiß", max(0.01, wear_sum), "#F59E0B", f"{wear_sum:.2f} €"),
            ],
            f"{total:.1f}€",
            "GESAMT",
        )



class Library(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win

        # Top header
        top = QHBoxLayout()
        top.addWidget(h1("Modell- & Datei-Bibliothek"))
        top.addStretch()
        self.folder_lbl = QLabel()
        self.folder_lbl.setObjectName("dim")
        btn_open_dir = QPushButton("Ordner öffnen")
        btn_open_dir.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(models_dir())))
        btn_import = QPushButton("+ Dateien importieren")
        btn_import.clicked.connect(self.import_external)
        btn_new_folder = QPushButton("+ Neuer Unterordner")
        btn_new_folder.clicked.connect(self.create_subfolder)
        top.addWidget(self.folder_lbl)
        top.addWidget(btn_open_dir)
        top.addWidget(btn_new_folder)
        top.addWidget(btn_import)

        # Filter bar
        fbar = QHBoxLayout()
        self.q = QLineEdit()
        self.q.setPlaceholderText("Dateiname suchen …")
        self.q.textChanged.connect(self.refresh)

        self.cat_combo = QComboBox()
        self.cat_combo.addItem("Alle Dateitypen", "all")
        self.cat_combo.addItem("3D-Modelle (.3mf, .stl, .step, .obj)", "models")
        self.cat_combo.addItem("G-Code (.gcode)", "gcode")
        self.cat_combo.addItem("ZIP-Archive (.zip)", "archives")
        self.cat_combo.currentIndexChanged.connect(self.refresh)

        self.sub_combo = QComboBox()
        self.sub_combo.setMinimumWidth(160)
        self.sub_combo.currentIndexChanged.connect(self.refresh)

        btn_refresh = QPushButton("Aktualisieren")
        btn_refresh.setIcon(make_vector_icon("refresh", "#8799B0", 14))
        btn_refresh.clicked.connect(self.reload_all)

        fbar.addWidget(self.q, 2)
        fbar.addWidget(QLabel("Typ:"))
        fbar.addWidget(self.cat_combo)
        fbar.addWidget(QLabel("Ordner:"))
        fbar.addWidget(self.sub_combo)
        fbar.addWidget(btn_refresh)

        # File Grid
        self.list = QListWidget()
        self.list.setViewMode(QListWidget.IconMode)
        self.list.setIconSize(QSize(115, 115))
        self.list.setResizeMode(QListWidget.Adjust)
        self.list.setGridSize(QSize(168, 172))
        self.list.setWordWrap(True)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self.context_menu)
        self.list.currentItemChanged.connect(self.update_inspector)
        self.list.itemDoubleClicked.connect(self.on_double_click)

        # Right-hand Inspector & File Actions Card
        self.inspector = QFrame()
        self.inspector.setObjectName("card")
        self.inspector.setFixedWidth(310)
        il = QVBoxLayout(self.inspector)
        il.setSpacing(8)

        self.prev_img = QLabel("Keine Datei ausgewählt")
        self.prev_img.setAlignment(Qt.AlignCenter)
        self.prev_img.setFixedHeight(180)
        self.prev_img.setStyleSheet("background:#0b121c;border:1px solid #1e2f44;border-radius:10px;color:#8198af")

        self.info_name = QLabel("—")
        self.info_name.setWordWrap(True)
        self.info_name.setStyleSheet("font-size:15px;font-weight:700")
        self.info_meta = QLabel("")
        self.info_meta.setWordWrap(True)
        self.info_meta.setObjectName("dim")

        self.btn_slicer = QPushButton("Im Slicer öffnen")
        self.btn_slicer.setObjectName("primary")
        self.btn_slicer.clicked.connect(self.open_slicer)

        self.btn_send = QPushButton("An Drucker senden …")
        self.btn_send.setObjectName("primary")
        self.btn_send.clicked.connect(self.send)

        self.btn_unzip = QPushButton("ZIP-Archiv entpacken")
        self.btn_unzip.setObjectName("primary")
        self.btn_unzip.clicked.connect(self.unzip_selected)

        self.btn_rename = QPushButton("Umbenennen …")
        self.btn_rename.clicked.connect(self.rename_selected)

        self.btn_dup = QPushButton("Duplizieren")
        self.btn_dup.clicked.connect(self.duplicate_selected)

        self.btn_move = QPushButton("In Ordner verschieben …")
        self.btn_move.clicked.connect(self.move_selected)

        self.btn_reveal = QPushButton("Speicherort öffnen")
        self.btn_reveal.clicked.connect(self.reveal_selected)

        self.btn_delete = QPushButton("Datei löschen")
        self.btn_delete.setObjectName("danger")
        self.btn_delete.clicked.connect(self.delete_selected)

        il.addWidget(self.prev_img)
        il.addWidget(self.info_name)
        il.addWidget(self.info_meta)
        il.addSpacing(6)
        for b in (
            self.btn_slicer, self.btn_send, self.btn_unzip,
            self.btn_rename, self.btn_dup, self.btn_move, self.btn_reveal, self.btn_delete
        ):
            il.addWidget(b)
        il.addStretch()

        body = QHBoxLayout()
        body.addWidget(self.list, 1)
        body.addWidget(self.inspector)

        l = QVBoxLayout(self)
        l.setSpacing(10)
        l.addLayout(top)
        l.addLayout(fbar)
        l.addLayout(body, 1)

        self.update_inspector(None)

    def showEvent(self, e):
        self.reload_all()

    def reload_all(self):
        root = models_dir()
        self.folder_lbl.setText(f"Ordner: {root}")
        cur_sub = self.sub_combo.currentData() or ""
        self.sub_combo.blockSignals(True)
        self.sub_combo.clear()
        self.sub_combo.addItem("Alle Ordner", "")
        for sf in library.list_subfolders(root):
            self.sub_combo.addItem(f"{sf}", sf)
        idx = self.sub_combo.findData(cur_sub)
        if idx >= 0:
            self.sub_combo.setCurrentIndex(idx)
        self.sub_combo.blockSignals(False)
        self.refresh()

    def refresh(self):
        self.list.clear()
        root = models_dir()
        cat = self.cat_combo.currentData() or "all"
        sub = self.sub_combo.currentData() or ""
        for f in library.scan(root, self.q.text(), category=cat, subfolder=sub)[:400]:
            it = QListWidgetItem(f.name)
            it.setData(Qt.UserRole, str(f))
            png = library.thumbnail(f)
            if png:
                pm = QPixmap()
                pm.loadFromData(png)
                it.setIcon(QIcon(pm))
            else:
                it.setIcon(QIcon(make_badge_pixmap(f.suffix)))
            self.list.addItem(it)
        self.update_inspector(self.list.currentItem())

    def current_path(self):
        it = self.list.currentItem()
        return Path(it.data(Qt.UserRole)) if it else None

    def update_inspector(self, item):
        if not item:
            self.prev_img.setPixmap(QPixmap())
            self.prev_img.setText("Keine Datei ausgewählt")
            self.info_name.setText("—")
            self.info_meta.setText("Wähle links eine Datei aus, um Details zu sehen oder sie zu verwalten.")
            for b in (
                self.btn_slicer, self.btn_send, self.btn_unzip,
                self.btn_rename, self.btn_dup, self.btn_move, self.btn_reveal, self.btn_delete
            ):
                b.setEnabled(False)
            return

        p = Path(item.data(Qt.UserRole))
        if not p.exists():
            return
        details = library.file_details(p)
        png = library.thumbnail(p)
        if png:
            pm = QPixmap()
            pm.loadFromData(png)
            self.prev_img.setPixmap(pm.scaled(270, 170, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.prev_img.setPixmap(make_badge_pixmap(p.suffix, 130))

        self.info_name.setText(details["name"])
        try:
            rel_dir = str(p.parent.relative_to(models_dir()))
        except ValueError:
            rel_dir = str(p.parent)
        lines = [
            f"Größe: {details['size']}",
            f"Geändert: {details['modified']}",
            f"Ordner: {'Hauptordner' if rel_dir == '.' else rel_dir}",
        ]
        for k, v in details["meta"].items():
            lines.append(f"{k}: {v}")
        self.info_meta.setText("\n".join(lines))

        ext = details["ext"]
        self.btn_slicer.setEnabled(ext in {".3mf", ".stl", ".obj", ".step", ".stp"})
        self.btn_send.setEnabled(ext == ".gcode")
        self.btn_unzip.setEnabled(ext == ".zip")
        for b in (self.btn_rename, self.btn_dup, self.btn_move, self.btn_reveal, self.btn_delete):
            b.setEnabled(True)

    def on_double_click(self, item):
        p = Path(item.data(Qt.UserRole))
        ext = p.suffix.lower()
        if ext in {".3mf", ".stl", ".obj", ".step", ".stp"}:
            self.open_slicer()
        elif ext == ".gcode":
            self.send()
        elif ext == ".zip":
            self.unzip_selected()

    def context_menu(self, pos):
        it = self.list.itemAt(pos)
        if not it:
            return
        self.list.setCurrentItem(it)
        p = Path(it.data(Qt.UserRole))
        ext = p.suffix.lower()
        m = QMenu(self)
        a_slice = m.addAction("Im Slicer öffnen") if ext in {".3mf", ".stl", ".obj", ".step", ".stp"} else None
        a_send = m.addAction("An Drucker senden …") if ext == ".gcode" else None
        a_unzip = m.addAction("ZIP-Archiv entpacken") if ext == ".zip" else None
        m.addSeparator()
        a_ren = m.addAction("Umbenennen …")
        a_dup = m.addAction("Duplizieren")
        a_mov = m.addAction("In Ordner verschieben …")
        a_rev = m.addAction("Speicherort öffnen")
        m.addSeparator()
        a_del = m.addAction("Löschen")
        chosen = m.exec(self.list.mapToGlobal(pos))
        if not chosen:
            return
        if chosen == a_slice:
            self.open_slicer()
        elif chosen == a_send:
            self.send()
        elif chosen == a_unzip:
            self.unzip_selected()
        elif chosen == a_ren:
            self.rename_selected()
        elif chosen == a_dup:
            self.duplicate_selected()
        elif chosen == a_mov:
            self.move_selected()
        elif chosen == a_rev:
            self.reveal_selected()
        elif chosen == a_del:
            self.delete_selected()

    def open_slicer(self):
        p = self.current_path()
        if not p:
            return
        try:
            used = library.open_in_slicer(p, slicer_cmd())
            if hasattr(self.win, "statusBar"):
                self.win.statusBar().showMessage(f"„{p.name}“ wurde in {used} geöffnet.", 5000)
        except Exception as e:
            QMessageBox.warning(self, "Slicer öffnen", str(e))

    def send(self):
        p = self.current_path()
        if not p:
            return
        if not S().value("controls", False, type=bool):
            QMessageBox.information(self, "Gesperrt", "Aktiviere zuerst „Steuerung“ in den Einstellungen.")
            return
        if not self.win.printers:
            QMessageBox.information(self, "Kein Drucker", "Bitte zuerst einen Drucker hinzufügen.")
            return
        if p.suffix.lower() != ".gcode":
            QMessageBox.information(self, "Nur G-Code", "Hochgeladen werden können nur .gcode-Dateien (vorher slicen).")
            return
        name, ok = QInputDialog.getItem(self, "Drucker wählen", "Senden an:", [x.name for x in self.win.printers], 0, False)
        if not ok:
            return
        mode, ok2 = QInputDialog.getItem(
            self,
            "Upload-Modus",
            "Aktion nach dem Hochladen:",
            ["Nur auf Drucker hochladen", "Hochladen & Druck sofort starten"],
            0,
            False,
        )
        if not ok2:
            return
        start_now = mode.startswith("Hochladen &")
        printer = next(x for x in self.win.printers if x.name == name)
        run_async(
            lambda: api.upload(printer, str(p), start=start_now),
            lambda r: QMessageBox.information(
                self,
                "Upload",
                ("Hochgeladen und Druck gestartet!" if start_now else "Erfolgreich hochgeladen.")
                if r[0] == "ok" else "Fehler: " + r[1],
            ),
        )

    def unzip_selected(self):
        p = self.current_path()
        if not p or p.suffix.lower() != ".zip":
            return
        try:
            out_dir, files = library.extract_zip(p)
            self.reload_all()
            QMessageBox.information(
                self,
                "Archiv entpackt",
                f"{len(files)} Modell-/G-Code-Datei(en) wurden nach „{out_dir.name}“ entpackt.",
            )
        except Exception as e:
            QMessageBox.warning(self, "Fehler beim Entpacken", str(e))

    def rename_selected(self):
        p = self.current_path()
        if not p:
            return
        new_name, ok = QInputDialog.getText(self, "Datei umbenennen", "Neuer Dateiname:", text=p.name)
        if ok and new_name.strip():
            try:
                library.rename_file(p, new_name)
                self.reload_all()
            except Exception as e:
                QMessageBox.warning(self, "Umbenennen fehlgeschlagen", str(e))

    def duplicate_selected(self):
        p = self.current_path()
        if not p:
            return
        try:
            library.duplicate_file(p)
            self.reload_all()
        except Exception as e:
            QMessageBox.warning(self, "Duplizieren fehlgeschlagen", str(e))

    def move_selected(self):
        p = self.current_path()
        if not p:
            return
        root = Path(models_dir())
        folders = ["(Hauptordner)"] + library.list_subfolders(root)
        choice, ok = QInputDialog.getItem(self, "Verschieben", "Zielordner auswählen:", folders, 0, False)
        if ok:
            target_dir = root if choice == "(Hauptordner)" else (root / choice)
            try:
                library.move_file(p, target_dir)
                self.reload_all()
            except Exception as e:
                QMessageBox.warning(self, "Verschieben fehlgeschlagen", str(e))

    def reveal_selected(self):
        p = self.current_path()
        if p:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p.parent)))

    def delete_selected(self):
        p = self.current_path()
        if not p:
            return
        if QMessageBox.question(self, "Datei löschen", f"Soll „{p.name}“ wirklich dauerhaft gelöscht werden?") == QMessageBox.Yes:
            try:
                library.delete_file(p)
                self.reload_all()
            except Exception as e:
                QMessageBox.warning(self, "Löschen fehlgeschlagen", str(e))

    def create_subfolder(self):
        name, ok = QInputDialog.getText(self, "Neuer Unterordner", "Ordnername im Modell-Ordner:")
        if ok and name.strip():
            clean = name.strip().strip("/\\")
            target = Path(models_dir()) / clean
            target.mkdir(parents=True, exist_ok=True)
            self.reload_all()

    def import_external(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "3D-Modelle oder G-Code importieren",
            str(Path.home()),
            "3D-Druck-Dateien (*.3mf *.stl *.obj *.step *.stp *.gcode *.zip)",
        )
        if files:
            sub = self.sub_combo.currentData() or ""
            target = Path(models_dir()) / sub if sub else Path(models_dir())
            imported = library.import_files(files, target)
            self.reload_all()
            QMessageBox.information(self, "Importiert", f"{len(imported)} Datei(en) in den Modell-Ordner kopiert.")



class SettingsPage(QWidget):
    settings_changed = Signal()

    def __init__(self, win=None):
        super().__init__()
        self.win = win
        s = S()

        l = QVBoxLayout(self)
        l.setSpacing(14)
        l.addWidget(h1("Einstellungen"))

        # 1. Download & Models Folder Card
        c_dir = QFrame()
        c_dir.setObjectName("card")
        dl = QVBoxLayout(c_dir)
        dl.addWidget(QLabel("<b>Download- & Modell-Ordner</b>"))
        dl.addWidget(QLabel("Alle Downloads aus dem integrierten Modell-Browser und von Druckern landen in diesem Ordner:"))
        row_dir = QHBoxLayout()
        self.models = QLineEdit(models_dir())
        self.models.setReadOnly(True)
        b_pick = QPushButton("Ordner auswählen …")
        b_pick.clicked.connect(self.pick)
        b_open = QPushButton("Im Dateimanager öffnen")
        b_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.models.text())))
        row_dir.addWidget(self.models, 1)
        row_dir.addWidget(b_pick)
        row_dir.addWidget(b_open)
        dl.addLayout(row_dir)
        l.addWidget(c_dir)

        # 2. Slicer Integration Card
        c_slicer = QFrame()
        c_slicer.setObjectName("card")
        sl = QVBoxLayout(c_slicer)
        sl.addWidget(QLabel("<b>Slicer-Direktintegration</b>"))
        detected = library.detect_slicers()
        det_str = ", ".join(f"{lbl} ({cmd[0]})" for lbl, cmd in detected) if detected else "Keiner automatisch im Systempfad erkannt"
        det_lbl = QLabel(f"Automatisch erkannt: {det_str}")
        det_lbl.setObjectName("dim")
        sl.addWidget(det_lbl)
        row_sl = QHBoxLayout()
        self.slicer_input = QLineEdit(s.value("slicer_cmd", ""))
        self.slicer_input.setPlaceholderText("Leer lassen für Automatik oder Befehl/Pfad (z.B. orca-slicer, prusa-slicer …)")
        b_slicer_pick = QPushButton("Programm wählen …")
        b_slicer_pick.clicked.connect(self.pick_slicer)
        row_sl.addWidget(self.slicer_input, 1)
        row_sl.addWidget(b_slicer_pick)
        sl.addLayout(row_sl)
        l.addWidget(c_slicer)

        # 2b. Spoolman Integration Card
        c_sm = QFrame()
        c_sm.setObjectName("card")
        sml = QVBoxLayout(c_sm)
        sml.addWidget(QLabel("<b>Spoolman-Integration (Filament- & Spulenverwaltung)</b>"))
        sm_sub = QLabel("Verbinde deinen Spoolman-Server (oder übernimm ihn automatisch aus der Moonraker-Konfiguration deiner Drucker):")
        sm_sub.setObjectName("dim")
        sml.addWidget(sm_sub)
        row_sm = QHBoxLayout()
        self.sm_url = QLineEdit(spoolman_url())
        self.sm_url.setPlaceholderText("z.B. http://192.168.178.170:7912 (leer = automatische Erkennung)")
        self.b_sm_detect = QPushButton("Automatisch erkennen")
        self.b_sm_detect.clicked.connect(self.detect_spoolman)
        self.b_sm_test = QPushButton("Verbindung testen")
        self.b_sm_test.clicked.connect(self.test_spoolman)
        row_sm.addWidget(self.sm_url, 1)
        row_sm.addWidget(self.b_sm_detect)
        row_sm.addWidget(self.b_sm_test)
        sml.addLayout(row_sm)
        l.addWidget(c_sm)

        # 3. Control Card (Native PC Version: notifications/webhooks are reserved for Server version)
        c_notif = QFrame()
        c_notif.setObjectName("card")
        nl = QVBoxLayout(c_notif)
        nl.addWidget(QLabel("<b>Steuerung & Autostart</b>"))
        
        self.ctl = QCheckBox("Drucker-Steuerung aktivieren (Pause/Abbruch, Not-Aus, Verfahren/Homing, Konsole, Datei-Upload)")
        self.ctl.setChecked(s.value("controls", False, type=bool))
        self.auto = QCheckBox("PrintBoard beim Anmelden automatisch starten")
        self.auto.setChecked(os.path.exists(self.autostart_file()))
        nl.addWidget(self.ctl)
        nl.addWidget(self.auto)

        info_lbl = QLabel("Hinweis: Webhook-Benachrichtigungen (Discord/Telegram) laufen über die PrintBoard Server-Version.")
        info_lbl.setObjectName("dim")
        nl.addWidget(info_lbl)
        l.addWidget(c_notif)

        save = QPushButton("Einstellungen speichern")
        save.setObjectName("primary")
        save.setFixedWidth(240)
        save.clicked.connect(self.save)
        l.addWidget(save)
        l.addStretch()

    @staticmethod
    def autostart_file():
        return str(Path.home() / ".config/autostart/printboard.desktop")

    def pick(self):
        d = QFileDialog.getExistingDirectory(self, "Modell- & Download-Ordner wählen", self.models.text())
        if d:
            Path(d).mkdir(parents=True, exist_ok=True)
            S().setValue("models", d)
            self.models.setText(d)

    def pick_slicer(self):
        f, _ = QFileDialog.getOpenFileName(self, "Slicer-Programm auswählen", "/usr/bin")
        if f:
            self.slicer_input.setText(f)

    def detect_spoolman(self):
        self.b_sm_detect.setEnabled(False)
        self.b_sm_detect.setText("Suche …")
        printers = getattr(self.win, "printers", []) if self.win else []

        def on_done(res):
            self.b_sm_detect.setEnabled(True)
            self.b_sm_detect.setText("Automatisch erkennen")
            if res[0] == "ok" and res[1]:
                self.sm_url.setText(res[1])
                set_spoolman_url(res[1])
                QMessageBox.information(self, "Spoolman erkannt", f"Spoolman-Server gefunden:\n{res[1]}")
            else:
                QMessageBox.warning(self, "Spoolman", "Kein Spoolman-Server automatisch gefunden. Bitte URL manuell eingeben.")

        run_async(lambda: spoolman.discover_url(printers), on_done)

    def test_spoolman(self):
        url = spoolman.normalize_url(self.sm_url.text())
        if not url:
            QMessageBox.warning(self, "Spoolman", "Bitte gib zuerst eine Spoolman Server-URL ein oder klicke auf „Automatisch erkennen“.")
            return
        self.b_sm_test.setEnabled(False)
        self.b_sm_test.setText("Prüfe …")

        def task():
            info = spoolman.get_info(url)
            spools = spoolman.list_spools(url, allow_archived=False)
            return info, len(spools)

        def on_done(res):
            self.b_sm_test.setEnabled(True)
            self.b_sm_test.setText("Verbindung testen")
            if res[0] == "ok":
                info, count = res[1]
                set_spoolman_url(url)
                QMessageBox.information(
                    self,
                    "Spoolman Verbindungstest",
                    f"Erfolgreich verbunden!\n\nVersion: v{info.get('version', '?')}\nAktive Spulen: {count}",
                )
            else:
                QMessageBox.critical(self, "Spoolman Fehler", f"Verbindung fehlgeschlagen:\n\n{res[1]}")

        run_async(task, on_done)

    def test_discord(self):
        url = self.dc.text().strip()
        if not url:
            QMessageBox.warning(self, "Discord Webhook", "Bitte gib zuerst eine Discord Webhook-URL ein.")
            return

        self.b_test_dc.setEnabled(False)
        self.b_test_dc.setText("Sende …")

        def on_done(res):
            self.b_test_dc.setEnabled(True)
            self.b_test_dc.setText("Webhook testen")
            status, payload = res
            if status == "ok":
                QMessageBox.information(
                    self,
                    "Discord Webhook Test",
                    "Test-Nachricht erfolgreich an Discord gesendet!\n\nPrüfe bitte deinen Discord-Kanal."
                )
            else:
                QMessageBox.critical(
                    self,
                    "Discord Webhook Fehler",
                    f"Fehler beim Senden der Nachricht an Discord:\n\n{payload}"
                )

        run_async(lambda: notify.send_discord(url), on_done)

    def save(self):
        s = S()
        d = self.models.text().strip()
        if d:
            Path(d).mkdir(parents=True, exist_ok=True)
            s.setValue("models", d)
        s.setValue("slicer_cmd", self.slicer_input.text().strip())
        set_spoolman_url(self.sm_url.text().strip())
        s.setValue("controls", self.ctl.isChecked())
        f = Path(self.autostart_file())
        if self.auto.isChecked():
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("[Desktop Entry]\nType=Application\nName=PrintBoard\nExec=printboard\nX-GNOME-Autostart-enabled=true\n")
        elif f.exists():
            f.unlink()
        self.settings_changed.emit()
        QMessageBox.information(self, "PrintBoard", "Einstellungen wurden gespeichert.")


def notify_cfg():
    s = S()
    return {"tg_token": s.value("tg_token", ""), "tg_chat": s.value("tg_chat", ""), "discord": s.value("discord", "")}
