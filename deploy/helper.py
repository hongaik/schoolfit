from openai import OpenAI
from pydantic import BaseModel, Field, ConfigDict, field_validator, BeforeValidator
from enum import Enum
from typing import Literal, Annotated
import pandas as pd, numpy as np
import math, ast, requests
from sklearn.preprocessing import MinMaxScaler
import streamlit as st
from pathlib import Path
ROOT = Path(__file__).resolve().parent


# root = "C:/HA/MTech AIS/Intelligent Reasoning Systems/Practice Module/project/data/"
ballot_history = pd.read_csv(ROOT / 'data' / 'ballot_history.csv')

master = pd.read_csv(ROOT / 'data' / 'master.csv').fillna({'sports_achievement_2025': "{}", 'arts_distinction_2024': '', 'school_tier': '4'})
master['sports_achievement_2025'] = master['sports_achievement_2025'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)
master['nature_code'] = master['nature_code'].map({'CO-ED SCHOOL': 'MF', "BOYS' SCHOOL": 'M', "GIRLS' SCHOOL": 'F'})

# cca_list = sorted(master['cca'].str.split('; ').explode().unique().tolist())
# niche_prog_list = (master['niche_programmes'].str.split('; ').explode().unique().tolist())
arts_dist_list = (master['arts_distinction_2024'].dropna().str.split('; ').explode().unique().tolist())
sports_nsg_list = sorted(master['sports_achievement_2025']\
    .dropna()\
    .apply(lambda d: sum(d.values(), []) if isinstance(d, dict) else [])\
    .explode()\
    .dropna()\
    .unique()\
    .tolist())
sch_list = sorted(master['school_name'].unique().tolist())

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def get_onemap_token():

    url = "https://www.onemap.gov.sg/api/auth/post/getToken"
    payload = {"email": st.secrets["onemap_token_email"], "password": st.secrets["onemap_token_pwd"]}
    response = requests.post(url, json=payload).json()
    return response.get("access_token")

token = get_onemap_token()

def get_travel_time(u_lat, u_lon, s_lat, s_lon, token):
    if None in [u_lat, u_lon, s_lat, s_lon]:
        return None, None, None

    url = "https://www.onemap.gov.sg/api/public/routingsvc/route"
    headers = {"Authorization": token}

    for route_type in ['pt', 'walk']:
        params = {
            "start": f"{u_lat},{u_lon}",
            "end": f"{s_lat},{s_lon}",
            "routeType": route_type,
        }

        if route_type == "pt":
            params.update({
            "date": "01-05-2026",
            "time": "06:30:00",
            "mode": "TRANSIT",
            "maxWalkDistance": "1000",
            "numItineraries": "3"
            })

        try:
            response = requests.get(url, headers=headers, params=params).json()
        except Exception as e:
            print(f"[{route_type}] Request failed for ({s_lat}, {s_lon}): {e}")
            return None, None, None
        
        # Parse PT response
        if route_type == "pt":
            if "plan" not in response or not response["plan"].get("itineraries"):
                print(f"[pt] No route for ({s_lat}, {s_lon}): {response}")
                return None, None, None
            itineraries = response["plan"]["itineraries"]
            itinerary = min(itineraries, key=lambda x: x.get("duration", float("inf")))
            pt_total_time_min = itinerary.get("duration", 0) / 60
            legs = itinerary.get("legs", [])
            pt_total_dist_km = round(sum(leg.get("distance", 0) for leg in legs) / 1000, 2)
            pt_walk_dist_km = round(itinerary.get("walkDistance", 0) / 1000, 2)

        # Parse drive/cycle/walk response
        else:
            if "route_summary" not in response:
                print(f"[{route_type}] No route for ({s_lat}, {s_lon}): {response}")
                return None, None, None
            summary = response["route_summary"]
            walk_total_time_min = summary.get("total_time", 0) / 60
            walk_total_dist_km = round(summary.get("total_distance", 0) / 1000, 2)

    if pt_total_time_min <= walk_total_time_min:
        return ("pt", round(pt_total_time_min))
    return ("walk", round(walk_total_time_min))

def get_coordinates(postal, onemap_token=token):
    try:
        # Basic format validation (Singapore postal codes are 6 digits)
        if len(str(postal)) == 5:
            postal = '0' + str(postal)
            
        if not str(postal).isdigit() or len(str(postal)) != 6:
                return f"Invalid Postal Format Error: {postal}"

        url = f"https://www.onemap.gov.sg/api/common/elastic/search?searchVal={postal}&returnGeom=Y&getAddrDetails=N&pageNum=1"
        headers = {}
        if onemap_token:
            headers["Authorization"] = onemap_token
        
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code != 200:
            return f"OneMap API Error: Status {response.status_code}"
            
        data = response.json()
        
        if data['found'] > 0:
            result = data['results'][0]
            return float(result['X']), float(result['Y']), float(result['LATITUDE']), float(result['LONGITUDE'])
        return f"Invalid Postal Code Error: {postal}"
    except requests.exceptions.RequestException as e:
        return f"OneMap API Connection Error: {str(e)}"
    except Exception as e:
        return f"Unexpected Error: {str(e)}"

def calculate_distance(X1, X2, Y1, Y2):
    return math.sqrt((X1 - X2)**2 + (Y1 - Y2)**2) / 1000.0

def get_distance_category(distance_km):
    if distance_km < 1.0:
        return 1 # < 1km
    elif distance_km < 2.0:
        return 2 # 1-2km
    else:
        return 3 # > 2km

def get_registration_phase(school_name, citizenship, dist_to_user,
                           has_sibling, former_student, is_alumni, is_staff, is_mk, 
                           is_volunteer, is_church_clan, is_community_leader):
    """
    Determines the earliest eligible P1 registration phase and priority code.
    Returns:
        str: The priority code (e.g. "P1", "P2A-1") OR "ERROR: <Reason>"
    """
    
    # --- Validation ---
    if not isinstance(citizenship, str):
        raise TypeError("Citizenship must be a string.")
    if citizenship not in ["SC", "PR", "International"]:
        raise ValueError(f"Invalid citizenship: {citizenship}")

    # --- Logic ---
    if citizenship == "International":
        return "Phase 3"

    # Phase 1: Guaranteed (Conceptually P1 does not balloting by distance usually, but let's assign P1)
    if school_name in has_sibling:
        return "Phase 1"        

    # # Calculate Distance - Catching specific errors from the helper
    # dist, error_msg = calculate_distance(user_postal, school_postal, onemap_token)
    
    # if error_msg:
    #     return f"ERROR: {error_msg}"

    # Helper for priority suffix
    def get_suffix(d_km, ctz):
        if d_km <= 1.0:
            cat = 1 # < 1km
        elif d_km <= 2.0:
            cat = 2 # 1-2km
        else:
            cat = 3 # > 2km
        # SC: 1, 2, 3
        # PR: 4, 5, 6
        if ctz == "PR":
            return f"-{cat + 3}"
        else:
            return f"-{cat}"

    suffix = get_suffix(dist_to_user, citizenship)

    # Phase 2A
    if school_name in is_alumni or school_name in is_staff or school_name in is_mk or school_name in former_student:
        return f"Phase 2A{suffix}"

    # Phase 2B
    # Check Community Leader specific 2km rule
    valid_community_leader = is_community_leader == 'Y' and (dist_to_user < 2.0)
    
    if school_name in is_volunteer or school_name in is_church_clan or valid_community_leader:
        return f"Phase 2B{suffix}"

    # Phase 2C
    return f"Phase 2C{suffix}"
    # Note: Phase 2C Supplementary is a fallback if 2C fails, 
    # but for initial eligibility check, 2C is the phase they enter.

def extract_user_request(user_input):
    # =========================================================
    # Helper: create dynamic string Enum from list
    # =========================================================
    def make_str_enum(enum_name: str, values: list[str]):
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

    def ensure_list(v):
        if v is None or v == "":
            return []
        if isinstance(v, list):
            return v
        return [v]

    # =========================================================
    # Dynamic enums
    # =========================================================
    # CCAType = make_str_enum("CCAType", cca_list)
    # ProgType = make_str_enum("ProgType", niche_prog_list)
    ArtsDistType = make_str_enum("ArtsDistType", arts_dist_list)
    SportsNSGType = make_str_enum("SportsNSGType", sports_nsg_list)
    SchoolType = make_str_enum("SchoolType", sch_list)
    SchoolList = Annotated[list[SchoolType], BeforeValidator(ensure_list)]

    SessionType = Enum(
        "SessionType",
        {
            "BLANK": "",
            "FULL_DAY": "FULL DAY",
            "SINGLE_SESSION": "SINGLE SESSION",
        },
        type=str,
    )

    MTType = Enum(
        "MTType",
        {
            "BLANK": "",
            "CHINESE": "CHINESE",
            "MALAY": "MALAY",
            "TAMIL": "TAMIL",
        },
        type=str,
    )

    YNType = Enum(
        "YNType",
        {
            "BLANK": "",
            "Y": "Y",
            "N": "N",
        },
        type=str,
    )


    # =========================================================
    # Pydantic schema
    # =========================================================
    class SchoolPreferenceRequest(BaseModel):
        model_config = ConfigDict(use_enum_values=True)

        # cca: list[str] = Field(
        #     default_factory=list,
        #     description=(
        #         "User's preferences or interests in co-curricular activities, extracted verbatim"                
        #         "Return [] if none are mentioned."
        #     )
        # )

        # prog: list[str] = Field(
        #     default_factory=list,
        #     description=(
        #         "User's preferences or interests in niche/special programmes, extracted verbatim"            
        #         "Return [] if the user does not mention programme preferences."
        #     )
        # )

        arts_dist: list[ArtsDistType] = Field(
            default_factory=list,
            description=(
                "Arts Distinction Programme interests. Select only if the user indicates a desire for schools that "
                "are strong in a specific performing arts area (e.g. strong choir, dance, band, orchestra). "
                "Do NOT select simply because the user mentions interest in a CCA; select only if the user is "
                "looking for schools with strong arts excellence or distinction in that area. "
                "Choose zero or more values from arts_dist_list."
            )
        )

        sports_nsg: list[SportsNSGType] = Field(
            default_factory=list,
            description=(
                "Sports National School Games (NSG) interests. Select only if the user indicates a desire for schools "
                "that are strong or competitive in a particular sport (e.g. strong soccer team, competitive badminton). "
                "Do NOT select simply because the user mentions liking a sport; select only if the user is looking for "
                "schools known for strong sports performance in that area. "
                "Choose zero or more values from sports_nsg_list."
            )
        )

        session: SessionType = Field(
            default=SessionType.BLANK,
            description='Preferred school session type. Choose exactly one of: "", "FULL DAY", "SINGLE SESSION".'
        )

        sap: YNType = Field(
            default=YNType.BLANK,
            description='Whether the user prefers a SAP (Special Assistance Plan) school. Choose one of: "", "Y", "N".'
        )

        autonomous: YNType = Field(
            default=YNType.BLANK,
            description='Whether the user prefers an autonomous school. Choose one of: "", "Y", "N".'
        )

        ip: YNType = Field(
            default=YNType.BLANK,
            description='Whether the user prefers a school offering the Integrated Programme (IP) or through-train pathway. Choose one of: "", "Y", "N".'
        )

        mt: MTType = Field(
            default=YNType.BLANK,
            description='Whether the user has a preference related to mother tongue language offering. Choose one of: "", "CHINESE", "MALAY", "TAMIL".'
        )

        has_sibling: SchoolList = Field(
            default_factory=list,
            description="Schools where the user currently has another child studying."
            "Match the user's input to the reasonably closest school name in sch_list allowing for minor spelling differences."
            "Choose zero or more schools from sch_list."
        )

        former_student: SchoolList = Field(
            default_factory=list,
            description="Schools where older child or sibling previously studied (alumni)."
            "Match the user's input to the reasonably closest school name in sch_list allowing for minor spelling differences."
            "Choose zero or more schools from sch_list."
        )

        is_alumni: SchoolList = Field(
            default_factory=list,
            description="Schools where the parent is an alumnus/alumna."
            "Match the user's input to the reasonably closest school name in sch_list allowing for minor spelling differences."
            "Choose zero or more schools from sch_list."
        )

        is_staff: SchoolList = Field(
            default_factory=list,
            description="Schools where the parent currently works as a staff member."
            "Match the user's input to the reasonably closest school name in sch_list allowing for minor spelling differences."
            "Choose zero or more schools from sch_list."
        )

        is_mk: SchoolList = Field(
            default_factory=list,
            description="Schools where the child is studying in the MOE Kindergarten in that primary school. "
            "Match the user's input to the reasonably closest school name in sch_list allowing for minor spelling differences."
            "Choose zero or more schools from sch_list."
        )

        is_volunteer: SchoolList = Field(
            default_factory=list,
            description="Schools where the parent volunteers."
            "Match the user's input to the reasonably closest school name in sch_list allowing for minor spelling differences."
            "Choose zero or more schools from sch_list."
        )

        is_church_clan: SchoolList = Field(
            default_factory=list,
            description="Schools affiliated with the parent's church or clan."
            "Match the user's input to the reasonably closest school name in sch_list allowing for minor spelling differences."
            "Choose zero or more schools from sch_list."
        )

        is_community_leader: YNType = Field(
            default=YNType.BLANK,
            description='Whether the parent is an endorsed active community leader. Choose one of: "", "Y", "N".'
        )

    # Return empty structure if input is blank
    if not str(user_input).strip():
        return SchoolPreferenceRequest().model_dump(mode="json")

    # =========================================================
    # Prompts
    # =========================================================
    sys_prompt = """
    You are extracting structured Singapore primary school admission preferences from a user's natural-language query.

    Follow these rules strictly:
    - Return output that conforms exactly to the provided schema.
    - Use only values allowed by the schema enums and field definitions.
    - For list fields, return [] when the user does not clearly mention a value.
    - For single-value fields, return "" when the user does not clearly mention a value.
    - Be conservative: do not infer existence of a preferences unless they are explicitly stated or strongly implied.
    - However, when the user specifies a preference or a broad domain (e.g. STEM, arts, sports), return all allowed values in the list that fall under that domain.
    - Always prefer returning multiple plausible matches rather than returning an empty list when a clear domain preference is stated.
    - Do not expand beyond the domain mentioned by the user.

    Interpretation rules:
    - cca: activities the user wants the child to participate in. Extract verbatim.
    - prog: school programmes, learning-focus preferences. Extract verbatim.
    - arts_dist: select only when the user wants schools that are strong/distinguished in that arts area, not merely because the user likes that CCA.
    - sports_nsg: select only when the user wants schools that are strong/competitive in that sport, not merely because the user likes that sport.
    - has_sibling: sibling currently studying in that school.
    - former_student: older sibling previously studied there (alumni) but no longer does.
    - is_alumni: parent is alumni of that school.
    - is_staff: parent is currently staff of that school.
    - is_mk: child attended or is attending an MOE Kindergarten linked to that school.
    - is_volunteer: parent volunteered at that school.
    - is_church_clan: school affiliation via church or clan connection.
    - is_community_leader: choose "Y" only if the user indicates this applies; choose "N" only if the user explicitly rules it out.

    If the user mentions multiple schools for a school-list field, return all of them.
    If the user mentions multiple values for a multi-select field, return all of them.
    """
    user_prompt = f"""
    Extract the user's school preferences from the following query.

    User query:
    {user_input}
    """

    # =========================================================
    # Structured output call
    # =========================================================
    response = client.responses.parse(
        model="gpt-5-mini",
        input=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
        text_format=SchoolPreferenceRequest,
    )

    return response.output_parsed.model_dump(mode="json")

def generate_recommendation_summary(parsed_preferences, breakdown_htmls):
    """
    Generates a natural language summary explaining why the top schools 
    were recommended based on the user's extracted preferences and breakdown HTMLs.
    """
    # Format preferences to send to LLM
    pref_strings = []
    for k, v in parsed_preferences.items():
        if v:
            if isinstance(v, list) and len(v) > 0:
                pref_strings.append(f"- {k}: {', '.join(v)}")
            elif not isinstance(v, list):
                pref_strings.append(f"- {k}: {v}")
    
    pref_text = "\n".join(pref_strings) if pref_strings else "No specific strong preferences provided."

    schools_text = "\n\n".join(breakdown_htmls)

    sys_prompt = """
    You are an analytical Singapore primary school admissions AI assistant named 'SchoolFit SG'.
    Your task is to write a highly factual, explanatory, and concise summary (exactly 3-5 bullet points) explaining 
    exactly why the top schools were recommended based strictly on the user's provided preferences and the data provided in the breakdown HTML.

    EXPLANATION FOR RANKING FACTORS:
    SchoolFit SG computes a personalized match score (out of 100) using a normalized, weighted average of your preferences:

    - Travel Time: Schools with shorter travel time (in minutes) score higher. We compute travel time using OneMap API routing service, which may differ slightly from Google Maps. Schools may be closer by distance but have longer travel times due to public transport connectivity.
    - CCAs & Programs: Schools which offer more of your desired Co-Curricular Activities and Niche Programmes (ALP, LLP) score higher.
    - Sports & Arts Excellence: Schools with strong National School Games (NSG) and Singapore Youth Festival (SYF) achievements in your desired CCA score higher, if specified.
    - School Characteristics: Schools with your preferred characteristics like Session Time, Special Assistance Plan (SAP), Autonomous, and Integrated Programme (IP) status score higher if specified.
    - Mother Tongue: Schools offering your specified Mother Tongue language score higher.
    
    CRITICAL RULES:
    1. Adopt a factual, and objective tone. Do not use conversational filler, fluff, or excessive encouragement.
    2. Format your entire output as an unnumbered bulleted list (using standard `-` bullets).
    3. Output 3 to 5 bullet points.
    4. Base your analysis entirely on the "Score Breakdown" HTML tables provided for each school. Look at the Wt (Weight), Val (Value), and Norm Val (Normalized Value) to explain the recommendations.
    6. When mentioning about schools, only use raw values (C) to explain. Do not mention about weights, normalised values or score (total score is okay).
    7. Values usually indicate number of matches, presence of certain characteristics, or travel time in minutes.

    MUST HAVE:
    1. Instead of quoting excessive values, help your reader understand simply what the values mean in the context. (e.g. higher weightage, 3 matches)
    """

    user_prompt = f"""
    Parent's Extracted Preferences:
    {pref_text}

    Top Recommended Schools (with Score Breakdown HTMLs):
    {schools_text}
    
    Write the factual summary explaining the recommendations (3-5 bullet points).
    """

    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"- We found some great options for you!\n- (Note: Detailed AI summary temporarily unavailable due to {e})"
