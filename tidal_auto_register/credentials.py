# -*- coding: utf-8 -*-
"""
凭证配置文件
存储邮箱登录信息和其他敏感数据
注意：此文件包含敏感信息，请勿分享或上传到公开仓库
"""

# 邮箱配置
EMAIL_CONFIG = {
    # 邮箱登录页面地址
    "url": "https://mail.xoxome.online/dashboard",
    
    # 登录凭证
    "username": "stevenkfwcwt",
    "password": "stevenkfwcwt1006",
    
    # 邮箱域名（用于生成完整邮箱地址）
    "domain": "xoxome.online",
}

# 完整邮箱地址
def get_full_email():
    """获取完整邮箱地址"""
    return f"{EMAIL_CONFIG['username']}@{EMAIL_CONFIG['domain']}"
