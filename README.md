# tdxtick

**通达信（TDX）A 股逐笔数据接口** —— 历史 + 实时，程序化获取，不依赖人工点击。

对一个**正在运行并已登录**的通达信 V7.73 客户端，提供两条数据通道与一个本地 HTTP API：

| 通道 | 覆盖 | 精度 | 内容 | 依赖 |
|---|---|---|---|---|
| **历史** | 任意沪深股 + 任意日期 | 毫秒 | 逐笔委托 / 撤单 / 成交，含订单号、channel/sequence | 客户端 `.tck` 回放（当天收盘后约 15:30 可下载） |
| **实时** | 任意股（自动切股） | 秒 | 逐笔成交；逐笔委托/撤单 | 客户端内存缓冲（委托需"逐笔委托明细"视图打开一次） |

> 版本守卫：所有操作前校验 `TdxW.exe` 的 SHA256，客户端升级后会**拒绝运行**而不是返回错误数据。
> 已验证版本：`58bd2117…736b`（V7.73）。

---

## 安装

```powershell
cd C:\path\to\tdxtick
D:\Install\Miniconda\python.exe -m pip install -r requirements.txt
```

## 命令行

```powershell
# 历史：任意股 + 任意日期（自动落盘 CSV/JSON）
D:\Install\Miniconda\python.exe -m tdxapi.cli history 002971 20260910 --out out\002971_20260910

# 实时成交（任意股，自动切股）
D:\Install\Miniconda\python.exe -m tdxapi.cli live 000001 --seconds 30

# 实时逐笔委托/撤单（需先打开一次"逐笔委托明细"）
D:\Install\Miniconda\python.exe -m tdxapi.cli orders 000001 --seconds 4

# HTTP 服务
D:\Install\Miniconda\python.exe -m tdxapi.server --pid <TDX_PID> --port 8712
```

## HTTP API

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/health` | 存活 + 版本哈希校验 |
| GET | `/v1/history/orders?code=002971&date=20260910` | 历史逐笔委托+撤单（ms、含订单号） |
| GET | `/v1/history/trades?code=002971&date=20260910` | 历史逐笔成交（ms） |
| GET | `/v1/live?code=000001&channel=trade\|order&seconds=4` | 实时快照（JSON） |
| GET | `/v1/stream?code=000001&channel=trade\|order&interval=1` | SSE 实时流 |

## Python API

```python
from tdxapi import history, live, orders

res = history.fetch("002971", "20260910", out_dir="out/002971")   # 历史（订单级）
recs = live.snapshot(code="000001", seconds=4, channel="trade")   # 实时成交
ords = orders.fetch_orders(code="000001", seconds=4)              # 实时委托/撤单
```


## 配置与部署

**只需在 `.env` 填一行：通达信的安装目录**

```ini
TDX_PATH=D:\Install\tdx
```

服务会自动：解析出 `TdxW.exe`、找到对应的通达信进程、绑定 **Tailscale 网卡**、生成并保存 Bearer Token 到 `.tdxtoken`（启动时会打印）。

启动（Windows，通达信需已登录）：

```powershell
copy .env.example .env      # 改成本机通达信目录
powershell -ExecutionPolicy Bypass -File run_node.ps1
```

访问（tailnet 内任意机器）：

```bash
curl http://<windows-tailscale-ip>:8712/health
curl -H "Authorization: Bearer <token>" "http://<ip>:8712/v1/live?code=000759&channel=order&seconds=3"
```

> 数据节点必须在 Windows（TDX 是 GUI 程序，靠 FRIDA 注入进程/读内存）。访问靠 Tailscale，**不需要 Docker、不需要公网**。

## 数据字段

- 成交：`time, price, shares, direction_raw, bid_order_number, ask_order_number`
- 委托：`time, price, shares, event(order|cancel), side(B|S), order_number`
- 历史还含 `channel, sequence, order_price, time(ms)` —— 可用 `bid_order_number`/`ask_order_number`
  与委托的 `order_number` **关联**，做订单流分析。

## 已知限制

- **一次只能实时服务一只股**（切股会替换客户端当前股缓冲）；多股并发需多开实例（`fleet.py`）或走实验性的无视图注入（`orders_wire.py`）。
- `channel=order`（委托）需要客户端"逐笔委托明细"视图打开一次；之后切股会自动跟随。
- 历史当天数据在收盘后（约 15:30）才可下载。

## 目录

```
tdxapi/            主包（version/procinfo/history/live/orders/orders_wire/window/fleet/server/cli）
scripts/           便捷入口（export_history.py / watch_live.py）
probes/            逆向探针（协议/内存分析，见 docs/）
docs/              逆向与设计文档
export_orders.py   独立历史导出脚本
tck_format.py      .tck 解码
tdx_session.py     历史下载（通达信内部加载器）
```

## 文档

- `docs/realtime-findings.md` —— 实时内存布局、协议帧、命令码
- `docs/decoder-reverse-engineering.md` —— 0x0554/0x055e 逐笔线协议逆向记录（含未完成部分）
- `docs/snapshot-20260911.md` —— 2026-09-11 成果快照

## 免责声明

仅供个人研究/数据分析使用；请遵守数据源与交易所相关规定，自行承担使用风险。
