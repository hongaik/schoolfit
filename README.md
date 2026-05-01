IRS-PM-2026-05-03-AIS08PT-GRP-SchoolFit-SG.zip

---

## SECTION 1 : PROJECT TITLE
## SchoolFit SG - An Intelligent Decision Support System for Singapore Primary School Selection

---

## SECTION 2 : EXECUTIVE SUMMARY / PAPER ABSTRACT
SchoolFit SG is an intelligent decision support system designed to simplify and improve the primary school selection process for parents in Singapore. Each year, around 38,000 families face a complex and high-stakes decision involving trade-offs between school suitability (e.g., distance, programmes, CCAs) and admission feasibility under the competitive Primary 1 (P1) registration system.

Current tools and platforms provide only fragmented insights—either school information or admission statistics—forcing parents to manually synthesize data and navigate uncertainty. SchoolFit SG addresses this gap by integrating both dimensions into a unified, data-driven recommendation system.

The system combines multiple AI and analytical techniques, including rule-based reasoning, semantic search, and multi-factor scoring, to deliver personalized school recommendations. It evaluates each school along two key axes:

Fit Score (how suitable the school is for the child)
Admission Probability (likelihood of successful entry based on P1 rules and historical balloting data)

Users can input preferences in natural language (e.g., “strong in sports” or “near home”), which are parsed into structured attributes. The system then filters eligible schools, computes weighted suitability scores, models admission eligibility across P1 phases, and estimates admission likelihood using historical data.

The output is a transparent, ranked list of schools accompanied by scores, probabilities, and reasoning traces, enabling parents to make informed and confident decisions.

By consolidating fragmented data and introducing intelligent reasoning, SchoolFit SG transforms a traditionally stressful and opaque process into a personalized, transparent, and data-driven decision experience.

---

## SECTION 3 : CREDITS / PROJECT CONTRIBUTION

| Official Full Name  | Student ID (MTech Applicable)  | Role |
| :------------ |:---------------:| :-----|
| Tan Xian Liang | A0183638U | Project Leader |
| Chua Wentian Carine | A0340663H | Project Member |
| Zhou Lin (Jolin) | A0340258H | Project Member |
| Goh Hong Aik | A0096493N | Project Member |

---

## SECTION 4 : BUSINESS USE CASE & TECHNICAL VIDEOS

Refer to Project file

---

## SECTION 5 : USER GUIDE

### Requirements

- **Python 3.10+** (3.11 works well)
- [OpenAI](https://platform.openai.com/) API key
- [OneMap](https://www.onemap.gov.sg/) API portal account (email + password used to obtain routing/geocoding tokens)

### Quick start

From the **repository root** (`schoolfit/`):

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r schoolfit_v2/requirements.txt
```

Secrets (never commit real keys):
secrets will be provided in zip file, secretes.toml (please don't share out)

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml — set OPENAI_API_KEY, onemap_token_email, onemap_token_pwd
```

Run the app:

```bash
streamlit run schoolfit_v2/app.py
```

Then open the URL Streamlit prints (typically `http://localhost:8501`).


### Repo layout

| Path | Purpose |
|------|---------|
| `schoolfit_v2/app.py` | Streamlit UI |
| `schoolfit_v2/graph.py` | LangGraph pipeline (8 nodes) |
| `schoolfit_v2/data/` | School CSVs and `data/artifacts/` embedding files for semantic CCA/programme search |
| `schoolfit_v2/knowledge_base/` | Rule engine and MOE/policy-style rules |
| `.streamlit/secrets.toml` | Local secrets (gitignored); use `secrets.toml.example` as template |

---
## SECTION 6 : PROJECT REPORT / PAPER

Refer to Project file

---