"""
MPC-HC HTTP client.

Polls the MPC-HC web interface and pushes state changes via the callback.
Commands are sent via GET /command.html.
"""

from __future__ import annotations

import asyncio
import logging
import re
import sys
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
CMD_PLAY_PAUSE = 889   # ID_PLAY_PLAYPAUSE (toggle)
CMD_PLAY = 887         # ID_PLAY_PLAY
CMD_PAUSE = 888        # ID_PLAY_PAUSE
CMD_STOP = 890
CMD_SEEK_FORWARD_SMALL = 902
CMD_SEEK_BACKWARD_SMALL = 903
CMD_VOLUME_UP = 904
CMD_VOLUME_DOWN = 905
CMD_MUTE = 907
CMD_NEXT_CHAPTER = 922   # swapped: 922 = next
CMD_PREV_CHAPTER = 921   # swapped: 921 = prev
CMD_NEXT_AUDIO = 952
CMD_PREV_AUDIO = 953
CMD_SKIP_FORWARD = 900
CMD_SKIP_BACKWARD = 901
CMD_NEXT_SUBTITLE = 954
CMD_PREV_SUBTITLE = 955
CMD_CONTEXT_MENU = 950

POLL_INTERVAL = 0.5  # seconds
RECONNECT_DELAY = 0.5

# Regex for status.html fields
_RE_FIELD = re.compile(r'<p id="([^"]+)"[^>]*>([^<]*)</p>', re.DOTALL)

# Base wm_command IDs for track selection via Win32
_AUDIO_BASE = 50000
_SUB_BASE = 50935

# Win32 PostMessage for track selection (HTTP API silently ignores these IDs)
_WM_COMMAND = 0x0111
_MPCHC_CLASSES = ("MediaPlayerClassicW", "MPC-BE", "MPC-BE64")

if sys.platform == "win32":
    import ctypes as _ctypes
    _user32: Any = _ctypes.windll.user32
else:
    _user32 = None


def _post_wm_command(cmd_id: int) -> bool:
    """Send WM_COMMAND directly to the MPC-HC window via Win32 PostMessageW."""
    if _user32 is None:
        return False
    for cls in _MPCHC_CLASSES:
        hwnd = _user32.FindWindowW(cls, None)
        if hwnd:
            _user32.PostMessageW(hwnd, _WM_COMMAND, cmd_id, 0)
            return True
    return False


def _ms_to_hmsms(ms: int) -> str:
    """Convert milliseconds to MPC-HC position string H:MM:SS:mmm."""
    ms = max(0, ms)
    hours, rem = divmod(ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1_000)
    return f"{hours}:{minutes:02d}:{seconds:02d}:{millis:03d}"


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
        return await self._get("/command.html", {"wm_command": -1, "position": _ms_to_hmsms(position_ms)})

    async def set_volume(self, volume: int) -> bool:
        """Set volume 0-100."""
        return await self._get("/command.html", {"wm_command": -2, "volume": max(0, min(100, volume))})

    async def set_audio_track(self, target: int, current: int, total: int) -> bool:
        """Cycle to audio track *target* using next/prev commands, or Win32 PostMessage."""
        if total <= 0:
            return False
        cmd_id = _AUDIO_BASE + target
        if _post_wm_command(cmd_id):
            _LOG.info("AUDIO select: target=%d  → PostMessage wm_command=%d", target, cmd_id)
            return True
        # Fallback: cycle via HTTP next/prev
        steps_fwd = (target - current) % total
        steps_bwd = (current - target) % total
        if steps_fwd == 0:
            return True
        cmd, steps = (CMD_NEXT_AUDIO, steps_fwd) if steps_fwd <= steps_bwd else (CMD_PREV_AUDIO, steps_bwd)
        direction = "NEXT" if cmd == CMD_NEXT_AUDIO else "PREV"
        _LOG.info("AUDIO select: target=%d  current=%d  total=%d  → %s x%d", target, current, total, direction, steps)
        for _ in range(steps):
            await self.send_command(cmd)
            await asyncio.sleep(0.05)
        return True

    async def set_subtitle_track(self, target: int, current: int, total: int) -> bool:
        """Cycle to subtitle track *target* using next/prev commands. target=-1 disables.

        MPC-HC's subtitle cycle has (total + 1) slots:
          0, 1, ..., total-1, [No subtitles], 0, 1, ...
        'No subtitles' (-1) maps to position *total* in the cycle.
        """
        if total <= 0:
            _LOG.warning("SUB select: target=%s  current=%s  total=0  → DROPPED (no tracks)",
                         "Off" if target < 0 else target, "Off" if current < 0 else current)
            return False

        cycle_len = total + 1
        pos_current = total if current < 0 else current
        pos_target = total if target < 0 else target

        steps_fwd = (pos_target - pos_current) % cycle_len
        steps_bwd = (pos_current - pos_target) % cycle_len

        t_lbl = "Off" if target < 0 else str(target)
        c_lbl = "Off" if current < 0 else str(current)

        if steps_fwd == 0:
            _LOG.info("SUB select: target=%s  current=%s  total=%d  → no-op (already selected)", t_lbl, c_lbl, total)
            return True

        cmd, steps = (CMD_NEXT_SUBTITLE, steps_fwd) if steps_fwd <= steps_bwd else (CMD_PREV_SUBTITLE, steps_bwd)
        direction = "NEXT" if cmd == CMD_NEXT_SUBTITLE else "PREV"
        _LOG.info("SUB select: target=%s  current=%s  total=%d  → %s x%d", t_lbl, c_lbl, total, direction, steps)
        for _ in range(steps):
            await self.send_command(cmd)
            await asyncio.sleep(0.05)
        return True

    async def send_key(self, vk_code: int, ctrl: bool = False, alt: bool = False) -> bool:
        """Send a keyboard message directly to the MPC-HC/MPC-BE window via Windows API.

        Use *alt=True* for Alt+key combos (e.g. Alt+Enter for fullscreen toggle).
        Alt keys require WM_SYSKEYDOWN / WM_SYSKEYUP instead of the regular variants.
        """
        import sys
        if sys.platform != "win32":
            _LOG.warning("send_key only supported on Windows")
            return False
        import ctypes

        WM_KEYDOWN    = 0x0100
        WM_KEYUP      = 0x0101
        WM_SYSKEYDOWN = 0x0104
        WM_SYSKEYUP   = 0x0105
        VK_CONTROL    = 0x11
        VK_MENU       = 0x12   # Alt key

        user32 = ctypes.windll.user32

        hwnd = 0
        for cls in _MPCHC_CLASSES:
            hwnd = user32.FindWindowW(cls, None)
            if hwnd:
                _LOG.debug("MPC window found: class=%s hwnd=%d", cls, hwnd)
                break

        if not hwnd:
            _LOG.warning("MPC window not found (tried %s)", ", ".join(_MPCHC_CLASSES))
            return False

        if ctrl:
            user32.PostMessageW(hwnd, WM_KEYDOWN, VK_CONTROL, 0)
            user32.PostMessageW(hwnd, WM_KEYDOWN, vk_code, 0)
            user32.PostMessageW(hwnd, WM_KEYUP, vk_code, 0)
            user32.PostMessageW(hwnd, WM_KEYUP, VK_CONTROL, 0)
        elif alt:
            # Alt combos must use WM_SYSKEYDOWN/UP
            user32.PostMessageW(hwnd, WM_SYSKEYDOWN, VK_MENU, 0)
            user32.PostMessageW(hwnd, WM_SYSKEYDOWN, vk_code, 0)
            user32.PostMessageW(hwnd, WM_SYSKEYUP, vk_code, 0)
            user32.PostMessageW(hwnd, WM_SYSKEYUP, VK_MENU, 0)
        else:
            user32.PostMessageW(hwnd, WM_KEYDOWN, vk_code, 0)
            user32.PostMessageW(hwnd, WM_KEYUP, vk_code, 0)

        _LOG.info("MPC key sent: vk=0x%02X ctrl=%s alt=%s", vk_code, ctrl, alt)
        return True

    async def close(self) -> None:
        """Close MPC-HC by killing the process that listens on our port."""
        import subprocess
        import sys
        if sys.platform != "win32":
            return
        _NW = subprocess.CREATE_NO_WINDOW
        try:
            # Find PID listening on the MPC-HC port
            port = int(self._base.rsplit(":", 1)[-1])
            out = subprocess.check_output(
                ["netstat", "-ano"], text=True, stderr=subprocess.DEVNULL,
                creationflags=_NW,
            )
            for line in out.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    pid = line.split()[-1]
                    subprocess.run(
                        ["taskkill", "/f", "/pid", pid],
                        capture_output=True, creationflags=_NW,
                    )
                    _LOG.info("MPC-HC closed (PID %s)", pid)
                    return
            # Fallback: kill by known exe names
            for name in ("mpc-hc64.exe", "mpc-hc.exe", "mpc-be64.exe", "mpc-be.exe"):
                result = subprocess.run(
                    ["taskkill", "/f", "/im", name],
                    capture_output=True, creationflags=_NW,
                )
                if result.returncode == 0:
                    _LOG.info("MPC-HC closed (%s)", name)
                    return
        except Exception as exc:
            _LOG.warning("MPC-HC close failed: %s", exc)

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
                elif params and "wm_command" in params:
                    # Log all actual commands (not polling)
                    _LOG.info("MPC-HC cmd %s → OK", params)
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
        _miss_streak = 0
        # True once we have fired active_player=mpchc at least once.
        # Used to decide whether a crash/close must trigger active_player=none.
        # Stays True even when _parse_status clears self._last on a brief idle
        # state, so a subsequent HTTP outage still fires the none transition.
        _reported_active = False
        # Fire active_player=none only after this many consecutive failed polls.
        # Prevents HDR / track-info flicker caused by brief HTTP unavailability
        # during resume seeks or file-open transitions (typ. 0.5–1 s).
        # 3 × 0.5 s = 1.5 s grace window before we declare MPC-HC gone.
        _GONE_AFTER = 3
        while self._running:
            fields = await self._fetch_status()
            if fields is None:
                _miss_streak += 1
                if _was_reachable:
                    if _miss_streak < _GONE_AFTER:
                        _LOG.debug(
                            "MPC-HC miss #%d/%d at %s — waiting before reset",
                            _miss_streak, _GONE_AFTER, self._base,
                        )
                    else:
                        _LOG.info(
                            "MPC-HC unreachable at %s (after %d misses) — "
                            "active_was=%s",
                            self._base, _miss_streak, _reported_active,
                        )
                        _was_reachable = False
                        had_active = _reported_active
                        _reported_active = False
                        self._last = {}
                        if had_active:
                            await self._on_state(
                                {"active_player": "none", "state": "idle", "filepath": ""}
                            )
                await asyncio.sleep(RECONNECT_DELAY)
                continue
            _miss_streak = 0  # successful poll — reset streak

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
                _ap = updates.get("active_player")
                if _ap == "mpchc":
                    _reported_active = True
                elif _ap == "none":
                    _reported_active = False
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

        # Active track names — hub resolves these to indices using MKV track lists
        if audiotrack != self._last.get("audiotrack"):
            updates["audiotrack_name"] = audiotrack
            self._last["audiotrack"] = audiotrack

        if subtitletrack != self._last.get("subtitletrack"):
            updates["subtitletrack_name"] = subtitletrack
            self._last["subtitletrack"] = subtitletrack

        # Current chapter — MPC-HC reports 1-based; state uses 0-based index
        chapternumber_str = fields.get("chapternumber", "")
        if chapternumber_str and chapternumber_str.isdigit():
            chapter_idx = max(0, int(chapternumber_str) - 1)
            if chapter_idx != self._last.get("current_chapter"):
                updates["current_chapter"] = chapter_idx
                self._last["current_chapter"] = chapter_idx

        return updates
