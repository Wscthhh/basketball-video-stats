$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath "$PSScriptRoot\.venv")) {
  py -m venv "$PSScriptRoot\.venv"
}
& "$PSScriptRoot\.venv\Scripts\python.exe" -m pip install -r "$PSScriptRoot\backend\requirements.txt"

$existing = Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($existing) {
  try {
    $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 3
    if ($health.ok) {
      Write-Host "COURTTRACE backend is already running at http://127.0.0.1:8000" -ForegroundColor Green
      Write-Host "Reusing process $($existing.OwningProcess). Press Ctrl+C only in the terminal that started it." -ForegroundColor DarkGray
      exit 0
    }
  } catch {
    throw "Port 8000 is occupied by process $($existing.OwningProcess), but it is not a COURTTRACE backend. Stop that process or choose another port."
  }
}

& "$PSScriptRoot\.venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
