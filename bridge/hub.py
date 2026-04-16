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


class Hub:
    def __init__(self, config: ConfigManager) -> None:
        self._config = config
        self._state = StateManager()
        self._last_filepath: str = ""
        self._mpchc_active = False  # True while MPC-HC has a file loaded
        self._last_audiotrack_name: str = ""
        self._last_subtitletrack_name: str = ""

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
            self._server.clear_artwork()
            _LOG.info("ACTIVE PLAYER → none   (mpchc idle, kodi may take over)")

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
            asyncio.get_running_loop().create_task(self._fetch_artwork(new_filepath))

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
        Background task: find artwork in Kodi, download the bytes,
        store them in the bridge server, and push the bridge-owned URL to state.
        """
        kodi_url = await self._kodi.get_file_artwork(filepath)
        if not kodi_url:
            return
        try:
            data, ct = await self._kodi.fetch_image_bytes(kodi_url)
        except Exception as exc:
            _LOG.warning("Artwork download failed (%s): %s", kodi_url, exc)
            return

        self._server.set_artwork(data, ct)
        bridge_url = f"{self._bridge_base_url()}/api/artwork"
        _LOG.info("MPC-HC artwork stored, serving at %s (%d bytes)", bridge_url, len(data))
        await self._push({"artwork_url": bridge_url})

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
