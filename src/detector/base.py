"""检测层抽象基类。"""

from abc import ABC, abstractmethod

import numpy as np

from src.common.models import Detection


class BaseDetector(ABC):
    """目标检测的统一接口。

    后期可替换为 ONNX Runtime / TensorRT 实现，
    上层代码只依赖此接口。
    """

    @abstractmethod
    def load(self) -> None:
        """加载模型。"""

    @abstractmethod
    def detect(self, frame: np.ndarray) -> list[Detection]:
        """对一帧图像做检测，返回检测结果列表。"""

    @abstractmethod
    def unload(self) -> None:
        """释放模型资源。"""
