#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Build the macOS app on a Mac so Python and native frameworks match the target." >&2
  exit 2
fi

ARCH="$(uname -m)"
if [[ "$ARCH" != "arm64" && "$ARCH" != "x86_64" ]]; then
  echo "Unsupported macOS architecture: $ARCH" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VERSION="$(python3 -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')"
python3 -m pip install --upgrade '.[desktop-build]'
python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --onedir \
  --name AscentCalculus \
  --osx-bundle-identifier org.cliffpackman.ascentcalculus \
  --collect-data ac.gui.static \
  --hidden-import webview.platforms.cocoa \
  ac/gui/desktop.py

OUT="dist/AscentCalculus-macos-${ARCH}"
mkdir -p "$OUT"
python3 -m pip wheel --no-deps . --wheel-dir "$OUT"
hdiutil create \
  -volname "Ascent Calculus Alpha" \
  -srcfolder dist/AscentCalculus.app \
  -ov -format UDZO \
  "$OUT/AscentCalculus-${VERSION}-macos-${ARCH}.dmg"
ditto -c -k --sequesterRsrc --keepParent \
  dist/AscentCalculus.app \
  "$OUT/AscentCalculus-${VERSION}-macos-${ARCH}.zip"
echo "Created release artifacts in $OUT"
