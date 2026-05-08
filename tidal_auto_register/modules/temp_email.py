# -*- coding: utf-8 -*-
"""
邮箱模块 - 精确元素定位版本
支持登录 mail.xoxome.online 并创建新邮箱
"""

import time
import re
import subprocess
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select


class TempEmailHandler:
    """邮箱处理器"""
    
    def __init__(self, driver, human_behavior, config=None, step_recorder=None):
        self.driver = driver
        self.human = human_behavior
        self.config = config
        self.step_recorder = step_recorder
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

    def _record_substep(self, step_name, note=""):
        if self.step_recorder:
            self.step_recorder.capture(step_name, driver=self.driver, note=note)
    
    def open_email_site(self):
        """打开邮箱网站"""
        print("[步骤] 打开邮箱网站...")
        self.email_tab_index = len(self.driver.window_handles) - 1
        self.driver.get(self.email_url)
        time.sleep(3)  # 等待页面加载
        
        # 等待页面完全加载
        try:
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except:
            pass
        time.sleep(2)
        self._record_substep("EM-01_打开邮箱网站完成")
    
    def login_email(self):
        """登录邮箱"""
        print("[步骤] 登录邮箱...")
        time.sleep(2)
        
        # 检查是否已经登录（页面有"生成邮箱"按钮说明已登录）
        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            if "生成邮箱" in page_text or "同步邮箱" in page_text:
                print("[信息] 已登录状态，跳过登录")
                self._record_substep("EM-02_邮箱已登录")
                return True
        except:
            pass
        
        # 填写用户名 - 快速填写，风车邮箱不监控机器人
        username_filled = False
        try:
            username_selectors = [
                "input[name='username']",
                "input[type='text']:not([readonly])",
                "input[placeholder*='用户']",
                "input.username"
            ]
            for sel in username_selectors:
                try:
                    inputs = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    for inp in inputs:
                        if inp.is_displayed() and inp.is_enabled():
                            print(f"[填写] 用户名: {self.email_username}")
                            inp.clear()
                            inp.send_keys(self.email_username)
                            username_filled = True
                            time.sleep(0.1)
                            self._record_substep("EM-03_填写邮箱用户名")
                            break
                    if username_filled:
                        break
                except:
                    continue
        except Exception as e:
            print(f"[信息] 用户名填写: {e}")
        
        # 填写密码 - 快速填写
        password_filled = False
        try:
            password_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            if password_input.is_displayed():
                print(f"[填写] 密码: {self.email_password}")
                password_input.clear()
                password_input.send_keys(self.email_password)
                password_filled = True
                time.sleep(0.1)
                self._record_substep("EM-04_填写邮箱密码")
        except:
            print("[信息] 未找到密码框")
        
        # 点击登录按钮 - 绿色按钮
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
        
        # 方法3: 通过文本"登录"或"登陆"查找
        if not clicked:
            try:
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    if btn.is_displayed():
                        text = btn.text.strip()
                        if "登录" in text or "登陆" in text or "Login" in text:
                            self.human.human_click(btn)
                            clicked = True
                            print(f"[点击] 登录按钮: {text}")
                            break
            except:
                pass
        
        # 方法4: 通过绿色背景按钮查找
        if not clicked:
            try:
                btns = self.driver.find_elements(By.CSS_SELECTOR, "button.bg-green-500, button.bg-green-600, button[class*='green']")
                for btn in btns:
                    if btn.is_displayed():
                        self.human.human_click(btn)
                        clicked = True
                        print("[点击] 登录按钮 (绿色)")
                        break
            except:
                pass
        
        if clicked:
            time.sleep(3)  # 等待登录完成
            print("[成功] 邮箱登录完成")
            self._record_substep("EM-05_邮箱登录完成")
        else:
            print("[警告] 未找到登录按钮，可能已登录")
            self._record_substep("EM-05_邮箱登录按钮未找到", note="可能已登录")
        
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
                        self._record_substep("EM-06_选择邮箱后缀", note=options[idx].text)
                        break
        except Exception as e:
            print(f"[信息] 后缀选择: {e}")
        
        # 2. 点击"生成邮箱"按钮
        print("[步骤] 点击生成邮箱按钮...")
        clicked = False

        # 方法0: 通过 XPath 精确匹配“生成邮箱”按钮
        try:
            generate_button = WebDriverWait(self.driver, 8).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[normalize-space()='生成邮箱' or contains(normalize-space(), '生成邮箱')]"
                ))
            )
            self.human.human_click(generate_button)
            clicked = True
            print("[点击] 生成邮箱按钮 (XPath)")
            self._record_substep("EM-07_点击生成邮箱按钮")
        except Exception:
            pass
        
        # 方法1: 通过class查找
        if not clicked:
            try:
                btn = self.driver.find_element(By.CSS_SELECTOR, "button.flex-1.font-medium")
                if btn.is_displayed():
                    self.human.human_click(btn)
                    clicked = True
                    print("[点击] 生成邮箱按钮 (class)")
                    self._record_substep("EM-07_点击生成邮箱按钮")
            except:
                pass
        
        # 方法2: 通过文本查找
        if not clicked:
            try:
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    if btn.is_displayed() and btn.is_enabled() and "生成邮箱" in btn.text:
                        self.human.human_click(btn)
                        clicked = True
                        print("[点击] 生成邮箱按钮 (文本)")
                        self._record_substep("EM-07_点击生成邮箱按钮")
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
                            self._record_substep("EM-07_点击生成邮箱按钮", note=text)
                            break
            except:
                pass
        
        if not clicked:
            print("[警告] 未找到生成邮箱按钮")
            self._record_substep("EM-07_生成邮箱按钮未找到", note="失败")
            raise Exception("未找到生成邮箱按钮")
        
        # 3. 等待邮箱生成
        print("[等待] 邮箱生成中，请10秒...")
        time.sleep(10)
        self._record_substep("EM-08_等待邮箱生成10秒完成")
        
        # 4. 点击复制按钮并获取生成的邮箱地址
        self._copy_generated_email()
        self._get_generated_email()

        if not self.email_address:
            raise Exception("生成邮箱后仍未获取到邮箱地址")
        
        print(f"[成功] 新邮箱: {self.email_address}")
        return self.email_address

    def _copy_generated_email(self):
        """点击复制按钮，尽量把生成邮箱放入剪贴板。"""
        print("[步骤] 点击复制按钮...")

        copy_clicked = False
        try:
            copy_button = WebDriverWait(self.driver, 8).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[normalize-space()='复制' or contains(normalize-space(), '复制')]"
                ))
            )
            self.human.human_click(copy_button)
            copy_clicked = True
            print("[点击] 复制按钮 (XPath)")
            time.sleep(0.8)
            self._record_substep("EM-09_点击复制按钮")
        except Exception:
            pass

        if not copy_clicked:
            try:
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    if btn.is_displayed() and btn.is_enabled() and "复制" in btn.text:
                        self.human.human_click(btn)
                        copy_clicked = True
                        print("[点击] 复制按钮 (文本)")
                        time.sleep(0.8)
                        self._record_substep("EM-09_点击复制按钮")
                        break
            except Exception:
                pass

        if not copy_clicked:
            print("[信息] 未找到复制按钮，继续尝试直接读取页面中的邮箱")
            self._record_substep("EM-09_复制按钮未找到", note="继续直接读邮箱")

    def _read_clipboard_email(self):
        """从 Windows 剪贴板读取邮箱地址。"""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=5,
                check=False,
            )
            clipboard_text = (result.stdout or "").strip()
            if clipboard_text and "@" in clipboard_text:
                return clipboard_text
        except Exception:
            pass
        return None
    
    def _get_generated_email(self):
        """获取生成的邮箱地址"""
        print("[步骤] 获取邮箱地址...")
        time.sleep(1)

        # 方法0: 优先读取剪贴板
        clipboard_email = self._read_clipboard_email()
        if clipboard_email:
            self.email_address = clipboard_email
            print(f"[找到] 剪贴板邮箱: {self.email_address}")
            self._record_substep("EM-10_获取邮箱地址成功", note=self.email_address)
            return self.email_address

        # 方法1: 优先读取“生成的邮箱”区域附近的输入框
        try:
            generated_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[readonly], input[placeholder*='邮箱'], input[type='text']")
            for inp in generated_inputs:
                if not inp.is_displayed():
                    continue
                value = (inp.get_attribute("value") or "").strip()
                if value and "@" in value and value != f"{self.email_username}@xoxome.online":
                    self.email_address = value
                    print(f"[找到] 邮箱输入框: {self.email_address}")
                    self._record_substep("EM-10_获取邮箱地址成功", note=self.email_address)
                    return self.email_address
        except Exception:
            pass
        
        # 方法2: 从 readonly 输入框获取（图片中显示的方式）
        try:
            inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[readonly], input[type='text']")
            for inp in inputs:
                value = inp.get_attribute("value")
                if value and "@" in value and value != f"{self.email_username}@xoxome.online":
                    self.email_address = value.strip()
                    print(f"[找到] 邮箱: {self.email_address}")
                    self._record_substep("EM-10_获取邮箱地址成功", note=self.email_address)
                    return self.email_address
        except:
            pass
        
        # 方法3: 从页面文本提取
        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            import re
            matches = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', page_text)
            for email in matches:
                if email != f"{self.email_username}@xoxome.online":
                    self.email_address = email
                    print(f"[找到] 邮箱: {self.email_address}")
                    self._record_substep("EM-10_获取邮箱地址成功", note=self.email_address)
                    return email
        except:
            pass
        
        # 方法4: 从表格中获取
        try:
            tds = self.driver.find_elements(By.TAG_NAME, "td")
            for td in tds:
                text = td.text.strip()
                if "@" in text:
                    self.email_address = text
                    print(f"[找到] 邮箱: {self.email_address}")
                    self._record_substep("EM-10_获取邮箱地址成功", note=self.email_address)
                    return text
        except:
            pass
        
        print("[警告] 未找到新邮箱地址")
        self._record_substep("EM-10_获取邮箱地址失败", note="未找到邮箱")
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
                self._record_substep("EM-11_收到并打开Tidal验证邮件")
                return True
            
            time.sleep(self.check_interval)
        
        raise Exception("等待验证邮件超时")
    
    def get_verification_link(self):
        """获取验证链接"""
        print("[步骤] 获取验证链接...")
        time.sleep(1)
        
        # 方法1: 查找 "Verify Email" 按钮/链接（优先）
        try:
            # 查找包含 "Verify" 文字的链接
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                text = link.text.strip().lower()
                href = link.get_attribute("href") or ""
                
                # 匹配 "Verify Email" 按钮
                if "verify" in text and ("email" in text or "tidal" in href.lower() or "ablink" in href.lower()):
                    if href and href.startswith("http"):
                        print(f"[成功] 找到 Verify Email 链接")
                        self._record_substep("EM-12_提取验证链接成功", note=href)
                        return href
        except:
            pass
        
        # 方法2: 查找 ablink.info.tidal.com 链接
        try:
            links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='ablink'], a[href*='tidal.com']")
            for link in links:
                href = link.get_attribute("href")
                if href and ("ablink" in href.lower() or "tidal.com" in href.lower()):
                    print(f"[成功] 找到 Tidal 链接")
                    self._record_substep("EM-12_提取验证链接成功", note=href)
                    return href
        except:
            pass
        
        # 方法3: 从页面源码提取 ablink 链接
        try:
            import re
            # 匹配 ablink.info.tidal.com 格式
            pattern = r'https?://ablink\.info\.tidal\.com[^\s<>"\']*'
            matches = re.findall(pattern, self.driver.page_source, re.IGNORECASE)
            if matches:
                print(f"[成功] 从页面源码提取到链接")
                self._record_substep("EM-12_提取验证链接成功", note=matches[0])
                return matches[0]
        except:
            pass
        
        # 方法4: 通用验证链接匹配
        try:
            import re
            pattern = r'https?://[^\s<>"\']+(?:verify|confirm|activate)[^\s<>"\']*'
            matches = re.findall(pattern, self.driver.page_source, re.IGNORECASE)
            if matches:
                self._record_substep("EM-12_提取验证链接成功", note=matches[0])
                return matches[0]
        except:
            pass
        
        raise Exception("未找到验证链接")
    
    def click_verification_link(self):
        """直接点击邮件中的 Verify Email 按钮"""
        print("[步骤] 点击 Verify Email 按钮...")
        time.sleep(1)

        def _switch_to_newest_tab_if_needed():
            if len(self.driver.window_handles) > 1:
                self.driver.switch_to.window(self.driver.window_handles[-1])

        def _is_tidal_verify_href(href, text):
            href_lower = (href or "").lower()
            text_lower = (text or "").lower()
            if "ablink" in href_lower and "tidal" in href_lower:
                return True
            if "login.tidal.com" in href_lower and (
                "authorize" in href_lower or "verification" in href_lower or "verify" in href_lower
            ):
                return True
            if "tidal.com" in href_lower and "verify" in text_lower:
                return True
            if "verify" in text_lower and "email" in text_lower:
                return True
            return False

        # 方法1: 在主文档中查找候选链接
        try:
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = (link.get_attribute("href") or "").strip()
                text = (link.text or "").strip()
                if not _is_tidal_verify_href(href, text):
                    continue

                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                time.sleep(0.8)
                try:
                    link.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", link)

                print(f"[点击] 验证链接 (主文档): {href or text}")
                time.sleep(3)
                _switch_to_newest_tab_if_needed()
                self._record_substep("EM-13_点击验证链接并打开页面", note=(href or text))
                return True
        except Exception as e:
            print(f"[警告] 主文档查找验证链接失败: {e}")

        # 方法2: 在 iframe 中查找候选链接
        try:
            self.driver.switch_to.default_content()
            frames = self.driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
            for index, frame in enumerate(frames):
                try:
                    self.driver.switch_to.default_content()
                    self.driver.switch_to.frame(frame)
                except Exception:
                    continue

                links = self.driver.find_elements(By.TAG_NAME, "a")
                for link in links:
                    href = (link.get_attribute("href") or "").strip()
                    text = (link.text or "").strip()
                    if not _is_tidal_verify_href(href, text):
                        continue

                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                    time.sleep(0.8)
                    try:
                        link.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", link)

                    print(f"[点击] 验证链接 (iframe-{index}): {href or text}")
                    time.sleep(3)
                    self.driver.switch_to.default_content()
                    _switch_to_newest_tab_if_needed()
                    self._record_substep("EM-13_点击验证链接并打开页面", note=(href or text))
                    return True

            self.driver.switch_to.default_content()
        except Exception as e:
            self.driver.switch_to.default_content()
            print(f"[警告] iframe 查找验证链接失败: {e}")

        # 方法3: 直接提取 href 并新标签打开（最终兜底）
        try:
            verify_link = self.get_verification_link()
            self.driver.execute_script("window.open(arguments[0], '_blank');", verify_link)
            time.sleep(2)
            _switch_to_newest_tab_if_needed()
            print(f"[点击] 通过兜底方式打开验证链接: {verify_link}")
            self._record_substep("EM-13_点击验证链接并打开页面", note=verify_link)
            return True
        except Exception as e:
            print(f"[警告] 兜底打开验证链接失败: {e}")

        raise Exception("未能点击验证链接")
    
    def switch_to_email_tab(self):
        """切换到邮箱标签页"""
        if self.email_tab_index is not None and self.email_tab_index < len(self.driver.window_handles):
            self.driver.switch_to.window(self.driver.window_handles[self.email_tab_index])
        else:
            self.driver.switch_to.window(self.driver.window_handles[0])
        self._record_substep("EM-14_切换到邮箱标签页")
