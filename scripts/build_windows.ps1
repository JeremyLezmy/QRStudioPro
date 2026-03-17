param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$iconPng = "assets/app_icon.png"
$iconIco = "assets/app_icon.ico"

if ((Test-Path $iconPng) -and -not (Test-Path $iconIco)) {
    & $PythonExe scripts/make_icons.py --source $iconPng --ico $iconIco
}

$args = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name", "QRStudioPro",
    "--collect-all", "customtkinter",
    "--collect-all", "tkinterdnd2",
    "--add-data", "assets;assets",
    "--add-data", "logo_phusis.png;.",
    "qr_gui.py"
)

if (Test-Path $iconIco) {
    $args += @("--icon", $iconIco)
}

& $PythonExe @args

Write-Host ""
Write-Host "Build terminé."
Write-Host "Executable: dist/QRStudioPro/QRStudioPro.exe"
