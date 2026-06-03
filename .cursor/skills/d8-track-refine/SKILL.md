---
name: d8-track-refine
description: Rebuild and refine D8 hiking tracks using a continuous corridor split workflow with strict continuity checks. Use when fixing D8 trackPoints, D8 waypoint drift, or D8 segment gaps/jumps.
disable-model-invocation: true
---

# D8 Track Refine

## Goal

把 `D8` 重建成「可連續顯示、段間無斷裂、開圖不跳線」的版本，並同步更新 waypoint/cache。

## When to use

- 使用者說要修 `D8`、`D8 trackPoints`、`D8 斷點`、`D8 跳線`
- `D8.json` 出現以下任一狀況：
  - 段間 gap 明顯 (`trackPointsN[-1]` 到 `trackPointsN+1[0]` 非 0)
  - 多段 `fallback-linear` 或長距離直線錯路
  - waypoint 座標漂移到錯誤山域

## Workflow

1. 讀取 `assets/data/D8.json`，確認：
   - `segments`（規劃段距/時間）
   - `metadata.segments`（現況 method/track_km）
   - `trackPoints1..N`（現況斷點與跳點）
2. 先決定是否要套用最新行程版本（目前建議 6 段，移除 `能高小屋舊址`）：
   - `光被八表紀念碑 -> 卡賀爾山 -> 能高山 -> 台灣池營地 -> 大陸池營地 -> 能高南峰南嶺 -> 南峰岔路口`
   - 若行程要改，先改 `segments` 再重建 track。
3. 鎖定固定座標（不要被 split 邊界點覆蓋）：
   - `卡賀爾山`: `24.0068789, 121.2703053` (`osm-peak/6098335070`)
   - `能高山`(= 能高山主峰): `23.9923208, 121.2602380` (`osm-peak/2268473312`)
   - `台灣池營地`: `23.9841799, 121.2619749` (`osm-water/590974738`)
   - `大陸池營地`: `23.9781801, 121.2641956` (`osm-node/7763559385`)
   - `南峰岔路口`: `23.9657146, 121.2776812` (`osm-jct/862885347+1189837906`)
4. 建立單一連續主路廊（corridor polyline），起訖點錨定在 D8 路線合理範圍。
5. 依 `segments` 的規劃里程比例，將主路廊切成各段 `trackPointsN`。
6. 對每段做 densify（建議最大步長 `<= 0.04km`），避免地圖鋸齒跳線。
7. 重建 `waypoints`，但固定點名稱優先使用固定座標（不是邊界切分點）。
8. 更新 `metadata`：
   - `track_source`
   - `total_distance_km` / `total_time_min`
   - `metadata.segments[*].trackPoints/method/track_km`
9. 同步 `assets/data/geocode_cache.json`（含固定點 `source`）。
10. 若有用到 `南峰岔路口` 的隔日（D9），一併同步同名 waypoint 座標，避免跨日銜接漂移。

## Validation Checklist

- [ ] D8 每個非 loop 段都有對應 `trackPointsN`
- [ ] 所有段間邊界 gap = 0m（或趨近 0）
- [ ] 每段最大單步距離 `<= 40m`
- [ ] `waypoints` 順序與 `segments` 路徑方向一致
- [ ] D8 不再包含 `能高小屋舊址`（若採 6 段版本）
- [ ] `卡賀爾山 / 能高山 / 台灣池營地 / 大陸池營地 / 南峰岔路口` 與固定座標一致
- [ ] `D9` 的 `南峰岔路口` 與 D8 同座標
- [ ] 無跨區域暴衝（例如突然跳到遠離能高主稜的位置）

## D9 Companion Rules

當 D8/D9 一起修時，套用以下命名與點位：

- `南峰南鞍營地` -> `能高南峰南鞍營地`
- `3039鞍營地` -> `3159峰南鞍營地`
- `屯鹿池 → 屯鹿妹池` -> `屯鹿妹池`（移除 `屯鹿池`）

建議固定點：

- `能高南峰南鞍營地`: `23.9595919, 121.2752354`
- `3159峰南鞍營地`: `23.9474750, 121.2718900`
- `屯鹿妹池`: `23.8876028, 121.2643520`

## D10 Companion Rules

當使用者要求修 D10 時，優先套用以下規則：

- 移除 `北安東軍山東稜登山口`
- `摩即草山三岔路口` 用精準岔點：`23.8735163, 121.2646684`
- `摩即草山三岔路口 <-> 安東軍山` 只畫一組來回（去/回各一段，回程為去程反轉）
- 若使用者要求「`MIT鞍部鋪箭竹營地` 改成 `摩即三岔路口`」：
  - D10 終點改為 `摩即三岔路口`（`23.8371133, 121.2386565`）
  - 末段 `摩即地段前的平坦營地 -> 摩即三岔路口` 需重算公里與時間（目前採 `3.7km / 370min`）

建議 D10 7+1 段順序（共 8 段）：

1. `屯鹿妹池 -> 安東軍山三岔路口營地`
2. `安東軍山三岔路口營地 -> 摩即草山三岔路口`
3. `摩即草山三岔路口 -> 安東軍山`
4. `安東軍山 -> 摩即草山三岔路口`
5. `摩即草山三岔路口 -> 青草營地`
6. `青草營地 -> 樹林營地`
7. `樹林營地 -> 摩即地段前的平坦營地`
8. `摩即地段前的平坦營地 -> MIT鞍部箭竹營地`

## D11 Companion Rules

當使用者要求修 D11，且明確指定起點為 `MIT鞍部箭竹營地` 時：

- 起點改為 `MIT鞍部箭竹營地`
- 移除 `摩即山西峰`
- 移除 `摩即池/摩即池畔營地`
- `摩即山` 固定用點位：`23.8463480, 121.2449950`

建議段序（7 段）：

1. `MIT鞍部箭竹營地 -> 摩即三岔路口`
2. `摩即三岔路口 -> 摩即山`
3. `摩即山 -> 摩即三岔路口`
4. `摩即三岔路口 -> 摩即南鞍營地`
5. `摩即南鞍營地 -> 2640峰`
6. `2640峰 -> 走出地獄箭竹海`
7. `走出地獄箭竹海 -> 凹谷避風營地`

完成後驗證：

- D10 終點（MIT鞍部箭竹營地）與 D11 起點 gap = 0
- D11 內部段間 gap 全為 0

若 Overpass 不穩定，D11 可改用 `assets/data/osm_bbox_cache` 內已快取的 way 幾何切段：

- 主線：`410981216`
- 摩即山支線：`585194003`
- 依 waypoint 在 way 上最近點切出每段 `trackPoints`（避免 `manual-linear` 直線感）

## D12 Companion Rules

當使用者要求「做 D12 地圖」時，優先確保跨日銜接與可視化連續性：

- D12 起點 `凹谷避風營地` 必須與 D11 終點同座標：`23.8232750, 121.2366500`
- 先用 GPX 校正過的 waypoint 重建 `trackPoints`，必要時可用 `manual-linear + densify`（最大步長 `<= 40m`）
- `草山岔路口` 暫以 `interpolated` 管理，避免錯誤跳到非主稜線
- 其餘 D12 主要點（草山、卡社池、台電豪華工寮）優先使用 `gpx-exact`

完成後驗證：

- D11 -> D12 跨日 gap = 0
- D12 內部段間 gap = 0
- D12 `trackPoints` 數量與 `segments` 一致

若使用者要求「草山岔路口移到藍色叉叉」且「刪除草山下大黑水塘」：

- `草山岔路口` 改為 `23.8220285, 121.2375703`
- 從 D12 `segments` / `waypoints` 移除 `草山下大黑水塘`
- 將中段改為 `草山岔路口 -> 凹谷水池平坦大營地`（目前模板 `0.78km / 50min`）

若再要求「依據 OSM 重新產生 track points」：

- D12 改用 OSM way cache 切段（非 manual-linear）
- 主線用 `410981216`，草山支線往返用 `585194004`
- metadata.method 應為 `osm-way-cache-slice`

若再要求「重新計算公里數、預估時間」：

- 每段公里數以該段 `trackPoints` 實際長度回填（保留 2 位小數）
- 預估時間可用 `80 分/公里` 並四捨五入到 `5 分鐘`

## D14 Companion Rules

當使用者要求修 D14（六順七彩段）時，優先用「先定 waypoint、再生 track、最後回填時間」流程：

### 1) Waypoint 優先（不要先動 track）

- 先只確認/列出 `assets/data/D14.json` 的 `waypoints`（名稱 + 座標），避免一邊改 track 一邊漂移點位。
- 若使用者持續要求「東/西/南/北幾公尺微調」，每次只位移 `六順山前三岔路口`，並同步：
  - `assets/data/D14.json`
  - `assets/data/geocode_cache.json`
- 若有 `六順山前三岔路口（回）`，統一改名為 `六順山前三岔路口`（回程仍可由 `segments` 表達，不靠 waypoint 名稱區分）。

### 2) 用目前 waypoint 重新產生 trackPoints

- 重建 `trackPoints1..N` 時，必須以「使用者目前確認過的 waypoint」做 anchor。
- 優先嘗試 OSM routing；失敗才用 linear fallback。
- 重建後檢查：
  - 每段 `trackPointsN` 存在且點數 > 1
  - `metadata.segments[*].method` 與 `track_km` 有更新
  - 段間連接 gap（`trackPointsN[-1] -> trackPointsN+1[0]`）盡量為 0

### 3) D14 常見缺口修補（這次實務）

若發生以下症狀，按順序修：

- `台電豪華工寮` 出發前段缺線：
  - 在 `trackPoints1` 前端補 connector，使 `trackPoints1[0] == waypoint(台電豪華工寮)`。
- `六順山登山口 -> 六順山前三岔路口` 後半段缺線：
  - 在 `trackPoints2` 尾端補 connector，使 `trackPoints2[-1] == waypoint(六順山前三岔路口)`。
- 段與段之間有小縫（數公尺～十幾公尺）：
  - 將下一段首點強制對齊上一段末點，消除可視化斷線。

### 4) 公里數與時間回填規則（D14）

- 公里數：以各段 `trackPoints` 實際長度回填到 `segments[*].distance`（2 位小數）。
- 時間：
  - 若使用者指定速率（例如 `1 公里 20 分鐘`），該段以速率重算。
  - 其餘段按使用者指定的上河參考時間回填。
- 完成後同步：
  - `metadata.total_distance_km`
  - `metadata.total_time_min`
  - `index.html` 的 D14 `data-minutes` 與 `本日合計`

### 5) D14 快速驗證清單

- [ ] `waypoints` 是最後一次使用者微調後座標（未被 routing 覆蓋）
- [ ] `trackPoints1` 起點 = `台電豪華工寮` waypoint
- [ ] `trackPoints2` 終點 = `六順山前三岔路口` waypoint
- [ ] 所有段間 gap = 0m（或極小且已人工銜接）
- [ ] D14 的 `segments.distance/time`、`metadata totals`、`index.html` 合計一致

## D15 Companion Rules

當使用者要求處理 D15（`2761最低鞍部營地 -> 2603公尺鞍部`）時，使用以下固定流程：

### 1) Waypoint 來源優先序

- `2761最低鞍部營地`：**必須**沿用 D14 終點同座標（跨日連續）
- 其餘點（`關門北山/關門山/巖山/2603公尺鞍部`）：
  1. 優先用使用者提供 GPX 的同名 waypoint
  2. 若無同名 waypoint，取 GPX track 最近點（需記錄距離與 source）
- 座標更新後同步：
  - `assets/data/D15.json` `waypoints`
  - `assets/data/geocode_cache.json` 對應條目

### 2) 以主路廊切段重建 trackPoints

- 先建立 `2761 -> 2603` 的主路廊（優先 OSM，失敗才 linear）
- 依 D15 `segments` 規劃里程（1.6/2.6/1.7/2.9）在主路廊上切分邊界
- 由切分邊界重建 `trackPoints1..4`，並回填：
  - `metadata.segments[*].method`
  - `metadata.segments[*].track_km`
- 段間 gap 要求：
  - `trackPoints1[-1] == trackPoints2[0]`
  - `trackPoints2[-1] == trackPoints3[0]`
  - `trackPoints3[-1] == trackPoints4[0]`

### 3) 跨日連續強制修正

- 若 D15 `trackPoints1[0]` 與 D14 終點不一致，補前導 connector（forced-start）
- 驗證：
  - `D14(2761)` -> `D15 waypoints[0]` gap = 0m
  - `D14(2761)` -> `D15 trackPoints1[0]` gap = 0m

### 4) 公里數與時間回填（D15）

- 公里數：以 `trackPoints` 實長回填 `segments[*].distance`（2 位小數）
- 時間：參考上河地圖固定配置
  - `210, 150, 40, 250`（總計 `650`）
- 同步：
  - `metadata.total_distance_km`
  - `metadata.total_time_min`
  - `index.html` D15 的 `data-minutes` 與 `本日合計`

### 5) D15 快速驗證清單

- [ ] `D15 waypoints[0]` 等於 D14 終點 `2761最低鞍部營地`
- [ ] `trackPoints1..4` 全存在且每段點數 > 1
- [ ] `trackPoints1 -> 2 -> 3 -> 4` 段間 gap 全部 = 0m
- [ ] `segments.distance` 與 `metadata.segments[*].track_km` 一致
- [ ] `metadata.total_time_min == 650`
- [ ] `index.html` D15 顯示本日合計 `650 分鐘`

## Time Mapping (Sunriver G12)

若使用上河地圖 `G12_hiking.jpg`，D8/D9 時間請回填：

- D8: `170, 160, 35, 30, 165, 85`（總計 `645`）
- D9: `5, 3, 70, 90, 60, 100, 100, 90, 110`（總計 `628`）

更新 JSON 後要同步：

- `metadata.total_time_min`
- `index.html` 的 `data-minutes` 與 `本日合計`

## Frontend Safety Guard

更新 `index.html` 時，**不要** 用會輸出 `\\g<1>` 字樣的替換式直接改 `<ol class=\"segments\" ...>`。

完成後必查：

- D8 區塊存在 `id=\"d8-segments\"`
- D9 區塊存在 `id=\"d9-segments\"`
- 檔案內不應有殘留 `\\g<1>`、`\\g<2>`

## Quick Commands

```bash
python3 scripts/build_d8_tracks.py
```

### D14 一鍵重建指令

以下指令會：

1. 用目前 `D14` 的 `waypoints` 逐段重建 `trackPoints1..N`（優先 OSM，失敗 fallback-linear）
2. 修補常見缺口（`trackPoints1` 起點對齊 `台電豪華工寮`、`trackPoints2` 終點對齊 `六順山前三岔路口`、段間 gap 歸零）
3. 以 `trackPoints` 回填 `D14` 各段公里數
4. 套用時間（第 1 段 `20 分/公里`，其餘依 D14 目前上河參考配置）
5. 同步 `index.html` 的 D14 `data-minutes` 與 `本日合計`

```bash
python3 - <<'PY'
import json, re, sys
from math import radians, sin, cos, atan2, sqrt
from pathlib import Path

ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT / 'scripts'))
from osm_trail_router import OsmTrailRouter, haversine_km

D14 = ROOT / 'assets' / 'data' / 'D14.json'
INDEX = ROOT / 'index.html'

def path_km(pts):
    return sum(haversine_km(pts[i], pts[i+1]) for i in range(len(pts)-1)) if len(pts) > 1 else 0.0

def interpolate(a, b, n):
    n = max(2, int(n))
    out = []
    for i in range(n):
        t = i / (n - 1)
        out.append({
            'lat': a['lat'] + (b['lat'] - a['lat']) * t,
            'lon': a['lon'] + (b['lon'] - a['lon']) * t,
        })
    return out

def linear_track(a, b, planned):
    d_geo = haversine_km(a, b)
    n = max(12, int(max(d_geo, planned or 0.3) * 20))
    return interpolate(a, b, n)

def sane(track_km, planned_km, geo_km):
    if track_km < 0.03:
        return False
    if planned_km > 0 and track_km > max(planned_km * 4, planned_km + 8):
        return False
    if geo_km < 20 and track_km > geo_km * 2.5 + 5:
        return False
    return True

def hav(a, b, c, d):
    R = 6371.0
    dlat = radians(c - a)
    dlon = radians(d - b)
    x = sin(dlat / 2) ** 2 + cos(radians(a)) * cos(radians(c)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(x), sqrt(1 - x))

d = json.loads(D14.read_text(encoding='utf-8'))
router = OsmTrailRouter()
segs = d['segments']
wps = {w['name']: {'lat': float(w['lat']), 'lon': float(w['lon'])} for w in d['waypoints']}

# 1) rebuild trackPoints
for k in list(d.keys()):
    if k.startswith('trackPoints'):
        del d[k]
meta_segments = []
for i, s in enumerate(segs, start=1):
    a, b = wps[s['from']], wps[s['to']]
    planned = float(s.get('distance') or 0)
    pts, way_ids, method = router.route_segment(a, b, planned)
    tkm = path_km(pts) if pts else 0.0
    if not pts or len(pts) < 2 or not sane(tkm, planned, haversine_km(a, b)):
        pts = linear_track(a, b, planned)
        way_ids = []
        method = 'fallback-linear'
        tkm = path_km(pts)
    key = f'trackPoints{i}'
    d[key] = [{'lat': p['lat'], 'lon': p['lon']} for p in pts]
    meta_segments.append({
        'trackPoints': key,
        'way_ids': sorted(set(way_ids)),
        'from': s['from'],
        'to': s['to'],
        'method': method,
        'track_km': round(tkm, 2),
    })

# 2) patch known D14 gaps
start_wp = wps['台電豪華工寮']
tri_wp = wps['六順山前三岔路口']
tp1 = d['trackPoints1']
if hav(start_wp['lat'], start_wp['lon'], tp1[0]['lat'], tp1[0]['lon']) * 1000 > 1:
    bridge = interpolate(start_wp, {'lat': tp1[0]['lat'], 'lon': tp1[0]['lon']}, 12)
    d['trackPoints1'] = bridge[:-1] + tp1
    meta_segments[0]['method'] += '+forced-start'
tp2 = d['trackPoints2']
if hav(tp2[-1]['lat'], tp2[-1]['lon'], tri_wp['lat'], tri_wp['lon']) * 1000 > 1:
    bridge = interpolate({'lat': tp2[-1]['lat'], 'lon': tp2[-1]['lon']}, tri_wp, 6)
    d['trackPoints2'] = tp2 + bridge[1:]
    meta_segments[1]['method'] += '+forced-end'
for i in range(len(meta_segments) - 1):
    k1 = meta_segments[i]['trackPoints']
    k2 = meta_segments[i + 1]['trackPoints']
    a = d[k1][-1]
    b = d[k2][0]
    gap_m = hav(a['lat'], a['lon'], b['lat'], b['lon']) * 1000
    if 0.5 < gap_m < 50:
        d[k2] = [{'lat': a['lat'], 'lon': a['lon']}] + d[k2]
        meta_segments[i + 1]['method'] += '+linked'

# 3) recalc distances by trackPoints
for i, s in enumerate(segs, start=1):
    key = f'trackPoints{i}'
    km = round(path_km(d[key]), 2)
    s['distance'] = km
    meta_segments[i - 1]['track_km'] = km

# 4) time mapping for D14
seg1_time = round(segs[0]['distance'] * 20)  # 20 min/km
fixed = [70, 100, 120, 100, 100]             # seg2..seg6
times = [seg1_time] + fixed
for i, t in enumerate(times):
    segs[i]['time'] = int(t)

# 5) metadata + index sync
total_min = sum(times)
total_km = round(sum(float(s['distance']) for s in segs), 1)
meta = d.get('metadata') or {}
meta['track_source'] = 'OpenStreetMap hiking paths (Overpass) - anchored by user-adjusted waypoints'
meta['segments'] = meta_segments
meta['total_distance_km'] = total_km
meta['total_time_min'] = total_min
d['metadata'] = meta

D14.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

html = INDEX.read_text(encoding='utf-8')
html = re.sub(
    r'(<span id=\"D14\"[^>]*>.*?<details class=\"day\" data-minutes=\")\\d+(\"[^>]*>)',
    rf'\\g<1>{total_min}\\2',
    html, count=1, flags=re.DOTALL
)
html = re.sub(
    r'(<span id=\"D14\"[^>]*>.*?<div class=\"footer-line\">本日合計：)\\d+( 分鐘</div>)',
    rf'\\g<1>{total_min}\\2',
    html, count=1, flags=re.DOTALL
)
INDEX.write_text(html, encoding='utf-8')

print('D14 rebuilt')
print('total_km=', total_km, 'total_min=', total_min)
for i, s in enumerate(segs, start=1):
    print(i, s['from'], '->', s['to'], 'km=', s['distance'], 'time=', s['time'])
PY
```

驗證：

```bash
python3 - <<'PY'
import json,re,sys
sys.path.insert(0,'scripts')
from osm_trail_router import haversine_km
j=json.load(open('assets/data/D8.json'))
keys=sorted([k for k in j if k.startswith('trackPoints') and re.findall(r'\d+',k)], key=lambda x:int(re.findall(r'\d+',x)[0]))
for i in range(len(keys)-1):
    a=j[keys[i]][-1]; b=j[keys[i+1]][0]
    print('gap',i+1,'->',i+2,round(haversine_km(a,b)*1000,2),'m')
mx=0
for k in keys:
    p=j[k]
    if len(p)>1:
        mx=max(mx,max(haversine_km(p[i],p[i+1])*1000 for i in range(len(p)-1)))
print('max_step_m',round(mx,1))
PY
```

## Notes

- 優先確保「連續可用」與「地圖視覺正確」，再追求 way-id 級別精準化。
- 若 OSM API 不穩，先用已知合理 corridor 重建，再於下一輪替換為更精準 OSM 路徑。
- `能高山主峰` 視為 `能高山` 別名；資料命名以 `能高山` 為主，cache 可保留 alias。
