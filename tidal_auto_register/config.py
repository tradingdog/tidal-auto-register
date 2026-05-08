# -*- coding: utf-8 -*-
"""
Tidal 自动注册系统 - 配置文件
"""

class Config:
    # AdsPower配置
    ADSPOWER_API_URL = "http://local.adspower.net:50325"
    BROWSER_PROFILE_ID = "50355"  # 浏览器配置ID，留空则使用第一个可用的
    
    # 临时邮箱配置
    TEMP_EMAIL_URL = "https://mail.cx/"
    EMAIL_CHECK_INTERVAL = 3  # 检查邮件间隔（秒）
    EMAIL_CHECK_MAX_ATTEMPTS = 60  # 最大检查次数
    
    # Tidal配置
    TIDAL_URL = "https://tidal.com/"
    
    # 卡片信息文件路径（相对于项目根目录）
    CARD_FILE_PATH = "d:/my_program/Account_Tidal_Qobuz/card.txt"
    
    # 账号保存文件
    ACCOUNTS_FILE_PATH = "d:/my_program/Account_Tidal_Qobuz/tidal_auto_register/data/accounts.txt"
    
    # 人类行为参数
    TYPING_MIN_DELAY = 0.1  # 最小打字间隔（秒）
    TYPING_MAX_DELAY = 0.3  # 最大打字间隔
    CLICK_DELAY_MIN = 0.12    # 点击前最小延迟
    CLICK_DELAY_MAX = 0.34    # 点击前最大延迟
    
    # 页面等待参数
    PAGE_LOAD_TIMEOUT = 31   # 页面加载超时（秒）
    ELEMENT_WAIT_TIMEOUT = 13  # 元素等待超时（秒）
    
    # 随机延迟参数
    SHORT_DELAY = (0.3, 1.8)   # 短延迟范围
    MEDIUM_DELAY = (1.8, 3.8)  # 中等延迟范围
    LONG_DELAY = (3.8, 5.5)    # 长延迟范围
    
    # 密码配置
    PASSWORD_LENGTH = 12
    PASSWORD_PREFIX = "Tidal"  # 密码前缀
