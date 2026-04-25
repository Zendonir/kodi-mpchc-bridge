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
import mimetypes
from pathlib import Path
from typing import Any

from aiohttp import web

_STATIC_DIR = Path(__file__).parent / "static"

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
        self._app.router.add_get("/api/command", self._handle_command_get)
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
        self._app.router.add_get("/static/{filename}", self._handle_static)
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
        path = _STATIC_DIR / "index.html"
        try:
            return web.Response(body=path.read_bytes(), content_type="text/html")
        except OSError:
            return web.Response(text="UI not found", status=404)

    async def _handle_static(self, request: web.Request) -> web.Response:
        filename = request.match_info["filename"]
        path = _STATIC_DIR / filename
        if not path.is_file() or not path.resolve().is_relative_to(_STATIC_DIR.resolve()):
            return web.Response(text="not found", status=404)
        ct, _ = mimetypes.guess_type(filename)
        return web.Response(body=path.read_bytes(), content_type=ct or "application/octet-stream")

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

    async def _handle_command_get(self, request: web.Request) -> web.Response:
        """GET /api/command?cmd=play_pause&value=30  — browser-friendly shortcut."""
        cmd = request.rel_url.query.get("cmd")
        if not cmd:
            return web.json_response({"error": "missing cmd"}, status=400)
        raw = request.rel_url.query.get("value")
        value: object = None
        if raw is not None:
            try:
                value = int(raw)
            except ValueError:
                try:
                    value = float(raw)
                except ValueError:
                    value = raw
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

