#!/usr/bin/env python3
"""Rebuild D26: 南一段實走 GPX（進涇橋→庫哈諾辛山屋→關山→海諾南山下營地）。

GPX 在山屋附近有一段北繞迴圈（側行探路），本腳本自動偵測並跳過，
只保留主線軌跡：進涇橋直上山屋（第一次抵達），離開山屋後沿稜南行。
"""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "data"
CACHE = DATA / "geocode_cache.json"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_d8_d29_tracks import load_cache, save_cache  # noqa: E402
from osm_trail_router import haversine_km  # noqa: E402

# ── 座標 ──────────────────────────────────────────────────────────────────────
WAYPOINTS = {
    "進涇橋":           {"lat": 23.257803,  "lon": 120.918800},
    "3026庫哈諾辛山屋": {"lat": 23.254658,  "lon": 120.910291},
    "3444 主稜":        {"lat": 23.236507,  "lon": 120.915356},
    "關山":             {"lat": 23.228039,  "lon": 120.911721},
    "2920鞍部營地":     {"lat": 23.221406,  "lon": 120.911214},  # 動態更新
    "海諾南山":         {"lat": 23.185514,  "lon": 120.911304},  # OSM 山頂節點
    "海諾南山下營地":   {"lat": 23.184612,  "lon": 120.911304},  # 山頂正南 ~100m
}

WAYPOINT_ORDER = [
    "進涇橋", "3026庫哈諾辛山屋", "3444 主稜",
    "關山", "2920鞍部營地", "海諾南山", "海諾南山下營地",
]

# 段落規劃距離(km) 與時間(min)
# 距離：GPX 實測（G19 地圖無標示 km，以實走為準）
PLAN_DIST = [2.29, 3.02, 1.61, 3.94, 3.92, 0.12]
# 時間：G19 南一段縱走步程示意圖（南行方向）
PLAN_TIME = [135,  150,  130,  180,  130,  15]

# ── GPX 搜尋路徑（依優先順序）────────────────────────────────────────────────
GPX_CANDIDATES = [
    ROOT / "assets" / "gpx" / "20260320-0324 南一段.gpx",
    Path.home() / "Downloads" / "20260320-0324 南一段.gpx",
    # uploads 沙盒路徑（Cowork 上傳）
    Path("/sessions/amazing-optimistic-volta/mnt/uploads/20260320-0324 南一段.gpx"),
]


def find_gpx() -> Path:
    for p in GPX_CANDIDATES:
        if p.exists():
            return p
    raise SystemExit(
        "找不到 GPX 檔案。請將 '20260320-0324 南一段.gpx' 放到:\n"
        + "\n".join(f"  {p}" for p in GPX_CANDIDATES)
    )


# ── GPX 讀取 ──────────────────────────────────────────────────────────────────
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
    if len(pts) < 10:
        raise SystemExit(f"GPX 點數太少（{len(pts)}）: {path}")
    return pts


# ── 工具函式 ──────────────────────────────────────────────────────────────────
def path_km(pts: list) -> float:
    return sum(haversine_km(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def nearest_from(pts: list, coord: dict, start: int = 0, end: int | None = None) -> int:
    """pts[start:end] 中距 coord 最近的索引。"""
    if end is None:
        end = len(pts)
    best_i, best_d = start, float("inf")
    for i in range(start, end):
        d = haversine_km(coord, pts[i])
        if d < best_d:
            best_d, best_i = d, i
    return best_i


def first_approach(pts: list, coord: dict, start: int, threshold_km: float) -> int:
    """pts[start:] 中第一個進入 threshold_km 以內的索引；找不到則退為最近點。"""
    for i in range(start, len(pts)):
        if haversine_km(coord, pts[i]) <= threshold_km:
            return i
    return nearest_from(pts, coord, start)


def round_pts(pts: list) -> list:
    return [{"lat": round(p["lat"], 6), "lon": round(p["lon"], 6)} for p in pts]


def gpx_slice(pts: list, ia: int, ib: int,
              snap_start: dict | None = None,
              snap_end: dict | None = None) -> list[dict]:
    """取 pts[ia:ib+1]，可選擇性地把首尾吸附到精確座標。"""
    if ia > ib:
        ia, ib = ib, ia
        core = list(reversed(pts[ia: ib + 1]))
    else:
        core = pts[ia: ib + 1]
    out = [{"lat": p["lat"], "lon": p["lon"]} for p in core]
    if snap_start:
        out[0] = {"lat": snap_start["lat"], "lon": snap_start["lon"]}
    if snap_end:
        out[-1] = {"lat": snap_end["lat"], "lon": snap_end["lon"]}
    return out


# ── 核心：找出段落邊界索引 ────────────────────────────────────────────────────
def build_indices(pts: list) -> dict[str, int]:
    """
    回傳各關鍵點在 GPX 的索引。

    山屋邏輯：
      GPX 在山屋區有一段北繞迴圈（側行）。
      - i_hut_arrive：進涇橋上山後第一次抵達山屋（迴圈前）
      - i_hut_depart：迴圈結束後再次回到山屋，準備南下
    之後各點依序往南，直接用 nearest_from 即可。
    """
    W = WAYPOINTS
    n = len(pts)

    # 進涇橋：GPX 前幾個點
    i_bridge = nearest_from(pts, W["進涇橋"], 0, 50)

    # 山屋第一次抵達：在 i_bridge 之後、最近點之前的第一個 <0.2km 入點
    i_hut_arrive = first_approach(pts, W["3026庫哈諾辛山屋"],
                                  i_bridge + 1, threshold_km=0.2)

    # 山屋迴圈期間（迴圈最遠點）：從 i_hut_arrive 找距山屋最遠的點
    search_end = min(i_hut_arrive + 3000, n)
    i_loop_far = max(range(i_hut_arrive, search_end),
                     key=lambda i: haversine_km(W["3026庫哈諾辛山屋"], pts[i]))

    # 山屋離開點：迴圈最遠點之後，再次回到 0.15km 以內的最近點
    i_hut_depart = nearest_from(pts, W["3026庫哈諾辛山屋"],
                                 i_loop_far, min(i_loop_far + 2000, n))

    # 往南各點：從 i_hut_depart 起依序找
    i_ridge  = nearest_from(pts, W["3444 主稜"],   i_hut_depart)
    i_guan   = nearest_from(pts, W["關山"],         i_ridge)

    # 2920 鞍部：關山到海諾南山之間的最低鞍部
    i_hai_approx = nearest_from(pts, W["海諾南山"], i_guan)
    i_saddle = _saddle_index(pts, i_guan, i_hai_approx)

    i_hai    = nearest_from(pts, W["海諾南山"],     i_saddle)
    i_camp   = nearest_from(pts, W["海諾南山下營地"], i_hai)

    return {
        "進涇橋":                    i_bridge,
        "3026庫哈諾辛山屋_arrive":   i_hut_arrive,
        "3026庫哈諾辛山屋_depart":   i_hut_depart,
        "3444 主稜":                 i_ridge,
        "關山":                      i_guan,
        "2920鞍部營地":              i_saddle,
        "海諾南山":                  i_hai,
        "海諾南山下營地":            i_camp,
    }


def _saddle_index(pts: list, i_start: int, i_end: int) -> int:
    """關山到海諾南山之間的最低鞍部（海拔最小值）。"""
    end = min(i_end, len(pts))
    best = i_start
    best_ele = pts[i_start].get("ele") or float("inf")
    for i in range(i_start + 1, end):
        e = pts[i].get("ele") or float("inf")
        if e < best_ele:
            best_ele, best = e, i
    return best


# ── 主程式 ────────────────────────────────────────────────────────────────────
def main():
    gpx_path = find_gpx()
    print(f"GPX: {gpx_path}")
    pts = load_gpx(gpx_path)
    print(f"GPX 點數: {len(pts)}")

    idx = build_indices(pts)

    # 動態更新 2920 鞍部座標
    sp = pts[idx["2920鞍部營地"]]
    WAYPOINTS["2920鞍部營地"]["lat"] = round(sp["lat"], 6)
    WAYPOINTS["2920鞍部營地"]["lon"] = round(sp["lon"], 6)

    # 印出偵測結果
    for k, i in idx.items():
        print(f"  {k}: idx={i}, ele={pts[i]['ele']:.0f}m, "
              f"lat={pts[i]['lat']:.6f}, lon={pts[i]['lon']:.6f}")

    # ── 建立六段軌跡 ──────────────────────────────────────────────────────────
    # (gpx_start_key, gpx_end_key, from_wp, to_wp)
    SEGMENTS_DEF = [
        ("進涇橋",                  "3026庫哈諾辛山屋_arrive", "進涇橋",           "3026庫哈諾辛山屋"),
        ("3026庫哈諾辛山屋_depart", "3444 主稜",               "3026庫哈諾辛山屋", "3444 主稜"),
        ("3444 主稜",               "關山",                    "3444 主稜",        "關山"),
        ("關山",                    "2920鞍部營地",            "關山",             "2920鞍部營地"),
        ("2920鞍部營地",            "海諾南山",                "2920鞍部營地",     "海諾南山"),
        ("海諾南山",                "海諾南山下營地",          "海諾南山",         "海諾南山下營地"),
    ]

    data = json.loads((DATA / "D26.json").read_text(encoding="utf-8"))
    segs = data["segments"]

    # 清除舊 trackPoints
    for k in list(data.keys()):
        if k.startswith("trackPoints"):
            del data[k]

    meta_segments = []
    for i, (ik_from, ik_to, wp_from, wp_to) in enumerate(SEGMENTS_DEF):
        ia = idx[ik_from]
        ib = idx[ik_to]
        track = gpx_slice(pts, ia, ib,
                          snap_start=WAYPOINTS[wp_from],
                          snap_end=WAYPOINTS[wp_to])
        km = path_km(track)
        track_key = f"trackPoints{i + 1}"
        data[track_key] = round_pts(track)

        segs[i]["from"]        = wp_from
        segs[i]["to"]          = wp_to
        segs[i]["distance"]    = PLAN_DIST[i]
        segs[i]["time"]        = PLAN_TIME[i]
        segs[i]["description"] = f"{wp_from} → {wp_to}"

        meta_segments.append({
            "trackPoints": track_key,
            "from":        wp_from,
            "to":          wp_to,
            "gpx_idx":     [ia, ib],
            "track_km":    round(km, 2),
            "method":      "gpx-slice",
        })
        print(f"  seg{i+1} {wp_from} → {wp_to}: "
              f"idx {ia}-{ib}, {km:.2f} km, {PLAN_TIME[i]} min")

    # waypoints
    data["waypoints"] = [
        {"name": nm, "lat": round(WAYPOINTS[nm]["lat"], 6), "lon": round(WAYPOINTS[nm]["lon"], 6)}
        for nm in WAYPOINT_ORDER
    ]
    data.pop("trackPoints", None)

    # metadata
    meta = data.get("metadata") or {}
    meta["track_source"]        = "D26: GPX 南一段實走；山屋北繞迴圈已排除"
    meta["time_reference"]      = "assets/reference/G19_hiking.jpg"
    meta["coord_reference"]     = str(gpx_path)
    meta["total_distance_km"]   = round(sum(PLAN_DIST), 2)
    meta["total_time_min"]      = sum(PLAN_TIME)
    meta["map_reference_total"] = {"distance_km": 10.4, "time_min": 610}
    meta["segments"]            = meta_segments
    data["metadata"] = meta

    (DATA / "D26.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # ── 更新 geocode cache ────────────────────────────────────────────────────
    cache = load_cache()
    cache_updates = {
        "進涇橋":           {"source": "台20進涇橋-手動微調"},
        "3026庫哈諾辛山屋": {"source": "gpx-庫哈諾辛山屋3026m"},
        "庫哈諾辛山屋":     {"source": "gpx-庫哈諾辛山屋3026m"},
        "3444 主稜":        {"source": "gpx-ele-3444m"},
        "關山":             {"source": "gpx-關山3668m"},
        "2920鞍部營地":     {"source": "gpx-關山下行1km鞍部"},
        "海諾南山":         {"source": "gpx-海諾南山3173m"},
        "海諾南山下營地":   {"source": "海諾南山正南100m"},
    }
    for nm, extra in cache_updates.items():
        wp = WAYPOINTS.get(nm) or WAYPOINTS.get("3026庫哈諾辛山屋")
        cache[nm] = {"lat": wp["lat"], "lon": wp["lon"], **extra}
    save_cache(cache)

    # ── 同步 D27 起點 ─────────────────────────────────────────────────────────
    d27_path = DATA / "D27.json"
    if d27_path.exists():
        d27 = json.loads(d27_path.read_text(encoding="utf-8"))
        end = data["waypoints"][-1]
        if d27.get("waypoints"):
            d27["waypoints"][0]["lat"] = end["lat"]
            d27["waypoints"][0]["lon"] = end["lon"]
        d27_path.write_text(
            json.dumps(d27, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print("D27 起點已同步")

    # ── 同步 index.html 的 data-minutes ─────────────────────────────────────
    import re
    total_min = meta["total_time_min"]
    html_path = ROOT / "index.html"
    if html_path.exists():
        html = html_path.read_text(encoding="utf-8")
        html = re.sub(
            r'(<span id="D26"[^>]*>[\s\S]*?<details class="day" data-minutes=")\d+(")',
            rf"\g<1>{total_min}\2",
            html, count=1,
        )
        html = re.sub(
            r'(id="d26-segments"[\s\S]*?本日合計：)\d+( 分鐘</div>)',
            rf"\g<1>{total_min}\2",
            html, count=1,
        )
        html_path.write_text(html, encoding="utf-8")
        print(f"index.html D26 data-minutes → {total_min}")

    total_km = sum(m["track_km"] for m in meta_segments)
    print(f"\nD26 完成：{len(SEGMENTS_DEF)} 段，GPX 軌跡 {total_km:.2f} km，計畫時間 {total_min} 分")


if __name__ == "__main__":
    main()
