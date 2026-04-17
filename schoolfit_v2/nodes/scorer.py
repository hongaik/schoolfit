"""
Node 6 — Fit Scoring & Ranking.
Applies all 11 scoring dimension specs (R-S01..R-S11) from scoring_rules.py,
normalises per-dimension using the correct strategy (R-S12), computes the
weighted dot product (R-S13), and returns the top-N ranked schools.
Ballot history is merged for display ONLY — it does not affect scoring.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from data_loader import load_ballot_history
from knowledge_base.rules.scoring_rules import SCORE_DIMENSIONS, FINAL_SCORE_RULE_ID, WEIGHT_NORM_RULE_ID
from knowledge_base.rule_engine import RuleTrace
from state import SchoolFitState


def score_rank_node(state: SchoolFitState) -> dict:
    intent = state["user_intent"]
    df = state.get("schools_with_travel")

    if intent is None or df is None or df.empty:
        return {"top_schools": pd.DataFrame()}

    df = df.copy()
    traces = list(state.get("rule_traces", []))

    # Build shared scoring context (same for all schools in this batch)
    scoring_ctx = {
        "cca_matches": state.get("cca_matches", []),
        "prog_matches": state.get("prog_matches", []),
        "sports_matches": state.get("sports_matches", []),
        "arts_matches": state.get("arts_matches", []),
        "gender": intent.gender,
        "user_session": intent.session,
        "user_sap": intent.sap,
        "user_autonomous": intent.autonomous,
        "user_ip": intent.ip,
        "user_mt": intent.mother_tongue,
    }

    # ── Collect raw values per dimension ──────────────────────────────────────
    raw_cols: dict[str, str] = {}   # dim.rule_id → df column name for raw value

    for dim in SCORE_DIMENSIONS:
        col = f"_raw_{dim.rule_id}"
        raw_cols[dim.rule_id] = col

        if dim.normalisation == "binary":
            df[col] = df.apply(lambda row: dim.binary_fn(row, scoring_ctx), axis=1)
        else:
            df[col] = df.apply(lambda row: dim.raw_fn(row, scoring_ctx), axis=1)

    # ── Normalise & compute per-dimension score ───────────────────────────────
    score_cols: list[str] = []

    for dim in SCORE_DIMENSIONS:
        raw_col = raw_cols[dim.rule_id]
        score_col = f"score_{dim.rule_id}"
        score_cols.append(score_col)

        if dim.normalisation == "minmax":
            raw_vals = df[[raw_col]].fillna(0).values.astype(float)
            if raw_vals.max() > raw_vals.min():
                normed = MinMaxScaler().fit_transform(raw_vals).flatten()
            else:
                normed = np.zeros(len(df))
            df[score_col] = (1 - normed) if dim.invert else normed

        elif dim.normalisation == "ordinal":
            df[score_col] = df[raw_col].map(dim.ordinal_map).fillna(0).astype(float)

        else:  # binary
            df[score_col] = df[raw_col].astype(float)

        # Add a trace per dimension (R-S12 logic)
        traces.append(RuleTrace(
            rule_id=dim.rule_id,
            category="scoring",
            fired=True,
            output=dim.name,
            school_name="(all)",
            reason=dim.description,
        ))

    # ── R-S12: Normalise weights ──────────────────────────────────────────────
    raw_weights = np.array([getattr(intent, dim.weight_attr) for dim in SCORE_DIMENSIONS], dtype=float)
    weight_sum = raw_weights.sum()
    norm_weights = raw_weights / weight_sum if weight_sum > 0 else raw_weights

    traces.append(RuleTrace(
        rule_id=WEIGHT_NORM_RULE_ID,
        category="scoring",
        fired=True,
        output=norm_weights.tolist(),
        school_name="(all)",
        reason="Weights normalised to sum to 1 before computing dot product.",
    ))

    # ── R-S13: Final fit score ────────────────────────────────────────────────
    score_matrix = df[score_cols].values
    df["score_total"] = (100 * score_matrix.dot(norm_weights)).round(1)

    traces.append(RuleTrace(
        rule_id=FINAL_SCORE_RULE_ID,
        category="scoring",
        fired=True,
        output="score_total",
        school_name="(all)",
        reason="Fit score = 100 × Σ(norm_weight_i × score_i) for all dimensions where weight_i > 0.",
    ))

    # ── Rank and select top N ─────────────────────────────────────────────────
    top_n = int(intent.top_n) if intent.top_n else 5
    top = df.sort_values("score_total", ascending=False).head(top_n).reset_index(drop=True)

    # ── Merge ballot history (display-only — does NOT affect score) ───────────
    ballot = load_ballot_history()
    top = top.merge(ballot, how="left", on="school_name")

    # Store score dimensions metadata for use in the display layer
    top.attrs["score_dimensions"] = SCORE_DIMENSIONS
    top.attrs["norm_weights"] = dict(zip([d.rule_id for d in SCORE_DIMENSIONS], norm_weights))

    return {"top_schools": top, "rule_traces": traces}
