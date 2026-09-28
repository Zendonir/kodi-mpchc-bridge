"""
Unified state model for the bridge hub.

Holds the merged state of Kodi and MPC-HC and computes diffs
for WebSocket push to connected clients.
"""

from __future__ import annotations

import copy
import re
from dataclasses import asdict, dataclass, field
from typing import Any

# Kodi BBCode-style formatting tags used by skins, scrapers and addons in
# labels, e.g. "[B]Title[/B]" or "[COLOR red]Live[/COLOR]".  [CR] is a line
# break and is replaced by a space so words are not glued together.
_KODI_CR_RE = re.compile(r"\[CR\]", re.IGNORECASE)
_KODI_BBCODE_RE = re.compile(
    r"\[/?(?:B|I|U|S|LIGHT|UPPERCASE|LOWERCASE|CAPITALIZE|TABS|COLOR(?:\s+[^\]]*)?|FONT(?:\s+[^\]]*)?)\]",
    re.IGNORECASE,
)

# Plain-text state fields that may carry Kodi formatting tags.
_TEXT_FIELDS = ("title", "artist", "album", "tv_show")


def strip_kodi_formatting(value: Any) -> str:
    """Remove Kodi BBCode-style formatting tags from a label."""
    if not value or not isinstance(value, str):
        return value or ""
    if "[" not in value:
        return value
    cleaned = _KODI_CR_RE.sub(" ", value)
    cleaned = _KODI_BBCODE_RE.sub("", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _sanitize_updates(updates: dict[str, Any]) -> dict[str, Any]:
    """Return *updates* with Kodi formatting tags stripped from all labels.

    Works on copies so the caller's dicts/lists are never mutated.
    """
    out = dict(updates)
    for key in _TEXT_FIELDS:
        if isinstance(out.get(key), str):
            out[key] = strip_kodi_formatting(out[key])
    if isinstance(out.get("season_episodes"), list):
        out["season_episodes"] = [
            {**ep, "title": strip_kodi_formatting(ep.get("title", ""))} if isinstance(ep, dict) else ep
            for ep in out["season_episodes"]
        ]
    if isinstance(out.get("chapters"), list):
        out["chapters"] = [
            {**ch, "name": strip_kodi_formatting(ch.get("name", ""))} if isinstance(ch, dict) else ch
            for ch in out["chapters"]
        ]
    for key in ("audio_tracks", "subtitle_tracks"):
        if isinstance(out.get(key), list):
            out[key] = [
                {**t, "label": strip_kodi_formatting(t.get("label", ""))} if isinstance(t, dict) else t
                for t in out[key]
            ]
    return out


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

    # --- bridge config reflected in state (for remote UI) ---
    external_player_enabled: bool = True
    boot_target: str = "kodi"  # "kodi" | "windows"

    # --- Season episode list (populated when MPC-HC plays an episode) ---
    season_episodes: list[dict] = field(default_factory=list)
    playlist_index:  int = -1   # 0-based index of current file; -1 = unknown

    # --- Library item (for toggle_watched / show_movie_info) ---
    media_id: int = 0      # Kodi movieid / episodeid; 0 = not in library
    playcount: int = 0     # 0 = unwatched, >0 = watched

    # --- MPC-HC internals (not pushed to clients) ---
    filepath: str = ""

    def to_dict(self) -> dict:
        """Return full state as a plain dict (filepath excluded).

        Track arrays that are empty are replaced with a single sentinel entry
        (pos=-1, empty label) so external remotes never receive bare ``[]``
        and can always render at least a "no entries" placeholder.
        """
        d = asdict(self)
        d.pop("filepath", None)
        # Sentinel entries (pos=-1) signal "no tracks available" to external
        # clients.  UC Remote integration drivers should map pos==-1 to
        # entity state UNAVAILABLE on their entity_select entities.
        if not d["audio_tracks"]:
            d["audio_tracks"] = [
                {"pos": -1, "label": "—", "language": "", "codec": "", "channels": 0, "forced": False, "default": False}
            ]
        if not d["subtitle_tracks"]:
            d["subtitle_tracks"] = [
                {"pos": -1, "label": "—", "language": "", "codec": "", "forced": False, "default": False}
            ]
        if not d["chapters"]:
            d["chapters"] = [{"pos": -1, "name": "—", "time_ms": 0}]
        if not d["season_episodes"]:
            d["season_episodes"] = [
                {"episodeid": -1, "episode": 0, "title": "—", "file": "",
                 "playcount": 0, "resume_pos": 0.0, "runtime": 0}
            ]
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
        Kodi formatting tags ([B], [COLOR …], …) are stripped from labels.
        """
        for key, value in _sanitize_updates(updates).items():
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
                "season_episodes": [],
                "playlist_index": -1,
                "media_id": 0,
                "playcount": 0,
            }
        )
