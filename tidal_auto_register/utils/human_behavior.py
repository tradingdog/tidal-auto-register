# -*- coding: utf-8 -*-
"""
人类行为仿真模块
模拟真实人类的鼠标移动、键盘输入、随机延迟等行为
"""

import random
import time
import math
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


class HumanBehavior:
    """增强版人类行为仿真器 - 更像真人操作"""
    
    def __init__(self, driver, config=None):
        self.driver = driver
        self.config = config
        
        # 更像人类的延迟配置
        self.typing_min_delay = 0.12    # 打字最小延迟
        self.typing_max_delay = 0.35    # 打字最大延迟
        self.click_delay_min = 0.8      # 点击前最小延迟
        self.click_delay_max = 2.0      # 点击前最大延迟
        
        if config:
            self.typing_min_delay = getattr(config, 'TYPING_MIN_DELAY', self.typing_min_delay)
            self.typing_max_delay = getattr(config, 'TYPING_MAX_DELAY', self.typing_max_delay)
            self.click_delay_min = getattr(config, 'CLICK_DELAY_MIN', self.click_delay_min)
            self.click_delay_max = getattr(config, 'CLICK_DELAY_MAX', self.click_delay_max)
    
    def random_delay(self, min_sec=1.0, max_sec=3.0):
        """随机延迟 - 模拟人类思考时间"""
        delay = random.uniform(min_sec, max_sec)
        # 20%概率增加额外延迟（模拟分心/思考）
        if random.random() < 0.20:
            delay += random.uniform(1.0, 3.0)
        time.sleep(delay)
    
    def short_delay(self):
        """短延迟"""
        self.random_delay(0.8, 1.8)
    
    def medium_delay(self):
        """中等延迟"""
        self.random_delay(1.5, 3.5)
    
    def long_delay(self):
        """长延迟"""
        self.random_delay(3.0, 6.0)
    
    def random_mouse_movement(self):
        """随机鼠标移动 - 模拟人类随意移动鼠标"""
        try:
            # 获取窗口大小
            window_size = self.driver.get_window_size()
            max_x = window_size['width'] - 100
            max_y = window_size['height'] - 100
            
            # 随机移动几次
            actions = ActionChains(self.driver)
            for _ in range(random.randint(1, 3)):
                x = random.randint(100, max_x)
                y = random.randint(100, max_y)
                actions.move_by_offset(random.randint(-50, 50), random.randint(-50, 50))
                actions.pause(random.uniform(0.1, 0.3))
            actions.perform()
        except:
            pass
    
    def random_scroll(self):
        """随机滚动 - 模拟人类浏览页面"""
        try:
            scroll_amount = random.randint(-200, 200)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(random.uniform(0.3, 0.8))
        except:
            pass
    
    def _bezier_point(self, t, p0, p1, p2, p3):
        """计算三次贝塞尔曲线上的点"""
        return (
            (1-t)**3 * p0 + 
            3 * (1-t)**2 * t * p1 + 
            3 * (1-t) * t**2 * p2 + 
            t**3 * p3
        )
    
    def _generate_bezier_path(self, start_x, start_y, end_x, end_y):
        """生成贝塞尔曲线路径"""
        # 生成随机控制点
        ctrl1_x = start_x + (end_x - start_x) * random.uniform(0.2, 0.4) + random.uniform(-50, 50)
        ctrl1_y = start_y + (end_y - start_y) * random.uniform(0.2, 0.4) + random.uniform(-50, 50)
        ctrl2_x = start_x + (end_x - start_x) * random.uniform(0.6, 0.8) + random.uniform(-30, 30)
        ctrl2_y = start_y + (end_y - start_y) * random.uniform(0.6, 0.8) + random.uniform(-30, 30)
        
        # 计算路径点数量（基于距离）
        distance = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
        num_points = max(10, min(50, int(distance / 10)))
        
        path = []
        for i in range(num_points + 1):
            t = i / num_points
            # 添加轻微的时间扰动
            t = max(0, min(1, t + random.uniform(-0.02, 0.02)))
            
            x = self._bezier_point(t, start_x, ctrl1_x, ctrl2_x, end_x)
            y = self._bezier_point(t, start_y, ctrl1_y, ctrl2_y, end_y)
            path.append((int(x), int(y)))
        
        return path
    
    def human_move_to_element(self, element):
        """仿真人类鼠标移动到元素"""
        try:
            # 30%概率先随机移动一下鼠标
            if random.random() < 0.30:
                self.random_mouse_movement()
            
            # 滚动元素到可视区域
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                element
            )
            self.random_delay(1.0, 2.0)  # 滚动后等待
            
            # 使用ActionChains移动到元素
            actions = ActionChains(self.driver)
            actions.move_to_element(element)
            
            # 添加轻微的随机偏移
            offset_x = random.randint(-5, 5)
            offset_y = random.randint(-5, 5)
            actions.move_by_offset(offset_x, offset_y)
            actions.perform()
            
            # 移动后的停顿（模拟人类思考）
            self.random_delay(0.5, 1.2)
            
        except Exception as e:
            print(f"[警告] 鼠标移动失败: {e}")
    
    def human_click(self, element, double_click=False):
        """仿真人类点击 - 更自然的点击行为"""
        try:
            # 20%概率先随机滚动一下
            if random.random() < 0.20:
                self.random_scroll()
                time.sleep(random.uniform(0.5, 1.0))
            
            # 先移动到元素
            self.human_move_to_element(element)
            
            # 点击前的反应延迟（人类需要时间反应）
            self.random_delay(self.click_delay_min, self.click_delay_max)
            
            # 执行点击
            actions = ActionChains(self.driver)
            if double_click:
                actions.double_click(element)
            else:
                actions.click(element)
            actions.perform()
            
            # 点击后的停顿（等待页面响应）
            self.random_delay(1.0, 2.5)
            
        except Exception as e:
            print(f"[警告] 点击失败，尝试JS点击: {e}")
            # 备用方案：使用JavaScript点击
            self.driver.execute_script("arguments[0].click();", element)
            self.random_delay(1.0, 2.0)
    
    def human_type(self, element, text, clear_first=True):
        """仿真人类打字 - 更自然的输入行为"""
        try:
            # 先点击输入框
            self.human_click(element)
            
            # 清空现有内容
            if clear_first:
                element.send_keys(Keys.CONTROL + 'a')
                self.random_delay(0.5, 1.0)
                element.send_keys(Keys.DELETE)
                self.random_delay(0.5, 1.0)
            
            # 开始打字前的停顿（模拟准备打字）
            self.random_delay(0.5, 1.5)
            
            # 逐字符输入
            for i, char in enumerate(text):
                element.send_keys(char)
                
                # 基础打字延迟
                delay = random.uniform(self.typing_min_delay, self.typing_max_delay)
                
                # 特殊字符打字更慢（需要按Shift等）
                if char in '@#$%^&*()_+-=[]{}|;:\'",.< >?/\\':
                    delay += random.uniform(0.15, 0.4)
                
                # 12%概率停顿（模拟思考）
                if random.random() < 0.12:
                    delay += random.uniform(0.8, 2.0)
                
                # 打字节奏变化（每3-6个字符）
                if i > 0 and i % random.randint(3, 6) == 0:
                    delay += random.uniform(0.3, 0.8)
                
                time.sleep(delay)
            
            # 输入完成后的停顿（模拟检查输入）
            self.random_delay(1.0, 2.5)
            
        except Exception as e:
            print(f"[警告] 打字失败: {e}")
            self.driver.execute_script(
                "arguments[0].value = arguments[1];", 
                element, text
            )
    
    def human_scroll(self, direction='down', distance=None):
        """仿真人类滚动"""
        if distance is None:
            distance = random.randint(200, 400)
        
        if direction == 'up':
            distance = -distance
        
        # 分多次滚动
        steps = random.randint(3, 6)
        step_distance = distance / steps
        
        for _ in range(steps):
            self.driver.execute_script(f"window.scrollBy(0, {step_distance});")
            time.sleep(random.uniform(0.03, 0.1))
        
        # 滚动后停顿
        self.random_delay(0.3, 0.6)
    
    def scroll_to_element(self, element):
        """滚动到元素可见"""
        self.driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
            element
        )
        self.random_delay(0.5, 1.0)
    
    def wait_and_find(self, by, selector, timeout=15):
        """等待并查找元素"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        wait = WebDriverWait(self.driver, timeout)
        element = wait.until(EC.presence_of_element_located((by, selector)))
        
        # 找到后短暂延迟
        self.random_delay(0.2, 0.5)
        return element
    
    def wait_and_click(self, by, selector, timeout=15):
        """等待元素可点击并点击"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        wait = WebDriverWait(self.driver, timeout)
        element = wait.until(EC.element_to_be_clickable((by, selector)))
        
        self.human_click(element)
        return element
