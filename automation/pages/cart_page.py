# File: pages/cart_page.py
"""购物车页 Page Object — 查看已选商品并进入结账。

URL: ``/cart.html``

提供商品验证、移除、继续购物、进入结账等操作。

Usage::

    from pages.cart_page import CartPage

    cart = CartPage(driver, base_url=cfg.base_url)
    cart.go_to_checkout()
"""

from __future__ import annotations

from typing import List

from selenium.webdriver.common.by import By

from pages.base_page import BasePage


class CartPage(BasePage):
    """购物车页面对象（POM）。"""

    # ==================================================================
    # 元素定位器
    # ==================================================================

    LOC_CART_CONTAINER = (By.ID, 'cart_contents_container')
    """购物车内容容器"""

    LOC_CART_ITEMS = (By.CSS_SELECTOR, '.cart_item')
    """购物车中所有商品行"""

    LOC_CART_ITEM_NAMES = (By.CSS_SELECTOR, '.inventory_item_name')
    """购物车中商品名称"""

    LOC_CART_ITEM_PRICES = (By.CSS_SELECTOR, '.inventory_item_price')
    """购物车中商品价格"""

    LOC_CART_ITEM_QUANTITIES = (By.CSS_SELECTOR, '.cart_quantity')
    """购物车中每件商品数量"""

    LOC_CONTINUE_SHOPPING = (By.ID, 'continue-shopping')
    """Continue Shopping 按钮 — 返回商品列表页"""

    LOC_CHECKOUT_BTN = (By.ID, 'checkout')
    """Checkout 按钮 — 进入结账第一步"""

    LOC_TITLE = (By.CLASS_NAME, 'title')
    """页面标题（Your Cart）"""

    # ==================================================================
    # 动态定位器工厂方法（@staticmethod）
    # ==================================================================

    @staticmethod
    def _build_locator_remove_from_cart(slug: str) -> tuple:
        """构建「从购物车移除」按钮定位器。

        Args:
            slug: 商品名称 slug（如 ``sauce-labs-backpack``）。

        Returns:
            ``(By.CSS_SELECTOR, 'button[data-test="remove-{slug}"]')``。
        """
        return (By.CSS_SELECTOR, f'button[data-test="remove-{slug}"]')

    # ==================================================================
    # 业务操作
    # ==================================================================

    def remove_item(self, item_name: str) -> None:
        """从购物车中移除指定商品。

        Args:
            item_name: 商品完整名称（如 ``'Sauce Labs Backpack'``）。
        """
        from pages.inventory_page import _to_slug
        slug = _to_slug(item_name)
        self.click(self._build_locator_remove_from_cart(slug))

    def go_to_checkout(self) -> None:
        """点击 Checkout 按钮，进入结账信息填写页。"""
        self.click(self.LOC_CHECKOUT_BTN)

    def continue_shopping(self) -> None:
        """点击 Continue Shopping，返回商品列表页。"""
        self.click(self.LOC_CONTINUE_SHOPPING)

    # ==================================================================
    # 数据读取
    # ==================================================================

    def get_item_count(self) -> int:
        """获取购物车中商品种类数量。

        Returns:
            商品行数。
        """
        return self.get_element_count(self.LOC_CART_ITEMS)

    def get_item_names(self) -> List[str]:
        """获取购物车中所有商品名称。

        Returns:
            商品名称列表。
        """
        elements = self.find_elements(self.LOC_CART_ITEM_NAMES)
        return [el.text for el in elements]

    def get_item_prices(self) -> List[str]:
        """获取购物车中所有商品价格。

        Returns:
            价格字符串列表。
        """
        elements = self.find_elements(self.LOC_CART_ITEM_PRICES)
        return [el.text for el in elements]

    def is_item_in_cart(self, item_name: str) -> bool:
        """检查指定商品是否在购物车中。

        Args:
            item_name: 商品名称。

        Returns:
            ``True`` 如果商品在购物车中。
        """
        names = self.get_item_names()
        return item_name in names

    def is_cart_empty(self) -> bool:
        """检查购物车是否为空。

        Returns:
            ``True`` 如果无商品。
        """
        return self.get_item_count() == 0

    # ==================================================================
    # 页面状态
    # ==================================================================

    def is_cart_page_displayed(self) -> bool:
        """验证是否在购物车页面。

        Returns:
            ``True`` 如果购物车容器可见。
        """
        return self.is_displayed(self.LOC_CART_CONTAINER, timeout=5)

    def get_page_title(self) -> str:
        """获取页面标题文本（预期 'Your Cart'）。

        Returns:
            标题字符串。
        """
        return self.get_text(self.LOC_TITLE)
