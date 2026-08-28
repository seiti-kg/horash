; horash_setup_offline.iss - setup full offline para horash
; gera horash_setup_offline.exe (~400mb) com clamav + yara ja dentro
; requer: tools/bootstrap.ps1 ja rodado (pastas clamav/ yara/ existem) + pyinstaller horash.spec com HORASH_OFFLINE=1
; build via: set HORASH_OFFLINE=1 & pyinstaller horash.spec -> dist/horash.exe (com bundle), depois iscc

#define MyAppName "horash"
#define MyAppVersion "0.2.2"
#define MyAppPublisher "horash"
#define MyAppURL "https://github.com/seiti-kg/horash"

[Setup]
AppId={{horash-offline}}
AppName={#MyAppName} (offline)
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=horash_setup_offline
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern
SetupIconFile=..\web\favicon.ico
UninstallDisplayIcon={app}\horash.exe
DisableDirPage=no
DisableProgramGroupPage=yes
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Components]
Name: "core"; Description: "horash (obrigatorio)"; Types: full compact custom; Flags: fixed
Name: "yara"; Description: "YARA regras (ja incluso)"; Types: full; Flags: fixed
Name: "clamav"; Description: "ClamAV + banco (ja incluso, ~300 MB)"; Types: full; Flags: fixed

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; horash.exe offline ja contem clamav/ yara/ via HORASH_OFFLINE=1, mas tambem instalamos separado para atualizar via freshclam
Source: "..\dist\horash.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: core
Source: "..\clamav\*"; DestDir: "{app}\clamav"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: clamav
Source: "..\yara\*"; DestDir: "{app}\yara"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: yara
Source: "bootstrap.ps1"; DestDir: "{app}\tools"; Flags: ignoreversion; Components: core
Source: "..\web\favicon.ico"; DestDir: "{app}\web"; Flags: ignoreversion; Components: core
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion; Components: core
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion; Components: core

[Icons]
Name: "{group}\horash"; Filename: "{app}\horash.exe"; IconFilename: "{app}\web\favicon.ico"; Components: core
Name: "{group}\{cm:UninstallProgram,horash}"; Filename: "{uninstallexe}"; Components: core
Name: "{autodesktop}\horash"; Filename: "{app}\horash.exe"; IconFilename: "{app}\web\favicon.ico"; Tasks: desktopicon; Components: core

[Run]
Filename: "{app}\horash.exe"; Description: "{cm:LaunchProgram,horash}"; Flags: nowait postinstall skipifsilent
