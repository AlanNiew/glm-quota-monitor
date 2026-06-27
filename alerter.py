"""阈值告警：达到阈值时发送桌面通知，每档只触发一次、回落重置。

另含凭证失效告警：连续请求失败时通知一次，恢复正常后重置。
"""
from plyer import notification


class Alerter:
    """告警管理器。"""

    LABELS = {1: "注意", 2: "警告", 3: "严重"}
    TITLE_MAP = {
        "tokens_weekly": "Token 用量（每周）",
        "tokens_5h": "Token 用量（5 小时）",
        "time": "调用次数配额",
    }

    def __init__(self, config):
        # 阈值与档位（按由低到高排列）
        self.thresholds = [(config.warn1, 1), (config.warn2, 2), (config.warn3, 3)]
        self.triggered = {
            "tokens_weekly": 0,
            "tokens_5h": 0,
            "time": 0,
        }  # 各维度已触发的最高档
        self.auth_notified = False  # 凭证失效告警是否已触发

    def _level_of(self, pct) -> int:
        """返回百分比对应的告警档位（0 表示未触发）。"""
        if pct is None:
            return 0
        level = 0
        for threshold, lvl in self.thresholds:
            if pct >= threshold:
                level = max(level, lvl)
        return level

    def check(self, name: str, pct) -> None:
        """检查指定维度是否需要告警。"""
        level = self._level_of(pct)
        if level > self.triggered[name]:
            # 进入更高档 → 触发通知
            self.triggered[name] = level
            self._notify(name, pct, level)
        elif level < self.triggered[name]:
            # 回落到阈值以下 → 重置，允许后续再次触发
            self.triggered[name] = level

    def notify_auth_expired(self, error: str = "") -> None:
        """凭证连续失效告警：只触发一次，需 reset_auth 恢复后才能再次触发。"""
        if self.auth_notified:
            return
        self.auth_notified = True
        try:
            notification.notify(
                title="GLM 用量监控 · 凭证可能已过期",
                message=(
                    "连续请求失败，token 可能失效。\n"
                    "请 F12 重新抓包，更新 .env 的 GLM_AUTHORIZATION。\n"
                    f"{error}"
                ),
                app_name="GLM 用量监控",
                timeout=15,
            )
        except Exception:
            pass

    def reset_auth(self) -> None:
        """凭证恢复正常，重置失效告警状态。"""
        self.auth_notified = False

    def _notify(self, name: str, pct: float, level: int) -> None:
        """发送 Windows 桌面通知（失败不影响主流程）。"""
        label = self.LABELS.get(level, "提醒")
        try:
            notification.notify(
                title=f"GLM {self.TITLE_MAP.get(name, name)} · {label}",
                message=f"已使用 {pct}%，达到 {label} 阈值",
                app_name="GLM 用量监控",
                timeout=10,
            )
        except Exception:
            pass