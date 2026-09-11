"""逐笔委托 (order-by-order) for ANY stock, programmatically.

Verified path (2026-09-11):
  1. The client's "逐笔委托明细" view must be open ONCE (it follows the active stock).
  2. `fetch_orders(code=...)` types the code into the client (no manual click), waits for
     the client to subscribe, and reads the 委托 display buffer -> clean records.

Each record:
  {channel:'order', code, time, time_raw, price, shares, event:'order'|'cancel',
   side:'B'|'S', order_number}

Limitations / alternatives:
  * The 委托 view must be open (conversely, when open, switching stocks is automatic).
  * `orders_wire.fetch_orders` is the no-view path (inject 0x055e over the live socket);
    it is proven to return the data (zlib) but the delta stream is not yet field-decoded.
"""
from typing import List, Optional

from . import live

# A stock switch + settle + a short read window.
DEFAULT_SECONDS = 4.0


def fetch_orders(pid=None, code=None, seconds=DEFAULT_SECONDS, from_now=False,
                 on_event=None) -> List[dict]:
    """Switch the client to `code` and return its 逐笔委托 records.

    from_now=False  -> the whole 委托 buffer the client holds for that stock
    from_now=True   -> only newly arriving orders (for streaming)
    """
    return live.snapshot(pid=pid, code=code, seconds=seconds, channel="order",
                         from_now=from_now, on_event=on_event)
