#!/usr/bin/env python3
"""Rebuild D28: 雲水山營地 → 三叉峰下營地（南一段 GPX 實走）。

主要修正：
  - 所有座標從錯誤的 lon≈121.x 修正為 GPX 實走值（lon≈120.87-120.89）
  - trackPoints 改為 GPX 實走軌跡
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

# ── 座標 ──────────────────────────────────────────────────────────────────────
WAYPOINTS = {
    "雲水山營地":           {"lat": 23.136914, "lon": 120.887736},  # GPX d=0.005km（由 D27 同步）
    "雲馬最低鞍部營地":     {"lat": 23.118108, "lon": 120.884915},  # GPX 最低點 2858m
    "馬西巴秀山":           {"lat": 23.110371, "lon": 120.889162},  # GPX 最高點 3028m
    "馬西巴秀石洞營地":     {"lat": 23.108300, "lon": 120.889175},  # 山頂後 ~0.3km
    "3237公尺峰":           {"lat": 23.068605, "lon": 120.875250},  # GPX 局部峰 3229m（lat>23.055 範圍最高）
    "三叉峰下營地":         {"lat": 23.058269, "lon": 120.871002},  # OSM 實際座標
}

WAYPOINT_ORDER = [
    "雲水山營地", "雲馬最低鞍部營地", "馬西巴秀山",
    "馬西巴秀石洞營地", "3237公尺峰", "三叉峰下營地",
]

# 距離：GPX 實測；時間：G19 南一段步程示意圖（南行方向）
PLAN_DIST = [2.96,  1.42, 0.30, 6.97,  0.92]
PLAN_TIME = [90,    70,   35,   330,   65]
#             雲→鞍  鞍→馬  馬→洞  洞→峰  峰→營

GPX_CANDIDATES = [
    ROOT / "assets" / "gpx" / "20260320-0324 南一段.gpx",
    Path.home() / "Downloads" / "20260320-0324 南一段.gpx",
    Path("/sessions/amazing-optimistic-volta/mnt/uploads/20260320-0324 南一段.gpx"),
]


def find_gpx() -> Path:
    for p in GPX_CANDIDATES:
        if p.exists():
            return p
    raise SystemExit("找不到 GPX：" + ", ".join(str(p) for p in GPX_CANDIDATES))


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


def path_km(pts: list) -> float:
    return sum(haversine_km(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def nearest_from(pts, coord, start, end=None):
    end = end or len(pts)
    best_i, best_d = start, float("inf")
    for i in range(start, end):
        d = haversine_km(coord, pts[i])
        if d < best_d:
            best_d, best_i = d, i
    return best_i


def round_pts(pts):
    return [{"lat": round(p["lat"], 6), "lon": round(p["lon"], 6)} for p in pts]


def gpx_slice(pts, ia, ib, snap_start=None, snap_end=None):
    out = [{"lat": p["lat"], "lon": p["lon"]} for p in pts[ia: ib + 1]]
    if snap_start:
        out[0] = {"lat": snap_start["lat"], "lon": snap_start["lon"]}
    if snap_end:
        out[-1] = {"lat": snap_end["lat"], "lon": snap_end["lon"]}
    return out


def build_indices(pts, d27_end_idx):
    W = WAYPOINTS
    i_start = nearest_from(pts, W["雲水山營地"], d27_end_idx, d27_end_idx + 200)

    # 雲馬最低鞍部：雲水山後的最低點
    i_saddle = min(range(i_start, i_start + 2000),
                   key=lambda i: pts[i].get("ele") or float("inf"))

    # 馬西巴秀山：鞍部後到 idx+3000 的最高點
    i_masi = max(range(i_saddle, i_saddle + 3000),
                 key=lambda i: pts[i].get("ele") or 0)

    # 馬西巴秀石洞營地：山頂後 ~0.3km
    km, i_cave = 0.0, i_masi
    for i in range(i_masi + 1, len(pts)):
        km += haversine_km(pts[i - 1], pts[i])
        if km >= 0.3:
            i_cave = i
            break

    # 3237公尺峰：石洞後、lat > 23.055 範圍內的最高局部峰
    # （三叉峰本身在 lat≈23.051，3237峰更北）
    i_peak = max(
        (i for i in range(i_cave, i_cave + 8000)
         if pts[i].get("ele") and pts[i]["lat"] > 23.055),
        key=lambda i: pts[i].get("ele") or 0,
    )

    # 三叉峰下營地：3237峰之後以 OSM 座標搜尋
    i_camp = nearest_from(pts, W["三叉峰下營地"], i_peak)

    return {
        "雲水山營地":       i_start,
        "雲馬最低鞍部營地": i_saddle,
        "馬西巴秀山":       i_masi,
        "馬西巴秀石洞營地": i_cave,
        "3237公尺峰":       i_peak,
        "三叉峰下營地":     i_camp,
    }


def main():
    # D27 結束點
    d27 = json.loads((DATA / "D27.json").read_text(encoding="utf-8"))
    d27_end = d27["waypoints"][-1]
    WAYPOINTS["雲水山營地"]["lat"] = d27_end["lat"]
    WAYPOINTS["雲水山營地"]["lon"] = d27_end["lon"]

    gpx_path = find_gpx()
    pts = load_gpx(gpx_path)
    print(f"GPX: {gpx_path} ({len(pts)} 點)")

    d27_end_idx = nearest_from(pts, {"lat": d27_end["lat"], "lon": d27_end["lon"]}, 0)
    print(f"D27 結束: idx={d27_end_idx}")

    idx = build_indices(pts, d27_end_idx)

    for k, i in idx.items():
        print(f"  {k}: idx={i}, ele={pts[i]['ele']:.0f}m, "
              f"lat={pts[i]['lat']:.6f}, lon={pts[i]['lon']:.6f}")

    SEGMENTS_DEF = [
        ("雲水山營地",       "雲馬最低鞍部營地"),
        ("雲馬最低鞍部營地", "馬西巴秀山"),
        ("馬西巴秀山",       "馬西巴秀石洞營地"),
        ("馬西巴秀石洞營地", "3237公尺峰"),
        ("3237公尺峰",       "三叉峰下營地"),
    ]

    data = json.loads((DATA / "D28.json").read_text(encoding="utf-8"))

    # 更新 segments 結構（統一名稱）
    new_segs = []
    for i, (wp_from, wp_to) in enumerate(SEGMENTS_DEF):
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
    for i, (wp_from, wp_to) in enumerate(SEGMENTS_DEF):
        ia, ib = idx[wp_from], idx[wp_to]
        track = gpx_slice(pts, ia, ib,
                          snap_start=WAYPOINTS[wp_from],
                          snap_end=WAYPOINTS[wp_to])
        km = path_km(track)
        track_key = f"trackPoints{i + 1}"
        data[track_key] = round_pts(track)
        meta_segments.append({
            "trackPoints": track_key,
            "from": wp_from, "to": wp_to,
            "gpx_idx": [ia, ib],
            "track_km": round(km, 2),
            "method": "gpx-slice",
        })
        print(f"  seg{i+1} {wp_from} → {wp_to}: {km:.2f} km, {PLAN_TIME[i]} min")

    data["waypoints"] = [
        {"name": nm, "lat": round(WAYPOINTS[nm]["lat"], 6), "lon": round(WAYPOINTS[nm]["lon"], 6)}
        for nm in WAYPOINT_ORDER
    ]
    data.pop("trackPoints", None)

    total_min = sum(PLAN_TIME)
    meta = data.get("metadata") or {}
    meta["track_source"]      = "D28: GPX 南一段實走"
    meta["coord_reference"]   = str(gpx_path)
    meta["total_distance_km"] = round(sum(PLAN_DIST), 2)
    meta["total_time_min"]    = total_min
    meta["segments"]          = meta_segments
    data["metadata"] = meta

    (DATA / "D28.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # geocode cache
    cache = load_cache()
    for nm in WAYPOINT_ORDER:
        wp = WAYPOINTS[nm]
        cache[nm] = {"lat": wp["lat"], "lon": wp["lon"], "source": "gpx-南一段"}
    save_cache(cache)

    # 同步 D29 起點
    d29_path = DATA / "D29.json"
    if d29_path.exists():
        d29 = json.loads(d29_path.read_text(encoding="utf-8"))
        end = data["waypoints"][-1]
        if d29.get("waypoints"):
            d29["waypoints"][0]["lat"] = end["lat"]
            d29["waypoints"][0]["lon"] = end["lon"]
        d29_path.write_text(
            json.dumps(d29, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print("D29 起點已同步")

    # index.html
    html_path = ROOT / "index.html"
    if html_path.exists():
        html = html_path.read_text(encoding="utf-8")
        html = re.sub(
            r'(<span id="D28"[\s\S]*?<details class="day" data-minutes=")\d+(")',
            rf"\g<1>{total_min}\2", html, count=1,
        )
        html = re.sub(
            r'(id="d28-segments"[\s\S]*?本日合計：)\d+( 分鐘</div>)',
            rf"\g<1>{total_min}\2", html, count=1,
        )
        html_path.write_text(html, encoding="utf-8")
        print(f"index.html D28 data-minutes → {total_min}")

    total_km = sum(m["track_km"] for m in meta_segments)
    print(f"\nD28 完成：{len(SEGMENTS_DEF)} 段，GPX 軌跡 {total_km:.2f} km，計畫時間 {total_min} 分")


if __name__ == "__main__":
    main()
