#!/usr/bin/env bash
set -euo pipefail

VERSION="0.3.0"
APP_NAME="PrintBoard"
OUT_APPIMAGE="${APP_NAME}-${VERSION}-x86_64.AppImage"

echo "[1/4] Installing PyInstaller & building bundle..."
uv run --with pyinstaller --with PySide6 pyinstaller \
    --noconfirm \
    --onedir \
    --windowed \
    --name "$APP_NAME" \
    --add-data "printboard/icon.svg:printboard" \
    --add-data "printboard/web:printboard/web" \
    printboard_entry.py

echo "[2/4] Preparing AppDir..."
rm -rf AppDir
mkdir -p AppDir/usr/bin
cp -a "dist/${APP_NAME}/." AppDir/usr/bin/

cat > AppDir/AppRun <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/PrintBoard" "$@"
EOF
chmod +x AppDir/AppRun

cp data/printboard.desktop AppDir/printboard.desktop
sed -i 's/^Exec=.*/Exec=PrintBoard/' AppDir/printboard.desktop
cp data/printboard.svg AppDir/printboard.svg
ln -sf printboard.svg AppDir/.DirIcon

echo "[3/4] Fetching appimagetool..."
APPIMAGETOOL="/tmp/appimagetool-x86_64.AppImage"
if [ ! -x "$APPIMAGETOOL" ]; then
    curl -fSL -o "$APPIMAGETOOL" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$APPIMAGETOOL"
fi

echo "[4/4] Packaging ${OUT_APPIMAGE}..."
ARCH=x86_64 "$APPIMAGETOOL" --appimage-extract-and-run AppDir "$OUT_APPIMAGE"
ls -lh "$OUT_APPIMAGE"
