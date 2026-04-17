; ============================================================
; Kodi-MPC-HC Bridge — Inno Setup Installer Script
;
; UAC-freier Installer → %LocalAppData%\Programs\kodi-mpchc-bridge\
; Konfigurationsdaten → <Installationsverzeichnis>\config.json
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
#define AppExe       "kodi-bridge.exe"
#define AppTaskName  "KodiMpcHcBridge"
#define FwRuleName   "Kodi-MPC-HC Bridge"
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
; Desktop-Verknüpfung (opt-in)
Name: "desktopicon"; \
  Description: "Desktop-Verknüpfung erstellen"; \
  GroupDescription: "Zusätzliche Symbole:"; \
  Flags: unchecked
; Autostart (Standard: aktiv — "unchecked" wäre opt-out, kein Flag = Standard-aktiv)
Name: "autostart"; \
  Description: "Bridge beim Windows-Anmelden automatisch starten (empfohlen)"; \
  GroupDescription: "Autostart:"
; Firewall (Standard: aktiv)
Name: "firewall"; \
  Description: "Windows-Firewall-Regel für Bridge-Port 13590 einrichten (Admin-Fenster erscheint)"; \
  GroupDescription: "Firewall:"

[Files]
Source: "dist\{#AppExe}"; \
  DestDir: "{app}"; \
  Flags: ignoreversion

[Icons]
; Start Menu
Name: "{group}\{#AppName}";               Filename: "{app}\{#AppExe}"
Name: "{group}\{#AppName} deinstallieren"; Filename: "{uninstallexe}"
; Desktop shortcut — userdesktop (kein Admin nötig)
Name: "{userdesktop}\{#AppName}";          Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
; Bridge nach der Installation starten (optional, erscheint auf der Abschlussseite)
Filename: "{app}\{#AppExe}"; \
  Description: "{#AppName} jetzt starten"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; Laufende Instanz beenden — das war's; Rest läuft über Pascal-Code (CurUninstallStepChanged)
Filename: "taskkill"; \
  Parameters: "/f /im {#AppExe}"; \
  Flags: runhidden waituntilterminated; \
  RunOnceId: "KillBridge"

; ============================================================
; Pascal Script
; ============================================================
[Code]

var
  ConfigPage: TInputQueryWizardPage;

// --------------------------------------------------------------------------
// Hilfsfunktion: config.json vorhanden? (Upgrade-Erkennung)
// --------------------------------------------------------------------------
function ConfigExists: Boolean;
begin
  Result := FileExists(ExpandConstant('{app}\config.json'));
end;

// --------------------------------------------------------------------------
// Wizard-Seite: Kodi-Verbindungsdaten
// --------------------------------------------------------------------------
procedure InitializeWizard;
begin
  ConfigPage := CreateInputQueryPage(
    wpSelectDir,
    'Kodi-Verbindung konfigurieren',
    'Geben Sie die Verbindungsdaten Ihrer Kodi-Installation ein.',
    'Diese Einstellungen können später über das Tray-Icon → Einstellungen geändert werden.'
  );
  ConfigPage.Add('Kodi Host (IP oder Hostname):', False);
  ConfigPage.Add('Kodi HTTP-Port:', False);
  ConfigPage.Add('Kodi WebSocket-Port:', False);
  ConfigPage.Add('Benutzername  (leer = keine Authentifizierung):', False);
  ConfigPage.Add('Passwort:', True);

  ConfigPage.Values[0] := 'localhost';
  ConfigPage.Values[1] := '8080';
  ConfigPage.Values[2] := '9090';
  ConfigPage.Values[3] := '';
  ConfigPage.Values[4] := '';
end;

// --------------------------------------------------------------------------
// Konfigurationsseite beim Upgrade überspringen
// --------------------------------------------------------------------------
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if PageID = ConfigPage.ID then
    Result := ConfigExists;
end;

// --------------------------------------------------------------------------
// Eingabe-Validierung
// --------------------------------------------------------------------------
function NextButtonClick(CurPageID: Integer): Boolean;
var
  p: Integer;
begin
  Result := True;
  if CurPageID <> ConfigPage.ID then Exit;
  if ShouldSkipPage(CurPageID) then Exit;

  if Trim(ConfigPage.Values[0]) = '' then begin
    MsgBox('Bitte einen Kodi-Host eingeben (z. B. localhost oder 192.168.1.x).',
           mbError, MB_OK);
    Result := False; Exit;
  end;
  p := StrToIntDef(ConfigPage.Values[1], -1);
  if (p < 1) or (p > 65535) then begin
    MsgBox('Ungültiger HTTP-Port (1–65535).', mbError, MB_OK);
    Result := False; Exit;
  end;
  p := StrToIntDef(ConfigPage.Values[2], -1);
  if (p < 1) or (p > 65535) then begin
    MsgBox('Ungültiger WebSocket-Port (1–65535).', mbError, MB_OK);
    Result := False; Exit;
  end;
end;

// --------------------------------------------------------------------------
// JSON-Zeichen escapen
// --------------------------------------------------------------------------
function EscapeJson(const s: String): String;
var i: Integer; c: Char;
begin
  Result := '';
  for i := 1 to Length(s) do begin
    c := s[i];
    if      c = '"'  then Result := Result + '\"'
    else if c = '\' then Result := Result + '\\'
    else Result := Result + c;
  end;
end;

// --------------------------------------------------------------------------
// Task-Scheduler-Eintrag erstellen (kein Admin nötig, ONLOGON, User-Session).
// Nutzt Exec() mit vollständigem Pfad + zusammengesetztem Parameter-String,
// damit Leerzeichen im Installationspfad korrekt gequotet werden.
// --------------------------------------------------------------------------
procedure CreateAutostartTask;
var
  AppPath, Params: String;
  rc: Integer;
begin
  AppPath := ExpandConstant('{app}\{#AppExe}');
  Params  := '/create /f'
    + ' /tn "' + '{#AppTaskName}' + '"'
    + ' /tr "' + AppPath + '"'
    + ' /sc ONLOGON'
    + ' /rl LIMITED';
  Exec(ExpandConstant('{sys}\schtasks.exe'), Params, '',
       SW_HIDE, ewWaitUntilTerminated, rc);
end;

// --------------------------------------------------------------------------
// Task-Scheduler-Eintrag entfernen.
// --------------------------------------------------------------------------
procedure DeleteAutostartTask;
var
  rc: Integer;
begin
  Exec(ExpandConstant('{sys}\schtasks.exe'),
       '/delete /f /tn "' + '{#AppTaskName}' + '"',
       '', SW_HIDE, ewWaitUntilTerminated, rc);
end;

// --------------------------------------------------------------------------
// Firewall-Regel hinzufügen — via ShellExec 'runas' (UAC-Fenster wenn nötig).
// ewNoWait: Installer wartet nicht auf Abschluss (UAC-Fenster erscheint danach).
// --------------------------------------------------------------------------
procedure AddFirewallRule;
var
  ErrCode: Integer;
begin
  ShellExec(
    'runas', 'powershell.exe',
    '-NoProfile -NonInteractive -WindowStyle Hidden -Command '
    + '"New-NetFirewallRule'
    + ' -DisplayName ''' + '{#FwRuleName}' + ''''
    + ' -Direction Inbound -Action Allow -Protocol TCP'
    + ' -LocalPort 13590 -Profile Any -ErrorAction SilentlyContinue"',
    '', SW_HIDE, ewNoWait, ErrCode);
end;

// --------------------------------------------------------------------------
// Firewall-Regel entfernen — via ShellExec 'runas', WARTET auf Abschluss
// damit die Deinstallation die Regel tatsächlich entfernt hat.
// --------------------------------------------------------------------------
procedure RemoveFirewallRule;
var
  ErrCode: Integer;
begin
  ShellExec(
    'runas', 'powershell.exe',
    '-NoProfile -NonInteractive -WindowStyle Hidden -Command '
    + '"Remove-NetFirewallRule'
    + ' -DisplayName ''' + '{#FwRuleName}' + ''''
    + ' -ErrorAction SilentlyContinue"',
    '', SW_HIDE, ewWaitUntilTerminated, ErrCode);
end;

// --------------------------------------------------------------------------
// Nach Installation: config.json schreiben + Autostart + Firewall einrichten.
// --------------------------------------------------------------------------
procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigFile: String;
  Lines: TStringList;
  Json: String;
begin
  if CurStep <> ssPostInstall then Exit;

  // --- config.json (nur bei Erstinstallation) ---
  ConfigFile := ExpandConstant('{app}\config.json');
  if not FileExists(ConfigFile) then begin
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

  // --- Autostart-Task (Task-Planer, kein Admin) ---
  if WizardIsTaskSelected('autostart') then
    CreateAutostartTask;

  // --- Firewall-Regel (benötigt Admin → UAC-Fenster) ---
  if WizardIsTaskSelected('firewall') then
    AddFirewallRule;
end;

// --------------------------------------------------------------------------
// Bei Deinstallation: Firewall entfernen (UAC) + Autostart + config.json fragen.
// --------------------------------------------------------------------------
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ConfigFile: String;
begin
  if CurUninstallStep = usUninstall then begin

    // Firewall-Regel entfernen (Admin nötig → UAC-Fenster, wartet auf Abschluss)
    RemoveFirewallRule;

    // Autostart-Task entfernen (kein Admin nötig)
    DeleteAutostartTask;

    // config.json: Nutzer fragen
    ConfigFile := ExpandConstant('{app}\config.json');
    if FileExists(ConfigFile) then begin
      if MsgBox(
        'Möchten Sie die Konfigurationsdatei (config.json) ebenfalls löschen?' + #13#10 + #13#10 +
        '"Nein" behält die Einstellungen für eine spätere Neuinstallation.',
        mbConfirmation, MB_YESNO) = IDYES then
        DeleteFile(ConfigFile);
    end;
  end;
end;

// --------------------------------------------------------------------------
// Laufende Bridge vor Installation/Upgrade beenden
// --------------------------------------------------------------------------
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  rc: Integer;
begin
  Exec('taskkill', '/f /im {#AppExe}', '', SW_HIDE, ewWaitUntilTerminated, rc);
  Result := '';
end;
