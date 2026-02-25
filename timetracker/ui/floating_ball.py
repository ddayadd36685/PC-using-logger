from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import math
from typing import Callable, Optional

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QMenu, QWidget


@dataclass(frozen=True)
class FloatingBallState:
    title: str
    duration_sec: int


class FloatingBall(QWidget):
    def __init__(
        self,
        on_open_settings: Optional[Callable[[], None]] = None,
        on_open_health: Optional[Callable[[], None]] = None,
        on_hide: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)
        self._drag_offset: QPoint | None = None
        self._on_open_settings = on_open_settings
        self._on_open_health = on_open_health
        self._on_hide = on_hide
        self._on_quit = on_quit
        self._menu = QMenu(self)
        action_open = self._menu.addAction("打开设置")
        action_health = self._menu.addAction("打开健康遮罩")
        action_hide = self._menu.addAction("隐藏悬浮球")
        action_quit = self._menu.addAction("退出")
        action_open.triggered.connect(self._handle_open_settings)
        action_health.triggered.connect(self._handle_open_health)
        action_hide.triggered.connect(self._handle_hide)
        action_quit.triggered.connect(self._handle_quit)
        self._title = "未开始采样"
        self._duration = "0:00:00"
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)
        self.setFixedSize(108, 108)

    def update_state(self, state: FloatingBallState) -> None:
        duration = str(timedelta(seconds=state.duration_sec))
        self._title = state.title
        self._duration = duration
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect()
        center = rect.center()
        radius = rect.width() * 0.32
        pulse = (math.sin(self._phase) + 1.0) / 2.0
        glow_radius = rect.width() * (0.38 + 0.05 * pulse)
        gradient = QRadialGradient(center, glow_radius)
        gradient.setColorAt(0.0, QColor(0, 229, 255, 200))
        gradient.setColorAt(0.6, QColor(124, 77, 255, 90))
        gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, glow_radius, glow_radius)
        core_gradient = QRadialGradient(center, radius)
        core_gradient.setColorAt(0.0, QColor(0, 229, 255, 255))
        core_gradient.setColorAt(0.6, QColor(14, 24, 44, 255))
        core_gradient.setColorAt(1.0, QColor(6, 10, 20, 255))
        painter.setBrush(core_gradient)
        painter.setPen(QPen(QColor(0, 229, 255, 160), 2))
        painter.drawEllipse(center, radius, radius)
        title_font = QFont("Microsoft YaHei", 10)
        title_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(title_font)
        painter.setPen(QColor("#7CEBFF"))
        painter.drawText(rect.adjusted(0, 10, 0, -30), Qt.AlignmentFlag.AlignCenter, self._title)
        duration_font = QFont("Microsoft YaHei", 10)
        duration_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(duration_font)
        painter.setPen(QColor("#7CEBFF"))
        painter.drawText(rect.adjusted(0, 36, 0, -4), Qt.AlignmentFlag.AlignCenter, self._duration)

    def _tick(self) -> None:
        self._phase += 0.04
        if self._phase >= 2 * math.pi:
            self._phase = 0.0
        self.update()

    def contextMenuEvent(self, event) -> None:
        self._menu.exec(event.globalPos())

    def set_callbacks(
        self,
        on_open_settings: Optional[Callable[[], None]],
        on_open_health: Optional[Callable[[], None]],
        on_hide: Optional[Callable[[], None]],
        on_quit: Optional[Callable[[], None]],
    ) -> None:
        self._on_open_settings = on_open_settings
        self._on_open_health = on_open_health
        self._on_hide = on_hide
        self._on_quit = on_quit

    def _handle_open_settings(self) -> None:
        if self._on_open_settings:
            self._on_open_settings()

    def _handle_open_health(self) -> None:
        if self._on_open_health:
            self._on_open_health()

    def _handle_hide(self) -> None:
        if self._on_hide:
            self._on_hide()

    def _handle_quit(self) -> None:
        if self._on_quit:
            self._on_quit()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is None:
            return
        self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event) -> None:
        if self._drag_offset is None:
            return
        self._drag_offset = None
        self._snap_to_edge()

    def _snap_to_edge(self) -> None:
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return
        rect = screen.availableGeometry()
        current = self.frameGeometry()
        left = rect.left()
        right = rect.right() - current.width()
        top = rect.top()
        bottom = rect.bottom() - current.height()
        x = left if abs(current.left() - left) < abs(current.left() - right) else right
        y = min(max(current.top(), top), bottom)
        self.move(x, y)
