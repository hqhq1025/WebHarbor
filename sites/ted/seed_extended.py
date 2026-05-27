"""Derived extended seed data for the deepened TED mirror.

All collections in this module are produced **deterministically** from the
350 TALKS / 28 PLAYLISTS / 81 EVENTS in seed_data.py so a rebuild on any
machine reproduces byte-identical bytes. No datetime.now(), no random, no
network calls — pure derivation.
"""
from __future__ import annotations

import hashlib
import re
from typing import Dict, List

from seed_data import EVENTS, PLAYLISTS, TALKS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or "untitled"


def _stable_int(seed: str, lo: int, hi: int) -> int:
    digest = hashlib.sha256(seed.encode()).hexdigest()
    span = hi - lo + 1
    return lo + (int(digest[:12], 16) % span)


def _pick(seed: str, options: List[str]) -> str:
    return options[_stable_int(seed, 0, len(options) - 1)]


# ---------------------------------------------------------------------------
# SPEAKERS — one row per unique speaker, derived from TALKS
# ---------------------------------------------------------------------------

_ROLE_BANK = [
    "Author", "Researcher", "Designer", "Entrepreneur", "Scientist",
    "Educator", "Journalist", "Filmmaker", "Architect", "Engineer",
    "Activist", "Physician", "Artist", "Musician", "Economist",
    "Policy advisor", "Software engineer", "Climate scientist",
    "Public-health researcher", "Behavioral scientist", "Astrophysicist",
    "Curator", "Choreographer", "Linguist", "Mathematician",
    "Cognitive scientist", "Roboticist", "Sociologist", "Photographer",
    "Conservationist",
]

_AFFILIATION_BANK = [
    "MIT Media Lab", "Stanford University", "Harvard Medical School",
    "Royal College of Art", "ETH Zurich", "University of Cape Town",
    "National University of Singapore", "Sciences Po", "UC Berkeley",
    "University of Tokyo", "London School of Economics", "ETH Lausanne",
    "Columbia Journalism School", "RAND Corporation", "Wellcome Trust",
    "Allen Institute", "Santa Fe Institute", "Howard University",
    "World Resources Institute", "ICRC", "Mozilla Foundation",
    "Long Now Foundation", "Open Philanthropy", "NASA Goddard",
    "MoMA", "Carnegie Mellon", "Tata Institute", "Doctors Without Borders",
    "Greenpeace International", "Berklee College of Music",
]


def _build_speakers() -> List[Dict]:
    by_name: Dict[str, List[Dict]] = {}
    for t in TALKS:
        # Each talk may have a comma-separated speaker list — collapse to lead
        lead = t["speaker"].split(",")[0].strip()
        if lead:
            by_name.setdefault(lead, []).append(t)
    rows: List[Dict] = []
    for name, ts in sorted(by_name.items(), key=lambda kv: kv[0].lower()):
        slug = _slugify(name)
        lead_talk = max(ts, key=lambda x: x["views"])
        topics: List[str] = []
        for tk in ts:
            for tp in tk["topics"]:
                if tp not in topics:
                    topics.append(tp)
        role = _pick("role:" + name, _ROLE_BANK)
        org = _pick("org:" + name, _AFFILIATION_BANK)
        bio = (
            f"{name} is a {role.lower()} working at {org}. Their TED stage talks "
            f"explore {', '.join(topics[:3]) if topics else 'big ideas'}. Best known "
            f"for \"{lead_talk['title']}\" at {lead_talk['event']}."
        )
        why = (
            f"In a single talk, {name} reframes how audiences think about "
            f"{topics[0] if topics else 'the world around them'}. Their work bridges "
            f"research, lived practice, and craft."
        )
        rows.append({
            "slug": slug,
            "name": name,
            "role": role,
            "affiliation": org,
            "bio": bio,
            "why_listen": why,
            "photo": lead_talk["image"],
            "talks_count": len(ts),
            "total_views": sum(x["views"] for x in ts),
            "languages": _pick("lang:" + name, [
                "English", "English, Spanish", "English, French",
                "English, Mandarin", "English, Arabic", "English, Hindi",
                "English, Portuguese", "English, Swahili",
            ]),
        })
    return rows


SPEAKERS = _build_speakers()


# ---------------------------------------------------------------------------
# TOPIC PAGES — one row per unique topic referenced by TALKS
# ---------------------------------------------------------------------------

_TOPIC_HEADLINES = {
    "ai": ("AI", "Talks that explore how machines learn — and what humans owe each other in the process."),
    "technology": ("Technology", "From semiconductors to swarm robotics, ideas about the tools shaping daily life."),
    "science": ("Science", "Curiosity-driven research from the lab bench to deep space."),
    "design": ("Design", "How form, function, and intent collide to shape what we touch, see, and use."),
    "climate change": ("Climate change", "Carbon, oceans, policy, and the next decade — talks for the climate moment."),
    "health": ("Health", "Bodies, minds, and the systems that care for them."),
    "education": ("Education", "What schools are for, what they could be, and who decides."),
    "business": ("Business", "Founders, economists, and operators on building enterprises that last."),
    "culture": ("Culture", "Stories, rituals, and the questions every generation answers anew."),
    "music": ("Music", "Performance, theory, and what sound does to us."),
    "art": ("Art", "Artists on craft, criticism, and creative life."),
    "psychology": ("Psychology", "How we think, feel, and choose — and what that means for everything else."),
}


def _build_topic_pages() -> List[Dict]:
    by_topic: Dict[str, List[Dict]] = {}
    for t in TALKS:
        for tp in t["topics"]:
            by_topic.setdefault(tp.lower(), []).append(t)
    rows: List[Dict] = []
    for topic in sorted(by_topic):
        ts = sorted(by_topic[topic], key=lambda x: -x["views"])
        slug = _slugify(topic)
        headline = _TOPIC_HEADLINES.get(topic, (topic.title(), f"Talks tagged \"{topic}\" — selected ideas, voices, and experiments."))
        rows.append({
            "slug": slug,
            "name": headline[0],
            "description": headline[1],
            "talk_count": len(ts),
            "banner": ts[0]["image"],
            "popular_talk_slug": ts[0]["slug"],
        })
    return rows


TOPIC_PAGES = _build_topic_pages()


# ---------------------------------------------------------------------------
# SERIES — TED Series, curated talk runs grouped by recurring theme
# ---------------------------------------------------------------------------

SERIES_BLUEPRINTS = [
    {"slug": "small-thing-big-idea", "name": "Small Thing, Big Idea",
     "tagline": "Designs that changed the world",
     "description": "A daily-life object, a five-minute talk, an unexpected story.",
     "host": "Debbie Millman",
     "topic_filter": ["design", "art", "culture"]},
    {"slug": "way-beyond", "name": "Way Beyond",
     "tagline": "Big ideas from the edge of human capacity",
     "description": "Stories of people pushing the boundary of what bodies and minds can do.",
     "host": "Alexi Pappas",
     "topic_filter": ["personal growth", "sports", "psychology"]},
    {"slug": "ted-explains", "name": "TED Explains",
     "tagline": "Concise, expert-led explainers",
     "description": "Short, lively explainers that demystify the news cycle.",
     "host": "Ian Bremmer",
     "topic_filter": ["politics", "current events", "global issues"]},
    {"slug": "the-way-we-work", "name": "The Way We Work",
     "tagline": "Career advice for everyone",
     "description": "Practical, research-backed strategies for thriving at work.",
     "host": "Adam Grant",
     "topic_filter": ["work", "business", "leadership"]},
    {"slug": "ted-fellows-shape-the-future", "name": "TED Fellows: Shape the Future",
     "tagline": "Frontline innovators tell their stories",
     "description": "Scientists, artists, and activists from the TED Fellows program.",
     "host": "Lily Whitsitt",
     "topic_filter": ["science", "innovation", "social change"]},
    {"slug": "ted-countdown", "name": "TED Countdown",
     "tagline": "A global initiative to accelerate climate solutions",
     "description": "Climate-focused talks, deep dives, and follow-the-money reporting.",
     "host": "Lindsay Levin",
     "topic_filter": ["climate change", "environment", "sustainability"]},
    {"slug": "talks-with-google", "name": "Talks with Google",
     "tagline": "Conversations on technology and humanity",
     "description": "Industry leaders on the platforms shaping the next decade.",
     "host": "Lara Stein",
     "topic_filter": ["ai", "technology", "internet"]},
    {"slug": "ted-radio-hour", "name": "TED Radio Hour Originals",
     "tagline": "Stories that take you somewhere",
     "description": "Long-form interviews with the most memorable TED voices.",
     "host": "Manoush Zomorodi",
     "topic_filter": ["culture", "society", "personal growth"]},
]


def _build_series() -> List[Dict]:
    rows: List[Dict] = []
    for series in SERIES_BLUEPRINTS:
        filters = set(series["topic_filter"])
        matching = [
            t for t in TALKS
            if any(tp in filters for tp in (x.lower() for x in t["topics"]))
        ]
        matching.sort(key=lambda t: (-t["views"], t["slug"]))
        episodes = matching[:14] or sorted(TALKS, key=lambda t: -t["views"])[:6]
        rows.append({
            **series,
            "banner": episodes[0]["image"],
            "episode_count": len(episodes),
            "episode_slugs": [e["slug"] for e in episodes],
        })
    return rows


SERIES = _build_series()


# ---------------------------------------------------------------------------
# PODCASTS — TED Audio Collective shows
# ---------------------------------------------------------------------------

PODCAST_BLUEPRINTS = [
    {"slug": "ted-radio-hour", "name": "TED Radio Hour",
     "host": "Manoush Zomorodi", "publisher": "TED + NPR",
     "tagline": "Discover something new about the world by listening to a single big idea.",
     "frequency": "Weekly", "rss": "https://www.npr.org/rss/podcast.php?id=510298",
     "topic_filter": ["culture", "society"]},
    {"slug": "how-to-be-a-better-human", "name": "How to Be a Better Human",
     "host": "Chris Duffy", "publisher": "TED + PRX",
     "tagline": "Practical wisdom for everyday life from the TED stage and beyond.",
     "frequency": "Weekly", "rss": "https://www.ted.com/podcasts/how_to_be_a_better_human",
     "topic_filter": ["personal growth", "psychology"]},
    {"slug": "fixable", "name": "Fixable",
     "host": "Anne Morriss, Frances Frei", "publisher": "TED Audio Collective",
     "tagline": "Workplace problems — and how to fix them.",
     "frequency": "Weekly", "rss": "https://www.ted.com/podcasts/fixable",
     "topic_filter": ["work", "business", "leadership"]},
    {"slug": "the-ted-ai-show", "name": "The TED AI Show",
     "host": "Bilawal Sidhu", "publisher": "TED Audio Collective",
     "tagline": "AI in plain English with the people building it.",
     "frequency": "Weekly", "rss": "https://www.ted.com/podcasts/the_ted_ai_show",
     "topic_filter": ["ai", "technology"]},
    {"slug": "design-matters", "name": "Design Matters with Debbie Millman",
     "host": "Debbie Millman", "publisher": "TED Audio Collective",
     "tagline": "The world's first podcast about design.",
     "frequency": "Weekly", "rss": "https://www.designmattersmedia.com/feed",
     "topic_filter": ["design", "art", "creativity"]},
    {"slug": "far-flung", "name": "Far Flung",
     "host": "Saleem Reshamwala", "publisher": "TED Audio Collective",
     "tagline": "Big ideas from the unexpected corners of the world.",
     "frequency": "Bi-weekly", "rss": "https://www.ted.com/podcasts/far_flung",
     "topic_filter": ["global issues", "culture"]},
    {"slug": "ted-business", "name": "TED Business",
     "host": "Modupe Akinola", "publisher": "TED Audio Collective",
     "tagline": "Big ideas for builders, founders, and leaders.",
     "frequency": "Weekly", "rss": "https://www.ted.com/podcasts/ted_business",
     "topic_filter": ["business", "work", "leadership"]},
    {"slug": "ted-climate", "name": "TED Climate",
     "host": "Dan Kwartler", "publisher": "TED Audio Collective",
     "tagline": "Climate solutions from the people working on them.",
     "frequency": "Seasonal", "rss": "https://www.ted.com/podcasts/ted_climate",
     "topic_filter": ["climate change", "environment", "sustainability"]},
]


def _build_podcasts() -> List[Dict]:
    rows: List[Dict] = []
    for show in PODCAST_BLUEPRINTS:
        filters = set(show["topic_filter"])
        matching = [
            t for t in TALKS
            if any(tp in filters for tp in (x.lower() for x in t["topics"]))
        ]
        matching.sort(key=lambda t: (-t["views"], t["slug"]))
        episodes = matching[:18] or sorted(TALKS, key=lambda t: -t["views"])[:8]
        rows.append({
            **show,
            "banner": episodes[0]["image"],
            "episode_count": len(episodes),
            "episodes": [
                {
                    "slug": ep["slug"],
                    "title": ep["title"],
                    "speaker": ep["speaker"],
                    "duration_seconds": ep["duration_seconds"],
                    "published_at": ep["published_at"],
                    "image": ep["image"],
                    "description": f"On this episode of {show['name']}: {ep['speaker']} on \"{ep['title']}\".",
                }
                for ep in episodes
            ],
        })
    return rows


PODCASTS = _build_podcasts()


# ---------------------------------------------------------------------------
# TED-Ed — lessons drawn from talks where topic suggests classroom fit
# ---------------------------------------------------------------------------

_TED_ED_SUBJECTS = [
    "Mathematics", "Literature & Language", "Social Studies",
    "Health", "Science & Technology", "Philosophy & Religion",
    "The Arts", "Business & Economics", "Psychology", "Thinking & Learning",
]


def _build_ted_ed() -> List[Dict]:
    candidate = [t for t in TALKS if any(
        kw in t["title"].lower() or kw in " ".join(t["topics"]).lower()
        for kw in ["learn", "how", "why", "science", "explain", "history", "math", "language", "philosophy"]
    )]
    candidate.sort(key=lambda t: (-t["views"], t["slug"]))
    selected = candidate[:60] or TALKS[:60]
    rows: List[Dict] = []
    for t in selected:
        subject = _pick("eded-subj:" + t["slug"], _TED_ED_SUBJECTS)
        grade_band = _pick("eded-grade:" + t["slug"],
                            ["Grades 6–8", "Grades 9–12", "Grades 11–12", "Higher education"])
        rows.append({
            "slug": t["slug"],
            "title": t["title"],
            "educator": t["speaker"],
            "subject": subject,
            "grade_band": grade_band,
            "duration_seconds": min(t["duration_seconds"], 360 + (t["duration_seconds"] % 240)),
            "image": t["image"],
            "summary": f"A TED-Ed lesson based on \"{t['title']}\" by {t['speaker']}, designed for {grade_band.lower()}.",
            "dig_deeper": [
                "Watch the original TED talk on the same topic.",
                "Discuss with your class: what changed your mind?",
                f"Write a one-paragraph response to {t['speaker']}'s core claim.",
            ],
            "talk_slug": t["slug"],
        })
    return rows


TED_ED = _build_ted_ed()


# ---------------------------------------------------------------------------
# CONFERENCES — flagship + TED conferences, with apply/attend pages
# ---------------------------------------------------------------------------

CONFERENCE_BLUEPRINTS = [
    {"slug": "ted2026", "name": "TED2026", "city": "Vancouver, BC",
     "country": "Canada", "starts_on": "2026-04-13", "ends_on": "2026-04-17",
     "theme": "What now?", "track": "Flagship", "capacity": 1800,
     "status": "Open for application", "summary":
        "Five days of unmissable talks, performances, and gatherings as TED's "
        "flagship event returns to Vancouver. Sessions span AI, climate, design, "
        "and the moral questions that shape a new century."},
    {"slug": "tednext-2026", "name": "TEDNext 2026", "city": "Atlanta, GA",
     "country": "United States", "starts_on": "2026-11-09", "ends_on": "2026-11-12",
     "theme": "Show me", "track": "Next", "capacity": 1200,
     "status": "Application opens 2026-06-01", "summary":
        "TEDNext gathers builders, operators, and storytellers focused on the next "
        "decade of social and technological change."},
    {"slug": "tedwomen-2026", "name": "TEDWomen 2026", "city": "Atlanta, GA",
     "country": "United States", "starts_on": "2026-11-12", "ends_on": "2026-11-14",
     "theme": "Power tools", "track": "Women", "capacity": 1000,
     "status": "Application open", "summary":
        "TEDWomen returns with a program centered on builders, organizers, and "
        "leaders shaping what comes next."},
    {"slug": "ted-countdown-summit-2026", "name": "TED Countdown Summit 2026",
     "city": "Detroit, MI", "country": "United States",
     "starts_on": "2026-07-13", "ends_on": "2026-07-16",
     "theme": "The just transition", "track": "Countdown", "capacity": 1200,
     "status": "Application open", "summary":
        "A working summit that brings climate scientists, financiers, "
        "policy-makers, and artists into the same room for four days."},
    {"slug": "tedmonterey-2026", "name": "TEDMonterey 2026", "city": "Monterey, CA",
     "country": "United States", "starts_on": "2026-08-02", "ends_on": "2026-08-05",
     "theme": "The new wild", "track": "Monterey", "capacity": 1400,
     "status": "Application open", "summary":
        "A West Coast gathering at the edge of the Pacific."},
    {"slug": "tedglobal-2026", "name": "TEDGlobal 2026", "city": "Nairobi",
     "country": "Kenya", "starts_on": "2026-10-19", "ends_on": "2026-10-22",
     "theme": "Possible Africa", "track": "Global", "capacity": 1200,
     "status": "Application closes 2026-08-15", "summary":
        "Africa-led ideas and African storytellers, on a continental stage."},
    {"slug": "tedsummit-2026", "name": "TEDSummit 2026", "city": "Mexico City",
     "country": "Mexico", "starts_on": "2026-09-07", "ends_on": "2026-09-10",
     "theme": "Renewal", "track": "Summit", "capacity": 1000,
     "status": "By invitation", "summary":
        "A working summit for the TED community: TEDx organizers, fellows, "
        "translators, and longtime members."},
    {"slug": "ted-fellows-retreat-2026", "name": "TED Fellows Retreat 2026",
     "city": "Athens", "country": "Greece",
     "starts_on": "2026-06-08", "ends_on": "2026-06-12",
     "theme": "Reinvention", "track": "Fellows", "capacity": 200,
     "status": "By invitation", "summary":
        "An intimate gathering of the global TED Fellows network."},
    {"slug": "ted-democracy-2026", "name": "TED Democracy 2026", "city": "Washington, DC",
     "country": "United States", "starts_on": "2026-10-05", "ends_on": "2026-10-07",
     "theme": "What citizens can do", "track": "Special", "capacity": 700,
     "status": "Application open", "summary":
        "A three-day gathering exploring the architecture of self-government."},
    {"slug": "ted-ai-2026", "name": "TED AI 2026", "city": "San Francisco, CA",
     "country": "United States", "starts_on": "2026-10-13", "ends_on": "2026-10-15",
     "theme": "Models, makers, and moments", "track": "AI", "capacity": 900,
     "status": "Application open", "summary":
        "TED AI returns to the West Coast with researchers, ethicists, founders, "
        "and storytellers working at the AI frontier."},
    {"slug": "ted-health-2026", "name": "TED Health 2026", "city": "Boston, MA",
     "country": "United States", "starts_on": "2026-09-21", "ends_on": "2026-09-23",
     "theme": "Care", "track": "Health", "capacity": 700,
     "status": "Application open", "summary":
        "Clinicians, public-health leaders, and care workers gather to explore "
        "where medicine is going."},
    {"slug": "tedyouth-2026", "name": "TEDYouth 2026", "city": "Brooklyn, NY",
     "country": "United States", "starts_on": "2026-11-21", "ends_on": "2026-11-22",
     "theme": "What if?", "track": "Youth", "capacity": 600,
     "status": "Open registration", "summary":
        "A weekend of talks, hands-on workshops, and performances designed for "
        "students ages 13–19."},
]

_APPLICATION_ROLES = [
    "Attendee", "Speaker nominator", "Patron host", "Volunteer",
    "Press / journalist", "Educator delegate",
]


def _build_conferences() -> List[Dict]:
    rows: List[Dict] = []
    for c in CONFERENCE_BLUEPRINTS:
        # Build a session lineup of 6 talks per conference, deterministic.
        seed = "conf-lineup:" + c["slug"]
        talks_pool = sorted(TALKS, key=lambda x: x["slug"])
        picks = []
        for k in range(6):
            idx = _stable_int(seed + f":{k}", 0, len(talks_pool) - 1)
            cand = talks_pool[(idx + k) % len(talks_pool)]
            if cand not in picks:
                picks.append(cand)
        rows.append({
            **c,
            "banner": picks[0]["image"],
            "session_slugs": [t["slug"] for t in picks],
            "application_roles": _APPLICATION_ROLES,
        })
    return rows


CONFERENCES = _build_conferences()


# ---------------------------------------------------------------------------
# TEDx — local TEDx events
# ---------------------------------------------------------------------------

TEDX_EVENT_BLUEPRINTS = [
    ("tedxberkeley-2026", "TEDxBerkeley 2026", "Berkeley, CA", "USA", "2026-02-21", "Reframe"),
    ("tedxbeaconstreet-2026", "TEDxBeaconStreet 2026", "Brookline, MA", "USA", "2026-11-14", "Constellation"),
    ("tedxlondon-2026", "TEDxLondon 2026", "London", "UK", "2026-09-12", "Build the bridge"),
    ("tedxsydney-2026", "TEDxSydney 2026", "Sydney", "Australia", "2026-05-23", "Lift"),
    ("tedxsf-2026", "TEDxSan Francisco 2026", "San Francisco, CA", "USA", "2026-10-17", "Possible city"),
    ("tedxtokyo-2026", "TEDxTokyo 2026", "Tokyo", "Japan", "2026-03-21", "Light, return"),
    ("tedxberlin-2026", "TEDxBerlin 2026", "Berlin", "Germany", "2026-04-25", "Out of step"),
    ("tedxnairobi-2026", "TEDxNairobi 2026", "Nairobi", "Kenya", "2026-07-25", "Pan-African now"),
    ("tedxmexicocity-2026", "TEDxMexicoCity 2026", "Mexico City", "Mexico", "2026-11-07", "Cruce"),
    ("tedxsaopaulo-2026", "TEDxSaoPaulo 2026", "São Paulo", "Brazil", "2026-08-22", "Encruzilhada"),
    ("tedxmumbai-2026", "TEDxMumbai 2026", "Mumbai", "India", "2026-12-05", "Tomorrow's monsoon"),
    ("tedxlagos-2026", "TEDxLagos 2026", "Lagos", "Nigeria", "2026-09-26", "Compass"),
    ("tedxbarcelona-2026", "TEDxBarcelona 2026", "Barcelona", "Spain", "2026-06-13", "Sobremesa"),
    ("tedxamsterdam-2026", "TEDxAmsterdam 2026", "Amsterdam", "Netherlands", "2026-10-10", "Polderwerk"),
    ("tedxstockholm-2026", "TEDxStockholm 2026", "Stockholm", "Sweden", "2026-04-18", "Slow signal"),
    ("tedxauckland-2026", "TEDxAuckland 2026", "Auckland", "New Zealand", "2026-05-09", "Waka"),
    ("tedxportland-2026", "TEDxPortland 2026", "Portland, OR", "USA", "2026-04-04", "Maker city"),
    ("tedxgalway-2026", "TEDxGalway 2026", "Galway", "Ireland", "2026-09-19", "Cuan"),
    ("tedxwinnipeg-2026", "TEDxWinnipeg 2026", "Winnipeg, MB", "Canada", "2026-11-21", "Threshold"),
    ("tedxboulder-2026", "TEDxBoulder 2026", "Boulder, CO", "USA", "2026-08-08", "Altitude"),
    ("tedxnashvillewomen-2026", "TEDxNashvilleWomen 2026", "Nashville, TN", "USA", "2026-03-08", "Sustain note"),
    ("tedxcambridge-2026", "TEDxCambridge 2026", "Cambridge, MA", "USA", "2026-10-24", "Echo chamber"),
    ("tedxlisboa-2026", "TEDxLisboa 2026", "Lisbon", "Portugal", "2026-06-27", "Maré viva"),
    ("tedxhongkong-2026", "TEDxHongKong 2026", "Hong Kong", "Hong Kong", "2026-09-05", "Crosscurrents"),
    ("tedxgeneva-2026", "TEDxGeneva 2026", "Geneva", "Switzerland", "2026-05-30", "Confluence"),
    ("tedxmelbourne-2026", "TEDxMelbourne 2026", "Melbourne", "Australia", "2026-08-15", "Inner south"),
    ("tedxtelaviv-2026", "TEDxTelAviv 2026", "Tel Aviv", "Israel", "2026-04-11", "After the hour"),
    ("tedxbuenosaires-2026", "TEDxBuenosAires 2026", "Buenos Aires", "Argentina", "2026-07-04", "Vereda"),
    ("tedxistanbul-2026", "TEDxIstanbul 2026", "Istanbul", "Türkiye", "2026-10-31", "Boğaz"),
    ("tedxbogota-2026", "TEDxBogotá 2026", "Bogotá", "Colombia", "2026-09-12", "Sereno"),
]


def _build_tedx() -> List[Dict]:
    rows: List[Dict] = []
    talks_pool = sorted(TALKS, key=lambda x: x["slug"])
    for slug, name, city, country, date, theme in TEDX_EVENT_BLUEPRINTS:
        seed = "tedx-talk:" + slug
        idx = _stable_int(seed, 0, len(talks_pool) - 1)
        feature = talks_pool[idx]
        organizer_seed = "tedx-org:" + slug
        organizer = _pick(organizer_seed, [
            "Aisha Karim", "Pablo Rivera", "Mei Tanaka", "Daniel Okafor",
            "Sara Lindholm", "Marco Rossi", "Priya Iyer", "Liam O'Connor",
            "Niamh Walsh", "Rohan Mehta", "Lucia Costa", "Hana Jung",
            "Felix Brandt", "Renee Dupont", "Tomás Vega", "Astrid Sørensen",
        ])
        rows.append({
            "slug": slug,
            "name": name,
            "city": city,
            "country": country,
            "date": date,
            "theme": theme,
            "organizer": organizer,
            "capacity": _stable_int("tedx-cap:" + slug, 220, 1200),
            "banner": feature["image"],
            "feature_talk_slug": feature["slug"],
            "status": _pick("tedx-status:" + slug, [
                "Open for application", "Waitlist", "Sold out", "Open registration",
            ]),
        })
    return rows


TEDX_EVENTS = _build_tedx()


# ---------------------------------------------------------------------------
# MEMBERSHIP — tier blueprints
# ---------------------------------------------------------------------------

MEMBERSHIP_TIERS = [
    {"slug": "explorer", "name": "Explorer", "monthly_price": 0, "annual_price": 0,
     "tagline": "Start exploring TED — for free.",
     "perks": [
         "Watch every TED talk and TED-Ed lesson",
         "Save talks to your library",
         "Subscribe to up to 3 newsletters",
     ],
     "color": "#222"},
    {"slug": "supporter", "name": "Supporter", "monthly_price": 9, "annual_price": 99,
     "tagline": "Fund the talks. Get behind-the-curtain access.",
     "perks": [
         "Everything in Explorer",
         "Ad-free podcast feeds across the TED Audio Collective",
         "Quarterly conference dispatches from TED curators",
         "Members-only Q&A livestreams",
     ],
     "color": "#a0273e"},
    {"slug": "patron", "name": "Patron", "monthly_price": 19, "annual_price": 199,
     "tagline": "Go deeper. Join the room.",
     "perks": [
         "Everything in Supporter",
         "Early access to TED conference applications",
         "TED-curated members-only playlists",
         "Annual TED Patron print zine",
         "Two TED-branded gifts per year",
     ],
     "color": "#eb0028"},
    {"slug": "founder-circle", "name": "Founder Circle", "monthly_price": 49,
     "annual_price": 499, "tagline": "Help shape the next decade of TED.",
     "perks": [
         "Everything in Patron",
         "Two invitations to TED community gatherings each year",
         "Quarterly virtual sessions with TED programming team",
         "Listed on the TED Founder Circle wall (optional)",
     ],
     "color": "#111"},
]


# ---------------------------------------------------------------------------
# NEWSLETTERS — the seven TED newsletters
# ---------------------------------------------------------------------------

NEWSLETTERS = [
    {"slug": "ideas", "name": "TED Ideas", "frequency": "Weekly",
     "description": "The week's most-talked-about TED ideas, in one digest."},
    {"slug": "science", "name": "TED Science", "frequency": "Weekly",
     "description": "Lab benches, deep space, and what curiosity uncovers."},
    {"slug": "ai", "name": "TED AI", "frequency": "Weekly",
     "description": "AI without the hype — models, makers, ethics."},
    {"slug": "climate", "name": "TED Countdown", "frequency": "Bi-weekly",
     "description": "Climate solutions and the people working on them."},
    {"slug": "education", "name": "TED Educators", "frequency": "Monthly",
     "description": "Curated lessons, conversations, and tools for teachers."},
    {"slug": "design", "name": "TED Design", "frequency": "Monthly",
     "description": "Designers, makers, and the objects of daily life."},
    {"slug": "ted-talks-daily", "name": "TED Talks Daily", "frequency": "Daily",
     "description": "One can't-miss TED talk in your inbox each morning."},
]


# ---------------------------------------------------------------------------
# BLOG — TED Ideas blog posts derived from talks
# ---------------------------------------------------------------------------

_BLOG_BUCKETS = [
    ("ideas", "ideas"),
    ("essays", "long-form"),
    ("dispatches", "field notes"),
    ("conversations", "Q&A"),
    ("how-to", "explainers"),
]


def _build_blog_posts() -> List[Dict]:
    rows: List[Dict] = []
    by_views = sorted(TALKS, key=lambda t: (-t["views"], t["slug"]))
    selected = by_views[:80]
    for i, t in enumerate(selected):
        bucket_slug, bucket_label = _BLOG_BUCKETS[i % len(_BLOG_BUCKETS)]
        post_slug = f"{bucket_slug}-{t['slug']}"
        author = t["speaker"].split(",")[0].strip()
        topic = (t["topics"][0] if t["topics"] else "ideas")
        published = t["published_at"]
        title_root = t["title"].rstrip(". ")
        rows.append({
            "slug": post_slug,
            "title": f"Field notes: {title_root}",
            "author": author,
            "bucket": bucket_label,
            "bucket_slug": bucket_slug,
            "topic": topic,
            "published_at": published,
            "hero": t["image"],
            "summary": (
                f"Three short takeaways from {author}'s talk \"{title_root}\" — and "
                f"what teachers, builders, and skeptics are saying about it now."
            ),
            "body": (
                f"When {author} took the TED stage at {t['event']} to deliver "
                f"\"{title_root}\", the framing question was simple: what does "
                f"{topic} look like ten years from now? In the days since, the "
                f"talk has racked up {t['views']:,} views and unlocked a series "
                f"of follow-on conversations.\n\nThree takeaways stand out for "
                f"readers of TED Ideas. First, {author} insists that the right "
                f"unit of analysis is decades, not quarters. Second, the talk "
                f"argues against tidy narratives — and asks the audience to sit "
                f"with what isn't yet resolved. Third, the closing minutes hand "
                f"a deliberately small action to every viewer.\n\nWatch the "
                f"talk, save the transcript, and share one of {author}'s lines "
                f"with someone who would push back. That's the move."
            ),
            "talk_slug": t["slug"],
            "tags": (t["topics"][:3] or ["ideas"]),
        })
    return rows


BLOG_POSTS = _build_blog_posts()


# ---------------------------------------------------------------------------
# DEFAULT COMMENTS / RATINGS — seed engagement so /discussion pages are full
# ---------------------------------------------------------------------------

_COMMENT_LINES = [
    "Sat with this for a while afterwards — the framing question is what got me.",
    "Really wanted them to spend longer on the second case study.",
    "The transcript is worth a second read; one paragraph in particular hit hard.",
    "Has anyone tried implementing the small action they suggest? Curious about results.",
    "Disagree with the final claim, but the setup is the cleanest I've heard.",
    "Saved this to share with our team retreat in October.",
    "The Q&A at the end on YouTube is also worth watching, FYI.",
    "Refreshing not to hear the usual five buzzwords for once.",
    "Maybe my favorite TED talk of the year so far.",
    "Worth pairing this with the {related} talk on the same topic.",
    "The data point at minute six is the one I keep going back to.",
    "Anyone know the source on the statistic about adoption rates?",
    "Could have used a slide here but the storytelling did the work.",
    "Made me change my mind on something I thought was settled. Rare.",
    "Followed the speaker for years and this is the most pointed talk yet.",
]


def build_seed_comments_for_talk(talk_slug: str, related_slug: str = "") -> List[Dict]:
    rows: List[Dict] = []
    for i in range(8):
        seed = f"cmt:{talk_slug}:{i}"
        line = _COMMENT_LINES[i % len(_COMMENT_LINES)]
        body = line.replace("{related}", related_slug or "another")
        rows.append({
            "body": body,
            "score": _stable_int(seed + ":score", -2, 27),
        })
    return rows


# ---------------------------------------------------------------------------
# Compact summaries for sanity checks
# ---------------------------------------------------------------------------

EXTENDED_SUMMARY = {
    "speakers": len(SPEAKERS),
    "topic_pages": len(TOPIC_PAGES),
    "series": len(SERIES),
    "podcasts": len(PODCASTS),
    "ted_ed": len(TED_ED),
    "conferences": len(CONFERENCES),
    "tedx_events": len(TEDX_EVENTS),
    "membership_tiers": len(MEMBERSHIP_TIERS),
    "newsletters": len(NEWSLETTERS),
    "blog_posts": len(BLOG_POSTS),
}
