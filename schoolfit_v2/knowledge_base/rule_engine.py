"""
Knowledge Rule Engine for SchoolFit v2.

All domain business rules are registered here via the @engine.register() decorator.
Rules are plain Python functions: (context: dict) -> output | None
Returning None means the rule does not apply to this context (engine skips it).

Usage:
    from knowledge_base.rule_engine import engine, RuleCategory

    # Register a rule
    @engine.register(id="R-P02", category=RuleCategory.PHASE, description="...", source="...")
    def phase_1_sibling(ctx: dict) -> str | None:
        if ctx["school_name"] in ctx["has_sibling"]:
            return "Phase 1"
        return None

    # Evaluate: first-match (phase, signal, travel)
    output, traces = engine.run_first_match(RuleCategory.PHASE, context)

    # Evaluate: all-match (filter — all rules must pass)
    outputs, traces = engine.run_all(RuleCategory.FILTER, context)

    # Inspect
    print(engine.describe())
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


# =============================================================================
# Enums & data classes
# =============================================================================

class RuleCategory(str, Enum):
    FILTER  = "filter"
    PHASE   = "phase_eligibility"
    SCORING = "scoring"
    SIGNAL  = "admission_signal"
    TRAVEL  = "travel"


@dataclass
class Rule:
    id: str
    category: RuleCategory
    description: str
    source: str
    fn: Callable[[dict], Any]


@dataclass
class RuleTrace:
    rule_id: str
    category: str
    fired: bool
    output: Any
    school_name: str
    reason: str


# =============================================================================
# Rule Engine
# =============================================================================

class RuleEngine:
    """
    Centralized, decorator-based knowledge rule registry.
    Rules are registered in the order their modules are imported.
    """

    def __init__(self) -> None:
        self._rules: dict[str, Rule] = {}

    # ── Registration ─────────────────────────────────────────────────────────

    def register(
        self,
        id: str,
        category: RuleCategory,
        description: str,
        source: str = "System",
    ) -> Callable:
        """Decorator factory — attaches metadata and adds the function to the registry."""
        def decorator(fn: Callable) -> Callable:
            self._rules[id] = Rule(
                id=id,
                category=category,
                description=description,
                source=source,
                fn=fn,
            )
            return fn
        return decorator

    # ── Inspection ────────────────────────────────────────────────────────────

    def get_rules(self, category: Optional[RuleCategory] = None) -> list[Rule]:
        rules = list(self._rules.values())
        if category:
            rules = [r for r in rules if r.category == category]
        return rules

    def describe(self, category: Optional[RuleCategory] = None) -> str:
        """Human-readable summary of all registered rules."""
        lines: list[str] = []
        cats = [category] if category else list(RuleCategory)
        for cat in cats:
            cat_rules = self.get_rules(cat)
            if cat_rules:
                lines.append(f"\n[{cat.value.upper()}]")
                for r in cat_rules:
                    lines.append(f"  {r.id}: {r.description}")
                    lines.append(f"         Source: {r.source}")
        return "\n".join(lines)

    # ── Evaluation ────────────────────────────────────────────────────────────

    def _run_one(self, rule: Rule, context: dict) -> tuple[Any, RuleTrace]:
        output = rule.fn(context)
        return output, RuleTrace(
            rule_id=rule.id,
            category=rule.category.value,
            fired=(output is not None),
            output=output,
            school_name=context.get("school_name", ""),
            reason=rule.description,
        )

    def run_first_match(
        self, category: RuleCategory, context: dict
    ) -> tuple[Any, list[RuleTrace]]:
        """
        Evaluate rules in registration order; return the first non-None output.
        Used for mutually exclusive outcomes: PHASE, SIGNAL, TRAVEL.
        """
        traces: list[RuleTrace] = []
        for rule in self.get_rules(category):
            output, trace = self._run_one(rule, context)
            traces.append(trace)
            if output is not None:
                return output, traces
        return None, traces

    def run_all(
        self, category: RuleCategory, context: dict
    ) -> tuple[list[Any], list[RuleTrace]]:
        """
        Evaluate every rule in the category; collect all non-None outputs.
        Used for FILTER (all rules must pass) and SCORING (all dimensions evaluated).
        """
        outputs: list[Any] = []
        traces: list[RuleTrace] = []
        for rule in self.get_rules(category):
            output, trace = self._run_one(rule, context)
            traces.append(trace)
            if output is not None:
                outputs.append(output)
        return outputs, traces


# =============================================================================
# Global singleton — imported by all rule modules and nodes
# =============================================================================
engine = RuleEngine()
