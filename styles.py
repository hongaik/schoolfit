custom_css = """
    <style>
    /* Hide Streamlit Header Anchor Links */
    a.header-anchor {
        display: none !important;
    }
    
    /* Main Background */
    .stApp {
        background-color: #F7FBFF;
        font-family: 'Nunito', 'Comic Sans MS', sans-serif !important;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #4A90E2;
        font-weight: 800 !important;
    }
    
    /* Sidebar Background */
    [data-testid="stSidebar"] {
        background-color: #E8F4F8;
        border-right: 3px dashed #B3D4E0;
    }
    
    /* Input Labels */
    .stTextInput > label, .stSelectbox > label, .stSlider > label, .stTextArea > label {
        color: #FF7E67 !important;
        font-size: 18px !important;
        font-weight: 700 !important;
    }
    
    /* The Big "Find Schools" Button */
    div.stButton > button:first-child {
        background-color: #FF9A76;
        color: white;
        border-radius: 20px;
        border: 3px solid #FF7E67;
        font-size: 22px;
        font-weight: bold;
        padding: 10px 20px;
        width: 100%;
        transition: all 0.3s ease;
    }
    
    div.stButton > button:first-child:hover {
        background-color: #FF7E67;
        transform: scale(1.05);
        color: white;
        border: 3px solid #E85D44;
    }
    
    /* Custom Container for School Results */
    .school-card {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        border-left: 8px solid #FFCD3C;
        transition: transform 0.2s;
    }
    .school-card:hover {
        transform: translateY(-5px);
    }
    .school-title {
        color: #FF7E67;
        font-size: 22px;
        font-weight: bold;
        margin-bottom: 5px;
    }
    .school-score {
        color: #4A90E2;
        font-size: 18px;
        font-weight: bold;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    .tooltip-container {
        position: relative;
        display: inline-block;
        cursor: help;
    }
    .score-icon {
        display: inline-block;
        width: 18px;
        height: 18px;
        line-height: 18px;
        text-align: center;
        border-radius: 50%;
        background-color: #E8F4F8;
        color: #4A90E2;
        font-size: 12px;
        font-weight: bold;
        border: 1px solid #4A90E2;
    }
    .tooltip-container .tooltip {
        visibility: hidden;
        width: 260px;
        background-color: #444;
        color: #fff;
        text-align: left;
        border-radius: 6px;
        padding: 10px;
        position: absolute;
        z-index: 10;
        bottom: 130%; /* Position above the icon */
        left: 50%;
        margin-left: -130px; /* Center the tooltip */
        opacity: 0;
        transition: opacity 0.3s;
        font-size: 13px;
        font-weight: normal;
        line-height: 1.4;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
    }
    .tooltip-container:hover .tooltip {
        visibility: visible;
        opacity: 1;
    }
    .school-phase {
        display: inline-block;
        background-color: #FFCD3C;
        color: #8E5A00;
        padding: 4px 10px;
        border-radius: 10px;
        font-weight: bold;
        font-size: 14px;
        margin-top: 10px;
    }
    
    /* Mobile Responsive adjustments */
    @media (max-width: 768px) {
        .stColumns {
            flex-direction: column !important;
        }
    }
    </style>
"""

TITLE_HTML = "<h1 style='text-align: center; padding-top: 15px; pointer-events: none;'>🎒 SchoolFit SG 🌟</h1>"
SUBTITLE_HTML = "<h4 style='text-align: center; color: #7F8C8D; pointer-events: none;'>Let's find your perfect school!</h4>"

LANDING_HTML = """
<div style="text-align: center; padding: 50px;">
    <h3 style="pointer-events: none;">Fill in the magic book on the left to start your adventure! 📖✨</h3>
</div>
"""

INFO_MARKDOWN = """
***SchoolFit SG*** *computes a personalized match score (out of 100) using a normalized, weighted average of your preferences:*

- ***Travel Time***: *Schools with shorter travel time score higher. We compute travel time using OneMap API routing service, which may differ slightly from Google Maps. Schools may be closer by distance but have longer travel times due to public transport connectivity.*
- ***CCAs & Programs***: *Schools which offer more of your desired Co-Curricular Activities and Niche Programmes (ALP, LLP) score higher.*
- ***Sports & Arts Excellence***: *Schools with strong National School Games (NSG) and Singapore Youth Festival (SYF) achievements in your desired CCA score higher, if specified.*
- ***School Characteristics***: *Schools with your preferred characteristics like Session Time, Special Assistance Plan (SAP), Autonomous, and Integrated Programme (IP) status score higher if specified.*
- ***Mother Tongue***: *Schools offering your specified Mother Tongue language score higher.*

*The sliders in the sidebar control how much weight each category carries in your final score!*
"""

TABLE_ROW_TEMPLATE = '<tr style="border-bottom: 1px solid #555;"><td style="padding: 4px; text-align: left;">{name}</td><td style="padding: 4px; text-align: center;">{weight}</td><td style="padding: 4px; text-align: center;">{disp_val}</td><td style="padding: 4px; text-align: center;">{raw_val:.1f}</td><td style="padding: 4px; text-align: right;">{w_score:.1f}</td></tr>'

BREAKDOWN_TABLE_TEMPLATE = '<div style="font-weight: bold; margin-bottom: 8px; text-align: center; border-bottom: 2px solid #777; padding-bottom: 5px;">Score Breakdown</div><table style="width: 100%; font-size: 13px; color: white; border-collapse: collapse;"><tr style="color: #ccc; border-bottom: 1px solid #777;"><th style="padding: 4px; text-align: left;">Item (A)</th><th style="padding: 4px; text-align: center;">Wt (B)</th><th style="padding: 4px; text-align: center;">Val (C)</th><th style="padding: 4px; text-align: center;">Norm Val (D)</th><th style="padding: 4px; text-align: right;">Score (B*D)</th></tr>{table_rows}<tr style="font-weight: bold; color: #FFF; background-color: #555;"><td colspan="4" style="padding: 6px 4px; text-align: right; border-bottom-left-radius: 4px;">Total:</td><td style="padding: 6px 4px; text-align: right; border-bottom-right-radius: 4px;">{total_score:.1f}</td></tr></table>'

PHASE_DIV_TEMPLATE = '<div><div style="font-weight: {weight}; color: {color}; font-size: 13px; margin-bottom: 5px;">{phase_name} {star}</div><div style="font-size: 16px; font-weight: bold; color: {c_color};">{val}</div></div>'

PHASES_TOOLTIP_TEMPLATE = '<div class="tooltip-container" style="display: block; width: 100%;"><div style="display: flex; justify-content: space-between; text-align: center; margin-top: 15px; background-color: #F8F9FA; padding: 10px; border-radius: 8px;">{p1}{p2a}{p2b}{p2c}{p2cs}{p3}</div><span class="tooltip" style="width: 300px; margin-left: -150px; bottom: 100%; font-size: 12px; font-weight: normal; text-align: center; line-height: 1.5;">{tooltip_text}</span></div>'

PREF_TAG_TEMPLATE = '<div style="color: #6C7A89; font-size: 13px; margin-top: 8px;">🎯 {tags}</div>'

CARD_TEMPLATE = '<a href="{url}" target="_blank" style="text-decoration: none; color: inherit;"><div class="school-card"><div class="school-title"><span style="color: #2C2C2C;">#{rank}</span> {sch_name}</div><div class="school-score"><span>Score: {score}    </span><span class="tooltip-container"><span class="score-icon">?</span><span class="tooltip">{breakdown_html}</span></span></div><div style="color: #7F8C8D; margin-top: 5px;">📍 Travel time: {travel_time} mins</div>{pref_html}{phases_html}</div></a>'
