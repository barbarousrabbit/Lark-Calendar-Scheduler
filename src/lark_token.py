#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书API Token获取模块
"""

import requests
import json
import time
from typing import Optional
from config import LARK_CONFIG, TOKEN_EXPIRE_TIME

class LarkTokenManager:
    """飞书Token管理类"""
    
    def __init__(self):
        """初始化Token管理器"""
        self.app_id = LARK_CONFIG["app_id"]
        self.app_secret = LARK_CONFIG["app_secret"]
        self.base_url = LARK_CONFIG["base_url"]
        
        # Token缓存
        self._cached_token = None
        self._token_expire_time = 0
        
    def get_tenant_access_token(self) -> Optional[str]:
        """获取tenant_access_token（支持缓存）"""
        # 检查缓存
        current_time = time.time()
        if (self._cached_token and current_time < self._token_expire_time):
            return self._cached_token
        
        # 获取新token
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/json; charset=utf-8'
        }
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    token = result.get('tenant_access_token')
                    # 缓存token
                    self._cached_token = token
                    self._token_expire_time = current_time + TOKEN_EXPIRE_TIME - 300
                    return token
            return None
        except:
            return None

# 全局token管理器
_token_manager = LarkTokenManager()

def get_lark_token() -> Optional[str]:
    """获取飞书token的便捷函数"""
    return _token_manager.get_tenant_access_token()