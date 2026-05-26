"""Phys.org mirror — idempotent seed data.

Loads ``scraped_data/phys_data.json`` (real RSS-derived articles) and synthesizes
the side data agents need: source journals/institutions, additional body text,
benchmark users with saved articles + comments + search history.

The byte-identical reset invariant requires that each ``seed_*`` function is a
no-op when the DB is already populated. Per-row gates aren't enough — even an
empty ``commit()`` bumps SQLite metadata.
"""
import json
import os
import random
import re
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'scraped_data', 'phys_data.json')

# Pinned reference date so "published_at" values are stable across rebuilds and
# the byte-identical reset invariant holds.
MIRROR_REFERENCE_DATE = datetime(2026, 5, 12, 12, 0, 0)


CATEGORIES = [
    ('physics', 'Physics',
     'Latest news in physics, materials science, optics, quantum and superconductivity.', 10),
    ('earth', 'Earth Sciences',
     'Climate, geology, oceanography and the planet that supports us.', 20),
    ('technology', 'Technology',
     'AI, robotics, computing, energy, and engineering breakthroughs.', 30),
    ('biology', 'Biology',
     'Cell biology, ecology, evolution, plants and animals.', 40),
    ('chemistry', 'Chemistry',
     'Molecules, reactions, materials and analytical chemistry.', 50),
    ('astronomy', 'Astronomy & Space',
     'Cosmology, planetary science, missions and space exploration.', 60),
    ('nanotechnology', 'Nanotechnology',
     'Nanomaterials, nanoelectronics, bio- and nano-technology.', 70),
    ('other', 'Other Sciences',
     'Mathematics, social sciences, archaeology and education.', 80),
]


# Pools used to synthesize plausible journal / institution data per category.
# Real phys.org articles cite these journals heavily; using them keeps the
# detail page realistic. Each tuple is (journal, parent publisher).
JOURNALS_BY_CATEGORY = {
    'physics': [
        'Physical Review Letters', 'Nature Physics', 'Physical Review B',
        'Reviews of Modern Physics', 'New Journal of Physics',
        'Physical Review Applied', 'Optics Express', 'Nature Photonics',
    ],
    'earth': [
        'Nature Geoscience', 'Geophysical Research Letters',
        'Journal of Climate', 'Earth and Planetary Science Letters',
        'Nature Climate Change', 'Geology', 'Journal of Geophysical Research: Atmospheres',
    ],
    'technology': [
        'Nature Electronics', 'IEEE Transactions on Robotics',
        'ACM Computing Surveys', 'Joule', 'Energy & Environmental Science',
        'Nature Machine Intelligence', 'Science Robotics',
    ],
    'biology': [
        'Cell', 'Nature', 'Current Biology', 'Proceedings of the National Academy of Sciences',
        'eLife', 'Nature Ecology & Evolution', 'PLOS Biology', 'Molecular Ecology',
    ],
    'chemistry': [
        'Journal of the American Chemical Society', 'Nature Chemistry',
        'Angewandte Chemie International Edition', 'ACS Central Science',
        'Chemical Science', 'Inorganic Chemistry',
    ],
    'astronomy': [
        'The Astrophysical Journal', 'Monthly Notices of the Royal Astronomical Society',
        'Astronomy & Astrophysics', 'Nature Astronomy', 'Icarus',
        'Astrophysical Journal Letters',
    ],
    'nanotechnology': [
        'Nature Nanotechnology', 'ACS Nano', 'Nano Letters',
        'Advanced Materials', 'Small', 'npj 2D Materials and Applications',
    ],
    'other': [
        'Journal of Archaeological Science', 'Nature Human Behaviour',
        'PNAS', 'Science Advances', 'PLOS ONE', 'Proceedings of the Royal Society B',
    ],
}


INSTITUTIONS_BY_CATEGORY = {
    'physics': [
        'Massachusetts Institute of Technology', 'Stanford University',
        'CERN', 'University of Cambridge', 'ETH Zurich', 'Caltech',
        'Max Planck Institute for Quantum Optics', 'Technion',
        'Princeton University', 'Argonne National Laboratory',
    ],
    'earth': [
        'NOAA', 'University of Washington', 'Scripps Institution of Oceanography',
        'University of Oxford', 'Potsdam Institute for Climate Impact Research',
        'Woods Hole Oceanographic Institution', 'NASA Goddard Space Flight Center',
        'Columbia University',
    ],
    'technology': [
        'Carnegie Mellon University', 'Google DeepMind', 'IBM Research',
        'University of California, Berkeley', 'University of Toronto',
        'EPFL', 'Microsoft Research', 'KAIST', 'Tsinghua University',
    ],
    'biology': [
        'Harvard Medical School', 'University of Oxford',
        'Howard Hughes Medical Institute', 'EMBL-EBI',
        'Salk Institute', 'University of Tokyo', 'Wellcome Sanger Institute',
        'University of Pennsylvania',
    ],
    'chemistry': [
        'Northwestern University', 'University of Chicago',
        'University of California, Los Angeles', 'Scripps Research',
        'University of Bristol', 'Tokyo Institute of Technology',
        'Imperial College London',
    ],
    'astronomy': [
        'NASA Jet Propulsion Laboratory', 'European Southern Observatory',
        'Space Telescope Science Institute', 'Harvard-Smithsonian Center for Astrophysics',
        'Max Planck Institute for Astronomy', 'Caltech', 'University of Arizona',
    ],
    'nanotechnology': [
        'KAIST', 'Rice University', 'IBM Research – Zurich',
        'National University of Singapore', 'University of Manchester',
        'Tsinghua University', 'Lawrence Berkeley National Laboratory',
    ],
    'other': [
        'University of Oxford', 'Max Planck Institute for the Science of Human History',
        'University of Chicago', 'London School of Economics',
        'University of Cape Town', 'Hebrew University of Jerusalem',
    ],
}


# Synthetic body filler. Only used when the RSS description is too short.
GENERIC_PARAGRAPHS = [
    "The findings, the team writes, open new questions about how robust the underlying assumptions of the field really are, and suggest that further independent replications will be needed before the wider community converges on a single explanation.",
    "Beyond the immediate result, the work hints at practical applications. The authors caution, however, that translating these laboratory observations into deployable systems is likely to take several more years of engineering effort and additional safety review.",
    "Independent researchers not involved in the study described the data as 'compelling' and 'a useful starting point,' while noting that some of the boldest claims will need to be tested in larger and more diverse samples before being accepted as established science.",
]


def _slugify(text: str, maxlen: int = 70) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text or "").strip("-").lower()
    return s[:maxlen] or "article"


def _parse_pub(s: str) -> datetime:
    """Parse RSS pubDate. Falls back to MIRROR_REFERENCE_DATE.

    strptime's %Z only accepts UTC/GMT and the local TZ on most platforms, so
    real RSS dates like 'EDT' / 'PDT' don't parse. Strip the trailing zone
    word (or +0000-style offset) and parse the remainder."""
    if not s:
        return MIRROR_REFERENCE_DATE
    s = s.strip()
    m = re.match(r'(.+?\d{2}:\d{2}:\d{2})\s*\S+', s)
    base = m.group(1) if m else s
    for fmt in ("%a, %d %b %Y %H:%M:%S",
                "%a, %d %b %Y %H:%M",
                "%a, %d %b %Y"):
        try:
            return datetime.strptime(base.strip(), fmt)
        except Exception:
            continue
    return MIRROR_REFERENCE_DATE


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _build_body(rss_desc: str, title: str, *, rng: random.Random) -> str:
    """Return paragraph-separated body text. Use the RSS description as the
    lede and append synthetic-but-plausible follow-on paragraphs so each
    article has at least 3 paragraphs."""
    lede = _strip_html(rss_desc) or title
    paragraphs = [lede]
    pool = GENERIC_PARAGRAPHS[:]
    rng.shuffle(pool)
    paragraphs.append(pool[0])
    paragraphs.append(pool[1])
    return "\n\n".join(paragraphs)


def seed_database(db, User, Category, Article, Comment, bcrypt):
    if Article.query.count() > 0:
        return

    # Seed categories first (only if empty — gated by the outer check on
    # Article, but we double-check here to keep the function self-contained).
    cat_id_map = {}
    for slug, name, desc, order in CATEGORIES:
        c = Category.query.filter_by(slug=slug).first()
        if c is None:
            c = Category(slug=slug, name=name, description=desc, sort_order=order)
            db.session.add(c)
            db.session.flush()
        cat_id_map[slug] = c.id

    if not os.path.exists(DATA_FILE):
        # No scraped data — bail without committing anything else, leaving
        # only categories. (The reset invariant still holds because we did
        # commit categories on the first call; subsequent calls are gated.)
        db.session.commit()
        return

    with open(DATA_FILE) as f:
        items = json.load(f)

    # Pre-baked format: every field (slug, body, author_name, journal,
    # institution, doi_url, image_filename, subsection, category_slug,
    # published_at, views, featured, id) is stored verbatim in the JSON.
    # Rationale: keeping the JSON pre-baked is what enforces the
    # byte-identical reset invariant. The original RSS-scrape pipeline used
    # multiple seeded random.Random streams to pick journals / institutions
    # / view counts / featured ids; any drift in Python's PRNG, in the
    # category-pool ordering, or in the input RSS would silently shift
    # those values. Freezing the post-synthesis result instead means a
    # rebuild only depends on this single committed JSON.
    for it in items:
        published = datetime.strptime(it['published_at'], '%Y-%m-%d %H:%M:%S.%f')
        cat_slug = it.get('category_slug') or 'other'
        if cat_slug not in cat_id_map:
            cat_slug = 'other'
        art = Article(
            id=it['id'],
            slug=it['slug'],
            title=it['title'],
            subtitle=it.get('subtitle') or '',
            body=it.get('body') or '',
            author_name=it.get('author_name') or 'Phys.org Staff',
            source_journal=it.get('source_journal') or '',
            source_institution=it.get('source_institution') or '',
            doi_url=it.get('doi_url') or '',
            image_filename=it.get('image_filename') or '',
            subsection=it.get('subsection') or '',
            category_id=cat_id_map[cat_slug],
            published_at=published,
            views=int(it.get('views') or 0),
            featured=bool(it.get('featured')),
        )
        db.session.add(art)

    db.session.commit()


# ---------------------------------------------------------------------------
# Benchmark users
# ---------------------------------------------------------------------------

BENCH_USERS = [
    dict(username='alice_j', email='alice.j@test.com', full_name='Alice Johnson',
         bio='PhD student in astrophysics. Saving everything about exoplanets and dark matter.',
         location='Boston, MA', interests='astronomy,physics'),
    dict(username='bob_c', email='bob.c@test.com', full_name='Bob Chen',
         bio='Climate-tech reporter. Following ocean carbon, methane and renewables stories.',
         location='Seattle, WA', interests='earth,technology'),
    dict(username='carol_d', email='carol.d@test.com', full_name='Carol Davis',
         bio='Computational biologist. Long-time fan of CRISPR, protein design and ecology.',
         location='Cambridge, UK', interests='biology,chemistry'),
    dict(username='david_k', email='david.k@test.com', full_name='David Kim',
         bio='Materials engineer. Reads everything tagged Nanotechnology, Optics & Photonics.',
         location='Seoul, South Korea', interests='nanotechnology,physics'),
]
PASSWORD = 'TestPass123!'

# Pre-generated bcrypt hash for PASSWORD. bcrypt.generate_password_hash uses a
# random salt on every call, which would break the byte-identical reset
# invariant — so we pin one valid hash here. Verified at boot time by
# bcrypt.check_password_hash; rotate by running:
#   from flask_bcrypt import Bcrypt; from flask import Flask
#   print(Bcrypt(Flask(__name__)).generate_password_hash('TestPass123!').decode())
PINNED_PASSWORD_HASH = (
    '$2b$12$zV7HfiJmZTqLsgP30kyvJemamXfJyBv66FPuQOrwYXXsyQvrafvie'
)


# Stable user-id mapping: 1001..1004 (well above article-derived ids so we
# don't collide with any future re-numbering).
USER_ID_BASE = 1001


def _pick_articles(Article, *, where: dict, n: int, seed: str) -> list:
    """Return up to n articles matching ``where`` filters, deterministically
    ordered by id so the result is identical across rebuilds."""
    q = Article.query
    for k, v in where.items():
        q = q.filter(getattr(Article, k) == v)
    items = q.order_by(Article.id).all()
    rng = random.Random(seed)
    rng.shuffle(items)
    return items[:n]


def seed_benchmark_users(db, User, Category, Article, Comment, SavedArticle, SearchHistory, bcrypt):
    if User.query.filter_by(email='alice.j@test.com').first():
        return

    # Categories must exist (created by seed_database). Look up ids.
    pw_hash = PINNED_PASSWORD_HASH

    user_objs = {}
    for i, u in enumerate(BENCH_USERS):
        obj = User(
            id=USER_ID_BASE + i,
            username=u['username'],
            email=u['email'],
            full_name=u['full_name'],
            bio=u['bio'],
            location=u['location'],
            interests=u['interests'],
            password_hash=pw_hash,
            created_at=MIRROR_REFERENCE_DATE - timedelta(days=180 + i * 30),
        )
        db.session.add(obj)
        user_objs[u['username']] = obj
    db.session.flush()

    # Save articles aligned to each user's interests so saved-list tasks have
    # depth and disambiguation candidates.
    save_targets = {
        'alice_j': [
            ('astronomy', 4),
            ('physics', 2),
        ],
        'bob_c': [
            ('earth', 4),
            ('technology', 2),
        ],
        'carol_d': [
            ('biology', 4),
            ('chemistry', 2),
        ],
        'david_k': [
            ('nanotechnology', 3),
            ('physics', 2),
        ],
    }
    next_save_id = 1
    save_notes_by_user = {
        'alice_j': ['Read for thesis chapter 3', 'Cite in proposal', 'Follow-up reading',
                    'Discuss with advisor', 'Seminar candidate', 'Review for journal club'],
        'bob_c': ['Story idea — angle 2', 'Lead source candidate', 'Background reading',
                  'Quote for upcoming feature', 'Verify with NOAA contact', 'Pitch to editor'],
        'carol_d': ['Methods section', 'Lab meeting share', 'Forward to postdocs',
                    'Compare with our pipeline', 'Re-read after deadline', 'Class material'],
        'david_k': ['Material spec lookup', 'Patent landscape', 'Contact authors',
                    'Internal report cite', 'Compare with our process', 'Lab notebook ref'],
    }
    for username, plan in save_targets.items():
        u = user_objs[username]
        notes = save_notes_by_user[username]
        used = 0
        for cat_slug, n in plan:
            cat = Category.query.filter_by(slug=cat_slug).first()
            if cat is None:
                continue
            articles = _pick_articles(Article, where={'category_id': cat.id}, n=n,
                                      seed=f"{username}:save:{cat_slug}")
            for art in articles:
                sa = SavedArticle(
                    id=next_save_id,
                    user_id=u.id,
                    article_id=art.id,
                    note=notes[used % len(notes)],
                    created_at=MIRROR_REFERENCE_DATE - timedelta(days=2 + used * 3),
                )
                db.session.add(sa)
                next_save_id += 1
                used += 1

    # Comments per user (2-4 each) on a deterministic spread of articles.
    comments_plan = {
        'alice_j': [
            'Beautiful explanation of the dark-matter constraints — the figure 3 plot is doing a lot of work here.',
            'Worth comparing with the 2024 Planck re-analysis — different priors but converging conclusions.',
            'Saving this for the journal club tomorrow; the methodology section is a great teaching example.',
        ],
        'bob_c': [
            'This contradicts the line a senator pushed last week. Sourcing this for my Wednesday column.',
            'The institution statement and the paper itself disagree on the 2030 timeline. Anyone seen the PRR?',
            'Modeling assumptions feel optimistic, but the data underlying them is solid. Cautious thumbs up.',
        ],
        'carol_d': [
            'The CRISPR off-target rates here are an order of magnitude lower than what we see in our pipeline.',
            'I love that they released the raw sequencing data. Re-running their analysis tonight.',
            'Nice work, but I expected more discussion of polyploid edge cases.',
        ],
        'david_k': [
            'The fabrication tolerance is the real story here, not the zero-resistance claim.',
            'Anyone have access to the SI? The thickness vs. mobility curve is the only thing that matters.',
            'Calling it now: this technique will be in commercial sensors by 2028.',
        ],
    }
    next_comment_id = 1
    for username, comment_texts in comments_plan.items():
        u = user_objs[username]
        # Pick articles whose category matches the user's first interest tag,
        # so a "comments by alice on physics articles" task is well-defined.
        first_interest = u.interests.split(',')[0]
        cat = Category.query.filter_by(slug=first_interest).first()
        if cat is None:
            target_articles = Article.query.order_by(Article.id).limit(len(comment_texts)).all()
        else:
            target_articles = _pick_articles(Article, where={'category_id': cat.id},
                                             n=len(comment_texts),
                                             seed=f"{username}:comment")
        for i, art in enumerate(target_articles):
            c = Comment(
                id=next_comment_id,
                text=comment_texts[i],
                user_id=u.id,
                article_id=art.id,
                parent_id=None,
                score=0,
                created_at=MIRROR_REFERENCE_DATE - timedelta(days=1 + i * 4),
            )
            db.session.add(c)
            next_comment_id += 1

    # Seed a few cross-user reply chains so commenter-thread tasks work.
    reply_seeds = [
        ('bob_c', 'alice_j', 0, 'Totally agree on the priors point — the new constraint is much tighter though.'),
        ('alice_j', 'carol_d', 0, 'The polyploid section was a missed opportunity, you are right.'),
        ('david_k', 'bob_c', 1, 'I think the institution is hedging because of an unannounced pilot — keep watching.'),
    ]
    for replier_username, target_username, target_idx, text in reply_seeds:
        replier = user_objs[replier_username]
        target_user = user_objs[target_username]
        target_comments = Comment.query.filter_by(user_id=target_user.id) \
            .order_by(Comment.id).all()
        if target_idx >= len(target_comments):
            continue
        parent = target_comments[target_idx]
        c = Comment(
            id=next_comment_id,
            text=text,
            user_id=replier.id,
            article_id=parent.article_id,
            parent_id=parent.id,
            score=0,
            created_at=parent.created_at + timedelta(hours=6),
        )
        db.session.add(c)
        next_comment_id += 1

    # Search history per user (2-3 each)
    search_plan = {
        'alice_j': ['exoplanet atmosphere', 'dark matter halo', 'james webb'],
        'bob_c':   ['ocean carbon capture', 'methane emissions arctic'],
        'carol_d': ['CRISPR off-target', 'protein structure prediction', 'mitochondria'],
        'david_k': ['2D material superconductor', 'graphene transistor'],
    }
    next_sh_id = 1
    for username, queries in search_plan.items():
        u = user_objs[username]
        for j, q in enumerate(queries):
            sh = SearchHistory(
                id=next_sh_id,
                user_id=u.id,
                query_text=q,
                created_at=MIRROR_REFERENCE_DATE - timedelta(days=1 + j * 2,
                                                             hours=j * 5),
            )
            db.session.add(sh)
            next_sh_id += 1

    # -------------------------------------------------------------------
    # Extended seed data (added 2026-05-26).
    #
    # The original seed gives us 15 comments and 10 search-history rows,
    # which is too thin for richer benchmark coverage:
    #   * Pagination on user profile / per-article threads never triggers.
    #   * "How many comments by user X on category Y" tasks reduce to
    #     trivial 0/1/2 lookups.
    #   * Search-history widget tasks always show the same 2-3 entries.
    #
    # We therefore extend (rather than replace) the original tables so the
    # first 15 comment ids and 10 search ids stay byte-identical, keeping
    # any existing benchmark task that pinned IDs / counts still valid.
    #
    # All timestamps are derived from MIRROR_REFERENCE_DATE — never
    # datetime.now() — to preserve the byte-identical reset invariant.
    # -------------------------------------------------------------------

    extended_comments_by_user = {
        'alice_j': [
            ('astronomy', "The mass distribution in figure 2 is consistent with the EDR3 prior — nice independent cross-check."),
            ('astronomy', "JWST observation windows for this target are listed on STScI; would love to see follow-up at 4.5 microns."),
            ('astronomy', "Their treatment of dust extinction is more careful than the 2023 paper that triggered the controversy."),
            ('astronomy', "Eager to see this re-run with the next Gaia data release — angular precision should drop by a factor of two."),
            ('astronomy', "The accretion-disc inclination assumption probably swallows half the systematic error budget."),
            ('astronomy', "Lovely figure 6 — it finally makes the spin-orbit alignment story intuitive."),
            ('astronomy', "Footnote 14 quietly admits the calibration uncertainty doubles their headline error bar. Worth reading."),
            ('astronomy', "Has anyone reproduced this with the open-source pipeline on Zenodo? My runs disagreed by ~8%."),
            ('astronomy', "The radial velocity residuals are suspiciously low — I would push them to publish the raw RV timeseries."),
            ('astronomy', "If the proposed mechanism is correct, the next eclipse window should produce a measurable polarization signal."),
            ('astronomy', "Comparing this with the MNRAS letter from last spring, the two methods now bracket the same parameter space."),
            ('astronomy', "Saving this one for the orals reading list — a clean worked example of Bayesian model comparison."),
            ('physics', "The lattice spacing they use here is just below the threshold where finite-size effects start to dominate."),
            ('physics', "I wish the figure 3 inset showed the raw spectra, not just the fitted peaks."),
            ('physics', "Their bootstrap uncertainty is conservative — the systematic from the magnet calibration is probably larger."),
            ('physics', "Beautiful agreement between the perturbative prediction and the measured branching ratio."),
            ('physics', "The quoted coherence time is impressive — twice what was reported by the Princeton group last summer."),
            ('physics', "I would have liked one paragraph on why the alternative gauge-fixing was ruled out — currently it is a footnote."),
            ('physics', "Cross-posted this to the lab Slack — section 4.3 is exactly what we have been arguing about."),
            ('physics', "The supplementary material is the real paper; the main text is a roadmap."),
            ('physics', "An elegant proof, but the assumption that the noise is Gaussian breaks down in our setup."),
            ('physics', "Reads like the natural sequel to the 2024 PRL — nice continuity in the experimental program."),
        ],
        'bob_c': [
            ('earth', "Source check: the methane flux number here is 3x higher than the latest IPCC working-group draft. Asking around."),
            ('earth', "If this holds up under peer review, half the climate models will need recalibrating before AR7."),
            ('earth', "The ocean-acidification rate they report contradicts last week's NOAA statement. Story angle."),
            ('earth', "Good explainer for general audience — pulling the figure 1 graphic for my Tuesday newsletter."),
            ('earth', "Funding disclosure is buried at the bottom; the lead PI sits on the BP advisory board. Worth flagging."),
            ('earth', "The Antarctic ice-shelf timeline is the strongest part of this paper. The Arctic discussion feels rushed."),
            ('earth', "Cross-referenced with the European Drought Observatory; the regional numbers line up."),
            ('earth', "Need to call Wood Mackenzie on the cost-curve assumptions before I write this up."),
            ('earth', "Methodology is solid but the policy implications section is undisciplined — way overreaches the data."),
            ('earth', "The satellite-derived emission factor is a nice independent check on the bottom-up inventory."),
            ('earth', "Worth a longer feature: who funded the field campaign and why now?"),
            ('technology', "The energy-per-inference number is the only thing the venture crowd will read, and they will misuse it."),
            ('technology', "If the model card is honest about the training data, then the benchmark numbers are even more impressive."),
            ('technology', "Pitch idea: 'why your home solar installer is suddenly an AI shop' — this is the supply-chain story."),
            ('technology', "The robotics demo on YouTube undersells the actual paper — the planning algorithm is the contribution."),
            ('technology', "Calling the press office tomorrow to ask why they buried the negative ablation result on page 11."),
            ('technology', "The cost-per-watt projection assumes 2019-era subsidy regime — would not bet on it surviving the next term."),
            ('technology', "Asking my source at ARPA-E whether this fits the active solicitation."),
            ('technology', "Solid engineering paper, but framing it as 'AGI' in the press release is irresponsible."),
            ('technology', "Battery cycle-life data is the only metric utilities actually care about; nice that they led with it."),
            ('technology', "Following up on the open-source release — last time these authors promised code and shipped a notebook."),
            ('technology', "Quoting the lead author in this week's column. Their take on grid-scale storage is the most measured I have read."),
        ],
        'carol_d': [
            ('biology', "Off-target rates this low usually mean the guide library was hand-curated. Worth asking."),
            ('biology', "The ChIP-seq peaks in figure 4 do not look reproducible across the three biological replicates."),
            ('biology', "Why no Wilcoxon on the survival data? The t-test assumption is clearly violated."),
            ('biology', "Beautiful single-cell trajectory — exactly the kind of dataset I want for the next thesis chapter."),
            ('biology', "The polyploid edge case is genuinely hard; I would not penalise them too heavily for skipping it."),
            ('biology', "Their negative controls are weak. A scrambled guide is not the same as a true non-targeting condition."),
            ('biology', "Re-running their analysis on our dataset — preliminary numbers agree within 5%."),
            ('biology', "The protein-folding prediction matches the cryo-EM map within 1.8 Å, which is genuinely surprising."),
            ('biology', "Posting this on the lab Slack channel for journal club next Tuesday."),
            ('biology', "Authors deserve credit for releasing the raw counts table — almost no one does this for spatial data."),
            ('biology', "Glad to see the conservation comparison includes a non-vertebrate outgroup."),
            ('biology', "The transcription-factor knockout phenotype is the cleanest I have seen in a long time."),
            ('chemistry', "The yield optimization is impressive, but the catalyst loading is still industrially unviable."),
            ('chemistry', "Their crystal-structure data deposit is the only reason I trust the regiochemistry claim."),
            ('chemistry', "The kinetic isotope effect they report rules out the alternative mechanism in figure 7."),
            ('chemistry', "Need to compare this with the Sigma-Aldrich product spec before believing the purity claim."),
            ('chemistry', "Lovely application of the new dual-catalysis concept. Hard to disagree with the conclusion."),
            ('chemistry', "Footnote 9 admits a 12-hour reaction time — that is the metric most reviewers will jump on."),
            ('chemistry', "Worth re-reading after the next polymer-physics deadline; the analogy with our system is striking."),
            ('chemistry', "Their failed-attempts table at the end of the SI is the most useful figure in the paper."),
            ('chemistry', "I would love to see this scaled to a flow-chemistry setup — should be straightforward."),
            ('chemistry', "Solid paper, but the introduction is twice as long as it needs to be."),
        ],
        'david_k': [
            ('nanotechnology', "The mobility-vs-thickness curve in figure 3 is the real headline; the press release missed it."),
            ('nanotechnology', "Their ALD process is essentially the one we tried in 2024 — would love a side-by-side defect-density comparison."),
            ('nanotechnology', "Anyone able to access the SI without an institutional login? Asking for the patent team."),
            ('nanotechnology', "If the contact resistance numbers hold, this beats the IBM Zurich record from last quarter."),
            ('nanotechnology', "Worth flagging to the materials-procurement folks: this substrate is on the restricted-import list."),
            ('nanotechnology', "Cleanest TEM cross-sections I have seen for this material system in years."),
            ('nanotechnology', "Their wafer-scale uniformity number is the only metric a fab will care about."),
            ('nanotechnology', "Internal report draft cites this — please flag if anyone sees the retraction notice."),
            ('nanotechnology', "The lithography step they hand-wave in section 2.3 is actually the hardest part of the process."),
            ('nanotechnology', "If the bandgap engineering is reproducible, the photodetector market is up for grabs in 3 years."),
            ('nanotechnology', "The yield numbers in table 2 imply they got lucky on the last batch — would want to see 50 more devices."),
            ('nanotechnology', "Beautiful work, but framing it as a 'breakthrough' in the abstract undersells the careful incremental engineering."),
            ('physics', "The phonon-coupling analysis is the part of the paper that will actually generalise."),
            ('physics', "Their Hall measurement protocol is non-standard — would want to see the raw IV curves."),
            ('physics', "The reported coherence at room temperature is suspicious. What is the dephasing channel?"),
            ('physics', "Comparing with our internal benchmarks: their device area is 4x smaller, so the noise floor reads better."),
            ('physics', "Section 5 finally explains the temperature-dependent shift we have been chasing for a year."),
            ('physics', "Worth re-reading alongside the 2023 Nature Materials paper from Tsinghua — different scaling, same physics."),
            ('physics', "If the magnon-drag picture is right, the predicted angle-dependence should be easy to test."),
            ('physics', "Their figure 8 is essentially a textbook plot — would be great teaching material for the graduate course."),
            ('physics', "Lab-notebook reference: this is the source for the modified Drude fit we have been using."),
            ('physics', "The error bars on figure 5 are not properly propagated through the Bayesian step. Bothers me."),
        ],
    }
    # Track per-article inventory so a single follow-up reply can target a
    # known top-level by article. ``ext_top_level_by_user`` lists comment
    # objects keyed by username in insertion order, mirroring how the
    # reply seeds reference them.
    ext_top_level_by_user = {u: [] for u in extended_comments_by_user}
    # Time spacing: spread these comments back from MIRROR_REFERENCE_DATE
    # over ~120 days so the user profile timeline is non-degenerate.
    # ``offset_days`` formula: deterministic per (user_index, position).
    user_order = ['alice_j', 'bob_c', 'carol_d', 'david_k']
    for u_idx, username in enumerate(user_order):
        u = user_objs[username]
        plan = extended_comments_by_user[username]
        # Per-user deterministic article picks: for each (cat_slug, text)
        # entry we pick one article from that category, walking the
        # shuffled list to avoid hitting the same article twice within
        # this user's extended batch.
        used_article_ids_per_cat = {}
        for pos, (cat_slug, text) in enumerate(plan):
            cat = Category.query.filter_by(slug=cat_slug).first()
            if cat is None:
                continue
            if cat_slug not in used_article_ids_per_cat:
                pool = _pick_articles(
                    Article,
                    where={'category_id': cat.id},
                    n=max(13, len(plan)),
                    seed=f"ext:{username}:{cat_slug}",
                )
                used_article_ids_per_cat[cat_slug] = (pool, 0)
            pool, cursor = used_article_ids_per_cat[cat_slug]
            if cursor >= len(pool):
                # Wrap around if the category has fewer articles than
                # requested entries; reuse is acceptable here.
                cursor = 0
            target_article = pool[cursor]
            used_article_ids_per_cat[cat_slug] = (pool, cursor + 1)
            offset_days = 15 + u_idx * 2 + pos * 5
            offset_hours = (pos * 7 + u_idx * 3) % 24
            c = Comment(
                id=next_comment_id,
                text=text,
                user_id=u.id,
                article_id=target_article.id,
                parent_id=None,
                score=0,
                created_at=MIRROR_REFERENCE_DATE - timedelta(
                    days=offset_days, hours=offset_hours),
            )
            db.session.add(c)
            ext_top_level_by_user[username].append(c)
            next_comment_id += 1

    # 12 additional cross-user reply chains. ``target_idx`` indexes into
    # ext_top_level_by_user[target_username], so each reply is tied to a
    # known parent comment from the extended batch.
    ext_reply_seeds = [
        ('bob_c',   'alice_j', 0,  "Filed your dark-matter take for the Sunday roundup — thanks for the pointer."),
        ('alice_j', 'bob_c',   2,  "Worth following up on; the NOAA contradiction is the most interesting angle."),
        ('carol_d', 'alice_j', 5,  "Echoing this from a biology perspective — the dust-extinction caveat applies to our spectra too."),
        ('david_k', 'carol_d', 14, "Same observation on the materials side — the catalyst-loading story is repeated everywhere."),
        ('alice_j', 'david_k', 13, "Will steal the substrate caveat for our next group meeting, thanks."),
        ('carol_d', 'bob_c',   11, "Energy-per-inference comparisons cross over into our compute-bound bioinformatics workloads."),
        ('bob_c',   'david_k', 9,  "Photodetector market call is bold — keeping an eye on it for the technology beat."),
        ('david_k', 'alice_j', 19, "Section 4.3 is also the source of the half the lab arguments here. Welcome to the club."),
        ('alice_j', 'carol_d', 4,  "Same complaint about negative controls in astrophysics papers, just different sample."),
        ('carol_d', 'david_k', 20, "The Drude-fit reference is useful — citing in tomorrow's draft."),
        ('bob_c',   'carol_d', 7,  "The cryo-EM accuracy claim is the kind of headline number my editors love. May reach out."),
        ('david_k', 'bob_c',   18, "Battery cycle-life is exactly the wedge issue between research and procurement at our shop."),
    ]
    for replier_username, target_username, target_idx, text in ext_reply_seeds:
        replier = user_objs[replier_username]
        parents = ext_top_level_by_user.get(target_username, [])
        if target_idx >= len(parents):
            continue
        parent = parents[target_idx]
        c = Comment(
            id=next_comment_id,
            text=text,
            user_id=replier.id,
            article_id=parent.article_id,
            parent_id=parent.id,
            score=0,
            created_at=parent.created_at + timedelta(hours=9 + (target_idx % 5)),
        )
        db.session.add(c)
        next_comment_id += 1

    # Extended search-history: 48 more rows so the account-page widget,
    # search auto-suggest, and any "Nth recent query" benchmark have real
    # content to work with. Queries are real science topics covering a
    # broad span of phys.org categories so they are plausible per user.
    extended_search_plan = {
        'alice_j': [
            'pulsar timing array', 'gravitational wave detection',
            'supernova remnant cassiopeia', 'JWST mid-infrared spectroscopy',
            'binary neutron star merger', 'cosmic microwave background polarization',
            'lithium depletion young stars', 'magnetar burst rate',
            'exoplanet biosignature methane', 'astrochemistry interstellar medium',
            'TESS planet candidate vetting', 'dark energy survey y6',
        ],
        'bob_c': [
            'permafrost thaw siberia', 'atlantic meridional overturning',
            'great barrier reef bleaching', 'electric grid battery storage',
            'green hydrogen electrolysis cost', 'wildfire smoke air quality',
            'small modular reactor licensing', 'direct air capture pilot',
            'arctic shipping routes 2030', 'EV charging infrastructure rural',
            'IPCC AR7 working group', 'carbon offset verification market',
        ],
        'carol_d': [
            'base editing safety profile', 'organoid drug screening',
            'microbiome inflammatory bowel disease', 'mRNA vaccine influenza',
            'AlphaFold multimer prediction', 'cancer neoantigen identification',
            'cryo-electron tomography subtomogram', 'antibiotic resistance gene transfer',
            'CRISPR base editor prime', 'embryo gene therapy ethics',
            'gut-brain axis dopamine', 'enzyme directed evolution',
        ],
        'david_k': [
            'twisted bilayer graphene moire', 'quantum dot LED efficiency',
            'topological insulator surface states', 'high entropy alloy hardness',
            'metal-organic framework gas separation', 'silicon photonics integration',
            'wearable sensor flexible substrate', 'memristor neuromorphic computing',
            'thermoelectric generator nanowire', 'ferroelectric capacitor scaling',
            'spintronics magnetic tunnel junction', 'EUV photoresist roughness',
        ],
    }
    for u_idx, username in enumerate(user_order):
        u = user_objs[username]
        queries = extended_search_plan[username]
        for j, q in enumerate(queries):
            sh = SearchHistory(
                id=next_sh_id,
                user_id=u.id,
                query_text=q,
                # Spread back from day 15..130 to interleave with comment
                # timeline and avoid colliding with the original
                # search_plan timestamps (which sit in day 1..7).
                created_at=MIRROR_REFERENCE_DATE - timedelta(
                    days=15 + u_idx + j * 2,
                    hours=(j * 11 + u_idx * 5) % 24,
                ),
            )
            db.session.add(sh)
            next_sh_id += 1

    db.session.commit()
