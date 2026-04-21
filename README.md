# Kodi ↔ MPC-HC Bridge

**DE:** Eine Windows-Bridge zwischen Kodi und MPC-HC mit gemeinsamer REST/WebSocket-API und Web-UI.  
**EN:** A Windows bridge between Kodi and MPC-HC with a unified REST/WebSocket API and web UI.

---

## Inhaltsverzeichnis / Table of Contents

1. [Überblick / Overview](#überblick--overview)
2. [Funktionen / Features](#funktionen--features)
3. [Installation](#installation)
4. [Schnellstart / Quick Start](#schnellstart--quick-start)
5. [Konfiguration / Configuration](#konfiguration--configuration)
6. [Web-UI](#web-ui)
7. [API Referenz / API Reference](#api-referenz--api-reference)
8. [State-Modell / State Model](#state-modell--state-model)
9. [Kiosk & External Player](#kiosk--external-player)
10. [Headless, Tray, Autostart](#headless-tray-autostart)
11. [Fehlerbehebung / Troubleshooting](#fehlerbehebung--troubleshooting)
12. [Projektstruktur / Project Structure](#projektstruktur--project-structure)

---

## Überblick / Overview

**DE:** Die Bridge synchronisiert Kodi, MPC-HC und Remote-Clients. Dadurch gibt es eine zentrale Steuerung, Live-Statusupdates und ein einheitliches Befehlsmodell.  
**EN:** The bridge synchronizes Kodi, MPC-HC, and remote clients. This provides centralized control, live state updates, and a unified command model.

**DE – Kernidee:** Ein Command-Endpoint, ein WebSocket-Stream, automatisches Routing zum aktiven Player.  
**EN – Core idea:** One command endpoint, one WebSocket stream, automatic routing to the currently active player.

---

## Funktionen / Features

### 1) Einheitliche Steuerung / Unified Control
- **DE:** Befehle wie `play_pause`, `seek`, `set_volume`, Trackwechsel und Navigation gehen immer an die Bridge; sie routet automatisch korrekt.
- **EN:** Commands such as `play_pause`, `seek`, `set_volume`, track switching, and navigation are always sent to the bridge; it routes them automatically.

### 2) Intelligentes Routing / Smart Routing
- **DE:** Navigation wird bei aktivem MPC-HC als Tastatursteuerung umgesetzt, sonst an Kodi weitergegeben.
- **EN:** Navigation is translated to keyboard control when MPC-HC is active, otherwise forwarded to Kodi.

### 3) Metadaten / Metadata
- **DE:** Serien-/Musikdaten, Audio-/Untertiteltracks, Kapitel, Auflösung, FPS, Bitrate, HDR-Erkennung.
- **EN:** TV/music metadata, audio/subtitle tracks, chapters, resolution, FPS, bitrate, HDR detection.

### 4) Artwork / Cover Handling
- **DE:** Abruf aus Kodi-Artwork, lokalen Postern und Fallbacks; Ausgabe über `GET /api/artwork`.
- **EN:** Pulls artwork from Kodi, local poster files, and fallbacks; served via `GET /api/artwork`.

### 5) Serienlogik / Episode Logic
- **DE:** Episodenliste pro Staffel, Watch-/Resume-Status, `next_episode`/`prev_episode`, Auto-Advance.
- **EN:** Season episode list, watch/resume status, `next_episode`/`prev_episode`, auto-advance.

### 6) Kodi-Library-Sync
- **DE:** Watch-Status und Resume-Punkte können aktiv in die Kodi-Bibliothek zurückgeschrieben werden.
- **EN:** Watch status and resume points can be written back to the Kodi library.

### 7) External Player
- **DE:** Unterstützung für `playercorefactory.xml`, Resume-Dialog, Auto-Seek, SMB→UNC.
- **EN:** Supports `playercorefactory.xml`, resume dialog, auto-seek, SMB→UNC conversion.

### 8) Kiosk / Shell
- **DE:** Explorer aus-/einblenden, Kodi steuern, optional Shell-Ersatzbetrieb.
- **EN:** Hide/restore Explorer, control Kodi lifecycle, optional shell replacement mode.

---

## Installation

### Voraussetzungen / Requirements
- Windows 10/11 (64-bit)
- Kodi 20+ (HTTP + WebSocket aktiviert / enabled)
- MPC-HC (clsid2) mit Webinterface / with web interface

### Schritte / Steps
1. **DE:** Installer aus dem neuesten Release laden und starten.  
   **EN:** Download and run the latest installer.
2. **DE:** Kodi-Host/Port eintragen.  
   **EN:** Enter Kodi host/port.
3. **DE:** Optional Autostart/Firewall aktivieren.  
   **EN:** Optionally enable autostart/firewall rules.
4. **DE:** Bridge starten und Tray-Symbol prüfen.  
   **EN:** Start bridge and verify tray icon.

---

## Schnellstart / Quick Start

- Web UI: `http://localhost:13590`
- State: `GET http://localhost:13590/api/state`
- WebSocket: `ws://localhost:13590/api/ws`

```bash
curl -X POST http://localhost:13590/api/command \
  -H "Content-Type: application/json" \
  -d '{"cmd":"play_pause"}'
```

---

## Konfiguration / Configuration

**DE:** Die Konfiguration kann über Web-UI oder über `GET/POST /api/config` gepflegt werden.  
**EN:** Configuration can be managed in the web UI or via `GET/POST /api/config`.

Typische Felder / Typical fields:
- Kodi Host, Ports, Credentials
- MPC-HC Host/Port
- Polling/Timing
- External-Player-Optionen / options
- Kiosk-Optionen (`hide_explorer`, `shell_mode`, `kodi_exe_path`)
- Artwork-Modi je Medientyp / artwork modes per media type

---

## Web-UI

**DE:** Die Oberfläche bietet Transportsteuerung, Track-Auswahl, Episodenansicht, Settings, Kiosk-Bedienung und Logviewer.  
**EN:** The UI provides transport controls, track selection, episode view, settings, kiosk controls, and a log viewer.

Shortcuts: Pfeile/Arrows, Enter, Esc, Space, `[` und/and `]`.

---

## API Referenz / API Reference

### WebSocket
`GET ws://<host>:13590/api/ws`

- `state_full` on connect
- `state_patch` on every state change

Example:
```json
{ "type": "state_patch", "data": { "state": "paused", "position": 523.2 } }
```

### REST

#### `POST /api/command`
Body: `{ "cmd": "...", "value": ... }`

Wichtige Kommandos / Important commands:
- Transport: `play_pause`, `stop`
- Kapitel / Chapters: `next_chapter`, `prev_chapter`
- Seek: `skip_forward`, `skip_backward`, `seek_forward_small`, `seek_backward_small`, `seek`, `seek_relative`
- Volume: `set_volume`, `volume_up`, `volume_down`, `mute`
- Tracks: `audio_track`, `subtitle_track`, `mpchc_next_audio`, `mpchc_prev_audio`
- Kodi playlist: `shuffle`, `repeat`
- Navigation: `navigate_up/down/left/right/select/back/home`, `context_menu`, `show_info`, `show_osd`
- Display/System: `fullscreen`, `kodi_windows`, `system_restart`
- Episode: `next_episode`, `prev_episode`
- External player: `toggle_external_player`

Examples:
```json
{ "cmd": "seek", "value": 120.5 }
{ "cmd": "seek_relative", "value": -30 }
{ "cmd": "set_volume", "value": 75 }
{ "cmd": "subtitle_track", "value": -1 }
```

#### Weitere Endpoints / Additional endpoints
- `GET /api/state`
- `GET /api/config`
- `POST /api/config`
- `GET /api/artwork`
- `GET /api/logs?limit=50&level=INFO&search=text`
- `POST /api/external_play`
- `GET /api/external_player`
- `POST /api/external_player/setup`
- `POST /api/kiosk/kodi`
- `POST /api/kiosk/windows`
- `POST /api/kiosk/restart`
- `GET /api/kiosk/status`

---

## State-Modell / State Model

Wichtige Felder / Important fields:
- `active_player`: `kodi` | `mpchc` | `none`
- `state`: `playing` | `paused` | `stopped` | `idle`
- `position`, `duration`
- `title`, `media_type`, `year`, `rating`
- `tv_show`, `season`, `episode`, `season_count`, `episode_count`
- `artist`, `album`
- `video_width`, `video_height`, `video_fps`, `video_codec`, `video_bitrate_kbps`, `hdr`
- `audio_tracks[]`, `subtitle_tracks[]`

**DE:** `state_patch` enthält oft nur Teiländerungen; im Client lokal mergen.  
**EN:** `state_patch` often contains partial changes; merge it into client-side state.

---

## Kiosk & External Player

### Kiosk
- **DE:** Für HTPC-Setups kann Explorer versteckt und Kodi in den Fokus gebracht werden.
- **EN:** For HTPC setups, Explorer can be hidden and Kodi can be forced to foreground.

### External Player (Kodi → MPC-HC)
1. Setup in der Web-UI öffnen / Open setup in web UI.
2. Pfad zu `mpc-hc64.exe` setzen / Set path to `mpc-hc64.exe`.
3. Bridge schreibt `playercorefactory.xml` / Bridge writes `playercorefactory.xml`.
4. Kodi startet Video in MPC-HC / Kodi launches video in MPC-HC.

---

## Headless, Tray, Autostart

- **DE:** Standard ist Tray-Betrieb; Headless startet ohne Tray.
- **EN:** Default is tray mode; headless starts without tray.

```bash
kodi-bridge.exe --headless
```

- **DE:** Single-Instance-Schutz verhindert doppelte Instanzen.
- **EN:** Single-instance protection avoids duplicate bridge processes.

---

## Fehlerbehebung / Troubleshooting

### Keine Kodi-Verbindung / No Kodi connection
- Kodi HTTP/WebSocket aktiv? / enabled?
- Host/Port korrekt? / correct?
- Zugangsdaten korrekt? / valid credentials?
- Firewall-Regel vorhanden? / firewall rule present?

### Falscher Player reagiert / Wrong player reacts
- `GET /api/state` und `active_player` prüfen / verify
- MPC-HC Webinterface aktiv? / enabled?
- Kiosk/Fokusstatus prüfen (`/api/kiosk/status`)

### Kein Artwork / No artwork
- Kodi-Artwork vorhanden? / available?
- Lokale Posterdateien vorhanden? / local poster files present?
- `GET /api/artwork` direkt testen / test directly

### External Player startet nicht / External player does not launch
- `mpc-hc64.exe` Pfad korrekt? / path correct?
- `playercorefactory.xml` erfolgreich erstellt? / created successfully?
- Kodi ggf. neu starten / restart Kodi if needed

---

## Projektstruktur / Project Structure

- `main.py` – Einstiegspunkt / entry point
- `service.py` – Service-Startlogik / service startup logic
- `gui.py` – Tray & GUI-nahe Funktionen / tray & GUI-adjacent functions
- `bridge/server.py` – HTTP/WebSocket server
- `bridge/router.py` – command routing
- `bridge/hub.py` – zentrale Orchestrierung / central orchestration
- `bridge/state.py` – runtime state model
- `bridge/kodi_client.py` – Kodi integration
- `bridge/mpchc_client.py` – MPC-HC integration
- `bridge/mkv_parser.py` – media/container parsing
- `bridge/config.py` – config handling
- `bridge/log_buffer.py` – in-memory log buffer
- `bridge/i18n.py` – localization helpers
