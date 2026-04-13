"""分析层抽象基类。"""

from abc import ABC, abstractmethod

from src.common.models import Event, FrameData


class BaseAnalyzer(ABC):
    """行为分析的统一接口。

    接收带检测结果的帧数据，输出行为事件。
    可替换为基于深度学习的动作识别实现。
    """

    @abstractmethod
    def analyze(self, frame_data: FrameData) -> list[Event]:
        """分析一帧，返回检测到的事件列表（可能为空）。"""

    @abstractmethod
    def reset(self) -> None:
        """重置内部状态。"""
