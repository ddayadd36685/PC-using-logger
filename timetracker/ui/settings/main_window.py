from __future__ import annotations

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow, QTabWidget

from timetracker.ui.settings.app_list_page import AppListPage
from timetracker.ui.settings.general_page import GeneralPage
from timetracker.ui.settings.health_page import HealthPage
from timetracker.ui.settings.privacy_page import PrivacyPage
from timetracker.ui.settings.stats_page import StatsPage


class SettingsWindow(QMainWindow):
    def __init__(
        self,
        stats_page: StatsPage,
        app_list_page: AppListPage,
        general_page: GeneralPage,
        privacy_page: PrivacyPage,
        health_page: HealthPage,
    ) -> None:
        super().__init__()
        self.setWindowTitle("AI时间监控控制台")
        self._tabs = QTabWidget()
        self._tabs.addTab(stats_page, "统计控制台")
        self._tabs.addTab(app_list_page, "名单")
        self._tabs.addTab(general_page, "外观与行为")
        self._tabs.addTab(health_page, "健康提醒")
        self._tabs.addTab(privacy_page, "隐私与数据")
        self.setCentralWidget(self._tabs)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.hide()
        event.ignore()
