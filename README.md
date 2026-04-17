# Kodi ↔ MPC-HC Bridge

A lightweight Windows bridge that connects **Kodi** and **MPC-HC** (clsid2 fork) so a UC Remote — or any WebSocket client — can control both players through a single unified API.

---

## Features

- **Unified remote control** — one endpoint for Kodi and MPC-HC
- **Live state push** via WebSocket (`state_full` / `state_patch`)
- **MKV metadata** — audio tracks, subtitles, chapters, HDR detection, resolution, FPS, bitrate parsed directly from the container
- **Cover art** — fetched from the Kodi library, with local poster fallback
- **Season / episode counts** — "Episode 5 of 15 · Season 2 of 3"
- **HDR detection** — HDR10, HLG, Dolby Vision (from Kodi `hdrtype` or MKV EBML/BT.2020 primaries)
- **System tray icon** — status indicator, Settings dialog, Test Interface
- **Built-in web UI** — control and monitoring page served on the bridge port
- **Multilanguage** — UI language auto-detected from Windows locale: 🇬🇧 EN · 🇩🇪 DE · 🇫🇷 FR · 🇪🇸 ES · 🇮🇹 IT
- **Single-instance guard** — named mutex prevents duplicate tray icons
- **Rotating log file** — `kodi-bridge.log` (2 MB × 3 backups)

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
| View logs | `%LocalAppData%\Programs\kodi-mpchc-bridge\kodi-bridge.log` |
| Stop | Right-click tray → Quit |

### Headless mode (server / kiosk)

```bat
kodi-bridge.exe --headless
```

No tray icon, suitable for Launcher4Kodi or other shells that don't load Explorer.

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
{ "cmd": "seek",         "value": 120.5 }
{ "cmd": "set_volume",   "value": 75 }
{ "cmd": "audio_track",  "value": 1 }
{ "cmd": "subtitle_track","value": -1 }
```

### GET `/api/state` — full state snapshot

### GET/POST `/api/config` — read / update `config.json`

---

## State fields (selection)

| Field | Type | Description |
|-------|------|-------------|
| `active_player` | `"kodi"` \| `"mpchc"` \| `"none"` | Who is playing |
| `state` | `"playing"` \| `"paused"` \| `"stopped"` | Playback state |
| `title` | string | Title / filename |
| `media_type` | `"movie"` \| `"episode"` \| `"music"` \| `"other"` | |
| `tv_show` | string | Series name (episodes) |
| `season` / `episode` | int | Current season / episode number |
| `season_count` / `episode_count` | int | Total seasons / episodes in season |
| `hdr` | `"HDR10"` \| `"HLG"` \| `"DV"` \| `""` | HDR type |
| `video_width` / `video_height` | int | Resolution in pixels |
| `video_fps` | float | Frames per second |
| `audio_tracks` / `subtitle_tracks` | array | Available tracks |
| `artwork_url` | string | Cover art URL (proxied through bridge) |

---

## Configuration (`config.json`)

```jsonc
{
  "kodi_host":     "localhost",
  "kodi_port":     8080,
  "kodi_ws_port":  9090,
  "kodi_username": "",
  "kodi_password": "",
  "kodi_ssl":      false,
  "kodi_enabled":  true,
  "mpchc_host":    "localhost",
  "mpchc_port":    13579,
  "mpchc_enabled": true,
  "server_host":   "0.0.0.0",
  "server_port":   13590
}
```

Located at `%LocalAppData%\Programs\kodi-mpchc-bridge\config.json`.  
Editable via **tray → Settings** or directly with a text editor (restart required).

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
