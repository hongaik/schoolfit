"""
Knowledge base package.
Importing this package triggers registration of all rules into the global engine singleton.
"""
from knowledge_base.rule_engine import engine, RuleCategory, RuleTrace  # re-export

# Import rule modules to register their rules into the engine.
# Order matters for first-match categories (PHASE, SIGNAL, TRAVEL).
from knowledge_base.rules import filter_rules   # noqa: F401
from knowledge_base.rules import phase_rules    # noqa: F401
from knowledge_base.rules import scoring_rules  # noqa: F401
from knowledge_base.rules import signal_rules   # noqa: F401
from knowledge_base.rules import travel_rules   # noqa: F401

__all__ = ["engine", "RuleCategory", "RuleTrace"]
