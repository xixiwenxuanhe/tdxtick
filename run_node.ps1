# Windows 数据节点启动脚本（读取 .env）
# 用法: powershell -ExecutionPolicy Bypass -File run_node.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

# 载入 .env
$envFile = Join-Path $root ".env"
if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
      $k, $v = $line.Split("=", 2)
      [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim(), "Process")
    }
  }
}

$py = if ($env:TDXAPI_PYTHON) { $env:TDXAPI_PYTHON } else { "D:\Install\Miniconda\python.exe" }
Push-Location (Join-Path $root "tdxapi")
try {
  & $py -m tdxapi.server @args
} finally { Pop-Location }
