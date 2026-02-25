import time
from datetime import date

from PySide6.QtCore import QObject, QTimer, Signal

from timetracker.config.config_manager import ConfigManager
from timetracker.storage.models import FocusSlice
from timetracker.storage.repository import Repository
from timetracker.tracker.classifier import CategoryResult, Classifier
from timetracker.tracker import win_api
from timetracker.tracker.browser_bridge import BrowserBridgeServer, TabInfo


class Tracker(QObject):
    on_sample = Signal(object)

    def __init__(
        self,
        repo: Repository,
        config: ConfigManager,
        classifier: Classifier,
        bridge: BrowserBridgeServer,
    ) -> None:
        super().__init__()
        self._repo = repo
        self._config = config
        self._classifier = classifier
        self._bridge = bridge
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._paused = False
        self._last_flush_monotonic = time.monotonic()
        self._flush_interval_sec = 10
        self._sample_interval_ms = self._config.get_int("sample_interval_ms")

    def start(self) -> None:
        self._sample_interval_ms = self._config.get_int("sample_interval_ms")
        self._timer.setInterval(self._sample_interval_ms)
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self._repo.flush()

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def _poll(self) -> None:
        if self._paused:
            return
        if win_api.is_screen_locked():
            return
        window = win_api.get_foreground_window()
        if window is None:
            return
        tab = self._select_tab(window.process_name)
        result: CategoryResult = self._classifier.classify(window, tab)
        ts = int(time.time())
        duration_sec = max(1, int(round(self._sample_interval_ms / 1000)))
        slice_item = FocusSlice(
            ts=ts,
            date=date.fromtimestamp(ts).isoformat(),
            process_name=window.process_name,
            app_display=window.app_display,
            window_title=window.window_title,
            browser_name=tab.browser if tab else None,
            domain=tab.domain if tab else None,
            url=None if self._config.get_bool("privacy_mode") else (tab.url if tab else None),
            category_type=result.category_type,
            category_key=result.category_key,
            category_name=result.category_name,
            duration_sec=duration_sec,
        )
        self._repo.append_slice(slice_item)
        now = time.monotonic()
        if now - self._last_flush_monotonic >= self._flush_interval_sec:
            self._repo.flush()
            self._last_flush_monotonic = now
        self.on_sample.emit(result)

    def _select_tab(self, process_name: str) -> TabInfo | None:
        if not process_name:
            return None
        name = process_name.lower()
        if name not in {"chrome.exe", "msedge.exe"}:
            return None
        return self._bridge.get_current_tab()
