# -*- coding: utf-8 -*-
"""
卡片信息读取模块
从card.txt文件读取支付卡信息
"""


class CardReader:
    """卡片信息读取器"""
    
    def __init__(self, file_path):
        self.file_path = file_path
        self.card_info = None
        self._load_card()
    
    def _load_card(self):
        """加载卡片信息"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            
            if len(lines) < 5:
                raise ValueError(f"卡片信息不完整，需要至少5行数据，当前只有{len(lines)}行")
            
            # 解析地址（可能包含逗号分隔的城市、州、邮编）
            address_line = lines[4]
            address_parts = [p.strip() for p in address_line.split(',')]
            
            self.card_info = {
                "card_number": lines[0].strip(),           # 卡号
                "card_holder": lines[1].strip(),           # 持卡人姓名
                "expiry": lines[2].strip(),                # 有效期 MM/YY
                "cvv": lines[3].strip(),                   # CVV
                "full_address": address_line,              # 完整地址
                "street": address_parts[0] if len(address_parts) > 0 else "",
                "city": address_parts[1] if len(address_parts) > 1 else "",
                "state": address_parts[2] if len(address_parts) > 2 else "",
                "zip_code": address_parts[3] if len(address_parts) > 3 else "",
            }
            
            # 解析有效期
            if '/' in self.card_info["expiry"]:
                parts = self.card_info["expiry"].split('/')
                self.card_info["expiry_month"] = parts[0]
                self.card_info["expiry_year"] = parts[1]
            
            print(f"[信息] 卡片信息加载成功: ****{self.card_info['card_number'][-4:]}")
            
        except FileNotFoundError:
            raise FileNotFoundError(f"找不到卡片文件: {self.file_path}")
        except Exception as e:
            raise Exception(f"读取卡片信息失败: {e}")
    
    def reload(self):
        """重新加载卡片信息（用于卡片更新后）"""
        self._load_card()
    
    def get_card_number(self):
        """获取卡号"""
        return self.card_info.get("card_number", "")
    
    def get_card_holder(self):
        """获取持卡人姓名"""
        return self.card_info.get("card_holder", "")
    
    def get_expiry(self):
        """获取有效期（MM/YY格式）"""
        return self.card_info.get("expiry", "")
    
    def get_expiry_month(self):
        """获取有效期月份"""
        return self.card_info.get("expiry_month", "")
    
    def get_expiry_year(self):
        """获取有效期年份"""
        return self.card_info.get("expiry_year", "")
    
    def get_cvv(self):
        """获取CVV"""
        return self.card_info.get("cvv", "")
    
    def get_street(self):
        """获取街道地址"""
        return self.card_info.get("street", "")
    
    def get_city(self):
        """获取城市"""
        return self.card_info.get("city", "")
    
    def get_state(self):
        """获取州/省"""
        return self.card_info.get("state", "")
    
    def get_zip_code(self):
        """获取邮编"""
        return self.card_info.get("zip_code", "")
    
    def get_first_name(self):
        """获取名字（姓名的第一部分）"""
        name_parts = self.card_info.get("card_holder", "").split()
        return name_parts[0] if name_parts else ""
    
    def get_last_name(self):
        """获取姓氏（姓名的最后部分）"""
        name_parts = self.card_info.get("card_holder", "").split()
        return name_parts[-1] if len(name_parts) > 1 else ""
    
    def get_all(self):
        """获取所有卡片信息"""
        return self.card_info.copy()
    
    def __str__(self):
        """打印卡片信息摘要"""
        if self.card_info:
            return (
                f"卡号: ****{self.card_info['card_number'][-4:]}\n"
                f"持卡人: {self.card_info['card_holder']}\n"
                f"有效期: {self.card_info['expiry']}\n"
                f"地址: {self.card_info['city']}, {self.card_info['state']}"
            )
        return "卡片信息未加载"
