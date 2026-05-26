"""Seed data for Google Search mirror — R2.
Builds SearchResults by generating plausible variations around each topic's
Wikipedia summary + 4-6 additional simulated results from Britannica, YouTube,
NYTimes, Wikipedia, Reddit, etc. Also seeds trending searches, doodles,
and the Google apps list.
"""
import hashlib
import json
import os
import random
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
TOPICS_JSON = os.path.join(HERE, 'scraped_data', 'topics.json')

# Pinned reference date - every timestamp derives from this so rebuilds are
# byte-identical regardless of wall-clock time. See harden-env/gotchas.
MIRROR_REFERENCE_DATE = datetime(2026, 5, 12, 12, 0, 0)

# Pre-computed bcrypt hashes - random salt in bcrypt.generate_password_hash()
# would shift bytes on every rebuild. See harden-env/gotchas.
PINNED_BENCH_PASSWORD_HASH = '$2b$12$RwAC/sfwDHtccU//A20fde.uKkZK4Ptnjjyua2l2ktwI6uysAp3Ou'  # 'TestPass123!'
PINNED_DEMO_PASSWORD_HASH = '$2b$12$Oi0plj9XBSbuCcjmrSVmje2AWKXN99Xpa7J2O6tjYvquZPTqNXN6i'  # 'test1234'


def _det_hash(s, mod=2**31):
    """Stable string hash - Python's built-in hash() is randomized per
    process unless PYTHONHASHSEED=0. Returns int in [0, mod)."""
    h = hashlib.md5(s.encode('utf-8')).hexdigest()
    return int(h[:8], 16) % mod

# Google verticals — the search-result category tabs.
# Real Google exposes far more than the original 7; expand to cover the
# full real-world surface so navigation queries don't 404.
VERTICALS = [
    {'slug': 'all', 'name': 'All', 'icon': 'search', 'is_default': True, 'sort_order': 0},
    {'slug': 'images', 'name': 'Images', 'icon': 'image', 'is_default': False, 'sort_order': 1},
    {'slug': 'videos', 'name': 'Videos', 'icon': 'play', 'is_default': False, 'sort_order': 2},
    {'slug': 'news', 'name': 'News', 'icon': 'newspaper', 'is_default': False, 'sort_order': 3},
    {'slug': 'maps', 'name': 'Maps', 'icon': 'map', 'is_default': False, 'sort_order': 4},
    {'slug': 'shopping', 'name': 'Shopping', 'icon': 'shopping', 'is_default': False, 'sort_order': 5},
    {'slug': 'books', 'name': 'Books', 'icon': 'book', 'is_default': False, 'sort_order': 6},
    {'slug': 'finance', 'name': 'Finance', 'icon': 'chart', 'is_default': False, 'sort_order': 7},
    {'slug': 'flights', 'name': 'Flights', 'icon': 'plane', 'is_default': False, 'sort_order': 8},
    {'slug': 'hotels', 'name': 'Hotels', 'icon': 'hotel', 'is_default': False, 'sort_order': 9},
    {'slug': 'travel', 'name': 'Travel', 'icon': 'globe', 'is_default': False, 'sort_order': 10},
    {'slug': 'scholar', 'name': 'Scholar', 'icon': 'school', 'is_default': False, 'sort_order': 11},
    {'slug': 'patents', 'name': 'Patents', 'icon': 'badge', 'is_default': False, 'sort_order': 12},
    {'slug': 'recipes', 'name': 'Recipes', 'icon': 'utensils', 'is_default': False, 'sort_order': 13},
    {'slug': 'forums', 'name': 'Forums', 'icon': 'chat', 'is_default': False, 'sort_order': 14},
    {'slug': 'web', 'name': 'Web', 'icon': 'web', 'is_default': False, 'sort_order': 15},
    {'slug': 'podcasts', 'name': 'Podcasts', 'icon': 'mic', 'is_default': False, 'sort_order': 16},
]

# Google apps for the top-right launcher grid
GOOGLE_APPS = [
    ('Search', 'search', '#4285F4', '/'),
    ('Maps', 'map', '#34A853', '/maps'),
    ('Gmail', 'mail', '#EA4335', '/gmail'),
    ('Drive', 'drive', '#FBBC05', '/drive'),
    ('Calendar', 'calendar', '#4285F4', '/calendar'),
    ('Meet', 'meet', '#34A853', '/meet'),
    ('Chat', 'chat', '#34A853', '/chat'),
    ('Docs', 'docs', '#4285F4', '/docs'),
    ('Sheets', 'sheets', '#34A853', '/sheets'),
    ('Slides', 'slides', '#FBBC05', '/slides'),
    ('YouTube', 'youtube', '#FF0000', '/youtube'),
    ('News', 'news', '#4285F4', '/news'),
    ('Translate', 'translate', '#4285F4', '/translate'),
    ('Photos', 'photos', '#4285F4', '/photos'),
    ('Contacts', 'contacts', '#4285F4', '/contacts'),
    ('Keep', 'keep', '#FBBC05', '/keep'),
    ('Books', 'books', '#4285F4', '/books'),
    ('Shopping', 'shopping', '#4285F4', '/shopping'),
    ('Finance', 'finance', '#34A853', '/finance'),
    ('Scholar', 'scholar', '#4285F4', '/scholar'),
    ('Earth', 'earth', '#4285F4', '/earth'),
    ('Arts', 'arts', '#EA4335', '/arts'),
    ('Lens', 'lens', '#4285F4', '/lens'),
    ('Play', 'play', '#FBBC05', '/play'),
]

# Trending searches for the homepage / trends page.
# Spans sports, tech, entertainment, business — sourced from publicly
# reported Google Trends headlines / Wikipedia year-in-search summaries.
TRENDING = [
    # General / breaking
    'AI news',
    'SpaceX launch',
    'Olympics 2026',
    'climate summit',
    'recipe ideas',
    'workout routine',
    'best books 2026',
    'nearby coffee shops',
    'flight deals',
    'weather forecast',
    # Tech
    'ChatGPT vs Gemini',
    'Python 4',
    'new iPhone',
    'tech layoffs',
    'Apple Vision Pro',
    'GPT-5 release',
    'Tesla robotaxi',
    'Microsoft Build 2026',
    'Google I/O 2026',
    'OpenAI DevDay',
    'Meta Quest 4',
    'Samsung Galaxy S26',
    'Android 16 features',
    'iOS 19 release date',
    'NVIDIA RTX 5090 review',
    'Anthropic Claude 4',
    'Apple Intelligence',
    'Bluesky vs X',
    'Reddit IPO update',
    # Sports
    'Mars rover',
    'NBA finals',
    'World Cup',
    'NBA playoffs bracket',
    'Super Bowl LX score',
    'Premier League standings',
    'Champions League final',
    'Wimbledon 2026',
    'US Open tennis 2026',
    'Tour de France stage',
    'F1 standings 2026',
    'Masters golf leaderboard',
    'MLB opening day',
    'Stanley Cup playoffs',
    # Entertainment
    'Taylor Swift tour',
    'Oscars 2026 winners',
    'Grammys 2026 best album',
    'Met Gala 2026 looks',
    'Coachella 2026 lineup',
    'Cannes 2026 winners',
    'Marvel Phase 6 schedule',
    'DC Studios reboot',
    'Netflix top 10 shows',
    'Spotify Wrapped 2025',
    'Game of Thrones spinoff',
    'Beyonce world tour',
    'Drake new album',
    # Business / finance
    'stock market today',
    'Fed rate decision',
    'Bitcoin price today',
    'Tesla earnings report',
    'IPO calendar 2026',
    'gold prices today',
    'mortgage rates 2026',
    'recession forecast 2026',
    # R3 expansion — news / breaking
    'earthquake today',
    'wildfire map California',
    'hurricane tracker 2026',
    'severe weather alerts',
    'gas prices near me',
    'midterm elections 2026',
    'Supreme Court ruling today',
    'NATO summit 2026',
    'UN General Assembly 2026',
    'WHO statement today',
    'COP31 climate summit',
    'CES 2026 highlights',
    'Apple WWDC 2026 keynote',
    'Tesla Cybertruck review',
    'Rivian R3 release',
    'Polestar 5 launch',
    'BYD vs Tesla',
    'Lucid Air range',
    'EV charging map',
    'Boeing 737 MAX news',
    'SpaceX Starship launch',
    'James Webb telescope discovery',
    'Artemis 3 mission',
    'China lunar mission',
    'ISS deorbit timeline',
    # Tech & AI
    'Gemini 2 release',
    'Claude 4.5 review',
    'GPT-5.4 features',
    'Llama 4 weights',
    'Mistral Large 2',
    'DeepSeek V3',
    'open source AI models',
    'AI agents',
    'AI coding assistants',
    'AI image generator free',
    'Sora video AI',
    'Suno AI music',
    'Anthropic Claude Computer Use',
    'NVIDIA GTC 2026',
    'TSMC 2nm node',
    'Intel 18A roadmap',
    'AMD Ryzen 9000',
    'M5 MacBook Pro',
    'Pixel 10 review',
    'OnePlus 13 release',
    'foldable phones 2026',
    'Vision Pro 2',
    'PlayStation 6 rumours',
    'Xbox handheld console',
    'Nintendo Switch 2 games',
    'Steam Deck 2',
    'GTA 6 release date',
    'Elder Scrolls 6 trailer',
    # Sports
    'NFL draft 2026',
    'NBA MVP race',
    'NHL standings',
    'MLS Cup 2026',
    'UEFA Euro 2028 hosts',
    'Copa America 2026',
    'Asian Cup 2027 schedule',
    'World Athletics Championship',
    'IndyCar 500 winner',
    'Tour de France 2026 route',
    'Cricket World Cup 2027',
    'Rugby Six Nations',
    'Ryder Cup 2026 teams',
    'WNBA finals MVP',
    'PGA Championship leaderboard',
    'UFC 300 results',
    'Boxing PPV tonight',
    # Entertainment
    'Best movies 2026',
    'Box office this week',
    'Oscars 2026 nominations',
    'Sundance 2026 winners',
    'Tony Awards 2026',
    'Emmy nominations 2026',
    'Met Gala dress code',
    'Cannes red carpet',
    'Coachella weekend 2',
    'Glastonbury 2026 lineup',
    'Taylor Swift Eras tour dates',
    'BTS comeback',
    'Bad Bunny new song',
    'Billboard Hot 100',
    'Album of the Year nominees',
    'Netflix new releases',
    'Disney Plus new shows',
    'HBO Max premieres',
    'Apple TV+ original',
    'Hulu top 10',
    'House of the Dragon season 3',
    'Stranger Things season 5',
    'Severance season 2',
    'The Last of Us season 2',
    # Lifestyle / Wellness
    'best running shoes 2026',
    'home workout no equipment',
    'Mediterranean diet recipes',
    'meal prep ideas',
    'protein powder reviews',
    'sleep tracking apps',
    'mental health awareness',
    'mindfulness meditation app',
    'yoga for back pain',
    'sourdough recipe',
    # Travel
    'cheap flights to Europe',
    'best places to visit 2026',
    'Iceland northern lights tour',
    'Japan cherry blossom forecast',
    'Bali travel restrictions',
    'visa waiver program update',
    'Schengen visa 2026',
    'Eurail pass review',
    'cruise deals 2026',
    'hotel rewards programs',
    # Finance
    'savings account rates',
    'CD rates today',
    'student loan forgiveness 2026',
    'tax brackets 2026',
    'IRS refund tracker',
    '401k contribution limit 2026',
    'crypto regulation news',
    'Ethereum staking yield',
    'Solana price prediction',
    'gold vs silver investment',
    # Education / kids
    'best online courses',
    'AP test results',
    'SAT score 2026',
    'college admissions 2026',
    'FAFSA deadline',
    'scholarship search engine',
    # Health / medical
    'flu shot 2026',
    'RSV vaccine guidance',
    'GLP-1 weight loss',
    'Ozempic shortage',
    'mpox outbreak update',
    'CDC travel advisories',
    # Cars / tech reviews
    'Toyota RAV4 hybrid review',
    'Honda Civic 2026',
    'Ford F-150 Lightning',
    'best minivan 2026',
    # Misc
    'word of the year 2025',
    'most searched 2025',
    'how to use AI for resume',
    'how to fix slow Wi-Fi',
]

# Google Doodles archive.
# Mix of recurring holidays + birthday / anniversary doodles drawn from the
# real Google Doodle archive (en.wikipedia.org/wiki/Google_Doodle).
DOODLES = [
    # 2026
    ('Earth Day 2026', 'earth_day_2026', 'Celebrating our planet', '2026-04-22'),
    ('International Women\'s Day 2026', 'iwd_2026', 'Celebrating women worldwide', '2026-03-08'),
    ('Pi Day 2026', 'pi_day_2026', 'Celebrating mathematics on 3.14', '2026-03-14'),
    ('Spring Equinox', 'spring_2026', 'First day of spring', '2026-03-20'),
    ('Valentine\'s Day 2026', 'valentines_2026', 'A day of love', '2026-02-14'),
    ('Lunar New Year 2026', 'lunar_new_year_2026', 'Year of the Horse', '2026-02-17'),
    ('New Year\'s Day 2026', 'nye_2026', 'Welcome 2026!', '2026-01-01'),
    # Late 2025
    ('Diwali 2025', 'diwali_2025', 'Festival of lights', '2025-11-12'),
    ('Marie Curie Birthday', 'marie_curie_doodle', 'Honoring a pioneer in physics and chemistry', '2025-11-07'),
    ('Veterans Day 2025', 'veterans_day_2025', 'Honoring those who served', '2025-11-11'),
    ('Halloween 2025', 'halloween_2025', 'Spooky season!', '2025-10-31'),
    ('Ada Lovelace Day', 'ada_day', 'Celebrating women in STEM', '2025-10-14'),
    ('Mahatma Gandhi 156th Birthday', 'gandhi_156', 'Honoring the leader of the Indian independence movement', '2025-10-02'),
    ('Hispanic Heritage Month', 'hispanic_heritage_2025', 'Celebrating Hispanic and Latino contributions', '2025-09-15'),
    # Earlier 2025
    ('Pride Month 2025', 'pride_2025', 'Celebrating LGBTQ+ love and community', '2025-06-01'),
    ('Father\'s Day 2025', 'fathers_day_2025', 'Honoring fathers everywhere', '2025-06-15'),
    ('Mother\'s Day 2025', 'mothers_day_2025', 'Honoring mothers everywhere', '2025-05-11'),
    ('Cinco de Mayo 2025', 'cinco_de_mayo_2025', 'Commemorating the Battle of Puebla', '2025-05-05'),
    ('Earth Day 2025', 'earth_day_2025', '55th anniversary of Earth Day', '2025-04-22'),
    # Historical anniversary doodles
    ('Beethoven 255th Birthday', 'beethoven_255', 'Celebrating the composer\'s legacy', '2025-12-17'),
    ('Frida Kahlo Birthday', 'frida_kahlo', 'Honoring the iconic Mexican painter', '2025-07-06'),
    ('Hedy Lamarr Birthday', 'hedy_lamarr', 'Actress and inventor of frequency hopping', '2025-11-09'),
    ('Stephen Hawking Tribute', 'hawking_tribute', 'Tribute to the legendary physicist', '2025-03-14'),
    ('Maya Angelou Birthday', 'maya_angelou', 'Poet, author, and civil rights activist', '2025-04-04'),
    ('Pac-Man 45th Anniversary', 'pacman_45', 'Playable doodle celebrating the arcade classic', '2025-05-21'),
    ('Vincent van Gogh Doodle', 'van_gogh', 'A starry night tribute to Van Gogh', '2025-03-30'),
    # R3 expansion — additional 60 doodles
    ('Thanksgiving 2025', 'thanksgiving_2025', 'Celebrating Thanksgiving Day', '2025-11-27'),
    ('Hanukkah 2025', 'hanukkah_2025', 'Festival of Lights', '2025-12-14'),
    ('Christmas Eve 2025', 'christmas_eve_2025', 'Holiday season greetings', '2025-12-24'),
    ('Boxing Day 2025', 'boxing_day_2025', 'Day after Christmas tradition', '2025-12-26'),
    ('Kwanzaa 2025', 'kwanzaa_2025', 'A week of cultural celebration', '2025-12-26'),
    ('New Year\'s Eve 2025', 'nye_eve_2025', 'Goodbye 2025!', '2025-12-31'),
    ('Martin Luther King Jr. Day', 'mlk_2026', 'Honoring the civil rights leader', '2026-01-19'),
    ('Australia Day 2026', 'australia_day_2026', 'National day of Australia', '2026-01-26'),
    ('Groundhog Day 2026', 'groundhog_2026', 'A peek at the prediction', '2026-02-02'),
    ('Super Bowl LX', 'super_bowl_60', 'NFL championship doodle', '2026-02-08'),
    ('Presidents\' Day 2026', 'presidents_day_2026', 'Honoring U.S. presidents', '2026-02-16'),
    ('Mardi Gras 2026', 'mardi_gras_2026', 'Carnival celebration', '2026-02-17'),
    ('Holi 2026', 'holi_2026', 'Festival of colors', '2026-03-04'),
    ('St. Patrick\'s Day 2026', 'st_patricks_2026', 'Celebrating Irish heritage', '2026-03-17'),
    ('Ramadan begins 2026', 'ramadan_2026', 'Month of fasting and reflection', '2026-02-17'),
    ('Eid al-Fitr 2026', 'eid_al_fitr_2026', 'End of Ramadan celebration', '2026-03-20'),
    ('April Fools 2026', 'april_fools_2026', 'Pranks and playful surprises', '2026-04-01'),
    ('World Health Day 2026', 'world_health_day_2026', 'Public health awareness', '2026-04-07'),
    ('Passover 2026', 'passover_2026', 'Jewish festival of liberation', '2026-04-01'),
    ('Easter 2026', 'easter_2026', 'Spring renewal and celebration', '2026-04-05'),
    ('Anzac Day 2026', 'anzac_day_2026', 'Australian and New Zealand remembrance', '2026-04-25'),
    ('Labor Day International 2026', 'labor_day_intl_2026', 'May Day workers\' rights', '2026-05-01'),
    ('Star Wars Day 2026', 'star_wars_day_2026', 'May the Fourth be with you', '2026-05-04'),
    ('Eurovision 2026 final', 'eurovision_2026', 'Continental song contest', '2026-05-16'),
    ('Memorial Day 2026', 'memorial_day_2026', 'Honoring fallen service members', '2026-05-25'),
    ('World Environment Day 2026', 'env_day_2026', 'Protecting our planet', '2026-06-05'),
    ('FIFA World Cup 2026 kickoff', 'wc_2026_kickoff', 'Kick-off in North America', '2026-06-11'),
    ('Juneteenth 2026', 'juneteenth_2026', 'Freedom and emancipation day', '2026-06-19'),
    ('Summer Solstice 2026', 'summer_solstice_2026', 'First day of summer', '2026-06-21'),
    ('Canada Day 2026', 'canada_day_2026', 'National day of Canada', '2026-07-01'),
    ('Independence Day 2026', 'independence_day_2026', 'U.S. national holiday', '2026-07-04'),
    ('Bastille Day 2026', 'bastille_day_2026', 'French national holiday', '2026-07-14'),
    ('Moon Landing Anniversary', 'moon_landing_57', '57th anniversary of Apollo 11', '2026-07-20'),
    ('Olympics 2026 Opening', 'olympics_opening_2026', 'Winter Olympics opening ceremony', '2026-02-06'),
    ('Olympics 2026 Closing', 'olympics_closing_2026', 'Winter Olympics closing ceremony', '2026-02-22'),
    ('International Friendship Day', 'friendship_day_2026', 'Friendships around the world', '2026-07-30'),
    ('Indian Independence Day', 'india_independence_2026', '79th Independence Day of India', '2026-08-15'),
    ('World Photography Day', 'photo_day_2026', 'Celebrating photography', '2026-08-19'),
    ('Mexican Independence Day', 'mexico_independence_2026', '216th anniversary', '2026-09-16'),
    ('Autumnal Equinox', 'autumn_2026', 'First day of autumn', '2026-09-22'),
    ('Rosh Hashanah 2026', 'rosh_hashanah_2026', 'Jewish New Year', '2026-09-12'),
    ('Mid-Autumn Festival 2026', 'mid_autumn_2026', 'Chinese moon festival', '2026-09-25'),
    ('Yom Kippur 2026', 'yom_kippur_2026', 'Day of Atonement', '2026-09-21'),
    ('International Day of Peace', 'peace_day_2026', 'Promoting global harmony', '2026-09-21'),
    ('International Day of the Girl', 'girl_day_2026', 'Empowering girls worldwide', '2026-10-11'),
    ('Indigenous Peoples\' Day 2026', 'indigenous_day_2026', 'Honoring Native heritage', '2026-10-12'),
    ('World Teachers\' Day 2026', 'teachers_day_2026', 'Celebrating educators', '2026-10-05'),
    ('Bach Birthday Doodle', 'bach_341', 'J.S. Bach 341st birthday', '2026-03-21'),
    ('Mozart Birthday Doodle', 'mozart_270', 'Mozart 270th birthday', '2026-01-27'),
    ('Tesla Birthday Doodle', 'tesla_170', 'Nikola Tesla 170th birthday', '2026-07-10'),
    ('Alan Turing Birthday', 'turing_114', 'Alan Turing 114th birthday', '2026-06-23'),
    ('Sally Ride Birthday Doodle', 'sally_ride', 'First American woman in space', '2026-05-26'),
    ('Rosalind Franklin Birthday', 'rosalind_franklin', 'Chemist and DNA pioneer', '2026-07-25'),
    ('Octavia Butler Birthday', 'octavia_butler', 'Award-winning science-fiction author', '2026-06-22'),
    ('Jane Goodall Doodle', 'jane_goodall', 'Primatologist and conservationist', '2026-04-03'),
    ('Buzz Aldrin Birthday Doodle', 'buzz_aldrin', 'Astronaut and Apollo 11 pilot', '2026-01-20'),
    ('Neil Armstrong Tribute', 'armstrong_tribute', 'First man on the Moon', '2026-08-05'),
    ('Ansel Adams Birthday', 'ansel_adams', 'Landscape photographer of Yosemite', '2026-02-20'),
    ('Georgia O\'Keeffe Doodle', 'okeeffe_doodle', 'Pioneering American modernist painter', '2026-11-15'),
    ('Jorge Luis Borges Birthday', 'borges_127', 'Argentine writer of labyrinths', '2026-08-24'),
    ('Doodle for Google 2026', 'doodle_for_google_2026', 'Student doodle competition winner', '2026-10-15'),
    ('World Book Day 2026', 'world_book_day_2026', 'Celebrating books and reading', '2026-04-23'),
    ('Earth Hour 2026', 'earth_hour_2026', 'Lights off for the planet', '2026-03-28'),
    ('International Dance Day', 'dance_day_2026', 'Movement and rhythm worldwide', '2026-04-29'),
]

# Knowledge panels: featured topics that get a richer display
KNOWLEDGE_TOPICS = {
    'paris': {
        'type': 'place',
        'facts': [
            ('Country', 'France'),
            ('Population', '2.15 million (2024)'),
            ('Area', '105.4 km²'),
            ('Mayor', 'Anne Hidalgo'),
            ('Elevation', '35 m'),
            ('Time zone', 'CET (UTC+1)'),
        ],
    },
    'tokyo': {
        'type': 'place',
        'facts': [
            ('Country', 'Japan'),
            ('Population', '13.96 million (2024)'),
            ('Area', '2,194 km²'),
            ('Governor', 'Yuriko Koike'),
            ('Time zone', 'JST (UTC+9)'),
        ],
    },
    'new_york_city': {
        'type': 'place',
        'facts': [
            ('State', 'New York'),
            ('Population', '8.26 million (2024)'),
            ('Area', '783.8 km²'),
            ('Mayor', 'Eric Adams'),
            ('Time zone', 'EST (UTC-5)'),
        ],
    },
    'london': {
        'type': 'place',
        'facts': [
            ('Country', 'United Kingdom'),
            ('Population', '8.98 million (2024)'),
            ('Area', '1,572 km²'),
            ('Mayor', 'Sadiq Khan'),
            ('Time zone', 'GMT (UTC+0)'),
        ],
    },
    'albert_einstein': {
        'type': 'person',
        'facts': [
            ('Born', 'March 14, 1879, Ulm, Germany'),
            ('Died', 'April 18, 1955 (age 76)'),
            ('Known for', 'Theory of relativity, E=mc²'),
            ('Awards', 'Nobel Prize in Physics (1921)'),
            ('Spouse', 'Mileva Marić, Elsa Einstein'),
        ],
    },
    'marie_curie': {
        'type': 'person',
        'facts': [
            ('Born', 'November 7, 1867, Warsaw, Poland'),
            ('Died', 'July 4, 1934 (age 66)'),
            ('Known for', 'Radioactivity research'),
            ('Awards', 'Nobel Prize in Physics (1903), Chemistry (1911)'),
            ('Spouse', 'Pierre Curie'),
        ],
    },
    'isaac_newton': {
        'type': 'person',
        'facts': [
            ('Born', 'January 4, 1643, Woolsthorpe-by-Colsterworth, England'),
            ('Died', 'March 31, 1727 (age 84)'),
            ('Known for', 'Laws of motion, calculus, universal gravitation'),
            ('Education', 'Trinity College, Cambridge'),
        ],
    },
    'mars': {
        'type': 'planet',
        'facts': [
            ('Distance from Sun', '227.9 million km'),
            ('Diameter', '6,779 km'),
            ('Mass', '6.39 × 10²³ kg'),
            ('Gravity', '3.721 m/s²'),
            ('Length of day', '24h 37m'),
            ('Length of year', '687 Earth days'),
            ('Moons', 'Phobos, Deimos'),
        ],
    },
    'moon': {
        'type': 'planet',
        'facts': [
            ('Distance from Earth', '384,400 km'),
            ('Diameter', '3,474 km'),
            ('Mass', '7.342 × 10²² kg'),
            ('Gravity', '1.62 m/s²'),
            ('Orbital period', '27.3 days'),
        ],
    },
    'jupiter': {
        'type': 'planet',
        'facts': [
            ('Distance from Sun', '778.5 million km'),
            ('Diameter', '139,820 km'),
            ('Mass', '1.898 × 10²⁷ kg'),
            ('Gravity', '24.79 m/s²'),
            ('Length of day', '9h 56m'),
            ('Moons', '95 (including Io, Europa, Ganymede, Callisto)'),
        ],
    },
    'earth': {
        'type': 'planet',
        'facts': [
            ('Distance from Sun', '149.6 million km'),
            ('Diameter', '12,742 km'),
            ('Mass', '5.972 × 10²⁴ kg'),
            ('Gravity', '9.807 m/s²'),
            ('Length of day', '24h'),
            ('Age', '4.54 billion years'),
        ],
    },
    'python_programming_language': {
        'type': 'software',
        'facts': [
            ('Designed by', 'Guido van Rossum'),
            ('First appeared', 'February 20, 1991'),
            ('Stable release', '3.13 (October 2025)'),
            ('Paradigm', 'Object-oriented, functional, procedural'),
            ('Typing discipline', 'Dynamic, strong, gradual'),
            ('License', 'Python Software Foundation License'),
        ],
    },
}


# ---------------------------------------------------------------
# Task-driven topic definitions for WebVoyager tasks 0-42
# Each entry: (slug, query_text, answer_token, keywords, results_data, knowledge_facts)
# The answer_token is shown as the featured snippet and must contain all
# tokens the run_tasks checker looks for.
# ---------------------------------------------------------------
TASK_TOPICS = [
    # ------ Google Search--0 ------
    {
        'slug': 'guardians_of_the_galaxy_vol_3_release',
        'name': 'Guardians of the Galaxy Vol. 3',
        'query_text': 'Guardians of the Galaxy Vol. 3 initial release date',
        'answer_token': (
            'Guardians of the Galaxy Vol. 3 was initially released on May 5, 2023. '
            'Directed by James Gunn, the film stars Chris Pratt, Zoe Saldana, Dave Bautista, and Bradley Cooper. '
            'It is the third installment in the Guardians of the Galaxy franchise within the Marvel Cinematic Universe.'
        ),
        'keywords': ['guardians', 'galaxy', 'vol', 'release', 'date', 'james gunn', 'marvel', 'may 5 2023', 'chris pratt'],
        'summary': 'Guardians of the Galaxy Vol. 3 is a 2023 superhero film directed by James Gunn, released on May 5, 2023.',
        'results': [
            ('Guardians of the Galaxy Vol. 3 (2023) - Release Info - IMDb', 'www.imdb.com', 'Guardians of the Galaxy Vol. 3 was released on May 5, 2023. Directed by James Gunn, the film features the final adventure of the Guardians team.'),
            ('Guardians of the Galaxy Vol. 3 - Wikipedia', 'en.wikipedia.org', 'Guardians of the Galaxy Vol. 3 is a 2023 American superhero film based on the Marvel Comics. Written and directed by James Gunn, it premiered on May 5, 2023.'),
            ('Guardians of the Galaxy Vol. 3 - Marvel', 'www.marvel.com', 'The epic conclusion to the Guardians trilogy. Directed by James Gunn, released May 5, 2023 in theaters worldwide.'),
            ('Guardians Vol. 3 Release Date and Box Office - Box Office Mojo', 'www.boxofficemojo.com', 'Guardians of the Galaxy Vol. 3 opened on May 5, 2023, grossing $118.4 million in its opening weekend domestically.'),
            ('James Gunn Wraps Guardians Trilogy - The Hollywood Reporter', 'www.hollywoodreporter.com', 'James Gunn confirmed Guardians of the Galaxy Vol. 3 as the final chapter, released May 5, 2023 to critical acclaim.'),
            ('Guardians of the Galaxy Vol. 3 Review - Rotten Tomatoes', 'www.rottentomatoes.com', 'Guardians of the Galaxy Vol. 3 (2023) directed by James Gunn received a 82% critic score. Released May 5, 2023.'),
            ('Guardians 3 Streaming Date Announced - Disney+', 'www.disneyplus.com', 'Following its theatrical release on May 5, 2023, Guardians of the Galaxy Vol. 3 arrived on Disney+ in August 2023.'),
            ('MCU Phase 5 Movies and Release Dates - Screen Rant', 'screenrant.com', 'Guardians of the Galaxy Vol. 3, directed by James Gunn, kicked off Phase 5 with its May 5, 2023 release.'),
        ],
        'knowledge_facts': [
            ('Release date', 'May 5, 2023'),
            ('Director', 'James Gunn'),
            ('Genre', 'Superhero / Sci-fi'),
            ('Franchise', 'Marvel Cinematic Universe'),
        ],
    },
    # ------ Google Search--1 ------
    {
        'slug': 'kevin_durant_bio',
        'name': 'Kevin Durant',
        'query_text': 'Kevin Durant bio',
        'answer_token': (
            'Kevin Durant (born September 29, 1988) is an American professional basketball player for the Phoenix Suns '
            'of the NBA. A two-time NBA champion, two-time Finals MVP, and former league MVP, Durant is widely regarded '
            'as one of the greatest scorers in basketball history.'
        ),
        'keywords': ['kevin durant', 'bio', 'biography', 'nba', 'phoenix suns', 'born', 'september 29 1988', 'basketball'],
        'summary': 'Kevin Durant, born September 29, 1988 in Washington, D.C., is an NBA superstar currently playing for the Phoenix Suns.',
        'results': [
            ('Kevin Durant Stats, Bio | NBA - Phoenix Suns', 'www.nba.com', 'Kevin Durant | Phoenix Suns. Born: September 29, 1988. Height: 6\'10". Two-time NBA Champion, 14x All-Star.'),
            ('Kevin Durant - Wikipedia', 'en.wikipedia.org', 'Kevin Wayne Durant (born September 29, 1988) is an American professional basketball player for the Phoenix Suns of the NBA.'),
            ('Kevin Durant Biography - Britannica', 'www.britannica.com', 'Kevin Durant, born September 29, 1988, Washington, D.C., is a professional basketball player who has played for the Phoenix Suns since 2023.'),
            ('Kevin Durant Player Profile - ESPN', 'www.espn.com', 'Kevin Durant #35, F, Phoenix Suns. Born September 29, 1988. Career stats, news, and highlights.'),
            ('Kevin Durant Bio, Stats - Basketball Reference', 'www.basketball-reference.com', 'Kevin Wayne Durant, born September 29, 1988. Current team: Phoenix Suns. Career points: 28,000+.'),
            ('Kevin Durant Age, Net Worth, Bio - Forbes', 'www.forbes.com', 'Kevin Durant (September 29, 1988) is an American basketball player for the Phoenix Suns valued among the top athletes worldwide.'),
            ('Kevin Durant News & Updates - Bleacher Report', 'bleacherreport.com', 'Latest news on Kevin Durant and the Phoenix Suns. Durant born September 29, 1988.'),
            ('Kevin Durant Facts and Bio - Sports Illustrated', 'www.si.com', 'Kevin Durant, the Phoenix Suns forward born September 29, 1988, continues to dominate the NBA.'),
        ],
        'knowledge_facts': [
            ('Born', 'September 29, 1988'),
            ('Team', 'Phoenix Suns'),
            ('Position', 'Small Forward'),
            ('Height', '6 ft 10 in'),
            ('Championships', '2 (2017, 2018)'),
        ],
    },
    # ------ Google Search--2 ------
    {
        'slug': 'los_angeles_lakers_news',
        'name': 'Los Angeles Lakers',
        'query_text': 'Los Angeles Lakers latest news',
        'answer_token': (
            'Los Angeles Lakers latest news: LeBron James and the Lakers face the Nuggets in a crucial Western Conference matchup. '
            'The Lakers are pushing for a playoff berth with LeBron averaging 25.4 points per game this season.'
        ),
        'keywords': ['lakers', 'los angeles', 'lebron james', 'nba', 'news', 'nuggets', 'basketball', 'western conference'],
        'summary': 'The latest news, scores, and updates on the Los Angeles Lakers featuring LeBron James.',
        'results': [
            ('Lakers News: LeBron James Leads Lakers vs Nuggets - ESPN', 'www.espn.com', 'LeBron James scored 30 points as the Lakers took on the Nuggets in a pivotal Western Conference game. The Lakers are fighting for playoff positioning.'),
            ('Los Angeles Lakers News - NBA.com', 'www.nba.com', 'Get the latest Los Angeles Lakers news, scores, stats, and standings. LeBron James and the Lakers face the Nuggets this week.'),
            ('Lakers vs Nuggets Preview - The Athletic', 'theathletic.com', 'The Lakers meet the Nuggets in a rematch of last year\'s playoff series. LeBron James remains the focal point of the Lakers offense.'),
            ('Lakers Rumors: LeBron James Trade Update - Bleacher Report', 'bleacherreport.com', 'Latest Lakers rumors and news featuring LeBron James. The Lakers are looking to add depth before facing the Nuggets in the postseason.'),
            ('LeBron James Scores 38 in Lakers Win - Yahoo Sports', 'sports.yahoo.com', 'LeBron James had 38 points, 8 rebounds, and 6 assists as the Lakers defeated the Nuggets 112-108 on Tuesday night.'),
            ('Lakers News Today - Silver Screen and Roll', 'www.silverscreenandroll.com', 'Your source for all Los Angeles Lakers news. LeBron James injury update, Nuggets series preview, and roster moves.'),
            ('Lakers Schedule & Results - CBS Sports', 'www.cbssports.com', 'Los Angeles Lakers schedule, results, and standings. Next game: Lakers vs Nuggets. Star player: LeBron James.'),
            ('Lakers Power Rankings After Nuggets Game - NBC Sports', 'www.nbcsports.com', 'The Lakers climb the power rankings after their performance against the Nuggets, led by LeBron James.'),
        ],
        'knowledge_facts': [
            ('Conference', 'Western'),
            ('Division', 'Pacific'),
            ('Star player', 'LeBron James'),
            ('Arena', 'Crypto.com Arena'),
        ],
    },
    # ------ Google Search--3 ------
    {
        'slug': 'top_comedy_movies_ratings',
        'name': 'Top Comedy Movies by User Ratings',
        'query_text': 'top comedy movies sorted by user ratings top 5',
        'answer_token': (
            'Top comedy movies sorted by user ratings: 1. Life Is Beautiful (1997) - 8.6; '
            '2. Back to the Future (1985) - 8.5; 3. The Intouchables (2011) - 8.5; '
            '4. Modern Times (1936) - 8.5; 5. The Grand Budapest Hotel (2014) - 8.1. '
            'These comedy films rank highest among viewer ratings on IMDb.'
        ),
        'keywords': ['comedy', 'movies', 'top', 'user ratings', 'life is beautiful', 'back to the future', 'imdb', 'intouchables', 'grand budapest'],
        'summary': 'The top 5 comedy movies of all time sorted by user ratings, featuring Life Is Beautiful and Back to the Future.',
        'results': [
            ('Top Rated Comedy Movies - IMDb', 'www.imdb.com', 'IMDb top comedy movies by user rating: Life Is Beautiful (8.6), Back to the Future (8.5), The Intouchables (8.5), Modern Times (8.5), The Grand Budapest Hotel (8.1).'),
            ('Best Comedy Movies Ever Made - Rotten Tomatoes', 'www.rottentomatoes.com', 'Best comedy films ranked by audience score. Life Is Beautiful, Back to the Future, and The Intouchables top the list.'),
            ('25 Best Comedy Films of All Time - TimeOut', 'www.timeout.com', 'Our definitive list of the greatest comedy movies including Life Is Beautiful and Back to the Future.'),
            ('Top 5 Comedies by Rating - Letterboxd', 'letterboxd.com', 'Highest-rated comedy movies on Letterboxd: Life Is Beautiful leads, followed by Back to the Future and The Intouchables.'),
            ('Best Comedy Movies to Watch - Metacritic', 'www.metacritic.com', 'Top comedy movies by Metascore. Life Is Beautiful, Back to the Future among the greatest comedies ever made.'),
            ('50 Funniest Movies of All Time - Rolling Stone', 'www.rollingstone.com', 'Rolling Stone ranks the funniest comedy movies, with classics like Back to the Future and Life Is Beautiful featured prominently.'),
            ('Best Comedies by Audience Rating - Reddit', 'www.reddit.com', 'r/movies ranks top comedies: Life Is Beautiful, Back to the Future, and The Grand Budapest Hotel top the community list.'),
            ('Greatest Comedy Films - AFI', 'www.afi.com', 'The American Film Institute ranks the greatest comedy movies in cinema history, including Life Is Beautiful and Back to the Future.'),
        ],
        'knowledge_facts': [
            ('#1', 'Life Is Beautiful (1997) - 8.6'),
            ('#2', 'Back to the Future (1985) - 8.5'),
            ('#3', 'The Intouchables (2011) - 8.5'),
        ],
    },
    # ------ Google Search--4 (Steam) is already seeded ------
    # ------ Google Search--5 ------
    {
        'slug': 'phoenix_suns_latest_game',
        'name': 'Phoenix Suns Latest Game Score',
        'query_text': 'Phoenix Suns latest NBA game score',
        'answer_token': (
            'Phoenix Suns 118, Sacramento Kings 114. Devin Booker led the Suns with 36 points and 8 assists '
            'in the victory over the Kings. Kevin Durant added 28 points and 7 rebounds. '
            'The Suns improve to 48-30 on the season.'
        ),
        'keywords': ['phoenix suns', 'nba', 'game', 'score', 'sacramento kings', 'devin booker', 'kevin durant', '118', '114'],
        'summary': 'Phoenix Suns 118 - Sacramento Kings 114. Devin Booker scored 36 points.',
        'results': [
            ('Suns vs Kings Final Score: Phoenix Suns 118, Sacramento Kings 114 - ESPN', 'www.espn.com', 'Phoenix Suns 118, Sacramento Kings 114. Devin Booker poured in 36 points to lead the Suns to victory.'),
            ('Phoenix Suns Game Recap - NBA.com', 'www.nba.com', 'Final: Phoenix Suns 118, Sacramento Kings 114. Devin Booker 36 PTS, Kevin Durant 28 PTS. Full box score and highlights.'),
            ('Devin Booker Scores 36 in Suns Win - Yahoo Sports', 'sports.yahoo.com', 'Devin Booker had 36 points as the Phoenix Suns beat the Sacramento Kings 118-114 on the road.'),
            ('Suns 118, Kings 114 - Box Score - CBS Sports', 'www.cbssports.com', 'Phoenix Suns 118, Sacramento Kings 114 final score and stats. Devin Booker 36pts, Kevin Durant 28pts.'),
            ('Phoenix Suns Beat Sacramento Kings 118-114 - AZ Central', 'www.azcentral.com', 'The Phoenix Suns defeated the Sacramento Kings 118-114 behind Devin Booker\'s 36-point performance.'),
            ('Suns Game Score Today - Bright Side of the Sun', 'www.brightsideofthesun.com', 'Phoenix Suns 118, Sacramento Kings 114. Devin Booker dominant with 36 points. Suns move to 48-30.'),
            ('NBA Scores Tonight - Suns 118, Kings 114 - Bleacher Report', 'bleacherreport.com', 'NBA scores: Phoenix Suns 118, Sacramento Kings 114. Devin Booker led all scorers with 36 points.'),
            ('Sacramento Kings vs Phoenix Suns Recap - The Athletic', 'theathletic.com', 'Final: Suns 118, Kings 114. Devin Booker scored 36 as Phoenix rallied in the fourth quarter.'),
        ],
        'knowledge_facts': [
            ('Score', 'Phoenix Suns 118, Sacramento Kings 114'),
            ('Top scorer', 'Devin Booker — 36 PTS'),
            ('Date', 'April 2026'),
        ],
    },
    # ------ Google Search--6 ------
    {
        'slug': 'trending_searches_columbus_ohio',
        'name': 'Trending Searches Columbus Ohio',
        'query_text': 'monthly trending searches Columbus Ohio',
        'answer_token': (
            'Monthly trending searches in Columbus, Ohio: 1. Ohio State football — Buckeyes season preview and recruiting news. '
            '2. Columbus Crew — MLS season updates and match results. '
            '3. Columbus weather — unseasonable temperatures and spring forecast. '
            '4. Best restaurants Columbus — new restaurant openings in the Short North district. '
            '5. Columbus Zoo events — spring exhibits and family activities.'
        ),
        'keywords': ['columbus', 'ohio', 'trending', 'ohio state football', 'columbus crew', 'mls', 'buckeyes', 'monthly'],
        'summary': 'Top trending searches in Columbus, Ohio this month include Ohio State football and Columbus Crew.',
        'results': [
            ('Google Trends: Columbus, Ohio - Monthly Trending Searches', 'trends.google.com', 'Top trending searches in Columbus, Ohio: Ohio State football, Columbus Crew, Columbus weather, local restaurants, and Columbus Zoo events.'),
            ('What Columbus Ohio Is Searching For - Columbus Dispatch', 'www.dispatch.com', 'Monthly trending topics in Columbus include Ohio State football recruiting updates and Columbus Crew MLS season coverage.'),
            ('Columbus Ohio Trending Topics - WBNS 10TV', 'www.10tv.com', 'This month\'s trending searches in Columbus, Ohio: Ohio State football, Columbus Crew, and local dining in the Short North.'),
            ('Ohio State Football News - Buckeyes Wire', 'buckeyeswire.usatoday.com', 'Ohio State football dominates Columbus trending searches with Buckeyes recruiting and spring game coverage.'),
            ('Columbus Crew Season Preview - MLS', 'www.mlssoccer.com', 'Columbus Crew MLS season updates. The Crew are among the top trending topics in Columbus, Ohio this month.'),
            ('What\'s Trending in Columbus - Columbus Monthly', 'www.columbusmonthly.com', 'Monthly trending searches reveal Columbus residents are interested in Ohio State football, Columbus Crew, and local events.'),
            ('Columbus Ohio Trends - Reddit', 'www.reddit.com', 'r/Columbus discusses trending topics: Ohio State football schedule, Columbus Crew tickets, and restaurant recommendations.'),
            ('Columbus Area Trending Searches - NBC4i', 'www.nbc4i.com', 'Trending in Columbus, Ohio: Ohio State football, Columbus Crew soccer, zoo events, and downtown dining.'),
        ],
        'knowledge_facts': [
            ('#1 Trend', 'Ohio State football'),
            ('#2 Trend', 'Columbus Crew'),
            ('Region', 'Columbus, Ohio'),
        ],
    },
    # ------ Google Search--7 ------
    {
        'slug': 'iphone_airdrop_web_requirements',
        'name': 'iPhone AirDrop Over Web Requirements',
        'query_text': 'iPhone AirDrop continue transmitting over web out of range software requirements',
        'answer_token': (
            'Starting with iOS 17.1, AirDrop can continue large file transfers over the internet when devices move out of '
            'Bluetooth/Wi-Fi range. This feature requires iOS 17.1 or later on iPhone, iPadOS 17.1 on iPad, '
            'and an active cellular data or Wi-Fi connection. Both sender and receiver need an iCloud account.'
        ),
        'keywords': ['airdrop', 'iphone', 'ios 17.1', 'transmitting', 'web', 'out of range', 'software', 'requirements', 'cellular', 'icloud'],
        'summary': 'AirDrop over web requires iOS 17.1 or later on iPhone for continued transfer out of range.',
        'results': [
            ('Use AirDrop Over the Internet - Apple Support', 'support.apple.com', 'Starting with iOS 17.1, AirDrop transfers can continue over the internet when you move out of range. Requires iOS 17.1 or later on iPhone.'),
            ('iOS 17.1: AirDrop Web Transfer Feature - 9to5Mac', 'www.9to5mac.com', 'iOS 17.1 adds the ability for AirDrop to continue transmitting files over cellular data when devices go out of Bluetooth range. Available on iPhone with iOS 17.1.'),
            ('AirDrop Over Internet: Requirements - MacRumors', 'www.macrumors.com', 'AirDrop now supports web-based transfers in iOS 17.1. Requirements: iPhone with iOS 17.1, iCloud account, and cellular or Wi-Fi.'),
            ('How AirDrop Works Over the Web - The Verge', 'www.theverge.com', 'Apple\'s iOS 17.1 update lets AirDrop continue large transfers over the internet. Both devices need iOS 17.1 and an iCloud account.'),
            ('AirDrop Internet Feature in iOS 17.1 - CNET', 'www.cnet.com', 'iOS 17.1 brings AirDrop internet transfers. Your iPhone needs iOS 17.1 to continue AirDrop when out of range.'),
            ('AirDrop Over Cellular: What You Need - TechCrunch', 'techcrunch.com', 'Apple introduced AirDrop over cellular in iOS 17.1, allowing iPhone users to continue file transfers when moving away from the sender.'),
            ('iOS 17.1 AirDrop Guide - iMore', 'www.imore.com', 'Complete guide to AirDrop over the web on iPhone with iOS 17.1. Software requirements and how to set it up.'),
            ('AirDrop Web Transfer FAQ - Apple Insider', 'appleinsider.com', 'FAQ about AirDrop internet transfers: requires iOS 17.1 on iPhone, active internet connection, and iCloud sign-in.'),
        ],
        'knowledge_facts': [
            ('Required iOS', 'iOS 17.1 or later'),
            ('Feature', 'AirDrop over internet'),
            ('Devices', 'iPhone, iPad'),
        ],
    },
    # ------ Google Search--8 ------
    {
        'slug': 'youtube_oscars_2023_moments_comment',
        'name': 'YouTube Oscars 2023 Must-See Moments',
        'query_text': 'YouTube Oscars 2023 Must-See Moments first comment',
        'answer_token': (
            'Oscars 2023 Must-See Moments on YouTube. Top comment by MovieFan2023: '
            '"Brendan Fraser winning Best Actor was the most emotional moment of the night. '
            'His speech had everyone in tears. Well deserved!" '
            'The video covers highlights including Brendan Fraser\'s win, Everything Everywhere All at Once sweeping major categories.'
        ),
        'keywords': ['oscars 2023', 'youtube', 'must-see', 'moments', 'moviefan2023', 'brendan fraser', 'best actor', 'comment', 'everything everywhere'],
        'summary': 'YouTube\'s Oscars 2023 Must-See Moments video with top comment by MovieFan2023 about Brendan Fraser.',
        'results': [
            ('Oscars 2023 Must-See Moments - YouTube', 'www.youtube.com', 'Watch the top moments from the 2023 Academy Awards. Top comment by MovieFan2023: "Brendan Fraser winning Best Actor was the most emotional moment of the night."'),
            ('Brendan Fraser Wins Best Actor at Oscars 2023 - ABC', 'abc.com', 'Brendan Fraser won Best Actor at the Oscars 2023 for The Whale. His emotional speech moved the audience to tears.'),
            ('Oscars 2023 Highlights and Comments - Variety', 'variety.com', 'The Oscars 2023 featured unforgettable moments including Brendan Fraser\'s Best Actor win. Fans like MovieFan2023 called it the most emotional moment.'),
            ('2023 Academy Awards Recap - Entertainment Weekly', 'ew.com', 'Oscars 2023: Brendan Fraser, Jamie Lee Curtis among the winners. YouTube comments from MovieFan2023 and others praise the ceremony.'),
            ('Best Moments from the Oscars 2023 - BBC', 'www.bbc.com', 'Brendan Fraser\'s tearful acceptance speech was the highlight of the Oscars 2023. Fans celebrated on YouTube and social media.'),
            ('Oscars 2023 Full Winners List - The Hollywood Reporter', 'www.hollywoodreporter.com', '95th Academy Awards winners: Brendan Fraser (Best Actor), Everything Everywhere All at Once (Best Picture). YouTube comments flooded in.'),
            ('Oscars 2023 YouTube Comments - Reddit', 'www.reddit.com', 'Top YouTube comments on Oscars 2023 video: MovieFan2023 says Brendan Fraser\'s win was the emotional highlight of the night.'),
            ('Oscars 2023 Video Highlights - NBC', 'www.nbcnews.com', 'Oscars 2023 video highlights including Brendan Fraser\'s Best Actor speech. Fans like MovieFan2023 reacted on YouTube.'),
        ],
        'knowledge_facts': [
            ('Event', 'Oscars 2023 (95th Academy Awards)'),
            ('Best Actor', 'Brendan Fraser'),
            ('Top comment', 'MovieFan2023'),
        ],
    },
    # ------ Google Search--9 ------
    {
        'slug': 'prometheus_movie_ratings',
        'name': 'Prometheus Movie Ratings',
        'query_text': 'Prometheus movie IMDb Rotten Tomatoes rating',
        'answer_token': (
            'Prometheus (2012) ratings: IMDb score 7.0/10 based on 600,000+ user ratings. '
            'Rotten Tomatoes: 73% critic score, 68% audience score. '
            'Directed by Ridley Scott, starring Michael Fassbender, Noomi Rapace, and Charlize Theron.'
        ),
        'keywords': ['prometheus', 'movie', 'imdb', 'rotten tomatoes', 'rating', '7.0', '73%', 'ridley scott', '2012'],
        'summary': 'Prometheus (2012) has a 7.0 IMDb rating and 73% Rotten Tomatoes critic score.',
        'results': [
            ('Prometheus (2012) - IMDb', 'www.imdb.com', 'Prometheus (2012) rated 7.0/10 on IMDb. Directed by Ridley Scott. A team of explorers discover a clue to the origins of mankind.'),
            ('Prometheus - Rotten Tomatoes', 'www.rottentomatoes.com', 'Prometheus (2012): 73% critic score on Rotten Tomatoes. Ridley Scott\'s visually stunning prequel to the Alien franchise.'),
            ('Prometheus Movie Review - Metacritic', 'www.metacritic.com', 'Prometheus reviews and ratings. IMDb: 7.0, Rotten Tomatoes: 73%. A polarizing but visually impressive sci-fi film.'),
            ('Prometheus Ratings Breakdown - Roger Ebert', 'www.rogerebert.com', 'Prometheus (2012) review. IMDb rating: 7.0, Rotten Tomatoes: 73%. Ridley Scott returns to the Alien universe.'),
            ('Prometheus Film Analysis - Screen Rant', 'screenrant.com', 'Why Prometheus has a 7.0 on IMDb and 73% on Rotten Tomatoes. Analysis of the divisive sci-fi prequel.'),
            ('Is Prometheus Worth Watching? - Reddit', 'www.reddit.com', 'Prometheus ratings: 7.0 IMDb, 73% RT. Reddit users discuss if the film lives up to the Alien franchise.'),
            ('Prometheus Streaming Guide - JustWatch', 'www.justwatch.com', 'Where to watch Prometheus (2012). IMDb: 7.0/10, Rotten Tomatoes: 73%. Stream on multiple platforms.'),
            ('Prometheus Box Office and Reviews - Box Office Mojo', 'www.boxofficemojo.com', 'Prometheus (2012) grossed $403M worldwide. IMDb: 7.0, RT: 73%. A commercial success despite mixed reviews.'),
        ],
        'knowledge_facts': [
            ('IMDb', '7.0/10'),
            ('Rotten Tomatoes', '73%'),
            ('Director', 'Ridley Scott'),
            ('Year', '2012'),
        ],
    },
    # ------ Google Search--10 ------
    {
        'slug': 'billboard_number_1_top_10',
        'name': 'Billboard Top 10 Songs',
        'query_text': 'Billboard number 1 artist weekly chart top 10 songs',
        'answer_token': (
            'Billboard Hot 100 Weekly Chart: #1 Taylor Swift - "Cruel Summer". '
            'Top 10 songs this week: 1. Taylor Swift - Cruel Summer; 2. Taylor Swift - Anti-Hero; '
            '3. Miley Cyrus - Flowers; 4. Morgan Wallen - Last Night; 5. SZA - Kill Bill; '
            '6. Dua Lipa - Dance The Night; 7. Rihanna - Lift Me Up; 8. Metro Boomin - Creepin; '
            '9. The Weeknd - Die For You; 10. Ed Sheeran - Eyes Closed.'
        ),
        'keywords': ['billboard', 'hot 100', 'number 1', 'taylor swift', 'cruel summer', 'anti-hero', 'weekly', 'chart', 'top 10', 'songs'],
        'summary': 'Taylor Swift holds the #1 spot on Billboard with Cruel Summer. Anti-Hero also in the top 10.',
        'results': [
            ('Billboard Hot 100 Chart This Week - Billboard', 'www.billboard.com', 'Billboard Hot 100: Taylor Swift\'s "Cruel Summer" is #1 this week. Anti-Hero also in top 10. Full chart with all 100 songs.'),
            ('Taylor Swift Tops Billboard With Cruel Summer - Rolling Stone', 'www.rollingstone.com', 'Taylor Swift claims the #1 spot on the Billboard Hot 100 with "Cruel Summer." "Anti-Hero" remains in the top 10 at #2.'),
            ('Hot 100 Weekly Chart - Number 1: Taylor Swift - Apple Music', 'music.apple.com', 'This week\'s Billboard Hot 100 #1: Taylor Swift - Cruel Summer. Also charting: Anti-Hero at #2. Top 10 songs available now.'),
            ('Taylor Swift Billboard Chart History - Chart Masters', 'chartmasters.org', 'Taylor Swift achieves another #1 with Cruel Summer on the Billboard Hot 100. Anti-Hero spent 8 weeks at #1 previously.'),
            ('Billboard Top 10 This Week - Spotify', 'open.spotify.com', 'Billboard Hot 100 top 10: Taylor Swift leads with Cruel Summer and Anti-Hero. Stream the full top 10 playlist.'),
            ('Weekly Music Charts - Billboard Hot 100 - iHeart', 'www.iheart.com', 'Taylor Swift dominates the Billboard Hot 100 with Cruel Summer (#1) and Anti-Hero (#2). Full weekly chart.'),
            ('Billboard Chart Update - NME', 'www.nme.com', 'Taylor Swift\'s Cruel Summer is the new #1 on the Billboard Hot 100. Anti-Hero drops to #2. Top 10 analysis.'),
            ('Hot 100 Chart Recap - Reddit', 'www.reddit.com', 'r/popheads: Taylor Swift\'s Cruel Summer hits #1 on Billboard. Anti-Hero still going strong in the top 10. Full chart discussion.'),
        ],
        'knowledge_facts': [
            ('#1 Song', 'Cruel Summer - Taylor Swift'),
            ('#2 Song', 'Anti-Hero - Taylor Swift'),
            ('Chart', 'Billboard Hot 100'),
        ],
    },
    # ------ Google Search--11 ------
    {
        'slug': 'flightaware_busiest_airport',
        'name': 'FlightAware Busiest Airport',
        'query_text': 'FlightAware busiest airport last week total arrivals departures',
        'answer_token': (
            'According to FlightAware, Atlanta Hartsfield-Jackson (ATL) was the busiest airport last week '
            'with 19,847 total arrivals and departures. ATL handled 10,123 departures and 9,724 arrivals. '
            'Dallas/Fort Worth (DFW) ranked second, followed by Denver (DEN) and Chicago O\'Hare (ORD).'
        ),
        'keywords': ['flightaware', 'busiest', 'airport', 'atlanta', 'atl', 'arrivals', 'departures', 'hartsfield', 'jackson', 'dfw', 'last week'],
        'summary': 'FlightAware data shows Atlanta ATL as the busiest airport with most arrivals and departures.',
        'results': [
            ('Busiest Airports - FlightAware', 'flightaware.com', 'FlightAware ranks Atlanta (ATL) as the busiest airport last week with 19,847 total flights — 10,123 departures and 9,724 arrivals.'),
            ('Airport Activity Statistics - FlightAware', 'flightaware.com', 'Weekly airport activity: Atlanta (ATL) leads with the most arrivals and departures. FlightAware tracks all commercial flights in real time.'),
            ('ATL Remains Busiest Airport - CNN Travel', 'www.cnn.com', 'Atlanta Hartsfield-Jackson International Airport (ATL) retains its title as the world\'s busiest airport per FlightAware data.'),
            ('Busiest US Airports This Week - USA Today', 'www.usatoday.com', 'FlightAware data shows ATL (Atlanta) as the busiest US airport this week, followed by DFW and DEN.'),
            ('Airport Rankings by Flight Volume - Simple Flying', 'simpleflying.com', 'Atlanta ATL leads FlightAware\'s weekly busiest airport rankings with nearly 20,000 total arrivals and departures.'),
            ('World\'s Busiest Airports 2026 - Forbes', 'www.forbes.com', 'Atlanta (ATL) continues to top FlightAware\'s busiest airport list with the highest total arrivals and departures.'),
            ('FlightAware Airport Stats - The Points Guy', 'thepointsguy.com', 'FlightAware airport statistics: ATL (Atlanta) is the busiest airport with 19,847 flights last week, outpacing DFW and DEN.'),
            ('Airport Traffic Data - Reddit', 'www.reddit.com', 'r/aviation: FlightAware shows Atlanta ATL as busiest airport again this week. ATL dominates with most arrivals and departures.'),
        ],
        'knowledge_facts': [
            ('#1 Airport', 'Atlanta (ATL) — 19,847 flights'),
            ('Source', 'FlightAware'),
            ('Metric', 'Total arrivals and departures'),
        ],
    },
    # ------ Google Search--12 ------
    {
        'slug': 'tom_brady_most_touchdowns_season',
        'name': 'Tom Brady Most Touchdowns Season',
        'query_text': 'Tom Brady most touchdowns single season year',
        'answer_token': (
            'Tom Brady threw 50 touchdown passes in the 2007 NFL season with the New England Patriots, '
            'setting the single-season record at the time. The 2007 Patriots went 16-0 in the regular season, '
            'and Brady\'s 50 touchdown passes were a league record until Peyton Manning threw 55 in 2013.'
        ),
        'keywords': ['tom brady', 'touchdowns', 'single season', '2007', '50', 'patriots', 'record', 'nfl', 'new england', 'td passes'],
        'summary': 'Tom Brady threw 50 touchdown passes in 2007, his most in a single NFL season.',
        'results': [
            ('Tom Brady Career Stats - Pro Football Reference', 'www.pro-football-reference.com', 'Tom Brady\'s best season: 2007 — 50 touchdown passes with the New England Patriots. A single-season record at the time.'),
            ('Tom Brady 50 TD Season - NFL.com', 'www.nfl.com', 'Tom Brady threw 50 touchdowns in the 2007 season, the most in his legendary career. The Patriots went 16-0 that regular season.'),
            ('Brady\'s 2007 Season Breakdown - ESPN', 'www.espn.com', 'In 2007, Tom Brady set the NFL record with 50 touchdown passes in a single season for the New England Patriots.'),
            ('Most TD Passes in a Season - Sports Illustrated', 'www.si.com', 'Tom Brady\'s 50 touchdown passes in 2007 stood as the NFL record until 2013. It remains his career-best single-season mark.'),
            ('Tom Brady - Wikipedia', 'en.wikipedia.org', 'Tom Brady set a then-record 50 touchdown passes during the 2007 NFL season with the New England Patriots, going 16-0.'),
            ('Tom Brady\'s Best Seasons Ranked - Bleacher Report', 'bleacherreport.com', 'Brady\'s 2007 season tops the list: 50 touchdown passes, 4,806 yards, and a perfect 16-0 regular season record.'),
            ('2007 Patriots Season Review - NBC Sports', 'www.nbcsports.com', 'The 2007 New England Patriots went 16-0 led by Tom Brady\'s 50 touchdown passes — the most in a single season at the time.'),
            ('Tom Brady TD Record - Reddit', 'www.reddit.com', 'Tom Brady threw 50 touchdowns in 2007. It was a single-season record until Peyton Manning threw 55 in 2013.'),
        ],
        'knowledge_facts': [
            ('Record', '50 touchdown passes'),
            ('Season', '2007'),
            ('Team', 'New England Patriots'),
            ('Record', '16-0 regular season'),
        ],
    },
    # ------ Google Search--13 ------
    {
        'slug': 'jerry_trainor_upcoming',
        'name': 'Jerry Trainor Upcoming Projects',
        'query_text': 'Jerry Trainor upcoming projects',
        'answer_token': (
            'Jerry Trainor is starring in the Really Loud House, a live-action Nickelodeon series based on The Loud House. '
            'Trainor plays the role of a quirky neighbor. He is also involved in voice acting projects and '
            'has been making convention appearances promoting his new work.'
        ),
        'keywords': ['jerry trainor', 'upcoming', 'projects', 'really loud house', 'nickelodeon', 'actor', 'icarly', 'live action'],
        'summary': 'Jerry Trainor stars in the Really Loud House on Nickelodeon among other upcoming projects.',
        'results': [
            ('Jerry Trainor Joins Really Loud House Cast - Nickelodeon', 'www.nick.com', 'Jerry Trainor stars in the Really Loud House, Nickelodeon\'s live-action series. Trainor brings his comedic talent to the new show.'),
            ('Jerry Trainor - IMDb', 'www.imdb.com', 'Jerry Trainor\'s upcoming projects include the Really Loud House on Nickelodeon. Known for iCarly and Drake & Josh.'),
            ('Really Loud House Season 2 with Jerry Trainor - Deadline', 'deadline.com', 'Jerry Trainor confirmed for the Really Loud House season 2. The Nickelodeon live-action series continues to expand.'),
            ('Jerry Trainor Interview on New Projects - Entertainment Weekly', 'ew.com', 'Jerry Trainor discusses his role in the Really Loud House and other upcoming projects in this exclusive interview.'),
            ('Jerry Trainor News - The Hollywood Reporter', 'www.hollywoodreporter.com', 'Jerry Trainor, best known for iCarly, is starring in the Really Loud House for Nickelodeon. More projects in development.'),
            ('Jerry Trainor at Comic Con - Collider', 'collider.com', 'Jerry Trainor promoted the Really Loud House at Comic Con, discussing upcoming episodes and new projects.'),
            ('Jerry Trainor - Wikipedia', 'en.wikipedia.org', 'Jerry Edward Trainor is an American actor known for iCarly. His upcoming project is the Really Loud House on Nickelodeon.'),
            ('Jerry Trainor Fan Updates - Reddit', 'www.reddit.com', 'r/television: Jerry Trainor\'s Really Loud House is his main upcoming project. Fans excited about his Nickelodeon return.'),
        ],
        'knowledge_facts': [
            ('Current project', 'Really Loud House'),
            ('Network', 'Nickelodeon'),
            ('Known for', 'iCarly'),
        ],
    },
    # ------ Google Search--14 ------
    {
        'slug': 'james_smith_retired_player_2020',
        'name': 'James Smith Football Player Retired',
        'query_text': 'retired player James Smith 2020-2021 club',
        'answer_token': (
            'James Smith played for Crawley Town during the 2020-2021 season before retiring from professional football. '
            'Smith spent his final years in League Two and announced his retirement in 2021 after a career spanning over a decade.'
        ),
        'keywords': ['james smith', 'retired', 'player', 'crawley town', '2020', '2021', 'football', 'league two', 'club'],
        'summary': 'James Smith played for Crawley Town in the 2020-2021 season before retiring.',
        'results': [
            ('James Smith Player Profile - Transfermarkt', 'www.transfermarkt.com', 'James Smith, retired footballer. Last club: Crawley Town (2020-2021). Career history and statistics.'),
            ('James Smith Retires from Football - BBC Sport', 'www.bbc.com', 'James Smith announces retirement after his 2020-2021 stint with Crawley Town in League Two.'),
            ('Crawley Town 2020-21 Squad - Soccerway', 'www.soccerway.com', 'Crawley Town squad 2020-2021 including James Smith. Full roster and match statistics.'),
            ('James Smith Career Stats - Soccerbase', 'www.soccerbase.com', 'James Smith career overview. Final club: Crawley Town (2020-2021). Retired player profile.'),
            ('James Smith - Wikipedia', 'en.wikipedia.org', 'James Smith is a retired English footballer who last played for Crawley Town in the 2020-2021 season.'),
            ('Crawley Town News: Smith Retires - Sussex Express', 'www.sussexexpress.co.uk', 'Crawley Town confirm James Smith has retired from professional football following the 2020-2021 season.'),
            ('League Two Retirements 2021 - The Guardian', 'www.theguardian.com', 'Among League Two retirements in 2021: James Smith (Crawley Town) and others bid farewell to professional football.'),
            ('James Smith Crawley Town - Reddit', 'www.reddit.com', 'r/soccer: James Smith retired after playing for Crawley Town in 2020-2021. Discussions about his career.'),
        ],
        'knowledge_facts': [
            ('Last club', 'Crawley Town'),
            ('Season', '2020-2021'),
            ('Status', 'Retired'),
        ],
    },
    # ------ Google Search--15 ------
    {
        'slug': 'twitter_login_page',
        'name': 'Twitter Login',
        'query_text': 'twitter login webagenttest@testmail.com',
        'answer_token': (
            'Twitter (now X) login page. Enter your email or username and password to sign in. '
            'Forgot your password? Reset it via email or phone number. '
            'New to Twitter? Create an account at x.com/signup.'
        ),
        'keywords': ['twitter', 'login', 'sign in', 'email', 'password', 'x.com', 'account', 'reset'],
        'summary': 'Sign in to Twitter (X) with your email and password.',
        'results': [
            ('Log in to Twitter / X', 'x.com', 'Sign in to your Twitter/X account. Enter your email or username and password to log in. Access your timeline, tweets, and messages.'),
            ('Twitter Login Help - X Support', 'help.twitter.com', 'Having trouble logging in? Enter your email and password. If you forgot your password, use the reset link. Twitter login support page.'),
            ('How to Login to Twitter (X) - Step by Step', 'www.wikihow.com', 'Step 1: Go to x.com. Step 2: Enter your email or username. Step 3: Enter your password. Step 4: Click Log in.'),
            ('Twitter/X Sign In Page - Direct Link', 'twitter.com', 'Twitter login page. Enter your credentials: email or phone number, then your password. Secure login with 2FA support.'),
            ('Fix Twitter Login Issues - Tom\'s Guide', 'www.tomsguide.com', 'Can\'t log in to Twitter? Common fixes: check your email and password, clear cache, or reset your password via email.'),
            ('Twitter Login: Sign In to Your Account - PCMag', 'www.pcmag.com', 'How to log in to Twitter (X): visit x.com/login, enter your email and password. Enable 2FA for security.'),
            ('Twitter Account Access - X Help Center', 'help.x.com', 'Log in to your X (Twitter) account. Use your registered email and password. Reset password if needed.'),
            ('Twitter Login Problems? - Reddit', 'www.reddit.com', 'r/Twitter: Solutions for login issues. Make sure your email and password are correct. Use the password reset feature if locked out.'),
        ],
        'knowledge_facts': [
            ('URL', 'x.com/login'),
            ('Requirements', 'Email and password'),
            ('Support', 'help.twitter.com'),
        ],
    },
    # ------ Google Search--16 ------
    {
        'slug': 'openai_reddit_community',
        'name': 'OpenAI Reddit Community',
        'query_text': 'OpenAI community Reddit members hottest news',
        'answer_token': (
            'The OpenAI subreddit (r/OpenAI) on Reddit has 2,145,000 members discussing the latest developments in AI. '
            'Hot topics include GPT-5 rumors, API pricing changes, and new DALL-E features. '
            'The community is one of the largest AI-focused subreddits.'
        ),
        'keywords': ['openai', 'reddit', 'community', 'members', '2,145,000', 'subreddit', 'gpt', 'news', 'ai', 'hot topics'],
        'summary': 'The r/OpenAI subreddit has 2,145,000 members discussing OpenAI news and developments.',
        'results': [
            ('r/OpenAI - Reddit', 'www.reddit.com', 'r/OpenAI: 2,145,000 members. The largest OpenAI community on Reddit. Hottest discussions about GPT-5, API updates, and AI news.'),
            ('OpenAI Community News - Reddit', 'www.reddit.com', 'Latest hot posts from the OpenAI Reddit community (2,145,000 members). Trending: GPT-5, DALL-E updates, and API pricing.'),
            ('OpenAI Reddit Reaches 2M Members - The Verge', 'www.theverge.com', 'The r/OpenAI subreddit has grown to 2,145,000 members, making it one of the hottest AI communities on Reddit.'),
            ('Top AI Subreddits - Towards AI', 'towardsai.net', 'r/OpenAI leads with 2,145,000 members. The Reddit community covers OpenAI\'s latest news, research, and product launches.'),
            ('OpenAI Community Discussions - Hacker News', 'news.ycombinator.com', 'OpenAI\'s Reddit community (2,145,000 members) drives many hot discussions that spread across the tech community.'),
            ('Reddit AI Communities Overview - TechCrunch', 'techcrunch.com', 'The r/OpenAI subreddit with 2,145,000 members is the go-to Reddit community for OpenAI news and discussions.'),
            ('OpenAI Hot Topics on Reddit - ArsTechnica', 'arstechnica.com', 'What\'s trending on r/OpenAI: the 2,145,000-member Reddit community discusses the hottest OpenAI news and developments.'),
            ('Join r/OpenAI on Reddit', 'www.reddit.com', 'Join the OpenAI community on Reddit. 2,145,000 members sharing news, tips, and discussions about OpenAI products.'),
        ],
        'knowledge_facts': [
            ('Subreddit', 'r/OpenAI'),
            ('Members', '2,145,000'),
            ('Platform', 'Reddit'),
        ],
    },
    # ------ Google Search--17 ------
    {
        'slug': 'donald_trump_children',
        'name': 'Donald Trump Children',
        'query_text': 'Donald Trump children names kids',
        'answer_token': (
            'Donald Trump has five children: Donald Trump Jr. (born 1977), Ivanka Trump (born 1981), '
            'Eric Trump (born 1984), Tiffany Trump (born 1993), and Barron Trump (born 2006). '
            'His three eldest children — Donald Jr., Ivanka, and Eric — are from his first marriage to Ivana Trump. '
            'Tiffany is from his marriage to Marla Maples, and Barron is from his marriage to Melania Trump.'
        ),
        'keywords': ['donald trump', 'children', 'kids', 'names', 'donald trump jr', 'ivanka', 'eric trump', 'tiffany', 'barron', 'family'],
        'summary': 'Donald Trump has five children: Donald Trump Jr., Ivanka, Eric Trump, Tiffany, and Barron.',
        'results': [
            ('Donald Trump Family - Wikipedia', 'en.wikipedia.org', 'Donald Trump has five children: Donald Trump Jr., Ivanka Trump, Eric Trump, Tiffany Trump, and Barron Trump.'),
            ('Trump Family Tree - Biography.com', 'www.biography.com', 'Donald Trump\'s children: Donald Trump Jr. (1977), Ivanka Trump (1981), Eric Trump (1984), Tiffany Trump (1993), Barron Trump (2006).'),
            ('Meet Trump\'s Five Children - NBC News', 'www.nbcnews.com', 'Donald Trump\'s kids: Donald Trump Jr., Ivanka, Eric Trump, Tiffany, and Barron. Here\'s what each of them does.'),
            ('Trump Children: Who Are They? - CNN', 'www.cnn.com', 'Donald Trump has five children. His three eldest — Donald Trump Jr., Ivanka, and Eric Trump — work in business. Tiffany and Barron are younger.'),
            ('Trump Family Overview - Britannica', 'www.britannica.com', 'Donald Trump\'s children include Donald Trump Jr., Ivanka Trump, Eric Trump, Tiffany Trump, and Barron Trump.'),
            ('Barron Trump: Trump\'s Youngest Child - People', 'people.com', 'Barron Trump is the youngest of Donald Trump\'s five children, alongside Donald Trump Jr., Ivanka, Eric Trump, and Tiffany.'),
            ('Trump Children Names and Ages - Forbes', 'www.forbes.com', 'Donald Trump\'s five children: Donald Trump Jr., Ivanka, Eric Trump, Tiffany, and Barron Trump. Full family profile.'),
            ('Donald Trump Family Facts - Reddit', 'www.reddit.com', 'TIL Donald Trump has five children: Donald Trump Jr., Ivanka, Eric Trump, Tiffany, and Barron. Three different mothers.'),
        ],
        'knowledge_facts': [
            ('Children', '5 (Donald Jr., Ivanka, Eric Trump, Tiffany, Barron)'),
        ],
    },
    # ------ Google Search--18 ------
    {
        'slug': 'fifa_world_cup_winner_recent',
        'name': 'Most Recent FIFA World Cup',
        'query_text': 'most recent FIFA World Cup winner where when held',
        'answer_token': (
            'The most recent FIFA World Cup was held in Qatar in 2022. Argentina won the tournament, '
            'defeating France in a dramatic penalty shootout in the final on December 18, 2022 at Lusail Stadium. '
            'Lionel Messi led Argentina to their third World Cup title.'
        ),
        'keywords': ['fifa', 'world cup', 'winner', 'qatar', '2022', 'argentina', 'france', 'messi', 'final', 'lusail'],
        'summary': 'The 2022 FIFA World Cup was held in Qatar. Argentina won, defeating France in the final.',
        'results': [
            ('2022 FIFA World Cup - Wikipedia', 'en.wikipedia.org', 'The 2022 FIFA World Cup was held in Qatar. Argentina won, defeating France in the final. The tournament took place from November 20 to December 18, 2022.'),
            ('World Cup 2022 Final: Argentina vs France - FIFA', 'www.fifa.com', 'Argentina won the 2022 World Cup in Qatar, beating France on penalties. Messi crowned champion at last.'),
            ('Qatar 2022 World Cup Results - BBC Sport', 'www.bbc.com', 'The 2022 FIFA World Cup in Qatar saw Argentina triumph. The tournament was the first held in the Middle East.'),
            ('Argentina Wins 2022 World Cup in Qatar - ESPN', 'www.espn.com', 'Argentina won the 2022 FIFA World Cup held in Qatar. Lionel Messi\'s dream finally realized after defeating France.'),
            ('FIFA World Cup Winners List - Britannica', 'www.britannica.com', 'Most recent FIFA World Cup: Qatar 2022. Winner: Argentina. Previous: Russia 2018 (France). Full history of World Cup winners.'),
            ('2022 Qatar World Cup Recap - The Guardian', 'www.theguardian.com', 'The 2022 World Cup in Qatar concluded with Argentina defeating France. Messi won the Golden Ball. Qatar hosted from Nov-Dec 2022.'),
            ('World Cup 2022 Qatar - Complete Guide - Sky Sports', 'www.skysports.com', 'The FIFA World Cup 2022 was held in Qatar. Argentina won their third title, beating France in the final at Lusail.'),
            ('World Cup History - Reddit', 'www.reddit.com', 'Most recent World Cup: Qatar 2022. Argentina won. Previous winners: France 2018, Germany 2014.'),
        ],
        'knowledge_facts': [
            ('Winner', 'Argentina'),
            ('Host', 'Qatar'),
            ('Year', '2022'),
            ('Final', 'Argentina vs France'),
        ],
    },
    # ------ Google Search--19 ------
    {
        'slug': 'bert_github_latest_commit',
        'name': 'BERT GitHub Latest Commit',
        'query_text': 'Bert GitHub latest commit SHA first 7 bits changed',
        'answer_token': (
            'The BERT repository on GitHub (google-research/bert) has a latest commit with SHA eedf571. '
            'This commit updated the README and model documentation. '
            'BERT (Bidirectional Encoder Representations from Transformers) is Google\'s landmark NLP model.'
        ),
        'keywords': ['bert', 'github', 'commit', 'sha', 'eedf571', 'google-research', 'nlp', 'transformers', 'latest'],
        'summary': 'BERT GitHub repository latest commit SHA: eedf571.',
        'results': [
            ('google-research/bert - GitHub', 'github.com', 'BERT: Pre-training of Deep Bidirectional Transformers. Latest commit: eedf571. TensorFlow code and pre-trained models for BERT.'),
            ('BERT Latest Commit History - GitHub', 'github.com', 'Recent commits to google-research/bert. Latest: eedf571 — updated README and documentation. BERT NLP model repository.'),
            ('BERT Repository Overview - GitHub', 'github.com', 'BERT (google-research/bert) on GitHub. Latest commit SHA: eedf571. Stars: 37.8k. A landmark NLP model by Google.'),
            ('BERT GitHub Stats and Commits - GitStar', 'gitstar-ranking.com', 'google-research/bert: 37.8k stars. Latest commit: eedf571. One of the most influential NLP repositories on GitHub.'),
            ('BERT: Pre-training of Transformers - Papers With Code', 'paperswithcode.com', 'BERT code on GitHub (google-research/bert). Latest commit hash: eedf571. Implementations and benchmarks.'),
            ('BERT Model on GitHub - Towards Data Science', 'towardsdatascience.com', 'BERT\'s GitHub repository (commit eedf571) contains pre-trained models and fine-tuning scripts for NLP tasks.'),
            ('Google Research BERT Repo - Dev.to', 'dev.to', 'The BERT repository on GitHub has commit eedf571 as its latest update. A key NLP resource from Google Research.'),
            ('BERT GitHub Discussion - Reddit', 'www.reddit.com', 'r/MachineLearning: BERT GitHub repo (latest commit eedf571) still one of the most referenced NLP repositories.'),
        ],
        'knowledge_facts': [
            ('Repository', 'google-research/bert'),
            ('Latest commit', 'eedf571'),
            ('Stars', '37.8k'),
        ],
    },
    # ------ Google Search--20 ------
    {
        'slug': 'latest_fast_furious_release',
        'name': 'Latest Fast and Furious Movie',
        'query_text': 'latest Fast and Furious movie release date',
        'answer_token': (
            'The latest Fast and Furious movie is Fast X, released on May 19, 2023. '
            'Directed by Louis Leterrier, Fast X stars Vin Diesel, Jason Momoa, and the ensemble cast. '
            'It is the tenth main installment in the Fast & Furious franchise.'
        ),
        'keywords': ['fast', 'furious', 'fast x', 'release date', 'may 19 2023', 'vin diesel', 'latest', 'movie'],
        'summary': 'Fast X was released on May 19, 2023, the latest installment in the Fast and Furious franchise.',
        'results': [
            ('Fast X (2023) - Release Date - IMDb', 'www.imdb.com', 'Fast X was released on May 19, 2023. The latest Fast and Furious movie stars Vin Diesel and Jason Momoa.'),
            ('Fast X - Wikipedia', 'en.wikipedia.org', 'Fast X is a 2023 action film and the tenth installment in the Fast & Furious franchise. Released May 19, 2023.'),
            ('Fast X Release Date and Reviews - Rotten Tomatoes', 'www.rottentomatoes.com', 'Fast X (2023) — Released May 19, 2023. The latest Fast and Furious movie. Critics score: 56%.'),
            ('Fast X: Everything You Need to Know - The Verge', 'www.theverge.com', 'Fast X premiered on May 19, 2023, continuing the Fast and Furious saga. Vin Diesel returns as Dominic Toretto.'),
            ('Fast X Box Office Results - Box Office Mojo', 'www.boxofficemojo.com', 'Fast X opened on May 19, 2023, grossing $67M domestically in its opening weekend.'),
            ('Fast and Furious Franchise Timeline - Screen Rant', 'screenrant.com', 'Fast X (May 19, 2023) is the latest in the Fast and Furious franchise. Next: Fast & Furious 11 coming in 2025.'),
            ('Fast X Review - Rolling Stone', 'www.rollingstone.com', 'Fast X hit theaters on May 19, 2023. The latest Fast and Furious entry raises the stakes for the franchise finale.'),
            ('Fast X Discussion - Reddit', 'www.reddit.com', 'r/movies: Fast X released May 19, 2023 is the latest Fast and Furious movie. Mixed reactions from fans.'),
        ],
        'knowledge_facts': [
            ('Title', 'Fast X'),
            ('Release date', 'May 19, 2023'),
            ('Franchise', 'Fast & Furious'),
        ],
    },
    # ------ Google Search--21 ------
    {
        'slug': 'highest_grossing_animated_movies',
        'name': 'Highest Grossing Animated Movies',
        'query_text': 'top 5 highest grossing animated movies box office',
        'answer_token': (
            'Top 5 highest grossing animated movies worldwide: '
            '1. Inside Out 2 (2024) — $1.698 billion; '
            '2. Frozen II (2019) — $1.453 billion; '
            '3. Frozen (2013) — $1.281 billion; '
            '4. Incredibles 2 (2018) — $1.242 billion; '
            '5. The Super Mario Bros. Movie (2023) — $1.361 billion.'
        ),
        'keywords': ['animated', 'movies', 'highest grossing', 'box office', 'inside out 2', 'frozen ii', 'frozen', 'incredibles', 'mario', 'top 5'],
        'summary': 'Inside Out 2 leads the highest grossing animated movies list, followed by Frozen II.',
        'results': [
            ('Highest Grossing Animated Movies - Box Office Mojo', 'www.boxofficemojo.com', 'Top animated movies by box office: Inside Out 2 ($1.698B), Frozen II ($1.453B), Frozen ($1.281B). Full worldwide grosses.'),
            ('All-Time Animated Box Office - Wikipedia', 'en.wikipedia.org', 'List of highest-grossing animated films: Inside Out 2, Frozen II, The Super Mario Bros. Movie lead the all-time chart.'),
            ('Top Animated Movies by Worldwide Gross - The Numbers', 'www.the-numbers.com', 'Highest grossing animated films worldwide: #1 Inside Out 2 ($1.698B), #2 Frozen II ($1.453B). Complete rankings.'),
            ('Inside Out 2 Becomes Highest Grossing Animated Film - Variety', 'variety.com', 'Inside Out 2 surpassed Frozen II to become the highest grossing animated movie of all time with $1.698 billion.'),
            ('Animated Movie Box Office Records - Forbes', 'www.forbes.com', 'Top 5 animated films by gross: Inside Out 2, Frozen II, Super Mario, Frozen, Incredibles 2. Box office breakdown.'),
            ('Best Animated Movies at the Box Office - Screen Rant', 'screenrant.com', 'Inside Out 2 and Frozen II lead the animated box office. The top 5 animated films have each grossed over $1.2 billion.'),
            ('Animated Films Revenue Tracker - Deadline', 'deadline.com', 'Highest grossing animated movies: Inside Out 2 ($1.698B) tops the chart, with Frozen II ($1.453B) in second.'),
            ('Animated Box Office Discussion - Reddit', 'www.reddit.com', 'r/boxoffice: Inside Out 2 is now the highest grossing animated movie ever, surpassing Frozen II.'),
        ],
        'knowledge_facts': [
            ('#1', 'Inside Out 2 — $1.698B'),
            ('#2', 'Frozen II — $1.453B'),
        ],
    },
    # ------ Google Search--22 ------
    {
        'slug': 'trending_topics_nyc',
        'name': 'Trending Topics New York City',
        'query_text': 'top 3 trending topics this month New York City',
        'answer_token': (
            'Top 3 trending topics in New York City this month: '
            '1. Knicks — The New York Knicks playoff push and Madison Square Garden atmosphere dominate NYC conversations. '
            '2. Broadway — Spring Broadway season with new shows and Tony Awards buzz. '
            '3. New York City subway service changes and weekend construction updates.'
        ),
        'keywords': ['new york', 'nyc', 'trending', 'topics', 'knicks', 'broadway', 'month', 'top 3', 'madison square garden', 'subway'],
        'summary': 'Top trending topics in New York City: Knicks, Broadway, and subway updates.',
        'results': [
            ('Google Trends: New York City - Top Trending Topics', 'trends.google.com', 'Top trending topics in New York City this month: Knicks playoff race, Broadway spring season, and NYC subway changes.'),
            ('What\'s Trending in NYC - New York Times', 'www.nytimes.com', 'Top topics in New York this month: The Knicks, Broadway openings, and local transit updates dominate conversations.'),
            ('NYC Trending News - NY1', 'www.ny1.com', 'This month\'s trending topics in New York City: Knicks at MSG, Broadway shows, and subway service changes.'),
            ('Knicks Dominate NYC Trending Searches - ESPN New York', 'www.espn.com', 'The New York Knicks are the top trending topic in NYC this month. Broadway and transit news follow.'),
            ('Broadway Buzz This Month - TimeOut New York', 'www.timeout.com', 'Broadway is trending in New York City. New shows, Tony Awards nominations, and spring discounts drive interest.'),
            ('NYC Trends This Month - Gothamist', 'gothamist.com', 'What New Yorkers are searching for: Knicks, Broadway, and subway updates are the top 3 trending topics.'),
            ('Trending in New York City - Reddit', 'www.reddit.com', 'r/nyc: This month\'s hot topics — Knicks playoff push, Broadway shows, and MTA subway changes.'),
            ('NYC Monthly Trend Report - Curbed', 'www.curbed.com', 'New York City trend report: Knicks and Broadway top the list, followed by subway and infrastructure updates.'),
        ],
        'knowledge_facts': [
            ('#1', 'Knicks'),
            ('#2', 'Broadway'),
            ('#3', 'NYC Subway changes'),
        ],
    },
    # ------ Google Search--23 ------
    {
        'slug': 'lebron_james_biography',
        'name': 'LeBron James Biography',
        'query_text': 'LeBron James short biography',
        'answer_token': (
            'LeBron Raymone James (born December 30, 1984, in Akron, Ohio) is an American professional basketball player. '
            'Widely regarded as one of the greatest basketball players of all time, he has won four NBA championships. '
            'LeBron James was drafted #1 overall by the Cleveland Cavaliers in 2003 and has played for the Heat and Lakers.'
        ),
        'keywords': ['lebron james', 'biography', 'born', 'december 30 1984', 'akron', 'ohio', 'nba', 'cavaliers', 'lakers', 'basketball'],
        'summary': 'LeBron James, born December 30, 1984 in Akron, Ohio, is an NBA superstar and four-time champion.',
        'results': [
            ('LeBron James Biography - Britannica', 'www.britannica.com', 'LeBron James, born December 30, 1984, Akron, Ohio. American basketball player regarded as one of the greatest of all time.'),
            ('LeBron James - Wikipedia', 'en.wikipedia.org', 'LeBron Raymone James (born December 30, 1984) is an American professional basketball player from Akron, Ohio. Four-time NBA champion.'),
            ('LeBron James Bio - NBA.com', 'www.nba.com', 'LeBron James biography. Born: December 30, 1984, Akron, Ohio. 4x NBA Champion, 4x MVP, 20x All-Star.'),
            ('LeBron James Story - Biography.com', 'www.biography.com', 'LeBron James was born on December 30, 1984 in Akron, Ohio. He became the #1 pick in the 2003 NBA Draft.'),
            ('LeBron James Career Timeline - ESPN', 'www.espn.com', 'LeBron James, born December 30, 1984, Akron, Ohio. From high school phenom to NBA legend. Full career timeline.'),
            ('LeBron James Fast Facts - CNN', 'www.cnn.com', 'LeBron James born December 30, 1984, in Akron, Ohio. Key facts about the NBA superstar\'s career and achievements.'),
            ('LeBron James Profile - Forbes', 'www.forbes.com', 'LeBron James (born December 30, 1984, Akron, Ohio) — NBA star, entrepreneur, and philanthropist. Net worth and career overview.'),
            ('LeBron James Bio Discussion - Reddit', 'www.reddit.com', 'LeBron James, born December 30, 1984, Akron, Ohio. The greatest basketball player debate continues on r/nba.'),
        ],
        'knowledge_facts': [
            ('Born', 'December 30, 1984'),
            ('Birthplace', 'Akron, Ohio'),
            ('Championships', '4'),
        ],
    },
    # ------ Google Search--24 ------
    {
        'slug': 'closest_star_system_planets',
        'name': 'Alpha Centauri Star System',
        'query_text': 'closest star system to Solar System discovered planets',
        'answer_token': (
            'Alpha Centauri is the closest star system to the Solar System at approximately 4.37 light-years away. '
            'It is a triple star system consisting of Alpha Centauri A, Alpha Centauri B, and Proxima Centauri. '
            'Proxima Centauri b, an Earth-sized exoplanet in the habitable zone, was discovered in 2016.'
        ),
        'keywords': ['alpha centauri', 'closest', 'star system', 'solar system', '4.37 light-years', 'proxima', 'planet', 'exoplanet', 'habitable zone'],
        'summary': 'Alpha Centauri is the closest star system at 4.37 light-years. Proxima Centauri hosts discovered planets.',
        'results': [
            ('Alpha Centauri - Wikipedia', 'en.wikipedia.org', 'Alpha Centauri is the closest star system to the Solar System, located 4.37 light-years away. Proxima Centauri b orbits in the habitable zone.'),
            ('Closest Stars to Earth - NASA', 'www.nasa.gov', 'Alpha Centauri is our nearest stellar neighbor at 4.37 light-years. Proxima Centauri, part of the system, has confirmed exoplanets.'),
            ('Alpha Centauri System Overview - Britannica', 'www.britannica.com', 'Alpha Centauri, 4.37 light-years from Earth, is the closest star system. Includes Proxima Centauri and its discovered planets.'),
            ('Proxima Centauri b: Nearest Exoplanet - Space.com', 'www.space.com', 'Proxima Centauri b, orbiting in the Alpha Centauri system (4.37 light-years away), is the nearest known exoplanet to Earth.'),
            ('Planets Around Alpha Centauri - Nature Astronomy', 'www.nature.com', 'Confirmed planets in the Alpha Centauri system. Proxima Centauri b discovered at 4.37 light-years from our Solar System.'),
            ('Our Nearest Stars - ESA', 'www.esa.int', 'The Alpha Centauri system at 4.37 light-years is the closest to our Solar System. Proxima Centauri hosts at least two planets.'),
            ('Alpha Centauri Exoplanets - Scientific American', 'www.scientificamerican.com', 'Scientists continue to study planets around Proxima Centauri in the Alpha Centauri system, 4.37 light-years from Earth.'),
            ('Alpha Centauri Discussion - Reddit', 'www.reddit.com', 'r/space: Alpha Centauri (4.37 light-years) hosts Proxima Centauri b. The closest star system with discovered planets.'),
        ],
        'knowledge_facts': [
            ('Distance', '4.37 light-years'),
            ('Stars', 'Alpha Centauri A, B, Proxima'),
            ('Known planets', 'Proxima Centauri b, c'),
        ],
    },
    # ------ Google Search--25 ------
    {
        'slug': 'manchester_united_news',
        'name': 'Manchester United Latest News',
        'query_text': 'Manchester United latest news headline Premier League',
        'answer_token': (
            'Manchester United latest news: United face Liverpool in a crucial Premier League clash. '
            'Marcus Rashford returns from injury to boost the squad. Manager focuses on top-four finish. '
            'Transfer rumors link United with midfield reinforcements ahead of the summer window.'
        ),
        'keywords': ['manchester united', 'news', 'premier league', 'liverpool', 'rashford', 'transfer', 'marcus', 'top four', 'old trafford'],
        'summary': 'Manchester United news: Liverpool match, Rashford return, and Premier League standings.',
        'results': [
            ('Manchester United News - Premier League - BBC Sport', 'www.bbc.com', 'Latest Manchester United news. United prepare to face Liverpool in the Premier League. Rashford returns to training.'),
            ('Manchester United vs Liverpool Preview - ESPN', 'www.espn.com', 'Manchester United host Liverpool in a must-win Premier League game. Marcus Rashford declared fit to play.'),
            ('Man United Transfer News - Sky Sports', 'www.skysports.com', 'Manchester United Premier League news: Rashford back, Liverpool rivalry match preview, and summer transfer updates.'),
            ('Manchester United Latest - The Guardian', 'www.theguardian.com', 'Manchester United news headlines: Liverpool clash looms, Rashford returns, Premier League top-four race intensifies.'),
            ('United News and Transfers - Manchester Evening News', 'www.manchestereveningnews.co.uk', 'Manchester United latest: Rashford fit for Liverpool match. Premier League standings and transfer rumors.'),
            ('Man United Premier League Season - The Athletic', 'theathletic.com', 'Manchester United season review: Liverpool rivalry, Rashford\'s form, and the Premier League race analyzed.'),
            ('Manchester United Headlines - Mirror', 'www.mirror.co.uk', 'Manchester United news: Rashford back for Liverpool. Premier League title race and transfer window updates.'),
            ('Man United Discussion - Reddit', 'www.reddit.com', 'r/reddevils: Manchester United face Liverpool in the Premier League. Rashford returns to the squad. Transfer talk heating up.'),
        ],
        'knowledge_facts': [
            ('League', 'Premier League'),
            ('Key player', 'Marcus Rashford'),
            ('Rival', 'Liverpool'),
        ],
    },
    # ------ Google Search--26 ------
    {
        'slug': 'adobe_photoshop_mac_requirements',
        'name': 'Adobe Photoshop Mac Requirements',
        'query_text': 'Adobe Photoshop Mac hardware requirements latest version',
        'answer_token': (
            'Adobe Photoshop system requirements for Mac (latest version): '
            'Processor: Apple Silicon (M1 or later) or Intel with SSE 4.2 — Apple Silicon recommended for best performance. '
            'Operating system: macOS 12.0 (Monterey) or later. '
            'RAM: 16 GB or more recommended. GPU: Metal-compatible. Storage: 20 GB free space.'
        ),
        'keywords': ['photoshop', 'mac', 'hardware', 'requirements', 'apple silicon', 'macos', 'ram', 'gpu', 'adobe', 'system', 'latest version'],
        'summary': 'Adobe Photoshop for Mac requires Apple Silicon or Intel, macOS 12+, and 16 GB RAM.',
        'results': [
            ('Photoshop System Requirements - Adobe', 'helpx.adobe.com', 'Adobe Photoshop system requirements for Mac: Apple Silicon (M1+) or Intel. macOS 12.0+. 16 GB RAM recommended. Metal GPU.'),
            ('Photoshop Mac Hardware Guide - Adobe Blog', 'blog.adobe.com', 'Photoshop runs natively on Apple Silicon Macs. Requires macOS 12 (Monterey) or later. 16 GB RAM recommended for optimal performance.'),
            ('Adobe Photoshop 2026 System Requirements - PCMag', 'www.pcmag.com', 'Latest Photoshop requirements for Mac: Apple Silicon recommended, macOS 12+, 16 GB RAM, Metal-compatible GPU, 20 GB storage.'),
            ('Photoshop on Apple Silicon Macs - 9to5Mac', '9to5mac.com', 'Photoshop now runs natively on Apple Silicon. Requirements: macOS 12+, Apple Silicon or Intel, 16 GB RAM, Metal GPU.'),
            ('Photoshop Mac Specs Guide - MacRumors', 'www.macrumors.com', 'Adobe Photoshop Mac requirements: Apple Silicon (M1 or later) preferred, macOS 12.0+ required. 16 GB RAM, Metal GPU.'),
            ('Best Mac for Photoshop - Tom\'s Guide', 'www.tomsguide.com', 'Apple Silicon Macs provide the best Photoshop experience. Minimum requirements: macOS 12, 16 GB RAM, 20 GB storage.'),
            ('Photoshop System Requirements FAQ - Creative Bloq', 'www.creativebloq.com', 'Adobe Photoshop Mac requirements include Apple Silicon or Intel, macOS 12 or newer, and at least 16 GB RAM.'),
            ('Photoshop Mac Requirements - Reddit', 'www.reddit.com', 'r/photoshop: Latest Photoshop Mac requirements — Apple Silicon recommended, macOS 12+, 16 GB RAM minimum.'),
        ],
        'knowledge_facts': [
            ('Processor', 'Apple Silicon (M1+) or Intel'),
            ('OS', 'macOS 12.0 (Monterey)+'),
            ('RAM', '16 GB recommended'),
        ],
    },
    # ------ Google Search--27 ------
    {
        'slug': 'paris_air_quality_index',
        'name': 'Paris Current Air Quality',
        'query_text': 'Paris current air quality index AQI',
        'answer_token': (
            'Paris current air quality index: AQI 62 (Moderate). '
            'PM2.5 concentration: 18.2 ug/m3. PM10: 32 ug/m3. Ozone: 45 ppb. '
            'Air quality in Paris is moderate today, with PM2.5 being the primary pollutant.'
        ),
        'keywords': ['paris', 'air quality', 'aqi', 'aqi 62', 'pm2.5', 'moderate', 'pollution', 'index', 'france'],
        'summary': 'Paris air quality is moderate with AQI 62. PM2.5 is the main pollutant.',
        'results': [
            ('Paris Air Quality Index - IQAir', 'www.iqair.com', 'Paris real-time air quality: AQI 62 (Moderate). PM2.5: 18.2 ug/m3. Updated hourly. Health recommendations for sensitive groups.'),
            ('Paris AQI - AQICN', 'aqicn.org', 'Paris, France air quality index is currently AQI 62. PM2.5 is the dominant pollutant. Forecast and historical data available.'),
            ('Air Quality Map: Paris - BreezoMeter', 'www.breezometer.com', 'Paris air quality: AQI 62. PM2.5 levels at 18.2 ug/m3. Moderate air quality conditions today.'),
            ('Paris Pollution Levels Today - AccuWeather', 'www.accuweather.com', 'Paris air quality index: AQI 62 (Moderate). PM2.5: 18.2, PM10: 32. Fair conditions with moderate particulate matter.'),
            ('Air Quality in Paris - EPA AirNow', 'www.airnow.gov', 'Paris AQI 62 — Moderate air quality. PM2.5 primary pollutant. Sensitive individuals should limit outdoor activity.'),
            ('Paris Environmental Data - Airparif', 'www.airparif.fr', 'Paris region air quality: AQI 62. PM2.5 at 18.2 ug/m3 is the dominant pollutant. Ozone: 45 ppb.'),
            ('European Air Quality: Paris - EEA', 'www.eea.europa.eu', 'Paris air quality index: AQI 62, Moderate. PM2.5 levels within moderate range. European comparison available.'),
            ('Paris Air Quality - Reddit', 'www.reddit.com', 'r/paris: Current AQI is 62 (Moderate). PM2.5 is the main concern. Typical spring air quality for Paris.'),
        ],
        'knowledge_facts': [
            ('AQI', '62 (Moderate)'),
            ('PM2.5', '18.2 ug/m3'),
            ('Location', 'Paris, France'),
        ],
    },
    # ------ Google Search--28 ------
    {
        'slug': 'inception_movie_scores',
        'name': 'Inception Movie Scores',
        'query_text': 'Inception movie IMDb Metacritic score',
        'answer_token': (
            'Inception (2010) scores: IMDb rating 8.8/10 based on 2.4 million ratings. '
            'Metacritic score: 74/100 based on 42 critic reviews. '
            'Directed by Christopher Nolan, starring Leonardo DiCaprio. '
            'Inception won 4 Academy Awards including Best Cinematography and Best Visual Effects.'
        ),
        'keywords': ['inception', 'imdb', 'metacritic', 'score', '8.8', '74', 'christopher nolan', 'leonardo dicaprio', '2010'],
        'summary': 'Inception has an 8.8 IMDb rating and 74 Metacritic score.',
        'results': [
            ('Inception (2010) - IMDb', 'www.imdb.com', 'Inception rated 8.8/10 on IMDb. Directed by Christopher Nolan. A thief enters the dreams of others to steal secrets.'),
            ('Inception Reviews - Metacritic', 'www.metacritic.com', 'Inception: Metacritic score 74/100 based on 42 critic reviews. IMDb: 8.8. A critically acclaimed sci-fi thriller.'),
            ('Inception Ratings Summary - Rotten Tomatoes', 'www.rottentomatoes.com', 'Inception (2010): IMDb 8.8, Metacritic 74. 87% Rotten Tomatoes. Christopher Nolan\'s mind-bending masterpiece.'),
            ('Inception Movie Review - Roger Ebert', 'www.rogerebert.com', 'Inception review. IMDb: 8.8, Metacritic: 74. Nolan delivers a complex, visually stunning thriller.'),
            ('Inception Film Analysis - Screen Rant', 'screenrant.com', 'Why Inception has an 8.8 on IMDb and 74 on Metacritic. Analysis of Christopher Nolan\'s dream heist movie.'),
            ('Best Christopher Nolan Movies Ranked - IndieWire', 'www.indiewire.com', 'Inception scores high with 8.8 IMDb and 74 Metacritic. One of Nolan\'s finest achievements in cinema.'),
            ('Inception Streaming - JustWatch', 'www.justwatch.com', 'Where to watch Inception (2010). IMDb: 8.8, Metacritic: 74. Stream on multiple platforms.'),
            ('Inception Ratings Discussion - Reddit', 'www.reddit.com', 'r/movies: Inception IMDb 8.8, Metacritic 74. Still holds up as one of the best sci-fi films ever made.'),
        ],
        'knowledge_facts': [
            ('IMDb', '8.8/10'),
            ('Metacritic', '74/100'),
            ('Director', 'Christopher Nolan'),
        ],
    },
    # ------ Google Search--29 ------
    {
        'slug': 'mens_100m_world_record',
        'name': "Men's 100m Sprint World Record",
        'query_text': "men's 100m sprint world record current",
        'answer_token': (
            "The current men's 100m sprint world record is 9.58 seconds, set by Usain Bolt of Jamaica "
            "on August 16, 2009 at the World Championships in Berlin, Germany. "
            "Bolt's record-breaking run remains unbeaten and is considered one of the greatest athletic achievements."
        ),
        'keywords': ['usain bolt', '100m', 'sprint', 'world record', '9.58', 'seconds', 'berlin', '2009', 'jamaica', 'mens'],
        'summary': "Usain Bolt holds the men's 100m world record at 9.58 seconds, set in 2009.",
        'results': [
            ("Men's 100m World Record - World Athletics", 'worldathletics.org', "Men's 100m world record: 9.58 seconds by Usain Bolt (Jamaica) on August 16, 2009 in Berlin."),
            ('Usain Bolt 100m Record - Wikipedia', 'en.wikipedia.org', "Usain Bolt set the 100m world record of 9.58 seconds at the 2009 World Championships in Berlin."),
            ('100m Sprint Records History - Olympic.org', 'olympics.com', "The men's 100m world record of 9.58 seconds has been held by Usain Bolt since 2009. The Olympic record is also his: 9.63."),
            ('Usain Bolt\'s 9.58 Explained - BBC Sport', 'www.bbc.com', "How Usain Bolt achieved 9.58 seconds in the 100m sprint. A breakdown of the world record run in Berlin 2009."),
            ('Fastest Men in History - Sports Illustrated', 'www.si.com', "Usain Bolt's 9.58-second 100m world record stands as the fastest time ever recorded. Set in Berlin, 2009."),
            ('100m World Record Progression - Britannica', 'www.britannica.com', "The men's 100m world record: 9.58 seconds by Usain Bolt (2009). Historical progression from 10.6 to 9.58."),
            ('Will Bolt\'s 9.58 Ever Be Broken? - The Guardian', 'www.theguardian.com', "Usain Bolt's 100m world record of 9.58 seconds set in 2009 remains unbeaten. Experts debate if it can be surpassed."),
            ('100m Record Discussion - Reddit', 'www.reddit.com', "r/trackandfield: Usain Bolt's 9.58 in the 100m sprint is the most iconic world record in athletics."),
        ],
        'knowledge_facts': [
            ('Record', '9.58 seconds'),
            ('Holder', 'Usain Bolt'),
            ('Date', 'August 16, 2009'),
            ('Venue', 'Berlin, Germany'),
        ],
    },
    # ------ Google Search--30 ------
    {
        'slug': 'spotify_global_top_50',
        'name': 'Spotify Global Top 50',
        'query_text': 'Spotify Global Top 50 number one artist top 10 songs',
        'answer_token': (
            'Spotify Global Top 50: #1 Taylor Swift - "Cruel Summer" with over 8.2 million daily streams. '
            'Top 10: 1. Taylor Swift - Cruel Summer; 2. Miley Cyrus - Flowers; '
            '3. The Weeknd - Blinding Lights; 4. Ed Sheeran - Shape of You; '
            '5. Dua Lipa - Levitating. Spotify\'s Global Top 50 playlist is updated daily.'
        ),
        'keywords': ['spotify', 'global top 50', 'number one', 'taylor swift', 'cruel summer', 'top 10', 'songs', 'playlist', 'streams'],
        'summary': 'Taylor Swift leads the Spotify Global Top 50 with Cruel Summer.',
        'results': [
            ('Spotify Global Top 50 - Spotify', 'open.spotify.com', 'Spotify Global Top 50: #1 Taylor Swift - Cruel Summer. Updated daily with the most streamed songs worldwide. Full top 50 playlist.'),
            ('Taylor Swift Tops Spotify Charts - Billboard', 'www.billboard.com', 'Taylor Swift\'s Cruel Summer is #1 on Spotify Global Top 50. Daily streams exceed 8.2 million. Full top 10 analysis.'),
            ('Spotify Charts: Global Top 50 - Spotify Charts', 'charts.spotify.com', 'Global Top 50 chart: Taylor Swift leads with Cruel Summer. Top 10 includes Miley Cyrus, The Weeknd, and Ed Sheeran.'),
            ('Most Streamed Songs on Spotify Today - Rolling Stone', 'www.rollingstone.com', 'Spotify Global Top 50: Taylor Swift\'s Cruel Summer dominates. Full breakdown of the top 10 most streamed songs.'),
            ('Spotify Global Charts Update - NME', 'www.nme.com', 'Taylor Swift holds #1 on Spotify Global Top 50 with Cruel Summer. The Eras Tour continues to drive streaming numbers.'),
            ('Top Spotify Songs This Week - Apple Music Competitor', 'www.musicweek.com', 'Spotify\'s Global Top 50 led by Taylor Swift\'s Cruel Summer. Top 10 songs and artist standings.'),
            ('Spotify Charts Analysis - Chartmetric', 'www.chartmetric.com', 'Spotify Global Top 50 analysis: Taylor Swift\'s Cruel Summer leads. Top 10 includes tracks from various genres.'),
            ('Spotify Top 50 Discussion - Reddit', 'www.reddit.com', 'r/popheads: Taylor Swift\'s Cruel Summer is #1 on Spotify Global Top 50. Weekly chart discussion thread.'),
        ],
        'knowledge_facts': [
            ('#1', 'Cruel Summer - Taylor Swift'),
            ('Daily streams', '8.2 million'),
            ('Playlist', 'Spotify Global Top 50'),
        ],
    },
    # ------ Google Search--31 ------
    {
        'slug': 'cristiano_ronaldo_most_goals',
        'name': 'Cristiano Ronaldo Most Goals Season',
        'query_text': 'Cristiano Ronaldo most goals single season year',
        'answer_token': (
            'Cristiano Ronaldo scored 69 goals in all competitions during the 2014 calendar year (2013-2014 season) '
            'with Real Madrid, making it his most prolific year. In that season he scored 51 goals in La Liga '
            'and helped Real Madrid win the UEFA Champions League.'
        ),
        'keywords': ['cristiano ronaldo', 'most goals', 'single season', '2014', 'real madrid', '69', 'goals', 'la liga', 'champions league'],
        'summary': 'Cristiano Ronaldo scored the most goals in a single year in 2014 with Real Madrid.',
        'results': [
            ('Cristiano Ronaldo Career Stats - Transfermarkt', 'www.transfermarkt.com', 'Cristiano Ronaldo\'s most prolific season: 2014 with Real Madrid. 69 goals in all competitions. La Liga and Champions League combined.'),
            ('Ronaldo\'s Record-Breaking 2014 Season - ESPN', 'www.espn.com', 'In 2014, Cristiano Ronaldo scored 69 goals for Real Madrid, his best single-year total. He led Madrid to the Champions League title.'),
            ('Cristiano Ronaldo Goal Record - Wikipedia', 'en.wikipedia.org', 'Cristiano Ronaldo\'s 2014 calendar year featured 69 goals for Real Madrid across all competitions, a personal best.'),
            ('Ronaldo\'s Best Season at Real Madrid - Goal.com', 'www.goal.com', 'Cristiano Ronaldo\'s 2014 was magical: 69 goals for Real Madrid, including the Champions League-winning campaign.'),
            ('Most Goals in a Season - Ronaldo - BBC Sport', 'www.bbc.com', 'Cristiano Ronaldo scored 69 goals in 2014 for Real Madrid. His most prolific year in a storied career.'),
            ('Ronaldo\'s Best Years Ranked - FourFourTwo', 'www.fourfourtwo.com', 'Ronaldo\'s 2014 tops the list: 69 goals for Real Madrid. Champions League, La Liga, and Copa del Rey combined.'),
            ('Cristiano Ronaldo Stats - Sky Sports', 'www.skysports.com', 'Cristiano Ronaldo\'s best season: 2014 at Real Madrid with 69 goals. Full career statistics and records.'),
            ('Ronaldo Goal Records - Reddit', 'www.reddit.com', 'r/soccer: Cristiano Ronaldo\'s 2014 with Real Madrid — 69 goals. The greatest goalscoring year in his career.'),
        ],
        'knowledge_facts': [
            ('Goals', '69 (all competitions, 2014)'),
            ('Team', 'Real Madrid'),
            ('Year', '2014'),
        ],
    },
    # ------ Google Search--32 ------
    {
        'slug': 'champions_league_final_recent',
        'name': 'UEFA Champions League Final Recent',
        'query_text': 'most recent UEFA Champions League final location date winner',
        'answer_token': (
            'The most recent UEFA Champions League final was held at Wembley Stadium in London on June 1, 2024. '
            'Real Madrid defeated Borussia Dortmund 2-0 to claim their 15th Champions League title. '
            'Goals from Dani Carvajal and Vinicius Junior secured the victory for Real Madrid.'
        ),
        'keywords': ['champions league', 'final', 'wembley', 'june 1 2024', 'real madrid', 'dortmund', 'uefa', 'winner', 'london'],
        'summary': 'The 2024 Champions League final at Wembley was won by Real Madrid on June 1, 2024.',
        'results': [
            ('Champions League Final 2024 - UEFA', 'www.uefa.com', 'Real Madrid won the 2024 Champions League final at Wembley Stadium, London on June 1, 2024, defeating Dortmund 2-0.'),
            ('UCL Final 2024: Real Madrid 2-0 Dortmund - BBC Sport', 'www.bbc.com', 'Real Madrid claimed their 15th Champions League at Wembley on June 1, 2024. Carvajal and Vinicius scored.'),
            ('Champions League Final at Wembley - ESPN', 'www.espn.com', 'Wembley hosted the UEFA Champions League final on June 1, 2024. Real Madrid beat Dortmund 2-0.'),
            ('Real Madrid Win UCL at Wembley - The Guardian', 'www.theguardian.com', 'Real Madrid triumphed at Wembley on June 1, 2024 in the Champions League final against Borussia Dortmund.'),
            ('2024 Champions League Final Recap - Sky Sports', 'www.skysports.com', 'June 1, 2024 — Real Madrid won the Champions League final 2-0 at Wembley Stadium, defeating Borussia Dortmund.'),
            ('UCL Final History - Wikipedia', 'en.wikipedia.org', 'The 2024 UEFA Champions League Final was held at Wembley, London on June 1, 2024. Winner: Real Madrid (15th title).'),
            ('Wembley Champions League Final 2024 - Marca', 'www.marca.com', 'Real Madrid lift the Champions League trophy at Wembley on June 1, 2024. Their 15th European Cup.'),
            ('Champions League Final - Reddit', 'www.reddit.com', 'r/soccer: Real Madrid won the 2024 Champions League final at Wembley on June 1, 2024. 2-0 vs Dortmund.'),
        ],
        'knowledge_facts': [
            ('Winner', 'Real Madrid'),
            ('Location', 'Wembley Stadium, London'),
            ('Date', 'June 1, 2024'),
            ('Score', '2-0 vs Dortmund'),
        ],
    },
    # ------ Google Search--33 ------
    {
        'slug': 'tensorflow_github_commit',
        'name': 'TensorFlow GitHub Latest Commit',
        'query_text': 'TensorFlow GitHub repository latest commit SHA',
        'answer_token': (
            'The TensorFlow GitHub repository (tensorflow/tensorflow) latest commit SHA: '
            '9a4b3f2c7e5d1b8a6c9f0d2e4a7b3c1f5e6d8a9b. '
            'TensorFlow is Google\'s open-source machine learning framework with over 180k stars on GitHub.'
        ),
        'keywords': ['tensorflow', 'github', 'repository', 'commit', 'sha', '9a4b3f2c7e5d1b8a6c9f0d2e4a7b3c1f5e6d8a9b', 'google', 'machine learning'],
        'summary': 'TensorFlow GitHub latest commit SHA: 9a4b3f2c7e5d1b8a6c9f0d2e4a7b3c1f5e6d8a9b.',
        'results': [
            ('tensorflow/tensorflow - GitHub', 'github.com', 'TensorFlow: Open Source ML Framework. Latest commit: 9a4b3f2c7e5d1b8a6c9f0d2e4a7b3c1f5e6d8a9b. 180k+ stars.'),
            ('TensorFlow Commit History - GitHub', 'github.com', 'Recent commits to tensorflow/tensorflow. Latest: 9a4b3f2c7e5d1b8a6c9f0d2e4a7b3c1f5e6d8a9b.'),
            ('TensorFlow Repository Stats - GitHub', 'github.com', 'tensorflow/tensorflow: 180k+ stars. Latest commit SHA: 9a4b3f2c7e5d1b8a6c9f0d2e4a7b3c1f5e6d8a9b.'),
            ('TensorFlow on GitHub - TensorFlow.org', 'www.tensorflow.org', 'TensorFlow\'s source code on GitHub. Latest commit: 9a4b3f2c7e5d1b8a6c9f0d2e4a7b3c1f5e6d8a9b.'),
            ('TensorFlow Latest Release - PyPI', 'pypi.org', 'TensorFlow latest release. GitHub commit: 9a4b3f2c7e5d1b8a6c9f0d2e4a7b3c1f5e6d8a9b.'),
            ('TensorFlow GitHub Overview - Towards Data Science', 'towardsdatascience.com', 'TensorFlow GitHub repository overview. Latest commit hash: 9a4b3f2c7e5d1b8a6c9f0d2e4a7b3c1f5e6d8a9b.'),
            ('TensorFlow Development - Dev.to', 'dev.to', 'TensorFlow on GitHub: commit 9a4b3f2c7e5d1b8a6c9f0d2e4a7b3c1f5e6d8a9b. Active development continues.'),
            ('TensorFlow GitHub - Reddit', 'www.reddit.com', 'r/MachineLearning: TensorFlow repo latest commit 9a4b3f2c7e5d1b8a6c9f0d2e4a7b3c1f5e6d8a9b.'),
        ],
        'knowledge_facts': [
            ('Repository', 'tensorflow/tensorflow'),
            ('Latest commit', '9a4b3f2c7e5d1b8a6c9f0d2e4a7b3c1f5e6d8a9b'),
            ('Stars', '180k+'),
        ],
    },
    # ------ Google Search--34 ------
    {
        'slug': 'distance_earth_mars',
        'name': 'Distance from Earth to Mars',
        'query_text': 'distance from Earth to Mars today',
        'answer_token': (
            'The average distance from Earth to Mars is approximately 225 million km (140 million miles). '
            'Mars and Earth orbit the Sun at different speeds, so the actual distance varies from '
            '54.6 million km at closest approach to 401 million km when on opposite sides of the Sun.'
        ),
        'keywords': ['earth', 'mars', 'distance', '225 million', 'km', 'miles', 'planet', 'orbit', 'closest approach'],
        'summary': 'The average distance from Earth to Mars is about 225 million km.',
        'results': [
            ('How Far Is Mars From Earth? - NASA', 'www.nasa.gov', 'The average distance from Earth to Mars is about 225 million km. Current distance varies depending on orbital positions.'),
            ('Earth-Mars Distance Calculator - Space.com', 'www.space.com', 'Mars is currently about 225 million km from Earth on average. Closest approach can bring the planets within 54.6 million km.'),
            ('Mars Distance from Earth - Wikipedia', 'en.wikipedia.org', 'The average distance between Earth and Mars is 225 million km (140 million miles), varying from 54.6 to 401 million km.'),
            ('How Far Away Is Mars? - Britannica', 'www.britannica.com', 'Mars orbits at an average distance of 225 million km from Earth. The actual distance depends on both planets\' orbital positions.'),
            ('Mars Distance Today - TheSkyLive', 'theskylive.com', 'Current distance from Earth to Mars. Average: 225 million km. Real-time tracking of Mars\'s position.'),
            ('Earth to Mars: How Long Does It Take? - Scientific American', 'www.scientificamerican.com', 'At an average distance of 225 million km, signals take about 12.5 minutes to reach Mars from Earth.'),
            ('Mars Distance Facts - National Geographic', 'www.nationalgeographic.com', 'The distance from Earth to Mars averages 225 million km. At closest approach, it\'s about 54.6 million km.'),
            ('Earth-Mars Distance - Reddit', 'www.reddit.com', 'r/space: Earth to Mars distance is about 225 million km on average. Closest approaches happen roughly every 26 months.'),
        ],
        'knowledge_facts': [
            ('Average distance', '225 million km'),
            ('Closest approach', '54.6 million km'),
            ('Farthest', '401 million km'),
        ],
    },
    # ------ Google Search--35 ------
    {
        'slug': 'black_holes_nature_astronomy',
        'name': 'Latest Black Hole Research Nature Astronomy',
        'query_text': 'latest research paper black holes Nature Astronomy',
        'answer_token': (
            'Latest research in Nature Astronomy on black holes: "Discovery of an intermediate-mass black hole '
            'in the Milky Way\'s nuclear star cluster." The study presents evidence for an intermediate-mass '
            'black hole with approximately 10,000 solar masses, found using advanced spectroscopic techniques.'
        ),
        'keywords': ['nature astronomy', 'black hole', 'intermediate-mass', 'research', 'paper', 'milky way', 'discovery', 'spectroscopic'],
        'summary': 'Nature Astronomy published research on an intermediate-mass black hole discovery.',
        'results': [
            ('Intermediate-mass Black Hole Discovery - Nature Astronomy', 'www.nature.com', 'New research in Nature Astronomy reports the discovery of an intermediate-mass black hole in the Milky Way\'s nuclear cluster.'),
            ('Black Hole Research Update - Nature', 'www.nature.com', 'Nature Astronomy publishes groundbreaking paper on intermediate-mass black holes. Evidence from the Milky Way\'s center.'),
            ('New Black Hole Found in Milky Way - Science Daily', 'www.sciencedaily.com', 'Scientists publish in Nature Astronomy: an intermediate-mass black hole discovered. Advanced spectroscopic analysis confirms the finding.'),
            ('Black Hole Discovery - Space.com', 'www.space.com', 'Nature Astronomy paper reveals intermediate-mass black hole in the Milky Way. A breakthrough in black hole research.'),
            ('Intermediate-Mass Black Holes Explained - Scientific American', 'www.scientificamerican.com', 'A Nature Astronomy study finds an intermediate-mass black hole. These elusive objects bridge stellar and supermassive black holes.'),
            ('Latest Black Hole Papers - arXiv', 'arxiv.org', 'Recent preprints related to the Nature Astronomy intermediate-mass black hole discovery. References and citations.'),
            ('Black Hole Research News - Phys.org', 'phys.org', 'Nature Astronomy publishes new black hole findings: intermediate-mass object detected via spectroscopy in the Milky Way.'),
            ('Black Hole Paper Discussion - Reddit', 'www.reddit.com', 'r/astrophysics: Nature Astronomy intermediate-mass black hole paper discussion. Exciting implications for galactic evolution.'),
        ],
        'knowledge_facts': [
            ('Journal', 'Nature Astronomy'),
            ('Topic', 'Intermediate-mass black hole'),
            ('Location', 'Milky Way nuclear cluster'),
        ],
    },
    # ------ Google Search--36 ------
    {
        'slug': 'nobel_prize_physics_recent',
        'name': 'Most Recent Nobel Prize in Physics',
        'query_text': 'most recent Nobel Prize Physics winner contribution',
        'answer_token': (
            'The 2023 Nobel Prize in Physics was awarded to Pierre Agostini, Ferenc Krausz, and Anne L\'Huillier '
            'for experimental methods that generate attosecond pulses of light. Their work enables the study of '
            'electron dynamics in matter at previously impossible timescales.'
        ),
        'keywords': ['nobel prize', 'physics', '2023', 'agostini', 'krausz', 'huillier', 'attosecond', 'winner', 'contribution'],
        'summary': 'The 2023 Nobel Prize in Physics went to Agostini, Krausz, and L\'Huillier for attosecond physics.',
        'results': [
            ('2023 Nobel Prize in Physics - Nobel Prize', 'www.nobelprize.org', 'The 2023 Nobel Prize in Physics was awarded to Pierre Agostini, Ferenc Krausz, and Anne L\'Huillier for attosecond light pulses.'),
            ('Nobel Prize Physics 2023 Explained - Nature', 'www.nature.com', 'Pierre Agostini, Ferenc Krausz, and Anne L\'Huillier win the 2023 Nobel Prize in Physics for attosecond science.'),
            ('2023 Physics Nobel: Attosecond Light - BBC', 'www.bbc.com', 'The 2023 Nobel Prize in Physics goes to Agostini, Krausz, and L\'Huillier for creating ultrafast attosecond light pulses.'),
            ('Nobel Prize Physics Winners 2023 - CNN', 'www.cnn.com', 'Pierre Agostini shares the 2023 Nobel Prize in Physics with Krausz and L\'Huillier for attosecond pulse generation.'),
            ('Attosecond Physics Nobel - Science Magazine', 'www.science.org', 'The 2023 Nobel Prize in Physics recognizes Agostini, Krausz, and L\'Huillier for pioneering attosecond physics experiments.'),
            ('Nobel Prize 2023 Physics Summary - Britannica', 'www.britannica.com', '2023 Nobel Prize in Physics: Agostini, Krausz, L\'Huillier — experimental methods generating attosecond light pulses.'),
            ('Who Won the 2023 Physics Nobel? - Scientific American', 'www.scientificamerican.com', 'Pierre Agostini, Ferenc Krausz, and Anne L\'Huillier won the 2023 Nobel Prize in Physics for attosecond science breakthroughs.'),
            ('2023 Nobel Physics Discussion - Reddit', 'www.reddit.com', 'r/physics: The 2023 Nobel Prize in Physics goes to Agostini, Krausz, and L\'Huillier for attosecond pulses.'),
        ],
        'knowledge_facts': [
            ('Year', '2023'),
            ('Winners', 'Agostini, Krausz, L\'Huillier'),
            ('Contribution', 'Attosecond light pulses'),
        ],
    },
    # ------ Google Search--37 ------
    {
        'slug': 'super_earth_planets',
        'name': 'Top 3 Super-Earth Planets',
        'query_text': 'top 3 super-earth planets brief introduction',
        'answer_token': (
            'Top 3 super-earth exoplanets: 1. Kepler-452b — located in the habitable zone of a Sun-like star, '
            'sometimes called "Earth\'s cousin." Radius 1.6x Earth. '
            '2. LHS 1140 b — a rocky super-earth in its star\'s habitable zone, 40 light-years away. '
            '3. TOI-715 b — a recently confirmed super-earth in the conservative habitable zone.'
        ),
        'keywords': ['super-earth', 'kepler-452b', 'habitable zone', 'exoplanet', 'lhs 1140', 'toi-715', 'planets', 'rocky', 'earth cousin'],
        'summary': 'Top super-earth exoplanets include Kepler-452b, LHS 1140 b, and TOI-715 b.',
        'results': [
            ('What Are Super-Earths? - NASA', 'www.nasa.gov', 'Super-earth exoplanets: Kepler-452b orbits in the habitable zone of a Sun-like star. Introduction to rocky worlds larger than Earth.'),
            ('Top Super-Earth Exoplanets - Space.com', 'www.space.com', 'The most promising super-earths: Kepler-452b, LHS 1140 b, and TOI-715 b. All located in their star\'s habitable zone.'),
            ('Kepler-452b: Earth\'s Cousin - Britannica', 'www.britannica.com', 'Kepler-452b is a super-earth in the habitable zone. Discovered in 2015, it\'s sometimes called "Earth 2.0."'),
            ('Super-Earth Exoplanets Explained - National Geographic', 'www.nationalgeographic.com', 'Super-earths like Kepler-452b are rocky planets larger than Earth. Many orbit in the habitable zone of their stars.'),
            ('Most Habitable Super-Earths - Scientific American', 'www.scientificamerican.com', 'Top habitable super-earths: Kepler-452b, LHS 1140 b, TOI-715 b. Brief introduction to each planet\'s characteristics.'),
            ('Super-Earth Planet Guide - European Space Agency', 'www.esa.int', 'Guide to super-earth exoplanets in the habitable zone. Kepler-452b and LHS 1140 b are prime targets for future study.'),
            ('Super-Earths: Could They Support Life? - Nature', 'www.nature.com', 'Research on super-earth habitability. Kepler-452b, in the habitable zone of a Sun-like star, is a key target.'),
            ('Super-Earth Planets Discussion - Reddit', 'www.reddit.com', 'r/space: Top super-earths — Kepler-452b in the habitable zone is the most Earth-like exoplanet discovered.'),
        ],
        'knowledge_facts': [
            ('#1', 'Kepler-452b — habitable zone'),
            ('#2', 'LHS 1140 b'),
            ('#3', 'TOI-715 b'),
        ],
    },
    # ------ Google Search--38 ------
    {
        'slug': 'next_solar_eclipse_north_america',
        'name': 'Next Solar Eclipse North America',
        'query_text': 'next visible solar eclipse North America date one after',
        'answer_token': (
            'The next major total solar eclipse visible from North America will occur on August 23, 2044. '
            'The path of totality will cross through Montana, North Dakota, and parts of Canada. '
            'The following solar eclipse visible from North America after that will be on August 12, 2045.'
        ),
        'keywords': ['solar eclipse', 'north america', 'august 23 2044', '2044', 'next', 'total', 'visible', 'path of totality', 'montana'],
        'summary': 'The next solar eclipse visible from North America is on August 23, 2044.',
        'results': [
            ('Next Solar Eclipse in North America - NASA', 'www.nasa.gov', 'The next total solar eclipse visible from North America occurs on August 23, 2044. Path crosses Montana and North Dakota.'),
            ('Solar Eclipse Calendar - TimeAndDate', 'www.timeanddate.com', 'August 23, 2044: Next total solar eclipse visible from North America. After that: August 12, 2045.'),
            ('2044 Solar Eclipse Guide - Space.com', 'www.space.com', 'The next solar eclipse for North America: August 23, 2044. A total eclipse with a path through the northern US and Canada.'),
            ('Solar Eclipses 2024-2050 - Wikipedia', 'en.wikipedia.org', 'The next total solar eclipse visible in North America: August 23, 2044. The path of totality crosses Montana.'),
            ('Upcoming Solar Eclipses - GreatAmericanEclipse.com', 'www.greatamericaneclipse.com', 'North America\'s next solar eclipse: August 23, 2044. Planning guide and best viewing locations.'),
            ('When Is the Next Solar Eclipse? - LiveScience', 'www.livescience.com', 'After the 2024 eclipse, North America waits until August 23, 2044 for the next total solar eclipse.'),
            ('Solar Eclipse Schedule - National Geographic', 'www.nationalgeographic.com', 'The next total solar eclipse visible from North America will occur on August 23, 2044. Complete schedule.'),
            ('Solar Eclipse Discussion - Reddit', 'www.reddit.com', 'r/astronomy: The next North American solar eclipse is August 23, 2044. Mark your calendars!'),
        ],
        'knowledge_facts': [
            ('Next eclipse', 'August 23, 2044'),
            ('Type', 'Total solar eclipse'),
            ('Region', 'North America'),
        ],
    },
    # ------ Google Search--39 ------
    {
        'slug': 'trending_travel_destinations_2024_asia',
        'name': 'Trending Travel Destinations 2024 Asia',
        'query_text': 'top 10 trending travel destinations 2024 blog Asia',
        'answer_token': (
            'Top trending travel destinations in Asia for 2024: '
            '1. Tokyo, Japan — cultural experiences and food scene; '
            '2. Seoul, South Korea — K-pop culture and historic temples; '
            '3. Bali, Indonesia — tropical beaches and wellness retreats; '
            '4. Bangkok, Thailand — street food and temples; '
            '5. Hanoi, Vietnam — old quarter and street food.'
        ),
        'keywords': ['tokyo', 'seoul', '2024', 'travel', 'destinations', 'asia', 'trending', 'bali', 'bangkok', 'japan', 'korea'],
        'summary': 'Top trending Asian travel destinations for 2024 include Tokyo and Seoul.',
        'results': [
            ('Top Travel Destinations in Asia 2024 - Lonely Planet', 'www.lonelyplanet.com', 'Best places to visit in Asia 2024: Tokyo, Seoul, Bali, Bangkok, Hanoi. Trending destinations for travelers.'),
            ('2024 Travel Trends: Asia - TripAdvisor', 'www.tripadvisor.com', 'Trending Asian travel destinations for 2024: Tokyo and Seoul lead the list. Full top 10 with reviews and tips.'),
            ('Asia Travel Guide 2024 - Conde Nast Traveler', 'www.cntraveler.com', 'Where to go in Asia in 2024: Tokyo, Seoul, Bali top the trending destinations. Best times to visit and travel tips.'),
            ('Best Asian Destinations 2024 - National Geographic Travel', 'www.nationalgeographic.com', '2024 must-visit destinations in Asia: Tokyo for culture, Seoul for K-pop, Bali for beaches. Full travel guide.'),
            ('Trending Travel 2024: Asia Edition - Travel + Leisure', 'www.travelandleisure.com', 'Top 10 trending travel destinations in Asia for 2024. Tokyo and Seoul are the most searched destinations.'),
            ('2024 Asia Travel Blog - Nomadic Matt', 'www.nomadicmatt.com', 'My top Asia travel picks for 2024: Tokyo, Seoul, Bangkok, Bali, and Hanoi. Budget tips and itineraries.'),
            ('Where to Travel in Asia 2024 - Forbes Travel', 'www.forbes.com', 'Asia\'s hottest travel destinations for 2024: Tokyo, Seoul, Bali lead. Trending searches show growing interest.'),
            ('Asia 2024 Travel Discussion - Reddit', 'www.reddit.com', 'r/travel: Top trending Asian destinations for 2024 — Tokyo and Seoul are the most popular picks.'),
        ],
        'knowledge_facts': [
            ('#1', 'Tokyo, Japan'),
            ('#2', 'Seoul, South Korea'),
            ('#3', 'Bali, Indonesia'),
        ],
    },
    # ------ Google Search--40 ------
    {
        'slug': 'mount_kilimanjaro_elevation',
        'name': 'Mount Kilimanjaro Elevation',
        'query_text': 'Mount Kilimanjaro elevation',
        'answer_token': (
            'Mount Kilimanjaro stands at 5,895 meters (19,341 feet) above sea level, making it the highest peak '
            'in Africa. Located in Tanzania near the Kenyan border, Kilimanjaro is a dormant volcano and one of '
            'the Seven Summits.'
        ),
        'keywords': ['kilimanjaro', 'elevation', '5,895', '19,341', 'meters', 'feet', 'africa', 'tanzania', 'highest', 'mountain', 'volcano'],
        'summary': 'Mount Kilimanjaro is 5,895 m (19,341 ft) — the highest point in Africa.',
        'results': [
            ('Mount Kilimanjaro - Wikipedia', 'en.wikipedia.org', 'Mount Kilimanjaro elevation: 5,895 meters (19,341 feet). The highest peak in Africa, located in Tanzania.'),
            ('Kilimanjaro Facts - National Geographic', 'www.nationalgeographic.com', 'Kilimanjaro rises to 5,895 m (19,341 ft). Africa\'s tallest mountain is a dormant volcano in Tanzania.'),
            ('Mount Kilimanjaro Height - Britannica', 'www.britannica.com', 'Mount Kilimanjaro: 5,895 metres (19,341 feet) above sea level. The highest point on the African continent.'),
            ('Climbing Kilimanjaro: Elevation Guide - REI', 'www.rei.com', 'Kilimanjaro elevation: 5,895 m (19,341 ft). A trekking guide to Africa\'s highest peak.'),
            ('Kilimanjaro Peak Elevation - PeakBagger', 'www.peakbagger.com', 'Mount Kilimanjaro, Uhuru Peak: 5,895 meters / 19,341 feet. Highest point in Africa and one of the Seven Summits.'),
            ('Kilimanjaro Mountain Profile - AllTrails', 'www.alltrails.com', 'Mount Kilimanjaro elevation profile: summit at 5,895 m (19,341 ft). Popular trekking routes and difficulty ratings.'),
            ('How Tall Is Kilimanjaro? - Adventure Alternative', 'www.adventurealternative.com', 'Mount Kilimanjaro stands at 5,895 meters (19,341 feet). Guide to the elevation and climbing routes.'),
            ('Kilimanjaro Elevation - Reddit', 'www.reddit.com', 'r/mountaineering: Kilimanjaro at 5,895 m (19,341 ft) — highest free-standing mountain in the world.'),
        ],
        'knowledge_facts': [
            ('Elevation', '5,895 m (19,341 ft)'),
            ('Location', 'Tanzania, Africa'),
            ('Type', 'Dormant stratovolcano'),
        ],
    },
    # ------ Google Search--41 ------
    {
        'slug': 'los_angeles_air_pollution',
        'name': 'Los Angeles Air Pollution',
        'query_text': 'Los Angeles current air pollution level statistics',
        'answer_token': (
            'Los Angeles current air quality: AQI 88 (Moderate). '
            'PM2.5 concentration: 25.4 ug/m3. PM10: 42 ug/m3. Ozone: 62 ppb. '
            'Air quality in Los Angeles is moderate today, with PM2.5 as the primary pollutant.'
        ),
        'keywords': ['los angeles', 'air pollution', 'aqi', 'aqi 88', 'pm2.5', 'statistics', 'moderate', 'ozone', 'smog'],
        'summary': 'Los Angeles air quality is moderate with AQI 88 and PM2.5 as the primary pollutant.',
        'results': [
            ('Los Angeles Air Quality Index - IQAir', 'www.iqair.com', 'Los Angeles real-time air quality: AQI 88 (Moderate). PM2.5: 25.4 ug/m3. Updated hourly.'),
            ('LA AQI Today - AQICN', 'aqicn.org', 'Los Angeles, California air quality index: AQI 88. PM2.5 is the dominant pollutant. Forecast and historical data.'),
            ('Air Quality Map: Los Angeles - AirNow', 'www.airnow.gov', 'Los Angeles AQI 88 — Moderate air quality. PM2.5 primary pollutant. Sensitive groups should limit outdoor activity.'),
            ('LA Air Pollution Statistics - SCAQMD', 'www.aqmd.gov', 'South Coast Air Quality Management District: Los Angeles AQI 88 today. PM2.5 at 25.4 ug/m3. Ozone: 62 ppb.'),
            ('Los Angeles Smog Update - LA Times', 'www.latimes.com', 'Current LA air quality: AQI 88 (Moderate). PM2.5 levels elevated. Statistics show improvement from last decade.'),
            ('LA Air Quality Today - AccuWeather', 'www.accuweather.com', 'Los Angeles air quality: AQI 88. Moderate conditions. PM2.5 at 25.4 ug/m3. Check hourly updates.'),
            ('Air Quality in California - EPA', 'www.epa.gov', 'Los Angeles County air quality statistics: AQI 88. PM2.5 remains the primary concern in the region.'),
            ('LA Air Quality - Reddit', 'www.reddit.com', 'r/LosAngeles: Current AQI is 88 (Moderate). PM2.5 levels typical for this time of year.'),
        ],
        'knowledge_facts': [
            ('AQI', '88 (Moderate)'),
            ('PM2.5', '25.4 ug/m3'),
            ('Location', 'Los Angeles, CA'),
        ],
    },
    # ------ Google Search--42 ------
    {
        'slug': 'american_english_british_english_differences',
        'name': 'American vs British English Differences',
        'query_text': 'American English British English major differences article',
        'answer_token': (
            'Major differences between American English and British English: '
            'Spelling: color vs colour, honor vs honour, traveled vs travelled. '
            'Vocabulary: elevator vs lift, apartment vs flat, trunk vs boot. '
            'Grammar: "I have gotten" (American) vs "I have got" (British). '
            'Pronunciation: schedule, aluminum, and tomato are pronounced differently.'
        ),
        'keywords': ['american english', 'british english', 'differences', 'color vs colour', 'spelling', 'vocabulary', 'grammar', 'pronunciation'],
        'summary': 'Key differences between American and British English: spelling (color vs colour), vocabulary, and grammar.',
        'results': [
            ('American vs British English - Britannica', 'www.britannica.com', 'Major differences: American English uses "color" while British English uses "colour." Comprehensive comparison article.'),
            ('British vs American English Guide - Oxford Languages', 'languages.oup.com', 'The key differences between American and British English: spelling (color vs colour), vocabulary, and grammar.'),
            ('American English vs British English - Cambridge Dictionary', 'dictionary.cambridge.org', 'A guide to American English and British English differences. Color vs colour, apartment vs flat, and more.'),
            ('Differences Between US and UK English - BBC', 'www.bbc.com', 'From color vs colour to elevator vs lift: the major differences between American English and British English explained.'),
            ('American vs British English Article - Grammarly', 'www.grammarly.com', 'American English vs British English: spelling (color vs colour), vocabulary (truck vs lorry), and pronunciation differences.'),
            ('US vs UK English Comparison - Merriam-Webster', 'www.merriam-webster.com', 'How American English and British English diverged: color vs colour, honor vs honour, and other spelling differences.'),
            ('British vs American English - ThoughtCo', 'www.thoughtco.com', 'Comprehensive article on American English vs British English differences: color vs colour, grammar, and vocabulary.'),
            ('American vs British English - Reddit', 'www.reddit.com', 'r/linguistics: American English uses "color" while British English uses "colour." Major differences discussed.'),
        ],
        'knowledge_facts': [
            ('Spelling', 'color vs colour, honor vs honour'),
            ('Vocabulary', 'elevator vs lift'),
            ('Grammar', 'gotten vs got'),
        ],
    },
]


def _seed_task_topics(db, Topic, SearchResult, PaaQuestion, RelatedQuery, KnowledgeFact):
    """Seed all WebVoyager task-driven topics."""
    import json
    import random

    # Also fix the Steam topic's player count to include 1,242,850
    steam = Topic.query.filter_by(slug='steam_most_played_games').first()
    if steam:
        steam.answer_token = (
            'Steam most played games by current players: '
            '#1 Counter-Strike 2: 1,242,850 current players in-game; '
            '#2 Dota 2: 658,434 players; '
            '#3 PUBG: 412,287 players; '
            '#4 Elden Ring: 187,532 players; '
            '#5 Grand Theft Auto V: 156,890 players.'
        )
        # Update the first result snippet to include the exact number
        for r in steam.results:
            if r.rank == 0:
                r.snippet = (
                    'See the top 100 most played games on Steam right now, updated in real time. '
                    'Counter-Strike 2 tops the chart with 1,242,850 concurrent players, '
                    'followed by Dota 2 at 658,434 and PUBG at 412,287.'
                )
                break
        db.session.commit()

    for td in TASK_TOPICS:
        slug = td['slug']
        if Topic.query.filter_by(slug=slug).first():
            continue

        topic = Topic(
            slug=slug,
            name=td['name'],
            wiki_title=td['name'],
            summary=td['summary'],
            wiki_url='',
            query_text=td['query_text'],
            keywords_json=json.dumps(td['keywords']),
            answer_token=td['answer_token'],
            result_count=random.Random(_det_hash(slug)).randint(1_000_000, 500_000_000),
            search_time=round(random.Random(_det_hash(slug + '_t')).uniform(0.22, 0.79), 2),
            knowledge_type='topic',
            knowledge_panel_json=json.dumps({}),
        )
        db.session.add(topic)
        db.session.flush()

        # Results
        for i, (title, domain, snippet) in enumerate(td['results']):
            db.session.add(SearchResult(
                topic_id=topic.id,
                title=title,
                url=f'https://{domain}/{slug}',
                display_url=domain,
                snippet=snippet,
                source=domain.split('.')[1] if '.' in domain else domain,
                rank=i,
            ))

        # Knowledge facts
        for i, (k, v) in enumerate(td.get('knowledge_facts', [])):
            db.session.add(KnowledgeFact(topic_id=topic.id, key=k, value=v, rank=i))

        # PAA (generic)
        paa_qs = [
            (f'What is {td["name"]}?', f'{td["name"]}: {td["summary"][:200]}'),
            (f'Why is {td["name"]} important?', f'{td["name"]} is significant because of its impact and relevance.'),
        ]
        for i, (q, a) in enumerate(paa_qs):
            db.session.add(PaaQuestion(topic_id=topic.id, question=q, answer=a, rank=i))

    db.session.commit()


def _seed_scraped_topics(db, Topic, SearchResult, PaaQuestion, RelatedQuery, KnowledgeFact):
    """Replay topics dumped from the shipped Round 1 instance_seed DB.

    Round 1 polish added ~170 rich topics directly into the SQLite DB
    (bypassing seed_data.py). To make builds-from-source reproducible we
    dumped those rows into scraped_topics.json. This function inserts them
    back so a fresh rebuild produces a comparable topic universe.
    """
    scraped_path = os.path.join(HERE, 'scraped_topics.json')
    if not os.path.exists(scraped_path):
        return
    with open(scraped_path) as f:
        topics = json.load(f)

    inserted = 0
    for td in topics:
        slug = td['slug']
        if Topic.query.filter_by(slug=slug).first():
            continue

        topic = Topic(
            slug=slug,
            name=td['name'],
            wiki_title=td.get('wiki_title') or td['name'],
            summary=td.get('summary') or '',
            wiki_url=td.get('wiki_url') or '',
            query_text=td.get('query_text') or td['name'],
            keywords_json=td.get('keywords_json') or '[]',
            answer_token=td.get('answer_token') or '',
            images_json=td.get('images_json') or '[]',
            hero_image=td.get('hero_image') or '',
            result_count=td.get('result_count') or 0,
            search_time=td.get('search_time') or 0.5,
            knowledge_type=td.get('knowledge_type') or '',
            knowledge_panel_json=td.get('knowledge_panel_json') or '{}',
        )
        db.session.add(topic)
        db.session.flush()

        for r in td.get('results', []):
            db.session.add(SearchResult(
                topic_id=topic.id,
                title=r['title'], url=r['url'],
                display_url=r['display_url'], snippet=r['snippet'],
                source=r['source'], rank=r['rank'], image=r.get('image') or '',
            ))
        for p in td.get('paa', []):
            db.session.add(PaaQuestion(
                topic_id=topic.id, question=p['question'],
                answer=p['answer'], rank=p['rank'],
            ))
        for r in td.get('related', []):
            db.session.add(RelatedQuery(
                topic_id=topic.id, term=r['term'], rank=r['rank'],
            ))
        for k in td.get('knowledge_facts', []):
            db.session.add(KnowledgeFact(
                topic_id=topic.id, key=k['key'], value=k['value'], rank=k['rank'],
            ))
        inserted += 1

    if inserted:
        db.session.commit()
        print(f"[seed] _seed_scraped_topics inserted {inserted} topics")


def _seed_pop_topics(db, Topic, SearchResult, PaaQuestion, RelatedQuery, KnowledgeFact):
    """R2/R3 expansion: seed 600+ popular general-interest topics.

    Each pop topic gets 8 synthetic results from a fixed provider list, 4 PAA
    questions, 6 related queries, plus knowledge facts. Everything is
    derived deterministically from the slug so rebuilds are byte-identical.
    """
    POP_TOPICS = []
    try:
        from pop_topics_data import POP_TOPICS as _R2_TOPICS
        POP_TOPICS = list(_R2_TOPICS)
    except ImportError:
        pass
    try:
        from pop_topics_data_r3 import POP_TOPICS_R3
        _seen = {t[0] for t in POP_TOPICS}
        for t in POP_TOPICS_R3:
            if t[0] not in _seen:
                POP_TOPICS.append(t)
    except ImportError:
        pass
    if not POP_TOPICS:
        return

    # Per-topic providers: deterministic pick from a stable pool.
    _PROVIDERS = ['wikipedia', 'britannica', 'youtube', 'reddit', 'nytimes', 'bbc',
                  'medium', 'github', 'quanta', 'khan', 'nature', 'guardian',
                  'forbes', 'imdb', 'goodreads', 'allmusic']
    _PROVIDER_DOMAIN = {
        'wikipedia': 'en.wikipedia.org', 'britannica': 'www.britannica.com',
        'youtube': 'www.youtube.com', 'reddit': 'www.reddit.com',
        'nytimes': 'www.nytimes.com', 'bbc': 'www.bbc.com',
        'medium': 'medium.com', 'github': 'github.com',
        'quanta': 'www.quantamagazine.org', 'khan': 'www.khanacademy.org',
        'nature': 'www.nature.com', 'guardian': 'www.theguardian.com',
        'forbes': 'www.forbes.com', 'imdb': 'www.imdb.com',
        'goodreads': 'www.goodreads.com', 'allmusic': 'www.allmusic.com',
    }
    _TITLE_TPL = {
        'wikipedia': '{name} - Wikipedia',
        'britannica': '{name} | Britannica',
        'youtube': '{name} - YouTube',
        'reddit': 'r/{slug} - Reddit',
        'nytimes': '{name} - The New York Times',
        'bbc': '{name} - BBC News',
        'medium': '{name} on Medium',
        'github': '{name} on GitHub',
        'quanta': '{name} - Quanta Magazine',
        'khan': '{name} | Khan Academy',
        'nature': '{name} | Nature',
        'guardian': '{name} | The Guardian',
        'forbes': '{name} - Forbes',
        'imdb': '{name} - IMDb',
        'goodreads': '{name} - Goodreads',
        'allmusic': '{name} - AllMusic',
    }
    _URL_TPL = {
        'wikipedia': 'https://en.wikipedia.org/wiki/{slug}',
        'britannica': 'https://www.britannica.com/topic/{slug}',
        'youtube': 'https://www.youtube.com/results?search_query={slug}',
        'reddit': 'https://www.reddit.com/r/{slug}/',
        'nytimes': 'https://www.nytimes.com/topic/{slug}',
        'bbc': 'https://www.bbc.com/news/topics/{slug}',
        'medium': 'https://medium.com/tag/{slug}',
        'github': 'https://github.com/topics/{slug}',
        'quanta': 'https://www.quantamagazine.org/tag/{slug}/',
        'khan': 'https://www.khanacademy.org/{slug}',
        'nature': 'https://www.nature.com/subjects/{slug}',
        'guardian': 'https://www.theguardian.com/world/{slug}',
        'forbes': 'https://www.forbes.com/profile/{slug}',
        'imdb': 'https://www.imdb.com/find?q={slug}',
        'goodreads': 'https://www.goodreads.com/search?q={slug}',
        'allmusic': 'https://www.allmusic.com/search/all/{slug}',
    }

    inserted = 0
    for slug, name, qtext, summary, answer_token, kfacts in POP_TOPICS:
        if Topic.query.filter_by(slug=slug).first():
            continue

        rng = random.Random(_det_hash(slug + '_pop'))

        # Build an 8-provider permutation (wikipedia always first)
        providers = ['wikipedia'] + rng.sample(
            [p for p in _PROVIDERS if p != 'wikipedia'], 7
        )

        topic = Topic(
            slug=slug,
            name=name,
            wiki_title=name,
            summary=summary,
            wiki_url=_URL_TPL['wikipedia'].format(slug=slug),
            query_text=qtext,
            keywords_json=json.dumps(
                [w.lower() for w in name.split() if len(w) > 2] + [slug]
            ),
            answer_token=answer_token,
            result_count=rng.randint(1_000_000, 500_000_000),
            search_time=round(rng.uniform(0.22, 0.79), 2),
            knowledge_type='topic' if kfacts else '',
            knowledge_panel_json=json.dumps({
                'title': name,
                'subtitle': '',
                'description': summary,
                'facts': [[k, v] for k, v in kfacts],
            }) if kfacts else json.dumps({}),
        )
        db.session.add(topic)
        db.session.flush()

        # 8 results
        for rank, prov in enumerate(providers):
            title = _TITLE_TPL[prov].format(name=name, slug=slug)
            url = _URL_TPL[prov].format(slug=slug)
            display_url = _PROVIDER_DOMAIN[prov]
            snippet_pool = [
                f'{name}: {summary[:200]}',
                f'Learn about {name} - history, key facts, and modern significance. {summary[:160]}',
                f'{name} explained. {summary[:180]}',
                f'Browse the latest about {name}. {summary[:150]}',
                f'Everything you need to know about {name}. {summary[:170]}',
                f'r/{slug}: community discussion of {name}. {summary[:140]}',
                f'{name} overview - origin, timeline, and notable facts. {summary[:150]}',
                f'A deep dive into {name}. {summary[:170]}',
            ]
            snippet = snippet_pool[rank % len(snippet_pool)]
            db.session.add(SearchResult(
                topic_id=topic.id, title=title, url=url,
                display_url=display_url, snippet=snippet,
                source=prov, rank=rank, image=''
            ))

        # 4 PAA
        paa_qs = [
            (f'What is {name}?', f'{name}: {summary[:280]}'),
            (f'Why is {name} important?',
             f'{name} is significant because of its role and influence as described in the available references. {summary[:200]}'),
            (f'Where can I learn more about {name}?',
             f'Reliable references for {name} include Wikipedia, Britannica, and major news outlets. {summary[:160]}'),
            (f'What are the key facts about {name}?',
             f'The knowledge panel for {name} lists the most-asked attributes. {summary[:180]}'),
        ]
        for i, (q, a) in enumerate(paa_qs):
            db.session.add(PaaQuestion(
                topic_id=topic.id, question=q, answer=a, rank=i
            ))

        # 6 related queries (deterministic from slug)
        suffixes = ['definition', 'history', 'examples', 'facts', 'images', 'news']
        rng2 = random.Random(_det_hash(slug + '_rel'))
        rng2.shuffle(suffixes)
        base_lower = name.lower()
        for i, sfx in enumerate(suffixes):
            db.session.add(RelatedQuery(
                topic_id=topic.id, term=f'{base_lower} {sfx}', rank=i
            ))

        # Knowledge facts
        for i, (k, v) in enumerate(kfacts):
            db.session.add(KnowledgeFact(
                topic_id=topic.id, key=k, value=v, rank=i
            ))
        # R3: Always append two derived reference facts so every pop topic
        # has at least 2 entries even when the curated kfacts list is empty.
        # Deterministic — derived from slug only.
        base_rank = len(kfacts)
        db.session.add(KnowledgeFact(
            topic_id=topic.id, key='Wikipedia',
            value=f'en.wikipedia.org/wiki/{slug}', rank=base_rank,
        ))
        db.session.add(KnowledgeFact(
            topic_id=topic.id, key='Reference',
            value=f'Britannica, Wikipedia, primary sources', rank=base_rank + 1,
        ))

        inserted += 1

    if inserted:
        db.session.commit()
        print(f"[seed] _seed_pop_topics inserted {inserted} new topics")


# ----------------------------------------------------------------------------
# R4 enrichment — adds result_type/breadcrumb/favicon to every SearchResult
# and appends ~5 deeper results per topic so the SERP feels denser and more
# real (organic, featured, ad). Deterministic — keyed off topic slug + rank.
# ----------------------------------------------------------------------------

_R4_DEEP_PROVIDERS = [
    # (provider, domain, title_template, url_template, snippet_template)
    ('stackoverflow', 'stackoverflow.com',
     'Questions tagged [{slug}] - Stack Overflow',
     'https://stackoverflow.com/questions/tagged/{slug}',
     'Top voted questions tagged [{slug}] on Stack Overflow. {summary_120}'),
    ('archive', 'archive.org',
     '{name} : Free Download, Borrow, and Streaming - Internet Archive',
     'https://archive.org/details/{slug}',
     'Browse archived books, papers, audio, and video about {name}. {summary_100}'),
    ('jstor', 'www.jstor.org',
     '{name} on JSTOR',
     'https://www.jstor.org/topic/{slug}/',
     'JSTOR scholarly resources on {name}. Browse 2,400+ articles, primary sources, and chapters.'),
    ('scholar', 'scholar.google.com',
     '{name} - Google Scholar',
     'https://scholar.google.com/scholar?q={slug}',
     'Search peer-reviewed papers, theses, books, and conference proceedings about {name}.'),
    ('wayback', 'web.archive.org',
     'Wayback Machine: {name}',
     'https://web.archive.org/web/*/{slug}',
     'Archived web snapshots related to {name}. Over 600 billion captures from 1996-present.'),
    ('quora', 'www.quora.com',
     '{name} - Quora',
     'https://www.quora.com/topic/{slug}',
     'Read questions and expert answers about {name} on Quora. {summary_100}'),
    ('substack', 'substack.com',
     'Best {name} newsletters - Substack',
     'https://substack.com/discover/category/{slug}',
     'Independent writers publishing in-depth essays and newsletters about {name}.'),
    ('hackernews', 'news.ycombinator.com',
     '{name} - Hacker News',
     'https://news.ycombinator.com/from?site={slug}',
     'Recent Hacker News submissions and discussions about {name}.'),
    ('archdaily', 'www.archdaily.com',
     '{name} - ArchDaily',
     'https://www.archdaily.com/tag/{slug}',
     'Architectural projects, news, and competitions related to {name}.'),
    ('jstor_daily', 'daily.jstor.org',
     '{name} | JSTOR Daily',
     'https://daily.jstor.org/tag/{slug}/',
     'Long-form essays drawing on JSTOR scholarship about {name}.'),
    ('researchgate', 'www.researchgate.net',
     '{name} - ResearchGate',
     'https://www.researchgate.net/topic/{slug}',
     'Connect with researchers and access publications about {name} on ResearchGate.'),
    ('pubmed', 'pubmed.ncbi.nlm.nih.gov',
     '{name} - PubMed search',
     'https://pubmed.ncbi.nlm.nih.gov/?term={slug}',
     'Citations from MEDLINE and life-science journals indexed for {name}.'),
]

# Featured-result template (rank-0 override). Reused across all topics so
# every SERP has at least one rich answer-style card.
_FEATURED_PROVIDER = {
    'name': 'wikipedia', 'domain': 'en.wikipedia.org',
}


def _breadcrumb_for(display_url, url, slug):
    """en.wikipedia.org › wiki › Python — Google-style breadcrumb."""
    if not display_url:
        return ''
    try:
        from urllib.parse import urlparse
        p = urlparse(url or '')
        path = p.path.strip('/')
        if not path:
            return display_url
        parts = [seg for seg in path.split('/') if seg][:4]
        # Title-case the last segment, swap underscores for spaces.
        if parts:
            parts[-1] = parts[-1].replace('_', ' ').replace('-', ' ').title()
        return display_url + ' › ' + ' › '.join(parts)
    except Exception:
        return display_url


def _favicon_for(display_url):
    if not display_url:
        return ''
    return f'https://www.google.com/s2/favicons?domain={display_url}&sz=32'


def _seed_r4_enrichment(db, Topic, SearchResult):
    """Backfill result_type/breadcrumb/favicon + add ~5 deep results per topic.

    Idempotent: detects existing enrichment by checking if any SearchResult
    row already has a non-empty favicon and >= rank 10 row.
    """
    # Idempotency gate — once enrichment has run, every result has a non-empty
    # favicon. (Existing rank>=10 rows from scraped_topics.json predate R4 so
    # we can't gate on rank alone.)
    sample = SearchResult.query.filter(SearchResult.favicon != '').first()
    if sample is not None:
        return

    topics = Topic.query.order_by(Topic.id).all()
    deep_added = 0
    enriched = 0
    for t in topics:
        existing = list(t.results)
        # Backfill metadata on existing rows
        for r in existing:
            r.breadcrumb = _breadcrumb_for(r.display_url, r.url, t.slug)
            r.favicon = _favicon_for(r.display_url)
            if r.rank == 0:
                r.result_type = 'featured'
            else:
                r.result_type = 'organic'
            enriched += 1

        # Pick 5 deterministic deep providers
        rng = random.Random(_det_hash(t.slug + '_r4_deep'))
        # Exclude providers that already match the topic's existing display_urls
        existing_domains = {r.display_url for r in existing}
        pool = [p for p in _R4_DEEP_PROVIDERS if p[1] not in existing_domains]
        deep = rng.sample(pool, min(5, len(pool)))

        name = t.name or t.slug.replace('_', ' ').title()
        summary = (t.summary or f'{name} — overview, history, and key facts.')
        s100 = summary[:100]
        s120 = summary[:120]

        next_rank = max((r.rank for r in existing), default=-1) + 1
        # rank base for deep results sits at >= max(10, existing_max+1) so we
        # never collide with rows whose rank already exceeds 9 (some scraped
        # topics in scraped_topics.json carry rank up to 17).
        next_rank = max(next_rank, 10)
        for i, (prov, domain, title_tpl, url_tpl, snip_tpl) in enumerate(deep):
            title = title_tpl.format(name=name, slug=t.slug)
            url = url_tpl.format(name=name, slug=t.slug)
            snippet = snip_tpl.format(
                name=name, slug=t.slug,
                summary_100=s100, summary_120=s120,
            )
            # 6% of deep results flagged as 'ad' (sponsored). Deterministic.
            rng2 = random.Random(_det_hash(t.slug + '_r4_type_' + str(i)))
            is_ad = rng2.random() < 0.06
            db.session.add(SearchResult(
                topic_id=t.id,
                title=title,
                url=url,
                display_url=domain,
                snippet=snippet,
                source=prov,
                source_type='web',
                rank=next_rank + i,
                image='',
                result_type='ad' if is_ad else 'organic',
                breadcrumb=_breadcrumb_for(domain, url, t.slug),
                favicon=_favicon_for(domain),
            ))
            deep_added += 1

    db.session.commit()
    print(f"[seed] _seed_r4_enrichment enriched {enriched} existing rows, "
          f"added {deep_added} deep results across {len(topics)} topics")


def domain_for(provider):
    return {
        'wikipedia': 'en.wikipedia.org',
        'britannica': 'www.britannica.com',
        'nytimes': 'www.nytimes.com',
        'bbc': 'www.bbc.com',
        'youtube': 'www.youtube.com',
        'reddit': 'www.reddit.com',
        'stanford': 'plato.stanford.edu',
        'nature': 'www.nature.com',
        'sciam': 'www.scientificamerican.com',
        'nat_geo': 'www.nationalgeographic.com',
        'quanta': 'www.quantamagazine.org',
        'khan': 'www.khanacademy.org',
        'medium': 'medium.com',
        'github': 'github.com',
    }[provider]


def url_for(provider, topic_slug, topic):
    slug = topic.replace(' ', '_')
    tlow = topic.lower().replace(' ', '-')
    return {
        'wikipedia': f'https://en.wikipedia.org/wiki/{slug}',
        'britannica': f'https://www.britannica.com/topic/{tlow}',
        'nytimes': f'https://www.nytimes.com/topic/{tlow}',
        'bbc': f'https://www.bbc.com/news/topics/{topic_slug}',
        'youtube': f'https://www.youtube.com/results?search_query={topic.replace(" ", "+")}',
        'reddit': f'https://www.reddit.com/r/{topic_slug}/',
        'stanford': f'https://plato.stanford.edu/entries/{tlow}/',
        'nature': f'https://www.nature.com/subjects/{tlow}',
        'sciam': f'https://www.scientificamerican.com/topic/{topic_slug}/',
        'nat_geo': f'https://www.nationalgeographic.com/topic/{tlow}',
        'quanta': f'https://www.quantamagazine.org/tag/{tlow}/',
        'khan': f'https://www.khanacademy.org/science/{topic_slug}',
        'medium': f'https://medium.com/tag/{tlow}',
        'github': f'https://github.com/topics/{topic_slug}',
    }[provider]


SNIPPETS = {
    'wikipedia': '{topic} is a subject of broad scholarly coverage. This Wikipedia article provides an overview of its history, key concepts, notable figures, and ongoing research. Cited sources and further reading sections are available.',
    'britannica': 'Encyclopedia Britannica presents a concise, expert-written entry on {topic}, exploring its definition, origins, major developments, and contemporary significance.',
    'nytimes': 'The latest news, analysis, and opinion about {topic} from The New York Times. Updated daily with reporting from around the world.',
    'bbc': 'Read the latest {topic} news, features, and analysis from BBC correspondents. Includes video, audio, and in-depth coverage.',
    'youtube': 'Watch the best videos about {topic}. Tutorials, documentaries, talks, and highlights curated by creators on YouTube.',
    'reddit': 'Join the r/{slug} community on Reddit — discussions, questions, news, and media about {topic} from thousands of members.',
    'stanford': 'Stanford Encyclopedia of Philosophy: a peer-reviewed scholarly article on {topic}, covering major thinkers, arguments, and critiques.',
    'nature': 'Research articles, news, and analysis related to {topic} from Nature, the leading journal of scientific research.',
    'sciam': 'Scientific American covers the science of {topic}: breakthroughs, explainers, and what researchers are learning.',
    'nat_geo': 'National Geographic explores {topic} through stunning photography, field reporting, and in-depth stories.',
    'quanta': 'Quanta Magazine explains {topic} — the ideas, the math, and the people shaping the field.',
    'khan': 'Free {topic} lessons from Khan Academy: videos, articles, and practice exercises for learners of all levels.',
    'medium': 'Browse the top {topic} stories on Medium, with perspectives from writers, practitioners, and thinkers.',
    'github': 'Discover open source projects related to {topic}. Repositories, contributors, and code examples on GitHub.',
}


# People Also Ask templates
PAA_TEMPLATES = [
    'What is {topic}?',
    'Who invented {topic}?',
    'How does {topic} work?',
    'Why is {topic} important?',
    'When was {topic} first discovered?',
    'Is {topic} safe?',
    'What are the benefits of {topic}?',
    'How to learn {topic}?',
    'What is the future of {topic}?',
    'How big is {topic}?',
    'Where is {topic} located?',
    'Who uses {topic}?',
    'What causes {topic}?',
    'How old is {topic}?',
    'Why study {topic}?',
]


def load_topics():
    # If scraped_data/topics.json is absent (production image where
    # scraped/ is .dockerignored), return empty list. seed_database iterates
    # this list with per-row gates, so an empty list is a no-op when the DB
    # is already populated from instance_seed/.
    if not os.path.exists(TOPICS_JSON):
        return []
    with open(TOPICS_JSON) as f:
        return json.load(f)


def build_results_for_topic(topic_data):
    """Build a list of 8-12 search results for this topic."""
    topic = topic_data['topic']
    slug = topic_data['slug']
    summary = topic_data.get('summary') or f'{topic} — information, background, and related resources.'
    wiki_url = topic_data.get('url') or f'https://en.wikipedia.org/wiki/{topic.replace(" ", "_")}'
    images = topic_data.get('images', [])

    # Pick 8 providers for variety
    providers = ['wikipedia', 'britannica', 'nytimes', 'bbc', 'youtube', 'reddit', 'nature', 'sciam', 'nat_geo', 'quanta']
    random.seed(_det_hash(slug, 10000))
    picked = ['wikipedia'] + random.sample([p for p in providers if p != 'wikipedia'], 7)

    results = []
    for i, prov in enumerate(picked):
        snippet = SNIPPETS[prov].format(topic=topic, slug=slug)
        if prov == 'wikipedia':
            # Use real wikipedia summary if available
            if topic_data.get('summary'):
                snippet = topic_data['summary'][:320]
        title_map = {
            'wikipedia': f'{topic_data.get("title", topic)} - Wikipedia',
            'britannica': f'{topic} | Definition, History, & Facts | Britannica',
            'nytimes': f'{topic} - The New York Times',
            'bbc': f'{topic} - BBC News',
            'youtube': f'{topic} - YouTube',
            'reddit': f'r/{slug} - Reddit',
            'stanford': f'{topic} (Stanford Encyclopedia of Philosophy)',
            'nature': f'{topic} - Latest research | Nature',
            'sciam': f'{topic} | Scientific American',
            'nat_geo': f'{topic} | National Geographic',
            'quanta': f'{topic} - Quanta Magazine',
            'khan': f'{topic} | Khan Academy',
            'medium': f'{topic} on Medium',
            'github': f'{topic} · GitHub Topics',
        }
        results.append({
            'title': title_map[prov],
            'url': url_for(prov, slug, topic),
            'display_url': domain_for(prov),
            'snippet': snippet,
            'source': prov,
            'rank': i,
            'image': images[i % len(images)] if images else '',
        })
    return results


def build_paa(topic):
    random.seed(_det_hash(topic, 50000))
    picked = random.sample(PAA_TEMPLATES, 5)
    return [q.format(topic=topic) for q in picked]


def build_related(topic, topics_data):
    """Pick 8 related queries from other topics."""
    random.seed(_det_hash(topic, 20000))
    pool = [t['topic'] for t in topics_data if t['topic'] != topic]
    picks = random.sample(pool, min(8, len(pool)))
    # Add some natural modifiers
    mods = ['history', 'definition', 'meaning', 'images', 'facts', 'video', 'news', 'examples']
    random.shuffle(mods)
    out = []
    for i, p in enumerate(picks):
        if i < 4:
            out.append(f'{p.lower()} {mods[i]}')
        else:
            out.append(p.lower())
    return out


def seed_database(db, User, Vertical, Topic, SearchResult, PaaQuestion, RelatedQuery,
                  Doodle, GoogleApp, TrendingTerm, KnowledgeFact, bcrypt):
    """Populate the database.

    Top-level idempotency gate: once every "static" table has its full
    expected row count, return immediately. This protects the byte-identical
    `/reset/<site>` invariant — a no-op `db.session.commit()` still bumps
    SQLite metadata and would break the md5sum match across container
    restarts. See `.claude/skills/seed-database/SKILL.md` Phase 5 §1.
    """
    if (Vertical.query.count() >= len(VERTICALS)
            and GoogleApp.query.count() >= len(GOOGLE_APPS)
            and TrendingTerm.query.count() >= len(TRENDING)
            and Doodle.query.count() >= len(DOODLES)
            and Topic.query.count() > 400):
        return  # fully seeded; do not even commit
    # Verticals
    for v in VERTICALS:
        existing = Vertical.query.filter_by(slug=v['slug']).first()
        if not existing:
            db.session.add(Vertical(**v))
    db.session.commit()

    # Google Apps
    for name, icon, color, url in GOOGLE_APPS:
        if not GoogleApp.query.filter_by(name=name).first():
            db.session.add(GoogleApp(name=name, icon=icon, color=color, url=url))
    db.session.commit()

    # Trending
    _direction_pool = ['up', 'up', 'up', 'flat', 'down']
    for i, term in enumerate(TRENDING):
        if not TrendingTerm.query.filter_by(term=term).first():
            # Deterministic volume/direction derived from the term — so
            # re-running the seed produces byte-identical rows.
            seed_val = abs(hash(term)) % (2**31)
            rng = random.Random(seed_val)
            db.session.add(TrendingTerm(
                term=term, rank=i+1,
                volume=rng.randint(50000, 5000000),
                trend_direction=rng.choice(_direction_pool),
            ))
    db.session.commit()

    # Doodles
    _doodle_imgs = ['paris', 'mars', 'moon', 'galaxy', 'sunflower', 'ada_lovelace',
                    'marie_curie', 'albert_einstein', 'aurora_borealis', 'cherry_blossom']
    for idx, (title, slug, desc, date) in enumerate(DOODLES):
        if not Doodle.query.filter_by(slug=slug).first():
            # Deterministic image pick keyed off the slug index so rebuilds
            # are reproducible (no random.choice non-determinism).
            img = _doodle_imgs[idx % len(_doodle_imgs)]
            db.session.add(Doodle(
                title=title, slug=slug, description=desc,
                published=datetime.strptime(date, '%Y-%m-%d'),
                image_url=f'/static/images/topics/{img}/img_hero.jpg',
            ))
    db.session.commit()

    # Topics + SearchResults
    topics_data = load_topics()
    for td in topics_data:
        if Topic.query.filter_by(slug=td['slug']).first():
            continue
        _trng = random.Random(_det_hash(td['slug']))
        topic = Topic(
            slug=td['slug'],
            name=td['topic'],
            wiki_title=td.get('title', td['topic']),
            summary=td.get('summary', ''),
            wiki_url=td.get('url', ''),
            images_json=json.dumps(td.get('images', [])),
            hero_image=(td.get('images', [None])[0] if td.get('images') else ''),
            result_count=_trng.randint(1_000_000, 500_000_000),
            search_time=round(_trng.uniform(0.22, 0.79), 2),
        )
        db.session.add(topic)
        db.session.flush()

        # Build 8 results
        results = build_results_for_topic(td)
        for r in results:
            db.session.add(SearchResult(
                topic_id=topic.id,
                title=r['title'],
                url=r['url'],
                display_url=r['display_url'],
                snippet=r['snippet'],
                source=r['source'],
                rank=r['rank'],
                image=r['image'],
            ))

        # PAA
        for i, q in enumerate(build_paa(td['topic'])):
            db.session.add(PaaQuestion(topic_id=topic.id, question=q, rank=i,
                                       answer=f'{q} A brief answer would appear here. {td.get("summary", "")[:200]}'))

        # Related queries
        for i, rq in enumerate(build_related(td['topic'], topics_data)):
            db.session.add(RelatedQuery(topic_id=topic.id, term=rq, rank=i))

        # Knowledge facts
        if td['slug'] in KNOWLEDGE_TOPICS:
            kd = KNOWLEDGE_TOPICS[td['slug']]
            topic.knowledge_type = kd['type']
            for i, (k, v) in enumerate(kd['facts']):
                db.session.add(KnowledgeFact(topic_id=topic.id, key=k, value=v, rank=i))

    db.session.commit()

    # --- Task-driven topic: Steam most played games ---
    if not Topic.query.filter_by(slug='steam_most_played_games').first():
        steam_topic = Topic(
            slug='steam_most_played_games',
            name='Steam Most Played Games',
            wiki_title='Steam Most Played Games with Current Player Counts',
            summary='The most played games on Steam right now, ranked by current concurrent player count. Counter-Strike 2 leads with over 1.2 million concurrent players, followed by Dota 2 and PUBG.',
            wiki_url='https://store.steampowered.com/charts/mostplayed',
            query_text='most played steam games current player counts',
            keywords_json=json.dumps(['steam', 'most played', 'games', 'player count', 'concurrent', 'players', 'counter-strike', 'dota', 'pubg', 'top games', 'popular', 'charts']),
            answer_token='Counter-Strike 2: 1,218,882 players; Dota 2: 658,434 players; PUBG: 412,287 players; Elden Ring: 187,532 players; Grand Theft Auto V: 156,890 players',
            result_count=245000000,
            search_time=0.42,
            knowledge_type='software',
            knowledge_panel_json=json.dumps({
                'title': 'Steam Most Played Games',
                'subtitle': 'Live player counts',
                'description': 'Real-time ranking of the most played games on Steam by concurrent player count.',
                'facts': [
                    ['#1 Counter-Strike 2', '1,218,882 current players'],
                    ['#2 Dota 2', '658,434 current players'],
                    ['#3 PUBG: Battlegrounds', '412,287 current players'],
                    ['#4 Elden Ring', '187,532 current players'],
                    ['#5 Grand Theft Auto V', '156,890 current players'],
                    ['#6 Baldur\'s Gate 3', '142,876 current players'],
                    ['#7 Apex Legends', '134,209 current players'],
                    ['#8 Team Fortress 2', '118,543 current players'],
                    ['#9 Rust', '105,678 current players'],
                    ['#10 Path of Exile 2', '98,234 current players'],
                ],
            }),
        )
        db.session.add(steam_topic)
        db.session.flush()

        steam_results = [
            {
                'title': 'Steam Charts - Most Played Games on Steam',
                'url': 'https://store.steampowered.com/charts/mostplayed',
                'display_url': 'store.steampowered.com',
                'snippet': 'See the top 100 most played games on Steam right now, updated in real time. Counter-Strike 2 tops the chart with 1,218,882 concurrent players, followed by Dota 2 at 658,434 and PUBG at 412,287.',
                'source': 'steam', 'rank': 0,
            },
            {
                'title': 'Steam & Game Stats - Valve',
                'url': 'https://store.steampowered.com/stats/',
                'display_url': 'store.steampowered.com',
                'snippet': 'Steam player count statistics. Over 33 million concurrent users. Top games: CS2 (1.2M players), Dota 2 (658K), PUBG (412K), Elden Ring (187K), GTA V (156K), BG3 (142K).',
                'source': 'steam', 'rank': 1,
            },
            {
                'title': 'SteamDB - Most Played Games on Steam',
                'url': 'https://steamdb.info/charts/',
                'display_url': 'steamdb.info',
                'snippet': 'SteamDB tracks all Steam game statistics. Most played games by current players: Counter-Strike 2 (1,218,882), Dota 2 (658,434), PUBG (412,287), Elden Ring (187,532).',
                'source': 'steamdb', 'rank': 2,
            },
            {
                'title': 'Most Played Games on Steam - GitHyp',
                'url': 'https://www.githyp.com/most-played-games-on-steam/',
                'display_url': 'www.githyp.com',
                'snippet': 'Live most played Steam games chart with player counts. Counter-Strike 2 continues to dominate with over 1.2 million players. Full list of the top 50 most popular games updated hourly.',
                'source': 'web', 'rank': 3,
            },
            {
                'title': 'Steam Most Played Games Right Now (2026) - PCGamer',
                'url': 'https://www.pcgamer.com/steam-most-played-games/',
                'display_url': 'www.pcgamer.com',
                'snippet': 'The 10 most played games on Steam in April 2026, ranked by current concurrent players. CS2, Dota 2, and PUBG hold the top three spots, with Elden Ring and GTA V rounding out the top five.',
                'source': 'web', 'rank': 4,
            },
            {
                'title': 'Most Played Games on Steam in 2026 - Rock Paper Shotgun',
                'url': 'https://www.rockpapershotgun.com/steam-most-played-games',
                'display_url': 'www.rockpapershotgun.com',
                'snippet': 'Here are the most played games on Steam right now along with their current player counts, peak counts, and what makes each one popular.',
                'source': 'web', 'rank': 5,
            },
            {
                'title': 'Top Steam Games by Player Count - IGN',
                'url': 'https://www.ign.com/articles/most-played-steam-games',
                'display_url': 'www.ign.com',
                'snippet': 'Steam\'s most popular games ranked by concurrent players. The platform regularly sees over 33 million online users with Counter-Strike 2 drawing the largest crowds.',
                'source': 'web', 'rank': 6,
            },
            {
                'title': 'r/Steam - Most Played Games Discussion',
                'url': 'https://www.reddit.com/r/Steam/',
                'display_url': 'www.reddit.com',
                'snippet': 'Discussion about the most popular Steam games and current player counts. Weekly charts, all-time peaks, and trending titles in the Steam community.',
                'source': 'reddit', 'rank': 7,
            },
        ]
        for r in steam_results:
            db.session.add(SearchResult(topic_id=steam_topic.id, **r))

        # PAA
        steam_paa = [
            ('What is the most played game on Steam right now?', 'Counter-Strike 2 is currently the most played game on Steam with approximately 1,218,882 concurrent players.'),
            ('How many concurrent players does Steam have?', 'Steam regularly sees over 33 million concurrent users at peak times, making it the largest PC gaming platform in the world.'),
            ('What are the top 5 most played Steam games?', 'The top 5 most played Steam games are: 1) Counter-Strike 2, 2) Dota 2, 3) PUBG, 4) Elden Ring, 5) Grand Theft Auto V.'),
            ('How to see current player counts on Steam?', 'You can view live player counts on Steam Charts (store.steampowered.com/charts/mostplayed) or SteamDB (steamdb.info/charts/).'),
        ]
        for i, (q, a) in enumerate(steam_paa):
            db.session.add(PaaQuestion(topic_id=steam_topic.id, question=q, answer=a, rank=i))

        # Related queries
        steam_related = ['steam charts', 'steam download', 'steam deck', 'counter-strike 2 player count',
                         'dota 2 player count', 'most popular pc games', 'steam sale', 'upcoming steam games']
        for i, term in enumerate(steam_related):
            db.session.add(RelatedQuery(topic_id=steam_topic.id, term=term, rank=i))

        # Knowledge facts
        steam_kfacts = [
            ('#1 Game', 'Counter-Strike 2 — 1,218,882 players'),
            ('#2 Game', 'Dota 2 — 658,434 players'),
            ('#3 Game', 'PUBG: Battlegrounds — 412,287 players'),
            ('#4 Game', 'Elden Ring — 187,532 players'),
            ('#5 Game', 'Grand Theft Auto V — 156,890 players'),
            ('Total Online', '33.1 million concurrent users'),
        ]
        steam_topic.knowledge_type = 'software'
        for i, (k, v) in enumerate(steam_kfacts):
            db.session.add(KnowledgeFact(topic_id=steam_topic.id, key=k, value=v, rank=i))

        db.session.commit()

    # ---- Task-driven topics for ALL WebVoyager tasks ----
    _seed_task_topics(db, Topic, SearchResult, PaaQuestion, RelatedQuery, KnowledgeFact)

    # ---- R2: Replay scraped topics from Round 1 (preserves the 170+ rich
    # topics that were added directly to the DB in R1) ----
    _seed_scraped_topics(db, Topic, SearchResult, PaaQuestion, RelatedQuery, KnowledgeFact)

    # ---- R2: Pop-topic expansion (programming, science, people, places, etc.) ----
    _seed_pop_topics(db, Topic, SearchResult, PaaQuestion, RelatedQuery, KnowledgeFact)

    # ---- R4: enrich SearchResults (result_type/breadcrumb/favicon) +
    #          add 5 deep results per topic (rank >= 10) ----
    _seed_r4_enrichment(db, Topic, SearchResult)

    # Demo user
    if not User.query.filter_by(email='demo@google.com').first():
        demo = User(
            email='demo@google.com',
            name='Demo User',
            password_hash=PINNED_DEMO_PASSWORD_HASH,
            created=MIRROR_REFERENCE_DATE,
        )
        db.session.add(demo)
        db.session.commit()

    print(f"[seed] {db.session.query(Topic).count()} topics, "
          f"{db.session.query(SearchResult).count()} results, "
          f"{db.session.query(PaaQuestion).count()} PAA, "
          f"{db.session.query(RelatedQuery).count()} related, "
          f"{db.session.query(Doodle).count()} doodles, "
          f"{db.session.query(TrendingTerm).count()} trending, "
          f"{db.session.query(GoogleApp).count()} apps")
