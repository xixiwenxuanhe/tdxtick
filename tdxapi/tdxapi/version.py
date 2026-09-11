"""Frozen constants for the verified TDX build. Update only after re-validating."""

# TdxW.exe V7.73 (D:\Install\tdx) — verified 2026-09-11
BUILD_SHA256 = "58bd2117ec86e8c063639f7adae4218011bb93998e3d93dcd286672d1978736b"

# Historical .tck loader on the client's UI thread
HISTORY_LOADER_RVA = 0x213D50

# Live in-memory tick buffers (see RE_FINDINGS.md)
LIVE_TRADE_FN_RVA = 0x79BD0B   # 逐笔成交 list render
LIVE_ORDER_FN_RVA = 0x760A80   # 逐笔委托 list render (only when that window is open)
OBJ_STATE_OFFSET = 0x68        # -> object whose +0.. is the 6-char code
TRADE_COUNT_OFFSET = 0x250
TRADE_DATA_OFFSET = 0x348
ORDER_COUNT_OFFSET = 0x254
ORDER_DATA_OFFSET = 0x3D0
RECORD_SIZE = 20               # bytes, both channels

# Display buffer seconds field is stored 6h behind Beijing time
TIME_OFFSET_SECONDS = 21600

# Session filter for .tck (HHMMSSmmm)
SESSION_START = 91500000
SESSION_END = 150000999
