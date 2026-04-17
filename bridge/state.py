"""
Unified state model for the bridge hub.

Holds the merged state of Kodi and MPC-HC and computes diffs
for WebSocket push to connected clients.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TrackInfo:
    """Audio or subtitle track."""

    pos: int
    label: str
    language: str = ""
    codec: str = ""
    channels: int = 0
    forced: bool = False
    default: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ChapterInfo:
    """Chapter entry."""

    pos: int
    name: str
    time_ms: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class UnifiedState:
    """
    Full player state, sourced from whichever player is active.

    active_player: "kodi" | "mpchc" | "none"
    state:         "playing" | "paused" | "stopped" | "idle"
    media_type:    "movie" | "episode" | "music" | "other" | ""
    repeat:        "off" | "one" | "all"
    """

    # --- active player ---
    active_player: str = "none"

    # --- playback ---
    state: str = "idle"
    position: float = 0.0
    duration: float = 0.0

    # --- media metadata ---
    title: str = ""
    artist: str = ""
    album: str = ""
    year: int = 0
    media_type: str = ""
    artwork_url: str = ""

    # --- TV show extras ---
    tv_show: str = ""
    season: int = 0
    episode: int = 0
    season_count: int = 0   # total seasons in this TV show
    episode_count: int = 0  # total episodes in current season
    rating: float = 0.0

    # --- tracks ---
    audio_tracks: list[dict] = field(default_factory=list)
    subtitle_tracks: list[dict] = field(default_factory=list)
    chapters: list[dict] = field(default_factory=list)
    current_audio: int = 0
    current_subtitle: int = -1  # -1 = disabled
    current_chapter: int = 0

    # --- video / stream info (populated from MKV parse or Kodi stream details) ---
    video_width: int = 0
    video_height: int = 0
    video_fps: float = 0.0
    hdr: str = ""               # "HDR10" | "HLG" | "DV" | "" (SDR)
    video_codec: str = ""
    video_bitrate_kbps: int = 0

    # --- Kodi player controls ---
    volume: int = 0
    muted: bool = False
    shuffle: bool = False
    repeat: str = "off"

    # --- MPC-HC internals (not pushed to clients) ---
    filepath: str = ""

    def to_dict(self) -> dict:
        """Return full state as a plain dict (filepath excluded)."""
        d = asdict(self)
        d.pop("filepath", None)
        return d


class StateManager:
    """
    Manages the unified state and computes diffs for WS push.

    Usage::

        mgr = StateManager()
        patch = mgr.apply({"state": "playing", "position": 12.3})
        # patch contains only the fields that actually changed
    """

    def __init__(self) -> None:
        self._state = UnifiedState()
        self._prev: dict[str, Any] = self._state.to_dict()

    @property
    def state(self) -> UnifiedState:
        return self._state

    def apply(self, updates: dict[str, Any]) -> dict[str, Any]:
        """
        Apply *updates* to the state and return the diff dict.

        Only keys whose value actually changed are included in the diff.
        """
        for key, value in updates.items():
            if hasattr(self._state, key):
                setattr(self._state, key, value)

        current = self._state.to_dict()
        diff: dict[str, Any] = {}
        for key, value in current.items():
            if value != self._prev.get(key):
                diff[key] = value

        self._prev = copy.deepcopy(current)
        return diff

    def full(self) -> dict[str, Any]:
        """Return the complete state dict."""
        return self._state.to_dict()

    def reset(self) -> dict[str, Any]:
        """Reset to idle/empty state and return the diff."""
        return self.apply(
            {
                "active_player": "none",
                "state": "idle",
                "position": 0.0,
                "duration": 0.0,
                "title": "",
                "artist": "",
                "album": "",
                "year": 0,
                "media_type": "",
                "artwork_url": "",
                "tv_show": "",
                "season": 0,
                "episode": 0,
                "season_count": 0,
                "episode_count": 0,
                "rating": 0.0,
                "audio_tracks": [],
                "subtitle_tracks": [],
                "chapters": [],
                "current_audio": 0,
                "current_subtitle": -1,
                "current_chapter": 0,
                "filepath": "",
                "video_width": 0,
                "video_height": 0,
                "video_fps": 0.0,
                "hdr": "",
                "video_codec": "",
                "video_bitrate_kbps": 0,
            }
        )
