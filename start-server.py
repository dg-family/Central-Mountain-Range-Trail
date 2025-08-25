#!/usr/bin/env python3
"""
簡單的HTTP服務器，用於本地開發
解決瀏覽器CORS問題
"""

import http.server
import socketserver
import os
import sys

PORT = 8000

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # 添加CORS頭
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        # 處理預檢請求
        self.send_response(200)
        self.end_headers()

if __name__ == "__main__":
    # 切換到腳本所在目錄
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        with socketserver.TCPServer(("", PORT), CORSHTTPRequestHandler) as httpd:
            print(f"🚀 服務器啟動在 http://localhost:{PORT}")
            print(f"📁 服務目錄: {os.getcwd()}")
            print(f"🗺️  地圖測試: http://localhost:{PORT}/simple-map-test.html")
            print(f"📋 行程表: http://localhost:{PORT}/index.html")
            print(f"📦 補給點: http://localhost:{PORT}/supplies.html")
            print("\n按 Ctrl+C 停止服務器")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服務器已停止")
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ 端口 {PORT} 已被占用")
            print(f"請嘗試其他端口: python start-server.py {PORT + 1}")
        else:
            print(f"❌ 啟動服務器失敗: {e}")
        sys.exit(1)
