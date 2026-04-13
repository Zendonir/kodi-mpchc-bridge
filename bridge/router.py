"""
Command router.

Receives command dicts from clients and dispatches them to the correct
player (Kodi or MPC-HC) based on which is currently active.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bridge.kodi_client import KodiClient
    from bridge.mpchc_client import MpcHcClient
    from bridge.state import StateManager

_LOG = logging.getLogger(__name__)

# Commands that are always routed to Kodi (UI/app-level)
_KODI_ONLY = {
    "navigate_up", "navigate_down", "navigate_left", "navigate_right",
    "navigate_select", "navigate_back", "navigate_home",
    "context_menu", "show_osd", "show_info",
}

# Commands that are always routed to MPC-HC when it is active
_MPCHC_SPECIFIC = {
    "mpchc_next_audio", "mpchc_prev_audio",
}


class CommandRouter:
    def __init__(
        self,
        state: "StateManager",
        kodi: "KodiClient",
        mpchc: "MpcHcClient",
    ) -> None:
        self._state = state
        self._kodi = kodi
        self._mpchc = mpchc

    @property
    def _active(self) -> str:
        return self._state.state.active_player

    async def dispatch(self, cmd: str, value: object = None) -> bool:
        """
        Dispatch *cmd* to the appropriate player.

        Returns True if the command was handled.
        """
        _LOG.debug("dispatch cmd=%s value=%s active=%s", cmd, value, self._active)

        # Navigation always goes to Kodi
        if cmd in _KODI_ONLY:
            return await self._kodi_navigate(cmd)

        if self._active == "mpchc":
            return await self._handle_mpchc(cmd, value)
        elif self._active == "kodi":
            return await self._handle_kodi(cmd, value)
        else:
            _LOG.debug("No active player for cmd=%s", cmd)
            return False

    # ------------------------------------------------------------------
    # MPC-HC commands
    # ------------------------------------------------------------------
    async def _handle_mpchc(self, cmd: str, value: object) -> bool:
        from bridge.mpchc_client import (
            CMD_PLAY_PAUSE, CMD_STOP, CMD_NEXT_CHAPTER, CMD_PREV_CHAPTER,
            CMD_SKIP_FORWARD, CMD_SKIP_BACKWARD,
            CMD_SEEK_FORWARD_SMALL, CMD_SEEK_BACKWARD_SMALL,
            CMD_VOLUME_UP, CMD_VOLUME_DOWN, CMD_MUTE,
            CMD_NEXT_AUDIO, CMD_PREV_AUDIO,
        )

        if cmd == "play_pause":
            return await self._mpchc.send_command(CMD_PLAY_PAUSE)
        elif cmd == "stop":
            return await self._mpchc.send_command(CMD_STOP)
        elif cmd == "next_chapter":
            return await self._mpchc.send_command(CMD_NEXT_CHAPTER)
        elif cmd == "prev_chapter":
            return await self._mpchc.send_command(CMD_PREV_CHAPTER)
        elif cmd == "skip_forward":
            return await self._mpchc.send_command(CMD_SKIP_FORWARD)
        elif cmd == "skip_backward":
            return await self._mpchc.send_command(CMD_SKIP_BACKWARD)
        elif cmd == "seek_forward_small":
            return await self._mpchc.send_command(CMD_SEEK_FORWARD_SMALL)
        elif cmd == "seek_backward_small":
            return await self._mpchc.send_command(CMD_SEEK_BACKWARD_SMALL)
        elif cmd == "seek" and value is not None:
            pos_ms = int(float(value) * 1000)
            return await self._mpchc.seek(pos_ms)
        elif cmd == "volume_up":
            return await self._mpchc.send_command(CMD_VOLUME_UP)
        elif cmd == "volume_down":
            return await self._mpchc.send_command(CMD_VOLUME_DOWN)
        elif cmd == "mute":
            return await self._mpchc.send_command(CMD_MUTE)
        elif cmd == "set_volume" and value is not None:
            return await self._mpchc.set_volume(int(value))
        elif cmd == "audio_track" and value is not None:
            return await self._mpchc.set_audio_track(int(value))
        elif cmd == "subtitle_track" and value is not None:
            return await self._mpchc.set_subtitle_track(int(value))
        elif cmd == "mpchc_next_audio":
            return await self._mpchc.send_command(CMD_NEXT_AUDIO)
        elif cmd == "mpchc_prev_audio":
            return await self._mpchc.send_command(CMD_PREV_AUDIO)
        else:
            _LOG.debug("Unknown MPC-HC cmd: %s", cmd)
            return False

    # ------------------------------------------------------------------
    # Kodi commands
    # ------------------------------------------------------------------
    async def _handle_kodi(self, cmd: str, value: object) -> bool:
        if cmd == "play_pause":
            await self._kodi.play_pause()
        elif cmd == "stop":
            await self._kodi.stop()
        elif cmd == "next_chapter":
            await self._kodi.next_chapter()
        elif cmd == "prev_chapter":
            await self._kodi.prev_chapter()
        elif cmd == "skip_forward":
            await self._kodi.skip_forward()
        elif cmd == "skip_backward":
            await self._kodi.skip_backward()
        elif cmd == "seek" and value is not None:
            await self._kodi.seek(float(value))
        elif cmd == "set_volume" and value is not None:
            await self._kodi.set_volume(int(value))
        elif cmd == "volume_up":
            cur = self._state.state.volume
            await self._kodi.set_volume(min(100, cur + 5))
        elif cmd == "volume_down":
            cur = self._state.state.volume
            await self._kodi.set_volume(max(0, cur - 5))
        elif cmd == "mute":
            await self._kodi.set_mute(not self._state.state.muted)
        elif cmd == "audio_track" and value is not None:
            await self._kodi.set_audio_stream(int(value))
        elif cmd == "subtitle_track" and value is not None:
            await self._kodi.set_subtitle_stream(int(value))
        elif cmd == "shuffle":
            await self._kodi.set_shuffle(not self._state.state.shuffle)
        elif cmd == "repeat" and value is not None:
            await self._kodi.set_repeat(str(value))
        else:
            _LOG.debug("Unknown Kodi cmd: %s", cmd)
            return False
        return True

    async def _kodi_navigate(self, cmd: str) -> bool:
        action_map = {
            "navigate_up": "up",
            "navigate_down": "down",
            "navigate_left": "left",
            "navigate_right": "right",
            "navigate_select": "select",
            "navigate_back": "back",
            "navigate_home": "home",
            "context_menu": "contextmenu",
            "show_osd": "osd",
            "show_info": "info",
        }
        action = action_map.get(cmd)
        if action:
            await self._kodi.navigate(action)
            return True
        return False
