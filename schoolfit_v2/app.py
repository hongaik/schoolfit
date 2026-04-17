"""
SchoolFit SG v2 — Streamlit UI
Entry point: streamlit run schoolfit_v2/app.py
"""
import sys
from pathlib import Path

# Ensure project root is on sys.path so relative imports work when launched
# from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import folium
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from graph import make_initial_state, pipeline
from knowledge_base.rules.scoring_rules import SCORE_DIMENSIONS
from styles import (
    CARD_TEMPLATE,
    CUSTOM_CSS,
    INFO_MARKDOWN,
    LANDING_HTML,
    PHASE_ITEM,
    PHASE_ROW,
    SCORE_BREAKDOWN_TABLE,
    SCORE_ROW,
    SIGNAL_BADGE,
    SUBTITLE_HTML,
    TAGS_HTML,
    TITLE_HTML,
)

# =============================================================================
# Page config
# =============================================================================
st.set_page_config(
    page_title="SchoolFit SG",
    page_icon="🎒",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# =============================================================================
# Session state initialisation
# =============================================================================
if "result" not in st.session_state:
    st.session_state.result = None
if "running" not in st.session_state:
    st.session_state.running = False

# =============================================================================
# Header
# =============================================================================
st.markdown(TITLE_HTML, unsafe_allow_html=True)
st.markdown(SUBTITLE_HTML, unsafe_allow_html=True)
st.write("---")

# =============================================================================
# Input
# =============================================================================
user_input = st.text_area(
    "Tell us about your child! 🎒",
    height=120,
    placeholder=(
        "e.g. My son lives in Bishan (570123), Singapore Citizen. "
        "He loves swimming and robotics. Really important that the school is close to home "
        "and has a strong sports team. His sister is already at Ai Tong School."
    ),
    help=(
        "Describe your child's gender, home postal code, citizenship, activities, "
        "and any school preferences. The more detail you give, the better the match!"
    ),
)

run_col, info_col = st.columns([1, 3])
with run_col:
    run_button = st.button("Find My Perfect School! 🎈", width="stretch")
with info_col:
    with st.expander("ℹ️ How does scoring work?"):
        st.markdown(INFO_MARKDOWN)

# =============================================================================
# Sidebar — weight overrides (shown after a result is available)
# =============================================================================
with st.sidebar:
    st.markdown("## 🎛️ Fine-tune Weights")
    st.markdown(
        "_Weights were auto-inferred from your description. "
        "Adjust and re-run if needed._"
    )

    weight_overrides: dict[str, float] = {}
    if st.session_state.result and st.session_state.result.get("user_intent"):
        intent = st.session_state.result["user_intent"]
        for dim in SCORE_DIMENSIONS:
            current = getattr(intent, dim.weight_attr, 0.0)
            weight_overrides[dim.weight_attr] = st.slider(
                dim.name, 0, 5, int(current),
                help=dim.description,
                key=f"w_{dim.rule_id}",
            )
    else:
        st.caption("Weights will appear here after your first search.")

    st.write("---")
    with st.expander("🔍 Knowledge Rule Engine"):
        from knowledge_base import engine
        st.code(engine.describe(), language=None)


# =============================================================================
# Helpers — rendering
# =============================================================================

_SIGNAL_CSS = {
    "Guaranteed": "guaranteed",
    "Likely": "likely",
    "Competitive": "competitive",
    "Difficult": "difficult",
    "Unknown": "unknown",
}


def _signal_badge(signal: str) -> str:
    css = _SIGNAL_CSS.get(signal, "unknown")
    return SIGNAL_BADGE.format(css_class=css, label=signal)


def _build_breakdown_html(row: pd.Series, norm_weights: dict) -> tuple[str, float]:
    rows_html = ""
    total = 0.0
    for dim in SCORE_DIMENSIONS:
        w = norm_weights.get(dim.rule_id, 0.0)
        if w <= 0:
            continue
        raw_col = f"_raw_{dim.rule_id}"
        score_col = f"score_{dim.rule_id}"
        raw_val = row.get(raw_col, "-")
        norm_val = row.get(score_col, 0.0)
        w_score = float(norm_val) * 100 * w
        total += w_score
        rows_html += SCORE_ROW.format(
            name=dim.name,
            weight=f"{w:.0%}",
            val=raw_val,
            score=w_score,
        )
    html = SCORE_BREAKDOWN_TABLE.format(rows=rows_html, total=total)
    return html, total


def _build_phase_row_html(row: pd.Series, active_phase: str) -> str:
    phase_cols = [
        ("Phase 1", "P1"),
        ("Phase 2A", "2A"),
        ("Phase 2B", "2B"),
        ("Phase 2C", "2C"),
        ("Phase 2CS", "2CS"),
        ("Phase 3", "P3"),
    ]
    # Determine distance suffix (SC/PR already encoded in active_phase)
    dist = float(row.get("dist_to_user", 999))
    citizenship = ""  # read from active_phase suffix sign
    if "-" in active_phase:
        suffix = active_phase.split("-")[-1]
        cat = int(suffix) if suffix.isdigit() else 1
        citizenship = "PR" if cat > 3 else "SC"
    else:
        cat = 3
        citizenship = "SC"

    if dist <= 1.0:
        cat_num = 1
    elif dist <= 2.0:
        cat_num = 2
    else:
        cat_num = 3
    if citizenship == "PR":
        cat_num += 3

    items_html = ""
    for phase_name, short in phase_cols:
        is_active = active_phase.startswith(phase_name) and not (
            phase_name == "Phase 2C" and active_phase.startswith("Phase 2CS")
        )
        suffix = f"-{cat_num}" if phase_name not in ("Phase 1", "Phase 3") else ""
        col_key = f"{phase_name}{suffix}"
        val = row.get(col_key)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            display = "—"
        elif phase_name == "Phase 3":
            display = str(val).replace("%", "")
        else:
            try:
                display = f"{int(float(val))}%"
            except Exception:
                display = str(val)

        active_class = " phase-active" if is_active else ""
        label = f"{'⭐ ' if is_active else ''}{short}"
        items_html += PHASE_ITEM.format(
            active_class=active_class, label=label, val=display
        )
    return PHASE_ROW.format(items=items_html)


def _build_tags_html(row: pd.Series, cca_matches: list, prog_matches: list) -> str:
    tags = []
    school_ccas = set(str(row.get("cca", "")).split("; "))
    matched_ccas = list(school_ccas & set(cca_matches))
    if matched_ccas:
        tags.append(f"<b>CCA</b>: {', '.join(matched_ccas)}")

    school_progs = set(str(row.get("niche_programmes", "")).split("; "))
    matched_progs = list(school_progs & set(prog_matches))
    if matched_progs:
        tags.append(f"<b>Programmes</b>: {', '.join(matched_progs)}")

    if not tags:
        return ""
    return TAGS_HTML.format(tags=" | 🎯 ".join(tags))


# =============================================================================
# Run pipeline
# =============================================================================

if run_button:
    if not user_input.strip():
        st.warning("Please describe your child first!")
    else:
        # Apply any weight overrides from the sidebar to the input text
        # (on first run, overrides are empty; on re-run, they're applied via
        # a new state built from the adjusted intent)
        with st.spinner("🎩 Waving the magic wand... ✨"):
            initial = make_initial_state(user_input)
            result = pipeline.invoke(initial)

        # If weights were adjusted in the sidebar AND we already had a result,
        # patch the intent weights and re-run scoring only (fast path).
        if weight_overrides and result.get("user_intent"):
            intent = result["user_intent"]
            for attr, val in weight_overrides.items():
                object.__setattr__(intent, attr, float(val)) if hasattr(intent, attr) else None

        st.session_state.result = result

# =============================================================================
# Display results
# =============================================================================

result = st.session_state.result

if result is None:
    st.markdown(LANDING_HTML, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        logo = Path(__file__).parent.parent / "deploy" / "logo.png"
        if logo.exists():
            st.image(str(logo), width="stretch")

elif result.get("error"):
    st.error(result["error"], icon="🚨")

else:
    df = result.get("schools_with_phases")
    if df is None or df.empty:
        st.warning("No schools found matching your criteria. Try expanding your radius or adjusting preferences.")
    else:
        intent = result.get("user_intent")
        norm_weights = df.attrs.get("norm_weights", {})
        cca_matches = result.get("cca_matches", [])
        prog_matches = result.get("prog_matches", [])
        coords = result.get("coordinates")

        # ── Extracted intent summary ─────────────────────────────────────────
        if intent:
            with st.expander("✅ What we understood from your description"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Gender", "Boy 👦" if intent.gender == "M" else "Girl 👧")
                c2.metric("Postal Code", intent.postal_code)
                c3.metric("Citizenship", intent.citizenship)
                gender_pref = "Same-gender only" if intent.prefer_same_gender_school else "All schools (including co-ed)"
                st.metric("School Type", gender_pref)
                if intent.activities:
                    st.markdown(f"**Activities detected:** {', '.join(intent.activities)}")
                top_weights = [
                    (dim.name, getattr(intent, dim.weight_attr, 0))
                    for dim in SCORE_DIMENSIONS
                    if getattr(intent, dim.weight_attr, 0) > 0
                ]
                if top_weights:
                    st.markdown(
                        "**Inferred priorities:** " +
                        " · ".join(f"{n} ({int(w)}/5)" for n, w in sorted(top_weights, key=lambda x: -x[1]))
                    )

        st.write("---")

        # ── Filtering Pipeline Breakdown ──────────────────────────────────────
        exclusion_log = result.get("filter_exclusion_log", {})
        if exclusion_log or True:  # Show even if empty for context
            with st.expander("📊 Filtering Pipeline — Step by Step"):
                # Get master list count
                from data_loader import load_master
                total_schools = len(load_master())

                st.markdown(f"**Total schools in Singapore**: {total_schools}")

                # Build the pipeline flow
                passed_at_stage = total_schools
                pipeline_stages = [
                    ("R-F01", "Gender Match", "School gender must match child's gender"),
                    ("R-F02", "Distance Check", f"School within {intent.radius_km if intent else 3.0} km radius"),
                    ("R-F03", "Same-Gender Preference", "Only same-gender schools (if requested)"),
                ]

                for rule_id, rule_name, rule_desc in pipeline_stages:
                    excluded = len(exclusion_log.get(rule_id, []))
                    passed_after = passed_at_stage - excluded

                    col1, col2, col3 = st.columns([1, 1.5, 1])
                    with col1:
                        st.metric(f"{rule_name}\n({rule_id})", f"{passed_after}/{passed_at_stage}")
                    with col2:
                        st.caption(rule_desc)
                    with col3:
                        if excluded > 0:
                            st.error(f"❌ {excluded} excluded")
                        else:
                            st.success(f"✅ All pass")

                    # Show excluded schools for this rule
                    if excluded > 0:
                        excluded_schools = exclusion_log.get(rule_id, [])
                        with st.expander(f"Show {excluded} schools excluded by {rule_id}", expanded=False):
                            for school_name, reason in sorted(excluded_schools):
                                st.caption(f"• **{school_name}** — {reason}")

                    passed_at_stage = passed_after

                st.markdown(f"**Final Results**: {passed_at_stage} schools passed all filters (shown in Top Picks list above)")

        col_list, col_map = st.columns([1, 1.2])

        # ── School cards ─────────────────────────────────────────────────────
        with col_list:
            st.markdown("### 🏆 Top Picks For You!")
            for i, row in df.iterrows():
                breakdown_html, _total = _build_breakdown_html(row, norm_weights)
                phase_row_html = _build_phase_row_html(row, str(row.get("phase", "")))
                tags_html = _build_tags_html(row, cca_matches, prog_matches)

                travel_t = row.get("travel_time")
                travel_m = row.get("travel_mode", "")
                travel_str = f"{int(travel_t)}" if pd.notna(travel_t) and travel_t else "N/A"
                mode_str = str(travel_m).upper() if travel_m else ""

                card = CARD_TEMPLATE.format(
                    url=row.get("url_address", "#"),
                    rank=i + 1,
                    name=row["school_name"],
                    score=row["score_total"],
                    breakdown=breakdown_html,
                    travel_time=travel_str,
                    travel_mode=mode_str,
                    signal_badge=_signal_badge(str(row.get("admission_signal", "Unknown"))),
                    phase=row.get("phase", ""),
                    tags_html=tags_html,
                    phase_row_html=phase_row_html,
                )
                st.markdown(card, unsafe_allow_html=True)

        # ── Folium map ───────────────────────────────────────────────────────
        with col_map:
            st.markdown("### 🗺️ Explore the Map!")
            if coords:
                _x, _y, u_lat, u_lon = coords
                m = folium.Map(location=[u_lat, u_lon], zoom_start=14, tiles="CartoDB positron")
                folium.Marker(
                    [u_lat, u_lon],
                    popup="🏠 Your Home",
                    tooltip="You are here!",
                    icon=folium.Icon(color="red", icon="home", prefix="fa"),
                ).add_to(m)
                radius_km = intent.radius_km if intent else 3.0
                folium.Circle(
                    radius=radius_km * 1000,
                    location=[u_lat, u_lon],
                    color="#FF7E67",
                    weight=2,
                    fill=True,
                    fill_color="#FF9A76",
                    fill_opacity=0.05,
                ).add_to(m)
                for i, row in df.iterrows():
                    folium.Marker(
                        [row["lat"], row["long"]],
                        popup=f"<b>#{i+1} {row['school_name']}</b><br>Score: {row['score_total']}",
                        tooltip=f"#{i+1} {row['school_name']}",
                        icon=folium.Icon(
                            color="green" if i == 0 else "blue",
                            icon="graduation-cap",
                            prefix="fa",
                        ),
                    ).add_to(m)
                components.html(m._repr_html_(), height=580)

        # ── LLM Summary ──────────────────────────────────────────────────────
        summary = result.get("summary", "")
        if summary:
            st.write("---")
            st.markdown("### 🤖 Why These Schools?")
            st.success(summary)

        # ── Rule Traces ───────────────────────────────────────────────────────
        rule_traces = result.get("rule_traces", [])
        if rule_traces:
            st.write("---")
            from collections import defaultdict
            from knowledge_base.rule_engine import RuleCategory

            # Build per-rule stats
            stats: dict[str, dict] = defaultdict(lambda: {
                "category": "", "fired": 0, "not_fired": 0, "description": ""
            })
            for t in rule_traces:
                s = stats[t.rule_id]
                s["category"] = t.category.upper()
                s["description"] = t.reason
                if t.fired:
                    s["fired"] += 1
                else:
                    s["not_fired"] += 1

            rows = []
            for rule_id, s in sorted(stats.items()):
                total = s["fired"] + s["not_fired"]
                if s["category"] == "FILTER":
                    fired_label  = f"{s['fired']} schools passed"
                    missed_label = f"{s['not_fired']} excluded"
                elif s["category"] == "PHASE_ELIGIBILITY":
                    fired_label  = f"{s['fired']} phases assigned"
                    missed_label = f"{s['not_fired']} not applicable"
                elif s["category"] == "ADMISSION_SIGNAL":
                    fired_label  = f"{s['fired']} signals set"
                    missed_label = f"{s['not_fired']} fell through"
                elif s["category"] == "TRAVEL":
                    fired_label  = f"{s['fired']} modes selected"
                    missed_label = f"{s['not_fired']} not applicable"
                else:
                    fired_label  = str(s["fired"])
                    missed_label = str(s["not_fired"])
                rows.append({
                    "Rule": rule_id,
                    "Category": s["category"],
                    "Triggered": fired_label,
                    "Skipped": missed_label,
                    "Description": s["description"],
                })

            with st.expander(f"🔬 Knowledge Rule Engine — {len(rule_traces)} traces across {len(stats)} rules"):
                st.dataframe(
                    pd.DataFrame(rows),
                    hide_index=True,
                    use_container_width=True,
                )
                st.caption(
                    "**Triggered** = rule returned a non-None output (filter passed / phase assigned / signal set). "
                    "**Skipped** = rule returned None (condition not met)."
                )
