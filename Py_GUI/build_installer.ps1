$ErrorActionPreference = "Stop"

$InnoScript = "installer\SPR25_MEMS_TESTBENCH.iss"
$IsccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)

$Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $Iscc) {
    throw "Inno Setup compiler not found. Install Inno Setup 6, or open $InnoScript manually in Inno Setup and click Compile."
}

if (-not (Test-Path "dist\SPR25_MEMS_TESTBENCH\SPR25_MEMS_TESTBENCH.exe")) {
    throw "Build the app first with .\build_exe.ps1"
}

Write-Host "Building installer..."
& $Iscc $InnoScript

Write-Host ""
Write-Host "Installer complete:"
Write-Host "  installer_output\SPR25_MEMS_TESTBENCH_Setup.exe"
