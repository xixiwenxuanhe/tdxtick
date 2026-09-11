"""Wire-level 逐笔委托 (order-by-order) fetch for ANY stock, without touching the UI.

Protocol (verified 2026-09-11):
  request  0x055e  header 0c 03 08 02 0a 01 10 00 10 00 5e 05 | 01 00 "code"(6) seq(u32 LE) dc 05
  response 0x055e  payload = zlib (78 9c)  ->  a delta-encoded order stream
           (small tails may be un-compressed incremental records)

The request is injected on the client's already-established HQ socket via WSASend,
so the stock code is ours to choose (verified: client showing 603105 returned 000001).

NOTE: the decompressed delta stream is not yet fully field-decoded; `fetch_raw`
returns the decompressed bytes. The client decodes the same bytes into its 委托
display buffer, which `live.LiveReader(channel='order')` can read when that view is open.
"""
import pathlib
import struct
import time
import zlib

import frida

from .procinfo import find_process, verify_build

_JS = (pathlib.Path(__file__).resolve().parent / "js" / "orders_wire.js").read_text(encoding="utf-8")

CMD_POLL = 0x0555   # 委托 poll/heartbeat
CMD_DATA = 0x055E   # 委托 data


def build_request(code, seq=0, count=1500):
    code = code.lower()
    code = code[2:] if code.startswith(("sh", "sz")) else code
    if not (code.isdigit() and len(code) == 6):
        raise ValueError("需要 6 位股票代码")
    head = bytes.fromhex("0c0308020a0110001000") + struct.pack("<H", CMD_DATA)
    payload = b"\x01\x00" + code.encode() + struct.pack("<I", seq & 0xFFFFFFFF) + struct.pack("<H", count)
    return (head + payload).hex()


def fetch_raw(pid=None, code=None, seq=0, seconds=6.0, progress=print):
    """Inject a 0x055e request for `code` and collect the responses.

    Returns dict(code, seq, responses=[bytes], decompressed=[bytes], zlib_chunks=n).
    """
    pid = find_process(pid)
    verify_build(pid)
    session = frida.attach(pid)
    script = session.create_script(_JS)
    responses = []
    script.on("message", lambda m, d: responses.append(bytes(d)) if (m.get("payload", m).get("kind") == "resp55e" and d) else None)
    script.load()
    time.sleep(2.0)  # wait for the socket capture
    rc = script.exports_sync.inject(build_request(code, seq))
    if rc != 0:
        session.detach()
        raise RuntimeError(f"WSASend 注入失败 (rc={rc})；可能未捕获到行情 socket")
    time.sleep(seconds)
    session.detach()
    decompressed = []
    zc = 0
    for r in responses:
        if r[:2] in (b"\x78\x9c", b"\x78\x01", b"\x78\xda"):
            try:
                decompressed.append(zlib.decompress(r)); zc += 1; continue
            except zlib.error:
                pass
        decompressed.append(r)
    return dict(code=code, seq=seq, responses=responses, decompressed=decompressed, zlib_chunks=zc)


def fetch_orders(pid=None, code=None, seq=0, seconds=6.0, decode=None, progress=print):
    """Fetch 委托 for `code`.

    decode: optional callable(blob)->list[dict] to parse the decompressed stream
    (not provided by default because the delta stream format is still being finalised).
    Returns dict(code, seq, total_bytes, chunks=[bytes], records=<decode output or None>).
    """
    res = fetch_raw(pid=pid, code=code, seq=seq, seconds=seconds, progress=progress)
    blob = b"".join(res["decompressed"])
    out = dict(code=code, seq=seq, total_bytes=len(blob), chunks=res["decompressed"],
               zlib_chunks=res["zlib_chunks"], records=None)
    if decode is not None:
        out["records"] = decode(blob)
    return out


if __name__ == "__main__":
    import sys
    r = fetch_orders(pid=int(sys.argv[1]) if len(sys.argv) > 1 else None,
                     code=sys.argv[2] if len(sys.argv) > 2 else "000001")
    print(f"code={r['code']} bytes={r['total_bytes']} chunks={len(r['chunks'])} zlib={r['zlib_chunks']}")
