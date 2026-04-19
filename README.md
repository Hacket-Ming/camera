# 智能摄像头行为识别系统

基于 YOLOv8 的实时视频行为识别系统，支持检测"拿东西走"等异常行为并记录告警。

> 完整运行/部署步骤见 [RUNNING.md](RUNNING.md)，开发路线见 [plan.md](plan.md)。

## 功能

- 实时视频采集（本地摄像头 / RTSP / 视频文件）
- YOLOv8 目标检测 + ByteTrack 多目标追踪
- 基于追踪的行为分析（物体消失 + 人员靠近 → "拿东西走"告警）
- ROI 区域过滤（多边形归一化坐标，仅监控关注区域）
- 事件持久化（SQLite + 快照 JPEG 落盘）
- 画面实时标注（检测框 + track_id + FPS + ROI 轮廓）
- Web 监控界面（FastAPI + WebSocket，浏览器看实时画面与事件流）

## 目录结构

```
camera/
├── main.py                    # 启动入口
├── plan.md                    # 项目规划与开发路线
├── requirements.txt           # Python 依赖
├── config/
│   └── default.yaml           # 全局配置（摄像头/检测/分析参数）
├── src/
│   ├── pipeline.py            # 主处理管线（串联各层）
│   ├── capture/               # 采集层
│   │   ├── base.py            #   抽象接口 BaseCapture
│   │   └── camera.py          #   OpenCV 实现（本地/RTSP/文件）
│   ├── detector/              # 检测层
│   │   ├── base.py            #   抽象接口 BaseDetector
│   │   └── yolo.py            #   YOLOv8 实现
│   ├── analyzer/              # 分析层
│   │   ├── base.py            #   抽象接口 BaseAnalyzer
│   │   └── take_away.py       #   "拿东西走"规则引擎
│   ├── server/                # 服务层（FastAPI + WebSocket）
│   │   ├── app.py            #   REST + WS 路由
│   │   ├── frame_bus.py      #   线程→asyncio 桥接
│   │   ├── static/           #   前端 JS/CSS
│   │   └── templates/        #   监控页面 HTML
│   ├── storage/               # 事件存储层
│   │   ├── base.py            #   抽象接口
│   │   └── sqlite_store.py    #   SQLite + 快照文件落盘
│   └── common/                # 公共模块
│       ├── config.py          #   配置加载
│       ├── logger.py          #   日志
│       └── models.py          #   共享数据模型
├── data/events/               # 事件数据存储
└── tests/                     # 测试目录
```

## 环境要求

- Python 3.9+
- macOS / Linux

## 快速开始

**1. 创建虚拟环境并安装依赖**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. 运行**

```bash
# 默认（本地摄像头，弹出 OpenCV 预览窗口）
python main.py

# 无窗口模式（仅终端日志，事件入库）
python main.py --no-window

# Web 模式：浏览器访问 http://localhost:8000
python main.py --serve

# 使用自定义配置
python main.py --config config/default.yaml
```

预览窗口按 `q` 退出；Web 模式按 `Ctrl+C` 停止。

## 配置说明

编辑 `config/default.yaml` 调整参数：

```yaml
camera:
  source_type: local    # local / rtsp / file
  device_index: 0       # 本地摄像头索引
  rtsp_url: ""          # RTSP 地址

detector:
  model: yolov8n.pt     # 模型（首次运行自动下载）
  confidence: 0.5       # 置信度阈值

analyzer:
  disappear_frames: 15  # 物体消失判定帧数
  alert_cooldown: 10    # 告警冷却时间（秒）
```

## 架构设计

各层通过抽象接口解耦，便于后期替换实现：

```
采集层 (BaseCapture)
  └─ 后期可替换为 C++ ONNX / RTSP 实现

检测层 (BaseDetector)
  └─ 后期可替换为 ONNX Runtime / TensorRT

分析层 (BaseAnalyzer)
  └─ 后期可升级为深度学习动作识别模型
```

## 开发路线

| Phase | 内容 | 状态 |
|-------|------|------|
| 1 | 项目骨架、采集、检测、基础行为规则 | 完成 |
| 2 | ByteTrack 物体追踪、画面增强（FPS/track_id） | 完成 |
| 3 | ROI 过滤、SQLite 事件持久化、快照落盘 | 完成 |
| 4 | FastAPI 后端、WebSocket 实时推流、前端页面 | 完成 |
| 5 | IP 摄像头 RTSP 接入、C++ 推理优化、Docker 部署 | 计划中 |
