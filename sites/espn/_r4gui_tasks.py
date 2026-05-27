#!/usr/bin/env python3
"""Append R4 GUI Fantasy tasks to sites/espn/tasks.jsonl.

These tasks all use the new /r4/fantasy/* GUI surface (lineup builder,
waiver-wire window, trade analyzer, head-to-head matchup, plus drill-down
detail pages). All tasks are natural-language GUI instructions — no
API-mirror tasks, no URL-encoded parameter forms, no JSON parsing prompts.

Task IDs follow the format ESPN--r4_<theme>_<NN> per the round 4
benchmark convention.

Idempotent: re-running is a no-op once R4 GUI tasks are present.
"""
import json
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(HERE, 'tasks.jsonl')
DB = os.path.join(HERE, 'instance_seed', 'espn.db')

WEB = 'http://localhost:40014/'
UPSTREAM = 'https://www.espn.com/'


def load_existing():
    with open(TASKS, 'r', encoding='utf-8') as f:
        return [ln for ln in f if ln.strip()]


def has_r4gui_tasks(existing):
    return any('"ESPN--r4_' in ln for ln in existing)


def emit(records, theme, items):
    """Emit task records as dicts; ID = ESPN--r4_<theme>_<NN>."""
    for i, q in enumerate(items):
        tid = f'ESPN--r4_{theme}_{i:03d}'
        records.append({
            'web_name': 'ESPN', 'id': tid, 'ques': q,
            'web': WEB, 'upstream_url': UPSTREAM,
        })


def main():
    existing = load_existing()
    if has_r4gui_tasks(existing):
        print(f'R4 GUI tasks already present ({len(existing)} rows) — no-op.')
        return

    records = []

    # ─── Theme 1: lineup_builder ─────────────────────────────────────────
    # Mix of basic GUI walks + multi-step instructions.
    NFL_LEAGUES = ['Sunday Funday', 'Touchdown Titans', 'Gridiron Gladiators',
                    'Pigskin Prophets', 'End Zone Elite', 'Hail Mary Heroes',
                    'Red Zone Renegades', 'Fourth & Long',
                    'Field Goal Fanatics', 'Blitz Brigade',
                    'Pocket Passers', 'Two Minute Drill']
    NBA_LEAGUES = ['Hardwood Heroes', 'Hoop Dreams', 'Pick & Roll',
                    'Triple Double Club', 'Buzzer Beaters', 'Court Vision']
    MLB_LEAGUES = ['Bases Loaded', 'Grand Slam Society', 'Strikeout Kings',
                    'Diamond Dynasty', 'Bullpen Bandits']
    NFL_SLOTS = ['QB', 'RB1', 'RB2', 'WR1', 'WR2', 'TE', 'FLEX', 'DST', 'K']
    NBA_SLOTS = ['PG', 'SG', 'SF', 'PF', 'C', 'G', 'F', 'UTIL1', 'UTIL2']
    MLB_SLOTS = ['C', '1B', '2B', '3B', 'SS', 'OF1', 'OF2', 'OF3', 'SP1',
                  'SP2', 'RP']

    lineup_tasks = []
    # 2-3 step easy lineups
    for lg in NFL_LEAGUES:
        lineup_tasks.append(
            f"On ESPN Fantasy, open the {lg} league home page and from "
            "the standings click on the top-ranked team to view its starting "
            "lineup. Report the projected total points listed above the "
            "lineup table.")
        lineup_tasks.append(
            f"In the {lg} fantasy football league, open the team managed by "
            "Alice Johnson and report which player is currently slotted in "
            "the QB position for the current week.")
        lineup_tasks.append(
            f"In the {lg} fantasy football league, open Bob Chen's team's "
            "lineup builder, click the WR1 slot, and report this week's "
            "matchup opponent listed for that starter.")
    for lg in NBA_LEAGUES:
        lineup_tasks.append(
            f"Open the {lg} fantasy basketball league. From the standings, "
            "open the team in 1st place and report the player currently "
            "starting at point guard (PG) along with their projected points.")
        lineup_tasks.append(
            f"In the {lg} league, open Carol Davis's team and report the "
            "player listed in the C (center) slot together with their "
            "projected points for this week.")
    for lg in MLB_LEAGUES:
        lineup_tasks.append(
            f"On the {lg} fantasy baseball league page, open David Kim's "
            "team and list the three players currently starting in the "
            "OF1, OF2, and OF3 outfield slots.")
        lineup_tasks.append(
            f"From the {lg} standings, open the top team and report which "
            "two pitchers are starting in the SP1 and SP2 slots.")

    # Multi-step (4-6 steps): compute sums across multiple slots
    for lg in NFL_LEAGUES[:8]:
        lineup_tasks.append(
            f"On ESPN Fantasy, open the {lg} league, click into Alice "
            "Johnson's team's lineup builder, then click the RB1 and RB2 "
            "slot pages one after the other. Add up the projected points "
            "shown on each of those two slot detail pages and report the "
            "total.")
        lineup_tasks.append(
            f"In the {lg} league, open Bob Chen's team's lineup builder, "
            "find the FLEX slot, click it to see the slot detail page, "
            "and report (a) the current FLEX starter's name and (b) the "
            "name of the first alternative listed under 'Other eligible "
            "players'.")
    for lg in NBA_LEAGUES:
        lineup_tasks.append(
            f"On ESPN Fantasy, open the {lg} league standings, click the "
            "team in last place to view its lineup, then click the SF "
            "slot. Report the actual points scored so far by the current "
            "SF starter.")

    # 7+ steps: cross-team comparison
    for lg in NFL_LEAGUES[:5]:
        lineup_tasks.append(
            f"In the {lg} fantasy football league, compare Alice Johnson's "
            "team's QB and Bob Chen's team's QB this week. Open each team's "
            "lineup, click into both QB slots, and report which manager's "
            "QB has the higher projected points (and the difference).")

    # 3 disambiguation tasks (lineup theme): manager has multiple teams!
    lineup_tasks.append(
        "I want to set my lineup for this week on ESPN Fantasy, but I "
        "manage multiple teams across leagues — which fantasy team should "
        "I open if I'm specifically trying to start a kicker named Jake "
        "Moody? Find which of my teams currently has Jake Moody in the K "
        "slot.")
    lineup_tasks.append(
        "On ESPN Fantasy, Alice Johnson manages more than one fantasy "
        "football team. Browse the Sunday Funday and Touchdown Titans "
        "leagues, find Alice Johnson's team in each, and report which "
        "of those two teams has the higher projected total points for "
        "the current week.")
    lineup_tasks.append(
        "On ESPN Fantasy, Bob Chen has at least three NFL fantasy teams "
        "across different leagues. Compare the QB starter listed in each "
        "of his teams (open each lineup page) and report which league's "
        "Bob Chen team has Patrick Mahomes or Lamar Jackson in the QB "
        "slot — if neither, report the QB name in his Sunday Funday team.")

    emit(records, 'lineup', lineup_tasks)

    # ─── Theme 2: waiver_wire ────────────────────────────────────────────
    waiver_tasks = []
    for lg in NFL_LEAGUES + NBA_LEAGUES + MLB_LEAGUES:
        waiver_tasks.append(
            f"On ESPN Fantasy, open the {lg} league's Waiver Wire page "
            "and report how many waiver claims are currently in 'pending' "
            "status (count the rows where the Status column reads pending).")
        waiver_tasks.append(
            f"Open the {lg} league's Waiver Wire window and click the "
            "claim at the top of the priority list. Report the player "
            "being added and the player being dropped.")
        waiver_tasks.append(
            f"In the {lg} league's Waiver Wire, find any claim submitted "
            "by Alice Johnson, click into its detail page, and report the "
            "bid amount and whether the claim is pending, awarded, or "
            "failed.")

    # Multi-step: aggregate across all 12 NFL leagues
    waiver_tasks.append(
        "On ESPN Fantasy, browse every NFL fantasy league's Waiver Wire "
        "window (Sunday Funday, Touchdown Titans, ... Two Minute Drill). "
        "Count Alice Johnson's PENDING waiver claims across all those "
        "leagues and report the total count.")
    waiver_tasks.append(
        "On the Sunday Funday NFL fantasy league's Waiver Wire window, "
        "open every claim whose status is 'awarded', and report the "
        "highest bid amount among those awarded claims.")

    # 7+ steps
    waiver_tasks.append(
        "I want to know which fantasy NFL manager paid the most for a "
        "waiver pickup in the Sunday Funday league. Open the league's "
        "Waiver Wire window, click into every claim whose status is "
        "'awarded' to see its detail page, compare the bid amounts, and "
        "report the manager + player + bid amount.")

    # 3 disambiguation
    waiver_tasks.append(
        "I want to cancel my pending waiver claim on ESPN Fantasy, but "
        "I'm Alice Johnson and I have multiple pending claims across "
        "different leagues. Open the Waiver Wire window in each of "
        "Alice's NFL leagues and list every pending claim along with "
        "the league name so I can pick the right one.")
    waiver_tasks.append(
        "On ESPN Fantasy, Carol Davis has more than one pending waiver "
        "claim in the Hardwood Heroes NBA league — open the league's "
        "Waiver Wire window, find all of her claims, and report each "
        "claim's add player and drop player.")
    waiver_tasks.append(
        "I'm David Kim and I have several pending waiver claims; one of "
        "them is for an outfielder. Browse the Bases Loaded, Grand Slam "
        "Society, and Strikeout Kings MLB leagues' Waiver Wire windows, "
        "find every David Kim claim whose add-player position is OF (or "
        "any outfielder slot), and report the league and add player for "
        "each.")

    emit(records, 'waiver', waiver_tasks)

    # ─── Theme 3: trade_analyzer ─────────────────────────────────────────
    trade_tasks = []
    for lg in NFL_LEAGUES + NBA_LEAGUES + MLB_LEAGUES:
        trade_tasks.append(
            f"On ESPN Fantasy, open the {lg} league's Trade Analyzer page "
            "and report how many trades are currently in 'pending' status.")
        trade_tasks.append(
            f"Open the {lg} league's Trade Analyzer, click the first "
            "trade in the list, and on the swap detail page report which "
            "players Alice Johnson's team is sending in that trade.")
        trade_tasks.append(
            f"On the {lg} league's Trade Analyzer page, find any trade "
            "where Bob Chen is on the receiving side, click into the "
            "swap, and report the total value rating for each side "
            "(value out for both teams).")

    # Multi-step
    trade_tasks.append(
        "On ESPN Fantasy, open the Sunday Funday league's Trade Analyzer, "
        "click into Trade #1, and report (a) which team is rated higher "
        "in 'total value out', and (b) whether the analyzer note rates "
        "the trade as 'favorable' or 'risky'.")
    trade_tasks.append(
        "Across the Touchdown Titans, Gridiron Gladiators, and Pigskin "
        "Prophets NFL leagues, look at every pending trade between Alice "
        "Johnson and Bob Chen. Open each trade's detail page and report "
        "which league's trade has the largest difference between value_a "
        "and value_b.")

    # Disambiguation
    trade_tasks.append(
        "I want to accept a pending trade offer on ESPN Fantasy, but I "
        "have multiple pending trades. I'm Alice Johnson in the Sunday "
        "Funday NFL league. Open my Trade Analyzer in that league, find "
        "every pending trade I'm party to, and list each one's opposing "
        "manager and the players involved so I can pick which to accept.")

    emit(records, 'trade', trade_tasks)

    # ─── Theme 4: head_to_head matchup ─────────────────────────────────
    matchup_tasks = []
    for lg_id, lg in enumerate(NFL_LEAGUES + NBA_LEAGUES + MLB_LEAGUES, 1):
        matchup_tasks.append(
            f"On ESPN Fantasy, open the {lg} league home page and report "
            "the score of the first matchup card listed under 'Matchups' "
            "for the current week (both teams + both scores).")
        matchup_tasks.append(
            f"In the {lg} league, click into the first Week matchup card "
            "to see the head-to-head detail page, and report which team's "
            "QB / PG / SP1 (the top slot) scored more actual points.")

    # Multi-step
    matchup_tasks.append(
        "On ESPN Fantasy, open the Sunday Funday NFL league home page, "
        "click the matchup card where Alice Johnson's Phantom Hawks "
        "appear, and on the head-to-head page add up the actual points "
        "of Alice's RB1 and RB2 starters. Report that sum.")
    matchup_tasks.append(
        "In the Hardwood Heroes NBA league, open the matchup page that "
        "includes Carol Davis's team. Compare the actual points of "
        "Carol's center against the opposing team's center and report "
        "which scored more.")

    emit(records, 'matchup', matchup_tasks)

    # ─── Theme 5: roster_research ────────────────────────────────────────
    # Cross-page navigation: from lineup → player profile → matchup
    research_tasks = []
    research_tasks.append(
        "On ESPN Fantasy, open the Sunday Funday NFL league, click into "
        "Alice Johnson's team lineup, and from the lineup table click on "
        "the player listed in the WR1 slot to navigate to their full "
        "player profile. Report the player's name.")
    research_tasks.append(
        "In the Touchdown Titans NFL league, open Bob Chen's team lineup "
        "page, click the TE slot to see slot detail, then from the 'Other "
        "eligible players' section click the first alternative and report "
        "that player's listed position.")
    research_tasks.append(
        "On ESPN Fantasy, open the Pick & Roll NBA league, click into "
        "Carol Davis's team, click the SG slot, and report the projected "
        "and actual points shown for the current starter on the slot "
        "detail page.")
    research_tasks.append(
        "On the Bases Loaded MLB fantasy league page, open David Kim's "
        "team's lineup, click the SS slot's link, and report the matchup "
        "(opponent label) listed for the current starter.")
    research_tasks.append(
        "On ESPN Fantasy, browse to the Court Vision NBA league, find "
        "the team whose manager is Ethan Rivera (or the team listed in "
        "5th place if Ethan is not in this league), open that team's "
        "lineup, and report the player in the PG slot.")

    emit(records, 'research', research_tasks)

    # ─── Theme 6: standings_browse ──────────────────────────────────────
    standings_tasks = []
    standings_tasks.append(
        "On ESPN Fantasy, open the Sunday Funday NFL league home and "
        "report which team is currently in last place (i.e., bottom of "
        "the standings table) along with its manager's name.")
    standings_tasks.append(
        "Across all 12 NFL fantasy leagues on ESPN, find any league in "
        "which Alice Johnson's team is currently ranked 1st in the "
        "standings. Report the league name.")
    standings_tasks.append(
        "On ESPN Fantasy, open the Triple Double Club NBA league. List "
        "the top 3 teams in the standings by record (W-L), including "
        "the manager name and points-for for each.")
    standings_tasks.append(
        "Open the Diamond Dynasty MLB fantasy league standings. Identify "
        "the team with the highest 'PA' (points against) column value "
        "and report that team's name and manager.")
    standings_tasks.append(
        "On the Hail Mary Heroes NFL fantasy league home, report which "
        "team has the most waiver moves used (the Moves column).")
    standings_tasks.append(
        "On ESPN Fantasy, find which manager has more total wins across "
        "their teams in the Sunday Funday and Touchdown Titans NFL "
        "leagues combined: Alice Johnson, Bob Chen, Carol Davis, or "
        "David Kim. Open each league's standings, sum each manager's "
        "wins across both leagues, and report the leader.")

    emit(records, 'standings', standings_tasks)

    # ─── Append to tasks.jsonl ──────────────────────────────────────────
    with open(TASKS, 'a', encoding='utf-8') as f:
        for r in records:
            f.write(json.dumps(r) + '\n')

    print(f'R4 GUI tasks appended: {len(records)} new rows. '
          f'Total now: {len(existing) + len(records)}.')


if __name__ == '__main__':
    main()
