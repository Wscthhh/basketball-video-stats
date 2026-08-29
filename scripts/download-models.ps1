$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$gdown = Join-Path $root '.venv\Scripts\gdown.exe'
$models = Join-Path $root 'models'

if (-not (Test-Path -LiteralPath $python)) {
  throw 'Python environment not found. Run .\start-backend.ps1 first.'
}
if (-not (Test-Path -LiteralPath $models)) {
  New-Item -ItemType Directory -Path $models | Out-Null
}

& $python -m pip install gdown==5.2.0

$downloads = @(
  @{ Id = '1KejdrcEnto2AKjdgdo1U1syr5gODp6EL'; Name = 'ball_detector_model.pt' },
  @{ Id = '1fVBLZtPy9Yu6Tf186oS4siotkioHBLHy'; Name = 'player_detector.pt' },
  @{ Id = '1nGoG-pUkSg4bWAUIeQ8aN6n7O1fOkXU0'; Name = 'court_keypoint_detector.pt' }
)

foreach ($download in $downloads) {
  $target = Join-Path $models $download.Name
  if (Test-Path -LiteralPath $target) {
    Write-Host "$($download.Name) already exists, skipping." -ForegroundColor DarkGray
    continue
  }
  & $gdown --fuzzy "https://drive.google.com/file/d/$($download.Id)/view?usp=sharing" -O $target
}

Write-Host 'COURTTRACE models are ready.' -ForegroundColor Green
