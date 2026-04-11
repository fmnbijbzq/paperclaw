from __future__ import annotations

import logging
import os
from pathlib import Path

from app.config import AppSettings

_HANDLER_MARKER = "_paperclaw_console_handler"
_FILE_HANDLER_MARKER = "_paperclaw_file_handler"


def configure_logging(settings: AppSettings | None = None) -> None:
    """初始化日志系统，支持控制台输出和文件输出。"""
    level_name = (settings.log_level if settings else "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    # 解析日志格式配置
    log_format = (settings.log_format if settings else "%(asctime)s %(levelname)s %(name)s: %(message)s")
    if settings and getattr(settings, "log_include_location", False):
        log_format = "%(asctime)s %(levelname)s [%(name)s:%(filename)s:%(lineno)d]: %(message)s"

    # 解析日志文件名配置
    log_file = getattr(settings, "log_file", None) if settings else None
    if os.getenv("LOG_FILE"):
        log_file = os.getenv("LOG_FILE")

    root = logging.getLogger()

    # 更新或添加控制台 handler
    console_handler = None
    file_handler = None
    for handler in root.handlers:
        if getattr(handler, _HANDLER_MARKER, False):
            console_handler = handler
        if getattr(handler, _FILE_HANDLER_MARKER, False):
            file_handler = handler

    if root.handlers and console_handler is None and file_handler is None:
        return

    # 如果已经配置过，只更新级别
    if console_handler and file_handler:
        root.setLevel(level)
        console_handler.setLevel(level)
        file_handler.setLevel(level)
        return

    # 如果只有控制台 handler，检查是否需要添加文件 handler
    if console_handler:
        root.setLevel(level)
        console_handler.setLevel(level)
    else:
        # 全新配置
        root.setLevel(level)
        console_handler = logging.StreamHandler()
        setattr(console_handler, _HANDLER_MARKER, True)
        console_handler.setLevel(level)
        formatter = logging.Formatter(log_format)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

    # 配置文件 handler
    if log_file:
        if file_handler:
            file_handler.setLevel(level)
            return

        # 创建日志目录
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8", mode="a")
        setattr(file_handler, _FILE_HANDLER_MARKER, True)
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(log_format))
        root.addHandler(file_handler)

        if console_handler:
            console_handler.logger.info(f"日志文件已配置：{log_file}")
