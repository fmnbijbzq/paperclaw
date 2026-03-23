from __future__ import annotations

import logging

from app.config import AppSettings


def configure_logging(settings: AppSettings | None = None) -> None:
    level_name = (settings.log_level if settings else "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)
    if root.handlers:
        return

    handler = logging.StreamHandler()
    handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(formatter)
    root.addHandler(handler)
