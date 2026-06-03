#!/usr/bin/env python3
"""
同時啟動靜態文件服務器和 API 服務器
"""

import subprocess
import time
import sys
import os
from pathlib import Path

def start_servers():
    """啟動兩個服務器"""
    print("🚀 啟動中央山脈步道路線系統")
    print("📁 工作目錄:", Path(__file__).parent)
    print("\n🌐 服務器配置:")
    print("   - 靜態文件服務器: http://localhost:8000/ (start-server.py)")
    print("   - API 服務器: http://localhost:5001/ (trail_server.py)")
    print("\n📋 可用頁面:")
    print("   - 主頁面: http://localhost:8000/")
    print("   - 路線生成器: http://localhost:8000/trail_generator.html")
    print("   - 路線查看器: http://localhost:8000/trail.html")
    print("   - 地圖測試: http://localhost:8000/map-test.html")
    print("   - 行程表: http://localhost:8000/index.html")
    print("   - 補給點: http://localhost:8000/supplies.html")
    print("\n🔧 API 端點:")
    print("   - 健康檢查: http://localhost:5001/health")
    print("   - 路線生成: http://localhost:5001/generate_trail")
    print("\n按 Ctrl+C 停止所有服務器")
    
    try:
        # 啟動靜態文件服務器
        static_process = subprocess.Popen([sys.executable, "start-server.py"])
        print("✅ 靜態文件服務器已啟動 (PID: {})".format(static_process.pid))
        
        # 等待一下再啟動 API 服務器
        time.sleep(2)
        
        # 啟動 API 服務器
        api_process = subprocess.Popen([sys.executable, "trail_server.py"])
        print("✅ API 服務器已啟動 (PID: {})".format(api_process.pid))
        
        print("\n🎉 所有服務器已啟動完成！")
        print("💡 提示: 路線生成器會自動連接到 API 服務器")
        
        # 等待用戶中斷
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 正在停止服務器...")
            
    except KeyboardInterrupt:
        print("\n👋 用戶中斷")
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")
    finally:
        # 清理進程
        try:
            if 'static_process' in locals():
                static_process.terminate()
                print("✅ 靜態文件服務器已停止")
            if 'api_process' in locals():
                api_process.terminate()
                print("✅ API 服務器已停止")
        except:
            pass
        print("👋 所有服務器已停止")

if __name__ == "__main__":
    start_servers()

