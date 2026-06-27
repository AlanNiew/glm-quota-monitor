"""日志系统：轮转文件 + 控制台双输出。

打包为 --windowed 无控制台应用后，print 输出无处可去；本模块提供
基于 logging 的统一日志，写到 %APPDATA%\\glm-monitor\\monitor.log，
单文件 500KB 轮转、保留 3 份历史。控制台 handler 在无 stderr 环境
（PyInstaller --windowed）下静默跳过，不影响文件日志。

用法：
    from logger import setup, get
    setup()                       # 程序入口初始化一次
    log = get()                   # 任意模块取 logger
    log.info("启动完成")
"""
import logging
from logging.handlers import RotatingFileHandler

from paths import log_path

_INITIALIZED = False
_LOGGER_NAME = "glm"


def setup(level: str = "INFO") -> logging.Logger:
    """初始化根 logger。重复调用安全（只生效一次）。"""
    global _INITIALIZED
    logger = logging.getLogger(_LOGGER_NAME)
    if _INITIALIZED:
        return logger
    _INITIALIZED = True

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False  # 避免重复打印到 root logger
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 文件 handler（轮转：单文件 500KB，保留 3 份）
    try:
        fh = RotatingFileHandler(
            log_path(), maxBytes=512_000, backupCount=3, encoding="utf-8"
        )
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        # 日志目录不可写时静默，避免阻断主程序
        pass

    # 控制台 handler（开发期可见；打包 --windowed 时 sys.stderr 为 None 则跳过）
    try:
        import sys
        if sys.stderr is not None:
            ch = logging.StreamHandler()
            ch.setFormatter(fmt)
            logger.addHandler(ch)
    except Exception:
        pass

    return logger


def get() -> logging.Logger:
    """获取应用 logger（未初始化则自动按 INFO 初始化）。"""
    if not _INITIALIZED:
        setup()
    return logging.getLogger(_LOGGER_NAME)
