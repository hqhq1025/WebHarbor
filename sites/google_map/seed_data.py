"""
Seed data for Google Maps mirror.
Loads PLACES and CITIES from scrape_wiki so every entity has real images on disk.
Enriches each place with address, phone, hours, rating, etc.
"""
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote_plus
from scrape_wiki import PLACES as RAW_PLACES, CITIES as RAW_CITIES

# Pinned reference moment used for all explicit timestamps in seeded
# user-content (reviews, photos, timeline). Keeps the resulting DB
# deterministic across builds.
MIRROR_REFERENCE_DATE = datetime(2026, 4, 15, 12, 0, 0)

BASE = Path(__file__).parent

# Categories with display info
CATEGORIES = [
    {
        "slug": "restaurants", "name": "Restaurants", "icon": "restaurant",
        "color": "#ea4335",
        "description": "Discover the best places to eat, from cozy neighborhood cafes to world-class dining.",
    },
    {
        "slug": "hotels", "name": "Hotels", "icon": "hotel",
        "color": "#4285f4",
        "description": "Find the perfect place to stay - hotels, resorts, and boutique properties around the world.",
    },
    {
        "slug": "attractions", "name": "Attractions", "icon": "camera",
        "color": "#fbbc04",
        "description": "Iconic landmarks, historic sites, and must-see destinations in every city.",
    },
    {
        "slug": "museums", "name": "Museums", "icon": "museum",
        "color": "#34a853",
        "description": "Art, history, science - explore world-class collections and exhibitions.",
    },
    {
        "slug": "parks", "name": "Parks & Nature", "icon": "park",
        "color": "#34a853",
        "description": "Green spaces, gardens, beaches, and natural wonders for every kind of explorer.",
    },
    {
        "slug": "shopping", "name": "Shopping", "icon": "shopping_bag",
        "color": "#a142f4",
        "description": "Markets, malls, boutiques, and flagship stores in the world's best shopping destinations.",
    },
    {
        "slug": "entertainment", "name": "Entertainment", "icon": "theater_comedy",
        "color": "#f06292",
        "description": "Theaters, concert halls, clubs, and live venues for unforgettable nights out.",
    },
    {
        "slug": "transit", "name": "Transit", "icon": "directions_transit",
        "color": "#616161",
        "description": "Airports, train stations, and transportation hubs to help you get around.",
    },
]

# Additional "synthetic" restaurants and hotels and shops per city,
# so each category has enough entries for a rich listing.
RESTAURANT_STYLES = [
    ("Bistro", "restaurants", "Classic French-style bistro serving seasonal dishes in a warm neighborhood setting.", "$$"),
    ("Osteria", "restaurants", "Rustic Italian osteria with handmade pasta, wood-fired pizza, and wine from small producers.", "$$"),
    ("Ramen Bar", "restaurants", "Counter-seat ramen shop specializing in rich tonkotsu broth and house-made noodles.", "$"),
    ("Steakhouse", "restaurants", "Upscale steakhouse with dry-aged cuts, a curated wine list, and attentive service.", "$$$"),
    ("Sushi Counter", "restaurants", "Omakase sushi counter with seasonal fish and chef's choice tasting menus.", "$$$$"),
    ("Taqueria", "restaurants", "Casual taqueria serving street tacos, al pastor, and fresh-made salsas.", "$"),
    ("Wine Bar", "restaurants", "Intimate wine bar pairing small plates with an extensive natural-wine list.", "$$"),
    ("Brewpub", "restaurants", "Lively brewpub with house-brewed beers, wood-fired pizzas, and outdoor seating.", "$$"),
    ("Cafe", "restaurants", "Cozy neighborhood cafe with specialty coffee, fresh pastries, and all-day brunch.", "$"),
    ("Tapas Bar", "restaurants", "Spanish tapas bar with a long list of small plates, sherries, and Iberian wines.", "$$"),
    ("Dim Sum", "restaurants", "Bustling dim sum restaurant with trolley service and classic Cantonese favorites.", "$$"),
    ("Pho House", "restaurants", "Vietnamese noodle house specializing in slow-simmered beef pho and banh mi.", "$"),
]

HOTEL_STYLES = [
    ("Grand Hotel", "hotels", "Historic grand hotel with classic architecture, a lavish lobby, and white-glove service.", "$$$$"),
    ("Boutique Inn", "hotels", "Stylish boutique hotel with individually designed rooms and a locally-rooted bar and restaurant.", "$$$"),
    ("Business Hotel", "hotels", "Modern business hotel with full-service amenities, meeting rooms, and express check-in.", "$$"),
    ("Resort", "hotels", "Full-service resort with pool, spa, multiple restaurants, and easy access to the beach.", "$$$$"),
    ("Urban Loft", "hotels", "Design-forward loft hotel in a converted warehouse, with open layouts and artful touches.", "$$$"),
    ("Budget Stay", "hotels", "Comfortable budget hotel with clean rooms, fast Wi-Fi, and a great location near transit.", "$"),
]

SHOP_STYLES = [
    ("Department Store", "shopping", "Iconic multi-level department store with fashion, beauty, home, and a food hall.", "$$$"),
    ("Bookshop", "shopping", "Beloved independent bookshop with thoughtfully curated shelves and a reading corner.", "$$"),
    ("Vintage Market", "shopping", "Weekend vintage market with antiques, rare records, one-of-a-kind clothing, and street food.", "$$"),
    ("Concept Store", "shopping", "Concept store combining fashion, art, and home goods from emerging designers.", "$$$"),
    ("Farmers Market", "shopping", "Open-air farmers market with seasonal produce, artisan foods, and live music.", "$"),
]

ENTERTAINMENT_STYLES = [
    ("Jazz Club", "entertainment", "Intimate jazz club with nightly sets, craft cocktails, and an old-school speakeasy vibe.", "$$"),
    ("Comedy Club", "entertainment", "Stand-up comedy club with local talent and weekly touring headliners.", "$$"),
    ("Cinema", "entertainment", "Art-house cinema showing independent films, classics, and special events.", "$"),
    ("Concert Hall", "entertainment", "Historic concert hall hosting orchestras, chamber music, and world-class recitals.", "$$$"),
    ("Theater", "entertainment", "Grand theater with a rich program of plays, musicals, and dance performances.", "$$$"),
]

CAFE_STYLES = [
    ("Coffee Roaster", "restaurants", "Specialty coffee roaster serving single-origin pour-overs and espresso drinks.", "$"),
    ("Pastry Shop", "restaurants", "Acclaimed pastry shop with flaky croissants, seasonal tarts, and house-made chocolates.", "$"),
    ("Brunch Spot", "restaurants", "All-day brunch spot with fluffy pancakes, eggs benedict, and fresh juices.", "$$"),
]


CITY_COORDS = {
    "new-york": (40.7128, -74.0060),
    "los-angeles": (34.0522, -118.2437),
    "chicago": (41.8781, -87.6298),
    "san-francisco": (37.7749, -122.4194),
    "seattle": (47.6062, -122.3321),
    "boston": (42.3601, -71.0589),
    "las-vegas": (36.1699, -115.1398),
    "london": (51.5074, -0.1278),
    "paris": (48.8566, 2.3522),
    "rome": (41.9028, 12.4964),
    "barcelona": (41.3851, 2.1734),
    "madrid": (40.4168, -3.7038),
    "amsterdam": (52.3676, 4.9041),
    "berlin": (52.5200, 13.4050),
    "vienna": (48.2082, 16.3738),
    "prague": (50.0755, 14.4378),
    "istanbul": (41.0082, 28.9784),
    "athens": (37.9838, 23.7275),
    "venice": (45.4408, 12.3155),
    "florence": (43.7696, 11.2558),
    "milan": (45.4642, 9.1900),
    "tokyo": (35.6762, 139.6503),
    "kyoto": (35.0116, 135.7681),
    "beijing": (39.9042, 116.4074),
    "singapore": (1.3521, 103.8198),
    "dubai": (25.2048, 55.2708),
    "mumbai": (19.0760, 72.8777),
    "agra": (27.1767, 78.0081),
    "sydney": (-33.8688, 151.2093),
    "toronto": (43.6532, -79.3832),
    "vancouver": (49.2827, -123.1207),
    "mexico-city": (19.4326, -99.1332),
    "rio-de-janeiro": (-22.9068, -43.1729),
    "lima": (-12.0464, -77.0428),
    "edinburgh": (55.9533, -3.1883),
    "brussels": (50.8503, 4.3517),
    "budapest": (47.4979, 19.0402),
    "warsaw": (52.2297, 21.0122),
}


# Street names per city (roughly local-flavored)
STREET_NAMES = {
    "new-york": ["Broadway", "5th Ave", "Madison Ave", "Lexington Ave", "Park Ave"],
    "los-angeles": ["Sunset Blvd", "Rodeo Dr", "Melrose Ave", "Wilshire Blvd", "Beverly Dr"],
    "chicago": ["Michigan Ave", "State St", "Rush St", "Wacker Dr", "Halsted St"],
    "san-francisco": ["Market St", "Valencia St", "Polk St", "Fillmore St", "Mission St"],
    "seattle": ["Pike St", "1st Ave", "Pine St", "Denny Way", "Broadway E"],
    "boston": ["Newbury St", "Boylston St", "Tremont St", "Hanover St", "Charles St"],
    "las-vegas": ["Las Vegas Blvd", "Fremont St", "Tropicana Ave", "Sahara Ave", "Flamingo Rd"],
    "london": ["Oxford St", "Regent St", "Bond St", "King's Rd", "Shaftesbury Ave"],
    "paris": ["Rue de Rivoli", "Champs-Élysées", "Rue Saint-Honoré", "Boulevard Haussmann", "Rue Montorgueil"],
    "rome": ["Via del Corso", "Via Veneto", "Via Condotti", "Via Nazionale", "Via Giulia"],
    "barcelona": ["La Rambla", "Passeig de Gràcia", "Avinguda Diagonal", "Carrer de Balmes", "Gran Via"],
    "madrid": ["Gran Vía", "Calle de Alcalá", "Paseo del Prado", "Calle Mayor", "Calle Fuencarral"],
    "amsterdam": ["Damrak", "Kalverstraat", "Leidsestraat", "Prinsengracht", "Herengracht"],
    "berlin": ["Unter den Linden", "Friedrichstraße", "Kurfürstendamm", "Oranienstraße", "Torstraße"],
    "vienna": ["Kärntner Straße", "Graben", "Mariahilfer Straße", "Ringstraße", "Rotenturmstraße"],
    "prague": ["Wenceslas Square", "Pařížská", "Na Příkopě", "Celetná", "Karmelitská"],
    "istanbul": ["İstiklal Caddesi", "Bağdat Caddesi", "Nişantaşı", "Tarlabaşı Blv", "Divan Yolu"],
    "athens": ["Ermou St", "Athinas St", "Panepistimiou St", "Kolonaki Sq", "Plaka"],
    "venice": ["Strada Nuova", "Via Garibaldi", "Riva degli Schiavoni", "Calle Larga", "Fondamenta"],
    "florence": ["Via dei Calzaiuoli", "Via Tornabuoni", "Via del Corso", "Via Roma", "Ponte Vecchio"],
    "milan": ["Via Monte Napoleone", "Corso Buenos Aires", "Via della Spiga", "Corso Como", "Via Torino"],
    "tokyo": ["Omotesando", "Ginza Chuo-dori", "Shibuya Center-gai", "Takeshita Street", "Nakamise-dori"],
    "kyoto": ["Shijo-dori", "Sanjo-dori", "Kawaramachi-dori", "Pontocho", "Teramachi-dori"],
    "beijing": ["Wangfujing St", "Chang'an Ave", "Qianmen St", "Nanluoguxiang", "Guozijian St"],
    "singapore": ["Orchard Rd", "Clarke Quay", "Arab St", "Bugis St", "Chinatown"],
    "dubai": ["Sheikh Zayed Rd", "Al Wasl Rd", "Jumeirah Beach Rd", "Al Khail Rd", "Downtown Blv"],
    "mumbai": ["Marine Drive", "Colaba Causeway", "Linking Rd", "Hill Rd", "MG Rd"],
    "agra": ["Fatehabad Rd", "MG Rd", "Taj East Gate Rd", "Shah Jahan Rd", "Mall Rd"],
    "sydney": ["George St", "Pitt St", "Oxford St", "King St", "Darling Harbour"],
    "toronto": ["Yonge St", "Queen St W", "King St W", "Bloor St W", "Spadina Ave"],
    "vancouver": ["Robson St", "Granville St", "Main St", "Commercial Dr", "Davie St"],
    "mexico-city": ["Av Reforma", "Av Insurgentes", "Av Madero", "Av Juárez", "Polanco"],
    "rio-de-janeiro": ["Av Atlântica", "R Garcia d'Ávila", "Av Rio Branco", "Av Nossa Sra de Copacabana", "Leblon"],
    "lima": ["Av Larco", "Jr de la Unión", "Av Arequipa", "Av Benavides", "Calle Bolívar"],
    "edinburgh": ["Royal Mile", "Princes St", "George St", "Grassmarket", "Cockburn St"],
    "brussels": ["Rue Neuve", "Grand Place", "Av Louise", "Chaussée d'Ixelles", "Rue des Bouchers"],
    "budapest": ["Váci utca", "Andrássy út", "Király utca", "Nagymező utca", "Ráday utca"],
    "warsaw": ["Nowy Świat", "Krakowskie Przedmieście", "Marszałkowska", "Chmielna", "Mokotowska"],
}

OPEN_HOURS_TEMPLATES = [
    "Mon–Sun: 9:00 AM – 6:00 PM",
    "Tue–Sun: 10:00 AM – 7:00 PM, Closed Mon",
    "Mon–Sat: 8:00 AM – 10:00 PM, Sun 9:00 AM – 5:00 PM",
    "Open 24 hours",
    "Mon–Thu: 5:00 PM – 11:00 PM, Fri–Sat: 5:00 PM – 1:00 AM",
    "Mon–Sun: 7:00 AM – 11:00 PM",
    "Tue–Sat: 11:30 AM – 2:30 PM, 6:00 PM – 10:30 PM",
    "Mon–Fri: 10:00 AM – 5:00 PM, Weekends: 10:00 AM – 6:00 PM",
]


def google_maps_search_url(name, city_display=""):
    """Real Google Maps URL for seeded place/share fields."""
    query = f"{name} {city_display}".strip()
    return f"https://www.google.com/maps/place/{quote_plus(query)}/"


def coord_jitter(base, amount=0.01):
    return base + random.uniform(-amount, amount)


def build_places(db, Place, Category, City):
    """Seed DB with all places. Returns count of places."""
    cat_by_slug = {c.slug: c for c in Category.query.all()}
    city_by_slug = {c.slug: c for c in City.query.all()}

    random.seed(42)
    count = 0

    # --- 1) Real wiki places ---
    wiki_descriptions = {
        "eiffel-tower": "Wrought-iron lattice tower on the Champ de Mars, one of the most recognisable structures in the world.",
        "statue-of-liberty": "Colossal neoclassical sculpture on Liberty Island - a gift from France and a universal symbol of freedom.",
        "empire-state-building": "Iconic 102-story Art Deco skyscraper with an observation deck offering sweeping views of Manhattan.",
        "times-square": "Bustling intersection and major commercial area known for its bright lights, broadway theaters, and energy.",
        "brooklyn-bridge": "Historic hybrid cable-stayed / suspension bridge connecting Manhattan and Brooklyn over the East River.",
        "central-park": "Sprawling 843-acre park in the heart of Manhattan with lakes, trails, playgrounds, and open lawns.",
        "one-world-trade-center": "The main building of the rebuilt World Trade Center complex in Lower Manhattan, standing 1,776 feet tall.",
        "colosseum": "Ancient oval amphitheater in the center of Rome - the largest ever built and a UNESCO World Heritage Site.",
        "roman-forum": "Ruins of several important ancient government buildings at the center of Rome, full of millennia of history.",
        "pantheon-rome": "Former Roman temple and current Catholic church, featuring a famous concrete dome nearly 2,000 years old.",
        "trevi-fountain": "The largest Baroque fountain in Rome - toss a coin over your shoulder to ensure you return.",
        "vatican-city": "Independent city-state and headquarters of the Roman Catholic Church, home to St. Peter's Basilica.",
        "sagrada-familia": "Gaudí's unfinished masterpiece - a breathtaking basilica that has been under construction since 1882.",
        "park-guell": "A whimsical public park full of gardens and architectural elements designed by Antoni Gaudí.",
        "casa-batllo": "Colorful and sculptural apartment building by Gaudí, a masterpiece of Catalan Modernism.",
        "big-ben": "The iconic clock tower at the north end of the Palace of Westminster - a symbol of London.",
        "tower-bridge": "A combined bascule and suspension bridge over the River Thames, iconic for its twin towers.",
        "london-eye": "A giant Ferris wheel on the South Bank offering stunning views of the London skyline.",
        "buckingham-palace": "The London residence and administrative headquarters of the British monarch.",
        "westminster-abbey": "Large, gothic abbey church - the site of every coronation since 1066.",
        "tower-of-london": "Historic castle on the north bank of the Thames - home to the Crown Jewels and centuries of royal history.",
        "british-museum": "One of the world's great museums, with 8 million works chronicling human culture and history.",
        "natural-history-museum-london": "A magnificent museum with dinosaur skeletons, fossils, gems, and natural wonders.",
        "tate-modern": "Britain's national gallery of international modern art, housed in a former power station.",
        "louvre": "The world's most-visited museum, home to the Mona Lisa, Venus de Milo, and countless treasures.",
        "notre-dame-de-paris": "A medieval Catholic cathedral on the Île de la Cité, an icon of French Gothic architecture.",
        "arc-de-triomphe": "The triumphal arch standing at the western end of the Champs-Élysées, honouring those who fought for France.",
        "musee-d-orsay": "A museum in a former railway station housing the world's largest collection of Impressionist masterpieces.",
        "montmartre": "A historic hilltop neighborhood famous for its artistic history, bohemian vibe, and Sacré-Cœur basilica.",
        "sacre-coeur": "Roman Catholic basilica dedicated to the Sacred Heart of Jesus, perched atop Montmartre.",
        "palace-of-versailles": "The opulent former royal palace of France - gilded halls, gardens, and fountains.",
        "great-wall-of-china": "A series of fortifications built across the historical northern borders of ancient China.",
        "forbidden-city": "A palace complex in central Beijing that served as the home of emperors of the Ming and Qing dynasties.",
        "temple-of-heaven": "An imperial complex of religious buildings used for annual ceremonies of prayer to Heaven.",
        "summer-palace": "A vast ensemble of lakes, gardens and palaces in Beijing - a masterpiece of Chinese landscape design.",
        "tiananmen-square": "A city square in the center of Beijing, one of the largest public squares in the world.",
        "burj-khalifa": "The world's tallest building at 828 meters, with observation decks and a stunning exterior lighting display.",
        "palm-jumeirah": "A man-made archipelago in the shape of a palm tree - home to luxury resorts and residences.",
        "dubai-mall": "One of the world's largest shopping malls, featuring an aquarium, ice rink, and over 1,200 stores.",
        "burj-al-arab": "A luxury hotel on an artificial island, known for its sail-shaped silhouette and opulent interiors.",
        "sydney-opera-house": "A multi-venue performing arts centre at Sydney Harbour, known for its iconic sail-like roof design.",
        "sydney-harbour-bridge": "A heritage-listed steel arch bridge across Sydney Harbour - climb it for unforgettable views.",
        "bondi-beach": "One of Australia's most famous beaches, known for surfing, sand, and the scenic coastal walk to Coogee.",
        "taj-mahal": "An ivory-white marble mausoleum on the right bank of the river Yamuna - one of the wonders of the world.",
        "gateway-of-india": "An arch-monument built during the 20th century in Mumbai, overlooking the Arabian Sea.",
        "tokyo-tower": "A communications and observation tower in Shibakōen - the second tallest structure in Japan.",
        "tokyo-skytree": "A broadcasting, restaurant, and observation tower in Tokyo - the tallest tower in the world.",
        "sensoji": "An ancient Buddhist temple in Asakusa - Tokyo's oldest and most significant temple.",
        "shibuya-crossing": "The world's busiest pedestrian crossing - experience the controlled chaos in the heart of Tokyo.",
        "meiji-shrine": "A Shinto shrine set in a dense forest oasis in the middle of Tokyo, dedicated to Emperor Meiji.",
        "fushimi-inari": "A Shinto shrine famous for its thousands of vermilion torii gates winding up the mountainside.",
        "kinkakuji": "The Golden Pavilion, a Zen Buddhist temple whose top two floors are covered in gold leaf.",
        "ginkakuji": "The Silver Pavilion, a Zen temple known for its refined elegance and moss garden.",
        "golden-gate-bridge": "An iconic 1.7-mile suspension bridge connecting San Francisco to Marin County.",
        "alcatraz": "A small island in San Francisco Bay, famous for its notorious former federal penitentiary.",
        "fishermans-wharf": "A neighborhood and tourist attraction known for seafood, sea lions, and views of the bay.",
        "lombard-street": "An east-west street famous for a steep, one-block section with eight hairpin turns.",
        "golden-gate-park": "A large urban park stretching over 1,000 acres with gardens, museums, and recreation.",
        "hollywood-sign": "An iconic landmark on Mount Lee, originally erected in 1923 to advertise a real estate development.",
        "griffith-observatory": "An observatory perched on the southern slope of Mount Hollywood, offering city views and space exhibits.",
        "santa-monica-pier": "A large double-jointed pier at the foot of Colorado Avenue - home to an amusement park and restaurants.",
        "venice-beach": "A beachfront neighborhood known for its canals, boardwalk, skate park, and Muscle Beach.",
        "getty-center": "A campus of the Getty Museum housing European paintings, drawings, and decorative arts.",
        "willis-tower": "Formerly the Sears Tower, this 110-story skyscraper has an observation deck on the 103rd floor.",
        "millennium-park": "A public park in the Loop featuring the Cloud Gate ('The Bean') and the Jay Pritzker Pavilion.",
        "navy-pier": "A 3,300-foot-long pier on the Chicago shoreline of Lake Michigan with rides, shops, and restaurants.",
        "art-institute-of-chicago": "One of the oldest and largest art museums in the United States, with over 300,000 works.",
        "space-needle": "An observation tower built for the 1962 World's Fair and a symbol of Seattle's skyline.",
        "pike-place-market": "A historic public market overlooking Elliott Bay - home to fresh seafood, produce, and local crafts.",
        "chihuly-garden": "An exhibition showcasing the studio glass work of Dale Chihuly in a garden and indoor gallery setting.",
        "fenway-park": "The oldest active Major League Baseball stadium - home of the Boston Red Sox since 1912.",
        "freedom-trail": "A 2.5-mile-long path through downtown Boston connecting 16 historic sites.",
        "harvard-yard": "The old, historic center of Harvard University's campus in Cambridge.",
        "las-vegas-strip": "A 4.2-mile stretch of South Las Vegas Boulevard lined with casinos, resorts, and nightclubs.",
        "bellagio": "A luxury resort and casino known for its famous dancing fountains and fine art gallery.",
        "caesars-palace": "A luxury hotel and casino with Roman-themed architecture and world-class entertainment.",
        "venetian-resort": "A luxury hotel and casino resort with replicas of Venetian landmarks and indoor gondola rides.",
        "golden-gate-park-2": "A world-famous national park featuring granite cliffs, waterfalls, giant sequoias, and diverse wildlife.",
        "grand-canyon": "A steep-sided canyon carved by the Colorado River, one of the Seven Natural Wonders of the World.",
        "marina-bay-sands": "An integrated resort in Singapore featuring a hotel, mall, casino, and a SkyPark infinity pool.",
        "gardens-by-the-bay": "A nature park with iconic Supertree Grove and cooled conservatories showcasing plants from around the world.",
        "merlion": "A mythical creature and national personification of Singapore, depicted as a lion-headed fish.",
        "raffles-hotel": "A colonial-style luxury hotel opened in 1887 - a Singapore institution and historic landmark.",
        "brandenburg-gate": "An 18th-century neoclassical monument - one of the best-known landmarks of Germany.",
        "reichstag": "A historic government building housing the German Bundestag, with a famous glass dome.",
        "berlin-wall": "A guarded concrete barrier that physically and ideologically divided Berlin from 1961 to 1989.",
        "pergamon-museum": "A museum on the Museum Island in Berlin, housing ancient Greek, Roman, and Islamic artifacts.",
        "museum-island": "A UNESCO World Heritage Site featuring five world-famous museums on an island in the Spree River.",
        "rijksmuseum": "The Dutch national museum dedicated to arts and history - home to Rembrandt's Night Watch.",
        "van-gogh-museum": "A museum dedicated to the works of Vincent van Gogh and his contemporaries.",
        "anne-frank-house": "A biographical museum dedicated to Jewish wartime diarist Anne Frank.",
        "vondelpark": "A 47-hectare public urban park in Amsterdam - one of the most visited in the world.",
        "canal-ring": "The 17th-century canal belt of Amsterdam, a UNESCO World Heritage Site.",
        "prado": "Madrid's main national art museum, featuring European art from the 12th to early 20th century.",
        "royal-palace-madrid": "The official residence of the Spanish royal family at the city of Madrid.",
        "retiro-park": "A large public park with gardens, a lake, monuments, and a crystal palace.",
        "plaza-mayor-madrid": "A major public square in the heart of Madrid, surrounded by three-story residential buildings.",
        "hagia-sophia": "A former Byzantine church, former Ottoman mosque, and now a mosque and museum in Istanbul.",
        "blue-mosque": "An Ottoman-era imperial mosque with six minarets and stunning blue tile interior.",
        "topkapi-palace": "A large museum and historical royal residence of Ottoman sultans.",
        "grand-bazaar": "One of the largest and oldest covered markets in the world, with 61 streets and over 4,000 shops.",
        "acropolis": "An ancient citadel above Athens containing the remains of several buildings, including the Parthenon.",
        "parthenon": "A former temple dedicated to the goddess Athena, regarded as an enduring symbol of ancient Greece.",
        "charles-bridge": "A medieval stone arch bridge crossing the Vltava river in Prague - lined with baroque statues.",
        "prague-castle": "A castle complex from the 9th century - the official residence of the President of the Czech Republic.",
        "old-town-square": "A historic square in Prague's Old Town with the Astronomical Clock and gothic architecture.",
        "st-stephens-cathedral": "The mother church of the Roman Catholic Archdiocese of Vienna.",
        "schonbrunn-palace": "A Baroque palace that was the main summer residence of the Habsburg rulers.",
        "belvedere-palace": "A historic building complex consisting of two Baroque palaces and an orangery.",
        "cn-tower": "A 553.3-metre concrete communications and observation tower in downtown Toronto.",
        "niagara-falls": "Three waterfalls straddling the international border between Canada and the United States.",
        "stanley-park": "A 405-hectare public park bordering downtown Vancouver, surrounded by waters of Burrard Inlet.",
        "capilano-bridge": "A simple suspension bridge crossing the Capilano River, 140m long and 70m above the river.",
        "mexico-city-cathedral": "The largest cathedral in the Americas, built over centuries with multiple architectural styles.",
        "teotihuacan": "An ancient Mesoamerican city located in a sub-valley of the Valley of Mexico.",
        "christ-the-redeemer": "An Art Deco statue of Jesus Christ atop Mount Corcovado, overlooking Rio de Janeiro.",
        "sugarloaf": "A peak situated on a peninsula at the mouth of Guanabara Bay, reachable by cable car.",
        "copacabana": "A beachfront neighborhood with a 4km curved beach - one of the most famous beaches in the world.",
        "machu-picchu": "A 15th-century Inca citadel located on a mountain ridge above the Sacred Valley.",
        "doge-palace": "A palace built in Venetian Gothic style, and one of the main landmarks of the city of Venice.",
        "rialto-bridge": "The oldest of the four bridges spanning the Grand Canal in Venice - a popular landmark.",
        "st-marks-square": "The principal public square of Venice, dominated by St Mark's Basilica and the Campanile.",
        "santa-maria-del-fiore": "The cathedral of Florence, famous for its massive terracotta-tiled dome by Filippo Brunelleschi.",
        "uffizi-gallery": "A prominent art museum with priceless works, including Botticelli's Birth of Venus.",
        "ponte-vecchio": "A medieval stone closed-spandrel segmental arch bridge over the Arno River, noted for the shops along it.",
        "duomo-milano": "The cathedral of Milan - the largest church in Italy, with a famous marble façade.",
        "galleria-vittorio-emanuele": "Italy's oldest active shopping gallery, housing luxury boutiques in a stunning glass-roofed arcade.",
        "edinburgh-castle": "A historic castle on Castle Rock, dominating the skyline of Edinburgh.",
        "royal-mile": "The main thoroughfare of the Old Town of Edinburgh, running between Edinburgh Castle and Holyrood Palace.",
        "grand-place": "The central square of Brussels, surrounded by opulent guild houses and the city's Town Hall.",
        "atomium": "A 102-metre building in Brussels originally constructed for the 1958 World's Fair.",
        "parliament-building-budapest": "The seat of the National Assembly of Hungary - a notable landmark on the Danube.",
        "buda-castle": "The historical castle and palace complex of the Hungarian kings in Budapest.",
        "chain-bridge": "A suspension bridge that spans the River Danube between Buda and Pest - the first permanent bridge.",
        "warsaw-old-town": "The historic center of Warsaw, a UNESCO World Heritage Site meticulously rebuilt after WWII.",
        "market-square-krakow": "The main square of the Old Town of Kraków - the largest medieval town square in Europe.",
    }

    # Pricing/rating ranges by category
    price_by_cat = {
        "attractions": ["Free", "$", "$"],
        "museums": ["$", "$$"],
        "parks": ["Free", "Free", "$"],
        "hotels": ["$$", "$$$", "$$$$"],
        "restaurants": ["$", "$$", "$$$"],
        "shopping": ["$$", "$$$"],
        "entertainment": ["$$", "$$$"],
        "transit": ["Free"],
    }

    for slug, wiki_title, cat_slug, city_slug in RAW_PLACES:
        cat = cat_by_slug.get(cat_slug)
        city = city_by_slug.get(city_slug)
        if not cat or not city:
            continue

        # Hero image = first img in places/slug
        place_img_dir = BASE / f"static/images/places/{slug}"
        imgs = sorted(place_img_dir.glob("img_*"))
        if imgs:
            hero = f"/static/images/places/{slug}/{imgs[0].name}"
            gallery = [f"/static/images/places/{slug}/{i.name}" for i in imgs]
        else:
            hero = "/static/images/heroes/eiffel-tower.jpg"
            gallery = [hero]

        # Build display name from slug
        name = wiki_title.replace("_", " ").replace("%20", " ").replace("%C3%A9", "é").replace("%C3%BC", "ü").replace("%C3%AD", "í").replace("%C3%A3", "ã").replace("%C3%BA", "ú").replace("%C3%A1", "á").replace("%27", "'").replace("%C4%B1", "ı").replace("%C3%B3", "ó").replace("%C5%93", "œ").replace("%C5%8D", "ō")
        # Strip disambiguators
        if "(" in name:
            name = name.split("(")[0].strip()
        if "," in name:
            name = name.split(",")[0].strip()

        # Special name overrides
        name_overrides = {
            "eiffel-tower": "Eiffel Tower",
            "statue-of-liberty": "Statue of Liberty",
            "empire-state-building": "Empire State Building",
            "times-square": "Times Square",
            "brooklyn-bridge": "Brooklyn Bridge",
            "central-park": "Central Park",
            "one-world-trade-center": "One World Trade Center",
            "colosseum": "Colosseum",
            "roman-forum": "Roman Forum",
            "pantheon-rome": "Pantheon",
            "trevi-fountain": "Trevi Fountain",
            "vatican-city": "Vatican City",
            "sagrada-familia": "Sagrada Família",
            "park-guell": "Park Güell",
            "casa-batllo": "Casa Batlló",
            "big-ben": "Big Ben",
            "tower-bridge": "Tower Bridge",
            "london-eye": "London Eye",
            "buckingham-palace": "Buckingham Palace",
            "westminster-abbey": "Westminster Abbey",
            "tower-of-london": "Tower of London",
            "british-museum": "British Museum",
            "natural-history-museum-london": "Natural History Museum",
            "tate-modern": "Tate Modern",
            "louvre": "The Louvre",
            "notre-dame-de-paris": "Notre-Dame de Paris",
            "arc-de-triomphe": "Arc de Triomphe",
            "musee-d-orsay": "Musée d'Orsay",
            "montmartre": "Montmartre",
            "sacre-coeur": "Sacré-Cœur Basilica",
            "palace-of-versailles": "Palace of Versailles",
            "great-wall-of-china": "Great Wall of China",
            "forbidden-city": "Forbidden City",
            "temple-of-heaven": "Temple of Heaven",
            "summer-palace": "Summer Palace",
            "tiananmen-square": "Tiananmen Square",
            "burj-khalifa": "Burj Khalifa",
            "palm-jumeirah": "Palm Jumeirah",
            "dubai-mall": "The Dubai Mall",
            "burj-al-arab": "Burj Al Arab Jumeirah",
            "sydney-opera-house": "Sydney Opera House",
            "sydney-harbour-bridge": "Sydney Harbour Bridge",
            "bondi-beach": "Bondi Beach",
            "taj-mahal": "Taj Mahal",
            "gateway-of-india": "Gateway of India",
            "tokyo-tower": "Tokyo Tower",
            "tokyo-skytree": "Tokyo Skytree",
            "sensoji": "Sensō-ji",
            "shibuya-crossing": "Shibuya Crossing",
            "meiji-shrine": "Meiji Shrine",
            "fushimi-inari": "Fushimi Inari-taisha",
            "kinkakuji": "Kinkaku-ji (Golden Pavilion)",
            "ginkakuji": "Ginkaku-ji (Silver Pavilion)",
            "golden-gate-bridge": "Golden Gate Bridge",
            "alcatraz": "Alcatraz Island",
            "fishermans-wharf": "Fisherman's Wharf",
            "lombard-street": "Lombard Street",
            "golden-gate-park": "Golden Gate Park",
            "hollywood-sign": "Hollywood Sign",
            "griffith-observatory": "Griffith Observatory",
            "santa-monica-pier": "Santa Monica Pier",
            "venice-beach": "Venice Beach",
            "getty-center": "Getty Center",
            "willis-tower": "Willis Tower",
            "millennium-park": "Millennium Park",
            "navy-pier": "Navy Pier",
            "art-institute-of-chicago": "Art Institute of Chicago",
            "space-needle": "Space Needle",
            "pike-place-market": "Pike Place Market",
            "chihuly-garden": "Chihuly Garden and Glass",
            "fenway-park": "Fenway Park",
            "freedom-trail": "Freedom Trail",
            "harvard-yard": "Harvard University",
            "las-vegas-strip": "Las Vegas Strip",
            "bellagio": "Bellagio Hotel & Casino",
            "caesars-palace": "Caesars Palace",
            "venetian-resort": "The Venetian Resort",
            "golden-gate-park-2": "Yosemite National Park",
            "grand-canyon": "Grand Canyon",
            "marina-bay-sands": "Marina Bay Sands",
            "gardens-by-the-bay": "Gardens by the Bay",
            "merlion": "Merlion Park",
            "raffles-hotel": "Raffles Hotel Singapore",
            "brandenburg-gate": "Brandenburg Gate",
            "reichstag": "Reichstag Building",
            "berlin-wall": "Berlin Wall Memorial",
            "pergamon-museum": "Pergamon Museum",
            "museum-island": "Museum Island",
            "rijksmuseum": "Rijksmuseum",
            "van-gogh-museum": "Van Gogh Museum",
            "anne-frank-house": "Anne Frank House",
            "vondelpark": "Vondelpark",
            "canal-ring": "Amsterdam Canal Ring",
            "prado": "Museo del Prado",
            "royal-palace-madrid": "Royal Palace of Madrid",
            "retiro-park": "Buen Retiro Park",
            "plaza-mayor-madrid": "Plaza Mayor",
            "hagia-sophia": "Hagia Sophia",
            "blue-mosque": "Sultan Ahmed (Blue) Mosque",
            "topkapi-palace": "Topkapı Palace",
            "grand-bazaar": "Grand Bazaar",
            "acropolis": "Acropolis of Athens",
            "parthenon": "Parthenon",
            "charles-bridge": "Charles Bridge",
            "prague-castle": "Prague Castle",
            "old-town-square": "Old Town Square",
            "st-stephens-cathedral": "St. Stephen's Cathedral",
            "schonbrunn-palace": "Schönbrunn Palace",
            "belvedere-palace": "Belvedere Palace",
            "cn-tower": "CN Tower",
            "niagara-falls": "Niagara Falls",
            "stanley-park": "Stanley Park",
            "capilano-bridge": "Capilano Suspension Bridge",
            "mexico-city-cathedral": "Mexico City Metropolitan Cathedral",
            "teotihuacan": "Teotihuacan",
            "christ-the-redeemer": "Christ the Redeemer",
            "sugarloaf": "Sugarloaf Mountain",
            "copacabana": "Copacabana Beach",
            "machu-picchu": "Machu Picchu",
            "doge-palace": "Doge's Palace",
            "rialto-bridge": "Rialto Bridge",
            "st-marks-square": "Piazza San Marco",
            "santa-maria-del-fiore": "Florence Cathedral (Duomo)",
            "uffizi-gallery": "Uffizi Gallery",
            "ponte-vecchio": "Ponte Vecchio",
            "duomo-milano": "Milan Cathedral (Duomo)",
            "galleria-vittorio-emanuele": "Galleria Vittorio Emanuele II",
            "edinburgh-castle": "Edinburgh Castle",
            "royal-mile": "Royal Mile",
            "grand-place": "Grand Place",
            "atomium": "Atomium",
            "parliament-building-budapest": "Hungarian Parliament Building",
            "buda-castle": "Buda Castle",
            "chain-bridge": "Széchenyi Chain Bridge",
            "warsaw-old-town": "Warsaw Old Town",
            "market-square-krakow": "Main Square (Rynek Główny)",
        }
        name = name_overrides.get(slug, name)

        city_coord = CITY_COORDS.get(city_slug, (0, 0))
        lat = coord_jitter(city_coord[0], 0.04)
        lng = coord_jitter(city_coord[1], 0.05)

        streets = STREET_NAMES.get(city_slug, ["Main St"])
        addr = f"{random.randint(1, 999)} {random.choice(streets)}, {city.display_name}"

        rating = round(random.uniform(4.2, 4.9), 1)
        review_count = random.randint(1200, 85000)
        price = random.choice(price_by_cat.get(cat_slug, ["$"]))

        description = wiki_descriptions.get(slug, f"A popular {cat_slug[:-1] if cat_slug.endswith('s') else cat_slug} in {city.display_name}.")

        p = Place(
            slug=slug,
            name=name,
            category_id=cat.id,
            city_id=city.id,
            subtitle=f"{cat.name[:-1] if cat.name.endswith('s') else cat.name} in {city.display_name}",
            description=description,
            address=addr,
            phone=f"+{random.randint(1, 99)} {random.randint(100, 999)} {random.randint(1000, 9999)}",
            hours=random.choice(OPEN_HOURS_TEMPLATES),
            rating=rating,
            review_count=review_count,
            price_level=price,
            website=google_maps_search_url(name, city.display_name),
            hero_image=hero,
            photos_json=json.dumps(gallery),
            lat=lat,
            lng=lng,
            is_featured=(count < 12),
            is_popular=(rating >= 4.6),
        )
        db.session.add(p)
        count += 1

    # --- 2) Synthetic restaurants / hotels / shops / etc per city ---
    all_style_packs = [
        (RESTAURANT_STYLES, 3),
        (HOTEL_STYLES, 2),
        (SHOP_STYLES, 1),
        (ENTERTAINMENT_STYLES, 1),
        (CAFE_STYLES, 1),
    ]

    for city_slug, wiki_title, display, country in RAW_CITIES:
        city = city_by_slug.get(city_slug)
        if not city:
            continue
        streets = STREET_NAMES.get(city_slug, ["Main St"])
        city_coord = CITY_COORDS.get(city_slug, (0, 0))

        # Get some image sets from places in this city for synthetic entries
        city_places_imgs = []
        for slug, _, _, c_slug in RAW_PLACES:
            if c_slug == city_slug:
                d = BASE / f"static/images/places/{slug}"
                imgs = sorted(d.glob("img_*"))
                if imgs:
                    city_places_imgs.append((slug, imgs))

        for style_pack, per_city in all_style_packs:
            for idx in range(min(per_city, len(style_pack))):
                style_name, cat_slug, desc, price = random.choice(style_pack)
                cat = cat_by_slug.get(cat_slug)
                if not cat:
                    continue
                # Name like "Broadway Bistro (Manhattan)"
                name = f"{random.choice(streets).split(' ')[0]} {style_name}"
                syn_slug = f"{city_slug}-{style_name.lower().replace(' ', '-')}-{idx+1}"
                # Make unique
                while Place.query.filter_by(slug=syn_slug).first():
                    syn_slug += "-x"

                # Use images from one of the city's places
                if city_places_imgs:
                    donor_slug, donor_imgs = random.choice(city_places_imgs)
                    hero = f"/static/images/places/{donor_slug}/{donor_imgs[0].name}"
                    gallery = [f"/static/images/places/{donor_slug}/{i.name}" for i in donor_imgs[:3]]
                else:
                    hero = "/static/images/heroes/eiffel-tower.jpg"
                    gallery = [hero]

                lat = coord_jitter(city_coord[0], 0.03)
                lng = coord_jitter(city_coord[1], 0.04)

                p = Place(
                    slug=syn_slug,
                    name=name,
                    category_id=cat.id,
                    city_id=city.id,
                    subtitle=f"{style_name} in {display}",
                    description=desc,
                    address=f"{random.randint(1, 999)} {random.choice(streets)}, {display}",
                    phone=f"+{random.randint(1, 99)} {random.randint(100, 999)} {random.randint(1000, 9999)}",
                    hours=random.choice(OPEN_HOURS_TEMPLATES),
                    rating=round(random.uniform(4.0, 4.8), 1),
                    review_count=random.randint(80, 3500),
                    price_level=price,
                    website=google_maps_search_url(name, display),
                    hero_image=hero,
                    photos_json=json.dumps(gallery),
                    lat=lat,
                    lng=lng,
                    is_featured=False,
                    is_popular=random.random() > 0.6,
                )
                db.session.add(p)
                count += 1

    db.session.commit()

    # --- 3) Enrich places with parking_info and delivery_available ---
    # Shopping/large stores get parking info
    for p in Place.query.all():
        cat = Category.query.get(p.category_id)
        cat_slug = cat.slug if cat else ""
        # Parking info — stores and shopping centers, hotels, large attractions
        if cat_slug == "shopping":
            p.parking_info = random.choice([
                "Free parking lot available",
                "Paid parking garage on-site ($5/hr)",
                "Large free parking lot with 500+ spaces",
                "Validated parking available with purchase",
                "Multi-level parking garage — first 2 hours free",
            ])
            p.has_parking_lot = True
        elif cat_slug == "hotels":
            p.parking_info = random.choice([
                "Valet parking available ($30/night)",
                "Free self-parking for guests",
                "Underground parking garage ($25/day)",
                "No on-site parking — nearby public garage 0.2 mi",
            ])
            p.has_parking_lot = True
        elif cat_slug in ("attractions", "museums", "entertainment"):
            p.parking_info = random.choice([
                "Street parking available",
                "Nearby public parking garage",
                "Limited street parking — public transit recommended",
                "Free parking lot",
            ])
            p.has_parking_lot = random.random() > 0.4
        elif cat_slug == "restaurants":
            p.parking_info = random.choice([
                "Street parking available",
                "Free parking lot",
                "Valet parking available",
                "",
            ])
            p.has_parking_lot = random.random() > 0.5
            # Delivery for restaurants
            p.delivery_available = random.random() > 0.3
        elif cat_slug == "parks":
            p.parking_info = random.choice([
                "Free parking areas near main entrance",
                "Metered street parking around the perimeter",
                "Parking lots available at multiple entrances",
            ])
            p.has_parking_lot = True

    db.session.commit()
    return count


def build_cities(db, City):
    """Seed cities from RAW_CITIES with hero images."""
    city_blurbs = {
        "new-york": "The city that never sleeps - from Times Square to Central Park, discover iconic NYC.",
        "paris": "The City of Light - world-class museums, grand boulevards, and unmatched cafe culture.",
        "london": "A global capital steeped in history, with royal palaces, bustling markets, and great theatre.",
        "rome": "The Eternal City where ancient ruins stand beside bustling piazzas and world-class cuisine.",
        "tokyo": "A fascinating blend of tradition and hyper-modernity - one of the world's great cities.",
        "barcelona": "Gaudí's architectural playground on the sun-soaked Mediterranean coast.",
        "berlin": "A vibrant, creative capital with unmatched history, nightlife, and street art.",
    }

    for slug, wiki_title, display, country in RAW_CITIES:
        city_img_dir = BASE / f"static/images/cities/{slug}"
        imgs = sorted(city_img_dir.glob("img_*"))
        hero = f"/static/images/cities/{slug}/{imgs[0].name}" if imgs else "/static/images/heroes/eiffel-tower.jpg"
        coord = CITY_COORDS.get(slug, (0, 0))
        c = City(
            slug=slug,
            display_name=display,
            country=country,
            hero_image=hero,
            description=city_blurbs.get(slug, f"Explore {display} - one of {country}'s most beloved destinations."),
            lat=coord[0],
            lng=coord[1],
        )
        db.session.add(c)
    db.session.commit()


def build_categories(db, Category):
    for c in CATEGORIES:
        db.session.add(Category(
            slug=c["slug"],
            name=c["name"],
            icon=c["icon"],
            color=c["color"],
            description=c["description"],
        ))
    db.session.commit()


def seed_task_data(db, Place, Category, City, Route):
    """Seed additional places, cities, categories, and routes required by run_tasks.py."""
    import json

    # ---- Extra categories needed by tasks ----
    EXTRA_CATS = [
        {"slug": "bus-stops", "name": "Bus Stops", "icon": "directions_bus",
         "color": "#616161", "description": "Public transit bus stops."},
        {"slug": "parking", "name": "Parking", "icon": "local_parking",
         "color": "#607d8b", "description": "Parking garages and lots."},
        {"slug": "services", "name": "Services", "icon": "build",
         "color": "#795548", "description": "Locksmiths, plumbers, and local services."},
        {"slug": "health-beauty", "name": "Health & Beauty", "icon": "spa",
         "color": "#e91e63", "description": "Salons, spas, and wellness services."},
        {"slug": "fitness", "name": "Fitness & Recreation", "icon": "fitness_center",
         "color": "#ff5722", "description": "Gyms, climbing walls, and recreational facilities."},
        {"slug": "ev-charging", "name": "EV Charging", "icon": "ev_station",
         "color": "#4caf50", "description": "Electric vehicle charging stations."},
    ]
    for c in EXTRA_CATS:
        if not Category.query.filter_by(slug=c["slug"]).first():
            db.session.add(Category(
                slug=c["slug"], name=c["name"], icon=c["icon"],
                color=c["color"], description=c["description"],
            ))
    db.session.commit()

    cat_by_slug = {c.slug: c for c in Category.query.all()}

    # ---- Extra cities with state-suffixed slugs ----
    EXTRA_CITIES = [
        ("seattle-wa", "Seattle, WA", "United States", 47.6062, -122.3321),
        ("altavista-va", "Altavista, VA", "United States", 37.1113, -79.2865),
        ("chicago-il", "Chicago, IL", "United States", 41.8781, -87.6298),
        ("new-york-ny", "New York, NY", "United States", 40.7128, -74.0060),
        ("brooklyn-ny", "Brooklyn, NY", "United States", 40.6782, -73.9442),
        ("detroit-mi", "Detroit, MI", "United States", 42.3314, -83.0458),
        ("texas-city-tx", "Texas City, TX", "United States", 29.3838, -94.9027),
        ("orlando-fl", "Orlando, FL", "United States", 28.5383, -81.3792),
        ("washington-dc", "Washington, DC", "United States", 38.9072, -77.0369),
        ("boston-ma", "Boston, MA", "United States", 42.3601, -71.0589),
        ("atlanta-ga", "Atlanta, GA", "United States", 33.7490, -84.3880),
        ("pittsburgh-pa", "Pittsburgh, PA", "United States", 40.4406, -79.9959),
        ("miami-fl", "Miami, FL", "United States", 25.7617, -80.1918),
        ("denver-co", "Denver, CO", "United States", 39.7392, -104.9903),
        ("gloucester-ma", "Gloucester, MA", "United States", 42.6159, -70.6620),
        ("salem-ma", "Salem, MA", "United States", 42.5195, -70.8967),
        ("alanson-mi", "Alanson, MI", "United States", 45.4408, -84.7878),
        ("ypsilanti-mi", "Ypsilanti, MI", "United States", 42.2411, -83.6130),
        ("avon-oh", "Avon, OH", "United States", 41.4517, -82.0354),
        ("calabasas-ca", "Calabasas, CA", "United States", 34.1367, -118.6609),
        ("san-francisco-ca", "San Francisco, CA", "United States", 37.7749, -122.4194),
    ]
    for slug, display, country, lat, lng in EXTRA_CITIES:
        if not City.query.filter_by(slug=slug).first():
            db.session.add(City(
                slug=slug, display_name=display, country=country,
                hero_image="/static/images/heroes/eiffel-tower.jpg",
                description=f"Explore {display}.",
                lat=lat, lng=lng,
            ))
    db.session.commit()

    city_by_slug = {c.slug: c for c in City.query.all()}

    def _hero():
        return "/static/images/heroes/eiffel-tower.jpg"

    def _gallery():
        return json.dumps(["/static/images/heroes/eiffel-tower.jpg"])

    # ---- Helper to add a place ----
    place_counter = [0]

    def add_place(name, cat_slug, city_slug, **kwargs):
        cat = cat_by_slug.get(cat_slug)
        city = city_by_slug.get(city_slug)
        if not cat or not city:
            return None
        slug = kwargs.pop("slug", None) or f"task-{cat_slug}-{city_slug}-{place_counter[0]}"
        place_counter[0] += 1
        # Check for duplicate slug
        while Place.query.filter_by(slug=slug).first():
            slug += "-x"
        defaults = dict(
            slug=slug, name=name, category_id=cat.id, city_id=city.id,
            subtitle=kwargs.pop("subtitle", f"{cat.name} in {city.display_name}"),
            description=kwargs.pop("description", f"{name} — a popular destination."),
            address=kwargs.pop("address", f"123 Main St, {city.display_name}"),
            phone=kwargs.pop("phone", "+1 555 1234"),
            hours=kwargs.pop("hours", "Mon-Sun: 9:00 AM - 6:00 PM"),
            rating=kwargs.pop("rating", 4.5),
            review_count=kwargs.pop("review_count", 500),
            price_level=kwargs.pop("price_level", "$$"),
            website=kwargs.pop("website", google_maps_search_url(name, city.display_name)),
            hero_image=_hero(), photos_json=_gallery(),
            lat=kwargs.pop("lat", city.lat + random.uniform(-0.02, 0.02)),
            lng=kwargs.pop("lng", city.lng + random.uniform(-0.02, 0.02)),
        )
        defaults.update(kwargs)
        p = Place(**defaults)
        db.session.add(p)
        return p

    random.seed(99)

    # ================================================================
    # Task 0: 5+ beauty salons rating>4.8 in Seattle-WA
    # ================================================================
    salon_names = [
        "Luxe Beauty Salon", "Radiance Beauty Studio", "Bella Salon & Spa",
        "The Beauty Bar Seattle", "Emerald City Beauty Salon",
        "Pine Street Beauty Lounge", "Capitol Hill Salon",
    ]
    for sn in salon_names:
        add_place(sn, "health-beauty", "seattle-wa",
                  subcategory="Beauty Salon", rating=round(random.uniform(4.86, 4.95), 2),
                  address=f"{random.randint(100, 999)} Pike St, Seattle, WA",
                  tags_json=json.dumps(["beauty", "salon", "seattle", "hair", "spa"]))

    # ================================================================
    # Task 1: Bus stop Main & Amherst in Altavista VA
    # ================================================================
    add_place("Main St & Amherst St Bus Stop", "bus-stops", "altavista-va",
              address="Main St & Amherst St, Altavista, VA",
              description="Bus stop at the intersection of Main St and Amherst St in Altavista.",
              tags_json=json.dumps(["bus", "stop", "main", "amherst", "altavista"]))
    add_place("Court St Bus Stop", "bus-stops", "altavista-va",
              address="100 Court St, Altavista, VA",
              tags_json=json.dumps(["bus", "stop", "altavista"]))

    # ================================================================
    # Task 2: Apple Stores near 90028 (Hollywood, LA)
    # ================================================================
    for i, loc in enumerate([
        ("Apple The Grove", "189 The Grove Dr, Los Angeles, CA 90036"),
        ("Apple Tower Theater", "550 S Broadway, Los Angeles, CA 90013"),
        ("Apple Third Street Promenade", "1415 3rd St Promenade, Santa Monica, CA 90401"),
        ("Apple Century City", "10250 Santa Monica Blvd, Los Angeles, CA 90067"),
    ]):
        add_place(loc[0], "shopping", "los-angeles",
                  chain_brand="Apple", address=loc[1],
                  description=f"Apple Store — shop for iPhone, Mac, iPad, and more.",
                  tags_json=json.dumps(["apple", "store", "electronics", "iphone", "mac"]))

    # ================================================================
    # Task 6: Uniqlo in Chicago
    # ================================================================
    for i, loc in enumerate([
        ("Uniqlo Michigan Ave", "830 N Michigan Ave, Chicago, IL"),
        ("Uniqlo State Street", "40 S State St, Chicago, IL"),
        ("Uniqlo Lincoln Park", "2526 N Clark St, Chicago, IL"),
        ("Uniqlo Wicker Park", "1569 N Milwaukee Ave, Chicago, IL"),
    ]):
        add_place(loc[0], "shopping", "chicago",
                  chain_brand="Uniqlo", address=loc[1],
                  description="Uniqlo — casual wear, basics, and quality everyday clothing.",
                  tags_json=json.dumps(["uniqlo", "clothing", "fashion", "chicago"]))

    # ================================================================
    # Task 8: Climbing gym near 90028 (Hollywood)
    # ================================================================
    add_place("Hollywood Boulders Climbing Gym", "fitness", "los-angeles",
              zip_code="90028", address="6600 Sunset Blvd, Hollywood, CA 90028",
              description="Indoor rock climbing and bouldering in the heart of Hollywood.",
              tags_json=json.dumps(["climbing", "bouldering", "gym", "hollywood", "90028"]))
    add_place("Sender One Climbing Hollywood", "fitness", "los-angeles",
              zip_code="90028", address="6565 Santa Monica Blvd, Hollywood, CA 90028",
              description="Premier climbing gym in Hollywood with top-rope, lead, and bouldering.",
              tags_json=json.dumps(["climbing", "bouldering", "gym", "hollywood", "90028"]))
    add_place("Cliffs of Hollywood", "fitness", "los-angeles",
              zip_code="90028", address="6201 Hollywood Blvd, Hollywood, CA 90028",
              description="Climbing facility near Hollywood with courses for all levels.",
              tags_json=json.dumps(["climbing", "gym", "hollywood", "90028"]))

    # ================================================================
    # Task 11: WA stores with parking
    # ================================================================
    for sn in ["Kids & Maternity Outlet", "Little Ones Maternity & Baby", "BabyLand WA Store"]:
        add_place(sn, "shopping", "seattle-wa",
                  state="WA", has_parking_lot=True,
                  description=f"{sn} — kids, maternity, and baby essentials with on-site parking.",
                  tags_json=json.dumps(["kids", "maternity", "baby", "store", "washington", "parking"]))

    # ================================================================
    # Task 12: 5+ burger places near 44012 (Avon, OH)
    # ================================================================
    burger_names = [
        "Burger Barn 44012", "Avon Burger House", "Flame Burger Grill",
        "Burger Nation Avon", "Classic Burger Joint Avon", "Big Burger Co",
    ]
    for bn in burger_names:
        add_place(bn, "restaurants", "avon-oh",
                  zip_code="44012", subcategory="Burger Restaurant",
                  address=f"{random.randint(100, 999)} Detroit Rd, Avon, OH 44012",
                  description=f"{bn} — juicy burgers, fries, and shakes.",
                  rating=round(random.uniform(4.0, 4.8), 1),
                  tags_json=json.dumps(["burger", "burgers", "restaurant", "44012", "avon"]))

    # ================================================================
    # Task 13: Parking in Gloucester MA
    # ================================================================
    for pn in ["Gloucester Parking Lot A", "Harbor Parking Gloucester", "Main St Garage Gloucester"]:
        add_place(pn, "parking", "gloucester-ma",
                  address=f"Gloucester, MA", is_24h=False,
                  description=f"{pn} — convenient parking in Gloucester.",
                  tags_json=json.dumps(["parking", "gloucester", "lot"]))

    # ================================================================
    # Task 14: Motorcycle parking (near Radio City)
    # ================================================================
    for mn in ["Midtown Motorcycle Parking W 50th", "6th Ave Motorcycle Garage",
               "Rockefeller Center Motorcycle Lot"]:
        add_place(mn, "parking", "new-york",
                  motorcycle_parking=True,
                  address="W 50th St, New York, NY 10020",
                  description=f"{mn} — motorcycle and scooter parking near Radio City Music Hall.",
                  nearest_landmark="Radio City Music Hall",
                  tags_json=json.dumps(["motorcycle", "parking", "radio city", "midtown"]))

    # ================================================================
    # Task 16: EV charging near Smithsonian in Washington DC
    # ================================================================
    for en in ["Smithsonian EV Charging Station", "National Mall EV Lot",
               "DC EV Charging Hub Independence Ave"]:
        add_place(en, "ev-charging", "washington-dc",
                  ev_charging=True,
                  address="Independence Ave SW, Washington, DC 20560",
                  description=f"{en} — EV charging parking near the Smithsonian museums.",
                  nearest_landmark="Smithsonian Institution",
                  tags_json=json.dumps(["ev", "charging", "parking", "smithsonian", "washington"]))

    # ================================================================
    # Task 19: Hilton near Pittsburgh Airport
    # ================================================================
    add_place("Hilton Pittsburgh Airport", "hotels", "pittsburgh-pa",
              chain_brand="Hilton",
              address="1000 Park Lane Dr, Pittsburgh, PA 15275",
              description="Hilton Pittsburgh Airport — full-service hotel near PIT.",
              tags_json=json.dumps(["hilton", "hotel", "pittsburgh", "airport"]),
              lat=40.4959, lng=-80.2378)
    add_place("Giant Eagle Moon Township", "shopping", "pittsburgh-pa",
              address="900 Beaver Grade Rd, Moon Township, PA 15108",
              description="Giant Eagle supermarket in Moon Township.",
              tags_json=json.dumps(["giant eagle", "supermarket", "grocery", "moon township"]),
              lat=40.5064, lng=-80.2155)

    # ================================================================
    # Task 20: Tesla Destination Charger near Air & Space Museum (DC)
    # ================================================================
    add_place("Tesla Destination Charger National Mall", "ev-charging", "washington-dc",
              chain_brand="Tesla", ev_charging=True,
              address="600 Independence Ave SW, Washington, DC 20560",
              description="Tesla Destination Charger near the National Air and Space Museum.",
              tags_json=json.dumps(["tesla", "charger", "destination", "ev", "washington", "air", "space"]))

    # ================================================================
    # Task 22: Best Buy near 33139 (Miami Beach)
    # ================================================================
    add_place("Best Buy Miami Beach", "shopping", "miami-fl",
              chain_brand="Best Buy", zip_code="33139",
              address="1205 Washington Ave, Miami Beach, FL 33139",
              description="Best Buy electronics store in Miami Beach.",
              tags_json=json.dumps(["best buy", "electronics", "33139", "miami"]))

    # ================================================================
    # Task 27: Target stores in Atlanta
    # ================================================================
    for tn in ["Target Midtown Atlanta", "Target Buckhead", "Target Atlantic Station"]:
        add_place(tn, "shopping", "atlanta-ga",
                  chain_brand="Target",
                  address=f"Atlanta, GA 30309",
                  description=f"{tn} — your one-stop shop for everything.",
                  tags_json=json.dumps(["target", "store", "atlanta", "shopping"]))

    # ================================================================
    # Task 30: 24h parking near Brooklyn Bridge
    # ================================================================
    for pn in ["Brooklyn Bridge 24H Parking", "DUMBO Parking Garage 24H",
               "Cadman Plaza 24H Lot"]:
        add_place(pn, "parking", "brooklyn-ny",
                  is_24h=True,
                  address="Brooklyn, NY 11201",
                  description=f"{pn} — open 24 hours near Brooklyn Bridge.",
                  nearest_landmark="Brooklyn Bridge",
                  tags_json=json.dumps(["parking", "24h", "brooklyn", "bridge"]))

    # ================================================================
    # Task 32: Plumbers in Orlando not 24h
    # ================================================================
    for pn in ["Orlando Expert Plumbing", "Sunshine Plumbers Orlando",
               "Central FL Plumbing Co"]:
        add_place(pn, "services", "orlando-fl",
                  is_24h=False, subcategory="Plumber",
                  address="Orlando, FL 32801",
                  description=f"{pn} — licensed plumbing services in Orlando.",
                  tags_json=json.dumps(["plumber", "plumbing", "orlando", "services"]))

    # ================================================================
    # Task 34: Hiking trails near 80202 (Denver)
    # ================================================================
    for tn in ["Cherry Creek Trail", "Confluence Park Trail", "Platte River Trail Denver"]:
        add_place(tn, "parks", "denver-co",
                  zip_code="80202",
                  address="Denver, CO 80202",
                  description=f"{tn} — scenic hiking and walking trail in downtown Denver.",
                  subcategory="Trail",
                  tags_json=json.dumps(["hiking", "trail", "80202", "denver", "walk"]))

    # ================================================================
    # Task 36: Pizza near 30309 (Atlanta)
    # ================================================================
    pizza_names = [
        "Antico Pizza Napoletana", "Fellini's Pizza Atlanta",
        "Ammazza Pizza", "Junior's Pizza 30309", "Midtown Pizza Kitchen",
    ]
    for pn in pizza_names:
        add_place(pn, "restaurants", "atlanta-ga",
                  zip_code="30309", subcategory="Pizza",
                  address=f"Atlanta, GA 30309",
                  description=f"{pn} — authentic pizza in Atlanta.",
                  tags_json=json.dumps(["pizza", "30309", "atlanta", "restaurant"]))

    # ================================================================
    # Task 37: Parking in Salem MA
    # ================================================================
    for pn in ["Salem Parking Garage", "Derby St Lot Salem", "Museum Place Parking Salem"]:
        add_place(pn, "parking", "salem-ma",
                  address="Salem, MA 01970",
                  description=f"{pn} — parking in historic Salem, MA.",
                  tags_json=json.dumps(["parking", "salem", "lot"]))

    # ================================================================
    # Task 38: Bicycle parking near Empire State Building
    # ================================================================
    for bn in ["Empire State Bicycle Parking", "34th St Bike Rack Station",
               "Herald Square Bicycle Corral"]:
        add_place(bn, "parking", "new-york",
                  bicycle_parking=True,
                  address="350 5th Ave, New York, NY 10118",
                  nearest_landmark="Empire State Building",
                  description=f"{bn} — bicycle parking near the Empire State Building.",
                  tags_json=json.dumps(["bicycle", "parking", "empire state", "bike"]))

    # ================================================================
    # Task 40: Boston lobster / seafood restaurants rating>=4.6
    # ================================================================
    seafood_names = [
        "Legal Sea Foods Boston", "Neptune Oyster",
        "Island Creek Oyster Bar", "Row 34 Lobster Bar",
    ]
    for sn in seafood_names:
        add_place(sn, "restaurants", "boston-ma",
                  subcategory="Seafood",
                  rating=round(random.uniform(4.6, 4.9), 1),
                  address="Boston, MA 02101",
                  description=f"{sn} — fresh lobster, oysters, and New England seafood.",
                  tags_json=json.dumps(["lobster", "seafood", "boston", "restaurant"]))

    # ================================================================
    # Task 5: Parking near Thalia Hall Chicago — non-24h, in chicago-il
    # ================================================================
    for pn in ["Thalia Hall Lot", "Pilsen Parking Garage", "18th St Parking Chicago"]:
        add_place(pn, "parking", "chicago-il",
                  is_24h=False,
                  address="1807 S Allport St, Chicago, IL 60608",
                  description=f"{pn} — non-24h parking near Thalia Hall, Pilsen.",
                  tags_json=json.dumps(["parking", "thalia", "hall", "chicago", "pilsen"]))

    # ================================================================
    # Task 15: Daytime-only parking nearest MSG — non-24h in new-york-ny
    # ================================================================
    for pn in ["MSG Daytime Parking West 33rd", "Penn Station Parking Lot",
               "Herald Sq Parking Garage"]:
        add_place(pn, "parking", "new-york-ny",
                  is_24h=False,
                  address="W 33rd St, New York, NY 10001",
                  nearest_landmark="Madison Square Garden",
                  description=f"{pn} — daytime parking near Madison Square Garden.",
                  tags_json=json.dumps(["parking", "daytime", "madison square garden", "msg"]))

    # ================================================================
    # Task 17: non-24h services in Texas City TX
    # ================================================================
    for sn in ["Texas City Lock & Key", "Gulf Coast Locksmith",
               "Bay Area Locksmith TX"]:
        add_place(sn, "services", "texas-city-tx",
                  is_24h=False, subcategory="Locksmith",
                  address="Texas City, TX 77590",
                  description=f"{sn} — locksmith services in Texas City.",
                  tags_json=json.dumps(["locksmith", "texas city", "lock", "key"]))

    # ================================================================
    # Task 25: non-24h parking near Fox Theater in Detroit
    # ================================================================
    for pn in ["Fox Theater Parking Deck", "Woodward Ave Garage Detroit",
               "Grand Circus Parking Lot"]:
        add_place(pn, "parking", "detroit-mi",
                  is_24h=False,
                  address="2211 Woodward Ave, Detroit, MI 48201",
                  nearest_landmark="Fox Theatre Detroit",
                  description=f"{pn} — parking near the Fox Theatre, closes at midnight.",
                  tags_json=json.dumps(["parking", "fox", "theater", "detroit"]))

    db.session.commit()

    # ================================================================
    # ROUTES (for directions tests)
    # ================================================================
    ROUTES = [
        {
            "origin_query": "Central Park Zoo",
            "destination_query": "Broadway Theater",
            "origin_name": "Central Park Zoo",
            "destination_name": "Broadway Theater",
            "mode": "walking",
            "distance": "1.8 km",
            "distance_km": 1.8,
            "duration": "22 min",
            "duration_min": 22,
            "summary": "Central Park Zoo to Broadway Theater via 5th Ave",
            "origin_address": "Central Park Zoo, 64th St, New York, NY",
            "destination_address": "Broadway Theater District, New York, NY",
            "steps": [
                {"instruction": "Head south on East Dr toward 5th Ave", "distance": "0.3 km"},
                {"instruction": "Turn right onto 5th Ave", "distance": "0.5 km"},
                {"instruction": "Continue south on 5th Ave past Central Park Zoo", "distance": "0.4 km"},
                {"instruction": "Turn right onto W 50th St", "distance": "0.3 km"},
                {"instruction": "Turn left onto Broadway", "distance": "0.2 km"},
                {"instruction": "Arrive at Broadway Theater District", "distance": "0.1 km"},
            ],
        },
        {
            "origin_query": "Boston Logan Airport",
            "destination_query": "North Station",
            "origin_name": "Boston Logan International Airport",
            "destination_name": "North Station",
            "mode": "driving",
            "distance": "5.6 km",
            "distance_km": 5.6,
            "duration": "15 min",
            "duration_min": 15,
            "summary": "Logan Airport to North Station via I-93 S",
            "origin_address": "Boston Logan Airport, East Boston, MA",
            "destination_address": "North Station, Causeway St, Boston, MA",
            "steps": [
                {"instruction": "Head west on Airport Rd toward I-90 W", "distance": "0.8 km"},
                {"instruction": "Take I-90 W / Ted Williams Tunnel", "distance": "2.0 km"},
                {"instruction": "Merge onto I-93 N", "distance": "1.5 km"},
                {"instruction": "Take exit toward Causeway St / North Station", "distance": "0.8 km"},
                {"instruction": "Turn right onto Causeway St", "distance": "0.3 km"},
                {"instruction": "Arrive at North Station", "distance": "0.2 km"},
            ],
        },
        {
            "origin_query": "Gloucester",
            "destination_query": "North Plymouth",
            "origin_name": "Gloucester",
            "destination_name": "North Plymouth",
            "mode": "driving",
            "distance": "105 km",
            "distance_km": 105.0,
            "duration": "1 hr 20 min",
            "duration_min": 80,
            "summary": "Gloucester to North Plymouth via MA-3 S",
            "origin_address": "Gloucester, MA",
            "destination_address": "North Plymouth, MA",
            "steps": [
                {"instruction": "Head west on MA-128 S", "distance": "25 km"},
                {"instruction": "Merge onto I-95 S / MA-128 S", "distance": "20 km"},
                {"instruction": "Take MA-3 S toward Plymouth", "distance": "45 km"},
                {"instruction": "Take exit 8 toward North Plymouth", "distance": "10 km"},
                {"instruction": "Turn left onto Court St", "distance": "3 km"},
                {"instruction": "Arrive at North Plymouth", "distance": "2 km"},
            ],
        },
        {
            "origin_query": "Chicago",
            "destination_query": "Los Angeles",
            "origin_name": "Chicago",
            "destination_name": "Los Angeles",
            "mode": "driving",
            "distance": "2,800 km",
            "distance_km": 2800.0,
            "duration": "26 hr",
            "duration_min": 1560,
            "summary": "Chicago to Los Angeles via I-55 S and I-40 W",
            "origin_address": "Chicago, IL",
            "destination_address": "Los Angeles, CA",
            "steps": [
                {"instruction": "Head south on I-55 S from Chicago", "distance": "480 km"},
                {"instruction": "Continue onto I-44 W through Missouri", "distance": "420 km"},
                {"instruction": "Merge onto I-40 W through Oklahoma and Texas", "distance": "950 km"},
                {"instruction": "Continue on I-40 W through New Mexico and Arizona", "distance": "720 km"},
                {"instruction": "Take I-15 S to I-10 W toward Los Angeles", "distance": "180 km"},
                {"instruction": "Arrive in Los Angeles, CA", "distance": "50 km"},
            ],
        },
        {
            "origin_query": "Hilton Pittsburgh Airport",
            "destination_query": "Giant Eagle Moon Township",
            "origin_name": "Hilton Pittsburgh Airport",
            "destination_name": "Giant Eagle Moon Township",
            "mode": "walking",
            "distance": "2.1 km",
            "distance_km": 2.1,
            "duration": "26 min",
            "duration_min": 26,
            "summary": "Hilton Pittsburgh Airport to Giant Eagle Moon Township via Beaver Grade Rd",
            "origin_address": "1000 Park Lane Dr, Pittsburgh, PA",
            "destination_address": "900 Beaver Grade Rd, Moon Township, PA",
            "steps": [
                {"instruction": "Head east on Park Lane Dr", "distance": "0.3 km"},
                {"instruction": "Turn left onto Beaver Grade Rd", "distance": "1.2 km"},
                {"instruction": "Continue on Beaver Grade Rd past University Blvd", "distance": "0.4 km"},
                {"instruction": "Arrive at Giant Eagle Moon Township on your right", "distance": "0.2 km"},
            ],
        },
        {
            "origin_query": "Metropolitan Museum of Art",
            "destination_query": "Times Square",
            "origin_name": "Metropolitan Museum of Art",
            "destination_name": "Times Square",
            "mode": "walking",
            "distance": "3.2 km",
            "distance_km": 3.2,
            "duration": "40 min",
            "duration_min": 40,
            "summary": "Metropolitan Museum of Art to Times Square via 5th Ave",
            "origin_address": "1000 5th Ave, New York, NY",
            "destination_address": "Times Square, Manhattan, NY",
            "steps": [
                {"instruction": "Head south on 5th Ave from the Metropolitan Museum", "distance": "0.8 km"},
                {"instruction": "Continue south on 5th Ave past Rockefeller Center", "distance": "1.0 km"},
                {"instruction": "Turn right onto W 47th St", "distance": "0.6 km"},
                {"instruction": "Turn left onto 7th Ave / Broadway", "distance": "0.5 km"},
                {"instruction": "Arrive at Times Square", "distance": "0.3 km"},
            ],
        },
        {
            "origin_query": "San Francisco International Airport",
            "destination_query": "Union Square",
            "origin_name": "San Francisco International Airport",
            "destination_name": "Union Square San Francisco",
            "mode": "driving",
            "distance": "21 km",
            "distance_km": 21.0,
            "duration": "25 min",
            "duration_min": 25,
            "summary": "SFO to Union Square via US-101 N",
            "origin_address": "San Francisco International Airport, San Francisco, CA",
            "destination_address": "Union Square, San Francisco, CA",
            "steps": [
                {"instruction": "Exit SFO via N McDonnell Rd toward US-101 N", "distance": "2.0 km"},
                {"instruction": "Merge onto US-101 N", "distance": "12.0 km"},
                {"instruction": "Take exit toward I-80 E / 4th St", "distance": "3.0 km"},
                {"instruction": "Turn left onto 4th St, then right onto Market St", "distance": "2.5 km"},
                {"instruction": "Turn right onto Powell St toward Union Square", "distance": "1.0 km"},
                {"instruction": "Arrive at Union Square, San Francisco", "distance": "0.5 km"},
            ],
        },
        {
            "origin_query": "Salem",
            "destination_query": "Marblehead",
            "origin_name": "Salem",
            "destination_name": "Marblehead",
            "mode": "driving",
            "distance": "6.4 km",
            "distance_km": 6.4,
            "duration": "12 min",
            "duration_min": 12,
            "summary": "Salem to Marblehead via MA-114 E",
            "origin_address": "Salem, MA",
            "destination_address": "Marblehead, MA",
            "steps": [
                {"instruction": "Head east on MA-114 E from Salem", "distance": "3.0 km"},
                {"instruction": "Continue on Lafayette St toward Marblehead", "distance": "2.0 km"},
                {"instruction": "Turn right onto Pleasant St", "distance": "1.0 km"},
                {"instruction": "Arrive in Marblehead center", "distance": "0.4 km"},
            ],
        },
        {
            "origin_query": "Miami",
            "destination_query": "New Orleans",
            "origin_name": "Miami",
            "destination_name": "New Orleans",
            "mode": "driving",
            "distance": "1,320 km",
            "distance_km": 1320.0,
            "duration": "12 hr 30 min",
            "duration_min": 750,
            "summary": "Miami to New Orleans via I-75 N and I-10 W",
            "origin_address": "Miami, FL",
            "destination_address": "New Orleans, LA",
            "steps": [
                {"instruction": "Head north on I-95 N from Miami", "distance": "15 km"},
                {"instruction": "Take Florida's Turnpike N / I-75 N toward Naples", "distance": "250 km"},
                {"instruction": "Merge onto I-75 N through central Florida", "distance": "400 km"},
                {"instruction": "Take I-10 W through Tallahassee and the Florida Panhandle", "distance": "450 km"},
                {"instruction": "Continue on I-10 W through Alabama and Mississippi", "distance": "180 km"},
                {"instruction": "Arrive in New Orleans, LA", "distance": "25 km"},
            ],
        },
    ]

    for r in ROUTES:
        db.session.add(Route(
            origin_query=r["origin_query"],
            destination_query=r["destination_query"],
            origin_name=r["origin_name"],
            destination_name=r["destination_name"],
            mode=r["mode"],
            distance=r["distance"],
            distance_km=r["distance_km"],
            duration=r["duration"],
            duration_min=r["duration_min"],
            summary=r["summary"],
            origin_address=r.get("origin_address", ""),
            destination_address=r.get("destination_address", ""),
            steps_json=json.dumps(r["steps"]),
        ))

    db.session.commit()
    print(f"Seeded {place_counter[0]} task-specific places and {len(ROUTES)} routes.")


# ============================================================================
# Expansion pass: bring catalog up to volume needed for realistic browsing.
# Gates are coarse count thresholds so the WHOLE function early-returns
# on second invocation, preserving byte-identical reset.
# ============================================================================

EXPAND_CITIES = [
    # (slug, display, country, lat, lng)
    # --- USA breadth ---
    ("houston-tx", "Houston, TX", "United States", 29.7604, -95.3698),
    ("dallas-tx", "Dallas, TX", "United States", 32.7767, -96.7970),
    ("austin-tx", "Austin, TX", "United States", 30.2672, -97.7431),
    ("san-antonio-tx", "San Antonio, TX", "United States", 29.4241, -98.4936),
    ("fort-worth-tx", "Fort Worth, TX", "United States", 32.7555, -97.3308),
    ("el-paso-tx", "El Paso, TX", "United States", 31.7619, -106.4850),
    ("phoenix-az", "Phoenix, AZ", "United States", 33.4484, -112.0740),
    ("tucson-az", "Tucson, AZ", "United States", 32.2226, -110.9747),
    ("mesa-az", "Mesa, AZ", "United States", 33.4152, -111.8315),
    ("san-diego-ca", "San Diego, CA", "United States", 32.7157, -117.1611),
    ("san-jose-ca", "San Jose, CA", "United States", 37.3382, -121.8863),
    ("sacramento-ca", "Sacramento, CA", "United States", 38.5816, -121.4944),
    ("fresno-ca", "Fresno, CA", "United States", 36.7378, -119.7871),
    ("long-beach-ca", "Long Beach, CA", "United States", 33.7701, -118.1937),
    ("oakland-ca", "Oakland, CA", "United States", 37.8044, -122.2712),
    ("bakersfield-ca", "Bakersfield, CA", "United States", 35.3733, -119.0187),
    ("portland-or", "Portland, OR", "United States", 45.5152, -122.6784),
    ("eugene-or", "Eugene, OR", "United States", 44.0521, -123.0868),
    ("salt-lake-city-ut", "Salt Lake City, UT", "United States", 40.7608, -111.8910),
    ("las-vegas-nv", "Las Vegas, NV", "United States", 36.1699, -115.1398),
    ("reno-nv", "Reno, NV", "United States", 39.5296, -119.8138),
    ("boise-id", "Boise, ID", "United States", 43.6150, -116.2023),
    ("colorado-springs-co", "Colorado Springs, CO", "United States", 38.8339, -104.8214),
    ("boulder-co", "Boulder, CO", "United States", 40.0150, -105.2705),
    ("albuquerque-nm", "Albuquerque, NM", "United States", 35.0844, -106.6504),
    ("santa-fe-nm", "Santa Fe, NM", "United States", 35.6870, -105.9378),
    ("minneapolis-mn", "Minneapolis, MN", "United States", 44.9778, -93.2650),
    ("saint-paul-mn", "St. Paul, MN", "United States", 44.9537, -93.0900),
    ("milwaukee-wi", "Milwaukee, WI", "United States", 43.0389, -87.9065),
    ("madison-wi", "Madison, WI", "United States", 43.0731, -89.4012),
    ("des-moines-ia", "Des Moines, IA", "United States", 41.5868, -93.6250),
    ("omaha-ne", "Omaha, NE", "United States", 41.2565, -95.9345),
    ("lincoln-ne", "Lincoln, NE", "United States", 40.8136, -96.7026),
    ("kansas-city-mo", "Kansas City, MO", "United States", 39.0997, -94.5786),
    ("saint-louis-mo", "St. Louis, MO", "United States", 38.6270, -90.1994),
    ("oklahoma-city-ok", "Oklahoma City, OK", "United States", 35.4676, -97.5164),
    ("tulsa-ok", "Tulsa, OK", "United States", 36.1540, -95.9928),
    ("little-rock-ar", "Little Rock, AR", "United States", 34.7465, -92.2896),
    ("new-orleans-la", "New Orleans, LA", "United States", 29.9511, -90.0715),
    ("baton-rouge-la", "Baton Rouge, LA", "United States", 30.4515, -91.1871),
    ("jackson-ms", "Jackson, MS", "United States", 32.2988, -90.1848),
    ("birmingham-al", "Birmingham, AL", "United States", 33.5186, -86.8104),
    ("montgomery-al", "Montgomery, AL", "United States", 32.3668, -86.3000),
    ("mobile-al", "Mobile, AL", "United States", 30.6954, -88.0399),
    ("nashville-tn", "Nashville, TN", "United States", 36.1627, -86.7816),
    ("memphis-tn", "Memphis, TN", "United States", 35.1495, -90.0490),
    ("knoxville-tn", "Knoxville, TN", "United States", 35.9606, -83.9207),
    ("chattanooga-tn", "Chattanooga, TN", "United States", 35.0456, -85.3097),
    ("jacksonville-fl", "Jacksonville, FL", "United States", 30.3322, -81.6557),
    ("tampa-fl", "Tampa, FL", "United States", 27.9506, -82.4572),
    ("miami-beach-fl", "Miami Beach, FL", "United States", 25.7907, -80.1300),
    ("tallahassee-fl", "Tallahassee, FL", "United States", 30.4383, -84.2807),
    ("fort-lauderdale-fl", "Fort Lauderdale, FL", "United States", 26.1224, -80.1373),
    ("savannah-ga", "Savannah, GA", "United States", 32.0809, -81.0912),
    ("charleston-sc", "Charleston, SC", "United States", 32.7765, -79.9311),
    ("columbia-sc", "Columbia, SC", "United States", 34.0007, -81.0348),
    ("raleigh-nc", "Raleigh, NC", "United States", 35.7796, -78.6382),
    ("charlotte-nc", "Charlotte, NC", "United States", 35.2271, -80.8431),
    ("asheville-nc", "Asheville, NC", "United States", 35.5951, -82.5515),
    ("richmond-va", "Richmond, VA", "United States", 37.5407, -77.4360),
    ("virginia-beach-va", "Virginia Beach, VA", "United States", 36.8529, -75.9780),
    ("norfolk-va", "Norfolk, VA", "United States", 36.8508, -76.2859),
    ("annapolis-md", "Annapolis, MD", "United States", 38.9784, -76.4922),
    ("baltimore-md", "Baltimore, MD", "United States", 39.2904, -76.6122),
    ("philadelphia-pa", "Philadelphia, PA", "United States", 39.9526, -75.1652),
    ("harrisburg-pa", "Harrisburg, PA", "United States", 40.2732, -76.8867),
    ("buffalo-ny", "Buffalo, NY", "United States", 42.8864, -78.8784),
    ("albany-ny", "Albany, NY", "United States", 42.6526, -73.7562),
    ("rochester-ny", "Rochester, NY", "United States", 43.1566, -77.6088),
    ("syracuse-ny", "Syracuse, NY", "United States", 43.0481, -76.1474),
    ("hartford-ct", "Hartford, CT", "United States", 41.7658, -72.6734),
    ("new-haven-ct", "New Haven, CT", "United States", 41.3083, -72.9279),
    ("providence-ri", "Providence, RI", "United States", 41.8240, -71.4128),
    ("manchester-nh", "Manchester, NH", "United States", 42.9956, -71.4548),
    ("portland-me", "Portland, ME", "United States", 43.6591, -70.2568),
    ("burlington-vt", "Burlington, VT", "United States", 44.4759, -73.2121),
    ("cleveland-oh", "Cleveland, OH", "United States", 41.4993, -81.6944),
    ("cincinnati-oh", "Cincinnati, OH", "United States", 39.1031, -84.5120),
    ("columbus-oh", "Columbus, OH", "United States", 39.9612, -82.9988),
    ("indianapolis-in", "Indianapolis, IN", "United States", 39.7684, -86.1581),
    ("grand-rapids-mi", "Grand Rapids, MI", "United States", 42.9634, -85.6681),
    ("ann-arbor-mi", "Ann Arbor, MI", "United States", 42.2808, -83.7430),
    ("anchorage-ak", "Anchorage, AK", "United States", 61.2181, -149.9003),
    ("honolulu-hi", "Honolulu, HI", "United States", 21.3069, -157.8583),
    ("juneau-ak", "Juneau, AK", "United States", 58.3019, -134.4197),
    # --- World breadth ---
    ("bangkok", "Bangkok", "Thailand", 13.7563, 100.5018),
    ("hanoi", "Hanoi", "Vietnam", 21.0285, 105.8542),
    ("ho-chi-minh", "Ho Chi Minh City", "Vietnam", 10.8231, 106.6297),
    ("kuala-lumpur", "Kuala Lumpur", "Malaysia", 3.1390, 101.6869),
    ("jakarta", "Jakarta", "Indonesia", -6.2088, 106.8456),
    ("manila", "Manila", "Philippines", 14.5995, 120.9842),
    ("seoul", "Seoul", "South Korea", 37.5665, 126.9780),
    ("busan", "Busan", "South Korea", 35.1796, 129.0756),
    ("osaka", "Osaka", "Japan", 34.6937, 135.5023),
    ("hong-kong", "Hong Kong", "Hong Kong", 22.3193, 114.1694),
    ("taipei", "Taipei", "Taiwan", 25.0330, 121.5654),
    ("auckland", "Auckland", "New Zealand", -36.8485, 174.7633),
    ("wellington", "Wellington", "New Zealand", -41.2865, 174.7762),
    ("melbourne", "Melbourne", "Australia", -37.8136, 144.9631),
    ("brisbane", "Brisbane", "Australia", -27.4698, 153.0251),
    ("perth", "Perth", "Australia", -31.9505, 115.8605),
    ("cape-town", "Cape Town", "South Africa", -33.9249, 18.4241),
    ("johannesburg", "Johannesburg", "South Africa", -26.2041, 28.0473),
    ("marrakech", "Marrakech", "Morocco", 31.6295, -7.9811),
    ("cairo", "Cairo", "Egypt", 30.0444, 31.2357),
    ("tel-aviv", "Tel Aviv", "Israel", 32.0853, 34.7818),
    ("doha", "Doha", "Qatar", 25.2854, 51.5310),
    ("abu-dhabi", "Abu Dhabi", "United Arab Emirates", 24.4539, 54.3773),
    ("riyadh", "Riyadh", "Saudi Arabia", 24.7136, 46.6753),
    ("delhi", "Delhi", "India", 28.6139, 77.2090),
    ("bangalore", "Bangalore", "India", 12.9716, 77.5946),
    ("chennai", "Chennai", "India", 13.0827, 80.2707),
    ("kolkata", "Kolkata", "India", 22.5726, 88.3639),
    ("kathmandu", "Kathmandu", "Nepal", 27.7172, 85.3240),
    ("colombo", "Colombo", "Sri Lanka", 6.9271, 79.8612),
    ("buenos-aires", "Buenos Aires", "Argentina", -34.6037, -58.3816),
    ("santiago", "Santiago", "Chile", -33.4489, -70.6693),
    ("bogota", "Bogotá", "Colombia", 4.7110, -74.0721),
    ("quito", "Quito", "Ecuador", -0.1807, -78.4678),
    ("havana", "Havana", "Cuba", 23.1136, -82.3666),
    ("san-juan", "San Juan", "Puerto Rico", 18.4655, -66.1057),
    ("montreal", "Montreal", "Canada", 45.5017, -73.5673),
    ("calgary", "Calgary", "Canada", 51.0447, -114.0719),
    ("ottawa", "Ottawa", "Canada", 45.4215, -75.6972),
    ("quebec-city", "Quebec City", "Canada", 46.8139, -71.2080),
    ("reykjavik", "Reykjavik", "Iceland", 64.1466, -21.9426),
    ("oslo", "Oslo", "Norway", 59.9139, 10.7522),
    ("stockholm", "Stockholm", "Sweden", 59.3293, 18.0686),
    ("copenhagen", "Copenhagen", "Denmark", 55.6761, 12.5683),
    ("helsinki", "Helsinki", "Finland", 60.1699, 24.9384),
    ("dublin", "Dublin", "Ireland", 53.3498, -6.2603),
    ("glasgow", "Glasgow", "United Kingdom", 55.8642, -4.2518),
    ("manchester-uk", "Manchester", "United Kingdom", 53.4808, -2.2426),
    ("munich", "Munich", "Germany", 48.1351, 11.5820),
    ("hamburg", "Hamburg", "Germany", 53.5511, 9.9937),
    ("frankfurt", "Frankfurt", "Germany", 50.1109, 8.6821),
    ("cologne", "Cologne", "Germany", 50.9375, 6.9603),
    ("zurich", "Zurich", "Switzerland", 47.3769, 8.5417),
    ("geneva", "Geneva", "Switzerland", 46.2044, 6.1432),
    ("lisbon", "Lisbon", "Portugal", 38.7223, -9.1393),
    ("porto", "Porto", "Portugal", 41.1579, -8.6291),
    ("seville", "Seville", "Spain", 37.3891, -5.9845),
    ("valencia", "Valencia", "Spain", 39.4699, -0.3763),
    ("naples", "Naples", "Italy", 40.8518, 14.2681),
    ("bologna", "Bologna", "Italy", 44.4949, 11.3426),
    ("marseille", "Marseille", "France", 43.2965, 5.3698),
    ("lyon", "Lyon", "France", 45.7640, 4.8357),
    ("sofia", "Sofia", "Bulgaria", 42.6977, 23.3219),
    ("bucharest", "Bucharest", "Romania", 44.4268, 26.1025),
    ("belgrade", "Belgrade", "Serbia", 44.7866, 20.4489),
    ("zagreb", "Zagreb", "Croatia", 45.8150, 15.9819),
    ("krakow", "Kraków", "Poland", 50.0647, 19.9450),
    ("shanghai", "Shanghai", "China", 31.2304, 121.4737),
    ("guangzhou", "Guangzhou", "China", 23.1291, 113.2644),
    ("chengdu", "Chengdu", "China", 30.5728, 104.0668),
    ("xian", "Xi'an", "China", 34.3416, 108.9398),
    ("hiroshima", "Hiroshima", "Japan", 34.3853, 132.4553),
    ("sapporo", "Sapporo", "Japan", 43.0618, 141.3545),
    ("hakone", "Hakone", "Japan", 35.2329, 139.1075),
    ("nara", "Nara", "Japan", 34.6851, 135.8048),
]


def expand_cities(db, City):
    """Add ~160 more well-known cities. Idempotent: gate by count threshold."""
    if City.query.count() >= 200:
        return
    added = 0
    for slug, display, country, lat, lng in EXPAND_CITIES:
        if City.query.filter_by(slug=slug).first():
            continue
        db.session.add(City(
            slug=slug, display_name=display, country=country,
            hero_image="/static/images/heroes/eiffel-tower.jpg",
            description=f"Explore {display} - one of {country}'s most beloved destinations.",
            lat=lat, lng=lng,
        ))
        added += 1
    db.session.commit()
    print(f"expand_cities: added {added} cities (total {City.query.count()})")


# --- Templates for catalog-density places per city ---
_EXPAND_TEMPLATES = [
    # (category_slug, name_pattern, subtitle, desc, price, rating_lo, rating_hi)
    ("restaurants", "{anchor} Trattoria", "Italian restaurant",
     "Family-run trattoria serving handmade pasta, wood-fired pizza, and Italian wines.", "$$", 4.1, 4.7),
    ("restaurants", "{anchor} Noodle House", "Asian noodle bar",
     "Asian noodle bar with rich broths, hand-pulled noodles, and small plates.", "$", 4.0, 4.6),
    ("restaurants", "{anchor} Steakhouse", "Steakhouse",
     "Classic steakhouse with prime cuts, an extensive wine list, and dim lighting.", "$$$", 4.2, 4.8),
    ("restaurants", "Cafe {anchor}", "Cafe and bakery",
     "Neighborhood cafe with single-origin coffee, fresh pastries, and all-day brunch.", "$", 4.3, 4.8),
    ("restaurants", "{anchor} Tacos", "Taqueria",
     "Casual taqueria with house-made tortillas, salsas, and street-style tacos.", "$", 4.0, 4.7),
    ("restaurants", "{anchor} Sushi Bar", "Sushi bar",
     "Intimate sushi bar with seasonal fish and omakase chef's choice menus.", "$$$", 4.3, 4.9),
    ("hotels", "{anchor} Boutique Hotel", "Boutique hotel",
     "Design-forward boutique hotel with individually styled rooms and an in-house bar.", "$$$", 4.2, 4.7),
    ("hotels", "{anchor} Plaza Inn", "Mid-range hotel",
     "Comfortable mid-range hotel with full amenities, fitness center, and quick airport shuttle.", "$$", 4.0, 4.5),
    ("hotels", "{anchor} Suites", "All-suite hotel",
     "All-suite property with kitchenettes, family-friendly layouts, and free breakfast.", "$$", 4.1, 4.6),
    ("shopping", "{anchor} Marketplace", "Market",
     "Open-air marketplace with produce, artisan goods, and street food stalls.", "$", 4.2, 4.7),
    ("shopping", "{anchor} Bookshop", "Bookstore",
     "Independent bookshop with thoughtful curation and a cozy reading nook.", "$$", 4.3, 4.8),
    ("shopping", "{anchor} Outfitters", "Outdoor retailer",
     "Outdoor retailer with gear for hiking, camping, climbing, and travel.", "$$$", 4.0, 4.6),
    ("attractions", "{anchor} Observation Point", "Viewpoint",
     "Scenic observation point with sweeping city views, especially at sunset.", "Free", 4.4, 4.9),
    ("attractions", "Old Town {anchor}", "Historic district",
     "Historic district lined with heritage buildings, public squares, and walking tours.", "Free", 4.3, 4.8),
    ("museums", "{anchor} Museum of Art", "Art museum",
     "Regional art museum featuring rotating exhibitions and a permanent collection.", "$", 4.2, 4.8),
    ("museums", "{anchor} History Museum", "History museum",
     "History museum tracing the city's founding, industries, and notable residents.", "$", 4.1, 4.7),
    ("parks", "{anchor} City Park", "Public park",
     "Large urban park with walking trails, a pond, picnic lawns, and playgrounds.", "Free", 4.4, 4.9),
    ("parks", "{anchor} Botanical Garden", "Botanical garden",
     "Curated botanical garden featuring native plants, themed greenhouses, and seasonal blooms.", "$", 4.4, 4.9),
    ("entertainment", "{anchor} Jazz Club", "Live music venue",
     "Intimate jazz club with nightly sets, craft cocktails, and a relaxed crowd.", "$$", 4.2, 4.7),
    ("entertainment", "{anchor} Cinema", "Movie theater",
     "Independent cinema showing arthouse releases, festival picks, and classic revivals.", "$", 4.0, 4.5),
    ("transit", "{anchor} Transit Hub", "Transit station",
     "Multi-modal transit hub with bus, rail, and rideshare connections.", "Free", 3.8, 4.4),
    ("services", "{anchor} Locksmith Services", "Locksmith",
     "Licensed locksmith offering residential, automotive, and emergency lockout help.", "$$", 4.0, 4.7),
    ("services", "{anchor} Auto Repair", "Auto repair shop",
     "Trusted auto repair shop with ASE-certified mechanics and same-day service.", "$$", 4.1, 4.7),
    ("health-beauty", "{anchor} Day Spa", "Day spa",
     "Full-service day spa offering massage, facials, and seasonal wellness packages.", "$$$", 4.3, 4.8),
    ("health-beauty", "{anchor} Hair Studio", "Hair salon",
     "Full-service hair salon specializing in cuts, color, and extensions.", "$$", 4.1, 4.7),
    ("fitness", "{anchor} Climbing Gym", "Climbing gym",
     "Indoor climbing gym with top-rope, lead, and bouldering walls for all levels.", "$$", 4.3, 4.8),
    ("fitness", "{anchor} Yoga Studio", "Yoga studio",
     "Drop-in yoga studio with vinyasa, restorative, and hot yoga classes daily.", "$$", 4.3, 4.8),
    ("ev-charging", "{anchor} EV Charging Plaza", "EV charging station",
     "Public EV charging plaza with multiple CCS and Tesla connectors.", "$", 4.2, 4.7),
    ("parking", "{anchor} Public Parking Garage", "Parking garage",
     "Public parking garage with hourly and daily rates, covered spaces.", "$$", 3.9, 4.5),
]

# Curated chain brands per category for varied catalog listings
_EXPAND_CHAINS = {
    "restaurants": ["Shake Shack", "Chipotle", "Sweetgreen", "Five Guys", "P.F. Chang's"],
    "hotels": ["Hilton", "Marriott", "Hyatt", "Sheraton", "Holiday Inn", "Best Western"],
    "shopping": ["Whole Foods Market", "Trader Joe's", "Target", "Costco", "Best Buy", "REI"],
    "fitness": ["Equinox", "Planet Fitness", "Anytime Fitness", "Orangetheory Fitness"],
    "ev-charging": ["Tesla Supercharger", "Electrify America", "ChargePoint Station", "EVgo Fast Charging"],
}


def expand_places(db, Place, Category, City):
    """Densify the catalog so every city has 8-10 places spanning categories.

    Idempotent: gate by Place count threshold.
    """
    if Place.query.count() >= 1500:
        return

    random.seed(20260415)
    cat_by_slug = {c.slug: c for c in Category.query.all()}
    cities = City.query.order_by(City.id).all()
    if not cities:
        return

    # Donor images: pull from places that already have curated gallery photos
    donor_pool = []
    for p in Place.query.filter(Place.hero_image.like("/static/images/places/%")).limit(60).all():
        try:
            photos = json.loads(p.photos_json or "[]")
        except Exception:
            photos = []
        if p.hero_image:
            donor_pool.append((p.hero_image, photos or [p.hero_image]))
    if not donor_pool:
        donor_pool = [("/static/images/heroes/eiffel-tower.jpg",
                       ["/static/images/heroes/eiffel-tower.jpg"])]

    added = 0
    for city in cities:
        # Anchor word for naming, derived from display name
        anchor = city.display_name.split(",")[0].split(" ")[0]
        # Use templates in deterministic but varied order per city
        templates = list(_EXPAND_TEMPLATES)
        random.Random(hash(city.slug) & 0xFFFF_FFFF).shuffle(templates)

        for idx, (cat_slug, pattern, subtitle, desc, price, rlo, rhi) in enumerate(templates):
            cat = cat_by_slug.get(cat_slug)
            if not cat:
                continue
            # Inject occasional chain brand into the name for realism + distractors
            chain = ""
            if idx % 4 == 0 and cat_slug in _EXPAND_CHAINS:
                chain = random.choice(_EXPAND_CHAINS[cat_slug])
                name = f"{chain} {anchor}"
            else:
                name = pattern.format(anchor=anchor)

            slug = f"x-{city.slug}-{cat_slug}-{idx}"
            if Place.query.filter_by(slug=slug).first():
                continue

            hero, gallery = random.choice(donor_pool)
            lat = city.lat + random.uniform(-0.04, 0.04)
            lng = city.lng + random.uniform(-0.05, 0.05)
            rating = round(random.uniform(rlo, rhi), 1)
            review_count = random.randint(60, 5400)

            tags = [cat_slug, anchor.lower(), city.country.lower()]
            if chain:
                tags.append(chain.split()[0].lower())

            db.session.add(Place(
                slug=slug, name=name, category_id=cat.id, city_id=city.id,
                subtitle=subtitle,
                description=desc,
                address=f"{random.randint(10, 999)} Main St, {city.display_name}",
                phone=f"+{random.randint(1, 99)} {random.randint(100, 999)} {random.randint(1000, 9999)}",
                hours=random.choice([
                    "Mon-Sun: 9:00 AM - 9:00 PM",
                    "Mon-Sat: 10:00 AM - 8:00 PM, Sun 11:00 AM - 6:00 PM",
                    "Tue-Sun: 11:00 AM - 10:00 PM, Closed Mon",
                    "Open 24 hours",
                    "Mon-Fri: 7:00 AM - 7:00 PM, Weekends 8:00 AM - 5:00 PM",
                ]),
                website=google_maps_search_url(name, city.display_name),
                rating=rating,
                review_count=review_count,
                price_level=price,
                hero_image=hero,
                photos_json=json.dumps(gallery[:5]),
                lat=lat, lng=lng,
                tags_json=json.dumps(tags),
                chain_brand=chain,
                subcategory=subtitle,
                is_24h=(random.random() < 0.06),
                is_popular=(rating >= 4.5 and random.random() < 0.4),
                has_parking_lot=(cat_slug in ("shopping", "hotels", "fitness") or random.random() < 0.3),
                delivery_available=(cat_slug == "restaurants" and random.random() < 0.55),
                ev_charging=(cat_slug == "ev-charging"),
            ))
            added += 1
            if added % 250 == 0:
                db.session.commit()

    db.session.commit()
    print(f"expand_places: added {added} catalog places (total {Place.query.count()})")


# --- 22 additional routes between popular destinations ---
_EXPAND_ROUTES = [
    ("Eiffel Tower", "Louvre Museum", "walking", "2.4 km", 2.4, "30 min", 30,
     "Eiffel Tower to Louvre via Quai Branly and Pont Royal",
     "Eiffel Tower, Champ de Mars, Paris", "Louvre Museum, Rue de Rivoli, Paris", [
         {"instruction": "Head east on Quai Branly", "distance": "0.8 km"},
         {"instruction": "Cross Pont de la Concorde", "distance": "0.5 km"},
         {"instruction": "Walk along Tuileries Garden", "distance": "0.7 km"},
         {"instruction": "Arrive at Louvre Museum main entrance", "distance": "0.4 km"},
     ]),
    ("Colosseum", "Trevi Fountain", "walking", "1.3 km", 1.3, "17 min", 17,
     "Colosseum to Trevi Fountain via Via dei Fori Imperiali",
     "Colosseum, Rome", "Trevi Fountain, Rome", [
         {"instruction": "Head northwest on Via dei Fori Imperiali", "distance": "0.6 km"},
         {"instruction": "Continue onto Via IV Novembre", "distance": "0.4 km"},
         {"instruction": "Turn right onto Via del Tritone", "distance": "0.2 km"},
         {"instruction": "Arrive at Trevi Fountain", "distance": "0.1 km"},
     ]),
    ("Big Ben", "London Eye", "walking", "0.7 km", 0.7, "9 min", 9,
     "Westminster to London Eye via Westminster Bridge",
     "Big Ben, Westminster, London", "London Eye, South Bank, London", [
         {"instruction": "Head east across Westminster Bridge", "distance": "0.4 km"},
         {"instruction": "Take stairs down to South Bank promenade", "distance": "0.2 km"},
         {"instruction": "Arrive at London Eye ticket office", "distance": "0.1 km"},
     ]),
    ("Tokyo Tower", "Tokyo Skytree", "transit", "9.6 km", 9.6, "35 min", 35,
     "Tokyo Tower to Skytree via Toei Asakusa Line",
     "Tokyo Tower, Shibakoen, Tokyo", "Tokyo Skytree, Oshiage, Tokyo", [
         {"instruction": "Walk to Akabanebashi Station (8 min)", "distance": "0.6 km"},
         {"instruction": "Take Toei Oedo Line to Kuramae", "distance": "5.0 km"},
         {"instruction": "Transfer to Toei Asakusa Line for Oshiage", "distance": "3.5 km"},
         {"instruction": "Walk to Tokyo Skytree base", "distance": "0.5 km"},
     ]),
    ("Brooklyn Bridge", "Statue of Liberty", "transit", "11 km", 11.0, "55 min", 55,
     "Brooklyn Bridge to Statue of Liberty via Battery Park ferry",
     "Brooklyn Bridge, NY", "Statue of Liberty, Liberty Island, NY", [
         {"instruction": "Walk south along Centre St toward Battery Park", "distance": "2.4 km"},
         {"instruction": "Board Statue Cruises ferry at Battery Park", "distance": "0.3 km"},
         {"instruction": "Ferry to Liberty Island", "distance": "8.0 km"},
         {"instruction": "Disembark and walk to monument base", "distance": "0.3 km"},
     ]),
    ("Sydney Opera House", "Bondi Beach", "driving", "7.8 km", 7.8, "20 min", 20,
     "Opera House to Bondi via Bondi Rd",
     "Sydney Opera House, Sydney", "Bondi Beach, Sydney", [
         {"instruction": "Head east on Macquarie St", "distance": "0.6 km"},
         {"instruction": "Take Cross City Tunnel and William St east", "distance": "2.4 km"},
         {"instruction": "Continue onto Oxford St then Bondi Rd", "distance": "4.0 km"},
         {"instruction": "Arrive at Bondi Beach esplanade", "distance": "0.8 km"},
     ]),
    ("Houston", "Austin", "driving", "265 km", 265.0, "2 hr 50 min", 170,
     "Houston to Austin via TX-71 W and US-290 W",
     "Houston, TX", "Austin, TX", [
         {"instruction": "Head west on I-10 W out of Houston", "distance": "70 km"},
         {"instruction": "Take exit toward US-290 W", "distance": "5 km"},
         {"instruction": "Continue west on US-290 toward Brenham", "distance": "100 km"},
         {"instruction": "Merge onto TX-71 W toward Bastrop", "distance": "70 km"},
         {"instruction": "Take exit toward central Austin", "distance": "15 km"},
         {"instruction": "Arrive in Austin, TX", "distance": "5 km"},
     ]),
    ("Seattle-Tacoma International Airport", "Pike Place Market", "driving", "23 km", 23.0, "30 min", 30,
     "SEA Airport to Pike Place Market via I-5 N",
     "Seattle-Tacoma International Airport, SeaTac, WA", "Pike Place Market, Seattle, WA", [
         {"instruction": "Head north on Airport Expressway", "distance": "2 km"},
         {"instruction": "Merge onto I-5 N", "distance": "16 km"},
         {"instruction": "Take exit 165 toward Madison St", "distance": "1 km"},
         {"instruction": "Turn right onto 1st Ave", "distance": "3 km"},
         {"instruction": "Arrive at Pike Place Market entrance", "distance": "1 km"},
     ]),
    ("Golden Gate Park", "Fisherman's Wharf", "driving", "9.2 km", 9.2, "22 min", 22,
     "Golden Gate Park to Fisherman's Wharf via Park Presidio Blvd",
     "Golden Gate Park, San Francisco, CA", "Fisherman's Wharf, San Francisco, CA", [
         {"instruction": "Head north on Park Presidio Blvd", "distance": "2.0 km"},
         {"instruction": "Continue onto Marina Blvd along the bay", "distance": "4.0 km"},
         {"instruction": "Turn right onto Bay St", "distance": "2.2 km"},
         {"instruction": "Arrive at Fisherman's Wharf", "distance": "1.0 km"},
     ]),
    ("Dallas", "Fort Worth", "driving", "55 km", 55.0, "45 min", 45,
     "Dallas to Fort Worth via I-30 W",
     "Dallas, TX", "Fort Worth, TX", [
         {"instruction": "Head west on I-30 W from downtown Dallas", "distance": "10 km"},
         {"instruction": "Continue west on I-30 W through Arlington", "distance": "35 km"},
         {"instruction": "Take exit 14B toward downtown Fort Worth", "distance": "5 km"},
         {"instruction": "Arrive in downtown Fort Worth", "distance": "5 km"},
     ]),
    ("Las Vegas Strip", "Hoover Dam", "driving", "55 km", 55.0, "50 min", 50,
     "Las Vegas Strip to Hoover Dam via US-93 S",
     "Las Vegas Strip, NV", "Hoover Dam, NV", [
         {"instruction": "Head south on Las Vegas Blvd", "distance": "6 km"},
         {"instruction": "Merge onto I-215 E toward Henderson", "distance": "15 km"},
         {"instruction": "Continue onto US-93 S / I-11 S", "distance": "30 km"},
         {"instruction": "Take exit for Hoover Dam Access Rd", "distance": "3 km"},
         {"instruction": "Arrive at Hoover Dam visitor center", "distance": "1 km"},
     ]),
    ("Denver", "Boulder", "driving", "47 km", 47.0, "40 min", 40,
     "Denver to Boulder via US-36 W",
     "Denver, CO", "Boulder, CO", [
         {"instruction": "Head north on I-25 N out of Denver", "distance": "5 km"},
         {"instruction": "Take exit 217 onto US-36 W toward Boulder", "distance": "35 km"},
         {"instruction": "Take exit toward 28th St", "distance": "4 km"},
         {"instruction": "Continue onto Canyon Blvd", "distance": "2 km"},
         {"instruction": "Arrive in downtown Boulder", "distance": "1 km"},
     ]),
    ("Portland", "Mount Hood", "driving", "100 km", 100.0, "1 hr 25 min", 85,
     "Portland to Mount Hood via US-26 E",
     "Portland, OR", "Mount Hood, OR", [
         {"instruction": "Head east on Burnside St", "distance": "5 km"},
         {"instruction": "Continue onto US-26 E", "distance": "85 km"},
         {"instruction": "Take exit toward Timberline Lodge", "distance": "8 km"},
         {"instruction": "Arrive at Mount Hood Timberline area", "distance": "2 km"},
     ]),
    ("Atlanta", "Savannah", "driving", "395 km", 395.0, "4 hr", 240,
     "Atlanta to Savannah via I-75 S and I-16 E",
     "Atlanta, GA", "Savannah, GA", [
         {"instruction": "Head south on I-75 S out of Atlanta", "distance": "150 km"},
         {"instruction": "Take I-16 E toward Macon", "distance": "10 km"},
         {"instruction": "Continue on I-16 E for ~225 km", "distance": "225 km"},
         {"instruction": "Take exit 165 toward downtown Savannah", "distance": "10 km"},
     ]),
    ("Philadelphia", "Washington, DC", "transit", "225 km", 225.0, "1 hr 50 min", 110,
     "Philadelphia to DC via Amtrak Northeast Regional",
     "30th Street Station, Philadelphia, PA", "Union Station, Washington, DC", [
         {"instruction": "Board Amtrak Northeast Regional at 30th St Station", "distance": "0.1 km"},
         {"instruction": "Train stops at Wilmington and Baltimore", "distance": "120 km"},
         {"instruction": "Continue to BWI Airport stop", "distance": "60 km"},
         {"instruction": "Arrive at Union Station, Washington DC", "distance": "45 km"},
     ]),
    ("Chicago O'Hare International Airport", "Magnificent Mile", "transit", "27 km", 27.0, "50 min", 50,
     "O'Hare to Mag Mile via CTA Blue Line + Red Line",
     "Chicago O'Hare International Airport, Chicago, IL", "Magnificent Mile, Chicago, IL", [
         {"instruction": "Take CTA Blue Line from O'Hare toward Loop", "distance": "22 km"},
         {"instruction": "Transfer at Jackson to Red Line northbound", "distance": "0.3 km"},
         {"instruction": "Ride Red Line to Chicago/State", "distance": "3 km"},
         {"instruction": "Walk east on Chicago Ave to Michigan Ave", "distance": "1.5 km"},
     ]),
    ("Berlin Brandenburg Airport", "Brandenburg Gate", "transit", "30 km", 30.0, "45 min", 45,
     "BER to Brandenburg Gate via S-Bahn",
     "Berlin Brandenburg Airport, Schönefeld", "Brandenburg Gate, Berlin", [
         {"instruction": "Board FEX or S9 toward city center", "distance": "20 km"},
         {"instruction": "Transfer to S1 at Friedrichstraße", "distance": "8 km"},
         {"instruction": "Walk west to Brandenburger Tor", "distance": "0.8 km"},
     ]),
    ("Singapore Changi Airport", "Marina Bay Sands", "transit", "22 km", 22.0, "40 min", 40,
     "Changi Airport to Marina Bay Sands via MRT",
     "Singapore Changi Airport", "Marina Bay Sands, Singapore", [
         {"instruction": "Take MRT East-West Line toward Tanah Merah", "distance": "3 km"},
         {"instruction": "Transfer to East-West Line city-bound", "distance": "15 km"},
         {"instruction": "Transfer at Bayfront to walk to MBS", "distance": "0.3 km"},
         {"instruction": "Walk to Marina Bay Sands lobby", "distance": "0.5 km"},
     ]),
    ("Vancouver", "Whistler", "driving", "120 km", 120.0, "1 hr 50 min", 110,
     "Vancouver to Whistler via Sea-to-Sky Highway",
     "Vancouver, BC, Canada", "Whistler Village, BC, Canada", [
         {"instruction": "Head north on BC-99 (Sea-to-Sky)", "distance": "40 km"},
         {"instruction": "Continue along Howe Sound past Britannia Beach", "distance": "30 km"},
         {"instruction": "Pass through Squamish", "distance": "20 km"},
         {"instruction": "Continue toward Whistler Village", "distance": "30 km"},
     ]),
    ("Montreal", "Quebec City", "driving", "255 km", 255.0, "2 hr 50 min", 170,
     "Montreal to Quebec City via Autoroute 20 E",
     "Montreal, QC, Canada", "Quebec City, QC, Canada", [
         {"instruction": "Head east on Autoroute 20 from Montreal", "distance": "60 km"},
         {"instruction": "Continue past Drummondville", "distance": "90 km"},
         {"instruction": "Pass Lévis on the south shore", "distance": "80 km"},
         {"instruction": "Cross Pont Pierre-Laporte", "distance": "10 km"},
         {"instruction": "Arrive in Vieux-Québec", "distance": "15 km"},
     ]),
    ("Buenos Aires", "Iguazu Falls", "driving", "1280 km", 1280.0, "15 hr", 900,
     "Buenos Aires to Iguazu via RN-12 N",
     "Buenos Aires, Argentina", "Iguazu Falls, Argentina", [
         {"instruction": "Head north on RN-9 toward Rosario", "distance": "300 km"},
         {"instruction": "Continue onto RN-12 N", "distance": "550 km"},
         {"instruction": "Pass through Posadas", "distance": "320 km"},
         {"instruction": "Take exit toward Puerto Iguazú", "distance": "100 km"},
         {"instruction": "Arrive at Iguazu National Park entrance", "distance": "10 km"},
     ]),
    ("Cape Town International Airport", "Table Mountain", "driving", "30 km", 30.0, "30 min", 30,
     "Cape Town Airport to Table Mountain via N2 W",
     "Cape Town International Airport, Cape Town", "Table Mountain Cableway, Cape Town", [
         {"instruction": "Head west on N2 toward Cape Town", "distance": "20 km"},
         {"instruction": "Take exit toward Kloof Nek Rd", "distance": "5 km"},
         {"instruction": "Continue up Tafelberg Rd", "distance": "4 km"},
         {"instruction": "Arrive at Lower Cableway Station", "distance": "1 km"},
     ]),
]


def expand_routes(db, Route):
    """Add 22 more routes for breadth. Idempotent: gate by Route count."""
    if Route.query.count() >= 30:
        return
    added = 0
    for tup in _EXPAND_ROUTES:
        (origin_q, dest_q, mode, dist, dist_km, dur, dur_min, summary,
         origin_addr, dest_addr, steps) = tup
        existing = Route.query.filter_by(
            origin_query=origin_q, destination_query=dest_q, mode=mode).first()
        if existing:
            continue
        db.session.add(Route(
            origin_query=origin_q, destination_query=dest_q,
            origin_name=origin_q, destination_name=dest_q,
            mode=mode, distance=dist, distance_km=dist_km,
            duration=dur, duration_min=dur_min, summary=summary,
            origin_address=origin_addr, destination_address=dest_addr,
            steps_json=json.dumps(steps),
        ))
        added += 1
    db.session.commit()
    print(f"expand_routes: added {added} routes (total {Route.query.count()})")


# --- User content: reviews, photos, timeline entries -----------------------

_REVIEW_BODIES = {
    5: [
        ("Absolutely fantastic", "One of the best experiences we've had. Staff were attentive, the space was beautiful, and we left already planning our return visit."),
        ("Highly recommend", "Met expectations and then some. Came on a weekday afternoon and there was no wait, plenty of seating, and clean restrooms."),
        ("Worth the trip", "Easily worth the detour. We took our time exploring and the photos don't really do it justice."),
        ("Five stars no notes", "Service was warm, prices were fair, and everything came out exactly as ordered."),
        ("Memorable visit", "Brought my parents during their visit and they loved it. The little details really make this place stand out."),
    ],
    4: [
        ("Very good overall", "Solid experience. Lost a star because parking was a hassle, but once we were inside we had no complaints."),
        ("Would come again", "Enjoyable for a couple of hours. A bit crowded on the weekend, but staff handled it well."),
        ("Better than expected", "Walked in skeptical and walked out impressed. Friendly people, good value."),
        ("Comfortable spot", "Nothing flashy, but everything you'd want from a place like this. Will be back."),
        ("Strong showing", "Good food, decent atmosphere, slightly slow service. Would still recommend to a friend."),
    ],
    3: [
        ("Mixed bag", "Some things were great, others felt rushed. Manager was nice when I flagged an issue, which helped."),
        ("Just okay", "It was fine. Nothing to write home about but nothing terrible either."),
        ("Has potential", "Concept is interesting and the space is well done. Execution needs a bit of polish."),
        ("Average", "Reasonable prices, average quality. Crowded at peak hours; quieter mid-week."),
        ("Three-star experience", "Some highs and lows. The highs were genuinely high; the lows kept it from being a higher rating."),
    ],
    2: [
        ("Disappointing", "Had higher hopes after reading the other reviews. Service was slow and the space felt tired."),
        ("Not great", "Wouldn't rush back. There are better options nearby for the price."),
        ("Below expectations", "Felt understaffed when we visited. Took 20 minutes just to get water refills."),
        ("Two-star visit", "A few small things added up. Not a terrible place, just not for us."),
    ],
    1: [
        ("Would not recommend", "Multiple things went wrong and no one seemed to care. Will not be returning."),
        ("Bad experience", "Hard to overstate how off the visit felt. Asked to speak with a manager and never got one."),
        ("One star is generous", "Genuinely the worst experience we've had in months. Save your time and go somewhere else."),
    ],
}


_PHOTO_CAPTIONS = [
    "Beautiful afternoon light",
    "View from the entrance",
    "Sunset from outside",
    "Loved the architecture",
    "Quiet corner we found",
    "Crowded but worth it",
    "Snapped this before dinner",
    "Postcard moment",
    "Up close on the details",
    "First-time visitor",
    "Quick stop on the way",
    "Couldn't resist a photo",
    "From our table",
    "Walking around the perimeter",
    "Morning view, very peaceful",
    "Lots to take in",
    "Wide shot of the area",
    "Hidden gem",
    "Family loved this",
    "Memorable visit",
]

_TIMELINE_NOTES = [
    "Stopped by on the way home", "Quick visit during lunch break",
    "Long-planned trip with friends", "Birthday celebration here",
    "Anniversary dinner", "First-time visit, will be back",
    "Weekend wander", "Brought the kids - they loved it",
    "Met old friends after years", "Recommended by a colleague",
    "Saw it on a list of must-visit spots", "Tried the new menu",
    "Beautiful weather, perfect outing", "Hosted a small gathering nearby",
    "Pulled over while road tripping", "Walked here from the hotel",
    "", "", "", "",
]


def seed_user_content(db, User, Place, Review, Photo, TimelineEntry):
    """Populate review / photo / timeline_entry tables with realistic
    user-generated content across the 4 benchmark users.

    Idempotent: gate by counts on all three tables.
    Must run AFTER seed_benchmark_users().
    """
    if (Review.query.count() > 0 and Photo.query.count() > 0
            and TimelineEntry.query.count() > 0):
        return

    users = User.query.order_by(User.id).all()
    if not users:
        return

    # Stable ordering - prefer popular & well-known places for content
    places = (Place.query
              .order_by(Place.is_popular.desc(), Place.id)
              .limit(450).all())
    if not places:
        return

    rng = random.Random(31415)

    # ---------- REVIEWS (~280) ----------
    if Review.query.count() == 0:
        target = 280
        for i in range(target):
            user = users[i % len(users)]
            place = places[(i * 13 + 7) % len(places)]
            rating = rng.choices([5, 4, 3, 2, 1],
                                 weights=[44, 30, 14, 8, 4])[0]
            title, body = rng.choice(_REVIEW_BODIES[rating])
            # Deterministic created_at offset, but spread over ~18 months
            days_ago = (i * 5 + (i * i) % 17) % 540 + 3
            created = MIRROR_REFERENCE_DATE - timedelta(
                days=days_ago, hours=(i * 7) % 24, minutes=(i * 11) % 60)
            db.session.add(Review(
                user_id=user.id, place_id=place.id,
                rating=rating, title=title, body=body,
                created_at=created,
            ))
            if (i + 1) % 100 == 0:
                db.session.commit()
        db.session.commit()
        print(f"seed_user_content: added {Review.query.count()} reviews")

    # ---------- PHOTOS (~140) ----------
    if Photo.query.count() == 0:
        target = 140
        for i in range(target):
            user = users[(i + 1) % len(users)]
            place = places[(i * 19 + 3) % len(places)]
            # Reuse the place's hero/gallery URLs - no new image files needed
            try:
                gallery = json.loads(place.photos_json or "[]")
            except Exception:
                gallery = []
            img = (gallery or [place.hero_image
                               or "/static/images/heroes/eiffel-tower.jpg"])[i % max(1, len(gallery) or 1)]
            caption = rng.choice(_PHOTO_CAPTIONS)
            days_ago = (i * 7 + 5) % 420 + 2
            created = MIRROR_REFERENCE_DATE - timedelta(
                days=days_ago, hours=(i * 5) % 24, minutes=(i * 13) % 60)
            db.session.add(Photo(
                user_id=user.id, place_id=place.id,
                image_url=img, caption=caption, created_at=created,
            ))
            if (i + 1) % 100 == 0:
                db.session.commit()
        db.session.commit()
        print(f"seed_user_content: added {Photo.query.count()} photos")

    # ---------- TIMELINE ENTRIES (~75) ----------
    if TimelineEntry.query.count() == 0:
        target = 75
        for i in range(target):
            user = users[(i + 2) % len(users)]
            place = places[(i * 23 + 11) % len(places)]
            note = rng.choice(_TIMELINE_NOTES)
            days_ago = (i * 6 + 2) % 360 + 1
            visited = MIRROR_REFERENCE_DATE - timedelta(
                days=days_ago, hours=(i * 4) % 24, minutes=(i * 17) % 60)
            db.session.add(TimelineEntry(
                user_id=user.id, place_id=place.id,
                visited_at=visited, note=note,
            ))
        db.session.commit()
        print(f"seed_user_content: added {TimelineEntry.query.count()} timeline entries")
