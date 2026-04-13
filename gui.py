"""
Windows system tray GUI for kodi-mpchc-bridge.

Provides: Install / Start / Stop / Uninstall and a log window.
Requires: pystray, Pillow
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import scrolledtext
import logging

import pystray
from PIL import Image, ImageDraw

import service

_LOG = logging.getLogger(__name__)

_PID_FILE = os.path.join(tempfile.gettempdir(), "kodi-mpchc-bridge.pid")
_BRIDGE_COLOR = (0, 122, 204)  # blue


# ---------------------------------------------------------------------------
# Tray icon image
# ---------------------------------------------------------------------------
def _make_icon() -> Image.Image:
    img = Image.new("RGB", (64, 64), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)
    draw.ellipse([8, 8, 56, 56], fill=_BRIDGE_COLOR)
    draw.rectangle([28, 18, 36, 46], fill="white")
    draw.rectangle([18, 28, 46, 36], fill="white")
    return img


# ---------------------------------------------------------------------------
# Log window
# ---------------------------------------------------------------------------
class LogWindow:
    def __init__(self) -> None:
        self._root: tk.Tk | None = None
        self._text: scrolledtext.ScrolledText | None = None
        self._lock = threading.Lock()
        self._buffer: list[str] = []

    def show(self) -> None:
        if self._root is not None:
            self._root.deiconify()
            self._root.lift()
            return
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        self._root = tk.Tk()
        self._root.title("kodi-mpchc-bridge — Log")
        self._root.geometry("700x400")
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._text = scrolledtext.ScrolledText(
            self._root, state="disabled", font=("Consolas", 8), wrap="word"
        )
        self._text.pack(fill="both", expand=True)

        with self._lock:
            for line in self._buffer:
                self._append(line)
            self._buffer.clear()

        self._root.mainloop()
        self._root = None
        self._text = None

    def _on_close(self) -> None:
        if self._root:
            self._root.withdraw()

    def append(self, line: str) -> None:
        with self._lock:
            if self._text is None:
                self._buffer.append(line)
                return
        self._root.after(0, self._append, line)  # type: ignore[union-attr]

    def _append(self, line: str) -> None:
        if self._text is None:
            return
        self._text.configure(state="normal")
        self._text.insert("end", line + "\n")
        self._text.see("end")
        self._text.configure(state="disabled")


# ---------------------------------------------------------------------------
# GUI logging handler
# ---------------------------------------------------------------------------
class _GuiHandler(logging.Handler):
    def __init__(self, window: LogWindow) -> None:
        super().__init__()
        self._window = window

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._window.append(self.format(record))
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Bridge process management
# ---------------------------------------------------------------------------
def _is_running() -> bool:
    """Check if bridge process is alive via PID file."""
    try:
        with open(_PID_FILE) as f:
            pid = int(f.read().strip())
        # Check process exists
        subprocess.check_call(
            ["tasklist", "/fi", f"PID eq {pid}", "/nh"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        # If tasklist exits 0 and pid is in output
        out = subprocess.check_output(
            ["tasklist", "/fi", f"PID eq {pid}", "/nh"],
            text=True, stderr=subprocess.DEVNULL,
        )
        return str(pid) in out
    except Exception:
        return False


def _http_alive(port: int) -> bool:
    import urllib.request
    try:
        urllib.request.urlopen(f"http://localhost:{port}/", timeout=1)
        return True
    except Exception:
        return False


def _start_bridge(log: LogWindow, port: int) -> None:
    if _http_alive(port):
        log.append("[INFO] Bridge already running on port " + str(port))
        return

    # Kill anything on the port first
    for line in service.kill_port(port):
        log.append("[INFO] " + line)

    exe = sys.executable
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    cmd = [exe, script, "--headless"]
    try:
        proc = subprocess.Popen(
            cmd,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
            close_fds=True,
        )
        with open(_PID_FILE, "w") as f:
            f.write(str(proc.pid))
        log.append(f"[INFO] Bridge started (PID {proc.pid})")
    except Exception as exc:
        log.append(f"[ERROR] Failed to start bridge: {exc}")


def _stop_bridge(log: LogWindow) -> None:
    try:
        with open(_PID_FILE) as f:
            pid = int(f.read().strip())
        subprocess.run(["taskkill", "/f", "/pid", str(pid)], capture_output=True)
        os.remove(_PID_FILE)
        log.append(f"[INFO] Bridge stopped (PID {pid})")
    except FileNotFoundError:
        log.append("[INFO] Bridge not running (no PID file)")
    except Exception as exc:
        log.append(f"[ERROR] Stop failed: {exc}")


# ---------------------------------------------------------------------------
# Tray app
# ---------------------------------------------------------------------------
class TrayApp:
    def __init__(self, config_port: int = 13580) -> None:
        self._port = config_port
        self._log = LogWindow()
        self._icon: pystray.Icon | None = None

    def run(self) -> None:
        # Attach GUI log handler
        handler = _GuiHandler(self._log)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s — %(message)s"))
        logging.getLogger().addHandler(handler)

        icon_img = _make_icon()
        menu = pystray.Menu(
            pystray.MenuItem("Show Log", self._on_show_log),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Start Bridge", self._on_start),
            pystray.MenuItem("Stop Bridge", self._on_stop),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Install Autostart", self._on_install),
            pystray.MenuItem("Uninstall Autostart", self._on_uninstall),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._on_exit),
        )
        self._icon = pystray.Icon("kodi-mpchc-bridge", icon_img, "kodi-mpchc-bridge", menu)
        self._icon.run()

    # ------------------------------------------------------------------
    # Menu actions (run on tray thread)
    # ------------------------------------------------------------------
    def _on_show_log(self, icon, item) -> None:
        self._log.show()

    def _on_start(self, icon, item) -> None:
        threading.Thread(target=_start_bridge, args=(self._log, self._port), daemon=True).start()

    def _on_stop(self, icon, item) -> None:
        threading.Thread(target=_stop_bridge, args=(self._log,), daemon=True).start()

    def _on_install(self, icon, item) -> None:
        ok, msgs = service.install()
        for m in msgs:
            self._log.append(("[INFO] " if ok else "[ERROR] ") + m)
        self._log.show()

    def _on_uninstall(self, icon, item) -> None:
        _stop_bridge(self._log)
        ok, msgs = service.uninstall()
        for m in msgs:
            self._log.append(("[INFO] " if ok else "[ERROR] ") + m)
        self._log.show()

    def _on_exit(self, icon, item) -> None:
        icon.stop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    logging.basicConfig(level=logging.INFO)
    # Read port from config if available
    port = 13580
    try:
        from bridge.config import ConfigManager
        cfg = ConfigManager(os.path.dirname(os.path.abspath(__file__))).cfg
        port = cfg.server_port
    except Exception:
        pass

    app = TrayApp(config_port=port)
    app.run()


if __name__ == "__main__":
    main()
