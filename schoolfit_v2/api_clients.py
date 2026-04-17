"""
Cached API client factories for the SchoolFit v2 pipeline.
All clients are initialised once per Streamlit session via @st.cache_resource.
"""
from __future__ import annotations

import os
import requests
import streamlit as st
from langchain_openai import ChatOpenAI


# =============================================================================
# OpenAI / LangChain LLM
# =============================================================================

@st.cache_resource
def get_llm(model: str = "gpt-4o-mini") -> ChatOpenAI:
    """Single cached LangChain ChatOpenAI instance for the session."""
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        api_key = os.environ.get("OPENAI_API_KEY", "")
    return ChatOpenAI(model=model, api_key=api_key, temperature=0, request_timeout=30)


# =============================================================================
# OneMap token
# =============================================================================

@st.cache_resource
def get_onemap_token() -> str:
    """Fetch and cache the OneMap API bearer token for the session.

    Accepts two forms in secrets.toml:
      - onemap_token_pwd = "your_account_password"  → fetches a fresh token via getToken
      - onemap_token_pwd = "eyJ..."                 → uses the value directly as a token
    """
    try:
        email = st.secrets["onemap_token_email"]
        pwd_or_token = st.secrets["onemap_token_pwd"]
    except Exception:
        email = os.environ.get("ONEMAP_EMAIL", "")
        pwd_or_token = os.environ.get("ONEMAP_PWD", "")

    if not pwd_or_token:
        return ""

    # If the value is already a JWT (starts with "eyJ"), use it directly.
    if pwd_or_token.startswith("eyJ"):
        return pwd_or_token

    url = "https://www.onemap.gov.sg/api/auth/post/getToken"
    try:
        resp = requests.post(
            url, json={"email": email, "password": pwd_or_token}, timeout=10
        )
        resp.raise_for_status()
        return resp.json().get("access_token", "")
    except Exception:
        return ""
