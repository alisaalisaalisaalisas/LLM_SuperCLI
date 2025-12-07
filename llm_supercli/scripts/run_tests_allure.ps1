# run_tests_allure.ps1
# Script to run pytest with Allure reporting and generate/view HTML reports

param(
    [switch]$SkipOpen,      # Skip opening the report in browser
    [switch]$CleanResults,  # Clean previous results before running
    [string]$TestPath = ""  # Optional: specific test path to run
)

$ErrorActionPreference = "Stop"

# Configuration
$ResultsDir = "allure-results"
$ReportDir = "allure-report"

Write-Host "=== Allure Test Runner ===" -ForegroundColor Cyan

# Clean previous results if requested
if ($CleanResults -and (Test-Path $ResultsDir)) {
    Write-Host "Cleaning previous results..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $ResultsDir
}

# Build pytest command
$pytestArgs = @("--alluredir=$ResultsDir")
if ($TestPath) {
    $pytestArgs += $TestPath
}

# Run pytest with Allure output
Write-Host "`nRunning pytest with Allure output..." -ForegroundColor Green
Write-Host "Command: pytest $($pytestArgs -join ' ')" -ForegroundColor Gray

try {
    pytest @pytestArgs
    $testExitCode = $LASTEXITCODE
} catch {
    Write-Host "Error running pytest: $_" -ForegroundColor Red
    exit 1
}

# Check if results were generated
if (-not (Test-Path $ResultsDir)) {
    Write-Host "Error: No Allure results generated. Check pytest output." -ForegroundColor Red
    exit 1
}

$resultFiles = Get-ChildItem -Path $ResultsDir -Filter "*-result.json" -ErrorAction SilentlyContinue
if ($resultFiles.Count -eq 0) {
    Write-Host "Warning: No test result files found in $ResultsDir" -ForegroundColor Yellow
}

Write-Host "`nAllure results generated in: $ResultsDir" -ForegroundColor Green

# Generate HTML report
Write-Host "`nGenerating Allure HTML report..." -ForegroundColor Green
try {
    allure generate $ResultsDir -o $ReportDir --clean
    Write-Host "Report generated in: $ReportDir" -ForegroundColor Green
} catch {
    Write-Host "Error generating report. Is Allure CLI installed?" -ForegroundColor Red
    Write-Host "Install with: scoop install allure (Windows) or brew install allure (macOS)" -ForegroundColor Yellow
    exit 1
}

# Open report in browser
if (-not $SkipOpen) {
    Write-Host "`nOpening report in browser..." -ForegroundColor Green
    try {
        allure open $ReportDir
    } catch {
        Write-Host "Error opening report: $_" -ForegroundColor Red
        Write-Host "You can manually open: $ReportDir/index.html" -ForegroundColor Yellow
    }
} else {
    Write-Host "`nSkipping browser open. View report at: $ReportDir/index.html" -ForegroundColor Yellow
}

Write-Host "`n=== Done ===" -ForegroundColor Cyan
exit $testExitCode
