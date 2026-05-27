#!/usr/bin/env python3
"""Generate ESPN R6 GUI POST-driven natural-language tasks (≥60).

Each task corresponds to a /POST endpoint added in app.py — phrased as a
realistic ESPN fan instruction. We do NOT include any API path. All routes
go through GUI form pages.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'tasks.jsonl')
WEB = 'http://localhost:40014/'
UPSTREAM = 'https://www.espn.com/'

TASKS = [
    # ─── Fantasy lineup (3) ─────────────────────────────────────────────────
    ('post_001', "On ESPN Fantasy, open the lineup builder for the Phantom Hawks team in the Sunday Funday NFL league and save the starting lineup for the current week."),
    ('post_002', "In the Silver Reapers fantasy team's lineup, click into the FLEX slot and swap in a replacement player named Saquon Barkley, then confirm the swap."),
    ('post_003', "From the Touchdown Titans league, open the Thunder Stallions team and save a lineup that benches the K and DST slots only."),
    # ─── Fantasy waivers (4) ────────────────────────────────────────────────
    ('post_004', "Submit a waiver claim on ESPN Fantasy for the player with ID 12 in the Sunday Funday NFL league for the Phantom Hawks team, with a $15 bid."),
    ('post_005', "On ESPN Fantasy, claim player ID 25 in the Touchdown Titans league for the Silver Reapers team and submit a $7 waiver bid with no drop player."),
    ('post_006', "On ESPN Fantasy, drop player ID 30 from the Phantom Hawks roster in the Sunday Funday NFL league."),
    ('post_007', "Drop the player with ID 18 from the Thunder Stallions team in the Sunday Funday NFL league via the waiver wire drop form."),
    # ─── Fantasy trade lifecycle (4) ────────────────────────────────────────
    ('post_008', "On ESPN Fantasy, propose a trade in the Sunday Funday NFL league: from Phantom Hawks to Silver Reapers, sending 'Christian McCaffrey' and receiving 'Justin Jefferson'."),
    ('post_009', "Accept the existing fantasy trade with slug 'l1-tr1' on ESPN."),
    ('post_010', "Reject the existing fantasy trade with slug 'l1-tr2' on ESPN."),
    ('post_011', "Submit a counter offer to the existing fantasy trade 'l1-tr3' on ESPN, sending 'Travis Kelce' for 'Bijan Robinson' with a one-line note."),
    # ─── Fantasy league lifecycle (5) ────────────────────────────────────────
    ('post_012', "Create a new ESPN fantasy NFL league named 'WebHarbor Friday Night Lights' with 10 teams and PPR scoring."),
    ('post_013', "Create a new ESPN fantasy NBA league named 'Court Vision Cup' with 12 teams and Category scoring."),
    ('post_014', "Send a league invite for the Sunday Funday NFL league on ESPN to recipient 'fan@example.com' with a short personal note saying 'Join us!'."),
    ('post_015', "On ESPN Fantasy, join the public Touchdown Titans NFL league with a new team named 'WebHarbor Wolves' managed by 'Test Manager'."),
    ('post_016', "In the live draft room for the Sunday Funday NFL league on ESPN, make pick for the Phantom Hawks team selecting 'Saquon Barkley' (RB, NYG)."),
    # ─── Fantasy settings + team admin (4) ──────────────────────────────────
    ('post_017', "Update the Sunday Funday NFL league settings on ESPN to use Half-PPR scoring and set the current week to 15."),
    ('post_018', "On ESPN Fantasy, update the Touchdown Titans league settings: roster size 18, current week 16."),
    ('post_019', "Rename the Phantom Hawks fantasy team to 'Boston Phantom Hawks' on ESPN."),
    ('post_020', "Upload a new avatar for the Silver Reapers fantasy team on ESPN, choosing the 'trophy' preset."),
    # ─── Bracket picks (5) ──────────────────────────────────────────────────
    ('post_021', "On ESPN's 2024 NCAA Men's bracket, open matchup #1 and pick 'UConn Huskies' as the winner."),
    ('post_022', "On ESPN's 2024 NCAA Women's bracket, open matchup #50 and pick 'South Carolina Gamecocks' as the winner."),
    ('post_023', "Lock in your 2024 NCAA Men's champion as 'UConn Huskies' on ESPN's bracket champion-pick page."),
    ('post_024', "Submit and lock your full 2024 NCAA Men's bracket on ESPN."),
    ('post_025', "On ESPN, lock the tiebreaker score for your 2024 NCAA Men's bracket at 142 combined points."),
    # ─── Bracket pools (4) ──────────────────────────────────────────────────
    ('post_026', "Create a new ESPN bracket pool named 'WebHarbor Madness' tied to the NCAA Men's 2024 bracket with standard scoring."),
    ('post_027', "Create a new bracket pool named 'Office Champions' for the NCAA Women's 2024 bracket using seed-based scoring on ESPN."),
    ('post_028', "Join the existing ESPN bracket pool 'ncaa-mens-2024-bracket-pool-2024' with display name 'WebHarbor Guest' and the listed invite code."),
    ('post_029', "Send a bracket-pool invite from 'ncaa-mens-2024-bracket-pool-2024' to recipient 'colleague@example.com' on ESPN."),
    # ─── Article comments (4) ───────────────────────────────────────────────
    ('post_030', "Post a comment on the ESPN article 'Celtics eye best regular season in years' that reads 'Banner 18 incoming.'"),
    ('post_031', "Post a comment on the ESPN article 'LeBron James surpasses all-time scoring record' from name 'Test Fan' saying 'Greatest scorer of all time.'"),
    ('post_032', "Reply to comment #1 on ESPN with the text 'Totally agree — they are peaking at the right time.'"),
    ('post_033', "Upvote comment #5 on ESPN."),
    # ─── Comment community + follows (5) ────────────────────────────────────
    ('post_034', "Upvote comment #1 on ESPN."),
    ('post_035', "Reply to comment #3 on ESPN with the text 'Defense wins championships.'"),
    ('post_036', "Follow the NBA team Boston Celtics on ESPN."),
    ('post_037', "Follow the NBA team Los Angeles Lakers on ESPN."),
    ('post_038', "Follow the NBA player Jayson Tatum on ESPN."),
    # ─── Watchlist + alerts (5) ─────────────────────────────────────────────
    ('post_039', "Add the team 'boston-celtics' to your ESPN watchlist with label 'Boston Celtics'."),
    ('post_040', "Add the show 'sportscenter-with-scott-van-pelt' as a watchlist entry on ESPN labeled 'SVP Late Night'."),
    ('post_041', "Add the game with slug 'pacers-bucks-2024-04-09' to your ESPN watchlist labeled 'Pacers @ Bucks recap'."),
    ('post_042', "Subscribe to a live-game-start alert on ESPN for the team slug 'los-angeles-lakers' via push notification."),
    ('post_043', "Subscribe to overtime alerts on ESPN for the game slug 'celtics-warriors-2024-04-10' via email."),
    # ─── Polls (5) ──────────────────────────────────────────────────────────
    ('post_044', "Cast a vote in ESPN's NBA MVP poll (poll id 1) for 'Nikola Jokic'."),
    ('post_045', "Cast a vote in ESPN's NFL Rookie of the Year poll (poll id 2) for 'C.J. Stroud'."),
    ('post_046', "Cast a vote in ESPN's NCAA men's 2024 champion poll (poll id 4) for 'UConn Huskies'."),
    ('post_047', "Cast a vote in ESPN's 2024 Stanley Cup poll (poll id 5) for 'Florida Panthers'."),
    ('post_048', "Cast a vote in ESPN's 2024 UEFA Champions League poll (poll id 6) for 'Real Madrid'."),
    # ─── Mixed / additional fan paths (12+ for a total ≥60) ─────────────────
    ('post_049', "Follow the NBA player LeBron James on ESPN."),
    ('post_050', "Follow the NBA team Miami Heat on ESPN."),
    ('post_051', "Send a fantasy invite from the Touchdown Titans NFL league to 'guest@example.com' with the message 'You are on the clock.'"),
    ('post_052', "Send a fantasy invite from the Pigskin Prophets NFL league to 'pal@example.com' on ESPN."),
    ('post_053', "Join the Pigskin Prophets NFL league on ESPN with new team name 'WebHarbor Wildcards' managed by 'Sample Manager'."),
    ('post_054', "On ESPN's NCAA Men's 2024 bracket, pick matchup #10 with winner 'Houston Cougars'."),
    ('post_055', "On ESPN's NCAA Men's 2024 bracket, pick matchup #25 with winner 'Purdue Boilermakers'."),
    ('post_056', "Lock in your 2024 NCAA Women's champion as 'South Carolina Gamecocks' on ESPN."),
    ('post_057', "Submit and lock your full 2024 NCAA Women's bracket on ESPN."),
    ('post_058', "Join the existing bracket pool 'ncaa-womens-2024-bracket-pool-2024' on ESPN with display name 'WebHarbor Guest W'."),
    ('post_059', "Create a fantasy MLB league named 'Diamond Pros' with 10 teams and Roto scoring on ESPN."),
    ('post_060', "Rename the Thunder Stallions fantasy team to 'Detroit Thunder Stallions' on ESPN."),
    ('post_061', "Upload a new avatar for the Phantom Hawks fantasy team on ESPN, choosing the 'fire' preset."),
    ('post_062', "In the Sunday Funday NFL draft room on ESPN, make pick for Silver Reapers selecting 'Justin Jefferson' (WR, MIN)."),
    ('post_063', "Counter the trade with slug 'l2-tr1' on ESPN, sending 'Bijan Robinson' for 'Tyreek Hill' with a note 'fair value'."),
    ('post_064', "Accept the fantasy trade with slug 'l2-tr2' on ESPN."),
    ('post_065', "Reject the fantasy trade with slug 'l3-tr1' on ESPN."),
]


def main():
    new_rows = []
    for tid, ques in TASKS:
        new_rows.append({
            'web_name': 'ESPN',
            'id': f'ESPN--{tid}',
            'ques': ques,
            'web': WEB,
            'upstream_url': UPSTREAM,
        })
    # Append to tasks.jsonl, skip ids that already exist
    existing = set()
    if os.path.exists(OUT):
        with open(OUT) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                o = json.loads(line)
                existing.add(o.get('id'))
    appended = 0
    with open(OUT, 'a') as f:
        for r in new_rows:
            if r['id'] in existing:
                continue
            f.write(json.dumps(r) + '\n')
            appended += 1
    print(f'Appended {appended} R6 GUI POST tasks (skipped {len(new_rows)-appended} duplicates).')


if __name__ == '__main__':
    main()
