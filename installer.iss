; ============================================================
; Kodi-MPC-HC Bridge — Inno Setup Installer Script
;
; Erstellt einen UAC-freien Installer, der das Programm in
; %LocalAppData%\Programs\kodi-mpchc-bridge installiert.
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

#define AppName        "Kodi-MPC-HC Bridge"
#define AppPublisher   "kodi-mpchc-bridge"
#define AppURL         "https://github.com/Zendonir/kodi-mpchc-bridge"
#define AppExe         "bridge.exe"
#define AppGUID        "{{B7A3C2D1-E4F5-4890-BCDE-F01234567890}"

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
InternalCompressLevel=ultra64

; --- Appearance ---
WizardStyle=modern
WizardSmallImageFile=
SetupIconFile=
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}

; --- Target architecture ---
ArchitecturesInstallIn64BitMode=x64compatible

; --- Misc ---
AllowNoIcons=yes
AlwaysRestart=no
CloseApplications=force

[Languages]
Name: "german";  MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
; German overrides
german.BeveledLabel=Kodi-MPC-HC Bridge Installer

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
; Start Menu — main shortcut
Name: "{group}\{#AppName}"; \
  Filename: "{app}\{#AppExe}"

; Start Menu — uninstaller
Name: "{group}\{#AppName} deinstallieren"; \
  Filename: "{uninstallexe}"

; Desktop shortcut (optional task)
Name: "{commondesktop}\{#AppName}"; \
  Filename: "{app}\{#AppExe}"; \
  Tasks: desktopicon

[Run]
; Offer to start after install
Filename: "{app}\{#AppExe}"; \
  Description: "{#AppName} jetzt starten"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; 1. Kill any running instance
Filename: "taskkill"; \
  Parameters: "/f /im {#AppExe}"; \
  Flags: runhidden waituntilterminated; \
  RunOnceId: "KillBridge"

; 2. Remove Task-Scheduler autostart entry (if set up from within the app)
Filename: "schtasks"; \
  Parameters: "/delete /f /tn KodiMpcHcBridge"; \
  Flags: runhidden; \
  RunOnceId: "RemoveAutostart"

[Code]
// --------------------------------------------------------------------------
// Custom wizard page: show port info + config location note
// --------------------------------------------------------------------------
procedure InitializeWizard;
begin
  // Nothing extra needed right now.
end;

// Warn if bridge.exe is currently running before install/upgrade
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  rc: Integer;
begin
  Exec('taskkill', '/f /im {#AppExe}', '', SW_HIDE,
       ewWaitUntilTerminated, rc);
  Result := '';
end;
