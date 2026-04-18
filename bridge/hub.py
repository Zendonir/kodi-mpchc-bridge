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
import re
import sys
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

# TV-episode filename patterns: S01E02, 1x02, etc.
_RE_EPISODE = re.compile(r"[Ss]\d{1,2}[Ee]\d{1,2}|\d{1,2}x\d{2}", re.ASCII)


def _detect_media_type(filepath: str) -> str:
    """Guess 'movie' or 'episode' from the video file path."""
    import os
    if not filepath:
        return "movie"
    # Check filename first
    name = os.path.basename(filepath)
    if _RE_EPISODE.search(name):
        return "episode"
    # Check immediate parent folder name ("Season 1", "Staffel 2", …)
    parent = os.path.basename(os.path.dirname(filepath)).lower()
    if "season" in parent or "staffel" in parent or "serie" in parent:
        return "episode"
    return "movie"


def _match_track(tracks: list[dict], current_name: str) -> int:
    """
    Match MPC-HC's current track string against parsed MKV track list.
    Returns 0-based index, or -1 for 'No subtitles'.
    """
    if not current_name or not tracks:
        return 0
    cur = current_name.lower()

    # "S: No subtitles" — no active subtitle track
    if "no subtitles" in cur:
        return -1

    # MPC-HC's virtual auto-forced track — match our synthetic "Forced (auto)" entry
    if "forced subtitles" in cur:
        for t in tracks:
            if t.get("label", "").lower() == "forced (auto)":
                return t["pos"]
        return 0

    lang_m = re.search(r'\[([a-z]{3})\]', cur)
    cur_lang = lang_m.group(1) if lang_m else ""
    _CODEC_HINTS = {
        "truehd": "A_TRUEHD", "eac3": "A_EAC3", "e-ac3": "A_EAC3",
        "dts-hd": "A_DTS", "dts": "A_DTS",
        "ac3": "A_AC3", "aac": "A_AAC", "flac": "A_FLAC",
        "mp3": "A_MPEG", "opus": "A_OPUS", "vorbis": "A_VORBIS",
        "vobsub": "S_VOBSUB", "ass": "S_TEXT/ASS",
        "subrip": "S_TEXT/UTF8", "pgs": "S_HDMV/PGS",
    }
    cur_codec = ""
    for hint, codec in _CODEC_HINTS.items():
        if hint in cur:
            cur_codec = codec
            break

    # Whether the MPC-HC name marks this as a forced track
    name_is_forced = "[forced]" in cur

    best_pos, best_score = 0, -1
    for t in tracks:
        score = 0
        if cur_lang and t.get("language", "").lower() == cur_lang:
            score += 10
        if cur_codec and t.get("codec", "").upper().startswith(cur_codec.upper().split("/")[0]):
            score += 5
        if t.get("label") and t["label"].lower() in cur:
            score += 3
        # Forced flag: strongly reward an exact forced/non-forced match,
        # penalise a mismatch so forced tracks don't steal non-forced slots.
        track_is_forced = t.get("forced", False)
        if name_is_forced == track_is_forced:
            score += 8
        else:
            score -= 4
        if score > best_score:
            best_score, best_pos = score, t["pos"]
    return best_pos


def _show_resume_dialog(position_sec: float) -> bool:
    """
    Show a Windows MessageBox asking the user whether to resume or start from
    the beginning.  Returns True = resume, False = start from beginning.

    Runs in a thread-pool executor so it does not block the asyncio event loop.
    Falls back to True (resume) on non-Windows or if the dialog raises.
    """
    if sys.platform != "win32":
        return True
    import ctypes

    h = int(position_sec // 3600)
    m = int((position_sec % 3600) // 60)
    s = int(position_sec % 60)
    time_str = f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"

    msg = (
        f"Möchten Sie den Film fortsetzen?\n\n"
        f"  ▶  Fortsetzen ab {time_str}\n"
        f"  ↩  Von Anfang starten"
    )
    title = "Kodi · MPC-HC Bridge"

    MB_YESNO        = 0x0004
    MB_ICONQUESTION = 0x0020
    MB_TOPMOST      = 0x40000
    MB_SETFOREGROUND = 0x10000
    IDYES = 6

    result = ctypes.windll.user32.MessageBoxW(
        0, msg, title,
        MB_YESNO | MB_ICONQUESTION | MB_TOPMOST | MB_SETFOREGROUND,
    )
    return result == IDYES


class Hub:
    def __init__(self, config: ConfigManager) -> None:
        self._config = config
        self._state = StateManager()
        self._last_filepath: str = ""
        self._mpchc_active = False  # True while MPC-HC has a file loaded
        self._last_audiotrack_name: str = ""
        self._last_subtitletrack_name: str = ""
        # Last known position/duration from MPC-HC polls — used for Kodi sync on stop
        self._mpchc_last_position: float = 0.0
        self._mpchc_last_duration: float = 0.0

        cfg = config.cfg

        self._kodi = KodiClient(
            host=cfg.kodi_host,
            ws_port=cfg.kodi_ws_port,
            http_port=cfg.kodi_port,
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

        self._router = CommandRouter(
            self._state, self._kodi, self._mpchc,
            on_mpchc_stop=self._signal_mpchc_stopped,
            on_toggle_ext_player=self._toggle_external_player,
        )

        self._server = BridgeServer(
            state_manager=self._state,
            router=self._router,
            config_manager=config,
            host=cfg.server_host,
            port=cfg.server_port,
            on_external_play=self.external_play,
            on_player_setup=self.setup_external_player,
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
        # Push initial external_player_enabled so remote UIs get correct state
        await self._push({"external_player_enabled": cfg.external_player_enabled})
        if cfg.external_player_enabled:
            if cfg.mpchc_exe_path:
                _LOG.info("External player: exe=%r  resume=%s", cfg.mpchc_exe_path, cfg.resume_enabled)
            else:
                _LOG.warning(
                    "External player NOT configured (mpchc_exe_path is empty). "
                    "Open the Bridge web UI at http://localhost:%d and use "
                    "'External Player Setup' to configure it.",
                    cfg.server_port,
                )
        else:
            _LOG.info("External player DISABLED — Kodi will handle playback itself")

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
            _filepath = updates.get("filepath", "")
            updates["media_type"] = _detect_media_type(_filepath)
            # Clear stale video / metadata from any previous player so the
            # remote doesn't show leftover Kodi HDR / year / show data while
            # MKV parsing + library lookup run in the background.
            for _k in ("hdr", "video_codec"):
                updates.setdefault(_k, "")
            for _k in ("video_width", "video_height", "video_bitrate_kbps"):
                updates.setdefault(_k, 0)
            updates.setdefault("video_fps", 0.0)
            for _k in ("year", "season", "episode"):
                updates.setdefault(_k, 0)
            updates.setdefault("tv_show", "")
            _LOG.info("ACTIVE PLAYER → mpchc  (file: %s, type: %s)",
                      _filepath, updates["media_type"])
        elif new_active == "none" and self._mpchc_active:
            self._mpchc_active = False
            self._server.clear_artwork()
            updates["artwork_url"] = ""   # clear artwork on remote immediately
            updates["media_type"] = ""    # clear type so Kodi can set its own
            # Clear video info so Kodi's own stream details take over cleanly
            updates.setdefault("hdr", "")
            updates.setdefault("video_codec", "")
            updates.setdefault("video_fps", 0.0)
            _LOG.info("ACTIVE PLAYER → none   (mpchc idle, kodi may take over)")
            # Sync playback state to Kodi library in the background
            _fp  = self._last_filepath
            _pos = self._mpchc_last_position
            _dur = self._mpchc_last_duration
            if _fp:
                _sync_task = asyncio.get_running_loop().create_task(
                    self._sync_to_kodi(_fp, _pos, _dur)
                )
                _sync_task.add_done_callback(
                    lambda t: _LOG.warning("Kodi sync task raised: %s", t.exception())
                    if not t.cancelled() and t.exception() else None
                )

        # Track position and duration from every MPC-HC poll (used for Kodi sync on stop).
        # Only update when the value is non-zero: MPC-HC reports position=0 when it
        # transitions to idle/stopped, which would overwrite the last playing position
        # and cause the wrong resume point / watched-state to be synced to Kodi.
        if updates.get("position", 0) > 0:
            self._mpchc_last_position = updates["position"]
        if updates.get("duration", 0) > 0:
            self._mpchc_last_duration = updates["duration"]

        # Capture raw track names before they are consumed
        audiotrack_name = updates.pop("audiotrack_name", None)
        subtitletrack_name = updates.pop("subtitletrack_name", None)
        if audiotrack_name is not None:
            self._last_audiotrack_name = audiotrack_name
        if subtitletrack_name is not None:
            self._last_subtitletrack_name = subtitletrack_name

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
                # Resolve active track names against freshly parsed track lists
                if self._last_audiotrack_name:
                    idx = _match_track(mkv_updates.get("audio_tracks", []), self._last_audiotrack_name)
                    updates["current_audio"] = idx
                    _LOG.info("MPC-HC initial audio track: %r → %d", self._last_audiotrack_name, idx)
                if self._last_subtitletrack_name:
                    idx = _match_track(mkv_updates.get("subtitle_tracks", []), self._last_subtitletrack_name)
                    updates["current_subtitle"] = idx
                    _LOG.info("MPC-HC initial subtitle track: %r → %d", self._last_subtitletrack_name, idx)

            # Fetch cover art from Kodi library in background (avoids blocking state push)
            task = asyncio.get_running_loop().create_task(self._fetch_artwork(new_filepath))
            task.add_done_callback(
                lambda t: _LOG.warning("Artwork task raised: %s", t.exception())
                if not t.cancelled() and t.exception() else None
            )

        # Resolve track name changes on subsequent polls (ongoing resync)
        if audiotrack_name is not None and "current_audio" not in updates:
            audio_tracks = self._state.state.audio_tracks
            if audio_tracks:
                idx = _match_track(audio_tracks, audiotrack_name)
                updates["current_audio"] = idx
                _LOG.debug("MPC-HC audiotrack resync: %r → %d", audiotrack_name, idx)
        if subtitletrack_name is not None and "current_subtitle" not in updates:
            sub_tracks = self._state.state.subtitle_tracks
            if sub_tracks:
                idx = _match_track(sub_tracks, subtitletrack_name) if subtitletrack_name else -1
                updates["current_subtitle"] = idx
                _LOG.info("SUB resync: MPC-HC reports %r → resolved to index %d", subtitletrack_name, idx)

        # Log significant state changes
        if "state" in updates:
            _LOG.info("MPCHC state: %s  pos=%.1fs", updates["state"], updates.get("position", 0))

        await self._push(updates)

    async def _fetch_artwork(self, filepath: str) -> None:
        """
        Background task: fetch artwork AND library metadata, then push to state.

        Order of preference for artwork:
        1. Kodi library (get_file_info — also returns title/year/show/season/episode)
        2. Local poster file next to the video (poster.jpg, folder.jpg, …)
        """
        try:
            data: bytes | None = None
            ct = "image/jpeg"

            # Kodi library lookup — returns artwork URL + metadata
            info = await self._kodi.get_file_info(filepath)
            if info:
                # Push metadata immediately (year, tv_show, season, episode, title)
                meta_patch = {
                    k: v for k, v in info.items()
                    if k != "artwork_url" and v not in ("", 0)
                }
                if meta_patch:
                    _LOG.info("FileInfo metadata: %s", meta_patch)
                    await self._push(meta_patch)

                kodi_url = info.get("artwork_url", "")
                if kodi_url:
                    data, ct = await self._kodi.fetch_image_bytes(kodi_url)

            if not data:
                # Filesystem fallback: look for poster/folder images in same dir
                result = await asyncio.get_running_loop().run_in_executor(
                    None, self._load_local_poster, filepath
                )
                if result:
                    data, ct = result

            if data:
                self._server.set_artwork(data, ct)
                bridge_url = f"{self._bridge_base_url()}/api/artwork"
                _LOG.info("Artwork stored at %s (%d bytes)", bridge_url, len(data))
                await self._push({"artwork_url": bridge_url})
            else:
                _LOG.info("No artwork found for %r", filepath)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            _LOG.warning("Artwork/metadata fetch failed for %r: %s", filepath, exc)

    @staticmethod
    def _load_local_poster(filepath: str) -> tuple[bytes, str] | None:
        """
        Look for a poster/cover image file in the same folder as *filepath*.
        Common naming conventions for Kodi/Plex/Jellyfin are tried in order.
        Returns (bytes, content_type) or None.
        """
        import os
        folder = os.path.dirname(filepath)
        if not folder or not os.path.isdir(folder):
            return None
        base = os.path.splitext(os.path.basename(filepath))[0]
        _EXT_CT = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
        candidates = [
            "poster.jpg", "poster.jpeg", "poster.png",
            "folder.jpg", "folder.png",
            "cover.jpg",  "cover.png",
            f"{base}.jpg", f"{base}.jpeg", f"{base}.png",
            f"{base}-poster.jpg", f"{base}-poster.png",
        ]
        for name in candidates:
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                ext = os.path.splitext(name)[1].lower()
                ct = _EXT_CT.get(ext, "image/jpeg")
                try:
                    with open(path, "rb") as fh:
                        data = fh.read()
                    _LOG.info("Local poster: %s (%d bytes)", path, len(data))
                    return data, ct
                except Exception as exc:
                    _LOG.warning("Cannot read local poster %s: %s", path, exc)
        return None

    def _bridge_base_url(self) -> str:
        import socket
        host = self._config.cfg.server_host
        if host in ("0.0.0.0", ""):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                host = s.getsockname()[0]
                s.close()
            except Exception:
                host = "127.0.0.1"
        return f"http://{host}:{self._config.cfg.server_port}"

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
    # MPC Proxy integration
    # ------------------------------------------------------------------
    @staticmethod
    def _proxy_xml_path() -> str:
        """Return the full path to Kodi's playercorefactory.xml."""
        import os
        return os.path.join(
            os.environ.get("APPDATA", ""),
            "Kodi", "userdata", "playercorefactory.xml",
        )

    @staticmethod
    def proxy_status() -> str:
        """
        Check whether MPC Proxy is currently active in Kodi's
        ``playercorefactory.xml``.

        Returns ``"active"`` if the file exists and references MPC Proxy,
        ``"inactive"`` otherwise (file missing, empty, or different player).
        """
        import os
        xml_path = Hub._proxy_xml_path()
        if not os.path.exists(xml_path):
            return "inactive"
        try:
            with open(xml_path, "r", encoding="utf-8", errors="replace") as fh:
                return "active" if "MPC Proxy" in fh.read() else "inactive"
        except Exception:
            return "inactive"

    @staticmethod
    def setup_proxy(proxy_path: str) -> tuple[bool, str]:
        """
        Write *playercorefactory.xml* to Kodi's userdata folder so that
        MPC Proxy is used as the external player for all video files.

        If a ``playercorefactory.xml`` already exists and no ``.bak`` backup
        has been taken yet, a backup is created first so the original can be
        restored later via :meth:`disable_proxy`.

        Returns ``(True, xml_path)`` on success or ``(False, error_msg)`` on failure.
        """
        import os
        import shutil
        import xml.sax.saxutils as _saxutils

        appdata = os.environ.get("APPDATA", "")
        if not appdata:
            return False, "APPDATA environment variable not set"

        userdata = os.path.join(appdata, "Kodi", "userdata")
        try:
            os.makedirs(userdata, exist_ok=True)
        except OSError as exc:
            return False, f"Cannot create Kodi userdata dir: {exc}"

        xml_path = os.path.join(userdata, "playercorefactory.xml")
        bak_path = xml_path + ".bak"

        # Back up the existing file exactly once (don't overwrite an earlier backup)
        if os.path.exists(xml_path) and not os.path.exists(bak_path):
            try:
                shutil.copy2(xml_path, bak_path)
                _LOG.info("MPC Proxy setup: backed up original → %s", bak_path)
            except OSError as exc:
                _LOG.warning("MPC Proxy setup: backup skipped — %s", exc)

        proxy_esc = _saxutils.escape(proxy_path, {'"': "&quot;"})
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<playercorefactory>\n'
            '  <players>\n'
            '    <player name="MPC Proxy" type="ExternalPlayer" audio="false" video="true">\n'
            f'      <filename>{proxy_esc}</filename>\n'
            '      <args>"{filepath}"</args>\n'
            '      <hidexbmc>false</hidexbmc>\n'
            '      <hideconsole>true</hideconsole>\n'
            '    </player>\n'
            '  </players>\n'
            '  <rules action="prepend">\n'
            '    <rule video="true" player="MPC Proxy"/>\n'
            '  </rules>\n'
            '</playercorefactory>\n'
        )
        try:
            with open(xml_path, "w", encoding="utf-8") as fh:
                fh.write(xml)
            _LOG.info("MPC Proxy setup: wrote %s", xml_path)
            return True, xml_path
        except OSError as exc:
            _LOG.error("MPC Proxy setup failed: %s", exc)
            return False, str(exc)

    @staticmethod
    def disable_proxy() -> tuple[bool, str]:
        """
        Deactivate MPC Proxy as Kodi's external player.

        * If a ``.bak`` backup exists → restore it (the user's original config).
        * Otherwise → delete ``playercorefactory.xml`` entirely.

        Returns ``(True, detail_msg)`` on success or ``(False, error_msg)`` on failure.
        ``detail_msg`` is one of ``"restored"``, ``"removed"``, or ``"already_inactive"``.
        """
        import os
        import shutil

        xml_path = Hub._proxy_xml_path()
        bak_path = xml_path + ".bak"

        if os.path.exists(bak_path):
            try:
                shutil.copy2(bak_path, xml_path)
                _LOG.info("MPC Proxy disabled: original config restored from %s", bak_path)
                return True, "restored"
            except OSError as exc:
                _LOG.error("MPC Proxy disable (restore) failed: %s", exc)
                return False, str(exc)

        if os.path.exists(xml_path):
            try:
                os.remove(xml_path)
                _LOG.info("MPC Proxy disabled: removed %s (no backup existed)", xml_path)
                return True, "removed"
            except OSError as exc:
                _LOG.error("MPC Proxy disable (remove) failed: %s", exc)
                return False, str(exc)

        return True, "already_inactive"

    # ------------------------------------------------------------------
    # Toggle external player on / off
    # ------------------------------------------------------------------
    async def _toggle_external_player(self) -> bool:
        """Flip external_player_enabled in config and broadcast to all clients."""
        new_val = not self._config.cfg.external_player_enabled
        self._config.update({"external_player_enabled": new_val})
        _LOG.info("External player %s via remote command", "ENABLED" if new_val else "DISABLED")
        await self._push({"external_player_enabled": new_val})
        return True

    # ------------------------------------------------------------------
    # Immediate MPC-HC stop signal (called by router on explicit stop/back)
    # ------------------------------------------------------------------
    async def _signal_mpchc_stopped(self) -> None:
        """
        Called by the CommandRouter when the user explicitly stops MPC-HC via
        the bridge (stop button, back/home nav).

        Immediately pushes active_player=none so the --play process can exit
        right away and Kodi returns to its UI without waiting for the next
        MPC-HC poll cycle.
        """
        if not self._mpchc_active:
            return
        _LOG.info("Explicit stop — immediately signalling active_player=none")
        # Re-use the full transition logic in _on_mpchc_update
        await self._on_mpchc_update({"active_player": "none", "state": "idle"})

    # ------------------------------------------------------------------
    # External player — setup (writes playercorefactory.xml + config)
    # ------------------------------------------------------------------
    def setup_external_player(
        self, mpchc_exe: str, resume_enabled: bool
    ) -> tuple[bool, str]:
        """
        1. Persist mpchc_exe_path + resume_enabled to config.json.
        2. Write %APPDATA%\\Kodi\\userdata\\playercorefactory.xml so that
           Kodi calls ``kodi-bridge.exe --play "{filepath}"`` as external player.

        Returns (True, xml_path) on success, (False, error_msg) on failure.
        """
        import os
        import shutil
        import sys
        import xml.sax.saxutils as _sx

        # 1. Update config ────────────────────────────────────────────────────
        self._config.update({
            "mpchc_exe_path": mpchc_exe,
            "resume_enabled": resume_enabled,
        })
        _LOG.info("Config updated: mpchc_exe_path=%r, resume_enabled=%s",
                  mpchc_exe, resume_enabled)

        # 2. Determine this exe's path ─────────────────────────────────────────
        if getattr(sys, "frozen", False):
            bridge_exe = sys.executable  # kodi-bridge.exe in frozen mode
        else:
            # Dev / source mode — derive from config file location
            bridge_exe = os.path.join(
                os.path.dirname(self._config._path), "kodi-bridge.exe"
            )

        # 3. Write playercorefactory.xml ──────────────────────────────────────
        appdata = os.environ.get("APPDATA", "")
        if not appdata:
            return False, "APPDATA environment variable not set"
        userdata = os.path.join(appdata, "Kodi", "userdata")
        try:
            os.makedirs(userdata, exist_ok=True)
        except OSError as exc:
            return False, f"Cannot create Kodi userdata dir: {exc}"

        xml_path = os.path.join(userdata, "playercorefactory.xml")
        bak_path = xml_path + ".bak"
        if os.path.exists(xml_path) and not os.path.exists(bak_path):
            try:
                shutil.copy2(xml_path, bak_path)
                _LOG.info("Backed up original playercorefactory.xml → %s", bak_path)
            except OSError:
                pass  # non-fatal

        exe_esc = _sx.escape(bridge_exe, {'"': "&quot;"})
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<playercorefactory>\n'
            '  <players>\n'
            '    <player name="Kodi-MPC-HC Bridge"'
            ' type="ExternalPlayer" audio="false" video="true">\n'
            f'      <filename>{exe_esc}</filename>\n'
            '      <args>--play "{1}"</args>\n'
            '      <hidexbmc>true</hidexbmc>\n'
            '      <hideconsole>true</hideconsole>\n'
            '    </player>\n'
            '  </players>\n'
            '  <rules action="prepend">\n'
            '    <rule video="true" audio="false" player="Kodi-MPC-HC Bridge"/>\n'
            '  </rules>\n'
            '</playercorefactory>\n'
        )
        try:
            with open(xml_path, "w", encoding="utf-8") as fh:
                fh.write(xml)
            _LOG.info("playercorefactory.xml written → %s", xml_path)
            return True, xml_path
        except OSError as exc:
            _LOG.error("Cannot write playercorefactory.xml: %s", exc)
            return False, str(exc)

    # ------------------------------------------------------------------
    # External player / built-in resume
    # ------------------------------------------------------------------
    async def external_play(self, filepath: str) -> None:
        """
        Called when ``kodi-bridge.exe --play <filepath>`` POSTs to
        ``/api/external_play``.

        Sequence
        --------
        1. (Optional) Read Kodi's resume position for the file.
        2. Launch MPC-HC with the file path.
        3. Poll MPC-HC's HTTP API until it responds (max 15 s, 0.5 s intervals).
        4. After a 1 s settling pause, seek to the resume position.
        """
        import subprocess
        import sys

        cfg = self._config.cfg
        mpc_exe = (cfg.mpchc_exe_path or "").strip()
        if not mpc_exe:
            _LOG.error("external_play: mpchc_exe_path not configured — cannot launch player")
            return

        # 1. Resume position ──────────────────────────────────────────────────
        resume_pos: float = 0.0
        if cfg.resume_enabled:
            try:
                resume_pos = await self._kodi.get_resume_position(filepath)
                _LOG.info(
                    "external_play: Kodi resume position = %.1f s for %r",
                    resume_pos, filepath,
                )
            except Exception as exc:
                _LOG.warning("external_play: could not read resume position: %s", exc)

        # 1b. Resume dialog — ask user to continue or start from beginning.
        #     Only shown when there is a meaningful resume point (>60 s), so
        #     new films (resume=0) and finished films (resume=0) skip the dialog.
        if resume_pos >= 60.0:
            try:
                should_resume = await asyncio.get_running_loop().run_in_executor(
                    None, _show_resume_dialog, resume_pos
                )
                if not should_resume:
                    _LOG.info("external_play: user chose 'play from beginning'")
                    resume_pos = 0.0
                else:
                    _LOG.info("external_play: user chose 'resume'")
            except Exception as exc:
                _LOG.warning("external_play: resume dialog failed: %s — defaulting to resume", exc)

        # 2. Launch MPC-HC ────────────────────────────────────────────────────
        try:
            kwargs: dict = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            subprocess.Popen([mpc_exe, filepath], **kwargs)
            _LOG.info("external_play: launched %r with %r", mpc_exe, filepath)
        except Exception as exc:
            _LOG.error("external_play: launch failed: %s", exc)
            return

        if resume_pos <= 0.0:
            return  # nothing to seek to

        # 3. Poll until MPC-HC HTTP API is ready (max 15 s) ──────────────────
        import aiohttp as _aiohttp

        mpc_url = f"http://{cfg.mpchc_host}:{cfg.mpchc_port}/variables.html"
        deadline = asyncio.get_running_loop().time() + 15.0
        ready = False
        try:
            async with _aiohttp.ClientSession(
                timeout=_aiohttp.ClientTimeout(total=1.5)
            ) as sess:
                while asyncio.get_running_loop().time() < deadline:
                    try:
                        async with sess.get(mpc_url) as resp:
                            if resp.status == 200:
                                ready = True
                                break
                    except Exception:
                        pass
                    await asyncio.sleep(0.5)
        except Exception as exc:
            _LOG.warning("external_play: poll session error: %s", exc)

        if not ready:
            _LOG.warning("external_play: MPC-HC did not respond within 15 s — seek skipped")
            return

        # 4. Settle then seek ─────────────────────────────────────────────────
        await asyncio.sleep(1.0)
        seek_ms = int(resume_pos * 1000)
        _LOG.info("external_play: seeking to %d ms (%.1f s)", seek_ms, resume_pos)
        await self._mpchc.seek(seek_ms)

    async def _sync_to_kodi(
        self, filepath: str, position: float, duration: float
    ) -> None:
        """
        Sync MPC-HC playback end state to Kodi's video library.

        Decision logic
        --------------
        * position ≥ 90 % of duration  →  mark watched
          (playcount = 1, lastplayed = now, resume cleared)
        * position ≥ 60 s              →  save resume point
        * otherwise                    →  reset playcount only

        Kodi auto-marks any file as watched when an external player process
        exits (Player.OnStop).  We must always reset playcount to 0 when the
        film was NOT actually finished, otherwise the library incorrectly shows
        it as seen.  A short sleep is inserted so that our write arrives
        *after* Kodi's auto-mark (the --play process exits ≤1 s after we push
        active_player=none, and Kodi fires OnStop shortly after).
        """
        if not filepath:
            return

        _WATCH_THRESHOLD = 0.90   # fraction of duration considered "done"
        _MIN_RESUME_SECS = 60.0   # don't save resume for <1 min watched
        _AUTO_MARK_WAIT  = 2.0    # seconds to wait for Kodi's auto-mark to land

        try:
            found = await self._kodi.find_library_item(filepath)
        except Exception as exc:
            _LOG.warning("kodi sync: library lookup failed for %r: %s", filepath, exc)
            return

        if found is None:
            _LOG.info("kodi sync: %r not in Kodi library — nothing to update", filepath)
            return

        media_type, item = found
        media_id: int = item.get("movieid") or item.get("episodeid") or 0
        if not media_id:
            _LOG.warning("kodi sync: could not determine media id for %r", filepath)
            return

        # Wait for Kodi to complete its external-player-exit processing before
        # writing our state (Kodi fires Player.OnStop and may auto-mark as
        # watched when the --play process exits, ≈1 s after stop signal).
        await asyncio.sleep(_AUTO_MARK_WAIT)

        if duration > 0 and position >= duration * _WATCH_THRESHOLD:
            # Truly finished — mark watched (our intent matches Kodi's auto-mark).
            _LOG.info(
                "kodi sync: position %.1f s / %.1f s (%.0f %%) → marking watched"
                "  [%s id=%d]",
                position, duration, 100 * position / duration,
                media_type, media_id,
            )
            await self._kodi.set_watched(media_type, media_id)

        elif position >= _MIN_RESUME_SECS:
            # Not finished — atomic write: reset playcount=0 AND set resume in
            # one call so no Kodi write can slip between them and zero the resume.
            _LOG.info(
                "kodi sync: position %.1f s / %.1f s → saving resume + reset watched"
                "  [%s id=%d]",
                position, duration, media_type, media_id,
            )
            await self._kodi.set_resume_and_reset_watched(
                media_type, media_id, position, duration
            )

        else:
            # Too short to save a resume point — just reset the auto-watched mark.
            _LOG.debug(
                "kodi sync: position %.1f s is too short to save"
                " — playcount reset only  [%s id=%d]",
                position, media_type, media_id,
            )
            await self._kodi.reset_watched(media_type, media_id)

        # Notify Kodi to refresh its library UI immediately (progress bar,
        # watched checkmark) without waiting for the user to navigate away.
        await self._kodi.notify_library_update(media_type, media_id)

    # ------------------------------------------------------------------
    # MKV parser (blocking, runs in thread pool)
    # ------------------------------------------------------------------
    def _parse_mkv_sync(self, filepath: str) -> dict[str, Any]:
        try:
            tracks = parse_mkv(filepath)
            audio, subs, chapters, video_info = tracks_to_dicts(tracks)
            result: dict[str, Any] = {}
            if audio:
                result["audio_tracks"] = audio
            if subs:
                result["subtitle_tracks"] = subs
            if chapters:
                result["chapters"] = chapters
            # Always push video info (even zeros clear stale values)
            result.update(video_info)
            v = tracks.video
            _LOG.info(
                "MKV parsed: %d audio, %d subs, %d chapters, "
                "video=%dx%d %.3ffps %s bitrate=%dkbps from %s",
                len(audio), len(subs), len(chapters),
                v.width, v.height, v.fps, v.hdr or "SDR",
                v.bitrate_kbps, filepath,
            )
            return result
        except Exception as exc:
            _LOG.warning("MKV parse error for %s: %s", filepath, exc)
            return {}
