#!/usr/bin/env python3
"""Rebuild D29: 三叉峰下營地 → 石山林道登山口（南一段 GPX 實走）。

主要修正：
  - 舊座標全錯（lon=120.91-120.98），實際路線向西北走（lon=120.79-120.87）
  - GPX 起點附近有三叉峰來回小迴圈，idx=4490→4791 含此段
  - 卑南主山 side trip 在 GPX 此段內，seg2 以單點表示
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_d8_d29_tracks import load_cache, save_cache  # noqa: E402
from osm_trail_router import haversine_km  # noqa: E402

# ── 座標（均從新 GPX 實走取得）────────────────────────────────────────────────
WAYPOINTS = {
    "三叉峰下營地":         {"lat": 23.058269, "lon": 120.871002},  # OSM 實際座標（由 D28 同步）
    "卑南主山":             {"lat": 23.051120, "lon": 120.874290},  # GPX 最高點 3281m（G19：3293m）
    "三叉路口":             {"lat": 23.058350, "lon": 120.871350},  # GPX 三叉峰來回後重返點
    "新舊路岔路":           {"lat": 23.072950, "lon": 120.859590},  # GPX 距離估算
    "林道鞍部":             {"lat": 23.078550, "lon": 120.850430},  # GPX 距離估算
    "石瀑區":               {"lat": 23.078410, "lon": 120.842110},  # GPX 距離估算
    "石山岔路口":           {"lat": 23.080010, "lon": 120.838900},  # GPX 距離估算
    "石山西鞍":             {"lat": 23.083140, "lon": 120.832060},  # GPX 距離估算
    "溪南山登山口":         {"lat": 23.084520, "lon": 120.823750},  # GPX 距離估算
    "石山林道登山口":       {"lat": 23.087580, "lon": 120.791700},  # GPX 距離估算
}

WAYPOINT_ORDER = [
    "三叉峰下營地", "卑南主山", "三叉路口",
    "新舊路岔路", "林道鞍部", "石瀑區",
    "石山岔路口", "石山西鞍", "溪南山登山口", "石山林道登山口",
]

# 距離：GPX 實測；時間：G19（南行方向）
# seg7 = 石山 side trip
PLAN_DIST = [1.07,  1.10,  2.61,  1.99,  1.10,  0.40,  0.10,  1.30,  1.00,  4.30]
PLAN_TIME = [35,    30,    145,   130,   100,   40,    4,     75,    15,    100]
#             下→卑  卑→三  三→新  新→林  林→石瀑 石瀑→岔 石山side 岔→西鞍 西鞍→溪南 溪南→登山口

GPX_FILE = ROOT / "assets" / "gpx" / "南一段.gpx"


def load_gpx(path: Path) -> list[dict]:
    ns = {"gpx": "http://www.topografix.com/GPX/1/1"}
    root = ET.parse(path).getroot()
    pts = []
    for tp in root.findall(".//gpx:trkpt", ns):
        ele_el = tp.find("gpx:ele", ns)
        pts.append({
            "lat": float(tp.get("lat")),
            "lon": float(tp.get("lon")),
            "ele": float(ele_el.text) if ele_el is not None and ele_el.text else None,
        })
    return pts


def path_km(pts):
    return sum(haversine_km(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def nearest_from(pts, coord, start, end=None):
    end = end or len(pts)
    best_i, best_d = start, float("inf")
    for i in range(start, end):
        d = haversine_km(coord, pts[i])
        if d < best_d:
            best_d, best_i = d, i
    return best_i


def idx_at_km(cum, target_km, from_idx):
    base = cum[from_idx]
    for i in range(from_idx, len(cum)):
        if cum[i] - base >= target_km:
            return i
    return len(cum) - 1


def round_pts(pts):
    return [{"lat": round(p["lat"], 6), "lon": round(p["lon"], 6)} for p in pts]


def gpx_slice(pts, ia, ib, snap_start=None, snap_end=None):
    out = [{"lat": p["lat"], "lon": p["lon"]} for p in pts[ia: ib + 1]]
    if snap_start:
        out[0] = {"lat": snap_start["lat"], "lon": snap_start["lon"]}
    if snap_end:
        out[-1] = {"lat": snap_end["lat"], "lon": snap_end["lon"]}
    return out


def build_indices(pts, d28_end_idx):
    W = WAYPOINTS

    i_start = nearest_from(pts, W["三叉峰下營地"], d28_end_idx, d28_end_idx + 100)

    # 卑南主山：i_start 後 lat < 23.055 範圍內的最高點（GPX idx≈4638）
    i_binan = max(
        (i for i in range(i_start, i_start + 500) if pts[i]["lat"] < 23.055),
        key=lambda i: pts[i].get("ele") or 0,
    )

    # 三叉路口：卑南主山之後重返起始緯度的點
    i_sanjiao = i_binan
    for i in range(i_binan + 1, len(pts)):
        if pts[i]["lat"] >= pts[i_start]["lat"]:
            i_sanjiao = i
            break

    # 建立累積距離表（從 i_sanjiao 起算）
    cum = [0.0] * len(pts)
    for i in range(i_sanjiao + 1, len(pts)):
        cum[i] = cum[i - 1] + haversine_km(pts[i - 1], pts[i])
    cum[i_sanjiao] = 0.0

    # 各段邊界依 G19 規劃距離定位
    plan_km = [2.61, 1.99, 1.10, 0.40, 1.30, 1.00, 4.30]
    names   = ["新舊路岔路", "林道鞍部", "石瀑區", "石山岔路口", "石山西鞍", "溪南山登山口", "石山林道登山口"]
    cum_km  = 0.0
    result  = {"三叉峰下營地": i_start, "卑南主山": i_binan, "三叉路口": i_sanjiao}
    for name, d in zip(names, plan_km):
        cum_km += d
        result[name] = idx_at_km(cum, cum_km, i_sanjiao)

    return result


def main():
    # D28 結束點
    d28 = json.loads((DATA / "D28.json").read_text(encoding="utf-8"))
    d28_end = d28["waypoints"][-1]
    WAYPOINTS["三叉峰下營地"]["lat"] = d28_end["lat"]
    WAYPOINTS["三叉峰下營地"]["lon"] = d28_end["lon"]

    if not GPX_FILE.exists():
        raise SystemExit(f"找不到 GPX：{GPX_FILE}")

    pts = load_gpx(GPX_FILE)
    print(f"GPX: {GPX_FILE} ({len(pts)} 點)")

    d28_end_idx = nearest_from(pts, {"lat": d28_end["lat"], "lon": d28_end["lon"]}, 0)
    print(f"D28 結束: idx={d28_end_idx}")

    idx = build_indices(pts, d28_end_idx)

    # 用 GPX 實際座標更新 WAYPOINTS
    for name, i in idx.items():
        if name in WAYPOINTS:
            WAYPOINTS[name]["lat"] = round(pts[i]["lat"], 6)
            WAYPOINTS[name]["lon"] = round(pts[i]["lon"], 6)

    for k, i in idx.items():
        print(f"  {k}: idx={i}, ele={pts[i]['ele']:.0f}m, "
              f"lat={pts[i]['lat']:.6f}, lon={pts[i]['lon']:.6f}")

    # ── 段落定義 ──────────────────────────────────────────────────────────────
    # seg2（卑南主山來回）= side trip，GPX 迴圈已含在 seg1，此處以單點表示
    SEGMENTS_DEF = [
        ("三叉峰下營地", "卑南主山",       True),
        ("卑南主山",     "三叉路口",       True),
        ("三叉路口",     "新舊路岔路",     True),
        ("新舊路岔路",   "林道鞍部",       True),
        ("林道鞍部",     "石瀑區",         True),
        ("石瀑區",       "石山岔路口",     True),
        ("石山岔路口",   "石山岔路口",     False),  # 石山 side trip
        ("石山岔路口",   "石山西鞍",       True),
        ("石山西鞍",     "溪南山登山口",   True),
        ("溪南山登山口", "石山林道登山口", True),
    ]

    data = json.loads((DATA / "D29.json").read_text(encoding="utf-8"))

    # 重建 segments
    new_segs = []
    for i, (wp_from, wp_to, _) in enumerate(SEGMENTS_DEF):
        new_segs.append({
            "from": wp_from, "to": wp_to,
            "distance": PLAN_DIST[i], "time": PLAN_TIME[i],
            "description": f"{wp_from} → {wp_to}",
        })
    data["segments"] = new_segs

    for k in list(data.keys()):
        if k.startswith("trackPoints"):
            del data[k]

    meta_segments = []
    for i, (wp_from, wp_to, use_gpx) in enumerate(SEGMENTS_DEF):
        track_key = f"trackPoints{i + 1}"
        if not use_gpx:
            pt = WAYPOINTS[wp_from]
            track = [{"lat": round(pt["lat"], 6), "lon": round(pt["lon"], 6)}]
            km = 0.0
        else:
            ia, ib = idx[wp_from], idx[wp_to]
            track = gpx_slice(pts, ia, ib,
                              snap_start=WAYPOINTS[wp_from],
                              snap_end=WAYPOINTS[wp_to])
            km = path_km(track)
        data[track_key] = round_pts(track)
        meta_segments.append({
            "trackPoints": track_key,
            "from": wp_from, "to": wp_to,
            "gpx_idx": [idx.get(wp_from, 0), idx.get(wp_to, 0)],
            "track_km": round(km, 2),
            "method": "gpx-slice" if use_gpx else "side-trip",
        })
        print(f"  seg{i+1} {wp_from} → {wp_to}: {km:.2f} km, {PLAN_TIME[i]} min")

    data["waypoints"] = [
        {"name": nm, "lat": round(WAYPOINTS[nm]["lat"], 6), "lon": round(WAYPOINTS[nm]["lon"], 6)}
        for nm in WAYPOINT_ORDER
    ]
    data.pop("trackPoints", None)

    total_min = sum(PLAN_TIME)
    meta = data.get("metadata") or {}
    meta["track_source"]      = "D29: GPX 南一段實走（南一段.gpx）"
    meta["coord_reference"]   = str(GPX_FILE)
    meta["total_distance_km"] = round(sum(PLAN_DIST), 2)
    meta["total_time_min"]    = total_min
    meta["segments"]          = meta_segments
    data["metadata"] = meta

    (DATA / "D29.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    cache = load_cache()
    for nm in WAYPOINT_ORDER:
        wp = WAYPOINTS[nm]
        cache[nm] = {"lat": wp["lat"], "lon": wp["lon"], "source": "gpx-南一段-D29"}
    save_cache(cache)

    html_path = ROOT / "index.html"
    if html_path.exists():
        html = html_path.read_text(encoding="utf-8")
        html = re.sub(
            r'(<span id="D29"[\s\S]*?<details class="day" data-minutes=")\d+(")',
            rf"\g<1>{total_min}\2", html, count=1,
        )
        html = re.sub(
            r'(id="d29-segments"[\s\S]*?本日合計：)\d+( 分鐘</div>)',
            rf"\g<1>{total_min}\2", html, count=1,
        )
        html_path.write_text(html, encoding="utf-8")
        print(f"index.html D29 data-minutes → {total_min}")

    total_km = sum(m["track_km"] for m in meta_segments)
    print(f"\nD29 完成：{len(SEGMENTS_DEF)} 段，GPX 軌跡 {total_km:.2f} km，計畫時間 {total_min} 分")


if __name__ == "__main__":
    main()
