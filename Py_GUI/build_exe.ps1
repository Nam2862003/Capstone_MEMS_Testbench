$ErrorActionPreference = "Stop"

$AppName = "SPR25_MEMS_TESTBENCH"
$Python = "python"

Write-Host "Creating virtual environment..."
& $Python -m venv .venv

Write-Host "Installing dependencies..."
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "Removing old build outputs..."
if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist) { Remove-Item dist -Recurse -Force }

Write-Host "Building EXE..."
& .\.venv\Scripts\python.exe -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --icon "assets\app_icon.ico" `
    --name $AppName `
    --add-data "assets;assets" `
    main.py

Write-Host ""
Write-Host "Build complete:"
Write-Host "  dist\$AppName\$AppName.exe"
Write-Host ""
Write-Host "Zip and share the whole dist\$AppName folder, not just the exe."
