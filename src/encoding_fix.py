#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编码修复模块
统一设置程序编码，解决Windows下中文显示问题
"""

import sys
import os


def setup_encoding():
    """设置UTF-8编码"""
    try:
        # Windows系统编码设置
        if sys.platform == "win32":
            # 设置环境变量
            os.environ['PYTHONIOENCODING'] = 'utf-8'
            
            # 重新配置标准输出/错误流编码
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8')
            if hasattr(sys.stderr, 'reconfigure'):  
                sys.stderr.reconfigure(encoding='utf-8')
            
            # 设置控制台代码页为UTF-8
            try:
                os.system('chcp 65001 >nul 2>&1')
            except:
                pass
                
        return True
    except Exception as e:
        print(f"Warning: Failed to setup encoding: {e}")
        return False


# 自动执行编码设置
setup_encoding()