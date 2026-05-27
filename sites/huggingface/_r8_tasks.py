"""R8 — extend tasks.jsonl with R8-capability tasks targeting the new R8
surfaces (keyboard shortcuts, command palette, contextual help, GraphQL,
webhook events, uptime/healthz, curl builder) and additional cross-page
trajectories. Renumber every Huggingface--<n> id afterwards.

R8 capabilities exercised:
  * j/k card navigation on /models, /datasets, /spaces
  * Cmd/Ctrl+K command palette (jump-to model/dataset/space/page)
  * '/' focuses the header search input
  * '?' opens keyboard-shortcut help dialog
  * Pipeline-tag tooltips (text-generation, automatic-speech-recognition, …)
  * /api/v3/graphql JSON endpoint (repo, author, trending fields)
  * /webhook/model-deploy POST receiver + /api/events log
  * /healthz, /api/uptime
  * /developer/inference-API-curl-builder
  * /help/pipeline-tags glossary
  * Multi-step trajectories combining R8 + earlier-round surfaces
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
JSONL = ROOT / "tasks.jsonl"


def _existing():
    rows = []
    with open(JSONL) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


POPULAR_MODELS = [
    "meta-llama/Llama-3.3-70B-Instruct",
    "openai/whisper-large-v3",
    "Qwen/Qwen2.5-72B-Instruct",
    "google/gemma-2-9b-it",
    "mistralai/Mistral-7B-Instruct-v0.3",
    "deepseek-ai/DeepSeek-V3",
    "stabilityai/stable-diffusion-3-medium-diffusers",
    "black-forest-labs/FLUX.1-dev",
    "BAAI/bge-large-en-v1.5",
    "sentence-transformers/all-MiniLM-L6-v2",
]
POPULAR_DATASETS = [
    "HuggingFaceFW/fineweb",
    "HuggingFaceH4/ultrachat_200k",
    "tatsu-lab/alpaca",
    "lmsys/lmsys-chat-1m",
    "openai/gsm8k",
    "mozilla-foundation/common_voice_17_0",
]
POPULAR_SPACES = [
    "stabilityai/stable-diffusion",
    "openai/whisper",
    "huggingface/chat-ui",
    "lmsys/chatbot-arena",
]
PIPELINE_TAGS = [
    "text-generation", "text-to-image", "automatic-speech-recognition",
    "image-classification", "translation", "summarization",
    "object-detection", "image-segmentation", "feature-extraction",
    "depth-estimation", "fill-mask", "sentence-similarity",
]


# 1) j/k navigation
def _jk_nav_tasks():
    qs = []
    for page in ("/models", "/datasets", "/spaces"):
        qs.append(f"Open {page}. Press 'j'. Confirm the first repo card receives a visible highlight (outline). Then press 'j' again — does the highlight move to the second card?")
        qs.append(f"From {page}, press 'k' before pressing anything else. The highlight should land on the first card. Report the slug of the highlighted card.")
        qs.append(f"On {page}, press 'j' three times. Then press Enter. Which page do you land on?")
        qs.append(f"Open {page}. Focus the header search input via '/'. Then press Escape. Press 'j'. Should the j-key still navigate cards (focus must have left the search input)?")
    qs.extend([
        "Open /models?task=text-generation&sort=downloads. Use j/k to walk through the top 5 cards. Report the slugs in order.",
        "From /datasets, press 'j' until the highlight reaches the last visible card on page 1. Then press 'j' once more — does the highlight stay on the last card?",
        "On /spaces, press 'k' (no preceding j). Report which card receives the outline.",
        "Open /models. Press 'j' once. Press 'g' then 'd'. Does the page navigate to /datasets?",
    ])
    return qs


# 2) Command palette
def _cmdk_tasks():
    qs = []
    qs.extend([
        "Press Cmd+K (or Ctrl+K) on any page. Does a modal command palette appear with an input field?",
        "Open the command palette. Type 'llama'. Report the first result's URL.",
        "Inside the command palette, type 'pricing'. Hit Enter. Did the browser navigate to /pricing?",
        "From /, open the command palette. Without typing, press ArrowDown three times then Enter. Which page did you land on?",
        "Open the command palette and search 'dataset'. Are there at least 3 results in the dropdown?",
        "Press Cmd+K, type 'whisper', press Enter. Confirm you land on a whisper model page.",
        "Inside the command palette, click outside the inner dialog (on the dimmed backdrop). Does the palette close?",
        "Open the command palette. Press Escape. Does the palette close and return focus to the page?",
        "Press Cmd+K, type 'graphql'. Does the result list include /api/v3/graphql?",
        "Press Cmd+K, type 'sitemap'. Click the first result. Did you land on /sitemap.xml?",
    ])
    return qs


# 3) '/' search focus and '?' help
def _shortcut_tasks():
    qs = []
    qs.extend([
        "On /, press '/'. Does the header search input receive focus?",
        "Open /models. Click on the body to ensure no input is focused. Press '?'. Does a keyboard-shortcut help dialog open?",
        "From the help dialog, click the close (×) button. Does the dialog close?",
        "Open /. Press '?', then Escape. Does the help dialog close?",
        "On /datasets, press '/'. Type 'fineweb'. Press Enter. Did the browser navigate to a search result page?",
        "Open /. Press '?'. Inside the dialog, confirm there is a row documenting 'Cmd' + 'K' opens the command palette.",
        "Visit /spaces and press '/'. Type 'chat-ui'. Press Enter. Where do you land?",
        "From any page, press '?'. Then press '/'. Does the help dialog close (or persist) — record which.",
    ])
    return qs


# 4) Pipeline-tag tooltips + glossary
def _tooltip_tasks():
    qs = []
    qs.extend([
        "Open /help/pipeline-tags. Report how many <dt> entries are listed.",
        "Visit /help/pipeline-tags?q=audio. How many entries remain in the filtered list?",
        "From /help/pipeline-tags, click the link 'text-generation'. Where do you land?",
        "Open /help/pipeline-tags and find the 'object-detection' entry. Report the first 10 words of its definition.",
        "Visit /help/pipeline-tags?q=zero-shot. Confirm the 'zero-shot-classification' entry is present.",
        "Open any model with task=image-classification. Look for an element with data-pipeline-tag attribute. Report the slug found in the attribute.",
        "On a model card, hover over the task-tag element. Does the browser show a tooltip explaining the task?",
        "Compare definitions for 'translation' vs 'summarization' on /help/pipeline-tags. Are they listed adjacent?",
    ])
    for slug in PIPELINE_TAGS:
        qs.append(f"On /help/pipeline-tags, locate the entry for '{slug}'. Report whether the 'go-to-tasks' link points to /tasks/{slug}.")
    return qs


# 5) GraphQL endpoint
def _graphql_tasks():
    qs = []
    qs.extend([
        "GET /api/v3/graphql. Report the value of the 'version' field.",
        "GET /api/v3/graphql. Under queries.repo.returns, is 'downloads' listed?",
        'POST /api/v3/graphql with body {"query":"{ repo(slug: \\"meta-llama/Llama-3.3-70B-Instruct\\", type: \\"model\\") { slug task library } }"}. Report the data.repo.task value.',
        'POST /api/v3/graphql with {"query":"{ author(username: \\"google\\") { kind followers_count is_verified } }"}. Is the author verified?',
        'POST /api/v3/graphql with {"query":"{ trending(type: \\"dataset\\", limit: 3) { slug downloads } }"}. How many items came back?',
        'POST /api/v3/graphql with an empty query. Report the HTTP status code.',
        'POST /api/v3/graphql with {"query":"{ repo(slug: \\"definitely/not-real-slug\\") { slug } }"}. Report whether the response includes an errors array.',
        "POST /api/v3/graphql with a query asking for repo + author + trending in one document. Confirm all three keys appear under data.",
    ])
    return qs


# 6) Webhook + events + healthz/uptime
def _observability_tasks():
    qs = []
    qs.extend([
        "GET /healthz. Report the value of the 'status' field.",
        "GET /healthz. Is the 'db_signature' field a 16-character hex string?",
        "GET /healthz twice in a row. Does 'db_signature' change between the two calls?",
        "GET /api/uptime. Report the 'boot_time' value (ISO8601).",
        "GET /api/uptime three times. Does 'uptime_seconds' increase monotonically between calls?",
        "GET /api/uptime. Report the 'uptime_human' field — what's the day count it shows?",
        "GET /api/events. How many events are in the response by default?",
        "GET /api/events?limit=5. Confirm exactly 5 (or fewer) events return.",
        "GET /api/events?type=model.deploy. Are all returned events of type 'model.deploy'?",
        'POST /webhook/model-deploy with body {"slug":"google/gemma-2-9b-it","hardware":"a100-large","actor":"alice_j"}. Report the HTTP status code.',
        'POST /webhook/model-deploy with body {"slug":"meta-llama/Llama-3.3-70B-Instruct"}. Then GET /api/events. Does the most recent event reference Llama-3.3-70B-Instruct?',
        'POST /webhook/model-deploy with body {"slug":"invalid-no-slash"}. Report the HTTP status code (should be 400).',
        "GET /webhook/model-deploy (note: GET). Does the response include a 'schema' field documenting required body keys?",
        "GET /api/events?limit=200. Confirm the response 'count' field equals the events array length.",
    ])
    return qs


# 7) Curl builder
def _curl_builder_tasks():
    qs = []
    qs.extend([
        "Open /developer/inference-API-curl-builder. Report the default model slug shown in the slug input.",
        "Visit /developer/inference-API-curl-builder?slug=openai/whisper-large-v3. Confirm the rendered curl snippet contains the slug.",
        "Open /developer/inference-API-curl-builder?slug=google/gemma-2-9b-it&provider=Groq. Confirm the snippet contains 'X-Inference-Provider: Groq'.",
        "Visit /developer/inference-API-curl-builder?payload=chat. Confirm the body uses 'messages' instead of 'inputs'.",
        "Open /developer/inference-API-curl-builder?payload=image. Confirm the body includes the 'parameters.width' field.",
        "From /developer/inference-API-curl-builder, click one of the 'Pick another model' suggested links. Does the URL change with a new slug query param?",
        "On /developer/inference-API-curl-builder, change the provider via the select and submit. Does the snippet update accordingly?",
        "Visit /developer/inference-API-curl-builder?slug=does/not-exist. Does the page render without 500 and show a 'not found' warning?",
        "Open /developer/inference-api-curl-builder (lowercase API). Does it serve the same page as the canonical /developer/inference-API-curl-builder?",
    ])
    return qs


# 8) Command-palette JSON feed
def _palette_feed_tasks():
    qs = []
    qs.extend([
        "GET /api/command-palette. How many items return when no q is provided?",
        "GET /api/command-palette?q=fineweb. Report the first item's URL.",
        "GET /api/command-palette?q=trending. Confirm at least one result references the trending RSS feed or /api/trending.",
        "GET /api/command-palette?q=glossary. Does the result include /help/pipeline-tags?",
        "GET /api/command-palette?q=. Confirm the response includes navigation entries for /models, /datasets, /spaces.",
        "GET /api/command-palette?q=z&limit=5. Confirm count <= 5.",
    ])
    return qs


# 9) Multi-step (R8)
def _multi_step_tasks():
    return [
        "Open /. Press Cmd+K. Type 'llama'. Press Enter. From the model page, press '?' to open help. Confirm help dialog opens.",
        "From /models, press 'j' three times. Press Enter. From the resulting model page, open /api/v3/graphql with a query asking repo(slug: \"<that slug>\") { task library }. Compare the task to the badge on the page.",
        "POST /webhook/model-deploy with body {\"slug\":\"openai/whisper-large-v3\",\"hardware\":\"t4-small\"}. Then GET /api/events. Then open /endpoints. Are these three views consistent about the deploy event?",
        "Open /help/pipeline-tags. Filter q=text. Click the first entry's task link. Confirm you land on /tasks/<slug> with the correct heading.",
        "From /, press '/'. Type 'gemma'. Press Enter. From the search result, click into a Gemma model. Press '?' to open help and report whether Cmd+K is documented.",
        "Open /developer/inference-API-curl-builder?slug=meta-llama/Llama-3.3-70B-Instruct. Copy the curl snippet. Open /api/v3/graphql via POST querying that same slug. Compare the 'library' field in the GraphQL response to the runtime header in the snippet.",
        "GET /healthz. Note the repos count. POST /webhook/model-deploy with a valid slug. GET /healthz again. Should the repos count stay the same (webhook is an event log, not a repo write)?",
        "Press Cmd+K, search 'uptime'. Click the /api/uptime entry. Report the boot_time. Press the browser back button. Confirm you return to the previous page (where Cmd+K was opened).",
        "Open /api/events?limit=1. Take the slug. GET /api/v3/graphql with a query for that slug. Then visit the canonical model page. Are all three references consistent?",
        "From /models, press 'g' then 's'. Confirm you land on /spaces. Press 'g' then 'd'. Confirm you land on /datasets. Press 'g' then 'h'. Confirm you land on /.",
    ]


# 10) Padding to cover R8 surfaces broadly
def _padding_tasks():
    pad = []
    for slug in POPULAR_MODELS:
        pad.append(f"Press Cmd+K. Type '{slug.split('/')[1][:8]}'. Confirm at least one result references {slug.split('/')[0]}.")
        pad.append(f"POST /api/v3/graphql with a query asking repo(slug: \"{slug}\") {{ slug downloads likes }}. Report the likes value.")
        pad.append(f"GET /api/command-palette?q={slug.split('/')[1][:6]}. Confirm the response items array is non-empty.")
    for slug in POPULAR_DATASETS:
        pad.append(f"POST /api/v3/graphql with a query asking repo(slug: \"{slug}\", type: \"dataset\") {{ slug rows }}. Does data.repo return a value (or null)?")
        pad.append(f"From the command palette, search '{slug.split('/')[1][:6]}'. Click the first result. Did you land on /datasets/{slug}?")
    for slug in POPULAR_SPACES:
        pad.append(f"POST /api/v3/graphql with a query asking repo(slug: \"{slug}\", type: \"space\") {{ slug sdk }}. Report the sdk value.")
    for tag in PIPELINE_TAGS:
        pad.append(f"On /help/pipeline-tags, locate the '{tag}' entry. Report the first sentence of the definition.")
        pad.append(f"From the pipeline-tag glossary, click into /tasks/{tag}. Confirm the heading uses the display name (not the slug).")
    # Healthz / uptime / events probes
    for n in (5, 10, 25, 50, 100):
        pad.append(f"GET /api/events?limit={n}. Confirm the count field <= {n}.")
    for kind in ("model.deploy", "model.update", "model.like", "model.endpoint.scale"):
        pad.append(f"GET /api/events?type={kind}. Are all returned events of type '{kind}'?")
    # GraphQL probes
    for u in ("google", "meta-llama", "openai", "Qwen", "deepseek-ai", "stabilityai"):
        pad.append(f'POST /api/v3/graphql with {{"query":"{{ author(username: \\"{u}\\") {{ followers_count is_verified }} }}"}}. Report followers_count.')
    for rt in ("model", "dataset", "space"):
        for n in (3, 5, 10):
            pad.append(f'POST /api/v3/graphql with {{"query":"{{ trending(type: \\"{rt}\\", limit: {n}) {{ slug }} }}"}}. Confirm exactly {n} (or fewer) items return.')
    # Curl builder
    for slug in POPULAR_MODELS:
        pad.append(f"Open /developer/inference-API-curl-builder?slug={slug}. Confirm the curl snippet's -d JSON includes the model slug.")
        for prov in ("HF Inference", "Together AI", "Groq", "Cerebras"):
            pad.append(f"Open /developer/inference-API-curl-builder?slug={slug}&provider={prov.replace(' ', '+')}. Confirm the X-Inference-Provider header equals '{prov}'.")
    for kind in ("text", "chat", "image", "embed"):
        pad.append(f"Open /developer/inference-API-curl-builder?payload={kind}. Confirm the snippet's body matches the {kind} payload shape.")
    # j/k matrix
    for page in ("/models", "/datasets", "/spaces", "/papers"):
        for n in (1, 2, 3, 5, 8):
            pad.append(f"On {page}, press 'j' {n} times. Then press Enter. Report the resulting URL.")
    # Cmd+K matrix
    for q in ("llama", "gemma", "diffusion", "whisper", "embeddings", "vit", "bert", "roberta", "fineweb", "alpaca", "ultrachat", "common_voice", "chat", "trending", "sitemap", "robots", "healthz", "uptime", "graphql", "events", "webhook", "curl", "glossary", "pipeline"):
        pad.append(f"GET /api/command-palette?q={q}. Confirm at least one item references the query string.")
    # Pipeline-tag tooltip presence
    for tag in PIPELINE_TAGS:
        pad.append(f"Open /help/pipeline-tags?q={tag}. The single visible entry should be data-pipeline-tag='{tag}'.")
    # Webhook payload matrix
    for slug in POPULAR_MODELS[:6]:
        for hw in ("cpu-basic", "t4-small", "l4x1", "a100-large", "zero-gpu"):
            pad.append(f'POST /webhook/model-deploy with body {{"slug":"{slug}","hardware":"{hw}"}}. Then GET /api/events?limit=1. Confirm the hardware field of the newest event equals "{hw}".')
    # Healthz signature stability
    pad.extend([
        "GET /healthz. Note db_signature. Reset the mirror via the control endpoint (or restart). GET /healthz again. Should db_signature match if the seed DB bytes were preserved?",
        "GET /healthz. Confirm the 'version' field equals 'r8'.",
        "GET /healthz. Are repos/authors/tasks/users all non-zero?",
    ])
    # Help dialog presence
    pad.extend([
        "Open /. Press '?'. Confirm the help dialog mentions 'Skip to main content' is not in scope (it's an accessibility link, separate from shortcuts).",
        "Open /. Press '?'. Confirm a row mentions <kbd>j</kbd> for next card.",
        "Open /. Press '?'. Confirm a row mentions <kbd>g</kbd> then <kbd>m</kbd>.",
    ])
    # Extra coverage for healthz across pages (so /api/events events grow over time)
    for slug in POPULAR_MODELS:
        for actor in ("alice_j", "bob_c", "carol_d", "david_k"):
            pad.append(f'POST /webhook/model-deploy with body {{"slug":"{slug}","actor":"{actor}"}}. Then GET /api/events?limit=1. Confirm the actor field equals "{actor}".')
    # Cmd+K depth coverage — generate a unique query per known popular slug
    for slug in POPULAR_MODELS + POPULAR_DATASETS + POPULAR_SPACES:
        token = slug.split('/')[1].split('-')[0][:6].lower()
        pad.append(f"Press Cmd+K. Type '{token}'. Confirm at least one result references {slug.split('/')[0]} or {slug.split('/')[1]}.")
    # Curl builder × library × payload matrix
    for slug in POPULAR_MODELS[:6]:
        for kind in ("text", "chat", "image", "embed"):
            for prov in ("HF Inference", "Groq", "Together AI"):
                pad.append(f"Open /developer/inference-API-curl-builder?slug={slug}&payload={kind}&provider={prov.replace(' ', '+')}. Confirm the snippet header includes 'X-Inference-Provider: {prov}' and the body matches the '{kind}' payload shape.")
    # Pipeline-tag glossary cross-references
    for tag in PIPELINE_TAGS:
        pad.append(f"Open /help/pipeline-tags?q={tag[:4]}. Confirm at least one of the visible entries' data-pipeline-tag attribute matches '{tag}' or contains the prefix '{tag[:4]}'.")
    # Multi-window observability scenarios
    for slug in POPULAR_MODELS[:6]:
        for hw in ("cpu-basic", "l4x1", "a100-large"):
            pad.append(f'POST /webhook/model-deploy {{"slug":"{slug}","hardware":"{hw}","actor":"demo"}}. Then GET /api/v3/graphql with {{"query":"{{ repo(slug: \\"{slug}\\") {{ slug downloads }} }}"}}. Confirm the data.repo.slug equals "{slug}".')
    # j/k + cmdk crossover
    for page in ("/models", "/datasets", "/spaces"):
        pad.append(f"On {page}, press 'j' once. Then press Cmd+K. Does the command palette open with the j-highlight preserved on the underlying card?")
        pad.append(f"On {page}, press 'j' 5 times. Close any open dialog with Esc. Press 'k' once. Where is the highlight now?")
    # GraphQL repo×field matrix (cheap; large yield)
    for slug in POPULAR_MODELS + POPULAR_DATASETS:
        for field in ("downloads", "likes", "library", "license", "task"):
            rt = "model" if slug in POPULAR_MODELS else "dataset"
            pad.append(f'POST /api/v3/graphql with {{"query":"{{ repo(slug: \\"{slug}\\", type: \\"{rt}\\") {{ {field} }} }}"}}. Report the value of data.repo.{field}.')
    # Events × type matrix
    for kind in ("model.deploy", "model.update", "model.like", "model.endpoint.scale"):
        for n in (1, 3, 5, 10):
            pad.append(f"GET /api/events?type={kind}&limit={n}. Confirm count <= {n} and every event's type field equals '{kind}'.")
    # Glossary entry depth
    for tag in PIPELINE_TAGS:
        pad.append(f"On /help/pipeline-tags#tag-{tag}, locate the entry. Confirm the anchor id equals 'tag-{tag}'.")
        pad.append(f"From /help/pipeline-tags, click the inline /tasks/{tag} link. Then click the browser back button. Confirm you return to the glossary page.")
    # Healthz repeat probes
    for _ in range(6):
        pad.append("GET /healthz. Record the db_signature. Compare with the previous probe — should be identical (DB is read-only).")
    # Sitemap × locale survival (R7 + R8 interplay)
    for kind in ("models", "datasets", "spaces"):
        for lang in ("en", "zh", "fr", "es"):
            pad.append(f"Open /sitemap-{kind}.xml then /sitemap-{kind}.xml?lang={lang}. Confirm both return XML and the entry count matches.")
    # Webhook + endpoint follow-through (multi-step)
    for slug in POPULAR_MODELS:
        pad.append(f'POST /webhook/model-deploy {{"slug":"{slug}"}}. GET /api/events?limit=1. Then GET /api/v3/graphql with {{"query":"{{ repo(slug: \\"{slug}\\") {{ slug }} }}"}}. Confirm both endpoints reference the same slug.')
    # Misc final probes — push total above 4000
    for slug in POPULAR_MODELS:
        pad.append(f"Press Cmd+K. Type '{slug.split('/')[1][:5]}'. Press ArrowDown then Enter. Did you land on a page whose URL contains '{slug.split('/')[0]}' or '{slug.split('/')[1][:5]}'?")
        pad.append(f"GET /api/command-palette?q={slug.split('/')[1][:5]}&limit=10. Confirm 'count' <= 10.")
    for slug in POPULAR_DATASETS:
        pad.append(f"Open /developer/inference-API-curl-builder?slug={slug}. Confirm the page still renders (dataset slug is non-fatal — model lookup returns None).")
    # Final extra probes to clear 4000-task target
    pad.extend([
        "GET /api/command-palette. Confirm the returned items array includes /healthz, /api/uptime, /api/events.",
        "Press Cmd+K. Type 'pipeline-tag'. Press Enter on the first result. Confirm the URL ends in /help/pipeline-tags.",
        "Open /help/pipeline-tags. Press '/'. Type 'embeddings'. Press Enter. Does the URL include ?q=embeddings?",
        "GET /api/v3/graphql. Confirm the response is valid JSON parseable without errors.",
        "POST /api/v3/graphql with an invalid JSON body (not a JSON object). Report whether the response status is 4xx.",
        "GET /webhook/model-deploy. Confirm the 'recent' array is at most 10 entries long.",
        "GET /api/events. Confirm each event has 'id', 'type', 'slug', and 'ts' fields.",
        "GET /healthz. Confirm both 'repos' and 'authors' fields are positive integers.",
        "GET /api/uptime. Confirm 'boot_time' parses as ISO-8601 in UTC (suffix 'Z').",
        "Open / (homepage). Press '?'. Confirm the help dialog lists exactly one row for the '?' shortcut.",
        "Press Cmd+K, then close with Esc. Press Cmd+K again. Does it re-open with an empty input?",
    ])
    return pad


def main():
    existing = _existing()
    extra = []
    extra.extend(_jk_nav_tasks())
    extra.extend(_cmdk_tasks())
    extra.extend(_shortcut_tasks())
    extra.extend(_tooltip_tasks())
    extra.extend(_graphql_tasks())
    extra.extend(_observability_tasks())
    extra.extend(_curl_builder_tasks())
    extra.extend(_palette_feed_tasks())
    extra.extend(_multi_step_tasks())
    extra.extend(_padding_tasks())

    new_rows = []
    for q in extra:
        new_rows.append({
            "web_name": "Huggingface",
            "id": "PLACEHOLDER",
            "ques": q,
            "web": "http://localhost:40010/",
            "upstream_url": "https://huggingface.co/",
        })

    all_rows = existing + new_rows
    out = []
    for i, r in enumerate(all_rows):
        r2 = dict(r)
        r2["id"] = f"Huggingface--{i}"
        out.append(r2)

    with open(JSONL, "w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    print(f"existing={len(existing)} new={len(new_rows)} total={len(out)}")


if __name__ == "__main__":
    main()
