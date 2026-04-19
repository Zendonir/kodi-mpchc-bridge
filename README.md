# Kodi ↔ MPC-HC Bridge

A lightweight Windows bridge that connects **Kodi** and **MPC-HC** (clsid2 fork) so a UC Remote — or any WebSocket client — can control both players through a single unified API.

---

## Features

### Playback & Control
- **Unified remote control** — one endpoint for Kodi and MPC-HC; commands are automatically routed to the active player
- **Smart navigation routing** — arrow/back/home commands go to MPC-HC (keyboard injection) when MPC-HC is active, otherwise forwarded to Kodi
- **Full playback commands** — play/pause, stop, seek (absolute + relative + custom interval), skip ±1 min, chapter prev/next, small seek ±10 s
- **Volume control** — set, up/down, mute (mirrored from Kodi even while MPC-HC is active)
- **Audio & subtitle track selection** — for both players
- **Shuffle & repeat** — Kodi playlist controls
- **Fullscreen toggle** — Alt+Enter for MPC-HC, Kodi action for Kodi, F11 for foreground window when idle

### Media Metadata
- **MKV / video container parsing** — audio tracks, subtitles, chapters, resolution, FPS, bitrate parsed directly from the file (`.mkv` via EBML, other containers via ffprobe fallback)
- **HDR detection** — HDR10, HLG, Dolby Vision — from Kodi `hdrtype`, MKV EBML colour primaries, or ffprobe
- **Rich TV episode info** — series title, season, episode number, season/episode counts ("Episode 5 of 15 · Season 2 of 3"), episode rating
- **Music metadata** — artist, album
- **Track details** — language, codec, channels, forced/default flags for audio and subtitle tracks; chapter timestamps

### Cover Art
- **Kodi library artwork** — fetches from Kodi's texture cache with configurable mode per media type:
  - Movies: poster / fanart / thumbnail
  - TV episodes: series poster / season poster / episode thumbnail / fanart
  - Music: album cover (thumb) / fanart
- **Local poster fallback** — scans the video folder for `poster.jpg`, `folder.jpg`, `cover.jpg`, `<filename>.jpg`, etc.
- **Show poster fallback** — if per-episode art lookup fails, fetches the TV show poster directly
- **Art served via bridge** — cached and proxied at `GET /api/artwork`

### Season Episode List
- **Full season list** — fetched from Kodi library when an episode is playing via MPC-HC
- **Watched / resume status** — shows ✓ watched badge and resume-point timestamp per episode
- **Click to play** — clicking any episode in the web UI launches it in MPC-HC immediately
- **Next / prev episode buttons** — navigate within the season from the remote or web UI
- **Auto-advance** — automatically plays the next episode when ≤ 5 seconds remain

### Kodi Library Sync
- **Watched sync** — marks a video as watched when ≥ 90 % was played (overrides Kodi's auto-mark)
- **Resume point save** — saves position to Kodi library when ≥ 60 s were watched but not finished
- **Watched reset** — resets auto-watch flag when the video was stopped very early
- **Immediate library refresh** — notifies Kodi to update its UI (progress bar, checkmark) right away

### External Player Integration
- **Resume dialog** — full-screen overlay (tkinter) shown when a Kodi resume position ≥ 60 s exists; supports both keyboard and remote navigation
- **Auto-seek on launch** — polls MPC-HC HTTP API until ready, then seeks to the saved position
- **SMB → UNC conversion** — converts `smb://host/share/...` paths to `\\host\share\...` for MPC-HC
- **playercorefactory.xml auto-setup** — written automatically via the web UI "External Player Setup"; existing file backed up
- **Toggle external player** — enable/disable on the fly (renames the XML, no restart needed); state broadcast to all clients

### Kiosk Mode
- **Explorer shell control** — hides Windows Explorer (taskbar + desktop) on startup, restores on exit
- **Shell mode** — bridge can be configured as the Windows shell (`shell_mode=true`), replacing `explorer.exe` at login
- **Kodi lifecycle management** — auto-launches Kodi on startup; kill/restart/focus via web UI or remote command
- **Toggle command** — `kodi_windows` switches between Kodi (kiosk) and Windows desktop in one button press
- **Kiosk web UI** — dedicated Kodi / Windows / Restart-Kodi buttons with live status highlighting

### Server & API
- **WebSocket push** — real-time state updates; `state_full` on connect, `state_patch` on every change
- **REST API** — full HTTP API (see [API](#api) section)
- **In-browser log viewer** — filterable by level (DEBUG / INFO / WARNING / ERROR) and keyword, with auto-refresh
- **Built-in web UI** — dark-theme control and monitoring page served on the bridge port
- **Keyboard shortcuts in web UI** — arrow keys, Enter, Esc, Space, `[`/`]` for custom seek

### System
- **System tray icon** — status indicator, Settings dialog, Test Interface (Windows)
- **Headless mode** — `--headless` flag, no tray icon (suitable for Launcher4Kodi / kiosk shells)
- **Single-instance guard** — named mutex prevents duplicate tray icons
- **Rotating log file** — `kodi-bridge.log` (2 MB × 3 backups)
- **Multilanguage UI** — browser locale auto-detected: 🇬🇧 EN · 🇩🇪 DE · 🇫🇷 FR · 🇪🇸 ES · 🇮🇹 IT
- **System restart** — schedules Windows restart in 10 s via `shutdown.exe`

---

## Requirements

| Component | Minimum |
|-----------|---------|
| Windows | 10 / 11 (64-bit) |
| Kodi | 20+ with HTTP API (port 8080) + WebSocket (port 9090) enabled |
| MPC-HC | [clsid2 fork](https://github.com/clsid2/mpc-hc) with Web Interface (port 13579) enabled |

---

## Installation

1. Download `kodi-mpchc-bridge-setup-*.exe` from the [latest release](https://github.com/Zendonir/kodi-mpchc-bridge/releases/latest)
2. Run the installer — **no administrator rights required**
3. Enter your Kodi host/port in the wizard
4. Choose autostart and firewall options
5. The bridge starts automatically and a **tray icon** appears

The installer places everything in `%LocalAppData%\Programs\kodi-mpchc-bridge\`.

> The installer UI language is detected automatically from your Windows locale.

---

## Usage

| Action | How |
|--------|-----|
| Open web interface | Browser → `http://localhost:13590` |
| Open test interface | Double-click tray icon |
| Change settings | Right-click tray → Settings |
| View logs | `%LocalAppData%\Programs\kodi-mpchc-bridge\kodi-bridge.log` or web UI → Log |
| Stop | Right-click tray → Quit |

### External player setup

Open the web UI at `http://localhost:13590`, click **Settings → External Player Setup** and enter the path to `mpc-hc64.exe`. The bridge writes `playercorefactory.xml` into Kodi's userdata folder automatically.

### Headless mode (server / kiosk)

```bat
kodi-bridge.exe --headless
```

No tray icon, suitable for Launcher4Kodi or other shells that don't load Explorer.

### Kiosk mode

Set `hide_explorer = true` and `kodi_exe_path` in `config.json` (or via the web UI Settings card). On startup the bridge kills Explorer, launches Kodi, and restores Explorer when it exits.

For a fully shell-less setup set `shell_mode = true` and add `kodi-bridge.exe` as the Windows shell in the registry — Explorer is never started at login.

---

## API

### WebSocket — `ws://host:13590/api/ws`

```jsonc
// On connect
{ "type": "state_full",  "data": { /* full state */ } }

// On change
{ "type": "state_patch", "data": { /* changed fields only */ } }
```

### POST `/api/command`

```jsonc
{ "cmd": "play_pause" }
{ "cmd": "stop" }
{ "cmd": "next_chapter" }
{ "cmd": "prev_chapter" }
{ "cmd": "skip_forward" }          // +1 min
{ "cmd": "skip_backward" }         // −1 min
{ "cmd": "seek_forward_small" }    // +10 s
{ "cmd": "seek_backward_small" }   // −10 s
{ "cmd": "seek",           "value": 120.5 }   // absolute seconds
{ "cmd": "seek_relative",  "value": -30 }     // relative seconds
{ "cmd": "set_volume",     "value": 75 }      // 0–100
{ "cmd": "volume_up" }
{ "cmd": "volume_down" }
{ "cmd": "mute" }
{ "cmd": "audio_track",    "value": 1 }       // 0-based index
{ "cmd": "subtitle_track", "value": -1 }      // -1 = off
{ "cmd": "shuffle" }                          // toggle
{ "cmd": "repeat",         "value": "all" }   // "off" | "one" | "all"
{ "cmd": "navigate_up" }
{ "cmd": "navigate_down" }
{ "cmd": "navigate_left" }
{ "cmd": "navigate_right" }
{ "cmd": "navigate_select" }
{ "cmd": "navigate_back" }
{ "cmd": "navigate_home" }
{ "cmd": "context_menu" }
{ "cmd": "show_info" }
{ "cmd": "show_osd" }                         // always sent to Kodi
{ "cmd": "fullscreen" }
{ "cmd": "next_episode" }
{ "cmd": "prev_episode" }
{ "cmd": "toggle_external_player" }
{ "cmd": "kodi_windows" }                     // minimize/restore Kodi or kiosk toggle
{ "cmd": "system_restart" }                   // Windows restart in 10 s
{ "cmd": "mpchc_next_audio" }                 // MPC-HC only
{ "cmd": "mpchc_prev_audio" }                 // MPC-HC only
```

### GET `/api/state` — full state snapshot

### GET/POST `/api/config` — read / update `config.json`

### GET `/api/artwork` — current cover art (JPEG/PNG)

### GET `/api/logs?limit=50&level=INFO&search=keyword` — recent log records

### POST `/api/external_play` — launch MPC-HC for a file path

```jsonc
{ "filepath": "C:\\Movies\\film.mkv" }
```

### GET `/api/external_player` — external player config status

### POST `/api/external_player/setup` — write playercorefactory.xml

```jsonc
{ "mpchc_exe": "C:\\Program Files\\MPC-HC\\mpc-hc64.exe", "resume_enabled": true }
```

### Kiosk endpoints

```
POST /api/kiosk/kodi      — hide Explorer, launch/focus Kodi
POST /api/kiosk/windows   — kill Kodi, restore Explorer
POST /api/kiosk/restart   — kill Kodi and relaunch
GET  /api/kiosk/status    — { "kodi_running": bool, "explorer_hidden": bool }
```

---

## State fields

| Field | Type | Description |
|-------|------|-------------|
| `active_player` | `"kodi"` \| `"mpchc"` \| `"none"` | Which player is active |
| `state` | `"playing"` \| `"paused"` \| `"stopped"` \| `"idle"` | Playback state |
| `position` | float | Current position in seconds |
| `duration` | float | Total duration in seconds |
| `title` | string | Title / filename |
| `media_type` | `"movie"` \| `"episode"` \| `"music"` \| `"other"` \| `""` | |
| `tv_show` | string | Series name (episodes only) |
| `season` / `episode` | int | Current season / episode number |
| `season_count` / `episode_count` | int | Total seasons / episodes in season |
| `artist` / `album` | string | Music metadata |
| `year` | int | Release year |
| `rating` | float | Kodi rating |
| `hdr` | `"HDR10"` \| `"HLG"` \| `"DV"` \| `""` | HDR type (empty = SDR) |
| `video_width` / `video_height` | int | Resolution in pixels |
| `video_fps` | float | Frames per second |
| `video_codec` | string | Video codec identifier |
| `video_bitrate_kbps` | int | Video bitrate in kbps |
| `audio_tracks` | array | Available audio tracks (pos, label, language, codec, channels, forced, default) |
| `subtitle_tracks` | array | Available subtitle tracks |
| `chapters` | array | Chapter list (pos, name, time_ms) |
| `current_audio` | int | Active audio track index |
| `current_subtitle` | int | Active subtitle index (−1 = off) |
| `current_chapter` | int | Current chapter index |
| `volume` | int | Volume 0–100 |
| `muted` | bool | Mute state |
| `shuffle` | bool | Shuffle active |
| `repeat` | `"off"` \| `"one"` \| `"all"` | Repeat mode |
| `artwork_url` | string | Cover art URL (proxied through bridge) |
| `season_episodes` | array | Full episode list for current season |
| `playlist_index` | int | 0-based index of current episode in list (−1 = unknown) |
| `external_player_enabled` | bool | Whether external player is currently active |

---

## Configuration (`config.json`)

```jsonc
{
  // Kodi
  "kodi_host":     "localhost",
  "kodi_port":     8080,
  "kodi_ws_port":  9090,
  "kodi_username": "kodi",
  "kodi_password": "kodi",
  "kodi_ssl":      false,
  "kodi_enabled":  true,

  // MPC-HC
  "mpchc_host":    "localhost",
  "mpchc_port":    13579,
  "mpchc_enabled": true,

  // Bridge server
  "server_host":   "0.0.0.0",
  "server_port":   13590,

  // External player
  "mpchc_exe_path":           "",     // full path to mpc-hc64.exe / mpc-be64.exe
  "resume_enabled":           false,  // seek to Kodi resume position on launch
  "external_player_enabled":  true,   // false → Kodi uses its own player

  // Artwork mode (per media type)
  "movie_art_mode":   "poster",         // "poster" | "fanart" | "thumb"
  "episode_art_mode": "poster",         // "poster" | "season.poster" | "thumb" | "fanart"
  "music_art_mode":   "thumb",          // "thumb" | "fanart"

  // Kiosk mode
  "kodi_exe_path":  "",     // full path to Kodi.exe
  "hide_explorer":  false,  // kill Explorer on startup, launch Kodi
  "shell_mode":     false   // bridge is the Windows shell (no Explorer at login)
}
```

Located at `%LocalAppData%\Programs\kodi-mpchc-bridge\config.json`.  
Editable via **tray → Settings**, the **web UI Settings card**, or directly with a text editor (restart required for most changes; artwork mode and kiosk path apply immediately).

---

## Building from source

```bat
pip install aiohttp yarl Pillow pystray pyinstaller
pyinstaller bridge.spec
:: Installer (requires Inno Setup 6)
iscc /DAppVersion=1.2.3 installer.iss
```

Output: `dist\kodi-bridge.exe` and `dist\kodi-mpchc-bridge-setup-1.2.3.exe`

---

## License

MIT
