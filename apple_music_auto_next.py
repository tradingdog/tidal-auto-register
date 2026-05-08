import time
import random
import psutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pyautogui
import ctypes
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def find_chrome_tabs():
    chrome_options = Options()
    chrome_options.debugger_address = "127.0.0.1:9222"
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(15)
        
        for handle in driver.window_handles:
            driver.switch_to.window(handle)
            if 'music.apple.com' in driver.current_url.lower():
                print("成功定位Apple Music标签页")
                try:
                    driver.maximize_window()
                except Exception as e:
                    print(f"窗口最大化失败（可忽略）: {str(e)}")
                return driver
        print("未找到Apple Music标签页")
        return None
    except Exception as e:
        print(f"连接Chrome时出错: {str(e)}")
        return None

def human_like_click(element, driver):
    for attempt in range(3):
        try:
            # 先使用Selenium滚动到元素
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(0.5)
            
            # 使用ActionChains模拟更真实的点击
            action = webdriver.ActionChains(driver)
            action.move_to_element(element).pause(random.uniform(0.1, 0.3)).click().perform()
            
            # 验证点击结果
            time.sleep(1)
            if element.is_enabled():
                return True
        except Exception as e:
            print(f"点击失败尝试 {attempt+1}/3: {str(e)}")
            time.sleep(1)
    return False

def check_page_ready():
    # 修改为检测播放器核心元素而不仅仅是readyState
    return driver.execute_script("""
        const player = document.querySelector('audio');
        return player !== null && player.readyState !== 0;
    """)

def monitor_player(driver):
    main_window = driver.current_window_handle
    first_skip = True
    next_interval = 0

    def get_real_scale_factor():
        hDC = ctypes.windll.user32.GetDC(0)
        scale = ctypes.windll.gdi32.GetDeviceCaps(hDC, 118) / 96
        ctypes.windll.user32.ReleaseDC(0, hDC)
        return scale

    while True:
        try:
            driver.switch_to.window(main_window)
            try:
                driver.execute_script("window.focus();")
                # 新增窗口激活逻辑
                ctypes.windll.user32.ShowWindow(driver.current_window_handle, 9)
                ctypes.windll.user32.SetForegroundWindow(driver.current_window_handle)
            except Exception as e:
                print(f"窗口激活失败（可忽略）: {str(e)}")

            # 首次切歌（15秒后）
            if first_skip:
                print("⏳ 等待15秒后执行首次切歌...")
                time.sleep(15)
                first_skip = False
                next_interval = random.randint(600, 900)
                print(f"⏱ 下次切歌将在 {next_interval//60} 分 {next_interval%60} 秒后")
            
            # 执行切歌操作
            print(f"\n🎵 开始切歌操作 ({time.strftime('%Y-%m-%d %H:%M:%S')})")
            try:
                # 更新元素定位方式
                host_element = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR,
                        'amp-playback-controls-item-skip.next'
                    ))
                )
                
                # 修正后的坐标采样逻辑
                button_location = None
                for _ in range(3):
                    loc = driver.execute_script("""
                        const host = arguments[0];
                        const button = host.shadowRoot.querySelector('button.button--next');
                        if (!button) return null;
                        const rect = button.getBoundingClientRect();
                        return {
                            x: rect.left + rect.width/2,
                            y: rect.top + rect.height/2
                        };
                    """, host_element)
                    if loc:
                        button_location = loc
                        time.sleep(0.3)

                if not button_location:
                    raise Exception("无法定位内部按钮坐标")

                # 更新坐标计算逻辑
                win_rect = driver.get_window_rect()
                scroll_offset = driver.execute_script("return {x: window.scrollX, y: window.scrollY};")
                scale_factor = get_real_scale_factor()
                
                actual_x = (win_rect['x'] + (button_location['x'] + scroll_offset['x']) * scale_factor + 8)
                actual_y = (win_rect['y'] + (button_location['y'] + scroll_offset['y']) * scale_factor + 28 * scale_factor)
                
                # 新增随机偏移
                actual_x += random.uniform(-3, 3)
                actual_y += random.uniform(-3, 3)

                # 更新点击方式为直接JS点击
                print("🎯 执行可靠JS点击...")
                driver.execute_script("""
                    arguments[0].shadowRoot.querySelector('button.button--next').click();
                """, host_element)

                # 新增点击验证
                time.sleep(1)
                initial_time = driver.execute_script("return document.querySelector('audio').currentTime")
                new_time = driver.execute_script("return document.querySelector('audio').currentTime")
                if abs(new_time - initial_time) > 1:
                    print("✅ 切歌成功")
                else:
                    print("⚠️ 点击未生效")

            except Exception as e:
                print(f"❌ 切歌失败: {str(e)}")
                driver.save_screenshot('error_screenshot.png')
                print("📸 错误截图已保存为error_screenshot.png")
            
            # 等待随机间隔
            print(f"⏳ 下次切歌将在 {next_interval//60} 分 {next_interval%60} 秒后")
            time.sleep(next_interval)
            
            # 生成新的随机间隔
            next_interval = random.randint(600, 900)

        except Exception as e:
            print(f"⚠️ 发生未处理异常: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    # 检查是否已有Chrome在运行
    if not any(p.name() == 'chrome.exe' for p in psutil.process_iter()):
        print("请先启动Chrome浏览器")
        exit()
    
    driver = find_chrome_tabs()
    if driver:
        monitor_player(driver)
    else:
        print("未找到Apple Music标签页") 