# -*- coding: utf-8 -*-
"""
Tidal 自动注册系统 - 主程序
"""

import sys
import os
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from modules.adspower import ChromeBrowser
from modules.temp_email import TempEmailHandler
from modules.tidal_register import TidalRegister
from utils.human_behavior import HumanBehavior
from utils.card_reader import CardReader


def main():
    print("=" * 50)
    print("   Tidal 自动注册系统 v1.0")
    print("=" * 50)
    
    browser = None
    
    try:
        # 初始化
        print("\n[初始化] 加载配置...")
        config = Config()
        
        print("[初始化] 读取卡片信息...")
        card = CardReader(config.CARD_FILE_PATH)
        print(card)
        
        # 步骤1: 启动浏览器
        print("\n" + "=" * 50)
        print("  步骤 1/6: 启动Chrome浏览器")
        print("=" * 50)
        
        browser = ChromeBrowser()
        driver = browser.start_browser(incognito=True)
        human = HumanBehavior(driver, config)
        
        # 步骤2: 登录邮箱并创建新邮箱
        print("\n" + "=" * 50)
        print("  步骤 2/6: 登录邮箱并创建新邮箱")
        print("=" * 50)
        
        email_handler = TempEmailHandler(driver, human, config)
        email_handler.open_email_site()
        email_handler.login_email()
        temp_email = email_handler.create_new_email()
        
        print(f"\n[成功] 使用邮箱: {temp_email}")
        
        # 步骤3: 注册Tidal账号
        print("\n" + "=" * 50)
        print("  步骤 3/6: 注册Tidal账号")
        print("=" * 50)
        
        browser.new_tab()
        time.sleep(0.5)
        
        tidal = TidalRegister(driver, human, card, config)
        tidal.perform_registration(temp_email)
        
        print("[成功] 注册步骤完成")
        
        # 步骤4: 选择订阅并支付
        print("\n" + "=" * 50)
        print("  步骤 4/6: 选择订阅并支付")
        print("=" * 50)
        
        tidal.perform_subscription()
        
        print("[成功] 订阅步骤完成")
        
        # 步骤5: 验证邮箱
        print("\n" + "=" * 50)
        print("  步骤 5/6: 验证邮箱")
        print("=" * 50)
        
        email_handler.switch_to_email_tab()
        time.sleep(1)
        
        email_handler.wait_for_verification_email(timeout_minutes=5)
        email_handler.click_verification_link()
        
        print("[成功] 邮箱验证完成")
        
        # 步骤6: 保存账号
        print("\n" + "=" * 50)
        print("  步骤 6/6: 保存账号")
        print("=" * 50)
        
        tidal.save_account(config.ACCOUNTS_FILE_PATH)
        
        # 完成
        print("\n" + "=" * 50)
        print("   注册完成！")
        print("=" * 50)
        print(f"\n   邮箱: {temp_email}")
        print(f"   密码: {tidal.password}")
        print(f"\n   已保存到: {config.ACCOUNTS_FILE_PATH}")
        print("=" * 50)
        
        input("\n按 Enter 键关闭浏览器...")
        
    except KeyboardInterrupt:
        print("\n[中断] 用户取消")
    except Exception as e:
        print("\n" + "=" * 50)
        print("   发生错误！")
        print("=" * 50)
        print(f"\n[错误] {e}")
        traceback.print_exc()
        input("\n按 Enter 键退出...")
    finally:
        if browser:
            browser.stop_browser()
        print("[完成] 程序结束")


if __name__ == "__main__":
    main()
