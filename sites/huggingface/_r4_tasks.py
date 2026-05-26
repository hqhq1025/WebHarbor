"""R4 — append new tasks targeting the new R4 capabilities, then renumber
the entire tasks.jsonl so every Huggingface--<n> id is unique and sequential.

R4 capabilities exercised by the new templates:
  * bibtex export on /papers/<id>
  * model-card section collapse
  * monthly download sparkline
  * dataset-viewer pagination + split tabs
  * file-tree expand/collapse aside
  * /<u>/organizations
  * /AutoTrain
  * /pricing/spaces, /pricing/datasets
  * /docs/transformers/<topic>
  * /<repo>/files-and-versions alias
  * /discussions/<id> top-level shortcut
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


NEW_QUESTIONS = [
    # --- paper-bibtex-export (4)
    "Open /papers/2504.03275 and copy the BibTeX citation. Report the BibTeX entry's @misc key.",
    "On /papers/2504.03105 (FLUX.2), look at the BibTeX citation panel. What year field does it show?",
    "Open the paper page for arxiv id 2504.02810 (DPO-Bench) and download the BibTeX (use ?format=bibtex). Report the `primaryClass` value.",
    "Visit /papers/2503.18804 (OLMo-2) and read its BibTeX citation. Report the `archivePrefix` field's value.",
    # --- model-card-citation-bibtex / readme section navigation (6)
    "Open the model card for meta-llama/Llama-3.3-70B-Instruct. Expand the 'Intended uses & limitations' section and copy the first paragraph.",
    "Visit Qwen/Qwen2.5-72B-Instruct's model card. List every collapsible section heading shown on the page.",
    "On the model card for openai/whisper-large-v3, expand the 'Training & data' section and report the first sentence.",
    "Open google/gemma-2-9b-it and report how many collapsible readme sections appear, including the Overview section.",
    "Visit black-forest-labs/FLUX.1-dev and identify which readme section heading covers license information.",
    "Open stabilityai/stable-diffusion-3-medium-diffusers, expand 'How to use', and report what library import statement is shown.",
    # --- monthly download sparkline (6)
    "On the model page for meta-llama/Llama-3.3-70B-Instruct, look at the monthly download sparkline. Report the model's trending score.",
    "Visit openai/whisper-large-v3 and read the trending score shown below the sparkline.",
    "On the dataset page for HuggingFaceFW/fineweb-edu, look at the 12-month download sparkline. How many bars are shown?",
    "Open google/gemma-2-9b-it's model page and report the trending score from the sidebar.",
    "Visit Qwen/Qwen2.5-72B-Instruct and look at the sparkline labels — what are the two extreme x-axis captions?",
    "Open mistralai/Mistral-7B-Instruct-v0.3 and report whether the sparkline's most recent month bar is taller than the first month bar.",
    # --- dataset-loader-config-name + viewer split tabs (8)
    "Open the dataset viewer for HuggingFaceH4/ultrachat_200k. Switch to the validation split tab. How many rows does it list?",
    "On HuggingFaceFW/fineweb-edu's dataset viewer, navigate to page 2 of the train split. Report row index 1's first column value.",
    "Open the dataset viewer for argilla/distilabel-capybara-dpo-7k-binarized. Switch to the test split tab. What's the visible row count?",
    "Visit the dataset viewer for OpenAssistant/oasst1 and report the column names shown in the train split header.",
    "On the dataset viewer for allenai/dolma, click into the 'validation' tab. Confirm the active split shown in the meta strip.",
    "Open the dataset viewer for tatsu-lab/alpaca and use the pagination — go to the last page. What is the page number shown?",
    "Visit the dataset viewer for lmsys/lmsys-chat-1m. List the three split tabs and which one is active by default.",
    "On the dataset viewer for HuggingFaceH4/ultrachat_200k, navigate to page 3 (?page=3). Report the row count visible on that page.",
    # --- file-tree expand/collapse + files-and-versions (8)
    "Open meta-llama/Llama-3.3-70B-Instruct's files-and-versions page. Click 'Expand all' in the file tree pane. List the top-level directories.",
    "Visit /openai/whisper-large-v3/files-and-versions. In the file tree pane, what is the first file under 'Root files'?",
    "Open black-forest-labs/FLUX.1-dev's files-and-versions. Confirm the page renders the same content as /tree/main.",
    "Go to bert-base-uncased's file tree and click 'Collapse all'. Confirm the directories all collapse.",
    "On Qwen/Qwen2.5-72B-Instruct's files-and-versions page, find the README.md size in the listing.",
    "Open stabilityai/stable-diffusion-3-medium-diffusers's files-and-versions page and locate model.safetensors. Report its size badge.",
    "Visit HuggingFaceFW/fineweb-edu/files-and-versions. Look at the dataset's file tree aside. How many top-level entries are shown?",
    "On openai/whisper-large-v3, navigate to /openai/whisper-large-v3/files-and-versions/tokenizer.json (or via the side aside). Report the file's size.",
    # --- organization-create + /<u>/organizations (6)
    "Visit /demo/organizations and report the page title.",
    "Open /huggingface/organizations (as if 'huggingface' were a user) and list how many organization cards are shown.",
    "Go to /Qwen/organizations and copy the 'Create new organization' form's Type dropdown options.",
    "Visit /meta-llama/organizations and identify whether the 'Create organization' submit button is labelled 'Create organization' or 'Submit'.",
    "On /openai/organizations, count the verified organization cards in the listing.",
    "Open /google/organizations and report the first organization card's display name (alphabetical).",
    # --- AutoTrain status (8)
    "Open /AutoTrain and report which job is in Queued status.",
    "Visit /autotrain and find the job named 'stable-diffusion-3-anime'. Report its progress percent.",
    "On the AutoTrain page, which job is in Failed status?",
    "Go to /AutoTrain and list every job marked as Running.",
    "Open /autotrain. What hardware tier does the 'mistral-7b-rag-distill' job use?",
    "Visit /AutoTrain and report the duration of the 'qa-finetune-mlqa' job.",
    "On /autotrain, locate the 'New training job' form. List the 4 hardware options shown in the Hardware dropdown.",
    "Open /AutoTrain and report the total number of jobs displayed in the recent jobs table.",
    # --- pricing-spaces (5)
    "Open /pricing/spaces and report the price of the Nvidia A10G tier.",
    "Visit /pricing/spaces. Which tier is described as best for 'Frontier-model inference'?",
    "Go to /pricing/spaces and report the L40S hardware specs (CPU·RAM·GPU).",
    "On /pricing/spaces, expand the 'Is there a free tier?' FAQ. What does the answer say about CPU Basic?",
    "Open /pricing/spaces. List every hardware tier slug shown in the table.",
    # --- pricing-datasets (4)
    "Visit /pricing/datasets and report the monthly cost of the Pro plan.",
    "On /pricing/datasets, what is the bandwidth overage rate per GB?",
    "Open /pricing/datasets and report the storage overage rate per GB per month.",
    "Visit /pricing/datasets. Open the 'What's the largest single file I can upload?' FAQ. Report the size limit.",
    # --- docs/transformers/<topic> (5)
    "Open /docs/transformers/pipeline and report the topic badge or breadcrumb shown.",
    "Visit /docs/transformers/quicktour. Confirm the page renders (no 404).",
    "Open /docs/transformers/training and report the URL slug in the breadcrumb.",
    "Visit /docs/transformers/inference. Read the body and report the first sentence.",
    "Open /docs/transformers/installation. Report the topic name in the page title.",
    # --- space-secret-add (3)
    "Open black-forest-labs/FLUX.1-dev's space page (or any space detail). Report the hardware shown in the side card.",
    "Visit huggingface/tgi Space. Report its current Status badge text.",
    "Open the space for stabilityai/stable-diffusion-3-demo. Find the 'Use in libraries' tag. Report its value.",
    # --- leaderboard-submission (4)
    "Open /leaderboards/open-llm-leaderboard-v2. List the column headers of the rankings table.",
    "Visit /leaderboards/open-asr and report the rank-1 model's name.",
    "On /leaderboards/mteb, click into intfloat/multilingual-e5-large. Report the model's license_display.",
    "Open /leaderboards/text-to-image-arena. Report which model is in rank 1 and its license.",
    # --- dataset-filter-by-language (4)
    "Open /datasets and filter (or search) for tag 'chinese'. Report how many datasets match.",
    "Visit /datasets?q=japanese and report the top result's slug.",
    "On /datasets, filter for modality=audio and report the top dataset's name.",
    "Open /datasets?q=korean and report the top-listed dataset's likes count.",
    # --- code-snippet-copy (4)
    "Open meta-llama/Llama-3.3-70B-Instruct's model page. Find the 'Use in libraries' code block. What pipeline string is used?",
    "Visit openai/whisper-large-v3 and report the pipeline task string in the code snippet.",
    "On google/gemma-2-9b-it's model page, find the code snippet's `model=` argument. Report the exact slug.",
    "Open Qwen/Qwen2.5-72B-Instruct and report the import statement shown in the side-card code block.",
    # --- /discussions/<id> shortcut (3)
    "Visit /discussions/1. Confirm it redirects you to a /<author>/<name>/discussions/1 URL. Report the destination path.",
    "Open /discussions/10 and copy the discussion title from the resulting page.",
    "Visit /discussions/50. Report the repo slug shown after the redirect.",
    # --- multi-step (10)
    "On Hugging Face, find a text-generation model with Apache-2.0 license, open its files-and-versions page, then go to its discussions tab. Report the latest discussion title.",
    "Open the most-liked text-to-image space, expand its readme sections, and report whether a 'License' section heading exists.",
    "From /papers, pick the paper with the highest upvotes published in April 2026, navigate to its first related model, and copy that model's BibTeX entry @misc key.",
    "Search '/models?q=llama', open the first result, expand its 'How to use' readme section, and report the python pipeline code shown.",
    "Visit /leaderboards/mteb, click into rank-1 model, open its files-and-versions, and report the count of top-level directories.",
    "From /autotrain, find a Completed job, then navigate to /pricing/spaces and report the hourly price of the hardware tier used.",
    "Open /pricing/datasets, follow back to /pricing, then click into the Pro plan detail page. Report its full feature count.",
    "Find the /docs/transformers/pipeline page, then navigate to the linked /papers index. Report the upvote count of the top paper.",
    "From /huggingface/organizations, follow the first verified org card to its /organizations/<u> page. Report its followers_count.",
    "On the dataset viewer for HuggingFaceH4/ultrachat_200k, switch to validation split, then go to page 2. Report the active split shown in the meta strip.",
]


def main():
    existing = _existing()
    new_rows = []
    for q in NEW_QUESTIONS:
        new_rows.append({
            "web_name": "Huggingface",
            "id": "PLACEHOLDER",
            "ques": q,
            "web": "http://localhost:40010/",
            "upstream_url": "https://huggingface.co/",
        })

    # ---------- Bulk template-generated R4 tasks ----------
    # Use a curated list of (slug, kind, task) tuples to fan out each surface
    # template across multiple targets so the bench gets coverage breadth
    # without 1:1 hand-written questions.
    POPULAR_MODELS = [
        ("meta-llama/Llama-3.3-70B-Instruct", "text-generation"),
        ("Qwen/Qwen2.5-72B-Instruct", "text-generation"),
        ("google/gemma-2-9b-it", "text-generation"),
        ("mistralai/Mistral-7B-Instruct-v0.3", "text-generation"),
        ("microsoft/Phi-3.5-mini-instruct", "text-generation"),
        ("openai/whisper-large-v3", "automatic-speech-recognition"),
        ("black-forest-labs/FLUX.1-dev", "text-to-image"),
        ("stabilityai/stable-diffusion-3-medium-diffusers", "text-to-image"),
        ("sentence-transformers/all-MiniLM-L6-v2", "sentence-similarity"),
        ("intfloat/multilingual-e5-large", "sentence-similarity"),
        ("BAAI/bge-large-en-v1.5", "sentence-similarity"),
        ("coqui/XTTS-v2", "text-to-speech"),
        ("microsoft/resnet-50", "image-classification"),
        ("google/vit-base-patch16-224", "image-classification"),
        ("facebook/bart-large-cnn", "summarization"),
        ("Helsinki-NLP/opus-mt-en-ja", "translation"),
        ("dslim/bert-base-NER", "token-classification"),
        ("cardiffnlp/twitter-roberta-base-sentiment", "text-classification"),
        ("deepset/roberta-base-squad2", "question-answering"),
        ("bert-base-uncased", "fill-mask"),
    ]
    POPULAR_DATASETS = [
        "HuggingFaceFW/fineweb-edu",
        "HuggingFaceH4/ultrachat_200k",
        "OpenAssistant/oasst1",
        "tatsu-lab/alpaca",
        "lmsys/lmsys-chat-1m",
        "allenai/dolma",
        "argilla/distilabel-capybara-dpo-7k-binarized",
        "mozilla-foundation/common_voice_17_0",
        "LAION/laion2B-en",
        "EleutherAI/the_pile",
    ]
    POPULAR_SPACES = [
        "open-llm-leaderboard/open_llm_leaderboard",
        "huggingface/tgi",
        "lmsys/chatbot-arena",
        "stabilityai/stable-diffusion-3-demo",
        "black-forest-labs/FLUX.1-schnell",
    ]
    PIPELINE_TOPICS = [
        "pipeline", "quicktour", "training", "inference", "installation",
        "fine-tuning", "tokenizer", "model-doc", "main-classes", "perf-train",
    ]
    LANGS = ["chinese", "japanese", "korean", "spanish", "french", "german", "arabic", "russian", "portuguese", "hindi"]

    extra = []

    # 1) bibtex per paper id (12)
    for pid, tag in [("2504.03275", "ChainOfThoughtDistill"), ("2504.03105", "FLUX.2"),
                     ("2504.02998", "WhisperL4"), ("2504.02810", "DPOBench"),
                     ("2504.02645", "EdgeDiffusion"), ("2504.02501", "QuantSurvival"),
                     ("2503.18804", "OLMo2"), ("2504.03275", "Multilingual"),
                     ("2504.03105", "FLUXFlow"), ("2504.02810", "PrefOpt"),
                     ("2504.02998", "StreamASR"), ("2503.18804", "OLMo")]:
        extra.append(f"Visit /papers/{pid} and report the BibTeX `year` field shown in the citation panel.")

    # 2) model card sections collapse (M models × 4 questions = up to ~80)
    for slug, task in POPULAR_MODELS:
        extra.append(f"Open the model card for {slug}. Confirm the readme has collapsible sections and report the first section heading.")
        extra.append(f"On {slug}'s model page, find the sidebar 'Use in libraries' code block and report the pipeline task argument.")
        extra.append(f"Visit {slug} and read the sparkline trending score shown next to the 12-month bars.")
        extra.append(f"Open {slug}'s files-and-versions page. List how many top-level directories are visible in the file tree aside.")

    # 3) dataset viewer pagination (DS × 4 = 40)
    for slug in POPULAR_DATASETS:
        for split in ("train", "validation", "test"):
            extra.append(f"On the dataset viewer for {slug}, switch to the {split} split tab. Report the active split shown in the meta strip.")
        extra.append(f"Open the dataset viewer for {slug} and navigate to page 2. Report the page number shown in the pagination bar.")

    # 4) space hardware/status (SP × 3 = 15)
    for slug in POPULAR_SPACES:
        extra.append(f"Open the space page for {slug}. Report its hardware tier from the side card.")
        extra.append(f"On {slug}'s space page, report the Status badge text.")
        extra.append(f"Visit {slug} and confirm whether its readme uses collapsible sections (yes/no).")

    # 5) docs/transformers topics (10)
    for topic in PIPELINE_TOPICS:
        extra.append(f"Open /docs/transformers/{topic}. Confirm the page renders without 404 and report the topic in the breadcrumb.")

    # 6) /<u>/organizations (10)
    for user in ["demo", "huggingface", "Qwen", "meta-llama", "google", "openai",
                 "microsoft", "stabilityai", "black-forest-labs", "mistralai"]:
        extra.append(f"Visit /{user}/organizations and report how many organization cards are listed.")

    # 7) AutoTrain checks (10)
    autotrain_jobs = ["qa-finetune-mlqa", "llama-3-finance-lora",
                      "stable-diffusion-3-anime", "whisper-large-v3-japanese",
                      "phi-4-medical-qa", "mistral-7b-rag-distill"]
    for j in autotrain_jobs:
        extra.append(f"Open /AutoTrain and report the status of the job '{j}'.")
    for j in autotrain_jobs[:4]:
        extra.append(f"Visit /autotrain. For the '{j}' job, report its hardware tier.")

    # 8) /pricing/spaces and /pricing/datasets (12)
    for tier in ["CPU Basic", "CPU Upgrade", "Nvidia T4", "Nvidia L4",
                 "Nvidia L40S"]:
        extra.append(f"Open /pricing/spaces and report the price of the '{tier}' tier.")
    for plan in ["Public", "Pro", "Enterprise"]:
        extra.append(f"On /pricing/datasets, report the storage limit listed for the '{plan}' plan.")
    for q in ["Are public datasets truly free?",
              "What's the largest single file I can upload?",
              "Can I bring my own S3 bucket?",
              "Is there a free tier?"]:
        extra.append(f"On /pricing/spaces or /pricing/datasets, expand the FAQ '{q}' and report the first sentence of the answer.")

    # 9) discussions/<id> redirect (5)
    for did in [1, 5, 10, 25, 50]:
        extra.append(f"Visit /discussions/{did}. Confirm the redirect lands on a /<author>/<name>/discussions/{did} page. Report the canonical repo slug.")

    # 10) dataset language filter (10)
    for lang in LANGS:
        extra.append(f"Open /datasets?q={lang} and report the top-listed dataset's slug.")

    # 11) bibtex export format=bibtex (8)
    for pid in ["2504.03275", "2504.03105", "2504.02998", "2504.02810",
                "2504.02645", "2504.02501", "2503.18804", "2504.03275"]:
        extra.append(f"Open /papers/{pid}?format=bibtex and verify it returns plain BibTeX. Report the `eprint` value.")

    # 12) leaderboard submission / read (8)
    for lb in ["open-llm-leaderboard-v2", "open-asr", "mteb", "text-to-image-arena",
               "translation-bleu", "code-bench", "vision-language",
               "open-llm-leaderboard-v2"]:
        extra.append(f"Open /leaderboards/{lb} and report the rank-1 model's name.")

    # 13) code snippet read (M models × 1 = 20)
    for slug, task in POPULAR_MODELS:
        extra.append(f"Visit {slug} and report the model slug used inside the `pipeline(... model=...)` snippet.")

    # 14) files-and-versions alt URL (20)
    for slug, task in POPULAR_MODELS:
        extra.append(f"Open /{slug}/files-and-versions and report the page title.")

    # 15) sparkline reading (M × 2 = 40)
    for slug, task in POPULAR_MODELS:
        extra.append(f"Open {slug} and look at the 12-month sparkline. Report whether the most recent bar (rightmost, darker) is taller than the first bar.")
        extra.append(f"Visit {slug} and report the trending score from the sidebar.")

    # 16) multi-step combos (12)
    extra.extend([
        "Go to /AutoTrain, find the Failed job, navigate to /pricing/spaces, and report the price of that job's hardware tier.",
        "From /papers, find the top paper of April 2026, navigate to its first related model, and report the model's trending score.",
        "Open /pricing/datasets, follow back to /pricing, click the Pro plan detail page, then report the per-month price displayed.",
        "Visit /docs/transformers/pipeline, navigate to /papers index, and report the upvotes of the top paper.",
        "From /demo/organizations follow the first verified org to /organizations/<u> page, then to that org's first model.",
        "Open dataset viewer for HuggingFaceH4/ultrachat_200k, switch to validation, then go to page 2. Report the page number.",
        "Navigate to a Completed AutoTrain job, then to the /pricing/spaces page. Report the price of A10G.",
        "From /pricing/spaces, expand the 'auto-sleep idle Spaces' FAQ, and report the default sleep time on Pro.",
        "Open Qwen/Qwen2.5-72B-Instruct, expand its readme sections, and count the number of expandable sections.",
        "Visit dataset viewer for tatsu-lab/alpaca, switch to test split, navigate page 2. Report row count visible.",
        "From /leaderboards index, click MTEB, then click into the rank-1 model, then open its files-and-versions. Report the README size.",
        "Open /AutoTrain, click '+ New training job', and confirm the form shows 4 hardware options. Report the priciest tier listed.",
    ])

    for q in extra:
        new_rows.append({
            "web_name": "Huggingface",
            "id": "PLACEHOLDER",
            "ques": q,
            "web": "http://localhost:40010/",
            "upstream_url": "https://huggingface.co/",
        })

    # Combine existing + new, then renumber sequentially.
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
