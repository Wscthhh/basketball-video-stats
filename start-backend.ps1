$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath "$PSScriptRoot\.venv")) {
  py -m venv "$PSScriptRoot\.venv"
}
& "$PSScriptRoot\.venv\Scripts\python.exe" -m pip install -r "$PSScriptRoot\backend\requirements.txt"
& "$PSScriptRoot\.venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
