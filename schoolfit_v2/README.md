# SchoolFit SG v2

AI-powered P1 primary school matching for Singapore families.  
Built as a cognitive agent pipeline using LangGraph + LangChain + a centralized Knowledge Rule Engine.

---

# Local Run step
create virtual env

python3 -m venv venv

source venv/bin/activate

# 1. Install dependencies

pip install -r schoolfit_v2/requirements.txt

# 2. Create secrets file at project root

cat > .streamlit/secrets.toml << 'EOF'

OPENAI_API_KEY = "

onemap_token_email = "[your@email.com](mailto:your@email.com)"

onemap_token_pwd = ""

EOF

# 3. Launch

streamlit run schoolfit_v2/app.py

Open the architecture diagram in a browser anytime:

open schoolfit_v2/architecture.html

## What We Built

### Architecture Overview

```
User types one natural-language message
           │
           ▼
  ┌─────────────────────────────────────────────────────┐
  │              LangGraph Pipeline (graph.py)          │
  │                                                     │
  │  [1] extract_intent   ← LangChain: NL → UserIntent  │
  │         │                                           │
  │  [2] validate_geocode ← OneMap API: postal → coords │
  │         │                                           │
  │  [3] semantic_match   ← sentence-transformers       │
  │         │                                           │
  │  [4] filter_schools   ─────────────┐                │
  │         │  (retry if empty)        │                │
  │  [5] compute_travel_time           │  Knowledge     │
  │         │                          ├─ Rule Engine   │
  │  [6] score_rank       ─────────────┤  (16 rules)    │
  │         │                          │                │
  │  [7] compute_phases   ─────────────┘                │
  │         │                                           │
  │  [8] generate_summary ← LangChain: grounded summary │
  └─────────────────────────────────────────────────────┘
           │
           ▼
   Streamlit UI (app.py)
   School cards + Folium map + LLM summary
```

### File Structure

```
schoolfit_v2/
├── app.py                      Streamlit UI — layout, state, rendering only
├── graph.py                    LangGraph pipeline: 8 nodes + conditional edges
├── state.py                    SchoolFitState TypedDict + UserIntent Pydantic schema
├── api_clients.py              Cached LLM + OneMap token (@st.cache_resource)
├── data_loader.py              Cached CSV/embedding loaders (reads schoolfit_v2/data/)
├── styles.py                   CSS + HTML card/tooltip/phase templates
├── data/                     CSVs + data/artifacts/ (CCA & programme embeddings)
│   ├── rule_engine.py          RuleEngine class, Rule + RuleTrace dataclasses
│   └── rules/
│       ├── filter_rules.py     R-F01..R-F02  (gender + distance hard filters)
│       ├── phase_rules.py      R-P01..R-P06  (MOE P1 phase eligibility)
│       ├── scoring_rules.py    R-S01..R-S11  (11 fit score dimension specs)
│       ├── signal_rules.py     R-A01..R-A05  (admission confidence signal)
│       └── travel_rules.py     R-T01..R-T03  (travel mode selection + fallback)
│
└── nodes/
    ├── extractor.py            Node 1: LangChain LCEL — NL text → UserIntent
    ├── validator.py            Node 2: OneMap geocoding + postal validation
    ├── matcher.py              Node 3: Semantic CCA + programme matching (offline)
    ├── filter.py               Node 4: Hard filters via R-F rules
    ├── travel.py               Node 5: OneMap routing + R-T rule mode selection
    ├── scorer.py               Node 6: 11-dimension fit scoring + ballot merge
    ├── phases.py               Node 7: R-P phase rules + R-A signal rules
    └── summarizer.py           Node 8: LangChain LCEL — grounded recommendation summary
```

### Knowledge Rule Engine

16 rules registered at startup across 5 categories:

| Category | Rules | Applied By |
|---|---|---|
| Filter (R-F) | R-F01 gender match, R-F02 distance radius | Node 4 |
| Phase Eligibility (R-P) | R-P01 International → Phase 3, R-P02 sibling → Phase 1, R-P03 alumni/staff/MK → Phase 2A, R-P04 volunteer/church → Phase 2B, R-P05 community leader → Phase 2B, R-P06 default → Phase 2C | Node 7 |
| Admission Signal (R-A) | R-A01 Guaranteed, R-A02 Likely (≥70%), R-A03 Competitive (40–70%), R-A04 Difficult (<40%), R-A05 Unknown | Node 7 |
| Travel (R-T) | R-T01 use faster of PT/walk, R-T02 PT fallback if walk fails, R-T03 return None if PT fails | Node 5 |
| Scoring (R-S) | 11 `ScoreDimension` specs (not registered as engine functions — see below) | Node 6 |

> **Note on scoring rules:** Dimensions R-S01..R-S11 are defined as `ScoreDimension` dataclass specs in `scoring_rules.py` rather than engine-registered functions. This is because MinMaxNorm requires all schools' values simultaneously — it cannot be computed per-school in isolation. R-S12 (weight normalisation) and R-S13 (final score formula) are implemented directly in `scorer.py`.

### Pipeline State

A single `SchoolFitState` TypedDict (defined in `state.py`) flows through every node.
No global variables, no module-level side effects, no hidden state.

Key fields accumulated across the pipeline:

```
user_input → user_intent → coordinates → cca_matches / prog_matches
→ filtered_schools → schools_with_travel → top_schools
→ schools_with_phases (+ phase + admission_signal columns)
→ rule_traces (accumulated from nodes 4, 6, 7)
→ summary
```

### Conditional Edges (Error Handling + Retries)

| From Node | Condition | Outcome |
|---|---|---|
| extract_intent | LLM error | END — show error |
| validate_geocode | Invalid postal / API error | END — show error |
| filter_schools | Schools found | Continue to travel |
| filter_schools | Empty, retry < 2 | Loop back with radius × 1.5 |
| filter_schools | Empty, retry ≥ 2 | END — "no schools found" |

### Fit Score (11 Dimensions)

| # | Dimension | Method | Rule |
|---|---|---|---|
| 1 | Travel Time | MinMaxNorm, inverted | R-S01 |
| 2 | CCA Match | MinMaxNorm (intersection count) | R-S02 |
| 3 | Programme Match | MinMaxNorm (intersection count) | R-S03 |
| 4 | PSLE Tier | Ordinal map {1→1.0, 2→0.75, 3→0.5, 4→0.25} | R-S04 |
| 5 | Sports Excellence (NSG) | MinMaxNorm (intersection count by gender) | R-S05 |
| 6 | Arts Excellence (SYF) | MinMaxNorm (intersection count) | R-S06 |
| 7 | Session Type | Binary match | R-S07 |
| 8 | SAP School | Binary match | R-S08 |
| 9 | Autonomous School | Binary match | R-S09 |
| 10 | IP School | Binary match | R-S10 |
| 11 | Mother Tongue | Binary presence (guarded empty-string check) | R-S11 |

Weights are LLM-inferred from emphasis in the user's text and can be overridden via sidebar sliders.  
Ballot history is merged **for display only** — it has no effect on the fit score or ranking.

---

## What's New vs legacy v1

### Input Design

| v1 | v2 |
|---|---|
| Complex sidebar form: 10+ widgets, sliders, multi-selects, expanders | Single natural-language text area |
| User must manually map interests to CCA/programme dropdowns | LLM extracts activities, infers weights, matches school names automatically |
| Weights set manually by sliders before running | Weights inferred from text emphasis; sliders appear in sidebar for optional override |

### Architecture

| v1 | v2 |
|---|---|
| Single `app.py` (~380 lines) containing scoring, API calls, rendering, and business logic | Separated into 14 modules across `nodes/`, `knowledge_base/`, and top-level files |
| No explicit pipeline — sequential imperative code | LangGraph 8-node state machine with named transitions and conditional edges |
| No knowledge base — rules as scattered if/else chains | Centralized `knowledge_base/` with 16 rules, each tagged with ID, description, and source |
| No pipeline state — globals and module-level variables | `SchoolFitState` TypedDict flows through every node; no globals, no side effects |

### Bug Fixes

| Bug (v1) | Fix (v2) |
|---|---|
| `get_travel_time` returned 3-tuple on error, 2-tuple on success → unpacking crash | R-T rules always return consistent `(mode, minutes)` 2-tuple; `(None, None)` on failure |
| `client.responses.parse()` with `model="gpt-5-mini"` — both wrong | LangChain `llm.with_structured_output(UserIntent)` + `model="gpt-4o-mini"` |
| `score_mt`: `parsed['mt'] in x and parsed['mt']` → empty string always matched | R-S11: guard is `user_mt and user_mt in school_mts` (preference checked first) |
| Arts Excellence `disp_val = len(sch[sch_col])` → string character count, not matches | R-S06: `len(set(school_arts.split("; ")) & set(arts_matches))` |
| Module-level `client = OpenAI(...)` and `token = get_onemap_token()` ran on every import | `@st.cache_resource` factory functions in `api_clients.py` |
| `score_psle_tier` could produce NaN for unmapped tier values | R-S04 ordinal map has `.fillna(0)` safety in scorer |
| `get_phase_div` + `get_val` redefined inside every loop iteration | Extracted as standalone functions in `app.py` |
| `devcontainer.json` pointed to wrong `requirements.txt` path | Requirements path is now `schoolfit_v2/requirements.txt` |

### Admission Profile

| v1 | v2 |
|---|---|
| `ballot_history` merged into the scored DataFrame — implicitly affected ranking | `ballot_history` merged **after** scoring, in `scorer.py`, for display only |
| Phase displayed as a single badge | Full phase table showing odds for all phases (P1, 2A, 2B, 2C, 2CS, P3) |
| No confidence signal | Admission signal badge: Guaranteed / Likely / Competitive / Difficult / Unknown (R-A rules) |

### Explainability

| v1 | v2 |
|---|---|
| LLM summary generated from HTML breakdown strings | Summary generated from structured score breakdown + rule traces |
| No record of which rules fired | `rule_traces: list[RuleTrace]` in state, accumulated across nodes 4, 6, 7 |
| Rule source not documented | Every rule has an `id`, `description`, and `source` field |
| Rules inspectable only by reading source code | `engine.describe()` exposed in sidebar "Knowledge Rule Engine" expander |

---

## Setup & Running

### Dependencies

```bash
pip install -r schoolfit_v2/requirements.txt
```

### Secrets

Create `.streamlit/secrets.toml` in the project root:

```toml
OPENAI_API_KEY = "sk-..."
onemap_token_email = "your@email.com"
onemap_token_pwd = "your_onemap_password"
```

### Run

```bash
streamlit run schoolfit_v2/app.py
```

### Data

CSV data files and precomputed CCA/programme embeddings are read from `schoolfit_v2/data/` (CSVs alongside `data/artifacts/` `.npy` / `.pkl` / `.json`).

---

## Design Decisions

| Decision | Rationale |
|---|---|
| Folder `schoolfit_v2/` as the app surface | Keeps CSVs + embedding artifacts together under `schoolfit_v2/data/`. |
| Ballot history display-only | "Is this school right for my child?" (fit score) ≠ "Can I get in?" (admission odds). Conflating them distorts ranking. |
| Rule engine as decorator registry | Rules are plain functions — easy to test in isolation. Decorator attaches metadata without polluting function bodies. |
| Rule traces in state | Passing traces to the LLM summarizer grounds explanations in specific rules that fired, not generic descriptions. |
| sentence-transformers offline | CCA + programme matching runs against pre-computed embeddings — no runtime API cost, no latency. |
| OneMap routing over straight-line distance | A school 0.8 km away with poor transit may take 30 min. Travel time is a more accurate proxy for family impact. |
| LangGraph for pipeline orchestration | Explicit state, named transitions, and conditional edges make retries and errors first-class — not buried in if/else. |
