param(
    [string]$ReviewsRoot,
    [switch]$BuildSite,
    [switch]$ProfileAudio,
    [string]$TimingsCsv,
    [string]$PerformanceSummaryCsv
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
    $ReviewsRoot = Read-Host 'Full path to your reviewed folder (containing good, above-average, average, below-average, bad, unlistenable)'
}
$ReviewsRoot = $ReviewsRoot.Trim('"')
if (-not (Test-Path -LiteralPath $ReviewsRoot -PathType Container)) { throw "Review root missing: $ReviewsRoot" }
$folders = @('good','above-average','average','below-average','bad','unlistenable')
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
  --unlistenable (Join-Path $ReviewsRoot 'unlistenable') `
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
# Optional telemetry bridge. Preserve research export if timing logs are absent.
if (-not $TimingsCsv) {
    $candidates = @(
        (Join-Path $repo 'generation_timings.csv'),
        (Join-Path $repo 'data\generation_timings.csv')
    )
    foreach ($c in $candidates) { if (Test-Path -LiteralPath $c) { $TimingsCsv = $c; break } }
}
if ($TimingsCsv) {
    if (-not (Test-Path -LiteralPath $TimingsCsv -PathType Leaf)) { throw "Timing CSV not found: $TimingsCsv" }
    $costArgs = @('tools/analytics/cost_import.py', '--timings', $TimingsCsv,
       '--generations', (Join-Path $exportPath 'generations.json'),
       '--output', (Join-Path $exportPath 'cost-analysis.json'))
    if ($PerformanceSummaryCsv) { $costArgs += @('--summary', $PerformanceSummaryCsv) }
    Write-Host '[GBR] Importing pod cost telemetry...'
    & $python.Source @costArgs
    if ($LASTEXITCODE -ne 0) { throw 'Cost telemetry import failed. Existing ratings export is preserved.' }
} else {
    Write-Warning 'No generation_timings.csv discovered. Supply -TimingsCsv path to enable cost metrics.'
}
if ($BuildSite) {
    Write-Host '[GBR] Building website...'
    & (Join-Path $repo 'tools\launchers\build-site.bat')
    if ($LASTEXITCODE -ne 0) { throw 'Website build failed.' }
}
Write-Host '[GBR] Complete. Local dashboard: http://localhost:8000/analytics/'
Write-Host '[GBR] Built preview: http://localhost:8000/_site/analytics/ (after -BuildSite)'
