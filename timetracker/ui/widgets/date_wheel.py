from __future__ import annotations

from PySide6.QtCore import QAbstractAnimation, QDate, Property, QEasingCurve, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget


class ScrollWheelWidget(QWidget):
    valueChanged = Signal(str)

    def __init__(self, items: list[str]) -> None:
        super().__init__()
        self.items = [str(item) for item in items]
        self._offset = 0.0
        self._suppress_emit = False
        self.item_height = 40
        self.setFixedSize(70, 160)

        self.stop_timer = QTimer(self)
        self.stop_timer.setSingleShot(True)
        self.stop_timer.setInterval(150)
        self.stop_timer.timeout.connect(self._snap_to_nearest)

        self.animation = QPropertyAnimation(self, b"offset", self)
        self.animation.setDuration(220)
        self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.animation.finished.connect(self._emit_current)

    def set_items(self, items: list[str]) -> None:
        self.items = [str(item) for item in items]
        self._offset = max(0.0, min(self._offset, max(0, len(self.items) - 1)))
        self.update()

    def set_index(self, index: int, emit: bool = True) -> None:
        self._offset = float(max(0, min(index, len(self.items) - 1)))
        self.update()
        if emit:
            self._emit_current()

    def get_offset(self) -> float:
        return self._offset

    def set_offset(self, value: float) -> None:
        self._offset = value
        self.update()

    offset = Property(float, get_offset, set_offset)

    @property
    def current_index(self) -> int:
        return int(round(self._offset))

    @property
    def current_value(self) -> str:
        idx = max(0, min(self.current_index, len(self.items) - 1))
        return self.items[idx] if self.items else ""

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        width = self.width()
        height = self.height()
        center_y = height / 2.0

        painter.setPen(QColor(255, 255, 255, 35))
        painter.drawLine(6, int(center_y - self.item_height / 2), width - 6, int(center_y - self.item_height / 2))
        painter.drawLine(6, int(center_y + self.item_height / 2), width - 6, int(center_y + self.item_height / 2))

        visible_half = int((height / 2) / self.item_height) + 1
        base_index = int(self._offset)
        remainder = self._offset - base_index

        font = QFont("Microsoft YaHei", 10)
        font.setBold(True)
        for i in range(-visible_half - 1, visible_half + 2):
            idx = base_index + i
            if 0 <= idx < len(self.items):
                distance = i - remainder
                y_pos = center_y + distance * self.item_height
                max_dist = (height / 2.0) / self.item_height
                ratio = 1.0 - (abs(distance) / max_dist)
                if ratio <= 0:
                    continue
                alpha = int(255 * (ratio**1.4))
                color = QColor(200, 230, 255, alpha)
                if abs(distance) < 0.01:
                    color = QColor("#00E5FF")
                painter.setPen(color)
                font.setPointSize(11 + int(5 * ratio))
                painter.setFont(font)
                painter.drawText(
                    0,
                    int(y_pos - self.item_height / 2),
                    width,
                    self.item_height,
                    Qt.AlignmentFlag.AlignCenter,
                    self.items[idx],
                )

    def wheelEvent(self, event) -> None:
        if self.animation.state() == QAbstractAnimation.State.Running:
            self.animation.stop()
        delta = event.angleDelta().y()
        if delta == 0:
            return
        steps = delta / 120.0
        self._offset -= steps * 0.5
        if self._offset < 0:
            self._offset = 0.0
        elif self._offset > len(self.items) - 1:
            self._offset = float(len(self.items) - 1)
        self.update()
        self.stop_timer.start()

    def _snap_to_nearest(self) -> None:
        target = float(round(self._offset))
        target = max(0.0, min(target, len(self.items) - 1))
        self.animation.setStartValue(self._offset)
        self.animation.setEndValue(target)
        self.animation.start()

    def _emit_current(self) -> None:
        if self._suppress_emit:
            return
        self.valueChanged.emit(self.current_value)


class DateWheel(QWidget):
    dateChanged = Signal(QDate)

    def __init__(self) -> None:
        super().__init__()
        self._min = QDate(2000, 1, 1)
        self._max = QDate(2099, 12, 31)
        self._updating = False
        self._year_items = [str(y) for y in range(self._min.year(), self._max.year() + 1)]
        self._month_items = [f"{m:02d}" for m in range(1, 13)]
        self._day_items = [f"{d:02d}" for d in range(1, 32)]

        self._year_wheel = ScrollWheelWidget(self._year_items)
        self._month_wheel = ScrollWheelWidget(self._month_items)
        self._day_wheel = ScrollWheelWidget(self._day_items)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self._year_wheel)
        layout.addWidget(self._month_wheel)
        layout.addWidget(self._day_wheel)

        self._date = QDate.currentDate()
        self._year_wheel.valueChanged.connect(self._handle_change)
        self._month_wheel.valueChanged.connect(self._handle_change)
        self._day_wheel.valueChanged.connect(self._handle_change)
        self.setDate(self._date)

    def date(self) -> QDate:
        return self._date

    def setDate(self, date: QDate) -> None:
        clamped = self._clamp(date)
        if clamped == self._date:
            return
        self._updating = True
        self._date = clamped
        self._year_wheel._suppress_emit = True
        self._month_wheel._suppress_emit = True
        self._day_wheel._suppress_emit = True
        self._year_wheel.set_index(self._year_items.index(str(clamped.year())), emit=False)
        self._month_wheel.set_index(clamped.month() - 1, emit=False)
        self._update_day_items(clamped.year(), clamped.month(), clamped.day(), emit=False)
        self._year_wheel._suppress_emit = False
        self._month_wheel._suppress_emit = False
        self._day_wheel._suppress_emit = False
        self._updating = False
        self.dateChanged.emit(self._date)

    def _clamp(self, date: QDate) -> QDate:
        if date < self._min:
            return self._min
        if date > self._max:
            return self._max
        return date

    def _update_day_items(self, year: int, month: int, day: int, emit: bool = True) -> None:
        max_day = QDate(year, month, 1).daysInMonth()
        self._day_items = [f"{d:02d}" for d in range(1, max_day + 1)]
        self._day_wheel.set_items(self._day_items)
        self._day_wheel.set_index(min(day, max_day) - 1, emit=emit)

    def _handle_change(self, _value: str) -> None:
        if self._updating:
            return
        year_str = self._year_wheel.current_value
        month_str = self._month_wheel.current_value
        day_str = self._day_wheel.current_value
        
        if not (year_str and month_str and day_str):
             return

        year = int(year_str)
        month = int(month_str)
        day = int(day_str)
        
        self._updating = True
        # Update day items based on year/month
        self._update_day_items(year, month, day, emit=False)
        
        # Re-read day because it might have been clamped by _update_day_items
        day_str = self._day_wheel.current_value
        if day_str:
            day = int(day_str)
        
        self._updating = False
        
        max_day = QDate(year, month, 1).daysInMonth()
        day = min(day, max_day)
        
        try:
            new_date = QDate(year, month, day)
            if new_date.isValid() and new_date != self._date:
                self._date = new_date
                self.dateChanged.emit(self._date)
        except Exception:
            pass


class DateEditPopup(QWidget):
    dateSelected = Signal(QDate)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Main container with styling
        self._container = QWidget(self)
        self._container.setObjectName("DatePopupContainer")
        self._container.setStyleSheet("""
            QWidget#DatePopupContainer {
                background-color: #1a1b26;
                border: 1px solid #414868;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #7aa2f7;
                color: #1a1b26;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #89b4fa;
            }
            QPushButton:pressed {
                background-color: #6d91de;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._container)
        
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(16, 16, 16, 16)
        container_layout.setSpacing(12)
        
        self._wheel = DateWheel()
        container_layout.addWidget(self._wheel)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self._confirm_btn = QPushButton("确认")
        self._confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._confirm_btn.clicked.connect(self._confirm)
        
        btn_layout.addWidget(self._confirm_btn)
        btn_layout.addStretch()
        
        container_layout.addLayout(btn_layout)

    def setDate(self, date: QDate) -> None:
        self._wheel.setDate(date)

    def _confirm(self) -> None:
        self.dateSelected.emit(self._wheel.date())
        self.close()

    def show_at(self, pos) -> None:
        # Move first to get geometry
        self.move(pos)
        self.show()
        
        # Adjust position if out of screen bounds
        screen = self.screen()
        if not screen:
            return
            
        screen_geo = screen.availableGeometry()
        popup_geo = self.geometry()
        
        # Check right edge
        if popup_geo.right() > screen_geo.right():
            diff = popup_geo.right() - screen_geo.right()
            new_x = popup_geo.x() - diff - 10  # Add some padding
            self.move(new_x, popup_geo.y())
            
        # Check bottom edge
        if popup_geo.bottom() > screen_geo.bottom():
            diff = popup_geo.bottom() - screen_geo.bottom()
            new_y = popup_geo.y() - diff - 10
            self.move(self.x(), new_y)
