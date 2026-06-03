#!/usr/bin/env python3
"""Refine D20, D21, D29 by rebuilding continuous split tracks."""
import json
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "data"
sys.path.insert(0, str(ROOT / "scripts"))
from osm_trail_router import haversine_km  # noqa: E402


def path_km(pts):
    return sum(haversine_km(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def densify(points, max_step_km=0.04):
    if len(points) < 2:
        return points
    out = [points[0]]
    for i in range(len(points) - 1):
        a, b = points[i], points[i + 1]
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


def point_at_distance(pts, target_km):
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
    return densify(out, max_step_km=0.04)


def rebuild_day(day, corridor):
    path = DATA / f"D{day}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    segs = data.get("segments", [])
    if not segs:
        return

    poly = densify(corridor, max_step_km=0.04)
    total_track = path_km(poly)
    non_loop_plan = sum(float(s.get("distance") or 0.0) for s in segs if s.get("from") != s.get("to"))
    if total_track <= 0 or non_loop_plan <= 0:
        return

    for k in list(data.keys()):
        if k.startswith("trackPoints"):
            del data[k]

    # Build waypoints and segment boundaries in planned-distance proportion.
    waypoints = []
    seen = set()
    meta_segments = []
    track_idx = 0
    cursor_plan = 0.0

    def add_wp(name, km_pos):
        if name in seen:
            return
        p, _ = point_at_distance(poly, km_pos)
        waypoints.append({"name": name, "lat": p["lat"], "lon": p["lon"]})
        seen.add(name)

    # first waypoint
    add_wp(segs[0]["from"], 0.0)
    km_cursor = 0.0
    for seg in segs:
        f, t = seg["from"], seg["to"]
        planned = float(seg.get("distance") or 0.0)
        if f == t:
            add_wp(t, km_cursor)
            continue

        seg_km = total_track * (planned / non_loop_plan)
        start_km = km_cursor
        end_km = min(total_track, km_cursor + seg_km)
        pts = subpath_between(poly, start_km, end_km)
        if len(pts) < 2:
            km_cursor = end_km
            add_wp(t, km_cursor)
            continue
        track_idx += 1
        key = f"trackPoints{track_idx}"
        data[key] = pts
        meta_segments.append(
            {
                "trackPoints": key,
                "way_ids": [],
                "from": f,
                "to": t,
                "method": "manual-refine-split",
                "track_km": round(path_km(pts), 2),
            }
        )
        km_cursor = end_km
        add_wp(t, km_cursor)
        cursor_plan += planned

    data["waypoints"] = waypoints
    md = data.get("metadata") or {}
    md["track_source"] = "Manual refined corridor split"
    md["total_distance_km"] = round(sum(float(s.get("distance") or 0) for s in segs), 1)
    md["total_time_min"] = sum(int(s.get("time") or 0) for s in segs)
    md["segments"] = meta_segments
    data["metadata"] = md
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"D{day}: rebuilt {track_idx} tracks, corridor {total_track:.2f}km")


def main():
    # D20: 嘆息灣 -> 馬博拉斯山屋 (use a corrected local corridor near south section)
    rebuild_day(
        20,
        [
            {"lat": 23.5540, "lon": 121.1460},  # 嘆息灣 (refined near D18 end)
            {"lat": 23.5380, "lon": 121.1250},
            {"lat": 23.5250, "lon": 121.1050},
            {"lat": 23.5120, "lon": 121.0920},
            {"lat": 23.5000, "lon": 121.1200},  # 馬博拉斯山屋 (refined anchor)
        ],
    )

    # D21: 馬博拉斯山屋 -> 大水窟山屋
    rebuild_day(
        21,
        [
            {"lat": 23.5000, "lon": 121.1200},  # 馬博拉斯山屋 (same as D20 end)
            {"lat": 23.4910, "lon": 121.1050},
            {"lat": 23.4830, "lon": 121.0880},
            {"lat": 23.4760, "lon": 121.0640},
            {"lat": 23.4690, "lon": 121.0400},
            {"lat": 23.4580, "lon": 121.0180},  # 大水窟山屋
        ],
    )

    # D29: 三叉峰下營地 -> 石山林道登山口7K (fix outlier branch coordinates)
    rebuild_day(
        29,
        [
            {"lat": 23.1180, "lon": 121.0450},  # D28 end
            {"lat": 23.1140, "lon": 121.0200},
            {"lat": 23.1100, "lon": 120.9980},
            {"lat": 23.1060, "lon": 120.9860},
            {"lat": 23.1000, "lon": 120.9800},  # 石山林道登山口 7K
        ],
    )


if __name__ == "__main__":
    main()
