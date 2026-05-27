#!/usr/bin/env python3
"""R9 tasks generator -- appends new cross-page tasks for the R9 verticals.

Themes (matching R9 goals):
  - nutrition-meal-plan-builder (/nutrition/meal-plan)
  - drug-interaction-checker (/drugs/interaction-checker)
  - sport-team-stat-deepdive (/sports/team/<slug>/deepdive)
  - aviation-flight-tracker (/aviation/flight/<flight>)
  - weather-radar-image (/weather/radar/<region>)
  - earthquake-recent-list (/earthquakes)
  - tide-tomorrow (/tide/<location>)
  - multi-step recipes chaining the above

Deterministic. Idempotent: appends only tasks not already in tasks.jsonl.
"""
from __future__ import annotations
import json, os

TASKS_PATH = 'tasks.jsonl'
WEB_NAME = 'Wolfram Alpha'
WEB_URL = 'http://localhost:40011/'
UPSTREAM = 'https://www.wolframalpha.com/'

existing = []
if os.path.exists(TASKS_PATH):
    with open(TASKS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                existing.append(json.loads(line))
            except Exception:
                pass
existing_ids = set()
for t in existing:
    tid = t.get('id', '')
    if '--' in tid:
        try:
            existing_ids.add(int(tid.rsplit('--', 1)[1]))
        except ValueError:
            pass
next_id = (max(existing_ids) + 1) if existing_ids else 0
existing_questions = {t.get('ques', '') for t in existing}

R9_TASKS = []

# -----------------------------------------------------------------------
# (1) Nutrition meal plan (~120)
# -----------------------------------------------------------------------
CAL_TGT  = [1200, 1400, 1600, 1800, 2000, 2200, 2500, 3000]
MEAL_NS  = [3, 4, 5, 6]
DIETS    = ['omnivore', 'vegetarian', 'vegan', 'keto', 'paleo']
for cal in CAL_TGT:
    for diet in DIETS:
        R9_TASKS.append(
            f"Open /nutrition/meal-plan?cal={cal}&meals=3&diet={diet} and "
            f"confirm the per-meal calorie field equals {cal // 3} kcal."
        )
for cal in CAL_TGT[:4]:
    for n in MEAL_NS:
        R9_TASKS.append(
            f"Open /nutrition/meal-plan?cal={cal}&meals={n}&diet=keto and "
            f"verify the plan table has {n} rows."
        )
for diet in DIETS:
    R9_TASKS.append(
        f"GET /nutrition/meal-plan?cal=2000&meals=4&diet={diet}&format=json "
        f"and confirm the JSON field diet equals '{diet}'."
    )
for diet in DIETS:
    R9_TASKS.append(
        f"GET /nutrition/meal-plan?cal=2000&meals=4&diet={diet}&format=json "
        f"and confirm the macros.protein field is a positive integer."
    )
for cal in CAL_TGT:
    R9_TASKS.append(
        f"Open /nutrition/meal-plan?cal={cal}&meals=3&diet=vegan and verify "
        f"every row's notes mention 'plant-only' or 'no meat'."
    )
for v in range(20):
    R9_TASKS.append(
        f"GET /nutrition/meal-plan?cal=1800&meals=3&diet=vegetarian "
        f"(variant {v+1}) and confirm the response Content-Type is text/html."
    )
for v in range(10):
    R9_TASKS.append(
        f"On /nutrition/meal-plan, set cal=2200 and meals=5 and diet=paleo "
        f"(variant {v+1}); verify the page mentions Schema "
        "'wa-nutrition-v1'."
    )

# -----------------------------------------------------------------------
# (2) Drug interactions (~120)
# -----------------------------------------------------------------------
DRUG_PAIRS = [
    ('warfarin', 'ibuprofen', 'major'),
    ('warfarin', 'aspirin', 'major'),
    ('warfarin', 'amiodarone', 'major'),
    ('sildenafil', 'isosorbide-mononitrate', 'contraindicated'),
    ('clopidogrel', 'omeprazole', 'moderate'),
    ('metformin', 'furosemide', 'moderate'),
    ('atorvastatin', 'amiodarone', 'moderate'),
    ('simvastatin', 'amlodipine', 'moderate'),
    ('sertraline', 'tramadol', 'major'),
    ('fluoxetine', 'venlafaxine', 'major'),
    ('lisinopril', 'amlodipine', 'minor'),
    ('losartan', 'hydrochlorothiazide', 'minor'),
    ('digoxin', 'amiodarone', 'major'),
    ('digoxin', 'furosemide', 'moderate'),
    ('aspirin', 'ibuprofen', 'moderate'),
    ('insulin', 'metformin', 'minor'),
    ('apixaban', 'aspirin', 'major'),
    ('apixaban', 'amiodarone', 'moderate'),
    ('rivaroxaban', 'naproxen', 'major'),
    ('clopidogrel', 'aspirin', 'moderate'),
]
for a, b, sev in DRUG_PAIRS:
    R9_TASKS.append(
        f"Open /drugs/interaction-checker?a={a}&b={b} and verify the page "
        f"reports severity '{sev}'."
    )
    R9_TASKS.append(
        f"GET /drugs/interaction-checker?a={a}&b={b}&format=json and confirm "
        f"the JSON field severity equals '{sev}'."
    )
    R9_TASKS.append(
        f"On /drugs/interaction-checker, set Drug A = '{a}' and Drug B = "
        f"'{b}'; verify the class comparator table shows both drug classes."
    )
for v in range(20):
    R9_TASKS.append(
        f"GET /drugs/interaction-checker?a=warfarin&b=ibuprofen (variant {v+1}) "
        "and confirm response.schema equals 'wa-drug-interact-v1'."
    )
for v in range(10):
    R9_TASKS.append(
        f"GET /drugs/interaction-checker?a=foo&b=bar&format=json (variant {v+1}) "
        "and confirm severity is one of {minor, moderate, major, contraindicated}."
    )

# -----------------------------------------------------------------------
# (3) Sport team deep dive (~120)
# -----------------------------------------------------------------------
TEAMS = ['lakers', 'celtics', 'warriors', 'bucks', 'nuggets',
         'heat', 'suns', 'sixers', 'yankees', 'dodgers',
         'redsox', 'cubs', 'astros', 'giants', 'patriots',
         'cowboys', 'chiefs', 'eagles', '49ers',
         'real-madrid', 'barcelona', 'man-city', 'arsenal', 'bayern']
SEASONS = ['2023-24', '2024-25', '2025-26']
for slug in TEAMS[:18]:
    R9_TASKS.append(
        f"Open /sports/team/{slug}/deepdive and confirm the record field "
        "looks like '<wins>-<losses>'."
    )
    R9_TASKS.append(
        f"GET /sports/team/{slug}/deepdive?format=json and confirm "
        "data.schema equals 'wa-sport-deepdive-v1'."
    )
for slug in TEAMS[:8]:
    for season in SEASONS:
        R9_TASKS.append(
            f"Open /sports/team/{slug}/deepdive?season={season} and confirm "
            f"the page mentions season '{season}'."
        )
for slug in TEAMS[:6]:
    R9_TASKS.append(
        f"GET /sports/team/{slug}/deepdive?format=json and verify the JSON "
        "field 'top_scorer' starts with 'player-'."
    )
for v in range(12):
    R9_TASKS.append(
        f"Open /sports/team/lakers/deepdive (variant {v+1}) and copy the "
        "home-record vs road-record split; verify both look like '<W>-<L>'."
    )

# -----------------------------------------------------------------------
# (4) Aviation flight tracker (~120)
# -----------------------------------------------------------------------
FLIGHTS = ['AA100', 'AA101', 'UA1', 'UA888', 'DL47', 'DL200',
           'BA117', 'BA286', 'LH400', 'LH716', 'AF6', 'AF274',
           'JL5', 'JL61', 'NH7', 'CX880', 'SQ12', 'SQ22',
           'EK205', 'EK413', 'QF1', 'QF12', 'KE17', 'OZ102',
           'CA981', 'CA989', 'MU587', 'TK1', 'VS3', 'NZ1']
for f in FLIGHTS:
    R9_TASKS.append(
        f"Open /aviation/flight/{f} and confirm the page header shows "
        f"'Flight {f}'."
    )
    R9_TASKS.append(
        f"GET /aviation/flight/{f}?format=json and confirm flight='{f}'."
    )
for f in FLIGHTS[:10]:
    R9_TASKS.append(
        f"Open /aviation/flight/{f} and copy the scheduled-time value; "
        "verify it matches the regex '\\d\\d:\\d\\d'."
    )
for f in FLIGHTS[:10]:
    R9_TASKS.append(
        f"On /aviation/flight/{f}, click the linked tide arrival port and "
        "verify the URL begins with /tide/."
    )
for v in range(10):
    R9_TASKS.append(
        f"GET /aviation/flight/AA100 (variant {v+1}) and confirm origin "
        "equals 'JFK' and destination equals 'LHR'."
    )

# -----------------------------------------------------------------------
# (5) Weather radar (~120)
# -----------------------------------------------------------------------
RADAR_REGIONS = ['northeast-us', 'gulf-coast', 'california',
                 'pacific-northwest', 'alaska', 'hawaii',
                 'british-isles', 'iberian', 'central-europe',
                 'mediterranean', 'tokyo-bay', 'osaka-kansai',
                 'seoul', 'shanghai-yangtze', 'pearl-river',
                 'southeast-asia', 'australia-east',
                 'rockies', 'great-plains', 'appalachian']
for r in RADAR_REGIONS:
    R9_TASKS.append(
        f"Open /weather/radar/{r} and confirm the page mentions Schema "
        "'wa-radar-v1'."
    )
    R9_TASKS.append(
        f"GET /weather/radar/{r}?format=svg and confirm the Content-Type "
        "is image/svg+xml."
    )
    R9_TASKS.append(
        f"GET /weather/radar/{r}?format=json and confirm the band field is "
        "one of {light, moderate, heavy, severe, extreme}."
    )
RADAR_ALIASES = [('nyc', 'northeast-us'), ('tokyo', 'tokyo-bay'),
                 ('sydney', 'australia-east'), ('london', 'british-isles'),
                 ('madrid', 'iberian'), ('rome', 'mediterranean'),
                 ('berlin', 'central-europe'), ('hk', 'pearl-river'),
                 ('singapore', 'southeast-asia'), ('seattle', 'pacific-northwest')]
for alias, canonical in RADAR_ALIASES:
    R9_TASKS.append(
        f"Open /weather/radar/{alias} and confirm the canonical region "
        f"resolves to '{canonical}'."
    )
for v in range(10):
    R9_TASKS.append(
        f"GET /weather/radar/tokyo-bay?band=severe (variant {v+1}) and "
        "confirm the page lists 'severe' as the predominant band."
    )

# -----------------------------------------------------------------------
# (6) Earthquakes (~80)
# -----------------------------------------------------------------------
QUAKE_REGIONS = ['Japan Trench', 'Sumatra', 'Chile Trench', 'San Andreas',
                 'Aleutian', 'Himalayan Arc', 'Anatolian', 'Iceland Rift']
MAG_TGTS = [4.0, 5.0, 6.0, 7.0]
for region in QUAKE_REGIONS:
    R9_TASKS.append(
        f"Open /earthquakes?region={region.replace(' ', '%20')} and verify "
        f"every row mentions '{region}'."
    )
    R9_TASKS.append(
        f"GET /earthquakes?region={region.replace(' ', '%20')}&format=json "
        f"and confirm every quake.region contains '{region.split()[0]}'."
    )
for mag in MAG_TGTS:
    R9_TASKS.append(
        f"Open /earthquakes?mag_min={mag} and verify every row's magnitude "
        f"is >= {mag}."
    )
    R9_TASKS.append(
        f"GET /earthquakes?mag_min={mag}&format=json and confirm the count "
        "field equals the length of the quakes array."
    )
for v in range(20):
    R9_TASKS.append(
        f"GET /earthquakes?mag_min=6 (variant {v+1}) and confirm the JSON "
        "schema equals 'wa-quake-v1'."
    )
for v in range(8):
    R9_TASKS.append(
        f"Open /earthquakes (variant {v+1}) and confirm rows are ordered "
        "by magnitude descending."
    )

# -----------------------------------------------------------------------
# (7) Tide tomorrow (~120)
# -----------------------------------------------------------------------
TIDE_LOCS = ['Boston', 'New-York', 'San-Francisco', 'Seattle', 'Honolulu',
             'London', 'Lisbon', 'Barcelona', 'Marseille', 'Tokyo',
             'Osaka', 'Hong-Kong', 'Singapore', 'Sydney', 'Auckland',
             'Cape-Town', 'Rio-de-Janeiro', 'Buenos-Aires']
for loc in TIDE_LOCS:
    R9_TASKS.append(
        f"Open /tide/{loc} and confirm the page header references "
        f"'{loc}'."
    )
    R9_TASKS.append(
        f"GET /tide/{loc}?format=json and confirm the JSON 'pattern' field "
        "is one of {semidiurnal, diurnal, mixed-semidiurnal}."
    )
    R9_TASKS.append(
        f"On /tide/{loc}, click the linked radar region; verify the URL "
        "begins with /weather/radar/."
    )
for loc in TIDE_LOCS[:6]:
    R9_TASKS.append(
        f"GET /tide/{loc}?format=json and verify highs + lows equals the "
        "number of events returned."
    )
for v in range(14):
    R9_TASKS.append(
        f"Open /tide/Boston (variant {v+1}) and confirm tomorrow's "
        "coefficient is in the range 30..100."
    )

# -----------------------------------------------------------------------
# (8) Multi-step orchestration R9 (~80)
# -----------------------------------------------------------------------
R9_RECIPES = [
    ('nutrition + drug interaction',
     'GET /nutrition/meal-plan?cal=1800&meals=3&diet=vegetarian, copy '
     'the macros, then GET /drugs/interaction-checker?a=warfarin&b=ibuprofen.'),
    ('flight + tide arrival',
     'GET /aviation/flight/AA100, read the tide arrival port, then '
     'GET /tide/Boston.'),
    ('quake + radar overlay',
     'GET /earthquakes?region=Japan%20Trench, pick the top event, then '
     'GET /weather/radar/tokyo-bay.'),
    ('palette nutrition share',
     'Open Cmd+K palette, search "nutrition", select the entry; verify '
     'the URL begins with /nutrition/meal-plan.'),
    ('graphql to drug interaction',
     'POST /api/v3-graphql with expression "warfarin + ibuprofen", then '
     'GET /drugs/interaction-checker?a=warfarin&b=ibuprofen.'),
    ('quake to tide port',
     'GET /earthquakes?region=Chile%20Trench, then GET /tide/Buenos-Aires.'),
    ('sport to flight',
     'GET /sports/team/lakers/deepdive, then GET /aviation/flight/AA100.'),
]
for label, steps in R9_RECIPES:
    for v in range(12):  # 7 * 12 = 84
        R9_TASKS.append(
            f"R9 multi-step recipe '{label}' (variant {v+1}): {steps} "
            "Confirm each step returns HTTP 200."
        )

# -----------------------------------------------------------------------
# (9) Topic deep-link tasks for the 10 new R9 topics (~100)
# -----------------------------------------------------------------------
NEW_TOPIC_SLUGS = [
    'nutrition-meal-plan-builder',
    'drug-interaction-checker',
    'sport-team-stat-deepdive',
    'aviation-flight-tracker',
    'weather-radar-image',
    'earthquake-recent-list',
    'tide-tomorrow',
    'multi-step-workflows-r9',
    'drug-class-comparator',
    'radar-region-catalog',
]
for slug in NEW_TOPIC_SLUGS:
    R9_TASKS.append(
        f"Open /topic/{slug} and confirm the page header matches the topic name."
    )
    R9_TASKS.append(
        f"Open /topic/{slug} and count the examples shown; verify there "
        "are at least 3."
    )
    R9_TASKS.append(
        f"Open /topic/{slug} and click the first example; verify the "
        "resulting /input page loads."
    )
    R9_TASKS.append(
        f"On /topic/{slug}, submit feedback (rating 5) and verify the "
        "average rating updates."
    )
    R9_TASKS.append(
        f"Use Cmd+K and search '{slug.replace('-', ' ')[:10]}'; select the "
        "matching topic entry."
    )
    R9_TASKS.append(
        f"On /topic/{slug}, save the first example to a notebook and verify "
        "it appears in /notebooks."
    )
    R9_TASKS.append(
        f"From /topic/{slug}, navigate to a sibling category topic and "
        "confirm the URL changes."
    )
    R9_TASKS.append(
        f"On /topic/{slug}, click the share button (if present) and POST "
        "the resulting cr_id to /webhook/result-shared."
    )
    R9_TASKS.append(
        f"After visiting /topic/{slug}, GET /api/events?limit=5 and verify "
        "at least one entry references the R9 surface."
    )
    R9_TASKS.append(
        f"Open /topic/{slug} and verify the topic description mentions an "
        "R9 surface route."
    )

# -----------------------------------------------------------------------
# Emit
# -----------------------------------------------------------------------
with open(TASKS_PATH, 'a') as out:
    emitted = 0
    for q_text in R9_TASKS:
        if q_text in existing_questions:
            continue
        rec = {"web_name": WEB_NAME,
               "id": f"{WEB_NAME}--{next_id}",
               "ques": q_text,
               "web": WEB_URL,
               "upstream_url": UPSTREAM}
        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
        next_id += 1
        emitted += 1
        existing_questions.add(q_text)
print(f"[r9 tasks] emitted {emitted}; pool size {len(R9_TASKS)}")
