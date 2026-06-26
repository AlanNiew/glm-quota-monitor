"""系统托盘：图标按用量变色，提供刷新/退出菜单。"""
from PIL import Image, ImageDraw
import pystray


class TrayApp:
    """pystray 托盘应用。"""

    def __init__(self, monitor):
        self.monitor = monitor
        self.icon = None

    def _make_image(self, pct):
        """根据使用百分比生成对应颜色的圆形图标。"""
        if pct is None:
            color = (110, 110, 110)
        elif pct >= 95:
            color = (220, 53, 69)
        elif pct >= 90:
            color = (253, 126, 30)
        elif pct >= 80:
            color = (255, 193, 7)
        else:
            color = (40, 167, 69)
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([6, 6, 58, 58], fill=color + (255,))
        d.ellipse([20, 20, 44, 44], fill=(30, 30, 30, 255))
        return img

    def _overall_pct(self, state):
        """取两个配额百分比的最大值作为整体状态。"""
        if not state or not state.ok:
            return None
        pcts = [p for p in (state.tokens_pct, state.time_pct) if p is not None]
        return max(pcts) if pcts else None

    def _build_title(self, state):
        """构建托盘 hover 提示文本。"""
        if not state or not state.ok:
            return "GLM 用量监控 · 等待数据..."
        t = f"{state.tokens_pct}%" if state.tokens_pct is not None else "—"
        c = f"{state.time_pct}%" if state.time_pct is not None else "—"
        return f"GLM 用量监控  Token {t} | 调用 {c}"

    def update(self, state):
        """刷新托盘图标与提示。"""
        if self.icon is None:
            return
        pct = self._overall_pct(state)
        self.icon.icon = self._make_image(pct)
        self.icon.title = self._build_title(state)

    def _on_refresh(self, icon, item):
        """菜单：立即刷新。"""
        self.monitor.refresh_now.set()

    def _on_exit(self, icon, item):
        """菜单：退出。"""
        self.monitor.stop_event.set()
        icon.stop()

    def start(self):
        """在子线程启动托盘（非阻塞）。"""
        menu = pystray.Menu(
            pystray.MenuItem("立即刷新", self._on_refresh),
            pystray.MenuItem("退出", self._on_exit),
        )
        self.icon = pystray.Icon(
            "glm-quota-monitor",
            self._make_image(None),
            "GLM 用量监控 · 启动中...",
            menu,
        )
        self.icon.run_detached()

    def stop(self):
        """停止托盘图标（pystray 的 run_detached 创建的是非 daemon 线程，
        需显式停止，否则用户按 q 退出时进程会挂起）。"""
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:
                pass
