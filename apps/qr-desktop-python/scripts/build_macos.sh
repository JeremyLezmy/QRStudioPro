#!/usr/bin/env bash
set -euo pipefail

PYTHON_EXE="${PYTHON_EXE:-python3}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

SHARED_ASSETS="$PROJECT_ROOT/../../shared/assets"
ICON_PNG="$SHARED_ASSETS/app_icon.png"
ICON_ICNS="$SHARED_ASSETS/app_icon.icns"

if [[ -f "$ICON_PNG" ]]; then
  "$PYTHON_EXE" scripts/make_icons.py --source "$ICON_PNG" --icns "$ICON_ICNS"
fi

ARGS=(
  -m PyInstaller
  --noconfirm
  --clean
  --windowed
  --name QRStudioPro
  --collect-all customtkinter
  --collect-all tkinterdnd2
  --add-data "$SHARED_ASSETS:assets"
  --osx-bundle-identifier "com.phusis.qrstudiopro"
  qr_gui.py
)

if [[ -f "$ICON_ICNS" ]]; then
  ARGS+=(--icon "$ICON_ICNS")
fi

"$PYTHON_EXE" "${ARGS[@]}"

DMG_PATH="dist/QRStudioPro-macos.dmg"
hdiutil create \
  -volname "QRStudioPro" \
  -srcfolder "dist/QRStudioPro.app" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

echo ""
echo "Build termine."
echo "Application: dist/QRStudioPro.app"
echo "DMG: $DMG_PATH"
