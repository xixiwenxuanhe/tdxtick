"""Historical 逐笔 (order/cancel/trade) for any stock+date, via TDX's own .tck replay loader.

Requires the client running and logged in. Today's data is only available after ~15:01.
"""
import collections
import csv
import datetime as dt
import hashlib
import json
import math
import os
import pathlib
import struct
import threading
import time
import uuid
import zlib

import frida

from .config import tdx_exe
from .procinfo import find_process, main_window, verify_build
from .version import (HISTORY_LOADER_RVA, SESSION_END, SESSION_START)

# --- container / record format -------------------------------------------------
RECORD = struct.Struct("<HIdIIIccII")   # 36-byte replay record
TCK_HEADER = struct.Struct("<QQQ")

_DOWNLOAD_JS = r"""
const main = Process.getModuleByName('TdxW.exe');
const request = new NativeFunction(main.base.add(%LOADER_RVA%),'pointer',
                                   ['uint8','pointer','int','pointer']);
const crt = Process.getModuleByName('MSVCR100.dll');
const fclose = new NativeFunction(crt.getExportByName('fclose'),'int',['pointer']);
const user = Process.getModuleByName('USER32.dll');
const post = new NativeFunction(user.getExportByName('PostMessageW'),'bool',
                                ['pointer','uint','pointer','pointer']);
let pending = null, active = false;
for (const n of ['DispatchMessageW','DispatchMessageA']) {
  Interceptor.attach(user.getExportByName(n), { onEnter(a) {
    if (!pending || a[0].readPointer().toString() !== pending.hwnd ||
        a[0].add(8).readU32() !== 0x83f1 ||
        a[0].add(16).readU64().toString() !== '5522517') return;
    const q = pending; pending = null; active = true;
    send({kind:'executing'});
    try {
      const code = Memory.allocUtf8String(q.code), ext = Memory.allocUtf8String('tck');
      const file = request(q.market, code, q.date, ext);
      const ok = !file.isNull();
      if (ok) fclose(file);
      active = false; send({kind:'done', ok});
    } catch (e) { active = false; send({kind:'failed', error:String(e)}); }
  }});
}
rpc.exports = {
  queue(q) {
    if (pending || active) throw new Error('Download already active');
    pending = q;
    if (!post(ptr(q.hwnd), 0x83f1, ptr(5522517), ptr(0))) { pending = null; return false; }
    return true;
  },
  cancelPending() { if (active) return false; pending = null; return true; },
  reset() { pending = null; active = false; return true; }
};
"""

#: 整次下载的硬超时（秒）。超过即放弃并抛 TimeoutError，**不再无限等**。
#: 之前 finally 里的 `terminal.wait()` 无超时 —— 客户端一旦不回调就永久挂住，
#: 同时占着文件锁和服务端全局锁，把后续所有请求拖死。
DOWNLOAD_TIMEOUT = float(os.environ.get("TDXAPI_HISTORY_TIMEOUT") or 150)
#: 把请求送进主线程后，多久没开始执行就判定主线程无响应。
START_GRACE = float(os.environ.get("TDXAPI_HISTORY_START_GRACE") or 30)
#: 收尾时等待/分离的宽限（秒），必须有界。
DETACH_GRACE = float(os.environ.get("TDXAPI_HISTORY_DETACH_GRACE") or 10)


def _cancel_pending(script):
    """尽量清掉注入脚本里"下载中"的状态，失败不影响调用方。"""
    if not script:
        return
    try:
        script.exports_sync.cancel_pending()
        script.exports_sync.reset()
    except Exception:
        pass


def _safe_detach(session):
    try:
        session.detach()
    except Exception:
        pass


#: 各市场「委托流覆盖」级别。
#: 沪市：上交所只发布"进入订单簿"的委托（"立即全部成交"的主动委托不发布）→ 只含挂单（被动方）；
#: 深市：逐笔委托（UA201）发布全部委托。详见 docs/sh-vs-sz-tick-fields.md。
COVERAGE = {1: "resting_only", 0: "full"}
#: 委托记录 `quantity_shares` 的语义。
#: 沪市：对"主动成交后又挂单"的委托，该字段是**成交后剩余量**，不是原始委托量；
#: 深市：就是原始委托量。⇒ 沪市 `原始量 = 记录量 + 该委托的即时成交量`。
QUANTITY_SEMANTICS = {1: "remaining_after_immediate_fill", 0: "original"}


def market_of(code):
    code = code.lower()
    if code.startswith("sh"):
        return 1
    if code.startswith("sz"):
        return 0
    if code.startswith("6"):
        return 1
    if code.startswith(("0", "3")):
        return 0
    raise ValueError("只支持沪深股票代码（6xxxxx->sh, 0/3xxxxx->sz）")


def _norm_code(code):
    code = code.lower()
    return code[2:] if code.startswith(("sh", "sz")) else code


# --- download via the client ---------------------------------------------------
def download(code, date, market, pid=None, progress=print):
    """Ask the client to fetch `date`'s .tck; return (cache_path, info). Cached per day."""
    code = _norm_code(code)
    pid = find_process(pid, exe=tdx_exe())
    exe, digest = verify_build(pid)
    hwnd = main_window(pid)
    cache = exe.parent / "T0002" / "zst_cache" / f"{'sh' if market == 1 else 'sz'}{code}_{date}.tck"

    import msvcrt  # Windows only
    lock = exe.parent / "T0002" / "codex_tck_download.lock"
    with lock.open("a+b") as guard:
        if guard.seek(0, 2) == 0:
            guard.write(b"0"); guard.flush()
        guard.seek(0)
        try:
            msvcrt.locking(guard.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise RuntimeError("另一个导出任务正在使用通达信，请稍后重试。")

        session = script = preclose_backup = None
        terminal = threading.Event(); started = threading.Event(); result = {}
        try:
            cn = dt.timezone(dt.timedelta(hours=8))
            close = dt.datetime.strptime(date, "%Y%m%d").replace(hour=15, minute=1, tzinfo=cn)
            if cache.exists() and cache.stat().st_mtime < close.timestamp():
                preclose_backup = cache.with_name(cache.name + ".preclose-" + uuid.uuid4().hex)
                cache.rename(preclose_backup)

            session = frida.attach(pid)

            def detached(reason, crash=None):
                if not terminal.is_set():
                    result.update(error=f"通达信连接已断开：{reason}"); terminal.set()
            session.on("detached", detached)

            def receive(message, data):
                if message.get("type") == "error":
                    result.update(error=message.get("description", str(message))); terminal.set(); return
                payload = message.get("payload", {})
                if payload.get("kind") == "executing":
                    started.set()
                elif payload.get("kind") in ("done", "failed"):
                    result.update(payload); terminal.set()

            script = session.create_script(_DOWNLOAD_JS.replace("%LOADER_RVA%", hex(HISTORY_LOADER_RVA)))
            script.on("message", receive); script.load()
            if not script.exports_sync.queue(dict(code=code, date=int(date), market=market, hwnd=hex(hwnd))):
                raise RuntimeError("无法把请求送入通达信主线程。")

            begun = time.monotonic()
            while True:
                # 按“距截止还剩多少”自适应轮询，保证截止时间在 ~0.2s 内被兑现
                left = DOWNLOAD_TIMEOUT - (time.monotonic() - begun)
                if terminal.wait(min(10.0, max(0.2, left))):
                    break
                elapsed = time.monotonic() - begun
                progress(f"通达信正在获取 {code}/{date}，已等待 {elapsed:.0f}s", flush=True)
                if not started.is_set() and elapsed >= START_GRACE:
                    _cancel_pending(script)
                    raise TimeoutError("通达信主线程没有响应；请检查是否登录或有弹窗。")
                if elapsed >= DOWNLOAD_TIMEOUT:
                    _cancel_pending(script)
                    raise TimeoutError(
                        f"通达信下载超时（>{elapsed:.0f}s）；客户端可能卡住，请稍后重试或重启客户端。")
            if result.get("error"):
                raise RuntimeError(result["error"])
            if not result.get("ok") or not cache.is_file() or cache.stat().st_size <= 24:
                raise RuntimeError(f"通达信未提供 {code}/{date} 的逐笔文件（非交易日/停牌/超范围/无权限）。")
            return cache, dict(pid=pid, exe=str(exe), exe_sha256=digest, loader_rva=hex(HISTORY_LOADER_RVA),
                               request_date=date, request_code=code, request_market=market,
                               preclose_cache_backup=str(preclose_backup) if preclose_backup else None)
        finally:
            # 先解锁：任何收尾步骤卡住都不应该把后续请求拖死。
            try:
                guard.seek(0); msvcrt.locking(guard.fileno(), msvcrt.LK_UNLCK, 1)
            except Exception:
                pass
            _cancel_pending(script)
            if session:
                # 分离操作也要有界——否则卡在这里同样会占住服务端锁。
                _t = threading.Thread(target=_safe_detach, args=(session,), daemon=True)
                _t.start(); _t.join(DETACH_GRACE)
            if preclose_backup and not result.get("ok") and not cache.exists():
                try:
                    preclose_backup.rename(cache)
                except Exception:
                    pass


# --- decode --------------------------------------------------------------------
def load_tck(path):
    blob = pathlib.Path(path).read_bytes()
    if len(blob) < 25:
        raise ValueError("TCK 为空或截断")
    tag, compressed, uncompressed = TCK_HEADER.unpack_from(blob, 0)
    if compressed != len(blob) - 24 or not 0 < uncompressed <= 2_000_000_000:
        raise ValueError("TCK 长度头非法")
    z = zlib.decompressobj()
    data = z.decompress(blob[24:], uncompressed + 1)
    if not z.eof or z.unused_data or z.unconsumed_tail or len(data) != uncompressed:
        raise ValueError("TCK 解压流长度不一致")
    if len(data) % RECORD.size:
        raise ValueError("36 字节记录被截断")
    return blob, data, dict(header_tag_raw=tag, compressed_bytes=compressed, uncompressed_bytes=uncompressed)


def time_string(t):
    ms = t % 1000; s = t // 1000 % 100; m = t // 100000 % 100; h = t // 10000000
    if not (0 <= h < 24 and 0 <= m < 60 and 0 <= s < 60):
        raise ValueError(f"非法 HHMMSSmmm: {t}")
    return f"{h:02}:{m:02}:{s:02}.{ms:03}"


def decode(data, code, date, market):
    """Yield normalised records from raw 36-byte replay data."""
    known = {}
    for i, values in enumerate(RECORD.iter_unpack(data)):
        flag, t, price, quantity, channel, sequence, typ, action, bid, ask = values
        typ = typ.decode("ascii"); action = action.decode("ascii")
        if not math.isfinite(price) or price < 0:
            raise ValueError(f"price 非法 @ {i}")
        order_no = 0; side = ""; order_price = None
        if flag == 0 and action in ("B", "S"):
            event = "order"; side = action
            order_no = (bid if side == "B" else ask) if market == 1 else sequence
            known[(channel, side, order_no)] = price
            order_price = price
        elif flag == 1 and action == "C":
            event = "cancel"
            side = "B" if bid else ("S" if ask else "")
            order_no = bid or ask
            order_price = known.get((channel, side, order_no))
        elif flag == 1 and action == "0":
            event = "trade"
        else:
            event = "other"
        yield dict(source_index=i, code=code, date=date, market=market,
                   time=time_string(t), time_raw=t, event=event, side=side,
                   price=float(price), price_raw=format(price, ".10g"),
                   order_price=None if order_price is None else float(order_price),
                   quantity_shares=quantity, channel=channel, sequence=sequence,
                   order_number=order_no or "", bid_order_number=bid or "",
                   ask_order_number=ask or "", order_type_raw=typ, action_raw=action,
                   record_type_raw=flag)


def _write_csv(path, rows, columns):
    with pathlib.Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns); w.writeheader(); w.writerows(rows)


def fetch(code, date, market=None, pid=None, out_dir=None, progress=print):
    """Download+decode. Returns dict(records, orders, trades, summary, tck_path).

    `date` is 'YYYYMMDD'. `out_dir=None` uses exports/<mkt><code>_<date>_<ts>/.
    """
    code = _norm_code(code)
    if market is None:
        market = market_of(code)
    cache, info = download(code, date, market, pid=pid, progress=progress)
    blob, data, header = load_tck(cache)
    rows = list(decode(data, code, date, market))
    if not rows:
        raise ValueError("没有回放记录")
    session = [r for r in rows if SESSION_START <= r["time_raw"] <= SESSION_END]
    orders = [r for r in session if r["event"] in ("order", "cancel")]
    trades = [r for r in session if r["event"] == "trade"]
    if not orders:
        raise ValueError("09:15-15:00 没有委托/撤单记录")
    summary = dict(code=code, date=date, market=market, **header,
                   coverage=COVERAGE.get(market, "unknown"),
                   quantity_semantics=QUANTITY_SEMANTICS.get(market, "unknown"),
                   tck_sha256=hashlib.sha256(blob).hexdigest(),
                   raw_sha256=hashlib.sha256(data).hexdigest(),
                   total_source_records=len(rows), session_records=len(session),
                   orders_and_cancels=len(orders), trades=len(trades),
                   events=dict(collections.Counter(r["event"] for r in session)),
                   first_order_time=orders[0]["time"], last_order_time=orders[-1]["time"],
                   nonmonotonic_time=sum(a["time_raw"] > b["time_raw"] for a, b in zip(rows, rows[1:])),
                   unmatched_cancels=sum(1 for r in orders if r["event"] == "cancel" and r["order_price"] is None),
                   source="live TDX V7.73 .tck replay (millisecond, order-level)")
    if out_dir is not None:
        out_dir = pathlib.Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
        columns = list(rows[0])
        (out_dir / "source.tck").write_bytes(blob)
        _write_csv(out_dir / "all_records.csv", rows, columns)
        _write_csv(out_dir / "orders.csv", orders, columns)
        _write_csv(out_dir / "trades.csv", trades, columns)
        (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        summary["output"] = str(out_dir)
    return dict(records=rows, orders=orders, trades=trades, summary=summary, tck_path=str(cache))
