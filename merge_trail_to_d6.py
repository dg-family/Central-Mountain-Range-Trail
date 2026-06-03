#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
將 trail.json 的內容整合到 D6.json 中
保留 D6.json 的原有結構，但使用 trail.json 的 trackPoints 數據
"""

import json
import shutil
from pathlib import Path

def merge_trail_to_d6():
    """將 trail.json 的內容整合到 D6.json 中"""
    
    # 文件路徑
    trail_file = Path("trail.json")
    d6_file = Path("assets/data/D6.json")
    backup_file = Path("assets/data/D6_backup.json")
    
    print("🔄 開始整合 trail.json 到 D6.json")
    
    # 檢查文件是否存在
    if not trail_file.exists():
        print("❌ trail.json 不存在")
        return False
    
    if not d6_file.exists():
        print("❌ D6.json 不存在")
        return False
    
    try:
        # 備份原始 D6.json
        shutil.copy2(d6_file, backup_file)
        print(f"✅ 已備份原始 D6.json 到 {backup_file}")
        
        # 讀取 trail.json
        with open(trail_file, 'r', encoding='utf-8') as f:
            trail_data = json.load(f)
        
        # 讀取 D6.json
        with open(d6_file, 'r', encoding='utf-8') as f:
            d6_data = json.load(f)
        
        print(f"📊 trail.json 統計:")
        print(f"   - waypoints: {len(trail_data.get('waypoints', []))}")
        print(f"   - 路線數量: {trail_data.get('metadata', {}).get('total_routes', 0)}")
        
        # 統計 trackPoints
        trackpoints_count = 0
        for key in trail_data.keys():
            if key.startswith('trackPoints'):
                trackpoints_count += len(trail_data[key])
        
        print(f"   - 總點數: {trackpoints_count}")
        
        # 更新 D6.json 的內容
        updated_d6 = {
            # 保留 D6.json 的 waypoints（如果 trail.json 有更新的話使用 trail.json 的）
            "waypoints": trail_data.get('waypoints', d6_data.get('waypoints', [])),
            
            # 添加 trail.json 的所有 trackPoints
        }
        
        # 複製所有 trackPoints
        for key in trail_data.keys():
            if key.startswith('trackPoints'):
                updated_d6[key] = trail_data[key]
        
        # 添加 metadata（如果 D6.json 原本沒有的話）
        if 'metadata' in trail_data:
            updated_d6['metadata'] = trail_data['metadata']
        
        # 寫入更新後的 D6.json
        with open(d6_file, 'w', encoding='utf-8') as f:
            json.dump(updated_d6, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 已更新 D6.json")
        print(f"📊 更新後統計:")
        print(f"   - waypoints: {len(updated_d6.get('waypoints', []))}")
        
        # 統計更新後的 trackPoints
        updated_trackpoints_count = 0
        for key in updated_d6.keys():
            if key.startswith('trackPoints'):
                updated_trackpoints_count += len(updated_d6[key])
        
        print(f"   - 總點數: {updated_trackpoints_count}")
        
        # 顯示路線信息
        if 'metadata' in updated_d6 and 'routes' in updated_d6['metadata']:
            print(f"   - 路線信息:")
            for route in updated_d6['metadata']['routes']:
                print(f"     路線 {route['route_number']}: Way ID {route['way_id']} ({route['points_count']} 點)")
        
        return True
        
    except Exception as e:
        print(f"❌ 整合失敗: {e}")
        
        # 如果失敗，嘗試恢復備份
        if backup_file.exists():
            try:
                shutil.copy2(backup_file, d6_file)
                print("✅ 已恢復原始 D6.json")
            except Exception as restore_error:
                print(f"❌ 恢復備份失敗: {restore_error}")
        
        return False

def create_d6_with_trail():
    """創建一個新的 D6.json，完全基於 trail.json"""
    
    trail_file = Path("trail.json")
    new_d6_file = Path("assets/data/D6_new.json")
    
    print("🔄 創建新的 D6.json（基於 trail.json）")
    
    if not trail_file.exists():
        print("❌ trail.json 不存在")
        return False
    
    try:
        # 讀取 trail.json
        with open(trail_file, 'r', encoding='utf-8') as f:
            trail_data = json.load(f)
        
        # 創建新的 D6.json
        new_d6_data = {
            "waypoints": trail_data.get('waypoints', []),
        }
        
        # 複製所有 trackPoints
        for key in trail_data.keys():
            if key.startswith('trackPoints'):
                new_d6_data[key] = trail_data[key]
        
        # 添加 metadata
        if 'metadata' in trail_data:
            new_d6_data['metadata'] = trail_data['metadata']
        
        # 寫入新的 D6.json
        with open(new_d6_file, 'w', encoding='utf-8') as f:
            json.dump(new_d6_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 已創建新的 D6.json: {new_d6_file}")
        
        # 統計信息
        trackpoints_count = 0
        for key in new_d6_data.keys():
            if key.startswith('trackPoints'):
                trackpoints_count += len(new_d6_data[key])
        
        print(f"📊 新文件統計:")
        print(f"   - waypoints: {len(new_d6_data.get('waypoints', []))}")
        print(f"   - 總點數: {trackpoints_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ 創建失敗: {e}")
        return False

def main():
    """主函數"""
    print("🚀 中央山脈步道路線數據整合工具")
    print("=" * 50)
    
    while True:
        print("\n請選擇操作:")
        print("1. 將 trail.json 整合到現有的 D6.json")
        print("2. 創建新的 D6.json（完全基於 trail.json）")
        print("3. 查看當前文件狀態")
        print("4. 退出")
        
        choice = input("\n請輸入選項 (1-4): ").strip()
        
        if choice == '1':
            success = merge_trail_to_d6()
            if success:
                print("\n✅ 整合完成！")
            else:
                print("\n❌ 整合失敗！")
                
        elif choice == '2':
            success = create_d6_with_trail()
            if success:
                print("\n✅ 創建完成！")
            else:
                print("\n❌ 創建失敗！")
                
        elif choice == '3':
            print("\n📊 當前文件狀態:")
            
            files_to_check = [
                ("trail.json", "路線生成結果"),
                ("assets/data/D6.json", "現有 D6 數據"),
                ("assets/data/D6_backup.json", "D6 備份"),
                ("assets/data/D6_new.json", "新 D6 數據")
            ]
            
            for file_path, description in files_to_check:
                path = Path(file_path)
                if path.exists():
                    size = path.stat().st_size
                    print(f"   ✅ {description}: {file_path} ({size:,} bytes)")
                else:
                    print(f"   ❌ {description}: {file_path} (不存在)")
                    
        elif choice == '4':
            print("\n👋 再見！")
            break
            
        else:
            print("\n❌ 無效選項，請重新選擇")

if __name__ == "__main__":
    main()

