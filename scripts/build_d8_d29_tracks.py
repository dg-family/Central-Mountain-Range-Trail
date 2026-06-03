#!/usr/bin/env python3
"""Build map tracks for D7–D29; preserve planned distance/time in JSON."""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "data"
CACHE = DATA / "geocode_cache.json"

# 中央山脈縱走合理範圍（排除 Nominatim 誤判）
BBOX = {"lat_min": 22.85, "lat_max": 24.45, "lon_min": 120.55, "lon_max": 121.45}

# 手動座標（登山常用 / OSM peak）
KNOWN = {
    "奇萊山屋營地": (24.1086735, 121.3269869),
    "奇萊主山": (24.086458, 121.3232629),
    "卡羅樓山": (24.0782975, 121.3158416),
    "奇萊裡山": (24.0625243, 121.3001493),
    "天池山莊": (24.0453283, 121.2796478),
    "光被八表紀念碑": (24.0282173, 121.2795283),
    "卡賀爾山": (24.0068789, 121.2703053),
    "能高山": (23.9923208, 121.2602380),
    "能高山主峰": (23.9923208, 121.2602380),  # alias: 等同能高山
    "能高小屋舊址": (23.468, 121.176),
    "台灣池營地": (23.9841799, 121.2619749),
    "大陸池營地": (23.9781801, 121.2641956),
    "能高南峰北嶺": (23.9742745, 121.2743815),
    "能高南峰南嶺": (23.9742745, 121.2743815),  # alias
    "能高山南峰": (23.9653660, 121.2781119),
    "南峰岔路口": (23.9657146, 121.2776812),
    "能高南峰南鞍營地": (23.9595919, 121.2752354),
    "南峰南鞍營地": (23.9595919, 121.2752354),  # alias
    "3159峰南鞍營地": (23.9474750, 121.2718900),
    "3039鞍營地": (23.9474750, 121.2718900),  # alias
    "屯鹿妹池": (23.8876028, 121.2643520),
    "白石山": (23.9075929, 121.2748252),
    "白石池": (23.9252855, 121.2755879),
    "光頭山": (23.9390826, 121.2731015),
    "萬里池": (23.9012637, 121.2714844),
    "北安東軍山東稜登山口": (23.8816966, 121.2631345),
    "安東軍山三岔路口營地": (23.8817100, 121.2630900),
    "安東軍山": (23.8727380, 121.2661060),
    "摩即草山三岔路口": (23.8734860, 121.2646940),
    "青草營地": (23.8712500, 121.2588500),
    "樹林營地": (23.8694040, 121.2574800),
    "摩即地段前的平坦營地": (23.8635059, 121.2525407),
    "MIT鞍部箭竹營地": (23.8510360, 121.2469500),
    "MIT鞍部鋪箭竹營地": (23.8510360, 121.2469500),  # alias
    "摩即三岔路口": (23.8465060, 121.2439400),
    "摩即山 2643M": (23.8462651, 121.2449682),
    "摩即山": (23.8463480, 121.2449950),
    "摩即山西峰": (23.8336908, 121.2378731),
    "摩即池": (23.8263879, 121.2365547),
    "摩即池畔營地": (23.8263879, 121.2365547),
    "摩即南鞍營地": (23.8413010, 121.2389450),
    "2640峰": (23.8130638, 121.2336643),
    "走出地獄箭竹海": (23.8293380, 121.2370300),
    "凹谷避風營地": (23.8232750, 121.2366500),
    "草山岔路口": (23.822225, 121.238380),
    "草山 2811M": (23.8211750, 121.2401100),
    "草山下大黑水塘": (23.8215470, 121.2392700),
    "凹谷水池平坦大營地": (23.8160670, 121.2351760),
    "漂亮石陣": (23.8028680, 121.2263100),
    "卡社大山前漂亮白木林": (23.7854770, 121.2280960),
    "卡社大山 2947M": (23.120, 121.310),
    "卡社池優美谷地": (23.7791020, 121.2168800),
    "台電豪華工寮": (23.7691250, 121.2075100),
    "六順山登山口": (23.485, 121.095),
    "七彩湖日出展望點": (23.488, 121.098),
    "網咖": (23.488, 121.098),
    "六順山前三岔路口": (23.490, 121.100),
    "2813鞍營地": (23.492, 121.102),
    "2761最低鞍部營地": (23.478, 121.102),
    "關門北山": (23.478, 121.105),
    "關門山": (23.476, 121.108),
    "巖山": (23.474, 121.110),
    "2603公尺鞍部": (23.472, 121.112),
    "大石公山": (23.470, 121.114),
    "小石公山": (23.468, 121.116),
    "2833公尺鞍部": (23.466, 121.118),
    "3255公尺峰下營地": (23.464, 121.120),
    "丹大山": (23.600, 121.213),
    "盧利拉駱山": (23.596, 121.200),
    "太平溪源營地": (23.582, 121.229),
    "三岔路營地": (23.575, 121.195),
    "馬路巴拉讓山": (23.581, 121.183),
    "東鞍營地": (23.584, 121.170),
    "僕落西擴山": (23.554, 121.146),
    "義西請馬至山": (23.587, 121.153),
    "烏妹浪胖池": (23.580, 121.140),
    "烏妹浪胖山": (23.575, 121.135),
    "哈伊拉羅溪北源營地": (23.570, 121.130),
    "馬利加南山": (23.520, 121.080),
    "馬利加南西鞍": (23.515, 121.075),
    "馬利亞文路山東峰": (23.510, 121.070),
    "馬博拉斯山屋": (24.078, 121.158),
    "馬博前岔路": (24.075, 121.155),
    "秀馬最低鞍部": (24.070, 121.150),
    "秀姑巒山": (23.386, 121.120),
    "秀姑坪岔路": (23.384, 121.118),
    "達芬尖山登山口": (23.280, 120.914),
    "大水窟山屋": (23.458, 121.018),
    "達芬谷山屋": (23.281, 120.914),
    "塔芬池": (23.275, 120.908),
    "轆轆山登山口": (23.198, 120.872),
    "轆轆谷山屋": (23.198, 120.872),
    "雲峰東峰三岔路口營地": (23.190, 120.865),
    "西北鞍南雙池營地": (23.185, 120.860),
    "拉庫音溪山屋": (23.165, 120.835),
    "新康山三岔路口": (23.155, 120.825),
    "嘉明湖岔路口": (23.145, 120.815),
    "三叉山登山口": (23.135, 120.805),
    "向陽山北峰下解說牌": (23.125, 120.795),
    "向陽三岔路口": (23.115, 120.785),
    "嘉明湖避難山屋": (23.105, 120.775),
    "向陽西側登山口": (23.095, 120.765),
    "西側登山口": (23.095, 120.765),
    "向陽森林遊樂區": (23.249, 121.002),
    "進涇橋": (23.257803, 120.9188),
    "3026庫哈諾辛山屋": (23.254658, 120.910291),
    "庫哈諾辛山屋": (23.254658, 120.910291),
    "3444 主稜": (23.236507, 120.915356),
    "關山": (23.228039, 120.911721),
    "2920鞍部營地": (23.221353, 120.911179),
    "海諾南山": (23.209776, 120.911445),
    "海諾南山下營地": (23.208874, 120.911445),
    "小關山北峰": (23.350, 120.978),
    "四岔路口": (23.345, 120.975),
    "雲水山": (23.129, 121.012),
    "雲馬最低鞍部營地": (23.125, 121.008),
    "馬西巴秀山": (23.120, 121.005),
    "馬西巴秀石洞營地": (23.118, 121.003),
    "3237公尺峰": (23.116, 121.001),
    "三叉峰下營地": (23.118, 121.045),
    "嘆息灣": (24.228, 121.318),
    "石瀑區": (23.110, 120.990),
    "石山岔路口": (23.108, 120.988),
    "石山西鞍": (23.106, 120.986),
    "溪南山登山口": (23.104, 120.984),
    "石山林道登山口 7K特生中心": (23.100, 120.980),
    "松雪樓／奇萊登山口": (24.1392158, 121.2877891),
    "成功山屋": (24.1160195, 121.3186148),
}


def in_bbox(lat, lon):
    return BBOX["lat_min"] <= lat <= BBOX["lat_max"] and BBOX["lon_min"] <= lon <= BBOX["lon_max"]


def dist_km(a, b):
    from math import radians, sin, cos, atan2, sqrt

    R = 6371
    dLat = radians(b["lat"] - a["lat"])
    dLon = radians(b["lon"] - a["lon"])
    x = sin(dLat / 2) ** 2 + cos(radians(a["lat"])) * cos(radians(b["lat"])) * sin(dLon / 2) ** 2
    return R * 2 * atan2(sqrt(x), sqrt(1 - x))


def normalize_name(name):
    n = name.strip()
    n = re.sub(r"^途經[^→]+→\s*", "", n)
    if "→" in n:
        parts = [p.strip() for p in n.split("→")]
        n = parts[-1] if parts else n
    n = re.sub(r"\(.*?\)", "", n)
    n = re.sub(r"（.*?）", "", n)
    n = n.split("/")[0].strip()
    n = re.sub(r"\s*<[^>]+>", "", n)
    return n


def load_cache():
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache):
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def overpass_peak(name):
    """OSM 山峰查詢（中央山脈範圍）"""
    esc = name.replace('"', '\\"')
    query = f"""
    [out:json][timeout:25];
    (
      node["natural"="peak"]["name"="{esc}"]({BBOX['lat_min']},{BBOX['lon_min']},{BBOX['lat_max']},{BBOX['lon_max']});
      node["natural"="peak"]["name:zh"="{esc}"]({BBOX['lat_min']},{BBOX['lon_min']},{BBOX['lat_max']},{BBOX['lon_max']});
    );
    out 1;
    """
    url = "https://overpass-api.de/api/interpreter"
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "CentralMountainTrail/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            j = json.loads(resp.read())
        els = j.get("elements", [])
        if els:
            return {"lat": els[0]["lat"], "lon": els[0]["lon"], "source": "overpass-peak"}
    except Exception as e:
        print(f"    overpass {name}: {e}")
    return None


def resolve_coord(name, cache):
    key = normalize_name(name)
    if not key:
        return None
    if key in KNOWN:
        lat, lon = KNOWN[key]
        return {"lat": lat, "lon": lon}
    if key in cache and cache[key]:
        c = cache[key]
        if in_bbox(c["lat"], c["lon"]):
            return {"lat": c["lat"], "lon": c["lon"]}
    # 部分匹配 KNOWN
    for k, (lat, lon) in KNOWN.items():
        if k in key or key in k:
            return {"lat": lat, "lon": lon}
    peak = overpass_peak(key)
    if peak:
        cache[key] = peak
        time.sleep(0.8)
        return peak
    return None


def interpolate(a, b, n=20):
    if n < 2:
        n = 2
    pts = []
    for i in range(n):
        t = i / (n - 1)
        pts.append({"lat": a["lat"] + (b["lat"] - a["lat"]) * t, "lon": a["lon"] + (b["lon"] - a["lon"]) * t})
    return pts


def fill_chain(names, seg_dists, resolved, cache):
    """在已解析端點之間，依規劃里程比例內插缺點座標。"""
    n = len(names)
    # 找已解析索引
    idx_ok = [i for i in range(n) if resolved.get(names[i])]
    if not idx_ok:
        return
    for a, b in zip(idx_ok, idx_ok[1:]):
        if b - a <= 1:
            continue
        ca = resolved[names[a]]
        cb = resolved[names[b]]
        dists = seg_dists[a:b]
        total = sum(dists) or (b - a)
        cum = 0.0
        for i in range(a + 1, b):
            cum += dists[i - 1] if i - 1 < len(dists) else 0
            t = cum / total if total else (i - a) / (b - a)
            resolved[names[i]] = {
                "lat": ca["lat"] + (cb["lat"] - ca["lat"]) * t,
                "lon": ca["lon"] + (cb["lon"] - ca["lon"]) * t,
            }


def build_segment_track(a, b, planned_km):
    d = dist_km(a, b)
    n = max(12, int(max(d, planned_km or 0.3) * 20))
    return interpolate(a, b, n)


def process_day(day_num, cache, prev_end=None):
    path = DATA / f"D{day_num}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    segs = data.get("segments", [])

    if not segs or (len(segs) == 1 and segs[0].get("time", 0) == 0):
        print(f"D{day_num}: skip (預備日)")
        return prev_end

    for k in list(data.keys()):
        if k.startswith("trackPoints"):
            del data[k]

    # 路線節點序列
    names = [segs[0]["from"]]
    seg_dists = []
    for s in segs:
        names.append(s["to"])
        seg_dists.append(float(s.get("distance") or 0))

    resolved = {}
    if prev_end:
        resolved[names[0]] = prev_end
    for nm in names:
        if nm not in resolved:
            c = resolve_coord(nm, cache)
            if c:
                resolved[nm] = c

    fill_chain(names, seg_dists, resolved, cache)

    if names[0] not in resolved and prev_end:
        resolved[names[0]] = prev_end

    all_track = []
    waypoints_ordered = []
    names_seen = set()

    def add_wp(name, coord):
        if name not in names_seen and coord:
            waypoints_ordered.append({"lat": coord["lat"], "lon": coord["lon"], "name": name})
            names_seen.add(name)

    prev = prev_end
    for i, seg in enumerate(segs):
        f, t = seg["from"], seg["to"]
        c_from = resolved.get(f) or prev
        c_to = resolved.get(t)
        if not c_from or not c_to:
            print(f"  D{day_num} seg{i+1} missing: {f} -> {t}")
            continue
        if i == 0:
            add_wp(f, c_from)
        add_wp(t, c_to)
        planned = float(seg.get("distance") or 0)
        seg_track = build_segment_track(c_from, c_to, planned)
        if all_track and dist_km(all_track[-1], seg_track[0]) < 0.001:
            seg_track = seg_track[1:]
        all_track.extend(seg_track)
        prev = c_to

    data["waypoints"] = waypoints_ordered
    data["trackPoints"] = all_track
    meta = data.get("metadata") or {}
    meta["track_source"] = "planned segments + geocoded/interpolated waypoints"
    meta["total_distance_km"] = round(sum(float(s.get("distance") or 0) for s in segs), 1)
    meta["total_time_min"] = sum(int(s.get("time") or 0) for s in segs)
    data["metadata"] = meta

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"D{day_num}: {len(all_track)} pts, {meta['total_distance_km']}km, "
        f"{meta['total_time_min']}min, {len(waypoints_ordered)} wp"
    )
    return prev


def seed_cache():
    cache = load_cache()
    for k, v in list(cache.items()):
        if v and not in_bbox(v["lat"], v["lon"]):
            cache[k] = None
    for k, (lat, lon) in KNOWN.items():
        cache[k] = {"lat": lat, "lon": lon, "source": "known"}
    for d in range(1, 7):
        p = DATA / f"D{d}.json"
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        for w in data.get("waypoints", []):
            lat, lon = w.get("lat"), w.get("lon")
            if lat and (lat != 0 or lon != 0) and in_bbox(lat, lon):
                key = normalize_name(w["name"])
                cache[key] = {"lat": lat, "lon": lon, "source": f"D{d}"}
    save_cache(cache)
    return cache


def sync_index_minutes():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    for d in range(7, 30):
        p = DATA / f"D{d}.json"
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        total = sum(int(s.get("time") or 0) for s in data.get("segments", []))
        html = re.sub(
            rf'(<span id="D{d}"[^>]*>.*?<details class="day" data-minutes=")\d+(")',
            rf"\g<1>{total}\2",
            html,
            count=1,
            flags=re.DOTALL,
        )
        html = re.sub(
            rf'(id="d{d}-segments"[^>]*>[\s\S]*?<div class="footer-line">本日合計：)\d+( 分鐘</div>)',
            rf"\g<1>{total}\2",
            html,
            count=1,
        )
    (ROOT / "index.html").write_text(html, encoding="utf-8")
    print("index.html data-minutes synced")


def main():
    cache = seed_cache()
    prev = {"lat": 24.1086735, "lon": 121.3269869}
    for d in range(7, 30):
        prev = process_day(d, cache, prev)
        if d % 4 == 0:
            save_cache(cache)
    save_cache(cache)
    sync_index_minutes()
    print("done")


if __name__ == "__main__":
    main()
