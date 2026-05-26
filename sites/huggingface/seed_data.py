"""
Phase 4: Seed Data for HuggingFace mirror.
Populates Tasks, Authors, and Repositories (models/datasets/spaces).
"""
import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent


# ------------------------------------------------------------
# 1) Task taxonomy (55+ tasks grouped by modality)
# ------------------------------------------------------------
TASKS = [
    # (slug, display, modality, icon, description)
    # Multimodal
    ("any-to-any",              "Any-to-Any",               "Multimodal",           "🔀",  "Unified models handling inputs and outputs across modalities."),
    ("audio-text-to-text",      "Audio-Text-to-Text",       "Multimodal",           "🎤",  "Combine audio and text prompts to generate text responses."),
    ("document-question-answering", "Document Question Answering", "Multimodal",  "📄",  "Ask questions over scanned documents or PDFs."),
    ("visual-document-retrieval", "Visual Document Retrieval", "Multimodal",       "🔎",  "Retrieve documents by matching visual and textual signals."),
    ("image-text-to-text",      "Image-Text-to-Text",       "Multimodal",           "🖼️", "Multimodal models that consume image + text and output text."),
    ("visual-question-answering","Visual Question Answering","Multimodal",          "❓",  "Answer questions grounded in the content of an image."),
    # NLP
    ("feature-extraction",      "Feature Extraction",       "Natural Language Processing", "🧬", "Extract dense representations from text for downstream tasks."),
    ("fill-mask",               "Fill-Mask",                "Natural Language Processing", "📝", "Predict missing tokens in a masked sentence."),
    ("question-answering",      "Question Answering",       "Natural Language Processing", "💬", "Answer questions against a given context passage."),
    ("sentence-similarity",     "Sentence Similarity",      "Natural Language Processing", "🧮", "Score semantic similarity between sentences."),
    ("summarization",           "Summarization",            "Natural Language Processing", "✂️", "Condense documents into concise summaries."),
    ("table-question-answering","Table Question Answering", "Natural Language Processing", "📊", "Answer natural-language questions against tabular data."),
    ("text-classification",     "Text Classification",      "Natural Language Processing", "🏷️", "Assign labels like sentiment or topic to text."),
    ("text-generation",         "Text Generation",          "Natural Language Processing", "✍️", "Autoregressive models that produce coherent text."),
    ("text-ranking",            "Text Ranking",             "Natural Language Processing", "📈", "Rank candidate passages by relevance to a query."),
    ("token-classification",    "Token Classification",     "Natural Language Processing", "🔖", "Per-token labels such as named entities or parts of speech."),
    ("translation",             "Translation",              "Natural Language Processing", "🌐", "Translate text between languages."),
    ("zero-shot-classification","Zero-Shot Classification", "Natural Language Processing", "🎯", "Classify text against arbitrary labels without training."),
    # Computer Vision
    ("depth-estimation",        "Depth Estimation",         "Computer Vision",       "🗺️", "Predict per-pixel depth from monocular images."),
    ("image-classification",    "Image Classification",     "Computer Vision",       "🖼️", "Assign a label to an entire image."),
    ("image-feature-extraction","Image Feature Extraction", "Computer Vision",       "🔬", "Extract embeddings from images for retrieval or similarity."),
    ("image-segmentation",      "Image Segmentation",       "Computer Vision",       "🧩", "Predict a label for every pixel in an image."),
    ("image-to-image",          "Image-to-Image",           "Computer Vision",       "🔄", "Translate an input image into another image."),
    ("image-to-text",           "Image-to-Text",            "Computer Vision",       "📖", "Generate textual descriptions of images."),
    ("image-to-video",          "Image-to-Video",           "Computer Vision",       "🎬", "Turn a single image into a short video."),
    ("object-detection",        "Object Detection",         "Computer Vision",       "📦", "Locate and classify objects within images."),
    ("text-to-image",           "Text-to-Image",            "Computer Vision",       "🎨", "Generate images from text prompts."),
    ("text-to-video",           "Text-to-Video",            "Computer Vision",       "🎥", "Generate short videos from text prompts."),
    ("unconditional-image-generation", "Unconditional Image Generation", "Computer Vision", "🌀", "Sample images unconditionally from a learned distribution."),
    ("zero-shot-image-classification", "Zero-Shot Image Classification", "Computer Vision", "🎯", "Classify images without task-specific training."),
    ("text-to-3d",              "Text-to-3D",               "Computer Vision",       "🧊",  "Generate 3D assets from text prompts."),
    ("image-to-3d",             "Image-to-3D",              "Computer Vision",       "📐",  "Reconstruct 3D geometry from a single image."),
    # Audio
    ("audio-classification",    "Audio Classification",     "Audio",                 "🔊",  "Classify sound events, speakers, or music genres."),
    ("audio-to-audio",          "Audio-to-Audio",           "Audio",                 "🎧",  "Transform audio — enhancement, source separation."),
    ("automatic-speech-recognition", "Automatic Speech Recognition", "Audio",       "🗣️", "Transcribe spoken audio into text."),
    ("text-to-speech",          "Text-to-Speech",           "Audio",                 "🔈",  "Synthesize speech from input text."),
    # Tabular
    ("tabular-classification",  "Tabular Classification",   "Tabular",               "📋",  "Classify rows of structured tabular data."),
    ("tabular-regression",      "Tabular Regression",       "Tabular",               "📉",  "Predict continuous targets from tabular features."),
    # RL
    ("reinforcement-learning",  "Reinforcement Learning",   "Reinforcement Learning","🕹️", "Agents that learn from environmental rewards."),
]

MODALITIES = ["Multimodal", "Natural Language Processing", "Computer Vision", "Audio", "Tabular", "Reinforcement Learning"]

# ------------------------------------------------------------
# 2) Library options
# ------------------------------------------------------------
LIBRARIES = [
    "Transformers", "Diffusers", "Safetensors", "PyTorch", "TensorFlow",
    "JAX", "ONNX", "GGUF", "sentence-transformers", "Transformers.js",
    "MLX", "PEFT", "timm", "Keras", "Flax", "PaddlePaddle",
]

LICENSES = [
    ("apache-2.0", "Apache 2.0"),
    ("mit", "MIT"),
    ("cc-by-4.0", "CC BY 4.0"),
    ("cc-by-sa-4.0", "CC BY-SA 4.0"),
    ("cc-by-nc-4.0", "CC BY-NC 4.0"),
    ("openrail", "OpenRAIL"),
    ("creativeml-openrail-m", "CreativeML OpenRAIL-M"),
    ("llama-3.3", "Llama 3.3 Community"),
    ("gemma", "Gemma"),
    ("bsd-3-clause", "BSD 3-Clause"),
    ("gpl-3.0", "GPL-3.0"),
    ("other", "Other"),
]

LANGUAGES = ["English", "Multilingual", "Chinese", "Spanish", "French", "German", "Japanese", "Korean", "Arabic", "Portuguese"]

SPACE_SDKS = ["gradio", "streamlit", "docker", "static"]
SPACE_HARDWARE = [
    ("cpu-basic",   "CPU Basic",      "2 vCPU · 16GB",   "free"),
    ("cpu-upgrade", "CPU Upgrade",    "8 vCPU · 32GB",   "$0.03/hr"),
    ("t4-small",    "Nvidia T4",      "4 vCPU · 15GB · T4 (16GB)",  "$0.40/hr"),
    ("l4x1",        "Nvidia L4",      "8 vCPU · 30GB · L4 (24GB)",  "$0.80/hr"),
    ("l40sx1",      "Nvidia L40S",    "8 vCPU · 62GB · L40S (48GB)","$1.80/hr"),
    ("a100-large",  "Nvidia A100",    "12 vCPU · 142GB · A100 (80GB)", "$2.50/hr"),
    ("zero-gpu",    "ZeroGPU",        "dynamic · H200 (70GB)",     "free"),
]

INFERENCE_PROVIDERS = ["HF Inference", "Together AI", "Groq", "Novita", "SambaNova", "Hyperbolic", "Cerebras", "fal", "Nscale", "Replicate"]

# ------------------------------------------------------------
# 3) Authors / Organizations (from scraped data + curated)
# ------------------------------------------------------------
AUTHORS = [
    # (username, display, kind, bio, followers, is_verified, website)
    ("huggingface",   "Hugging Face",      "org",  "The home of machine learning. We build the platform where the ML community collaborates on models, datasets, and applications.", 52183, True,  "https://huggingface.co"),
    ("google",        "Google",            "org",  "Research from Google's machine learning teams: Gemma, T5, BERT, Flan, PaLI and more.", 50781, True,  "https://ai.google"),
    ("meta-llama",    "Meta Llama",        "org",  "Meta's family of open foundation models: Llama, Code Llama, and multimodal Llama variants.", 78293, True,  "https://llama.meta.com"),
    ("microsoft",     "Microsoft",         "org",  "Research and production models from Microsoft — Phi, GraphormerT, BioGPT, DeBERTa and more.", 19438, True,  "https://microsoft.com/research"),
    ("openai",        "OpenAI",            "org",  "Whisper, CLIP, Jukebox, Point-E and other open-source contributions from OpenAI.", 62910, True,  "https://openai.com"),
    ("stabilityai",   "Stability AI",      "org",  "Generative models for images, video, audio and 3D: Stable Diffusion, Stable Video Diffusion, and more.", 34201, True,  "https://stability.ai"),
    ("mistralai",     "Mistral AI",        "org",  "Open-weight European LLMs: Mistral 7B, Mixtral 8x7B, Codestral and more.", 29584, True,  "https://mistral.ai"),
    ("nvidia",        "NVIDIA",            "org",  "Hardware-optimized models, embeddings, and NVFP4 quantized releases.", 15102, True,  "https://nvidia.com/research"),
    ("anthropic",     "Anthropic",         "org",  "Research organization focused on building reliable, interpretable AI systems.", 8321,  True,  "https://anthropic.com"),
    ("bigcode",       "BigCode",           "org",  "A collaborative project for the responsible development of code LLMs — StarCoder and friends.", 9104,  True,  "https://bigcode-project.org"),
    ("eleutherai",    "EleutherAI",        "org",  "Grassroots research collective behind GPT-Neo, Pythia, and many open-source evaluation tools.", 11203, True,  "https://eleuther.ai"),
    ("tiiuae",        "Technology Innovation Institute", "org", "Research organization behind Falcon, Noor, and other Arabic-first LLMs.", 6302,  True,  "https://tii.ae"),
    ("Qwen",          "Qwen",              "org",  "Alibaba's open-source model family — Qwen, Qwen2, Qwen2.5 and beyond.", 21458, True,  "https://qwenlm.github.io"),
    ("deepseek-ai",   "DeepSeek",          "org",  "DeepSeek LLM, DeepSeek-Coder, DeepSeek-V3, DeepSeek-R1 and more.", 18520, True,  "https://deepseek.com"),
    ("intfloat",      "IntFloat",          "user", "Embeddings wizard — e5, multilingual-e5, gte and related retrieval models.", 5280,  False, ""),
    ("sentence-transformers", "Sentence Transformers", "org", "Pretrained sentence encoders and cross-encoders ready for semantic search.", 8712,  True,  "https://sbert.net"),
    ("openbmb",       "OpenBMB",           "org",  "Open-source Big Models — MiniCPM, VoxCPM and more.", 4812,  True,  "https://openbmb.ai"),
    ("baai",          "BAAI",              "org",  "Beijing Academy of Artificial Intelligence — AquilaChat, BGE embeddings, and Emu models.", 6103,  True,  "https://baai.ac.cn"),
    ("facebook",      "Facebook AI",       "org",  "FAIR's legacy releases: BART, RoBERTa, XLM, DINO and more.", 25102, True,  "https://ai.meta.com"),
    ("laion",         "LAION",             "org",  "Large-scale open datasets powering the next wave of generative AI.", 9832,  True,  "https://laion.ai"),
    ("cohereforai",   "Cohere For AI",     "org",  "Cohere's non-profit research lab building multilingual and open science resources.", 4320,  True,  "https://cohere.for.ai"),
    ("Salesforce",    "Salesforce",        "org",  "XGen, BLIP, Einstein foundation models and enterprise-ready vision/text tooling.", 6421,  True,  "https://einstein.ai"),
    ("unsloth",       "Unsloth AI",        "org",  "Finetuning library plus pre-quantized models for the whole open-source community.", 3902,  True,  "https://unsloth.ai"),
    ("TheBloke",      "TheBloke",          "user", "Quantized GGUF builds of virtually every popular open-source LLM.", 28103, False, ""),
    ("bert-base",     "BERT Base",         "user", "Community mirror of the classic BERT base models.", 1203,  False, ""),
    ("naver",         "Naver",             "org",  "Korean AI research — HyperCLOVA and multilingual search models.", 2103,  True,  "https://clova.ai"),
    ("netflix",       "Netflix",           "org",  "Recommendation and representation models for streaming workloads.", 1402,  True,  "https://research.netflix.com"),
    ("tencent",       "Tencent",           "org",  "HY-OmniWeaving, Hunyuan models, and multimodal experiments from Tencent AI Lab.", 2901,  True,  "https://ai.tencent.com"),
    ("nlpcloud",      "NLP Cloud",         "org",  "Production-ready NLP endpoints — classification, generation, NER.", 821,   False, ""),
    ("ByteDance",     "ByteDance",         "org",  "Models from ByteDance's research teams powering TikTok and beyond.", 3104,  True,  "https://bytedance.com"),
    ("XuehangCang",   "Xuehang Cang",      "user", "Independent researcher releasing experimental fine-tunes.", 412,   False, ""),
    ("prithivMLmods", "Prithiv MLmods",    "user", "Prolific fine-tuner behind dozens of Spaces and quantized models.", 5120,  False, ""),
    ("lmsys",         "LMSYS",             "org",  "Large Model Systems Org — Vicuna, Arena evaluations, and open judging pipelines.", 7210,  True,  "https://lmsys.org"),
    ("allenai",       "Allen AI",          "org",  "AI2 — OLMo, Longformer, and fully open-source language model pipelines.", 8401,  True,  "https://allenai.org"),
    ("databricks",    "Databricks",        "org",  "Dolly, DBRX and the open-source enterprise data intelligence stack.", 6503,  True,  "https://databricks.com"),
    ("mosaicml",      "MosaicML",          "org",  "MPT series and high-throughput training toolkits.", 3910,  True,  "https://mosaicml.com"),
    ("internlm",      "InternLM",          "org",  "Shanghai AI Lab's InternLM and related multimodal checkpoints.", 4812,  True,  "https://internlm.org"),
    ("timm-official", "timm",              "org",  "The canonical PyTorch image models library.", 9120,  True,  "https://github.com/huggingface/pytorch-image-models"),
    ("argilla",        "Argilla",            "org",  "Open-source data curation platform for LLMs. Notux, distilabel, and data quality tools.", 3204, True, "https://argilla.io"),
    ("dreamfusion-ai", "DreamFusion AI",     "org",  "Text-to-3D generation using 2D diffusion priors. DreamFusion and related 3D generation models.", 1820, False, ""),
    ("Helsinki-NLP",   "Helsinki NLP",       "org",  "University of Helsinki NLP group. OPUS-MT multilingual translation models.", 4510, True, "https://blogs.helsinki.fi/language-technology/"),
    ("grammarly",      "Grammarly",          "org",  "AI writing assistant. CoEdIt text editing and error correction models.", 2810, True, "https://grammarly.com"),
    ("PaddlePaddle",   "PaddlePaddle",       "org",  "Baidu's open-source deep learning platform. ERNIE, PaddleNLP, and PaddleOCR models.", 5120, True, "https://paddlepaddle.org.cn"),
    ("GanjinZero",     "GanjinZero",         "user", "Biomedical NLP researcher. BioBART and medical text models.", 820, False, ""),
    ("traveller-ai",   "Traveller AI",       "user", "Travel domain AI models and chat assistants.", 340, False, ""),
    ("ai2lumos",       "AI2 Lumos",          "org",  "Allen AI's Lumos project for complex reasoning and planning.", 1200, False, ""),
    ("flax-community", "Flax Community",     "org",  "Community-driven models built with JAX/Flax.", 2100, False, ""),
    ("GonzaloA",       "GonzaloA",           "user", "NLP researcher focused on misinformation detection.", 520, False, ""),
    ("deepset",        "deepset",            "org",  "NLP for enterprise — Haystack framework and fine-tuned QA models.", 4200, True, "https://deepset.ai"),
    ("Jean-Baptiste",  "Jean-Baptiste",      "user", "French NLP researcher. CamemBERT NER and French language models.", 1100, False, ""),
    ("elastic",        "Elastic",            "org",  "Search and observability. NLP models for Elasticsearch integration.", 3200, True, "https://elastic.co"),
    ("HuggingFaceH4",  "Hugging Face H4",    "org",  "Hugging Face alignment team — Zephyr, UltraChat, and RLHF experiments.", 12500, True, "https://huggingface.co"),
    ("bigscience",     "BigScience",         "org",  "BigScience workshop — BLOOM, T0, and large-scale collaborative research.", 8200, True, ""),
    ("black-forest-labs","Black Forest Labs", "org",  "FLUX.1 and next-gen image generation models.", 6800, True, "https://blackforestlabs.ai"),
]


# ------------------------------------------------------------
# 4) Model descriptions — rich enough for detail pages
# ------------------------------------------------------------
MODEL_DESCRIPTIONS = {
    "text-generation": [
        "A state-of-the-art autoregressive language model for dialogue, instruction-following, and long-form writing. Instruction-tuned on high-quality preference data with RLHF.",
        "Dense transformer language model trained on a carefully filtered mixture of web text, code, and academic corpora. Excellent zero-shot reasoning and chat.",
        "Quantized build optimized for local inference via llama.cpp / Ollama. Preserves most benchmark performance at a fraction of the memory footprint.",
        "Mixture-of-experts transformer with 8 experts per layer and sparse routing. High effective capacity at modest active parameter count.",
        "Multilingual chat model supporting 20+ languages with strong code, math, and agent-style tool use capabilities.",
    ],
    "text-to-image": [
        "Latent diffusion model trained on a curated multi-billion image dataset. Supports classifier-free guidance and text-conditioned generation at up to 2048×2048.",
        "Rectified-flow image generator with a dual transformer backbone. Excellent prompt adherence, photorealism, and typography rendering.",
        "Fine-tuned LoRA adapter specialized for anime-style illustration on a strong base model.",
        "Compact text-to-image model distilled from a larger teacher. Single-step sampling for real-time generation on consumer GPUs.",
    ],
    "image-text-to-text": [
        "Multimodal model that accepts interleaved image and text tokens and produces grounded natural-language responses. Strong on document QA and diagram reasoning.",
        "Vision-language model built on a SigLIP image encoder and a strong open-source LLM decoder. Finetuned on 3M multimodal conversations.",
    ],
    "automatic-speech-recognition": [
        "Large-scale multilingual speech recognition model trained on 680K hours of multilingual and multitask supervised data collected from the web.",
        "Streaming ASR model with Conformer encoder and transducer decoder. Sub-second end-to-end latency on edge devices.",
    ],
    "text-to-speech": [
        "Neural text-to-speech model based on VITS-style end-to-end synthesis. Supports speaker conditioning and expressive prosody control.",
        "Flow-matching based TTS producing natural 24 kHz audio with speaker identity preserved across languages.",
    ],
    "image-classification": [
        "Vision transformer pretrained on ImageNet-21k and fine-tuned on ImageNet-1k. State-of-the-art top-1 accuracy at the base scale.",
        "ConvNeXt model family — modernized ConvNets that match transformer accuracy with CNN-style efficiency.",
    ],
    "object-detection": [
        "DETR-style end-to-end object detector with learnable queries and bipartite matching loss. No anchors, no NMS.",
        "YOLO variant fine-tuned for small-object detection on aerial imagery. COCO-style format.",
    ],
    "feature-extraction": [
        "Sentence embedding model trained with contrastive loss on 1B pairs. Top performer on MTEB retrieval and clustering benchmarks.",
        "Dense passage retrieval model producing 1024-dim embeddings suitable for semantic search over billions of documents.",
    ],
    "image-segmentation": [
        "Mask2Former universal segmentation model — instance, semantic, and panoptic segmentation with a unified architecture.",
    ],
    "translation": [
        "Multilingual neural machine translation model covering 200+ languages with a single encoder-decoder.",
    ],
    "summarization": [
        "BART-large fine-tuned on CNN/DailyMail. Abstractive summarization with coverage loss for factual consistency.",
    ],
    "question-answering": [
        "Extractive QA model fine-tuned on SQuAD. Span-level predictions with confidence scores.",
    ],
    "image-to-video": [
        "State-of-the-art image-to-video diffusion model. Key features include temporal consistency, high-resolution output, and configurable motion strength. Generates short video clips from a single image.",
    ],
    "text-to-3d": [
        "Text-to-3D generation model using score distillation sampling with 2D diffusion priors. Key features include NeRF-based optimization, multi-view consistency, and mesh export support.",
    ],
    "default": [
        "High-quality machine learning model hosted on the Hugging Face Hub. See the README for details on training data, evaluation, and intended use.",
    ],
}


DATASET_DESCRIPTIONS = [
    "High-quality text corpus for pretraining language models. Carefully deduplicated and language-filtered.",
    "Multimodal dataset of image-caption pairs sourced from a permissively licensed subset of the web.",
    "Benchmark dataset with train/validation/test splits designed for evaluating a specific NLP task.",
    "Instruction-tuning dataset pairing user prompts with high-quality assistant responses.",
    "Reasoning traces dataset — prompts, chains of thought, and final answers for distillation and fine-tuning.",
    "Speech corpus containing thousands of hours of audio and aligned transcripts in multiple languages.",
    "Structured tabular dataset with clean schema, ideal for classical ML and feature engineering experiments.",
    "Video understanding benchmark with multi-second clips and frame-level annotations.",
]


SPACE_DESCRIPTIONS = [
    "Interactive demo running live inference on GPU. Upload your input, tweak parameters, and see results in seconds.",
    "Gradio-powered Space showcasing the latest model capabilities with a clean, configurable UI.",
    "Zero-configuration web app that runs the underlying model on ZeroGPU — free for everyone.",
    "Full-featured playground for exploring the model with example prompts and downloadable outputs.",
    "Community demo built by a contributor — try the model end-to-end without writing any code.",
]


# ------------------------------------------------------------
# 5) Additional curated slugs to fill each task with variety
# ------------------------------------------------------------
CURATED_MODELS = [
    # text-generation — HuggingFace-authored NLP model (most recently updated)
    ("huggingface/SmolLM2-1.7B-Instruct",              "text-generation",  "Transformers", 1.7, True),
    # text-generation
    ("meta-llama/Llama-3.3-70B-Instruct",           "text-generation",  "Transformers", 70, True),
    ("meta-llama/Llama-3.2-3B-Instruct",            "text-generation",  "Transformers", 3,  True),
    ("meta-llama/Llama-3.2-1B-Instruct",            "text-generation",  "Transformers", 1,  True),
    ("mistralai/Mistral-7B-Instruct-v0.3",          "text-generation",  "Transformers", 7,  True),
    ("mistralai/Mixtral-8x7B-Instruct-v0.1",        "text-generation",  "Transformers", 47, True),
    ("google/gemma-2-9b-it",                        "text-generation",  "Transformers", 9,  True),
    ("google/gemma-2-27b-it",                       "text-generation",  "Transformers", 27, True),
    ("Qwen/Qwen2.5-7B-Instruct",                    "text-generation",  "Transformers", 7,  True),
    ("Qwen/Qwen2.5-32B-Instruct",                   "text-generation",  "Transformers", 32, True),
    ("Qwen/Qwen2.5-72B-Instruct",                   "text-generation",  "Transformers", 72, True),
    ("deepseek-ai/DeepSeek-V3",                     "text-generation",  "Transformers", 671, True),
    ("deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",    "text-generation",  "Transformers", 32, True),
    ("microsoft/Phi-3.5-mini-instruct",             "text-generation",  "Transformers", 4,  True),
    ("tiiuae/Falcon3-10B-Instruct",                 "text-generation",  "Transformers", 10, True),
    ("allenai/OLMo-2-1124-7B-Instruct",             "text-generation",  "Transformers", 7,  True),
    ("bigcode/starcoder2-15b",                      "text-generation",  "Transformers", 15, False),
    # text-to-image
    ("stabilityai/stable-diffusion-3-medium-diffusers", "text-to-image", "Diffusers",   2,  True),
    ("stabilityai/stable-diffusion-xl-base-1.0",    "text-to-image",    "Diffusers",    3,  True),
    ("black-forest-labs/FLUX.1-dev",                "text-to-image",    "Diffusers",    12, True),
    ("black-forest-labs/FLUX.1-schnell",            "text-to-image",    "Diffusers",    12, True),
    ("stabilityai/stable-cascade",                  "text-to-image",    "Diffusers",    3,  True),
    # automatic-speech-recognition
    ("openai/whisper-large-v3",                     "automatic-speech-recognition", "Transformers", 2,  True),
    ("openai/whisper-small",                        "automatic-speech-recognition", "Transformers", 1,  False),
    ("nvidia/parakeet-tdt-1.1b",                    "automatic-speech-recognition", "Transformers", 1,  True),
    # text-to-speech
    ("coqui/XTTS-v2",                               "text-to-speech",   "Transformers", 1,  True),
    ("microsoft/speecht5_tts",                      "text-to-speech",   "Transformers", 1,  False),
    # image-text-to-text
    ("google/paligemma-3b-mix-448",                 "image-text-to-text", "Transformers", 3, True),
    ("microsoft/Florence-2-large",                  "image-text-to-text", "Transformers", 1, True),
    ("Qwen/Qwen2-VL-72B-Instruct",                  "image-text-to-text", "Transformers", 72, True),
    # image-classification
    ("google/vit-base-patch16-224",                 "image-classification", "Transformers", 0, False),
    ("microsoft/resnet-50",                         "image-classification", "Transformers", 0, False),
    # object-detection
    ("facebook/detr-resnet-50",                     "object-detection", "Transformers", 0, False),
    ("google/owlv2-base-patch16-ensemble",          "object-detection", "Transformers", 0, False),
    # image-segmentation
    ("facebook/sam-vit-huge",                       "image-segmentation", "Transformers", 0, True),
    ("facebook/maskformer-swin-large-ade",          "image-segmentation", "Transformers", 0, False),
    # feature-extraction
    ("sentence-transformers/all-MiniLM-L6-v2",      "feature-extraction", "sentence-transformers", 0, True),
    ("BAAI/bge-large-en-v1.5",                      "feature-extraction", "sentence-transformers", 0, True),
    ("intfloat/multilingual-e5-large",              "feature-extraction", "sentence-transformers", 0, True),
    # fill-mask
    ("google-bert/bert-base-uncased",               "fill-mask",        "Transformers", 0, True),
    ("FacebookAI/roberta-base",                     "fill-mask",        "Transformers", 0, True),
    # translation
    ("facebook/nllb-200-distilled-600M",            "translation",      "Transformers", 1,  True),
    ("Helsinki-NLP/opus-mt-en-de",                  "translation",      "Transformers", 0, False),
    # summarization
    ("facebook/bart-large-cnn",                     "summarization",    "Transformers", 0, True),
    ("google/pegasus-xsum",                         "summarization",    "Transformers", 0, False),
    # question-answering
    ("deepset/roberta-base-squad2",                 "question-answering", "Transformers", 0, True),
    # text-classification
    ("cardiffnlp/twitter-roberta-base-sentiment",   "text-classification", "Transformers", 0, False),
    ("distilbert/distilbert-base-uncased-finetuned-sst-2-english", "text-classification", "Transformers", 0, False),
    # token-classification
    ("dslim/bert-base-NER",                         "token-classification", "Transformers", 0, False),
    # audio-classification
    ("MIT/ast-finetuned-audioset-10-10-0.4593",     "audio-classification", "Transformers", 0, False),
    # depth-estimation
    ("depth-anything/Depth-Anything-V2-Large",      "depth-estimation", "Transformers", 0, True),
    # reinforcement-learning
    ("sb3/ppo-LunarLander-v2",                      "reinforcement-learning", "stable-baselines3", 0, False),
    # text-to-video
    ("genmo/mochi-1-preview",                       "text-to-video",    "Diffusers",    10, True),
    # image-to-3d
    ("stabilityai/stable-zero123",                  "image-to-3d",      "Diffusers",    1,  False),
    # zero-shot classification
    ("facebook/bart-large-mnli",                    "zero-shot-classification", "Transformers", 0, True),
    # sentence similarity
    ("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", "sentence-similarity", "sentence-transformers", 0, False),
    # image-to-image
    ("timbrooks/instruct-pix2pix",                  "image-to-image", "Diffusers", 1, True),
    # image-to-video (HF--11)
    ("stabilityai/stable-video-diffusion-xt-2",     "image-to-video", "Diffusers", 2, True),
    ("stabilityai/stable-video-diffusion-img2vid-xt","image-to-video", "Diffusers", 2, False),
    ("genmo/mochi-1-image2video",                   "image-to-video", "Diffusers", 5, False),
    # text-to-3d (HF--41)
    ("dreamfusion-ai/dreamfusion-sd-v1",            "text-to-3d", "Diffusers", 1, True),
    ("dreamfusion-ai/dreamfusion-if-v2",            "text-to-3d", "Diffusers", 1, False),
    ("openai/shap-e",                               "text-to-3d", "Diffusers", 1, False),
]


# Task-driven models with special attributes (updated dates, languages, etc.)
# Each: (slug, task, library, params_b, is_featured, overrides_dict)
TASK_DRIVEN_MODELS = [
    # HF--0: sentiment analysis models updated March 2023
    ("cardiffnlp/twitter-xlm-roberta-base-sentiment-latest", "text-classification", "Transformers", 0, True,
     {"updated_days_ago_override": None, "updated_at_fixed": "2023-03-15",
      "license": "apache-2.0", "license_display": "Apache 2.0",
      "description": "Sentiment analysis model based on XLM-RoBERTa, fine-tuned for Twitter sentiment classification. Supports multilingual sentiment detection.",
      "tags_extra": ["sentiment", "sentiment-analysis", "twitter"]}),
    ("nlptown/bert-base-multilingual-uncased-sentiment", "text-classification", "Transformers", 0, False,
     {"updated_at_fixed": "2023-03-20",
      "description": "Multilingual BERT model for sentiment analysis, classifying product reviews into 1-5 stars. Fine-tuned on 100k reviews.",
      "tags_extra": ["sentiment", "sentiment-analysis"]}),
    ("lxyuan/distilbert-base-multilingual-cased-sentiments-student", "text-classification", "Transformers", 0, False,
     {"updated_at_fixed": "2023-03-12",
      "description": "DistilBERT-based multilingual sentiment classifier. Fast inference for sentiment analysis tasks.",
      "tags_extra": ["sentiment", "sentiment-analysis"]}),

    # HF--1: dragon/wizard text generation
    ("HuggingFaceH4/zephyr-7b-story-dragon-wizard", "text-generation", "Transformers", 7, True,
     {"description": "Zephyr 7B fine-tuned for creative story generation. This model excels at writing dragon and wizard fantasy stories. Generates vivid narratives with dragon encounters and wizard adventures.",
      "tags_extra": ["dragon", "wizard", "story", "creative-writing"],
      "readme_extra": "## Example\nGenerate a story about a dragon and a wizard who embark on a quest together."}),

    # HF--2: translation models updated March 2026
    ("Helsinki-NLP/opus-mt-en-fr-2026", "translation", "Transformers", 0, False,
     {"updated_at_fixed": "2026-03-10",
      "description": "English-French neural machine translation model. Updated March 2026 with improved BLEU scores.",
      "tags_extra": ["translation", "en-fr"]}),
    ("Helsinki-NLP/opus-mt-en-de-2026", "translation", "Transformers", 0, False,
     {"updated_at_fixed": "2026-03-12",
      "description": "English-German translation model updated for 2026 with better handling of compound nouns.",
      "tags_extra": ["translation", "en-de"]}),
    ("Helsinki-NLP/opus-mt-en-es-2026", "translation", "Transformers", 0, False,
     {"updated_at_fixed": "2026-03-15",
      "description": "English-Spanish translation model refreshed in March 2026.",
      "tags_extra": ["translation", "en-es"]}),

    # HF--9: opus-mt-en-ja with metrics
    ("Helsinki-NLP/opus-mt-en-ja", "translation", "Transformers", 0, True,
     {"description": "English to Japanese (en-ja) neural machine translation model from the OPUS-MT project. Achieves strong BLEU and chrF scores on FLORES benchmark.",
      "readme_extra": "## Evaluation\n\nBenchmark metrics on the FLORES-101 test set:\n\n| Metric | Score |\n|--------|-------|\n| BLEU   | 22.4  |\n| chrF   | 48.7  |\n| chrF++ | 47.2  |\n\nTested against FLORES evaluation suite.",
      "tags_extra": ["translation", "en-ja", "opus-mt", "japanese"]}),

    # HF--12: error correction model
    ("grammarly/coedit-large", "text-generation", "Transformers", 0.77, True,
     {"description": "CoEdIt: Text Editing by Task-Specific Instruction Tuning. Error correction, grammar fixing, paraphrasing, and text simplification model.",
      "tags_extra": ["coedit", "error-correction", "grammar", "editing"],
      "readme_extra": "## Usage\nCoEdIt performs grammatical error correction and text editing tasks."}),
    ("grammarly/coedit-xl", "text-generation", "Transformers", 3, False,
     {"description": "CoEdIt-XL: Larger version of the error correction and text editing model. Grammar correction and coherence improvement.",
      "tags_extra": ["coedit", "error-correction", "grammar"]}),

    # HF--15: PaddlePaddle models
    ("PaddlePaddle/ernie-3.0-base-zh", "text-classification", "PaddlePaddle", 0.11, True,
     {"description": "ERNIE 3.0 base model for Chinese NLP tasks. Built with PaddlePaddle framework.",
      "library": "PaddlePaddle",
      "tags_extra": ["paddle", "paddlepaddle", "ernie", "chinese"]}),
    ("PaddlePaddle/uie-base", "token-classification", "PaddlePaddle", 0.11, False,
     {"description": "Universal Information Extraction model built with PaddlePaddle. Entity recognition and relation extraction.",
      "library": "PaddlePaddle",
      "tags_extra": ["paddle", "paddlepaddle", "uie"]}),
    ("PaddlePaddle/ernie-tiny", "text-classification", "PaddlePaddle", 0.05, False,
     {"description": "Compact ERNIE model for efficient inference, built with PaddlePaddle.",
      "library": "PaddlePaddle",
      "tags_extra": ["paddle", "paddlepaddle"]}),

    # HF--19: English summarization model updated recently
    ("facebook/bart-large-cnn-2026", "summarization", "Transformers", 0.4, True,
     {"updated_at_fixed": "2026-03-20", "language": "English",
      "description": "BART-Large fine-tuned on CNN/DailyMail for English summarization. Updated 2026 with improved features and evaluation.",
      "readme_extra": "## Features\n\nThis English summarization model provides abstractive summaries of news articles.",
      "tags_extra": ["summarization", "english", "bart", "cnn"]}),

    # HF--20: NER model updated 2022 with 1M+ downloads
    ("Jean-Baptiste/camembert-ner", "token-classification", "Transformers", 0.11, False,
     {"updated_at_fixed": "2022-06-15", "downloads": 2_500_000,
      "description": "CamemBERT-based NER model for French named entity recognition. Updated 2022. Over 2.5M downloads.",
      "tags_extra": ["ner", "named-entity-recognition", "camembert"]}),
    ("dslim/bert-base-NER-2022", "token-classification", "Transformers", 0.11, False,
     {"updated_at_fixed": "2022-09-01", "downloads": 3_800_000,
      "description": "BERT-based NER model updated in 2022. Named entity recognition for English text. Over 3M downloads.",
      "tags_extra": ["ner", "named-entity-recognition", "bert"]}),
    ("elastic/distilbert-base-cased-finetuned-conll03-english-ner-2022", "token-classification", "Transformers", 0.07, False,
     {"updated_at_fixed": "2022-04-15", "downloads": 1_200_000,
      "description": "DistilBERT fine-tuned for NER on CoNLL-03 English. Updated 2022. NER tagging with high accuracy.",
      "tags_extra": ["ner", "named-entity-recognition", "distilbert", "conll"]}),

    # HF--23: ASR models updated March 2026 (need 3 total, already 1 might match)
    ("openai/whisper-large-v3-turbo-2026", "automatic-speech-recognition", "Transformers", 1, True,
     {"updated_at_fixed": "2026-03-05",
      "description": "Whisper Large V3 Turbo — faster inference ASR model. Updated March 2026 with improved accuracy.",
      "tags_extra": ["whisper", "asr", "speech"]}),
    ("nvidia/parakeet-ctc-1.1b-2026", "automatic-speech-recognition", "Transformers", 1.1, False,
     {"updated_at_fixed": "2026-03-18",
      "description": "Parakeet CTC 1.1B ASR model updated March 2026. State-of-the-art speech recognition.",
      "tags_extra": ["parakeet", "asr", "speech"]}),
    ("facebook/seamless-m4t-v2-large-2026", "automatic-speech-recognition", "Transformers", 2.3, False,
     {"updated_at_fixed": "2026-03-22",
      "description": "SeamlessM4T v2 Large for multilingual ASR and translation. Updated March 2026.",
      "tags_extra": ["seamless", "asr", "speech", "multilingual"]}),

    # HF--28: multilingual QA
    ("deepset/xlm-roberta-large-squad2-multilingual", "question-answering", "Transformers", 0.56, True,
     {"language": "Multilingual",
      "description": "XLM-RoBERTa Large fine-tuned on SQuAD v2 for multilingual question answering. Supports English, French, German, Chinese, Spanish, and more.",
      "readme_extra": "## Supported Languages\n\nThis model supports question answering in English, French, German, Chinese, Spanish, Japanese, Korean, and Arabic.",
      "tags_extra": ["qa", "multilingual", "squad", "xlm-roberta"]}),

    # HF--29: medical summarization
    ("GanjinZero/biobart-v2-large", "summarization", "Transformers", 0.4, True,
     {"description": "BioBART v2 Large for medical text summarization. Fine-tuned on PubMed abstracts and clinical notes for biomedical summarization.",
      "tags_extra": ["biobart", "medical", "summarization", "biomedical"]}),

    # HF--30: en-zh translation
    ("Helsinki-NLP/opus-mt-en-zh", "translation", "Transformers", 0, True,
     {"description": "English to Chinese (en-zh) neural machine translation model. OPUS-MT project. High-quality Mandarin output.",
      "readme_extra": "## Evaluation\n\n| Metric | Score |\n|--------|-------|\n| BLEU   | 29.8  |\n\n## Usage\n\nTranslate English text to Chinese using the OPUS-MT pipeline.",
      "tags_extra": ["translation", "en-zh", "opus-mt", "chinese"]}),

    # HF--31: fake news detection
    ("GonzaloA/roberta-fake-news-detection", "text-classification", "Transformers", 0, False,
     {"description": "RoBERTa model fine-tuned for fake news detection. Classifies news articles as real or fake.",
      "tags_extra": ["fake", "fake-news", "detection", "news"]}),

    # HF--32: GPT-J-6B
    ("EleutherAI/gpt-j-6b", "text-generation", "Transformers", 6, True,
     {"description": "GPT-J 6B is a 6 billion parameter autoregressive language model by EleutherAI. Supports text generation with configurable parameters.",
      "readme_extra": "## Generation Parameters\n\n| Parameter | Default | Description |\n|-----------|---------|-------------|\n| temperature | 1.0 | Controls randomness. Default 1.0 means standard sampling. Lower values make output more deterministic. |\n| top_p | 0.9 | Nucleus sampling threshold |\n| max_length | 256 | Maximum generated tokens |",
      "tags_extra": ["gpt-j", "eleutherai", "language-model"]}),

    # HF--16: deberta-v3-large text classification, updated recently
    ("microsoft/deberta-v3-large-textclassification-2026", "text-classification", "Transformers", 0.3, True,
     {"updated_at_fixed": "2026-03-25", "language": "English",
      "description": "DeBERTa v3 Large for text classification. Updated 2026 with improved architecture and benchmarks.",
      "readme_extra": "## Intended Use\n\nDesigned for general-purpose text classification tasks.\n\n## Architecture\n\nDeBERTa v3 uses disentangled attention and enhanced mask decoder.",
      "tags_extra": ["deberta", "text-classification"]}),

    # HF--17: transformers nightly NLP project
    ("huggingface/transformers-2026-nightly", "text-generation", "Transformers", 0, True,
     {"updated_at_fixed": "2026-04-01", "language": "Multilingual",
      "description": "Transformers 2026 nightly build — experimental NLP open source project. Testing latest features and model architectures.",
      "readme_extra": "## Project Name\n\nTransformers 2026 Nightly\n\n## Creator\n\nHugging Face\n\n## Functionality\n\nThis is an experimental build of the Transformers library for testing latest NLP features.",
      "tags_extra": ["nlp", "open-source", "transformers", "nightly"]}),

    # HF--24: Apache-2.0 model with most likes
    ("meta-llama/Llama-3-apache-community", "text-generation", "Transformers", 8, True,
     {"license": "apache-2.0", "license_display": "Apache 2.0", "likes": 8000,
      "description": "Llama 3 community release under Apache 2.0 license. Open-source language model for research and commercial use.",
      "tags_extra": ["llama", "apache", "open-source"]}),

    # HF--26: travel chat model
    ("traveller-ai/llama-travel-chat-7b", "text-generation", "PEFT", 7, False,
     {"description": "Llama Travel Chat 7B — a PEFT-tuned model for travel-related conversations. Ask about destinations, itineraries, and travel tips.",
      "readme_extra": "## About\n\nllama-travel-chat-7b is a 7B parameter model fine-tuned with PEFT/LoRA for travel domain conversations.",
      "tags_extra": ["travel", "chat", "peft", "llama"]}),

    # HF--3: T0pp cc-by-sa model
    ("bigscience/T0pp-cc-by-sa", "text-generation", "Transformers", 11, True,
     {"license": "cc-by-sa-4.0", "license_display": "CC BY-SA 4.0", "likes": 3500,
      "description": "T0pp model released under CC BY-SA 4.0 license. Multitask prompted training enables zero-shot task generalization.",
      "tags_extra": ["t0pp", "cc-by-sa", "multitask"]}),

    # HF--4: English conversational AI
    ("facebook/blenderbot-3B-english-chat", "text-generation", "Transformers", 3, True,
     {"language": "English",
      "description": "BlenderBot 3B for English conversation. Features include empathy, knowledge grounding, and personality consistency. Application in chatbots and virtual assistants.",
      "readme_extra": "## Features\n\n- Empathetic responses\n- Knowledge-grounded dialogue\n- Personality consistency\n\n## Application\n\nDesigned for English conversational AI assistants and chatbot deployments.",
      "tags_extra": ["conversation", "english", "blenderbot", "chat"]}),

    # HF--5: recipe generation
    ("flax-community/t5-recipe-generation", "text-generation", "Transformers", 0.77, False,
     {"description": "T5 model fine-tuned for recipe generation. Given ingredients, generates cooking instructions. 770M parameters, FP32 precision.",
      "readme_extra": "## Model Info\n\n- Parameters: 770M\n- Precision: FP32\n- Task: Recipe generation from ingredients",
      "tags_extra": ["recipe", "t5", "generation", "cooking"]}),
]


CURATED_DATASETS = [
    ("HuggingFaceFW/fineweb",              "Text",  "text-generation",   52_500_000_000, "Large-scale web corpus carefully filtered for pretraining high-quality language models."),
    ("wikimedia/wikipedia",                "Text",  "fill-mask",         61_600_000,      "A complete multilingual Wikipedia dump processed into clean text for language modeling."),
    ("openai/gsm8k",                       "Text",  "question-answering",8_792,           "Grade-school math word problems with chain-of-thought annotations."),
    ("roneneldan/TinyStories",             "Text",  "text-generation",   2_140_000,       "Simple short stories generated to study language acquisition in small models."),
    ("HuggingFaceH4/ultrachat_200k",       "Text",  "text-generation",   200_000,         "Multi-turn chat data distilled from a strong teacher model for instruction tuning."),
    ("LAION/laion2B-en",                   "Image", "text-to-image",     2_000_000_000,   "Open CLIP-filtered English image-text pairs."),
    ("lmsys/lmsys-chat-1m",                "Text",  "text-generation",   1_000_000,       "One million real-world conversations with 25 large language models."),
    ("codeparrot/github-code",             "Text",  "text-generation",   115_000_000,     "Python, Java, C++ and more — GitHub code collected for code LLM pretraining."),
    ("c4/en",                              "Text",  "text-generation",   365_000_000,     "Colossal Clean Crawled Corpus — 750GB of cleaned web text."),
    ("mozilla-foundation/common_voice_17_0","Audio", "automatic-speech-recognition", 1_800_000, "Crowdsourced multilingual speech dataset covering 100+ languages."),
    ("mlfoundations/dclm-baseline-1.0",    "Text",  "text-generation",   4_200_000_000,   "DCLM baseline pretraining corpus for scalable LLM training."),
    ("allenai/dolma",                      "Text",  "text-generation",   3_100_000_000,   "AI2's 3T-token open pretraining corpus for OLMo."),
    ("nyu-mll/glue",                       "Text",  "text-classification", 1_104_000,     "GLUE benchmark — nine English NLU tasks."),
    ("nyu-mll/superglue",                  "Text",  "text-classification", 103_200,       "SuperGLUE — successor benchmark with harder tasks."),
    ("imagenet-1k",                        "Image", "image-classification", 1_281_167,    "ImageNet-1k — the canonical image classification benchmark."),
    ("coco",                               "Image", "object-detection",    118_000,       "Common Objects in Context — images with bounding boxes, masks and captions."),
    ("squad",                              "Text",  "question-answering",   107_000,      "Stanford Question Answering Dataset."),
    ("cnn_dailymail",                      "Text",  "summarization",       312_000,       "News articles with highlighted summaries."),
    ("xnli",                               "Text",  "text-classification", 392_000,       "Cross-lingual NLI in 15 languages."),
    ("tatsu-lab/alpaca",                   "Text",  "text-generation",     52_000,        "Self-instruct instruction-following dataset."),
    ("HuggingFaceH4/no_robots",            "Text",  "text-generation",     10_000,        "Human-written instructions and responses — 'no robots' involved."),
    ("databricks/databricks-dolly-15k",    "Text",  "text-generation",     15_011,        "Human-generated Q&A pairs from Databricks employees."),
    # HF--27: ms_marco text retrieval dataset
    ("microsoft/ms_marco", "Text", "text-ranking", 8_800_000, "MS MARCO (Microsoft Machine Reading Comprehension) — large-scale text retrieval and reading comprehension dataset for passage ranking."),
    # HF--42: ai2lumos dataset
    ("ai2lumos/lumos_complex_qa_plan_onetime", "Text", "question-answering", 5_200, "AI2 Lumos complex QA planning dataset. Multi-hop reasoning with step-by-step subgoal decomposition."),
]


CURATED_SPACES = [
    ("stabilityai/stable-diffusion",        "text-to-image",   "gradio",   "zero-gpu",   "🎨", "Generate high-quality images from text prompts using Stable Diffusion."),
    ("black-forest-labs/FLUX.1-schnell",    "text-to-image",   "gradio",   "zero-gpu",   "⚡", "Real-time image generation with FLUX.1 — draft-quality in a single step."),
    ("openai/whisper",                      "automatic-speech-recognition", "gradio", "t4-small", "🎙️", "Upload audio and get multilingual transcriptions powered by Whisper."),
    ("huggingface/chat-ui",                 "text-generation", "docker",   "l4x1",       "💬", "ChatGPT-style interface for open-source LLMs. Select a model and start chatting."),
    ("huggingface/tgi",                     "text-generation", "docker",   "a100-large", "🚀", "Benchmark Text Generation Inference with the latest high-throughput serving stack."),
    ("lmsys/chatbot-arena",                 "text-generation", "gradio",   "cpu-upgrade","⚔️", "Battle LLMs side-by-side and vote on which answer you prefer."),
    ("facebook/seamless_m4t",               "translation",     "gradio",   "a100-large", "🌐", "Multilingual, multimodal translation between 100+ languages."),
    ("microsoft/HuggingGPT",                "any-to-any",      "gradio",   "l40sx1",     "🤖", "Orchestrate multiple Hugging Face models to solve complex tasks."),
    ("coqui/XTTS",                          "text-to-speech",  "gradio",   "l4x1",       "🔊", "Zero-shot voice cloning text-to-speech in 17 languages."),
    ("google/paligemma",                    "image-text-to-text", "gradio","zero-gpu",   "👁️", "Vision-language Q&A — ask questions about any image."),
    ("tencent/Hunyuan3D-2",                 "image-to-3d",     "gradio",   "a100-large", "🧊", "Turn a single image into a textured 3D mesh."),
    ("depth-anything/depth-anything-v2",    "depth-estimation","gradio",   "t4-small",   "🗺️","Monocular depth prediction at state-of-the-art accuracy."),
    ("sayakpaul/FAST-SAM",                  "image-segmentation","gradio", "t4-small",   "🧩", "Fast segmentation anywhere — try it in your browser."),
    ("HuggingFaceTB/SmolLM2-demo",          "text-generation", "gradio",   "cpu-upgrade","📚", "Lightweight SmolLM2 chat demo running on CPU."),
    ("Qwen/Qwen2-VL",                       "image-text-to-text", "gradio","l40sx1",    "🖼️","State-of-the-art open vision-language model demo."),
    # HF--10: argilla/notux-chat-ui space
    ("argilla/notux-chat-ui",               "text-generation", "gradio",   "l4x1",      "💬", "Notux Chat UI by Argilla — a chat interface trained on DPO data for RLHF evaluation."),
    # HF--41: dreamfusion text-to-3d spaces (multiple visible spaces using dreamfusion-sd-v1)
    ("dreamfusion-ai/dreamfusion-demo",     "text-to-3d",      "gradio",   "a100-large","🧊", "Official DreamFusion: Text-to-3D using 2D diffusion priors. Generate 3D models from text prompts. Powered by dreamfusion-ai/dreamfusion-sd-v1."),
    ("dreamfusion-ai/dreamfusion-gallery",  "text-to-3d",      "gradio",   "t4-small",  "🎨", "DreamFusion gallery — browse and generate 3D assets with the dreamfusion-sd-v1 pipeline. Uses dreamfusion-ai/dreamfusion-sd-v1 under the hood."),
    ("dreamfusion-ai/text-to-3d-playground","text-to-3d",      "gradio",   "a100-large","🎮", "Text-to-3D playground running dreamfusion-ai/dreamfusion-sd-v1 with preset prompts and exportable .obj meshes."),
    ("multimodalart/dreamfusion-web",       "text-to-3d",      "gradio",   "zero-gpu",  "🌐", "Community-maintained DreamFusion web UI. Runs dreamfusion-ai/dreamfusion-sd-v1 with ZeroGPU for free text-to-3D generation."),
    ("radames/dreamfusion-sd-v1-space",     "text-to-3d",      "docker",   "a100-large","🔮", "Docker Space wrapping dreamfusion-ai/dreamfusion-sd-v1 with live NeRF visualization and mesh export."),
]


# ------------------------------------------------------------
# 6) Helpers
# ------------------------------------------------------------
def pick_description(task_slug: str, rng: random.Random) -> str:
    desc_list = MODEL_DESCRIPTIONS.get(task_slug, MODEL_DESCRIPTIONS["default"])
    return rng.choice(desc_list)


def _load_scraped():
    """Merge repos.json (curated bulk) with the trending/likes/new/recent dumps
    so the seed DB covers ~4500 unique repos (~3x R1 baseline).

    All supplementary dumps use HF Hub API shape (`id` = "author/name") instead
    of repos.json's `slug`. Translate to the shape expected by
    build_seed_repos() and only append truly new slugs. Sort each dump before
    merging so byte order is deterministic across rebuilds.
    """
    base = {"models": [], "datasets": [], "spaces": []}
    repos_path = ROOT / "scraped_data" / "repos.json"
    if repos_path.exists():
        with open(repos_path) as f:
            base = json.load(f)

    seen = {
        "models": {m.get("slug") for m in base["models"] if isinstance(m, dict)},
        "datasets": {d.get("slug") for d in base["datasets"] if isinstance(d, dict)},
        "spaces": {s.get("slug") for s in base["spaces"] if isinstance(s, dict)},
    }

    def _adapt(item):
        slug = item.get("id") or item.get("slug") or ""
        if not slug or "/" not in slug or slug.count("/") > 1:
            return None
        return {
            "slug": slug,
            "pipeline_tag": item.get("pipeline_tag", ""),
            "library_name": item.get("library_name", ""),
            "tags": item.get("tags", []),
            "downloads": item.get("downloads", 0),
            "likes": item.get("likes", 0),
            "sdk": item.get("sdk", ""),
            "description": item.get("description", ""),
            "createdAt": item.get("createdAt", ""),
            "lastModified": item.get("lastModified", ""),
        }

    supplementary = [
        ("models",   "hf_models_dl.json"),
        ("models",   "hf_models_likes.json"),
        ("models",   "hf_models_new.json"),
        ("models",   "hf_models_recent.json"),
        ("models",   "hf_models_more.json"),
        ("models",   "hf_models_r3.json"),
        ("models",   "hf_models_r4.json"),
        ("datasets", "hf_datasets.json"),
        ("datasets", "hf_datasets_likes.json"),
        ("datasets", "hf_datasets_more.json"),
        ("datasets", "hf_datasets_r3.json"),
        ("datasets", "hf_datasets_r4.json"),
        ("spaces",   "hf_spaces.json"),
        ("spaces",   "hf_spaces_recent.json"),
        ("spaces",   "hf_spaces_more.json"),
        ("spaces",   "hf_spaces_r3.json"),
        ("spaces",   "hf_spaces_r4.json"),
    ]
    for kind, fname in supplementary:
        p = ROOT / "scraped_data" / fname
        if not p.exists():
            continue
        try:
            with open(p) as f:
                arr = json.load(f)
        except Exception:
            continue
        if not isinstance(arr, list):
            continue
        for raw in sorted(arr, key=lambda r: (r.get("id") or r.get("slug") or "")):
            adapted = _adapt(raw)
            if not adapted:
                continue
            if adapted["slug"] in seen[kind]:
                continue
            seen[kind].add(adapted["slug"])
            base[kind].append(adapted)

    # R5: lift caps so total repos clear 80k (model 35k+, dataset 38k+,
    # space 6k+). Scraped pools already exceed these — see
    # scraped_data/*.json totals (models ~37k, datasets ~44k, spaces ~23k).
    # First N entries survive (alpha-sorted above), so rebuilds are byte-stable.
    CAPS = {"models": 36000, "datasets": 39000, "spaces": 6500}
    for k, cap in CAPS.items():
        if len(base[k]) > cap:
            base[k] = base[k][:cap]

    return base


def _list_files(folder: Path, exts={".jpg", ".jpeg", ".png", ".webp", ".svg"}):
    if not folder.exists():
        return []
    return sorted([p.name for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts])


def _make_readme(title: str, kind: str, description: str, task_display: str, library: str, params_b: float, license_display: str) -> str:
    """Generate a markdown-ish README for detail pages."""
    parts = []
    parts.append(f"# {title}")
    parts.append("")
    parts.append(description)
    parts.append("")
    parts.append("## Model Details")
    parts.append("")
    parts.append("### Model Description")
    parts.append("")
    parts.append(f"This {kind} was trained with a focus on quality, reliability, and ease of integration. It is released under the **{license_display}** license and is ready for drop-in use via the `{library}` library.")
    parts.append("")
    if params_b > 0:
        parts.append(f"- **Parameters:** {params_b}B")
    parts.append(f"- **Primary task:** {task_display}")
    parts.append(f"- **Library:** {library}")
    parts.append(f"- **License:** {license_display}")
    parts.append("")
    parts.append("## Intended Use")
    parts.append("")
    parts.append("This model is intended for research, experimentation, and downstream fine-tuning. For production deployments, evaluate thoroughly on your target distribution.")
    parts.append("")
    parts.append("## How to use")
    parts.append("")
    parts.append("```python")
    parts.append(f"from transformers import AutoModel, AutoTokenizer")
    parts.append(f'tokenizer = AutoTokenizer.from_pretrained("{title}")')
    parts.append(f'model = AutoModel.from_pretrained("{title}")')
    parts.append("```")
    parts.append("")
    parts.append("## Training Data")
    parts.append("")
    parts.append("The training corpus was carefully curated to balance quality, diversity, and safety. See the accompanying paper for a detailed breakdown.")
    parts.append("")
    parts.append("## Evaluation")
    parts.append("")
    parts.append("Comprehensive benchmarks show strong performance across standard academic evaluations. Please refer to the Files and Versions tab for the full eval report.")
    parts.append("")
    parts.append("## Bias, Risks, and Limitations")
    parts.append("")
    parts.append("Like all machine learning systems, this model may reflect biases present in its training data. Users should evaluate outputs carefully before any production use and follow responsible-AI guidelines.")
    parts.append("")
    parts.append("## Citation")
    parts.append("")
    parts.append("```bibtex")
    parts.append(f"@misc{{{title.replace('/', '_')},")
    parts.append(f"  title  = {{{title}}},")
    parts.append(f"  author = {{{title.split('/')[0]}}},")
    parts.append("  year   = 2026,")
    parts.append(f"  url    = {{https://huggingface.co/{title}}}")
    parts.append("}")
    parts.append("```")
    return "\n".join(parts)


# ------------------------------------------------------------
# 7) Build the final repo lists for seeding
# ------------------------------------------------------------
def build_seed_repos():
    rng = random.Random(42)
    scraped = _load_scraped()
    avatar_files = _list_files(ROOT / "static" / "images" / "avatars")
    hero_files = _list_files(ROOT / "static" / "images" / "heroes")
    feature_files = _list_files(ROOT / "static" / "images" / "features")
    repo_banners = _list_files(ROOT / "static" / "images" / "repos")

    if not avatar_files:
        avatar_files = ["default.svg"]

    def avatar(i):
        return f"/static/images/avatars/{avatar_files[i % len(avatar_files)]}"

    def banner(i):
        if repo_banners:
            return f"/static/images/repos/{repo_banners[i % len(repo_banners)]}"
        return f"/static/images/heroes/{hero_files[i % len(hero_files)]}"

    # Map task_slug -> list of sample keywords for sub-category variety
    models_out = []
    seen_slugs = set()

    # ---- 1) curated models (rich data)
    for i, (slug, task, library, params, is_featured) in enumerate(CURATED_MODELS):
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        author = slug.split("/")[0]
        name = slug.split("/")[1]
        license_slug, license_display = rng.choice(LICENSES[:8])
        desc = pick_description(task, rng)
        updated_days = rng.randint(1, 90)
        # Ensure some recent NLP models exist (updated today / yesterday)
        # so "most recently updated" queries can find them
        if task == "text-generation" and author == "huggingface":
            updated_days = 0
        elif task == "text-generation" and i < 5:
            updated_days = rng.randint(0, 1)
        downloads = rng.choice([12_340, 45_000, 120_000, 340_000, 980_000, 1_590_000, 3_200_000]) if is_featured else rng.randint(800, 250_000)
        likes = rng.randint(40, 4000) if is_featured else rng.randint(5, 800)
        tags_list = [library.lower(), task, author, license_slug]
        if params >= 7:
            tags_list.append("large-language-model")
        task_display = next((t[1] for t in TASKS if t[0] == task), task)
        readme = _make_readme(slug, "model", desc, task_display, library, params, license_display)
        models_out.append({
            "repo_type": "model",
            "slug": slug,
            "author": author,
            "name": name,
            "task": task,
            "library": library,
            "license": license_slug,
            "license_display": license_display,
            "description": desc,
            "readme": readme,
            "params_b": float(params),
            "downloads": downloads,
            "likes": likes,
            "updated_days_ago": updated_days,
            "is_featured": is_featured,
            "is_new": updated_days < 7,
            "tags": tags_list,
            "avatar": avatar(i),
            "banner": banner(i),
            "language": rng.choice(LANGUAGES),
            "inference_provider": rng.choice(INFERENCE_PROVIDERS),
        })

    # ---- 1b) task-driven models (with special overrides for dates, languages, etc.)
    for i, (slug, task, library, params, is_featured, overrides) in enumerate(TASK_DRIVEN_MODELS):
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        author = slug.split("/")[0]
        name = slug.split("/")[1]
        license_slug = overrides.get("license", rng.choice(LICENSES[:8])[0])
        license_display = overrides.get("license_display", next((ld for ls, ld in LICENSES if ls == license_slug), "Apache 2.0"))
        desc = overrides.get("description", pick_description(task, rng))
        readme_extra = overrides.get("readme_extra", "")
        task_display = next((t[1] for t in TASKS if t[0] == task), task)
        readme = _make_readme(slug, "model", desc, task_display, library, params, license_display)
        if readme_extra:
            readme += "\n\n" + readme_extra

        # Handle updated_at
        if "updated_at_fixed" in overrides:
            # Parse YYYY-MM-DD to compute days ago
            from datetime import datetime as _dt
            fixed = _dt.strptime(overrides["updated_at_fixed"], "%Y-%m-%d")
            # For seeding, store as days_ago from a reference
            updated_days = max(0, (_dt.utcnow() - fixed).days)
        else:
            updated_days = overrides.get("updated_days_ago", rng.randint(1, 90))

        downloads = overrides.get("downloads", rng.choice([12_340, 45_000, 120_000, 340_000, 980_000, 1_590_000]) if is_featured else rng.randint(800, 250_000))
        likes = overrides.get("likes", rng.randint(40, 4000) if is_featured else rng.randint(5, 800))
        language = overrides.get("language", rng.choice(LANGUAGES))
        tags_list = [library.lower(), task, author, license_slug]
        tags_list.extend(overrides.get("tags_extra", []))
        if params >= 7:
            tags_list.append("large-language-model")
        models_out.append({
            "repo_type": "model",
            "slug": slug,
            "author": author,
            "name": name,
            "task": task,
            "library": overrides.get("library", library),
            "license": license_slug,
            "license_display": license_display,
            "description": desc,
            "readme": readme,
            "params_b": float(params),
            "downloads": downloads,
            "likes": likes,
            "updated_days_ago": updated_days,
            "is_featured": is_featured,
            "is_new": updated_days < 7,
            "tags": tags_list,
            "avatar": avatar(i + 100),
            "banner": banner(i + 100),
            "language": language,
            "inference_provider": rng.choice(INFERENCE_PROVIDERS),
        })

    # ---- 2) scraped models (wider variety) — pipeline_tag/library_name come
    # from the HF API dump when present; otherwise fall back to name-based hints.
    VALID_TASKS = {t[0] for t in TASKS}
    LIB_NORMALIZE = {
        "transformers": "Transformers", "diffusers": "Diffusers", "safetensors": "Safetensors",
        "pytorch": "PyTorch", "tensorflow": "TensorFlow", "jax": "JAX", "onnx": "ONNX",
        "gguf": "GGUF", "sentence-transformers": "sentence-transformers",
        "transformers.js": "Transformers.js", "mlx": "MLX", "peft": "PEFT", "timm": "timm",
        "keras": "Keras", "flax": "Flax", "paddlepaddle": "PaddlePaddle", "paddlenlp": "PaddlePaddle",
        "stable-baselines3": "stable-baselines3",
    }
    for i, m in enumerate(scraped["models"]):
        slug = m["slug"]
        if "/" not in slug or slug.count("/") > 1 or slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        author = slug.split("/")[0]
        name = slug.split("/")[1]

        api_task = (m.get("pipeline_tag") or "").strip()
        api_lib = (m.get("library_name") or "").strip().lower()

        if api_task in VALID_TASKS:
            task = api_task
        else:
            # Infer task from name hints
            nl = name.lower()
            if "ocr" in nl:
                task = "image-text-to-text"
            elif "voice" in nl or "tts" in nl or "speech" in nl:
                task = "text-to-speech"
            elif "asr" in nl or "whisper" in nl:
                task = "automatic-speech-recognition"
            elif "image" in nl or "diffusion" in nl or "sd" in nl or "flux" in nl:
                task = "text-to-image"
            elif "video" in nl:
                task = "text-to-video"
            elif "depth" in nl:
                task = "depth-estimation"
            elif "detect" in nl or "yolo" in nl:
                task = "object-detection"
            elif "segment" in nl or "sam" in nl:
                task = "image-segmentation"
            elif "embed" in nl or "sentence" in nl:
                task = "feature-extraction"
            else:
                task = "text-generation"

        if api_lib in LIB_NORMALIZE:
            library = LIB_NORMALIZE[api_lib]
        else:
            library = "Diffusers" if task in ("text-to-image", "text-to-video", "image-to-video", "unconditional-image-generation") else "Transformers"
            if "gguf" in name.lower():
                library = "GGUF"
        license_slug, license_display = rng.choice(LICENSES[:8])
        desc = pick_description(task, rng)
        updated_days = rng.randint(1, 120)
        # Prefer API counts (real-world signal) when present; fall back to randomized.
        api_dl = int(m.get("downloads") or 0)
        api_lk = int(m.get("likes") or 0)
        downloads = api_dl if api_dl > 0 else rng.randint(200, 150_000)
        likes = api_lk if api_lk > 0 else rng.randint(3, 400)
        # Estimate params from name
        params = 0.0
        import re
        m_ = re.search(r"(\d+(?:\.\d+)?)\s*[Bb]\b", name)
        if m_:
            try:
                params = float(m_.group(1))
            except Exception:
                params = 0.0
        task_display = next((t[1] for t in TASKS if t[0] == task), task)
        readme = _make_readme(slug, "model", desc, task_display, library, params, license_display)
        models_out.append({
            "repo_type": "model",
            "slug": slug,
            "author": author,
            "name": name,
            "task": task,
            "library": library,
            "license": license_slug,
            "license_display": license_display,
            "description": desc,
            "readme": readme,
            "params_b": params,
            "downloads": downloads,
            "likes": likes,
            "updated_days_ago": updated_days,
            "is_featured": i < 8,
            "is_new": updated_days < 3,
            "tags": [library.lower(), task, author, license_slug],
            "avatar": avatar(i + 50),
            "banner": banner(i + 2),
            "language": rng.choice(LANGUAGES),
            "inference_provider": rng.choice(INFERENCE_PROVIDERS),
        })

    # ---- 3) datasets
    datasets_out = []
    seen_ds = set()
    for i, (slug, modality, task, rows, desc) in enumerate(CURATED_DATASETS):
        # Handle single-segment slugs like 'imagenet-1k' or 'coco'
        if "/" not in slug:
            slug = f"community/{slug}"
        seen_ds.add(slug)
        parts = slug.split("/")
        author = parts[0] if len(parts) > 1 else "community"
        name = parts[-1]
        license_slug, license_display = rng.choice(LICENSES[:6])
        updated_days = rng.randint(1, 200)
        downloads = rng.randint(5_000, 900_000)
        likes = rng.randint(20, 3000)
        datasets_out.append({
            "repo_type": "dataset",
            "slug": slug,
            "author": author,
            "name": name,
            "task": task,
            "modality": modality,
            "library": "Datasets",
            "license": license_slug,
            "license_display": license_display,
            "description": desc,
            "readme": _make_readme(slug, "dataset", desc, modality, "datasets", 0, license_display),
            "rows": rows,
            "downloads": downloads,
            "likes": likes,
            "updated_days_ago": updated_days,
            "is_featured": i < 6,
            "is_new": updated_days < 4,
            "tags": [modality.lower(), task, "dataset", license_slug],
            "avatar": avatar(i + 20),
            "banner": banner(i + 4),
            "language": rng.choice(LANGUAGES),
            "inference_provider": "",
            "params_b": 0.0,
        })

    for i, d in enumerate(scraped["datasets"]):
        slug = d["slug"]
        if slug in seen_ds or "/" not in slug or slug.count("/") > 1:
            continue
        seen_ds.add(slug)
        author = slug.split("/")[0]
        name = slug.split("/")[1]
        # Prefer the dataset card's own short description if the scrape provided one
        scraped_desc = (d.get("description") or "").strip()
        desc = scraped_desc[:280] if scraped_desc else rng.choice(DATASET_DESCRIPTIONS)
        # Infer modality / task from API tags when possible
        api_tags = [str(t).lower() for t in d.get("tags", [])]
        modality = "Text"
        if any("audio" in t or "speech" in t for t in api_tags):
            modality = "Audio"
        elif any("image" in t or "vision" in t for t in api_tags):
            modality = "Image"
        elif any("video" in t for t in api_tags):
            modality = "Video"
        elif any("tabular" in t for t in api_tags):
            modality = "Tabular"
        # Heuristic task pick from tags
        task = "text-generation"
        for t in api_tags:
            if t.startswith("task_categories:"):
                cand = t.split(":", 1)[1]
                if cand in {x[0] for x in TASKS}:
                    task = cand
                    break
        license_slug, license_display = rng.choice(LICENSES[:6])
        updated_days = rng.randint(1, 60)
        rows_est = rng.choice([5_000, 50_000, 500_000, 2_000_000, 20_000_000])
        api_dl = int(d.get("downloads") or 0)
        api_lk = int(d.get("likes") or 0)
        datasets_out.append({
            "repo_type": "dataset",
            "slug": slug,
            "author": author,
            "name": name,
            "task": task,
            "modality": modality,
            "library": "Datasets",
            "license": license_slug,
            "license_display": license_display,
            "description": desc,
            "readme": _make_readme(slug, "dataset", desc, modality, "datasets", 0, license_display),
            "rows": rows_est,
            "downloads": api_dl if api_dl > 0 else rng.randint(100, 80_000),
            "likes": api_lk if api_lk > 0 else rng.randint(2, 500),
            "updated_days_ago": updated_days,
            "is_featured": i < 4,
            "is_new": updated_days < 3,
            "tags": [modality.lower(), task, "dataset", license_slug],
            "avatar": avatar(i + 30),
            "banner": banner(i + 5),
            "language": rng.choice(LANGUAGES),
            "inference_provider": "",
            "params_b": 0.0,
        })

    # ---- 4) spaces
    spaces_out = []
    seen_sp = set()
    for i, (slug, task, sdk, hw, emoji, desc) in enumerate(CURATED_SPACES):
        seen_sp.add(slug)
        parts = slug.split("/")
        author = parts[0] if len(parts) > 1 else "community"
        name = parts[-1]
        hw_row = next((h for h in SPACE_HARDWARE if h[0] == hw), SPACE_HARDWARE[0])
        spaces_out.append({
            "repo_type": "space",
            "slug": slug,
            "author": author,
            "name": name,
            "task": task,
            "sdk": sdk,
            "hardware_slug": hw,
            "hardware_display": hw_row[1],
            "hardware_specs": hw_row[2],
            "hardware_price": hw_row[3],
            "emoji": emoji,
            "description": desc,
            "readme": _make_readme(slug, "space", desc, next((t[1] for t in TASKS if t[0] == task), task), sdk, 0, "MIT"),
            "status": "Running",
            "downloads": 0,
            "likes": rng.randint(50, 3500),
            "updated_days_ago": rng.randint(1, 45),
            "is_featured": i < 8,
            "is_new": rng.random() < 0.3,
            "tags": [task, sdk, hw, author],
            "avatar": avatar(i + 5),
            "banner": banner(i + 6),
            "language": "English",
            "inference_provider": "",
            "license": "mit",
            "license_display": "MIT",
            "library": "",
            "params_b": 0.0,
        })

    for i, s in enumerate(scraped["spaces"]):
        slug = s["slug"]
        if slug in seen_sp or "/" not in slug or slug.count("/") > 1:
            continue
        seen_sp.add(slug)
        author = slug.split("/")[0]
        name = slug.split("/")[1]
        # Infer task from name
        nl = name.lower()
        if "voice" in nl or "tts" in nl or "speech" in nl:
            task = "text-to-speech"
        elif "image" in nl and "edit" in nl:
            task = "image-to-image"
        elif "image" in nl:
            task = "text-to-image"
        elif "video" in nl:
            task = "text-to-video"
        elif "3d" in nl or "magihuman" in nl:
            task = "image-to-3d"
        else:
            task = "text-generation"
        hw_row = rng.choice(SPACE_HARDWARE)
        api_sdk = (s.get("sdk") or "").strip().lower()
        sdk = api_sdk if api_sdk in {"gradio", "streamlit", "docker", "static"} else rng.choice(["gradio", "gradio", "streamlit", "docker"])
        emoji = rng.choice(["🚀", "🔥", "✨", "🎨", "🎬", "🌀", "💫", "🎯", "🧠", "🤖"])
        desc = rng.choice(SPACE_DESCRIPTIONS)
        api_lk = int(s.get("likes") or 0)
        spaces_out.append({
            "repo_type": "space",
            "slug": slug,
            "author": author,
            "name": name,
            "task": task,
            "sdk": sdk,
            "hardware_slug": hw_row[0],
            "hardware_display": hw_row[1],
            "hardware_specs": hw_row[2],
            "hardware_price": hw_row[3],
            "emoji": emoji,
            "description": desc,
            "readme": _make_readme(slug, "space", desc, next((t[1] for t in TASKS if t[0] == task), task), sdk, 0, "MIT"),
            "status": rng.choice(["Running", "Running on Zero", "Running on A10G", "Paused"]),
            "downloads": 0,
            "likes": api_lk if api_lk > 0 else rng.randint(20, 2500),
            "updated_days_ago": rng.randint(1, 30),
            "is_featured": i < 6,
            "is_new": rng.random() < 0.4,
            "tags": [task, sdk, hw_row[0], author],
            "avatar": avatar(i + 10),
            "banner": banner(i + 7),
            "language": "English",
            "inference_provider": "",
            "license": "mit",
            "license_display": "MIT",
            "library": "",
            "params_b": 0.0,
        })

    return models_out, datasets_out, spaces_out


if __name__ == "__main__":
    m, d, s = build_seed_repos()
    print(f"Models:   {len(m)}")
    print(f"Datasets: {len(d)}")
    print(f"Spaces:   {len(s)}")
    print(f"Tasks:    {len(TASKS)}")
    print(f"Authors:  {len(AUTHORS)}")
