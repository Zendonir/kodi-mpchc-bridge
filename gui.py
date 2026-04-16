"""
Kodi ↔ MPC-HC Bridge — Installer / Manager GUI

Pure tkinter, no extra dependencies.
Tabs: Einstellungen | Installation | Log
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

_LOG = logging.getLogger(__name__)

_PID_FILE = os.path.join(tempfile.gettempdir(), "kodi-mpchc-bridge.pid")
_SERVICE_NAME = "KodiMpcHcBridge"
_SERVICE_DISPLAY = "Kodi MPC-HC Bridge"
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

def _run_as_admin(cmd: str) -> bool:
    """Run *cmd* via cmd.exe with UAC elevation. Returns True if launched."""
    if sys.platform != "win32":
        return False
    import ctypes
    rc = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", "cmd.exe", f"/c {cmd}", None, 0
    )
    return int(rc) > 32


def _run_hidden(cmd: list[str], timeout: int = 10) -> tuple[int, str]:
    """Run *cmd* silently, return (returncode, stdout+stderr)."""
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as exc:
        return -1, str(exc)


def _exe_path() -> str:
    """Return the absolute path to the current executable or script."""
    if getattr(sys, "frozen", False):
        return sys.executable
    return f"{sys.executable} \"{os.path.abspath('main.py')}\""


# ─────────────────────────────────────────────────────────────────────────────
# Service helpers (sc.exe)
# ─────────────────────────────────────────────────────────────────────────────

def service_status() -> str:
    """Return 'running' | 'stopped' | 'not_installed'."""
    rc, out = _run_hidden(["sc", "query", _SERVICE_NAME])
    if rc != 0:
        return "not_installed"
    if "RUNNING" in out:
        return "running"
    return "stopped"


def service_install(exe: str) -> tuple[bool, str]:
    """Install Windows Service (admin required)."""
    binpath = f"\"{exe}\" --headless"
    cmd = (
        f'sc create {_SERVICE_NAME} '
        f'binpath= "{binpath}" '
        f'start= auto '
        f'DisplayName= "{_SERVICE_DISPLAY}" '
        f'&& sc description {_SERVICE_NAME} "Bridges Kodi and MPC-HC for remote control" '
        f'&& sc start {_SERVICE_NAME}'
    )
    ok = _run_as_admin(cmd)
    if ok:
        return True, "Service-Installation gestartet (UAC-Fenster beachten)."
    return False, "Service-Installation abgebrochen."


def service_uninstall() -> tuple[bool, str]:
    """Remove Windows Service (admin required)."""
    cmd = f"sc stop {_SERVICE_NAME} & sc delete {_SERVICE_NAME}"
    ok = _run_as_admin(cmd)
    if ok:
        return True, "Service-Deinstallation gestartet."
    return False, "Abgebrochen."


# ─────────────────────────────────────────────────────────────────────────────
# Firewall helpers (netsh)
# ─────────────────────────────────────────────────────────────────────────────

def firewall_rule_exists(port: int) -> bool:
    rc, out = _run_hidden(
        ["netsh", "advfirewall", "firewall", "show", "rule", f"name={_FIREWALL_RULE}"]
    )
    return rc == 0 and "Rule Name" in out


def firewall_add(port: int) -> tuple[bool, str]:
    cmd = (
        f'netsh advfirewall firewall add rule '
        f'name="{_FIREWALL_RULE}" '
        f'dir=in action=allow protocol=TCP localport={port} '
        f'description="Kodi-MPC-HC Bridge inbound port"'
    )
    ok = _run_as_admin(cmd)
    if ok:
        return True, f"Firewall-Regel für Port {port} wird hinzugefügt."
    return False, "Abgebrochen."


def firewall_remove() -> tuple[bool, str]:
    cmd = f'netsh advfirewall firewall delete rule name="{_FIREWALL_RULE}"'
    ok = _run_as_admin(cmd)
    if ok:
        return True, "Firewall-Regel wird entfernt."
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

        self._root = tk.Tk()
        self._root.title("Kodi ↔ MPC-HC Bridge")
        self._root.configure(bg=_C_BG)
        self._root.resizable(True, True)
        self._root.minsize(560, 500)

        self._build_ui()
        self._refresh_status()

        # Route logging to GUI
        handler = _GuiLogHandler(self._log)
        handler.setFormatter(
            logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
                              datefmt="%H:%M:%S")
        )
        logging.getLogger().addHandler(handler)

        # Periodic status refresh
        self._schedule_refresh()

    # ── config ───────────────────────────────────────────────────────────────

    def _load_config(self) -> None:
        try:
            from bridge.config import ConfigManager
            self._cfg_mgr = ConfigManager(os.path.dirname(os.path.abspath(__file__)))
            self._port = self._cfg_mgr.cfg.server_port
        except Exception:
            self._cfg_mgr = None

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Header
        hdr = tk.Frame(self._root, bg=_C_ACCENT, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(
            hdr, text="  🔷  Kodi ↔ MPC-HC Bridge",
            bg=_C_ACCENT, fg="white", font=("Segoe UI", 14, "bold"), anchor="w"
        ).pack(side="left", padx=12, pady=10)

        # Status bar
        self._status_var = tk.StringVar(value="…")
        self._status_lbl = tk.Label(
            self._root, textvariable=self._status_var,
            bg=_C_PANEL, fg=_C_FG_DIM, font=("Segoe UI", 9), anchor="w", padx=12, pady=6
        )
        self._status_lbl.pack(fill="x")

        # Notebook
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
        nb.pack(fill="both", expand=True, padx=0, pady=0)

        self._tab_settings = tk.Frame(nb, bg=_C_BG)
        self._tab_install  = tk.Frame(nb, bg=_C_BG)
        self._tab_log      = tk.Frame(nb, bg=_C_BG)

        nb.add(self._tab_settings, text="  ⚙  Einstellungen  ")
        nb.add(self._tab_install,  text="  🔧  Installation  ")
        nb.add(self._tab_log,      text="  📋  Log  ")

        self._build_settings_tab()
        self._build_install_tab()
        self._build_log_tab()

        # Bottom action bar
        bar = tk.Frame(self._root, bg=_C_PANEL, pady=8)
        bar.pack(fill="x", side="bottom")
        self._btn_start = self._btn(bar, "▶  Bridge starten", self._on_start, _C_SUCCESS)
        self._btn_start.pack(side="left", padx=(12, 4))
        self._btn_stop = self._btn(bar, "■  Stoppen", self._on_stop, _C_ERROR)
        self._btn_stop.pack(side="left", padx=4)
        self._btn(bar, "🧪  Test-Client", self._on_test_client, _C_ACCENT).pack(side="left", padx=4)
        self._btn(bar, "✖  Beenden", self._root.destroy, _C_BTN).pack(side="right", padx=12)

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

    # ── Install tab ──────────────────────────────────────────────────────────

    def _build_install_tab(self) -> None:
        p = self._tab_install

        # Autostart (HKCU, no admin)
        auto = self._section(p, "Autostart  (Benutzer-Registry, kein Admin)")
        self._lbl_autostart = tk.Label(
            auto, text="", bg=_C_PANEL, fg=_C_FG, font=("Segoe UI", 9), anchor="w"
        )
        self._lbl_autostart.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        self._btn(auto, "✔  Aktivieren", self._on_autostart_install, _C_SUCCESS)\
            .grid(row=1, column=0, padx=(0, 8), sticky="w")
        self._btn(auto, "✖  Entfernen", self._on_autostart_remove, _C_ERROR)\
            .grid(row=1, column=1, sticky="w")
        auto.columnconfigure(2, weight=1)

        # Service (sc.exe, admin)
        svc = self._section(p, "Windows-Dienst  (Admin erforderlich, läuft ohne Login)")
        tk.Label(
            svc,
            text="⚠  Der Dienst läuft in Session 0 — Win32-Fensterbefehle (Track-Auswahl)\n"
                 "   funktionieren im Service-Modus nicht. Für Desktop-Nutzung Autostart bevorzugen.",
            bg=_C_PANEL, fg=_C_WARN, font=("Segoe UI", 8), justify="left", anchor="w"
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        self._lbl_service = tk.Label(
            svc, text="", bg=_C_PANEL, fg=_C_FG, font=("Segoe UI", 9), anchor="w"
        )
        self._lbl_service.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 8))
        self._btn(svc, "✔  Service installieren", self._on_svc_install, _C_SUCCESS)\
            .grid(row=2, column=0, padx=(0, 8), sticky="w")
        self._btn(svc, "✖  Service entfernen",   self._on_svc_remove,  _C_ERROR)\
            .grid(row=2, column=1, sticky="w")
        svc.columnconfigure(2, weight=1)

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

    # ── Status refresh ───────────────────────────────────────────────────────

    def _refresh_status(self) -> None:
        # Bridge running?
        running = _bridge_running(self._port)
        if running:
            self._status_var.set(f"● Bridge läuft  ·  Port {self._port}")
            self._status_lbl.config(fg=_C_SUCCESS)
        else:
            self._status_var.set(f"○ Bridge gestoppt  ·  Port {self._port}")
            self._status_lbl.config(fg=_C_FG_DIM)

        # Autostart
        if sys.platform == "win32":
            installed = service.is_installed()
            self._lbl_autostart.config(
                text=("✅  Autostart aktiv" if installed else "❌  Autostart nicht eingerichtet"),
                fg=(_C_SUCCESS if installed else _C_FG_DIM),
            )
            # Service
            ss = service_status()
            svc_text = {"running": "✅  Service läuft", "stopped": "⚠  Service installiert (gestoppt)",
                        "not_installed": "❌  Service nicht installiert"}.get(ss, ss)
            self._lbl_service.config(
                text=svc_text,
                fg=(_C_SUCCESS if ss == "running" else _C_WARN if ss == "stopped" else _C_FG_DIM),
            )
            # Firewall
            fw_ok = firewall_rule_exists(self._port)
            self._lbl_firewall.config(
                text=(f"✅  Firewall-Regel vorhanden (Port {self._port})"
                      if fw_ok else f"❌  Keine Firewall-Regel für Port {self._port}"),
                fg=(_C_SUCCESS if fw_ok else _C_FG_DIM),
            )

    def _schedule_refresh(self) -> None:
        self._refresh_status()
        self._root.after(5000, self._schedule_refresh)

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

    def _on_svc_install(self) -> None:
        exe = sys.executable if getattr(sys, "frozen", False) else \
              f"{sys.executable} {os.path.abspath('main.py')}"
        ok, msg = service_install(exe)
        self._log(("[INFO] " if ok else "[ERROR] ") + msg)
        self._root.after(3000, self._refresh_status)

    def _on_svc_remove(self) -> None:
        ok, msg = service_uninstall()
        self._log(("[INFO] " if ok else "[ERROR] ") + msg)
        self._root.after(3000, self._refresh_status)

    def _on_fw_add(self) -> None:
        ok, msg = firewall_add(self._port)
        self._log(("[INFO] " if ok else "[ERROR] ") + msg)
        self._root.after(3000, self._refresh_status)

    def _on_fw_remove(self) -> None:
        ok, msg = firewall_remove()
        self._log(("[INFO] " if ok else "[ERROR] ") + msg)
        self._root.after(3000, self._refresh_status)

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
        w, h = 620, 580
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
