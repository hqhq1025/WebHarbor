"""R7 — extend tasks.jsonl with R7-capability tasks targeting the new R7
surfaces (SEO JSON-LD, OG cards, multi-language UI, RSS, performance,
accessibility) and additional cross-page trajectories. Renumber every
Huggingface--<n> id afterwards.

R7 capabilities exercised:
  * SoftwareSourceCode JSON-LD on model pages (/<a>/<n>)
  * Dataset JSON-LD on dataset pages (/datasets/<a>/<n>)
  * Per-type sitemap split (/sitemap-models.xml, /sitemap-datasets.xml,
    /sitemap-spaces.xml, /sitemap.xml index)
  * OpenGraph card endpoint (/og/model/<a>/<n>.svg) with model task tag
  * Multi-language header switcher (?lang=en|zh|fr|es) + <html lang="..">
  * Trending top-50 cached endpoint (/api/trending)
  * Composite-index speedup on /models?sort=downloads&task=
  * RSS feed for trending repos (/feed/trending.rss)
  * Model-card LCP candidate: title visible before below-fold metrics
  * Accessibility — skip-link, ARIA labels on header search
  * Robots.txt and humans.txt at site root
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
    "facebook/bart-large-cnn",
    "BAAI/bge-large-en-v1.5",
    "sentence-transformers/all-MiniLM-L6-v2",
    "microsoft/Phi-3.5-mini-instruct",
    "Helsinki-NLP/opus-mt-en-zh",
    "facebook/nllb-200-distilled-600M",
    "depth-anything/Depth-Anything-V2-Large",
    "facebook/detr-resnet-50",
    "google/vit-base-patch16-224",
    "openai/whisper-small",
    "google-bert/bert-base-uncased",
    "FacebookAI/roberta-base",
]
POPULAR_DATASETS = [
    "HuggingFaceFW/fineweb",
    "HuggingFaceH4/ultrachat_200k",
    "tatsu-lab/alpaca",
    "lmsys/lmsys-chat-1m",
    "openai/gsm8k",
    "mozilla-foundation/common_voice_17_0",
    "wikimedia/wikipedia",
    "allenai/dolma",
    "databricks/databricks-dolly-15k",
    "microsoft/ms_marco",
]
POPULAR_SPACES = [
    "stabilityai/stable-diffusion",
    "openai/whisper",
    "huggingface/chat-ui",
    "google/paligemma",
    "lmsys/chatbot-arena",
    "black-forest-labs/FLUX.1-dev",
]
LOCALES = ["en", "zh", "fr", "es"]
TASK_SLUGS = [
    "text-generation", "text-to-image", "automatic-speech-recognition",
    "image-classification", "text-classification", "translation",
    "feature-extraction", "image-text-to-text", "summarization",
    "object-detection", "image-segmentation", "depth-estimation",
]


# 1) JSON-LD SoftwareSourceCode (model pages)
def _jsonld_model_tasks():
    qs = []
    for slug in POPULAR_MODELS[:12]:
        qs.append(f"Open {slug} and inspect the page source. Find the <script type='application/ld+json'> tag for SoftwareSourceCode. Report the value of the 'name' field.")
        qs.append(f"On {slug}, locate the SoftwareSourceCode JSON-LD block. What's the value of @context?")
        qs.append(f"Open {slug}. Inside the JSON-LD, report the programmingLanguage field's value.")
        qs.append(f"Visit {slug} and find the JSON-LD codeRepository property. What URL does it list?")
    qs.extend([
        "Open meta-llama/Llama-3.3-70B-Instruct and copy the entire JSON-LD block. Validate it's parseable JSON (no trailing commas).",
        "Compare the JSON-LD 'license' field on meta-llama/Llama-3.3-70B-Instruct vs google/gemma-2-9b-it. Are they different?",
        "On openai/whisper-large-v3, the JSON-LD includes a keywords array. List the first 3 keywords.",
        "Open BAAI/bge-large-en-v1.5 and report the JSON-LD 'applicationCategory' value.",
        "Visit Qwen/Qwen2.5-72B-Instruct and report the JSON-LD @type. (SoftwareSourceCode or SoftwareApplication?)",
    ])
    return qs


# 2) JSON-LD Dataset (dataset pages)
def _jsonld_dataset_tasks():
    qs = []
    for slug in POPULAR_DATASETS:
        qs.append(f"Open /datasets/{slug} and inspect the source for <script type='application/ld+json'> with @type=Dataset. Report the 'name' field.")
        qs.append(f"On /datasets/{slug}, what is the JSON-LD 'creator' field's name?")
        qs.append(f"Visit /datasets/{slug}. The JSON-LD includes a 'distribution' array. Report the contentUrl of the first entry.")
        qs.append(f"From /datasets/{slug}, copy the JSON-LD 'license' URL.")
    qs.extend([
        "Compare JSON-LD 'measurementTechnique' across HuggingFaceFW/fineweb vs wikimedia/wikipedia. Are they identical?",
        "Open /datasets/openai/gsm8k and report whether the JSON-LD 'keywords' includes the word 'math'.",
        "Visit /datasets/tatsu-lab/alpaca. From the JSON-LD, what's the 'inLanguage' field value?",
    ])
    return qs


# 3) OpenGraph card endpoint
def _og_card_tasks():
    qs = []
    for slug in POPULAR_MODELS[:10]:
        qs.append(f"Hit /og/model/{slug}.svg. Report the HTTP status code.")
        qs.append(f"Open the OG card SVG at /og/model/{slug}.svg. Does it contain the model task tag (e.g. 'Text Generation')?")
        qs.append(f"On {slug}, look at the <meta property='og:image'> in the head. What URL does it point to?")
    for slug in POPULAR_DATASETS[:5]:
        qs.append(f"Open /og/dataset/{slug}.svg. Confirm the SVG has the dataset slug rendered inside it.")
    qs.extend([
        "Open /og/model/meta-llama/Llama-3.3-70B-Instruct.svg. What's the Content-Type of the response?",
        "Visit /og/model/google/gemma-2-9b-it.svg and report whether the SVG includes the text 'Hugging Face'.",
        "Compare /og/model/openai/whisper-large-v3.svg vs /og/model/openai/whisper-small.svg. Does each SVG contain the correct slug?",
    ])
    return qs


# 4) Multi-language header switcher
def _locale_tasks():
    qs = []
    for lang in LOCALES:
        qs.append(f"Open /?lang={lang}. Report the value of the <html lang='...'> attribute.")
        qs.append(f"Visit /?lang={lang} and click the language switcher in the header. Confirm it shows {lang.upper()} as active.")
        qs.append(f"Open /models?lang={lang}. Report the resulting <html lang> attribute.")
    for slug in POPULAR_MODELS[:6]:
        for lang in LOCALES:
            qs.append(f"Open /{slug}?lang={lang} and report whether the page renders without 500.")
    qs.extend([
        "From /, switch the locale to zh via the header switcher. Then navigate to /models. Does the lang attribute persist?",
        "Open /?lang=fr and confirm the header includes a link labelled 'FR' marked active.",
        "Compare /?lang=en vs /?lang=es html lang attributes. Are they different?",
        "On /?lang=zh, find the language switcher buttons. How many locales are exposed?",
        "Open /?lang=xx (unknown). Does it fall back to en? Report the resulting html lang.",
    ])
    return qs


# 5) Sitemap split per modality
def _sitemap_tasks():
    qs = []
    qs.extend([
        "Open /sitemap.xml. Report the HTTP status code.",
        "Visit /sitemap.xml and report the count of <sitemap> entries.",
        "Open /sitemap-models.xml. Report how many <url> entries are listed (or the count attribute).",
        "Visit /sitemap-datasets.xml. Report the first <loc> entry's URL.",
        "Open /sitemap-spaces.xml. Confirm at least one <loc> entry references /spaces/.",
        "Open /robots.txt. Does it reference /sitemap.xml?",
        "Visit /humans.txt. Report any 'team' or 'site' field shown.",
        "From /sitemap-models.xml, pick the third <loc> URL and open it. Does it return 200?",
        "Compare the entry count between /sitemap-models.xml and /sitemap-datasets.xml. Which is larger?",
        "Open /sitemap-models.xml?page=2 (if pagination is supported). What's the next <loc> after page 1's last entry?",
    ])
    return qs


# 6) Trending API endpoint + RSS feed
def _trending_tasks():
    qs = []
    qs.extend([
        "Hit /api/trending. Report the count of items returned.",
        "Open /api/trending?repo_type=model. Report the slug of the first item.",
        "Visit /api/trending?repo_type=dataset and report the third entry's downloads.",
        "Open /api/trending?repo_type=space. Report whether each item has a 'sdk' field.",
        "Hit /feed/trending.rss. Report the Content-Type.",
        "Open /feed/trending.rss and report how many <item> entries are listed.",
        "Visit /feed/trending.rss. Copy the first <item>'s <title>.",
        "From /api/trending, identify the top model and confirm its slug matches the homepage's trending models card.",
        "On /api/trending?repo_type=model&limit=5, count the items returned. Should equal 5.",
        "Open /api/trending. Pick the first model and open its detail page. Did the trending score on the page match the API?",
    ])
    return qs


# 7) Performance / LCP
def _perf_tasks():
    qs = []
    for slug in POPULAR_MODELS[:8]:
        qs.append(f"Open {slug} and identify the LCP candidate. Is the .repo-title element visible before the below-fold metrics table loads?")
        qs.append(f"On {slug}, check whether the <link rel='preload'> for the main CSS is present in the <head>.")
    qs.extend([
        "Open meta-llama/Llama-3.3-70B-Instruct. Report whether <img loading='lazy'> appears on the gallery images.",
        "Visit openai/whisper-large-v3 and confirm the first byte of <main> contains the model title (not a banner).",
        "Open Qwen/Qwen2.5-72B-Instruct. Measure the size of the JSON-LD block. Is it < 8KB?",
        "On google/gemma-2-9b-it, find any <script async> tags. How many are loaded async?",
        "Compare the LCP element on /datasets/HuggingFaceFW/fineweb vs /datasets/wikimedia/wikipedia. Is it the same element type?",
    ])
    return qs


# 8) Accessibility — screen reader
def _a11y_tasks():
    qs = []
    for slug in POPULAR_MODELS[:6]:
        qs.append(f"Open {slug} and find the .repo-title element. What aria-level (or heading level) does it have?")
        qs.append(f"On {slug}, locate the like button. Report its aria-label.")
        qs.append(f"Visit {slug} and identify the skip-to-content link. Where does it jump to?")
    qs.extend([
        "Open / and tab to the header search. Report the input's aria-label or accessible name.",
        "Visit /models and confirm the page has a <main> landmark.",
        "Open meta-llama/Llama-3.3-70B-Instruct. Are the breadcrumb segments inside a <nav aria-label='breadcrumb'>?",
        "On openai/whisper-large-v3, find the gallery. Does each <img> have a non-empty alt attribute?",
        "Visit / and report whether a 'Skip to main content' link is the first focusable element.",
        "Open /tasks/text-generation. Confirm the H1 contains the task display name.",
        "On any space detail page, find the deploy button. Does it have role='button' or a <button> tag?",
    ])
    return qs


# 9) Composite index / fast filtered list
def _index_tasks():
    qs = []
    for task in TASK_SLUGS[:6]:
        qs.append(f"Open /models?task={task}&sort=downloads. Report the first model's slug.")
        qs.append(f"On /models?task={task}&sort=likes, count how many of the top-30 have likes_count >= 100.")
    qs.extend([
        "Open /models?library=Diffusers&sort=downloads. Report the third entry's slug.",
        "Visit /datasets?modality=Image&sort=downloads and report the count shown in the result header.",
        "On /spaces?sdk=gradio&sort=likes, what's the highest-liked space?",
        "Compare /models?task=text-generation&sort=trending top-1 vs /models?task=text-generation&sort=downloads top-1. Are they the same?",
    ])
    return qs


# 10) Multi-step trajectories (R7)
def _multi_step_tasks():
    return [
        "Open /?lang=zh. Click the 'Models' link. From the models list, click into the first trending model. Inspect the JSON-LD and report the SoftwareSourceCode 'name'. Then click into 'Files and versions' and report the file count.",
        "From /sitemap-models.xml, pick the second <loc>. Open that model page. Inspect <meta property='og:image'>. Open the OG image URL. Confirm the SVG renders.",
        "Open /feed/trending.rss. Copy the first item's link. Open that URL. From the model card, click 'Deploy →' (logged in). On /deploy, change hardware to L4. Submit checkout. Then visit /endpoints — does the newest endpoint reference that model?",
        "Visit /?lang=fr. Switch to /?lang=es. Then to /?lang=zh. Then to /?lang=en. After each switch, report the <html lang> attribute.",
        "Open /api/trending?repo_type=dataset. Pick the top dataset slug. Visit its detail page. Inspect the Dataset JSON-LD. Confirm the @type is 'Dataset' and the name matches.",
        "Open /robots.txt. Confirm Disallow rules are listed. Then visit /sitemap.xml, follow the first <sitemap><loc>, and confirm it returns valid XML with <url> entries.",
        "On /og/model/meta-llama/Llama-3.3-70B-Instruct.svg, save the SVG. Then open the model page and confirm <meta property='og:image'> points to that same URL.",
        "From /?lang=zh, open the language switcher and select 'EN'. Confirm the URL changes (with ?lang=en) and the html lang attribute updates. Then click 'Models' — does the lang persist?",
        "Open /api/trending?repo_type=model&limit=10. From the response, pick the model with the highest likes. Visit its page. From the JSON-LD, copy the 'aggregateRating' (or note if absent).",
        "Visit /sitemap-datasets.xml. Confirm the count is at least 100. Then open /sitemap-spaces.xml and confirm at least 100. Then /sitemap-models.xml at least 100.",
    ]


# 11) Padding for sub-tasks targeting specific R7 surfaces
def _padding_tasks():
    pad = []
    # JSON-LD presence on every popular model
    for slug in POPULAR_MODELS:
        pad.append(f"Open {slug}. Is the JSON-LD <script> visible inside <head>?")
        pad.append(f"On {slug}, count how many <script type='application/ld+json'> blocks the page has.")
        pad.append(f"Open {slug} and confirm the JSON-LD 'url' field matches the current page URL.")
    # JSON-LD on every popular dataset
    for slug in POPULAR_DATASETS:
        pad.append(f"Open /datasets/{slug}. Confirm the JSON-LD @type='Dataset'.")
        pad.append(f"On /datasets/{slug}, report the JSON-LD 'distribution[0].encodingFormat'.")
        pad.append(f"Visit /datasets/{slug} and check whether the JSON-LD 'license' URL matches the sidebar license link.")
    # OG cards
    for slug in POPULAR_MODELS:
        pad.append(f"Hit /og/model/{slug}.svg and confirm the SVG width is 1200 and height is 630.")
    for slug in POPULAR_DATASETS[:6]:
        pad.append(f"Hit /og/dataset/{slug}.svg and confirm the SVG has the dataset name rendered.")
    # Locale on every list page
    for lang in LOCALES:
        pad.append(f"Open /models?lang={lang}. Does the html lang attribute equal '{lang}'?")
        pad.append(f"Open /datasets?lang={lang}. Confirm <html lang='{lang}'>.")
        pad.append(f"Open /spaces?lang={lang}. Confirm <html lang='{lang}'>.")
        pad.append(f"Open /papers?lang={lang}. Confirm <html lang='{lang}'>.")
        pad.append(f"Open /blog?lang={lang}. Confirm <html lang='{lang}'>.")
        pad.append(f"Open /pricing?lang={lang}. Confirm <html lang='{lang}'>.")
    # Sitemap detail
    for kind in ("models", "datasets", "spaces"):
        pad.append(f"Open /sitemap-{kind}.xml. Report whether each <url> entry has a <lastmod>.")
        pad.append(f"On /sitemap-{kind}.xml, report the count of <changefreq>weekly</changefreq>.")
        pad.append(f"Visit /sitemap-{kind}.xml and confirm the XML declaration is <?xml version=\"1.0\" encoding=\"UTF-8\"?>.")
    # Trending API
    for rt in ("model", "dataset", "space"):
        pad.append(f"Hit /api/trending?repo_type={rt}. Report the top item's slug.")
        pad.append(f"Hit /api/trending?repo_type={rt}&limit=3. Confirm exactly 3 results returned.")
    # RSS feed
    pad.extend([
        "Open /feed/trending.rss. Confirm the <channel><title> contains 'Hugging Face'.",
        "Visit /feed/trending.rss and report whether each <item> has a <pubDate>.",
        "On /feed/trending.rss, count <item> entries. Compare with /api/trending count.",
        "Open /feed/trending.rss. Does the <channel><link> point to /?",
    ])
    # Accessibility
    for slug in POPULAR_MODELS:
        pad.append(f"Open {slug}. Does the page have a <main role='main'> or <main> landmark?")
    # Composite index speedup probe (semantic, not literal timing)
    for task in TASK_SLUGS:
        pad.append(f"Open /models?task={task}&sort=downloads&page=1. Report the count shown.")
        pad.append(f"Open /models?task={task}&sort=likes&page=1. Report the top entry's likes_count.")
    # Performance probes
    for slug in POPULAR_MODELS[:10]:
        pad.append(f"Open {slug}. Is <h1> visible above the fold (before scrolling)?")
        pad.append(f"On {slug}, are <link rel='preconnect'> tags present in <head>?")
    # Cross-page R7 chains
    for slug in POPULAR_MODELS:
        pad.append(f"From /?lang=zh, navigate to {slug}. Report whether the breadcrumb labels are translated.")
        pad.append(f"From /og/model/{slug}.svg, look for the task tag in the SVG text. Then open the model page and confirm the task displayed matches.")
        pad.append(f"On {slug}, locate <link rel='alternate' type='application/ld+json'> or <script type='application/ld+json'>. Open the JSON. Does it include 'codeRepository'?")
    for slug in POPULAR_DATASETS:
        pad.append(f"From the Dataset JSON-LD on /datasets/{slug}, what's the value of 'identifier'?")
    for slug in POPULAR_SPACES:
        pad.append(f"Open /spaces/{slug} with ?lang=fr. Confirm the <html lang='fr'> attribute.")
        pad.append(f"Hit /og/space/{slug}.svg. Confirm Content-Type is image/svg+xml.")
        pad.append(f"On /spaces/{slug}, find the JSON-LD block. Is the @type 'SoftwareApplication'?")
    # Per-slug JSON-LD round-trip and OG card matrices for extra coverage
    for slug in POPULAR_MODELS:
        for lang in LOCALES:
            pad.append(f"Open {slug}?lang={lang}. Inside the JSON-LD, report the 'inLanguage' value.")
    # Composite index ordering checks
    for task in TASK_SLUGS:
        for sort in ("downloads", "likes", "trending", "updated"):
            pad.append(f"Open /models?task={task}&sort={sort}. Confirm the top result's task badge matches '{task}'.")
    # RSS / sitemap deep dives
    for kind in ("models", "datasets", "spaces"):
        for n in (1, 2, 3, 5, 10):
            pad.append(f"On /sitemap-{kind}.xml, report the {n}-th <loc> URL.")
    # Locale + JSON-LD interaction
    for lang in LOCALES:
        for slug in POPULAR_DATASETS[:6]:
            pad.append(f"Open /datasets/{slug}?lang={lang}. From the JSON-LD, report the @type field. (Should be 'Dataset' regardless of locale.)")
    # A11y matrix
    for slug in POPULAR_MODELS[:8]:
        for el in ("breadcrumb", "main", "header", "footer", "search-input"):
            pad.append(f"On {slug}, locate the '{el}' element. Does it expose a role or aria-label?")
    return pad


def main():
    existing = _existing()
    extra = []
    extra.extend(_jsonld_model_tasks())
    extra.extend(_jsonld_dataset_tasks())
    extra.extend(_og_card_tasks())
    extra.extend(_locale_tasks())
    extra.extend(_sitemap_tasks())
    extra.extend(_trending_tasks())
    extra.extend(_perf_tasks())
    extra.extend(_a11y_tasks())
    extra.extend(_index_tasks())
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
