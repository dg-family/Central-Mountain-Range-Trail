#!/usr/bin/env python3
"""Route between points on OpenStreetMap hiking path network (Overpass)."""
from __future__ import annotations

import hashlib
import heapq
import json
import math
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "assets" / "data" / "osm_bbox_cache"
WAY_CACHE = ROOT / "assets" / "data" / "osm_way_cache"
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
UA = "CentralMountainTrail/2.0"


def haversine_km(a: Dict, b: Dict) -> float:
    r = 6371.0
    lat1, lon1 = math.radians(a["lat"]), math.radians(a["lon"])
    lat2, lon2 = math.radians(b["lat"]), math.radians(b["lon"])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    x = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(x), math.sqrt(1 - x))


def node_key(p: Dict, prec: int = 5) -> Tuple[float, float]:
    return (round(p["lat"], prec), round(p["lon"], prec))


class OsmTrailRouter:
    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._mem: Dict[str, Tuple] = {}
        self._ep = 0

    def _bbox_key(self, s: float, w: float, n: float, e: float) -> str:
        return f"{s:.3f}_{w:.3f}_{n:.3f}_{e:.3f}"

    def _cache_path(self, key: str) -> Path:
        h = hashlib.sha1(key.encode()).hexdigest()[:16]
        return self.cache_dir / f"{h}.json"

    def fetch_way(self, way_id: int) -> List[dict]:
        WAY_CACHE.mkdir(parents=True, exist_ok=True)
        cp = WAY_CACHE / f"{way_id}.json"
        if cp.exists():
            return json.loads(cp.read_text(encoding="utf-8"))
        # OSM API 0.6（單一 way 較穩定）
        try:
            api_url = f"https://api.openstreetmap.org/api/0.6/way/{way_id}/full/json"
            req = urllib.request.Request(api_url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            nodes = {e["id"]: (e["lat"], e["lon"]) for e in data.get("elements", []) if e["type"] == "node"}
            for el in data.get("elements", []):
                if el["type"] == "way" and el["id"] == way_id:
                    pts = [{"lat": nodes[nid][0], "lon": nodes[nid][1]} for nid in el.get("nodes", []) if nid in nodes]
                    if len(pts) >= 2:
                        cp.write_text(json.dumps(pts), encoding="utf-8")
                        time.sleep(1.0)
                        return pts
        except Exception as exc:
            print(f"    osm api way {way_id}: {exc}", flush=True)
        query = f"[out:json][timeout:60];way({way_id});out geom;"
        for attempt in range(5):
            url = OVERPASS_ENDPOINTS[self._ep % len(OVERPASS_ENDPOINTS)]
            self._ep += 1
            try:
                req = urllib.request.Request(
                    url,
                    data=urllib.parse.urlencode({"data": query}).encode(),
                    headers={"User-Agent": UA},
                )
                with urllib.request.urlopen(req, timeout=90) as resp:
                    data = json.loads(resp.read())
                for el in data.get("elements", []):
                    if el.get("type") == "way" and el.get("geometry"):
                        pts = [{"lat": p["lat"], "lon": p["lon"]} for p in el["geometry"]]
                        cp.write_text(json.dumps(pts), encoding="utf-8")
                        time.sleep(2.0)
                        return pts
            except Exception as exc:
                print(f"    way {way_id} retry: {exc}", flush=True)
                time.sleep(4 * (attempt + 1))
        return []

    def route_via_way_ids(self, way_ids: List[int], a: Dict, b: Dict) -> Tuple[List[dict], List[int], str]:
        merged: List[dict] = []
        used: List[int] = []
        for wid in way_ids:
            geom = self.fetch_way(wid)
            if not geom:
                continue
            if merged and haversine_km(merged[-1], geom[0]) < 0.001:
                geom = geom[1:]
            merged.extend(geom)
            used.append(wid)
        if len(merged) >= 2:
            trimmed = self.subpath_on_way(merged, a, b)
            if trimmed and len(trimmed) >= 2:
                return trimmed, used, "osm-known-ways"
        return [], [], "failed"

    def fetch_ways(self, south: float, west: float, north: float, east: float) -> List[dict]:
        key = self._bbox_key(south, west, north, east)
        if key in self._mem:
            return self._mem[key][0]

        cp = self._cache_path(key)
        if cp.exists():
            elements = json.loads(cp.read_text(encoding="utf-8"))
            self._mem[key] = (elements,)
            return elements

        query = f"""
        [out:json][timeout:90];
        (
          way["highway"~"path|footway|track|steps"]({south},{west},{north},{east});
          way["route"="hiking"]({south},{west},{north},{east});
        );
        out geom;
        """
        for attempt in range(6):
            url = OVERPASS_ENDPOINTS[self._ep % len(OVERPASS_ENDPOINTS)]
            self._ep += 1
            try:
                req = urllib.request.Request(
                    url,
                    data=urllib.parse.urlencode({"data": query}).encode(),
                    headers={"User-Agent": UA},
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read())
                elements = [e for e in data.get("elements", []) if e.get("type") == "way" and e.get("geometry")]
                cp.write_text(json.dumps(elements), encoding="utf-8")
                self._mem[key] = (elements,)
                time.sleep(2.5)
                return elements
            except Exception as exc:
                wait = 5 * (attempt + 1)
                print(f"    overpass retry {attempt + 1} ({url}): {exc}", flush=True)
                time.sleep(wait)
        return []

    def build_graph(self, elements: List[dict]):
        adj: Dict = defaultdict(list)
        nodes: Dict = {}
        edge_ways: Dict = {}

        for el in elements:
            wid = el["id"]
            geom = el["geometry"]
            for i in range(len(geom) - 1):
                p1, p2 = geom[i], geom[i + 1]
                n1, n2 = node_key(p1), node_key(p2)
                nodes[n1] = {"lat": p1["lat"], "lon": p1["lon"]}
                nodes[n2] = {"lat": p2["lat"], "lon": p2["lon"]}
                w = haversine_km(p1, p2)
                adj[n1].append((n2, w, wid))
                adj[n2].append((n1, w, wid))
                edge_ways[(n1, n2)] = wid
                edge_ways[(n2, n1)] = wid
        return adj, nodes, edge_ways

    def nearest_node(self, nodes: Dict, pt: Dict, max_km: float) -> Tuple[Optional[Tuple], float]:
        best, best_d = None, 1e9
        for nid, p in nodes.items():
            d = haversine_km(pt, p)
            if d < best_d:
                best_d, best = d, nid
        if best_d > max_km:
            return None, best_d
        return best, best_d

    def dijkstra(
        self, adj: Dict, start: Tuple, end: Tuple
    ) -> Tuple[Optional[List[Tuple]], Optional[List[int]]]:
        pq = [(0.0, start)]
        dist = {start: 0.0}
        prev: Dict = {}
        prev_way: Dict = {}

        while pq:
            d, u = heapq.heappop(pq)
            if u == end:
                path = []
                ways = []
                cur = end
                while cur in prev:
                    path.append(cur)
                    ways.append(prev_way[cur])
                    cur = prev[cur]
                path.append(start)
                path.reverse()
                ways.reverse()
                return path, ways
            if d > dist.get(u, 1e18):
                continue
            for v, w, wid in adj[u]:
                nd = d + w
                if nd < dist.get(v, 1e18):
                    dist[v] = nd
                    prev[v] = u
                    prev_way[v] = wid
                    heapq.heappush(pq, (nd, v))
        return None, None

    def subpath_on_way(self, geom: List[dict], a: Dict, b: Dict) -> Optional[List[dict]]:
        if len(geom) < 2:
            return None
        best_i, best_da = 0, 1e9
        best_j, best_db = 0, 1e9
        for i, p in enumerate(geom):
            da = haversine_km(a, p)
            db = haversine_km(b, p)
            if da < best_da:
                best_da, best_i = da, i
            if db < best_db:
                best_db, best_j = db, i
        if best_da > 3.5 or best_db > 3.5:
            return None
        if best_i <= best_j:
            sub = geom[best_i : best_j + 1]
        else:
            sub = list(reversed(geom[best_j : best_i + 1]))
        return [{"lat": p["lat"], "lon": p["lon"]} for p in sub]

    def try_single_way(self, elements: List[dict], a: Dict, b: Dict) -> Tuple[Optional[List[dict]], List[int]]:
        best = None
        best_wid = None
        best_score = 1e9
        for el in elements:
            geom = el.get("geometry") or []
            sub = self.subpath_on_way(geom, a, b)
            if not sub or len(sub) < 2:
                continue
            length = sum(haversine_km(sub[i], sub[i + 1]) for i in range(len(sub) - 1))
            da = min(haversine_km(a, p) for p in geom)
            db = min(haversine_km(b, p) for p in geom)
            score = da + db + length * 0.01
            if score < best_score:
                best_score = score
                best = sub
                best_wid = el["id"]
        if best:
            return best, [best_wid]
        return None, []

    def route_segment(
        self, a: Dict, b: Dict, planned_km: float = 0.0
    ) -> Tuple[List[dict], List[int], str]:
        geo = haversine_km(a, b)
        if geo > 12:
            merged: List[dict] = []
            all_wids: List[int] = []
            steps = min(5, max(3, int(geo / 8)))
            chain = [a]
            for i in range(1, steps):
                t = i / steps
                chain.append(
                    {
                        "lat": a["lat"] + (b["lat"] - a["lat"]) * t,
                        "lon": a["lon"] + (b["lon"] - a["lon"]) * t,
                    }
                )
            chain.append(b)
            method = "osm-chained"
            for i in range(len(chain) - 1):
                sub, wids, m = self._route_once(chain[i], chain[i + 1], planned_km / steps)
                if not sub:
                    continue
                method = m
                if merged and haversine_km(merged[-1], sub[0]) < 0.001:
                    sub = sub[1:]
                merged.extend(sub)
                all_wids.extend(wids)
            if merged:
                return merged, all_wids, method
            return [], [], "failed"

        return self._route_once(a, b, planned_km)

    def _route_once(
        self, a: Dict, b: Dict, planned_km: float = 0.0
    ) -> Tuple[List[dict], List[int], str]:
        geo = haversine_km(a, b)
        pads = [0.04, 0.07, 0.10, 0.14, 0.20]
        if geo > 8:
            pads = [0.06, 0.10, 0.15, 0.22]
        snap_km = 2.5 if geo < 12 else 4.0

        for pad in pads:
            south = min(a["lat"], b["lat"]) - pad
            north = max(a["lat"], b["lat"]) + pad
            west = min(a["lon"], b["lon"]) - pad
            east = max(a["lon"], b["lon"]) + pad
            elements = self.fetch_ways(south, west, north, east)
            if not elements:
                continue

            single, wids = self.try_single_way(elements, a, b)
            if single and len(single) >= 2:
                return single, wids, "osm-single-way"

            adj, nodes, _ = self.build_graph(elements)
            if len(nodes) < 2:
                continue
            sa, da = self.nearest_node(nodes, a, snap_km)
            sb, db = self.nearest_node(nodes, b, snap_km)
            if not sa or not sb:
                continue
            path, ways = self.dijkstra(adj, sa, sb)
            if path and len(path) >= 2:
                pts = [nodes[n] for n in path]
                return pts, ways or [], "osm-graph"

        return [], [], "failed"
