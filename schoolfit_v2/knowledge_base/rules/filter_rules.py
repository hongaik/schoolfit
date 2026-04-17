"""
Filter Rules (R-F) — applied by Node 4 (filter.py).

Each rule takes a per-school context and returns True (school passes) or None (fails).
A school is included only if ALL filter rules return True.

Context keys:
    nature_code (str): "M", "F", or "MF"
    dist_to_user (float): straight-line distance in km
    gender (str): "M" or "F"
    radius_km (float): effective search radius
"""
from knowledge_base.rule_engine import engine, RuleCategory

SOURCE = "MOE School Data / System"


@engine.register(
    id="R-F01",
    category=RuleCategory.FILTER,
    description=(
        "Gender filter: school must accept the child's gender. "
        "Boys' schools (M) exclude girls; Girls' schools (F) exclude boys; "
        "Co-ed (MF) accepts all."
    ),
    source=SOURCE,
)
def gender_filter(ctx: dict):
    return True if ctx["gender"] in ctx["nature_code"] else None


@engine.register(
    id="R-F02",
    category=RuleCategory.FILTER,
    description=(
        "Distance filter: school must be within the user's specified radius (km) "
        "from their home postal code."
    ),
    source="System",
)
def distance_filter(ctx: dict):
    return True if ctx["dist_to_user"] <= ctx["radius_km"] else None


@engine.register(
    id="R-F03",
    category=RuleCategory.FILTER,
    description=(
        "Same-gender-only filter: if user wants only same-gender schools "
        "(boys-only for boys, girls-only for girls), exclude co-ed schools."
    ),
    source="System",
)
def same_gender_filter(ctx: dict):
    prefer_same = ctx.get("prefer_same_gender_school", False)
    if not prefer_same:
        return True  # no preference; all schools pass

    # Check if school matches the child's gender exactly (not co-ed)
    school_nature = ctx["nature_code"]
    child_gender = ctx["gender"]

    # M or F (not MF) → same gender school
    # MF → co-ed, fails the same-gender-only filter
    return True if school_nature == child_gender else None
