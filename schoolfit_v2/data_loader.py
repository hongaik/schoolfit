"""
Cached data and model loaders for SchoolFit v2.
All heavy I/O (CSV reads, embedding loads, model downloads) happens once per
Streamlit session via @st.cache_resource.

CSVs live under data/; precomputed embeddings live under data/artifacts/.
"""
from __future__ import annotations

import ast
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"
ARTIFACT_ROOT = DATA_ROOT / "artifacts"


# =============================================================================
# School data
# =============================================================================

@st.cache_resource
def load_master() -> pd.DataFrame:
    df = pd.read_csv(DATA_ROOT / "master.csv").fillna({
        "sports_achievement_2025": "{}",
        "arts_distinction_2024": "",
        "school_tier": "4",
    })
    df["sports_achievement_2025"] = df["sports_achievement_2025"].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else x
    )
    df["nature_code"] = df["nature_code"].map({
        "CO-ED SCHOOL": "MF",
        "BOYS' SCHOOL": "M",
        "GIRLS' SCHOOL": "F",
    })
    return df


@st.cache_resource
def load_ballot_history() -> pd.DataFrame:
    return pd.read_csv(DATA_ROOT / "ballot_history.csv")


# =============================================================================
# Reference lists (derived from master data)
# =============================================================================

@st.cache_resource
def load_school_list() -> list[str]:
    return sorted(load_master()["school_name"].unique().tolist())


@st.cache_resource
def load_arts_dist_list() -> list[str]:
    master = load_master()
    return (
        master["arts_distinction_2024"]
        .dropna()
        .str.split("; ")
        .explode()
        .dropna()
        .unique()
        .tolist()
    )


@st.cache_resource
def load_sports_nsg_list() -> list[str]:
    master = load_master()
    return sorted(
        master["sports_achievement_2025"]
        .dropna()
        .apply(lambda d: sum(d.values(), []) if isinstance(d, dict) else [])
        .explode()
        .dropna()
        .unique()
        .tolist()
    )


# =============================================================================
# Semantic embeddings + sentence model
# =============================================================================

@st.cache_resource
def load_cca_embeddings() -> tuple[np.ndarray, list[str]]:
    vectors = np.load(ARTIFACT_ROOT / "cca_vectors.npy")
    with open(ARTIFACT_ROOT / "cca_names.pkl", "rb") as f:
        names = pickle.load(f)
    return vectors, names


@st.cache_resource
def load_prog_embeddings() -> tuple[np.ndarray, list[str]]:
    vectors = np.load(ARTIFACT_ROOT / "alp_llp_vectors.npy")
    with open(ARTIFACT_ROOT / "alp_llp_domains.pkl", "rb") as f:
        names = pickle.load(f)
    return vectors, names


@st.cache_resource
def load_sentence_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
