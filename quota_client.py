"""GLM 配额接口请求与解析。"""
from dataclasses import dataclass, field
from typing import List, Optional

import requests


@dataclass
class UsageData:
    """一次拉取得到的用量数据。"""
    level: str = ""                                        # 套餐等级，如 "lite"
    # —— Token 用量配额（可能存在多条 TOKENS_LIMIT，按 (unit, number) 区分周期）——
    tokens_weekly_pct: Optional[float] = None              # 每周限额已用% (unit=6, number=1)
    tokens_weekly_reset: Optional[int] = None              # 每周限额重置时间（ms）
    tokens_5h_pct: Optional[float] = None                  # 5 小时滚动窗口已用% (unit=3, number=5)
    tokens_5h_reset: Optional[int] = None                  # 5 小时窗口重置时间（ms）
    # 旧字段：取 weekly 与 5h 中较大者，保持历史趋势曲线与外部脚本兼容
    tokens_pct: Optional[float] = None
    tokens_next_reset: Optional[int] = None
    # —— 调用次数配额 ——
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
                # 多条 TOKENS_LIMIT 用 (unit, number) 元组区分周期：
                #   (6, 1) → 每周，(3, 5) → 5 小时滚动窗口
                key = (lim.get("unit"), lim.get("number"))
                pct = lim.get("percentage")
                reset = lim.get("nextResetTime")
                if key == (6, 1):
                    result.tokens_weekly_pct = pct
                    result.tokens_weekly_reset = reset
                elif key == (3, 5):
                    result.tokens_5h_pct = pct
                    result.tokens_5h_reset = reset
                else:
                    # 未知周期：保守记录到日志可用字段，避免静默丢失
                    # （暂复用 weekly 槽位，待新增周期类型时再扩展）
                    pass
            elif limit_type == "TIME_LIMIT":
                # 调用次数配额：含绝对值与按模型拆分
                result.time_total = lim.get("usage")
                result.time_current = lim.get("currentValue")
                result.time_remaining = lim.get("remaining")
                result.time_pct = lim.get("percentage")
                result.time_next_reset = lim.get("nextResetTime")
                result.time_details = lim.get("usageDetails") or []

        # 兼容旧字段：取 weekly 与 5h 中已用较大者，重置时间取更早到来的那个，
        # 让趋势曲线、托盘标题等老消费者无需改动即可呈现「最紧迫」的 Token 状态。
        pcts = [p for p in (result.tokens_weekly_pct, result.tokens_5h_pct) if p is not None]
        if pcts:
            result.tokens_pct = max(pcts)
            # tokens_next_reset 对应到触发 max 的那条限额的重置时间
            if result.tokens_weekly_pct is not None and result.tokens_5h_pct is not None:
                if result.tokens_weekly_pct >= result.tokens_5h_pct:
                    result.tokens_next_reset = result.tokens_weekly_reset
                else:
                    result.tokens_next_reset = result.tokens_5h_reset
            elif result.tokens_weekly_pct is not None:
                result.tokens_next_reset = result.tokens_weekly_reset
            else:
                result.tokens_next_reset = result.tokens_5h_reset

        return result
