param(
    [switch]$Apply,
    [switch]$CleanGenerated
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Gbr = Join-Path $Root 'good-boy-records'

if (-not (Test-Path $Gbr)) {
    throw "good-boy-records was not found under $Root. Run this script from the porto root."
}

$LegacyRelative = @(
    'good-boy-records\APPLY-CENTRAL-WHEEL.bat',
    'good-boy-records\APPLY-CONVEYOR-LAYOUT.bat',
    'good-boy-records\APPLY-SOURCE-CLEANUP.bat',
    'good-boy-records\REBUILD-DENSE-GENRE-WALL.bat',
    'good-boy-records\BUILD-SPEC-REVIEW-v11.md',
    'good-boy-records\BUILD-SPEC-v11.md',
    'good-boy-records\CHROMIUM-QA-v11.13.json',
    'good-boy-records\RELEASE-v11.13.md',
    'good-boy-records\RESPONSIVE-QA-v11.13.md',
    'good-boy-records\README-CONVEYOR-LAYOUT.md',
    'good-boy-records\README-CONVEYOR-REFINEMENT.md',
    'good-boy-records\README-COVER-WALL-LAYOUT.md',
    'good-boy-records\README-DENSE-GENRE-WALL-FILL.md',
    'good-boy-records\README-DENSE-GENRE-WALL.md',
    'good-boy-records\README-FULL-BLEED-WALL.md',
    'good-boy-records\.github',
    'good-boy-records\tools\__pycache__'
)

$Targets = foreach ($rel in $LegacyRelative) {
    $p = Join-Path $Root $rel
    if (Test-Path -LiteralPath $p) { $p }
}

# Any additional Python cache folders / pyc files under GBR are generated junk.
$Targets += Get-ChildItem -LiteralPath $Gbr -Recurse -Force -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue | ForEach-Object FullName
$Targets += Get-ChildItem -LiteralPath $Gbr -Recurse -Force -File -Filter '*.pyc' -ErrorAction SilentlyContinue | ForEach-Object FullName

if ($CleanGenerated) {
    $site = Join-Path $Gbr '_site'
    if (Test-Path $site) { $Targets += $site }
    $pages = Join-Path $Root '_pages'
    if (Test-Path $pages) { $Targets += $pages }
}

$Targets = $Targets | Sort-Object -Unique

Write-Host "PORTO / GBR legacy cleanup" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host "Mode: $($(if ($Apply) {'APPLY'} else {'PREVIEW'}))"
if ($CleanGenerated) { Write-Host 'Generated output (_site/_pages) is included.' -ForegroundColor Yellow }
Write-Host ''

if (-not $Targets) {
    Write-Host 'Nothing matched the conservative legacy list.' -ForegroundColor Green
    exit 0
}

foreach ($path in $Targets) {
    $rel = $path.Substring($Root.Length).TrimStart('\')
    if ($Apply) {
        Remove-Item -LiteralPath $path -Recurse -Force
        Write-Host "REMOVED  $rel" -ForegroundColor DarkYellow
    } else {
        Write-Host "WOULD REMOVE  $rel"
    }
}

Write-Host ''
if (-not $Apply) {
    Write-Host 'Preview only. Re-run with -Apply to remove these files.' -ForegroundColor Cyan
    Write-Host 'For a completely fresh generated build: .\CLEAN-PORTO-LEGACY.ps1 -Apply -CleanGenerated'
} else {
    Write-Host 'Cleanup complete.' -ForegroundColor Green
}
