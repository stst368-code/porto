param([switch]$Apply)
$ErrorActionPreference = 'Stop'
$Gbr = Split-Path -Parent $MyInvocation.MyCommand.Path
$Repo = Split-Path -Parent $Gbr
$GitIgnore = Join-Path $Repo '.gitignore'
$Pattern = 'good-boy-records/showcase/'

Write-Host "Good Boy Records external-showcase migration"
Write-Host "Repository: $Repo"
Write-Host "Showcase:   $(Join-Path $Gbr 'showcase')"
Write-Host ""

if (-not $Apply) {
    Write-Host "PREVIEW ONLY"
    Write-Host "Would add to .gitignore: $Pattern"
    Write-Host "Would run: git rm --cached -r --ignore-unmatch -- good-boy-records/showcase"
    Write-Host ""
    Write-Host "Run again with -Apply only AFTER UPLOAD-SHOWCASE-R2.bat passes rclone check."
    exit 0
}

if (-not (Test-Path $GitIgnore)) { New-Item -ItemType File -Path $GitIgnore | Out-Null }
$lines = Get-Content -LiteralPath $GitIgnore -ErrorAction SilentlyContinue
if ($lines -notcontains $Pattern) { Add-Content -LiteralPath $GitIgnore -Value $Pattern }

Push-Location $Repo
try {
    git rm --cached -r --ignore-unmatch -- good-boy-records/showcase
    Write-Host ""
    Write-Host "showcase/ is now ignored and untracked. Local files were NOT deleted."
    Write-Host "Review git status, then commit the catalogue/config/workflow changes."
} finally { Pop-Location }
