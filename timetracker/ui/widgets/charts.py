from __future__ import annotations

import math
from typing import List, Optional, TypedDict

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class PieEntry(TypedDict):
    key: str
    label: str
    value: int
    color: QColor


class PieChartWidget(QWidget):
    slice_clicked = Signal(str)
    GAP_DEG = 1.2

    def __init__(self) -> None:
        super().__init__()
        self._entries: List[PieEntry] = []
        self._selected_key: Optional[str] = None
        self._slices: List[dict] = []
        self._chart_center = QPointF(0, 0)
        self._outer_r = 0.0
        self._inner_r = 0.0
        self._colors = [
            QColor("#00E5FF"),
            QColor("#7C4DFF"),
            QColor("#00E676"),
            QColor("#FFEA00"),
            QColor("#FF6D00"),
            QColor("#FF1744"),
        ]
        self.setMinimumHeight(220)

    def set_data(self, entries: List[PieEntry], selected_key: Optional[str]) -> None:
        self._entries = entries
        self._selected_key = selected_key
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(16, 16, -16, -16)
        header_height = 24.0
        header_rect = QRectF(rect.left(), rect.top(), rect.width(), header_height)
        chart_rect = QRectF(
            rect.left(),
            rect.top() + header_height + 6,
            rect.width() * 0.55,
            rect.height() - header_height - 6,
        )
        size = min(chart_rect.width(), chart_rect.height())
        center = chart_rect.center()
        outer_r = size * 0.42
        inner_r = outer_r * 0.58
        self._chart_center = center
        self._outer_r = outer_r
        self._inner_r = inner_r
        total = sum(entry["value"] for entry in self._entries)
        if total <= 0:
            self._draw_empty(painter, rect)
            return
        start_angle = 0.0
        self._slices = []
        for idx, entry in enumerate(self._entries):
            value = entry["value"]
            if value <= 0:
                continue
            span = 360.0 * value / total
            if span <= self.GAP_DEG:
                continue
            color = entry["color"]
            selected = entry["key"] == self._selected_key
            outer = outer_r * (1.08 if selected else 1.0)
            inner = inner_r * (0.92 if selected else 1.0)
            offset = outer_r * 0.08 if selected else 0.0
            mid_rad = math.radians(start_angle + span / 2)
            dx = math.cos(mid_rad) * offset
            dy = math.sin(mid_rad) * offset
            cx = center.x() + dx
            cy = center.y() + dy
            path = self._make_slice_path(
                cx,
                cy,
                inner,
                outer,
                start_angle + self.GAP_DEG / 2,
                span - self.GAP_DEG,
            )
            slice_color = color.lighter(130) if selected else color
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(slice_color)
            painter.drawPath(path)
            if selected:
                painter.setPen(QPen(QColor(255, 255, 255, 180), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(path)
            self._slices.append(
                {
                    "start": start_angle,
                    "span": span,
                    "key": entry["key"],
                    "center": QPointF(cx, cy),
                    "inner": inner,
                    "outer": outer,
                }
            )
            start_angle += span
        self._draw_header_text(painter, header_rect, total)
        self._draw_center_text(painter, chart_rect, total)
        self._draw_legend(painter, rect, total)

    def _draw_empty(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(QPen(QColor("#2F3A4F"), 2))
        painter.setBrush(QColor(0, 0, 0, 0))
        size = min(rect.width(), rect.height())
        center = rect.center()
        circle = QRectF(center.x() - size * 0.35, center.y() - size * 0.35, size * 0.7, size * 0.7)
        painter.drawEllipse(circle)
        painter.setPen(QColor("#6B7A90"))
        painter.setFont(QFont("Microsoft YaHei", 9))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "暂无数据")

    def _draw_legend(self, painter: QPainter, rect: QRectF, total: int) -> None:
        start_x = rect.left() + rect.width() * 0.6
        y = rect.top() + 10
        painter.setFont(QFont("Microsoft YaHei", 9))
        for idx, entry in enumerate(self._entries):
            label = entry["label"]
            value = entry["value"]
            color = entry["color"]
            painter.setPen(QPen(color, 8))
            painter.drawPoint(QPointF(start_x, y + 6))
            painter.setPen(QColor("#D6E2F1"))
            percent = f"{value * 100 / total:.1f}%" if total else "0%"
            duration = format_duration(value)
            painter.drawText(QPointF(start_x + 12, y + 10), f"{label}  {percent}  {duration}")
            y += 20

    def _draw_center_text(self, painter: QPainter, rect: QRectF, total: int) -> None:
        selected = next((item for item in self._entries if item["key"] == self._selected_key), None)
        if selected is None:
            painter.setPen(QColor("#D6E2F1"))
            painter.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.DemiBold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "点击扇区")
            return
        percent = selected["value"] * 100 / total if total else 0.0
        painter.setPen(QColor(selected["color"]).lighter(140))
        painter.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        painter.drawText(rect.adjusted(0, 0, 0, 0), Qt.AlignmentFlag.AlignCenter, f"{percent:.1f}%")

    def _draw_header_text(self, painter: QPainter, rect: QRectF, total: int) -> None:
        selected = next((item for item in self._entries if item["key"] == self._selected_key), None)
        if selected is None:
            return
        text = f"{selected['label']}  {format_duration(selected['value'])}"
        painter.setPen(QColor(selected["color"]).lighter(140))
        painter.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.DemiBold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _make_slice_path(
        self,
        cx: float,
        cy: float,
        inner_r: float,
        outer_r: float,
        start_deg: float,
        span_deg: float,
    ) -> QPainterPath:
        outer_rect = QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)
        inner_rect = QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)
        path = QPainterPath()
        qt_start = -start_deg
        qt_span = -span_deg
        path.arcMoveTo(outer_rect, qt_start)
        path.arcTo(outer_rect, qt_start, qt_span)
        path.arcTo(inner_rect, qt_start + qt_span, -qt_span)
        path.closeSubpath()
        return path

    def mousePressEvent(self, event) -> None:
        for slice_item in self._slices:
            center = slice_item["center"]
            dx = event.position().x() - center.x()
            dy = event.position().y() - center.y()
            distance = math.hypot(dx, dy)
            if distance < slice_item["inner"] or distance > slice_item["outer"]:
                continue
            angle = math.degrees(math.atan2(dy, dx)) % 360.0
            start = (slice_item["start"] + self.GAP_DEG / 2) % 360.0
            end = (slice_item["start"] + slice_item["span"] - self.GAP_DEG / 2) % 360.0
            if self._angle_in_range(angle, start, end):
                self.slice_clicked.emit(slice_item["key"])
                break

    @staticmethod
    def _angle_in_range(angle: float, start: float, end: float) -> bool:
        if start <= end:
            return start <= angle <= end
        return angle >= start or angle <= end


class TrendChartWidget(QWidget):
    DOT_R = 4
    DOT_R_HOVER = 7
    SNAP_DIST = 36

    def __init__(self) -> None:
        super().__init__()
        self._labels: List[str] = []
        self._series: List[dict] = []
        self._hover_index: Optional[int] = None
        self._hover_x = 0.0
        self._scale = 1.0
        self._offset_x = 0.0
        self._drag_start_x: float | None = None
        self._drag_start_off = 0.0
        self._colors = [
            QColor("#00E5FF"),
            QColor("#FF6D00"),
            QColor("#7C4DFF"),
            QColor("#00E676"),
        ]
        self.setMinimumHeight(240)
        self.setMouseTracking(True)

    def set_data(self, labels: List[str], series: List[dict]) -> None:
        self._labels = labels
        self._series = series
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(72, 32, -22, -32)
        painter.save()
        painter.setClipRect(rect)
        self._draw_grid(painter, rect)
        if not self._labels or not self._series:
            painter.restore()
            self._draw_empty(painter, rect)
            return
        max_value = max((max(item["values"]) if item["values"] else 0) for item in self._series)
        if max_value <= 0:
            painter.restore()
            self._draw_empty(painter, rect)
            return
        for idx, item in reversed(list(enumerate(self._series))):
            color = item.get("color", self._colors[idx % len(self._colors)])
            values = item["values"]
            points = [self._map_point(i, value, rect, max_value) for i, value in enumerate(values)]
            line_path = self._build_line_path(points)
            self._draw_area(painter, points, line_path, color, rect)
            self._draw_line(painter, line_path, color)
        for idx, item in enumerate(self._series):
            color = item.get("color", self._colors[idx % len(self._colors)])
            values = item["values"]
            points = [self._map_point(i, value, rect, max_value) for i, value in enumerate(values)]
            self._draw_points(painter, points, color)
        if self._hover_index is not None:
            self._draw_crosshair(painter, rect)
            self._draw_tooltip(painter, rect, max_value)
        painter.restore()
        self._draw_y_labels(painter, rect, max_value)
        self._draw_legend(painter, rect)
        self._draw_x_labels(painter, rect)

    def _draw_grid(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(QPen(QColor("#1C2A3B"), 1))
        for i in range(6):
            y = rect.top() + i * rect.height() / 5
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))

    def _build_line_path(self, points: list[QPointF]) -> QPainterPath:
        if len(points) < 2:
            return QPainterPath()
        path = QPainterPath()
        path.moveTo(points[0])
        for i in range(1, len(points)):
            prev = points[i - 1]
            cur = points[i]
            cpx = (prev.x() + cur.x()) / 2
            path.cubicTo(QPointF(cpx, prev.y()), QPointF(cpx, cur.y()), cur)
        return path

    def _draw_line(self, painter: QPainter, line_path: QPainterPath, color: QColor) -> None:
        if line_path.isEmpty():
            return
        pen = QPen(color, 2.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(line_path)

    def _draw_area(
        self,
        painter: QPainter,
        points: list[QPointF],
        line_path: QPainterPath,
        color: QColor,
        rect: QRectF,
    ) -> None:
        if len(points) < 2 or line_path.isEmpty():
            return
        area_path = QPainterPath(line_path)
        area_path.lineTo(QPointF(points[-1].x(), rect.bottom()))
        area_path.lineTo(QPointF(points[0].x(), rect.bottom()))
        area_path.closeSubpath()
        grad = QLinearGradient(0, rect.top(), 0, rect.bottom())
        c1 = QColor(color)
        c1.setAlpha(90)
        c2 = QColor(color)
        c2.setAlpha(8)
        grad.setColorAt(0.0, c1)
        grad.setColorAt(1.0, c2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawPath(area_path)

    def _draw_points(self, painter: QPainter, points: list[QPointF], color: QColor) -> None:
        for i, pt in enumerate(points):
            hover = self._hover_index == i
            r = self.DOT_R_HOVER if hover else self.DOT_R
            painter.setPen(QPen(color.lighter(160), 2))
            painter.setBrush(QColor("#0C1626"))
            painter.drawEllipse(pt, r, r)
            if hover:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color)
                painter.drawEllipse(pt, r - 2, r - 2)

    def _draw_empty(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(QColor("#6B7A90"))
        painter.setFont(QFont("Microsoft YaHei", 9))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "暂无数据")

    def _draw_legend(self, painter: QPainter, rect: QRectF) -> None:
        x = rect.left()
        y = rect.top() - 18
        painter.setFont(QFont("Microsoft YaHei", 8))
        for idx, item in enumerate(self._series):
            color = item.get("color", self._colors[idx % len(self._colors)])
            painter.setPen(QPen(color, 8))
            painter.drawPoint(QPointF(x, y))
            painter.setPen(QColor("#CFE4FF"))
            painter.drawText(QPointF(x + 10, y + 4), item["name"])
            x += 80

    def _draw_x_labels(self, painter: QPainter, rect: QRectF) -> None:
        if not self._labels:
            return
        painter.setFont(QFont("Microsoft YaHei", 8))
        painter.setPen(QColor("#8EA6C2"))
        steps = min(5, len(self._labels) - 1) if len(self._labels) > 1 else 1
        for i in range(steps + 1):
            idx = int(i * (len(self._labels) - 1) / steps) if steps else 0
            x = self._map_x(idx, rect)
            if rect.left() <= x <= rect.right():
                painter.drawText(QPointF(x - 12, rect.bottom() + 14), self._labels[idx])

    def _draw_y_labels(self, painter: QPainter, rect: QRectF, max_value: int) -> None:
        painter.setFont(QFont("Microsoft YaHei", 8))
        painter.setPen(QColor("#8EA6C2"))
        steps = 5
        for i in range(steps + 1):
            value = int(max_value * (steps - i) / steps)
            y = rect.top() + rect.height() * i / steps
            painter.drawText(
                QRectF(4, y - 8, rect.left() - 8, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                format_duration(value),
            )

    def _draw_crosshair(self, painter: QPainter, rect: QRectF) -> None:
        if self._hover_index is None:
            return
        x = self._map_x(self._hover_index, rect)
        pen = QPen(QColor(255, 255, 255, 60), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))

    def _draw_tooltip(self, painter: QPainter, rect: QRectF, max_value: int) -> None:
        index = self._hover_index
        if index is None:
            return
        label = self._labels[index]
        items = []
        total = 0
        for item in self._series:
            value = item["values"][index] if index < len(item["values"]) else 0
            total += value
            items.append((item["name"], value, item.get("color", QColor("#CFE4FF"))))
        total_text = f"总计: {self._format_hours(total)}"
        title_font = QFont("Microsoft YaHei", 9, QFont.Weight.DemiBold)
        body_font = QFont("Microsoft YaHei", 9)
        title_metrics = QFontMetrics(title_font)
        body_metrics = QFontMetrics(body_font)
        line_h = 20
        width = max(title_metrics.horizontalAdvance(label), body_metrics.horizontalAdvance(total_text)) + 56
        for name, value, _ in items:
            line = f"{name}: {self._format_hours(value)}"
            width = max(width, body_metrics.horizontalAdvance(line) + 56)
        height = 16 + line_h * (len(items) + 2)
        x = self._map_x(index, rect)
        tx = x + 14
        ty = rect.top() + 6
        if tx + width > self.width() - 10:
            tx = x - width - 14
        card = QRectF(tx, ty, width, height)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(18, 26, 40, 230))
        path = QPainterPath()
        path.addRoundedRect(card, 8, 8)
        painter.drawPath(path)
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        painter.setFont(title_font)
        painter.setPen(QColor("#EAF3FF"))
        painter.drawText(QRectF(tx + 12, ty + 6, width - 24, line_h), Qt.AlignmentFlag.AlignLeft, label)
        painter.setFont(body_font)
        y = ty + 6 + line_h
        for name, value, color in items:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(QPointF(tx + 16, y + line_h / 2), 4, 4)
            painter.setPen(QColor("#CFE4FF"))
            text = f"{name}: {self._format_hours(value)}"
            painter.drawText(QRectF(tx + 26, y, width - 38, line_h), Qt.AlignmentFlag.AlignLeft, text)
            y += line_h
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(QRectF(tx + 26, y, width - 38, line_h), Qt.AlignmentFlag.AlignLeft, total_text)

    def mouseMoveEvent(self, event) -> None:
        rect = QRectF(self.rect()).adjusted(56, 32, -22, -32)
        if not rect.contains(event.position()):
            return
        if not self._labels or not self._series:
            return
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_start_x is not None:
            self._offset_x = self._drag_start_off + (event.position().x() - self._drag_start_x)
            self._clamp_offset(rect)
            self.update()
            return
        best_i = None
        best_d = 1e9
        for i in range(len(self._labels)):
            x = self._map_x(i, rect)
            d = abs(event.position().x() - x)
            if d < best_d:
                best_d = d
                best_i = i
                self._hover_x = x
        new_index = best_i if best_d <= self.SNAP_DIST else None
        if new_index != self._hover_index:
            self._hover_index = new_index
            self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        rect = QRectF(self.rect()).adjusted(56, 32, -22, -32)
        if not rect.contains(event.position()):
            return
        self._drag_start_x = event.position().x()
        self._drag_start_off = self._offset_x
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_x = None
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def wheelEvent(self, event) -> None:
        rect = QRectF(self.rect()).adjusted(56, 32, -22, -32)
        if not rect.contains(event.position()):
            return
        delta = event.angleDelta().y()
        if delta == 0:
            return
        scale = self._scale
        new_scale = max(1.0, min(6.0, scale + (0.1 if delta > 0 else -0.1)))
        if new_scale == scale:
            return
        mouse_x = event.position().x()
        ratio = (mouse_x - rect.left() - self._offset_x) / max(1.0, rect.width() * scale)
        self._scale = new_scale
        self._offset_x = mouse_x - rect.left() - ratio * rect.width() * new_scale
        self._clamp_offset(rect)
        self.update()

    def leaveEvent(self, event) -> None:
        if self._hover_index is not None:
            self._hover_index = None
            self.update()

    def _map_point(self, index: int, value: int, rect: QRectF, max_value: int) -> QPointF:
        x = self._map_x(index, rect)
        y = rect.bottom() - (value / max_value) * rect.height()
        return QPointF(x, y)

    def _map_x(self, index: int, rect: QRectF) -> float:
        if len(self._labels) <= 1:
            return rect.left()
        return rect.left() + index / (len(self._labels) - 1) * rect.width() * self._scale + self._offset_x

    def _clamp_offset(self, rect: QRectF) -> None:
        if self._scale <= 1.0:
            self._offset_x = 0.0
            return
        min_offset = rect.width() - rect.width() * self._scale
        self._offset_x = min(0.0, max(min_offset, self._offset_x))

    def _format_hours(self, total_seconds: int) -> str:
        return f"{total_seconds / 3600:.1f}h"


def format_duration(total_seconds: int) -> str:
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours >= 1:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"
