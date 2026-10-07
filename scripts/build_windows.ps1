$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Version = (python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])").Trim()

python -m pip install --upgrade ".[desktop-build]"
python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --onedir `
  --name AscentCalculus `
  --collect-data ac.gui.static `
  --collect-all webview `
  --collect-all pythonnet `
  --collect-all clr_loader `
  --hidden-import clr `
  --hidden-import webview.platforms.edgechromium `
  --hidden-import webview.platforms.winforms `
  ac/gui/desktop.py

$Iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $Iscc)) {
  throw "Inno Setup 6 compiler not found at $Iscc"
}
& $Iscc "/DAppVersion=$Version" "scripts\windows-installer.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed with exit code $LASTEXITCODE" }

New-Item -ItemType Directory -Force "dist\AscentCalculus-windows-x64" | Out-Null
Move-Item -Force "dist\AscentCalculus-$Version-windows-x64-setup.exe" `
  "dist\AscentCalculus-windows-x64\AscentCalculus-$Version-windows-x64-setup.exe"
python -m pip wheel --no-deps . --wheel-dir "dist\AscentCalculus-windows-x64"
