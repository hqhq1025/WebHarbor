"""R10 task generator. Appends 8-step compound + cross-vertical compound
tasks to tasks.jsonl. Deterministic and idempotent: re-running detects and
skips any R10 ids already present.

Builds on gen_r9_tasks.py conventions:
  - START_ID picks the next free id past R9 output.
  - Same SEED_QUERIES sweep for stability.
  - All tasks land in tasks.jsonl with the standard web_name / web /
    upstream_url envelope.
"""
import json
import os

TASKS_PATH = os.path.join(os.path.dirname(__file__), 'tasks.jsonl')

# Same canonical query list as R9 - keeps deterministic ordering across the
# whole R-series.
SEED_QUERIES = [
    'photosynthesis', 'large+language+model', 'black+hole', 'mediterranean+diet',
    'quantum+entanglement', 'climate+change+causes', 'Lebron+James+career',
    'Stephen+Curry+stats', 'Olympic+games+2026', 'Wimbledon+2024+winner',
    'super+bowl+LVIII', 'Oppenheimer+movie', 'Barbie+movie', 'Dune+Part+Two',
    'cherry+blossom+Japan', 'aurora+borealis+forecast', 'grand+canyon+hiking',
    'pyramids+of+giza', 'breaking+bad+finale', 'mount+everest+facts',
    'tour+de+France+2024', 'NBA+playoffs+2025', 'NASA+moon+landing+1969',
    'GDP+per+capita+US+2025', 'Tesla+Model+S+specs', 'Apple+M4+chip',
    'GPT-4+vs+Claude+3', 'Nobel+Prize+2024+physics',
]

# Common pivot topic slugs used when the task must drill into /topic/<slug>.
PIVOT_TOPICS = [
    'photosynthesis', 'large_language_model', 'black_hole',
    'mediterranean_diet', 'quantum_entanglement', 'climate_change_causes',
    'alan_turing', 'albert_einstein', 'abraham_lincoln', 'alpha_centauri',
]

# Verticals covered in cross-vertical compounds.
PRIMARY_VERTICALS = ['images', 'videos', 'news', 'shopping', 'books']
SECONDARY_VERTICALS = ['maps', 'finance', 'scholar', 'patents', 'recipes', 'forums']

# Refine modifiers - the "refine" step appends one of these to the original
# query to simulate the agent narrowing intent before vertical-switching.
REFINE_MODIFIERS = [
    'overview', '2025', 'wikipedia', 'history', 'meaning',
    'tutorial', 'guide', 'examples',
]

START_ID = 5357  # next free id after R9 ends at 5356


def gen_8step_compound():
    """8-step compound tasks: home → query → tabs → click → back → refine →
    vertical-switch → snapshot.

    Each task explicitly walks the agent through all 8 navigation steps so
    that a successful trace exercises the full SERP surface.
    """
    out = []
    for q in SEED_QUERIES:
        for i, slug in enumerate(PIVOT_TOPICS):
            mod = REFINE_MODIFIERS[i % len(REFINE_MODIFIERS)]
            vert = PRIMARY_VERTICALS[i % len(PRIMARY_VERTICALS)]
            out.append(
                f"Starting from / (home), submit a search for '{q}' to reach "
                f"/search?q={q}; click the People-also-ask block to reveal at "
                f"least one answer, then open the /topic/{slug} card; press "
                f"back to return to the SERP; refine the query to '{q}+{mod}'; "
                f"switch to the {vert} tab via /search?q={q}+{mod}&tbm={vert}; "
                f"finally open /search/snapshot/{slug} and report the answer "
                f"token shown."
            )
    return out


def gen_cross_vertical():
    """Cross-vertical compound tasks visiting 5 verticals (images, videos,
    news, shopping, books) for the same query and reporting per-vertical
    facts.
    """
    out = []
    # Pattern A: walk all 5 primary verticals.
    for q in SEED_QUERIES:
        out.append(
            f"Open /search?q={q}; in order, visit the images, videos, news, "
            f"shopping, and books tabs (i.e. /search?q={q}&tbm=images then "
            f"&tbm=videos then &tbm=news then &tbm=shopping then &tbm=books) "
            f"and report whether each tab page returns HTTP 200."
        )
    # Pattern B: pairwise comparisons across two verticals.
    pairs = [
        ('images', 'videos'),
        ('news', 'shopping'),
        ('books', 'scholar'),
        ('maps', 'finance'),
        ('recipes', 'forums'),
        ('patents', 'podcasts'),
    ]
    for q in SEED_QUERIES:
        for a, b in pairs:
            out.append(
                f"Open /search?q={q}; switch to /search?q={q}&tbm={a}, then "
                f"to /search?q={q}&tbm={b}, and report whether the result "
                f"count badge differs between the {a} and {b} tabs (yes/no)."
            )
    # Pattern C: vertical-homepage + corresponding vertical-search.
    hp_pairs = [
        ('/imghp', 'images'),
        ('/videohp', 'videos'),
        ('/trending', 'news'),
        ('/doodles', 'all'),
    ]
    for q in SEED_QUERIES:
        for hp, vert in hp_pairs:
            out.append(
                f"Visit the vertical homepage {hp}; then run a search for "
                f"'{q}' and switch to /search?q={q}&tbm={vert}; report "
                f"whether the {vert} vertical landing renders a SERP for the "
                f"same query."
            )
    return out


def gen_back_and_refine():
    """Back-and-refine compound tasks emphasising the back / refine
    navigation arc that R-prior task sets under-covered.
    """
    out = []
    for q in SEED_QUERIES[:14]:
        for slug in PIVOT_TOPICS[:6]:
            for mod in REFINE_MODIFIERS[:4]:
                out.append(
                    f"Open /search?q={q}; click into /topic/{slug}; press "
                    f"back to /search?q={q}; refine to '{q}+{mod}' and "
                    f"report the top organic-result domain on the refined "
                    f"SERP."
                )
    return out


def main():
    sections = [
        gen_8step_compound(),
        gen_cross_vertical(),
        gen_back_and_refine(),
    ]

    existing_ids = set()
    if os.path.exists(TASKS_PATH):
        with open(TASKS_PATH) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    existing_ids.add(d.get('id'))
                except Exception:
                    pass

    next_id = START_ID
    new_lines = []
    for sec in sections:
        for ques in sec:
            tid = f'Google Search--{next_id}'
            next_id += 1
            if tid in existing_ids:
                continue
            row = {
                'web_name': 'Google Search',
                'web': 'http://localhost:40009/',
                'upstream_url': 'https://www.google.com/',
                'id': tid,
                'ques': ques,
            }
            new_lines.append(json.dumps(row, ensure_ascii=False))

    if not new_lines:
        print('[r10-tasks] nothing to append')
        return

    with open(TASKS_PATH, 'a') as fh:
        for line in new_lines:
            fh.write(line + '\n')
    print(f'[r10-tasks] appended {len(new_lines)} tasks; '
          f'next free id now {next_id}')


if __name__ == '__main__':
    main()
