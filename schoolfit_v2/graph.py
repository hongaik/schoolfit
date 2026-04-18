"""
LangGraph pipeline for SchoolFit v2.
Defines the 8-node state machine and its conditional edges.
The compiled graph is exposed as `pipeline` — call pipeline.invoke(initial_state).
"""
from __future__ import annotations

import time
from langgraph.graph import END, StateGraph

from nodes.extractor import extract_intent_node
from nodes.filter import filter_schools_node
from nodes.matcher import derive_matches_node
from nodes.phases import compute_phases_node
from nodes.scorer import score_rank_node
from nodes.summarizer import generate_summary_node
from nodes.travel import compute_travel_time_node
from nodes.validator import validate_geocode_node
from state import SchoolFitState


def _logged(name: str, fn):
    """Wrap a node function with start/done terminal logging."""
    def wrapper(state):
        print(f"[SchoolFit] ▶ {name} ...", flush=True)
        t0 = time.time()
        result = fn(state)
        print(f"[SchoolFit] ✓ {name} done ({time.time()-t0:.1f}s)", flush=True)
        return result
    return wrapper


# =============================================================================
# Routing functions (conditional edges)
# =============================================================================

def _route_after_extraction(state: SchoolFitState) -> str:
    return END if state.get("error") else "validate_geocode"


def _route_after_validation(state: SchoolFitState) -> str:
    return END if state.get("error") else "derive_matches"


def _route_after_filter(state: SchoolFitState) -> str:
    filtered = state.get("filtered_schools")
    empty = filtered is None or len(filtered) == 0

    if not empty:
        return "compute_travel_time"
    # retry_count was incremented by the filter node
    if state.get("retry_count", 0) < 2:
        return "filter_schools"   # loop back with relaxed radius
    return END


# =============================================================================
# Graph construction
# =============================================================================

def _build_pipeline():
    wf = StateGraph(SchoolFitState)

    # ── Register nodes ────────────────────────────────────────────────────────
    wf.add_node("extract_intent",      _logged("extract_intent",      extract_intent_node))
    wf.add_node("validate_geocode",    _logged("validate_geocode",    validate_geocode_node))
    wf.add_node("derive_matches",      _logged("derive_matches",      derive_matches_node))
    wf.add_node("filter_schools",      _logged("filter_schools",      filter_schools_node))
    wf.add_node("compute_travel_time", _logged("compute_travel_time", compute_travel_time_node))
    wf.add_node("score_rank",          _logged("score_rank",          score_rank_node))
    wf.add_node("compute_phases",      _logged("compute_phases",      compute_phases_node))
    wf.add_node("generate_summary",    _logged("generate_summary",    generate_summary_node))

    # ── Edges ─────────────────────────────────────────────────────────────────
    wf.set_entry_point("extract_intent")

    wf.add_conditional_edges(
        "extract_intent",
        _route_after_extraction,
        {END: END, "validate_geocode": "validate_geocode"},
    )
    wf.add_conditional_edges(
        "validate_geocode",
        _route_after_validation,
        {END: END, "derive_matches": "derive_matches"},
    )
    wf.add_edge("derive_matches", "filter_schools")
    wf.add_conditional_edges(
        "filter_schools",
        _route_after_filter,
        {
            END: END,
            "filter_schools": "filter_schools",
            "compute_travel_time": "compute_travel_time",
        },
    )
    wf.add_edge("compute_travel_time", "score_rank")
    wf.add_edge("score_rank",          "compute_phases")
    wf.add_edge("compute_phases",      "generate_summary")
    wf.add_edge("generate_summary",    END)

    return wf.compile()


# Compiled once at import time — reused across all Streamlit interactions.
pipeline = _build_pipeline()


# =============================================================================
# Initial state factory
# =============================================================================

def make_initial_state(form_data: dict, prebuilt_intent=None) -> dict:
    """Return a fresh state dict for a new pipeline invocation from form data.

    Pass prebuilt_intent to skip the LLM extraction step in Node 1
    (avoids a redundant API call when the app already validated the form).
    """
    cca_score_map = form_data.get("cca_score_map", {})
    prog_score_map = form_data.get("prog_score_map", {})
    cca_selections = form_data.get("cca_selections", [])
    prog_selections = form_data.get("prog_selections", [])
    return {
        "form_data": form_data,
        "user_intent": prebuilt_intent,
        "coordinates": None,
        "cca_matches": list(cca_selections),
        "prog_matches": list(prog_selections),
        "cca_match_scores": [cca_score_map.get(n, 1.0) for n in cca_selections],
        "prog_match_scores": [prog_score_map.get(n, 1.0) for n in prog_selections],
        "sports_matches": [],
        "arts_matches": [],
        "filtered_schools": None,
        "schools_with_travel": None,
        "top_schools": None,
        "schools_with_phases": None,
        "rule_traces": [],
        "filter_exclusion_log": {},
        "summary": "",
        "error": None,
        "retry_count": 0,
    }
