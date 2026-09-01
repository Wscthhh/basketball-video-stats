$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$iscc = Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'
$source = Join-Path $root 'release\runtime-stage\backend\CourtTraceBackend\CourtTraceBackend.exe'
$script = Join-Path $root 'installer\courttrace-runtime.iss'
if (-not (Test-Path -LiteralPath $iscc)) { throw 'Inno Setup is not installed.' }
if (-not (Test-Path -LiteralPath $source)) { throw 'Run npm run desktop:runtime first.' }
& $iscc $script
if (-not $?) { throw 'Runtime installer packaging failed.' }
Write-Host 'Runtime installer created in release.'
