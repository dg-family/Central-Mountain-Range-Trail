#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中央山脈步道路線系統 - 統一服務器
整合靜態文件服務和路線生成 API
"""

from flask import Flask, request, jsonify, send_from_directory, render_template_string
import json
import tempfile
import os
import subprocess
import sys
from pathlib import Path
import argparse

app = Flask(__name__)

# 確保 find_trail.py 存在
SCRIPT_DIR = Path(__file__).parent
FIND_TRAIL_SCRIPT = SCRIPT_DIR / "find_trail.py"

# 預設端口
DEFAULT_PORT = 8000

@app.route('/')
def index():
    """主頁面 - 顯示所有可用的頁面"""
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>中央山脈步道路線系統</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                margin: 0;
                padding: 20px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .header h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
                font-weight: 300;
            }
            .header p {
                font-size: 1.1em;
                opacity: 0.9;
            }
            .content {
                padding: 40px;
            }
            .section {
                margin-bottom: 30px;
                padding: 25px;
                background: #f8f9fa;
                border-radius: 10px;
                border-left: 5px solid #3498db;
            }
            .section h2 {
                color: #2c3e50;
                margin-bottom: 20px;
                font-size: 1.5em;
                display: flex;
                align-items: center;
            }
            .section h2::before {
                content: "📍";
                margin-right: 10px;
                font-size: 1.2em;
            }
            .link-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }
            .link-card {
                background: white;
                border: 1px solid #e1e8ed;
                border-radius: 8px;
                padding: 20px;
                text-decoration: none;
                color: inherit;
                transition: all 0.3s ease;
            }
            .link-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(0,0,0,0.1);
                border-color: #3498db;
            }
            .link-card h3 {
                color: #2c3e50;
                margin-bottom: 10px;
                font-size: 1.2em;
            }
            .link-card p {
                color: #7f8c8d;
                font-size: 0.9em;
                margin: 0;
            }
            .status {
                background: #d4edda;
                color: #155724;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                border: 1px solid #c3e6cb;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>中央山脈步道路線系統</h1>
                <p>整合的步道路線管理和查看系統</p>
            </div>
            
            <div class="content">
                <div class="status">
                    ✅ 服務器運行正常 | 端口: {{ port }} | 工作目錄: {{ work_dir }}
                </div>
                
                <div class="section">
                    <h2>路線生成與管理</h2>
                    <div class="link-grid">
                        <a href="/trail_generator.html" class="link-card">
                            <h3>🚀 路線生成器</h3>
                            <p>使用 Web 界面生成和管理步道路線，支援 waypoints 和 routes 排序</p>
                        </a>
                        <a href="/trail.html" class="link-card">
                            <h3>🗺️ 路線查看器</h3>
                            <p>在地圖上查看生成的步道路線和 waypoints</p>
                        </a>
                        <a href="/test_generator.html" class="link-card">
                            <h3>🧪 功能測試</h3>
                            <p>測試系統功能和 API 連接</p>
                        </a>
                    </div>
                </div>
                
                <div class="section">
                    <h2>地圖與導航</h2>
                    <div class="link-grid">
                        <a href="/map-test.html" class="link-card">
                            <h3>🗺️ 地圖測試</h3>
                            <p>測試地圖功能和基本導航</p>
                        </a>
                        <a href="/index.html" class="link-card">
                            <h3>📋 行程表</h3>
                            <p>查看完整的行程安排和路線規劃</p>
                        </a>
                        <a href="/supplies.html" class="link-card">
                            <h3>📦 補給點</h3>
                            <p>查看補給點位置和相關信息</p>
                        </a>
                    </div>
                </div>
                
                <div class="section">
                    <h2>系統信息</h2>
                    <div class="link-grid">
                        <a href="/health" class="link-card">
                            <h3>💚 健康檢查</h3>
                            <p>檢查系統狀態和 API 可用性</p>
                        </a>
                        <a href="/trail.json" class="link-card">
                            <h3>📄 路線數據</h3>
                            <p>查看當前生成的路線 JSON 數據</p>
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    ''', port=request.environ.get('SERVER_PORT', DEFAULT_PORT), work_dir=SCRIPT_DIR)

@app.route('/trail_generator.html')
def trail_generator():
    """路線生成器頁面"""
    return send_from_directory('.', 'trail_generator.html')

@app.route('/trail.html')
def trail_viewer():
    """路線查看器頁面"""
    return send_from_directory('.', 'trail.html')

@app.route('/test_generator.html')
def test_generator():
    """測試頁面"""
    return send_from_directory('.', 'test_generator.html')

@app.route('/map-test.html')
def map_test():
    """地圖測試頁面"""
    return send_from_directory('.', 'map-test.html')

@app.route('/index.html')
def index_html():
    """行程表頁面"""
    return send_from_directory('.', 'index.html')

@app.route('/supplies.html')
def supplies():
    """補給點頁面"""
    return send_from_directory('.', 'supplies.html')

@app.route('/trail.json')
def trail_data():
    """路線數據"""
    return send_from_directory('.', 'trail.json')

@app.route('/generate_trail', methods=['POST'])
def generate_trail():
    """生成路線的 API 端點 - 基於 waypoints 生成 trackPoints"""
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
        
        # 檢查是否有 waypoints
        waypoints = json_data.get('waypoints', [])
        if not waypoints or len(waypoints) < 2:
            return jsonify({
                'success': False,
                'error': '需要至少2個 waypoints 來生成路線'
            }), 400
        
        print(f"🎯 基於 {len(waypoints)} 個 waypoints 生成 trackPoints")
        
        # 使用智能路線生成器
        try:
            # 創建臨時 JSON 文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
                temp_json_file = f.name
            
            # 構建命令
            cmd = [sys.executable, str(SCRIPT_DIR / "waypoint_based_trail_generator.py"), temp_json_file, "-o", "trail.json"]
            if way_ids:
                cmd.extend(["--way-ids"] + [str(way_id) for way_id in way_ids])
            
            # 執行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=SCRIPT_DIR,
                timeout=60  # 1分鐘超時
            )
            
            if result.returncode == 0:
                # 讀取生成的 trail.json
                trail_file = SCRIPT_DIR / "trail.json"
                if trail_file.exists():
                    with open(trail_file, 'r', encoding='utf-8') as f:
                        output_data = json.load(f)
                    
                    route_count = output_data['metadata']['total_routes']
                    total_points = sum(len(output_data[k]) for k in output_data.keys() if k.startswith('trackPoints'))
                    
                    print(f"✅ 智能路線生成成功: {route_count} 條路線，{total_points} 個點")
                else:
                    raise Exception("未找到生成的 trail.json 文件")
            else:
                raise Exception(f"智能路線生成失敗: {result.stderr}")
                
        except Exception as e:
            print(f"⚠️ 智能路線生成失敗，使用簡單直線連接: {e}")
            
            # 回退到簡單的直線連接
            trackpoints = {}
            route_count = 0
            total_points = 0
            
            for i in range(len(waypoints) - 1):
                start_wp = waypoints[i]
                end_wp = waypoints[i + 1]
                
                # 創建簡單的直線連接（兩個點）
                route_points = [
                    {"lat": start_wp["lat"], "lon": start_wp["lon"]},
                    {"lat": end_wp["lat"], "lon": end_wp["lon"]}
                ]
                
                route_count += 1
                total_points += len(route_points)
                
                # 添加到 trackPoints
                track_key = f"trackPoints{route_count}"
                trackpoints[track_key] = route_points
                
                print(f"✅ 路線 {route_count}: {start_wp['name']} → {end_wp['name']} ({len(route_points)} 個點)")
            
            # 構建輸出數據
            output_data = {
                "waypoints": waypoints,
                "way_ids": way_ids,  # 保留原始 way_ids 作為參考
                **trackpoints,  # 展開所有 trackPoints
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "total_routes": route_count,
                    "api_type": "Waypoint-based Linear Connection (Fallback)",
                    "description": "基於 waypoints 生成的直線連接路線（回退模式）",
                    "routes": []
                }
            }
            
            # 添加路線詳細信息到 metadata
            for i in range(len(waypoints) - 1):
                start_wp = waypoints[i]
                end_wp = waypoints[i + 1]
                track_key = f"trackPoints{i+1}"
                
                if track_key in trackpoints:
                    track_points = trackpoints[track_key]
                    output_data['metadata']['routes'].append({
                        'route_number': i+1,
                        'start_waypoint': start_wp['name'],
                        'end_waypoint': end_wp['name'],
                        'points_count': len(track_points),
                        'start_point': track_points[0] if track_points else None,
                        'end_point': track_points[-1] if track_points else None
                    })
        
        finally:
            # 清理臨時文件
            try:
                if 'temp_json_file' in locals():
                    os.unlink(temp_json_file)
            except:
                pass
        
        # 寫入 trail.json 文件
        output_file = "trail.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"🎉 生成完成！輸出文件: {output_file}")
        print(f"📊 統計: {route_count} 條路線，{total_points} 個點")
        
        return jsonify({
            'success': True,
            'output': f"基於 {len(waypoints)} 個 waypoints 生成了 {route_count} 條路線，共 {total_points} 個點",
            'output_file': 'trail.json',
            'route_count': route_count,
            'total_points': total_points,
            'waypoints_count': len(waypoints)
        })
                
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
        'script_path': str(FIND_TRAIL_SCRIPT),
        'server_type': 'unified_server',
        'features': [
            'static_file_serving',
            'trail_generation_api',
            'cors_support',
            'health_check'
        ]
    })

@app.errorhandler(404)
def not_found(error):
    """404 錯誤處理"""
    return jsonify({
        'error': '頁面不存在',
        'message': '請檢查 URL 是否正確',
        'available_pages': [
            '/',
            '/trail_generator.html',
            '/trail.html',
            '/test_generator.html',
            '/map-test.html',
            '/index.html',
            '/supplies.html'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """500 錯誤處理"""
    return jsonify({
        'error': '內部服務器錯誤',
        'message': '請稍後再試'
    }), 500

def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='中央山脈步道路線系統 - 統一服務器')
    parser.add_argument('--port', '-p', type=int, default=DEFAULT_PORT, 
                       help=f'服務器端口 (預設: {DEFAULT_PORT})')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='服務器主機 (預設: 0.0.0.0)')
    parser.add_argument('--debug', action='store_true',
                       help='啟用調試模式')
    
    args = parser.parse_args()
    
    print("🚀 啟動中央山脈步道路線系統 - 統一服務器")
    print(f"📁 工作目錄: {SCRIPT_DIR}")
    print(f"🔧 腳本路徑: {FIND_TRAIL_SCRIPT}")
    print(f"✅ 腳本存在: {FIND_TRAIL_SCRIPT.exists()}")
    print(f"\n🌐 服務器將在以下地址啟動:")
    print(f"   - 主頁面: http://localhost:{args.port}/")
    print(f"   - 路線生成器: http://localhost:{args.port}/trail_generator.html")
    print(f"   - 路線查看器: http://localhost:{args.port}/trail.html")
    print(f"   - 地圖測試: http://localhost:{args.port}/map-test.html")
    print(f"   - 行程表: http://localhost:{args.port}/index.html")
    print(f"   - 補給點: http://localhost:{args.port}/supplies.html")
    print(f"\n🔧 功能特色:")
    print(f"   - 靜態文件服務 (CORS 支援)")
    print(f"   - 路線生成 API")
    print(f"   - 健康檢查端點")
    print(f"   - 統一管理界面")
    print(f"\n按 Ctrl+C 停止服務器")
    
    try:
        app.run(host=args.host, port=args.port, debug=args.debug)
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"\n❌ 端口 {args.port} 已被占用")
            print(f"請嘗試其他端口: python unified_server.py --port {args.port + 1}")
        else:
            print(f"\n❌ 啟動服務器失敗: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 服務器已停止")

if __name__ == '__main__':
    main()
