"""Phase 2 单元测试 — 验证追踪驱动的行为分析。"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pytest

from src.analyzer.take_away import TakeAwayAnalyzer
from src.common.models import Detection, FrameData


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


def test_take_away_triggered_when_person_nearby_then_object_disappears():
    """人靠近物体后物体消失 → 触发告警。"""
    analyzer = TakeAwayAnalyzer(
        disappear_frames=5,
        recent_frames_window=10,
        proximity_distance=300,
        alert_cooldown=0,
    )

    cup_bbox = (500, 400, 600, 500)
    person_near = (550, 400, 700, 700)

    # 人靠近物体 5 帧
    for fid in range(1, 6):
        events = analyzer.analyze(_make_frame(fid, [_cup(cup_bbox, 1), _person(person_near)]))
        assert events == []

    # 物体连续消失，前 4 帧不触发
    for fid in range(6, 10):
        events = analyzer.analyze(_make_frame(fid, []))
        assert events == []

    # 第 10 帧（消失满 5 帧）触发告警
    events = analyzer.analyze(_make_frame(10, []))
    assert len(events) == 1
    assert events[0].event_type == "take_away"
    assert "cup" in events[0].description
    assert "#1" in events[0].description


def test_no_alert_when_object_disappears_without_person():
    """物体消失但附近从未有人 → 不告警。"""
    analyzer = TakeAwayAnalyzer(
        disappear_frames=5,
        recent_frames_window=10,
        proximity_distance=300,
        alert_cooldown=0,
    )

    cup_bbox = (500, 400, 600, 500)
    for fid in range(1, 6):
        analyzer.analyze(_make_frame(fid, [_cup(cup_bbox, 1)]))

    for fid in range(6, 13):
        events = analyzer.analyze(_make_frame(fid, []))
        assert events == []


def test_no_alert_when_person_far_from_object():
    """人在画面但远离物体 → 物体消失也不告警。"""
    analyzer = TakeAwayAnalyzer(
        disappear_frames=5,
        recent_frames_window=10,
        proximity_distance=100,  # 严格的距离阈值
        alert_cooldown=0,
    )

    cup_bbox = (100, 100, 200, 200)
    person_far = (1000, 600, 1100, 700)

    for fid in range(1, 6):
        analyzer.analyze(_make_frame(fid, [_cup(cup_bbox, 1), _person(person_far)]))

    for fid in range(6, 13):
        events = analyzer.analyze(_make_frame(fid, []))
        assert events == []


def test_brief_occlusion_does_not_trigger():
    """物体被短暂遮挡（少于 disappear_frames）→ 不告警。"""
    analyzer = TakeAwayAnalyzer(
        disappear_frames=10,
        recent_frames_window=20,
        proximity_distance=300,
        alert_cooldown=0,
    )

    cup_bbox = (500, 400, 600, 500)
    person_near = (550, 400, 700, 700)

    for fid in range(1, 6):
        analyzer.analyze(_make_frame(fid, [_cup(cup_bbox, 1), _person(person_near)]))

    # 短暂消失 3 帧（不到阈值）
    for fid in range(6, 9):
        events = analyzer.analyze(_make_frame(fid, [_person(person_near)]))
        assert events == []

    # 物体重新出现
    for fid in range(9, 15):
        events = analyzer.analyze(_make_frame(fid, [_cup(cup_bbox, 1), _person(person_near)]))
        assert events == []


def test_alert_cooldown_prevents_burst():
    """告警冷却期内不重复告警。"""
    analyzer = TakeAwayAnalyzer(
        disappear_frames=3,
        recent_frames_window=10,
        proximity_distance=300,
        alert_cooldown=999,  # 大冷却期
    )

    person_near = (550, 400, 700, 700)

    # 第一个物体被拿走
    for fid in range(1, 4):
        analyzer.analyze(_make_frame(fid, [_cup((500, 400, 600, 500), 1), _person(person_near)]))
    for fid in range(4, 8):
        events = analyzer.analyze(_make_frame(fid, [_person(person_near)]))
        if events:
            break

    # 紧接着第二个物体被拿走
    for fid in range(8, 11):
        analyzer.analyze(_make_frame(fid, [_cup((500, 400, 600, 500), 2), _person(person_near)]))
    triggered_again = False
    for fid in range(11, 15):
        events = analyzer.analyze(_make_frame(fid, [_person(person_near)]))
        if events:
            triggered_again = True
    assert not triggered_again, "冷却期内不应重复告警"


def test_detections_without_track_id_are_ignored():
    """未启用追踪时（track_id=None）物体被分析器忽略，不影响主流程。"""
    analyzer = TakeAwayAnalyzer(disappear_frames=3, alert_cooldown=0)
    det = Detection(label="cup", confidence=0.9, bbox=(0, 0, 10, 10), track_id=None)
    events = analyzer.analyze(_make_frame(1, [det]))
    assert events == []
