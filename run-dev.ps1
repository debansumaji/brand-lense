$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$python = Join-Path $backend '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $python)) {
  $python = Join-Path $root '.python\python.exe'
}

if (-not (Test-Path -LiteralPath $python)) {
  $python = 'py'
}

Start-Process powershell -ArgumentList @(
  '-NoExit', '-Command',
  "Set-Location -LiteralPath '$backend'; `$env:USE_MOCK_AI='true'; & '$python' -m uvicorn main:app --reload --port 8000"
)
Start-Process powershell -ArgumentList @(
  '-NoExit', '-Command',
  "Set-Location -LiteralPath '$frontend'; npm.cmd run dev"
)

Write-Host 'Backend and frontend are starting in separate terminals.'
