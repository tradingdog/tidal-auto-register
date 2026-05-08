# -*- coding: utf-8 -*-
"""
人类行为仿真模块 - PyAutoGUI版本
使用系统级鼠标/键盘控制，更难被检测
"""

import random
import time
import math
import os
import io
import importlib
from contextlib import redirect_stderr, redirect_stdout

# 配置：是否使用 PyAutoGUI（可通过环境变量 USE_PYAUTOGUI=0 禁用）
ENABLE_PYAUTOGUI = os.environ.get('USE_PYAUTOGUI', '1') != '0'

# 使用PyAutoGUI进行系统级鼠标控制
USE_PYAUTOGUI = False
PYAUTOGUI_IMPORT_ERROR = None
if ENABLE_PYAUTOGUI:
    try:
        output_buffer = io.StringIO()
        with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
            pyautogui = importlib.import_module("pyautogui")
        pyautogui.FAILSAFE = False  # 禁用安全模式
        pyautogui.PAUSE = 0  # 禁用默认暂停
        USE_PYAUTOGUI = True
        print("[信息] 已加载 PyAutoGUI 系统级鼠标控制")
    except Exception as e:
        PYAUTOGUI_IMPORT_ERROR = e
        print(f"[警告] PyAutoGUI 加载失败，回退到 Selenium 鼠标控制: {e}")
else:
    print("[信息] PyAutoGUI 已禁用（环境变量 USE_PYAUTOGUI=0）")

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


class HumanBehavior:
    """完整人类行为仿真器 - 模拟真实人类操作的所有细节"""
    
    def __init__(self, driver, config=None):
        self.driver = driver
        self.config = config
        
        # 人类打字速度（每秒2-4个字符，带变化）
        self.typing_min_delay = 0.18
        self.typing_max_delay = 0.45
        
        # 人类点击延迟（思考+反应时间）
        self.click_delay_min = 1.5
        self.click_delay_max = 3.5
        
        # 下拉框选择延迟
        self.select_delay_min = 1.0
        self.select_delay_max = 2.5
        
        # 操作之间的思考时间
        self.think_delay_min = 2.0
        self.think_delay_max = 5.0
        
        if config:
            self.typing_min_delay = getattr(config, 'TYPING_MIN_DELAY', self.typing_min_delay)
            self.typing_max_delay = getattr(config, 'TYPING_MAX_DELAY', self.typing_max_delay)
    
    # ==================== 延迟方法 ====================
    
    def random_delay(self, min_sec=2.0, max_sec=5.0):
        """随机延迟 - 模拟人类思考时间"""
        delay = random.uniform(min_sec, max_sec)
        
        # 30%概率增加额外延迟（模拟分心/思考/犹豫）
        if random.random() < 0.30:
            delay += random.uniform(2.0, 5.0)
        
        # 10%概率有更长的停顿（模拟被其他事情打断）
        if random.random() < 0.10:
            delay += random.uniform(3.0, 8.0)
        
        time.sleep(delay)
    
    def micro_delay(self):
        """微延迟 - 模拟手指移动时间"""
        time.sleep(random.uniform(0.05, 0.15))
    
    def short_delay(self):
        """短延迟 - 快速反应"""
        self.random_delay(1.5, 3.0)
    
    def medium_delay(self):
        """中等延迟 - 正常操作"""
        self.random_delay(3.0, 6.0)
    
    def long_delay(self):
        """长延迟 - 需要思考"""
        self.random_delay(5.0, 10.0)
    
    def think_pause(self):
        """思考停顿 - 在重要操作前"""
        delay = random.uniform(self.think_delay_min, self.think_delay_max)
        
        # 模拟人类看屏幕思考
        if random.random() < 0.4:
            self._simulate_reading()
        
        time.sleep(delay)
    
    def hesitation(self):
        """犹豫 - 在点击前的短暂迟疑"""
        time.sleep(random.uniform(0.3, 1.2))
    
    # ==================== 鼠标行为 ====================
    
    def _bezier_point(self, t, p0, p1, p2, p3):
        """计算三次贝塞尔曲线上的点"""
        return (
            (1-t)**3 * p0 + 
            3 * (1-t)**2 * t * p1 + 
            3 * (1-t) * t**2 * p2 + 
            t**3 * p3
        )
    
    def _add_hand_tremor(self, x, y):
        """添加手部微颤抖"""
        # 人手握鼠标时会有轻微抖动
        tremor_x = random.gauss(0, 1.5)  # 高斯分布的微小偏移
        tremor_y = random.gauss(0, 1.5)
        return x + tremor_x, y + tremor_y
    
    def _generate_human_path(self, start_x, start_y, end_x, end_y):
        """生成人类鼠标移动路径（带抖动和速度变化）"""
        # 控制点随机偏移（人不会走直线）
        ctrl1_x = start_x + (end_x - start_x) * random.uniform(0.2, 0.4) + random.uniform(-80, 80)
        ctrl1_y = start_y + (end_y - start_y) * random.uniform(0.2, 0.4) + random.uniform(-80, 80)
        ctrl2_x = start_x + (end_x - start_x) * random.uniform(0.6, 0.8) + random.uniform(-50, 50)
        ctrl2_y = start_y + (end_y - start_y) * random.uniform(0.6, 0.8) + random.uniform(-50, 50)
        
        # 根据距离计算点数
        distance = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
        num_points = max(15, min(80, int(distance / 8)))
        
        path = []
        for i in range(num_points + 1):
            t = i / num_points
            
            # 速度变化（开始慢，中间快，结束慢）
            if t < 0.2:
                t = t * 0.7  # 开始慢
            elif t > 0.8:
                t = 0.8 + (t - 0.8) * 0.7  # 结束慢
            
            x = self._bezier_point(t, start_x, ctrl1_x, ctrl2_x, end_x)
            y = self._bezier_point(t, start_y, ctrl1_y, ctrl2_y, end_y)
            
            # 添加手部抖动
            x, y = self._add_hand_tremor(x, y)
            path.append((int(x), int(y)))
        
        return path
    
    def random_mouse_movement(self):
        """随机鼠标移动 - PyAutoGUI版本"""
        if USE_PYAUTOGUI:
            try:
                # 获取当前鼠标位置
                current_x, current_y = pyautogui.position()
                
                # 随机移动1-3次
                for _ in range(random.randint(1, 3)):
                    # 随机偏移
                    offset_x = random.randint(-150, 150)
                    offset_y = random.randint(-100, 100)
                    
                    new_x = max(50, min(current_x + offset_x, pyautogui.size()[0] - 50))
                    new_y = max(50, min(current_y + offset_y, pyautogui.size()[1] - 50))
                    
                    # 使用人类曲线移动
                    pyautogui.moveTo(
                        new_x, new_y,
                        duration=random.uniform(0.2, 0.5),
                        tween=pyautogui.easeOutQuad
                    )
                    time.sleep(random.uniform(0.1, 0.4))
                    
                    current_x, current_y = new_x, new_y
                return
            except:
                pass
        
        # 备用：Selenium方式
        try:
            actions = ActionChains(self.driver)
            for _ in range(random.randint(1, 3)):
                offset_x = random.randint(-100, 100)
                offset_y = random.randint(-80, 80)
                steps = random.randint(3, 8)
                for i in range(steps):
                    actions.move_by_offset(offset_x // steps, offset_y // steps)
                    actions.pause(random.uniform(0.02, 0.08))
                actions.pause(random.uniform(0.1, 0.4))
            actions.perform()
        except:
            pass
    
    def random_scroll(self):
        """随机滚动 - 模拟人类浏览"""
        try:
            scroll_amount = random.randint(-250, 250)
            
            # 分步滚动（人类滚动不是一次性的）
            steps = random.randint(3, 8)
            for _ in range(steps):
                self.driver.execute_script(f"window.scrollBy(0, {scroll_amount // steps});")
                time.sleep(random.uniform(0.03, 0.1))
            
            time.sleep(random.uniform(0.5, 1.5))
        except:
            pass
    
    def _simulate_reading(self):
        """模拟人类阅读页面（通过鼠标移动和滚动）"""
        try:
            # 小幅度随机鼠标移动（眼睛在看屏幕）
            actions = ActionChains(self.driver)
            for _ in range(random.randint(2, 5)):
                actions.move_by_offset(random.randint(-30, 30), random.randint(-20, 20))
                actions.pause(random.uniform(0.2, 0.6))
            actions.perform()
            
            # 偶尔小幅滚动
            if random.random() < 0.3:
                self.driver.execute_script(f"window.scrollBy(0, {random.randint(-100, 100)});")
        except:
            pass
    
    # ==================== 元素交互 ====================
    
    def _get_element_screen_position(self, element):
        """获取元素在屏幕上的绝对坐标 - 使用JS获取更准确的位置"""
        try:
            # 使用 JavaScript 获取元素的视口位置
            js_code = """
            var rect = arguments[0].getBoundingClientRect();
            return {
                x: rect.left + rect.width / 2,
                y: rect.top + rect.height / 2,
                width: rect.width,
                height: rect.height
            };
            """
            elem_viewport = self.driver.execute_script(js_code, element)
            
            # 获取浏览器窗口在屏幕上的位置
            window_pos = self.driver.get_window_position()
            window_x = window_pos['x']
            window_y = window_pos['y']
            
            # Chrome浏览器工具栏高度（地址栏+标签栏），根据实际情况调整
            # 无痕模式大约 75-85px，普通模式可能更高
            toolbar_height = 80
            
            # 计算屏幕绝对坐标
            screen_x = window_x + elem_viewport['x']
            screen_y = window_y + toolbar_height + elem_viewport['y']
            
            # 添加随机偏移（人不会精确点击中心）
            offset_range_x = min(15, int(elem_viewport['width'] * 0.3))
            offset_range_y = min(10, int(elem_viewport['height'] * 0.3))
            screen_x += random.randint(-offset_range_x, offset_range_x)
            screen_y += random.randint(-offset_range_y, offset_range_y)
            
            return int(screen_x), int(screen_y)
        except Exception as e:
            print(f"[警告] 获取元素坐标失败: {e}")
            return None, None
    
    def _pyautogui_move_to(self, x, y, duration=None):
        """使用PyAutoGUI移动鼠标到指定坐标（带人类曲线）"""
        if not USE_PYAUTOGUI:
            return
        
        if duration is None:
            # 人类移动速度有变化，距离远的时间长
            current_pos = pyautogui.position()
            distance = math.sqrt((x - current_pos[0])**2 + (y - current_pos[1])**2)
            duration = random.uniform(0.4, 0.8) + distance / 2000  # 距离越远时间越长
        
        try:
            # 随机选择移动曲线类型
            tween_funcs = [
                pyautogui.easeOutQuad,
                pyautogui.easeInOutQuad,
                pyautogui.easeOutCubic,
            ]
            tween = random.choice(tween_funcs)
            
            # 使用PyAutoGUI移动
            pyautogui.moveTo(x, y, duration=duration, tween=tween)
            
            # 到达后的微小修正（人类会微调位置）
            time.sleep(random.uniform(0.1, 0.3))
            if random.random() < 0.6:
                pyautogui.move(
                    random.randint(-4, 4), 
                    random.randint(-3, 3),
                    duration=random.uniform(0.05, 0.15)
                )
        except Exception as e:
            print(f"[警告] PyAutoGUI移动失败: {e}")
    
    def _pyautogui_click(self, x=None, y=None, clicks=1):
        """使用PyAutoGUI点击"""
        if not USE_PYAUTOGUI:
            return
        
        try:
            # 点击前的微小移动（手不完全静止）
            if random.random() < 0.3:
                pyautogui.move(
                    random.randint(-2, 2),
                    random.randint(-1, 1),
                    duration=0.05
                )
            
            if x is not None and y is not None:
                pyautogui.click(x, y, clicks=clicks)
            else:
                pyautogui.click(clicks=clicks)
            
            # 点击后的微小移动（手指离开鼠标的动作）
            time.sleep(random.uniform(0.05, 0.15))
            if random.random() < 0.4:
                pyautogui.move(
                    random.randint(-5, 5),
                    random.randint(-3, 3),
                    duration=0.1
                )
        except Exception as e:
            print(f"[警告] PyAutoGUI点击失败: {e}")

    def supports_desktop_automation(self):
        """返回当前是否可用系统级桌面自动化。"""
        return USE_PYAUTOGUI

    def human_move_to_coordinate(self, x, y):
        """移动鼠标到屏幕坐标。"""
        if not USE_PYAUTOGUI:
            return False

        try:
            if random.random() < 0.35:
                self.random_mouse_movement()
                time.sleep(random.uniform(0.2, 0.6))

            self.hesitation()
            self._pyautogui_move_to(x, y)
            time.sleep(random.uniform(0.15, 0.35))
            return True
        except Exception as e:
            print(f"[警告] 坐标移动失败: {e}")
            return False

    def human_click_coordinate(self, x, y, clicks=1, post_pause_range=(1.0, 2.0)):
        """在屏幕坐标上执行仿真人类点击。"""
        if not USE_PYAUTOGUI:
            return False

        moved = self.human_move_to_coordinate(x, y)
        if not moved:
            return False

        time.sleep(random.uniform(max(0.08, self.click_delay_min), max(0.18, self.click_delay_max)))
        self._pyautogui_click(clicks=clicks)

        if post_pause_range:
            time.sleep(random.uniform(*post_pause_range))

        return True

    def human_type_text(self, text, min_delay=0.20, max_delay=0.50, final_pause_range=(1.0, 2.0)):
        """在当前聚焦输入框中使用系统键盘输入文本。"""
        if USE_PYAUTOGUI:
            try:
                time.sleep(random.uniform(0.2, 0.6))

                for index, char in enumerate(text):
                    pyautogui.write(char, interval=0)

                    delay = random.uniform(min_delay, max_delay)
                    if char.isdigit():
                        delay += random.uniform(0.02, 0.12)
                    if char in '@#$%^&*()_+-=[]{}|;:\'\",.<>?/\\':
                        delay += random.uniform(0.05, 0.20)
                    if index > 0 and random.random() < 0.12:
                        delay += random.uniform(0.15, 0.55)

                    time.sleep(delay)

                if final_pause_range:
                    time.sleep(random.uniform(*final_pause_range))
                return True
            except Exception as e:
                print(f"[警告] 桌面打字失败，回退到活动元素输入: {e}")

        try:
            active_element = self.driver.switch_to.active_element
            active_element.send_keys(text)
            if final_pause_range:
                time.sleep(random.uniform(*final_pause_range))
            return True
        except Exception as e:
            print(f"[警告] 活动元素输入失败: {e}")
            return False

    def human_press_key(self, key, presses=1, interval_range=(0.20, 0.50), hold_range=(0.06, 0.14)):
        """按单个按键若干次。"""
        if USE_PYAUTOGUI:
            try:
                normalized_key = {
                    'return': 'enter',
                    'escape': 'esc',
                    'control': 'ctrl',
                }.get(key, key)

                for press_index in range(presses):
                    if normalized_key in {'enter', 'tab', 'backspace', 'delete', 'esc'}:
                        pyautogui.keyDown(normalized_key)
                        time.sleep(random.uniform(*hold_range))
                        pyautogui.keyUp(normalized_key)
                    else:
                        pyautogui.press(normalized_key)

                    if press_index < presses - 1:
                        time.sleep(random.uniform(*interval_range))
                return True
            except Exception as e:
                print(f"[警告] 桌面按键失败，回退到活动元素按键: {e}")

        try:
            active_element = self.driver.switch_to.active_element
            if key == 'enter':
                active_element.send_keys(Keys.ENTER)
            else:
                active_element.send_keys(key)
            return True
        except Exception as e:
            print(f"[警告] 活动元素按键失败: {e}")
            return False

    def human_hotkey(self, *keys, post_pause_range=(0.10, 0.20)):
        """按组合键。"""
        normalized_keys = [
            {
                'control': 'ctrl',
                'escape': 'esc',
                'return': 'enter',
            }.get(str(key).lower(), str(key).lower())
            for key in keys
            if key
        ]

        if not normalized_keys:
            return False

        if USE_PYAUTOGUI:
            try:
                for key in normalized_keys:
                    pyautogui.keyDown(key)
                    time.sleep(random.uniform(0.03, 0.08))

                for key in reversed(normalized_keys):
                    time.sleep(random.uniform(0.03, 0.08))
                    pyautogui.keyUp(key)

                if post_pause_range:
                    time.sleep(random.uniform(*post_pause_range))
                return True
            except Exception as e:
                print(f"[警告] 桌面组合键失败，回退到活动元素按键: {e}")

        try:
            active_element = self.driver.switch_to.active_element
            key_mapping = {
                'ctrl': Keys.CONTROL,
                'alt': Keys.ALT,
                'shift': Keys.SHIFT,
                'enter': Keys.ENTER,
                'tab': Keys.TAB,
                'backspace': Keys.BACKSPACE,
                'delete': Keys.DELETE,
                'esc': Keys.ESCAPE,
            }
            active_element.send_keys(*[key_mapping.get(key, key) for key in normalized_keys])
            if post_pause_range:
                time.sleep(random.uniform(*post_pause_range))
            return True
        except Exception as e:
            print(f"[警告] 活动元素组合键失败: {e}")
            return False

    def human_scroll_wheel(self, steps, direction='down', interval_range=(0.20, 0.45)):
        """模拟鼠标滚轮滚动。"""
        if steps <= 0:
            return True

        if USE_PYAUTOGUI:
            try:
                for _ in range(steps):
                    amount = random.randint(320, 460)
                    pyautogui.scroll(-amount if direction == 'down' else amount)
                    time.sleep(random.uniform(*interval_range))
                return True
            except Exception as e:
                print(f"[警告] 桌面滚轮失败，回退到页面滚动: {e}")

        try:
            for _ in range(steps):
                offset = random.randint(280, 420)
                if direction == 'down':
                    offset = -offset
                self.driver.execute_script(f"window.scrollBy(0, {-offset});")
                time.sleep(random.uniform(*interval_range))
            return True
        except Exception as e:
            print(f"[警告] 页面滚动失败: {e}")
            return False

    def human_move_to_element(self, element):
        """仿真人类鼠标移动到元素 - PyAutoGUI版本"""
        try:
            # 40%概率先随机移动一下
            if random.random() < 0.40:
                self.random_mouse_movement()
                time.sleep(random.uniform(0.3, 0.8))
            
            # 滚动元素到可视区域
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                element
            )
            time.sleep(random.uniform(1.0, 2.0))
            
            if USE_PYAUTOGUI:
                # 使用PyAutoGUI系统级鼠标移动
                screen_x, screen_y = self._get_element_screen_position(element)
                if screen_x and screen_y:
                    self._pyautogui_move_to(screen_x, screen_y)
                    time.sleep(random.uniform(0.3, 0.8))
                    return
            
            # 备用：使用Selenium ActionChains
            actions = ActionChains(self.driver)
            actions.move_to_element(element)
            offset_x = random.randint(-8, 8)
            offset_y = random.randint(-5, 5)
            actions.move_by_offset(offset_x, offset_y)
            actions.pause(random.uniform(0.1, 0.3))
            actions.perform()
            
            time.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            print(f"[警告] 鼠标移动失败: {e}")
    
    def human_click(self, element, double_click=False):
        """仿真人类点击 - PyAutoGUI版本"""
        try:
            # 30%概率先随机滚动
            if random.random() < 0.30:
                self.random_scroll()
                time.sleep(random.uniform(0.8, 1.5))
            
            # 滚动元素到可视区域
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                element
            )
            time.sleep(random.uniform(1.0, 2.0))
            
            # 点击前的犹豫/思考
            self.hesitation()
            
            # 点击前的最后确认延迟
            time.sleep(random.uniform(self.click_delay_min, self.click_delay_max))
            
            if USE_PYAUTOGUI:
                # 使用PyAutoGUI系统级点击
                screen_x, screen_y = self._get_element_screen_position(element)
                if screen_x and screen_y:
                    # 移动到位置
                    self._pyautogui_move_to(screen_x, screen_y)
                    time.sleep(random.uniform(0.2, 0.5))
                    
                    # 执行点击
                    clicks = 2 if double_click else 1
                    self._pyautogui_click(clicks=clicks)
                    
                    # 点击后停顿
                    time.sleep(random.uniform(1.5, 3.5))
                    return
            
            # 备用：使用Selenium ActionChains
            actions = ActionChains(self.driver)
            if double_click:
                actions.double_click(element)
            else:
                actions.click(element)
            actions.perform()
            
            time.sleep(random.uniform(1.5, 3.5))
            
        except Exception as e:
            print(f"[警告] 点击失败，尝试JS点击: {e}")
            self.driver.execute_script("arguments[0].click();", element)
            time.sleep(random.uniform(1.5, 3.0))
    
    def human_select(self, select_element, value=None, index=None, visible_text=None):
        """仿真人类选择下拉框 - 完整的选择行为"""
        from selenium.webdriver.support.ui import Select
        
        try:
            # 先移动到下拉框
            self.human_move_to_element(select_element)
            
            # 点击展开下拉框前的犹豫
            time.sleep(random.uniform(0.8, 1.8))
            
            # 点击展开
            select_element.click()
            
            # 人类会花时间看选项
            time.sleep(random.uniform(1.5, 3.0))
            
            # 模拟眼睛扫描选项
            if random.random() < 0.5:
                self._simulate_reading()
            
            # 选择选项前的思考
            time.sleep(random.uniform(0.5, 1.5))
            
            # 执行选择
            select = Select(select_element)
            if value is not None:
                select.select_by_value(str(value))
            elif index is not None:
                select.select_by_index(index)
            elif visible_text is not None:
                select.select_by_visible_text(visible_text)
            
            # 选择后确认停顿
            time.sleep(random.uniform(1.0, 2.5))
            
        except Exception as e:
            print(f"[警告] 下拉选择失败: {e}")
    
    def human_type(self, element, text, clear_first=True):
        """仿真人类打字 - 包含打字错误、退格、停顿"""
        try:
            # 先点击输入框
            self.human_click(element)
            
            # 清空现有内容
            if clear_first:
                element.send_keys(Keys.CONTROL + 'a')
                time.sleep(random.uniform(0.3, 0.8))
                element.send_keys(Keys.DELETE)
                time.sleep(random.uniform(0.5, 1.2))
            
            # 开始打字前的停顿（双手放到键盘上）
            time.sleep(random.uniform(1.0, 2.5))
            
            i = 0
            while i < len(text):
                char = text[i]
                
                # 5%概率打错字然后退格（人类经常打错）
                if random.random() < 0.05 and i > 0:
                    wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
                    element.send_keys(wrong_char)
                    time.sleep(random.uniform(0.1, 0.3))
                    
                    # 发现错误，停顿，然后退格
                    time.sleep(random.uniform(0.3, 0.8))
                    element.send_keys(Keys.BACKSPACE)
                    time.sleep(random.uniform(0.2, 0.5))
                
                # 打当前字符
                element.send_keys(char)
                
                # 基础打字延迟（随机变化）
                delay = random.uniform(self.typing_min_delay, self.typing_max_delay)
                
                # 特殊字符更慢（需要按Shift或看键盘）
                if char in '@#$%^&*()_+-=[]{}|;:\'",.< >?/\\':
                    delay += random.uniform(0.2, 0.5)
                
                # 数字也稍慢（可能需要看键盘）
                if char.isdigit():
                    delay += random.uniform(0.1, 0.3)
                
                # 15%概率停顿思考
                if random.random() < 0.15:
                    delay += random.uniform(1.0, 3.0)
                
                # 打字节奏变化（每隔几个字符有变化）
                if i > 0 and i % random.randint(4, 8) == 0:
                    delay += random.uniform(0.4, 1.2)
                
                time.sleep(delay)
                i += 1
            
            # 输入完成后检查（人类会看一眼输入内容）
            time.sleep(random.uniform(1.5, 3.5))
            
        except Exception as e:
            print(f"[警告] 打字失败: {e}")
            self.driver.execute_script("arguments[0].value = arguments[1];", element, text)
    
    def human_scroll_and_read(self, direction='down', distance=None):
        """模拟人类滚动并阅读"""
        if distance is None:
            distance = random.randint(200, 500)
        
        if direction == 'up':
            distance = -distance
        
        # 分多次滚动（人类滚动是断断续续的）
        steps = random.randint(4, 10)
        step_distance = distance / steps
        
        for i in range(steps):
            self.driver.execute_script(f"window.scrollBy(0, {step_distance});")
            
            # 每步之间的停顿（在阅读）
            if random.random() < 0.4:
                time.sleep(random.uniform(0.5, 2.0))
            else:
                time.sleep(random.uniform(0.05, 0.15))
        
        # 滚动后阅读停顿
        time.sleep(random.uniform(1.0, 3.0))
    
    def scroll_to_element(self, element):
        """滚动到元素可见"""
        self.driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
            element
        )
        # 滚动后人类需要时间定位元素
        time.sleep(random.uniform(1.0, 2.5))
    
    def wait_and_find(self, by, selector, timeout=15):
        """等待并查找元素"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        wait = WebDriverWait(self.driver, timeout)
        element = wait.until(EC.presence_of_element_located((by, selector)))
        
        # 找到后短暂延迟
        time.sleep(random.uniform(0.5, 1.5))
        return element
    
    def wait_and_click(self, by, selector, timeout=15):
        """等待元素可点击并点击"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        wait = WebDriverWait(self.driver, timeout)
        element = wait.until(EC.element_to_be_clickable((by, selector)))
        
        self.human_click(element)
        return element
