from dataclasses import dataclass
from typing import Optional

import win32api
import win32con
import win32gui
import win32process
import win32ts


@dataclass(frozen=True)
class WindowInfo:
    process_name: str
    app_display: str
    window_title: str
    is_fullscreen: bool


def _get_process_path(hwnd: int) -> str:
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    if not pid:
        return ""
    process = win32api.OpenProcess(
        win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid
    )
    try:
        return win32process.GetModuleFileNameEx(process, 0)
    finally:
        win32api.CloseHandle(process)


def get_foreground_window() -> Optional[WindowInfo]:
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return None
    title = win32gui.GetWindowText(hwnd) or ""
    path = _get_process_path(hwnd)
    process_name = path.split("\\")[-1].lower() if path else ""
    app_display = process_name
    rect = win32gui.GetWindowRect(hwnd)
    screen_w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    screen_h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    is_fullscreen = rect[0] <= 0 and rect[1] <= 0 and rect[2] >= screen_w and rect[3] >= screen_h
    return WindowInfo(
        process_name=process_name,
        app_display=app_display,
        window_title=title,
        is_fullscreen=is_fullscreen,
    )


def is_screen_locked() -> bool:
    try:
        session_id = win32ts.WTSGetActiveConsoleSessionId()
        state = win32ts.WTSQuerySessionInformation(
            0, session_id, win32ts.WTSConnectState
        )
        if isinstance(state, tuple):
            state = state[0]
        return state != win32ts.WTSActive
    except Exception:
        return False
