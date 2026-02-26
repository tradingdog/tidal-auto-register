# -*- coding: utf-8 -*-
"""
邮箱模块 - 精确元素定位版本
支持登录 mail.xoxome.online 并创建新邮箱
"""

import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select


class TempEmailHandler:
    """邮箱处理器"""
    
    def __init__(self, driver, human_behavior, config=None):
        self.driver = driver
        self.human = human_behavior
        self.config = config
        self.email_address = None
        self.email_tab_index = None
        
        # 从credentials.py读取配置
        try:
            from credentials import EMAIL_CONFIG
            self.email_url = EMAIL_CONFIG["url"]
            self.email_username = EMAIL_CONFIG["username"]
            self.email_password = EMAIL_CONFIG["password"]
        except ImportError:
            raise Exception("找不到credentials.py文件")
        
        self.check_interval = 3
        self.max_attempts = 60
    
    def open_email_site(self):
        """打开邮箱网站"""
        print("[步骤] 打开邮箱网站...")
        self.email_tab_index = len(self.driver.window_handles) - 1
        self.driver.get(self.email_url)
        time.sleep(1.5)
    
    def login_email(self):
        """登录邮箱"""
        print("[步骤] 登录邮箱...")
        time.sleep(1)
        
        # 填写用户名
        try:
            username_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='username'], input[type='text']")
            if username_input.is_displayed():
                print(f"[填写] 用户名: {self.email_username}")
                self.human.human_type(username_input, self.email_username)
                time.sleep(0.3)
        except:
            print("[信息] 可能已登录，跳过用户名")
        
        # 填写密码
        try:
            password_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            if password_input.is_displayed():
                print("[填写] 密码: ******")
                self.human.human_type(password_input, self.email_password)
                time.sleep(0.3)
        except:
            print("[信息] 未找到密码框")
        
        # 点击登录按钮 - 绿色按钮，class包含 w-full font-bold
        print("[步骤] 点击登录按钮...")
        clicked = False
        
        # 方法1: 通过精确的class查找
        try:
            btn = self.driver.find_element(By.CSS_SELECTOR, "button.w-full.font-bold")
            if btn.is_displayed():
                self.human.human_click(btn)
                clicked = True
                print("[点击] 登录按钮 (class)")
        except:
            pass
        
        # 方法2: 通过type=submit查找
        if not clicked:
            try:
                btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                if btn.is_displayed():
                    self.human.human_click(btn)
                    clicked = True
                    print("[点击] 登录按钮 (submit)")
            except:
                pass
        
        # 方法3: 通过文本"登录"查找
        if not clicked:
            try:
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    if btn.is_displayed() and "登录" in btn.text:
                        self.human.human_click(btn)
                        clicked = True
                        print(f"[点击] 登录按钮: {btn.text}")
                        break
            except:
                pass
        
        if clicked:
            time.sleep(2)
            print("[成功] 邮箱登录完成")
        else:
            print("[警告] 未找到登录按钮")
        
        return True
    
    def create_new_email(self):
        """创建新邮箱"""
        print("[步骤] 创建新邮箱...")
        time.sleep(1)
        
        # 1. 选择邮箱后缀（下拉框）
        print("[步骤] 选择邮箱后缀...")
        try:
            # 查找select下拉框
            selects = self.driver.find_elements(By.TAG_NAME, "select")
            for select_elem in selects:
                if select_elem.is_displayed():
                    select = Select(select_elem)
                    options = select.options
                    if len(options) > 1:
                        # 随机选择一个后缀（跳过第一个）
                        import random
                        idx = random.randint(1, min(3, len(options) - 1))
                        select.select_by_index(idx)
                        print(f"[选择] 后缀: {options[idx].text}")
                        time.sleep(0.5)
                        break
        except Exception as e:
            print(f"[信息] 后缀选择: {e}")
        
        # 2. 点击"生成邮箱"按钮
        print("[步骤] 点击生成邮箱按钮...")
        clicked = False
        
        # 方法1: 通过class查找
        try:
            btn = self.driver.find_element(By.CSS_SELECTOR, "button.flex-1.font-medium")
            if btn.is_displayed():
                self.human.human_click(btn)
                clicked = True
                print("[点击] 生成邮箱按钮 (class)")
        except:
            pass
        
        # 方法2: 通过文本查找
        if not clicked:
            try:
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    if btn.is_displayed() and "生成邮箱" in btn.text:
                        self.human.human_click(btn)
                        clicked = True
                        print("[点击] 生成邮箱按钮 (文本)")
                        break
            except:
                pass
        
        # 方法3: 通过黑色按钮样式查找
        if not clicked:
            try:
                btns = self.driver.find_elements(By.CSS_SELECTOR, "button.rounded-md, button.bg-black, button.monochrome-button")
                for btn in btns:
                    if btn.is_displayed():
                        text = btn.text.strip()
                        if "生成" in text or "邮箱" in text:
                            self.human.human_click(btn)
                            clicked = True
                            print(f"[点击] 按钮: {text}")
                            break
            except:
                pass
        
        if not clicked:
            print("[警告] 未找到生成邮箱按钮")
        
        # 3. 等待邮箱生成（网络延迟需要较长时间）
        print("[等待] 邮箱生成中，请20秒...")
        time.sleep(20)
        
        # 4. 获取生成的邮箱地址
        self._get_generated_email()
        
        print(f"[成功] 新邮箱: {self.email_address}")
        return self.email_address
    
    def _get_generated_email(self):
        """获取生成的邮箱地址"""
        print("[步骤] 获取邮箱地址...")
        time.sleep(1)
        
        # 方法1: 从 readonly 输入框获取（图片中显示的方式）
        try:
            inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[readonly], input[type='text']")
            for inp in inputs:
                value = inp.get_attribute("value")
                if value and "@" in value and value != f"{self.email_username}@xoxome.online":
                    self.email_address = value.strip()
                    print(f"[找到] 邮箱: {self.email_address}")
                    return self.email_address
        except:
            pass
        
        # 方法2: 从页面文本提取
        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            import re
            matches = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', page_text)
            for email in matches:
                if email != f"{self.email_username}@xoxome.online":
                    self.email_address = email
                    print(f"[找到] 邮箱: {self.email_address}")
                    return email
        except:
            pass
        
        # 方法3: 从表格中获取
        try:
            tds = self.driver.find_elements(By.TAG_NAME, "td")
            for td in tds:
                text = td.text.strip()
                if "@" in text:
                    self.email_address = text
                    print(f"[找到] 邮箱: {self.email_address}")
                    return text
        except:
            pass
        
        print("[警告] 未找到新邮箱地址")
        return self.email_address
    
    def get_email_address(self):
        """返回邮箱地址"""
        return self.email_address
    
    def refresh_inbox(self):
        """刷新收件箱"""
        # 尝试点击刷新按钮
        try:
            btns = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in btns:
                text = btn.text.lower()
                if "同步" in text or "刷新" in text or "refresh" in text:
                    self.human.human_click(btn)
                    time.sleep(1)
                    return True
        except:
            pass
        
        # 直接刷新页面
        self.driver.refresh()
        time.sleep(1.5)
        return True
    
    def check_for_tidal_email(self):
        """检查Tidal邮件"""
        try:
            # 查找包含tidal的行
            rows = self.driver.find_elements(By.CSS_SELECTOR, "tr, .mail-item, .email-row")
            for row in rows:
                if "tidal" in row.text.lower():
                    return row
            
            # 从页面文本查找
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            if "tidal" in body_text:
                # 尝试点击包含tidal的元素
                elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'TIDAL') or contains(text(), 'Tidal') or contains(text(), 'tidal')]")
                for elem in elements:
                    if elem.is_displayed() and elem.tag_name in ['tr', 'div', 'a', 'td']:
                        return elem
        except:
            pass
        return None
    
    def wait_for_verification_email(self, timeout_minutes=5):
        """等待验证邮件"""
        print(f"[步骤] 等待Tidal验证邮件...")
        
        max_attempts = int(timeout_minutes * 60 / self.check_interval)
        
        for attempt in range(max_attempts):
            print(f"[等待] 检查邮件... ({attempt + 1}/{max_attempts})")
            
            self.refresh_inbox()
            time.sleep(1)
            
            tidal_email = self.check_for_tidal_email()
            if tidal_email:
                print("[成功] 收到Tidal邮件!")
                self.human.human_click(tidal_email)
                time.sleep(1.5)
                return True
            
            time.sleep(self.check_interval)
        
        raise Exception("等待验证邮件超时")
    
    def get_verification_link(self):
        """获取验证链接"""
        print("[步骤] 获取验证链接...")
        time.sleep(1)
        
        # 查找验证链接
        try:
            links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='verify'], a[href*='confirm'], a[href*='tidal']")
            for link in links:
                href = link.get_attribute("href")
                if href and ("verify" in href.lower() or "confirm" in href.lower()):
                    print(f"[成功] 找到验证链接")
                    return href
        except:
            pass
        
        # 从页面源码提取
        try:
            pattern = r'https?://[^\s<>"\']+(?:verify|confirm|activate)[^\s<>"\']*'
            matches = re.findall(pattern, self.driver.page_source, re.IGNORECASE)
            if matches:
                return matches[0]
        except:
            pass
        
        raise Exception("未找到验证链接")
    
    def click_verification_link(self):
        """点击验证链接"""
        url = self.get_verification_link()
        print("[步骤] 访问验证链接...")
        
        self.driver.execute_script(f"window.open('{url}');")
        self.driver.switch_to.window(self.driver.window_handles[-1])
        time.sleep(3)
        
        print("[成功] 验证页面已打开")
        return True
    
    def switch_to_email_tab(self):
        """切换到邮箱标签页"""
        if self.email_tab_index is not None and self.email_tab_index < len(self.driver.window_handles):
            self.driver.switch_to.window(self.driver.window_handles[self.email_tab_index])
        else:
            self.driver.switch_to.window(self.driver.window_handles[0])
