"""Application logging.

`lynjax info` has always reported a log directory and the settings have always
carried a log level, but nothing ever configured logging to use them: the
directory did not exist and every logger call went to wherever the default
handler pointed. For a tool whose job is auditing someone else's network, the
record of what it reached is part of the product, not a debugging aid.

The file is rotated so a long-running server cannot fill a disk, and the console
stays readable for someone watching `lynjax serve` in a terminal.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

from lynjax.core.config import Settings

#: Keep roughly a week of activity at a size that stays greppable.
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 5

FILE_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
CONSOLE_FORMAT = "%(levelname)-8s %(name)s: %(message)s"

#: Libraries that are chatty at INFO and say nothing an operator needs.
NOISY_LOGGERS = ("uvicorn.access", "asyncio", "paramiko.transport")


def configure_logging(settings: Settings) -> Path | None:
    """Set up console and file logging. Returns the log file, if one was opened.

    A log directory that cannot be created is not fatal: the tool still works,
    it just loses its audit trail, and refusing to start over that would be a
    worse trade on a technician's laptop.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level, logging.INFO))

    # Called from both `serve` and the CLI, so clear rather than accumulate.
    for handler in list(root.handlers):
        root.removeHandler(handler)

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(logging.Formatter(CONSOLE_FORMAT))
    root.addHandler(console)

    log_file: Path | None = None
    try:
        settings.log_dir.mkdir(parents=True, exist_ok=True)
        log_file = settings.log_file

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(logging.Formatter(FILE_FORMAT))
        root.addHandler(file_handler)
    except OSError as exc:
        root.warning(
            "Could not open the log file in %s (%s). Continuing with console "
            "logging only; this run will leave no audit trail on disk.",
            settings.log_dir,
            exc,
        )

    for name in NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    return log_file
