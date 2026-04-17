"""
kodi-mpchc-bridge — entry point.

Usage:
    bridge.exe                    → Manager-GUI (Einstellungen + Status)
    bridge.exe --headless         → Bridge ohne GUI starten (Autostart)
    bridge.exe --test-client      → Test-Client GUI öffnen
    bridge.exe --config-dir PATH  → Anderes Verzeichnis für config.json
    bridge.exe --log-level LEVEL  → DEBUG / INFO / WARNING / ERROR
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import sys

_LOG = logging.getLogger(__name__)

# Config directory = Installationsverzeichnis (neben bridge.exe), auch im frozen-Modus.
# Bei PyInstaller onefile zeigt __file__ auf den temp-Extraktionspfad,
# sys.executable hingegen immer auf die echte .exe im Installationsverzeichnis.
if getattr(sys, "frozen", False):
    _APP_DIR = os.path.dirname(sys.executable)
else:
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))


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
    parser = argparse.ArgumentParser(description="kodi-mpchc-bridge")
    parser.add_argument(
        "--config-dir",
        default=_APP_DIR,
        help="Verzeichnis für config.json (Standard: Installationsverzeichnis)",
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
