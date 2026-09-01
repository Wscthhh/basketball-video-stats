$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $root '.venv\Scripts\python.exe'
$backendRelease = Join-Path $root 'release\backend'
$ffmpegRelease = Join-Path $root 'release\ffmpeg'

if (-not (Test-Path -LiteralPath $venvPython)) { throw 'Missing .venv. Run start-backend.ps1 once first.' }
if (-not (Test-Path -LiteralPath (Join-Path $root 'models'))) { throw 'Missing models directory.' }

& $venvPython -m pip install pyinstaller
if (-not $?) { throw 'PyInstaller installation failed.' }
New-Item -ItemType Directory -Force -Path $backendRelease, $ffmpegRelease | Out-Null
& $venvPython -m PyInstaller --noconfirm --clean --onedir --name CourtTraceBackend --distpath $backendRelease --workpath (Join-Path $root 'release\pyinstaller-build') --specpath (Join-Path $root 'release') (Join-Path $root 'backend\desktop_server.py')
if (-not $?) { throw 'Backend packaging failed.' }

$ffmpeg = (Get-Command ffmpeg -ErrorAction SilentlyContinue).Source
if (-not $ffmpeg) { throw 'FFmpeg is required to build the desktop package.' }
Copy-Item -LiteralPath $ffmpeg -Destination (Join-Path $ffmpegRelease 'ffmpeg.exe') -Force
Write-Host 'Desktop backend prepared. Run npm run desktop:package to create the NSIS installer.'
