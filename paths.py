"""统一管理应用数据目录（%APPDATA%\\glm-monitor）。

打包成无窗口 exe 后，脚本所在目录可能只读，历史数据库与日志
统一存到用户级 %APPDATA% 下，避免权限与多用户冲突。
开发期若无 APPDATA 环境变量，回退到脚本旁目录，方便调试。
"""
import os
import sys
from pathlib import Path

APP_NAME = "glm-monitor"


def app_dir() -> Path:
    """返回应用数据根目录，不存在则创建。

    优先 %APPDATA%\\glm-monitor；打包后无 APPDATA（极罕见）回退到
    可执行文件/脚本所在目录。
    """
    base = os.getenv("APPDATA")
    if base:
        root = Path(base) / APP_NAME
    else:
        root = Path(sys.argv[0]).resolve().parent if getattr(sys, "frozen", False) else Path.cwd()
    root.mkdir(parents=True, exist_ok=True)
    return root


def db_path() -> Path:
    """SQLite 数据库路径。"""
    return app_dir() / "usage.db"


def log_path() -> Path:
    """日志文件路径。"""
    return app_dir() / "monitor.log"
