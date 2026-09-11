"""Local HTTP API for TDX 逐笔 data (stock+date history, realtime trade/order).

Run:
    python -m tdxapi.server --pid <TDX_PID> --host 127.0.0.1 --port 8712

Endpoints:
    GET /health
    GET /v1/history/orders?code=002971&date=20260910        # tck, ms-level, order+cancel
    GET /v1/history/trades?code=002971&date=20260910        # tck, ms-level, trades
    GET /v1/live?code=000001&channel=trade|order&seconds=4  # realtime snapshot (JSON)
    GET /v1/stream?code=000001&channel=trade|order          # SSE, continuous

Notes:
    * The client holds tick data for ONE stock at a time. This service serialises stock
      switches (a lock). For concurrent multi-stock use several instances (`fleet.py`)
      or the experimental wire path (`orders_wire.py`).
    * `channel=order` needs the client's "逐笔委托明细" view open once.
"""
import argparse
import concurrent.futures
import contextlib
import json
import os
import pathlib
import subprocess
import threading
import time

from flask import Flask, Response, jsonify, request

from . import config, history, live, orders, procinfo

app = Flask(__name__)
_state = {"pid": None, "lock": threading.Lock(), "current": None, "token": None}

#: 等锁上限（秒）—— 超过即快速 503，不无限排队。
LOCK_WAIT = float(os.environ.get("TDXAPI_LOCK_WAIT") or 15)
#: history 请求硬上限（秒）。
HISTORY_DEADLINE = float(os.environ.get("TDXAPI_HISTORY_DEADLINE") or 180)
#: live 在 `seconds` 之外的额外宽限（秒）。
LIVE_GRACE = float(os.environ.get("TDXAPI_LIVE_GRACE") or 30)
#: SSE 连续失败多少次后结束流（避免对着坏掉的客户端空转）。
STREAM_MAX_ERRORS = int(os.environ.get("TDXAPI_STREAM_MAX_ERRORS") or 5)

_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="tdxapi")


class Busy(Exception):
    """另一个请求正占着客户端——快速失败，而不是排队等死。"""
    code, name = 503, "busy"


class Deadline(Exception):
    """上游（FRIDA / 客户端 / .tck 下载器）超时。"""
    code, name = 504, "timeout"


def _pid():
    return _state["pid"]


def _coverage(code):
    """把市场级的「委托流覆盖」标注带给调用方——沪市照深市经验写代码会静默算错。"""
    try:
        m = history.market_of(code)
    except ValueError:
        return {}
    return {"market": m,
            "coverage": history.COVERAGE.get(m, "unknown"),
            "quantity_semantics": history.QUANTITY_SEMANTICS.get(m, "unknown")}


def _bounded(fn, deadline, what):
    """跑 `fn` 并施加硬上限；超时抛 Deadline。"""
    fut = _pool.submit(fn)
    try:
        return fut.result(timeout=deadline)
    except concurrent.futures.TimeoutError:
        raise Deadline(f"{what} 超过 {deadline:g}s 未返回") from None


@contextlib.contextmanager
def _serialized(pid, code=None):
    """序列化"驱动客户端"的工作；拿不到锁就立刻 503。

    客户端同一时刻只能服务一只股（切股会替换缓冲），所以必须串行；
    但**不能无限等** —— 曾经因为一个卡死的请求把后面全部拖死。
    """
    if not _state["lock"].acquire(timeout=LOCK_WAIT):
        raise Busy(f"另一个请求正在使用客户端（等待 {LOCK_WAIT:g}s 未获得锁）")
    try:
        if code is not None and _state["current"] != code:
            from . import window
            window.switch_stock(pid, code, settle=3.0)
            _state["current"] = code
        yield
    finally:
        _state["lock"].release()


def _run_serialized(pid, code, fn, deadline, what):
    """在串行区里跑 `fn`，并施加硬上限。"""
    def job():
        with _serialized(pid, code):
            return fn()
    return _bounded(job, deadline, what)


@app.before_request
def _require_token():
    """Bearer-token gate; /health is open for liveness checks."""
    if request.path == "/health" or request.method == "OPTIONS":
        return None
    token = _state.get("token")
    if not token:
        return None
    if request.headers.get("Authorization", "") != f"Bearer {token}":
        return jsonify(error="unauthorized"), 401
    return None


@app.errorhandler(Exception)
def _json_error(e):
    """Never return HTML error pages; callers need structured JSON."""
    import werkzeug.exceptions as wexc
    if isinstance(e, (Busy, Deadline)):
        return jsonify(error=e.name, detail=str(e)), e.code
    code = e.code if isinstance(e, wexc.HTTPException) else 400
    name = "bad_request"
    if isinstance(e, TimeoutError):
        code, name = 504, "timeout"
    elif isinstance(e, KeyError):
        name = "missing_param"
    elif isinstance(e, (ValueError, TypeError)):
        name = "invalid_param"
    elif isinstance(e, RuntimeError):
        name = "runtime_error"
    elif isinstance(e, wexc.NotFound):
        name = "not_found"
    return jsonify(error=name, detail=str(e)), code


@app.get("/health")
def health():
    try:
        p = procinfo.find_process(_pid())
        exe, digest = procinfo.verify_build(p)
        return jsonify(ok=True, pid=p, exe=str(exe), sha256=digest, current=_state["current"])
    except Exception as e:  # noqa: BLE001
        return jsonify(ok=False, error=str(e)), 503


@app.get("/v1/history/orders")
def history_orders():
    code, date = request.args["code"], request.args["date"].replace("-", "")
    pid = _pid()
    res = _run_serialized(pid, None,
                          lambda: history.fetch(code, date, pid=pid, progress=lambda *_: None),
                          HISTORY_DEADLINE, f"history {code}/{date}")
    return jsonify(code=res["summary"]["code"], date=res["summary"]["date"],
                   count=len(res["orders"]), records=res["orders"], summary=res["summary"])


@app.get("/v1/history/trades")
def history_trades():
    code, date = request.args["code"], request.args["date"].replace("-", "")
    pid = _pid()
    res = _run_serialized(pid, None,
                          lambda: history.fetch(code, date, pid=pid, progress=lambda *_: None),
                          HISTORY_DEADLINE, f"history {code}/{date}")
    return jsonify(code=res["summary"]["code"], date=res["summary"]["date"],
                   count=len(res["trades"]), records=res["trades"], summary=res["summary"])


@app.get("/v1/live")
def v1_live():
    code = request.args["code"]
    channel = request.args.get("channel", "trade")
    seconds = float(request.args.get("seconds", 4))
    from_now = request.args.get("from_now", "0") in ("1", "true", "yes")
    pid = _pid()
    recs = _run_serialized(
        pid, code,
        lambda: live.snapshot(pid=pid, code=None, seconds=seconds, channel=channel, from_now=from_now),
        seconds + LIVE_GRACE, f"live {code}/{channel}")
    return jsonify(**_coverage(code), code=code, channel=channel, count=len(recs), records=recs)


@app.get("/v1/stream")
def v1_stream():
    code = request.args["code"]
    channel = request.args.get("channel", "trade")
    interval = float(request.args.get("interval", 1.0))
    pid = _pid()
    with _serialized(pid, code):   # 只在这一刻切股，不长期占锁
        pass
    tail = f"{code}/{channel}"

    def gen():
        yield f": stream {code} {channel}\n\n"
        errors = 0
        while True:
            try:
                recs = _bounded(
                    lambda: live.snapshot(pid=pid, code=None, seconds=interval,
                                          channel=channel, from_now=True),
                    interval + LIVE_GRACE, f"live {tail}")
                errors = 0
            except Exception as e:  # noqa: BLE001
                errors += 1
                yield (f"event: error\ndata: "
                       f"{json.dumps({'error': type(e).__name__, 'detail': str(e)})}\n\n")
                if errors >= STREAM_MAX_ERRORS:
                    yield (f"event: stop\ndata: "
                           f"{json.dumps({'reason': 'too_many_errors'})}\n\n")
                    return
                time.sleep(interval)
                continue
            for r in recs:
                yield f"data: {json.dumps(r, ensure_ascii=False)}\n\n"
            if not recs:
                yield ": keepalive\n\n"
    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _load_or_create_token():
    """Token from .env/env; otherwise auto-generate and persist to <repo>/.tdxtoken."""
    tok = config.get("TDXAPI_TOKEN")
    if tok:
        return tok
    f = pathlib.Path(__file__).resolve().parents[2] / ".tdxtoken"
    try:
        if f.is_file():
            tok = f.read_text(encoding="utf-8").strip()
            if tok:
                return tok
    except Exception:
        pass
    import secrets
    tok = "tdx_" + secrets.token_hex(16)
    try:
        f.write_text(tok, encoding="utf-8")
    except Exception:
        pass
    return tok


def _tailscale_ip():
    for exe in (r"C:\Program Files\Tailscale\tailscale.exe", "tailscale"):
        try:
            out = subprocess.run([exe, "ip", "-4"], capture_output=True, text=True, timeout=10).stdout
            ip = out.strip().splitlines()[0].strip() if out.strip() else ""
            if ip.startswith("100."):
                return ip
        except Exception:
            pass
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tdxapi.server")
    config.load_env()
    ap.add_argument("--pid", type=int, default=(int(config.get("TDX_PID")) if config.get("TDX_PID") else None))
    ap.add_argument("--host", default=config.get("TDXAPI_HOST"), help="默认：Tailscale IP，取不到则 127.0.0.1")
    ap.add_argument("--port", type=int, default=int(config.get("TDXAPI_PORT", 8712)))
    ap.add_argument("--token", default=config.get("TDXAPI_TOKEN"), help="Bearer Token（默认自动生成并保存到 .tdxtoken）")
    a = ap.parse_args(argv)
    _state["token"] = a.token or _load_or_create_token()
    if not a.host:
        a.host = _tailscale_ip() or "127.0.0.1"
    if not a.token:
        config.load_env()
    _state["pid"] = procinfo.find_process(a.pid, exe=config.tdx_exe())
    procinfo.verify_build(_state["pid"])
    print(f"tdxapi serving on http://{a.host}:{a.port}  (TDX pid {_state['pid']})", flush=True)
    print(f"  auth: {'Bearer ' + _state['token'][:8] + '...' if _state.get('token') else 'DISABLED'}", flush=True)
    app.run(host=a.host, port=a.port, threaded=True)


if __name__ == "__main__":
    main()
