$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$stage = Join-Path $root 'release\runtime-stage'
$archive = Join-Path $root 'release\CourtTrace-Runtime-0.1.0.zip'
if (-not (Test-Path -LiteralPath (Join-Path $root 'release\backend\CourtTraceBackend\CourtTraceBackend.exe'))) { throw 'Run npm run desktop:prepare-runtime first.' }
if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Copy-Item -LiteralPath (Join-Path $root 'release\backend') -Destination $stage -Recurse
Copy-Item -LiteralPath (Join-Path $root 'release\ffmpeg') -Destination $stage -Recurse
Copy-Item -LiteralPath (Join-Path $root 'models') -Destination $stage -Recurse
if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
tar -a -c -f $archive -C $stage backend ffmpeg models
if (-not $?) { throw 'Runtime archive failed.' }
Write-Host "Runtime archive created: $archive"
