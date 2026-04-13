"""
Hub — orchestrates all components.

Wires together StateManager, KodiClient, MpcHcClient, MkV parser,
CommandRouter, and BridgeServer.

Priority rule:
  MPC-HC wins whenever it has a file loaded (active_player == "mpchc").
  While MPC-HC is active, Kodi state updates are filtered out — only
  volume/mute pass through so the Kodi volume control still works.
  When MPC-HC becomes idle again, Kodi state is immediately re-synced.
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

# Fields that Kodi may update even while MPC-HC is active
_KODI_PASSTHROUGH_WHILE_MPCHC = {"volume", "muted"}


class Hub:
    def __init__(self, config: ConfigManager) -> None:
        self._config = config
        self._state = StateManager()
        self._last_filepath: str = ""
        self._mpchc_active = False  # True while MPC-HC has a file loaded

        cfg = config.cfg

        self._kodi = KodiClient(
            host=cfg.kodi_host,
            port=cfg.kodi_ws_port,
            username=cfg.kodi_username,
            password=cfg.kodi_password,
            on_state=self._on_kodi_update,
            ssl=cfg.kodi_ssl,
        )

        self._mpchc = MpcHcClient(
            host=cfg.mpchc_host,
            port=cfg.mpchc_port,
            on_state=self._on_mpchc_update,
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
    # MPC-HC state handler
    # ------------------------------------------------------------------
    async def _on_mpchc_update(self, updates: dict[str, Any]) -> None:
        new_active = updates.get("active_player")

        if new_active == "mpchc" and not self._mpchc_active:
            self._mpchc_active = True
            _LOG.info("ACTIVE PLAYER → mpchc  (file: %s)", updates.get("filepath", ""))
        elif new_active == "none" and self._mpchc_active:
            self._mpchc_active = False
            _LOG.info("ACTIVE PLAYER → none   (mpchc idle, kodi may take over)")

        # MKV parsing on filepath change
        new_filepath = updates.get("filepath")
        if new_filepath is not None and new_filepath != self._last_filepath:
            self._last_filepath = new_filepath
            _LOG.info("MPC-HC filepath: %s", new_filepath)
            if new_filepath and new_filepath.lower().endswith(".mkv"):
                _LOG.info("Parsing MKV tracks…")
                mkv_updates = await asyncio.get_running_loop().run_in_executor(
                    None, self._parse_mkv_sync, new_filepath
                )
                updates.update(mkv_updates)

        # Log significant state changes
        if "state" in updates:
            _LOG.info("MPCHC state: %s  pos=%.1fs", updates["state"], updates.get("position", 0))

        await self._push(updates)

    # ------------------------------------------------------------------
    # Kodi state handler
    # ------------------------------------------------------------------
    async def _on_kodi_update(self, updates: dict[str, Any]) -> None:
        if self._mpchc_active:
            # Filter: only volume/mute pass through while MPC-HC is playing
            filtered = {k: v for k, v in updates.items() if k in _KODI_PASSTHROUGH_WHILE_MPCHC}
            if filtered:
                _LOG.debug("Kodi update while mpchc active — passing only: %s", list(filtered))
                await self._push(filtered)
            else:
                _LOG.debug("Kodi update while mpchc active — dropped: %s", list(updates))
            return

        # Log active player transitions from Kodi
        if updates.get("active_player") == "kodi" and self._state.state.active_player != "kodi":
            _LOG.info("ACTIVE PLAYER → kodi   (state=%s, title=%s)",
                      updates.get("state", "?"), updates.get("title", ""))
        if "state" in updates and updates.get("active_player") != "kodi":
            _LOG.debug("Kodi state: %s  pos=%.1fs", updates["state"], updates.get("position", 0))

        await self._push(updates)

    # ------------------------------------------------------------------
    # Common push
    # ------------------------------------------------------------------
    async def _push(self, updates: dict[str, Any]) -> None:
        patch = self._state.apply(updates)
        if patch:
            await self._server.push_patch(patch)

    # ------------------------------------------------------------------
    # MKV parser (blocking, runs in thread pool)
    # ------------------------------------------------------------------
    def _parse_mkv_sync(self, filepath: str) -> dict[str, Any]:
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
