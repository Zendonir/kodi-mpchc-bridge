"""
Bridge configuration — loaded from / stored to config.json.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field, fields
import dataclasses

_LOG = logging.getLogger(__name__)
_CFG_FILE = "config.json"


@dataclass
class BridgeConfig:
    # Kodi
    kodi_host: str = "localhost"
    kodi_port: int = 8080
    kodi_ws_port: int = 9090
    kodi_username: str = "kodi"
    kodi_password: str = "kodi"
    kodi_ssl: bool = False
    kodi_enabled: bool = True

    # MPC-HC
    mpchc_host: str = "localhost"
    mpchc_port: int = 13579
    mpchc_enabled: bool = True

    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 13590

    # External player / resume feature
    mpchc_exe_path: str = ""              # full path to mpc-hc64.exe / mpc-be64.exe
    resume_enabled: bool = False          # seek to Kodi resume position on external launch
    external_player_enabled: bool = True  # False → --play exits immediately, Kodi uses own player
    episode_art_mode: str = "poster"      # "poster" = tvshow poster, "thumb" = episode thumbnail

    def __post_init__(self) -> None:
        for f in fields(self):
            if not isinstance(f.default, dataclasses.MISSING.__class__) and getattr(self, f.name) is None:
                setattr(self, f.name, f.default)

    def to_dict(self) -> dict:
        return asdict(self)


class ConfigManager:
    def __init__(self, data_path: str = ".") -> None:
        self._path = os.path.join(data_path, _CFG_FILE)
        self._cfg = BridgeConfig()
        self._load()

    @property
    def cfg(self) -> BridgeConfig:
        return self._cfg

    def to_dict(self) -> dict:
        return self._cfg.to_dict()

    def update(self, data: dict) -> None:
        for k, v in data.items():
            if hasattr(self._cfg, k):
                setattr(self._cfg, k, v)
        self._save()

    def _load(self) -> None:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if hasattr(self._cfg, k):
                    setattr(self._cfg, k, v)
            _LOG.debug("Config loaded from %s", self._path)
        except FileNotFoundError:
            _LOG.info("No config file found, using defaults")
        except Exception as exc:
            _LOG.warning("Config load error: %s", exc)

    def _save(self) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._cfg.to_dict(), f, indent=2, ensure_ascii=False)
        except OSError as exc:
            _LOG.error("Cannot save config: %s", exc)
