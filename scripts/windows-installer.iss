#ifndef AppVersion
  #define AppVersion "0.1.0a21"
#endif

[Setup]
AppId={{7B85C912-44C5-4A47-9B73-2C9A1348A4CC}
AppName=Ascent Calculus
AppVersion={#AppVersion}
AppPublisher=Cliff Lee
DefaultDirName={localappdata}\Programs\Ascent Calculus
DefaultGroupName=Ascent Calculus
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=AscentCalculus-{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\AscentCalculus.exe

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\AscentCalculus\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Ascent Calculus"; Filename: "{app}\AscentCalculus.exe"
Name: "{autodesktop}\Ascent Calculus"; Filename: "{app}\AscentCalculus.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AscentCalculus.exe"; Description: "Launch Ascent Calculus"; Flags: postinstall nowait skipifsilent
