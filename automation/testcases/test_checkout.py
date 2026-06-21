# File: testcases/test_checkout.py
"""购物车 & 结账流程冒烟测试 — ATC-03 / ATC-04。

ATC-03: 多商品加购与购物车 Badge 数字同步验证。
ATC-04: 完整结账流程（Inventory → Cart → Checkout → Complete）。

POM 铁律: 本文件禁止出现 ``driver.find_element`` 等裸 Selenium API。
"""

from __future__ import annotations

import allure
from selenium.webdriver.remote.webdriver import WebDriver

from pages.login_page import LoginPage
from pages.inventory_page import InventoryPage
from pages.cart_page import CartPage
from pages.checkout_page import CheckoutPage
from utils.settings import Settings


# ------------------------------------------------------------------
# 辅助函数 — 预登录（减少重复代码）
# ------------------------------------------------------------------

def _perform_login(
    driver: WebDriver,
    settings: Settings,
    account_key: str = 'standard_user',
) -> InventoryPage:
    """执行登录并返回 InventoryPage 实例。

    Args:
        driver: WebDriver fixture 实例。
        settings: Settings fixture 实例。
        account_key: 账号键名，默认 ``'standard_user'``。

    Returns:
        已登录的 InventoryPage 实例。
    """
    account = settings.get_account(account_key)
    login_page = LoginPage(
        driver, timeout=settings.explicit_wait, base_url=settings.base_url,
    )
    login_page.open()
    login_page.do_login(account['username'], account['password'])
    return InventoryPage(
        driver, timeout=settings.explicit_wait, base_url=settings.base_url,
    )


# ==================================================================
# ATC-03
# ==================================================================


@allure.feature('购物车模块')
@allure.story('多商品加购与 Badge 同步')
@allure.title('ATC-03: 多商品加购与购物车 Badge 数字同步验证')
@allure.description(
    '依次添加 3 件商品到购物车，每添加一件即验证'
    '购物车 Badge 数字递增同步。'
)
@allure.severity(allure.severity_level.CRITICAL)
def test_multi_item_add_to_cart_badge_sync(driver, settings) -> None:
    """ATC-03 — 加购与 Badge 数字同步。

    步骤:
        1. 登录标准用户
        2. 依次添加 3 件商品
        3. 每添加一件验证 Badge 计数

    Args:
        driver: function 级 WebDriver fixture。
        settings: session 级 Settings fixture。
    """
    # ---- Step 1: 登录 ----
    with allure.step('Step 1: 登录标准用户'):
        inventory = _perform_login(driver, settings)
        assert inventory.is_inventory_page_displayed(), (
            '登录后未跳转到商品列表页'
        )
        # 确保初始状态干净（购物车为空）
        inventory.reset_app_state()

    # 测试商品列表
    items = [
        'Sauce Labs Backpack',
        'Sauce Labs Bike Light',
        'Sauce Labs Bolt T-Shirt',
    ]

    # ---- Step 2~4: 依次加购并验证 Badge ----
    for idx, item_name in enumerate(items, start=1):
        with allure.step(
            f'Step {idx + 1}: 添加商品 [{idx}/3] «{item_name}»'
        ):
            inventory.add_item_to_cart(item_name)

        with allure.step(f'验证 Badge 计数 = {idx}'):
            actual_count = inventory.get_cart_badge_count()
            assert actual_count == idx, (
                f'购物车 Badge 数量不符！'
                f'添加第 {idx} 件商品 «{item_name}» 后，'
                f'预期 Badge = {idx}，实际 Badge = {actual_count}'
            )

    allure.dynamic.parameter('items', items)


# ==================================================================
# ATC-04
# ==================================================================


@allure.feature('结账模块')
@allure.story('完整结账流程')
@allure.title('ATC-04: 完整结账流程 — Inventory → Cart → Checkout → Complete')
@allure.description(
    '端到端验证从商品加购到下单成功的完整交易链路：'
    'Inventory(加购) → Cart(确认) → '
    'Checkout Step1(填信息) → Step2(概览确认) → Complete(成功页)。'
)
@allure.severity(allure.severity_level.BLOCKER)
def test_complete_checkout_flow(driver, settings) -> None:
    """ATC-04 — 完整结账流程。

    步骤:
        1. 登录 + 清空购物车
        2. 加购 2 件商品
        3. 进入购物车验证商品
        4. 进入结账 Step1 — 填写收货信息
        5. Step2 — 订单概览确认
        6. 点击 Finish — 验证下单成功

    Args:
        driver: function 级 WebDriver fixture。
        settings: session 级 Settings fixture。
    """
    # ---- Step 1: 登录 ----
    with allure.step('Step 1: 登录标准用户并重置应用状态'):
        inventory = _perform_login(driver, settings)
        assert inventory.is_inventory_page_displayed(), (
            '登录后未跳转到商品列表页'
        )
        inventory.reset_app_state()

    # ---- Step 2: 加购 2 件商品 ----
    checkout_items = [
        'Sauce Labs Fleece Jacket',
        'Sauce Labs Onesie',
    ]
    with allure.step(
        f'Step 2: 加购商品 — {", ".join(checkout_items)}'
    ):
        for item in checkout_items:
            inventory.add_item_to_cart(item)

    # 验证 Badge
    badge_count = inventory.get_cart_badge_count()
    assert badge_count == len(checkout_items), (
        f'加购后 Badge 数量不符，'
        f'预期 {len(checkout_items)}，实际 {badge_count}'
    )

    # ---- Step 3: 进入购物车 ----
    with allure.step('Step 3: 进入购物车并验证商品'):
        inventory.go_to_cart()
        cart = CartPage(
            driver,
            timeout=settings.explicit_wait,
            base_url=settings.base_url,
        )
        assert cart.is_cart_page_displayed(), (
            '未能进入购物车页面'
        )

        cart_items = cart.get_item_names()
        for item in checkout_items:
            assert item in cart_items, (
                f'商品 «{item}» 未出现在购物车中，'
                f'购物车包含: {cart_items}'
            )

    # ---- Step 4: 进入结账 Step1 — 填写信息 ----
    with allure.step('Step 4: 进入结账 — 填写收货信息'):
        cart.go_to_checkout()
        checkout = CheckoutPage(
            driver,
            timeout=settings.explicit_wait,
            base_url=settings.base_url,
        )
        assert checkout.is_step1_displayed(), (
            '未能进入结账信息填写页 (Step1)'
        )

        checkout.fill_shipping_info('Jie', 'Chao', '442000')
        checkout.continue_to_overview()

    # ---- Step 5: Step2 — 订单概览确认 ----
    with allure.step('Step 5: 订单概览 — 验证商品与金额'):
        assert checkout.is_step2_displayed(), (
            '未能进入订单概览页 (Step2)'
        )

        # 验证概览页商品与加购一致
        overview_items = checkout.get_overview_item_names()
        for item in checkout_items:
            assert item in overview_items, (
                f'概览页缺少商品 «{item}」，'
                f'当前概览商品: {overview_items}'
            )
        assert checkout.get_overview_item_count() == len(checkout_items), (
            f'概览页商品数量不符，'
            f'预期 {len(checkout_items)}，'
            f'实际 {checkout.get_overview_item_count()}'
        )

        # 验证金额存在（非空即可 — 具体金额由边界值用例覆盖）
        total_str = checkout.get_total()
        assert total_str, '订单总金额为空'
        assert 'Total' in total_str, (
            f'总金额格式异常: {total_str}'
        )

        # 确认下单
        checkout.finish_checkout()

    # ---- Step 6: 验证下单成功 ----
    with allure.step('Step 6: 验证下单成功 — Complete 页'):
        assert checkout.is_complete_displayed(), (
            '未能进入下单完成页 (Complete)'
        )

        complete_msg = checkout.get_complete_message()
        expected_msg = 'Thank you for your order!'
        assert complete_msg == expected_msg, (
            f'下单成功消息不符，'
            f'预期 "{expected_msg}"，'
            f'实际 "{complete_msg}"'
        )

        assert checkout.is_pony_express_displayed(), (
            '完成页小马快递图片未显示'
        )

    allure.dynamic.parameter('checkout_items', checkout_items)
