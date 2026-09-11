"""tdxapi — programmatic access to a running 通达信 client.

Two data planes:
  * history  : any stock + any date, millisecond, order-level (via the client's .tck replay)
  * live     : realtime 逐笔 from the client's memory buffers (optionally auto-switching stock)

Public API:
    from tdxapi import history, live
    res = history.fetch("002971", "20260910", out_dir="...")
    recs = live.snapshot(pid=None, code="002971", seconds=5)

CLI:
    python -m tdxapi.cli history 002971 20260910 --out out/
    python -m tdxapi.cli live 002971 --seconds 10
"""
from . import config, fleet, history, live, orders, orders_wire, procinfo, version, window  # noqa: F401

__all__ = ["history", "live", "orders", "orders_wire", "fleet", "procinfo", "version", "window"]
__version__ = "0.1.0"
