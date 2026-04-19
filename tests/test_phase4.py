"""Phase 4 单元测试 — 验证 FastAPI 接口与 FrameBus。"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src.common.models import Event
from src.server.app import create_app
from src.server.frame_bus import FrameBus
from src.storage.sqlite_store import SqliteEventStore


@pytest.fixture
def store(tmp_path):
    s = SqliteEventStore(
        db_path=tmp_path / "events.db",
        snapshot_dir=tmp_path / "snap",
    )
    base = datetime(2026, 4, 18, 9, 0, 0)
    s.save(Event("take_away", "cup #1", base, metadata={"track_id": 1}))
    s.save(Event("take_away", "cup #2", base + timedelta(minutes=5), metadata={"track_id": 2}))
    s.save(Event("loiter", "person #9", base + timedelta(minutes=10)))
    yield s
    s.close()


def test_index_returns_html(tmp_path, store):
    app = create_app(event_store=store, snapshot_dir=tmp_path / "snap")
    client = TestClient(app)
    res = client.get("/")
    assert res.status_code == 200
    assert "智能摄像头" in res.text


def test_list_events_default(tmp_path, store):
    app = create_app(event_store=store, snapshot_dir=tmp_path / "snap")
    client = TestClient(app)
    res = client.get("/api/events")
    assert res.status_code == 200
    data = res.json()
    assert len(data["events"]) == 3
    # 默认按 id 倒序
    assert data["events"][0]["description"] == "person #9"


def test_list_events_filter_by_type(tmp_path, store):
    app = create_app(event_store=store, snapshot_dir=tmp_path / "snap")
    client = TestClient(app)
    res = client.get("/api/events?event_type=take_away")
    assert res.status_code == 200
    events = res.json()["events"]
    assert len(events) == 2
    assert all(e["event_type"] == "take_away" for e in events)


def test_list_events_invalid_time(tmp_path, store):
    app = create_app(event_store=store, snapshot_dir=tmp_path / "snap")
    client = TestClient(app)
    res = client.get("/api/events?start=not-a-date")
    assert res.status_code == 400


def test_list_events_no_store_returns_empty(tmp_path):
    app = create_app(event_store=None, snapshot_dir=tmp_path / "snap")
    client = TestClient(app)
    res = client.get("/api/events")
    assert res.status_code == 200
    assert res.json() == {"events": []}


# ---------- FrameBus ----------

def test_frame_bus_latest_overwrites():
    bus = FrameBus()
    assert bus.get_latest_frame() == (0, None)
    bus.publish_frame(b"a")
    bus.publish_frame(b"b")
    seq, jpeg = bus.get_latest_frame()
    assert seq == 2
    assert jpeg == b"b"


def test_frame_bus_event_subscription():
    """事件应通过 loop.call_soon_threadsafe 跨线程入队。"""
    async def runner():
        bus = FrameBus()
        bus.attach_loop(asyncio.get_running_loop())
        q = bus.subscribe_events()

        # 模拟从其他线程发布
        import threading
        def publisher():
            bus.publish_event({"event_type": "take_away", "id": 1})
        threading.Thread(target=publisher).start()

        ev = await asyncio.wait_for(q.get(), timeout=1.0)
        assert ev["id"] == 1
        bus.unsubscribe_events(q)

    asyncio.run(runner())


def test_frame_bus_publish_without_loop_is_silent():
    bus = FrameBus()
    # 未 attach_loop，也无订阅者：不应抛
    bus.publish_event({"x": 1})


def test_ws_stream_sends_latest_jpeg(tmp_path, store):
    bus = FrameBus()
    app = create_app(event_store=store, frame_bus=bus, snapshot_dir=tmp_path / "snap")
    client = TestClient(app)
    bus.publish_frame(b"\xff\xd8jpeg-bytes\xff\xd9")
    with client.websocket_connect("/ws/stream") as ws:
        data = ws.receive_bytes()
        assert data == b"\xff\xd8jpeg-bytes\xff\xd9"
