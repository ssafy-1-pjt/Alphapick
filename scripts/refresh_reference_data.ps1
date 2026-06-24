param(
    [double]$FinancialSleep = 0.18,
    [double]$NewsSleep = 0.25
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $projectRoot "backend"
$documentsRoot = Split-Path -Parent $projectRoot
$python = Get-ChildItem $documentsRoot -Directory |
    ForEach-Object { Join-Path $_.FullName "backend\.venv\Scripts\python.exe" } |
    Where-Object { Test-Path $_ } |
    Select-Object -First 1
if (-not $python) {
    throw "Django virtual environment was not found under the Documents workspace."
}

Push-Location $backend
try {
    & $python manage.py refresh_financials --market KOSPI --sleep $FinancialSleep
    & $python manage.py refresh_financials --market KOSDAQ --sleep $FinancialSleep
    & $python manage.py rebuild_v4_scores
    & $python manage.py refresh_news_sentiment --all --include-dart --display 30 --days 30 --disclosure-days 365 --sleep $NewsSleep
}
finally {
    Pop-Location
}
