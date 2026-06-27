"""开机自启：读写 HKCU\\...\\Run 注册表项。

打包后用 exe 路径；开发期用 python.exe 运行 monitor.py。
"""
import os
import sys
import winreg

APP_NAME = "GLMMonitor"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _command() -> str:
    """构造自启命令行。

    打包（PyInstaller frozen）：直接运行 exe。
    开发期：用当前解释器运行 monitor.py 绝对路径。
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    script = os.path.abspath(os.path.join(os.path.dirname(__file__), "monitor.py"))
    return f'"{sys.executable}" "{script}"'


def is_enabled() -> bool:
    """查询开机自启是否已开启。"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP_NAME)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def enable() -> bool:
    """开启开机自启，返回是否成功。"""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, _command())
        return True
    except OSError as e:
        from logger import get
        get().warning("写入开机自启失败：%s", e)
        return False


def disable() -> bool:
    """关闭开机自启（未开启也返回 True）。"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, APP_NAME)
        return True
    except FileNotFoundError:
        return True  # 本来就没开
    except OSError as e:
        from logger import get
        get().warning("删除开机自启失败：%s", e)
        return False


def toggle() -> bool:
    """切换开关，返回切换后的状态。"""
    if is_enabled():
        disable()
        return False
    enable()
    return True
