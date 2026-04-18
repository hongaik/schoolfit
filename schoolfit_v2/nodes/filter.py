"""
Node 4 — School Filtering.
Applies hard filter rules (R-F01, R-F02) from the Knowledge Rule Engine
to reduce the school set to gender-compatible and distance-eligible schools.

On empty results, increments retry_count (the LangGraph conditional edge
will re-invoke this node with a relaxed radius).
"""
from __future__ import annotations

import math

import pandas as pd

from data_loader import load_master
from knowledge_base import RuleCategory, engine
from state import SchoolFitState


def _svY21_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Euclidean distance between two SVY21 points, converted to km."""
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2) / 1000.0


def filter_schools_node(state: SchoolFitState) -> dict:
    intent = state["user_intent"]
    coords = state["coordinates"]
    retry = state.get("retry_count", 0)

    if intent is None or coords is None:
        return {"error": "Missing intent or coordinates — cannot filter schools."}

    user_x, user_y, _lat, _lon = coords
    # Cap so retries cannot expand into an island-wide search (intent is already clamped in UserIntent).
    effective_radius = min(intent.radius_km * (1.5 ** retry), 12.0)

    master = load_master().copy()
    master["dist_to_user"] = master.apply(
        lambda row: _svY21_distance(user_x, user_y, row["X"], row["Y"]), axis=1
    )

    traces = list(state.get("rule_traces", []))
    passing_rows = []

    # Track exclusions: cumulative per stage, not overlapping
    # Step 1: Schools that fail R-F01
    # Step 2: Schools that fail R-F01 OR R-F02 (cumulative)
    # Step 3: Schools that fail R-F01 OR R-F02 OR R-F03 (cumulative)
    exclusion_log: dict[str, list] = {
        "R-F01": [],
        "R-F02": [],
        "R-F03": [],
    }

    # Track cumulative exclusions (schools that failed at this stage or earlier)
    cumulative_excluded = set()

    for _, row in master.iterrows():
        school_name = row["school_name"]
        nature_code = row["nature_code"]
        ctx = {
            "school_name": school_name,
            "nature_code": nature_code,
            "dist_to_user": row["dist_to_user"],
            "gender": intent.gender,
            "radius_km": effective_radius,
            "prefer_same_gender_school": intent.prefer_same_gender_school,
        }
        results, row_traces = engine.run_all(RuleCategory.FILTER, ctx)
        traces.extend(row_traces)

        # Determine at which stage this school was excluded (if any)
        excluded_at = None
        for trace in row_traces:
            if not trace.fired:
                # First rule that failed for this school determines its exclusion stage
                if excluded_at is None:
                    excluded_at = trace.rule_id
                    exclusion_log[trace.rule_id].append((school_name, trace.reason))
                    cumulative_excluded.add(school_name)
                    break  # Only record first failed rule per school

        # School passes only if ALL filter rules fired (returned non-None, i.e., True)
        # Use traces to check, since engine.run_all() filters out None outputs
        if all(trace.fired for trace in row_traces):
            passing_rows.append(row)

    filtered = pd.DataFrame(passing_rows).reset_index(drop=True) if passing_rows else pd.DataFrame()

    update: dict = {
        "filtered_schools": filtered,
        "rule_traces": traces,
        "filter_exclusion_log": exclusion_log,
    }
    if len(filtered) == 0:
        update["retry_count"] = retry + 1
    return update
