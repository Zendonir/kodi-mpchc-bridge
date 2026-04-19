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
#define AppTaskName          "KodiMpcHcBridge"
#define AppWatchdogTaskName  "KodiMpcHcBridgeWatchdog"
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
; -- External player wizard page --
english.PlayerPageTitle=Configure external player
english.PlayerPageSubtitle=Play Kodi videos directly in MPC-HC / MPC-BE (optional)
english.PlayerEnable=Configure Kodi to open videos in an external player
english.PlayerExeLbl=MPC-HC / MPC-BE executable:
english.PlayerBrowseBtn=Browse...
english.PlayerUseResume=Use built-in resume (seek MPC-HC to Kodi's saved position)
english.PlayerBackupChk=Backup existing playercorefactory.xml as .bak
english.ErrPlayerNoExe=Please select the MPC-HC / MPC-BE executable.
english.KioskHideExplorer=Hide Explorer on startup (kiosk mode)
english.KioskKodiExeLbl=Kodi executable (for kiosk mode):
english.KioskShellMode=Start Bridge as Windows shell – replaces Explorer on login (dedicated media PC)

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
; -- Externer Player --
german.PlayerPageTitle=Externen Player konfigurieren
german.PlayerPageSubtitle=Kodi-Videos direkt in MPC-HC / MPC-BE abspielen (optional)
german.PlayerEnable=Kodi auf externen Videoplayer umleiten
german.PlayerExeLbl=MPC-HC / MPC-BE Programmdatei:
german.PlayerBrowseBtn=Durchsuchen...
german.PlayerUseResume=Integriertes Resume (MPC-HC springt zur gespeicherten Kodi-Position)
german.PlayerBackupChk=Bestehende playercorefactory.xml als .bak sichern
german.ErrPlayerNoExe=Bitte die MPC-HC / MPC-BE Programmdatei auswählen.
german.KioskHideExplorer=Explorer beim Start verstecken (Kiosk-Modus)
german.KioskKodiExeLbl=Kodi-Programmdatei (für Kiosk-Modus):
german.KioskShellMode=Bridge als Windows-Shell starten – ersetzt Explorer beim Anmelden (dedizierter Medien-PC)

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
; -- Lecteur externe --
french.PlayerPageTitle=Configurer le lecteur externe
french.PlayerPageSubtitle=Lire les vidéos Kodi directement dans MPC-HC / MPC-BE (optionnel)
french.PlayerEnable=Configurer Kodi pour utiliser un lecteur externe
french.PlayerExeLbl=Exécutable MPC-HC / MPC-BE :
french.PlayerBrowseBtn=Parcourir...
french.PlayerUseResume=Resume intégré (positionne MPC-HC à la position Kodi)
french.PlayerBackupChk=Sauvegarder playercorefactory.xml existant en .bak
french.ErrPlayerNoExe=Veuillez sélectionner l'exécutable MPC-HC / MPC-BE.
french.KioskHideExplorer=Masquer l'Explorateur au démarrage (mode kiosque)
french.KioskKodiExeLbl=Exécutable Kodi (mode kiosque) :
french.KioskShellMode=Démarrer le Bridge comme shell Windows – remplace l'Explorateur à la connexion

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
; -- Reproductor externo --
spanish.PlayerPageTitle=Configurar reproductor externo
spanish.PlayerPageSubtitle=Reproducir vídeos de Kodi directamente en MPC-HC / MPC-BE (opcional)
spanish.PlayerEnable=Configurar Kodi para usar un reproductor externo
spanish.PlayerExeLbl=Ejecutable MPC-HC / MPC-BE:
spanish.PlayerBrowseBtn=Examinar...
spanish.PlayerUseResume=Resume integrado (lleva MPC-HC a la posición guardada en Kodi)
spanish.PlayerBackupChk=Copia de seguridad de playercorefactory.xml existente como .bak
spanish.ErrPlayerNoExe=Por favor, seleccione el ejecutable MPC-HC / MPC-BE.
spanish.KioskHideExplorer=Ocultar el Explorador al inicio (modo quiosco)
spanish.KioskKodiExeLbl=Ejecutable de Kodi (modo quiosco):
spanish.KioskShellMode=Iniciar Bridge como shell de Windows – reemplaza al Explorador al iniciar sesión

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
; -- Lettore esterno --
italian.PlayerPageTitle=Configura lettore esterno
italian.PlayerPageSubtitle=Riproduci i video di Kodi direttamente in MPC-HC / MPC-BE (opzionale)
italian.PlayerEnable=Configura Kodi per usare un lettore esterno
italian.PlayerExeLbl=Eseguibile MPC-HC / MPC-BE:
italian.PlayerBrowseBtn=Sfoglia...
italian.PlayerUseResume=Resume integrato (porta MPC-HC alla posizione salvata in Kodi)
italian.PlayerBackupChk=Backup del playercorefactory.xml esistente come .bak
italian.ErrPlayerNoExe=Selezionare l'eseguibile MPC-HC / MPC-BE.
italian.KioskHideExplorer=Nascondi Explorer all'avvio (modalità chiosco)
italian.KioskKodiExeLbl=Eseguibile Kodi (modalità chiosco):
italian.KioskShellMode=Avvia il Bridge come shell Windows – sostituisce Esplora risorse all'accesso

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
  // ── Kodi connection page ──────────────────────────────────────────────────
  ConfigPage: TInputQueryWizardPage;

  // ── External player page (one custom page, all controls) ─────────────────
  PlayerPage:      TWizardPage;
  chkEnablePlayer: TNewCheckBox;
  lblPlayerExe:    TLabel;
  edtPlayerExe:    TNewEdit;
  btnBrowseExe:    TNewButton;
  chkUseResume:    TNewCheckBox;
  chkBackup:       TNewCheckBox;
  // ── Kiosk controls (on the same page) ─────────────────────────────────────
  chkHideExplorer: TNewCheckBox;
  lblKodiExe:      TLabel;
  edtKodiExe:      TNewEdit;
  btnBrowseKodi:   TNewButton;
  chkShellMode:    TNewCheckBox;

// --------------------------------------------------------------------------
// Get the previously-installed directory from the uninstall registry key.
// Safe to call at any point — does NOT use {app} (which is unavailable
// until the install directory page has been confirmed).
// --------------------------------------------------------------------------
function GetInstalledDir: String;
begin
  Result := '';
  RegQueryStringValue(HKCU,
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\' +
    '{B7A3C2D1-E4F5-4890-BCDE-F01234567890}_is1',
    'InstallLocation', Result);
  // Strip trailing backslash if present
  if (Length(Result) > 0) and (Result[Length(Result)] = '\') then
    Result := Copy(Result, 1, Length(Result) - 1);
end;

// --------------------------------------------------------------------------
// Helper: config.json exists? (upgrade detection)
// --------------------------------------------------------------------------
function ConfigExists: Boolean;
var
  Dir: String;
begin
  Dir := GetInstalledDir;
  Result := (Dir <> '') and FileExists(Dir + '\config.json');
end;

// --------------------------------------------------------------------------
// Read a string value from an existing config.json.
// Uses simple substring search — good enough for well-formed JSON files
// written by the bridge (no nested objects or arrays in string values).
// --------------------------------------------------------------------------
function ReadConfigString(const Key: String): String;
var
  FilePath, SearchStr: String;
  Content: AnsiString;
  P, Q: Integer;
  Ch: Char;
begin
  Result := '';
  FilePath := GetInstalledDir + '\config.json';
  if not FileExists(FilePath) then Exit;
  if not LoadStringFromFile(FilePath, Content) then Exit;

  SearchStr := '"' + Key + '": "';
  P := Pos(SearchStr, Content);
  if P = 0 then Exit;
  P := P + Length(SearchStr);

  // Walk forward collecting characters, honouring backslash escapes
  Q := P;
  while Q <= Length(Content) do begin
    Ch := Content[Q];
    if Ch = '"' then Break;
    if (Ch = '\') and (Q < Length(Content)) then begin
      // Emit the character after the backslash literally (handles \\ and \")
      Inc(Q);
      Result := Result + Content[Q];
    end else
      Result := Result + Ch;
    Inc(Q);
  end;
end;

// --------------------------------------------------------------------------
// Read a boolean value (true/false) from config.json.
// --------------------------------------------------------------------------
function ReadConfigBool(const Key: String): Boolean;
var
  FilePath, SearchStr: String;
  Content: AnsiString;
  P: Integer;
begin
  Result := False;
  FilePath := GetInstalledDir + '\config.json';
  if not FileExists(FilePath) then Exit;
  if not LoadStringFromFile(FilePath, Content) then Exit;
  SearchStr := '"' + Key + '": ';
  P := Pos(SearchStr, Content);
  if P = 0 then Exit;
  Result := Copy(Content, P + Length(SearchStr), 4) = 'true';
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
// XML escaping — element content  (&  <  > only; " not needed in content)
// --------------------------------------------------------------------------
function EscapeXmlContent(const s: String): String;
var i: Integer; c: Char;
begin
  Result := '';
  for i := 1 to Length(s) do begin
    c := s[i];
    if      c = '&' then Result := Result + '&amp;'
    else if c = '<' then Result := Result + '&lt;'
    else if c = '>' then Result := Result + '&gt;'
    else Result := Result + c;
  end;
end;

// --------------------------------------------------------------------------
// XML escaping — attribute values  (adds " → &quot;)
// --------------------------------------------------------------------------
function EscapeXmlAttr(const s: String): String;
var i: Integer; c: Char;
begin
  Result := '';
  for i := 1 to Length(s) do begin
    c := s[i];
    if      c = '&'  then Result := Result + '&amp;'
    else if c = '<'  then Result := Result + '&lt;'
    else if c = '>'  then Result := Result + '&gt;'
    else if c = '"'  then Result := Result + '&quot;'
    else Result := Result + c;
  end;
end;

// --------------------------------------------------------------------------
// Enable/disable shell-mode checkbox based on hide-explorer checkbox
// --------------------------------------------------------------------------
procedure ToggleKioskControls(Sender: TObject);
begin
  chkShellMode.Enabled := chkHideExplorer.Checked;
  if not chkHideExplorer.Checked then
    chkShellMode.Checked := False;
end;

// --------------------------------------------------------------------------
// Create the watchdog scheduled task + write watchdog.ps1
// The watchdog runs at logon and restarts Explorer if the bridge crashes
// while acting as the Windows shell.
// --------------------------------------------------------------------------
procedure CreateWatchdogTask;
var
  AppDir, WdPath, TaskScriptPath, WdScript, TaskScript: String;
  rc: Integer;
begin
  AppDir         := ExpandConstant('{app}');
  WdPath         := AppDir + '\watchdog.ps1';
  TaskScriptPath := ExpandConstant('{tmp}\kodi_watchdog_task.ps1');

  // Write the watchdog PowerShell loop script to the install directory
  WdScript :=
    '# Kodi-MPC-HC Bridge - Shell Mode Watchdog' + #13#10 +
    '# Restores Explorer.exe when Bridge has crashed and no shell is running.' + #13#10 +
    'while ($true) {' + #13#10 +
    '    Start-Sleep -Seconds 30' + #13#10 +
    '    $bridge   = Get-Process ''kodi-bridge'' -ErrorAction SilentlyContinue' + #13#10 +
    '    $explorer = Get-Process ''explorer''    -ErrorAction SilentlyContinue' + #13#10 +
    '    if (-not $bridge -and -not $explorer) {' + #13#10 +
    '        Start-Process explorer.exe' + #13#10 +
    '        exit' + #13#10 +
    '    }' + #13#10 +
    '}';
  SaveStringToFile(WdPath, WdScript, False);

  // Register a Task Scheduler task: run watchdog at logon, hidden
  TaskScript :=
    '$act = New-ScheduledTaskAction -Execute ''powershell.exe''' + #13#10 +
    '    -Argument ''-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + WdPath + '"''' + #13#10 +
    '$tri = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME' + #13#10 +
    '$pri = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited' + #13#10 +
    '$set = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew' + #13#10 +
    'Register-ScheduledTask -TaskName ''{#AppWatchdogTaskName}'' -Action $act -Trigger $tri -Principal $pri -Settings $set -Force -ErrorAction Stop';

  if SaveStringToFile(TaskScriptPath, TaskScript, False) then
    Exec('powershell.exe',
         '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + TaskScriptPath + '"',
         '', SW_HIDE, ewWaitUntilTerminated, rc);
end;

// --------------------------------------------------------------------------
// Update kiosk-related fields in an existing config.json.
// Runs on every install (including upgrades) so that the registry Shell key
// and config.json always stay in sync.
// Uses PowerShell ConvertFrom-Json / ConvertTo-Json to patch only the three
// kiosk fields without touching any other user settings.
// --------------------------------------------------------------------------
procedure UpdateKioskConfig;
var
  ConfigFile, ScriptPath, Script: String;
  HideVal, ShellVal, ExeVal: String;
  rc: Integer;
begin
  ConfigFile := ExpandConstant('{app}\config.json');
  if not FileExists(ConfigFile) then Exit;

  ScriptPath := ExpandConstant('{tmp}\update_kiosk_cfg.ps1');

  if chkHideExplorer.Checked then HideVal  := '$true'  else HideVal  := '$false';
  if chkShellMode.Checked    then ShellVal := '$true'  else ShellVal := '$false';
  // PS single-quoted string — backslashes are literal, only ' needs doubling
  ExeVal := Trim(edtKodiExe.Text);

  Script :=
    '$f = ' + #39 + ConfigFile + #39 + #13#10 +
    '$c = Get-Content $f -Raw | ConvertFrom-Json' + #13#10 +
    '$c | Add-Member -Force -NotePropertyName hide_explorer -NotePropertyValue ' + HideVal  + #13#10 +
    '$c | Add-Member -Force -NotePropertyName shell_mode    -NotePropertyValue ' + ShellVal + #13#10 +
    '$c | Add-Member -Force -NotePropertyName kodi_exe_path -NotePropertyValue ' + #39 + ExeVal + #39 + #13#10 +
    '($c | ConvertTo-Json -Depth 10) | Set-Content $f -Encoding UTF8';

  if SaveStringToFile(ScriptPath, Script, False) then
    Exec('powershell.exe',
         '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + ScriptPath + '"',
         '', SW_HIDE, ewWaitUntilTerminated, rc);
end;

// --------------------------------------------------------------------------
// Remove the watchdog scheduled task (and its script file).
// --------------------------------------------------------------------------
procedure DeleteWatchdogTask;
var rc: Integer;
begin
  Exec(ExpandConstant('{sys}\schtasks.exe'),
       '/delete /f /tn {#AppWatchdogTaskName}',
       '', SW_HIDE, ewWaitUntilTerminated, rc);
end;

// --------------------------------------------------------------------------
// Enable/disable sub-controls based on master checkbox
// --------------------------------------------------------------------------
procedure TogglePlayerControls(Sender: TObject);
var en: Boolean;
begin
  en := chkEnablePlayer.Checked;
  lblPlayerExe.Enabled  := en;
  edtPlayerExe.Enabled  := en;
  btnBrowseExe.Enabled  := en;
  chkUseResume.Enabled  := en;
  chkBackup.Enabled     := en;
end;

// --------------------------------------------------------------------------
// Browse for player executable
// --------------------------------------------------------------------------
procedure BrowseExeClick(Sender: TObject);
var F: String;
begin
  F := edtPlayerExe.Text;
  if GetOpenFileName('', F, '',
    'Executables (*.exe)|*.exe|All files (*.*)|*.*', 'exe') then
    edtPlayerExe.Text := F;
end;

// --------------------------------------------------------------------------
// Browse for Kodi executable
// --------------------------------------------------------------------------
procedure BrowseKodiExeClick(Sender: TObject);
var F: String;
begin
  F := edtKodiExe.Text;
  if GetOpenFileName('', F, '',
    'Executables (*.exe)|*.exe|All files (*.*)|*.*', 'exe') then
    edtKodiExe.Text := F;
end;

// --------------------------------------------------------------------------
// Create wizard pages
// --------------------------------------------------------------------------
procedure InitializeWizard;
var
  PW: Integer;
  ExistingExe: String;
begin
  // ── Page 1: Kodi connection ───────────────────────────────────────────────
  ConfigPage := CreateInputQueryPage(
    wpSelectDir,
    CustomMessage('ConfigPageTitle'),
    CustomMessage('ConfigPageSubtitle'),
    CustomMessage('ConfigPageDesc')
  );
  ConfigPage.Add(CustomMessage('ConfigHost'),     False);
  ConfigPage.Add(CustomMessage('ConfigHttpPort'), False);
  ConfigPage.Add(CustomMessage('ConfigWsPort'),   False);
  ConfigPage.Add(CustomMessage('ConfigUser'),     False);
  ConfigPage.Add(CustomMessage('ConfigPass'),     True);

  ConfigPage.Values[0] := 'localhost';
  ConfigPage.Values[1] := '8080';
  ConfigPage.Values[2] := '9090';
  ConfigPage.Values[3] := '';
  ConfigPage.Values[4] := '';

  // ── Page 2: External player ───────────────────────────────────────────────
  PlayerPage := CreateCustomPage(
    ConfigPage.ID,
    CustomMessage('PlayerPageTitle'),
    CustomMessage('PlayerPageSubtitle')
  );

  PW := PlayerPage.Surface.Width;

  // ── Row A (Y=0): master enable checkbox ───────────────────────────────────
  chkEnablePlayer := TNewCheckBox.Create(PlayerPage.Surface);
  chkEnablePlayer.Parent  := PlayerPage.Surface;
  chkEnablePlayer.SetBounds(0, 0, PW, ScaleY(20));
  chkEnablePlayer.Caption := CustomMessage('PlayerEnable');
  chkEnablePlayer.Checked := False;
  chkEnablePlayer.OnClick := @TogglePlayerControls;

  // ── Row B (Y≈40): exe label ───────────────────────────────────────────────
  lblPlayerExe := TLabel.Create(PlayerPage.Surface);
  lblPlayerExe.Parent   := PlayerPage.Surface;
  lblPlayerExe.AutoSize := False;
  lblPlayerExe.SetBounds(0, ScaleY(40), PW, ScaleY(17));
  lblPlayerExe.Caption  := CustomMessage('PlayerExeLbl');
  lblPlayerExe.Enabled  := False;

  // ── Row C (Y≈59): exe edit + browse button ────────────────────────────────
  edtPlayerExe := TNewEdit.Create(PlayerPage.Surface);
  edtPlayerExe.Parent  := PlayerPage.Surface;
  edtPlayerExe.SetBounds(0, ScaleY(59), PW - ScaleX(90), ScaleY(23));
  edtPlayerExe.Text    := 'C:\Program Files\MPC-HC\mpc-hc64.exe';
  edtPlayerExe.Enabled := False;

  btnBrowseExe := TNewButton.Create(PlayerPage.Surface);
  btnBrowseExe.Parent   := PlayerPage.Surface;
  btnBrowseExe.SetBounds(PW - ScaleX(86), ScaleY(59), ScaleX(86), ScaleY(23));
  btnBrowseExe.Caption  := CustomMessage('PlayerBrowseBtn');
  btnBrowseExe.Enabled  := False;
  btnBrowseExe.OnClick  := @BrowseExeClick;

  // ── Row D (Y≈100): resume checkbox ───────────────────────────────────────
  chkUseResume := TNewCheckBox.Create(PlayerPage.Surface);
  chkUseResume.Parent   := PlayerPage.Surface;
  chkUseResume.SetBounds(0, ScaleY(100), PW, ScaleY(20));
  chkUseResume.Caption  := CustomMessage('PlayerUseResume');
  chkUseResume.Checked  := True;
  chkUseResume.Enabled  := False;

  // ── Row E (Y≈132): backup checkbox ───────────────────────────────────────
  chkBackup := TNewCheckBox.Create(PlayerPage.Surface);
  chkBackup.Parent   := PlayerPage.Surface;
  chkBackup.SetBounds(0, ScaleY(132), PW, ScaleY(20));
  chkBackup.Caption  := CustomMessage('PlayerBackupChk');
  chkBackup.Checked  := True;
  chkBackup.Enabled  := False;

  // ── Row F (Y≈172): kiosk – hide explorer checkbox ────────────────────────
  chkHideExplorer := TNewCheckBox.Create(PlayerPage.Surface);
  chkHideExplorer.Parent   := PlayerPage.Surface;
  chkHideExplorer.SetBounds(0, ScaleY(172), PW, ScaleY(20));
  chkHideExplorer.Caption  := CustomMessage('KioskHideExplorer');
  chkHideExplorer.Checked  := False;

  // ── Row G (Y≈202): Kodi exe label ────────────────────────────────────────
  lblKodiExe := TLabel.Create(PlayerPage.Surface);
  lblKodiExe.Parent   := PlayerPage.Surface;
  lblKodiExe.AutoSize := False;
  lblKodiExe.SetBounds(0, ScaleY(202), PW, ScaleY(17));
  lblKodiExe.Caption  := CustomMessage('KioskKodiExeLbl');

  // ── Row H (Y≈221): Kodi exe edit + browse button ─────────────────────────
  edtKodiExe := TNewEdit.Create(PlayerPage.Surface);
  edtKodiExe.Parent  := PlayerPage.Surface;
  edtKodiExe.SetBounds(0, ScaleY(221), PW - ScaleX(90), ScaleY(23));
  edtKodiExe.Text    := 'C:\Program Files\Kodi\Kodi.exe';

  btnBrowseKodi := TNewButton.Create(PlayerPage.Surface);
  btnBrowseKodi.Parent   := PlayerPage.Surface;
  btnBrowseKodi.SetBounds(PW - ScaleX(86), ScaleY(221), ScaleX(86), ScaleY(23));
  btnBrowseKodi.Caption  := CustomMessage('PlayerBrowseBtn');
  btnBrowseKodi.OnClick  := @BrowseKodiExeClick;

  // ── Row F hook: toggling hide-explorer enables/disables shell-mode ────────
  chkHideExplorer.OnClick := @ToggleKioskControls;

  // ── Row I (Y≈262): shell-mode checkbox (sub-option of hide-explorer) ──────
  chkShellMode := TNewCheckBox.Create(PlayerPage.Surface);
  chkShellMode.Parent   := PlayerPage.Surface;
  chkShellMode.SetBounds(ScaleX(20), ScaleY(262), PW - ScaleX(20), ScaleY(20));
  chkShellMode.Caption  := CustomMessage('KioskShellMode');
  chkShellMode.Checked  := False;
  chkShellMode.Enabled  := False;   // only active when chkHideExplorer is checked

  // ── Pre-fill from existing config.json on upgrade ─────────────────────────
  if ConfigExists then begin
    ExistingExe := ReadConfigString('mpchc_exe_path');
    if Trim(ExistingExe) <> '' then begin
      edtPlayerExe.Text      := ExistingExe;
      chkEnablePlayer.Checked := True;
      chkUseResume.Checked    := ReadConfigBool('resume_enabled');
      TogglePlayerControls(nil);
    end;
    if ReadConfigBool('hide_explorer') then begin
      chkHideExplorer.Checked := True;
      ToggleKioskControls(nil);     // enable chkShellMode
    end;
    if ReadConfigBool('shell_mode') then
      chkShellMode.Checked := True;
    ExistingExe := ReadConfigString('kodi_exe_path');
    if Trim(ExistingExe) <> '' then
      edtKodiExe.Text := ExistingExe;
  end;
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

  // ── Kodi config page ──────────────────────────────────────────────────────
  if (CurPageID = ConfigPage.ID) and (not ShouldSkipPage(CurPageID)) then begin
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

  // ── External player page ─────────────────────────────────────────────────
  if CurPageID = PlayerPage.ID then begin
    if chkEnablePlayer.Checked and (Trim(edtPlayerExe.Text) = '') then begin
      MsgBox(CustomMessage('ErrPlayerNoExe'), mbError, MB_OK);
      Result := False; Exit;
    end;
  end;
end;

// --------------------------------------------------------------------------
// Create autostart Task Scheduler entry.
// --------------------------------------------------------------------------
procedure CreateAutostartTask;
var
  AppPath, ScriptPath, Script: String;
  rc: Integer;
begin
  AppPath    := ExpandConstant('{app}\{#AppExe}');
  ScriptPath := ExpandConstant('{tmp}\kodi_create_task.ps1');

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
// Add firewall rule — requires admin → UAC prompt.
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
// Write playercorefactory.xml to %APPDATA%\Kodi\userdata\
// --------------------------------------------------------------------------
procedure WritePlayerCoreFactory;
var
  KodiUD, XmlPath, BakPath: String;
  PlayerName, Exe, Args: String;
  Xml: String;
  MpcBase: String;
begin
  KodiUD  := GetEnv('APPDATA') + '\Kodi\userdata';
  XmlPath := KodiUD + '\playercorefactory.xml';
  BakPath := XmlPath + '.bak';

  ForceDirectories(KodiUD);

  // Back up existing config once (never overwrite an existing .bak)
  if chkBackup.Checked then
    if FileExists(XmlPath) and (not FileExists(BakPath)) then
      FileCopy(XmlPath, BakPath, False);

  if chkUseResume.Checked then begin
    // ── Resume mode: Bridge is the external player ─────────────────────────
    PlayerName := 'Kodi-MPC-HC Bridge';
    Exe        := ExpandConstant('{app}\{#AppExe}');
    Args       := '--play "{1}"';
  end else begin
    // ── Direct mode: MPC-HC launched directly ─────────────────────────────
    Exe     := Trim(edtPlayerExe.Text);
    Args    := '"{1}" /fullscreen';
    MpcBase := LowerCase(ExtractFileName(Exe));
    if Pos('mpc-be', MpcBase) > 0 then
      PlayerName := 'MPC-BE'
    else
      PlayerName := 'MPC-HC';
  end;

  Xml :=
    '<?xml version="1.0" encoding="utf-8"?>' + #13#10 +
    '<playercorefactory>' + #13#10 +
    '  <players>' + #13#10 +
    '    <player' +
      ' name="'  + EscapeXmlAttr(PlayerName) + '"' +
      ' type="ExternalPlayer"' +
      ' audio="false"' +
      ' video="true">' + #13#10 +
    '      <filename>'    + EscapeXmlContent(Exe)  + '</filename>'    + #13#10 +
    '      <args>'        + EscapeXmlContent(Args) + '</args>'        + #13#10 +
    '      <hidexbmc>true</hidexbmc>'       + #13#10 +
    '      <hideconsole>true</hideconsole>' + #13#10 +
    '    </player>' + #13#10 +
    '  </players>' + #13#10 +
    '  <rules action="prepend">' + #13#10 +
    '    <rule video="true" audio="false"' +
      ' player="' + EscapeXmlAttr(PlayerName) + '"/>' + #13#10 +
    '  </rules>' + #13#10 +
    '</playercorefactory>';

  SaveStringToFile(XmlPath, Xml, False);
end;

// --------------------------------------------------------------------------
// After installation: write config.json + player config + autostart + firewall
// --------------------------------------------------------------------------
procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigFile: String;
  Lines: TStringList;
  Json: String;
  ResumeStr, HideExplorerStr, ShellModeStr: String;
begin
  if CurStep <> ssPostInstall then Exit;

  // --- config.json (first installation only) ---
  ConfigFile := ExpandConstant('{app}\config.json');
  if not FileExists(ConfigFile) then begin
    if chkUseResume.Checked    then ResumeStr      := 'true' else ResumeStr      := 'false';
    if chkHideExplorer.Checked then HideExplorerStr := 'true' else HideExplorerStr := 'false';
    if chkShellMode.Checked    then ShellModeStr    := 'true' else ShellModeStr    := 'false';

    if chkEnablePlayer.Checked then begin
      Json :=
        '{' + #13#10 +
        '  "kodi_host": "'       + EscapeJson(Trim(ConfigPage.Values[0])) + '",' + #13#10 +
        '  "kodi_port": '        + IntToStr(StrToIntDef(ConfigPage.Values[1], 8080)) + ',' + #13#10 +
        '  "kodi_ws_port": '     + IntToStr(StrToIntDef(ConfigPage.Values[2], 9090)) + ',' + #13#10 +
        '  "kodi_username": "'   + EscapeJson(ConfigPage.Values[3]) + '",' + #13#10 +
        '  "kodi_password": "'   + EscapeJson(ConfigPage.Values[4]) + '",' + #13#10 +
        '  "kodi_ssl": false,' + #13#10 +
        '  "kodi_enabled": true,' + #13#10 +
        '  "mpchc_host": "localhost",' + #13#10 +
        '  "mpchc_port": 13579,' + #13#10 +
        '  "mpchc_enabled": true,' + #13#10 +
        '  "server_host": "0.0.0.0",' + #13#10 +
        '  "server_port": 13590,' + #13#10 +
        '  "mpchc_exe_path": "' + EscapeJson(Trim(edtPlayerExe.Text)) + '",' + #13#10 +
        '  "resume_enabled": ' + ResumeStr + ',' + #13#10 +
        '  "kodi_exe_path": "' + EscapeJson(Trim(edtKodiExe.Text)) + '",' + #13#10 +
        '  "hide_explorer": ' + HideExplorerStr + ',' + #13#10 +
        '  "shell_mode": ' + ShellModeStr + #13#10 +
        '}';
    end else begin
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
        '  "server_port": 13590,' + #13#10 +
        '  "kodi_exe_path": "' + EscapeJson(Trim(edtKodiExe.Text)) + '",' + #13#10 +
        '  "hide_explorer": ' + HideExplorerStr + ',' + #13#10 +
        '  "shell_mode": ' + ShellModeStr + #13#10 +
        '}';
    end;
    Lines := TStringList.Create;
    try
      Lines.Text := Json;
      Lines.SaveToFile(ConfigFile);
    finally
      Lines.Free;
    end;
  end;

  // --- External player config (only if user enabled it) ---
  if chkEnablePlayer.Checked then
    WritePlayerCoreFactory;

  // --- Always sync kiosk fields in config.json (handles upgrades too) ---
  UpdateKioskConfig;

  // --- Shell-mode registry key ---
  // HKCU\...\Winlogon\Shell → bridge path  (shell-mode ON)
  //                         → deleted       (shell-mode OFF → Windows uses HKLM default = explorer.exe)
  if chkShellMode.Checked then
    RegWriteStringValue(HKCU,
      'Software\Microsoft\Windows NT\CurrentVersion\Winlogon',
      'Shell', ExpandConstant('{app}\{#AppExe}'))
  else
    RegDeleteValue(HKCU,
      'Software\Microsoft\Windows NT\CurrentVersion\Winlogon',
      'Shell');

  // --- Watchdog task (shell-mode only) ---
  // Creates watchdog.ps1 in {app} and registers the task.
  // Always delete first to remove a stale task from a previous install.
  DeleteWatchdogTask;
  if chkShellMode.Checked then
    CreateWatchdogTask;

  // --- Autostart task ---
  // In shell-mode the registry Shell key starts the bridge on login automatically;
  // a separate task is not needed (and a second instance would fail to bind the port).
  if chkShellMode.Checked then
    DeleteAutostartTask
  else if WizardIsTaskSelected('autostart') then
    CreateAutostartTask
  else
    DeleteAutostartTask;

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

    // Remove watchdog task + script
    DeleteWatchdogTask;
    DeleteFile(ExpandConstant('{app}\watchdog.ps1'));

    // Restore Windows shell: remove HKCU override so Windows falls back
    // to the HKLM default (explorer.exe).  Safe no-op if never set.
    RegDeleteValue(HKCU,
      'Software\Microsoft\Windows NT\CurrentVersion\Winlogon',
      'Shell');

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
  ShellVal: String;
begin
  // If bridge is registered as the Windows shell, start Explorer before
  // killing the bridge so the user keeps a usable desktop during the upgrade.
  if RegQueryStringValue(HKCU,
      'Software\Microsoft\Windows NT\CurrentVersion\Winlogon',
      'Shell', ShellVal) then begin
    if Pos(LowerCase('{#AppExe}'), LowerCase(ShellVal)) > 0 then begin
      Exec('explorer.exe', '', '', SW_SHOW, ewNoWait, rc);
      Sleep(2000);  // give Explorer time to draw the desktop
    end;
  end;
  Exec('taskkill', '/f /im {#AppExe}', '', SW_HIDE, ewWaitUntilTerminated, rc);
  Result := '';
end;
