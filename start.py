#!/usr/bin/env python3
"""
中央山脈步道路線系統 - 啟動腳本
這是 unified_server.py 的簡化版本，提供更簡單的啟動方式
"""

import sys
import os
from pathlib import Path

# 添加當前目錄到 Python 路徑
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 導入並運行統一服務器
from unified_server import main

if __name__ == '__main__':
    main()

