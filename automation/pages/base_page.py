# File: pages/base_page.py
"""页面对象基类 — 所有 Page Object 的抽象父类。

提供智能等待、JS 降级点击、日志追踪等通用能力。
所有 Page 类必须继承此基类，禁止在 Page 类中直接调用
``driver.find_element`` 等裸 Selenium API。

Key Features:
    - 绝对禁止 ``time.sleep()``，全部使用 ``WebDriverWait`` + ``expected_conditions``
    - ``click()`` 自动捕获 ``ElementClickInterceptedException``
      并降级为 JavaScript 强制执行
    - 核心操作（click / type / find）自动记录 INFO 日志

Usage::

    from pages.base_page import BasePage

    class LoginPage(BasePage):
        USERNAME_INPUT = (By.ID, 'user-name')
        ...
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional, Tuple

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils.logger_util import get_logger

# ------------------------------------------------------------------
# 类型别名
# ------------------------------------------------------------------

Locator = Tuple[str, str]
"""元素定位器：``(By.XXX, 'value')`` 二元组。"""

logger = get_logger(__name__)


# ==================================================================
# BasePage
# ==================================================================

class BasePage:
    """页面对象抽象基类。

    封装 Selenium 4 常用操作，提供：
        - 显式等待查找（可见 / 可点击 / 存在）
        - 安全点击（自动 JS 降级）
        - 文本输入（自动清空 + 键入）
        - 页面导航、截图、JS 执行、滚动

    Attributes:
        driver: WebDriver 实例。
        timeout: 默认显式等待超时秒数。
        base_url: 被测系统根 URL。
    """

    def __init__(
        self,
        driver: WebDriver,
        timeout: int = 15,
        base_url: str = '',
    ) -> None:
        """初始化基类。

        Args:
            driver: WebDriver 实例（由 conftest fixture 注入）。
            timeout: 默认显式等待超时（秒）。
            base_url: 基础 URL，用于 ``open()`` 路径拼接。
        """
        self.driver: WebDriver = driver
        self.timeout: int = timeout
        self.base_url: str = base_url

    # ==================================================================
    # 页面导航
    # ==================================================================

    def open(self, path: str = '') -> None:
        """打开指定页面路径。

        Args:
            path: 相对路径（如 ``/inventory.html``），留空打开首页。
        """
        url = self.base_url.rstrip('/') + '/' + path.lstrip('/')
        logger.info('🌐 打开页面: %s', url)
        self.driver.get(url)

    def refresh(self) -> None:
        """刷新当前页面。"""
        logger.info('🔄 刷新页面')
        self.driver.refresh()

    def back(self) -> None:
        """浏览器后退。"""
        logger.info('⬅ 浏览器后退')
        self.driver.back()

    # ==================================================================
    # 元素查找 — 全部基于 WebDriverWait，零 time.sleep
    # ==================================================================

    def find_element(
        self,
        locator: Locator,
        timeout: Optional[int] = None,
    ) -> WebElement:
        """显式等待元素**可见**后返回。

        Args:
            locator: ``(By.XXX, 'value')`` 定位器。
            timeout: 超时秒数，默认使用实例 ``self.timeout``。

        Returns:
            可见的 WebElement。

        Raises:
            TimeoutException: 超时未找到。
        """
        wait = self._wait(timeout)
        logger.debug('查找元素: %s', locator)
        return wait.until(EC.visibility_of_element_located(locator))

    def find_elements(
        self,
        locator: Locator,
        timeout: Optional[int] = None,
    ) -> List[WebElement]:
        """显式等待**至少一个**元素出现，返回全部匹配列表。

        Args:
            locator: 定位器。
            timeout: 超时秒数。

        Returns:
            WebElement 列表（可能为空列表，不会抛异常）。
        """
        wait = self._wait(timeout)
        try:
            wait.until(EC.presence_of_element_located(locator))
        except TimeoutException:
            return []
        return self.driver.find_elements(*locator)

    def find_element_clickable(
        self,
        locator: Locator,
        timeout: Optional[int] = None,
    ) -> WebElement:
        """显式等待元素**可点击**后返回。

        Args:
            locator: 定位器。
            timeout: 超时秒数。

        Returns:
            可点击的 WebElement。

        Raises:
            TimeoutException: 超时未变得可点击。
        """
        wait = self._wait(timeout)
        logger.debug('等待可点击: %s', locator)
        return wait.until(EC.element_to_be_clickable(locator))

    def is_displayed(
        self,
        locator: Locator,
        timeout: int = 3,
    ) -> bool:
        """检查元素是否可见（不会抛异常）。

        Args:
            locator: 定位器。
            timeout: 最长等待秒数，默认 3。

        Returns:
            ``True`` 如果元素可见。
        """
        try:
            self.find_element(locator, timeout)
            return True
        except (TimeoutException, NoSuchElementException):
            return False

    def is_present(
        self,
        locator: Locator,
        timeout: int = 3,
    ) -> bool:
        """检查元素是否存在于 DOM（不要求可见）。

        Args:
            locator: 定位器。
            timeout: 最长等待秒数。

        Returns:
            ``True`` 如果元素存在于 DOM。
        """
        try:
            wait = self._wait(timeout)
            wait.until(EC.presence_of_element_located(locator))
            return True
        except TimeoutException:
            return False

    def get_element_count(self, locator: Locator) -> int:
        """返回匹配元素的数量。

        Args:
            locator: 定位器。

        Returns:
            匹配元素个数（0 表示无匹配）。
        """
        return len(self.driver.find_elements(*locator))

    # ==================================================================
    # 元素操作
    # ==================================================================

    def click(
        self,
        locator: Locator,
        timeout: Optional[int] = None,
    ) -> None:
        """安全点击 — 自动 JS 降级。

        优先使用原生 Selenium ``click()``；
        如果抛出 ``ElementClickInterceptedException``
        （元素被遮挡/不可点击），自动降级为 JavaScript 强制点击。

        Args:
            locator: 定位器。
            timeout: 超时秒数。

        Raises:
            TimeoutException: 超时未找到可点击元素（且 JS 降级也失败时）。
        """
        try:
            el = self.find_element_clickable(locator, timeout)
            logger.info('🖱 点击元素: %s', locator)
            el.click()
        except ElementClickInterceptedException:
            logger.warning(
                '⚠ 点击被拦截，降级为 JS 强制执行: %s', locator
            )
            el = self.find_element(locator, timeout)
            self.driver.execute_script('arguments[0].click();', el)
            logger.info('🖱 JS 点击成功: %s', locator)

    def type(
        self,
        locator: Locator,
        text: str,
        clear_first: bool = True,
        timeout: Optional[int] = None,
    ) -> None:
        """在输入框中键入文本。

        Args:
            locator: 定位器。
            text: 要输入的文本。
            clear_first: 是否先清空已有内容，默认 ``True``。
            timeout: 超时秒数。
        """
        el = self.find_element_clickable(locator, timeout)
        if clear_first:
            el.clear()
        el.send_keys(text)
        logger.info('⌨ 输入文本: %s → «%s»', locator, text)

    def get_text(
        self,
        locator: Locator,
        timeout: Optional[int] = None,
    ) -> str:
        """获取元素可见文本。

        Args:
            locator: 定位器。
            timeout: 超时秒数。

        Returns:
            元素 ``.text`` 内容。
        """
        el = self.find_element(locator, timeout)
        text = el.text
        logger.debug('获取文本: %s → «%s»', locator, text)
        return text

    def get_attribute(
        self,
        locator: Locator,
        attribute: str,
        timeout: Optional[int] = None,
    ) -> Optional[str]:
        """获取元素属性值。

        Args:
            locator: 定位器。
            attribute: 属性名（如 ``'value'``、``'class'``、``'data-test'``）。
            timeout: 超时秒数。

        Returns:
            属性值字符串，不存在返回 ``None``。
        """
        el = self.find_element(locator, timeout)
        return el.get_attribute(attribute)

    def scroll_into_view(
        self,
        locator: Locator,
        timeout: Optional[int] = None,
    ) -> None:
        """将元素滚动到可视区域。

        Args:
            locator: 定位器。
            timeout: 超时秒数。
        """
        el = self.find_element(locator, timeout)
        self.driver.execute_script(
            'arguments[0].scrollIntoView({behavior: "smooth", block: "center"});',
            el,
        )
        logger.debug('滚动到元素: %s', locator)

    # ==================================================================
    # 等待条件
    # ==================================================================

    def wait_for_url_contains(
        self,
        substring: str,
        timeout: Optional[int] = None,
    ) -> bool:
        """等待 URL 包含指定字符串。

        Args:
            substring: URL 中期望出现的文本。
            timeout: 超时秒数。

        Returns:
            ``True`` 如果 URL 包含子串。
        """
        try:
            wait = self._wait(timeout)
            wait.until(EC.url_contains(substring))
            logger.info('✅ URL 匹配: «%s»', substring)
            return True
        except TimeoutException:
            logger.warning('⏰ URL 未匹配: 期望包含 «%s», 实际 «%s»',
                           substring, self.current_url)
            return False

    def wait_for_title_contains(
        self,
        substring: str,
        timeout: Optional[int] = None,
    ) -> bool:
        """等待页面标题包含指定字符串。

        Args:
            substring: 标题中期望出现的文本。
            timeout: 超时秒数。

        Returns:
            ``True`` 如果标题包含子串。
        """
        try:
            wait = self._wait(timeout)
            wait.until(EC.title_contains(substring))
            logger.info('✅ 标题匹配: «%s»', substring)
            return True
        except TimeoutException:
            logger.warning('⏰ 标题未匹配: 期望包含 «%s», 实际 «%s»',
                           substring, self.title)
            return False

    def wait_until_invisible(
        self,
        locator: Locator,
        timeout: Optional[int] = None,
    ) -> bool:
        """等待元素不可见。

        Args:
            locator: 定位器。
            timeout: 超时秒数。

        Returns:
            ``True`` 如果元素消失。
        """
        try:
            wait = self._wait(timeout)
            wait.until(EC.invisibility_of_element_located(locator))
            logger.debug('元素已不可见: %s', locator)
            return True
        except TimeoutException:
            return False

    # ==================================================================
    # 页面状态
    # ==================================================================

    @property
    def title(self) -> str:
        """当前页面标题。"""
        return self.driver.title

    @property
    def current_url(self) -> str:
        """当前页面完整 URL。"""
        return self.driver.current_url

    @property
    def page_source(self) -> str:
        """当前页面 HTML 源码。"""
        return self.driver.page_source

    # ==================================================================
    # 截图
    # ==================================================================

    def screenshot(self, filepath: str) -> str:
        """截取当前页面并保存为 PNG。

        Args:
            filepath: 保存路径（含 ``.png`` 文件名）。

        Returns:
            实际保存的绝对路径。
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.driver.save_screenshot(str(path))
        logger.info('📸 截图已保存: %s', path)
        return str(path.resolve())

    # ==================================================================
    # JavaScript
    # ==================================================================

    def execute_script(self, script: str, *args: Any) -> Any:
        """执行同步 JavaScript 脚本。

        Args:
            script: JS 代码字符串。
            *args: 传递给 JS 的参数（会被序列化为 ``arguments[0]...N``）。

        Returns:
            JS 执行返回值（可能为 DOM 元素 / 字符串 / 布尔值等）。
        """
        return self.driver.execute_script(script, *args)

    # ==================================================================
    # 内部工具
    # ==================================================================

    def _wait(self, timeout: Optional[int]) -> WebDriverWait:
        """构造 WebDriverWait 实例。

        Args:
            timeout: 超时秒数，None 则使用默认。

        Returns:
            WebDriverWait 实例。
        """
        return WebDriverWait(self.driver, timeout or self.timeout)
