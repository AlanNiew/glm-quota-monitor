"""配置加载：从 .env 读取凭证与运行参数。"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """运行配置。"""
    authorization: str        # 接口认证 token（请求头 authorization）
    organization: str         # bigmodel-organization
    project: str              # bigmodel-project
    url: str                  # 配额接口地址
    refresh_interval: int     # 刷新间隔（秒）
    warn1: float              # 注意阈值（%）
    warn2: float              # 警告阈值（%）
    warn3: float              # 严重阈值（%）
    db_path: str              # SQLite 数据库路径
    dashboard: bool           # 是否显示终端仪表盘
    tray: bool                # 是否显示系统托盘
    float_ball: bool          # 是否显示 Token 悬浮球


def _flag(name: str, default: str = "1") -> bool:
    """解析布尔环境变量（1/true/yes/on → True）。"""
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def load_config() -> Config:
    """加载并返回配置。"""
    return Config(
        authorization=os.getenv("GLM_AUTHORIZATION", ""),
        organization=os.getenv("GLM_ORGANIZATION", ""),
        project=os.getenv("GLM_PROJECT", ""),
        url=os.getenv("GLM_API_URL", "https://bigmodel.cn/api/monitor/usage/quota/limit"),
        refresh_interval=int(os.getenv("REFRESH_INTERVAL", "60")),
        warn1=float(os.getenv("WARN_1", "80")),
        warn2=float(os.getenv("WARN_2", "90")),
        warn3=float(os.getenv("WARN_3", "95")),
        db_path=os.getenv("DB_PATH", "usage.db"),
        dashboard=_flag("DASHBOARD"),
        tray=_flag("TRAY"),
        float_ball=_flag("FLOAT_BALL"),
    )
