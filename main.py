"""
kodi-mpchc-bridge — entry point.

Usage:
    python main.py [--config-dir PATH] [--log-level LEVEL]

When run with --headless, no GUI is shown (useful for autostart).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import sys

from bridge.config import ConfigManager
from bridge.hub import Hub

_LOG = logging.getLogger(__name__)


def _setup_logging(level: str) -> None:
    fmt = "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s"
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format=fmt)
    # Quiet noisy libraries
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)


async def _run(config_dir: str) -> None:
    config = ConfigManager(config_dir)
    hub = Hub(config)
    await hub.start()

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler():
        stop_event.set()

    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _signal_handler)

    try:
        _LOG.info("Bridge running. Press Ctrl+C to stop.")
        await stop_event.wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        _LOG.info("Shutting down…")
        await hub.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="kodi-mpchc-bridge hub")
    parser.add_argument(
        "--config-dir",
        default=os.path.dirname(os.path.abspath(__file__)),
        help="Directory for config.json (default: script directory)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    parser.add_argument("--headless", action="store_true", help="Run without GUI")
    args = parser.parse_args()

    _setup_logging(args.log_level)

    asyncio.run(_run(args.config_dir))


if __name__ == "__main__":
    main()
