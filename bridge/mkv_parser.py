"""
Minimal EBML/MKV parser — extracts audio tracks, subtitle tracks, and chapters.

No external dependencies. Reads only the Segment Info, Tracks, and Chapters
elements near the beginning of the file (up to READ_LIMIT bytes).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Optional

READ_LIMIT = 4 * 1024 * 1024  # 4 MB

# ---------------------------------------------------------------------------
# EBML element IDs
# ---------------------------------------------------------------------------
_ID_EBML = 0x1A45DFA3
_ID_SEGMENT = 0x18538067
_ID_SEGMENT_INFO = 0x1549A966
_ID_TRACKS = 0x1654AE6B
_ID_TRACK_ENTRY = 0xAE
_ID_TRACK_NUMBER = 0xD7
_ID_TRACK_TYPE = 0x83
_ID_TRACK_NAME = 0x536E
_ID_CODEC_ID = 0x86
_ID_LANGUAGE = 0x22B59C
_ID_LANGUAGE_IETF = 0x22B59D
_ID_DEFAULT_DURATION = 0x23E383
_ID_FLAG_DEFAULT = 0x88
_ID_FLAG_FORCED = 0x55AA
_ID_AUDIO = 0xE1
_ID_CHANNELS = 0x9F
_ID_CHAPTERS = 0x1043A770
_ID_EDITION_ENTRY = 0x45B9
_ID_CHAPTER_ATOM = 0xB6
_ID_CHAPTER_UID = 0x73C4
_ID_CHAPTER_TIME_START = 0x91
_ID_CHAPTER_DISPLAY = 0x80
_ID_CHAPTER_STRING = 0x85
_ID_CHAPTER_HIDDEN = 0x98

# Track types
_TRACK_TYPE_VIDEO = 1
_TRACK_TYPE_AUDIO = 2
_TRACK_TYPE_SUBTITLE = 17

# ---------------------------------------------------------------------------
# Codec → short name maps
# ---------------------------------------------------------------------------
_AUDIO_CODEC_NAME: dict[str, str] = {
    "A_AC3": "DD",
    "A_EAC3": "DD+",
    "A_TRUEHD": "TrueHD",
    "A_DTS": "DTS",
    "A_DTS/MA": "DTS-MA",
    "A_DTS/HRA": "DTS-HRA",
    "A_VORBIS": "Vorbis",
    "A_OPUS": "Opus",
    "A_AAC": "AAC",
    "A_FLAC": "FLAC",
    "A_PCM/INT/LIT": "PCM",
    "A_PCM/INT/BIG": "PCM",
    "A_MPEG/L3": "MP3",
    "A_MPEG/L2": "MP2",
}

_CHANNELS_STR: dict[int, str] = {
    1: "1.0",
    2: "2.0",
    6: "5.1",
    7: "6.1",
    8: "7.1",
}

_SUB_CODEC_NAME: dict[str, str] = {
    "S_HDMV/PGS": "PGS",
    "S_VOBSUB": "VobSub",
    "S_TEXT/UTF8": "SRT",
    "S_TEXT/ASS": "ASS",
    "S_TEXT/SSA": "SSA",
    "S_DVBSUB": "DVB",
    "S_HDMV/TEXTST": "TextST",
}


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------
@dataclass
class AudioTrack:
    pos: int  # 0-based index as seen in MPC-HC
    language: str
    label: str
    codec: str
    channels: int
    forced: bool = False
    default: bool = False


@dataclass
class SubtitleTrack:
    pos: int
    language: str
    label: str
    codec: str
    forced: bool = False
    default: bool = False


@dataclass
class Chapter:
    pos: int  # 0-based
    name: str
    time_ms: int


@dataclass
class MkvTracks:
    audio: list[AudioTrack] = field(default_factory=list)
    subtitles: list[SubtitleTrack] = field(default_factory=list)
    chapters: list[Chapter] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Low-level EBML helpers
# ---------------------------------------------------------------------------
def _read_vint(data: bytes, pos: int) -> tuple[int, int]:
    """Parse EBML variable-length integer; return (value, new_pos)."""
    if pos >= len(data):
        raise EOFError("Unexpected end of data reading vint")
    first = data[pos]
    if first == 0:
        raise ValueError("Invalid EBML vint (leading byte is 0)")
    width = 1
    mask = 0x80
    while not (first & mask):
        width += 1
        mask >>= 1
    value = first & (mask - 1)
    for i in range(1, width):
        if pos + i >= len(data):
            raise EOFError("Unexpected end of data reading vint bytes")
        value = (value << 8) | data[pos + i]
    return value, pos + width


def _read_element_id(data: bytes, pos: int) -> tuple[int, int]:
    """Parse EBML element ID; return (id, new_pos)."""
    if pos >= len(data):
        raise EOFError("Unexpected end of data reading element ID")
    first = data[pos]
    if first & 0x80:
        return first, pos + 1
    elif first & 0x40:
        return struct.unpack_from(">H", data, pos)[0], pos + 2
    elif first & 0x20:
        val = struct.unpack_from(">I", data, pos)[0] & 0x00FFFFFF
        return (data[pos] << 16) | (data[pos + 1] << 8) | data[pos + 2], pos + 3
    elif first & 0x10:
        return struct.unpack_from(">I", data, pos)[0], pos + 4
    else:
        raise ValueError(f"Invalid EBML element ID at {pos}: 0x{first:02x}")


def _read_uint(data: bytes, pos: int, size: int) -> int:
    value = 0
    for i in range(size):
        value = (value << 8) | data[pos + i]
    return value


def _read_string(data: bytes, pos: int, size: int) -> str:
    return data[pos : pos + size].decode("utf-8", errors="replace").rstrip("\x00")


def _iter_children(data: bytes, start: int, end: int):
    """Yield (element_id, data_start, data_end) for children in [start, end)."""
    pos = start
    while pos < end:
        try:
            eid, pos = _read_element_id(data, pos)
            esize, pos = _read_vint(data, pos)
        except (EOFError, ValueError, struct.error):
            break
        if esize == 0x00FFFFFFFFFFFFFF:
            # unknown size — skip rest
            break
        yield eid, pos, pos + esize
        pos += esize


# ---------------------------------------------------------------------------
# Language normalisation
# ---------------------------------------------------------------------------
def _normalise_lang(lang: str) -> str:
    """Map ISO-639-2B codes to common 3-letter uppercase tags."""
    lang = lang.strip().lower()
    _MAP = {
        "ger": "GER",
        "deu": "GER",
        "de": "GER",
        "eng": "ENG",
        "en": "ENG",
        "fre": "FRE",
        "fra": "FRE",
        "fr": "FRE",
        "spa": "SPA",
        "es": "SPA",
        "ita": "ITA",
        "it": "ITA",
        "jpn": "JPN",
        "ja": "JPN",
        "chi": "CHI",
        "zho": "CHI",
        "zh": "CHI",
        "rus": "RUS",
        "ru": "RUS",
        "por": "POR",
        "pt": "POR",
        "dut": "DUT",
        "nld": "DUT",
        "nl": "DUT",
        "und": "UND",
        "": "UND",
    }
    return _MAP.get(lang, lang.upper()[:3])


# ---------------------------------------------------------------------------
# Audio label builder
# ---------------------------------------------------------------------------
def _audio_label(track_name: str, codec_id: str, channels: int, language: str) -> str:
    lang = _normalise_lang(language)
    codec = _AUDIO_CODEC_NAME.get(codec_id, codec_id.split("/")[0].replace("A_", ""))
    ch = _CHANNELS_STR.get(channels, f"{channels}ch" if channels > 0 else "")

    # Atmos detection via track name
    atmos = "Atmos" if "atmos" in track_name.lower() else ""

    parts = [lang]
    if ch:
        parts.append(ch)
    if codec:
        parts.append(codec)
    if atmos:
        parts.append(atmos)
    return " ".join(parts)


def _subtitle_label(track_name: str, codec_id: str, language: str, forced: bool) -> str:
    lang = _normalise_lang(language)
    codec = _SUB_CODEC_NAME.get(codec_id, codec_id.split("/")[-1])

    parts = [lang]
    if forced:
        parts.append("Forced")
    if codec:
        parts.append(codec)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Track parsers
# ---------------------------------------------------------------------------
def _parse_track_entry(data: bytes, start: int, end: int) -> Optional[tuple]:
    """
    Parse a TrackEntry element.
    Returns (track_number, track_type, name, codec_id, language, channels, default, forced)
    or None on error.
    """
    track_number = 0
    track_type = 0
    name = ""
    codec_id = ""
    language = ""
    language_ietf = ""
    channels = 0
    flag_default = 0
    flag_forced = 0

    for eid, ds, de in _iter_children(data, start, end):
        size = de - ds
        if eid == _ID_TRACK_NUMBER:
            track_number = _read_uint(data, ds, size)
        elif eid == _ID_TRACK_TYPE:
            track_type = _read_uint(data, ds, size)
        elif eid == _ID_TRACK_NAME:
            name = _read_string(data, ds, size)
        elif eid == _ID_CODEC_ID:
            codec_id = _read_string(data, ds, size)
        elif eid == _ID_LANGUAGE:
            language = _read_string(data, ds, size)
        elif eid == _ID_LANGUAGE_IETF:
            language_ietf = _read_string(data, ds, size)
        elif eid == _ID_FLAG_DEFAULT:
            flag_default = _read_uint(data, ds, size)
        elif eid == _ID_FLAG_FORCED:
            flag_forced = _read_uint(data, ds, size)
        elif eid == _ID_AUDIO:
            for aeid, ads, ade in _iter_children(data, ds, de):
                if aeid == _ID_CHANNELS:
                    channels = _read_uint(data, ads, ade - ads)

    lang = language_ietf if language_ietf else language
    return (track_number, track_type, name, codec_id, lang, channels, bool(flag_default), bool(flag_forced))


def _parse_chapter_atom(data: bytes, start: int, end: int) -> Optional[Chapter]:
    time_ns = 0
    name = ""
    hidden = False

    for eid, ds, de in _iter_children(data, start, end):
        size = de - ds
        if eid == _ID_CHAPTER_TIME_START:
            time_ns = _read_uint(data, ds, size)
        elif eid == _ID_CHAPTER_HIDDEN:
            hidden = bool(_read_uint(data, ds, size))
        elif eid == _ID_CHAPTER_DISPLAY:
            for ceid, cds, cde in _iter_children(data, ds, de):
                if ceid == _ID_CHAPTER_STRING:
                    name = _read_string(data, cds, cde - cds)

    if hidden:
        return None
    return Chapter(pos=0, name=name or "", time_ms=time_ns // 1_000_000)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def parse_mkv(path: str) -> MkvTracks:
    """
    Parse audio tracks, subtitle tracks and chapters from an MKV file.

    Reads at most READ_LIMIT bytes. Returns empty MkvTracks on any error.
    """
    try:
        with open(path, "rb") as fh:
            data = fh.read(READ_LIMIT)
    except OSError:
        return MkvTracks()

    result = MkvTracks()

    # Find Segment
    pos = 0
    segment_start = -1
    try:
        while pos < len(data):
            eid, pos = _read_element_id(data, pos)
            esize, pos = _read_vint(data, pos)
            if eid == _ID_SEGMENT:
                segment_start = pos
                break
            pos += esize
    except (EOFError, ValueError, struct.error):
        return result

    if segment_start < 0:
        return result

    # Iterate top-level segment children
    audio_pos = 0
    sub_pos = 0
    chapter_pos = 0

    for eid, ds, de in _iter_children(data, segment_start, min(len(data), segment_start + 32 * 1024 * 1024)):
        if eid == _ID_TRACKS:
            for teid, tds, tde in _iter_children(data, ds, de):
                if teid == _ID_TRACK_ENTRY:
                    parsed = _parse_track_entry(data, tds, tde)
                    if parsed is None:
                        continue
                    _tn, ttype, tname, codec_id, lang, channels, default, forced = parsed
                    if ttype == _TRACK_TYPE_AUDIO:
                        label = _audio_label(tname, codec_id, channels, lang)
                        result.audio.append(
                            AudioTrack(
                                pos=audio_pos,
                                language=_normalise_lang(lang),
                                label=label,
                                codec=codec_id,
                                channels=channels,
                                default=default,
                                forced=forced,
                            )
                        )
                        audio_pos += 1
                    elif ttype == _TRACK_TYPE_SUBTITLE:
                        label = _subtitle_label(tname, codec_id, lang, forced)
                        result.subtitles.append(
                            SubtitleTrack(
                                pos=sub_pos,
                                language=_normalise_lang(lang),
                                label=label,
                                codec=codec_id,
                                forced=forced,
                                default=default,
                            )
                        )
                        sub_pos += 1

        elif eid == _ID_CHAPTERS:
            for eid2, ds2, de2 in _iter_children(data, ds, de):
                if eid2 == _ID_EDITION_ENTRY:
                    for eid3, ds3, de3 in _iter_children(data, ds2, de2):
                        if eid3 == _ID_CHAPTER_ATOM:
                            ch = _parse_chapter_atom(data, ds3, de3)
                            if ch is not None:
                                ch.pos = chapter_pos
                                result.chapters.append(ch)
                                chapter_pos += 1
                    break  # use first edition only

    return result


def tracks_to_dicts(tracks: MkvTracks) -> tuple[list[dict], list[dict], list[dict]]:
    """Convert MkvTracks to plain dicts suitable for JSON serialisation."""
    audio = [
        {
            "pos": t.pos,
            "label": t.label,
            "language": t.language,
            "codec": t.codec,
            "channels": t.channels,
            "forced": t.forced,
            "default": t.default,
        }
        for t in tracks.audio
    ]
    subs = [
        {
            "pos": t.pos,
            "label": t.label,
            "language": t.language,
            "codec": t.codec,
            "forced": t.forced,
            "default": t.default,
        }
        for t in tracks.subtitles
    ]
    chapters = [
        {
            "pos": t.pos,
            "name": t.name,
            "time_ms": t.time_ms,
        }
        for t in tracks.chapters
    ]
    return audio, subs, chapters
