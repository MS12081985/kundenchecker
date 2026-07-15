#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
[ -x "$PYTHON" ] || { echo "Fehler: .venv-Python nicht gefunden." >&2; exit 1; }
VERSION=$("$PYTHON" -c 'from config.app_config import AppConfig; print(AppConfig.VERSION)')
"$PYTHON" -m PyInstaller --version >/dev/null || { echo "Fehler: PyInstaller fehlt. requirements-dev.txt installieren." >&2; exit 1; }
rm -rf build dist
mkdir -p release
"$PYTHON" -m PyInstaller --noconfirm KundenChecker.spec
[ -d dist/KundenChecker.app ] || { echo "Fehler: App-Bundle fehlt." >&2; exit 1; }
rm -rf release/dmg-root
mkdir -p release/dmg-root
cp -R dist/KundenChecker.app release/dmg-root/
ln -s /Applications release/dmg-root/Applications
hdiutil create -volname "KundenChecker-$VERSION" -srcfolder release/dmg-root -ov -format UDZO "release/KundenChecker-$VERSION.dmg"
rm -rf release/dmg-root
echo "App: dist/KundenChecker.app"
echo "DMG: release/KundenChecker-$VERSION.dmg"
shasum -a 256 "release/KundenChecker-$VERSION.dmg"
