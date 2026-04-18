"""
Node 3 — Derive Matches.
CCA and programme selections arrive as exact names chosen by the user in the
sidebar (semantic search ran there at input time). This node derives the
sports_matches and arts_matches subsets needed by the scorer.
"""
from __future__ import annotations

from data_loader import (
    load_arts_dist_list,
    load_sports_nsg_list,
)
from state import SchoolFitState


def derive_matches_node(state: SchoolFitState) -> dict:
    """Node 3: derive sports/arts subsets from exact CCA selections."""
    # Get matches that were already selected at form input time
    cca_matches = state.get("cca_matches", [])
    prog_matches = state.get("prog_matches", [])
    cca_match_scores = state.get("cca_match_scores", [])
    prog_match_scores = state.get("prog_match_scores", [])

    # Derive sports/arts subsets from cca_matches for scoring dimensions
    sports_nsg = set(load_sports_nsg_list())
    arts_dist = set(load_arts_dist_list())

    sports_matches = [c for c in cca_matches if c in sports_nsg]
    arts_matches = [c for c in cca_matches if c in arts_dist]

    return {
        "cca_matches": cca_matches,
        "prog_matches": prog_matches,
        "cca_match_scores": cca_match_scores,
        "prog_match_scores": prog_match_scores,
        "sports_matches": sports_matches,
        "arts_matches": arts_matches,
    }
