RFC: Decision Support System for Singapore Primary School Registration
Status: Draft
Version: 3.0
Date: 2026-04-14
Reference: System Architecture & User Flow Diagrams
SchoolFit_SG.pptx

## Change Log
- v3.0 (2026-04-14): Introduced centralized Knowledge Rule Engine (`knowledge_base/`) as a
  first-class architectural component. All business rules extracted from nodes into a declarative,
  inspectable, traceable rule registry. Nodes are now thin — they delegate to the rule engine.
  Rule traces added to pipeline state and surfaced to the LLM summarizer for grounded explanation.
  Full rule catalogue (R-F, R-P, R-S, R-A, R-T) documented.
- v2.0 (2026-04-13): Redesigned as a cognitive agent pipeline using LangGraph + LangChain.
  Switched from form-based to natural-language input. Ballot history moved from scoring
  to display-only admission metadata. New folder `schoolfit_v2/`. LLM-inferred weights added.
- v1.0 (2026-03-01): Initial draft.

---

## 1. Overview

This document proposes a decision support system to help Singaporean parents navigate the
complex P1 school registration process. The system provides a single, unified ranked list of
primary schools, ordered purely by a Fit Score that measures how well each school aligns with
a child's specific needs and family priorities.

The system is designed as a **cognitive agent pipeline**: the user provides a single natural-
language description of their child and preferences, and the system reasons through that input
step-by-step — extracting structure, applying rules, matching semantics, scoring, and finally
generating a grounded explanation — using the best technique at each stage.

At the heart of the system is a **Knowledge Rule Engine**: a centralized, declarative registry
of all domain business rules. Rules are defined once, tagged by category and source, and
evaluated by a shared engine. LangGraph nodes are thin orchestrators — they delegate all
rule evaluation to the engine. The engine records traces of which rules fired for each school,
which feeds the LLM explanation to produce fully grounded, auditable narratives.

Crucially, this system separates **school fit** from **admission profile**. The Fit Score drives
ranking. Historical ballot odds and registration phase are displayed as inline metadata on each
result card. Ballot history does NOT influence ranking.

---

## 2. Motivation

The P1 registration process is a source of significant stress for parents. They must
simultaneously evaluate school quality, personal fit (CCAs, culture, programmes), and complex
admission odds determined by registration phase, citizenship, and home distance.

Existing tools require parents to navigate separate MOE pages, manually cross-reference CCA
lists, and interpret historical ballot data themselves. This system aims to demystify the process
by codifying all decision factors — including the legally-defined MOE phase rules — into a
transparent, data-driven, and reproducible pipeline accessible through a single natural-language
input.

---

## 3. Goals

1. **Natural Language Input**: Accept a single free-text description of the child and family
   preferences. No forms, no dropdowns. The system extracts all structured parameters via LLM.

2. **Unified Ranking**: Score and rank all qualifying schools in a single list based on a
   transparent Fit Score across 11 dimensions.

3. **Inline Admission Profile**: For every school, display registration phase, historical ballot
   odds per phase, and a confidence signal (Guaranteed / Likely / Competitive / Difficult) as
   display-only metadata that does not affect rank.

4. **LLM-Inferred Weights**: The LLM infers scoring weights from the emphasis in the user's
   text. Users can review and override inferred weights before scoring runs.

5. **Centralized Knowledge Rule Engine**: All business rules live in one place — declared,
   tagged, and described. Rules are independently testable and updatable without touching
   pipeline node code.

6. **Traceable Reasoning**: The rule engine records which rules fired for each school. These
   traces are passed to the LLM summarizer, enabling grounded, rule-referenced explanations.

7. **Cognitive Agent Design**: The processing pipeline is an explicit LangGraph state machine.
   Each node does one well-defined job. The pipeline is auditable, visualizable, and handles
   errors and retries through conditional edges.

8. **Parent Autonomy**: The system provides recommendations and data. The final decision
   remains entirely with the parent.

---

## 4. System Architecture

### 4.1 Folder Structure

All new code lives in `schoolfit_v2/`. The existing `deploy/` folder is preserved as reference.

```
schoolfit_v2/
├── app.py                      # Streamlit UI — layout, state, rendering only
├── graph.py                    # LangGraph pipeline: node wiring + conditional edges
├── state.py                    # SchoolFitState TypedDict + all Pydantic schemas
│
├── knowledge_base/             # ★ Centralized Knowledge Rule Engine
│   ├── __init__.py
│   ├── rule_engine.py          # RuleEngine class, Rule + RuleTrace dataclasses
│   └── rules/
│       ├── __init__.py         # Instantiates + exports the global engine singleton
│       ├── filter_rules.py     # R-F01..R-F04 — gender and distance hard filters
│       ├── phase_rules.py      # R-P01..R-P08 — MOE P1 phase eligibility
│       ├── scoring_rules.py    # R-S01..R-S13 — per-dimension fit scores + normalization
│       ├── signal_rules.py     # R-A01..R-A05 — admission confidence signal
│       └── travel_rules.py     # R-T01..R-T03 — travel mode selection + fallback
│
├── nodes/                      # LangGraph nodes — thin orchestrators only
│   ├── extractor.py            # Node 1: LangChain LCEL — NL text → UserIntent
│   ├── validator.py            # Node 2: OneMap geocoding + postal validation
│   ├── matcher.py              # Node 3: Semantic CCA + program matching (offline)
│   ├── filter.py               # Node 4: delegates to filter_rules (R-F)
│   ├── travel.py               # Node 5: OneMap routing + delegates to travel_rules (R-T)
│   ├── scorer.py               # Node 6: delegates to scoring_rules (R-S)
│   ├── phases.py               # Node 7: delegates to phase_rules + signal_rules (R-P, R-A)
│   └── summarizer.py           # Node 8: LangChain LCEL — grounded summary with rule traces
│
├── api_clients.py              # Cached OneMap + LLM clients (@st.cache_resource)
├── data_loader.py              # Cached CSV + embedding loading (@st.cache_resource)
├── styles.py                   # CSS + HTML templates for school cards and tooltips
├── requirements.txt
├── data/                       # master.csv, ballot_history.csv, full_records.csv
└── artifacts/                  # Pre-computed CCA + program embeddings (npy + pkl)
```

### 4.2 Knowledge Rule Engine Design

The rule engine is a **decorator-based registry**. Each rule is a plain Python function
decorated with metadata. The engine evaluates rules, records traces, and can be
queried by category or ID.

```
┌─────────────────────────────────────────────────────────────┐
│                    Knowledge Rule Engine                     │
│                                                             │
│  Rule Registry                                              │
│  ┌──────────┬────────────┬─────────────────┬─────────────┐ │
│  │  Rule ID │  Category  │   Description   │   Source    │ │
│  ├──────────┼────────────┼─────────────────┼─────────────┤ │
│  │  R-F01   │  filter    │ Gender match... │ MOE Data    │ │
│  │  R-P01   │  phase     │ International.. │ MOE Policy  │ │
│  │  R-S01   │  scoring   │ Travel time...  │ System      │ │
│  │  R-A01   │  signal    │ Phase 1 = Gtd   │ System      │ │
│  │  R-T01   │  travel    │ PT vs walk...   │ System      │ │
│  └──────────┴────────────┴─────────────────┴─────────────┘ │
│                                                             │
│  engine.run(rule_id, context)  → (output, RuleTrace)       │
│  engine.run_category(cat, ctx) → [(output, RuleTrace), ...] │
│  engine.get_rules(category)    → [Rule, ...]               │
└─────────────────────────────────────────────────────────────┘
```

**Rule structure:**
```python
@dataclass
class Rule:
    id: str               # e.g. "R-P02"
    category: RuleCategory
    description: str      # human-readable explanation
    source: str           # e.g. "MOE P1 Registration Exercise Guidelines 2025"
    fn: Callable          # rule function: (context: dict) -> output | None

@dataclass
class RuleTrace:
    rule_id: str
    fired: bool           # True if rule produced a non-None output
    output: Any           # the rule's output value
    school_name: str      # which school this trace is for
    reason: str           # copied from Rule.description — for LLM explanation
```

**Rule authoring pattern** (decorator-based registration):
```python
# knowledge_base/rules/phase_rules.py

@engine.register(
    id="R-P02",
    category=RuleCategory.PHASE,
    description="Phase 1: Child qualifies if a sibling is currently enrolled "
                "in this school. No balloting applies.",
    source="MOE P1 Registration Exercise Guidelines 2025"
)
def phase_1_sibling(ctx: dict) -> str | None:
    if ctx["school_name"] in ctx["has_sibling"]:
        return "Phase 1"
    return None  # rule does not apply — engine moves to next rule
```

**Node delegation pattern** (nodes stay thin):
```python
# nodes/phases.py  — thin node, all logic in the rule engine

def compute_phases_node(state: SchoolFitState) -> dict:
    schools = state["schools_with_travel"].copy()
    all_traces = []

    def get_phase(row):
        ctx = build_rule_context(row, state["user_intent"])
        for rule in engine.get_rules(RuleCategory.PHASE):
            output, trace = engine.run(rule.id, ctx)
            all_traces.append(trace)
            if output is not None:
                return output          # first matching rule wins
        return "Phase 2C"              # default if no rule matched

    schools["phase"] = schools.apply(get_phase, axis=1)
    return {"schools_with_phases": schools, "rule_traces": state["rule_traces"] + all_traces}
```

### 4.3 Pipeline State

A single `SchoolFitState` TypedDict flows through every node. Includes `rule_traces` so
the summarizer can reference which rules fired for each school.

```python
class SchoolFitState(TypedDict):
    # Input
    user_input: str

    # Node 1: extraction
    user_intent: UserIntent | None

    # Node 2: geocoding
    coordinates: tuple[float, float, float, float] | None   # X, Y, lat, lon

    # Node 3: semantic matching
    cca_matches: list[str]
    prog_matches: list[str]

    # Node 4: filtered schools (gender + distance applied)
    filtered_schools: pd.DataFrame | None

    # Node 5: travel time added
    schools_with_travel: pd.DataFrame | None

    # Node 6: fit scores + ranking
    scored_schools: pd.DataFrame | None
    top_schools: pd.DataFrame | None

    # Node 7: phase eligibility + admission signal added
    schools_with_phases: pd.DataFrame | None

    # Rule engine traces (accumulated across all rule-using nodes: 4, 5, 6, 7)
    rule_traces: list[RuleTrace]

    # Node 8: LLM summary
    summary: str

    # Control flow
    error: str | None
    retry_count: int
```

### 4.4 LangGraph Pipeline

The rule engine is a **shared service** called by nodes 4, 5, 6, and 7. It is not itself
a node — it has no I/O latency and does not need to be an async step.

```
START
  │
  ▼
[Node 1] extract_intent
  LangChain LCEL: ChatPromptTemplate | ChatOpenAI | PydanticOutputParser(UserIntent)
  Extracts: gender, postal_code, citizenship, activities[], inferred weights,
            preferences (SAP/IP/session/MT), family context (sibling/alumni/etc.)
  │
  ▼
[Node 2] validate_geocode
  OneMap API: postal_code → (X, Y, lat, lon)
  ├─ [error edge] → END — surface error to Streamlit
  └─ [success edge] ──────────────────────────────────────────────────────┐
  │                                                                       │
  ▼ [Node 3] semantic_match  ←── offline, no API cost                    │
  sentence-transformers:                                                  │
    activities[] → CCA matches[]     (parallel)                          │
    activities[] → Program matches[] (parallel)                          │
  │                                                                       │
  ▼ [Node 4] filter_schools  ←── delegates to KNOWLEDGE RULE ENGINE      │
  Calls: engine.run_category(FILTER, ctx)                                │
  Rules: R-F01 (gender), R-F02 (gender), R-F03 (gender), R-F04 (radius) │
  ├─ [empty, retry_count = 0] → relax radius_km × 1.5, retry ───────────┘
  ├─ [empty, retry_count > 0] → END — "no schools found" message
  └─ [results found] ──────────────────────────────────────────────────────┐
  │                                                                        │
  ▼ [Node 5] compute_travel_time  ←── OneMap API + travel_rules           │
  OneMap routing per filtered school (cached per lat/lon pair)            │
  Calls: engine.run_category(TRAVEL, ctx) for mode selection              │
  Rules: R-T01 (PT wins), R-T02 (PT fallback), R-T03 (both fail)         │
  Always returns 2-tuple: (mode, minutes) or (None, None)                │
  │                                                                        │
  ▼ [Node 6] score_rank  ←── delegates to KNOWLEDGE RULE ENGINE           │
  Calls: engine.run_category(SCORING, ctx) per school                    │
  Rules: R-S01..R-S13                                                     │
  ballot_history merged for display only — not used in scoring            │
  Sorts descending → top_n schools                                        │
  │                                                                        │
  ▼ [Node 7] compute_phases  ←── delegates to KNOWLEDGE RULE ENGINE       │
  Calls: engine.run_category(PHASE, ctx) per school                      │
  Rules: R-P01..R-P08                                                     │
  Calls: engine.run_category(SIGNAL, ctx) per school + phase             │
  Rules: R-A01..R-A05                                                     │
  Appends all RuleTraces to state.rule_traces                             │
  │                                                                        │
  ▼ [Node 8] generate_summary  ←── LangChain LCEL                         │
  Input: top_schools score breakdown + rule_traces                        │
  LLM explains recommendations referencing which rules fired              │
  Output: grounded 3–5 bullet factual summary                            │
  │
  ▼
END → return SchoolFitState to Streamlit for rendering
```

### 4.5 Conditional Edges Summary

| From Node | Condition | To Node |
|---|---|---|
| validate_geocode | geocoding API error | END (show error) |
| validate_geocode | invalid postal format | END (show error) |
| filter_schools | schools found | compute_travel_time |
| filter_schools | empty, retry_count = 0 | filter_schools (radius × 1.5) |
| filter_schools | empty, retry_count > 0 | END ("no schools in area") |

---

## 5. Knowledge Rule Catalogue

All rules registered in the engine. Each rule has a stable ID that appears in rule traces
and can be referenced in LLM explanations.

### Category R-F — Filter Rules
Applied by: Node 4 (filter.py)

| Rule ID | Description | Source |
|---|---|---|
| R-F01 | Boys' school (`BOYS' SCHOOL`): admit only male gender | MOE School Data |
| R-F02 | Girls' school (`GIRLS' SCHOOL`): admit only female gender | MOE School Data |
| R-F03 | Co-ed school (`CO-ED SCHOOL`): admit all genders | MOE School Data |
| R-F04 | Distance hard filter: school must be within `radius_km` of user's home | System |

### Category R-P — Phase Eligibility Rules
Applied by: Node 7 (phases.py). Rules evaluated in priority order; first match wins.

| Rule ID | Description | Source |
|---|---|---|
| R-P01 | International citizen → Phase 3 (no distance priority) | MOE P1 Guidelines |
| R-P02 | Has sibling currently enrolled in this school → Phase 1 (Guaranteed) | MOE P1 Guidelines |
| R-P03 | Parent is alumni, OR parent is current staff, OR child is in school's MOE Kindergarten, OR older sibling previously attended → Phase 2A + distance suffix | MOE P1 Guidelines |
| R-P04 | Parent is active volunteer at this school, OR school is affiliated with parent's church/clan → Phase 2B + distance suffix | MOE P1 Guidelines |
| R-P05 | Parent is endorsed community leader AND home is within 2 km → Phase 2B + distance suffix | MOE P1 Guidelines |
| R-P06 | All other Singapore Citizens and PRs → Phase 2C + distance suffix | MOE P1 Guidelines |
| R-P07 | Distance suffix for SC: <1 km → `-1`, 1–2 km → `-2`, >2 km → `-3` | MOE P1 Guidelines |
| R-P08 | Distance suffix for PR: offset +3 → `-4`, `-5`, `-6` | MOE P1 Guidelines |

### Category R-S — Scoring Rules
Applied by: Node 6 (scorer.py).

| Rule ID | Dimension | Score Logic |
|---|---|---|
| R-S01 | Travel Time | `1 − MinMaxNorm(travel_minutes)` — lower travel → higher score |
| R-S02 | CCA Match | `MinMaxNorm(len(user_ccas ∩ school_ccas))` |
| R-S03 | Program Match | `MinMaxNorm(len(user_progs ∩ school_progs))` |
| R-S04 | PSLE Tier | Ordinal map: `{1: 1.0, 2: 0.75, 3: 0.5, 4: 0.25}`, default 0 |
| R-S05 | Sports NSG | `MinMaxNorm(len(user_sports ∩ school_nsg[gender]))` |
| R-S06 | Arts SYF | `MinMaxNorm(len(user_arts ∩ school_syf))` |
| R-S07 | Session Type | Binary: `1` if school session == preference, else `0`. Skip if no preference. |
| R-S08 | SAP School | Binary: `1` if school SAP status == preference, else `0`. Skip if no preference. |
| R-S09 | Autonomous | Binary: `1` if school autonomous status == preference. Skip if no preference. |
| R-S10 | IP School | Binary: `1` if school IP status == preference. Skip if no preference. |
| R-S11 | Mother Tongue | `1` if preference is non-empty AND preferred MT is offered by school. Guard: `preference and preference in school_mts` |
| R-S12 | Weight normalization | `norm_w = w / sum(w)` if `sum(w) > 0`, else uniform. Applied before dot product. |
| R-S13 | Fit score | `fit_score = 100 × Σ(norm_w_i × score_i)` for all dimensions where `w_i > 0` |

### Category R-A — Admission Signal Rules
Applied by: Node 7 (phases.py), after phase is determined.

| Rule ID | Signal | Condition |
|---|---|---|
| R-A01 | Guaranteed | Phase 1 (sibling in school) |
| R-A02 | Likely | Phase 1 non-sibling, OR historical ballot odds ≥ 70% for user's phase+suffix |
| R-A03 | Competitive | 40% ≤ historical ballot odds < 70% |
| R-A04 | Difficult | Historical ballot odds < 40% |
| R-A05 | Unknown | No historical ballot data available for this school/phase combination |

### Category R-T — Travel Rules
Applied by: Node 5 (travel.py).

| Rule ID | Description |
|---|---|
| R-T01 | If both PT and walk routing succeed → use whichever has the lower travel time |
| R-T02 | If PT routing succeeds but walk routing fails → use PT result (do not discard) |
| R-T03 | If PT routing fails → return `(None, None)`; do not attempt walk as standalone |

---

## 6. Fit Scoring & Admission Profile

### 6.1 Fit Score (Used for Ranking)

A normalized, weighted average across 11 dimensions (rules R-S01..R-S13). Weights are
LLM-inferred from the user's natural-language input and can be overridden via UI sliders.

```
fit_score = 100 × Σ (norm_weight_i × score_i)   for all i where weight_i > 0
```

Weights are normalized to sum to 1 before the dot product (R-S12).

### 6.2 Admission Profile (Display-Only Metadata — Does NOT Affect Ranking)

Displayed as inline metadata on each school result card. Never used in fit_score calculation.

| Field | Source | Rule(s) |
|---|---|---|
| Registration Phase | Phase rule engine | R-P01..R-P08 |
| Historical Ballot Odds | ballot_history.csv | — (raw data) |
| Confidence Signal | Derived from ballot odds + phase | R-A01..R-A05 |

Phase column suffix encodes citizenship × distance bracket (R-P07, R-P08):
`Phase 2A-1` = Phase 2A, SC, within 1 km.
`Phase 2B-5` = Phase 2B, PR, 1–2 km.

---

## 7. Implementation Plan

| Phase | Milestone | Description | Priority |
|---|---|---|---|
| 1. Foundation | Folder + State | Create `schoolfit_v2/`, define `SchoolFitState`, `UserIntent`, `api_clients.py` with `@st.cache_resource` for OneMap token and LLM client | High |
| | Knowledge Rule Engine | Build `rule_engine.py`: `RuleEngine`, `Rule`, `RuleTrace`. Implement `register()` decorator, `run()`, `run_category()`, `get_rules()`. | High |
| | Rule Authoring | Author all rules in `filter_rules.py`, `phase_rules.py`, `scoring_rules.py`, `signal_rules.py`, `travel_rules.py`. Unit-test each rule independently. | High |
| | LangGraph Skeleton | Wire all 8 nodes + conditional edges in `graph.py`. Nodes return stub data initially. | High |
| 2. Core Nodes | Extractor (Node 1) | LangChain LCEL: NL → UserIntent. LLM infers weights from text emphasis. | High |
| | Validator (Node 2) | OneMap geocoding + postal code validation + error edge. | High |
| | Matcher (Node 3) | Port semantic CCA + program matching from `deploy/search_retrieve.py`. | High |
| | Filter (Node 4) | Thin node. Delegate gender + distance logic to R-F rules. Radius retry via conditional edge. | High |
| | Travel (Node 5) | OneMap routing per school. Delegate mode selection to R-T rules. Cache per lat/lon pair. | High |
| | Scorer (Node 6) | Thin node. Delegate all 11 scoring dimensions to R-S rules. Merge ballot_history for display. | High |
| | Phases (Node 7) | Thin node. Delegate phase to R-P rules, signal to R-A rules. Accumulate all traces into state. | High |
| 3. UI + Summary | Streamlit UI | Single NL text input. "Review & Adjust" expander with pre-filled weight sliders. School cards + Folium map. Ballot odds table + signal badge on each card. | High |
| | Summarizer (Node 8) | LangChain LCEL summary chain. Grounded on score breakdown + rule traces. 3–5 factual bullets. | Medium |
| 4. Polish | Error UX | Surface geocoding errors, no-schools-found, API failures cleanly in Streamlit. | Medium |
| | Rule Introspection | Add a debug/info sidebar panel showing which rules were registered and which fired. | Low |
| | Data Refresh Pipeline | Document annual refresh process for master.csv, ballot_history.csv, embeddings, rule sources. | Low |

---

## 8. Reasoning Subsystem: A Hybrid Cognitive Architecture

The system uses five distinct reasoning techniques. The Knowledge Rule Engine unifies
three of them (filtering, phase logic, scoring, signal derivation) under one auditable roof.
LangGraph makes the interaction between all techniques explicit.

| Technique | Applied To | Component | Why |
|---|---|---|---|
| LLM Extraction (LangChain LCEL) | User Preference Parsing + Weight Inference | Node 1 (extractor.py) | LLMs handle ambiguous natural language. Pydantic structured output ensures reliable extraction. |
| Knowledge Rule Engine | Filtering, Phase Eligibility, Fit Scoring, Admission Signal | Nodes 4, 6, 7 via `knowledge_base/` | All deterministic domain logic lives in one place. Rules are declared, tagged, sourced, and independently testable. Traces enable grounded LLM explanations. |
| Probabilistic Display | Admission Odds | Node 7 (signal_rules.py + ballot_history.csv) | Balloting is stochastic. Historical recency-weighted data is the most honest model of admission chances. Displayed as metadata — never distorts the fit ranking. |
| KB Taxonomy + Semantic Matching | CCA & Programme Score | Node 3 (matcher.py) | Sentence-transformer embeddings handle synonym and domain matching without runtime LLM cost. Fast, offline, explainable. |
| LLM Summarization (LangChain LCEL) | Recommendation Explanation | Node 8 (summarizer.py) | LLMs generate clear, grounded narratives. Summary is strictly grounded on score breakdown + rule traces to prevent hallucination. |

### Why LangGraph

LangGraph is used as the pipeline orchestrator because:

1. **Explicit state**: `SchoolFitState` is the single source of truth passed between nodes.
   No global variables, no hidden side effects.
2. **Auditable transitions**: Every step is a named node. The graph can be visualized,
   logged, and debugged node-by-node.
3. **Conditional control flow**: Retry logic (relax radius), error handling (bad postal code),
   and graceful degradation are modeled as graph edges — not buried in if/else chains.
4. **Separation of concerns**: Each node is independently testable with a mock state input.
   Nodes are thin — all business logic lives in the rule engine or the LangChain chains.

---

## 9. Key Design Decisions & Rationale

| Decision | Rationale |
|---|---|
| Centralized Knowledge Rule Engine | In v1, rules were scattered across 3+ files with no single home. Centralizing them makes the system inspectable ("what rules does this system know?"), updatable (change a rule without touching nodes), and traceable (which rule determined this school's phase?). |
| Decorator-based rule registry | Rules are plain Python functions — easy to test, read, and author. The decorator attaches metadata without polluting the function body. |
| Rule traces in pipeline state | Passing traces to the LLM summarizer means explanations can reference specific rules that fired (e.g., "R-P03 fired: parent is staff → Phase 2A"), not just generic descriptions. |
| New folder `schoolfit_v2/` | Preserves the working v1 reference. Clean slate avoids inheriting structural debt. |
| Ballot history display-only | Conflating admission probability with fit score answers two different questions with one number. Parents should see both dimensions independently. |
| LLM infers weights from NL | Users don't think in slider percentages. "Most important thing is she's close to home" is a natural weight signal. Sliders remain available for manual override. |
| sentence-transformers run offline | CCA + program matching runs against pre-computed embeddings with no runtime API cost. Avoids LLM latency for a deterministic matching task. |
| OneMap for routing, not straight-line distance | A school 0.8 km away with poor transit connectivity may take 30 minutes. Travel time is a more accurate proxy than Euclidean distance. |
| R-T02: PT fallback when walk fails | v1 bug: if walk routing failed, the PT result was discarded and the function returned None. R-T02 explicitly preserves the PT result as a fallback. |
