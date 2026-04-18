"""
Node 1 — Intent Extraction.
LangChain LCEL chain: NL text → UserIntent (Pydantic structured output).
Also infers scoring weights from emphasis in the user's text.
"""
from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from api_clients import get_llm
from data_loader import load_school_list
from state import SchoolFitState, UserIntent

# =============================================================================
# Prompt
# =============================================================================

_SYSTEM = """\
You are extracting structured Singapore P1 primary school admission preferences
from a parent's natural-language description of their child.

EXTRACTION RULES
- gender: "M" for boy/son, "F" for girl/daughter. Required.
- postal_code: 6-digit Singapore postal code. Required.
- citizenship: default "SC" unless stated otherwise.
- activities: ALL interests, hobbies, sports, arts, and CCAs mentioned — \
free-form strings. Include everything.
- prefer_same_gender_school: True if user wants ONLY same-gender schools \
(e.g. "boys-only school", "boys school", "I want only boys", "same gender school"). \
False otherwise (default allows co-ed).
- top_n: default 5 unless user specifies (max 10).
- radius_km: default 3.0 unless the user states a distance. Use a sensible local range \
(typically 1–6 km for "near home"). Do NOT output huge values (e.g. 50 or 100) unless \
the user explicitly wants to search the whole island; those values defeat "close to home" matching.

WEIGHT INFERENCE (0–5 scale, default shown)
Infer from how strongly the user emphasises each factor:
- w_dist (default 3): increase for "close to home / near / walking distance / \
important location"; decrease for "willing to travel / distance doesn't matter".
- w_cca (default 3): increase for "passionate about activities / CCA is important".
- w_prog (default 3): increase for "STEM / special programmes / learning focus".
- w_psle_tier (default 3): increase for "good academics / top school / \
PSLE performance / academic reputation".
- w_sports (default 0): set > 0 ONLY if user explicitly wants a school with \
STRONG SPORTS TEAMS / NSG excellence.
- w_arts (default 0): set > 0 ONLY if user explicitly wants a school with \
STRONG ARTS / SYF distinction.
- w_session / w_sap / w_autonomous / w_ip / w_mt (default 0): \
set > 0 only if explicitly mentioned.

PREFERENCE EXTRACTION
- session: extract only if stated ("FULL DAY" or "SINGLE SESSION").
- sap: "Y" if user wants SAP, "N" if explicitly not, "" otherwise.
- autonomous, ip: same pattern.
- mother_tongue: "CHINESE", "MALAY", "TAMIL", or "" if not mentioned.

SCHOOL NAME MATCHING (for family context fields)
Match user-mentioned school names to the known school list below.
Allow minor spelling differences. Return [] if none mentioned.
Fields: has_sibling, former_student, is_alumni, is_staff, is_mk,
        is_volunteer, is_church_clan.
is_community_leader: "Y" only if explicitly stated; "N" only if explicitly ruled out.

KNOWN SCHOOL NAMES (use these exact strings for school-list fields):
{school_list}
"""

_HUMAN = "{user_input}"

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", _HUMAN),
])


# =============================================================================
# Node function
# =============================================================================

def extract_intent_node(state: SchoolFitState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(UserIntent)
    chain = _prompt | structured_llm

    school_list = load_school_list()

    try:
        intent: UserIntent = chain.invoke({
            "user_input": state["user_input"],
            "school_list": "\n".join(school_list),
        })
        return {"user_intent": intent}
    except Exception as exc:
        return {"error": f"Could not understand your input. Please try rephrasing. ({exc})"}
