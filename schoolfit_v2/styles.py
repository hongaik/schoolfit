"""HTML/CSS templates for the SchoolFit v2 UI."""

# =============================================================================
# CSS
# =============================================================================

CUSTOM_CSS = """
<style>
a.header-anchor { display: none !important; }

.stApp {
    background-color: #F7FBFF;
    font-family: 'Nunito', 'Segoe UI', sans-serif !important;
}
h1, h2, h3, h4, h5, h6 { color: #4A90E2; font-weight: 800 !important; }

[data-testid="stSidebar"] {
    background-color: #E8F4F8;
    border-right: 3px dashed #B3D4E0;
}

.stTextInput > label, .stSelectbox > label,
.stSlider > label, .stTextArea > label {
    color: #FF7E67 !important;
    font-size: 16px !important;
    font-weight: 700 !important;
}

div.stButton > button:first-child {
    background-color: #FF9A76;
    color: white;
    border-radius: 20px;
    border: 3px solid #FF7E67;
    font-size: 20px;
    font-weight: bold;
    padding: 10px 20px;
    width: 100%;
    transition: all 0.3s ease;
}
div.stButton > button:first-child:hover {
    background-color: #FF7E67;
    transform: scale(1.03);
    border: 3px solid #E85D44;
}

.school-card {
    background-color: #FFFFFF;
    padding: 18px 20px;
    border-radius: 15px;
    box-shadow: 0px 4px 12px rgba(0,0,0,0.08);
    margin-bottom: 18px;
    border-left: 7px solid #FFCD3C;
    transition: transform 0.2s;
}
.school-card:hover { transform: translateY(-4px); }

.school-title {
    color: #FF7E67;
    font-size: 20px;
    font-weight: bold;
    margin-bottom: 4px;
}
.school-score {
    color: #4A90E2;
    font-size: 16px;
    font-weight: bold;
    display: flex;
    align-items: center;
    gap: 6px;
}
.tooltip-container {
    position: relative;
    display: inline-block;
    cursor: help;
}
.score-icon {
    display: inline-block;
    width: 17px; height: 17px;
    line-height: 17px;
    text-align: center;
    border-radius: 50%;
    background-color: #E8F4F8;
    color: #4A90E2;
    font-size: 11px;
    font-weight: bold;
    border: 1px solid #4A90E2;
}
.tooltip-container .tooltip {
    visibility: hidden;
    width: 270px;
    background-color: #333;
    color: #fff;
    text-align: left;
    border-radius: 6px;
    padding: 10px;
    position: absolute;
    z-index: 100;
    bottom: 130%;
    left: 50%;
    margin-left: -135px;
    opacity: 0;
    transition: opacity 0.25s;
    font-size: 12px;
    font-weight: normal;
    line-height: 1.5;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
}
.tooltip-container:hover .tooltip { visibility: visible; opacity: 1; }

.signal-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: bold;
    margin-top: 6px;
}
.sig-guaranteed { background: #D4EDDA; color: #155724; }
.sig-likely      { background: #CCE5FF; color: #004085; }
.sig-competitive { background: #FFF3CD; color: #856404; }
.sig-difficult   { background: #F8D7DA; color: #721C24; }
.sig-unknown     { background: #E2E3E5; color: #383D41; }

.phase-row {
    display: flex;
    justify-content: space-between;
    background: #F8F9FA;
    padding: 8px 10px;
    border-radius: 8px;
    margin-top: 10px;
    font-size: 12px;
    text-align: center;
}
.phase-item { flex: 1; }
.phase-label { color: #7F8C8D; margin-bottom: 2px; }
.phase-val   { font-weight: bold; color: #2C2C2C; }
.phase-active .phase-label { color: #FF7E67; font-weight: bold; }
.phase-active .phase-val   { color: #FF7E67; }
</style>
"""

# =============================================================================
# Static HTML
# =============================================================================

TITLE_HTML    = "<h1 style='text-align:center;padding-top:15px;pointer-events:none;'>🎒 SchoolFit SG 🌟</h1>"
SUBTITLE_HTML = "<h4 style='text-align:center;color:#7F8C8D;pointer-events:none;'>AI-powered P1 school matching for Singapore families</h4>"

LANDING_HTML = """
<div style="text-align:center;padding:40px 20px;">
  <h3 style="pointer-events:none;">
    Tell us about your child in the box above to start your adventure! 📖✨
  </h3>
  <p style="color:#7F8C8D;font-size:15px;">
    e.g. "My daughter lives in Toa Payoh (310123), she's a SC, loves swimming
    and choir. Really important the school is close to home."
  </p>
</div>
"""

# =============================================================================
# Card templates
# =============================================================================

SCORE_BREAKDOWN_TABLE = (
    '<div style="font-weight:bold;margin-bottom:6px;text-align:center;'
    'border-bottom:2px solid #777;padding-bottom:4px;">Score Breakdown</div>'
    '<table style="width:100%;font-size:12px;color:white;border-collapse:collapse;">'
    '<tr style="color:#ccc;border-bottom:1px solid #777;">'
    '<th style="padding:3px;text-align:left;">Dimension</th>'
    '<th style="padding:3px;text-align:center;">Wt</th>'
    '<th style="padding:3px;text-align:center;">Val</th>'
    '<th style="padding:3px;text-align:right;">Score</th>'
    '</tr>{rows}'
    '<tr style="font-weight:bold;background:#555;">'
    '<td colspan="3" style="padding:5px 3px;text-align:right;">Total</td>'
    '<td style="padding:5px 3px;text-align:right;">{total:.1f}</td>'
    '</tr></table>'
)

SCORE_ROW = (
    '<tr style="border-bottom:1px solid #555;">'
    '<td style="padding:3px;text-align:left;">{name}</td>'
    '<td style="padding:3px;text-align:center;">{weight}</td>'
    '<td style="padding:3px;text-align:center;">{val}</td>'
    '<td style="padding:3px;text-align:right;">{score:.1f}</td>'
    '</tr>'
)

CARD_TEMPLATE = (
    '<a href="{url}" target="_blank" style="text-decoration:none;color:inherit;">'
    '<div class="school-card">'
    '<div class="school-title"><span style="color:#2C2C2C;">#{rank}</span> {name}</div>'
    '<div class="school-score">'
    '<span>Score: {score}</span>'
    '<span class="tooltip-container">'
    '<span class="score-icon">?</span>'
    '<span class="tooltip">{breakdown}</span>'
    '</span>'
    '</div>'
    '<div style="color:#7F8C8D;margin-top:4px;font-size:13px;">'
    '📍 {travel_time} min · {travel_mode} &nbsp;|&nbsp; '
    '{signal_badge} &nbsp;|&nbsp; 🗓️ {phase}'
    '</div>'
    '{tags_html}'
    '{phase_row_html}'
    '</div></a>'
)

SIGNAL_BADGE = '<span class="signal-badge sig-{css_class}">{label}</span>'

PHASE_ROW = '<div class="phase-row">{items}</div>'
PHASE_ITEM = (
    '<div class="phase-item{active_class}">'
    '<div class="phase-label">{label}</div>'
    '<div class="phase-val">{val}</div>'
    '</div>'
)

TAGS_HTML = '<div style="color:#6C7A89;font-size:12px;margin-top:6px;">🎯 {tags}</div>'

INFO_MARKDOWN = """\
**SchoolFit SG** computes a personalized match score (out of 100) using a
normalized, weighted average across 11 dimensions:

- **Travel Time** — shorter travel = higher score (via OneMap routing)
- **CCA Match** — count of your desired CCAs offered by the school
- **Programme Match** — count of ALP/LLP programmes matching your interests
- **PSLE Tier** — school's academic tier (Tier 1 highest)
- **Sports Excellence** — NSG achievements in your desired sport
- **Arts Excellence** — SYF distinctions in your desired arts form
- **Session / SAP / Autonomous / IP / Mother Tongue** — binary matches to preferences

Weights are inferred from how strongly you expressed each preference.
You can review and adjust them in the sidebar before re-running.

The **Admission Profile** (phase and ballot odds) is displayed for each school
as information only — it does **not** affect the rank.
"""
