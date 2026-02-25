import time
from datetime import date

from PySide6.QtCore import QObject, QTimer, Signal

from timetracker.config.config_manager import ConfigManager
from timetracker.storage.models import FocusSession, FocusSlice
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
        self._idle = False
        self._current_session: FocusSession | None = None
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

    def set_idle(self, idle: bool) -> None:
        self._idle = idle

    def _poll(self) -> None:
        if self._paused:
            return
        if self._idle:
            window = None
            tab = None
            result = CategoryResult("app", "system.idle", "Idle")
        else:
            window = win_api.get_foreground_window()
            if window is None:
                return
            tab = self._select_tab(window.process_name)
            result = self._classifier.classify(window, tab)
        ts = int(time.time())
        duration_sec = max(1, int(round(self._sample_interval_ms / 1000)))
        slice_item = FocusSlice(
            ts=ts,
            date=date.fromtimestamp(ts).isoformat(),
            process_name=window.process_name if window else "idle",
            app_display=window.app_display if window else "Idle",
            window_title=window.window_title if window else "Idle",
            browser_name=tab.browser if tab else None,
            domain=tab.domain if tab else None,
            url=None if self._config.get_bool("privacy_mode") else (tab.url if tab else None),
            category_type=result.category_type,
            category_key=result.category_key,
            category_name=result.category_name,
            duration_sec=duration_sec,
        )
        self._repo.append_slice(slice_item)
        self._update_session(slice_item, ts, duration_sec)
        now = time.monotonic()
        if now - self._last_flush_monotonic >= self._flush_interval_sec:
            self._repo.flush()
            self._last_flush_monotonic = now
        self.on_sample.emit(result)

    def _update_session(self, slice_item: FocusSlice, ts: int, duration_sec: int) -> None:
        interval_sec = max(1, int(round(self._sample_interval_ms / 1000)))
        threshold = interval_sec * 3
        if self._current_session is None:
            started_at = ts - duration_sec + 1
            session = FocusSession(
                id=None,
                date=slice_item.date,
                category_type=slice_item.category_type,
                category_key=slice_item.category_key,
                category_name=slice_item.category_name,
                started_at=started_at,
                ended_at=ts,
                duration_sec=duration_sec,
            )
            session_id = self._repo.insert_session(session)
            self._current_session = FocusSession(
                id=session_id,
                date=session.date,
                category_type=session.category_type,
                category_key=session.category_key,
                category_name=session.category_name,
                started_at=session.started_at,
                ended_at=session.ended_at,
                duration_sec=session.duration_sec,
            )
            return
        same_key = slice_item.category_key == self._current_session.category_key
        gap = ts - self._current_session.ended_at
        if same_key and gap <= threshold:
            ended_at = ts
            duration = ended_at - self._current_session.started_at + 1
            self._repo.update_session_end(self._current_session.id or 0, ended_at, duration)
            self._current_session = FocusSession(
                id=self._current_session.id,
                date=self._current_session.date,
                category_type=self._current_session.category_type,
                category_key=self._current_session.category_key,
                category_name=self._current_session.category_name,
                started_at=self._current_session.started_at,
                ended_at=ended_at,
                duration_sec=duration,
            )
            return
        started_at = ts - duration_sec + 1
        session = FocusSession(
            id=None,
            date=slice_item.date,
            category_type=slice_item.category_type,
            category_key=slice_item.category_key,
            category_name=slice_item.category_name,
            started_at=started_at,
            ended_at=ts,
            duration_sec=duration_sec,
        )
        session_id = self._repo.insert_session(session)
        self._current_session = FocusSession(
            id=session_id,
            date=session.date,
            category_type=session.category_type,
            category_key=session.category_key,
            category_name=session.category_name,
            started_at=session.started_at,
            ended_at=session.ended_at,
            duration_sec=session.duration_sec,
        )

    def _select_tab(self, process_name: str) -> TabInfo | None:
        if not process_name:
            return None
        name = process_name.lower()
        if name not in {"chrome.exe", "msedge.exe"}:
            return None
        return self._bridge.get_current_tab()
