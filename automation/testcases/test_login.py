# File: testcases/test_login.py
"""登录模块冒烟测试 — ATC-01。

测试标准用户登录流程，验证成功登录后跳转到商品列表页。

POM 铁律: 本文件禁止出现 ``driver.find_element`` 等裸 Selenium API，
         所有操作必须通过 Page Object 封装方法完成。
"""

from __future__ import annotations

import allure
import pytest

from pages.login_page import LoginPage
from pages.inventory_page import InventoryPage
from utils.data_loader import load_json


@allure.feature('登录模块')
@allure.story('标准用户登录')
@allure.title('ATC-01: 标准用户登录成功验证')
@allure.description(
    '验证 standard_user 凭据登录后'
    '成功跳转到 /inventory.html 商品列表页。'
)
@allure.severity(allure.severity_level.BLOCKER)
def test_standard_user_login_success(driver, settings) -> None:
    """ATC-01 — 标准用户登录成功。

    步骤:
        1. 打开登录页
        2. 输入 standard_user 凭据
        3. 点击登录按钮
        4. 验证跳转到商品列表页

    Args:
        driver: function 级 WebDriver fixture。
        settings: session 级 Settings fixture。
    """
    account = settings.get_account('standard_user')
    login_page = LoginPage(
        driver, timeout=settings.explicit_wait, base_url=settings.base_url,
    )

    # ---- Step 1: 打开登录页 ----
    with allure.step('Step 1: 打开登录页面'):
        login_page.open()
        assert login_page.is_login_page_displayed(), (
            '登录页未正常加载，登录按钮不可见'
        )

    # ---- Step 2: 输入凭据并登录 ----
    with allure.step(
        f'Step 2: 输入用户名 [{account["username"]}] 并登录'
    ):
        login_page.do_login(account['username'], account['password'])

    # ---- Step 3: 验证跳转 ----
    with allure.step('Step 3: 验证登录成功 — 跳转到商品列表页'):
        inventory_page = InventoryPage(
            driver,
            timeout=settings.explicit_wait,
            base_url=settings.base_url,
        )
        assert inventory_page.is_inventory_page_displayed(), (
            '登录失败: 商品列表容器不可见，未成功跳转到 /inventory.html'
        )

    # ---- Step 4: 验证页面标题 ----
    with allure.step('Step 4: 验证页面标题为 Products'):
        actual_title = inventory_page.get_page_title()
        expected_title = 'Products'
        assert actual_title == expected_title, (
            f'页面标题不符，预期 "{expected_title}"，实际 "{actual_title}"'
        )


# ==================================================================
# ATC-05 — 异常登录数据驱动（参数化）
# ==================================================================

# 在模块加载时读取 JSON（pytest 参数化需要 collection 阶段可用）
_login_failure_cases: list[dict] = load_json('data/login_data.json')


@allure.feature('登录模块')
@allure.story('异常登录场景')
@allure.title('ATC-05: 异常登录数据驱动验证 — {test_case[test_id]}')
@allure.description('参数化验证多组异常凭据的登录失败错误消息')
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize(
    'test_case',
    _login_failure_cases,
    ids=lambda case: case['test_id'],
)
def test_login_failure_scenarios(
    driver,
    settings,
    test_case: dict,
) -> None:
    """ATC-05 — 异常登录数据驱动。

    从 ``data/login_data.json`` 读取多组异常凭据，
    逐条验证登录失败时的错误消息是否符合预期。

    覆盖场景:
        - 锁定用户 (locked_out_user)
        - 空用户名
        - 空密码
        - 错误密码

    Args:
        driver: function 级 WebDriver fixture。
        settings: session 级 Settings fixture。
        test_case: parametrize 注入的单条测试数据。
    """
    login_page = LoginPage(
        driver, timeout=settings.explicit_wait, base_url=settings.base_url,
    )

    # ---- Step 1: 打开登录页 ----
    with allure.step('打开登录页面'):
        login_page.open()

    # ---- Step 2: 使用异常凭据登录 ----
    with allure.step(
        f'输入异常凭据: username=«{test_case["username"]}», '
        f'password=«{test_case["password"]}»'
    ):
        login_page.do_login(
            test_case['username'], test_case['password'],
        )

    # ---- Step 3: 验证错误消息 ----
    with allure.step(
        f'验证错误消息包含: «{test_case["expected_error"]}»'
    ):
        assert login_page.is_error_displayed(), (
            f'预期应显示错误消息，但错误消息不可见 | '
            f'case={test_case["test_id"]}'
        )
        actual_error = login_page.get_error_message()
        assert test_case['expected_error'] in actual_error, (
            f'错误消息不匹配 | case={test_case["test_id"]} | '
            f'预期包含: «{test_case["expected_error"]}» | '
            f'实际: «{actual_error}»'
        )

    allure.dynamic.parameter('test_id', test_case['test_id'])
    allure.dynamic.parameter('expected_error', test_case['expected_error'])
