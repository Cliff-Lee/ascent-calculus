$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

python -m pip install --upgrade ".[desktop-build]"
python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --onedir `
  --name AscentCalculus `
  --collect-submodules tkinter `
  ac/gui/desktop.py

$PackagedExe = Join-Path $Root "dist\AscentCalculus\AscentCalculus.exe"
if (-not (Test-Path $PackagedExe)) { throw "Packaged Windows executable not found at $PackagedExe" }
$Smoke = Start-Process -FilePath $PackagedExe -ArgumentList "--startup-check" -Wait -PassThru
if ($Smoke.ExitCode -ne 0) { throw "Packaged Windows engine check failed: $($Smoke.ExitCode)" }
$WindowSmoke = Start-Process -FilePath $PackagedExe -ArgumentList "--window-smoke-check" -Wait -PassThru
if ($WindowSmoke.ExitCode -ne 0) { throw "Packaged Windows window check failed: $($WindowSmoke.ExitCode)" }

$Iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $Iscc)) {
  throw "Inno Setup 6 compiler not found at $Iscc"
}
& $Iscc "/DAppVersion=0.1.0a34" "scripts\windows-installer.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed with exit code $LASTEXITCODE" }

New-Item -ItemType Directory -Force "dist\AscentCalculus-windows-x64" | Out-Null
Move-Item -Force "dist\AscentCalculus-0.1.0a34-windows-x64-setup.exe" `
  "dist\AscentCalculus-windows-x64\AscentCalculus-0.1.0a34-windows-x64-setup.exe"
python -m pip wheel --no-deps . --wheel-dir "dist\AscentCalculus-windows-x64"
