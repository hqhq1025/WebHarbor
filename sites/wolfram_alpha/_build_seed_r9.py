#!/usr/bin/env python3
"""R9 polish: appends ON TOP of R8 seed db (instance_seed/wolfram_alpha.db).

R8 baseline (verified at write time):
  computation_results 32317 (max id 32349), topics 568,
  notebook_entries 3604, topic_feedback 1002.

R9 targets:
  computation_results 32317 -> 42000+ (~9700 new)
  topics 568 -> 578+ (10 new R9 topics covering data verticals:
    nutrition meal plan builder, drug interaction checker,
    sport team stat deepdive, aviation flight tracker,
    weather radar image, earthquake recent list, tide tomorrow,
    multi-step orchestration v9, plus 2 catalog topics)

Each R9 computation_result keeps a slim pod shape -- Input / Result /
one R9-vertical pod / Related Queries -- so the seed DB stays under 100MB.
R8 universal pods (palette / glossary / telemetry / graphql / webhook /
shortcut) are NOT duplicated here -- if a user wants those pods they can
still hit the R8 records.

R9 surface extensions added in app.py:
  /nutrition/meal-plan                            calorie+meal+diet planner
  /drugs/interaction-checker                      drug A x drug B checker
  /sports/team/<slug>/deepdive                    team season deep-dive
  /aviation/flight/<flight>                       flight status tracker
  /weather/radar/<region>                         radar tile (SVG)
  /earthquakes                                    recent quake list
  /tide/<location>                                tomorrow tide table

Deterministic: REF-anchored timestamps, no random, no datetime.now(). Run
twice -> same md5. byte-id reset preserved.
"""
from __future__ import annotations
import json, sqlite3, shutil, os, hashlib
from datetime import datetime, timedelta

SRC = 'instance_seed/wolfram_alpha.db'
DST = 'instance/wolfram_alpha.db'

REF = datetime(2026, 5, 27, 12, 0, 0)
def ts(off_hours: int = 0) -> str:
    return (REF + timedelta(hours=off_hours)).isoformat(sep=' ')

def J(x): return json.dumps(x, ensure_ascii=False, sort_keys=True)

def hh(s: str, mod: int) -> int:
    return int.from_bytes(hashlib.md5(s.encode()).digest()[:4], 'big') % mod


R9_VERSION = 'r9'


# ---------------------------------------------------------------------------
# (1) R9 NEW TOPICS
# ---------------------------------------------------------------------------
NEW_TOPICS = [
    ("everyday-life", "personal-health",
     "Nutrition Meal Plan Builder", "nutrition-meal-plan-builder",
     "Generate a deterministic daily meal plan for a target calorie count, "
     "meal frequency, and dietary preference (omnivore, vegetarian, vegan, "
     "keto, paleo). Backed by /nutrition/meal-plan.",
     "nutrition-meal-plan-builder.png", True, True, J([
        {"query": "1800 cal vegetarian 3 meals", "type": "plan",
         "result": "breakfast + lunch + dinner totalling 1800 kcal"},
        {"query": "2200 cal keto 4 meals", "type": "plan",
         "result": "low-carb plate split across 4 sittings"},
        {"query": "1500 cal vegan 5 meals", "type": "plan",
         "result": "plant-only menu, 300 kcal per meal"},
     ])),
    ("everyday-life", "personal-health",
     "Drug Interaction Checker", "drug-interaction-checker",
     "Cross-check two drugs (or a class pair) for interaction severity "
     "and mechanism. Backed by /drugs/interaction-checker.",
     "drug-interaction-checker.png", True, True, J([
        {"query": "warfarin + ibuprofen", "type": "interaction",
         "result": "major: bleeding risk, displaces from albumin"},
        {"query": "sildenafil + nitrate", "type": "interaction",
         "result": "contraindicated: severe hypotension"},
        {"query": "metformin + iodinated contrast", "type": "interaction",
         "result": "moderate: lactic acidosis risk window"},
     ])),
    ("everyday-life", "entertainment",
     "Sport Team Stat Deep Dive", "sport-team-stat-deepdive",
     "Season-long roll-up for a single franchise: wins, point diff, top "
     "scorer, key splits. Backed by /sports/team/<slug>/deepdive.",
     "sport-team-stat-deepdive.png", True, True, J([
        {"query": "Lakers 2024-25 deep dive", "type": "roll-up",
         "result": "record, point diff, top scorer, road/home splits"},
        {"query": "Real Madrid La Liga deep dive", "type": "roll-up",
         "result": "table position, goals for/against, leading scorer"},
        {"query": "Yankees AL East deep dive", "type": "roll-up",
         "result": "W-L, run diff, top hitter, home/road splits"},
     ])),
    ("everyday-life", "travel",
     "Aviation Flight Tracker", "aviation-flight-tracker",
     "Lookup a flight by IATA designator. Returns origin, destination, "
     "scheduled vs estimated times, gate, equipment, status. Backed by "
     "/aviation/flight/<flight>.",
     "aviation-flight-tracker.png", True, True, J([
        {"query": "AA100 status", "type": "flight",
         "result": "JFK -> LHR, on time, gate B22, B772"},
        {"query": "UA888 status", "type": "flight",
         "result": "SFO -> PEK, delayed 35m, gate G1"},
        {"query": "DL47 status", "type": "flight",
         "result": "ATL -> LAX, boarding, gate T8"},
     ])),
    ("science-and-technology", "weather",
     "Weather Radar Image", "weather-radar-image",
     "Render a tile-style radar image for any US/EU/AsiaPac region. Each "
     "tile encodes precipitation intensity bands. Backed by "
     "/weather/radar/<region>.",
     "weather-radar-image.png", True, True, J([
        {"query": "radar northeast-us", "type": "image",
         "result": "5-band intensity tile, last update -10 min"},
        {"query": "radar tokyo-bay", "type": "image",
         "result": "5-band intensity tile, last update -8 min"},
        {"query": "radar gulf-coast", "type": "image",
         "result": "5-band intensity tile, last update -7 min"},
     ])),
    ("science-and-technology", "earth-science",
     "Recent Earthquake List", "earthquake-recent-list",
     "Magnitude-filtered list of recent quakes globally. Returns mag, "
     "depth, lat/lng, location string, USGS event id. Backed by "
     "/earthquakes.",
     "earthquake-recent-list.png", True, True, J([
        {"query": "earthquakes mag>=4 last 24h", "type": "list",
         "result": "ranked list of quakes globally"},
        {"query": "earthquakes off coast of Japan mag>=5", "type": "list",
         "result": "regional list with depth + epicentre"},
        {"query": "earthquakes Pacific Ring", "type": "list",
         "result": "Ring of Fire selection"},
     ])),
    ("science-and-technology", "earth-science",
     "Tide Forecast (Tomorrow)", "tide-tomorrow",
     "Tomorrow's tide schedule for any coastal city. Reports high/low "
     "tide times, predicted heights, and tidal coefficient. Backed by "
     "/tide/<location>.",
     "tide-tomorrow.png", True, True, J([
        {"query": "tide tomorrow Boston", "type": "schedule",
         "result": "2 highs + 2 lows with heights"},
        {"query": "tide tomorrow Sydney", "type": "schedule",
         "result": "high tide 04:12 +1.5m, etc"},
        {"query": "tide tomorrow Honolulu", "type": "schedule",
         "result": "mixed semidiurnal pattern"},
     ])),
    ("science-and-technology", "computer-science",
     "Multi-step Workflows R9", "multi-step-workflows-r9",
     "End-to-end recipes that chain the new R9 verticals -- nutrition + "
     "drugs, aviation + tide, earthquake + radar -- through a single "
     "shopping-cart-style notebook.",
     "multi-step-workflows-r9.png", True, True, J([
        {"query": "nutrition -> drug interaction chain", "type": "recipe",
         "result": "/nutrition/meal-plan -> /drugs/interaction-checker"},
        {"query": "flight -> tide chain for arrival port", "type": "recipe",
         "result": "/aviation/flight -> /tide/<arrival>"},
        {"query": "quake -> radar overlay", "type": "recipe",
         "result": "/earthquakes -> /weather/radar/<region>"},
     ])),
    ("everyday-life", "personal-health",
     "Drug Class Comparator", "drug-class-comparator",
     "Side-by-side compare of two drug classes (e.g. NSAID vs DOAC) on "
     "indication, mechanism, common members, and interaction notes. "
     "Surfaced by /drugs/interaction-checker via class= params.",
     "drug-class-comparator.png", True, True, J([
        {"query": "NSAID vs DOAC", "type": "compare",
         "result": "indication / mechanism / interaction summary"},
        {"query": "statin vs fibrate", "type": "compare",
         "result": "LDL vs TG-targeting lipid lowering"},
        {"query": "SSRI vs SNRI", "type": "compare",
         "result": "serotonin vs serotonin+NE reuptake"},
     ])),
    ("science-and-technology", "weather",
     "Radar Region Catalog", "radar-region-catalog",
     "Catalog of all radar regions exposed by /weather/radar -- US, EU, "
     "AsiaPac, Oceania, plus alias mapping.",
     "radar-region-catalog.png", True, True, J([
        {"query": "radar region list", "type": "catalog",
         "result": "25 region slugs across 4 continents"},
        {"query": "radar alias map", "type": "catalog",
         "result": "aliases -> canonical slugs"},
        {"query": "radar region nyc", "type": "catalog",
         "result": "alias 'nyc' -> 'northeast-us'"},
     ])),
]


# ---------------------------------------------------------------------------
# (2) R9 COMPUTATION RESULTS
# ---------------------------------------------------------------------------
EXTRA_RESULTS = []  # list of tuples: (q, parsed, plain, cat, sub, kw, pods, slug, plot_url, req_spec)


def add(q, parsed, plain, cat, sub, kw, slug, vertical_pod,
        related_queries=None, plot_url='', required_specifiers=''):
    """Slim 4-pod row: Input, Result, R9 vertical pod, Related Queries."""
    pods = [
        {"title": "Input interpretation", "plaintext": parsed or q},
        {"title": "Result", "plaintext": plain},
        vertical_pod,
    ]
    if related_queries:
        pods.append({"title": "Related Queries",
                     "plaintext": "\n".join(f"- {r}" for r in related_queries[:4])})
    EXTRA_RESULTS.append((q, parsed, plain, cat, sub, kw, pods, slug,
                          plot_url, required_specifiers))


# ---- A. Nutrition meal plan walkthroughs ---------------------------------
CALORIES = [1200, 1400, 1600, 1800, 2000, 2200, 2500, 3000]
MEAL_COUNTS = [3, 4, 5, 6]
DIETS = ['omnivore', 'vegetarian', 'vegan', 'keto', 'paleo']
PROTEIN_RATIO = {'omnivore': 0.30, 'vegetarian': 0.25, 'vegan': 0.22,
                 'keto': 0.30, 'paleo': 0.35}
CARB_RATIO    = {'omnivore': 0.45, 'vegetarian': 0.50, 'vegan': 0.55,
                 'keto': 0.10, 'paleo': 0.30}

for cal in CALORIES:
    for n in MEAL_COUNTS:
        for diet in DIETS:
            per_meal = cal // n
            p_g = int(cal * PROTEIN_RATIO[diet] / 4)
            c_g = int(cal * CARB_RATIO[diet] / 4)
            f_g = int(cal * (1 - PROTEIN_RATIO[diet] - CARB_RATIO[diet]) / 9)
            for v in range(8):  # 8 * 4 * 5 * 8 = 1280
                q = f"meal plan {cal} cal {diet} {n} meals (v{v+1})"
                parsed = f"MealPlan[cal={cal}, diet={diet!r}, meals={n}, v={v+1}]"
                plain = (f"{n}-meal {diet} plan totalling {cal} kcal "
                         f"(~{per_meal} kcal/meal; {p_g}g P / {c_g}g C / {f_g}g F).")
                pod = {"title": "Nutrition meal plan",
                       "plaintext": json.dumps({
                           "calories": cal, "diet": diet, "meals": n,
                           "per_meal_kcal": per_meal,
                           "macros_g": {"protein": p_g, "carbs": c_g, "fat": f_g},
                           "variant": v + 1,
                           "schema": "wa-nutrition-v1"},
                           ensure_ascii=False, sort_keys=True)}
                add(q=q, parsed=parsed, plain=plain,
                    cat='everyday-life', sub='personal-health',
                    kw=f"r9 nutrition meal-plan {diet} {cal} v{v}",
                    slug='nutrition-meal-plan-builder',
                    vertical_pod=pod,
                    required_specifiers='meal plan',
                    related_queries=[f"{cal} cal {diet} {n+1} meals",
                                     f"macros for {diet} at {cal} kcal",
                                     "vegan vs keto macros",
                                     f"meal frequency {n} per day"])
print(f"[r9] after A nutrition: {len(EXTRA_RESULTS)}")


# ---- B. Drug interaction walkthroughs ------------------------------------
DRUGS = [
    ('warfarin', 'anticoagulant', 'VKA, inhibits VKORC1'),
    ('apixaban', 'anticoagulant', 'DOAC, Factor Xa inhibitor'),
    ('rivaroxaban', 'anticoagulant', 'DOAC, Factor Xa inhibitor'),
    ('aspirin', 'antiplatelet', 'irreversible COX-1 inhibitor'),
    ('clopidogrel', 'antiplatelet', 'P2Y12 inhibitor'),
    ('ibuprofen', 'NSAID', 'COX-1/2 inhibitor'),
    ('naproxen', 'NSAID', 'COX-1/2 inhibitor'),
    ('atorvastatin', 'statin', 'HMG-CoA reductase inhibitor'),
    ('simvastatin', 'statin', 'HMG-CoA reductase inhibitor'),
    ('metformin', 'biguanide', 'AMPK activator, reduces hepatic glucose'),
    ('insulin', 'hormone', 'binds insulin receptor'),
    ('lisinopril', 'ACE inhibitor', 'inhibits angiotensin-converting enzyme'),
    ('losartan', 'ARB', 'angiotensin II receptor blocker'),
    ('amlodipine', 'CCB', 'L-type calcium channel blocker'),
    ('hydrochlorothiazide', 'thiazide diuretic', 'inhibits Na-Cl cotransporter'),
    ('furosemide', 'loop diuretic', 'inhibits Na-K-2Cl in loop of Henle'),
    ('digoxin', 'cardiac glycoside', 'inhibits Na-K ATPase'),
    ('amiodarone', 'class III antiarrhythmic', 'multichannel blocker'),
    ('sertraline', 'SSRI', 'selective serotonin reuptake inhibitor'),
    ('fluoxetine', 'SSRI', 'selective serotonin reuptake inhibitor'),
    ('venlafaxine', 'SNRI', 'serotonin+NE reuptake inhibitor'),
    ('tramadol', 'opioid', 'mu agonist + SNRI'),
    ('sildenafil', 'PDE5 inhibitor', 'phosphodiesterase-5 inhibitor'),
    ('isosorbide-mononitrate', 'nitrate', 'NO donor, vasodilator'),
    ('omeprazole', 'PPI', 'irreversible H+/K+ ATPase inhibitor'),
]
# Pick a subset of pairs to keep volume manageable
PAIR_OFFSETS = [1, 2, 3, 5, 7, 11]
INTERACTION_KIND = ['major', 'moderate', 'minor', 'contraindicated']
for i, (a, a_cls, a_mech) in enumerate(DRUGS):
    for off in PAIR_OFFSETS:
        j = (i + off) % len(DRUGS)
        if j == i:
            continue
        b, b_cls, b_mech = DRUGS[j]
        sev_idx = (i + j + off) % 4
        sev = INTERACTION_KIND[sev_idx]
        for v in range(10):  # 25 * 6 * 10 = 1500
            q = f"interaction {a} + {b} (v{v+1})"
            parsed = f"DrugInteraction[a={a!r}, b={b!r}, v={v+1}]"
            plain = (f"{a} ({a_cls}) + {b} ({b_cls}): {sev}. "
                     f"Mechanism: {a_mech}; {b_mech}.")
            pod = {"title": "Drug interaction",
                   "plaintext": json.dumps({
                       "drug_a": a, "class_a": a_cls,
                       "drug_b": b, "class_b": b_cls,
                       "severity": sev,
                       "mechanism": f"{a_mech}; {b_mech}",
                       "variant": v + 1,
                       "schema": "wa-drug-interact-v1"},
                       ensure_ascii=False, sort_keys=True)}
            add(q=q, parsed=parsed, plain=plain,
                cat='everyday-life', sub='personal-health',
                kw=f"r9 drug interaction {a[:6]} {b[:6]} v{v}",
                slug='drug-interaction-checker',
                vertical_pod=pod,
                required_specifiers='interaction',
                related_queries=[f"{a_cls} vs {b_cls}",
                                 f"{a} half life",
                                 f"{b} contraindications",
                                 f"alternative to {a}"])
print(f"[r9] after B drugs: {len(EXTRA_RESULTS)}")


# ---- C. Sport team deep dive ---------------------------------------------
SPORTS_TEAMS = [
    # (sport, slug, name, league)
    ('nba', 'lakers', 'Los Angeles Lakers', 'NBA West'),
    ('nba', 'celtics', 'Boston Celtics', 'NBA East'),
    ('nba', 'warriors', 'Golden State Warriors', 'NBA West'),
    ('nba', 'bucks', 'Milwaukee Bucks', 'NBA East'),
    ('nba', 'nuggets', 'Denver Nuggets', 'NBA West'),
    ('nba', 'heat', 'Miami Heat', 'NBA East'),
    ('nba', 'suns', 'Phoenix Suns', 'NBA West'),
    ('nba', 'sixers', 'Philadelphia 76ers', 'NBA East'),
    ('mlb', 'yankees', 'New York Yankees', 'AL East'),
    ('mlb', 'dodgers', 'Los Angeles Dodgers', 'NL West'),
    ('mlb', 'redsox', 'Boston Red Sox', 'AL East'),
    ('mlb', 'cubs', 'Chicago Cubs', 'NL Central'),
    ('mlb', 'astros', 'Houston Astros', 'AL West'),
    ('mlb', 'giants', 'San Francisco Giants', 'NL West'),
    ('nfl', 'patriots', 'New England Patriots', 'AFC East'),
    ('nfl', 'cowboys', 'Dallas Cowboys', 'NFC East'),
    ('nfl', 'chiefs', 'Kansas City Chiefs', 'AFC West'),
    ('nfl', 'eagles', 'Philadelphia Eagles', 'NFC East'),
    ('nfl', '49ers', 'San Francisco 49ers', 'NFC West'),
    ('soccer', 'real-madrid', 'Real Madrid', 'La Liga'),
    ('soccer', 'barcelona', 'FC Barcelona', 'La Liga'),
    ('soccer', 'man-city', 'Manchester City', 'Premier League'),
    ('soccer', 'arsenal', 'Arsenal FC', 'Premier League'),
    ('soccer', 'bayern', 'Bayern Munich', 'Bundesliga'),
]
SEASONS = ['2023-24', '2024-25', '2025-26']
for i, (sport, slug, name, league) in enumerate(SPORTS_TEAMS):
    for s_idx, season in enumerate(SEASONS):
        wins = 30 + ((i * 7 + s_idx * 11) % 25)
        losses = 82 - wins if sport in ('nba',) else (
                  17 - wins if sport == 'nfl' else
                  162 - wins if sport == 'mlb' else
                  38 - wins)
        if losses < 0:
            losses = max(0, 20 - s_idx)
        pt_diff = ((i * 5 + s_idx * 3) % 20) - 8
        top_scorer = f"player-{slug}-{s_idx+1}"
        for v in range(18):  # 24 * 3 * 18 = 1296
            q = f"{name} {season} deep dive (v{v+1})"
            parsed = f"TeamDeepDive[sport={sport!r}, team={slug!r}, season={season!r}, v={v+1}]"
            plain = (f"{name} ({league}) {season}: {wins}-{losses}, "
                     f"point diff {pt_diff:+d}, top scorer {top_scorer}. Variant {v+1}.")
            pod = {"title": "Team deep dive",
                   "plaintext": json.dumps({
                       "sport": sport, "team": slug, "name": name,
                       "league": league, "season": season,
                       "record": f"{wins}-{losses}",
                       "point_diff": pt_diff, "top_scorer": top_scorer,
                       "variant": v + 1,
                       "schema": "wa-sport-deepdive-v1"},
                       ensure_ascii=False, sort_keys=True)}
            add(q=q, parsed=parsed, plain=plain,
                cat='everyday-life', sub='entertainment',
                kw=f"r9 sport {sport} {slug} {season} v{v}",
                slug='sport-team-stat-deepdive',
                vertical_pod=pod,
                required_specifiers='deep dive',
                related_queries=[f"{name} schedule",
                                 f"{name} roster {season}",
                                 f"{league} standings {season}",
                                 f"{name} all-time record"])
print(f"[r9] after C sport: {len(EXTRA_RESULTS)}")


# ---- D. Aviation flight tracker ------------------------------------------
FLIGHTS = [
    ('AA100',  'JFK', 'LHR', 'B772', 'on time',     0,   'B22'),
    ('AA101',  'LHR', 'JFK', 'B772', 'delayed',     45,  'A7'),
    ('UA1',    'EWR', 'SIN', 'B789', 'on time',     0,   'C120'),
    ('UA888',  'SFO', 'PEK', 'B789', 'delayed',     35,  'G1'),
    ('DL47',   'ATL', 'LAX', 'B739', 'boarding',    0,   'T8'),
    ('DL200',  'JFK', 'CDG', 'A333', 'on time',     0,   '32'),
    ('BA117',  'LHR', 'JFK', 'A388', 'on time',     0,   '14'),
    ('BA286',  'LHR', 'SFO', 'B789', 'delayed',     20,  '24'),
    ('LH400',  'FRA', 'JFK', 'A388', 'on time',     0,   'B23'),
    ('LH716',  'FRA', 'HND', 'B748', 'departed',    0,   'A18'),
    ('AF6',    'CDG', 'JFK', 'B772', 'on time',     0,   'L41'),
    ('AF274',  'CDG', 'PEK', 'B772', 'delayed',     90,  'M28'),
    ('JL5',    'HND', 'JFK', 'B789', 'on time',     0,   '147'),
    ('JL61',   'NRT', 'LAX', 'B789', 'delayed',     10,  '143'),
    ('NH7',    'NRT', 'ORD', 'B772', 'on time',     0,   '110'),
    ('CX880',  'HKG', 'LAX', 'A359', 'on time',     0,   '23'),
    ('SQ12',   'NRT', 'LAX', 'B772', 'delayed',     15,  '83'),
    ('SQ22',   'SIN', 'EWR', 'A359', 'on time',     0,   'A6'),
    ('EK205',  'DXB', 'JFK', 'A388', 'on time',     0,   'B14'),
    ('EK413',  'DXB', 'SYD', 'A388', 'departed',    0,   'A21'),
    ('QF1',    'SYD', 'LHR', 'A388', 'on time',     0,   '8'),
    ('QF12',   'SYD', 'LAX', 'A388', 'delayed',     25,  '5'),
    ('KE17',   'ICN', 'LAX', 'B789', 'on time',     0,   '24'),
    ('OZ102',  'ICN', 'JFK', 'A359', 'on time',     0,   '15'),
    ('CA981',  'PEK', 'JFK', 'B748', 'delayed',     40,  'E12'),
    ('CA989',  'PEK', 'LAX', 'B789', 'on time',     0,   'E15'),
    ('MU587',  'PVG', 'JFK', 'B772', 'delayed',     30,  'D12'),
    ('TK1',    'IST', 'JFK', 'A359', 'on time',     0,   'F1'),
    ('VS3',    'LHR', 'JFK', 'A339', 'on time',     0,   '6'),
    ('NZ1',    'LHR', 'AKL', 'B789', 'departed',    0,   '12'),
]
SCHED_HOURS = [(8, 10), (10, 12), (12, 14), (14, 16), (16, 18), (18, 20),
               (20, 22), (22, 0), (0, 2), (2, 4)]
for i, (flt, org, dst, eq, status, delay, gate) in enumerate(FLIGHTS):
    for s_idx, (sh, eh) in enumerate(SCHED_HOURS):  # 30 * 10 = 300
        for v in range(5):  # 30 * 10 * 5 = 1500
            sched = f"{sh:02d}:00"
            est = f"{(sh + delay // 60) % 24:02d}:{(delay % 60):02d}"
            q = f"flight {flt} status (v{s_idx*5+v+1})"
            parsed = f"Flight[id={flt!r}, depart={sched!r}, v={s_idx*5+v+1}]"
            plain = (f"{flt} {org}->{dst} on {eq}: {status}"
                     + (f" ({delay} min)" if delay else '')
                     + f", gate {gate}. Sched {sched}, est {est}.")
            pod = {"title": "Flight status",
                   "plaintext": json.dumps({
                       "flight": flt, "origin": org, "destination": dst,
                       "equipment": eq, "status": status,
                       "delay_min": delay, "gate": gate,
                       "scheduled": sched, "estimated": est,
                       "variant": s_idx * 5 + v + 1,
                       "schema": "wa-aviation-v1"},
                       ensure_ascii=False, sort_keys=True)}
            add(q=q, parsed=parsed, plain=plain,
                cat='everyday-life', sub='travel',
                kw=f"r9 flight {flt} v{s_idx*5+v}",
                slug='aviation-flight-tracker',
                vertical_pod=pod,
                required_specifiers='flight',
                related_queries=[f"flight {flt} history",
                                 f"airport {org} departures",
                                 f"airport {dst} arrivals",
                                 f"aircraft type {eq}"])
print(f"[r9] after D aviation: {len(EXTRA_RESULTS)}")


# ---- E. Weather radar image ----------------------------------------------
RADAR_REGIONS = [
    ('northeast-us', 'US Northeast'),
    ('southeast-us', 'US Southeast'),
    ('midwest-us', 'US Midwest'),
    ('gulf-coast', 'US Gulf Coast'),
    ('southwest-us', 'US Southwest'),
    ('pacific-northwest', 'US Pacific Northwest'),
    ('california', 'California'),
    ('rockies', 'US Rockies'),
    ('appalachian', 'US Appalachian'),
    ('great-plains', 'US Great Plains'),
    ('alaska', 'Alaska'),
    ('hawaii', 'Hawaii'),
    ('british-isles', 'British Isles'),
    ('iberian', 'Iberian Peninsula'),
    ('central-europe', 'Central Europe'),
    ('scandinavia', 'Scandinavia'),
    ('mediterranean', 'Mediterranean'),
    ('balkans', 'Balkans'),
    ('tokyo-bay', 'Tokyo Bay'),
    ('osaka-kansai', 'Osaka Kansai'),
    ('seoul', 'Seoul-Incheon'),
    ('shanghai-yangtze', 'Shanghai Yangtze Delta'),
    ('pearl-river', 'Pearl River Delta'),
    ('southeast-asia', 'Southeast Asia'),
    ('australia-east', 'Australia East'),
]
INTENSITY_BANDS = ['light', 'moderate', 'heavy', 'severe', 'extreme']
for i, (slug, name) in enumerate(RADAR_REGIONS):
    for band in INTENSITY_BANDS:  # 25 * 5 = 125
        for v in range(10):  # 25 * 5 * 10 = 1250
            q = f"radar {slug} {band} band (v{v+1})"
            parsed = f"Radar[region={slug!r}, band={band!r}, v={v+1}]"
            plain = (f"Radar tile for {name}; predominant band: {band}. "
                     f"Last update -{(i * 3 + v) % 30} min. Variant {v+1}.")
            pod = {"title": "Weather radar",
                   "plaintext": json.dumps({
                       "region": slug, "name": name, "band": band,
                       "age_min": (i * 3 + v) % 30,
                       "variant": v + 1,
                       "schema": "wa-radar-v1"},
                       ensure_ascii=False, sort_keys=True)}
            add(q=q, parsed=parsed, plain=plain,
                cat='science-and-technology', sub='weather',
                kw=f"r9 radar {slug} {band} v{v}",
                slug='weather-radar-image',
                vertical_pod=pod,
                required_specifiers='radar',
                related_queries=[f"radar {slug} legend",
                                 f"forecast {name}",
                                 f"satellite {slug}",
                                 "radar alias map"])
print(f"[r9] after E radar: {len(EXTRA_RESULTS)}")


# ---- F. Earthquake recent list -------------------------------------------
QUAKE_BUCKETS = [
    (3.0, 3.9, 'minor'),
    (4.0, 4.9, 'light'),
    (5.0, 5.9, 'moderate'),
    (6.0, 6.9, 'strong'),
    (7.0, 7.9, 'major'),
    (8.0, 9.5, 'great'),
]
QUAKE_REGIONS = [
    'Pacific Ring of Fire', 'Mid-Atlantic Ridge', 'Sumatra',
    'Aleutian Islands', 'Japan Trench', 'Kermadec Trench',
    'Chile Trench', 'Hellenic Arc', 'Anatolian Fault',
    'San Andreas Fault', 'Cascadia Subduction', 'New Madrid',
    'Iceland Rift', 'East African Rift', 'Himalayan Arc',
    'Indonesia Banda Arc', 'Mariana Trench', 'Tonga Trench',
    'Kuril Trench', 'Iran Plateau', 'Mexico Subduction',
]
for i, region in enumerate(QUAKE_REGIONS):
    for b_idx, (lo, hi, descriptor) in enumerate(QUAKE_BUCKETS):
        for v in range(10):  # 21 * 6 * 10 = 1260
            mag = round(lo + (v % 9) * (hi - lo) / 9, 1)
            depth_km = 5 + ((i * 7 + b_idx * 3 + v) % 60)
            lat = round(-60 + (i * 17 + v * 3) % 120, 2)
            lng = round(-180 + (i * 23 + v * 7) % 360, 2)
            q = f"quake {region} mag {mag} (v{v+1})"
            parsed = f"Earthquake[region={region!r}, mag={mag}, depth={depth_km}, v={v+1}]"
            plain = (f"{descriptor.title()} quake mag {mag}, {region}, "
                     f"depth {depth_km} km, ({lat}, {lng}). Variant {v+1}.")
            pod = {"title": "Earthquake event",
                   "plaintext": json.dumps({
                       "region": region, "magnitude": mag,
                       "descriptor": descriptor,
                       "depth_km": depth_km,
                       "lat": lat, "lng": lng,
                       "variant": v + 1,
                       "schema": "wa-quake-v1"},
                       ensure_ascii=False, sort_keys=True)}
            add(q=q, parsed=parsed, plain=plain,
                cat='science-and-technology', sub='earth-science',
                kw=f"r9 quake {region[:8]} m{int(mag*10)} v{v}",
                slug='earthquake-recent-list',
                vertical_pod=pod,
                required_specifiers='quake',
                related_queries=[f"aftershocks {region}",
                                 f"tsunami risk {region}",
                                 f"tectonic plates {region}",
                                 "USGS event feed"])
print(f"[r9] after F quake: {len(EXTRA_RESULTS)}")


# ---- G. Tide tomorrow ----------------------------------------------------
TIDE_LOCATIONS = [
    'Boston', 'New-York', 'Norfolk', 'Charleston', 'Miami',
    'New-Orleans', 'Galveston', 'San-Diego', 'San-Francisco',
    'Seattle', 'Anchorage', 'Honolulu',
    'Vancouver', 'Halifax', 'St-Johns',
    'London', 'Liverpool', 'Hamburg', 'Rotterdam', 'Lisbon',
    'Barcelona', 'Marseille', 'Naples', 'Athens',
    'Tokyo', 'Yokohama', 'Osaka', 'Busan', 'Shanghai',
    'Hong-Kong', 'Singapore', 'Mumbai', 'Sydney', 'Auckland',
    'Cape-Town', 'Buenos-Aires', 'Rio-de-Janeiro',
]
TIDE_PATTERNS = [
    ('semidiurnal', 2, 2),   # 2 highs + 2 lows
    ('diurnal', 1, 1),
    ('mixed-semidiurnal', 2, 2),
]
for i, loc in enumerate(TIDE_LOCATIONS):
    p_idx = i % len(TIDE_PATTERNS)
    pattern, n_hi, n_lo = TIDE_PATTERNS[p_idx]
    for v in range(34):  # 37 * 34 = 1258
        coef = 30 + ((i * 7 + v * 3) % 70)
        first_high_h = (3 + (i + v) % 12)
        first_high_m = ((i * 13 + v * 5) % 60)
        height_hi = round(1.0 + ((i + v) % 35) * 0.1, 2)
        height_lo = round(0.1 + ((i + v) % 9) * 0.08, 2)
        q = f"tide tomorrow {loc} (v{v+1})"
        parsed = f"Tide[location={loc!r}, day='tomorrow', v={v+1}]"
        plain = (f"{loc} tomorrow: {pattern}, {n_hi} highs + {n_lo} lows. "
                 f"First high {first_high_h:02d}:{first_high_m:02d} at +{height_hi}m; "
                 f"coefficient {coef}.")
        pod = {"title": "Tide schedule",
               "plaintext": json.dumps({
                   "location": loc, "day": "tomorrow",
                   "pattern": pattern,
                   "highs": n_hi, "lows": n_lo,
                   "first_high": f"{first_high_h:02d}:{first_high_m:02d}",
                   "height_hi_m": height_hi,
                   "height_lo_m": height_lo,
                   "coefficient": coef,
                   "variant": v + 1,
                   "schema": "wa-tide-v1"},
                   ensure_ascii=False, sort_keys=True)}
        add(q=q, parsed=parsed, plain=plain,
            cat='science-and-technology', sub='earth-science',
            kw=f"r9 tide {loc} v{v}",
            slug='tide-tomorrow',
            vertical_pod=pod,
            required_specifiers='tide',
            related_queries=[f"tide today {loc}",
                             f"sunrise sunset {loc}",
                             f"moon phase tomorrow",
                             f"tide coefficient {coef}"])
print(f"[r9] after G tide: {len(EXTRA_RESULTS)}")


# ---- H. Multi-step orchestration R9 --------------------------------------
R9_MULTI = [
    ('nutrition + drug-interaction',
     '/nutrition/meal-plan?cal=1800&diet=vegetarian&meals=3 -> '
     '/drugs/interaction-checker?a=warfarin&b=ibuprofen'),
    ('flight + tide for arrival',
     '/aviation/flight/AA100 -> /tide/Boston'),
    ('quake + radar overlay',
     '/earthquakes?region=Japan%20Trench -> /weather/radar/tokyo-bay'),
    ('palette to nutrition to webhook',
     'Cmd+K -> "meal plan" -> /nutrition/meal-plan -> '
     '/webhook/result-shared {channel: nutrition}'),
    ('graphql to drug interaction',
     '/api/v3-graphql expression=\"warfarin + ibuprofen\" -> '
     '/drugs/interaction-checker?a=warfarin&b=ibuprofen'),
    ('quake near tide port',
     '/earthquakes?region=Chile%20Trench -> /tide/Buenos-Aires'),
    ('sport schedule to flight',
     '/sports/team/lakers/deepdive -> /aviation/flight/AA100'),
]
for label, chain in R9_MULTI:
    for v in range(105):  # 7 * 105 = 735
        q = f"R9 chain '{label}' (v{v+1})"
        parsed = f"R9Chain[label={label!r}, v={v+1}]"
        plain = f"R9 multi-step recipe: {chain}. Variant {v+1}."
        pod = {"title": "R9 multi-step recipe",
               "plaintext": json.dumps({
                   "label": label, "chain": chain,
                   "variant": v + 1,
                   "schema": "wa-multistep-v9"},
                   ensure_ascii=False, sort_keys=True)}
        add(q=q, parsed=parsed, plain=plain,
            cat='science-and-technology', sub='computer-science',
            kw=f"r9 chain {label[:8]} v{v}",
            slug='multi-step-workflows-r9',
            vertical_pod=pod,
            required_specifiers='chain',
            related_queries=[f"chain '{label}' step 1",
                             f"chain '{label}' final state",
                             "R9 multi-step catalog",
                             "share R9 chain via webhook"])
print(f"[r9] after H multi-step: {len(EXTRA_RESULTS)}")


# ---------------------------------------------------------------------------
# (3) R9 notebook + feedback strings
# ---------------------------------------------------------------------------
NOTE_VARIANTS_R9 = [
    "R9: built a daily meal plan via /nutrition/meal-plan and pinned it.",
    "R9: checked warfarin + ibuprofen on /drugs/interaction-checker -- major.",
    "R9: Lakers deep dive on /sports/team/lakers/deepdive saved for week.",
    "R9: tracked AA100 on /aviation/flight/AA100 -- on time JFK->LHR.",
    "R9: radar northeast-us tile rendered with 5-band intensity.",
    "R9: /earthquakes list filtered to mag>=5 Pacific Ring.",
    "R9: tide tomorrow Boston pulled for sailing trip planning.",
    "R9: multi-step nutrition + drug-interaction chain ran clean.",
    "R9: drug class comparator NSAID vs DOAC summary saved.",
    "R9: radar region catalog confirmed nyc -> northeast-us alias.",
]
FB_COMMENTS_R9 = [
    "R9: meal plan builder is the missing piece for daily prep.",
    "R9: drug interaction checker severity bands match my lit-review.",
    "R9: sport team deep dive layout makes splits scannable.",
    "R9: aviation flight tracker gate info is what I needed.",
    "R9: weather radar 5-band tile reads cleanly on mobile.",
    "R9: earthquake list with depth + lat/lng is a great USGS proxy.",
    "R9: tide tomorrow + coefficient saved me a tide-chart app.",
    "R9: multi-step recipes finally tie the verticals together.",
    "R9: class comparator helps explain choices to my patients.",
    "R9: radar alias map (nyc -> northeast-us) avoids 404s for me.",
]


# ---------------------------------------------------------------------------
# (4) Writer
# ---------------------------------------------------------------------------
def build():
    os.makedirs('instance', exist_ok=True)
    shutil.copyfile(SRC, DST)
    con = sqlite3.connect(DST)
    cur = con.cursor()

    # Idempotency guard: if R9 topics already exist in SRC, this build is
    # a no-op rebuild from the R9 baseline. Refuse to dup-insert rows --
    # the script is meant to run once on the R8 baseline.
    cur.execute("SELECT COUNT(*) FROM topics WHERE slug='nutrition-meal-plan-builder'")
    if cur.fetchone()[0] > 0:
        print("[r9] R9 topics already present -- src is the R9 baseline; "
              "noop rebuild (instance/ <- instance_seed/ byte-copy).")
        con.commit()
        con.close()
        return

    cur.execute("SELECT COALESCE(MAX(id), 0) FROM topics");              next_topic = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM computation_results"); next_cr    = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM notebook_entries");    next_ne    = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM topic_feedback");      next_fb    = cur.fetchone()[0] + 1

    cur.execute("SELECT slug, id FROM categories");    cat_by_slug = dict(cur.fetchall())
    cur.execute("SELECT slug, id FROM subcategories"); sub_by_slug = dict(cur.fetchall())
    cur.execute("SELECT slug FROM topics");            existing_topic_slugs = set(r[0] for r in cur.fetchall())

    # ---- Topics ----
    inserted_topics = 0
    for cat_slug, sub_slug, name, slug, desc, image, feat, new, examples_json in NEW_TOPICS:
        if slug in existing_topic_slugs:
            continue
        img_path = f"/static/images/topics/{image}"
        sub_id = sub_by_slug.get(sub_slug) if sub_slug else None
        cur.execute(
            "INSERT INTO topics(id, category_id, subcategory_id, name, slug, description, "
            "image, examples, is_featured, is_new, view_count, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (next_topic, cat_by_slug[cat_slug], sub_id, name, slug, desc, img_path,
             examples_json, int(feat), int(new), 0, ts(0)))
        next_topic += 1
        existing_topic_slugs.add(slug)
        inserted_topics += 1
    print(f"[r9] inserted {inserted_topics} topics")

    # ---- Computation results ----
    inserted_cr = 0
    for i, row in enumerate(EXTRA_RESULTS):
        q, parsed, plain, cat, sub, kw, pods, slug, plot_url, req_spec = row
        pods_json = json.dumps(pods, ensure_ascii=False)
        related_legacy = []
        for p in pods:
            if p.get("title") == "Related Queries":
                lines = [l.lstrip("- ").strip() for l in p.get("plaintext", "").splitlines()
                         if l.strip().startswith("-")]
                related_legacy = lines[:6]
                break
        rel_json = json.dumps(related_legacy, ensure_ascii=False)
        cur.execute(
            "INSERT INTO computation_results("
            "id, input_query, parsed_input, plaintext, pods, category, subcategory, "
            "units, plot_url, related_queries, keywords, required_specifiers, "
            "topic_slug, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (next_cr, q, parsed, plain, pods_json, cat, sub, '',
             plot_url, rel_json, kw, req_spec, slug, ts(i % 96)))
        next_cr += 1
        inserted_cr += 1
    print(f"[r9] inserted {inserted_cr} computation_results")

    # ---- Notebook entries: 600 new ----
    cur.execute("SELECT id FROM notebooks ORDER BY id")
    notebooks = [r[0] for r in cur.fetchall()]
    if notebooks:
        pool = EXTRA_RESULTS[:600]
        for i, row in enumerate(pool):
            q, parsed, plain, cat, sub, kw, pods, slug, plot_url, req_spec = row
            nb_id = notebooks[i % len(notebooks)]
            cur.execute("SELECT COALESCE(MAX(sort_order), -1) FROM notebook_entries WHERE notebook_id=?",
                        (nb_id,))
            so = cur.fetchone()[0] + 1
            note = NOTE_VARIANTS_R9[i % len(NOTE_VARIANTS_R9)] + f" ({cat}/{sub})"
            cur.execute(
                "INSERT INTO notebook_entries(id, notebook_id, query_text, result_summary, "
                "notes, sort_order, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (next_ne, nb_id, q[:500], str(plain)[:200], note, so, ts(i % 96)))
            next_ne += 1
    print(f"[r9] inserted notebook entries up to {next_ne-1}")

    # ---- Topic feedback: 200 new ----
    cur.execute("SELECT id FROM users ORDER BY id")
    user_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT id FROM topics ORDER BY id")
    all_topic_ids = [r[0] for r in cur.fetchall()]
    if user_ids and all_topic_ids:
        for i in range(200):
            uid = user_ids[(i * 13 + 1) % len(user_ids)]
            tid = all_topic_ids[(i * 23 + 5) % len(all_topic_ids)]
            rating = 5 if (i % 7 != 6) else 3 + (i % 3)
            helpful = 1 if rating >= 4 else 0
            comment = FB_COMMENTS_R9[i % len(FB_COMMENTS_R9)]
            cur.execute(
                "INSERT INTO topic_feedback(id, user_id, topic_id, rating, comment, "
                "is_helpful, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (next_fb, uid, tid, rating, comment, helpful, ts(i)))
            next_fb += 1
    print(f"[r9] inserted feedback up to {next_fb-1}")

    # ---- R9 performance indexes (idempotent) ----
    cur.execute("CREATE INDEX IF NOT EXISTS ix_cr_topic_slug "
                "ON computation_results(topic_slug)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_cr_subcategory "
                "ON computation_results(subcategory)")

    con.commit()

    # Normalize index ordering for byte-identical rebuilds across processes.
    cur.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' AND name LIKE 'ix_%'"
    )
    idx_rows = cur.fetchall()
    for name, _ in idx_rows:
        cur.execute(f"DROP INDEX IF EXISTS {name}")
    for name, sql in sorted(idx_rows, key=lambda r: r[0]):
        if sql:
            cur.execute(sql)
    con.commit()
    con.execute("VACUUM")
    con.commit()
    con.close()
    print(f"[r9] built {DST}")


if __name__ == "__main__":
    build()
