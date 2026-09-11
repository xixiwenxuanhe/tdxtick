"""Realtime 逐笔 (trade/cancel/order) from the client's memory buffers.

Threaded callbacks, no manual clicking (optionally auto-switches the client to `code`).
"""
import json
import pathlib
import struct
import threading
import time

import frida

from .procinfo import find_process, verify_build
from .version import TIME_OFFSET_SECONDS
from .window import switch_stock

_JS_PATH = pathlib.Path(__file__).resolve().parent / "js" / "live.js"

TRADE = struct.Struct("<HIIbBII")     # sec, price*1e4, lots, odd, dir, bid, ask
ORDER = struct.Struct("<HIIbcccHI")   # sec, price*1e4, lots, odd, typ, act, flags, aux, num


def clock(sec):
    sec = (sec + TIME_OFFSET_SECONDS) % 86400
    return f"{sec//3600:02}:{sec//60%60:02}:{sec%60:02}"


def decode(channel, raw, code):
    """Decode a raw batch of 20-byte records into dicts."""
    st = ORDER if channel == "order" else TRADE
    out = []
    for i in range(0, len(raw) - len(raw) % 20, 20):
        f = st.unpack_from(raw, i)
        if channel == "order":
            sec, price, lots, odd, typ, act, flags, aux, num = f
            typ = typ.decode("ascii", "replace"); act = act.decode("ascii", "replace")
            out.append(dict(channel="order", code=code, time=clock(sec), time_raw=sec,
                            price=price / 10000, shares=lots * 100 + odd,
                            event="cancel" if act == "C" else "order",
                            side=typ if act == "C" else act, order_number=num))
        else:
            sec, price, lots, odd, direction, bid, ask = f
            out.append(dict(channel="trade", code=code, time=clock(sec), time_raw=sec,
                            price=price / 10000, shares=lots * 100 + odd,
                            direction_raw=direction, bid_order_number=bid, ask_order_number=ask))
    return out


class LiveReader:
    """Attach once and receive tick records for the client's current (or switched) stock.

    on_record: callable(dict)   (called on the frida message thread)
    on_event:  callable(dict)   (attach/head_shift/reset/err/ready)
    """

    def __init__(self, pid=None, code=None, on_record=None, on_event=None, from_now=True):
        self.pid = find_process(pid)
        verify_build(self.pid)
        self.code = code
        self.on_record = on_record or (lambda r: None)
        self.on_event = on_event or (lambda e: None)
        self.from_now = from_now
        self._session = None
        self._script = None
        self._stop = threading.Event()

    def start(self):
        if self.code:
            switch_stock(self.pid, self.code, settle=3.0)
        js = _JS_PATH.read_text(encoding="utf-8").replace("%NOW_ONLY%", "true" if self.from_now else "false")
        self._session = frida.attach(self.pid)
        self._script = self._session.create_script(js)
        self._script.on("message", self._on_message)
        self._script.load()
        return self

    def _on_message(self, message, data):
        p = message.get("payload", message)
        kind = p.get("kind")
        if kind == "batch" and data:
            want = self.code[2:] if self.code and self.code.lower().startswith(("sh", "sz")) else self.code
            if want and p["code"] != want:
                return
            for rec in decode(p["channel"], data, p["code"]):
                self.on_record(rec)
        else:
            self.on_event(p)

    def run(self, seconds=None):
        """Block; if seconds is None, run until stop()/Ctrl-C."""
        if seconds is None:
            while not self._stop.wait(1):
                pass
        else:
            time.sleep(seconds)
        return self

    def stop(self):
        self._stop.set()
        s = self._session
        self._session = None
        if s:
            # detach() can block on a busy target; do it in the background
            t = threading.Thread(target=lambda: self._safe_detach(s), daemon=True)
            t.start()

    @staticmethod
    def _safe_detach(session):
        try:
            session.detach()
        except Exception:
            pass


def snapshot(pid, code, seconds=5.0, channel="trade", from_now=True, on_event=None):
    """Convenience: switch to `code`, collect records for `seconds`, return a list."""
    out = []
    reader = LiveReader(pid=pid, code=code, on_record=out.append, on_event=on_event, from_now=from_now)
    reader.start()
    try:
        time.sleep(seconds)
    finally:
        reader.stop()
    return [r for r in out if channel in (None, "all", r["channel"])] if channel else out
