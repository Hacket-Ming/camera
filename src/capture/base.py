"""采集层抽象基类，定义统一接口。"""

from abc import ABC, abstractmethod

import numpy as np


class BaseCapture(ABC):
    """视频采集的统一接口。

    不同来源（本地摄像头、RTSP、视频文件）实现此接口，
    上层代码无需关心视频来源差异。
    """

    @abstractmethod
    def open(self) -> None:
        """打开视频源。"""

    @abstractmethod
    def read(self) -> tuple[bool, np.ndarray | None]:
        """读取一帧。返回 (是否成功, 帧数据)。"""

    @abstractmethod
    def release(self) -> None:
        """释放资源。"""

    @abstractmethod
    def is_opened(self) -> bool:
        """视频源是否已打开。"""

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
