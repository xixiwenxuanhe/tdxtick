"""Run: export_orders.py 002971 [20260907] [--out DIR]."""
import argparse, datetime as dt, json, pathlib, re, sys, tempfile, time
from tdx_session import download
from tck_format import export_tck
ROOT=pathlib.Path(__file__).resolve().parent
CN=dt.timezone(dt.timedelta(hours=8))
def arguments(argv=None):
    p=argparse.ArgumentParser(description="通过已登录通达信导出指定股票、日期的逐笔委托/撤单。默认日期为北京时间今天。")
    p.add_argument("code",help="6 位沪深股票代码，可带 sh/sz 前缀")
    p.add_argument("date",nargs="?",help="YYYYMMDD 或 YYYY-MM-DD；省略为今天")
    p.add_argument("--market",choices=["sh","sz"])
    p.add_argument("--pid",type=int)
    p.add_argument("--out",type=pathlib.Path,help="保存目录（必须为空或不存在）")
    a=p.parse_args(argv);now=dt.datetime.now(CN);raw=a.code.lower()
    prefix=raw[:2] if raw.startswith(("sh","sz")) else None
    a.code=raw[2:] if prefix else raw
    if not re.fullmatch(r"\d{6}",a.code):p.error("股票代码必须是 6 位数字。")
    if prefix and a.market and prefix!=a.market:p.error("股票代码前缀与 --market 冲突。")
    a.market=a.market or prefix
    if not a.market:
        if a.code.startswith("6"):a.market="sh"
        elif a.code.startswith(("0","3")):a.market="sz"
        else:p.error("当前已验证沪深股票；北交所未适配。")
    if a.date and not re.fullmatch(r"\d{8}|\d{4}-\d{2}-\d{2}",a.date):p.error("日期格式必须为 YYYYMMDD 或 YYYY-MM-DD。")
    try:day=dt.datetime.strptime(a.date.replace("-",""),"%Y%m%d").date() if a.date else now.date()
    except ValueError:p.error("日期无效，请使用 YYYYMMDD 或 YYYY-MM-DD。")
    if day>now.date():p.error("不能获取未来日期。")
    if day.weekday()>=5:p.error("所选日期为周末，不是沪深股票交易日。")
    if day==now.date() and now.time()<dt.time(15,1):
        p.error("当天尚未收盘，请在 15:01 后获取 09:15 至收盘的数据。")
    a.date=day.strftime("%Y%m%d")
    if a.out is None:a.out=ROOT/"exports"/f"{a.market}{a.code}_{a.date}_{now.strftime('%H%M%S_%f')}"
    a.out=a.out.resolve()
    if a.out.exists() and (not a.out.is_dir() or any(a.out.iterdir())):p.error("输出目录非空，请选择新目录。")
    return a
def main(argv=None):
    a=arguments(argv);begun=time.monotonic()
    print(f"请求 {a.market}{a.code} / {a.date}，范围 09:15—15:00。",flush=True)
    market=1 if a.market=="sh" else 0
    source,connection=download(a.code,a.date,market,pid=a.pid)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".tdx-export-",dir=a.out.parent) as tmp:
        summary=export_tck(source,tmp,a.code,a.date,market)
        manifest=dict(**connection,source_cache=str(source),
            cache_modified=dt.datetime.fromtimestamp(source.stat().st_mtime,CN).isoformat(),
            exported_at=dt.datetime.now(CN).isoformat(),
            elapsed_seconds=round(time.monotonic()-begun,2),output=str(a.out))
        pathlib.Path(tmp,"request.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
        a.out.mkdir(exist_ok=True)
        for file in pathlib.Path(tmp).iterdir():file.rename(a.out/file.name)
    print(f"完成：{summary['orders_and_cancels']:,} 条委托/撤单；{summary['trades']:,} 条成交。")
    print(f"委托范围：{summary['first_order_time']} — {summary['last_order_time']}")
    print(f"输出：{a.out}")
    return summary
def cli():
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,"reconfigure"):stream.reconfigure(encoding="utf-8")
    try:main()
    except (RuntimeError,ValueError,OSError,TimeoutError) as e:
        print(f"导出失败：{e}",file=sys.stderr);sys.exit(1)
if __name__=="__main__":cli()
