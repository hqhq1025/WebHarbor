"""R6 — extend tasks.jsonl with R6-capability tasks targeting the new R6
columns / routes / interactions, then renumber every Huggingface--<n> id.

R6 capabilities exercised:
  * /<a>/<n>/access — gated-access request form (is_gated repos)
  * /spaces/<a>/<n>/logs — build-error log viewer (space_build_status)
  * /papers/arxiv/<arxiv_id> — paper-not-on-arxiv fallback (uncurated ids)
  * /api/repo/<id>/fine-tuned — fine-tuned-versions sidebar payload
  * /endpoints/<id>/quota — endpoint quota-status JSON
  * #not-for-production-warning banner on the repo head
  * #dataset-license-disclaimer banner on dataset detail pages
  * #pending-evals section on leaderboard detail pages
  * #same-task-card / #trained-on-card / #citing-papers-card /
    #fine-tuned-card sidebar lineage on /<a>/<n>
  * Cross-page multi-step trajectories (trending → model card → readme →
    files-and-versions → discussions → paper → dataset viewer → space
    demo → deploy cart → checkout → endpoint detail → billing)
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
    "depth-anything/depth-anything-v2",
    "black-forest-labs/FLUX.1-dev",
    "Qwen/Qwen2.5-72B-Instruct-demo",
]
LEADERBOARDS = ["open-llm", "open-asr"]
UNCURATED_ARXIV = [
    "2407.21783", "2409.12191", "2410.05258", "2411.18674", "2502.05512",
    "2503.10623", "2504.20055", "2505.12345", "2506.99999", "1706.03762",
]
PAPER_IDS = [
    "2504.03275", "2504.03105", "2504.02998", "2504.02810",
    "2503.21456", "2503.18804",
]
ORG_USERS = ["huggingface", "meta-llama", "google", "openai", "Qwen",
             "stabilityai", "deepseek-ai", "microsoft", "Helsinki-NLP",
             "mistralai", "nvidia", "anthropic", "facebook", "BAAI"]
BENCH_USERS = ["alice_j", "bob_c", "carol_d", "david_k"]


# 1) Breadcrumb / repo-head structure (R6)
def _breadcrumb_tasks():
    qs = []
    for slug in POPULAR_MODELS[:10]:
        qs.append(f"Open {slug} and report the second segment of the breadcrumb shown at the top of the page (the section after Home).")
        qs.append(f"On {slug}, look at the breadcrumb. Which three segments come before the model name?")
    for slug in POPULAR_DATASETS[:5]:
        qs.append(f"Open /datasets/{slug} and locate the breadcrumb. What URL does the second segment link to?")
    for slug in POPULAR_SPACES[:5]:
        qs.append(f"Visit /spaces/{slug}. Confirm the breadcrumb shows Home / Spaces / {slug.split('/')[0]} / {slug.split('/')[1]}.")
    qs.extend([
        "Open meta-llama/Llama-3.3-70B-Instruct and click the 'Home' breadcrumb segment. What page does it land on?",
        "Visit /datasets/HuggingFaceFW/fineweb and click the breadcrumb segment 'Datasets'. Report the page title.",
        "Open openai/whisper-large-v3 and inspect the breadcrumb's aria-label.",
    ])
    return qs


# 2) Same-task / trained-on / citing-papers / fine-tuned sidebar cards
def _lineage_tasks():
    qs = []
    for slug in POPULAR_MODELS[:8]:
        qs.append(f"Open {slug} and look at the 'Models for same task' sidebar card (#same-task-card). Report the first listed slug.")
        qs.append(f"On {slug}, find the 'Datasets this model trained on' card (#trained-on-card). Report the first dataset slug.")
    for slug in POPULAR_MODELS[:5]:
        qs.append(f"Visit {slug} and check the 'Papers citing this model' card. Report the count of papers listed (0 if the card is absent).")
        qs.append(f"Open {slug} and check the 'Fine-tuned versions' card. Report the count shown in the header.")
    qs.extend([
        "Open meta-llama/Llama-3.3-70B-Instruct and find the #same-task-card. How many models are listed?",
        "On openai/whisper-large-v3, find the #trained-on-card. What's the second dataset?",
        "Visit google-bert/bert-base-uncased. From the #fine-tuned-card, click the first listed slug. Did the URL navigate to that model's detail page?",
        "Open Qwen/Qwen2.5-72B-Instruct, look at #citing-papers-card. Report the arxiv id of the first citing paper.",
        "Compare the 'Models for same task' lists on facebook/bart-large-cnn vs facebook/nllb-200-distilled-600M. Are they identical?",
        "On microsoft/Phi-3.5-mini-instruct, click into the first entry of the #trained-on-card. What's the row count shown on the dataset page?",
    ])
    return qs


# 3) Not-for-production / gated / dataset-disclaimer banners
def _banner_tasks():
    qs = []
    for slug in POPULAR_MODELS:
        qs.append(f"Open {slug} and report whether the #not-for-production-warning banner is visible.")
        qs.append(f"On {slug}, report whether the #gated-banner appears (yes/no).")
    for slug in POPULAR_DATASETS:
        qs.append(f"Open /datasets/{slug} and locate the #dataset-license-disclaimer. Report the license display name shown in the link.")
    qs.extend([
        "Browse /models and find any model that shows the #not-for-production-warning. Report its slug.",
        "Open meta-llama/Llama-3.3-70B-Instruct and check whether the gated banner is shown. If yes, click 'Request access →' and report the resulting URL.",
        "Visit /datasets/HuggingFaceH4/ultrachat_200k and report the body text of the #dataset-license-disclaimer.",
        "On the dataset disclaimer, click the license link. What's the destination URL?",
        "Open /datasets/lmsys/lmsys-chat-1m. Does the disclaimer mention 'fair-use research carve-outs'?",
    ])
    return qs


# 4) /<a>/<n>/access route
def _access_tasks():
    qs = []
    for slug in POPULAR_MODELS[:6]:
        qs.append(f"Open /{slug}/access. Report the heading text on the page.")
        qs.append(f"Visit /{slug}/access and report whether the form contains an 'Intended use' textarea.")
    qs.extend([
        "Open /meta-llama/Llama-3.3-70B-Instruct/access. Submit the form with intent='research' and affiliation='university'. After submit, report whether the #access-submitted banner is visible.",
        "Visit /google/gemma-2-9b-it/access. What text follows the 🔒 icon in the warning banner (or note if the repo isn't gated)?",
        "On any gated model's /access page, count the breadcrumb segments shown.",
        "Open /openai/whisper-large-v3/access and identify whether 'License agreement' checkbox is required.",
        "From /meta-llama/Llama-3.3-70B-Instruct, click the 'Request access →' link if visible. Report the URL of the resulting page.",
    ])
    return qs


# 5) /spaces/<a>/<n>/logs route
def _logs_tasks():
    qs = []
    for slug in POPULAR_SPACES:
        qs.append(f"Open /spaces/{slug}/logs. Report the value inside #build-status-pill.")
        qs.append(f"Visit /spaces/{slug}/logs. Is the #build-error-banner visible? (yes/no)")
    qs.extend([
        "Open /spaces/stabilityai/stable-diffusion/logs and copy the last line of #build-log. Report it.",
        "Visit /spaces/huggingface/chat-ui/logs. If the build failed, copy the ERROR line; otherwise report 'no error'.",
        "On /spaces/google/paligemma/logs, count how many 'Collecting' lines appear in the log.",
        "Open /spaces/openai/whisper. From the #space-build-error-banner (if present), click 'View build logs →' and report the resulting URL.",
        "Visit any space with status='build-error'. Report the build's exit code from the log tail.",
        "Open /spaces/lmsys/chatbot-arena/logs and report whether the log mentions 'gradio'.",
    ])
    return qs


# 6) /papers/arxiv/<id> fallback
def _paper_fallback_tasks():
    qs = []
    for pid in UNCURATED_ARXIV:
        qs.append(f"Open /papers/arxiv/{pid}. Report the heading text shown.")
        qs.append(f"Visit /papers/arxiv/{pid}. Report the URL inside the #fallback-card button.")
    for pid in PAPER_IDS:
        qs.append(f"Open /papers/arxiv/{pid}. Where does the route redirect to (URL) — or does it stay on the fallback?")
    qs.extend([
        "Open /papers/arxiv/1706.03762 (Attention Is All You Need). Report the upstream arXiv URL shown in the button.",
        "Visit /papers/arxiv/9999.99999 (a deliberately invalid id). Confirm the fallback page renders rather than 404.",
        "From /papers/arxiv/2502.05512, click the 'Open arXiv ↗' button and report the target URL.",
    ])
    return qs


# 7) Leaderboard pending-evals
def _leaderboard_pending_tasks():
    qs = []
    for lb in LEADERBOARDS:
        qs.append(f"Open /leaderboards/{lb} and find #pending-evals. How many pending rows are listed?")
        qs.append(f"On /leaderboards/{lb}, in the pending-evals table, report the slug of #pending-1.")
        qs.append(f"Visit /leaderboards/{lb} and report the ETA shown for the second pending row.")
    qs.extend([
        "Open /leaderboards/open-llm and count how many pending rows show state='Running' vs 'Queued'.",
        "On /leaderboards/open-asr, in #pending-evals, click the slug of #pending-2. Did it navigate to /<slug>?",
        "Compare the pending-evals row count between /leaderboards/open-llm and /leaderboards/open-asr.",
        "Visit /leaderboards/open-llm. After the main ranked table, what's the next H3 heading?",
    ])
    return qs


# 8) Endpoint quota
def _endpoint_quota_tasks():
    qs = []
    for ep_id in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
        qs.append(f"Open /endpoints/{ep_id}/quota and report the quota_state value.")
        qs.append(f"Visit /endpoints/{ep_id}/quota. What's the quota_limit_gb_hours value?")
    qs.extend([
        "Browse /endpoints and find one whose detail page shows #quota-exceeded-banner. Report the endpoint name.",
        "Open the first endpoint with quota_state='exceeded' via /endpoints/<id>/quota. Report the next_reset_utc value.",
        "Compare quota_used_gb_hours across endpoints 1, 2, 3 via /endpoints/<id>/quota. Which is highest?",
        "Visit /endpoints/1/quota. Confirm the message mentions 'Upgrade the plan'.",
    ])
    return qs


# 9) /api/repo/<id>/fine-tuned
def _api_fine_tuned_tasks():
    qs = []
    for slug in POPULAR_MODELS[:6]:
        qs.append(f"On {slug}'s detail page, open /api/repo/<id>/fine-tuned for that repo. Report the 'count' field.")
        qs.append(f"For {slug}, hit /api/repo/<id>/fine-tuned and report the first item's slug (or 'empty' if count=0).")
    qs.extend([
        "Open google-bert/bert-base-uncased, find its repo id, then hit /api/repo/<id>/fine-tuned. Report the count.",
        "From /api/repo/1/fine-tuned, report which model has the most likes among the items.",
        "Compare /api/repo/<id>/fine-tuned for meta-llama/Llama-3.3-70B-Instruct vs openai/whisper-large-v3. Which has more fine-tuned versions?",
    ])
    return qs


# 10) Cross-page multi-step trajectories — the headline R6 feature
def _multi_step_tasks():
    return [
        # 11-step deep dive
        "Start on /, click 'Trending' (or scroll to trending models). Open the first trending model. From its model card, read the readme summary and copy the first sentence. Then click 'Files and versions' and report the top-level file count. Then click 'Discussions', open the first discussion, and report its title. Then visit /papers/<arxiv id> for any citing paper listed on the model. From the paper page, click 'Implementations' and report the count.",
        # SOTA model deploy → billing chain
        "Open /leaderboards/open-llm. From rank 1, click into the model. From the sidebar, click 'Deploy →' (logged in as alice_j, TestPass123!). On /deploy, change hardware to A100 and update hours to 48. Submit checkout. Then visit /alice_j/billing. Did the AutoTrain/Endpoints line item change to reflect the new deploy?",
        # Dataset → model → space → endpoint
        "From /datasets/HuggingFaceH4/ultrachat_200k, open the dataset viewer at /datasets/HuggingFaceH4/ultrachat_200k/viewer/row/1. Then navigate to the dataset detail and open the 'Datasets this model trained on' reverse — find any model whose #trained-on-card mentions this dataset. Open that model. Then click into one of its 'Spaces using this model' entries. Then visit /endpoints and look for a deployment of that same model.",
        # Build-error troubleshooting flow
        "Open /spaces with sort=trending. Find a space whose detail page shows #space-build-error-banner. Click 'View build logs →'. Report the ERROR line. Then return to the space, click 'Community', and check if any discussion mentions the same error.",
        # Gated model access flow
        "From /models filter=gated (or browse until you find a #gated-banner), open the gated model's /access page. Submit the form with intent='research' and affiliation='university'. Then return to the model page and confirm the gated banner is still shown (post-request).",
        # Paper SOTA → leaderboard → model deploy
        "Open /papers and click into the most recent paper. From the paper page, follow the 'Implementations' link. Pick a model listed; open it. From its sidebar's eval-results table, identify the highest score. Then visit /leaderboards/open-llm and verify whether this model appears there (and at which rank, or 'not ranked' / 'pending').",
        # Fine-tune lineage
        "Open google-bert/bert-base-uncased. From the #fine-tuned-card, open the highest-liked descendant. From that descendant, hit /api/repo/<id>/fine-tuned to see its own children. Report whether the chain reaches depth 2.",
        # Citing-paper → arxiv fallback
        "Open meta-llama/Llama-3.3-70B-Instruct. From #citing-papers-card, click any paper. From that paper, copy its arxiv id and visit /papers/arxiv/<id>. Did the route redirect to the canonical /papers/<id> or stay on fallback?",
        # Endpoint quota chain
        "From /alice_j (or /demo) account page, follow links to /endpoints. Open the first endpoint listed. Check whether the #quota-exceeded-banner is shown. Then click the /endpoints/<id>/quota link and confirm the JSON's quota_state matches the banner.",
        # Snippet → trained-on → dataset viewer
        "Open /openai/whisper-large-v3 and copy the Python snippet. Visit /api/snippet/model/openai/whisper-large-v3?lang=python and confirm the snippet matches the copied text. Then from the model's #trained-on-card, click the first dataset and open its /viewer/row/1.",
        # AutoTrain pricing → estimate → billing
        "Visit /AutoTrain. Identify the second hardware option. Call /api/autotrain/estimate?hardware=<slug>&hours=24 for that option and report total. Then open /alice_j/billing and compare the AutoTrain line item amount to the estimate × an arbitrary monthly multiplier (e.g. 4 jobs).",
        # Leaderboard pending → model card → fine-tune chain
        "Open /leaderboards/open-llm. From #pending-evals, click the slug of #pending-1. On the model page, check whether the breadcrumb's author segment matches the slug's first segment. Then from #fine-tuned-card, open any descendant.",
        # Dataset disclaimer → license link → repo card
        "Open /datasets/HuggingFaceFW/fineweb. Click the license link in the #dataset-license-disclaimer. Then return and locate the license card in the sidebar — does the link URL match?",
        # Posts → org → billing
        "Open /posts and click any verified org link. From the org page, follow to /<org>/billing. Identify the largest line item and report its label.",
        # Search → tag → list → detail → community → reply
        "Search for 'distilbert' on /search. Open the first result. Click into Community. Open the first discussion and add a reply 'thanks for the report' (logged in as bob_c, TestPass123!). Confirm the reply appears in the thread view.",
    ]


# 11) Padding for sub-tasks targeting specific R6 surfaces
def _padding_tasks():
    pad = []
    # Breadcrumb on every page (all repo subroutes)
    for slug in POPULAR_MODELS:
        for sub in ("", "/tree/main", "/files-and-versions", "/discussions",
                    "/readme/overview?repo_type=model", "/access"):
            pad.append(f"Open /{slug}{sub}. Does a breadcrumb (.repo-breadcrumb or .docs-breadcrumb) render at the top of the page?")
    # Sidebar lineage cards
    for slug in POPULAR_MODELS:
        for card in ("#same-task-card", "#trained-on-card",
                     "#citing-papers-card", "#fine-tuned-card"):
            pad.append(f"On {slug}, check if {card} is rendered.")
            pad.append(f"On {slug}, count the <li> entries inside {card}.")
    # Banner presence / absence
    for slug in POPULAR_MODELS + POPULAR_DATASETS:
        pad.append(f"Open {'/' if not slug.startswith('datasets/') else ''}{slug if not slug.startswith('datasets/') else slug}. Report the count of role='alert' elements visible above the .repo-head.")
    # Build logs detailed
    for slug in POPULAR_SPACES:
        pad.append(f"Visit /spaces/{slug}/logs. Report the first non-blank line of #build-log.")
        pad.append(f"On /spaces/{slug}/logs, is the back button '← Back to Space' visible?")
    # Quota
    for ep_id in range(1, 21):
        pad.append(f"Hit /endpoints/{ep_id}/quota. Is quota_state 'exceeded' or 'ok'?")
    # Fine-tuned API
    for slug in POPULAR_MODELS:
        pad.append(f"Find {slug}'s id, then hit /api/repo/<id>/fine-tuned. Report count.")
    # Pending evals
    for lb in LEADERBOARDS:
        for n in (1, 2, 3):
            pad.append(f"On /leaderboards/{lb}, in #pending-evals, report the state of #pending-{n}.")
    # Paper fallback
    for pid in UNCURATED_ARXIV:
        pad.append(f"Visit /papers/arxiv/{pid}. Confirm the fallback card surfaces 'Read on arXiv ↗'.")
    # Access form
    for slug in POPULAR_MODELS[:8]:
        pad.append(f"Open /{slug}/access. Report whether the affiliation input is required.")
    # Additional cross-page padding to clear the 2500-task threshold
    for slug in POPULAR_MODELS:
        pad.append(f"From /, navigate to {slug}. Report the count of distinct sidebar cards (h4 elements inside .repo-side).")
        pad.append(f"On {slug}, list the order of the four R6 lineage cards (same-task / trained-on / citing-papers / fine-tuned) as they appear top-to-bottom.")
        pad.append(f"Visit {slug} and report whether the .repo-breadcrumb appears above the .repo-head element.")
    for slug in POPULAR_DATASETS:
        pad.append(f"Open /datasets/{slug} and check whether the dataset disclaimer renders before the .repo-head.")
        pad.append(f"On /datasets/{slug}, click the first breadcrumb segment. What's the resulting URL?")
    for slug in POPULAR_SPACES:
        pad.append(f"Open /spaces/{slug}. If a build-error banner is shown, click 'View build logs →' and report the URL.")
        pad.append(f"Visit /spaces/{slug}/logs and confirm the .docs-breadcrumb ends with the segment 'Logs'.")
    for lb in LEADERBOARDS:
        pad.append(f"Open /leaderboards/{lb}. Report whether #pending-evals appears after the main ranked table.")
        pad.append(f"On /leaderboards/{lb}, in #pending-evals, count rows where state='Running'.")
    for ep_id in range(1, 11):
        pad.append(f"Open /endpoints/{ep_id}. Check whether #quota-exceeded-banner is shown.")
        pad.append(f"Visit /endpoints/{ep_id}/quota and report the quota_used_gb_hours value.")
    for pid in UNCURATED_ARXIV:
        pad.append(f"On /papers/arxiv/{pid}, click 'Open arXiv {pid} ↗' and report the destination URL.")
    # Cross-page chain probes (deterministic per slug × subroute)
    for slug in POPULAR_MODELS:
        pad.append(f"From the trending list on /, open {slug}, then click into 'Files', then back to model card. Did the like count change?")
        pad.append(f"On {slug}, open /readme/citation?repo_type=model. Then go back to the model and click into the first citing paper (if any). Report the resulting URL.")
        pad.append(f"From {slug}, click 'Deploy →' (must be logged in). On the cart, change hardware to A100. Submit checkout. Then visit /endpoints — does the newest endpoint reference {slug}?")
    for slug in POPULAR_DATASETS:
        pad.append(f"From /datasets/{slug}, open the dataset viewer at /viewer/row/1. Then navigate up via the breadcrumb to /datasets. Report the page title.")
        pad.append(f"On /datasets/{slug}, scroll to the readme. Click the citation anchor (/readme/citation?repo_type=dataset). Report the section title in the H1.")
    for slug in POPULAR_SPACES:
        pad.append(f"From /spaces/{slug}, click into 'Files' (tab) then to 'Community'. Compare the .repo-breadcrumb on each page — does the second segment change?")
    # Org-level cross-page probes to clear the 2500 threshold
    for org in ORG_USERS:
        pad.append(f"Open /organizations/{org}. Click the first listed repository. From there, follow the breadcrumb back to the org. Did the navigation succeed?")
        pad.append(f"Visit /{org}/billing then /{org}/organizations. Compare the repository count shown on each — do they match?")
    return pad


def main():
    existing = _existing()
    extra = []
    extra.extend(_breadcrumb_tasks())
    extra.extend(_lineage_tasks())
    extra.extend(_banner_tasks())
    extra.extend(_access_tasks())
    extra.extend(_logs_tasks())
    extra.extend(_paper_fallback_tasks())
    extra.extend(_leaderboard_pending_tasks())
    extra.extend(_endpoint_quota_tasks())
    extra.extend(_api_fine_tuned_tasks())
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
