# 通达信实时逐笔 逆向记录

对象：通达信金融终端 V7.73（`D:\Install\tdx\TdxW.exe`，SHA256 `58bd2117…736b`，64 位）
时间：2026-09-11 盘中实测；标的 000759（中百集团，SZ）

## 1. 结论速览

| 通道 | 状态 | 来源 |
|---|---|---|
| 历史 逐笔委托/撤单/成交（毫秒、含订单号） | 可用 | `.tck` 回放（`export_orders.py`），收盘后可得 |
| 实时 逐笔**成交**（秒级、含买卖订单号） | **可用** | 进程内存对象 |
| 实时 逐笔**委托** | **仅当"逐笔委托明细"窗口打开时可用** | 进程内存对象（另一个对象，按需拉取） |
| 实时 逐笔委托（免窗口 / 多只） | 需继续：解码 `mp_tick_ans` 或调用内部请求 | 见 §5 |

官方 Python 接口 `tqcenter` **不能**取 tick：`get_market_data` 的 `valid_periods` 不含 `'tick'`，`period=='tick'` 是死代码；`subscribe_hq` 只推行情快照。盘中拉当天 `.tck` 会被服务端拒绝（`Error: system error`）。

## 2. 进程内存布局（已验证）

在 `TdxW.exe+0x79bd0b`（成交列表渲染）和 `TdxW.exe+0x760a80`（委托列表渲染）下钩子：

```
obj->[+0x68] 是个 state 对象，其 +0x00 起为 6 字节代码，如 "000759"

成交数组:  count = u32  @ obj+0x250      data = ptr @ obj+0x348
委托数组:  count = u32  @ obj+0x254      data = ptr @ obj+0x3d0

记录均 20 字节:
  成交  <HIIbBII>   = 秒, 价*10000, 手, 零股, 方向, 买委托号, 卖委托号
  委托  <HIIbcccHI> = 秒, 价*10000, 手, 零股, 类型, 动作, flags, aux, 委托号
         普通单: 动作 = 'B'/'S'，类型 = '1'/'2'；撤单: 动作='C'，类型 = 原方向
  显示时间 = 秒字段 + 21600 (6h 经验偏移)
```

要点：
- 数组是**只追加**（实测 30 s 内 73 个快照前缀完全一致，0 次头部位移）；到 count≈40k 仍不淘汰。
- `data` 指针会因扩容**变化**，必须每次都从 `+0x250/+0x348` 重新读取。
- 成交数组对**当前股票**常驻；委托数组只在委托明细窗口打开时被填充/刷新。
- 同一时刻整个进程只有 **1 个**该类的对象实例（用 vtable `0x7ff7047a5870` 全内存扫描确认），即只跟踪当前股票。

## 3. 网络层

TDX 走 `TdxAsioComm64.dll`（Boost.Asio + IOCP），实际系统调用是 `WS2_32!WSARecv` / `WSASend`，调用点 `TdxAsioComm64.dll+0x9f2e`（收）与 `+0x7c92`（发）。

请求/响应帧（例，0x0c 起）：
```
0c 0a 08 03 03 01 10 00 10 00 50 05 00 00 "000759" <u32 序列> 01 00
```
抓到的命令码（`xx 05`，即 little-endian 的 0x05xx）：

| 命令 | 方向 | 观察到的载荷 |
|---|---|---|
| 0x0550 | req/resp | `"000759"` + u32 递增序列；响应 12 字节 |
| 0x0554 | req/resp | 请求带 `"000759"` + 序列 + `dc 05`(1500)；响应 payload 是**非 zlib 的增量/字编码流**（不是明文 18B 记录），需专用解压器 |
| 0x0547 / 0x0527 / 0x054e | req | `"000759"` + u32 计数 |
| 0x054c | req | 批量股票代码列表（如 "880594","880219"…） |
| 0x0552 | resp | 大量 zlib（`78 9c`）压缩块 |

命令分派对比代码位于 `TdxW.exe`（文件偏移→RVA 用 pefile 换算）：
- `rva 0x5337d5`：一串 `cmp eax,0x555/0x54c/…/0x550/0x551/0x588/0x552/0x553/0x558/0x559/0x554/0x556/0x8f9`
- `rva 0x8cbc0e`：`0x554` 与 `0x551` 同分支 → `mov edx,0xb48200` 后调 vtable `[rax+0x70]`
- `rva 0x3b16b2`：`0x550` 等分支

## 4. iOS 端符号 + 结构体布局（解密 IPA，含完整符号表）

`com.tdx.pushMessage_7.27_decrypted.ipa` → `Frameworks/TdxCore.framework/TdxCore`（Mach-O arm64，已解密，**保留 49207 个符号**，可直接 capstone 反汇编）。类型名给出了协议结构体：

- `mp_tick_req` / `mp_tick_ans` —— 逐笔
- `mp_zst_req` / `mp_zst_ans` / `mp_sim_zst` / `mp_5zst_ans` —— 分时走势（**ZST = 走势图**，对应 Windows 的 `T0002/zst_cache/*.zsm|*.auc2`）
- `mp_hqinfo` / `mp_hqinfo_req` / `mp_hqinfo_ans`、`mp_fxt_req/ans`、`mp_combhq_req`、`mp_mask_ans`、`mp_pageall_ans`

### 关键函数地址（`TdxCore` 内，file offset = vaddr）

| 地址 | 符号 |
|---|---|
| `0x1157cc` | `CMaintainData::SetTick(mp_tick_req*, mp_tick_ans*, int)` |
| `0x115aa4` | `CMaintainData::GetTick(mp_tick_req*, mp_tick_ans*, int)` |
| `0x115af4` | `CMaintainData::GetTick(mp_tick_req*, TArrayByte&)` |
| `0x109730` | `CMaintainData::RefreshTick(mp_tick_req*)` |
| `0x72d4`   | `GetTickAns(mp_pageall_ans*, TArrayByte&)` |
| `0x7214`   | 由 `GetTickAns` 调用的 120B attach-info 构造器 |
| `0x11514c` | `CMaintainData::GetZST(mp_zst_req*, mp_zst_ans*, int)` |
| `0x3517a4` | `CThrQuotesSDK2TDXSvc::MakeTick(CJsonItemEx&, TArrayByte&, IJob*, ISession)` |

### `mp_tick_ans` 布局（由 `SetTick`/`GetTickAns` 反汇编得出）

```
+0x00  u16
+0x02  定长字符串（22 字节，fmt "%s"）
+0x1c  u8   flag   (1 = 有效)
+0x1d  s16  count  (逐笔条数)
+0x27  count × 18 字节  逐笔记录   <-- 线格式记录大小 = 18 字节
末尾   120 字节 attach info
总长 = count*0x12 + 0x9f
```

- `mp_tick_req` 大小 = **46 字节**（`SetTick` 里对 `req` 做 46 字节拷贝；`RefreshTick` 里清零 `req+0x1e`）。
- 原始线数据放在 `mp_pageall_ans + 0xfc` 处（`GetTickAns` 直接 `memcpy` 到 `ans+0x27`），页数在 `pageall_ans+0x7c`。
- `CMaintainData` 本体内：逐笔缓冲指针 `this+0x230`、条数 `this+0x23c`、标志 `this+0x248`；分时缓冲 `this+0x1f8`、条数 `this+0x204`、标志 `this+0x210`。

`GetOptEx` 的分支：`$_0=zst`、`$_2=tick`、`$_4=fxt`、`$_5=hqinfo`、`$_8=combhq`。
L2 相关符号：`L2Subscribe`、`L2Session`、`L2Permission`、`HQL2Login`、`L2PASS`。

### 下一步（用已知明文破 18 字节记录）

用 18 字节记录大小反查消费端（渲染/`GetZST` 类似的读取代码），即可还原 time/price/vol/direction/bid/ask 的字段偏移；再与 Windows `0x0554` 响应逐字节对齐（当前股票已知成交值做校验）。

## 5. 剩余工作（实时逐笔委托免窗口）

三条可选路径，按推荐度：

1. **解码 `mp_tick_ans` 线格式**：用 capstone 反汇编 iOS 的 `CMaintainData::SetTick/GetTick`（Mach-O symtab 里找地址），从字段访问偏移还原结构体；再和 Windows 的 `0x0554` 响应逐字节对齐（可用当前股票已知的成交值做已知明文校验）。解出后即可直接读 socket，覆盖多只。
2. **调用内部请求函数**：定位 Windows 端构造 `mp_tick_req` 并投递的函数（`TdxAsioComm64.dll+0x7c92` 的上层调用者），用 FRIDA 直接为任意代码发起请求，再读返回对象。
3. **UI 自动化**：程序化打开"逐笔委托明细"（菜单项字符串在 `TdxW.exe` 0x9bd330），配合 `watch_ticks.py` 已支持的 order 通道；单只、脆弱，作为兜底。

## 6. 工具

- `realtime_validation/watch_ticks.py`（+`.js`）—— 实时逐笔读取器，同时钩成交与委托两个通道，输出 JSONL，带完整性告警（头部位移/重置）。
  用法：`python watch_ticks.py <pid> [--seconds N] [--code 000759] [--all] [--out ticks.jsonl]`
- `realtime_validation/observe.py` —— 原始快照采集（验证用）
- `probe/` —— 逆向探针：`mods` `exports` `objdump` `scan`(全内存找实例) `find_writer` `alloc` `netdump` `netreq` `capresp` `head`
- `probe/netcap/` —— 抓到的响应帧样本
- `probe_intraday_tck.py` —— 证明盘中拉 tck 失败
- iOS 解包产物：`C:\Users\xixiw\Downloads\tdx-ios\TdxCore`

---

## 7. 后续进展（2026-09-11 下午）

### 7.1 已交付可用方案（见 `tdxapi/`）

- **history**: 任意股+任意日期，毫秒、含订单号（`.tck` 回放）。实测 002971/20260910 = 67,663 委托+撤单 / 30,570 成交。
- **live**: 程序化切股 + 读内存逐笔。实测切换 000759→002971 并实时取到成交。
- 目录：`tdxapi/`（version/procinfo/history/live/window/cli + js/live.js），统一 CLI 与 README。

### 7.2 lab 实例

主实例 `D:\Install\tdx`（用户），逆向专用 `D:\Install\tdx-lab`（robocopy 全量复制，可同时运行）。
用 `tdxapi/window.py` 的程序化按键可把 lab 切到任意股。

### 7.3 解码器（0x0554）追查记录

- 写「逐笔显示缓冲」的拷贝走 **MSVCR100.dll 的 memcpy**（不是 ntdll，之前一直钩错）。
- 抓到写入调用栈（均为 UI 线程）：
  `TdxW+0x54a685 / TdxW+0x79f7a5 / TdxW+0x799af3`、
  `TCalc64.dll+0x119b8 ← +0x45184 ← +0x4988f ← +0x4b22c ← +0x904f9 ← TdxW.exe+0x1ebc05 ← +0x1e538b ← +0x880a13 ← +0x87ea67`。
  → UI/计算线程只是把已解码记录拷进显示缓冲，**真正的线解码在这条链更上游**。
- TdxAsioComm 的收发底层 helper 在 `TdxAsioComm64.dll+0x9e80`（内部 `call [rip+0x4e532]`→WSARecv，返回于 +0x9f2e）。
- `0x0554` 非 zlib/deflate/gzip/bz2/lzma；熵 5.88 bit/B；首条 21–22B、后续 ~13B 的增量式；`(22 + 7×13 = 113)` 与 8 条样本吻合。
- MAM 的 `Thread.backtrace` 返回的是 Frida 自身栈（不可用）；Stalker 跟 GQCS 线程抓不到解码（不在该线程）。

### 7.4 下一步（建议）

1. 在**交易时段**对 lab 抓一对「0x0554 原始载荷 ↔ 同刻内存已解码记录」（pairs 工具已就绪），用已知明文反推字段/位布局。
2. 从 `TdxW.exe+0x880a13 / 0x87ea67`（疑似网络消息分发）往上，或对 `TdxAsioComm64` 收包缓冲下读监视，定位帧解析→回调，再定位回调里的解码。
3. 若拿到解码器，可直接对任意股构造 0x0554 请求 → 免切股、并发多只、盘中也无需 UI。


## 8. 0x0554 变长整数层（新增）

已确认 0x0554 不是固定块或不可逆浮点编码。先按 TDX signed-varint（首字节 6 位数据+符号，后续每字节 7 位）解码，再按 `5 + 6*n` 个值分组。`000759` 样本中，时间使用 `abs(v) ^ 0x6c09`，手数使用 `abs(v) ^ 9`，订单号使用 `abs(v) ^ 0x04993249`；实现和回归样本见 `probe/decoder0554.py` 与 `probe/test_decoder0554.py`。价格初始值及 aux（零股/方向）仍需用新会话样本闭合。
