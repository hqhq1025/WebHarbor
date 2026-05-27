"""
GUI Deepen module for BBC News mirror.

Adds 25+ visual HTML pages modeled on real bbc.com surfaces that the
existing mirror does not cover:

  - 8 sport hubs (football / cricket / rugby-union / tennis / formula1 /
    olympics / american-football / boxing)
  - sport scoreboard / standings / team / fixtures / results / live blog
  - weather forecast (per city) / weather world / weather UK
  - iPlayer episode / iPlayer category / iPlayer schedule
  - Sounds podcast / Sounds live station
  - News in_pictures gallery / News explainer / News longform
  - Programmes (BBC bbcprogrammes-id format)
  - Bitesize subject
  - Regional homes: cymru / scotland / northernireland / wales
  - Business markets index / Business companies ticker
  - News topic hub

All data is deterministically derived from md5 seeds so the seed DB is
never mutated (byte-identical reset invariant preserved).

GUI tasks attached to each page are appended into tasks.jsonl with
prefix `BBC News--gui_<page>_<NNN>`.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta

from flask import abort, render_template, request, jsonify


# --------------------------------------------------------------------- #
# Deterministic anchor + seed helpers                                    #
# --------------------------------------------------------------------- #

GUI_REFERENCE_DATE = datetime(2026, 4, 15, 9, 0, 0)


def _gui_seed(*parts) -> str:
    return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()


def _gui_pick(h: str, offset: int, pool):
    return pool[int(h[offset:offset + 2], 16) % len(pool)]


def _gui_int(h: str, offset: int, lo: int, hi: int) -> int:
    return lo + (int(h[offset:offset + 4], 16) % (hi - lo + 1))


# --------------------------------------------------------------------- #
# Canonical pools (real names from real BBC pages)                       #
# --------------------------------------------------------------------- #

PREMIER_LEAGUE_TEAMS = [
    "Arsenal", "Aston Villa", "AFC Bournemouth", "Brentford",
    "Brighton & Hove Albion", "Burnley", "Chelsea", "Crystal Palace",
    "Everton", "Fulham", "Leeds United", "Liverpool",
    "Manchester City", "Manchester United", "Newcastle United",
    "Nottingham Forest", "Sunderland", "Tottenham Hotspur",
    "West Ham United", "Wolverhampton Wanderers",
]

LA_LIGA_TEAMS = [
    "Real Madrid", "Barcelona", "Atletico Madrid", "Real Sociedad",
    "Athletic Club", "Villarreal", "Real Betis", "Sevilla",
    "Valencia", "Osasuna", "Getafe", "Girona", "Las Palmas",
    "Mallorca", "Celta Vigo", "Cadiz", "Alaves", "Rayo Vallecano",
    "Granada", "Almeria",
]

CRICKET_TEAMS = [
    "England", "Australia", "India", "Pakistan", "New Zealand",
    "South Africa", "Sri Lanka", "West Indies", "Bangladesh",
    "Afghanistan", "Ireland", "Zimbabwe",
]

THE_HUNDRED_TEAMS = [
    "London Spirit", "Trent Rockets", "Manchester Originals",
    "Birmingham Phoenix", "Welsh Fire", "Oval Invincibles",
    "Northern Superchargers", "Southern Brave",
]

RUGBY_PREMIERSHIP = [
    "Bath", "Bristol Bears", "Exeter Chiefs", "Gloucester",
    "Harlequins", "Leicester Tigers", "Newcastle Falcons",
    "Northampton Saints", "Sale Sharks", "Saracens",
]

SIX_NATIONS = ["England", "France", "Ireland", "Italy", "Scotland", "Wales"]

ATP_PLAYERS = [
    "Carlos Alcaraz", "Jannik Sinner", "Novak Djokovic", "Daniil Medvedev",
    "Alexander Zverev", "Andrey Rublev", "Holger Rune", "Hubert Hurkacz",
    "Casper Ruud", "Grigor Dimitrov", "Stefanos Tsitsipas", "Taylor Fritz",
]
WTA_PLAYERS = [
    "Iga Swiatek", "Aryna Sabalenka", "Coco Gauff", "Elena Rybakina",
    "Jessica Pegula", "Ons Jabeur", "Marketa Vondrousova", "Qinwen Zheng",
    "Maria Sakkari", "Daria Kasatkina", "Beatriz Haddad Maia", "Madison Keys",
]

F1_DRIVERS = [
    ("Max Verstappen", "Red Bull"),
    ("Lando Norris", "McLaren"),
    ("Charles Leclerc", "Ferrari"),
    ("Carlos Sainz", "Ferrari"),
    ("Oscar Piastri", "McLaren"),
    ("George Russell", "Mercedes"),
    ("Lewis Hamilton", "Mercedes"),
    ("Sergio Perez", "Red Bull"),
    ("Fernando Alonso", "Aston Martin"),
    ("Lance Stroll", "Aston Martin"),
    ("Pierre Gasly", "Alpine"),
    ("Esteban Ocon", "Alpine"),
    ("Alex Albon", "Williams"),
    ("Yuki Tsunoda", "RB"),
    ("Nico Hulkenberg", "Haas"),
    ("Kevin Magnussen", "Haas"),
    ("Valtteri Bottas", "Stake"),
    ("Zhou Guanyu", "Stake"),
    ("Logan Sargeant", "Williams"),
    ("Daniel Ricciardo", "RB"),
]
F1_CIRCUITS = [
    ("Bahrain Grand Prix", "Bahrain International Circuit", "Sakhir"),
    ("Saudi Arabian Grand Prix", "Jeddah Corniche Circuit", "Jeddah"),
    ("Australian Grand Prix", "Albert Park", "Melbourne"),
    ("Japanese Grand Prix", "Suzuka", "Suzuka"),
    ("Chinese Grand Prix", "Shanghai International Circuit", "Shanghai"),
    ("Miami Grand Prix", "Miami International Autodrome", "Miami"),
    ("Emilia Romagna Grand Prix", "Imola", "Imola"),
    ("Monaco Grand Prix", "Circuit de Monaco", "Monte Carlo"),
    ("Canadian Grand Prix", "Circuit Gilles Villeneuve", "Montreal"),
    ("Spanish Grand Prix", "Circuit de Barcelona-Catalunya", "Barcelona"),
    ("Austrian Grand Prix", "Red Bull Ring", "Spielberg"),
    ("British Grand Prix", "Silverstone", "Silverstone"),
]

NFL_TEAMS = [
    "Kansas City Chiefs", "Buffalo Bills", "Baltimore Ravens",
    "San Francisco 49ers", "Philadelphia Eagles", "Dallas Cowboys",
    "Detroit Lions", "Miami Dolphins", "Cincinnati Bengals",
    "Green Bay Packers", "Houston Texans", "Cleveland Browns",
    "Pittsburgh Steelers", "Los Angeles Rams", "Tampa Bay Buccaneers",
    "Seattle Seahawks",
]

BOXING_FIGHTERS = [
    "Tyson Fury", "Oleksandr Usyk", "Anthony Joshua", "Deontay Wilder",
    "Canelo Alvarez", "Dmitry Bivol", "Terence Crawford", "Errol Spence Jr",
    "Naoya Inoue", "Gervonta Davis", "Ryan Garcia", "Devin Haney",
]

OLYMPICS_NATIONS = [
    "United States", "China", "Japan", "Australia", "France",
    "Great Britain", "South Korea", "Netherlands", "Germany",
    "Italy", "Canada", "Hungary",
]

SPORTS = [
    ("football", "Football", "scores-fixtures"),
    ("cricket", "Cricket", "england"),
    ("rugby-union", "Rugby Union", "premiership"),
    ("tennis", "Tennis", "live-scores"),
    ("formula1", "Formula 1", "results"),
    ("olympics", "Olympics", "medals"),
    ("american-football", "American Football", "nfl"),
    ("boxing", "Boxing", "fights"),
]

UK_CITIES = [
    ("london", "London", 6, 17, 22),
    ("manchester", "Manchester", 4, 14, 19),
    ("birmingham", "Birmingham", 5, 15, 20),
    ("leeds", "Leeds", 4, 13, 18),
    ("glasgow", "Glasgow", 3, 12, 17),
    ("edinburgh", "Edinburgh", 3, 12, 17),
    ("cardiff", "Cardiff", 6, 15, 20),
    ("belfast", "Belfast", 4, 13, 18),
    ("liverpool", "Liverpool", 5, 14, 19),
    ("bristol", "Bristol", 6, 16, 21),
    ("newcastle", "Newcastle", 3, 12, 17),
    ("southampton", "Southampton", 7, 17, 22),
]

WORLD_CITIES = [
    ("new-york", "New York", "United States", 12, 22),
    ("tokyo", "Tokyo", "Japan", 16, 25),
    ("paris", "Paris", "France", 9, 18),
    ("berlin", "Berlin", "Germany", 7, 17),
    ("madrid", "Madrid", "Spain", 14, 26),
    ("rome", "Rome", "Italy", 13, 23),
    ("dubai", "Dubai", "UAE", 25, 38),
    ("sydney", "Sydney", "Australia", 11, 19),
    ("singapore", "Singapore", "Singapore", 26, 32),
    ("mumbai", "Mumbai", "India", 24, 33),
    ("lagos", "Lagos", "Nigeria", 23, 31),
    ("sao-paulo", "Sao Paulo", "Brazil", 14, 23),
]

IPLAYER_CATEGORIES = [
    ("drama", "Drama", [
        ("happy-valley", "Happy Valley", "Sarah Lancashire", 6, 58),
        ("line-of-duty", "Line of Duty", "Vicky McClure", 7, 60),
        ("peaky-blinders", "Peaky Blinders", "Cillian Murphy", 6, 58),
        ("sherlock", "Sherlock", "Benedict Cumberbatch", 4, 90),
        ("bodyguard", "Bodyguard", "Richard Madden", 1, 60),
        ("vigil", "Vigil", "Suranne Jones", 2, 58),
    ]),
    ("comedy", "Comedy", [
        ("fleabag", "Fleabag", "Phoebe Waller-Bridge", 2, 27),
        ("ghosts", "Ghosts", "Charlotte Ritchie", 5, 30),
        ("inside-no-9", "Inside No. 9", "Reece Shearsmith", 9, 30),
        ("the-office", "The Office", "Ricky Gervais", 2, 30),
        ("mum", "Mum", "Lesley Manville", 3, 30),
        ("motherland", "Motherland", "Anna Maxwell Martin", 4, 28),
    ]),
    ("documentary", "Documentary", [
        ("planet-earth-iii", "Planet Earth III", "David Attenborough", 1, 60),
        ("frozen-planet-ii", "Frozen Planet II", "David Attenborough", 1, 60),
        ("blue-planet-ii", "Blue Planet II", "David Attenborough", 1, 58),
        ("dynasties", "Dynasties", "David Attenborough", 1, 60),
        ("seven-worlds-one-planet", "Seven Worlds, One Planet", "David Attenborough", 1, 60),
        ("the-green-planet", "The Green Planet", "David Attenborough", 1, 60),
    ]),
    ("news", "News", [
        ("newsnight", "Newsnight", "Victoria Derbyshire", 1, 45),
        ("panorama", "Panorama", "Various", 1, 30),
        ("question-time", "Question Time", "Fiona Bruce", 1, 60),
        ("the-andrew-marr-show", "The Andrew Marr Show", "Andrew Marr", 1, 60),
        ("bbc-news-at-ten", "BBC News at Ten", "Huw Edwards", 1, 30),
        ("hardtalk", "HARDtalk", "Stephen Sackur", 1, 25),
    ]),
    ("sport", "Sport", [
        ("match-of-the-day", "Match of the Day", "Gary Lineker", 1, 90),
        ("ski-sunday", "Ski Sunday", "Ed Leigh", 1, 30),
        ("super-league-show", "Super League Show", "Tanya Arnold", 1, 30),
        ("a-question-of-sport", "A Question of Sport", "Paddy McGuinness", 51, 30),
        ("countryfile", "Countryfile", "Matt Baker", 1, 60),
        ("snooker", "Snooker", "Hazel Irvine", 1, 90),
    ]),
]

TV_CHANNELS = [
    ("bbc-one", "BBC One"),
    ("bbc-two", "BBC Two"),
    ("bbc-four", "BBC Four"),
    ("bbc-news", "BBC News"),
    ("cbeebies", "CBeebies"),
    ("cbbc", "CBBC"),
]

PODCASTS = [
    ("global-news-podcast", "Global News Podcast", "BBC World Service",
        "The day's top stories from the BBC World Service.", "Weekdays", 30),
    ("newscast", "Newscast", "Adam Fleming",
        "Daily political and news analysis from BBC journalists.", "Daily", 35),
    ("americast", "Americast", "Justin Webb, Sarah Smith",
        "Politics, culture and life in the United States.", "Weekly", 45),
    ("the-news-quiz", "The News Quiz", "Andy Zaltzman",
        "A satirical take on the week's news.", "Weekly", 28),
    ("more-or-less", "More or Less", "Tim Harford",
        "Behind the stats in the news.", "Weekly", 28),
    ("in-our-time", "In Our Time", "Melvyn Bragg",
        "Discussion of the history of ideas.", "Weekly", 50),
    ("the-coming-storm", "The Coming Storm", "Gabriel Gatehouse",
        "The story of QAnon and US conspiracy culture.", "Series", 40),
    ("tech-tent", "Tech Tent", "Rory Cellan-Jones",
        "Weekly technology programme.", "Weekly", 30),
    ("desert-island-discs", "Desert Island Discs", "Lauren Laverne",
        "Guests choose music for a desert island.", "Weekly", 45),
    ("from-our-own-correspondent", "From Our Own Correspondent", "Kate Adie",
        "Foreign correspondents on stories from around the world.", "Weekly", 30),
]

LIVE_STATIONS = [
    ("radio-1", "BBC Radio 1", "The home of new music."),
    ("radio-2", "BBC Radio 2", "The home of great music from across the decades."),
    ("radio-3", "BBC Radio 3", "Classical music, jazz and world."),
    ("radio-4", "BBC Radio 4", "News, drama and comedy."),
    ("radio-5-live", "BBC Radio 5 Live", "Live sport and news."),
    ("radio-6-music", "BBC Radio 6 Music", "Alternative music from across the decades."),
    ("world-service", "BBC World Service", "International news in English."),
    ("asian-network", "BBC Asian Network", "Asian music and conversation."),
]

NEWS_TOPICS = [
    ("ukraine-war", "Ukraine war"),
    ("us-election", "US Election 2024"),
    ("climate-change", "Climate change"),
    ("middle-east-crisis", "Middle East crisis"),
    ("artificial-intelligence", "Artificial intelligence"),
    ("cost-of-living", "Cost of living"),
    ("king-charles-iii", "King Charles III"),
    ("nhs", "NHS"),
    ("brexit", "Brexit"),
    ("space", "Space"),
    ("royal-family", "Royal Family"),
    ("interest-rates", "Interest rates"),
]

NEWS_PICTURES_EVENTS = [
    ("eurovision-2026", "Eurovision Song Contest 2026", "Malmo, Sweden"),
    ("trooping-the-colour", "Trooping the Colour 2026", "London, UK"),
    ("paris-olympics-opening", "Paris 2024 Olympics opening ceremony", "Paris, France"),
    ("notre-dame-reopening", "Notre Dame reopens after fire", "Paris, France"),
    ("coronation-king-charles", "The Coronation of King Charles III", "Westminster Abbey"),
    ("glastonbury-2026", "Glastonbury Festival 2026", "Worthy Farm, UK"),
    ("kentucky-derby-150", "150th Kentucky Derby", "Louisville, Kentucky"),
    ("met-gala-2026", "Met Gala 2026", "New York, USA"),
    ("china-floods", "Flooding across central China", "Henan, China"),
    ("turkey-earthquake", "Turkey-Syria earthquake aftermath", "Antakya, Turkey"),
]

NEWS_EXPLAINERS = [
    ("what-is-quantitative-easing", "What is quantitative easing?"),
    ("how-does-the-electoral-college-work", "How does the US Electoral College work?"),
    ("what-is-a-recession", "What is a recession?"),
    ("how-does-a-general-election-work", "How does a UK general election work?"),
    ("what-is-cop29", "What is COP29 and why does it matter?"),
    ("what-are-tariffs", "What are tariffs and how do they work?"),
    ("how-vaccines-work", "How do vaccines work?"),
    ("what-is-an-icbm", "What is an ICBM?"),
    ("how-bitcoin-mining-works", "How does Bitcoin mining work?"),
    ("what-is-article-50", "What is Article 50?"),
]

NEWS_LONGFORM = [
    ("the-secret-history-of-stonehenge", "The secret history of Stonehenge"),
    ("inside-the-mind-of-an-ai-engineer", "Inside the mind of an AI engineer"),
    ("the-last-coal-miners-of-yorkshire", "The last coal miners of Yorkshire"),
    ("the-fall-of-silicon-valley-bank", "The fall of Silicon Valley Bank"),
    ("how-to-save-the-amazon", "How to save the Amazon rainforest"),
    ("the-rise-of-the-influencer-economy", "The rise of the influencer economy"),
    ("the-women-who-broke-bletchley", "The women who broke Bletchley"),
    ("the-children-left-behind-in-mariupol", "The children left behind in Mariupol"),
    ("the-quiet-extinction", "The quiet extinction of British insects"),
    ("inside-the-arctic-doomsday-vault", "Inside the Arctic Doomsday Vault"),
]

PROGRAMMES = [
    ("b006q2x0", "Doctor Who", "BBC One", "Sci-fi adventure", 2005, 13, 50),
    ("b007jzkn", "Top Gear", "BBC Two", "Motoring entertainment", 2002, 33, 60),
    ("b006mf4f", "EastEnders", "BBC One", "London soap opera", 1985, 39, 30),
    ("b006m86d", "QI", "BBC Two", "Comedy panel quiz", 2003, 21, 30),
    ("b006v5tb", "The Great British Bake Off", "BBC One", "Baking competition", 2010, 14, 75),
    ("b006wkqw", "Strictly Come Dancing", "BBC One", "Celebrity ballroom dancing", 2004, 21, 90),
    ("b0071b63", "Mastermind", "BBC Two", "Quiz show", 1972, 50, 30),
    ("b006q5sf", "Antiques Roadshow", "BBC One", "Antique valuations", 1979, 46, 60),
    ("b00644nk", "Newsnight", "BBC Two", "Current affairs", 1980, 44, 45),
    ("b006q5kf", "Match of the Day", "BBC One", "Football highlights", 1964, 60, 90),
    ("b006v9dv", "Question Time", "BBC One", "Political debate", 1979, 45, 60),
    ("b006q2y0", "MasterChef", "BBC One", "Cooking competition", 2005, 19, 60),
]

BITESIZE_SUBJECTS = [
    ("maths", "Maths", "KS2, KS3, GCSE, A-Level"),
    ("english", "English", "KS2, KS3, GCSE, A-Level"),
    ("science", "Science", "KS2, KS3, GCSE, A-Level"),
    ("history", "History", "KS3, GCSE, A-Level"),
    ("geography", "Geography", "KS3, GCSE, A-Level"),
    ("french", "French", "KS3, GCSE"),
    ("spanish", "Spanish", "KS3, GCSE"),
    ("computer-science", "Computer Science", "KS3, GCSE, A-Level"),
    ("religious-studies", "Religious Studies", "KS3, GCSE"),
    ("physics", "Physics", "GCSE, A-Level"),
    ("chemistry", "Chemistry", "GCSE, A-Level"),
    ("biology", "Biology", "GCSE, A-Level"),
]

MARKET_INDICES = [
    ("ftse-100", "FTSE 100", "London", "GBP", 7800, 8200),
    ("ftse-250", "FTSE 250", "London", "GBP", 19000, 20500),
    ("dow-jones", "Dow Jones", "New York", "USD", 38000, 41000),
    ("nasdaq", "Nasdaq Composite", "New York", "USD", 16000, 18500),
    ("sp-500", "S&P 500", "New York", "USD", 5000, 5500),
    ("nikkei-225", "Nikkei 225", "Tokyo", "JPY", 36000, 41000),
    ("dax", "DAX", "Frankfurt", "EUR", 17000, 19000),
    ("cac-40", "CAC 40", "Paris", "EUR", 7400, 8200),
    ("hang-seng", "Hang Seng", "Hong Kong", "HKD", 16000, 19000),
    ("ibex-35", "IBEX 35", "Madrid", "EUR", 10000, 11500),
]

COMPANIES = [
    ("AAPL", "Apple Inc.", "Nasdaq", "USD", "Consumer Electronics"),
    ("MSFT", "Microsoft Corporation", "Nasdaq", "USD", "Software"),
    ("GOOGL", "Alphabet Inc.", "Nasdaq", "USD", "Internet"),
    ("AMZN", "Amazon.com Inc.", "Nasdaq", "USD", "E-commerce"),
    ("TSLA", "Tesla Inc.", "Nasdaq", "USD", "Automotive"),
    ("NVDA", "NVIDIA Corporation", "Nasdaq", "USD", "Semiconductors"),
    ("META", "Meta Platforms Inc.", "Nasdaq", "USD", "Social Media"),
    ("HSBA.L", "HSBC Holdings plc", "LSE", "GBP", "Banking"),
    ("BP.L", "BP plc", "LSE", "GBP", "Oil & Gas"),
    ("SHEL.L", "Shell plc", "LSE", "GBP", "Oil & Gas"),
    ("AZN.L", "AstraZeneca plc", "LSE", "GBP", "Pharmaceuticals"),
    ("ULVR.L", "Unilever plc", "LSE", "GBP", "Consumer Goods"),
    ("BARC.L", "Barclays plc", "LSE", "GBP", "Banking"),
    ("VOD.L", "Vodafone Group plc", "LSE", "GBP", "Telecommunications"),
]


# --------------------------------------------------------------------- #
# Page-specific builders                                                 #
# --------------------------------------------------------------------- #

def build_sport_hub(sport_key: str):
    sport_map = {s[0]: s for s in SPORTS}
    if sport_key not in sport_map:
        return None
    _, sport_label, _ = sport_map[sport_key]
    h = _gui_seed("gui", "sport_hub", sport_key)

    headlines_pool = {
        "football": [
            "Manchester City clinch fourth consecutive Premier League title",
            "Arsenal in talks to sign Spanish midfielder",
            "Liverpool announce new manager",
            "England squad named for World Cup qualifiers",
            "Champions League final preview: tactical analysis",
        ],
        "cricket": [
            "England beat Australia in dramatic Ashes Test",
            "Joe Root scores double century at Lord's",
            "The Hundred 2026 fixtures revealed",
            "India announce T20 World Cup squad",
            "Ben Stokes returns to ODI captaincy",
        ],
        "rugby-union": [
            "England retain Six Nations title with Grand Slam",
            "Saracens crowned Premiership champions",
            "Springboks announce World Cup squad",
            "Marcus Smith named Player of the Year",
            "Ireland top World Rugby rankings",
        ],
        "tennis": [
            "Alcaraz wins fourth Grand Slam at Wimbledon",
            "Swiatek extends WTA world number one streak",
            "Djokovic announces retirement at end of season",
            "Andy Murray plays final ATP tournament",
            "Roland Garros 2026 draw revealed",
        ],
        "formula1": [
            "Verstappen wins Monaco Grand Prix",
            "Hamilton finishes second in Mercedes farewell race",
            "McLaren extend constructors' championship lead",
            "Norris claims maiden pole position at Silverstone",
            "Ferrari announce 2027 driver lineup",
        ],
        "olympics": [
            "Team GB win 65 medals at Paris 2024",
            "Adam Peaty wins fourth Olympic gold",
            "Keely Hodgkinson takes 800m gold in Paris",
            "USA top medal table with 126 medals",
            "Brisbane 2032 venues unveiled",
        ],
        "american-football": [
            "Chiefs win Super Bowl LIX in overtime",
            "Mahomes named Super Bowl MVP for fourth time",
            "NFL Draft 2026: first-round predictions",
            "49ers extend Brock Purdy to five-year contract",
            "Tom Brady inducted into Pro Football Hall of Fame",
        ],
        "boxing": [
            "Fury vs Usyk II ends in split decision",
            "Anthony Joshua announces comeback fight",
            "Canelo Alvarez to defend titles in Las Vegas",
            "Naoya Inoue unifies bantamweight division",
            "Tyson Fury hangs up gloves after Usyk rematch",
        ],
    }
    headlines = headlines_pool.get(sport_key, [])
    if not headlines:
        headlines = [f"{sport_label} headline {i}" for i in range(5)]

    if sport_key == "football":
        teams = PREMIER_LEAGUE_TEAMS
        league = "Premier League"
        next_fixture = f"{teams[int(h[:2], 16) % len(teams)]} v {teams[(int(h[:2], 16) + 3) % len(teams)]}"
    elif sport_key == "cricket":
        teams = CRICKET_TEAMS
        league = "England Tests"
        next_fixture = f"{teams[int(h[:2], 16) % len(teams)]} v {teams[(int(h[:2], 16) + 2) % len(teams)]}"
    elif sport_key == "rugby-union":
        teams = RUGBY_PREMIERSHIP
        league = "Gallagher Premiership"
        next_fixture = f"{teams[int(h[:2], 16) % len(teams)]} v {teams[(int(h[:2], 16) + 2) % len(teams)]}"
    elif sport_key == "tennis":
        teams = ATP_PLAYERS
        league = "ATP Tour"
        next_fixture = f"{teams[int(h[:2], 16) % len(teams)]} v {teams[(int(h[:2], 16) + 1) % len(teams)]}"
    elif sport_key == "formula1":
        teams = [d[0] for d in F1_DRIVERS]
        league = "F1 Championship"
        next_fixture = f"{F1_CIRCUITS[int(h[:2], 16) % len(F1_CIRCUITS)][0]}"
    elif sport_key == "olympics":
        teams = OLYMPICS_NATIONS
        league = "Olympics medal table"
        next_fixture = "Athletics 100m final"
    elif sport_key == "american-football":
        teams = NFL_TEAMS
        league = "NFL"
        next_fixture = f"{teams[int(h[:2], 16) % len(teams)]} v {teams[(int(h[:2], 16) + 4) % len(teams)]}"
    else:  # boxing
        teams = BOXING_FIGHTERS
        league = "Heavyweight Title"
        next_fixture = f"{teams[int(h[:2], 16) % len(teams)]} v {teams[(int(h[:2], 16) + 1) % len(teams)]}"

    return {
        "sport_key": sport_key,
        "sport_label": sport_label,
        "league_label": league,
        "headlines": [
            {"slot": i + 1, "headline": hd,
             "summary": f"Latest in {sport_label}: {hd[:60]}...",
             "minutes_ago": 10 + (i * 27)}
            for i, hd in enumerate(headlines)
        ],
        "teams": teams[:12],
        "next_fixture": next_fixture,
        "next_kickoff": (GUI_REFERENCE_DATE + timedelta(days=int(h[4:6], 16) % 7)).strftime("%a %d %b %H:%M"),
        "top_scorer": teams[int(h[6:8], 16) % len(teams)],
        "top_scorer_count": 10 + (int(h[8:10], 16) % 18),
        "ref_date": GUI_REFERENCE_DATE.strftime("%a %d %B %Y"),
    }


def build_sport_scoreboard(sport: str, date_str: str):
    sport_map = {s[0]: s for s in SPORTS}
    if sport not in sport_map:
        return None
    _, sport_label, _ = sport_map[sport]
    h = _gui_seed("gui", "scoreboard", sport, date_str)

    if sport == "football":
        pool, comp = PREMIER_LEAGUE_TEAMS, "Premier League"
    elif sport == "cricket":
        pool, comp = CRICKET_TEAMS, "International Test"
    elif sport == "rugby-union":
        pool, comp = RUGBY_PREMIERSHIP, "Gallagher Premiership"
    elif sport == "tennis":
        pool, comp = ATP_PLAYERS, "ATP 1000"
    elif sport == "formula1":
        pool, comp = [d[0] for d in F1_DRIVERS], "F1 Grand Prix"
    elif sport == "olympics":
        pool, comp = OLYMPICS_NATIONS, "Athletics"
    elif sport == "american-football":
        pool, comp = NFL_TEAMS, "NFL Regular Season"
    else:
        pool, comp = BOXING_FIGHTERS, "Heavyweight Title"

    fixtures = []
    for i in range(8):
        seg = _gui_seed(h, "match", i)
        a_idx = int(seg[0:2], 16) % len(pool)
        b_idx = (a_idx + 1 + int(seg[2:4], 16) % (len(pool) - 1)) % len(pool)
        hs = int(seg[4:6], 16) % 5
        as_ = int(seg[6:8], 16) % 5
        status_pool = ["FT", "FT", "FT", "Half-time", "Live 67'", "Live 23'", "FT", "Postponed"]
        fixtures.append({
            "match_id": f"gui-{sport}-{date_str}-{i:02d}",
            "home": pool[a_idx],
            "away": pool[b_idx],
            "home_score": hs,
            "away_score": as_,
            "status": status_pool[i % len(status_pool)],
            "kickoff_time": f"{12 + i:02d}:{(int(seg[8:10], 16) % 6)*10:02d}",
            "venue": f"{pool[a_idx]} Stadium",
        })

    return {
        "sport_key": sport,
        "sport_label": sport_label,
        "date_str": date_str,
        "competition": comp,
        "fixtures": fixtures,
        "total_matches": len(fixtures),
    }


def build_sport_standings(sport: str, league: str):
    h = _gui_seed("gui", "standings", sport, league)
    if sport == "football":
        if league == "la-liga":
            teams = LA_LIGA_TEAMS
            league_label = "La Liga"
        else:
            teams = PREMIER_LEAGUE_TEAMS
            league_label = "Premier League" if league == "premier-league" else league.replace("-", " ").title()
    elif sport == "cricket":
        teams = THE_HUNDRED_TEAMS if league == "the-hundred" else CRICKET_TEAMS
        league_label = league.replace("-", " ").title()
    elif sport == "rugby-union":
        teams = SIX_NATIONS if league == "six-nations" else RUGBY_PREMIERSHIP
        league_label = "Six Nations" if league == "six-nations" else "Gallagher Premiership"
    elif sport == "formula1":
        teams = [d[0] for d in F1_DRIVERS]
        league_label = "F1 Drivers' Standings"
    elif sport == "american-football":
        teams = NFL_TEAMS
        league_label = "NFL AFC" if league == "afc" else "NFL NFC"
    else:
        teams = OLYMPICS_NATIONS
        league_label = "Medal table"

    rows = []
    # Stable shuffle by md5 ordering
    keyed = sorted(teams, key=lambda t: _gui_seed(h, t))
    for i, t in enumerate(keyed):
        seg = _gui_seed(h, "row", i)
        played = 28 + (int(seg[:2], 16) % 12)
        won = (played * (30 + int(seg[2:4], 16) % 60)) // 100
        drawn = (played - won) // 2
        lost = played - won - drawn
        gf = won * 2 + drawn
        ga = lost * 2 + drawn // 2
        points = won * 3 + drawn
        rows.append({
            "rank": i + 1,
            "team": t,
            "played": played,
            "won": won,
            "drawn": drawn,
            "lost": lost,
            "goals_for": gf,
            "goals_against": ga,
            "goal_difference": gf - ga,
            "points": points,
        })
    rows.sort(key=lambda r: (-r["points"], -r["goal_difference"], r["team"]))
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return {
        "sport_key": sport,
        "league_slug": league,
        "league_label": league_label,
        "rows": rows,
        "season": "2025/26",
    }


def build_sport_team(sport: str, team_id: str):
    h = _gui_seed("gui", "team", sport, team_id)
    team_name = team_id.replace("-", " ").title()
    venue_pool = ["Emirates Stadium", "Old Trafford", "Anfield", "Stamford Bridge",
                  "Etihad Stadium", "Tottenham Hotspur Stadium", "St James' Park",
                  "Villa Park", "Goodison Park", "Craven Cottage"]
    return {
        "sport_key": sport,
        "team_id": team_id,
        "team_name": team_name,
        "founded": 1880 + (int(h[:2], 16) % 110),
        "manager": ["Pep Guardiola", "Mikel Arteta", "Jurgen Klopp",
                    "Erik ten Hag", "Mauricio Pochettino", "Ange Postecoglou",
                    "Eddie Howe", "Unai Emery", "Sean Dyche"][int(h[2:4], 16) % 9],
        "captain": ["Bruno Fernandes", "Martin Odegaard", "Virgil van Dijk",
                    "Harry Kane", "Kevin De Bruyne", "James Maddison"][int(h[4:6], 16) % 6],
        "venue": venue_pool[int(h[6:8], 16) % len(venue_pool)],
        "capacity": 25000 + (int(h[8:10], 16) % 50000),
        "league_position": 1 + (int(h[10:12], 16) % 20),
        "trophies_total": int(h[12:14], 16) % 30,
        "squad_size": 22 + (int(h[14:16], 16) % 10),
        "founded_country": "England",
        "form": "WWDLW",
        "next_fixture": f"{team_name} v {venue_pool[int(h[16:18], 16) % len(venue_pool)].split()[0]} FC",
        "kit_color": "#" + h[18:24],
    }


def build_sport_fixtures(sport: str):
    h = _gui_seed("gui", "fixtures", sport)
    fixtures = []
    pool = PREMIER_LEAGUE_TEAMS if sport == "football" else CRICKET_TEAMS
    for i in range(12):
        seg = _gui_seed(h, "fx", i)
        d = (GUI_REFERENCE_DATE + timedelta(days=i // 2)).strftime("%a %d %b")
        a = pool[int(seg[:2], 16) % len(pool)]
        b = pool[(int(seg[:2], 16) + 5) % len(pool)]
        fixtures.append({
            "date": d,
            "kickoff": f"{(15 + i % 5):02d}:00",
            "home": a,
            "away": b,
            "competition": "Premier League" if sport == "football" else "T20",
            "venue": f"{a} Stadium",
        })
    return {"sport_key": sport, "fixtures": fixtures,
            "sport_label": next((s[1] for s in SPORTS if s[0] == sport), sport.title())}


def build_sport_results(sport: str):
    h = _gui_seed("gui", "results", sport)
    pool = PREMIER_LEAGUE_TEAMS if sport == "football" else CRICKET_TEAMS
    results = []
    for i in range(12):
        seg = _gui_seed(h, "res", i)
        d = (GUI_REFERENCE_DATE - timedelta(days=i + 1)).strftime("%a %d %b")
        a = pool[int(seg[:2], 16) % len(pool)]
        b = pool[(int(seg[:2], 16) + 7) % len(pool)]
        results.append({
            "date": d,
            "home": a,
            "away": b,
            "home_score": int(seg[2:4], 16) % 5,
            "away_score": int(seg[4:6], 16) % 5,
            "competition": "Premier League" if sport == "football" else "T20",
        })
    return {"sport_key": sport, "results": results,
            "sport_label": next((s[1] for s in SPORTS if s[0] == sport), sport.title())}


def build_sport_live_blog(sport: str, event_id: str):
    h = _gui_seed("gui", "live_blog", sport, event_id)
    pool = PREMIER_LEAGUE_TEAMS if sport == "football" else CRICKET_TEAMS
    a = pool[int(h[:2], 16) % len(pool)]
    b = pool[(int(h[:2], 16) + 3) % len(pool)]
    minute = 1 + (int(h[2:4], 16) % 90)
    updates = []
    for i in range(20):
        seg = _gui_seed(h, "u", i)
        m = max(1, minute - i * 4)
        events = ["Goal!", "Yellow card", "Corner", "Substitution",
                  "Free kick", "Saved", "Offside", "Penalty appeal", "Booking"]
        updates.append({
            "minute": m,
            "event": events[int(seg[:2], 16) % len(events)],
            "team": a if i % 2 == 0 else b,
            "detail": f"Update {i + 1} in the match between {a} and {b}.",
        })
    return {
        "sport_key": sport,
        "event_id": event_id,
        "home": a, "away": b,
        "home_score": int(h[4:6], 16) % 4,
        "away_score": int(h[6:8], 16) % 4,
        "current_minute": minute,
        "updates": updates,
        "venue": f"{a} Stadium",
        "competition": "Premier League" if sport == "football" else "Test Match",
    }


def build_weather_forecast(loc: str):
    city_map = {c[0]: c for c in UK_CITIES}
    if loc in city_map:
        slug, name, base_lo, base_hi, _ = city_map[loc]
        country = "United Kingdom"
    else:
        wm = {c[0]: c for c in WORLD_CITIES}
        if loc not in wm:
            return None
        slug, name, country, base_lo, base_hi = wm[loc]
    h = _gui_seed("gui", "weather_forecast", loc)
    current_temp = base_lo + (int(h[:2], 16) % max(1, (base_hi - base_lo + 1)))
    conditions_pool = ["Sunny", "Partly cloudy", "Cloudy", "Light rain",
                       "Heavy rain", "Showers", "Drizzle", "Thunderstorm",
                       "Snow", "Mist", "Fog", "Windy"]
    sunrise = f"{5 + int(h[8:10], 16) % 2:02d}:{10 + int(h[10:12], 16) % 50:02d}"
    sunset = f"{19 + int(h[12:14], 16) % 2:02d}:{10 + int(h[14:16], 16) % 50:02d}"
    forecast = []
    for i in range(7):
        seg = _gui_seed(h, "day", i)
        hi = base_lo + (int(seg[:2], 16) % max(1, (base_hi - base_lo + 4)))
        lo = max(base_lo - 4, hi - 5 - (int(seg[2:4], 16) % 6))
        forecast.append({
            "day_name": (GUI_REFERENCE_DATE + timedelta(days=i)).strftime("%A"),
            "day_short": (GUI_REFERENCE_DATE + timedelta(days=i)).strftime("%a"),
            "date_label": (GUI_REFERENCE_DATE + timedelta(days=i)).strftime("%d %b"),
            "high_c": hi, "low_c": lo,
            "condition": conditions_pool[int(seg[4:6], 16) % len(conditions_pool)],
            "rain_chance": int(seg[6:8], 16) % 100,
            "wind_kph": 5 + (int(seg[8:10], 16) % 35),
            "uv_index": int(seg[10:12], 16) % 11,
        })
    return {
        "location_slug": slug, "location_name": name, "country": country,
        "current_temp_c": current_temp,
        "current_temp_f": int(current_temp * 9 / 5 + 32),
        "current_condition": conditions_pool[int(h[2:4], 16) % len(conditions_pool)],
        "feels_like_c": current_temp - 2 + (int(h[4:6], 16) % 5),
        "wind_kph": 5 + (int(h[6:8], 16) % 40),
        "wind_direction": ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][int(h[8:10], 16) % 8],
        "humidity_pct": 30 + (int(h[10:12], 16) % 60),
        "uv_index": int(h[12:14], 16) % 11,
        "pollen_level": ["Low", "Moderate", "High", "Very high"][int(h[14:16], 16) % 4],
        "pressure_mb": 990 + (int(h[16:18], 16) % 40),
        "visibility_km": 5 + (int(h[18:20], 16) % 25),
        "sunrise": sunrise, "sunset": sunset,
        "forecast": forecast,
        "ref_date": GUI_REFERENCE_DATE.strftime("%a %d %B %Y"),
    }


def build_weather_world():
    rows = []
    for slug, name, country, base_lo, base_hi in WORLD_CITIES:
        h = _gui_seed("gui", "weather_world", slug)
        temp = base_lo + (int(h[:2], 16) % max(1, base_hi - base_lo + 1))
        rows.append({
            "slug": slug, "name": name, "country": country,
            "temp_c": temp,
            "condition": ["Sunny", "Cloudy", "Rain", "Storm",
                          "Snow", "Fog", "Clear"][int(h[2:4], 16) % 7],
            "humidity": 30 + (int(h[4:6], 16) % 60),
            "wind_kph": 5 + (int(h[6:8], 16) % 30),
        })
    return {"cities": rows,
            "ref_date": GUI_REFERENCE_DATE.strftime("%a %d %B %Y"),
            "total_cities": len(rows)}


def build_weather_uk():
    rows = []
    for slug, name, base_lo, base_hi, hot in UK_CITIES:
        h = _gui_seed("gui", "weather_uk", slug)
        temp = base_lo + (int(h[:2], 16) % max(1, base_hi - base_lo + 1))
        rows.append({
            "slug": slug, "name": name,
            "temp_c": temp,
            "condition": ["Sunny", "Cloudy", "Light rain", "Showers",
                          "Mist", "Clear", "Partly cloudy"][int(h[2:4], 16) % 7],
            "rain_chance": int(h[4:6], 16) % 100,
            "wind_kph": 5 + (int(h[6:8], 16) % 30),
        })
    return {"cities": rows,
            "ref_date": GUI_REFERENCE_DATE.strftime("%a %d %B %Y"),
            "country": "United Kingdom"}


def build_iplayer_episode(ep_id: str):
    cat_for = None
    show_meta = None
    for cat_slug, cat_label, shows in IPLAYER_CATEGORIES:
        for slug, name, lead, seasons, dur in shows:
            if slug == ep_id:
                cat_for = (cat_slug, cat_label)
                show_meta = (slug, name, lead, seasons, dur)
                break
        if show_meta:
            break
    if not show_meta:
        return None
    slug, name, lead, seasons, dur = show_meta
    h = _gui_seed("gui", "iplayer_ep", ep_id)
    episodes = []
    for i in range(min(8, seasons * 6)):
        seg = _gui_seed(h, "ep", i)
        episodes.append({
            "season": (i // 6) + 1, "episode": (i % 6) + 1,
            "title": f"{name} - Series {(i // 6) + 1} Episode {(i % 6) + 1}",
            "duration_min": dur + (int(seg[:2], 16) % 5) - 2,
            "synopsis": f"Series {(i // 6) + 1}, Episode {(i % 6) + 1} of {name}.",
            "first_broadcast": (GUI_REFERENCE_DATE - timedelta(days=14 + i * 7)).strftime("%d %b %Y"),
        })
    return {
        "show_id": slug, "show_name": name, "lead_actor": lead,
        "category_slug": cat_for[0], "category_label": cat_for[1],
        "total_seasons": seasons, "duration_per_episode": dur,
        "episodes": episodes,
        "rating_pct": 75 + (int(h[:2], 16) % 25),
        "age_rating": ["U", "PG", "12", "15", "18"][int(h[2:4], 16) % 5],
        "available_until": (GUI_REFERENCE_DATE + timedelta(days=180)).strftime("%d %b %Y"),
    }


def build_iplayer_category(cat_slug: str):
    cm = {c[0]: c for c in IPLAYER_CATEGORIES}
    if cat_slug not in cm:
        return None
    _, cat_label, shows = cm[cat_slug]
    return {
        "category_slug": cat_slug, "category_label": cat_label,
        "shows": [
            {"id": s[0], "name": s[1], "lead": s[2],
             "seasons": s[3], "episode_min": s[4]}
            for s in shows
        ],
        "total_shows": len(shows),
    }


def build_iplayer_schedule(channel: str, date_str: str):
    cm = {c[0]: c for c in TV_CHANNELS}
    if channel not in cm:
        return None
    _, channel_label = cm[channel]
    h = _gui_seed("gui", "iplayer_schedule", channel, date_str)
    all_shows = [s for _, _, shows in IPLAYER_CATEGORIES for s in shows]
    schedule = []
    times = ["06:00", "07:30", "09:00", "11:00", "13:00", "14:30",
            "16:00", "18:00", "19:30", "21:00", "22:30", "23:45"]
    for i, t in enumerate(times):
        seg = _gui_seed(h, "slot", i)
        s = all_shows[int(seg[:4], 16) % len(all_shows)]
        schedule.append({
            "time": t,
            "title": s[1],
            "duration_min": s[4] + (int(seg[4:6], 16) % 10) - 5,
            "synopsis": f"{s[1]} - tonight's edition.",
            "lead": s[2],
        })
    return {
        "channel_slug": channel, "channel_label": channel_label,
        "date_str": date_str, "schedule": schedule,
    }


def build_sounds_podcast(slug: str):
    pm = {p[0]: p for p in PODCASTS}
    if slug not in pm:
        return None
    _, name, host, desc, schedule, dur = pm[slug]
    h = _gui_seed("gui", "podcast", slug)
    episodes = []
    for i in range(12):
        seg = _gui_seed(h, "ep", i)
        episodes.append({
            "episode_num": 100 - i,
            "title": f"{name} - Episode {100 - i}",
            "duration_min": dur + (int(seg[:2], 16) % 8) - 4,
            "published": (GUI_REFERENCE_DATE - timedelta(days=i * 3)).strftime("%d %b %Y"),
            "summary": f"Episode {100 - i} covers the latest stories.",
        })
    return {
        "podcast_slug": slug, "podcast_name": name,
        "host": host, "description": desc, "schedule": schedule,
        "duration_per_ep": dur, "total_episodes_listed": 100,
        "episodes": episodes,
        "subscribers": 100000 + (int(h[:4], 16) % 500000),
        "average_rating": 4.0 + (int(h[4:6], 16) % 10) / 10.0,
    }


def build_sounds_live(station: str):
    sm = {s[0]: s for s in LIVE_STATIONS}
    if station not in sm:
        return None
    _, name, tagline = sm[station]
    h = _gui_seed("gui", "live", station)
    now_dj_pool = ["Greg James", "Scott Mills", "Annie Mac", "Lauren Laverne",
                   "Ken Bruce", "Steve Wright", "Trevor Nelson",
                   "Mark Goodier", "Sara Cox", "Tony Blackburn"]
    now_track_pool = [
        ("Levitating", "Dua Lipa"),
        ("Espresso", "Sabrina Carpenter"),
        ("As It Was", "Harry Styles"),
        ("Anti-Hero", "Taylor Swift"),
        ("Bad Habit", "Steve Lacy"),
        ("Flowers", "Miley Cyrus"),
        ("Kill Bill", "SZA"),
        ("Unholy", "Sam Smith"),
    ]
    coming_up = []
    for i in range(6):
        seg = _gui_seed(h, "up", i)
        coming_up.append({
            "time": f"{(11 + i * 2) % 24:02d}:00",
            "show": f"{now_dj_pool[int(seg[:2], 16) % len(now_dj_pool)]} on {name}",
            "duration_min": 60 + (int(seg[2:4], 16) % 60),
        })
    now_track = now_track_pool[int(h[:2], 16) % len(now_track_pool)]
    return {
        "station_slug": station, "station_name": name, "tagline": tagline,
        "now_dj": now_dj_pool[int(h[2:4], 16) % len(now_dj_pool)],
        "now_track_title": now_track[0],
        "now_track_artist": now_track[1],
        "now_show_title": f"The {now_dj_pool[int(h[4:6], 16) % len(now_dj_pool)].split()[0]} Show",
        "listener_count": 10000 + (int(h[6:10], 16) % 90000),
        "coming_up": coming_up,
        "stream_quality_kbps": 320,
    }


def build_news_pictures(event_slug: str):
    em = {e[0]: e for e in NEWS_PICTURES_EVENTS}
    if event_slug not in em:
        return None
    _, title, location = em[event_slug]
    h = _gui_seed("gui", "pictures", event_slug)
    images = []
    for i in range(15):
        seg = _gui_seed(h, "img", i)
        images.append({
            "image_id": f"img-{event_slug}-{i + 1:02d}",
            "caption": f"Picture {i + 1}: a moment from {title}.",
            "photographer": ["Reuters", "AFP", "PA Media", "Getty Images",
                             "AP", "BBC"][int(seg[:2], 16) % 6],
            "credit": ["Reuters", "AFP", "PA Media", "Getty Images",
                       "AP", "BBC"][int(seg[:2], 16) % 6],
        })
    return {
        "event_slug": event_slug, "event_title": title,
        "event_location": location,
        "images": images, "total_images": len(images),
        "published": GUI_REFERENCE_DATE.strftime("%d %B %Y"),
    }


def build_news_explainer(slug: str):
    em = {e[0]: e for e in NEWS_EXPLAINERS}
    if slug not in em:
        return None
    _, title = em[slug]
    h = _gui_seed("gui", "explainer", slug)
    sections = []
    sec_titles = ["Introduction", "Background", "Key facts", "How it works",
                  "Who is affected", "What happens next", "Sources"]
    for i, t in enumerate(sec_titles):
        seg = _gui_seed(h, "sec", i)
        sections.append({
            "anchor": f"section-{i + 1}", "title": t,
            "word_count": 80 + (int(seg[:2], 16) % 200),
        })
    sources = [
        "Office for National Statistics", "Bank of England",
        "BBC Reality Check", "UK Government", "World Bank", "Reuters",
    ]
    return {
        "explainer_slug": slug, "explainer_title": title,
        "sections": sections, "total_sections": len(sections),
        "sources": sources, "reading_time_min": 6 + (int(h[:2], 16) % 5),
        "author": "BBC Reality Check team",
        "published": GUI_REFERENCE_DATE.strftime("%d %B %Y"),
    }


def build_news_longform(slug: str):
    em = {e[0]: e for e in NEWS_LONGFORM}
    if slug not in em:
        return None
    _, title = em[slug]
    h = _gui_seed("gui", "longform", slug)
    chapters = []
    ch_titles = ["The beginning", "First encounter", "The investigation",
                 "Turning point", "Revelations", "Conflict", "Resolution",
                 "Aftermath", "Legacy"]
    for i, t in enumerate(ch_titles):
        seg = _gui_seed(h, "ch", i)
        chapters.append({
            "anchor": f"chapter-{i + 1}", "title": t,
            "word_count": 600 + (int(seg[:2], 16) % 800),
        })
    return {
        "longform_slug": slug, "longform_title": title,
        "chapters": chapters, "total_chapters": len(chapters),
        "total_words": sum(c["word_count"] for c in chapters),
        "reading_time_min": sum(c["word_count"] for c in chapters) // 200,
        "author": ["Sarah Rainsford", "John Simpson", "Lyse Doucet",
                   "Orla Guerin", "Jeremy Bowen"][int(h[:2], 16) % 5],
        "published": GUI_REFERENCE_DATE.strftime("%d %B %Y"),
    }


def build_programme(pid: str):
    pm = {p[0]: p for p in PROGRAMMES}
    if pid not in pm:
        return None
    _, name, channel, genre, year, series, dur = pm[pid]
    h = _gui_seed("gui", "programme", pid)
    return {
        "programme_id": pid, "programme_name": name,
        "channel": channel, "genre": genre,
        "first_year": year, "total_series": series,
        "episode_duration_min": dur,
        "total_episodes": series * (6 + int(h[:2], 16) % 12),
        "average_viewers_m": 1.0 + (int(h[2:4], 16) % 70) / 10.0,
        "official_site": f"https://www.bbc.co.uk/programmes/{pid}",
        "available_on_iplayer": True,
        "category_tag": genre,
    }


def build_bitesize(subject: str):
    sm = {s[0]: s for s in BITESIZE_SUBJECTS}
    if subject not in sm:
        return None
    _, label, levels = sm[subject]
    h = _gui_seed("gui", "bitesize", subject)
    topics_pool = {
        "maths": ["Algebra", "Geometry", "Statistics", "Probability",
                  "Trigonometry", "Calculus", "Number", "Ratio"],
        "english": ["Reading", "Writing", "Grammar", "Literature",
                    "Poetry", "Shakespeare", "Drama", "Speaking"],
        "science": ["Forces", "Materials", "Living things", "Earth",
                    "Energy", "Electricity", "Plants", "Ecosystems"],
        "history": ["Ancient Egypt", "Tudors", "Victorians", "WWI",
                    "WWII", "Cold War", "Industrial Revolution", "Romans"],
        "geography": ["Rivers", "Mountains", "Climate", "Population",
                      "Tectonics", "Urbanisation", "Tourism", "Glaciers"],
        "french": ["Salutations", "Family", "School", "Free time",
                   "Food", "Holidays", "Future tense", "Past tense"],
        "spanish": ["Saludos", "Familia", "Escuela", "Tiempo libre",
                    "Comida", "Vacaciones", "Futuro", "Preterito"],
        "computer-science": ["Algorithms", "Programming", "Data structures",
                             "Computer systems", "Networks", "Cyber security",
                             "Databases", "Logic gates"],
        "religious-studies": ["Christianity", "Islam", "Judaism", "Hinduism",
                              "Buddhism", "Sikhism", "Ethics", "Philosophy"],
        "physics": ["Forces", "Energy", "Waves", "Electricity",
                    "Magnetism", "Atomic structure", "Particle physics",
                    "Thermodynamics"],
        "chemistry": ["Atomic structure", "Bonding", "Quantitative",
                      "Reactions", "Organic", "Energy changes",
                      "Rate of reaction", "Periodic table"],
        "biology": ["Cell biology", "Organisation", "Infection",
                    "Bioenergetics", "Homeostasis", "Inheritance",
                    "Evolution", "Ecology"],
    }
    topics = topics_pool.get(subject, [f"Topic {i}" for i in range(8)])
    guide_count = 4 + int(h[:2], 16) % 6
    guides = []
    for i, t in enumerate(topics):
        seg = _gui_seed(h, "g", i)
        guides.append({
            "topic_slug": t.lower().replace(" ", "-"),
            "topic_name": t,
            "level": levels.split(",")[i % len(levels.split(","))].strip(),
            "guide_count": 3 + (int(seg[:2], 16) % 6),
        })
    return {
        "subject_slug": subject, "subject_label": label,
        "levels_label": levels, "topics": guides,
        "total_topics": len(guides),
        "exam_boards": ["AQA", "Edexcel", "OCR", "WJEC"][:1 + int(h[2:4], 16) % 4],
    }


def build_region(region_slug: str):
    region_meta = {
        "cymru": ("Wales (Cymraeg)", "Cymru", "Cardiff",
                  ["Newyddion", "Chwaraeon", "Hanes", "Diwylliant", "Tywydd"]),
        "scotland": ("Scotland", "Scotland", "Edinburgh",
                     ["News", "Sport", "History", "Politics", "Weather"]),
        "northernireland": ("Northern Ireland", "Northern Ireland", "Belfast",
                             ["News", "Sport", "Politics", "Stormont", "Weather"]),
        "wales": ("Wales", "Wales", "Cardiff",
                  ["News", "Sport", "Politics", "Senedd", "Weather"]),
    }
    if region_slug not in region_meta:
        return None
    region_name, short, capital, sections = region_meta[region_slug]
    h = _gui_seed("gui", "region", region_slug)
    headlines = []
    headline_pool = [
        "First minister addresses parliament on economy",
        "New hospital opens in capital",
        "Sport team wins national cup",
        "Climate change report released",
        "Education reforms announced",
        "Transport infrastructure plan unveiled",
        "Cultural festival breaks attendance record",
        "Local business wins international award",
    ]
    for i, t in enumerate(headline_pool[:8]):
        seg = _gui_seed(h, "hd", i)
        headlines.append({
            "headline": f"{short}: {t}",
            "section": sections[int(seg[:2], 16) % len(sections)],
            "minutes_ago": 5 + i * 13,
        })
    return {
        "region_slug": region_slug, "region_name": region_name,
        "short_name": short, "capital": capital, "sections": sections,
        "headlines": headlines,
        "ref_date": GUI_REFERENCE_DATE.strftime("%a %d %B %Y"),
    }


def build_market(index_slug: str):
    im = {m[0]: m for m in MARKET_INDICES}
    if index_slug not in im:
        return None
    _, name, exchange, currency, base_lo, base_hi = im[index_slug]
    h = _gui_seed("gui", "market", index_slug)
    current = base_lo + (int(h[:4], 16) % max(1, base_hi - base_lo))
    change = (int(h[4:6], 16) - 128)
    change_pct = round(change / 100.0, 2)
    history = []
    for i in range(12):
        seg = _gui_seed(h, "month", i)
        delta = (int(seg[:4], 16) % 800) - 400
        history.append({
            "month": (GUI_REFERENCE_DATE - timedelta(days=i * 30)).strftime("%b %Y"),
            "close": current + delta,
        })
    top_movers = []
    for i in range(6):
        seg = _gui_seed(h, "mv", i)
        comp = COMPANIES[int(seg[:2], 16) % len(COMPANIES)]
        top_movers.append({
            "ticker": comp[0], "name": comp[1],
            "change_pct": round((int(seg[2:6], 16) % 1000 - 500) / 100.0, 2),
        })
    return {
        "index_slug": index_slug, "index_name": name,
        "exchange": exchange, "currency": currency,
        "current_value": current, "change_points": change,
        "change_pct": change_pct, "day_range_lo": current - 50,
        "day_range_hi": current + 50, "year_lo": base_lo,
        "year_hi": base_hi, "history": history, "top_movers": top_movers,
        "ref_date": GUI_REFERENCE_DATE.strftime("%a %d %B %Y"),
    }


def build_company(ticker: str):
    cm = {c[0]: c for c in COMPANIES}
    if ticker not in cm:
        return None
    _, name, exchange, currency, industry = cm[ticker]
    h = _gui_seed("gui", "company", ticker)
    base = 50 + int(h[:4], 16) % 350
    return {
        "ticker": ticker, "company_name": name,
        "exchange": exchange, "currency": currency, "industry": industry,
        "current_price": base,
        "change_points": (int(h[4:6], 16) - 128) / 10.0,
        "change_pct": (int(h[6:8], 16) - 128) / 10.0,
        "market_cap_bn": 10 + (int(h[8:12], 16) % 2000),
        "pe_ratio": 5 + (int(h[12:14], 16) % 40),
        "dividend_yield": (int(h[14:16], 16) % 50) / 10.0,
        "year_high": base + 20 + (int(h[16:18], 16) % 50),
        "year_low": max(1, base - 20 - (int(h[18:20], 16) % 50)),
        "volume_m": 1 + (int(h[20:24], 16) % 200) / 10.0,
        "ceo": ["Tim Cook", "Satya Nadella", "Sundar Pichai", "Andy Jassy",
                "Elon Musk", "Jensen Huang", "Mark Zuckerberg"][int(h[:2], 16) % 7],
        "ref_date": GUI_REFERENCE_DATE.strftime("%a %d %B %Y"),
    }


def build_news_topic(topic: str):
    tm = {t[0]: t for t in NEWS_TOPICS}
    if topic not in tm:
        return None
    _, label = tm[topic]
    h = _gui_seed("gui", "topic", topic)
    articles = []
    for i in range(10):
        seg = _gui_seed(h, "art", i)
        articles.append({
            "title": f"{label}: development {i + 1}",
            "summary": f"The latest on {label} from BBC News correspondents.",
            "author": ["Lyse Doucet", "Frank Gardner", "Laura Kuenssberg",
                       "Chris Mason", "Faisal Islam"][int(seg[:2], 16) % 5],
            "hours_ago": 1 + (int(seg[2:4], 16) % 72),
        })
    return {
        "topic_slug": topic, "topic_label": label,
        "articles": articles, "total_articles": len(articles),
        "followers": 10000 + (int(h[:4], 16) % 500000),
        "ref_date": GUI_REFERENCE_DATE.strftime("%a %d %B %Y"),
    }


# --------------------------------------------------------------------- #
# Page registry — for task generation and route registration            #
# --------------------------------------------------------------------- #

# Page registry: each entry maps a page key to its sample params used by
# task generation. Routes are registered via register(app).

SPORT_KEYS = [s[0] for s in SPORTS]
SPORT_TEAMS_SAMPLE = ["arsenal", "manchester-city", "liverpool", "chelsea",
                      "tottenham", "newcastle", "england", "australia",
                      "leicester-tigers", "saracens"]
SPORT_LEAGUE_SAMPLE = {"football": ["premier-league", "la-liga", "championship"],
                       "cricket": ["the-hundred", "test"],
                       "rugby-union": ["six-nations", "premiership"],
                       "formula1": ["drivers"],
                       "american-football": ["afc", "nfc"],
                       "olympics": ["medals"]}


def _date_sample(offset_days: int = 0):
    return (GUI_REFERENCE_DATE + timedelta(days=offset_days)).strftime("%Y-%m-%d")


def register(app):
    """Register all GUI deepen routes onto the Flask app."""

    @app.route("/sport/<sport>/hub")
    def gui_sport_hub(sport):
        d = build_sport_hub(sport)
        if d is None:
            abort(404)
        # Map each sport_key to its dedicated template (8 templates total).
        tpl_map = {
            "football": "gui_sport_football.html",
            "cricket": "gui_sport_cricket.html",
            "rugby-union": "gui_sport_rugby_union.html",
            "tennis": "gui_sport_tennis.html",
            "formula1": "gui_sport_formula1.html",
            "olympics": "gui_sport_olympics.html",
            "american-football": "gui_sport_american_football.html",
            "boxing": "gui_sport_boxing.html",
        }
        return render_template(tpl_map[sport], data=d, active_nav_slug="sport")

    @app.route("/sport/<sport>/scoreboard/<date_str>")
    def gui_sport_scoreboard(sport, date_str):
        d = build_sport_scoreboard(sport, date_str)
        if d is None:
            abort(404)
        return render_template("gui_sport_scoreboard.html",
                               data=d, active_nav_slug="sport")

    @app.route("/sport/<sport>/standings/<league>")
    def gui_sport_standings(sport, league):
        d = build_sport_standings(sport, league)
        if d is None:
            abort(404)
        return render_template("gui_sport_standings.html",
                               data=d, active_nav_slug="sport")

    @app.route("/sport/<sport>/team/<team_id>")
    def gui_sport_team(sport, team_id):
        d = build_sport_team(sport, team_id)
        if d is None:
            abort(404)
        return render_template("gui_sport_team.html",
                               data=d, active_nav_slug="sport")

    @app.route("/sport/<sport>/fixtures")
    def gui_sport_fixtures(sport):
        d = build_sport_fixtures(sport)
        return render_template("gui_sport_fixtures.html",
                               data=d, active_nav_slug="sport")

    @app.route("/sport/<sport>/results")
    def gui_sport_results(sport):
        d = build_sport_results(sport)
        return render_template("gui_sport_results.html",
                               data=d, active_nav_slug="sport")

    @app.route("/sport/<sport>/live/<event_id>")
    def gui_sport_live_blog(sport, event_id):
        d = build_sport_live_blog(sport, event_id)
        return render_template("gui_sport_live_blog.html",
                               data=d, active_nav_slug="sport")

    @app.route("/weather/forecast/<location>")
    def gui_weather_forecast(location):
        d = build_weather_forecast(location)
        if d is None:
            abort(404)
        return render_template("gui_weather_forecast.html",
                               data=d, active_nav_slug="weather")

    @app.route("/weather/world")
    def gui_weather_world():
        d = build_weather_world()
        return render_template("gui_weather_world.html",
                               data=d, active_nav_slug="weather")

    @app.route("/weather/uk")
    def gui_weather_uk():
        d = build_weather_uk()
        return render_template("gui_weather_uk.html",
                               data=d, active_nav_slug="weather")

    @app.route("/iplayer/show/<ep_id>")
    def gui_iplayer_episode(ep_id):
        d = build_iplayer_episode(ep_id)
        if d is None:
            abort(404)
        return render_template("gui_iplayer_episode.html",
                               data=d, active_nav_slug="audio")

    @app.route("/iplayer/cat/<cat>")
    def gui_iplayer_category(cat):
        d = build_iplayer_category(cat)
        if d is None:
            abort(404)
        return render_template("gui_iplayer_category.html",
                               data=d, active_nav_slug="audio")

    @app.route("/iplayer/schedule/<channel>/<date_str>")
    def gui_iplayer_schedule(channel, date_str):
        d = build_iplayer_schedule(channel, date_str)
        if d is None:
            abort(404)
        return render_template("gui_iplayer_schedule.html",
                               data=d, active_nav_slug="audio")

    @app.route("/sounds/podcast/<slug>")
    def gui_sounds_podcast(slug):
        d = build_sounds_podcast(slug)
        if d is None:
            abort(404)
        return render_template("gui_sounds_podcast.html",
                               data=d, active_nav_slug="audio")

    @app.route("/sounds/live/<station>")
    def gui_sounds_live(station):
        d = build_sounds_live(station)
        if d is None:
            abort(404)
        return render_template("gui_sounds_live.html",
                               data=d, active_nav_slug="audio")

    @app.route("/news/in_pictures/<event_slug>")
    def gui_news_pictures(event_slug):
        d = build_news_pictures(event_slug)
        if d is None:
            abort(404)
        return render_template("gui_news_pictures.html",
                               data=d, active_nav_slug="news")

    @app.route("/news/explainers/<slug>")
    def gui_news_explainer(slug):
        d = build_news_explainer(slug)
        if d is None:
            abort(404)
        return render_template("gui_news_explainer.html",
                               data=d, active_nav_slug="news")

    @app.route("/news/longform/<slug>")
    def gui_news_longform(slug):
        d = build_news_longform(slug)
        if d is None:
            abort(404)
        return render_template("gui_news_longform.html",
                               data=d, active_nav_slug="news")

    @app.route("/programmes/<pid>")
    def gui_programmes(pid):
        d = build_programme(pid)
        if d is None:
            abort(404)
        return render_template("gui_programmes.html",
                               data=d, active_nav_slug="audio")

    @app.route("/bitesize/subjects/<subject>")
    def gui_bitesize_subject(subject):
        d = build_bitesize(subject)
        if d is None:
            abort(404)
        return render_template("gui_bitesize_subject.html",
                               data=d, active_nav_slug="news")

    @app.route("/cymru")
    def gui_region_cymru():
        d = build_region("cymru")
        return render_template("gui_region_cymru.html",
                               data=d, active_nav_slug="news")

    @app.route("/scotland")
    def gui_region_scotland():
        d = build_region("scotland")
        return render_template("gui_region_scotland.html",
                               data=d, active_nav_slug="news")

    @app.route("/northernireland")
    def gui_region_ni():
        d = build_region("northernireland")
        return render_template("gui_region_ni.html",
                               data=d, active_nav_slug="news")

    @app.route("/wales")
    def gui_region_wales():
        d = build_region("wales")
        return render_template("gui_region_wales.html",
                               data=d, active_nav_slug="news")

    @app.route("/business/markets/<idx>")
    def gui_business_market(idx):
        d = build_market(idx)
        if d is None:
            abort(404)
        return render_template("gui_business_market.html",
                               data=d, active_nav_slug="business")

    @app.route("/business/companies/<ticker>")
    def gui_business_company(ticker):
        d = build_company(ticker)
        if d is None:
            abort(404)
        return render_template("gui_business_company.html",
                               data=d, active_nav_slug="business")

    @app.route("/news/topics/<topic>")
    def gui_news_topic(topic):
        d = build_news_topic(topic)
        if d is None:
            abort(404)
        return render_template("gui_news_topic.html",
                               data=d, active_nav_slug="news")
