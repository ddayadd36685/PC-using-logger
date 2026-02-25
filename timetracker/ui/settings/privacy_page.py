from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QFormLayout, QMessageBox, QPushButton, QWidget

from timetracker.config.config_manager import ConfigManager
from timetracker.storage.repository import Repository


class PrivacyPage(QWidget):
    def __init__(self, config: ConfigManager, repo: Repository) -> None:
        super().__init__()
        self._config = config
        self._repo = repo

        self._privacy_checkbox = QCheckBox("隐私模式（仅保存域名）")
        self._privacy_checkbox.setChecked(self._config.get_bool("privacy_mode"))
        self._privacy_checkbox.toggled.connect(self._handle_privacy_toggle)

        self._clear_button = QPushButton("清理数据")
        self._clear_button.clicked.connect(self._handle_clear)

        layout = QFormLayout()
        layout.addRow(self._privacy_checkbox)
        layout.addRow(self._clear_button)
        self.setLayout(layout)

    def _handle_privacy_toggle(self, checked: bool) -> None:
        self._config.set("privacy_mode", checked)

    def _handle_clear(self) -> None:
        result = QMessageBox.question(self, "确认清理", "确定要清理所有本地数据吗？")
        if result == QMessageBox.StandardButton.Yes:
            self._repo.clear_data()
