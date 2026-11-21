; TRÇeviri kurulum dosyası (Inno Setup 6). Derleme:  ISCC /DDistDir=<PyInstaller dist\TRCeviri> /DAppVer=2.1.0 TRCeviri.iss
#ifndef AppVer
  #define AppVer "2.1.0"
#endif
#ifndef DistDir
  #define DistDir "..\dist\TRCeviri"
#endif

[Setup]
AppId={{6C1F4E7A-2B8D-4E61-9A3F-7D2C5B8E9A10}
AppName=Brolis Game Translate
AppVersion={#AppVer}
AppVerName=Brolis Game Translate {#AppVer}
AppPublisher=Brolis
DefaultDirName={localappdata}\Programs\TRCeviri
DefaultGroupName=Brolis Game Translate
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=TRCeviri-Kurulum
OutputDir=out
SetupIconFile=TRCeviri.ico
UninstallDisplayIcon={app}\TRCeviri.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "tr"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstüne kısayol oluştur"; GroupDescription: "Kısayollar:"
Name: "startup"; Description: "Windows açılınca Brolis Game Translate'i başlat ve canlı çeviriyi aç"; GroupDescription: "Başlangıç:"; Flags: unchecked

[InstallDelete]
; eski adla oluşturulmuş kısayolları kaldır
Type: files; Name: "{userdesktop}\TRÇeviri.lnk"
Type: files; Name: "{userprograms}\TRÇeviri.lnk"
Type: files; Name: "{userstartup}\TRÇeviri.lnk"

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\Brolis Game Translate"; Filename: "{app}\TRCeviri.exe"
Name: "{userdesktop}\Brolis Game Translate"; Filename: "{app}\TRCeviri.exe"; Tasks: desktopicon
Name: "{userstartup}\Brolis Game Translate"; Filename: "{app}\TRCeviri.exe"; Parameters: "--baslat"; Tasks: startup

[Run]
; Not: 'skipifsilent' yok — otomatik güncelleme (/SILENT) bitince uygulama kendiliğinden yeniden açılır.
Filename: "{app}\TRCeviri.exe"; Description: "Brolis Game Translate'i şimdi başlat"; Flags: nowait postinstall
