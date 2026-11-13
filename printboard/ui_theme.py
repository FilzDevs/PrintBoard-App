"""Design system, geometric vector icon engine, colored analytical charts,
print queue, maintenance tracker, and command palette for PrintBoard.
"""
from collections import deque
import datetime
import json
import math
import time
from pathlib import Path

from PySide6.QtCore import Qt, QRectF, QPointF, QSize, Signal
from PySide6.QtGui import (
    QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath,
    QPen, QPixmap, QBrush, QPolygonF
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QDialog, QLineEdit, QListWidget, QListWidgetItem, QComboBox,
    QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QCheckBox
)

from . import api, costs, spoolman, store

THEMES = {
    "obsidian": {
        "name": "Obsidian Studio",
        "bg_main": "#070A10",
        "bg_sidebar": "#0A0E17",
        "bg_surface": "#0E1420",
        "bg_elevated": "#131C2B",
        "bg_input": "#090D14",
        "border": "#1B2638",
        "border_hover": "#2B3E59",
        "text": "#F1F5F9",
        "text_dim": "#8799B0",
        "text_muted": "#51637A",
        "accent": "#06B6D4",
        "accent_alt": "#3B82F6",
        "accent_fg": "#041016",
        "success": "#10B981",
        "warning": "#F59E0B",
        "danger": "#F43F5E",
    },
    "graphite": {
        "name": "Graphite Pro",
        "bg_main": "#09090B",
        "bg_sidebar": "#0F0F13",
        "bg_surface": "#15151B",
        "bg_elevated": "#1D1D25",
        "bg_input": "#0D0D11",
        "border": "#262630",
        "border_hover": "#3B3B4A",
        "text": "#FAFAFA",
        "text_dim": "#A1A1AA",
        "text_muted": "#6E6E77",
        "accent": "#6366F1",
        "accent_alt": "#8B5CF6",
        "accent_fg": "#FFFFFF",
        "success": "#10B981",
        "warning": "#F59E0B",
        "danger": "#EF4444",
    },
    "light": {
        "name": "Daylight Clean",
        "bg_main": "#F1F5F9",
        "bg_sidebar": "#FFFFFF",
        "bg_surface": "#FFFFFF",
        "bg_elevated": "#F8FAFC",
        "bg_input": "#FFFFFF",
        "border": "#E2E8F0",
        "border_hover": "#94A3B8",
        "text": "#0F172A",
        "text_dim": "#475569",
        "text_muted": "#94A3B8",
        "accent": "#0284C7",
        "accent_alt": "#2563EB",
        "accent_fg": "#FFFFFF",
        "success": "#059669",
        "warning": "#D97706",
        "danger": "#E11D48",
    },
}

CHART_PALETTE = [
    "#06B6D4",  # Cyan
    "#8B5CF6",  # Violet
    "#F59E0B",  # Amber
    "#10B981",  # Emerald
    "#F43F5E",  # Rose
    "#3B82F6",  # Blue
    "#EC4899",  # Pink
]


def build_qss(theme_key: str = "obsidian") -> str:
    t = THEMES.get(theme_key, THEMES["obsidian"])
    return f"""
    QWidget {{
        background: {t['bg_main']};
        color: {t['text']};
        font-size: 13px;
        font-family: "Inter", "SF Pro Display", "Segoe UI", Roboto, sans-serif;
    }}
    QMainWindow::separator {{
        background: {t['border']};
    }}
    QStatusBar {{
        background: {t['bg_sidebar']};
        color: {t['text_dim']};
        border-top: 1px solid {t['border']};
        padding: 4px 12px;
        font-size: 11.5px;
    }}
    QFrame#topbar {{
        background: {t['bg_sidebar']};
        border-bottom: 1px solid {t['border']};
    }}
    QListWidget#sidebar {{
        background: {t['bg_sidebar']};
        border: 0;
        padding: 10px 8px;
        min-width: 216px;
        max-width: 216px;
        outline: none;
    }}
    QListWidget#sidebar::item {{
        padding: 10px 13px;
        margin-bottom: 3px;
        border-radius: 9px;
        color: {t['text_dim']};
        font-weight: 600;
        font-size: 13px;
    }}
    QListWidget#sidebar::item:hover {{
        background: {t['bg_elevated']};
        color: {t['text']};
    }}
    QListWidget#sidebar::item:selected {{
        background: {t['bg_elevated']};
        color: {t['accent']};
        font-weight: 700;
        border-left: 3px solid {t['accent']};
    }}
    QListWidget {{
        background: {t['bg_surface']};
        border: 1px solid {t['border']};
        border-radius: 11px;
        padding: 8px;
        outline: none;
    }}
    QListWidget::item {{
        padding: 8px 10px;
        border-radius: 7px;
    }}
    QListWidget::item:selected {{
        background: {t['bg_elevated']};
        color: {t['accent']};
    }}
    QFrame#card {{
        background: {t['bg_surface']};
        border: 1px solid {t['border']};
        border-radius: 13px;
    }}
    QFrame#card:hover {{
        border: 1px solid {t['border_hover']};
    }}
    QFrame#card QLabel {{
        background: transparent;
    }}
    QFrame#metric_pill {{
        background: {t['bg_elevated']};
        border: 1px solid {t['border']};
        border-radius: 9px;
    }}
    QFrame#metric_pill QLabel {{
        background: transparent;
    }}
    QLabel#h1 {{
        font-size: 20px;
        font-weight: 800;
        color: {t['text']};
        letter-spacing: -0.4px;
        background: transparent;
    }}
    QLabel#h2 {{
        font-size: 14px;
        font-weight: 700;
        color: {t['text']};
        background: transparent;
    }}
    QLabel#dim {{
        color: {t['text_dim']};
        font-size: 12px;
        background: transparent;
    }}
    QPushButton {{
        background: {t['bg_elevated']};
        border: 1px solid {t['border']};
        border-radius: 8px;
        padding: 7px 14px;
        font-weight: 600;
        color: {t['text']};
    }}
    QPushButton:hover {{
        background: {t['bg_surface']};
        border-color: {t['accent']};
        color: {t['accent']};
    }}
    QPushButton:disabled {{
        background: {t['bg_input']};
        color: {t['text_muted']};
        border-color: {t['border']};
    }}
    QPushButton#primary {{
        background: {t['accent']};
        border: 1px solid {t['accent']};
        color: {t['accent_fg']};
        font-weight: 700;
    }}
    QPushButton#primary:hover {{
        background: {t['accent_alt']};
        border-color: {t['accent_alt']};
        color: #FFFFFF;
    }}
    QPushButton#danger {{
        background: rgba(244, 63, 94, 0.14);
        border: 1px solid {t['danger']};
        color: {t['danger']};
        font-weight: 700;
    }}
    QPushButton#danger:hover {{
        background: {t['danger']};
        color: #FFFFFF;
    }}
    QPushButton#warn {{
        background: rgba(245, 158, 11, 0.14);
        border: 1px solid {t['warning']};
        color: {t['warning']};
        font-weight: 700;
    }}
    QPushButton#ghost {{
        background: transparent;
        border: 1px solid {t['border']};
        color: {t['text_dim']};
        padding: 5px 11px;
        border-radius: 7px;
    }}
    QPushButton#ghost:hover {{
        border-color: {t['accent']};
        color: {t['accent']};
        background: {t['bg_elevated']};
    }}
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit {{
        background: {t['bg_input']};
        border: 1px solid {t['border']};
        border-radius: 8px;
        padding: 7px 11px;
        color: {t['text']};
        selection-background-color: {t['accent']};
        selection-color: {t['accent_fg']};
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus {{
        border: 1px solid {t['accent']};
    }}
    QProgressBar {{
        background: {t['bg_input']};
        border: 1px solid {t['border']};
        border-radius: 5px;
        height: 8px;
        text-align: center;
        color: transparent;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {t['accent_alt']}, stop:1 {t['accent']});
        border-radius: 4px;
    }}
    QTabWidget::pane {{
        border: 1px solid {t['border']};
        border-radius: 11px;
        background: {t['bg_surface']};
    }}
    QTabBar::tab {{
        background: {t['bg_elevated']};
        border: 1px solid {t['border']};
        padding: 8px 16px;
        margin-right: 5px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        color: {t['text_dim']};
        font-weight: 600;
    }}
    QTabBar::tab:selected {{
        background: {t['bg_surface']};
        color: {t['accent']};
        border-bottom-color: {t['bg_surface']};
        font-weight: 700;
    }}
    QTableWidget {{
        background: {t['bg_surface']};
        alternate-background-color: {t['bg_elevated']};
        border: 1px solid {t['border']};
        border-radius: 11px;
        gridline-color: {t['border']};
    }}
    QHeaderView::section {{
        background: {t['bg_elevated']};
        color: {t['text_dim']};
        padding: 8px 10px;
        border: 0;
        border-bottom: 1px solid {t['border']};
        font-weight: 700;
        font-size: 11px;
        text-transform: uppercase;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {t['border_hover']};
        min-height: 24px;
        border-radius: 4px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollArea {{
        background: transparent;
        border: none;
    }}
    """


def make_vector_icon(kind: str, color_hex: str = "#8799B0", size: int = 18) -> QIcon:
    pm = QPixmap(size * 2, size * 2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(2.0, 2.0)

    col = QColor(color_hex)
    pen = QPen(col, 1.65, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    s = float(size)
    if kind == "printers":
        p.drawRoundedRect(QRectF(2.5, 2.5, s - 5, s - 5), 2.5, 2.5)
        p.drawLine(QPointF(5, s - 5.5), QPointF(s - 5, s - 5.5))
        p.drawRect(QRectF(s / 2 - 2, 5, 4, 3.5))
        p.drawLine(QPointF(s / 2, 8.5), QPointF(s / 2, 10.5))
    elif kind == "spool":
        c = QPointF(s / 2, s / 2)
        p.drawEllipse(c, s / 2 - 2.2, s / 2 - 2.2)
        p.drawEllipse(c, 2.6, 2.6)
        p.drawLine(QPointF(s / 2, 2.2), QPointF(s / 2, s / 2 - 2.6))
        p.drawLine(QPointF(s / 2, s / 2 + 2.6), QPointF(s / 2, s - 2.2))
    elif kind == "queue":
        p.drawLine(QPointF(7, 5), QPointF(s - 2.5, 5))
        p.drawLine(QPointF(7, s / 2), QPointF(s - 2.5, s / 2))
        p.drawLine(QPointF(7, s - 5), QPointF(s - 2.5, s - 5))
        poly = QPolygonF([QPointF(2.5, 3.3), QPointF(5.5, 5.0), QPointF(2.5, 6.7)])
        p.setBrush(col)
        p.drawPolygon(poly)
    elif kind == "maintenance":
        p.drawEllipse(QPointF(6.5, 6.5), 3.2, 3.2)
        p.drawLine(QPointF(8.8, 8.8), QPointF(s - 3.0, s - 3.0))
        p.drawLine(QPointF(s - 5.2, s - 3.0), QPointF(s - 3.0, s - 5.2))
    elif kind == "stats":
        p.drawLine(QPointF(3, s - 3), QPointF(s - 3, s - 3))
        p.drawRoundedRect(QRectF(4, s - 8.5, 2.5, 5.5), 1, 1)
        p.drawRoundedRect(QRectF(8, s - 13, 2.5, 10), 1, 1)
        p.drawRoundedRect(QRectF(12, s - 10.5, 2.5, 7.5), 1, 1)
    elif kind == "library":
        p.drawEllipse(QPointF(s / 2, 5.2), s / 2 - 3, 2.2)
        p.drawLine(QPointF(3, 5.2), QPointF(3, s - 5))
        p.drawLine(QPointF(s - 3, 5.2), QPointF(s - 3, s - 5))
        p.drawArc(QRectF(3, s - 7.5, s - 6, 4.5), 180 * 16, 180 * 16)
    elif kind == "globe":
        c = QPointF(s / 2, s / 2)
        r = s / 2 - 2.2
        p.drawEllipse(c, r, r)
        p.drawEllipse(c, r * 0.48, r)
        p.drawLine(QPointF(2.2, s / 2), QPointF(s - 2.2, s / 2))
    elif kind == "settings":
        c = QPointF(s / 2, s / 2)
        p.drawEllipse(c, 2.8, 2.8)
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            p.drawLine(
                QPointF(c.x() + math.cos(rad) * 4.5, c.y() + math.sin(rad) * 4.5),
                QPointF(c.x() + math.cos(rad) * 6.8, c.y() + math.sin(rad) * 6.8),
            )
    elif kind == "camera":
        p.drawRoundedRect(QRectF(2.2, 4.5, s - 7.2, s - 9), 2, 2)
        poly = QPolygonF([
            QPointF(s - 5.0, 7.2),
            QPointF(s - 1.8, 5.0),
            QPointF(s - 1.8, s - 5.0),
            QPointF(s - 5.0, s - 7.2),
        ])
        p.drawPolygon(poly)
    elif kind == "search":
        p.drawEllipse(QPointF(7.5, 7.5), 4.5, 4.5)
        p.drawLine(QPointF(10.8, 10.8), QPointF(s - 2.5, s - 2.5))
    elif kind == "plus":
        p.drawLine(QPointF(s / 2, 3.5), QPointF(s / 2, s - 3.5))
        p.drawLine(QPointF(3.5, s / 2), QPointF(s - 3.5, s / 2))
    elif kind == "refresh":
        p.drawArc(QRectF(3, 3, s - 6, s - 6), 35 * 16, 290 * 16)
        p.drawLine(QPointF(s - 3.5, 3.2), QPointF(s - 3.5, 6.8))
        p.drawLine(QPointF(s - 6.8, 6.8), QPointF(s - 3.5, 6.8))
    elif kind == "back":
        p.drawLine(QPointF(s - 3.5, s / 2), QPointF(4.0, s / 2))
        p.drawLine(QPointF(8.0, s / 2 - 4.0), QPointF(4.0, s / 2))
        p.drawLine(QPointF(8.0, s / 2 + 4.0), QPointF(4.0, s / 2))
    elif kind == "external":
        p.drawRoundedRect(QRectF(3, 5, s - 8, s - 8), 1.8, 1.8)
        p.drawLine(QPointF(8.5, s - 8.5), QPointF(s - 3, 3))
        p.drawLine(QPointF(s - 7, 3), QPointF(s - 3, 3))
        p.drawLine(QPointF(s - 3, 3), QPointF(s - 3, 7))
    elif kind == "grid":
        w2 = (s - 7) / 2
        p.drawRoundedRect(QRectF(2.5, 2.5, w2, w2), 1.5, 1.5)
        p.drawRoundedRect(QRectF(4.5 + w2, 2.5, w2, w2), 1.5, 1.5)
        p.drawRoundedRect(QRectF(2.5, 4.5 + w2, w2, w2), 1.5, 1.5)
        p.drawRoundedRect(QRectF(4.5 + w2, 4.5 + w2, w2, w2), 1.5, 1.5)
    elif kind == "play":
        poly = QPolygonF([QPointF(5, 3.5), QPointF(s - 4, s / 2), QPointF(5, s - 3.5)])
        p.setBrush(col)
        p.drawPolygon(poly)
    elif kind == "pause":
        p.drawRoundedRect(QRectF(4.5, 4, 2.8, s - 8), 1, 1)
        p.drawRoundedRect(QRectF(s - 7.3, 4, 2.8, s - 8), 1, 1)
    elif kind == "flame":
        path = QPainterPath()
        path.moveTo(s / 2, 2.5)
        path.cubicTo(s - 3, 6.5, s - 3, s - 3, s / 2, s - 2.5)
        path.cubicTo(3, s - 3, 3, 6.5, s / 2, 2.5)
        p.drawPath(path)

    p.end()
    return QIcon(pm)


class RadialProgressGauge(QWidget):
    """Dual-track circular arc gauge displaying print progress, state ring, and thumbnail."""

    def __init__(self, size: int = 86):
        super().__init__()
        self.setFixedSize(size, size)
        self._progress = 0.0
        self._color = QColor("#06B6D4")
        self._track_color = QColor("#182334")
        self._label = "0%"
        self._sublabel = "BEREIT"
        self._thumb = None

    def set_data(self, progress: float, color_hex: str, label: str, sublabel: str = "", thumb_pm: QPixmap = None):
        self._progress = max(0.0, min(1.0, float(progress or 0.0)))
        self._color = QColor(color_hex)
        self._label = label
        self._sublabel = sublabel
        self._thumb = thumb_pm
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        pad = 5.0
        rect = QRectF(pad, pad, w - 2 * pad, h - 2 * pad)

        if self._thumb and not self._thumb.isNull():
            inner_r = rect.adjusted(6, 6, -6, -6)
            path = QPainterPath()
            path.addEllipse(inner_r)
            p.save()
            p.setClipPath(path)
            scaled = self._thumb.scaled(
                int(inner_r.width()), int(inner_r.height()),
                Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            p.drawPixmap(int(inner_r.x()), int(inner_r.y()), scaled)
            p.fillRect(inner_r, QColor(6, 9, 15, 160))
            p.restore()

        p.setPen(QPen(self._track_color, 5.2, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(rect, 0, 360 * 16)

        if self._progress > 0.003:
            p.setPen(QPen(self._color, 5.2, Qt.SolidLine, Qt.RoundCap))
            span = int(-self._progress * 360 * 16)
            p.drawArc(rect, 90 * 16, span)

        f_main = QFont("Inter", 12, QFont.Bold)
        p.setFont(f_main)
        p.setPen(QColor("#F8FAFC"))
        p.drawText(QRectF(0, h * 0.24, w, h * 0.30), Qt.AlignCenter, self._label)

        if self._sublabel:
            f_sub = QFont("Inter", 7, QFont.Bold)
            p.setFont(f_sub)
            p.setPen(self._color)
            p.drawText(QRectF(0, h * 0.54, w, h * 0.22), Qt.AlignCenter, self._sublabel[:10].upper())

        p.end()


class TempSparklineChart(QFrame):
    """Real-time multi-channel colored temperature chart with gradient fills and target markers."""

    def __init__(self, max_points: int = 80, height: int = 165):
        super().__init__()
        self.setObjectName("card")
        self.setMinimumHeight(height)
        self.max_points = max_points
        self.series = {}
        self.targets = {}

    def push_temps(self, temps_list):
        if not temps_list:
            return
        for name, cur, tgt in temps_list:
            if cur is None:
                continue
            if name not in self.series:
                self.series[name] = deque(maxlen=self.max_points)
            self.series[name].append(float(cur))
            self.targets[name] = float(tgt or 0.0)
        self.update()

    def clear_history(self):
        self.series.clear()
        self.targets.clear()
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        left, right, top, bottom = 42, 16, 36, 22
        cw = max(40, w - left - right)
        ch = max(30, h - top - bottom)

        p.setPen(QColor("#94A3B8"))
        p.setFont(QFont("Inter", 9, QFont.Bold))
        p.drawText(14, 21, "THERMISCHE TELEMETRIE (°C)")

        max_temp = 260.0
        for dq in self.series.values():
            if dq:
                max_temp = max(max_temp, max(dq) + 20.0)
        max_temp = min(320.0, max(100.0, math.ceil(max_temp / 50.0) * 50.0))

        p.setFont(QFont("Inter", 8))
        for frac in (0.0, 0.5, 1.0):
            gy = top + ch * (1.0 - frac)
            p.setPen(QPen(QColor("#1B2638"), 1, Qt.DashLine))
            p.drawLine(int(left), int(gy), int(w - right), int(gy))
            p.setPen(QColor("#64748B"))
            val_lbl = f"{int(frac * max_temp)}°"
            p.drawText(QRectF(4, gy - 8, left - 8, 16), Qt.AlignRight | Qt.AlignVCenter, val_lbl)

        if not self.series:
            p.setPen(QColor("#64748B"))
            p.setFont(QFont("Inter", 10))
            p.drawText(QRectF(left, top, cw, ch), Qt.AlignCenter, "Warte auf Temperatur-Telemetrie ...")
            p.end()
            return

        legend_x = w - right
        for idx, (name, dq) in enumerate(list(self.series.items())[:5]):
            if not dq:
                continue
            col = QColor(CHART_PALETTE[idx % len(CHART_PALETTE)])
            pts = list(dq)
            cur_val = pts[-1]
            tgt_val = self.targets.get(name, 0.0)

            leg_txt = f"{name}: {cur_val:.1f}°C" + (f" / {tgt_val:.0f}°C" if tgt_val > 0 else "")
            p.setFont(QFont("Inter", 8, QFont.Bold))
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(leg_txt) + 18
            legend_x -= tw
            if legend_x > 190:
                p.setBrush(col)
                p.setPen(Qt.NoPen)
                p.drawRoundedRect(QRectF(legend_x, 12, 8, 8), 2, 2)
                p.setPen(col)
                p.drawText(int(legend_x + 12), 20, leg_txt)

            if tgt_val > 0:
                ty = top + ch * (1.0 - min(1.0, tgt_val / max_temp))
                tpen = QPen(col, 1.0, Qt.DotLine)
                p.setPen(tpen)
                p.drawLine(int(left), int(ty), int(w - right), int(ty))

            n = len(pts)
            path = QPainterPath()
            fill_path = QPainterPath()
            for i, val in enumerate(pts):
                px = left + (cw * (i / max(1, self.max_points - 1))) if n < self.max_points else left + (cw * (i / max(1, n - 1)))
                py = top + ch * (1.0 - max(0.0, min(1.0, val / max_temp)))
                if i == 0:
                    path.moveTo(px, py)
                    fill_path.moveTo(px, top + ch)
                    fill_path.lineTo(px, py)
                else:
                    path.lineTo(px, py)
                    fill_path.lineTo(px, py)
                if i == n - 1:
                    fill_path.lineTo(px, top + ch)
                    fill_path.closeSubpath()

            grad = QLinearGradient(0, top, 0, top + ch)
            c_top = QColor(col)
            c_top.setAlpha(52)
            c_bot = QColor(col)
            c_bot.setAlpha(0)
            grad.setColorAt(0.0, c_top)
            grad.setColorAt(1.0, c_bot)
            p.fillPath(fill_path, QBrush(grad))

            p.setPen(QPen(col, 2.1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)

        p.end()


class DonutRingChart(QFrame):
    """Multi-segment colored donut chart with center total and legend."""

    def __init__(self, title: str = "VERTEILUNG", height: int = 165):
        super().__init__()
        self.setObjectName("card")
        self.setMinimumHeight(height)
        self.title = title
        self.segments = []  # list of (label, value, color_hex, unit_str)
        self.center_top = "0"
        self.center_sub = ""

    def set_segments(self, segments, center_top: str = "", center_sub: str = ""):
        self.segments = [s for s in segments if s[1] > 0]
        self.center_top = center_top
        self.center_sub = center_sub
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        p.setPen(QColor("#94A3B8"))
        p.setFont(QFont("Inter", 9, QFont.Bold))
        p.drawText(14, 21, self.title)

        ring_size = min(w * 0.38, h - 42.0, 108.0)
        rx = 18.0
        ry = 30.0 + (h - 36.0 - ring_size) / 2.0
        rect = QRectF(rx, ry, ring_size, ring_size)

        total = sum(s[1] for s in self.segments)
        if total <= 0:
            p.setPen(QPen(QColor("#1B2638"), 10.0, Qt.SolidLine))
            p.drawEllipse(rect)
            p.setPen(QColor("#64748B"))
            p.setFont(QFont("Inter", 9))
            p.drawText(QRectF(rx + ring_size + 16, 30, w - rx - ring_size - 24, h - 36), Qt.AlignVCenter, "Keine Daten vorhanden")
            p.end()
            return

        angle_cursor = 90.0 * 16.0
        for idx, (label, val, col_hex, _) in enumerate(self.segments):
            frac = val / total
            span = -int(round(frac * 360.0 * 16.0))
            pen = QPen(QColor(col_hex), 10.5, Qt.SolidLine, Qt.FlatCap)
            p.setPen(pen)
            p.drawArc(rect, int(angle_cursor), span)
            angle_cursor += span

        p.setPen(QColor("#F8FAFC"))
        p.setFont(QFont("Inter", 11, QFont.Bold))
        p.drawText(QRectF(rx, ry + ring_size * 0.25, ring_size, ring_size * 0.30), Qt.AlignCenter, self.center_top)
        if self.center_sub:
            p.setPen(QColor("#8799B0"))
            p.setFont(QFont("Inter", 7, QFont.Bold))
            p.drawText(QRectF(rx, ry + ring_size * 0.53, ring_size, ring_size * 0.22), Qt.AlignCenter, self.center_sub)

        lx = rx + ring_size + 20.0
        ly = 36.0
        row_h = min(22.0, max(16.0, (h - 42.0) / max(1, len(self.segments))))
        for label, val, col_hex, unit_str in self.segments[:5]:
            p.setBrush(QColor(col_hex))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(lx, ly + 3, 9, 9), 2.5, 2.5)

            p.setPen(QColor("#E2E8F0"))
            p.setFont(QFont("Inter", 9, QFont.DemiBold))
            p.drawText(QRectF(lx + 15, ly - 1, w - lx - 75, row_h), Qt.AlignLeft | Qt.AlignVCenter, label)

            p.setPen(QColor(col_hex))
            p.setFont(QFont("Inter", 9, QFont.Bold))
            p.drawText(QRectF(w - 86, ly - 1, 72, row_h), Qt.AlignRight | Qt.AlignVCenter, unit_str)
            ly += row_h

        p.end()


class FleetBarChart(QFrame):
    """Colored horizontal bar chart for printer utilization and print hours."""

    def __init__(self, title: str = "FLOTTEN-AUSLASTUNG & FORTSCHRITT", height: int = 165):
        super().__init__()
        self.setObjectName("card")
        self.setMinimumHeight(height)
        self.title = title
        self.bars = []  # list of (name, pct_0_to_1, right_text, color_hex)

    def set_bars(self, bars):
        self.bars = bars
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        p.setPen(QColor("#94A3B8"))
        p.setFont(QFont("Inter", 9, QFont.Bold))
        p.drawText(14, 21, self.title)

        if not self.bars:
            p.setPen(QColor("#64748B"))
            p.setFont(QFont("Inter", 9))
            p.drawText(QRectF(14, 30, w - 28, h - 36), Qt.AlignCenter, "Keine aktiven Drucker")
            p.end()
            return

        y = 34.0
        avail_h = h - 42.0
        row_h = min(28.0, max(20.0, avail_h / max(1, len(self.bars[:4]))))
        for idx, (name, frac, right_txt, col_hex) in enumerate(self.bars[:4]):
            frac = max(0.02, min(1.0, float(frac or 0.0)))
            p.setPen(QColor("#E2E8F0"))
            p.setFont(QFont("Inter", 8.5, QFont.DemiBold))
            p.drawText(QRectF(14, y, 110, 14), Qt.AlignLeft | Qt.AlignVCenter, name[:16])

            p.setPen(QColor(col_hex))
            p.setFont(QFont("Inter", 8.5, QFont.Bold))
            p.drawText(QRectF(w - 110, y, 96, 14), Qt.AlignRight | Qt.AlignVCenter, right_txt)

            track_r = QRectF(14, y + 15, w - 28, 6.5)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#151F30"))
            p.drawRoundedRect(track_r, 3.2, 3.2)

            fill_r = QRectF(14, y + 15, (w - 28) * frac, 6.5)
            p.setBrush(QColor(col_hex))
            p.drawRoundedRect(fill_r, 3.2, 3.2)
            y += row_h

        p.end()


class CommandPaletteDialog(QDialog):
    """Quick command palette (Ctrl+K) for printer and navigation actions."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("Befehlspalette")
        self.resize(580, 420)
        self.setModal(True)

        l = QVBoxLayout(self)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(10)

        hdr = QLabel("SCHNELLBEFEHLE & NAVIGATION  (ESC ZUM SCHLIESSEN)")
        hdr.setStyleSheet("font-size: 11px; font-weight: 800; color: #06B6D4; letter-spacing: 0.8px;")
        l.addWidget(hdr)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Tippe einen Befehl, Druckernamen, Vorheizen oder Ansicht ...")
        self.search.textChanged.connect(self.filter_items)
        self.search.returnPressed.connect(self.run_selected)
        l.addWidget(self.search)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _: self.run_selected())
        l.addWidget(self.list, 1)

        self.commands = self._build_commands()
        self.filter_items("")
        self.search.setFocus()

    def _build_commands(self):
        cmds = [
            ("Ansicht: Drucker-Flotte & Live-Dashboard", lambda: self.win.nav.setCurrentRow(0)),
            ("Ansicht: Spoolman Filament-Verwaltung", lambda: self.win.nav.setCurrentRow(1)),
            ("Ansicht: Druck-Warteschlange & Batch-Dispatcher", lambda: self.win.nav.setCurrentRow(2)),
            ("Ansicht: Wartung & Verschleiß-Tracker", lambda: self.win.nav.setCurrentRow(3)),
            ("Ansicht: Statistik & Energiekosten", lambda: self.win.nav.setCurrentRow(4)),
            ("Ansicht: Lokale 3D-Modell-Bibliothek", lambda: self.win.nav.setCurrentRow(5)),
            ("Ansicht: 3D-Modelle im Web suchen", lambda: self.win.nav.setCurrentRow(6)),
            ("Ansicht: Einstellungen", lambda: self.win.nav.setCurrentRow(7)),
            ("Kamera-Workspace: Freie Kamera-Matrix öffnen", self.win.show_all_cams),
            ("Aktion: Neuen Drucker hinzufügen", self.win.add_printer),
            ("Design: Obsidian Studio (Dark) aktivieren", lambda: self.win.apply_theme("obsidian")),
            ("Design: Graphite Pro (Dark) aktivieren", lambda: self.win.apply_theme("graphite")),
            ("Design: Daylight Clean (Light) aktivieren", lambda: self.win.apply_theme("light")),
        ]
        for p in getattr(self.win, "printers", []):
            cmds.append((f"Drucker öffnen: {p.name} ({p.host})", lambda pr=p: self.win.open_detail(pr.id)))
            if getattr(p, "printer_type", "moonraker") != "bambu":
                cmds.append((
                    f"Vorheizen PLA (210°C / 60°C): {p.name}",
                    lambda pr=p: self._preheat(pr, 210, 60),
                ))
                cmds.append((
                    f"Vorheizen PETG (240°C / 75°C): {p.name}",
                    lambda pr=p: self._preheat(pr, 240, 75),
                ))
                cmds.append((
                    f"Vorheizen ASA/ABS (260°C / 100°C): {p.name}",
                    lambda pr=p: self._preheat(pr, 260, 100),
                ))
                cmds.append((
                    f"Heizungen ausschalten (Abkühlen): {p.name}",
                    lambda pr=p: self._preheat(pr, 0, 0),
                ))
        return cmds

    def _preheat(self, p, nozzle, bed):
        from .pages import run_async
        run_async(lambda: (
            api.control(p, "temp", heater="extruder", target=nozzle),
            api.control(p, "temp", heater="heater_bed", target=bed),
        ), lambda _: None)

    def filter_items(self, text: str):
        q = text.strip().lower()
        self.list.clear()
        for label, fn in self.commands:
            if not q or q in label.lower():
                it = QListWidgetItem(label)
                it.setData(Qt.UserRole, fn)
                self.list.addItem(it)
        if self.list.count() > 0:
            self.list.setCurrentRow(0)

    def run_selected(self):
        it = self.list.currentItem()
        if not it:
            return
        fn = it.data(Qt.UserRole)
        self.accept()
        if callable(fn):
            fn()


QUEUE_FILE = store.CFG / "queue.json"


def load_queue() -> list:
    try:
        return json.loads(QUEUE_FILE.read_text())
    except Exception:
        return []


def save_queue(items: list):
    store.CFG.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(items, indent=2))


class PrintQueuePage(QWidget):
    """Production Print Queue & Auto-Dispatcher for multi-printer farms."""

    def __init__(self, win=None):
        super().__init__()
        self.win = win
        self.items = load_queue()

        l = QVBoxLayout(self)
        l.setSpacing(14)

        top = QHBoxLayout()
        title_col = QVBoxLayout()
        h = QLabel("Druck-Warteschlange & Batch-Dispatcher")
        h.setObjectName("h1")
        sub = QLabel("Plane Druckaufträge im Voraus, lege Serien-Kopien fest und verteile Jobs auf freie Drucker.")
        sub.setObjectName("dim")
        title_col.addWidget(h)
        title_col.addWidget(sub)
        top.addLayout(title_col, 1)

        self.auto_dispatch_chk = QCheckBox("Auto-Dispatch bei freiem Drucker")
        top.addWidget(self.auto_dispatch_chk)

        btn_dispatch_now = QPushButton("Nächsten Job auf freiem Drucker starten")
        btn_dispatch_now.setIcon(make_vector_icon("play", "#041016", 14))
        btn_dispatch_now.setObjectName("primary")
        btn_dispatch_now.clicked.connect(self.dispatch_next_available)
        top.addWidget(btn_dispatch_now)
        l.addLayout(top)

        add_card = QFrame()
        add_card.setObjectName("card")
        al = QHBoxLayout(add_card)
        al.setContentsMargins(14, 12, 14, 12)

        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("Lokale .gcode Datei oder Dateiname auf dem Drucker ...")
        btn_browse = QPushButton("Datei wählen ...")
        btn_browse.clicked.connect(self.pick_local_gcode)

        self.printer_combo = QComboBox()
        self.printer_combo.setMinimumWidth(170)

        self.copies_spin = QSpinBox()
        self.copies_spin.setRange(1, 100)
        self.copies_spin.setValue(1)
        self.copies_spin.setPrefix("Kopien: ")

        self.mat_input = QLineEdit()
        self.mat_input.setPlaceholderText("Material (PLA, PETG)")
        self.mat_input.setFixedWidth(140)

        btn_add = QPushButton("Zur Warteschlange")
        btn_add.setIcon(make_vector_icon("plus", "#041016", 14))
        btn_add.setObjectName("primary")
        btn_add.clicked.connect(self.add_job)

        al.addWidget(self.file_input, 1)
        al.addWidget(btn_browse)
        al.addWidget(self.printer_combo)
        al.addWidget(self.copies_spin)
        al.addWidget(self.mat_input)
        al.addWidget(btn_add)
        l.addWidget(add_card)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Pos.", "G-Code Auftrag", "Ziel-Drucker", "Material", "Kopien", "Aktionen"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        l.addWidget(self.table, 1)

    def showEvent(self, e):
        self.refresh_printers()
        self.rebuild_table()

    def refresh_printers(self):
        self.printer_combo.clear()
        self.printer_combo.addItem("Beliebiger freier Drucker", "any")
        for p in getattr(self.win, "printers", []):
            self.printer_combo.addItem(f"{p.name} ({p.host})", p.id)

    def pick_local_gcode(self):
        from .pages import models_dir
        path, _ = QFileDialog.getOpenFileName(self, "G-Code für Warteschlange wählen", models_dir(), "G-Code (*.gcode)")
        if path:
            self.file_input.setText(path)

    def add_job(self):
        fp = self.file_input.text().strip()
        if not fp:
            QMessageBox.warning(self, "Warteschlange", "Bitte wähle zuerst eine G-Code-Datei aus.")
            return
        self.items.append({
            "id": f"q_{int(time.time() * 1000)}",
            "file": fp,
            "name": Path(fp).name,
            "printer_id": self.printer_combo.currentData() or "any",
            "printer_label": self.printer_combo.currentText(),
            "copies": self.copies_spin.value(),
            "material": self.mat_input.text().strip() or "PLA",
            "added_at": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
        })
        save_queue(self.items)
        self.file_input.clear()
        self.rebuild_table()

    def rebuild_table(self):
        self.table.setRowCount(len(self.items))
        for r, it in enumerate(self.items):
            self.table.setItem(r, 0, QTableWidgetItem(f"#{r + 1}"))
            self.table.setItem(r, 1, QTableWidgetItem(it.get("name") or it.get("file", "")))
            self.table.setItem(r, 2, QTableWidgetItem(it.get("printer_label", "Beliebig")))
            self.table.setItem(r, 3, QTableWidgetItem(it.get("material", "—")))
            self.table.setItem(r, 4, QTableWidgetItem(f"{it.get('copies', 1)}x"))

            act_w = QWidget()
            hl = QHBoxLayout(act_w)
            hl.setContentsMargins(4, 2, 4, 2)
            hl.setSpacing(6)
            b_start = QPushButton("Starten")
            b_start.setObjectName("primary")
            b_start.clicked.connect(lambda _, idx=r: self.start_item_at(idx))
            b_del = QPushButton("Entfernen")
            b_del.setObjectName("danger")
            b_del.clicked.connect(lambda _, idx=r: self.remove_item_at(idx))
            hl.addWidget(b_start)
            hl.addWidget(b_del)
            self.table.setCellWidget(r, 5, act_w)

    def remove_item_at(self, idx: int):
        if 0 <= idx < len(self.items):
            self.items.pop(idx)
            save_queue(self.items)
            self.rebuild_table()

    def start_item_at(self, idx: int):
        if not (0 <= idx < len(self.items)):
            return
        job = self.items[idx]
        printers = getattr(self.win, "printers", [])
        if not printers:
            QMessageBox.warning(self, "Warteschlange", "Keine Drucker eingerichtet.")
            return

        target_p = None
        pid = job.get("printer_id", "any")
        if pid != "any":
            target_p = next((p for p in printers if p.id == pid), None)
        if not target_p:
            for p in printers:
                st = getattr(self.win, "last_status_data", {}).get(p.id, {})
                if st.get("state") in ("standby", "complete", "cancelled"):
                    target_p = p
                    break
            if not target_p:
                target_p = printers[0]

        fp = job.get("file", "")
        from .pages import run_async

        def task():
            if Path(fp).is_file():
                return api.upload_gcode(target_p, fp, start_print=True)
            return api.start_print(target_p, fp)

        def on_done(res):
            if res[0] == "ok":
                if job.get("copies", 1) > 1:
                    job["copies"] -= 1
                else:
                    if job in self.items:
                        self.items.remove(job)
                save_queue(self.items)
                self.rebuild_table()
                self.win.poll()
                QMessageBox.information(self, "Druck gestartet", f"Auftrag '{job.get('name')}' wurde an {target_p.name} übergeben.")
            else:
                QMessageBox.warning(self, "Fehler beim Starten", str(res[1]))

        run_async(task, on_done)

    def dispatch_next_available(self):
        if not self.items:
            QMessageBox.information(self, "Warteschlange", "Die Warteschlange ist leer.")
            return
        self.start_item_at(0)


MAINT_FILE = store.CFG / "maintenance.json"

DEFAULT_TASKS = [
    ("nozzle", "Düse & Hotend-Silikonsocke prüfen / wechseln", 250.0),
    ("rails", "Linearschienen / Stangen reinigen & neu fetten", 150.0),
    ("belts", "Riemenspannung (X/Y) & Pulleys kontrollieren", 200.0),
    ("plate", "PEI-Bauplatte mit warmem Spülwasser & IPA entfetten", 50.0),
    ("extruder", "Extruder-Förderräder & PTFE-Schlauch auf Abrieb prüfen", 300.0),
]


def load_maint() -> dict:
    try:
        return json.loads(MAINT_FILE.read_text())
    except Exception:
        return {}


def save_maint(data: dict):
    store.CFG.mkdir(parents=True, exist_ok=True)
    MAINT_FILE.write_text(json.dumps(data, indent=2))


class MaintenancePage(QWidget):
    """Tracks printer operating hours and component maintenance intervals."""

    def __init__(self, win=None):
        super().__init__()
        self.win = win
        self.data = load_maint()
        self.printer_hours = {}

        l = QVBoxLayout(self)
        l.setSpacing(14)

        top = QHBoxLayout()
        tcol = QVBoxLayout()
        h = QLabel("Wartungs- & Verschleiß-Tracker")
        h.setObjectName("h1")
        sub = QLabel("Überwacht automatisch die realen Druckstunden aus Moonraker und erinnert an Komponenten-Wartung.")
        sub.setObjectName("dim")
        tcol.addWidget(h)
        tcol.addWidget(sub)
        top.addLayout(tcol, 1)

        self.p_combo = QComboBox()
        self.p_combo.setMinimumWidth(200)
        self.p_combo.currentIndexChanged.connect(self.reload_printer_stats)
        top.addWidget(QLabel("Drucker:"))
        top.addWidget(self.p_combo)

        btn_sync = QPushButton("Betriebsstunden synchronisieren")
        btn_sync.setIcon(make_vector_icon("refresh", "#041016", 14))
        btn_sync.setObjectName("primary")
        btn_sync.clicked.connect(self.reload_printer_stats)
        top.addWidget(btn_sync)
        l.addLayout(top)

        self.kpi_lbl = QLabel("Gesamte Betriebsstunden: —")
        self.kpi_lbl.setObjectName("h2")
        l.addWidget(self.kpi_lbl)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Wartungsaufgabe", "Intervall", "Seit letzter Wartung", "Status / Verschleiß", "Quittieren"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        l.addWidget(self.table, 1)

    def showEvent(self, e):
        self.p_combo.blockSignals(True)
        self.p_combo.clear()
        for p in getattr(self.win, "printers", []):
            self.p_combo.addItem(f"{p.name} ({p.host})", p.id)
        self.p_combo.blockSignals(False)
        self.reload_printer_stats()

    def reload_printer_stats(self):
        printers = getattr(self.win, "printers", [])
        idx = self.p_combo.currentIndex()
        if not printers or idx < 0 or idx >= len(printers):
            return
        p = printers[idx]
        from .pages import run_async

        def task():
            if getattr(p, "printer_type", "moonraker") == "bambu":
                return 0.0
            jobs = api.history(p, limit=500)
            st = costs.stats(jobs)
            return float(st.get("hours") or 0.0)

        def on_done(res):
            hours = res[1] if res[0] == "ok" else 0.0
            self.printer_hours[p.id] = hours
            self.kpi_lbl.setText(f"Erfasste Gesamtdruckzeit für {p.name}: {hours:.1f} Stunden")
            self.render_tasks(p, hours)

        run_async(task, on_done)

    def render_tasks(self, p, total_hours: float):
        p_rec = self.data.get(p.id, {})
        self.table.setRowCount(len(DEFAULT_TASKS))
        for r, (key, title, interval_h) in enumerate(DEFAULT_TASKS):
            last_reset_h = float(p_rec.get(key, {}).get("reset_at_hours", 0.0))
            last_date = p_rec.get(key, {}).get("last_date", "Noch nie")
            used_h = max(0.0, total_hours - last_reset_h)
            pct = min(1.0, used_h / interval_h) if interval_h > 0 else 0.0

            self.table.setItem(r, 0, QTableWidgetItem(title))
            self.table.setItem(r, 1, QTableWidgetItem(f"alle {interval_h:.0f} h"))
            self.table.setItem(r, 2, QTableWidgetItem(f"{used_h:.1f} h (Reset: {last_date})"))

            status_txt = "OK" if pct < 0.8 else ("BALD FÄLLIG" if pct < 1.0 else "WARTUNG FÄLLIG")
            status_it = QTableWidgetItem(f"{status_txt} ({pct * 100:.0f}%)")
            status_it.setForeground(QColor("#10B981" if pct < 0.8 else ("#F59E0B" if pct < 1.0 else "#F43F5E")))
            self.table.setItem(r, 3, status_it)

            btn = QPushButton("Wartung erledigt")
            btn.clicked.connect(lambda _, k=key, pr=p, h=total_hours: self.ack_task(pr, k, h))
            self.table.setCellWidget(r, 4, btn)

    def ack_task(self, p, key: str, current_hours: float):
        if p.id not in self.data:
            self.data[p.id] = {}
        self.data[p.id][key] = {
            "reset_at_hours": current_hours,
            "last_date": datetime.datetime.now().strftime("%d.%m.%Y"),
        }
        save_maint(self.data)
        self.render_tasks(p, current_hours)
