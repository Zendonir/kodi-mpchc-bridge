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
        # MPC-HC web API: POST or GET /command.html with position=<ms>
        # wm_command must be omitted (or 0) for a pure position seek
        return await self._get("/command.html", {"position": position_ms})

    async def set_volume(self, volume: int) -> bool:
        """Set volume 0-100."""
        return await self._get("/command.html", {"volume": max(0, min(100, volume))})

    async def set_audio_track(self, pos: int) -> bool:
        """Select audio track by 0-based position."""
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
        url = self._base + path
        try:
            session = await self._get_session()
            async with session.get(url, params=params) as resp:
                ok = resp.status == 200
                if not ok:
                    body = await resp.text()
                    _LOG.warning("MPC-HC %s params=%s → HTTP %d  body=%r", path, params, resp.status, body[:200])
                else:
                    _LOG.debug("MPC-HC %s params=%s → OK", path, params)
                return ok
        except Exception as exc:
            _LOG.warning("MPC-HC request failed: %s  url=%s  params=%s", exc, url, params)
            return False

    async def _fetch_status(self) -> dict[str, str] | None:
        # Try /variables.html first (more reliable in newer MPC-HC builds),
        # fall back to /status.html
        for path in ("/variables.html", "/status.html"):
            try:
                session = await self._get_session()
                async with session.get(self._base + path) as resp:
                    if resp.status != 200:
                        continue
                    html = await resp.text()
                    fields = {m.group(1): m.group(2).strip() for m in _RE_FIELD.finditer(html)}
                    # Accept if we got at least a "state" field
                    if "state" in fields:
                        if not hasattr(self, "_status_path") or self._status_path != path:
                            self._status_path = path
                            _LOG.info("MPC-HC: using endpoint %s", path)
                        return fields
            except Exception:
                continue
        return None

    async def _poll_loop(self) -> None:
        _LOG.info("MPC-HC polling started at %s", self._base)
        _was_reachable = False
        while self._running:
            fields = await self._fetch_status()
            if fields is None:
                if _was_reachable:
                    _LOG.info("MPC-HC unreachable at %s", self._base)
                    _was_reachable = False
                if self._last:
                    # Was connected, now lost
                    self._last = {}
                    await self._on_state({"active_player": "none", "state": "idle", "filepath": ""})
                await asyncio.sleep(RECONNECT_DELAY)
                continue

            if not _was_reachable:
                _LOG.info(
                    "MPC-HC reachable at %s — parsed fields: %s",
                    self._base, list(fields.keys()),
                )
                _LOG.info(
                    "MPC-HC state=%s (%s)  file=%s  filepath=%s",
                    fields.get("state", "?"),
                    fields.get("statestring", "?"),
                    fields.get("file", "<missing>") or "<empty>",
                    fields.get("filepath", "<missing>") or "<empty>",
                )
                _was_reachable = True

            updates = self._parse_status(fields)
            if updates:
                _LOG.debug("MPC-HC update: %s", {k: v for k, v in updates.items() if k != "filepath"})
                await self._on_state(updates)

            await asyncio.sleep(POLL_INTERVAL)

    def _parse_status(self, fields: dict[str, str]) -> dict[str, Any]:
        """
        Compare *fields* with last known values and return unified-state updates.
        """
        updates: dict[str, Any] = {}

        raw_state = int(fields.get("state", "-1"))
        # Prefer "filepath" (full path) over "file" (filename only)
        filepath = fields.get("filepath", "") or fields.get("file", "")
        title = fields.get("file", "")  # short filename for display
        position_ms = int(fields.get("position", "0") or 0)
        duration_ms = int(fields.get("duration", "0") or 0)
        volume = int(fields.get("volumelevel", "0") or 0)
        muted = fields.get("muted", "0") == "1"
        # current track positions (0-based integers, empty string if unknown)
        audiotrack = fields.get("audiotrack", "")
        subtitletrack = fields.get("subtitletrack", "")

        # Active player: MPC-HC is active when a file is loaded (not idle/no-source)
        is_active = raw_state >= _STATE_STOPPED and bool(filepath)

        prev_filepath = self._last.get("filepath", "")

        if is_active and not self._last.get("active"):
            updates["active_player"] = "mpchc"
            updates["filepath"] = filepath
            if title:
                updates["title"] = title
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
            if title:
                updates["title"] = title
            self._last["filepath"] = filepath

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

        # Active track indices (MPC-HC reports 0-based)
        if audiotrack != "" and audiotrack != self._last.get("audiotrack"):
            try:
                updates["current_audio"] = int(audiotrack)
                self._last["audiotrack"] = audiotrack
            except ValueError:
                pass

        if subtitletrack != "" and subtitletrack != self._last.get("subtitletrack"):
            try:
                sub_idx = int(subtitletrack)
                updates["current_subtitle"] = sub_idx if sub_idx >= 0 else -1
                self._last["subtitletrack"] = subtitletrack
            except ValueError:
                pass

        return updates
