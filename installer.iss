; ============================================================
; Kodi-MPC-HC Bridge — Inno Setup Installer Script
;
; UAC-free installer → %LocalAppData%\Programs\kodi-mpchc-bridge\
; Configuration      → <install dir>\config.json
;
; Build:
;   iscc installer.iss
;   iscc /DAppVersion=1.2.3 installer.iss
;
; Output: dist\kodi-mpchc-bridge-setup-{version}.exe
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

; --- Language detection ---
ShowLanguageDialog=auto
LanguageDetectionMethod=uilanguage

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

; ============================================================
; Languages
; ============================================================
[Languages]
Name: "english";  MessagesFile: "compiler:Default.isl"
Name: "german";   MessagesFile: "compiler:Languages\German.isl"
Name: "french";   MessagesFile: "compiler:Languages\French.isl"
Name: "spanish";  MessagesFile: "compiler:Languages\Spanish.isl"
Name: "italian";  MessagesFile: "compiler:Languages\Italian.isl"

; ============================================================
; Custom messages  (one block per language)
; ============================================================
[CustomMessages]

; ── English ───────────────────────────────────────────────────────────────────
english.ConfigPageTitle=Configure Kodi connection
english.ConfigPageSubtitle=Enter the connection details of your Kodi installation.
english.ConfigPageDesc=These settings can be changed later via the tray icon → Settings.
english.ConfigHost=Kodi Host (IP or hostname):
english.ConfigHttpPort=Kodi HTTP port:
english.ConfigWsPort=Kodi WebSocket port:
english.ConfigUser=Username  (blank = no authentication):
english.ConfigPass=Password:
english.ErrNoHost=Please enter a Kodi host.
english.ErrBadHttp=Invalid HTTP port (1–65535).
english.ErrBadWs=Invalid WebSocket port (1–65535).
english.AskDelConfig=Delete the configuration file (config.json) as well?%n%n"No" keeps the settings for a future reinstallation.
english.RunNow=Start %1 now
english.DesktopIconDesc=Create a desktop shortcut
english.DesktopIconGroup=Additional icons:
english.AutostartDesc=Start Bridge automatically when Windows starts (recommended)
english.AutostartGroup=Autostart:
english.FirewallDesc=Configure Windows Firewall rule for Bridge port 13590 (admin prompt appears briefly)
english.FirewallGroup=Firewall:

; ── German ────────────────────────────────────────────────────────────────────
german.ConfigPageTitle=Kodi-Verbindung konfigurieren
german.ConfigPageSubtitle=Geben Sie die Verbindungsdaten Ihrer Kodi-Installation ein.
german.ConfigPageDesc=Diese Einstellungen können später über das Tray-Icon → Einstellungen geändert werden.
german.ConfigHost=Kodi Host (IP oder Hostname):
german.ConfigHttpPort=Kodi HTTP-Port:
german.ConfigWsPort=Kodi WebSocket-Port:
german.ConfigUser=Benutzername  (leer = keine Authentifizierung):
german.ConfigPass=Passwort:
german.ErrNoHost=Bitte einen Kodi-Host eingeben.
german.ErrBadHttp=Ungültiger HTTP-Port (1–65535).
german.ErrBadWs=Ungültiger WebSocket-Port (1–65535).
german.AskDelConfig=Möchten Sie die Konfigurationsdatei (config.json) ebenfalls löschen?%n%n"Nein" behält die Einstellungen für eine spätere Neuinstallation.
german.RunNow=%1 jetzt starten
german.DesktopIconDesc=Desktop-Verknüpfung erstellen
german.DesktopIconGroup=Zusätzliche Symbole:
german.AutostartDesc=Bridge beim Windows-Anmelden automatisch starten (empfohlen)
german.AutostartGroup=Autostart:
german.FirewallDesc=Windows-Firewall-Regel für Bridge-Port 13590 einrichten (Admin-Fenster erscheint kurz)
german.FirewallGroup=Firewall:

; ── French ────────────────────────────────────────────────────────────────────
french.ConfigPageTitle=Configurer la connexion Kodi
french.ConfigPageSubtitle=Entrez les informations de connexion de votre installation Kodi.
french.ConfigPageDesc=Ces paramètres peuvent être modifiés ultérieurement via l'icône de la barre des tâches → Paramètres.
french.ConfigHost=Hôte Kodi (IP ou nom d'hôte) :
french.ConfigHttpPort=Port HTTP Kodi :
french.ConfigWsPort=Port WebSocket Kodi :
french.ConfigUser=Nom d'utilisateur  (vide = pas d'authentification) :
french.ConfigPass=Mot de passe :
french.ErrNoHost=Veuillez entrer un hôte Kodi.
french.ErrBadHttp=Port HTTP invalide (1–65535).
french.ErrBadWs=Port WebSocket invalide (1–65535).
french.AskDelConfig=Supprimer également le fichier de configuration (config.json) ?%n%n"Non" conserve les paramètres pour une future réinstallation.
french.RunNow=Démarrer %1 maintenant
french.DesktopIconDesc=Créer un raccourci sur le bureau
french.DesktopIconGroup=Icônes supplémentaires :
french.AutostartDesc=Démarrer le Bridge automatiquement au démarrage de Windows (recommandé)
french.AutostartGroup=Démarrage automatique :
french.FirewallDesc=Configurer la règle de pare-feu Windows pour le port 13590 (une invite admin apparaît brièvement)
french.FirewallGroup=Pare-feu :

; ── Spanish ───────────────────────────────────────────────────────────────────
spanish.ConfigPageTitle=Configurar conexión de Kodi
spanish.ConfigPageSubtitle=Introduzca los datos de conexión de su instalación de Kodi.
spanish.ConfigPageDesc=Estos ajustes se pueden modificar más tarde mediante el icono de la bandeja → Configuración.
spanish.ConfigHost=Host de Kodi (IP o nombre de host):
spanish.ConfigHttpPort=Puerto HTTP de Kodi:
spanish.ConfigWsPort=Puerto WebSocket de Kodi:
spanish.ConfigUser=Usuario  (vacío = sin autenticación):
spanish.ConfigPass=Contraseña:
spanish.ErrNoHost=Por favor, introduzca un host de Kodi.
spanish.ErrBadHttp=Puerto HTTP no válido (1–65535).
spanish.ErrBadWs=Puerto WebSocket no válido (1–65535).
spanish.AskDelConfig=¿Eliminar también el archivo de configuración (config.json)?%n%n"No" conserva los ajustes para una futura reinstalación.
spanish.RunNow=Iniciar %1 ahora
spanish.DesktopIconDesc=Crear un acceso directo en el escritorio
spanish.DesktopIconGroup=Iconos adicionales:
spanish.AutostartDesc=Iniciar el Bridge automáticamente al iniciar Windows (recomendado)
spanish.AutostartGroup=Inicio automático:
spanish.FirewallDesc=Configurar regla de Firewall de Windows para el puerto 13590 (aparece una ventana de administrador brevemente)
spanish.FirewallGroup=Firewall:

; ── Italian ───────────────────────────────────────────────────────────────────
italian.ConfigPageTitle=Configura connessione Kodi
italian.ConfigPageSubtitle=Inserisci i dati di connessione della tua installazione Kodi.
italian.ConfigPageDesc=Queste impostazioni possono essere modificate in seguito tramite l'icona nella barra delle applicazioni → Impostazioni.
italian.ConfigHost=Host Kodi (IP o nome host):
italian.ConfigHttpPort=Porta HTTP Kodi:
italian.ConfigWsPort=Porta WebSocket Kodi:
italian.ConfigUser=Utente  (vuoto = nessuna autenticazione):
italian.ConfigPass=Password:
italian.ErrNoHost=Inserisci un host Kodi.
italian.ErrBadHttp=Porta HTTP non valida (1–65535).
italian.ErrBadWs=Porta WebSocket non valida (1–65535).
italian.AskDelConfig=Eliminare anche il file di configurazione (config.json)?%n%n"No" mantiene le impostazioni per una futura reinstallazione.
italian.RunNow=Avvia %1 ora
italian.DesktopIconDesc=Crea un collegamento sul desktop
italian.DesktopIconGroup=Icone aggiuntive:
italian.AutostartDesc=Avvia il Bridge automaticamente all'avvio di Windows (consigliato)
italian.AutostartGroup=Avvio automatico:
italian.FirewallDesc=Configura regola Windows Firewall per la porta 13590 (appare brevemente una finestra di amministratore)
italian.FirewallGroup=Firewall:

; ============================================================
[Tasks]
; Desktop shortcut (opt-in)
Name: "desktopicon"; \
  Description: "{cm:DesktopIconDesc}"; \
  GroupDescription: "{cm:DesktopIconGroup}"; \
  Flags: unchecked
; Autostart (default: on)
Name: "autostart"; \
  Description: "{cm:AutostartDesc}"; \
  GroupDescription: "{cm:AutostartGroup}"
; Firewall (default: on)
Name: "firewall"; \
  Description: "{cm:FirewallDesc}"; \
  GroupDescription: "{cm:FirewallGroup}"

[Files]
Source: "dist\{#AppExe}"; \
  DestDir: "{app}"; \
  Flags: ignoreversion

[Icons]
; Start Menu
Name: "{group}\{#AppName}";               Filename: "{app}\{#AppExe}"
Name: "{group}\{#AppName} Uninstall";     Filename: "{uninstallexe}"
; Desktop shortcut — userdesktop (no admin needed)
Name: "{userdesktop}\{#AppName}";          Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
; Launch bridge after installation (finish page)
Filename: "{app}\{#AppExe}"; \
  Description: "{cm:RunNow,{#AppName}}"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; Kill running instance — autostart + firewall are removed in Pascal code
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
// Helper: config.json exists? (upgrade detection)
// --------------------------------------------------------------------------
function ConfigExists: Boolean;
begin
  Result := FileExists(ExpandConstant('{app}\config.json'));
end;

// --------------------------------------------------------------------------
// Wizard page: Kodi connection details
// --------------------------------------------------------------------------
procedure InitializeWizard;
begin
  ConfigPage := CreateInputQueryPage(
    wpSelectDir,
    CustomMessage('ConfigPageTitle'),
    CustomMessage('ConfigPageSubtitle'),
    CustomMessage('ConfigPageDesc')
  );
  ConfigPage.Add(CustomMessage('ConfigHost'),    False);
  ConfigPage.Add(CustomMessage('ConfigHttpPort'),False);
  ConfigPage.Add(CustomMessage('ConfigWsPort'),  False);
  ConfigPage.Add(CustomMessage('ConfigUser'),    False);
  ConfigPage.Add(CustomMessage('ConfigPass'),    True);

  ConfigPage.Values[0] := 'localhost';
  ConfigPage.Values[1] := '8080';
  ConfigPage.Values[2] := '9090';
  ConfigPage.Values[3] := '';
  ConfigPage.Values[4] := '';
end;

// --------------------------------------------------------------------------
// Skip config page on upgrade
// --------------------------------------------------------------------------
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if PageID = ConfigPage.ID then
    Result := ConfigExists;
end;

// --------------------------------------------------------------------------
// Input validation
// --------------------------------------------------------------------------
function NextButtonClick(CurPageID: Integer): Boolean;
var
  p: Integer;
begin
  Result := True;
  if CurPageID <> ConfigPage.ID then Exit;
  if ShouldSkipPage(CurPageID) then Exit;

  if Trim(ConfigPage.Values[0]) = '' then begin
    MsgBox(CustomMessage('ErrNoHost'), mbError, MB_OK);
    Result := False; Exit;
  end;
  p := StrToIntDef(ConfigPage.Values[1], -1);
  if (p < 1) or (p > 65535) then begin
    MsgBox(CustomMessage('ErrBadHttp'), mbError, MB_OK);
    Result := False; Exit;
  end;
  p := StrToIntDef(ConfigPage.Values[2], -1);
  if (p < 1) or (p > 65535) then begin
    MsgBox(CustomMessage('ErrBadWs'), mbError, MB_OK);
    Result := False; Exit;
  end;
end;

// --------------------------------------------------------------------------
// JSON character escaping
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
// Create autostart Task Scheduler entry.
//
// Why a PowerShell script file instead of schtasks.exe?
//   • schtasks has subtle quoting issues with paths containing spaces
//     when the parameter string is passed via CreateProcess.
//   • Register-ScheduledTask (PowerShell cmdlet) is more robust, has no
//     quoting traps, and runs reliably without admin rights.
//   • The .ps1 file bypasses all command-line escaping problems:
//     AppPath is written directly into the script content.
// --------------------------------------------------------------------------
procedure CreateAutostartTask;
var
  AppPath, ScriptPath, Script: String;
  rc: Integer;
begin
  AppPath    := ExpandConstant('{app}\{#AppExe}');
  ScriptPath := ExpandConstant('{tmp}\kodi_create_task.ps1');

  // Single-quotes (char 39) for PowerShell literals —
  // no risk of variable expansion in the path.
  Script :=
    '$act = New-ScheduledTaskAction -Execute ' + #39 + AppPath + #39 + #13#10 +
    '$tri = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME' + #13#10 +
    '$pri = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited' + #13#10 +
    '$set = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries' + #13#10 +
    'Register-ScheduledTask -TaskName ' + #39 + '{#AppTaskName}' + #39 +
    ' -Action $act -Trigger $tri -Principal $pri -Settings $set -Force -ErrorAction Stop';

  if SaveStringToFile(ScriptPath, Script, False) then
    Exec('powershell.exe',
         '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + ScriptPath + '"',
         '', SW_HIDE, ewWaitUntilTerminated, rc);
end;

// --------------------------------------------------------------------------
// Remove Task Scheduler entry.
// schtasks /delete is safe here — no path, just the task name.
// --------------------------------------------------------------------------
procedure DeleteAutostartTask;
var
  rc: Integer;
begin
  Exec(ExpandConstant('{sys}\schtasks.exe'),
       '/delete /f /tn ' + '{#AppTaskName}',
       '', SW_HIDE, ewWaitUntilTerminated, rc);
end;

// --------------------------------------------------------------------------
// Add firewall rule — requires admin → UAC prompt appears briefly.
// ewNoWait: installer does not block; UAC window appears in background.
// --------------------------------------------------------------------------
procedure AddFirewallRule;
var
  ErrCode: Integer;
begin
  ShellExec(
    'runas', 'powershell.exe',
    '-NoProfile -NonInteractive -ExecutionPolicy Bypass -Command '
    + '"New-NetFirewallRule -DisplayName ' + #39 + '{#FwRuleName}' + #39
    + ' -Direction Inbound -Action Allow -Protocol TCP'
    + ' -LocalPort 13590 -Profile Any -ErrorAction SilentlyContinue"',
    '', SW_HIDE, ewNoWait, ErrCode);
end;

// --------------------------------------------------------------------------
// Remove firewall rule — requires admin → UAC prompt.
// ewWaitUntilTerminated: uninstall waits until rule is actually gone.
// --------------------------------------------------------------------------
procedure RemoveFirewallRule;
var
  ErrCode: Integer;
begin
  ShellExec(
    'runas', 'powershell.exe',
    '-NoProfile -NonInteractive -ExecutionPolicy Bypass -Command '
    + '"Remove-NetFirewallRule -DisplayName ' + #39 + '{#FwRuleName}' + #39
    + ' -ErrorAction SilentlyContinue"',
    '', SW_HIDE, ewWaitUntilTerminated, ErrCode);
end;

// --------------------------------------------------------------------------
// After installation: write config.json + set up autostart + firewall.
// --------------------------------------------------------------------------
procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigFile: String;
  Lines: TStringList;
  Json: String;
begin
  if CurStep <> ssPostInstall then Exit;

  // --- config.json (first installation only) ---
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

  // --- Autostart task (no admin needed) ---
  if WizardIsTaskSelected('autostart') then
    CreateAutostartTask;

  // --- Firewall rule (admin needed → UAC prompt) ---
  if WizardIsTaskSelected('firewall') then
    AddFirewallRule;
end;

// --------------------------------------------------------------------------
// On uninstall: remove firewall + autostart, ask about config.json.
// --------------------------------------------------------------------------
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ConfigFile: String;
begin
  if CurUninstallStep = usUninstall then begin

    // Remove firewall rule (admin → UAC, wait for completion)
    RemoveFirewallRule;

    // Remove autostart task (no admin)
    DeleteAutostartTask;

    // config.json: ask user
    ConfigFile := ExpandConstant('{app}\config.json');
    if FileExists(ConfigFile) then begin
      if MsgBox(
        CustomMessage('AskDelConfig'),
        mbConfirmation, MB_YESNO) = IDYES then
        DeleteFile(ConfigFile);
    end;
  end;
end;

// --------------------------------------------------------------------------
// Kill running bridge before installation / upgrade
// --------------------------------------------------------------------------
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  rc: Integer;
begin
  Exec('taskkill', '/f /im {#AppExe}', '', SW_HIDE, ewWaitUntilTerminated, rc);
  Result := '';
end;
