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
        return web.Response(text="kodi-mpchc-bridge running", content_type="text/plain")

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
