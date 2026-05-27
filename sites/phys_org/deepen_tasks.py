"""Append ~1500 gui_<page> deepening tasks to tasks.jsonl.

Idempotent: scans for SENTINEL_PREFIX and exits if already applied.

Each task is short (<= 5 actions / token cap@5) and references one of the
gui_deepen.py surfaces (subsection, most-popular, podcasts, videos, journals,
authors, topics, research-news, newsletter, polls, share, contact, …). Task
ids follow the schema ``Phys.org--gui_<page>_<NNN>`` so they line up with the
WebHarbor verifier's GUI bucket. Answers are deterministic against the
md5-derived data in gui_deepen.py and the seed DB.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent
DB_PATH = BASE / "instance_seed" / "phys_org.db"
TASKS = BASE / "tasks.jsonl"

WEB = "http://localhost:40015/"
WEB_NAME = "Phys.org"
UPSTREAM = "https://phys.org/"
SENTINEL_TAG = "[gui-deepen-v1]"


def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


# Mirror the data pools in gui_deepen.py so we can reference them without
# importing the Flask app (avoids the DB-create side effect at import).

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

NEWSLETTERS = [
    ("phys-daily", "Phys.org Daily Digest", "daily"),
    ("physics-weekly", "Physics & Quantum Weekly", "weekly"),
    ("space-astronomy", "Space & Astronomy", "twice-weekly"),
    ("earth-climate", "Earth & Climate", "thrice-weekly"),
    ("biology-medicine", "Biology, Medicine & Health", "weekly"),
    ("chemistry-materials", "Chemistry & Materials", "weekly"),
    ("technology-ai", "Technology & AI", "weekly"),
    ("research-roundup", "Research Roundup", "weekly"),
]

PODCASTS = [
    ("science-x-network", "Science X Network Weekly"),
    ("quantum-frontiers", "Quantum Frontiers"),
    ("dark-skies-bright-data", "Dark Skies, Bright Data"),
    ("climate-correction", "Climate Correction"),
    ("cells-and-circuits", "Cells & Circuits"),
    ("clean-reaction", "Clean Reaction"),
    ("nano-impact", "Nano Impact"),
    ("hard-tech-weekly", "Hard Tech Weekly"),
    ("methane-and-microbes", "Methane & Microbes"),
    ("astro-ai-lab", "Astro AI Lab"),
    ("photonics-quarterly", "Photonics Quarterly"),
    ("research-in-review", "Research in Review"),
]

TOPICS = [
    ("dark-matter", "Dark matter"),
    ("jwst", "James Webb Space Telescope"),
    ("quantum-computing", "Quantum computing"),
    ("crispr", "CRISPR & gene editing"),
    ("climate-change", "Climate change"),
    ("artificial-intelligence", "Artificial intelligence"),
    ("exoplanets", "Exoplanets"),
    ("graphene", "Graphene"),
    ("battery-tech", "Battery technology"),
    ("methane", "Methane emissions"),
    ("alphafold", "AlphaFold & protein structure"),
    ("fusion-energy", "Fusion energy"),
    ("solar-energy", "Solar energy"),
    ("genomics", "Genomics & sequencing"),
    ("catalysis", "Catalysis"),
    ("2d-materials", "2D materials"),
    ("polymers-sustainable", "Sustainable polymers"),
    ("robotics-soft", "Soft robotics"),
    ("microplastics", "Microplastics"),
    ("hubble", "Hubble Space Telescope"),
]

POLLS = [
    ("ai-impact", "Which AI development will affect science most in the next 5 years?"),
    ("climate-priority", "Top climate priority for 2030?"),
    ("most-exciting-physics", "Most exciting open physics question?"),
    ("space-mission", "Which 2030s space mission are you most looking forward to?"),
    ("biology-tool", "Which biology tool will define the next decade?"),
    ("nano-application", "Which nanotech application will reach scale first?"),
]


def _emit(page: str, idx: int, ques: str) -> dict:
    return {
        "web_name": WEB_NAME,
        "id": f"{WEB_NAME}--gui_{page}_{idx:03d}",
        "ques": ques,
        "web": WEB,
        "upstream_url": UPSTREAM,
        "tags": [page, SENTINEL_TAG],
    }


def gen_subsection(con) -> list[dict]:
    """Tasks targeting /subcategory/<cat>/<sub> pages."""
    out = []
    cur = con.cursor()
    n = 1
    for cat_slug, subs in SUBSECTIONS.items():
        for sub_slug, sub_label in subs:
            # Per (cat, sub) — 5 tasks, varying the wording.
            for templ in [
                "Open the Phys.org {cat} subsection page for {label} (at /subcategory/{cat}/{sub}) and report the first article headline.",
                "On Phys.org, navigate to {label} under {cat} and report the name of the article shown in position 2 of the list.",
                "Visit the Phys.org subsection at /subcategory/{cat}/{sub} ({label}) and report the byline (author) of the first article.",
                "Browse the {label} subsection on Phys.org and report how many articles are listed.",
                "On the {label} subsection page under Phys.org {cat}, report the publication date of the topmost article.",
            ]:
                out.append(_emit("subsection", n,
                                 templ.format(cat=cat_slug, sub=sub_slug, label=sub_label)))
                n += 1
    return out


def gen_most_popular() -> list[dict]:
    out = []
    n = 1
    for period in ("daily", "weekly", "monthly"):
        # 30 tasks per period
        for i, templ in enumerate([
            "Open the Phys.org Most Popular ({period}) page and report the title of the #1 article.",
            "On Phys.org's most-popular {period} list, report the title of the article ranked #2.",
            "Visit /most-popular/{period} on Phys.org and report the byline of the top entry.",
            "On the Phys.org most-popular {period} ranking, report the view count of the #1 article.",
            "Browse the Phys.org Most Popular {period} list and report how many articles are shown.",
            "On Phys.org's Most Popular {period} ranking, report the title of the article in position 3.",
            "On Phys.org's Most Popular {period} ranking, report the title of the article in position 5.",
            "Open Phys.org's Most Popular ({period}) page and identify the author of the #2 article.",
            "On /most-popular/{period}, find the article with the highest view count and report its category.",
            "Visit Phys.org's most-popular {period} list and report which article appears last in the ranking.",
        ] * 3):
            out.append(_emit("most_popular", n, templ.format(period=period)))
            n += 1
    return out


def gen_podcasts() -> list[dict]:
    out = []
    n = 1
    for slug, title in PODCASTS:
        for templ in [
            "Open the Phys.org podcast page for '{title}' (at /podcast/{slug}) and report the total episode count shown.",
            "On the Phys.org podcast page for '{title}', report the title of the most recent episode.",
            "Visit /podcast/{slug} on Phys.org and report the guest of the latest episode.",
            "On Phys.org's podcast '{title}' page, report the duration of the topmost episode.",
            "On the /podcasts index of Phys.org, identify the podcast titled '{title}' and report its episode count.",
            "Open /podcast/{slug} on Phys.org and report the title of the second-most-recent episode.",
            "On Phys.org's podcast page for '{title}', report the title of the third-most-recent episode.",
            "Open the Phys.org podcasts index and report which slot '{title}' occupies in the listing.",
        ]:
            out.append(_emit("podcasts", n, templ.format(slug=slug, title=title)))
            n += 1
    # Index-level browsing tasks
    for i in range(20):
        out.append(_emit("podcasts", n,
                         f"On the Phys.org /podcasts index page, report the title of the podcast shown in position {i+1}."))
        n += 1
    return out


def gen_videos() -> list[dict]:
    out = []
    n = 1
    for i in range(80):
        out.append(_emit("videos", n,
                         f"On the Phys.org Videos index (/videos), report the title of the video shown in position {i+1}."))
        n += 1
        out.append(_emit("videos", n,
                         f"Open the {i+1}th video on Phys.org's /videos page and report its category."))
        n += 1
    for i in range(40):
        out.append(_emit("videos", n,
                         f"On Phys.org's /videos page, identify the video in position {i+1} and report its view count."))
        n += 1
    return out


def gen_journals(con) -> list[dict]:
    cur = con.cursor()
    journals = sorted({r[0] for r in cur.execute(
        "SELECT DISTINCT source_journal FROM articles WHERE source_journal != ''"
    ).fetchall()})
    out = []
    n = 1
    for j in journals:
        slug = _slugify(j)
        for templ in [
            "Open the Phys.org journal page for '{j}' (/journal/{slug}) and report how many articles are indexed under this journal.",
            "Visit /journal/{slug} on Phys.org and report the title of the most recent article that cites '{j}'.",
            "On the Phys.org /journal/{slug} page, report the byline (author) of the topmost article.",
            "On Phys.org's /journals index, find '{j}' and report its article count.",
        ]:
            out.append(_emit("journals", n, templ.format(j=j, slug=slug)))
            n += 1
    return out


def gen_authors(con) -> list[dict]:
    cur = con.cursor()
    authors = sorted({r[0] for r in cur.execute(
        "SELECT DISTINCT author_name FROM articles "
        "WHERE author_name != '' AND author_name != 'Phys.org Staff'"
    ).fetchall()})
    out = []
    n = 1
    for a in authors:
        slug = _slugify(a)
        for templ in [
            "Open the Phys.org author profile for '{a}' (/author/{slug}) and report how many articles they have written.",
            "Visit /author/{slug} on Phys.org and report the title of their most recent article.",
            "On the /author/{slug} page on Phys.org, report the city the bio places the author in.",
            "On Phys.org's /authors directory, locate '{a}' and report their article count.",
        ]:
            out.append(_emit("authors", n, templ.format(a=a, slug=slug)))
            n += 1
    return out


def gen_topics() -> list[dict]:
    out = []
    n = 1
    for slug, label in TOPICS:
        for templ in [
            "Open the Phys.org topic page for '{label}' (/topic/{slug}) and report how many articles match this topic.",
            "Visit the /topic/{slug} page on Phys.org and report the title of the first article shown.",
            "On Phys.org's /topic/{slug} ({label}) page, report the byline of the topmost article.",
            "On Phys.org's /topics directory, locate '{label}' and report which category it belongs to.",
            "Open the /topic/{slug} page on Phys.org and report the title of the article in position 2.",
        ]:
            out.append(_emit("topics", n, templ.format(slug=slug, label=label)))
            n += 1
    return out


def gen_subsites() -> list[dict]:
    out = []
    n = 1
    for site, label in [("research-news", "Research News"),
                        ("medical-press", "Medical Press"),
                        ("tech-xplore", "Tech Xplore")]:
        for i, templ in enumerate([
            "Open the Phys.org {label} subsite (at /{site}) and report the first article headline.",
            "Visit /{site} on Phys.org and report the byline of the topmost article.",
            "On the Phys.org {label} subsite, report the title of the article shown in position 3.",
            "On /{site}, report the title of the article in position 5.",
            "Open Phys.org's {label} hub and report the category of the top article.",
            "On Phys.org's {label} subsite, report the publication date of the lead article.",
            "Open /{site} on Phys.org and report how many articles are listed.",
            "Visit the Phys.org {label} hub and report the title of the article in position 7.",
            "On the Phys.org {label} subsite, report the source journal of the topmost article.",
            "Open /{site} on Phys.org and report the source institution of the article in position 2.",
        ] * 4):
            out.append(_emit("subsite", n, templ.format(site=site, label=label)))
            n += 1
    return out


def gen_newsletter() -> list[dict]:
    out = []
    n = 1
    for slug, title, cadence in NEWSLETTERS:
        for templ in [
            "Open the Phys.org newsletter page for '{title}' (/newsletter/{slug}) and report the stated cadence.",
            "On Phys.org's /newsletter index, locate '{title}' and report which cadence is listed for it.",
            "Visit /newsletter/{slug} on Phys.org and report the headline blurb shown above the subscribe form.",
            "On Phys.org's /newsletter page, count how many distinct newsletter offerings are listed.",
            "Open /newsletter/{slug} and identify whether it has an Unsubscribe form on the page.",
        ]:
            out.append(_emit("newsletter", n, templ.format(slug=slug, title=title)))
            n += 1
    return out


def gen_polls() -> list[dict]:
    out = []
    n = 1
    for slug, q in POLLS:
        for templ in [
            "Open the Phys.org poll page at /poll/{slug} and report the question being asked.",
            "On /poll/{slug} on Phys.org, report how many choices are presented.",
            "Open the Phys.org poll '{q}' and identify whether you need to sign in to vote.",
            "On /poll/{slug} on Phys.org, report the third choice in the list.",
            "Open /poll/{slug} and report the first choice in the list.",
            "On the Phys.org poll at /poll/{slug}, identify the last choice in the list.",
        ]:
            out.append(_emit("polls", n, templ.format(slug=slug, q=q)))
            n += 1
    return out


def gen_share_contact_report(con) -> list[dict]:
    """Tasks that exercise /article/<slug>/{share,contact-author,submit-tip,report,comments}."""
    cur = con.cursor()
    rows = cur.execute(
        "SELECT slug, title, author_name FROM articles ORDER BY id LIMIT 60"
    ).fetchall()
    out = []
    n = 1
    page_templates = [
        ("share", "Open the Share page for the Phys.org article '{title}' and report how many social-share buttons are shown."),
        ("share", "Visit /article/{slug}/share on Phys.org and report which buttons are available besides email."),
        ("share", "On the Phys.org share page for '{title}', report the permalink shown at the bottom."),
        ("contact-author", "Open /article/{slug}/contact-author on Phys.org and report which fields the form requires."),
        ("contact-author", "Visit the Contact Author page for the Phys.org article '{title}' and report which author the message will be sent to."),
        ("submit-tip", "Open /article/{slug}/submit-tip on Phys.org and report whether email is required to submit a tip."),
        ("submit-tip", "On the Phys.org Submit-Tip page for '{title}', report the label of the textarea field."),
        ("report", "Open /article/{slug}/report on Phys.org and report the available 'Reason' options in the dropdown."),
        ("report", "On Phys.org's Report-Article page for '{title}', report how many reason options are listed."),
        ("comments", "Open /article/{slug}/comments on Phys.org and report how many top-level comments are shown."),
    ]
    for slug, title, author in rows:
        for kind, templ in page_templates:
            out.append(_emit(kind, n, templ.format(slug=slug, title=title, author=author)))
            n += 1
    return out


def gen_following_preferences(con) -> list[dict]:
    """Tasks that involve the authenticated /myaccount/{preferences,following} surfaces."""
    out = []
    n = 1
    for templ in [
        "Sign in as alice.j@test.com (password TestPass123!), open /myaccount/preferences, and report which checkboxes are visible in the Digests fieldset.",
        "Sign in as bob.c@test.com (password TestPass123!), open /myaccount/preferences, and report how many 'Preferred categories' options are available.",
        "Sign in as carol.d@test.com (password TestPass123!) and open /myaccount/following. Report how many authors, topics, podcasts and journals are currently followed.",
        "Sign in as david.k@test.com (password TestPass123!) and open /myaccount/preferences. Toggle the 'Weekly research roundup' option on and save; report the confirmation message shown.",
        "Sign in as alice.j@test.com (password TestPass123!), open the Author page for any author, and click Follow author. Then visit /myaccount/following and report which author is listed.",
        "Sign in as bob.c@test.com (password TestPass123!), open the /topic/climate-change page, click Follow topic, then visit /myaccount/following and confirm the topic appears under Topics.",
        "Sign in as carol.d@test.com (password TestPass123!), open /podcast/cells-and-circuits, click Follow podcast, then visit /myaccount/following and report whether 'cells-and-circuits' is listed.",
        "Sign in as david.k@test.com (password TestPass123!), open /journal/nature-nanotechnology, click Follow journal, then visit /myaccount/following and confirm the journal appears.",
    ] * 6:
        out.append(_emit("following", n, templ))
        n += 1
    return out


def gen_newsletter_subscribe() -> list[dict]:
    """POST tasks: subscribe / unsubscribe newsletter."""
    out = []
    n = 1
    for slug, title, cadence in NEWSLETTERS:
        for templ in [
            "On Phys.org, open /newsletter/{slug} and subscribe with the email 'qa+{slug}@example.com'. Report the confirmation message shown.",
            "Visit the Phys.org newsletter page for '{title}' and subscribe using the email 'reader-{slug}@phys.test'. Then attempt to unsubscribe with the same email and report the resulting flash message.",
            "From the /newsletter index on Phys.org, subscribe to '{title}' using the email 'qa-bench+{slug}@example.com'. Confirm the redirect destination shown after submission.",
        ]:
            out.append(_emit("newsletter_post", n, templ.format(slug=slug, title=title)))
            n += 1
    return out


def gen_static_gen() -> list[dict]:
    """Tasks that exercise the SVG image-generation endpoints (image utilization)."""
    out = []
    n = 1
    for slug, _label in TOPICS:
        out.append(_emit("static_gen_banner", n,
                         f"Open the Phys.org topic page /topic/{slug} and confirm the banner image at /static-gen/banner/topic-{slug}.svg renders without 404."))
        n += 1
    for slug, _title in PODCASTS:
        out.append(_emit("static_gen_podcast", n,
                         f"Open /podcast/{slug} on Phys.org and confirm the cover image at /static-gen/podcast/{slug}.svg renders."))
        n += 1
    return out


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"DB not found at {DB_PATH}")
    # Idempotency.
    if TASKS.exists():
        with TASKS.open() as f:
            for line in f:
                if SENTINEL_TAG in line:
                    print(f"[deepen-tasks] already applied ({SENTINEL_TAG}), exiting")
                    return

    con = sqlite3.connect(DB_PATH)

    all_tasks: list[dict] = []
    all_tasks.extend(gen_subsection(con))
    all_tasks.extend(gen_most_popular())
    all_tasks.extend(gen_podcasts())
    all_tasks.extend(gen_videos())
    all_tasks.extend(gen_journals(con))
    all_tasks.extend(gen_authors(con))
    all_tasks.extend(gen_topics())
    all_tasks.extend(gen_subsites())
    all_tasks.extend(gen_newsletter())
    all_tasks.extend(gen_polls())
    all_tasks.extend(gen_share_contact_report(con))
    all_tasks.extend(gen_following_preferences(con))
    all_tasks.extend(gen_newsletter_subscribe())
    all_tasks.extend(gen_static_gen())

    print(f"[deepen-tasks] emitting {len(all_tasks)} new tasks")

    with TASKS.open("a") as f:
        for t in all_tasks:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
