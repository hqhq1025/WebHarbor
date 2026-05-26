"""
Task-driven static content for the Hugging Face mirror.

Provides structured dict-based content for pages that the WebVoyager
tasks expect to find: documentation topics, blog posts, daily papers,
classroom benefits, pricing plans, and dataset viewer rows.
"""


# ---------------------------------------------------------------------------
# Documentation topic pages — answers to WebVoyager doc-lookup tasks.
# ---------------------------------------------------------------------------
DOC_PAGES = {
    "llama-tokenizer": {
        "title": "LlamaTokenizer — Transformers Documentation",
        "section": "API / Models / Llama",
        "library": "transformers",
        "keywords": ["llama", "tokenizer", "spaces_between_special_tokens", "llamatokenizer"],
        "body": (
            "## LlamaTokenizer\n"
            "\n"
            "The `LlamaTokenizer` class provides BPE tokenization for Llama-family models.\n"
            "It inherits from `PreTrainedTokenizer` and shares most of the arguments.\n"
            "\n"
            "### Parameters\n"
            "\n"
            "- **vocab_file** (str) — Path to the sentencepiece vocabulary file.\n"
            "- **unk_token** (str, defaults to '<unk>') — Unknown token.\n"
            "- **bos_token** (str, defaults to '<s>') — Beginning of sequence token.\n"
            "- **eos_token** (str, defaults to '</s>') — End of sequence token.\n"
            "- **pad_token** (str, optional) — Padding token.\n"
            "- **sp_model_kwargs** (dict, optional) — Arguments passed to SentencePieceProcessor.\n"
            "- **add_bos_token** (bool, defaults to True) — Whether to add BOS token.\n"
            "- **add_eos_token** (bool, defaults to False) — Whether to add EOS token.\n"
            "- **clean_up_tokenization_spaces** (bool, defaults to False) — Whether to clean up tokenization spaces.\n"
            "- **use_default_system_prompt** (bool, defaults to False) — Use the default Llama system prompt.\n"
            "- **spaces_between_special_tokens** (bool, defaults to False) — Whether or not to insert whitespace between special tokens when decoding.\n"
            "- **legacy** (bool, optional) — Whether or not the legacy tokenizer should be used.\n"
            "\n"
            "The `spaces_between_special_tokens` parameter has type **bool** and its default value is **False**.\n"
        ),
    },
    "trl-forward-modelling": {
        "title": "Forward modelling and loss margins — TRL Documentation",
        "section": "TRL / Advanced usage",
        "library": "trl",
        "keywords": ["trl", "forward", "modelling", "modeling", "margin", "loss", "dpo"],
        "body": (
            "## Forward modelling — adding a margin to the loss\n"
            "\n"
            "TRL's `DPOTrainer`, `CPOTrainer` and `SimPOTrainer` all support adding a margin to\n"
            "their preference loss. To add a margin simply pass `margin` in your dataset or via\n"
            "the training arguments:\n"
            "\n"
            "```python\n"
            "from trl import DPOConfig, DPOTrainer\n"
            "\n"
            "config = DPOConfig(\n"
            "    output_dir='./dpo-margin',\n"
            "    loss_type='sigmoid',\n"
            "    # Add a margin term to the logits difference\n"
            "    label_smoothing=0.0,\n"
            "    beta=0.1,\n"
            ")\n"
            "\n"
            "# In your dataset each example may carry a 'margin' column:\n"
            "# { 'prompt': ..., 'chosen': ..., 'rejected': ..., 'margin': 0.5 }\n"
            "\n"
            "trainer = DPOTrainer(\n"
            "    model=model,\n"
            "    args=config,\n"
            "    train_dataset=train_dataset,\n"
            "    tokenizer=tokenizer,\n"
            ")\n"
            "trainer.train()\n"
            "```\n"
            "\n"
            "Internally the trainer computes the standard DPO loss and subtracts the margin\n"
            "from the logit difference before applying the sigmoid: "
            "`loss = -log(sigmoid(beta * (chosen_logps - rejected_logps - margin)))`.\n"
        ),
    },
    "pytorch-to-tensorflow": {
        "title": "Convert a PyTorch model to TensorFlow — Transformers",
        "section": "Interoperability / Framework conversion",
        "library": "transformers",
        "keywords": ["convert", "pytorch", "tensorflow", "tf", "interoperability"],
        "body": (
            "## Converting PyTorch checkpoints to TensorFlow\n"
            "\n"
            "The Transformers library supports loading PyTorch checkpoints into a TensorFlow model\n"
            "(and vice versa) via the `from_pt=True` argument.\n"
            "\n"
            "### Step 1 — Save the PyTorch model\n"
            "```python\n"
            "from transformers import AutoModel, AutoTokenizer\n"
            "model = AutoModel.from_pretrained('bert-base-uncased')\n"
            "model.save_pretrained('./bert-pt')\n"
            "```\n"
            "\n"
            "### Step 2 — Reload it as a TensorFlow model\n"
            "```python\n"
            "from transformers import TFAutoModel\n"
            "tf_model = TFAutoModel.from_pretrained('./bert-pt', from_pt=True)\n"
            "```\n"
            "\n"
            "### Step 3 — Save the TensorFlow weights\n"
            "```python\n"
            "tf_model.save_pretrained('./bert-tf')\n"
            "```\n"
            "\n"
            "The cross-framework loader matches layer names automatically. For custom architectures you can\n"
            "subclass `TFPreTrainedModel` and implement the layer mapping yourself.\n"
        ),
    },
    "trainer-api": {
        "title": "Trainer API — Training on a custom dataset",
        "section": "Transformers / Trainer",
        "library": "transformers",
        "keywords": ["trainer", "training", "custom", "dataset", "trainer api"],
        "body": (
            "## Using the Trainer API for custom datasets\n"
            "\n"
            "`Trainer` is the main class for training Transformers models with minimal boilerplate.\n"
            "\n"
            "### Minimal example\n"
            "```python\n"
            "from transformers import Trainer, TrainingArguments\n"
            "\n"
            "args = TrainingArguments(\n"
            "    output_dir='./out',\n"
            "    num_train_epochs=3,\n"
            "    per_device_train_batch_size=8,\n"
            "    per_device_eval_batch_size=8,\n"
            "    learning_rate=5e-5,\n"
            "    weight_decay=0.01,\n"
            "    evaluation_strategy='epoch',\n"
            "    save_strategy='epoch',\n"
            "    logging_dir='./logs',\n"
            "    fp16=True,\n"
            ")\n"
            "\n"
            "trainer = Trainer(\n"
            "    model=model,\n"
            "    args=args,\n"
            "    train_dataset=train_ds,\n"
            "    eval_dataset=val_ds,\n"
            "    tokenizer=tokenizer,\n"
            "    compute_metrics=compute_metrics,\n"
            ")\n"
            "trainer.train()\n"
            "```\n"
            "\n"
            "### Configurable parameters of the Trainer class\n"
            "- **model** — A `PreTrainedModel` instance.\n"
            "- **args** — `TrainingArguments` controlling learning rate, schedule, batch size, mixed precision, etc.\n"
            "- **data_collator** — Custom batch collator.\n"
            "- **train_dataset / eval_dataset** — Your custom datasets.\n"
            "- **tokenizer** — Used for padding and decoding examples.\n"
            "- **compute_metrics** — Callable returning a metric dict.\n"
            "- **callbacks** — List of `TrainerCallback` objects (e.g. `EarlyStoppingCallback`).\n"
            "- **optimizers** — Tuple `(optimizer, scheduler)` if you want to override defaults.\n"
        ),
    },
    "pipeline-tour": {
        "title": "The pipeline API — Transformers Quick Tour",
        "section": "Transformers / Quick tour",
        "library": "transformers",
        "keywords": ["pipeline", "quick tour", "sentiment", "tour", "inference"],
        "body": (
            "## The pipeline() function\n"
            "\n"
            "`pipeline()` is the easiest way to use a pretrained model for inference. Pass a task\n"
            "name and it will download a sensible default model.\n"
            "\n"
            "### Sentiment analysis\n"
            "```python\n"
            "from transformers import pipeline\n"
            "classifier = pipeline('sentiment-analysis')\n"
            "classifier('We are very happy to show you the Transformers library.')\n"
            "# [{'label': 'POSITIVE', 'score': 0.9998}]\n"
            "```\n"
            "\n"
            "When you instantiate `pipeline('sentiment-analysis')` without a `model=` argument,\n"
            "the default model loaded is **distilbert/distilbert-base-uncased-finetuned-sst-2-english**.\n"
            "It is a DistilBERT checkpoint fine-tuned on the Stanford Sentiment Treebank (SST-2).\n"
        ),
    },
    "peft-adapters": {
        "title": "PEFT — Load adapters in 8-bit or 4-bit",
        "section": "PEFT / Tutorials",
        "library": "peft",
        "keywords": ["peft", "adapter", "adapters", "8bit", "4bit", "quantization", "load"],
        "body": (
            "## Loading adapters in 8-bit or 4-bit\n"
            "\n"
            "PEFT supports loading base models with `bitsandbytes` quantization and then attaching LoRA\n"
            "adapters on top. Install `bitsandbytes` first:\n"
            "\n"
            "```bash\n"
            "pip install bitsandbytes accelerate peft transformers\n"
            "```\n"
            "\n"
            "### Load in 8-bit\n"
            "```python\n"
            "from transformers import AutoModelForCausalLM, BitsAndBytesConfig\n"
            "from peft import PeftModel\n"
            "\n"
            "bnb_config = BitsAndBytesConfig(load_in_8bit=True)\n"
            "base = AutoModelForCausalLM.from_pretrained(\n"
            "    'meta-llama/Llama-2-7b-hf',\n"
            "    quantization_config=bnb_config,\n"
            "    device_map='auto',\n"
            ")\n"
            "model = PeftModel.from_pretrained(base, 'my-user/my-lora-adapter')\n"
            "```\n"
            "\n"
            "### Load in 4-bit\n"
            "```python\n"
            "bnb_config = BitsAndBytesConfig(\n"
            "    load_in_4bit=True,\n"
            "    bnb_4bit_use_double_quant=True,\n"
            "    bnb_4bit_quant_type='nf4',\n"
            "    bnb_4bit_compute_dtype='bfloat16',\n"
            ")\n"
            "base = AutoModelForCausalLM.from_pretrained(\n"
            "    'meta-llama/Llama-2-7b-hf',\n"
            "    quantization_config=bnb_config,\n"
            "    device_map='auto',\n"
            ")\n"
            "model = PeftModel.from_pretrained(base, 'my-user/my-lora-adapter')\n"
            "```\n"
            "\n"
            "With 4-bit you trade a little accuracy for a 4-8x memory saving — perfect for fine-tuning\n"
            "7B/13B models on a single consumer GPU.\n"
        ),
    },
    "text-embeddings-inference": {
        "title": "Text Embeddings Inference — TEI",
        "section": "TEI / Overview",
        "library": "text-embeddings-inference",
        "keywords": ["text embeddings inference", "tei", "embeddings", "toolkit"],
        "body": (
            "## Text Embeddings Inference (TEI)\n"
            "\n"
            "TEI is a blazing-fast inference server for text embedding and sequence classification models.\n"
            "\n"
            "### Strengths\n"
            "- **Fast** — Built in Rust, uses CUDA kernels, token-level dynamic batching and Flash Attention.\n"
            "- **Small** — Docker images under 150MB, no Python runtime.\n"
            "- **Production-ready** — OpenAPI spec, Prometheus metrics, safetensors support.\n"
            "- **Flexible** — Supports BERT, RoBERTa, DistilBERT, MPNet, GTE, BGE, E5, Jina and many more.\n"
            "- **Scalable** — Horizontal scaling, gRPC and HTTP endpoints.\n"
            "- **Easy to deploy** — Single command `docker run` to start a server.\n"
            "- **Tracing** — OpenTelemetry integration out of the box.\n"
        ),
    },
    "transformers-add-tokens": {
        "title": "Adding new tokens to a tokenizer — Transformers",
        "section": "Transformers / Tokenizers",
        "library": "transformers",
        "keywords": ["add new tokens", "add tokens", "tokenizer", "add_tokens", "special token"],
        "body": (
            "## Adding new tokens to a tokenizer\n"
            "\n"
            "You can add regular or special tokens to any tokenizer. Resize the model's input\n"
            "embeddings afterwards.\n"
            "\n"
            "```python\n"
            "from transformers import AutoTokenizer, AutoModel\n"
            "\n"
            "tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')\n"
            "model = AutoModel.from_pretrained('bert-base-uncased')\n"
            "\n"
            "new_tokens = ['[CODE]', '[EOL]', 'myspecialword']\n"
            "num_added = tokenizer.add_tokens(new_tokens)\n"
            "\n"
            "# Adding special tokens\n"
            "tokenizer.add_special_tokens({'additional_special_tokens': ['[USR]', '[SYS]']})\n"
            "\n"
            "# Resize embeddings so the new tokens have rows in the embedding matrix\n"
            "model.resize_token_embeddings(len(tokenizer))\n"
            "```\n"
        ),
    },
    "transformers": {
        "title": "Transformers — Hugging Face Documentation",
        "section": "Libraries / Transformers",
        "library": "transformers",
        "github_stars": "136k",
        "github_url": "https://github.com/huggingface/transformers",
        "keywords": ["transformers", "library", "docs", "documentation", "huggingface docs", "github stars"],
        "body": (
            "## Transformers\n"
            "\n"
            "**GitHub Stars: 136,000+**\n"
            "\n"
            "State-of-the-art Machine Learning for JAX, PyTorch, and TensorFlow.\n"
            "Transformers provides thousands of pretrained models to perform tasks on different modalities "
            "such as text, vision, and audio.\n"
            "\n"
            "### Installation\n"
            "```bash\n"
            "pip install transformers\n"
            "```\n"
            "\n"
            "### Quick start\n"
            "```python\n"
            "from transformers import pipeline\n"
            "classifier = pipeline('sentiment-analysis')\n"
            "classifier('I love this library!')\n"
            "# [{'label': 'POSITIVE', 'score': 0.9998}]\n"
            "```\n"
        ),
    },
    "datasets": {
        "title": "Datasets — Hugging Face Documentation",
        "section": "Libraries / Datasets",
        "library": "datasets",
        "github_stars": "19.4k",
        "github_url": "https://github.com/huggingface/datasets",
        "keywords": ["datasets", "library", "docs", "documentation", "huggingface docs", "github stars"],
        "body": (
            "## Datasets\n"
            "\n"
            "**GitHub Stars: 19,400+**\n"
            "\n"
            "The largest hub of ready-to-use datasets for ML models with fast, easy-to-use and efficient "
            "data manipulation tools. Access datasets from the Hub or create your own.\n"
            "\n"
            "### Installation\n"
            "```bash\n"
            "pip install datasets\n"
            "```\n"
            "\n"
            "### Quick start\n"
            "```python\n"
            "from datasets import load_dataset\n"
            "dataset = load_dataset('imdb')\n"
            "print(dataset['train'][0])\n"
            "```\n"
        ),
    },
    "tokenizers": {
        "title": "Tokenizers — Hugging Face Documentation",
        "section": "Libraries / Tokenizers",
        "library": "tokenizers",
        "github_stars": "9.2k",
        "github_url": "https://github.com/huggingface/tokenizers",
        "keywords": ["tokenizers", "library", "docs", "documentation", "huggingface docs", "github stars"],
        "body": (
            "## Tokenizers\n"
            "\n"
            "**GitHub Stars: 9,200+**\n"
            "\n"
            "Fast, flexible, and easy-to-use tokenizers. Written in Rust with Python bindings, "
            "Tokenizers is optimized for both research and production use cases.\n"
            "\n"
            "### Installation\n"
            "```bash\n"
            "pip install tokenizers\n"
            "```\n"
            "\n"
            "### Features\n"
            "- Train new vocabularies and tokenize using the most popular methods.\n"
            "- Extremely fast (encoding 1 GB of text in <20 seconds on CPU).\n"
            "- Easy to use but also very versatile.\n"
            "- Designed for both research and production.\n"
            "- Normalization comes with alignment tracking.\n"
            "- Pre-tokenization, post-processing — full pipeline available.\n"
        ),
    },
}


# ---------------------------------------------------------------------------
# Blog posts — tagged so /blog?tag=diffusion filters cleanly.
# ---------------------------------------------------------------------------
BLOG_POSTS = [
    {
        "slug": "stable-diffusion-3-release",
        "title": "Introducing Stable Diffusion 3 on Hugging Face",
        "author": "Stability AI Team",
        "published": "2026-03-15",
        "tags": ["Diffusion", "Generative", "Text-to-Image"],
        "excerpt": "We're thrilled to announce the release of Stable Diffusion 3 — our most capable open text-to-image model, now available on the Hub.",
        "body": (
            "## Overview\n"
            "\n"
            "Stable Diffusion 3 is the latest generation of our flagship text-to-image diffusion model. It introduces a new\n"
            "rectified-flow transformer backbone, a dual text encoder stack, and native support for long, nuanced prompts.\n"
            "SD3 ships under a permissive research license and is available directly from the Hub.\n"
            "\n"
            "## What's new\n"
            "- **Rectified flow transformer** — straight-line denoising trajectories enable faster sampling.\n"
            "- **Dual text encoders** — combines CLIP and T5-XXL for better prompt adherence.\n"
            "- **Text rendering** — legible typography in generated images.\n"
            "- **Memory efficient** — runs on consumer GPUs with 8-bit inference.\n"
            "\n"
            "## Try it out\n"
            "Head to the [stabilityai/stable-diffusion-3-medium-diffusers](/models) page or run the linked Space for a zero-install demo.\n"
        ),
    },
    {
        "slug": "diffusers-03-release",
        "title": "Diffusers 0.30 — Lightning-fast Diffusion Pipelines",
        "author": "Diffusers Team",
        "published": "2026-04-02",
        "tags": ["Diffusion", "Diffusers", "Release"],
        "excerpt": "The latest Diffusers release brings 2x faster sampling, a new scheduler API and drop-in support for SD3, FLUX and Mochi.",
        "body": (
            "## Overview\n"
            "\n"
            "Diffusers 0.30 is here! This release focuses on making diffusion-based generation faster, more\n"
            "memory-efficient and easier to customize. Highlights include a unified scheduler API, native SD3/FLUX\n"
            "pipelines, and a new LCM (Latent Consistency Model) distillation workflow.\n"
            "\n"
            "## Highlights\n"
            "- 2× faster sampling with flow matching schedulers\n"
            "- New `AutoPipelineForText2Image` for effortless pipeline dispatch\n"
            "- Out-of-the-box SD3, FLUX.1 and Mochi support\n"
            "- First-class ONNX and TensorRT export\n"
        ),
    },
    {
        "slug": "llama-3-3-on-the-hub",
        "title": "Llama 3.3 is now on the Hub",
        "author": "Meta Llama Team",
        "published": "2026-03-01",
        "tags": ["LLM", "Llama", "NLP"],
        "excerpt": "Llama 3.3 70B Instruct is now available with a new Llama 3.3 community license and extended 128k context.",
        "body": "Full post content for Llama 3.3 release.",
    },
    {
        "slug": "open-asr-leaderboard",
        "title": "The Open ASR Leaderboard — Whisper, Parakeet and friends",
        "author": "HF Audio Team",
        "published": "2026-02-12",
        "tags": ["Audio", "ASR", "Benchmark"],
        "excerpt": "We evaluated the top open-source ASR models on 8 public datasets — see the full results.",
        "body": "Full post content for the ASR leaderboard.",
    },
]


# ---------------------------------------------------------------------------
# Daily papers — the first one is the 'featured' paper.
# ---------------------------------------------------------------------------
DAILY_PAPERS = [
    {
        "arxiv_id": "2504.03275",
        "title": "Scaling Chain-of-Thought Distillation Across 100+ Languages",
        "authors": "Maria Chen, Aditya Rao, Emily Zhao, Lukas Berg",
        "published": "2026-04-09",
        "upvotes": 248,
        "abstract": (
            "We present a framework for distilling chain-of-thought reasoning from a strong teacher model into "
            "compact student models across 100+ languages. Our approach combines synthetic data generation, "
            "self-refinement, and multilingual curriculum learning to transfer reasoning ability with less than "
            "5% of the teacher's parameters."
        ),
        "related_models": ["meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen2.5-72B-Instruct"],
        "related_datasets": ["HuggingFaceH4/ultrachat_200k"],
    },
    {
        "arxiv_id": "2504.03105",
        "title": "FLUX.2 — Rectified Flow Transformers at Scale",
        "authors": "Black Forest Labs",
        "published": "2026-04-08",
        "upvotes": 197,
        "abstract": "Rectified flow transformers scale gracefully to billion-parameter text-to-image models.",
        "related_models": ["black-forest-labs/FLUX.1-dev"],
        "related_datasets": [],
    },
    {
        "arxiv_id": "2504.02998",
        "title": "Whisper-L4 — Streaming ASR with Sub-100ms Latency",
        "authors": "OpenAI Audio",
        "published": "2026-04-07",
        "upvotes": 153,
        "abstract": "A streaming variant of Whisper with dramatically lower end-to-end latency.",
        "related_models": ["openai/whisper-large-v3"],
        "related_datasets": ["mozilla-foundation/common_voice_17_0"],
    },
    {
        "arxiv_id": "2504.02810",
        "title": "DPO-Bench: A Reproducible Suite for Preference Optimization",
        "authors": "Argilla Research, HuggingFaceH4",
        "published": "2026-04-05",
        "upvotes": 132,
        "abstract": (
            "We release DPO-Bench, a fully reproducible evaluation suite for preference optimization "
            "methods. The benchmark covers DPO, IPO, KTO, ORPO, SimPO and 14 derivatives, with frozen "
            "reference policies, deterministic data splits and a fixed judge model."
        ),
        "related_models": ["HuggingFaceH4/zephyr-7b-story-dragon-wizard"],
        "related_datasets": ["HuggingFaceH4/ultrachat_200k"],
    },
    {
        "arxiv_id": "2504.02645",
        "title": "Edge-Diffusion: Real-time Text-to-Image on Mobile GPUs",
        "authors": "Stability AI Mobile",
        "published": "2026-04-04",
        "upvotes": 118,
        "abstract": (
            "Edge-Diffusion is a distilled rectified-flow transformer that reaches 0.6 sec/image on "
            "an iPhone 15 Pro GPU at 512×512 — within 2.5 FID of SD3-medium on COCO."
        ),
        "related_models": ["stabilityai/stable-diffusion-3-medium-diffusers", "black-forest-labs/FLUX.1-schnell"],
        "related_datasets": ["LAION/laion2B-en"],
    },
    {
        "arxiv_id": "2504.02501",
        "title": "Quantization Survival Guide: How Far Can You Push GGUF in 2026?",
        "authors": "Unsloth AI, TheBloke",
        "published": "2026-04-02",
        "upvotes": 104,
        "abstract": (
            "A comprehensive evaluation of K-quant, I-matrix and AWQ recipes for the 2026 LLM landscape. "
            "We measure perplexity, MMLU and JEAR drift across 24 base models and 9 quantization levels."
        ),
        "related_models": ["meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen2.5-72B-Instruct"],
        "related_datasets": [],
    },
    {
        "arxiv_id": "2503.18804",
        "title": "OLMo-2: A Truly Open Multitrillion-token LLM",
        "authors": "Allen Institute for AI",
        "published": "2026-03-28",
        "upvotes": 162,
        "abstract": (
            "OLMo-2 ships a fully open release of every training-pipeline artifact: pretraining corpus, "
            "data recipes, eval suites, optimizer states, and checkpoint diffs. 7B and 13B variants match "
            "Llama-3 on 8 out of 10 reasoning tasks."
        ),
        "related_models": ["allenai/OLMo-2-1124-7B-Instruct"],
        "related_datasets": ["allenai/dolma"],
    },
    {
        "arxiv_id": "2503.18120",
        "title": "BGE-M3 Multilingual Embeddings at Trillion Scale",
        "authors": "BAAI Retrieval Group",
        "published": "2026-03-22",
        "upvotes": 89,
        "abstract": (
            "BGE-M3 unifies dense, sparse and multi-vector retrieval in a single 567M-parameter encoder. "
            "MTEB-X covers 24 languages and 8 retrieval slices — state of the art on 19 of 24."
        ),
        "related_models": ["BAAI/bge-large-en-v1.5", "intfloat/multilingual-e5-large"],
        "related_datasets": ["microsoft/ms_marco"],
    },
    {
        "arxiv_id": "2503.17912",
        "title": "Open-Reasoner: Distilling DeepSeek-R1 into Sub-7B Students",
        "authors": "DeepSeek-AI, EleutherAI",
        "published": "2026-03-18",
        "upvotes": 144,
        "abstract": (
            "We release distilled checkpoints of DeepSeek-R1 at 1.5B, 3B and 7B sizes. The students retain "
            "82% of the teacher's chain-of-thought accuracy on MATH while running 7-12× faster."
        ),
        "related_models": ["deepseek-ai/DeepSeek-R1-Distill-Qwen-32B", "deepseek-ai/DeepSeek-V3"],
        "related_datasets": ["openai/gsm8k"],
    },
    {
        "arxiv_id": "2503.17004",
        "title": "Florence-3: A General-Purpose Vision Foundation Model",
        "authors": "Microsoft Florence Team",
        "published": "2026-03-12",
        "upvotes": 121,
        "abstract": (
            "Florence-3 is a 3.7B vision-language model trained on 1.2B image-text pairs with a unified "
            "prompt format spanning OCR, grounding, captioning, detection and chart QA."
        ),
        "related_models": ["microsoft/Florence-2-large", "google/paligemma-3b-mix-448"],
        "related_datasets": ["coco"],
    },
    {
        "arxiv_id": "2503.15800",
        "title": "Long-RAG: Retrieval-Augmented Generation Beyond 1M Tokens",
        "authors": "Hugging Face Research, DeepSeek, Anthropic",
        "published": "2026-03-08",
        "upvotes": 98,
        "abstract": (
            "Long-RAG combines hierarchical retrieval with positional re-ranking and exact-match anchors to "
            "preserve precision over a 1M-token context window. We release retrieval indexes, prompts and "
            "evals as open-source artifacts."
        ),
        "related_models": ["Qwen/Qwen2.5-72B-Instruct", "meta-llama/Llama-3.3-70B-Instruct"],
        "related_datasets": ["HuggingFaceFW/fineweb"],
    },
    {
        "arxiv_id": "2503.14502",
        "title": "ZeroGPU at Scale: A Year of Free GPU for Everyone",
        "authors": "Hugging Face Infra",
        "published": "2026-03-04",
        "upvotes": 87,
        "abstract": (
            "Operational lessons from running 1.4M weekly Spaces on a shared H200 fleet. We share the "
            "scheduler design, fairness model and cost breakdown that made ZeroGPU economically viable."
        ),
        "related_models": [],
        "related_datasets": [],
    },
]


# ---------------------------------------------------------------------------
# Leaderboards — public benchmark rankings. Each leaderboard is a dict with
# columns + rows (already sorted, rank 1 first).
# ---------------------------------------------------------------------------
LEADERBOARDS = {
    "open-llm": {
        "title": "Open LLM Leaderboard v2",
        "emoji": "🦙",
        "description": (
            "Community evaluation of open-weight large language models on six reasoning, knowledge, "
            "math and instruction-following benchmarks. Scores are averaged to a single overall metric."
        ),
        "tags": ["text-generation", "reasoning", "instruction-tuned"],
        "columns": ["Rank", "Model", "Params", "Average", "MMLU-Pro", "GPQA", "MATH lvl-5", "MUSR", "IFEval"],
        "rows": [
            [1, "meta-llama/Llama-3.3-70B-Instruct",      "70B",  "47.82", "57.04", "16.78", "30.59", "21.81", "75.18"],
            [2, "Qwen/Qwen2.5-72B-Instruct",              "72B",  "47.31", "55.07", "17.34", "33.10", "20.51", "73.18"],
            [3, "deepseek-ai/DeepSeek-V3",                "671B", "46.95", "56.42", "18.81", "29.20", "18.40", "72.92"],
            [4, "Qwen/Qwen2.5-32B-Instruct",              "32B",  "39.41", "47.27", "12.30", "31.93", "21.61", "63.95"],
            [5, "google/gemma-2-27b-it",                  "27B",  "37.21", "44.93", "11.79", "13.50", "23.57", "78.05"],
            [6, "tiiuae/Falcon3-10B-Instruct",            "10B",  "32.05", "37.99",  "9.71", "22.05", "11.49", "78.16"],
            [7, "google/gemma-2-9b-it",                   "9B",   "30.47", "37.94",  "8.50", "11.85", "13.71", "80.40"],
            [8, "meta-llama/Llama-3.2-3B-Instruct",       "3B",   "21.32", "26.06",  "1.91",  "6.34",  "9.43", "62.94"],
            [9, "microsoft/Phi-3.5-mini-instruct",        "4B",   "21.04", "31.81",  "6.59", "12.92",  "9.65", "55.21"],
           [10, "allenai/OLMo-2-1124-7B-Instruct",        "7B",   "20.92", "26.18",  "5.94", "10.41",  "9.40", "53.92"],
        ],
    },
    "open-asr": {
        "title": "Open ASR Leaderboard",
        "emoji": "🎙️",
        "description": (
            "WER (lower is better) across 8 public speech-recognition test sets. Models are evaluated "
            "with greedy decoding at 16 kHz mono audio. Average is computed across all 8 splits."
        ),
        "tags": ["automatic-speech-recognition", "audio", "benchmark"],
        "columns": ["Rank", "Model", "Avg WER", "LibriSpeech-clean", "LibriSpeech-other", "TED-LIUM", "Common Voice", "Earnings-22"],
        "rows": [
            [1, "openai/whisper-large-v3-turbo-2026", "6.21",  "1.92",  "3.84",  "4.18", "10.42", "12.74"],
            [2, "openai/whisper-large-v3",            "6.65",  "1.95",  "3.92",  "4.41", "11.07", "13.18"],
            [3, "nvidia/parakeet-tdt-1.1b",           "6.93",  "1.69",  "3.55",  "4.08", "12.34", "14.12"],
            [4, "nvidia/parakeet-ctc-1.1b-2026",      "7.04",  "1.74",  "3.61",  "4.21", "12.50", "13.95"],
            [5, "facebook/seamless-m4t-v2-large-2026","7.81",  "2.18",  "4.45",  "5.07", "12.94", "14.62"],
            [6, "openai/whisper-small",               "9.74",  "3.42",  "7.61",  "5.94", "14.20", "17.32"],
        ],
    },
    "mteb": {
        "title": "MTEB English Embedding Leaderboard",
        "emoji": "🧬",
        "description": (
            "Massive Text Embedding Benchmark — 56 tasks covering retrieval, classification, clustering, "
            "reranking, STS, summarization. Higher = better."
        ),
        "tags": ["feature-extraction", "embeddings", "retrieval"],
        "columns": ["Rank", "Model", "Dim", "Avg", "Retrieval", "STS", "Classification"],
        "rows": [
            [1, "BAAI/bge-large-en-v1.5",                                   "1024", "67.83", "54.29", "85.43", "75.92"],
            [2, "intfloat/multilingual-e5-large",                           "1024", "66.20", "52.71", "84.10", "75.18"],
            [3, "sentence-transformers/all-MiniLM-L6-v2",                   "384",  "59.45", "41.93", "78.94", "63.20"],
            [4, "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", "384", "57.30", "39.50", "76.18", "62.10"],
            [5, "FacebookAI/roberta-base",                                  "768",  "44.21", "28.74", "70.45", "58.34"],
        ],
    },
    "text-to-image-arena": {
        "title": "Text-to-Image Arena",
        "emoji": "🎨",
        "description": (
            "Anonymous side-by-side voting on 1.2k prompts covering portrait, landscape, typography, "
            "and concept art. Elo computed every 4 hours from community votes."
        ),
        "tags": ["text-to-image", "generative", "arena"],
        "columns": ["Rank", "Model", "Elo", "Votes", "License"],
        "rows": [
            [1, "black-forest-labs/FLUX.1-dev",                          "1218", "84,217", "FLUX-1-dev (research)"],
            [2, "black-forest-labs/FLUX.1-schnell",                      "1194", "78,403", "Apache-2.0"],
            [3, "stabilityai/stable-diffusion-3-medium-diffusers",       "1147", "62,108", "Stability research"],
            [4, "stabilityai/stable-cascade",                            "1095", "48,925", "Stability research"],
            [5, "stabilityai/stable-diffusion-xl-base-1.0",              "1042", "92,418", "OpenRAIL-M"],
        ],
    },
    "translation-bleu": {
        "title": "Open Translation Leaderboard (FLORES-200 devtest)",
        "emoji": "🌐",
        "description": (
            "BLEU on FLORES-200 devtest for selected high-resource pairs. Each cell averages 5 generations "
            "at beam=5. Higher = better."
        ),
        "tags": ["translation", "multilingual", "benchmark"],
        "columns": ["Rank", "Model", "Avg BLEU", "en→zh", "en→fr", "en→de", "en→ja", "en→es"],
        "rows": [
            [1, "facebook/nllb-200-distilled-600M", "31.4", "29.8", "38.5", "32.1", "22.4", "34.2"],
            [2, "Helsinki-NLP/opus-mt-en-zh",       "30.9", "30.4", "37.6", "31.8", "21.9", "33.0"],
            [3, "Helsinki-NLP/opus-mt-en-fr-2026",  "30.2",  "—",   "38.4",  "—",    "—",   "—"  ],
            [4, "Helsinki-NLP/opus-mt-en-de-2026",  "29.8",  "—",    "—",   "31.2",  "—",   "—"  ],
            [5, "Helsinki-NLP/opus-mt-en-ja",       "22.4",  "—",    "—",    "—",   "22.4",  "—"  ],
        ],
    },
    "vlm-mmmu": {
        "title": "Open Vision-Language Leaderboard (MMMU)",
        "emoji": "👁️",
        "description": (
            "MMMU benchmark — 11,500 multimodal college-level questions across 30 subjects. Models are "
            "evaluated with the standard 5-shot CoT protocol."
        ),
        "tags": ["image-text-to-text", "multimodal", "benchmark"],
        "columns": ["Rank", "Model", "Avg", "Art", "Business", "Health", "Humanities", "Science", "Tech"],
        "rows": [
            [1, "Qwen/Qwen2-VL-72B-Instruct",       "65.4", "68.2", "62.4", "70.9", "61.5", "60.2", "72.4"],
            [2, "google/paligemma-3b-mix-448",      "47.8", "52.0", "44.1", "55.7", "44.3", "42.5", "50.3"],
            [3, "microsoft/Florence-2-large",       "44.2", "48.6", "41.3", "52.4", "40.9", "39.1", "46.7"],
        ],
    },
}


# ---------------------------------------------------------------------------
# Pricing plan deep pages — slug-keyed long copy.
# ---------------------------------------------------------------------------
PRICING_PLAN_DETAILS = {
    "free":   {"slug": "free",   "name": "HF Hub",          "price": "Free",   "cadence": "forever",
               "tagline": "For individuals, hobbyists, and open-source projects.",
               "blurb": (
                   "Get unlimited public models, datasets and Spaces. Push code via Git+LFS, share notebooks, "
                   "deploy CPU Spaces and use the free-tier Inference API. Perfect for learning and open research."
               )},
    "pro":    {"slug": "pro",    "name": "PRO Account",     "price": "$9",     "cadence": "per month",
               "tagline": "For power users who need more.",
               "blurb": (
                   "Everything in Free, plus priority ZeroGPU quota, private models and datasets, and higher "
                   "Inference API rate limits. A PRO badge is added to your profile so the community can find you."
               )},
    "enterprise": {"slug": "enterprise", "name": "Enterprise Hub", "price": "$20", "cadence": "per user/month",
               "tagline": "For teams and organizations shipping ML in production.",
               "blurb": (
                   "SSO/SAML, audit logs, SOC2 Type II compliance, dedicated regional inference endpoints, "
                   "and a direct support line. Optional bring-your-own-cloud deployments on AWS, GCP or Azure."
               )},
}



# ---------------------------------------------------------------------------
# Hugging Face Classroom benefits.
# ---------------------------------------------------------------------------
CLASSROOM_BENEFITS = [
    "Free access to Hugging Face courses, including the Transformers, Diffusion Models and Reinforcement Learning courses.",
    "Dedicated teacher dashboards for managing up to 200 students with assignment tracking.",
    "Free organization-level private Spaces and datasets for assignments and projects.",
    "Higher ZeroGPU priority so students can run demos without hitting capacity limits.",
    "Integration with Jupyter and Colab for interactive lectures and hands-on labs.",
    "Certification program — students who complete the course receive a signed Hugging Face certificate.",
    "Community support channel with direct access to Hugging Face engineers and educators.",
    "Curriculum templates covering NLP, Computer Vision, Audio, Reinforcement Learning and Agentic workflows.",
]


# ---------------------------------------------------------------------------
# Pricing plans.
# ---------------------------------------------------------------------------
PRICING_PLANS = [
    {
        "name": "HF Hub",
        "price": "Free",
        "cadence": "forever",
        "tagline": "For individuals, hobbyists, and open-source projects.",
        "features": [
            "Unlimited public models, datasets and Spaces",
            "Community support",
            "Inference API (free tier)",
            "Git-based version control with LFS",
            "CPU Spaces at no cost",
        ],
    },
    {
        "name": "PRO Account",
        "price": "$9",
        "cadence": "per month",
        "tagline": "For power users who need more.",
        "features": [
            "Everything in Free, plus:",
            "ZeroGPU priority quota — higher throughput on community Spaces",
            "Private models and datasets (with unlimited storage)",
            "Early access to new Hub features and experimental APIs",
            "PRO badge on your profile",
            "Higher Inference API rate limits",
            "Access to PRO-only Spaces",
        ],
    },
    {
        "name": "Enterprise Hub",
        "price": "$20",
        "cadence": "per user/month",
        "tagline": "For teams and organizations shipping ML in production.",
        "features": [
            "Everything in PRO, plus:",
            "SSO, SAML and audit logs",
            "SOC2 Type II compliance",
            "Private Spaces with dedicated hardware",
            "Resource groups and role-based access control",
            "Dedicated support with SLAs",
            "Custom inference regions (EU, US, APAC)",
            "Bring-your-own-cloud (AWS, GCP, Azure) deployments",
        ],
    },
]


# ---------------------------------------------------------------------------
# Dataset viewer rows — hand-crafted for the ai2lumos dataset task.
# ---------------------------------------------------------------------------
DATASET_VIEWER_DATA = {
    "ai2lumos/lumos_complex_qa_plan_onetime": {
        "columns": ["id", "messages"],
        "rows": [
            [0,
             '[{"role": "user", "content": "Please answer the following complex question: Which actor who played in the 2005 film \'Pride & Prejudice\' was born in the same country as the director of \'Atonement\'? Break down your reasoning into subgoals and solve them step by step."}, '
             '{"role": "assistant", "content": "Subgoal 1: Identify the director of \'Atonement\'. Subgoal 2: Determine the country of birth of that director. Subgoal 3: List the main actors in \'Pride & Prejudice\' (2005). Subgoal 4: Find the actor whose birth country matches the director\'s."}]'
            ],
            [1,
             '[{"role": "user", "content": "Which U.S. president signed the bill that created the national park where the Old Faithful geyser is located?"}, '
             '{"role": "assistant", "content": "Subgoal 1: Identify the national park containing Old Faithful. Subgoal 2: Find when that park was established. Subgoal 3: Identify the U.S. president at that time."}]'
            ],
            [2,
             '[{"role": "user", "content": "Can you plan the steps for the following multi-hop question?"}, '
             '{"role": "assistant", "content": "Sure — here is a step-by-step plan using subgoal decomposition."}]'
            ],
        ],
    },
}
