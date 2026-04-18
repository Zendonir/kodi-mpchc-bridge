"""
In-memory circular log buffer.

Shared between the logging setup (main.py) and the HTTP server (/api/logs).
Stores the last _CAPACITY log records so the web UI can display them.
"""
from __future__ import annotations

import logging
from collections import deque
from typing import Any

_CAPACITY = 500
_FMT = logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s \u2014 %(message)s")


class _LogBuffer(logging.Handler):
    def __init__(self, capacity: int = _CAPACITY) -> None:
        super().__init__(level=logging.DEBUG)
        self._records: deque[dict[str, Any]] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._records.append({
                "level": record.levelname,
                "name":  record.name,
                "msg":   _FMT.format(record),
            })
        except Exception:
            self.handleError(record)

    def get(
        self,
        limit: int = 50,
        level: str = "",
        search: str = "",
    ) -> list[dict[str, Any]]:
        """
        Return the last *limit* records matching optional filters.

        Parameters
        ----------
        limit  : Maximum number of records to return (newest last).
        level  : If non-empty, keep only records at this exact level
                 (``"DEBUG"``, ``"INFO"``, ``"WARNING"``, ``"ERROR"``).
        search : Case-insensitive substring filter applied to the formatted message.
        """
        records: list[dict[str, Any]] = list(self._records)
        if level:
            records = [r for r in records if r["level"] == level]
        if search:
            low = search.lower()
            records = [r for r in records if low in r["msg"].lower()]
        return records[-limit:]


# Module-level singleton — registered in main._setup_logging, queried by BridgeServer
handler = _LogBuffer()
