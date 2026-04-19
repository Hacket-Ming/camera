"""跨线程帧/事件总线 — 桥接同步 Pipeline 与异步 FastAPI。

设计：
- Pipeline 线程调用 publish_frame/publish_event（无锁等待，O(订阅者数)）
- 帧采用"最新覆盖"策略：只保留一帧，用 seq 号让消费者识别新帧
- 事件采用每订阅者独立 asyncio.Queue 的扇出，跨线程通过 loop.call_soon_threadsafe 入队
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any


class FrameBus:
    def __init__(self, event_queue_max: int = 100):
        self._lock = threading.Lock()
        self._latest_jpeg: bytes | None = None
        self._frame_seq: int = 0
        self._event_queue_max = event_queue_max
        self._event_subscribers: list[asyncio.Queue] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """FastAPI 启动时调用，绑定事件循环用于跨线程入队。"""
        self._loop = loop

    # --- 帧 ---

    def publish_frame(self, jpeg: bytes) -> None:
        with self._lock:
            self._latest_jpeg = jpeg
            self._frame_seq += 1

    def get_latest_frame(self) -> tuple[int, bytes | None]:
        with self._lock:
            return self._frame_seq, self._latest_jpeg

    # --- 事件 ---

    def publish_event(self, event: dict[str, Any]) -> None:
        """从任意线程发布事件。无订阅者时丢弃。"""
        if self._loop is None or not self._event_subscribers:
            return
        for q in list(self._event_subscribers):
            self._loop.call_soon_threadsafe(self._safe_put, q, event)

    def subscribe_events(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=self._event_queue_max)
        self._event_subscribers.append(q)
        return q

    def unsubscribe_events(self, q: asyncio.Queue) -> None:
        try:
            self._event_subscribers.remove(q)
        except ValueError:
            pass

    @staticmethod
    def _safe_put(q: asyncio.Queue, item: Any) -> None:
        try:
            q.put_nowait(item)
        except asyncio.QueueFull:
            pass
