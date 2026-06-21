# File: utils/logger_util.py
"""日志工具模块 — 控制台 + 文件双输出日志系统。

基于标准库 :mod:`logging` 封装，支持：
- 控制台实时输出（可开关）
- 文件按天切割（TimedRotatingFileHandler）
- 统一格式：时间 | 级别 | 模块名 | 消息

Usage::

    from utils.logger_util import get_logger
    logger = get_logger(__name__)
    logger.info('测试开始')
    logger.error('元素定位失败', exc_info=True)
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional


# ------------------------------------------------------------------
# 模块级全局状态 — 确保整个进程只初始化一次
# ------------------------------------------------------------------

_initialized: bool = False
_log_dir: Optional[Path] = None


def init_logging(
    log_dir: Optional[Path] = None,
    level: str = 'INFO',
    fmt: str = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt: str = '%Y-%m-%d %H:%M:%S',
    when: str = 'midnight',
    interval: int = 1,
    backup_count: int = 30,
    console_output: bool = True,
) -> None:
    """初始化日志系统（整个进程生命周期仅执行一次）。

    Args:
        log_dir: 日志文件目录，默认 ``automation/logs/``。
        level: 日志级别，如 ``INFO``、``DEBUG``。
        fmt: 日志格式字符串。
        datefmt: 时间格式字符串。
        when: 切割间隔类型（``midnight`` / ``H`` / ``D`` 等）。
        interval: 切割间隔数值。
        backup_count: 保留的历史日志份数。
        console_output: 是否同时输出到控制台。
    """
    global _initialized, _log_dir  # noqa: PLW0603

    if _initialized:
        return

    # 解析日志目录
    if log_dir is None:
        log_dir = (
            Path(__file__).resolve().parent.parent / 'logs'
        )
    log_dir.mkdir(parents=True, exist_ok=True)
    _log_dir = log_dir

    # 获取 root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    # 清除已有 handler（防止重复添加）
    root_logger.handlers.clear()

    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    # 文件 handler — 按天切割
    file_handler = TimedRotatingFileHandler(
        filename=str(log_dir / 'automation.log'),
        when=when,
        interval=interval,
        backupCount=backup_count,
        encoding='utf-8',
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 控制台 handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """获取指定模块的 logger 实例。

    如果日志系统尚未初始化，以默认配置自动初始化（避免首次调用报错）。

    Args:
        name: 通常传入 ``__name__``，用于标识日志来源模块。

    Returns:
        配置好的 :class:`logging.Logger` 实例。
    """
    if not _initialized:
        init_logging()
    return logging.getLogger(name)


def get_log_dir() -> Optional[Path]:
    """返回当前日志文件目录路径。

    Returns:
        日志目录 Path，未初始化时返回 None。
    """
    return _log_dir
