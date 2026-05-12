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
]


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
