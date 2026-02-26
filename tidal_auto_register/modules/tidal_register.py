# -*- coding: utf-8 -*-
"""
Tidal 注册核心模块 - 精确元素定位版本
"""

import random
import string
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select


class TidalRegister:
    """Tidal注册器"""
    
    def __init__(self, driver, human_behavior, card_reader, config=None):
        self.driver = driver
        self.human = human_behavior
        self.card = card_reader
        self.config = config
        
        self.email = None
        self.password = None
        self.username = None
        self.tidal_url = "https://tidal.com/"
    
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
        """打开Tidal网站"""
        print("[步骤] 打开Tidal网站...")
        
        max_retries = 3
        for attempt in range(max_retries):
            self.driver.get(self.tidal_url)
            time.sleep(8)  # 等待页面加载
            
            # 检查页面是否正常加载
            page_ok = self._check_tidal_page()
            
            if page_ok:
                break
            elif attempt < max_retries - 1:
                print(f"[重试] 第{attempt + 2}次尝试...")
                time.sleep(5)
        
        # 等待页面完全加载
        try:
            WebDriverWait(self.driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except:
            pass
        
        time.sleep(3)
        
        # 处理cookie弹窗
        self._handle_cookie_popup()
        
        print("[成功] Tidal页面已加载")
    
    def _check_tidal_page(self):
        """检查Tidal页面是否正常加载"""
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            page_source = self.driver.page_source.lower()
            
            # 检查是否被拦截
            error_signs = [
                "captcha", "geo.captcha", "意外终止", 
                "enable js", "ad blocker", "access denied",
                "blocked", "forbidden", "error"
            ]
            
            for sign in error_signs:
                if sign in body_text or sign in page_source:
                    print(f"[警告] 检测到拦截: {sign}")
                    # 尝试刷新
                    print("[信息] 刷新页面...")
                    self.driver.refresh()
                    time.sleep(8)
                    return False
            
            # 检查是否有Tidal特征元素
            if "tidal" in page_source or "music" in body_text:
                return True
            
            return True  # 默认认为正常
            
        except Exception as e:
            print(f"[警告] 页面检查失败: {e}")
            return False
    
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
        """点击 Log in / Create a free account 按钮"""
        print("[步骤] 点击 Create a free account...")
        time.sleep(1)
        
        clicked = False
        
        # 方法1: 通过 data-test 属性查找（图片中显示的精确选择器）
        try:
            btn = self.driver.find_element(By.CSS_SELECTOR, "button[data-test='combined-login-signup-button']")
            if btn.is_displayed():
                self.human.human_click(btn)
                clicked = True
                print("[点击] combined-login-signup-button")
        except:
            pass
        
        # 方法2: 通过 data-test 包含 signup 查找
        if not clicked:
            try:
                btns = self.driver.find_elements(By.CSS_SELECTOR, "button[data-test*='signup'], button[data-test*='login']")
                for btn in btns:
                    if btn.is_displayed():
                        self.human.human_click(btn)
                        clicked = True
                        print("[点击] signup/login 按钮")
                        break
            except:
                pass
        
        # 方法3: 通过文本 "Log in / Create" 或 "Create a free account" 查找
        if not clicked:
            try:
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    if btn.is_displayed():
                        text = btn.text.lower()
                        if "create" in text or "sign up" in text or "log in" in text:
                            self.human.human_click(btn)
                            clicked = True
                            print(f"[点击] 按钮: {btn.text}")
                            break
            except:
                pass
        
        # 方法4: 通过链接查找
        if not clicked:
            try:
                links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='signup'], a[href*='login']")
                for link in links:
                    if link.is_displayed():
                        self.human.human_click(link)
                        clicked = True
                        print("[点击] signup/login 链接")
                        break
            except:
                pass
        
        if clicked:
            time.sleep(2)
            return True
        else:
            print("[调试] 页面上的按钮:")
            try:
                btns = self.driver.find_elements(By.TAG_NAME, "button")
                for btn in btns[:8]:
                    if btn.is_displayed() and btn.text.strip():
                        print(f"  - {btn.text}")
            except:
                pass
            raise Exception("找不到Create a free account按钮")
    
    # ========== 步骤3: 选择邮箱注册 ==========
    def select_email_signup(self):
        """选择邮箱注册方式"""
        print("[步骤] 选择邮箱注册...")
        time.sleep(1)
        
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
        """点击继续按钮"""
        print("[步骤] 点击继续...")
        time.sleep(0.5)
        
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
                    time.sleep(1.5)
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
                    time.sleep(1.5)
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
        """填写出生日期"""
        print("[步骤] 填写出生日期...")
        time.sleep(1)
        
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
        import random
        year = random.randint(1990, 2005)
        month = random.randint(1, 12)
        day = random.randint(1, 28)  # 使用1-28避免无效日期
        
        # 选择Day
        try:
            day_select = self.driver.find_element(By.CSS_SELECTOR, "select#tbi-day, select[id*='day']")
            if day_select.is_displayed():
                Select(day_select).select_by_value(str(day))
                print(f"[选择] Day: {day}")
                time.sleep(0.3)
        except Exception as e:
            print(f"[警告] Day选择失败: {e}")
        
        # 选择Month
        try:
            month_select = self.driver.find_element(By.CSS_SELECTOR, "select#tbi-month, select[id*='month']")
            if month_select.is_displayed():
                Select(month_select).select_by_value(str(month))
                print(f"[选择] Month: {month}")
                time.sleep(0.3)
        except Exception as e:
            print(f"[警告] Month选择失败: {e}")
        
        # 选择Year
        try:
            year_select = self.driver.find_element(By.CSS_SELECTOR, "select#tbi-year, select[id*='year']")
            if year_select.is_displayed():
                Select(year_select).select_by_value(str(year))
                print(f"[选择] Year: {year}")
                time.sleep(0.3)
        except Exception as e:
            print(f"[警告] Year选择失败: {e}")
        
        print(f"[完成] 出生日期: {year}-{month:02d}-{day:02d}")
        return True
    
    # ========== 步骤10: 点击 Sign up 按钮 ==========
    def click_signup_button(self):
        """勾选条款并点击 Sign up 按钮"""
        print("[步骤] 检查并勾选条款...")
        time.sleep(1)
            
        # 勾选 Terms checkbox (id="terms1") - 必须勾选
        terms_checked = False
            
        # 方法1: 直接通过ID查找并点击
        try:
            cb = self.driver.find_element(By.ID, "terms1")
            if not cb.is_selected():
                # 尝试多种方式勾选
                # 1. JS click
                self.driver.execute_script("arguments[0].click();", cb)
                time.sleep(0.5)
                    
                # 2. 如果还没勾选，尝试设置checked属性
                if not cb.is_selected():
                    self.driver.execute_script("arguments[0].checked = true;", cb)
                    # 触发change事件
                    self.driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", cb)
                    time.sleep(0.5)
                    
                # 3. 如果还没勾选，尝试点击父元素
                if not cb.is_selected():
                    parent = cb.find_element(By.XPATH, "..")
                    self.driver.execute_script("arguments[0].click();", parent)
                    time.sleep(0.5)
                
            if cb.is_selected():
                terms_checked = True
                print("[勾选] Terms 成功")
            else:
                print("[警告] Terms 未能勾选")
        except Exception as e:
            print(f"[警告] Terms查找失败: {e}")
            
        # 方法2: 如果上面失败，通过name查找
        if not terms_checked:
            try:
                cb = self.driver.find_element(By.CSS_SELECTOR, "input[name='terms']")
                if not cb.is_selected():
                    self.driver.execute_script("arguments[0].click();", cb)
                    time.sleep(0.5)
                    if not cb.is_selected():
                        self.driver.execute_script("arguments[0].checked = true; arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", cb)
                        time.sleep(0.5)
                if cb.is_selected():
                    terms_checked = True
                    print("[勾选] Terms (name) 成功")
            except:
                pass
            
        # 方法3: 遍历所有checkbox，找到required的并勾选
        if not terms_checked:
            try:
                checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
                for cb in checkboxes:
                    if cb.is_displayed() and not cb.is_selected():
                        # 检查是否是required的
                        is_required = cb.get_attribute("required")
                        if is_required:
                            self.driver.execute_script("arguments[0].click();", cb)
                            time.sleep(0.3)
                            if not cb.is_selected():
                                self.driver.execute_script("arguments[0].checked = true; arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", cb)
                            print("[勾选] Required checkbox")
                            terms_checked = True
                            break
            except:
                pass
            
        # 方法4: 最后尝试 - 勾选所有未选中的checkbox
        try:
            checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
            for cb in checkboxes:
                if cb.is_displayed() and not cb.is_selected():
                    self.driver.execute_script("arguments[0].checked = true; arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", cb)
                    time.sleep(0.3)
                    print("[勾选] checkbox")
        except:
            pass
            
        time.sleep(1)  # 等待按钮状态更新
            
        # 现在点击 Sign up 按钮
        print("[步骤] 点击 Sign up 按钮...")
            
        try:
            btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            if btn.is_displayed():
                # 等待按钮enabled
                for _ in range(15):
                    if btn.is_enabled():
                        break
                    print("[等待] 按钮未激活...")
                    time.sleep(0.5)
                    
                if btn.is_enabled():
                    self.human.human_click(btn)
                    print("[点击] Sign up 按钮")
                    time.sleep(3)
                    print("[成功] Sign up 完成")
                else:
                    print("[错误] Sign up 按钮仍然disabled，Terms可能未勾选")
                return True
        except Exception as e:
            print(f"[警告] Sign up 失败: {e}")
            
        return True
    
    # ========== 步骤11: 选择订阅计划 ==========
    def select_subscription(self):
        """选择订阅计划"""
        print("[步骤] 选择订阅计划...")
        time.sleep(2)
        
        # 查找订阅计划卡片
        try:
            cards = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid*='plan'], .plan-card, .subscription-option")
            if cards:
                self.human.human_click(cards[0])
                time.sleep(1)
        except:
            pass
        
        # 点击试用/继续按钮
        try:
            buttons = self.driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], button.primary")
            for btn in buttons:
                if btn.is_displayed():
                    self.human.human_click(btn)
                    time.sleep(2)
                    return True
        except:
            pass
        
        return True
    
    # ========== 步骤10: 填写支付信息 ==========
    def fill_payment(self):
        """填写支付信息"""
        print("[步骤] 填写支付信息...")
        time.sleep(2)
        
        # 检查是否有iframe
        try:
            iframes = self.driver.find_elements(By.CSS_SELECTOR, "iframe[src*='stripe'], iframe[name*='card'], iframe")
            for iframe in iframes:
                if iframe.is_displayed():
                    self.driver.switch_to.frame(iframe)
                    print("[信息] 切换到支付iframe")
                    break
        except:
            pass
        
        # 填写卡号
        self._fill_card_number()
        
        # 填写有效期
        self._fill_expiry()
        
        # 填写CVV
        self._fill_cvv()
        
        # 切回主框架
        try:
            self.driver.switch_to.default_content()
        except:
            pass
        
        # 填写账单地址
        self._fill_billing_address()
        
        print("[成功] 支付信息填写完成")
        return True
    
    def _fill_card_number(self):
        """填写卡号"""
        card_num = self.card.get_card_number()
        selectors = [
            "input[autocomplete='cc-number']",
            "input[name*='cardNumber']",
            "input[name*='number']",
            "input[placeholder*='1234']",
        ]
        
        for selector in selectors:
            try:
                input_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                if input_elem.is_displayed():
                    print(f"[填写] 卡号: ****{card_num[-4:]}")
                    self.human.human_type(input_elem, card_num)
                    return
            except:
                continue
    
    def _fill_expiry(self):
        """填写有效期"""
        expiry = self.card.get_expiry()
        selectors = [
            "input[autocomplete='cc-exp']",
            "input[name*='expir']",
            "input[placeholder*='MM']",
        ]
        
        for selector in selectors:
            try:
                input_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                if input_elem.is_displayed():
                    print(f"[填写] 有效期: {expiry}")
                    self.human.human_type(input_elem, expiry)
                    return
            except:
                continue
    
    def _fill_cvv(self):
        """填写CVV"""
        cvv = self.card.get_cvv()
        selectors = [
            "input[autocomplete='cc-csc']",
            "input[name*='cvv']",
            "input[name*='cvc']",
        ]
        
        for selector in selectors:
            try:
                input_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                if input_elem.is_displayed():
                    print("[填写] CVV: ***")
                    self.human.human_type(input_elem, cvv)
                    return
            except:
                continue
    
    def _fill_billing_address(self):
        """填写账单地址"""
        print("[步骤] 填写账单地址...")
        
        # 街道
        try:
            addr_input = self.driver.find_element(By.CSS_SELECTOR, "input[name*='address'], input[autocomplete='street-address']")
            if addr_input.is_displayed():
                self.human.human_type(addr_input, self.card.get_street())
        except:
            pass
        
        # 城市
        try:
            city_input = self.driver.find_element(By.CSS_SELECTOR, "input[name*='city'], input[autocomplete='address-level2']")
            if city_input.is_displayed():
                self.human.human_type(city_input, self.card.get_city())
        except:
            pass
        
        # 州
        try:
            state_elem = self.driver.find_element(By.CSS_SELECTOR, "select[name*='state'], input[name*='state']")
            if state_elem.is_displayed():
                if state_elem.tag_name == 'select':
                    Select(state_elem).select_by_value(self.card.get_state())
                else:
                    self.human.human_type(state_elem, self.card.get_state())
        except:
            pass
        
        # 邮编
        try:
            zip_input = self.driver.find_element(By.CSS_SELECTOR, "input[name*='zip'], input[name*='postal']")
            if zip_input.is_displayed():
                self.human.human_type(zip_input, self.card.get_zip_code())
        except:
            pass
    
    # ========== 步骤11: 提交支付 ==========
    def submit_payment(self):
        """提交支付"""
        print("[步骤] 提交支付...")
        
        try:
            btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            if btn.is_displayed():
                self.human.human_click(btn)
                print("[点击] 提交支付")
                time.sleep(5)
                return True
        except:
            pass
        
        return True
    
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
    def perform_registration(self, email):
        """执行注册流程"""
        try:
            self.open_tidal()
            self.click_create_account()
            self.select_email_signup()
            self.enter_email(email)
            self.click_continue()
            self.enter_password()
            self.enter_username()
            self.accept_terms()
            self.click_continue()
            # 新增: 填写出生日期并点击 Sign up
            self.enter_birthday()
            self.click_signup_button()
            return True
        except Exception as e:
            print(f"[错误] 注册失败: {e}")
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
