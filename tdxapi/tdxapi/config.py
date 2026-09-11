"""Settings loaded from a .env file (and environment variables).

Priority: explicit CLI arg > environment variable > .env file > default.

.env 只需一行：
  TDX_PATH          通达信的安装目录（TdxW.exe 所在目录）

可选覆盖（一般不用填）：
  TDX_PID / TDXAPI_HOST / TDXAPI_PORT / TDXAPI_TOKEN / TDX_EXPORT_DIR
"""
import os
import pathlib

_ENV_CACHE = {}


def load_env(path=None):
    """Parse a .env file (KEY=VALUE) without extra deps. Idempotent."""
    if _ENV_CACHE:
        return _ENV_CACHE
    candidates = [pathlib.Path(path)] if path else [
        pathlib.Path.cwd() / ".env",
        pathlib.Path(__file__).resolve().parents[1] / ".env",   # repo root
        pathlib.Path(__file__).resolve().parents[2] / ".env",
    ]
    for p in candidates:
        try:
            if not p or not p.is_file():
                continue
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    _ENV_CACHE[k] = v
        except Exception:
            pass
    return _ENV_CACHE


def get(key, default=None):
    return os.environ.get(key) or _ENV_CACHE.get(key) or default


def tdx_exe():
    """Resolve the TDX executable from TDX_PATH (a directory or the exe itself)."""
    raw = get("TDX_PATH") or get("TDX_EXE")
    if not raw:
        return None
    p = pathlib.Path(raw)
    if p.is_dir():
        p = p / "TdxW.exe"
    return p
