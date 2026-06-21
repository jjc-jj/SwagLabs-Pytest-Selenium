# File: utils/data_loader.py
"""数据加载工具 — JSON / YAML 外部测试数据解析。

提供统一的文件读取接口，自动基于 ``automation/`` 根目录
解析相对路径，避免测试代码中硬编码绝对路径。

Usage::

    from utils.data_loader import load_json, load_yaml

    login_cases = load_json('data/login_data.json')
    shipping_data = load_yaml('data/checkout_data.yaml')
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

# automation/ 根目录（utils/ 的父目录）
_AUTOMATION_ROOT = Path(__file__).resolve().parent.parent


def load_json(
    filepath: str,
    base_dir: Optional[Path] = None,
) -> Any:
    """加载 JSON 文件。

    Args:
        filepath: JSON 文件相对路径（相对于 ``automation/`` 根目录）。
        base_dir: 自定义基准目录，默认 ``automation/``。

    Returns:
        解析后的 Python 对象（dict / list / str / int 等）。

    Raises:
        FileNotFoundError: 文件不存在。
        json.JSONDecodeError: JSON 格式错误。
    """
    base = base_dir or _AUTOMATION_ROOT
    full_path = base / filepath
    if not full_path.exists():
        raise FileNotFoundError(
            f'JSON 数据文件不存在: {full_path}'
        )
    with open(full_path, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def load_yaml(
    filepath: str,
    base_dir: Optional[Path] = None,
) -> Any:
    """加载 YAML 文件。

    Args:
        filepath: YAML 文件相对路径（相对于 ``automation/`` 根目录）。
        base_dir: 自定义基准目录，默认 ``automation/``。

    Returns:
        解析后的 Python 对象。

    Raises:
        FileNotFoundError: 文件不存在。
        yaml.YAMLError: YAML 解析错误。
    """
    base = base_dir or _AUTOMATION_ROOT
    full_path = base / filepath
    if not full_path.exists():
        raise FileNotFoundError(
            f'YAML 数据文件不存在: {full_path}'
        )
    with open(full_path, 'r', encoding='utf-8') as fh:
        return yaml.safe_load(fh)
