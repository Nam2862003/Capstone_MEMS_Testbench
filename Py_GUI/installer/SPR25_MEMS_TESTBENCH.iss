#define MyAppName "SPR25 MEMS TESTBENCH"
#define MyAppExeName "SPR25_MEMS_TESTBENCH.exe"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "SPR25"

[Setup]
AppId={{B4D68DE8-3A6F-47E4-BE7D-130336065647}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\SPR25_MEMS_TESTBENCH
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\installer_output
OutputBaseFilename=SPR25_MEMS_TESTBENCH_Setup
SetupIconFile=..\assets\app_icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce

[Files]
Source: "..\dist\SPR25_MEMS_TESTBENCH\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
