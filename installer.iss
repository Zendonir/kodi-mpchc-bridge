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
; -- External player wizard page --
english.PlayerPageTitle=Configure external player
english.PlayerPageSubtitle=Play Kodi videos directly in MPC-HC / MPC-BE (optional)
english.PlayerEnable=Configure Kodi to open videos in an external player
english.PlayerExeLbl=MPC-HC / MPC-BE executable:
english.PlayerBrowseBtn=Browse...
english.PlayerUseResume=Use built-in resume (seek MPC-HC to Kodi's saved position)
english.PlayerBackupChk=Backup existing playercorefactory.xml as .bak
english.ErrPlayerNoExe=Please select the MPC-HC / MPC-BE executable.

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

  // ── External player page ──────────────────────────────────────────────────
  PlayerPage:      TWizardPage;
  chkEnablePlayer: TNewCheckBox;
  edtPlayerExe:    TNewEdit;
  btnBrowseExe:    TNewButton;
  chkUseResume:    TNewCheckBox;
  chkBackup:       TNewCheckBox;

// --------------------------------------------------------------------------
// Helper: config.json exists? (upgrade detection)
// --------------------------------------------------------------------------
function ConfigExists: Boolean;
begin
  Result := FileExists(ExpandConstant('{app}\config.json'));
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
// Enable / disable all player-page sub-controls
// --------------------------------------------------------------------------
procedure TogglePlayerControls(Sender: TObject);
var e: Boolean;
begin
  e := chkEnablePlayer.Checked;
  edtPlayerExe.Enabled := e;
  btnBrowseExe.Enabled := e;
  chkUseResume.Enabled := e;
  chkBackup.Enabled    := e;
end;

// --------------------------------------------------------------------------
// Browse for player exe
// --------------------------------------------------------------------------
procedure BrowseExeClick(Sender: TObject);
var FileName: String;
begin
  FileName := edtPlayerExe.Text;
  if GetOpenFileName(
    '',
    FileName,
    '',
    'Executables (*.exe)|*.exe|All files (*.*)|*.*',
    'exe'
  ) then
    edtPlayerExe.Text := FileName;
end;

// --------------------------------------------------------------------------
// Create wizard pages
// --------------------------------------------------------------------------
procedure InitializeWizard;
var
  PW, BH: Integer;
  lbl: TLabel;
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

  // ── Page 2: External player (optional) ───────────────────────────────────
  PlayerPage := CreateCustomPage(
    ConfigPage.ID,
    CustomMessage('PlayerPageTitle'),
    CustomMessage('PlayerPageSubtitle')
  );

  PW := PlayerPage.Surface.Width;  // ~428 px at 96 DPI
  BH := 23;                        // standard control height

  // ── Group A  (Y=0): Master enable ────────────────────────────────────────
  chkEnablePlayer := TNewCheckBox.Create(WizardForm);
  chkEnablePlayer.Parent  := PlayerPage.Surface;
  chkEnablePlayer.Caption := CustomMessage('PlayerEnable');
  chkEnablePlayer.SetBounds(0, 0, PW, 20);
  chkEnablePlayer.Checked := False;
  chkEnablePlayer.OnClick := @TogglePlayerControls;

  // ── Group B  (Y=50): Exe path ─────────────────────────────────────────────
  lbl := TLabel.Create(WizardForm);
  lbl.Parent   := PlayerPage.Surface;
  lbl.Caption  := CustomMessage('PlayerExeLbl');
  lbl.SetBounds(0, 50, PW, 16);
  lbl.AutoSize := False;

  edtPlayerExe := TNewEdit.Create(WizardForm);
  edtPlayerExe.Parent  := PlayerPage.Surface;
  edtPlayerExe.SetBounds(0, 70, PW - 92, BH);
  edtPlayerExe.Enabled := False;

  btnBrowseExe := TNewButton.Create(WizardForm);
  btnBrowseExe.Parent   := PlayerPage.Surface;
  btnBrowseExe.Caption  := CustomMessage('PlayerBrowseBtn');
  btnBrowseExe.SetBounds(PW - 88, 70, 88, BH);
  btnBrowseExe.Enabled  := False;
  btnBrowseExe.OnClick  := @BrowseExeClick;

  // ── Group C  (Y=120): Resume checkbox ────────────────────────────────────
  chkUseResume := TNewCheckBox.Create(WizardForm);
  chkUseResume.Parent   := PlayerPage.Surface;
  chkUseResume.Caption  := CustomMessage('PlayerUseResume');
  chkUseResume.SetBounds(0, 120, PW, 20);
  chkUseResume.Checked  := True;
  chkUseResume.Enabled  := False;

  // ── Group D  (Y=170): Backup checkbox ────────────────────────────────────
  chkBackup := TNewCheckBox.Create(WizardForm);
  chkBackup.Parent   := PlayerPage.Surface;
  chkBackup.Caption  := CustomMessage('PlayerBackupChk');
  chkBackup.SetBounds(0, 170, PW, 20);
  chkBackup.Checked  := True;
  chkBackup.Enabled  := False;
end;

// --------------------------------------------------------------------------
// Skip config page on upgrade (player page is always shown)
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

  // ── External player page ──────────────────────────────────────────────────
  if CurPageID = PlayerPage.ID then begin
    if chkEnablePlayer.Checked then begin
      if Trim(edtPlayerExe.Text) = '' then begin
        MsgBox(CustomMessage('ErrPlayerNoExe'), mbError, MB_OK);
        Result := False; Exit;
      end;
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

  // Create Kodi userdata directory if it doesn't exist yet
  ForceDirectories(KodiUD);

  // Back up existing config once (never overwrite an existing .bak)
  if chkBackup.Checked then
    if FileExists(XmlPath) and (not FileExists(BakPath)) then
      FileCopy(XmlPath, BakPath, False);

  if chkUseResume.Checked then begin
    // ── Resume mode: Bridge is the external player ─────────────────────────
    // Kodi launches kodi-bridge.exe --play "{filepath}"
    // Bridge reads Kodi resume position and seeks MPC-HC after launch.
    PlayerName := 'Kodi-MPC-HC Bridge';
    Exe        := ExpandConstant('{app}\{#AppExe}');
    Args       := '--play "{filepath}"';
  end else begin
    // ── Direct mode: MPC-HC launched without resume seek ──────────────────
    Exe  := Trim(edtPlayerExe.Text);
    Args := '"{filepath}" /fullscreen';
    // Auto-detect player name from exe filename
    MpcBase := LowerCase(ExtractFileName(Exe));
    if Pos('mpc-be', MpcBase) > 0 then
      PlayerName := 'MPC-BE'
    else
      PlayerName := 'MPC-HC';
  end;

  // Hardcoded defaults: hide Kodi=true, hide console=true, video=true, audio=false
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
    '    <rule' +
      ' video="true"' +
      ' audio="false"' +
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
  ResumeStr: String;
begin
  if CurStep <> ssPostInstall then Exit;

  // --- config.json (first installation only) ---
  ConfigFile := ExpandConstant('{app}\config.json');
  if not FileExists(ConfigFile) then begin
    // Include player settings only when the player page was filled in
    if chkUseResume.Checked then ResumeStr := 'true' else ResumeStr := 'false';
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
        '  "resume_enabled": ' + ResumeStr + #13#10 +
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
        '  "server_port": 13590' + #13#10 +
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
