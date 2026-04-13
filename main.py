"""项目入口 — 启动视频处理管线。

用法:
    python main.py                    # 使用默认配置
    python main.py --config my.yaml   # 使用自定义配置
    python main.py --no-window        # 无窗口模式（服务器部署）
"""

import argparse
import sys

from src.common.config import load_config
from src.common.logger import setup_logger
from src.capture.camera import create_capture
from src.detector.yolo import create_detector
from src.analyzer.take_away import create_analyzer
from src.pipeline import Pipeline

logger = setup_logger("main")


def main():
    parser = argparse.ArgumentParser(description="智能摄像头行为识别系统")
    parser.add_argument("--config", type=str, default=None,
                        help="配置文件路径（默认 config/default.yaml）")
    parser.add_argument("--no-window", action="store_true",
                        help="无窗口模式")
    args = parser.parse_args()

    config = load_config(args.config)
    logger.info("配置加载完成")

    capture = create_capture(config)
    detector = create_detector(config)
    analyzer = create_analyzer(config)

    pipeline = Pipeline(capture, detector, analyzer)

    try:
        pipeline.run(show_window=not args.no_window)
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在退出...")
        pipeline.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()
