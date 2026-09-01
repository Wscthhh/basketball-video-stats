#define AppName "COURTTRACE"
#define AppVersion "0.1.0"
#define AppPublisher "COURTTRACE"
#define AppExeName "COURTTRACE.exe"
#define SourceRoot "..\release\win-unpacked"

[Setup]
AppId={{6A4C36BE-74D8-5BEA-9DAB-89BBF199C065}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
OutputDir=..\release
OutputBaseFilename=COURTTRACE-Setup-{#AppVersion}
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
Compression=lzma2/fast
SolidCompression=no
WizardStyle=modern
UninstallDisplayName={#AppName} {#AppVersion}
Uninstallable=yes

[Files]
Source: "{#SourceRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
