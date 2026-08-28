; horash_setup.iss - setup leve (online) para horash
; gera horash_setup.exe (~12mb) que instala horash.exe leve + baixa engines sob demanda
; requer Inno Setup 6: iscc tools/horash_setup.iss
; build via: pyinstaller horash.spec -> dist/horash.exe, depois iscc

#define MyAppName "horash"
#define MyAppVersion "0.2.3"
#define MyAppPublisher "horash"
#define MyAppURL "https://github.com/seiti-kg/horash"

[Setup]
AppId={{horash}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=horash_setup
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
Name: "yara"; Description: "YARA regras (7 MB, recomendado)"; Types: full; ExtraDiskSpaceRequired: 7340032
Name: "clamav"; Description: "ClamAV + banco (~300 MB, recomendado para >650MB)"; Types: full; ExtraDiskSpaceRequired: 314572800

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; core - exe leve ja contem web/ e src/ via pyinstaller
Source: "..\dist\horash.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: core
Source: "bootstrap.ps1"; DestDir: "{app}\tools"; Flags: ignoreversion; Components: core
Source: "install_clamav.ps1"; DestDir: "{app}\tools"; Flags: ignoreversion; Components: clamav
Source: "install_yara.ps1"; DestDir: "{app}\tools"; Flags: ignoreversion; Components: yara
Source: "fix_yara.py"; DestDir: "{app}\tools"; Flags: ignoreversion; Components: yara
Source: "..\web\favicon.ico"; DestDir: "{app}\web"; Flags: ignoreversion; Components: core
; docs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion; Components: core
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion; Components: core

[Icons]
Name: "{group}\horash"; Filename: "{app}\horash.exe"; IconFilename: "{app}\web\favicon.ico"; Components: core
Name: "{group}\{cm:UninstallProgram,horash}"; Filename: "{uninstallexe}"; Components: core
Name: "{autodesktop}\horash"; Filename: "{app}\horash.exe"; IconFilename: "{app}\web\favicon.ico"; Tasks: desktopicon; Components: core

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\tools\bootstrap.ps1"" {code:GetBootstrapArgs}"; StatusMsg: "Baixando proteções (ClamAV/YARA)..."; Flags: waituntilterminated; Components: yara clamav
Filename: "{app}\horash.exe"; Description: "{cm:LaunchProgram,horash}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\clamav"
Type: filesandordirs; Name: "{app}\yara"

[Code]
function GetBootstrapArgs(Param: String): String;
var
  Args: String;
begin
  Args := '';
  if not IsComponentSelected('clamav') then Args := Args + ' -no-clamav';
  if not IsComponentSelected('yara') then Args := Args + ' -no-yara';
  Result := Args;
end;

function InitializeUninstall(): Boolean;
begin
  Result := True;
end;
