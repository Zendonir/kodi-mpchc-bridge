"""
Kodi JSON-RPC WebSocket client.

Connects to Kodi, subscribes to player events and pushes unified-state
updates via the on_state callback. Also provides methods for sending
commands.
"""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.parse
from typing import Any, Callable, Awaitable

import aiohttp

_LOG = logging.getLogger(__name__)

RECONNECT_DELAY = 5.0
POSITION_POLL_INTERVAL = 1.0
REQUEST_TIMEOUT = 5.0

StateCallback = Callable[[dict[str, Any]], Awaitable[None]]

# Kodi player types
_PLAYER_ID_VIDEO = 1
_PLAYER_ID_AUDIO = 0

# Kodi media type → unified media_type
_MEDIA_TYPE_MAP = {
    "movie": "movie",
    "episode": "episode",
    "musicvideo": "movie",
    "song": "music",
    "album": "music",
    "artist": "music",
    "channel": "other",
    "unknown": "other",
}


class KodiClient:
    """
    Kodi JSON-RPC over WebSocket.

    Fires *on_state* with unified-state patch dicts whenever
    something changes in Kodi.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        on_state: StateCallback,
        ssl: bool = False,
    ) -> None:
        scheme = "wss" if ssl else "ws"
        self._ws_url = f"{scheme}://{host}:{port}/jsonrpc"
        self._http_url = f"{'https' if ssl else 'http'}://{host}:{port}/jsonrpc"
        self._auth = aiohttp.BasicAuth(username, password) if username else None
        self._on_state = on_state
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._running = False
        self._task: asyncio.Task | None = None
        self._poll_task: asyncio.Task | None = None
        self._req_id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._active_player_id: int | None = None
        self._last: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._connect_loop(), name="kodi-ws")

    async def stop(self) -> None:
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
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
    # JSON-RPC helpers
    # ------------------------------------------------------------------
    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    async def _call(self, method: str, params: dict | None = None) -> Any:
        """Send a JSON-RPC request and await the result."""
        req_id = self._next_id()
        payload = {"jsonrpc": "2.0", "method": method, "id": req_id}
        if params:
            payload["params"] = params

        if self._ws and not self._ws.closed:
            fut: asyncio.Future = asyncio.get_running_loop().create_future()
            self._pending[req_id] = fut
            try:
                await self._ws.send_json(payload)
                result = await asyncio.wait_for(fut, timeout=REQUEST_TIMEOUT)
                return result
            except asyncio.TimeoutError:
                _LOG.debug("Kodi WS RPC timeout: %s — retrying via HTTP", method)
                self._pending.pop(req_id, None)
                # Fall through to HTTP retry below
            finally:
                self._pending.pop(req_id, None)

        # HTTP JSON-RPC (primary when WS not connected, fallback after WS timeout)
        try:
            session = await self._get_session()
            kwargs: dict[str, Any] = {"json": payload, "timeout": aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)}
            if self._auth:
                kwargs["auth"] = self._auth
            async with session.post(self._http_url, **kwargs) as resp:
                if resp.status == 401:
                    _LOG.warning("Kodi HTTP auth failed (401) for %s — check kodi_username/kodi_password in config.json", method)
                    return None
                data = await resp.json()
                result = data.get("result")
                _LOG.debug("Kodi HTTP RPC OK: %s → %s", method, type(result).__name__)
                return result
        except Exception as exc:
            _LOG.warning("Kodi HTTP RPC failed: %s — %s", method, exc)
            return None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    async def play_pause(self) -> None:
        if self._active_player_id is not None:
            await self._call("Player.PlayPause", {"playerid": self._active_player_id})

    async def stop(self) -> None:
        if self._active_player_id is not None:
            await self._call("Player.Stop", {"playerid": self._active_player_id})

    async def seek(self, position_sec: float) -> None:
        if self._active_player_id is not None:
            h = int(position_sec // 3600)
            m = int((position_sec % 3600) // 60)
            s = int(position_sec % 60)
            ms = int((position_sec - int(position_sec)) * 1000)
            await self._call(
                "Player.Seek",
                {
                    "playerid": self._active_player_id,
                    "value": {"hours": h, "minutes": m, "seconds": s, "milliseconds": ms},
                },
            )

    async def set_volume(self, volume: int) -> None:
        await self._call("Application.SetVolume", {"volume": max(0, min(100, volume))})

    async def set_mute(self, muted: bool) -> None:
        await self._call("Application.SetMute", {"mute": muted})

    async def set_shuffle(self, shuffle: bool) -> None:
        if self._active_player_id is not None:
            await self._call(
                "Player.SetShuffle",
                {"playerid": self._active_player_id, "shuffle": shuffle},
            )

    async def set_repeat(self, repeat: str) -> None:
        if self._active_player_id is not None:
            await self._call(
                "Player.SetRepeat",
                {"playerid": self._active_player_id, "repeat": repeat},
            )

    async def navigate(self, action: str) -> None:
        """Send Input.ExecuteAction for navigation (up/down/left/right/select/back etc.)."""
        await self._call("Input.ExecuteAction", {"action": action})

    async def set_audio_stream(self, index: int) -> None:
        if self._active_player_id is not None:
            await self._call(
                "Player.SetAudioStream",
                {"playerid": self._active_player_id, "stream": index},
            )

    async def set_subtitle_stream(self, index: int) -> None:
        if self._active_player_id is not None:
            if index < 0:
                await self._call(
                    "Player.SetSubtitle",
                    {"playerid": self._active_player_id, "subtitle": "off"},
                )
            else:
                await self._call(
                    "Player.SetSubtitle",
                    {"playerid": self._active_player_id, "subtitle": index, "enable": True},
                )

    async def next_chapter(self) -> None:
        if self._active_player_id is not None:
            await self._call("Player.GoTo", {"playerid": self._active_player_id, "to": "next"})

    async def prev_chapter(self) -> None:
        if self._active_player_id is not None:
            await self._call("Player.GoTo", {"playerid": self._active_player_id, "to": "previous"})

    async def skip_forward(self) -> None:
        if self._active_player_id is not None:
            await self._call(
                "Player.Seek",
                {"playerid": self._active_player_id, "value": "bigforward"},
            )

    async def skip_backward(self) -> None:
        if self._active_player_id is not None:
            await self._call(
                "Player.Seek",
                {"playerid": self._active_player_id, "value": "bigbackward"},
            )

    # ------------------------------------------------------------------
    # Connection loop
    # ------------------------------------------------------------------
    async def _connect_loop(self) -> None:
        while self._running:
            try:
                await self._connect()
            except asyncio.CancelledError:
                return
            except Exception as exc:
                _LOG.warning("Kodi WS disconnected: %s. Reconnecting in %ss.", exc, RECONNECT_DELAY)

            if not self._running:
                return

            # signal idle
            if self._last.get("active"):
                self._last = {}
                try:
                    await self._on_state({"active_player": "none", "state": "idle"})
                except Exception:
                    pass

            await asyncio.sleep(RECONNECT_DELAY)

    async def _connect(self) -> None:
        session = await self._get_session()
        kwargs: dict[str, Any] = {}
        if self._auth:
            kwargs["auth"] = self._auth

        _LOG.info("Connecting to Kodi at %s", self._ws_url)
        async with session.ws_connect(self._ws_url, **kwargs) as ws:
            self._ws = ws
            _LOG.info("Kodi WebSocket connected")

            # Start message reader FIRST so RPC responses can be received
            # while _sync_initial() awaits its futures.
            reader_task = asyncio.create_task(self._read_loop(ws), name="kodi-reader")
            self._poll_task = asyncio.create_task(self._position_poll(), name="kodi-pos")

            try:
                await self._sync_initial()
                # Wait for reader to finish (disconnected)
                await reader_task
            finally:
                reader_task.cancel()
                self._poll_task.cancel()
                self._ws = None

    async def _read_loop(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                await self._handle_message(json.loads(msg.data))
            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                break

    # ------------------------------------------------------------------
    # Initial state sync
    # ------------------------------------------------------------------
    async def _sync_initial(self) -> None:
        """Fetch current Kodi state on (re)connect."""
        # Get active players
        players = await self._call("Player.GetActivePlayers") or []
        if players:
            player = players[0]
            self._active_player_id = player["playerid"]
            await self._sync_player(player["playerid"])
        else:
            self._active_player_id = None

        # Get application volume
        app = await self._call("Application.GetProperties", {"properties": ["volume", "muted"]}) or {}
        updates: dict[str, Any] = {}
        if "volume" in app:
            updates["volume"] = app["volume"]
        if "muted" in app:
            updates["muted"] = app["muted"]
        if updates:
            await self._on_state(updates)

    async def _sync_player(self, player_id: int) -> None:
        """Fetch full player state."""
        item = await self._call(
            "Player.GetItem",
            {
                "playerid": player_id,
                "properties": [
                    "title", "artist", "album", "year", "thumbnail",
                    "showtitle", "season", "episode", "rating",
                    "streamdetails", "art", "file",
                ],
            },
        ) or {}

        props = await self._call(
            "Player.GetProperties",
            {
                "playerid": player_id,
                "properties": [
                    "speed", "time", "totaltime", "type",
                    "currentaudiostream", "audiostreams",
                    "currentsubtitle", "subtitles", "subtitleenabled",
                    "currentchapter", "chapter", "chapters",
                    "shuffled", "repeat",
                ],
            },
        ) or {}

        # Only claim active if we actually got meaningful data from Kodi
        if not props and not item:
            _LOG.debug("Kodi _sync_player: both calls returned None, skipping active claim")
            return

        updates = self._build_state_update(item, props)
        updates["active_player"] = "kodi"
        self._last["active"] = True
        await self._on_state(updates)

    def _build_state_update(self, item: dict, props: dict) -> dict[str, Any]:
        """Build a unified-state update dict from Kodi item+props."""
        updates: dict[str, Any] = {}

        # Playback state
        speed = props.get("speed", 0)
        updates["state"] = "playing" if speed != 0 else "paused"

        # Position/duration
        t = props.get("time", {})
        updates["position"] = t.get("hours", 0) * 3600 + t.get("minutes", 0) * 60 + t.get("seconds", 0)
        d = props.get("totaltime", {})
        updates["duration"] = d.get("hours", 0) * 3600 + d.get("minutes", 0) * 60 + d.get("seconds", 0)

        # Media info
        media = item.get("item", item)
        media_type_raw = props.get("type", media.get("type", "unknown"))
        updates["media_type"] = _MEDIA_TYPE_MAP.get(media_type_raw, "other")
        updates["title"] = media.get("title", "") or ""
        updates["artist"] = ", ".join(media.get("artist", [])) if isinstance(media.get("artist"), list) else media.get("artist", "") or ""
        updates["album"] = media.get("album", "") or ""
        updates["year"] = media.get("year", 0) or 0
        updates["tv_show"] = media.get("showtitle", "") or ""
        updates["season"] = media.get("season", 0) or 0
        updates["episode"] = media.get("episode", 0) or 0
        updates["rating"] = round(media.get("rating", 0.0) or 0.0, 1)

        # Artwork
        thumb = media.get("thumbnail", "") or ""
        updates["artwork_url"] = thumb

        # Audio streams
        audio_streams = props.get("audiostreams", [])
        updates["audio_tracks"] = [
            {
                "pos": i,
                "label": self._stream_label(s, "audio"),
                "language": s.get("language", ""),
                "codec": s.get("codec", ""),
                "channels": s.get("channels", 0),
                "forced": False,
                "default": False,
            }
            for i, s in enumerate(audio_streams)
        ]
        cur_audio = props.get("currentaudiostream", {})
        updates["current_audio"] = cur_audio.get("index", 0)

        # Subtitles
        subtitles = props.get("subtitles", [])
        sub_enabled = props.get("subtitleenabled", False)
        updates["subtitle_tracks"] = [
            {
                "pos": i,
                "label": self._stream_label(s, "subtitle"),
                "language": s.get("language", ""),
                "codec": s.get("codec", ""),
                "forced": False,
                "default": False,
            }
            for i, s in enumerate(subtitles)
        ]
        cur_sub = props.get("currentsubtitle", {})
        updates["current_subtitle"] = cur_sub.get("index", -1) if sub_enabled else -1

        # Chapters
        chapter_count = props.get("chapters", 0)
        updates["current_chapter"] = props.get("currentchapter", 0)
        if chapter_count > 0 and not updates.get("chapters"):
            # Chapters are named by number; detailed names require separate call
            updates["chapters"] = [
                {"pos": i, "name": f"Chapter {i + 1}", "time_ms": 0}
                for i in range(chapter_count)
            ]

        # Shuffle / repeat
        updates["shuffle"] = props.get("shuffled", False)
        updates["repeat"] = props.get("repeat", "off")

        return updates

    @staticmethod
    def _stream_label(stream: dict, kind: str) -> str:
        lang = stream.get("language", "und") or "und"
        name = stream.get("name", "") or ""
        codec = (stream.get("codec", "") or "").upper()
        if kind == "audio":
            ch = stream.get("channels", 0)
            ch_str = {6: "5.1", 8: "7.1"}.get(ch, f"{ch}ch" if ch else "")
            parts = [lang.upper()[:3]]
            if ch_str:
                parts.append(ch_str)
            if codec:
                parts.append(codec)
            return " ".join(parts)
        else:
            parts = [lang.upper()[:3]]
            if codec:
                parts.append(codec)
            return " ".join(parts)

    # ------------------------------------------------------------------
    # Message handler
    # ------------------------------------------------------------------
    async def _handle_message(self, msg: dict) -> None:
        # JSON-RPC response (result or error)
        if "id" in msg and ("result" in msg or "error" in msg):
            fut = self._pending.get(msg["id"])
            if fut and not fut.done():
                if "result" in msg:
                    fut.set_result(msg["result"])
                else:
                    # Resolve with None on error so callers don't hang
                    _LOG.debug("Kodi RPC error for id %s: %s", msg["id"], msg.get("error"))
                    fut.set_result(None)
            return

        method = msg.get("method", "")
        params = msg.get("params", {})

        if method in ("Player.OnPlay", "Player.OnResume"):
            data = params.get("data", {})
            player_id = data.get("player", {}).get("playerid", _PLAYER_ID_VIDEO)
            self._active_player_id = player_id
            await self._sync_player(player_id)

        elif method == "Player.OnPause":
            await self._on_state({"state": "paused"})

        elif method == "Player.OnStop":
            self._active_player_id = None
            self._last["active"] = False
            await self._on_state({
                "state": "stopped",
                "position": 0.0,
                "audio_tracks": [],
                "subtitle_tracks": [],
                "chapters": [],
            })

        elif method == "Player.OnSeek":
            data = params.get("data", {})
            t = data.get("player", {}).get("time", {})
            pos = t.get("hours", 0) * 3600 + t.get("minutes", 0) * 60 + t.get("seconds", 0)
            await self._on_state({"position": pos})

        elif method == "Player.OnAVChange":
            if self._active_player_id is not None:
                await self._sync_player(self._active_player_id)

        elif method == "Application.OnVolumeChanged":
            data = params.get("data", {})
            await self._on_state({
                "volume": data.get("volume", 0),
                "muted": data.get("muted", False),
            })

    # ------------------------------------------------------------------
    # Position polling (fills in position between seek events)
    # ------------------------------------------------------------------
    async def _position_poll(self) -> None:
        while True:
            await asyncio.sleep(POSITION_POLL_INTERVAL)
            if self._active_player_id is None:
                continue
            props = await self._call(
                "Player.GetProperties",
                {"playerid": self._active_player_id, "properties": ["time", "speed"]},
            )
            if props is None:
                continue
            t = props.get("time", {})
            pos = t.get("hours", 0) * 3600 + t.get("minutes", 0) * 60 + t.get("seconds", 0)
            speed = props.get("speed", 0)
            state = "playing" if speed != 0 else "paused"
            await self._on_state({"position": float(pos), "state": state})
