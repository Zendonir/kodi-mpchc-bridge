"""
kodi-mpchc-bridge — entry point.

Usage:
    bridge.exe                    → Bridge starten + Tray-Icon (Standardmodus)
    bridge.exe --headless         → Nur Bridge, kein Tray (Server/Dienst)
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


def _setup_logging(level: str, log_dir: str | None = None) -> None:
    """
    Konsole: gewählter Level (Standard INFO).
    Log-Datei: kodi-bridge.log im Installationsverzeichnis, rotiert bei 2 MB,
               3 Backups — immer ab DEBUG, damit Fehler vollständig erfasst werden.
    """
    fmt = "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s"
    int_level = getattr(logging, level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [logging.StreamHandler()]

    # In-memory circular buffer — queried by HTTP /api/logs
    try:
        from bridge.log_buffer import handler as _log_buf
        handlers.append(_log_buf)
    except Exception:
        pass

    if log_dir:
        try:
            from logging.handlers import RotatingFileHandler
            log_path = os.path.join(log_dir, "kodi-bridge.log")
            fh = RotatingFileHandler(
                log_path,
                maxBytes=2 * 1024 * 1024,  # 2 MB
                backupCount=3,
                encoding="utf-8",
            )
            fh.setLevel(logging.DEBUG)          # Datei immer vollständig
            fh.setFormatter(logging.Formatter(fmt))
            handlers.append(fh)
        except Exception as exc:
            # Nicht fatal — weiter ohne Datei-Logging
            print(f"[WARN] Log-Datei konnte nicht geöffnet werden: {exc}")

    logging.basicConfig(level=int_level, format=fmt, handlers=handlers)
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
        "--play",
        metavar="FILEPATH",
        default=None,
        help="Datei über die laufende Bridge-Instanz in MPC-HC öffnen (externer Player-Modus)",
    )
    args = parser.parse_args()

    # ── External player mode ───────────────────────────────────────────────────
    # Kodi calls:  kodi-bridge.exe --play "{filepath}"
    #
    # This process acts as the "pseudo-player" that Kodi waits on:
    #   1. POST /api/external_play  → bridge opens MPC-HC (with resume seek)
    #   2. Poll /api/state          → wait until active_player == "mpchc"
    #   3. Poll /api/state          → stay alive while active_player == "mpchc"
    #   4. Exit                     → Kodi sees player closed → returns to UI
    if args.play:
        import json as _json
        import time as _time
        import urllib.request as _urq

        # Log to file too — process runs hidden (hideconsole=true in playercorefactory.xml)
        _setup_logging(args.log_level, log_dir=args.config_dir)
        port = 13590
        try:
            from bridge.config import ConfigManager
            port = ConfigManager(args.config_dir).cfg.server_port
        except Exception:
            pass

        base = f"http://localhost:{port}"

        # ── Step 1: tell bridge to launch MPC-HC ─────────────────────────────
        payload = _json.dumps({"filepath": args.play}).encode()
        try:
            req = _urq.Request(
                f"{base}/api/external_play", data=payload,
                headers={"Content-Type": "application/json"},
            )
            with _urq.urlopen(req, timeout=5) as resp:
                body = _json.loads(resp.read())
                status = body.get("status", "launching")
                _LOG.info("--play: bridge accepted (HTTP %d, status=%s)", resp.status, status)
                if status == "disabled":
                    _LOG.info("--play: external player disabled — exiting immediately")
                    sys.exit(0)
        except Exception as exc:
            _LOG.error("--play: cannot reach bridge at %s — %s", base, exc)
            sys.exit(1)

        def _active_player() -> str | None:
            """Return active_player field from /api/state, or None on error."""
            try:
                with _urq.urlopen(f"{base}/api/state", timeout=3) as r:
                    return _json.loads(r.read()).get("active_player", "none")
            except Exception:
                return None

        # ── Step 2: wait up to 30 s for MPC-HC to appear ─────────────────────
        _LOG.info("--play: waiting for MPC-HC to become active…")
        _deadline = _time.monotonic() + 30
        while _time.monotonic() < _deadline:
            if _active_player() == "mpchc":
                break
            _time.sleep(1)
        else:
            _LOG.warning("--play: MPC-HC did not start within 30 s — exiting")
            sys.exit(0)

        # ── Step 3: stay alive while MPC-HC is playing ────────────────────────
        _LOG.info("--play: MPC-HC active — holding process alive for Kodi…")
        while True:
            ap = _active_player()
            if ap is not None and ap != "mpchc":
                break
            _time.sleep(0.5)

        _LOG.info("--play: MPC-HC closed — releasing Kodi")
        sys.exit(0)

    # Alle anderen Modi schreiben Logs in den Installationspfad
    _setup_logging(args.log_level, log_dir=args.config_dir)

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
