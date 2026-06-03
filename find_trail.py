#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中央山脈步道路線生成器
使用Overpass API和OSRM API獲取OpenStreetMap路線數據
支援多段路線的智能分段和連接
"""

import json
import requests
import argparse
import time
from typing import List, Dict, Optional
import polyline

class MultiRouteProcessorHybrid:
    def __init__(self):
        # 預定義的路線分段規則 - 按照實際行走順序
        self.route_rules = {
            # Way ID: (start_waypoint_name, end_waypoint_name)
            531491993: ("大禹嶺", "屏風山登山口(111.2K)"),
            918227944: ("屏風山登山口(111.2K)", "鐵線吊橋"),
            968626070: ("鐵線吊橋", "屏風山屋"),
            968626068: ("屏風山屋", "屏風山"),
            1049745494: ("屏風山", "鐵線吊橋"),  # 修正：從屏風山到鐵線吊橋
            220625142: (None, "屏風山屋"),  # 從起點到屏風山屋
            220625149: ("前20個點", "前20個點"),  # 第七段：前20個點
            411431051: ("屏風山屋", "屏風山"),  # 備用路線
            220625143: ("屏風山舊路與新路分岔點", None),  # 路線10：從屏風山舊路與新路分岔點到終點
            410181708: ("路線10終點", "屏風南峰營地"),  # 路線11：從路線10終點到屏風南峰營地
        }
        
        # 特殊處理：第九段使用不同的邏輯
        self.route_9_rule = ("後60個點", "後60個點")  # 第九段：後60個點
    
    def get_way_geometry_raw(self, way_id: int) -> List[Dict[str, float]]:
        """獲取Way的原始幾何數據，不進行分段"""
        # 嘗試使用 Overpass API
        overpass_url = "https://overpass-api.de/api/interpreter"
        query = f"""
        [out:json];
        way({way_id});
        out geom;
        """
        
        try:
            response = requests.get(overpass_url, params={'data': query}, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data['elements']:
                    way = data['elements'][0]
                    if 'geometry' in way:
                        # 轉換為標準格式
                        points = []
                        for point in way['geometry']:
                            points.append({
                                'lat': point['lat'],
                                'lon': point['lon']
                            })
                        print(f"✅ Overpass獲取到 {len(points)} 個點")
                        return points
        except Exception as e:
            print(f"⚠️ Overpass API 錯誤: {e}")
        
        # 如果 Overpass 失敗，嘗試 OSRM
        try:
            osrm_url = f"https://router.project-osrm.org/route/v1/driving/{way_id}"
            response = requests.get(osrm_url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if 'routes' in data and data['routes']:
                    route = data['routes'][0]
                    if 'geometry' in route:
                        # 解碼 polyline
                        coords = polyline.decode(route['geometry'])
                        points = [{'lat': lat, 'lon': lon} for lat, lon in coords]
                        print(f"✅ OSRM獲取到 {len(points)} 個點")
                        return points
        except Exception as e:
            print(f"⚠️ OSRM API 錯誤: {e}")
        
        return []

    def get_way_geometry(self, way_id: int, waypoints: List[Dict] = None) -> List[Dict[str, float]]:
        """獲取指定 Way 的完整幾何座標，優先使用Overpass API"""
        # 嘗試使用 Overpass API
        overpass_url = "https://overpass-api.de/api/interpreter"
        query = f"""
        [out:json];
        way({way_id});
        out geom;
        """
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(overpass_url, params={'data': query}, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    if data['elements']:
                        way = data['elements'][0]
                        if 'geometry' in way:
                            # 轉換為標準格式
                            way_points = []
                            for point in way['geometry']:
                                way_points.append({
                                    'lat': point['lat'],
                                    'lon': point['lon']
                                })
                            print(f"✅ Overpass獲取到 {len(way_points)} 個點")
                            break
                        else:
                            print(f"❌ Way {way_id} 沒有幾何數據")
                            return []
                    else:
                        print(f"❌ 找不到 Way {way_id}")
                        return []
                else:
                    print(f"⚠️ Overpass API 錯誤 (嘗試 {attempt + 1}/{max_retries}): {response.status_code} {response.reason}")
                    if attempt < max_retries - 1:
                        wait_time = 5 * (attempt + 1)
                        print(f"⏳ 等待 {wait_time} 秒後重試...")
                        time.sleep(wait_time)
                    else:
                        print("❌ Overpass API失敗，嘗試OSRM API")
                        return self.get_way_geometry_osrm(way_id)
            except Exception as e:
                print(f"⚠️ Overpass API 錯誤 (嘗試 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 5 * (attempt + 1)
                    print(f"⏳ 等待 {wait_time} 秒後重試...")
                    time.sleep(wait_time)
                else:
                    print("❌ Overpass API失敗，嘗試OSRM API")
                    return self.get_way_geometry_osrm(way_id)
        else:
            return []
        
        # 如果沒有提供 waypoints 或沒有規則，返回完整路徑
        if not waypoints or way_id not in self.route_rules:
            print(f"📍 沒有規則，返回完整路徑，總共 {len(way_points)} 個點")
            return way_points
        
        # 獲取預定義的規則
        start_waypoint_name, end_waypoint_name = self.route_rules[way_id]
        
        # 特殊處理：手動分段
        if start_waypoint_name == "前20個點" and end_waypoint_name == "前20個點":
            # 第七段：從起點到屏風山屋
            start_index = 0
            end_index = len(way_points) - 1
            
            # 尋找屏風山屋作為終點
            for i, point in enumerate(way_points):
                for wp in waypoints:
                    if (wp.get('name') == "屏風山屋" and
                        abs(point['lat'] - wp['lat']) < 0.000001 and 
                        abs(point['lon'] - wp['lon']) < 0.000001):
                        end_index = i
                        print(f"📍 第七段找到終點 屏風山屋: {point['lat']}, {point['lon']}")
                        break
                if end_index < len(way_points) - 1:
                    break
            
            result_points = way_points[start_index:end_index + 1]
            print(f"📍 第七段：從起點到屏風山屋，總共 {len(result_points)} 個點")
            return result_points
        elif start_waypoint_name == "路線10終點":
            # 路線11：從路線10終點開始
            start_index = 0
            end_index = len(way_points) - 1
            
            # 尋找路線10終點作為起點 (24.142605, 121.339029)
            for i, point in enumerate(way_points):
                if (abs(point['lat'] - 24.142605) < 0.000001 and 
                    abs(point['lon'] - 121.339029) < 0.000001):
                    start_index = i
                    print(f"📍 路線11找到起點 路線10終點: {point['lat']}, {point['lon']}")
                    break
            
            # 尋找屏風南峰營地作為終點
            if end_waypoint_name == "屏風南峰營地":
                for i, point in enumerate(way_points):
                    for wp in waypoints:
                        if (wp.get('name') == "屏風南峰營地" and
                            abs(point['lat'] - wp['lat']) < 0.000001 and 
                            abs(point['lon'] - wp['lon']) < 0.000001):
                            end_index = i
                            print(f"📍 路線11找到終點 屏風南峰營地: {point['lat']}, {point['lon']}")
                            break
                    if end_index < len(way_points) - 1:
                        break
            
            # 處理反向分段（起點索引大於終點索引）
            if start_index <= end_index:
                result_points = way_points[start_index:end_index + 1]
            else:
                # 如果起點索引大於終點索引，需要反向提取
                result_points = way_points[end_index:start_index + 1]
                result_points.reverse()  # 反轉順序以保持正確方向
            
            print(f"📍 路線11：從路線10終點到屏風南峰營地，總共 {len(result_points)} 個點")
            return result_points
        elif start_waypoint_name == "後60個點" and end_waypoint_name == "後60個點":
            # 第九段：後60個點
            result_points = way_points[20:80]
            print(f"📍 第九段：後60個點，總共 {len(result_points)} 個點")
            return result_points
        
        # 找到起點和終點的索引
        start_index = 0
        end_index = len(way_points) - 1
        
        if start_waypoint_name:
            for i, point in enumerate(way_points):
                for wp in waypoints:
                    if (wp.get('name') == start_waypoint_name and
                        abs(point['lat'] - wp['lat']) < 0.000001 and 
                        abs(point['lon'] - wp['lon']) < 0.000001):
                        start_index = i
                        print(f"📍 找到起點 {start_waypoint_name}: {point['lat']}, {point['lon']}")
                        break
                if start_index > 0:
                    break
        
        if end_waypoint_name:
            for i, point in enumerate(way_points):
                for wp in waypoints:
                    if (wp.get('name') == end_waypoint_name and
                        abs(point['lat'] - wp['lat']) < 0.000001 and 
                        abs(point['lon'] - wp['lon']) < 0.000001):
                        end_index = i
                        print(f"📍 找到終點 {end_waypoint_name}: {point['lat']}, {point['lon']}")
                        break
                if end_index < len(way_points) - 1:
                    break
        
        # 提取指定範圍的點（處理反向情況）
        if start_index <= end_index:
            result_points = way_points[start_index:end_index + 1]
        else:
            # 如果起點索引大於終點索引，需要反向提取
            result_points = way_points[end_index:start_index + 1]
            result_points.reverse()  # 反轉順序以保持正確方向
        
        print(f"📍 根據規則分段: {start_index} 到 {end_index}，總共 {len(result_points)} 個點")
        return result_points
    
    def get_way_geometry_osrm(self, way_id: int) -> List[Dict[str, float]]:
        """使用OSRM API獲取Way幾何數據（備用方案）"""
        try:
            # 注意：OSRM API需要起點和終點座標，這裡使用一個簡化的方法
            # 實際使用中可能需要更複雜的邏輯
            osrm_url = f"https://router.project-osrm.org/route/v1/driving/{way_id}"
            response = requests.get(osrm_url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if 'routes' in data and data['routes']:
                    route = data['routes'][0]
                    if 'geometry' in route:
                        # 解碼 polyline
                        coords = polyline.decode(route['geometry'])
                        points = [{'lat': lat, 'lon': lon} for lat, lon in coords]
                        print(f"✅ OSRM備用方案獲取到 {len(points)} 個點")
                        return points
        except Exception as e:
            print(f"❌ OSRM API 錯誤: {e}")
        
        return []
    
    def process_routes(self, start_file: str, way_ids: List[int], output_file: str = None) -> str:
        """處理多條路線並生成JSON輸出"""
        print(f"📁 讀取起始文件: {start_file}")
        
        # 讀取起始文件
        try:
            with open(start_file, 'r', encoding='utf-8') as f:
                start_data = json.load(f)
        except Exception as e:
            print(f"❌ 無法讀取起始文件: {e}")
            return None
        
        # 獲取waypoints
        start_waypoints = start_data.get('waypoints', [])
        if start_waypoints:
            print(f"📍 起始點: {start_waypoints[0]['name']} - {start_waypoints[0]['lat']}, {start_waypoints[0]['lon']}")
        
        # 初始化輸出數據
        output_data = {
            'waypoints': start_waypoints,
            'metadata': {
                'total_routes': len(way_ids),
                'api_type': 'Hybrid (Overpass + OSRM fallback)',
                'routes': []
            }
        }
        
        # 處理每條路線
        total_points = 0
        route_count = 0
        
        for i, way_id in enumerate(way_ids, 1):
            print(f"\n🛤️ 處理路線 {i}: Way {way_id}")
            
            # 獲取 Way 幾何
            way_points = self.get_way_geometry(way_id, start_waypoints)
            if not way_points:
                print(f"❌ 無法獲取 Way {way_id} 的數據")
                continue
            
            print(f"✅ 獲取到 {len(way_points)} 個點")
            total_points += len(way_points)
            route_count += 1
            
            # 特殊處理：第九段使用不同的分段邏輯
            if i == 9 and way_id == 220625149:
                # 第九段：從屏風山到屏風山舊路與新路分岔點
                # 重新獲取完整的Way幾何，然後分段
                full_way_points = self.get_way_geometry_raw(way_id)
                
                # 找到屏風山和屏風山舊路與新路分岔點的索引
                start_index = 0
                end_index = len(full_way_points) - 1
                
                # 尋找屏風山作為起點
                for j, point in enumerate(full_way_points):
                    for wp in start_waypoints:
                        if (wp.get('name') == "屏風山" and
                            abs(point['lat'] - wp['lat']) < 0.000001 and 
                            abs(point['lon'] - wp['lon']) < 0.000001):
                            start_index = j
                            print(f"📍 第九段找到起點 屏風山: {point['lat']}, {point['lon']}")
                            break
                    if start_index > 0:
                        break
                
                # 尋找屏風山舊路與新路分岔點作為終點
                for j, point in enumerate(full_way_points):
                    for wp in start_waypoints:
                        if (wp.get('name') == "屏風山舊路與新路分岔點" and
                            abs(point['lat'] - wp['lat']) < 0.000001 and 
                            abs(point['lon'] - wp['lon']) < 0.000001):
                            end_index = j
                            print(f"📍 第九段找到終點 屏風山舊路與新路分岔點: {point['lat']}, {point['lon']}")
                            break
                    if end_index < len(full_way_points) - 1:
                        break
                
                # 處理反向分段（起點索引大於終點索引）
                if start_index <= end_index:
                    way_points = full_way_points[start_index:end_index + 1]
                else:
                    # 如果起點索引大於終點索引，需要反向提取
                    way_points = full_way_points[end_index:start_index + 1]
                    way_points.reverse()  # 反轉順序以保持正確方向
                
                print(f"📍 第九段：從屏風山到屏風山舊路與新路分岔點，總共 {len(way_points)} 個點")
                total_points = total_points - 21 + len(way_points)  # 調整總點數
            
            # 添加到 trackPoints
            track_key = f"trackPoints{route_count}"
            output_data[track_key] = way_points
            
            # 添加到metadata
            output_data['metadata']['routes'].append({
                'route_number': route_count,
                'way_id': way_id,
                'points_count': len(way_points),
                'start_point': way_points[0] if way_points else None,
                'end_point': way_points[-1] if way_points else None
            })
        
        # 寫入輸出文件
        if not output_file:
            output_file = "trail.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 多路線處理完成!")
        print(f"📁 輸出文件: {output_file}")
        print(f"📊 統計信息:")
        print(f"  - 路線數量: {route_count}")
        print(f"  - Waypoints: {len(start_waypoints)} (來自 {start_file})")
        print(f"  - 總點數: {total_points}")
        print(f"  - 使用API: {output_data['metadata']['api_type']}")
        
        return output_file

def main():
    parser = argparse.ArgumentParser(description='中央山脈步道路線生成器')
    parser.add_argument('start_file', help='起始JSON文件路徑')
    parser.add_argument('way_ids', nargs='+', type=int, help='要處理的Way ID列表')
    parser.add_argument('-o', '--output', help='輸出文件路徑')
    
    args = parser.parse_args()
    
    processor = MultiRouteProcessorHybrid()
    output_file = processor.process_routes(args.start_file, args.way_ids, args.output)
    
    if output_file:
        print(f"\n🎉 處理完成！輸出文件: {output_file}")
    else:
        print("\n❌ 處理失敗")

if __name__ == "__main__":
    main()
