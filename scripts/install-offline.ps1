$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$manifestPath = Join-Path $root 'CourtTrace-Runtime-0.1.1.json'
$part = Join-Path $root 'CourtTrace-Runtime-0.1.1.7z.001'
$extractor = Join-Path $root '7za.exe'
$runtime = Join-Path $env:LOCALAPPDATA 'COURTTRACE\runtime'
$appInstaller = Get-ChildItem -LiteralPath $root -Filter 'COURTTRACE-Setup-*.exe' | Select-Object -First 1

if (-not $appInstaller -or -not (Test-Path -LiteralPath $manifestPath) -or -not (Test-Path -LiteralPath $part) -or -not (Test-Path -LiteralPath $extractor)) { throw '离线安装包不完整，请确认所有文件位于同一目录。' }
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
foreach ($item in $manifest.parts) {
  $file = Join-Path $root $item.name
  if (-not (Test-Path -LiteralPath $file)) { throw "缺少 Runtime 分卷：$($item.name)" }
  if ((Get-FileHash -Algorithm SHA256 -LiteralPath $file).Hash.ToLower() -ne $item.sha256.ToLower()) { throw "Runtime 分卷校验失败：$($item.name)" }
}

if (Test-Path -LiteralPath $runtime) { Remove-Item -LiteralPath $runtime -Recurse -Force }
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
& $extractor x $part "-o$runtime" -y
if (-not $?) { throw 'Runtime 解压失败。' }
$backend = Join-Path $runtime 'backend\CourtTraceBackend\CourtTraceBackend.exe'
if (-not (Test-Path -LiteralPath $backend)) { throw 'Runtime 解压后缺少后端文件。' }
Start-Process -FilePath 'netsh.exe' -ArgumentList "advfirewall firewall delete rule name=`"COURTTRACE Mobile Upload`"" -Verb RunAs -Wait -WindowStyle Hidden | Out-Null
Start-Process -FilePath 'netsh.exe' -ArgumentList "advfirewall firewall add rule name=`"COURTTRACE Mobile Upload`" dir=in action=allow program=`"$backend`" protocol=TCP localport=8000 profile=private,public enable=yes" -Verb RunAs -Wait -WindowStyle Hidden | Out-Null
Start-Process -FilePath $appInstaller.FullName -ArgumentList '/S' -Wait
Write-Host 'COURTTRACE 离线安装完成。Runtime、模型和应用已安装。' -ForegroundColor Green
