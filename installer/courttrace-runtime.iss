#define AppName "COURTTRACE Runtime"
#define AppVersion "0.1.1"
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
PrivilegesRequired=admin
Compression=lzma2/fast
SolidCompression=no
WizardStyle=modern
Uninstallable=no

[Files]
Source: "{#SourceRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Run]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""COURTTRACE Mobile Upload"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""COURTTRACE Mobile Upload"" dir=in action=allow program=""{app}\backend\CourtTraceBackend\CourtTraceBackend.exe"" protocol=TCP localport=8000 profile=private,public enable=yes"; Flags: runhidden waituntilterminated
