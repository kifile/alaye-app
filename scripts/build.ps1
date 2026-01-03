#!/usr/bin/env pwsh

# Build script for pywebview application using Nuitka
# This script compiles main.py into a standalone Windows executable

Write-Host "Building pywebview application with Nuitka..." -ForegroundColor Green
Write-Host ""

# Check if nuitka is installed
try {
    python -c "import nuitka" 2>$null
} catch {
    Write-Host "Error: Nuitka is not installed. Please install it first:" -ForegroundColor Red
    Write-Host "  pip install nuitka" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if main.py exists
$mainPyPath = "main.py"
if (-not (Test-Path $mainPyPath)) {
    Write-Host "Error: main.py not found. Please run this script from the project root directory." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Create build directory if it doesn't exist
$buildDir = "build"
if (-not (Test-Path $buildDir)) {
    New-Item -ItemType Directory -Path $buildDir | Out-Null
}

Write-Host "Building frontend resources..." -ForegroundColor Cyan
Write-Host "Output will be saved to: frontend\out" -ForegroundColor Cyan
Write-Host ""

# Build frontend resources
try {
    Push-Location "frontend"
    & npm run build

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Frontend build failed! Please check the error messages above." -ForegroundColor Red
        Pop-Location
        Read-Host "Press Enter to exit"
        exit 1
    }
    Pop-Location

    Write-Host "Frontend build completed successfully!" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host ""
    Write-Host "Frontend build failed with exception: $($_.Exception.Message)" -ForegroundColor Red
    Pop-Location
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Starting Nuitka compilation..." -ForegroundColor Cyan
Write-Host "Output will be saved to: build\main.exe" -ForegroundColor Cyan
Write-Host ""

# Nuitka command
$nuitkaArgs = @(
    "--onefile",
    "--windows-console-mode=disable",
    "--output-dir=build",
    "--remove-output",
    "--assume-yes-for-downloads",
    "--enable-plugin=pywebview",
    "--include-data-dir=frontend/out=frontend/out",
    "--windows-icon-from-ico=assets/icon.ico",
    "main.py"
)

try {
    & nuitka @nuitkaArgs

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "Build completed successfully!" -ForegroundColor Green
        Write-Host "Executable location: build\main.exe" -ForegroundColor Green
        Write-Host ""
        Write-Host "To run the application:" -ForegroundColor Cyan
        Write-Host "  build\main.exe" -ForegroundColor Yellow
    } else {
        Write-Host ""
        Write-Host "Build failed! Please check the error messages above." -ForegroundColor Red
        exit $LASTEXITCODE
    }
} catch {
    Write-Host ""
    Write-Host "Build failed with exception: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Read-Host "Press Enter to exit"