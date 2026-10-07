#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" || "$(dpkg --print-architecture)" != "amd64" ]]; then
  echo "Build the Ubuntu .deb on Ubuntu 24.04 x86_64." >&2
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SYSTEM_PYTHON=/usr/bin/python3
OUT="$ROOT/dist/AscentCalculus-ubuntu-24.04-amd64"
STAGE="$ROOT/build/deb-root"
rm -rf "$STAGE" "$OUT"
mkdir -p "$STAGE/DEBIAN" "$STAGE/usr/lib/ascent-calculus" \
  "$STAGE/usr/share/applications" "$STAGE/usr/bin" "$OUT"

cp -R ac "$STAGE/usr/lib/ascent-calculus/ac"

cat > "$STAGE/DEBIAN/control" <<'EOF'
Package: ascent-calculus
Version: 0.1.0a21
Section: science
Priority: optional
Architecture: amd64
Depends: python3 (>= 3.11), python3-tk
Maintainer: Cliff Lee
Description: Alpha research workbench for ascent sequences
 Visual workbench and Python calculus for exploring ascent sequences,
 transformations, and bounded conjecture checks.
EOF

cat > "$STAGE/usr/bin/ascent-calculus" <<'EOF'
#!/bin/sh
export PYTHONPATH="/usr/lib/ascent-calculus${PYTHONPATH:+:$PYTHONPATH}"
exec /usr/bin/python3 -m ac.gui.desktop "$@"
EOF
chmod 0755 "$STAGE/usr/bin/ascent-calculus"

cat > "$STAGE/usr/share/applications/ascent-calculus.desktop" <<'EOF'
[Desktop Entry]
Name=Ascent Calculus
Comment=Alpha research workbench for ascent sequences
Exec=ascent-calculus
Terminal=false
Type=Application
Categories=Science;Math;
EOF

dpkg-deb --root-owner-group --build "$STAGE" "$OUT/ascent-calculus_0.1.0a21_amd64.deb"
python3 -m pip wheel --no-deps . --wheel-dir "$OUT"
echo "Created release artifacts in $OUT"
