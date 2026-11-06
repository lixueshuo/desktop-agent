[Setup]
AppName=Desktop Agent
AppVersion=1.0.0
DefaultDirName={localappdata}\Programs\DesktopAgent
DefaultGroupName=Desktop Agent
PrivilegesRequired=lowest
OutputDir=dist\installer
OutputBaseFilename=DesktopAgent-Setup-1.0.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "dist\DesktopAgent\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Desktop Agent"; Filename: "{app}\DesktopAgent.exe"
Name: "{autodesktop}\Desktop Agent"; Filename: "{app}\DesktopAgent.exe"

[Run]
Filename: "{app}\DesktopAgent.exe"; Description: "Open Desktop Agent"; Flags: nowait postinstall skipifsilent
