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
    tokens_pct REAL,                   -- TOKENS_LIMIT 已用%
    tokens_next_reset INTEGER,         -- TOKENS_LIMIT 重置时间（ms）
    time_total INTEGER,                -- TIME_LIMIT 总额
    time_current INTEGER,              -- TIME_LIMIT 已用
    time_remaining INTEGER,            -- TIME_LIMIT 剩余
    time_pct REAL,                     -- TIME_LIMIT 已用%
    time_next_reset INTEGER,           -- TIME_LIMIT 重置时间（ms）
    time_details TEXT                  -- 按模型拆分（JSON）
);
"""


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
        """初始化数据表。"""
        with self._conn() as conn:
            conn.execute(CREATE_SQL)

    def insert(self, usage) -> None:
        """写入一条用量记录。"""
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO usage_log
                   (ts, level, tokens_pct, tokens_next_reset,
                    time_total, time_current, time_remaining, time_pct,
                    time_next_reset, time_details)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    datetime.now().isoformat(timespec="seconds"),
                    usage.level,
                    usage.tokens_pct,
                    usage.tokens_next_reset,
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
