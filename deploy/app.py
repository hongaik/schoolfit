import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import folium
from pathlib import Path
ROOT = Path(__file__).resolve().parent
from helper import *
from search_retrieve import *
from styles import *

# Set page configuration for a kid-friendly look
st.set_page_config(
    page_title="SchoolFit SG 🏫✨",
    page_icon="🎒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Session State
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "input_valid" not in st.session_state:
    st.session_state.input_valid = False
if "error_msg" not in st.session_state:
    st.session_state.error_msg = ""

def reset_state():
    st.session_state.submitted = False
    st.session_state.input_valid = False

# --- Custom CSS for a Clean, Polished, and Kid-Friendly UI ---
st.markdown(custom_css, unsafe_allow_html=True)

# --- Title Header ---
st.markdown(TITLE_HTML, unsafe_allow_html=True)
st.markdown(SUBTITLE_HTML, unsafe_allow_html=True)
st.write("---")

# --- Sidebar Inputs ---
with st.sidebar:
    st.markdown("## 🙋🏽‍♂️🙋🏻‍♀️ Tell us about yourself!")
    
    st.markdown("### 💬 Tell us your interests!")
    with st.expander(" CCAs, Special Programs & More!"):
        raw_cca = st.text_input("⚽ Describe your CCA interests briefly... (Comma separated if multiple)", help="Let us recommend for you!", placeholder="e.g. Singing, Team sports", on_change=reset_state)
        cca_options = find_similar_cca([i.strip() for i in raw_cca.split(',') if i.strip()]) if raw_cca.strip() else cca_list
        cca_selections = st.multiselect("⭐ Or pick from the list!", options=cca_options, default=cca_options if raw_cca.strip() else [], help="Or pick from the list!", on_change=reset_state)
        
        raw_prog = st.text_input("🔬 Describe your program interests briefly... (Comma separated if multiple)", help="Let us recommend for you!", placeholder="e.g. STEM, Performing Arts, Coding", on_change=reset_state)
        prog_options = find_similar_prog([i.strip() for i in raw_prog.split(',') if i.strip()]) if raw_prog.strip() else niche_prog_list
        prog_selections = st.multiselect("⭐ Or pick from the list!", options=prog_options, default=prog_options if raw_prog.strip() else [], help="Or pick from the list!", on_change=reset_state)
        
        pref_text = st.text_area(
            "🤟 Bonus: Anything else you like?",
            placeholder="e.g. Prefer a SAP school, top 4 in basketball or maybe big brother is already at Nanyang Primary! 🎒",
            height=180,
            help="Describe other preferences like Sports/Performing Arts achievements, Session Type, SAP/Autonomous/IP status, or Mother Tongue offered.\n\nYou can also mention things like: sibling in school X, parent alumni/staff/volunteer, MOE Kindergarten, church/clan affiliation, or community leadership.",
            on_change=reset_state
        )

    with st.form("school_preference_form"):
        postal_code = st.text_input("🏠 My Postal Code", value="123456", max_chars=6)
        
        col1, col2 = st.columns(2)
        with col1:
            gender = st.radio("👶 I am a...", ["Boy", "Girl"], index=0, format_func=lambda x: "👦 Boy" if x=="Boy" else "👧 Girl")
            gender = "M" if gender == "Boy" else "F"
        with col2:
            citizenship = st.selectbox("🌎 Citizenship", ["SC", "PR", "International"])
            
        radius_filter = st.slider("🗺️ Add a distance boundary! (km)", min_value=0.5, max_value=10.0, value=3.0, step=0.5, help="Schools further than this distance will not be shown.")
        
        st.markdown("### 🎛️ What do you value most?")
        with st.expander("🌟 Tell us your priorities!"):
            w_dist = st.slider("⏳ Travel Time", 0, 5, 3, help="How important is travel duration?")
            w_cca = st.slider("⚽ CCAs", 0, 5, 3, help="How important are the CCAs?")
            w_prog = st.slider("🔬 Special Programs", 0, 5, 3, help="How important are special/niche programs?")
            w_psle_tier = st.slider("🎯 PSLE Tier", 0, 5, 3, help="How important is the school's PSLE tier? Note: Tiering is based on informal sources and may be subjective.")

            with st.expander("More options ➕"):
                w_sports = st.slider("🏆 Sports Excellence", 0, 5, 0, help="How important is the school's sports performance in your desired CCA?")
                w_arts = st.slider("🎨 Arts Excellence", 0, 5, 0, help="How important is the school's arts performance in your desired CCA?")
                w_session = st.slider("⏰ Session Time", 0, 5, 0, help="How important is the school session (e.g. single session)?")
                w_sap = st.slider("🧠 SAP School", 0, 5, 0, help="Do you prefer a Special Assistance Plan (SAP) school?")
                w_auto = st.slider("🚀 Autonomous School", 0, 5, 0, help="Do you prefer an Autonomous school?")
                w_ip = st.slider("🎓 Integrated Prog (IP)", 0, 5, 0, help="Do you prefer an Integrated Programme (IP) school?")
                w_mt = st.slider("🗣️ Mother Tongue", 0, 5, 0, help="How important is the Mother Tongue language offering?")
                
        st.write("---")
        top_n = st.slider("🎯 How many schools to show?", min_value=1, max_value=10, value=5, help="Select how many top recommendations you want to see!")
        
        find_button = st.form_submit_button("Find My Perfect School! 🎈")
    
    if find_button:
        user_coordinates = get_coordinates(postal_code)        
        if len(postal_code) != 6 or not postal_code.isdigit() or 'Error' in user_coordinates:
            st.session_state.error_msg = "Oopsie! Invalid postal code!"
            st.session_state.input_valid = False
            st.session_state.submitted = False
        else:
            st.session_state.error_msg = ""
            st.session_state.input_valid = True
            st.session_state.submitted = True
            st.session_state.user_coordinates = user_coordinates

# --- Main Content Area ---
if not st.session_state.submitted and not st.session_state.error_msg:
    # Landing state
    st.markdown(LANDING_HTML, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.image(ROOT / "logo.png", use_container_width=True)

elif st.session_state.error_msg:
    st.error(st.session_state.error_msg, icon="🚨")

# --- Compute results and display ---    
elif st.session_state.input_valid:
    with st.spinner("🎩 Waving the magic wand... finding your perfect school... ✨"):

        # User coords
        user_X, user_Y, user_lat, user_lon = st.session_state.user_coordinates
        

        # Parse free text input
        parsed = extract_user_request(pref_text)

        score_components = [
            # name, score_col_name, weight_var, user's input, school's data
            ("Travel Time", "score_dist", w_dist, 'travel_time', 'travel_time'),
            ("CCA", "score_cca", w_cca, cca_selections, 'cca'),
            ("Programs", "score_niche_prog", w_prog, prog_selections, 'niche_programmes'),
            ("PSLE Tier", "score_psle_tier", w_psle_tier, 'school_tier', 'school_tier'),
            ("Sports Excellence", "score_sports_nsg", w_sports, 'sports_nsg', 'sports_achievement_2025'),
            ("Arts Excellence", "score_arts_dist", w_arts, 'arts_dist', 'arts_distinction_2024'),
            ("Session", "score_session", w_session, 'session_code', 'session_code'),
            ("SAP", "score_sap", w_sap, 'sap_ind', 'sap_ind'),
            ("Autonomous", "score_autonomous", w_auto, 'autonomous_ind', 'autonomous_ind'),
            ("IP", "score_ip", w_ip, 'ip_ind', 'ip_ind'),
            ("Mother Tongue", "score_mt", w_mt, 'mother_tongue', 'mother_tongue')
        ]
        
        # Filter for schools based on gender and radius
        master['dist_to_user'] = master.apply(lambda x: calculate_distance(X1=user_X, Y1=user_Y, X2=x['X'], Y2=x['Y']), axis=1)
        filtered = master[(master['nature_code'].str.contains(gender)) & (master['dist_to_user'] <= radius_filter)].copy()

        # Compute travel time for each school
        filtered[['travel_mode', 'travel_time']] = filtered.apply(
            lambda x: get_travel_time(user_lat, user_lon, x['lat'], x['long'], token),
            axis=1,
            result_type='expand'
        )

        # Score each school
        filtered['score_dist'] = 1 - MinMaxScaler().fit_transform(filtered[['travel_time']])
        filtered['score_cca'] = MinMaxScaler().fit_transform(filtered['cca'].apply(lambda x: len(set(x.split('; ')) & set(cca_selections))).values.reshape(-1,1)).flatten()
        filtered['score_niche_prog'] = MinMaxScaler().fit_transform(filtered['niche_programmes'].apply(lambda x: len(set(x.split('; ')) & set(prog_selections))).values.reshape(-1,1)).flatten()
        filtered['score_psle_tier'] = filtered['school_tier'].astype(int).astype(str).map({'1': 1, '2': 0.75, '3': 0.5, '4': 0.25})
        filtered['score_sports_nsg'] = MinMaxScaler().fit_transform(filtered['sports_achievement_2025'].apply(lambda x: len(set(x.get(gender, [])) & set(parsed['sports_nsg']))).values.reshape(-1,1)).flatten()
        filtered['score_arts_dist'] = MinMaxScaler().fit_transform(filtered['arts_distinction_2024'].apply(lambda x: len(set(x.split('; ')) & set(parsed['arts_dist']))).values.reshape(-1,1)).flatten()
        filtered['score_session'] = filtered['session_code'].apply(lambda x: 1 if parsed['session'] == x else 0)
        for col in ['sap', 'autonomous', 'ip']:
            filtered[f'score_{col}'] = filtered[f'{col}_ind'].apply(lambda x: 1 if parsed[col] == x else 0)
        filtered['score_mt'] = filtered['mother_tongue'].apply(lambda x: 1 if parsed['mt'] in x and parsed['mt'] else 0)
        filtered['phase'] = filtered.apply(lambda x: get_registration_phase(
            school_name=x['school_name'],
            citizenship=citizenship,
            dist_to_user=x['dist_to_user'],
            has_sibling=parsed['has_sibling'],
            former_student=parsed['former_student'],
            is_alumni=parsed['is_alumni'],
            is_staff=parsed['is_staff'],
            is_mk=parsed['is_mk'],
            is_volunteer=parsed['is_volunteer'],
            is_church_clan=parsed['is_church_clan'],
            is_community_leader=parsed['is_community_leader']
        ), axis=1)

        # Normalize weights
        score_cols = [comp[1] for comp in score_components]
        raw_weights = np.array([comp[2] for comp in score_components], dtype=float)
        
        if raw_weights.sum() > 0:
            norm_weights = raw_weights / raw_weights.sum()
        else:
            norm_weights = raw_weights
            
        # Update the components list with normalized weights for the tooltip
        score_components = [(c[0], c[1], nw, c[3], c[4]) for c, nw in zip(score_components, norm_weights)]
        
        filtered['score_total'] = (100 * filtered[score_cols].dot(norm_weights)).round(1)

        # Merge with ballot history
        filtered = filtered.merge(ballot_history, how='left', on='school_name')

        # Take the top N requested by the user
        top_schools = filtered.sort_values(by='score_total', ascending=False).reset_index(drop=True).head(int(top_n))

    with st.expander("ℹ️ How does scoring work?"):
        st.markdown(INFO_MARKDOWN)
        # Placeholder for the LLM summary, which will be filled after the UI loop
        summary_placeholder = st.empty()
        
    # --- Layout: Map and List ---
    # Stack columns vertically on mobile and horizontally on desktop using Streamlit columns
    col_list, col_map = st.columns([1, 1.2])
    
    with col_list:
        st.markdown(f"### 🏆 Our Top Picks For You!")
        
        breakdown_htmls_for_llm = []
        for i, sch in top_schools.iterrows():
            
            table_rows = ""
            total_score = 0.0

            for name, col_name, weight, user_col, sch_col in score_components:
                if weight > 0:
                    if name in ['CCA', 'Programs']:
                        disp_val = len(set(sch[sch_col].split('; ')) & set(user_col))
                    elif name == 'Sports Excellence':
                        disp_val = len(set(sch[sch_col].get(gender, [])) & set(parsed[user_col]))
                    elif name == 'Arts Excellence':
                        disp_val = len(sch[sch_col])
                    else:
                        disp_val = sch[sch_col]
                    raw_val = sch[col_name] * 100
                    w_score = raw_val * weight
                    total_score += w_score
                    weight_str = f"{weight:.0%}"
                    table_rows += TABLE_ROW_TEMPLATE.format(name=name, weight=weight_str, disp_val=disp_val, raw_val=raw_val, w_score=w_score)

            breakdown_html = BREAKDOWN_TABLE_TEMPLATE.format(table_rows=table_rows, total_score=total_score)
            
            breakdown_htmls_for_llm.append(f"#{i+1} {sch['school_name']}:\n{breakdown_html}")

            d_km = sch["dist_to_user"]
            if d_km <= 1.0: cat = 1
            elif d_km <= 2.0: cat = 2
            else: cat = 3
            if citizenship == "PR": suffix = f"-{cat + 3}"
            else: suffix = f"-{cat}"

            def get_val(col):
                val = sch.get(col, '-')
                if pd.isna(val) or val == '': return '-'
                try:
                    return f'{int(val)}%' if float(val) == int(float(val)) else f'{val}%'
                except:
                    return f'{val}%'

            p_actual = sch['phase']
            
            def get_phase_div(phase_name, phase_col):
                val = get_val(phase_col)
                val = val.replace('%', '') if phase_col == 'Phase 3' else val
                is_active = p_actual.startswith(phase_name) and not (phase_name == 'Phase 2C' and p_actual.startswith('Phase 2CS'))
                color = '#FF7E67' if is_active else '#7F8C8D'
                star = '⭐' if is_active else ''
                weight = 'bold' if is_active else 'normal'
                c_color = '#2C2C2C' if is_active else '#7F8C8D'
                return PHASE_DIV_TEMPLATE.format(weight=weight, color=color, phase_name=phase_name, star=star, c_color=c_color, val=val)

            tooltip_text = f"These values estimate the chance of admission for each phase based on historical records. Your child's citizenship ({citizenship}) and distance-to-home ({round(sch['dist_to_user'], 2)} km) also determine whether balloting applies. No data available for Phase 3 (international students)."

            phases_html = PHASES_TOOLTIP_TEMPLATE.format(
                p1=get_phase_div('Phase 1', 'Phase 1'),
                p2a=get_phase_div('Phase 2A', f'Phase 2A{suffix}'),
                p2b=get_phase_div('Phase 2B', f'Phase 2B{suffix}'),
                p2c=get_phase_div('Phase 2C', f'Phase 2C{suffix}'),
                p2cs=get_phase_div('Phase 2CS', f'Phase 2CS{suffix}'),
                p3=get_phase_div('Phase 3', 'Phase 3'),
                tooltip_text=tooltip_text
            )

            pref_tags = []
            
            # CCA Checks
            if cca_selections:
                sch_ccas = str(sch.get('cca', '')).split('; ')
                matched_ccas = list(set(sch_ccas) & set(cca_selections))
                if matched_ccas:
                    pref_tags.append(f"<b>CCA</b>: {', '.join(matched_ccas)}")
                    
            # Programs Checks
            if prog_selections:
                sch_progs = str(sch.get('niche_programmes', '')).split('; ')
                matched_progs = list(set(sch_progs) & set(prog_selections))
                if matched_progs:
                    pref_tags.append(f"<b>Programs</b>: {', '.join(matched_progs)}")
                    
            # Extracted Preference (parsed) Checks
            if parsed.get('sports_nsg'):
                sch_sports = sch.get('sports_achievement_2025', {}).get(gender, [])
                matched_sports = list(set(sch_sports) & set(parsed['sports_nsg']))
                if matched_sports:
                    pref_tags.append(f"<b>NSG Achievement</b>: {', '.join(matched_sports)}")
                    
            if parsed.get('arts_dist'):
                sch_arts = str(sch.get('arts_distinction_2024', '')).split('; ')
                matched_arts = list(set(sch_arts) & set(parsed['arts_dist']))
                if matched_arts:
                    pref_tags.append(f"<b>SYF Distinction</b>: {', '.join(matched_arts)}")
                    
            if parsed.get('session') and parsed.get('session') == sch.get('session_code'):
                pref_tags.append(f"<b>Session</b>: {parsed['session']}")
                
            for tag, key, ind_key in [('SAP', 'sap', 'sap_ind'), ('Autonomous', 'autonomous', 'autonomous_ind'), ('IP', 'ip', 'ip_ind')]:
                if parsed.get(key) and sch.get(ind_key) == 'Y':
                    pref_tags.append(f"<b>{tag}</b>: {parsed[key]}")
                
            if parsed.get('mt') and parsed['mt'] in str(sch.get('mother_tongue', '')):
                pref_tags.append(f"<b>MT</b>: {parsed['mt']}")

            pref_html = ""
            if pref_tags:
                pref_html = PREF_TAG_TEMPLATE.format(tags=" | 🎯 ".join(pref_tags))

            card_html = CARD_TEMPLATE.format(
                url=sch["url_address"],
                rank=i+1,
                sch_name=sch["school_name"],
                score=sch["score_total"],
                breakdown_html=breakdown_html,
                travel_time=sch["travel_time"],
                pref_html=pref_html,
                phases_html=phases_html
            )

            st.markdown(card_html, unsafe_allow_html=True)
            
    with col_map:
        st.markdown("### 🗺️ Explore the Map!")
        
        # Initialize Folium Map
        m = folium.Map(location=[user_lat, user_lon], zoom_start=14, tiles="CartoDB positron")
        
        # Add User Marker
        folium.Marker(
            [user_lat, user_lon],
            popup="🏠 Your House!",
            tooltip="You are here!",
            icon=folium.Icon(color="red", icon="home", prefix="fa")
        ).add_to(m)
        
        # Add Radius Circle
        folium.Circle(
            radius=radius_filter * 1000, # convert km to meters
            location=[user_lat, user_lon],
            color="#FF7E67",
            weight=2,
            fill=True,
            fill_color="#FF9A76",
            fill_opacity=0.05
        ).add_to(m)
        
        # Add School Markers
        for i, sch in top_schools.iterrows():
            folium.Marker(
                [sch["lat"], sch["long"]],
                popup=f"<b>#{i+1} {sch['school_name']}</b><br>Score: {sch['score_total']}",
                tooltip=f"#{i+1} {sch['school_name']}",
                icon=folium.Icon(color="green" if i == 0 else "blue", icon="graduation-cap", prefix="fa")
            ).add_to(m)
            
        # Display map as static HTML to prevent flickering on interaction
        components.html(m._repr_html_(), height=600)

    # Finally, generate the summary using the injected HTML breakdowns and display in placeholder
    with summary_placeholder.container():
        with st.spinner("🤖 Writing your personalized summary..."):
            parsed_text = generate_recommendation_summary(parsed, breakdown_htmls_for_llm)
        st.success(parsed_text)
