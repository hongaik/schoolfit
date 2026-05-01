"""
Cached API client factories for the SchoolFit v2 pipeline.
LLM client uses @st.cache_resource; OneMap token is session-cached with expiry-based refresh.
"""
from __future__ import annotations

import os
import time

import requests
import streamlit as st
from langchain_openai import ChatOpenAI

_ONEMAP_ACCESS = "_onemap_access_token"
_ONEMAP_EXPIRES = "_onemap_token_expires_at"
# Refresh this many seconds before OneMap's expiry to avoid edge-of-expiry 401s.
_ONEMAP_EXPIRY_BUFFER_SEC = 120
# If the API omits expiry_timestamp, assume this TTL (seconds) before re-fetching.
_ONEMAP_FALLBACK_TTL_SEC = 48 * 3600


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

def get_onemap_token() -> str:
    """Return a valid OneMap bearer token, refreshing before expiry when using password auth.

    Accepts two forms in secrets.toml (or ONEMAP_* env vars):
      - onemap_token_pwd = account password → POST getToken; re-fetches using expiry_timestamp
      - onemap_token_pwd = "eyJ..."         → used as-is (no auto-refresh; replace when it expires)
    """
    try:
        email = st.secrets["onemap_token_email"]
        pwd_or_token = st.secrets["onemap_token_pwd"]
    except Exception:
        email = os.environ.get("ONEMAP_EMAIL", "")
        pwd_or_token = os.environ.get("ONEMAP_PWD", "")

    if not pwd_or_token:
        return ""

    if pwd_or_token.startswith("eyJ"):
        return pwd_or_token

    now = time.time()
    cached = st.session_state.get(_ONEMAP_ACCESS, "")
    exp_raw = st.session_state.get(_ONEMAP_EXPIRES)
    try:
        exp_at = float(exp_raw) if exp_raw is not None else 0.0
    except (TypeError, ValueError):
        exp_at = 0.0

    if (
        cached
        and exp_at > 0
        and now < exp_at - _ONEMAP_EXPIRY_BUFFER_SEC
    ):
        return cached

    url = "https://www.onemap.gov.sg/api/auth/post/getToken"
    try:
        resp = requests.post(
            url, json={"email": email, "password": pwd_or_token}, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        new_token = data.get("access_token", "")
        if not new_token:
            if cached and exp_at > now:
                return cached
            return ""

        raw_exp = data.get("expiry_timestamp")
        if raw_exp is not None:
            try:
                new_exp = float(raw_exp)
            except (TypeError, ValueError):
                new_exp = now + _ONEMAP_FALLBACK_TTL_SEC
        else:
            new_exp = now + _ONEMAP_FALLBACK_TTL_SEC

        st.session_state[_ONEMAP_ACCESS] = new_token
        st.session_state[_ONEMAP_EXPIRES] = new_exp
        return new_token
    except Exception:
        if cached and exp_at > now:
            return cached
        return ""
