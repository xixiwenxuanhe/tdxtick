"""Concurrent realtime for several stocks, one TDX instance per stock.

Because the client keeps tick data for a single "current stock" at a time, the way to
watch N stocks simultaneously without decoding the wire protocol is to run N independent
TDX instances (separate install folders), pin each to one stock, and merge their readers.

Each instance is a full copy of the install (~850 MB) and needs its own login.
"""
import ctypes
import pathlib
import subprocess
import time
from ctypes import wintypes as W
from typing import Callable, Dict, List, Optional

from . import live, procinfo
from .window import switch_stock

DEFAULT_SOURCE = pathlib.Path(r"D:\Install\tdx")
DEFAULT_BASE = pathlib.Path(r"D:\Install")
INSTANCE_PREFIX = "tdx-lab"


def _list_tdxw():
    """Return [(pid, path)] for every running TdxW.exe, via PowerShell."""
    ps = (r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    try:
        out = subprocess.run([ps, "-NoProfile", "-Command",
                              "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
                              "Get-Process TdxW -ErrorAction SilentlyContinue | "
                              "ForEach-Object { \"$($_.Id)|$($_.Path)\" }"],
                             capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return []
    res = []
    for line in out.splitlines():
        line = line.strip()
        if "|" in line:
            pid, path = line.split("|", 1)
            try:
                res.append((int(pid), pathlib.Path(path)))
            except ValueError:
                pass
    return res


def instance_dir(index: int, base: pathlib.Path = DEFAULT_BASE) -> pathlib.Path:
    return base / (INSTANCE_PREFIX if index == 1 else f"{INSTANCE_PREFIX}{index}")


def ensure_instances(n: int, source: pathlib.Path = DEFAULT_SOURCE,
                     base: pathlib.Path = DEFAULT_BASE, progress=print) -> List[pathlib.Path]:
    """Make sure `n` instance folders exist (index 1..n), copying the source as needed."""
    dirs = []
    for i in range(1, n + 1):
        d = instance_dir(i, base)
        if (d / "TdxW.exe").is_file():
            dirs.append(d)
            continue
        progress(f"[fleet] 复制 {source} -> {d} (约 850MB，请稍候)…")
        subprocess.run(["robocopy", str(source), str(d), "/E", "/MT:16", "/NFL", "/NDL",
                        "/NJH", "/NJS", "/NP", "/R:1", "/W:1"], check=False)
        if not (d / "TdxW.exe").is_file():
            raise RuntimeError(f"复制失败：{d}")
        dirs.append(d)
    return dirs


def wait_main_window(pid: int, timeout: float = 150, progress=print) -> int:
    """Wait until the instance has a visible main window (i.e. logged in). Returns hwnd."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            return procinfo.main_window(pid)
        except Exception:
            time.sleep(3)
    raise TimeoutError(f"实例 {pid} 超时仍未登录出主窗口")


def launch(path: pathlib.Path):
    subprocess.Popen([str(path / "TdxW.exe")], cwd=str(path))


def wait_instance(path: pathlib.Path, timeout: float = 90) -> int:
    """Wait until the TdxW.exe running from `path` appears; return its pid."""
    want = str(path.resolve()).lower()
    deadline = time.time() + timeout
    while time.time() < deadline:
        for pid, exe in _list_tdxw():
            try:
                if str(exe.parent.resolve()).lower() == str(path.resolve()).lower():
                    return pid
            except Exception:
                pass
        time.sleep(2)
    raise TimeoutError(f"实例未启动：{path}")


class Fleet:
    """One instance per code. `on_record(record)` receives merged live records."""

    def __init__(self, codes: List[str], on_record: Optional[Callable] = None,
                 on_event: Optional[Callable] = None, source: pathlib.Path = DEFAULT_SOURCE,
                 base: pathlib.Path = DEFAULT_BASE, reuse_existing: bool = True, progress=print):
        self.codes = [c.lower().replace("sh", "").replace("sz", "") if c.lower().startswith(("sh", "sz")) else c for c in codes]
        self.on_record = on_record or (lambda r: None)
        self.on_event = on_event or (lambda e: None)
        self.source = source
        self.base = base
        self.reuse = reuse_existing
        self.progress = progress
        self._readers: Dict[str, live.LiveReader] = {}
        self.instances: List[dict] = []
        self._attached = set()

    def bring_up(self):
        dirs = ensure_instances(len(self.codes), self.source, self.base, self.progress)
        existing = _list_tdxw()
        for code, d in zip(self.codes, dirs):
            pid = None
            if self.reuse:
                for p, exe in existing:
                    try:
                        if str(exe.parent.resolve()).lower() == str(d.resolve()).lower():
                            pid = p; break
                    except Exception:
                        pass
            if pid is None:
                self.progress(f"[fleet] 启动 {d.name} -> {code}")
                launch(d)
                pid = wait_instance(d)
            self.progress(f"[fleet] {d.name} pid={pid} 等待登录…")
            wait_main_window(pid, progress=self.progress)
            self.progress(f"[fleet] {d.name} pid={pid} 钉到 {code}")
            switch_stock(pid, code, settle=4.0)
            self.instances.append(dict(code=code, pid=pid, path=d))
        return self

    def _event(self, e):
        if e.get("kind") == "attach":
            self._attached.add(e.get("code"))
        self.on_event(e)

    def stream(self, seconds: Optional[float] = None):
        for inst in self.instances:
            r = live.LiveReader(pid=inst["pid"], code=None, on_record=self.on_record, on_event=self._event)
            r.start()
            self._readers[inst["code"]] = r
        # 预热：确认每个实例都真的订阅上了；没上的重切一次
        deadline = time.time() + 10
        while time.time() < deadline and len(self._attached) < len(self.instances):
            time.sleep(1)
        for inst in self.instances:
            if inst["code"] not in self._attached:
                self.progress(f"[fleet] {inst['path'].name} 未订阅 {inst['code']}，重切一次")
                try:
                    switch_stock(inst["pid"], inst["code"], settle=4.0)
                except Exception as e:  # noqa: BLE001
                    self.progress(f"[fleet] 重切失败：{e}")
        time.sleep(2)
        try:
            if seconds is None:
                while True:
                    time.sleep(1)
            else:
                time.sleep(seconds)
        finally:
            self.stop()
        return self

    def stop(self):
        for r in self._readers.values():
            try:
                r.stop()
            except Exception:
                pass
        self._readers.clear()
