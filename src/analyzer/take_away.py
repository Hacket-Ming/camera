"""'拿东西走'行为识别 — 基于规则的实现。

策略：
1. 追踪 ROI 区域内的物体数量
2. 当检测到人出现且物体数量减少时，判定为"拿东西走"
3. 冷却机制避免重复告警
"""

import time
from datetime import datetime

import cv2
import numpy as np

from src.common.logger import setup_logger
from src.common.models import Detection, Event, FrameData
from src.analyzer.base import BaseAnalyzer

logger = setup_logger(__name__)

# 非人物类别，用于统计物体
_PERSON_LABEL = "person"


class TakeAwayAnalyzer(BaseAnalyzer):
    def __init__(self, disappear_frames: int = 15, alert_cooldown: float = 10.0):
        self._disappear_frames = disappear_frames
        self._alert_cooldown = alert_cooldown

        # 内部状态
        self._baseline_object_count: int | None = None
        self._missing_counter: int = 0
        self._last_alert_time: float = 0.0
        self._person_present: bool = False

    def analyze(self, frame_data: FrameData) -> list[Event]:
        detections = frame_data.detections
        persons = [d for d in detections if d.label == _PERSON_LABEL]
        objects = [d for d in detections if d.label != _PERSON_LABEL]

        self._person_present = len(persons) > 0
        current_count = len(objects)

        # 初始化基线
        if self._baseline_object_count is None:
            self._baseline_object_count = current_count
            return []

        events = []

        # 物体数量减少且有人在场
        if self._person_present and current_count < self._baseline_object_count:
            self._missing_counter += 1
        else:
            self._missing_counter = max(0, self._missing_counter - 1)

        # 连续多帧物体减少，触发告警
        if self._missing_counter >= self._disappear_frames:
            now = time.time()
            if now - self._last_alert_time > self._alert_cooldown:
                snapshot = self._encode_snapshot(frame_data.frame)
                events.append(Event(
                    event_type="take_away",
                    description=(
                        f"检测到拿走行为: 物体数量从 {self._baseline_object_count} "
                        f"减少到 {current_count}"
                    ),
                    timestamp=frame_data.timestamp,
                    snapshot=snapshot,
                ))
                self._last_alert_time = now
                logger.warning("触发告警: 拿东西走 (物体 %d → %d)",
                               self._baseline_object_count, current_count)

            # 更新基线
            self._baseline_object_count = current_count
            self._missing_counter = 0

        return events

    def reset(self) -> None:
        self._baseline_object_count = None
        self._missing_counter = 0
        self._last_alert_time = 0.0
        self._person_present = False

    @staticmethod
    def _encode_snapshot(frame: np.ndarray) -> bytes:
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return buf.tobytes()


def create_analyzer(config: dict) -> TakeAwayAnalyzer:
    ana_cfg = config["analyzer"]
    return TakeAwayAnalyzer(
        disappear_frames=ana_cfg["disappear_frames"],
        alert_cooldown=ana_cfg["alert_cooldown"],
    )
