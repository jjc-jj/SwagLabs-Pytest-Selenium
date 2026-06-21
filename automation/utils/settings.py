# File: utils/settings.py
"""配置解析模块 — 单例模式加载 YAML 全局配置。

提供线程安全的单例配置管理器，所有环境参数（URL、账号、
超时时间、浏览器选项）均通过此类以属性方式访问。

Usage::

    from utils.settings import Settings
    cfg = Settings()
    print(cfg.base_url)         # 'https://www.saucedemo.com/'
    print(cfg.get_account('standard_user'))  # {'username': ..., 'password': ...}
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, ClassVar, Dict, Optional

import yaml


class Settings:
    """全局配置单例。

    首次实例化时自动从 ``config/config.yaml`` 加载配置，
    后续实例化返回同一实例，避免重复 I/O。

    Attributes:
        _instance: 单例引用。
        _config: 已解析的 YAML 字典。
        _lock: 线程安全锁。
    """

    _instance: ClassVar[Optional['Settings']] = None
    _config: ClassVar[Optional[Dict[str, Any]]] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __new__(cls, config_path: Optional[Path] = None) -> 'Settings':
        """返回单例实例（线程安全）。"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """初始化配置（仅首次调用执行加载）。

        Args:
            config_path: YAML 配置文件绝对路径。
                         默认位于 ``automation/config/config.yaml``。
        """
        if self.__class__._config is not None:
            return
        with self.__class__._lock:
            if self.__class__._config is not None:
                return
            if config_path is None:
                # 从 utils/settings.py 向上定位 config/config.yaml
                config_path = (
                    Path(__file__).resolve().parent.parent
                    / 'config' / 'config.yaml'
                )
            self._load_config(config_path)

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _load_config(self, config_path: Path) -> None:
        """从 YAML 文件加载配置。

        Args:
            config_path: YAML 文件路径。

        Raises:
            FileNotFoundError: 配置文件不存在。
            yaml.YAMLError: YAML 解析失败。
        """
        if not config_path.exists():
            raise FileNotFoundError(
                f'配置文件不存在: {config_path}'
            )
        with open(config_path, 'r', encoding='utf-8') as fh:
            self.__class__._config = yaml.safe_load(fh)

    # ------------------------------------------------------------------
    # 环境
    # ------------------------------------------------------------------

    @property
    def base_url(self) -> str:
        """被测系统基础 URL。"""
        return self._config['environment']['base_url']

    @property
    def api_url(self) -> str:
        """API 基础 URL。"""
        return self._config['environment']['api_url']

    # ------------------------------------------------------------------
    # 账号
    # ------------------------------------------------------------------

    def get_account(self, key: str = 'standard_user') -> Dict[str, str]:
        """获取测试账号凭据。

        Args:
            key: 账号键名，默认 ``standard_user``。

        Returns:
            包含 ``username`` 和 ``password`` 的字典。

        Raises:
            KeyError: 账号键名不存在。
        """
        return self._config['accounts'][key]

    @property
    def accounts(self) -> Dict[str, Dict[str, str]]:
        """所有测试账号。"""
        return self._config['accounts']

    # ------------------------------------------------------------------
    # 浏览器
    # ------------------------------------------------------------------

    @property
    def browser_type(self) -> str:
        """浏览器类型：``chrome`` 或 ``edge``。"""
        return self._config['browser']['type'].lower()

    @property
    def browser_headless(self) -> bool:
        """是否启用无头模式。"""
        return bool(self._config['browser']['headless'])

    @property
    def browser_driver_path(self) -> str:
        """WebDriver 可执行文件路径（空字符串表示从 PATH 获取）。"""
        return self._config['browser'].get('driver_path', '')

    # ------------------------------------------------------------------
    # 代理
    # ------------------------------------------------------------------

    @property
    def proxy_enabled(self) -> bool:
        """是否启用代理。"""
        return bool(self._config.get('proxy', {}).get('enabled', False))

    @property
    def proxy_http(self) -> str:
        """HTTP 代理地址。"""
        return self._config.get('proxy', {}).get('http', '')

    @property
    def proxy_https(self) -> str:
        """HTTPS 代理地址。"""
        return self._config.get('proxy', {}).get('https', '')

    @property
    def proxy_bypass(self) -> str:
        """代理绕过列表。"""
        return self._config.get('proxy', {}).get('bypass', '')

    # ------------------------------------------------------------------
    # 加载策略
    # ------------------------------------------------------------------

    @property
    def loading_disable_images(self) -> bool:
        """是否禁用图片加载以提速。"""
        return bool(self._config.get('loading', {}).get('disable_images', True))

    # ------------------------------------------------------------------
    # 超时
    # ------------------------------------------------------------------

    @property
    def implicit_wait(self) -> int:
        return int(self._config['timeout']['implicit_wait'])

    @property
    def explicit_wait(self) -> int:
        return int(self._config['timeout']['explicit_wait'])

    @property
    def page_load_timeout(self) -> int:
        return int(self._config['timeout']['page_load'])

    @property
    def script_timeout(self) -> int:
        return int(self._config['timeout']['script'])

    # ------------------------------------------------------------------
    # 浏览器选项
    # ------------------------------------------------------------------

    @property
    def options(self) -> Dict[str, Any]:
        """浏览器启动选项（ChromeOptions / EdgeOptions 开关）。"""
        return self._config['options']

    # ------------------------------------------------------------------
    # 日志
    # ------------------------------------------------------------------

    @property
    def log_level(self) -> str:
        return self._config['logging']['level'].upper()

    @property
    def log_format(self) -> str:
        return self._config['logging']['format']

    @property
    def log_date_format(self) -> str:
        return self._config['logging']['date_format']

    @property
    def log_file_dir(self) -> str:
        return self._config['logging']['file_dir']

    @property
    def log_when(self) -> str:
        return self._config['logging']['when']

    @property
    def log_interval(self) -> int:
        return int(self._config['logging'].get('interval', 1))

    @property
    def log_backup_count(self) -> int:
        return int(self._config['logging']['backup_count'])

    @property
    def log_console_output(self) -> bool:
        return bool(self._config['logging']['console_output'])

    # ------------------------------------------------------------------
    # 截图
    # ------------------------------------------------------------------

    @property
    def screenshot_on_failure(self) -> bool:
        return bool(self._config['screenshot']['on_failure'])

    @property
    def screenshot_save_path(self) -> str:
        return self._config['screenshot']['save_path']

    @property
    def screenshot_format(self) -> str:
        return self._config['screenshot']['format']

    # ------------------------------------------------------------------
    # 重试
    # ------------------------------------------------------------------

    @property
    def retry_max_attempts(self) -> int:
        return int(self._config['retry']['max_attempts'])

    @property
    def retry_delay(self) -> int:
        return int(self._config['retry']['delay'])

    # ------------------------------------------------------------------
    # 便捷方法
    # ------------------------------------------------------------------

    def get(self, *keys: str, default: Any = None) -> Any:
        """通过点路径获取嵌套配置值。

        Args:
            *keys: 层级键序列，如 ``('timeout', 'implicit_wait')``。
            default: 键缺失时的默认值。

        Returns:
            配置值或 default。
        """
        node = self._config
        for key in keys:
            if isinstance(node, dict):
                node = node.get(key)
                if node is None:
                    return default
            else:
                return default
        return node
