import ctypes
import signal
import sys

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QMessageBox, QToolTip

from timetracker.config.config_manager import ConfigManager
from timetracker.health.health_manager import HealthManager
from timetracker.storage.db import Database
from timetracker.storage.repository import Repository
from timetracker.tracker.browser_bridge import BrowserBridgeServer
from timetracker.tracker.classifier import Classifier
from timetracker.tracker.tracker import Tracker
from timetracker.ui.floating_ball import FloatingBall, FloatingBallState
from timetracker.ui.settings.app_list_page import AppListPage
from timetracker.ui.settings.general_page import GeneralPage
from timetracker.ui.settings.health_page import HealthPage
from timetracker.ui.settings.main_window import SettingsWindow
from timetracker.ui.settings.privacy_page import PrivacyPage
from timetracker.ui.settings.stats_page import StatsPage
from timetracker.ui.overlay import RestOverlay
from timetracker.ui.tray import TrayController
from timetracker.ui.style import build_style
from timetracker.utils.paths import resource_path

APP_MUTEX_NAME = "TimeTracker_Unique_20240224"
APP_WINDOW_TITLE = "AI时间监控控制台"
_APP_MUTEX = None


def bring_existing_window_to_front() -> None:
    hwnd = ctypes.windll.user32.FindWindowW(None, APP_WINDOW_TITLE)
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 9)
        ctypes.windll.user32.SetForegroundWindow(hwnd)


def ensure_single_instance() -> bool:
    global _APP_MUTEX
    _APP_MUTEX = ctypes.windll.kernel32.CreateMutexW(None, False, APP_MUTEX_NAME)
    if ctypes.windll.kernel32.GetLastError() == 183:
        bring_existing_window_to_front()
        return False
    return True


def main() -> int:
    if not ensure_single_instance():
        return 0
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QFont("Microsoft YaHei", 10))
    QToolTip.setFont(QFont("Microsoft YaHei", 9))
    db = Database()
    config = ConfigManager(db)
    repo = Repository(db, store_raw_events=config.get_bool("store_raw_events"))
    classifier = Classifier()
    bridge = BrowserBridgeServer()
    bridge.start()
    if not bridge.wait_ready():
        detail = bridge.get_start_error() or "无法绑定本地端口 127.0.0.1:49152"
        QMessageBox.warning(None, "浏览器桥接启动失败", detail)
    tracker = Tracker(repo, config, classifier, bridge)
    floating_ball = FloatingBall()
    health_manager = HealthManager(config)
    overlay = RestOverlay(config)
    icon_path = resource_path("timetracker/assets/Health_Monitor_Icon.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    def apply_ball_visibility(visible: bool) -> None:
        if visible:
            floating_ball.show()
        else:
            floating_ball.hide()

    app.setStyleSheet(build_style())
    stats_page = StatsPage(repo, config)
    general_page = GeneralPage(config, apply_ball_visibility)
    privacy_page = PrivacyPage(config, repo)
    def apply_health_enabled(enabled: bool) -> None:
        config.set("health_enabled", enabled)
        if enabled:
            health_manager.start()
        else:
            health_manager.stop()

    health_page = HealthPage(config, apply_health_enabled)
    app_list_page = AppListPage(config, repo, stats_page.refresh_now)
    settings_window = SettingsWindow(stats_page, app_list_page, general_page, privacy_page, health_page)

    def open_settings() -> None:
        settings_window.show()
        settings_window.raise_()
        settings_window.activateWindow()

    def quit_app() -> None:
        tracker.stop()
        bridge.stop()
        health_manager.stop()
        app.quit()

    tray: TrayController | None = None

    def toggle_tracking(paused: bool) -> None:
        if paused:
            tracker.pause()
            health_manager.pause()
        else:
            tracker.resume()
            health_manager.resume()

    def toggle_ball(visible: bool) -> None:
        config.set("floating_ball_visible", visible)
        apply_ball_visibility(visible)
        if tray is not None:
            tray.set_ball_visible(visible)

    def open_health_overlay() -> None:
        health_manager.force_show_overlay()

    floating_ball.set_callbacks(open_settings, open_health_overlay, lambda: toggle_ball(False), quit_app)

    tray = TrayController(open_settings, open_health_overlay, toggle_tracking, toggle_ball, quit_app)
    tray.show()
    apply_ball_visibility(config.get_bool("floating_ball_visible"))
    apply_health_enabled(config.get_bool("health_enabled"))

    def handle_sigint(*_args: object) -> None:
        quit_app()

    signal.signal(signal.SIGINT, handle_sigint)

    def handle_sample(result) -> None:
        total = repo.get_today_current(result.category_key)
        floating_ball.update_state(FloatingBallState(result.category_name, total))
        tray.set_tooltip(f"当前：{result.category_name}")
        duration_sec = max(1, int(round(config.get_int("sample_interval_ms") / 1000)))
        health_manager.notify_working(result, duration_sec)

    tracker.on_sample.connect(handle_sample)
    overlay.set_callbacks(health_manager.user_start_rest, health_manager.user_delay, health_manager.user_skip)
    health_manager.on_show_overlay.connect(overlay.show_overlay)
    health_manager.on_hide_overlay.connect(overlay.hide_overlay)
    health_manager.on_rest_tick.connect(overlay.update_countdown)
    tracker.start()
    exit_code = app.exec()
    tracker.stop()
    return int(exit_code)


if __name__ == "__main__":
    sys.exit(main())
