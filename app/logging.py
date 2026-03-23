from __future__ import annotations

import logging

from app.config import AppSettings

_HANDLER_MARKER = "_paperclaw_console_handler"


def configure_logging(settings: AppSettings | None = None) -> None:
    level_name = (settings.log_level if settings else "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    for handler in root.handlers:
        if getattr(handler, _HANDLER_MARKER, False):
            root.setLevel(level)
            handler.setLevel(level)
            return
    if root.handlers:
        return

    root.setLevel(level)
    handler = logging.StreamHandler()
    setattr(handler, _HANDLER_MARKER, True)
    handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(formatter)
    root.addHandler(handler)
