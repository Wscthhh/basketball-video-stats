$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$stage = Join-Path $root 'release\runtime-stage'
$runtimeVersion = '0.1.1'
$archive = Join-Path $root "release\CourtTrace-Runtime-$runtimeVersion.zip"
$volumeBase = Join-Path $root "release\CourtTrace-Runtime-$runtimeVersion.7z"
$manifest = Join-Path $root "release\CourtTrace-Runtime-$runtimeVersion.json"
if (-not (Test-Path -LiteralPath (Join-Path $root 'release\backend\CourtTraceBackend\CourtTraceBackend.exe'))) { throw 'Run npm run desktop:prepare-runtime first.' }
if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Copy-Item -LiteralPath (Join-Path $root 'release\backend') -Destination $stage -Recurse
Copy-Item -LiteralPath (Join-Path $root 'release\ffmpeg') -Destination $stage -Recurse
Copy-Item -LiteralPath (Join-Path $root 'models') -Destination $stage -Recurse
@{ version = $runtimeVersion } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $stage 'version.json') -Encoding ASCII
if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
tar -a -c -f $archive -C $stage backend ffmpeg models
if (-not $?) { throw 'Runtime archive failed.' }
$sevenZip = Join-Path $root 'node_modules\7zip-bin\win\x64\7za.exe'
if (-not (Test-Path -LiteralPath $sevenZip)) { throw 'Missing 7za.' }
Get-ChildItem (Join-Path $root 'release') -Filter "CourtTrace-Runtime-$runtimeVersion.7z.*" -ErrorAction SilentlyContinue | Remove-Item -Force
& $sevenZip a "${volumeBase}" (Join-Path $stage '*') '-v1000m' '-mx=1' '-y'
if (-not $?) { throw 'Split runtime archive failed.' }
$parts = @(Get-ChildItem "$volumeBase.*" | Sort-Object Name | ForEach-Object { @{ index = [int]($_.Name.Split('.')[-1]); name = $_.Name; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLower() } })
@{ version = $runtimeVersion; parts = $parts } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifest -Encoding ASCII
Remove-Item -LiteralPath $archive -Force
Write-Host "Runtime split archives and manifest created in release."
