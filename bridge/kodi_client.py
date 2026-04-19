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
REQUEST_TIMEOUT = 2.0

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
        ws_port: int,
        http_port: int,
        username: str,
        password: str,
        on_state: StateCallback,
        ssl: bool = False,
    ) -> None:
        scheme = "wss" if ssl else "ws"
        http_scheme = "https" if ssl else "http"
        self._ws_url = f"{scheme}://{host}:{ws_port}/jsonrpc"
        self._http_url = f"{http_scheme}://{host}:{http_port}/jsonrpc"
        self._http_base = f"{http_scheme}://{host}:{http_port}"
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
            _LOG.warning("Kodi HTTP RPC failed: %s — %s: %s", method, type(exc).__name__, exc)
            return None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    async def fetch_image_bytes(self, url: str) -> tuple[bytes, str]:
        """
        Download image bytes from *url* using Kodi auth.
        Returns (data, content_type).  Raises on failure.
        """
        from yarl import URL as YarlURL

        session = await self._get_session()
        kwargs: dict[str, Any] = {"timeout": aiohttp.ClientTimeout(total=10)}
        if self._auth:
            kwargs["auth"] = self._auth
        # encoded=True prevents aiohttp/yarl from decoding and re-encoding the
        # path, which would corrupt percent-encoded characters like %3A → :
        async with session.get(YarlURL(url, encoded=True), **kwargs) as resp:
            resp.raise_for_status()
            data = await resp.read()
            return data, resp.content_type or "image/jpeg"

    async def get_file_info(
        self,
        filepath: str,
        movie_art_mode: str = "poster",
        episode_art_mode: str = "poster",
        music_art_mode: str = "thumb",
    ) -> dict[str, Any]:
        """
        Look up *filepath* in the Kodi library.

        Returns a dict with artwork_url, title, year, tv_show, season, episode.
        All keys are always present; empty / zero when not found.

        Strategy:
        1. Player.GetActivePlayers + Player.GetItem  (active item — fastest)
        2. VideoLibrary.GetMovies by filename
        3. VideoLibrary.GetEpisodes by filename
        4. Files.GetFileDetails (last resort)
        """
        import os

        _EMPTY: dict[str, Any] = {
            "artwork_url": "", "title": "",
            "year": 0, "tv_show": "", "season": 0, "episode": 0,
            "season_count": 0, "episode_count": 0,
        }

        def _pick_art(item: dict, media_type: str = "") -> str:
            art = item.get("art") or {}
            tn  = item.get("thumbnail", "") or ""

            # Auto-detect when caller doesn't know
            if not media_type:
                if art.get("tvshow.poster") or art.get("season.poster") or item.get("showtitle"):
                    media_type = "episode"
                elif item.get("type") in ("song", "album", "artist", "music"):
                    media_type = "music"
                else:
                    media_type = "movie"

            if media_type == "episode":
                if episode_art_mode == "thumb":
                    return (art.get("thumb","") or art.get("season.poster","")
                            or art.get("tvshow.poster","") or art.get("poster","")
                            or art.get("fanart","") or tn or "")
                if episode_art_mode == "season.poster":
                    return (art.get("season.poster","") or art.get("tvshow.poster","")
                            or art.get("thumb","") or art.get("poster","")
                            or art.get("fanart","") or tn or "")
                if episode_art_mode == "fanart":
                    return (art.get("fanart","") or art.get("tvshow.poster","")
                            or art.get("season.poster","") or art.get("thumb","")
                            or art.get("poster","") or tn or "")
                # "poster" (default) → tvshow.poster first
                return (art.get("tvshow.poster","") or art.get("season.poster","")
                        or art.get("poster","") or art.get("thumb","")
                        or art.get("fanart","") or tn or "")

            if media_type == "music":
                if music_art_mode == "fanart":
                    return (art.get("fanart","") or art.get("thumb","") or tn or "")
                return (art.get("thumb","") or tn or art.get("fanart","") or "")

            # movie
            if movie_art_mode == "fanart":
                return (art.get("fanart","") or art.get("poster","")
                        or art.get("thumb","") or tn or "")
            if movie_art_mode == "thumb":
                return (art.get("thumb","") or art.get("poster","")
                        or art.get("fanart","") or tn or "")
            # "poster" (default)
            return (art.get("poster","") or art.get("thumb","")
                    or art.get("fanart","") or tn or "")

        def _meta(item: dict, *, is_episode: bool = False, is_music: bool = False) -> dict[str, Any]:
            if is_episode:
                mt = "episode"
            elif is_music:
                mt = "music"
            else:
                mt = "movie"
            thumb = _pick_art(item, mt)
            return {
                "artwork_url": self._image_url(thumb) if thumb else "",
                "title":    item.get("title", "")     or item.get("label", "") or "",
                "year":     item.get("year", 0)        or 0,
                "tv_show":  item.get("showtitle", "")  or "" if is_episode else "",
                "season":   item.get("season", 0)      or 0  if is_episode else 0,
                "episode":  item.get("episode", 0)     or 0  if is_episode else 0,
                # tvshowid is used by hub to fetch season episode list; not stored in state
                "tvshowid": item.get("tvshowid", -1)   if is_episode else -1,
            }

        filename = os.path.basename(filepath)

        # Saved from the mismatch path (step 1): show-level info that applies
        # to any episode of the same series — used as a last-resort fallback
        # when the episode itself can't be found via steps 2-5.
        _mismatch_tvshowid: int = -1
        _mismatch_tv_show:  str = ""
        _mismatch_art:      str = ""
        _mismatch_season:   int = 0   # season of the *new* file (from mismatch item)

        # 1) Active Kodi player → fastest, most complete metadata
        players = await self._call("Player.GetActivePlayers") or []
        for player in players:
            pid = player.get("playerid")
            if pid is None:
                continue
            result = await self._call("Player.GetItem", {
                "playerid": pid,
                "properties": [
                    "art", "thumbnail", "file",
                    "title", "year", "showtitle", "season", "episode", "tvshowid",
                ],
            })
            _LOG.info("FileInfo [1/4] Player.GetItem(player=%d) → %s", pid, result)
            if result and isinstance(result, dict):
                item = result.get("item", {})
                # Only use if the active file matches ours
                active_file = item.get("file", "")
                if os.path.basename(active_file) == filename:
                    is_ep = item.get("type", "") == "episode" or bool(item.get("showtitle"))
                    m = _meta(item, is_episode=is_ep)
                    if is_ep:
                        tvshowid = item.get("tvshowid", -1)
                        cur_season = item.get("season", 0)
                        if tvshowid >= 0 and cur_season > 0:
                            sc, ec = await self._fetch_season_counts(tvshowid, cur_season)
                            m["season_count"] = sc
                            m["episode_count"] = ec
                    _LOG.info("FileInfo [1/4] matched: title=%r year=%r s%s/%s e%s/%s",
                              m["title"], m["year"],
                              m.get("season"), m.get("season_count"),
                              m.get("episode"), m.get("episode_count"))
                    return m
                # File doesn't match (Kodi still on the previous episode).
                # Extract show-level info that is valid for any episode of the
                # series (tvshowid, tv_show, tvshow.poster/season.poster).
                # Episode-specific fields (title/season/episode/thumb) belong
                # to the wrong episode and must NOT be used.
                is_ep2     = item.get("type", "") == "episode" or bool(item.get("showtitle"))
                tvshow_id2 = item.get("tvshowid", -1) if is_ep2 else -1
                # Show-safe art: only poster / season poster / fanart — never thumb
                _sa = item.get("art") or {}
                safe_art = (
                    _sa.get("tvshow.poster", "")
                    or _sa.get("season.poster", "")
                    or _sa.get("poster", "")
                    or _sa.get("fanart", "")
                    or ""
                )
                _mismatch_tvshowid = tvshow_id2
                _mismatch_tv_show  = item.get("showtitle", "") or "" if is_ep2 else ""
                _mismatch_art      = self._image_url(safe_art) if safe_art else ""
                # Season of the *mismatched* item is the best guess for the new
                # episode's season (they usually belong to the same season).
                _mismatch_season   = item.get("season", 0) if is_ep2 else 0

                if episode_art_mode != "thumb":
                    # Poster / season-poster / fanart are identical for all
                    # episodes of this show → safe to return immediately.
                    _LOG.info(
                        "FileInfo [1/4] file mismatch (Kodi on %r) "
                        "— using tvshow art  tvshowid=%d",
                        os.path.basename(active_file), tvshow_id2,
                    )
                    return {
                        **_EMPTY,
                        "artwork_url": _mismatch_art,
                        "tvshowid":    _mismatch_tvshowid,
                        "tv_show":     _mismatch_tv_show,
                    }
                # thumb mode: each episode has its own scene thumbnail →
                # fall through to GetEpisodes (step 3) to find the correct one.
                _LOG.info(
                    "FileInfo [1/4] file mismatch (Kodi on %r) tvshowid=%d "
                    "— thumb mode, falling through to episode lookup",
                    os.path.basename(active_file), tvshow_id2,
                )

        # 2) Movie library by filename
        result = await self._call("VideoLibrary.GetMovies", {
            "filter": {"field": "filename", "operator": "is", "value": filename},
            "properties": ["thumbnail", "art", "title", "year"],
            "limits": {"end": 1},
        })
        _LOG.info("FileInfo [2/4] GetMovies(%r) → %s", filename, result)
        if result and isinstance(result, dict):
            movies = result.get("movies", [])
            if movies:
                m = _meta(movies[0])
                _LOG.info("FileInfo [2/4] movie: title=%r year=%r art=%r", m["title"], m["year"], m["artwork_url"])
                return m

        # 3) Episode library by filename
        result = await self._call("VideoLibrary.GetEpisodes", {
            "filter": {"field": "filename", "operator": "is", "value": filename},
            "properties": ["thumbnail", "art", "title", "year", "showtitle",
                           "season", "episode", "tvshowid"],
            "limits": {"end": 1},
        })
        _LOG.info("FileInfo [3/4] GetEpisodes(%r) → %s", filename, result)
        if result and isinstance(result, dict):
            episodes = result.get("episodes", [])
            if episodes:
                ep = episodes[0]
                m = _meta(ep, is_episode=True)
                # Fetch season count + episode count for current season
                tvshowid = ep.get("tvshowid", -1)
                cur_season = ep.get("season", 0)
                if tvshowid >= 0 and cur_season > 0:
                    sc, ec = await self._fetch_season_counts(tvshowid, cur_season)
                    m["season_count"] = sc
                    m["episode_count"] = ec
                _LOG.info("FileInfo [3/4] ep: title=%r show=%r s%s/%s e%s/%s",
                          m["title"], m["tv_show"],
                          m.get("season"), m.get("season_count"),
                          m.get("episode"), m.get("episode_count"))
                return m

        # 3b) Episode lookup via tvshowid+season (MySQL-backed Kodi libraries do
        #     not support VideoLibrary.GetEpisodes with a filename filter — the
        #     call returns None instead of an empty list).  When we landed on the
        #     mismatch path in step 1 we already know the tvshowid and season, so
        #     we can fetch all episodes for that season and match by filename in
        #     Python — reliable on both SQLite and MySQL setups.
        if _mismatch_tvshowid >= 0 and _mismatch_season > 0:
            result3b = await self._call("VideoLibrary.GetEpisodes", {
                "tvshowid": _mismatch_tvshowid,
                "season":   _mismatch_season,
                "properties": [
                    "thumbnail", "art", "title", "year", "showtitle",
                    "season", "episode", "tvshowid", "file",
                ],
            })
            eps3b = (result3b or {}).get("episodes", [])
            _LOG.info(
                "FileInfo [3b] GetEpisodes(tvshowid=%d, season=%d) → %d eps",
                _mismatch_tvshowid, _mismatch_season, len(eps3b),
            )
            for ep in eps3b:
                if os.path.basename(ep.get("file", "")) == filename:
                    m = _meta(ep, is_episode=True)
                    tvshowid_ep   = ep.get("tvshowid", _mismatch_tvshowid)
                    cur_season_ep = ep.get("season",   _mismatch_season)
                    if tvshowid_ep >= 0 and cur_season_ep > 0:
                        sc, ec = await self._fetch_season_counts(tvshowid_ep, cur_season_ep)
                        m["season_count"] = sc
                        m["episode_count"] = ec
                    _LOG.info(
                        "FileInfo [3b] matched: title=%r s%s/%s e%s/%s",
                        m["title"],
                        m.get("season"), m.get("season_count"),
                        m.get("episode"), m.get("episode_count"),
                    )
                    return m

        # 4) Files.GetFileDetails (exact path, last resort)
        result = await self._call("Files.GetFileDetails", {
            "file": filepath,
            "media": "video",
            "properties": ["thumbnail", "art", "title"],
        })
        _LOG.info("FileInfo [4/4] GetFileDetails → %s", result)
        if result and isinstance(result, dict):
            item = result.get("filedetails", {})
            thumb = _pick_art(item)
            if thumb:
                return {**_EMPTY, "artwork_url": self._image_url(thumb),
                        "title": item.get("label", "") or ""}

        # 5) SQLite direct fallback — bypasses JSON-RPC API issues
        #    (e.g. MPC-HC is the active player so Kodi has no active player object,
        #    or the episode filename has characters that confuse the filter).
        db_result = await asyncio.get_running_loop().run_in_executor(
            None, lambda: self._get_file_info_from_db_sync(
                filepath, movie_art_mode, episode_art_mode, music_art_mode
            )
        )
        if db_result:
            _LOG.info("FileInfo [5/5] DB fallback: title=%r art=%r",
                      db_result.get("title"), db_result.get("artwork_url", "")[:60])
            return db_result

        # All steps failed — if we captured show info from a step-1 mismatch,
        # return that as a last-resort fallback so the season episode list is
        # still available and we at least show the series poster.
        if _mismatch_tvshowid >= 0:
            _LOG.info(
                "FileInfo: no exact match; using mismatch show info "
                "tvshowid=%d  art=%r",
                _mismatch_tvshowid, _mismatch_art[:60],
            )
            return {
                **_EMPTY,
                "artwork_url": _mismatch_art,
                "tvshowid":    _mismatch_tvshowid,
                "tv_show":     _mismatch_tv_show,
            }

        _LOG.info("FileInfo: nothing found in Kodi library for %r", filepath)
        return dict(_EMPTY)

    async def _fetch_season_counts(self, tvshowid: int, current_season: int) -> tuple[int, int]:
        """
        Return (total_seasons, episodes_in_current_season) for a TV show.
        Uses VideoLibrary.GetSeasons — one call, no extra overhead.
        """
        result = await self._call("VideoLibrary.GetSeasons", {
            "tvshowid": tvshowid,
            "properties": ["season", "episode"],
        })
        if not result or not isinstance(result, dict):
            return 0, 0
        seasons = result.get("seasons", [])
        total_seasons = len(seasons)
        ep_count = next(
            (s.get("episode", 0) for s in seasons if s.get("season") == current_season),
            0,
        )
        return total_seasons, ep_count

    async def get_season_episodes(self, tvshowid: int, season: int) -> list[dict]:
        """
        Fetch all episodes for a show/season from Kodi, sorted by episode number.

        Each returned dict contains:
          episodeid, episode, title, file, playcount, resume_pos (seconds),
          runtime (seconds).

        Returns an empty list if the call fails or returns no data.
        """
        result = await self._call("VideoLibrary.GetEpisodes", {
            "tvshowid": tvshowid,
            "season":   season,
            "properties": [
                "title", "episode", "season", "file",
                "resume", "playcount", "runtime",
            ],
            "sort": {"order": "ascending", "method": "episode"},
        })
        if not result or not isinstance(result, dict):
            return []
        episodes = result.get("episodes", [])
        out: list[dict] = []
        for ep in episodes:
            out.append({
                "episodeid":  ep.get("episodeid", 0),
                "episode":    ep.get("episode",   0),
                "title":      ep.get("title",      ""),
                "file":       ep.get("file",        ""),
                "playcount":  ep.get("playcount",   0),
                "resume_pos": float((ep.get("resume") or {}).get("position", 0)),
                "runtime":    ep.get("runtime", 0),
            })
        _LOG.info(
            "get_season_episodes: tvshowid=%d season=%d → %d episodes",
            tvshowid, season, len(out),
        )
        return out

    def _image_url(self, kodi_url: str) -> str:
        """
        Convert a Kodi image:// URL to a fetchable HTTP(S) URL.

        Kodi stores artwork in two forms:
          image://https%3a%2f%2fassets.fanart.tv%2f...  → remote image (Fanart.tv/TMDB)
          image://video@Y%3a%5cFilme%5c...              → local video thumbnail

        For remote images the inner HTTP URL is extracted and used directly.
        For local thumbnails Kodi's image proxy is used.
        """
        if not kodi_url:
            return ""
        if not kodi_url.startswith("image://"):
            return kodi_url

        # Decode once so we always work with the unescaped form
        normalized = urllib.parse.unquote(kodi_url)   # image://https://...  or  image://video@...
        inner = normalized[len("image://"):].rstrip("/")

        # Remote image wrapped in image:// → use the URL directly
        if inner.startswith("https://") or inner.startswith("http://"):
            _LOG.debug("_image_url: direct remote URL %s", inner)
            return inner

        # Local / Kodi-internal → route through Kodi's image proxy
        encoded = urllib.parse.quote(normalized, safe="")
        proxy = f"{self._http_base}/image/{encoded}"
        _LOG.debug("_image_url: Kodi proxy %s", proxy)
        return proxy

    # ------------------------------------------------------------------
    # Textures cache helpers
    # ------------------------------------------------------------------
    def _resolve_texture_path_sync(self, art_url: str) -> "str | None":
        """
        Look up *art_url* in Kodi's ``Textures13.db`` and return the full
        local path to the cached image file under ``Thumbnails\\``, or None
        if not cached.

        Kodi stores artwork URLs as-is (e.g. ``https://artworks.thetvdb.com/…``
        or ``smb://HOMESERVER/…``) in both ``MyVideos*.db`` → ``art.url`` and
        ``Textures13.db`` → ``texture.url``.  The mapping is 1-to-1, so a
        direct lookup works without any URL rewriting.
        """
        import os
        import sqlite3

        appdata = os.environ.get("APPDATA", "")
        if not appdata:
            return None
        tx_db = os.path.join(
            appdata, "Kodi", "userdata", "Database", "Textures13.db"
        )
        if not os.path.isfile(tx_db):
            return None
        root = os.path.join(appdata, "Kodi", "userdata", "Thumbnails")

        # Try both the URL as-is and with a trailing slash stripped,
        # because Kodi sometimes adds a trailing "/" to video thumbnails.
        candidates = [art_url]
        if art_url.endswith("/"):
            candidates.append(art_url.rstrip("/"))

        try:
            conn = sqlite3.connect(
                f"file:{tx_db}?mode=ro", uri=True, timeout=2.0
            )
            try:
                for url_try in candidates:
                    row = conn.execute(
                        "SELECT cachedurl FROM texture WHERE url=? LIMIT 1",
                        (url_try,),
                    ).fetchone()
                    if row:
                        path = os.path.join(root, row[0].replace("/", os.sep))
                        if os.path.isfile(path):
                            return path
                        _LOG.debug("Textures13: entry found but file missing: %s", path)
            finally:
                conn.close()
        except Exception as exc:
            _LOG.debug("Textures13 lookup failed for %r: %s", art_url[:60], exc)
        return None

    async def fetch_artwork_bytes(self, art_url: str) -> "tuple[bytes, str] | None":
        """
        Fetch artwork bytes for *art_url*.

        Strategy
        --------
        1. Look up the URL in Kodi's local ``Textures13.db`` texture cache.
           If found, read the file directly from ``Thumbnails\\`` — no HTTP
           round-trip needed, works even when the original source is offline.
        2. Fall back to an HTTP fetch (Kodi proxy for local thumbnails,
           direct download for remote HTTPS URLs).

        Returns ``(data, content_type)`` or ``None`` on failure.
        """
        import os

        # 1. Local Textures cache
        path = await asyncio.get_running_loop().run_in_executor(
            None, self._resolve_texture_path_sync, art_url
        )
        if path:
            try:
                with open(path, "rb") as fh:
                    data = fh.read()
                ext = os.path.splitext(path)[1].lower()
                ct = {
                    ".jpg":  "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".png":  "image/png",
                    ".webp": "image/webp",
                }.get(ext, "image/jpeg")
                _LOG.info(
                    "Artwork from Textures cache: %s (%d bytes)", path, len(data)
                )
                return data, ct
            except Exception as exc:
                _LOG.debug("Cannot read texture cache file %s: %s", path, exc)

        # 2. HTTP fallback
        try:
            data, ct = await self.fetch_image_bytes(art_url)
            return data, ct
        except Exception as exc:
            _LOG.debug("HTTP artwork fetch failed for %r: %s", art_url[:60], exc)

        return None

    async def get_tvshow_art(self, tvshowid: int) -> str:
        """
        Return the best available art URL for a TV show (poster > fanart).
        Used as a fallback when per-episode art lookup fails.
        """
        result = await self._call("VideoLibrary.GetTVShowDetails", {
            "tvshowid": tvshowid,
            "properties": ["art", "thumbnail"],
        })
        if not result or not isinstance(result, dict):
            return ""
        item = result.get("tvshowdetails", {})
        art = item.get("art") or {}
        url = (
            art.get("poster", "")
            or art.get("fanart", "")
            or item.get("thumbnail", "")
            or ""
        )
        return self._image_url(url) if url else ""

    def _get_file_info_from_db_sync(
        self,
        filepath: str,
        movie_art_mode: str = "poster",
        episode_art_mode: str = "poster",
        music_art_mode: str = "thumb",
    ) -> "dict[str, Any] | None":
        """
        Read file info + artwork directly from Kodi's SQLite database.

        Used as a fallback when the JSON-RPC API cannot find the file
        (e.g. MPC-HC is the active player so Kodi reports no active item,
        or the filename contains characters that confuse the library filter).

        Opens the DB read-only so it never blocks or corrupts Kodi's own writes.
        Returns a dict compatible with get_file_info(), or None on failure.
        """
        import glob
        import os
        import sqlite3

        appdata = os.environ.get("APPDATA", "")
        if not appdata:
            return None
        db_pattern = os.path.join(
            appdata, "Kodi", "userdata", "Database", "MyVideos*.db"
        )
        # Sort descending so we always pick the newest DB version
        dbs = sorted(glob.glob(db_pattern), reverse=True)
        if not dbs:
            _LOG.debug("Kodi DB fallback: no MyVideos*.db found under %s", appdata)
            return None

        db_path = dbs[0]
        filename = os.path.basename(filepath)

        _EMPTY_DB: dict[str, Any] = {
            "artwork_url": "", "title": "", "year": 0,
            "tv_show": "", "season": 0, "episode": 0,
            "season_count": 0, "episode_count": 0,
            "tvshowid": -1,
        }

        try:
            conn = sqlite3.connect(
                f"file:{db_path}?mode=ro", uri=True,
                timeout=2.0, check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            try:
                cur = conn.cursor()

                # ── TV episode ────────────────────────────────────────────
                cur.execute("""
                    SELECT e.idEpisode,
                           e.c00                     AS ep_title,
                           CAST(e.c12 AS INTEGER)    AS season_num,
                           CAST(e.c13 AS INTEGER)    AS episode_num,
                           e.idShow,
                           ts.c00                    AS show_title
                    FROM   episode e
                    JOIN   files   f  ON f.idFile  = e.idFile
                    JOIN   tvshow  ts ON ts.idShow  = e.idShow
                    WHERE  LOWER(f.strFilename) = LOWER(?)
                    LIMIT  1
                """, (filename,))
                row = cur.fetchone()
                if row:
                    result: dict[str, Any] = {
                        **_EMPTY_DB,
                        "title":    row["ep_title"]   or "",
                        "tv_show":  row["show_title"] or "",
                        "season":   row["season_num"] or 0,
                        "episode":  row["episode_num"] or 0,
                        "tvshowid": row["idShow"],
                    }
                    # Fetch all relevant art for episode + show, then pick by mode.
                    cur.execute(
                        "SELECT media_type || '.' || type AS key, url FROM art"
                        " WHERE (media_id=? AND media_type='episode' AND type IN ('thumb','fanart'))"
                        "    OR (media_id=? AND media_type='tvshow'  AND type IN ('poster','fanart'))",
                        (row["idEpisode"], row["idShow"]),
                    )
                    ep_art = {r["key"]: r["url"] for r in cur.fetchall()}
                    ep_thumb    = ep_art.get("episode.thumb",  "")
                    ep_fanart   = ep_art.get("episode.fanart", "")
                    show_poster = ep_art.get("tvshow.poster",  "")
                    show_fanart = ep_art.get("tvshow.fanart",  "")
                    if episode_art_mode == "thumb":
                        ep_url = ep_thumb or show_poster or ep_fanart or show_fanart
                    elif episode_art_mode == "season.poster":
                        # season.poster not stored separately here → use show poster
                        ep_url = show_poster or ep_thumb or ep_fanart or show_fanart
                    elif episode_art_mode == "fanart":
                        ep_url = ep_fanart or show_fanart or show_poster or ep_thumb
                    else:  # "poster" → tvshow poster
                        ep_url = show_poster or ep_thumb or ep_fanart or show_fanart
                    if ep_url:
                        result["artwork_url"] = self._image_url(ep_url)
                    return result

                # ── Movie ─────────────────────────────────────────────────
                cur.execute("""
                    SELECT m.idMovie,
                           m.c00                   AS title,
                           CAST(m.c07 AS INTEGER)  AS year
                    FROM   movie m
                    JOIN   files f ON f.idFile = m.idFile
                    WHERE  LOWER(f.strFilename) = LOWER(?)
                    LIMIT  1
                """, (filename,))
                row = cur.fetchone()
                if row:
                    result = {
                        **_EMPTY_DB,
                        "title": row["title"] or "",
                        "year":  row["year"]  or 0,
                    }
                    cur.execute(
                        "SELECT type, url FROM art"
                        " WHERE media_id=? AND media_type='movie'"
                        "   AND type IN ('poster','thumb','fanart')",
                        (row["idMovie"],),
                    )
                    mv_art = {r["type"]: r["url"] for r in cur.fetchall()}
                    mv_poster = mv_art.get("poster", "")
                    mv_thumb  = mv_art.get("thumb",  "")
                    mv_fanart = mv_art.get("fanart", "")
                    if movie_art_mode == "fanart":
                        mv_url = mv_fanart or mv_poster or mv_thumb
                    elif movie_art_mode == "thumb":
                        mv_url = mv_thumb or mv_poster or mv_fanart
                    else:  # "poster"
                        mv_url = mv_poster or mv_thumb or mv_fanart
                    if mv_url:
                        result["artwork_url"] = self._image_url(mv_url)
                    return result

            finally:
                conn.close()

        except Exception as exc:
            _LOG.debug("Kodi DB fallback error: %s", exc)

        return None

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

    @staticmethod
    def _norm_path(p: str) -> str:
        """
        Normalise a path for equality comparison across smb:// and UNC forms.

        ``smb://HOST/share/ep.mkv`` and ``\\\\HOST\\share\\ep.mkv`` both
        become ``//host/share/ep.mkv`` so they compare equal regardless of
        whether the path came from Kodi's library (smb://) or Windows/MPC-HC
        (UNC).
        """
        if p.startswith("smb://"):
            p = "//" + p[6:]
        return p.replace("\\", "/").lower()

    async def find_library_item(self, filepath: str) -> tuple[str, dict] | None:
        """
        Look up *filepath* in Kodi's video library.

        Tries movies first, then TV episodes.  Matching uses the basename
        for the API filter (one call per media type) and confirms the full
        path with normalised slashes.  Both smb:// (Kodi library) and UNC
        (Windows/MPC-HC) paths are normalised before comparison so they
        always match.

        Returns *(media_type, item_dict)* where *media_type* is ``"movie"``
        or ``"episode"`` and *item_dict* is the raw Kodi item (contains
        ``movieid``/``episodeid``, ``file``, ``resume``), or ``None`` if
        not found.
        """
        import os
        filename = os.path.basename(filepath)
        norm = self._norm_path(filepath)

        for method, list_key, media_type in (
            ("VideoLibrary.GetMovies",   "movies",   "movie"),
            ("VideoLibrary.GetEpisodes", "episodes", "episode"),
        ):
            result = await self._call(method, {
                "properties": ["file", "resume"],
                "filter": {"field": "filename", "operator": "is", "value": filename},
            })
            for item in (result or {}).get(list_key, []):
                if self._norm_path(item.get("file", "")) == norm:
                    _LOG.debug("find_library_item: %s → %s id=%s",
                               filename, media_type,
                               item.get("movieid") or item.get("episodeid"))
                    return media_type, item

        _LOG.debug("find_library_item: %s not in Kodi library", filename)
        return None

    async def get_resume_position(self, filepath: str) -> float:
        """
        Return the stored Kodi resume position for *filepath* in seconds,
        or ``0.0`` if no resume point is stored or the file is not in the
        library.
        """
        found = await self.find_library_item(filepath)
        if found is None:
            return 0.0
        _, item = found
        pos = float((item.get("resume") or {}).get("position", 0))
        _LOG.info("get_resume_position: %s → %.1f s",
                  filepath.split("\\")[-1].split("/")[-1], pos)
        return pos

    async def set_resume_position(
        self,
        media_type: str,
        media_id: int,
        position: float,
        total: float,
    ) -> bool:
        """
        Store *position* as Kodi's resume point for a movie or episode.

        Parameters
        ----------
        media_type : ``"movie"`` or ``"episode"``
        media_id   : Kodi library item ID
        position   : Current playback position in seconds
        total      : Total duration in seconds (shown in Kodi's resume UI)
        """
        if media_type == "movie":
            method = "VideoLibrary.SetMovieDetails"
            params: dict = {"movieid": media_id,
                            "resume": {"position": position, "total": total}}
        else:
            method = "VideoLibrary.SetEpisodeDetails"
            params = {"episodeid": media_id,
                      "resume": {"position": position, "total": total}}
        result = await self._call(method, params)
        if result is not None:
            _LOG.info("set_resume_position: %s id=%d → %.1f s / %.1f s",
                      media_type, media_id, position, total)
            return True
        _LOG.warning("set_resume_position: %s id=%d failed", media_type, media_id)
        return False

    async def reset_watched(self, media_type: str, media_id: int) -> bool:
        """
        Reset watched status to unwatched (playcount = 0).

        Called after MPC-HC stops when the film was not finished.  Kodi
        auto-marks any file as watched when an external player process exits,
        so we need to undo that explicitly.
        """
        if media_type == "movie":
            method = "VideoLibrary.SetMovieDetails"
            params: dict = {"movieid": media_id, "playcount": 0}
        else:
            method = "VideoLibrary.SetEpisodeDetails"
            params = {"episodeid": media_id, "playcount": 0}
        result = await self._call(method, params)
        if result is not None:
            _LOG.info("reset_watched: %s id=%d → playcount=0", media_type, media_id)
            return True
        _LOG.warning("reset_watched: %s id=%d failed", media_type, media_id)
        return False

    async def set_resume_and_reset_watched(
        self,
        media_type: str,
        media_id: int,
        position: float,
        total: float,
    ) -> bool:
        """
        Atomically set resume position AND reset playcount to 0 in a single
        API call.

        This avoids the race condition where two separate calls
        (reset_watched → set_resume_position) could be split by Kodi's own
        database writes, leaving the resume at 0.
        """
        if media_type == "movie":
            method = "VideoLibrary.SetMovieDetails"
            params: dict = {
                "movieid":  media_id,
                "playcount": 0,
                "resume":   {"position": position, "total": total},
            }
        else:
            method = "VideoLibrary.SetEpisodeDetails"
            params = {
                "episodeid": media_id,
                "playcount":  0,
                "resume":     {"position": position, "total": total},
            }
        result = await self._call(method, params)
        if result is not None:
            _LOG.info(
                "set_resume_and_reset_watched: %s id=%d → resume=%.1fs  playcount=0",
                media_type, media_id, position,
            )
            return True
        _LOG.warning("set_resume_and_reset_watched: %s id=%d failed", media_type, media_id)
        return False

    async def notify_library_update(self, media_type: str, media_id: int) -> None:
        """
        Notify Kodi to refresh its library UI for a specific item.

        Without this, the progress bar / watched state in the Kodi UI stays
        stale until the user navigates away and back.
        """
        await self._call("JSONRPC.NotifyAll", {
            "sender":  "kodi-mpchc-bridge",
            "message": "VideoLibrary.OnUpdate",
            "data":    {"item": {"type": media_type, "id": media_id}},
        })

    async def set_watched(self, media_type: str, media_id: int) -> bool:
        """
        Mark a movie or episode as watched in Kodi.

        Sets ``playcount = 1``, ``lastplayed = now``, and clears the resume
        point so Kodi's "resume / play from start" dialog no longer appears.
        """
        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if media_type == "movie":
            method = "VideoLibrary.SetMovieDetails"
            params: dict = {
                "movieid":    media_id,
                "playcount":  1,
                "lastplayed": now,
                "resume":     {"position": 0.0, "total": 0.0},
            }
        else:
            method = "VideoLibrary.SetEpisodeDetails"
            params = {
                "episodeid":  media_id,
                "playcount":  1,
                "lastplayed": now,
                "resume":     {"position": 0.0, "total": 0.0},
            }
        result = await self._call(method, params)
        if result is not None:
            _LOG.info("set_watched: %s id=%d → playcount=1 lastplayed=%s",
                      media_type, media_id, now)
            return True
        _LOG.warning("set_watched: %s id=%d failed", media_type, media_id)
        return False

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
                    "showtitle", "season", "episode", "tvshowid", "rating",
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

        # Fetch season counts for TV episodes (one extra call, only when episode)
        if updates.get("media_type") == "episode" or updates.get("tv_show"):
            actual_item = item.get("item", item)
            tvshowid = actual_item.get("tvshowid", -1)
            cur_season = updates.get("season", 0)
            if tvshowid >= 0 and cur_season > 0:
                sc, ec = await self._fetch_season_counts(tvshowid, cur_season)
                updates["season_count"] = sc
                updates["episode_count"] = ec
                _LOG.info("Kodi episode counts: s%d/%d e%d/%d",
                          cur_season, sc, updates.get("episode", 0), ec)

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
        # season_count / episode_count are set by the caller (_sync_player or
        # get_file_info) after a _fetch_season_counts() call; not set here
        # because _build_state_update is synchronous.
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

        # Video stream info from streamdetails (populated by Kodi scraper)
        media = item.get("item", item)
        sd_video = (media.get("streamdetails") or {}).get("video", [])
        if sd_video:
            vs = sd_video[0]
            updates["video_width"] = vs.get("width", 0) or 0
            updates["video_height"] = vs.get("height", 0) or 0
            # NOTE: vs["duration"] is the TOTAL film duration in seconds, NOT frame rate.
            # Kodi JSON-RPC does not expose FPS via streamdetails; leave 0 so the MKV
            # parser value (set by MPC-HC path) is not overwritten with nonsense.
            updates["video_codec"] = vs.get("codec", "") or ""
            # hdrtype is present in Kodi 20+ ("dolbyvision", "hdr10", "hlg", "")
            hdr_raw = (vs.get("hdrtype") or "").lower()
            if hdr_raw in ("hdr10", "hdr"):
                updates["hdr"] = "HDR10"
            elif hdr_raw == "dolbyvision":
                updates["hdr"] = "DV"
            elif hdr_raw == "hlg":
                updates["hdr"] = "HLG"
            else:
                updates["hdr"] = ""

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
                "artwork_url": "",
                "title": "",
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
