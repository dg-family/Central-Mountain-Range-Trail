#!/usr/bin/env python3
"""Apply OSM hiking trail geometry to D7–D29 (preserve segment distance/time)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "data"
KNOWN_WAYS_PATH = DATA / "known_segment_ways.json"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from osm_trail_router import OsmTrailRouter, haversine_km  # noqa: E402

# Reuse waypoint resolution from build script
from build_d8_d29_tracks import (  # noqa: E402
    build_segment_track,
    fill_chain,
    load_cache,
    save_cache,
    resolve_coord,
)


def path_length_km(pts):
    return sum(haversine_km(pts[i], pts[i + 1]) for i in range(len(pts) - 1)) if len(pts) > 1 else 0.0


def track_is_sane(track_km: float, planned_km: float, geo_km: float) -> bool:
    if track_km < 0.05:
        return False
    if planned_km > 0 and track_km > max(planned_km * 4, planned_km + 8):
        return False
    if geo_km < 20 and track_km > geo_km * 2.5 + 5:
        return False
    return True


def resolve_point(name: str, cache: dict, fallback: dict | None) -> dict | None:
    c = resolve_coord(name, cache)
    if c:
        return {"lat": c["lat"], "lon": c["lon"], "name": name}
    return fallback


def apply_day(day_num: int, router: OsmTrailRouter, cache: dict, known_ways: dict, prev_end: dict | None):
    path = DATA / f"D{day_num}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    segs = data.get("segments", [])

    if not segs or (len(segs) == 1 and segs[0].get("time", 0) == 0):
        print(f"D{day_num}: skip")
        return prev_end

    for k in list(data.keys()):
        if k.startswith("trackPoints"):
            del data[k]

    # Resolve all waypoints first and fill missing nodes by segment-distance interpolation.
    names = [segs[0]["from"]]
    seg_dists = []
    for s in segs:
        names.append(s["to"])
        seg_dists.append(float(s.get("distance") or 0))
    resolved = {}
    if prev_end:
        resolved[names[0]] = prev_end
    for nm in names:
        c = resolve_coord(nm, cache)
        if c:
            resolved[nm] = {"lat": c["lat"], "lon": c["lon"], "name": nm}
    fill_chain(names, seg_dists, resolved, cache)

    waypoints_out = []
    names_seen = set()
    meta_segments = []
    track_idx = 0
    stats = {"osm": 0, "fail": 0}

    def add_wp(name, coord):
        if name not in names_seen and coord:
            waypoints_out.append({"lat": coord["lat"], "lon": coord["lon"], "name": name})
            names_seen.add(name)

    for i, seg in enumerate(segs):
        f, t = seg["from"], seg["to"]
        planned = float(seg.get("distance") or 0)

        if f == t:
            print(f"  D{day_num} seg{i+1}: loop/skip {f}")
            continue

        c_from = resolved.get(f) or resolve_point(f, cache, prev_end)
        c_to = resolved.get(t) or resolve_point(t, cache, None)
        if not c_from or not c_to:
            print(f"  D{day_num} seg{i+1}: no coords {f} -> {t}")
            stats["fail"] += 1
            continue

        if i == 0:
            add_wp(f, c_from)
        add_wp(t, c_to)

        print(f"  D{day_num} seg{i+1}: routing {f} -> {t}...", flush=True)
        seg_key = f"D{day_num}:{f}:{t}"
        if seg_key in known_ways:
            pts, way_ids, method = router.route_via_way_ids(known_ways[seg_key], c_from, c_to)
        else:
            pts, way_ids, method = router.route_segment(c_from, c_to, planned)
        geo = haversine_km(c_from, c_to)
        track_km = path_length_km(pts) if pts else 0

        if pts and len(pts) >= 2 and not track_is_sane(track_km, planned, geo):
            print(
                f"  D{day_num} seg{i+1}: reject OSM ({method} {track_km:.1f}km vs plan {planned}km)",
                flush=True,
            )
            pts = []

        if not pts or len(pts) < 2:
            pts = build_segment_track(c_from, c_to, planned)
            method = "fallback-linear"
            track_km = path_length_km(pts)
            print(f"  D{day_num} seg{i+1}: linear fallback {f} -> {t}", flush=True)
            if not pts or len(pts) < 2:
                stats["fail"] += 1
                continue

        track_idx += 1
        key = f"trackPoints{track_idx}"
        data[key] = [{"lat": p["lat"], "lon": p["lon"]} for p in pts]
        stats["osm"] += 1 if method.startswith("osm") else 0
        meta_segments.append(
            {
                "trackPoints": key,
                "way_ids": sorted(set(way_ids)),
                "from": f,
                "to": t,
                "method": method,
                "track_km": round(track_km, 2),
            }
        )
        print(
            f"  D{day_num} seg{i+1}: {method} {len(pts)}pts {track_km:.1f}km "
            f"(plan {planned}km) {f} -> {t}"
        )
        prev_end = c_to

    data["waypoints"] = waypoints_out
    data.pop("trackPoints", None)
    meta = data.get("metadata") or {}
    meta["track_source"] = "OpenStreetMap hiking paths (Overpass)"
    meta["total_distance_km"] = round(sum(float(s.get("distance") or 0) for s in segs), 1)
    meta["total_time_min"] = sum(int(s.get("time") or 0) for s in segs)
    meta["segments"] = meta_segments
    data["metadata"] = meta

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"D{day_num}: {track_idx} tracks, osm={stats['osm']} fail={stats['fail']}")
    return prev_end


def load_known_ways():
    if KNOWN_WAYS_PATH.exists():
        return json.loads(KNOWN_WAYS_PATH.read_text(encoding="utf-8"))
    return {}


def main():
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    end = int(sys.argv[2]) if len(sys.argv) > 2 else 29

    cache = load_cache()
    known_ways = load_known_ways()
    router = OsmTrailRouter()
    prev = {"lat": 24.1086735, "lon": 121.3269869}

    for d in range(start, end + 1):
        print(f"\n=== D{d} ===")
        prev = apply_day(d, router, cache, known_ways, prev)
        if d % 3 == 0:
            save_cache(cache)
    save_cache(cache)
    print("\nall done")


if __name__ == "__main__":
    main()
