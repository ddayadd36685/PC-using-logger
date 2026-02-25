from __future__ import annotations

from datetime import date
from enum import Enum

from PySide6.QtCore import QObject, QTimer, Signal

from timetracker.config.config_manager import ConfigManager
from timetracker.tracker.classifier import CategoryResult
from timetracker.tracker import win_api


class HealthState(Enum):
    WORKING = "working"
    OVERLAY_SHOWN = "overlay_shown"
    RESTING = "resting"
    PAUSED = "paused"


class HealthManager(QObject):
    on_show_overlay = Signal()
    on_hide_overlay = Signal()
    on_rest_tick = Signal(int)

    def __init__(self, config: ConfigManager) -> None:
        super().__init__()
        self._config = config
        self._state = HealthState.PAUSED
        self._work_sec = 0
        self._rest_remaining = 0
        self._skip_count = 0
        self._current_day = date.today()
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick_rest)

    def start(self) -> None:
        if self._state == HealthState.PAUSED:
            self._state = HealthState.WORKING

    def stop(self) -> None:
        self._state = HealthState.PAUSED
        self._work_sec = 0
        self._rest_remaining = 0
        self._timer.stop()
        self.on_hide_overlay.emit()

    def pause(self) -> None:
        if self._state != HealthState.PAUSED:
            self._state = HealthState.PAUSED
            self._timer.stop()
            self.on_hide_overlay.emit()

    def resume(self) -> None:
        if self._state == HealthState.PAUSED:
            self._state = HealthState.WORKING

    def notify_working(self, result: CategoryResult, duration_sec: int) -> None:
        if self._state != HealthState.WORKING:
            return
        self._maybe_reset_day()
        if self._is_whitelisted(result):
            return
        if self._is_fullscreen():
            return
        self._work_sec += duration_sec
        if self._work_sec < self._work_threshold():
            return
        self._state = HealthState.OVERLAY_SHOWN
        self.on_show_overlay.emit()

    def user_start_rest(self) -> None:
        if self._state != HealthState.OVERLAY_SHOWN:
            return
        self._rest_remaining = self._rest_duration()
        if self._rest_remaining <= 0:
            self._state = HealthState.WORKING
            self._work_sec = 0
            self.on_hide_overlay.emit()
            return
        self._state = HealthState.RESTING
        self.on_rest_tick.emit(self._rest_remaining)
        self._timer.start()

    def force_show_overlay(self) -> None:
        self._maybe_reset_day()
        if self._state == HealthState.RESTING:
            return
        self._state = HealthState.OVERLAY_SHOWN
        self.on_show_overlay.emit()

    def user_delay(self) -> None:
        if self._state != HealthState.OVERLAY_SHOWN:
            return
        delay_sec = max(0, self._config.get_int("health_delay_min") * 60)
        self._work_sec = max(0, self._work_threshold() - delay_sec)
        self._state = HealthState.WORKING
        self.on_hide_overlay.emit()

    def user_skip(self) -> bool:
        if self._state != HealthState.OVERLAY_SHOWN:
            return False
        if self._skip_count >= self._config.get_int("health_skip_max"):
            return False
        self._skip_count += 1
        self._work_sec = 0
        self._state = HealthState.WORKING
        self.on_hide_overlay.emit()
        return True

    def _tick_rest(self) -> None:
        if self._state != HealthState.RESTING:
            return
        self._rest_remaining -= 1
        if self._rest_remaining <= 0:
            self._timer.stop()
            self._state = HealthState.WORKING
            self._work_sec = 0
            self.on_hide_overlay.emit()
            return
        self.on_rest_tick.emit(self._rest_remaining)

    def _work_threshold(self) -> int:
        return max(1, self._config.get_int("health_work_min") * 60)

    def _rest_duration(self) -> int:
        return max(0, self._config.get_int("health_rest_min") * 60)

    def _maybe_reset_day(self) -> None:
        today = date.today()
        if today != self._current_day:
            self._current_day = today
            self._work_sec = 0
            self._skip_count = 0

    def _is_whitelisted(self, result: CategoryResult) -> bool:
        whitelist = self._config.get_json("health_whitelist") or []
        key = (result.category_key or "").lower()
        return key in {str(item).lower() for item in whitelist}

    def _is_fullscreen(self) -> bool:
        window = win_api.get_foreground_window()
        return bool(window and window.is_fullscreen)
