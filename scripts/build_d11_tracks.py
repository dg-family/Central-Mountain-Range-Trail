#!/usr/bin/env python3
"""Rebuild D11 from 摩即三岔路口; remove H2620 west peak stop."""
import json
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "data"
sys.path.insert(0, str(ROOT / "scripts"))
from osm_trail_router import haversine_km  # noqa: E402

D11_PATH = DATA / "D11.json"
GEO_CACHE = DATA / "geocode_cache.json"
OSM_CACHE_DIR = DATA / "osm_bbox_cache"

MAIN_WAY_ID = 410981216
MOJI_BRANCH_WAY_ID = 585194003

MIT_START = {"lat": 23.8510360, "lon": 121.2469500}  # 起點 (GPX exact)
MOJI_JCT = {"lat": 23.8465060, "lon": 121.2439400}  # 摩即三岔路口 (GPX exact)
MOJI_MT = {"lat": 23.8463480, "lon": 121.2449950}  # 摩即山 (GPX exact)
MOJI_SOUTH_SADDLE = {"lat": 23.8413010, "lon": 121.2389450}  # GPX exact
P2640 = {"lat": 23.8353195, "lon": 121.2379875}  # interpolated
EXIT_BAMBOO = {"lat": 23.8293380, "lon": 121.2370300}  # GPX exact
WIND_CAMP = {"lat": 23.8232750, "lon": 121.2366500}  # GPX exact

SEG_TEMPLATE = [
    ("MIT鞍部箭竹營地", "摩即三岔路口", 0.66, 55, "MIT鞍部箭竹營地 → 摩即三岔路口"),
    ("摩即三岔路口", "摩即山", 0.12, 10, "摩即三岔路口 → 摩即山"),
    ("摩即山", "摩即三岔路口", 0.12, 10, "摩即山 → 摩即三岔路口"),
    ("摩即三岔路口", "摩即南鞍營地", 0.96, 75, "摩即三岔路口 → 摩即南鞍營地"),
    ("摩即南鞍營地", "2640峰", 0.74, 60, "摩即南鞍營地 → 2640峰"),
    ("2640峰", "走出地獄箭竹海", 0.76, 60, "2640峰 → 走出地獄箭竹海"),
    ("走出地獄箭竹海", "凹谷避風營地", 0.81, 65, "走出地獄箭竹海 → 凹谷避風營地"),
]

FIXED_WAYPOINTS = {
    "MIT鞍部箭竹營地": MIT_START,
    "摩即三岔路口": MOJI_JCT,
    "摩即山": MOJI_MT,
    "摩即山 2643M": MOJI_MT,  # alias
    "摩即南鞍營地": MOJI_SOUTH_SADDLE,
    "2640峰": P2640,
    "走出地獄箭竹海": EXIT_BAMBOO,
    "凹谷避風營地": WIND_CAMP,
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


def linear(a, b, steps=12):
    out = []
    for i in range(steps + 1):
        t = i / steps
        out.append({"lat": a["lat"] + (b["lat"] - a["lat"]) * t, "lon": a["lon"] + (b["lon"] - a["lon"]) * t})
    return out


def load_way_geometries(way_ids):
    want = set(way_ids)
    found = {}
    for fp in OSM_CACHE_DIR.glob("*.json"):
        if want == set(found.keys()):
            break
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for item in data:
            if (
                isinstance(item, dict)
                and item.get("type") == "way"
                and item.get("id") in want
                and isinstance(item.get("geometry"), list)
                and item["geometry"]
            ):
                found[item["id"]] = [{"lat": p["lat"], "lon": p["lon"]} for p in item["geometry"]]
    return found


def nearest_idx(pts, p):
    best_i = 0
    best_d = float("inf")
    for i, q in enumerate(pts):
        d = haversine_km(p, q)
        if d < best_d:
            best_d = d
            best_i = i
    return best_i, best_d


def subpath_from_way(way_pts, a, b):
    ia, da = nearest_idx(way_pts, a)
    ib, db = nearest_idx(way_pts, b)
    if ia <= ib:
        core = way_pts[ia : ib + 1]
    else:
        core = list(reversed(way_pts[ib : ia + 1]))
    out = []
    if haversine_km(a, core[0]) > 0.0002:
        out.append({"lat": a["lat"], "lon": a["lon"]})
    out.extend(core)
    if haversine_km(out[-1], b) > 0.0002:
        out.append({"lat": b["lat"], "lon": b["lon"]})
    # Guardrail: if waypoint is too far from selected way, fallback to straight split.
    if max(da, db) > 0.25:
        return []
    return out


def main():
    data = json.loads(D11_PATH.read_text(encoding="utf-8"))

    segs = [
        {"from": f, "to": t, "distance": d, "time": m, "description": desc}
        for f, t, d, m, desc in SEG_TEMPLATE
    ]
    data["segments"] = segs

    for k in list(data.keys()):
        if k.startswith("trackPoints"):
            del data[k]

    way_geos = load_way_geometries([MAIN_WAY_ID, MOJI_BRANCH_WAY_ID])
    if MAIN_WAY_ID not in way_geos or MOJI_BRANCH_WAY_ID not in way_geos:
        raise SystemExit("missing cached OSM way geometry for D11 rebuild")
    meta_segments = []
    for i, seg in enumerate(segs, 1):
        a = FIXED_WAYPOINTS[seg["from"]]
        b = FIXED_WAYPOINTS[seg["to"]]
        if "摩即山" in (seg["from"], seg["to"]):
            wid = MOJI_BRANCH_WAY_ID
            pts = subpath_from_way(way_geos[MOJI_BRANCH_WAY_ID], a, b)
            method = "osm-way-cache-slice"
            wids = [wid]
        else:
            wid = MAIN_WAY_ID
            pts = subpath_from_way(way_geos[MAIN_WAY_ID], a, b)
            method = "osm-way-cache-slice"
            wids = [wid]
        if len(pts) < 2:
            # Keep route generation robust even if Overpass is unstable.
            pts = linear(a, b, 24)
            method = "fallback-linear"
            wids = []
        pts = densify(pts, 0.04)
        data[f"trackPoints{i}"] = pts
        meta_segments.append(
            {
                "trackPoints": f"trackPoints{i}",
                "way_ids": sorted(set(wids or [])),
                "from": seg["from"],
                "to": seg["to"],
                "method": method,
                "track_km": round(path_km(pts), 2),
            }
        )

    names = [segs[0]["from"]] + [s["to"] for s in segs]
    waypoints = []
    seen = set()
    for name in names:
        if name in seen:
            continue
        p = FIXED_WAYPOINTS[name]
        waypoints.append({"name": name, "lat": p["lat"], "lon": p["lon"]})
        seen.add(name)
    data["waypoints"] = waypoints

    data["metadata"] = {
        "track_source": "OpenStreetMap hiking paths (D11 from Moji junction)",
        "total_distance_km": round(sum(float(s["distance"]) for s in segs), 1),
        "total_time_min": sum(int(s["time"]) for s in segs),
        "segments": meta_segments,
    }
    D11_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cache = json.loads(GEO_CACHE.read_text(encoding="utf-8"))
    for wp in waypoints:
        cache[wp["name"]] = {"lat": wp["lat"], "lon": wp["lon"], "source": "d11-moji-start"}
    GEO_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"D11 rebuilt: {len(segs)} segs, total {data['metadata']['total_distance_km']}km")


if __name__ == "__main__":
    main()
