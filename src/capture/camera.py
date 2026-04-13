"""本地摄像头 / RTSP / 视频文件采集实现。"""

import cv2
import numpy as np

from src.capture.base import BaseCapture
from src.common.logger import setup_logger

logger = setup_logger(__name__)


class CameraCapture(BaseCapture):
    """基于 OpenCV VideoCapture 的通用采集器。

    支持：
    - 本地摄像头（device_index=0,1,...）
    - RTSP 流（rtsp://...）
    - 视频文件（/path/to/video.mp4）
    """

    def __init__(
        self,
        source: int | str = 0,
        width: int = 1280,
        height: int = 720,
        fps: int = 0,
    ):
        self._source = source
        self._width = width
        self._height = height
        self._fps = fps
        self._cap: cv2.VideoCapture | None = None

    def open(self) -> None:
        logger.info("打开视频源: %s", self._source)
        self._cap = cv2.VideoCapture(self._source)
        if not self._cap.isOpened():
            raise RuntimeError(f"无法打开视频源: {self._source}")

        if isinstance(self._source, int):
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
            if self._fps > 0:
                self._cap.set(cv2.CAP_PROP_FPS, self._fps)

        actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self._cap.get(cv2.CAP_PROP_FPS)
        logger.info("视频源已打开: %dx%d @ %.1f fps", actual_w, actual_h, actual_fps)

    def read(self) -> tuple[bool, np.ndarray | None]:
        if self._cap is None:
            return False, None
        ret, frame = self._cap.read()
        if not ret:
            return False, None
        return True, frame

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.info("视频源已释放")

    def is_opened(self) -> bool:
        return self._cap is not None and self._cap.isOpened()


def create_capture(config: dict) -> CameraCapture:
    """根据配置创建对应的采集器。"""
    cam_cfg = config["camera"]
    source_type = cam_cfg["source_type"]

    if source_type == "local":
        source = cam_cfg["device_index"]
    elif source_type == "rtsp":
        source = cam_cfg["rtsp_url"]
    elif source_type == "file":
        source = cam_cfg["video_path"]
    else:
        raise ValueError(f"不支持的视频源类型: {source_type}")

    return CameraCapture(
        source=source,
        width=cam_cfg["width"],
        height=cam_cfg["height"],
        fps=cam_cfg["fps"],
    )
