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
; Update-Modus: bestehende Installation wird überschrieben ohne Deinstallation
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
; Autostart via Task-Planer (opt-in, Standard: aktiv)
Name: "autostart"; \
  Description: "Bridge beim Windows-Anmelden automatisch starten (empfohlen)"; \
  GroupDescription: "Autostart:"; \
  Flags: checked
; Firewall-Regel (opt-in, UAC-Fenster erscheint nach Installation)
Name: "firewall"; \
  Description: "Windows-Firewall-Regel für Bridge-Port 13590 einrichten (Admin erforderlich)"; \
  GroupDescription: "Firewall:"; \
  Flags: checked

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
; Autostart-Task im Task-Planer registrieren (kein Admin, ONLOGON, Standard-Benutzer)
; Startet bridge.exe ohne --headless → Bridge + Tray-Icon werden gemeinsam gestartet.
Filename: "schtasks"; \
  Parameters: "/create /f /tn KodiMpcHcBridge /tr ""{app}\{#AppExe}"" /sc ONLOGON /rl LIMITED"; \
  Flags: runhidden waituntilterminated; \
  Tasks: autostart
; Bridge direkt nach der Installation starten
Filename: "{app}\{#AppExe}"; \
  Description: "{#AppName} jetzt starten"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; Laufende Instanz beenden
Filename: "taskkill"; \
  Parameters: "/f /im {#AppExe}"; \
  Flags: runhidden waituntilterminated; \
  RunOnceId: "KillBridge"
; Autostart-Task entfernen
Filename: "schtasks"; \
  Parameters: "/delete /f /tn KodiMpcHcBridge"; \
  Flags: runhidden; \
  RunOnceId: "RemoveAutostart"
; Firewall-Regel entfernen (kein UAC nötig — Remove läuft im Kontext des Uninstallers)
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -NonInteractive -WindowStyle Hidden -Command ""Remove-NetFirewallRule -DisplayName 'Kodi-MPC-HC Bridge' -ErrorAction SilentlyContinue"""; \
  Flags: runhidden; \
  RunOnceId: "RemoveFirewall"

; ============================================================
; Pascal Script
; ============================================================
[Code]

var
  ConfigPage: TInputQueryWizardPage;

// --------------------------------------------------------------------------
// Hilfsfunktion: Liefert true wenn bereits eine config.json vorhanden ist
// (Upgrade-Szenario).
// --------------------------------------------------------------------------
function ConfigExists: Boolean;
begin
  Result := FileExists(ExpandConstant('{app}\config.json'));
end;

// --------------------------------------------------------------------------
// Wizard-Seite: Kodi-Verbindungsdaten — nur bei Erstinstallation anzeigen.
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
// Konfigurationsseite bei Upgrade überspringen — config.json bereits da.
// --------------------------------------------------------------------------
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if PageID = ConfigPage.ID then
    Result := ConfigExists;
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
  if ShouldSkipPage(CurPageID) then Exit;

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
// JSON-Zeichen escapen
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

// --------------------------------------------------------------------------
// Firewall-Regel via eleviertem PowerShell hinzufügen.
// Zeigt UAC-Fenster, wenn der aktuelle Nutzer kein Admin ist.
// --------------------------------------------------------------------------
procedure AddFirewallRule;
var
  Port: Integer;
  ErrCode: Integer;
begin
  // Port aus der Konfigurationsseite lesen (Fallback: 13590)
  Port := 13590;
  ShellExec(
    'runas',
    'powershell.exe',
    '-NoProfile -NonInteractive -WindowStyle Hidden -Command "' +
      'New-NetFirewallRule' +
      ' -DisplayName ''Kodi-MPC-HC Bridge''' +
      ' -Direction Inbound' +
      ' -Action Allow' +
      ' -Protocol TCP' +
      ' -LocalPort ' + IntToStr(Port) +
      ' -Profile Any' +
      ' -ErrorAction SilentlyContinue"',
    '',
    SW_HIDE,
    ewNoWait,
    ErrCode
  );
end;

// --------------------------------------------------------------------------
// Nach der Installation: config.json im Installationsverzeichnis ablegen.
// Nur bei Erstinstallation — bei Upgrade bleibt vorhandene config.json erhalten.
// --------------------------------------------------------------------------
procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigFile: String;
  Lines: TStringList;
  Json: String;
begin
  if CurStep <> ssPostInstall then Exit;

  ConfigFile := ExpandConstant('{app}\config.json');

  // Vorhandene Konfiguration nicht überschreiben (Upgrade-Szenario)
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

  // Firewall-Regel einrichten (UAC-Fenster erscheint, falls nötig)
  if WizardIsTaskSelected('firewall') then
    AddFirewallRule;
end;

// --------------------------------------------------------------------------
// Bei Deinstallation: Nutzer fragen ob config.json gelöscht werden soll.
// --------------------------------------------------------------------------
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ConfigFile: String;
begin
  if CurUninstallStep = usUninstall then begin
    ConfigFile := ExpandConstant('{app}\config.json');
    if FileExists(ConfigFile) then begin
      if MsgBox(
        'Möchten Sie die Konfigurationsdatei (config.json) ebenfalls löschen?' + #13#10 + #13#10 +
        'Wenn Sie "Nein" wählen, bleibt Ihre Konfiguration für eine spätere' + #13#10 +
        'Neuinstallation erhalten.',
        mbConfirmation, MB_YESNO) = IDYES then
        DeleteFile(ConfigFile);
    end;
  end;
end;

// --------------------------------------------------------------------------
// Laufende Bridge vor Installation/Upgrade beenden (verhindert Dateisperren)
// --------------------------------------------------------------------------
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  rc: Integer;
begin
  Exec('taskkill', '/f /im {#AppExe}', '', SW_HIDE,
       ewWaitUntilTerminated, rc);
  Result := '';
end;
