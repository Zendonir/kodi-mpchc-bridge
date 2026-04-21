"""
HTTP + WebSocket server.

Provides:
  GET  /api/state          — current unified state as JSON
  POST /api/command        — send a command {"cmd": "...", "value": ...}
  GET  /api/config         — current config as JSON
  POST /api/config         — update config
  WS   /api/ws             — subscribe to state-push stream

WebSocket push format::

    {"type": "state_full", "data": {...}}   # on connect
    {"type": "state_patch", "data": {...}}  # on change
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from aiohttp import web

_LOG = logging.getLogger(__name__)


class BridgeServer:
    def __init__(
        self,
        state_manager,
        router,
        config_manager,
        host: str = "0.0.0.0",
        port: int = 13590,
        on_external_play=None,
        on_player_setup=None,
        on_kiosk_kodi=None,
        on_kiosk_windows=None,
        on_kiosk_restart=None,
        on_kiosk_status=None,
    ) -> None:
        self._state = state_manager
        self._router = router
        self._config = config_manager
        self._host = host
        self._port = port
        self._on_external_play = on_external_play
        self._on_player_setup = on_player_setup
        self._on_kiosk_kodi = on_kiosk_kodi
        self._on_kiosk_windows = on_kiosk_windows
        self._on_kiosk_restart = on_kiosk_restart
        self._on_kiosk_status = on_kiosk_status
        self._ws_clients: set[web.WebSocketResponse] = set()
        self._app = web.Application()
        self._runner: web.AppRunner | None = None
        self._setup_routes()

    def _setup_routes(self) -> None:
        self._app.router.add_get("/api/state", self._handle_state)
        self._app.router.add_post("/api/command", self._handle_command)
        self._app.router.add_get("/api/config", self._handle_config_get)
        self._app.router.add_post("/api/config", self._handle_config_post)
        self._app.router.add_post("/api/external_play", self._handle_external_play)
        self._app.router.add_get("/api/external_player", self._handle_ext_player_get)
        self._app.router.add_post("/api/external_player/setup", self._handle_ext_player_setup)
        self._app.router.add_get("/api/ws", self._handle_ws)
        self._app.router.add_get("/api/artwork", self._handle_artwork)
        self._app.router.add_get("/api/logs", self._handle_logs)
        self._app.router.add_post("/api/kiosk/kodi", self._handle_kiosk_kodi)
        self._app.router.add_post("/api/kiosk/windows", self._handle_kiosk_windows)
        self._app.router.add_post("/api/kiosk/restart", self._handle_kiosk_restart)
        self._app.router.add_get("/api/kiosk/status", self._handle_kiosk_status)
        self._app.router.add_get("/", self._handle_root)
        self._artwork_data: bytes | None = None
        self._artwork_ct: str = "image/jpeg"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def start(self) -> None:
        self._runner = web.AppRunner(self._app, access_log=None)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self._host, self._port)
        await site.start()
        _LOG.info("Bridge server listening on %s:%s", self._host, self._port)

    async def stop(self) -> None:
        # Close all WS clients
        for ws in list(self._ws_clients):
            await ws.close()
        if self._runner:
            await self._runner.cleanup()

    # ------------------------------------------------------------------
    # State push
    # ------------------------------------------------------------------
    async def push_patch(self, patch: dict[str, Any]) -> None:
        """Push a state patch to all connected WS clients."""
        if not patch or not self._ws_clients:
            return
        msg = json.dumps({"type": "state_patch", "data": patch})
        dead = set()
        for ws in self._ws_clients:
            try:
                await ws.send_str(msg)
            except Exception:
                dead.add(ws)
        self._ws_clients -= dead

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------
    async def _handle_root(self, request: web.Request) -> web.Response:
        return web.Response(text=_WEB_UI, content_type="text/html")

    async def _handle_state(self, request: web.Request) -> web.Response:
        return web.json_response(self._state.full())

    async def _handle_command(self, request: web.Request) -> web.Response:
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "invalid JSON"}, status=400)

        cmd = body.get("cmd")
        value = body.get("value")
        if not cmd:
            return web.json_response({"error": "missing cmd"}, status=400)

        ok = await self._router.dispatch(cmd, value)
        return web.json_response({"ok": ok})

    async def _handle_config_get(self, request: web.Request) -> web.Response:
        return web.json_response(self._config.to_dict())

    async def _handle_config_post(self, request: web.Request) -> web.Response:
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "invalid JSON"}, status=400)
        self._config.update(body)
        return web.json_response({"ok": True})

    async def _handle_external_play(self, request: web.Request) -> web.Response:
        """POST /api/external_play — launch MPC-HC for a filepath (resume if configured)."""
        if self._on_external_play is None:
            return web.json_response({"error": "external play not configured"}, status=501)

        # If external player is disabled, tell --play to exit immediately so
        # Kodi falls back to its own internal player without any timeout wait.
        if not self._config.cfg.external_player_enabled:
            _LOG.info("external_play: external player disabled — rejecting launch request")
            return web.json_response({"ok": True, "status": "disabled"})

        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "invalid JSON"}, status=400)
        filepath = (body.get("filepath") or "").strip()
        if not filepath:
            return web.json_response({"error": "missing filepath"}, status=400)
        asyncio.create_task(self._on_external_play(filepath))
        return web.json_response({"ok": True, "status": "launching"})

    async def _handle_ext_player_get(self, request: web.Request) -> web.Response:
        """GET /api/external_player — current external player config."""
        import os
        cfg = self._config.cfg
        appdata = os.environ.get("APPDATA", "")
        xml_path = os.path.join(appdata, "Kodi", "userdata", "playercorefactory.xml") if appdata else ""
        return web.json_response({
            "mpchc_exe_path": cfg.mpchc_exe_path,
            "resume_enabled": cfg.resume_enabled,
            "external_player_enabled": cfg.external_player_enabled,
            "xml_exists": os.path.exists(xml_path),
            "xml_path": xml_path,
        })

    async def _handle_ext_player_setup(self, request: web.Request) -> web.Response:
        """POST /api/external_player/setup — write playercorefactory.xml + update config."""
        if self._on_player_setup is None:
            return web.json_response({"error": "not available"}, status=501)
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "invalid JSON"}, status=400)
        mpchc_exe = (body.get("mpchc_exe") or "").strip()
        if not mpchc_exe:
            return web.json_response({"error": "mpchc_exe is required"}, status=400)
        resume_enabled = bool(body.get("resume_enabled", True))
        ok, detail = self._on_player_setup(mpchc_exe, resume_enabled)
        if ok:
            return web.json_response({"ok": True, "xml_path": detail})
        return web.json_response({"ok": False, "error": detail}, status=500)

    async def _handle_kiosk_kodi(self, request: web.Request) -> web.Response:
        """POST /api/kiosk/kodi — hide Explorer, launch/focus Kodi."""
        if self._on_kiosk_kodi is None:
            return web.json_response({"ok": False, "error": "not configured"}, status=501)
        try:
            ok = await self._on_kiosk_kodi()
            return web.json_response({"ok": ok})
        except Exception as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=500)

    async def _handle_kiosk_windows(self, request: web.Request) -> web.Response:
        """POST /api/kiosk/windows — kill Kodi, restore Explorer."""
        if self._on_kiosk_windows is None:
            return web.json_response({"ok": False, "error": "not configured"}, status=501)
        try:
            ok = await self._on_kiosk_windows()
            return web.json_response({"ok": ok})
        except Exception as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=500)

    async def _handle_kiosk_restart(self, request: web.Request) -> web.Response:
        """POST /api/kiosk/restart — kill Kodi and relaunch it."""
        if self._on_kiosk_restart is None:
            return web.json_response({"ok": False, "error": "not configured"}, status=501)
        try:
            ok = await self._on_kiosk_restart()
            return web.json_response({"ok": ok})
        except Exception as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=500)

    async def _handle_kiosk_status(self, request: web.Request) -> web.Response:
        """GET /api/kiosk/status — current kiosk state for UI button highlighting."""
        if self._on_kiosk_status is None:
            return web.json_response({"kodi_running": False, "explorer_hidden": False})
        try:
            return web.json_response(self._on_kiosk_status())
        except Exception as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=500)

    def set_artwork(self, data: bytes, content_type: str) -> None:
        """Store artwork fetched from Kodi. Called by the hub."""
        self._artwork_data = data
        self._artwork_ct = content_type or "image/jpeg"

    def clear_artwork(self) -> None:
        """Clear cached artwork (e.g. when playback stops)."""
        self._artwork_data = None

    async def _handle_artwork(self, request: web.Request) -> web.Response:
        """GET /api/artwork — serve the cached cover art fetched from Kodi."""
        if not self._artwork_data:
            return web.Response(status=404, text="no artwork")
        return web.Response(body=self._artwork_data, content_type=self._artwork_ct)

    async def _handle_logs(self, request: web.Request) -> web.Response:
        """GET /api/logs?limit=50&level=INFO&search=keyword — last N log records."""
        try:
            from bridge.log_buffer import handler as _buf
            limit  = max(1, min(500, int(request.rel_url.query.get("limit",  "50"))))
            level  = request.rel_url.query.get("level",  "").upper().strip()
            search = request.rel_url.query.get("search", "").strip()
            if level not in ("DEBUG", "INFO", "WARNING", "ERROR"):
                level = ""
            records = _buf.get(limit=limit, level=level, search=search)
        except Exception as exc:
            _LOG.warning("_handle_logs error: %s", exc)
            records = []
        return web.json_response({"records": records})

    async def _handle_ws(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)
        self._ws_clients.add(ws)
        _LOG.debug("WS client connected (%d total)", len(self._ws_clients))

        # Send full state on connect
        try:
            await ws.send_str(json.dumps({"type": "state_full", "data": self._state.full()}))
        except Exception:
            pass

        try:
            async for _ in ws:
                pass  # clients are receive-only on this endpoint
        finally:
            self._ws_clients.discard(ws)
            _LOG.debug("WS client disconnected (%d total)", len(self._ws_clients))

        return ws


# ---------------------------------------------------------------------------
# Embedded web UI — served at /
# ---------------------------------------------------------------------------
_WEB_UI = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>kodi-mpchc-bridge</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:system-ui,sans-serif;background:#111;color:#ddd;padding:16px}
  h1{color:#fff;font-size:1.2rem;margin-bottom:8px}
  #status{display:inline-block;padding:3px 10px;border-radius:12px;font-size:.8rem;
          background:#333;margin-bottom:14px}
  #status.ok{background:#1a5c2a;color:#6f6}
  #status.err{background:#5c1a1a;color:#f66}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
  @media(max-width:640px){.grid{grid-template-columns:1fr}}
  .card{background:#1c1c1c;border-radius:8px;padding:12px}
  .card h2{font-size:.8rem;color:#888;text-transform:uppercase;
           letter-spacing:.06em;margin-bottom:10px}
  table{width:100%;border-collapse:collapse;font-size:.84rem}
  td{padding:3px 6px;border-bottom:1px solid #252525;vertical-align:top}
  td:first-child{color:#888;white-space:nowrap;width:42%}
  td:last-child{color:#fff;word-break:break-word}
  .artwork{max-width:100%;max-height:220px;width:auto;border-radius:6px;
           display:block;margin:0 auto 10px}
  .btns{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:8px}
  button{background:#2a2a2a;color:#ddd;border:1px solid #444;border-radius:6px;
         padding:5px 11px;cursor:pointer;font-size:.84rem;transition:background .15s}
  button:hover{background:#3a3a3a}
  button:active{background:#1e5a8a}
  .dpad{display:inline-grid;grid-template-columns:44px 44px 44px;
        grid-template-rows:44px 44px 44px;gap:4px;vertical-align:middle}
  .dpad button{width:44px;height:44px;padding:0;font-size:1.1rem;font-weight:bold}
  .dpad .ok{background:#1a3d1a;border-color:#2a6a2a;font-size:.85rem}
  .dpad .ok:hover{background:#244d24}
  .nav-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:6px}
  .sep{border-top:1px solid #2a2a2a;margin:8px 0}
  .player-badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:.75rem}
  .player-badge.kodi{background:#1a3d5c;color:#6af}
  .player-badge.mpchc{background:#3d1a1a;color:#f96}
  .player-badge.none{background:#2a2a2a;color:#666}
  .kbd-hint{font-size:.72rem;color:#555;margin-top:6px}
  kbd{background:#222;border:1px solid #444;border-radius:3px;padding:1px 5px;font-size:.75rem}
  /* Season episode list */
  .ep-list{max-height:320px;overflow-y:auto;margin-top:4px}
  .ep-row{display:flex;align-items:center;gap:8px;padding:5px 8px;border-radius:6px;
          cursor:pointer;font-size:.83rem;transition:background .12s}
  .ep-row:hover{background:#2a2a2a}
  .ep-row.ep-current{background:#1a3a1a;border-left:3px solid #4a4}
  .ep-row.ep-watched{color:#555}
  .ep-num{min-width:36px;font-size:.75rem;color:#666;text-align:right;flex-shrink:0}
  .ep-row.ep-current .ep-num{color:#6f6}
  .ep-title{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .ep-row.ep-current .ep-title{color:#eee;font-weight:600}
  .ep-row.ep-watched .ep-title{color:#555}
  .ep-badge{font-size:.72rem;padding:1px 6px;border-radius:8px;white-space:nowrap;flex-shrink:0}
  .ep-badge.ep-seen{background:#1a3d1a;color:#6f6}
  .ep-badge.ep-resume{background:#3d2a00;color:#fa0}
  .ep-runtime{min-width:36px;text-align:right;font-size:.72rem;color:#555;flex-shrink:0}
  .season-hdr{font-size:.78rem;color:#888;margin-bottom:6px}
  /* Log viewer */
  .log-controls{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:8px}
  .log-controls select,.log-controls input[type=text]{background:#1e1e1e;border:1px solid #444;
    color:#ddd;border-radius:4px;padding:3px 7px;font-size:.82rem}
  .log-output{font-family:'Cascadia Code','Consolas',monospace;font-size:.72rem;height:340px;
    overflow-y:auto;background:#0a0a0a;padding:8px;border-radius:4px;line-height:1.5}
  .log-ln{padding:1px 0;border-bottom:1px solid #111;white-space:pre-wrap;word-break:break-all}
  .log-DEBUG{color:#555}
  .log-INFO{color:#999}
  .log-WARNING{color:#c80}
  .log-ERROR{color:#e44}
  /* Settings card */
  .settings-section{margin-bottom:12px}
  .settings-section:last-child{margin-bottom:0}
  .settings-section-title{font-size:.73rem;color:#888;text-transform:uppercase;
    letter-spacing:.06em;margin-bottom:5px;padding-bottom:3px;border-bottom:1px solid #252525}
  .radio-group{display:flex;gap:14px;flex-wrap:wrap}
  .radio-group label{display:flex;align-items:center;gap:6px;cursor:pointer;font-size:.84rem;
    padding:3px 8px;border-radius:5px;border:1px solid transparent;transition:border-color .12s}
  .radio-group label:hover{border-color:#444}
  .radio-group input[type=radio]{cursor:pointer;accent-color:#4a9;width:14px;height:14px}
  /* Custom seek row */
  .seek-row{display:flex;align-items:center;gap:5px}
  .seek-row input[type=number]{width:58px;background:#1e1e1e;border:1px solid #444;color:#ddd;
    border-radius:4px;padding:3px 6px;font-size:.84rem;text-align:center;-moz-appearance:textfield}
  .seek-row input[type=number]::-webkit-inner-spin-button{-webkit-appearance:none}
  .seek-row .seek-unit{font-size:.75rem;color:#555}
</style>
</head>
<body>
<h1>kodi-mpchc-bridge</h1>
<div id="status"></div>

<div class="grid">

  <!-- Card: Controls + Navigation -->
  <div class="card">
    <h2 data-i18n="card_controls"></h2>
    <img id="artwork" class="artwork" src="" alt="" style="display:none">

    <div class="btns">
      <button onclick="cmd('play_pause')">&#x23EF;</button>
      <button onclick="cmd('stop')">&#x23F9;</button>
      <button onclick="cmd('prev_chapter')">&#x23EE;</button>
      <button onclick="cmd('next_chapter')">&#x23ED;</button>
      <button onclick="cmd('skip_backward')" data-i18n="btn_skip_back"></button>
      <button onclick="cmd('skip_forward')"  data-i18n="btn_skip_fwd"></button>
      <button onclick="cmd('seek_backward_small')" data-i18n="btn_seek_back"></button>
      <button onclick="cmd('seek_forward_small')"  data-i18n="btn_seek_fwd"></button>
    </div>
    <div class="btns">
      <div class="seek-row">
        <button onclick="seekCustom(-1)" data-i18n="btn_seek_minus"></button>
        <input id="seek-secs" type="number" value="30" min="1" max="7200">
        <span class="seek-unit">s</span>
        <button onclick="seekCustom(1)" data-i18n="btn_seek_plus"></button>
      </div>
    </div>
    <div class="btns">
      <button onclick="cmd('volume_down')">&#x1F509;</button>
      <button onclick="cmd('volume_up')">&#x1F50A;</button>
      <button onclick="cmd('mute')">&#x1F507;</button>
    </div>

    <div class="sep"></div>

    <div class="nav-row">
      <div class="dpad">
        <div></div>
        <button onclick="cmd('navigate_up')" data-i18n-title="nav_up">&#x25B2;</button>
        <div></div>
        <button onclick="cmd('navigate_left')" data-i18n-title="nav_left">&#x25C4;</button>
        <button class="ok" onclick="cmd('navigate_select')" data-i18n-title="nav_ok">OK</button>
        <button onclick="cmd('navigate_right')" data-i18n-title="nav_right">&#x25BA;</button>
        <div></div>
        <button onclick="cmd('navigate_down')" data-i18n-title="nav_down">&#x25BC;</button>
        <div></div>
      </div>
      <div>
        <div class="btns" style="flex-direction:column;gap:5px">
          <button onclick="cmd('navigate_back')" data-i18n="btn_back"></button>
          <button onclick="cmd('navigate_home')" data-i18n="btn_home"></button>
          <button onclick="cmd('context_menu')"  data-i18n="btn_menu"></button>
          <button onclick="cmd('show_info')"      data-i18n="btn_info"></button>
          <button id="btn-watched" onclick="cmd('toggle_watched')" data-i18n="btn_watched" style="display:none"></button>
        </div>
      </div>
    </div>
    <div class="kbd-hint" data-i18n-html="kbd_hint"></div>

    <div class="sep"></div>
    <div class="btns">
      <button onclick="cmd('fullscreen')" data-i18n="btn_fullscreen"></button>
      <button onclick="restartConfirm()" data-i18n="btn_restart_pc" style="background:#5c1a1a;border-color:#8a2a2a;color:#f99"></button>
      <button onclick="toggleLogs()" data-i18n="btn_logs" style="background:#1a2a3d;border-color:#2a4a6a;color:#6af"></button>
      <button onclick="toggleSettings()" data-i18n="btn_settings" style="background:#1a2a3d;border-color:#2a4a6a;color:#6af"></button>
    </div>
    <div class="btns" id="kiosk-btns" style="display:none">
      <button id="btn-kiosk-kodi" onclick="kioskCmd('kodi')" data-i18n="btn_kiosk_kodi" style="background:#1a3d1a;border-color:#2a6a2a;color:#9f9"></button>
      <button id="btn-kiosk-windows" onclick="kioskCmd('windows')" data-i18n="btn_kiosk_windows" style="background:#2a2a2a;border-color:#555;color:#ddd"></button>
      <button id="btn-kiosk-restart" onclick="kioskCmd('restart')" data-i18n="btn_kiosk_restart" style="background:#3d2a00;border-color:#7a5500;color:#fc6"></button>
    </div>
  </div>

  <!-- Card: Playback info -->
  <div class="card">
    <h2 data-i18n="card_playback"></h2>
    <table id="tbl-play"></table>
  </div>

  <!-- Card: Video info -->
  <div class="card">
    <h2 data-i18n="card_video"></h2>
    <table id="tbl-video"></table>
  </div>

  <!-- Card: Tracks -->
  <div class="card">
    <h2 data-i18n="card_tracks"></h2>
    <table id="tbl-tracks"></table>
  </div>

  <!-- Card: Season episodes (full width, hidden when no episode is playing) -->
  <div class="card" id="card-season" style="grid-column:1/-1;display:none">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
      <h2 id="season-hdr" style="margin:0"></h2>
      <div style="display:flex;gap:5px">
        <button id="btn-prev-ep" onclick="prevEpisode()" data-i18n="btn_prev_ep" disabled></button>
        <button id="btn-next-ep" onclick="nextEpisode()" data-i18n="btn_next_ep" disabled></button>
      </div>
    </div>
    <div id="ep-list" class="ep-list"></div>
  </div>

  <!-- Card: Log viewer (full width, hidden by default) -->
  <div class="card" id="card-logs" style="grid-column:1/-1;display:none">
    <h2 data-i18n="card_logs"></h2>
    <div class="log-controls">
      <select id="log-level">
        <option value="">ALL</option>
        <option value="DEBUG">DEBUG</option>
        <option value="INFO">INFO</option>
        <option value="WARNING">WARNING</option>
        <option value="ERROR">ERROR</option>
      </select>
      <input id="log-search" type="text" placeholder="Filter\u2026" style="flex:1;min-width:100px">
      <select id="log-count">
        <option value="50" selected>50</option>
        <option value="100">100</option>
        <option value="200">200</option>
        <option value="500">500</option>
      </select>
      <label style="display:flex;align-items:center;gap:4px;font-size:.82rem;cursor:pointer;white-space:nowrap">
        <input type="checkbox" id="log-auto"> Auto
      </label>
      <button onclick="fetchLogs()" data-i18n="btn_log_refresh"></button>
    </div>
    <div id="log-output" class="log-output"></div>
  </div>

  <!-- Card: Settings (full width, hidden by default) -->
  <div class="card" id="card-settings" style="grid-column:1/-1;display:none">
    <h2 data-i18n="card_settings"></h2>

    <!-- Film -->
    <div class="settings-section">
      <div class="settings-section-title" data-i18n="lbl_art_movie"></div>
      <div class="radio-group">
        <label><input type="radio" name="art_movie" value="poster"
          onchange="saveArtMode('movie_art_mode',this)"><span data-i18n="opt_art_poster"></span></label>
        <label><input type="radio" name="art_movie" value="fanart"
          onchange="saveArtMode('movie_art_mode',this)"><span data-i18n="opt_art_fanart"></span></label>
        <label><input type="radio" name="art_movie" value="thumb"
          onchange="saveArtMode('movie_art_mode',this)"><span data-i18n="opt_art_thumb"></span></label>
      </div>
    </div>

    <!-- Serien -->
    <div class="settings-section">
      <div class="settings-section-title" data-i18n="lbl_art_episode"></div>
      <div class="radio-group">
        <label><input type="radio" name="art_episode" value="poster"
          onchange="saveArtMode('episode_art_mode',this)"><span data-i18n="opt_art_tvposter"></span></label>
        <label><input type="radio" name="art_episode" value="season.poster"
          onchange="saveArtMode('episode_art_mode',this)"><span data-i18n="opt_art_seasonposter"></span></label>
        <label><input type="radio" name="art_episode" value="thumb"
          onchange="saveArtMode('episode_art_mode',this)"><span data-i18n="opt_art_thumb"></span></label>
        <label><input type="radio" name="art_episode" value="fanart"
          onchange="saveArtMode('episode_art_mode',this)"><span data-i18n="opt_art_fanart"></span></label>
      </div>
    </div>

    <!-- Musik -->
    <div class="settings-section">
      <div class="settings-section-title" data-i18n="lbl_art_music"></div>
      <div class="radio-group">
        <label><input type="radio" name="art_music" value="thumb"
          onchange="saveArtMode('music_art_mode',this)"><span data-i18n="opt_art_thumb"></span></label>
        <label><input type="radio" name="art_music" value="fanart"
          onchange="saveArtMode('music_art_mode',this)"><span data-i18n="opt_art_fanart"></span></label>
      </div>
    </div>

    <!-- Kiosk / Boot-Ziel -->
    <div class="settings-section">
      <div class="settings-section-title" data-i18n="lbl_boot_target"></div>
      <div class="radio-group" style="margin-bottom:10px">
        <label><input type="radio" name="boot_target" value="kodi"
          onchange="saveBootTarget(this)"><span data-i18n="opt_boot_kodi"></span></label>
        <label><input type="radio" name="boot_target" value="windows"
          onchange="saveBootTarget(this)"><span data-i18n="opt_boot_windows"></span></label>
      </div>
      <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
        <label style="font-size:.84rem;white-space:nowrap" data-i18n="lbl_kodi_exe"></label>
        <input type="text" id="inp_kodi_exe"
          style="flex:1;min-width:180px;background:#1a1a1a;border:1px solid #333;
                 color:#e0e0e0;padding:3px 6px;border-radius:4px;font-size:.82rem"
          onchange="saveKioskSetting('kodi_exe_path',this.value)">
      </div>
    </div>
  </div>

</div>

<script>
// ── i18n ──────────────────────────────────────────────────────────────────────
const _LANG = (navigator.language || 'en').slice(0,2).toLowerCase();
const _TR = {
  en:{
    status_connecting:'Connecting\u2026',
    status_connected:'\u25CF Connected',
    status_reconnecting:'\u25CB Disconnected \u2013 reconnecting\u2026',
    card_controls:'Controls',
    card_playback:'Playback',
    card_video:'Video Info',
    card_tracks:'Tracks',
    btn_skip_back:'\u23EA \u22121\u202Fmin',
    btn_skip_fwd:'+1\u202Fmin \u23E9',
    btn_seek_back:'\u221210s',
    btn_seek_fwd:'+10s',
    btn_back:'\u2190 Back',
    btn_home:'\u2302 Home',
    btn_menu:'\u2630 Menu',
    btn_info:'\u2139 Info',
    btn_watched:'\u2606 Unwatched',
    btn_watched_on:'\u2605 Watched',
    nav_up:'Up (\u2191)', nav_down:'Down (\u2193)',
    nav_left:'Left (\u2190)', nav_right:'Right (\u2192)', nav_ok:'OK (Enter)',
    kbd_hint:'Keyboard: <kbd>\u2191\u2193\u2190\u2192</kbd> navigate &nbsp;<kbd>Enter</kbd> OK &nbsp;<kbd>Esc</kbd> Back &nbsp;<kbd>Space</kbd> Play/Pause',
    lbl_active_player:'Player', lbl_state:'State', lbl_title:'Title',
    lbl_artist:'Artist', lbl_album:'Album', lbl_media_type:'Type',
    lbl_position:'Position', lbl_duration:'Duration', lbl_volume:'Volume',
    lbl_muted:'Muted', lbl_shuffle:'Shuffle', lbl_repeat:'Repeat',
    lbl_year:'Year', lbl_tv_show:'Show', lbl_season:'Season', lbl_episode:'Episode',
    lbl_video_width:'Width', lbl_video_height:'Height', lbl_video_fps:'Frame rate',
    lbl_hdr:'HDR', lbl_video_codec:'Codec', lbl_video_bitrate_kbps:'Bitrate',
    lbl_current_audio:'Audio', lbl_current_subtitle:'Subtitle', lbl_current_chapter:'Chapter',
    val_yes:'Yes', val_no:'No', val_of:'of',
    btn_fullscreen:'\u26F6 Fullscreen',
    btn_restart_pc:'\u23FB Restart PC',
    confirm_restart:'Schedule a system restart in 10 seconds?',
    card_season:'Season',
    lbl_ep_resume:'Resume',
    lbl_no_episodes:'No episode data available.',
    btn_prev_ep:'\u23EE Prev',
    btn_next_ep:'Next \u23ED',
    btn_logs:'\U0001F4CB Log',
    card_logs:'Bridge Log',
    btn_log_refresh:'\u21BB',
    btn_seek_minus:'\u23EA s',
    btn_seek_plus:'s \u23E9',
    btn_settings:'\u2699 Settings',
    card_settings:'Settings',
    lbl_art_movie:'Movie',
    lbl_art_episode:'TV Series',
    lbl_art_music:'Music',
    opt_art_poster:'Poster',
    opt_art_fanart:'Fanart\u202F/\u202FBackdrop',
    opt_art_thumb:'Thumbnail',
    opt_art_tvposter:'Series poster',
    opt_art_seasonposter:'Season poster',
    lbl_kiosk:'Kiosk',
    opt_hide_explorer:'Hide Explorer on startup (kiosk mode)',
    lbl_kodi_exe:'Kodi path:',
    btn_kiosk_kodi:'Kodi',
    btn_kiosk_windows:'Windows',
    btn_kiosk_restart:'Restart Kodi',
    lbl_boot_target:'Boot target',
    opt_boot_kodi:'Kodi \u2014 hide Explorer on startup',
    opt_boot_windows:'Windows \u2014 normal desktop',
  },
  de:{
    status_connecting:'Verbinde\u2026',
    status_connected:'\u25CF Verbunden',
    status_reconnecting:'\u25CB Getrennt \u2013 verbinde erneut\u2026',
    card_controls:'Steuerung',
    card_playback:'Wiedergabe',
    card_video:'Video-Info',
    card_tracks:'Spuren',
    btn_skip_back:'\u23EA \u22121\u202Fmin',
    btn_skip_fwd:'+1\u202Fmin \u23E9',
    btn_seek_back:'\u221210s',
    btn_seek_fwd:'+10s',
    btn_back:'\u2190 Zur\u00FCck',
    btn_home:'\u2302 Home',
    btn_menu:'\u2630 Men\u00FC',
    btn_info:'\u2139 Info',
    btn_watched:'\u2606 Ungesehen',
    btn_watched_on:'\u2605 Gesehen',
    nav_up:'Hoch (\u2191)', nav_down:'Runter (\u2193)',
    nav_left:'Links (\u2190)', nav_right:'Rechts (\u2192)', nav_ok:'OK (Enter)',
    kbd_hint:'Tastatur: <kbd>\u2191\u2193\u2190\u2192</kbd> navigieren &nbsp;<kbd>Enter</kbd> OK &nbsp;<kbd>Esc</kbd> Zur\u00FCck &nbsp;<kbd>Leertaste</kbd> Play/Pause',
    lbl_active_player:'Player', lbl_state:'Status', lbl_title:'Titel',
    lbl_artist:'Interpret', lbl_album:'Album', lbl_media_type:'Typ',
    lbl_position:'Position', lbl_duration:'Dauer', lbl_volume:'Lautst\u00E4rke',
    lbl_muted:'Stumm', lbl_shuffle:'Shuffle', lbl_repeat:'Wiederholen',
    lbl_year:'Jahr', lbl_tv_show:'Serie', lbl_season:'Staffel', lbl_episode:'Folge',
    lbl_video_width:'Breite', lbl_video_height:'H\u00F6he', lbl_video_fps:'Framerate',
    lbl_hdr:'HDR', lbl_video_codec:'Codec', lbl_video_bitrate_kbps:'Bitrate',
    lbl_current_audio:'Audio-Spur', lbl_current_subtitle:'Untertitel', lbl_current_chapter:'Kapitel',
    val_yes:'Ja', val_no:'Nein', val_of:'von',
    btn_fullscreen:'\u26F6 Vollbild',
    btn_restart_pc:'\u23FB PC neu starten',
    confirm_restart:'PC in 10 Sekunden neu starten?',
    card_season:'Staffel',
    lbl_ep_resume:'Fortsetzen',
    lbl_no_episodes:'Keine Episodendaten verf\u00fcgbar.',
    btn_prev_ep:'\u23EE Zurück',
    btn_next_ep:'Weiter \u23ED',
    btn_logs:'\U0001F4CB Log',
    card_logs:'Bridge Log',
    btn_log_refresh:'\u21BB',
    btn_seek_minus:'\u23EA s',
    btn_seek_plus:'s \u23E9',
    btn_settings:'\u2699 Einstellungen',
    card_settings:'Einstellungen',
    lbl_art_movie:'Film',
    lbl_art_episode:'Serien',
    lbl_art_music:'Musik',
    opt_art_poster:'Poster',
    opt_art_fanart:'Fanart\u202F/\u202FHintergrund',
    opt_art_thumb:'Thumbnail',
    opt_art_tvposter:'Seriencover',
    opt_art_seasonposter:'Staffelcover',
    lbl_kiosk:'Kiosk',
    opt_hide_explorer:'Explorer beim Start verstecken (Kiosk-Modus)',
    lbl_kodi_exe:'Kodi-Pfad:',
    btn_kiosk_kodi:'Kodi',
    btn_kiosk_windows:'Windows',
    btn_kiosk_restart:'Kodi neustarten',
    lbl_boot_target:'Boot-Ziel',
    opt_boot_kodi:'Kodi \u2014 Explorer beim Start verstecken',
    opt_boot_windows:'Windows \u2014 normaler Desktop',
  },
  fr:{
    status_connecting:'Connexion\u2026',
    status_connected:'\u25CF Connect\u00E9',
    status_reconnecting:'\u25CB D\u00E9connect\u00E9 \u2013 reconnexion\u2026',
    card_controls:'Contr\u00F4les',
    card_playback:'Lecture',
    card_video:'Infos vid\u00E9o',
    card_tracks:'Pistes',
    btn_skip_back:'\u23EA \u22121\u202Fmin',
    btn_skip_fwd:'+1\u202Fmin \u23E9',
    btn_seek_back:'\u221210s',
    btn_seek_fwd:'+10s',
    btn_back:'\u2190 Retour',
    btn_home:'\u2302 Accueil',
    btn_menu:'\u2630 Menu',
    btn_info:'\u2139 Infos',
    btn_watched:'\u2606 Non vu',
    btn_watched_on:'\u2605 Vu',
    nav_up:'Haut (\u2191)', nav_down:'Bas (\u2193)',
    nav_left:'Gauche (\u2190)', nav_right:'Droite (\u2192)', nav_ok:'OK (Entr\u00E9e)',
    kbd_hint:'Clavier\u00A0: <kbd>\u2191\u2193\u2190\u2192</kbd> naviguer &nbsp;<kbd>Entr\u00E9e</kbd> OK &nbsp;<kbd>\u00C9chap</kbd> Retour &nbsp;<kbd>Espace</kbd> Lecture/Pause',
    lbl_active_player:'Lecteur', lbl_state:'\u00C9tat', lbl_title:'Titre',
    lbl_artist:'Artiste', lbl_album:'Album', lbl_media_type:'Type',
    lbl_position:'Position', lbl_duration:'Dur\u00E9e', lbl_volume:'Volume',
    lbl_muted:'Muet', lbl_shuffle:'Al\u00E9atoire', lbl_repeat:'R\u00E9p\u00E9ter',
    lbl_year:'Ann\u00E9e', lbl_tv_show:'S\u00E9rie', lbl_season:'Saison', lbl_episode:'\u00C9pisode',
    lbl_video_width:'Largeur', lbl_video_height:'Hauteur', lbl_video_fps:'Fr\u00E9quence',
    lbl_hdr:'HDR', lbl_video_codec:'Codec', lbl_video_bitrate_kbps:'D\u00E9bit',
    lbl_current_audio:'Audio', lbl_current_subtitle:'Sous-titres', lbl_current_chapter:'Chapitre',
    val_yes:'Oui', val_no:'Non', val_of:'sur',
    btn_fullscreen:'\u26F6 Plein \u00E9cran',
    btn_restart_pc:'\u23FB Red\u00E9marrer le PC',
    confirm_restart:'Planifier un red\u00E9marrage du syst\u00E8me dans 10 secondes\u00A0?',
    lbl_kiosk:'Kiosque',
    opt_hide_explorer:'Masquer l\u2019Explorateur au d\u00E9marrage (mode kiosque)',
    lbl_kodi_exe:'Chemin Kodi\u00A0:',
    lbl_boot_target:'Cible de d\u00E9marrage',
    opt_boot_kodi:'Kodi \u2014 masquer l\u2019Explorateur au d\u00E9marrage',
    opt_boot_windows:'Windows \u2014 bureau normal',
  },
  es:{
    status_connecting:'Conectando\u2026',
    status_connected:'\u25CF Conectado',
    status_reconnecting:'\u25CB Desconectado \u2013 reconectando\u2026',
    card_controls:'Controles',
    card_playback:'Reproducci\u00F3n',
    card_video:'Info de v\u00EDdeo',
    card_tracks:'Pistas',
    btn_skip_back:'\u23EA \u22121\u202Fmin',
    btn_skip_fwd:'+1\u202Fmin \u23E9',
    btn_seek_back:'\u221210s',
    btn_seek_fwd:'+10s',
    btn_back:'\u2190 Volver',
    btn_home:'\u2302 Inicio',
    btn_menu:'\u2630 Men\u00FA',
    btn_info:'\u2139 Info',
    btn_watched:'\u2606 No visto',
    btn_watched_on:'\u2605 Visto',
    nav_up:'Arriba (\u2191)', nav_down:'Abajo (\u2193)',
    nav_left:'Izquierda (\u2190)', nav_right:'Derecha (\u2192)', nav_ok:'OK (Intro)',
    kbd_hint:'Teclado: <kbd>\u2191\u2193\u2190\u2192</kbd> navegar &nbsp;<kbd>Intro</kbd> OK &nbsp;<kbd>Esc</kbd> Volver &nbsp;<kbd>Espacio</kbd> Play/Pausa',
    lbl_active_player:'Reproductor', lbl_state:'Estado', lbl_title:'T\u00EDtulo',
    lbl_artist:'Artista', lbl_album:'\u00C1lbum', lbl_media_type:'Tipo',
    lbl_position:'Posici\u00F3n', lbl_duration:'Duraci\u00F3n', lbl_volume:'Volumen',
    lbl_muted:'Silencio', lbl_shuffle:'Aleatorio', lbl_repeat:'Repetir',
    lbl_year:'A\u00F1o', lbl_tv_show:'Serie', lbl_season:'Temporada', lbl_episode:'Episodio',
    lbl_video_width:'Ancho', lbl_video_height:'Alto', lbl_video_fps:'Fotogramas',
    lbl_hdr:'HDR', lbl_video_codec:'C\u00F3dec', lbl_video_bitrate_kbps:'Tasa de bits',
    lbl_current_audio:'Audio', lbl_current_subtitle:'Subt\u00EDtulos', lbl_current_chapter:'Cap\u00EDtulo',
    val_yes:'S\u00ED', val_no:'No', val_of:'de',
    btn_fullscreen:'\u26F6 Pantalla completa',
    btn_restart_pc:'\u23FB Reiniciar PC',
    confirm_restart:'\u00BFProgramar un reinicio del sistema en 10 segundos?',
    lbl_kiosk:'Quiosco',
    opt_hide_explorer:'Ocultar el Explorador al inicio (modo quiosco)',
    lbl_kodi_exe:'Ruta de Kodi:',
    lbl_boot_target:'Destino de arranque',
    opt_boot_kodi:'Kodi \u2014 ocultar Explorador al inicio',
    opt_boot_windows:'Windows \u2014 escritorio normal',
  },
  it:{
    status_connecting:'Connessione\u2026',
    status_connected:'\u25CF Connesso',
    status_reconnecting:'\u25CB Disconnesso \u2013 riconnessione\u2026',
    card_controls:'Controlli',
    card_playback:'Riproduzione',
    card_video:'Info video',
    card_tracks:'Tracce',
    btn_skip_back:'\u23EA \u22121\u202Fmin',
    btn_skip_fwd:'+1\u202Fmin \u23E9',
    btn_seek_back:'\u221210s',
    btn_seek_fwd:'+10s',
    btn_back:'\u2190 Indietro',
    btn_home:'\u2302 Home',
    btn_menu:'\u2630 Menu',
    btn_info:'\u2139 Info',
    btn_watched:'\u2606 Non visto',
    btn_watched_on:'\u2605 Visto',
    nav_up:'Su (\u2191)', nav_down:'Gi\u00F9 (\u2193)',
    nav_left:'Sinistra (\u2190)', nav_right:'Destra (\u2192)', nav_ok:'OK (Invio)',
    kbd_hint:'Tastiera: <kbd>\u2191\u2193\u2190\u2192</kbd> navigare &nbsp;<kbd>Invio</kbd> OK &nbsp;<kbd>Esc</kbd> Indietro &nbsp;<kbd>Spazio</kbd> Play/Pausa',
    lbl_active_player:'Lettore', lbl_state:'Stato', lbl_title:'Titolo',
    lbl_artist:'Artista', lbl_album:'Album', lbl_media_type:'Tipo',
    lbl_position:'Posizione', lbl_duration:'Durata', lbl_volume:'Volume',
    lbl_muted:'Muto', lbl_shuffle:'Casuale', lbl_repeat:'Ripeti',
    lbl_year:'Anno', lbl_tv_show:'Serie', lbl_season:'Stagione', lbl_episode:'Episodio',
    lbl_video_width:'Larghezza', lbl_video_height:'Altezza', lbl_video_fps:'Fotogrammi',
    lbl_hdr:'HDR', lbl_video_codec:'Codec', lbl_video_bitrate_kbps:'Bitrate',
    lbl_current_audio:'Audio', lbl_current_subtitle:'Sottotitoli', lbl_current_chapter:'Capitolo',
    val_yes:'S\u00EC', val_no:'No', val_of:'di',
    btn_fullscreen:'\u26F6 Schermo intero',
    btn_restart_pc:'\u23FB Riavvia PC',
    confirm_restart:'Pianificare il riavvio del sistema tra 10 secondi?',
    lbl_kiosk:'Chiosco',
    opt_hide_explorer:'Nascondi Explorer all\u2019avvio (modalit\u00E0 chiosco)',
    lbl_kodi_exe:'Percorso Kodi:',
    lbl_boot_target:'Destinazione avvio',
    opt_boot_kodi:'Kodi \u2014 nascondi Explorer all\u2019avvio',
    opt_boot_windows:'Windows \u2014 desktop normale',
  },
};
const _T = _TR[_LANG] || _TR.en;
function t(k){ return _T[k] || (_TR.en[k]) || k; }

// Apply static translations to the DOM
(function applyI18n(){
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll('[data-i18n-html]').forEach(el => {
    el.innerHTML = t(el.dataset.i18nHtml);
  });
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    el.title = t(el.dataset.i18nTitle);
  });
  document.getElementById('status').textContent = t('status_connecting');
})();

// ── State & rendering ─────────────────────────────────────────────────────────
const PLAY_KEYS  = ['active_player','state','title','year','media_type',
                    'tv_show','season','episode',
                    'artist','album','position','duration','volume','muted',
                    'shuffle','repeat'];
const VIDEO_KEYS = ['video_width','video_height','video_fps','hdr',
                    'video_codec','video_bitrate_kbps'];
const TRACK_KEYS = ['current_audio','current_subtitle','current_chapter'];

let state = {};

function fmt(k, v) {
  if (v === null || v === undefined) return '\u2014';
  if (k === 'position' || k === 'duration') {
    const s = Math.round(v);
    return new Date(s * 1000).toISOString().substr(11, 8);
  }
  if (k === 'volume') return v + '\u202F%';
  if (k === 'video_fps') return v ? v.toFixed(3) + '\u202Ffps' : '\u2014';
  if (k === 'video_bitrate_kbps') return v ? (v / 1000).toFixed(1) + '\u202FMbps' : '\u2014';
  if (k === 'video_width' || k === 'video_height') return v ? v + '\u202Fpx' : '\u2014';
  if (k === 'year') return v ? String(v) : '\u2014';
  if (k === 'season') {
    if (!v) return '\u2014';
    return state.season_count > 0 ? `${v}\u202F${t('val_of')}\u202F${state.season_count}` : String(v);
  }
  if (k === 'episode') {
    if (!v) return '\u2014';
    return state.episode_count > 0 ? `${v}\u202F${t('val_of')}\u202F${state.episode_count}` : String(v);
  }
  if (typeof v === 'boolean') return v ? t('val_yes') : t('val_no');
  if (Array.isArray(v)) return v.length ? v.map(x => x.label || x.name || '?').join(', ') : '\u2014';
  return v ? String(v) : '\u2014';
}

function label(k) {
  return t('lbl_' + k) || k;
}

function renderTable(id, keys) {
  const rows = keys.map(k => {
    let v = fmt(k, state[k]);
    if (k === 'active_player') {
      const cls = state[k] || 'none';
      v = `<span class="player-badge ${cls}">${state[k] || 'none'}</span>`;
    }
    if ((k === 'tv_show' || k === 'season' || k === 'episode') &&
        state.media_type !== 'episode' && !state.tv_show) return '';
    if ((k === 'artist' || k === 'album') && state.media_type !== 'music' &&
        !state.artist && !state.album) return '';
    return `<tr><td>${label(k)}</td><td>${v}</td></tr>`;
  }).join('');
  document.getElementById(id).innerHTML = rows;
}

function updateWatchedBtn() {
  const btn = document.getElementById('btn-watched');
  if (!btn) return;
  const hasItem = state.media_id > 0 && (state.media_type === 'movie' || state.media_type === 'episode');
  btn.style.display = hasItem ? '' : 'none';
  if (hasItem) {
    btn.textContent = state.playcount > 0 ? t('btn_watched_on') : t('btn_watched');
  }
}

function renderAll() {
  renderTable('tbl-play',  PLAY_KEYS);
  renderTable('tbl-video', VIDEO_KEYS);

  const trackRows = TRACK_KEYS.map(k => {
    let display = fmt(k, state[k]);
    const listKey = k.replace('current_audio','audio_tracks')
                     .replace('current_subtitle','subtitle_tracks')
                     .replace('current_chapter','chapters');
    const arr = state[listKey] || [];
    if (arr.length) {
      const item = arr[state[k]];
      if (item) display = item.label || item.name || display;
    }
    return `<tr><td>${label(k)}</td><td>${display}</td></tr>`;
  }).join('');
  document.getElementById('tbl-tracks').innerHTML = trackRows;

  const artEl = document.getElementById('artwork');
  if (state.artwork_url) {
    artEl.src = state.artwork_url + '?t=' + Date.now();
    artEl.style.display = 'block';
  } else {
    artEl.style.display = 'none';
    artEl.src = '';
  }

  renderSeasonEpisodes();
  updateWatchedBtn();
}

function cmd(c, val) {
  const body = {cmd: c};
  if (val !== undefined) body.value = val;
  fetch('/api/command', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  }).catch(() => {});
}

function restartConfirm() {
  if (confirm(t('confirm_restart'))) { cmd('system_restart'); }
}

function kioskCmd(mode) {
  fetch('/api/kiosk/' + mode, {method:'POST'}).catch(()=>{});
  setTimeout(updateKioskStatus, 4000);
}

let _kioskStatusTimer = null;
async function updateKioskStatus() {
  try {
    const s = await fetch('/api/kiosk/status').then(r => r.json());
    const btns = document.getElementById('kiosk-btns');
    if (btns) btns.style.display = '';
    const bKodi    = document.getElementById('btn-kiosk-kodi');
    const bWin     = document.getElementById('btn-kiosk-windows');
    if (bKodi) bKodi.style.background    = s.kodi_running && s.explorer_hidden ? '#1a5c2a' : '#1a3d1a';
    if (bWin)  bWin.style.background     = !s.explorer_hidden ? '#3a3a3a' : '#2a2a2a';
  } catch(e) {}
}
// Poll kiosk status every 5 s to keep button highlight in sync
_kioskStatusTimer = setInterval(updateKioskStatus, 5000);
updateKioskStatus();

document.addEventListener('keydown', function(e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  if (e.key === '[') { e.preventDefault(); seekCustom(-1); return; }
  if (e.key === ']') { e.preventDefault(); seekCustom(1);  return; }
  const map = {
    ArrowUp:'navigate_up', ArrowDown:'navigate_down',
    ArrowLeft:'navigate_left', ArrowRight:'navigate_right',
    Enter:'navigate_select', Escape:'navigate_back',
    Backspace:'navigate_back', ' ':'play_pause',
  };
  if (map[e.key]) { e.preventDefault(); cmd(map[e.key]); }
});

// ── Log viewer ────────────────────────────────────────────────────────────────
let _logAutoTimer = null;

function toggleLogs() {
  const card = document.getElementById('card-logs');
  if (!card) return;
  const visible = card.style.display !== 'none';
  card.style.display = visible ? 'none' : '';
  if (!visible) fetchLogs();
}

// ── Settings card ─────────────────────────────────────────────────────────────
function toggleSettings() {
  const card = document.getElementById('card-settings');
  if (!card) return;
  const visible = card.style.display !== 'none';
  card.style.display = visible ? 'none' : '';
  if (!visible) loadSettings();
}

async function loadSettings() {
  try {
    const cfg = await fetch('/api/config').then(r => r.json());
    syncSettingsUI(cfg);
  } catch(e) {}
}

function syncSettingsUI(cfg) {
  if (!cfg) return;
  var modeMap = {
    art_movie:   cfg.movie_art_mode   || 'poster',
    art_episode: cfg.episode_art_mode || 'poster',
    art_music:   cfg.music_art_mode   || 'thumb',
  };
  Object.keys(modeMap).forEach(function(name) {
    document.querySelectorAll('input[name="' + name + '"]').forEach(function(r) {
      r.checked = r.value === modeMap[name];
    });
  });
  // Boot target
  var bootVal = cfg.hide_explorer ? 'kodi' : 'windows';
  document.querySelectorAll('input[name="boot_target"]').forEach(function(r) {
    r.checked = r.value === bootVal;
  });
  var inpKodi = document.getElementById('inp_kodi_exe');
  if (inpKodi) inpKodi.value = cfg.kodi_exe_path || '';
}

function saveBootTarget(radio) {
  saveKioskSetting('hide_explorer', radio.value === 'kodi');
}

function saveKioskSetting(key, val) {
  var body = {};
  body[key] = val;
  fetch('/api/config', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  }).catch(function() {});
}

function saveArtMode(configKey, radio) {
  var body = {};
  body[configKey] = radio.value;
  fetch('/api/config', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  }).catch(function() {});
}

// ── Custom seek ───────────────────────────────────────────────────────────────
function seekCustom(sign) {
  var secs = parseFloat((document.getElementById('seek-secs') || {}).value || '30');
  if (!isNaN(secs) && secs > 0) {
    cmd('seek_relative', sign * secs);
  }
}

async function fetchLogs() {
  const level  = (document.getElementById('log-level')  || {}).value || '';
  const search = (document.getElementById('log-search') || {}).value || '';
  const count  = (document.getElementById('log-count')  || {}).value || '50';
  let url = '/api/logs?limit=' + encodeURIComponent(count);
  if (level)  url += '&level='  + encodeURIComponent(level);
  if (search) url += '&search=' + encodeURIComponent(search);
  try {
    const d = await fetch(url).then(r => r.json());
    const out = document.getElementById('log-output');
    if (!out) return;
    const recs = d.records || [];
    out.innerHTML = recs.map(function(r) {
      const txt = r.msg
        .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      return '<div class="log-ln log-' + r.level + '">' + txt + '</div>';
    }).join('');
    out.scrollTop = out.scrollHeight;
  } catch(e) {}
}

(function _setupLogListeners() {
  // Auto-refresh toggle
  document.addEventListener('DOMContentLoaded', function() {}, false);
  var autoChk = document.getElementById('log-auto');
  if (autoChk) {
    autoChk.addEventListener('change', function() {
      clearInterval(_logAutoTimer);
      if (this.checked) { _logAutoTimer = setInterval(fetchLogs, 2000); fetchLogs(); }
    });
  }
  // Re-fetch on Enter in search box
  var srch = document.getElementById('log-search');
  if (srch) { srch.addEventListener('keydown', function(e){ if(e.key==='Enter') fetchLogs(); }); }
}());

// ── Episode navigation ────────────────────────────────────────────────────────
function prevEpisode() {
  const eps = state.season_episodes;
  const idx = state.playlist_index != null ? state.playlist_index : -1;
  if (!eps || idx <= 0) return;
  playEpisode(eps[idx - 1].file);
}

function nextEpisode() {
  const eps = state.season_episodes;
  const idx = state.playlist_index != null ? state.playlist_index : -1;
  if (!eps || idx < 0 || idx >= eps.length - 1) return;
  playEpisode(eps[idx + 1].file);
}

// ── Season episode list ───────────────────────────────────────────────────────
function fmtRuntime(secs) {
  if (!secs) return '';
  const m = Math.round(secs / 60);
  return m + '\u202Fmin';
}

function fmtResumeTime(secs) {
  if (!secs) return '';
  const s = Math.round(secs);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  return h > 0
    ? h + ':' + String(m).padStart(2,'0') + ':' + String(ss).padStart(2,'0')
    : m + ':' + String(ss).padStart(2,'0');
}

let _epScrolledIdx = -2; // sentinel: force first scroll
let _epRenderedLen = -1;
let _epRenderedIdx = -2;

function renderSeasonEpisodes() {
  const card = document.getElementById('card-season');
  const hdr  = document.getElementById('season-hdr');
  const list = document.getElementById('ep-list');
  if (!card || !hdr || !list) return;

  const eps = state.season_episodes;
  if (!eps || !eps.length) {
    card.style.display = 'none';
    _epRenderedLen = -1; _epRenderedIdx = -2;
    return;
  }
  card.style.display = '';

  // Header: "Staffel 2  ·  The Office  (12 Folgen)"
  const season = (eps[0] && eps[0].season) ? eps[0].season : (state.season || '');
  const show   = state.tv_show || '';
  hdr.textContent =
    t('card_season') + (season ? ' ' + season : '') +
    (show ? '  \u00B7  ' + show : '') +
    '  (' + eps.length + ')';

  const idx = state.playlist_index != null ? state.playlist_index : -1;

  // Skip full DOM rebuild when list length and current index haven't changed
  const needRebuild = eps.length !== _epRenderedLen || idx !== _epRenderedIdx;
  if (!needRebuild) {
    const prevBtn = document.getElementById('btn-prev-ep');
    const nextBtn = document.getElementById('btn-next-ep');
    if (prevBtn) prevBtn.disabled = idx <= 0;
    if (nextBtn) nextBtn.disabled = idx < 0 || idx >= eps.length - 1;
    return;
  }
  _epRenderedLen = eps.length;
  _epRenderedIdx = idx;

  // Build rows — file path stored in data-epfile attribute (no JS quoting needed)
  list.innerHTML = eps.map((ep, i) => {
    const isCur     = i === idx;
    const isWatched = ep.playcount > 0 && !isCur;
    const hasResume = ep.resume_pos > 10 && !isWatched;

    let cls = 'ep-row';
    if (isCur)     cls += ' ep-current';
    if (isWatched) cls += ' ep-watched';

    // Encode file path as a safe HTML attribute value
    const fileAttr = (ep.file || '')
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;');

    const numStr  = 'E' + String(ep.episode).padStart(2, '0');
    const title   = (ep.title || ('Episode ' + ep.episode))
                      .replace(/&/g,'&amp;').replace(/</g,'&lt;');
    const runtime = fmtRuntime(ep.runtime);

    let badges = '';
    if (isCur) {
      badges += '<span class="ep-badge ep-seen">&#x25B6;</span>';
    } else if (isWatched) {
      badges += '<span class="ep-badge ep-seen">&#x2713;</span>';
    }
    if (hasResume) {
      badges += '<span class="ep-badge ep-resume">&#x23F5; ' + fmtResumeTime(ep.resume_pos) + '</span>';
    }

    return (
      '<div class="' + cls + '" data-epfile="' + fileAttr + '">' +
        '<span class="ep-num">'     + numStr  + '</span>' +
        '<span class="ep-title">'   + title   + '</span>' +
        badges +
        '<span class="ep-runtime">' + runtime + '</span>' +
      '</div>'
    );
  }).join('');

  // Event delegation — one handler on the container, reads data-epfile
  list.onclick = function(e) {
    const row = e.target.closest('.ep-row');
    if (row && row.dataset.epfile) playEpisode(row.dataset.epfile);
  };

  // Enable / disable prev/next navigation buttons
  const prevBtn = document.getElementById('btn-prev-ep');
  const nextBtn = document.getElementById('btn-next-ep');
  if (prevBtn) prevBtn.disabled = idx <= 0;
  if (nextBtn) nextBtn.disabled = idx < 0 || idx >= eps.length - 1;

  // Scroll current episode into view — only when index actually changes
  if (idx >= 0 && idx !== _epScrolledIdx) {
    _epScrolledIdx = idx;
    const rows = list.querySelectorAll('.ep-row');
    if (rows[idx]) rows[idx].scrollIntoView({block: 'nearest'});
  } else if (idx < 0) {
    _epScrolledIdx = -2;
  }
}

function playEpisode(filepath) {
  fetch('/api/external_play', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({filepath: filepath}),
  }).catch(function() {});
}

function connect() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${proto}://${location.host}/api/ws`);
  const el = document.getElementById('status');

  ws.onopen  = () => { el.textContent = t('status_connected');     el.className = 'ok';  };
  ws.onclose = () => {
    el.textContent = t('status_reconnecting'); el.className = 'err';
    setTimeout(connect, 3000);
  };
  ws.onerror = () => { el.className = 'err'; };
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if      (msg.type === 'state_full')  { state = msg.data; }
    else if (msg.type === 'state_patch') { Object.assign(state, msg.data); }
    renderAll();
  };
}

connect();
</script>
</body>
</html>
"""
