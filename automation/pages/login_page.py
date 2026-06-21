# File: pages/login_page.py
"""登录页 Page Object — Sauce Demo 登录表单。

URL: ``/`` （首页即登录页）

元素定位：
    - 用户名输入框：``#user-name``
    - 密码输入框：``#password``
    - 登录按钮：``#login-button``
    - 错误消息：``h3[data-test="error"]``

Usage::

    from pages.login_page import LoginPage

    login_page = LoginPage(driver, base_url=cfg.base_url)
    login_page.open()
    login_page.do_login('standard_user', 'secret_sauce')
"""

from __future__ import annotations

from typing import Optional

from selenium.webdriver.common.by import By

from pages.base_page import BasePage


class LoginPage(BasePage):
    """Sauce Demo 登录页面对象。

    所有元素定位器定义为类属性元组，操作方法仅包含业务行为，
    不包含任何断言逻辑。
    """

    # ==================================================================
    # 元素定位器
    # ==================================================================

    USERNAME_INPUT = (By.ID, 'user-name')
    """用户名输入框"""

    PASSWORD_INPUT = (By.ID, 'password')
    """密码输入框"""

    LOGIN_BUTTON = (By.ID, 'login-button')
    """登录按钮"""

    ERROR_MESSAGE = (By.CSS_SELECTOR, 'h3[data-test="error"]')
    """登录失败错误消息"""

    ERROR_CLOSE_BTN = (By.CSS_SELECTOR, '.error-button')
    """错误消息关闭按钮"""

    # 页面底部
    LOGIN_LOGO = (By.CLASS_NAME, 'login_logo')
    """Swag Labs logo"""

    BOT_IMAGE = (By.CLASS_NAME, 'bot_column')
    """登录页机器人插图"""

    # ==================================================================
    # 业务操作方法
    # ==================================================================

    def do_login(
        self,
        username: str,
        password: str,
    ) -> None:
        """执行登录操作。

        输入用户名 → 输入密码 → 点击登录按钮。
        登录成功后将自动跳转到 ``/inventory.html``。

        Args:
            username: 用户名。
            password: 密码。
        """
        self.type(self.USERNAME_INPUT, username)
        self.type(self.PASSWORD_INPUT, password)
        self.click(self.LOGIN_BUTTON)

    def get_error_message(self) -> str:
        """获取登录失败时的错误提示文本。

        Returns:
            错误消息文本；如果未显示错误则返回空字符串。
        """
        if self.is_displayed(self.ERROR_MESSAGE, timeout=2):
            return self.get_text(self.ERROR_MESSAGE)
        return ''

    def is_error_displayed(self) -> bool:
        """检查是否显示了登录错误消息。

        Returns:
            ``True`` 如果错误消息可见。
        """
        return self.is_displayed(self.ERROR_MESSAGE, timeout=2)

    def dismiss_error(self) -> None:
        """关闭错误提示弹框。"""
        if self.is_displayed(self.ERROR_CLOSE_BTN, timeout=2):
            self.click(self.ERROR_CLOSE_BTN)

    def is_login_page_displayed(self) -> bool:
        """验证当前是否为登录页。

        Returns:
            ``True`` 如果登录按钮可见。
        """
        return self.is_displayed(self.LOGIN_BUTTON, timeout=3)

    # ==================================================================
    # 便捷方法 — 预定义账号快速登录
    # ==================================================================

    def login_as_standard_user(self) -> None:
        """使用 standard_user 快速登录。"""
        self.do_login('standard_user', 'secret_sauce')

    def login_as_locked_out_user(self) -> None:
        """使用 locked_out_user 登录（预期失败）。"""
        self.do_login('locked_out_user', 'secret_sauce')

    def login_as_problem_user(self) -> None:
        """使用 problem_user 登录。"""
        self.do_login('problem_user', 'secret_sauce')

    def login_as_performance_glitch_user(self) -> None:
        """使用 performance_glitch_user 登录。"""
        self.do_login('performance_glitch_user', 'secret_sauce')
