#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置管理
"""

import os
from datetime import datetime

# 飞书OAuth配置
OAUTH_CONFIG = {
    "client_id": "cli_a735216a7178d009",
    "client_secret": "CVk3xzJcAbhhdtxiR5yNIhsoPT68h3nv",
    "redirect_uri": "https://example.com/oauth2/callback",
    "scope": "calendar:calendar:readonly calendar:calendar calendar:calendar:read",
    "state": "abc123"
}

# 飞书API配置  
API_CONFIG = {
    "base_url": "https://open.larksuite.com/open-apis",
    "calendar_url": "https://open.larksuite.com/open-apis/calendar/v4/calendars",
    "events_url_template": "https://open.larksuite.com/open-apis/calendar/v4/calendars/{}/events",
    "token_url": "https://open.larksuite.com/open-apis/authen/v2/oauth/token"
}

# 飞书表格配置
TABLE_CONFIG = {
    "app_token": "YqkXbLfb8a0VYGsInq4uTAjpsUb",
    "table_id": "tbl9yjYfvEzsQ2No",
    "app_id": "cli_a735216a7178d009",
    "app_secret": "CVk3xzJcAbhhdtxiR5yNIhsoPT68h3nv"
}

# 飞书Lark配置（从lark_config.py合并）
LARK_CONFIG = {
    "app_id": "cli_a735216a7178d009",
    "app_secret": "CVk3xzJcAbhhdtxiR5yNIhsoPT68h3nv",
    "base_url": "https://open.feishu.cn/open-apis"
}

# Token过期时间
TOKEN_EXPIRE_TIME = 7200

# 文件路径配置
PATHS = {
    "token_file": "data/feishu_data.json",
    "personal_calendars": "data/personal_calendars",
    "calendar_history": "data/calendar_history", 
    "record_tracking": "data/record_tracking",
    "scheduler_logs": "data/scheduler_logs",
    "db_file": "data/record_tracking/upload_tracker.db",
    "pid_file": "scheduler.pid",
    "result_file": "data/calendar_result.txt"
}

# 调度配置
SCHEDULE_CONFIG = {
    "work_time": "10:00",  # 工作日执行时间
    "check_interval": 60,  # 检查间隔（秒）
    "batch_size": 50,      # 批量上传大小
    "timeout": 30          # 请求超时（秒）
}

def ensure_directories():
    """确保必要的目录存在"""
    for path_key in ["personal_calendars", "calendar_history", "record_tracking", "scheduler_logs"]:
        path = PATHS[path_key]
        if not os.path.exists(path):
            os.makedirs(path)

def get_current_time():
    """获取当前时间字符串"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def get_batch_id():
    """生成批次ID"""
    return datetime.now().strftime('%Y%m%d_%H%M%S')