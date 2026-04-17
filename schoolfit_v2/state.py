"""
Pipeline state and schema definitions for SchoolFit v2.
SchoolFitState is the single source of truth passed through every LangGraph node.
"""
from __future__ import annotations

from typing import Any, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field


# =============================================================================
# UserIntent — extracted from the user's natural-language input by Node 1
# =============================================================================

class UserIntent(BaseModel):
    """Structured representation of a parent's school preferences."""

    # Core demographics
    gender: str = Field(
        description='Child gender. Must be "M" for boy or "F" for girl.'
    )
    postal_code: str = Field(
        description="6-digit Singapore postal code of the family home."
    )
    citizenship: str = Field(
        default="SC",
        description='Citizenship. One of: "SC", "PR", "International".'
    )

    # Activities / interests (free-form; Node 3 converts to CCA + programme matches)
    activities: list[str] = Field(
        default_factory=list,
        description=(
            "All activities, hobbies, and interests the child has. "
            "Extract every mention, e.g. ['swimming', 'choir', 'robotics', 'STEM']."
        )
    )

    # Gender school preference
    prefer_same_gender_school: bool = Field(
        default=False,
        description=(
            "If True, only same-gender schools (boys-only for boys, girls-only for girls). "
            "Extract True if user mentions 'boys school', 'boys only', 'same gender', etc."
        )
    )

    # Search configuration
    top_n: int = Field(default=5, description="How many schools to show. Default 5, max 10.")
    radius_km: float = Field(default=3.0, description="Max distance from home to school in km.")

    # --- Inferred weights (0–5 scale; LLM reads emphasis from text) ---
    w_dist: float = Field(default=3.0, description="Weight: travel time importance.")
    w_cca: float = Field(default=3.0, description="Weight: CCA match importance.")
    w_prog: float = Field(default=3.0, description="Weight: special programme match importance.")
    w_psle_tier: float = Field(default=3.0, description="Weight: PSLE academic tier importance.")
    w_sports: float = Field(default=0.0, description="Weight: sports NSG excellence importance.")
    w_arts: float = Field(default=0.0, description="Weight: arts SYF distinction importance.")
    w_session: float = Field(default=0.0, description="Weight: session type importance.")
    w_sap: float = Field(default=0.0, description="Weight: SAP school preference importance.")
    w_autonomous: float = Field(default=0.0, description="Weight: autonomous school importance.")
    w_ip: float = Field(default=0.0, description="Weight: IP/through-train preference importance.")
    w_mt: float = Field(default=0.0, description="Weight: mother tongue offering importance.")

    # --- School characteristic preferences ---
    session: str = Field(
        default="",
        description='Session preference. One of: "", "FULL DAY", "SINGLE SESSION".'
    )
    sap: str = Field(default="", description='SAP school preference. One of: "", "Y", "N".')
    autonomous: str = Field(default="", description='Autonomous school. One of: "", "Y", "N".')
    ip: str = Field(default="", description='IP school. One of: "", "Y", "N".')
    mother_tongue: str = Field(
        default="",
        description='Mother tongue preference. One of: "", "CHINESE", "MALAY", "TAMIL".'
    )

    # --- Family context (school names matched to the known school list) ---
    has_sibling: list[str] = Field(
        default_factory=list,
        description="Schools where a sibling is currently enrolled."
    )
    former_student: list[str] = Field(
        default_factory=list,
        description="Schools where an older sibling previously studied."
    )
    is_alumni: list[str] = Field(
        default_factory=list,
        description="Schools where the parent is an alumnus/alumna."
    )
    is_staff: list[str] = Field(
        default_factory=list,
        description="Schools where the parent is currently on staff."
    )
    is_mk: list[str] = Field(
        default_factory=list,
        description="Schools where the child attends the MOE Kindergarten."
    )
    is_volunteer: list[str] = Field(
        default_factory=list,
        description="Schools where the parent volunteers (min. 40 hours)."
    )
    is_church_clan: list[str] = Field(
        default_factory=list,
        description="Schools affiliated with the parent's church or clan association."
    )
    is_community_leader: str = Field(
        default="",
        description='Endorsed community leader. One of: "", "Y", "N".'
    )


# =============================================================================
# SchoolFitState — LangGraph pipeline state
# =============================================================================

class SchoolFitState(TypedDict):
    # ── Input ──────────────────────────────────────────────────────────────
    user_input: str

    # ── Node 1: intent extraction ──────────────────────────────────────────
    user_intent: Optional[UserIntent]

    # ── Node 2: geocoding ─────────────────────────────────────────────────
    coordinates: Optional[tuple]            # (X, Y, lat, lon) SVY21 + WGS84

    # ── Node 3: semantic matching ─────────────────────────────────────────
    cca_matches: list                       # list[str] — matched CCA names
    prog_matches: list                      # list[str] — matched programme names

    # ── Node 4: hard filtering ────────────────────────────────────────────
    filtered_schools: Optional[Any]         # pd.DataFrame

    # ── Node 5: travel time ───────────────────────────────────────────────
    schools_with_travel: Optional[Any]      # pd.DataFrame (adds travel_mode, travel_time)

    # ── Node 6: scoring + ranking ─────────────────────────────────────────
    top_schools: Optional[Any]              # pd.DataFrame (top_n rows, score cols added)

    # ── Node 7: phase eligibility + admission signal ──────────────────────
    schools_with_phases: Optional[Any]      # pd.DataFrame (adds phase, admission_signal)

    # ── Rule engine traces (accumulated across nodes 4, 6, 7) ─────────────
    rule_traces: list                       # list[RuleTrace]
    filter_exclusion_log: dict              # dict[rule_id, list[(school_name, reason)]]

    # ── Node 8: LLM summary ───────────────────────────────────────────────
    summary: str

    # ── Control flow ──────────────────────────────────────────────────────
    error: Optional[str]
    retry_count: int
