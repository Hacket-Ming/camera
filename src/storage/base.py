"""事件存储抽象接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from src.common.models import Event


class BaseEventStore(ABC):
    """事件持久化的统一接口。可替换为不同后端（SQLite/Postgres/远程）。"""

    @abstractmethod
    def save(self, event: Event) -> int:
        """保存事件，返回主键 ID。"""

    @abstractmethod
    def query(
        self,
        event_type: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """按条件查询事件，返回字典列表。"""

    @abstractmethod
    def close(self) -> None:
        """释放资源。"""
