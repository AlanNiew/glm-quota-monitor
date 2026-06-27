# GLM 用量监控

监控智谱 GLM（bigmodel.cn）套餐的 Token 与调用次数用量，提供终端仪表盘、桌面悬浮球与系统托盘，支持阈值告警与开机自启。可打包成无窗口后台应用。

## 功能

- 桌面悬浮球：环形进度条，颜色随用量变化（绿/黄/橙/红），鼠标悬停显示用量明细（重置时间、按模型拆分等）
- 系统托盘：图标变色，右键菜单（刷新/显隐悬浮球/打开数据目录/开机自启/退出），双击切换悬浮球
- 终端仪表盘：双配额进度条、调用次数绝对值、按模型拆分、预计耗尽时间、双折线趋势（可选，开发调试用）
- 历史记录：SQLite 存储，6h / 24h / 7d 趋势窗口
- 阈值告警：80% / 90% / 95% 桌面通知（每档只提醒一次，回落重置）
- 开机自启：托盘菜单一键开关（写 HKCU 注册表）
- 日志系统：轮转文件日志，便于后台运行时排错
- 每 60s 自动刷新（启动即拉一次）

## 快速开始（开发模式）

```powershell
cd glm-quota-monitor
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt

Copy-Item .env.example .env
# 编辑 .env，填入你的 GLM 凭证

.\venv\Scripts\python monitor.py
```

## 配置（.env）

| 变量 | 说明 | 默认 |
|------|------|------|
| `GLM_AUTHORIZATION` | 接口认证 token（请求头 `authorization`） | — |
| `GLM_ORGANIZATION` | 组织 ID（`bigmodel-organization`） | — |
| `GLM_PROJECT` | 项目 ID（`bigmodel-project`） | — |
| `REFRESH_INTERVAL` | 刷新间隔（秒） | `60` |
| `WARN_1` / `WARN_2` / `WARN_3` | 告警阈值（%） | `80` / `90` / `95` |
| `DB_PATH` | SQLite 路径（留空 = `%APPDATA%\glm-monitor\usage.db`） | `%APPDATA%\...` |
| `DASHBOARD` | 终端仪表盘（1/0） | `0` |
| `TRAY` | 系统托盘（1/0） | `1` |
| `FLOAT_BALL` | 悬浮球（1/0） | `1` |

> 抓包入口：登录 bigmodel.cn → 打开「用量」页 → F12 抓 `https://bigmodel.cn/api/monitor/usage/quota/limit` 请求，复制三个请求头的值。

## 打包与后台运行

打包成无控制台单文件 exe，仅保留悬浮球 + 托盘后台运行：

```powershell
.\build.ps1
```

产出 `dist\glm-monitor.exe`。使用方式：

1. 把 `.env` 复制到 exe 旁（程序会读取 exe 同目录的 `.env`）
2. 双击运行（无控制台窗口，悬浮球 + 托盘即出现）
3. 通过托盘菜单「开机自启」可设置开机自动运行

> 打包已排除 `rich` / `plotext`（仅终端仪表盘用），减小体积。

## 操作

| 操作 | 终端 | 悬浮球 | 托盘 |
|------|------|--------|------|
| 切换趋势窗口 | `1`=6h `2`=24h `3`=7d | — | — |
| 用量明细 | — | 鼠标悬停 | hover 标题 |
| 显隐悬浮球 | — | — | 双击图标 / 右键菜单 |
| 立即刷新 | — | — | 右键 → 立即刷新 |
| 打开数据目录 | — | — | 右键 → 打开数据目录 |
| 开机自启 | — | — | 右键 → 开机自启 |
| 退出 | `q` | 右键 → 退出 | 右键 → 退出 |

悬浮球：左键拖动移动位置。托盘图标颜色：< 80% 绿 / 80–90% 黄 / 90–95% 橙 / ≥95% 红。

## 数据目录

历史数据库、日志统一存于：

```
%APPDATA%\glm-monitor\
├── usage.db        # SQLite 历史用量
└── monitor.log     # 运行日志（500KB 轮转，保留 3 份）
```

删除这些文件可安全重建（仅丢失历史趋势）。「打开数据目录」可从托盘菜单直达。

## 项目结构

| 文件 | 作用 |
|------|------|
| `monitor.py` | 主入口，编排多线程 |
| `quota_client.py` | 接口请求与解析 |
| `dashboard.py` | rich 终端仪表盘 + plotext 趋势（可选） |
| `tray.py` | pystray 系统托盘 |
| `float_ball.py` | PySide6 悬浮球（环形进度 + Tooltip） |
| `alerter.py` | 阈值告警 + 桌面通知 |
| `storage.py` | SQLite 历史存储 |
| `config.py` | 从 `.env` 加载配置 |
| `paths.py` | `%APPDATA%` 数据目录管理 |
| `logger.py` | 轮转文件日志 |
| `autostart.py` | 开机自启（注册表读写） |
| `generate_icon.py` | 生成应用图标 `assets/glm.ico` |
| `build.ps1` | PyInstaller 打包脚本 |

## 技术栈

`PySide6` · `pystray` · `Pillow` · `plyer` · `requests` · `python-dotenv`
（终端仪表盘可选：`rich` · `plotext`）

## 注意事项

- `TOKENS_LIMIT` 接口仅返回百分比（无绝对 token 数），故 Token 配额只显示百分比与重置时间。
- 仅支持 Windows（键盘交互依赖 `msvcrt`，托盘与悬浮球为 Windows 桌面特性）。
- `.env` 含真实凭证，已被 `.gitignore` 排除，勿分享或提交。
- 凭证为 JWT 但 payload 无 `exp`，过期由服务端会话决定；连续 2 次拉取失败会触发「凭证可能已过期」桌面通知，并在日志记录。
