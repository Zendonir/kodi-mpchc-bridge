"""
Kodi ↔ MPC-HC Bridge — Tray-Icon

Läuft ohne Fenster im Hintergrund.
Alle Aktionen über das Tray-Rechtsklick-Menü:
  • Test-Oberfläche öffnen  (Doppelklick)
  • Einstellungen…
  • Beenden
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox

import pystray
from PIL import Image as _PilImage, ImageDraw as _PilDraw

_LOG = logging.getLogger(__name__)

# ── Farben (nur für den Einstellungsdialog) ───────────────────────────────────
_C_BG       = "#1e1e2e"
_C_PANEL    = "#2a2a3e"
_C_ACCENT   = "#007acc"
_C_FG       = "#e0e0e0"
_C_FG_DIM   = "#888"
_C_ENTRY_BG = "#16162a"


# ─────────────────────────────────────────────────────────────────────────────
class TrayApp:
    """
    Tray-Icon-Anwendung ohne sichtbares Hauptfenster.
    Die Bridge selbst läuft als Asyncio-Loop im selben Prozess
    (gestartet von main.py in einem Daemon-Thread).
    """

    def __init__(self, port: int = 13590, config_dir: str = ".") -> None:
        self._port = port
        self._config_dir = config_dir
        self._tray_running = False   # letzter bekannter Bridge-Status

        # Versteckter tkinter-Root — nur für after()-Callbacks + Dialoge
        self._root = tk.Tk()
        self._root.withdraw()
        self._root.protocol("WM_DELETE_WINDOW", self._do_quit)

        self._settings_win: tk.Toplevel | None = None

        self._tray: pystray.Icon = self._create_tray()
        self._schedule_status()

    # ── Icon ─────────────────────────────────────────────────────────────────

    def _make_icon(self, running: bool) -> _PilImage.Image:
        sz = 64
        img = _PilImage.new("RGBA", (sz, sz), (0, 0, 0, 0))
        draw = _PilDraw.Draw(img)
        bg = (70, 185, 80, 255) if running else (100, 100, 100, 255)
        draw.ellipse([2, 2, sz - 3, sz - 3], fill=bg)
        w = (255, 255, 255, 210)
        draw.rectangle([13, 18, 22, 50], fill=w)   # linker Pfeiler
        draw.rectangle([42, 18, 51, 50], fill=w)   # rechter Pfeiler
        draw.rectangle([13, 26, 51, 35], fill=w)   # Querbalken
        return img

    def _create_tray(self) -> pystray.Icon:
        menu = pystray.Menu(
            pystray.MenuItem(
                "Test-Oberfläche öffnen",
                self._on_open_test,
                default=True,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Einstellungen…", self._on_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Beenden", self._on_quit),
        )
        icon = pystray.Icon(
            "kodi-mpchc-bridge",
            self._make_icon(False),
            "kodi-mpchc-bridge — wird gestartet…",
            menu,
        )
        threading.Thread(target=icon.run, daemon=True, name="tray").start()
        return icon

    def _update_tray_icon(self, running: bool) -> None:
        if running == self._tray_running:
            return
        self._tray_running = running
        try:
            self._tray.icon = self._make_icon(running)
            self._tray.title = (
                f"kodi-mpchc-bridge — läuft  (Port {self._port})"
                if running else
                f"kodi-mpchc-bridge — gestoppt  (Port {self._port})"
            )
        except Exception:
            pass

    # ── Status-Polling ────────────────────────────────────────────────────────

    def _check_running(self) -> bool:
        import urllib.request
        try:
            urllib.request.urlopen(
                f"http://localhost:{self._port}/api/state", timeout=1
            )
            return True
        except Exception:
            return False

    def _schedule_status(self) -> None:
        def _bg() -> None:
            running = self._check_running()
            try:
                self._root.after(0, lambda: self._update_tray_icon(running))
            except Exception:
                pass
        threading.Thread(target=_bg, daemon=True).start()
        self._root.after(5000, self._schedule_status)

    # ── Tray-Callbacks ────────────────────────────────────────────────────────

    def _on_open_test(self, icon=None, item=None) -> None:
        self._root.after(0, self._launch_test_client)

    def _on_settings(self, icon=None, item=None) -> None:
        self._root.after(0, self._show_settings)

    def _on_quit(self, icon=None, item=None) -> None:
        try:
            self._tray.stop()
        except Exception:
            pass
        self._root.after(0, self._do_quit)

    def _do_quit(self) -> None:
        try:
            self._root.destroy()
        except Exception:
            pass

    # ── Test-Client ───────────────────────────────────────────────────────────

    def _launch_test_client(self) -> None:
        try:
            if getattr(sys, "frozen", False):
                cmd = [sys.executable, "--test-client"]
            else:
                script = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "main.py"
                )
                cmd = [sys.executable, script, "--test-client"]
            subprocess.Popen(
                cmd,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )
        except Exception as exc:
            messagebox.showerror(
                "Fehler",
                f"Test-Oberfläche konnte nicht gestartet werden:\n{exc}",
            )

    # ── Einstellungen-Dialog ──────────────────────────────────────────────────

    def _show_settings(self) -> None:
        # Nur ein Dialog gleichzeitig
        if (
            self._settings_win is not None
            and self._settings_win.winfo_exists()
        ):
            self._settings_win.lift()
            self._settings_win.focus_force()
            return

        win = tk.Toplevel(self._root)
        win.title("Einstellungen — Kodi-MPC-HC Bridge")
        win.configure(bg=_C_BG)
        win.resizable(False, False)
        win.attributes("-topmost", True)
        self._settings_win = win

        cfg = None
        cfg_mgr = None
        try:
            from bridge.config import ConfigManager
            cfg_mgr = ConfigManager(self._config_dir)
            cfg = cfg_mgr.cfg
        except Exception:
            pass

        vars_: dict[str, tk.StringVar] = {}

        def _section(title: str) -> tk.Frame:
            tk.Label(
                win, text=f"  {title}",
                bg=_C_ACCENT, fg="white",
                font=("Segoe UI", 9, "bold"), anchor="w", padx=4, pady=3,
            ).pack(fill="x", padx=12, pady=(10, 0))
            f = tk.Frame(win, bg=_C_PANEL)
            f.pack(fill="x", padx=12)
            f.columnconfigure(1, weight=1)
            return f

        def _row(
            parent: tk.Frame, label: str, key: str,
            default: str, show: str = "", row: int = 0,
        ) -> None:
            tk.Label(
                parent, text=label + ":", bg=_C_PANEL, fg=_C_FG_DIM,
                font=("Segoe UI", 9), anchor="w", width=18,
            ).grid(row=row, column=0, sticky="w", padx=(10, 6), pady=4)
            var = tk.StringVar(value=default)
            vars_[key] = var
            tk.Entry(
                parent, textvariable=var, show=show,
                bg=_C_ENTRY_BG, fg=_C_FG, insertbackground=_C_FG,
                relief="flat", font=("Segoe UI", 10),
                highlightthickness=1, highlightcolor=_C_ACCENT,
                highlightbackground="#444", width=26,
            ).grid(row=row, column=1, sticky="ew", padx=(0, 10), pady=4)

        kf = _section("Kodi-Verbindung")
        _row(kf, "Host",             "kodi_host",     cfg.kodi_host       if cfg else "localhost", row=0)
        _row(kf, "HTTP-Port",        "kodi_port",     str(cfg.kodi_port)  if cfg else "8080",      row=1)
        _row(kf, "WebSocket-Port",   "kodi_ws_port",  str(cfg.kodi_ws_port) if cfg else "9090",    row=2)
        _row(kf, "Benutzername",     "kodi_username", cfg.kodi_username   if cfg else "",           row=3)
        _row(kf, "Passwort",         "kodi_password", cfg.kodi_password   if cfg else "", "*",      row=4)

        sf = _section("Bridge-Server")
        _row(sf, "MPC-HC Port",  "mpchc_port",  str(cfg.mpchc_port)  if cfg else "13579", row=0)
        _row(sf, "Bridge-Port",  "server_port", str(cfg.server_port) if cfg else "13590", row=1)

        tk.Label(
            win,
            text="  Benutzername/Passwort leer lassen wenn Kodi keine Authentifizierung verwendet.",
            bg=_C_BG, fg=_C_FG_DIM, font=("Segoe UI", 8), anchor="w",
        ).pack(fill="x", padx=14, pady=(6, 0))

        btn_frame = tk.Frame(win, bg=_C_BG)
        btn_frame.pack(fill="x", padx=12, pady=10)

        def _save() -> None:
            if not cfg_mgr:
                messagebox.showerror("Fehler", "Config-Manager nicht verfügbar.", parent=win)
                return
            data: dict = {}
            for key, var in vars_.items():
                val = var.get().strip()
                if key in ("kodi_port", "kodi_ws_port", "mpchc_port", "server_port"):
                    try:
                        data[key] = int(val)
                    except ValueError:
                        messagebox.showerror(
                            "Ungültige Eingabe",
                            f"{key}: Ganzzahl erwartet.",
                            parent=win,
                        )
                        return
                else:
                    data[key] = val
            cfg_mgr.update(data)
            messagebox.showinfo(
                "Gespeichert",
                "Einstellungen gespeichert.\n"
                "Bridge neu starten (Beenden → erneut öffnen) damit die\n"
                "neuen Werte aktiv werden.",
                parent=win,
            )
            win.destroy()

        tk.Button(
            btn_frame, text="💾  Speichern", command=_save,
            bg=_C_ACCENT, fg="white",
            activebackground="#005a9e", activeforeground="white",
            relief="flat", cursor="hand2",
            font=("Segoe UI", 9), padx=14, pady=6,
        ).pack(side="right", padx=(6, 0))

        tk.Button(
            btn_frame, text="Abbrechen", command=win.destroy,
            bg="#333355", fg="white",
            activebackground="#4444aa", activeforeground="white",
            relief="flat", cursor="hand2",
            font=("Segoe UI", 9), padx=14, pady=6,
        ).pack(side="right")

        # Fenster zentrieren
        win.update_idletasks()
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    # ── Mainloop ──────────────────────────────────────────────────────────────

    def run(self) -> None:
        self._root.mainloop()


# ─────────────────────────────────────────────────────────────────────────────

def main(port: int = 13590, config_dir: str = ".") -> None:
    logging.basicConfig(level=logging.INFO)
    TrayApp(port=port, config_dir=config_dir).run()
