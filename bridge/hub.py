"""
Hub — orchestrates all components.

Wires together StateManager, KodiClient, MpcHcClient, MkV parser,
CommandRouter, and BridgeServer.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from bridge.config import ConfigManager
from bridge.kodi_client import KodiClient
from bridge.mkv_parser import parse_mkv, tracks_to_dicts
from bridge.mpchc_client import MpcHcClient
from bridge.router import CommandRouter
from bridge.server import BridgeServer
from bridge.state import StateManager

_LOG = logging.getLogger(__name__)


class Hub:
    def __init__(self, config: ConfigManager) -> None:
        self._config = config
        self._state = StateManager()
        self._last_filepath: str = ""

        cfg = config.cfg

        self._kodi = KodiClient(
            host=cfg.kodi_host,
            port=cfg.kodi_ws_port,
            username=cfg.kodi_username,
            password=cfg.kodi_password,
            on_state=self._on_state_update,
            ssl=cfg.kodi_ssl,
        )

        self._mpchc = MpcHcClient(
            host=cfg.mpchc_host,
            port=cfg.mpchc_port,
            on_state=self._on_state_update,
        )

        self._router = CommandRouter(self._state, self._kodi, self._mpchc)

        self._server = BridgeServer(
            state_manager=self._state,
            router=self._router,
            config_manager=config,
            host=cfg.server_host,
            port=cfg.server_port,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def start(self) -> None:
        await self._server.start()
        cfg = self._config.cfg
        if cfg.kodi_enabled:
            self._kodi.start()
        if cfg.mpchc_enabled:
            self._mpchc.start()
        _LOG.info("Hub started")

    async def stop(self) -> None:
        await self._kodi.stop()
        await self._mpchc.stop()
        await self._server.stop()
        _LOG.info("Hub stopped")

    # ------------------------------------------------------------------
    # State update callback (called by both clients)
    # ------------------------------------------------------------------
    async def _on_state_update(self, updates: dict[str, Any]) -> None:
        """
        Receive partial state updates from a client, apply them,
        trigger MKV parsing if filepath changed, then push diffs to WS.
        """
        # MPC-HC filepath change → parse MKV
        new_filepath = updates.get("filepath")
        if new_filepath is not None and new_filepath != self._last_filepath:
            self._last_filepath = new_filepath
            if new_filepath and new_filepath.lower().endswith(".mkv"):
                mkv_updates = await asyncio.get_event_loop().run_in_executor(
                    None, self._parse_mkv_sync, new_filepath
                )
                updates.update(mkv_updates)

        patch = self._state.apply(updates)
        if patch:
            await self._server.push_patch(patch)

    def _parse_mkv_sync(self, filepath: str) -> dict[str, Any]:
        """Parse MKV file and return state updates (runs in thread pool)."""
        try:
            tracks = parse_mkv(filepath)
            audio, subs, chapters = tracks_to_dicts(tracks)
            result: dict[str, Any] = {}
            if audio:
                result["audio_tracks"] = audio
            if subs:
                result["subtitle_tracks"] = subs
            if chapters:
                result["chapters"] = chapters
            _LOG.debug(
                "MKV parsed: %d audio, %d subs, %d chapters from %s",
                len(audio), len(subs), len(chapters), filepath,
            )
            return result
        except Exception as exc:
            _LOG.warning("MKV parse error for %s: %s", filepath, exc)
            return {}
