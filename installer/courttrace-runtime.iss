#define AppName "COURTTRACE Runtime"
#define AppVersion "0.1.0"
#define AppPublisher "COURTTRACE"
#define SourceRoot "..\release\runtime-stage"

[Setup]
AppId={{B81598C5-65E2-4D89-8E2A-2E2BD0D3EABD}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\COURTTRACE\runtime
OutputDir=..\release
OutputBaseFilename=COURTTRACE-Runtime-Setup-{#AppVersion}
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
Compression=lzma2/fast
SolidCompression=no
WizardStyle=modern
Uninstallable=no

[Files]
Source: "{#SourceRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
