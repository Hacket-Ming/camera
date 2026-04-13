"""主处理管线 — 串联采集、检测、分析各层。"""

from datetime import datetime

import cv2

from src.capture.base import BaseCapture
from src.detector.base import BaseDetector
from src.analyzer.base import BaseAnalyzer
from src.common.logger import setup_logger
from src.common.models import FrameData

logger = setup_logger(__name__)


class Pipeline:
    """视频处理管线。

    将采集层、检测层、分析层串联起来，
    逐帧处理并在画面上标注检测结果。
    """

    def __init__(self, capture: BaseCapture, detector: BaseDetector,
                 analyzer: BaseAnalyzer):
        self._capture = capture
        self._detector = detector
        self._analyzer = analyzer
        self._frame_id = 0
        self._running = False

    def run(self, show_window: bool = True) -> None:
        """启动管线主循环。"""
        self._capture.open()
        self._detector.load()
        self._running = True
        logger.info("管线启动")

        try:
            while self._running:
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

                # 检测
                frame_data.detections = self._detector.detect(frame)

                # 分析
                events = self._analyzer.analyze(frame_data)
                for event in events:
                    logger.info("事件: [%s] %s", event.event_type, event.description)

                # 画面标注
                annotated = self._draw_detections(frame, frame_data)

                if show_window:
                    cv2.imshow("Camera Monitor", annotated)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("q"):
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

    @staticmethod
    def _draw_detections(frame, frame_data: FrameData):
        annotated = frame.copy()
        for det in frame_data.detections:
            x1, y1, x2, y2 = det.bbox
            color = (0, 255, 0) if det.label != "person" else (0, 0, 255)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            label_text = f"{det.label} {det.confidence:.2f}"
            cv2.putText(annotated, label_text, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        return annotated
