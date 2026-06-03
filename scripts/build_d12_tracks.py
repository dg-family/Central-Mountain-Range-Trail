#!/usr/bin/env python3
"""Rebuild D12 map tracks from corrected GPX-aligned waypoints."""
import json
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "data"
sys.path.insert(0, str(ROOT / "scripts"))
from osm_trail_router import haversine_km  # noqa: E402

D12_PATH = DATA / "D12.json"
GEO_CACHE = DATA / "geocode_cache.json"
OSM_CACHE_DIR = DATA / "osm_bbox_cache"
MAIN_WAY_ID = 410981216
GRASS_BRANCH_WAY_ID = 585194004

FIXED = {
    "凹谷避風營地": {"lat": 23.8232750, "lon": 121.2366500},
    "草山岔路口": {"lat": 23.8220285, "lon": 121.2375703},  # moved to corrected junction point
    "草山 2811M": {"lat": 23.8211750, "lon": 121.2401100},
    "凹谷水池平坦大營地": {"lat": 23.8160670, "lon": 121.2351760},
    "漂亮石陣": {"lat": 23.8028680, "lon": 121.2263100},
    "卡社大山前漂亮白木林": {"lat": 23.7854770, "lon": 121.2280960},
    "卡社(北丹)大山 2947M": {"lat": 23.7818360, "lon": 121.2208000},
    "卡社池優美谷地": {"lat": 23.7791020, "lon": 121.2168800},
    "台電豪華工寮": {"lat": 23.7691250, "lon": 121.2075100},
}

SEG_TEMPLATE = [
    ("凹谷避風營地", "草山岔路口", 0.19, 15, "凹谷避風營地 → 途經最後的摩即關卡 → 草山岔路口"),
    ("草山岔路口", "草山 2811M", 0.30, 25, "草山岔路口 → 草山 2811M"),
    ("草山 2811M", "草山岔路口", 0.30, 25, "草山 2811M → 草山岔路口"),
    ("草山岔路口", "凹谷水池平坦大營地", 0.79, 65, "草山岔路口 → 凹谷水池平坦大營地"),
    ("凹谷水池平坦大營地", "漂亮石陣", 1.95, 155, "凹谷水池平坦大營地 → 途經2675峰、超大營地 → 漂亮石陣"),
    ("漂亮石陣", "卡社大山前漂亮白木林", 2.20, 175, "漂亮石陣 → 卡社大山前漂亮白木林"),
    ("卡社大山前漂亮白木林", "卡社(北丹)大山 2947M", 0.96, 75, "卡社大山前漂亮白木林 → 卡社(北丹)大山 2947M"),
    ("卡社(北丹)大山 2947M", "卡社池優美谷地", 0.96, 75, "卡社(北丹)大山 2947M → 卡社池優美谷地"),
    ("卡社池優美谷地", "台電豪華工寮", 2.13, 170, "卡社池優美谷地 → 台電豪華工寮(補給點)"),
]


def path_km(pts):
    return sum(haversine_km(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def linear(a, b, steps=16):
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
    # If endpoint too far from selected way, caller should fallback.
    if max(da, db) > 0.25:
        return []
    return out


def main():
    data = json.loads(D12_PATH.read_text(encoding="utf-8"))
    segs = [{"from": f, "to": t, "distance": d, "time": m, "description": desc} for f, t, d, m, desc in SEG_TEMPLATE]
    data["segments"] = segs
    way_geos = load_way_geometries([MAIN_WAY_ID, GRASS_BRANCH_WAY_ID])
    if MAIN_WAY_ID not in way_geos or GRASS_BRANCH_WAY_ID not in way_geos:
        raise SystemExit("missing cached OSM way geometry for D12 rebuild")

    for k in list(data.keys()):
        if k.startswith("trackPoints"):
            del data[k]

    names = [segs[0]["from"]] + [s["to"] for s in segs]
    for n in names:
        if n not in FIXED:
            raise SystemExit(f"missing FIXED waypoint: {n}")

    meta = []
    for i, seg in enumerate(segs, 1):
        a = FIXED[seg["from"]]
        b = FIXED[seg["to"]]
        if (
            seg["from"] in ("草山岔路口", "草山 2811M")
            and seg["to"] in ("草山岔路口", "草山 2811M")
        ):
            wid = GRASS_BRANCH_WAY_ID
        else:
            wid = MAIN_WAY_ID
        pts = subpath_from_way(way_geos[wid], a, b)
        method = "osm-way-cache-slice"
        wids = [wid]
        if len(pts) < 2:
            pts = linear(a, b, 24)
            method = "fallback-linear"
            wids = []
        pts = densify(pts, 0.04)
        key = f"trackPoints{i}"
        data[key] = pts
        meta.append(
            {
                "trackPoints": key,
                "way_ids": wids,
                "from": seg["from"],
                "to": seg["to"],
                "method": method,
                "track_km": round(path_km(pts), 2),
            }
        )

    waypoints = []
    seen = set()
    for n in names:
        if n in FIXED and n not in seen:
            waypoints.append({"name": n, "lat": FIXED[n]["lat"], "lon": FIXED[n]["lon"]})
            seen.add(n)
    data["waypoints"] = waypoints
    data["metadata"] = {
        "track_source": "OpenStreetMap hiking paths (D12 way-cache slices)",
        "total_distance_km": round(sum(float(s.get("distance") or 0) for s in segs), 1),
        "total_time_min": sum(int(s.get("time") or 0) for s in segs),
        "segments": meta,
    }
    D12_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cache = json.loads(GEO_CACHE.read_text(encoding="utf-8"))
    cache.pop("草山下大黑水塘", None)
    for n, p in FIXED.items():
        source = "osm-way-junction" if n == "草山岔路口" else "gpx-exact"
        cache[n] = {"lat": p["lat"], "lon": p["lon"], "source": source}
    GEO_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"D12 rebuilt: {len(segs)} segments")


if __name__ == "__main__":
    main()
