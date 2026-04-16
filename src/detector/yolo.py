"""YOLOv8 检测器实现（可选 ByteTrack 追踪）。"""

from __future__ import annotations

import numpy as np
from ultralytics import YOLO

from src.common.logger import setup_logger
from src.common.models import Detection
from src.detector.base import BaseDetector

logger = setup_logger(__name__)


class YOLODetector(BaseDetector):
    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        confidence: float = 0.5,
        target_classes: list[str] | None = None,
        enable_tracking: bool = True,
        tracker: str = "bytetrack.yaml",
    ):
        self._model_name = model_name
        self._confidence = confidence
        self._target_classes = set(target_classes) if target_classes else None
        self._enable_tracking = enable_tracking
        self._tracker = tracker
        self._model: YOLO | None = None

    def load(self) -> None:
        logger.info("加载模型: %s (tracking=%s)", self._model_name, self._enable_tracking)
        self._model = YOLO(self._model_name)
        logger.info("模型加载完成")

    def detect(self, frame: np.ndarray) -> list[Detection]:
        if self._model is None:
            raise RuntimeError("模型未加载，请先调用 load()")

        if self._enable_tracking:
            results = self._model.track(
                frame,
                conf=self._confidence,
                tracker=self._tracker,
                persist=True,
                verbose=False,
            )
        else:
            results = self._model(frame, conf=self._confidence, verbose=False)

        detections = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                label = result.names[int(box.cls[0])]
                if self._target_classes and label not in self._target_classes:
                    continue
                x1, y1, x2, y2 = box.xyxy[0].int().tolist()
                track_id = int(box.id[0]) if box.id is not None else None
                detections.append(Detection(
                    label=label,
                    confidence=float(box.conf[0]),
                    bbox=(x1, y1, x2, y2),
                    track_id=track_id,
                ))

        return detections

    def unload(self) -> None:
        self._model = None
        logger.info("模型已释放")


def create_detector(config: dict) -> YOLODetector:
    det_cfg = config["detector"]
    track_cfg = det_cfg.get("tracking", {})
    return YOLODetector(
        model_name=det_cfg["model"],
        confidence=det_cfg["confidence"],
        target_classes=det_cfg.get("target_classes"),
        enable_tracking=track_cfg.get("enabled", True),
        tracker=track_cfg.get("tracker", "bytetrack.yaml"),
    )
