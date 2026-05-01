RFC: Decision Support System for Singapore Primary School Registration
Status: Active
Version: 4.0
Date: 2026-04-19
Reference: System Architecture & User Flow Diagrams

## Change Log
- v4.0 (2026-04-19): Migrated to form-based input. Semantic CCA/programme search moved to
  sidebar UI layer (input_helpers.py). LLM retained only for bonus free-text extraction. Node 3
  renamed to `derive_matches` — it derives sports/arts subsets, not semantic search. Added full
  scoring formula documentation (R-S12, R-S13). Data files moved to schoolfit_v2/data/.
  Auto-bump logic for binary preference weights documented.
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
primary schools, ordered purely by a **Fit Score** that measures how well each school aligns
with a child's specific needs and family priorities.

The system is designed as a **cognitive agent pipeline**: the user fills a structured sidebar
form, and the system reasons through that input step-by-step — extracting structure, applying
rules, scoring, and generating a grounded explanation. A **semantic search layer** in the sidebar
UI helps users discover CCA and programme matches before submitting the form. An optional
**bonus text box** accepts free-form preferences that are parsed by an LLM.

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
transparent, data-driven, and reproducible pipeline accessible through a structured form with
natural-language bonus input.

---

## 3. Goals

1. **Structured + Natural Language Input**: Accept key details via form (gender, postal code,
   citizenship, interests, weights) and an optional free-text bonus box. The system extracts
   structured preferences from the bonus text via LLM. Semantic search in the sidebar suggests
   CCA and programme matches as the user types.

2. **Unified Ranking**: Score and rank all qualifying schools in a single list based on a
   transparent Fit Score across 11 dimensions.

3. **Inline Admission Profile**: For every school, display registration phase, historical ballot
   odds per phase, and a confidence signal (Guaranteed / Likely / Competitive / Difficult) as
   display-only metadata that does not affect rank.

4. **User-Controlled Weights**: Users set scoring weights via sliders (0–5 scale per dimension).
   Auto-bump logic: if the bonus text LLM extracts a binary preference (e.g. SAP preferred) but
   the corresponding slider is still at 0, the weight is automatically set to 3 so the preference
   actually affects scoring.

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

All v2 code lives in `schoolfit_v2/`. Static data and precomputed embeddings live under
`schoolfit_v2/data/` (`data/artifacts/` holds `.npy` / `.pkl` / `.json` used for semantic search).

```
schoolfit/
├── schoolfit_v2/
│   ├── app.py                      # Streamlit UI — layout, state, rendering only
│   ├── graph.py                    # LangGraph pipeline: node wiring + conditional edges
│   ├── state.py                    # SchoolFitState TypedDict + UserIntent Pydantic schema
│   ├── input_helpers.py            # Sidebar semantic CCA/programme search (not in pipeline)
│   ├── input_validator.py          # Form validation + LLM bonus text extraction
│   │
│   ├── knowledge_base/             # ★ Centralized Knowledge Rule Engine
│   │   ├── __init__.py
│   │   ├── rule_engine.py          # RuleEngine class, Rule + RuleTrace dataclasses
│   │   └── rules/
│   │       ├── __init__.py         # Instantiates + exports the global engine singleton
│   │       ├── filter_rules.py     # R-F01..R-F03 — gender and distance hard filters
│   │       ├── phase_rules.py      # R-P01..R-P06 — MOE P1 phase eligibility
│   │       ├── scoring_rules.py    # R-S01..R-S13 — per-dimension fit scores + normalisation
│   │       ├── signal_rules.py     # R-A01..R-A05 — admission confidence signal
│   │       └── travel_rules.py     # R-T01..R-T03 — travel mode selection + fallback
│   │
│   ├── nodes/                      # LangGraph nodes — thin orchestrators only
│   │   ├── extractor.py            # Node 1: form data → UserIntent (LLM for bonus text only)
│   │   ├── validator.py            # Node 2: OneMap geocoding + postal validation
│   │   ├── matcher.py              # Node 3: derive sports/arts subsets from CCA selections
│   │   ├── filter.py               # Node 4: delegates to filter_rules (R-F)
│   │   ├── travel.py               # Node 5: OneMap routing + delegates to travel_rules (R-T)
│   │   ├── scorer.py               # Node 6: delegates to scoring_rules (R-S)
│   │   ├── phases.py               # Node 7: delegates to phase_rules + signal_rules (R-P, R-A)
│   │   └── summarizer.py           # Node 8: LangChain LCEL — grounded summary
│   │
│   ├── api_clients.py              # Cached OneMap + LLM clients (@st.cache_resource)
│   ├── data_loader.py              # Cached CSV + embedding loading (@st.cache_resource)
│   ├── styles.py                   # CSS + HTML templates for school cards and tooltips
│   ├── requirements.txt
│   └── data/
│       ├── master.csv, ballot_history.csv, full_records.csv
│       └── artifacts/               # Pre-computed embeddings (.npy, .pkl, .json)
│           ├── cca_vectors.npy
│           ├── cca_names.pkl
│           ├── alp_llp_vectors.npy
│           ├── alp_llp_domains.pkl
│           └── alp_llp.json
└── .streamlit/                     # secrets.toml (local)
```

### 4.2 Input Layer Architecture

The input flow is split across two layers: the **Streamlit sidebar UI** and the **pipeline**.
Semantic search runs entirely in the UI — the pipeline receives exact selections only.

```
┌─────────────────────────────────────────────────────────────────────┐
│  Streamlit Sidebar — input_helpers.py + app.py                      │
│                                                                     │
│  1. Structured inputs:                                              │
│     - Postal code, gender, citizenship, radius, top_n               │
│     - Weight sliders (0–5) for each of the 11 scoring dimensions   │
│                                                                     │
│  2. Semantic CCA search (input_helpers.find_similar_cca()):         │
│     - User types interest text (e.g. "singing, team sports")       │
│     - SentenceTransformer encodes query against cca_vectors.npy     │
│     - Returns top 10 matches (name, similarity score 0–1)          │
│     - User selects from multiselect — exact names go to form        │
│                                                                     │
│  3. Semantic programme search (find_similar_prog()):                │
│     - Same as CCA, uses alp_llp_vectors.npy                        │
│     - Stricter threshold (50% vs 30% of top score)                 │
│     - Filters out "GENERAL HOLISTIC DEVELOPMENT"                    │
│                                                                     │
│  4. Bonus text box (free-form):                                     │
│     - input_validator.parse_bonus_preferences() — LLM extraction   │
│     - Extracts: SAP/IP/session/MT, sibling, alumni, staff,         │
│       volunteer, church/clan, community leader                      │
│     - Auto-bump: if LLM extracts a preference but slider = 0,      │
│       weight is auto-set to 3                                       │
│     - Auto-default: if slider > 0 but no bonus text value,         │
│       SAP/Autonomous/IP default to "Y" so scoring rule activates   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ form_data (dict with exact selections)
                              ▼
┌────────────────────────────────┐
│  LangGraph Pipeline (8 nodes)  │
│  See §4.4                      │
└────────────────────────────────┘
```

### 4.3 Knowledge Rule Engine Design

The rule engine is a **decorator-based registry**. Each rule is a plain Python function
decorated with metadata. The engine evaluates rules, records traces, and can be
queried by category.

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
│  engine.run_first_match(cat, ctx) → (output, [RuleTrace])  │
│  engine.run_all(cat, ctx)         → (outputs, [RuleTrace]) │
│  engine.get_rules(category)       → [Rule, ...]            │
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
    category: str
    fired: bool           # True if rule produced a non-None output
    output: Any           # the rule's output value
    school_name: str      # which school this trace is for
    reason: str           # copied from Rule.description — for LLM explanation
```

**Rule authoring pattern:**
```python
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

### 4.4 LangGraph Pipeline

```
START
  │
  ▼
[Node 1] extract_intent
  Checks if UserIntent already pre-built (app passes it to skip LLM re-call)
  Cold path: calls build_user_intent() → validates form fields, runs LLM bonus extraction
  Returns: user_intent, coordinates
  ├─ [error edge] → END
  └─ [success edge]
  │
  ▼
[Node 2] validate_geocode
  OneMap API: postal_code → (X, Y, lat, lon) SVY21 + WGS84
  ├─ [error edge] → END
  └─ [success edge]
  │
  ▼
[Node 3] derive_matches   ← NO semantic search (already done in sidebar)
  Reads exact CCA and programme selections from state (cca_matches, prog_matches)
  Derives sports_matches (CCA names in NSG list) and arts_matches (CCA names in SYF list)
  These subsets are used by R-S05 and R-S06 for sports/arts excellence scoring
  │
  ▼
[Node 4] filter_schools   ← delegates to KNOWLEDGE RULE ENGINE
  Computes SVY21 distance for each school in master.csv
  Runs engine.run_all(FILTER, ctx) per school — rules R-F01, R-F02, R-F03
  Records filter_exclusion_log: which rule excluded which school
  ├─ [empty, retry_count < 2] → relax radius × 1.5 (cap 12 km), loop back
  ├─ [empty, retry_count ≥ 2] → END
  └─ [results found]
  │
  ▼
[Node 5] compute_travel_time   ← OneMap routing + travel_rules
  Per filtered school: PT route + walk route via OneMap API
  Module-level cache: (u_lat, u_lon, s_lat, s_lon) → (mode, minutes)
  Runs engine.run_first_match(TRAVEL, ctx) for mode selection (R-T01..R-T03)
  Falls back to distance-based estimate in scorer if API fails
  │
  ▼
[Node 6] score_rank   ← delegates to KNOWLEDGE RULE ENGINE
  Runs all 11 scoring dimensions (R-S01..R-S11) — see §5.3 for full formula
  R-S12: normalises weights to sum to 1
  R-S13: fit_score = 100 × Σ(norm_weight_i × score_i)
  Merges ballot_history (display only — never affects score)
  Sorts descending → top-N schools
  │
  ▼
[Node 7] compute_phases   ← delegates to KNOWLEDGE RULE ENGINE
  Per top-N school: engine.run_first_match(PHASE, ctx) → R-P01..R-P06
  Per school: engine.run_first_match(SIGNAL, ctx) → R-A01..R-A05
  Uses ballot_history columns (e.g. "Phase 2C-1") for admission odds
  │
  ▼
[Node 8] generate_summary   ← LangChain LCEL
  ChatOpenAI gpt-4o-mini: score breakdown + dimension descriptions → 3–5 bullet narrative
  Grounded strictly on actual data (travel times, CCA counts, tier, phase)
  │
  ▼
END → return SchoolFitState to Streamlit for rendering
```

### 4.5 Pipeline State

```python
class SchoolFitState(TypedDict):
    # ── Input ──────────────────────────────────────────────
    form_data: Optional[dict]           # form field values from sidebar

    # ── Node 1: intent ─────────────────────────────────────
    user_intent: Optional[UserIntent]

    # ── Node 2: geocoding ──────────────────────────────────
    coordinates: Optional[tuple]        # (X, Y, lat, lon) SVY21 + WGS84

    # ── Node 3: derive_matches ─────────────────────────────
    cca_matches: list[str]              # exact CCA names from form
    prog_matches: list[str]             # exact programme names from form
    cca_match_scores: list[float]       # sidebar similarity scores (aligned)
    prog_match_scores: list[float]      # sidebar similarity scores (aligned)
    sports_matches: list[str]           # subset of cca_matches in NSG list
    arts_matches: list[str]             # subset of cca_matches in SYF list

    # ── Node 4: filtering ──────────────────────────────────
    filtered_schools: Optional[Any]     # pd.DataFrame
    filter_exclusion_log: dict          # {rule_id: [(school_name, reason)]}

    # ── Node 5: travel ─────────────────────────────────────
    schools_with_travel: Optional[Any]  # pd.DataFrame + travel_mode, travel_time

    # ── Node 6: scoring ────────────────────────────────────
    top_schools: Optional[Any]          # pd.DataFrame, top-N ranked by score_total

    # ── Node 7: phases ─────────────────────────────────────
    schools_with_phases: Optional[Any]  # pd.DataFrame + phase, admission_signal

    # ── Rule traces ────────────────────────────────────────
    rule_traces: list                   # accumulated from nodes 4, 5, 6, 7

    # ── Node 8: summary ────────────────────────────────────
    summary: str

    # ── Control flow ───────────────────────────────────────
    error: Optional[str]
    retry_count: int
```

**UserIntent key fields:**
- Demographics: `gender` (M/F), `postal_code`, `citizenship` (SC/PR/International)
- Selections: `activities[]`, `prefer_same_gender_school`, `top_n`, `radius_km`
- Weights (0–5 scale): `w_dist`, `w_cca`, `w_prog`, `w_psle_tier`, `w_sports`, `w_arts`,
  `w_session`, `w_sap`, `w_autonomous`, `w_ip`, `w_mt`
- Characteristics: `session`, `sap`, `autonomous`, `ip`, `mother_tongue`
- Family: `has_sibling[]`, `former_student[]`, `is_alumni[]`, `is_staff[]`, `is_mk[]`,
  `is_volunteer[]`, `is_church_clan[]`, `is_community_leader`

### 4.6 Conditional Edges

| From Node | Condition | To Node |
|---|---|---|
| extract_intent | error building intent | END (show error) |
| validate_geocode | API error or invalid postal | END (show error) |
| filter_schools | schools found | compute_travel_time |
| filter_schools | empty, retry_count < 2 | filter_schools (radius × 1.5, cap 12 km) |
| filter_schools | empty, retry_count ≥ 2 | END ("no schools in area") |

---

## 5. Knowledge Rule Catalogue

30 rules total across 5 categories.

### 5.1 Category R-F — Filter Rules (3 rules)
Applied by: Node 4 (filter.py) using `engine.run_all(FILTER, ctx)`.
**All rules must fire** (return non-None) for a school to pass. First failed rule per school
is recorded in `filter_exclusion_log`.

| Rule ID | Description | Source |
|---|---|---|
| R-F01 | Gender match: school's nature_code must include child's gender (M/F/MF) | MOE School Data |
| R-F02 | Distance filter: school must be within `effective_radius_km` of user's home (SVY21 Euclidean) | System |
| R-F03 | Same-gender preference: if `prefer_same_gender_school=True`, exclude co-ed (MF) schools | System |

### 5.2 Category R-P — Phase Eligibility Rules (6 rules)
Applied by: Node 7 (phases.py) using `engine.run_first_match(PHASE, ctx)`.
Evaluated in priority order; first match wins. Default if no rule matches: Phase 2C.

Distance suffix encoding (appended to phases 2A, 2B, 2C):
- SC: dist ≤ 1 km → `-1`, 1–2 km → `-2`, > 2 km → `-3`
- PR: same brackets offset by +3 → `-4`, `-5`, `-6`

| Rule ID | Condition | Phase Returned |
|---|---|---|
| R-P01 | Citizenship is International | "Phase 3" |
| R-P02 | Sibling currently enrolled in this school | "Phase 1" |
| R-P03 | Parent is alumni OR parent is staff OR child attends MOE KG OR older sibling formerly attended | "Phase 2A{suffix}" |
| R-P04 | Parent is active volunteer (≥40 hrs) OR school affiliated with parent's church/clan | "Phase 2B{suffix}" |
| R-P05 | Parent is endorsed community leader AND dist ≤ 2 km | "Phase 2B{suffix}" |
| R-P06 | All SC/PR (default) | "Phase 2C{suffix}" |

**Examples:** `Phase 2A-1` = Phase 2A, SC, ≤ 1 km. `Phase 2B-5` = Phase 2B, PR, 1–2 km.

### 5.3 Category R-S — Scoring Rules (11 dimensions + 2 meta-rules)
Applied by: Node 6 (scorer.py).

#### Scoring Formula

The fit score is a **normalised weighted dot product** across 11 scoring dimensions.

**Step 1 — Collect raw values**

For each school and each dimension:
```
if normalisation == "binary":
    raw_value = dim.binary_fn(school_row, scoring_ctx)   → 0 or 1

if normalisation == "minmax" or "ordinal":
    raw_value = dim.raw_fn(school_row, scoring_ctx)      → float
```

**Step 2 — Normalise per dimension (R-S01..R-S11)**

```
if normalisation == "minmax":
    raw_values = [raw_value for all N schools in batch]
    if max(raw_values) > min(raw_values):
        norm_values = MinMaxScaler().fit_transform(raw_values)   → [0, 1]
    else:
        norm_values = [0.0, ..., 0.0]                            → all zero if no variation
    score_i = (1 − norm_values) if dim.invert else norm_values   → inverted for travel time

if normalisation == "ordinal":
    score_i = ordinal_map.get(raw_value, 0.0)   → lookup in fixed mapping

if normalisation == "binary":
    score_i = float(raw_value)   → already 0.0 or 1.0
```

**Step 3 — Normalise weights (R-S12)**

```
raw_weights = [intent.w_dist, intent.w_cca, intent.w_prog, intent.w_psle_tier,
               intent.w_sports, intent.w_arts, intent.w_session, intent.w_sap,
               intent.w_autonomous, intent.w_ip, intent.w_mt]

norm_weights = raw_weights / sum(raw_weights)   if sum > 0
             = raw_weights                      otherwise
```

**Step 4 — Final fit score (R-S13)**

```
score_matrix = shape (N_schools, 11)   # each column is one dimension's scores
score_total  = 100 × score_matrix · norm_weights   # dot product, one value per school
```

Only dimensions with `weight > 0` contribute to the final score.
Score range: 0–100.

**Example** (4 equal-weight dimensions, school with scores [0.8, 0.6, 0.4, 1.0]):
```
raw_weights = [3, 3, 3, 3, 0, 0, 0, 0, 0, 0, 0]
norm_weights = [0.25, 0.25, 0.25, 0.25, 0, ...]
score_total  = 100 × (0.8×0.25 + 0.6×0.25 + 0.4×0.25 + 1.0×0.25)
             = 100 × 0.70 = 70.0
```

#### Dimension Specifications

| Rule ID | Name | Weight Attr | Normalisation | Raw Value | Logic |
|---|---|---|---|---|---|
| R-S01 | Travel Time | w_dist | minmax (inverted) | Minutes (OneMap routing, or dist × 12 as fallback) | Lower travel time → higher score |
| R-S02 | CCA Match | w_cca | minmax | Count of matching CCAs | `len(user_ccas ∩ school_ccas)` |
| R-S03 | Programme Match | w_prog | minmax | Count of matching ALP/LLP programmes | `len(user_progs ∩ school_progs)` |
| R-S04 | PSLE Tier | w_psle_tier | ordinal | Tier 1–4 | Tier 1→1.0, 2→0.75, 3→0.5, 4→0.25 |
| R-S05 | Sports Excellence | w_sports | minmax | NSG achievement count | `len(user_sports ∩ school_nsg[gender])` — gender-specific |
| R-S06 | Arts Excellence | w_arts | minmax | SYF distinction count | `len(user_arts ∩ school_syf)` |
| R-S07 | Session Type | w_session | binary | 0 or 1 | 1 if school session == `intent.session`; guard: preference must be non-empty |
| R-S08 | SAP School | w_sap | binary | 0 or 1 | 1 if school `sap_ind` == `intent.sap`; guard: preference must be non-empty |
| R-S09 | Autonomous School | w_autonomous | binary | 0 or 1 | 1 if school `autonomous_ind` == `intent.autonomous`; guard: preference must be non-empty |
| R-S10 | IP School | w_ip | binary | 0 or 1 | 1 if school `ip_ind` == `intent.ip`; guard: preference must be non-empty |
| R-S11 | Mother Tongue | w_mt | binary | 0 or 1 | 1 if `intent.mother_tongue` is non-empty AND offered by school |
| R-S12 | Weight Normalisation | — | — | — | `norm_weights = raw_weights / sum(raw_weights)` |
| R-S13 | Fit Score | — | — | — | `score_total = 100 × Σ(norm_weight_i × score_i)` |

**Important — Binary dimension guard:**
Binary dimensions (R-S07..R-S11) only contribute to scoring when the preference value is
non-empty. This means:
- Slider > 0 alone is not enough — the preference target must also be set.
- For SAP, Autonomous, IP: if slider > 0 but no bonus text, `input_validator.py` auto-defaults
  the preference to `"Y"` (i.e. prefer schools with that attribute).
- For Session: must be explicitly specified in bonus text — slider alone cannot determine
  whether the user prefers Full Day or Single Session.
- For Mother Tongue: must be specified in bonus text (CHINESE / MALAY / TAMIL).

### 5.4 Category R-A — Admission Signal Rules (5 rules)
Applied by: Node 7 (phases.py) using `engine.run_first_match(SIGNAL, ctx)`.
Uses ballot odds from `ballot_history.csv` (column name matches the phase string exactly).

| Rule ID | Condition | Signal |
|---|---|---|
| R-A01 | Phase 1 (sibling enrolled) | "Guaranteed" |
| R-A02 | Ballot odds ≥ 70% | "Likely" |
| R-A03 | 40% ≤ ballot odds < 70% | "Competitive" |
| R-A04 | Ballot odds < 40% | "Difficult" |
| R-A05 | No ballot data available | "Unknown" |

### 5.5 Category R-T — Travel Rules (3 rules)
Applied by: Node 5 (travel.py) using `engine.run_first_match(TRAVEL, ctx)`.
Called after PT and walk routing are both attempted.

| Rule ID | Condition | Returns |
|---|---|---|
| R-T01 | Both PT and walk routes available | (faster of the two, minutes) |
| R-T02 | PT succeeded, walk failed | ("pt", pt_time) |
| R-T03 | PT failed | (None, None) — walk is not used as standalone fallback |

---

## 6. Fit Scoring & Admission Profile

### 6.1 Fit Score (Used for Ranking)

A normalised, weighted dot product across 11 dimensions (R-S01..R-S11). Full formula in §5.3.

```
fit_score = 100 × Σ (norm_weight_i × score_i)   for all i where weight_i > 0
```

Weights are normalised to sum to 1 before the dot product (R-S12).

### 6.2 Weight Auto-Bump

Binary dimensions require both a non-zero weight AND a non-empty preference value to have
any effect. The input layer handles two auto-fix cases:

1. **LLM extracted a preference, slider still at 0**: weight is bumped to 3.0
   ```
   w_sap = float(form_data["w_sap"]) or (3.0 if llm_prefs.get("sap") else 0.0)
   ```

2. **Slider > 0, but no bonus text specified the value**: SAP/Autonomous/IP default to `"Y"`
   ```
   sap = llm_prefs.get("sap") or ("Y" if form_data["w_sap"] > 0 else "")
   ```

Session defaults to empty even if the slider is > 0 — the user must specify Full Day or
Single Session in the bonus text, because a slider cannot determine which they prefer.

### 6.3 Admission Profile (Display-Only — Does NOT Affect Ranking)

Displayed as inline metadata on each school result card. Never used in fit_score calculation.

| Field | Source | Rule(s) |
|---|---|---|
| Registration Phase | Phase rule engine | R-P01..R-P06 |
| Historical Ballot Odds | ballot_history.csv | — (raw data) |
| Confidence Signal | Derived from ballot odds + phase | R-A01..R-A05 |

Phase column suffix encodes citizenship × distance bracket:
`Phase 2A-1` = Phase 2A, SC, < 1 km.
`Phase 2B-5` = Phase 2B, PR, 1–2 km.

---

## 7. Reasoning Subsystem: A Hybrid Cognitive Architecture

The system uses five distinct reasoning techniques.

| Technique | Applied To | Component | Why |
|---|---|---|---|
| Form Input + LLM Bonus Extraction | User Preference Parsing | Sidebar UI + input_validator.py | Structured form ensures reliable capture; LLM handles the flexible bonus text (family context, school characteristics). |
| Semantic Similarity | CCA & Programme Discovery | Sidebar UI (input_helpers.py) | Sentence-transformer embeddings match natural descriptions ("singing") to exact CCA names offline, at input time, without pipeline LLM cost. |
| Knowledge Rule Engine | Filtering, Phase Eligibility, Fit Scoring, Admission Signal | Nodes 4, 6, 7 via `knowledge_base/` | All deterministic domain logic in one place. Declared, tagged, sourced, independently testable. Traces enable grounded LLM explanations. |
| Probabilistic Display | Admission Odds | Node 7 + ballot_history.csv | Balloting is stochastic. Historical data is the most honest model of admission chances. Displayed as metadata — never distorts the fit ranking. |
| LLM Summarisation | Recommendation Explanation | Node 8 (summarizer.py) | LLMs generate clear, grounded narratives. Summary grounded strictly on score breakdown to prevent hallucination. |

### Why LangGraph

LangGraph is used as the pipeline orchestrator because:

1. **Explicit state**: `SchoolFitState` is the single source of truth. No global variables.
2. **Auditable transitions**: Every step is a named node. Visualizable, logged, and debuggable.
3. **Conditional control flow**: Retry logic, error handling, and graceful degradation are
   modeled as graph edges — not buried in if/else chains.
4. **Separation of concerns**: Each node is independently testable. All business logic lives
   in the rule engine or the LangChain chains, not in the nodes.

---

## 8. Key Design Decisions & Rationale

| Decision | Rationale |
|---|---|
| Form-based input with bonus text | Form inputs give reliable structure for critical fields (gender, postal code, weights). Bonus text handles open-ended preferences without forcing all users through NL parsing. |
| Semantic search in sidebar, not pipeline | CCA search runs offline at input time — no API call, no pipeline latency. Results are reviewed and confirmed by the user before the pipeline runs. |
| LLM only for bonus text | Reduces LLM calls from "everything" to one optional call. Structured form data never needs LLM parsing. |
| Pre-built intent to avoid double LLM call | App validates intent before pipeline invocation. `make_initial_state(prebuilt_intent=...)` passes it through, so Node 1 skips the LLM call entirely. |
| Binary preference auto-default to "Y" | If a user sets SAP slider > 0 but writes nothing in bonus text, the system infers they want SAP schools. Session is excluded from this because the slider cannot distinguish Full Day from Single Session. |
| Centralized Knowledge Rule Engine | Rules are scattered across v1 files with no single home. Centralizing them makes the system inspectable, updatable, and traceable. |
| Rule traces in pipeline state | Traces passed to LLM summarizer mean explanations reference specific rules (e.g., "R-P03 fired: parent is alumni → Phase 2A"), not generic descriptions. |
| Ballot history display-only | Conflating admission probability with fit score answers two questions with one number. Parents should see both dimensions independently. |
| OneMap routing over straight-line distance | A school 0.8 km away with poor transit connectivity may take 30 minutes. Travel time is a more accurate proximity proxy. |
| R-T02: PT fallback when walk fails | Previous bug: if walk routing failed, the PT result was discarded. R-T02 explicitly preserves the PT result when walk fails. |
| MinMax normalisation cross-school | Normalising per-batch (not per fixed scale) ensures meaningful relative ranking even when all schools score similarly on a dimension — avoids the degenerate case where all scores collapse to the same value. |
| Data in schoolfit_v2/data/ | CSV data and embeddings live together; `data/artifacts/` holds offline-generated vectors for semantic search. |

---

## 9. Implementation Status

| Component | Status |
|---|---|
| Knowledge Rule Engine (rule_engine.py) | ✅ Complete |
| All rules (R-F, R-P, R-S, R-A, R-T) | ✅ Complete — 30 rules total |
| LangGraph pipeline (graph.py, 8 nodes) | ✅ Complete |
| Form-based UI (app.py) | ✅ Complete |
| Semantic CCA/programme search (input_helpers.py) | ✅ Complete |
| LLM bonus text extraction (input_validator.py) | ✅ Complete |
| Score breakdown tooltip + tags on cards | ✅ Complete |
| Filtering pipeline trace UI | ✅ Complete |
| Rule Engine trace table UI | ✅ Complete |
| Folium map | ✅ Complete |
| LLM summary (Node 8) | ✅ Complete |
| OneMap travel routing (Node 5) | ✅ Complete — requires valid API token |
| Data refresh pipeline | 🔲 Not documented |
