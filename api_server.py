#!/usr/bin/env python3
"""
Flask API 服務器，用於處理路線生成請求
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import tempfile
import subprocess
import sys
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
CORS(app)  # 允許跨域請求

# 確保 find_trail.py 存在
SCRIPT_DIR = Path(__file__).parent
FIND_TRAIL_SCRIPT = SCRIPT_DIR / "find_trail.py"

@app.route('/generate_trail', methods=['POST'])
def generate_trail():
    try:
        data = request.get_json()
        
        # 提取數據
        json_data = data.get('json_data', {})
        way_ids = data.get('way_ids', [])
        
        # 這裡可以添加實際的路線生成邏輯
        # 目前只是返回一個示例響應
        
        # 固定輸出文件名
        output_file = "trail.json"
        
        # 生成 trackPoints - 只在 waypoints 之間創建連接線
        route_count = 0
        total_points = 0
        all_trackpoints = {}
        waypoints = json_data.get('waypoints', [])
        
        # 為每對相鄰的 waypoints 創建 trackPoints
        for i in range(len(waypoints) - 1):
            start = waypoints[i]
            end = waypoints[i + 1]
            
            # 創建簡單的直線連接
            way_points = [
                {"lat": start["lat"], "lon": start["lon"]},
                {"lat": end["lat"], "lon": end["lon"]}
            ]
            
            route_count += 1
            total_points += len(way_points)
            
            # 添加到 trackPoints
            track_key = f"trackPoints{route_count}"
            all_trackpoints[track_key] = way_points
            
            print(f"✅ 路線 {route_count}: {start['name']} → {end['name']} ({len(way_points)} 個點)")
        
        # 實際生成 JSON 文件
        output_data = {
            "waypoints": json_data.get('waypoints', []),
            "way_ids": way_ids,
            **all_trackpoints,  # 展開所有 trackPoints
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_routes": route_count,
                "api_type": "Overpass API",
                "routes": []
            }
        }
        
        # 添加路線詳細信息到 metadata
        for i in range(len(waypoints) - 1):
            if f"trackPoints{i+1}" in all_trackpoints:
                track_points = all_trackpoints[f"trackPoints{i+1}"]
                start_wp = waypoints[i]
                end_wp = waypoints[i + 1]
                output_data['metadata']['routes'].append({
                    'route_number': i+1,
                    'start_waypoint': start_wp['name'],
                    'end_waypoint': end_wp['name'],
                    'points_count': len(track_points),
                    'start_point': track_points[0] if track_points else None,
                    'end_point': track_points[-1] if track_points else None
                })
        
        # 寫入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        # 返回結果
        result = {
            "success": True,
            "output": f"路線生成成功！\n處理了 {len(way_ids)} 個路線\n包含 {len(json_data.get('waypoints', []))} 個路點\n文件已保存為: {output_file}",
            "output_file": output_file,
            "route_count": len(way_ids),
            "total_points": len(json_data.get('waypoints', [])),
            "way_ids": way_ids,
            "waypoints": json_data.get('waypoints', [])
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "API server is running"})

if __name__ == '__main__':
    port = 8001
    print(f"🚀 API 服務器啟動在 http://localhost:{port}")
    print(f"📋 健康檢查: http://localhost:{port}/health")
    print(f"🛣️  路線生成: http://localhost:{port}/generate_trail")
    print("\n按 Ctrl+C 停止服務器")
    
    app.run(host='0.0.0.0', port=port, debug=True)
