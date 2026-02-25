from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QCheckBox, QFormLayout, QSpinBox, QWidget

from timetracker.config.config_manager import ConfigManager


class GeneralPage(QWidget):
    def __init__(
        self,
        config: ConfigManager,
        on_toggle_ball: Callable[[bool], None],
    ) -> None:
        super().__init__()
        self._config = config
        self._on_toggle_ball = on_toggle_ball

        self._ball_checkbox = QCheckBox("显示悬浮球")
        self._ball_checkbox.setChecked(self._config.get_bool("floating_ball_visible"))
        self._ball_checkbox.toggled.connect(self._handle_ball_toggle)

        self._autostart_checkbox = QCheckBox("开机自启")
        self._autostart_checkbox.setChecked(self._config.get_bool("autostart"))
        self._autostart_checkbox.toggled.connect(self._handle_autostart_toggle)

        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(500, 5000)
        self._interval_spin.setSingleStep(100)
        self._interval_spin.setValue(self._config.get_int("sample_interval_ms"))
        self._interval_spin.valueChanged.connect(self._handle_interval_change)

        layout = QFormLayout()
        layout.addRow(self._ball_checkbox)
        layout.addRow(self._autostart_checkbox)
        layout.addRow("采样间隔（毫秒）", self._interval_spin)
        self.setLayout(layout)

    def _handle_ball_toggle(self, checked: bool) -> None:
        self._config.set("floating_ball_visible", checked)
        self._on_toggle_ball(checked)

    def _handle_autostart_toggle(self, checked: bool) -> None:
        self._config.set("autostart", checked)

    def _handle_interval_change(self, value: int) -> None:
        self._config.set("sample_interval_ms", value)
