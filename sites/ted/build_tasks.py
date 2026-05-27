"""Generate the deepened TED tasks.jsonl (≥1500 GUI-only tasks).

Tasks are deterministic — pure derivation from the seed data. Each task is
verifiable: the answer can be read off the local mirror DOM without leaving
the mirror.

Task IDs follow the convention TED--gui_<page>_<NNN> where <page> identifies
the page family the task exercises.
"""
import json
from pathlib import Path

from seed_data import EVENTS, PLAYLISTS, TALKS
from seed_extended import (BLOG_POSTS, CONFERENCES, MEMBERSHIP_TIERS,
                            NEWSLETTERS, PODCASTS, SERIES, SPEAKERS, TED_ED,
                            TEDX_EVENTS, TOPIC_PAGES)

WEB = "http://localhost:40015/"
UPSTREAM = "https://www.ted.com/"

OUT_PATH = Path(__file__).resolve().parent / "tasks.jsonl"


def fmt(page: str, idx: int) -> str:
    return f"TED--gui_{page}_{idx:04d}"


def build_tasks():
    rows = []

    # ---------------------------------------------------------------
    # TALK DETAIL — five question templates × 350 talks = 1750
    # ---------------------------------------------------------------
    talk_templates = [
        ("duration",  "Open the TED talk \"{title}\" and report the runtime in minutes."),
        ("event",     "Open the talk \"{title}\" and report which TED event it was recorded at."),
        ("speaker",   "Open the talk \"{title}\" and list the speaker's name."),
        ("topics",    "Open the talk \"{title}\" and list two topics it is tagged with."),
        ("views",     "Open the talk \"{title}\" and report the views count shown in the stats panel."),
    ]
    talk_idx = {tag: 0 for tag, _ in talk_templates}
    for talk in TALKS:
        title = talk["title"].replace('"', "'")
        for tag, prompt in talk_templates:
            rows.append({
                "web_name": "TED",
                "id": fmt(f"talk_{tag}", talk_idx[tag]),
                "ques": prompt.format(title=title),
                "web": WEB,
                "upstream_url": UPSTREAM,
            })
            talk_idx[tag] += 1

    # ---------------------------------------------------------------
    # SPEAKERS — 317 speakers × 2 templates = 634
    # ---------------------------------------------------------------
    speaker_idx = {"affiliation": 0, "talks_count": 0}
    for sp in SPEAKERS:
        name = sp["name"]
        rows.append({
            "web_name": "TED",
            "id": fmt("speaker_affiliation", speaker_idx["affiliation"]),
            "ques": f"Open the speaker page for {name} and report their listed affiliation.",
            "web": WEB, "upstream_url": UPSTREAM,
        })
        speaker_idx["affiliation"] += 1
        rows.append({
            "web_name": "TED",
            "id": fmt("speaker_talks", speaker_idx["talks_count"]),
            "ques": f"Open the speaker page for {name} and report how many talks they have on TED.",
            "web": WEB, "upstream_url": UPSTREAM,
        })
        speaker_idx["talks_count"] += 1

    # ---------------------------------------------------------------
    # TOPICS — pick top 60 topics × 2 templates = 120
    # ---------------------------------------------------------------
    top_topics = sorted(TOPIC_PAGES, key=lambda x: -x["talk_count"])[:60]
    for i, tp in enumerate(top_topics):
        rows.append({
            "web_name": "TED",
            "id": fmt("topic_count", i),
            "ques": f"Open the topic page for {tp['name']} and report how many talks are listed.",
            "web": WEB, "upstream_url": UPSTREAM,
        })
        rows.append({
            "web_name": "TED",
            "id": fmt("topic_popular", i),
            "ques": f"Open the topic page for {tp['name']} and report the speaker of the most-viewed talk shown at the top.",
            "web": WEB, "upstream_url": UPSTREAM,
        })

    # ---------------------------------------------------------------
    # PLAYLISTS — 28 playlists × 2 templates = 56
    # ---------------------------------------------------------------
    for i, pl in enumerate(PLAYLISTS):
        rows.append({
            "web_name": "TED",
            "id": fmt("playlist_first", i),
            "ques": f"Open the TED playlist \"{pl['title']}\" and report the title of the first talk.",
            "web": WEB, "upstream_url": UPSTREAM,
        })
        rows.append({
            "web_name": "TED",
            "id": fmt("playlist_count", i),
            "ques": f"Open the TED playlist \"{pl['title']}\" and report how many talks it contains.",
            "web": WEB, "upstream_url": UPSTREAM,
        })

    # ---------------------------------------------------------------
    # SERIES — 8 series × 3 templates = 24
    # ---------------------------------------------------------------
    for i, s in enumerate(SERIES):
        rows.append({
            "web_name": "TED",
            "id": fmt("series_host", i),
            "ques": f"Open the TED series page \"{s['name']}\" and report the name of the host.",
            "web": WEB, "upstream_url": UPSTREAM,
        })
        rows.append({
            "web_name": "TED",
            "id": fmt("series_episodes", i),
            "ques": f"Open the TED series page \"{s['name']}\" and report how many episodes it has.",
            "web": WEB, "upstream_url": UPSTREAM,
        })
        rows.append({
            "web_name": "TED",
            "id": fmt("series_tagline", i),
            "ques": f"Open the TED series page \"{s['name']}\" and report its tagline.",
            "web": WEB, "upstream_url": UPSTREAM,
        })

    # ---------------------------------------------------------------
    # PODCASTS — 8 shows × 3 templates + per-episode = 24 + 144
    # ---------------------------------------------------------------
    pod_ep_idx = 0
    for i, p in enumerate(PODCASTS):
        rows.append({
            "web_name": "TED",
            "id": fmt("podcast_host", i),
            "ques": f"Open the podcast page for \"{p['name']}\" and report its host.",
            "web": WEB, "upstream_url": UPSTREAM,
        })
        rows.append({
            "web_name": "TED",
            "id": fmt("podcast_freq", i),
            "ques": f"Open the podcast page for \"{p['name']}\" and report its publishing frequency.",
            "web": WEB, "upstream_url": UPSTREAM,
        })
        rows.append({
            "web_name": "TED",
            "id": fmt("podcast_publisher", i),
            "ques": f"Open the podcast page for \"{p['name']}\" and report its publisher.",
            "web": WEB, "upstream_url": UPSTREAM,
        })
        for ep in p["episodes"]:
            rows.append({
                "web_name": "TED",
                "id": fmt("podcast_episode", pod_ep_idx),
                "ques": f"Open episode \"{ep['title']}\" in the \"{p['name']}\" podcast and report its duration in seconds (use mm:ss × 60 if needed).",
                "web": WEB, "upstream_url": UPSTREAM,
            })
            pod_ep_idx += 1

    # ---------------------------------------------------------------
    # TED-Ed — 60 lessons × 2 templates = 120
    # ---------------------------------------------------------------
    for i, l in enumerate(TED_ED):
        rows.append({
            "web_name": "TED",
            "id": fmt("ted_ed_subject", i),
            "ques": f"Open the TED-Ed lesson \"{l['title']}\" and report its subject area.",
            "web": WEB, "upstream_url": UPSTREAM,
        })
        rows.append({
            "web_name": "TED",
            "id": fmt("ted_ed_grade", i),
            "ques": f"Open the TED-Ed lesson \"{l['title']}\" and report the recommended grade band.",
            "web": WEB, "upstream_url": UPSTREAM,
        })

    # ---------------------------------------------------------------
    # CONFERENCES — 12 confs × 3 templates = 36
    # ---------------------------------------------------------------
    for i, c in enumerate(CONFERENCES):
        rows.append({
            "web_name": "TED",
            "id": fmt("conference_theme", i),
            "ques": f"Open the {c['name']} conference page and report its theme.",
            "web": WEB, "upstream_url": UPSTREAM,
        })
        rows.append({
            "web_name": "TED",
            "id": fmt("conference_city", i),
            "ques": f"Open the {c['name']} conference page and report the host city.",
            "web": WEB, "upstream_url": UPSTREAM,
        })
        rows.append({
            "web_name": "TED",
            "id": fmt("conference_capacity", i),
            "ques": f"Open the {c['name']} conference page and report the listed capacity.",
            "web": WEB, "upstream_url": UPSTREAM,
        })

    # ---------------------------------------------------------------
    # TEDX — 30 events × 2 templates = 60
    # ---------------------------------------------------------------
    for i, e in enumerate(TEDX_EVENTS):
        rows.append({
            "web_name": "TED",
            "id": fmt("tedx_theme", i),
            "ques": f"Open the TEDx event page for {e['name']} and report its theme.",
            "web": WEB, "upstream_url": UPSTREAM,
        })
        rows.append({
            "web_name": "TED",
            "id": fmt("tedx_organizer", i),
            "ques": f"Open the TEDx event page for {e['name']} and report its organizer.",
            "web": WEB, "upstream_url": UPSTREAM,
        })

    # ---------------------------------------------------------------
    # MEMBERSHIP — 4 tiers × 2 templates = 8
    # ---------------------------------------------------------------
    for i, t in enumerate(MEMBERSHIP_TIERS):
        rows.append({
            "web_name": "TED",
            "id": fmt("membership_price", i),
            "ques": f"Open the TED Membership levels page and report the monthly price of the {t['name']} tier.",
            "web": WEB, "upstream_url": UPSTREAM,
        })
        rows.append({
            "web_name": "TED",
            "id": fmt("membership_tagline", i),
            "ques": f"Open the TED Membership levels page and report the tagline of the {t['name']} tier.",
            "web": WEB, "upstream_url": UPSTREAM,
        })

    # ---------------------------------------------------------------
    # NEWSLETTERS — 7 × 1 = 7
    # ---------------------------------------------------------------
    for i, n in enumerate(NEWSLETTERS):
        rows.append({
            "web_name": "TED",
            "id": fmt("newsletter_freq", i),
            "ques": f"Open the TED newsletters page and report the publishing frequency of the {n['name']} newsletter.",
            "web": WEB, "upstream_url": UPSTREAM,
        })

    # ---------------------------------------------------------------
    # BLOG — 80 posts × 2 = 160
    # ---------------------------------------------------------------
    for i, b in enumerate(BLOG_POSTS):
        rows.append({
            "web_name": "TED",
            "id": fmt("blog_author", i),
            "ques": f"Open the TED Ideas blog post titled \"{b['title']}\" and report the author.",
            "web": WEB, "upstream_url": UPSTREAM,
        })
        rows.append({
            "web_name": "TED",
            "id": fmt("blog_bucket", i),
            "ques": f"Open the TED Ideas blog post titled \"{b['title']}\" and report which category (bucket) it is filed under.",
            "web": WEB, "upstream_url": UPSTREAM,
        })

    # ---------------------------------------------------------------
    # INTERACTIVE — save / subscribe / register / translate / playlist / note
    # Cap at a few high-quality multi-step flows referencing specific seed items.
    # ---------------------------------------------------------------
    interactive_seeds = [
        # (page-tag, prompt)
        ("save", "Sign in as alice.j@test.com (password TestPass123!) and save the TED talk \"How I set myself free\" with the note 'inspiration'."),
        ("save", "Sign in as bob.c@test.com and save the talk \"How to be smarter about the news\" with the note 'media literacy reading'."),
        ("note", "Sign in as alice.j@test.com and add a personal note 'rewatch with team' to the Keke Palmer talk \"How I set myself free\"."),
        ("note", "Sign in as carol.d@test.com and add a note 'design retro material' on the Tom Rizzuto streaming talk."),
        ("rate", "Sign in as alice.j@test.com, open the Keke Palmer talk, and rate it 5/5."),
        ("rate", "Sign in as bob.c@test.com, open the Ian Bremmer news talk, and rate it 4/5."),
        ("comment", "Sign in as alice.j@test.com, open the discussion for the Keke Palmer talk \"How I set myself free\", and post the comment 'Loved the framing of agency'."),
        ("comment", "Sign in as david.k@test.com and post a comment 'sharing with policy team' on the Ian Bremmer news talk discussion page."),
        ("share", "Sign in as alice.j@test.com, open the Keke Palmer talk, and share it via email."),
        ("share", "Sign in as bob.c@test.com, open the Ian Bremmer talk, and share it via LinkedIn."),
        ("playlist_create", "Sign in as alice.j@test.com and create a new private playlist titled 'Friday classroom warmups'."),
        ("playlist_create", "Sign in as bob.c@test.com and create a public playlist titled 'Climate reading list 2026'."),
        ("playlist_add", "Sign in as alice.j@test.com, open your favorites playlist, and add the talk \"How I set myself free\" by Keke Palmer."),
        ("playlist_delete_item", "Sign in as alice.j@test.com and remove the first item from your favorites playlist."),
        ("subscribe", "Sign in as alice.j@test.com and upgrade your membership to the Patron tier on annual billing."),
        ("subscribe", "Sign in as bob.c@test.com and upgrade your membership to the Supporter tier on monthly billing."),
        ("newsletter", "Subscribe alice.j@test.com to the TED AI newsletter from the newsletter subscribe page."),
        ("newsletter", "Subscribe bob.c@test.com to the TED Countdown newsletter."),
        ("conference_apply", "Sign in as alice.j@test.com and submit a conference application for TED2026 with role 'Attendee' and a short motivation."),
        ("conference_apply", "Sign in as bob.c@test.com and apply to TEDNext 2026 as a 'Speaker nominator'."),
        ("conference_attend", "Sign in as alice.j@test.com, open the TED2026 attend logistics page, and confirm interest in side events."),
        ("tedx_rsvp", "Sign in as carol.d@test.com and submit an RSVP for TEDxBerkeley 2026 as a Volunteer."),
        ("translate_submit", "Sign in as emily.r@test.com and submit a Spanish translation draft for the Keke Palmer talk \"How I set myself free\"."),
        ("translate_review", "Sign in as alice.j@test.com, open the translator dashboard, and mark your most recent submission as approved."),
        ("event_register", "Sign in as alice.j@test.com and register interest in the TED Countdown Summit event."),
        ("blog_comment", "Sign in as alice.j@test.com, open the first TED Ideas blog post listed, and post the comment 'Saving this for our reading group.'"),
        ("blog_share", "Sign in as bob.c@test.com, open the first TED Ideas blog post, and share it via X / Twitter."),
        ("profile_update", "Sign in as alice.j@test.com and change the newsletter topic on the account page to 'design'."),
        ("profile_update", "Sign in as bob.c@test.com and change the city on the account page to 'Cambridge, MA'."),
        ("register_account", "Create a new TED account with email new.user@test.com, username new_user, display name 'New User', and password TestPass123!."),
        ("login_logout", "Sign in as alice.j@test.com and then sign out from the topbar."),
        ("comment_vote", "Sign in as bob.c@test.com, open the discussion for the Keke Palmer talk, and upvote the first comment."),
        ("comment_report", "Sign in as carol.d@test.com, open the discussion for the Ian Bremmer talk, and report the first comment as spam."),
        ("note_delete", "Sign in as alice.j@test.com, open your notes page, and delete one note."),
        ("playlist_delete", "Sign in as alice.j@test.com, open one of your playlists, and delete it."),
    ]
    for i, (tag, q) in enumerate(interactive_seeds):
        rows.append({
            "web_name": "TED",
            "id": fmt(f"act_{tag}", i),
            "ques": q,
            "web": WEB, "upstream_url": UPSTREAM,
        })

    # ---------------------------------------------------------------
    # BROWSE / FILTER — sort / filter / multi-step navigation
    # ---------------------------------------------------------------
    browse_seeds = [
        "Open the TED Talks page, filter to talks under 8 minutes, and report the title of the first talk shown.",
        "Open the TED Talks page, sort by Most viewed, and report the speaker of the first talk shown.",
        "Open the topics page, find the topic with the highest talk count, and report its name.",
        "Open the Conferences page and report the city of the next flagship TED conference listed.",
        "Open the TEDx page and report how many TEDx events are listed.",
        "Open the Podcasts page and report how many podcasts are in the TED Audio Collective directory.",
        "Open the Series page and report the host of TED Countdown series.",
        "Open the TED Ideas blog and filter by the 'long-form' bucket; report the title of the first post.",
        "From the home page navigation, open the Speakers directory and report how many speakers are listed.",
        "Open the search page, search for 'AI' in the Speakers tab, and report how many results come back.",
        "Open the search page, search for 'climate' in the Blog tab, and report the title of the first matching post.",
        "Open the search page, search for 'design' in the Podcasts tab, and report the title of the first matching podcast.",
        "Open the TED-Ed page, filter by subject 'Science & Technology', and report how many lessons remain.",
        "Open the TED-Ed page, filter to grade band 'Grades 9–12', and report the title of the first lesson.",
        "Open the TED Talks page, set the event filter to TED2026, and report how many talks are listed.",
    ]
    for i, q in enumerate(browse_seeds):
        rows.append({
            "web_name": "TED",
            "id": fmt("browse", i),
            "ques": q,
            "web": WEB, "upstream_url": UPSTREAM,
        })

    return rows


def main():
    rows = build_tasks()
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} tasks to {OUT_PATH}")


if __name__ == "__main__":
    main()
