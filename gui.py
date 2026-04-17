"""
Kodi ↔ MPC-HC Bridge — Manager GUI

Tabs: Einstellungen | System | Log
System-tray icon: schließen minimiert ins Tray, Rechtsklick öffnet Menü.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

import service

# pystray is optional — tray icon only shown when it is installed
try:
    import pystray
    from PIL import Image as _PilImage, ImageDraw as _PilDraw
    _TRAY_AVAILABLE = True
except ImportError:
    _TRAY_AVAILABLE = False

_LOG = logging.getLogger(__name__)

_PID_FILE = os.path.join(tempfile.gettempdir(), "kodi-mpchc-bridge.pid")
_FIREWALL_RULE = "Kodi-MPC-HC Bridge"

# ── colours ──────────────────────────────────────────────────────────────────
_C_BG       = "#1e1e2e"
_C_PANEL    = "#2a2a3e"
_C_ACCENT   = "#007acc"
_C_SUCCESS  = "#4caf50"
_C_WARN     = "#ff9800"
_C_ERROR    = "#f44336"
_C_FG       = "#e0e0e0"
_C_FG_DIM   = "#888"
_C_ENTRY_BG = "#16162a"
_C_BTN      = "#333355"
_C_BTN_HOV  = "#4444aa"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — Windows admin / subprocess
# ─────────────────────────────────────────────────────────────────────────────

def _run_hidden(cmd: list[str], timeout: int = 15) -> tuple[int, str]:
    """Run *cmd* silently, return (returncode, stdout+stderr)."""
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as exc:
        return -1, str(exc)


def _is_admin() -> bool:
    """Return True if the current process has admin/elevated privileges."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _elevate_ps_file(script_content: str) -> bool:
    """
    Write *script_content* to a temp .ps1 file and launch it elevated via UAC.
    Async — does NOT wait for completion.  Returns True if UAC accepted the launch.
    """
    if sys.platform != "win32":
        return False
    import ctypes, tempfile
    tf = tempfile.NamedTemporaryFile(
        suffix=".ps1", delete=False, mode="w", encoding="utf-8"
    )
    tf.write(script_content)
    tf.close()

    # Schedule cleanup after 60 s
    def _cleanup():
        import time
        time.sleep(60)
        try:
            os.unlink(tf.name)
        except OSError:
            pass
    threading.Thread(target=_cleanup, daemon=True).start()

    rc = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", "powershell.exe",
        f'-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{tf.name}"',
        None, 1,   # SW_SHOWNORMAL — UAC dialog is visible
    )
    return int(rc) > 32


def _elevate(exe: str, args: str) -> bool:
    """Launch *exe* with *args* via UAC elevation (for non-PS commands like sc.exe)."""
    if sys.platform != "win32":
        return False
    import ctypes
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, args, None, 1)
    return int(rc) > 32


def _exe_path() -> str:
    """Return the absolute path to the current executable or script."""
    if getattr(sys, "frozen", False):
        return sys.executable
    return f"{sys.executable} \"{os.path.abspath('main.py')}\""


# ─────────────────────────────────────────────────────────────────────────────
# Firewall helpers — PowerShell (handles rule names with spaces reliably)
# ─────────────────────────────────────────────────────────────────────────────

def firewall_rule_exists(port: int) -> bool:
    """Check via PowerShell Get-NetFirewallRule — no elevation needed for reading."""
    rc, out = _run_hidden([
        "powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
        f"if (Get-NetFirewallRule -DisplayName '{_FIREWALL_RULE}'"
        f" -ErrorAction SilentlyContinue) {{ 'EXISTS' }} else {{ 'NOT_FOUND' }}",
    ])
    return "EXISTS" in out


def _ps_fw_add(port: int) -> str:
    return (
        f'New-NetFirewallRule '
        f'-DisplayName "{_FIREWALL_RULE}" '
        f'-Direction Inbound -Action Allow -Protocol TCP '
        f'-LocalPort {port} -Profile Any -ErrorAction Stop'
    )


def _ps_fw_remove() -> str:
    return (
        f'Remove-NetFirewallRule '
        f'-DisplayName "{_FIREWALL_RULE}" '
        f'-ErrorAction SilentlyContinue'
    )


def firewall_add(port: int) -> tuple[bool, str]:
    if _is_admin():
        # Already elevated — run directly and get the real return code
        rc, out = _run_hidden(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _ps_fw_add(port)],
            timeout=20,
        )
        if rc == 0:
            return True, f"✅ Firewall-Regel für Port {port} erfolgreich hinzugefügt."
        return False, f"Fehler (rc={rc}): {out[:300]}"
    else:
        # Need UAC elevation — temp PS1 file + ShellExecuteW runas
        ok = _elevate_ps_file(_ps_fw_add(port))
        if ok:
            return True, f"Firewall-Regel für Port {port} wird hinzugefügt — UAC-Fenster bestätigen."
        return False, "Abgebrochen (UAC verweigert oder kein Admin)."


def firewall_remove() -> tuple[bool, str]:
    if _is_admin():
        rc, out = _run_hidden(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _ps_fw_remove()],
            timeout=20,
        )
        if rc == 0:
            return True, "✅ Firewall-Regel erfolgreich entfernt."
        return False, f"Fehler (rc={rc}): {out[:300]}"
    else:
        ok = _elevate_ps_file(_ps_fw_remove())
        if ok:
            return True, "Firewall-Regel wird entfernt — UAC-Fenster bestätigen."
        return False, "Abgebrochen."


# ─────────────────────────────────────────────────────────────────────────────
# Bridge process helpers
# ─────────────────────────────────────────────────────────────────────────────

def _bridge_running(port: int) -> bool:
    import urllib.request
    try:
        urllib.request.urlopen(f"http://localhost:{port}/api/state", timeout=1)
        return True
    except Exception:
        return False


def _start_bridge_proc(port: int) -> tuple[bool, str]:
    if _bridge_running(port):
        return True, "Bridge läuft bereits."
    # Kill anything on the port first
    service.kill_port(port)
    if getattr(sys, "frozen", False):
        cmd_parts = [sys.executable, "--headless"]
    else:
        cmd_parts = [sys.executable, os.path.abspath("main.py"), "--headless"]
    try:
        flags = 0
        if sys.platform == "win32":
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
        proc = subprocess.Popen(cmd_parts, creationflags=flags, close_fds=True)
        with open(_PID_FILE, "w") as f:
            f.write(str(proc.pid))
        return True, f"Bridge gestartet (PID {proc.pid})"
    except Exception as exc:
        return False, f"Fehler: {exc}"


def _stop_bridge_proc() -> tuple[bool, str]:
    try:
        with open(_PID_FILE) as f:
            pid = int(f.read().strip())
        subprocess.run(["taskkill", "/f", "/pid", str(pid)], capture_output=True)
        os.remove(_PID_FILE)
        return True, f"Bridge gestoppt (PID {pid})"
    except FileNotFoundError:
        return False, "Kein PID-File — Bridge läuft nicht."
    except Exception as exc:
        return False, f"Fehler: {exc}"


# ─────────────────────────────────────────────────────────────────────────────
# Logging handler
# ─────────────────────────────────────────────────────────────────────────────

class _GuiLogHandler(logging.Handler):
    def __init__(self, callback) -> None:
        super().__init__()
        self._cb = callback

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._cb(self.format(record))
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Main installer window
# ─────────────────────────────────────────────────────────────────────────────

class InstallerApp:
    def __init__(self) -> None:
        self._port = 13590
        self._load_config()
        self._tray: "pystray.Icon | None" = None  # type: ignore[name-defined]
        self._bridge_running_flag = False          # used to colour the tray icon

        self._root = tk.Tk()
        self._root.title("Kodi ↔ MPC-HC Bridge")
        self._root.configure(bg=_C_BG)
        self._root.resizable(True, True)
        self._root.minsize(600, 580)

        # Closing the window hides to tray instead of exiting
        self._root.protocol("WM_DELETE_WINDOW", self._hide_to_tray)

        self._build_ui()
        self._refresh_status()

        # Route logging to GUI
        self._log_handler = _GuiLogHandler(self._log)
        self._log_handler.setFormatter(
            logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
                              datefmt="%H:%M:%S")
        )
        logging.getLogger().addHandler(self._log_handler)

        # Periodic status refresh
        self._schedule_refresh()

        # System-tray icon (only when pystray is available)
        if _TRAY_AVAILABLE:
            self._create_tray()

    # ── config ───────────────────────────────────────────────────────────────

    def _load_config(self) -> None:
        try:
            from bridge.config import ConfigManager
            # Config liegt im Installationsverzeichnis (neben bridge.exe).
            # Im frozen-Modus zeigt __file__ auf den temp-Extraktionspfad —
            # sys.executable zeigt immer auf die echte .exe.
            if getattr(sys, "frozen", False):
                data_dir = os.path.dirname(sys.executable)
            else:
                data_dir = os.path.dirname(os.path.abspath(__file__))
            self._cfg_mgr = ConfigManager(data_dir)
            self._port = self._cfg_mgr.cfg.server_port
        except Exception:
            self._cfg_mgr = None

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Header (packed top → first)
        hdr = tk.Frame(self._root, bg=_C_ACCENT, height=56)
        hdr.pack(side="top", fill="x")
        hdr.pack_propagate(False)
        tk.Label(
            hdr, text="  🔷  Kodi ↔ MPC-HC Bridge",
            bg=_C_ACCENT, fg="white", font=("Segoe UI", 14, "bold"), anchor="w"
        ).pack(side="left", padx=12, pady=10)

        # Status bar (packed top → second)
        self._status_var = tk.StringVar(value="…")
        self._status_lbl = tk.Label(
            self._root, textvariable=self._status_var,
            bg=_C_PANEL, fg=_C_FG_DIM, font=("Segoe UI", 9), anchor="w", padx=12, pady=6
        )
        self._status_lbl.pack(side="top", fill="x")

        # Bottom action bar — packed BEFORE notebook so expand=True doesn't steal its space
        bar = tk.Frame(self._root, bg=_C_PANEL, pady=10)
        bar.pack(side="bottom", fill="x")
        self._btn_start = self._btn(bar, "▶  Bridge starten", self._on_start, _C_SUCCESS)
        self._btn_start.pack(side="left", padx=(14, 6))
        self._btn_stop = self._btn(bar, "■  Stoppen", self._on_stop, _C_ERROR)
        self._btn_stop.pack(side="left", padx=6)
        self._btn(bar, "🧪  Test-Client", self._on_test_client, _C_ACCENT).pack(side="left", padx=6)
        self._btn(bar, "✖  Beenden", self._root.destroy, _C_BTN).pack(side="right", padx=14)

        # Notebook (packed last with expand — fills all remaining space)
        style = ttk.Style(self._root)
        style.theme_use("clam")
        style.configure("TNotebook", background=_C_BG, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=_C_PANEL, foreground=_C_FG_DIM,
                        padding=[14, 6], font=("Segoe UI", 9))
        style.map("TNotebook.Tab",
                  background=[("selected", _C_BG)],
                  foreground=[("selected", _C_FG)])

        nb = ttk.Notebook(self._root)
        nb.pack(side="top", fill="both", expand=True)

        self._tab_settings = tk.Frame(nb, bg=_C_BG)
        self._tab_install  = tk.Frame(nb, bg=_C_BG)
        self._tab_log      = tk.Frame(nb, bg=_C_BG)

        nb.add(self._tab_settings, text="  ⚙  Einstellungen  ")
        nb.add(self._tab_install,  text="  🔧  System  ")
        nb.add(self._tab_log,      text="  📋  Log  ")

        self._build_settings_tab()
        self._build_install_tab()
        self._build_log_tab()

    def _btn(self, parent, text: str, cmd, color=_C_BTN, width: int = 0) -> tk.Button:
        b = tk.Button(
            parent, text=text, command=cmd,
            bg=color, fg="white", activebackground=_C_BTN_HOV, activeforeground="white",
            relief="flat", cursor="hand2", font=("Segoe UI", 9),
            padx=14, pady=6,
        )
        if width:
            b.config(width=width)
        return b

    def _label(self, parent, text: str, dim: bool = False) -> tk.Label:
        return tk.Label(
            parent, text=text, bg=_C_BG,
            fg=_C_FG_DIM if dim else _C_FG,
            font=("Segoe UI", 9), anchor="w"
        )

    def _entry(self, parent, var: tk.StringVar, show: str = "") -> tk.Entry:
        return tk.Entry(
            parent, textvariable=var,
            bg=_C_ENTRY_BG, fg=_C_FG, insertbackground=_C_FG,
            relief="flat", font=("Segoe UI", 10),
            highlightthickness=1, highlightcolor=_C_ACCENT,
            highlightbackground="#444", show=show,
        )

    def _section(self, parent, title: str) -> tk.Frame:
        """A titled section box."""
        outer = tk.Frame(parent, bg=_C_BG)
        outer.pack(fill="x", padx=16, pady=(12, 0))
        tk.Label(
            outer, text=f"  {title}", bg=_C_ACCENT, fg="white",
            font=("Segoe UI", 9, "bold"), anchor="w", padx=4, pady=3
        ).pack(fill="x")
        inner = tk.Frame(outer, bg=_C_PANEL, padx=14, pady=10)
        inner.pack(fill="x")
        return inner

    # ── Settings tab ─────────────────────────────────────────────────────────

    def _build_settings_tab(self) -> None:
        p = self._tab_settings
        cfg = self._cfg_mgr.cfg if self._cfg_mgr else None

        # Kodi section
        kodi = self._section(p, "Kodi")
        fields_kodi = [
            ("Host",         "kodi_host",     "", cfg.kodi_host     if cfg else "localhost"),
            ("HTTP-Port",    "kodi_port",     "", str(cfg.kodi_port) if cfg else "8080"),
            ("WS-Port",      "kodi_ws_port",  "", str(cfg.kodi_ws_port) if cfg else "9090"),
            ("Benutzername", "kodi_username", "", cfg.kodi_username  if cfg else ""),
            ("Passwort",     "kodi_password", "*", cfg.kodi_password if cfg else ""),
        ]
        self._vars: dict[str, tk.StringVar] = {}
        for row, (label, key, show, default) in enumerate(fields_kodi):
            self._label(kodi, label + ":").grid(row=row, column=0, sticky="w", pady=3, padx=(0, 12))
            var = tk.StringVar(value=default)
            self._vars[key] = var
            self._entry(kodi, var, show=show).grid(row=row, column=1, sticky="ew", pady=3)
        kodi.columnconfigure(1, weight=1)

        # MPC-HC / Bridge section
        srv = self._section(p, "MPC-HC / Bridge-Server")
        fields_srv = [
            ("MPC-HC Host",  "mpchc_host",   "", cfg.mpchc_host    if cfg else "localhost"),
            ("MPC-HC Port",  "mpchc_port",   "", str(cfg.mpchc_port) if cfg else "13579"),
            ("Bridge-Port",  "server_port",  "", str(cfg.server_port) if cfg else "13590"),
        ]
        for row, (label, key, show, default) in enumerate(fields_srv):
            self._label(srv, label + ":").grid(row=row, column=0, sticky="w", pady=3, padx=(0, 12))
            var = tk.StringVar(value=default)
            self._vars[key] = var
            self._entry(srv, var, show=show).grid(row=row, column=1, sticky="ew", pady=3)
        srv.columnconfigure(1, weight=1)

        # Note: empty user/password = Kodi without auth
        self._label(
            p, "  ℹ  Benutzername und Passwort leer lassen wenn Kodi ohne Authentifizierung läuft.",
            dim=True
        ).pack(anchor="w", padx=16, pady=(8, 0))

        self._btn(p, "💾  Einstellungen speichern", self._on_save_config, _C_ACCENT).pack(
            anchor="e", padx=16, pady=12
        )

    # ── System tab ───────────────────────────────────────────────────────────

    def _build_install_tab(self) -> None:
        p = self._tab_install

        # Autostart (Task Scheduler, kein Admin)
        auto = self._section(p, "Autostart  (Task-Planer — funktioniert ohne Explorer/Shell)")
        self._lbl_autostart = tk.Label(
            auto, text="", bg=_C_PANEL, fg=_C_FG, font=("Segoe UI", 9), anchor="w"
        )
        self._lbl_autostart.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        self._btn(auto, "✔  Aktivieren", self._on_autostart_install, _C_SUCCESS)\
            .grid(row=1, column=0, padx=(0, 8), sticky="w")
        self._btn(auto, "✖  Entfernen", self._on_autostart_remove, _C_ERROR)\
            .grid(row=1, column=1, sticky="w")
        auto.columnconfigure(2, weight=1)

        # Firewall
        fw = self._section(p, "Windows-Firewall  (Admin erforderlich)")
        self._lbl_firewall = tk.Label(
            fw, text="", bg=_C_PANEL, fg=_C_FG, font=("Segoe UI", 9), anchor="w"
        )
        self._lbl_firewall.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        self._btn(fw, "✔  Regel hinzufügen", self._on_fw_add,    _C_SUCCESS)\
            .grid(row=1, column=0, padx=(0, 8), sticky="w")
        self._btn(fw, "✖  Regel entfernen",  self._on_fw_remove, _C_ERROR)\
            .grid(row=1, column=1, sticky="w")
        fw.columnconfigure(2, weight=1)

    # ── Log tab ──────────────────────────────────────────────────────────────

    def _build_log_tab(self) -> None:
        p = self._tab_log
        self._log_text = scrolledtext.ScrolledText(
            p, state="disabled",
            bg=_C_ENTRY_BG, fg="#aaffaa",
            font=("Consolas", 8), wrap="word",
            relief="flat",
        )
        self._log_text.pack(fill="both", expand=True, padx=8, pady=8)
        self._btn(p, "🗑  Log leeren", self._on_clear_log, _C_BTN).pack(anchor="e", padx=8, pady=(0, 8))

    # ── Status refresh (non-blocking) ────────────────────────────────────────
    #
    # ALL subprocess / network calls are moved to a background thread.
    # Results are marshalled back to the main thread via root.after(0, …).
    # This prevents the tkinter event loop from freezing.

    # Cache firewall state — PowerShell is slow (1-3 s) so we only check
    # it once on startup, then only when the user explicitly acts on it.
    _fw_cache: bool = False
    _fw_checked: bool = False

    def _refresh_status(self) -> None:
        """Schedule a background status check and return immediately."""
        threading.Thread(target=self._refresh_status_bg, daemon=True).start()

    def _refresh_status_bg(self) -> None:
        """Run all blocking checks in a worker thread."""
        running = _bridge_running(self._port)
        installed = False
        fw_ok = self._fw_cache

        if sys.platform == "win32":
            try:
                installed = service.is_installed()
            except Exception:
                pass
            # Firewall check via PowerShell — only run once per explicit action
            # or on first startup (not on every periodic refresh)
            if not self._fw_checked:
                try:
                    fw_ok = firewall_rule_exists(self._port)
                    self._fw_cache = fw_ok
                    self._fw_checked = True
                except Exception:
                    pass

        # Marshal UI update back to main thread
        try:
            self._root.after(0, lambda: self._apply_status(running, installed, fw_ok))
        except Exception:
            pass  # window already destroyed

    def _apply_status(self, running: bool, installed: bool, fw_ok: bool) -> None:
        """Apply gathered status to UI widgets — must run on the main thread."""
        try:
            if running:
                self._status_var.set(f"● Bridge läuft  ·  Port {self._port}")
                self._status_lbl.config(fg=_C_SUCCESS)
            else:
                self._status_var.set(f"○ Bridge gestoppt  ·  Port {self._port}")
                self._status_lbl.config(fg=_C_FG_DIM)
            self._update_tray(running)

            if sys.platform == "win32":
                self._lbl_autostart.config(
                    text=("✅  Autostart aktiv" if installed else "❌  Autostart nicht eingerichtet"),
                    fg=(_C_SUCCESS if installed else _C_FG_DIM),
                )
                self._lbl_firewall.config(
                    text=(f"✅  Firewall-Regel vorhanden (Port {self._port})"
                          if fw_ok else f"❌  Keine Firewall-Regel für Port {self._port}"),
                    fg=(_C_SUCCESS if fw_ok else _C_FG_DIM),
                )
        except tk.TclError:
            pass  # window was destroyed while the after() callback was pending

    def _invalidate_fw_cache(self) -> None:
        """Force a fresh firewall check on the next refresh cycle."""
        self._fw_checked = False

    def _schedule_refresh(self) -> None:
        self._root.after(5000, self._schedule_refresh)
        self._refresh_status()

    # ── System-tray icon ─────────────────────────────────────────────────────

    def _make_tray_image(self, running: bool) -> "_PilImage.Image":  # type: ignore[name-defined]
        """Create a 64×64 RGBA icon image for the system tray."""
        sz = 64
        img = _PilImage.new("RGBA", (sz, sz), (0, 0, 0, 0))
        draw = _PilDraw.Draw(img)
        # Background circle — green when running, grey when stopped
        bg = (70, 185, 80, 255) if running else (100, 100, 100, 255)
        draw.ellipse([2, 2, sz - 3, sz - 3], fill=bg)
        # Simple "bridge" symbol: two vertical pillars + horizontal beam
        w = (255, 255, 255, 210)
        draw.rectangle([13, 18, 22, 50], fill=w)   # left pillar
        draw.rectangle([42, 18, 51, 50], fill=w)   # right pillar
        draw.rectangle([13, 26, 51, 35], fill=w)   # horizontal beam
        return img

    def _create_tray(self) -> None:
        """Create and start the system-tray icon in a background thread."""
        menu = pystray.Menu(  # type: ignore[name-defined]
            pystray.MenuItem(  # type: ignore[name-defined]
                "GUI öffnen / Einstellungen",
                self._on_tray_open,
                default=True,   # double-click triggers this action
            ),
            pystray.Menu.SEPARATOR,  # type: ignore[name-defined]
            pystray.MenuItem("Bridge starten", self._on_tray_start),  # type: ignore[name-defined]
            pystray.MenuItem("Bridge stoppen", self._on_tray_stop),   # type: ignore[name-defined]
            pystray.Menu.SEPARATOR,  # type: ignore[name-defined]
            pystray.MenuItem("Beenden",        self._on_tray_quit),   # type: ignore[name-defined]
        )
        self._tray = pystray.Icon(  # type: ignore[name-defined]
            "kodi-mpchc-bridge",
            self._make_tray_image(False),
            "kodi-mpchc-bridge — gestoppt",
            menu,
        )
        threading.Thread(target=self._tray.run, daemon=True, name="tray").start()

    def _update_tray(self, running: bool) -> None:
        """Update tray icon colour and tooltip to reflect bridge status."""
        if not self._tray:
            return
        if running == self._bridge_running_flag:
            return  # no change — skip the (slightly expensive) icon rebuild
        self._bridge_running_flag = running
        try:
            self._tray.icon  = self._make_tray_image(running)
            self._tray.title = (
                f"kodi-mpchc-bridge — läuft  (Port {self._port})"
                if running else
                f"kodi-mpchc-bridge — gestoppt  (Port {self._port})"
            )
        except Exception:
            pass

    def _hide_to_tray(self) -> None:
        """Called when the user clicks the window's X button."""
        if _TRAY_AVAILABLE and self._tray:
            self._root.withdraw()   # hide, keep mainloop alive
        else:
            self._do_quit()         # no tray — really exit

    def _show_window(self) -> None:
        """Restore the main window from tray."""
        self._root.deiconify()
        self._root.lift()
        self._root.focus_force()

    def _do_quit(self) -> None:
        """Clean up and exit the application."""
        logging.getLogger().removeHandler(self._log_handler)
        try:
            self._root.destroy()
        except Exception:
            pass

    # ── Tray menu callbacks (called from tray thread) ────────────────────────

    def _on_tray_open(self, icon, item) -> None:  # noqa: ANN001
        self._root.after(0, self._show_window)

    def _on_tray_start(self, icon, item) -> None:  # noqa: ANN001
        self._root.after(0, self._on_start)

    def _on_tray_stop(self, icon, item) -> None:   # noqa: ANN001
        self._root.after(0, self._on_stop)

    def _on_tray_quit(self, icon, item) -> None:   # noqa: ANN001
        icon.stop()
        self._root.after(0, self._do_quit)

    # ── Button handlers ──────────────────────────────────────────────────────

    def _on_save_config(self) -> None:
        if not self._cfg_mgr:
            self._log("Kein Config-Manager verfügbar.")
            return
        data: dict = {}
        for key, var in self._vars.items():
            val = var.get().strip()
            if key in ("kodi_port", "kodi_ws_port", "mpchc_port", "server_port"):
                try:
                    data[key] = int(val)
                except ValueError:
                    messagebox.showerror("Ungültige Eingabe", f"{key}: Ganzzahl erwartet.")
                    return
            else:
                data[key] = val
        self._cfg_mgr.update(data)
        self._port = data.get("server_port", self._port)
        self._log("✅  Einstellungen gespeichert.")
        self._refresh_status()

    def _on_start(self) -> None:
        def _task():
            ok, msg = _start_bridge_proc(self._port)
            self._log(("[INFO] " if ok else "[ERROR] ") + msg)
            self._root.after(1500, self._refresh_status)
        threading.Thread(target=_task, daemon=True).start()

    def _on_stop(self) -> None:
        def _task():
            ok, msg = _stop_bridge_proc()
            self._log(("[INFO] " if ok else "[ERROR] ") + msg)
            self._root.after(1500, self._refresh_status)
        threading.Thread(target=_task, daemon=True).start()

    def _on_test_client(self) -> None:
        if getattr(sys, "frozen", False):
            # In frozen exe: launch same exe with --test-client flag
            threading.Thread(
                target=lambda: subprocess.Popen(
                    [sys.executable, "--test-client"],
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                ),
                daemon=True,
            ).start()
        else:
            script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_client.py")
            threading.Thread(
                target=lambda: subprocess.Popen([sys.executable, script]),
                daemon=True,
            ).start()

    def _on_autostart_install(self) -> None:
        ok, msgs = service.install()
        for m in msgs:
            self._log(("[INFO] " if ok else "[ERROR] ") + m)
        self._refresh_status()

    def _on_autostart_remove(self) -> None:
        ok, msgs = service.uninstall()
        for m in msgs:
            self._log(("[INFO] " if ok else "[ERROR] ") + m)
        self._refresh_status()

    def _on_fw_add(self) -> None:
        ok, msg = firewall_add(self._port)
        self._log(("[INFO] " if ok else "[ERROR] ") + msg)
        if ok:
            self._lbl_firewall.config(text="⏳  Warte auf UAC-Bestätigung…", fg=_C_WARN)
            self._poll_firewall(expect_present=True, attempts=8)

    def _on_fw_remove(self) -> None:
        ok, msg = firewall_remove()
        self._log(("[INFO] " if ok else "[ERROR] ") + msg)
        if ok:
            self._lbl_firewall.config(text="⏳  Warte auf UAC-Bestätigung…", fg=_C_WARN)
            self._poll_firewall(expect_present=False, attempts=8)

    def _poll_firewall(self, expect_present: bool, attempts: int) -> None:
        """Poll every 2 s until firewall state matches *expect_present*, max *attempts* tries."""
        def _check(remaining: int) -> None:
            exists = firewall_rule_exists(self._port)
            if exists == expect_present:
                # Reached expected state — update cache so periodic refresh shows correct value
                self._fw_cache = expect_present
                self._fw_checked = True
                if expect_present:
                    self._log(f"[INFO] ✅ Firewall-Regel erfolgreich hinzugefügt (Port {self._port}).")
                    self._lbl_firewall.config(
                        text=f"✅  Firewall-Regel vorhanden (Port {self._port})", fg=_C_SUCCESS
                    )
                else:
                    self._log("[INFO] ✅ Firewall-Regel erfolgreich entfernt.")
                    self._lbl_firewall.config(
                        text=f"❌  Keine Firewall-Regel für Port {self._port}", fg=_C_FG_DIM
                    )
                self._refresh_status()
            elif remaining > 0:
                # Not yet — try again after 2 s
                self._root.after(2000, lambda: _check(remaining - 1))
            else:
                # Timeout
                if expect_present:
                    self._log("[WARN] ⚠  Firewall-Regel nicht gefunden — UAC abgelehnt oder Fehler.")
                else:
                    self._log("[WARN] ⚠  Firewall-Regel noch vorhanden — UAC abgelehnt oder Fehler.")
                self._refresh_status()

        self._root.after(2000, lambda: _check(attempts - 1))

    def _on_clear_log(self) -> None:
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.configure(state="disabled")

    # ── Log helper ───────────────────────────────────────────────────────────

    def _log(self, text: str) -> None:
        def _append():
            self._log_text.configure(state="normal")
            self._log_text.insert("end", text + "\n")
            self._log_text.see("end")
            self._log_text.configure(state="disabled")
        if threading.current_thread() is threading.main_thread():
            _append()
        else:
            self._root.after(0, _append)

    # ── Run ──────────────────────────────────────────────────────────────────

    def run(self) -> None:
        # Centre on screen
        self._root.update_idletasks()
        w, h = 660, 700
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        self._root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self._root.mainloop()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(level=logging.INFO)
    app = InstallerApp()
    app.run()


if __name__ == "__main__":
    main()
