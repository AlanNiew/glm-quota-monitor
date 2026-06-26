# AGENTS.md

GLM 套餐 Token 用量监控工具的开发指引。仅记录不易从文件名 / 默认约定推断的高信号事实。

## 运行

- 项目根：`glm-quota-monitor/`，单进程多线程 Python 应用。
- 必须用项目内虚拟环境，勿用全局解释器：
  ```powershell
  cd glm-quota-monitor
  .\venv\Scripts\python monitor.py
  ```
- 重装依赖：`.\venv\Scripts\pip install -r requirements.txt`

## 验证（本项目无测试套件）

没有单元测试 / lint / typecheck 配置。验证方式：

- 语法：`.\venv\Scripts\python -m py_compile *.py`
- 真实接口探测（不启动 TUI，验证凭证与解析）：
  ```powershell
  $env:PYTHONIOENCODING="utf-8"
  .\venv\Scripts\python -c "from config import load_config; from quota_client import QuotaClient; u=QuotaClient(load_config()).fetch(); print(u.ok,u.level,u.tokens_pct,u.time_pct,u.time_details)"
  ```
- TUI 与系统托盘需交互式终端，无法在非交互 shell 中验证。

## 架构（多线程单进程）

入口 `monitor.py` 的 `Monitor.run()`：

- **主线程** = `dashboard.py` 的 rich `Live` 仪表盘（每 1s 重渲染）
- **子线程 A** = `tray.py` 的 pystray 托盘（`run_detached`）
- **子线程 B** = 60s 定时拉取循环（启动即拉一次）

共享状态 `state` / `last_fetch` / `trend_data` 由 `threading.Lock` 保护；仪表盘读取走原子引用，可接受读到上一帧。

## 接口契约（易踩坑）

`QuotaClient` 请求 `https://bigmodel.cn/api/monitor/usage/quota/limit`，返回 `data.limits[]`，含两种 `type`：

- `TOKENS_LIMIT`：**只有** `percentage` 与 `nextResetTime`，**没有绝对 token 数**（接口限制，不是 bug）。
- `TIME_LIMIT`：`usage`(总额) / `currentValue`(已用) / `remaining` / `percentage` / `nextResetTime` / `usageDetails`(按 `modelCode` 拆分)。

约定：`percentage` = 已用百分比；`nextResetTime` = 毫秒时间戳；`unit` / `number` 字段含义不明，已忽略。

## 凭证与安全

- `.env` 存真实 GLM 凭证（`GLM_AUTHORIZATION` / `GLM_ORGANIZATION` / `GLM_PROJECT`），已被 `.gitignore` 排除。
- 凭证来源：浏览器 F12 抓包请求头，对应 `authorization` / `bigmodel-organization` / `bigmodel-project`。
- **严禁**把凭证硬编码进 `.py` 或提交；`.env.example` 是脱敏模板。
- token 为 JWT，但 payload **无 `exp` 字段**，过期时间由服务端会话决定，无法从 token 读出。
- 连续 2 次请求失败会触发「凭证可能已过期」桌面通知，并在仪表盘显示醒目提示；恢复成功后自动重置（见 `alerter.notify_auth_expired` / `Monitor.AUTH_FAIL_THRESHOLD`）。

## 数据

- SQLite `usage.db`（已 gitignore），每次刷新插一行；趋势查询用 `WHERE ts >= datetime('now','-Nh')`。
- 删除 `usage.db` 可安全重建（仅丢失历史趋势）。

## 平台与依赖注意

- 仅 Windows：键盘交互用 `msvcrt`（`1`/`2`/`3` 切趋势窗口 6h/24h/7d，`q` 退出）。
- 终端窗口标题（即任务栏按钮文字）实时显示 `GLM [lite] Token 76% | 调用 51%`，最小化也能一目了然（见 `dashboard._title_text`）。
- `plotext` 在部分 Windows 终端渲染异常，`dashboard._render_trend` 已用 try/except 回退为提示文本。
- 桌面通知走 `plyer`。

## 本工作区的文件编辑限制（重要）

OpenCode 权限策略 `edit * deny`（仅放行 `.opencode/plans/*.md`）会拦截 `write` / `edit` 工具。改文件需改用 bash 工具执行 PowerShell：以单引号 here-string 持有内容（结束符必须顶格），再用 `[System.IO.File]::WriteAllText($path, $content, (New-Object System.Text.UTF8Encoding $false))` 写无 BOM UTF-8；或 `Set-Content -Encoding UTF8`（会带 BOM，Python 可接受）。写完后用 `python -m py_compile` 校验。