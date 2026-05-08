# -*- coding: utf-8 -*-
"""
浏览器控制模块
优先使用稳定的本地 Chrome + chromedriver 启动链路，避免 Selenium Manager 卡顿。
在稳定链路失败且环境已安装 undetected-chromedriver 时，再回退到备用模式。
"""

import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import time
import urllib.request
import zipfile


SELENIUM_AVAILABLE = False
USE_UNDETECTED = False
uc = None

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except ImportError:
    webdriver = None
    Service = None
    print("[错误] 未安装 selenium，无法启动 Chrome 浏览器")

try:
    import undetected_chromedriver as uc
    USE_UNDETECTED = True
    print("[信息] 已加载 undetected-chromedriver（备用模式）")
except ImportError:
    print("[信息] 未安装 undetected-chromedriver，将使用稳定本地驱动模式")


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHROME_BINARY_CANDIDATES = [
    r"C:\Users\Lenovo\AppData\Local\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]
WEBDRIVER_STARTUP_RETRIES = 4
WEBDRIVER_STARTUP_RETRY_DELAY = 2.0
WEBDRIVER_DOWNLOAD_TIMEOUT = 30
CHROMEDRIVER_PLATFORM = "win64"
CHROMEDRIVER_CACHE_DIR = ".webdriver_cache"


def resolve_chrome_binary_path():
    """在 Windows 常见路径中查找 Chrome 可执行文件。"""
    for candidate in CHROME_BINARY_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return None


def detect_chrome_version(chrome_binary_path):
    """通过 chrome.exe --version 获取本机 Chrome 版本。"""
    try:
        result = subprocess.run(
            [chrome_binary_path, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=10,
            check=False,
        )
        version_text = f"{result.stdout} {result.stderr}".strip()
        match = re.search(r"(\d+\.\d+\.\d+\.\d+)", version_text)
        if match:
            return match.group(1)
    except Exception:
        pass

    try:
        ps_command = f"(Get-Item '{chrome_binary_path}').VersionInfo.ProductVersion"
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=10,
            check=False,
        )
        version_text = f"{result.stdout} {result.stderr}".strip()
        match = re.search(r"(\d+\.\d+\.\d+\.\d+)", version_text)
        if match:
            return match.group(1)
    except Exception:
        pass

    return None


def resolve_chromedriver_version(chrome_version):
    """根据 Chrome build 解析匹配的 chromedriver 版本。"""
    build_version = ".".join(chrome_version.split(".")[:3])
    metadata_url = "https://googlechromelabs.github.io/chrome-for-testing/latest-patch-versions-per-build.json"

    try:
        with urllib.request.urlopen(metadata_url, timeout=WEBDRIVER_DOWNLOAD_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
        build_info = data.get("builds", {}).get(build_version)
        if build_info:
            return build_info.get("version")
    except Exception as e:
        print(f"[警告] 查询 chromedriver 版本失败，回退到 Chrome 同版本号: {e}")

    return chrome_version


def find_existing_chromedriver(driver_version):
    """优先复用已存在的 chromedriver，避免重复下载。"""
    candidates = [
        Path.home() / ".cache" / "selenium" / "chromedriver" / CHROMEDRIVER_PLATFORM / driver_version / "chromedriver.exe",
        PROJECT_ROOT / CHROMEDRIVER_CACHE_DIR / driver_version / f"chromedriver-{CHROMEDRIVER_PLATFORM}" / "chromedriver.exe",
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    build_version = ".".join(driver_version.split(".")[:3])
    fallback_matches = []

    selenium_cache_root = Path.home() / ".cache" / "selenium" / "chromedriver" / CHROMEDRIVER_PLATFORM
    if selenium_cache_root.exists():
        for version_dir in selenium_cache_root.iterdir():
            candidate = version_dir / "chromedriver.exe"
            if version_dir.is_dir() and version_dir.name.startswith(build_version) and candidate.exists():
                fallback_matches.append((version_dir.name, candidate))

    project_cache_root = PROJECT_ROOT / CHROMEDRIVER_CACHE_DIR
    if project_cache_root.exists():
        for version_dir in project_cache_root.iterdir():
            candidate = version_dir / f"chromedriver-{CHROMEDRIVER_PLATFORM}" / "chromedriver.exe"
            if version_dir.is_dir() and version_dir.name.startswith(build_version) and candidate.exists():
                fallback_matches.append((version_dir.name, candidate))

    webdriver_manager_root = Path.home() / ".wdm" / "drivers" / "chromedriver" / "win64"
    if webdriver_manager_root.exists():
        for version_dir in webdriver_manager_root.iterdir():
            candidate = version_dir / "chromedriver-win32" / "chromedriver.exe"
            if version_dir.is_dir() and version_dir.name.startswith(build_version) and candidate.exists():
                fallback_matches.append((version_dir.name, candidate))

    if fallback_matches:
        fallback_matches.sort(key=lambda item: tuple(int(part) for part in item[0].split(".")), reverse=True)
        matched_version, matched_path = fallback_matches[0]
        print(f"[信息] 使用同 build 已缓存 chromedriver: {matched_version}")
        return str(matched_path)

    return None


def download_file(url, target_path):
    """下载文件，失败时回退到 PowerShell。"""
    try:
        with urllib.request.urlopen(url, timeout=WEBDRIVER_DOWNLOAD_TIMEOUT) as response, open(target_path, "wb") as target:
            shutil.copyfileobj(response, target)
        if target_path.exists() and target_path.stat().st_size > 0:
            return True
    except Exception:
        pass

    try:
        ps_command = f"Invoke-WebRequest -UseBasicParsing '{url}' -OutFile '{target_path}'"
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=WEBDRIVER_DOWNLOAD_TIMEOUT,
            check=False,
        )
        return result.returncode == 0 and target_path.exists() and target_path.stat().st_size > 0
    except Exception:
        return False


def ensure_local_chromedriver(chrome_binary_path):
    """下载并缓存匹配当前 Chrome 的官方 chromedriver。"""
    chrome_version = detect_chrome_version(chrome_binary_path)
    if not chrome_version:
        print("[错误] 无法识别本机 Chrome 版本")
        return None

    driver_version = resolve_chromedriver_version(chrome_version)
    if not driver_version:
        print("[错误] 无法解析 chromedriver 版本")
        return None

    existing_driver = find_existing_chromedriver(driver_version)
    if existing_driver:
        actual_version = Path(existing_driver).parent.name
        if actual_version == "chromedriver-win32":
            actual_version = Path(existing_driver).parent.parent.name
        print(f"[信息] 使用已缓存 chromedriver: {actual_version}")
        return existing_driver

    cache_root = PROJECT_ROOT / CHROMEDRIVER_CACHE_DIR / driver_version
    driver_dir = cache_root / f"chromedriver-{CHROMEDRIVER_PLATFORM}"
    driver_path = driver_dir / "chromedriver.exe"
    if driver_path.exists():
        return str(driver_path)

    cache_root.mkdir(parents=True, exist_ok=True)
    zip_path = cache_root / "chromedriver.zip"
    download_url = (
        f"https://storage.googleapis.com/chrome-for-testing-public/"
        f"{driver_version}/{CHROMEDRIVER_PLATFORM}/chromedriver-{CHROMEDRIVER_PLATFORM}.zip"
    )

    try:
        print(f"[信息] 下载 chromedriver {driver_version} ...")
        if not download_file(download_url, zip_path):
            raise RuntimeError("下载结果为空或下载失败")

        with zipfile.ZipFile(zip_path, "r") as zip_file:
            zip_file.extractall(cache_root)
    except Exception as e:
        print(f"[错误] 下载 chromedriver 失败: {e}")
        return None
    finally:
        if zip_path.exists():
            zip_path.unlink(missing_ok=True)

    if driver_path.exists():
        return str(driver_path)

    print("[错误] chromedriver 解压后未找到可执行文件")
    return None


def build_chrome_options(incognito=True):
    """构建统一的 Chrome 启动参数。"""
    options = webdriver.ChromeOptions()

    if incognito:
        options.add_argument("--incognito")

    chrome_binary = resolve_chrome_binary_path()
    if chrome_binary:
        options.binary_location = chrome_binary

    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--start-maximized")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-hang-monitor")

    return options


def init_chrome_driver_with_retry(scene_name, incognito=True):
    """稳定启动 Chrome：本地缓存官方驱动 + 显式 Service + 重试。"""
    if not SELENIUM_AVAILABLE:
        print(f"[错误] {scene_name} 浏览器初始化失败：未安装 selenium")
        return None

    chrome_binary = resolve_chrome_binary_path()
    if not chrome_binary:
        print(f"[错误] {scene_name} 浏览器初始化失败：未找到 Chrome 安装路径")
        return None

    driver_path = ensure_local_chromedriver(chrome_binary)
    if not driver_path:
        print(f"[错误] {scene_name} 浏览器初始化失败：无法准备 chromedriver")
        return None

    last_error = None
    for attempt in range(1, WEBDRIVER_STARTUP_RETRIES + 1):
        try:
            if attempt > 1:
                print(f"[重试] 第 {attempt}/{WEBDRIVER_STARTUP_RETRIES} 次启动浏览器...")

            options = build_chrome_options(incognito=incognito)
            service = Service(executable_path=driver_path)
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except Exception as e:
            last_error = e
            print(f"[警告] {scene_name} 浏览器启动失败（第 {attempt} 次）: {e}")
            if attempt < WEBDRIVER_STARTUP_RETRIES:
                time.sleep(WEBDRIVER_STARTUP_RETRY_DELAY)

    print(f"[错误] {scene_name} 浏览器初始化失败，已重试 {WEBDRIVER_STARTUP_RETRIES} 次")
    if last_error:
        print(f"[错误] 最终错误: {last_error}")
    return None


class ChromeBrowser:
    """使用 undetected-chromedriver + 深度反检测的浏览器控制器"""
    
    def __init__(self):
        self.driver = None
    
    def start_browser(self, incognito=True):
        """
        启动 Chrome 浏览器。
        使用与参考实现一致的稳定本地驱动链路。
        """
        print("[信息] 正在启动Chrome浏览器...")

        driver = self._start_normal_browser(incognito)
        if driver:
            return driver

        raise Exception("启动Chrome浏览器失败")
    
    def _start_undetected_browser(self, incognito=True):
        """使用 undetected-chromedriver 启动浏览器 + 深度反检测"""
        try:
            options = uc.ChromeOptions()
            
            # 无痕模式
            if incognito:
                options.add_argument("--incognito")
                print("[信息] 已启用无痕模式")
            
            # 设置语言 - 使用更真实的语言设置
            options.add_argument("--lang=en-US,en;q=0.9")
            
            # 窗口设置
            options.add_argument("--start-maximized")
            
            # 禁用通知
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-popup-blocking")
            
            # 额外的反检测参数
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")
            
            # 禁用密码保存弹窗
            prefs = {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.default_content_setting_values.javascript": 1,
                "profile.managed_default_content_settings.javascript": 1,
                "profile.default_content_setting_values.notifications": 2,
                "webrtc.ip_handling_policy": "disable_non_proxied_udp",
                "webrtc.multiple_routes_enabled": False,
                "webrtc.nonproxied_udp_enabled": False
            }
            options.add_experimental_option("prefs", prefs)
            
            # 创建 undetected-chromedriver 实例
            self.driver = uc.Chrome(
                options=options,
                use_subprocess=True,  # 使用子进程模式
                version_main=None,    # 自动检测Chrome版本
            )
            
            # 注入深度反检测JS
            self._inject_stealth_js()
            
            # 设置页面加载超时
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(10)
            
            print("[成功] Chrome浏览器启动成功（undetected + 深度反检测模式）")
            return self.driver
            
        except Exception as e:
            print(f"[错误] undetected-chromedriver 启动失败: {e}")
            print("[尝试] 回退到普通模式...")
            return self._start_normal_browser(incognito)
    
    def _warmup_browser(self):
        """浏览器预热 - 先访问其他网站建立正常浏览历史"""
        print("[预热] 模拟正常浏览行为...")
        try:
            # 先访问 Google
            self.driver.get("https://www.google.com")
            time.sleep(random.uniform(2, 4))
            
            # 模拟滚动
            self.driver.execute_script("window.scrollTo(0, 300);")
            time.sleep(random.uniform(1, 2))
            
            # 搜索 tidal music
            try:
                search_box = self.driver.find_element("name", "q")
                search_box.click()
                time.sleep(random.uniform(0.5, 1))
                
                # 模拟人类打字
                for char in "tidal music streaming":
                    search_box.send_keys(char)
                    time.sleep(random.uniform(0.08, 0.2))
                
                time.sleep(random.uniform(1, 2))
                search_box.send_keys("\n")
                time.sleep(random.uniform(3, 5))
                
                # 滚动查看搜索结果
                self.driver.execute_script("window.scrollTo(0, 500);")
                time.sleep(random.uniform(2, 4))
                
            except:
                pass
            
            print("[预热] 完成")
        except Exception as e:
            print(f"[预热] 跳过: {e}")
    
    def _inject_stealth_js(self):
        """注入与参考实现一致的最小 webdriver 隐藏脚本。"""
        stealth_js = """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        """
        
        try:
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": stealth_js
            })
            print("[信息] 已注入最小化 webdriver 隐藏脚本")
        except Exception as e:
            print(f"[警告] 反检测脚本注入失败: {e}")
    
    def _start_normal_browser(self, incognito=True):
        """稳定本地驱动模式启动浏览器。"""
        self.driver = init_chrome_driver_with_retry("Chrome", incognito=incognito)
        if not self.driver:
            return None

        try:
            self._inject_stealth_js()
        except Exception as e:
            print(f"[警告] 深度反检测脚本注入失败: {e}")

        self.driver.set_page_load_timeout(60)
        self.driver.implicitly_wait(10)

        mode_text = "稳定本地驱动 + 无痕模式" if incognito else "稳定本地驱动模式"
        print(f"[成功] Chrome浏览器启动成功（{mode_text}）")
        return self.driver
    
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
