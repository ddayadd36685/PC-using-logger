from dataclasses import dataclass
import ctypes
from ctypes import wintypes
from typing import Optional

from comtypes import GUID, COMMETHOD, HRESULT, IUnknown, POINTER  # type: ignore
from comtypes import client as com_client  # type: ignore

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
    pid: int = 0


def _get_pid_and_path(hwnd: int) -> tuple[int, str]:
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    if not pid:
        return 0, ""
    try:
        process = win32api.OpenProcess(
            win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid
        )
    except Exception:
        return pid, ""
    try:
        path = win32process.GetModuleFileNameEx(process, 0)
        return pid, path
    except Exception:
        return pid, ""
    finally:
        win32api.CloseHandle(process)


def get_foreground_window() -> Optional[WindowInfo]:
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return None
    try:
        title = win32gui.GetWindowText(hwnd) or ""
        pid, path = _get_pid_and_path(hwnd)
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
            pid=pid,
        )
    except Exception:
        return None


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


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


def get_idle_seconds() -> float:
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    tick_count = ctypes.windll.kernel32.GetTickCount()
    idle_ms = tick_count - info.dwTime
    return max(0.0, idle_ms / 1000.0)


# Audio Endpoint API
CLSID_MMDeviceEnumerator = GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}")
IID_IMMDeviceEnumerator = GUID("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
IID_IMMDevice = GUID("{D666063F-1587-4E43-81F1-B948E807363F}")
IID_IAudioMeterInformation = GUID("{C02216F6-8C67-4B5B-9D00-D008E73E0064}")

class IMMDevice(IUnknown):
    _iid_ = IID_IMMDevice
    _methods_ = [
        COMMETHOD([], HRESULT, "Activate",
                  (["in"], POINTER(GUID), "iid"),
                  (["in"], ctypes.c_int, "dwClsCtx"),
                  (["in"], POINTER(ctypes.c_int), "pActivationParams"),
                  (["out"], POINTER(POINTER(IUnknown)), "ppInterface")),
    ]

class IMMDeviceEnumerator(IUnknown):
    _iid_ = IID_IMMDeviceEnumerator
    _methods_ = [
        COMMETHOD([], HRESULT, "EnumAudioEndpoints",
                  (["in"], ctypes.c_int, "dataFlow"),
                  (["in"], ctypes.c_int, "dwStateMask"),
                  (["out"], POINTER(POINTER(IUnknown)), "ppDevices")),
        COMMETHOD([], HRESULT, "GetDefaultAudioEndpoint",
                  (["in"], ctypes.c_int, "dataFlow"),
                  (["in"], ctypes.c_int, "role"),
                  (["out"], POINTER(POINTER(IMMDevice)), "ppEndpoint")),
    ]

class IAudioMeterInformation(IUnknown):
    _iid_ = IID_IAudioMeterInformation
    _methods_ = [
        COMMETHOD([], HRESULT, "GetPeakValue",
                  (["out"], POINTER(ctypes.c_float), "pfPeak")),
    ]

IID_IAudioSessionManager2 = GUID("{77AA99A0-1BD6-484F-8BC2-3C8DFE1A6A91}")
IID_IAudioSessionControl = GUID("{F4B1A599-7266-4319-A8CA-E70ACB11E8CD}")
IID_IAudioSessionControl2 = GUID("{BFB7FF88-7239-4FC9-8FA2-07C950BE9C6D}")
IID_IAudioSessionEnumerator = GUID("{E2F5BB11-0570-40CA-ACDD-3AA01277DEE8}")

class IAudioSessionControl(IUnknown):
    _iid_ = IID_IAudioSessionControl
    _methods_ = [
        COMMETHOD([], HRESULT, "GetState", (["out"], POINTER(ctypes.c_int), "pRetVal")),
        COMMETHOD([], HRESULT, "GetDisplayName", (["out"], POINTER(ctypes.c_wchar_p), "pRetVal")),
        COMMETHOD([], HRESULT, "SetDisplayName", (["in"], ctypes.c_wchar_p, "Value"), (["in"], POINTER(GUID), "EventContext")),
        COMMETHOD([], HRESULT, "GetIconPath", (["out"], POINTER(ctypes.c_wchar_p), "pRetVal")),
        COMMETHOD([], HRESULT, "SetIconPath", (["in"], ctypes.c_wchar_p, "Value"), (["in"], POINTER(GUID), "EventContext")),
        COMMETHOD([], HRESULT, "GetGroupingParam", (["out"], POINTER(GUID), "pRetVal")),
        COMMETHOD([], HRESULT, "SetGroupingParam", (["in"], POINTER(GUID), "Override"), (["in"], POINTER(GUID), "EventContext")),
        COMMETHOD([], HRESULT, "RegisterAudioSessionNotification", (["in"], POINTER(IUnknown), "NewNotifications")),
        COMMETHOD([], HRESULT, "UnregisterAudioSessionNotification", (["in"], POINTER(IUnknown), "NewNotifications")),
    ]

class IAudioSessionControl2(IAudioSessionControl):
    _iid_ = IID_IAudioSessionControl2
    _methods_ = [
        COMMETHOD([], HRESULT, "GetSessionIdentifier", (["out"], POINTER(ctypes.c_wchar_p), "pRetVal")),
        COMMETHOD([], HRESULT, "GetSessionInstanceIdentifier", (["out"], POINTER(ctypes.c_wchar_p), "pRetVal")),
        COMMETHOD([], HRESULT, "GetProcessId", (["out"], POINTER(ctypes.c_uint), "pRetVal")),
        COMMETHOD([], HRESULT, "IsSystemSoundsSession", (["out"], POINTER(ctypes.c_int), "pRetVal")),
        COMMETHOD([], HRESULT, "SetDuckingPreference", (["in"], ctypes.c_int, "optOut")),
    ]

class IAudioSessionEnumerator(IUnknown):
    _iid_ = IID_IAudioSessionEnumerator
    _methods_ = [
        COMMETHOD([], HRESULT, "GetCount", (["out"], POINTER(ctypes.c_int), "SessionCount")),
        COMMETHOD([], HRESULT, "GetSession", (["in"], ctypes.c_int, "SessionCount"), (["out"], POINTER(POINTER(IAudioSessionControl)), "Session")),
    ]

class IAudioSessionManager2(IUnknown):
    _iid_ = IID_IAudioSessionManager2
    _methods_ = [
        COMMETHOD([], HRESULT, "GetAudioSessionNotification", (["out"], POINTER(POINTER(IUnknown)), "NewNotifications")),
        COMMETHOD([], HRESULT, "GetSessionEnumerator", (["out"], POINTER(POINTER(IAudioSessionEnumerator)), "SessionEnum")),
        COMMETHOD([], HRESULT, "RegisterSessionNotification", (["in"], POINTER(IUnknown), "NewNotifications")),
        COMMETHOD([], HRESULT, "UnregisterSessionNotification", (["in"], POINTER(IUnknown), "NewNotifications")),
        COMMETHOD([], HRESULT, "RegisterDuckNotification", (["in"], ctypes.c_wchar_p, "sessionID"), (["in"], POINTER(IUnknown), "NewNotifications")),
        COMMETHOD([], HRESULT, "UnregisterDuckNotification", (["in"], POINTER(IUnknown), "NewNotifications")),
    ]

def is_audio_playing(pid: int | None = None) -> bool:
    """
    Check if audio is playing.
    If pid is provided, checks if the specific process is playing audio.
    If pid is None, checks if any audio is playing on the default device.
    """
    try:
        enumerator = com_client.CreateObject(
            CLSID_MMDeviceEnumerator,
            interface=IMMDeviceEnumerator
        )
        endpoint = enumerator.GetDefaultAudioEndpoint(0, 0)
        
        # If no PID specified, check global peak value
        if pid is None:
            interface_ptr = endpoint.Activate(IID_IAudioMeterInformation, 1, None)
            meter = interface_ptr.QueryInterface(IAudioMeterInformation)
            val = meter.GetPeakValue()
            return val > 1e-4

        # If PID specified, check session specific peak value
        session_manager = endpoint.Activate(IID_IAudioSessionManager2, 1, None).QueryInterface(IAudioSessionManager2)
        session_enumerator = session_manager.GetSessionEnumerator()
        count = session_enumerator.GetCount()

        for i in range(count):
            session_control = session_enumerator.GetSession(i)
            try:
                session_control2 = session_control.QueryInterface(IAudioSessionControl2)
                session_pid = session_control2.GetProcessId()
                if session_pid == pid:
                    meter = session_control.QueryInterface(IAudioMeterInformation)
                    val = meter.GetPeakValue()
                    if val > 1e-4:
                        return True
            except Exception:
                continue
                
        return False
    except Exception:
        return False
