# File: utils/driver_factory.py
"""WebDriver 工厂模块 — 企业级浏览器实例工厂。

深度优化网络栈、资源加载策略、进程隔离，确保在跨境/弱网/
企业内网等复杂环境下快速稳定初始化。

核心能力:
    - 页面加载策略 ``eager`` — DOM 就绪即继续，不等待静态资源
    - 硬性超时兜底 — page_load ≤ 15s / script ≤ 10s
    - 图片禁用 — 通过 Chrome Prefs 拦截图片请求（可配置开关）
    - DNS 优化 — 禁用 DoH 升级 + DNS prefetch 控制
    - 干净 Profile — 每次启动独立临时 User Data Dir
    - 企业代理 — 支持 HTTP/HTTPS 代理（YAML 驱动）
    - 防御性初始化 — try/except + DriverInitializationError 自定义异常

Usage::

    from utils.driver_factory import create_driver
    driver = create_driver()
    driver.get('https://www.saucedemo.com/')
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService

from utils.logger_util import get_logger
from utils.settings import Settings

logger = get_logger(__name__)

# ==================================================================
# 自定义异常
# ==================================================================


class DriverInitializationError(Exception):
    """WebDriver 初始化失败时抛出的自定义异常。

    封装底层 Selenium 异常，附加浏览器类型和环境信息，
    便于 CI/CD 日志快速定位根因。
    """

    def __init__(
        self,
        browser: str,
        headless: bool,
        original: Exception,
    ) -> None:
        self.browser = browser
        self.headless = headless
        self.original = original
        super().__init__(
            f'WebDriver 初始化失败 | browser={browser} | '
            f'headless={headless} | 原因: {original}'
        )


# ==================================================================
# 公开 API
# ==================================================================


def create_driver(
    browser_type: Optional[str] = None,
    headless: Optional[bool] = None,
    driver_path: Optional[str] = None,
    settings: Optional[Settings] = None,
    enable_images: Optional[bool] = None,
) -> webdriver.Remote:
    """创建 WebDriver 实例（企业级配置）。

    所有参数均可选，未传入时自动从 YAML 配置读取。

    Args:
        browser_type: ``'chrome'`` 或 ``'edge'``，默认从配置读取。
        headless: 是否启用无头模式，默认从配置读取。
        driver_path: WebDriver 可执行文件路径，默认从配置读取
                     （留空则从系统 PATH 自动发现）。
        settings: Settings 实例，常用于测试中注入 mock 配置。
        enable_images: 是否启用图片加载。None 时从配置读取；
                       ``True`` 强制开启（UI 视觉比对），
                       ``False`` 强制关闭（极速模式）。

    Returns:
        配置完成的 :class:`selenium.webdriver.Remote` 实例。

    Raises:
        ValueError: 浏览器类型不支持（非 chrome/edge）。
        FileNotFoundError: 指定的 driver_path 不存在。
        DriverInitializationError: WebDriver 初始化失败
                                   （驱动版本不匹配 / 端口占用 / 超时等）。
    """
    cfg: Settings = settings or Settings()

    browser = (browser_type or cfg.browser_type).lower()
    is_headless = headless if headless is not None else cfg.browser_headless
    driver_exe = driver_path or cfg.browser_driver_path
    show_images = (
        enable_images
        if enable_images is not None
        else not cfg.loading_disable_images
    )

    # 校验 driver 路径
    if driver_exe:
        _path = Path(driver_exe)
        if not _path.exists():
            raise FileNotFoundError(
                f'WebDriver 可执行文件不存在: {driver_exe}'
            )
    else:
        _path = None

    # 分发 + 防御性初始化
    try:
        if browser == 'chrome':
            return _create_chrome(
                headless=is_headless,
                driver_path=_path,
                cfg=cfg,
                enable_images=show_images,
            )
        elif browser == 'edge':
            return _create_edge(
                headless=is_headless,
                driver_path=_path,
                cfg=cfg,
                enable_images=show_images,
            )
        else:
            raise ValueError(
                f'不支持的浏览器类型: "{browser}"，'
                f'可选值: chrome / edge'
            )
    except DriverInitializationError:
        raise
    except Exception as exc:
        logger.error(
            'WebDriver 初始化异常 | browser=%s | headless=%s | exc=%s',
            browser, is_headless, exc,
        )
        raise DriverInitializationError(browser, is_headless, exc) from exc


# ==================================================================
# 通用参数构建
# ==================================================================


def _build_common_arguments(
    cfg: Settings,
    headless: bool,
) -> list[str]:
    """构建浏览器启动参数列表。

    包含三大类参数：
        1. GPU / 沙箱 / 证书（稳定性）
        2. DNS / 网络（跨境加载优化）
        3. 窗口 / 日志抑制

    Args:
        cfg: Settings 单例。
        headless: 是否无头模式（影响 --no-sandbox 注入）。

    Returns:
        ``--arg`` 形式参数列表。
    """
    opts = cfg.options
    args: list[str] = []

    # ================================================================
    # 第一类: GPU / 沙箱 / 证书 / 扩展
    # ================================================================

    # --disable-gpu: 禁用 GPU 硬件加速
    # 作用: 避免虚拟机/CI 环境中 GPU 驱动不兼容导致黑屏或崩溃
    if opts.get('disable_gpu', True):
        args.append('--disable-gpu')

    # --ignore-certificate-errors: 忽略 SSL 证书错误
    # 作用: 企业内部自签名证书环境必需
    if opts.get('ignore_certificate_errors', True):
        args.append('--ignore-certificate-errors')

    # --disable-extensions: 禁用浏览器扩展
    # 作用: 避免扩展注入 JS 干扰页面行为
    if opts.get('disable_extensions', True):
        args.append('--disable-extensions')

    # --disable-infobars: 禁用 "Chrome 正受到自动测试软件的控制" 横幅
    # 作用: 防止 infobar 遮挡页面元素导致 ElementClickIntercepted
    if opts.get('disable_infobars', True):
        args.append('--disable-infobars')

    # --incognito: 隐私模式
    # 作用: 隔离 Cookie / Storage，避免测试间数据污染
    if opts.get('incognito', False):
        args.append('--incognito')

    # --no-sandbox: 禁用沙箱
    # 作用: Headless 模式下沙箱常导致启动失败，Docker/CI 环境必须开启
    if headless or not opts.get('sandbox', True):
        args.append('--no-sandbox')

    # ================================================================
    # 第二类: DNS / 网络栈优化
    # ================================================================

    # --disable-features=DnsOverHttpsUpgrade
    # 作用: 禁止浏览器将 DNS 查询升级为 DoH（DNS-over-HTTPS）。
    #       境外 DoH 服务器（如 Cloudflare/Google）在国内可能解析超时，
    #       回退到系统 DNS 后大幅降低 DNS 解析延迟。
    args.append('--disable-features=DnsOverHttpsUpgrade')

    # --dns-prefetch-disable
    # 作用: 禁用 DNS 预解析。减少不必要的 DNS 查询，
    #       在跨境弱网环境下减少 TCP 连接竞争。
    args.append('--dns-prefetch-disable')

    # --disable-background-networking
    # 作用: 禁用后台网络任务（组件更新/扩展同步/安全浏览更新等），
    #       减少非测试相关的网络请求，降低页面加载时的带宽竞争。
    args.append('--disable-background-networking')

    # --disable-sync
    # 作用: 禁用 Chrome Sync（书签/密码同步），
    #       减少后台 HTTP 请求和 WebSocket 连接开销。
    args.append('--disable-sync')

    # --disable-default-apps
    # 作用: 禁止 Chrome 预装默认应用（如 Gmail/Docs 等），
    #       减少启动时扩展和后台页面初始化。
    args.append('--disable-default-apps')

    # --disable-dev-shm-usage
    # 作用: 不使用 /dev/shm 共享内存（Docker 默认 /dev/shm 仅 64MB），
    #       改为使用 /tmp。在 Windows 上无副作用，在 Linux 上防止 OOM 崩溃。
    args.append('--disable-dev-shm-usage')

    # ================================================================
    # 第三类: 窗口 / 调试端口
    # ================================================================

    rdp = opts.get('remote_debugging_port', 0)
    if rdp > 0:
        args.append(f'--remote-debugging-port={rdp}')

    return args


# ==================================================================
# Prefs 构建（图片拦截）
# ==================================================================


def _build_prefs(enable_images: bool) -> dict:
    """构建 Chrome/Edge Preferences 字典。

    Args:
        enable_images: ``True`` 允许图片加载；``False`` 拦截图片。

    Returns:
        Chrome Preferences 字典，用于 ``add_experimental_option('prefs', ...)``。
    """
    if enable_images:
        return {}

    return {
        # profile.managed_default_content_settings.images: 2 = 禁止
        # 参考: https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/content_settings/core/common/content_settings.h
        'profile.managed_default_content_settings.images': 2,
    }


# ==================================================================
# 代理构建
# ==================================================================


def _apply_proxy_settings(
    options: ChromeOptions | EdgeOptions,
    cfg: Settings,
) -> None:
    """将 YAML 代理配置应用到浏览器 Options。

    支持 HTTP/HTTPS 代理和绕过列表。

    Args:
        options: ChromeOptions 或 EdgeOptions 实例。
        cfg: Settings 单例。
    """
    if not cfg.proxy_enabled:
        return

    proxy_args: list[str] = []

    # HTTP 代理
    http_proxy = cfg.proxy_http
    if http_proxy:
        proxy_args.append(f'--proxy-server={http_proxy}')
        logger.info('已配置 HTTP 代理: %s', http_proxy)

    # HTTPS 代理（独立于 HTTP 代理时使用）
    https_proxy = cfg.proxy_https
    if https_proxy and https_proxy != http_proxy:
        # 如果 HTTPS 和 HTTP 代理不同，使用 --proxy-server 指定 HTTPS 代理
        # 否则上面已经设置
        if not http_proxy:
            proxy_args.append(f'--proxy-server={https_proxy}')
            logger.info('已配置 HTTPS 代理: %s', https_proxy)

    # 绕过列表
    bypass = cfg.proxy_bypass
    if bypass:
        proxy_args.append(f'--proxy-bypass-list={bypass}')
        logger.info('代理绕过列表: %s', bypass)

    for arg in proxy_args:
        options.add_argument(arg)


# ==================================================================
# 通用能力注入
# ==================================================================


def _inject_common_caps(
    driver: webdriver.Remote,
    cfg: Settings,
    headless: bool,
) -> None:
    """注入超时、等待、窗口等通用能力。

    硬性超时兜底策略:
        - page_load: 取 cfg 值与 15s 中较小值（eager 策略下 DOM < 5s）
        - script: 取 cfg 值与 10s 中较小值（防止 JS 死循环）

    Args:
        driver: 已创建的 WebDriver 实例。
        cfg: Settings 单例。
        headless: 是否无头模式。
    """
    # 隐式等待
    driver.implicitly_wait(cfg.implicit_wait)

    # 页面加载超时 — 从 YAML 读取，跨境场景建议 30s
    page_timeout = cfg.page_load_timeout
    driver.set_page_load_timeout(page_timeout)

    # 脚本执行超时 — 从 YAML 读取，建议 10s 防止 JS 死循环
    script_timeout = cfg.script_timeout
    driver.set_script_timeout(script_timeout)

    # 窗口最大化（非 headless 模式）
    if cfg.options.get('window_maximize', True) and not headless:
        driver.maximize_window()

    logger.info(
        'WebDriver 初始化完成 | browser=%s | headless=%s | '
        'implicit_wait=%ss | page_timeout=%ss | script_timeout=%ss',
        cfg.browser_type,
        headless,
        cfg.implicit_wait,
        page_timeout,
        script_timeout,
    )


# ==================================================================
# Core Factory — Chrome
# ==================================================================


def _create_chrome(
    headless: bool,
    driver_path: Optional[Path],
    cfg: Settings,
    enable_images: bool,
) -> webdriver.Chrome:
    """创建 Chrome WebDriver（企业级配置）。

    Args:
        headless: 无头模式开关。
        driver_path: chromedriver 路径或 None。
        cfg: Settings 单例。
        enable_images: 是否启用图片加载。

    Returns:
        配置完成的 Chrome WebDriver。

    Raises:
        DriverInitializationError: 驱动初始化失败。
    """
    options = ChromeOptions()

    # ---- 1. 通用启动参数 ----
    for arg in _build_common_arguments(cfg, headless):
        options.add_argument(arg)

    # ---- 2. Headless 特有参数 ----
    if headless:
        options.add_argument('--headless=new')
        options.add_argument('--window-size=1920,1080')

    # ---- 3. DevTools 日志抑制 ----
    options.add_experimental_option('excludeSwitches', ['enable-logging'])

    # ---- 4. 页面加载策略: eager ----
    options.page_load_strategy = 'eager'

    # ---- 5. 图片加载 Prefs ----
    prefs = _build_prefs(enable_images)
    if prefs:
        options.add_experimental_option('prefs', prefs)
        logger.info('图片加载已禁用（极速模式）')
    else:
        logger.info('图片加载已启用（UI 视觉模式）')

    # ---- 6. 干净 User Data Dir（避免缓存污染）----
    user_data_dir = tempfile.mkdtemp(prefix='swag_labs_chrome_')
    options.add_argument(f'--user-data-dir={user_data_dir}')
    logger.debug('临时 User Data Dir: %s', user_data_dir)

    # ---- 7. 企业代理 ----
    _apply_proxy_settings(options, cfg)

    # ---- 8. 创建 Service & Driver ----
    service_kwargs = {}
    if driver_path and driver_path.exists():
        service_kwargs['executable_path'] = str(driver_path)
    service = ChromeService(**service_kwargs)

    driver = webdriver.Chrome(service=service, options=options)
    _inject_common_caps(driver, cfg, headless)
    return driver


# ==================================================================
# Core Factory — Edge
# ==================================================================


def _create_edge(
    headless: bool,
    driver_path: Optional[Path],
    cfg: Settings,
    enable_images: bool,
) -> webdriver.Edge:
    """创建 Edge WebDriver（企业级配置）。

    Edge 基于 Chromium，大部分参数与 Chrome 通用，
    差异仅在于 Service 和 Options 类型。

    Args:
        headless: 无头模式开关。
        driver_path: edgedriver 路径或 None。
        cfg: Settings 单例。
        enable_images: 是否启用图片加载。

    Returns:
        配置完成的 Edge WebDriver。

    Raises:
        DriverInitializationError: 驱动初始化失败。
    """
    options = EdgeOptions()

    # ---- 1. 通用启动参数 ----
    for arg in _build_common_arguments(cfg, headless):
        options.add_argument(arg)

    # ---- 2. Headless 特有参数 ----
    if headless:
        options.add_argument('--headless=new')
        options.add_argument('--window-size=1920,1080')

    # ---- 3. DevTools 日志抑制 ----
    options.add_experimental_option('excludeSwitches', ['enable-logging'])

    # ---- 4. 页面加载策略: eager ----
    options.page_load_strategy = 'eager'

    # ---- 5. 图片加载 Prefs ----
    prefs = _build_prefs(enable_images)
    if prefs:
        options.add_experimental_option('prefs', prefs)
        logger.info('图片加载已禁用（极速模式）')
    else:
        logger.info('图片加载已启用（UI 视觉模式）')

    # ---- 6. 干净 User Data Dir（避免缓存污染）----
    user_data_dir = tempfile.mkdtemp(prefix='swag_labs_edge_')
    options.add_argument(f'--user-data-dir={user_data_dir}')
    logger.debug('临时 User Data Dir: %s', user_data_dir)

    # ---- 7. 企业代理 ----
    _apply_proxy_settings(options, cfg)

    # ---- 8. 创建 Service & Driver ----
    service_kwargs = {}
    if driver_path and driver_path.exists():
        service_kwargs['executable_path'] = str(driver_path)
    service = EdgeService(**service_kwargs)

    driver = webdriver.Edge(service=service, options=options)
    _inject_common_caps(driver, cfg, headless)
    return driver
