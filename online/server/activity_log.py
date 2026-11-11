"""
Persistent activity log for Chasma Online.

Writes one line per event (joins, leaves, room lifecycle, errors, periodic
heartbeats) to `$CHASMA_LOG_DIR/activity.log`, rotated by size, and mirrors the
same lines to stdout so `docker logs` still shows them.

The log directory is bind-mounted from the host (see online/docker-compose.yml)
so it survives container rebuilds -- `docker logs` does not. If the process dies
hard (segfault inside onnxruntime, etc.) Python cannot log; `faulthandler`
writes the native traceback to `faults.log` in the same directory instead.

Lines are `<UTC ISO time> <LEVEL> <event> key=value ...` so they grep cleanly:
    grep ' join ' activity.log
    grep -E 'ERROR|server_start' activity.log
"""

import faulthandler
import logging
import os
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

LOGGER_NAME = "chasma"
log = logging.getLogger(LOGGER_NAME)

MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 5

_configured = False
_fault_file = None


class _UTCFormatter(logging.Formatter):
    converter = time.gmtime

    def formatTime(self, record, datefmt=None):
        t = time.strftime("%Y-%m-%dT%H:%M:%S", self.converter(record.created))
        return f"{t}.{int(record.msecs):03d}Z"


def _fmt_value(value: Any) -> str:
    text = str(value)
    if text == "" or any(ch.isspace() for ch in text) or '"' in text:
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def event(kind: str, level: int = logging.INFO, /, exc_info: bool = False, **fields: Any) -> None:
    """Log one structured event: `event('join', room='ABCD', name='Jay')`."""
    parts = [kind] + [f"{k}={_fmt_value(v)}" for k, v in fields.items()]
    log.log(level, " ".join(parts), exc_info=exc_info)


def configure() -> None:
    """Attach file + stdout handlers once. Safe to call repeatedly."""
    global _configured, _fault_file
    if _configured:
        return
    _configured = True

    formatter = _UTCFormatter("%(asctime)s %(levelname)s %(message)s")
    log.setLevel(logging.INFO)
    log.propagate = False

    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    log.addHandler(stream)

    log_dir = os.environ.get("CHASMA_LOG_DIR")
    if not log_dir:
        return  # local dev / tests: stdout only

    path = Path(log_dir)
    try:
        path.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            path / "activity.log", maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        log.addHandler(file_handler)

        _fault_file = open(path / "faults.log", "a", encoding="utf-8")
        faulthandler.enable(file=_fault_file, all_threads=True)
    except OSError as exc:
        log.error("log_setup_failed dir=%s error=%s", log_dir, exc)
