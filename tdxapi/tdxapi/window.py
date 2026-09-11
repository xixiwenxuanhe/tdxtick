"""Programmatically drive the TDX window (no manual clicking).

`switch_stock` types a stock code into the client's main window so it subscribes to
that stock's tick feed. Uses AttachThreadInput so SetForegroundWindow works reliably
even when our process is in the background. It briefly takes foreground focus.
"""
import ctypes
import time
from ctypes import wintypes as W

from .procinfo import main_window

_u = ctypes.WinDLL("user32")
_k = ctypes.WinDLL("kernel32")
_u.ShowWindow.argtypes = [W.HWND, ctypes.c_int]
_u.SetForegroundWindow.argtypes = [W.HWND]
_u.GetForegroundWindow.restype = W.HWND
_u.GetWindowThreadProcessId.argtypes = [W.HWND, ctypes.POINTER(W.DWORD)]
_u.AttachThreadInput.argtypes = [W.DWORD, W.DWORD, W.BOOL]
_u.SetFocus.argtypes = [W.HWND]
_u.BringWindowToTop.argtypes = [W.HWND]
_k.GetCurrentThreadId.restype = W.DWORD

_VK = {c: 0x30 + i for i, c in enumerate("0123456789")}
_VK["\r"] = 0x0D


def _focus(hwnd):
    fg = _u.GetForegroundWindow()
    pid = W.DWORD()
    fg_thread = _u.GetWindowThreadProcessId(fg, ctypes.byref(pid)) if fg else 0
    cur = _k.GetCurrentThreadId()
    attached = False
    if fg_thread and fg_thread != cur:
        attached = bool(_u.AttachThreadInput(cur, fg_thread, True))
    _u.ShowWindow(hwnd, 9)          # SW_RESTORE
    _u.BringWindowToTop(hwnd)
    _u.SetForegroundWindow(hwnd)
    _u.SetFocus(hwnd)
    if attached:
        _u.AttachThreadInput(cur, fg_thread, False)
    time.sleep(0.35)


def switch_stock(pid, code, settle=3.0, retries=3):
    """Type `code` + Enter into the client's main window and wait `settle` seconds.

    Retries a few times because focus/input can race when several instances are driven.
    """
    code = code.lower()
    code = code[2:] if code.startswith(("sh", "sz")) else code
    if not code.isdigit() or len(code) != 6:
        raise ValueError("需要 6 位股票代码")
    hwnd = main_window(pid)
    last_err = None
    for _ in range(max(1, retries)):
        try:
            _focus(hwnd)
            for ch in code + "\r":
                vk = _VK[ch]
                _u.keybd_event(vk, 0, 0, 0); time.sleep(0.03)
                _u.keybd_event(vk, 0, 2, 0); time.sleep(0.03)
            time.sleep(settle)
            return hwnd
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1)
    if last_err:
        raise last_err
    return hwnd
