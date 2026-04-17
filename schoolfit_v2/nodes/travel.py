"""
Node 5 — Travel Time Computation.
Calls the OneMap routing API for each filtered school and selects the best
travel mode using travel rules (R-T01..R-T03) from the Knowledge Rule Engine.

Results are cached in a module-level dict to avoid repeat API calls within
the same server process (keyed on rounded lat/lon pairs).
"""
from __future__ import annotations

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from api_clients import get_onemap_token
from knowledge_base import RuleCategory, engine
from state import SchoolFitState

# Module-level cache: (u_lat, u_lon, s_lat, s_lon) → (mode, minutes)
_travel_cache: dict[tuple, tuple] = {}

_PT_DATE = "01-05-2026"
_PT_TIME = "06:30:00"


def _fetch_routes(u_lat: float, u_lon: float, s_lat: float, s_lon: float, token: str):
    """Call OneMap for PT and walk routes. Returns (pt_time, walk_time) in minutes."""
    headers = {"Authorization": token} if token else {}
    base_url = "https://www.onemap.gov.sg/api/public/routingsvc/route"
    pt_time = None
    walk_time = None

    # ── PT route ─────────────────────────────────────────────────────────────
    try:
        resp = requests.get(base_url, headers=headers, params={
            "start": f"{u_lat},{u_lon}",
            "end": f"{s_lat},{s_lon}",
            "routeType": "pt",
            "date": _PT_DATE,
            "time": _PT_TIME,
            "mode": "TRANSIT",
            "maxWalkDistance": "1000",
            "numItineraries": "3",
        }, timeout=6).json()

        if "plan" in resp and resp["plan"].get("itineraries"):
            best = min(resp["plan"]["itineraries"], key=lambda x: x.get("duration", float("inf")))
            pt_time = best.get("duration", 0) / 60
    except Exception:
        pass

    # ── Walk route ────────────────────────────────────────────────────────────
    try:
        resp = requests.get(base_url, headers=headers, params={
            "start": f"{u_lat},{u_lon}",
            "end": f"{s_lat},{s_lon}",
            "routeType": "walk",
        }, timeout=6).json()

        if "route_summary" in resp:
            walk_time = resp["route_summary"].get("total_time", 0) / 60
    except Exception:
        pass

    return pt_time, walk_time


def _get_travel(u_lat: float, u_lon: float, s_lat: float, s_lon: float, token: str) -> tuple:
    """Cached wrapper around _fetch_routes + travel rule selection."""
    key = (round(u_lat, 5), round(u_lon, 5), round(s_lat, 5), round(s_lon, 5))
    if key in _travel_cache:
        return _travel_cache[key]

    pt_time, walk_time = _fetch_routes(u_lat, u_lon, s_lat, s_lon, token)
    ctx = {"pt_time": pt_time, "walk_time": walk_time}
    result, _traces = engine.run_first_match(RuleCategory.TRAVEL, ctx)

    if result is None:
        result = (None, None)

    _travel_cache[key] = result
    return result


# =============================================================================
# Node function
# =============================================================================

def compute_travel_time_node(state: SchoolFitState) -> dict:
    coords = state["coordinates"]
    filtered = state["filtered_schools"]

    if coords is None or filtered is None or filtered.empty:
        return {"schools_with_travel": filtered}

    u_lat, u_lon = coords[2], coords[3]
    token = get_onemap_token()

    df = filtered.copy()
    indices = list(df.index)
    rows = {i: (float(df.loc[i, "lat"]), float(df.loc[i, "long"])) for i in indices}

    results: dict[int, tuple] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(_get_travel, u_lat, u_lon, s_lat, s_lon, token): idx
            for idx, (s_lat, s_lon) in rows.items()
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
            except Exception:
                results[idx] = (None, None)

    df["travel_mode"] = [results[i][0] for i in indices]
    df["travel_time"] = [results[i][1] for i in indices]

    return {"schools_with_travel": df}
