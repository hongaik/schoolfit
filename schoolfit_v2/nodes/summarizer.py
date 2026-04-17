"""
Node 8 — LLM Recommendation Summary.
LangChain LCEL chain: score breakdown + rule traces → grounded 3–5 bullet narrative.
The summary explains WHY these schools ranked highest based strictly on the data,
referencing which scoring dimensions and rules drove the recommendations.
"""
from __future__ import annotations

import pandas as pd
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from api_clients import get_llm
from knowledge_base.rules.scoring_rules import SCORE_DIMENSIONS
from state import SchoolFitState

_SYSTEM = """\
You are SchoolFit SG — an analytical Singapore P1 school admissions assistant.
Write a factual, concise summary (exactly 3–5 bullet points) explaining why
the recommended schools were selected.

SCORING DIMENSIONS (for your reference):
{dimensions_desc}

CRITICAL RULES:
1. Output only an unnumbered bulleted list using "- " bullets.
2. Base your analysis ENTIRELY on the provided score breakdown data.
3. Reference specific schools by name.
4. When explaining scores, focus on meaningful values (e.g. "3 matched CCAs",
   "12-minute travel time", "Tier 1 school") — not abstract weights.
5. Do not use filler phrases like "great options" or "exciting choices".
6. If Phase 1 (Guaranteed) schools appear, highlight them.
"""

_HUMAN = """\
User's activities/interests: {activities}

Top Recommended Schools (Score Breakdown):
{breakdown}
"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", _HUMAN),
])


def _build_breakdown(df: pd.DataFrame, norm_weights: dict) -> str:
    lines = []
    for i, row in df.iterrows():
        lines.append(f"#{i + 1} {row['school_name']} — Total: {row['score_total']}/100")
        lines.append(f"  Phase: {row.get('phase', 'N/A')} | Signal: {row.get('admission_signal', 'N/A')}")
        lines.append(f"  Travel: {row.get('travel_time', 'N/A')} min ({row.get('travel_mode', 'N/A')})")
        for dim in SCORE_DIMENSIONS:
            w = norm_weights.get(dim.rule_id, 0)
            if w > 0:
                raw_col = f"_raw_{dim.rule_id}"
                score_col = f"score_{dim.rule_id}"
                raw_val = row.get(raw_col, "-")
                norm_val = row.get(score_col, "-")
                lines.append(
                    f"  {dim.name}: raw={raw_val}, norm={round(float(norm_val), 2) if norm_val != '-' else '-'}"
                    f", weight={w:.0%}"
                )
        lines.append("")
    return "\n".join(lines)


def generate_summary_node(state: SchoolFitState) -> dict:
    df = state.get("schools_with_phases")
    intent = state.get("user_intent")

    if df is None or df.empty or intent is None:
        return {"summary": ""}

    norm_weights = df.attrs.get("norm_weights", {})
    breakdown = _build_breakdown(df, norm_weights)
    activities_str = ", ".join(intent.activities) if intent.activities else "not specified"

    dimensions_desc = "\n".join(
        f"- {d.name} ({d.rule_id}): {d.description}" for d in SCORE_DIMENSIONS
    )

    llm = get_llm()
    chain = _prompt | llm | StrOutputParser()

    try:
        summary = chain.invoke({
            "dimensions_desc": dimensions_desc,
            "activities": activities_str,
            "breakdown": breakdown,
        })
    except Exception as exc:
        summary = f"- Schools were ranked by fit score across travel time, CCAs, programmes, and academic tier.\n- (AI summary unavailable: {exc})"

    return {"summary": summary}
