; ============================================================
; Kodi-MPC-HC Bridge — Inno Setup Installer Script
;
; UAC-freier Installer → %LocalAppData%\Programs\kodi-mpchc-bridge\
; Konfigurationsdaten → %LocalAppData%\kodi-mpchc-bridge\config.json
;
; Bauen:
;   iscc installer.iss
;   iscc /DAppVersion=1.2.3 installer.iss
;
; Ausgabe: dist\kodi-mpchc-bridge-setup-{version}.exe
; ============================================================

#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif

#define AppName      "Kodi-MPC-HC Bridge"
#define AppPublisher "kodi-mpchc-bridge"
#define AppURL       "https://github.com/Zendonir/kodi-mpchc-bridge"
#define AppExe       "bridge.exe"
#define AppGUID      "{{B7A3C2D1-E4F5-4890-BCDE-F01234567890}"

[Setup]
AppId={#AppGUID}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases/latest

; --- Install location (no admin needed) ---
DefaultDirName={localappdata}\Programs\kodi-mpchc-bridge
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline dialog

; --- Output ---
OutputDir=dist
OutputBaseFilename=kodi-mpchc-bridge-setup-{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes

; --- Appearance ---
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}

; --- Target architecture ---
ArchitecturesInstallIn64BitMode=x64compatible

; --- Misc ---
AllowNoIcons=yes
CloseApplications=force

[Languages]
Name: "german";  MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; \
  Description: "Desktop-Verknüpfung erstellen"; \
  GroupDescription: "Zusätzliche Symbole:"; \
  Flags: unchecked

[Files]
Source: "dist\{#AppExe}"; \
  DestDir: "{app}"; \
  Flags: ignoreversion

[Icons]
; Start Menu
Name: "{group}\{#AppName}";                        Filename: "{app}\{#AppExe}"
Name: "{group}\{#AppName} deinstallieren";          Filename: "{uninstallexe}"
; Desktop shortcut — userdesktop (no admin needed)
Name: "{userdesktop}\{#AppName}";                  Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; \
  Description: "{#AppName} jetzt starten"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; Kill running instance
Filename: "taskkill"; \
  Parameters: "/f /im {#AppExe}"; \
  Flags: runhidden waituntilterminated; \
  RunOnceId: "KillBridge"
; Remove Task-Scheduler autostart entry
Filename: "schtasks"; \
  Parameters: "/delete /f /tn KodiMpcHcBridge"; \
  Flags: runhidden; \
  RunOnceId: "RemoveAutostart"

; ============================================================
; Pascal Script — Konfigurationsseite + config.json schreiben
; ============================================================
[Code]

var
  ConfigPage: TInputQueryWizardPage;

// --------------------------------------------------------------------------
// Wizard page: Kodi-Verbindungsdaten eingeben
// --------------------------------------------------------------------------
procedure InitializeWizard;
begin
  ConfigPage := CreateInputQueryPage(
    wpSelectDir,
    'Kodi-Verbindung konfigurieren',
    'Geben Sie die Verbindungsdaten Ihrer Kodi-Installation ein.',
    'Diese Einstellungen können später jederzeit in der Bridge-GUI geändert werden.'
  );
  ConfigPage.Add('Kodi Host (IP oder Hostname):', False);
  ConfigPage.Add('Kodi HTTP-Port:', False);
  ConfigPage.Add('Kodi WebSocket-Port:', False);
  ConfigPage.Add('Benutzername  (leer = Kodi ohne Authentifizierung):', False);
  ConfigPage.Add('Passwort:', True);   // True = Passwort verbergen

  // Standard-Werte
  ConfigPage.Values[0] := 'localhost';
  ConfigPage.Values[1] := '8080';
  ConfigPage.Values[2] := '9090';
  ConfigPage.Values[3] := '';
  ConfigPage.Values[4] := '';
end;

// --------------------------------------------------------------------------
// Eingabe-Validierung beim Weiterklicken
// --------------------------------------------------------------------------
function NextButtonClick(CurPageID: Integer): Boolean;
var
  p: Integer;
begin
  Result := True;
  if CurPageID <> ConfigPage.ID then Exit;

  if Trim(ConfigPage.Values[0]) = '' then begin
    MsgBox('Bitte einen Kodi-Host eingeben (z. B. localhost oder 192.168.1.x).',
           mbError, MB_OK);
    Result := False; Exit;
  end;

  p := StrToIntDef(ConfigPage.Values[1], -1);
  if (p < 1) or (p > 65535) then begin
    MsgBox('Ungültiger Kodi HTTP-Port — bitte eine Zahl zwischen 1 und 65535 eingeben.',
           mbError, MB_OK);
    Result := False; Exit;
  end;

  p := StrToIntDef(ConfigPage.Values[2], -1);
  if (p < 1) or (p > 65535) then begin
    MsgBox('Ungültiger Kodi WebSocket-Port — bitte eine Zahl zwischen 1 und 65535 eingeben.',
           mbError, MB_OK);
    Result := False; Exit;
  end;
end;

// --------------------------------------------------------------------------
// Nach der Installation: config.json in %LocalAppData%\kodi-mpchc-bridge\
// schreiben (nur wenn noch keine Konfiguration vorhanden ist).
// --------------------------------------------------------------------------
function EscapeJson(const s: String): String;
var
  i: Integer;
  c: Char;
begin
  Result := '';
  for i := 1 to Length(s) do begin
    c := s[i];
    if c = '"'  then Result := Result + '\"'
    else if c = '\' then Result := Result + '\\'
    else Result := Result + c;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigDir, ConfigFile: String;
  Lines: TStringList;
  Json: String;
begin
  if CurStep <> ssPostInstall then Exit;

  ConfigDir  := ExpandConstant('{localappdata}\kodi-mpchc-bridge');
  ConfigFile := ConfigDir + '\config.json';

  // Create directory if it doesn't exist
  if not ForceDirectories(ConfigDir) then Exit;

  // Don't overwrite an existing config (upgrade scenario)
  if FileExists(ConfigFile) then Exit;

  Json :=
    '{' + #13#10 +
    '  "kodi_host": "'     + EscapeJson(Trim(ConfigPage.Values[0])) + '",' + #13#10 +
    '  "kodi_port": '      + IntToStr(StrToIntDef(ConfigPage.Values[1], 8080)) + ',' + #13#10 +
    '  "kodi_ws_port": '   + IntToStr(StrToIntDef(ConfigPage.Values[2], 9090)) + ',' + #13#10 +
    '  "kodi_username": "' + EscapeJson(ConfigPage.Values[3]) + '",' + #13#10 +
    '  "kodi_password": "' + EscapeJson(ConfigPage.Values[4]) + '",' + #13#10 +
    '  "kodi_ssl": false,' + #13#10 +
    '  "kodi_enabled": true,' + #13#10 +
    '  "mpchc_host": "localhost",' + #13#10 +
    '  "mpchc_port": 13579,' + #13#10 +
    '  "mpchc_enabled": true,' + #13#10 +
    '  "server_host": "0.0.0.0",' + #13#10 +
    '  "server_port": 13590' + #13#10 +
    '}';

  Lines := TStringList.Create;
  try
    Lines.Text := Json;
    Lines.SaveToFile(ConfigFile);
  finally
    Lines.Free;
  end;
end;

// --------------------------------------------------------------------------
// Kill running bridge before install/upgrade (avoids file-in-use errors)
// --------------------------------------------------------------------------
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  rc: Integer;
begin
  Exec('taskkill', '/f /im {#AppExe}', '', SW_HIDE,
       ewWaitUntilTerminated, rc);
  Result := '';
end;
