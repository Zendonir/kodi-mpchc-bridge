"""
Command router.

Receives command dicts from clients and dispatches them to the correct
player (Kodi or MPC-HC) based on which is currently active.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from bridge.kodi_client import KodiClient
    from bridge.mpchc_client import MpcHcClient
    from bridge.state import StateManager

_LOG = logging.getLogger(__name__)

# Commands that are always routed to Kodi (UI/app-level), regardless of active player
_KODI_ONLY = {
    "show_osd",
}

# Navigation commands with smart routing:
#   MPC-HC active → handled by MPC-HC (keyboard/close/context)
#   otherwise     → forwarded to Kodi
_SMART_NAV = {
    "navigate_up", "navigate_down", "navigate_left", "navigate_right",
    "navigate_select", "navigate_back", "navigate_home",
    "show_info", "context_menu",
}

# Windows virtual-key codes used for MPC-HC keyboard control
_VK_LEFT    = 0x25
_VK_RIGHT   = 0x27
_VK_UP      = 0x26
_VK_DOWN    = 0x28
_VK_RETURN  = 0x0D
_VK_J       = 0x4A
_VK_APPS    = 0x5D  # "Menu / Applications" key — opens context menus
_VK_F11     = 0x7A  # F11 — generic fullscreen toggle

# Commands that are always routed to MPC-HC when it is active
_MPCHC_SPECIFIC = {
    "mpchc_next_audio", "mpchc_prev_audio",
}


def _find_process_window(exe_name: str) -> int:
    """
    Return the HWND of the first visible top-level window belonging to
    *exe_name* (e.g. "kodi.exe").  Returns 0 if not found.
    Only works on Windows.
    """
    if sys.platform != "win32":
        return 0
    import ctypes
    import ctypes.wintypes
    import subprocess

    # Resolve PID via tasklist
    try:
        out = subprocess.check_output(
            ["tasklist", "/fi", f"imagename eq {exe_name}", "/fo", "csv", "/nh"],
            text=True, stderr=subprocess.DEVNULL,
        )
        target_pid = 0
        for line in out.strip().splitlines():
            parts = line.strip('"').split('","')
            if parts and parts[0].lower() == exe_name.lower():
                target_pid = int(parts[1])
                break
        if not target_pid:
            return 0
    except Exception:
        return 0

    # Enumerate top-level windows to find one owned by that PID
    found: list[int] = [0]
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)

    def _cb(hwnd: int, _: int) -> bool:
        pid = ctypes.wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == target_pid and ctypes.windll.user32.IsWindowVisible(hwnd):
            found[0] = hwnd
            return False  # stop enumeration
        return True

    ctypes.windll.user32.EnumWindows(EnumWindowsProc(_cb), 0)
    return found[0]


class CommandRouter:
    def __init__(
        self,
        state: "StateManager",
        kodi: "KodiClient",
        mpchc: "MpcHcClient",
        on_mpchc_stop: "Callable | None" = None,
        on_toggle_ext_player: "Callable | None" = None,
        on_play_episode: "Callable | None" = None,
        on_kiosk_toggle: "Callable | None" = None,
        on_toggle_watched: "Callable | None" = None,
    ) -> None:
        self._state = state
        self._kodi = kodi
        self._mpchc = mpchc
        # Optional async callback — called before MPC-HC is closed so the hub
        # can immediately signal active_player=none (speeds up Kodi return).
        self._on_mpchc_stop = on_mpchc_stop
        # Optional async callback — toggles external_player_enabled in config.
        self._on_toggle_ext_player = on_toggle_ext_player
        # Optional async callback(direction) — plays next/prev episode from the
        # season episode list currently in state.
        self._on_play_episode = on_play_episode
        # Optional async callback — kiosk mode: kill Kodi / toggle Explorer.
        # When None, the classic minimize/restore behaviour is used.
        self._on_kiosk_toggle = on_kiosk_toggle
        # Optional async callback — toggle watched/unwatched in Kodi library.
        self._on_toggle_watched = on_toggle_watched
        # While the resume dialog is visible this is set to the dialog's
        # inject-key function.  All nav/stop commands are redirected there.
        self._dialog_handler: "Callable[[str], None] | None" = None

    def set_dialog_handler(self, handler: "Callable[[str], None] | None") -> None:
        """Register / unregister the active resume-dialog key-inject function.

        Thread-safe: may be called from the dialog thread (thread-pool executor).
        The handler itself schedules work via tkinter's ``root.after()``.
        """
        self._dialog_handler = handler

    @property
    def _active(self) -> str:
        return self._state.state.active_player

    async def dispatch(self, cmd: str, value: object = None) -> bool:
        """
        Dispatch *cmd* to the appropriate player.

        Returns True if the command was handled.
        """
        # Resume-dialog intercept — while the dialog is on screen all
        # navigation and stop/back commands are forwarded directly to it.
        if self._dialog_handler is not None:
            _DIALOG_MAP: dict[str, str] = {
                "navigate_left":   "Left",
                "navigate_up":     "Left",
                "navigate_right":  "Right",
                "navigate_down":   "Right",
                "navigate_select": "Return",
                # Back / Home / Stop → cancel the dialog entirely (no launch)
                "navigate_back":   "Cancel",
                "navigate_home":   "Cancel",
                "stop":            "Cancel",
            }
            keysym = _DIALOG_MAP.get(cmd)
            if keysym is not None:
                _LOG.info("CMD %-22s → resume-dialog (%s)", cmd, keysym)
                self._dialog_handler(keysym)
                return True

        active = self._active

        # Episode navigation — available whenever a season list is loaded
        if cmd in ("next_episode", "prev_episode"):
            _LOG.info("CMD %-22s → episode nav", cmd)
            if self._on_play_episode:
                return await self._on_play_episode(cmd)
            return False

        # Toggle watched / unwatched — always available when media_id is known
        if cmd == "toggle_watched":
            _LOG.info("CMD %-22s → toggle watched/unwatched", cmd)
            if self._on_toggle_watched:
                return await self._on_toggle_watched()
            return False

        # System-level commands (player-independent)
        if cmd == "toggle_external_player":
            _LOG.info("CMD %-22s → system (toggle external player)", cmd)
            if self._on_toggle_ext_player:
                return await self._on_toggle_ext_player()
            return False

        if cmd == "kodi_windows":
            _LOG.info("CMD %-22s → system (Kodi/Windows toggle)", cmd)
            if self._on_kiosk_toggle:
                return await self._on_kiosk_toggle()
            return self._toggle_kodi_windows()

        if cmd == "system_restart":
            _LOG.info("CMD %-22s → system (PC restart in 10 s)", cmd)
            return self._system_restart()

        if cmd == "system_shutdown":
            _LOG.info("CMD %-22s → system (PC shutdown in 10 s)", cmd)
            return self._system_shutdown()

        if cmd == "fullscreen":
            _LOG.info("CMD %-22s → system (fullscreen, active=%s)", cmd, active)
            return await self._fullscreen(active)

        # Always-Kodi navigation (OSD)
        if cmd in _KODI_ONLY:
            _LOG.info("CMD %-22s → kodi (always)", cmd)
            return await self._kodi_navigate(cmd)

        # show_info — if a library item is known, always open Kodi's info dialog
        if cmd == "show_info":
            media_id   = self._state.state.media_id
            media_type = self._state.state.media_type
            if media_id > 0 and media_type in ("movie", "episode"):
                _LOG.info("CMD %-22s → kodi movie info (media_id=%d)", cmd, media_id)
                await self._kodi.show_movie_info(media_type, media_id)
                return True
            # No library item — fall back to default behaviour
            if active == "mpchc":
                _LOG.info("CMD %-22s → mpchc (Ctrl+J fallback)", cmd)
                return await self._handle_mpchc_nav(cmd)
            else:
                _LOG.info("CMD %-22s → kodi (info action)", cmd)
                return await self._kodi_navigate(cmd)

        # Smart navigation: MPC-HC gets keyboard control when active
        if cmd in _SMART_NAV:
            if active == "mpchc":
                _LOG.info("CMD %-22s → mpchc (nav/key)", cmd)
                return await self._handle_mpchc_nav(cmd)
            else:
                _LOG.info("CMD %-22s → kodi (navigation)", cmd)
                return await self._kodi_navigate(cmd)

        if active == "mpchc":
            _LOG.info("CMD %-22s → mpchc  (value=%s)", cmd, value)
            return await self._handle_mpchc(cmd, value)
        elif active == "kodi":
            _LOG.info("CMD %-22s → kodi   (value=%s)", cmd, value)
            return await self._handle_kodi(cmd, value)
        else:
            _LOG.info("CMD %-22s → DROPPED (no active player)", cmd)
            return False

    # ------------------------------------------------------------------
    # System commands
    # ------------------------------------------------------------------
    def _toggle_kodi_windows(self) -> bool:
        """
        Minimize Kodi to show the Windows desktop, or restore it if minimized.
        Works by finding the main Kodi window via its process name.
        """
        if sys.platform != "win32":
            _LOG.warning("kodi_windows toggle only supported on Windows")
            return False

        import ctypes

        SW_MINIMIZE = 6
        SW_RESTORE  = 9
        user32 = ctypes.windll.user32

        hwnd = _find_process_window("kodi.exe")
        if not hwnd:
            _LOG.warning("kodi_windows: Kodi window not found")
            return False

        if user32.IsIconic(hwnd):
            # Kodi is minimized → restore and bring to front
            user32.ShowWindow(hwnd, SW_RESTORE)
            user32.SetForegroundWindow(hwnd)
            _LOG.info("kodi_windows: Kodi restored to foreground")
        else:
            # Kodi is visible → minimize (Windows desktop becomes visible)
            user32.ShowWindow(hwnd, SW_MINIMIZE)
            _LOG.info("kodi_windows: Kodi minimized, Windows desktop visible")

        return True

    def _system_restart(self) -> bool:
        """Schedule a Windows system restart in 10 seconds via shutdown.exe."""
        if sys.platform != "win32":
            _LOG.warning("system_restart only supported on Windows")
            return False
        import subprocess
        try:
            subprocess.Popen(
                ["shutdown", "/r", "/t", "10"],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            _LOG.info("System restart scheduled in 10 s")
            return True
        except Exception as exc:
            _LOG.error("system_restart failed: %s", exc)
            return False

    def _system_shutdown(self) -> bool:
        """Schedule a Windows system shutdown in 10 seconds via shutdown.exe."""
        if sys.platform != "win32":
            _LOG.warning("system_shutdown only supported on Windows")
            return False
        import subprocess
        try:
            subprocess.Popen(
                ["shutdown", "/s", "/t", "10"],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            _LOG.info("System shutdown scheduled in 10 s")
            return True
        except Exception as exc:
            _LOG.error("system_shutdown failed: %s", exc)
            return False

    async def _fullscreen(self, active: str) -> bool:
        """Toggle fullscreen for the active player."""
        if active == "mpchc":
            # Alt+Enter toggles fullscreen in MPC-HC / MPC-BE
            return await self._mpchc.send_key(_VK_RETURN, alt=True)
        elif active == "kodi":
            return await self._kodi_navigate("fullscreen")
        else:
            # No active player — send F11 to whichever window has focus
            return self._send_f11_to_foreground()

    def _send_f11_to_foreground(self) -> bool:
        """Send F11 to the current foreground window (generic fullscreen toggle)."""
        if sys.platform != "win32":
            return False
        import ctypes
        WM_KEYDOWN = 0x0100
        WM_KEYUP   = 0x0101
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            _LOG.warning("fullscreen: no foreground window found")
            return False
        user32.PostMessageW(hwnd, WM_KEYDOWN, _VK_F11, 0)
        user32.PostMessageW(hwnd, WM_KEYUP,   _VK_F11, 0)
        _LOG.info("F11 sent to foreground window hwnd=%d", hwnd)
        return True

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
            # Signal hub immediately so active_player=none is pushed right away
            # → --play process exits → Kodi returns without waiting for poll timeout
            if self._on_mpchc_stop:
                await self._on_mpchc_stop()
            await self._mpchc.close()
            return True
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
        elif cmd == "seek_relative" and value is not None:
            cur_pos = self._state.state.position  # seconds (float)
            target  = max(0.0, cur_pos + float(value))
            return await self._mpchc.seek(int(target * 1000))
        elif cmd == "volume_up":
            return await self._mpchc.send_command(CMD_VOLUME_UP)
        elif cmd == "volume_down":
            return await self._mpchc.send_command(CMD_VOLUME_DOWN)
        elif cmd == "mute":
            return await self._mpchc.send_command(CMD_MUTE)
        elif cmd == "set_volume" and value is not None:
            return await self._mpchc.set_volume(int(value))
        elif cmd == "audio_track" and value is not None:
            target = int(value)
            cur = self._state.state.current_audio
            total = len(self._state.state.audio_tracks)
            ok = await self._mpchc.set_audio_track(target, cur, total)
            if ok:
                self._state.apply({"current_audio": target})
            return ok
        elif cmd == "subtitle_track" and value is not None:
            target = int(value)
            cur = self._state.state.current_subtitle
            total = len(self._state.state.subtitle_tracks)
            ok = await self._mpchc.set_subtitle_track(target, cur, total)
            if ok:
                self._state.apply({"current_subtitle": target})
            return ok
        elif cmd == "chapter" and value is not None:
            target = int(value)
            cur = self._state.state.current_chapter
            delta = target - cur
            ok = True
            for _ in range(abs(delta)):
                ok = await self._mpchc.send_command(CMD_NEXT_CHAPTER if delta > 0 else CMD_PREV_CHAPTER)
                if not ok:
                    break
            return ok
        elif cmd == "mpchc_next_audio":
            return await self._mpchc.send_command(CMD_NEXT_AUDIO)
        elif cmd == "mpchc_prev_audio":
            return await self._mpchc.send_command(CMD_PREV_AUDIO)
        else:
            _LOG.debug("Unknown MPC-HC cmd: %s", cmd)
            return False

    # ------------------------------------------------------------------
    # MPC-HC navigation / keyboard commands
    # ------------------------------------------------------------------
    async def _handle_mpchc_nav(self, cmd: str) -> bool:
        if cmd in ("navigate_back", "navigate_home"):
            # Back / Home → close MPC-HC (same as stop — signal immediately)
            if self._on_mpchc_stop:
                await self._on_mpchc_stop()
            await self._mpchc.close()
            return True
        elif cmd == "show_info":
            # Info → Ctrl+J
            return await self._mpchc.send_key(_VK_J, ctrl=True)
        elif cmd == "context_menu":
            # Menu → MPC-HC context menu via wm_command 950
            from bridge.mpchc_client import CMD_CONTEXT_MENU
            return await self._mpchc.send_command(CMD_CONTEXT_MENU)
        elif cmd == "navigate_up":
            return await self._mpchc.send_key(_VK_UP)
        elif cmd == "navigate_down":
            return await self._mpchc.send_key(_VK_DOWN)
        elif cmd == "navigate_left":
            return await self._mpchc.send_key(_VK_LEFT)
        elif cmd == "navigate_right":
            return await self._mpchc.send_key(_VK_RIGHT)
        elif cmd == "navigate_select":
            # OK / Enter
            return await self._mpchc.send_key(_VK_RETURN)
        _LOG.debug("Unhandled MPC-HC nav cmd: %s", cmd)
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
        elif cmd == "seek_relative" and value is not None:
            cur_pos = self._state.state.position
            target  = max(0.0, cur_pos + float(value))
            await self._kodi.seek(target)
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
        elif cmd == "chapter" and value is not None:
            target = int(value)
            cur = self._state.state.current_chapter
            delta = target - cur
            for _ in range(abs(delta)):
                if delta > 0:
                    await self._kodi.next_chapter()
                else:
                    await self._kodi.prev_chapter()
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
            "fullscreen": "fullscreen",
        }
        action = action_map.get(cmd)
        if action:
            await self._kodi.navigate(action)
            return True
        return False
