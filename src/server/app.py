"""FastAPI 服务 — 提供 REST API、WebSocket 实时画面与事件推送。"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.common.logger import setup_logger
from src.server.frame_bus import FrameBus
from src.storage.base import BaseEventStore

logger = setup_logger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"
_TEMPLATE_DIR = Path(__file__).parent / "templates"


def create_app(
    event_store: BaseEventStore | None = None,
    frame_bus: FrameBus | None = None,
    snapshot_dir: str | Path = "data/snapshots",
    stream_fps: int = 25,
) -> FastAPI:
    """构建 FastAPI 应用，依赖通过参数注入便于测试。"""
    app = FastAPI(title="智能摄像头行为识别系统")

    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
    snap_dir = Path(snapshot_dir)
    snap_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/snapshots", StaticFiles(directory=str(snap_dir)), name="snapshots")

    @app.on_event("startup")
    async def _on_startup() -> None:
        if frame_bus is not None:
            frame_bus.attach_loop(asyncio.get_running_loop())
            logger.info("FrameBus 绑定事件循环")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        html_path = _TEMPLATE_DIR / "index.html"
        if not html_path.exists():
            return HTMLResponse("<h1>监控页面未生成</h1>", status_code=500)
        return HTMLResponse(html_path.read_text(encoding="utf-8"))

    @app.get("/api/events")
    async def list_events(
        event_type: Optional[str] = Query(None, description="按事件类型过滤"),
        start: Optional[str] = Query(None, description="ISO8601 起始时间"),
        end: Optional[str] = Query(None, description="ISO8601 截止时间"),
        limit: int = Query(100, ge=1, le=1000),
    ):
        if event_store is None:
            return {"events": []}
        try:
            start_dt = datetime.fromisoformat(start) if start else None
            end_dt = datetime.fromisoformat(end) if end else None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"时间格式错误: {exc}") from exc
        events = event_store.query(
            event_type=event_type, start=start_dt, end=end_dt, limit=limit
        )
        return {"events": events}

    @app.websocket("/ws/stream")
    async def ws_stream(ws: WebSocket) -> None:
        await ws.accept()
        if frame_bus is None:
            await ws.close(code=1011, reason="frame bus 未启用")
            return
        last_seq = -1
        interval = 1.0 / max(stream_fps, 1)
        try:
            while True:
                seq, jpeg = frame_bus.get_latest_frame()
                if jpeg is not None and seq != last_seq:
                    await ws.send_bytes(jpeg)
                    last_seq = seq
                await asyncio.sleep(interval)
        except WebSocketDisconnect:
            pass
        except Exception:
            logger.exception("WS stream 异常")

    @app.websocket("/ws/events")
    async def ws_events(ws: WebSocket) -> None:
        await ws.accept()
        if frame_bus is None:
            await ws.close(code=1011, reason="frame bus 未启用")
            return
        q = frame_bus.subscribe_events()
        try:
            while True:
                event = await q.get()
                await ws.send_json(event)
        except WebSocketDisconnect:
            pass
        except Exception:
            logger.exception("WS events 异常")
        finally:
            frame_bus.unsubscribe_events(q)

    return app
