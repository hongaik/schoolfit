"""
SchoolFit SG v2 — Streamlit UI (Form-Based Input)
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
from input_helpers import find_similar_cca, find_similar_prog, get_full_cca_list, get_full_prog_list
from input_validator import build_user_intent
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
if "form_submitted" not in st.session_state:
    st.session_state.form_submitted = False
if "form_data" not in st.session_state:
    st.session_state.form_data = None
if "error_msg" not in st.session_state:
    st.session_state.error_msg = ""
if "built_intent" not in st.session_state:
    st.session_state.built_intent = None

# =============================================================================
# Header
# =============================================================================
st.markdown(TITLE_HTML, unsafe_allow_html=True)
st.markdown(SUBTITLE_HTML, unsafe_allow_html=True)
st.write("---")

# =============================================================================
# Sidebar — Form-Based Input
# =============================================================================
with st.sidebar:
    st.markdown("## 🙋🏽‍♂️🙋🏻‍♀️ Tell us about yourself!")

    # ── Your Details (OUTSIDE form for visibility — shown first) ───────────
    st.markdown("### 🏠 Your Details")

    postal_code = st.text_input(
        "🏠 My Postal Code",
        value="",
        max_chars=6,
        placeholder="e.g. 570123",
        help="6-digit Singapore postal code",
        key="postal_code_input",
    )

    col1, col2 = st.columns(2)
    with col1:
        gender = st.radio(
            "👶 I am a...",
            ["Boy", "Girl"],
            index=0,
            format_func=lambda x: "👦 Boy" if x == "Boy" else "👧 Girl",
            key="gender_radio",
        )
        gender_code = "M" if gender == "Boy" else "F"

    with col2:
        citizenship = st.selectbox(
            "🌎 Citizenship",
            ["SC", "PR", "International"],
            key="citizenship_select",
        )

    radius_km = st.slider(
        "🗺️ Distance boundary (km)",
        min_value=0.5,
        max_value=10.0,
        value=3.0,
        step=0.5,
        help="Schools further than this distance will not be shown",
        key="radius_slider",
    )

    st.write("---")

    # ── CCA & Programmes (OUTSIDE form for reactive updates) ───────────────
    with st.expander("💬 Tell us your interests!", expanded=True):
        raw_cca = st.text_input(
            "⚽ Describe your CCA interests...",
            placeholder="e.g. Singing, Team sports, Chess",
            help="Type your interests and we'll suggest matching CCAs",
            key="raw_cca_input",
        )

        # Get CCA matches with scores
        cca_matches_with_scores = (
            find_similar_cca([i.strip() for i in raw_cca.split(",") if i.strip()])
            if raw_cca.strip()
            else [(name, 0.5) for name in get_full_cca_list()]
        )
        # Chips show name only; score shown in caption below
        cca_options = [name for name, _ in cca_matches_with_scores]
        cca_score_label = {name: f"{score*100:.0f}%" for name, score in cca_matches_with_scores}

        _cca_key = f"cca_sel_{abs(hash(raw_cca))}"
        cca_selections = st.multiselect(
            "⭐ Or pick from the list!",
            options=cca_options,
            default=cca_options if raw_cca.strip() else [],
            help="Select CCAs your child is interested in",
            key=_cca_key,
        )
        if cca_selections and raw_cca.strip():
            st.caption(" · ".join(f"Similarity Score:**{n}** {cca_score_label[n]}" for n in cca_selections))

        raw_prog = st.text_input(
            "🔬 Describe your program interests...",
            placeholder="e.g. STEM, Performing Arts, Coding",
            help="Type your interests and we'll suggest matching programmes",
            key="raw_prog_input",
        )

        # Get programme matches with scores
        prog_matches_with_scores = (
            find_similar_prog([i.strip() for i in raw_prog.split(",") if i.strip()])
            if raw_prog.strip()
            else [(name, 0.5) for name in get_full_prog_list()]
        )
        # Chips show name only; score shown in caption below
        prog_options = [name for name, _ in prog_matches_with_scores]
        prog_score_label = {name: f"{score*100:.0f}%" for name, score in prog_matches_with_scores}

        _prog_key = f"prog_sel_{abs(hash(raw_prog))}"
        prog_selections = st.multiselect(
            "⭐ Or pick from the list!",
            options=prog_options,
            default=prog_options if raw_prog.strip() else [],
            help="Select special programmes your child is interested in",
            key=_prog_key,
        )
        if prog_selections and raw_prog.strip():
            st.caption(" · ".join(f"Similarity Score:**{n}** {prog_score_label[n]}" for n in prog_selections))

        pref_text = st.text_area(
            "🤟 Bonus: Anything else you like?",
            placeholder=(
                "e.g. Prefer a SAP school, strong in basketball, "
                "sister is at Nanyang Primary, parent is alumni, full-day session"
            ),
            height=150,
            help=(
                "Mention: sports/arts excellence, session type, SAP/Autonomous/IP preferences, "
                "mother tongue, or family connections (sibling, alumni, staff, volunteer, church/clan)"
            ),
            key="pref_text",
        )

    st.write("---")

    # ── Weights + Submit (inside form to batch submission) ──────────────────
    with st.form("school_preference_form"):
        st.markdown("### 🎛️ What do you value most?")
        w_dist = st.slider(
            "⏳ Travel Time",
            0,
            5,
            3,
            help="How important is short travel time to school?",
            key="w_dist_slider",
        )
        w_cca = st.slider(
            "⚽ CCAs",
            0,
            5,
            3,
            help="How important are CCAs matching your child's interests?",
            key="w_cca_slider",
        )
        w_prog = st.slider(
            "🔬 Special Programs",
            0,
            5,
            3,
            help="How important are special programmes (ALP/LLP)?",
            key="w_prog_slider",
        )
        w_psle_tier = st.slider(
            "🎯 PSLE Tier",
            0,
            5,
            3,
            help="How important is the school's academic tier?",
            key="w_psle_tier_slider",
        )

        with st.expander("More options ➕"):
            w_sports = st.slider(
                "🏆 Sports Excellence",
                0,
                5,
                0,
                help="How important is the school's sports performance?",
                key="w_sports_slider",
            )
            w_arts = st.slider(
                "🎨 Arts Excellence",
                0,
                5,
                0,
                help="How important is the school's arts performance?",
                key="w_arts_slider",
            )
            w_session = st.slider(
                "⏰ Session Time",
                0,
                5,
                0,
                help="How important is full-day vs single session?",
                key="w_session_slider",
            )
            w_sap = st.slider(
                "🧠 SAP School",
                0,
                5,
                0,
                help="How important is Special Assistance Plan (SAP) status?",
                key="w_sap_slider",
            )
            w_autonomous = st.slider(
                "🚀 Autonomous School",
                0,
                5,
                0,
                help="How important is autonomous school status?",
                key="w_autonomous_slider",
            )
            w_ip = st.slider(
                "🎓 Integrated Program (IP)",
                0,
                5,
                0,
                help="How important is through-train pathway?",
                key="w_ip_slider",
            )
            w_mt = st.slider(
                "🗣️ Mother Tongue",
                0,
                5,
                0,
                help="How important is mother tongue language offering?",
                key="w_mt_slider",
            )

        st.write("---")
        top_n = st.slider(
            "🎯 How many schools to show?",
            min_value=1,
            max_value=10,
            value=5,
            help="Select how many top recommendations you want to see",
            key="top_n_slider",
        )

        st.write("---")
        run_button = st.form_submit_button("Find My Perfect School! 🎈", use_container_width=True)

    # ── Form submission handler ──────────────────────────────────────────────
    if run_button:
        # Collect form data
        _cca_score_dict = dict(cca_matches_with_scores)
        _prog_score_dict = dict(prog_matches_with_scores)
        form_data = {
            "postal_code": postal_code,
            "gender": gender_code,
            "citizenship": citizenship,
            "cca_selections": cca_selections,
            "prog_selections": prog_selections,
            "cca_score_map": {n: _cca_score_dict.get(n, 1.0) for n in cca_selections},
            "prog_score_map": {n: _prog_score_dict.get(n, 1.0) for n in prog_selections},
            "pref_text": pref_text,
            "radius_km": radius_km,
            "w_dist": w_dist,
            "w_cca": w_cca,
            "w_prog": w_prog,
            "w_psle_tier": w_psle_tier,
            "w_sports": w_sports,
            "w_arts": w_arts,
            "w_session": w_session,
            "w_sap": w_sap,
            "w_autonomous": w_autonomous,
            "w_ip": w_ip,
            "w_mt": w_mt,
            "top_n": top_n,
            "prefer_same_gender_school": False,
        }

        # Validate and build intent
        intent, error_msg = build_user_intent(form_data)

        if error_msg:
            st.session_state.error_msg = error_msg
            st.session_state.form_submitted = False
            st.session_state.built_intent = None
        else:
            st.session_state.error_msg = ""
            st.session_state.form_submitted = True
            st.session_state.form_data = form_data
            st.session_state.built_intent = intent  # reuse — avoids second LLM call in Node 1


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
            norm_val=float(norm_val) if norm_val != "-" else 0.0,
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




def _build_tags_html(
    row: pd.Series,
    cca_matches: list,
    prog_matches: list,
    intent=None,
    sports_matches: list = None,
    arts_matches: list = None,
) -> str:
    tags = []

    school_ccas = set(str(row.get("cca", "")).split("; "))
    matched_ccas = list(school_ccas & set(cca_matches))
    if matched_ccas:
        tags.append(f"<b>CCA</b>: {', '.join(sorted(matched_ccas))}")

    school_progs = set(str(row.get("niche_programmes", "")).split("; "))
    matched_progs = list(school_progs & set(prog_matches))
    if matched_progs:
        tags.append(f"<b>Programmes</b>: {', '.join(sorted(matched_progs))}")

    if intent:
        gender = intent.gender

        # Sports NSG — use sports_matches from state (user's NSG-eligible selections)
        if intent.w_sports > 0 and sports_matches:
            sch_sports = row.get("sports_achievement_2025", {})
            if isinstance(sch_sports, dict):
                gender_sports = set(sch_sports.get(gender, []))
                matched_sports = list(gender_sports & set(sports_matches))
                if matched_sports:
                    tags.append(f"<b>NSG Achievement</b>: {', '.join(sorted(matched_sports))}")

        # Arts distinction — use arts_matches from state (user's SYF-eligible selections)
        if intent.w_arts > 0 and arts_matches:
            sch_arts = set(str(row.get("arts_distinction_2024", "")).split("; "))
            matched_arts = list(sch_arts & set(arts_matches))
            if matched_arts:
                tags.append(f"<b>SYF Distinction</b>: {', '.join(sorted(matched_arts))}")

        # Session
        if intent.session and row.get("session_code") == intent.session:
            tags.append(f"<b>Session</b>: {intent.session}")

        # SAP / Autonomous / IP
        for label, pref_attr, col in [
            ("SAP", "sap", "sap_ind"),
            ("Autonomous", "autonomous", "autonomous_ind"),
            ("IP", "ip", "ip_ind"),
        ]:
            pref = getattr(intent, pref_attr, "")
            if pref and row.get(col) == pref:
                tags.append(f"<b>{label}</b>: {pref}")

        # Mother tongue
        if intent.mother_tongue and intent.mother_tongue in str(row.get("mother_tongue", "")):
            tags.append(f"<b>MT</b>: {intent.mother_tongue}")

    if not tags:
        return ""
    return TAGS_HTML.format(tags=" | 🎯 ".join(tags))


# =============================================================================
# Run pipeline (on form submission)
# =============================================================================

if st.session_state.form_submitted:
    with st.spinner("🎩 Waving the magic wand... ✨"):
        initial = make_initial_state(
            st.session_state.form_data,
            prebuilt_intent=st.session_state.built_intent,
        )
        result = pipeline.invoke(initial)
        st.session_state.result = result
        st.session_state.form_submitted = False  # Reset after run

# =============================================================================
# Display errors
# =============================================================================

if st.session_state.error_msg:
    st.error(st.session_state.error_msg, icon="🚨")

# =============================================================================
# Display results
# =============================================================================

result = st.session_state.result

if result is None:
    st.markdown(LANDING_HTML, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        logo = Path(__file__).resolve().parent / "data" / "logo.png"
        if logo.exists():
            st.image(str(logo), use_container_width=True)

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
        cca_match_scores = result.get("cca_match_scores", [])
        prog_match_scores = result.get("prog_match_scores", [])
        if len(cca_match_scores) == len(cca_matches):
            cca_score_map = dict(zip(cca_matches, cca_match_scores))
        else:
            cca_score_map = {}
        if len(prog_match_scores) == len(prog_matches):
            prog_score_map = dict(zip(prog_matches, prog_match_scores))
        else:
            prog_score_map = {}
        coords = result.get("coordinates")

        # ── Your Search Summary ──────────────────────────────────────────────
        if intent:
            with st.expander("✅ Your Search Preferences"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Gender", "👦 Boy" if intent.gender == "M" else "👧 Girl")
                c2.metric("Postal Code", intent.postal_code)
                c3.metric("Citizenship", intent.citizenship)

                c4, c5 = st.columns(2)
                with c4:
                    st.metric("Search Radius", f"{float(intent.radius_km):.1f} km")
                with c5:
                    st.metric("Show Top", f"{int(intent.top_n)} schools")

                # Selected interests
                if cca_matches or prog_matches:
                    st.markdown("**📌 Selected Interests:**")
                    if cca_matches:
                        st.caption(f"**CCAs:** {', '.join(cca_matches)}")
                    if prog_matches:
                        st.caption(f"**Programmes:** {', '.join(prog_matches)}")

                # Weight priorities
                top_weights = [
                    (dim.name, getattr(intent, dim.weight_attr, 0))
                    for dim in SCORE_DIMENSIONS
                    if getattr(intent, dim.weight_attr, 0) > 0
                ]
                if top_weights:
                    st.markdown("**⭐ Your Priorities:**")
                    st.caption(
                        " · ".join(f"{n} ({int(w)}/5)" for n, w in sorted(top_weights, key=lambda x: -x[1]))
                    )

                # LLM-extracted bonus preferences
                _bonus_items = []
                if intent.session:
                    _bonus_items.append(f"Session: {intent.session}")
                if intent.sap:
                    _bonus_items.append(f"SAP: {intent.sap}")
                if intent.autonomous:
                    _bonus_items.append(f"Autonomous: {intent.autonomous}")
                if intent.ip:
                    _bonus_items.append(f"IP: {intent.ip}")
                if intent.mother_tongue:
                    _bonus_items.append(f"Mother Tongue: {intent.mother_tongue}")
                if intent.has_sibling:
                    _bonus_items.append(f"Sibling at: {', '.join(intent.has_sibling)}")
                if intent.former_student:
                    _bonus_items.append(f"Former student: {', '.join(intent.former_student)}")
                if intent.is_alumni:
                    _bonus_items.append(f"Parent alumni: {', '.join(intent.is_alumni)}")
                if intent.is_staff:
                    _bonus_items.append(f"Parent staff: {', '.join(intent.is_staff)}")
                if intent.is_mk:
                    _bonus_items.append(f"MOE Kindergarten: {', '.join(intent.is_mk)}")
                if intent.is_volunteer:
                    _bonus_items.append(f"Volunteer: {', '.join(intent.is_volunteer)}")
                if intent.is_church_clan:
                    _bonus_items.append(f"Church/Clan: {', '.join(intent.is_church_clan)}")
                if intent.is_community_leader:
                    _bonus_items.append(f"Community Leader: {intent.is_community_leader}")
                if _bonus_items:
                    st.markdown("**🤖 Extracted from your bonus text:**")
                    st.caption(" · ".join(_bonus_items))
        with st.expander("ℹ️ How does scoring work?"):
            st.markdown(INFO_MARKDOWN)

        # ── LLM Summary ──────────────────────────────────────────────────────
        summary = result.get("summary", "")
        if summary:
            st.markdown("### 🤖 Why These Schools?")
            st.success(summary)
            st.write("---")

        col_list, col_map = st.columns([1, 1.2])

        # ── School cards ─────────────────────────────────────────────────────
        with col_list:
            st.markdown("### 🏆 Top Picks For You!")
            # Prefer schools_with_travel — same cohort the scorer ranked (avoids misleading counts).
            _scored_pool = result.get("schools_with_travel")
            _filtered = result.get("filtered_schools")
            _pool_n = None
            if _scored_pool is not None and hasattr(_scored_pool, "__len__"):
                _pool_n = len(_scored_pool)
            elif _filtered is not None and hasattr(_filtered, "__len__"):
                _pool_n = len(_filtered)
            if _pool_n is not None and _pool_n > len(df):
                st.caption(
                    f"Showing the **top {len(df)}** by fit score out of **{_pool_n}** schools "
                    "in your search radius (then ranked). Say e.g. “top 10 schools” to list more. "
                    "If the list feels island-wide, check **radius_km** in “What we understood” — "
                    "very large radii favour famous schools over neighbourhood ones."
                )
            for i, row in df.iterrows():
                breakdown_html, _total = _build_breakdown_html(row, norm_weights)
                phase_row_html = _build_phase_row_html(row, str(row.get("phase", "")))
                tags_html = _build_tags_html(
                    row,
                    cca_matches,
                    prog_matches,
                    intent=intent,
                    sports_matches=result.get("sports_matches", []),
                    arts_matches=result.get("arts_matches", []),
                )

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

        # ── Filtering Pipeline Breakdown ──────────────────────────────────────
        st.write("---")
        exclusion_log = result.get("filter_exclusion_log", {})
        with st.expander("📊 Filtering Pipeline — Step by Step"):
            from data_loader import load_master as _load_master
            total_schools = len(_load_master())
            st.markdown(f"**Total schools in Singapore**: {total_schools}")
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
                if excluded > 0:
                    with st.expander(f"Show {excluded} schools excluded by {rule_id}", expanded=False):
                        for school_name, reason in sorted(exclusion_log.get(rule_id, [])):
                            st.caption(f"• **{school_name}** — {reason}")
                passed_at_stage = passed_after
            _fs = result.get("filtered_schools")
            _n_ok = len(_fs) if _fs is not None and hasattr(_fs, "__len__") else 0
            st.markdown(
                f"**Schools that passed all filters**: {_n_ok} "
                "(the step counts above are per-rule exclusions, not the final tally)."
            )

        # ── Rule Traces ───────────────────────────────────────────────────────
        rule_traces = result.get("rule_traces", [])
        if rule_traces:
            from collections import defaultdict

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
