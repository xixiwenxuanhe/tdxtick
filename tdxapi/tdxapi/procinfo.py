"""Process / window / build checks for the running TDX client."""
import ctypes
import hashlib
import pathlib
from ctypes import wintypes as W

import frida

from .version import BUILD_SHA256


def find_process(pid=None, exe=None):
    """Return the TdxW.exe pid: matching `pid`, else `exe` path, else the single one."""
    candidates = [p for p in frida.get_local_device().enumerate_processes()
                  if p.name.lower() == "tdxw.exe" and (pid is None or p.pid == pid)]
    if not candidates:
        raise RuntimeError("没有找到通达信(TdxW.exe)，请先启动并登录。")
    if pid is None and exe is not None and len(candidates) > 1:
        want = str(pathlib.Path(exe).resolve()).lower()
        matched = []
        for c in candidates:
            try:
                if str(executable_path(c.pid).resolve()).lower() == want:
                    matched.append(c)
            except Exception:
                pass
        if matched:
            candidates = matched
    if pid is None and len(candidates) > 1:
        raise RuntimeError(f"检测到 {len(candidates)} 个通达信实例，请在 .env 填 TDX_PATH 或 --pid 指定。"
                           f" pid={[c.pid for c in candidates]}")
    return candidates[0].pid


def executable_path(pid):
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
    k.OpenProcess.restype = W.HANDLE
    k.QueryFullProcessImageNameW.argtypes = [W.HANDLE, W.DWORD, W.LPWSTR, ctypes.POINTER(W.DWORD)]
    k.CloseHandle.argtypes = [W.HANDLE]
    h = k.OpenProcess(0x1000, False, pid)
    if not h:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        b = ctypes.create_unicode_buffer(32768)
        n = W.DWORD(len(b))
        if not k.QueryFullProcessImageNameW(h, 0, b, ctypes.byref(n)):
            raise ctypes.WinError(ctypes.get_last_error())
        return pathlib.Path(b.value)
    finally:
        k.CloseHandle(h)


def verify_build(pid):
    """Return (exe_path, sha256) and refuse to continue on an unknown build."""
    exe = executable_path(pid)
    digest = hashlib.sha256(exe.read_bytes()).hexdigest()
    if digest != BUILD_SHA256:
        raise RuntimeError(
            "通达信版本与已验证版本不一致，为避免读到错误数据已停止。"
            f"\n  expected {BUILD_SHA256}\n  actual   {digest}\n"
            "需要重新适配 offsets 后再使用。")
    return exe, digest


def main_window(pid):
    """Largest visible top-level window of the process (the MDI frame)."""
    u = ctypes.WinDLL("user32")
    u.GetWindowThreadProcessId.argtypes = [W.HWND, ctypes.POINTER(W.DWORD)]
    u.GetWindowRect.argtypes = [W.HWND, ctypes.POINTER(W.RECT)]
    u.IsWindowVisible.argtypes = [W.HWND]
    windows = []

    @ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    def callback(h, l):
        p = W.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u.IsWindowVisible(h):
            r = W.RECT()
            u.GetWindowRect(h, ctypes.byref(r))
            windows.append(((r.right - r.left) * (r.bottom - r.top), int(h)))
        return True

    u.EnumWindows(callback, 0)
    if not windows:
        raise RuntimeError("找不到通达信主窗口；请先完成登录。")
    return max(windows)[1]
