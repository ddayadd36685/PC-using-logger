from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QCheckBox, QFormLayout, QLineEdit, QPushButton, QSpinBox, QWidget

from timetracker.config.config_manager import ConfigManager


class HealthPage(QWidget):
    def __init__(self, config: ConfigManager, on_toggle_health: Callable[[bool], None]) -> None:
        super().__init__()
        self._config = config
        self._on_toggle_health = on_toggle_health

        self._enabled_checkbox = QCheckBox("启用健康提醒")
        self._enabled_checkbox.setChecked(self._config.get_bool("health_enabled"))
        self._enabled_checkbox.toggled.connect(self._handle_enabled_toggle)

        self._work_spin = QSpinBox()
        self._work_spin.setRange(10, 240)
        self._work_spin.setValue(self._config.get_int("health_work_min"))
        self._work_spin.valueChanged.connect(self._handle_work_change)

        self._rest_spin = QSpinBox()
        self._rest_spin.setRange(1, 60)
        self._rest_spin.setValue(self._config.get_int("health_rest_min"))
        self._rest_spin.valueChanged.connect(self._handle_rest_change)

        self._delay_spin = QSpinBox()
        self._delay_spin.setRange(0, 60)
        self._delay_spin.setValue(self._config.get_int("health_delay_min"))
        self._delay_spin.valueChanged.connect(self._handle_delay_change)

        self._skip_spin = QSpinBox()
        self._skip_spin.setRange(0, 10)
        self._skip_spin.setValue(self._config.get_int("health_skip_max"))
        self._skip_spin.valueChanged.connect(self._handle_skip_change)

        self._whitelist_input = QLineEdit()
        self._whitelist_input.setPlaceholderText("进程名或站点 key，用逗号分隔")
        self._whitelist_input.setText(",".join(self._config.get_json("health_whitelist") or []))

        self._save_whitelist = QPushButton("保存白名单")
        self._save_whitelist.clicked.connect(self._handle_whitelist_save)

        layout = QFormLayout()
        layout.addRow(self._enabled_checkbox)
        layout.addRow("连续工作（分钟）", self._work_spin)
        layout.addRow("休息时长（分钟）", self._rest_spin)
        layout.addRow("延迟时长（分钟）", self._delay_spin)
        layout.addRow("每日最多跳过次数", self._skip_spin)
        layout.addRow("白名单", self._whitelist_input)
        layout.addRow(self._save_whitelist)
        self.setLayout(layout)

    def _handle_enabled_toggle(self, checked: bool) -> None:
        self._config.set("health_enabled", checked)
        self._on_toggle_health(checked)

    def _handle_work_change(self, value: int) -> None:
        self._config.set("health_work_min", value)

    def _handle_rest_change(self, value: int) -> None:
        self._config.set("health_rest_min", value)

    def _handle_delay_change(self, value: int) -> None:
        self._config.set("health_delay_min", value)

    def _handle_skip_change(self, value: int) -> None:
        self._config.set("health_skip_max", value)

    def _handle_whitelist_save(self) -> None:
        raw = self._whitelist_input.text()
        items = [item.strip() for item in raw.split(",") if item.strip()]
        self._config.set("health_whitelist", items)
        self._whitelist_input.setText(",".join(items))
