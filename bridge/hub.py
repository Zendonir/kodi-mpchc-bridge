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


def _smb_to_unc(path: str) -> str:
    """
    Convert ``smb://host/share/path`` to ``\\\\host\\share\\path``.
    Already-UNC and local paths are returned unchanged.
    Needed because Kodi stores library file paths as smb:// URLs but
    MPC-HC only understands Windows UNC paths.
    """
    if path.startswith("smb://"):
        return "\\\\" + path[6:].replace("/", "\\")
    return path


def _norm_path(path: str) -> str:
    """
    Normalise a file path for equality comparison across smb:// and UNC forms.

    Both ``smb://HOST/share/ep.mkv`` and ``\\\\HOST\\share\\ep.mkv`` become
    ``//host/share/ep.mkv`` so they compare equal regardless of origin.
    """
    p = path
    if p.startswith("smb://"):
        p = "//" + p[6:]
    return p.replace("\\", "/").lower()


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


def _show_resume_dialog(
    position_sec: float,
    on_ready: "Any | None" = None,
    on_done:  "Any | None" = None,
) -> "bool | None":
    """
    Show a full-screen dark overlay asking the user to resume or restart.

    Returns:
      True   — resume from saved position ("Ja")
      False  — play from beginning ("Nein")
      None   — cancelled (stop/back pressed → do not launch MPC-HC at all)

    Keyboard navigation (physical keyboard):
      ← / →  /  Tab     — switch between Ja and Nein
      Enter / Space      — confirm focused button
      Esc / Backspace    — choose Nein (start from beginning)

    Remote / bridge navigation (via on_ready callback):
      Left / Right       — switch buttons
      Return             — confirm focused button
      Cancel             — abort dialog, don't launch player

    on_ready(inject_fn) is called once the dialog is ready; the bridge router
    stores inject_fn and uses it to forward remote key commands into the dialog.
    on_done() is called when the dialog closes.

    Runs in a thread-pool executor (blocking), so it never blocks the asyncio
    event loop.  Falls back to True (resume) if tkinter is unavailable.
    """
    if sys.platform != "win32":
        return True

    try:
        import tkinter as tk
    except ImportError:
        _LOG.warning("_show_resume_dialog: tkinter not available — defaulting to resume")
        return True

    h = int(position_sec // 3600)
    m = int((position_sec % 3600) // 60)
    s = int(position_sec % 60)
    time_str = f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"

    result  = [True]   # default: resume
    focused = [0]      # 0 = Ja,  1 = Nein

    root = tk.Tk()
    root.title("Kodi · MPC-HC Bridge")
    root.attributes("-fullscreen", True)
    root.attributes("-topmost", True)
    root.overrideredirect(True)   # remove OS title bar for clean overlay
    root.configure(bg="#111111")

    def _choose(val: "bool | None") -> None:
        result[0] = val
        root.quit()

    # ── Button wrapper frames act as focus-indicator borders ─────────────────
    # frame bg="#ffffff" = focused (white border)  /  bg="#111111" = unfocused
    frame_yes: "tk.Frame"
    frame_no:  "tk.Frame"

    def _set_focus(idx: int) -> None:
        """Move keyboard focus to button 0 (Ja) or 1 (Nein) and redraw borders."""
        focused[0] = idx
        frame_yes.config(bg="#ffffff" if idx == 0 else "#111111")
        frame_no.config( bg="#ffffff" if idx == 1 else "#111111")

    def _on_key_sym(ks: str) -> None:
        """Handle a key by name (keysym).  Called both from tkinter events and
        from the remote-inject path (router → inject_fn → root.after)."""
        if ks in ("Right", "Tab"):
            _set_focus(1)
        elif ks == "Left":
            _set_focus(0)
        elif ks in ("Return", "KP_Enter", "space"):
            _choose(focused[0] == 0)   # confirm whichever button is active
        elif ks in ("Escape", "BackSpace"):
            _choose(False)             # Nein — play from beginning
        elif ks == "Cancel":
            _choose(None)              # abort — don't launch player at all

    def _on_key(event) -> str:
        _on_key_sym(event.keysym)
        return "break"  # prevent tkinter's own Tab / arrow handling

    root.bind("<Key>", _on_key)

    # ── Center frame ─────────────────────────────────────────────────────────
    center = tk.Frame(root, bg="#111111")
    center.place(relx=0.5, rely=0.44, anchor="center")

    tk.Label(
        center,
        text="Film fortsetzen?",
        font=("Segoe UI", 40, "bold"),
        fg="#ffffff", bg="#111111",
    ).pack(pady=(0, 14))

    tk.Label(
        center,
        text=f"Zuletzt gesehen bis  {time_str}",
        font=("Segoe UI", 20),
        fg="#888888", bg="#111111",
    ).pack(pady=(0, 56))

    btn_row = tk.Frame(center, bg="#111111")
    btn_row.pack()

    # Ja — pre-selected, white border
    frame_yes = tk.Frame(btn_row, bg="#ffffff", padx=4, pady=4)
    frame_yes.grid(row=0, column=0, padx=28)
    btn_yes = tk.Button(
        frame_yes,
        text="Ja",
        font=("Segoe UI", 24, "bold"),
        bg="#1c6e2e", fg="#ffffff",
        activebackground="#27963e", activeforeground="#ffffff",
        relief="flat", bd=0,
        width=12, pady=22,
        cursor="hand2",
        command=lambda: _choose(True),
    )
    btn_yes.pack()

    # Nein — no border initially
    frame_no = tk.Frame(btn_row, bg="#111111", padx=4, pady=4)
    frame_no.grid(row=0, column=1, padx=28)
    btn_no = tk.Button(
        frame_no,
        text="Nein",
        font=("Segoe UI", 24),
        bg="#2d2d2d", fg="#cccccc",
        activebackground="#3d3d3d", activeforeground="#ffffff",
        relief="flat", bd=0,
        width=12, pady=22,
        cursor="hand2",
        command=lambda: _choose(False),
    )
    btn_no.pack()

    # ── Keyboard hint ────────────────────────────────────────────────────────
    tk.Label(
        root,
        text="\u2190 \u2192 Auswahl   \u00B7   Enter = Best\u00E4tigen   \u00B7   Esc = Nein",
        font=("Segoe UI", 13),
        fg="#3a3a3a", bg="#111111",
    ).place(relx=0.5, rely=0.91, anchor="center")

    # ── Remote-control bridge: allow the router to inject key events ────────
    def _inject_key(keysym: str) -> None:
        """Thread-safe: schedule a key-sym into this dialog's tkinter loop."""
        try:
            root.after(0, lambda: _on_key_sym(keysym))
        except Exception:
            pass

    if on_ready is not None:
        # Called from this thread (thread-pool executor) — the router simply
        # stores the function reference; Python GIL makes the assignment safe.
        on_ready(_inject_key)

    # Give keyboard focus to the root window so all key events are caught
    root.focus_force()
    root.update()
    root.mainloop()

    if on_done is not None:
        on_done()

    try:
        root.destroy()
    except Exception:
        pass

    return result[0]


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
        # Auto-next: True after we have triggered the next episode so we don't
        # trigger twice for the same file.  Reset whenever the filepath changes.
        self._autonext_triggered: bool = False

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
            on_play_episode=self._play_episode_cmd,
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
            # NOTE: season_episodes / playlist_index are intentionally NOT cleared
            # here.  MPC-HC briefly reports state=0 during file transitions (when
            # the user switches to a different episode in the web UI), which also
            # fires active_player→none.  Clearing the list here would make it
            # disappear on every episode switch.  The list is cleared in two
            # places instead:
            #   • _signal_mpchc_stopped() — explicit Stop / Back from the remote
            #   • _on_kodi_update()       — when Kodi regains the active player
            #     role after the last episode ends naturally
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

        # ── Auto-advance to next episode when ≤ 5 s remain ───────────────────
        _pos = self._mpchc_last_position
        _dur = self._mpchc_last_duration
        if (
            self._mpchc_active
            and not self._autonext_triggered
            and _dur > 30.0          # ignore loading / very short clips
            and _pos > 0.0
            and (_dur - _pos) <= 5.0
        ):
            _eps = self._state.state.season_episodes
            _idx = self._state.state.playlist_index
            if _eps and 0 <= _idx < len(_eps) - 1:
                _next_file = _eps[_idx + 1].get("file", "")
                if _next_file:
                    self._autonext_triggered = True
                    _LOG.info(
                        "Auto-next: %.1f s remaining → episode %d → %d  (%s)",
                        _dur - _pos, _idx, _idx + 1, _next_file,
                    )
                    asyncio.create_task(
                        self.external_play(_next_file, no_dialog=True)
                    )

        # Capture raw track names before they are consumed
        audiotrack_name = updates.pop("audiotrack_name", None)
        subtitletrack_name = updates.pop("subtitletrack_name", None)
        if audiotrack_name is not None:
            self._last_audiotrack_name = audiotrack_name
        if subtitletrack_name is not None:
            self._last_subtitletrack_name = subtitletrack_name

        # Video info / track parsing on filepath change.
        # MKV → full EBML parse (tracks, chapters, video info) + ffprobe HDR fallback.
        # Other video containers → ffprobe HDR only (EBML returns empty gracefully).
        _VIDEO_EXTS = frozenset({
            ".mkv", ".mp4", ".m4v", ".mov", ".avi",
            ".ts", ".m2ts", ".mpg", ".mpeg", ".wmv",
        })
        new_filepath = updates.get("filepath")
        if new_filepath is not None and new_filepath != self._last_filepath:
            self._last_filepath = new_filepath
            self._autonext_triggered = False  # reset for each new file
            _LOG.info("MPC-HC filepath: %s", new_filepath)
            import os as _os
            _fp_ext = _os.path.splitext(new_filepath.lower())[1] if new_filepath else ""
            if new_filepath and _fp_ext in _VIDEO_EXTS:
                if _fp_ext == ".mkv":
                    _LOG.info("Parsing MKV tracks + video info…")
                else:
                    _LOG.info("Probing video info via ffprobe (%s)…", _fp_ext)
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

            # Immediately update playlist_index if the new file is already in the
            # season episode list that's currently displayed.  This gives instant
            # visual feedback on episode switches without waiting for _fetch_artwork
            # to complete (which requires multiple async Kodi API round-trips).
            if new_filepath:
                existing_eps = self._state.state.season_episodes
                if existing_eps:
                    cur_norm = _norm_path(new_filepath)
                    quick_idx = next(
                        (i for i, ep in enumerate(existing_eps)
                         if _norm_path(ep.get("file", "")) == cur_norm),
                        None,
                    )
                    if quick_idx is not None:
                        updates["playlist_index"] = quick_idx
                        _LOG.info(
                            "playlist_index quick-update: %r → index %d",
                            new_filepath, quick_idx,
                        )

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

        Also fetches the full season episode list when an episode is detected,
        storing it in state so the web UI can display it.
        """
        try:
            data: bytes | None = None
            ct = "image/jpeg"

            # Kodi library lookup — returns artwork URL + metadata
            info = await self._kodi.get_file_info(
                filepath,
                episode_art_mode=self._config.cfg.episode_art_mode,
            )
            if info:
                # Extract tvshowid before pushing (not a UnifiedState field)
                tvshowid: int = info.pop("tvshowid", -1)

                # Push metadata immediately (year, tv_show, season, episode, title)
                meta_patch = {
                    k: v for k, v in info.items()
                    if k != "artwork_url" and v not in ("", 0)
                }
                if meta_patch:
                    _LOG.info("FileInfo metadata: %s", meta_patch)
                    await self._push(meta_patch)

                # Season episode list — fetch when it's a TV episode
                cur_season = info.get("season", 0)
                if tvshowid >= 0 and cur_season > 0:
                    try:
                        eps = await self._kodi.get_season_episodes(tvshowid, cur_season)
                        if eps:
                            cur_norm = _norm_path(filepath)
                            idx = next(
                                (i for i, e in enumerate(eps)
                                 if _norm_path(e.get("file", "")) == cur_norm),
                                -1,
                            )
                            await self._push({"season_episodes": eps, "playlist_index": idx})
                            _LOG.info(
                                "Season S%02d: %d episodes fetched, current index=%d",
                                cur_season, len(eps), idx,
                            )
                    except Exception as exc:
                        _LOG.warning("Season episode fetch failed: %s", exc)

                kodi_url = info.get("artwork_url", "")
                if kodi_url:
                    _art = await self._kodi.fetch_artwork_bytes(kodi_url)
                    if _art:
                        data, ct = _art

                # Fallback: if artwork still not found but we know the tvshowid,
                # fetch the show poster directly from Kodi + Textures cache.
                # This covers the common case where per-episode art lookup fails
                # but the show poster is already cached locally.
                if not data and tvshowid >= 0:
                    try:
                        show_url = await self._kodi.get_tvshow_art(tvshowid)
                        if show_url:
                            _art2 = await self._kodi.fetch_artwork_bytes(show_url)
                            if _art2:
                                data, ct = _art2
                                _LOG.info("Artwork from show poster (tvshowid=%d)", tvshowid)
                    except Exception as exc:
                        _LOG.debug("Show poster fallback failed: %s", exc)

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
            # Kodi is taking over as active player — clear any leftover season
            # episode list from MPC-HC.  This covers the case where the last
            # episode ends naturally (MPC-HC goes idle, no explicit Stop pressed)
            # so the season card doesn't linger on-screen after Kodi resumes.
            updates.setdefault("season_episodes", [])
            updates.setdefault("playlist_index", -1)
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
    # Toggle external player on / off
    # ------------------------------------------------------------------
    async def _toggle_external_player(self) -> bool:
        """
        Flip external_player_enabled in config, update playercorefactory.xml
        so Kodi immediately uses/stops using the external player, and broadcast
        the new state to all connected clients.
        """
        new_val = not self._config.cfg.external_player_enabled
        self._config.update({"external_player_enabled": new_val})
        _LOG.info("External player %s via remote command", "ENABLED" if new_val else "DISABLED")

        # Modify playercorefactory.xml so Kodi's behaviour changes immediately:
        #   OFF → rename .xml → .xml.bridge_disabled  (Kodi uses internal player)
        #   ON  → restore .xml.bridge_disabled → .xml  (Kodi calls bridge again)
        if new_val:
            self._enable_ext_player_xml()
        else:
            self._disable_ext_player_xml()

        await self._push({"external_player_enabled": new_val})
        return True

    def _disable_ext_player_xml(self) -> None:
        """
        Rename playercorefactory.xml → playercorefactory.xml.bridge_disabled
        so Kodi falls back to its internal player immediately.
        """
        import os
        xml_path = os.path.join(
            os.environ.get("APPDATA", ""), "Kodi", "userdata", "playercorefactory.xml"
        )
        if not xml_path or not os.path.exists(xml_path):
            _LOG.info("_disable_ext_player_xml: XML not found — nothing to rename")
            return
        disabled_path = xml_path + ".bridge_disabled"
        try:
            os.replace(xml_path, disabled_path)
            _LOG.info("Ext. player XML disabled (renamed → %s)", disabled_path)
        except OSError as exc:
            _LOG.warning("Cannot disable ext. player XML: %s", exc)

    def _enable_ext_player_xml(self) -> None:
        """
        Restore playercorefactory.xml.bridge_disabled → playercorefactory.xml,
        or re-write it from config if the disabled backup does not exist.
        """
        import os
        xml_path = os.path.join(
            os.environ.get("APPDATA", ""), "Kodi", "userdata", "playercorefactory.xml"
        )
        if not xml_path:
            return
        disabled_path = xml_path + ".bridge_disabled"
        if os.path.exists(disabled_path):
            try:
                os.replace(disabled_path, xml_path)
                _LOG.info("Ext. player XML re-enabled (restored from %s)", disabled_path)
                return
            except OSError as exc:
                _LOG.warning("Cannot restore ext. player XML: %s — will re-write", exc)
        # Fallback: re-write the XML from current config values
        cfg = self._config.cfg
        if cfg.mpchc_exe_path:
            ok, detail = self.setup_external_player(cfg.mpchc_exe_path, cfg.resume_enabled)
            _LOG.info("Ext. player XML re-written: ok=%s  path=%s", ok, detail)
        else:
            _LOG.warning(
                "Ext. player toggle ON but mpchc_exe_path not configured — "
                "playercorefactory.xml was NOT written"
            )

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
        # Explicit stop: clear the season episode list now.
        # (Not done in _on_mpchc_update itself so that the list survives the
        # brief active_player→none blip that MPC-HC emits during file switches.)
        await self._push({"season_episodes": [], "playlist_index": -1})

    # ------------------------------------------------------------------
    # Episode navigation (next / prev within season list)
    # ------------------------------------------------------------------
    async def _play_episode_cmd(self, direction: str) -> bool:
        """
        Called by the router for ``next_episode`` / ``prev_episode`` commands.

        Looks up the adjacent episode in the current ``season_episodes`` list
        and fires ``external_play`` for it.  Returns False when no list is
        loaded or the boundary is already reached.
        """
        eps = self._state.state.season_episodes
        idx = self._state.state.playlist_index
        if not eps or idx < 0:
            _LOG.debug("_play_episode_cmd: no season list / index — ignored")
            return False
        new_idx = idx + (1 if direction == "next_episode" else -1)
        if new_idx < 0 or new_idx >= len(eps):
            _LOG.debug("_play_episode_cmd: boundary reached (idx=%d, len=%d)", idx, len(eps))
            return False
        filepath = eps[new_idx].get("file", "")
        if not filepath:
            _LOG.warning("_play_episode_cmd: episode %d has no file path", new_idx)
            return False
        _LOG.info("Episode nav %s: index %d → %d  (%s)", direction, idx, new_idx, filepath)
        asyncio.create_task(self.external_play(filepath))
        return True

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
    async def external_play(self, filepath: str, no_dialog: bool = False) -> None:
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
        if resume_pos >= 60.0 and not no_dialog:
            try:
                _rtr = self._router

                def _register(inject_fn: "Any") -> None:
                    _rtr.set_dialog_handler(inject_fn)

                def _unregister() -> None:
                    _rtr.set_dialog_handler(None)

                should_resume = await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: _show_resume_dialog(resume_pos, _register, _unregister),
                )
                if should_resume is None:
                    _LOG.info("external_play: user cancelled dialog — aborting launch")
                    return
                elif not should_resume:
                    _LOG.info("external_play: user chose 'play from beginning'")
                    resume_pos = 0.0
                else:
                    _LOG.info("external_play: user chose 'resume'")
            except Exception as exc:
                _LOG.warning("external_play: resume dialog failed: %s — defaulting to resume", exc)

        # 2. Launch MPC-HC ────────────────────────────────────────────────────
        # MPC-HC cannot open smb:// URLs — convert to Windows UNC path first.
        mpc_filepath = _smb_to_unc(filepath)
        if mpc_filepath != filepath:
            _LOG.info("external_play: converted smb:// → UNC: %r", mpc_filepath)
        try:
            kwargs: dict = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            subprocess.Popen([mpc_exe, mpc_filepath], **kwargs)
            _LOG.info("external_play: launched %r with %r", mpc_exe, mpc_filepath)
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
    # Video info parser (blocking, runs in thread pool)
    # ------------------------------------------------------------------
    def _parse_mkv_sync(self, filepath: str) -> dict[str, Any]:
        """
        Parse video metadata from *filepath*.

        For .mkv: full EBML parse (tracks, chapters, resolution, FPS, HDR)
                  with ffprobe HDR fallback inside parse_mkv().
        For other containers: parse_mkv() returns empty gracefully; the ffprobe
                  fallback inside it still fills in the HDR field.
        """
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
            # Always push video info (even zeros clear stale values from previous file)
            result.update(video_info)
            v = tracks.video
            _LOG.info(
                "Video info: %d audio, %d subs, %d chapters, "
                "%dx%d %.3ffps %s bitrate=%dkbps  [%s]",
                len(audio), len(subs), len(chapters),
                v.width, v.height, v.fps, v.hdr or "SDR",
                v.bitrate_kbps, filepath,
            )
            return result
        except Exception as exc:
            _LOG.warning("Video parse error for %s: %s", filepath, exc)
            return {}
