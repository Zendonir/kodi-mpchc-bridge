"""
Kodi media browser for external remotes (UC Remote integration).

Exposes Kodi favourites, PVR (Live TV / Radio) channels and installed
video / music add-ons as a simple folder tree:

    root
    ├── favourites                    Kodi favourites (Favourites.GetFavourites)
    ├── pvr/tv                        TV channel groups
    │   └── pvr/tv/<groupid>          channels of a group (with Now/Next EPG)
    ├── pvr/radio                     Radio channel groups
    │   └── pvr/radio/<groupid>
    ├── addons/video                  installed video add-ons
    └── addons/audio                  installed music add-ons

Every item carries an ``id``; folders are browsed with that id, playable
items are started via :meth:`KodiBrowser.play`.  Playable ids:

    channel/<channelid>               PVR channel      → Player.Open
    addon/<addonid>                   add-on           → Addons.ExecuteAddon
    file/<path>                       media favourite  → Player.Open
    window/<window>/<parameter>       window favourite → GUI.ActivateWindow

Empty or unavailable roots (no PVR backend, no favourites …) are hidden.
Ids longer than 255 characters are skipped — the UC Remote rejects them.
"""

from __future__ import annotations

import asyncio
import logging
import re
import urllib.parse
from typing import Any

from bridge.i18n import T
from bridge.state import strip_kodi_formatting

_LOG = logging.getLogger(__name__)

# UC Remote limits media ids and subtitles to 255 characters.
MAX_ID_LEN = 255
MAX_TEXT_LEN = 255
_IMAGE_CACHE_SIZE = 200

_CHANNEL_TYPES = ("tv", "radio")
_ADDON_TYPES = {"video": "xbmc.addon.video", "audio": "xbmc.addon.audio"}

# Script favourites look like RunScript("script.foo") / RunAddon(plugin.bar)
_RUN_ADDON_RE = re.compile(r"Run(?:Script|Addon|Plugin)\(\s*\"?([A-Za-z0-9_.\-]+)", re.IGNORECASE)


def _clip(text: str | None) -> str | None:
    """Clip *text* to the UC Remote's 255-character label limit."""
    if not text:
        return None
    if len(text) > MAX_TEXT_LEN:
        return text[: MAX_TEXT_LEN - 3].rstrip() + "..."
    return text


def _item(
    item_id: str,
    title: str,
    kind: str,
    *,
    subtitle: str | None = None,
    thumbnail: str | None = None,
    can_play: bool = False,
    can_browse: bool = False,
) -> dict[str, Any]:
    return {
        "id": item_id,
        "title": _clip(strip_kodi_formatting(title)) or item_id,
        "subtitle": _clip(strip_kodi_formatting(subtitle)) if subtitle else None,
        "kind": kind,
        "thumbnail": thumbnail,
        "can_play": can_play,
        "can_browse": can_browse,
    }


def _folder(item_id: str, title: str, items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"id": item_id, "title": title, "items": items or []}


class KodiBrowser:
    """Builds browse listings from Kodi JSON-RPC and starts playback."""

    def __init__(self, kodi) -> None:
        self._kodi = kodi
        # Small LRU-ish cache for thumbnails: kodi art path → (bytes, content type)
        self._image_cache: dict[str, tuple[bytes, str]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def browse(self, item_id: str | None) -> dict[str, Any] | None:
        """Return the folder listing for *item_id*, or ``None`` if unknown."""
        item_id = (item_id or "root").strip("/") or "root"
        parts = item_id.split("/")

        if item_id == "root":
            return await self._root()
        if item_id == "favourites":
            return _folder(item_id, T("browse_favourites"), await self._favourites())
        if parts[0] == "pvr" and len(parts) >= 2 and parts[1] in _CHANNEL_TYPES:
            ctype = parts[1]
            title = T("browse_live_tv") if ctype == "tv" else T("browse_radio")
            if len(parts) == 2:
                return _folder(item_id, title, await self._channel_groups(ctype))
            return _folder(item_id, title, await self._channels(ctype, parts[2]))
        if parts[0] == "addons" and len(parts) == 2 and parts[1] in _ADDON_TYPES:
            title = T("browse_video_addons") if parts[1] == "video" else T("browse_music_addons")
            return _folder(item_id, title, await self._addons(parts[1]))
        return None

    async def play(self, item_id: str) -> bool:
        """Start the playable item *item_id*. Returns True on success."""
        kind, _, rest = (item_id or "").partition("/")
        if not rest:
            return False
        if kind == "channel":
            try:
                channel_id = int(rest)
            except ValueError:
                return False
            return await self._ok("Player.Open", {"item": {"channelid": channel_id}})
        if kind == "addon":
            return await self._ok("Addons.ExecuteAddon", {"addonid": rest, "wait": False})
        if kind == "file":
            return await self._ok("Player.Open", {"item": {"file": rest}})
        if kind == "window":
            window, _, param = rest.partition("/")
            params: dict[str, Any] = {"window": window}
            if param:
                params["parameters"] = [param]
            return await self._ok("GUI.ActivateWindow", params)
        return False

    async def image(self, kodi_url: str) -> tuple[bytes, str] | None:
        """Fetch a thumbnail referenced by a browse item (via Kodi's image proxy)."""
        if not kodi_url:
            return None
        cached = self._image_cache.get(kodi_url)
        if cached:
            return cached
        result = await self._kodi.fetch_artwork_bytes(self._kodi.image_url(kodi_url))
        if result:
            if len(self._image_cache) >= _IMAGE_CACHE_SIZE:
                self._image_cache.pop(next(iter(self._image_cache)))
            self._image_cache[kodi_url] = result
        return result

    # ------------------------------------------------------------------
    # Listings
    # ------------------------------------------------------------------
    async def _root(self) -> dict[str, Any]:
        favs, tv, radio, video, audio = await asyncio.gather(
            self._favourites(),
            self._channel_groups("tv"),
            self._channel_groups("radio"),
            self._addons("video"),
            self._addons("audio"),
        )
        items: list[dict[str, Any]] = []
        for item_id, title, content in (
            ("favourites", T("browse_favourites"), favs),
            ("pvr/tv", T("browse_live_tv"), tv),
            ("pvr/radio", T("browse_radio"), radio),
            ("addons/video", T("browse_video_addons"), video),
            ("addons/audio", T("browse_music_addons"), audio),
        ):
            if content:
                items.append(_item(item_id, title, "folder", can_browse=True))
        return _folder("root", "Kodi", items)

    async def _favourites(self) -> list[dict[str, Any]]:
        result = await self._kodi.rpc(
            "Favourites.GetFavourites",
            {"properties": ["window", "windowparameter", "thumbnail", "path"]},
        )
        favs = (result or {}).get("favourites") if isinstance(result, dict) else None
        items: list[dict[str, Any]] = []
        for fav in favs or []:
            if not isinstance(fav, dict):
                continue
            title = urllib.parse.unquote(fav.get("title", "") or "")
            fav_type = fav.get("type", "")
            path = fav.get("path", "") or ""
            if fav_type == "media" and path:
                item_id = f"file/{path}"
            elif fav_type == "window" and fav.get("window"):
                param = fav.get("windowparameter", "") or ""
                item_id = f"window/{fav['window']}/{param}" if param else f"window/{fav['window']}"
            elif fav_type == "script" and (match := _RUN_ADDON_RE.search(path) or re.fullmatch(r"[\w.\-]+", path)):
                addon_id = match.group(1) if match.groups() else match.group(0)
                item_id = f"addon/{addon_id}"
            else:
                _LOG.debug("browse: unsupported favourite %r (type=%s)", title, fav_type)
                continue
            if len(item_id) > MAX_ID_LEN:
                _LOG.debug("browse: skipping favourite %r — id longer than %d chars", title, MAX_ID_LEN)
                continue
            items.append(
                _item(item_id, title, "favourite", thumbnail=self._thumb(fav.get("thumbnail")), can_play=True)
            )
        return items

    async def _channel_groups(self, ctype: str) -> list[dict[str, Any]]:
        result = await self._kodi.rpc("PVR.GetChannelGroups", {"channeltype": ctype})
        groups = (result or {}).get("channelgroups") if isinstance(result, dict) else None
        if not groups:
            return []
        # A single group (usually "All channels") adds a pointless level —
        # list its channels directly instead.
        if len(groups) == 1:
            return await self._channels(ctype, str(groups[0].get("channelgroupid", f"all{ctype}")))
        return [
            _item(
                f"pvr/{ctype}/{g.get('channelgroupid')}",
                g.get("label", "") or T("browse_all_channels"),
                "folder",
                can_browse=True,
            )
            for g in groups
            if isinstance(g, dict) and g.get("channelgroupid") is not None
        ]

    async def _channels(self, ctype: str, group: str) -> list[dict[str, Any]]:
        try:
            group_id: int | str = int(group)
        except ValueError:
            group_id = group if group in ("alltv", "allradio") else f"all{ctype}"
        params: dict[str, Any] = {
            "channelgroupid": group_id,
            "properties": ["thumbnail", "channelnumber", "hidden", "broadcastnow", "broadcastnext"],
        }
        result = await self._kodi.rpc("PVR.GetChannels", params)
        if result is None:
            # Older Kodi versions reject some properties — retry with the minimum.
            params["properties"] = ["thumbnail"]
            result = await self._kodi.rpc("PVR.GetChannels", params)
        channels = (result or {}).get("channels") if isinstance(result, dict) else None
        items: list[dict[str, Any]] = []
        for ch in channels or []:
            if not isinstance(ch, dict) or ch.get("hidden") or ch.get("channelid") is None:
                continue
            epg: list[str] = []
            now = strip_kodi_formatting((ch.get("broadcastnow") or {}).get("title"))
            nxt = strip_kodi_formatting((ch.get("broadcastnext") or {}).get("title"))
            if now:
                epg.append(f"{T('browse_now')}: {now}")
            if nxt:
                epg.append(f"{T('browse_next')}: {nxt}")
            label = ch.get("label", "") or ""
            number = ch.get("channelnumber")
            if number:
                label = f"{number}. {label}"
            items.append(
                _item(
                    f"channel/{ch['channelid']}",
                    label,
                    "channel",
                    subtitle=" | ".join(epg) or None,
                    thumbnail=self._thumb(ch.get("thumbnail")),
                    can_play=True,
                )
            )
        return items

    async def _addons(self, content: str) -> list[dict[str, Any]]:
        result = await self._kodi.rpc(
            "Addons.GetAddons",
            {"type": _ADDON_TYPES[content], "enabled": True, "properties": ["name", "thumbnail", "summary"]},
        )
        addons = (result or {}).get("addons") if isinstance(result, dict) else None
        items: list[dict[str, Any]] = []
        for addon in addons or []:
            addon_id = addon.get("addonid", "") if isinstance(addon, dict) else ""
            if not addon_id or len(f"addon/{addon_id}") > MAX_ID_LEN:
                continue
            items.append(
                _item(
                    f"addon/{addon_id}",
                    addon.get("name", "") or addon_id,
                    "addon",
                    subtitle=addon.get("summary") or None,
                    thumbnail=self._thumb(addon.get("thumbnail")),
                    can_play=True,
                )
            )
        items.sort(key=lambda i: i["title"].lower())
        return items

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _thumb(kodi_url: str | None) -> str | None:
        """Return a bridge-relative image URL for a Kodi art path."""
        if not kodi_url:
            return None
        return "/api/image?url=" + urllib.parse.quote(kodi_url, safe="")

    async def _ok(self, method: str, params: dict[str, Any]) -> bool:
        result = await self._kodi.rpc(method, params)
        ok = result == "OK" or result is True
        _LOG.info("browse: %s %s → %s", method, params, result)
        return ok
