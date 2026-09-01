$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$iscc = Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'
$source = Join-Path $root 'release\win-unpacked\COURTTRACE.exe'
$script = Join-Path $root 'installer\courttrace.iss'
if (-not (Test-Path -LiteralPath $iscc)) { throw 'Inno Setup is not installed.' }
if (-not (Test-Path -LiteralPath $source)) { throw 'Missing release\win-unpacked. Run npm run desktop:prepare first.' }
& $iscc $script
if (-not $?) { throw 'Inno Setup packaging failed.' }
Write-Host 'Installer created in release.'
