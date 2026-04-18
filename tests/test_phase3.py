"""Phase 3 单元测试 — 验证 SQLite 事件存储与 ROI 过滤。"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pytest

from src.analyzer.take_away import TakeAwayAnalyzer
from src.common.models import Detection, Event, FrameData, Roi
from src.storage.sqlite_store import SqliteEventStore


def _make_frame(frame_id: int, detections: list[Detection]) -> FrameData:
    fake_img = np.zeros((720, 1280, 3), dtype=np.uint8)
    return FrameData(
        frame=fake_img,
        timestamp=datetime.now(),
        frame_id=frame_id,
        detections=detections,
    )


def _person(bbox: tuple[int, int, int, int], tid: int = 100) -> Detection:
    return Detection(label="person", confidence=0.9, bbox=bbox, track_id=tid)


def _cup(bbox: tuple[int, int, int, int], tid: int) -> Detection:
    return Detection(label="cup", confidence=0.9, bbox=bbox, track_id=tid)


# ---------- SQLite 存储 ----------

def test_sqlite_save_and_query_roundtrip(tmp_path):
    store = SqliteEventStore(
        db_path=tmp_path / "events.db",
        snapshot_dir=tmp_path / "snap",
    )
    try:
        ev = Event(
            event_type="take_away",
            description="cup #3 被拿走",
            timestamp=datetime(2026, 4, 17, 10, 30, 0),
            snapshot=b"\xff\xd8\xff\xd9",  # 最小 JPEG 头尾
            metadata={"track_id": 3, "label": "cup"},
        )
        row_id = store.save(ev)
        assert row_id > 0

        rows = store.query()
        assert len(rows) == 1
        r = rows[0]
        assert r["event_type"] == "take_away"
        assert r["description"] == "cup #3 被拿走"
        assert r["metadata"]["track_id"] == 3
        assert r["snapshot_path"] and r["snapshot_path"].endswith(".jpg")
    finally:
        store.close()


def test_sqlite_query_filters(tmp_path):
    store = SqliteEventStore(
        db_path=tmp_path / "events.db",
        snapshot_dir=tmp_path / "snap",
    )
    try:
        base = datetime(2026, 4, 17, 12, 0, 0)
        store.save(Event("take_away", "A", base))
        store.save(Event("loiter", "B", base + timedelta(minutes=5)))
        store.save(Event("take_away", "C", base + timedelta(minutes=10)))

        all_rows = store.query()
        assert len(all_rows) == 3

        taken = store.query(event_type="take_away")
        assert len(taken) == 2
        assert {r["description"] for r in taken} == {"A", "C"}

        windowed = store.query(start=base + timedelta(minutes=1))
        assert len(windowed) == 2
    finally:
        store.close()


def test_sqlite_save_without_snapshot(tmp_path):
    store = SqliteEventStore(
        db_path=tmp_path / "events.db",
        snapshot_dir=tmp_path / "snap",
    )
    try:
        store.save(Event("take_away", "无快照", datetime.now()))
        rows = store.query()
        assert rows[0]["snapshot_path"] is None
    finally:
        store.close()


# ---------- Roi ----------

def test_roi_contains_point():
    # 矩形 ROI 占据画面左半，归一化坐标
    roi = Roi(polygon_norm=[(0.0, 0.0), (0.5, 0.0), (0.5, 1.0), (0.0, 1.0)])
    # 画面尺寸 1280x720
    assert roi.contains_point(100, 100, 1280, 720) is True
    assert roi.contains_point(1000, 100, 1280, 720) is False


def test_empty_roi_contains_all():
    roi = Roi(polygon_norm=[])
    assert roi.is_empty()
    assert roi.contains_point(0, 0, 100, 100) is True


# ---------- 分析器 + ROI ----------

def test_analyzer_ignores_object_outside_roi():
    """ROI 外的物体消失不应触发告警。"""
    # ROI 只覆盖画面左半 (x < 640)
    roi = Roi(polygon_norm=[(0.0, 0.0), (0.5, 0.0), (0.5, 1.0), (0.0, 1.0)])
    analyzer = TakeAwayAnalyzer(
        disappear_frames=3,
        recent_frames_window=10,
        proximity_distance=400,
        alert_cooldown=0,
        roi=roi,
    )

    # 杯子在 ROI 外（右半）
    cup_bbox = (900, 400, 1000, 500)
    person_near = (950, 400, 1100, 700)

    for fid in range(1, 5):
        events = analyzer.analyze(_make_frame(fid, [_cup(cup_bbox, 1), _person(person_near)]))
        assert events == []

    for fid in range(5, 12):
        events = analyzer.analyze(_make_frame(fid, []))
        assert events == []


def test_analyzer_triggers_for_object_inside_roi():
    """ROI 内的物体被拿走应触发告警。"""
    roi = Roi(polygon_norm=[(0.0, 0.0), (0.5, 0.0), (0.5, 1.0), (0.0, 1.0)])
    analyzer = TakeAwayAnalyzer(
        disappear_frames=3,
        recent_frames_window=10,
        proximity_distance=400,
        alert_cooldown=0,
        roi=roi,
    )

    # 杯子在 ROI 内（左半 x<640）
    cup_bbox = (200, 400, 300, 500)
    person_near = (250, 400, 400, 700)

    for fid in range(1, 5):
        analyzer.analyze(_make_frame(fid, [_cup(cup_bbox, 1), _person(person_near)]))

    triggered = False
    for fid in range(5, 12):
        events = analyzer.analyze(_make_frame(fid, []))
        if events:
            triggered = True
            assert events[0].metadata["track_id"] == 1
            assert events[0].metadata["label"] == "cup"
    assert triggered, "ROI 内的物体消失应该触发告警"
