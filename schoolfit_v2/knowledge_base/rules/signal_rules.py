"""
Admission Signal Rules (R-A) — applied by Node 7 (phases.py).

Rules are evaluated in registration order; the first match wins.
Each rule returns a signal string ("Guaranteed", "Likely", "Competitive",
"Difficult", "Unknown") or None (rule does not apply).

Context keys:
    phase (str): determined phase, e.g. "Phase 1", "Phase 2C-1"
    ballot_odds (float | None): historical admission % for this phase+suffix, 0–100
"""
from knowledge_base.rule_engine import engine, RuleCategory

SOURCE = "System / MOE Historical Ballot Data"


@engine.register(
    id="R-A01",
    category=RuleCategory.SIGNAL,
    description=(
        "Guaranteed: Child has a sibling in this school (Phase 1). "
        "Admission is guaranteed — no balloting."
    ),
    source=SOURCE,
)
def signal_guaranteed(ctx: dict):
    if ctx.get("phase") == "Phase 1":
        return "Guaranteed"
    return None


@engine.register(
    id="R-A02",
    category=RuleCategory.SIGNAL,
    description=(
        "Likely: Historical ballot odds for this school/phase are ≥ 70%. "
        "Most applicants in this phase were admitted historically."
    ),
    source=SOURCE,
)
def signal_likely(ctx: dict):
    odds = ctx.get("ballot_odds")
    if odds is not None and odds >= 70:
        return "Likely"
    return None


@engine.register(
    id="R-A03",
    category=RuleCategory.SIGNAL,
    description=(
        "Competitive: Historical ballot odds are between 40% and 70%. "
        "Admission is possible but not certain."
    ),
    source=SOURCE,
)
def signal_competitive(ctx: dict):
    odds = ctx.get("ballot_odds")
    if odds is not None and 40 <= odds < 70:
        return "Competitive"
    return None


@engine.register(
    id="R-A04",
    category=RuleCategory.SIGNAL,
    description=(
        "Difficult: Historical ballot odds are below 40%. "
        "The school is oversubscribed in this phase historically."
    ),
    source=SOURCE,
)
def signal_difficult(ctx: dict):
    odds = ctx.get("ballot_odds")
    if odds is not None and odds < 40:
        return "Difficult"
    return None


@engine.register(
    id="R-A05",
    category=RuleCategory.SIGNAL,
    description=(
        "Unknown: No historical ballot data is available for this school and phase. "
        "Cannot estimate admission probability."
    ),
    source=SOURCE,
)
def signal_unknown(ctx: dict):
    # Default — always fires if no earlier rule matched
    return "Unknown"
