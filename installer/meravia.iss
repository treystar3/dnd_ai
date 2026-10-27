; Inno Setup 6.1+ script. Build with build_installer.bat.
; Installs the game for the current user (no administrator needed), adds shortcuts, and offers to install Ollama (and Microsoft's WebView2
; window component) when they are missing. The AI model itself is downloaded by the game on first launch, with a progress bar.

#define AppName "Meravia"
#define AppExe "Meravia.exe"
#ifndef AppVersion
  #define AppVersion "0.0.1"
#endif

[Setup]
AppId={{6F0B5C0E-6B3D-4F55-9C77-5E0D3A0D1A11}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
OutputBaseFilename=Meravia_{#AppVersion}_setup
OutputDir=Output
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExe}

[Tasks]
Name: "ollama"; Description: "Install Ollama, the free local AI program the game needs (about 1 GB; skipped if you already have it)"; Check: not OllamaInstalled
Name: "desktopicon"; Description: "Add a desktop shortcut"; Flags: unchecked

[Files]
Source: "..\dist\Meravia\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{tmp}\OllamaSetup.exe"; Parameters: "/SILENT /NORESTART"; StatusMsg: "Installing Ollama (Windows may ask for permission)..."; Check: HaveOllamaSetup
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Installing the window component..."; Check: HaveWebView2Setup
Filename: "{app}\{#AppExe}"; Flags: nowait; Check: WizardSilent
Filename: "{app}\{#AppExe}"; Description: "Start the game (it will download its AI model the first time)"; Flags: nowait postinstall skipifsilent

[Code]
var
  DownloadPage: TDownloadWizardPage;

{ An upgrade over a build whose exe had another name: that exe is removed, and so is any shortcut of ours in the Start menu or on
  the desktop that still points at it, so no shortcut can start the old build (which would offer the same update for ever). The
  uninstaller (unins*.exe) is left alone. AppId is unchanged, so an upgrade installs into the same folder and the saves in it stay. }
procedure RemoveStaleExes;
var
  F: TFindRec;
begin
  if FindFirst(ExpandConstant('{app}\*.exe'), F) then
  try
    repeat
      if (CompareText(F.Name, '{#AppExe}') <> 0) and (CompareText(Copy(F.Name, 1, 5), 'unins') <> 0) then
        DeleteFile(ExpandConstant('{app}\') + F.Name);
    until not FindNext(F);
  finally
    FindClose(F);
  end;
end;

procedure RemoveStaleShortcuts(const Dir: String);
var
  F: TFindRec;
  Shell, Link: Variant;
  Target: String;
begin
  try
    Shell := CreateOleObject('WScript.Shell');
  except
    Exit;
  end;
  if FindFirst(Dir + '\*.lnk', F) then
  try
    repeat
      Link := Shell.CreateShortcut(Dir + '\' + F.Name);
      Target := Link.TargetPath;
      if (CompareText(ExtractFilePath(Target), AddBackslash(ExpandConstant('{app}'))) = 0)
         and (CompareText(ExtractFileName(Target), '{#AppExe}') <> 0) then
        DeleteFile(Dir + '\' + F.Name);
    until not FindNext(F);
  finally
    FindClose(F);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    RemoveStaleExes;
    RemoveStaleShortcuts(ExpandConstant('{autoprograms}'));
    RemoveStaleShortcuts(ExpandConstant('{autodesktop}'));
  end;
end;

function HaveOllamaSetup: Boolean;
begin
  Result := FileExists(ExpandConstant('{tmp}\OllamaSetup.exe'));
end;

function HaveWebView2Setup: Boolean;
begin
  Result := FileExists(ExpandConstant('{tmp}\MicrosoftEdgeWebview2Setup.exe'));
end;

function OllamaInstalled: Boolean;
begin
  Result := FileExists(ExpandConstant('{localappdata}\Programs\Ollama\ollama.exe')) or FileExists(ExpandConstant('{commonpf}\Ollama\ollama.exe'));
end;

function WebView2Installed: Boolean;
var
  v: String;
begin
  Result := RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', v)
         or RegQueryStringValue(HKCU, 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', v);
  if Result then
    Result := (v <> '') and (v <> '0.0.0.0');
end;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), SetupMessage(msgPreparingDesc), nil);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Any: Boolean;
begin
  Result := True;
  if CurPageID = wpReady then
  begin
    DownloadPage.Clear;
    Any := False;
    if WizardIsTaskSelected('ollama') and not OllamaInstalled then
    begin
      DownloadPage.Add('https://ollama.com/download/OllamaSetup.exe', 'OllamaSetup.exe', '');
      Any := True;
    end;
    if not WebView2Installed then
    begin
      DownloadPage.Add('https://go.microsoft.com/fwlink/p/?LinkId=2124703', 'MicrosoftEdgeWebview2Setup.exe', '');
      Any := True;
    end;
    if Any then
    begin
      DownloadPage.Show;
      try
        try
          DownloadPage.Download;
        except
          if DownloadPage.AbortedByUser then
            Result := False
          else
            SuppressibleMsgBox('A download did not finish (' + GetExceptionMessage + '). The game is installed anyway and will offer to fix this the first time you start it.', mbInformation, MB_OK, IDOK);
        end;
      finally
        DownloadPage.Hide;
      end;
    end;
  end;
end;
