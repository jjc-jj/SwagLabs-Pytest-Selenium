# File: pages/checkout_page.py
"""结账流程 Page Object — 三步结账（信息 → 概览 → 完成）。

URL:
    - Step 1（信息填写）: ``/checkout-step-one.html``
    - Step 2（订单概览）: ``/checkout-step-two.html``
    - Step 3（完成确认）: ``/checkout-complete.html``

Usage::

    from pages.checkout_page import CheckoutPage

    checkout = CheckoutPage(driver, base_url=cfg.base_url)
    checkout.fill_shipping_info('Jie', 'Chao', '442000')
    checkout.continue_to_overview()
    checkout.finish_checkout()
    msg = checkout.get_complete_message()
"""

from __future__ import annotations

from typing import List, Optional

from selenium.webdriver.common.by import By

from pages.base_page import BasePage


class CheckoutPage(BasePage):
    """结账流程页面对象（POM）。

    覆盖三步结账的所有元素和方法，不包含断言逻辑。
    """

    # ==================================================================
    # Step 1 — 信息填写页 (/checkout-step-one.html)
    # ==================================================================

    LOC_FIRST_NAME = (By.ID, 'first-name')
    """名字输入框"""

    LOC_LAST_NAME = (By.ID, 'last-name')
    """姓氏输入框"""

    LOC_POSTAL_CODE = (By.ID, 'postal-code')
    """邮编输入框"""

    LOC_CONTINUE_BTN = (By.ID, 'continue')
    """Continue 按钮 — 进入订单概览"""

    LOC_CANCEL_BTN = (By.ID, 'cancel')
    """Cancel 按钮 — 返回购物车"""

    LOC_STEP1_ERROR = (By.CSS_SELECTOR, 'h3[data-test="error"]')
    """Step1 错误消息"""

    LOC_STEP1_CONTAINER = (By.CSS_SELECTOR, '.checkout_info')
    """Step1 信息表单容器"""

    # ==================================================================
    # Step 2 — 订单概览页 (/checkout-step-two.html)
    # ==================================================================

    LOC_SUMMARY_CONTAINER = (By.CSS_SELECTOR, '.checkout_summary_container')
    """订单概览容器"""

    LOC_CART_ITEMS = (By.CSS_SELECTOR, '.cart_item')
    """概览页商品行（与购物车结构相同）"""

    LOC_CART_ITEM_NAMES = (By.CSS_SELECTOR, '.inventory_item_name')
    """概览页商品名称"""

    LOC_PAYMENT_INFO = (By.CSS_SELECTOR, '[data-test="payment-info-value"]')
    """付款信息"""

    LOC_SHIPPING_INFO = (By.CSS_SELECTOR, '[data-test="shipping-info-value"]')
    """配送信息"""

    LOC_SUBTOTAL = (By.CSS_SELECTOR, '.summary_subtotal_label')
    """小计标签（Item total）"""

    LOC_TAX = (By.CSS_SELECTOR, '.summary_tax_label')
    """税费标签（Tax）"""

    LOC_TOTAL = (By.CSS_SELECTOR, '.summary_total_label')
    """总计标签（Total）"""

    LOC_FINISH_BTN = (By.ID, 'finish')
    """Finish 按钮 — 确认下单"""

    LOC_STEP2_CANCEL = (By.ID, 'cancel')
    """Cancel 按钮 — 返回商品列表"""

    # ==================================================================
    # Step 3 — 完成页 (/checkout-complete.html)
    # ==================================================================

    LOC_COMPLETE_CONTAINER = (By.ID, 'checkout_complete_container')
    """完成页容器"""

    LOC_COMPLETE_HEADER = (By.CSS_SELECTOR, '.complete-header')
    """完成页标题（THANK YOU FOR YOUR ORDER）"""

    LOC_COMPLETE_TEXT = (By.CSS_SELECTOR, '.complete-text')
    """完成页描述文本"""

    LOC_PONY_EXPRESS = (By.CSS_SELECTOR, '.pony_express')
    """小马快递图片"""

    LOC_BACK_HOME_BTN = (By.ID, 'back-to-products')
    """Back Home 按钮 — 返回商品列表"""

    # ==================================================================
    # 标题
    # ==================================================================

    LOC_TITLE = (By.CLASS_NAME, 'title')
    """页面标题"""

    # ==================================================================
    # Step 1 — 业务方法
    # ==================================================================

    def fill_shipping_info(
        self,
        first_name: str,
        last_name: str,
        postal_code: str,
    ) -> None:
        """填写收货信息。

        Args:
            first_name: 名。
            last_name: 姓。
            postal_code: 邮编。
        """
        self.type(self.LOC_FIRST_NAME, first_name)
        self.type(self.LOC_LAST_NAME, last_name)
        self.type(self.LOC_POSTAL_CODE, postal_code)

    def continue_to_overview(self) -> None:
        """点击 Continue 按钮，进入订单概览页。"""
        self.click(self.LOC_CONTINUE_BTN)

    def cancel_checkout(self) -> None:
        """点击 Cancel 按钮，返回购物车页。"""
        self.click(self.LOC_CANCEL_BTN)

    def get_step1_error(self) -> str:
        """获取 Step1 错误消息。

        Returns:
            错误文本；无错误返回空字符串。
        """
        if self.is_displayed(self.LOC_STEP1_ERROR, timeout=2):
            return self.get_text(self.LOC_STEP1_ERROR)
        return ''

    def is_step1_displayed(self) -> bool:
        """检查是否在信息填写页。

        Returns:
            ``True`` 如果 Step1 表单可见。
        """
        return self.is_displayed(self.LOC_STEP1_CONTAINER, timeout=5)

    # ==================================================================
    # Step 2 — 业务方法
    # ==================================================================

    def finish_checkout(self) -> None:
        """点击 Finish 按钮，完成下单。"""
        self.click(self.LOC_FINISH_BTN)

    def cancel_overview(self) -> None:
        """在概览页点击 Cancel，返回商品列表。"""
        self.click(self.LOC_STEP2_CANCEL)

    def get_overview_item_names(self) -> List[str]:
        """获取订单概览中的商品名称列表。

        Returns:
            商品名称列表。
        """
        elements = self.find_elements(self.LOC_CART_ITEM_NAMES)
        return [el.text for el in elements]

    def get_overview_item_count(self) -> int:
        """获取订单概览中的商品数量。

        Returns:
            商品数量。
        """
        return self.get_element_count(self.LOC_CART_ITEMS)

    def get_payment_info(self) -> str:
        """获取付款信息文本。

        Returns:
            付款信息字符串。
        """
        return self.get_text(self.LOC_PAYMENT_INFO)

    def get_shipping_info(self) -> str:
        """获取配送信息文本。

        Returns:
            配送信息字符串。
        """
        return self.get_text(self.LOC_SHIPPING_INFO)

    def get_subtotal(self) -> str:
        """获取小计文本。

        Returns:
            如 ``'Item total: $29.99'``。
        """
        return self.get_text(self.LOC_SUBTOTAL)

    def get_tax(self) -> str:
        """获取税费文本。

        Returns:
            如 ``'Tax: $2.40'``。
        """
        return self.get_text(self.LOC_TAX)

    def get_total(self) -> str:
        """获取总计文本。

        Returns:
            如 ``'Total: $32.39'``。
        """
        return self.get_text(self.LOC_TOTAL)

    def is_step2_displayed(self) -> bool:
        """检查是否在订单概览页。

        Returns:
            ``True`` 如果概览容器可见。
        """
        return self.is_displayed(self.LOC_SUMMARY_CONTAINER, timeout=5)

    # ==================================================================
    # Step 3 — 业务方法
    # ==================================================================

    def get_complete_message(self) -> str:
        """获取下单成功页的标题文本。

        Returns:
            如 ``'THANK YOU FOR YOUR ORDER'``。
        """
        return self.get_text(self.LOC_COMPLETE_HEADER)

    def get_complete_description(self) -> str:
        """获取下单成功页的描述文本。

        Returns:
            描述文本。
        """
        return self.get_text(self.LOC_COMPLETE_TEXT)

    def back_to_home(self) -> None:
        """点击 Back Home 按钮，返回商品列表页。"""
        self.click(self.LOC_BACK_HOME_BTN)

    def is_complete_displayed(self) -> bool:
        """检查是否在订单完成页。

        Returns:
            ``True`` 如果完成容器可见。
        """
        return self.is_displayed(self.LOC_COMPLETE_CONTAINER, timeout=5)

    def is_pony_express_displayed(self) -> bool:
        """检查小马快递图片是否显示。

        Returns:
            ``True`` 如果图片可见。
        """
        return self.is_displayed(self.LOC_PONY_EXPRESS, timeout=3)

    # ==================================================================
    # 通用
    # ==================================================================

    def get_page_title(self) -> str:
        """获取当前步骤的页面标题。

        Returns:
            标题字符串（如 ``'Checkout: Your Information'``）。
        """
        return self.get_text(self.LOC_TITLE)
