# File: pages/inventory_page.py
"""商品列表页 Page Object — Sauce Demo 商品橱窗。

URL: ``/inventory.html``

提供商品查找、加入购物车、排序、购物车徽章、侧边栏登出等操作。
所有定位器使用 ``data-test`` 属性（Sauce Demo 官方测试标记）。

Usage::

    from pages.inventory_page import InventoryPage

    inv = InventoryPage(driver, base_url=cfg.base_url)
    inv.add_item_to_cart('Sauce Labs Backpack')
    count = inv.get_cart_badge_count()
"""

from __future__ import annotations

from typing import List, Optional

from selenium.webdriver.common.by import By

from pages.base_page import BasePage
from utils.logger_util import get_logger

_module_logger = get_logger(__name__)

# ------------------------------------------------------------------
# 商品名称 → data-test slug 映射表
# ------------------------------------------------------------------
_ITEM_SLUG_MAP = {
    'Sauce Labs Backpack': 'sauce-labs-backpack',
    'Sauce Labs Bike Light': 'sauce-labs-bike-light',
    'Sauce Labs Bolt T-Shirt': 'sauce-labs-bolt-t-shirt',
    'Sauce Labs Fleece Jacket': 'sauce-labs-fleece-jacket',
    'Sauce Labs Onesie': 'sauce-labs-onesie',
    'Test.allTheThings() T-Shirt (Red)': 'test.allthethings()-t-shirt-(red)',
}


def _to_slug(item_name: str) -> str:
    """将商品名称转为 data-test 中的 slug。

    Args:
        item_name: 商品完整展示名称。

    Returns:
        对应的 slug，如 ``sauce-labs-backpack``。
    """
    if item_name in _ITEM_SLUG_MAP:
        return _ITEM_SLUG_MAP[item_name]
    # fallback: 小写 + 空格转连字符
    return item_name.lower().replace(' ', '-')


class InventoryPage(BasePage):
    """商品列表页面对象（POM）。

    元素定位器全部以 ``LOC_`` 前缀的类属性形式定义。
    """

    # ==================================================================
    # 元素定位器
    # ==================================================================

    # ---- 页面容器 ----
    LOC_INVENTORY_CONTAINER = (By.ID, 'inventory_container')
    """商品列表容器"""

    LOC_PRODUCT_ITEMS = (By.CSS_SELECTOR, '.inventory_item')
    """所有商品卡片"""

    LOC_PRODUCT_NAMES = (By.CSS_SELECTOR, '.inventory_item_name')
    """所有商品名称"""

    LOC_PRODUCT_PRICES = (By.CSS_SELECTOR, '.inventory_item_price')
    """所有商品价格"""

    LOC_PRODUCT_DESCRIPTIONS = (By.CSS_SELECTOR, '.inventory_item_desc')
    """所有商品描述"""

    LOC_PRODUCT_IMAGES = (By.CSS_SELECTOR, '.inventory_item_img')
    """所有商品图片"""

    # ---- 标题 ----
    LOC_TITLE = (By.CLASS_NAME, 'title')
    """页面标题（Products）"""

    # ---- 排序 ----
    LOC_SORT_DROPDOWN = (By.CSS_SELECTOR, 'select.product_sort_container')
    """排序下拉框"""

    # ---- 购物车 ----
    LOC_CART_LINK = (By.CSS_SELECTOR, '.shopping_cart_link')
    """购物车图标链接"""

    LOC_CART_BADGE = (By.CSS_SELECTOR, '.shopping_cart_badge')
    """购物车数量徽章"""

    # ---- 侧边栏菜单 ----
    LOC_MENU_BUTTON = (By.ID, 'react-burger-menu-btn')
    """汉堡菜单按钮"""

    LOC_MENU_SIDEBAR = (By.CSS_SELECTOR, '.bm-menu')
    """侧边栏菜单容器"""

    LOC_LOGOUT_LINK = (By.ID, 'logout_sidebar_link')
    """登出链接"""

    LOC_MENU_CLOSE_BTN = (By.ID, 'react-burger-cross-btn')
    """关闭菜单按钮"""

    LOC_RESET_APP_LINK = (By.ID, 'reset_sidebar_link')
    """重置应用状态链接"""

    # ---- Footer ----
    LOC_FOOTER = (By.CSS_SELECTOR, '.footer')
    """页脚"""

    # ==================================================================
    # 动态定位器工厂方法（@staticmethod）
    # ==================================================================

    @staticmethod
    def _build_locator_add_to_cart(slug: str) -> tuple:
        """构建「加入购物车」按钮定位器。

        Args:
            slug: 商品名称 slug（如 ``sauce-labs-backpack``）。

        Returns:
            ``(By.CSS_SELECTOR, 'button[data-test="add-to-cart-{slug}"]')``。
        """
        return (By.CSS_SELECTOR, f'button[data-test="add-to-cart-{slug}"]')

    @staticmethod
    def _build_locator_remove_from_cart(slug: str) -> tuple:
        """构建「从购物车移除」按钮定位器。

        Args:
            slug: 商品名称 slug。

        Returns:
            ``(By.CSS_SELECTOR, 'button[data-test="remove-{slug}"]')``。
        """
        return (By.CSS_SELECTOR, f'button[data-test="remove-{slug}"]')

    @staticmethod
    def _build_locator_product_title_link(slug: str) -> tuple:
        """构建商品标题链接定位器。

        Args:
            slug: 商品名称 slug。

        Returns:
            ``(By.CSS_SELECTOR, 'a[id="item_{slug}_title_link"]')``。
        """
        return (By.CSS_SELECTOR, f'a[id="item_{slug}_title_link"]')

    # ==================================================================
    # 商品操作方法
    # ==================================================================

    def add_item_to_cart(self, item_name: str) -> None:
        """将指定商品加入购物车。

        Args:
            item_name: 商品展示名称（如 ``'Sauce Labs Backpack'``）。
        """
        slug = _to_slug(item_name)
        self.click(self._build_locator_add_to_cart(slug))

    def remove_item_from_cart(self, item_name: str) -> None:
        """将指定商品从购物车移除（列表页移除按钮）。

        Args:
            item_name: 商品展示名称。
        """
        slug = _to_slug(item_name)
        self.click(self._build_locator_remove_from_cart(slug))

    def is_item_in_cart(self, item_name: str) -> bool:
        """检查商品是否已加入购物车（按钮变为 Remove）。

        Args:
            item_name: 商品名称。

        Returns:
            ``True`` 如果 Remove 按钮可见。
        """
        slug = _to_slug(item_name)
        return self.is_displayed(
            self._build_locator_remove_from_cart(slug), timeout=2
        )

    def get_product_names(self) -> List[str]:
        """获取当前页面所有商品名称。

        Returns:
            商品名称列表。
        """
        elements = self.find_elements(self.LOC_PRODUCT_NAMES)
        return [el.text for el in elements]

    def get_product_prices(self) -> List[str]:
        """获取当前页面所有商品价格。

        Returns:
            价格字符串列表（含 ``$`` 符号）。
        """
        elements = self.find_elements(self.LOC_PRODUCT_PRICES)
        return [el.text for el in elements]

    def get_inventory_count(self) -> int:
        """获取当前页面的商品数量。

        Returns:
            商品卡片数量。
        """
        return self.get_element_count(self.LOC_PRODUCT_ITEMS)

    def get_product_price(self, item_name: str) -> str:
        """获取单个商品的价格。

        Args:
            item_name: 商品名称。

        Returns:
            价格字符串（如 ``'$29.99'``）。
        """
        slug = _to_slug(item_name)
        item_link = self.find_element(
            self._build_locator_product_title_link(slug),
            timeout=5,
        )
        # 向上两层到 inventory_item，再向下找 price
        price_el = item_link.find_element(
            By.XPATH,
            '../../div[@class="inventory_item_price"]',
        )
        return price_el.text

    # ==================================================================
    # 排序
    # ==================================================================

    def sort_by(self, option_value: str) -> None:
        """选择排序方式。

        Args:
            option_value: ``<option>`` 的 value 属性：
                - ``'az'`` — Name (A to Z)
                - ``'za'`` — Name (Z to A)
                - ``'lohi'`` — Price (low to high)
                - ``'hilo'`` — Price (high to low)
        """
        from selenium.webdriver.support.ui import Select

        dropdown = self.find_element(self.LOC_SORT_DROPDOWN)
        select = Select(dropdown)
        select.select_by_value(option_value)
        self.logger.info('🔽 排序方式: %s', option_value)

    @property
    def logger(self):
        """暴露 logger 给 Page 类使用。"""
        return _module_logger

    # ==================================================================
    # 购物车
    # ==================================================================

    def get_cart_badge_count(self) -> int:
        """获取购物车徽章数字。

        Returns:
            购物车中商品数量；如果徽章不可见返回 0。
        """
        if self.is_displayed(self.LOC_CART_BADGE, timeout=2):
            text = self.get_text(self.LOC_CART_BADGE)
            return int(text) if text.isdigit() else 0
        return 0

    def go_to_cart(self) -> None:
        """点击购物车图标，跳转到购物车页面。"""
        self.click(self.LOC_CART_LINK)

    # ==================================================================
    # 侧边栏 / 导航
    # ==================================================================

    def open_menu(self) -> None:
        """打开左侧汉堡菜单。"""
        self.click(self.LOC_MENU_BUTTON)

    def close_menu(self) -> None:
        """关闭侧边栏菜单。"""
        if self.is_displayed(self.LOC_MENU_CLOSE_BTN, timeout=2):
            self.click(self.LOC_MENU_CLOSE_BTN)

    def logout(self) -> None:
        """执行登出操作（打开菜单 → 点击 Logout）。"""
        self.open_menu()
        # 等待侧边栏滑出动画
        self.find_element(self.LOC_LOGOUT_LINK, timeout=5)
        self.click(self.LOC_LOGOUT_LINK)

    def reset_app_state(self) -> None:
        """重置应用状态（清空购物车）。"""
        self.open_menu()
        self.find_element(self.LOC_RESET_APP_LINK, timeout=5)
        self.click(self.LOC_RESET_APP_LINK)

    # ==================================================================
    # 页面状态
    # ==================================================================

    def is_inventory_page_displayed(self) -> bool:
        """验证是否在商品列表页。

        Returns:
            ``True`` 如果商品容器可见。
        """
        return self.is_displayed(self.LOC_INVENTORY_CONTAINER, timeout=5)

    def get_page_title(self) -> str:
        """获取页面标题文本（如 'Products'）。

        Returns:
            标题字符串。
        """
        return self.get_text(self.LOC_TITLE)
