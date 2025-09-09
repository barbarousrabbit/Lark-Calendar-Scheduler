#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的日志管理
"""

import encoding_fix
import json
import os
from datetime import datetime
from config import PATHS, get_current_time

class Logger:
    """简化的日志记录器"""
    
    def __init__(self, module_name="app"):
        self.module_name = module_name
        self.logs_dir = PATHS["scheduler_logs"]
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
    
    def info(self, message):
        """信息日志"""
        print(f"ℹ️ {message}")
        self._write_log("INFO", message)
    
    def success(self, message):
        """成功日志"""
        print(f"✅ {message}")
        self._write_log("SUCCESS", message)
    
    def warning(self, message):
        """警告日志"""
        print(f"⚠️ {message}")
        self._write_log("WARNING", message)
    
    def error(self, message):
        """错误日志"""
        print(f"❌ {message}")
        self._write_log("ERROR", message)
    
    def _write_log(self, level, message):
        """写入日志文件"""
        try:
            log_entry = {
                "time": get_current_time(),
                "module": self.module_name,
                "level": level,
                "message": message
            }
            
            date_str = datetime.now().strftime('%Y%m%d')
            log_file = os.path.join(self.logs_dir, f"app_{date_str}.json")
            
            logs = []
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        logs = json.load(f)
                except:
                    logs = []
            
            logs.append(log_entry)
            
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        except:
            pass  # 日志失败不影响主程序

# 全局日志器实例
logger = Logger()