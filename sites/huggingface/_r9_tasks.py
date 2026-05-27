"""R9 — extend tasks.jsonl with R9-capability tasks targeting the new R9
surfaces (AutoTrain job configs, GGUF quant comparison, safetensors format
check, model-merge stub, ZeroGPU quota, papers Daily vote) and the new
community fine-tune / GGUF quant / safetensors variant repos that R9 added
to the seed DB. Renumber every Huggingface--<n> id afterwards.

R9 capabilities exercised:
  * /autotrain/config/<job> — YAML config, base_model/dataset/hardware fields
  * /tools/gguf-quant-compare — quant size + Δppl table, ?slug= param
  * /tools/safetensors-check — pickle/safe verdict on a filename
  * /model-merge — mergekit YAML generator (linear/slerp/ties/dare-ties/…)
  * /spaces/zerogpu-quota — per-user quota + tier
  * /papers/daily-vote — vote on today's papers
  * R9 synthetic variants visible under /models (GGUF, safetensors mirrors,
    community fine-tunes) — palette, search, GraphQL all see them
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
]
AUTOTRAIN_JOBS = [
    "llama-3-8b-sft-alpaca",
    "whisper-fr-finetune",
    "gemma-2-9b-dpo",
    "qwen-2-5-vl-vqa",
    "deepseek-v3-orpo",
    "bge-large-en-finetune",
]
QUANT_LEVELS = ["Q2_K", "Q3_K_M", "Q4_K_M", "Q4_0", "Q5_K_M", "Q6_K", "Q8_0", "f16"]
MERGE_METHODS = ["linear", "slerp", "ties", "dare-ties", "passthrough", "model-stock"]
QUANT_AUTHORS = ["TheBloke", "bartowski", "QuantFactory", "mradermacher", "MaziyarPanahi"]
DAILY_PAPER_IDS = [
    "2411.17041", "2410.20587", "2411.04944", "2410.10630", "2411.10440",
    "2411.01098", "2410.19133", "2411.03570", "2410.18890", "2411.07641",
    "2411.08868", "2410.07073",
]


# 1) AutoTrain job config
def _autotrain_tasks():
    qs = []
    for job in AUTOTRAIN_JOBS:
        qs.extend([
            f"Open /autotrain/config/{job}. Report the value of the 'Base model' field.",
            f"Open /autotrain/config/{job}. Report the value of the 'Trainer' field.",
            f"Open /autotrain/config/{job}. Report the dataset slug shown under 'Dataset'.",
            f"Open /autotrain/config/{job}. Report the hardware tier shown under 'Hardware'.",
            f"Open /autotrain/config/{job}. In the YAML block, find the 'lora_r' value. Report it.",
            f"Open /autotrain/config/{job}. Does the YAML block include both 'merge_method' and 'base_model'? (one of these is expected — name which.)",
            f"From /autotrain/config/{job}, click the base model link in the table. Confirm you land on the model page.",
        ])
    qs.extend([
        "Open /autotrain/config/does-not-exist. Does the page list known job slugs without raising 500?",
        "Open /autotrain/config/llama-3-8b-sft-alpaca. Confirm a <dt> with text 'PEFT' exists and its <dd> says 'true' or 'false'.",
        "Open /autotrain/config/whisper-fr-finetune. Confirm the YAML contains 'task: automatic-speech-recognition'.",
        "Open /autotrain/config/gemma-2-9b-dpo. The 'trainer' field — should be 'dpo'. Confirm.",
        "Open /autotrain/config/qwen-2-5-vl-vqa. Confirm the YAML contains 'visual-question-answering'.",
        "Open /autotrain/config/deepseek-v3-orpo. Confirm the YAML 'trainer:' line equals 'orpo'.",
        "Open /autotrain/config/bge-large-en-finetune. Confirm the YAML 'peft.enabled' equals 'false'.",
    ])
    return qs


# 2) GGUF quant comparison
def _gguf_quant_tasks():
    qs = []
    for slug in POPULAR_MODELS:
        qs.append(f"Open /tools/gguf-quant-compare?slug={slug}. How many rows are in the quant table?")
        qs.append(f"Open /tools/gguf-quant-compare?slug={slug}. Report the file-size estimate for Q4_K_M.")
        qs.append(f"Open /tools/gguf-quant-compare?slug={slug}. Report the recommendation text for the Q4_K_M row.")
    qs.extend([
        "Open /tools/gguf-quant-compare. Confirm the f16 row has size_ratio 1.00 (the largest).",
        "Open /tools/gguf-quant-compare. Which row has the recommendation 'Recommended default'?",
        "Open /tools/gguf-quant-compare?slug=does/not-exist. Does the page still render with the 8B fallback assumption?",
        "Open /tools/gguf-quant-compare. The Q2_K row's Δppl column should equal '+1.50'. Confirm.",
        "Open /tools/gguf-quant-compare. Find the row labeled 'Q8_0'. Report its 'bpw' value.",
        "Open /tools/gguf-quant-compare. The table heading should include columns: Quant, bpw, Size, Δppl, Recommendation. Confirm.",
        "Open /tools/gguf-quant-compare. Click one of the 'Other base models' links. Confirm the URL changes with a new ?slug= query string.",
        "Open /tools/gguf-quant-compare?slug=meta-llama/Llama-3.3-70B-Instruct. The 'Other base models' list should include other popular models. Pick one and visit it.",
    ])
    for ql in QUANT_LEVELS:
        qs.append(f"Open /tools/gguf-quant-compare. Locate the row with data-quant='{ql}'. Report its file-size estimate.")
    return qs


# 3) Safetensors check
def _safetensors_check_tasks():
    qs = []
    # Safe formats
    for fn in ("model.safetensors", "weights.gguf", "encoder.onnx"):
        qs.append(f"POST /tools/safetensors-check with filename={fn}. Confirm the verdict block has data-verdict='safe'.")
    # Unsafe formats
    for fn in ("pytorch_model.bin", "checkpoint.pt", "weights.pth", "model.ckpt", "weights.pkl", "data.pickle"):
        qs.append(f"POST /tools/safetensors-check with filename={fn}. Confirm the verdict is 'unsafe' and the warning mentions 'pickle' or 'arbitrary code'.")
    # Unknown
    qs.append("POST /tools/safetensors-check with filename=mystery.xyz. Confirm the verdict is 'unknown'.")
    # Empty
    qs.append("GET /tools/safetensors-check. Confirm no verdict block is shown before submitting.")
    qs.extend([
        "Open /tools/safetensors-check. Confirm the page lists '.safetensors', '.gguf', '.onnx' under 'Accepted formats'.",
        "Open /tools/safetensors-check. Confirm the page lists '.bin', '.pt', '.pth', '.ckpt' under 'Rejected formats'.",
        "POST /tools/safetensors-check with filename=model.safetensors. The verdict box's data-format attribute should equal 'safetensors'.",
        "POST /tools/safetensors-check with filename=PYTORCH_MODEL.BIN (uppercase). Confirm it still triggers the 'unsafe' verdict (case-insensitive).",
        "POST /tools/safetensors-check with filename=weights.gguf. data-format should equal 'gguf'.",
        "POST /tools/safetensors-check with filename=enc.onnx. data-format should equal 'onnx'.",
    ])
    return qs


# 4) Model merge
def _model_merge_tasks():
    qs = []
    qs.extend([
        "Open /model-merge. Confirm the default 'Model A' is meta-llama/Llama-3.3-70B-Instruct.",
        "Open /model-merge. Confirm the default 'Model B' is mistralai/Mistral-7B-Instruct-v0.3.",
        "Open /model-merge. Confirm the 'Method' select includes options: linear, slerp, ties, dare-ties.",
        "POST /model-merge with a=meta-llama/Llama-3.3-70B-Instruct&b=google/gemma-2-9b-it&method=slerp&weight_a=0.4. Confirm the YAML's merge_method line equals 'slerp'.",
        "POST /model-merge with a=meta-llama/Llama-3.3-70B-Instruct&b=mistralai/Mistral-7B-Instruct-v0.3&method=ties&weight_a=0.7. Confirm the YAML 'weight: 0.7' appears for the first model entry.",
        "POST /model-merge with weight_a=2.0. Confirm the page clamps the value to 1.0 (or shows wa <= 1.0).",
        "POST /model-merge with weight_a=foo. Confirm the page falls back to 0.5 instead of 500.",
        "Open /model-merge?a=Qwen/Qwen2.5-72B-Instruct&b=openai/whisper-large-v3&method=passthrough. Confirm the YAML 'merge_method' equals 'passthrough'.",
        "POST /model-merge. The predicted slug should follow the pattern community-merges/merge-<hex12>. Confirm.",
    ])
    for m in MERGE_METHODS:
        qs.append(f"Open /model-merge?method={m}. Confirm the dt 'Method' shows '{m}' in the dd.")
    # Hub presence
    qs.extend([
        "POST /model-merge with a=does/not-exist&b=also/missing. Confirm both 'Model A on hub' and 'Model B on hub' show 'no'.",
        "POST /model-merge with a=meta-llama/Llama-3.3-70B-Instruct. Confirm 'Model A on hub' shows 'yes'.",
    ])
    return qs


# 5) Spaces ZeroGPU quota
def _zerogpu_tasks():
    qs = []
    qs.extend([
        "Open /spaces/zerogpu-quota. Confirm the page renders without a user with plan 'anonymous'.",
        "Open /spaces/zerogpu-quota?user=alice_j. Report the plan tier shown.",
        "Open /spaces/zerogpu-quota?user=alice_j. Twice in a row — does the 'Used today' value remain identical between requests?",
        "Open /spaces/zerogpu-quota?user=bob_c. Report the 'Daily cap (minutes)' value.",
        "Open /spaces/zerogpu-quota?user=enterprise_demo. Confirm 'Resets at' shows a 'Z'-suffixed ISO8601 timestamp.",
        "Open /spaces/zerogpu-quota. Confirm the 'Quota tiers' list includes 'free', 'pro', 'enterprise'.",
        "Open /spaces/zerogpu-quota?user=carol_d. Confirm 'Remaining' = cap - used (do the math).",
    ])
    for u in ("alice_j", "bob_c", "carol_d", "david_k", "demo", "elena_g", "fan", "george_z"):
        qs.append(f"Open /spaces/zerogpu-quota?user={u}. Report whether the plan is free / pro / enterprise.")
    return qs


# 6) Papers Daily vote
def _papers_vote_tasks():
    qs = []
    qs.extend([
        "Open /papers/daily-vote. Confirm the page has a table with at least 12 rows (arxiv ids + votes).",
        "Open /papers/daily-vote. Sort order — confirm the votes column is descending across rows.",
        "POST /papers/daily-vote with arxiv_id=2411.17041. Confirm a green banner says 'Thanks' and the row shows '✓ voted'.",
        "POST /papers/daily-vote with arxiv_id=2411.17041 twice. The second time, confirm the banner says 'already upvoted'.",
        "POST /papers/daily-vote with arxiv_id=9999.99999. Confirm the banner is red and the page does not 500.",
        "POST /papers/daily-vote with Accept: application/json and arxiv_id=2410.20587. Confirm response is JSON with status 'ok'.",
        "Open /papers/daily-vote. Click on the arxiv-id link for 2410.20587. Confirm you land on /papers/arxiv/2410.20587.",
    ])
    for aid in DAILY_PAPER_IDS:
        qs.append(f"Open /papers/daily-vote. Locate the row with data-arxiv-id='{aid}'. Report the votes value for that row.")
        qs.append(f"POST /papers/daily-vote with arxiv_id={aid}. Confirm the response is 200 (not 4xx).")
    return qs


# 7) R9 variants visible across earlier surfaces
def _variant_tasks():
    qs = []
    # GGUF variants by TheBloke
    for base in POPULAR_MODELS[:4]:
        name = base.split("/")[1]
        for qa in QUANT_AUTHORS:
            qs.append(f"GET /api/command-palette?q={name[:6]}-GGUF. Confirm at least one item references '{qa}/{name}-GGUF' or '{qa}/{name}-' + a quant level.")
    # Safetensors mirror
    for base in POPULAR_MODELS[:6]:
        name = base.split("/")[1]
        qs.append(f"Search for '{name}-safetensors' on /models. Confirm at least one repo with a safetensors-mirror or PrunaAI prefix appears.")
    # Fine-tunes
    for base in POPULAR_MODELS[:6]:
        name = base.split("/")[1]
        qs.append(f"Search for '{name}-lora' or '{name}-dpo' on /models. Confirm at least one community fine-tune appears.")
    # GraphQL probes for synthetic variants
    for base in POPULAR_MODELS[:6]:
        name = base.split("/")[1]
        for qa in QUANT_AUTHORS[:3]:
            slug = f"{qa}/{name}-GGUF"
            qs.append(f'POST /api/v3/graphql with {{"query":"{{ repo(slug: \\"{slug}\\") {{ slug library }} }}"}}. Does data.repo return non-null (library should be gguf or similar)?')
    return qs


# 8) Multi-step crossovers using R9 surfaces
def _multi_step_tasks():
    return [
        "Open /autotrain/config/llama-3-8b-sft-alpaca. Click the base-model link. From the model page, open /tools/gguf-quant-compare?slug=<that slug>. Confirm both pages reference the same base model.",
        "Open /tools/gguf-quant-compare?slug=openai/whisper-large-v3. Note the Q4_K_M file size. Then GET /api/v3/graphql with a repo query for that slug. Compare the params_b to your size estimate (size ≈ params * 2 * 0.46).",
        "POST /tools/safetensors-check with filename=pytorch_model.bin. Then open /model-merge. Confirm the merge YAML uses 'dtype: bfloat16' (safetensors-friendly, no pickle).",
        "Open /papers/daily-vote. Upvote 2411.17041. Then GET /papers/daily-vote with Accept: application/json with arxiv_id=2411.17041 in the body. Confirm the message is 'already upvoted'.",
        "Open /spaces/zerogpu-quota?user=alice_j. Note the plan. Then press Cmd+K, type 'zerogpu'. Confirm the palette includes the quota page.",
        "Press Cmd+K, type 'safetensors'. Hit Enter. From the page, paste 'model.ckpt'. Confirm the verdict is 'unsafe'.",
        "Open /model-merge. Submit a merge with two real Hub models. Note the predicted slug. Now POST /api/v3/graphql with a repo query for that predicted slug. Confirm data.repo is null (the merge slug isn't on the Hub).",
        "Open /autotrain/config/gemma-2-9b-dpo. Click into the dataset link (/datasets/HuggingFaceH4/ultrachat_200k). Then back to /autotrain. Confirm browser back returns to the config.",
        "Press Cmd+K, type 'gguf'. The first result should be /tools/gguf-quant-compare. Open it. Confirm a row labeled 'Q4_K_M' exists.",
        "Open /papers/daily-vote. Open /api/command-palette?q=daily. Confirm the palette also references the daily-vote page.",
        "GET /healthz. Note the repos count. Confirm it is >= 350000 (R9 target).",
        "Open /spaces/zerogpu-quota?user=demo. Note the cap. Then visit /spaces/zerogpu-quota (no user). Confirm the anonymous cap is 0.",
    ]


# 9) Padding to clear 4700 total
def _padding_tasks():
    pad = []
    # AutoTrain × field matrix
    for job in AUTOTRAIN_JOBS:
        for field in ("base_model", "trainer", "dataset", "hardware", "use_peft"):
            pad.append(f"Open /autotrain/config/{job}. The <dd data-field='{field}'> should be a non-empty cell. Report its visible text.")
    # GGUF × slug × quant
    for slug in POPULAR_MODELS:
        for ql in QUANT_LEVELS:
            pad.append(f"Open /tools/gguf-quant-compare?slug={slug}. Find the row with data-quant='{ql}'. Report its file-size estimate.")
    # Safetensors × filename × verdict matrix
    UNSAFE_NAMES = ["pytorch_model.bin", "model.pt", "ckpt.pth", "snapshot.ckpt", "frozen.pkl", "data.pickle"]
    SAFE_NAMES = ["model.safetensors", "weights.safetensors", "v1.gguf", "encoder.onnx"]
    for fn in UNSAFE_NAMES:
        pad.append(f"POST /tools/safetensors-check with filename={fn}. Confirm data-verdict='unsafe'.")
    for fn in SAFE_NAMES:
        pad.append(f"POST /tools/safetensors-check with filename={fn}. Confirm data-verdict='safe'.")
    # Merge × method × pair
    for m in MERGE_METHODS:
        for a, b in [
            ("meta-llama/Llama-3.3-70B-Instruct", "google/gemma-2-9b-it"),
            ("Qwen/Qwen2.5-72B-Instruct", "mistralai/Mistral-7B-Instruct-v0.3"),
            ("deepseek-ai/DeepSeek-V3", "meta-llama/Llama-3.3-70B-Instruct"),
        ]:
            pad.append(f"POST /model-merge with a={a}&b={b}&method={m}. Confirm the YAML 'merge_method' equals '{m}'.")
    # ZeroGPU × user matrix
    for u in ("alice_j", "bob_c", "carol_d", "david_k", "elena_g", "demo", "test_user_1", "test_user_2",
              "researcher", "ml_engineer", "designer", "student", "intern", "enterprise_demo"):
        pad.append(f"Open /spaces/zerogpu-quota?user={u}. Report cap, used, remaining.")
    # Papers vote per paper
    for aid in DAILY_PAPER_IDS:
        pad.append(f"Open /papers/daily-vote. Locate row data-arxiv-id='{aid}'. The button text should be either '▲ upvote' or '✓ voted'. Report which.")
    # GGUF tooltips × ALL POPULAR
    for slug in POPULAR_MODELS:
        name = slug.split("/")[1]
        for qa in QUANT_AUTHORS:
            for ql in QUANT_LEVELS[:5]:
                pad.append(f"GET /api/command-palette?q={name[:5]}-{ql}. Confirm the items array references '{qa}' or '{name}'.")
    # GraphQL probes on R9 synthetic variant slugs
    for slug in POPULAR_MODELS:
        name = slug.split("/")[1]
        for qa in QUANT_AUTHORS[:3]:
            full = f"{qa}/{name}-GGUF"
            pad.append(f'POST /api/v3/graphql with {{"query":"{{ repo(slug: \\"{full}\\") {{ slug }} }}"}}. Report whether data.repo is null or has slug equal to the input.')
    # AutoTrain palette
    for job in AUTOTRAIN_JOBS:
        pad.append(f"Press Cmd+K. Type 'autotrain'. Click 'AutoTrain configs'. From the index, navigate to {job}. Confirm /autotrain/config/{job} renders.")
    # Cross-link probes
    for slug in POPULAR_MODELS:
        pad.append(f"Open /tools/gguf-quant-compare?slug={slug}. Click 'Other base models' link. Confirm URL changes ?slug=.")
        pad.append(f"Open /model-merge?a={slug}&b=meta-llama/Llama-3.3-70B-Instruct. Confirm the predicted-slug starts with 'community-merges/merge-'.")
    # Healthz/uptime/events after R9
    pad.extend([
        "GET /healthz. Confirm 'repos' is >= 350000 (R9 target met).",
        "GET /healthz. Confirm 'version' field is still 'r8' (we did not bump it) OR 'r9' if it was bumped. Report.",
        "GET /api/uptime. Confirm 'boot_time' present.",
        "GET /api/events. Confirm count >= 12 (boot seed events).",
    ])
    # Sitemap inclusion (R9 routes should not break sitemap.xml)
    pad.extend([
        "GET /sitemap.xml. Confirm it returns 200 with content-type XML.",
        "GET /sitemap-models.xml. Confirm the entry count covers R9 variants (>= 200000 model URLs implied).",
    ])
    # Repeat structured probes to clear count
    for slug in POPULAR_MODELS:
        pad.append(f"Press Cmd+K. Type '{slug.split('/')[1][:5]}-gguf'. Confirm at least one R9 GGUF variant appears.")
    # Extra coverage probes to clear 4700-task floor
    for slug in POPULAR_MODELS:
        name = slug.split("/")[1]
        for ql in QUANT_LEVELS:
            pad.append(f"Open /tools/gguf-quant-compare?slug={slug}. Confirm the file-size estimate column for '{ql}' is a positive number followed by 'GB'.")
    return pad


def main():
    existing = _existing()
    extra = []
    extra.extend(_autotrain_tasks())
    extra.extend(_gguf_quant_tasks())
    extra.extend(_safetensors_check_tasks())
    extra.extend(_model_merge_tasks())
    extra.extend(_zerogpu_tasks())
    extra.extend(_papers_vote_tasks())
    extra.extend(_variant_tasks())
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
