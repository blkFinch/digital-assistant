# AI VTuber Dev Cockpit Startup Script
# Initialize venv and launch dev cockpit

param(
    [switch]$Fresh = $false
)

$ErrorActionPreference = 'Stop'

$projectRoot = $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($projectRoot)) {
    $projectRoot = (Get-Location).Path
}

$requirementsPath = Join-Path -Path $projectRoot -ChildPath "requirements.txt"
$devCockpitPath = Join-Path -Path (Join-Path -Path (Join-Path -Path $projectRoot -ChildPath "core_agent") -ChildPath "app") -ChildPath "dev_cockpit.py"

# Prefer an existing venv if present
$candidateVenvNames = @("venv", ".venv")
$venvPath = $null
foreach ($name in $candidateVenvNames) {
    $candidate = Join-Path -Path $projectRoot -ChildPath $name
    if (Test-Path -LiteralPath $candidate) {
        $venvPath = $candidate
        break
    }
}

# Default location if none exists
if ($null -eq $venvPath) {
    $venvPath = Join-Path -Path $projectRoot -ChildPath "venv"
}

Write-Host "AI VTuber Dev Cockpit Launcher" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

if ((Test-Path -LiteralPath $venvPath) -and $Fresh) {
    Write-Host "Removing existing venv..." -ForegroundColor Yellow
    Remove-Item -LiteralPath $venvPath -Recurse -Force
}

# Create venv if it doesn't exist
if (-not (Test-Path -LiteralPath $venvPath)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow

    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $pyLauncher) {
        & py -3 -m venv $venvPath
    } else {
        & python -m venv $venvPath
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create venv" -ForegroundColor Red
        exit 1
    }
    Write-Host "Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "Virtual environment already exists" -ForegroundColor Green
}

# Use venv python directly (more reliable than activation)
$venvPython = Join-Path -Path (Join-Path -Path $venvPath -ChildPath "Scripts") -ChildPath "python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "Could not find venv python at: $venvPython" -ForegroundColor Red
    exit 1
}

# Install requirements
Write-Host "Installing dependencies..." -ForegroundColor Yellow
& $venvPython -m pip install -r $requirementsPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install dependencies" -ForegroundColor Red
    exit 1
}
Write-Host "Dependencies installed" -ForegroundColor Green

# Launch dev cockpit
Write-Host ""
Write-Host "Launching Dev Cockpit..." -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

& $venvPython $devCockpitPath
