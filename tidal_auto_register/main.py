"""
Tidal 自动注册系统 - 主程序 v0.2.19
"""

import sys
import os
import time
import traceback
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from modules.adspower import ChromeBrowser
from modules.temp_email import TempEmailHandler
from modules.tidal_register import TidalRegister, BotDetectedException
from utils.human_behavior import HumanBehavior
from utils.card_reader import CardReader
from utils.step_screenshot import StepScreenshotRecorder


class TeeStream:
    """将输出同时写入终端和日志文件。"""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def capture_runtime_step(recorder, step_name, driver=None, note=""):
    if recorder:
        recorder.capture(step_name, driver=driver, note=note)


def init_runtime_logger(project_root):
    """初始化运行日志：每次运行创建独立时间戳日志文件。"""
    logs_dir = os.path.join(project_root, "data", "logs", "runtime")
    os.makedirs(logs_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    log_path = os.path.join(logs_dir, f"run_{timestamp}.log")
    log_file = open(log_path, "w", encoding="utf-8")

    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = TeeStream(original_stdout, log_file)
    sys.stderr = TeeStream(original_stderr, log_file)
    return log_path, log_file, original_stdout, original_stderr


def create_instant_account_snapshot(base_accounts_path, email, password):
    """账号密码生成后，立即创建独立快照文件 accounts_日期时间.txt。"""
    accounts_dir = os.path.dirname(base_accounts_path)
    os.makedirs(accounts_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_path = os.path.join(accounts_dir, f"accounts_{timestamp}.txt")
    line_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{line_time} | Email: {email} | Password: {password}\n"

    with open(snapshot_path, "w", encoding="utf-8") as snapshot_file:
        snapshot_file.write(line)

    return snapshot_path


def main():
    project_root = os.path.dirname(os.path.abspath(__file__))
    log_file_path, log_file, original_stdout, original_stderr = init_runtime_logger(project_root)

    print("=" * 50)
    print("   Tidal 自动注册系统 v0.2.19")
    print("=" * 50)
    print(f"[日志] 本次运行日志: {log_file_path}")
    
    browser = None
    driver = None
    recorder = None
    should_close_browser = True  # 默认关闭浏览器
    instant_accounts_path = None
    
    try:
        # 初始化
        print("\n[初始化] 加载配置...")
        config = Config()
        recorder = StepScreenshotRecorder(project_root)
        
        print("[初始化] 读取卡片信息...")
        card = CardReader(config.CARD_FILE_PATH)
        print(card)
        
        # 步骤1: 启动浏览器
        print("\n" + "=" * 50)
        print("  步骤 1/11: 启动Chrome浏览器")
        print("=" * 50)
        
        browser = ChromeBrowser()
        driver = browser.start_browser(incognito=True)
        capture_runtime_step(recorder, "步骤1_启动Chrome浏览器完成", driver=driver)
        human = HumanBehavior(driver, config)
        
        tidal = TidalRegister(driver, human, card, config, step_recorder=recorder)

        # 步骤2: 预检查 Tidal 首页访问状态
        print("\n" + "=" * 50)
        print("  步骤 2/11: 预检查Tidal首页访问状态")
        print("=" * 50)

        tidal.ensure_home_access_ready()
        capture_runtime_step(recorder, "步骤2_预检查Tidal首页访问状态完成", driver=driver)

        # 步骤3: 登录邮箱并创建新邮箱
        print("\n" + "=" * 50)
        print("  步骤 3/11: 登录邮箱并创建新邮箱")
        print("=" * 50)

        browser.new_tab()
        time.sleep(0.5)
        
        email_handler = TempEmailHandler(driver, human, config, step_recorder=recorder)
        email_handler.open_email_site()
        email_handler.login_email()
        temp_email = email_handler.create_new_email()
        capture_runtime_step(recorder, "步骤3_登录邮箱并创建新邮箱完成", driver=driver, note=temp_email)
        
        print(f"\n[成功] 使用邮箱: {temp_email}")
        
        # 步骤4: 注册Tidal账号
        print("\n" + "=" * 50)
        print("  步骤 4/11: 注册Tidal账号")
        print("=" * 50)

        if not tidal.switch_to_primary_tidal_tab():
            browser.switch_to_tab(0)
        time.sleep(0.5)

        tidal.perform_registration(temp_email, skip_open=True)
        capture_runtime_step(recorder, "步骤4_注册Tidal账号完成", driver=driver, note=temp_email)

        # 账号密码就绪后立即生成独立快照文件
        if tidal.email and tidal.password:
            instant_accounts_path = create_instant_account_snapshot(
                config.ACCOUNTS_FILE_PATH,
                tidal.email,
                tidal.password,
            )
            print(f"[成功] 已立即创建账号快照: {instant_accounts_path}")
            capture_runtime_step(recorder, "步骤4_立即创建账号快照文件", driver=driver, note=instant_accounts_path)
        
        # 检查机器人检测
        tidal.check_bot_detection()
        
        # 步骤5: 进入订阅页面
        print("\n" + "=" * 50)
        print("  步骤 5/11: 进入订阅页面")
        print("=" * 50)
        
        tidal.enter_subscription_page()
        time.sleep(2)
        capture_runtime_step(recorder, "步骤5_进入订阅页面完成", driver=driver)
        
        # 检查机器人检测
        tidal.check_bot_detection()
        
        # 步骤6: 点击 View Plans
        print("\n" + "=" * 50)
        print("  步骤 6/11: 点击 View Plans")
        print("=" * 50)
        
        tidal.click_view_plans()
        time.sleep(3)
        capture_runtime_step(recorder, "步骤6_点击ViewPlans完成", driver=driver)
        
        # 检查机器人检测 - 这是最容易被拦截的步骤
        tidal.check_bot_detection()
        
        # 步骤7: 选择订阅计划
        print("\n" + "=" * 50)
        print("  步骤 7/11: 选择订阅计划")
        print("=" * 50)
        
        tidal.select_subscription()
        time.sleep(2)
        capture_runtime_step(recorder, "步骤7_选择订阅计划完成", driver=driver)
        
        # 检查机器人检测
        tidal.check_bot_detection()
        
        # 步骤8: 填写支付信息
        print("\n" + "=" * 50)
        print("  步骤 8/11: 填写支付信息")
        print("=" * 50)
        
        tidal.fill_payment()
        tidal.submit_payment()
        capture_runtime_step(recorder, "步骤8_填写并提交支付信息完成", driver=driver)
        
        print("[成功] 订阅流程完成")
        
        # 步骤9: 验证邮箱
        print("\n" + "=" * 50)
        print("  步骤 9/11: 验证邮箱")
        print("=" * 50)
        
        email_handler.switch_to_email_tab()
        time.sleep(1)
        
        email_handler.wait_for_verification_email(timeout_minutes=5)
        email_handler.click_verification_link()
        capture_runtime_step(recorder, "步骤9_验证邮箱完成", driver=driver)
        
        print("[成功] 邮箱验证完成")
        
        # 步骤10: 保存账号
        print("\n" + "=" * 50)
        print("  步骤 10/11: 保存账号")
        print("=" * 50)
        
        tidal.save_account(config.ACCOUNTS_FILE_PATH)
        capture_runtime_step(recorder, "步骤10_保存账号完成", driver=driver, note=config.ACCOUNTS_FILE_PATH)
        
        # 步骤11: 取消会员订阅
        print("\n" + "=" * 50)
        print("  步骤 11/11: 取消会员订阅")
        print("=" * 50)
        
        # 切换到最新标签页（验证邮箱打开的新标签页）
        if driver and len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])
            print("[切换] 切换到验证邮箱后的标签页")
        
        time.sleep(3)
        
        # 执行取消订阅流程
        tidal.cancel_subscription()
        capture_runtime_step(recorder, "步骤11_取消会员订阅完成", driver=driver)
        
        # 完成
        print("\n" + "=" * 50)
        print("   注册完成！")
        print("=" * 50)
        print(f"\n   邮箱: {temp_email}")
        print(f"   密码: {tidal.password}")
        print(f"\n   已保存到: {config.ACCOUNTS_FILE_PATH}")
        if instant_accounts_path:
            print(f"   快照文件: {instant_accounts_path}")
        print("=" * 50)
        capture_runtime_step(recorder, "步骤12_整条注册流程完成", driver=driver, note=temp_email)
        
        input("\n按 Enter 键关闭浏览器...")
    
    except BotDetectedException as e:
        # 机器人检测异常 - 不关闭浏览器
        should_close_browser = False
        capture_runtime_step(recorder, "异常_机器人检测拦截", driver=driver, note=str(e))
        print(f"\n[机器人检测] {e}")
        print("\n[提示] 浏览器保持打开状态，您可以手动处理验证")
        input("\n处理完成后按 Enter 键退出程序（浏览器不会关闭）...")
        
    except KeyboardInterrupt:
        capture_runtime_step(recorder, "异常_用户手动中断", driver=driver)
        print("\n[中断] 用户取消")
    except Exception as e:
        capture_runtime_step(recorder, "异常_程序运行错误", driver=driver, note=str(e))
        print("\n" + "=" * 50)
        print("   发生错误！")
        print("=" * 50)
        print(f"\n[错误] {e}")
        traceback.print_exc()
        input("\n按 Enter 键退出...")
    finally:
        try:
            if browser and should_close_browser:
                browser.stop_browser()
            elif browser and not should_close_browser:
                print("[信息] 浏览器保持打开状态")
            print("[完成] 程序结束")
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            log_file.close()


if __name__ == "__main__":
    main()
