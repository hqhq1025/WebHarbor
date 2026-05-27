#!/usr/bin/env python3
"""Append R5 GUI Bracket tasks to sites/espn/tasks.jsonl.

GUI tasks targeting the new /r5/* surface: NCAA Men's + Women's March
Madness brackets, NBA Play-In Tournament, and NHL Stanley Cup Playoffs
brackets. All tasks are natural-language multi-step GUI instructions.

Task IDs: ESPN--r5_<theme>_<NN>. Idempotent: re-running is a no-op once
R5 GUI tasks are present.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(HERE, 'tasks.jsonl')

WEB = 'http://localhost:40014/'
UPSTREAM = 'https://www.espn.com/'


def load_existing():
    with open(TASKS, 'r', encoding='utf-8') as f:
        return [ln for ln in f if ln.strip()]


def has_r5gui_tasks(existing):
    return any('"ESPN--r5_' in ln for ln in existing)


def emit(records, theme, items):
    for i, q in enumerate(items):
        tid = f'ESPN--r5_{theme}_{i:03d}'
        records.append({
            'web_name': 'ESPN', 'id': tid, 'ques': q,
            'web': WEB, 'upstream_url': UPSTREAM,
        })


def main():
    existing = load_existing()
    if has_r5gui_tasks(existing):
        print(f'R5 GUI tasks already present ({len(existing)} rows) — no-op.')
        return

    records = []

    # ─── Theme 1: NCAA Men's bracket ─────────────────────────────────────
    REGIONS_M = ['East', 'West', 'South', 'Midwest']
    BRACKET_SLUG_M = 'ncaa-mens-2024'

    mens_tasks = []
    # 2-3 step easy
    mens_tasks.append(
        "On ESPN's Bracket Center, open the NCAA Division I Men's "
        "Basketball Tournament 2024 bracket and report the named champion "
        "and runner-up listed at the top of the bracket page.")
    mens_tasks.append(
        "Open the 2024 NCAA Men's Tournament bracket on ESPN and report "
        "the announced venue (host stadium) of the championship game.")
    mens_tasks.append(
        "On ESPN's NCAA Men's 2024 bracket page, list the four region "
        "names linked under 'Regions'.")
    for region in REGIONS_M:
        mens_tasks.append(
            f"On ESPN's NCAA Men's 2024 bracket, open the {region} region "
            "and report which team is the 1-seed along with that team's "
            "conference.")
        mens_tasks.append(
            f"In the {region} region of the 2024 NCAA Men's bracket on "
            "ESPN, report the team listed as the 12-seed and its "
            "regular-season record.")
        mens_tasks.append(
            f"Open the {region} region of the 2024 NCAA Men's bracket on "
            "ESPN. Report the head coach of the team seeded #4.")

    # Round-level browsing
    for rn, label in [(1, 'Round of 64'), (2, 'Round of 32'),
                       (3, 'Sweet 16'), (4, 'Elite Eight'),
                       (5, 'Final Four'), (6, 'National Championship')]:
        mens_tasks.append(
            f"On ESPN's NCAA Men's 2024 bracket, open the {label} (round "
            f"{rn}) page and report how many matchups are listed on that "
            "round page.")

    # Single-matchup detail
    for region in REGIONS_M:
        mens_tasks.append(
            f"On ESPN's NCAA Men's 2024 bracket, open the {region} "
            "region's Round of 64 page and click into the (1) vs (16) "
            "matchup. Report the leading scorer's name and points listed "
            "on that matchup detail page.")
        mens_tasks.append(
            f"In the {region} region of the 2024 NCAA Men's bracket, open "
            "the Sweet 16 page and report the score of the first matchup "
            "listed (both teams + both scores + winner).")

    # Multi-step path tracing
    mens_tasks.append(
        "On ESPN's NCAA Men's 2024 bracket, open the East region. Trace "
        "UConn's tournament path by opening UConn's seed-profile page "
        "(click on UConn in the seed table). Report the number of games "
        "shown on UConn's tournament path list.")
    mens_tasks.append(
        "On ESPN's NCAA Men's 2024 bracket, open Purdue's seed profile "
        "from the Midwest region. Report Purdue's head coach and the "
        "score of Purdue's Final Four game listed on the path list.")
    mens_tasks.append(
        "Open the 2024 NCAA Men's bracket National Championship page on "
        "ESPN and report (a) the leading scorer's name, (b) their points "
        "total, and (c) the final score.")
    mens_tasks.append(
        "On ESPN's NCAA Men's 2024 bracket, open the Final Four round "
        "page. Report both Final Four matchups (which team beat which) "
        "and identify the eventual national champion.")

    # 7+ step cross-region comparison
    mens_tasks.append(
        "On ESPN's NCAA Men's 2024 bracket, open each region (East, "
        "West, South, Midwest) and report which region's 12-seed had "
        "the best regular-season record. Open the seed-table on each "
        "region page to see records.")
    mens_tasks.append(
        "Across the East, West, South, and Midwest regions of the 2024 "
        "NCAA Men's bracket on ESPN, find which region's 1-seed survived "
        "the deepest into the tournament. Open each region's results "
        "list and identify the elimination round of each 1-seed.")

    # Disambiguation
    mens_tasks.append(
        "On ESPN's NCAA Men's 2024 bracket, I'm trying to find a team — "
        "I know a 13-seed pulled off an upset over a 4-seed in the Round "
        "of 64, but I don't know which region. Browse each of the four "
        "regions' Round of 64 pages, find the (4) vs (13) matchup where "
        "the 13-seed won, and report the 13-seed's name and its region.")
    mens_tasks.append(
        "I want to look up the Cinderella story from the 2024 NCAA Men's "
        "Tournament — a double-digit seed that reached the Elite Eight. "
        "Browse the four regions' Elite Eight matchups on ESPN's bracket "
        "and identify any team seeded 10 or worse that appeared in an "
        "Elite Eight game; report that team's name, seed, and region.")

    emit(records, 'ncaa_mens', mens_tasks)

    # ─── Theme 2: NCAA Women's bracket ───────────────────────────────────
    BRACKET_SLUG_W = 'ncaa-womens-2024'
    REGIONS_W = ['Albany 1', 'Portland 3']

    womens_tasks = []
    womens_tasks.append(
        "On ESPN's Bracket Center, open the 2024 NCAA Division I Women's "
        "Basketball Tournament bracket and report the named champion + "
        "runner-up at the top of the page.")
    womens_tasks.append(
        "On the 2024 NCAA Women's bracket on ESPN, report the venue and "
        "TV network listed at the top of the bracket page.")
    for region in REGIONS_W:
        womens_tasks.append(
            f"In the {region} region of ESPN's 2024 NCAA Women's bracket, "
            "report which team is the 1-seed and that team's regular-"
            "season record.")
        womens_tasks.append(
            f"Open the {region} region on ESPN's 2024 NCAA Women's "
            "bracket. Report the head coach of the 3-seed.")
        womens_tasks.append(
            f"In the {region} region of ESPN's 2024 NCAA Women's "
            "bracket's Round of 64, click into the (1) vs (16) matchup "
            "and report the leading scorer name and points.")
    womens_tasks.append(
        "On ESPN's 2024 NCAA Women's bracket, open the Albany 1 region "
        "Sweet 16 page and report all matchups listed (team a vs team b "
        "+ winner for each).")
    womens_tasks.append(
        "On the 2024 NCAA Women's bracket on ESPN, open South Carolina's "
        "seed-profile page from the Albany 1 region. Report the number "
        "of games on South Carolina's tournament path list.")

    # Disambiguation
    womens_tasks.append(
        "I'm looking for a women's NCAA program coached by Dawn Staley "
        "in the 2024 bracket — but there are 16 teams per region on "
        "ESPN's bracket. Open the Albany 1 region's seed table, find the "
        "row whose coach is Dawn Staley, and report that team's seed + "
        "conference + record.")

    emit(records, 'ncaa_womens', womens_tasks)

    # ─── Theme 3: NBA Play-In ────────────────────────────────────────────
    play_in_tasks = []
    play_in_tasks.append(
        "On ESPN, open the NBA Play-In Tournament 2024 page from the "
        "Bracket Center. Report how many games are listed in the Eastern "
        "Conference section and how many in the Western Conference "
        "section.")
    play_in_tasks.append(
        "On ESPN's NBA Play-In Tournament 2024 page, click into the "
        "Eastern Conference 7v8 game (Philadelphia 76ers vs Miami Heat). "
        "Report the leading scorer name and points listed on the detail "
        "page.")
    play_in_tasks.append(
        "Open the Western Conference 7v8 Play-In game on ESPN (Pelicans "
        "vs Lakers). Report the final score and which team won.")
    play_in_tasks.append(
        "On ESPN's NBA Play-In Tournament page, open the Eastern "
        "Conference 9v10 game (Chicago Bulls vs Atlanta Hawks). Report "
        "the venue and the leading scorer name + points.")
    play_in_tasks.append(
        "On ESPN, browse to the NBA Play-In Tournament 2024 Eastern "
        "Conference 'eighth-final' game (loser of 7v8 vs winner of 9v10). "
        "Report which team won and the final score.")
    play_in_tasks.append(
        "On ESPN's NBA Play-In 2024 page, browse the Western Conference "
        "'eighth-final' game. Report the winner, the leading scorer's "
        "name, and the venue.")

    # Multi-step
    play_in_tasks.append(
        "On ESPN's NBA Play-In Tournament 2024 page, open every Eastern "
        "Conference game and add up Tyrese Maxey's and Jimmy Butler's "
        "leading-scorer point totals across the Eastern games. Report "
        "that combined total.")
    play_in_tasks.append(
        "On ESPN's NBA Play-In Tournament page, open both 9v10 games "
        "(Eastern and Western) and report which 9v10 winner advanced to "
        "play in the eighth-final game in their conference (compare the "
        "9v10 game winners to the eighth-final team rosters).")

    # Disambiguation
    play_in_tasks.append(
        "I want to look up the 2024 NBA Play-In game where the Bulls "
        "lost a heartbreaker — but the Bulls actually won their 9v10 "
        "game. Browse ESPN's Eastern Conference Play-In games and report "
        "which game the Chicago Bulls played in last (and lost), "
        "including the score and the team that eliminated them.")

    emit(records, 'play_in', play_in_tasks)

    # ─── Theme 4: NHL Playoffs ───────────────────────────────────────────
    nhl_tasks = []
    nhl_tasks.append(
        "On ESPN, open the NHL Stanley Cup Playoffs 2024 page from the "
        "Bracket Center. Report which teams played in the Eastern "
        "Conference Final and the series result.")
    nhl_tasks.append(
        "On the NHL 2024 Stanley Cup Playoffs page on ESPN, report all "
        "four matchups listed under Round 1 of the Eastern Conference "
        "(team a vs team b, plus winner).")
    nhl_tasks.append(
        "Open ESPN's NHL 2024 Stanley Cup Playoffs page. Under the "
        "Western Conference, list every Round 1 series and report which "
        "team won each.")
    nhl_tasks.append(
        "On ESPN's NHL 2024 Stanley Cup Playoffs page, click into the "
        "Eastern Conference Final series. Report the series result "
        "(wins-wins) and the start date listed.")
    nhl_tasks.append(
        "On ESPN's NHL 2024 Stanley Cup Playoffs, click into the Western "
        "Conference Final series. Report which team won and the series "
        "result (wins-wins).")
    nhl_tasks.append(
        "On ESPN's NHL 2024 Stanley Cup Playoffs page, browse the Second "
        "Round series in the Eastern Conference. Report every matchup "
        "(team a vs team b + winner).")
    nhl_tasks.append(
        "On ESPN's NHL 2024 Stanley Cup Playoffs page, open the Round 1 "
        "Western Conference 1v8 series (Dallas Stars vs Nashville "
        "Predators). Report the seeding and series-result row shown on "
        "the series detail page.")

    # Multi-step / cross-round
    nhl_tasks.append(
        "On ESPN's NHL 2024 Stanley Cup Playoffs page, trace the Florida "
        "Panthers' path: open their Round 1, Round 2, and Conference "
        "Final series detail pages in order, and report the series "
        "result for each round.")
    nhl_tasks.append(
        "On ESPN's NHL 2024 Stanley Cup Playoffs page, trace the "
        "Edmonton Oilers' path through Round 1, Round 2, and the Western "
        "Conference Final, reporting the series result for each round.")

    # Disambiguation
    nhl_tasks.append(
        "I want to look up an NHL 2024 playoff series — I remember it "
        "involved the New York Rangers in Round 2 — but I don't remember "
        "the opponent. Open ESPN's NHL 2024 Playoffs page, find the "
        "Eastern Conference Round 2 series that involved the Rangers (if "
        "any), and report the opponent and series result.")

    emit(records, 'nhl_playoffs', nhl_tasks)

    # ─── Theme 5: bracket_history cross-bracket ─────────────────────────
    history_tasks = []
    history_tasks.append(
        "On ESPN's Bracket Center, list every tournament/bracket "
        "available (men's, women's, NBA play-in, NHL playoffs) along "
        "with each one's year and the named champion (if shown).")
    history_tasks.append(
        "Across ESPN's NCAA Men's 2024 and NCAA Women's 2024 brackets, "
        "report which 1-seed in either tournament went on to be crowned "
        "champion. Open both bracket home pages on the Bracket Center "
        "and compare the named champion to each region's 1-seed.")
    history_tasks.append(
        "On ESPN's Bracket Center, open the NHL 2024 Playoffs and the "
        "NBA Play-In 2024 pages. Report whether any team appears in "
        "both surfaces' results pages (it shouldn't — sanity-check that "
        "the NBA and NHL brackets list disjoint franchises).")

    emit(records, 'history', history_tasks)

    # ─── Theme 6: round-level browse on women's bracket ─────────────────
    misc_tasks = []
    misc_tasks.append(
        "On ESPN's 2024 NCAA Women's bracket, open the Round of 32 page "
        "and report all matchups listed in the Portland 3 region.")
    misc_tasks.append(
        "On ESPN's 2024 NCAA Women's bracket, open the Elite Eight round "
        "page and report the matchup listed in the Albany 1 region "
        "(both teams + score + winner).")
    misc_tasks.append(
        "On ESPN's 2024 NCAA Men's bracket, open the Elite Eight round "
        "page. Report which region had the higher combined score (sum "
        "score_a + score_b) in that round.")
    misc_tasks.append(
        "On ESPN's 2024 NCAA Men's bracket, open the Sweet 16 round "
        "page. Identify which Sweet 16 matchup had the largest margin "
        "of victory (score difference) and report it.")
    misc_tasks.append(
        "Open the 2024 NCAA Men's bracket South region on ESPN. Browse "
        "the seed table and report the average regular-season record of "
        "the bottom four seeds (13, 14, 15, 16). Just report each "
        "record listed; no need to compute a numeric average.")
    misc_tasks.append(
        "On ESPN's 2024 NCAA Men's bracket West region, click into the "
        "(5) vs (12) Round of 64 matchup. Report the leading scorer "
        "name, the score, and which team won.")
    misc_tasks.append(
        "On the 2024 NCAA Men's bracket on ESPN, click into the South "
        "region. Find any Sweet 16 game where the higher seed (lower "
        "number) lost, click into the matchup detail page, and report "
        "the result.")

    emit(records, 'round_browse', misc_tasks)

    # ─── Theme 7: seed_profile drilldown (men's) ────────────────────────
    # 16 seeds × 4 regions = 64 seeds in the men's bracket. We'll generate
    # one task for the prominent seeds.
    SEED_TASKS_M = [
        # (region, seed_num, team_name)
        ('East', 1, 'UConn'), ('East', 2, 'Iowa State'),
        ('East', 3, 'Illinois'), ('East', 4, 'Auburn'),
        ('East', 11, 'Duquesne'), ('East', 14, 'Morehead State'),
        ('West', 1, 'North Carolina'), ('West', 4, 'Alabama'),
        ('West', 11, 'New Mexico'), ('West', 13, 'Charleston'),
        ('South', 1, 'Houston'), ('South', 4, 'Duke'),
        ('South', 11, 'NC State'), ('South', 12, 'James Madison'),
        ('Midwest', 1, 'Purdue'), ('Midwest', 2, 'Tennessee'),
        ('Midwest', 3, 'Creighton'), ('Midwest', 11, 'Oregon'),
        ('Midwest', 12, 'McNeese'),
    ]
    seed_profile_tasks = []
    for region, num, team in SEED_TASKS_M:
        seed_profile_tasks.append(
            f"On ESPN's NCAA Men's 2024 bracket, open the {region} region "
            f"and click on {team} (the {num}-seed) to see its bracket "
            "profile page. Report the head coach's name shown on the "
            "profile.")
        seed_profile_tasks.append(
            f"On ESPN's NCAA Men's 2024 bracket {region} region, open "
            f"{team}'s seed profile page and report how many games "
            "({team} played in the tournament — i.e., the number of "
            "rows in the Tournament path list).")
    emit(records, 'seed_profile_m', seed_profile_tasks)

    # ─── Theme 8: round_drill — per-region round detail ────────────────
    round_drill = []
    for region in REGIONS_M:
        for round_num in (1, 2, 3):
            round_drill.append(
                f"On ESPN's NCAA Men's 2024 bracket {region} region, "
                f"open round {round_num}. Report every matchup listed in "
                "that round (both teams + winner for each).")
    # Round 1 individual slot results
    for region in REGIONS_M:
        for sa, sb in [(1, 16), (8, 9), (5, 12), (4, 13),
                        (6, 11), (3, 14), (7, 10), (2, 15)]:
            round_drill.append(
                f"On ESPN's NCAA Men's 2024 bracket, in the {region} "
                f"region's Round of 64, click into the ({sa}) vs ({sb}) "
                "matchup. Report the score, the winning team, and the "
                "leading scorer with their points.")
    emit(records, 'round_drill_m', round_drill)

    # ─── Theme 9: NCAA Women's per-region drill ────────────────────────
    womens_drill = []
    for region in REGIONS_W:
        for round_num in (1, 2, 3):
            womens_drill.append(
                f"On ESPN's NCAA Women's 2024 bracket {region} region, "
                f"open round {round_num} and report every matchup listed "
                "(both teams + winner for each).")
        for sa, sb in [(1, 16), (8, 9), (5, 12), (4, 13)]:
            womens_drill.append(
                f"On ESPN's NCAA Women's 2024 bracket {region} region "
                f"Round of 64, click into the ({sa}) vs ({sb}) matchup "
                "and report the score, winner, and the leading scorer.")
    emit(records, 'ncaaw_drill', womens_drill)

    # ─── Theme 10: NHL series detail drill ─────────────────────────────
    nhl_drill = []
    NHL_R1 = [(1, 8), (2, 7), (3, 6), (4, 5)]
    for conf in ('east', 'west'):
        for sa, sb in NHL_R1:
            nhl_drill.append(
                "On ESPN's NHL 2024 Stanley Cup Playoffs, click into "
                f"the {conf.upper()} Round 1 ({sa}) vs ({sb}) series. "
                "Report the series winner, the series-result (wins-wins), "
                "and the start date listed.")
    for conf in ('east', 'west'):
        for slot in (0, 1):
            nhl_drill.append(
                "On ESPN's NHL 2024 Stanley Cup Playoffs, open the "
                f"{conf.upper()} Round 2 series at slot {slot} (the "
                f"{'first' if slot == 0 else 'second'} matchup listed). "
                "Report which two teams played and the winner.")
        nhl_drill.append(
            "On ESPN's NHL 2024 Stanley Cup Playoffs, open the "
            f"{conf.upper()} Conference Final series detail page. Report "
            "the start date and the wins-wins series result.")
    emit(records, 'nhl_drill', nhl_drill)

    # ─── Theme 11: play-in detail tasks ────────────────────────────────
    play_in_drill = []
    play_in_slugs = [
        ('east', '7v8', 'Philadelphia 76ers', 'Miami Heat'),
        ('east', '9v10', 'Chicago Bulls', 'Atlanta Hawks'),
        ('east', 'eighth-final', 'Miami Heat', 'Chicago Bulls'),
        ('west', '7v8', 'New Orleans Pelicans', 'Los Angeles Lakers'),
        ('west', '9v10', 'Sacramento Kings', 'Golden State Warriors'),
        ('west', 'eighth-final', 'New Orleans Pelicans', 'Sacramento Kings'),
    ]
    for conf, mtype, ta, tb in play_in_slugs:
        play_in_drill.append(
            "On ESPN's NBA Play-In Tournament 2024 page, click into the "
            f"{conf.upper()} Conference {mtype} game ({ta} vs {tb}). "
            "Report the venue, leading scorer, and final score.")
    emit(records, 'play_in_drill', play_in_drill)

    # ─── Theme 12: bracket-wide aggregates ─────────────────────────────
    aggregate_tasks = []
    aggregate_tasks.append(
        "On ESPN's 2024 NCAA Men's bracket, browse each of the four "
        "regions' Round of 64 results pages. Identify the matchup with "
        "the largest margin of victory across the entire opening round "
        "and report the matchup + the score.")
    aggregate_tasks.append(
        "On ESPN's 2024 NCAA Men's bracket, browse each region's Sweet "
        "16 page. Identify which Sweet 16 matchup had the highest total "
        "score (score_a + score_b) and report it.")
    aggregate_tasks.append(
        "On ESPN's NHL 2024 Stanley Cup Playoffs, browse every Round 1 "
        "series in both conferences (8 series total). Count how many "
        "series were swept 4-0 and report that count along with which "
        "teams swept.")
    aggregate_tasks.append(
        "On ESPN's NHL 2024 Stanley Cup Playoffs, identify which Round 1 "
        "lower-seeded team (seed 5–8) won their series. Browse all 8 "
        "Round 1 series detail pages and report each upset.")
    aggregate_tasks.append(
        "On ESPN's 2024 NCAA Men's bracket Final Four round page, "
        "compute the total points scored across both Final Four games "
        "(sum every score_a and score_b in both matchups) and report it.")
    aggregate_tasks.append(
        "On ESPN's 2024 NCAA Men's bracket National Championship page, "
        "report the leading scorer's points. Then open the Final Four "
        "page and report the leading scorer's points in both Final Four "
        "games. Is the championship-game leading-scorer points total "
        "higher or lower than either Final Four leading-scorer total?")
    aggregate_tasks.append(
        "On ESPN's NBA Play-In Tournament 2024 page, add up the leading-"
        "scorer point totals across all six Play-In games (3 Eastern + 3 "
        "Western) and report that combined total.")
    aggregate_tasks.append(
        "On ESPN's 2024 NCAA Men's bracket East region, find the team "
        "with the lowest regular-season record listed in the seed table "
        "(highest losses count). Click into that team's seed profile "
        "page and report its head coach.")
    aggregate_tasks.append(
        "On ESPN's 2024 NCAA Men's bracket Midwest region, find the team "
        "with the best regular-season record (highest win total) in the "
        "seed table. Click into that team's profile and report the "
        "team's conference.")
    aggregate_tasks.append(
        "On ESPN's 2024 NCAA Men's bracket West region, browse the seed "
        "table and list every team whose record column shows '25 wins or "
        "more' (i.e., wins ≥ 25). Report each team name and its seed.")
    aggregate_tasks.append(
        "Browse all four regions of ESPN's 2024 NCAA Men's bracket. "
        "Identify which region's 8-seed advanced to the Round of 32 "
        "(by winning their 8 vs 9 Round of 64 game). Report each "
        "region's 8 vs 9 winner.")
    aggregate_tasks.append(
        "On ESPN's 2024 NCAA Men's bracket, open every region's Elite "
        "Eight page. Across the four Elite Eight games, report the "
        "average winning margin (just report each margin; no need to "
        "compute the literal arithmetic mean).")
    emit(records, 'aggregate', aggregate_tasks)

    # ─── Append ─────────────────────────────────────────────────────────
    with open(TASKS, 'a', encoding='utf-8') as f:
        for r in records:
            f.write(json.dumps(r) + '\n')

    print(f'R5 GUI tasks appended: {len(records)} new rows. '
          f'Total now: {len(existing) + len(records)}.')


if __name__ == '__main__':
    main()
