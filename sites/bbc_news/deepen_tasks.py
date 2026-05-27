"""Append 1600 deepening tasks to tasks.jsonl for rounds R3-R10.

Each round produces 200 tasks that reference its new rN_ routes. Tasks are
deterministic (md5-derived) and read-only, no DB writes.

Re-running this script is idempotent: it scans tasks.jsonl for an existing
sentinel marker and exits early if already applied.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent
DB = BASE / "instance_seed" / "bbc_news.db"
TASKS = BASE / "tasks.jsonl"

WEB = "http://localhost:40004/"
WEB_NAME = "BBC News"
UPSTREAM = "https://www.bbc.com/news/"
SENTINEL_PREFIX = "[r3-r10-deepen-v1]"


def _digest(*parts) -> str:
    return hashlib.md5("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()


def pick_articles(cur, section: str, limit: int = 220) -> list[str]:
    return [r[0] for r in cur.execute(
        "SELECT slug FROM articles WHERE section_slug=? ORDER BY slug LIMIT ?",
        (section, limit),
    ).fetchall()]


def pick_articles_multi(cur, sections: list[str], total: int) -> list[str]:
    out: list[str] = []
    per = max(20, total // max(1, len(sections)))
    for s in sections:
        out.extend(pick_articles(cur, s, per))
    # Stable, deterministic order
    return sorted(set(out))[:total]


def _next_id(start: int) -> int:
    return start


def emit_round(con, round_name: str, templates: list[tuple[str, str]],
               slug_pool: list[str], count: int, base_id: int) -> list[dict]:
    """Generate `count` tasks for one round.

    `templates` is a list of (ques_template, marker_kind) where the template
    has `{slug}` placeholder. We cycle through templates and slugs deterministically.
    """
    out = []
    n_slugs = len(slug_pool)
    n_t = len(templates)
    for i in range(count):
        slug = slug_pool[i % n_slugs]
        ques_t, marker_kind = templates[i % n_t]
        ques = ques_t.format(slug=slug)
        out.append({
            "web_name": WEB_NAME,
            "id": f"{WEB_NAME}--{base_id + i}",
            "ques": ques,
            "web": WEB,
            "upstream_url": UPSTREAM,
            "tags": [round_name, marker_kind, SENTINEL_PREFIX],
        })
    return out


def main() -> None:
    if not DB.exists():
        raise SystemExit(f"DB not found: {DB}")
    # Idempotency check
    if TASKS.exists():
        with TASKS.open() as f:
            for line in f:
                if SENTINEL_PREFIX in line:
                    print(f"[deepen-tasks] already applied ({SENTINEL_PREFIX}), exiting")
                    return

    con = sqlite3.connect(DB)
    cur = con.cursor()

    # Existing task count -> next id
    next_id = 0
    if TASKS.exists():
        with TASKS.open() as f:
            for _ in f:
                next_id += 1
    print(f"[deepen-tasks] existing tasks: {next_id}")

    # Article pools per round
    r3_topics = ["world", "uk", "business", "technology", "politics",
                 "health", "science", "sport"]
    r4_regions = ["uk", "world", "africa", "asia", "europe",
                  "middle-east", "latin-america", "us-canada", "australia"]
    r4_langs = ["en-gb", "zh", "ar", "fa", "ru", "es", "pt-br", "hi", "sw"]
    r5_pool = pick_articles_multi(
        cur, ["iplayer", "sounds", "radio4", "fivelive", "video"], 220)
    if len(r5_pool) < 220:
        r5_pool = pick_articles_multi(cur, ["iplayer", "sounds", "radio4"], 220)
    r6_authors = [r[0] for r in cur.execute(
        "SELECT DISTINCT author FROM articles "
        "WHERE author!='' AND author!='BBC News' ORDER BY author LIMIT 80"
    ).fetchall()]
    r6_pool = pick_articles_multi(cur, ["uk", "world", "business", "politics"], 220)
    r7_pool = pick_articles_multi(
        cur, ["bbc_future", "bbc_worklife", "bbc_earth_deep", "bbcverify"], 220)
    r8_pool = pick_articles_multi(
        cur, ["technology", "business", "health", "sport", "world"], 220)
    r8_chart_topics = ["technology", "business", "health", "sport", "world"]
    r9_cities = ["london", "manchester", "edinburgh", "cardiff", "belfast",
                 "birmingham", "glasgow", "liverpool", "leeds", "newcastle",
                 "bristol", "sheffield", "nottingham", "leicester", "york"]
    r9_sports = ["football", "rugby", "cricket", "tennis",
                 "formula1", "athletics", "boxing", "golf"]
    r9_shows = ["global-news-podcast", "world-business-report", "newscast",
                "americast", "the-coming-storm", "in-our-time", "more-or-less",
                "documentary-podcast", "tech-tent", "the-news-quiz"]
    r10_pool = pick_articles_multi(
        cur, ["uk", "world", "technology", "business", "science"], 220)

    rounds: list[tuple[str, list[dict]]] = []

    # -------- R3: live ticker + breaking pill + live-updates --------
    r3_tasks = []
    for i in range(200):
        topic = r3_topics[i % len(r3_topics)]
        if i % 4 == 0:
            q = (f"On BBC News, GET /r3/ticker?topic={topic}&format=json and "
                 "report the value of `r3_ticker_refresh_seconds` plus the "
                 "headline of the first entry in `r3_ticker_entries`.")
            kind = "r3_ticker"
        elif i % 4 == 1:
            q = (f"On BBC News, open /r3/ticker?topic={topic} and report the "
                 "topic shown in the page header plus the count of "
                 "`r3-ticker-entry` items.")
            kind = "r3_ticker"
        elif i % 4 == 2:
            q = ("On BBC News, GET /r3/breaking-pill and report the value of "
                 "`r3_breaking_pill_ttl` plus the `headline` field.")
            kind = "r3_breaking_pill"
        else:
            q = (f"On BBC News, GET /r3/live-updates/{topic} and report the "
                 "value of `r3_count` plus the first entry's `r3_headline`.")
            kind = "r3_live_updates"
        r3_tasks.append({
            "web_name": WEB_NAME, "id": f"{WEB_NAME}--{next_id + len(r3_tasks)}",
            "ques": q, "web": WEB, "upstream_url": UPSTREAM,
            "tags": ["r3", kind, SENTINEL_PREFIX],
        })
    rounds.append(("r3", r3_tasks))

    # -------- R4: regional + language sub-feeds --------
    r4_tasks = []
    start = next_id + sum(len(t) for _, t in rounds)
    for i in range(200):
        if i % 2 == 0:
            region = r4_regions[i % len(r4_regions)]
            q = (f"On BBC News, GET /r4/region/{region}?format=json and "
                 "report the `r4_region_label`, `r4_lang_code`, and the value "
                 "of `r4_total_items`.")
            kind = "r4_region_mirror"
        else:
            lang = r4_langs[(i // 2) % len(r4_langs)]
            q = (f"On BBC News, GET /r4/language/{lang}?format=json and "
                 "report the `r4_region_label` plus the first slug under "
                 "`r4_region_articles`.")
            kind = "r4_language_mirror"
        r4_tasks.append({
            "web_name": WEB_NAME, "id": f"{WEB_NAME}--{start + i}",
            "ques": q, "web": WEB, "upstream_url": UPSTREAM,
            "tags": ["r4", kind, SENTINEL_PREFIX],
        })
    rounds.append(("r4", r4_tasks))

    # -------- R5: video / iplayer / sounds card --------
    r5_tasks = []
    start = next_id + sum(len(t) for _, t in rounds)
    for i in range(200):
        slug = r5_pool[i % len(r5_pool)] if r5_pool else "newscast"
        if i % 3 == 0:
            q = (f"On BBC News, GET /r5/video-card/{slug}?format=json and "
                 "report `r5_duration_label` plus `r5_bitrate_kbps`.")
            kind = "r5_video_card"
        elif i % 3 == 1:
            q = (f"On BBC News, GET /r5/iplayer-card/{slug}?format=json and "
                 "report `r5_available_until` plus `r5_play_url`.")
            kind = "r5_iplayer_card"
        else:
            q = (f"On BBC News, GET /r5/sounds-card/{slug}?format=json and "
                 "report `r5_bitrate_kbps` plus `r5_embed_url`.")
            kind = "r5_sounds_card"
        r5_tasks.append({
            "web_name": WEB_NAME, "id": f"{WEB_NAME}--{start + i}",
            "ques": q, "web": WEB, "upstream_url": UPSTREAM,
            "tags": ["r5", kind, SENTINEL_PREFIX],
        })
    rounds.append(("r5", r5_tasks))

    # -------- R6: follow-author, comment-stats, save-for-later --------
    r6_tasks = []
    start = next_id + sum(len(t) for _, t in rounds)
    for i in range(200):
        if i % 3 == 0 and r6_authors:
            author = r6_authors[i % len(r6_authors)]
            author_url = author.replace(" ", "%20")
            q = (f"On BBC News, GET /r6/follow-author/{author_url}?format=json"
                 " and report the value of `r6_follower_count` plus "
                 "`r6_article_count`.")
            kind = "r6_follow_author"
        elif i % 3 == 1:
            slug = r6_pool[i % len(r6_pool)] if r6_pool else "newscast"
            q = (f"On BBC News, GET /r6/comment-stats/{slug} and report "
                 "`r6_total_comments` plus `r6_top_level_comments`.")
            kind = "r6_comment_stats"
        else:
            slug = r6_pool[i % len(r6_pool)] if r6_pool else "newscast"
            q = (f"On BBC News, GET /r6/save-for-later/{slug} and report "
                 "`r6_save_ttl_days` plus `r6_save_token`.")
            kind = "r6_save_for_later"
        r6_tasks.append({
            "web_name": WEB_NAME, "id": f"{WEB_NAME}--{start + i}",
            "ques": q, "web": WEB, "upstream_url": UPSTREAM,
            "tags": ["r6", kind, SENTINEL_PREFIX],
        })
    rounds.append(("r6", r6_tasks))

    # -------- R7: longform / in-depth / explainer --------
    r7_tasks = []
    start = next_id + sum(len(t) for _, t in rounds)
    for i in range(200):
        slug = r7_pool[i % len(r7_pool)] if r7_pool else "newscast"
        if i % 3 == 0:
            q = (f"On BBC News, GET /r7/longform/{slug}?format=json and "
                 "report `r7_word_count` plus the title of the first chapter.")
            kind = "r7_longform_view"
        elif i % 3 == 1:
            q = (f"On BBC News, GET /r7/in-depth/{slug}?format=json and "
                 "report `r7_read_time_min` plus `r7_longform_kicker`.")
            kind = "r7_in_depth_view"
        else:
            q = (f"On BBC News, GET /r7/explainer/{slug}?format=json and "
                 "report `r7_explainer_title` plus `r7_token`.")
            kind = "r7_explainer_view"
        r7_tasks.append({
            "web_name": WEB_NAME, "id": f"{WEB_NAME}--{start + i}",
            "ques": q, "web": WEB, "upstream_url": UPSTREAM,
            "tags": ["r7", kind, SENTINEL_PREFIX],
        })
    rounds.append(("r7", r7_tasks))

    # -------- R8: editor's picks / most-read / chart card --------
    r8_tasks = []
    start = next_id + sum(len(t) for _, t in rounds)
    for i in range(200):
        if i % 3 == 0:
            q = ("On BBC News, GET /r8/editors-picks?format=json and "
                 "report the count of items in `r8_editors_picks` plus "
                 "`r8_reference_date`.")
            kind = "r8_editors_picks"
        elif i % 3 == 1:
            q = ("On BBC News, GET /r8/most-read and report `r8_top_n` "
                 "plus the slug of the #1 ranked story.")
            kind = "r8_most_read"
        else:
            topic = r8_chart_topics[i % len(r8_chart_topics)]
            q = (f"On BBC News, GET /r8/chart-card/{topic} and report "
                 "`r8_topic` plus the `r8_value` of the most-recent day "
                 "(D-0) in `r8_chart_rows`.")
            kind = "r8_chart_card"
        r8_tasks.append({
            "web_name": WEB_NAME, "id": f"{WEB_NAME}--{start + i}",
            "ques": q, "web": WEB, "upstream_url": UPSTREAM,
            "tags": ["r8", kind, SENTINEL_PREFIX],
        })
    rounds.append(("r8", r8_tasks))

    # -------- R9: weather widget / sport scoreboard / podcast --------
    r9_tasks = []
    start = next_id + sum(len(t) for _, t in rounds)
    for i in range(200):
        if i % 3 == 0:
            city = r9_cities[i % len(r9_cities)]
            q = (f"On BBC News, GET /r9/weather-widget/{city}?format=json "
                 "and report `r9_current_temp` plus `r9_current_condition`.")
            kind = "r9_weather_widget"
        elif i % 3 == 1:
            sp = r9_sports[i % len(r9_sports)]
            q = (f"On BBC News, GET /r9/sport-scoreboard/{sp} and report "
                 "the count of fixtures plus the `r9_score` of the first "
                 "fixture.")
            kind = "r9_sport_scoreboard"
        else:
            sh = r9_shows[i % len(r9_shows)]
            q = (f"On BBC News, GET /r9/podcast-listen/{sh} and report "
                 "`r9_podcast_bitrate_kbps` plus the `r9_duration_min` of "
                 "episode 1.")
            kind = "r9_podcast_listen"
        r9_tasks.append({
            "web_name": WEB_NAME, "id": f"{WEB_NAME}--{start + i}",
            "ques": q, "web": WEB, "upstream_url": UPSTREAM,
            "tags": ["r9", kind, SENTINEL_PREFIX],
        })
    rounds.append(("r9", r9_tasks))

    # -------- R10: GraphQL + /api/v1/article + /r10/healthz + sitemap --------
    r10_tasks = []
    start = next_id + sum(len(t) for _, t in rounds)
    for i in range(200):
        slug = r10_pool[i % len(r10_pool)] if r10_pool else "newscast"
        m = i % 5
        if m == 0:
            q = (f"On BBC News, GET /r10/graphql?query_kind=article&slug={slug}"
                 " and report `r10_graphql_version` plus the headline returned "
                 "in the data payload.")
            kind = "r10_graphql"
        elif m == 1:
            cat = r4_regions[i % len(r4_regions)].replace("-", "_")
            q = (f"On BBC News, GET /r10/graphql?query_kind=category&category="
                 f"{cat}&limit=3 and report `r10_graphql_schema` plus the "
                 "number of articles returned.")
            kind = "r10_graphql"
        elif m == 2:
            q = (f"On BBC News, GET /api/v1/article/{slug} and report "
                 "`r10_api_version` plus the article's `section`.")
            kind = "r10_api_v1_article"
        elif m == 3:
            q = ("On BBC News, GET /r10/healthz and report `r10_api_version`"
                 " plus `r10_graphql_version`.")
            kind = "r10_healthz"
        else:
            q = ("On BBC News, GET /r10/sitemap.xml and report the count of "
                 "<url> elements plus whether '/r10/graphql' appears in the "
                 "sitemap.")
            kind = "r10_sitemap_xml"
        r10_tasks.append({
            "web_name": WEB_NAME, "id": f"{WEB_NAME}--{start + i}",
            "ques": q, "web": WEB, "upstream_url": UPSTREAM,
            "tags": ["r10", kind, SENTINEL_PREFIX],
        })
    rounds.append(("r10", r10_tasks))

    total = sum(len(t) for _, t in rounds)
    print(f"[deepen-tasks] generated {total} tasks across {len(rounds)} rounds")
    for name, ts in rounds:
        print(f"  {name}: +{len(ts)} tasks")

    with TASKS.open("a") as f:
        for _, ts in rounds:
            for t in ts:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"[deepen-tasks] appended to {TASKS}")


if __name__ == "__main__":
    main()
