"""FastAPI 服务 — 提供 REST API 和 WebSocket 实时画面。"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(title="智能摄像头行为识别系统")

_STATIC_DIR = Path(__file__).parent / "static"
_TEMPLATE_DIR = Path(__file__).parent / "templates"

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/")
async def index():
    return {"status": "running", "message": "智能摄像头行为识别系统"}


@app.get("/api/events")
async def get_events():
    """查询历史事件（占位，后续接入数据库）。"""
    return {"events": []}


# WebSocket 实时画面推送将在 Phase 4 实现
