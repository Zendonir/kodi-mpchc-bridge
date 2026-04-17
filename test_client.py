"""
Bridge test client GUI.

Communicates with kodi-mpchc-bridge via the same protocol the UC Remote
integration uses:
  - WebSocket  ws://host:port/api/ws   → receives state_full / state_patch
  - HTTP POST  http://host:port/api/command  → sends commands

Run:  python test_client.py [--host HOST] [--port PORT]

Requirements: aiohttp (already in requirements.txt)

Language is detected from the OS UI locale automatically (EN/DE/FR/ES/IT).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import threading
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
import urllib.request
import urllib.error
import time
from typing import Any

import aiohttp

from bridge.i18n import T

# ---------------------------------------------------------------------------
# Async bridge client (runs on its own thread / event loop)
# ---------------------------------------------------------------------------
class AsyncBridgeClient:
    def __init__(self, host: str, port: int, on_state, on_log, on_connect):
        self._ws_url = f"ws://{host}:{port}/api/ws"
        self._cmd_url = f"http://{host}:{port}/api/command"
        self._on_state = on_state
        self._on_log = on_log
        self._on_connect = on_connect
        self._loop: asyncio.AbstractEventLoop | None = None
        self._session: aiohttp.ClientSession | None = None
        self._running = False

    def start(self):
        self._running = True
        t = threading.Thread(target=self._thread, daemon=True)
        t.start()

    def stop(self):
        self._running = False

    def send(self, cmd: str, value=None):
        """Thread-safe command send."""
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._post_cmd(cmd, value), self._loop)

    def _thread(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect_loop())

    async def _connect_loop(self):
        self._session = aiohttp.ClientSession()
        while self._running:
            try:
                self._on_log("Connecting\u2026")
                async with self._session.ws_connect(self._ws_url, heartbeat=30) as ws:
                    self._on_log("Connected \u2713")
                    self._on_connect(True)
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            self._on_state(data.get("data", {}), data.get("type") == "state_full")
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break
            except Exception as exc:
                self._on_log(f"Disconnected: {exc}")
            self._on_connect(False)
            if self._running:
                self._on_log("Reconnecting in 3s\u2026")
                await asyncio.sleep(3)
        if self._session:
            await self._session.close()

    async def _post_cmd(self, cmd: str, value=None):
        payload: dict[str, Any] = {"cmd": cmd}
        if value is not None:
            payload["value"] = value
        try:
            async with self._session.post(
                self._cmd_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=3),
            ) as resp:
                ok = resp.status == 200
                self._on_log(f"\u2192 {cmd}" + (f"={value}" if value is not None else "") + (" \u2713" if ok else " \u2717"))
        except Exception as exc:
            self._on_log(f"\u2192 {cmd} ERROR: {exc}")


# ---------------------------------------------------------------------------
# GUI colours
# ---------------------------------------------------------------------------
DARK_BG  = "#1e1e1e"
PANEL_BG = "#252526"
BTN_BG   = "#3c3c3c"
BTN_FG   = "#cccccc"
ACCENT   = "#007acc"
TEXT_FG  = "#cccccc"
DIM_FG   = "#888888"
OK_FG    = "#4ec94e"
ERR_FG   = "#f44747"


def _style_btn(btn: tk.Button, accent=False):
    btn.configure(
        bg=ACCENT if accent else BTN_BG,
        fg="white" if accent else BTN_FG,
        activebackground="#005a9e" if accent else "#505050",
        activeforeground="white",
        relief="flat",
        bd=0,
        padx=8,
        pady=4,
        cursor="hand2",
    )


class App(tk.Tk):
    def __init__(self, host: str, port: int):
        super().__init__()
        self._host = host
        self._port = port
        self._state: dict[str, Any] = {}
        self._connected = False

        self.title(T("tc_window_title"))
        self.configure(bg=DARK_BG)
        self.resizable(True, True)
        self.minsize(760, 520)

        self._mono  = tkfont.Font(family="Consolas",  size=9)
        self._bold  = tkfont.Font(family="Segoe UI",  size=10, weight="bold")
        self._small = tkfont.Font(family="Segoe UI",  size=9)
        self._large = tkfont.Font(family="Segoe UI",  size=13, weight="bold")

        self._build_ui()

        self._client = AsyncBridgeClient(
            host, port,
            on_state=self._on_state,
            on_log=self._on_log,
            on_connect=self._on_connect,
        )
        self._client.start()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        # Top bar: connection info
        top = tk.Frame(self, bg=PANEL_BG, pady=6)
        top.pack(fill="x", padx=0, pady=0)

        tk.Label(top, text=T("tc_bridge_lbl"), bg=PANEL_BG, fg=DIM_FG, font=self._small).pack(side="left", padx=(12, 4))
        self._addr_var = tk.StringVar(value=f"{self._host}:{self._port}")
        tk.Label(top, textvariable=self._addr_var, bg=PANEL_BG, fg=TEXT_FG, font=self._mono).pack(side="left")

        self._status_lbl = tk.Label(top, text=T("tc_disconnected"), bg=PANEL_BG, fg=ERR_FG, font=self._small)
        self._status_lbl.pack(side="left", padx=12)

        self._active_lbl = tk.Label(top, text="", bg=PANEL_BG, fg=ACCENT, font=self._bold)
        self._active_lbl.pack(side="left", padx=12)

        # Main area: left info + right controls
        main = tk.Frame(self, bg=DARK_BG)
        main.pack(fill="both", expand=True, padx=10, pady=8)
        main.columnconfigure(0, weight=2)
        main.columnconfigure(1, weight=3)
        main.rowconfigure(0, weight=1)

        self._build_info_panel(main)
        self._build_controls_panel(main)

        # Log at bottom
        self._build_log(self)

    def _lbl(self, parent, text, row, col, fg=DIM_FG, colspan=1, sticky="w"):
        tk.Label(parent, text=text, bg=PANEL_BG, fg=fg, font=self._small).grid(
            row=row, column=col, sticky=sticky, padx=(8, 4), pady=2
        )

    def _val(self, parent, var, row, col, colspan=1, fg=TEXT_FG, font=None):
        lbl = tk.Label(parent, textvariable=var, bg=PANEL_BG, fg=fg, font=font or self._small,
                       anchor="w", wraplength=260)
        lbl.grid(row=row, column=col, columnspan=colspan, sticky="w", padx=(0, 8), pady=2)
        return lbl

    def _build_info_panel(self, parent):
        frame = tk.LabelFrame(parent, text=T("tc_now_playing"), bg=PANEL_BG, fg=DIM_FG,
                              font=self._small, bd=1, relief="groove")
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        frame.columnconfigure(1, weight=1)

        self._v_state  = tk.StringVar(value="\u2014")
        self._v_title  = tk.StringVar(value="\u2014")
        self._v_artist = tk.StringVar(value="")
        self._v_album  = tk.StringVar(value="")
        self._v_type   = tk.StringVar(value="")
        self._v_pos    = tk.StringVar(value="0:00:00")
        self._v_dur    = tk.StringVar(value="0:00:00")
        self._v_vol    = tk.StringVar(value="0")
        self._v_muted  = tk.StringVar(value="")
        self._v_shuffle= tk.StringVar(value="")
        self._v_repeat = tk.StringVar(value="off")

        rows = [
            (T("tc_state_lbl"),   self._v_state),
            (T("tc_title_lbl"),   self._v_title),
            (T("tc_artist_lbl"),  self._v_artist),
            (T("tc_album_lbl"),   self._v_album),
            (T("tc_type_lbl"),    self._v_type),
            (T("tc_pos_lbl"),     self._v_pos),
            (T("tc_dur_lbl"),     self._v_dur),
            (T("tc_vol_lbl"),     self._v_vol),
            (T("tc_muted_lbl"),   self._v_muted),
            (T("tc_shuffle_lbl"), self._v_shuffle),
            (T("tc_repeat_lbl"),  self._v_repeat),
        ]
        for i, (lbl, var) in enumerate(rows):
            self._lbl(frame, lbl, i, 0)
            self._val(frame, var, i, 1)

        # Cover art
        cover_row = len(rows)
        self._lbl(frame, T("tc_cover_lbl"), cover_row, 0)
        self._artwork_label = tk.Label(
            frame, bg=PANEL_BG, fg=DIM_FG, font=self._small,
            text="\u2014", anchor="w", width=22, height=8,
        )
        self._artwork_label.grid(
            row=cover_row, column=1, sticky="w", padx=(0, 8), pady=4
        )
        self._img_ref = None
        self._current_art_url = ""

        # Progress bar
        self._progress = ttk.Progressbar(frame, orient="horizontal", mode="determinate")
        self._progress.grid(row=len(rows) + 1, column=0, columnspan=2, sticky="ew",
                            padx=8, pady=(4, 8))

        # Seek entry
        seek_row = len(rows) + 2
        self._lbl(frame, T("tc_seek_lbl"), seek_row, 0)
        self._seek_var = tk.StringVar(value="0")
        seek_entry = tk.Entry(frame, textvariable=self._seek_var, width=8,
                              bg=BTN_BG, fg=TEXT_FG, insertbackground=TEXT_FG,
                              relief="flat", font=self._mono)
        seek_entry.grid(row=seek_row, column=1, sticky="w", padx=(0, 4), pady=2)
        seek_entry.bind("<Return>", lambda e: self._cmd("seek", float(self._seek_var.get() or 0)))

        seek_btn = tk.Button(frame, text="Go", command=lambda: self._cmd("seek", float(self._seek_var.get() or 0)))
        _style_btn(seek_btn, accent=True)
        seek_btn.grid(row=seek_row, column=1, sticky="e", padx=(0, 8))

    def _build_controls_panel(self, parent):
        right = tk.Frame(parent, bg=DARK_BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)

        # --- Playback ---
        pb = tk.LabelFrame(right, text=T("tc_playback"), bg=PANEL_BG, fg=DIM_FG,
                           font=self._small, bd=1, relief="groove")
        pb.pack(fill="x", pady=(0, 5))

        row1 = tk.Frame(pb, bg=PANEL_BG)
        row1.pack(pady=6)
        for text, cmd in [
            ("\u23ee Prev",       "prev_chapter"),
            ("\u23ea Skip\u2212", "skip_backward"),
            ("\u23ef Play/Pause", "play_pause"),
            ("\u23e9 Skip+",      "skip_forward"),
            ("\u23ed Next",       "next_chapter"),
            ("\u23f9 Stop",       "stop"),
        ]:
            b = tk.Button(row1, text=text, command=lambda c=cmd: self._cmd(c))
            _style_btn(b, accent=(cmd == "play_pause"))
            b.pack(side="left", padx=3)

        row2 = tk.Frame(pb, bg=PANEL_BG)
        row2.pack(pady=(0, 6))
        for text, delta in [("\u25c1\u25c1 \u221215s", -15), ("\u25b7\u25b7 +15s", 15)]:
            b = tk.Button(row2, text=text, command=lambda d=delta: self._seek_relative(d))
            _style_btn(b)
            b.pack(side="left", padx=3)

        # --- Volume ---
        vol = tk.LabelFrame(right, text=T("tc_volume_panel"), bg=PANEL_BG, fg=DIM_FG,
                            font=self._small, bd=1, relief="groove")
        vol.pack(fill="x", pady=(0, 5))
        vrow = tk.Frame(vol, bg=PANEL_BG)
        vrow.pack(pady=6)
        for text, cmd in [
            ("\U0001f50a Vol\u2212", "volume_down"),
            ("\U0001f50a Vol+",      "volume_up"),
            ("\U0001f507 Mute",      "mute"),
        ]:
            b = tk.Button(vrow, text=text, command=lambda c=cmd: self._cmd(c))
            _style_btn(b)
            b.pack(side="left", padx=3)

        self._vol_slider = tk.Scale(vol, from_=0, to=100, orient="horizontal",
                                    bg=PANEL_BG, fg=TEXT_FG, troughcolor=BTN_BG,
                                    highlightthickness=0, command=self._on_vol_slide)
        self._vol_slider.pack(fill="x", padx=12, pady=(0, 6))

        # --- Tracks ---
        trk = tk.LabelFrame(right, text=T("tc_tracks_panel"), bg=PANEL_BG, fg=DIM_FG,
                            font=self._small, bd=1, relief="groove")
        trk.pack(fill="x", pady=(0, 5))
        trk.columnconfigure(1, weight=1)

        tk.Label(trk, text=T("tc_audio_lbl"), bg=PANEL_BG, fg=DIM_FG, font=self._small).grid(
            row=0, column=0, padx=(8, 4), pady=4, sticky="w")
        self._audio_var = tk.StringVar()
        self._audio_cb = ttk.Combobox(trk, textvariable=self._audio_var, state="readonly", width=40)
        self._audio_cb.grid(row=0, column=1, padx=(0, 8), pady=4, sticky="ew")
        self._audio_cb.bind("<<ComboboxSelected>>", self._on_audio_select)

        tk.Label(trk, text=T("tc_sub_lbl"), bg=PANEL_BG, fg=DIM_FG, font=self._small).grid(
            row=1, column=0, padx=(8, 4), pady=4, sticky="w")
        self._sub_var = tk.StringVar()
        self._sub_cb = ttk.Combobox(trk, textvariable=self._sub_var, state="readonly", width=40)
        self._sub_cb.grid(row=1, column=1, padx=(0, 8), pady=4, sticky="ew")
        self._sub_cb.bind("<<ComboboxSelected>>", self._on_sub_select)

        tk.Label(trk, text=T("tc_chapter_lbl"), bg=PANEL_BG, fg=DIM_FG, font=self._small).grid(
            row=2, column=0, padx=(8, 4), pady=4, sticky="w")
        self._ch_var = tk.StringVar()
        self._ch_cb = ttk.Combobox(trk, textvariable=self._ch_var, state="readonly", width=40)
        self._ch_cb.grid(row=2, column=1, padx=(0, 8), pady=4, sticky="ew")
        self._ch_cb.bind("<<ComboboxSelected>>", self._on_chapter_select)

        # --- Navigation ---
        nav = tk.LabelFrame(right, text=T("tc_nav_panel"), bg=PANEL_BG, fg=DIM_FG,
                            font=self._small, bd=1, relief="groove")
        nav.pack(fill="x", pady=(0, 5))
        nav_inner = tk.Frame(nav, bg=PANEL_BG)
        nav_inner.pack(pady=6)

        # D-pad grid
        dpad = tk.Frame(nav_inner, bg=PANEL_BG)
        dpad.pack(side="left", padx=10)
        for text, r, c, cmd in [
            ("\u2191",  0, 1, "navigate_up"),
            ("\u2190",  1, 0, "navigate_left"),
            ("OK",      1, 1, "navigate_select"),
            ("\u2192",  1, 2, "navigate_right"),
            ("\u2193",  2, 1, "navigate_down"),
        ]:
            b = tk.Button(dpad, text=text, width=4, command=lambda c=cmd: self._cmd(c))
            _style_btn(b, accent=(text == "OK"))
            b.grid(row=r, column=c, padx=2, pady=2)

        extra = tk.Frame(nav_inner, bg=PANEL_BG)
        extra.pack(side="left", padx=10)
        for text, cmd in [
            ("Back",     "navigate_back"),
            ("Home",     "navigate_home"),
            ("Menu",     "context_menu"),
            ("Info",     "show_info"),
            ("Kodi/Win", "kodi_windows"),
        ]:
            b = tk.Button(extra, text=text, command=lambda c=cmd: self._cmd(c))
            _style_btn(b)
            b.pack(anchor="w", pady=2, fill="x")

    def _build_log(self, parent):
        log_frame = tk.Frame(parent, bg=DARK_BG)
        log_frame.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(log_frame, text=T("tc_log_lbl"), bg=DARK_BG, fg=DIM_FG, font=self._small).pack(anchor="w")
        self._log_text = tk.Text(
            log_frame, height=5, bg="#111", fg=DIM_FG, font=self._mono,
            relief="flat", state="disabled", wrap="word",
        )
        self._log_text.pack(fill="x")

    # ------------------------------------------------------------------
    # Callbacks (called from async thread → schedule on Tk thread)
    # ------------------------------------------------------------------
    def _on_state(self, patch: dict, is_full: bool):
        self.after(0, self._apply_state, patch, is_full)

    def _on_log(self, msg: str):
        self.after(0, self._append_log, msg)

    def _on_connect(self, connected: bool):
        self._connected = connected
        self.after(0, self._update_status)

    # ------------------------------------------------------------------
    # Tk thread: state application
    # ------------------------------------------------------------------
    def _apply_state(self, patch: dict, is_full: bool):
        if is_full:
            self._state = patch
        else:
            self._state.update(patch)

        s = self._state

        active = s.get("active_player", "none")
        self._active_lbl.configure(
            text=f"[{active.upper()}]" if active != "none" else "",
            fg=ACCENT if active == "kodi" else ("#e89b3c" if active == "mpchc" else DIM_FG),
        )

        self._v_state.set(s.get("state", "\u2014"))
        self._v_title.set(s.get("title", "") or s.get("filepath", "").split("\\")[-1] or "\u2014")
        self._v_artist.set(s.get("artist", ""))
        self._v_album.set(s.get("album", ""))
        self._v_type.set(s.get("media_type", ""))

        pos = s.get("position", 0)
        dur = s.get("duration", 0)
        self._v_pos.set(_fmt_time(pos))
        self._v_dur.set(_fmt_time(dur))

        if dur > 0:
            self._progress["value"] = (pos / dur) * 100
        else:
            self._progress["value"] = 0

        vol = s.get("volume", 0)
        self._v_vol.set(str(vol))
        self._v_muted.set("\U0001f507" if s.get("muted") else "")
        self._v_shuffle.set("\U0001f500" if s.get("shuffle") else "")
        self._v_repeat.set(s.get("repeat", "off"))

        artwork = s.get("artwork_url", "")
        if artwork != self._current_art_url:
            self._current_art_url = artwork
            self._load_artwork_bg(artwork)

        if not self._vol_slider.identify(self._vol_slider.winfo_pointerx() - self._vol_slider.winfo_rootx(),
                                         self._vol_slider.winfo_pointery() - self._vol_slider.winfo_rooty()):
            self._vol_slider.set(vol)

        # Update track dropdowns
        if "audio_tracks" in patch or is_full:
            tracks = s.get("audio_tracks", [])
            labels = [f"{t['pos']}: {t['label']}" for t in tracks]
            self._audio_cb["values"] = labels
            cur = s.get("current_audio", 0)
            if labels and cur < len(labels):
                self._audio_var.set(labels[cur])

        if "subtitle_tracks" in patch or is_full:
            tracks = s.get("subtitle_tracks", [])
            off_label = f"-1: {T('tc_off')}"
            labels = [off_label] + [f"{t['pos']}: {t['label']}" for t in tracks]
            self._sub_cb["values"] = labels
            cur = s.get("current_subtitle", -1)
            if cur < 0:
                self._sub_var.set(off_label)
            elif cur < len(tracks):
                self._sub_var.set(f"{cur}: {tracks[cur]['label']}")

        if "chapters" in patch or is_full:
            chapters = s.get("chapters", [])
            labels = [
                f"{c['pos']}: {c['name'] if c['name'] else 'Chapter ' + str(c['pos'] + 1)}"
                for c in chapters
            ]
            self._ch_cb["values"] = labels
            cur = s.get("current_chapter", 0)
            if labels and cur < len(labels):
                self._ch_var.set(labels[cur])

    def _update_status(self):
        if self._connected:
            self._status_lbl.configure(text=T("tc_connected"), fg=OK_FG)
        else:
            self._status_lbl.configure(text=T("tc_disconnected"), fg=ERR_FG)

    def _append_log(self, msg: str):
        self._log_text.configure(state="normal")
        ts = time.strftime("%H:%M:%S")
        self._log_text.insert("end", f"[{ts}] {msg}\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _cmd(self, cmd: str, value=None):
        self._client.send(cmd, value)

    def _seek_relative(self, delta: float):
        current = self._state.get("position", 0)
        target = max(0, current + delta)
        self._cmd("seek", target)
        self._append_log(f"Seek to {_fmt_time(target)} ({delta:+.0f}s)")

    _vol_slide_after: str | None = None

    def _on_vol_slide(self, value):
        if self._vol_slide_after:
            self.after_cancel(self._vol_slide_after)
        self._vol_slide_after = self.after(300, self._commit_vol, int(float(value)))

    def _commit_vol(self, vol: int):
        self._cmd("set_volume", vol)

    def _on_audio_select(self, _event=None):
        sel = self._audio_var.get()
        if not sel:
            return
        pos = int(sel.split(":")[0])
        self._cmd("audio_track", pos)

    def _on_sub_select(self, _event=None):
        sel = self._sub_var.get()
        if not sel:
            return
        pos = int(sel.split(":")[0].replace("\u2212", "-"))
        self._cmd("subtitle_track", pos)

    def _on_chapter_select(self, _event=None):
        sel = self._ch_var.get()
        if not sel:
            return
        pos = int(sel.split(":")[0])
        chapters = self._state.get("chapters", [])
        for ch in chapters:
            if ch["pos"] == pos:
                self._cmd("seek", ch["time_ms"] / 1000.0)
                return

    # ------------------------------------------------------------------
    # Cover art
    # ------------------------------------------------------------------
    def _load_artwork_bg(self, url: str) -> None:
        if not url:
            self.after(0, self._set_artwork, None)
            return

        def _fetch():
            try:
                import urllib.request as _ur
                with _ur.urlopen(url, timeout=8) as resp:
                    data = resp.read()
                self.after(0, self._set_artwork, data)
            except Exception:
                self.after(0, self._set_artwork, None)

        threading.Thread(target=_fetch, daemon=True).start()

    def _set_artwork(self, data: bytes | None) -> None:
        if data is None:
            self._artwork_label.configure(image="", text="\u2014")
            self._img_ref = None
            return
        try:
            from PIL import Image, ImageTk
            import io
            img = Image.open(io.BytesIO(data))
            img.thumbnail((180, 180))
            photo = ImageTk.PhotoImage(img)
            self._artwork_label.configure(image=photo, text="", width=180, height=180)
            self._img_ref = photo
        except ImportError:
            self._artwork_label.configure(image="", text=T("tc_pillow_missing"))
        except Exception:
            self._artwork_label.configure(image="", text="\u2014")

    def _on_close(self):
        self._client.stop()
        self.destroy()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fmt_time(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(host: str = "localhost", port: int = 13590) -> None:
    app = App(host, port)
    style = ttk.Style(app)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("TCombobox", fieldbackground=BTN_BG, background=BTN_BG,
                    foreground=TEXT_FG, selectbackground=ACCENT)
    style.configure("Horizontal.TProgressbar", troughcolor=BTN_BG, background=ACCENT)
    app.mainloop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bridge test client")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=13590)
    args = parser.parse_args()
    main(args.host, args.port)
