"""
Input helpers for form-based school preference input.
Provides CCA and programme suggestion functions using semantic similarity.
"""
from __future__ import annotations

import json
import numpy as np
import pickle
import streamlit as st
from pathlib import Path
from sentence_transformers import SentenceTransformer, util

# =============================================================================
# Setup paths and cached models
# =============================================================================

ROOT = Path(__file__).resolve().parent
DEPLOY_ROOT = ROOT.parent / "deploy"


@st.cache_resource
def load_embedding_model():
    """Load and cache the sentence transformer model."""
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


@st.cache_resource
def load_cca_data():
    """Load cached CCA embeddings and names."""
    try:
        cca_vectors = np.load(DEPLOY_ROOT / "artifacts" / "cca_vectors.npy")
        with open(DEPLOY_ROOT / "artifacts" / "cca_names.pkl", "rb") as f:
            cca_names = pickle.load(f)
        return cca_vectors, cca_names
    except Exception as e:
        print(f"Warning: Could not load CCA embeddings: {e}")
        return None, None


@st.cache_resource
def load_prog_data():
    """Load cached programme embeddings and names."""
    try:
        prog_vectors = np.load(DEPLOY_ROOT / "artifacts" / "alp_llp_vectors.npy")
        with open(DEPLOY_ROOT / "artifacts" / "alp_llp_domains.pkl", "rb") as f:
            prog_names = pickle.load(f)
        return prog_vectors, prog_names
    except Exception as e:
        print(f"Warning: Could not load programme embeddings: {e}")
        return None, None


@st.cache_resource
def load_alp_llp_json():
    """Load ALP/LLP metadata."""
    try:
        with open(DEPLOY_ROOT / "artifacts" / "alp_llp.json") as f:
            return json.load(f)
    except Exception:
        return []


@st.cache_resource
def get_full_cca_list():
    """Get complete list of all CCAs from master data."""
    from data_loader import load_master
    master = load_master()
    cca_set = set()
    for ccas_str in master["cca"].dropna():
        for cca in str(ccas_str).split("; "):
            if cca.strip():
                cca_set.add(cca.strip())
    return sorted(list(cca_set))


@st.cache_resource
def get_full_prog_list():
    """Get complete list of all programmes from master data."""
    from data_loader import load_master
    master = load_master()
    prog_set = set()
    for progs_str in master["niche_programmes"].dropna():
        for prog in str(progs_str).split("; "):
            if prog.strip():
                prog_set.add(prog.strip())
    return sorted(list(prog_set))


# =============================================================================
# CCA Similarity Matching
# =============================================================================

def get_best_cca_match(user_query: str, model, cca_embeddings, cca_names) -> dict:
    """
    Find CCA matches for a single user query using semantic similarity.
    Returns dict of {cca_name: similarity_score (0-1)}.
    """
    if not user_query.strip():
        return {}

    # Create embedding for user query
    query_vec = model.encode(user_query)

    # Cosine similarity scores
    scores = util.cos_sim(query_vec, cca_embeddings)[0]
    best_idx = np.argmax(scores)

    # Get matches with at least 30% of top score
    threshold = scores[best_idx].item() * 0.3
    top_matches = [
        (cca_names[i], scores[i].item())
        for i, score in enumerate(scores)
        if score > threshold
    ]
    top_matches = sorted(top_matches, key=lambda x: x[1], reverse=True)
    top_matches_dict = dict(top_matches)

    # Normalize scores to 0-1
    if top_matches_dict:
        max_score = max(top_matches_dict.values())
        top_matches_dict = {name: score / max_score for name, score in top_matches_dict.items()}

    return top_matches_dict


def cca_similarity(user_inputs: list[str], model, cca_embeddings, cca_names) -> list[tuple]:
    """
    Find CCA matches for multiple user inputs using semantic similarity.
    Returns sorted list of (cca_name, aggregated_score) tuples.
    """
    aggregated_matches = {}

    for user_input in user_inputs:
        if not user_input.strip():
            continue

        top_matches = get_best_cca_match(user_input, model, cca_embeddings, cca_names)

        if not aggregated_matches:
            # First input: seed aggregated matches
            aggregated_matches = top_matches.copy()
        else:
            # Subsequent inputs: accumulate scores
            for name, score in top_matches.items():
                if name in aggregated_matches:
                    aggregated_matches[name] += score
                else:
                    aggregated_matches[name] = score

    # Normalize final scores
    if aggregated_matches:
        max_score = max(aggregated_matches.values())
        aggregated_matches = {name: score / max_score for name, score in aggregated_matches.items()}

    sorted_matches = sorted(aggregated_matches.items(), key=lambda x: x[1], reverse=True)
    return sorted_matches


def find_similar_cca(user_inputs: list[str]) -> list[tuple]:
    """
    Find top CCA suggestions based on user inputs.
    Returns list of tuples (cca_name, similarity_score) up to 10 most similar.
    Similarity scores are normalized to 0-1 range.
    """
    model = load_embedding_model()
    cca_embeddings, cca_names = load_cca_data()

    if cca_embeddings is None or not user_inputs:
        # Fallback: return full list with neutral scores
        full_list = get_full_cca_list()
        return [(name, 0.5) for name in full_list]

    # Get matches (already sorted by score descending)
    matches = cca_similarity(user_inputs, model, cca_embeddings, cca_names)

    # Return top 10 as tuples (name, score)
    return matches[:10]


# =============================================================================
# Programme Similarity Matching
# =============================================================================

def get_best_prog_match(user_query: str, model, prog_embeddings, prog_names) -> dict:
    """
    Find programme matches for a single user query using semantic similarity.
    Returns dict of {prog_name: similarity_score (0-1)}.
    """
    if not user_query.strip():
        return {}

    # Create embedding for user query
    query_vec = model.encode(user_query)

    # Cosine similarity scores
    scores = util.cos_sim(query_vec, prog_embeddings)[0]
    best_idx = np.argmax(scores)

    # Get matches with at least 50% of top score (stricter than CCA)
    threshold = scores[best_idx].item() * 0.5
    top_matches = [
        (prog_names[i], scores[i].item())
        for i, score in enumerate(scores)
        if score > threshold
    ]
    top_matches = sorted(top_matches, key=lambda x: x[1], reverse=True)
    top_matches_dict = dict(top_matches)

    # Normalize scores to 0-1
    if top_matches_dict:
        max_score = max(top_matches_dict.values())
        top_matches_dict = {name: score / max_score for name, score in top_matches_dict.items()}

    return top_matches_dict


def prog_similarity(user_inputs: list[str], model, prog_embeddings, prog_names) -> list[tuple]:
    """
    Find programme matches for multiple user inputs using semantic similarity.
    Returns sorted list of (prog_name, aggregated_score) tuples.
    """
    aggregated_matches = {}

    for user_input in user_inputs:
        if not user_input.strip():
            continue

        top_matches = get_best_prog_match(user_input, model, prog_embeddings, prog_names)

        if not aggregated_matches:
            # First input: seed aggregated matches
            aggregated_matches = top_matches.copy()
        else:
            # Subsequent inputs: accumulate scores
            for name, score in top_matches.items():
                if name in aggregated_matches:
                    aggregated_matches[name] += score
                else:
                    aggregated_matches[name] = score

    # Normalize final scores
    if aggregated_matches:
        max_score = max(aggregated_matches.values())
        aggregated_matches = {name: score / max_score for name, score in aggregated_matches.items()}

    sorted_matches = sorted(aggregated_matches.items(), key=lambda x: x[1], reverse=True)
    return sorted_matches


def find_similar_prog(user_inputs: list[str]) -> list[tuple]:
    """
    Find top programme suggestions based on user inputs.
    Returns list of tuples (prog_name, similarity_score) up to 10 most similar.
    Similarity scores are normalized to 0-1 range.
    Filters out generic "GENERAL HOLISTIC DEVELOPMENT" programme.
    """
    model = load_embedding_model()
    prog_embeddings, prog_names = load_prog_data()

    if prog_embeddings is None or not user_inputs:
        # Fallback: return full list with neutral scores
        full_list = get_full_prog_list()
        return [(name, 0.5) for name in full_list]

    # Get matches (already sorted by score descending)
    matches = prog_similarity(user_inputs, model, prog_embeddings, prog_names)

    # Filter out generic programmes and return top 10 as tuples
    suggestions = [
        (name, score) for name, score in matches[:10]
        if name.upper() != "GENERAL HOLISTIC DEVELOPMENT"
    ]
    return suggestions
