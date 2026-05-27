"""Seed data for the Eventbrite mirror. Idempotent at the function level."""
# Uses globals from app.py.

import random as _rnd

# ─── Realistic content pools (used by deterministic generator) ────────────────

_ORG_PREFIXES = [
    'OUT OF ORDINARY', 'Refuge', 'Pioneer Works', 'The Bushwick Collective',
    'Elsewhere Brooklyn', 'Brooklyn Bowl', 'House of Yes', 'Stafford Room',
    'The DL Rooftop', 'Mama Taco', 'Don Rique', 'HK Hall', 'Littlefield',
    'MAMATACO', 'Aldea Coffee', 'Ace Hotel', 'Public Works', 'The Independent',
    'The Fillmore', 'August Hall', 'The Chapel', 'The Warfield',
    'Resident DTLA', 'The Echo', 'Avalon Hollywood', 'Hollywood Forever',
    'The Wiltern', 'Hotel Cafe', 'Troubadour', 'Hotel Figueroa',
    'Schubas', 'Lincoln Hall', 'Thalia Hall', 'Concord Music Hall',
    'Empty Bottle', 'Sleeping Village', 'House of Blues', 'Riviera Theatre',
    'Mohawk', 'Stubb\'s BBQ', 'Antone\'s', 'Hotel Vegas', 'Continental Club',
    'Cheer Up Charlies', 'Empire Control Room', 'The Long Center',
    'Crocodile Café', 'Showbox', 'Neumos', 'Sunset Tavern', 'Tractor Tavern',
    'The Triple Door', 'Nectar Lounge', 'Capitol Hill Block Party',
    'Bluebird Theater', 'Larimer Lounge', 'Ogden Theatre', 'Mission Ballroom',
    'Red Rocks Amphitheatre', 'The Gothic Theatre', 'Cervantes Masterpiece',
    'Royale Boston', 'The Sinclair', 'Brighton Music Hall', 'Paradise Rock Club',
    'The Wilbur', 'Crystal Ballroom', 'Doug Fir Lounge', 'Wonder Ballroom',
    'Mississippi Studios', 'Aladdin Theater', '9:30 Club', 'The Anthem',
    'Black Cat', 'U Street Music Hall', 'Songbyrd', 'Tabernacle Atlanta',
    'Variety Playhouse', 'Buckhead Theatre', 'Center Stage', 'The Masquerade',
    'The Fillmore Miami', 'Wynwood Yard', 'Klipsch Amphitheater',
    'The Met Philadelphia', 'Union Transfer', 'World Cafe Live', 'TLA Philly',
    'First Avenue', 'Fine Line Music Café', 'Skyway Theatre', 'Varsity Theater',
    'Roseland Theater', 'Hawthorne Theatre', 'Wonder Ballroom Portland',
    'Crescent Ballroom', 'The Van Buren', 'Marquee Theatre', 'The Rebel Lounge',
    'House of Blues Las Vegas', 'Brooklyn Bowl Vegas', 'The Pearl', 'Vinyl HOB',
    'Soda Bar', 'Casbah', 'Belly Up', 'Music Box SD', 'House of Blues SD',
    'Exit/In Nashville', 'The End', '3rd & Lindsley', 'The Basement East',
    'Tipitina\'s', 'The Maple Leaf', 'Howlin\' Wolf', 'House of Blues NOLA',
    'El Club Detroit', 'The Magic Stick', 'Saint Andrew\'s Hall',
    'Cat\'s Cradle', 'Lincoln Theatre Raleigh', 'The Ritz Raleigh',
    'Ottobar Baltimore', '8x10 Club',
]
_ORG_KIND_SUFFIX = ['Productions', 'Presents', 'Events', 'Collective', 'Society',
                    'Studio', 'Group', 'Club', 'Festival Co.', 'Workshops',
                    'Speakers', 'Network', 'Foundation', 'Sessions']

_VENUE_TEMPLATES = {
    'ny--new-york': [
        'House of Yes, 2 Wyckoff Ave, Brooklyn, NY 11237',
        'Elsewhere, 599 Johnson Ave, Brooklyn, NY 11237',
        'Webster Hall, 125 E 11th St, New York, NY 10003',
        'Brooklyn Bowl, 61 Wythe Ave, Brooklyn, NY 11249',
        'Music Hall of Williamsburg, 66 N 6th St, Brooklyn, NY 11249',
        'Le Poisson Rouge, 158 Bleecker St, New York, NY 10012',
        'Pioneer Works, 159 Pioneer St, Brooklyn, NY 11231',
        'The Bell House, 149 7th St, Brooklyn, NY 11215',
        'Knockdown Center, 52-19 Flushing Ave, Maspeth, NY 11378',
        'Sony Hall, 235 W 46th St, New York, NY 10036',
        'Brooklyn Steel, 319 Frost St, Brooklyn, NY 11222',
        'The Box, 189 Chrystie St, New York, NY 10002',
    ],
    'ca--los-angeles': [
        'The Wiltern, 3790 Wilshire Blvd, Los Angeles, CA 90010',
        'The Roxy, 9009 Sunset Blvd, West Hollywood, CA 90069',
        'Hollywood Bowl, 2301 N Highland Ave, Los Angeles, CA 90068',
        'The Echo, 1822 Sunset Blvd, Los Angeles, CA 90026',
        'The Fonda Theatre, 6126 Hollywood Blvd, Los Angeles, CA 90028',
        'Avalon Hollywood, 1735 Vine St, Los Angeles, CA 90028',
        'The Greek Theatre, 2700 N Vermont Ave, Los Angeles, CA 90027',
        'Resident DTLA, 428 S Hewitt St, Los Angeles, CA 90013',
        'Belasco Theater, 1050 S Hill St, Los Angeles, CA 90015',
    ],
    'il--chicago': [
        'Schubas Tavern, 3159 N Southport Ave, Chicago, IL 60657',
        'Empty Bottle, 1035 N Western Ave, Chicago, IL 60622',
        'Thalia Hall, 1807 S Allport St, Chicago, IL 60608',
        'The Vic Theatre, 3145 N Sheffield Ave, Chicago, IL 60657',
        'Riviera Theatre, 4746 N Racine Ave, Chicago, IL 60640',
        'Lincoln Hall, 2424 N Lincoln Ave, Chicago, IL 60614',
        'Concord Music Hall, 2047 N Milwaukee Ave, Chicago, IL 60647',
    ],
    'tx--austin': [
        'Stubb\'s Bar-B-Q, 801 Red River St, Austin, TX 78701',
        'Mohawk, 912 Red River St, Austin, TX 78701',
        'Antone\'s, 305 E 5th St, Austin, TX 78701',
        'Hotel Vegas, 1502 E 6th St, Austin, TX 78702',
        'Continental Club, 1315 S Congress Ave, Austin, TX 78704',
        'The Long Center, 701 W Riverside Dr, Austin, TX 78704',
    ],
    'tx--houston': [
        'White Oak Music Hall, 2915 N Main St, Houston, TX 77009',
        'House of Blues Houston, 1204 Caroline St, Houston, TX 77002',
        'Warehouse Live, 813 St Emanuel St, Houston, TX 77003',
        'Heights Theater, 339 W 19th St, Houston, TX 77008',
    ],
    'ca--san-francisco': [
        'The Fillmore, 1805 Geary Blvd, San Francisco, CA 94115',
        'The Independent, 628 Divisadero St, San Francisco, CA 94117',
        'Bottom of the Hill, 1233 17th St, San Francisco, CA 94107',
        'Bimbo\'s 365 Club, 1025 Columbus Ave, San Francisco, CA 94133',
        'August Hall, 420 Mason St, San Francisco, CA 94102',
        'The Chapel, 777 Valencia St, San Francisco, CA 94110',
    ],
    'wa--seattle': [
        'The Showbox, 1426 1st Ave, Seattle, WA 98101',
        'Neumos, 925 E Pike St, Seattle, WA 98122',
        'The Crocodile, 2200 2nd Ave, Seattle, WA 98121',
        'Sunset Tavern, 5433 Ballard Ave NW, Seattle, WA 98107',
        'Tractor Tavern, 5213 Ballard Ave NW, Seattle, WA 98107',
        'Capitol Hill Block Party, 1009 E Union St, Seattle, WA 98122',
    ],
    'co--denver': [
        'Ogden Theatre, 935 E Colfax Ave, Denver, CO 80218',
        'Bluebird Theater, 3317 E Colfax Ave, Denver, CO 80206',
        'Mission Ballroom, 4242 Wynkoop St, Denver, CO 80216',
        'Larimer Lounge, 2721 Larimer St, Denver, CO 80205',
        'Red Rocks Amphitheatre, 18300 W Alameda Pkwy, Morrison, CO 80465',
        'Cervantes Masterpiece, 2637 Welton St, Denver, CO 80205',
        'Gothic Theatre, 3263 S Broadway, Englewood, CO 80113',
    ],
    'ma--boston': [
        'Paradise Rock Club, 967 Commonwealth Ave, Boston, MA 02215',
        'Royale Boston, 279 Tremont St, Boston, MA 02116',
        'The Sinclair, 52 Church St, Cambridge, MA 02138',
        'Brighton Music Hall, 158 Brighton Ave, Allston, MA 02134',
        'The Wilbur, 246 Tremont St, Boston, MA 02116',
    ],
    'dc--washington': [
        '9:30 Club, 815 V St NW, Washington, DC 20001',
        'The Anthem, 901 Wharf St SW, Washington, DC 20024',
        'Black Cat, 1811 14th St NW, Washington, DC 20009',
        'Songbyrd, 540 Penn St NE, Washington, DC 20002',
        'Echostage, 2135 Queens Chapel Rd NE, Washington, DC 20018',
    ],
    'ga--atlanta': [
        'Tabernacle, 152 Luckie St NW, Atlanta, GA 30303',
        'Variety Playhouse, 1099 Euclid Ave NE, Atlanta, GA 30307',
        'Buckhead Theatre, 3110 Roswell Rd NE, Atlanta, GA 30305',
        'The Masquerade, 50 Lower Alabama St, Atlanta, GA 30303',
        'Center Stage, 1374 W Peachtree St NW, Atlanta, GA 30309',
    ],
    'fl--miami': [
        'The Fillmore Miami Beach, 1700 Washington Ave, Miami Beach, FL 33139',
        'Wynwood Yard, 56 NW 29th St, Miami, FL 33127',
        'Klipsch Amphitheater, 301 Biscayne Blvd, Miami, FL 33132',
        'Gramps, 176 NW 24th St, Miami, FL 33127',
    ],
    'pa--philadelphia': [
        'The Met Philadelphia, 858 N Broad St, Philadelphia, PA 19130',
        'Union Transfer, 1026 Spring Garden St, Philadelphia, PA 19123',
        'World Cafe Live, 3025 Walnut St, Philadelphia, PA 19104',
        'TLA, 334 South St, Philadelphia, PA 19147',
    ],
    'mn--minneapolis': [
        'First Avenue, 701 1st Ave N, Minneapolis, MN 55403',
        'Fine Line Music Café, 318 N 1st Ave, Minneapolis, MN 55401',
        'Skyway Theatre, 711 Hennepin Ave, Minneapolis, MN 55403',
        'Varsity Theater, 1308 4th St SE, Minneapolis, MN 55414',
    ],
    'or--portland': [
        'Crystal Ballroom, 1332 W Burnside St, Portland, OR 97209',
        'Doug Fir Lounge, 830 E Burnside St, Portland, OR 97214',
        'Wonder Ballroom, 128 NE Russell St, Portland, OR 97212',
        'Mississippi Studios, 3939 N Mississippi Ave, Portland, OR 97227',
        'Aladdin Theater, 3017 SE Milwaukie Ave, Portland, OR 97202',
    ],
    'az--phoenix': [
        'Crescent Ballroom, 308 N 2nd Ave, Phoenix, AZ 85003',
        'The Van Buren, 401 W Van Buren St, Phoenix, AZ 85003',
        'Marquee Theatre, 730 N Mill Ave, Tempe, AZ 85281',
    ],
    'nv--las-vegas': [
        'House of Blues Las Vegas, 3950 S Las Vegas Blvd, Las Vegas, NV 89119',
        'Brooklyn Bowl Las Vegas, 3545 S Las Vegas Blvd, Las Vegas, NV 89109',
        'The Pearl Concert Theater, 4321 W Flamingo Rd, Las Vegas, NV 89103',
        'Vinyl HOB, 4455 Paradise Rd, Las Vegas, NV 89169',
    ],
    'ca--san-diego': [
        'Soda Bar, 3615 El Cajon Blvd, San Diego, CA 92104',
        'Casbah, 2501 Kettner Blvd, San Diego, CA 92101',
        'Belly Up Tavern, 143 S Cedros Ave, Solana Beach, CA 92075',
        'Music Box, 1337 India St, San Diego, CA 92101',
    ],
    'tn--nashville': [
        'Exit/In, 2208 Elliston Pl, Nashville, TN 37203',
        'The End, 2219 Elliston Pl, Nashville, TN 37203',
        '3rd & Lindsley, 818 3rd Ave S, Nashville, TN 37210',
        'The Basement East, 917 Woodland St, Nashville, TN 37206',
    ],
    'la--new-orleans': [
        'Tipitina\'s, 501 Napoleon Ave, New Orleans, LA 70115',
        'The Maple Leaf, 8316 Oak St, New Orleans, LA 70118',
        'Howlin\' Wolf, 907 S Peters St, New Orleans, LA 70130',
        'House of Blues New Orleans, 225 Decatur St, New Orleans, LA 70130',
    ],
    'mi--detroit': [
        'El Club, 4114 W Vernor Hwy, Detroit, MI 48209',
        'The Magic Stick, 4140 Woodward Ave, Detroit, MI 48201',
        'Saint Andrew\'s Hall, 431 E Congress St, Detroit, MI 48226',
        'The Crofoot, 1 S Saginaw St, Pontiac, MI 48342',
    ],
    'nc--raleigh': [
        'Cat\'s Cradle, 300 E Main St, Carrboro, NC 27510',
        'Lincoln Theatre, 126 E Cabarrus St, Raleigh, NC 27601',
        'The Ritz, 2820 Industrial Dr, Raleigh, NC 27609',
    ],
    'md--baltimore': [
        'Ottobar, 2549 N Howard St, Baltimore, MD 21218',
        '8x10 Club, 10 E Cross St, Baltimore, MD 21230',
        'Rams Head Live, 20 Market Pl, Baltimore, MD 21202',
    ],
}

# Title templates by category — each contributes 8-12 archetypal event titles.
_TITLE_TEMPLATES = {
    'music': [
        '{artist} Live at {venue_short}', '{artist}: The {tour} Tour',
        '{theme} Night ft. {artist}', 'Sunset Sessions: {artist}',
        '{day_name} Block Party w/ {artist}',
        'Open Mic at {venue_short}', '{theme} Karaoke Night',
        '{genre} vs {genre2} Party', 'Vinyl Sundays — {genre} Edition',
        '{artist} & Friends — Acoustic Showcase',
    ],
    'business': [
        '{topic} Summit {year}', '{topic} Founders Meetup',
        '{topic} Workshop — From Idea to Launch',
        'Women in {topic}: {year} Annual', '{city_name} {topic} Networking Night',
        '{topic} for Beginners — Hands-on Bootcamp',
        '{topic} & AI — A Deep Dive',
        'Startup Pitch Night: {topic}', '{topic} Career Fair {year}',
    ],
    'food-drink': [
        'Wine Tasting at {venue_short}', 'Sushi Masterclass with Chef {chef}',
        '{cuisine} Food Festival {year}', '{cuisine} Street Eats Pop-Up',
        'Whiskey & Chocolate Pairing Night', 'Vegan Brunch Crawl',
        'Cocktail Mixology 101', 'Farm-to-Table Dinner — {cuisine} Edition',
        'Pizza & Pints: A Pairing Workshop',
    ],
    'arts': [
        '{play} — Opening Night', '{art_style} Exhibit Opening',
        'Improv Comedy Showcase', 'Standup at {venue_short} ft. {comic}',
        'Poetry Slam: {theme}', 'Live Painting & Drinks',
        'Drag Brunch at {venue_short}',
        'Off-Broadway: {play}', 'Modern Dance: {company} in Residence',
    ],
    'holiday': [
        '{holiday} Block Party', '{holiday} Brunch at {venue_short}',
        '{holiday} Fireworks Cruise', '{holiday} 5K Run',
        '{holiday} Family Festival', '{holiday} Costume Crawl',
    ],
    'health': [
        'Rooftop Yoga Sunday', 'Mindful Meditation Workshop',
        'Sound Bath Healing Circle', 'Breathwork Reset',
        '{practice} Teacher Training', 'Plant-Based Nutrition Talk',
        'Mental Health First Aid Workshop', 'Pilates Pop-Up',
    ],
    'hobbies': [
        'Board Game Night', 'Chess Open Tournament',
        'Watercolor Workshop for Beginners',
        'Pottery & Wine Night', 'Photography Walk: {neighborhood}',
        'Crochet Circle', 'Knitting Social',
        'DIY Candle Making', 'Macramé Plant Hanger Workshop',
    ],
    'family': [
        'Family Story Time at {venue_short}', 'Kids STEM Workshop',
        'LEGO Build Saturday', 'Parent & Toddler Music Class',
        'Teen Coding Bootcamp', 'Sensory Play for Babies',
        '{age} & Up Science Exploration',
    ],
    'sports': [
        '{sport} League Sign-Up Night', 'Saturday {sport} Pickup',
        '{sport} Tournament — Spring {year}', 'Marathon Training Group',
        'CrossFit Open Workout', 'Climbing Night at {venue_short}',
        'Beach Volleyball Mixer', 'Cycling Club Long Ride',
    ],
    'travel': [
        'Sunrise Hike in {park}', 'Kayak the {water}',
        'Bike Tour: {neighborhood}', 'Camping Trip — {park}',
        'Stargazing Night at {park}', 'Foraging Walk',
        'Birding Sunday in {park}',
    ],
    'charity': [
        'Charity Gala for {cause}', '{cause} Awareness 5K',
        'Silent Auction Benefit', 'Volunteer Cleanup Day',
        'Donation Drive: {cause}', 'Annual Fundraiser for {cause}',
    ],
    'spirituality': [
        'New Moon Circle', 'Tarot & Tea Workshop',
        'Crystal Healing Intro', 'Astrology 101: Reading Your Chart',
        'Reiki Share Circle', 'Sound Healing & Sage Ceremony',
    ],
    'community': [
        '{city_name} Pride Mixer', 'Local Makers Market',
        '{neighborhood} Block Party', 'Community Potluck',
        'Newcomers Welcome Night', '{city_name} Singles Mixer',
    ],
    'fashion': [
        'Sample Sale — {brand}', 'Vintage Pop-Up Market',
        'Designer Trunk Show: {brand}', 'Sustainable Style Workshop',
        'Bridal Try-On Event',
    ],
    'film': [
        'Outdoor Movie Night: {movie}', 'Indie Film Premiere: {movie}',
        'Documentary Screening: {movie}', 'Film Trivia Night',
        '{festival} Film Festival {year}',
    ],
    'home': [
        'Plant Swap Sunday', 'Houseplant 101 Workshop',
        'Home Buying Seminar', 'Container Gardening Class',
        'Interior Design Q&A', 'Composting at Home',
    ],
    'auto': [
        'Cars & Coffee — {city_name}', 'Classic Car Show {year}',
        'Sailing Charter Sunday', 'Motorcycle Group Ride',
        'EV Test Drive Event',
    ],
    'school': [
        'Back-to-School Resource Fair', 'College Prep Night',
        'PTA Fundraiser Bingo', 'Robotics Club Open House',
    ],
}

_FILLERS = {
    'artist': ['DJ Sable', 'Nora Vexil', 'The Brassknuckle Five', 'Marlowe',
               'Coastal Static', 'Velvet Quartz', 'Junior Pesos', 'The Reds',
               'Lila Moon', 'Cesar & the Wolves', 'Glasswind', 'Knox & Cell',
               'Ruby Tides', 'Atlas Bloom', 'Pinewood Drift', 'Echo Habit',
               'Marigold Hex', 'Stoneflower', 'Hex Magnolia', 'River Mason',
               'The Polite Riot', 'Hello Fern', 'Sage & Smoke', 'Tabletop'],
    'tour': ['Solstice', 'Aftermath', 'Quiet Hours', 'Echoes', 'Open Sky',
             'Lowlight', 'Half Light', 'Sea Foam', 'Northern Lights'],
    'theme': ['90s', '2000s', 'Disco', 'Lo-Fi', 'Latin', 'Afrobeats',
              'Bollywood', 'Y2K', 'Indie', 'House', 'Tropical'],
    'day_name': ['Friday', 'Saturday', 'Sunday'],
    'genre': ['Hip Hop', 'House', 'Techno', 'Bachata', 'Salsa', 'R&B',
              'Dancehall', 'Reggaeton', 'Funk', 'Soul', 'Disco', 'EDM'],
    'genre2': ['Soca', 'Slow Jams', 'Trap', 'Bass', 'Garage', 'Bossa Nova'],
    'topic': ['Web3', 'AI', 'Real Estate', 'Marketing', 'FinTech',
              'Climate Tech', 'Design', 'Product Management', 'Cybersecurity',
              'Data Science', 'E-commerce', 'Healthcare Innovation',
              'Sustainability'],
    'year': ['2026', '2027'],
    'cuisine': ['Italian', 'Japanese', 'Korean', 'Mexican', 'Thai',
                'Mediterranean', 'Ethiopian', 'Vietnamese', 'Indian',
                'Peruvian', 'Lebanese', 'Spanish'],
    'chef': ['Marisol Cruz', 'Daichi Watanabe', 'Anais Beaumont',
             'Theo Brennan', 'Soomin Park', 'Jin Hua', 'Ren Aragão'],
    'play': ['The Last Lighthouse', 'A House of Echoes', 'Tin Soldiers',
             'Magnolia & the Sea', 'Glass Garden', 'Paper Crowns',
             'A Night in Marsaille', 'Quiet Town'],
    'art_style': ['Modernist', 'Surrealist', 'Photographic', 'Abstract',
                  'Folk', 'Outsider', 'Mixed Media', 'Sculpture'],
    'comic': ['Marlon Hayes', 'Jenny Park', 'Theo Romanov', 'Aisha N.',
              'Doogie Khan', 'Sam Cortez', 'Britt Sloan'],
    'company': ['Glasshouse Dance', 'Riverbend Collective', 'Spiral Dance Co.',
                'Eastsider Studio', 'Vox Body'],
    'holiday': ['Memorial Day', 'July 4th', 'Halloween',
                'Thanksgiving', 'Christmas', 'New Year\'s Eve',
                'Cinco de Mayo', 'Mother\'s Day', 'Father\'s Day',
                'Pride Weekend', 'Labor Day'],
    'practice': ['Yoga', 'Pilates', 'Tai Chi', 'Qigong'],
    'neighborhood': ['Williamsburg', 'Echo Park', 'Wicker Park', 'East Austin',
                     'Capitol Hill', 'Mission', 'RiNo', 'Brooklyn Heights',
                     'Silver Lake', 'Logan Square'],
    'sport': ['Basketball', 'Soccer', 'Tennis', 'Volleyball', 'Pickleball',
              'Kickball', 'Flag Football', 'Ultimate Frisbee', 'Dodgeball'],
    'park': ['Prospect Park', 'Griffith Park', 'Lincoln Park',
             'Zilker Park', 'Discovery Park', 'Mount Tam', 'Rocky Mountain NP',
             'Catalina State Park', 'Joshua Tree NP'],
    'water': ['Hudson River', 'LA River', 'Lake Michigan', 'Lady Bird Lake',
              'Puget Sound', 'Charles River', 'Mississippi River',
              'Biscayne Bay', 'Willamette River'],
    'cause': ['Mental Health', 'Climate Action', 'Food Security',
              'Affordable Housing', 'Animal Welfare', 'Arts Education',
              'Cancer Research', 'Veterans Support'],
    'brand': ['Northwell Studio', 'Aldea & Co.', 'Atlas Tailoring',
              'Wildflower Knit', 'Ferment Atelier', 'Storm Cloth'],
    'movie': ['The Quiet Coast', 'Bluebell Summer', 'Stilllight',
              'Cinder & Smoke', 'The Last Cartographer', 'Marsh Music'],
    'festival': ['Nightowl', 'Tiderise', 'Slow Burn', 'Lantern'],
    'age': ['Ages 4', 'Ages 6', 'Ages 8', 'Ages 10', 'Ages 12'],
}

# Subcategories per category — used to set ev.subcategory.
_SUBCATS = {
    'music': ['Electronic', 'Hip Hop', 'Rock', 'Jazz', 'Latin', 'Country',
              'R&B', 'Folk', 'Classical', 'Pop', 'Reggae', 'Metal'],
    'business': ['Career', 'Startups', 'Marketing', 'Finance', 'Real Estate',
                 'Leadership', 'Networking'],
    'food-drink': ['Wine', 'Beer', 'Spirits', 'Tasting', 'Cooking Class',
                   'Food Festival', 'Vegan'],
    'arts': ['Theater', 'Comedy', 'Visual Arts', 'Dance', 'Literary',
             'Opera', 'Musicals'],
    'holiday': ['Halloween', 'July 4th', 'Christmas', 'New Year', 'Pride'],
    'health': ['Yoga', 'Mental Health', 'Nutrition', 'Meditation',
               'Fitness Class', 'Wellness'],
    'hobbies': ['Crafts', 'Games', 'Photography', 'Drawing', 'Knitting'],
    'family': ['Education', 'Kids Activities', 'Parenting', 'Teens'],
    'sports': ['Basketball', 'Running', 'Cycling', 'Soccer', 'Pickleball',
               'Climbing', 'Volleyball'],
    'travel': ['Hiking', 'Camping', 'Bike Tour', 'Birding', 'Stargazing'],
    'charity': ['Gala', 'Fundraiser', 'Volunteer', 'Drive', '5K'],
    'spirituality': ['Tarot', 'Astrology', 'Crystals', 'Reiki', 'Sound Bath'],
    'community': ['Mixer', 'Festival', 'Pride', 'Newcomers', 'Block Party'],
    'fashion': ['Sample Sale', 'Trunk Show', 'Pop-Up', 'Bridal'],
    'film': ['Premiere', 'Outdoor Screening', 'Documentary', 'Festival'],
    'home': ['Gardening', 'Plants', 'Interior Design', 'DIY'],
    'auto': ['Cars', 'Boats', 'Aviation', 'Motorcycles'],
    'school': ['College Prep', 'PTA', 'Robotics', 'Resource Fair'],
}

# Free / paid tier mixes — chosen by category and per-event roll
_TIER_RECIPES = [
    [('General Admission', 25)],
    [('General Admission', 35), ('VIP', 75)],
    [('Early Bird', 15), ('General Admission', 25), ('VIP', 60)],
    [('Free RSVP', 0)],
    [('Free with RSVP before 11pm', 0), ('General Admission', 20)],
    [('Student', 10), ('General Admission', 25), ('VIP', 65)],
    [('General Admission', 45)],
    [('Early Bird', 35), ('General Admission', 55), ('Premium', 95), ('VIP', 145)],
    [('General Admission', 18)],
    [('Free RSVP', 0), ('Donation', 5)],
    [('General Admission', 95), ('VIP', 195)],
    [('Beginner Workshop', 60), ('Full Day', 120)],
    [('General Admission', 30), ('Group of 4', 100)],
]


def _seeded_random(seed_str):
    r = _rnd.Random()
    r.seed(int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16))
    return r


def _make_description(ev_title, category_name, organizer_name, city_name, fmt_):
    """Produce a 300-700 word body. Deterministic given inputs."""
    r = _seeded_random(ev_title + category_name)
    para1 = (
        f"Join us at {organizer_name} for {ev_title} — a special "
        f"{category_name.lower()} {fmt_.lower()} taking place in {city_name}. "
        "Whether you're a longtime fan or a newcomer to the scene, this "
        "event is designed to bring together a community that cares about "
        "great experiences. Doors open early so you have time to grab a "
        "drink, meet people, and settle in before the program starts."
    )
    para2 = (
        "What to expect: a thoughtfully programmed evening that balances "
        "the headline experience with room to mingle. We've worked with "
        "the venue to make sure sound and sight lines are excellent from "
        "every angle, and we have a small selection of local vendors on "
        "site for snacks and merch. Our team will be wearing branded "
        "t-shirts — flag any of us down if you need help finding the "
        "restrooms, coat check, or have an accessibility need."
    )
    sample_lines = [
        "Arrive early to grab the best seats — we recommend showing up 30 minutes before the doors open.",
        "Bring a valid government-issued ID; some sections of the venue are 21+.",
        "Photography is welcome, but please no flash during the main set.",
        "All ages welcome unless otherwise noted. Children under 5 do not need a ticket if they sit on a lap.",
        "Coat check is available for $3. Cash and card accepted at the bar.",
        "The venue is wheelchair-accessible. Reach out if you have specific accommodation needs.",
        "We partner with local rideshare and shuttle services — see the directions section for details.",
        "Please leave large bags at home; we run a fast bag check at the door.",
    ]
    bullets = '\n'.join('• ' + s for s in r.sample(sample_lines, 5))
    para3 = (
        f"About the organizer: {organizer_name} has been hosting events "
        f"in {city_name} for years and is known for curating intimate, "
        "community-driven gatherings. Follow them on Eventbrite to be "
        "the first to hear about future shows, member-only presales, and "
        "occasional pop-up activations."
    )
    para4 = (
        "Refunds and policy: please review the refund policy listed on "
        "this page before purchase. Tickets are non-transferable unless "
        "you contact the organizer to update the attendee name. If the "
        "event is cancelled or rescheduled, you will be notified by email "
        "with options to refund or transfer."
    )
    para5 = (
        "Accessibility: the venue is wheelchair-accessible from the main "
        "entrance, with ADA-compliant restrooms on the same floor as the "
        "main room. ASL interpretation is available on request — please "
        "email the organizer at least 7 days in advance. Service animals "
        "are welcome."
    )
    return '\n\n'.join([para1, para2, "Here are a few things to know before you go:\n\n" + bullets, para3, para4, para5])


def _make_agenda(start_dt, fmt_, r):
    """Return JSON list of agenda items for the event."""
    blocks = []
    cursor = start_dt
    if fmt_ in ('Conference', 'Seminar'):
        items = [
            ('Registration & Coffee', 30),
            ('Opening Keynote', 45),
            ('Panel: Industry Outlook', 60),
            ('Networking Break', 20),
            ('Breakout Session A', 50),
            ('Lunch (provided)', 60),
            ('Breakout Session B', 50),
            ('Closing Remarks', 30),
        ]
    elif fmt_ == 'Festival':
        items = [
            ('Gates open', 30),
            ('Opening Act', 45),
            ('Main Stage Set 1', 60),
            ('Food Vendor Break', 30),
            ('Main Stage Set 2', 75),
            ('Headliner', 90),
            ('Closing', 30),
        ]
    elif fmt_ == 'Party':
        items = [
            ('Doors', 30),
            ('Opener', 60),
            ('Headlining Set', 120),
            ('Last Call', 30),
        ]
    elif fmt_ == 'Class':
        items = [
            ('Check-in', 15),
            ('Intro & Setup', 20),
            ('Hands-on Session', 90),
            ('Wrap-up & Q&A', 25),
        ]
    else:
        items = [
            ('Doors / Check-in', 30),
            ('Program', 90),
            ('Mingle', 30),
        ]
    for (title, mins) in items:
        blocks.append({
            'time': cursor.strftime('%-I:%M %p'),
            'title': title,
            'description': '',
        })
        cursor = cursor + timedelta(minutes=mins)
    return blocks


def _make_speakers(category_slug, r):
    names = [
        'Maya Sandoval', 'Theo Brennan', 'Anais Beaumont', 'Soomin Park',
        'Cyril Okafor', 'Jin Hua', 'Ren Aragão', 'Pippa Yoshida',
        'Marlon Hayes', 'Britt Sloan', 'Dev Patel-Hughes', 'Lisbet Hagen',
        'Omar Riza', 'Tova Ekstrom', 'Aviva Marchand',
    ]
    titles_by_cat = {
        'business': ['CEO', 'Founder', 'VP of Product', 'Head of Marketing',
                     'Investor', 'Operating Partner'],
        'arts':     ['Director', 'Curator', 'Visual Artist', 'Choreographer'],
        'health':   ['Wellness Coach', 'Registered Dietitian', 'Yoga Instructor',
                     'Mindfulness Teacher'],
        'community':['Community Organizer', 'Volunteer Lead'],
        'family':   ['Educator', 'Pediatric Coach'],
        'school':   ['Principal', 'Teacher', 'Curriculum Lead'],
    }
    base_titles = titles_by_cat.get(category_slug, ['Speaker', 'Guest', 'Host'])
    n = r.choice([0, 0, 1, 2, 2, 3, 3, 4])
    out = []
    used = set()
    for _ in range(n):
        name = r.choice(names)
        if name in used: continue
        used.add(name)
        out.append({
            'name': name,
            'title': r.choice(base_titles),
            'bio': f'{name} brings years of practice to the field and is a frequent guest at events like this.',
        })
    return out


def _make_faq(r):
    pool = [
        ('What\'s the refund policy?',
         'Refunds are subject to the organizer\'s refund policy listed on this page. You can request a refund from the order page in your account.'),
        ('Is the venue accessible?',
         'Yes. The venue is wheelchair-accessible from the main entrance, and ADA-compliant restrooms are available on the same floor.'),
        ('Can I transfer my ticket?',
         'Tickets are non-transferable by default. To update the attendee name, please contact the organizer at least 24 hours before the event.'),
        ('Will food be provided?',
         'A small selection of vendors will be on site. You\'re welcome to bring small snacks, but outside drinks are not permitted.'),
        ('What time should I arrive?',
         'We suggest arriving 30 minutes before the start time to get through the door check and find your seat.'),
        ('Is there parking?',
         'Limited parking is available on the surrounding streets. We recommend rideshare or public transit.'),
        ('Are children allowed?',
         'This event is welcoming to all ages unless otherwise marked. Children under 5 do not need a ticket if seated on a lap.'),
        ('Can I bring my dog?',
         'Service animals are welcome. We aren\'t able to accommodate other pets inside the venue.'),
    ]
    n = r.choice([4, 5, 5, 6])
    return [{'q': q, 'a': a} for (q, a) in r.sample(pool, n)]


# ─── Organizers seed ──────────────────────────────────────────────────────────

# Real-world organizer flavor (used by tasks): a small set of "named" organizers
# that we set up explicitly so that benchmark tasks can reference them by name.
_NAMED_ORGANIZERS = [
    # (slug, name, city_slug, bio, follower_seed, verified)
    ('out-of-ordinary',   'OUT OF ORDINARY',
        'ny--new-york', 'NYC nightlife brand running rooftop parties, RSVP-only mixers, and TikTok-era throwback nights across Manhattan and Brooklyn.', 18420, True),
    ('refuge-brooklyn',   'Refuge',
        'ny--new-york', 'A queer-friendly Brooklyn warehouse party series featuring international DJs and benefit lineups.', 9210, True),
    ('pioneer-works',     'Pioneer Works',
        'ny--new-york', 'A nonprofit cultural center in Red Hook, Brooklyn presenting science, music, technology, and visual art programming.', 41200, True),
    ('bushwick-collective','The Bushwick Collective',
        'ny--new-york', 'Curated outdoor mural collective in Bushwick, known for the annual Block Party and rotating street art installations.', 27600, True),
    ('elsewhere-bk',      'Elsewhere Brooklyn',
        'ny--new-york', 'Bushwick concert venue & nightclub with three stages, a rooftop, and forward-thinking electronic / indie programming.', 33500, True),
    ('hollywood-bowl-events', 'Hollywood Bowl Events',
        'ca--los-angeles', 'Iconic outdoor amphitheatre in the Hollywood Hills, hosting the LA Phil, KCRW Festival, and headlining concerts each summer.', 88300, True),
    ('the-wiltern-presents', 'The Wiltern Presents',
        'ca--los-angeles', 'Historic Koreatown art-deco theatre with a 1,850-capacity room programming touring rock, hip hop, and Latin acts.', 21400, False),
    ('schubas-tavern',    'Schubas Tavern',
        'il--chicago', 'Lakeview\'s long-running songwriter-friendly venue, featuring nightly bookings of folk, indie, and emerging local acts.', 7200, False),
    ('thalia-hall',       'Thalia Hall',
        'il--chicago', 'Pilsen historic venue hosting tours, comedy, and weekend dance nights in a restored 1892 opera house.', 14900, True),
    ('stubbs-bbq',        'Stubb\'s BBQ Live',
        'tx--austin', 'Austin\'s Red River venue famous for its outdoor amphitheatre, Sunday gospel brunch, and SXSW programming.', 16300, True),
    ('mohawk-austin',     'Mohawk Austin',
        'tx--austin', 'Two-stage indoor/outdoor Red River club known for indie tours, DIY-friendly billings, and city skyline views.', 9100, False),
    ('the-fillmore-sf',   'The Fillmore',
        'ca--san-francisco', 'The legendary Fillmore in SF — apples at the door since 1965 — programming rock, hip hop, electronic, and comedy.', 49800, True),
    ('the-independent-sf','The Independent',
        'ca--san-francisco', 'Intimate Divisadero club booking some of the best touring indie and electronic acts in the country.', 12700, False),
    ('the-showbox-seattle','The Showbox',
        'wa--seattle', 'Historic Pike Place venue celebrating its 86th year in 2025 with rock, hip hop, jazz, and stand-up.', 18300, True),
    ('red-rocks-presents','Red Rocks Presents',
        'co--denver', 'Programmer for the Red Rocks Amphitheatre concert season — bookings, presales, and concert announcements.', 119000, True),
    ('paradise-rock-bos', 'Paradise Rock Club',
        'ma--boston', 'Boston University-area rock club celebrating decades of breakout shows for college-radio favorites.', 8400, False),
    ('930-club-dc',       '9:30 Club',
        'dc--washington', 'DC\'s flagship music venue — winner of Pollstar\'s "Nightclub of the Decade" and the city\'s definitive concert experience.', 27300, True),
    ('tabernacle-atl',    'Tabernacle Atlanta',
        'ga--atlanta', 'Historic former church turned concert venue in downtown Atlanta, programming touring rock, hip hop, and electronic acts.', 21800, True),
    ('first-avenue-mn',   'First Avenue & 7th St Entry',
        'mn--minneapolis', 'The "Prince club" — Minneapolis\'s historic flagship venue and the original Purple Rain stage.', 31600, True),
    ('crystal-ballroom-pdx','Crystal Ballroom',
        'or--portland', 'Bouncing-floor dance hall in downtown Portland, OR, programming touring rock, comedy, and dance nights.', 13200, True),
    ('exit-in-nashville', 'Exit/In',
        'tn--nashville', 'Nashville\'s storied Elliston Place venue, a rock and singer-songwriter institution since 1971.', 9700, False),
    ('tipitinas-nola',    'Tipitina\'s',
        'la--new-orleans', 'Uptown New Orleans landmark established by the Neville Brothers and Allen Toussaint in 1977.', 16700, True),
    ('startup-grind',     'Startup Grind',
        'ca--san-francisco', 'A global community of founders, hosting monthly fireside chats and Demo Days across 600+ cities.', 142000, True),
    ('women-who-code',    'Women Who Code',
        'ca--san-francisco', 'Global nonprofit empowering women in tech with monthly meetups, study groups, and conference programming.', 96000, True),
    ('product-hunt-events','Product Hunt Events',
        'ca--san-francisco', 'Maker-led community events from the Product Hunt team — meetups, launch parties, and demo nights.', 54000, True),
    ('toastmasters-nyc',  'Toastmasters NYC',
        'ny--new-york', 'NYC chapter of Toastmasters International running weekly public-speaking and leadership meetings.', 8800, False),
    ('saatchi-art-events','Saatchi Art Events',
        'ca--los-angeles', 'Art-world programming from the Saatchi Art team — openings, artist talks, and curator-led walkthroughs.', 23400, False),
    ('moma-events',       'MoMA Events',
        'ny--new-york', 'Public programs from the Museum of Modern Art — talks, screenings, and member previews.', 87200, True),
    ('audubon-society',   'National Audubon Society',
        'ny--new-york', 'Birding walks, conservation education, and citizen science events across the US.', 56400, True),
    ('sierra-club-events','Sierra Club Events',
        'ca--san-francisco', 'The Sierra Club\'s local outings — hikes, kayak trips, and environmental advocacy events.', 33700, True),
    ('the-moth',          'The Moth',
        'ny--new-york', 'StorySLAM, GrandSLAM, and Mainstage true-stories-told-live events across NYC and beyond.', 78300, True),
    ('drag-brunch-co',    'Drag Brunch Co.',
        'ny--new-york', 'Sunday drag brunch programming at venues across NYC, LA, Chicago, and Las Vegas.', 14200, False),
    ('soulcycle-events',  'SoulCycle Events',
        'ny--new-york', 'Pop-up rides, theme classes, and signature retreats from the SoulCycle community team.', 38900, True),
    ('y7-studio-events',  'Y7 Studio Events',
        'ny--new-york', 'Hip hop yoga pop-ups, candlelit flows, and instructor workshops from Y7 Studio.', 17100, False),
    ('eb-online-conf',    'Eventbrite Online Conferences',
        'ny--new-york', 'Curated online conferences for product, design, marketing, and engineering professionals.', 22000, True),
]


def _make_organizer_pool():
    """Returns a list of (slug, name, city_slug, bio, follower_seed, verified)."""
    pool = list(_NAMED_ORGANIZERS)
    used = {p[0] for p in pool}
    # Generate the remaining synthetic organizers.
    for ci, (city_slug, city_name, _state, _, _) in enumerate(CITIES):
        for ki in range(8):
            base = _ORG_PREFIXES[(ci * 5 + ki) % len(_ORG_PREFIXES)]
            suffix = _ORG_KIND_SUFFIX[(ci * 3 + ki) % len(_ORG_KIND_SUFFIX)]
            name = f"{base} {suffix}"
            slug = slugify(f"{base}-{suffix}-{city_slug[:4]}-{ki}", 80)
            if slug in used: continue
            used.add(slug)
            bio = (f"{name} curates {('online' if ki%6==5 else 'live')} programming "
                   f"in {city_name} and surrounding neighborhoods, with a focus "
                   "on community, craft, and inviting first-time guests into a warm room.")
            followers = 200 + (hash(slug) % 9800)
            pool.append((slug, name, city_slug, bio, followers, False))
    # Cap at ~210
    return pool[:215]


# ─── Event generation ─────────────────────────────────────────────────────────

def _format_for_category(cat):
    return {
        'music':       ['Party', 'Performance', 'Festival'],
        'business':    ['Conference', 'Seminar', 'Networking'],
        'food-drink':  ['Class', 'Tour', 'Performance'],
        'arts':        ['Performance', 'Class', 'Tour'],
        'holiday':     ['Festival', 'Party'],
        'health':      ['Class', 'Seminar'],
        'hobbies':     ['Class', 'Networking'],
        'family':      ['Class', 'Festival'],
        'sports':      ['Class', 'Tour'],
        'travel':      ['Tour', 'Class'],
        'charity':     ['Festival', 'Performance', 'Networking'],
        'spirituality':['Class', 'Seminar'],
        'community':   ['Networking', 'Party', 'Festival'],
        'fashion':     ['Performance', 'Networking'],
        'film':        ['Performance', 'Festival'],
        'home':        ['Class', 'Seminar'],
        'auto':        ['Tour', 'Networking'],
        'school':      ['Networking', 'Class'],
    }.get(cat, ['Performance'])


def _fill_title(template, city_name, r):
    """Substitute {x} fillers in a title template."""
    out = template
    for _ in range(8):
        m = re.search(r'\{(\w+)\}', out)
        if not m: break
        key = m.group(1)
        if key == 'venue_short':
            val = r.choice(['House of Yes', 'Elsewhere', 'The Echo', 'Schubas',
                            'Stubb\'s', 'The Sinclair', '9:30 Club', 'Tipitina\'s',
                            'Doug Fir', 'The Showbox', 'Brooklyn Bowl'])
        elif key == 'city_name':
            val = city_name
        else:
            pool = _FILLERS.get(key, [key])
            val = r.choice(pool)
        out = out.replace('{' + key + '}', val, 1)
    return out


def _make_events(organizers_by_slug):
    """Generate ~850 events deterministically and yield Event rows + tier rows."""
    today = datetime(2026, 5, 27, 12, 0, 0)  # deterministic "now" baseline
    rows = []
    used_slugs = set()
    # Build organizer pools by city + a small "online-friendly" pool.
    organizers_by_city = {}
    for o in organizers_by_slug.values():
        organizers_by_city.setdefault(o.city_slug, []).append(o)
    online_orgs = [o for o in organizers_by_slug.values() if 'online' in (o.bio or '').lower() or 'eb_online' in o.slug or o.slug == 'eb-online-conf']
    if not online_orgs:
        online_orgs = list(organizers_by_slug.values())[:5]

    # Quotas: ~40 events per city + ~120 online + a few hand-curated ones below.
    target_per_city = 36
    target_online = 100

    for (city_slug, city_name, _state, _, _) in CITIES:
        orgs = organizers_by_city.get(city_slug) or list(organizers_by_slug.values())[:8]
        for i in range(target_per_city):
            r = _seeded_random(f"{city_slug}|{i}")
            cat_slug = r.choice([c[0] for c in CATEGORIES])
            cat_name = CAT_MAP[cat_slug][0]
            org = orgs[(i * 7) % len(orgs)]
            fmt_ = r.choice(_format_for_category(cat_slug))
            tpl = r.choice(_TITLE_TEMPLATES.get(cat_slug, _TITLE_TEMPLATES['music']))
            title = _fill_title(tpl, city_name, r)
            slug = slugify(f"{title}-{city_slug[:5]}-{i}", 100)
            base = slug
            n = 1
            while slug in used_slugs:
                n += 1; slug = f"{base}-{n}"
            used_slugs.add(slug)

            # Distribute events from today-30 to today+180 days
            day_offset = r.randint(-30, 180)
            hour = r.choice([10, 13, 15, 17, 19, 19, 19, 20, 20, 21, 22])
            start_dt = today + timedelta(days=day_offset)
            start_dt = start_dt.replace(hour=hour, minute=r.choice([0, 0, 0, 30]), second=0, microsecond=0)
            duration = r.choice([60, 90, 120, 150, 180, 240, 300])
            end_dt = start_dt + timedelta(minutes=duration)
            venue = r.choice(_VENUE_TEMPLATES.get(city_slug,
                            ['Community Hall, 123 Main St']))
            venue_name = venue.split(',')[0]

            subcats = _SUBCATS.get(cat_slug, ['General'])
            sub = r.choice(subcats)
            tags = r.sample(['live', 'curated', 'late-night', 'family-friendly',
                             '21+', 'all-ages', 'food', 'drinks', 'rsvp',
                             'pop-up', 'limited', 'sold-fast', 'rooftop',
                             'outdoor', 'indoor'], k=r.choice([3, 4, 5]))
            refund = r.choice(['strict', 'moderate', 'flexible', 'any'])
            lang = r.choice(['English']*9 + ['Spanish', 'French'])
            age = r.choice(['All ages', 'All ages', '21+', '18+', 'Ages 12+'])

            tickets_recipe = r.choice(_TIER_RECIPES)
            description = _make_description(title, cat_name, org.name, city_name, fmt_)
            agenda = _make_agenda(start_dt, fmt_, r)
            speakers = _make_speakers(cat_slug, r)
            faq = _make_faq(r)
            featured = (i % 7 == 0) and day_offset >= 0 and day_offset <= 30

            rows.append({
                'slug': slug, 'title': title,
                'summary': title + ' — ' + venue_name,
                'description': description,
                'category_slug': cat_slug, 'subcategory': sub,
                'tags': json.dumps(tags),
                'organizer_id': org.id, 'is_online': False,
                'city_slug': city_slug, 'venue_name': venue_name,
                'venue_address': venue,
                'online_url': '',
                'timezone': 'America/New_York',
                'start_dt': start_dt, 'end_dt': end_dt,
                'image_token': f'gradient-{r.randint(0, 15)}',
                'refund_policy': refund,
                'language': lang, 'format': fmt_,
                'age_restriction': age, 'is_featured': featured,
                'agenda_json': json.dumps(agenda),
                'speakers_json': json.dumps(speakers),
                'faq_json': json.dumps(faq),
                '_tickets': tickets_recipe,
                '_seed_key': slug,
            })

    # Online events
    for i in range(target_online):
        r = _seeded_random(f"online|{i}")
        cat_slug = r.choice([c[0] for c in CATEGORIES])
        cat_name = CAT_MAP[cat_slug][0]
        org = online_orgs[i % len(online_orgs)] if online_orgs else list(organizers_by_slug.values())[0]
        fmt_ = r.choice(['Conference', 'Seminar', 'Class'])
        tpl = r.choice(_TITLE_TEMPLATES.get(cat_slug, _TITLE_TEMPLATES['business']))
        title = _fill_title(tpl, 'Online', r) + ' (Online)'
        slug = slugify(f"online-{title}-{i}", 100)
        base = slug; n = 1
        while slug in used_slugs:
            n += 1; slug = f"{base}-{n}"
        used_slugs.add(slug)
        day_offset = r.randint(-20, 180)
        hour = r.choice([9, 11, 13, 15, 17, 19])
        start_dt = today + timedelta(days=day_offset)
        start_dt = start_dt.replace(hour=hour, minute=0, second=0, microsecond=0)
        end_dt = start_dt + timedelta(minutes=r.choice([60, 90, 120, 240]))
        description = _make_description(title, cat_name, org.name, 'Online', fmt_)
        agenda = _make_agenda(start_dt, fmt_, r)
        speakers = _make_speakers(cat_slug, r)
        faq = _make_faq(r)
        recipe = r.choice([
            [('Free RSVP', 0)],
            [('General Admission', 25)],
            [('Early Bird', 19), ('General Admission', 39)],
            [('Free RSVP', 0), ('Premium Access', 49)],
            [('Student', 15), ('General Admission', 35)],
        ])
        rows.append({
            'slug': slug, 'title': title,
            'summary': title + ' — Online',
            'description': description,
            'category_slug': cat_slug, 'subcategory': r.choice(_SUBCATS.get(cat_slug, ['General'])),
            'tags': json.dumps(['online', 'webinar', 'live']),
            'organizer_id': org.id, 'is_online': True,
            'city_slug': 'online', 'venue_name': 'Online Event',
            'venue_address': '',
            'online_url': f'https://events.example/online/{slug}',
            'timezone': 'America/New_York',
            'start_dt': start_dt, 'end_dt': end_dt,
            'image_token': f'gradient-{r.randint(0, 15)}',
            'refund_policy': r.choice(['flexible', 'any']),
            'language': r.choice(['English']*8 + ['Spanish']),
            'format': fmt_,
            'age_restriction': 'All ages', 'is_featured': (i % 9 == 0),
            'agenda_json': json.dumps(agenda),
            'speakers_json': json.dumps(speakers),
            'faq_json': json.dumps(faq),
            '_tickets': recipe,
            '_seed_key': slug,
        })

    return rows


# ─── Hand-curated benchmark events (referenced by tasks) ──────────────────────

def _curated_events(orgs_by_slug):
    """Specific events the benchmark tasks pin to. Deterministic dates."""
    today = datetime(2026, 5, 27, 12, 0, 0)
    weekend_sat = today + timedelta(days=(5 - today.weekday()) % 7)
    weekend_sat = weekend_sat.replace(hour=20, minute=0, second=0, microsecond=0)

    out = []

    # 1. Free music event this weekend in NY by OUT OF ORDINARY
    out.append({
        'slug': 'rnb-rooftop-free-rsvp-brooklyn-2026',
        'title': 'R&B vs Slow Jams Rooftop — Free with RSVP',
        'summary': 'Free rooftop dance night in Williamsburg with RSVP before 11pm.',
        'description': _make_description('R&B vs Slow Jams Rooftop', 'Music',
                                          'OUT OF ORDINARY', 'New York', 'Party'),
        'category_slug': 'music',
        'subcategory': 'R&B',
        'tags': json.dumps(['rsvp', 'free', 'rooftop', '21+', 'dance']),
        'organizer_id': orgs_by_slug['out-of-ordinary'].id,
        'is_online': False, 'city_slug': 'ny--new-york',
        'venue_name': 'The DL Rooftop',
        'venue_address': 'The DL Rooftop, 95 Delancey St, New York, NY 10002',
        'online_url': '',
        'timezone': 'America/New_York',
        'start_dt': weekend_sat,
        'end_dt': weekend_sat + timedelta(hours=4),
        'image_token': 'gradient-0', 'refund_policy': 'any',
        'language': 'English', 'format': 'Party',
        'age_restriction': '21+', 'is_featured': True,
        'agenda_json': json.dumps([
            {'time': '8:00 PM', 'title': 'Doors / RSVP check-in', 'description': ''},
            {'time': '9:00 PM', 'title': 'Opening set: DJ Sable', 'description': ''},
            {'time':'10:30 PM', 'title':'Main set: Velvet Quartz', 'description': ''},
            {'time':'12:00 AM', 'title':'Last call', 'description': ''},
        ]),
        'speakers_json': json.dumps([]),
        'faq_json': json.dumps(_make_faq(_seeded_random('rnb-rooftop-faq'))),
        '_tickets': [('Free RSVP before 11 PM', 0), ('General Admission after 11 PM', 20)],
        '_seed_key': 'rnb-rooftop-free-rsvp-brooklyn-2026',
    })

    # 2. Bushwick Block Party (the named annual event)
    out.append({
        'slug': '15th-annual-bushwick-collective-block-party',
        'title': '15th Annual Bushwick Collective Block Party',
        'summary': 'The annual Bushwick block party — outdoor murals, hip hop, and food trucks.',
        'description': _make_description('15th Annual Bushwick Block Party',
                                          'Community & Culture',
                                          'The Bushwick Collective',
                                          'New York', 'Festival'),
        'category_slug': 'community',
        'subcategory': 'Block Party',
        'tags': json.dumps(['outdoor', 'free', 'family-friendly', 'community', 'murals']),
        'organizer_id': orgs_by_slug['bushwick-collective'].id,
        'is_online': False, 'city_slug': 'ny--new-york',
        'venue_name': 'Bushwick Collective Outdoor Murals',
        'venue_address': 'Troutman St & St Nicholas Ave, Brooklyn, NY 11237',
        'online_url': '',
        'timezone': 'America/New_York',
        'start_dt': (today + timedelta(days=10)).replace(hour=10, minute=0, second=0, microsecond=0),
        'end_dt':   (today + timedelta(days=10)).replace(hour=20, minute=0, second=0, microsecond=0),
        'image_token': 'gradient-3', 'refund_policy': 'any',
        'language': 'English', 'format': 'Festival',
        'age_restriction': 'All ages', 'is_featured': True,
        'agenda_json': json.dumps(_make_agenda(
            (today + timedelta(days=10)).replace(hour=10, minute=0, second=0, microsecond=0),
            'Festival', _seeded_random('bushwick'))),
        'speakers_json': json.dumps([]),
        'faq_json': json.dumps(_make_faq(_seeded_random('bushwick-faq'))),
        '_tickets': [('Free RSVP', 0), ('Donation Supporter', 10)],
        '_seed_key': '15th-annual-bushwick-collective-block-party',
    })

    # 3. Pioneer Works — Kim Stanley Robinson talk (paid, 7 days out)
    out.append({
        'slug': 'science-fiction-kim-stanley-robinson',
        'title': 'Science + Fiction: Kim Stanley Robinson',
        'summary': 'An evening with Kim Stanley Robinson at Pioneer Works.',
        'description': _make_description('Science + Fiction: Kim Stanley Robinson',
                                          'Performing & Visual Arts',
                                          'Pioneer Works', 'New York', 'Seminar'),
        'category_slug': 'arts',
        'subcategory': 'Literary',
        'tags': json.dumps(['literary', 'science-fiction', 'talk']),
        'organizer_id': orgs_by_slug['pioneer-works'].id,
        'is_online': False, 'city_slug': 'ny--new-york',
        'venue_name': 'Pioneer Works',
        'venue_address': 'Pioneer Works, 159 Pioneer St, Brooklyn, NY 11231',
        'online_url': '',
        'timezone': 'America/New_York',
        'start_dt': (today + timedelta(days=20)).replace(hour=20, minute=0, second=0, microsecond=0),
        'end_dt':   (today + timedelta(days=20)).replace(hour=22, minute=0, second=0, microsecond=0),
        'image_token': 'gradient-9', 'refund_policy': 'flexible',
        'language': 'English', 'format': 'Seminar',
        'age_restriction': 'All ages', 'is_featured': True,
        'agenda_json': json.dumps(_make_agenda(
            (today + timedelta(days=20)).replace(hour=20, minute=0, second=0, microsecond=0),
            'Seminar', _seeded_random('pw'))),
        'speakers_json': json.dumps([
            {'name': 'Kim Stanley Robinson', 'title': 'Author',
             'bio': 'KSR is the Hugo and Nebula award-winning author of the Mars trilogy.'},
        ]),
        'faq_json': json.dumps(_make_faq(_seeded_random('pw-faq'))),
        '_tickets': [('General Admission', 25), ('Pioneer Works Member', 15), ('VIP Reception', 75)],
        '_seed_key': 'science-fiction-kim-stanley-robinson',
    })

    # 4. SF AI conference (online) — for the "online conference about AI" task
    out.append({
        'slug': 'ai-product-summit-online-2026',
        'title': 'AI Product Summit 2026 — Online',
        'summary': 'A one-day online conference on AI for product teams.',
        'description': _make_description('AI Product Summit 2026',
                                          'Business', 'Eventbrite Online Conferences',
                                          'Online', 'Conference'),
        'category_slug': 'business',
        'subcategory': 'Startups',
        'tags': json.dumps(['online', 'ai', 'product', 'conference']),
        'organizer_id': orgs_by_slug['eb-online-conf'].id,
        'is_online': True, 'city_slug': 'online',
        'venue_name': 'Online Event', 'venue_address': '',
        'online_url': 'https://events.example/online/ai-product-summit-online-2026',
        'timezone': 'America/Los_Angeles',
        'start_dt': datetime(2026, 6, 18, 9, 0, 0),   # June 18, 2026
        'end_dt':   datetime(2026, 6, 18, 17, 0, 0),
        'image_token': 'gradient-1', 'refund_policy': 'flexible',
        'language': 'English', 'format': 'Conference',
        'age_restriction': 'All ages', 'is_featured': True,
        'agenda_json': json.dumps(_make_agenda(datetime(2026,6,18,9,0,0),
                                                'Conference', _seeded_random('aips'))),
        'speakers_json': json.dumps([
            {'name': 'Maya Sandoval', 'title': 'Head of AI, Stripe',
             'bio': 'Maya leads applied ML at Stripe and writes about ML systems in production.'},
            {'name': 'Theo Brennan', 'title': 'Founder, Lattice AI',
             'bio': 'Theo founded Lattice AI after a decade at Google.'},
            {'name': 'Soomin Park', 'title': 'VP Product, Notion',
             'bio': 'Soomin oversees product for AI features at Notion.'},
        ]),
        'faq_json': json.dumps(_make_faq(_seeded_random('aips-faq'))),
        '_tickets': [('Free Stream', 0), ('General Admission', 49), ('Workshop Pass', 149)],
        '_seed_key': 'ai-product-summit-online-2026',
    })

    # 5. Sold-out SF event for "sold-out" task
    out.append({
        'slug': 'fillmore-sold-out-night-sf-2026',
        'title': 'The Brassknuckle Five — Live at The Fillmore',
        'summary': 'A rare SF show by The Brassknuckle Five — sold out.',
        'description': _make_description('The Brassknuckle Five Live at The Fillmore',
                                          'Music', 'The Fillmore', 'San Francisco', 'Performance'),
        'category_slug': 'music',
        'subcategory': 'Rock',
        'tags': json.dumps(['rock', 'sold-out', 'live']),
        'organizer_id': orgs_by_slug['the-fillmore-sf'].id,
        'is_online': False, 'city_slug': 'ca--san-francisco',
        'venue_name': 'The Fillmore',
        'venue_address': 'The Fillmore, 1805 Geary Blvd, San Francisco, CA 94115',
        'online_url': '',
        'timezone': 'America/Los_Angeles',
        'start_dt': (today + timedelta(days=15)).replace(hour=21, minute=0, second=0, microsecond=0),
        'end_dt':   (today + timedelta(days=15)).replace(hour=23, minute=30, second=0, microsecond=0),
        'image_token': 'gradient-2', 'refund_policy': 'strict',
        'language': 'English', 'format': 'Performance',
        'age_restriction': '21+', 'is_featured': True,
        'agenda_json': json.dumps([{'time':'9:00 PM','title':'Doors','description':''},
                                    {'time':'10:00 PM','title':'Headlining set','description':''}]),
        'speakers_json': json.dumps([]),
        'faq_json': json.dumps(_make_faq(_seeded_random('fillmore-faq'))),
        '_tickets': [('General Admission (SOLD OUT)', 45, 200, 200),
                     ('VIP Balcony (SOLD OUT)', 95, 50, 50)],
        '_seed_key': 'fillmore-sold-out-night-sf-2026',
    })

    return out


# ─── Help / FAQ articles ──────────────────────────────────────────────────────

_HELP_ARTICLES = [
    ('attending-refunds', 'How do I get a refund?', 'Attending an event',
     'Refunds depend on the organizer policy listed on the event page. To request one, open the event in My Tickets and click "Request refund".'),
    ('attending-transfer', 'Can I transfer a ticket to someone else?', 'Attending an event',
     'Yes — open the order in My Tickets and choose Edit attendee name. Some events disable transfers.'),
    ('attending-cant-find', 'I can\'t find my tickets', 'Attending an event',
     'Check the inbox of the email used to purchase. You can also see all orders in your account under Tickets.'),
    ('attending-cancel-event', 'The event was cancelled', 'Attending an event',
     'If the organizer cancels, you will be refunded to your original payment method within 7-10 days.'),
    ('attending-add-calendar', 'Add an event to my calendar', 'Attending an event',
     'On the event page, scroll to the "When and where" section and click "Add to calendar". An .ics file will download.'),
    ('attending-disability', 'Accessibility & accommodations', 'Attending an event',
     'Contact the organizer at least 7 days in advance with your accommodation request. Most venues are wheelchair-accessible.'),
    ('account-update-email', 'Update my email address', 'Your account',
     'Visit Account > Edit profile and change your email. You\'ll be asked to re-verify.'),
    ('account-password', 'Reset my password', 'Your account',
     'On the login page click "Forgot password" and follow the link.'),
    ('account-interests', 'Manage my interests', 'Your account',
     'In Account > Interests, pick the categories you want to see more of on your homepage.'),
    ('account-following', 'Following organizers', 'Your account',
     'Click "Follow" on any organizer page to see their events on your homepage and get email updates.'),
    ('account-delete', 'Delete my account', 'Your account',
     'Visit Account > Settings > Delete account. This cannot be undone.'),
    ('organizing-create', 'Create my first event', 'Organizing events',
     'Go to "Create an event" from the top nav. The flow guides you through Basics, Details, Tickets, and Publish.'),
    ('organizing-tickets', 'Set up ticket tiers', 'Organizing events',
     'Each event can have multiple tiers (Early Bird, General Admission, VIP). Configure capacity and price per tier.'),
    ('organizing-attendee-info', 'Collect custom info from attendees', 'Organizing events',
     'Add custom questions in the checkout step — dietary restrictions, t-shirt size, etc.'),
    ('organizing-fees', 'How much does Eventbrite charge?', 'Organizing events',
     'Eventbrite charges a per-ticket service fee plus payment processing. Free events have no fees.'),
    ('organizing-payouts', 'When do I get paid?', 'Organizing events',
     'Payouts are issued 4-5 business days after your event ends.'),
    ('organizing-promote', 'Promote my event', 'Organizing events',
     'Use the share buttons on your event page. You can also boost it from the organizer dashboard.'),
    ('organizing-resched', 'Reschedule or cancel an event', 'Organizing events',
     'From the organizer dashboard, click Edit > Event details. You can reschedule or cancel — attendees are notified.'),
    ('payments-cards', 'Accepted payment methods', 'Payments',
     'Visa, Mastercard, American Express, Discover, Apple Pay, Google Pay, and PayPal.'),
    ('payments-failed', 'My payment failed', 'Payments',
     'Check your card details and try again. If the issue persists, contact your bank.'),
    ('payments-currency', 'Change currency', 'Payments',
     'On the event page, use the currency selector in the top right to see localized prices.'),
    ('safety-account', 'Account safety', 'Safety',
     'Enable two-factor authentication from Account > Settings > Security.'),
    ('safety-suspicious', 'Report a suspicious event', 'Safety',
     'On the event page, scroll to the bottom and click "Report this event".'),
]


# ─── Top-level seed entry point ──────────────────────────────────────────────

def seed_database():
    """Idempotent seed of the entire catalog. Gated on Event.count()."""
    if Event.query.count() > 0:
        return

    # 1) Organizers
    pool = _make_organizer_pool()
    org_rows = []
    for (slug, name, city_slug, bio, follower_seed, verified) in pool:
        if Organizer.query.filter_by(slug=slug).first():
            continue
        h = int(hashlib.md5(slug.encode()).hexdigest()[:6], 16)
        org = Organizer(
            slug=slug, name=name, bio=bio,
            city_slug=city_slug,
            website=f'https://events.example/{slug}',
            contact_email=f'hello@{slug.replace("-", "")[:20]}.events',
            follower_seed=follower_seed,
            avatar_color=EVENT_GRADIENTS[h % len(EVENT_GRADIENTS)].split(',')[0].replace('linear-gradient(135deg', '').replace('(', ''),
            verified=verified,
        )
        db.session.add(org)
        org_rows.append(org)
    db.session.flush()

    orgs_by_slug = {o.slug: o for o in Organizer.query.all()}

    # 2) Curated benchmark events
    event_dicts = _curated_events(orgs_by_slug) + _make_events(orgs_by_slug)

    # 3) Persist events + tiers
    for ed in event_dicts:
        tickets_recipe = ed.pop('_tickets')
        ed.pop('_seed_key', None)
        ev = Event(**ed)
        db.session.add(ev)
        db.session.flush()
        for pos, recipe in enumerate(tickets_recipe):
            # recipe is either (name, price) or (name, price, capacity, sold)
            if len(recipe) >= 4:
                name, price, cap, sold = recipe[0], float(recipe[1]), int(recipe[2]), int(recipe[3])
            else:
                name, price = recipe[0], float(recipe[1])
                # cap & initial sold count are deterministic on the event seed
                r = _seeded_random(ev.slug + '|' + name)
                cap = r.choice([50, 80, 100, 150, 200, 250, 300, 500, 750])
                # Most tiers have moderate sold counts; some early-bird tiers
                # have higher sold rates; "Free RSVP" tiers track strongly.
                if 'Free' in name or 'RSVP' in name:
                    sold = r.randint(int(cap*0.35), int(cap*0.85))
                elif 'Early Bird' in name:
                    sold = r.randint(int(cap*0.6), int(cap*0.95))
                elif 'VIP' in name or 'Premium' in name:
                    sold = r.randint(int(cap*0.15), int(cap*0.6))
                else:
                    sold = r.randint(int(cap*0.2), int(cap*0.7))
                sold = max(0, min(sold, cap))
            sale_start = ev.start_dt - timedelta(days=60)
            sale_end   = ev.start_dt - timedelta(hours=2)
            db.session.add(TicketTier(
                event_id=ev.id, name=name, price=price,
                capacity=cap, sold=sold, position=pos,
                description='', sale_start=sale_start, sale_end=sale_end,
                min_per_order=1, max_per_order=10,
            ))
    db.session.commit()

    # 4) Help articles
    for (slug, title, section, body) in _HELP_ARTICLES:
        if HelpArticle.query.filter_by(slug=slug).first():
            continue
        db.session.add(HelpArticle(slug=slug, title=title, section=section, body=body))

    # Add more help articles to hit 50+
    extra_help = []
    sections = ['Attending an event', 'Your account', 'Organizing events', 'Payments', 'Safety']
    extra_topics = [
        ('attending-checkin', 'Event check-in', 'Show your QR code from the My Tickets page on your phone, or print the PDF.'),
        ('attending-late', 'I\'m running late', 'Most events allow late entry — check your ticket page for the door close time.'),
        ('attending-lost-ticket', 'Lost my ticket', 'Reprint from My Tickets > Order > Download PDF.'),
        ('attending-group', 'Buying tickets for a group', 'You can purchase up to 10 tickets in a single order; enter each attendee\'s name during checkout.'),
        ('account-2fa', 'Two-factor authentication', 'In Account > Settings, turn on 2FA via authenticator app or SMS.'),
        ('account-emails', 'Email notifications', 'Choose which emails you receive in Account > Notifications.'),
        ('account-language', 'Change language', 'Account > Preferences > Language.'),
        ('account-merging', 'Merge two accounts', 'Contact support to merge accounts; we\'ll keep your order history.'),
        ('organizing-recurring', 'Set up a recurring event', 'In the create flow, set the recurrence schedule under Details > Recurring.'),
        ('organizing-discount', 'Apply discount codes', 'From the organizer dashboard, create promo codes and assign them to specific ticket tiers.'),
        ('organizing-payouts-international', 'International payouts', 'We support payouts to 40+ countries via Stripe.'),
        ('organizing-team', 'Add team members', 'Organizer dashboard > Settings > Team to invite collaborators.'),
        ('organizing-checkin-app', 'Use the Eventbrite Organizer app', 'Available on iOS and Android — scan QR codes at the door.'),
        ('payments-refund-process', 'How long do refunds take?', 'Refunds typically post within 5-7 business days.'),
        ('payments-multi-currency', 'Selling across currencies', 'Organizers can list events in any of 35 supported currencies.'),
        ('safety-reporting', 'Reporting fraud', 'If you suspect a fraudulent event, click Report on the event page or email trust@eventbrite-help.example.'),
        ('safety-privacy', 'Privacy policy summary', 'We only share attendee info with organizers as needed for event delivery.'),
        ('safety-gdpr', 'GDPR / CCPA requests', 'Submit a data request from Account > Settings > Privacy.'),
        ('attending-online-events', 'Joining an online event', 'On the day of the event, your join link is available in My Tickets and was emailed at the time of purchase.'),
        ('attending-recording', 'Will the event be recorded?', 'Recording availability is set by the organizer and noted on the event page.'),
        ('attending-add-saved', 'Save an event for later', 'Click the heart icon on any event card to save it.'),
        ('attending-share', 'Share an event with a friend', 'Use the share button on the event page or copy the URL.'),
        ('attending-mobile-app', 'Use the Eventbrite app', 'iOS and Android — download from the app store.'),
        ('organizing-stream', 'Stream an online event', 'Connect Zoom, Hopin, or YouTube Live in the create flow.'),
        ('organizing-q-and-a', 'Custom checkout questions', 'Collect dietary, t-shirt size, accessibility requests at checkout.'),
        ('organizing-waitlist', 'Waitlist sold-out events', 'When tickets sell out you can collect waitlist signups for cancellations.'),
        ('payments-eb-fees-free', 'No fees on free events', 'There are no service fees when you sell free tickets via Eventbrite.'),
        ('safety-covid', 'COVID-19 safety', 'Follow local public health guidance and the organizer\'s posted policy.'),
        ('attending-faq-vip', 'What does VIP include?', 'Depends on the event — typically early entry, exclusive seating, and a swag bag.'),
        ('attending-faq-late', 'What if I miss the event?', 'Unfortunately we cannot refund for no-shows unless the organizer\'s policy allows it.'),
    ]
    for (slug, title, body) in extra_topics:
        if HelpArticle.query.filter_by(slug=slug).first():
            continue
        section = sections[(hash(slug) % len(sections))]
        db.session.add(HelpArticle(slug=slug, title=title, section=section, body=body))
    db.session.commit()


def seed_benchmark_users():
    """Idempotent: 4 benchmark users with specific orders/saves/follows."""
    if User.query.filter_by(email='alice.j@test.com').first():
        return
    today = datetime(2026, 5, 27, 12, 0, 0)

    users_data = [
        ('alice.j@test.com', 'Alice Johnson', 'alice12345',
         'New York', ['music', 'arts', 'food-drink']),
        ('bob.s@test.com', 'Bob Smith', 'bobpassword',
         'Los Angeles', ['business', 'sports', 'travel']),
        ('carol.m@test.com', 'Carol Martinez', 'carolpw2026',
         'Austin', ['music', 'health', 'community']),
        ('david.k@test.com', 'David Kim', 'davidkim2026',
         'San Francisco', ['business', 'film', 'spirituality']),
    ]
    user_objs = []
    for em, name, pw, city, interests in users_data:
        u = User(email=em, name=name, city=city, interests=json.dumps(interests))
        u.set_password(pw)
        db.session.add(u)
        user_objs.append(u)
    db.session.flush()

    # Make 60+ benchmark orders
    all_events = (Event.query.filter(Event.start_dt < datetime(2026, 12, 1))
                             .order_by(Event.id.asc()).all())
    orgs = Organizer.query.all()
    r = _seeded_random('benchmark-orders')

    target_orders_per_user = 16  # 4 users * 16 = 64
    used = set()
    for u in user_objs:
        for k in range(target_orders_per_user):
            attempts = 0
            while attempts < 25:
                ev = r.choice(all_events)
                if (u.id, ev.id) in used:
                    attempts += 1; continue
                used.add((u.id, ev.id))
                break
            else:
                continue
            tier_choices = [t for t in ev.tickets if t.remaining() >= 2]
            if not tier_choices:
                tier_choices = ev.tickets
            if not tier_choices:
                continue
            tier = r.choice(tier_choices)
            qty  = r.choice([1, 1, 1, 2, 2, 3])
            qty  = min(qty, max(1, tier.remaining()))
            o = Order(
                code='ORD' + ''.join(r.choice('ABCDEFGHJKMNPQRSTUVWXYZ23456789') for _ in range(9)),
                user_id=u.id, event_id=ev.id,
                created_at=today - timedelta(days=r.randint(1, 60)),
                total=tier.price * qty,
                status='confirmed',
                contact_email=u.email, contact_name=u.name,
                contact_phone='+1-555-0100',
                notes=json.dumps({'dietary': r.choice(['', '', 'Vegetarian', 'Gluten-free'])}),
            )
            db.session.add(o); db.session.flush()
            db.session.add(OrderItem(order_id=o.id, tier_id=tier.id, qty=qty,
                                     unit_price=tier.price))
            tier.sold += qty
            for i in range(qty):
                attendee_name = u.name if i == 0 else f"Guest of {u.name.split()[0]} #{i}"
                db.session.add(IssuedTicket(
                    order_id=o.id, tier_id=tier.id,
                    code='TKT' + ''.join(r.choice('ABCDEFGHJKMNPQRSTUVWXYZ23456789') for _ in range(10)),
                    attendee_name=attendee_name,
                    attendee_email=u.email if i == 0 else f"guest{i}@test.com",
                ))

    # Follows & saves: each user follows 4-8 organizers, saves 6-12 events.
    for u in user_objs:
        follow_orgs = r.sample(orgs, k=min(len(orgs), r.choice([4, 5, 6, 7, 8])))
        for o in follow_orgs:
            db.session.add(Follow(user_id=u.id, organizer_id=o.id,
                                  followed_at=today - timedelta(days=r.randint(1, 90))))
        upcoming = (Event.query.filter(Event.start_dt >= today)
                              .order_by(Event.id.asc()).limit(400).all())
        saves = r.sample(upcoming, k=min(len(upcoming), r.choice([6, 7, 8, 9, 10, 11, 12])))
        for ev in saves:
            db.session.add(SavedEvent(user_id=u.id, event_id=ev.id,
                                       saved_at=today - timedelta(days=r.randint(1, 30))))
    db.session.commit()
