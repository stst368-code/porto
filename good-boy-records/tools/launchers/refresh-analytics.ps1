param(
    [string]$ReviewsRoot,
    [switch]$BuildSite,
    [switch]$ProfileAudio
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $repo
$configPath = Join-Path $repo 'data\analytics\local-config.json'
$dbPath = Join-Path $repo 'data\analytics.sqlite'
$exportPath = Join-Path $repo 'data\analytics'
if (-not $ReviewsRoot -and (Test-Path $configPath)) {
    $saved = Get-Content $configPath -Raw | ConvertFrom-Json
    $ReviewsRoot = $saved.reviewsRoot
}
if (-not $ReviewsRoot) {
    $ReviewsRoot = Read-Host 'Full path to your reviewed folder (containing good, above-average, average, below-average, bad)'
}
$ReviewsRoot = $ReviewsRoot.Trim('"')
if (-not (Test-Path -LiteralPath $ReviewsRoot -PathType Container)) { throw "Review root missing: $ReviewsRoot" }
$folders = @('good','above-average','average','below-average','bad')
foreach ($folder in $folders) {
    if (-not (Test-Path -LiteralPath (Join-Path $ReviewsRoot $folder) -PathType Container)) {
        throw "Required quality folder missing: $(Join-Path $ReviewsRoot $folder)"
    }
}
if (-not (Test-Path 'data\catalogue.json')) { throw 'Missing data\catalogue.json' }
New-Item -ItemType Directory -Force -Path $exportPath | Out-Null
@{reviewsRoot=$ReviewsRoot} | ConvertTo-Json | Set-Content -Path $configPath -Encoding UTF8
$python = Get-Command python -ErrorAction Stop
Write-Host '[GBR] Scanning quality folders...'
$profileArgs = @()
if ($ProfileAudio) { $profileArgs = @('--profile-missing') }
& $python.Source 'tools/analytics/analytics.py' scan --db $dbPath `
  --good (Join-Path $ReviewsRoot 'good') `
  --above-average (Join-Path $ReviewsRoot 'above-average') `
  --average (Join-Path $ReviewsRoot 'average') `
  --below-average (Join-Path $ReviewsRoot 'below-average') `
  --bad (Join-Path $ReviewsRoot 'bad') `
  --catalogue 'data/catalogue.json' @profileArgs
if ($LASTEXITCODE -ne 0) { throw 'Scan failed; export not run.' }
Write-Host '[GBR] Exporting research data...'
& $python.Source 'tools/analytics/analytics.py' export --db $dbPath --output $exportPath
if ($LASTEXITCODE -ne 0) { throw 'Export failed.' }
@'
import json, pathlib, sqlite3
p=pathlib.Path('data/analytics/generations.json')
obj=json.loads(p.read_text(encoding='utf-8'))
with sqlite3.connect('data/analytics.sqlite') as db:
    count=db.execute('SELECT COUNT(*) FROM generations').fetchone()[0]
assert count>0, 'Database has no generations; refusing to accept an empty export.'
assert obj['count']==count==len(obj['generations']), 'Export count mismatch.'
print(f'[GBR] Verified {count} database and published research records.')
'@ | & $python.Source -
if ($LASTEXITCODE -ne 0) { throw 'Validation failed.' }
if ($BuildSite) {
    Write-Host '[GBR] Building website...'
    & (Join-Path $repo 'tools\launchers\build-site.bat')
    if ($LASTEXITCODE -ne 0) { throw 'Website build failed.' }
}
Write-Host '[GBR] Complete. Local dashboard: http://localhost:8000/analytics/'
Write-Host '[GBR] Built preview: http://localhost:8000/_site/analytics/ (after -BuildSite)'
