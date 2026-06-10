#!/usr/bin/env python3
"""Extend NBA players via ESPN site API (stats.nba.com blocked on this host).

Target: 202 -> 500+ players
Source: site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{id}/roster
Notes:
 - ESPN API doesn't need auth and is fast.
 - It exposes the current-season roster for each of 30 NBA teams.
 - Each roster has 15-19 players -> ~450 total active players, matches 500 target.
"""
import sqlite3
import urllib.request
import json
import re
import time

DB = '/home/v-haoqiwang/repos/WebHarbor/sites/nba/instance/nba.db'

UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'


def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    existing_slugs = {r[0] for r in cur.execute('SELECT slug FROM players').fetchall()}
    existing_names = {r[0] for r in cur.execute('SELECT name FROM players').fetchall()}
    before = cur.execute('SELECT COUNT(*) FROM players').fetchone()[0]
    print(f'before: {before} players')

    teams = cur.execute('SELECT id, abbreviation, slug, name FROM teams').fetchall()
    # Map ESPN team abbreviations to our team_ids
    team_by_abbr = {abbr: tid for tid, abbr, slug, name in teams}
    team_by_name = {name.lower(): tid for tid, abbr, slug, name in teams}
    print(f'  teams known: {len(teams)}')

    # Pull the list of all ESPN team IDs
    try:
        tdata = fetch('http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams')
    except Exception as e:
        print(f'FATAL: cannot fetch ESPN teams: {e}')
        return
    espn_teams = tdata['sports'][0]['leagues'][0]['teams']
    print(f'  ESPN teams: {len(espn_teams)}')

    added = 0
    for entry in espn_teams:
        et = entry['team']
        espn_team_id = et['id']
        abbr = et.get('abbreviation', '').upper()
        team_id = team_by_abbr.get(abbr)
        if team_id is None:
            # fuzzy by display name
            team_id = team_by_name.get(et.get('displayName', '').lower())
        if team_id is None:
            print(f'  warn: cannot map ESPN team {abbr} {et.get("displayName")}')
            team_id = 1
        try:
            roster = fetch(f'http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{espn_team_id}/roster')
        except Exception as e:
            print(f'  fail roster {abbr}: {e}')
            continue
        athletes = roster.get('athletes', [])
        team_added = 0
        for ath in athletes:
            name = ath.get('fullName') or ath.get('displayName') or ''
            if not name or name in existing_names:
                continue
            slug = slugify(name)
            if slug in existing_slugs:
                continue
            position = (ath.get('position') or {}).get('abbreviation', '') if isinstance(ath.get('position'), dict) else ''
            jersey = ath.get('jersey', '') or ''
            height = ath.get('displayHeight', '') or ''
            weight = int(ath.get('weight') or 0)
            age = int(ath.get('age') or 0)
            bp = ath.get('birthPlace') or {}
            country = (bp.get('country') or '')[:60]
            college = ((ath.get('college') or {}).get('name') or '')[:80]
            headshot = (ath.get('headshot') or {}).get('href', '') if isinstance(ath.get('headshot'), dict) else ''
            debut = ath.get('debutYear', '')
            bio = f"{name} (#{jersey}, {position}) plays for {et.get('displayName')}."
            if debut:
                bio += f' Debuted in the league in {debut}.'

            cur.execute('''INSERT INTO players (team_id, name, slug, position, jersey,
                                                height, weight, age, country, college,
                                                ppg, rpg, apg, spg, bpg, fg_pct, three_pct,
                                                bio, image)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (team_id, name, slug, position, str(jersey),
                         height, weight, age, country, college,
                         0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                         bio, headshot))
            existing_names.add(name)
            existing_slugs.add(slug)
            added += 1
            team_added += 1
        print(f'  {abbr}: +{team_added}')
        con.commit()
        time.sleep(0.4)

    after = cur.execute('SELECT COUNT(*) FROM players').fetchone()[0]
    print(f'after: {after} (+{added})')
    con.close()


if __name__ == '__main__':
    main()
