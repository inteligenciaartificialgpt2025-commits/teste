; ================================================================
; Instalador Inno Setup para Automacao de Janelas
; Compile este arquivo com o Inno Setup Compiler apos executar
; build_exe.bat. O instalador final sera criado na pasta installer.
; ================================================================

#define MyAppName "Automação de Janelas"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Publisher Genérico"
#define MyAppExeName "AutomacaoJanelas.exe"
#define MyBuildDir "dist\AutomacaoJanelas"
#define MyIconFile "assets\app.ico"

[Setup]
AppId={{8C2AE4EF-4F6C-4C78-9D9E-2B987F7C0A49}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Automacao Janelas
DefaultGroupName={#MyAppName}
OutputDir=installer
OutputBaseFilename=AutomacaoJanelasSetup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
#ifdef MyIconFile
#ifexist MyIconFile
SetupIconFile={#MyIconFile}
#endif
#endif

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos:"; Flags: checkedonce

[Files]
; Instala todo o pacote one-folder gerado pelo PyInstaller, incluindo DLLs e dependencias.
Source: "{#MyBuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Atalho no Menu Iniciar.
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
; Atalho opcional na Área de Trabalho.
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
; Atalho para desinstalar no Menu Iniciar.
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Executar {#MyAppName}"; Flags: nowait postinstall skipifsilent
