"""
Windows autostart helpers — Task Scheduler (ONLOGON trigger).

Uses the Windows Task Scheduler instead of the HKCU Run key so that
the bridge starts even when Explorer is not the shell (e.g. Launcher4Kodi
or other kiosk / HTPC setups where Explorer never runs at login).

No administrator rights required — the task runs under the current user's
interactive session.
"""

from __future__ import annotations

import os
import subprocess
import sys

_TASK_NAME = "KodiMpcHcBridge"

# Legacy registry key — only used during migration / cleanup
_REG_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_REG_VALUE   = "KodiMpcHcBridge"


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _run_hidden(cmd: list[str], timeout: int = 15) -> tuple[int, str]:
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as exc:
        return -1, str(exc)


def _exe_parts() -> tuple[str, str]:
    """
    Return (program, arguments) for the scheduled task action.

    Frozen exe  → ("C:\\...\\bridge.exe",       "--headless")
    Dev run     → ("C:\\Python\\python.exe",    '"C:\\...\\main.py" --headless')
    """
    if getattr(sys, "frozen", False):
        return sys.executable, "--headless"
    return sys.executable, f'"{os.path.abspath("main.py")}" --headless'


def _ps_quote(s: str) -> str:
    """Wrap a string in PowerShell single-quotes, escaping inner single-quotes."""
    return "'" + s.replace("'", "''") + "'"


def _remove_legacy_reg() -> None:
    """Silently remove the old HKCU Run-key entry if it is still present."""
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as k:
            winreg.DeleteValue(k, _REG_VALUE)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def is_installed() -> bool:
    """
    Return True if the Task Scheduler autostart entry exists.

    Also returns True if only the legacy HKCU Run key is present
    (so the GUI shows the correct state until the user re-installs).
    """
    if sys.platform != "win32":
        return False
    rc, _ = _run_hidden(["schtasks", "/query", "/tn", _TASK_NAME])
    if rc == 0:
        return True
    # Fallback: check old registry entry for backward compatibility
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_RUN_KEY) as key:
            winreg.QueryValueEx(key, _REG_VALUE)
            return True
    except Exception:
        return False


def install() -> tuple[bool, list[str]]:
    """
    Register an ONLOGON scheduled task for the current user.

    The task fires when the user logs in, regardless of whether Explorer
    is the shell — required for Launcher4Kodi / kiosk setups.
    No admin rights needed.
    """
    if sys.platform != "win32":
        return False, ["Only supported on Windows"]

    program, arguments = _exe_parts()

    # Build the Register-ScheduledTask PowerShell one-liner.
    # -RunLevel Limited  → no UAC elevation at runtime
    # -LogonType Interactive → runs in the user's desktop session
    # ExecutionTimeLimit 0  → no automatic timeout
    ps = (
        f"$act = New-ScheduledTaskAction"
        f" -Execute {_ps_quote(program)}"
        f" -Argument {_ps_quote(arguments)}; "
        f"$tri = New-ScheduledTaskTrigger -AtLogOn"
        f' -User "$env:USERDOMAIN\\$env:USERNAME"; '
        f"$pri = New-ScheduledTaskPrincipal"
        f' -UserId "$env:USERDOMAIN\\$env:USERNAME"'
        f" -LogonType Interactive -RunLevel Limited; "
        f"$set = New-ScheduledTaskSettingsSet"
        f" -ExecutionTimeLimit (New-TimeSpan -Hours 0)"
        f" -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries; "
        f"Register-ScheduledTask -TaskName {_ps_quote(_TASK_NAME)}"
        f" -Action $act -Trigger $tri -Principal $pri -Settings $set"
        f" -Force -ErrorAction Stop"
    )
    rc, out = _run_hidden(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
        timeout=20,
    )
    if rc == 0:
        _remove_legacy_reg()   # clean up old Run key if still present
        return True, [
            f"Autostart eingerichtet (Task-Planer, ONLOGON): {_TASK_NAME}",
            "Startet beim nächsten Login — unabhängig von Explorer/Shell.",
        ]
    return False, [f"Fehler beim Einrichten des Tasks (rc={rc}): {out[:400]}"]


def uninstall() -> tuple[bool, list[str]]:
    """Remove the scheduled task and any legacy registry entry."""
    if sys.platform != "win32":
        return False, ["Only supported on Windows"]

    rc, out = _run_hidden(["schtasks", "/delete", "/f", "/tn", _TASK_NAME])
    _remove_legacy_reg()

    if rc == 0:
        return True, ["Autostart-Task entfernt."]
    # schtasks returns non-zero if the task doesn't exist — that's fine
    low = out.lower()
    if "cannot find" in low or "does not exist" in low or "nicht gefunden" in low:
        return True, ["Autostart-Task war nicht vorhanden."]
    return False, [f"Fehler beim Entfernen (rc={rc}): {out[:400]}"]


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
