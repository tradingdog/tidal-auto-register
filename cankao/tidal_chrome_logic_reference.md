# Tidal 新建播放列表 + 无痕 Chrome 启动逻辑参考文档

> **参考源文件**：`d:\my_program\Playlist\main.py`
> 所有行号均为该文件中的实际行号。

---

## 一、依赖库与导入

**参考行：163–180**

```python
# tidalapi：Tidal API 封装库
try:
    import tidalapi
    TIDAL_AVAILABLE = True
except ImportError:
    TIDAL_AVAILABLE = False

# selenium：浏览器自动化
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
```

**安装命令**：
```
pip install tidalapi selenium
```

---

## 二、关键配置常量

**参考行：195–210、228–238**

```python
# Tidal 配置
TIDAL_TRACK_COUNT_MIN = 10        # 每张专辑最少添加歌曲数
TIDAL_TRACK_COUNT_MAX = 13        # 每张专辑最多添加歌曲数
TIDAL_DELAY_MIN = 0.5             # 操作间隔最小延迟（秒）
TIDAL_DELAY_MAX = 1.0             # 操作间隔最大延迟（秒）
TIDAL_CREDENTIALS_FILE = ".tidal_credentials.json"  # 凭据缓存文件
TIDAL_EMAIL_FILE = "tidal_email.txt"                # 账号文件
WEBDRIVER_STARTUP_RETRIES = 4    # 浏览器启动最大重试次数
WEBDRIVER_STARTUP_RETRY_DELAY = 2.0
WEBDRIVER_DOWNLOAD_TIMEOUT = 30  # chromedriver 下载超时（秒）
CHROMEDRIVER_PLATFORM = "win64"
CHROMEDRIVER_CACHE_DIR = ".webdriver_cache"

# Chrome 二进制路径候选列表（Windows）
CHROME_BINARY_CANDIDATES = [
    r"C:\Users\Lenovo\AppData\Local\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]
```

---

## 三、无痕 Chrome 浏览器启动完整链路

### 3.1 查找 Chrome 可执行文件

**参考行：304–309**  
函数名：`resolve_chrome_binary_path()`

- 遍历 `CHROME_BINARY_CANDIDATES` 列表，返回第一个存在的路径。

---

### 3.2 检测本机 Chrome 版本

**参考行：312–350**  
函数名：`detect_chrome_version(chrome_binary_path)`

- 方法1：用 `subprocess` 调用 `chrome.exe --version` 获取版本字符串，正则提取 `\d+\.\d+\.\d+\.\d+`。
- 方法2（回退）：用 PowerShell 读取 `VersionInfo.ProductVersion`。

---

### 3.3 解析匹配的 chromedriver 版本

**参考行：352–367**  
函数名：`resolve_chromedriver_version(chrome_version)`

- 取 Chrome 版本前三段（如 `147.0.7727`）作为 build key。
- 请求 Google 官方 JSON 接口查询对应 chromedriver 版本：  
  `https://googlechromelabs.github.io/chrome-for-testing/latest-patch-versions-per-build.json`

---

### 3.4 查找本地已缓存的 chromedriver

**参考行：369–381**  
函数名：`find_existing_chromedriver(driver_version)`

- 检查两个候选路径：
  - `~/.cache/selenium/chromedriver/{platform}/{version}/chromedriver.exe`（selenium manager 缓存）
  - `{项目目录}/.webdriver_cache/{version}/chromedriver-win64/chromedriver.exe`（本地下载缓存）

---

### 3.5 下载 chromedriver（带 PowerShell 回退）

**参考行：383–408**  
函数名：`download_file(url, target_path)`

- 先用 `urllib.request.urlopen` 下载。
- 失败时回退到 PowerShell `Invoke-WebRequest`。

---

### 3.6 确保 chromedriver 就绪（主入口）

**参考行：408–457**  
函数名：`ensure_local_chromedriver(chrome_binary_path)`

完整流程：
1. 调用 `detect_chrome_version` 获取版本
2. 调用 `resolve_chromedriver_version` 匹配驱动版本
3. 调用 `find_existing_chromedriver` 尝试复用本地缓存
4. 若无缓存，下载官方 zip 并解压到本地缓存目录
5. 返回 `chromedriver.exe` 绝对路径

---

### 3.7 构建 Chrome 启动参数（**无痕模式在此**）

**参考行：459–483**  
函数名：`build_chrome_options()`

```python
options = webdriver.ChromeOptions()
options.add_argument("--incognito")          # ← 无痕模式关键参数

# 反自动化检测
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

options.add_argument("--start-maximized")
options.add_argument("--disable-infobars")
options.add_argument("--disable-notifications")

# 禁止后台节流（防止页面休眠）
options.add_argument("--disable-backgrounding-occluded-windows")
options.add_argument("--disable-renderer-backgrounding")
options.add_argument("--disable-background-timer-throttling")
options.add_argument("--disable-hang-monitor")
```

---

### 3.8 启动 Chrome 驱动（带重试）

**参考行：486–526**  
函数名：`init_chrome_driver_with_retry(scene_name)`

- 调用 `ensure_local_chromedriver` 准备驱动
- 调用 `build_chrome_options` 获取启动参数
- 最多重试 `WEBDRIVER_STARTUP_RETRIES`（默认4）次
- 启动后注入 JS 隐藏 `navigator.webdriver` 属性（反检测）

```python
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": "Object.defineProperty(navigator, 'webdriver', { get: () => undefined })"
})
```

---

### 3.9 Tidal 专用浏览器初始化

**参考行：527–542**  
函数名：`init_tidal_browser()`

```python
def init_tidal_browser():
    if not SELENIUM_AVAILABLE:
        print("✗ 未安装 selenium")
        return None
    driver = init_chrome_driver_with_retry("Tidal")
    return driver
```

---

## 四、Tidal OAuth 自动化登录

**参考行：543–659**  
函数名：`auto_complete_tidal_oauth(driver, auth_url, email, password)`

### 完整步骤：

1. **打开 OAuth 链接**：`driver.get(auth_url)` → 等待 5 秒
2. **输入邮箱**：  
   CSS 选择器：`input#email, input[name='email'], input[type='email']`  
   逐字符模拟输入（每字符间隔 0.02–0.08 秒）
3. **点击 Continue**：  
   CSS 选择器：`button[type='submit'], button[ui-test-id='check-user-continue-button']`
4. **等待 2 秒**
5. **输入密码**：  
   CSS 选择器：`input#password`  
   先点击获焦，再逐字符输入
6. **点击 Log In**：  
   CSS 选择器：`button[ui-test-id='login-user-login-button'], button[type='submit']`
7. **等待 5 秒**
8. **点击 Continue（设备链接页面）**：  
   CSS 选择器：`button.btn-primary, button[type='button']`  
   确认按钮文字包含 "continue"（大小写不敏感）

> 每步均用 `WebDriverWait(driver, 10).until(EC.element_to_be_clickable(...))` 等待元素可交互

---

## 五、Tidal Session 管理

### 5.1 保存登录凭据

**参考行：671–683**  
函数名：`save_tidal_credentials(session)`

保存到 `.tidal_credentials.json`，字段：`token_type`, `access_token`, `refresh_token`, `expiry_time`

### 5.2 加载登录凭据

**参考行：660–669**  
函数名：`load_tidal_credentials()`

### 5.3 带自动化浏览器的完整登录流程（核心）

**参考行：716–796**  
函数名：`login_tidal_with_automation(email, password)`

```
流程：
1. 创建 tidalapi.Session()
2. 删除旧凭据文件
3. session.login_oauth() → 获取 auth_url 和 future
4. init_tidal_browser() → 启动无痕 Chrome
5. auto_complete_tidal_oauth(driver, auth_url, email, password)
6. future.result(timeout=30) → 等待 OAuth 完成
7. session.check_login() → 验证登录状态
8. save_tidal_credentials(session) → 保存凭据
9. 返回 (session, driver)
```

### 5.4 Token 刷新（当 401 错误时调用）

**参考行：797–826**  
函数名：`refresh_tidal_session(session)`

- 先尝试 `session.token_refresh(session.refresh_token)`
- 失败则重新走 `session.login_oauth()` 流程（不启动浏览器，打印链接让用户手动访问）

---

## 六、Tidal 播放列表操作

### 6.1 获取或新建播放列表

**参考行：973–985**  
函数名：`get_or_create_playlist_on_tidal(session, playlist_name, description="")`

```python
user_playlists = session.user.playlists()
for playlist in user_playlists:
    if playlist.name.lower() == playlist_name.lower():
        return playlist, False  # 已存在

playlist = session.user.create_playlist(playlist_name, description)
return playlist, True  # 新建
```

### 6.2 向播放列表添加歌曲

**参考行：987–1090**  
函数名：`add_tracks_to_playlist_with_delay(session, playlist, tracks, track_count)`

- 从专辑曲目中随机抽取 `track_count` 首
- 优先尝试**批量添加** `playlist.add(track_ids)`
- 遇到 401/412 错误时先刷新 Session（`refresh_tidal_session`），然后重试
- 批量失败后降级为**逐首添加**，每首间随机延迟

---

## 七、单账号完整处理流程

**参考行：1251–1364**  
函数名：`run_tidal_for_single_account(account_info, account_index, total_accounts, base_dir, args)`

```
步骤：
1. login_tidal_with_automation(email, password)
   → 返回 (session, driver)

2. 生成专辑列表（随机抽取 + 历史权重去重）
   → 写入 T+{timestamp}.txt 文件

3. process_tidal_playlist(session, txt_path, track_min, track_max)
   → 解析 txt → 逐专辑搜索 → get_or_create_playlist → add_tracks

4. driver.quit()  # 关闭浏览器
```

---

## 八、多账号入口

**参考行：3311–3450（main() 函数内）**

账号文件 `tidal_email.txt` 格式（空行分隔不同账号）：
```
邮箱1
密码1

邮箱2
密码2
```

加载函数：`load_tidal_accounts()`（**参考行：247–270**）

循环调用 `run_tidal_for_single_account`，账号间等待 3 秒。

---

## 九、关键依赖关系图

```
main()
 └─ run_tidal_for_single_account()         行 1251
     ├─ login_tidal_with_automation()      行 716
     │   ├─ tidalapi.Session().login_oauth()
     │   ├─ init_tidal_browser()           行 527
     │   │   └─ init_chrome_driver_with_retry()  行 486
     │   │       ├─ resolve_chrome_binary_path()  行 304
     │   │       ├─ ensure_local_chromedriver()   行 408
     │   │       │   ├─ detect_chrome_version()   行 312
     │   │       │   ├─ resolve_chromedriver_version() 行 352
     │   │       │   ├─ find_existing_chromedriver()  行 369
     │   │       │   └─ download_file()           行 383
     │   │       └─ build_chrome_options()        行 459  ← 无痕模式
     │   └─ auto_complete_tidal_oauth()           行 543
     │       └─ (selenium 填邮箱/密码/点击按钮)
     └─ process_tidal_playlist()                  行 1091
         ├─ get_or_create_playlist_on_tidal()     行 973
         └─ add_tracks_to_playlist_with_delay()   行 987
             └─ refresh_tidal_session() (按需)    行 797
```

---

## 十、新程序实现要点

1. **无痕模式**：`--incognito` 参数加在 `ChromeOptions` 上（见 §3.7）
2. **驱动版本自动匹配**：不要硬编码驱动版本，走"检测Chrome版本→查询匹配驱动→下载/复用"链路（见 §3.2–3.6）
3. **反检测**：启动后立即用 CDP 注入 JS 覆盖 `navigator.webdriver`（见 §3.8）
4. **OAuth 流程**：tidalapi 的 `session.login_oauth()` 会返回一个 `future`，浏览器完成授权点击 Continue 后 future 才会 resolve（见 §4、§5.3）
5. **401 处理**：添加歌曲时遇到 401/412 要先刷 session 再重试，不能直接放弃（见 §6.2）
6. **新建 vs 复用播放列表**：`create_playlist` 之前先遍历检查是否已存在同名列表（见 §6.1）
