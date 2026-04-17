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
    ) -> None:
        self._state = state_manager
        self._router = router
        self._config = config_manager
        self._host = host
        self._port = port
        self._ws_clients: set[web.WebSocketResponse] = set()
        self._app = web.Application()
        self._runner: web.AppRunner | None = None
        self._setup_routes()

    def _setup_routes(self) -> None:
        self._app.router.add_get("/api/state", self._handle_state)
        self._app.router.add_post("/api/command", self._handle_command)
        self._app.router.add_get("/api/config", self._handle_config_get)
        self._app.router.add_post("/api/config", self._handle_config_post)
        self._app.router.add_get("/api/ws", self._handle_ws)
        self._app.router.add_get("/api/artwork", self._handle_artwork)
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
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>kodi-mpchc-bridge</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:system-ui,sans-serif;background:#111;color:#ddd;padding:16px}
  h1{color:#fff;font-size:1.2rem;margin-bottom:12px}
  #status{display:inline-block;padding:3px 10px;border-radius:12px;font-size:.8rem;
          background:#333;margin-bottom:16px}
  #status.ok{background:#1a5c2a;color:#6f6}
  #status.err{background:#5c1a1a;color:#f66}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
  @media(max-width:600px){.grid{grid-template-columns:1fr}}
  .card{background:#1c1c1c;border-radius:8px;padding:12px}
  .card h2{font-size:.85rem;color:#888;text-transform:uppercase;
           letter-spacing:.06em;margin-bottom:10px}
  table{width:100%;border-collapse:collapse;font-size:.85rem}
  td{padding:4px 6px;border-bottom:1px solid #2a2a2a;vertical-align:top}
  td:first-child{color:#888;white-space:nowrap;width:40%}
  td:last-child{color:#fff;word-break:break-all}
  .artwork{max-width:100%;border-radius:6px;display:block;margin:0 auto}
  .btns{display:flex;flex-wrap:wrap;gap:6px;margin-top:4px}
  button{background:#2a2a2a;color:#ddd;border:1px solid #444;border-radius:6px;
         padding:6px 12px;cursor:pointer;font-size:.85rem;transition:background .15s}
  button:hover{background:#3a3a3a}
  button:active{background:#1e5a8a}
  .player-badge{display:inline-block;padding:2px 8px;border-radius:10px;
                font-size:.75rem;background:#2a2a2a}
  .player-badge.kodi{background:#1a3d5c;color:#6af}
  .player-badge.mpchc{background:#3d1a1a;color:#f96}
  .player-badge.none{background:#2a2a2a;color:#666}
</style>
</head>
<body>
<h1>kodi-mpchc-bridge</h1>
<div id="status">Verbinde…</div>

<div class="grid">
  <!-- Artwork + controls -->
  <div class="card">
    <h2>Steuerung</h2>
    <img id="artwork" class="artwork" src="" alt="" style="display:none;margin-bottom:10px">
    <div class="btns">
      <button onclick="cmd('play_pause')">⏯ Play/Pause</button>
      <button onclick="cmd('stop')">⏹ Stop</button>
      <button onclick="cmd('prev_chapter')">⏮ Kapitel −</button>
      <button onclick="cmd('next_chapter')">Kapitel + ⏭</button>
      <button onclick="cmd('skip_backward')">⏪ −1 Min</button>
      <button onclick="cmd('skip_forward')">+1 Min ⏩</button>
      <button onclick="cmd('seek_backward_small')">◀ −10s</button>
      <button onclick="cmd('seek_forward_small')">+10s ▶</button>
      <button onclick="cmd('volume_down')">🔉</button>
      <button onclick="cmd('volume_up')">🔊</button>
      <button onclick="cmd('mute')">🔇 Mute</button>
      <button onclick="cmd('context_menu')">☰ Menü</button>
      <button onclick="cmd('navigate_back')">← Zurück</button>
      <button onclick="cmd('navigate_home')">⌂ Home</button>
    </div>
  </div>

  <!-- Playback state -->
  <div class="card">
    <h2>Wiedergabe</h2>
    <table id="tbl-play"></table>
  </div>

  <!-- Video info -->
  <div class="card">
    <h2>Video-Info</h2>
    <table id="tbl-video"></table>
  </div>

  <!-- Tracks -->
  <div class="card">
    <h2>Spuren</h2>
    <table id="tbl-tracks"></table>
  </div>
</div>

<script>
const PLAY_KEYS  = ['active_player','state','title','artist','album',
                    'media_type','position','duration','volume','muted',
                    'shuffle','repeat','year','tv_show','season','episode'];
const VIDEO_KEYS = ['video_width','video_height','video_fps','hdr',
                    'video_codec','video_bitrate_kbps'];
const TRACK_KEYS = ['current_audio','current_subtitle','current_chapter'];

let state = {};

function fmt(k, v) {
  if (v === null || v === undefined) return '—';
  if (k === 'position' || k === 'duration') {
    const s = Math.round(v);
    return new Date(s * 1000).toISOString().substr(11, 8);
  }
  if (k === 'volume') return v + ' %';
  if (k === 'video_fps') return v ? v.toFixed(3) + ' fps' : '—';
  if (k === 'video_bitrate_kbps') return v ? (v / 1000).toFixed(1) + ' Mbps' : '—';
  if (k === 'video_width' || k === 'video_height') return v ? v + ' px' : '—';
  if (typeof v === 'boolean') return v ? 'Ja' : 'Nein';
  if (Array.isArray(v)) return v.length ? v.map(t => t.label || t.name || '?').join(', ') : '—';
  return String(v || '—');
}

function label(k) {
  const L = {active_player:'Player',state:'Status',title:'Titel',artist:'Interpret',
    album:'Album',media_type:'Typ',position:'Position',duration:'Dauer',
    volume:'Lautstärke',muted:'Stumm',shuffle:'Shuffle',repeat:'Wiederholen',
    year:'Jahr',tv_show:'Serie',season:'Staffel',episode:'Episode',
    video_width:'Breite',video_height:'Höhe',video_fps:'Framerate',
    hdr:'HDR',video_codec:'Codec',video_bitrate_kbps:'Bitrate',
    current_audio:'Audio-Spur',current_subtitle:'Untertitel',current_chapter:'Kapitel'};
  return L[k] || k;
}

function renderTable(id, keys) {
  const rows = keys.map(k => {
    let v = fmt(k, state[k]);
    if (k === 'active_player') {
      const cls = state[k] || 'none';
      v = `<span class="player-badge ${cls}">${state[k] || 'none'}</span>`;
    }
    return `<tr><td>${label(k)}</td><td>${v}</td></tr>`;
  }).join('');
  document.getElementById(id).innerHTML = rows;
}

function renderAll() {
  renderTable('tbl-play',  PLAY_KEYS);
  renderTable('tbl-video', VIDEO_KEYS);
  const trackRows = TRACK_KEYS.map(k => {
    let display = fmt(k, state[k]);
    const listKey = k.replace('current_', '').replace('audio','audio_tracks')
                     .replace('subtitle','subtitle_tracks').replace('chapter','chapters');
    const arr = state[listKey] || [];
    if (arr.length) {
      const item = arr[state[k]] || arr[0];
      display = (item && (item.label || item.name)) ? (item.label || item.name) : display;
    }
    return `<tr><td>${label(k)}</td><td>${display}</td></tr>`;
  }).join('');
  document.getElementById('tbl-tracks').innerHTML = trackRows;

  const artEl = document.getElementById('artwork');
  if (state.artwork_url) {
    artEl.src = state.artwork_url;
    artEl.style.display = 'block';
  } else {
    artEl.style.display = 'none';
  }
}

function cmd(c, val) {
  const body = {cmd: c};
  if (val !== undefined) body.value = val;
  fetch('/api/command', {method:'POST',headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body)}).catch(() => {});
}

function connect() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${proto}://${location.host}/api/ws`);
  const el = document.getElementById('status');

  ws.onopen = () => { el.textContent = '● Verbunden'; el.className = 'ok'; };
  ws.onclose = () => {
    el.textContent = '○ Getrennt – verbinde erneut…'; el.className = 'err';
    setTimeout(connect, 3000);
  };
  ws.onerror = () => { el.className = 'err'; };
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'state_full') {
      state = msg.data;
    } else if (msg.type === 'state_patch') {
      Object.assign(state, msg.data);
    }
    renderAll();
  };
}

connect();
</script>
</body>
</html>
"""
