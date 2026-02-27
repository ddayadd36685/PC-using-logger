from __future__ import annotations

from typing import Callable

from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from timetracker.utils.paths import resource_path

class TrayController:
    def __init__(
        self,
        on_open_settings: Callable[[], None],
        on_open_health: Callable[[], None],
        on_toggle_tracking: Callable[[bool], None],
        on_toggle_ball: Callable[[bool], None],
        on_quit: Callable[[], None],
        ball_visible: bool = True,
    ) -> None:
        self._tray = QSystemTrayIcon()
        self._tray.setIcon(self._build_icon())
        self._menu = QMenu()

        self._action_open = QAction("打开设置")
        self._action_open.triggered.connect(on_open_settings)

        self._action_health = QAction("打开健康遮罩")
        self._action_health.triggered.connect(on_open_health)

        self._action_pause = QAction("暂停记录")
        self._action_pause.setCheckable(True)
        self._action_pause.toggled.connect(lambda checked: on_toggle_tracking(checked))

        self._action_ball = QAction("显示悬浮球")
        self._action_ball.setCheckable(True)
        self._action_ball.setChecked(ball_visible)
        self._action_ball.toggled.connect(lambda checked: on_toggle_ball(checked))

        self._action_quit = QAction("退出")
        self._action_quit.triggered.connect(on_quit)

        self._menu.addAction(self._action_open)
        self._menu.addAction(self._action_health)
        self._menu.addSeparator()
        self._menu.addAction(self._action_pause)
        self._menu.addAction(self._action_ball)
        self._menu.addSeparator()
        self._menu.addAction(self._action_quit)

        self._tray.setContextMenu(self._menu)

    def show(self) -> None:
        self._tray.show()

    def set_ball_visible(self, visible: bool) -> None:
        self._action_ball.setChecked(visible)

    def set_tracking_paused(self, paused: bool) -> None:
        self._action_pause.setChecked(paused)

    def set_tooltip(self, text: str) -> None:
        self._tray.setToolTip(text)

    @staticmethod
    def _build_icon() -> QIcon:
        icon_path = resource_path("timetracker/assets/Health_Monitor_Icon.ico")
        if icon_path.exists():
            return QIcon(str(icon_path))
        pixmap = QPixmap(32, 32)
        pixmap.fill()
        return QIcon(pixmap)
