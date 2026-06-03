#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中央山脈步道路線生成器 Web 服務器
提供 Web 界面來執行 find_trail.py
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import tempfile
import os
import subprocess
import sys
from pathlib import Path

app = Flask(__name__)
CORS(app)  # 啟用 CORS 支援

# 確保 find_trail.py 存在
SCRIPT_DIR = Path(__file__).parent
FIND_TRAIL_SCRIPT = SCRIPT_DIR / "find_trail.py"

@app.route('/')
def index():
    """主頁面"""
    return send_from_directory('.', 'trail_generator.html')

@app.route('/trail_generator.html')
def trail_generator():
    """路線生成器頁面"""
    return send_from_directory('.', 'trail_generator.html')

@app.route('/trail.html')
def trail_viewer():
    """路線查看器頁面"""
    return send_from_directory('.', 'trail.html')

@app.route('/trail.json')
def trail_data():
    """路線數據"""
    return send_from_directory('.', 'trail.json')

@app.route('/generate_trail', methods=['POST'])
def generate_trail():
    """生成路線的 API 端點"""
    try:
        # 獲取請求數據
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '沒有收到請求數據'
            }), 400
        
        json_data = data.get('json_data')
        way_ids = data.get('way_ids', [])
        
        if not json_data:
            return jsonify({
                'success': False,
                'error': '缺少 JSON 數據'
            }), 400
        
        if not way_ids:
            return jsonify({
                'success': False,
                'error': '缺少 Way IDs'
            }), 400
        
        # 創建臨時 JSON 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
            temp_json_file = f.name
        
        try:
            # 構建命令
            cmd = [sys.executable, str(FIND_TRAIL_SCRIPT), temp_json_file] + [str(way_id) for way_id in way_ids]
            
            # 執行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=SCRIPT_DIR,
                timeout=300  # 5分鐘超時
            )
            
            # 檢查執行結果
            if result.returncode == 0:
                # 讀取生成的 trail.json
                trail_file = SCRIPT_DIR / "trail.json"
                if trail_file.exists():
                    with open(trail_file, 'r', encoding='utf-8') as f:
                        trail_data = json.load(f)
                    
                    # 計算統計信息
                    route_count = len([k for k in trail_data.keys() if k.startswith('trackPoints')])
                    total_points = sum(len(trail_data[k]) for k in trail_data.keys() if k.startswith('trackPoints'))
                    
                    return jsonify({
                        'success': True,
                        'output': result.stdout,
                        'output_file': 'trail.json',
                        'route_count': route_count,
                        'total_points': total_points,
                        'command': ' '.join(cmd)
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': '生成成功但找不到輸出文件',
                        'output': result.stdout,
                        'stderr': result.stderr
                    })
            else:
                return jsonify({
                    'success': False,
                    'error': f'執行失敗 (返回碼: {result.returncode})',
                    'output': result.stdout,
                    'stderr': result.stderr,
                    'command': ' '.join(cmd)
                })
                
        finally:
            # 清理臨時文件
            try:
                os.unlink(temp_json_file)
            except:
                pass
                
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': '執行超時 (超過5分鐘)'
        }), 408
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'服務器錯誤: {str(e)}'
        }), 500

@app.route('/health')
def health_check():
    """健康檢查端點"""
    return jsonify({
        'status': 'healthy',
        'script_exists': FIND_TRAIL_SCRIPT.exists(),
        'script_path': str(FIND_TRAIL_SCRIPT)
    })

@app.errorhandler(404)
def not_found(error):
    """404 錯誤處理"""
    return jsonify({
        'error': '頁面不存在',
        'message': '請檢查 URL 是否正確'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """500 錯誤處理"""
    return jsonify({
        'error': '內部服務器錯誤',
        'message': '請稍後再試'
    }), 500

if __name__ == '__main__':
    print("🚀 啟動中央山脈步道路線生成器 Web 服務器")
    print(f"📁 工作目錄: {SCRIPT_DIR}")
    print(f"🔧 腳本路徑: {FIND_TRAIL_SCRIPT}")
    print(f"✅ 腳本存在: {FIND_TRAIL_SCRIPT.exists()}")
    print("\n🌐 服務器將在以下地址啟動:")
    print("   - 主頁面: http://localhost:5001/")
    print("   - 路線生成器: http://localhost:5001/trail_generator.html")
    print("   - 路線查看器: http://localhost:5001/trail.html")
    print("\n按 Ctrl+C 停止服務器")
    
    app.run(host='0.0.0.0', port=5001, debug=True)
