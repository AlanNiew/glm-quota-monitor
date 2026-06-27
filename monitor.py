"""GLM 用量监控主程序：终端仪表盘 + 系统托盘 + 定时拉取。"""
import sys
import threading
from datetime import datetime

from config import load_config
from quota_client import QuotaClient
from storage import Storage
from alerter import Alerter
from tray import TrayApp
from float_ball import FloatBall
from logger import setup


class Monitor:
    """监控核心：编排数据拉取、存储、告警、托盘与仪表盘。"""

    AUTH_FAIL_THRESHOLD = 2  # 连续失败达到此次数 → 触发凭证过期告警

    def __init__(self):
        self.log = setup()
        self.config = load_config()
        if not self.config.authorization:
            self.log.error("未配置 GLM_AUTHORIZATION，请在 .env 中填写凭证")
            sys.exit(1)

        self.client = QuotaClient(self.config)
        self.storage = Storage(self.config.db_path)
        self.alerter = Alerter(self.config)
        self.tray = TrayApp(self) if self.config.tray else None
        if self.config.dashboard:
            from dashboard import Dashboard  # 延迟加载，避免 rich/plotext 拖入后台运行模式
            self.dashboard = Dashboard(self)
        else:
            self.dashboard = None
        self.float_ball = FloatBall(self) if self.config.float_ball else None

        self.lock = threading.Lock()
        self.state = None              # 最近一次 UsageData
        self.last_fetch = None         # 最近一次拉取时间
        self.trend_data = []           # 当前窗口趋势记录
        self.trend_window = 24         # 当前趋势窗口（小时）
        self.consecutive_failures = 0  # 连续失败次数

        self.stop_event = threading.Event()
        self.refresh_now = threading.Event()

    def refresh_trend(self, hours: int):
        """重新查询指定窗口的趋势数据。"""
        self.trend_window = hours
        self.trend_data = self.storage.query_trend(hours)

    def _do_fetch(self):
        """执行一次拉取并更新全部状态。"""
        usage = self.client.fetch()
        with self.lock:
            self.state = usage
            self.last_fetch = datetime.now()
        if usage.ok:
            self.consecutive_failures = 0
            self.alerter.reset_auth()  # 凭证恢复，重置失效告警
            self.storage.insert(usage)
            self.trend_data = self.storage.query_trend(self.trend_window)
            self.alerter.check("tokens", usage.tokens_pct)
            self.alerter.check("time", usage.time_pct)
        else:
            self.consecutive_failures += 1
            self.log.warning("拉取失败（第 %d 次）：%s", self.consecutive_failures, usage.error)
            if self.consecutive_failures == self.AUTH_FAIL_THRESHOLD:
                self.alerter.notify_auth_expired(usage.error)
        if self.tray is not None:
            self.tray.update(usage)

    def _fetch_loop(self):
        """定时拉取：启动即拉一次，之后按间隔刷新（可被立即刷新提前唤醒）。"""
        while not self.stop_event.is_set():
            self._do_fetch()
            self.refresh_now.wait(timeout=self.config.refresh_interval)
            if self.refresh_now.is_set():
                self.refresh_now.clear()

    def run(self):
        """启动监控，按配置开关分配线程。

        线程规则：
        - 有悬浮球 → QApplication 占主线程（Qt 要求）；有仪表盘则仪表盘移子线程
        - 无悬浮球有仪表盘 → 仪表盘占主线程
        - 两者都无 → 主线程 wait(stop_event)，仅托盘 + 后台拉取
        """
        self.log.info(
            "监控启动（dashboard=%s tray=%s float_ball=%s）",
            self.config.dashboard, self.config.tray is not None, self.config.float_ball is not None,
        )
        threading.Thread(target=self._fetch_loop, daemon=True).start()

        if self.tray is not None:
            try:
                self.tray.start()
            except Exception as e:
                self.log.warning("托盘启动失败（不影响其他功能）: %s", e)

        if self.float_ball is not None:
            if self.dashboard is not None:
                threading.Thread(
                    target=self.dashboard.run, args=(self.stop_event,), daemon=True
                ).start()
            self._run_blocking(self.float_ball.run_main)
        elif self.dashboard is not None:
            self._run_blocking(lambda: self.dashboard.run(self.stop_event))
        else:
            self.log.info("监控运行中（仅托盘 + 后台拉取），通过托盘菜单退出")
            self._run_blocking(self.stop_event.wait)

    def _run_blocking(self, target):
        """执行阻塞函数，退出时统一清理托盘和悬浮球。"""
        try:
            target()
        finally:
            if self.tray is not None:
                self.tray.stop()
            if self.float_ball is not None:
                self.float_ball.stop()
            self.log.info("已退出监控")


if __name__ == "__main__":
    Monitor().run()