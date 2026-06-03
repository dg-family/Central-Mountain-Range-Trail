#!/usr/bin/env python3
"""Rebuild D9 tracks with corrected Nenggao south corridor coordinates."""
import json
import re
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "data"
sys.path.insert(0, str(ROOT / "scripts"))
from osm_trail_router import OsmTrailRouter, haversine_km  # noqa: E402

D9_PATH = DATA / "D9.json"
GEO_CACHE = DATA / "geocode_cache.json"

FORK = {"lat": 23.9657146, "lon": 121.2776812}  # OSM junction 862885347+1189837906
SOUTH_PEAK = {"lat": 23.9653660, "lon": 121.2781119}  # OSM peak
END_D9 = {"lat": 23.8876028, "lon": 121.2643520}  # 屯鹿妹池 (OSM)

FIXED_WAYPOINTS = {
    "南峰岔路口": {"lat": 23.9657146, "lon": 121.2776812},
    "能高山南峰": {"lat": 23.9653660, "lon": 121.2781119},
    "能高南峰南鞍營地": {"lat": 23.9595919, "lon": 121.2752354},
    "南峰南鞍營地": {"lat": 23.9595919, "lon": 121.2752354},  # alias
    "3159峰南鞍營地": {"lat": 23.9474750, "lon": 121.2718900},
    "3039鞍營地": {"lat": 23.9474750, "lon": 121.2718900},  # alias
    "光頭山": {"lat": 23.9390826, "lon": 121.2731015},
    "白石池": {"lat": 23.9252855, "lon": 121.2755879},
    "萬里池": {"lat": 23.9012637, "lon": 121.2714844},
    "屯鹿妹池": {"lat": 23.8876028, "lon": 121.2643520},
}
FIXED_SOURCES = {
    "南峰岔路口": "osm-jct/862885347+1189837906",
    "能高山南峰": "osm-peak/能高山南峰",
    "能高南峰南鞍營地": "nominatim/osm",
    "南峰南鞍營地": "nominatim/osm",
    "3159峰南鞍營地": "nominatim/osm",
    "3039鞍營地": "nominatim/osm",
    "光頭山": "nominatim/osm",
    "白石池": "nominatim/osm",
    "萬里池": "nominatim/osm",
    "屯鹿妹池": "nominatim/osm",
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
    data = json.loads(D9_PATH.read_text(encoding="utf-8"))
    segs = data.get("segments", [])
    if len(segs) != 9:
        raise SystemExit("D9 segments not expected 9")

    router = OsmTrailRouter()

    # seg1/seg2: 南峰岔路口 <-> 能高山南峰 (out & back)
    loop_out, w_out, m_out = router.route_segment(FORK, SOUTH_PEAK, float(segs[0]["distance"]))
    if len(loop_out) < 2:
        raise SystemExit("failed to route seg1")
    loop_out = densify(loop_out, 0.04)
    loop_back = list(reversed(loop_out))

    # seg3~9: single corridor from fork to 屯鹿妹池
    main_pts, main_wids, main_method = router.route_segment(FORK, END_D9, sum(float(s["distance"]) for s in segs[2:]))
    if len(main_pts) < 2:
        raise SystemExit("failed to route main D9 corridor")
    main_pts = densify(main_pts, 0.04)
    total_main_km = path_km(main_pts)

    plans = [float(s["distance"]) for s in segs[2:]]
    plan_sum = sum(plans)
    boundaries = [0.0]
    run = 0.0
    for p in plans:
        run += p
        boundaries.append(total_main_km * (run / plan_sum if plan_sum else 0.0))
    boundaries[-1] = total_main_km

    for k in list(data.keys()):
        if k.startswith("trackPoints"):
            del data[k]

    data["trackPoints1"] = loop_out
    data["trackPoints2"] = loop_back
    for i in range(7):
        data[f"trackPoints{i+3}"] = subpath_between(main_pts, boundaries[i], boundaries[i + 1])

    # waypoints: use segment boundaries, but override fixed named points.
    names = [segs[0]["from"]] + [s["to"] for s in segs]
    boundary_points = [loop_out[0], loop_out[-1], loop_back[-1]]
    for i in range(7):
        boundary_points.append(data[f"trackPoints{i+3}"][-1])
    waypoints = []
    seen = set()
    for i, name in enumerate(names):
        if name in seen:
            continue
        p = FIXED_WAYPOINTS.get(name, boundary_points[i])
        waypoints.append({"name": name, "lat": p["lat"], "lon": p["lon"]})
        seen.add(name)
    data["waypoints"] = waypoints

    # metadata
    meta_segments = []
    meta_segments.append(
        {
            "trackPoints": "trackPoints1",
            "way_ids": sorted(set(w_out or [])),
            "from": segs[0]["from"],
            "to": segs[0]["to"],
            "method": m_out,
            "track_km": round(path_km(loop_out), 2),
        }
    )
    meta_segments.append(
        {
            "trackPoints": "trackPoints2",
            "way_ids": sorted(set(w_out or [])),
            "from": segs[1]["from"],
            "to": segs[1]["to"],
            "method": "osm-single-way-reverse",
            "track_km": round(path_km(loop_back), 2),
        }
    )
    for i in range(7):
        key = f"trackPoints{i+3}"
        meta_segments.append(
            {
                "trackPoints": key,
                "way_ids": sorted(set(main_wids or [])),
                "from": segs[i + 2]["from"],
                "to": segs[i + 2]["to"],
                "method": "osm-corridor-split" if main_method.startswith("osm") else main_method,
                "track_km": round(path_km(data[key]), 2),
            }
        )

    data["metadata"] = {
        "track_source": "OpenStreetMap hiking paths (D9 refined corridor split)",
        "total_distance_km": round(sum(float(s["distance"]) for s in segs), 1),
        "total_time_min": sum(int(s["time"]) for s in segs),
        "segments": meta_segments,
    }
    D9_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Sync cache
    cache = json.loads(GEO_CACHE.read_text(encoding="utf-8"))
    for wp in waypoints:
        source = FIXED_SOURCES.get(wp["name"], "d9-corridor-split")
        cache[wp["name"]] = {"lat": wp["lat"], "lon": wp["lon"], "source": source}
    GEO_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"D9 rebuilt: 9 tracks, main corridor {total_main_km:.2f}km, points {len(main_pts)}")


if __name__ == "__main__":
    main()
