"""
kodi-mpchc-bridge — entry point.

Usage:
    bridge.exe                    → Installer/Manager GUI
    bridge.exe --headless         → Bridge ohne GUI starten (Autostart/Service)
    bridge.exe --test-client      → Test-Client GUI öffnen
    bridge.exe --config-dir PATH  → Anderes Verzeichnis für config.json
    bridge.exe --log-level LEVEL  → DEBUG / INFO / WARNING / ERROR
"""

from __future__ import annotations

import argparse
import asyncio
import glob
import logging
import os
import shutil
import signal
import sys
import tempfile

_LOG = logging.getLogger(__name__)


def _cleanup_stale_pyinstaller_dirs() -> None:
    """
    Remove leftover _MEI* temp dirs created by previous one-file PyInstaller runs
    that were killed without a clean shutdown (service stop, Task Manager, crash).

    The PyInstaller bootloader also attempts this at startup, but it runs before
    Python and shows a warning dialog when it fails due to file locks (antivirus,
    Windows Search indexer, …).  Running cleanup *before* that on *this* start-up
    is too late to silence the dialog for the current run, but it ensures the
    leftover dir is gone so the *next* launch won't see the warning.

    Safe: we never remove the directory our own process is running from.
    """
    if not getattr(sys, "frozen", False):
        return
    current = getattr(sys, "_MEIPASS", None)
    tmpdir = tempfile.gettempdir()
    for path in glob.glob(os.path.join(tmpdir, "_MEI*")):
        if path == current:
            continue
        try:
            shutil.rmtree(path)
        except Exception:
            pass  # best-effort; bootloader will retry on next launch


def _setup_logging(level: str) -> None:
    fmt = "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s"
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format=fmt)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)


# ─────────────────────────────────────────────────────────────────────────────
# Bridge loop (headless)
# ─────────────────────────────────────────────────────────────────────────────

async def _run_bridge(config_dir: str) -> None:
    from bridge.config import ConfigManager
    from bridge.hub import Hub

    config = ConfigManager(config_dir)
    hub = Hub(config)
    await hub.start()

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _sig():
        stop_event.set()

    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _sig)

    try:
        _LOG.info("Bridge running. Press Ctrl+C to stop.")
        await stop_event.wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        _LOG.info("Shutting down…")
        await hub.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    _cleanup_stale_pyinstaller_dirs()
    parser = argparse.ArgumentParser(description="kodi-mpchc-bridge")
    parser.add_argument(
        "--config-dir",
        default=os.path.dirname(os.path.abspath(__file__)),
        help="Verzeichnis für config.json",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="Bridge ohne GUI starten (für Autostart/Service)",
    )
    parser.add_argument(
        "--test-client", action="store_true",
        help="Test-Client GUI öffnen",
    )
    args = parser.parse_args()

    _setup_logging(args.log_level)

    if args.test_client:
        # Test-Client GUI
        try:
            import test_client
            test_client.main()
        except Exception as exc:
            _LOG.error("Test-Client konnte nicht geöffnet werden: %s", exc)
        return

    if args.headless:
        # Headless bridge loop
        asyncio.run(_run_bridge(args.config_dir))
        return

    # Default: Installer/Manager GUI
    try:
        import gui
        gui.main()
    except Exception as exc:
        _LOG.error("GUI konnte nicht gestartet werden: %s", exc)
        # Fallback: headless
        asyncio.run(_run_bridge(args.config_dir))


if __name__ == "__main__":
    main()
