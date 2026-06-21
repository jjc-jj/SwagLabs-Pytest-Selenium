# File: testcases/conftest.py
"""Pytest 全局 Fixtures & Hooks — WebDriver 生命周期 + 失败自动截图。

Fixture 清单:
    - ``settings`` (session) — 配置单例 + 日志初始化
    - ``driver`` (function) — 每个用例独立 WebDriver，yield 优雅销毁
    - ``test_logger`` (function) — 每用例专属 logger

Hook 清单:
    - ``pytest_runtest_makereport`` — 测试失败时自动截图并附加到 Allure 报告

防御性设计:
    - driver teardown 使用 try/finally + 内层 try/except，
      确保 quit() 异常不会覆盖原始测试异常
    - Hook 中每个 Allure 附件独立 try/except，互不干扰
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Generator

import allure
import pytest
from selenium.common.exceptions import WebDriverException

# 将 automation/ 加入 sys.path
_automation_root = Path(__file__).resolve().parent.parent
if str(_automation_root) not in sys.path:
    sys.path.insert(0, str(_automation_root))

from utils.driver_factory import create_driver  # noqa: E402
from utils.logger_util import get_logger, init_logging  # noqa: E402
from utils.settings import Settings  # noqa: E402

logger = get_logger(__name__)


# ==================================================================
# Session‑level fixtures
# ==================================================================


@pytest.fixture(scope='session')
def settings() -> Settings:
    """Session 级 Settings 单例。

    整个测试会话共享一份配置，首次加载后常驻内存。
    日志系统也在此初始化（全局一次）。

    Returns:
        Settings 单例实例。
    """
    cfg = Settings()
    log_dir = _automation_root / cfg.log_file_dir
    init_logging(
        log_dir=log_dir,
        level=cfg.log_level,
        fmt=cfg.log_format,
        datefmt=cfg.log_date_format,
        when=cfg.log_when,
        interval=cfg.log_interval,
        backup_count=cfg.log_backup_count,
        console_output=cfg.log_console_output,
    )
    logger.info(
        '\n%s\n'
        '  Swag Labs 自动化测试启动\n'
        '  Base URL : %s\n'
        '  Browser  : %s\n'
        '  Headless : %s\n'
        '%s',
        '=' * 60, cfg.base_url, cfg.browser_type, cfg.browser_headless,
        '=' * 60,
    )
    return cfg


# ==================================================================
# Function‑level fixtures
# ==================================================================


@pytest.fixture(scope='function')
def driver(settings: Settings) -> Generator:
    """Function 级 WebDriver fixture。

    每个测试用例获得独立的浏览器实例，确保用例间完全隔离。

    **防御性 teardown**: yield 后的清理代码使用双层 try 结构：
        - 外层 ``try/finally`` 确保 quit() 一定执行
        - 内层 ``try/except`` 防止 quit() 自身的异常覆盖原始测试失败信息

    Args:
        settings: session 级 Settings fixture。

    Yields:
        配置完成的 WebDriver 实例。
    """
    logger.info('--- 创建 WebDriver (function scope) ---')
    _driver = create_driver(settings=settings)
    try:
        yield _driver
    finally:
        logger.info('--- 销毁 WebDriver ---')
        try:
            _driver.quit()
        except WebDriverException as exc:
            logger.warning(
                'driver.quit() 异常（浏览器可能已崩溃）: %s', exc
            )
        except Exception as exc:
            logger.error(
                'driver.quit() 未预期的异常: %s', exc
            )


@pytest.fixture(scope='function')
def test_logger(request: pytest.FixtureRequest) -> logging.Logger:
    """为每个测试函数返回专属 logger。

    Args:
        request: Pytest fixture request 对象。

    Returns:
        以 ``test.<函数名>`` 命名的 Logger。
    """
    return get_logger(f'test.{request.node.name}')


# ==================================================================
# Pytest Hooks — 失败自动截图 & Allure 集成
# ==================================================================


def _safe_nodeid_to_filename(nodeid: str) -> str:
    """将 pytest nodeid 转为安全的文件名片段。

    跨平台处理 ``/``、``\\``、``::`` 等分隔符。

    Args:
        nodeid: pytest 节点 ID，如 ``testcases/test_login.py::test_xxx``。

    Returns:
        文件名安全字符串。
    """
    return (
        nodeid.replace('\\', '_')
        .replace('/', '_')
        .replace('::', '_')
    )


def _is_driver_alive(driver_instance) -> bool:
    """检查 WebDriver 实例是否仍可用。

    Args:
        driver_instance: WebDriver 实例。

    Returns:
        ``True`` 如果 driver 仍然可用（有 session_id）。
    """
    try:
        return (
            driver_instance is not None
            and getattr(driver_instance, 'session_id', None) is not None
        )
    except Exception:
        return False


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
    call: pytest.CallInfo,
) -> Generator:
    """测试失败时自动截图并附加到 Allure 报告。

    仅捕获 ``call`` 阶段（测试函数执行）的失败，
    setup/teardown 失败不截图（此时 driver 可能不可用）。

    **防御性设计**:
        - 每个 Allure 附件独立 try/except，一个附件失败不影响另一个
        - 截图前检查 driver 是否仍存活（session_id 非空）
        - 附件失败仅日志记录，绝不抛异常干扰 Pytest 框架

    Args:
        item: 当前测试项。
        call: 当前执行阶段信息。
    """
    outcome = yield
    report = outcome.get_result()

    # 仅处理测试函数执行阶段的失败
    if report.when != 'call' or not report.failed:
        return

    # 从 fixture 中获取 driver
    driver_instance = item.funcargs.get('driver')
    if not _is_driver_alive(driver_instance):
        logger.warning(
            'driver 不可用（已崩溃或不存在），跳过失败截图'
        )
        return

    # 生成截图路径
    test_name = _safe_nodeid_to_filename(item.nodeid)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    screenshot_dir = _automation_root / 'reports' / 'screenshots'
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = (
        screenshot_dir / f'FAIL_{test_name}_{timestamp}.png'
    )

    # ---- 附件 1: 截图 PNG ----
    try:
        driver_instance.save_screenshot(str(screenshot_path))
        logger.info('失败截图已保存: %s', screenshot_path)

        allure.attach(
            driver_instance.get_screenshot_as_png(),
            name=f'失败截图: {item.name}',
            attachment_type=allure.attachment_type.PNG,
        )
    except Exception as exc:
        logger.error('截图附件失败: %s', exc)

    # ---- 附件 2: 页面源码 HTML（独立 try，互不干扰）----
    try:
        page_source = driver_instance.page_source
        if page_source:
            allure.attach(
                page_source,
                name=f'页面源码: {item.name}',
                attachment_type=allure.attachment_type.HTML,
            )
    except Exception as exc:
        logger.error('页面源码附件失败: %s', exc)


# ==================================================================
# 自动修复 pytest-html 报告
# ==================================================================


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config: pytest.Config) -> None:
    """测试会话结束后自动修复 HTML 报告。

    修复 ``history.pushState`` SecurityError（file:// 协议下
    JS 初始化崩溃导致表格空白）。修复后的报告可双击直接打开。
    """
    # 仅当生成了 HTML 报告时才修复
    html_path = config.getoption('htmlpath', default=None)
    if not html_path:
        return

    report_file = _automation_root / html_path
    if not report_file.exists():
        return

    try:
        content = report_file.read_text(encoding='utf-8')
        old = 'window.history.pushState({}, null, unescape(url.href))'
        new = 'try{window.history.pushState({}, null, unescape(url.href))}catch(e){}'

        if 'try{window.history.pushState(' in content:
            return  # already patched

        if old in content:
            content = content.replace(old, new)
            report_file.write_text(content, encoding='utf-8')
            logger.info('HTML 报告已自动修复 (pushState → try/catch)')
    except Exception as exc:
        logger.warning('HTML 报告自动修复失败: %s', exc)
