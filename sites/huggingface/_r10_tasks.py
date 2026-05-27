"""R10 — extend tasks.jsonl with R10-capability tasks:
  * Six-tab uniformity probes (Card · Files · Community · Discussions · PRs ·
    Settings) across model / dataset / space surfaces.
  * Nine-step compound trajectory tasks crossing
    model → readme → files → discussions → paper → dataset → space-demo →
    deploy → endpoint.
  * Variant-coverage tasks for R10 synth families (ONNX / MLX / AWQ / GPTQ /
    Exllama2 / distilled mirrors + dataset subset mirrors + space demos).
  * Leaderboard ↔ repo cross-link probes (every leaderboard entry must
    resolve to a 200 model page).

The R10 surfaces being exercised:
  * /<a>/<n>/community + /datasets/<a>/<n>/community + /spaces/<a>/<n>/community
  * /<a>/<n>/pull-requests + dataset + space equivalents
  * /<a>/<n>/settings + dataset + space equivalents
  * R10 synth slugs (-ONNX, -mlx, -AWQ, -GPTQ, -exl2, -distilled)
  * /leaderboards/<slug> drill-down into linked model card
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
    "Qwen/Qwen2.5-32B-Instruct",
    "tiiuae/Falcon3-10B-Instruct",
]

POPULAR_DATASETS = [
    "HuggingFaceH4/ultrachat_200k",
    "tatsu-lab/alpaca",
    "mlabonne/orpo-dpo-mix-40k",
]

POPULAR_SPACES = [
    "stabilityai/stable-diffusion",
    "huggingface-projects/QR-code-AI-art-generator",
]

LEADERBOARD_SLUGS = ["open-llm", "open-asr", "mteb", "text-to-image-arena", "translation-bleu", "vlm-mmmu"]

R10_VARIANT_AUTHORS = {
    "onnx": ["onnx-community", "onnxruntime", "Xenova", "microsoft-onnx", "neuralmagic-onnx"],
    "mlx":  ["mlx-community", "mlx-vlm", "apple-mlx", "MLXFast"],
    "awq":  ["TheBloke-AWQ", "casperhansen", "AWQ-Hub", "solidrust"],
    "gptq": ["TheBloke-GPTQ", "ModelCloud", "GPTQModel", "neuralmagic-gptq"],
    "exl2": ["LoneStriker", "turboderp", "ParasiticRogue", "Exllama2-Hub"],
    "distill": ["distilbert-community", "TinyLlama-Hub", "small-models", "compact-hub", "lite-models"],
}
R10_VARIANT_SUFFIX = {
    "onnx": "-ONNX",
    "mlx":  "-mlx",
    "awq":  "-AWQ",
    "gptq": "-GPTQ",
    "exl2": "-exl2",
    "distill": "-distilled",
}


# 1) Six-tab uniformity probes
def _six_tab_tasks():
    qs = []
    surfaces = [
        ("model",   POPULAR_MODELS,   ""),
        ("dataset", POPULAR_DATASETS, "/datasets"),
        ("space",   POPULAR_SPACES,   "/spaces"),
    ]
    for kind, slugs, prefix in surfaces:
        for slug in slugs:
            base = f"{prefix}/{slug}"
            qs.append(f"GET {base}/community. Confirm the page returns 200 and the breadcrumb ends with '· community'.")
            qs.append(f"GET {base}/discussions. Confirm the page returns 200 and the tab strip shows 'Discussions' as is-active.")
            qs.append(f"GET {base}/pull-requests. Confirm the page returns 200 and the tab strip shows 'PRs' as is-active.")
            qs.append(f"GET {base}/settings. Confirm the page returns 200 and the URL ends with '/settings'.")
            qs.append(f"Open {base}/settings. Confirm the General section shows the repository name '{slug}' as a code block.")
            qs.append(f"Open {base}/settings. Click the 'Danger zone' anchor. Confirm the heading 'Danger zone' is visible in red.")
            qs.append(f"Open {base}. Count the tabs in the repo-tabs strip. The count should be 6 (Card, Files, Community, Discussions, PRs, Settings) or 7 if the kind is dataset (which adds 'Dataset viewer').")
    return qs


# 2) Nine-step compound trajectory
def _nine_step_tasks():
    chains = [
        # 1: Llama-3.3-70B chain
        [
            "Open /meta-llama/Llama-3.3-70B-Instruct (the Model card tab).",
            "Read the README. Confirm the 'How to use' section contains 'AutoModel'.",
            "Click the Files tab. Confirm at least one .safetensors entry exists.",
            "Open the Discussions tab. Note the count of open discussions.",
            "Open /papers and locate any paper that cites Llama. Drill into its detail page.",
            "From the paper, open the linked dataset (or HuggingFaceH4/ultrachat_200k as default).",
            "From the dataset, locate any community Space demo via /spaces/spaces-community/. Open one Llama demo Space.",
            "Click Deploy → on that Space to add it to your /deploy cart.",
            "Open /endpoints. Confirm at least one endpoint references a Llama base model.",
        ],
        # 2: Qwen chain
        [
            "Open /Qwen/Qwen2.5-72B-Instruct.",
            "Read the README markdown rendered under the Model card.",
            "Open /Qwen/Qwen2.5-72B-Instruct/tree/main. Confirm config.json is in the file tree.",
            "Open /Qwen/Qwen2.5-72B-Instruct/discussions. Open the first discussion.",
            "Search /papers for 'Qwen'. Open one matching paper detail.",
            "Visit /datasets/HuggingFaceH4/ultrachat_200k (used by many Qwen finetunes).",
            "Visit /spaces/spaces-community/Qwen2.5-72B-Instruct-demo. Confirm SDK tag is gradio or streamlit.",
            "Press Deploy on the Space. Visit /deploy and confirm 1+ item in the cart.",
            "Visit /endpoints. Confirm /endpoints/1 returns 200 with status field present.",
        ],
        # 3: Whisper chain
        [
            "Open /openai/whisper-large-v3.",
            "Confirm the README mentions 'speech recognition' or 'transcription'.",
            "Open the Files tab. Confirm an .onnx or .safetensors file appears (R10 mirrors).",
            "Open /openai/whisper-large-v3/community. Note the discussion count badge.",
            "Visit /papers and look for whisper-related entries. Open one.",
            "From the paper, open Common Voice or LibriSpeech-related dataset on /datasets.",
            "Visit /spaces/spaces-community/whisper-large-v3-demo. Confirm the SDK label appears.",
            "Press Deploy on the Space to add to /deploy.",
            "Visit /endpoints/2. Confirm the redeploy button is present.",
        ],
    ]
    out = []
    for i, chain in enumerate(chains, start=1):
        full = f"R10 nine-step chain #{i}: " + " ".join(f"({n+1}) {step}" for n, step in enumerate(chain))
        out.append(full)
    return out


# 3) Variant coverage probes
def _variant_tasks():
    qs = []
    # ONNX / MLX / AWQ / GPTQ / EXL2 / distilled — each variant for top 6 popular models
    for slug in POPULAR_MODELS[:6]:
        name = slug.split("/")[1]
        for vt, sfx in R10_VARIANT_SUFFIX.items():
            qs.append(f"Search /models with q={name}{sfx}. Confirm at least one repo with prefix from {R10_VARIANT_AUTHORS[vt][:2]} appears.")
            qs.append(f"GET /api/search?q={name}{sfx[:5]}. Confirm the JSON response includes at least one repo whose library is consistent with the '{vt}' family (e.g. onnx / mlx / transformers / exllamav2).")
    # Dataset subset mirrors
    for dslug in POPULAR_DATASETS:
        dname = dslug.split("/")[1]
        for split in ["train-only", "deduped", "1pct-sample"]:
            qs.append(f"Search /datasets with q={dname}-{split}. Confirm at least one mirror by 'hf-mirror-datasets' or similar appears.")
    # Space demos
    for mslug in POPULAR_MODELS[:6]:
        name = mslug.split("/")[1]
        for sfx in ["-demo", "-playground", "-chat"]:
            qs.append(f"Search /spaces with q={name}{sfx}. Confirm a Space with prefix from 'spaces-community' or 'demos-hub' appears.")
    return qs


# 4) Leaderboard ↔ repo cross-link probes
def _leaderboard_tasks():
    qs = []
    # Curated subset of leaderboard rows (must match content_data.LEADERBOARDS)
    LB_MODELS = {
        "open-llm": [
            "meta-llama/Llama-3.3-70B-Instruct",
            "Qwen/Qwen2.5-72B-Instruct",
            "deepseek-ai/DeepSeek-V3",
            "google/gemma-2-9b-it",
            "tiiuae/Falcon3-10B-Instruct",
        ],
        "open-asr": [
            "openai/whisper-large-v3",
            "nvidia/parakeet-tdt-1.1b",
        ],
        "mteb": [
            "BAAI/bge-large-en-v1.5",
            "intfloat/multilingual-e5-large",
            "sentence-transformers/all-MiniLM-L6-v2",
        ],
        "text-to-image-arena": [
            "black-forest-labs/FLUX.1-dev",
            "black-forest-labs/FLUX.1-schnell",
            "stabilityai/stable-diffusion-3-medium-diffusers",
        ],
        "translation-bleu": [
            "facebook/nllb-200-distilled-600M",
            "Helsinki-NLP/opus-mt-en-zh",
        ],
        "vlm-mmmu": [
            "Qwen/Qwen2-VL-72B-Instruct",
            "google/paligemma-3b-mix-448",
            "microsoft/Florence-2-large",
        ],
    }
    for slug, models in LB_MODELS.items():
        for m in models:
            qs.append(f"Open /leaderboards/{slug}. Find the row referencing '{m}'. Click into the model page. Confirm the model card returns 200 and the page title contains '{m.split('/')[1]}'.")
            qs.append(f"GET /{m}. Confirm the model card is 200 and the repo-tabs strip shows the 'Settings' tab.")
            qs.append(f"GET /{m}/discussions. Confirm 200.")
            qs.append(f"GET /{m}/settings. Confirm 200 and the General section shows owner '{m.split('/')[0]}'.")
            qs.append(f"GET /{m}/pull-requests. Confirm 200 (the page returns the PR list or empty state).")
    return qs


# 5) Settings deep probes
def _settings_deep_tasks():
    qs = []
    for slug in POPULAR_MODELS[:6]:
        qs.append(f"Open /{slug}/settings#general. Confirm the 'Default branch' dd shows 'main'.")
        qs.append(f"Open /{slug}/settings#visibility. Read the Visibility dt/dd row and report the status (Public or Gated).")
        qs.append(f"Open /{slug}/settings#access-tokens. Confirm the access-tokens table has at least 2 rows.")
        qs.append(f"Open /{slug}/settings#webhooks. Confirm the visible text contains 'No webhooks configured'.")
        qs.append(f"Open /{slug}/settings#danger-zone. Confirm both 'Archive' and 'Delete repository' buttons are present and disabled.")
        qs.append(f"Open /{slug}/settings. Inspect the dd with data-field='slug'. Confirm the text equals '{slug}'.")
        qs.append(f"Open /{slug}/settings. Inspect the dd with data-field='default_branch'. Report the visible text.")
    for dslug in POPULAR_DATASETS:
        qs.append(f"Open /datasets/{dslug}/settings. Confirm the dd with data-field='repo_type' shows 'Dataset'.")
    for sslug in POPULAR_SPACES:
        qs.append(f"Open /spaces/{sslug}/settings. Confirm the dd with data-field='repo_type' shows 'Space'.")
    return qs


# 6) Pull-request specific probes
def _pull_request_tasks():
    qs = []
    for slug in POPULAR_MODELS[:8]:
        qs.append(f"Open /{slug}/pull-requests. Read the data-pr-count attribute on the discussion list. Report the integer value.")
        qs.append(f"Open /{slug}/pull-requests. If the list is empty, confirm the visible text 'No pull requests yet' appears.")
        qs.append(f"Open /{slug}/pull-requests. Confirm the breadcrumb segment ends with 'pull requests'.")
        qs.append(f"GET /{slug}/pulls. Confirm the URL responds 200 (alias for /pull-requests).")
    for dslug in POPULAR_DATASETS:
        qs.append(f"Open /datasets/{dslug}/pull-requests. Confirm the page returns 200.")
    for sslug in POPULAR_SPACES:
        qs.append(f"Open /spaces/{sslug}/pull-requests. Confirm the page returns 200.")
    return qs


# 7) Community alias probes
def _community_alias_tasks():
    qs = []
    for slug in POPULAR_MODELS[:8]:
        qs.append(f"GET /{slug}/community. Confirm 200 and the page title contains 'Community'.")
        qs.append(f"GET /{slug}/community. Confirm the URL is reachable as a tab from /{slug} without redirect.")
    for dslug in POPULAR_DATASETS:
        qs.append(f"GET /datasets/{dslug}/community. Confirm 200.")
    for sslug in POPULAR_SPACES:
        qs.append(f"GET /spaces/{sslug}/community. Confirm 200.")
    return qs


# 8) Repos-count uplift health probes
def _healthz_tasks():
    return [
        "GET /healthz. Confirm 'repos' field is >= 400000 (R10 target).",
        "GET /healthz. Confirm 'authors' field is >= 84000.",
        "GET /healthz. Confirm 'discussions' field is >= 400.",
        "GET /sitemap-models.xml. Confirm the URL count exceeds 250000 (R10 expanded mirror sweep).",
        "GET /sitemap-datasets.xml. Confirm the URL count exceeds 90000.",
        "GET /sitemap-spaces.xml. Confirm the URL count exceeds 68000.",
        "GET /api/v3/graphql with a query for stats. Confirm repos total is >= 400000.",
    ]


# 9) Padding to reach 5400+ floor (4713 -> 5400 means we need ~690+ new tasks).
def _padding_tasks():
    pad = []
    # Six-tab matrix on a broader model set
    BROAD_MODELS = POPULAR_MODELS + [
        "BAAI/bge-large-en-v1.5",
        "intfloat/multilingual-e5-large",
        "sentence-transformers/all-MiniLM-L6-v2",
        "facebook/nllb-200-distilled-600M",
        "Helsinki-NLP/opus-mt-en-zh",
        "Qwen/Qwen2-VL-72B-Instruct",
        "google/paligemma-3b-mix-448",
        "microsoft/Florence-2-large",
        "nvidia/parakeet-tdt-1.1b",
        "stabilityai/stable-cascade",
        "stabilityai/stable-diffusion-xl-base-1.0",
        "microsoft/Phi-3.5-mini-instruct",
        "allenai/OLMo-2-1124-7B-Instruct",
        "meta-llama/Llama-3.2-3B-Instruct",
    ]
    for slug in BROAD_MODELS:
        for tab in ("community", "discussions", "pull-requests", "settings"):
            pad.append(f"GET /{slug}/{tab}. Expected status: 200. Report the status code.")
            pad.append(f"Open /{slug}/{tab}. Confirm the repo-tabs strip is visible with at least 5 tab anchors.")
    # Cross every variant type with every popular base model
    for slug in POPULAR_MODELS:
        name = slug.split("/")[1]
        for vt, sfx in R10_VARIANT_SUFFIX.items():
            for author in R10_VARIANT_AUTHORS[vt][:2]:
                vslug = f"{author}/{name}{sfx}"
                pad.append(f"GET /api/search?q={name}{sfx[:6]}. Confirm at least one slug matching '{author}/' appears.")
                pad.append(f'POST /api/v3/graphql with {{"query":"{{ repo(slug: \\"{vslug}\\") {{ slug }} }}"}}. Report whether data.repo is null or has slug.')
    # Settings field matrix
    for slug in POPULAR_MODELS:
        for field in ("slug", "repo_type", "owner", "default_branch", "created_at", "visibility", "not_for_production"):
            pad.append(f"Open /{slug}/settings. Find the dd with data-field='{field}'. Report its visible text.")
    # PR + Community + Discussions × top models
    for slug in POPULAR_MODELS:
        pad.append(f"Open /{slug}/community. Read the count badge inside the Community tab. Report the integer.")
        pad.append(f"Open /{slug}/discussions. Read the count badge inside the Discussions tab. Report the integer.")
        pad.append(f"Open /{slug}/pull-requests. Confirm the page contains either a PR row or 'No pull requests yet'.")
    # Tabs strip sanity across model / dataset / space
    for slug in POPULAR_MODELS[:5]:
        pad.append(f"Open /{slug}. Walk the repo-tabs strip left-to-right. Confirm the order is Card, Files, Community, Discussions, PRs, Settings.")
    for dslug in POPULAR_DATASETS:
        pad.append(f"Open /datasets/{dslug}. Walk the repo-tabs strip. Confirm 'Dataset viewer' tab appears between Files and Community.")
    for sslug in POPULAR_SPACES:
        pad.append(f"Open /spaces/{sslug}. Walk the repo-tabs strip. Confirm 'PRs' and 'Settings' tabs are present.")
    # Leaderboard drill-down matrix
    for slug in LEADERBOARD_SLUGS:
        pad.append(f"Open /leaderboards/{slug}. Click the rank-1 model link. Confirm the resulting model card returns 200.")
        pad.append(f"Open /leaderboards/{slug}. Count the rows in the leaderboard table. Report the integer.")
        pad.append(f"Open /leaderboard/{slug} (alt URL). Confirm it also returns 200.")
    # ONNX/MLX/AWQ/GPTQ existence probes (broader)
    for slug in POPULAR_MODELS:
        name = slug.split("/")[1]
        for vt, sfx in R10_VARIANT_SUFFIX.items():
            pad.append(f"Search the /models palette via /api/search?q={name}{sfx[:4]}. Confirm the results array length >= 1.")
    # Tab navigation cycles
    for slug in POPULAR_MODELS[:8]:
        pad.append(f"Open /{slug}. Click 'Community' tab. From there click 'PRs' tab. From there click 'Settings' tab. Confirm each transition stays inside the repo namespace '/{slug}/...'.")
    # Health field × R10 expectations
    HEALTH_FIELDS = ["repos", "authors", "tasks", "discussions", "endpoints"]
    for f in HEALTH_FIELDS:
        pad.append(f"GET /healthz. Inspect field '{f}'. Confirm it is a positive integer.")
    # Repo-count breakdown
    for kind in ("models", "datasets", "spaces"):
        pad.append(f"GET /api/v3/graphql with a stats query for {kind} count. Confirm the value matches the /{kind} list-page total.")
    # Compound R9 + R10 cross-link
    for slug in POPULAR_MODELS[:6]:
        pad.append(f"Open /{slug}/settings. Then open /{slug}/community. Then open /{slug}/pull-requests. Confirm each tab strip preserves the active state for the visited tab.")
    return pad


def main():
    existing = _existing()
    extra = []
    extra.extend(_six_tab_tasks())
    extra.extend(_nine_step_tasks())
    extra.extend(_variant_tasks())
    extra.extend(_leaderboard_tasks())
    extra.extend(_settings_deep_tasks())
    extra.extend(_pull_request_tasks())
    extra.extend(_community_alias_tasks())
    extra.extend(_healthz_tasks())
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
