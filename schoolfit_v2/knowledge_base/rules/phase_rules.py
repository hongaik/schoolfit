"""
Phase Eligibility Rules (R-P) — applied by Node 7 (phases.py).

Rules are evaluated in registration order; the first matching rule wins.
Each rule returns a phase string (e.g. "Phase 1") or None (rule does not apply).

Context keys:
    school_name (str)
    citizenship (str): "SC", "PR", or "International"
    dist_to_user (float): km
    has_sibling (list[str]): schools with current sibling enrolled
    former_student (list[str]): schools where older sibling previously studied
    is_alumni (list[str]): schools where parent is alumnus
    is_staff (list[str]): schools where parent is staff
    is_mk (list[str]): schools where child attends MOE Kindergarten
    is_volunteer (list[str]): schools where parent volunteers
    is_church_clan (list[str]): schools affiliated with parent's church/clan
    is_community_leader (str): "Y" or "" or "N"

Source: MOE P1 Registration Exercise Guidelines (updated annually)
"""
from knowledge_base.rule_engine import engine, RuleCategory

SOURCE = "MOE P1 Registration Exercise Guidelines"


def _distance_suffix(dist_km: float, citizenship: str) -> str:
    """Return phase priority suffix based on distance bracket and citizenship."""
    if dist_km <= 1.0:
        cat = 1
    elif dist_km <= 2.0:
        cat = 2
    else:
        cat = 3
    if citizenship == "PR":
        cat += 3   # PR categories: 4, 5, 6
    return f"-{cat}"


@engine.register(
    id="R-P01",
    category=RuleCategory.PHASE,
    description=(
        "International students are assigned directly to Phase 3. "
        "No distance priority applies."
    ),
    source=SOURCE,
)
def phase_international(ctx: dict):
    if ctx["citizenship"] == "International":
        return "Phase 3"
    return None


@engine.register(
    id="R-P02",
    category=RuleCategory.PHASE,
    description=(
        "Phase 1: Child qualifies if a sibling is currently enrolled in this school. "
        "No balloting — admission is guaranteed."
    ),
    source=SOURCE,
)
def phase_1_sibling(ctx: dict):
    if ctx["school_name"] in ctx["has_sibling"]:
        return "Phase 1"
    return None


@engine.register(
    id="R-P03",
    category=RuleCategory.PHASE,
    description=(
        "Phase 2A: Child qualifies if the parent is an alumnus/alumna of this school, "
        "OR the parent is currently on staff, "
        "OR an older sibling previously studied here, "
        "OR the child attends this school's MOE Kindergarten. "
        "Phase suffix reflects citizenship and distance bracket."
    ),
    source=SOURCE,
)
def phase_2a(ctx: dict):
    name = ctx["school_name"]
    qualifies = (
        name in ctx["is_alumni"]
        or name in ctx["is_staff"]
        or name in ctx["former_student"]
        or name in ctx["is_mk"]
    )
    if qualifies:
        suffix = _distance_suffix(ctx["dist_to_user"], ctx["citizenship"])
        return f"Phase 2A{suffix}"
    return None


@engine.register(
    id="R-P04",
    category=RuleCategory.PHASE,
    description=(
        "Phase 2B: Child qualifies if the parent is an active volunteer at this school "
        "(minimum 40 hours), OR if the school is affiliated with the parent's church or "
        "clan association. Phase suffix reflects citizenship and distance bracket."
    ),
    source=SOURCE,
)
def phase_2b_volunteer_church(ctx: dict):
    name = ctx["school_name"]
    qualifies = name in ctx["is_volunteer"] or name in ctx["is_church_clan"]
    if qualifies:
        suffix = _distance_suffix(ctx["dist_to_user"], ctx["citizenship"])
        return f"Phase 2B{suffix}"
    return None


@engine.register(
    id="R-P05",
    category=RuleCategory.PHASE,
    description=(
        "Phase 2B: Child qualifies if the parent is an endorsed active community leader "
        "AND the home is within 2 km of the school. "
        "Phase suffix reflects citizenship and distance bracket."
    ),
    source=SOURCE,
)
def phase_2b_community_leader(ctx: dict):
    is_leader = ctx.get("is_community_leader") == "Y"
    within_2km = ctx["dist_to_user"] < 2.0
    if is_leader and within_2km:
        suffix = _distance_suffix(ctx["dist_to_user"], ctx["citizenship"])
        return f"Phase 2B{suffix}"
    return None


@engine.register(
    id="R-P06",
    category=RuleCategory.PHASE,
    description=(
        "Phase 2C: Default phase for Singapore Citizens and PRs who do not qualify "
        "for Phase 1, 2A, or 2B. Phase suffix reflects citizenship and distance bracket."
    ),
    source=SOURCE,
)
def phase_2c_default(ctx: dict):
    # This rule fires for all SC/PR who haven't matched an earlier phase.
    # Since R-P01..R-P05 are checked first, reaching here means 2C applies.
    if ctx["citizenship"] in ("SC", "PR"):
        suffix = _distance_suffix(ctx["dist_to_user"], ctx["citizenship"])
        return f"Phase 2C{suffix}"
    return None
