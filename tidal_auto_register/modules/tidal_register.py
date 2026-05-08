# -*- coding: utf-8 -*-
"""
Tidal 注册核心模块 - 精确元素定位版本
"""

import random
import re
import string
import time
import io
import importlib
import os
from datetime import datetime
from contextlib import redirect_stderr, redirect_stdout
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from utils.tidal_coordinates import (
    DAY_KEYS,
    MONTH_KEYS,
    SCROLL_STEPS,
    TYPE_DELAY_RANGES,
    WAIT_SECONDS,
    YEAR_PRESS_COUNTS,
    get_fixed_point,
    get_template_path,
    get_template_target,
)


_PYAUTOGUI = None
_PYAUTOGUI_LOAD_ATTEMPTED = False
_IMAGE_IMPORTS = None
_IMAGE_LOAD_ATTEMPTED = False


def _load_pyautogui():
    """按需加载 PyAutoGUI，失败时返回 None。"""
    global _PYAUTOGUI, _PYAUTOGUI_LOAD_ATTEMPTED

    if _PYAUTOGUI_LOAD_ATTEMPTED:
        return _PYAUTOGUI

    _PYAUTOGUI_LOAD_ATTEMPTED = True
    try:
        output_buffer = io.StringIO()
        with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
            _module = importlib.import_module("pyautogui")

        _module.FAILSAFE = False
        _module.PAUSE = 0
        _PYAUTOGUI = _module
    except Exception as e:
        print(f"[警告] PyAutoGUI 不可用，坐标点击回退到元素点击: {e}")
        _PYAUTOGUI = None

    return _PYAUTOGUI


def _load_image_imports():
    """按需加载图像匹配依赖，失败时返回 None。"""
    global _IMAGE_IMPORTS, _IMAGE_LOAD_ATTEMPTED

    if _IMAGE_LOAD_ATTEMPTED:
        return _IMAGE_IMPORTS

    _IMAGE_LOAD_ATTEMPTED = True
    try:
        output_buffer = io.StringIO()
        with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
            cv2 = importlib.import_module("cv2")
            numpy = importlib.import_module("numpy")
            mss = importlib.import_module("mss").mss

        _IMAGE_IMPORTS = (cv2, numpy, mss)
    except Exception as e:
        print(f"[警告] 图像匹配依赖加载失败，跳过模板匹配: {e}")
        _IMAGE_IMPORTS = None

    return _IMAGE_IMPORTS


class BotDetectedException(Exception):
    """机器人检测异常 - 被Tidal检测为机器人时抛出"""
    pass


class TidalRegister:
    """Tidal注册器"""
    
    def __init__(self, driver, human_behavior, card_reader, config=None, step_recorder=None):
        self.driver = driver
        self.human = human_behavior
        self.card = card_reader
        self.config = config
        self.step_recorder = step_recorder
        
        self.email = None
        self.password = None
        self.username = None
        self.tidal_url = "https://tidal.com/"
        self.tidal_precheck_url = "https://link.tidal.com/RGZST"
        self.tidal_precheck_wait_seconds = 20
        self.primary_tidal_tab_handle = None
        self._last_day_key = None
        self._last_month_key = None
        self._last_year_press_count = None

    def _record_substep(self, step_name, note=""):
        if self.step_recorder:
            self.step_recorder.capture(step_name, driver=self.driver, note=note)

    def _click_first_matching_element(self, selectors=None, texts=None, tags=None, html_keywords=None):
        """通过元素定位兜底点击，作为坐标点击不可用时的回退方案。"""
        selectors = selectors or []
        texts = [text.lower() for text in (texts or [])]
        html_keywords = [keyword.lower() for keyword in (html_keywords or [])]
        tags = tags or ["button", "a"]

        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        self.human.human_click(element)
                        return True
            except Exception:
                continue

        for tag in tags:
            try:
                elements = self.driver.find_elements(By.TAG_NAME, tag)
                for element in elements:
                    if not element.is_displayed():
                        continue

                    element_text = (element.text or "").strip().lower()
                    inner_html = (element.get_attribute("innerHTML") or "").lower()

                    if texts and not any(text in element_text for text in texts):
                        if not html_keywords or not any(keyword in inner_html for keyword in html_keywords):
                            continue

                    self.human.human_click(element)
                    return True
            except Exception:
                continue

        return False

    def _pick_non_repeating(self, choices, attr_name):
        """尽量避免与上一次选择重复。"""
        previous = getattr(self, attr_name, None)
        candidates = [choice for choice in choices if choice != previous] or list(choices)
        selected = random.choice(candidates)
        setattr(self, attr_name, selected)
        return selected

    def _get_typing_ranges(self):
        char_delay = TYPE_DELAY_RANGES["tidal_input"]
        final_pause = TYPE_DELAY_RANGES["tidal_input_done"]
        return char_delay, final_pause

    def _get_template_scales(self, step_id):
        """为特定模板提供多尺度匹配，降低 DPI/缩放带来的误差。"""
        if step_id == "TD-00-ACCESS-RESTRICTED":
            return [0.75, 0.85, 0.95, 1.00, 1.05, 1.15, 1.25, 1.35]
        return [1.00]

    def _get_template_match_result(self, step_id):
        """返回模板匹配详情，包含分数、中心点和缩放比例。"""
        imports = _load_image_imports()
        if not imports:
            return None

        template_target = get_template_target(step_id)
        template_path = get_template_path(step_id)
        if not os.path.exists(template_path):
            print(f"[信息] 模板不存在，跳过 {step_id}: {template_path}")
            return None

        cv2, np, mss = imports

        try:
            with mss() as sct:
                screenshot = np.array(sct.grab(sct.monitors[1]))
                screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
                screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

            template = cv2.imread(template_path)
            if template is None:
                print(f"[警告] 模板读取失败: {template_path}")
                return None

            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

            best_score = -1.0
            best_loc = None
            best_size = None
            best_scale = 1.0

            for scale in self._get_template_scales(step_id):
                if scale == 1.0:
                    scaled_template = template_gray
                else:
                    scaled_width = max(1, int(template_gray.shape[1] * scale))
                    scaled_height = max(1, int(template_gray.shape[0] * scale))
                    if scaled_width >= screenshot_gray.shape[1] or scaled_height >= screenshot_gray.shape[0]:
                        continue
                    interpolation = cv2.INTER_LINEAR if scale > 1.0 else cv2.INTER_AREA
                    scaled_template = cv2.resize(
                        template_gray,
                        (scaled_width, scaled_height),
                        interpolation=interpolation,
                    )

                result = cv2.matchTemplate(screenshot_gray, scaled_template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                if max_val > best_score:
                    best_score = max_val
                    best_loc = max_loc
                    best_scale = scale
                    best_size = scaled_template.shape[:2]

            if best_loc is None or not best_size:
                return None

            print(
                f"[模板匹配] {step_id} -> {template_target.file_name}: {best_score:.3f} "
                f"(scale={best_scale:.2f})"
            )

            height, width = best_size
            center_x = best_loc[0] + width // 2
            center_y = best_loc[1] + height // 2
            return {
                "score": best_score,
                "center": (center_x, center_y),
                "scale": best_scale,
            }
        except Exception as e:
            print(f"[警告] 模板匹配失败 {step_id}: {e}")
            return None

    def _page_contains_keywords(self, keywords):
        """通过多种页面文本来源检查关键文案。"""
        normalized_keywords = [re.sub(r"\s+", "", keyword).lower() for keyword in keywords if keyword]
        text_sources = []

        def append_text(value):
            if not value:
                return
            normalized_value = re.sub(r"\s+", "", str(value)).lower()
            if normalized_value:
                text_sources.append(normalized_value)

        try:
            append_text(self.driver.title)
        except Exception:
            pass

        try:
            append_text(self.driver.current_url)
        except Exception:
            pass

        try:
            append_text(self.driver.find_element(By.TAG_NAME, "html").text)
        except Exception:
            pass

        try:
            append_text(self.driver.find_element(By.TAG_NAME, "body").text)
        except Exception:
            pass

        try:
            append_text(
                self.driver.execute_script(
                    "return document.body ? (document.body.innerText || document.body.textContent || '') : '';"
                )
            )
        except Exception:
            pass

        try:
            append_text(self.driver.page_source)
        except Exception:
            pass

        for source in text_sources:
            if any(keyword in source for keyword in normalized_keywords):
                return True

        return False

    def _match_template_on_screen(self, step_id):
        """返回模板在主屏幕中的中心坐标。"""
        match_result = self._get_template_match_result(step_id)
        if not match_result:
            return None

        template_target = get_template_target(step_id)
        if match_result["score"] < template_target.threshold:
            return None

        return match_result["center"]

    def _click_fixed_step(self, step_id, post_pause=(1.0, 2.0)):
        """点击固定坐标步骤。"""
        point = get_fixed_point(step_id)
        print(f"[步骤] {step_id} - {point.description}...")
        clicked = self.human.human_click_coordinate(point.x, point.y, post_pause_range=post_pause)
        if clicked:
            self._record_substep(f"{step_id}_{point.description}")
        return clicked

    def _click_template_step(self, step_id, post_pause=(1.0, 2.0)):
        """模板匹配后点击中心坐标，或点击模板配置中的固定坐标。"""
        target = get_template_target(step_id)
        matched_center = self._match_template_on_screen(step_id)
        if not matched_center:
            return False

        click_x = target.click_x if target.click_x is not None else matched_center[0]
        click_y = target.click_y if target.click_y is not None else matched_center[1]
        print(f"[步骤] {step_id} - {target.description}...")
        clicked = self.human.human_click_coordinate(click_x, click_y, post_pause_range=post_pause)
        if clicked:
            self._record_substep(f"{step_id}_{target.description}")
        return clicked

    def _focus_and_type_fixed_step(self, step_id, text):
        """点击固定坐标输入框并输入文本。"""
        char_delay, final_pause = self._get_typing_ranges()
        if not self._click_fixed_step(step_id, post_pause=(0.4, 0.8)):
            return False
        typed = self.human.human_type_text(
            text,
            min_delay=char_delay[0],
            max_delay=char_delay[1],
            final_pause_range=final_pause,
        )
        if typed:
            self._record_substep(f"{step_id}_输入完成", note=text)
        return typed

    def _focus_and_type_template_step(self, step_id, text):
        """点击模板中心输入框并输入文本。"""
        char_delay, final_pause = self._get_typing_ranges()
        if not self._click_template_step(step_id, post_pause=(0.4, 0.8)):
            return False
        typed = self.human.human_type_text(
            text,
            min_delay=char_delay[0],
            max_delay=char_delay[1],
            final_pause_range=final_pause,
        )
        if typed:
            self._record_substep(f"{step_id}_输入完成", note=text)
        return typed

    def _open_home_via_driver_get(self, wait_for_browser_ready=False, target_url=None, wait_seconds=None, step_note=None):
        """通过 driver.get 打开目标页面并等待。"""
        target_url = target_url or self.tidal_url
        wait_seconds = WAIT_SECONDS["TD-01-LOAD"] if wait_seconds is None else wait_seconds
        step_note = step_note or f"driver_get打开页面并等待{wait_seconds}秒"

        print(f"[步骤] 通过 driver.get 打开页面: {target_url}")

        if wait_for_browser_ready:
            time.sleep(WAIT_SECONDS["TD-00-BROWSER-READY"])

        self.driver.get(target_url)
        time.sleep(wait_seconds)
        self._record_substep(f"TD-PRE-01_{step_note}")
        return True

    def _open_primary_tidal_tab_after_precheck(self):
        """预检查通过后，新开 tidal.com 主流程标签页。"""
        print("[步骤] 预检查通过，新开 tidal.com 标签页...")

        original_handles = list(self.driver.window_handles)
        self.driver.execute_script("window.open('about:blank', '_blank');")
        time.sleep(0.5)

        latest_handles = list(self.driver.window_handles)
        new_handles = [handle for handle in latest_handles if handle not in original_handles]
        new_handle = new_handles[0] if new_handles else latest_handles[-1]

        self.driver.switch_to.window(new_handle)
        self.primary_tidal_tab_handle = new_handle
        self.driver.get(self.tidal_url)
        time.sleep(WAIT_SECONDS["TD-01-LOAD"])
        self._record_substep("TD-PRE-02_新开tidal主标签并等待10秒")
        return True

    def switch_to_primary_tidal_tab(self):
        """切回预检查后创建的主 Tidal 标签页。"""
        try:
            handles = self.driver.window_handles
            if self.primary_tidal_tab_handle and self.primary_tidal_tab_handle in handles:
                self.driver.switch_to.window(self.primary_tidal_tab_handle)
                return True
        except Exception:
            return False

        return False

    def _handle_home_popups(self):
        """按模板匹配依次处理翻译弹窗和 Cookie 弹窗。"""
        print("[步骤] 检查首页弹窗...")
        self._click_template_step("TD-01-TRANSLATION", post_pause=(0.5, 1.0))
        self._click_template_step("TD-01-COOKIES", post_pause=(0.5, 1.0))
        self._record_substep("TD-01_检查首页弹窗完成")

    def _is_access_restricted_screen(self):
        """检查首页是否命中访问受限模板或页面文案。"""
        match_result = self._get_template_match_result("TD-00-ACCESS-RESTRICTED")
        if match_result and match_result["score"] >= get_template_target("TD-00-ACCESS-RESTRICTED").threshold:
            return True

        restricted_keywords = [
            "访问暂时受限",
            "access temporarily restricted",
            "我不是机器人",
            "i'm not a robot",
            "系统侦测到您浏览网页的速度异常",
            "无法操作验证页面",
            "网路机器人相同",
        ]

        if self._page_contains_keywords(restricted_keywords):
            print("[信息] 通过页面文案检测到访问受限")
            return True

        if match_result:
            print(
                f"[信息] 访问受限模板未达到正式阈值，按正常页面继续: "
                f"{match_result['score']:.3f} < {get_template_target('TD-00-ACCESS-RESTRICTED').threshold:.3f}"
            )

        return False

    def ensure_home_access_ready(self):
        """先打开 Tidal 首页，如果访问受限则等待用户手动解决后继续。"""
        print("[步骤] 预检查 Tidal 首页访问状态...")
        self._open_home_via_driver_get(
            wait_for_browser_ready=True,
            target_url=self.tidal_precheck_url,
            wait_seconds=self.tidal_precheck_wait_seconds,
            step_note="link_tidal预检查并等待20秒",
        )
        self._record_substep("TD-00_link_tidal预检查等待20秒后待检查")

        while self._is_access_restricted_screen():
            self._record_substep("TD-00_检测到访问暂时受限")
            print("\n" + "=" * 60)
            print("   ⚠️ 检测到 Tidal 访问暂时受限")
            print("=" * 60)
            print("[提示] 请先在当前浏览器里手动完成验证或解除限制")
            print("[提示] 处理完成后，在程序里输入 y 再继续")
            print("=" * 60)

            user_input = input("请输入 y 继续复查：").strip().lower()
            if user_input != "y":
                print("[等待] 未输入 y，继续等待人工处理...")
                continue

            time.sleep(2)
            self._open_home_via_driver_get(
                wait_for_browser_ready=False,
                target_url=self.tidal_precheck_url,
                wait_seconds=self.tidal_precheck_wait_seconds,
                step_note="link_tidal人工处理后复查并等待20秒",
            )
            self._record_substep("TD-00_人工处理后重新检查link_tidal")

        self._open_primary_tidal_tab_after_precheck()
        self._handle_home_popups()
        self._simulate_human_page_view()
        self._record_substep("TD-00_Tidal首页访问正常")
        print("[成功] Tidal 首页访问正常")
        return True

    def _select_dropdown_by_template(self, step_id, key, presses=1):
        """模板匹配后点击下拉框，再按键确认选项。"""
        if not self._click_template_step(step_id, post_pause=(0.4, 0.6)):
            return False

        time.sleep(0.5)
        self.human.human_press_key(key, presses=presses, interval_range=(0.20, 0.30))
        time.sleep(0.5)
        self.human.human_press_key("enter", presses=1, interval_range=(0.20, 0.30))
        self._record_substep(f"{step_id}_下拉选择完成", note=f"key={key},presses={presses}")
        return True
    
    def generate_password(self, length=12):
        """生成随机密码"""
        chars = string.ascii_letters + string.digits + "!@#$"
        pwd = [
            random.choice(string.ascii_uppercase),
            random.choice(string.ascii_lowercase),
            random.choice(string.digits),
            random.choice("!@#$"),
        ]
        for _ in range(length - 4):
            pwd.append(random.choice(chars))
        random.shuffle(pwd)
        self.password = "Td" + ''.join(pwd)
        return self.password
    
    def generate_username(self):
        """生成随机用户名"""
        adj = ["Happy", "Lucky", "Cool", "Swift", "Brave"]
        noun = ["Music", "Wave", "Beat", "Sound", "Tune"]
        self.username = random.choice(adj) + random.choice(noun) + str(random.randint(100, 9999))
        return self.username
    
    # ========== 步骤1: 打开Tidal ==========
    def open_tidal(self):
        """打开Tidal网站 - 模拟真人访问"""
        print("[步骤] 打开Tidal网站...")
        
        # 增加随机延迟，模拟人类决策时间
        time.sleep(random.uniform(2, 4))
        
        max_retries = 3
        for attempt in range(max_retries):
            self.driver.get(self.tidal_url)

            # 首页固定等待 10 秒，随后检测翻译弹窗和 Cookie 弹窗
            time.sleep(WAIT_SECONDS["TD-01-LOAD"])
            self._handle_home_popups()
            self._simulate_human_page_view()
            
            # 检查页面是否正常加载
            page_ok = self._check_tidal_page()
            
            if page_ok:
                break
            elif attempt < max_retries - 1:
                print(f"[重试] 第{attempt + 2}次尝试...")
                time.sleep(random.uniform(5, 8))
        
        # 等待页面完全加载
        try:
            WebDriverWait(self.driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except:
            pass
        
        # 模拟人类阅读页面
        time.sleep(random.uniform(1.5, 3.0))
        self._simulate_human_page_view()
        
        print("[成功] Tidal页面已加载")
    
    def _simulate_human_page_view(self):
        """模拟人类查看页面的行为"""
        try:
            # 随机滚动
            scroll_y = random.randint(100, 400)
            self.driver.execute_script(f"window.scrollTo(0, {scroll_y});")
            time.sleep(random.uniform(0.5, 1.5))
            
            # 随机鼠标移动（通过JS）
            self.driver.execute_script("""
                var event = new MouseEvent('mousemove', {
                    clientX: Math.random() * window.innerWidth,
                    clientY: Math.random() * window.innerHeight
                });
                document.dispatchEvent(event);
            """)
            time.sleep(random.uniform(0.3, 0.8))
            
            # 偶尔滚回顶部
            if random.random() < 0.3:
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(random.uniform(0.5, 1))
        except:
            pass
    
    def _check_tidal_page(self):
        """检查Tidal页面是否正常加载"""
        # 先检查是否被机器人检测拦截
        if self._is_blocked_by_bot_detection():
            return False
        
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            page_source = self.driver.page_source.lower()
            
            # 检查是否有 captcha - 视为机器人检测
            if "captcha" in body_text or "captcha" in page_source:
                print("\n" + "=" * 60)
                print("   ⚠️ 检测到 CAPTCHA 验证！")
                print("=" * 60)
                print("[拦截] Tidal 要求人机验证")
                print("[停止] 程序将停止，但不关闭浏览器")
                print("[提示] 请手动完成验证后重新运行程序")
                print("=" * 60)
                raise BotDetectedException("检测到 CAPTCHA，程序停止")
            
            # 检查是否被其他方式拦截
            error_signs = [
                "geo.captcha", "意外终止", 
                "enable js", "ad blocker", "access denied",
                "blocked", "forbidden"
            ]
            
            for sign in error_signs:
                if sign in body_text or sign in page_source:
                    print(f"[警告] 检测到拦截: {sign}")
                    print("[信息] 刷新页面...")
                    self.driver.refresh()
                    time.sleep(8)
                    return False
            
            # 检查是否有Tidal特征元素
            if "tidal" in page_source or "music" in body_text:
                return True
            
            return True  # 默认认为正常
            
        except BotDetectedException:
            raise
        except Exception as e:
            print(f"[警告] 页面检查失败: {e}")
            return False
    
    def _is_blocked_by_bot_detection(self):
        """检查是否被机器人检测拦截"""
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            page_url = self.driver.current_url.lower()
            
            # 机器人检测页面的特征
            bot_detection_signs = [
                "访问暂时受限",
                "Access temporarily restricted",
                "我不是机器人",
                "I'm not a robot",
                "系统侦测到您浏览网页的速度异常",
                "IP位址",
                "网路机器人相同",
                "无法操作验证页面"
            ]
            
            for sign in bot_detection_signs:
                if sign in body_text:
                    print("\n" + "=" * 60)
                    print("   ⚠️ 检测到机器人拦截页面！")
                    print("=" * 60)
                    print(f"[拦截] 当前URL: {page_url}")
                    print(f"[拦截] 检测到: {sign}")
                    print("[停止] 程序将停止，但不关闭浏览器")
                    print("[提示] 您可以手动处理验证后重新运行程序")
                    print("=" * 60)
                    
                    # 抛出特殊异常终止程序
                    raise BotDetectedException("被检测为机器人，程序停止")
            
            return False
        except BotDetectedException:
            raise
        except:
            return False
    
    def check_bot_detection(self):
        """公开的机器人检测检查方法 - 在每个步骤后调用"""
        return self._is_blocked_by_bot_detection()
    
    def _handle_cookie_popup(self):
        """处理cookie弹窗 - 点击Accept"""
        print("[步骤] 检查cookie弹窗...")
        time.sleep(3)  # 等待弹窗出现
        
        # 优先点击 Accept 按钮
        try:
            accept_btn = self.driver.find_element(By.ID, "onetrust-accept-btn-handler")
            if accept_btn.is_displayed():
                self.human.human_click(accept_btn)
                print("[点击] Accept Cookie")
                time.sleep(2)
                return
        except:
            pass
        
        # 备用: 通过文本查找Accept按钮
        try:
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                if btn.is_displayed():
                    text = btn.text.lower()
                    btn_id = btn.get_attribute("id") or ""
                    # 优先Accept
                    if "accept" in text or "accept" in btn_id.lower():
                        self.human.human_click(btn)
                        print(f"[点击] Accept: {btn.text}")
                        time.sleep(2)
                        return
        except:
            pass
        
        print("[信息] 未发现cookie弹窗")
    
    # ========== 步骤2: 点击Create a free account ==========
    def click_create_account(self):
        """使用真实鼠标点击 Create a free account 按钮"""
        print("[步骤] 点击 Create a free account...")
        time.sleep(1)

        if self._click_fixed_step("OK-01", post_pause=(1.0, 2.0)):
            return True

        if self._click_first_matching_element(
            texts=["create a free account", "free account"],
            tags=["button", "a"],
            html_keywords=["free account"]
        ):
            print("[点击] Create a free account (元素兜底)")
            time.sleep(2)
            return True

        raise Exception("找不到Create a free account按钮")
    
    # ========== 步骤3: 选择邮箱注册 ==========
    def select_email_signup(self):
        """选择邮箱注册方式"""
        print("[步骤] 检查是否需要点击邮箱注册入口...")
        time.sleep(1)

        try:
            email_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[autocomplete='email']")
            if any(input_elem.is_displayed() for input_elem in email_inputs):
                print("[信息] 已进入邮箱输入页面，跳过邮箱注册入口点击")
                return True
        except Exception:
            pass
        
        # 查找邮箱注册按钮
        try:
            btns = self.driver.find_elements(By.CSS_SELECTOR, "button, a")
            for btn in btns:
                if btn.is_displayed():
                    text = btn.text.lower()
                    html = btn.get_attribute("innerHTML").lower()
                    if "email" in text or "email" in html or "mail" in text:
                        self.human.human_click(btn)
                        print("[点击] 邮箱注册按钮")
                        time.sleep(1)
                        return True
        except:
            pass
        
        print("[信息] 未找到邮箱选项，尝试继续...")
        return True
    
    # ========== 步骤4: 输入邮箱 ==========
    def enter_email(self, email):
        """输入邮箱"""
        print(f"[步骤] 输入邮箱: {email}")
        self.email = email
        time.sleep(0.5)

        if self._focus_and_type_fixed_step("TD-02", email):
            print("[填写] 邮箱输入完成（坐标）")
            return True
        
        # 查找邮箱输入框
        selectors = [
            "input[type='email']",
            "input[name='email']",
            "input[autocomplete='email']",
            "input[placeholder*='@']",
            "input[placeholder*='email']",
        ]
        
        for selector in selectors:
            try:
                input_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                if input_elem.is_displayed():
                    self.human.human_type(input_elem, email)
                    print("[填写] 邮箱输入完成")
                    return True
            except:
                continue
        
        raise Exception("找不到邮箱输入框")
    
    # ========== 步骤5: 点击继续 ==========
    def click_continue(self):
        """点击继续按钮 - 人类行为"""
        print("[步骤] 点击继续...")

        if self._click_fixed_step("TD-04", post_pause=(1.2, 2.0)):
            print("[点击] Continue 按钮（坐标）")
            return True
        
        # 人类在点击按钮前会思考
        self.human.think_pause()
        
        # 查找提交/继续按钮
        selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button.primary",
        ]
        
        for selector in selectors:
            try:
                btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                if btn.is_displayed() and btn.is_enabled():
                    self.human.human_click(btn)
                    print("[点击] 继续按钮")
                    # 点击后等待页面响应
                    time.sleep(random.uniform(2.5, 4.5))
                    return True
            except:
                continue
        
        # 通过文本查找
        try:
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                if btn.is_displayed() and btn.is_enabled():
                    self.human.human_click(btn)
                    print("[点击] 按钮")
                    time.sleep(random.uniform(2.5, 4.5))
                    return True
        except:
            pass
        
        raise Exception("找不到继续按钮")
    
    # ========== 步骤6: 输入密码 ==========
    def enter_password(self):
        """输入密码"""
        password = self.generate_password()
        print(f"[步骤] 设置密码: {password}")
        time.sleep(0.5)

        if self._focus_and_type_fixed_step("TD-05", password):
            print("[填写] 密码输入完成（坐标）")
            return True
        
        try:
            pwd_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
            for pwd_input in pwd_inputs:
                if pwd_input.is_displayed():
                    self.human.human_type(pwd_input, password)
                    break
            
            # 如果有确认密码框
            if len(pwd_inputs) > 1 and pwd_inputs[1].is_displayed():
                self.human.human_type(pwd_inputs[1], password)
            
            print("[填写] 密码输入完成")
            return True
        except:
            raise Exception("找不到密码输入框")
    
    # ========== 步骤7: 输入用户名（可选） ==========
    def enter_username(self):
        """输入用户名"""
        try:
            selectors = [
                "input[name='username']",
                "input[name='name']",
                "input[autocomplete='username']",
            ]
            
            for selector in selectors:
                try:
                    input_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if input_elem.is_displayed():
                        username = self.generate_username()
                        print(f"[步骤] 输入用户名: {username}")
                        self.human.human_type(input_elem, username)
                        return True
                except:
                    continue
        except:
            pass
        
        print("[信息] 未发现用户名输入框")
        return True
    
    # ========== 步骤8: 同意条款 ==========
    def accept_terms(self):
        """勾选条款"""
        try:
            checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox'], [role='checkbox']")
            for cb in checkboxes:
                if cb.is_displayed() and not cb.is_selected():
                    print("[步骤] 勾选条款...")
                    self.human.human_click(cb)
                    time.sleep(0.3)
        except:
            pass
        return True
    
    # ========== 步骤9: 填写出生日期 ==========
    def enter_birthday(self):
        """填写出生日期 - 完整人类模拟"""
        print("[步骤] 填写出生日期...")

        day_key = self._pick_non_repeating(DAY_KEYS, "_last_day_key")
        month_key = self._pick_non_repeating(MONTH_KEYS, "_last_month_key")
        year_press_count = self._pick_non_repeating(YEAR_PRESS_COUNTS, "_last_year_press_count")

        if self._select_dropdown_by_template("DOB-01", day_key, presses=1):
            print(f"[选择] Day: {day_key}")
            time.sleep(random.uniform(0.8, 1.3))

            if self._select_dropdown_by_template("DOB-02", month_key, presses=1):
                print(f"[选择] Month 首字母: {month_key}")
                time.sleep(random.uniform(0.8, 1.3))

                if self._select_dropdown_by_template("DOB-03", "1", presses=year_press_count):
                    print(f"[选择] Year 向下次数: {year_press_count}")
                    time.sleep(random.uniform(1.0, 1.5))
                    print("[完成] 出生日期填写完成（模板 + 键盘）")
                    return True
        
        # 人类会先看一下页面
        self.human.think_pause()
        
        # 检查是否有出生日期字段
        try:
            day_select = self.driver.find_element(By.CSS_SELECTOR, "select#tbi-day, select[id*='day']")
            if not day_select.is_displayed():
                print("[信息] 未发现出生日期页面")
                return True
        except:
            print("[信息] 未发现出生日期页面")
            return True
        
        # 生成随机出生日期 (18-35岁)
        year = random.randint(1990, 2005)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        
        # 人类在填写表单前会先看一眼整个表单
        self.human.random_mouse_movement()
        time.sleep(random.uniform(1.5, 3.0))
        
        # 选择Day - 人类选择下拉框的完整行为
        print("[步骤] 选择 Day...")
        try:
            day_elem = self.driver.find_element(By.CSS_SELECTOR, "select#tbi-day, select[id*='day']")
            self.human.human_select(day_elem, value=str(day))
            print(f"[选择] Day: {day}")
            
            # 选择后人类会稍微停顿确认
            time.sleep(random.uniform(1.5, 3.0))
        except Exception as e:
            print(f"[警告] Day选择失败: {e}")
        
        # 移动到Month前的自然延迟
        self.human.random_mouse_movement()
        time.sleep(random.uniform(1.0, 2.5))
        
        # 选择Month
        print("[步骤] 选择 Month...")
        try:
            month_elem = self.driver.find_element(By.CSS_SELECTOR, "select#tbi-month, select[id*='month']")
            self.human.human_select(month_elem, value=str(month))
            print(f"[选择] Month: {month}")
            
            time.sleep(random.uniform(1.5, 3.0))
        except Exception as e:
            print(f"[警告] Month选择失败: {e}")
        
        # 移动到Year前的自然延迟
        self.human.random_mouse_movement()
        time.sleep(random.uniform(1.0, 2.5))
        
        # 选择Year
        print("[步骤] 选择 Year...")
        try:
            year_elem = self.driver.find_element(By.CSS_SELECTOR, "select#tbi-year, select[id*='year']")
            self.human.human_select(year_elem, value=str(year))
            print(f"[选择] Year: {year}")
            
            time.sleep(random.uniform(1.5, 3.0))
        except Exception as e:
            print(f"[警告] Year选择失败: {e}")
        
        # 填写完成后人类会检查一遍
        self.human.think_pause()
        print(f"[完成] 出生日期: {year}-{month:02d}-{day:02d}")
        
        # 图像匹配检查（图1）
        self._check_birthday_page_image()
        
        return True
    
    def _check_birthday_page_image(self):
        """匹配图1，如果匹配失败则点击指定坐标"""
        imports = _load_image_imports()
        pyautogui = _load_pyautogui()
        
        print("[步骤] 检查页面图像匹配...")

        if not imports:
            print("[信息] 图像匹配依赖不可用，跳过模板匹配")
            return True

        cv2, np, mss = imports
        
        try:
            # 截图
            with mss() as sct:
                screenshot = np.array(sct.grab(sct.monitors[1]))
                screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
            
            # 尝试加载图1 (images/birthday_check.png)
            template_path = os.path.join(os.path.dirname(__file__), '..', 'images', 'birthday_check.png')
            if os.path.exists(template_path):
                template = cv2.imread(template_path)
                if template is not None:
                    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
                    max_val = np.max(result)
                    print(f"[图像匹配] 阈值: {max_val:.3f}")
                    
                    if max_val >= 0.9:
                        print("[图像匹配] 匹配成功，继续执行")
                        return True
                    else:
                        if not pyautogui:
                            print("[警告] PyAutoGUI 不可用，无法执行生日页兜底坐标点击")
                            return False

                        print("[图像匹配] 匹配失败，点击坐标 (580, 655)")
                        pyautogui.moveTo(580, 655, duration=0.3)
                        time.sleep(0.2)
                        pyautogui.click()
                        time.sleep(1)
                        return False
                else:
                    print("[警告] 无法加载图1，跳过图像匹配")
                    return True
            else:
                print(f"[信息] 图1不存在: {template_path}，跳过图像匹配")
                return True
        except Exception as e:
            print(f"[警告] 图像匹配失败: {e}")
            return True
    
    # ========== 步骤10: 点击 Sign up 按钮 ==========
    def click_signup_button(self):
        """使用真实鼠标点击勾选条款，然后点击 Sign up 按钮"""
        print("[步骤] 使用真实鼠标点击勾选条款...")
        time.sleep(1)

        if not self._click_fixed_step("OK-03", post_pause=(0.4, 0.8)):
            self.accept_terms()
        
        # 等待3秒，让Sign up按钮被点亮
        print("[等待] 等待Sign up按钮点亮...")
        time.sleep(3)
        
        print("[步骤] 点击 Sign up 按钮...")

        if self._click_fixed_step("OK-04", post_pause=(2.5, 3.5)):
            print("[成功] Sign up 完成")
            return True

        if self._click_first_matching_element(
            selectors=["button[type='submit']", "button.primary", "button"],
            texts=["sign up", "create account"],
            tags=["button", "a"]
        ):
            print("[点击] Sign up 按钮 (元素兜底)")
            time.sleep(3)
            print("[成功] Sign up 完成")
            
        return True
    
    # ========== 步骤11: 点击头像进入订阅 ==========
    def click_profile_menu(self):
        """使用真实鼠标点击右上角头像图标"""
        print("[步骤] 点击头像图标...")
        time.sleep(2)

        if self._click_fixed_step("OK-05", post_pause=(1.0, 2.0)):
            return True

        if self._click_first_matching_element(
            selectors=[
                "button[aria-label*='profile']",
                "button[aria-label*='account']",
                "button[aria-haspopup='menu']",
                "[class*='avatar']",
                "[data-test*='avatar']"
            ],
            texts=["profile", "account"],
            tags=["button", "a", "div"]
        ):
            print("[点击] 头像图标 (元素兜底)")
            time.sleep(2)
            return True

        return False
    
    def click_manage_subscription(self):
        """使用真实鼠标点击管理订阅 - 会打开新标签页"""
        print("[步骤] 点击 Manage subscription...")
        time.sleep(1)
        
        # 记录当前标签页数量
        current_handles = len(self.driver.window_handles)
        print(f"[信息] 当前标签页数: {current_handles}")
        
        if not self._click_fixed_step("OK-06", post_pause=(1.0, 2.0)):
            if not self._click_first_matching_element(
                texts=["manage subscription", "subscription"],
                tags=["button", "a"]
            ):
                return False
            print("[点击] Manage subscription (元素兜底)")
        
        # 等待新标签页打开
        time.sleep(3)
        
        # 检查是否打开了新标签页
        new_handles = len(self.driver.window_handles)
        print(f"[信息] 现在标签页数: {new_handles}")
        
        if new_handles > current_handles:
            # 切换到新标签页
            self.driver.switch_to.window(self.driver.window_handles[-1])
            print(f"[切换] 已切换到新标签页")
            print(f"[当前URL] {self.driver.current_url}")
        else:
            print(f"[信息] 未打开新标签页，当前URL: {self.driver.current_url}")
        
        time.sleep(2)
        return True
    
    def login_for_subscription(self):
        """订阅页面重新登录 - Sign up or log in 页面"""
        print("[步骤] 订阅页面登录...")
        time.sleep(5)  # 等待页面加载

        if self._focus_and_type_fixed_step("SUB-01", self.email):
            print(f"[填写] 邮箱: {self.email}")
            if self._click_fixed_step("SUB-02", post_pause=(1.0, 1.4)):
                print("[点击] Continue")
                time.sleep(3)

                if self._focus_and_type_fixed_step("SUB-03", self.password):
                    print(f"[填写] 密码: {self.password}")
                    if self._click_fixed_step("SUB-04", post_pause=(1.0, 1.4)):
                        print("[点击] Log In")
                        time.sleep(5)
                        print("[成功] 订阅页面登录完成（坐标）")
                        return True
        
        # 第一步：输入邮箱
        print("[步骤] 输入邮箱...")
        email_entered = False
        
        # 等待邮箱输入框出现
        for _ in range(10):
            try:
                email_input = self.driver.find_element(By.CSS_SELECTOR, "input#email, input[name='email'], input[type='username']")
                if email_input.is_displayed():
                    print(f"[填写] 邮箱: {self.email}")
                    self.human.human_type(email_input, self.email)
                    email_entered = True
                    break
            except:
                time.sleep(1)
        
        if not email_entered:
            print("[警告] 未找到邮箱输入框")
            return False
        
        # 点击 Continue 按钮
        print("[步骤] 点击 Continue...")
        time.sleep(1)
        
        try:
            # 方法1: 通过ui-test-id
            btn = self.driver.find_element(By.CSS_SELECTOR, "button[ui-test-id='check-user-continue-button']")
            if btn.is_displayed():
                self.human.human_click(btn)
                print("[点击] Continue")
        except:
            # 方法2: 通过type=submit
            try:
                btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                if btn.is_displayed():
                    self.human.human_click(btn)
                    print("[点击] Submit")
            except:
                pass
        
        time.sleep(3)  # 等待密码页面加载
        
        # 第二步：输入密码
        print("[步骤] 输入密码...")
        password_entered = False
        
        # 等待密码输入框出现
        for _ in range(10):
            try:
                pwd_input = self.driver.find_element(By.CSS_SELECTOR, "input#password, input[name='password'], input[type='password']")
                if pwd_input.is_displayed():
                    print(f"[填写] 密码: {self.password}")
                    self.human.human_type(pwd_input, self.password)
                    password_entered = True
                    break
            except:
                time.sleep(1)
        
        if not password_entered:
            print("[警告] 未找到密码输入框")
            return False
        
        # 点击 Log In 按钮
        print("[步骤] 点击 Log In...")
        time.sleep(1)
        
        try:
            # 方法1: 通过ui-test-id
            btn = self.driver.find_element(By.CSS_SELECTOR, "button[ui-test-id='login-user-login-button']")
            if btn.is_displayed():
                self.human.human_click(btn)
                print("[点击] Log In")
        except:
            # 方法2: 通过type=submit
            try:
                btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                if btn.is_displayed():
                    self.human.human_click(btn)
                    print("[点击] Submit")
            except:
                pass
        
        time.sleep(5)  # 等待登录完成
        
        print("[成功] 订阅页面登录完成")
        return True
    
    # ========== 步骤12: 点击 View Plans ==========
    def click_view_plans(self):
        """点击 View Plans 按钮"""
        print("[步骤] 点击 View Plans...")
        time.sleep(3)

        if self._click_fixed_step("PLAN-01", post_pause=(0.8, 1.2)):
            print("[点击] View Plans（坐标）")
            time.sleep(WAIT_SECONDS["PLAN-01"])
            return True
        
        # 方法1: 通过文本查找
        try:
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                if btn.is_displayed() and "view plan" in btn.text.lower():
                    self.human.human_click(btn)
                    print("[点击] View Plans")
                    time.sleep(3)
                    return True
        except:
            pass
        
        # 方法2: 通过链接查找
        try:
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                if link.is_displayed() and "view plan" in link.text.lower():
                    self.human.human_click(link)
                    print("[点击] View Plans link")
                    time.sleep(3)
                    return True
        except:
            pass
        
        print("[警告] 未找到 View Plans 按钮")
        return False
    
    # ========== 步骤13: 选择订阅计划 ==========
    def select_subscription(self):
        """选择订阅计划并点击 Continue"""
        print("[步骤] 选择订阅计划...")
        time.sleep(3)
        
        # 默认已选择 Individual，直接点击 Continue
        print("[信息] 默认选择 Individual 计划")

        if self._click_fixed_step("PLAN-02", post_pause=(0.8, 1.2)):
            print("[点击] Continue（坐标）")
            time.sleep(WAIT_SECONDS["PLAN-02"])
            return True
        
        # 点击 Continue 按钮
        try:
            btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], button.btn-light")
            if btn.is_displayed():
                self.human.human_click(btn)
                print("[点击] Continue")
                time.sleep(3)
                return True
        except:
            pass
        
        # 备用: 通过文本查找
        try:
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                if btn.is_displayed() and "continue" in btn.text.lower():
                    self.human.human_click(btn)
                    print("[点击] Continue")
                    time.sleep(3)
                    return True
        except:
            pass
        
        return True
    
    # ========== 步骤14: 填写支付信息 ==========
    def fill_payment(self):
        """填写支付信息 - Card Details 页面"""
        print("[步骤] 填写支付信息...")
        time.sleep(3)
        
        # 1. 填写 Full Name（主页面）
        print("[步骤] 填写 Full Name...")
        full_name = self.card.get_full_name()
        if self._focus_and_type_template_step("PAY-01", full_name):
            print(f"[填写] Full Name: {full_name}（模板）")
        else:
            try:
                name_input = self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='Full Name']")
                if name_input.is_displayed():
                    self.human.human_type(name_input, full_name)
                    print(f"[填写] Full Name: {full_name}")
            except Exception as e:
                print(f"[警告] Full Name 填写失败: {e}")
        
        time.sleep(1)
        
        # 2. 填写 Card Number（在 iframe 中）
        print("[步骤] 填写 Card Number...")
        card_num = self.card.get_card_number()
        if self._focus_and_type_template_step("PAY-02", card_num):
            print(f"[填写] Card Number: ****{card_num[-4:]}（模板）")
        else:
            try:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    title = iframe.get_attribute("title") or ""
                    if "card number" in title.lower():
                        self.driver.switch_to.frame(iframe)
                        print("[切换] 进入 Card Number iframe")
                        card_input = self.driver.find_element(By.CSS_SELECTOR, "input#encryptedCardNumber, input[data-fieldtype='encryptedCardNumber']")
                        self.human.human_type(card_input, card_num)
                        print(f"[填写] Card Number: ****{card_num[-4:]}")
                        self.driver.switch_to.default_content()
                        break
            except Exception as e:
                print(f"[警告] Card Number 填写失败: {e}")
                self.driver.switch_to.default_content()
        
        time.sleep(1)
        
        # 3. 填写 Exp. Date（在 iframe 中）
        print("[步骤] 填写 Exp. Date...")
        expiry = self.card.get_expiry()
        expiry_digits = ''.join(char for char in expiry if char.isdigit())[:4]
        if self._focus_and_type_template_step("PAY-03", expiry_digits):
            print(f"[填写] Exp. Date: {expiry_digits}（模板）")
        else:
            try:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    title = iframe.get_attribute("title") or ""
                    if "expiry" in title.lower():
                        self.driver.switch_to.frame(iframe)
                        print("[切换] 进入 Expiry Date iframe")
                        exp_input = self.driver.find_element(By.CSS_SELECTOR, "input#encryptedExpiryDate, input[data-fieldtype='encryptedExpiryDate']")
                        self.human.human_type(exp_input, expiry)
                        print(f"[填写] Exp. Date: {expiry}")
                        self.driver.switch_to.default_content()
                        break
            except Exception as e:
                print(f"[警告] Exp. Date 填写失败: {e}")
                self.driver.switch_to.default_content()
        
        time.sleep(1)
        
        # 4. 填写 CVC（可能在 iframe 中）
        print("[步骤] 填写 CVC...")
        cvv = self.card.get_cvv()
        if self._focus_and_type_template_step("PAY-04", cvv):
            print(f"[填写] CVC: {cvv}（模板）")
        else:
            try:
                cvc_input = self.driver.find_element(By.CSS_SELECTOR, "input#encryptedSecurityCode")
                self.human.human_type(cvc_input, cvv)
                print(f"[填写] CVC: {cvv}")
            except:
                try:
                    iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                    for iframe in iframes:
                        title = iframe.get_attribute("title") or ""
                        if "cvc" in title.lower() or "security" in title.lower():
                            self.driver.switch_to.frame(iframe)
                            print("[切换] 进入 CVC iframe")
                            cvc_input = self.driver.find_element(By.CSS_SELECTOR, "input#encryptedSecurityCode, input[data-fieldtype='encryptedSecurityCode']")
                            self.human.human_type(cvc_input, cvv)
                            print(f"[填写] CVC: {cvv}")
                            self.driver.switch_to.default_content()
                            break
                except Exception as e:
                    print(f"[警告] CVC 填写失败: {e}")
                    self.driver.switch_to.default_content()
        
        time.sleep(1)
        
        # 5. 填写 ZIP Code（主页面）- 只在美国/加拿大地区才需要
        print("[步骤] 检查是否需要填写 ZIP Code...")
        zip_code = self.card.get_zip_code()
        if zip_code and self._focus_and_type_template_step("PAY-05", zip_code):
            print(f"[填写] ZIP Code: {zip_code}（模板）")
        else:
            try:
                zip_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input#postalCode, input[name='postalCode']")
                if zip_inputs and zip_inputs[0].is_displayed():
                    self.human.human_type(zip_inputs[0], zip_code)
                    print(f"[填写] ZIP Code: {zip_code}")
                else:
                    print("[信息] 当前地区不需要填写 ZIP Code，跳过")
            except:
                print("[信息] 未找到 ZIP Code 输入框，跳过")
        
        time.sleep(1)
        
        # 6. 勾选自动续费同意复选框
        print("[步骤] 勾选同意复选框...")
        checkbox_clicked = False

        self.human.human_scroll_wheel(SCROLL_STEPS["PAY-06"], direction='down')
        if self._click_template_step("PAY-06", post_pause=(0.4, 0.8)):
            checkbox_clicked = True
        
        # 方法1: 通过复选框ID点击
        if not checkbox_clicked:
            try:
                checkbox_selectors = [
                    "input#autoRenewalConsentCreditCard1",  # 实际ID带数字后缀
                    "input#autoRenewalConsentCreditCard",
                    "input[name='autoRenewalConsentCreditCard']",
                    "input[type='checkbox'][id*='autoRenewal']",
                    "input[type='checkbox'][name*='Consent']"
                ]
                for sel in checkbox_selectors:
                    try:
                        checkbox = self.driver.find_element(By.CSS_SELECTOR, sel)
                        if checkbox.is_displayed() and not checkbox.is_selected():
                            self.driver.execute_script("arguments[0].click();", checkbox)
                            print(f"[勾选] 复选框 ({sel})")
                            checkbox_clicked = True
                            time.sleep(0.5)
                            break
                    except:
                        continue
            except Exception as e:
                print(f"[警告] 方法1失败: {e}")
        
        # 方法2: 通过点击 label 来勾选
        if not checkbox_clicked:
            try:
                label_selectors = [
                    "label[for='autoRenewalConsentCreditCard1']",
                    "label[for='autoRenewalConsentCreditCard']",
                    "label.form-style-links",
                    "label[for*='autoRenewal']"
                ]
                for sel in label_selectors:
                    try:
                        label = self.driver.find_element(By.CSS_SELECTOR, sel)
                        if label.is_displayed():
                            self.driver.execute_script("arguments[0].click();", label)
                            print(f"[勾选] 通过label点击 ({sel})")
                            checkbox_clicked = True
                            time.sleep(0.5)
                            break
                    except:
                        continue
            except Exception as e:
                print(f"[警告] 方法2失败: {e}")
        
        # 方法3: 通过包含文字的div/label点击
        if not checkbox_clicked:
            try:
                # 查找包含 "I consent" 文字的元素
                elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'I consent')]")
                for elem in elements:
                    if elem.is_displayed():
                        self.driver.execute_script("arguments[0].click();", elem)
                        print("[勾选] 通过文字定位点击")
                        checkbox_clicked = True
                        time.sleep(0.5)
                        break
            except Exception as e:
                print(f"[警告] 方法3失败: {e}")
        
        if not checkbox_clicked:
            print("[警告] 未能勾选复选框，请检查页面")
        
        print("[成功] 支付信息填写完成")
        return True
    
    # ========== 步骤15: 提交支付 ==========
    def submit_payment(self):
        """点击 Continue 提交支付"""
        print("[步骤] 提交支付...")
        time.sleep(2)

        if self._click_template_step("PAY-07", post_pause=(0.8, 1.2)):
            time.sleep(WAIT_SECONDS["PAY-07"])
            print("[成功] 支付提交完成（模板）")
            return True
        
        # 查找 Continue 按钮
        btn = None
        btn_selectors = [
            "button[type='submit']",
            "button.btn-primary",
            "button.btn-light",
            "button[type='submit'].btn-primary",
            "button[type='submit'].btn-light"
        ]
        
        for sel in btn_selectors:
            try:
                btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                if btn.is_displayed() and "continue" in btn.text.lower():
                    break
            except:
                continue
        
        # 备用: 通过文本查找
        if not btn:
            try:
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for b in buttons:
                    if b.is_displayed() and "continue" in b.text.lower():
                        btn = b
                        break
            except:
                pass
        
        if not btn:
            print("[错误] 未找到 Continue 按钮")
            return False
        
        # 等待按钮可点击
        for i in range(20):
            if btn.is_enabled():
                break
            print("[等待] 按钮未激活...")
            time.sleep(1)
        
        if btn.is_enabled():
            self.human.human_click(btn)
            print("[点击] Continue 提交")
            time.sleep(5)
            print("[成功] 支付提交完成")
            return True
        else:
            print("[错误] Continue 按钮仍未激活，请检查表单是否填写完整")
            return False
    
    # ========== 步骤16: 取消订阅 ==========
    def cancel_subscription(self):
        """取消订阅流程"""
        print("[步骤] 开始取消订阅...")
        
        # 1. 打开 profile 页面
        print("[步骤] 打开 Profile 页面...")
        self.driver.get("https://account.tidal.com/profile")
        time.sleep(5)

        if "account.tidal.com/profile" in self.driver.current_url.lower():
            self.human.human_scroll_wheel(SCROLL_STEPS["CAN-01"], direction='down')
            if self._click_template_step("CAN-01", post_pause=(0.8, 1.2)):
                time.sleep(WAIT_SECONDS["CAN-01"])

                self.human.human_scroll_wheel(SCROLL_STEPS["CAN-02"], direction='down')
                if self._click_template_step("CAN-02", post_pause=(0.8, 1.2)):
                    time.sleep(WAIT_SECONDS["CAN-02"])

                    self.human.human_scroll_wheel(SCROLL_STEPS["CAN-03"], direction='down')
                    if self._click_template_step("CAN-03", post_pause=(0.8, 1.2)):
                        time.sleep(WAIT_SECONDS["CAN-03"])
                        print("[完成] 取消订阅流程完成（模板）")
                        return True
        
        # 2. 点击 Subscription 链接
        print("[步骤] 点击 Subscription...")
        try:
            sub_link = self.driver.find_element(By.CSS_SELECTOR, "a[href='/subscription']")
            if sub_link.is_displayed():
                self.human.human_click(sub_link)
                print("[点击] Subscription")
                time.sleep(3)
        except:
            # 备用: 通过文本查找
            try:
                links = self.driver.find_elements(By.TAG_NAME, "a")
                for link in links:
                    if link.is_displayed() and "subscription" in link.text.lower():
                        self.human.human_click(link)
                        print(f"[点击] {link.text}")
                        time.sleep(3)
                        break
            except:
                pass
        
        # 3. 点击 Cancel subscription 链接
        print("[步骤] 点击 Cancel subscription...")
        time.sleep(2)
        try:
            cancel_link = self.driver.find_element(By.CSS_SELECTOR, "a[href='/subscription/cancel']")
            if cancel_link.is_displayed():
                self.human.human_click(cancel_link)
                print("[点击] Cancel subscription")
                time.sleep(3)
        except:
            # 备用: 通过文本查找
            try:
                links = self.driver.find_elements(By.TAG_NAME, "a")
                for link in links:
                    if link.is_displayed() and "cancel" in link.text.lower():
                        self.human.human_click(link)
                        print(f"[点击] {link.text}")
                        time.sleep(3)
                        break
            except:
                pass
        
        # 4. 点击 Continue Cancellation 按钮（第一次）
        print("[步骤] 点击 Continue Cancellation...")
        time.sleep(2)
        self._click_continue_cancellation()
        
        # 5. 点击 Continue Cancellation 按钮（第二次，可选）
        print("[步骤] 检查是否需要再次确认...")
        time.sleep(2)
        self._click_continue_cancellation()
        
        # 6. 验证取消成功
        time.sleep(3)
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            if "cancelled" in body_text or "取消" in body_text:
                print("[成功] 订阅已取消")
                return True
        except:
            pass
        
        print("[完成] 取消订阅流程完成")
        return True
    
    def _click_continue_cancellation(self):
        """点击 Continue Cancellation 按钮"""
        try:
            # 方法1: 通过href查找
            btn = self.driver.find_element(By.CSS_SELECTOR, "a[href*='cancel-confirm'], a[href*='cancel'].btn-secondary")
            if btn.is_displayed():
                self.human.human_click(btn)
                print("[点击] Continue Cancellation")
                time.sleep(3)
                return True
        except:
            pass
        
        try:
            # 方法2: 通过class查找
            btns = self.driver.find_elements(By.CSS_SELECTOR, ".btn-secondary, button.btn-secondary")
            for btn in btns:
                if btn.is_displayed():
                    text = btn.text.lower()
                    if "continue" in text and "cancel" in text:
                        self.human.human_click(btn)
                        print("[点击] Continue Cancellation")
                        time.sleep(3)
                        return True
        except:
            pass
        
        try:
            # 方法3: 通过文本查找
            elements = self.driver.find_elements(By.CSS_SELECTOR, "a, button")
            for elem in elements:
                if elem.is_displayed():
                    text = elem.text.lower()
                    if "continue" in text and "cancel" in text:
                        self.human.human_click(elem)
                        print(f"[点击] {elem.text}")
                        time.sleep(3)
                        return True
        except:
            pass
        
        print("[信息] 未找到 Continue Cancellation 按钮")
        return False
    
    # ========== 保存账号 ==========
    def save_account(self, file_path):
        """保存账号信息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp} | Email: {self.email} | Password: {self.password}\n"
        
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(line)
        
        print(f"[成功] 账号已保存")
        print(f"[账号] {self.email}")
        print(f"[密码] {self.password}")
    
    # ========== 完整注册流程 ==========
    def perform_registration(self, email, skip_open=False):
        """执行注册流程"""
        try:
            if not skip_open:
                self.ensure_home_access_ready()
            self.click_create_account()
            self.select_email_signup()
            self.enter_email(email)
            self.click_continue()
            self.enter_password()
            self.click_continue()
            # 填写出生日期并点击 Sign up
            self.enter_birthday()
            self.click_signup_button()
            print("[成功] 注册步骤完成")
            return True
        except Exception as e:
            print(f"[错误] 注册失败: {e}")
            raise
    
    def enter_subscription_page(self):
        """进入订阅页面（Sign up后）"""
        try:
            print("[步骤] 进入订阅页面...")
            time.sleep(3)
            
            # 1. 点击右上角头像
            self.click_profile_menu()
            
            # 2. 点击 Manage subscription
            self.click_manage_subscription()
            
            # 3. 重新登录
            self.login_for_subscription()
            
            print("[成功] 已进入订阅页面")
            return True
        except Exception as e:
            print(f"[错误] 进入订阅页面失败: {e}")
            raise
    
    def perform_subscription(self):
        """执行订阅流程"""
        try:
            self.select_subscription()
            self.fill_payment()
            self.submit_payment()
            return True
        except Exception as e:
            print(f"[错误] 订阅失败: {e}")
            raise
