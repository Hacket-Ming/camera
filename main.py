"""项目入口 — 启动视频处理管线。

用法:
    python main.py                    # 使用默认配置（弹出窗口）
    python main.py --config my.yaml   # 使用自定义配置
    python main.py --no-window        # 无窗口模式（仅终端日志）
    python main.py --serve            # Web 模式：浏览器访问 http://<host>:<port>
"""

import argparse
import sys
import threading

from src.common.config import load_config
from src.common.logger import setup_logger
from src.common.models import Roi
from src.capture.camera import create_capture
from src.detector.yolo import create_detector
from src.analyzer.take_away import create_analyzer
from src.pipeline import Pipeline
from src.storage.sqlite_store import create_event_store

logger = setup_logger("main")


def _build_pipeline(config, frame_bus=None):
    capture = create_capture(config)
    detector = create_detector(config)
    analyzer = create_analyzer(config)
    event_store = create_event_store(config)

    roi_points = (config.get("analyzer") or {}).get("roi") or []
    roi = Roi(polygon_norm=[tuple(p) for p in roi_points]) if roi_points else None

    stream_quality = (config.get("server") or {}).get("stream_quality", 70)

    pipeline = Pipeline(
        capture, detector, analyzer,
        event_store=event_store, roi=roi,
        frame_bus=frame_bus, stream_quality=stream_quality,
    )
    return pipeline, event_store


def _run_local(config, show_window: bool) -> None:
    pipeline, _ = _build_pipeline(config)
    try:
        pipeline.run(show_window=show_window)
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在退出...")
        pipeline.stop()
        sys.exit(0)


def _run_serve(config) -> None:
    import uvicorn

    from src.server.app import create_app
    from src.server.frame_bus import FrameBus

    bus = FrameBus()
    pipeline, event_store = _build_pipeline(config, frame_bus=bus)

    snapshot_dir = (config.get("storage") or {}).get("snapshot_dir", "data/snapshots")
    server_cfg = config.get("server") or {}
    app = create_app(
        event_store=event_store,
        frame_bus=bus,
        snapshot_dir=snapshot_dir,
    )

    pipeline_thread = threading.Thread(
        target=lambda: pipeline.run(show_window=False),
        name="pipeline",
        daemon=True,
    )
    pipeline_thread.start()
    logger.info("管线后台线程已启动")

    host = server_cfg.get("host", "0.0.0.0")
    port = server_cfg.get("port", 8000)
    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    finally:
        pipeline.stop()


def main():
    parser = argparse.ArgumentParser(description="智能摄像头行为识别系统")
    parser.add_argument("--config", type=str, default=None,
                        help="配置文件路径（默认 config/default.yaml）")
    parser.add_argument("--no-window", action="store_true",
                        help="无窗口模式")
    parser.add_argument("--serve", action="store_true",
                        help="启动 Web 服务（浏览器查看实时画面+事件）")
    args = parser.parse_args()

    config = load_config(args.config)
    logger.info("配置加载完成")

    if args.serve:
        _run_serve(config)
    else:
        _run_local(config, show_window=not args.no_window)


if __name__ == "__main__":
    main()
