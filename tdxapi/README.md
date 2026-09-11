# tdxapi — 通达信逐笔数据程序化接口

对一个**正在运行并已登录**的通达信 V7.73 客户端，提供两条纯程序化的数据通道（无需人工点击）：

| 通道 | 覆盖 | 精度 | 内容 | 依赖 |
|---|---|---|---|---|
| `history` | 任意沪深股 + 任意日期 | **毫秒** | 逐笔委托 / 撤单 / 成交，含订单号、channel/sequence | 客户端 `.tck` 回放（收盘后可取当天） |
| `live` | 任意股（会自动切股） | 秒 | 逐笔成交 | 客户端内存缓冲 |
| `orders` | **任意股（会自动切股）** | 秒 | **逐笔委托 / 撤单**（含委托号、方向、价、量） | 客户端内存缓冲（需"逐笔委托明细"视图打开一次） |

> 版本守卫：所有操作前会校验 `TdxW.exe` 的 SHA256，客户端升级后**会拒绝运行**而不是返回错误数据。
> 已验证版本：`58bd2117…736b`（V7.73）。若客户端更新，需要重新核对 `tdxapi/version.py` 里的 offsets。

## 安装

```powershell
cd C:\Users\xixiw\Downloads\tdx-interface-research\tdxapi
D:\Install\Miniconda\python.exe -m pip install -r requirements.txt
```

## 命令行

```powershell
# 历史：任意股 + 任意日期（自动落盘 CSV/JSON）
D:\Install\Miniconda\python.exe -m tdxapi.cli history 002971 20260910 --out out\002971_20260910

# 实时：自动把客户端切到该股，输出 jsonl（Ctrl-C 退出）
D:\Install\Miniconda\python.exe -m tdxapi.cli live 002971 --seconds 30 --out live_002971.jsonl

# 任意股逐笔委托（先用一次客户端打开"逐笔委托明细"，之后可全自动换股）
D:\Install\Miniconda\python.exe -m tdxapi.cli orders 000001 --seconds 4 --out orders_000001.jsonl

# 多实例时指定进程
D:\Install\Miniconda\python.exe -m tdxapi.cli live 002971 --pid 15332 --seconds 10
```

`history` 输出目录包含：`orders.csv`（委托+撤单）、`trades.csv`（成交）、`all_records.csv`、`source.tck`、`summary.json`。

## Python API

```python
from tdxapi import history, live

# 历史（毫秒级、含订单号）
res = history.fetch("002971", "20260910", out_dir="out/002971")
res["orders"][0]     # dict(event=..., side=..., order_number=..., time='09:30:00.123', ...)
res["summary"]       # 统计/校验字段

# 实时（会短暂抢焦点切股；不需要人工点击）
recs = live.snapshot(pid=None, code="002971", seconds=5)
for r in recs:
    print(r["time"], r["price"], r["shares"], r["bid_order_number"], r["ask_order_number"])

# 或事件回调（长期运行）
reader = live.LiveReader(code="002971", on_record=print, on_event=print)
reader.start().run(60)   # 或 run(None) 一直跑
reader.stop()

# 任意股逐笔委托（程序化切股 + 读内存；无需人工点击）
from tdxapi import orders
recs = orders.fetch_orders(code="000001", seconds=4)          # 该股当前全部委托
recs = orders.fetch_orders(code="000001", seconds=4, from_now=True)  # 只取新到的(流式)
```


## HTTP API 服务

```powershell
cd C:\Users\xixiw\Downloads\tdx-interface-research\tdxapi
D:\Install\Miniconda\python.exe -m tdxapi.server --pid 23124 --host 127.0.0.1 --port 8712
```

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 存活 + 版本哈希校验 |
| GET | `/v1/history/orders?code=002971&date=20260910` | 历史逐笔委托+撤单（ms、含订单号） |
| GET | `/v1/history/trades?code=002971&date=20260910` | 历史逐笔成交（ms） |
| GET | `/v1/live?code=000001&channel=trade\|order&seconds=4` | 实时快照（JSON） |
| GET | `/v1/stream?code=000001&channel=trade\|order&interval=1` | SSE 实时流 |

说明：
- 服务对**切股做串行化**（一个实例同一时刻只服务一只股）。要多股并发，用 `fleet.py` 多开实例，或等 `orders_wire`（无视图注入）收尾。
- `channel=order` 需要客户端"逐笔委托明细"视图打开一次。
- 历史当天数据在**收盘后（约 15:30）**才可下载；过去日期秒回（有缓存）。
- 建议用 Tailscale/Cloudflare Tunnel 暴露，并加 Bearer Token（见下）。

## 数据字段

`live` 成交记录：
```
{"channel":"trade","code":"002971","time":"11:16:19","time_raw":18979,
 "price":36.25,"shares":200,"direction_raw":0,
 "bid_order_number":23349341,"ask_order_number":23335544}
```
`history` 记录（`history.decode`）：`time`(含毫秒)、`event`(order/cancel/trade)、`side`、
`price`、`quantity_shares`、`order_number`、`bid_order_number`、`ask_order_number`、`channel`、`sequence`。

## 已知限制

- **一次只能实时服务一只股**：切股会替换客户端当前股的缓冲，不能并发多只；切股会短暂抢占窗口焦点。
- `live` 的 `order` 通道只有在客户端打开"逐笔委托明细"窗口时才有数据（打开一次即可，之后切股自动跟随）；`trade` 通道常驻。
- `orders.fetch_orders` 走的正是这条路径（程序化切股，无需人工点击）；另有实验性的 `orders_wire`（直接注入 `0x055e`，无需视图，已验证能取到数据，字节流字段格式仍在收尾）。
- 当天 `.tck` 需在 15:01 之后才能取；实时通道时间只到秒。
- 交换级完整性不做保证（由通达信服务端提供）。

## 目录

```
tdxapi/
  tdxapi/version.py     # 版本哈希 + 已验证的 offsets（升级后需重核）
  tdxapi/procinfo.py    # 进程/窗口/版本校验
  tdxapi/history.py     # .tck 下载 + 解码
  tdxapi/live.py        # 内存逐笔读取
  tdxapi/window.py      # 程序化切股
  tdxapi/js/live.js     # frida 实时钩子
  tdxapi/cli.py         # 统一命令行
```

## 相关研究记录

协议逆向、offsets 推导、未完成的 0x0554 解码见
`../realtime_validation/RE_FINDINGS.md`。
