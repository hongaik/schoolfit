"""
Node 1 — Intent Extraction from Form Data.
Builds UserIntent from form-based input (validation + LLM bonus extraction).

If the Streamlit app already built and validated the intent before invoking
the pipeline, it passes it in state["user_intent"] to skip the redundant
LLM call. This node checks for that and short-circuits accordingly.
"""
from __future__ import annotations

from input_validator import build_user_intent, get_coordinates
from state import SchoolFitState


def extract_intent_node(state: SchoolFitState) -> dict:
    """
    Node 1: Build UserIntent from form data, or reuse if already built.

    Returns dict with:
    - user_intent: UserIntent object
    - coordinates: (X, Y, lat, lon) tuple
    - error: error message if validation/geocoding failed
    """
    # ── Short-circuit if app already built the intent ─────────────────────────
    # Reuse pre-validated intent from session to avoid a second LLM call.
    existing_intent = state.get("user_intent")
    if existing_intent is not None:
        coords = get_coordinates(existing_intent.postal_code)
        if isinstance(coords, str):
            return {"error": f"Coordinate error: {coords}"}
        return {"user_intent": existing_intent, "coordinates": coords}

    # ── Cold path: build intent from scratch (e.g. direct API/test usage) ─────
    form_data = state.get("form_data")
    if not form_data:
        return {"error": "No form data provided"}

    intent, error_msg = build_user_intent(form_data)
    if error_msg:
        return {"error": error_msg}

    coords = get_coordinates(intent.postal_code)
    if isinstance(coords, str):
        return {"error": f"Coordinate error: {coords}"}

    return {"user_intent": intent, "coordinates": coords}
