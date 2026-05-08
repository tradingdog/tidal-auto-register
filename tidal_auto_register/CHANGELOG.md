# CHANGELOG

## v0.2.19：新增运行日志与即时账号快照

- main.py 新增每次运行独立日志文件能力：程序启动即在 data/logs/runtime 下创建 run_日期时间.log，并把终端输出同步写入该文件。
- main.py 新增账号即时快照能力：当 Tidal 注册步骤完成并拿到邮箱/密码后，立即创建 accounts_日期时间.txt（位于 data 目录）保存该账号信息，不再等到后续步骤结束。
- 保留原有 data/accounts.txt 的步骤10追加保存逻辑，形成“即时快照 + 汇总历史”双轨记录。
- 同步更新 main.py、项目步骤.md、项目记忆文档.md 到 v0.2.19。

## v0.2.18：首开改为 link.tidal 预检查并分离主注册标签

- modules/tidal_register.py 的首页预检查入口改为 `https://link.tidal.com/RGZST`，并把该预检查等待固定为 20 秒，用于先做访问受限识别。
- 访问受限检测通过后，不再直接在预检查页继续主流程，而是新开一个 `https://tidal.com/` 标签页作为主注册页，降低预检查页对后续流程的干扰。
- main.py 的步骤 4 回切逻辑由固定 `tab 0` 改为优先切到 `switch_to_primary_tidal_tab()` 指向的主 Tidal 标签，避免切错到 link 预检查页。
- 同步更新 main.py、项目步骤.md、项目记忆文档.md 到 v0.2.18。

## v0.2.17：对齐 cankao 的 Tidal 打开口径

- 对比 cankao/main.py 后，收敛 modules/adspower.py 的稳定本地驱动参数到参考实现口径：保留无痕、最小反自动化参数和后台节流参数，移除额外语言、popup、sandbox、dev-shm、webrtc/prefs 等附加项。
- 浏览器启动链改为与参考一致：仅使用稳定本地驱动链路，不再在主链路失败后自动回退 undetected-chromedriver，避免不同启动指纹带来的不可控差异。
- modules/tidal_register.py 的首页预检查改回参考式 driver.get 直开 tidal.com，再做等待与访问受限检测，不再使用地址栏坐标键鼠输入路径。
- 同步更新 main.py、项目步骤.md、项目记忆文档.md 到 v0.2.17。

## v0.2.16：补强地址栏回车提交流程

- 更新 utils/human_behavior.py，把特殊按键改成更稳的 keyDown/keyUp 按下再抬起，并新增 human_hotkey 组合键能力，降低浏览器地址栏里回车、退格、Ctrl+A 这类按键丢失的概率。
- 更新 modules/tidal_register.py，地址栏点击后会先 Ctrl+L 聚焦、Ctrl+A 全选并退格清空，再按人类节奏输入 tidal.com，并在首次回车未触发跳转时自动补发一次回车。
- 新增地址栏跳转确认逻辑：如果当前仍是 data: 或 about:blank 这类空白页，代码会先验证 URL 是否真的开始跳转，避免“看起来按了回车，实际上没有提交”。
- 同步更新 main.py、项目步骤.md、项目记忆文档.md 到 v0.2.16。

## v0.2.15：改为地址栏坐标输入打开 Tidal 首页

- 更新 modules/tidal_register.py，Chrome 启动后不再直接调用 driver.get 打开首页，而是先等待 5 秒，点击浏览器地址栏坐标 279,65，再按人类节奏输入 tidal.com 并回车，随后固定等待 10 秒再做访问受限检测。
- 更新 utils/tidal_coordinates.py，新增 TD-00-URL-BAR 固定坐标和 TD-00-BROWSER-READY 等待配置，保持 Tidal 相关固定坐标和等待时长仍统一收口在同一配置文件。
- 保留桌面自动化不可用时的 driver.get 兜底，避免 PyAutoGUI 不可用时主流程完全无法启动。
- 同步更新 main.py、项目步骤.md、项目记忆文档.md 到 v0.2.15。

## v0.2.14：显式允许 JavaScript 并收回过重反检测注入

- 更新 modules/adspower.py，在 Chrome 启动 prefs 中显式允许 JavaScript，避免挑战页误报“您的电脑设定/软体阻挡网页 Javascript 程式运行”。
- 将浏览器启动阶段的深度反检测脚本收回为参考实现同级别的最小版本，只保留 navigator.webdriver 隐藏，移除 permissions、plugins、window.chrome、WebGL 等高干扰伪装。
- 保持无痕模式、本地 chromedriver 缓存复用和截图记录机制不变，只定点修复 Tidal 挑战页脚本兼容性问题。
- 同步更新 main.py、项目步骤.md、项目记忆文档.md 到 v0.2.14。

## v0.2.13：补强受限识别并记录全流程截图

- 更新 modules/tidal_register.py，把 Tidal 首页访问受限判断补强为“多尺度模板匹配 + 页面文本多来源检测 + access_restricted 低阈值兜底”，修复明明已显示受限却被判成正常的问题。
- 新增 utils/step_screenshot.py，并在 main.py、modules/tidal_register.py、modules/temp_email.py 中接入运行期截图记录；现在每次程序执行都会新建一个时间戳目录，子步骤完成后立即保存全屏截图和 manifest.jsonl。
- 截图目录固定写入 data/logs/screenshots/本次运行时间戳，截图文件名包含步骤名、日期、时间和毫秒时间戳，便于回溯具体出错节点。
- 同步更新 main.py、项目步骤.md、项目记忆文档.md 到 v0.2.13。

## v0.2.12：先做 Tidal 访问预检查再生成风车邮箱

- 调整主程序顺序：浏览器启动后先打开 Tidal 首页，固定等待 10 秒并匹配 access_restricted.png；若命中访问受限则等待用户手动处理并输入 y 后再继续。
- 更新 modules/temp_email.py，增强风车邮箱新版前端的“生成邮箱”和“复制”按钮定位，生成后固定等待 10 秒，再优先从剪贴板和生成结果输入框获取邮箱地址。
- 更新 modules/tidal_register.py，新增 Tidal 首页访问预检查逻辑，并让默认注册入口也走这套顺序，避免 main_attach 等旧入口继续先消耗邮箱积分。
- 重写 项目步骤.md 中的风车邮箱步骤明细，并同步 main.py、项目记忆文档.md 到 v0.2.12。

## v0.2.11：改用稳定本地驱动链路加速 Chrome 启动

- 重构 modules/adspower.py 的浏览器启动逻辑，优先使用“检测本机 Chrome 版本 + 匹配 chromedriver + 显式 Service + 无痕参数”的稳定链路，彻底绕开 Selenium Manager 的慢启动路径。
- chromedriver 缓存匹配新增“同 build 版本复用”，即使补丁版本不同也能直接命中本地缓存，避免再次进入下载流程。
- 保留 undetected-chromedriver 作为备用回退模式，但不再作为默认首选启动方式。
- 同步更新 main.py、项目步骤.md、项目记忆文档.md 到 v0.2.11。

## v0.2.10：转移模板文件到 images 并兼容旧目录

- 已将 template 目录中的 Tidal 模板 PNG 全部转移到 images 目录，避免后续因为目录放错导致模板匹配失效。
- 更新 utils/tidal_coordinates.py，模板路径现在优先读取 images，若旧目录 template 中仍存在同名文件也会自动兜底兼容。
- 同步更新 项目步骤.md、项目记忆文档.md 和 main.py 的版本展示为 v0.2.10。

## v0.2.9：接入 Tidal 专用坐标模板脚本并重写步骤文档

- 新增并启用 Tidal 专用坐标配置文件 utils/tidal_coordinates.py，把固定坐标、模板文件、滚轮次数、等待时长和按键范围统一收口管理。
- 更新 modules/tidal_register.py，让 Tidal 首页弹窗、注册、订阅登录、套餐选择、支付和取消订阅优先走固定坐标或模板匹配，再保留 Selenium 元素兜底。
- 保持风车邮箱流程独立，不把邮箱站点坐标写入 Tidal 专用坐标脚本。
- 重写 项目步骤.md 为按执行顺序排列的步骤 ID 文档，并同步更新 项目记忆文档.md 和 main.py 版本展示为 v0.2.9。

## v0.2.8：抑制 PyAutoGUI 检测阶段的 cv2 噪声输出

- 在 human_behavior 和 tidal_register 中把 PyAutoGUI、cv2、numpy、mss 的探测导入改成静默加载，避免 NumPy ABI 诊断把整段 traceback 直接打印到控制台。
- 保留 v0.2.7 的降级逻辑，当前环境若仍存在 ABI 冲突，会继续自动回退到 Selenium 模式，但输出更干净，便于判断真实错误。
- 统一 main.py 中展示的版本号为 v0.2.8。

## v0.2.7：修复 PyAutoGUI 与 NumPy 冲突导致的启动崩溃

- 修复 human_behavior 中只捕获 ImportError 的问题，改为在 PyAutoGUI 因 cv2 或 NumPy ABI 冲突加载失败时自动回退到 Selenium 模式。
- 为 tidal_register 中几个直接 import pyautogui 或 cv2 的坐标方法补充可降级导入与元素点击兜底，避免程序在导入阶段或运行阶段直接崩溃。
- 保留后续坐标化改造空间，当前目标优先改为“程序先能启动，再逐项替换为固定坐标或模板匹配”。
- 统一 main.py 中展示的版本号为 v0.2.7。

## v0.2.6：步骤文档改为 Markdown 并补充待鼠标化清单

- 将 项目步骤.txt 改为 项目步骤.md，重排为更易读的 Markdown 结构。
- 在步骤文档中新增交互编号，区分“已坐标化”“半模拟”“非模拟”，把仍未完成固定坐标或模板匹配鼠标化的按钮、输入框、下拉框全部列出。
- 更新项目记忆文档中的步骤文档引用和维护要求，统一改为 项目步骤.md。
- 统一 main.py 中展示的版本号为 v0.2.6。

## v0.2.5：补充项目步骤文档并统一维护规则

- 新增 项目步骤.txt，按自然语言整理完整自动模式和连接已打开浏览器模式的当前执行流程。
- 更新 项目记忆文档，补充版本说明规范、Git 提交标题规范、CHANGELOG 同步要求和 项目步骤.txt 同步要求。
- 校正文档中的关键坐标与实现现状，明确后续优先优化为全流程模拟鼠标加固定坐标或模板匹配坐标。
- 统一 main.py 中展示的版本号为 v0.2.5。