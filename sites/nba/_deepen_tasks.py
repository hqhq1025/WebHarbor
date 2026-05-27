#!/usr/bin/env python3
"""NBA deepen — generate ≥1500 GUI tasks across every new surface.

Reads instance_seed/nba.db to enumerate concrete slugs. Emits stable task
ids `NBA--gui_<page>_<NNN>`. Pure GUI phrasing — no "GET /api", no "parse
the JSON". Writes the rebuilt tasks.jsonl in-place.
"""
import hashlib
import json
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "instance_seed", "nba.db")
OUT = os.path.join(HERE, "tasks.jsonl")

BASE = {"web_name": "NBA", "web": "http://localhost:40015/", "upstream_url": "https://www.nba.com/"}


def h(key, mod):
    return int.from_bytes(hashlib.md5(key.encode()).digest()[:4], "big") % mod


def pick(key, options):
    return options[h(key, len(options))]


def load():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    teams = [dict(r) for r in conn.execute(
        "SELECT slug, name, city, conference, division, arena, coach, "
        "wins, losses, ppg, oppg FROM teams ORDER BY id"
    )]
    players = [dict(r) for r in conn.execute(
        "SELECT slug, name, position, jersey, team_id, ppg, rpg, apg, "
        "spg, bpg, fg_pct, three_pct FROM players ORDER BY ppg DESC"
    )]
    team_by_id = {dict(r)['id']: dict(r) for r in conn.execute(
        "SELECT id, slug, name, city FROM teams"
    )}
    games = [dict(r) for r in conn.execute(
        "SELECT id, status, home_team_id, away_team_id, home_score, away_score "
        "FROM games ORDER BY id"
    )]
    prospects = [dict(r) for r in conn.execute(
        "SELECT slug, name, position, college, country, mock_rank, tier, comp "
        "FROM draft_prospects ORDER BY mock_rank"
    )]
    videos = [dict(r) for r in conn.execute(
        "SELECT slug, title, kind, team_slug, player_slug, duration, views "
        "FROM videos ORDER BY views DESC LIMIT 60"
    )]
    products = [dict(r) for r in conn.execute(
        "SELECT slug, name, category, team_slug, price FROM products ORDER BY id"
    )]
    f_teams = [dict(r) for r in conn.execute(
        "SELECT slug, league_slug, name, wins, losses, pts_for "
        "FROM fantasy_teams WHERE user_id > 0 ORDER BY id"
    )]
    f_leagues = [dict(r) for r in conn.execute(
        "SELECT slug, name, scoring, team_count FROM fantasy_leagues"
    )]
    awards = [dict(r) for r in conn.execute(
        "SELECT year, slug, name, winner_slug FROM awards WHERE year=2026"
    )]
    leaders = [dict(r) for r in conn.execute(
        "SELECT category, rank, player_slug, value FROM stat_leaderboards "
        "ORDER BY category, rank"
    )]
    conn.close()
    for p in players:
        p["team"] = team_by_id.get(p["team_id"], {"slug": "lakers", "name": "Lakers", "city": "Los Angeles"})
    return {
        "teams": teams, "players": players, "games": games,
        "prospects": prospects, "videos": videos, "products": products,
        "f_teams": f_teams, "f_leagues": f_leagues, "awards": awards,
        "leaders": leaders, "team_by_id": team_by_id,
    }


def emit(out, ctx, page, ques):
    n = ctx["counter"][page]
    ctx["counter"][page] = n + 1
    tid = f"NBA--gui_{page}_{n:03d}"
    out.append({**BASE, "id": tid, "ques": ques})


# ── page generators ────────────────────────────────────────────────────────

def gen_team_news(out, ctx, data):
    variants = [
        "Open the {city} {name} News page from the team's left-nav and report the most recent two news headlines and their tags shown on the page.",
        "Navigate to the {city} {name} team page, click News in the team subnav, and report the headline plus tag for the latest story.",
        "From the {city} {name} team page, navigate to News and tell me what topic the latest 'Roster spotlight' or 'Practice notes' story covers in its body paragraph.",
    ]
    for t in data["teams"]:
        for v in variants:
            emit(out, ctx, "team_news", v.format(city=t['city'], name=t['name']))


def gen_team_video(out, ctx, data):
    variants = [
        "Open the {city} {name} Video page and report two clip titles plus their kinds (Highlights, Top10, Intro, Access, Presser, or Locker).",
        "From the {city} {name} Video page, browse the Team Highlights row and report the title of the first Highlights clip plus the title of the first Top10 clip.",
        "From the {city} {name} Video page, find the Pregame Intro clip and report its duration and view count.",
    ]
    for t in data["teams"]:
        for v in variants:
            emit(out, ctx, "team_video", v.format(city=t['city'], name=t['name']))


def gen_team_tickets(out, ctx, data):
    for t in data["teams"]:
        emit(out, ctx, "team_tickets",
             f"Open the {t['city']} {t['name']} Tickets page and report the next two scheduled home or road games it lists, including arenas.")
        emit(out, ctx, "team_tickets",
             f"On the {t['city']} {t['name']} Tickets page, choose any upcoming game, set Section to Suite Level, Seats to 3 and submit Buy Tickets. Report the confirmation number from the My Ticket Orders page.")


def gen_team_store(out, ctx, data):
    for t in data["teams"]:
        emit(out, ctx, "team_store",
             f"Open the {t['city']} {t['name']} Store page and report two team products with their prices.")


def gen_team_stats_adv(out, ctx, data):
    for t in data["teams"]:
        emit(out, ctx, "team_stats_advanced",
             f"Open Advanced Stats for the {t['city']} {t['name']} and report the eFG% and Pace shown for the most recent game listed.")
        emit(out, ctx, "team_stats_advanced",
             f"From the {t['city']} {t['name']} Advanced Stats page, find the game with the lowest Turnover% and report that game's eFG% and OREB%.")


def gen_player_career(out, ctx, data):
    for p in data["players"][:60]:
        emit(out, ctx, "player_career",
             f"Open {p['name']}'s Career page and report his Home and Away PPG from the season splits table.")
        emit(out, ctx, "player_career",
             f"On {p['name']}'s Career page, find the signature shoe card and report the brand, colorway and listed price.")
        emit(out, ctx, "player_career",
             f"From {p['name']}'s Career page, report two leaderboard rankings shown (category and rank), then click into one of them.")


def gen_player_gamelog(out, ctx, data):
    for p in data["players"][:50]:
        emit(out, ctx, "player_gamelog",
             f"Open {p['name']}'s Game Log and report his points, rebounds and assists from his most recent game and whether it was a Win or Loss.")
        emit(out, ctx, "player_gamelog",
             f"On {p['name']}'s Game Log, find the game with the highest PTS and report the opponent and the FG line for that game.")


def gen_player_splits(out, ctx, data):
    for p in data["players"][:50]:
        emit(out, ctx, "player_splits",
             f"Open {p['name']}'s Splits page and report his Wins-vs-Losses PPG comparison.")
        emit(out, ctx, "player_splits",
             f"On {p['name']}'s Splits page, report his Before All-Star and After All-Star FG% values.")


def gen_player_news(out, ctx, data):
    for p in data["players"][:40]:
        emit(out, ctx, "player_news",
             f"Open {p['name']}'s News page and report the latest news item's tag and the first sentence of its body.")


def gen_player_shoes(out, ctx, data):
    for p in data["players"][:40]:
        emit(out, ctx, "player_shoes",
             f"Open {p['name']}'s Signature Shoes page and report the brand, shoe name and listed price.")


def gen_game_box(out, ctx, data):
    for g in data["games"][:30]:
        emit(out, ctx, "game_box",
             f"Open the Box Score for game #{g['id']} and report each team's Q1 and Q4 points plus their final FG made-attempted line.")
        emit(out, ctx, "game_box",
             f"On the Box Score for game #{g['id']}, report which team had more assists and the AST values for both teams.")


def gen_game_pbp(out, ctx, data):
    for g in data["games"][:25]:
        emit(out, ctx, "game_pbp",
             f"Open the Play-by-Play for game #{g['id']} and report the Q1 opening event description and the score after that play.")
        emit(out, ctx, "game_pbp",
             f"From the Play-by-Play of game #{g['id']}, find any Q3 event and report which team's player made the play and the description.")


def gen_game_shot(out, ctx, data):
    for g in data["games"][:25]:
        emit(out, ctx, "game_shotchart",
             f"Open the Shot Chart for game #{g['id']} and report how many of the listed shots were 3-point attempts and how many were Made.")
        emit(out, ctx, "game_shotchart",
             f"On the Shot Chart for game #{g['id']}, find a Made 3-pointer and report its distance and the team that took it.")


def gen_game_ff(out, ctx, data):
    for g in data["games"][:20]:
        emit(out, ctx, "game_four_factors",
             f"Open the Four Factors view for game #{g['id']} and report each team's eFG% and Pace.")


def gen_draft(out, ctx, data):
    for year in (2024, 2025, 2026):
        emit(out, ctx, "draft_year",
             f"Open the {year} Draft Central page and report the top three mock-board prospects with their colleges.")
        emit(out, ctx, "draft_prospects",
             f"Open the {year} Draft Prospects page and find the player listed with a 7-2 wingspan; report his name, height and college.")
        emit(out, ctx, "draft_lottery",
             f"Open the {year} Draft Lottery page and report the team with the #1 final pick and its odds percentage.")
        emit(out, ctx, "draft_picks",
             f"Open the {year} Draft Picks page and report the team that holds first-round pick #3 and the prospect assigned to that pick.")
    # individual prospect-focused tasks
    for p in data["prospects"][:30]:
        emit(out, ctx, "draft_prospects",
             f"On the 2026 Draft Prospects page, locate {p['name']} and report his mock rank, position and comp player.")
        emit(out, ctx, "draft_prospects",
             f"Find {p['name']} on the 2026 Draft Prospects page and report his listed strengths in one sentence.")


def gen_awards(out, ctx, data):
    for a in data["awards"]:
        emit(out, ctx, "awards_year",
             f"Open the 2026 NBA Awards page and report the winner of the {a['name']} along with the vote share.")
        emit(out, ctx, "awards_year",
             f"On the 2026 NBA Awards page, find the {a['name']} card and report the runner-up and the third-place player.")
    emit(out, ctx, "awards_year", "Open the 2026 NBA Awards page and report which player appears as runner-up for the Kia Most Valuable Player award.")
    emit(out, ctx, "awards_year", "Open the 2025 NBA Awards page and report the MVP winner with his vote share.")
    emit(out, ctx, "awards_year", "After signing in, submit a 2026 MVP ballot listing shai-gilgeous-alexander first, nikola-jokic second, and luka-doncic third. Report the success flash text shown.")


def gen_allstar(out, ctx, data):
    for year in (2024, 2025, 2026):
        emit(out, ctx, "allstar_year",
             f"Open the {year} NBA All-Star page and report the top East frontcourt fan-vote leader with his vote count.")
        emit(out, ctx, "allstar_year",
             f"On the {year} NBA All-Star page, scroll to the Celebrity Game section and report two celebrity participants with their team assignments.")
        emit(out, ctx, "allstar_celebrity_game",
             f"Open the {year} Celebrity All-Star Game page and report two participants with their roles (Captain, Starter, Reserve, or Honorary captain).")
    for p in data["players"][:20]:
        emit(out, ctx, "allstar_voting",
             f"After signing in, open the 2026 All-Star Voting page, choose {p['name']} from his conference's candidate grid and submit the ballot. Report the success flash shown.")


def gen_stats_leaders(out, ctx, data):
    cats = [("ppg", "Points"), ("rpg", "Rebounds"), ("apg", "Assists"),
            ("spg", "Steals"), ("bpg", "Blocks"),
            ("fg_pct", "FG percentage"), ("three_pct", "Three-point percentage")]
    for slug, label in cats:
        for i in range(6):
            emit(out, ctx, "stats_leaders_category",
                 f"Open the NBA {label} Leaders page and report the top three players with their stat values.")
    # team-level
    for t in data["teams"]:
        for slug, label in [("ppg", "Points"), ("rpg", "Rebounds"), ("apg", "Assists"),
                            ("bpg", "Blocks"), ("three_pct", "Three-point percentage")]:
            emit(out, ctx, "stats_team_leaders",
                 f"Open the {t['city']} {t['name']} {label} Leaders page and report the team's top scorer or stat leader in that category along with the value.")


def gen_playoffs(out, ctx, data):
    for year in (2024, 2025, 2026):
        emit(out, ctx, "playoffs_year",
             f"Open the {year} NBA Playoffs page and report two East teams listed in the {year} playoff field.")
        emit(out, ctx, "playoffs_bracket",
             f"Open the {year} Playoff Bracket page and report two Western Conference teams along with their season records.")
        emit(out, ctx, "playoffs_finals",
             f"Open the {year} NBA Finals page and report two teams shown with their arenas and head coaches.")


def gen_video(out, ctx, data):
    kinds = ["Highlights", "Recap", "Film", "Top10", "Dunks", "Blocks", "Assists", "Wired", "Presser", "Practice"]
    for k in kinds:
        for i in range(6):
            emit(out, ctx, "video_index",
                 f"Open the NBA Video library and filter by {k}; report the top clip's title and its view count.")
    for v in data["videos"][:30]:
        emit(out, ctx, "video_detail",
             f"Open the video clip titled '{v['title']}' from the NBA Video library and report its duration and view count.")
        emit(out, ctx, "video_detail",
             f"After signing in, open the video clip '{v['title']}', click Like Highlight and report the flash message shown.")


def gen_fantasy(out, ctx, data):
    for l in data["f_leagues"]:
        emit(out, ctx, "fantasy_league_detail",
             f"Open the Fantasy League page for {l['name']} and report its scoring format and team count.")
        emit(out, ctx, "fantasy_league_detail",
             f"On the {l['name']} fantasy league standings, report the top team's name with its W-L record.")
    for ft in data["f_teams"]:
        emit(out, ctx, "fantasy_team_detail",
             f"Open the fantasy team page for {ft['name']} and report its W-L record and its points-for total.")
        emit(out, ctx, "fantasy_team_detail",
             f"On the fantasy team page for {ft['name']}, report two roster slots and the players occupying them.")
    # POST-style
    for ft in data["f_teams"][:8]:
        emit(out, ctx, "fantasy_lineup",
             f"After signing in, open the Set Lineup page for fantasy team {ft['name']} and lock the PG slot, then submit. Report the flash message shown after saving.")


def gen_account_pages(out, ctx, data):
    for surface, title in [("my_follows", "My Follows"),
                           ("my_alerts", "My Alerts"),
                           ("my_saved_games", "My Saved Games"),
                           ("my_ticket_orders", "My Ticket Orders"),
                           ("my_wishlist", "My Wishlist"),
                           ("my_mock_drafts", "My Mock Drafts"),
                           ("preferences", "Preferences")]:
        for i in range(4):
            emit(out, ctx, surface,
                 f"After signing in, open the {title} page from the account tabs and report two items it currently shows for the logged-in user.")
    # POST actions
    for t in data["teams"][:15]:
        emit(out, ctx, "follow_team",
             f"Sign in, open the {t['city']} {t['name']} team page and click Follow {t['city']} {t['name']}. Then open My Follows and confirm the team appears.")
    for p in data["players"][:15]:
        emit(out, ctx, "follow_player",
             f"Sign in, open {p['name']}'s player page and click the Follow button. Then open My Follows and confirm the player appears.")
    for surface in ["alert_add", "alert_toggle"]:
        for i in range(5):
            label = pick(f"{surface}-{i}", ["Lakers tipoff", "Celtics tipoff", "Knicks player news", "MVP voting open", "Score swing for Mavericks"])
            emit(out, ctx, surface,
                 f"After signing in, open My Alerts and {'create a new alert labeled ' + repr(label) if surface=='alert_add' else 'pause an existing alert'}. Confirm the change on the My Alerts page.")
    for v in data["videos"][:10]:
        emit(out, ctx, "video_share",
             f"After signing in, open the video '{v['title']}', share it via email to teammate@example.com, and report the flash message shown.")
    for prod in data["products"][:15]:
        emit(out, ctx, "wishlist_add",
             f"After signing in, open the product page for {prod['name']} from the NBA Store and add it to your wishlist; confirm it appears on My Wishlist.")


def gen_search_followups(out, ctx, data):
    # Cross-surface tasks combining new pages
    for t in data["teams"][:20]:
        emit(out, ctx, "cross",
             f"Open the {t['city']} {t['name']} team page; click into Advanced Stats and report the most recent game's pace.")
        emit(out, ctx, "cross",
             f"Open the {t['city']} {t['name']} team page; click into Video and report the title of the first Locker clip.")
    for p in data["players"][:20]:
        emit(out, ctx, "cross",
             f"Open {p['name']}'s player page; switch to Game Log and report his recent points-per-game over the last three games.")
    for g in data["games"][:15]:
        emit(out, ctx, "cross",
             f"Open game #{g['id']}; click Box Score and then Play-by-Play, and report any Q1 event description.")


GENERATORS = [
    gen_team_news, gen_team_video, gen_team_tickets, gen_team_store, gen_team_stats_adv,
    gen_player_career, gen_player_gamelog, gen_player_splits, gen_player_news, gen_player_shoes,
    gen_game_box, gen_game_pbp, gen_game_shot, gen_game_ff,
    gen_draft, gen_awards, gen_allstar,
    gen_stats_leaders, gen_playoffs, gen_video, gen_fantasy,
    gen_account_pages, gen_search_followups,
]


def main():
    data = load()
    out = []
    ctx = {"counter": {}}
    # Initialize counters for known page slugs
    for page in [
        "team_news", "team_video", "team_tickets", "team_store", "team_stats_advanced",
        "player_career", "player_gamelog", "player_splits", "player_news", "player_shoes",
        "game_box", "game_pbp", "game_shotchart", "game_four_factors",
        "draft_year", "draft_prospects", "draft_lottery", "draft_picks",
        "awards_year", "allstar_year", "allstar_voting", "allstar_celebrity_game",
        "stats_leaders_category", "stats_team_leaders",
        "playoffs_year", "playoffs_bracket", "playoffs_finals",
        "video_index", "video_detail",
        "fantasy_league_detail", "fantasy_team_detail", "fantasy_lineup",
        "my_follows", "my_alerts", "my_saved_games", "my_ticket_orders",
        "my_wishlist", "my_mock_drafts", "preferences",
        "follow_team", "follow_player", "alert_add", "alert_toggle",
        "video_share", "wishlist_add",
        "cross",
    ]:
        ctx["counter"][page] = 0

    for gen in GENERATORS:
        gen(out, ctx, data)

    with open(OUT, "w") as f:
        for row in out:
            f.write(json.dumps(row) + "\n")

    print(f"Wrote {len(out)} tasks to {OUT}")
    by_page = {}
    for r in out:
        page = r["id"].split("_", 1)[1].rsplit("_", 1)[0]
        by_page[page] = by_page.get(page, 0) + 1
    for page in sorted(by_page):
        print(f"  {page}: {by_page[page]}")


if __name__ == "__main__":
    main()
