from dataclasses import dataclass
import asyncio
import json
import threading
import time
from typing import Optional

import tldextract
import websockets


@dataclass(frozen=True)
class TabInfo:
    url: str
    domain: str
    title: str
    browser: str
    ts: float


class BrowserBridgeServer:
    def __init__(self) -> None:
        self._current: Optional[TabInfo] = None
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._ready_event = threading.Event()
        self._last_error: str | None = None
        self._host = "127.0.0.1"
        self._port = 49152

    def start(self, host: str = "127.0.0.1", port: int = 49152) -> None:
        self._host = host
        self._port = port
        if self._thread and self._thread.is_alive():
            return None
        self._stop_event.clear()
        self._ready_event.clear()
        self._last_error = None
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        return None

    def get_current_tab(self) -> Optional[TabInfo]:
        with self._lock:
            return self._current

    def stop(self) -> None:
        self._stop_event.set()
        self._ready_event.clear()

    def _run_loop(self) -> None:
        try:
            asyncio.run(self._serve())
        except Exception as exc:
            self._last_error = str(exc)
            self._ready_event.clear()

    async def _serve(self) -> None:
        try:
            async with websockets.serve(self._handler, self._host, self._port):
                self._ready_event.set()
                while not self._stop_event.is_set():
                    await asyncio.sleep(0.5)
        except Exception as exc:
            self._last_error = str(exc)
            self._ready_event.clear()

    def wait_ready(self, timeout_sec: float = 1.5) -> bool:
        return self._ready_event.wait(timeout=timeout_sec)

    def get_start_error(self) -> str | None:
        return self._last_error

    async def _handler(self, websocket) -> None:
        async for message in websocket:
            try:
                payload = json.loads(message)
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            if payload.get("type") != "tab_change":
                continue
            url = str(payload.get("url") or "")
            title = str(payload.get("title") or "")
            browser = str(payload.get("browser") or "")
            ts = float(payload.get("ts") or time.time())
            domain = self._extract_domain(url)
            info = TabInfo(url=url, domain=domain, title=title, browser=browser, ts=ts)
            with self._lock:
                self._current = info

    @staticmethod
    def _extract_domain(url: str) -> str:
        if not url:
            return ""
        extracted = tldextract.extract(url)
        if extracted.registered_domain:
            return extracted.registered_domain
        parts = [p for p in [extracted.domain, extracted.suffix] if p]
        return ".".join(parts)
