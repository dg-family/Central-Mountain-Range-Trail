#!/usr/bin/env python3
"""Rebuild D7 map tracks from OSM ways; preserve segment distance/time."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "data"
sys.path.insert(0, str(ROOT / "scripts"))
from osm_trail_router import OsmTrailRouter, haversine_km  # noqa: E402

MAIN_TRAIL = 358514963
SOUTH_TRAIL = 409912306
# 能高越嶺古道主線（避開深堀山支線 1096346714/1096346715）
NENGAO_LISHAN_JCT = 668168868        # 奇萊裡山 ↔ 奇萊南峰岔路
NENGAO_FORK_CONNECT = 234566667      # 奇萊南峰岔路 ↔ 南華山岔路
NENGAO_NANHUA_TO_TIANCHI = 234566673 # 南華山岔路 ↔ 天池山莊（南華山步道）
NENGAO_MAIN_SOUTH = 649829759        # 天池山莊 ↔ 光被八表方向
NENGAO_TO_MONUMENT = 234430102

PLACES = {
    "奇萊山屋營地": {"lat": 24.1086735, "lon": 121.3269869},
    "奇萊主山": {"lat": 24.086458, "lon": 121.3232629, "osm_node": 2268473288},
    "卡羅樓山": {"lat": 24.0782975, "lon": 121.3158416, "osm_node": 10088331384},
    "奇萊裡山": {"lat": 24.0625243, "lon": 121.3001493, "osm_node": 10839281050},
    "天池山莊": {"lat": 24.0453283, "lon": 121.2796478, "osm_way": 233579579},
    "光被八表紀念碑": {"lat": 24.0282173, "lon": 121.2795283, "osm_node": 2419444455},
    "奇萊南峰岔路": {"lat": 24.0558638, "lon": 121.2853298},
    "南華山岔路": {"lat": 24.0504987, "lon": 121.2841044},
}

SEG_TEXT = [
    ("奇萊山屋營地", "奇萊主山", "奇萊山屋營地 → 奇萊主山（奇萊主峰步道主徑來回）"),
    ("奇萊主山", "卡羅樓山", "奇萊主山 → 卡羅樓山"),
    ("卡羅樓山", "奇萊裡山", "卡羅樓山 → 奇萊裡山"),
    ("奇萊裡山", "奇萊南峰岔路", "奇萊裡山 → 奇萊南峰岔路"),
    ("奇萊南峰岔路", "南華山岔路", "奇萊南峰岔路 → 南華山岔路"),
    ("南華山岔路", "天池山莊", "南華山岔路 → 天池山莊"),
    ("天池山莊", "光被八表紀念碑", "天池山莊 → 光被八表紀念碑"),
]

SEG_PLAN = [
    (3.6, 150),
    (2.5, 180),
    (3.0, 200),
    (2.6, 70),
    (0.7, 20),
    (1.2, 30),
    (2.5, 40),
]


def load_way(router: OsmTrailRouter, wid: int):
    return router.fetch_way(wid)


def nearest_idx(pts, coord):
    best_i, best_d = 0, 1e9
    for i, p in enumerate(pts):
        d = haversine_km(p, coord)
        if d < best_d:
            best_d, best_i = d, i
    return best_i, best_d


def subpath_on_way(pts, a, b, max_snap_km=2.5):
    ia, da = nearest_idx(pts, a)
    ib, db = nearest_idx(pts, b)
    if da > max_snap_km or db > max_snap_km:
        return None
    if ia <= ib:
        sub = pts[ia : ib + 1]
    else:
        sub = list(reversed(pts[ib : ia + 1]))
    return [{"lat": p["lat"], "lon": p["lon"]} for p in sub] if len(sub) >= 2 else None


def path_km(pts):
    return sum(haversine_km(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def merge_paths(parts, max_gap_km=0.35):
    """Concatenate path segments; drop duplicate join point when gap is small."""
    merged = []
    for part in parts:
        if not part:
            continue
        if merged and haversine_km(merged[-1], part[0]) <= max_gap_km:
            part = part[1:] if haversine_km(merged[-1], part[0]) < 0.001 else part
        merged.extend(part)
    return merged if len(merged) >= 2 else []


def linear_bridge(a, b, steps=8):
    """短距補點，避免段與段之間留下明顯斷裂。"""
    if steps < 2:
        return [cp([a, b])[0], cp([a, b])[1]]
    out = []
    for i in range(steps + 1):
        t = i / steps
        out.append(
            {
                "lat": a["lat"] + (b["lat"] - a["lat"]) * t,
                "lon": a["lon"] + (b["lon"] - a["lon"]) * t,
            }
        )
    return out


def slice_way(pts, start, end):
    ia, da = nearest_idx(pts, start)
    ib, db = nearest_idx(pts, end)
    if da > 2.5 or db > 2.5:
        return None
    if ia <= ib:
        sub = pts[ia : ib + 1]
    else:
        sub = list(reversed(pts[ib : ia + 1]))
    return [{"lat": p["lat"], "lon": p["lon"]} for p in sub]


def build_seg1(router):
    """山屋沿主徑至奇萊主山（seg2 自山頂交會點沿主徑南下銜接）。"""
    main = load_way(router, MAIN_TRAIL)
    ia, _ = nearest_idx(main, PLACES["奇萊山屋營地"])
    ib, _ = nearest_idx(main, PLACES["奇萊主山"])
    if ib < ia:
        ia, ib = ib, ia
    out = [{"lat": p["lat"], "lon": p["lon"]} for p in main[ia : ib + 1]]
    return out, [MAIN_TRAIL], "osm-known-ways"


def build_seg2(router):
    """奇萊主山沿主徑南端 → 銜接卡羅樓方向步道 → 卡羅樓山。"""
    main = load_way(router, MAIN_TRAIL)
    south = load_way(router, SOUTH_TRAIL)
    ib, _ = nearest_idx(main, PLACES["奇萊主山"])
    ic, _ = nearest_idx(south, PLACES["卡羅樓山"])

    # 主徑從奇萊主山往南端延伸
    main_tail = [{"lat": p["lat"], "lon": p["lon"]} for p in main[ib:]]
    # 主徑終點 → 卡羅樓步道起點
    bridge, bw, _ = router.route_segment(main_tail[-1], south[1], 0.5)
    # 卡羅樓步道（自 south[1] 起）→ 卡羅樓山
    south_leg = subpath_on_way(south, south[1], PLACES["卡羅樓山"])

    parts = [main_tail]
    if bridge:
        parts.append(bridge)
    if south_leg:
        parts.append(south_leg)

    pts = merge_paths(parts)
    wids = [MAIN_TRAIL, SOUTH_TRAIL] + (bw or [])
    return pts, sorted(set(wids)), "osm-known-ways" if pts else "failed"


def build_seg3(router):
    """卡羅樓山 → 奇萊裡山（含步道末端至山頂銜接）。"""
    south = load_way(router, SOUTH_TRAIL)
    leg = subpath_on_way(south, PLACES["卡羅樓山"], south[-1], max_snap_km=3.0)
    if not leg:
        ic, _ = nearest_idx(south, PLACES["卡羅樓山"])
        leg = [{"lat": p["lat"], "lon": p["lon"]} for p in south[ic:]]

    tail, tw, _ = router.route_segment(leg[-1], PLACES["奇萊裡山"], 0.5)
    pts = merge_paths([leg, tail] if tail else [leg])
    wids = [SOUTH_TRAIL] + (tw or [])
    return pts, sorted(set(wids)), "osm-known-ways" if pts else "failed"


def cp(pts):
    return [{"lat": p["lat"], "lon": p["lon"]} for p in pts]


def build_chained(router, a, b, planned):
    chain = [a]
    for t in (0.33, 0.66):
        chain.append(
            {"lat": a["lat"] + (b["lat"] - a["lat"]) * t, "lon": a["lon"] + (b["lon"] - a["lon"]) * t}
        )
    chain.append(b)
    merged, wids = [], []
    for i in range(len(chain) - 1):
        sub, w, _ = router.route_segment(chain[i], chain[i + 1], planned / 3)
        if not sub:
            return [], [], "failed"
        merged = merge_paths([merged, sub])
        wids.extend(w)
    if merged:
        return merged, wids, "osm-chained"
    return [], [], "failed"


def _oriented(way, start):
    """回傳以最接近 start 的端點為起點的 way 副本。"""
    if haversine_km(way[0], start) <= haversine_km(way[-1], start):
        return cp(way)
    return cp(list(reversed(way)))


def build_seg4(router):
    """奇萊裡山 → 奇萊南峰岔路 → 南華山岔路 → 天池山莊（能高越嶺主線，不繞深堀山）。"""
    w668 = load_way(router, NENGAO_LISHAN_JCT)          # 裡山 ↔ 奇萊南峰岔路
    w667 = load_way(router, NENGAO_FORK_CONNECT)        # 奇萊南峰岔路 ↔ 南華山岔路
    w673 = load_way(router, NENGAO_NANHUA_TO_TIANCHI)   # 南華山岔路 ↔ 天池山莊
    if not all([w668, w667, w673]):
        return [], [], "failed"

    idx_l, _ = nearest_idx(w668, PLACES["奇萊裡山"])
    leg1 = cp(list(reversed(w668[: idx_l + 1])))        # 裡山 → 奇萊南峰岔路
    leg2 = _oriented(w667, PLACES["奇萊南峰岔路"])        # 奇萊南峰岔路 → 南華山岔路
    leg3 = _oriented(w673, PLACES["南華山岔路"])          # 南華山岔路 → 天池附近

    pts = merge_paths([leg1, leg2, leg3], max_gap_km=0.15)
    if pts and haversine_km(pts[-1], PLACES["天池山莊"]) > 0.06:
        tail, _, _ = router.route_segment(pts[-1], PLACES["天池山莊"], 0.1)
        pts = merge_paths([pts, tail or []], max_gap_km=0.15)

    if not pts:
        return [], [], "failed"
    wids = [NENGAO_LISHAN_JCT, NENGAO_FORK_CONNECT, NENGAO_NANHUA_TO_TIANCHI]
    return pts, sorted(set(wids)), "osm-known-ways"


def build_seg5(router):
    """天池山莊 → 光被八表紀念碑：能高越嶺古道 649829759 + 234430102。"""
    w759 = load_way(router, NENGAO_MAIN_SOUTH)
    w102 = load_way(router, NENGAO_TO_MONUMENT)
    if not w759 or not w102:
        return [], [], "failed"

    idx_t, _ = nearest_idx(w759, PLACES["天池山莊"])
    pts = merge_paths([cp(w759[idx_t:]), cp(w102)])

    tw = []
    if pts and haversine_km(pts[-1], PLACES["光被八表紀念碑"]) > 0.05:
        tail, tw, _ = router.route_segment(pts[-1], PLACES["光被八表紀念碑"], 0.2)
        pts = merge_paths([pts, tail or []])

    wids = [NENGAO_MAIN_SOUTH, NENGAO_TO_MONUMENT] + (tw or [])
    return pts, sorted(set(wids)), "osm-known-ways"


def main():
    path = DATA / "D7.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    segs = data.get("segments", [])
    router = OsmTrailRouter()

    for k in list(data.keys()):
        if k.startswith("trackPoints"):
            del data[k]

    if len(segs) != len(SEG_TEXT):
        segs = [{} for _ in SEG_TEXT]
        data["segments"] = segs

    for i, (f, t, desc) in enumerate(SEG_TEXT):
        d, m = SEG_PLAN[i]
        segs[i]["from"] = f
        segs[i]["to"] = t
        segs[i]["distance"] = d
        segs[i]["time"] = m
        segs[i]["description"] = desc

    data["waypoints"] = [{"name": n, **c} for n, c in PLACES.items()]
    meta_segs = []
    track_idx = 0

    def add_track(seg_num, pts, wids, method):
        nonlocal track_idx
        if not pts:
            print(f"  seg{seg_num}: skip track")
            return
        track_idx += 1
        key = f"trackPoints{track_idx}"
        data[key] = pts
        tk = path_km(pts)
        meta_segs.append(
            {
                "trackPoints": key,
                "way_ids": sorted(set(wids)),
                "from": segs[seg_num - 1]["from"],
                "to": segs[seg_num - 1]["to"],
                "method": method,
                "track_km": round(tk, 2),
            }
        )
        planned = float(segs[seg_num - 1]["distance"])
        print(f"  seg{seg_num}: {method} {len(pts)}pts {tk:.1f}km (plan {planned}km)")

    builders = [
        (1, lambda: build_seg1(router)),
        (2, lambda: build_seg2(router)),
        (3, lambda: build_seg3(router)),
    ]

    for seg_num, job in builders:
        pts, wids, method = job()
        planned = float(segs[seg_num - 1]["distance"])
        if not pts and seg_num == 3:
            pts, wids, method = router.route_segment(
                PLACES["卡羅樓山"], PLACES["奇萊裡山"], planned
            )
        add_track(seg_num, pts, wids, method)

    # seg4~6: split by fork waypoints
    pts456, w456, method456 = build_seg4(router)
    if pts456:
        i_q, _ = nearest_idx(pts456, PLACES["奇萊南峰岔路"])
        i_n, _ = nearest_idx(pts456, PLACES["南華山岔路"])
        if i_n < i_q:
            i_q, i_n = i_n, i_q
        seg4_pts = pts456[: i_q + 1]
        seg5_pts = pts456[i_q : i_n + 1]
        seg6_pts = pts456[i_n:]
        add_track(4, seg4_pts, [NENGAO_LISHAN_JCT], method456)
        add_track(5, seg5_pts, [NENGAO_FORK_CONNECT], method456)
        add_track(6, seg6_pts, [NENGAO_NANHUA_TO_TIANCHI], method456)
    else:
        for seg_num in (4, 5, 6):
            a, b = PLACES[segs[seg_num - 1]["from"]], PLACES[segs[seg_num - 1]["to"]]
            planned = float(segs[seg_num - 1]["distance"])
            pts, wids, method = router.route_segment(a, b, planned)
            add_track(seg_num, pts, wids, method)

    # seg7: 直接從 seg6 終點續接至光被八表，避免天池山莊出口跳點
    prev = data.get(f"trackPoints{track_idx}", [])
    start7 = prev[-1] if prev else PLACES["天池山莊"]
    plan7 = float(segs[6]["distance"])
    pts7, w7, m7 = router.route_segment(start7, PLACES["光被八表紀念碑"], plan7)
    if not pts7:
        pts7, w7, m7 = build_seg5(router)
    if prev and pts7 and haversine_km(prev[-1], pts7[0]) > 0.02:
        bridge1, bw1, _ = router.route_segment(prev[-1], pts7[0], 0.2)
        stitched_parts = []
        stitched_wids = []
        if bridge1:
            stitched_parts.append(bridge1)
            stitched_wids.extend(bw1 or [])
            end1 = bridge1[-1]
            if haversine_km(end1, pts7[0]) > 0.02:
                bridge2, bw2, _ = router.route_segment(end1, pts7[0], 0.2)
                if bridge2:
                    if haversine_km(end1, bridge2[0]) > 0.01:
                        stitched_parts.append(linear_bridge(end1, bridge2[0], steps=6))
                    stitched_parts.append(bridge2)
                    stitched_wids.extend(bw2 or [])
                else:
                    stitched_parts.append(linear_bridge(end1, pts7[0], steps=8))
        if stitched_parts:
            pts7 = merge_paths(stitched_parts + [pts7], max_gap_km=0.15)
            w7 = list(w7) + stitched_wids
    add_track(7, pts7, w7, m7)

    data.pop("trackPoints", None)
    data["metadata"] = {
        "track_source": "OpenStreetMap (D7 qilai/nenggao trails)",
        "total_distance_km": round(sum(float(s["distance"]) for s in segs), 1),
        "total_time_min": sum(int(s["time"]) for s in segs),
        "segments": meta_segs,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"D7: {track_idx} tracks, {data['metadata']['total_distance_km']}km, {data['metadata']['total_time_min']}min")


if __name__ == "__main__":
    main()
