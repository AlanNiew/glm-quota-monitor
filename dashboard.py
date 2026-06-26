"""rich 终端仪表盘渲染与键盘交互。"""
import time
from datetime import datetime

from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

import plotext as plt


WINDOWS = ["6h", "24h", "7d"]
WINDOW_HOURS = {"6h": 6, "24h": 24, "7d": 168}


class Dashboard:
    """终端仪表盘。"""

    def __init__(self, monitor):
        self.monitor = monitor
        self.window = "24h"

    def set_window(self, key: str):
        """切换趋势窗口。"""
        if key in WINDOW_HOURS and key != self.window:
            self.window = key
            self.monitor.refresh_trend(WINDOW_HOURS[key])

    def _title_text(self) -> str:
        """生成终端窗口标题（反映到任务栏按钮）。"""
        state = self.monitor.state
        if not state:
            return "GLM 用量监控 · 启动中"
        if not state.ok:
            fails = self.monitor.consecutive_failures
            return f"GLM 监控 · 请求失败({fails}次)"
        t = f"{state.tokens_pct}%" if state.tokens_pct is not None else "—"
        c = f"{state.time_pct}%" if state.time_pct is not None else "—"
        lvl = f"[{state.level}]" if state.level else ""
        return f"GLM {lvl} Token {t} | 调用 {c}"

    def _fmt_reset(self, ms):
        """毫秒时间戳转可读时间。"""
        if not ms:
            return "—"
        try:
            return datetime.fromtimestamp(ms / 1000).strftime("%m-%d %H:%M")
        except Exception:
            return "—"

    def _bar(self, pct, width=24):
        """生成带颜色的文本进度条。"""
        if pct is None:
            return "[dim]数据缺失[/dim]"
        ratio = max(0.0, min(1.0, pct / 100.0))
        filled = int(ratio * width)
        if pct >= 95:
            color = "bold red"
        elif pct >= 90:
            color = "bold orange3"
        elif pct >= 80:
            color = "bold yellow"
        else:
            color = "bold green"
        bar = "█" * filled + "░" * (width - filled)
        return f"[{color}]{bar}[/] [{color}]{pct}%[/]"

    def _eta_seconds(self, state):
        """根据历史速率估算 TIME_LIMIT 预计耗尽秒数。"""
        trend = self.monitor.trend_data
        if not state or state.time_remaining is None or len(trend) < 2:
            return None
        try:
            first_ts = datetime.fromisoformat(trend[0]["ts"])
            last_ts = datetime.fromisoformat(trend[-1]["ts"])
            dt = (last_ts - first_ts).total_seconds()
            if dt <= 0:
                return None
            first_v = trend[0]["time_current"]
            last_v = trend[-1]["time_current"]
            if first_v is None or last_v is None:
                return None
            rate = (last_v - first_v) / dt  # 次/秒
            if rate <= 0:
                return None
            return state.time_remaining / rate
        except Exception:
            return None

    def _fmt_eta(self, secs):
        """把秒数格式化为可读时长。"""
        if secs is None:
            return "—"
        if secs < 3600:
            return f"{int(secs / 60)} 分钟"
        if secs < 86400:
            return f"{secs / 3600:.1f} 小时"
        return f"{secs / 86400:.1f} 天"

    def _render_trend(self):
        """用 plotext 渲染双折线趋势图，返回 rich Text。"""
        trend = self.monitor.trend_data
        try:
            plt.clf()
            plt.theme("clear")
            plt.plotsize(70, 12)
            xs = list(range(len(trend)))
            token_y = [r.get("tokens_pct") for r in trend]
            time_y = [r.get("time_pct") for r in trend]
            plotted = False
            if any(v is not None for v in token_y):
                plt.plot(xs, token_y, label="Token%")
                plotted = True
            if any(v is not None for v in time_y):
                plt.plot(xs, time_y, label="调用%")
                plotted = True
            if not plotted or len(trend) < 2:
                return Text("  数据积累中，至少需要 2 条记录...", style="dim")
            plt.title(f"用量趋势 (近 {self.window})")
            plt.ylabel("已用 %")
            return Text.from_ansi(plt.build())
        except Exception:
            return Text("  趋势图渲染失败", style="dim red")

    def build(self) -> Layout:
        """构建整页布局。"""
        root = Layout()
        root.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )
        root["body"].split_row(
            Layout(name="quota"),
            Layout(name="trend"),
        )

        state = self.monitor.state
        last = self.monitor.last_fetch

        # —— 头部 ——
        now = datetime.now()
        if last:
            elapsed = int((now - last).total_seconds())
            remain = max(0, self.monitor.config.refresh_interval - elapsed)
            status_time = f"上次刷新 {last.strftime('%H:%M:%S')}   下次 {remain}s"
        else:
            status_time = "等待首次刷新..."
        level = f"[{state.level}]" if state and state.level else ""
        root["header"].update(
            Panel(
                Text(f"● GLM 用量监控  {level}    {status_time}", style="bold cyan"),
                style="cyan",
            )
        )

        # —— 左：配额 ——
        qtable = Table.grid(padding=(0, 2))
        qtable.add_column(style="bold")
        qtable.add_column()

        if not state:
            qtable.add_row("", "正在获取数据...")
        elif not state.ok:
            fails = self.monitor.consecutive_failures
            hint = ""
            if fails >= 2:
                hint = "\n[yellow]! 凭证可能已过期，请 F12 重新抓包，更新 .env 的 GLM_AUTHORIZATION[/yellow]"
            qtable.add_row(
                "状态",
                f"[red]请求失败（连续 {fails} 次）[/red]\n[dim]{state.error}[/dim]{hint}",
            )
        else:
            # Token 用量配额
            qtable.add_row("Token 用量", self._bar(state.tokens_pct))
            qtable.add_row("  重置于", self._fmt_reset(state.tokens_next_reset))
            qtable.add_row("", "")
            # 调用次数配额
            qtable.add_row("调用次数", self._bar(state.time_pct))
            cur = state.time_current if state.time_current is not None else "—"
            tot = state.time_total if state.time_total is not None else "—"
            rem = state.time_remaining if state.time_remaining is not None else "—"
            qtable.add_row("  进度", f"{cur} / {tot}   剩余 {rem}")
            qtable.add_row("  预计耗尽", self._fmt_eta(self._eta_seconds(state)))
            qtable.add_row("  重置于", self._fmt_reset(state.time_next_reset))
            # 模型拆分
            if state.time_details:
                detail = " · ".join(
                    f"{d.get('modelCode')} {d.get('usage')}" for d in state.time_details
                )
                qtable.add_row("  按模型", detail)
        root["quota"].update(Panel(qtable, title="配额", border_style="blue"))

        # —— 右：趋势 ——
        root["trend"].update(
            Panel(self._render_trend(), title=f"趋势 [{self.window}]", border_style="magenta")
        )

        # —— 底部 ——
        w1, w2, w3 = (
            self.monitor.config.warn1,
            self.monitor.config.warn2,
            self.monitor.config.warn3,
        )
        cur_key = WINDOWS.index(self.window) + 1
        win_hint = "  ".join(
            f"[{'bold' if i == cur_key else 'dim'}][{i}] {WINDOWS[i-1]}[/]"
            for i in (1, 2, 3)
        )
        root["footer"].update(
            Panel(
                Text(
                    f"阈值 {w1}/{w2}/{w3}%   通知已开启   |   趋势窗口: {win_hint}   [q] 退出",
                    style="dim",
                ),
                style="dim",
            )
        )

        return root

    def run(self, stop_event):
        """主线程运行 Live 渲染 + 键盘监听 + 终端标题（任务栏）更新。"""
        import threading

        threading.Thread(target=self._key_loop, args=(stop_event,), daemon=True).start()
        with Live(self.build(), refresh_per_second=1, screen=False) as live:
            while not stop_event.is_set():
                live.console.set_window_title(self._title_text())  # 同步到任务栏按钮
                live.update(self.build())
                time.sleep(1)
            live.console.set_window_title(self._title_text())
            live.update(self.build())

    def _key_loop(self, stop_event):
        """Windows 下非阻塞读取按键。"""
        try:
            import msvcrt
        except ImportError:
            return
        while not stop_event.is_set():
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch == b"1":
                    self.set_window("6h")
                elif ch == b"2":
                    self.set_window("24h")
                elif ch == b"3":
                    self.set_window("7d")
                elif ch in (b"q", b"Q"):
                    stop_event.set()
                    break
            time.sleep(0.1)