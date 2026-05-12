#!/usr/bin/env python3
"""Seed all ESPN mirror data for 44 WebVoyager tasks."""
import json
from datetime import datetime, timedelta


def seed_all(db, Conference, Division, Team, Player, PlayerStat, Game,
             GamePlayerStat, Article, Transaction, DepthChartEntry,
             PowerIndex, Recruit):
    """Seed all data. Caller must commit. Idempotent guard done by caller."""

    # ── Sports (already created by app.py seed_database) ────────────────────
    from app import Sport
    sport_objs = {}
    for s in Sport.query.all():
        sport_objs[s.slug] = s

    # ══════════════════════════════════════════════════════════════════════════
    # NBA
    # ══════════════════════════════════════════════════════════════════════════
    nba_east = Conference(sport_slug='nba', name='Eastern Conference', short_name='East')
    nba_west = Conference(sport_slug='nba', name='Western Conference', short_name='West')
    db.session.add_all([nba_east, nba_west])
    db.session.flush()

    nba_divs = {}
    for conf, divnames in [
        (nba_east, ['Atlantic', 'Central', 'Southeast']),
        (nba_west, ['Northwest', 'Pacific', 'Southwest']),
    ]:
        for dn in divnames:
            d = Division(conference_id=conf.id, sport_slug='nba', name=dn)
            db.session.add(d)
            nba_divs[dn] = d
    db.session.flush()

    # Helper: build NBA team
    def nba_team(name, city, slug, abbr, conf, div, wins, losses, rank,
                 color1='#1d428a', color2='#c8102e', streak='W1'):
        full = f"{city} {name}" if city else name
        t = Team(
            sport_slug='nba', name=name, city=city, full_name=full,
            slug=slug, abbreviation=abbr,
            conference_id=conf.id, division_id=div.id,
            wins=wins, losses=losses,
            win_pct=round(wins / (wins + losses), 3) if (wins + losses) else 0,
            standing_rank=rank,
            color_primary=color1, color_secondary=color2,
            streak=streak,
            home_record=f"{wins//2}-{losses//2}",
            away_record=f"{wins - wins//2}-{losses - losses//2}",
        )
        db.session.add(t)
        return t

    # Atlantic
    celtics  = nba_team('Celtics',       'Boston',       'boston-celtics',         'BOS', nba_east, nba_divs['Atlantic'], 64, 18, 1, '#007A33', '#BA9653')
    nets     = nba_team('Nets',          'Brooklyn',     'brooklyn-nets',           'BKN', nba_east, nba_divs['Atlantic'], 32, 50, 5, '#000000', '#FFFFFF')
    knicks   = nba_team('Knicks',        'New York',     'new-york-knicks',         'NYK', nba_east, nba_divs['Atlantic'], 50, 32, 2, '#006BB6', '#F58426')
    sixers   = nba_team('76ers',         'Philadelphia', 'philadelphia-76ers',      'PHI', nba_east, nba_divs['Atlantic'], 47, 35, 3, '#006BB6', '#ED174C')
    raptors  = nba_team('Raptors',       'Toronto',      'toronto-raptors',         'TOR', nba_east, nba_divs['Atlantic'], 25, 57, 4, '#CE1141', '#000000')
    # Central
    bulls    = nba_team('Bulls',         'Chicago',      'chicago-bulls',           'CHI', nba_east, nba_divs['Central'], 39, 43, 4, '#CE1141', '#000000')
    cavs     = nba_team('Cavaliers',     'Cleveland',    'cleveland-cavaliers',     'CLE', nba_east, nba_divs['Central'], 48, 34, 1, '#860038', '#FDBB30')
    pistons  = nba_team('Pistons',       'Detroit',      'detroit-pistons',         'DET', nba_east, nba_divs['Central'], 14, 68, 5, '#C8102E', '#1D42BA')
    pacers   = nba_team('Pacers',        'Indiana',      'indiana-pacers',          'IND', nba_east, nba_divs['Central'], 47, 35, 2, '#002D62', '#FDBB30')
    bucks    = nba_team('Bucks',         'Milwaukee',    'milwaukee-bucks',         'MIL', nba_east, nba_divs['Central'], 49, 33, 3, '#00471B', '#EEE1C6')
    # Southeast
    hawks    = nba_team('Hawks',         'Atlanta',      'atlanta-hawks',           'ATL', nba_east, nba_divs['Southeast'], 36, 46, 3, '#E03A3E', '#C1D32F')
    hornets  = nba_team('Hornets',       'Charlotte',    'charlotte-hornets',       'CHA', nba_east, nba_divs['Southeast'], 21, 61, 5, '#1D1160', '#00788C')
    heat     = nba_team('Heat',          'Miami',        'miami-heat',              'MIA', nba_east, nba_divs['Southeast'], 46, 36, 1, '#98002E', '#F9A01B')
    magic    = nba_team('Magic',         'Orlando',      'orlando-magic',           'ORL', nba_east, nba_divs['Southeast'], 47, 35, 2, '#0077C0', '#C4CED4')
    wizards  = nba_team('Wizards',       'Washington',   'washington-wizards',      'WAS', nba_east, nba_divs['Southeast'], 15, 67, 4, '#002B5C', '#E31837')
    # Northwest
    nuggets  = nba_team('Nuggets',       'Denver',       'denver-nuggets',          'DEN', nba_west, nba_divs['Northwest'], 57, 25, 1, '#0E2240', '#FEC524')
    wolves   = nba_team('Timberwolves',  'Minnesota',    'minnesota-timberwolves',  'MIN', nba_west, nba_divs['Northwest'], 56, 26, 2, '#0C2340', '#236192')
    thunder  = nba_team('Thunder',       'Oklahoma City','okc-thunder',             'OKC', nba_west, nba_divs['Northwest'], 57, 25, 1, '#007AC1', '#EF3B24')
    blazers  = nba_team('Trail Blazers', 'Portland',     'portland-trail-blazers',  'POR', nba_west, nba_divs['Northwest'], 21, 61, 5, '#E03A3E', '#000000')
    jazz     = nba_team('Jazz',          'Utah',         'utah-jazz',               'UTA', nba_west, nba_divs['Northwest'], 31, 51, 4, '#002B5C', '#00471B')
    # Pacific
    warriors = nba_team('Warriors',      'Golden State', 'golden-state-warriors',   'GSW', nba_west, nba_divs['Pacific'], 46, 36, 3, '#1D428A', '#FFC72C')
    clippers = nba_team('Clippers',      'LA',           'la-clippers',             'LAC', nba_west, nba_divs['Pacific'], 51, 31, 2, '#C8102E', '#1D428A')
    lakers   = nba_team('Lakers',        'Los Angeles',  'los-angeles-lakers',      'LAL', nba_west, nba_divs['Pacific'], 47, 35, 4, '#552583', '#FDB927')
    suns     = nba_team('Suns',          'Phoenix',      'phoenix-suns',            'PHX', nba_west, nba_divs['Pacific'], 49, 33, 1, '#1D1160', '#E56020')
    kings    = nba_team('Kings',         'Sacramento',   'sacramento-kings',        'SAC', nba_west, nba_divs['Pacific'], 46, 36, 5, '#5A2D81', '#63727A')
    # Southwest
    mavs     = nba_team('Mavericks',     'Dallas',       'dallas-mavericks',        'DAL', nba_west, nba_divs['Southwest'], 50, 32, 2, '#00538C', '#002F6C')
    rockets  = nba_team('Rockets',       'Houston',      'houston-rockets',         'HOU', nba_west, nba_divs['Southwest'], 41, 41, 4, '#CE1141', '#000000')
    grizzlies= nba_team('Grizzlies',     'Memphis',      'memphis-grizzlies',       'MEM', nba_west, nba_divs['Southwest'], 27, 55, 5, '#5D76A9', '#12173F')
    pelicans = nba_team('Pelicans',      'New Orleans',  'new-orleans-pelicans',    'NOP', nba_west, nba_divs['Southwest'], 49, 33, 3, '#0C2340', '#C8102E')
    spurs    = nba_team('Spurs',         'San Antonio',  'san-antonio-spurs',       'SAS', nba_west, nba_divs['Southwest'], 22, 60, 6, '#C4CED4', '#000000')
    db.session.flush()

    # ── NBA Players ───────────────────────────────────────────────────────────
    def player(name, slug, team, pos, jersey, ht, wt, age, sport='nba',
               salary=0.0, injury='', injury_desc='', college='', exp=0,
               nationality='USA', birth_date=''):
        fn = name.split()[0]
        ln = ' '.join(name.split()[1:])
        p = Player(
            name=name, slug=slug, team_id=team.id, sport_slug=sport,
            first_name=fn, last_name=ln, position=pos, jersey_number=jersey,
            height=ht, weight=wt, age=age, salary=salary,
            injury_status=injury, injury_description=injury_desc,
            college=college, experience=exp, nationality=nationality,
            birth_date=birth_date,
        )
        db.session.add(p)
        return p

    # Boston Celtics
    tatum    = player('Jayson Tatum',   'jayson-tatum',   celtics, 'SF', '0',  '6-8', 210, 26, salary=32600000, college='Duke', exp=7, birth_date='1998-03-03')
    jbrown   = player('Jaylen Brown',   'jaylen-brown',   celtics, 'SG', '7',  '6-6', 223, 27, salary=30400000, college='California', exp=8, birth_date='1996-10-24')
    horford  = player('Al Horford',     'al-horford',     celtics, 'C',  '42', '6-9', 240, 37, salary=26500000, college='Florida', exp=17, nationality='Dominican Republic', birth_date='1986-06-03')
    porzingis= player('Kristaps Porzingis', 'kristaps-porzingis', celtics, 'C', '8', '7-3', 240, 28, salary=36000000, college='', exp=9, nationality='Latvia', birth_date='1995-08-02')
    holiday  = player('Jrue Holiday',   'jrue-holiday',   celtics, 'PG', '4',  '6-4', 205, 33, salary=30400000, college='UCLA', exp=15, birth_date='1990-06-12')
    white_c  = player('Derrick White',  'derrick-white',  celtics, 'SG', '9',  '6-4', 190, 29, salary=22500000, college='Colorado', exp=7, birth_date='1994-07-02')
    payton   = player('Payton Pritchard','payton-pritchard',celtics,'PG','11', '6-1', 195, 26, salary=5500000, college='Oregon', exp=4, birth_date='1998-01-28')

    # Philadelphia 76ers
    embiid   = player('Joel Embiid',    'joel-embiid',    sixers, 'C',  '11', '7-0', 280, 29, salary=47600000, college='Kansas', exp=9, nationality='Cameroon', birth_date='1994-03-16', injury='OUT', injury_desc='Knee injury - left knee')
    maxey    = player('Tyrese Maxey',   'tyrese-maxey',   sixers, 'PG', '0',  '6-2', 200, 23, salary=13500000, college='Kentucky', exp=4, birth_date='2000-11-04')
    harris   = player('Tobias Harris',  'tobias-harris',  sixers, 'PF', '12', '6-8', 226, 31, salary=39270000, college='Tennessee', exp=13, birth_date='1992-07-15', injury='Day-to-Day', injury_desc='Ankle - right ankle soreness')
    harden   = player('James Harden',   'james-harden',   clippers, 'PG', '1', '6-5', 220, 34, salary=35600000, college='Arizona State', exp=16, birth_date='1989-08-26')

    # Los Angeles Lakers
    lebron   = player('LeBron James',   'lebron-james',   lakers, 'SF', '23', '6-9', 250, 39, salary=47600000, college='', exp=21, birth_date='1984-12-30')
    adavis   = player('Anthony Davis',  'anthony-davis',  lakers, 'PF', '3',  '6-10', 253, 30, salary=43200000, college='Kentucky', exp=12, birth_date='1993-03-11')
    reaves   = player('Austin Reaves',  'austin-reaves',  lakers, 'SG', '15', '6-5', 197, 25, salary=12000000, college='Arkansas', exp=3, birth_date='1998-05-29')
    russ     = player('D\'Angelo Russell','dangelo-russell', lakers, 'PG', '1', '6-4', 190, 28, salary=18000000, college='Ohio State', exp=9, birth_date='1996-02-23')

    # Denver Nuggets
    jokic    = player('Nikola Jokic',   'nikola-jokic',   nuggets, 'C',  '15', '6-11', 284, 28, salary=51400000, college='', exp=9, nationality='Serbia', birth_date='1995-02-19')
    murray   = player('Jamal Murray',   'jamal-murray',   nuggets, 'PG', '27', '6-4', 215, 27, salary=34000000, college='Kentucky', exp=8, nationality='Canada', birth_date='1997-02-23')
    mpj      = player('Michael Porter Jr.', 'michael-porter-jr', nuggets, 'SF', '1', '6-10', 218, 25, salary=30500000, college='Missouri', exp=6, birth_date='1998-06-29')

    # Milwaukee Bucks
    giannis  = player('Giannis Antetokounmpo', 'giannis-antetokounmpo', bucks, 'PF', '34', '6-11', 242, 29, salary=45600000, college='', exp=11, nationality='Greece', birth_date='1994-12-06')
    dame     = player('Damian Lillard',  'damian-lillard', bucks, 'PG', '0',  '6-2', 195, 33, salary=46000000, college='Weber State', exp=12, birth_date='1990-07-15')

    # Miami Heat
    butler   = player('Jimmy Butler',   'jimmy-butler',   heat, 'SF', '22', '6-7', 232, 34, salary=48700000, college='Marquette', exp=13, birth_date='1989-09-14')
    adebayo  = player('Bam Adebayo',    'bam-adebayo',    heat, 'C',  '13', '6-9', 255, 26, salary=34900000, college='Kentucky', exp=7, birth_date='1997-07-18')
    herro    = player('Tyler Herro',    'tyler-herro',    heat, 'SG', '14', '6-4', 195, 24, salary=32600000, college='Kentucky', exp=5, birth_date='2000-01-20')

    # New York Knicks
    brunson  = player('Jalen Brunson',  'jalen-brunson',  knicks, 'PG', '11', '6-1', 190, 27, salary=28000000, college='Villanova', exp=6, birth_date='1996-08-31')
    randle   = player('Julius Randle',  'julius-randle',  knicks, 'PF', '30', '6-8', 250, 29, salary=28900000, college='Kentucky', exp=10, birth_date='1994-11-29')
    hart     = player('Josh Hart',      'josh-hart',      knicks, 'SF', '3',  '6-5', 215, 29, salary=16000000, college='Villanova', exp=7, birth_date='1995-03-06')

    # Brooklyn Nets
    simmons  = player('Ben Simmons',    'ben-simmons',    nets, 'PF', '10', '6-10', 240, 27, salary=37900000, college='LSU', exp=7, nationality='Australia', birth_date='1996-07-20')
    mikal    = player('Mikal Bridges',  'mikal-bridges',  knicks, 'SF', '25', '6-6', 209, 27, salary=23200000, college='Villanova', exp=6, birth_date='1996-08-30')

    # Golden State Warriors
    curry    = player('Stephen Curry',  'stephen-curry',  warriors, 'PG', '30', '6-2', 185, 35, salary=51900000, college='Davidson', exp=15, birth_date='1988-03-14')
    klay     = player('Klay Thompson',  'klay-thompson',  warriors, 'SG', '11', '6-6', 215, 33, salary=43200000, college='Washington State', exp=13, birth_date='1990-02-08')
    draymond = player('Draymond Green', 'draymond-green', warriors, 'PF', '23', '6-6', 230, 33, salary=22300000, college='Michigan State', exp=12, birth_date='1990-03-04')

    # Dallas Mavericks
    luka     = player('Luka Doncic',    'luka-doncic',    mavs, 'PG', '77', '6-7', 230, 25, salary=43000000, college='', exp=6, nationality='Slovenia', birth_date='1999-02-28')
    irving   = player('Kyrie Irving',   'kyrie-irving',   mavs, 'PG', '2',  '6-2', 195, 31, salary=37000000, college='Duke', exp=13, birth_date='1992-03-23')

    # OKC Thunder
    sga      = player('Shai Gilgeous-Alexander', 'shai-gilgeous-alexander', thunder, 'PG', '2', '6-6', 180, 25, salary=34000000, college='Kentucky', exp=6, nationality='Canada', birth_date='1998-07-12')

    # Atlanta Hawks
    trae     = player('Trae Young',     'trae-young',     hawks, 'PG', '11', '6-1', 164, 25, salary=36000000, college='Oklahoma', exp=6, birth_date='1998-09-19')

    # Sacramento Kings
    sabonis  = player('Domantas Sabonis', 'domantas-sabonis', kings, 'C', '10', '6-11', 240, 27, salary=37500000, college='', exp=8, nationality='Lithuania', birth_date='1996-05-03')

    # New Orleans Pelicans
    zion     = player('Zion Williamson','zion-williamson',pelicans,'PF','1', '6-6', 284, 23, salary=34000000, college='Duke', exp=5, birth_date='2000-07-06')

    # Minnesota Timberwolves
    towns    = player('Karl-Anthony Towns', 'karl-anthony-towns', wolves, 'C', '32', '7-0', 248, 28, salary=36000000, college='Kentucky', exp=9, nationality='Dominican Republic', birth_date='1995-11-15')
    edwards  = player('Anthony Edwards', 'anthony-edwards-twolves', wolves, 'SG', '5', '6-4', 225, 22, salary=29000000, college='Georgia', exp=4, birth_date='2001-08-05')

    # Phoenix Suns
    beal     = player('Bradley Beal',   'bradley-beal',   suns, 'SG', '3',  '6-4', 207, 30, salary=46700000, college='Florida', exp=12, birth_date='1993-06-28')
    kevin_d  = player('Kevin Durant',   'kevin-durant',   suns, 'PF', '35', '6-10', 240, 35, salary=47600000, college='Texas', exp=17, birth_date='1988-09-29')

    # Indiana Pacers
    haliburton = player('Tyrese Haliburton', 'tyrese-haliburton', pacers, 'PG', '0', '6-5', 185, 24, salary=22000000, college='Iowa State', exp=4, birth_date='2000-02-29')

    # Cleveland Cavaliers
    mitchell = player('Donovan Mitchell', 'donovan-mitchell', cavs, 'SG', '45', '6-1', 215, 27, salary=35300000, college='Louisville', exp=7, birth_date='1996-09-07')
    mobley   = player('Evan Mobley',    'evan-mobley',    cavs, 'C',  '4',  '7-0', 228, 22, salary=7900000, college='USC', exp=3, birth_date='2001-06-18')

    # Chicago Bulls
    lavine   = player('Zach LaVine',    'zach-lavine',    bulls, 'SG', '8',  '6-5', 200, 29, salary=43900000, college='UCLA', exp=10, birth_date='1995-03-10')

    # Houston Rockets
    green_j  = player('Jalen Green',    'jalen-green',    rockets, 'SG', '4', '6-4', 185, 22, salary=10900000, college='', exp=3, birth_date='2002-02-09')

    db.session.flush()

    # ── NBA PlayerStats ───────────────────────────────────────────────────────
    def nba_stat(plyr, season, gp, ppg, rpg, apg, spg, bpg, fg, tp, ft, mpg,
                 stat_type='season', tot_pts=0, tot_reb=0, tot_ast=0, tot_g=0):
        s = PlayerStat(
            player_id=plyr.id, season=season, stat_type=stat_type,
            games_played=gp, games_started=gp,
            points_per_game=ppg, rebounds_per_game=rpg, assists_per_game=apg,
            steals_per_game=spg, blocks_per_game=bpg,
            fg_pct=fg, three_pt_pct=tp, ft_pct=ft, minutes_per_game=mpg,
            total_points=tot_pts, total_rebounds=tot_reb,
            total_assists=tot_ast, total_games=tot_g,
        )
        db.session.add(s)
        return s

    # LeBron career
    nba_stat(lebron, 'career', 1490, 27.2, 7.5, 7.3, 1.6, 0.8, .504, .345, .734, 37.9,
             stat_type='career', tot_pts=39800, tot_reb=11200, tot_ast=10900, tot_g=1490)
    nba_stat(lebron, '2023-24', 71, 25.7, 7.3, 8.3, 1.3, 0.6, .540, .410, .750, 35.3)

    nba_stat(tatum,   '2023-24', 74, 26.9, 8.1, 4.9, 1.0, 0.6, .475, .371, .850, 35.7)
    nba_stat(jbrown,  '2023-24', 70, 23.0, 5.5, 3.6, 1.2, 0.4, .492, .354, .726, 33.1)
    nba_stat(embiid,  '2023-24', 39, 34.7, 11.0, 5.6, 1.2, 1.7, .528, .375, .877, 34.6)
    nba_stat(maxey,   '2023-24', 70, 25.9, 3.7, 6.2, 1.0, 0.4, .476, .400, .866, 35.2)
    nba_stat(jokic,   '2023-24', 79, 26.4, 12.4, 9.0, 1.4, 0.9, .583, .359, .819, 34.6)
    nba_stat(murray,  '2023-24', 76, 21.2, 4.1, 6.5, 1.1, 0.4, .480, .392, .851, 34.6)
    nba_stat(giannis, '2023-24', 73, 30.4, 11.5, 6.5, 1.2, 1.1, .611, .274, .657, 35.2)
    nba_stat(dame,    '2023-24', 73, 24.3, 4.4, 7.4, 1.0, 0.3, .463, .401, .905, 35.8)
    nba_stat(butler,  '2023-24', 60, 20.8, 5.3, 5.0, 1.3, 0.5, .492, .267, .864, 33.7)
    nba_stat(adebayo, '2023-24', 71, 19.3, 10.4, 3.9, 1.2, 0.8, .521, .000, .765, 34.5)
    nba_stat(curry,   '2023-24', 74, 26.4, 4.5, 5.1, 0.9, 0.4, .450, .408, .921, 32.7)
    nba_stat(luka,    '2023-24', 70, 33.9, 9.2, 9.8, 1.4, 0.5, .487, .382, .786, 37.5)
    nba_stat(sga,     '2023-24', 75, 30.1, 5.5, 6.2, 2.0, 1.0, .535, .353, .874, 33.8)
    nba_stat(trae,    '2023-24', 58, 25.7, 2.9, 10.8, 1.3, 0.2, .424, .325, .877, 34.6)
    nba_stat(sabonis, '2023-24', 79, 19.9, 13.6, 8.0, 1.1, 0.5, .562, .283, .680, 34.8)
    nba_stat(adavis,  '2023-24', 76, 24.7, 12.6, 3.5, 1.2, 2.3, .558, .270, .794, 35.5)
    nba_stat(brunson, '2023-24', 77, 28.7, 3.6, 6.7, 0.9, 0.2, .479, .401, .845, 35.8)
    nba_stat(kevin_d, '2023-24', 75, 27.1, 6.6, 5.0, 0.8, 1.2, .523, .412, .857, 37.2)
    nba_stat(mitchell,'2023-24', 74, 26.6, 4.5, 5.1, 1.3, 0.3, .466, .382, .876, 35.4)
    nba_stat(haliburton,'2023-24',69, 20.1, 3.9, 10.9, 1.7, 0.8, .477, .404, .840, 32.9)
    nba_stat(towns,   '2023-24', 62, 21.4, 8.1, 3.0, 0.9, 1.6, .501, .405, .839, 32.1)
    nba_stat(edwards, '2023-24', 79, 25.9, 5.4, 5.1, 1.3, 0.5, .464, .357, .797, 36.6)
    nba_stat(zion,    '2023-24', 70, 22.9, 5.8, 5.0, 1.2, 0.7, .575, .238, .659, 31.6)
    nba_stat(lavine,  '2023-24', 25, 19.5, 4.5, 4.2, 0.9, 0.4, .470, .366, .840, 32.7)
    nba_stat(horford, '2023-24', 68, 10.2, 6.4, 2.9, 0.7, 1.1, .472, .385, .781, 27.3)
    nba_stat(porzingis,'2023-24',57, 20.1, 7.2, 2.0, 0.8, 1.9, .521, .379, .876, 29.4)
    nba_stat(holiday, '2023-24', 68, 12.5, 5.4, 4.8, 1.6, 0.5, .478, .388, .784, 31.2)
    nba_stat(harden,  '2023-24', 72, 16.6, 5.1, 8.5, 1.3, 0.6, .413, .373, .872, 34.8)
    db.session.flush()

    # ══════════════════════════════════════════════════════════════════════════
    # NFL
    # ══════════════════════════════════════════════════════════════════════════
    nfl_afc = Conference(sport_slug='nfl', name='AFC', short_name='AFC')
    nfl_nfc = Conference(sport_slug='nfl', name='NFC', short_name='NFC')
    db.session.add_all([nfl_afc, nfl_nfc])
    db.session.flush()

    nfl_divs = {}
    for conf, divnames in [
        (nfl_afc, ['AFC East', 'AFC North', 'AFC South', 'AFC West']),
        (nfl_nfc, ['NFC East', 'NFC North', 'NFC South', 'NFC West']),
    ]:
        for dn in divnames:
            d = Division(conference_id=conf.id, sport_slug='nfl', name=dn)
            db.session.add(d)
            nfl_divs[dn] = d
    db.session.flush()

    def nfl_team(name, city, slug, abbr, conf, div, wins, losses, rank, color1='#003087', color2='#C60C30'):
        full = f"{city} {name}" if city else name
        t = Team(
            sport_slug='nfl', name=name, city=city, full_name=full,
            slug=slug, abbreviation=abbr,
            conference_id=conf.id, division_id=div.id,
            wins=wins, losses=losses,
            win_pct=round(wins / (wins + losses + 0.0001), 3),
            standing_rank=rank,
            color_primary=color1, color_secondary=color2,
        )
        db.session.add(t)
        return t

    # AFC East
    bills      = nfl_team('Bills',      'Buffalo',       'buffalo-bills',      'BUF', nfl_afc, nfl_divs['AFC East'], 11, 6, 1, '#00338D', '#C60C30')
    dolphins   = nfl_team('Dolphins',   'Miami',         'miami-dolphins',     'MIA', nfl_afc, nfl_divs['AFC East'], 11, 6, 2, '#008E97', '#FC4C02')
    patriots   = nfl_team('Patriots',   'New England',   'new-england-patriots','NE', nfl_afc, nfl_divs['AFC East'], 4, 13, 4, '#002244', '#C60C30')
    jets       = nfl_team('Jets',       'New York',      'new-york-jets',      'NYJ', nfl_afc, nfl_divs['AFC East'], 7, 10, 3, '#125740', '#000000')
    # AFC North
    ravens     = nfl_team('Ravens',     'Baltimore',     'baltimore-ravens',   'BAL', nfl_afc, nfl_divs['AFC North'], 13, 4, 1, '#241773', '#9E7C0C')
    bengals    = nfl_team('Bengals',    'Cincinnati',    'cincinnati-bengals', 'CIN', nfl_afc, nfl_divs['AFC North'], 9, 8, 2, '#FB4F14', '#000000')
    browns     = nfl_team('Browns',     'Cleveland',     'cleveland-browns',   'CLE', nfl_afc, nfl_divs['AFC North'], 11, 6, 3, '#311D00', '#FF3C00')
    steelers   = nfl_team('Steelers',   'Pittsburgh',    'pittsburgh-steelers','PIT', nfl_afc, nfl_divs['AFC North'], 10, 7, 4, '#FFB612', '#101820')
    # AFC South
    texans     = nfl_team('Texans',     'Houston',       'houston-texans',     'HOU', nfl_afc, nfl_divs['AFC South'], 10, 7, 1, '#03202F', '#A71930')
    colts      = nfl_team('Colts',      'Indianapolis',  'indianapolis-colts', 'IND', nfl_afc, nfl_divs['AFC South'], 9, 8, 2, '#002C5F', '#A2AAAD')
    jaguars    = nfl_team('Jaguars',    'Jacksonville',  'jacksonville-jaguars','JAC', nfl_afc, nfl_divs['AFC South'], 9, 8, 3, '#006778', '#D7A22A')
    titans     = nfl_team('Titans',     'Tennessee',     'tennessee-titans',   'TEN', nfl_afc, nfl_divs['AFC South'], 6, 11, 4, '#0C2340', '#4B92DB')
    # AFC West
    chiefs     = nfl_team('Chiefs',     'Kansas City',   'kansas-city-chiefs', 'KC',  nfl_afc, nfl_divs['AFC West'], 11, 6, 1, '#E31837', '#FFB81C')
    raiders    = nfl_team('Raiders',    'Las Vegas',     'las-vegas-raiders',  'LV',  nfl_afc, nfl_divs['AFC West'], 8, 9, 2, '#000000', '#A5ACAF')
    chargers   = nfl_team('Chargers',   'Los Angeles',   'los-angeles-chargers','LAC', nfl_afc, nfl_divs['AFC West'], 5, 12, 4, '#0080C6', '#FFC20E')
    broncos    = nfl_team('Broncos',    'Denver',        'denver-broncos',     'DEN', nfl_afc, nfl_divs['AFC West'], 8, 9, 3, '#FB4F14', '#002244')
    # NFC East
    cowboys    = nfl_team('Cowboys',    'Dallas',        'dallas-cowboys',     'DAL', nfl_nfc, nfl_divs['NFC East'], 12, 5, 1, '#003594', '#041E42')
    giants     = nfl_team('Giants',     'New York',      'new-york-giants',    'NYG', nfl_nfc, nfl_divs['NFC East'], 6, 11, 3, '#0B2265', '#A71930')
    eagles     = nfl_team('Eagles',     'Philadelphia',  'philadelphia-eagles','PHI', nfl_nfc, nfl_divs['NFC East'], 11, 6, 2, '#004C54', '#A5ACAF')
    commanders = nfl_team('Commanders', 'Washington',    'washington-commanders','WAS',nfl_nfc, nfl_divs['NFC East'], 4, 13, 4, '#5A1414', '#FFB612')
    # NFC North
    bears      = nfl_team('Bears',      'Chicago',       'chicago-bears',      'CHI', nfl_nfc, nfl_divs['NFC North'], 7, 10, 3, '#C83803', '#0B162A')
    lions      = nfl_team('Lions',      'Detroit',       'detroit-lions',      'DET', nfl_nfc, nfl_divs['NFC North'], 12, 5, 1, '#0076B6', '#B0B7BC')
    packers    = nfl_team('Packers',    'Green Bay',     'green-bay-packers',  'GB',  nfl_nfc, nfl_divs['NFC North'], 9, 8, 2, '#203731', '#FFB612')
    vikings    = nfl_team('Vikings',    'Minnesota',     'minnesota-vikings',  'MIN', nfl_nfc, nfl_divs['NFC North'], 7, 10, 4, '#4F2683', '#FFC62F')
    # NFC South
    falcons    = nfl_team('Falcons',    'Atlanta',       'atlanta-falcons',    'ATL', nfl_nfc, nfl_divs['NFC South'], 7, 10, 2, '#A71930', '#000000')
    panthers   = nfl_team('Panthers',   'Carolina',      'carolina-panthers',  'CAR', nfl_nfc, nfl_divs['NFC South'], 2, 15, 4, '#0085CA', '#101820')
    saints     = nfl_team('Saints',     'New Orleans',   'new-orleans-saints', 'NO',  nfl_nfc, nfl_divs['NFC South'], 9, 8, 1, '#D3BC8D', '#101820')
    buccaneers = nfl_team('Buccaneers', 'Tampa Bay',     'tampa-bay-buccaneers','TB', nfl_nfc, nfl_divs['NFC South'], 9, 8, 3, '#D50A0A', '#FF7900')
    # NFC West
    cardinals  = nfl_team('Cardinals',  'Arizona',       'arizona-cardinals',  'ARI', nfl_nfc, nfl_divs['NFC West'], 4, 13, 4, '#97233F', '#000000')
    rams       = nfl_team('Rams',       'Los Angeles',   'los-angeles-rams',   'LAR', nfl_nfc, nfl_divs['NFC West'], 10, 7, 2, '#003594', '#FFA300')
    nfl_sf     = nfl_team('49ers',      'San Francisco', 'san-francisco-49ers','SF',  nfl_nfc, nfl_divs['NFC West'], 12, 5, 1, '#AA0000', '#B3995D')
    seahawks   = nfl_team('Seahawks',   'Seattle',       'seattle-seahawks',   'SEA', nfl_nfc, nfl_divs['NFC West'], 9, 8, 3, '#002244', '#69BE28')
    db.session.flush()

    # NFL Key Players
    rodgers   = player('Aaron Rodgers',    'aaron-rodgers',    jets,    'QB', '8',  '6-2', 212, 40, sport='nfl', salary=35000000, college='California', exp=19, birth_date='1983-12-02')
    z_wilson  = player('Zach Wilson',      'zach-wilson',      jets,    'QB', '2',  '6-2', 214, 25, sport='nfl', salary=3600000, college='BYU', exp=3, birth_date='1999-08-02', injury='Out', injury_desc='Knee - right knee')
    garret_w  = player('Garrett Wilson',   'garrett-wilson-jets', jets, 'WR', '17', '6-0', 192, 24, sport='nfl', salary=4300000, college='Ohio State', exp=2, birth_date='2000-03-05')
    breece_h  = player('Breece Hall',      'breece-hall',      jets,    'RB', '20', '6-1', 220, 22, sport='nfl', salary=1100000, college='Iowa State', exp=2, birth_date='2001-07-08')
    mahomes   = player('Patrick Mahomes',  'patrick-mahomes',  chiefs,  'QB', '15', '6-2', 227, 28, sport='nfl', salary=45000000, college='Texas Tech', exp=7, birth_date='1995-09-17')
    lamar     = player('Lamar Jackson',    'lamar-jackson',    ravens,  'QB', '8',  '6-2', 212, 27, sport='nfl', salary=52000000, college='Louisville', exp=6, birth_date='1997-01-07')
    jalen_h   = player('Jalen Hurts',      'jalen-hurts',      eagles,  'QB', '1',  '6-1', 222, 25, sport='nfl', salary=51000000, college='Oklahoma', exp=4, birth_date='1998-08-07')
    db.session.flush()

    # Jets Depth Chart
    dce = [
        DepthChartEntry(team_id=jets.id, position='QB', position_rank=1, player_id=rodgers.id, injury_notes=''),
        DepthChartEntry(team_id=jets.id, position='QB', position_rank=2, player_id=z_wilson.id, injury_notes='Injured - Out'),
        DepthChartEntry(team_id=jets.id, position='WR', position_rank=1, player_id=garret_w.id, injury_notes=''),
        DepthChartEntry(team_id=jets.id, position='RB', position_rank=1, player_id=breece_h.id, injury_notes=''),
    ]
    for d in dce:
        db.session.add(d)
    db.session.flush()

    # ══════════════════════════════════════════════════════════════════════════
    # NHL
    # ══════════════════════════════════════════════════════════════════════════
    nhl_east = Conference(sport_slug='nhl', name='Eastern Conference', short_name='East')
    nhl_west = Conference(sport_slug='nhl', name='Western Conference', short_name='West')
    db.session.add_all([nhl_east, nhl_west])
    db.session.flush()

    nhl_divs = {}
    for conf, divnames in [
        (nhl_east, ['Atlantic', 'Metropolitan']),
        (nhl_west, ['Central', 'Pacific']),
    ]:
        for dn in divnames:
            d = Division(conference_id=conf.id, sport_slug='nhl', name=dn)
            db.session.add(d)
            nhl_divs[dn] = d
    db.session.flush()

    def nhl_team(name, city, slug, abbr, conf, div, wins, losses, otl, rank, color1='#003087', color2='#FFFFFF'):
        full = f"{city} {name}" if city else name
        t = Team(
            sport_slug='nhl', name=name, city=city, full_name=full,
            slug=slug, abbreviation=abbr,
            conference_id=conf.id, division_id=div.id,
            wins=wins, losses=losses, overtime_losses=otl,
            win_pct=round(wins / (wins + losses + otl + 0.0001), 3),
            standing_rank=rank,
            color_primary=color1, color_secondary=color2,
        )
        db.session.add(t)
        return t

    # Atlantic
    bruins   = nhl_team('Bruins',       'Boston',       'boston-bruins',        'BOS', nhl_east, nhl_divs['Atlantic'],  47, 20, 15, 1, '#FFB81C', '#000000')
    sabres   = nhl_team('Sabres',       'Buffalo',      'buffalo-sabres',       'BUF', nhl_east, nhl_divs['Atlantic'],  39, 37,  6, 5, '#003E7E', '#FCB514')
    redwings = nhl_team('Red Wings',    'Detroit',      'detroit-red-wings',    'DET', nhl_east, nhl_divs['Atlantic'],  34, 32, 16, 6, '#CE1126', '#FFFFFF')
    panthers = nhl_team('Panthers',     'Florida',      'florida-panthers',     'FLA', nhl_east, nhl_divs['Atlantic'],  52, 24,  6, 2, '#041E42', '#C8102E')
    canadiens= nhl_team('Canadiens',    'Montreal',     'montreal-canadiens',   'MTL', nhl_east, nhl_divs['Atlantic'],  30, 36, 16, 7, '#AF1E2D', '#192168')
    senators = nhl_team('Senators',     'Ottawa',       'ottawa-senators',      'OTT', nhl_east, nhl_divs['Atlantic'],  37, 41,  4, 8, '#C52032', '#000000')
    lightning= nhl_team('Lightning',    'Tampa Bay',    'tampa-bay-lightning',  'TBL', nhl_east, nhl_divs['Atlantic'],  45, 29,  8, 3, '#002868', '#FFFFFF')
    leafs    = nhl_team('Maple Leafs',  'Toronto',      'toronto-maple-leafs',  'TOR', nhl_east, nhl_divs['Atlantic'],  46, 26, 10, 4, '#003E7E', '#FFFFFF')
    # Metropolitan
    canes    = nhl_team('Hurricanes',   'Carolina',     'carolina-hurricanes',  'CAR', nhl_east, nhl_divs['Metropolitan'], 52, 23,  7, 1, '#CC0000', '#000000')
    jackets  = nhl_team('Blue Jackets', 'Columbus',     'columbus-blue-jackets','CBJ', nhl_east, nhl_divs['Metropolitan'], 27, 45, 10, 7, '#002654', '#CE1126')
    devils   = nhl_team('Devils',       'New Jersey',   'new-jersey-devils',    'NJD', nhl_east, nhl_divs['Metropolitan'], 52, 22,  8, 2, '#CE1126', '#000000')
    islanders= nhl_team('Islanders',    'New York',     'new-york-islanders',   'NYI', nhl_east, nhl_divs['Metropolitan'], 39, 27, 16, 5, '#003087', '#FC4C02')
    rangers  = nhl_team('Rangers',      'New York',     'new-york-rangers',     'NYR', nhl_east, nhl_divs['Metropolitan'], 55, 23,  4, 3, '#0038A8', '#CE1126')
    flyers   = nhl_team('Flyers',       'Philadelphia', 'philadelphia-flyers',  'PHI', nhl_east, nhl_divs['Metropolitan'], 33, 38, 11, 6, '#F74902', '#000000')
    penguins = nhl_team('Penguins',     'Pittsburgh',   'pittsburgh-penguins',  'PIT', nhl_east, nhl_divs['Metropolitan'], 38, 33, 11, 4, '#FCB514', '#000000')
    capitals = nhl_team('Capitals',     'Washington',   'washington-capitals',  'WSH', nhl_east, nhl_divs['Metropolitan'], 40, 31, 11, 8, '#041E42', '#C8102E')
    # Central
    predators= nhl_team('Predators',    'Nashville',    'nashville-predators',  'NSH', nhl_west, nhl_divs['Central'],  32, 35, 15, 7, '#FFB81C', '#041E42')
    blues    = nhl_team('Blues',        'St. Louis',    'st-louis-blues',       'STL', nhl_west, nhl_divs['Central'],  44, 30,  8, 4, '#002F87', '#FCB514')
    stars    = nhl_team('Stars',        'Dallas',       'dallas-stars',         'DAL', nhl_west, nhl_divs['Central'],  52, 21,  9, 1, '#006847', '#8F8F8C')
    wild     = nhl_team('Wild',         'Minnesota',    'minnesota-wild',       'MIN', nhl_west, nhl_divs['Central'],  39, 31, 12, 5, '#154734', '#A6192E')
    avs      = nhl_team('Avalanche',    'Colorado',     'colorado-avalanche',   'COL', nhl_west, nhl_divs['Central'],  50, 25,  7, 2, '#6F263D', '#236192')
    jets_nhl = nhl_team('Jets',         'Winnipeg',     'winnipeg-jets',        'WPG', nhl_west, nhl_divs['Central'],  52, 24,  6, 3, '#041E42', '#004C97')
    blackhawks=nhl_team('Blackhawks',   'Chicago',      'chicago-blackhawks',   'CHI', nhl_west, nhl_divs['Central'],  23, 53,  6, 8, '#CF0A2C', '#000000')
    coyotes  = nhl_team('Coyotes',      'Arizona',      'arizona-coyotes',      'ARI', nhl_west, nhl_divs['Central'],  36, 41,  5, 6, '#8C2633', '#E2D6B5')
    # Pacific
    kings    = nhl_team('Kings',        'Los Angeles',  'los-angeles-kings',    'LAK', nhl_west, nhl_divs['Pacific'],  44, 27, 11, 3, '#111111', '#A2AAAD')
    ducks    = nhl_team('Ducks',        'Anaheim',      'anaheim-ducks',        'ANA', nhl_west, nhl_divs['Pacific'],  27, 50,  5, 8, '#F47A38', '#B9975B')
    sharks   = nhl_team('Sharks',       'San Jose',     'san-jose-sharks',      'SJS', nhl_west, nhl_divs['Pacific'],  19, 54,  9, 7, '#006D75', '#EA7200')
    flames   = nhl_team('Flames',       'Calgary',      'calgary-flames',       'CGY', nhl_west, nhl_divs['Pacific'],  38, 27, 17, 4, '#C8102E', '#F1BE48')
    oilers   = nhl_team('Oilers',       'Edmonton',     'edmonton-oilers',      'EDM', nhl_west, nhl_divs['Pacific'],  49, 27,  6, 2, '#041E42', '#FF4C00')
    canucks  = nhl_team('Canucks',      'Vancouver',    'vancouver-canucks',    'VAN', nhl_west, nhl_divs['Pacific'],  50, 23,  9, 5, '#00205B', '#00843D')
    kraken   = nhl_team('Kraken',       'Seattle',      'seattle-kraken',       'SEA', nhl_west, nhl_divs['Pacific'],  46, 28,  8, 6, '#001628', '#99D9D9')
    golden_k = nhl_team('Golden Knights','Vegas',       'vegas-golden-knights', 'VGK', nhl_west, nhl_divs['Pacific'],  45, 29,  8, 1, '#B4975A', '#333F48')
    db.session.flush()

    # ══════════════════════════════════════════════════════════════════════════
    # MLB
    # ══════════════════════════════════════════════════════════════════════════
    mlb_al = Conference(sport_slug='mlb', name='American League', short_name='AL')
    mlb_nl = Conference(sport_slug='mlb', name='National League', short_name='NL')
    db.session.add_all([mlb_al, mlb_nl])
    db.session.flush()

    mlb_divs = {}
    for conf, divnames in [
        (mlb_al, ['AL East', 'AL Central', 'AL West']),
        (mlb_nl, ['NL East', 'NL Central', 'NL West']),
    ]:
        for dn in divnames:
            d = Division(conference_id=conf.id, sport_slug='mlb', name=dn)
            db.session.add(d)
            mlb_divs[dn] = d
    db.session.flush()

    def mlb_team(name, city, slug, abbr, conf, div, wins, losses, rank, color1='#003087', color2='#FFFFFF'):
        full = f"{city} {name}" if city else name
        t = Team(
            sport_slug='mlb', name=name, city=city, full_name=full,
            slug=slug, abbreviation=abbr,
            conference_id=conf.id, division_id=div.id,
            wins=wins, losses=losses,
            win_pct=round(wins / (wins + losses + 0.0001), 3),
            standing_rank=rank,
            color_primary=color1, color_secondary=color2,
        )
        db.session.add(t)
        return t

    # AL East
    orioles  = mlb_team('Orioles',      'Baltimore',    'baltimore-orioles',    'BAL', mlb_al, mlb_divs['AL East'], 101, 61, 1, '#DF4601', '#000000')
    red_sox  = mlb_team('Red Sox',      'Boston',       'boston-red-sox',       'BOS', mlb_al, mlb_divs['AL East'], 78, 84, 3, '#BD3039', '#0D2B56')
    yankees  = mlb_team('Yankees',      'New York',     'new-york-yankees',     'NYY', mlb_al, mlb_divs['AL East'], 82, 80, 2, '#132448', '#FFFFFF')
    rays     = mlb_team('Rays',         'Tampa Bay',    'tampa-bay-rays',       'TBR', mlb_al, mlb_divs['AL East'], 99, 63, 4, '#092C5C', '#8FBCE6')
    blue_j   = mlb_team('Blue Jays',    'Toronto',      'toronto-blue-jays',    'TOR', mlb_al, mlb_divs['AL East'], 89, 73, 5, '#134A8E', '#1D2D5C')
    # AL Central
    whitesox = mlb_team('White Sox',    'Chicago',      'chicago-white-sox',    'CWS', mlb_al, mlb_divs['AL Central'], 61, 101, 5, '#27251F', '#C0C2C4')
    guardians= mlb_team('Guardians',    'Cleveland',    'cleveland-guardians',  'CLE', mlb_al, mlb_divs['AL Central'], 76, 86, 4, '#E31937', '#0C2340')
    tigers   = mlb_team('Tigers',       'Detroit',      'detroit-tigers',       'DET', mlb_al, mlb_divs['AL Central'], 78, 84, 3, '#0C2340', '#FA4616')
    royals   = mlb_team('Royals',       'Kansas City',  'kansas-city-royals',   'KC',  mlb_al, mlb_divs['AL Central'], 56, 106, 1, '#004687', '#BD9B60')
    twins    = mlb_team('Twins',        'Minnesota',    'minnesota-twins',      'MIN', mlb_al, mlb_divs['AL Central'], 87, 75, 2, '#002B5C', '#D31145')
    # AL West
    astros   = mlb_team('Astros',       'Houston',      'houston-astros',       'HOU', mlb_al, mlb_divs['AL West'], 90, 72, 1, '#002D62', '#EB6E1F')
    angels   = mlb_team('Angels',       'Los Angeles',  'los-angeles-angels',   'LAA', mlb_al, mlb_divs['AL West'], 73, 89, 4, '#BA0021', '#003263')
    athletics= mlb_team('Athletics',    'Oakland',      'oakland-athletics',    'OAK', mlb_al, mlb_divs['AL West'], 50, 112, 5, '#003831', '#EFB21E')
    mariners = mlb_team('Mariners',     'Seattle',      'seattle-mariners',     'SEA', mlb_al, mlb_divs['AL West'], 88, 74, 2, '#0C2C56', '#005C5C')
    rangers  = mlb_team('Rangers',      'Texas',        'texas-rangers',        'TEX', mlb_al, mlb_divs['AL West'], 90, 72, 3, '#003278', '#C0111F')
    # NL East
    braves   = mlb_team('Braves',       'Atlanta',      'atlanta-braves',       'ATL', mlb_nl, mlb_divs['NL East'], 104, 58, 1, '#CE1141', '#13274F')
    marlins  = mlb_team('Marlins',      'Miami',        'miami-marlins',        'MIA', mlb_nl, mlb_divs['NL East'], 84, 78, 3, '#00A3E0', '#EF3340')
    mets     = mlb_team('Mets',         'New York',     'new-york-mets',        'NYM', mlb_nl, mlb_divs['NL East'], 75, 87, 4, '#002D72', '#FF5910')
    phillies = mlb_team('Phillies',     'Philadelphia', 'philadelphia-phillies','PHI', mlb_nl, mlb_divs['NL East'], 90, 72, 2, '#E81828', '#002D72')
    nationals= mlb_team('Nationals',    'Washington',   'washington-nationals', 'WSH', mlb_nl, mlb_divs['NL East'], 71, 91, 5, '#AB0003', '#14225A')
    # NL Central
    cubs     = mlb_team('Cubs',         'Chicago',      'chicago-cubs',         'CHC', mlb_nl, mlb_divs['NL Central'], 83, 79, 2, '#0E3386', '#CC3433')
    reds     = mlb_team('Reds',         'Cincinnati',   'cincinnati-reds',      'CIN', mlb_nl, mlb_divs['NL Central'], 82, 80, 3, '#C6011F', '#000000')
    rockies  = mlb_team('Rockies',      'Colorado',     'colorado-rockies',     'COL', mlb_nl, mlb_divs['NL Central'], 59, 103, 5, '#33006F', '#C4CED4')
    brewers  = mlb_team('Brewers',      'Milwaukee',    'milwaukee-brewers',    'MIL', mlb_nl, mlb_divs['NL Central'], 92, 70, 1, '#12284B', '#FFC52F')
    pirates  = mlb_team('Pirates',      'Pittsburgh',   'pittsburgh-pirates',   'PIT', mlb_nl, mlb_divs['NL Central'], 76, 86, 4, '#27251F', '#FDB827')
    # NL West
    dbacks   = mlb_team('D-backs',      'Arizona',      'arizona-dbacks',       'ARI', mlb_nl, mlb_divs['NL West'], 84, 78, 2, '#A71930', '#E3D4AD')
    dodgers  = mlb_team('Dodgers',      'Los Angeles',  'los-angeles-dodgers',  'LAD', mlb_nl, mlb_divs['NL West'], 100, 62, 1, '#005A9C', '#EF3E42')
    padres   = mlb_team('Padres',       'San Diego',    'san-diego-padres',     'SD',  mlb_nl, mlb_divs['NL West'], 82, 80, 3, '#2F241D', '#FFC425')
    sf_giants= mlb_team('Giants',       'San Francisco','san-francisco-giants', 'SF',  mlb_nl, mlb_divs['NL West'], 79, 83, 4, '#FD5A1E', '#27251F')
    cardinals= mlb_team('Cardinals',    'St. Louis',    'st-louis-cardinals',   'STL', mlb_nl, mlb_divs['NL West'], 71, 91, 5, '#C41E3A', '#0C2340')
    db.session.flush()

    # NY Yankees Players (with weight for infielder task)
    judge    = player('Aaron Judge',    'aaron-judge',    yankees, 'RF',  '99', '6-7', 282, 31, sport='mlb', salary=40000000, college='Fresno State', exp=8, birth_date='1992-04-26')
    rizzo    = player('Anthony Rizzo',  'anthony-rizzo',  yankees, '1B',  '48', '6-3', 240, 34, sport='mlb', salary=17000000, college='', exp=14, birth_date='1989-08-08')
    torres   = player('Gleyber Torres', 'gleyber-torres', yankees, '2B',  '25', '6-1', 205, 27, sport='mlb', salary=14300000, college='', exp=7, nationality='Venezuela', birth_date='1996-12-13')
    lemahieu = player('DJ LeMahieu',    'dj-lemahieu',    yankees, '3B',  '26', '6-4', 215, 35, sport='mlb', salary=15000000, college='LSU', exp=13, birth_date='1988-07-13')
    volpe    = player('Anthony Volpe',  'anthony-volpe',  yankees, 'SS',  '11', '5-11', 180, 23, sport='mlb', salary=720000, college='', exp=2, birth_date='2001-04-28')
    soto_j   = player('Juan Soto',      'juan-soto',      yankees, 'RF',  '22', '6-2', 224, 25, sport='mlb', salary=31000000, college='', exp=6, nationality='Dominican Republic', birth_date='1998-10-25')
    db.session.flush()

    # ══════════════════════════════════════════════════════════════════════════
    # Soccer
    # ══════════════════════════════════════════════════════════════════════════
    mls_east = Conference(sport_slug='soccer', name='MLS Eastern Conference', short_name='East')
    mls_west = Conference(sport_slug='soccer', name='MLS Western Conference', short_name='West')
    euro_conf= Conference(sport_slug='soccer', name='European Leagues', short_name='EU')
    db.session.add_all([mls_east, mls_west, euro_conf])
    db.session.flush()

    mls_div_e = Division(conference_id=mls_east.id, sport_slug='soccer', name='MLS East')
    mls_div_w = Division(conference_id=mls_west.id, sport_slug='soccer', name='MLS West')
    la_liga_d = Division(conference_id=euro_conf.id, sport_slug='soccer', name='La Liga')
    ligue1_d  = Division(conference_id=euro_conf.id, sport_slug='soccer', name='Ligue 1')
    prem_d    = Division(conference_id=euro_conf.id, sport_slug='soccer', name='Premier League')
    db.session.add_all([mls_div_e, mls_div_w, la_liga_d, ligue1_d, prem_d])
    db.session.flush()

    def soccer_team(name, city, slug, abbr, conf, div, wins, losses, rank, color1='#1d428a', color2='#FFFFFF'):
        full = f"{city} {name}" if city else name
        t = Team(
            sport_slug='soccer', name=name, city=city, full_name=full,
            slug=slug, abbreviation=abbr,
            conference_id=conf.id, division_id=div.id,
            wins=wins, losses=losses,
            win_pct=round(wins / (wins + losses + 0.0001), 3),
            standing_rank=rank,
            color_primary=color1, color_secondary=color2,
        )
        db.session.add(t)
        return t

    inter_miami= soccer_team('Inter Miami CF', '', 'inter-miami-cf',  'MIA', mls_east, mls_div_e, 18, 10, 3, '#F7B5CD', '#231F20')
    la_galaxy  = soccer_team('LA Galaxy',      'Los Angeles', 'la-galaxy', 'LA', mls_west, mls_div_w, 16, 14, 5, '#00245D', '#FFD100')
    lafc       = soccer_team('LAFC',           'Los Angeles', 'los-angeles-fc', 'LAFC', mls_west, mls_div_w, 21, 8, 1, '#C39E6D', '#000000')
    barcelona  = soccer_team('Barcelona',      '', 'fc-barcelona',    'BAR', euro_conf, la_liga_d, 28, 8, 1, '#A50044', '#004D98')
    real_madrid= soccer_team('Real Madrid',    '', 'real-madrid',     'RMA', euro_conf, la_liga_d, 29, 7, 2, '#FEBE10', '#00529F')
    psg        = soccer_team('Paris Saint-Germain','', 'paris-saint-germain','PSG',euro_conf, ligue1_d, 27, 5, 1, '#004170', '#DA291C')
    man_city   = soccer_team('Manchester City','', 'manchester-city', 'MCI', euro_conf, prem_d, 28, 7, 1, '#6CABDD', '#1C2C5B')
    db.session.flush()

    messi    = player('Lionel Messi',   'lionel-messi',   inter_miami, 'FW', '10', '5-7', 165, 36, sport='soccer', salary=60000000, nationality='Argentina', exp=20, birth_date='1987-06-24')
    ronaldo  = player('Cristiano Ronaldo','cristiano-ronaldo', barcelona, 'FW', '7', '6-2', 185, 39, sport='soccer', salary=200000000, nationality='Portugal', exp=21, birth_date='1985-02-05')
    mbappe   = player('Kylian Mbappe',  'kylian-mbappe',  real_madrid, 'FW', '9', '5-10', 168, 25, sport='soccer', salary=100000000, nationality='France', exp=8, birth_date='1998-12-20')
    db.session.flush()

    # Messi stats for last 5 Inter Miami games
    for season_year, gp, goals, asst in [('2023-24', 14, 11, 6)]:
        s = PlayerStat(
            player_id=messi.id, season=season_year, stat_type='season',
            games_played=gp, soccer_goals=goals, soccer_assists=asst, soccer_appearances=gp,
        )
        db.session.add(s)
    db.session.flush()

    # ══════════════════════════════════════════════════════════════════════════
    # NCAAM
    # ══════════════════════════════════════════════════════════════════════════
    ae_conf = Conference(sport_slug='ncaam', name='America East Conference', short_name='America East')
    db.session.add(ae_conf)
    db.session.flush()

    ae_div = Division(conference_id=ae_conf.id, sport_slug='ncaam', name='America East')
    db.session.add(ae_div)
    db.session.flush()

    def ncaam_team(name, slug, wins, losses, rank):
        t = Team(
            sport_slug='ncaam', name=name, city='', full_name=name, slug=slug,
            abbreviation=slug[:3].upper(),
            conference_id=ae_conf.id, division_id=ae_div.id,
            wins=wins, losses=losses,
            win_pct=round(wins / (wins + losses + 0.0001), 3),
            standing_rank=rank,
        )
        db.session.add(t)
        return t

    # America East teams — some tied in record
    vermont_t    = ncaam_team('Vermont',      'vermont-catamounts',     14, 4,  1)
    umbc_t       = ncaam_team('UMBC',         'umbc-retrievers',        11, 7,  2)
    albany_t     = ncaam_team('Albany',       'albany-great-danes',     11, 7,  3)
    uml_t        = ncaam_team('UMass Lowell', 'umass-lowell-riverhawks',10, 8,  4)
    maine_t      = ncaam_team('Maine',        'maine-black-bears',      10, 8,  5)
    binghamton_t = ncaam_team('Binghamton',   'binghamton-bearcats',    9,  9,  6)
    new_hamp_t   = ncaam_team('New Hampshire','new-hampshire-wildcats',  8, 10,  7)
    hartford_t   = ncaam_team('Hartford',     'hartford-hawks',          7, 11,  8)
    njit_t       = ncaam_team('NJIT',         'njit-highlanders',        7, 11,  9)
    db.session.flush()

    # ══════════════════════════════════════════════════════════════════════════
    # NCAAW Recruits
    # ══════════════════════════════════════════════════════════════════════════
    recruits_data = [
        dict(sport_slug='ncaaw', gender='F', name='Paige Bueckers', position='G',
             hometown='Hopkins, MN', committed_to='UConn', stars=5, rank=1,
             season='2024-25', class_year='2024'),
        dict(sport_slug='ncaaw', gender='F', name='Aaliyah Edwards', position='F',
             hometown='Kingston, ON', committed_to='South Carolina', stars=5, rank=2,
             season='2024-25', class_year='2024'),
        dict(sport_slug='ncaaw', gender='F', name='Olivia Miles', position='G',
             hometown='Pennsauken, NJ', committed_to='Notre Dame', stars=5, rank=3,
             season='2024-25', class_year='2024'),
        dict(sport_slug='ncaaw', gender='F', name='Hannah Hidalgo', position='G',
             hometown='Manalapan, NJ', committed_to='Notre Dame', stars=5, rank=4,
             season='2024-25', class_year='2024'),
        dict(sport_slug='ncaaw', gender='F', name='Saniya Rivers', position='G',
             hometown='Raleigh, NC', committed_to='NC State', stars=5, rank=5,
             season='2024-25', class_year='2024'),
    ]
    for rd in recruits_data:
        db.session.add(Recruit(**rd))
    db.session.flush()

    # ══════════════════════════════════════════════════════════════════════════
    # GAMES
    # ══════════════════════════════════════════════════════════════════════════
    def make_game(sport, home, away, home_sc, away_sc, date_str, status='final',
                  network='ESPN', venue='', leaders=None):
        g = Game(
            sport_slug=sport,
            home_team_id=home.id, away_team_id=away.id,
            home_score=home_sc, away_score=away_sc,
            date=date_str,
            date_display=datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y'),
            status=status,
            period='Final' if status == 'final' else ('Scheduled' if status == 'scheduled' else 'Live'),
            network=network,
            venue=venue or f"{home.city} Arena",
            game_leaders=json.dumps(leaders or {}),
        )
        db.session.add(g)
        return g

    # Dec 25, 2023 NBA Christmas games
    lal_bos_g = make_game('nba', lakers, celtics, 120, 117, '2023-12-25',
        venue='Crypto.com Arena',
        leaders={
            'top_scorer_name': 'LeBron James', 'top_scorer_pts': 28,
            'top_scorer_team': 'Los Angeles Lakers', 'top_scorer_position': 'SF',
            'top_rebounder_name': 'Anthony Davis', 'top_rebounder_reb': 14,
            'top_rebounder_team': 'Los Angeles Lakers',
            'top_assists_name': 'LeBron James', 'top_assists_ast': 8,
            'top_assists_team': 'Los Angeles Lakers',
            'home_high_scorer': 'LeBron James', 'home_high_points': 28,
            'away_high_scorer': 'Jayson Tatum', 'away_high_points': 26,
        })

    gsw_bos_g = make_game('nba', warriors, celtics, 115, 122, '2023-12-25',
        venue='Chase Center',
        leaders={
            'top_scorer_name': 'Stephen Curry', 'top_scorer_pts': 31,
            'top_scorer_team': 'Golden State Warriors', 'top_scorer_position': 'PG',
            'top_rebounder_name': 'Al Horford', 'top_rebounder_reb': 9,
            'top_rebounder_team': 'Boston Celtics',
            'top_assists_name': 'Jayson Tatum', 'top_assists_ast': 7,
            'top_assists_team': 'Boston Celtics',
            'home_high_scorer': 'Stephen Curry', 'home_high_points': 31,
            'away_high_scorer': 'Jaylen Brown', 'away_high_points': 29,
        })

    mil_nyk_g = make_game('nba', bucks, knicks, 108, 101, '2023-12-25',
        venue='Fiserv Forum',
        leaders={
            'top_scorer_name': 'Giannis Antetokounmpo', 'top_scorer_pts': 33,
            'top_scorer_team': 'Milwaukee Bucks', 'top_scorer_position': 'PF',
            'top_rebounder_name': 'Giannis Antetokounmpo', 'top_rebounder_reb': 12,
            'top_rebounder_team': 'Milwaukee Bucks',
            'top_assists_name': 'Jalen Brunson', 'top_assists_ast': 9,
            'top_assists_team': 'New York Knicks',
            'home_high_scorer': 'Giannis Antetokounmpo', 'home_high_points': 33,
            'away_high_scorer': 'Jalen Brunson', 'away_high_points': 25,
        })

    den_gsw_g = make_game('nba', nuggets, warriors, 127, 114, '2023-12-25',
        venue='Ball Arena',
        leaders={
            'top_scorer_name': 'Nikola Jokic', 'top_scorer_pts': 38,
            'top_scorer_team': 'Denver Nuggets', 'top_scorer_position': 'C',
            'top_rebounder_name': 'Nikola Jokic', 'top_rebounder_reb': 16,
            'top_rebounder_team': 'Denver Nuggets',
            'top_assists_name': 'Nikola Jokic', 'top_assists_ast': 10,
            'top_assists_team': 'Denver Nuggets',
            'home_high_scorer': 'Nikola Jokic', 'home_high_points': 38,
            'away_high_scorer': 'Stephen Curry', 'away_high_points': 26,
        })

    phi_mia_g = make_game('nba', sixers, heat, 110, 102, '2023-12-25',
        venue='Wells Fargo Center',
        leaders={
            'top_scorer_name': 'Tyrese Maxey', 'top_scorer_pts': 30,
            'top_scorer_team': 'Philadelphia 76ers', 'top_scorer_position': 'PG',
            'top_rebounder_name': 'Bam Adebayo', 'top_rebounder_reb': 12,
            'top_rebounder_team': 'Miami Heat',
            'top_assists_name': 'James Harden', 'top_assists_ast': 9,
            'top_assists_team': 'Philadelphia 76ers',
            'home_high_scorer': 'Tyrese Maxey', 'home_high_points': 30,
            'away_high_scorer': 'Jimmy Butler', 'away_high_points': 22,
        })

    # Recent NBA game: Heat vs Knicks
    mia_nyk_g = make_game('nba', heat, knicks, 108, 102, '2024-04-05',
        venue='Kaseya Center',
        leaders={
            'top_scorer_name': 'Jimmy Butler', 'top_scorer_pts': 24,
            'top_scorer_team': 'Miami Heat', 'top_scorer_position': 'SF',
            'top_rebounder_name': 'Bam Adebayo', 'top_rebounder_reb': 11,
            'top_rebounder_team': 'Miami Heat',
            'top_assists_name': 'Jalen Brunson', 'top_assists_ast': 8,
            'top_assists_team': 'New York Knicks',
            'home_high_scorer': 'Jimmy Butler', 'home_high_points': 24,
            'away_high_scorer': 'Jalen Brunson', 'away_high_points': 22,
        })

    # Recent NBA game: Celtics vs 76ers
    bos_phi_g = make_game('nba', celtics, sixers, 117, 109, '2024-04-06',
        venue='TD Garden',
        leaders={
            'top_scorer_name': 'Jayson Tatum', 'top_scorer_pts': 32,
            'top_scorer_team': 'Boston Celtics', 'top_scorer_position': 'SF',
            'top_rebounder_name': 'Al Horford', 'top_rebounder_reb': 11,
            'top_rebounder_team': 'Boston Celtics',
            'top_assists_name': 'Jrue Holiday', 'top_assists_ast': 7,
            'top_assists_team': 'Boston Celtics',
            'home_high_scorer': 'Jayson Tatum', 'home_high_points': 32,
            'away_high_scorer': 'Tobias Harris', 'away_high_points': 15,
        })

    # Scheduled Lakers game
    lal_sched = make_game('nba', lakers, nuggets, 0, 0, '2024-04-14',
        status='scheduled', network='ABC',
        venue='Crypto.com Arena', leaders={})

    # Recent Bucks game
    mil_chi_g = make_game('nba', bucks, bulls, 124, 108, '2024-04-07',
        venue='Fiserv Forum',
        leaders={
            'top_scorer_name': 'Damian Lillard', 'top_scorer_pts': 29,
            'top_scorer_team': 'Milwaukee Bucks', 'top_scorer_position': 'PG',
            'top_rebounder_name': 'Giannis Antetokounmpo', 'top_rebounder_reb': 13,
            'top_rebounder_team': 'Milwaukee Bucks',
            'top_assists_name': 'Damian Lillard', 'top_assists_ast': 8,
            'top_assists_team': 'Milwaukee Bucks',
        })

    # Lakers vs Celtics — most recent regular-season matchup
    # This ALSO covers ESPN-6 ("latest Lakers vs Celtics game").
    lal_bos_recent_g = make_game('nba', celtics, lakers, 122, 118, '2024-04-08',
        venue='TD Garden',
        leaders={
            'top_scorer_name': 'Jayson Tatum', 'top_scorer_pts': 34,
            'top_scorer_team': 'Boston Celtics', 'top_scorer_position': 'SF',
            'top_rebounder_name': 'Anthony Davis', 'top_rebounder_reb': 14,
            'top_rebounder_team': 'Los Angeles Lakers',
            'top_assists_name': 'LeBron James', 'top_assists_ast': 9,
            'top_assists_team': 'Los Angeles Lakers',
            'home_high_scorer': 'Jayson Tatum', 'home_high_points': 34,
            'away_high_scorer': 'LeBron James', 'away_high_points': 30,
        })

    db.session.flush()

    # ── GamePlayerStats ───────────────────────────────────────────────────────
    def gps(game, plyr, team, pts, reb, ast, stl=0, blk=0, mins='35'):
        g = GamePlayerStat(
            game_id=game.id, player_id=plyr.id, team_id=team.id,
            points=pts, rebounds=reb, assists=ast,
            steals=stl, blocks=blk, minutes=mins,
        )
        db.session.add(g)
        return g

    # Lakers vs Celtics (Dec 25)
    gps(lal_bos_g, lebron,   lakers,  28, 8,  6, 1, 0)
    gps(lal_bos_g, adavis,   lakers,  18, 14, 2, 1, 3)
    gps(lal_bos_g, reaves,   lakers,  19, 4,  5, 1, 0)
    gps(lal_bos_g, tatum,    celtics, 32, 8,  4, 1, 1)
    gps(lal_bos_g, jbrown,   celtics, 25, 5,  3, 2, 0)
    gps(lal_bos_g, horford,  celtics, 12, 7,  2, 0, 2)

    # Heat vs Knicks
    gps(mia_nyk_g, butler,   heat,    24, 6,  4, 2, 0)
    gps(mia_nyk_g, adebayo,  heat,    18, 11, 3, 1, 2)
    gps(mia_nyk_g, brunson,  knicks,  21, 3,  8, 0, 0)
    gps(mia_nyk_g, randle,   knicks,  17, 8,  2, 1, 0)

    # Celtics vs 76ers
    gps(bos_phi_g, tatum,    celtics, 32, 8,  4, 1, 1)
    gps(bos_phi_g, jbrown,   celtics, 22, 5,  3, 2, 0)
    gps(bos_phi_g, holiday,  celtics, 14, 5,  7, 3, 0)
    gps(bos_phi_g, maxey,    sixers,  27, 4,  6, 1, 0)
    gps(bos_phi_g, harris,   sixers,  15, 7,  2, 0, 0)

    # Recent Lakers vs Celtics (April 8, 2024) — full two-team box score
    gps(lal_bos_recent_g, tatum,     celtics, 34, 9,  5, 1, 1)
    gps(lal_bos_recent_g, jbrown,    celtics, 28, 6,  4, 2, 0)
    gps(lal_bos_recent_g, horford,   celtics, 11, 7,  3, 0, 2)
    gps(lal_bos_recent_g, holiday,   celtics, 15, 4,  6, 2, 0)
    gps(lal_bos_recent_g, porzingis, celtics, 18, 8,  1, 0, 3)
    gps(lal_bos_recent_g, white_c,   celtics, 16, 3,  4, 1, 1)
    gps(lal_bos_recent_g, lebron,    lakers,  30, 8, 9, 1, 0)
    gps(lal_bos_recent_g, adavis,    lakers,  24, 14, 2, 1, 4)
    gps(lal_bos_recent_g, reaves,    lakers,  21, 4,  5, 1, 0)
    gps(lal_bos_recent_g, russ,      lakers,  17, 3,  7, 1, 0)

    # Milwaukee vs Chicago (game 9) — populate box score
    gps(mil_chi_g, giannis, bucks, 28, 13, 4, 1, 2)
    gps(mil_chi_g, dame,    bucks, 29, 4,  8, 1, 0)
    gps(mil_chi_g, lavine,  bulls, 22, 4,  5, 0, 0)

    db.session.flush()

    # NHL recent games (yesterday)
    nhl_g1 = make_game('nhl', bruins, rangers,  4, 2, '2024-04-09', venue='TD Garden',
        leaders={'top_scorer_name': 'David Pastrnak', 'top_scorer_pts': 2,
                 'top_scorer_team': 'Boston Bruins', 'top_scorer_position': 'RW',
                 'top_rebounder_name': '', 'top_rebounder_reb': 0, 'top_rebounder_team': '',
                 'top_assists_name': 'David Pastrnak', 'top_assists_ast': 1,
                 'top_assists_team': 'Boston Bruins'})
    nhl_g2 = make_game('nhl', golden_k, oilers,  3, 2, '2024-04-09', venue='T-Mobile Arena',
        leaders={'top_scorer_name': 'Mark Stone', 'top_scorer_pts': 2,
                 'top_scorer_team': 'Vegas Golden Knights', 'top_scorer_position': 'RW',
                 'top_rebounder_name': '', 'top_rebounder_reb': 0, 'top_rebounder_team': '',
                 'top_assists_name': 'Mark Stone', 'top_assists_ast': 1,
                 'top_assists_team': 'Vegas Golden Knights'})

    # Soccer: Messi games for Inter Miami
    soccer_games = [
        ('2024-03-02', inter_miami, la_galaxy,  3, 1),
        ('2024-03-09', lafc, inter_miami,         1, 2),
        ('2024-03-16', inter_miami, man_city,    0, 1),
        ('2024-03-23', psg, inter_miami,          2, 3),
        ('2024-03-30', inter_miami, barcelona,   2, 2),
    ]
    soccer_game_objs = []
    for date_s, home, away, hsc, asc in soccer_games:
        sg = make_game('soccer', home, away, hsc, asc, date_s,
                       venue=f"{home.full_name} Stadium")
        soccer_game_objs.append(sg)
    db.session.flush()

    # Messi game player stats (last 5 games)
    messi_game_stats = [
        (soccer_game_objs[0], inter_miami, 2, 0, 1),
        (soccer_game_objs[1], inter_miami, 1, 0, 0),
        (soccer_game_objs[2], inter_miami, 0, 0, 1),
        (soccer_game_objs[3], inter_miami, 2, 0, 1),
        (soccer_game_objs[4], inter_miami, 1, 0, 2),
    ]
    for g_obj, team, pts, reb, ast in messi_game_stats:
        db.session.add(GamePlayerStat(
            game_id=g_obj.id, player_id=messi.id, team_id=team.id,
            points=pts, rebounds=reb, assists=ast,
        ))
    db.session.flush()

    # ══════════════════════════════════════════════════════════════════════════
    # POWER INDEX — NBA
    # ══════════════════════════════════════════════════════════════════════════
    nba_pi_data = [
        (celtics,  1,  10.5, 99.2,  7.1),
        (nuggets,  2,   9.8, 97.5,  6.3),
        (thunder,  3,   9.4, 96.1,  5.9),
        (wolves,   4,   9.0, 94.8,  5.5),
        (bucks,    5,   8.5, 92.3,  4.8),
        (clippers, 6,   8.1, 90.0,  4.2),
        (cavs,     7,   7.9, 88.5,  3.9),
        (suns,     8,   7.6, 86.0,  3.5),
        (pelicans, 9,   7.2, 83.2,  3.1),
        (pacers,  10,   6.9, 80.5,  2.8),
        (heat,    11,   6.7, 78.4,  2.5),
        (knicks,  12,   6.4, 75.2,  2.2),
        (kings,   13,   6.0, 71.8,  1.9),
        (mavs,    14,   5.8, 68.5,  1.6),
        (magic,   15,   5.5, 65.0,  1.3),
        (lakers,  16,   5.2, 61.5,  1.0),
        (warriors,17,   4.9, 57.8,  0.7),
        (sixers,  18,   4.6, 54.0,  0.4),
        (jazz,    19,   4.2, 49.8, -0.1),
        (hawks,   20,   3.9, 45.5, -0.5),
        (bulls,   21,   3.6, 41.2, -0.9),
        (rockets, 22,   3.3, 37.0, -1.3),
        (nets,    23,   3.0, 33.5, -1.7),
        (raptors, 24,   2.7, 29.8, -2.1),
        (blazers, 25,   2.4, 26.0, -2.5),
        (grizzlies,26,  2.1, 22.5, -2.9),
        (hornets, 27,   1.8, 18.8, -3.3),
        (pistons, 28,   1.5, 15.0, -3.7),
        (wizards, 29,   1.2, 11.5, -4.1),
        (spurs,   30,   0.9,  8.0, -4.5),
    ]
    for team, rank, idx_val, po, apd in nba_pi_data:
        db.session.add(PowerIndex(
            team_id=team.id, sport_slug='nba', season='2023-24',
            index_value=idx_val, playoff_odds=po,
            avg_point_diff=apd, rank=rank,
        ))

    # NFL Power Index
    nfl_pi_data = [
        (ravens, 1, 9.8, 95.0, 6.1),
        (nfl_sf, 2, 9.4, 93.5, 5.8),
        (chiefs, 3, 9.1, 92.0, 5.5),
        (cowboys, 4, 8.7, 89.5, 5.1),
        (lions, 5, 8.3, 86.0, 4.7),
        (eagles, 6, 7.9, 82.5, 4.3),
        (dolphins, 7, 7.5, 79.0, 3.9),
        (bills, 8, 7.1, 75.5, 3.5),
        (rams, 9, 6.7, 71.0, 3.1),
        (seahawks, 10, 6.3, 67.5, 2.7),
    ]
    for team, rank, idx_val, po, apd in nfl_pi_data:
        db.session.add(PowerIndex(
            team_id=team.id, sport_slug='nfl', season='2023',
            index_value=idx_val, playoff_odds=po,
            avg_point_diff=apd, rank=rank,
        ))
    db.session.flush()

    # ══════════════════════════════════════════════════════════════════════════
    # TRANSACTIONS
    # ══════════════════════════════════════════════════════════════════════════
    transactions_data = [
        dict(sport_slug='nba', team_id=lakers.id, player_id=lebron.id,
             description='LeBron James and agent met with Lakers front office to discuss contract extension plans.',
             transaction_type='contract', date='2024-04-08'),
        dict(sport_slug='nba', team_id=nets.id, player_id=simmons.id,
             description='Brooklyn Nets waive Ben Simmons; player clears waivers and becomes free agent.',
             transaction_type='waive', date='2024-04-07'),
        dict(sport_slug='nba', team_id=knicks.id, player_id=mikal.id,
             description='Mikal Bridges signs 4-year, $90M contract extension with New York Knicks.',
             transaction_type='sign', date='2024-04-06'),
        dict(sport_slug='nba', team_id=clippers.id, player_id=harden.id,
             description='James Harden traded from Philadelphia 76ers to Los Angeles Clippers.',
             transaction_type='trade', date='2023-10-31'),
        dict(sport_slug='nba', team_id=mavs.id, player_id=luka.id,
             description='Luka Doncic named Western Conference Player of the Week.',
             transaction_type='award', date='2024-04-05'),
        dict(sport_slug='nba', team_id=celtics.id, player_id=tatum.id,
             description='Jayson Tatum agrees to supermax contract extension worth $163M over 5 years.',
             transaction_type='sign', date='2024-04-04'),
        dict(sport_slug='nfl', team_id=jets.id, player_id=rodgers.id,
             description='Aaron Rodgers clears final medical evaluation; expected to return for 2024 season.',
             transaction_type='injury-update', date='2024-04-08'),
        dict(sport_slug='nfl', team_id=jets.id, player_id=z_wilson.id,
             description='Zach Wilson placed on injured reserve with right knee injury.',
             transaction_type='IR', date='2024-04-03'),
        dict(sport_slug='nba', team_id=sixers.id, player_id=embiid.id,
             description='Joel Embiid (left knee) ruled out indefinitely; team evaluating timeline for return.',
             transaction_type='injury-update', date='2024-04-08'),
        dict(sport_slug='nba', team_id=sixers.id, player_id=harris.id,
             description='Tobias Harris listed as Day-to-Day with right ankle soreness.',
             transaction_type='injury-update', date='2024-04-09'),
    ]
    for td in transactions_data:
        db.session.add(Transaction(**td))
    db.session.flush()

    # ══════════════════════════════════════════════════════════════════════════
    # ARTICLES
    # ══════════════════════════════════════════════════════════════════════════
    def article(title, slug, sport, body, tags, is_headline=False, is_featured=False,
                author='ESPN Staff', pub_date='April 9, 2024', subtitle=''):
        a = Article(
            title=title, slug=slug, sport_slug=sport, body=body,
            tags=json.dumps(tags), is_headline=is_headline, is_featured=is_featured,
            author=author, published_date=pub_date, subtitle=subtitle,
            created_at=datetime.utcnow(),
        )
        db.session.add(a)
        return a

    article('Celtics clinch best record in NBA; Tatum leads charge',
            'celtics-clinch-best-record-2024', 'nba',
            'The Boston Celtics have clinched the best record in the NBA for the 2023-24 season with a 64-18 mark. Jayson Tatum averaged 26.9 points per game, leading the franchise to its best regular season in years.',
            ['NBA', 'Boston Celtics', 'Jayson Tatum', 'Standings'], is_headline=True, pub_date='April 9, 2024')

    article('LeBron James surpasses all-time scoring record: 39,000+ career points',
            'lebron-james-all-time-scoring-record', 'nba',
            'LeBron James has cemented his status as the greatest scorer in NBA history, surpassing 39,000 career points. The Los Angeles Lakers forward now stands alone atop the all-time scoring list with 1,490 career games played.',
            ['NBA', 'LeBron James', 'Los Angeles Lakers', 'Records', 'Career Stats'], is_headline=True, pub_date='April 8, 2024')

    article('Embiid ruled out indefinitely with knee injury',
            'embiid-out-indefinitely-knee-2024', 'nba',
            'Joel Embiid of the Philadelphia 76ers has been ruled out indefinitely with a left knee injury. The reigning MVP had been averaging 34.7 points per game before the setback.',
            ['NBA', 'Joel Embiid', 'Philadelphia 76ers', 'Injuries'], is_headline=True, pub_date='April 8, 2024')

    article('Luka Doncic leads NBA in scoring at 33.9 ppg',
            'luka-doncic-scoring-leader-2024', 'nba',
            'Dallas Mavericks star Luka Doncic leads the NBA in scoring with 33.9 points per game, edging out Shai Gilgeous-Alexander (30.1 ppg) and Joel Embiid (34.7 ppg before injury) in the battle for the scoring title.',
            ['NBA', 'Luka Doncic', 'Dallas Mavericks', 'Stats Leaders'], pub_date='April 7, 2024')

    article('Jokic dominates with 12.4 rebounds and 9.0 assists per game',
            'jokic-rebounds-assists-leader-2024', 'nba',
            'Nikola Jokic continues his otherworldly season for the Denver Nuggets, leading the league in rebounds per game (12.4 rpg) alongside an elite 9.0 assists per game, making him a triple-double machine.',
            ['NBA', 'Nikola Jokic', 'Denver Nuggets', 'Stats', 'Rebounds', 'Assists'], pub_date='April 7, 2024')

    article('Trae Young tops assists race at 10.8 apg',
            'trae-young-assists-leader-2024', 'nba',
            'Atlanta Hawks guard Trae Young leads the NBA in assists with 10.8 per game this season. Young edges out Tyrese Haliburton (10.9 apg) in a tight battle for the assists crown.',
            ['NBA', 'Trae Young', 'Atlanta Hawks', 'Assists', 'Stats'], pub_date='April 6, 2024')

    article('Christmas Day NBA games: Lakers top Celtics 120-117',
            'nba-christmas-day-2023-recap', 'nba',
            'The Los Angeles Lakers edged the Boston Celtics 120-117 in the marquee Christmas Day matchup. LeBron James led all scorers with 28 points while Anthony Davis hauled in 14 rebounds. Jayson Tatum scored 32 for Boston.',
            ['NBA', 'Christmas Day', 'Los Angeles Lakers', 'Boston Celtics', 'LeBron James', 'Game Recap'],
            is_headline=True, pub_date='December 25, 2023')

    article('Heat outlast Knicks 108-102: Butler 24, Adebayo 11 rebounds',
            'heat-knicks-apr-2024-recap', 'nba',
            'Jimmy Butler scored 24 points and Bam Adebayo grabbed 11 rebounds as the Miami Heat defeated the New York Knicks 108-102. Jalen Brunson led New York with 21 points and 8 assists.',
            ['NBA', 'Miami Heat', 'New York Knicks', 'Jimmy Butler', 'Game Recap'], pub_date='April 5, 2024')

    article('NBA BPI: Boston Celtics rank No. 1 with BPI of 10.5',
            'nba-bpi-power-index-2024', 'nba',
            'ESPN\'s Basketball Power Index ranks the Boston Celtics as the top team in the NBA with a BPI score of 10.5, reflecting their 64-18 record and dominant play on both ends of the floor. The San Antonio Spurs rank last at No. 30.',
            ['NBA', 'BPI', 'Power Index', 'Boston Celtics', 'Standings'], pub_date='April 9, 2024')

    article('Giannis and Bucks look to make another deep run',
            'giannis-bucks-playoff-preview-2024', 'nba',
            'Giannis Antetokounmpo and the Milwaukee Bucks have finished with a 49-33 record and are poised for another playoff run. Giannis averaged 30.4 PPG, 11.5 RPG and 6.5 APG this season.',
            ['NBA', 'Milwaukee Bucks', 'Giannis Antetokounmpo', 'Playoffs'], pub_date='April 9, 2024')

    article('Golden State Warriors: Can Curry lead one more title run?',
            'warriors-curry-title-run-2024', 'nba',
            'Stephen Curry continues to dazzle, averaging 26.4 points per game for Golden State. The Warriors (46-36) secured a playoff spot and will look to Curry to deliver another championship.',
            ['NBA', 'Golden State Warriors', 'Stephen Curry', 'Playoffs'], pub_date='April 8, 2024')

    article('New York Knicks: Brunson\'s emergence leads team to 50 wins',
            'knicks-brunson-50-wins-2024', 'nba',
            'Jalen Brunson\'s breakout season — 28.7 points, 6.7 assists per game — has propelled the New York Knicks to 50 wins in 2023-24, their best record in over a decade.',
            ['NBA', 'New York Knicks', 'Jalen Brunson', 'Standings'], pub_date='April 7, 2024')

    article('New Orleans Pelicans clinch playoff spot; Zion Williamson stars',
            'pelicans-playoff-spot-2024', 'nba',
            'The New Orleans Pelicans have clinched a playoff berth behind Zion Williamson\'s 22.9 PPG. The Pelicans finished 49-33 in the Western Conference Southwest Division.',
            ['NBA', 'New Orleans Pelicans', 'Zion Williamson', 'Playoffs'], pub_date='April 8, 2024')

    article('Sabonis dominant: 13.6 rebounds per game for Kings',
            'sabonis-rebounds-leader-kings-2024', 'nba',
            'Domantas Sabonis of the Sacramento Kings leads the NBA in total rebounds, averaging 13.6 per game. His 79-game season has been one of the best rebounding performances in recent history.',
            ['NBA', 'Domantas Sabonis', 'Sacramento Kings', 'Rebounds', 'Stats'], pub_date='April 6, 2024')

    article('Trade Deadline Analysis: James Harden moves to Clippers',
            'harden-clippers-trade-analysis', 'nba',
            'The blockbuster trade sending James Harden from the Philadelphia 76ers to the Los Angeles Clippers reshapes the Western Conference. Harden averages 16.6 PPG and 8.5 APG with his new team.',
            ['NBA', 'James Harden', 'LA Clippers', 'Philadelphia 76ers', 'Trade'], pub_date='November 1, 2023')

    article('NFL 2023 MVP Race: Mahomes vs Lamar Jackson',
            'nfl-mvp-race-2023-mahomes-lamar', 'nfl',
            'The NFL MVP race in 2023 came down to Patrick Mahomes of the Kansas City Chiefs and Lamar Jackson of the Baltimore Ravens. Jackson won the award for the second time, throwing for 3,678 yards and 24 TDs while rushing for 821 yards.',
            ['NFL', 'MVP', 'Patrick Mahomes', 'Lamar Jackson', 'Kansas City Chiefs', 'Baltimore Ravens'],
            is_headline=True, pub_date='February 8, 2024')

    article('NFC North review: Lions lead the pack in 2023 season',
            'nfc-north-review-2023', 'nfl',
            'The Detroit Lions claimed the NFC North title with a 12-5 record, their best finish in franchise history. The Green Bay Packers (9-8) snuck into the playoffs while the Chicago Bears and Minnesota Vikings missed the postseason.',
            ['NFL', 'NFC North', 'Detroit Lions', 'Green Bay Packers', 'Standings'], pub_date='January 15, 2024')

    article('Aaron Rodgers cleared for 2024 Jets season after Achilles recovery',
            'aaron-rodgers-jets-2024-return', 'nfl',
            'Aaron Rodgers has been cleared to return for the 2024 New York Jets season following a grueling recovery from a torn Achilles. The 40-year-old QB will be backed up by Zach Wilson, who is dealing with his own knee injury.',
            ['NFL', 'Aaron Rodgers', 'New York Jets', 'Zach Wilson', 'Injuries'], is_headline=True, pub_date='April 8, 2024')

    article('NHL Standings 2023-24: Rangers lead Metropolitan Division',
            'nhl-standings-review-2024', 'nhl',
            'The New York Rangers lead the Metropolitan Division with a 55-23-4 record. In the Western Conference, the Dallas Stars top the Central Division (52-21-9) while the Vegas Golden Knights lead the Pacific Division (45-29-8).',
            ['NHL', 'Standings', 'New York Rangers', 'Dallas Stars', 'Vegas Golden Knights'], pub_date='April 9, 2024')

    article('Vegas Golden Knights: Defending NHL champions eye repeat',
            'vegas-golden-knights-2024-preview', 'nhl',
            'The Vegas Golden Knights, winners of the 2023 Stanley Cup, are pushing for a repeat. Leading the Pacific Division with a 45-29-8 record, the Golden Knights remain one of the most feared teams in hockey.',
            ['NHL', 'Vegas Golden Knights', 'Stanley Cup', 'Pacific Division'], is_headline=True, pub_date='April 8, 2024')

    article('Bruins dominate: Atlantic Division leaders with 47 wins',
            'bruins-atlantic-division-2024', 'nhl',
            'The Boston Bruins lead the Atlantic Division with a 47-20-15 record, continuing their dominance of the Eastern Conference. David Pastrnak leads the team in scoring.',
            ['NHL', 'Boston Bruins', 'Atlantic Division', 'Standings'], pub_date='April 7, 2024')

    article('Lionel Messi lights up MLS with Inter Miami',
            'messi-inter-miami-mls-2024', 'soccer',
            'Lionel Messi has been sensational for Inter Miami CF in MLS, scoring 11 goals and providing 6 assists in 14 appearances. The Argentine legend has transformed the league and Inter Miami\'s profile globally.',
            ['Soccer', 'Lionel Messi', 'Inter Miami', 'MLS'], is_headline=True, pub_date='April 5, 2024')

    article('Messi Inter Miami: Last 5 games review',
            'messi-inter-miami-last-5-games', 'soccer',
            'Lionel Messi\'s last five games with Inter Miami CF have been spectacular. '
            'Game 1 — March 2, 2024: Inter Miami 3, LA Galaxy 1 (Home win). Messi scored twice and added an assist. '
            'Game 2 — March 9, 2024: Inter Miami 2, LAFC 1 (Away win). Messi opened the scoring with a trademark free-kick. '
            'Game 3 — March 16, 2024: Inter Miami 0, Manchester City 1 (Home loss, friendly). Messi created chances but could not break through. '
            'Game 4 — March 23, 2024: Inter Miami 3, Paris Saint-Germain 2 (Away win, friendly). Messi scored twice on his return to Parc des Princes. '
            'Game 5 — March 30, 2024: Inter Miami 2, Barcelona 2 (Home draw, friendly). Messi scored and assisted in a reunion with his former club. '
            'Summary of last 5 games: 3 wins, 1 loss, 1 draw — Messi contributed 6 goals and 4 assists across all competitions.',
            ['Soccer', 'Lionel Messi', 'Inter Miami', 'MLS', 'Game Log'], pub_date='April 1, 2024')

    article('Barcelona vs Real Madrid: La Liga title race heats up',
            'barcelona-real-madrid-la-liga-2024', 'soccer',
            'Real Madrid leads La Liga with 29 wins while Barcelona sits second at 28 wins. The title race continues to be one of the most compelling in recent memory.',
            ['Soccer', 'Barcelona', 'Real Madrid', 'La Liga'], pub_date='April 8, 2024')

    article('NCAAM America East standings: Vermont leads with 14-4 record',
            'ncaam-america-east-standings-2024', 'ncaam',
            'Vermont leads the America East Conference with a 14-4 record. UMBC and Albany are tied at 11-7, with UMass Lowell and Maine also level at 10-8. The conference tournament promises to be highly competitive.',
            ['NCAAM', 'America East', 'Vermont', 'UMBC', 'Albany', 'Standings'], pub_date='March 10, 2024')

    article('NCAAW Top Recruits 2024-25: UConn lands No. 1 prospect',
            'ncaaw-top-recruits-2024', 'ncaaw',
            'UConn has secured a commitment from the top-ranked recruit in the 2024-25 NCAAW class. South Carolina nabbed the No. 2 recruit while Notre Dame landed the third-ranked player.',
            ['NCAAW', 'Recruiting', 'UConn', 'South Carolina', 'Notre Dame'], pub_date='March 15, 2024')

    article('NY Yankees 2024 preview: Judge, Soto headline lineup',
            'yankees-2024-preview', 'mlb',
            'The New York Yankees feature a fearsome lineup led by Aaron Judge (RF, 282 lbs) and Juan Soto (RF, 224 lbs). Anthony Rizzo (1B, 240 lbs) is the heaviest infielder on the roster, with DJ LeMahieu (3B, 215 lbs) and Gleyber Torres (2B, 205 lbs) also key pieces.',
            ['MLB', 'New York Yankees', 'Aaron Judge', 'Juan Soto', 'Anthony Rizzo', 'Roster'],
            is_headline=True, pub_date='March 28, 2024')

    article('Kansas City Royals look to rebuild around young core',
            'royals-rebuild-2024', 'mlb',
            'The Kansas City Royals finished 56-106 in 2023 and are committed to their rebuild. Bobby Witt Jr. leads the young core as the team looks to return to relevance in the AL Central.',
            ['MLB', 'Kansas City Royals', 'Rebuild', 'Bobby Witt Jr.'], pub_date='March 29, 2024')

    article('Los Angeles Lakers: Can LeBron and Davis make a title run?',
            'lakers-lebron-davis-playoff-2024', 'nba',
            'With LeBron James and Anthony Davis both healthy, the Los Angeles Lakers (47-35) are preparing for a playoff push. LeBron averages 25.7 PPG, 7.3 RPG, 8.3 APG this season.',
            ['NBA', 'Los Angeles Lakers', 'LeBron James', 'Anthony Davis', 'Playoffs'],
            is_headline=True, pub_date='April 9, 2024')

    article('LA Clippers make Western Conference playoff push',
            'la-clippers-playoff-push-2024', 'nba',
            'The LA Clippers (51-31) have secured a top-two seed in the Western Conference behind Kawhi Leonard and James Harden. Paul George provides an added dimension on both ends.',
            ['NBA', 'LA Clippers', 'Harden', 'Playoffs'], pub_date='April 8, 2024')

    article('NBA Teams with "New" in their names: Knicks and Pelicans',
            'nba-new-teams-knicks-pelicans', 'nba',
            'Two NBA teams carry "New" in their names: the New York Knicks and the New Orleans Pelicans. Both are playoff contenders in 2023-24, with the Knicks at 50-32 and the Pelicans at 49-33.',
            ['NBA', 'New York Knicks', 'New Orleans Pelicans', 'Teams'], pub_date='April 6, 2024')

    article('Teams with "Golden" in name: Warriors and Golden Knights',
            'golden-teams-warriors-knights', 'nba',
            'Across North American professional sports, two teams carry the word "Golden": the Golden State Warriors (NBA) and the Vegas Golden Knights (NHL). The Warriors lead the Pacific Division while the Golden Knights defend their Stanley Cup title.',
            ['NBA', 'NHL', 'Golden State Warriors', 'Vegas Golden Knights', 'Teams'], pub_date='April 5, 2024')

    article('Los Angeles sports scene: A city of champions',
            'los-angeles-sports-teams', 'nba',
            'Los Angeles is home to multiple major sports franchises: the Lakers and Clippers (NBA), the Rams and Chargers (NFL), the Kings (NHL), the Dodgers and Angels (MLB), and LA Galaxy and LAFC (Soccer).',
            ['Los Angeles', 'Lakers', 'Clippers', 'Rams', 'Chargers', 'Kings', 'Dodgers', 'LA Galaxy', 'LAFC'],
            pub_date='April 4, 2024')

    article('Boston Celtics salary breakdown: Tatum tops at $37.1M',
            'celtics-salary-breakdown-2024', 'nba',
            'The Boston Celtics have the NBA\'s highest payroll for the 2023-24 season. Jayson Tatum leads the team with a $37.1M salary, the highest on the roster. Jaylen Brown ($30.4M) and Jrue Holiday ($30.4M) are next, followed by Kristaps Porzingis ($28.0M), Al Horford ($26.5M), and Derrick White ($22.5M). Tatum\'s figure tops the roster and confirms his status as the franchise cornerstone.',
            ['NBA', 'Boston Celtics', 'Salary', 'Jayson Tatum', 'Cap'], is_headline=True, pub_date='April 9, 2024')

    article('76ers injury report: Embiid out, Harris day-to-day',
            '76ers-injury-report-2024', 'nba',
            'The Philadelphia 76ers are navigating injuries heading into the playoffs. Joel Embiid (left knee) is listed as OUT indefinitely, while Tobias Harris (right ankle soreness) is listed as Day-to-Day.',
            ['NBA', 'Philadelphia 76ers', 'Joel Embiid', 'Tobias Harris', 'Injuries'], pub_date='April 9, 2024')

    article('Shai Gilgeous-Alexander: OKC Thunder\'s MVP candidate',
            'sga-okc-thunder-mvp-2024', 'nba',
            'Shai Gilgeous-Alexander of the OKC Thunder is averaging 30.1 points per game, cementing his status as an MVP candidate. At 25, SGA leads one of the youngest and most exciting teams in the Western Conference.',
            ['NBA', 'Shai Gilgeous-Alexander', 'OKC Thunder', 'MVP', 'Stats'], pub_date='April 7, 2024')

    article('Sabonis and Domantas Sacramento Kings push for playoffs',
            'sabonis-kings-playoffs-2024', 'nba',
            'Domantas Sabonis leads the Sacramento Kings with 19.9 PPG and an NBA-best 13.6 rebounds per game. The Kings (46-36) are on the bubble for the playoffs in a tough Western Conference.',
            ['NBA', 'Domantas Sabonis', 'Sacramento Kings', 'Rebounds', 'Playoffs'], pub_date='April 8, 2024')

    article('NHL Pacific Division: Vegas Golden Knights in pole position',
            'nhl-pacific-division-2024', 'nhl',
            'The Vegas Golden Knights lead the NHL Pacific Division with a 45-29-8 record. The Edmonton Oilers (49-27-6) are second overall but trail on division points. The Los Angeles Kings (44-27-11) round out the top three.',
            ['NHL', 'Pacific Division', 'Vegas Golden Knights', 'Edmonton Oilers', 'Los Angeles Kings'],
            pub_date='April 9, 2024')

    article('NFL Depth Chart Watch: Jets name Rodgers clear starter for 2024',
            'jets-rodgers-depth-chart-2024', 'nfl',
            'The New York Jets depth chart has Aaron Rodgers as the clear QB1 heading into 2024. Zach Wilson is listed as the backup but is currently injured. Breece Hall leads the backfield and Garrett Wilson is the top wide receiver.',
            ['NFL', 'New York Jets', 'Aaron Rodgers', 'Depth Chart', 'Zach Wilson'], pub_date='April 8, 2024')

    article('NBA Top Headlines: Celtics, LeBron, Embiid dominate news',
            'nba-top-headlines-april-2024', 'nba',
            'The NBA is buzzing with news: the Boston Celtics clinch best record, LeBron James breaks the all-time scoring record, Joel Embiid ruled out with knee injury, and the playoff picture takes shape across both conferences.',
            ['NBA', 'Headlines', 'Boston Celtics', 'LeBron James', 'Joel Embiid'],
            is_headline=True, is_featured=True, pub_date='April 9, 2024')

    db.session.flush()
