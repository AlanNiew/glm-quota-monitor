"""Token 消耗量悬浮球（PySide6）：环形进度条，浅色风格，抗锯齿渲染。

QPainter + Antialiasing 绘制四层：柔和投影 → 暗色轨道环 → 彩色进度弧
→ 白色渐变内圆 → 深色百分比文字。独立子线程运行 QApplication.exec()，
QTimer 每秒触发重绘读取最新状态。

交互：左键拖动移动，右键弹出退出菜单。
"""
import sys
import threading

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QRadialGradient, QBrush
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QMenu,
)

# ── 浅色配色（Apple system colors 风格）──
_TRACK = QColor("#E5E5EA")            # 轨道环（浅灰）
_INNER_LIGHT = QColor("#FFFFFF")      # 内圆渐变中心（纯白）
_INNER_DARK = QColor("#F2F2F7")       # 内圆渐变边缘（微灰）
_INNER_BORDER = QColor("#E5E5EA")     # 内圆描边
_TEXT = QColor("#1C1C1E")             # 百分比数字（近黑）
_TEXT_DIM = QColor("#8E8E93")         # % 符号（中灰）


def _arc_color(pct):
    """按百分比返回进度弧颜色（柔和饱和度）。"""
    if pct is None:
        return QColor("#C7C7CC")  # 无数据
    if pct >= 95:
        return QColor("#FF3B30")  # 红
    if pct >= 90:
        return QColor("#FF9500")  # 橙
    if pct >= 80:
        return QColor("#FFCC00")  # 黄
    return QColor("#34C759")      # 绿


class FloatBall:
    """悬浮球管理器。QApplication 应在主线程运行（Qt 要求）。

    调用 run_main() 在主线程阻塞运行；start() 为兼容接口（子线程，可能不显示）。
    """

    def __init__(self, monitor):
        self._monitor = monitor
        self._app = None
        self._widget = None
        self._thread = None

    def run_main(self):
        """在当前线程（应为主线程）阻塞运行 QApplication。

        Qt 要求 QApplication 在主线程创建，否则窗口在 Windows 上可能不显示。
        """
        try:
            self._app = QApplication.instance() or QApplication(sys.argv[:1])
            self._widget = _BallWidget(self._monitor)
            self._app.exec()
        except Exception:
            import traceback
            traceback.print_exc()

    def start(self):
        """兼容接口：在子线程运行（不推荐，Qt 要求主线程）。"""
        self._thread = threading.Thread(target=self.run_main, daemon=True)
        self._thread.start()

    def stop(self):
        """关闭悬浮球（线程安全，可跨线程调用）。"""
        if self._app is not None:
            self._app.quit()


class _BallWidget(QWidget):
    """悬浮球窗口：无边框、透明背景、置顶、环形进度条。"""

    SIZE = 72

    def __init__(self, monitor):
        super().__init__()
        self._monitor = monitor
        self._drag_offset = None

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self.SIZE, self.SIZE)

        # 初始位置：屏幕右下角，避开任务栏
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.SIZE - 24, screen.height() - self.SIZE - 80)

        # 每秒触发重绘
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(1000)

        # 定期检查退出标志（dashboard/tray 触发退出时同步关闭 QApplication）
        self._stop_timer = QTimer(self)
        self._stop_timer.timeout.connect(self._check_stop)
        self._stop_timer.start(500)

        self.show()

    def _check_stop(self):
        """检测 monitor 的 stop_event，同步退出 QApplication。"""
        if self._monitor.stop_event.is_set():
            QApplication.quit()

    def paintEvent(self, _event):
        """绘制环形进度条：轨道环 → 进度弧 → 内圆 → 文字。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        state = self._monitor.state
        pct = state.tokens_pct if (state and state.ok) else None
        ratio = max(0.0, min(1.0, (pct or 0) / 100.0)) if pct is not None else 0.0

        S = self.SIZE
        m = 6   # 环与窗口边缘间距
        rw = 7  # 环线宽
        rect = QRectF(m, m, S - 2 * m, S - 2 * m)

        self._draw_shadow(painter, S)
        self._draw_rings(painter, rect, rw, ratio, pct)
        self._draw_inner(painter, S, m, rw, state, pct)
        painter.end()

    def _draw_shadow(self, painter, S):
        """手动画柔和投影（径向渐变黑→透明）。

        QGraphicsDropShadowEffect 与 WA_TranslucentBackground 冲突会导致
        整个透明 widget 被渲染为完全不可见，故改用手绘径向渐变模拟阴影。
        """
        grad = QRadialGradient(QPointF(S / 2, S / 2 + 3), S * 0.5)
        grad.setColorAt(0.0, QColor(0, 0, 0, 50))
        grad.setColorAt(0.6, QColor(0, 0, 0, 20))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(0, 3, S, S))

    def _draw_rings(self, painter, rect, rw, ratio, pct):
        """绘制轨道环 + 进度弧。"""
        pen = QPen(_TRACK, rw)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(rect, 0, 360 * 16)  # Qt 角度 = 实际角度 × 16

        if ratio > 0:
            # 从 12 点钟方向顺时针（start=90°×16，span 负 = 顺时针）
            pen.setColor(_arc_color(pct))
            painter.setPen(pen)
            painter.drawArc(rect, 90 * 16, int(-ratio * 360 * 16))

    def _draw_inner(self, painter, S, m, rw, state, pct):
        """绘制内圆（径向渐变）+ 百分比文字。"""
        cx, cy = S / 2, S / 2
        ir = (S / 2 - m) - rw / 2  # 内圆半径 = 环内缘

        # 内圆
        inner = QRectF(cx - ir, cy - ir, 2 * ir, 2 * ir)
        grad = QRadialGradient(QPointF(cx, cy - ir * 0.4), ir * 1.3)
        grad.setColorAt(0, _INNER_LIGHT)
        grad.setColorAt(1, _INNER_DARK)
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(_INNER_BORDER, 1))
        painter.drawEllipse(inner)

        # 百分比数字
        if state is None:
            num = "—"
        elif not state.ok:
            num = "!"
        else:
            num = str(int(round(pct)))

        painter.setPen(_TEXT)
        font = QFont("Segoe UI", 15)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(0, -3, S, S), Qt.AlignCenter, num)

        painter.setPen(_TEXT_DIM)
        painter.setFont(QFont("Segoe UI", 7))
        painter.drawText(QRectF(0, 14, S, S), Qt.AlignCenter, "%")

    # —— 鼠标交互 ——

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, _event):
        self._drag_offset = None

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("退出悬浮球", self._quit)
        menu.exec(event.globalPos())

    def _quit(self):
        """退出悬浮球并通知整个监控停止。"""
        self._monitor.stop_event.set()
        QApplication.quit()
