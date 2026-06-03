#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基於 Waypoints 的智能路線生成器
結合 find_trail.py 的 Overpass API 方法和智能起始點判斷
"""

import json
import math
import argparse
import requests
import polyline
from typing import List, Dict, Tuple, Optional
from datetime import datetime

class SmartWaypointBasedTrailGenerator:
    def __init__(self):
        self.earth_radius = 6371  # 地球半徑（公里）
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """計算兩點間的距離（公里）"""
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = (math.sin(dlat/2) * math.sin(dlat/2) + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(dlon/2) * math.sin(dlon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return self.earth_radius * c
    
    def get_way_geometry_from_overpass(self, way_id: int) -> List[Dict[str, float]]:
        """使用 Overpass API 獲取 Way 的幾何數據"""
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
                if data.get('elements'):
                    way = data['elements'][0]
                    if 'geometry' in way:
                        points = []
                        for point in way['geometry']:
                            points.append({
                                'lat': point['lat'],
                                'lon': point['lon']
                            })
                        print(f"✅ Overpass 獲取到 {len(points)} 個點")
                        return points
        except Exception as e:
            print(f"⚠️ Overpass API 錯誤: {e}")
        
        return []
    
    def get_way_geometry_from_osrm(self, way_id: int) -> List[Dict[str, float]]:
        """使用 OSRM API 獲取 Way 的幾何數據（備用）"""
        try:
            osrm_url = f"https://router.project-osrm.org/route/v1/driving/{way_id}"
            response = requests.get(osrm_url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if 'routes' in data and data['routes']:
                    route = data['routes'][0]
                    if 'geometry' in route:
                        coords = polyline.decode(route['geometry'])
                        points = [{'lat': lat, 'lon': lon} for lat, lon in coords]
                        print(f"✅ OSRM 獲取到 {len(points)} 個點")
                        return points
        except Exception as e:
            print(f"⚠️ OSRM API 錯誤: {e}")
        
        return []
    
    def find_nearest_point_on_route(self, target_point: Dict, route_points: List[Dict]) -> Tuple[int, float]:
        """在路線中找到最近的點"""
        min_distance = float('inf')
        nearest_index = -1
        
        for i, point in enumerate(route_points):
            distance = self.calculate_distance(
                target_point['lat'], target_point['lon'],
                point['lat'], point['lon']
            )
            if distance < min_distance:
                min_distance = distance
                nearest_index = i
        
        return nearest_index, min_distance
    
    def determine_route_direction(self, start_waypoint: Dict, end_waypoint: Dict, 
                                route_points: List[Dict]) -> List[Dict]:
        """判斷路線方向：起始點是否在路線中間，決定行走方向"""
        if len(route_points) < 2:
            return route_points
        
        # 找到起始和終點 waypoint 在路線上的最近位置
        start_index, start_distance = self.find_nearest_point_on_route(start_waypoint, route_points)
        end_index, end_distance = self.find_nearest_point_on_route(end_waypoint, route_points)
        
        print(f"📍 起始點 '{start_waypoint['name']}' 在路線位置 {start_index} (距離: {start_distance:.3f}km)")
        print(f"📍 終點 '{end_waypoint['name']}' 在路線位置 {end_index} (距離: {end_distance:.3f}km)")
        
        # 判斷起始點是否在路線中間
        route_length = len(route_points)
        start_is_middle = 0.2 < start_index / route_length < 0.8
        end_is_middle = 0.2 < end_index / route_length < 0.8
        
        if start_is_middle:
            print(f"🎯 起始點在路線中間位置 ({start_index}/{route_length})")
            
            # 判斷行走方向：選擇能碰到更多 waypoints 的方向
            if start_index <= end_index:
                # 從起始點向終點方向
                direction = "forward"
                selected_points = route_points[start_index:end_index + 1]
                print(f"➡️ 選擇正向行走: {start_index} → {end_index}")
            else:
                # 從起始點向反方向
                direction = "backward"
                selected_points = route_points[end_index:start_index + 1]
                selected_points.reverse()  # 反轉順序
                print(f"⬅️ 選擇反向行走: {start_index} → {end_index}")
        else:
            # 起始點在端點附近，按正常順序
            if start_index <= end_index:
                selected_points = route_points[start_index:end_index + 1]
                print(f"➡️ 正常順序: {start_index} → {end_index}")
            else:
                selected_points = route_points[end_index:start_index + 1]
                selected_points.reverse()
                print(f"⬅️ 反轉順序: {start_index} → {end_index}")
        
        return selected_points
    
    def generate_intermediate_points(self, start: Dict, end: Dict, num_points: int = 10) -> List[Dict]:
        """在兩點之間生成中間點（當無法獲取真實路線時使用）"""
        if num_points < 2:
            return [start, end]
        
        points = []
        for i in range(num_points):
            ratio = i / (num_points - 1)
            lat = start['lat'] + (end['lat'] - start['lat']) * ratio
            lon = start['lon'] + (end['lon'] - start['lon']) * ratio
            points.append({'lat': lat, 'lon': lon})
        
        return points
    
    def smart_route_generation(self, waypoints: List[Dict], way_ids: List[int] = None) -> Dict:
        """智能路線生成，結合 Overpass API 和起始點判斷"""
        if len(waypoints) < 2:
            raise ValueError("需要至少2個 waypoints")
        
        print(f"🎯 開始智能路線生成，共 {len(waypoints)} 個 waypoints")
        if way_ids:
            print(f"🔗 使用 {len(way_ids)} 個 Way IDs: {way_ids}")
        
        # 生成 trackPoints
        trackpoints = {}
        route_count = 0
        total_points = 0
        total_distance = 0
        api_type = "Hybrid (Overpass + Smart Direction)"
        
        for i in range(len(waypoints) - 1):
            start_wp = waypoints[i]
            end_wp = waypoints[i + 1]
            
            print(f"\n🛤️ 處理路線 {i+1}: {start_wp['name']} → {end_wp['name']}")
            
            # 嘗試使用 Overpass API 獲取真實路線
            route_points = []
            if way_ids and i < len(way_ids):
                way_id = way_ids[i]
                print(f"🔍 嘗試獲取 Way {way_id} 的真實路線...")
                
                # 先嘗試 Overpass API
                route_points = self.get_way_geometry_from_overpass(way_id)
                
                # 如果 Overpass 失敗，嘗試 OSRM
                if not route_points:
                    print(f"⚠️ Overpass 失敗，嘗試 OSRM...")
                    route_points = self.get_way_geometry_from_osrm(way_id)
                
                if route_points:
                    # 使用智能方向判斷
                    route_points = self.determine_route_direction(start_wp, end_wp, route_points)
                    api_type = "Overpass + Smart Direction"
                else:
                    print(f"⚠️ 無法獲取 Way {way_id} 的真實路線，使用直線連接")
                    api_type = "Hybrid (Fallback to Linear)"
            
            # 如果沒有獲取到真實路線，使用直線連接
            if not route_points:
                segment_distance = self.calculate_distance(
                    start_wp['lat'], start_wp['lon'],
                    end_wp['lat'], end_wp['lon']
                )
                
                # 根據距離決定中間點的數量
                if segment_distance < 1.0:
                    route_points = [start_wp, end_wp]
                elif segment_distance < 5.0:
                    route_points = self.generate_intermediate_points(start_wp, end_wp, 5)
                else:
                    route_points = self.generate_intermediate_points(start_wp, end_wp, 10)
            
            route_count += 1
            total_points += len(route_points)
            
            # 計算這段路線的距離
            segment_distance = 0
            for j in range(len(route_points) - 1):
                segment_distance += self.calculate_distance(
                    route_points[j]['lat'], route_points[j]['lon'],
                    route_points[j+1]['lat'], route_points[j+1]['lon']
                )
            total_distance += segment_distance
            
            # 添加到 trackPoints
            track_key = f"trackPoints{route_count}"
            trackpoints[track_key] = route_points
            
            print(f"✅ 路線 {route_count}: {start_wp['name']} → {end_wp['name']} ({len(route_points)} 個點, {segment_distance:.2f}km)")
        
        print(f"\n📊 總統計: {route_count} 條路線，{total_points} 個點，總距離 {total_distance:.2f}km")
        
        # 構建輸出數據
        output_data = {
            "waypoints": waypoints,
            "way_ids": way_ids or [],
            **trackpoints,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_routes": route_count,
                "total_distance_km": round(total_distance, 2),
                "api_type": api_type,
                "description": "結合 Overpass API 和智能起始點判斷的路線生成",
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
                
                # 計算這段路線的距離
                segment_distance = 0
                for j in range(len(track_points) - 1):
                    segment_distance += self.calculate_distance(
                        track_points[j]['lat'], track_points[j]['lon'],
                        track_points[j+1]['lat'], track_points[j+1]['lon']
                    )
                
                output_data['metadata']['routes'].append({
                    'route_number': i+1,
                    'start_waypoint': start_wp['name'],
                    'end_waypoint': end_wp['name'],
                    'distance_km': round(segment_distance, 2),
                    'points_count': len(track_points),
                    'start_point': track_points[0] if track_points else None,
                    'end_point': track_points[-1] if track_points else None,
                    'way_id': way_ids[i] if way_ids and i < len(way_ids) else None
                })
        
        return output_data

def main():
    parser = argparse.ArgumentParser(description='智能路線生成器 - 結合 Overpass API 和起始點判斷')
    parser.add_argument('input_file', help='包含 waypoints 的 JSON 文件')
    parser.add_argument('-o', '--output', default='trail.json', help='輸出文件路徑')
    parser.add_argument('--way-ids', nargs='*', type=int, help='可選的 Way IDs 列表')
    
    args = parser.parse_args()
    
    # 讀取輸入文件
    with open(args.input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    waypoints = data.get('waypoints', [])
    if not waypoints:
        print("❌ 輸入文件中沒有找到 waypoints")
        return
    
    # 生成路線
    generator = SmartWaypointBasedTrailGenerator()
    output_data = generator.smart_route_generation(waypoints, args.way_ids)
    
    # 寫入輸出文件
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n🎉 生成完成！")
    print(f"📁 輸出文件: {args.output}")
    print(f"📊 統計: {output_data['metadata']['total_routes']} 條路線，總距離 {output_data['metadata']['total_distance_km']}km")
    print(f"🔧 API 類型: {output_data['metadata']['api_type']}")

if __name__ == "__main__":
    main()
