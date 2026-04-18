"""
Node 3 — Semantic Matching.
Converts free-form user activities into matched CCA names and programme names
using pre-computed sentence-transformer embeddings (offline, no API cost).
Also derives sports_matches and arts_matches for scoring dimensions R-S05/R-S06.
"""
from __future__ import annotations

import numpy as np
from sentence_transformers import util

from data_loader import (
    load_arts_dist_list,
    load_cca_embeddings,
    load_prog_embeddings,
    load_sentence_model,
    load_sports_nsg_list,
)
from state import SchoolFitState

_TOP_K = 10          # max number of matches returned per category
_CCA_THRESHOLD = 0.3   # fraction of top score to include as a CCA match
_PROG_THRESHOLD = 0.5  # stricter threshold for programmes


# =============================================================================
# Helpers
# =============================================================================

def _aggregate_similarities(
    queries: list[str],
    embeddings: np.ndarray,
    names: list[str],
    threshold: float,
    top_k: int,
) -> tuple[list[str], list[float]]:
    """
    For each query, compute cosine similarity against all embeddings.
    Aggregate scores across queries, normalise, return top-k (name, score) pairs.
    Scores are normalised to 0–1 within the candidate set (relative match strength).
    """
    if not queries:
        return [], []

    model = load_sentence_model()
    aggregated: dict[str, float] = {}

    for query in queries:
        query_vec = model.encode(query)
        scores = util.cos_sim(query_vec, embeddings)[0]
        best_score = float(scores.max())
        if best_score == 0:
            continue
        for i, score in enumerate(scores):
            s = float(score)
            if s >= best_score * threshold:
                name = names[i]
                aggregated[name] = aggregated.get(name, 0) + s / best_score

    if not aggregated:
        return [], []

    max_agg = max(aggregated.values())
    normalised = {k: v / max_agg for k, v in aggregated.items()}
    sorted_names = sorted(normalised, key=lambda k: normalised[k], reverse=True)
    pairs: list[tuple[str, float]] = []
    for n in sorted_names[:top_k]:
        nu = n.upper()
        if nu == "GENERAL HOLISTIC DEVELOPMENT":
            continue
        pairs.append((nu, normalised[n]))
    names_out = [p[0] for p in pairs]
    scores_out = [p[1] for p in pairs]
    return names_out, scores_out


# =============================================================================
# Node function
# =============================================================================

def semantic_match_node(state: SchoolFitState) -> dict:
    intent = state["user_intent"]
    activities = intent.activities if intent else []

    cca_vectors, cca_names = load_cca_embeddings()
    prog_vectors, prog_names = load_prog_embeddings()

    cca_matches, cca_match_scores = _aggregate_similarities(
        activities, cca_vectors, cca_names, _CCA_THRESHOLD, _TOP_K
    )
    prog_matches, prog_match_scores = _aggregate_similarities(
        activities, prog_vectors, prog_names, _PROG_THRESHOLD, _TOP_K
    )

    # Derive sports/arts subsets from cca_matches (no extra API calls)
    sports_nsg = set(load_sports_nsg_list())
    arts_dist = set(load_arts_dist_list())

    return {
        "cca_matches": cca_matches,
        "prog_matches": prog_matches,
        "cca_match_scores": cca_match_scores,
        "prog_match_scores": prog_match_scores,
        # These are stored in the state ctx passed to scorer
        "sports_matches": [c for c in cca_matches if c in sports_nsg],
        "arts_matches": [c for c in cca_matches if c in arts_dist],
    }
