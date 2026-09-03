$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$version = (Get-Content (Join-Path $root 'package.json') -Raw | ConvertFrom-Json).version
$release = Join-Path $root 'release'
$offline = Join-Path $release "COURTTRACE-Offline-$version"
& (Join-Path $root 'scripts\build-desktop.ps1')
if (-not $?) { throw 'Desktop backend preparation failed.' }
& (Join-Path $root 'scripts\build-runtime.ps1')
if (-not $?) { throw 'Runtime split build failed.' }
& npm run build
if (-not $?) { throw 'Frontend build failed.' }
$env:CSC_IDENTITY_AUTO_DISCOVERY = 'false'
& npx electron-builder --win nsis --publish never
if (-not $?) { throw 'Application installer build failed.' }
if (Test-Path -LiteralPath $offline) { Remove-Item -LiteralPath $offline -Recurse -Force }
New-Item -ItemType Directory -Force -Path $offline | Out-Null
Copy-Item (Join-Path $release "COURTTRACE-Setup-$version.exe") $offline
Copy-Item (Join-Path $release "CourtTrace-Runtime-0.1.1.json") $offline
$manifest = Get-Content (Join-Path $release 'CourtTrace-Runtime-0.1.1.json') -Raw | ConvertFrom-Json
foreach ($part in $manifest.parts) { Copy-Item (Join-Path $release $part.name) $offline }
Copy-Item (Join-Path $root 'node_modules\7zip-bin\win\x64\7za.exe') (Join-Path $offline '7za.exe')
Copy-Item (Join-Path $root 'scripts\install-offline.ps1') $offline
Write-Host "Offline package created: $offline"
