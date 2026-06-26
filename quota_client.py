"""GLM 配额接口请求与解析。"""
from dataclasses import dataclass, field
from typing import List, Optional

import requests


@dataclass
class UsageData:
    """一次拉取得到的用量数据。"""
    level: str = ""                                        # 套餐等级，如 "lite"
    tokens_pct: Optional[float] = None                     # TOKENS_LIMIT 已用百分比
    tokens_next_reset: Optional[int] = None                # TOKENS_LIMIT 重置时间（毫秒）
    time_total: Optional[int] = None                       # TIME_LIMIT 总额（usage）
    time_current: Optional[int] = None                     # TIME_LIMIT 已用（currentValue）
    time_remaining: Optional[int] = None                   # TIME_LIMIT 剩余（remaining）
    time_pct: Optional[float] = None                       # TIME_LIMIT 已用百分比
    time_next_reset: Optional[int] = None                  # TIME_LIMIT 重置时间（毫秒）
    time_details: List[dict] = field(default_factory=list)  # 按模型拆分用量
    ok: bool = False                                       # 是否成功
    error: str = ""                                        # 错误信息


class QuotaClient:
    """配额接口客户端。"""

    def __init__(self, config):
        self.url = config.url
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/149.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "accept-language": "zh",
            "authorization": config.authorization,
            "bigmodel-organization": config.organization,
            "bigmodel-project": config.project,
            "referer": "https://bigmodel.cn/coding-plan/personal/usage",
            "set-language": "zh",
        }

    def fetch(self) -> UsageData:
        """请求接口并解析为 UsageData。"""
        try:
            resp = requests.get(self.url, headers=self.headers, timeout=15)
            resp.raise_for_status()
            body = resp.json()
        except Exception as e:
            return UsageData(ok=False, error=f"请求失败: {e}")

        if body.get("code") != 200 or not body.get("success"):
            return UsageData(ok=False, error=body.get("msg", "接口返回非成功状态"))

        data = body.get("data", {}) or {}
        result = UsageData(level=data.get("level", ""), ok=True)

        for lim in data.get("limits", []) or []:
            limit_type = lim.get("type")
            if limit_type == "TOKENS_LIMIT":
                # Token 用量配额：仅返回百分比与重置时间
                result.tokens_pct = lim.get("percentage")
                result.tokens_next_reset = lim.get("nextResetTime")
            elif limit_type == "TIME_LIMIT":
                # 调用次数配额：含绝对值与按模型拆分
                result.time_total = lim.get("usage")
                result.time_current = lim.get("currentValue")
                result.time_remaining = lim.get("remaining")
                result.time_pct = lim.get("percentage")
                result.time_next_reset = lim.get("nextResetTime")
                result.time_details = lim.get("usageDetails") or []

        return result
