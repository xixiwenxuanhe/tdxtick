# tdxtick

通达信（TDX）A 股**逐笔数据**接口 —— 历史 + 实时，程序化获取，不依赖人工点击。

对一个**正在运行并已登录**的 Windows 版通达信 V7.73 客户端，提供两条数据通道和三种用法：

- **数据通道**
  - 历史：任意沪深股 + 任意日期，毫秒级，逐笔委托 / 撤单 / 成交（含订单号）
  - 实时：任意股（自动切股），逐笔成交、逐笔委托 / 撤单
- **用法**
  - Python 包 `tdxapi`
  - 本地 HTTP API（Tailscale 内访问）
  - 命令行 CLI

## 安装与配置

```powershell
cd C:\path\to\tdxtick
D:\Install\Miniconda\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

`.env` 只需一行 —— 通达信安装目录：

```ini
TDX_PATH=D:\Install\tdx
TDXAPI_TOKEN=...      # 可选；不填则自动生成并保存到 .tdxtoken
```

服务会自动：解析 `TdxW.exe` → 定位进程 → 绑定 Tailscale 网卡 → 取 token。

启动（Windows，通达信需已登录）：

```powershell
powershell -ExecutionPolicy Bypass -File run_node.ps1
```

## 接口

### HTTP API

- `GET /health` —— 存活 + 版本哈希校验
- `GET /v1/history/orders?code=002971&date=20260910` —— 历史逐笔委托 + 撤单（毫秒、含订单号）
- `GET /v1/history/trades?code=002971&date=20260910` —— 历史逐笔成交（毫秒）
- `GET /v1/live?code=000001&channel=trade|order&seconds=4` —— 实时快照（JSON）
- `GET /v1/stream?code=000001&channel=trade|order&interval=1` —— SSE 实时流
- 鉴权：`Authorization: Bearer <TDXAPI_TOKEN>`（`/health` 免鉴权）；非法/缺失参数返回 JSON `400`

```bash
curl -H "Authorization: Bearer <token>" "http://<windows-tailscale-ip>:8712/v1/live?code=000759&channel=order&seconds=3"
```

### Python API

```python
from tdxapi import history, live, orders

res  = history.fetch("002971", "20260910", out_dir="out/002971")  # 历史（订单级）
recs = live.snapshot(code="000001", seconds=4, channel="trade")   # 实时成交
ords = orders.fetch_orders(code="000001", seconds=4)              # 实时委托/撤单
```

### 命令行

```powershell
D:\Install\Miniconda\python.exe -m tdxapi.cli history 002971 20260910 --out out\002971
D:\Install\Miniconda\python.exe -m tdxapi.cli live 000001 --seconds 30
D:\Install\Miniconda\python.exe -m tdxapi.cli orders 000001 --seconds 4
D:\Install\Miniconda\python.exe -m tdxapi.cli fleet 600000 000001 002971 --seconds 60
D:\Install\Miniconda\python.exe -m tdxapi.server --pid <TDX_PID> --port 8712
```

### 数据字段

- 成交：`time, price, shares, direction_raw, bid_order_number, ask_order_number`
- 委托：`time, price, shares, event(order|cancel), side(B|S), order_number`
  - ⚠️ 沪市：`shares` 对"主动成交后又挂单"的委托是**剩余量**而非原始量（见 FAQ）
- 历史额外：`channel, sequence, order_price, time(ms)`
- 关联：用成交的 `bid_order_number`/`ask_order_number` 关联委托的 `order_number`，做订单流分析

## 已实现

- **历史逐笔**（任意沪深股 + 任意日期）
  - 走客户端 `.tck` 回放加载器下载并解码，自动落盘 CSV / JSON
  - 逐笔委托 / 撤单 / 成交，含订单号、channel、sequence，毫秒精度
  - 当天数据收盘后（约 15:30）可下载
- **实时逐笔**
  - 成交：任意股自动切股，读客户端内存缓冲
  - 委托 / 撤单：程序化切股后读缓冲（"逐笔委托明细"视图需打开一次，之后自动跟随切股）
  - 多股并发：`tdxapi.cli fleet <code...>`，一只股一个 TDX 实例（各自独立安装目录 + 登录），合并输出
- **HTTP 服务**
  - `/health`、`/v1/history/*`、`/v1/live`、`/v1/stream`（SSE）
  - Bearer 鉴权；非法参数统一返回 JSON 4xx（不再 500 HTML）
  - 自动绑定 Tailscale 网卡
- **工程化**
  - 版本守卫：校验 `TdxW.exe` 的 SHA256（已验证 V7.73 / `58bd2117…736b`），客户端升级后拒绝运行而不是返回错数据
  - 最小配置：`.env` 只需 `TDX_PATH`，其余自动推导
  - 单文件启动脚本 `run_node.ps1`

## 暂未实现

- **无视图实时委托 `orders_wire`**
  - 目标：直接往客户端行情 socket 注入 `0x055e`，取任意股逐笔委托，不依赖视图、不用切股
  - 现状：请求 / 响应链路已跑通（注入 + zlib 解压），已验证能取到指定股数据（约 1.5 万条）
  - 卡点：`0x055e` 响应是「逐记录差分 + 逐位置密钥 0x49」的变长字节流，`price` / `num` 的定点格式与记录边界未完全解出
- **成交 ↔ 委托按订单号关联**（订单流聚合接口）
  - 深市可 100% 关联；沪市只能关联被动方（原因见「说明 / FAQ」）
- **单实例多股并发（免切股）**
  - 现状：一个实例同时只服务一只股（切股串行化）；多股靠 `fleet`，代价是 N 份 TDX 安装 + N 个登录
  - 方案：基于 `orders_wire` 向同一 socket 注入多个 `0x055e` 订阅
- **服务常驻**：用 Windows 计划任务 / NSSM 包装 `run_node.ps1`，崩溃自启
- **收盘后自动回补**：每日约 15:30 自动下载自选股当天 `.tck` 并入库
- **历史入 DuckDB / Parquet**：统一查询层与 keyset 分页
- **SSE `/v1/stream` 多股订阅**（依赖多实例或 `orders_wire`）
- **Token 轮换 / 多 Token**
- **沪市记录加 `coverage: "resting_only"` 标注**，避免调用方误做订单存续重建

## 说明 / FAQ

### 沪市"逐笔委托"为什么只有被动挂单方，深市却是完整的？

- 这是**两市交易所行情发布规则不同**，不是通达信的问题，也不是本项目抓取/解码的问题。
- 上交所：根据《上海证券交易所 LDDS 系统竞价 Level-2 行情接口说明书》§4.3.1「竞价逐笔合并数据」——
  - 连续竞价阶段，"立即全部成交"的主动委托**不发布委托记录**（只发成交）；
  - 只有"成交后剩余"才在成交**之后**补发一条委托记录，之后再变化不再发；
  - 集合竞价期间不发逐笔，结束时统一补发，且**先发委托、再发成交**。
  - 因此委托记录的 `quantity_shares` 是**剩余量**，不是原始量：`原始量 = 记录量 + 该委托的即时成交量`（实测 600000 有 637 笔暴露为"记录量 < 已成交量"，占 1.04%，修正后 0 笔真透支；深市 0）。
- 深交所：根据《深圳证券交易所 STEP 行情数据接口规范》§4.4.5 ——
  - 逐笔委托（UA201）与逐笔成交（UA202）在**同一数据流统一连续编号**；
  - UA201 携带 `Price` / `OrderQty`（**原始委托价与委托量**），**每一笔委托都会发布**。
- 实测（`600000` / `20260911`）与规则完全吻合：
  - 每笔成交至少有一方在委托流里：62,526 笔**无一例外**
  - 在委托流里的那一方：**100%** 是委托号更小（更早到达）的被动方
  - 集合竞价成交：480 笔**双边全部命中**
  - 连续竞价成交：62,046 笔，仅 4,494 双边命中（7%）
  - 深市对照 `002971`：**100%** 双边命中
- 影响：
  - 深市可做**完整订单账本**（`委托量 = 成交量 + 撤单量 + 剩余量` 闭环）
  - 沪市做不了完整账本，只能做「被动挂单 + 成交」类分析（被动撤单率、挂单存续、主动单聚合成交额）
  - 沪市以"委托量"为分母的统计（大单识别、挂单规模、撤单率）在那 ~7% 上会**系统性低估**，
    需按上述公式修正，且锚点用合并流的 `sequence` 邻接而非毫秒（毫秒会撞车）
- 完整推导见 `docs/sh-vs-sz-tick-fields.md`。
