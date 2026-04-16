"""公共数据模型，各层共享。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np


@dataclass
class Detection:
    """单个检测结果。"""
    label: str
    confidence: float
    # 边界框 (x1, y1, x2, y2)，像素坐标
    bbox: tuple[int, int, int, int]
    # 追踪 ID，启用追踪后由 tracker 分配；首帧或未启用时为 None
    track_id: int | None = None


@dataclass
class FrameData:
    """一帧的完整数据，在各层之间传递。"""
    frame: np.ndarray
    timestamp: datetime
    frame_id: int
    detections: list[Detection] = field(default_factory=list)


@dataclass
class Event:
    """行为事件记录。"""
    event_type: str
    description: str
    timestamp: datetime
    # 事件发生时的截图（JPEG 字节），可选
    snapshot: bytes | None = None
