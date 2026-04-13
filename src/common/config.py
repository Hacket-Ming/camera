from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_CONFIG = _PROJECT_ROOT / "config" / "default.yaml"


def load_config(path: Path | str | None = None) -> dict[str, Any]:
    """加载 YAML 配置文件，返回字典。"""
    config_path = Path(path) if path else _DEFAULT_CONFIG
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_project_root() -> Path:
    return _PROJECT_ROOT
