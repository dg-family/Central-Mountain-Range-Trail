#!/usr/bin/env python3
"""Rebuild D8 tracks from a continuous OSM graph path and split by plan."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "data"
sys.path.insert(0, str(ROOT / "scripts"))
from osm_trail_router import OsmTrailRouter, haversine_km  # noqa: E402

D8_PATH = DATA / "D8.json"
GEO_CACHE = DATA / "geocode_cache.json"

START = {"lat": 24.0282173, "lon": 121.2795283}  # 光被八表紀念碑
SOUTH_PEAK = {"lat": 23.9653660, "lon": 121.2781119}  # 能高山南峰（OSM peak）
TAIL_TO_JUNCTION_KM = 0.10  # D9 規劃：岔路 ↔ 南峰 各 0.1km
FIXED_WAYPOINTS = {
    # Use exact OSM peak nodes; do not replace with split-boundary points.
    "卡賀爾山": {"lat": 24.0068789, "lon": 121.2703053},
    "能高山": {"lat": 23.9923208, "lon": 121.2602380},
    "能高山主峰": {"lat": 23.9923208, "lon": 121.2602380},  # alias
    "台灣池營地": {"lat": 23.9841799, "lon": 121.2619749},  # 台灣池（OSM water）
    "大陸池營地": {"lat": 23.9781801, "lon": 121.2641956},  # OSM camp_site
    "南峰岔路口": {"lat": 23.9657146, "lon": 121.2776812},  # OSM path junction
}
FIXED_WAYPOINT_SOURCES = {
    "卡賀爾山": "osm-peak/6098335070",
    "能高山": "osm-peak/2268473312",
    "能高山主峰": "osm-peak/2268473312",
    "台灣池營地": "osm-water/590974738",
    "大陸池營地": "osm-node/7763559385",
    "南峰岔路口": "osm-jct/862885347+1189837906",
}


def path_km(pts):
    return sum(haversine_km(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def densify_path(pts, max_step_km=0.04):
    """Split long edges so map rendering does not show harsh jumps."""
    if len(pts) < 2:
        return pts
    out = [pts[0]]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        d = haversine_km(a, b)
        if d > max_step_km:
            pieces = int(d / max_step_km) + 1
            for j in range(1, pieces):
                t = j / pieces
                out.append(
                    {
                        "lat": a["lat"] + (b["lat"] - a["lat"]) * t,
                        "lon": a["lon"] + (b["lon"] - a["lon"]) * t,
                    }
                )
        out.append(b)
    return out


def route_main_path(router: OsmTrailRouter):
    """Route START -> SOUTH_PEAK using graph path in a focused bbox."""
    pad = 0.03
    south = min(START["lat"], SOUTH_PEAK["lat"]) - pad
    north = max(START["lat"], SOUTH_PEAK["lat"]) + pad
    west = min(START["lon"], SOUTH_PEAK["lon"]) - pad
    east = max(START["lon"], SOUTH_PEAK["lon"]) + pad
    elements = router.fetch_ways(south, west, north, east)
    if not elements:
        return [], []

    adj, nodes, _ = router.build_graph(elements)
    sa, _ = router.nearest_node(nodes, START, 5.0)
    sb, _ = router.nearest_node(nodes, SOUTH_PEAK, 5.0)
    if not sa or not sb:
        return [], []

    path_nodes, ways = router.dijkstra(adj, sa, sb)
    if not path_nodes or len(path_nodes) < 2:
        return [], []
    pts = [nodes[n] for n in path_nodes]
    return [{"lat": p["lat"], "lon": p["lon"]} for p in pts], list(ways or [])


def point_at_distance(pts, target_km):
    """Return point and edge index at distance from path start."""
    if target_km <= 0:
        return {"lat": pts[0]["lat"], "lon": pts[0]["lon"]}, 0
    walked = 0.0
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        d = haversine_km(a, b)
        if walked + d >= target_km and d > 0:
            t = (target_km - walked) / d
            return {
                "lat": a["lat"] + (b["lat"] - a["lat"]) * t,
                "lon": a["lon"] + (b["lon"] - a["lon"]) * t,
            }, i
        walked += d
    return {"lat": pts[-1]["lat"], "lon": pts[-1]["lon"]}, len(pts) - 2


def trim_tail(pts, ways, trim_km):
    total = path_km(pts)
    keep = max(0.2, total - trim_km)
    end_pt, end_edge = point_at_distance(pts, keep)
    out = [pts[0]]
    for i in range(1, end_edge + 1):
        out.append(pts[i])
    if haversine_km(out[-1], end_pt) > 0.0005:
        out.append(end_pt)
    return out, ways[: end_edge + 1]


def subpath_between(pts, ways, d0, d1):
    p0, e0 = point_at_distance(pts, d0)
    p1, e1 = point_at_distance(pts, d1)
    if e1 < e0:
        e0, e1, p0, p1 = e1, e0, p1, p0
    out = [p0]
    for i in range(e0 + 1, e1 + 1):
        out.append(pts[i])
    if haversine_km(out[-1], p1) > 0.0002:
        out.append(p1)
    seg_wids = sorted(set(ways[e0 : e1 + 1])) if ways else []
    return out, seg_wids


def main():
    data = json.loads(D8_PATH.read_text(encoding="utf-8"))
    segs = data.get("segments", [])
    if len(segs) < 2:
        raise SystemExit("D8 segments missing")

    plans = [float(s.get("distance") or 0.0) for s in segs]
    total_plan = sum(plans)

    router = OsmTrailRouter()
    full_pts, full_ways = route_main_path(router)
    if len(full_pts) < 2:
        raise SystemExit("failed to build D8 main path")

    # Trim last 0.1km to land on「南峰岔路口」rather than summit.
    full_pts, full_ways = trim_tail(full_pts, full_ways, TAIL_TO_JUNCTION_KM)
    total_track = path_km(full_pts)

    boundaries = [0.0]
    run = 0.0
    for p in plans:
        run += p
        boundaries.append(total_track * (run / total_plan if total_plan else 0.0))
    boundaries[-1] = total_track

    for k in list(data.keys()):
        if k.startswith("trackPoints"):
            del data[k]

    names = [segs[0]["from"]] + [s["to"] for s in segs]
    waypoints = []
    meta_segments = []
    boundary_points = []

    seg_count = len(segs)
    for i in range(seg_count):
        seg_pts, seg_wids = subpath_between(full_pts, full_ways, boundaries[i], boundaries[i + 1])
        seg_pts = densify_path(seg_pts, max_step_km=0.04)
        if len(seg_pts) < 2:
            raise SystemExit(f"bad segment {i+1}")
        key = f"trackPoints{i+1}"
        data[key] = seg_pts
        track_len = path_km(seg_pts)
        meta_segments.append(
            {
                "trackPoints": key,
                "way_ids": seg_wids,
                "from": segs[i]["from"],
                "to": segs[i]["to"],
                "method": "osm-graph-split",
                "track_km": round(track_len, 2),
            }
        )
        if i == 0:
            boundary_points.append(seg_pts[0])
        boundary_points.append(seg_pts[-1])

    for i, name in enumerate(names):
        p = FIXED_WAYPOINTS.get(name, boundary_points[i])
        waypoints.append({"name": name, "lat": p["lat"], "lon": p["lon"]})
    data["waypoints"] = waypoints

    data["metadata"] = {
        "track_source": "OpenStreetMap hiking paths (D8 graph-split)",
        "total_distance_km": round(sum(float(s["distance"]) for s in segs), 1),
        "total_time_min": sum(int(s["time"]) for s in segs),
        "segments": meta_segments,
    }
    D8_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Sync waypoint coords for later days' resolver.
    cache = json.loads(GEO_CACHE.read_text(encoding="utf-8"))
    for wp in waypoints:
        source = FIXED_WAYPOINT_SOURCES.get(wp["name"], "d8-graph-split")
        cache[wp["name"]] = {"lat": wp["lat"], "lon": wp["lon"], "source": source}
    GEO_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"D8 rebuilt: {len(meta_segments)} segs, {round(total_track,2)}km track, {len(full_pts)} pts")


if __name__ == "__main__":
    main()
