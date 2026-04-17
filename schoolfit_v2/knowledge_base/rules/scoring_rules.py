"""
Scoring Dimension Specifications (R-S01..R-S13).

Rather than per-school rule functions (which can't do cross-school MinMaxNorm),
this module defines ScoreDimension specs — declarative descriptors that tell
the scorer node (nodes/scorer.py) HOW to compute each dimension.

The scorer node iterates over SCORE_DIMENSIONS, extracts raw values per school,
applies the correct normalisation strategy, then computes the weighted sum.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class ScoreDimension:
    """Declarative specification for one fit-score dimension."""
    rule_id: str                # R-S01 .. R-S13
    name: str                   # human-readable label
    weight_attr: str            # attribute name on UserIntent, e.g. "w_dist"
    normalisation: str          # "minmax" | "ordinal" | "binary"
    invert: bool = False        # True → score = 1 − MinMaxNorm(raw)
    # For "minmax" dims: function (row, ctx) → float raw value
    raw_fn: Optional[Callable] = None
    # For "ordinal" dims: mapping from raw string/int → 0-1 float
    ordinal_map: dict = field(default_factory=dict)
    # For "binary" dims: function (row, ctx) → 0 or 1
    binary_fn: Optional[Callable] = None
    description: str = ""


# =============================================================================
# Dimension specifications — mirrors RFC §5 Rule Catalogue R-S01..R-S13
# =============================================================================

SCORE_DIMENSIONS: list[ScoreDimension] = [

    ScoreDimension(
        rule_id="R-S01",
        name="Travel Time",
        weight_attr="w_dist",
        normalisation="minmax",
        invert=True,
        raw_fn=lambda row, _ctx: row.get("travel_time") or 999,
        description="Schools with shorter travel time score higher (raw: minutes).",
    ),

    ScoreDimension(
        rule_id="R-S02",
        name="CCA Match",
        weight_attr="w_cca",
        normalisation="minmax",
        raw_fn=lambda row, ctx: len(
            set(str(row.get("cca", "")).split("; ")) & set(ctx["cca_matches"])
        ),
        description="Count of CCA matches between user's desired CCAs and school offering.",
    ),

    ScoreDimension(
        rule_id="R-S03",
        name="Programme Match",
        weight_attr="w_prog",
        normalisation="minmax",
        raw_fn=lambda row, ctx: len(
            set(str(row.get("niche_programmes", "")).split("; ")) & set(ctx["prog_matches"])
        ),
        description="Count of ALP/LLP programme matches between user's preferences and school.",
    ),

    ScoreDimension(
        rule_id="R-S04",
        name="PSLE Tier",
        weight_attr="w_psle_tier",
        normalisation="ordinal",
        ordinal_map={"1": 1.0, "2": 0.75, "3": 0.5, "4": 0.25},
        raw_fn=lambda row, _ctx: str(int(float(row.get("school_tier", 4)))),
        description="School academic tier (Tier 1 = top, Tier 4 = general). Ordinal 0–1 scale.",
    ),

    ScoreDimension(
        rule_id="R-S05",
        name="Sports Excellence",
        weight_attr="w_sports",
        normalisation="minmax",
        raw_fn=lambda row, ctx: len(
            set(row.get("sports_achievement_2025", {}).get(ctx.get("gender", "M"), []))
            & set(ctx["sports_matches"])
        ),
        description="Count of NSG sports achievements matching user's desired sports (by gender).",
    ),

    ScoreDimension(
        rule_id="R-S06",
        name="Arts Excellence",
        weight_attr="w_arts",
        normalisation="minmax",
        raw_fn=lambda row, ctx: len(
            set(str(row.get("arts_distinction_2024", "")).split("; ")) & set(ctx["arts_matches"])
        ),
        description="Count of SYF Arts Distinction matches for user's desired performing arts.",
    ),

    ScoreDimension(
        rule_id="R-S07",
        name="Session Type",
        weight_attr="w_session",
        normalisation="binary",
        binary_fn=lambda row, ctx: (
            1 if ctx["user_session"] and row.get("session_code") == ctx["user_session"] else 0
        ),
        description="Binary: 1 if school session matches user's preference (Full Day / Single).",
    ),

    ScoreDimension(
        rule_id="R-S08",
        name="SAP School",
        weight_attr="w_sap",
        normalisation="binary",
        binary_fn=lambda row, ctx: (
            1 if ctx["user_sap"] and row.get("sap_ind") == ctx["user_sap"] else 0
        ),
        description="Binary: 1 if school SAP status matches user's preference.",
    ),

    ScoreDimension(
        rule_id="R-S09",
        name="Autonomous School",
        weight_attr="w_autonomous",
        normalisation="binary",
        binary_fn=lambda row, ctx: (
            1 if ctx["user_autonomous"] and row.get("autonomous_ind") == ctx["user_autonomous"]
            else 0
        ),
        description="Binary: 1 if autonomous status matches user's preference.",
    ),

    ScoreDimension(
        rule_id="R-S10",
        name="IP School",
        weight_attr="w_ip",
        normalisation="binary",
        binary_fn=lambda row, ctx: (
            1 if ctx["user_ip"] and row.get("ip_ind") == ctx["user_ip"] else 0
        ),
        description="Binary: 1 if IP/through-train status matches user's preference.",
    ),

    ScoreDimension(
        rule_id="R-S11",
        name="Mother Tongue",
        weight_attr="w_mt",
        normalisation="binary",
        binary_fn=lambda row, ctx: (
            1
            if ctx["user_mt"] and ctx["user_mt"] in str(row.get("mother_tongue", ""))
            else 0
        ),
        description=(
            "Binary: 1 if school offers the user's preferred mother tongue language. "
            "Guard: preference must be non-empty before comparing."
        ),
    ),
]


# R-S12 (weight normalisation) and R-S13 (final score formula) are
# implemented directly in nodes/scorer.py using numpy — see that file.
WEIGHT_NORM_RULE_ID = "R-S12"
FINAL_SCORE_RULE_ID = "R-S13"
