"""SQLite 历史存储与趋势查询。"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import List


CREATE_SQL = """
CREATE TABLE IF NOT EXISTS usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,                  -- 本地时间（ISO）
    level TEXT,                        -- 套餐等级
    tokens_pct REAL,                   -- Token 综合（取 weekly/5h 较大者，兼容旧趋势）
    tokens_next_reset INTEGER,         -- 对应重置时间（ms）
    tokens_weekly_pct REAL,            -- 每周 Token 限额已用% (unit=6, number=1)
    tokens_weekly_reset INTEGER,       -- 每周重置时间（ms）
    tokens_5h_pct REAL,                -- 5 小时滚动窗口已用% (unit=3, number=5)
    tokens_5h_reset INTEGER,           -- 5 小时窗口重置时间（ms）
    time_total INTEGER,                -- TIME_LIMIT 总额
    time_current INTEGER,              -- TIME_LIMIT 已用
    time_remaining INTEGER,            -- TIME_LIMIT 剩余
    time_pct REAL,                     -- TIME_LIMIT 已用%
    time_next_reset INTEGER,           -- TIME_LIMIT 重置时间（ms）
    time_details TEXT                  -- 按模型拆分（JSON）
);
"""

# 老库迁移：CREATE TABLE IF NOT EXISTS 不会为已存在的表补列，
# 需显式 ALTER TABLE。每条迁移幂等（先检查列是否存在）。
MIGRATIONS = [
    ("tokens_weekly_pct", "ALTER TABLE usage_log ADD COLUMN tokens_weekly_pct REAL"),
    ("tokens_weekly_reset", "ALTER TABLE usage_log ADD COLUMN tokens_weekly_reset INTEGER"),
    ("tokens_5h_pct", "ALTER TABLE usage_log ADD COLUMN tokens_5h_pct REAL"),
    ("tokens_5h_reset", "ALTER TABLE usage_log ADD COLUMN tokens_5h_reset INTEGER"),
]


class Storage:
    """历史数据存储。"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init(self):
        """初始化数据表，并为老库补齐新增列。"""
        with self._conn() as conn:
            conn.execute(CREATE_SQL)
            existing = {row[1] for row in conn.execute("PRAGMA table_info(usage_log)").fetchall()}
            for col, sql in MIGRATIONS:
                if col not in existing:
                    conn.execute(sql)

    def insert(self, usage) -> None:
        """写入一条用量记录。"""
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO usage_log
                   (ts, level, tokens_pct, tokens_next_reset,
                    tokens_weekly_pct, tokens_weekly_reset,
                    tokens_5h_pct, tokens_5h_reset,
                    time_total, time_current, time_remaining, time_pct,
                    time_next_reset, time_details)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    datetime.now().isoformat(timespec="seconds"),
                    usage.level,
                    usage.tokens_pct,
                    usage.tokens_next_reset,
                    usage.tokens_weekly_pct,
                    usage.tokens_weekly_reset,
                    usage.tokens_5h_pct,
                    usage.tokens_5h_reset,
                    usage.time_total,
                    usage.time_current,
                    usage.time_remaining,
                    usage.time_pct,
                    usage.time_next_reset,
                    json.dumps(usage.time_details, ensure_ascii=False),
                ),
            )

    def query_trend(self, hours: int) -> List[dict]:
        """查询最近 hours 小时的趋势记录（按时间升序）。

        阈值在 Python 端用本地时间 + ISO 格式计算，与 insert 写入格式完全一致，
        避免 SQLite datetime('now')（UTC、空格分隔）与 ts（本地、T 分隔）在时区与
        字典序上双重不一致导致窗口偏移。
        """
        threshold = (datetime.now() - timedelta(hours=hours)).isoformat(timespec="seconds")
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT ts, tokens_pct, time_current, time_pct
                   FROM usage_log
                   WHERE ts >= ?
                   ORDER BY ts ASC""",
                (threshold,),
            ).fetchall()
        return [dict(r) for r in rows]
