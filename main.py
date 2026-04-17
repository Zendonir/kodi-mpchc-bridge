"""
kodi-mpchc-bridge — entry point.

Usage:
    bridge.exe                    → Bridge starten + Tray-Icon (Standardmodus)
    bridge.exe --headless         → Nur Bridge, kein Tray (Server/Dienst)
    bridge.exe --test-client      → Test-Client-Fenster öffnen
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
import threading

_LOG = logging.getLogger(__name__)

# Config directory = Installationsverzeichnis (neben bridge.exe), auch im frozen-Modus.
# Bei PyInstaller onefile zeigt __file__ auf den temp-Extraktionspfad —
# sys.executable zeigt immer auf die echte .exe im Installationsverzeichnis.
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
# Bridge-Asyncio-Loop
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
        help="Nur Bridge ohne Tray-Icon (für Servernutzung)",
    )
    parser.add_argument(
        "--test-client", action="store_true",
        help="Test-Client-Fenster öffnen",
    )
    args = parser.parse_args()

    _setup_logging(args.log_level)

    # ── Test-Client ───────────────────────────────────────────────────────────
    if args.test_client:
        try:
            import test_client
            test_client.main()
        except Exception as exc:
            _LOG.error("Test-Client konnte nicht geöffnet werden: %s", exc)
        return

    # ── Headless — Bridge ohne Tray ───────────────────────────────────────────
    if args.headless:
        asyncio.run(_run_bridge(args.config_dir))
        return

    # ── Standard: Bridge + Tray-Icon (Einzelinstanz) ─────────────────────────

    # Einzelinstanz-Sperre via named Mutex — verhindert doppeltes Tray-Icon
    # wenn Autostart + manueller Start kollidieren.
    if sys.platform == "win32":
        import ctypes
        _mutex = ctypes.windll.kernel32.CreateMutexW(
            None, True, "Global\\KodiMpcHcBridgeMutex"
        )
        if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            _LOG.info("Bridge läuft bereits (Mutex gesperrt) — beende.")
            sys.exit(0)

    # Bridge-Loop in Daemon-Thread starten
    _LOG.info("Starte Bridge-Loop im Hintergrundthread…")

    def _bridge_thread() -> None:
        asyncio.run(_run_bridge(args.config_dir))

    bridge_t = threading.Thread(
        target=_bridge_thread, daemon=True, name="bridge-loop"
    )
    bridge_t.start()

    # Konfigurierte Port-Nummer für Tray-Status laden
    port = 13590
    try:
        from bridge.config import ConfigManager
        port = ConfigManager(args.config_dir).cfg.server_port
    except Exception:
        pass

    # Tray-Icon (blockiert bis Beenden)
    try:
        import gui
        gui.main(port=port, config_dir=args.config_dir)
    except ImportError as exc:
        _LOG.warning("Tray-GUI nicht verfügbar (%s) — Bridge läuft headless.", exc)
        bridge_t.join()


if __name__ == "__main__":
    main()
