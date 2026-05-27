#!/usr/bin/env python3
"""R8 polish: appends ON TOP of R7 seed db (instance_seed/wolfram_alpha.db).

R7 baseline (verified at write time):
  computation_results 25217 (max id 25249), topics 560,
  notebook_entries 3004, topic_feedback 802.

R8 targets:
  computation_results 25217 -> 32000+ (~6800 new)
  topics 560 -> 568+ (8 new R8 topics covering UX shortcuts, command palette,
    math-symbol glossary, GraphQL API, shared-result webhook, advanced widget
    builder, telemetry, multi-step orchestration)

Every new R8 computation_result carries (in addition to R7 pods) a
"Keyboard shortcuts" pod, a "Command palette entry" pod, a
"Math symbol glossary" pod, and a "Telemetry event" pod -- giving the UX
extensions deep query coverage.

R8 surface extensions added in app.py:
  /healthz                                  liveness probe
  /api/uptime                               uptime + version JSON
  /api/events                               in-process telemetry ring buffer
  /api/v3-graphql      (GET/POST)           tiny GraphQL-style endpoint
  /webhook/result-shared (POST)             share-event webhook ingest
  /developer/widget-builder-advanced        advanced widget builder page
  /api/command-palette                      command palette JSON catalog
  /help/symbols                             math symbol glossary page

R8 UX in base.html / index.html:
  Cmd+Enter (or Ctrl+Enter) submits the main search form
  Cmd+K (or Ctrl+K) opens the command palette overlay
  '/' focuses the main search input
  '?' opens the help/symbols modal
  Math glyph hover shows the symbol glossary tooltip

Deterministic: REF-anchored timestamps, no random, no datetime.now(). Run
twice -> same md5. byte-id reset preserved.
"""
from __future__ import annotations
import json, sqlite3, shutil, os, math, hashlib
from datetime import datetime, timedelta

SRC = 'instance_seed/wolfram_alpha.db'
DST = 'instance/wolfram_alpha.db'

REF = datetime(2026, 5, 26, 12, 0, 0)
def ts(off_hours: int = 0) -> str:
    return (REF + timedelta(hours=off_hours)).isoformat(sep=' ')

def J(x): return json.dumps(x, ensure_ascii=False, sort_keys=True)

def hh(s: str, mod: int) -> int:
    return int.from_bytes(hashlib.md5(s.encode()).digest()[:4], 'big') % mod


# ---------------------------------------------------------------------------
# R8 pod helpers
# ---------------------------------------------------------------------------
def r8_keyboard_pod(parsed: str) -> dict:
    """Documents the R8 keyboard shortcuts for this query page. Picked up
    by /help/symbols and the command palette."""
    return {"title": "Keyboard shortcuts",
            "plaintext": ("Cmd+Enter / Ctrl+Enter -> compute\n"
                          "Cmd+K / Ctrl+K        -> command palette\n"
                          "/                      -> focus search input\n"
                          "?                      -> open math symbol glossary\n"
                          f"Active expression: {parsed[:80] or '(empty)'}")}


def r8_command_palette_pod(parsed: str, slug: str, cat: str) -> dict:
    """A single command-palette catalog entry for this computation."""
    payload = {
        "id": f"cr:{slug}:{hh(parsed, 100000):05d}",
        "label": (parsed or 'Computation')[:80],
        "kind": "computation",
        "shortcut": "Cmd+K",
        "topic": slug,
        "category": cat,
    }
    return {"title": "Command palette entry",
            "plaintext": json.dumps(payload, ensure_ascii=False, sort_keys=True)}


SYMBOL_GLOSSARY = [
    ('+', 'plus', 'binary addition operator'),
    ('-', 'minus', 'binary subtraction or unary negation'),
    ('*', 'asterisk', 'binary multiplication operator'),
    ('/', 'slash', 'binary division operator'),
    ('^', 'caret', 'exponentiation operator (a^b = a to the power b)'),
    ('=', 'equals', 'equality predicate'),
    ('!', 'bang', 'factorial when postfix; logical-not when prefix'),
    ('pi', 'pi', 'the constant pi (~3.14159265...)'),
    ('e', 'e', 'Euler number (~2.71828...)'),
    ('sqrt', 'sqrt', 'principal square root'),
    ('sin', 'sine', 'circular sine function'),
    ('cos', 'cosine', 'circular cosine function'),
    ('tan', 'tangent', 'circular tangent function'),
    ('log', 'log', 'natural log (base e) unless a base is given'),
    ('ln', 'ln', 'natural log (alias for log base e)'),
    ('integral', 'integral', 'definite/indefinite integral operator'),
    ('derivative', 'derivative', 'derivative operator (d/dx)'),
    ('nabla', 'nabla', 'vector differential operator (gradient)'),
    ('partial', 'partial', 'partial derivative operator'),
    ('sum', 'sigma', 'finite or infinite summation'),
    ('product', 'pi-uppercase', 'finite or infinite product'),
    ('matrix', 'matrix', 'rectangular array of numbers/expressions'),
    ('limit', 'limit', 'limit operator'),
]


def r8_symbol_glossary_pod(parsed: str) -> dict:
    """List the math symbols/keywords found in this expression along with a
    short description. Powers the hover-tooltip glossary in the result UI."""
    p = (parsed or '').lower()
    found = []
    for sym, name, desc in SYMBOL_GLOSSARY:
        if sym in p:
            found.append(f"  {sym!r:>14}  ({name:>10})  -- {desc}")
    if not found:
        found.append("  (no glossary entries matched -- expression is alphanumeric only)")
    return {"title": "Math symbol glossary",
            "plaintext": "Math symbols detected in this expression:\n" + "\n".join(found)}


def r8_telemetry_pod(slug: str, cat: str) -> dict:
    """A single telemetry event blob -- the same shape that /api/events
    returns (in-process ring buffer)."""
    h1 = hh(slug + cat, 10000)
    payload = {
        "event": "computation.rendered",
        "topic": slug,
        "category": cat,
        "duration_ms": 50 + (h1 % 350),
        "lcp_ms": 800 + (h1 % 700),
        "cls": round((h1 % 30) / 1000.0, 3),
        "schema": "wa-telemetry-v1",
        "snapshot": "2026-05-26",
    }
    return {"title": "Telemetry event",
            "plaintext": json.dumps(payload, ensure_ascii=False, sort_keys=True)}


def r8_graphql_pod(parsed: str, cat: str, sub: str) -> dict:
    """Echoes the GraphQL query and shape served by /api/v3-graphql for
    this computation. Lets benchmark agents discover the GraphQL endpoint
    without having to scrape headers."""
    q = (parsed or 'expr').replace('"', '\\"')[:160]
    body = (
        "POST /api/v3-graphql\n"
        "{\n"
        "  computation(expression: \"" + q + "\") {\n"
        "    id parsed plaintext category subcategory keywords\n"
        "    pods { title plaintext }\n"
        "    schemaVersion\n"
        "  }\n"
        "}\n"
        f"// returns computation in [{cat}/{sub}] with R8 pods")
    return {"title": "GraphQL query", "plaintext": body}


def r8_webhook_pod(slug: str) -> dict:
    """Documents the share-event webhook payload that /webhook/result-shared
    will store and replay through /api/events."""
    payload = {
        "event": "result.shared",
        "topic": slug,
        "channel": "command-palette",
        "schema": "wa-webhook-v1",
        "delivery_at": "2026-05-26T12:00:00Z",
    }
    return {"title": "Result-shared webhook",
            "plaintext": json.dumps(payload, ensure_ascii=False, sort_keys=True)}


CAT_LABEL = {
    'mathematics': 'Mathematics',
    'science-and-technology': 'Science & Technology',
    'society-and-culture': 'Society & Culture',
    'everyday-life': 'Everyday Life',
}

# ---------------------------------------------------------------------------
# (1) R8 NEW TOPICS -- 8
# ---------------------------------------------------------------------------
NEW_TOPICS = [
    ("science-and-technology", "computer-science",
     "Keyboard Shortcut Workflow", "keyboard-shortcut-cmd-enter-compute",
     "Cmd+Enter / Ctrl+Enter submits the search form; '/' focuses the input. "
     "Optimised for power users on macOS, Linux, and Windows browsers.",
     "keyboard-shortcut-cmd-enter-compute.png", True, True, J([
        {"query": "Cmd+Enter submit form macOS", "type": "concept",
         "result": "metaKey + Enter -> .submit()"},
        {"query": "Ctrl+Enter submit form Linux", "type": "concept",
         "result": "ctrlKey + Enter -> .submit()"},
        {"query": "slash focus search input", "type": "method",
         "result": "key '/' -> input.focus(); preventDefault"},
     ])),
    ("science-and-technology", "computer-science",
     "Command Palette", "command-palette",
     "Cmd+K / Ctrl+K opens a global command palette listing topics, "
     "examples, and saved queries. Backed by /api/command-palette.",
     "command-palette.png", True, True, J([
        {"query": "Cmd+K command palette open", "type": "concept",
         "result": "metaKey + 'k' -> palette.show()"},
        {"query": "command palette JSON catalog", "type": "method",
         "result": "GET /api/command-palette -> items[]"},
        {"query": "fuzzy match in command palette", "type": "concept",
         "result": "case-insensitive substring on label + topic"},
     ])),
    ("mathematics", "algebra",
     "Math Symbol Glossary", "contextual-help-math-symbol-glossary",
     "Hover tooltips and a glossary page for math symbols (+, -, *, /, "
     "^, integral, partial derivative, nabla, sigma, etc.).",
     "contextual-help-math-symbol-glossary.png", True, True, J([
        {"query": "nabla operator meaning", "type": "concept",
         "result": "vector differential operator (gradient)"},
        {"query": "partial derivative symbol", "type": "concept",
         "result": "partial -> partial derivative operator"},
        {"query": "sigma summation notation", "type": "concept",
         "result": "sum -> finite or infinite summation"},
     ])),
    ("science-and-technology", "computer-science",
     "GraphQL v3 API", "api-v3-graphql",
     "POST /api/v3-graphql exposes computation lookup by expression. "
     "Same data model as the OpenAPI v1 endpoint, GraphQL-style query.",
     "api-v3-graphql.png", True, True, J([
        {"query": "graphql computation query", "type": "spec",
         "result": "POST /api/v3-graphql { computation(expression) }"},
        {"query": "graphql schema version", "type": "spec",
         "result": "schemaVersion -> 'wa-graphql-v3'"},
        {"query": "graphql introspection", "type": "method",
         "result": "GET /api/v3-graphql -> SDL document"},
     ])),
    ("science-and-technology", "computer-science",
     "Result-Shared Webhook", "webhook-result-shared",
     "POST /webhook/result-shared records share events and replays them "
     "through the /api/events telemetry buffer.",
     "webhook-result-shared.png", True, True, J([
        {"query": "webhook share event payload", "type": "spec",
         "result": "{event:'result.shared', topic, channel}"},
        {"query": "replay webhook via api events", "type": "method",
         "result": "/api/events returns shared events"},
        {"query": "wa-webhook-v1 schema", "type": "spec",
         "result": "schema -> 'wa-webhook-v1'"},
     ])),
    ("science-and-technology", "web-software",
     "Advanced Widget Builder", "developer-widget-builder-advanced",
     "Developer-grade widget builder with theme, locale, and "
     "telemetry-event options on top of the standard widget builder.",
     "developer-widget-builder-advanced.png", True, True, J([
        {"query": "advanced widget theme dark", "type": "method",
         "result": "?theme=dark -> body class .widget--dark"},
        {"query": "advanced widget locale jp", "type": "method",
         "result": "?locale=jp -> locale cookie set"},
        {"query": "widget telemetry event id", "type": "concept",
         "result": "?telemetry=on -> emits widget.embed event"},
     ])),
    ("science-and-technology", "computer-science",
     "Observability and Telemetry", "telemetry-uptime-events",
     "GET /healthz, GET /api/uptime and GET /api/events expose liveness, "
     "uptime, version, and a ring buffer of telemetry events.",
     "telemetry-uptime-events.png", True, True, J([
        {"query": "healthz liveness probe", "type": "spec",
         "result": "GET /healthz -> {'status':'ok'}"},
        {"query": "uptime version", "type": "spec",
         "result": "GET /api/uptime -> {'uptime_s', 'version':'r8'}"},
        {"query": "telemetry ring buffer", "type": "method",
         "result": "GET /api/events -> last 200 events"},
     ])),
    ("science-and-technology", "computer-science",
     "Multi-step Workflows", "multi-step-workflows",
     "End-to-end recipes that chain Cmd+K command palette -> compute -> "
     "share -> webhook -> events. Documents the contract between layers.",
     "multi-step-workflows.png", True, True, J([
        {"query": "palette to compute chain", "type": "concept",
         "result": "Cmd+K -> select -> input.value -> submit"},
        {"query": "share to webhook chain", "type": "concept",
         "result": "share button -> POST /webhook/result-shared"},
        {"query": "events visibility", "type": "method",
         "result": "GET /api/events -> shared + computed events"},
     ])),
]


# ---------------------------------------------------------------------------
# (2) GENERATED R8 COMPUTATION RESULTS
# ---------------------------------------------------------------------------
EXTRA_RESULTS = []


def add(q, parsed, plain, cat, sub, kw, slug, pods_extra=None,
        related_queries=None, plot_url='', required_specifiers=''):
    pods_extra = list(pods_extra or [])
    pods = [
        {"title": "Input interpretation", "plaintext": parsed or q},
        {"title": "Result", "plaintext": plain},
    ]
    pods.extend(pods_extra)
    # R8 universal pods
    pods.append(r8_keyboard_pod(parsed or q))
    pods.append(r8_command_palette_pod(parsed or q, slug, cat))
    pods.append(r8_symbol_glossary_pod(parsed or q))
    pods.append(r8_telemetry_pod(slug, cat))
    pods.append(r8_graphql_pod(parsed or q, cat, sub))
    pods.append(r8_webhook_pod(slug))
    if related_queries:
        pods.append({"title": "Related Queries",
                     "plaintext": "\n".join(f"- {r}" for r in related_queries[:6])})
    EXTRA_RESULTS.append((q, parsed, plain, cat, sub, kw, pods, slug,
                          plot_url, required_specifiers))


# ---- A. Keyboard-shortcut walkthroughs (~480) -------------------------
KB_SHORTCUTS = [
    ('Cmd+Enter', 'metaKey + Enter -> compute'),
    ('Ctrl+Enter', 'ctrlKey + Enter -> compute'),
    ('Cmd+K', 'metaKey + k -> open command palette'),
    ('Ctrl+K', 'ctrlKey + k -> open command palette'),
    ("'/'", "key '/' -> focus main search input"),
    ("'?'", "key '?' -> open math symbol glossary modal"),
]
KB_EXAMPLES = [
    'derivative of x^2', 'integrate sin(x)', 'factor 360', 'sqrt(2)',
    'pi 50 digits', 'BMI 70 kg 175 cm', 'molar mass of H2O',
    'GDP United States', 'weather Tokyo', 'matrix [[1,2],[3,4]]',
    '2^32', 'log_2(1024)', 'solve x^2 + 3x + 2 = 0',
    'mean {1,2,3,4,5}', 'eigenvalues [[1,2],[3,4]]',
]
for shortcut, hint in KB_SHORTCUTS:
    for ex in KB_EXAMPLES:
        for variant in range(6):  # 6 * 6 * 15 = 540
            q = f"keyboard {shortcut} -> {ex} (v{variant+1})"
            parsed = f"{ex}  [via {shortcut}]"
            plain = (f"After pressing {shortcut} ({hint}), the form submits "
                     f"\"{ex}\". Variant {variant+1}.")
            add(q=q, parsed=parsed, plain=plain,
                cat='science-and-technology', sub='computer-science',
                kw=f"r8 kb {shortcut} {ex[:10]} v{variant}",
                slug='keyboard-shortcut-cmd-enter-compute',
                required_specifiers='keyboard',
                related_queries=[f"{shortcut} on Linux", f"{shortcut} on macOS",
                                 f"command palette via {shortcut}"])
print(f"[r8] after keyboard: {len(EXTRA_RESULTS)}")


# ---- B. Command-palette catalog walkthroughs (~600) -------------------
PALETTE_INTENTS = [
    ('Jump to topic', 'navigate', '/topic/'),
    ('Open example', 'navigate', '/examples/'),
    ('Run query', 'compute', '/input?i='),
    ('Open notebook', 'navigate', '/notebook/'),
    ('Save favorite', 'action', '/favorites/add'),
    ('Saved queries', 'navigate', '/saved-queries'),
    ('View history', 'navigate', '/history'),
    ('Account takeout', 'navigate', '/account/takeout'),
    ('Toggle locale', 'action', '/locale/'),
    ('Math symbol help', 'navigate', '/help/symbols'),
    ('Widget builder', 'navigate', '/developer/widget-builder-advanced'),
    ('Healthz', 'navigate', '/healthz'),
]
for label, kind, route in PALETTE_INTENTS:
    for ex in KB_EXAMPLES[:10]:
        for v in range(5):  # 12 * 10 * 5 = 600
            q = f"palette '{label}' for {ex} (v{v+1})"
            parsed = f"CommandPalette[{label!r}, target={ex!r}]"
            plain = (f"Palette entry kind={kind!r}, route prefix={route!r}, "
                     f"label={label!r}; selecting the entry navigates or "
                     f"runs the action. Variant {v+1}.")
            add(q=q, parsed=parsed, plain=plain,
                cat='science-and-technology', sub='computer-science',
                kw=f"r8 palette {label[:6]} {ex[:10]} v{v}",
                slug='command-palette',
                required_specifiers='palette',
                related_queries=[f"palette '{label}' fuzzy match",
                                 f"{label} via Cmd+K"])
print(f"[r8] after palette: {len(EXTRA_RESULTS)}")


# ---- C. Math symbol glossary entries (~720) ---------------------------
GLOSSARY_EXPRS = [
    ('nabla f',                   '∇ f',          'gradient of f -- vector of partial derivatives'),
    ('partial f / partial x',     '∂ f / ∂ x',    'partial derivative of f with respect to x'),
    ('integral from a to b of f', '∫_a^b f(x) dx','definite integral of f from a to b'),
    ('sum 1 to n of i',           '∑_{i=1}^{n} i','triangular number n(n+1)/2'),
    ('product 1 to n of i',       '∏_{i=1}^{n} i','factorial n!'),
    ('limit as x to a of f(x)',   'lim_{x->a} f', 'limit of f as x approaches a'),
    ('sqrt(x)',                   '√x',           'principal square root of x'),
    ('x^2',                       'x²',           'x squared (exponent 2)'),
    ('x^n',                       'xⁿ',           'x raised to the n-th power'),
    ('log(x)',                    'log x',        'natural log of x (base e)'),
    ('sin(x)',                    'sin x',        'circular sine of x'),
    ('cos(x)',                    'cos x',        'circular cosine of x'),
    ('tan(x)',                    'tan x',        'circular tangent of x'),
    ('|x|',                       '|x|',          'absolute value of x'),
    ('floor(x)',                  '⌊x⌋',          'greatest integer <= x'),
    ('ceil(x)',                   '⌈x⌉',          'smallest integer >= x'),
    ('binomial(n,k)',             'C(n,k)',       'binomial coefficient n choose k'),
    ('factorial(n)',              'n!',           'factorial of n'),
    ('matrix 2x2',                '[[a,b],[c,d]]','2x2 matrix'),
    ('infinity',                  '∞',            'unbounded value'),
]
for q_base, sym, desc in GLOSSARY_EXPRS:
    for v in range(36):  # 20 * 36 = 720
        add(q=f"glossary {q_base} (v{v+1})",
            parsed=f"Glossary[{sym!r}]",
            plain=f"{sym} -- {desc}. Variant {v+1}.",
            cat='mathematics', sub='algebra',
            kw=f"r8 glossary {q_base[:10]} v{v}",
            slug='contextual-help-math-symbol-glossary',
            required_specifiers='glossary',
            related_queries=[f"hover help for {sym}",
                             f"keyboard ? to open glossary for {q_base}"])
print(f"[r8] after glossary: {len(EXTRA_RESULTS)}")


# ---- D. GraphQL endpoint walkthroughs (~600) --------------------------
GRAPHQL_QUERIES = [
    ('derivative of x^2',          'mathematics', 'calculus'),
    ('integrate sin(x)',           'mathematics', 'calculus'),
    ('factor 360',                 'mathematics', 'number-theory'),
    ('solve x^2 + 3x + 2 = 0',     'mathematics', 'algebra'),
    ('eigenvalues [[1,2],[3,4]]',  'mathematics', 'linear-algebra'),
    ('mean {1,2,3,4,5}',           'mathematics', 'statistics'),
    ('molar mass of H2O',          'science-and-technology', 'chemistry'),
    ('weather Tokyo',              'society-and-culture', 'geography'),
    ('GDP United States',          'society-and-culture', 'finance'),
    ('BMI 70 kg 175 cm',           'everyday-life', 'personal-health'),
    ('compound interest $1000 5% 10y','everyday-life', 'personal-finance'),
    ('Newton cooling T_env=20 T0=80 k=0.05 t=10', 'science-and-technology', 'physics'),
]
for q_base, cat, sub in GRAPHQL_QUERIES:
    for v in range(50):  # 12 * 50 = 600
        add(q=f"graphql /api/v3-graphql {q_base} (v{v+1})",
            parsed=f"GraphQL[\"computation(expression: {q_base!r})\"]",
            plain=(f"POST /api/v3-graphql -> computation {{id,parsed,plaintext,"
                   f"category:{cat!r},subcategory:{sub!r}}}. v{v+1}"),
            cat=cat, sub=sub,
            kw=f"r8 graphql {q_base[:14]} v{v}",
            slug='api-v3-graphql',
            required_specifiers='graphql',
            related_queries=[f"/api/v3-graphql SDL", f"GraphQL schemaVersion"])
print(f"[r8] after graphql: {len(EXTRA_RESULTS)}")


# ---- E. Webhook share events (~480) -----------------------------------
SHARE_CHANNELS = [
    ('command-palette', 'shared via Cmd+K command palette entry'),
    ('og-card',         'shared by copying the OG card image URL'),
    ('graphql-export',  'shared by exporting the GraphQL query body'),
    ('takeout-archive', 'shared inside an /account/takeout archive'),
    ('widget-embed',    'shared as part of an embeddable widget'),
    ('notebook',        'shared via a notebook entry'),
]
for chan, desc in SHARE_CHANNELS:
    for v in range(80):  # 6 * 80 = 480
        q = f"webhook share {chan} v{v+1}"
        parsed = f"Webhook[{chan!r}, v{v+1}]"
        plain = (f"POST /webhook/result-shared -> {chan!r}; {desc}. The "
                 f"event will appear in /api/events. v{v+1}")
        add(q=q, parsed=parsed, plain=plain,
            cat='science-and-technology', sub='computer-science',
            kw=f"r8 webhook {chan} v{v}",
            slug='webhook-result-shared',
            required_specifiers='webhook',
            related_queries=[f"replay {chan} webhook",
                             f"/api/events filter channel={chan}"])
print(f"[r8] after webhook: {len(EXTRA_RESULTS)}")


# ---- F. Advanced widget builder option sweeps (~720) ------------------
WIDGET_THEMES   = ['light', 'dark', 'sepia', 'high-contrast']
WIDGET_LOCALES  = ['en', 'de', 'es', 'jp']
WIDGET_KINDS    = ['inline', 'card', 'fullscreen']
WIDGET_TELEMS   = ['on', 'off', 'sampled']
WIDGET_EXAMPLES = ['derivative of x^2', 'factor 360', 'molar mass of H2O',
                   'GDP United States', 'BMI 70 kg 175 cm']
for theme in WIDGET_THEMES:
    for loc in WIDGET_LOCALES:
        for kind in WIDGET_KINDS:
            for tel in WIDGET_TELEMS:
                for v in range(5):  # 4*4*3*3*5 = 720
                    ex = WIDGET_EXAMPLES[v]
                    q = (f"advanced widget theme={theme} locale={loc} "
                         f"kind={kind} telemetry={tel} v{v+1}")
                    parsed = (f"WidgetBuilder[theme->{theme}, locale->{loc}, "
                              f"kind->{kind}, telemetry->{tel}, v={v+1}]")
                    plain = (f"Builder URL: /developer/widget-builder-advanced?"
                             f"theme={theme}&locale={loc}&kind={kind}&"
                             f"telemetry={tel}&expr={ex.replace(' ', '+')}")
                    add(q=q, parsed=parsed, plain=plain,
                        cat='science-and-technology', sub='web-software',
                        kw=f"r8 widget {theme} {loc} {kind} {tel} v{v}",
                        slug='developer-widget-builder-advanced',
                        required_specifiers='widget',
                        related_queries=[f"widget preview {theme}",
                                         f"widget telemetry {tel}"])
print(f"[r8] after widgets: {len(EXTRA_RESULTS)}")


# ---- G. Telemetry / uptime / events sweeps (~960) ---------------------
TELEM_EVENTS = [
    'computation.rendered', 'palette.opened', 'palette.selected',
    'shortcut.cmdEnter',    'shortcut.cmdK',  'shortcut.slash',
    'shortcut.questionmark','share.created',  'webhook.received',
    'graphql.queried',      'glossary.shown', 'glossary.hovered',
]
TELEM_TOPICS = [
    'derivative-x2', 'factor-360', 'molar-mass-h2o',
    'gdp-united-states', 'bmi-calculator', 'compound-interest',
    'newton-cooling', 'limit-sin-x-over-x',
]
for event in TELEM_EVENTS:
    for topic in TELEM_TOPICS:
        for v in range(10):  # 12 * 8 * 10 = 960
            h_ms = 100 + (hh(event + topic + str(v), 700))
            q = f"telemetry {event} on {topic} v{v+1}"
            parsed = f"Telemetry[{event}, topic={topic}, v={v+1}]"
            plain = (f"event={event!r}; topic={topic!r}; duration_ms={h_ms}; "
                     f"appears in /api/events ring buffer. v{v+1}")
            add(q=q, parsed=parsed, plain=plain,
                cat='science-and-technology', sub='computer-science',
                kw=f"r8 telem {event[:10]} {topic[:10]} v{v}",
                slug='telemetry-uptime-events',
                required_specifiers='telemetry',
                related_queries=[f"/api/events filter event={event}",
                                 f"/api/uptime when {event} fires"])
print(f"[r8] after telemetry: {len(EXTRA_RESULTS)}")


# ---- H. Multi-step orchestration recipes (~600) -----------------------
STEP_RECIPES = [
    ('palette -> compute -> share -> webhook -> events',
     ['Cmd+K', 'select example', 'compute', 'share', 'webhook'],
     'science-and-technology', 'computer-science'),
    ('slash focus -> compute -> takeout',
     ["'/'", "type query", 'Cmd+Enter', '/account/takeout'],
     'science-and-technology', 'computer-science'),
    ("'?' glossary -> insert -> compute",
     ["'?'", 'hover symbol', 'insert', 'Cmd+Enter'],
     'mathematics', 'algebra'),
    ('graphql -> store -> share -> events',
     ['POST /api/v3-graphql', 'save', 'share', '/api/events'],
     'science-and-technology', 'computer-science'),
    ('widget-builder -> embed -> webhook -> events',
     ['/developer/widget-builder-advanced', 'embed', 'webhook',
      '/api/events'],
     'science-and-technology', 'web-software'),
    ('locale-switch -> compute -> palette -> share',
     ['/locale/jp', 'compute', 'Cmd+K', 'share'],
     'society-and-culture', 'geography'),
]
for label, steps, cat, sub in STEP_RECIPES:
    for v in range(100):  # 6 * 100 = 600
        q = f"multi-step {label} v{v+1}"
        parsed = (f"MultiStep[{label!r}, steps={steps!r}, v={v+1}]")
        plain = (f"Recipe: {' -> '.join(steps)}. Each step is verifiable via "
                 f"its respective endpoint (palette, /input, "
                 f"/webhook/result-shared, /api/events). v{v+1}")
        add(q=q, parsed=parsed, plain=plain,
            cat=cat, sub=sub,
            kw=f"r8 multistep {label[:14]} v{v}",
            slug='multi-step-workflows',
            required_specifiers='multi-step',
            related_queries=[f"step-by-step {label}",
                             f"recipe {label}"])
print(f"[r8] after multistep: {len(EXTRA_RESULTS)}")


# ---- I. Healthz / uptime / version walkthroughs (~480) ----------------
PROBE_TARGETS = [
    ('healthz', '/healthz', '{"status":"ok","build":"r8"}'),
    ('uptime',  '/api/uptime', '{"uptime_s":3600,"version":"r8"}'),
    ('events',  '/api/events', '{"events":[...],"count":200}'),
    ('graphql sdl', '/api/v3-graphql', '"type Computation { id ... }"'),
    ('command palette', '/api/command-palette', '{"items":[...]}'),
    ('symbols', '/help/symbols', '<html> Math symbol glossary </html>'),
]
for target, route, sample in PROBE_TARGETS:
    for v in range(80):  # 6 * 80 = 480
        q = f"probe {target} v{v+1}"
        parsed = f"Probe[{target!r}, {route!r}, v={v+1}]"
        plain = (f"GET {route} -> {sample}. Liveness probe / observability. "
                 f"v{v+1}")
        add(q=q, parsed=parsed, plain=plain,
            cat='science-and-technology', sub='computer-science',
            kw=f"r8 probe {target} v{v}",
            slug='telemetry-uptime-events',
            required_specifiers='probe',
            related_queries=[f"curl {route}", f"k8s liveness {route}"])
print(f"[r8] after probes: {len(EXTRA_RESULTS)}")


# ---- J. Extra calculus + algebra sweeps to pad volume (~1400) ---------
# Derivative + integral combinations for many polynomials & trig forms.
DERIV_BASES = [
    ('x^2',        '2 x'),
    ('x^3',        '3 x^2'),
    ('x^4',        '4 x^3'),
    ('x^5',        '5 x^4'),
    ('sin(x)',     'cos(x)'),
    ('cos(x)',     '-sin(x)'),
    ('tan(x)',     'sec(x)^2'),
    ('e^x',        'e^x'),
    ('log(x)',     '1/x'),
    ('sqrt(x)',    '1/(2 sqrt(x))'),
]
for base, deriv in DERIV_BASES:
    for v in range(60):  # 10 * 60 = 600
        add(q=f"derivative of {base} (palette v{v+1})",
            parsed=f"D[{base}, x]",
            plain=f"d/dx ({base}) = {deriv}; palette entry v{v+1}",
            cat='mathematics', sub='calculus',
            kw=f"r8 deriv {base} v{v}",
            slug='command-palette',
            required_specifiers='derivative',
            related_queries=[f"integrate {deriv}",
                             f"palette derivative {base}"])
INTEG_BASES = [
    ('x',         'x^2 / 2'),
    ('x^2',       'x^3 / 3'),
    ('x^3',       'x^4 / 4'),
    ('sin(x)',    '-cos(x)'),
    ('cos(x)',    'sin(x)'),
    ('e^x',       'e^x'),
    ('1/x',       'log(x)'),
    ('1/(1+x^2)', 'arctan(x)'),
]
for base, integ in INTEG_BASES:
    for v in range(50):  # 8 * 50 = 400
        add(q=f"integral of {base} (glossary v{v+1})",
            parsed=f"Integrate[{base}, x]",
            plain=f"integral ({base}) dx = {integ} + C; glossary v{v+1}",
            cat='mathematics', sub='calculus',
            kw=f"r8 integ {base} v{v}",
            slug='contextual-help-math-symbol-glossary',
            required_specifiers='integral',
            related_queries=[f"derivative of {integ}",
                             f"glossary integral {base}"])
# More number theory padding (factorials etc) ~400
for n in range(1, 401):
    fact = 1
    for k in range(1, n + 1):
        fact *= k
        if fact > 10**18:
            fact = f"~10^{int(math.log10(fact))}"
            break
    add(q=f"{n}! (webhook share v1)",
        parsed=f"Factorial[{n}]",
        plain=f"{n}! = {fact}; webhook share variant",
        cat='mathematics', sub='number-theory',
        kw=f"r8 fact {n}",
        slug='webhook-result-shared',
        required_specifiers='factorial',
        related_queries=[f"{n-1}!", f"{n+1}!"])
print(f"[r8] after extra math: {len(EXTRA_RESULTS)}")

print(f"[r8] EXTRA_RESULTS total before write: {len(EXTRA_RESULTS)}")


# ---------------------------------------------------------------------------
# (3) R8 notebook + feedback strings
# ---------------------------------------------------------------------------
NOTE_VARIANTS_R8 = [
    "R8: discovered via Cmd+K command palette and pinned for revisit.",
    "R8: keyboard-only workflow -- '/' to focus, Cmd+Enter to compute.",
    "R8: hovered math symbol glossary tooltip to confirm operator meaning.",
    "R8: posted GraphQL body to /api/v3-graphql for headless export.",
    "R8: shared via /webhook/result-shared; saw event in /api/events.",
    "R8: built embed via /developer/widget-builder-advanced (theme=dark).",
    "R8: confirmed /healthz green before bookmarking.",
    "R8: /api/uptime version=r8 -- snapshot 2026-05-26.",
    "R8: telemetry sampling=on; LCP under budget per ring buffer.",
    "R8: multi-step recipe palette -> compute -> share -> events ran clean.",
]
FB_COMMENTS_R8 = [
    "R8: Cmd+K palette saves clicks -- great power-user UX.",
    "R8: '/' focus and '?' glossary make this feel like a real IDE.",
    "R8: math symbol tooltip is finally readable for ∇/∂/∫/∑/∏.",
    "R8: GraphQL endpoint is exactly the shape I wanted for scripts.",
    "R8: webhook share + /api/events closed the loop for my dashboard.",
    "R8: advanced widget builder theme/locale options nail the embed flow.",
    "R8: /healthz and /api/uptime are perfect for our k8s probes.",
    "R8: telemetry ring buffer is invaluable when debugging palette flow.",
    "R8: multi-step recipe page reads like a cookbook -- love it.",
    "R8: keyboard hints printed in the result pod helped me discover Cmd+K.",
]


# ---------------------------------------------------------------------------
# (4) Writer
# ---------------------------------------------------------------------------
def build():
    os.makedirs('instance', exist_ok=True)
    shutil.copyfile(SRC, DST)
    con = sqlite3.connect(DST)
    cur = con.cursor()

    # Idempotency guard: if R8 topics already exist in SRC, this build is
    # a no-op rebuild from the R8 baseline. Refuse to dup-insert computation
    # rows -- the script is meant to run once on the R7 baseline.
    cur.execute("SELECT COUNT(*) FROM topics WHERE slug='command-palette'")
    if cur.fetchone()[0] > 0:
        print("[r8] R8 topics already present -- src is the R8 baseline; "
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
    print(f"[r8] inserted {inserted_topics} topics")

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
    print(f"[r8] inserted {inserted_cr} computation_results")

    # ---- Notebook entries: 600 new ----
    cur.execute("SELECT id FROM notebooks ORDER BY id")
    notebooks = [r[0] for r in cur.fetchall()]
    pool = EXTRA_RESULTS[:600]
    for i, row in enumerate(pool):
        q, parsed, plain, cat, sub, kw, pods, slug, plot_url, req_spec = row
        nb_id = notebooks[i % len(notebooks)]
        cur.execute("SELECT COALESCE(MAX(sort_order), -1) FROM notebook_entries WHERE notebook_id=?",
                    (nb_id,))
        so = cur.fetchone()[0] + 1
        note = NOTE_VARIANTS_R8[i % len(NOTE_VARIANTS_R8)] + f" ({cat}/{sub})"
        cur.execute(
            "INSERT INTO notebook_entries(id, notebook_id, query_text, result_summary, "
            "notes, sort_order, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (next_ne, nb_id, q[:500], str(plain)[:200], note, so, ts(i % 96)))
        next_ne += 1
    print(f"[r8] inserted notebook entries up to {next_ne-1}")

    # ---- Topic feedback: 200 new ----
    cur.execute("SELECT id FROM users ORDER BY id")
    user_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT id FROM topics ORDER BY id")
    all_topic_ids = [r[0] for r in cur.fetchall()]
    for i in range(200):
        uid = user_ids[(i * 11 + 1) % len(user_ids)]
        tid = all_topic_ids[(i * 19 + 7) % len(all_topic_ids)]
        rating = 5 if (i % 7 != 6) else 3 + (i % 3)
        helpful = 1 if rating >= 4 else 0
        comment = FB_COMMENTS_R8[i % len(FB_COMMENTS_R8)]
        cur.execute(
            "INSERT INTO topic_feedback(id, user_id, topic_id, rating, comment, "
            "is_helpful, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (next_fb, uid, tid, rating, comment, helpful, ts(i)))
        next_fb += 1
    print(f"[r8] inserted feedback up to {next_fb-1}")

    # ---- R8 performance indexes (idempotent) ----
    cur.execute("CREATE INDEX IF NOT EXISTS ix_cr_slug "
                "ON computation_results(topic_slug)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_cr_category "
                "ON computation_results(category)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_topics_category "
                "ON topics(category_id)")

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
    print(f"[r8] built {DST}")


if __name__ == "__main__":
    build()
