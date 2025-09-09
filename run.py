#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动脚本 - 从根目录启动调度器
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 导入并运行调度器的主函数
from scheduler import main

if __name__ == "__main__":
    # 调用main函数处理命令行参数
    main()