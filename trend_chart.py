"""
PySide6 趋势图
- 区域填充 Area Fill（贝塞尔曲线，与折线共用同一路径）
- 鼠标悬浮 Tooltip（吸附最近数据点）
- 滚轮缩放（以鼠标位置为锚点）
- 鼠标拖拽平移
"""

import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QRect, QPointF, QRectF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont,
    QPainterPath, QLinearGradient, QCursor
)

# ── 数据 ────────────────────────────────────────────────────────────────────
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

SERIES = [
    {
        "label": "产品 A",
        "values": [120, 145, 132, 168, 190, 175, 210, 228, 215, 245, 268, 290],
        "color": QColor("#4F8EF7"),
    },
    {
        "label": "产品 B",
        "values": [80, 95, 110, 98, 125, 140, 132, 155, 148, 170, 185, 200],
        "color": QColor("#F7874F"),
    },
    {
        "label": "产品 C",
        "values": [50, 60, 55, 72, 68, 85, 90, 78, 95, 105, 98, 120],
        "color": QColor("#4FD4A8"),
    },
]

PAD = {"left": 60, "right": 30, "top": 40, "bottom": 50}


class TrendChart(QWidget):
    DOT_R        = 5
    DOT_R_HOVER  = 8
    SNAP_DIST    = 40
    SCALE_MIN    = 1.0
    SCALE_MAX    = 6.0

    def __init__(self, series, labels, parent=None):
        super().__init__(parent)
        self.series = series
        self.labels = labels

        # ── 缩放 / 平移状态 ──────────────────────────────────────────────
        self.scale    = 1.0   # X 轴缩放倍数
        self.offset_x = 0.0   # X 轴像素偏移

        self._drag_start_x   = None
        self._drag_start_off = None

        self.hovered_x_idx = None
        self.setMinimumSize(700, 420)
        self.setMouseTracking(True)

    # ── 图表区域 ──────────────────────────────────────────────────────────
    def _chart_rect(self):
        return QRect(
            PAD["left"], PAD["top"],
            self.width()  - PAD["left"] - PAD["right"],
            self.height() - PAD["top"]  - PAD["bottom"],
        )

    def _value_range(self):
        all_vals = [v for s in self.series for v in s["values"]]
        lo, hi = min(all_vals), max(all_vals)
        margin = (hi - lo) * 0.15
        return lo - margin, hi + margin

    # ── 坐标映射 ─────────────────────────────────────────────────────────
    def _map_x(self, xi, cr):
        n = len(self.labels)
        return cr.left() + xi / (n - 1) * cr.width() * self.scale + self.offset_x

    def _map_point(self, xi, value, cr, lo, hi):
        x = self._map_x(xi, cr)
        y = cr.bottom() - (value - lo) / (hi - lo) * cr.height()
        return QPointF(x, y)

    def _clamp_offset(self, cr):
        total_w = cr.width() * self.scale
        self.offset_x = max(cr.width() - total_w, min(0.0, self.offset_x))

    # ── 绘制 ─────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#1A1D2E"))

        cr      = self._chart_rect()
        lo, hi  = self._value_range()
        n       = len(self.labels)

        # 裁剪，防止内容溢出坐标轴
        painter.setClipRect(cr)

        self._draw_grid(painter, cr, lo, hi)

        for s in reversed(self.series):
            pts       = [self._map_point(i, s["values"][i], cr, lo, hi) for i in range(n)]
            line_path = self._build_line_path(pts)
            self._draw_area(painter, pts, line_path, s["color"], cr)
            self._draw_line(painter, line_path, s["color"])

        for s in self.series:
            pts = [self._map_point(i, s["values"][i], cr, lo, hi) for i in range(n)]
            for i, pt in enumerate(pts):
                hover = (i == self.hovered_x_idx)
                r = self.DOT_R_HOVER if hover else self.DOT_R
                painter.setPen(QPen(s["color"].lighter(160), 2))
                painter.setBrush(QBrush(QColor("#1A1D2E")))
                painter.drawEllipse(pt, r, r)
                if hover:
                    painter.setBrush(QBrush(s["color"]))
                    painter.setPen(Qt.NoPen)
                    painter.drawEllipse(pt, r - 3, r - 3)

        if self.hovered_x_idx is not None:
            pt0 = self._map_point(self.hovered_x_idx, lo, cr, lo, hi)
            pt1 = self._map_point(self.hovered_x_idx, hi, cr, lo, hi)
            painter.setPen(QPen(QColor(255, 255, 255, 50), 1, Qt.DashLine))
            painter.drawLine(pt0, pt1)

        painter.setClipping(False)

        self._draw_x_labels(painter, cr, n)
        self._draw_y_labels(painter, cr, lo, hi)
        self._draw_legend(painter)
        self._draw_scale_hint(painter)

        if self.hovered_x_idx is not None:
            self._draw_tooltip(painter, cr, lo, hi)

    def _draw_grid(self, painter, cr, lo, hi):
        for i in range(6):
            y = cr.bottom() - i / 5 * cr.height()
            painter.setPen(QPen(QColor(255, 255, 255, 18), 1))
            painter.drawLine(QPointF(cr.left(), y), QPointF(cr.right(), y))

    def _build_line_path(self, pts):
        path = QPainterPath()
        path.moveTo(pts[0])
        for i in range(1, len(pts)):
            prev, cur = pts[i - 1], pts[i]
            cpx = (prev.x() + cur.x()) / 2
            path.cubicTo(QPointF(cpx, prev.y()), QPointF(cpx, cur.y()), cur)
        return path

    def _draw_area(self, painter, pts, line_path, color, cr):
        area = QPainterPath(line_path)
        area.lineTo(QPointF(pts[-1].x(), cr.bottom()))
        area.lineTo(QPointF(pts[0].x(),  cr.bottom()))
        area.closeSubpath()

        grad = QLinearGradient(0, cr.top(), 0, cr.bottom())
        c1 = QColor(color)
        c1.setAlpha(85)
        c2 = QColor(color)
        c2.setAlpha(5)
        grad.setColorAt(0.0, c1)
        grad.setColorAt(1.0, c2)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawPath(area)

    def _draw_line(self, painter, line_path, color):
        painter.setPen(QPen(color, 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(line_path)

    def _draw_x_labels(self, painter, cr, n):
        painter.setPen(QColor("#8888AA"))
        painter.setFont(QFont("Arial", 9))
        for i, lbl in enumerate(self.labels):
            x = self._map_x(i, cr)
            if cr.left() <= x <= cr.right():
                painter.drawText(
                    QRectF(x - 20, cr.bottom() + 8, 40, 20),
                    Qt.AlignCenter, lbl
                )

    def _draw_y_labels(self, painter, cr, lo, hi):
        painter.setPen(QColor("#8888AA"))
        painter.setFont(QFont("Arial", 9))
        for i in range(6):
            val = lo + i / 5 * (hi - lo)
            y   = cr.bottom() - i / 5 * cr.height()
            painter.drawText(
                QRectF(4, y - 10, PAD["left"] - 10, 20),
                Qt.AlignRight | Qt.AlignVCenter, f"{val:.0f}"
            )

    def _draw_legend(self, painter):
        x0, y0 = PAD["left"], 10
        painter.setFont(QFont("Arial", 10))
        for i, s in enumerate(self.series):
            x = x0 + i * 110
            painter.setBrush(QBrush(s["color"]))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x, y0 + 3, 14, 6, 3, 3)
            painter.setPen(QColor("#CCCCDD"))
            painter.drawText(x + 20, y0 + 13, s["label"])

    def _draw_scale_hint(self, painter):
        painter.setPen(QColor("#555577"))
        painter.setFont(QFont("Arial", 9))
        painter.drawText(
            QRectF(self.width() - 90, self.height() - 22, 80, 18),
            Qt.AlignRight | Qt.AlignVCenter,
            f"缩放 {self.scale:.1f}×"
        )

    def _draw_tooltip(self, painter, cr, lo, hi):
        xi    = self.hovered_x_idx
        label = self.labels[xi]
        lines = [(s["label"], s["values"][xi], s["color"]) for s in self.series]

        line_h       = 22
        pad_x, pad_y = 14, 12
        width        = 150
        height       = pad_y * 2 + 20 + line_h * len(lines)

        pt_ref = self._map_point(xi, hi, cr, lo, hi)
        tx = pt_ref.x() + 14
        ty = cr.top() + 10
        if tx + width > self.width() - 10:
            tx = pt_ref.x() - width - 14

        rect = QRectF(tx, ty, width, height)
        bg   = QPainterPath()
        bg.addRoundedRect(rect, 8, 8)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#252840")))
        painter.drawPath(bg)
        painter.setPen(QPen(QColor(255, 255, 255, 35), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(bg)

        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(
            QRectF(tx + pad_x, ty + pad_y, width - pad_x * 2, 20),
            Qt.AlignLeft | Qt.AlignVCenter, label
        )
        for i, (lbl, val, color) in enumerate(lines):
            ry = ty + pad_y + 20 + i * line_h
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(tx + pad_x + 4, ry + line_h / 2), 4, 4)
            painter.setPen(QColor("#AAAACC"))
            painter.setFont(QFont("Arial", 9))
            painter.drawText(QRectF(tx + pad_x + 14, ry, 70, line_h),
                             Qt.AlignLeft | Qt.AlignVCenter, lbl)
            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(QFont("Arial", 9, QFont.Bold))
            painter.drawText(QRectF(tx + pad_x, ry, width - pad_x * 2, line_h),
                             Qt.AlignRight | Qt.AlignVCenter, f"{val}")

    # ── 交互事件 ─────────────────────────────────────────────────────────

    def wheelEvent(self, event):
        cr = self._chart_rect()
        if not cr.contains(event.position().toPoint()):
            return

        mouse_x = event.position().x()
        # 鼠标在当前内容中的比例锚点
        ratio = (mouse_x - cr.left() - self.offset_x) / (cr.width() * self.scale)

        factor    = 1.12 if event.angleDelta().y() > 0 else 1 / 1.12
        new_scale = max(self.SCALE_MIN, min(self.SCALE_MAX, self.scale * factor))
        if new_scale == self.scale:
            return

        # 保持鼠标锚点位置不变：
        # mouse_x = cr.left() + ratio * cr.width() * new_scale + new_offset
        self.offset_x = mouse_x - cr.left() - ratio * cr.width() * new_scale
        self.scale    = new_scale
        self._clamp_offset(cr)

        if self.scale <= self.SCALE_MIN + 0.001:
            self.scale    = self.SCALE_MIN
            self.offset_x = 0.0

        self.hovered_x_idx = None
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.scale > self.SCALE_MIN:
            self._drag_start_x   = event.position().x()
            self._drag_start_off = self.offset_x
            self.setCursor(QCursor(Qt.ClosedHandCursor))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_x = None
            self.setCursor(QCursor(
                Qt.OpenHandCursor if self.scale > self.SCALE_MIN else Qt.ArrowCursor
            ))

    def mouseMoveEvent(self, event):
        mx = event.position().x()

        if self._drag_start_x is not None:
            cr = self._chart_rect()
            self.offset_x = self._drag_start_off + (mx - self._drag_start_x)
            self._clamp_offset(cr)
            self.hovered_x_idx = None
            self.update()
            return

        cr = self._chart_rect()
        n  = len(self.labels)
        best_i, best_d = None, float("inf")
        for i in range(n):
            d = abs(mx - self._map_x(i, cr))
            if d < best_d:
                best_d, best_i = d, i

        new_idx = best_i if best_d < self.SNAP_DIST else None
        if new_idx != self.hovered_x_idx:
            self.hovered_x_idx = new_idx
            self.update()

        self.setCursor(QCursor(
            Qt.OpenHandCursor if self.scale > self.SCALE_MIN else Qt.ArrowCursor
        ))

    def leaveEvent(self, event):
        self.hovered_x_idx = None
        self._drag_start_x = None
        self.setCursor(QCursor(Qt.ArrowCursor))
        self.update()


# ── 主窗口 ──────────────────────────────────────────────────────────────────
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("趋势图 · 缩放 + 平移 + Tooltip · PySide6")
        self.setStyleSheet("background:#1A1D2E;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel(
            "年度销售趋势 "
            "<span style='color:#555577;font-size:11px;font-weight:normal'>"
            "· 滚轮缩放 · 拖拽平移</span>"
        )
        title.setTextFormat(Qt.RichText)
        title.setAlignment(Qt.AlignLeft)
        title.setStyleSheet(
            "color:#FFFFFF; font-size:16px; font-weight:bold;"
            "padding:0 0 8px 4px; background:transparent;"
        )
        layout.addWidget(title)
        layout.addWidget(TrendChart(SERIES, MONTHS))
        self.resize(760, 480)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
