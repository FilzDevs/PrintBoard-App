"""Full Spoolman GUI: Spools, Filaments, Vendors, SpoolmanDB Import, Weighing, and Printer/NFC Slot Assignment."""
from PySide6.QtCore import Qt, QRectF, QSize, QUrl, Signal
from PySide6.QtGui import QBrush, QColor, QDesktopServices, QFont, QIcon, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QMenu, QMessageBox, QProgressBar,
    QPushButton, QScrollArea, QSpinBox, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
)

from . import spoolman

MATERIAL_DENSITIES = {
    "PLA": 1.24,
    "PLA+": 1.24,
    "PLA-CF": 1.29,
    "PETG": 1.27,
    "PETG-CF": 1.30,
    "ABS": 1.04,
    "ASA": 1.07,
    "TPU": 1.21,
    "PA": 1.14,
    "PA-CF": 1.20,
    "PC": 1.20,
    "PVA": 1.23,
    "HIPS": 1.04,
    "PP": 0.90,
    "PEI": 1.27,
}

MATERIAL_TEMPS = {
    "PLA": (210, 60),
    "PLA+": (215, 60),
    "PLA-CF": (220, 60),
    "PETG": (240, 75),
    "PETG-CF": (250, 80),
    "ABS": (250, 100),
    "ASA": (255, 100),
    "TPU": (225, 50),
    "PA": (260, 80),
    "PA-CF": (275, 85),
    "PC": (270, 105),
}


def make_spool_pixmap(colors, fill_pct=1.0, size=36, label=""):
    """Render a filament spool icon with single or multi-color fill and remaining level ring."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)

    colors = colors or ["#64748b"]
    fill_pct = max(0.0, min(1.0, float(fill_pct if fill_pct is not None else 1.0)))

    cx, cy = size / 2.0, size / 2.0
    outer_r = size * 0.44
    inner_r = size * 0.18
    fil_r = inner_r + (outer_r - inner_r - 1.5) * (0.22 + 0.78 * fill_pct)

    # Outer spool flange shadow/rim
    p.setPen(QPen(QColor("#334d6b"), max(1.2, size * 0.035)))
    p.setBrush(QBrush(QColor("#0f1926")))
    p.drawEllipse(QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2))

    # Filament winding (single or multi-color gradient)
    if len(colors) == 1:
        c = QColor(colors[0])
        if not c.isValid():
            c = QColor("#64748b")
        p.setBrush(QBrush(c))
    else:
        grad = QLinearGradient(cx - fil_r, cy - fil_r, cx + fil_r, cy + fil_r)
        for i, hex_c in enumerate(colors):
            c = QColor(hex_c)
            if not c.isValid():
                c = QColor("#64748b")
            grad.setColorAt(i / max(1, len(colors) - 1), c)
        p.setBrush(QBrush(grad))

    p.setPen(QPen(QColor("#080d14"), 1.0))
    p.drawEllipse(QRectF(cx - fil_r, cy - fil_r, fil_r * 2, fil_r * 2))

    # Inner hub hole
    p.setBrush(QBrush(QColor("#080d14")))
    p.setPen(QPen(QColor("#2b425e"), max(1.0, size * 0.03)))
    p.drawEllipse(QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2))

    if label and size >= 90:
        p.setPen(QColor("#eaf0fa"))
        p.setFont(QFont("Sans Serif", max(8, int(size * 0.09)), QFont.Bold))
        p.drawText(QRectF(0, cy + outer_r - 18, size, 20), Qt.AlignCenter, label)

    p.end()
    return pm



class VendorDialog(QDialog):
    def __init__(self, parent=None, vendor=None):
        super().__init__(parent)
        self.setWindowTitle("Hersteller bearbeiten" if vendor else "Neuer Hersteller")
        self.resize(400, 230)
        self.name = QLineEdit((vendor or {}).get("name") or "")
        self.name.setPlaceholderText("z.B. Polymaker, eSUN, Bambu Lab, Elegoo …")
        self.tare = QDoubleSpinBox()
        self.tare.setRange(0, 2000)
        self.tare.setDecimals(1)
        self.tare.setSuffix(" g")
        self.tare.setSpecialValueText("Nicht angegeben")
        self.tare.setValue(float(vendor["empty_spool_weight"]) if vendor and vendor.get("empty_spool_weight") is not None else 0.0)
        self.ext_id = QLineEdit((vendor or {}).get("external_id") or "")
        self.ext_id.setPlaceholderText("optional (SpoolmanDB ID)")
        self.comment = QLineEdit((vendor or {}).get("comment") or "")

        f = QFormLayout(self)
        f.addRow("Name *:", self.name)
        f.addRow("Leerspulen-Gewicht (Tara):", self.tare)
        f.addRow("Externe ID:", self.ext_id)
        f.addRow("Kommentar:", self.comment)

        btns = QHBoxLayout()
        b_cancel = QPushButton("Abbrechen")
        b_ok = QPushButton("Speichern")
        b_ok.setObjectName("primary")
        b_cancel.clicked.connect(self.reject)
        b_ok.clicked.connect(self._on_save)
        btns.addStretch()
        btns.addWidget(b_cancel)
        btns.addWidget(b_ok)
        f.addRow(btns)

    def _on_save(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Fehlende Angabe", "Bitte gib einen Herstellernamen ein.")
            return
        self.accept()

    def payload(self):
        return {
            "name": self.name.text().strip(),
            "empty_spool_weight": self.tare.value() if self.tare.value() > 0 else None,
            "external_id": self.ext_id.text().strip() or None,
            "comment": self.comment.text().strip() or None,
        }


class FilamentDialog(QDialog):
    def __init__(self, parent, base_url, vendors, materials, filament=None):
        super().__init__(parent)
        self.base_url = base_url
        self.vendors = list(vendors or [])
        self.filament = filament
        self.setWindowTitle("Filament bearbeiten" if filament else "Neues Filament anlegen")
        self.resize(500, 560)

        self.name = QLineEdit((filament or {}).get("name") or "")
        self.name.setPlaceholderText("z.B. PLA Basic, PETG Rapid, PolyLite ASA …")

        # Vendor row with quick-add button
        self.vendor_combo = QComboBox()
        self._populate_vendors((filament or {}).get("vendor", {}).get("id") if filament and filament.get("vendor") else None)
        btn_new_vendor = QPushButton("+ Neu")
        btn_new_vendor.setToolTip("Neuen Hersteller anlegen")
        btn_new_vendor.clicked.connect(self._create_vendor_inline)
        v_row = QHBoxLayout()
        v_row.addWidget(self.vendor_combo, 1)
        v_row.addWidget(btn_new_vendor)

        # Material combo
        self.mat_combo = QComboBox()
        self.mat_combo.setEditable(True)
        all_mats = sorted(set(list(MATERIAL_DENSITIES.keys()) + list(materials or [])))
        self.mat_combo.addItems(all_mats)
        cur_mat = (filament or {}).get("material") or "PLA"
        self.mat_combo.setCurrentText(cur_mat)
        self.mat_combo.currentTextChanged.connect(self._on_material_changed)

        # Color picker row
        init_hex = ((filament or {}).get("color_hex") or "38BDF8").lstrip("#").upper()
        self.color_edit = QLineEdit(init_hex)
        self.color_edit.setPlaceholderText("RRGGBB (z.B. FF0000)")
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(28, 28)
        self.btn_pick_color = QPushButton("Farbe wählen …")
        self.btn_pick_color.clicked.connect(self._pick_color)
        self.color_edit.textChanged.connect(self._update_color_preview)
        c_row = QHBoxLayout()
        c_row.addWidget(self.color_preview)
        c_row.addWidget(self.color_edit, 1)
        c_row.addWidget(self.btn_pick_color)

        # Multi-color optional
        self.multi_hex = QLineEdit((filament or {}).get("multi_color_hexes") or "")
        self.multi_hex.setPlaceholderText("optional, z.B. 33D17A,A51D2D für Dual/Tricolor Silk")
        self.multi_hex.textChanged.connect(self._update_color_preview)

        # Variant (extra.variant)
        extra_dec = spoolman.decode_extra((filament or {}).get("extra"))
        self.variant = QLineEdit(str(extra_dec.get("variant") or ""))
        self.variant.setPlaceholderText("optional, z.B. Silk, Matte, Rapid, High Speed, CF …")

        # Physical specs
        self.diameter = QDoubleSpinBox()
        self.diameter.setRange(0.5, 5.0)
        self.diameter.setDecimals(2)
        self.diameter.setSingleStep(0.05)
        self.diameter.setSuffix(" mm")
        self.diameter.setValue(float((filament or {}).get("diameter") or 1.75))

        self.density = QDoubleSpinBox()
        self.density.setRange(0.2, 10.0)
        self.density.setDecimals(2)
        self.density.setSingleStep(0.01)
        self.density.setSuffix(" g/cm³")
        self.density.setValue(float((filament or {}).get("density") or MATERIAL_DENSITIES.get(cur_mat.upper(), 1.24)))

        self.weight = QDoubleSpinBox()
        self.weight.setRange(0, 10000)
        self.weight.setDecimals(0)
        self.weight.setSingleStep(50)
        self.weight.setSuffix(" g")
        self.weight.setValue(float((filament or {}).get("weight") or 1000.0))

        self.spool_weight = QDoubleSpinBox()
        self.spool_weight.setRange(0, 2000)
        self.spool_weight.setDecimals(0)
        self.spool_weight.setSuffix(" g")
        self.spool_weight.setSpecialValueText("Vom Hersteller / Standard")
        self.spool_weight.setValue(float(filament["spool_weight"]) if filament and filament.get("spool_weight") is not None else 0.0)

        self.price = QDoubleSpinBox()
        self.price.setRange(0, 1000)
        self.price.setDecimals(2)
        self.price.setSuffix(" €")
        self.price.setSpecialValueText("Nicht angegeben")
        self.price.setValue(float(filament["price"]) if filament and filament.get("price") is not None else 0.0)

        # Temperatures
        def_ext, def_bed = MATERIAL_TEMPS.get(cur_mat.upper(), (210, 60))
        self.ext_temp = QSpinBox()
        self.ext_temp.setRange(0, 450)
        self.ext_temp.setSuffix(" °C")
        self.ext_temp.setSpecialValueText("—")
        self.ext_temp.setValue(int(filament["settings_extruder_temp"]) if filament and filament.get("settings_extruder_temp") else def_ext)

        self.bed_temp = QSpinBox()
        self.bed_temp.setRange(0, 200)
        self.bed_temp.setSuffix(" °C")
        self.bed_temp.setSpecialValueText("—")
        self.bed_temp.setValue(int(filament["settings_bed_temp"]) if filament and filament.get("settings_bed_temp") is not None else def_bed)

        t_row = QHBoxLayout()
        t_row.addWidget(QLabel("Düse:"))
        t_row.addWidget(self.ext_temp)
        t_row.addSpacing(12)
        t_row.addWidget(QLabel("Bett:"))
        t_row.addWidget(self.bed_temp)
        t_row.addStretch()

        self.article = QLineEdit((filament or {}).get("article_number") or "")
        self.comment = QLineEdit((filament or {}).get("comment") or "")

        f = QFormLayout(self)
        f.addRow("Name *:", self.name)
        f.addRow("Hersteller:", v_row)
        f.addRow("Material *:", self.mat_combo)
        f.addRow("Variante:", self.variant)
        f.addRow("Farbe (Hex):", c_row)
        f.addRow("Mehrfarbig (Hex-Liste):", self.multi_hex)
        f.addRow("Durchmesser:", self.diameter)
        f.addRow("Dichte:", self.density)
        f.addRow("Netto-Spulengewicht:", self.weight)
        f.addRow("Leerspulen-Gewicht:", self.spool_weight)
        f.addRow("Standardpreis:", self.price)
        f.addRow("Temperaturen:", t_row)
        f.addRow("Artikelnummer:", self.article)
        f.addRow("Kommentar:", self.comment)

        btns = QHBoxLayout()
        b_cancel = QPushButton("Abbrechen")
        b_ok = QPushButton("Speichern")
        b_ok.setObjectName("primary")
        b_cancel.clicked.connect(self.reject)
        b_ok.clicked.connect(self._on_save)
        btns.addStretch()
        btns.addWidget(b_cancel)
        btns.addWidget(b_ok)
        f.addRow(btns)

        self._update_color_preview()

    def _populate_vendors(self, selected_id=None):
        self.vendor_combo.clear()
        self.vendor_combo.addItem("— Kein Hersteller —", None)
        for v in sorted(self.vendors, key=lambda x: (x.get("name") or "").lower()):
            self.vendor_combo.addItem(v.get("name") or f"#{v['id']}", v["id"])
        if selected_id is not None:
            idx = self.vendor_combo.findData(selected_id)
            if idx >= 0:
                self.vendor_combo.setCurrentIndex(idx)

    def _create_vendor_inline(self):
        dlg = VendorDialog(self)
        if dlg.exec():
            try:
                v = spoolman.create_vendor(self.base_url, dlg.payload())
                self.vendors.append(v)
                self._populate_vendors(v.get("id"))
            except Exception as e:
                QMessageBox.warning(self, "Fehler", str(e))

    def _on_material_changed(self, text):
        m = text.strip().upper()
        if not self.filament:
            if m in MATERIAL_DENSITIES:
                self.density.setValue(MATERIAL_DENSITIES[m])
            if m in MATERIAL_TEMPS:
                ext, bed = MATERIAL_TEMPS[m]
                self.ext_temp.setValue(ext)
                self.bed_temp.setValue(bed)

    def _pick_color(self):
        cur = QColor("#" + self.color_edit.text().strip().lstrip("#"))
        if not cur.isValid():
            cur = QColor("#38bdf8")
        c = QColorDialog.getColor(cur, self, "Filamentfarbe wählen")
        if c.isValid():
            self.color_edit.setText(c.name().lstrip("#").upper())

    def _update_color_preview(self):
        multi = [x.strip().lstrip("#") for x in self.multi_hex.text().split(",") if x.strip()]
        if len(multi) >= 2:
            colors = [f"#{x[:6]}" for x in multi]
        else:
            chex = self.color_edit.text().strip().lstrip("#")
            colors = [f"#{chex[:6]}" if len(chex) >= 6 else "#38bdf8"]
        self.color_preview.setPixmap(make_spool_pixmap(colors, 1.0, 26))

    def _on_save(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Fehlende Angabe", "Bitte gib einen Namen für das Filament ein.")
            return
        self.accept()

    def payload(self):
        multi = ",".join(x.strip().lstrip("#").upper() for x in self.multi_hex.text().split(",") if x.strip())
        chex = self.color_edit.text().strip().lstrip("#").upper()
        data = {
            "name": self.name.text().strip(),
            "vendor_id": self.vendor_combo.currentData(),
            "material": self.mat_combo.currentText().strip() or "PLA",
            "density": self.density.value(),
            "diameter": self.diameter.value(),
            "weight": self.weight.value() if self.weight.value() > 0 else None,
            "spool_weight": self.spool_weight.value() if self.spool_weight.value() > 0 else None,
            "price": self.price.value() if self.price.value() > 0 else None,
            "settings_extruder_temp": self.ext_temp.value() if self.ext_temp.value() > 0 else None,
            "settings_bed_temp": self.bed_temp.value() if self.bed_temp.value() > 0 else None,
            "article_number": self.article.text().strip() or None,
            "comment": self.comment.text().strip() or None,
        }
        if multi and "," in multi:
            data["multi_color_hexes"] = multi
            data["multi_color_direction"] = "coaxial"
            data["color_hex"] = None
        else:
            data["color_hex"] = chex if chex else None
            data["multi_color_hexes"] = None

        var_txt = self.variant.text().strip()
        if var_txt or (self.filament and "variant" in (self.filament.get("extra") or {})):
            data["extra"] = {"variant": spoolman.encode_extra_value(var_txt)}
        return data


class ExternalFilamentDialog(QDialog):
    """Search and import official filaments & vendors from SpoolmanDB (/api/v1/external/filament)."""
    def __init__(self, parent, base_url, vendors, run_async_fn):
        super().__init__(parent)
        self.base_url = base_url
        self.vendors = list(vendors or [])
        self.run_async = run_async_fn
        self.results = []
        self.imported_filament = None
        self.create_spool_checked = True

        self.setWindowTitle("Filament aus SpoolmanDB-Katalog importieren")
        self.resize(840, 560)

        l = QVBoxLayout(self)
        info = QLabel(
            "Durchsuche über 9.400 vordefinierte Filamente bekannter Hersteller (inkl. Dichte, Gewicht, Leerspulen-Tara, Temperaturen & Farbcode)."
        )
        info.setObjectName("dim")
        info.setWordWrap(True)
        l.addWidget(info)

        srow = QHBoxLayout()
        self.q = QLineEdit()
        self.q.setPlaceholderText("Hersteller, Material oder Farbname eingeben (z.B. „Polymaker PLA“, „Bambu PETG“, „eSUN ASA“) …")
        self.q.returnPressed.connect(self.search)
        self.btn_search = QPushButton("Suchen")
        self.btn_search.setObjectName("primary")
        self.btn_search.clicked.connect(self.search)
        srow.addWidget(self.q, 1)
        srow.addWidget(self.btn_search)
        l.addLayout(srow)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Farbe", "Hersteller", "Name", "Material", "Ø / Dichte", "Gewicht (Tara)", "Temp (Düse/Bett)"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self.import_selected)
        l.addWidget(self.table, 1)

        self.cb_create_spool = QCheckBox("Nach dem Import direkt auch eine neue Spule für dieses Filament anlegen")
        self.cb_create_spool.setChecked(True)
        l.addWidget(self.cb_create_spool)

        brow = QHBoxLayout()
        self.status_lbl = QLabel("Bereit.")
        self.status_lbl.setObjectName("dim")
        b_cancel = QPushButton("Schließen")
        self.b_import = QPushButton("Ausgewähltes Filament importieren")
        self.b_import.setObjectName("primary")
        b_cancel.clicked.connect(self.reject)
        self.b_import.clicked.connect(self.import_selected)
        brow.addWidget(self.status_lbl, 1)
        brow.addWidget(b_cancel)
        brow.addWidget(self.b_import)
        l.addLayout(brow)

        self.search()

    def search(self):
        q = self.q.text().strip()
        self.status_lbl.setText("Durchsuche SpoolmanDB …")
        self.btn_search.setEnabled(False)
        self.run_async(lambda: spoolman.search_external_filaments(self.base_url, q, limit=80), self._on_results)

    def _on_results(self, r):
        self.btn_search.setEnabled(True)
        if r[0] == "err":
            self.status_lbl.setText(f"Fehler: {r[1]}")
            return
        self.results = r[1] or []
        self.status_lbl.setText(f"{len(self.results)} Treffer angezeigt.")
        self.table.setRowCount(len(self.results))
        for i, item in enumerate(self.results):
            colors = spoolman.spool_colors(item)
            it_col = QTableWidgetItem(colors[0])
            it_col.setIcon(QIcon(make_spool_pixmap(colors, 1.0, 24)))
            mfg = item.get("manufacturer") or "—"
            name = item.get("name") or "—"
            mat = item.get("material") or "—"
            spec = f"{item.get('diameter', 1.75)} mm · {item.get('density', 1.24):.2f} g/cm³"
            w = item.get("weight") or 1000
            sw = item.get("spool_weight")
            w_str = f"{w:.0f} g" + (f" (Tara {sw:.0f} g)" if sw else "")
            et = item.get("extruder_temp")
            bt = item.get("bed_temp")
            t_str = f"{et or '—'} / {bt or '—'} °C"

            self.table.setItem(i, 0, it_col)
            for c_idx, val in enumerate((mfg, name, mat, spec, w_str, t_str), start=1):
                self.table.setItem(i, c_idx, QTableWidgetItem(str(val)))

    def import_selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.results):
            QMessageBox.information(self, "Auswahl", "Bitte wähle zuerst ein Filament in der Tabelle aus.")
            return
        ext_item = self.results[row]
        self.b_import.setEnabled(False)
        self.status_lbl.setText("Importiere Filament und Hersteller …")
        self.create_spool_checked = self.cb_create_spool.isChecked()
        self.run_async(
            lambda: spoolman.import_external_filament(self.base_url, ext_item, self.vendors),
            self._on_imported,
        )

    def _on_imported(self, r):
        self.b_import.setEnabled(True)
        if r[0] == "err":
            QMessageBox.warning(self, "Import fehlgeschlagen", r[1])
            return
        self.imported_filament = r[1]
        self.accept()


class SpoolDialog(QDialog):
    """Create or Edit a Spool in Spoolman."""
    def __init__(self, parent, base_url, filaments, vendors, materials, locations, printer_states=None, spool=None):
        super().__init__(parent)
        self.base_url = base_url
        self.filaments = list(filaments or [])
        self.vendors = list(vendors or [])
        self.materials = list(materials or [])
        self.printer_states = list(printer_states or [])
        self.spool = spool
        self.setWindowTitle(f"Spule #{spool['id']} bearbeiten" if spool else "Neue Spule anlegen")
        self.resize(520, 520)

        # Filament selector + inline creation button
        self.fil_combo = QComboBox()
        self.fil_combo.setIconSize(QSize(22, 22))
        cur_fid = ((spool or {}).get("filament") or {}).get("id")
        self._populate_filaments(cur_fid)
        self.fil_combo.currentIndexChanged.connect(self._on_filament_selected)

        btn_new_fil = QPushButton("+ Neues Filament …")
        btn_new_fil.clicked.connect(self._create_filament_inline)
        fil_row = QHBoxLayout()
        fil_row.addWidget(self.fil_combo, 1)
        fil_row.addWidget(btn_new_fil)

        # Weight fields
        self.initial_weight = QDoubleSpinBox()
        self.initial_weight.setRange(0, 20000)
        self.initial_weight.setDecimals(1)
        self.initial_weight.setSingleStep(50)
        self.initial_weight.setSuffix(" g")
        init_w = spoolman.spool_initial_weight(spool) if spool else 1000.0
        self.initial_weight.setValue(init_w)

        self.remaining_weight = QDoubleSpinBox()
        self.remaining_weight.setRange(0, 20000)
        self.remaining_weight.setDecimals(1)
        self.remaining_weight.setSingleStep(10)
        self.remaining_weight.setSuffix(" g")
        rem_w = float(spool.get("remaining_weight")) if spool and spool.get("remaining_weight") is not None else init_w
        self.remaining_weight.setValue(rem_w)

        self.spool_weight = QDoubleSpinBox()
        self.spool_weight.setRange(0, 3000)
        self.spool_weight.setDecimals(1)
        self.spool_weight.setSuffix(" g")
        self.spool_weight.setSpecialValueText("Vom Filament/Hersteller")
        self.spool_weight.setValue(float(spool["spool_weight"]) if spool and spool.get("spool_weight") is not None else 0.0)

        self.price = QDoubleSpinBox()
        self.price.setRange(0, 1000)
        self.price.setDecimals(2)
        self.price.setSuffix(" €")
        self.price.setSpecialValueText("Vom Filament übernehmen")
        self.price.setValue(float(spool["price"]) if spool and spool.get("price") is not None else 0.0)

        self.location = QComboBox()
        self.location.setEditable(True)
        self.location.addItem("")
        for loc in sorted(set(locations or [])):
            self.location.addItem(loc)
        self.location.setCurrentText((spool or {}).get("location") or "")

        self.lot_nr = QLineEdit((spool or {}).get("lot_nr") or "")
        self.lot_nr.setPlaceholderText("optional (Chargen-/Batch-Nummer)")

        # NFC Card UIDs (extra.card_uids) with button to pick from printer NFC readers
        extra_dec = spoolman.decode_extra((spool or {}).get("extra"))
        self.card_uids = QLineEdit(str(extra_dec.get("card_uids") or ""))
        self.card_uids.setPlaceholderText("optional, z.B. 04974B3FE22A81 (NFC-Tag UID)")
        btn_nfc = QPushButton("Vom Drucker lesen …")
        btn_nfc.setToolTip("Erkannte NFC Card-UID direkt von einem Drucker-Slot übernehmen")
        btn_nfc.clicked.connect(self._pick_nfc_from_printer)
        nfc_row = QHBoxLayout()
        nfc_row.addWidget(self.card_uids, 1)
        nfc_row.addWidget(btn_nfc)

        self.comment = QLineEdit((spool or {}).get("comment") or "")
        self.comment.setPlaceholderText("optional (Notizen zur Spule)")

        self.archived = QCheckBox("Spule ist archiviert (leer / nicht mehr in Verwendung)")
        self.archived.setChecked(bool((spool or {}).get("archived", False)))

        f = QFormLayout(self)
        f.addRow("Filament *:", fil_row)
        f.addRow("Netto-Anfangsgewicht:", self.initial_weight)
        f.addRow("Aktuelles Restgewicht:", self.remaining_weight)
        f.addRow("Leerspulen-Gewicht (Tara):", self.spool_weight)
        f.addRow("Kaufpreis (Spule):", self.price)
        f.addRow("Lagerort:", self.location)
        f.addRow("Chargen-Nr. (Lot):", self.lot_nr)
        f.addRow("NFC Card-UID(s):", nfc_row)
        f.addRow("Kommentar:", self.comment)
        f.addRow("", self.archived)

        btns = QHBoxLayout()
        b_cancel = QPushButton("Abbrechen")
        b_ok = QPushButton("Speichern")
        b_ok.setObjectName("primary")
        b_cancel.clicked.connect(self.reject)
        b_ok.clicked.connect(self._on_save)
        btns.addStretch()
        btns.addWidget(b_cancel)
        btns.addWidget(b_ok)
        f.addRow(btns)

        if not spool:
            self._on_filament_selected()

    def _populate_filaments(self, selected_id=None):
        self.fil_combo.blockSignals(True)
        self.fil_combo.clear()
        for fil in sorted(
            self.filaments,
            key=lambda x: (
                ((x.get("vendor") or {}).get("name") or "").lower(),
                (x.get("name") or "").lower(),
                x.get("id", 0),
            ),
        ):
            vname = (fil.get("vendor") or {}).get("name") or ""
            fname = fil.get("name") or "?"
            mat = fil.get("material") or ""
            label = f"#{fil['id']} · {vname} {fname} ({mat})".strip()
            icon = QIcon(make_spool_pixmap(spoolman.spool_colors(fil), 1.0, 22))
            self.fil_combo.addItem(icon, label, fil["id"])
        if selected_id is not None:
            idx = self.fil_combo.findData(selected_id)
            if idx >= 0:
                self.fil_combo.setCurrentIndex(idx)
        self.fil_combo.blockSignals(False)

    def _on_filament_selected(self):
        fid = self.fil_combo.currentData()
        fil = next((x for x in self.filaments if x.get("id") == fid), None)
        if not fil or self.spool:
            return
        if fil.get("weight"):
            self.initial_weight.setValue(float(fil["weight"]))
            self.remaining_weight.setValue(float(fil["weight"]))
        if fil.get("spool_weight") is not None:
            self.spool_weight.setValue(float(fil["spool_weight"]))
        if fil.get("price") is not None:
            self.price.setValue(float(fil["price"]))

    def _create_filament_inline(self):
        dlg = FilamentDialog(self, self.base_url, self.vendors, self.materials)
        if dlg.exec():
            try:
                created = spoolman.create_filament(self.base_url, dlg.payload())
                self.filaments.append(created)
                self._populate_filaments(created.get("id"))
                self._on_filament_selected()
            except Exception as e:
                QMessageBox.warning(self, "Fehler", str(e))

    def _pick_nfc_from_printer(self):
        choices = []
        for ps in self.printer_states:
            pname = ps.get("printer_name", "Drucker")
            for sl in ps.get("slots") or []:
                uid = sl.get("card_uid")
                if uid:
                    choices.append((f"{pname} · {sl['label']}: {uid} ({sl.get('type') or '?'})", uid))
        if not choices:
            QMessageBox.information(
                self,
                "Kein NFC-Tag erkannt",
                "Aktuell wurde an keinem Drucker-Slot ein NFC-Tag (CARD_UID) erkannt.",
            )
            return
        labels = [c[0] for c in choices]
        picked, ok = QInputDialog.getItem(self, "NFC Card-UID übernehmen", "Erkannte NFC-Tags an deinen Druckern:", labels, 0, False)
        if ok and picked:
            uid = next(c[1] for c in choices if c[0] == picked)
            cur = [u.strip() for u in self.card_uids.text().split(",") if u.strip()]
            if uid not in cur:
                cur.append(uid)
            self.card_uids.setText(",".join(cur))

    def _on_save(self):
        if self.fil_combo.currentData() is None:
            QMessageBox.warning(self, "Filament fehlt", "Bitte wähle zuerst ein Filament aus oder lege eines an.")
            return
        self.accept()

    def payload(self):
        data = {
            "filament_id": int(self.fil_combo.currentData()),
            "initial_weight": self.initial_weight.value() if self.initial_weight.value() > 0 else None,
            "remaining_weight": self.remaining_weight.value(),
            "spool_weight": self.spool_weight.value() if self.spool_weight.value() > 0 else None,
            "price": self.price.value() if self.price.value() > 0 else None,
            "location": self.location.currentText().strip() or None,
            "lot_nr": self.lot_nr.text().strip() or None,
            "comment": self.comment.text().strip() or None,
            "archived": self.archived.isChecked(),
        }
        uid_txt = self.card_uids.text().strip()
        if uid_txt or (self.spool and "card_uids" in (self.spool.get("extra") or {})):
            data["extra"] = {"card_uids": spoolman.encode_extra_value(uid_txt)}
        return data


class MeasureSpoolDialog(QDialog):
    """Weigh a spool on a scale to update remaining filament weight."""
    def __init__(self, parent, spool):
        super().__init__(parent)
        self.spool = spool
        self.setWindowTitle(f"Spule #{spool['id']} abwiegen (Waage)")
        self.resize(430, 260)

        fil = spool.get("filament") or {}
        vendor = fil.get("vendor") or {}
        tare = (
            spool.get("spool_weight")
            or fil.get("spool_weight")
            or vendor.get("empty_spool_weight")
            or 200.0
        )
        cur_rem = float(spool.get("remaining_weight") or 0.0)

        l = QVBoxLayout(self)
        title = QLabel(f"<b>{spoolman.spool_display_name(spool)}</b>")
        l.addWidget(title)

        info = QLabel(
            f"Leerspulen-Tara: <b>{tare:.0f} g</b> · Bisheriges Restgewicht: <b>{cur_rem:.1f} g</b>"
        )
        info.setObjectName("dim")
        l.addWidget(info)

        self.gross_spin = QDoubleSpinBox()
        self.gross_spin.setRange(0, 25000)
        self.gross_spin.setDecimals(1)
        self.gross_spin.setSingleStep(5)
        self.gross_spin.setSuffix(" g (Brutto auf Waage)")
        self.gross_spin.setValue(tare + cur_rem)
        self.gross_spin.valueChanged.connect(lambda v: self._update_calc(v, tare))

        self.calc_lbl = QLabel()
        self.calc_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #38bdf8;")
        self._update_calc(self.gross_spin.value(), tare)

        f = QFormLayout()
        f.addRow("Gewicht auf der Waage:", self.gross_spin)
        f.addRow("Berechnetes Netto-Filament:", self.calc_lbl)
        l.addLayout(f)

        btns = QHBoxLayout()
        b_cancel = QPushButton("Abbrechen")
        b_ok = QPushButton("Messwert speichern")
        b_ok.setObjectName("primary")
        b_cancel.clicked.connect(self.reject)
        b_ok.clicked.connect(self.accept)
        btns.addStretch()
        btns.addWidget(b_cancel)
        btns.addWidget(b_ok)
        l.addLayout(btns)

    def _update_calc(self, gross, tare):
        net = max(0.0, gross - tare)
        self.calc_lbl.setText(f"{net:.1f} g verbleibend")

    def gross_weight(self):
        return self.gross_spin.value()


class UseSpoolDialog(QDialog):
    """Deduct (or add back) filament weight or length on a spool."""
    def __init__(self, parent, spool):
        super().__init__(parent)
        self.spool = spool
        self.setWindowTitle(f"Filament-Verbrauch buchen (#{spool['id']})")
        self.resize(420, 240)

        l = QVBoxLayout(self)
        l.addWidget(QLabel(f"<b>{spoolman.spool_display_name(spool)}</b>"))
        sub = QLabel("Positiver Wert zieht Filament ab; negativer Wert bucht Filament wieder hinzu.")
        sub.setObjectName("dim")
        sub.setWordWrap(True)
        l.addWidget(sub)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Nach Gewicht (Gramm)", "weight")
        self.mode_combo.addItem("Nach Länge (Millimeter)", "length")
        self.mode_combo.currentIndexChanged.connect(self._on_mode)

        self.val_spin = QDoubleSpinBox()
        self.val_spin.setRange(-10000, 10000)
        self.val_spin.setDecimals(1)
        self.val_spin.setValue(10.0)
        self.val_spin.setSuffix(" g")

        f = QFormLayout()
        f.addRow("Einheit:", self.mode_combo)
        f.addRow("Verbrauch:", self.val_spin)
        l.addLayout(f)

        btns = QHBoxLayout()
        b_cancel = QPushButton("Abbrechen")
        b_ok = QPushButton("Verbrauch buchen")
        b_ok.setObjectName("primary")
        b_cancel.clicked.connect(self.reject)
        b_ok.clicked.connect(self.accept)
        btns.addStretch()
        btns.addWidget(b_cancel)
        btns.addWidget(b_ok)
        l.addLayout(btns)

    def _on_mode(self):
        if self.mode_combo.currentData() == "weight":
            self.val_spin.setSuffix(" g")
        else:
            self.val_spin.setSuffix(" mm")

    def usage(self):
        if self.mode_combo.currentData() == "weight":
            return {"use_weight": self.val_spin.value(), "use_length": None}
        return {"use_weight": None, "use_length": self.val_spin.value()}


class AssignSpoolDialog(QDialog):
    """Assign a Spoolman spool to a printer or multi-extruder toolhead channel."""
    def __init__(self, parent, spool, printers, printer_states):
        super().__init__(parent)
        self.spool = spool
        self.printers = printers
        self.printer_states = {ps["printer_id"]: ps for ps in (printer_states or [])}
        self.setWindowTitle(f"Spule #{spool['id']} einem Drucker zuweisen")
        self.resize(460, 270)

        l = QVBoxLayout(self)
        l.addWidget(QLabel(f"<b>{spoolman.spool_display_name(spool)}</b>"))

        self.target_combo = QComboBox()
        for p in printers:
            ps = self.printer_states.get(p.id) or {}
            slots = ps.get("slots") or []
            if slots:
                for sl in slots:
                    act = " AKTIV" if sl.get("active") else ""
                    uid_info = f" · NFC {sl['card_uid']}" if sl.get("card_uid") else ""
                    cur_s = f" (aktuell #{sl['spool_id']})" if sl.get("spool_id") else " (leer)"
                    self.target_combo.addItem(
                        f"{p.name} · Slot {sl['label']}{act}{cur_s}{uid_info}",
                        {"printer": p, "channel": sl["channel"], "card_uid": sl.get("card_uid")},
                    )
            self.target_combo.addItem(
                f"{p.name} · Aktive Hauptspule (Moonraker)",
                {"printer": p, "channel": None, "card_uid": ""},
            )

        self.cb_link_nfc = QCheckBox("Erkannten NFC-Tag (CARD_UID) des Slots dauerhaft mit dieser Spule verknüpfen")
        self.cb_link_nfc.setChecked(True)
        self.target_combo.currentIndexChanged.connect(self._on_target_changed)

        f = QFormLayout()
        f.addRow("Ziel-Drucker / Extruder:", self.target_combo)
        l.addLayout(f)
        l.addWidget(self.cb_link_nfc)
        self._on_target_changed()

        btns = QHBoxLayout()
        b_cancel = QPushButton("Abbrechen")
        b_ok = QPushButton("Jetzt zuweisen")
        b_ok.setObjectName("primary")
        b_cancel.clicked.connect(self.reject)
        b_ok.clicked.connect(self.accept)
        btns.addStretch()
        btns.addWidget(b_cancel)
        btns.addWidget(b_ok)
        l.addLayout(btns)

    def _on_target_changed(self):
        d = self.target_combo.currentData() or {}
        uid = d.get("card_uid")
        self.cb_link_nfc.setVisible(bool(uid))
        if uid:
            self.cb_link_nfc.setText(f"NFC-Tag ({uid}) auch in Spoolman mit Spule #{self.spool['id']} verknüpfen")

    def selection(self):
        d = self.target_combo.currentData() or {}
        return {
            "printer": d.get("printer"),
            "channel": d.get("channel"),
            "card_uid": d.get("card_uid") if self.cb_link_nfc.isVisible() and self.cb_link_nfc.isChecked() else "",
        }



class SpoolmanPage(QWidget):
    def __init__(self, win, get_url_fn, set_url_fn, get_local_spool_fn, set_local_spool_fn, run_async_fn):
        super().__init__()
        self.win = win
        self.get_url = get_url_fn
        self.set_url = set_url_fn
        self.get_local_spool = get_local_spool_fn
        self.set_local_spool = set_local_spool_fn
        self.run_async = run_async_fn

        self.bundle = {
            "url": "",
            "info": {},
            "spools": [],
            "filaments": [],
            "vendors": [],
            "locations": [],
            "materials": [],
            "printer_states": [],
        }

        # Top header bar
        top = QHBoxLayout()
        title = QLabel("Spoolman Filament-Manager")
        title.setObjectName("h1")
        self.conn_badge = QLabel("Verbinde …")
        self.conn_badge.setObjectName("dim")

        btn_refresh = QPushButton("Aktualisieren")
        btn_refresh.clicked.connect(self.reload)
        btn_backup = QPushButton("DB-Backup")
        btn_backup.setToolTip("SQLite-Datenbank-Backup auf dem Spoolman-Server erstellen")
        btn_backup.clicked.connect(self.create_backup)
        btn_web = QPushButton("Spoolman Web-UI")
        btn_web.clicked.connect(self.open_web_ui)

        top.addWidget(title)
        top.addSpacing(10)
        top.addWidget(self.conn_badge)
        top.addStretch()
        top.addWidget(btn_refresh)
        top.addWidget(btn_backup)
        top.addWidget(btn_web)

        # KPI Summary Cards
        self.kpi = {}
        kpi_row = QHBoxLayout()
        for key, label in (
            ("spools", "Aktive Spulen"),
            ("weight", "Gesamtbestand"),
            ("value", "Bestandswert"),
            ("catalog", "Filamente & Hersteller"),
            ("low", "Fast leer (< 150 g)"),
        ):
            c = QFrame()
            c.setObjectName("card")
            cl = QVBoxLayout(c)
            cl.setContentsMargins(14, 10, 14, 10)
            tl = QLabel(label)
            tl.setObjectName("dim")
            vl = QLabel("—")
            vl.setStyleSheet("font-size:18px;font-weight:700;color:#55c5ff")
            cl.addWidget(tl)
            cl.addWidget(vl)
            self.kpi[key] = vl
            kpi_row.addWidget(c)

        # Main Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_spools_tab(), "Spulen (Bestand)")
        self.tabs.addTab(self._build_filaments_tab(), "Filamente (Typen)")
        self.tabs.addTab(self._build_vendors_tab(), "Hersteller (Vendors)")
        self.tabs.addTab(self._build_printers_tab(), "Drucker-Slots & NFC-Zuordnung")

        l = QVBoxLayout(self)
        l.setSpacing(12)
        l.addLayout(top)
        l.addLayout(kpi_row)
        l.addWidget(self.tabs, 1)

    def showEvent(self, e):
        super().showEvent(e)
        self.reload()

    def _build_spools_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(12, 12, 12, 12)
        l.setSpacing(10)

        fbar = QHBoxLayout()
        self.sp_search = QLineEdit()
        self.sp_search.setPlaceholderText("Spule suchen (Name, Hersteller, Material, #ID, NFC-UID, Lagerort) …")
        self.sp_search.textChanged.connect(self.render_spools)

        self.sp_mat_filter = QComboBox()
        self.sp_mat_filter.setMinimumWidth(120)
        self.sp_mat_filter.currentIndexChanged.connect(self.render_spools)

        self.sp_vendor_filter = QComboBox()
        self.sp_vendor_filter.setMinimumWidth(140)
        self.sp_vendor_filter.currentIndexChanged.connect(self.render_spools)

        self.sp_loc_filter = QComboBox()
        self.sp_loc_filter.setMinimumWidth(120)
        self.sp_loc_filter.currentIndexChanged.connect(self.render_spools)

        self.sp_archived_cb = QCheckBox("Archivierte zeigen")
        self.sp_archived_cb.toggled.connect(self.render_spools)

        btn_add_spool = QPushButton("+ Neue Spule …")
        btn_add_spool.setObjectName("primary")
        btn_add_spool.clicked.connect(self.add_spool)

        fbar.addWidget(self.sp_search, 2)
        fbar.addWidget(QLabel("Material:"))
        fbar.addWidget(self.sp_mat_filter)
        fbar.addWidget(QLabel("Hersteller:"))
        fbar.addWidget(self.sp_vendor_filter)
        fbar.addWidget(QLabel("Ort:"))
        fbar.addWidget(self.sp_loc_filter)
        fbar.addWidget(self.sp_archived_cb)
        fbar.addWidget(btn_add_spool)

        # Table + Right Inspector
        self.sp_table = QTableWidget(0, 8)
        self.sp_table.setHorizontalHeaderLabels([
            "ID", "Filament & Farbe", "Hersteller", "Material", "Temp", "Restgewicht", "Status / Drucker", "Preis"
        ])
        self.sp_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.sp_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.sp_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.sp_table.setAlternatingRowColors(True)
        self.sp_table.setIconSize(QSize(26, 26))
        self.sp_table.currentCellChanged.connect(lambda r, c, pr, pc: self.update_spool_inspector())
        self.sp_table.doubleClicked.connect(lambda _: self.edit_selected_spool())
        self.sp_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sp_table.customContextMenuRequested.connect(self._spool_context_menu)

        # Right-hand Inspector Card
        self.sp_inspector = QFrame()
        self.sp_inspector.setObjectName("card")
        self.sp_inspector.setFixedWidth(320)
        il = QVBoxLayout(self.sp_inspector)
        il.setSpacing(7)

        self.sp_prev_icon = QLabel("Keine Spule ausgewählt")
        self.sp_prev_icon.setAlignment(Qt.AlignCenter)
        self.sp_prev_icon.setFixedHeight(140)
        self.sp_prev_icon.setStyleSheet("background:#0b121c;border:1px solid #1e2f44;border-radius:10px;color:#8198af")

        self.sp_info_title = QLabel("—")
        self.sp_info_title.setWordWrap(True)
        self.sp_info_title.setStyleSheet("font-size:15px;font-weight:700")

        self.sp_fill_bar = QProgressBar()
        self.sp_fill_bar.setRange(0, 1000)
        self.sp_fill_bar.setFixedHeight(10)

        self.sp_info_meta = QLabel("Wähle links eine Spule aus.")
        self.sp_info_meta.setWordWrap(True)
        self.sp_info_meta.setObjectName("dim")

        self.btn_sp_assign = QPushButton("Drucker / Extruder zuweisen …")
        self.btn_sp_assign.setObjectName("primary")
        self.btn_sp_assign.clicked.connect(self.assign_selected_spool)

        self.btn_sp_weigh = QPushButton("Abwiegen (Waage) …")
        self.btn_sp_weigh.clicked.connect(self.weigh_selected_spool)

        self.btn_sp_use = QPushButton("Verbrauch buchen …")
        self.btn_sp_use.clicked.connect(self.use_selected_spool)

        self.btn_sp_edit = QPushButton("Spule bearbeiten …")
        self.btn_sp_edit.clicked.connect(self.edit_selected_spool)

        self.btn_sp_dup = QPushButton("Spule duplizieren")
        self.btn_sp_dup.clicked.connect(self.duplicate_selected_spool)

        self.btn_sp_arch = QPushButton("Archivieren")
        self.btn_sp_arch.clicked.connect(self.toggle_archive_selected_spool)

        self.btn_sp_del = QPushButton("Spule löschen")
        self.btn_sp_del.setObjectName("danger")
        self.btn_sp_del.clicked.connect(self.delete_selected_spool)

        il.addWidget(self.sp_prev_icon)
        il.addWidget(self.sp_info_title)
        il.addWidget(self.sp_fill_bar)
        il.addWidget(self.sp_info_meta)
        il.addSpacing(4)
        for b in (
            self.btn_sp_assign, self.btn_sp_weigh, self.btn_sp_use,
            self.btn_sp_edit, self.btn_sp_dup, self.btn_sp_arch, self.btn_sp_del
        ):
            il.addWidget(b)
        il.addStretch()

        body = QHBoxLayout()
        body.addWidget(self.sp_table, 1)
        body.addWidget(self.sp_inspector)

        l.addLayout(fbar)
        l.addLayout(body, 1)
        self.update_spool_inspector()
        return w

    def _build_filaments_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(12, 12, 12, 12)
        l.setSpacing(10)

        bar = QHBoxLayout()
        self.fil_search = QLineEdit()
        self.fil_search.setPlaceholderText("Filament suchen (Name, Hersteller, Material, Variante) …")
        self.fil_search.textChanged.connect(self.render_filaments)

        btn_ext = QPushButton("Aus SpoolmanDB importieren …")
        btn_ext.setObjectName("primary")
        btn_ext.clicked.connect(self.import_from_external_db)

        btn_add = QPushButton("+ Neues Filament …")
        btn_add.setObjectName("primary")
        btn_add.clicked.connect(self.add_filament)

        btn_spool = QPushButton("+ Spule für Auswahl")
        btn_spool.clicked.connect(self.add_spool_for_selected_filament)

        btn_edit = QPushButton("Bearbeiten …")
        btn_edit.clicked.connect(self.edit_selected_filament)

        btn_del = QPushButton("Löschen")
        btn_del.setObjectName("danger")
        btn_del.clicked.connect(self.delete_selected_filament)

        bar.addWidget(self.fil_search, 1)
        for b in (btn_ext, btn_add, btn_spool, btn_edit, btn_del):
            bar.addWidget(b)

        self.fil_table = QTableWidget(0, 9)
        self.fil_table.setHorizontalHeaderLabels([
            "ID", "Name & Farbe", "Hersteller", "Material", "Variante", "Ø / Dichte", "Gewicht (Tara)", "Düse / Bett", "Spulen"
        ])
        self.fil_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.fil_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.fil_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.fil_table.setAlternatingRowColors(True)
        self.fil_table.setIconSize(QSize(24, 24))
        self.fil_table.doubleClicked.connect(lambda _: self.edit_selected_filament())

        l.addLayout(bar)
        l.addWidget(self.fil_table, 1)
        return w

    def _build_vendors_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(12, 12, 12, 12)
        l.setSpacing(10)

        bar = QHBoxLayout()
        self.ven_search = QLineEdit()
        self.ven_search.setPlaceholderText("Hersteller suchen …")
        self.ven_search.textChanged.connect(self.render_vendors)

        btn_add = QPushButton("+ Neuer Hersteller …")
        btn_add.setObjectName("primary")
        btn_add.clicked.connect(self.add_vendor)

        btn_edit = QPushButton("Bearbeiten …")
        btn_edit.clicked.connect(self.edit_selected_vendor)

        btn_del = QPushButton("Löschen")
        btn_del.setObjectName("danger")
        btn_del.clicked.connect(self.delete_selected_vendor)

        bar.addWidget(self.ven_search, 1)
        bar.addWidget(btn_add)
        bar.addWidget(btn_edit)
        bar.addWidget(btn_del)

        self.ven_table = QTableWidget(0, 6)
        self.ven_table.setHorizontalHeaderLabels([
            "ID", "Herstellername", "Leerspulen-Gewicht (Tara)", "Filamente", "Aktive Spulen", "Kommentar"
        ])
        self.ven_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.ven_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.ven_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.ven_table.setAlternatingRowColors(True)
        self.ven_table.doubleClicked.connect(lambda _: self.edit_selected_vendor())

        l.addLayout(bar)
        l.addWidget(self.ven_table, 1)
        return w

    def _build_printers_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(12, 12, 12, 12)

        info = QLabel(
            "Hier siehst du live alle Drucker, Multi-Extruder-Slots (z.B. Snapmaker U1 T0–T3 inkl. NFC-Tags) sowie die aktive Moonraker-Spule und kannst Spulen direkt zuweisen."
        )
        info.setObjectName("dim")
        info.setWordWrap(True)
        l.addWidget(info)

        self.printers_scroll = QScrollArea()
        self.printers_scroll.setWidgetResizable(True)
        self.printers_scroll.setFrameShape(QFrame.NoFrame)
        self.printers_container = QWidget()
        self.printers_layout = QVBoxLayout(self.printers_container)
        self.printers_layout.setSpacing(14)
        self.printers_scroll.setWidget(self.printers_container)

        l.addWidget(self.printers_scroll, 1)
        return w

    def reload(self):
        url = self.get_url()
        printers = getattr(self.win, "printers", [])
        self.conn_badge.setText("Lade Spoolman-Daten …")
        self.conn_badge.setStyleSheet("color:#9eb0c3")
        self.run_async(lambda: spoolman.fetch_bundle(url, printers, allow_archived=True), self._on_bundle_loaded)

    def _on_bundle_loaded(self, r):
        if r[0] == "err":
            self.conn_badge.setText(f"Nicht verbunden ({r[1]})")
            self.conn_badge.setStyleSheet("color:#f87171;font-weight:700")
            return
        b = r[1]
        self.bundle = b
        if b.get("url") and not self.get_url():
            self.set_url(b["url"])
        ver = (b.get("info") or {}).get("version", "?")
        self.conn_badge.setText(f"Verbunden: Spoolman v{ver} ({b['url']})")
        self.conn_badge.setStyleSheet("color:#34d399;font-weight:700")

        self._update_kpis()
        self._update_filter_combos()
        self.render_spools()
        self.render_filaments()
        self.render_vendors()
        self.render_printer_slots()

    def _spool_printer_badges(self):
        """Map spool_id -> list of printer/slot badge strings."""
        mapping = {}
        for ps in self.bundle.get("printer_states") or []:
            pname = ps.get("printer_name", "")
            pid = ps.get("printer_id", "")
            slots = ps.get("slots") or []
            if slots:
                for sl in slots:
                    sid = sl.get("spool_id")
                    if sid:
                        act = " " if sl.get("active") else ""
                        mapping.setdefault(int(sid), []).append(f"{pname} ({sl['label']}{act})")
            else:
                sid = ps.get("active_spool_id") or self.get_local_spool(pid)
                if sid:
                    mapping.setdefault(int(sid), []).append(f"{pname}")
        return mapping

    def _update_kpis(self):
        spools = self.bundle.get("spools") or []
        active_spools = [s for s in spools if not s.get("archived")]
        archived_count = len(spools) - len(active_spools)
        total_g = sum(float(s.get("remaining_weight") or 0.0) for s in active_spools)
        total_m = sum(float(s.get("remaining_length") or 0.0) for s in active_spools) / 1000.0
        total_val = 0.0
        low_count = 0
        for s in active_spools:
            rem = float(s.get("remaining_weight") or 0.0)
            init = spoolman.spool_initial_weight(s)
            pr = spoolman.spool_price(s)
            if pr is not None and init > 0:
                total_val += pr * min(1.0, rem / init)
            elif pr is not None:
                total_val += pr
            if 0 < rem < 150.0:
                low_count += 1

        fils = self.bundle.get("filaments") or []
        vends = self.bundle.get("vendors") or []

        arch_str = f" (+{archived_count} arch.)" if archived_count else ""
        self.kpi["spools"].setText(f"{len(active_spools)}{arch_str}")
        self.kpi["weight"].setText(f"{total_g / 1000:.2f} kg ({total_m:.0f} m)")
        self.kpi["value"].setText(f"{total_val:.2f} €")
        self.kpi["catalog"].setText(f"{len(fils)} Typen · {len(vends)} Herst.")
        self.kpi["low"].setText(f"{low_count} Spulen" if low_count else "0 (Alles OK)")
        self.kpi["low"].setStyleSheet(
            f"font-size:18px;font-weight:700;color:{'#facc15' if low_count else '#34d399'}"
        )

    def _update_filter_combos(self):
        spools = self.bundle.get("spools") or []
        mats = sorted({(s.get("filament") or {}).get("material") or "" for s in spools if (s.get("filament") or {}).get("material")})
        vends = sorted({((s.get("filament") or {}).get("vendor") or {}).get("name") or "" for s in spools if ((s.get("filament") or {}).get("vendor") or {}).get("name")})
        locs = sorted({s.get("location") or "" for s in spools if s.get("location")})

        for combo, title, items in (
            (self.sp_mat_filter, "Alle Materialien", mats),
            (self.sp_vendor_filter, "Alle Hersteller", vends),
            (self.sp_loc_filter, "Alle Orte", locs),
        ):
            cur = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(title, "")
            for it in items:
                combo.addItem(it, it)
            idx = combo.findData(cur)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            combo.blockSignals(False)

    def render_spools(self):
        spools = self.bundle.get("spools") or []
        q = self.sp_search.text().strip().lower()
        f_mat = self.sp_mat_filter.currentData() or ""
        f_ven = self.sp_vendor_filter.currentData() or ""
        f_loc = self.sp_loc_filter.currentData() or ""
        show_arch = self.sp_archived_cb.isChecked()
        badges = self._spool_printer_badges()

        selected_id = self.selected_spool_id()
        filtered = []
        for s in spools:
            if not show_arch and s.get("archived"):
                continue
            fil = s.get("filament") or {}
            ven = (fil.get("vendor") or {}).get("name") or ""
            mat = fil.get("material") or ""
            loc = s.get("location") or ""
            if f_mat and mat != f_mat:
                continue
            if f_ven and ven != f_ven:
                continue
            if f_loc and loc != f_loc:
                continue
            if q:
                extra_dec = spoolman.decode_extra(s.get("extra"))
                hay = f"#{s.get('id')} {fil.get('name', '')} {ven} {mat} {loc} {s.get('comment', '')} {extra_dec.get('card_uids', '')}".lower()
                if q not in hay:
                    continue
            filtered.append(s)

        self._filtered_spools = filtered
        self.sp_table.setRowCount(len(filtered))
        reselect_row = -1

        for i, s in enumerate(filtered):
            sid = s["id"]
            if sid == selected_id:
                reselect_row = i
            fil = s.get("filament") or {}
            ven = (fil.get("vendor") or {}).get("name") or "—"
            mat = fil.get("material") or "—"
            rem = float(s.get("remaining_weight") or 0.0)
            init = spoolman.spool_initial_weight(s)
            pct = max(0.0, min(1.0, rem / init)) if init > 0 else 0.0
            colors = spoolman.spool_colors(s)

            it_id = QTableWidgetItem(f"#{sid}")
            it_id.setData(Qt.UserRole, sid)

            fname = fil.get("name") or "?"
            if s.get("archived"):
                fname += " [Archiviert]"
            it_name = QTableWidgetItem(fname)
            it_name.setIcon(QIcon(make_spool_pixmap(colors, pct, 26)))

            et = fil.get("settings_extruder_temp")
            bt = fil.get("settings_bed_temp")
            t_str = f"{et or '—'} / {bt or '—'} °C"

            rem_str = f"{rem:.0f} g ({pct * 100:.0f}%)"
            it_rem = QTableWidgetItem(rem_str)
            if rem < 150 and not s.get("archived"):
                it_rem.setForeground(QColor("#facc15"))

            status_parts = []
            if sid in badges:
                status_parts.extend(badges[sid])
            if s.get("location"):
                status_parts.append(f"{s['location']}")
            extra_dec = spoolman.decode_extra(s.get("extra"))
            if extra_dec.get("card_uids"):
                status_parts.append("NFC")
            it_status = QTableWidgetItem(" · ".join(status_parts) if status_parts else "—")
            if sid in badges:
                it_status.setForeground(QColor("#38bdf8"))

            pr = spoolman.spool_price(s)
            pr_str = f"{pr:.2f} €" if pr is not None else "—"

            self.sp_table.setItem(i, 0, it_id)
            self.sp_table.setItem(i, 1, it_name)
            self.sp_table.setItem(i, 2, QTableWidgetItem(ven))
            self.sp_table.setItem(i, 3, QTableWidgetItem(mat))
            self.sp_table.setItem(i, 4, QTableWidgetItem(t_str))
            self.sp_table.setItem(i, 5, it_rem)
            self.sp_table.setItem(i, 6, it_status)
            self.sp_table.setItem(i, 7, QTableWidgetItem(pr_str))

        if reselect_row >= 0:
            self.sp_table.selectRow(reselect_row)
        elif filtered:
            self.sp_table.selectRow(0)
        else:
            self.update_spool_inspector()

    def selected_spool_id(self):
        row = self.sp_table.currentRow()
        if row < 0:
            return None
        it = self.sp_table.item(row, 0)
        return it.data(Qt.UserRole) if it else None

    def selected_spool(self):
        sid = self.selected_spool_id()
        if sid is None:
            return None
        return next((s for s in (self.bundle.get("spools") or []) if s.get("id") == sid), None)

    def update_spool_inspector(self):
        s = self.selected_spool()
        if not s:
            self.sp_prev_icon.setPixmap(QPixmap())
            self.sp_prev_icon.setText("Keine Spule ausgewählt")
            self.sp_info_title.setText("—")
            self.sp_fill_bar.setValue(0)
            self.sp_info_meta.setText("Wähle links eine Spule aus, um Details zu sehen oder Aktionen auszuführen.")
            for b in (
                self.btn_sp_assign, self.btn_sp_weigh, self.btn_sp_use,
                self.btn_sp_edit, self.btn_sp_dup, self.btn_sp_arch, self.btn_sp_del
            ):
                b.setEnabled(False)
            return

        fil = s.get("filament") or {}
        ven = (fil.get("vendor") or {}).get("name") or "—"
        mat = fil.get("material") or "—"
        rem = float(s.get("remaining_weight") or 0.0)
        used = float(s.get("used_weight") or 0.0)
        init = spoolman.spool_initial_weight(s)
        pct = max(0.0, min(1.0, rem / init)) if init > 0 else 0.0
        colors = spoolman.spool_colors(s)

        self.sp_prev_icon.setPixmap(make_spool_pixmap(colors, pct, 122, mat))
        self.sp_info_title.setText(spoolman.spool_display_name(s))
        self.sp_fill_bar.setValue(int(pct * 1000))

        rem_len_m = float(s.get("remaining_length") or 0.0) / 1000.0
        tare = s.get("spool_weight") or fil.get("spool_weight") or (fil.get("vendor") or {}).get("empty_spool_weight")
        pr = spoolman.spool_price(s)
        extra_dec = spoolman.decode_extra(s.get("extra"))
        badges = self._spool_printer_badges().get(s["id"], [])

        lines = [
            f"Hersteller: {ven}",
            f"Material: {mat} ({fil.get('diameter', 1.75)} mm · {fil.get('density', 1.24)} g/cm³)",
            f"Restgewicht: {rem:.1f} g / {init:.0f} g ({pct * 100:.0f}%)",
            f"Verbraucht: {used:.1f} g · Restlänge: {rem_len_m:.1f} m",
            f"Leerspule (Tara): {f'{tare:.0f} g' if tare else '—'}",
            f"Temperatur: Düse {fil.get('settings_extruder_temp') or '—'} °C / Bett {fil.get('settings_bed_temp') or '—'} °C",
            f"Farbe: {', '.join(colors)}",
        ]
        if pr is not None:
            lines.append(f"Preis: {pr:.2f} €")
        if s.get("location"):
            lines.append(f"Lagerort: {s['location']}")
        if badges:
            lines.append(f"Zugewiesen: {', '.join(badges)}")
        if extra_dec.get("card_uids"):
            lines.append(f"NFC-UID: {extra_dec['card_uids']}")
        if s.get("lot_nr"):
            lines.append(f"Lot-Nr.: {s['lot_nr']}")
        if s.get("comment"):
            lines.append(f"Notiz: {s['comment']}")

        self.sp_info_meta.setText("\n".join(lines))
        self.btn_sp_arch.setText("Wiederherstellen" if s.get("archived") else "Archivieren")
        for b in (
            self.btn_sp_assign, self.btn_sp_weigh, self.btn_sp_use,
            self.btn_sp_edit, self.btn_sp_dup, self.btn_sp_arch, self.btn_sp_del
        ):
            b.setEnabled(True)

    def _spool_context_menu(self, pos):
        s = self.selected_spool()
        if not s:
            return
        m = QMenu(self)
        a_asg = m.addAction("Drucker / Extruder zuweisen …")
        a_wgh = m.addAction("Abwiegen (Waage) …")
        a_use = m.addAction("Verbrauch buchen …")
        m.addSeparator()
        a_ed = m.addAction("Spule bearbeiten …")
        a_dup = m.addAction("Spule duplizieren")
        a_arc = m.addAction("Wiederherstellen" if s.get("archived") else "Archivieren")
        m.addSeparator()
        a_del = m.addAction("Spule löschen")
        chosen = m.exec(self.sp_table.viewport().mapToGlobal(pos))
        if chosen == a_asg:
            self.assign_selected_spool()
        elif chosen == a_wgh:
            self.weigh_selected_spool()
        elif chosen == a_use:
            self.use_selected_spool()
        elif chosen == a_ed:
            self.edit_selected_spool()
        elif chosen == a_dup:
            self.duplicate_selected_spool()
        elif chosen == a_arc:
            self.toggle_archive_selected_spool()
        elif chosen == a_del:
            self.delete_selected_spool()

    def render_filaments(self):
        fils = self.bundle.get("filaments") or []
        spools = self.bundle.get("spools") or []
        spool_counts = {}
        for s in spools:
            if not s.get("archived"):
                fid = (s.get("filament") or {}).get("id")
                if fid:
                    spool_counts[fid] = spool_counts.get(fid, 0) + 1

        q = self.fil_search.text().strip().lower()
        filtered = []
        for f in fils:
            ven = (f.get("vendor") or {}).get("name") or ""
            mat = f.get("material") or ""
            extra_dec = spoolman.decode_extra(f.get("extra"))
            var = str(extra_dec.get("variant") or "")
            if q:
                hay = f"#{f.get('id')} {f.get('name', '')} {ven} {mat} {var}".lower()
                if q not in hay:
                    continue
            filtered.append(f)

        self.fil_table.setRowCount(len(filtered))
        for i, f in enumerate(filtered):
            fid = f["id"]
            it_id = QTableWidgetItem(f"#{fid}")
            it_id.setData(Qt.UserRole, fid)

            colors = spoolman.spool_colors(f)
            it_name = QTableWidgetItem(f.get("name") or "?")
            it_name.setIcon(QIcon(make_spool_pixmap(colors, 1.0, 22)))

            ven = (f.get("vendor") or {}).get("name") or "—"
            mat = f.get("material") or "—"
            extra_dec = spoolman.decode_extra(f.get("extra"))
            var = str(extra_dec.get("variant") or "—")
            spec = f"{f.get('diameter', 1.75)} mm · {f.get('density', 1.24):.2f} g/cm³"
            w = f.get("weight") or 1000
            sw = f.get("spool_weight")
            w_str = f"{w:.0f} g" + (f" ({sw:.0f} g)" if sw else "")
            t_str = f"{f.get('settings_extruder_temp') or '—'} / {f.get('settings_bed_temp') or '—'} °C"
            cnt = str(spool_counts.get(fid, 0))

            self.fil_table.setItem(i, 0, it_id)
            self.fil_table.setItem(i, 1, it_name)
            for idx, val in enumerate((ven, mat, var, spec, w_str, t_str, cnt), start=2):
                self.fil_table.setItem(i, idx, QTableWidgetItem(val))

    def render_vendors(self):
        vends = self.bundle.get("vendors") or []
        fils = self.bundle.get("filaments") or []
        spools = self.bundle.get("spools") or []

        fil_counts = {}
        for f in fils:
            vid = (f.get("vendor") or {}).get("id")
            if vid:
                fil_counts[vid] = fil_counts.get(vid, 0) + 1

        sp_counts = {}
        for s in spools:
            if not s.get("archived"):
                vid = ((s.get("filament") or {}).get("vendor") or {}).get("id")
                if vid:
                    sp_counts[vid] = sp_counts.get(vid, 0) + 1

        q = self.ven_search.text().strip().lower()
        filtered = [v for v in vends if not q or q in f"{v.get('name', '')} {v.get('comment', '')}".lower()]
        self.ven_table.setRowCount(len(filtered))
        for i, v in enumerate(filtered):
            vid = v["id"]
            it_id = QTableWidgetItem(f"#{vid}")
            it_id.setData(Qt.UserRole, vid)
            tare = f"{v['empty_spool_weight']:.0f} g" if v.get("empty_spool_weight") is not None else "—"
            self.ven_table.setItem(i, 0, it_id)
            self.ven_table.setItem(i, 1, QTableWidgetItem(v.get("name") or "?"))
            self.ven_table.setItem(i, 2, QTableWidgetItem(tare))
            self.ven_table.setItem(i, 3, QTableWidgetItem(str(fil_counts.get(vid, 0))))
            self.ven_table.setItem(i, 4, QTableWidgetItem(str(sp_counts.get(vid, 0))))
            self.ven_table.setItem(i, 5, QTableWidgetItem(v.get("comment") or "—"))

    def render_printer_slots(self):
        while self.printers_layout.count():
            item = self.printers_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        printers = getattr(self.win, "printers", [])
        p_states = {ps["printer_id"]: ps for ps in (self.bundle.get("printer_states") or [])}
        spools_by_id = {s["id"]: s for s in (self.bundle.get("spools") or [])}

        if not printers:
            lbl = QLabel("Noch keine Drucker eingerichtet.")
            lbl.setObjectName("dim")
            self.printers_layout.addWidget(lbl)
            return

        for p in printers:
            ps = p_states.get(p.id) or {"online": False, "slots": []}
            c = QFrame()
            c.setObjectName("card")
            cl = QVBoxLayout(c)
            cl.setSpacing(10)

            hdr = QHBoxLayout()
            title = QLabel(f"<b>{p.name}</b> ({p.host}:{p.port})")
            title.setStyleSheet("font-size:16px")
            st_lbl = QLabel("Online" if ps.get("online") else "Offline")
            st_lbl.setStyleSheet(f"color:{'#34d399' if ps.get('online') else '#f87171'};font-weight:700")
            hdr.addWidget(title)
            hdr.addSpacing(8)
            hdr.addWidget(st_lbl)
            hdr.addStretch()

            active_sid = ps.get("active_spool_id") or self.get_local_spool(p.id)
            act_spool = spools_by_id.get(int(active_sid)) if active_sid else None
            act_txt = spoolman.spool_display_name(act_spool) if act_spool else "Keine aktive Hauptspule"
            act_badge = QLabel(f"Aktive Spule: <b>{act_txt}</b>")
            hdr.addWidget(act_badge)
            cl.addLayout(hdr)

            slots = ps.get("slots") or []
            if slots:
                grid = QGridLayout()
                grid.setSpacing(10)
                for idx, sl in enumerate(slots):
                    sc = QFrame()
                    sc.setStyleSheet(
                        "QFrame { background:#0b131f; border:1px solid #1e3148; border-radius:10px; padding:8px; }"
                    )
                    scl = QVBoxLayout(sc)
                    top_s = QHBoxLayout()
                    slot_title = QLabel(f"<b>Slot {sl['label']}</b> ({sl['extruder']})")
                    if sl.get("active"):
                        b_act = QLabel("AKTIV")
                        b_act.setStyleSheet("color:#38bdf8;font-weight:700")
                    else:
                        b_act = QLabel("Bereit" if sl.get("exist") else "Kein Filament")
                        b_act.setObjectName("dim")
                    top_s.addWidget(slot_title)
                    top_s.addStretch()
                    top_s.addWidget(b_act)
                    scl.addLayout(top_s)

                    sid = sl.get("spool_id")
                    sp = spools_by_id.get(int(sid)) if sid else None
                    sp_row = QHBoxLayout()
                    icon_lbl = QLabel()
                    if sp:
                        rem = float(sp.get("remaining_weight") or 0.0)
                        init = spoolman.spool_initial_weight(sp)
                        icon_lbl.setPixmap(make_spool_pixmap(spoolman.spool_colors(sp), rem / init if init else 1.0, 32))
                        sp_txt = QLabel(f"<b>{spoolman.spool_display_name(sp)}</b><br><span style='color:#8198af'>Rest: {rem:.0f} g</span>")
                    else:
                        icon_lbl.setPixmap(make_spool_pixmap([sl.get("color") or "#64748b"], 0.3, 32))
                        sp_txt = QLabel("<i>Keine Spoolman-Spule zugewiesen</i>")
                    sp_txt.setWordWrap(True)
                    sp_row.addWidget(icon_lbl)
                    sp_row.addWidget(sp_txt, 1)
                    scl.addLayout(sp_row)

                    uid = sl.get("card_uid")
                    uid_lbl = QLabel(f"NFC-UID: <code>{uid}</code>" if uid else "NFC: Kein Tag erkannt")
                    uid_lbl.setObjectName("dim")
                    scl.addWidget(uid_lbl)

                    btn_row = QHBoxLayout()
                    b_choose = QPushButton("Spule wählen …")
                    b_choose.clicked.connect(lambda _, pr=p, ch=sl["channel"], u=uid: self._choose_spool_for_slot(pr, ch, u))
                    btn_row.addWidget(b_choose)
                    if sid:
                        b_clr = QPushButton("Lösen")
                        b_clr.clicked.connect(lambda _, pr=p, ch=sl["channel"]: self._clear_slot_spool(pr, ch))
                        btn_row.addWidget(b_clr)
                    scl.addLayout(btn_row)
                    grid.addWidget(sc, idx // 2, idx % 2)
                cl.addLayout(grid)
            else:
                # Single extruder printer row
                srow = QHBoxLayout()
                b_choose = QPushButton("Aktive Spule zuweisen / wechseln …")
                b_choose.setObjectName("primary")
                b_choose.clicked.connect(lambda _, pr=p: self._choose_spool_for_slot(pr, None, ""))
                srow.addWidget(b_choose)
                if active_sid:
                    b_clr = QPushButton("Zuweisung aufheben")
                    b_clr.clicked.connect(lambda _, pr=p: self._clear_slot_spool(pr, None))
                    srow.addWidget(b_clr)
                srow.addStretch()
                cl.addLayout(srow)

            self.printers_layout.addWidget(c)

        self.printers_layout.addStretch()

    def add_spool(self, preselect_filament_id=None):
        base = self.bundle.get("url") or self.get_url()
        if not base:
            QMessageBox.warning(self, "Spoolman", "Keine Spoolman Server-URL konfiguriert.")
            return
        fils = self.bundle.get("filaments") or []
        fake_spool = {"filament": {"id": preselect_filament_id}} if preselect_filament_id else None
        dlg = SpoolDialog(
            self,
            base,
            fils,
            self.bundle.get("vendors"),
            self.bundle.get("materials"),
            self.bundle.get("locations"),
            self.bundle.get("printer_states"),
            spool=None,
        )
        if preselect_filament_id:
            idx = dlg.fil_combo.findData(preselect_filament_id)
            if idx >= 0:
                dlg.fil_combo.setCurrentIndex(idx)
                dlg._on_filament_selected()
        if dlg.exec():
            payload = dlg.payload()
            self.run_async(lambda: spoolman.create_spool(base, payload), self._after_mutation)

    def edit_selected_spool(self):
        s = self.selected_spool()
        if not s:
            return
        base = self.bundle.get("url") or self.get_url()
        dlg = SpoolDialog(
            self,
            base,
            self.bundle.get("filaments"),
            self.bundle.get("vendors"),
            self.bundle.get("materials"),
            self.bundle.get("locations"),
            self.bundle.get("printer_states"),
            spool=s,
        )
        if dlg.exec():
            payload = dlg.payload()
            sid = s["id"]
            self.run_async(lambda: spoolman.update_spool(base, sid, payload), self._after_mutation)

    def duplicate_selected_spool(self):
        s = self.selected_spool()
        if not s:
            return
        base = self.bundle.get("url") or self.get_url()
        fil = s.get("filament") or {}
        init_w = spoolman.spool_initial_weight(s)
        payload = {
            "filament_id": fil.get("id"),
            "initial_weight": init_w,
            "remaining_weight": init_w,
            "spool_weight": s.get("spool_weight"),
            "price": s.get("price"),
            "location": s.get("location"),
            "lot_nr": s.get("lot_nr"),
            "comment": s.get("comment"),
        }
        self.run_async(lambda: spoolman.create_spool(base, payload), self._after_mutation)

    def toggle_archive_selected_spool(self):
        s = self.selected_spool()
        if not s:
            return
        base = self.bundle.get("url") or self.get_url()
        sid = s["id"]
        new_arch = not bool(s.get("archived"))
        self.run_async(lambda: spoolman.update_spool(base, sid, {"archived": new_arch}), self._after_mutation)

    def delete_selected_spool(self):
        s = self.selected_spool()
        if not s:
            return
        if QMessageBox.question(
            self,
            "Spule löschen",
            f"Soll „{spoolman.spool_display_name(s)}“ wirklich dauerhaft aus Spoolman gelöscht werden?",
        ) != QMessageBox.Yes:
            return
        base = self.bundle.get("url") or self.get_url()
        sid = s["id"]
        self.run_async(lambda: spoolman.delete_spool(base, sid), self._after_mutation)

    def weigh_selected_spool(self):
        s = self.selected_spool()
        if not s:
            return
        dlg = MeasureSpoolDialog(self, s)
        if dlg.exec():
            base = self.bundle.get("url") or self.get_url()
            sid = s["id"]
            gw = dlg.gross_weight()
            self.run_async(lambda: spoolman.measure_spool(base, sid, gw), self._after_mutation)

    def use_selected_spool(self):
        s = self.selected_spool()
        if not s:
            return
        dlg = UseSpoolDialog(self, s)
        if dlg.exec():
            base = self.bundle.get("url") or self.get_url()
            sid = s["id"]
            u = dlg.usage()
            self.run_async(
                lambda: spoolman.use_spool(base, sid, use_weight=u["use_weight"], use_length=u["use_length"]),
                self._after_mutation,
            )

    def assign_selected_spool(self):
        s = self.selected_spool()
        if not s:
            return
        printers = getattr(self.win, "printers", [])
        if not printers:
            QMessageBox.information(self, "Kein Drucker", "Bitte zuerst einen Drucker hinzufügen.")
            return
        dlg = AssignSpoolDialog(self, s, printers, self.bundle.get("printer_states"))
        if dlg.exec():
            sel = dlg.selection()
            p = sel["printer"]
            ch = sel["channel"]
            uid = sel["card_uid"]
            base = self.bundle.get("url") or self.get_url()
            sid = s["id"]

            def task():
                if uid and base:
                    spoolman.link_nfc_uid_to_spool(base, s, uid)
                try:
                    spoolman.assign_spool_to_printer(p, sid, channel=ch)
                except Exception:
                    self.set_local_spool(p.id, sid)
                else:
                    self.set_local_spool(p.id, sid)
                return True

            self.run_async(task, self._after_mutation)

    def _choose_spool_for_slot(self, printer, channel, card_uid=""):
        spools = [s for s in (self.bundle.get("spools") or []) if not s.get("archived")]
        if not spools:
            QMessageBox.information(self, "Keine Spulen", "Bitte lege zuerst eine Spule in Spoolman an.")
            return
        items = [f"{spoolman.spool_display_name(s)} – {float(s.get('remaining_weight') or 0):.0f} g" for s in spools]
        choice, ok = QInputDialog.getItem(
            self,
            f"Spule für {printer.name}" + (f" (T{channel})" if channel is not None else ""),
            "Spoolman-Spule auswählen:",
            items,
            0,
            False,
        )
        if not ok or not choice:
            return
        idx = items.index(choice)
        spool = spools[idx]
        sid = spool["id"]
        base = self.bundle.get("url") or self.get_url()

        def task():
            if card_uid and base:
                spoolman.link_nfc_uid_to_spool(base, spool, card_uid)
            try:
                spoolman.assign_spool_to_printer(printer, sid, channel=channel)
            except Exception:
                self.set_local_spool(printer.id, sid)
            else:
                if channel is None:
                    self.set_local_spool(printer.id, sid)
            return True

        self.run_async(task, self._after_mutation)

    def _clear_slot_spool(self, printer, channel):
        def task():
            try:
                spoolman.assign_spool_to_printer(printer, None, channel=channel)
            except Exception:
                pass
            if channel is None:
                self.set_local_spool(printer.id, 0)
            return True

        self.run_async(task, self._after_mutation)

    def selected_filament(self):
        row = self.fil_table.currentRow()
        if row < 0:
            return None
        it = self.fil_table.item(row, 0)
        fid = it.data(Qt.UserRole) if it else None
        return next((f for f in (self.bundle.get("filaments") or []) if f.get("id") == fid), None)

    def add_filament(self):
        base = self.bundle.get("url") or self.get_url()
        if not base:
            return
        dlg = FilamentDialog(self, base, self.bundle.get("vendors"), self.bundle.get("materials"))
        if dlg.exec():
            payload = dlg.payload()
            self.run_async(lambda: spoolman.create_filament(base, payload), self._after_mutation)

    def edit_selected_filament(self):
        f = self.selected_filament()
        if not f:
            return
        base = self.bundle.get("url") or self.get_url()
        dlg = FilamentDialog(self, base, self.bundle.get("vendors"), self.bundle.get("materials"), filament=f)
        if dlg.exec():
            payload = dlg.payload()
            fid = f["id"]
            self.run_async(lambda: spoolman.update_filament(base, fid, payload), self._after_mutation)

    def delete_selected_filament(self):
        f = self.selected_filament()
        if not f:
            return
        if QMessageBox.question(
            self,
            "Filament löschen",
            f"Soll das Filament „{f.get('name')}“ wirklich gelöscht werden?\n(Nur möglich, wenn keine Spulen mehr damit verknüpft sind.)",
        ) != QMessageBox.Yes:
            return
        base = self.bundle.get("url") or self.get_url()
        fid = f["id"]
        self.run_async(lambda: spoolman.delete_filament(base, fid), self._after_mutation)

    def add_spool_for_selected_filament(self):
        f = self.selected_filament()
        if not f:
            QMessageBox.information(self, "Auswahl", "Bitte wähle zuerst ein Filament in der Tabelle aus.")
            return
        self.add_spool(preselect_filament_id=f["id"])

    def import_from_external_db(self):
        base = self.bundle.get("url") or self.get_url()
        if not base:
            return
        dlg = ExternalFilamentDialog(self, base, self.bundle.get("vendors"), self.run_async)
        if dlg.exec() and dlg.imported_filament:
            imp = dlg.imported_filament
            if dlg.create_spool_checked:
                w = float(imp.get("weight") or 1000.0)
                sp_payload = {
                    "filament_id": imp["id"],
                    "initial_weight": w,
                    "remaining_weight": w,
                    "spool_weight": imp.get("spool_weight"),
                }
                self.run_async(lambda: spoolman.create_spool(base, sp_payload), self._after_mutation)
            else:
                self.reload()

    def selected_vendor(self):
        row = self.ven_table.currentRow()
        if row < 0:
            return None
        it = self.ven_table.item(row, 0)
        vid = it.data(Qt.UserRole) if it else None
        return next((v for v in (self.bundle.get("vendors") or []) if v.get("id") == vid), None)

    def add_vendor(self):
        base = self.bundle.get("url") or self.get_url()
        if not base:
            return
        dlg = VendorDialog(self)
        if dlg.exec():
            payload = dlg.payload()
            self.run_async(lambda: spoolman.create_vendor(base, payload), self._after_mutation)

    def edit_selected_vendor(self):
        v = self.selected_vendor()
        if not v:
            return
        base = self.bundle.get("url") or self.get_url()
        dlg = VendorDialog(self, vendor=v)
        if dlg.exec():
            payload = dlg.payload()
            vid = v["id"]
            self.run_async(lambda: spoolman.update_vendor(base, vid, payload), self._after_mutation)

    def delete_selected_vendor(self):
        v = self.selected_vendor()
        if not v:
            return
        if QMessageBox.question(
            self,
            "Hersteller löschen",
            f"Soll der Hersteller „{v.get('name')}“ wirklich gelöscht werden?",
        ) != QMessageBox.Yes:
            return
        base = self.bundle.get("url") or self.get_url()
        vid = v["id"]
        self.run_async(lambda: spoolman.delete_vendor(base, vid), self._after_mutation)

    def create_backup(self):
        base = self.bundle.get("url") or self.get_url()
        if not base:
            return
        self.run_async(
            lambda: spoolman.trigger_backup(base),
            lambda r: QMessageBox.information(
                self,
                "Spoolman Datenbank-Backup",
                f"Backup erfolgreich auf dem Spoolman-Server gespeichert:\n{r[1].get('path', '')}"
                if r[0] == "ok" else f"Fehler beim Backup:\n{r[1]}",
            ),
        )

    def open_web_ui(self):
        base = self.bundle.get("url") or self.get_url()
        if base:
            QDesktopServices.openUrl(QUrl(base))

    def _after_mutation(self, r):
        if r and r[0] == "err":
            QMessageBox.warning(self, "Spoolman Fehler", str(r[1]))
            return
        self.reload()
        if hasattr(self.win, "poll"):
            self.win.poll()
