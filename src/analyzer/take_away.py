"""'拿东西走'行为识别 — 基于追踪的实现。

策略：
1. 用 track_id 追踪每个物体的出现帧和位置历史
2. 物体连续 N 帧未出现 → 视为"消失"
3. 检查消失前最近 M 帧内附近是否有人 → 判定"被拿走"
4. 冷却机制避免重复告警
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime

import cv2
import numpy as np

from src.analyzer.base import BaseAnalyzer
from src.common.logger import setup_logger
from src.common.models import Detection, Event, FrameData, Roi

logger = setup_logger(__name__)

_PERSON_LABEL = "person"


@dataclass
class TrackState:
    """单个被追踪物体的状态。"""
    track_id: int
    label: str
    last_seen_frame: int
    last_bbox: tuple[int, int, int, int]
    # 最近 N 帧中是否有人靠近的历史（True/False 队列）
    person_nearby_history: deque = field(default_factory=lambda: deque(maxlen=30))


class TakeAwayAnalyzer(BaseAnalyzer):
    def __init__(
        self,
        disappear_frames: int = 15,
        recent_frames_window: int = 30,
        proximity_distance: float = 200.0,
        alert_cooldown: float = 10.0,
        roi: Roi | None = None,
    ):
        self._disappear_frames = disappear_frames
        self._recent_frames_window = recent_frames_window
        self._proximity_distance = proximity_distance
        self._alert_cooldown = alert_cooldown
        self._roi = roi

        self._tracks: dict[int, TrackState] = {}
        self._last_alert_time: float = 0.0

    def analyze(self, frame_data: FrameData) -> list[Event]:
        detections = frame_data.detections
        frame_id = frame_data.frame_id
        h, w = frame_data.frame.shape[:2]

        persons = [d for d in detections if d.label == _PERSON_LABEL]
        objects = [
            d for d in detections
            if d.label != _PERSON_LABEL
            and d.track_id is not None
            and self._in_roi(d.bbox, w, h)
        ]

        # 更新本帧出现的物体状态
        seen_track_ids = set()
        for obj in objects:
            seen_track_ids.add(obj.track_id)
            state = self._tracks.get(obj.track_id)
            if state is None:
                state = TrackState(
                    track_id=obj.track_id,
                    label=obj.label,
                    last_seen_frame=frame_id,
                    last_bbox=obj.bbox,
                    person_nearby_history=deque(maxlen=self._recent_frames_window),
                )
                self._tracks[obj.track_id] = state
            state.last_seen_frame = frame_id
            state.last_bbox = obj.bbox
            state.person_nearby_history.append(self._has_person_nearby(obj.bbox, persons))

        # 检测消失的物体
        events = []
        disappeared_ids = []
        for tid, state in self._tracks.items():
            if tid in seen_track_ids:
                continue
            missing = frame_id - state.last_seen_frame
            if missing >= self._disappear_frames:
                # 消失前最近窗口内是否有人靠近
                if any(state.person_nearby_history):
                    event = self._make_event(state, frame_data)
                    if event is not None:
                        events.append(event)
                disappeared_ids.append(tid)

        # 清理已消失的 track
        for tid in disappeared_ids:
            del self._tracks[tid]

        return events

    def _make_event(self, state: TrackState, frame_data: FrameData) -> Event | None:
        now = time.time()
        if now - self._last_alert_time < self._alert_cooldown:
            return None
        self._last_alert_time = now

        snapshot = self._encode_snapshot(frame_data.frame)
        description = f"{state.label} #{state.track_id} 被拿走"
        logger.warning("触发告警: %s", description)
        return Event(
            event_type="take_away",
            description=description,
            timestamp=frame_data.timestamp,
            snapshot=snapshot,
            metadata={
                "track_id": state.track_id,
                "label": state.label,
                "last_bbox": list(state.last_bbox),
                "last_seen_frame": state.last_seen_frame,
                "current_frame": frame_data.frame_id,
            },
        )

    def _in_roi(self, bbox: tuple[int, int, int, int], width: int, height: int) -> bool:
        if self._roi is None or self._roi.is_empty():
            return True
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        return self._roi.contains_point(cx, cy, width, height)

    def _has_person_nearby(
        self,
        obj_bbox: tuple[int, int, int, int],
        persons: list[Detection],
    ) -> bool:
        if not persons:
            return False
        ox = (obj_bbox[0] + obj_bbox[2]) / 2
        oy = (obj_bbox[1] + obj_bbox[3]) / 2
        for p in persons:
            px = (p.bbox[0] + p.bbox[2]) / 2
            py = (p.bbox[1] + p.bbox[3]) / 2
            if ((ox - px) ** 2 + (oy - py) ** 2) ** 0.5 <= self._proximity_distance:
                return True
        return False

    def reset(self) -> None:
        self._tracks.clear()
        self._last_alert_time = 0.0

    @staticmethod
    def _encode_snapshot(frame: np.ndarray) -> bytes:
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return buf.tobytes()


def create_analyzer(config: dict) -> TakeAwayAnalyzer:
    ana_cfg = config["analyzer"]
    roi_points = ana_cfg.get("roi") or []
    roi = Roi(polygon_norm=[tuple(p) for p in roi_points]) if roi_points else None
    return TakeAwayAnalyzer(
        disappear_frames=ana_cfg["disappear_frames"],
        recent_frames_window=ana_cfg.get("recent_frames_window", 30),
        proximity_distance=ana_cfg.get("proximity_distance", 200.0),
        alert_cooldown=ana_cfg["alert_cooldown"],
        roi=roi,
    )
