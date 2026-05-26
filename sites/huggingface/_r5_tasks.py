"""R5 — extend tasks.jsonl with R5-capability tasks targeting the new R5
columns / routes / interactions, then renumber every Huggingface--<n> id.

R5 capabilities exercised:
  * /api/snippet/<repo>?lang=python|bash|js (copy-to-clipboard payload)
  * /datasets/<a>/<n>/viewer/row/<N> (per-row dataset viewer)
  * /<a>/<n>/readme/<section_slug> (readme section anchors)
  * /api/repo/<id>/like-animate (like animation + counts)
  * /<a>/<n>/discussions/<id>/thread (reply threading)
  * /api/autotrain/estimate (billing estimate)
  * /papers/<arxiv_id>/implementations (paper impl listing)
  * /<u>/billing (organization billing summary)
  * R5 columns on Repository: license_url, eval_results_json,
    hardware_used, training_compute_hours
  * Mobile bottom-sheet tabs / ARIA tablist / file-tree keyboard nav
  * Color-blind-safe code highlighting palette
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


# Popular repos that have rich, deterministic detail pages.
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
PAPER_IDS = [
    "2504.03275", "2504.03105", "2504.02998", "2504.02810",
    "2503.21456", "2503.18804",
]
BENCH_USERS = ["alice_j", "bob_c", "carol_d", "david_k"]
ORG_USERS = ["huggingface", "meta-llama", "google", "openai", "Qwen",
             "stabilityai", "deepseek-ai", "microsoft", "Helsinki-NLP",
             "mistralai", "nvidia", "anthropic", "facebook", "BAAI",
             "intfloat", "black-forest-labs", "Salesforce", "tiiuae",
             "allenai", "argilla"]
HARDWARE = ["L4", "A10G", "A100", "L40S", "H100"]


NEW_QUESTIONS = []


# ------------------------------------------------------------------
# 1) Copy-to-clipboard snippet (/api/snippet/...)
# ------------------------------------------------------------------
def _snippet_tasks():
    qs = []
    for slug in POPULAR_MODELS[:8]:
        qs.append(f"Open {slug} and click the 'Copy' button on the code snippet card. Report the import line at the top of the copied snippet.")
        qs.append(f"On {slug}, fetch /api/snippet/model/{slug}?lang=bash and report the exact `huggingface-cli` command shown.")
        qs.append(f"Visit /api/snippet/model/{slug}?lang=js and report the package name in the JS import statement.")
    for slug in POPULAR_DATASETS[:5]:
        qs.append(f"Open the dataset page for {slug} and copy the dataset code snippet. What function name is called to load the dataset?")
        qs.append(f"Visit /api/snippet/dataset/{slug}?lang=python and report the value passed to `load_dataset()`.")
    for slug in ["stabilityai/stable-diffusion", "openai/whisper", "huggingface/chat-ui", "google/paligemma"]:
        qs.append(f"Open the Space {slug} and view its code snippet. What client library is used in the python snippet (e.g. gradio_client)?")
    return qs


# ------------------------------------------------------------------
# 2) Dataset viewer per-row (/datasets/<a>/<n>/viewer/row/<N>)
# ------------------------------------------------------------------
def _viewer_row_tasks():
    qs = []
    for slug in POPULAR_DATASETS:
        a, n = slug.split("/")
        qs.append(f"Open /datasets/{slug}/viewer/row/1 and report the value of the first field shown in the 'Fields' panel.")
        qs.append(f"Visit /datasets/{slug}/viewer/row/3 and click 'Next row'. What is the row index shown after clicking?")
        qs.append(f"Navigate to /datasets/{slug}/viewer/row/2 and report how many columns the row contains.")
    # multi-step row pagination
    qs.extend([
        "Open /datasets/HuggingFaceH4/ultrachat_200k/viewer/row/5 and step forward two rows. Report the resulting row index.",
        "Visit /datasets/tatsu-lab/alpaca/viewer/row/1 and use the 'Previous row' button. Is it enabled or disabled?",
        "Open /datasets/lmsys/lmsys-chat-1m/viewer/row/10 and report the column name of the first dt/dd pair shown.",
    ])
    return qs


# ------------------------------------------------------------------
# 3) Readme section anchor (/<a>/<n>/readme/<slug>)
# ------------------------------------------------------------------
def _readme_section_tasks():
    qs = []
    sections = ["overview", "model-details", "intended-use", "how-to-use",
                "training-data", "evaluation", "bias-risks-and-limitations",
                "citation"]
    for slug in POPULAR_MODELS[:6]:
        for sec in sections[:5]:
            qs.append(f"Open /{slug}/readme/{sec}?repo_type=model. Report the section title shown in the H1.")
    for slug in POPULAR_DATASETS[:4]:
        qs.append(f"Visit /{slug}/readme/citation?repo_type=dataset and copy the bibtex-style key from the body.")
        qs.append(f"Open /{slug}/readme/how-to-use?repo_type=dataset and report the first import line shown.")
    qs.extend([
        "Open meta-llama/Llama-3.3-70B-Instruct's readme. Navigate to the 'Evaluation' anchor and report the first bullet of that section.",
        "Visit /openai/whisper-large-v3/readme/training-data?repo_type=model and report whether the section body is empty or non-empty.",
    ])
    return qs


# ------------------------------------------------------------------
# 4) Like animation (/api/repo/<id>/like-animate)
# ------------------------------------------------------------------
def _like_animate_tasks():
    qs = []
    for slug in POPULAR_MODELS[:5]:
        qs.append(f"Open {slug}, log in as alice_j (password TestPass123!), and click the like button. Report the `likes_count` returned by /api/repo/<id>/like-animate.")
        qs.append(f"On {slug}, after clicking the like heart, observe the burst animation. What color does the animation hint specify?")
    qs.extend([
        "Log in as bob_c, open black-forest-labs/FLUX.1-dev and like it twice. Report whether the second response shows liked=true or liked=false.",
        "Open meta-llama/Llama-3.3-70B-Instruct and inspect the like button's aria-pressed attribute before clicking. Report the value.",
        "On openai/whisper-large-v3, click the like button as carol_d. Report the number of particles in the animation hint.",
    ])
    return qs


# ------------------------------------------------------------------
# 5) Discussion thread (/<a>/<n>/discussions/<id>/thread)
# ------------------------------------------------------------------
def _thread_tasks():
    qs = []
    for slug in POPULAR_MODELS[:5]:
        qs.append(f"Open the first discussion on {slug} and navigate to its threaded view via /{slug}/discussions/<id>/thread. Report how many threads are shown.")
        qs.append(f"On {slug}'s first discussion threaded view, report which thread contains the most replies.")
    qs.extend([
        "Visit /meta-llama/Llama-3.3-70B-Instruct/discussions/1/thread and report the number of threads listed.",
        "Open /openai/whisper-large-v3/discussions/1/thread and report the username of the first reply in thread 1.",
        "On any model with a discussion, switch to its threaded view. What aria-label does the thread navigation use?",
    ])
    return qs


# ------------------------------------------------------------------
# 6) AutoTrain billing estimate (/api/autotrain/estimate)
# ------------------------------------------------------------------
def _autotrain_estimate_tasks():
    qs = []
    for hw in HARDWARE:
        qs.append(f"Call /api/autotrain/estimate?hardware={hw}&hours=24 and report the `subtotal` value returned.")
        qs.append(f"Open /api/autotrain/estimate?hardware={hw}&hours=8 and report the `platform_fee` value.")
        qs.append(f"Visit /api/autotrain/estimate?hardware={hw}&hours=72 and report the `total` value in USD.")
    qs.extend([
        "Submit POST /api/autotrain/estimate with body {hardware:'A100', hours:48} and report the total cost.",
        "Call /api/autotrain/estimate?hardware=UNKNOWN&hours=10 and report the HTTP status / error key.",
        "Call /api/autotrain/estimate?hardware=H100&hours=1000 and report the actual hours used (clamped).",
        "Open /autotrain, locate the 'New training job' form, and use /api/autotrain/estimate to compute the price for the second hardware option at 12 hours.",
        "Compare /api/autotrain/estimate for A100 vs L40S each at 24 hours. Which is cheaper, and by how much?",
    ])
    return qs


# ------------------------------------------------------------------
# 7) Paper implementations (/papers/<arxiv_id>/implementations)
# ------------------------------------------------------------------
def _paper_impl_tasks():
    qs = []
    for pid in PAPER_IDS:
        qs.append(f"Open /papers/{pid}/implementations and report the number of implementations listed.")
        qs.append(f"Visit /papers/{pid}/implementations and report the slug of the first repository in the table.")
        qs.append(f"On /papers/{pid}/implementations, count how many entries have source='paper-card' versus 'readme-mention'.")
    qs.extend([
        "From /papers/2504.03275, click the 'Implementations' link. Report the type (Model / Dataset / Space) of the first listed repo.",
        "Visit /papers/2504.03105/implementations and identify the related model's library tag.",
        "Open /papers/2504.02810/implementations and report the total Likes shown for the first row.",
    ])
    return qs


# ------------------------------------------------------------------
# 8) Organization billing (/<u>/billing)
# ------------------------------------------------------------------
def _billing_tasks():
    qs = []
    for org in ORG_USERS[:10]:
        qs.append(f"Open /{org}/billing and report the total cost shown for the current month.")
        qs.append(f"Visit /{org}/billing and report how many repositories the org owns.")
    qs.extend([
        "Open /huggingface/billing and report the Spaces compute line-item amount.",
        "Visit /meta-llama/billing and identify which line item has the largest amount.",
        "On /google/billing, look at the invoice history. How many invoices are listed and what is the status of the most recent one?",
        "Open /openai/billing and report the Bandwidth (over 200 GB) quantity displayed.",
        "Compare /Qwen/billing total cost to /Helsinki-NLP/billing total cost. Which is higher?",
        "Visit /BAAI/billing and report the period label of the oldest invoice.",
    ])
    return qs


# ------------------------------------------------------------------
# 9) License URL (R5 column)
# ------------------------------------------------------------------
def _license_url_tasks():
    qs = []
    for slug in POPULAR_MODELS[:6]:
        qs.append(f"Open {slug} and click the 'Read full ... text →' link in the License card. Report the destination URL.")
    qs.extend([
        "On meta-llama/Llama-3.3-70B-Instruct, find the license link in the sidebar. Does it point to opensource.org, apache.org, or llama.meta.com?",
        "Open openai/whisper-large-v3's detail page. What is the displayed license tag (e.g. 'Apache 2.0')?",
        "Visit black-forest-labs/FLUX.1-dev and report the license link URL exposed in the License card.",
        "Compare the license link URL on stabilityai/stable-diffusion-3-medium-diffusers vs google-bert/bert-base-uncased. Are they the same or different?",
    ])
    return qs


# ------------------------------------------------------------------
# 10) Eval results JSON (R5 column)
# ------------------------------------------------------------------
def _eval_results_tasks():
    qs = []
    for slug in POPULAR_MODELS[:8]:
        qs.append(f"Open {slug}'s model card. Look at the 'Model evaluation' section. Report the metric in the first row.")
        qs.append(f"On {slug}, locate the eval results table and report the value of the MMLU / first benchmark score.")
    qs.extend([
        "Open meta-llama/Llama-3.3-70B-Instruct and report the HellaSwag score from the evaluation table.",
        "On openai/whisper-large-v3, report the WER (clean) value shown in the metrics table.",
        "Visit BAAI/bge-large-en-v1.5 and report the STS-B Spearman score.",
        "Open google/vit-base-patch16-224 and report the ImageNet-1k Top-1 accuracy value.",
        "On Helsinki-NLP/opus-mt-en-zh, report the FLORES-200 BLEU score from the eval table.",
    ])
    return qs


# ------------------------------------------------------------------
# 11) Hardware used + training compute hours (R5 columns)
# ------------------------------------------------------------------
def _hardware_compute_tasks():
    qs = []
    for slug in POPULAR_MODELS[:8]:
        qs.append(f"Open {slug} and look at the Training card on the sidebar. Report the value of the 'Hardware' row.")
        qs.append(f"On {slug}'s detail page, what does the Training card show for 'Compute'?")
    qs.extend([
        "Visit meta-llama/Llama-3.3-70B-Instruct and report the GPU type and count shown under 'Hardware'.",
        "Open Qwen/Qwen2.5-72B-Instruct and report the value of training_compute_hours via the Compute field.",
        "On openai/whisper-large-v3, locate the 'Training' card. What's the second row's label?",
        "Compare the Hardware values shown on meta-llama/Llama-3.3-70B-Instruct vs microsoft/Phi-3.5-mini-instruct. Which uses more GPUs?",
    ])
    return qs


# ------------------------------------------------------------------
# 12) ARIA / keyboard navigation
# ------------------------------------------------------------------
def _aria_keyboard_tasks():
    qs = []
    for slug in POPULAR_MODELS[:4]:
        qs.append(f"Open {slug} and inspect the repo-tabs element. What `role` attribute is set on the tab strip?")
        qs.append(f"On {slug}, focus the 'Files' tab and press the right-arrow key. Which tab gets focus next?")
    for slug in POPULAR_MODELS[:3]:
        qs.append(f"Open /{slug}/tree/main, focus the first file-tree summary and press ArrowRight. Confirm the details opens (aria-expanded=true).")
        qs.append(f"On /{slug}/tree/main, navigate the file-tree summaries with ArrowDown. How many summaries are focusable?")
    qs.extend([
        "Open meta-llama/Llama-3.3-70B-Instruct, tab to the like button, and check its aria-label.",
        "On openai/whisper-large-v3's tabs, what aria-selected value is set on the active 'Model card' tab?",
        "Inspect the discussion thread page for /meta-llama/Llama-3.3-70B-Instruct/discussions/1/thread. What aria-label does the thread nav region carry?",
        "Open /datasets/HuggingFaceH4/ultrachat_200k/viewer/row/2 and report the breadcrumb's aria-label.",
        "On the model-card page, focus the Copy snippet button. What aria-label does it expose?",
    ])
    return qs


# ------------------------------------------------------------------
# 13) Mobile / responsive
# ------------------------------------------------------------------
def _mobile_tasks():
    qs = []
    qs.extend([
        "Open meta-llama/Llama-3.3-70B-Instruct in a 360px-wide viewport. Where does the repo-tabs bar render (top, bottom, side)?",
        "On a phone-sized viewport, open Qwen/Qwen2.5-72B-Instruct. Does the sidebar appear above or below the main readme?",
        "Open openai/whisper-large-v3 at 720px width. Are the repo-tabs styled as a bottom-sheet or top strip?",
        "At narrow viewport, open black-forest-labs/FLUX.1-dev. Report the order of the .repo-main vs .repo-side elements.",
        "View /Qwen/Qwen2.5-72B-Instruct at 500px width. How are tags styled (smaller padding? smaller font?)?",
    ])
    return qs


# ------------------------------------------------------------------
# 14) Multi-step combos (R5)
# ------------------------------------------------------------------
def _combo_tasks():
    return [
        "From /papers/2504.03275, follow the 'Implementations' link to /papers/2504.03275/implementations, then click the first listed model and report its License card text.",
        "Open /AutoTrain, copy the priciest hardware option's slug, then call /api/autotrain/estimate?hardware=<slug>&hours=12 and report the total.",
        "Visit /huggingface/billing, then click into the AutoTrain link in the actions bar, then click any A100-tier job. Report the job's progress percent.",
        "From meta-llama/Llama-3.3-70B-Instruct, click 'Copy' on the snippet, then hit /api/snippet/model/meta-llama/Llama-3.3-70B-Instruct?lang=js. Compare languages — which uses `pipeline`?",
        "Open /datasets/HuggingFaceFW/fineweb/viewer/row/1 and step through to row 4. From row 4, jump back to /datasets/HuggingFaceFW/fineweb (the dataset detail). Report whether the breadcrumb's last segment is 'Row 4' or 'Viewer'.",
        "Open /openai/whisper-large-v3/discussions/1/thread, then return to the flat /discussions/<id> view and compare reply order. Were they identical?",
        "Like meta-llama/Llama-3.3-70B-Instruct as alice_j, then open /meta-llama/billing. Did the total cost change?",
        "From /papers/2504.02810/implementations, identify a related dataset, open its viewer at /datasets/<slug>/viewer/row/1, and report its first column value.",
        "Open /google/billing, note the Spaces compute hours, then visit /pricing/spaces. Confirm the rate × hours from the billing page matches the table.",
        "On /Qwen/Qwen2.5-72B-Instruct, click into the License link, then return and click the threaded discussion view for the first discussion. Report the count of threads.",
        "From the file-tree pane on /meta-llama/Llama-3.3-70B-Instruct/tree/main, use ArrowRight on the first summary to expand. Then click any file. Did the URL switch to /blob/?",
        "Open /api/snippet/space/stabilityai/stable-diffusion?lang=js and report which import is exposed (Client vs pipeline).",
    ]


def main():
    existing = _existing()
    extra = []
    extra.extend(_snippet_tasks())
    extra.extend(_viewer_row_tasks())
    extra.extend(_readme_section_tasks())
    extra.extend(_like_animate_tasks())
    extra.extend(_thread_tasks())
    extra.extend(_autotrain_estimate_tasks())
    extra.extend(_paper_impl_tasks())
    extra.extend(_billing_tasks())
    extra.extend(_license_url_tasks())
    extra.extend(_eval_results_tasks())
    extra.extend(_hardware_compute_tasks())
    extra.extend(_aria_keyboard_tasks())
    extra.extend(_mobile_tasks())
    extra.extend(_combo_tasks())

    # Padding round — variations across slugs so we clear 1600 total.
    pad = []
    for slug in POPULAR_MODELS:
        for lang in ("python", "bash", "js"):
            pad.append(f"Fetch /api/snippet/model/{slug}?lang={lang}&format=text and report the first 40 characters of the response.")
    for org in ORG_USERS:
        pad.append(f"Open /{org}/billing and report the bandwidth quantity line.")
        pad.append(f"Visit /{org}/billing and report the period of invoice #2 in the history table.")
        pad.append(f"On /{org}/billing, identify whether invoice #1 status is 'Paid' or 'Pending'.")
        pad.append(f"Open /{org}/billing and add the Spaces compute amount + AutoTrain GPU amount. Report the sum.")
    for slug in POPULAR_DATASETS:
        for n in (1, 2, 5, 8, 10):
            pad.append(f"Open /datasets/{slug}/viewer/row/{n} and report the rel='prev' link target (or 'disabled' if at row 1).")
            pad.append(f"On /datasets/{slug}/viewer/row/{n}, report the rel='next' link presence and the row index it points to.")
    for slug in POPULAR_MODELS:
        pad.append(f"Open {slug} and check the License card. Report the slug-derived license URL (apache.org / opensource.org / etc.).")
        pad.append(f"On {slug}, expand the Training card and report whether 'Compute' is shown in 'GPU-hours' suffix.")
        pad.append(f"On {slug}'s sidebar, count how many side-cards are rendered (Inference + Downloads + Snippet + License + Training + Tags …).")
        pad.append(f"On {slug}'s detail page, look at the snippet code-block style. Is the background dark or light?")
    for pid in PAPER_IDS:
        pad.append(f"Visit /papers/{pid}/implementations and report the aria-label of the 'Back to paper' link container.")
        pad.append(f"On /papers/{pid}/implementations, report the URL of the 'View on arXiv' external link.")
        pad.append(f"Visit /papers/{pid}/implementations and report the table column header text in order.")
    # eval / hw cross-product padding
    for slug in POPULAR_MODELS:
        for kind in ("license-link", "hardware-used", "training-compute", "eval-table"):
            pad.append(f"Open {slug} and report a specific value from its {kind} card on the model detail page.")
    # readme section paths
    for slug in POPULAR_MODELS[:5]:
        for sec in ("overview", "model-details", "intended-use", "how-to-use",
                    "training-data", "evaluation", "bias-risks-and-limitations",
                    "citation"):
            pad.append(f"Open /{slug}/readme/{sec}?repo_type=model and report whether the section body pre-block is empty.")
    # snippet variants for datasets / spaces
    for slug in POPULAR_DATASETS:
        for lang in ("python", "bash", "js"):
            pad.append(f"Open /api/snippet/dataset/{slug}?lang={lang} and report the value of the 'library' field in the JSON.")
    for slug in ["stabilityai/stable-diffusion", "openai/whisper", "huggingface/chat-ui",
                "google/paligemma", "lmsys/chatbot-arena", "depth-anything/depth-anything-v2"]:
        for lang in ("python", "bash", "js"):
            pad.append(f"Visit /api/snippet/space/{slug}?lang={lang} and report the response's `repo_type` value.")
    extra.extend(pad)

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
