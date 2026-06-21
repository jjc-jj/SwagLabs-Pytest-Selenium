# File: testcases/test_inventory.py
"""商品列表排序冒烟测试 — ATC-02。

验证商品列表页 4 种排序方式的正确性：
    - az:  Name (A to Z)
    - za:  Name (Z to A)
    - lohi: Price (low to high)
    - hilo: Price (high to low)

排序比对在 Python 内存中执行，与 UI 实际排序逐项对比。
"""

from __future__ import annotations

import allure
import pytest

from pages.login_page import LoginPage
from pages.inventory_page import InventoryPage

# ------------------------------------------------------------------
# 排序选项 → 预期行为映射
# ------------------------------------------------------------------

# 用于 parametrize 的排序测试数据
_SORT_TEST_CASES = [
    pytest.param(
        'az',
        'name',
        False,
        id='Name-A-to-Z',
    ),
    pytest.param(
        'za',
        'name',
        True,
        id='Name-Z-to-A',
    ),
    pytest.param(
        'lohi',
        'price',
        False,
        id='Price-low-to-high',
    ),
    pytest.param(
        'hilo',
        'price',
        True,
        id='Price-high-to-low',
    ),
]


# ------------------------------------------------------------------
# 辅助函数
# ------------------------------------------------------------------


def _parse_price(price_str: str) -> float:
    """将 UI 价格字符串转为浮点数。

    处理格式: ``"$29.99"`` → ``29.99``。

    Args:
        price_str: 含 ``$`` 前缀的价格文本。

    Returns:
        浮点价格值。

    Raises:
        ValueError: 无法解析时抛出。
    """
    cleaned = price_str.strip().replace('$', '').replace(',', '')
    return float(cleaned)


def _sort_names(
    names: list[str],
    reverse: bool,
) -> list[str]:
    """对名称列表排序（大小写敏感，匹配 UI 行为）。

    Args:
        names: 商品名称列表。
        reverse: ``True`` 为降序。

    Returns:
        排序后的列表。
    """
    return sorted(names, key=lambda s: s, reverse=reverse)


def _sort_prices(
    prices: list[str],
    reverse: bool,
) -> list[str]:
    """对价格列表按数值排序，返回原始格式字符串。

    Args:
        prices: 价格字符串列表（如 ``["$29.99", "$9.99"]``）。
        reverse: ``True`` 为降序。

    Returns:
        按数值排序后的价格字符串列表。
    """
    # 按解析后的 float 值排序，保留原始格式
    return sorted(prices, key=_parse_price, reverse=reverse)


# ==================================================================
# 辅助 fixture — 已登录的 InventoryPage
# ==================================================================


def _do_login_and_goto_inventory(driver, settings) -> InventoryPage:
    """登录标准用户并返回 InventoryPage 实例。

    Args:
        driver: WebDriver fixture。
        settings: Settings fixture。

    Returns:
        已登录的 InventoryPage。
    """
    account = settings.get_account('standard_user')
    login_page = LoginPage(
        driver, timeout=settings.explicit_wait, base_url=settings.base_url,
    )
    login_page.open()
    login_page.do_login(account['username'], account['password'])
    return InventoryPage(
        driver, timeout=settings.explicit_wait, base_url=settings.base_url,
    )


# ==================================================================
# ATC-02
# ==================================================================


@allure.feature('商品列表模块')
@allure.story('商品排序')
@allure.title('ATC-02: 商品列表多维度排序验证 — {sort_by}-{direction}-{reverse_}')
@allure.description(
    '验证 4 种排序方式 (az / za / lohi / hilo) '
    '下 UI 展示顺序与 Python 内存排序结果一致。'
    '价格需从 "$29.99" 转为 float 再做数值比对。'
)
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.parametrize(
    'sort_value, sort_type, reverse_',
    _SORT_TEST_CASES,
)
def test_inventory_sort_validation(
    driver,
    settings,
    sort_value: str,
    sort_type: str,
    reverse_: bool,
) -> None:
    """ATC-02 — 商品列表排序验证。

    步骤:
        1. 登录标准用户
        2. 选择排序方式
        3. 提取 UI 列表数据
        4. Python 内存排序
        5. 逐项比对 UI 顺序与预期顺序

    Args:
        driver: function 级 WebDriver fixture。
        settings: session 级 Settings fixture。
        sort_value: 排序选项 value（az / za / lohi / hilo）。
        sort_type: ``'name'`` 或 ``'price'``。
        reverse_: ``True`` 为降序。
    """
    # ---- Step 1: 登录 ----
    with allure.step('Step 1: 登录标准用户'):
        inventory = _do_login_and_goto_inventory(driver, settings)
        assert inventory.is_inventory_page_displayed(), (
            '登录后未跳转到商品列表页'
        )

    # ---- Step 2: 选择排序并提取 UI 数据 ----
    with allure.step(
        f'Step 2: 选择排序 «{sort_value}» 并提取 UI 列表'
    ):
        inventory.sort_by(sort_value)

        if sort_type == 'name':
            ui_data = inventory.get_product_names()
        else:
            ui_data = inventory.get_product_prices()

        assert len(ui_data) > 0, (
            f'未提取到任何商品数据，sort={sort_value}'
        )

    # ---- Step 3: Python 内存排序 ----
    with allure.step(
        f'Step 3: Python 内存排序 (type={sort_type}, '
        f'reverse={reverse_})'
    ):
        if sort_type == 'name':
            expected_data = _sort_names(ui_data.copy(), reverse_)
        else:
            # 价格排序：展示原始格式，但按数值比对
            expected_data = _sort_prices(ui_data.copy(), reverse_)

    # ---- Step 4: 逐项比对 ----
    with allure.step('Step 4: 逐项比对 UI 顺序与预期顺序'):
        mismatches: list[dict] = []
        for idx, (ui_val, exp_val) in enumerate(
            zip(ui_data, expected_data)
        ):
            if ui_val != exp_val:
                mismatches.append({
                    'index': idx,
                    'ui_value': ui_val,
                    'expected_value': exp_val,
                })

        assert len(mismatches) == 0, (
            f'排序验证失败 | sort={sort_value} | '
            f'共 {len(ui_data)} 项 | '
            f'{len(mismatches)} 项不匹配:\n' +
            '\n'.join(
                f'  [{m["index"]}] '
                f'UI=«{m["ui_value"]}» '
                f'Expected=«{m["expected_value"]}»'
                for m in mismatches
            )
        )

    # ---- Step 5: 数值排序额外验证（仅价格）----
    if sort_type == 'price':
        with allure.step('Step 5: 验证价格单调性（数值级别）'):
            numeric_prices = [_parse_price(p) for p in ui_data]
            if not reverse_:
                # 升序：每个价格 >= 前一个
                for i in range(1, len(numeric_prices)):
                    assert numeric_prices[i] >= numeric_prices[i - 1], (
                        f'价格非单调递增 | index={i} | '
                        f'prev={numeric_prices[i - 1]} | '
                        f'curr={numeric_prices[i]}'
                    )
            else:
                # 降序：每个价格 <= 前一个
                for i in range(1, len(numeric_prices)):
                    assert numeric_prices[i] <= numeric_prices[i - 1], (
                        f'价格非单调递减 | index={i} | '
                        f'prev={numeric_prices[i - 1]} | '
                        f'curr={numeric_prices[i]}'
                    )

    allure.dynamic.parameter('sort_value', sort_value)
    allure.dynamic.parameter('ui_count', len(ui_data))
