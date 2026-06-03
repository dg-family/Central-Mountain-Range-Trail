#!/usr/bin/env python3
"""Rebuild D10 with Andong round-trip once and corrected junction."""
import json
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "data"
sys.path.insert(0, str(ROOT / "scripts"))
from osm_trail_router import OsmTrailRouter, haversine_km  # noqa: E402

D10_PATH = DATA / "D10.json"
GEO_CACHE = DATA / "geocode_cache.json"

# Corrected anchors on Andong/Moji corridor
START = {"lat": 23.8876028, "lon": 121.2643520}  # 屯鹿妹池
CAMP = {"lat": 23.8816966, "lon": 121.2631345}  # 安東軍山三岔路口營地
JCT = {"lat": 23.8735163, "lon": 121.2646684}  # 摩即草山三岔路口（精準）
ANDONG = {"lat": 23.8727074, "lon": 121.2661139}  # 安東軍山
MIT = {"lat": 23.8510360, "lon": 121.2469500}  # MIT鞍部箭竹營地 (GPX exact)
PRE_MIT_FLAT = {"lat": 23.86595, "lon": 121.25311}  # 摩即地段前的平坦營地 (proxy)

SEG_TEMPLATE = [
    ("屯鹿妹池", "安東軍山三岔路口營地", 1.3, 45, "屯鹿妹池 → 安東軍山三岔路口營地"),
    ("安東軍山三岔路口營地", "摩即草山三岔路口", 0.3, 8, "安東軍山三岔路口營地 → 摩即草山三岔路口"),
    ("摩即草山三岔路口", "安東軍山", 1.2, 50, "摩即草山三岔路口 → 安東軍山"),
    ("安東軍山", "摩即草山三岔路口", 0.2, 10, "安東軍山 → 摩即草山三岔路口"),
    ("摩即草山三岔路口", "青草營地", 0.9, 50, "摩即草山三岔路口 → 青草營地"),
    ("青草營地", "樹林營地", 0.35, 25, "青草營地 → 樹林營地"),
    ("樹林營地", "摩即地段前的平坦營地", 1.2, 85, "樹林營地 → 摩即地段前的平坦營地"),
    ("摩即地段前的平坦營地", "MIT鞍部箭竹營地", 2.8, 280, "摩即地段前的平坦營地 → MIT鞍部箭竹營地"),
]

FIXED_WAYPOINTS = {
    "屯鹿妹池": START,
    "安東軍山三岔路口營地": CAMP,
    "摩即草山三岔路口": JCT,  # same precise junction
    "安東軍山": ANDONG,
    "摩即地段前的平坦營地": PRE_MIT_FLAT,
    "MIT鞍部箭竹營地": MIT,
}
FIXED_SOURCES = {
    "屯鹿妹池": "nominatim/osm",
    "安東軍山三岔路口營地": "osm-node/安東軍山岔路",
    "摩即草山三岔路口": "osm-node/安東軍山岔路",
    "安東軍山": "nominatim/osm",
    "摩即地段前的平坦營地": "gpx-proxy/超大營地",
    "MIT鞍部箭竹營地": "gpx-exact",
}


def path_km(pts):
    return sum(haversine_km(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def densify(pts, max_step_km=0.04):
    if len(pts) < 2:
        return pts
    out = [pts[0]]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        d = haversine_km(a, b)
        if d > max_step_km:
            n = int(d / max_step_km) + 1
            for j in range(1, n):
                t = j / n
                out.append(
                    {
                        "lat": a["lat"] + (b["lat"] - a["lat"]) * t,
                        "lon": a["lon"] + (b["lon"] - a["lon"]) * t,
                    }
                )
        out.append(b)
    return out


def merge(parts, gap_bridge_km=0.25):
    out = []
    for part in parts:
        if not part:
            continue
        if out:
            g = haversine_km(out[-1], part[0])
            if 0.001 < g <= gap_bridge_km:
                n = max(3, int(g / 0.04) + 1)
                a, b = out[-1], part[0]
                for i in range(1, n):
                    t = i / n
                    out.append(
                        {
                            "lat": a["lat"] + (b["lat"] - a["lat"]) * t,
                            "lon": a["lon"] + (b["lon"] - a["lon"]) * t,
                        }
                    )
            if haversine_km(out[-1], part[0]) < 0.001:
                part = part[1:]
        out.extend(part)
    return densify(out, 0.04)


def point_at_distance(pts, km_target):
    if km_target <= 0:
        return {"lat": pts[0]["lat"], "lon": pts[0]["lon"]}, 0
    walked = 0.0
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        d = haversine_km(a, b)
        if walked + d >= km_target and d > 0:
            t = (km_target - walked) / d
            return {
                "lat": a["lat"] + (b["lat"] - a["lat"]) * t,
                "lon": a["lon"] + (b["lon"] - a["lon"]) * t,
            }, i
        walked += d
    return {"lat": pts[-1]["lat"], "lon": pts[-1]["lon"]}, len(pts) - 2


def subpath_between(pts, d0, d1):
    p0, e0 = point_at_distance(pts, d0)
    p1, e1 = point_at_distance(pts, d1)
    if e1 < e0:
        e0, e1, p0, p1 = e1, e0, p1, p0
    out = [p0]
    for i in range(e0 + 1, e1 + 1):
        out.append(pts[i])
    if haversine_km(out[-1], p1) > 0.0002:
        out.append(p1)
    return densify(out, 0.04)


def main():
    data = json.loads(D10_PATH.read_text(encoding="utf-8"))
    segs = data.get("segments", [])
    segs = [
        {"from": f, "to": t, "distance": d, "time": m, "description": desc}
        for f, t, d, m, desc in SEG_TEMPLATE
    ]
    data["segments"] = segs

    router = OsmTrailRouter()
    # seg1: 屯鹿妹池 -> 安東軍山三岔路口營地
    seg1, w1, m1 = router.route_segment(START, CAMP, float(segs[0]["distance"]))
    # seg2: 安東軍山三岔路口營地 -> 摩即草山三岔路口
    seg2, w2, m2 = router.route_segment(CAMP, JCT, float(segs[1]["distance"]))
    # seg3/seg4: 摩即草山三岔路口 -> 安東軍山 -> 摩即草山三岔路口 (來回一次)
    out_andong, w3, m3 = router.route_segment(JCT, ANDONG, float(segs[2]["distance"]))
    if len(seg1) < 2 or len(seg2) < 2 or len(out_andong) < 2:
        raise SystemExit("failed D10 early segments")
    seg1 = densify(seg1, 0.04)
    seg2 = densify(seg2, 0.04)
    out_andong = densify(out_andong, 0.04)
    seg3 = out_andong
    seg4 = list(reversed(out_andong))

    # seg5~8: continue from junction to end at MIT鞍部箭竹營地
    tail, w4, m4 = router.route_segment(JCT, MIT, sum(float(s["distance"]) for s in segs[4:]))
    if len(tail) < 2:
        raise SystemExit("failed D10 tail corridor")
    tail = densify(tail, 0.04)
    tail_km = path_km(tail)
    tail_plans = [float(s["distance"]) for s in segs[4:]]
    tail_sum = sum(tail_plans)
    bounds = [0.0]
    run = 0.0
    for p in tail_plans:
        run += p
        bounds.append(tail_km * (run / tail_sum if tail_sum else 0.0))
    bounds[-1] = tail_km

    for k in list(data.keys()):
        if k.startswith("trackPoints"):
            del data[k]
    data["trackPoints1"] = seg1
    data["trackPoints2"] = seg2
    data["trackPoints3"] = seg3
    data["trackPoints4"] = seg4
    for i in range(len(segs) - 4):
        data[f"trackPoints{i+5}"] = subpath_between(tail, bounds[i], bounds[i + 1])

    names = [segs[0]["from"]] + [s["to"] for s in segs]
    boundary_points = [data["trackPoints1"][0]] + [data[f"trackPoints{i+1}"][-1] for i in range(len(segs))]
    waypoints = []
    seen = set()
    for i, name in enumerate(names):
        if name in seen:
            continue
        p = FIXED_WAYPOINTS.get(name, boundary_points[i])
        waypoints.append({"name": name, "lat": p["lat"], "lon": p["lon"]})
        seen.add(name)
    data["waypoints"] = waypoints

    all_wids = sorted(set((w1 or []) + (w2 or []) + (w3 or []) + (w4 or [])))
    meta_segments = []
    methods = {
        1: m1,
        2: m2,
        3: m3,
        4: "osm-single-way-reverse" if m3.startswith("osm") else m3,
        5: m4,
        6: m4,
        7: m4,
    }
    for i in range(len(segs)):
        key = f"trackPoints{i+1}"
        meta_segments.append(
            {
                "trackPoints": key,
                "way_ids": all_wids,
                "from": segs[i]["from"],
                "to": segs[i]["to"],
                "method": "osm-corridor-split" if i >= 4 else methods[i + 1],
                "track_km": round(path_km(data[key]), 2),
            }
        )
    data["metadata"] = {
        "track_source": "OpenStreetMap hiking paths (D10 refined corridor split)",
        "total_distance_km": round(sum(float(s["distance"]) for s in segs), 1),
        "total_time_min": sum(int(s["time"]) for s in segs),
        "segments": meta_segments,
    }
    D10_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cache = json.loads(GEO_CACHE.read_text(encoding="utf-8"))
    for wp in waypoints:
        cache[wp["name"]] = {"lat": wp["lat"], "lon": wp["lon"], "source": FIXED_SOURCES.get(wp["name"], "d10-corridor-split")}
    GEO_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"D10 rebuilt: {len(segs)} tracks, tail {tail_km:.2f}km, andong_roundtrip {path_km(seg3):.2f}km")


if __name__ == "__main__":
    main()
