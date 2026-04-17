"""
Node 7 — Phase Eligibility & Admission Signal.
Applies phase rules (R-P01..R-P06) and signal rules (R-A01..R-A05)
from the Knowledge Rule Engine to each top school.
Ballot history columns (already merged in scorer) provide the odds for R-A.
"""
from __future__ import annotations

import pandas as pd

from knowledge_base import RuleCategory, engine
from knowledge_base.rule_engine import RuleTrace
from state import SchoolFitState


def _get_ballot_odds(row: pd.Series, phase: str) -> float | None:
    """
    Look up the historical ballot odds column for the user's phase + suffix.
    The phase string (e.g. "Phase 2C-1") maps directly to a ballot_history column.
    """
    col = phase  # column names in ballot_history match phase strings
    val = row.get(col)
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def compute_phases_node(state: SchoolFitState) -> dict:
    intent = state["user_intent"]
    top = state.get("top_schools")

    if intent is None or top is None or top.empty:
        return {"schools_with_phases": top}

    df = top.copy()
    traces = list(state.get("rule_traces", []))

    phases: list[str] = []
    signals: list[str] = []

    for _, row in df.iterrows():
        # Build per-school phase context
        phase_ctx = {
            "school_name": row["school_name"],
            "citizenship": intent.citizenship,
            "dist_to_user": float(row.get("dist_to_user", 999)),
            "has_sibling": intent.has_sibling,
            "former_student": intent.former_student,
            "is_alumni": intent.is_alumni,
            "is_staff": intent.is_staff,
            "is_mk": intent.is_mk,
            "is_volunteer": intent.is_volunteer,
            "is_church_clan": intent.is_church_clan,
            "is_community_leader": intent.is_community_leader,
        }

        # ── Phase (R-P rules, first match) ────────────────────────────────────
        phase, phase_traces = engine.run_first_match(RuleCategory.PHASE, phase_ctx)
        if phase is None:
            phase = f"Phase 2C"
        traces.extend(phase_traces)
        phases.append(phase)

        # ── Admission signal (R-A rules, first match) ─────────────────────────
        ballot_odds = _get_ballot_odds(row, phase)
        signal_ctx = {"phase": phase, "ballot_odds": ballot_odds}
        signal, signal_traces = engine.run_first_match(RuleCategory.SIGNAL, signal_ctx)
        if signal is None:
            signal = "Unknown"
        traces.extend(signal_traces)
        signals.append(signal)

    df["phase"] = phases
    df["admission_signal"] = signals

    return {"schools_with_phases": df, "rule_traces": traces}
