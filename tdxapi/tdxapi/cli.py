"""Unified CLI for tdxapi.

    python -m tdxapi.cli history 002971 20260910 [--out DIR] [--pid PID]
    python -m tdxapi.cli live 002971 [--seconds 15] [--pid PID] [--all] [--channel trade]
"""
import argparse
import datetime as dt
import json
import pathlib
import sys

from . import fleet, history, live, orders, procinfo

CN = dt.timezone(dt.timedelta(hours=8))


def _emit(rec, out_file):
    line = json.dumps(rec, ensure_ascii=False)
    if out_file:
        out_file.write(line + "\n"); out_file.flush()
    else:
        print(line, flush=True)


def cmd_history(a):
    now = dt.datetime.now(CN)
    date = (a.date or now.strftime("%Y%m%d")).replace("-", "")
    day = dt.datetime.strptime(date, "%Y%m%d").date()
    if day > now.date():
        raise SystemExit("不能获取未来日期")
    if day.weekday() >= 5:
        raise SystemExit("所选日期是周末")
    if day == now.date() and now.time() < dt.time(15, 1):
        raise SystemExit("当天请在 15:01 之后获取")
    out_dir = pathlib.Path(a.out) if a.out else (
        pathlib.Path.cwd() / "exports" / f"{'sh' if history.market_of(a.code)==1 else 'sz'}{history._norm_code(a.code)}_{date}_{now.strftime('%H%M%S')}")
    res = history.fetch(a.code, date, pid=a.pid, out_dir=out_dir)
    s = res["summary"]
    print(f"完成：委托/撤单 {s['orders_and_cancels']:,} 条，成交 {s['trades']:,} 条；"
          f"范围 {s['first_order_time']} — {s['last_order_time']}", file=sys.stderr)
    print(f"输出：{s.get('output')}", file=sys.stderr)
    return 0


def cmd_live(a):
    out_file = open(a.out, "a", encoding="utf-8") if a.out else None
    def on_record(r):
        if a.channel in (None, "all", r["channel"]):
            _emit(r, out_file)
    def on_event(e):
        if e.get("kind") in ("attach", "head_shift", "reset", "err", "ready"):
            print(f"[{e.get('kind')}] {json.dumps({k:v for k,v in e.items() if k!='kind'}, ensure_ascii=False)}",
                  file=sys.stderr, flush=True)
    try:
        reader = live.LiveReader(pid=a.pid, code=a.code, on_record=on_record, on_event=on_event,
                                 from_now=not a.all)
        reader.start()
        if a.seconds:
            reader.run(a.seconds)
        else:
            print("[live] Ctrl-C 退出", file=sys.stderr)
            reader.run(None)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            reader.stop()
        except Exception:
            pass
        if out_file:
            out_file.close()
    return 0


def cmd_fleet(a):
    out_file = open(a.out, "a", encoding="utf-8") if a.out else None
    def on_record(r):
        _emit(r, out_file)
    def on_event(e):
        print(f"[{e.get('kind')}] {json.dumps({k:v for k,v in e.items() if k!='kind'}, ensure_ascii=False)}",
              file=sys.stderr, flush=True)
    fl = fleet.Fleet(a.codes, on_record=on_record, on_event=on_event, progress=lambda m: print(m, file=sys.stderr, flush=True))
    try:
        fl.bring_up().stream(a.seconds)
    except KeyboardInterrupt:
        fl.stop()
    finally:
        if out_file:
            out_file.close()
    return 0


def cmd_orders(a):
    out_file = open(a.out, "a", encoding="utf-8") if a.out else None
    def on_event(e):
        if e.get("kind") in ("attach", "head_shift", "err", "ready"):
            print(f"[{e.get('kind')}] {json.dumps({k:v for k,v in e.items() if k!='kind'}, ensure_ascii=False)}",
                  file=sys.stderr, flush=True)
    recs = orders.fetch_orders(pid=a.pid, code=a.code, seconds=a.seconds,
                               from_now=a.follow, on_event=on_event)
    for r in recs:
        _emit(r, out_file)
    print(f"共 {len(recs)} 条委托记录", file=sys.stderr, flush=True)
    if out_file: out_file.close()
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tdxapi", description="通达信逐笔数据程序化接口")
    sub = ap.add_subparsers(dest="cmd", required=True)

    h = sub.add_parser("history", help="任意股+日期（毫秒、含订单号）")
    h.add_argument("code"); h.add_argument("date", nargs="?")
    h.add_argument("--out", help="输出目录（默认 exports/...）"); h.add_argument("--pid", type=int)
    h.set_defaults(func=cmd_history)

    l = sub.add_parser("live", help="实时逐笔（可选自动切股）")
    l.add_argument("code"); l.add_argument("--seconds", type=int, default=15)
    l.add_argument("--pid", type=int); l.add_argument("--all", action="store_true", help="先回填当前缓冲全部")
    l.add_argument("--channel", choices=["trade", "order", "all"], default="all")
    l.add_argument("--out", help="输出 jsonl 文件")
    l.set_defaults(func=cmd_live)

    f = sub.add_parser("fleet", help="多实例并发实时（一只股=一个实例）")
    f.add_argument("codes", nargs="+", help="要同时实时监控的股票代码列表")
    f.add_argument("--seconds", type=int, default=60)
    f.add_argument("--out", help="合并输出 jsonl")
    f.set_defaults(func=cmd_fleet)

    o = sub.add_parser("orders", help="任意股逐笔委托（需先打开一次委托明细视图）")
    o.add_argument("code"); o.add_argument("--seconds", type=float, default=4.0)
    o.add_argument("--pid", type=int); o.add_argument("--follow", action="store_true", help="只取新到的委托(流式)")
    o.add_argument("--out", help="输出 jsonl 文件")
    o.set_defaults(func=cmd_orders)

    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
