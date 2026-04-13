"""
MPC-HC HTTP client.

Polls the MPC-HC web interface and pushes state changes via the callback.
Commands are sent via GET /command.html.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Callable, Awaitable

import aiohttp

_LOG = logging.getLogger(__name__)

# MPC-HC state integers
_STATE_NOSOURCE = -1
_STATE_STOPPED = 0
_STATE_PAUSED = 1
_STATE_PLAYING = 2

_STATE_MAP = {
    _STATE_NOSOURCE: "idle",
    _STATE_STOPPED: "stopped",
    _STATE_PAUSED: "paused",
    _STATE_PLAYING: "playing",
}

# /command.html wm_command values
CMD_PLAY_PAUSE = 887
CMD_PLAY = 888
CMD_STOP = 890
CMD_SEEK_FORWARD_SMALL = 902
CMD_SEEK_BACKWARD_SMALL = 903
CMD_VOLUME_UP = 904
CMD_VOLUME_DOWN = 905
CMD_MUTE = 907
CMD_NEXT_CHAPTER = 921
CMD_PREV_CHAPTER = 922
CMD_NEXT_AUDIO = 952
CMD_PREV_AUDIO = 953
CMD_SKIP_FORWARD = 900
CMD_SKIP_BACKWARD = 901

POLL_INTERVAL = 0.5  # seconds
RECONNECT_DELAY = 3.0

# Regex for status.html fields
_RE_FIELD = re.compile(r'<p id="([^"]+)"[^>]*>([^<]*)</p>', re.DOTALL)


StateCallback = Callable[[dict[str, Any]], Awaitable[None]]


class MpcHcClient:
    """
    Polls MPC-HC status and fires *on_state* with changed fields.

    The callback receives a dict that maps unified-state field names
    to new values (only changed fields).
    """

    def __init__(self, host: str, port: int, on_state: StateCallback) -> None:
        self._base = f"http://{host}:{port}"
        self._on_state = on_state
        self._session: aiohttp.ClientSession | None = None
        self._running = False
        self._task: asyncio.Task | None = None

        # last known raw values for change detection
        self._last: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start polling in a background task."""
        self._running = True
        self._task = asyncio.create_task(self._poll_loop(), name="mpchc-poll")

    async def stop(self) -> None:
        """Stop polling and close the session."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._session:
            await self._session.close()
            self._session = None

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    async def send_command(self, wm_command: int, extra: dict | None = None) -> bool:
        """Send a wm_command to MPC-HC. Returns True on success."""
        params: dict[str, Any] = {"wm_command": wm_command}
        if extra:
            params.update(extra)
        return await self._get("/command.html", params)

    async def seek(self, position_ms: int) -> bool:
        """Seek to absolute position in milliseconds."""
        return await self._get("/command.html", {"wm_command": -1, "position": position_ms})

    async def set_volume(self, volume: int) -> bool:
        """Set volume 0-100 (MPC-HC accepts 0-100)."""
        # MPC-HC doesn't have a direct set-volume endpoint; we use the slider
        return await self._get("/command.html", {"wm_command": -1, "volume": max(0, min(100, volume))})

    async def set_audio_track(self, pos: int) -> bool:
        """Select audio track by 0-based position."""
        # MPC-HC API: audioid parameter (1-based in some versions, 0-based in others)
        # We navigate from track 0 by sending next-audio-track commands
        # Simpler: use audioid directly if supported
        return await self._get("/command.html", {"wm_command": -1, "audioid": pos})

    async def set_subtitle_track(self, pos: int) -> bool:
        """Select subtitle track by 0-based position. pos=-1 disables subtitles."""
        if pos < 0:
            return await self._get("/command.html", {"wm_command": -1, "subid": -1})
        return await self._get("/command.html", {"wm_command": -1, "subid": pos})

    # ------------------------------------------------------------------
    # Internal polling
    # ------------------------------------------------------------------
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=2.0)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def _get(self, path: str, params: dict | None = None) -> bool:
        try:
            session = await self._get_session()
            async with session.get(self._base + path, params=params) as resp:
                return resp.status == 200
        except Exception as exc:
            _LOG.debug("MPC-HC request failed: %s", exc)
            return False

    async def _fetch_status(self) -> dict[str, str] | None:
        try:
            session = await self._get_session()
            async with session.get(self._base + "/status.html") as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
                return {m.group(1): m.group(2).strip() for m in _RE_FIELD.finditer(html)}
        except Exception:
            return None

    async def _poll_loop(self) -> None:
        _LOG.info("MPC-HC polling started at %s", self._base)
        while self._running:
            fields = await self._fetch_status()
            if fields is None:
                if self._last:
                    # Was connected, now lost
                    self._last = {}
                    await self._on_state({"active_player": "none", "state": "idle", "filepath": ""})
                await asyncio.sleep(RECONNECT_DELAY)
                continue

            updates = self._parse_status(fields)
            if updates:
                await self._on_state(updates)

            await asyncio.sleep(POLL_INTERVAL)

    def _parse_status(self, fields: dict[str, str]) -> dict[str, Any]:
        """
        Compare *fields* with last known values and return unified-state updates.
        """
        updates: dict[str, Any] = {}

        raw_state = int(fields.get("state", "-1"))
        filepath = fields.get("file", "")
        position_ms = int(fields.get("position", "0") or 0)
        duration_ms = int(fields.get("duration", "0") or 0)
        volume = int(fields.get("volumelevel", "0") or 0)
        muted = fields.get("muted", "0") == "1"

        # Active player: MPC-HC is active when a file is loaded (not idle/no-source)
        is_active = raw_state >= _STATE_STOPPED and bool(filepath)

        prev_filepath = self._last.get("file", "")
        prev_state = self._last.get("state")

        if is_active and not self._last.get("active"):
            updates["active_player"] = "mpchc"
            updates["filepath"] = filepath
            self._last["active"] = True

        if not is_active and self._last.get("active"):
            self._last["active"] = False
            updates["active_player"] = "none"
            updates["state"] = "idle"
            updates["filepath"] = ""
            self._last = {}
            return updates

        if not is_active:
            self._last = {}
            return updates

        unified_state = _STATE_MAP.get(raw_state, "idle")
        if unified_state != self._last.get("unified_state"):
            updates["state"] = unified_state
            self._last["unified_state"] = unified_state

        if filepath != prev_filepath:
            updates["filepath"] = filepath
            self._last["file"] = filepath

        pos_sec = position_ms / 1000.0
        dur_sec = duration_ms / 1000.0

        if abs(pos_sec - self._last.get("position", -999)) > 0.9:
            updates["position"] = pos_sec
            self._last["position"] = pos_sec

        if dur_sec != self._last.get("duration") and dur_sec > 0:
            updates["duration"] = dur_sec
            self._last["duration"] = dur_sec

        if volume != self._last.get("volume"):
            updates["volume"] = volume
            self._last["volume"] = volume

        if muted != self._last.get("muted"):
            updates["muted"] = muted
            self._last["muted"] = muted

        return updates
