"""公共数据模型，各层共享。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

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
    # 结构化信息（track_id, label, bbox 等），便于查询与展示
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Roi:
    """感兴趣区域 — 多边形，归一化坐标 [0,1]。

    提供像素坐标下的点包含判定，供分析器过滤 ROI 外的物体。
    """
    # 归一化多边形顶点 [(x, y), ...]，顺时针或逆时针皆可
    polygon_norm: list[tuple[float, float]]

    def is_empty(self) -> bool:
        return len(self.polygon_norm) < 3

    def to_pixels(self, width: int, height: int) -> list[tuple[int, int]]:
        return [(int(x * width), int(y * height)) for x, y in self.polygon_norm]

    def contains_point(self, x: float, y: float, width: int, height: int) -> bool:
        """射线法判断点是否在多边形内（像素坐标）。空 ROI 视为包含全部。"""
        if self.is_empty():
            return True
        poly = self.to_pixels(width, height)
        inside = False
        n = len(poly)
        j = n - 1
        for i in range(n):
            xi, yi = poly[i]
            xj, yj = poly[j]
            if ((yi > y) != (yj > y)) and (
                x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi
            ):
                inside = not inside
            j = i
        return inside
