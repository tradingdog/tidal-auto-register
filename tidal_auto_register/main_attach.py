# -*- coding: utf-8 -*-
"""
Tidal 自动注册系统 - 连接已打开浏览器模式

使用方法:
1. 先以调试模式启动Chrome:
   chrome.exe --remote-debugging-port=9222
   
2. 手动打开两个页面:
   - tidal.com
   - mail.xoxome.online (风车邮箱)
   
3. 运行此脚本:
   python main_attach.py
"""

import sys
import os
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from config import Config
from modules.temp_email import TempEmailHandler
from modules.tidal_register import TidalRegister, BotDetectedException
from utils.human_behavior import HumanBehavior
from utils.card_reader import CardReader


class AttachBrowser:
    """连接到已打开的Chrome浏览器"""
    
    def __init__(self):
        self.driver = None
        self.tidal_tab = None
        self.email_tab = None
    
    def connect(self, debug_port=9222):
        """连接到已打开的浏览器 - 使用与apple_music相同的方式"""
        print(f"[连接] 尝试连接到浏览器 (端口: {debug_port})...")
        
        chrome_options = Options()
        chrome_options.debugger_address = f"127.0.0.1:{debug_port}"
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(15)
            print("[成功] 已连接到浏览器")
            print(f"[信息] 当前标签页数量: {len(self.driver.window_handles)}")
            return self.driver
        except Exception as e:
            print(f"[错误] 无法连接到浏览器: {e}")
            print("\n[提示] 请先以调试模式启动Chrome:")
            print(f"       chrome.exe --remote-debugging-port={debug_port}")
            raise
    
    def find_tabs(self):
        """遍历标签页，找到tidal和邮箱页面"""
        if not self.driver:
            return False, False
        
        tidal_found = False
        email_found = False
        
        print("\n[搜索] 正在遍历所有标签页...")
        
        for i, handle in enumerate(self.driver.window_handles):
            self.driver.switch_to.window(handle)
            url = self.driver.current_url.lower()
            
            print(f"  标签页 {i+1}: {url[:50]}...")
            
            # 查找Tidal页面
            if 'tidal' in url and not tidal_found:
                self.tidal_tab = handle
                tidal_found = True
                print(f"    [找到] Tidal页面")
            
            # 查找风车邮箱页面
            if 'mail.xoxome.online' in url and not email_found:
                self.email_tab = handle
                email_found = True
                print(f"    [找到] 邮箱页面")
        
        print(f"\n[结果] Tidal: {'OK' if tidal_found else 'X'}")
        print(f"[结果] 邮箱: {'OK' if email_found else 'X'}")
        
        return tidal_found, email_found
    
    def switch_to_tidal(self):
        """切换到Tidal标签页"""
        if self.tidal_tab:
            self.driver.switch_to.window(self.tidal_tab)
            print("[切换] Tidal页面")
            return True
        return False
    
    def switch_to_email(self):
        """切换到邮箱标签页"""
        if self.email_tab:
            self.driver.switch_to.window(self.email_tab)
            print("[切换] 邮箱页面")
            return True
        return False
    
    def new_tab(self, url=None):
        """打开新标签页"""
        self.driver.execute_script("window.open('');")
        self.driver.switch_to.window(self.driver.window_handles[-1])
        if url:
            self.driver.get(url)


def main():
    print("=" * 50)
    print("  Tidal 自动注册 - 连接已打开浏览器模式")
    print("=" * 50)
    
    browser = None
    
    try:
        # 初始化配置
        print("\n[初始化] 加载配置...")
        config = Config()
        
        print("[初始化] 读取卡片信息...")
        card = CardReader(config.CARD_FILE_PATH)
        print(card)
        
        # 步骤1: 连接到已打开的浏览器
        print("\n" + "=" * 50)
        print("  步骤 1: 连接到已打开的浏览器")
        print("=" * 50)
        
        browser = AttachBrowser()
        driver = browser.connect(debug_port=9222)
        human = HumanBehavior(driver, config)
        
        # 步骤2: 查找已打开的页面
        print("\n" + "=" * 50)
        print("  步骤 2: 查找已打开的页面")
        print("=" * 50)
        
        tidal_found, email_found = browser.find_tabs()
        
        if not tidal_found:
            print("\n[错误] 未找到Tidal页面！请先手动打开 tidal.com")
            return
        
        if not email_found:
            print("\n[错误] 未找到邮箱页面！请先手动打开 mail.xoxome.online")
            return
        
        # 步骤3: 在邮箱页面操作
        print("\n" + "=" * 50)
        print("  步骤 3: 登录邮箱并创建新邮箱")
        print("=" * 50)
        
        browser.switch_to_email()
        time.sleep(1)
        
        email_handler = TempEmailHandler(driver, human, config)
        # 如果已经登录，跳过登录步骤
        try:
            email_handler.login_email()
        except:
            print("[信息] 邮箱可能已登录，跳过登录步骤")
        
        temp_email = email_handler.create_new_email()
        print(f"\n[成功] 使用邮箱: {temp_email}")
        
        # 步骤4: 在Tidal页面注册
        print("\n" + "=" * 50)
        print("  步骤 4: 注册Tidal账号")
        print("=" * 50)
        
        browser.switch_to_tidal()
        time.sleep(1)
        
        tidal = TidalRegister(driver, human, card, config)
        tidal.perform_registration(temp_email)
        
        # 检查机器人检测
        tidal.check_bot_detection()
        
        # 步骤5: 进入订阅页面
        print("\n" + "=" * 50)
        print("  步骤 5: 进入订阅页面")
        print("=" * 50)
        
        tidal.enter_subscription_page()
        time.sleep(2)
        
        # 检查机器人检测
        tidal.check_bot_detection()
        
        # 步骤6: 选择订阅计划
        print("\n" + "=" * 50)
        print("  步骤 6: 选择订阅计划")
        print("=" * 50)
        
        tidal.choose_subscription_plan()
        time.sleep(2)
        
        # 检查机器人检测
        tidal.check_bot_detection()
        
        # 步骤7: 填写支付信息
        print("\n" + "=" * 50)
        print("  步骤 7: 填写支付信息")
        print("=" * 50)
        
        tidal.fill_payment_info()
        time.sleep(2)
        
        # 检查机器人检测
        tidal.check_bot_detection()
        
        # 步骤8: 验证邮箱
        print("\n" + "=" * 50)
        print("  步骤 8: 验证邮箱")
        print("=" * 50)
        
        browser.switch_to_email()
        time.sleep(1)
        
        email_handler.wait_for_tidal_email()
        email_handler.click_verification_link()
        
        # 步骤9: 完成
        print("\n" + "=" * 50)
        print("  注册完成！")
        print("=" * 50)
        
        print(f"\n邮箱: {temp_email}")
        print(f"密码: {tidal.password}")
        
    except BotDetectedException as e:
        print(f"\n[机器人检测] {e}")
        print("[提示] 浏览器保持打开状态，您可以手动处理")
        
    except Exception as e:
        print(f"\n[错误] {e}")
        traceback.print_exc()
    
    finally:
        print("\n[信息] 浏览器保持打开状态")


if __name__ == "__main__":
    main()
