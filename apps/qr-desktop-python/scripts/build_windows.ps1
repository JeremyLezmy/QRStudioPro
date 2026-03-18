param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$sharedAssets = (Resolve-Path (Join-Path $ProjectRoot "..\..\shared\assets")).Path
$iconPng = Join-Path $sharedAssets "app_icon.png"
$iconIco = Join-Path $sharedAssets "app_icon.ico"

if (Test-Path $iconPng) {
    & $PythonExe scripts/make_icons.py --source $iconPng --ico $iconIco
}

$args = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--windowed",
    "--onefile",
    "--name", "QRStudioPro",
    "--collect-all", "customtkinter",
    "--collect-all", "tkinterdnd2",
    "--add-data", "$sharedAssets;assets",
    "qr_gui.py"
)

if (Test-Path $iconIco) {
    $args += @("--icon", $iconIco)
}

& $PythonExe @args

Write-Host ""
Write-Host "Build terminé."
Write-Host "Executable: dist/QRStudioPro.exe"
