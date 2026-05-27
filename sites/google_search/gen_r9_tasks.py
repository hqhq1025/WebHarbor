"""R9 task generator. Appends tasks 4321..4XXX to tasks.jsonl covering the
seven new R9 surfaces. Deterministic and idempotent: re-running on top of
an existing tasks.jsonl will detect and skip already-present R9 ids.
"""
import json
import os

TASKS_PATH = os.path.join(os.path.dirname(__file__), 'tasks.jsonl')

# Stable seed queries (cycled, deterministic order).
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

# Pinned R9 slugs / tags for inner page lookups.
AI_OVERVIEW_SLUGS = [
    'photosynthesis', 'large_language_model', 'black_hole',
    'mediterranean_diet', 'quantum_entanglement', 'climate_change_causes',
]
LENS_TAGS = ['flower', 'clothing', 'landmark', 'plant', 'math', 'recipe']
NOTEBOOK_SLUGS = ['photosynthesis_study', 'llm_evaluation',
                  'climate_overview', 'mediterranean_diet_brief']
AR_SLUGS = ['tiger', 'shark', 'tyrannosaurus', 'octopus',
            'wolf', 'panda', 'planet_saturn', 'apollo_lander']
CONV_SLUGS = ['plan_paris_trip', 'learn_python_path', 'compare_air_purifiers']
GEN_MODES = ['off', 'compact', 'full', 'chat']

START_ID = 4321  # next free id after R8


def gen_ai_overview():
    """AI-Overview-citations tasks."""
    out = []
    for q in SEED_QUERIES:
        for slug in AI_OVERVIEW_SLUGS:
            out.append(
                f"Open /search?q={q}; navigate to /search/ai-overview?slug={slug} "
                f"and report how many citations the AI Overview card lists."
            )
    return out


def gen_generative_toggle():
    """generative-search-toggle tasks."""
    out = []
    for q in SEED_QUERIES:
        for mode in GEN_MODES:
            out.append(
                f"Open /search?q={q}; go to /search/generative-toggle and "
                f"report whether the mode `{mode}` is one of the available "
                f"generative-search modes (yes/no)."
            )
    return out


def gen_lens_photo():
    """lens-find-by-photo-AI-explanation tasks."""
    out = []
    for q in SEED_QUERIES:
        for tag in LENS_TAGS:
            out.append(
                f"Open /search?q={q}; visit /lens/find-photo-ai/{tag} and "
                f"report the action label shown for that tag."
            )
    return out


def gen_notebooklm():
    """NotebookLM-style-research tasks."""
    out = []
    for q in SEED_QUERIES:
        for slug in NOTEBOOK_SLUGS:
            out.append(
                f"Open /search?q={q}; visit /notebooklm/{slug} and report "
                f"how many sources the notebook lists."
            )
    return out


def gen_ar_search():
    """AR-on-camera-search-stub tasks."""
    out = []
    for q in SEED_QUERIES:
        for slug in AR_SLUGS:
            out.append(
                f"Open /search?q={q}; visit /ar-search/{slug} and report "
                f"the label shown for that AR scene."
            )
    return out


def gen_conversation():
    """search-as-conversation tasks."""
    out = []
    for q in SEED_QUERIES:
        for slug in CONV_SLUGS:
            out.append(
                f"Open /search?q={q}; visit /search/conversation/{slug} and "
                f"report how many turns the transcript contains."
            )
    return out


def gen_multistep():
    """Multi-step tasks chaining 2+ R9 endpoints."""
    out = []
    pairs = [
        ('/search/ai-overview?slug={ao}', '/search/ai-overview/citations/{ao}?format=json'),
        ('/notebooklm/{nb}', '/notebooklm/{nb}?format=json'),
        ('/search/conversation/{cv}', '/search/conversation/{cv}?format=json'),
        ('/lens/find-photo-ai/{lens}', '/lens/find-photo-ai'),
        ('/ar-search/{ar}', '/ar-search'),
        ('/search/generative-toggle', '/search/ai-overview'),
    ]
    for q in SEED_QUERIES:
        for i, (a_tpl, b_tpl) in enumerate(pairs):
            ao = AI_OVERVIEW_SLUGS[i % len(AI_OVERVIEW_SLUGS)]
            nb = NOTEBOOK_SLUGS[i % len(NOTEBOOK_SLUGS)]
            cv = CONV_SLUGS[i % len(CONV_SLUGS)]
            lens = LENS_TAGS[i % len(LENS_TAGS)]
            ar = AR_SLUGS[i % len(AR_SLUGS)]
            a = a_tpl.format(ao=ao, nb=nb, cv=cv, lens=lens, ar=ar)
            b = b_tpl.format(ao=ao, nb=nb, cv=cv, lens=lens, ar=ar)
            out.append(
                f"Open /search?q={q}; first visit {a}, then cross-check "
                f"the corresponding page at {b} and report whether the same "
                f"key fact (citation count / source count / turn count / "
                f"label / mode) appears on both pages (yes/no)."
            )
    return out


def main():
    sections = [
        gen_ai_overview(),
        gen_generative_toggle(),
        gen_lens_photo(),
        gen_notebooklm(),
        gen_ar_search(),
        gen_conversation(),
        gen_multistep(),
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
        print('[r9-tasks] nothing to append')
        return

    with open(TASKS_PATH, 'a') as fh:
        for line in new_lines:
            fh.write(line + '\n')
    print(f'[r9-tasks] appended {len(new_lines)} tasks; next free id now {next_id}')


if __name__ == '__main__':
    main()
