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


def _pid():
    return _state["pid"]


def _ensure(pid, code):
    """Switch the client to `code` if needed (serialised)."""
    with _state["lock"]:
        if _state["current"] != code:
            from . import window
            window.switch_stock(pid, code, settle=3.0)
            _state["current"] = code


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
    code, date = request.args["code"], request.args["date"]
    pid = _pid()
    with _state["lock"]:
        res = history.fetch(code, date.replace("-", ""), pid=pid, progress=lambda *_: None)
    return jsonify(code=res["summary"]["code"], date=res["summary"]["date"],
                   count=len(res["orders"]), records=res["orders"], summary=res["summary"])


@app.get("/v1/history/trades")
def history_trades():
    code, date = request.args["code"], request.args["date"]
    pid = _pid()
    with _state["lock"]:
        res = history.fetch(code, date.replace("-", ""), pid=pid, progress=lambda *_: None)
    return jsonify(code=res["summary"]["code"], date=res["summary"]["date"],
                   count=len(res["trades"]), records=res["trades"], summary=res["summary"])


@app.get("/v1/live")
def v1_live():
    code = request.args["code"]
    channel = request.args.get("channel", "trade")
    seconds = float(request.args.get("seconds", 4))
    from_now = request.args.get("from_now", "0") in ("1", "true", "yes")
    pid = _pid()
    _ensure(pid, code)
    recs = live.snapshot(pid=pid, code=None, seconds=seconds, channel=channel, from_now=from_now)
    return jsonify(code=code, channel=channel, count=len(recs), records=recs)


@app.get("/v1/stream")
def v1_stream():
    code = request.args["code"]
    channel = request.args.get("channel", "trade")
    interval = float(request.args.get("interval", 1.0))
    pid = _pid()
    _ensure(pid, code)

    def gen():
        yield f": stream {code} {channel}\n\n"
        last = 0
        while True:
            try:
                recs = live.snapshot(pid=pid, code=None, seconds=interval, channel=channel, from_now=True)
            except Exception as e:  # noqa: BLE001
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(interval); continue
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
