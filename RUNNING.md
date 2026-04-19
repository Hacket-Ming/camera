# 运行与部署指南

本文档说明如何在本机或服务器上把项目跑起来。功能详情见 [README.md](README.md)，开发路线见 [plan.md](plan.md)。

---

## 1. 环境准备

### 系统要求

| 项 | 要求 |
|---|---|
| 操作系统 | macOS / Linux（Windows 未验证） |
| Python | 3.9+（推荐 3.10/3.11） |
| 摄像头 | 本地 USB / 笔记本内置 / RTSP IP 摄像头 |
| 磁盘 | ≥ 200 MB（含 yolov8n.pt ≈ 6 MB + 依赖） |

### 必装组件

```bash
# macOS（已装 Homebrew）
brew install python@3.11

# Linux（Debian/Ubuntu）
sudo apt update
sudo apt install -y python3 python3-venv python3-pip libgl1
```

> Linux 服务器若未安装图形库，OpenCV 加载会缺 `libGL.so.1`，需补装 `libgl1`。

---

## 2. 获取代码与依赖

```bash
git clone https://github.com/Hacket-Ming/camera.git
cd camera

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

> 首次运行时 ultralytics 会自动下载 `yolov8n.pt`（约 6 MB），需联网。

---

## 3. 配置

主配置文件：`config/default.yaml`。常改参数：

```yaml
camera:
  source_type: local          # local（本机摄像头）/ rtsp / file
  device_index: 0             # 本机摄像头索引
  rtsp_url: ""                # RTSP 地址，例: rtsp://user:pass@192.168.1.10/stream
  video_path: ""              # 视频文件路径

detector:
  confidence: 0.5             # 置信度阈值，过滤弱检测
  target_classes:             # 关注的 COCO 类别
    - person
    - cup
    - cell phone

analyzer:
  roi: []                     # 多边形归一化坐标，例: [[0.2,0.3],[0.8,0.3],[0.8,0.9],[0.2,0.9]]
  disappear_frames: 15        # 物体连续 N 帧未出现判定消失
  proximity_distance: 200     # 人/物关联距离（像素）
  alert_cooldown: 10          # 告警冷却（秒）

server:
  host: "0.0.0.0"
  port: 8000

storage:
  enabled: true
  database_path: data/events/events.db
  snapshot_dir: data/snapshots
```

> 可复制一份自定义：`cp config/default.yaml config/local.yaml`，运行时用 `--config` 指定。

---

## 4. 运行模式

项目支持三种运行方式：

### 模式 A：本机预览窗口（默认）

弹出 OpenCV 窗口，画面带检测框 + track_id + FPS。

```bash
python main.py
```

按 `q` 退出。

> **macOS 第一次会弹系统授权对话框**，需允许终端访问摄像头，否则报 `not authorized to capture video`。

### 模式 B：无窗口（适合服务器/无界面环境）

仅在终端打日志，事件入库。

```bash
python main.py --no-window
```

按 `Ctrl+C` 停止。

### 模式 C：Web 服务（推荐用于远程查看）

启动 FastAPI，浏览器实时看画面 + 事件流。

```bash
python main.py --serve
```

打开浏览器：

- 监控页：<http://localhost:8000/>
- 事件 API：<http://localhost:8000/api/events?limit=50>
- API 文档：<http://localhost:8000/docs>

如需远程访问，确保 `server.host=0.0.0.0` 并放通 `server.port`。

---

## 5. 验证

### 单元测试（不需要摄像头/模型）

```bash
pytest tests/ -q
```

应输出 `22 passed`。

### 端到端检查（需要摄像头）

```bash
python main.py --serve
```

1. 浏览器打开 <http://localhost:8000/>，确认右上角连接状态变绿
2. 画面中出现自己 → 标注红色框 `person #N`
3. 拿一个杯子（或手机/书）放进画面、再快速移出 → 几秒后右侧"事件记录"出现 `[take_away] cup #N 被拿走`
4. 检查 `data/events/events.db` 与 `data/snapshots/*.jpg` 已落盘

---

## 6. 常见问题

| 现象 | 原因 / 解决 |
|---|---|
| `not authorized to capture video`（macOS） | 系统设置 → 隐私与安全 → 摄像头 → 勾选终端 |
| `Could not find a backend for the camera` | 设备索引错误，改 `camera.device_index` 试 0/1/2 |
| `CERTIFICATE_VERIFY_FAILED`（首次下载模型） | 网络受限；可手动下载 yolov8n.pt 放到项目根目录 |
| FPS 偏低（< 5） | CPU 性能不够；改用 `yolov8n.pt`（最小模型）或后续考虑 GPU/MPS |
| Web 模式画面卡顿 | 调低 `server.stream_quality`（默认 70），或降低摄像头分辨率 |
| RTSP 连接不上 | 确认地址含用户名/密码；用 `ffplay <url>` 先验证可拉流 |
| 同一物体 track_id 频繁变化 | ByteTrack 在快速运动/遮挡下会断 ID；可调 `analyzer.disappear_frames` 容忍更长间隔 |

---

## 7. 后台运行（生产部署提示）

### Linux systemd

新建 `/etc/systemd/system/camera-monitor.service`：

```ini
[Unit]
Description=Camera Behavior Monitor
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/opt/camera
ExecStart=/opt/camera/venv/bin/python main.py --serve
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now camera-monitor
sudo journalctl -u camera-monitor -f
```

### nohup（简单场景）

```bash
nohup ./venv/bin/python main.py --serve > camera.log 2>&1 &
```

### Docker

容器化部署在 Phase 5 计划中，目前未提供 Dockerfile。

---

## 8. 数据目录约定

| 路径 | 用途 |
|---|---|
| `data/events/events.db` | SQLite 事件元信息 |
| `data/snapshots/*.jpg` | 每次告警的画面快照 |
| `yolov8n.pt` | YOLOv8 nano 模型权重 |

可定期清理 `data/snapshots/` 老文件控制磁盘占用。
