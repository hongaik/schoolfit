"""
Node 2 — Geocoding & Validation.
Converts the postal code from UserIntent into (X, Y, lat, lon) coordinates
via the OneMap API. Sets state["error"] on failure so the conditional edge
can route to END.
"""
from __future__ import annotations

import requests

from api_clients import get_onemap_token
from state import SchoolFitState


def validate_geocode_node(state: SchoolFitState) -> dict:
    intent = state["user_intent"]
    if intent is None:
        return {"error": "Intent extraction failed — cannot geocode."}

    postal = str(intent.postal_code).strip().zfill(6)

    if not postal.isdigit() or len(postal) != 6:
        return {"error": f"'{postal}' is not a valid 6-digit Singapore postal code."}

    token = get_onemap_token()
    url = (
        "https://www.onemap.gov.sg/api/common/elastic/search"
        f"?searchVal={postal}&returnGeom=Y&getAddrDetails=N&pageNum=1"
    )
    headers = {"Authorization": token} if token else {}

    try:
        resp = requests.get(url, headers=headers, timeout=8)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return {"error": f"OneMap geocoding failed: {exc}"}

    if data.get("found", 0) == 0:
        return {"error": f"Postal code {postal} was not found. Please check and try again."}

    result = data["results"][0]
    coordinates = (
        float(result["X"]),
        float(result["Y"]),
        float(result["LATITUDE"]),
        float(result["LONGITUDE"]),
    )
    return {"coordinates": coordinates}
