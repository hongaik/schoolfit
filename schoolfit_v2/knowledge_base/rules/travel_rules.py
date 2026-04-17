"""
Travel Mode Selection Rules (R-T) — applied by Node 5 (travel.py).

Rules determine which routing result to use after both PT and walk routes
have been attempted. Rules are evaluated in order; first match wins.

Context keys:
    pt_time (float | None): public-transport travel time in minutes
    walk_time (float | None): walking travel time in minutes
"""
from knowledge_base.rule_engine import engine, RuleCategory

SOURCE = "System / OneMap Routing API"


@engine.register(
    id="R-T01",
    category=RuleCategory.TRAVEL,
    description=(
        "Both PT and walk routes are available: use whichever is faster. "
        "Returns (mode, minutes) tuple."
    ),
    source=SOURCE,
)
def travel_both_available(ctx: dict):
    pt = ctx.get("pt_time")
    walk = ctx.get("walk_time")
    if pt is not None and walk is not None:
        if pt <= walk:
            return ("pt", round(pt))
        return ("walk", round(walk))
    return None


@engine.register(
    id="R-T02",
    category=RuleCategory.TRAVEL,
    description=(
        "PT route succeeded but walk routing failed: use the PT result as fallback. "
        "Do not discard a valid PT result when walk is unavailable."
    ),
    source=SOURCE,
)
def travel_pt_fallback(ctx: dict):
    pt = ctx.get("pt_time")
    walk = ctx.get("walk_time")
    if pt is not None and walk is None:
        return ("pt", round(pt))
    return None


@engine.register(
    id="R-T03",
    category=RuleCategory.TRAVEL,
    description=(
        "PT routing failed: return (None, None). "
        "Walk is not attempted as a standalone route — PT is always tried first."
    ),
    source=SOURCE,
)
def travel_pt_failed(ctx: dict):
    pt = ctx.get("pt_time")
    if pt is None:
        return (None, None)
    return None
