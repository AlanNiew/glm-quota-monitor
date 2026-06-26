# GLM 用量监控

监控智谱 GLM（bigmodel.cn）套餐的 Token 与调用次数用量，在终端实时展示，并提供系统托盘状态与阈值告警。

## 功能

- 终端实时仪表盘：双配额进度条、调用次数绝对值、按模型拆分、预计耗尽时间、双折线趋势
- 系统托盘：图标按用量变色（绿 / 黄 / 橙 / 红），右键立即刷新 / 退出
- 历史记录：SQLite 存储，支持 6h / 24h / 7d 趋势窗口切换
- 阈值告警：达到 80% / 90% / 95% 时发送 Windows 桌面通知（每档只提醒一次，回落重置）
- 每 60s 自动刷新（启动即拉一次）

## 快速开始

```powershell
cd glm-quota-monitor

# 创建项目内虚拟环境并安装依赖
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt

# 配置凭证（首次）
Copy-Item .env.example .env
# 编辑 .env，填入你的 GLM 凭证

# 运行
.\venv\Scripts\python monitor.py
```

## 配置（.env）

| 变量 | 说明 | 来源 |
|------|------|------|
| `GLM_AUTHORIZATION` | 接口认证 token | 请求头 `authorization` |
| `GLM_ORGANIZATION` | 组织 ID | 请求头 `bigmodel-organization` |
| `GLM_PROJECT` | 项目 ID | 请求头 `bigmodel-project` |
| `REFRESH_INTERVAL` | 刷新间隔（秒），默认 60 | — |
| `WARN_1` / `WARN_2` / `WARN_3` | 告警阈值（%），默认 80 / 90 / 95 | — |
| `DB_PATH` | SQLite 路径，默认 `usage.db` | — |

> 抓包入口：登录 bigmodel.cn → 打开「用量」页 → F12 抓 `https://bigmodel.cn/api/monitor/usage/quota/limit` 请求，复制三个请求头的值。

## 操作

| 操作 | 终端 | 托盘 |
|------|------|------|
| 切换趋势窗口 | `1`=6h `2`=24h `3`=7d | — |
| 立即刷新 | — | 右键 → 立即刷新 |
| 退出 | `q` | 右键 → 退出 |

托盘图标颜色：< 80% 绿 / 80–90% 黄 / 90–95% 橙 / ≥95% 红。

## 项目结构

| 文件 | 作用 |
|------|------|
| `monitor.py` | 主入口，编排多线程 |
| `quota_client.py` | 接口请求与解析 |
| `dashboard.py` | rich 终端仪表盘 + plotext 趋势 |
| `tray.py` | pystray 系统托盘 |
| `alerter.py` | 阈值告警 + 桌面通知 |
| `storage.py` | SQLite 历史存储 |
| `config.py` | 从 `.env` 加载配置 |

## 技术栈

`rich` · `plotext` · `pystray` · `Pillow` · `plyer` · `requests` · `python-dotenv`

## 注意事项

- `TOKENS_LIMIT` 接口仅返回百分比（无绝对 token 数），故 Token 配额只显示百分比与重置时间。
- 仅支持 Windows（键盘交互依赖 `msvcrt`）。
- `.env` 含真实凭证，已被 `.gitignore` 排除，勿分享或提交。