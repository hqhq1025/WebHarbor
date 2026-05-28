"""
GUI Deepen module for the Phys.org mirror.

Adds 23 new HTML surfaces modelled on real phys.org pages that the baseline
mirror did not cover, plus the POST-driven interactions that real users have
on the site (newsletter subscribe, upvote / report / share an article, follow
an author / topic / podcast / journal, submit a tip, contact the editorial
team).

Design rules — same as bbc_news.gui_deepen:

  * Every GUI page derives its sample data from a deterministic md5 anchor
    seeded by the route arguments + the MIRROR_REFERENCE_DATE, so a rebuild
    on a different machine renders identical bytes.
  * POST routes write to runtime-only tables (NewsletterSubscription,
    ArticleVote, ArticleReport, …) that are *empty* in instance_seed and
    therefore do not affect the byte-identical reset invariant.
  * Article hero images, author headshots, podcast covers and category
    banners are SVGs generated on-the-fly via /static-gen/ so we don't ship
    new binary assets.

Tasks attached to each surface use the prefix ``Phys.org--gui_<page>_<NNN>``
and are appended to tasks.jsonl by deepen_tasks.py.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta
from typing import Iterable

from flask import (Response, abort, flash, jsonify, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required


# --------------------------------------------------------------------- #
# Deterministic helpers                                                  #
# --------------------------------------------------------------------- #

GUI_REFERENCE_DATE = datetime(2026, 5, 12, 12, 0, 0)


def _seed(*parts) -> str:
    return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()


def _pick(h: str, off: int, pool):
    return pool[int(h[off:off + 2], 16) % len(pool)]


def _int(h: str, off: int, lo: int, hi: int) -> int:
    return lo + (int(h[off:off + 4], 16) % (hi - lo + 1))


def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-") or "x"


# --------------------------------------------------------------------- #
# Pinned content pools (real phys.org surfaces)                          #
# --------------------------------------------------------------------- #

# Each top-level category has 3-6 real-phys.org subsections. Seeded from the
# 34 distinct ``Article.subsection`` values already in the DB.
SUBSECTIONS = {
    "physics": [
        ("general-physics", "General Physics"),
        ("quantum-physics", "Quantum Physics"),
        ("condensed-matter", "Condensed Matter"),
        ("optics-photonics", "Optics & Photonics"),
        ("superconductivity", "Superconductivity"),
    ],
    "earth": [
        ("earth-sciences", "Earth Sciences"),
        ("environment", "Environment"),
    ],
    "technology": [
        ("machine-learning-ai", "Machine learning & AI"),
        ("robotics", "Robotics"),
        ("engineering", "Engineering"),
        ("energy-green-tech", "Energy & Green Tech"),
        ("electronics-semiconductors", "Electronics & Semiconductors"),
        ("consumer-gadgets", "Consumer & Gadgets"),
        ("security", "Security"),
        ("software", "Software"),
        ("internet", "Internet"),
        ("automotive", "Automotive"),
    ],
    "biology": [
        ("cell-microbiology", "Cell & Microbiology"),
        ("evolution", "Evolution"),
        ("ecology", "Ecology"),
        ("plants-animals", "Plants & Animals"),
        ("molecular-computational", "Molecular & Computational biology"),
        ("biotechnology", "Biotechnology"),
    ],
    "chemistry": [
        ("analytical", "Analytical Chemistry"),
        ("biochemistry", "Biochemistry"),
        ("materials-science", "Materials Science"),
        ("polymers", "Polymers"),
    ],
    "astronomy": [
        ("astronomy", "Astronomy"),
        ("planetary", "Planetary Sciences"),
        ("space-exploration", "Space Exploration"),
        ("astrobiology", "Astrobiology"),
    ],
    "nanotechnology": [
        ("nanomaterials", "Nanomaterials"),
        ("nanophysics", "Nanophysics"),
        ("bio-medicine", "Bio & Medicine"),
    ],
    "other": [
        ("social-sciences", "Social Sciences"),
        ("archaeology", "Archaeology"),
        ("mathematics", "Mathematics"),
        ("education", "Education"),
    ],
}

# Newsletter offerings — modeled on phys.org's real digest list.
NEWSLETTERS = [
    ("phys-daily", "Phys.org Daily Digest",
     "Top science stories from across phys.org, delivered every morning.", "daily"),
    ("physics-weekly", "Physics & Quantum Weekly",
     "Best of physics, quantum and superconductivity reporting, weekly.", "weekly"),
    ("space-astronomy", "Space & Astronomy",
     "JWST, planetary missions and cosmology — twice a week.", "twice-weekly"),
    ("earth-climate", "Earth & Climate",
     "Climate, oceans, geology and the planet — three times a week.", "thrice-weekly"),
    ("biology-medicine", "Biology, Medicine & Health",
     "Cell biology, genomics, biotech and life sciences, weekly.", "weekly"),
    ("chemistry-materials", "Chemistry & Materials",
     "Catalysis, materials, polymers and nanotech research, weekly.", "weekly"),
    ("technology-ai", "Technology & AI",
     "AI, robotics, computing, energy and engineering breakthroughs, weekly.", "weekly"),
    ("research-roundup", "Research Roundup",
     "A curated digest of the most-cited and most-discussed studies, every Friday.", "weekly"),
]

# Podcasts — 12 pinned shows; cover image is an SVG generated by /static-gen/.
PODCASTS = [
    ("science-x-network", "Science X Network Weekly",
     "A roundup of the week's biggest stories from the Science X journals.", 42),
    ("quantum-frontiers", "Quantum Frontiers",
     "Long-form interviews with physicists working on qubits, error correction and exotic phases.", 31),
    ("dark-skies-bright-data", "Dark Skies, Bright Data",
     "Astronomy from the ground up — radio arrays, optical surveys, gravitational waves.", 58),
    ("climate-correction", "Climate Correction",
     "Climate scientists in their own words — what models predict and what we are measuring.", 28),
    ("cells-and-circuits", "Cells & Circuits",
     "Biology meets computation — single-cell sequencing, AlphaFold and the new toolkit.", 36),
    ("clean-reaction", "Clean Reaction",
     "Green chemistry, polymers, catalysis and the materials behind the energy transition.", 22),
    ("nano-impact", "Nano Impact",
     "Stories from the nano-frontier — 2D materials, quantum dots, biomedical devices.", 19),
    ("hard-tech-weekly", "Hard Tech Weekly",
     "Robotics, semiconductors and the deeply technical side of the AI boom.", 47),
    ("methane-and-microbes", "Methane & Microbes",
     "Earth-system biogeochemistry from the people building the carbon budget.", 24),
    ("astro-ai-lab", "Astro AI Lab",
     "Machine learning meets astrophysics — exoplanet detection, classification, simulations.", 17),
    ("photonics-quarterly", "Photonics Quarterly",
     "Optics, lasers and the photonic backbone of the next generation of sensors.", 14),
    ("research-in-review", "Research in Review",
     "An editorial commentary podcast — what the new science actually means.", 39),
]

VIDEOS_TOPICS = [
    "Hubble vs JWST: imaging the same nebula 30 years apart",
    "Building a neural-net surrogate for nonlinear optics in 4 minutes",
    "Lab tour: superconducting qubits at 10 millikelvin",
    "What a Mars sample looks like under an electron microscope",
    "Why direct air capture is harder than people think",
    "Inside a base-editing CRISPR experiment, step by step",
    "The 5-minute version of the Standard Model survey results",
    "How astronomers track a single asteroid across 8 years of data",
    "From RSS feed to research front page: the Phys.org pipeline",
    "Quantum chip benchmarks explained without buzzwords",
    "Climate model resolution: 100 km vs 10 km, side by side",
    "Cryo-EM in 90 seconds: protein structure from a beam of electrons",
    "Methane plume from space — what TROPOMI actually sees",
    "A wafer-scale photonic accelerator, hand-on tour",
    "Reading a galaxy cluster's velocity dispersion in real time",
    "The exoplanet transit method, explained with a desk lamp",
    "Why fusion reactors need exotic alloys",
    "Genome assembly on a laptop, by an undergrad",
    "What an LHC dataset actually looks like at the analysis stage",
    "Soft robotics: how a gecko-inspired gripper picks up an egg",
    "The IPCC AR7 working-group draft, summarised in 3 figures",
    "Lithium recycling — three reactors, three trade-offs",
    "Inside a synthetic-biology cleanroom",
    "Magnetar bursts caught live by a radio array",
    "The 3-billion-year-old fossil that changed evolution timelines",
    "An EV battery autopsy: failure modes you do not want",
    "Quantum dot LEDs: from cuvette to display",
    "How a cosmic ray hits a chip — and what it does to a memory cell",
    "Memristors meet deep nets: a 30-second demo",
    "What a satellite-derived methane inventory actually measures",
]

TOPICS = [
    ("dark-matter", "Dark matter", "physics"),
    ("jwst", "James Webb Space Telescope", "astronomy"),
    ("quantum-computing", "Quantum computing", "physics"),
    ("crispr", "CRISPR & gene editing", "biology"),
    ("climate-change", "Climate change", "earth"),
    ("artificial-intelligence", "Artificial intelligence", "technology"),
    ("exoplanets", "Exoplanets", "astronomy"),
    ("graphene", "Graphene", "nanotechnology"),
    ("battery-tech", "Battery technology", "technology"),
    ("methane", "Methane emissions", "earth"),
    ("alphafold", "AlphaFold & protein structure", "biology"),
    ("fusion-energy", "Fusion energy", "physics"),
    ("solar-energy", "Solar energy", "technology"),
    ("genomics", "Genomics & sequencing", "biology"),
    ("catalysis", "Catalysis", "chemistry"),
    ("2d-materials", "2D materials", "nanotechnology"),
    ("polymers-sustainable", "Sustainable polymers", "chemistry"),
    ("robotics-soft", "Soft robotics", "technology"),
    ("microplastics", "Microplastics", "earth"),
    ("hubble", "Hubble Space Telescope", "astronomy"),
]

POLLS = [
    ("ai-impact", "Which AI development will affect science most in the next 5 years?",
     ["Automated literature review", "Hypothesis generation",
      "Lab automation", "Simulation surrogates", "Peer review assist"]),
    ("climate-priority", "Top climate priority for 2030?",
     ["Energy storage", "Direct air capture",
      "Reforestation", "Methane abatement", "Grid modernisation"]),
    ("most-exciting-physics", "Most exciting open physics question?",
     ["Dark matter nature", "Quantum gravity",
      "High-Tc mechanism", "Neutrino mass ordering", "Baryogenesis"]),
    ("space-mission", "Which 2030s space mission are you most looking forward to?",
     ["LISA", "Habitable Worlds Observatory",
      "Mars Sample Return", "JUICE Ganymede orbit", "Roman Space Telescope"]),
    ("biology-tool", "Which biology tool will define the next decade?",
     ["Base editing", "Spatial transcriptomics",
      "Cryo-ET", "Organoid drug screens", "AlphaFold-Multimer"]),
    ("nano-application", "Which nanotech application will reach scale first?",
     ["Quantum-dot displays", "Nanopore sequencing",
      "MOF gas separation", "Wearable biosensors", "2D-material transistors"]),
]


# --------------------------------------------------------------------- #
# Author / Journal helpers — derived from the existing Article table    #
# --------------------------------------------------------------------- #

def _author_slug(name: str) -> str:
    return _slugify(name)


def _journal_slug(name: str) -> str:
    return _slugify(name)


def _build_author_bio(name: str) -> str:
    h = _seed("author-bio", name)
    role = _pick(h, 0, [
        "Senior staff writer", "Contributing editor", "Science correspondent",
        "Research reporter", "Features writer", "Staff writer",
    ])
    beat = _pick(h, 2, [
        "physics and quantum technology",
        "climate and earth science",
        "AI, computing and engineering",
        "biology, genomics and medicine",
        "materials, chemistry and nanotech",
        "astronomy and planetary science",
    ])
    years = _int(h, 4, 3, 22)
    base = _pick(h, 8, [
        "Cambridge, UK", "Boston, MA", "Berlin, Germany", "Tokyo, Japan",
        "San Francisco, CA", "Toronto, Canada", "Cape Town, South Africa",
        "Amsterdam, Netherlands", "Singapore", "Sydney, Australia",
    ])
    return (f"{role} covering {beat}. {years} years on the science beat, "
            f"based in {base}. Files for Phys.org's research-news desk.")


def _author_articles(Article, name: str):
    return Article.query.filter_by(author_name=name).order_by(
        Article.published_at.desc()).all()


# --------------------------------------------------------------------- #
# SVG generators (author headshot / podcast cover / category banner)    #
# --------------------------------------------------------------------- #

_AVATAR_PALETTE = [
    ("#1a4a8a", "#cfe1ff"), ("#0d3b66", "#f4d35e"),
    ("#264653", "#e9c46a"), ("#2a9d8f", "#e0fbfc"),
    ("#6a4c93", "#ffd6a5"), ("#a83279", "#ffd1dc"),
    ("#3a506b", "#caf0f8"), ("#283618", "#dad7cd"),
]

_BANNER_PALETTE = [
    ("#0b2545", "#13315c"), ("#1d3557", "#457b9d"),
    ("#2d3142", "#bfc0c0"), ("#22223b", "#4a4e69"),
    ("#003049", "#669bbc"), ("#1b1b3a", "#9381ff"),
]


def _svg_avatar(name: str) -> str:
    h = _seed("avatar", name)
    bg, fg = _AVATAR_PALETTE[int(h[:2], 16) % len(_AVATAR_PALETTE)]
    parts = name.split()
    initials = (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 160">'
        f'<rect width="160" height="160" fill="{bg}"/>'
        f'<circle cx="80" cy="70" r="34" fill="{fg}" opacity="0.85"/>'
        f'<rect x="32" y="108" width="96" height="64" rx="14" fill="{fg}" opacity="0.6"/>'
        f'<text x="80" y="86" text-anchor="middle" font-family="Helvetica,Arial" '
        f'font-size="34" font-weight="700" fill="{bg}">{initials}</text>'
        '</svg>'
    )


def _svg_podcast(slug: str, title: str) -> str:
    h = _seed("podcast", slug)
    bg, fg = _BANNER_PALETTE[int(h[:2], 16) % len(_BANNER_PALETTE)]
    abbr = "".join(w[0] for w in title.split()[:3]).upper()
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240">'
        f'<defs><linearGradient id="g" x1="0" x2="1" y1="0" y2="1">'
        f'<stop offset="0" stop-color="{bg}"/><stop offset="1" stop-color="{fg}"/>'
        '</linearGradient></defs>'
        f'<rect width="240" height="240" fill="url(#g)"/>'
        f'<circle cx="120" cy="100" r="44" fill="#fff" opacity="0.18"/>'
        f'<circle cx="120" cy="100" r="22" fill="#fff" opacity="0.42"/>'
        f'<text x="120" y="200" text-anchor="middle" font-family="Helvetica,Arial" '
        f'font-size="36" font-weight="800" fill="#fff" opacity="0.92">{abbr}</text>'
        '</svg>'
    )


def _svg_banner(slug: str, label: str) -> str:
    h = _seed("banner", slug)
    bg, fg = _BANNER_PALETTE[int(h[:2], 16) % len(_BANNER_PALETTE)]
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 220">'
        f'<defs><linearGradient id="g" x1="0" x2="1" y1="0" y2="0">'
        f'<stop offset="0" stop-color="{bg}"/><stop offset="1" stop-color="{fg}"/>'
        '</linearGradient></defs>'
        f'<rect width="800" height="220" fill="url(#g)"/>'
        f'<circle cx="120" cy="110" r="60" fill="#fff" opacity="0.16"/>'
        f'<circle cx="240" cy="170" r="32" fill="#fff" opacity="0.1"/>'
        f'<circle cx="700" cy="60" r="40" fill="#fff" opacity="0.14"/>'
        f'<text x="400" y="120" text-anchor="middle" font-family="Helvetica,Arial" '
        f'font-size="44" font-weight="800" fill="#fff" letter-spacing="2">{label.upper()}</text>'
        f'<text x="400" y="158" text-anchor="middle" font-family="Helvetica,Arial" '
        f'font-size="16" fill="#fff" opacity="0.7">phys.org research news</text>'
        '</svg>'
    )


def _svg_video(slug: str, title: str) -> str:
    h = _seed("video", slug)
    bg, fg = _BANNER_PALETTE[int(h[:2], 16) % len(_BANNER_PALETTE)]
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 270">'
        f'<rect width="480" height="270" fill="{bg}"/>'
        f'<polygon points="200,95 200,175 280,135" fill="{fg}" opacity="0.85"/>'
        f'<text x="240" y="240" text-anchor="middle" font-family="Helvetica,Arial" '
        f'font-size="12" fill="#fff" opacity="0.75">Phys.org video</text>'
        '</svg>'
    )


# --------------------------------------------------------------------- #
# Page data builders                                                     #
# --------------------------------------------------------------------- #

def _most_popular_period_label(period: str) -> str:
    return {"daily": "Today", "weekly": "This week", "monthly": "This month"}.get(period, period.title())


def build_subsection(cat_slug, sub_slug, Category, Article):
    cat = Category.query.filter_by(slug=cat_slug).first()
    if cat is None:
        return None
    label = None
    for s, l in SUBSECTIONS.get(cat_slug, []):
        if s == sub_slug:
            label = l
            break
    if label is None:
        return None
    # Match articles whose subsection name slugifies to sub_slug, fallback to
    # any article in the category if the subsection has no exact matches.
    arts = [a for a in Article.query.filter_by(category_id=cat.id).order_by(
        Article.published_at.desc()).all()
            if _slugify(a.subsection or "") == sub_slug]
    if not arts:
        arts = Article.query.filter_by(category_id=cat.id).order_by(
            Article.published_at.desc()).limit(12).all()
    return {"category": cat, "subsection_slug": sub_slug,
            "subsection_label": label, "articles": arts}


def build_most_popular(period: str, Article):
    Period = {"daily": 1, "weekly": 7, "monthly": 30}
    days = Period.get(period)
    if days is None:
        return None
    arts = Article.query.order_by(Article.views.desc()).limit(40).all()
    # Deterministic subsetting by period anchor so the three pages differ.
    h = _seed("popular", period)
    n = {"daily": 12, "weekly": 24, "monthly": 36}[period]
    arts = arts[:n]
    return {"period": period, "period_label": _most_popular_period_label(period),
            "articles": arts, "anchor": h[:8]}


def build_podcast_detail(slug: str):
    for s, title, blurb, ep_count in PODCASTS:
        if s == slug:
            episodes = []
            for i in range(min(ep_count, 12)):
                eh = _seed("podcast-ep", slug, i)
                ep_n = ep_count - i
                episodes.append({
                    "n": ep_n,
                    "title": f"#{ep_n}: " + _pick(eh, 0, [
                        "What the new data really shows",
                        "Inside the lab, on the day of the discovery",
                        "The methods that made the headline",
                        "Why peer review caught (or missed) it",
                        "Three open questions the paper left behind",
                        "From preprint to press release",
                    ]),
                    "minutes": _int(eh, 4, 18, 64),
                    "published_at": GUI_REFERENCE_DATE - timedelta(days=i * 7 + 3),
                    "guest": _pick(eh, 8, [
                        "Dr. Renata Müller", "Prof. Adekunle Osei",
                        "Dr. Priya Subramanian", "Dr. Chen Zhao",
                        "Prof. Hannah Goldberg", "Dr. Mikael Lindgren",
                    ]),
                })
            return {"slug": slug, "title": title, "blurb": blurb,
                    "episode_count": ep_count, "episodes": episodes}
    return None


def build_video_list(Article):
    items = []
    for i, t in enumerate(VIDEOS_TOPICS):
        h = _seed("video", i)
        slug = _slugify(t)[:60] + f"-{i+1:02d}"
        items.append({
            "slug": slug,
            "title": t,
            "minutes": _int(h, 0, 2, 9),
            "views": _int(h, 4, 1200, 92000),
            "published_at": GUI_REFERENCE_DATE - timedelta(days=i * 3 + 2),
            "category": _pick(h, 8, ["physics", "earth", "technology", "biology",
                                     "chemistry", "astronomy", "nanotechnology"]),
        })
    return items


def build_video_detail(slug: str, Article):
    items = build_video_list(Article)
    for v in items:
        if v["slug"] == slug:
            h = _seed("video-detail", slug)
            v["transcript_excerpt"] = (
                "[00:00] " + _pick(h, 0, [
                    "Today we're talking to the team behind the paper.",
                    "Welcome to Phys.org Video — three minutes to the finding.",
                    "Here's the experiment in one sentence.",
                ]) + "\n[01:12] "
                + _pick(h, 4, [
                    "The key surprise was the magnitude of the effect.",
                    "Replication is the next step, and they're already planning it.",
                    "We asked an independent reviewer what stood out.",
                ])
            )
            return v
    return None


def build_journal_detail(slug: str, Article):
    # Find one or more articles whose source_journal slugifies to slug.
    journal_label = None
    arts = []
    for a in Article.query.all():
        if a.source_journal and _journal_slug(a.source_journal) == slug:
            arts.append(a)
            if journal_label is None:
                journal_label = a.source_journal
    if not arts:
        return None
    arts.sort(key=lambda a: a.published_at or GUI_REFERENCE_DATE, reverse=True)
    return {"slug": slug, "journal_label": journal_label, "articles": arts}


def build_journal_list(Article):
    seen = {}
    for a in Article.query.all():
        if a.source_journal:
            seen.setdefault(a.source_journal, 0)
            seen[a.source_journal] += 1
    rows = sorted(seen.items())
    return [{"slug": _journal_slug(j), "label": j, "count": c} for j, c in rows]


def build_author_list(Article):
    seen = {}
    for a in Article.query.all():
        if a.author_name:
            seen.setdefault(a.author_name, 0)
            seen[a.author_name] += 1
    rows = sorted(seen.items())
    return [{"slug": _author_slug(n), "label": n, "count": c} for n, c in rows]


def build_author_profile(slug: str, Article):
    target_name = None
    for a in Article.query.all():
        if a.author_name and _author_slug(a.author_name) == slug:
            target_name = a.author_name
            break
    if target_name is None:
        return None
    arts = _author_articles(Article, target_name)
    return {"slug": slug, "name": target_name, "bio": _build_author_bio(target_name),
            "articles": arts, "count": len(arts)}


def build_topic(slug: str, Article):
    for s, label, cat in TOPICS:
        if s == slug:
            tokens = [t for t in re.split(r"\W+", label.lower()) if len(t) > 3]
            arts = []
            for a in Article.query.all():
                blob = (a.title + " " + (a.subtitle or "") + " " + (a.body or "")).lower()
                if any(t in blob for t in tokens):
                    arts.append(a)
            arts.sort(key=lambda a: a.published_at or GUI_REFERENCE_DATE, reverse=True)
            arts = arts[:40]
            return {"slug": slug, "label": label, "category": cat, "articles": arts}
    return None


def build_subsite_hub(name: str, Article, Category):
    """research-news / medical-press / tech-xplore: each pulls a curated slice
    of articles from the main table to behave like the real subsites."""
    if name == "research-news":
        cats = ["physics", "astronomy", "chemistry"]
        title = "Research News — Phys.org"
        tagline = "Curated research highlights from the physical sciences."
    elif name == "medical-press":
        cats = ["biology"]
        title = "Medical Press"
        tagline = "Biology, medicine and health research, curated by Medical Press."
    elif name == "tech-xplore":
        cats = ["technology", "nanotechnology"]
        title = "Tech Xplore"
        tagline = "Technology, AI, robotics and engineering — by Tech Xplore."
    else:
        return None
    cat_ids = [c.id for c in Category.query.filter(Category.slug.in_(cats)).all()]
    arts = Article.query.filter(Article.category_id.in_(cat_ids)).order_by(
        Article.published_at.desc()).limit(40).all()
    return {"name": name, "title": title, "tagline": tagline, "articles": arts}


# --------------------------------------------------------------------- #
# Registration                                                           #
# --------------------------------------------------------------------- #

def register(app, db, Article, Category, Comment, User,
             NewsletterSubscription, ArticleVote, ArticleReport,
             CommentLike, CommentReport, AuthorFollow, TopicFollow,
             PodcastFollow, JournalFollow, TipSubmission, ContactMessage,
             AuthorContactMessage, ShareLog, UserPreferences, PollVote):

    # ---- SVG generators (served from /static-gen/) ------------------ #
    @app.route("/static-gen/avatar/<slug>.svg")
    def gen_avatar(slug):
        # Try to recover the source author name from the slug by scanning
        # the Article table; otherwise fall back to the slug itself.
        for a in Article.query.all():
            if a.author_name and _author_slug(a.author_name) == slug:
                return Response(_svg_avatar(a.author_name), mimetype="image/svg+xml")
        return Response(_svg_avatar(slug.replace("-", " ").title()),
                        mimetype="image/svg+xml")

    @app.route("/static-gen/podcast/<slug>.svg")
    def gen_podcast_cover(slug):
        for s, title, *_ in PODCASTS:
            if s == slug:
                return Response(_svg_podcast(slug, title), mimetype="image/svg+xml")
        return Response(_svg_podcast(slug, slug.title()), mimetype="image/svg+xml")

    @app.route("/static-gen/banner/<slug>.svg")
    def gen_banner(slug):
        return Response(_svg_banner(slug, slug.replace("-", " ").title()),
                        mimetype="image/svg+xml")

    @app.route("/static-gen/video/<slug>.svg")
    def gen_video_thumb(slug):
        return Response(_svg_video(slug, slug), mimetype="image/svg+xml")

    # ---- GET surfaces ----------------------------------------------- #

    @app.route("/subcategory/<cat_slug>/<sub_slug>")
    @app.route("/category/<cat_slug>/<sub_slug>")
    def gui_subsection(cat_slug, sub_slug):
        d = build_subsection(cat_slug, sub_slug, Category, Article)
        if d is None:
            abort(404)
        return render_template("gui_subsection.html", **d)

    @app.route("/most-popular/<period>")
    def gui_most_popular(period):
        d = build_most_popular(period, Article)
        if d is None:
            abort(404)
        return render_template("gui_most_popular.html", **d)

    @app.route("/podcasts")
    def gui_podcasts():
        return render_template("gui_podcasts.html", podcasts=PODCASTS)

    @app.route("/podcast/<slug>")
    def gui_podcast_detail(slug):
        d = build_podcast_detail(slug)
        if d is None:
            abort(404)
        return render_template("gui_podcast_detail.html", **d)

    @app.route("/videos")
    def gui_videos():
        return render_template("gui_videos.html", videos=build_video_list(Article))

    @app.route("/video/<slug>")
    def gui_video_detail(slug):
        v = build_video_detail(slug, Article)
        if v is None:
            abort(404)
        return render_template("gui_video_detail.html", video=v)

    @app.route("/journals")
    def gui_journals():
        return render_template("gui_journals.html", journals=build_journal_list(Article))

    @app.route("/journal/<slug>")
    def gui_journal_detail(slug):
        d = build_journal_detail(slug, Article)
        if d is None:
            abort(404)
        return render_template("gui_journal_detail.html", **d)

    @app.route("/authors")
    def gui_authors():
        return render_template("gui_authors.html", authors=build_author_list(Article))

    @app.route("/author/<slug>")
    def gui_author_profile(slug):
        d = build_author_profile(slug, Article)
        if d is None:
            abort(404)
        # Is the current user following this author?
        following = False
        if current_user.is_authenticated:
            following = AuthorFollow.query.filter_by(
                user_id=current_user.id, author_slug=slug).first() is not None
        return render_template("gui_author_profile.html", following=following, **d)

    @app.route("/topics")
    def gui_topics():
        return render_template("gui_topics.html", topics=TOPICS)

    @app.route("/topic/<slug>")
    def gui_topic_detail(slug):
        d = build_topic(slug, Article)
        if d is None:
            abort(404)
        following = False
        if current_user.is_authenticated:
            following = TopicFollow.query.filter_by(
                user_id=current_user.id, topic_slug=slug).first() is not None
        return render_template("gui_topic_detail.html", following=following, **d)

    @app.route("/research-news")
    def gui_research_news():
        d = build_subsite_hub("research-news", Article, Category)
        return render_template("gui_subsite.html", **d)

    @app.route("/medical-press")
    def gui_medical_press():
        d = build_subsite_hub("medical-press", Article, Category)
        return render_template("gui_subsite.html", **d)

    @app.route("/tech-xplore")
    def gui_tech_xplore():
        d = build_subsite_hub("tech-xplore", Article, Category)
        return render_template("gui_subsite.html", **d)

    @app.route("/newsletter")
    @app.route("/newsletter/subscribe")
    def gui_newsletter():
        return render_template("gui_newsletter.html", newsletters=NEWSLETTERS)

    @app.route("/newsletter/<slug>")
    def gui_newsletter_detail(slug):
        for s, title, blurb, cadence in NEWSLETTERS:
            if s == slug:
                return render_template("gui_newsletter_detail.html",
                                       slug=slug, title=title,
                                       blurb=blurb, cadence=cadence)
        abort(404)

    @app.route("/article/<slug>/comments")
    def gui_article_comments(slug):
        art = Article.query.filter_by(slug=slug).first_or_404()
        top = Comment.query.filter_by(article_id=art.id, parent_id=None) \
            .order_by(Comment.created_at).all()
        return render_template("gui_article_comments.html",
                               article=art, top_comments=top)

    @app.route("/article/<slug>/share")
    def gui_article_share(slug):
        art = Article.query.filter_by(slug=slug).first_or_404()
        return render_template("gui_article_share.html", article=art)

    @app.route("/article/<slug>/contact-author")
    def gui_article_contact_author(slug):
        art = Article.query.filter_by(slug=slug).first_or_404()
        return render_template("gui_article_contact_author.html", article=art)

    @app.route("/article/<slug>/submit-tip")
    def gui_article_submit_tip(slug):
        art = Article.query.filter_by(slug=slug).first_or_404()
        return render_template("gui_article_submit_tip.html", article=art)

    @app.route("/article/<slug>/report")
    def gui_article_report_page(slug):
        art = Article.query.filter_by(slug=slug).first_or_404()
        return render_template("gui_article_report.html", article=art)

    @app.route("/poll/<slug>")
    def gui_poll(slug):
        for s, q, choices in POLLS:
            if s == slug:
                voted = False
                user_choice = None
                if current_user.is_authenticated:
                    pv = PollVote.query.filter_by(
                        user_id=current_user.id, poll_slug=slug).first()
                    if pv:
                        voted = True
                        user_choice = pv.choice
                tallies = {}
                for c in choices:
                    n = PollVote.query.filter_by(poll_slug=slug, choice=c).count()
                    tallies[c] = n
                return render_template("gui_poll.html",
                                       slug=slug, question=q, choices=choices,
                                       voted=voted, user_choice=user_choice,
                                       tallies=tallies)
        abort(404)

    @app.route("/myaccount/preferences")
    @login_required
    def gui_preferences():
        prefs = UserPreferences.query.filter_by(user_id=current_user.id).first()
        return render_template("gui_preferences.html", prefs=prefs,
                               newsletters=NEWSLETTERS)

    @app.route("/myaccount/following")
    @login_required
    def gui_following():
        authors = AuthorFollow.query.filter_by(user_id=current_user.id).all()
        topics = TopicFollow.query.filter_by(user_id=current_user.id).all()
        podcasts = PodcastFollow.query.filter_by(user_id=current_user.id).all()
        journals = JournalFollow.query.filter_by(user_id=current_user.id).all()
        return render_template("gui_following.html", authors=authors,
                               topics=topics, podcasts=podcasts, journals=journals)

    @app.route("/contact")
    def gui_contact():
        return render_template("gui_contact.html")

    @app.route("/about")
    def gui_about():
        return render_template("gui_about.html")

    # ---- POST surfaces ---------------------------------------------- #

    def _csrf_ok():
        # CSRFProtect catches missing tokens for us — no extra check needed.
        return True

    @app.route("/newsletter/subscribe", methods=["POST"])
    def post_newsletter_subscribe():
        slug = request.form.get("newsletter_slug", "phys-daily")
        email = (request.form.get("email") or "").strip()
        uid = current_user.id if current_user.is_authenticated else None
        if not any(n[0] == slug for n in NEWSLETTERS):
            flash("Unknown newsletter.", "error")
            return redirect(url_for("gui_newsletter"))
        existing = NewsletterSubscription.query.filter_by(
            user_id=uid, email=email, newsletter_slug=slug).first()
        if existing is None:
            db.session.add(NewsletterSubscription(
                user_id=uid, email=email, newsletter_slug=slug,
                created_at=datetime.utcnow()))
            db.session.commit()
            flash(f"Subscribed to {slug}.", "success")
        else:
            flash("You are already subscribed.", "info")
        return redirect(url_for("gui_newsletter_detail", slug=slug))

    @app.route("/newsletter/unsubscribe", methods=["POST"])
    def post_newsletter_unsubscribe():
        slug = request.form.get("newsletter_slug")
        email = (request.form.get("email") or "").strip()
        uid = current_user.id if current_user.is_authenticated else None
        q = NewsletterSubscription.query.filter_by(newsletter_slug=slug)
        if uid:
            q = q.filter(
                (NewsletterSubscription.user_id == uid) |
                (NewsletterSubscription.email == email))
        else:
            q = q.filter_by(email=email)
        for s in q.all():
            db.session.delete(s)
        db.session.commit()
        flash("Unsubscribed.", "info")
        return redirect(url_for("gui_newsletter"))

    @app.route("/article/<slug>/vote", methods=["POST"])
    @login_required
    def post_article_vote(slug):
        art = Article.query.filter_by(slug=slug).first_or_404()
        direction = request.form.get("direction", "up")
        if direction not in ("up", "down"):
            flash("Invalid vote.", "error")
            return redirect(url_for("article_detail", slug=slug))
        existing = ArticleVote.query.filter_by(
            user_id=current_user.id, article_id=art.id).first()
        if existing:
            existing.direction = direction
            existing.created_at = datetime.utcnow()
        else:
            db.session.add(ArticleVote(user_id=current_user.id, article_id=art.id,
                                       direction=direction,
                                       created_at=datetime.utcnow()))
        db.session.commit()
        flash(f"Vote recorded ({direction}).", "success")
        return redirect(url_for("article_detail", slug=slug))

    @app.route("/article/<slug>/report", methods=["POST"])
    def post_article_report(slug):
        art = Article.query.filter_by(slug=slug).first_or_404()
        reason = request.form.get("reason", "other")
        text = (request.form.get("text") or "").strip()
        uid = current_user.id if current_user.is_authenticated else None
        db.session.add(ArticleReport(user_id=uid, article_id=art.id,
                                     reason=reason, text=text,
                                     created_at=datetime.utcnow()))
        db.session.commit()
        flash("Report submitted; our editors will review it.", "success")
        return redirect(url_for("article_detail", slug=slug))

    @app.route("/article/<slug>/contact-author", methods=["POST"])
    def post_contact_author(slug):
        art = Article.query.filter_by(slug=slug).first_or_404()
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip()
        body = (request.form.get("body") or "").strip()
        if not email or not body:
            flash("Email and message are required.", "error")
            return redirect(url_for("gui_article_contact_author", slug=slug))
        db.session.add(AuthorContactMessage(
            user_id=current_user.id if current_user.is_authenticated else None,
            article_id=art.id, author_name=art.author_name,
            sender_name=name, sender_email=email, body=body,
            created_at=datetime.utcnow()))
        db.session.commit()
        flash(f"Your message to {art.author_name} has been queued.", "success")
        return redirect(url_for("article_detail", slug=slug))

    @app.route("/article/<slug>/submit-tip", methods=["POST"])
    def post_submit_tip(slug):
        art = Article.query.filter_by(slug=slug).first_or_404()
        tip_text = (request.form.get("tip") or "").strip()
        email = (request.form.get("email") or "").strip()
        if not tip_text:
            flash("Tip text is required.", "error")
            return redirect(url_for("gui_article_submit_tip", slug=slug))
        db.session.add(TipSubmission(
            user_id=current_user.id if current_user.is_authenticated else None,
            article_id=art.id, tip_text=tip_text, email=email,
            created_at=datetime.utcnow()))
        db.session.commit()
        flash("Tip submitted to the editorial desk.", "success")
        return redirect(url_for("article_detail", slug=slug))

    @app.route("/article/<slug>/share/email", methods=["POST"])
    def post_share_email(slug):
        art = Article.query.filter_by(slug=slug).first_or_404()
        recipient = (request.form.get("recipient") or "").strip()
        db.session.add(ShareLog(
            user_id=current_user.id if current_user.is_authenticated else None,
            article_id=art.id, channel="email", recipient=recipient,
            created_at=datetime.utcnow()))
        db.session.commit()
        flash(f"Article shared with {recipient}.", "success")
        return redirect(url_for("gui_article_share", slug=slug))

    @app.route("/article/<slug>/share/social", methods=["POST"])
    def post_share_social(slug):
        art = Article.query.filter_by(slug=slug).first_or_404()
        channel = request.form.get("channel", "x")
        db.session.add(ShareLog(
            user_id=current_user.id if current_user.is_authenticated else None,
            article_id=art.id, channel=channel, recipient="",
            created_at=datetime.utcnow()))
        db.session.commit()
        flash(f"Shared to {channel}.", "success")
        return redirect(url_for("gui_article_share", slug=slug))

    @app.route("/comment/<int:cid>/like", methods=["POST"])
    @login_required
    def post_comment_like(cid):
        c = Comment.query.get_or_404(cid)
        existing = CommentLike.query.filter_by(
            user_id=current_user.id, comment_id=c.id).first()
        if existing:
            db.session.delete(existing)
            flash("Like removed.", "info")
        else:
            db.session.add(CommentLike(user_id=current_user.id, comment_id=c.id,
                                       created_at=datetime.utcnow()))
            flash("Comment liked.", "success")
        db.session.commit()
        return redirect(url_for("article_detail", slug=c.article.slug)
                        + f"#comment-{c.id}")

    @app.route("/comment/<int:cid>/report", methods=["POST"])
    def post_comment_report(cid):
        c = Comment.query.get_or_404(cid)
        reason = request.form.get("reason", "other")
        db.session.add(CommentReport(
            user_id=current_user.id if current_user.is_authenticated else None,
            comment_id=c.id, reason=reason,
            created_at=datetime.utcnow()))
        db.session.commit()
        flash("Comment reported.", "success")
        return redirect(url_for("article_detail", slug=c.article.slug))

    @app.route("/author/<slug>/follow", methods=["POST"])
    @login_required
    def post_author_follow(slug):
        existing = AuthorFollow.query.filter_by(
            user_id=current_user.id, author_slug=slug).first()
        if existing:
            db.session.delete(existing)
            flash("Unfollowed.", "info")
        else:
            db.session.add(AuthorFollow(user_id=current_user.id, author_slug=slug,
                                        created_at=datetime.utcnow()))
            flash("Following.", "success")
        db.session.commit()
        return redirect(url_for("gui_author_profile", slug=slug))

    @app.route("/topic/<slug>/follow", methods=["POST"])
    @login_required
    def post_topic_follow(slug):
        existing = TopicFollow.query.filter_by(
            user_id=current_user.id, topic_slug=slug).first()
        if existing:
            db.session.delete(existing)
            flash("Unfollowed topic.", "info")
        else:
            db.session.add(TopicFollow(user_id=current_user.id, topic_slug=slug,
                                       created_at=datetime.utcnow()))
            flash("Following topic.", "success")
        db.session.commit()
        return redirect(url_for("gui_topic_detail", slug=slug))

    @app.route("/podcast/<slug>/follow", methods=["POST"])
    @login_required
    def post_podcast_follow(slug):
        existing = PodcastFollow.query.filter_by(
            user_id=current_user.id, podcast_slug=slug).first()
        if existing:
            db.session.delete(existing)
            flash("Unfollowed podcast.", "info")
        else:
            db.session.add(PodcastFollow(user_id=current_user.id, podcast_slug=slug,
                                         created_at=datetime.utcnow()))
            flash("Following podcast.", "success")
        db.session.commit()
        return redirect(url_for("gui_podcast_detail", slug=slug))

    @app.route("/journal/<slug>/follow", methods=["POST"])
    @login_required
    def post_journal_follow(slug):
        existing = JournalFollow.query.filter_by(
            user_id=current_user.id, journal_slug=slug).first()
        if existing:
            db.session.delete(existing)
            flash("Unfollowed journal.", "info")
        else:
            db.session.add(JournalFollow(user_id=current_user.id, journal_slug=slug,
                                         created_at=datetime.utcnow()))
            flash("Following journal.", "success")
        db.session.commit()
        return redirect(url_for("gui_journal_detail", slug=slug))

    @app.route("/poll/<slug>/vote", methods=["POST"])
    @login_required
    def post_poll_vote(slug):
        choice = request.form.get("choice", "").strip()
        for s, _q, choices in POLLS:
            if s == slug and choice in choices:
                existing = PollVote.query.filter_by(
                    user_id=current_user.id, poll_slug=slug).first()
                if existing:
                    existing.choice = choice
                    existing.created_at = datetime.utcnow()
                else:
                    db.session.add(PollVote(user_id=current_user.id,
                                            poll_slug=slug, choice=choice,
                                            created_at=datetime.utcnow()))
                db.session.commit()
                flash("Vote recorded.", "success")
                return redirect(url_for("gui_poll", slug=slug))
        flash("Invalid poll or choice.", "error")
        return redirect(url_for("index"))

    @app.route("/myaccount/preferences", methods=["POST"])
    @login_required
    def post_preferences():
        prefs = UserPreferences.query.filter_by(user_id=current_user.id).first()
        if prefs is None:
            prefs = UserPreferences(user_id=current_user.id)
            db.session.add(prefs)
        prefs.daily_digest = request.form.get("daily_digest") == "on"
        prefs.weekly_digest = request.form.get("weekly_digest") == "on"
        prefs.breaking_alerts = request.form.get("breaking_alerts") == "on"
        prefs.preferred_categories = ",".join(
            request.form.getlist("preferred_categories"))
        prefs.updated_at = datetime.utcnow()
        db.session.commit()
        flash("Preferences saved.", "success")
        return redirect(url_for("gui_preferences"))

    @app.route("/contact", methods=["POST"])
    def post_contact():
        subject = (request.form.get("subject") or "").strip()
        body = (request.form.get("body") or "").strip()
        email = (request.form.get("email") or "").strip()
        if not email or not body:
            flash("Email and message are required.", "error")
            return redirect(url_for("gui_contact"))
        db.session.add(ContactMessage(
            user_id=current_user.id if current_user.is_authenticated else None,
            subject=subject, body=body, email=email,
            created_at=datetime.utcnow()))
        db.session.commit()
        flash("Your message has been sent to the editorial team.", "success")
        return redirect(url_for("gui_contact"))

    # ===================================================================== #
    # Phase 2 deepening (R11): advanced search, topic taxonomy, journal     #
    # email alerts, podcast episode pages, newsletter manage page.          #
    # All POST surfaces reuse existing runtime tables (NewsletterSubscription,
    # JournalFollow, TopicFollow) to preserve byte-identical reset — no new
    # tables are introduced.                                                 #
    # ===================================================================== #

    # ---- Advanced search ------------------------------------------------ #

    @app.route("/search/advanced")
    def gui_search_advanced():
        # Build facet vocabularies from the live Article table so they stay
        # in sync with the seeded data (and any future re-seed).
        journals = sorted({a.source_journal for a in Article.query.all()
                           if a.source_journal})
        institutions = sorted({a.source_institution for a in Article.query.all()
                               if a.source_institution})
        authors = sorted({a.author_name for a in Article.query.all()
                          if a.author_name})
        cats = Category.query.order_by(Category.sort_order, Category.name).all()
        # Year range derived from seeded data — used to populate the year
        # dropdown deterministically without exposing arbitrary years.
        years = sorted({a.published_at.year for a in Article.query.all()
                        if a.published_at}, reverse=True)
        return render_template("gui_search_advanced.html",
                               journals=journals, institutions=institutions,
                               authors=authors, categories=cats, years=years,
                               results=None, total=0, query_params={})

    @app.route("/search/advanced/results")
    def gui_search_advanced_results():
        q = (request.args.get("q") or "").strip()
        cat_slug = (request.args.get("category") or "").strip()
        journal = (request.args.get("journal") or "").strip()
        institution = (request.args.get("institution") or "").strip()
        author = (request.args.get("author") or "").strip()
        year_from = request.args.get("year_from", type=int)
        year_to = request.args.get("year_to", type=int)
        sort = (request.args.get("sort") or "relevance").strip()

        from sqlalchemy import or_ as _or, desc as _desc
        base = Article.query
        if cat_slug:
            c = Category.query.filter_by(slug=cat_slug).first()
            if c:
                base = base.filter(Article.category_id == c.id)
        if journal:
            base = base.filter(Article.source_journal == journal)
        if institution:
            base = base.filter(Article.source_institution == institution)
        if author:
            base = base.filter(Article.author_name == author)
        if year_from:
            base = base.filter(Article.published_at >= datetime(year_from, 1, 1))
        if year_to:
            base = base.filter(Article.published_at < datetime(year_to + 1, 1, 1))

        if q:
            tokens = [t for t in re.split(r"\W+", q.lower()) if len(t) > 1]
            if tokens:
                base = base.filter(_or(*[
                    _or(Article.title.ilike(f"%{t}%"),
                        Article.subtitle.ilike(f"%{t}%"),
                        Article.body.ilike(f"%{t}%"))
                    for t in tokens]))

        if sort == "newest":
            base = base.order_by(_desc(Article.published_at))
        elif sort == "popular":
            base = base.order_by(_desc(Article.views))
        else:
            # relevance — when q present, score by token hits; else newest
            base = base.order_by(_desc(Article.published_at))

        results = base.limit(60).all()

        # Re-rank by token-overlap if relevance + q.
        if sort == "relevance" and q:
            tokens = [t for t in re.split(r"\W+", q.lower()) if len(t) > 1]
            def _score(a):
                blob = ((a.title or "") + " " + (a.subtitle or "")
                        + " " + (a.body or "")).lower()
                return sum(1 for t in tokens if t in blob)
            results.sort(key=lambda a: (-_score(a),
                                        -(a.published_at.timestamp()
                                          if a.published_at else 0)))

        cats = Category.query.order_by(Category.sort_order, Category.name).all()
        journals = sorted({a.source_journal for a in Article.query.all()
                           if a.source_journal})
        institutions = sorted({a.source_institution for a in Article.query.all()
                               if a.source_institution})
        authors = sorted({a.author_name for a in Article.query.all()
                          if a.author_name})
        years = sorted({a.published_at.year for a in Article.query.all()
                        if a.published_at}, reverse=True)
        return render_template("gui_search_advanced.html",
                               journals=journals, institutions=institutions,
                               authors=authors, categories=cats, years=years,
                               results=results, total=len(results),
                               query_params={
                                   "q": q, "category": cat_slug,
                                   "journal": journal, "institution": institution,
                                   "author": author, "year_from": year_from,
                                   "year_to": year_to, "sort": sort,
                               })

    # ---- Topic taxonomy (parent-category grouped) ---------------------- #

    @app.route("/topic-taxonomy")
    def gui_topic_taxonomy():
        # Group TOPICS by category so the agent can navigate hierarchically.
        groups = {}
        for s, label, cat in TOPICS:
            groups.setdefault(cat, []).append({"slug": s, "label": label})
        # Sort by category slug for deterministic order, topics by label.
        rows = []
        for cat in sorted(groups.keys()):
            cat_obj = Category.query.filter_by(slug=cat).first()
            rows.append({
                "cat_slug": cat,
                "cat_name": cat_obj.name if cat_obj else cat.title(),
                "topics": sorted(groups[cat], key=lambda t: t["label"]),
            })
        return render_template("gui_topic_taxonomy.html", groups=rows,
                               total_topics=len(TOPICS))

    # ---- Journal new-issue email alerts -------------------------------- #

    @app.route("/journal/<slug>/alerts")
    def gui_journal_alerts(slug):
        d = build_journal_detail(slug, Article)
        if d is None:
            abort(404)
        # Distinct alert subscriptions reuse NewsletterSubscription with the
        # synthetic newsletter_slug prefix 'journal-alert:'. This avoids
        # introducing a new table and keeps reset byte-identical.
        synthetic_slug = f"journal-alert:{slug}"
        subscribed = False
        if current_user.is_authenticated:
            subscribed = NewsletterSubscription.query.filter_by(
                user_id=current_user.id,
                newsletter_slug=synthetic_slug).first() is not None
        return render_template("gui_journal_alerts.html",
                               slug=slug, journal_label=d["journal_label"],
                               article_count=len(d["articles"]),
                               subscribed=subscribed,
                               synthetic_slug=synthetic_slug)

    @app.route("/journal/<slug>/alerts", methods=["POST"])
    def post_journal_alerts(slug):
        d = build_journal_detail(slug, Article)
        if d is None:
            abort(404)
        email = (request.form.get("email") or "").strip()
        cadence = (request.form.get("cadence") or "weekly").strip()
        synthetic_slug = f"journal-alert:{slug}"
        uid = current_user.id if current_user.is_authenticated else None
        if not email and uid is None:
            flash("Email is required.", "error")
            return redirect(url_for("gui_journal_alerts", slug=slug))
        existing = NewsletterSubscription.query.filter_by(
            user_id=uid, email=email,
            newsletter_slug=synthetic_slug).first()
        if existing is None:
            db.session.add(NewsletterSubscription(
                user_id=uid, email=email,
                newsletter_slug=f"{synthetic_slug}:{cadence}",
                created_at=datetime.utcnow()))
            db.session.commit()
            flash(f"You will receive {cadence} alerts when new "
                  f"{d['journal_label']} articles publish.", "success")
        else:
            flash("Alert already enabled for this journal.", "info")
        return redirect(url_for("gui_journal_alerts", slug=slug))

    # ---- Podcast episode page ------------------------------------------ #

    @app.route("/podcast/<slug>/episode/<int:n>")
    def gui_podcast_episode(slug, n):
        d = build_podcast_detail(slug)
        if d is None:
            abort(404)
        ep = None
        for e in d["episodes"]:
            if e["n"] == n:
                ep = e
                break
        if ep is None:
            abort(404)
        # Deterministic show-notes / transcript snippet keyed by (slug, n).
        h = _seed("podcast-ep-detail", slug, n)
        ep = dict(ep)
        ep["show_notes"] = (
            "In this episode we discuss " + _pick(h, 0, [
                "the methods, the data and the open questions left behind.",
                "what the new finding really means and what comes next.",
                "the experiment, the analysis and the peer review timeline.",
                "the research front and three independent commentaries.",
            ])
            + " " + _pick(h, 4, [
                "Recorded live at the Phys.org research desk.",
                "Recorded remotely with the corresponding author.",
                "Recorded after the press conference.",
            ])
        )
        ep["transcript_excerpt"] = (
            "[00:00] Welcome to " + d["title"] + ", episode " + str(n) + ".\n"
            "[00:14] " + _pick(h, 8, [
                "Today's guest joins us from their lab.",
                "We begin with the headline finding.",
                "Let's start with the experimental setup.",
            ]) + "\n[02:30] " + _pick(h, 12, [
                "The key uncertainty here is replication.",
                "The next milestone is independent confirmation.",
                "The follow-up paper is already on preprint.",
            ])
        )
        return render_template("gui_podcast_episode.html",
                               podcast_slug=slug, podcast_title=d["title"],
                               episode=ep)

    # ---- Newsletter manage / multi-subscribe --------------------------- #

    @app.route("/newsletter/manage")
    @login_required
    def gui_newsletter_manage():
        # Show which of the 8 newsletters this user has active subscriptions
        # for, plus a single form to subscribe to multiple at once.
        my_subs = {s.newsletter_slug for s in
                   NewsletterSubscription.query.filter_by(
                       user_id=current_user.id).all()
                   if not s.newsletter_slug.startswith("journal-alert:")}
        return render_template("gui_newsletter_manage.html",
                               newsletters=NEWSLETTERS, my_subs=my_subs)

    @app.route("/newsletter/manage", methods=["POST"])
    @login_required
    def post_newsletter_manage():
        wanted = set(request.form.getlist("newsletters"))
        current = {s.newsletter_slug: s for s in
                   NewsletterSubscription.query.filter_by(
                       user_id=current_user.id).all()
                   if not s.newsletter_slug.startswith("journal-alert:")}
        added = 0
        removed = 0
        for slug, *_ in NEWSLETTERS:
            if slug in wanted and slug not in current:
                db.session.add(NewsletterSubscription(
                    user_id=current_user.id, email="",
                    newsletter_slug=slug, created_at=datetime.utcnow()))
                added += 1
            elif slug in current and slug not in wanted:
                db.session.delete(current[slug])
                removed += 1
        db.session.commit()
        flash(f"Subscriptions updated — added {added}, removed {removed}.",
              "success")
        return redirect(url_for("gui_newsletter_manage"))
