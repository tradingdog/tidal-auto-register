# -*- coding: utf-8 -*-
"""
Tidal 坐标与模板配置

集中维护 Tidal 站内使用的固定坐标、模板文件、匹配阈值、滚轮次数和关键等待时间。
"""

from dataclasses import dataclass
import os
from typing import Optional


@dataclass(frozen=True)
class FixedPoint:
    step_id: str
    x: int
    y: int
    description: str
    notes: str = ""


@dataclass(frozen=True)
class TemplateTarget:
    step_id: str
    file_name: str
    threshold: float
    description: str
    click_x: Optional[int] = None
    click_y: Optional[int] = None
    notes: str = ""


IMAGES_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "images"))
LEGACY_TEMPLATE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "template"))


FIXED_POINTS = {
    "OK-01": FixedPoint("OK-01", 1492, 128, "Create a free account"),
    "OK-03": FixedPoint("OK-03", 572, 709, "条款复选框"),
    "OK-04": FixedPoint("OK-04", 842, 788, "Sign up 按钮"),
    "OK-05": FixedPoint("OK-05", 1446, 125, "头像图标"),
    "OK-06": FixedPoint("OK-06", 1313, 221, "Manage subscription"),
    "TD-02": FixedPoint("TD-02", 788, 429, "注册页邮箱输入框"),
    "TD-04": FixedPoint("TD-04", 805, 497, "注册页 Continue 按钮"),
    "TD-05": FixedPoint("TD-05", 759, 502, "注册页密码输入框"),
    "SUB-01": FixedPoint("SUB-01", 788, 429, "订阅登录页邮箱输入框"),
    "SUB-02": FixedPoint("SUB-02", 805, 497, "订阅登录页 Continue 按钮"),
    "SUB-03": FixedPoint("SUB-03", 759, 502, "订阅登录页密码输入框"),
    "SUB-04": FixedPoint("SUB-04", 797, 554, "Log In 按钮"),
    "PLAN-01": FixedPoint("PLAN-01", 302, 513, "View Plan 按钮"),
    "PLAN-02": FixedPoint("PLAN-02", 792, 778, "套餐页 Continue 按钮"),
}


TEMPLATE_TARGETS = {
    "TD-00-ACCESS-RESTRICTED": TemplateTarget(
        "TD-00-ACCESS-RESTRICTED",
        "access_restricted.png",
        0.90,
        "访问暂时受限页面",
    ),
    "TD-01-TRANSLATION": TemplateTarget(
        "TD-01-TRANSLATION",
        "chrome_translation.png",
        0.90,
        "Chrome 翻译弹窗",
        click_x=1419,
        click_y=103,
        notes="命中后点击右上角 x 关闭翻译弹窗",
    ),
    "TD-01-COOKIES": TemplateTarget(
        "TD-01-COOKIES",
        "tidal_cookies.png",
        0.90,
        "Cookie Accept 弹窗",
        click_x=713,
        click_y=803,
        notes="命中后点击 Accept 按钮",
    ),
    "DOB-01": TemplateTarget("DOB-01", "day.png", 0.90, "Day 下拉框"),
    "DOB-02": TemplateTarget("DOB-02", "month.png", 0.90, "Month 下拉框"),
    "DOB-03": TemplateTarget("DOB-03", "year.png", 0.90, "Year 下拉框"),
    "PAY-01": TemplateTarget("PAY-01", "full_name.png", 0.98, "Full Name 输入框"),
    "PAY-02": TemplateTarget("PAY-02", "card_number.png", 0.98, "Card Number 输入框"),
    "PAY-03": TemplateTarget("PAY-03", "exp_date.png", 0.98, "Exp. Date 输入框"),
    "PAY-04": TemplateTarget("PAY-04", "cvc.png", 0.98, "CVC 输入框"),
    "PAY-05": TemplateTarget("PAY-05", "zip_code.png", 0.98, "ZIP Code 输入框"),
    "PAY-06": TemplateTarget("PAY-06", "unchecked.png", 0.85, "支付页未勾选复选框"),
    "PAY-07": TemplateTarget("PAY-07", "pay_continue_btn.png", 0.90, "支付提交 Continue 按钮"),
    "CAN-01": TemplateTarget("CAN-01", "subscription.png", 0.90, "Subscription 按钮"),
    "CAN-02": TemplateTarget("CAN-02", "cancel_subscription.png", 0.90, "Cancel subscription 按钮"),
    "CAN-03": TemplateTarget("CAN-03", "continue_cancellation_final.png", 0.90, "Continue Cancellation 按钮"),
}


SCROLL_STEPS = {
    "PAY-06": 4,
    "CAN-01": 8,
    "CAN-02": 8,
    "CAN-03": 6,
}


WAIT_SECONDS = {
    "TD-00-BROWSER-READY": 5,
    "TD-01-LOAD": 10,
    "PLAN-01": 5,
    "PLAN-02": 5,
    "PAY-07": 10,
    "CAN-01": 3,
    "CAN-02": 3,
    "CAN-03": 3,
}


TYPE_DELAY_RANGES = {
    "tidal_input": (0.20, 0.50),
    "tidal_input_done": (1.00, 2.00),
    "dropdown_key": (0.50, 0.50),
}


MONTH_KEYS = ["j", "f", "m", "a", "s", "o", "n", "d"]
DAY_KEYS = [str(number) for number in range(1, 10)]
YEAR_PRESS_COUNTS = list(range(1, 11))


def get_fixed_point(step_id: str) -> FixedPoint:
    return FIXED_POINTS[step_id]


def get_template_target(step_id: str) -> TemplateTarget:
    return TEMPLATE_TARGETS[step_id]


def get_template_path(step_id: str) -> str:
    file_name = get_template_target(step_id).file_name
    image_path = os.path.join(IMAGES_DIR, file_name)
    legacy_path = os.path.join(LEGACY_TEMPLATE_DIR, file_name)

    if os.path.exists(image_path):
        return image_path

    if os.path.exists(legacy_path):
        return legacy_path

    return image_path


def list_required_templates() -> list[str]:
    return sorted({target.file_name for target in TEMPLATE_TARGETS.values()})
