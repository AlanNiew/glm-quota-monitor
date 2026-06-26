"""Token 消耗量悬浮球：无边框置顶小窗口，圆球显示 Token 用量百分比。

独立子线程运行 tkinter mainloop，通过 after 定时轮询 monitor.state 更新显示，
确保跨线程安全（update/stop 投递到 Tk 线程执行）。

交互：左键拖动移动位置，右键弹出退出菜单。
"""
import threading
import tkinter as tk

# 透明键色：窗口背景用此色 + -transparentcolor 使圆球外区域完全透明。
# 选 magenta 因与球体颜色（红/橙/黄/绿/灰）无冲突。
_TRANSPARENT = "#FF00FF"


def _ball_color(pct):
    """按百分比返回（球色, 文字色），与托盘图标逻辑一致。"""
    if pct is None:
        return "#6E6E6E", "#FFFFFF"
    if pct >= 95:
        return "#DC3545", "#FFFFFF"
    if pct >= 90:
        return "#FD7E1E", "#FFFFFF"
    if pct >= 80:
        return "#FFC107", "#1E1E1E"
    return "#28A745", "#FFFFFF"


class FloatBall:
    """Token 悬浮球。"""

    SIZE = 64  # 球直径（像素）

    def __init__(self, monitor):
        self.monitor = monitor
        self._root = None
        self._canvas = None
        self._thread = None
        self._drag_x = 0
        self._drag_y = 0

    def start(self):
        """在子线程启动悬浮球（非阻塞）。"""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """关闭悬浮球（可跨线程调用，通过 after 投递到 Tk 线程）。"""
        if self._root is not None:
            try:
                self._root.after(0, self._root.destroy)
            except Exception:
                pass

    # —— 以下方法均在 Tk 线程内执行 ——

    def _run(self):
        """悬浮球主循环（子线程；tkinter 全生命周期在此线程内）。"""
        try:
            self._root = tk.Tk()
        except Exception:
            return  # tkinter 不可用，静默跳过

        root = self._root
        root.overrideredirect(True)  # 无边框
        root.attributes("-topmost", True)  # 置顶

        # 尝试透明背景；非 Windows 退化为深色方块
        bg = _TRANSPARENT
        try:
            root.attributes("-transparentcolor", _TRANSPARENT)
        except Exception:
            bg = "#1A1A1A"

        # 初始位置：屏幕右下角，避开任务栏
        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        root.geometry(f"{self.SIZE}x{self.SIZE}+{sw - self.SIZE - 20}+{sh - self.SIZE - 80}")

        self._canvas = tk.Canvas(
            root, width=self.SIZE, height=self.SIZE,
            bg=bg, highlightthickness=0,
        )
        self._canvas.pack()

        menu = tk.Menu(root, tearoff=0)
        menu.add_command(label="退出悬浮球", command=self.stop)
        self._menu = menu

        # 左键拖动 / 右键菜单
        self._canvas.bind("<ButtonPress-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonPress-3>", lambda e: self._menu.tk_popup(e.x_root, e.y_root))

        self._refresh()
        root.mainloop()

    def _on_press(self, event):
        """记录拖动起点（鼠标相对于 Canvas 的坐标）。"""
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        """随鼠标移动窗口。"""
        x = self._root.winfo_x() + (event.x - self._drag_x)
        y = self._root.winfo_y() + (event.y - self._drag_y)
        self._root.geometry(f"+{x}+{y}")

    def _refresh(self):
        """每秒读取最新状态并重绘球体。"""
        state = self.monitor.state

        if state is None:
            bg, fg = "#6E6E6E", "#FFFFFF"
            num = "—"
        elif not state.ok:
            bg, fg = "#495057", "#FFFFFF"
            num = "!"
        else:
            bg, fg = _ball_color(state.tokens_pct)
            pct = state.tokens_pct
            num = str(int(round(pct))) if pct is not None else "—"

        c = self._canvas
        c.delete("all")
        c.create_oval(2, 2, self.SIZE - 2, self.SIZE - 2,
                      fill=bg, outline="#1A1A1A", width=2)
        c.create_text(self.SIZE / 2, self.SIZE / 2 - 4,
                      text=num, fill=fg, font=("Segoe UI", 17, "bold"))
        c.create_text(self.SIZE / 2, self.SIZE / 2 + 16,
                      text="%", fill=fg, font=("Segoe UI", 9))

        try:
            self._root.after(1000, self._refresh)
        except Exception:
            pass
