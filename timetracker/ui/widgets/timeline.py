from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


@dataclass(frozen=True)
class TimelineSegment:
    start_sec: int
    end_sec: int
    key: str
    label: str
    color: QColor


class TimelineWidget(QWidget):
    selected_changed = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._segments: list[TimelineSegment] = []
        self._selected_key: str | None = None
        self.setMinimumHeight(96)
        self.setMouseTracking(True)

    def set_data(self, segments: list[TimelineSegment]) -> None:
        self._segments = segments
        if self._selected_key is not None and not any(seg.key == self._selected_key for seg in segments):
            self._selected_key = None
        self.update()

    def set_selected_key(self, key: str | None) -> None:
        self._selected_key = key
        self.update()

    def get_selected_key(self) -> str | None:
        return self._selected_key

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(16, 10, -16, -16)
        label_area = QRectF(rect.left(), rect.top(), rect.width(), 18)
        bar_rect = QRectF(rect.left(), rect.top() + 24, rect.width(), 26)

        painter.setFont(QFont("Microsoft YaHei", 9))
        painter.setPen(QColor("#56607A"))
        for hour in range(0, 25, 3):
            x = bar_rect.left() + hour / 24 * bar_rect.width()
            painter.drawText(QRectF(x - 18, label_area.top(), 36, label_area.height()), Qt.AlignmentFlag.AlignCenter, f"{hour:02d}:00")

        painter.setPen(QPen(QColor(12, 20, 36, 180), 1))
        painter.setBrush(QColor(12, 20, 36, 160))
        painter.drawRoundedRect(bar_rect, 8, 8)

        selected_key = self._selected_key
        for idx, seg in enumerate(self._segments):
            start_x = bar_rect.left() + seg.start_sec / 86400 * bar_rect.width()
            end_x = bar_rect.left() + seg.end_sec / 86400 * bar_rect.width()
            width = max(2.0, end_x - start_x)
            rect_seg = QRectF(start_x, bar_rect.top(), width, bar_rect.height())
            color = QColor(seg.color)
            if selected_key is not None and seg.key != selected_key:
                color.setAlpha(90)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(rect_seg, 6, 6)
            if selected_key is not None and seg.key == selected_key:
                painter.setPen(QPen(QColor("#EAF3FF"), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(rect_seg.adjusted(1, 1, -1, -1), 6, 6)
            if width >= 48:
                painter.setPen(QColor("#F5FAFF"))
                painter.setFont(QFont("Microsoft YaHei", 8))
                painter.drawText(rect_seg, Qt.AlignmentFlag.AlignCenter, seg.label)

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        rect = QRectF(self.rect()).adjusted(16, 10, -16, -16)
        bar_rect = QRectF(rect.left(), rect.top() + 24, rect.width(), 26)
        if not bar_rect.contains(event.position()):
            self._selected_key = None
            self.selected_changed.emit(None)
            self.update()
            return
        x = event.position().x()
        hit_index = None
        for idx, seg in enumerate(self._segments):
            start_x = bar_rect.left() + seg.start_sec / 86400 * bar_rect.width()
            end_x = bar_rect.left() + seg.end_sec / 86400 * bar_rect.width()
            if start_x <= x <= end_x:
                hit_index = idx
                break
        self._selected_key = self._segments[hit_index].key if hit_index is not None else None
        self.selected_changed.emit(self._selected_key)
        self.update()
