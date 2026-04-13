# 智能摄像头行为识别系统

基于 YOLOv8 的实时视频行为识别系统，支持检测"拿东西走"等异常行为并记录告警。

## 功能

- 实时视频采集（本地摄像头 / RTSP / 视频文件）
- YOLOv8 目标检测（人体 + 物体）
- 基于规则的行为分析（物体消失 + 人员移动 → 告警）
- 画面实时标注（检测框 + 置信度）

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
│   ├── server/                # 服务层（FastAPI，Phase 4 完善）
│   │   └── app.py
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
# 默认（本地摄像头，弹出预览窗口）
python main.py

# 无窗口模式（服务器部署）
python main.py --no-window

# 使用自定义配置
python main.py --config config/default.yaml
```

按 `q` 退出预览窗口。

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
| 2 | YOLOv8 精调、物体追踪 | 计划中 |
| 3 | 行为规则完善、事件数据库 | 计划中 |
| 4 | FastAPI 后端、WebSocket 实时推流、前端页面 | 计划中 |
| 5 | IP 摄像头 RTSP 接入、C++ 推理优化、Docker 部署 | 计划中 |
