"""主处理管线 — 串联采集、检测、分析各层。"""

from __future__ import annotations

import time
from collections import deque
from datetime import datetime

import cv2
import numpy as np

from src.analyzer.base import BaseAnalyzer
from src.capture.base import BaseCapture
from src.common.logger import setup_logger
from src.common.models import FrameData
from src.detector.base import BaseDetector

logger = setup_logger(__name__)

# 人体固定红色，便于一眼识别
_PERSON_COLOR = (0, 0, 255)
# 物体调色板（BGR），按 track_id 哈希取色，保证同一物体跨帧颜色稳定
_PALETTE = [
    (0, 255, 0), (255, 128, 0), (255, 0, 255), (0, 255, 255),
    (255, 255, 0), (128, 0, 255), (0, 128, 255), (255, 0, 128),
]


class Pipeline:
    """视频处理管线 — 串联 采集→检测→分析→渲染。"""

    def __init__(self, capture: BaseCapture, detector: BaseDetector,
                 analyzer: BaseAnalyzer, fps_window: int = 30):
        self._capture = capture
        self._detector = detector
        self._analyzer = analyzer
        self._frame_id = 0
        self._running = False
        self._frame_times: deque[float] = deque(maxlen=fps_window)

    def run(self, show_window: bool = True) -> None:
        self._capture.open()
        self._detector.load()
        self._running = True
        logger.info("管线启动")

        try:
            while self._running:
                t0 = time.perf_counter()
                ok, frame = self._capture.read()
                if not ok:
                    logger.warning("读取帧失败，退出")
                    break

                self._frame_id += 1
                frame_data = FrameData(
                    frame=frame,
                    timestamp=datetime.now(),
                    frame_id=self._frame_id,
                )

                frame_data.detections = self._detector.detect(frame)

                events = self._analyzer.analyze(frame_data)
                for event in events:
                    logger.info("事件: [%s] %s", event.event_type, event.description)

                self._frame_times.append(time.perf_counter() - t0)
                fps = self._compute_fps()

                annotated = self._draw_overlay(frame, frame_data, fps)

                if show_window:
                    cv2.imshow("Camera Monitor", annotated)
                    if (cv2.waitKey(1) & 0xFF) == ord("q"):
                        logger.info("用户按 q 退出")
                        break
        finally:
            self.stop()

    def stop(self) -> None:
        self._running = False
        self._capture.release()
        self._detector.unload()
        cv2.destroyAllWindows()
        logger.info("管线已停止")

    def _compute_fps(self) -> float:
        if not self._frame_times:
            return 0.0
        avg = sum(self._frame_times) / len(self._frame_times)
        return 1.0 / avg if avg > 0 else 0.0

    def _draw_overlay(self, frame: np.ndarray, frame_data: FrameData,
                      fps: float) -> np.ndarray:
        annotated = frame.copy()

        for det in frame_data.detections:
            x1, y1, x2, y2 = det.bbox
            color = _PERSON_COLOR if det.label == "person" else self._color_for(det.track_id)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            tid_str = f" #{det.track_id}" if det.track_id is not None else ""
            label = f"{det.label}{tid_str} {det.confidence:.2f}"
            cv2.putText(annotated, label, (x1, max(y1 - 8, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        info = f"FPS: {fps:.1f}  Frame: {frame_data.frame_id}"
        cv2.putText(annotated, info, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        return annotated

    @staticmethod
    def _color_for(track_id: int | None) -> tuple[int, int, int]:
        if track_id is None:
            return (0, 255, 0)
        return _PALETTE[track_id % len(_PALETTE)]
