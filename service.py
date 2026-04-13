"""
Windows autostart helpers using HKCU Registry Run key.

No admin rights required.
"""

from __future__ import annotations

import os
import subprocess
import sys

_REG_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_REG_VALUE = "KodiMpcHcBridge"


def _exe_path() -> str:
    """Return the path to this executable (or main.py for dev runs)."""
    if getattr(sys, "frozen", False):
        return sys.executable
    return f'"{sys.executable}" "{os.path.abspath("main.py")}"'


def is_installed() -> bool:
    """Return True if the autostart entry exists."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_RUN_KEY) as key:
            winreg.QueryValueEx(key, _REG_VALUE)
            return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def install() -> tuple[bool, list[str]]:
    """Add HKCU autostart entry. Returns (success, messages)."""
    if sys.platform != "win32":
        return False, ["Only supported on Windows"]
    try:
        import winreg
        cmd = _exe_path() + " --headless"
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, _REG_VALUE, 0, winreg.REG_SZ, cmd)
        return True, [f"Autostart registered: {cmd}"]
    except Exception as exc:
        return False, [f"Failed to register autostart: {exc}"]


def uninstall() -> tuple[bool, list[str]]:
    """Remove HKCU autostart entry."""
    if sys.platform != "win32":
        return False, ["Only supported on Windows"]
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, _REG_VALUE)
        return True, ["Autostart entry removed"]
    except FileNotFoundError:
        return True, ["Autostart entry was not present"]
    except Exception as exc:
        return False, [f"Failed to remove autostart: {exc}"]


def kill_port(port: int) -> list[str]:
    """Kill any process listening on *port*. Returns log lines."""
    if sys.platform != "win32":
        return []
    lines: list[str] = []
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"], text=True, stderr=subprocess.DEVNULL
        )
        pids: set[str] = set()
        for line in out.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                if parts:
                    pids.add(parts[-1])
        for pid in pids:
            subprocess.run(
                ["taskkill", "/f", "/pid", pid],
                capture_output=True,
            )
            lines.append(f"Killed PID {pid} on port {port}")
    except Exception as exc:
        lines.append(f"kill_port error: {exc}")
    return lines
