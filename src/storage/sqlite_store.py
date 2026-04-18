"""SQLite 事件存储实现。

策略：
- 事件元信息写入 SQLite 表 events
- 快照 JPEG 字节写入文件，DB 仅存相对路径（避免 BLOB 膨胀 + 便于前端直接 URL 访问）
- metadata 字段序列化为 JSON 文本
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from src.common.logger import setup_logger
from src.common.models import Event
from src.storage.base import BaseEventStore

logger = setup_logger(__name__)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    description TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    snapshot_path TEXT,
    metadata TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
"""


class SqliteEventStore(BaseEventStore):
    def __init__(self, db_path: str | Path, snapshot_dir: str | Path):
        self._db_path = Path(db_path)
        self._snapshot_dir = Path(snapshot_dir)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._snapshot_dir.mkdir(parents=True, exist_ok=True)

        # SQLite 连接非线程安全；用 check_same_thread=False + 锁保护跨线程写入
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        logger.info("SQLite 事件存储就绪: %s", self._db_path)

    def save(self, event: Event) -> int:
        snapshot_path = self._write_snapshot(event)
        metadata_json = json.dumps(event.metadata or {}, ensure_ascii=False)
        with self._lock:
            cursor = self._conn.execute(
                "INSERT INTO events (event_type, description, timestamp, snapshot_path, metadata) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    event.event_type,
                    event.description,
                    event.timestamp.isoformat(),
                    snapshot_path,
                    metadata_json,
                ),
            )
            self._conn.commit()
            return cursor.lastrowid

    def query(
        self,
        event_type: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM events WHERE 1=1"
        params: list[Any] = []
        if event_type is not None:
            sql += " AND event_type = ?"
            params.append(event_type)
        if start is not None:
            sql += " AND timestamp >= ?"
            params.append(start.isoformat())
        if end is not None:
            sql += " AND timestamp <= ?"
            params.append(end.isoformat())
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()

        return [self._row_to_dict(r) for r in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _write_snapshot(self, event: Event) -> str | None:
        if not event.snapshot:
            return None
        fname = f"{event.timestamp.strftime('%Y%m%d_%H%M%S_%f')}_{event.event_type}.jpg"
        path = self._snapshot_dir / fname
        path.write_bytes(event.snapshot)
        try:
            return str(path.relative_to(Path.cwd()))
        except ValueError:
            return str(path)

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        meta_raw = data.get("metadata")
        if meta_raw:
            try:
                data["metadata"] = json.loads(meta_raw)
            except json.JSONDecodeError:
                data["metadata"] = {}
        else:
            data["metadata"] = {}
        return data


def create_event_store(config: dict) -> SqliteEventStore | None:
    """按配置创建事件存储；storage.enabled=false 时返回 None。"""
    storage_cfg = config.get("storage") or {}
    if not storage_cfg.get("enabled", True):
        return None
    db_path = storage_cfg.get("database_path") or config.get("database", {}).get(
        "path", "data/events/events.db"
    )
    snapshot_dir = storage_cfg.get("snapshot_dir", "data/snapshots")
    return SqliteEventStore(db_path=db_path, snapshot_dir=snapshot_dir)
