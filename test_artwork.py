# -*- coding: utf-8 -*-
"""
Artwork Resolution Test Script
================================
Tests the full artwork lookup chain: image:// decode → Textures13.db → local file.

Paste any art URLs from the bridge log (FileInfo [1/4] art dict) into ART_URLS below,
then run with:  python test_artwork.py

The script shows exactly which URLs are cached locally and which need HTTP download.
"""

import os
import sqlite3
import glob
import urllib.parse

# ── Paste art URLs here (from the bridge log's FileInfo [1/4] output) ─────────
ART_URLS: dict[str, str] = {
    "tvshow.poster":  "image://https%3a%2f%2fimage.tmdb.org%2ft%2fp%2foriginal%2fwcaDIAG1QdXQLRaj4vC1EFdBT2.jpg/",
    "season.poster":  "image://https%3a%2f%2fimage.tmdb.org%2ft%2fp%2foriginal%2fqQxJAVWIY0FI7dB9LVvtNLEjR2Y.jpg/",
    "thumb":          "image://https%3a%2f%2fimage.tmdb.org%2ft%2fp%2foriginal%2fzWgS4g1mHsz5RWdduf2U1qLFsMe.jpg/",
    "tvshow.fanart":  "image://https%3a%2f%2fimage.tmdb.org%2ft%2fp%2foriginal%2f8ZerYKvIaNUJZvAHXYTQu4qTwFw.jpg/",
    "season.banner":  "image://https%3a%2f%2fassets.fanart.tv%2ffanart%2fthe-100-588bc6bf5fa76.jpg/",
}

# ── Kodi paths ─────────────────────────────────────────────────────────────────
APPDATA       = os.environ.get("APPDATA", "")
TEXTURES_DB   = os.path.join(APPDATA, "Kodi", "userdata", "Database", "Textures13.db")
THUMBNAILS    = os.path.join(APPDATA, "Kodi", "userdata", "Thumbnails")
MV_DBS        = sorted(
    glob.glob(os.path.join(APPDATA, "Kodi", "userdata", "Database", "MyVideos*.db")),
    reverse=True,
)
MV_DB         = MV_DBS[0] if MV_DBS else None

SEP = "-" * 70


def decode_image_url(kodi_url: str) -> str:
    """
    Replicate _image_url() logic:
    image://https%3a%2f%2f.../ → https://...
    image://video@...          → keep as Kodi proxy input (returned unchanged here)
    """
    if not kodi_url.startswith("image://"):
        return kodi_url
    normalized = urllib.parse.unquote(kodi_url)          # image://https://...
    inner = normalized[len("image://"):].rstrip("/")
    if inner.startswith("https://") or inner.startswith("http://"):
        return inner
    # local / video thumbnail → return the normalized form for Textures lookup
    return normalized.rstrip("/")


def lookup_textures(url: str) -> str | None:
    """Return full local path from Textures13.db, or None."""
    if not os.path.isfile(TEXTURES_DB):
        return None
    candidates = [url, url.rstrip("/"), url + "/"]
    try:
        conn = sqlite3.connect(f"file:{TEXTURES_DB}?mode=ro", uri=True, timeout=2.0)
        try:
            for u in candidates:
                row = conn.execute(
                    "SELECT cachedurl FROM texture WHERE url=? LIMIT 1", (u,)
                ).fetchone()
                if row:
                    path = os.path.join(THUMBNAILS, row[0].replace("/", os.sep))
                    return path
        finally:
            conn.close()
    except Exception as exc:
        print(f"  ERROR querying Textures13: {exc}")
    return None


def lookup_textures_like(url: str) -> list[tuple[str, str]]:
    """Fuzzy search: find all Textures entries where url LIKE '%<fragment>%'."""
    fragment = url[-40:] if len(url) > 40 else url
    results = []
    try:
        conn = sqlite3.connect(f"file:{TEXTURES_DB}?mode=ro", uri=True, timeout=2.0)
        try:
            rows = conn.execute(
                "SELECT url, cachedurl FROM texture WHERE url LIKE ? LIMIT 5",
                (f"%{fragment}%",),
            ).fetchall()
            results = [(r[0], r[1]) for r in rows]
        finally:
            conn.close()
    except Exception as exc:
        print(f"  ERROR fuzzy search: {exc}")
    return results


def test_url(label: str, raw_url: str) -> None:
    print(f"\n{SEP}")
    print(f"  [{label}]")
    print(f"  RAW  : {raw_url}")

    decoded = decode_image_url(raw_url)
    print(f"  DEC  : {decoded}")

    # Exact lookup with decoded URL
    path = lookup_textures(decoded)
    if path:
        exists = os.path.isfile(path)
        size   = os.path.getsize(path) if exists else 0
        status = f"OK  {size:,} bytes" if exists else "CACHED but FILE MISSING"
        print(f"  PATH : {path}")
        print(f"  FILE : {status}")
        if exists and size > 0:
            print(f"  >>> ARTWORK READABLE - LOCAL CACHE HIT <<<")
    else:
        print(f"  PATH : (not in Textures13)")
        # Also try with the original raw URL
        path2 = lookup_textures(raw_url)
        if path2:
            exists2 = os.path.isfile(path2)
            print(f"  RAW lookup: {path2}  exists={exists2}")
        else:
            # Fuzzy search to understand the URL format stored in DB
            fuzzy = lookup_textures_like(decoded[-50:])
            if fuzzy:
                print(f"  FUZZY matches in Textures13:")
                for db_url, cached in fuzzy:
                    print(f"    DB url   : {db_url[:90]}")
                    print(f"    cachedurl: {cached}")
            else:
                print(f"  FUZZY: no match found either")


def show_textures_summary() -> None:
    print(f"\n{SEP}")
    print("  Textures13.db URL prefix summary:")
    try:
        conn = sqlite3.connect(f"file:{TEXTURES_DB}?mode=ro", uri=True, timeout=2.0)
        rows = conn.execute("""
            SELECT SUBSTR(url,1,35) as prefix, COUNT(*) as cnt
            FROM texture
            GROUP BY prefix
            ORDER BY cnt DESC
            LIMIT 12
        """).fetchall()
        conn.close()
        for r in rows:
            print(f"    {r[1]:5d}  {r[0]}")
    except Exception as exc:
        print(f"  ERROR: {exc}")


def check_myvideo_db_episode(filename: str) -> None:
    if not MV_DB:
        print("\n  No MyVideos*.db found")
        return
    print(f"\n{SEP}")
    print(f"  MyVideos DB: {os.path.basename(MV_DB)}")
    print(f"  Looking for episode filename: {filename!r}")
    try:
        conn = sqlite3.connect(f"file:{MV_DB}?mode=ro", uri=True, timeout=2.0)
        conn.row_factory = sqlite3.Row
        # Check if episode table has rows
        count = conn.execute("SELECT COUNT(*) FROM episode").fetchone()[0]
        print(f"  episode table rows: {count}")
        if count > 0:
            rows = conn.execute("""
                SELECT e.idEpisode, e.c00, e.c12, e.c13, e.idShow
                FROM episode e
                JOIN files f ON f.idFile=e.idFile
                WHERE LOWER(f.strFilename)=LOWER(?)
            """, (filename,)).fetchall()
            if rows:
                for r in rows:
                    print(f"  FOUND: ep={r['idEpisode']} show={r['idShow']} "
                          f"s{r['c12']}e{r['c13']} title={r['c00']}")
            else:
                print(f"  Not found in episode table")
        conn.close()
    except Exception as exc:
        print(f"  ERROR: {exc}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(SEP)
    print("  KODI ARTWORK RESOLUTION TEST")
    print(SEP)
    print(f"  APPDATA    : {APPDATA}")
    print(f"  Textures DB: {TEXTURES_DB}  exists={os.path.isfile(TEXTURES_DB)}")
    print(f"  Thumbnails : {THUMBNAILS}  exists={os.path.isdir(THUMBNAILS)}")
    print(f"  MyVideos DB: {MV_DB or '(none found)'}")

    show_textures_summary()

    print(f"\n{SEP}")
    print("  Testing art URL decoding + Textures13 lookup:")

    for label, raw_url in ART_URLS.items():
        test_url(label, raw_url)

    check_myvideo_db_episode("The 100 - 1x04 - Murphys Gesetz (4).mkv")

    print(f"\n{SEP}")
    print("  DONE")
    print(SEP)
