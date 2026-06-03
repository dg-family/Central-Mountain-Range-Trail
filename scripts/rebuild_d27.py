#!/usr/bin/env python3
"""Rebuild D27: 海諾南山下營地 → 雲水山營地（南一段 GPX 實走）。

關鍵修正：
  - 小關山北峰座標從 (23.35, 120.978) 錯誤值修正為 GPX 最高點
  - 最低鞍部從 (23.478, 121.102) 修正為四岔路口→雲水山間真正最低點
  - 雲水山營地座標已確認（d=0.005km）
  - seg2（前營地→北峰）時間從 5min 修正為 GPX 比例估算值
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
    "海諾南山下營地":   {"lat": 23.184612,  "lon": 120.911304},  # 由 D26 同步
    "小關山北峰前營地": {"lat": 23.163918,  "lon": 120.895152},  # GPX d=0.004km
    "小關山北峰":       {"lat": 23.151719,  "lon": 120.876091},  # GPX 最高點 3241m
    "小關山森林營地":   {"lat": 23.144500,  "lon": 120.883700},  # 森林營地
    "最低鞍部":         {"lat": 23.142810,  "lon": 120.885717},  # GPX 最低點 2915m
    "雲水山營地":       {"lat": 23.136900,  "lon": 120.887734},  # GPX d=0.005km
}

WAYPOINT_ORDER = [
    "海諾南山下營地", "小關山北峰前營地", "小關山北峰",
    "小關山森林營地", "雲水山營地",
]

# 距離：GPX 實測；時間：G19 南一段步程示意圖（南行方向）
PLAN_DIST = [4.22,  3.94, 1.81,  1.62]
PLAN_TIME = [90,    85,   200,   90]
#             下→前  前→峰  峰→森  森→雲

# ── GPX 搜尋路徑 ──────────────────────────────────────────────────────────────
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


def nearest_from(pts: list, coord: dict, start: int, end: int | None = None) -> int:
    end = end or len(pts)
    best_i, best_d = start, float("inf")
    for i in range(start, end):
        d = haversine_km(coord, pts[i])
        if d < best_d:
            best_d, best_i = d, i
    return best_i


def round_pts(pts: list) -> list:
    return [{"lat": round(p["lat"], 6), "lon": round(p["lon"], 6)} for p in pts]


def gpx_slice(pts: list, ia: int, ib: int,
              snap_start: dict | None = None,
              snap_end: dict | None = None) -> list[dict]:
    core = pts[ia: ib + 1]
    out = [{"lat": p["lat"], "lon": p["lon"]} for p in core]
    if snap_start:
        out[0] = {"lat": snap_start["lat"], "lon": snap_start["lon"]}
    if snap_end:
        out[-1] = {"lat": snap_end["lat"], "lon": snap_end["lon"]}
    return out


# ── 找各段邊界索引 ────────────────────────────────────────────────────────────
def build_indices(pts: list, d26_end_idx: int) -> dict[str, int]:
    W = WAYPOINTS
    start = d26_end_idx

    i_start  = nearest_from(pts, W["海諾南山下營地"],   start, start + 100)
    i_pre    = nearest_from(pts, W["小關山北峰前營地"],  i_start)

    # 小關山北峰：前營地之後到雲水山之前的最高點
    i_cloud_approx = nearest_from(pts, W["雲水山營地"], i_pre)
    i_peak = max(range(i_pre, i_cloud_approx + 1),
                 key=lambda i: pts[i].get("ele") or 0)

    i_forest = nearest_from(pts, W["小關山森林營地"],    i_peak, i_peak + 2000)
    i_cloud  = nearest_from(pts, W["雲水山營地"],         i_forest)

    return {
        "海諾南山下營地":   i_start,
        "小關山北峰前營地": i_pre,
        "小關山北峰":       i_peak,
        "小關山森林營地":   i_forest,
        "雲水山營地":       i_cloud,
    }


# ── 主程式 ────────────────────────────────────────────────────────────────────
def main():
    # D26 結束點
    d26 = json.loads((DATA / "D26.json").read_text(encoding="utf-8"))
    d26_end = d26["waypoints"][-1]
    WAYPOINTS["海諾南山下營地"]["lat"] = d26_end["lat"]
    WAYPOINTS["海諾南山下營地"]["lon"] = d26_end["lon"]

    gpx_path = find_gpx()
    pts = load_gpx(gpx_path)
    print(f"GPX: {gpx_path} ({len(pts)} 點)")

    # 找 D26 結束的 GPX 索引
    d26_end_idx = nearest_from(pts, {"lat": d26_end["lat"], "lon": d26_end["lon"]}, 0)
    print(f"D26 結束: idx={d26_end_idx}")

    idx = build_indices(pts, d26_end_idx)

    for k, i in idx.items():
        print(f"  {k}: idx={i}, ele={pts[i]['ele']:.0f}m, "
              f"lat={pts[i]['lat']:.6f}, lon={pts[i]['lon']:.6f}")

    # ── 段落定義 ──────────────────────────────────────────────────────────────
    SEGMENTS_DEF = [
        ("海諾南山下營地",   "小關山北峰前營地"),
        ("小關山北峰前營地", "小關山北峰"),
        ("小關山北峰",       "小關山森林營地"),
        ("小關山森林營地",   "雲水山營地"),
    ]

    data = json.loads((DATA / "D27.json").read_text(encoding="utf-8"))
    segs = data["segments"]

    for k in list(data.keys()):
        if k.startswith("trackPoints"):
            del data[k]

    meta_segments = []
    for i, (wp_from, wp_to) in enumerate(SEGMENTS_DEF):
        track_key = f"trackPoints{i + 1}"
        ia = idx[wp_from]
        ib = idx[wp_to]
        track = gpx_slice(pts, ia, ib,
                          snap_start=WAYPOINTS[wp_from],
                          snap_end=WAYPOINTS[wp_to])
        km = path_km(track)

        data[track_key] = round_pts(track)

        segs[i]["from"]        = wp_from
        segs[i]["to"]          = wp_to
        segs[i]["distance"]    = PLAN_DIST[i]
        segs[i]["time"]        = PLAN_TIME[i]
        segs[i]["description"] = segs[i].get("description") or f"{wp_from} → {wp_to}"

        meta_segments.append({
            "trackPoints": track_key,
            "from": wp_from, "to": wp_to,
            "gpx_idx": [idx.get(wp_from, 0), idx.get(wp_to, 0)],
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
    meta["track_source"]      = "D27: GPX 南一段實走"
    meta["coord_reference"]   = str(gpx_path)
    meta["total_distance_km"] = round(sum(PLAN_DIST), 2)
    meta["total_time_min"]    = total_min
    meta["segments"]          = meta_segments
    data["metadata"] = meta

    (DATA / "D27.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # 更新 geocode cache
    cache = load_cache()
    cache_src = {
        "小關山北峰前營地": "gpx-南一段-前營地",
        "小關山北峰":       "gpx-南一段-最高點3241m",
        "小關山森林營地":   "gpx-南一段-森林營地",
        "雲水山營地":       "gpx-南一段-雲水山營地",
    }
    for nm, src in cache_src.items():
        wp = WAYPOINTS[nm]
        cache[nm] = {"lat": wp["lat"], "lon": wp["lon"], "source": src}
    save_cache(cache)

    # 同步 D28 起點
    d28_path = DATA / "D28.json"
    if d28_path.exists():
        d28 = json.loads(d28_path.read_text(encoding="utf-8"))
        end = data["waypoints"][-1]
        if d28.get("waypoints"):
            d28["waypoints"][0]["lat"] = end["lat"]
            d28["waypoints"][0]["lon"] = end["lon"]
        d28_path.write_text(
            json.dumps(d28, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print("D28 起點已同步")

    # 同步 index.html data-minutes
    html_path = ROOT / "index.html"
    if html_path.exists():
        html = html_path.read_text(encoding="utf-8")
        html = re.sub(
            r'(<span id="D27"[\s\S]*?<details class="day" data-minutes=")\d+(")',
            rf"\g<1>{total_min}\2", html, count=1,
        )
        html = re.sub(
            r'(id="d27-segments"[\s\S]*?本日合計：)\d+( 分鐘</div>)',
            rf"\g<1>{total_min}\2", html, count=1,
        )
        html_path.write_text(html, encoding="utf-8")
        print(f"index.html D27 data-minutes → {total_min}")

    total_km = sum(m["track_km"] for m in meta_segments)
    print(f"\nD27 完成：{len(SEGMENTS_DEF)} 段，GPX 軌跡 {total_km:.2f} km，計畫時間 {total_min} 分")


if __name__ == "__main__":
    main()
