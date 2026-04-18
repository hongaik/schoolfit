"""
Form-based input validation and UserIntent builder.
Validates form data and builds structured UserIntent from form fields.
Uses LLM (same as deploy/) to extract structured preferences from free-text bonus box.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Annotated, Tuple

from pydantic import BaseModel, ConfigDict, Field, BeforeValidator

from api_clients import get_llm, get_onemap_token
from state import UserIntent
import requests


def get_coordinates(postal_code: str) -> Tuple[float, float, float, float] | str:
    """
    Geocode a Singapore postal code using OneMap API.
    Returns: (X, Y, latitude, longitude) in SVY21 + WGS84 format, or error string.
    """
    # Format validation
    postal = str(postal_code).strip()

    # Handle 5-digit postcodes (prepend 0)
    if len(postal) == 5 and postal.isdigit():
        postal = "0" + postal

    if not postal.isdigit() or len(postal) != 6:
        return f"Invalid postal code format: {postal} (must be 6 digits)"

    # OneMap search endpoint
    url = f"https://www.onemap.gov.sg/api/common/elastic/search?searchVal={postal}&returnGeom=Y&getAddrDetails=N&pageNum=1"

    token = get_onemap_token()
    headers = {}
    if token:
        headers["Authorization"] = token

    try:
        response = requests.get(url, headers=headers, timeout=5)

        if response.status_code != 200:
            return f"OneMap API error: Status {response.status_code}"

        data = response.json()

        if data.get("found", 0) > 0:
            result = data["results"][0]
            return (
                float(result["X"]),  # SVY21 X
                float(result["Y"]),  # SVY21 Y
                float(result["LATITUDE"]),  # WGS84 latitude
                float(result["LONGITUDE"]),  # WGS84 longitude
            )

        return f"Postal code not found: {postal}"

    except requests.exceptions.RequestException as e:
        return f"OneMap connection error: {str(e)}"
    except Exception as e:
        return f"Error geocoding postal code: {str(e)}"


def _make_str_enum(enum_name: str, values: list[str]):
    seen = set()
    members = {}
    counter = 0
    for v in values:
        v = str(v).strip()
        if v and v not in seen:
            members[f"V_{counter}"] = v
            seen.add(v)
            counter += 1
    return Enum(enum_name, members, type=str)


def parse_bonus_preferences(pref_text: str) -> dict:
    """
    Parse bonus preferences text using LLM structured extraction (same as deploy/).
    Returns dict with keys: has_sibling, former_student, is_alumni, is_staff, is_mk,
    is_volunteer, is_church_clan, is_community_leader, session, sap, autonomous, ip,
    mother_tongue, sports_nsg, arts_dist.
    """
    from data_loader import load_arts_dist_list, load_school_list, load_sports_nsg_list

    _empty: dict = {
        "has_sibling": [], "former_student": [], "is_alumni": [], "is_staff": [],
        "is_mk": [], "is_volunteer": [], "is_church_clan": [], "is_community_leader": "",
        "session": "", "sap": "", "autonomous": "", "ip": "", "mother_tongue": "",
        "sports_nsg": [], "arts_dist": [],
    }

    if not pref_text or not pref_text.strip():
        return _empty

    # ── Build dynamic enums from live data ──────────────────────────────────
    sch_list = load_school_list()
    arts_dist_list = load_arts_dist_list()
    sports_nsg_list = load_sports_nsg_list()

    ArtsDistType = _make_str_enum("ArtsDistType", arts_dist_list)
    SportsNSGType = _make_str_enum("SportsNSGType", sports_nsg_list)
    SchoolType = _make_str_enum("SchoolType", sch_list)

    def _ensure_list(v):
        if v is None or v == "":
            return []
        return v if isinstance(v, list) else [v]

    SchoolList = Annotated[list[SchoolType], BeforeValidator(_ensure_list)]

    SessionType = Enum("SessionType", {"BLANK": "", "FULL_DAY": "FULL DAY", "SINGLE_SESSION": "SINGLE SESSION"}, type=str)
    MTType = Enum("MTType", {"BLANK": "", "CHINESE": "CHINESE", "MALAY": "MALAY", "TAMIL": "TAMIL"}, type=str)
    YNType = Enum("YNType", {"BLANK": "", "Y": "Y", "N": "N"}, type=str)

    class SchoolPreferenceRequest(BaseModel):
        model_config = ConfigDict(use_enum_values=True)

        arts_dist: list[ArtsDistType] = Field(default_factory=list, description="Arts Distinction Programme interests. Select only if the user wants schools strong in a specific performing arts area. Choose zero or more values.")
        sports_nsg: list[SportsNSGType] = Field(default_factory=list, description="Sports NSG interests. Select only if the user wants schools strong/competitive in a particular sport. Choose zero or more values.")
        session: SessionType = Field(default=SessionType.BLANK, description='Preferred school session. One of: "", "FULL DAY", "SINGLE SESSION".')
        sap: YNType = Field(default=YNType.BLANK, description='SAP school preference. One of: "", "Y", "N".')
        autonomous: YNType = Field(default=YNType.BLANK, description='Autonomous school preference. One of: "", "Y", "N".')
        ip: YNType = Field(default=YNType.BLANK, description='Integrated Programme preference. One of: "", "Y", "N".')
        mt: MTType = Field(default=MTType.BLANK, description='Mother tongue preference. One of: "", "CHINESE", "MALAY", "TAMIL".')
        has_sibling: SchoolList = Field(default_factory=list, description="Schools where the user currently has a child studying.")
        former_student: SchoolList = Field(default_factory=list, description="Schools where an older sibling previously studied.")
        is_alumni: SchoolList = Field(default_factory=list, description="Schools where the parent is an alumnus/alumna.")
        is_staff: SchoolList = Field(default_factory=list, description="Schools where the parent works as staff.")
        is_mk: SchoolList = Field(default_factory=list, description="Schools where the child attends the MOE Kindergarten.")
        is_volunteer: SchoolList = Field(default_factory=list, description="Schools where the parent volunteers.")
        is_church_clan: SchoolList = Field(default_factory=list, description="Schools affiliated with the parent's church or clan.")
        is_community_leader: YNType = Field(default=YNType.BLANK, description='Parent is endorsed active community leader. One of: "", "Y", "N".')

    sys_prompt = """You are extracting structured Singapore primary school admission preferences from a user's natural-language query.

Follow these rules strictly:
- Return output that conforms exactly to the provided schema.
- Use only values allowed by the schema enums and field definitions.
- For list fields, return [] when the user does not clearly mention a value.
- For single-value fields, return "" when the user does not clearly mention a value.
- Be conservative: do not infer preferences unless explicitly stated or strongly implied.
- has_sibling: sibling currently studying in that school.
- former_student: older sibling previously studied there but no longer does.
- is_alumni: parent is alumni of that school.
- is_staff: parent is currently staff of that school.
- is_mk: child attended or is attending an MOE Kindergarten linked to that school.
- is_volunteer: parent volunteered at that school.
- is_church_clan: school affiliation via church or clan connection.
- is_community_leader: choose "Y" only if clearly stated."""

    user_prompt = f"Extract the user's school preferences from the following query.\n\nUser query:\n{pref_text}"

    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(SchoolPreferenceRequest)
        result_obj = structured_llm.invoke([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ])
        data = result_obj.model_dump(mode="json")
        # Remap 'mt' key to 'mother_tongue' to match existing interface
        data["mother_tongue"] = data.pop("mt", "")
        return data
    except Exception as e:
        print(f"[LLM extraction] Failed: {e}", flush=True)
        return _empty


def validate_form_data(form_data: dict) -> Tuple[bool, str]:
    """
    Validate form data.
    Returns (is_valid, error_message).
    """
    # Validate postal code format
    postal = str(form_data.get("postal_code", "")).strip()
    if not postal:
        return False, "Postal code is required"
    if not re.match(r"^\d{5,6}$", postal):
        return False, "Postal code must be 5-6 digits"

    # Validate gender
    gender = form_data.get("gender", "")
    if gender not in ("M", "F"):
        return False, "Gender must be 'M' or 'F'"

    # Validate citizenship
    citizenship = form_data.get("citizenship", "")
    if citizenship not in ("SC", "PR", "International"):
        return False, "Citizenship must be 'SC', 'PR', or 'International'"

    # Validate radius
    radius = form_data.get("radius_km", 3.0)
    try:
        radius_float = float(radius)
        if radius_float < 0.5 or radius_float > 10.0:
            return False, "Distance radius must be between 0.5 and 10 km"
    except ValueError:
        return False, "Distance radius must be a number"

    # Validate top_n
    top_n = form_data.get("top_n", 5)
    try:
        top_n_int = int(top_n)
        if top_n_int < 1 or top_n_int > 10:
            return False, "Top N must be between 1 and 10"
    except ValueError:
        return False, "Top N must be an integer"

    # Validate weights (all should be 0-5)
    weight_keys = [
        "w_dist", "w_cca", "w_prog", "w_psle_tier",
        "w_sports", "w_arts", "w_session", "w_sap",
        "w_autonomous", "w_ip", "w_mt"
    ]
    for key in weight_keys:
        try:
            w = int(form_data.get(key, 0))
            if w < 0 or w > 5:
                return False, f"{key} must be between 0 and 5"
        except ValueError:
            return False, f"{key} must be an integer"

    return True, ""


def build_user_intent(form_data: dict) -> Tuple[UserIntent | None, str]:
    """
    Build a UserIntent object from validated form data.
    Returns (intent, error_message).
    """
    # Validate form data first
    is_valid, error_msg = validate_form_data(form_data)
    if not is_valid:
        return None, error_msg

    # Geocode postal code
    coords = get_coordinates(form_data["postal_code"])
    if isinstance(coords, str):  # Error string
        return None, coords

    # Parse bonus preferences
    pref_text = form_data.get("pref_text", "")
    parsed_prefs = parse_bonus_preferences(pref_text)

    # Combine activities (CCA selections + programme selections)
    cca_selections = form_data.get("cca_selections", [])
    prog_selections = form_data.get("prog_selections", [])
    activities = list(cca_selections) + list(prog_selections)

    # Build UserIntent
    try:
        intent = UserIntent(
            # Core demographics
            gender=form_data["gender"],
            postal_code=form_data["postal_code"],
            citizenship=form_data.get("citizenship", "SC"),
            activities=activities,

            # Search config
            top_n=int(form_data.get("top_n", 5)),
            radius_km=float(form_data.get("radius_km", 3.0)),

            # Weights — auto-bump binary dimensions to 3 if LLM extracted a preference
            # but the user left the slider at 0 (so extracted preferences actually affect scoring)
            w_dist=float(form_data.get("w_dist", 3)),
            w_cca=float(form_data.get("w_cca", 3)),
            w_prog=float(form_data.get("w_prog", 3)),
            w_psle_tier=float(form_data.get("w_psle_tier", 3)),
            w_sports=float(form_data.get("w_sports", 0)),
            w_arts=float(form_data.get("w_arts", 0)),
            w_session=float(form_data.get("w_session", 0)) or (3.0 if parsed_prefs.get("session") else 0.0),
            w_sap=float(form_data.get("w_sap", 0)) or (3.0 if parsed_prefs.get("sap") else 0.0),
            w_autonomous=float(form_data.get("w_autonomous", 0)) or (3.0 if parsed_prefs.get("autonomous") else 0.0),
            w_ip=float(form_data.get("w_ip", 0)) or (3.0 if parsed_prefs.get("ip") else 0.0),
            w_mt=float(form_data.get("w_mt", 0)) or (3.0 if parsed_prefs.get("mother_tongue") else 0.0),

            # Preferences — if slider > 0 but bonus text didn't specify, default to "Y"
            # so the scoring rule has a non-empty value to match against
            session=parsed_prefs.get("session", ""),  # must come from bonus text — slider alone can't infer which session
            sap=parsed_prefs.get("sap", "") or ("Y" if float(form_data.get("w_sap", 0)) > 0 else ""),
            autonomous=parsed_prefs.get("autonomous", "") or ("Y" if float(form_data.get("w_autonomous", 0)) > 0 else ""),
            ip=parsed_prefs.get("ip", "") or ("Y" if float(form_data.get("w_ip", 0)) > 0 else ""),
            mother_tongue=parsed_prefs.get("mother_tongue", ""),

            # Family context
            has_sibling=parsed_prefs.get("has_sibling", []),
            former_student=parsed_prefs.get("former_student", []),
            is_alumni=parsed_prefs.get("is_alumni", []),
            is_staff=parsed_prefs.get("is_staff", []),
            is_mk=parsed_prefs.get("is_mk", []),
            is_volunteer=parsed_prefs.get("is_volunteer", []),
            is_church_clan=parsed_prefs.get("is_church_clan", []),
            is_community_leader=parsed_prefs.get("is_community_leader", ""),

            # Gender school preference
            prefer_same_gender_school=form_data.get("prefer_same_gender_school", False),
        )

        return intent, ""
    except Exception as e:
        return None, f"Error building intent: {str(e)}"
