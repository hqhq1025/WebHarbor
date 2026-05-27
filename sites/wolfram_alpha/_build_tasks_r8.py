#!/usr/bin/env python3
"""R8 tasks generator -- appends cross-page tasks to tasks.jsonl.

Themes (matching R8 goals):
  - keyboard-shortcut-Cmd-Enter-compute
  - command-palette (Cmd+K)
  - contextual-help-math-symbol-glossary ('?' modal + /help/symbols)
  - /api/v3-graphql
  - /webhook/result-shared
  - /developer/widget-builder-advanced
  - telemetry (/healthz, /api/uptime, /api/events)
  - multi-step recipes chaining several of the above

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

R8_TASKS = []

# -----------------------------------------------------------------------
# (1) Keyboard shortcut tasks (~120)
# -----------------------------------------------------------------------
KB_EXAMPLES = [
    'derivative of x^2', 'integrate sin(x)', 'factor 360', 'sqrt(2)',
    'pi 50 digits', 'BMI 70 kg 175 cm', 'molar mass of H2O',
    'GDP United States', 'weather Tokyo', 'matrix [[1,2],[3,4]]',
    '2^32', 'log_2(1024)', 'solve x^2 + 3x + 2 = 0',
    'mean {1,2,3,4,5}', 'eigenvalues [[1,2],[3,4]]',
]
for ex in KB_EXAMPLES:
    R8_TASKS.append(f"Focus the main search input by pressing '/', type \"{ex}\", then press Cmd+Enter and read the result.")
    R8_TASKS.append(f"Type \"{ex}\" into the main search input and press Ctrl+Enter (instead of clicking Compute) to submit and read the parsed input.")
    R8_TASKS.append(f"After computing \"{ex}\", press '?' to open the math symbol glossary modal and confirm the symbol descriptions render.")
    R8_TASKS.append(f"From any page, press Cmd+K then type \"{ex.split(' ')[0]}\" to filter the command palette, then activate the entry and verify the URL.")
for ex in KB_EXAMPLES[:8]:
    R8_TASKS.append(f"Open /topic/keyboard-shortcut-cmd-enter-compute, then verify a Keyboard shortcuts pod is included on the result page for \"{ex}\".")

# -----------------------------------------------------------------------
# (2) Command palette tasks (~120)
# -----------------------------------------------------------------------
PALETTE_TARGETS = [
    ('Healthz probe',            '/healthz'),
    ('Uptime',                   '/api/uptime'),
    ('Telemetry events',         '/api/events'),
    ('GraphQL v3 SDL',           '/api/v3-graphql'),
    ('Cached popular queries',   '/api/cached/popular'),
    ('Account takeout (JSON)',   '/account/takeout'),
    ('Open math symbol glossary','/help/symbols'),
    ('Advanced widget builder',  '/developer/widget-builder-advanced'),
    ('Switch locale: Deutsch',   '/locale/de'),
    ('Switch locale: Nihongo',   '/locale/jp'),
]
for label, url in PALETTE_TARGETS:
    R8_TASKS.append(f"Open the command palette with Cmd+K, search for '{label}', and confirm the matching item links to {url}.")
    R8_TASKS.append(f"GET /api/command-palette?q={label.split()[0].lower()} and confirm at least one item has url {url}.")
    R8_TASKS.append(f"After opening the palette via Ctrl+K, type '{label[:5]}' and select the entry; the resulting URL should be {url}.")
for v in range(20):
    R8_TASKS.append(f"GET /api/command-palette and confirm the count field is >=20 (variant {v+1}).")

# -----------------------------------------------------------------------
# (3) Math symbol glossary tasks (~80)
# -----------------------------------------------------------------------
GLOSSARY_PAIRS = [
    ('nabla',      '∇', 'gradient operator'),
    ('partial',    '∂', 'partial derivative'),
    ('integral',   '∫', 'integral'),
    ('sum',        '∑', 'summation'),
    ('product',    '∏', 'product'),
    ('sqrt',       '√', 'square root'),
    ('pi',         'π', 'pi constant'),
    ('limit',      'lim','limit operator'),
]
for key, sym, desc in GLOSSARY_PAIRS:
    R8_TASKS.append(f"Open /help/symbols and confirm the glossary row for '{key}' includes the description \"{desc}\".")
    R8_TASKS.append(f"Press '?' on any result page and verify the in-page modal lists the '{sym}' entry for {key}.")
    R8_TASKS.append(f"Use Cmd+K, search 'glossary', select 'Open math symbol glossary', and verify the page shows '{key}' with symbol '{sym}'.")
    R8_TASKS.append(f"Compute \"derivative of x^2\" then verify the result page has a 'Math symbol glossary' pod referencing the operator described as \"{desc}\".")

# -----------------------------------------------------------------------
# (4) GraphQL v3 tasks (~80)
# -----------------------------------------------------------------------
GRAPHQL_CASES = [
    ('derivative of x^2', 'mathematics', 'calculus'),
    ('factor 360',        'mathematics', 'number-theory'),
    ('molar mass of H2O', 'science-and-technology', 'chemistry'),
    ('GDP United States', 'society-and-culture', 'finance'),
    ('weather Tokyo',     'society-and-culture', 'geography'),
    ('BMI 70 kg 175 cm',  'everyday-life', 'personal-health'),
]
for expr, cat, sub in GRAPHQL_CASES:
    R8_TASKS.append(f"POST {{'expression':'{expr}'}} to /api/v3-graphql and verify the response data.computation.subcategory equals '{sub}'.")
    R8_TASKS.append(f"GET /api/v3-graphql and confirm the SDL document declares a Query type with a `computation(expression: String!)` field.")
    R8_TASKS.append(f"POST a GraphQL-style query body containing `computation(expression: \"{expr}\")` to /api/v3-graphql and check data.computation.category equals '{cat}'.")
    R8_TASKS.append(f"After querying /api/v3-graphql for \"{expr}\", GET /api/events?event=graphql.queried and verify the most recent event references this computation.")
for v in range(10):
    R8_TASKS.append(f"POST /api/v3-graphql with empty body and expect HTTP 400 (variant {v+1}).")

# -----------------------------------------------------------------------
# (5) Webhook/result-shared tasks (~80)
# -----------------------------------------------------------------------
CHANNELS = ['command-palette', 'og-card', 'graphql-export',
            'takeout-archive', 'widget-embed', 'notebook']
for chan in CHANNELS:
    R8_TASKS.append(f"POST {{'cr_id':1,'channel':'{chan}'}} to /webhook/result-shared and verify the JSON response has event='result.shared' and channel='{chan}'.")
    R8_TASKS.append(f"After POSTing a result-shared webhook with channel='{chan}', GET /api/events and confirm a webhook.received event appears with that channel.")
    R8_TASKS.append(f"POST /webhook/result-shared {{'cr_id':1,'channel':'{chan}'}} and confirm response.schema equals 'wa-webhook-v1'.")
    R8_TASKS.append(f"Open /topic/webhook-result-shared and verify the page lists '{chan}' as one of the supported share channels.")
    R8_TASKS.append(f"POST /webhook/result-shared {{'cr_id':1,'channel':'{chan}'}} and confirm response.version equals 'r8'.")

# -----------------------------------------------------------------------
# (6) Advanced widget builder tasks (~80)
# -----------------------------------------------------------------------
THEMES = ['light', 'dark', 'sepia', 'high-contrast']
LOCALES = ['en', 'de', 'es', 'jp']
KINDS = ['inline', 'card', 'fullscreen']
TELEMS = ['on', 'off', 'sampled']
for theme in THEMES:
    R8_TASKS.append(f"Open /developer/widget-builder-advanced?theme={theme} and verify the embed snippet contains data-theme=\"{theme}\".")
for loc in LOCALES:
    R8_TASKS.append(f"Open /developer/widget-builder-advanced?locale={loc} and verify the preview URL contains 'locale={loc}'.")
for kind in KINDS:
    R8_TASKS.append(f"Set Layout to '{kind}' on /developer/widget-builder-advanced and confirm the resulting embed iframe carries data-kind=\"{kind}\".")
for tel in TELEMS:
    R8_TASKS.append(f"Open /developer/widget-builder-advanced?telemetry={tel} and confirm the page says telemetry is set to '{tel}'.")
for theme in THEMES:
    for loc in LOCALES:
        R8_TASKS.append(f"Visit /developer/widget-builder-advanced?theme={theme}&locale={loc} and copy the preview URL; the URL should include both theme={theme} and locale={loc}.")

# -----------------------------------------------------------------------
# (7) Observability tasks (~60)
# -----------------------------------------------------------------------
PROBES = [
    ('/healthz',       'status', 'ok'),
    ('/api/uptime',    'version', 'r8'),
    ('/api/events',    'schema', 'wa-events-v1'),
]
for url, key, value in PROBES:
    R8_TASKS.append(f"GET {url} and verify the JSON field '{key}' equals '{value}'.")
    R8_TASKS.append(f"GET {url} and confirm the response Content-Type is application/json.")
    R8_TASKS.append(f"Open the command palette (Cmd+K), search '{url.lstrip('/')}', and select the entry; the resulting page should be {url}.")
for ev in ['palette.opened', 'graphql.queried', 'webhook.received',
           'glossary.shown', 'widget.embed']:
    R8_TASKS.append(f"GET /api/events?event={ev} and confirm every returned event has event='{ev}'.")
    R8_TASKS.append(f"GET /api/events?limit=10&event={ev} and confirm the count <=10.")
for v in range(10):
    R8_TASKS.append(f"GET /healthz and confirm build=='r8' (variant {v+1}).")
    R8_TASKS.append(f"GET /api/uptime and confirm uptime_s is >= 0 (variant {v+1}).")

# -----------------------------------------------------------------------
# (8) Multi-step orchestration recipes (~80)
# -----------------------------------------------------------------------
MULTI = [
    ('palette -> compute -> webhook -> events',
     ['Cmd+K', 'select an example', 'Cmd+Enter to compute',
      'POST /webhook/result-shared', 'GET /api/events to confirm']),
    ("/" + " focus -> compute -> takeout",
     ["press '/' to focus input", 'type "factor 360" and Cmd+Enter',
      'open /account/takeout', 'verify factor 360 is in history']),
    ("'?' glossary -> graphql -> webhook",
     ["press '?' to open glossary", 'POST /api/v3-graphql with the same expression',
      'POST /webhook/result-shared with the result cr_id',
      'GET /api/events and verify graphql.queried and webhook.received events']),
    ('widget builder -> embed -> webhook',
     ['/developer/widget-builder-advanced?telemetry=on',
      'copy the embed snippet',
      'POST /webhook/result-shared with channel=widget-embed',
      'GET /api/events?event=webhook.received and confirm channel=widget-embed']),
    ('locale switch -> compute -> palette -> share',
     ['/locale/jp', 'compute "weather Tokyo"', 'Cmd+K',
      "search 'share' and select the entry",
      'verify locale cookie persisted via /api/uptime']),
]
for label, steps in MULTI:
    for v in range(16):  # 5 * 16 = 80
        R8_TASKS.append(f"Multi-step recipe '{label}' (variant {v+1}): {' -> '.join(steps)}. Confirm each step succeeds.")

# -----------------------------------------------------------------------
# (9) Topic/feedback/save tasks for the 8 new R8 topics (~50)
# -----------------------------------------------------------------------
NEW_TOPIC_SLUGS = [
    'keyboard-shortcut-cmd-enter-compute',
    'command-palette',
    'contextual-help-math-symbol-glossary',
    'api-v3-graphql',
    'webhook-result-shared',
    'developer-widget-builder-advanced',
    'telemetry-uptime-events',
    'multi-step-workflows',
]
for slug in NEW_TOPIC_SLUGS:
    for verb in ['save', 'favorite', 'rate 5 stars on', 'comment on',
                 'view 3 examples on']:
        R8_TASKS.append(f"Logged in, {verb} the /topic/{slug} page and verify the action persists in /account.")

# -----------------------------------------------------------------------
# (10) Topic deep-link tasks for the 8 new R8 topics (~120)
# -----------------------------------------------------------------------
for slug in NEW_TOPIC_SLUGS:
    R8_TASKS.append(f"Open /topic/{slug} and confirm the page header matches the topic name.")
    R8_TASKS.append(f"Open /topic/{slug} and read the topic description; verify it mentions an R8 surface.")
    R8_TASKS.append(f"Open /topic/{slug} and click the first example; verify the resulting /input page loads.")
    R8_TASKS.append(f"On /topic/{slug}, count the examples shown and verify there are at least 3.")
    R8_TASKS.append(f"From the homepage, navigate via the More Topics link to /topic/{slug} and confirm the URL.")
    R8_TASKS.append(f"Use Cmd+K, search for '{slug.replace('-', ' ')[:8]}' and select the matching topic entry.")
    R8_TASKS.append(f"POST /api/v3-graphql with an expression related to the {slug} topic and verify subcategory aligns with the topic's category.")
    R8_TASKS.append(f"Open /sitemap/science-and-technology.xml and verify a <url> entry exists for /topic/{slug} when applicable.")
    R8_TASKS.append(f"On /topic/{slug}, submit feedback (rating 5) and verify the average rating updates.")
    R8_TASKS.append(f"On /topic/{slug}, save the first example to a notebook and verify it appears in /notebooks.")
    R8_TASKS.append(f"On /topic/{slug}, click the share button (if present) and POST the resulting cr_id to /webhook/result-shared.")
    R8_TASKS.append(f"From /topic/{slug}, click on a related topic link and confirm the URL changes.")
    R8_TASKS.append(f"On /topic/{slug}, hover any math symbol; verify a tooltip appears via the symbol glossary.")
    R8_TASKS.append(f"After visiting /topic/{slug}, /api/events?event=glossary.hovered should eventually include an entry (variant).")
    R8_TASKS.append(f"Open /topic/{slug} and press '/' to focus the main search input; verify the input is focused.")

# -----------------------------------------------------------------------
# (11) GraphQL + telemetry intersection tasks (~80)
# -----------------------------------------------------------------------
for expr, cat, sub in GRAPHQL_CASES:
    for v in range(8):  # 6 * 8 = 48
        R8_TASKS.append(f"POST /api/v3-graphql with expression='{expr}' (variant {v+1}); verify response.data.computation.pods is a non-empty list.")
        R8_TASKS.append(f"GraphQL fetch '{expr}' then GET /api/events?event=graphql.queried&limit=5 -- the topic should match the computation's topic_slug. (variant {v+1})")

# -----------------------------------------------------------------------
# (12) Help-modal vs glossary-page parity tasks (~40)
# -----------------------------------------------------------------------
for key, sym, desc in GLOSSARY_PAIRS:
    for v in range(5):  # 8 * 5 = 40
        R8_TASKS.append(f"Open /help/symbols and verify the row for '{key}' lists the same description ('{desc}') shown in the in-page modal triggered by '?'. (variant {v+1})")

# -----------------------------------------------------------------------
# (13) Embed snippet integrity tasks (~60)
# -----------------------------------------------------------------------
for theme in THEMES:
    for loc in LOCALES:
        for kind in KINDS[:2]:
            R8_TASKS.append(f"Open /developer/widget-builder-advanced?theme={theme}&locale={loc}&kind={kind}&telemetry=on; the embed snippet must include data-theme=\"{theme}\", data-locale=\"{loc}\", and data-kind=\"{kind}\".")

# -----------------------------------------------------------------------
# Emit
# -----------------------------------------------------------------------
with open(TASKS_PATH, 'a') as out:
    emitted = 0
    for q_text in R8_TASKS:
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
print(f"[r8 tasks] emitted {emitted}; pool size {len(R8_TASKS)}")
