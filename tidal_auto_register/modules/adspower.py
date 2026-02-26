# -*- coding: utf-8 -*-
"""
浏览器控制模块
支持直接启动Chrome浏览器（无痕模式）
增强反检测能力
"""

import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# 自动管理ChromeDriver
try:
    from webdriver_manager.chrome import ChromeDriverManager
    USE_WEBDRIVER_MANAGER = True
except ImportError:
    USE_WEBDRIVER_MANAGER = False


class ChromeBrowser:
    """增强反检测的Chrome浏览器控制器"""
    
    def __init__(self):
        self.driver = None
    
    def start_browser(self, incognito=True):
        """
        启动Chrome浏览器（增强反检测）
        """
        print("[信息] 正在启动Chrome浏览器...")
        
        try:
            chrome_options = Options()
            
            # 无痕模式
            if incognito:
                chrome_options.add_argument("--incognito")
                print("[信息] 已启用无痕模式")
            
            # ========== 核心反检测参数 ==========
            # 禁用自动化控制特征
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            
            # 设置真实的User-Agent
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            ]
            chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
            
            # 设置语言
            chrome_options.add_argument("--lang=en-US,en")
            
            # 窗口设置
            chrome_options.add_argument("--start-maximized")
            
            # 禁用一些可能暴露自动化的特征
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-gpu")
            
            # 禁用通知
            chrome_options.add_argument("--disable-notifications")
            
            # 禁用密码保存弹窗
            prefs = {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.default_content_setting_values.notifications": 2
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # 创建浏览器实例
            if USE_WEBDRIVER_MANAGER:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
            
            # ========== CDP命令隐藏webdriver特征 ==========
            # 注入JavaScript隐藏自动化特征
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    // 隐藏webdriver属性
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    
                    // 隐藏Chrome自动化特征
                    window.chrome = {
                        runtime: {},
                        loadTimes: function() {},
                        csi: function() {},
                        app: {}
                    };
                    
                    // 修改plugins数量
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    
                    // 修改languages
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });
                    
                    // 隐藏Permissions
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                    );
                """
            })
            
            # 设置页面加载超时
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(10)
            
            print("[成功] Chrome浏览器启动成功")
            return self.driver
            
        except Exception as e:
            error_msg = str(e)
            if "chromedriver" in error_msg.lower() or "not found" in error_msg.lower():
                raise Exception(
                    "找不到ChromeDriver！请确保：\n"
                    "1. 已安装Chrome浏览器\n"
                    "2. ChromeDriver已下载并添加到系统PATH\n"
                    "   或运行: pip install webdriver-manager"
                )
            raise Exception(f"启动Chrome浏览器失败: {e}")
    
    def stop_browser(self):
        """关闭浏览器"""
        if self.driver:
            try:
                self.driver.quit()
                print("[信息] 浏览器已关闭")
            except:
                pass
            self.driver = None
    
    def get_driver(self):
        """获取WebDriver实例"""
        return self.driver
    
    def new_tab(self, url=None):
        """打开新标签页"""
        if self.driver:
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            if url:
                self.driver.get(url)
    
    def switch_to_tab(self, index):
        """切换到指定标签页"""
        if self.driver and index < len(self.driver.window_handles):
            self.driver.switch_to.window(self.driver.window_handles[index])
    
    def close_current_tab(self):
        """关闭当前标签页"""
        if self.driver:
            self.driver.close()
            if self.driver.window_handles:
                self.driver.switch_to.window(self.driver.window_handles[-1])
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_browser()


# 兼容旧代码的别名
AdsPowerBrowser = ChromeBrowser
