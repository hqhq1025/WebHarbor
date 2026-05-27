"""
Seed data for Google Maps mirror.
Loads PLACES and CITIES from scrape_wiki so every entity has real images on disk.
Enriches each place with address, phone, hours, rating, etc.
"""
import hashlib
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
    {
        "slug": "pharmacies", "name": "Pharmacies", "icon": "local_pharmacy",
        "color": "#26a69a",
        "description": "24-hour pharmacies and neighborhood drugstores for prescriptions and essentials.",
    },
    {
        "slug": "atms", "name": "ATMs", "icon": "local_atm",
        "color": "#9e9d24",
        "description": "Cash machines and bank ATMs from major networks across every neighborhood.",
    },
    {
        "slug": "gas-stations", "name": "Gas Stations", "icon": "local_gas_station",
        "color": "#ff7043",
        "description": "Fuel stations from major brands with convenience stores and air pumps.",
    },
    {
        "slug": "supermarkets", "name": "Supermarkets", "icon": "shopping_cart",
        "color": "#5e35b1",
        "description": "Full-service grocery stores, food markets, and warehouse retailers.",
    },
    {
        "slug": "coffee-shops", "name": "Coffee Shops", "icon": "local_cafe",
        "color": "#8d6e63",
        "description": "Neighborhood coffee shops, specialty roasters, and chain cafes.",
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
        # --- R3 additions ---
        {"slug": "dog-parks", "name": "Dog Parks", "icon": "pets",
         "color": "#8bc34a", "description": "Off-leash dog parks and pet-friendly green spaces."},
        {"slug": "public-restrooms", "name": "Public Restrooms", "icon": "wc",
         "color": "#90a4ae", "description": "Public restrooms, comfort stations, and family bathrooms."},
        {"slug": "libraries", "name": "Libraries", "icon": "local_library",
         "color": "#5d4037", "description": "Public libraries, branches, and reading rooms."},
        {"slug": "post-offices", "name": "Post Offices", "icon": "local_post_office",
         "color": "#0277bd", "description": "USPS branches, postal stations, and shipping counters."},
        {"slug": "police-stations", "name": "Police Stations", "icon": "local_police",
         "color": "#283593", "description": "Police precincts, sheriff offices, and public safety stations."},
        {"slug": "fire-stations", "name": "Fire Stations", "icon": "local_fire_department",
         "color": "#c62828", "description": "Fire stations and emergency response houses."},
        {"slug": "indoor-mall-shops", "name": "Indoor Mall Shops", "icon": "store_mall_directory",
         "color": "#7e57c2", "description": "Sub-shops located inside shopping malls and indoor centers."},
        {"slug": "indoor-airport-shops", "name": "Airport Concourse Shops", "icon": "flight_takeoff",
         "color": "#00838f", "description": "Shops, lounges, and amenities inside airport terminals and concourses."},
        {"slug": "campus-buildings", "name": "Campus Buildings", "icon": "school",
         "color": "#6d4c41", "description": "University campus buildings - libraries, halls, labs, and quads."},
        {"slug": "car-rental", "name": "Car Rental", "icon": "car_rental",
         "color": "#1565c0", "description": "Rental agencies for cars, SUVs, and trucks - airport and city locations."},
        {"slug": "playgrounds", "name": "Playgrounds", "icon": "child_care",
         "color": "#f9a825", "description": "Children's playgrounds and family play areas with safety surfacing."},
        {"slug": "beaches", "name": "Beaches", "icon": "beach_access",
         "color": "#039be5", "description": "Public beaches, swimming areas, and beachfront amenities."},
        {"slug": "hospitals", "name": "Hospitals", "icon": "local_hospital",
         "color": "#d32f2f", "description": "Hospitals and emergency rooms with 24-hour emergency services."},
        {"slug": "dentists", "name": "Dentists", "icon": "medical_services",
         "color": "#00acc1", "description": "General dentists, orthodontists, and pediatric dental offices."},
        {"slug": "veterinarians", "name": "Veterinarians", "icon": "pets",
         "color": "#7cb342", "description": "Veterinary clinics, animal hospitals, and 24-hour emergency vet care."},
        {"slug": "schools", "name": "Schools", "icon": "school",
         "color": "#6a1b9a", "description": "K-12 schools - elementary, middle, and high schools."},
        {"slug": "religious", "name": "Religious Sites", "icon": "church",
         "color": "#8e24aa", "description": "Churches, mosques, temples, synagogues, and other places of worship."},
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
    # --- R2 expansion: additional US metros ---
    ("anaheim-ca", "Anaheim, CA", "United States", 33.8366, -117.9143),
    ("riverside-ca", "Riverside, CA", "United States", 33.9533, -117.3962),
    ("santa-barbara-ca", "Santa Barbara, CA", "United States", 34.4208, -119.6982),
    ("monterey-ca", "Monterey, CA", "United States", 36.6002, -121.8947),
    ("napa-ca", "Napa, CA", "United States", 38.2975, -122.2869),
    ("palm-springs-ca", "Palm Springs, CA", "United States", 33.8303, -116.5453),
    ("fort-collins-co", "Fort Collins, CO", "United States", 40.5853, -105.0844),
    ("aspen-co", "Aspen, CO", "United States", 39.1911, -106.8175),
    ("vail-co", "Vail, CO", "United States", 39.6403, -106.3742),
    ("flagstaff-az", "Flagstaff, AZ", "United States", 35.1983, -111.6513),
    ("scottsdale-az", "Scottsdale, AZ", "United States", 33.4942, -111.9261),
    ("sedona-az", "Sedona, AZ", "United States", 34.8697, -111.7610),
    ("park-city-ut", "Park City, UT", "United States", 40.6461, -111.4980),
    ("moab-ut", "Moab, UT", "United States", 38.5733, -109.5498),
    ("santa-fe-tx", "Galveston, TX", "United States", 29.3013, -94.7977),
    ("corpus-christi-tx", "Corpus Christi, TX", "United States", 27.8006, -97.3964),
    ("waco-tx", "Waco, TX", "United States", 31.5493, -97.1467),
    ("lubbock-tx", "Lubbock, TX", "United States", 33.5779, -101.8552),
    ("amarillo-tx", "Amarillo, TX", "United States", 35.2220, -101.8313),
    ("durham-nc", "Durham, NC", "United States", 35.9940, -78.8986),
    ("wilmington-nc", "Wilmington, NC", "United States", 34.2257, -77.9447),
    ("greensboro-nc", "Greensboro, NC", "United States", 36.0726, -79.7920),
    ("winston-salem-nc", "Winston-Salem, NC", "United States", 36.0999, -80.2442),
    ("greenville-sc", "Greenville, SC", "United States", 34.8526, -82.3940),
    ("myrtle-beach-sc", "Myrtle Beach, SC", "United States", 33.6891, -78.8867),
    ("hilton-head-sc", "Hilton Head, SC", "United States", 32.2163, -80.7526),
    ("athens-ga", "Athens, GA", "United States", 33.9519, -83.3576),
    ("augusta-ga", "Augusta, GA", "United States", 33.4735, -82.0105),
    ("orlando-fl", "Orlando, FL", "United States", 28.5383, -81.3792),
    ("st-petersburg-fl", "St. Petersburg, FL", "United States", 27.7676, -82.6403),
    ("naples-fl", "Naples, FL", "United States", 26.1420, -81.7948),
    ("key-west-fl", "Key West, FL", "United States", 24.5551, -81.7800),
    ("sarasota-fl", "Sarasota, FL", "United States", 27.3364, -82.5307),
    ("pittsburgh-pa", "Pittsburgh, PA", "United States", 40.4406, -79.9959),
    ("scranton-pa", "Scranton, PA", "United States", 41.4090, -75.6624),
    ("lancaster-pa", "Lancaster, PA", "United States", 40.0379, -76.3055),
    ("erie-pa", "Erie, PA", "United States", 42.1292, -80.0851),
    ("toledo-oh", "Toledo, OH", "United States", 41.6528, -83.5379),
    ("dayton-oh", "Dayton, OH", "United States", 39.7589, -84.1916),
    ("akron-oh", "Akron, OH", "United States", 41.0814, -81.5190),
    ("louisville-ky", "Louisville, KY", "United States", 38.2527, -85.7585),
    ("lexington-ky", "Lexington, KY", "United States", 38.0406, -84.5037),
    ("fort-wayne-in", "Fort Wayne, IN", "United States", 41.0793, -85.1394),
    ("bloomington-in", "Bloomington, IN", "United States", 39.1653, -86.5264),
    ("detroit-mi", "Detroit, MI", "United States", 42.3314, -83.0458),
    ("lansing-mi", "Lansing, MI", "United States", 42.7325, -84.5555),
    ("traverse-city-mi", "Traverse City, MI", "United States", 44.7631, -85.6206),
    ("st-louis-mo", "Springfield, MO", "United States", 37.2089, -93.2923),
    ("branson-mo", "Branson, MO", "United States", 36.6437, -93.2185),
    ("wichita-ks", "Wichita, KS", "United States", 37.6872, -97.3301),
    ("topeka-ks", "Topeka, KS", "United States", 39.0473, -95.6752),
    ("sioux-falls-sd", "Sioux Falls, SD", "United States", 43.5446, -96.7311),
    ("rapid-city-sd", "Rapid City, SD", "United States", 44.0805, -103.2310),
    ("fargo-nd", "Fargo, ND", "United States", 46.8772, -96.7898),
    ("bismarck-nd", "Bismarck, ND", "United States", 46.8083, -100.7837),
    ("billings-mt", "Billings, MT", "United States", 45.7833, -108.5007),
    ("bozeman-mt", "Bozeman, MT", "United States", 45.6770, -111.0429),
    ("missoula-mt", "Missoula, MT", "United States", 46.8721, -113.9940),
    ("cheyenne-wy", "Cheyenne, WY", "United States", 41.1400, -104.8202),
    ("jackson-wy", "Jackson, WY", "United States", 43.4799, -110.7624),
    ("idaho-falls-id", "Idaho Falls, ID", "United States", 43.4926, -112.0408),
    ("spokane-wa", "Spokane, WA", "United States", 47.6588, -117.4260),
    ("tacoma-wa", "Tacoma, WA", "United States", 47.2529, -122.4443),
    ("bellevue-wa", "Bellevue, WA", "United States", 47.6101, -122.2015),
    ("anchorage-ak-2", "Fairbanks, AK", "United States", 64.8378, -147.7164),
    ("salem-or", "Salem, OR", "United States", 44.9429, -123.0351),
    ("bend-or", "Bend, OR", "United States", 44.0582, -121.3153),
    ("hilo-hi", "Hilo, HI", "United States", 19.7297, -155.0900),
    ("maui-hi", "Maui, HI", "United States", 20.7984, -156.3319),
    ("kona-hi", "Kailua-Kona, HI", "United States", 19.6400, -155.9969),
    # --- R2 expansion: additional world cities ---
    ("rotterdam", "Rotterdam", "Netherlands", 51.9244, 4.4777),
    ("hague", "The Hague", "Netherlands", 52.0705, 4.3007),
    ("utrecht", "Utrecht", "Netherlands", 52.0907, 5.1214),
    ("antwerp", "Antwerp", "Belgium", 51.2194, 4.4025),
    ("ghent", "Ghent", "Belgium", 51.0543, 3.7174),
    ("luxembourg-city", "Luxembourg City", "Luxembourg", 49.6116, 6.1319),
    ("bern", "Bern", "Switzerland", 46.9480, 7.4474),
    ("basel", "Basel", "Switzerland", 47.5596, 7.5886),
    ("lausanne", "Lausanne", "Switzerland", 46.5197, 6.6323),
    ("salzburg", "Salzburg", "Austria", 47.8095, 13.0550),
    ("innsbruck", "Innsbruck", "Austria", 47.2692, 11.4041),
    ("graz", "Graz", "Austria", 47.0707, 15.4395),
    ("nice", "Nice", "France", 43.7102, 7.2620),
    ("bordeaux", "Bordeaux", "France", 44.8378, -0.5792),
    ("strasbourg", "Strasbourg", "France", 48.5734, 7.7521),
    ("toulouse", "Toulouse", "France", 43.6047, 1.4442),
    ("cannes", "Cannes", "France", 43.5528, 7.0174),
    ("granada", "Granada", "Spain", 37.1773, -3.5986),
    ("malaga", "Málaga", "Spain", 36.7213, -4.4216),
    ("bilbao", "Bilbao", "Spain", 43.2630, -2.9350),
    ("palma", "Palma de Mallorca", "Spain", 39.5696, 2.6502),
    ("turin", "Turin", "Italy", 45.0703, 7.6869),
    ("verona", "Verona", "Italy", 45.4384, 10.9916),
    ("genoa", "Genoa", "Italy", 44.4056, 8.9463),
    ("palermo", "Palermo", "Italy", 38.1157, 13.3615),
    ("dubrovnik", "Dubrovnik", "Croatia", 42.6507, 18.0944),
    ("split", "Split", "Croatia", 43.5081, 16.4402),
    ("ljubljana", "Ljubljana", "Slovenia", 46.0569, 14.5058),
    ("bratislava", "Bratislava", "Slovakia", 48.1486, 17.1077),
    ("riga", "Riga", "Latvia", 56.9496, 24.1052),
    ("tallinn", "Tallinn", "Estonia", 59.4370, 24.7536),
    ("vilnius", "Vilnius", "Lithuania", 54.6872, 25.2797),
    ("gdansk", "Gdańsk", "Poland", 54.3520, 18.6466),
    ("wroclaw", "Wrocław", "Poland", 51.1079, 17.0385),
    ("poznan", "Poznań", "Poland", 52.4064, 16.9252),
    ("thessaloniki", "Thessaloniki", "Greece", 40.6401, 22.9444),
    ("santorini", "Santorini", "Greece", 36.3932, 25.4615),
    ("mykonos", "Mykonos", "Greece", 37.4467, 25.3289),
    ("malta-valletta", "Valletta", "Malta", 35.8989, 14.5146),
    ("nicosia", "Nicosia", "Cyprus", 35.1856, 33.3823),
    ("tbilisi", "Tbilisi", "Georgia", 41.7151, 44.8271),
    ("yerevan", "Yerevan", "Armenia", 40.1792, 44.4991),
    ("baku", "Baku", "Azerbaijan", 40.4093, 49.8671),
    ("almaty", "Almaty", "Kazakhstan", 43.2220, 76.8512),
    ("astana", "Astana", "Kazakhstan", 51.1605, 71.4704),
    ("tashkent", "Tashkent", "Uzbekistan", 41.2995, 69.2401),
    ("ulaanbaatar", "Ulaanbaatar", "Mongolia", 47.8864, 106.9057),
    ("phnom-penh", "Phnom Penh", "Cambodia", 11.5564, 104.9282),
    ("vientiane", "Vientiane", "Laos", 17.9757, 102.6331),
    ("yangon", "Yangon", "Myanmar", 16.8661, 96.1951),
    ("siem-reap", "Siem Reap", "Cambodia", 13.3671, 103.8448),
    ("chiang-mai", "Chiang Mai", "Thailand", 18.7883, 98.9853),
    ("bali", "Denpasar (Bali)", "Indonesia", -8.6500, 115.2167),
    ("yogyakarta", "Yogyakarta", "Indonesia", -7.7956, 110.3695),
    ("cebu", "Cebu City", "Philippines", 10.3157, 123.8854),
    ("davao", "Davao City", "Philippines", 7.1907, 125.4553),
    ("nagoya", "Nagoya", "Japan", 35.1815, 136.9066),
    ("fukuoka", "Fukuoka", "Japan", 33.5904, 130.4017),
    ("kobe", "Kobe", "Japan", 34.6901, 135.1955),
    ("yokohama", "Yokohama", "Japan", 35.4437, 139.6380),
    ("incheon", "Incheon", "South Korea", 37.4563, 126.7052),
    ("daegu", "Daegu", "South Korea", 35.8722, 128.6025),
    ("jeju", "Jeju City", "South Korea", 33.4996, 126.5312),
    ("macau", "Macau", "Macau", 22.1987, 113.5439),
    ("kaohsiung", "Kaohsiung", "Taiwan", 22.6273, 120.3014),
    ("taichung", "Taichung", "Taiwan", 24.1477, 120.6736),
    ("xiamen", "Xiamen", "China", 24.4798, 118.0894),
    ("hangzhou", "Hangzhou", "China", 30.2741, 120.1551),
    ("nanjing", "Nanjing", "China", 32.0603, 118.7969),
    ("suzhou", "Suzhou", "China", 31.2989, 120.5853),
    ("kunming", "Kunming", "China", 24.8801, 102.8329),
    ("lhasa", "Lhasa", "China", 29.6520, 91.1721),
    ("kolkata-in", "Hyderabad", "India", 17.3850, 78.4867),
    ("jaipur", "Jaipur", "India", 26.9124, 75.7873),
    ("varanasi", "Varanasi", "India", 25.3176, 82.9739),
    ("pune", "Pune", "India", 18.5204, 73.8567),
    ("goa", "Panaji (Goa)", "India", 15.4909, 73.8278),
    ("dhaka", "Dhaka", "Bangladesh", 23.8103, 90.4125),
    ("karachi", "Karachi", "Pakistan", 24.8607, 67.0011),
    ("lahore", "Lahore", "Pakistan", 31.5497, 74.3436),
    ("tehran", "Tehran", "Iran", 35.6892, 51.3890),
    ("amman", "Amman", "Jordan", 31.9454, 35.9284),
    ("beirut", "Beirut", "Lebanon", 33.8938, 35.5018),
    ("muscat", "Muscat", "Oman", 23.5859, 58.4059),
    ("manama", "Manama", "Bahrain", 26.2235, 50.5876),
    ("kuwait-city", "Kuwait City", "Kuwait", 29.3759, 47.9774),
    ("nairobi", "Nairobi", "Kenya", -1.2864, 36.8172),
    ("mombasa", "Mombasa", "Kenya", -4.0435, 39.6682),
    ("zanzibar", "Zanzibar City", "Tanzania", -6.1659, 39.2026),
    ("addis-ababa", "Addis Ababa", "Ethiopia", 9.0320, 38.7469),
    ("accra", "Accra", "Ghana", 5.6037, -0.1870),
    ("lagos", "Lagos", "Nigeria", 6.5244, 3.3792),
    ("dakar", "Dakar", "Senegal", 14.7167, -17.4677),
    ("tunis", "Tunis", "Tunisia", 36.8065, 10.1815),
    ("algiers", "Algiers", "Algeria", 36.7538, 3.0588),
    ("casablanca", "Casablanca", "Morocco", 33.5731, -7.5898),
    ("fes", "Fes", "Morocco", 34.0181, -5.0078),
    ("durban", "Durban", "South Africa", -29.8587, 31.0218),
    ("victoria-falls", "Victoria Falls", "Zimbabwe", -17.9243, 25.8572),
    ("luanda", "Luanda", "Angola", -8.8390, 13.2894),
    ("antananarivo", "Antananarivo", "Madagascar", -18.8792, 47.5079),
    ("port-louis", "Port Louis", "Mauritius", -20.1640, 57.5031),
    ("port-of-spain", "Port of Spain", "Trinidad", 10.6549, -61.5019),
    ("kingston-jm", "Kingston", "Jamaica", 17.9712, -76.7929),
    ("nassau", "Nassau", "Bahamas", 25.0343, -77.3963),
    ("panama-city", "Panama City", "Panama", 8.9824, -79.5199),
    ("san-jose-cr", "San José", "Costa Rica", 9.9281, -84.0907),
    ("medellin", "Medellín", "Colombia", 6.2476, -75.5709),
    ("cartagena", "Cartagena", "Colombia", 10.3910, -75.4794),
    ("guayaquil", "Guayaquil", "Ecuador", -2.1709, -79.9224),
    ("la-paz", "La Paz", "Bolivia", -16.4897, -68.1193),
    ("asuncion", "Asunción", "Paraguay", -25.2637, -57.5759),
    ("montevideo", "Montevideo", "Uruguay", -34.9011, -56.1645),
    ("salvador-br", "Salvador", "Brazil", -12.9714, -38.5014),
    ("sao-paulo", "São Paulo", "Brazil", -23.5505, -46.6333),
    ("recife", "Recife", "Brazil", -8.0476, -34.8770),
    ("manaus", "Manaus", "Brazil", -3.1190, -60.0217),
    ("curitiba", "Curitiba", "Brazil", -25.4284, -49.2733),
    ("cuzco", "Cusco", "Peru", -13.5320, -71.9675),
    ("ushuaia", "Ushuaia", "Argentina", -54.8019, -68.3030),
    ("queenstown", "Queenstown", "New Zealand", -45.0312, 168.6626),
    ("hobart", "Hobart", "Australia", -42.8821, 147.3272),
    ("darwin", "Darwin", "Australia", -12.4634, 130.8456),
    ("adelaide", "Adelaide", "Australia", -34.9285, 138.6007),
    ("gold-coast", "Gold Coast", "Australia", -28.0167, 153.4000),
    ("cairns", "Cairns", "Australia", -16.9186, 145.7781),
    ("guam", "Hagåtña", "Guam", 13.4745, 144.7504),
    ("apia", "Apia", "Samoa", -13.8333, -171.7667),
    ("nuuk", "Nuuk", "Greenland", 64.1814, -51.6941),
    # --- R3 expansion: additional 400 worldwide cities ---
    # USA additional metros
    ("buffalo-ny", "Buffalo, NY", "United States", 42.8864, -78.8784),
    ("rochester-ny", "Rochester, NY", "United States", 43.1566, -77.6088),
    ("syracuse-ny", "Syracuse, NY", "United States", 43.0481, -76.1474),
    ("albany-ny", "Albany, NY", "United States", 42.6526, -73.7562),
    ("yonkers-ny", "Yonkers, NY", "United States", 40.9312, -73.8987),
    ("jersey-city-nj", "Jersey City, NJ", "United States", 40.7178, -74.0431),
    ("newark-nj", "Newark, NJ", "United States", 40.7357, -74.1724),
    ("paterson-nj", "Paterson, NJ", "United States", 40.9168, -74.1718),
    ("trenton-nj", "Trenton, NJ", "United States", 40.2206, -74.7597),
    ("camden-nj", "Camden, NJ", "United States", 39.9259, -75.1196),
    ("hartford-ct", "Hartford, CT", "United States", 41.7658, -72.6734),
    ("new-haven-ct", "New Haven, CT", "United States", 41.3083, -72.9279),
    ("stamford-ct", "Stamford, CT", "United States", 41.0534, -73.5387),
    ("bridgeport-ct", "Bridgeport, CT", "United States", 41.1865, -73.1952),
    ("providence-ri", "Providence, RI", "United States", 41.8240, -71.4128),
    ("worcester-ma", "Worcester, MA", "United States", 42.2626, -71.8023),
    ("springfield-ma", "Springfield, MA", "United States", 42.1015, -72.5898),
    ("cambridge-ma", "Cambridge, MA", "United States", 42.3736, -71.1097),
    ("lowell-ma", "Lowell, MA", "United States", 42.6334, -71.3162),
    ("manchester-nh", "Manchester, NH", "United States", 42.9956, -71.4548),
    ("concord-nh", "Concord, NH", "United States", 43.2081, -71.5376),
    ("portland-me", "Portland, ME", "United States", 43.6591, -70.2568),
    ("bangor-me", "Bangor, ME", "United States", 44.8016, -68.7712),
    ("burlington-vt", "Burlington, VT", "United States", 44.4759, -73.2121),
    ("montpelier-vt", "Montpelier, VT", "United States", 44.2601, -72.5754),
    ("wilmington-de", "Wilmington, DE", "United States", 39.7391, -75.5398),
    ("dover-de", "Dover, DE", "United States", 39.1582, -75.5244),
    ("annapolis-md", "Annapolis, MD", "United States", 38.9784, -76.4922),
    ("frederick-md", "Frederick, MD", "United States", 39.4143, -77.4105),
    ("rockville-md", "Rockville, MD", "United States", 39.0840, -77.1528),
    ("alexandria-va", "Alexandria, VA", "United States", 38.8048, -77.0469),
    ("richmond-va", "Richmond, VA", "United States", 37.5407, -77.4360),
    ("norfolk-va", "Norfolk, VA", "United States", 36.8508, -76.2859),
    ("virginia-beach-va", "Virginia Beach, VA", "United States", 36.8529, -75.9780),
    ("chesapeake-va", "Chesapeake, VA", "United States", 36.7682, -76.2875),
    ("roanoke-va", "Roanoke, VA", "United States", 37.2710, -79.9414),
    ("charleston-wv", "Charleston, WV", "United States", 38.3498, -81.6326),
    ("morgantown-wv", "Morgantown, WV", "United States", 39.6295, -79.9559),
    ("charlotte-nc", "Charlotte, NC", "United States", 35.2271, -80.8431),
    ("fayetteville-nc", "Fayetteville, NC", "United States", 35.0527, -78.8784),
    ("asheville-nc", "Asheville, NC", "United States", 35.5951, -82.5515),
    ("cary-nc", "Cary, NC", "United States", 35.7915, -78.7811),
    ("columbia-sc", "Columbia, SC", "United States", 34.0007, -81.0348),
    ("charleston-sc", "Charleston, SC", "United States", 32.7765, -79.9311),
    ("savannah-ga", "Savannah, GA", "United States", 32.0809, -81.0912),
    ("macon-ga", "Macon, GA", "United States", 32.8407, -83.6324),
    ("columbus-ga", "Columbus, GA", "United States", 32.4610, -84.9877),
    ("tallahassee-fl", "Tallahassee, FL", "United States", 30.4383, -84.2807),
    ("jacksonville-fl", "Jacksonville, FL", "United States", 30.3322, -81.6557),
    ("tampa-fl", "Tampa, FL", "United States", 27.9506, -82.4572),
    ("gainesville-fl", "Gainesville, FL", "United States", 29.6516, -82.3248),
    ("fort-myers-fl", "Fort Myers, FL", "United States", 26.6406, -81.8723),
    ("daytona-beach-fl", "Daytona Beach, FL", "United States", 29.2108, -81.0228),
    ("pensacola-fl", "Pensacola, FL", "United States", 30.4213, -87.2169),
    ("mobile-al", "Mobile, AL", "United States", 30.6954, -88.0399),
    ("montgomery-al", "Montgomery, AL", "United States", 32.3792, -86.3077),
    ("huntsville-al", "Huntsville, AL", "United States", 34.7304, -86.5861),
    ("birmingham-al", "Birmingham, AL", "United States", 33.5186, -86.8104),
    ("tuscaloosa-al", "Tuscaloosa, AL", "United States", 33.2098, -87.5692),
    ("jackson-ms", "Jackson, MS", "United States", 32.2988, -90.1848),
    ("biloxi-ms", "Biloxi, MS", "United States", 30.3960, -88.8853),
    ("tupelo-ms", "Tupelo, MS", "United States", 34.2576, -88.7034),
    ("baton-rouge-la", "Baton Rouge, LA", "United States", 30.4515, -91.1871),
    ("shreveport-la", "Shreveport, LA", "United States", 32.5252, -93.7502),
    ("lafayette-la", "Lafayette, LA", "United States", 30.2241, -92.0198),
    ("little-rock-ar", "Little Rock, AR", "United States", 34.7465, -92.2896),
    ("fort-smith-ar", "Fort Smith, AR", "United States", 35.3859, -94.3985),
    ("memphis-tn", "Memphis, TN", "United States", 35.1495, -90.0490),
    ("knoxville-tn", "Knoxville, TN", "United States", 35.9606, -83.9207),
    ("chattanooga-tn", "Chattanooga, TN", "United States", 35.0456, -85.3097),
    ("clarksville-tn", "Clarksville, TN", "United States", 36.5298, -87.3595),
    ("franklin-tn", "Franklin, TN", "United States", 35.9251, -86.8689),
    ("frankfort-ky", "Frankfort, KY", "United States", 38.2009, -84.8733),
    ("bowling-green-ky", "Bowling Green, KY", "United States", 36.9685, -86.4808),
    ("evansville-in", "Evansville, IN", "United States", 37.9716, -87.5711),
    ("south-bend-in", "South Bend, IN", "United States", 41.6764, -86.2520),
    ("indianapolis-in", "Indianapolis, IN", "United States", 39.7684, -86.1581),
    ("rockford-il", "Rockford, IL", "United States", 42.2711, -89.0940),
    ("peoria-il", "Peoria, IL", "United States", 40.6936, -89.5890),
    ("springfield-il", "Springfield, IL", "United States", 39.7817, -89.6501),
    ("naperville-il", "Naperville, IL", "United States", 41.7508, -88.1535),
    ("aurora-il", "Aurora, IL", "United States", 41.7606, -88.3201),
    ("madison-wi", "Madison, WI", "United States", 43.0731, -89.4012),
    ("milwaukee-wi", "Milwaukee, WI", "United States", 43.0389, -87.9065),
    ("green-bay-wi", "Green Bay, WI", "United States", 44.5133, -88.0133),
    ("appleton-wi", "Appleton, WI", "United States", 44.2619, -88.4154),
    ("kenosha-wi", "Kenosha, WI", "United States", 42.5847, -87.8212),
    ("duluth-mn", "Duluth, MN", "United States", 46.7867, -92.1005),
    ("rochester-mn", "Rochester, MN", "United States", 44.0121, -92.4802),
    ("st-paul-mn", "St. Paul, MN", "United States", 44.9537, -93.0900),
    ("bloomington-mn", "Bloomington, MN", "United States", 44.8408, -93.2983),
    ("des-moines-ia", "Des Moines, IA", "United States", 41.5868, -93.6250),
    ("cedar-rapids-ia", "Cedar Rapids, IA", "United States", 41.9779, -91.6656),
    ("iowa-city-ia", "Iowa City, IA", "United States", 41.6611, -91.5302),
    ("omaha-ne", "Omaha, NE", "United States", 41.2565, -95.9345),
    ("lincoln-ne", "Lincoln, NE", "United States", 40.8136, -96.7026),
    ("kansas-city-mo", "Kansas City, MO", "United States", 39.0997, -94.5786),
    ("springfield-mo", "Springfield, MO", "United States", 37.2089, -93.2923),
    ("st-joseph-mo", "St. Joseph, MO", "United States", 39.7675, -94.8467),
    ("overland-park-ks", "Overland Park, KS", "United States", 38.9822, -94.6708),
    ("lawrence-ks", "Lawrence, KS", "United States", 38.9717, -95.2353),
    ("manhattan-ks", "Manhattan, KS", "United States", 39.1836, -96.5717),
    ("oklahoma-city-ok", "Oklahoma City, OK", "United States", 35.4676, -97.5164),
    ("tulsa-ok", "Tulsa, OK", "United States", 36.1540, -95.9928),
    ("norman-ok", "Norman, OK", "United States", 35.2226, -97.4395),
    ("salt-lake-city-ut", "Salt Lake City, UT", "United States", 40.7608, -111.8910),
    ("provo-ut", "Provo, UT", "United States", 40.2338, -111.6585),
    ("ogden-ut", "Ogden, UT", "United States", 41.2230, -111.9738),
    ("st-george-ut", "St. George, UT", "United States", 37.0965, -113.5684),
    ("logan-ut", "Logan, UT", "United States", 41.7370, -111.8338),
    ("colorado-springs-co", "Colorado Springs, CO", "United States", 38.8339, -104.8214),
    ("boulder-co", "Boulder, CO", "United States", 40.0150, -105.2705),
    ("pueblo-co", "Pueblo, CO", "United States", 38.2544, -104.6091),
    ("santa-fe-nm", "Santa Fe, NM", "United States", 35.6870, -105.9378),
    ("albuquerque-nm", "Albuquerque, NM", "United States", 35.0844, -106.6504),
    ("las-cruces-nm", "Las Cruces, NM", "United States", 32.3199, -106.7637),
    ("boise-id", "Boise, ID", "United States", 43.6150, -116.2023),
    ("nampa-id", "Nampa, ID", "United States", 43.5407, -116.5635),
    ("coeur-dalene-id", "Coeur d'Alene, ID", "United States", 47.6777, -116.7805),
    ("vancouver-wa", "Vancouver, WA", "United States", 45.6387, -122.6615),
    ("eugene-or", "Eugene, OR", "United States", 44.0521, -123.0868),
    ("medford-or", "Medford, OR", "United States", 42.3265, -122.8756),
    ("anchorage-ak", "Anchorage, AK", "United States", 61.2181, -149.9003),
    ("juneau-ak", "Juneau, AK", "United States", 58.3019, -134.4197),
    ("fairbanks-ak-x", "Fairbanks, AK (City)", "United States", 64.8378, -147.7164),
    ("honolulu-hi", "Honolulu, HI", "United States", 21.3099, -157.8581),
    ("kahului-hi", "Kahului, HI", "United States", 20.8893, -156.4729),
    ("reno-nv", "Reno, NV", "United States", 39.5296, -119.8138),
    ("henderson-nv", "Henderson, NV", "United States", 36.0395, -114.9817),
    ("carson-city-nv", "Carson City, NV", "United States", 39.1638, -119.7674),
    ("billings-mt-x", "Billings, MT (Metro)", "United States", 45.7833, -108.5007),
    ("great-falls-mt", "Great Falls, MT", "United States", 47.5053, -111.3008),
    ("helena-mt", "Helena, MT", "United States", 46.5891, -112.0391),
    ("casper-wy", "Casper, WY", "United States", 42.8501, -106.3253),
    ("laramie-wy", "Laramie, WY", "United States", 41.3114, -105.5911),
    # World major - Asia
    ("guangzhou", "Guangzhou", "China", 23.1291, 113.2644),
    ("shenzhen", "Shenzhen", "China", 22.5431, 114.0579),
    ("chongqing", "Chongqing", "China", 29.4316, 106.9123),
    ("chengdu", "Chengdu", "China", 30.5728, 104.0668),
    ("wuhan", "Wuhan", "China", 30.5928, 114.3055),
    ("tianjin", "Tianjin", "China", 39.3434, 117.3616),
    ("xi-an", "Xi'an", "China", 34.3416, 108.9398),
    ("dalian", "Dalian", "China", 38.9140, 121.6147),
    ("qingdao", "Qingdao", "China", 36.0671, 120.3826),
    ("sanya", "Sanya", "China", 18.2528, 109.5119),
    ("changsha", "Changsha", "China", 28.2282, 112.9388),
    ("shenyang", "Shenyang", "China", 41.8057, 123.4315),
    ("zhuhai", "Zhuhai", "China", 22.2710, 113.5767),
    ("kyoto", "Kyoto", "Japan", 35.0116, 135.7681),
    ("sapporo", "Sapporo", "Japan", 43.0618, 141.3545),
    ("hiroshima", "Hiroshima", "Japan", 34.3853, 132.4553),
    ("nara", "Nara", "Japan", 34.6851, 135.8048),
    ("kanazawa", "Kanazawa", "Japan", 36.5613, 136.6562),
    ("sendai", "Sendai", "Japan", 38.2682, 140.8694),
    ("naha", "Naha", "Japan", 26.2123, 127.6791),
    ("busan", "Busan", "South Korea", 35.1796, 129.0756),
    ("gwangju", "Gwangju", "South Korea", 35.1595, 126.8526),
    ("daejeon", "Daejeon", "South Korea", 36.3504, 127.3845),
    ("ulsan", "Ulsan", "South Korea", 35.5384, 129.3114),
    ("hanoi", "Hanoi", "Vietnam", 21.0285, 105.8542),
    ("ho-chi-minh-city", "Ho Chi Minh City", "Vietnam", 10.8231, 106.6297),
    ("da-nang", "Da Nang", "Vietnam", 16.0544, 108.2022),
    ("hue", "Hue", "Vietnam", 16.4637, 107.5909),
    ("hoi-an", "Hoi An", "Vietnam", 15.8801, 108.3380),
    ("bangkok", "Bangkok", "Thailand", 13.7563, 100.5018),
    ("phuket", "Phuket", "Thailand", 7.8804, 98.3923),
    ("pattaya", "Pattaya", "Thailand", 12.9236, 100.8825),
    ("krabi", "Krabi", "Thailand", 8.0863, 98.9063),
    ("kuala-lumpur", "Kuala Lumpur", "Malaysia", 3.1390, 101.6869),
    ("penang", "George Town (Penang)", "Malaysia", 5.4141, 100.3288),
    ("johor-bahru", "Johor Bahru", "Malaysia", 1.4927, 103.7414),
    ("kota-kinabalu", "Kota Kinabalu", "Malaysia", 5.9804, 116.0735),
    ("kuching", "Kuching", "Malaysia", 1.5535, 110.3593),
    ("jakarta", "Jakarta", "Indonesia", -6.2088, 106.8456),
    ("surabaya", "Surabaya", "Indonesia", -7.2575, 112.7521),
    ("bandung", "Bandung", "Indonesia", -6.9175, 107.6191),
    ("medan", "Medan", "Indonesia", 3.5952, 98.6722),
    ("manila", "Manila", "Philippines", 14.5995, 120.9842),
    ("quezon-city", "Quezon City", "Philippines", 14.6760, 121.0437),
    ("boracay", "Boracay", "Philippines", 11.9674, 121.9248),
    ("baguio", "Baguio", "Philippines", 16.4023, 120.5960),
    ("colombo", "Colombo", "Sri Lanka", 6.9271, 79.8612),
    ("kandy", "Kandy", "Sri Lanka", 7.2906, 80.6337),
    ("delhi", "New Delhi", "India", 28.6139, 77.2090),
    ("mumbai", "Mumbai", "India", 19.0760, 72.8777),
    ("bangalore", "Bangalore", "India", 12.9716, 77.5946),
    ("chennai", "Chennai", "India", 13.0827, 80.2707),
    ("kolkata", "Kolkata", "India", 22.5726, 88.3639),
    ("agra", "Agra", "India", 27.1767, 78.0081),
    ("udaipur", "Udaipur", "India", 24.5854, 73.7125),
    ("kochi", "Kochi", "India", 9.9312, 76.2673),
    ("ahmedabad", "Ahmedabad", "India", 23.0225, 72.5714),
    ("kathmandu", "Kathmandu", "Nepal", 27.7172, 85.3240),
    ("pokhara", "Pokhara", "Nepal", 28.2096, 83.9856),
    ("thimphu", "Thimphu", "Bhutan", 27.4728, 89.6390),
    ("male", "Malé", "Maldives", 4.1755, 73.5093),
    ("doha", "Doha", "Qatar", 25.2854, 51.5310),
    ("riyadh", "Riyadh", "Saudi Arabia", 24.7136, 46.6753),
    ("jeddah", "Jeddah", "Saudi Arabia", 21.4858, 39.1925),
    ("mecca", "Mecca", "Saudi Arabia", 21.3891, 39.8579),
    ("dubai-2", "Dubai", "United Arab Emirates", 25.2048, 55.2708),
    ("abu-dhabi", "Abu Dhabi", "United Arab Emirates", 24.4539, 54.3773),
    ("sharjah", "Sharjah", "United Arab Emirates", 25.3463, 55.4209),
    ("istanbul-2", "Istanbul", "Turkey", 41.0082, 28.9784),
    ("ankara", "Ankara", "Turkey", 39.9334, 32.8597),
    ("izmir", "Izmir", "Turkey", 38.4192, 27.1287),
    ("antalya", "Antalya", "Turkey", 36.8969, 30.7133),
    ("cappadocia", "Göreme (Cappadocia)", "Turkey", 38.6431, 34.8289),
    # World - Europe
    ("manchester-uk", "Manchester", "United Kingdom", 53.4808, -2.2426),
    ("birmingham-uk", "Birmingham", "United Kingdom", 52.4862, -1.8904),
    ("liverpool-uk", "Liverpool", "United Kingdom", 53.4084, -2.9916),
    ("leeds-uk", "Leeds", "United Kingdom", 53.8008, -1.5491),
    ("glasgow-uk", "Glasgow", "United Kingdom", 55.8642, -4.2518),
    ("edinburgh-uk", "Edinburgh", "United Kingdom", 55.9533, -3.1883),
    ("cardiff-uk", "Cardiff", "United Kingdom", 51.4816, -3.1791),
    ("belfast-uk", "Belfast", "United Kingdom", 54.5973, -5.9301),
    ("oxford-uk", "Oxford", "United Kingdom", 51.7520, -1.2577),
    ("cambridge-uk", "Cambridge", "United Kingdom", 52.2053, 0.1218),
    ("brighton-uk", "Brighton", "United Kingdom", 50.8225, -0.1372),
    ("york-uk", "York", "United Kingdom", 53.9590, -1.0815),
    ("bath-uk", "Bath", "United Kingdom", 51.3811, -2.3590),
    ("dublin-2", "Dublin", "Ireland", 53.3498, -6.2603),
    ("cork-ie", "Cork", "Ireland", 51.8985, -8.4756),
    ("galway-ie", "Galway", "Ireland", 53.2707, -9.0568),
    ("lyon", "Lyon", "France", 45.7640, 4.8357),
    ("marseille", "Marseille", "France", 43.2965, 5.3698),
    ("lille", "Lille", "France", 50.6292, 3.0573),
    ("nantes", "Nantes", "France", 47.2184, -1.5536),
    ("rennes", "Rennes", "France", 48.1173, -1.6778),
    ("montpellier", "Montpellier", "France", 43.6108, 3.8767),
    ("avignon", "Avignon", "France", 43.9493, 4.8055),
    ("hamburg", "Hamburg", "Germany", 53.5511, 9.9937),
    ("munich", "Munich", "Germany", 48.1351, 11.5820),
    ("cologne", "Cologne", "Germany", 50.9375, 6.9603),
    ("frankfurt", "Frankfurt", "Germany", 50.1109, 8.6821),
    ("stuttgart", "Stuttgart", "Germany", 48.7758, 9.1829),
    ("dresden", "Dresden", "Germany", 51.0504, 13.7373),
    ("nuremberg", "Nuremberg", "Germany", 49.4521, 11.0767),
    ("hannover", "Hannover", "Germany", 52.3759, 9.7320),
    ("milan", "Milan", "Italy", 45.4642, 9.1900),
    ("naples", "Naples", "Italy", 40.8518, 14.2681),
    ("florence", "Florence", "Italy", 43.7696, 11.2558),
    ("venice", "Venice", "Italy", 45.4408, 12.3155),
    ("bologna", "Bologna", "Italy", 44.4949, 11.3426),
    ("siena", "Siena", "Italy", 43.3188, 11.3308),
    ("pisa", "Pisa", "Italy", 43.7228, 10.4017),
    ("cinque-terre", "Cinque Terre", "Italy", 44.1257, 9.7080),
    ("madrid-2", "Madrid", "Spain", 40.4168, -3.7038),
    ("seville", "Seville", "Spain", 37.3886, -5.9823),
    ("valencia", "Valencia", "Spain", 39.4699, -0.3763),
    ("zaragoza", "Zaragoza", "Spain", 41.6488, -0.8891),
    ("santiago-de-compostela", "Santiago de Compostela", "Spain", 42.8782, -8.5448),
    ("porto", "Porto", "Portugal", 41.1579, -8.6291),
    ("lisbon-2", "Lisbon", "Portugal", 38.7223, -9.1393),
    ("faro-pt", "Faro", "Portugal", 37.0194, -7.9304),
    ("vienna-2", "Vienna", "Austria", 48.2082, 16.3738),
    ("zurich", "Zurich", "Switzerland", 47.3769, 8.5417),
    ("geneva", "Geneva", "Switzerland", 46.2044, 6.1432),
    ("interlaken", "Interlaken", "Switzerland", 46.6863, 7.8632),
    ("zermatt", "Zermatt", "Switzerland", 46.0207, 7.7491),
    ("oslo-2", "Oslo", "Norway", 59.9139, 10.7522),
    ("bergen", "Bergen", "Norway", 60.3913, 5.3221),
    ("tromso", "Tromsø", "Norway", 69.6492, 18.9553),
    ("stavanger", "Stavanger", "Norway", 58.9700, 5.7331),
    ("stockholm-2", "Stockholm", "Sweden", 59.3293, 18.0686),
    ("gothenburg", "Gothenburg", "Sweden", 57.7089, 11.9746),
    ("malmo", "Malmö", "Sweden", 55.6050, 13.0038),
    ("copenhagen-2", "Copenhagen", "Denmark", 55.6761, 12.5683),
    ("aarhus", "Aarhus", "Denmark", 56.1629, 10.2039),
    ("odense", "Odense", "Denmark", 55.4038, 10.4024),
    ("helsinki-2", "Helsinki", "Finland", 60.1699, 24.9384),
    ("tampere", "Tampere", "Finland", 61.4978, 23.7610),
    ("rovaniemi", "Rovaniemi", "Finland", 66.5039, 25.7294),
    ("reykjavik-2", "Reykjavik", "Iceland", 64.1466, -21.9426),
    ("warsaw", "Warsaw", "Poland", 52.2297, 21.0122),
    ("krakow", "Kraków", "Poland", 50.0647, 19.9450),
    ("prague", "Prague", "Czech Republic", 50.0755, 14.4378),
    ("brno", "Brno", "Czech Republic", 49.1951, 16.6068),
    ("budapest", "Budapest", "Hungary", 47.4979, 19.0402),
    ("debrecen", "Debrecen", "Hungary", 47.5316, 21.6273),
    ("bucharest", "Bucharest", "Romania", 44.4268, 26.1025),
    ("brasov", "Brașov", "Romania", 45.6427, 25.5887),
    ("sofia", "Sofia", "Bulgaria", 42.6977, 23.3219),
    ("plovdiv", "Plovdiv", "Bulgaria", 42.1354, 24.7453),
    ("belgrade", "Belgrade", "Serbia", 44.7866, 20.4489),
    ("zagreb", "Zagreb", "Croatia", 45.8150, 15.9819),
    ("sarajevo", "Sarajevo", "Bosnia and Herzegovina", 43.8563, 18.4131),
    ("skopje", "Skopje", "North Macedonia", 41.9981, 21.4254),
    ("tirana", "Tirana", "Albania", 41.3275, 19.8187),
    ("athens-2", "Athens", "Greece", 37.9838, 23.7275),
    ("crete-heraklion", "Heraklion (Crete)", "Greece", 35.3387, 25.1442),
    ("rhodes", "Rhodes", "Greece", 36.4341, 28.2176),
    ("moscow-2", "Moscow", "Russia", 55.7558, 37.6173),
    ("st-petersburg-ru", "Saint Petersburg", "Russia", 59.9311, 30.3609),
    ("kyiv", "Kyiv", "Ukraine", 50.4501, 30.5234),
    ("lviv", "Lviv", "Ukraine", 49.8397, 24.0297),
    ("minsk", "Minsk", "Belarus", 53.9006, 27.5590),
    # World - Africa
    ("cairo-2", "Cairo", "Egypt", 30.0444, 31.2357),
    ("alexandria-eg", "Alexandria", "Egypt", 31.2001, 29.9187),
    ("luxor", "Luxor", "Egypt", 25.6872, 32.6396),
    ("aswan", "Aswan", "Egypt", 24.0889, 32.8998),
    ("sharm-el-sheikh", "Sharm El Sheikh", "Egypt", 27.9158, 34.3300),
    ("marrakech", "Marrakech", "Morocco", 31.6295, -7.9811),
    ("tangier", "Tangier", "Morocco", 35.7595, -5.8340),
    ("rabat", "Rabat", "Morocco", 34.0209, -6.8416),
    ("johannesburg-2", "Johannesburg", "South Africa", -26.2041, 28.0473),
    ("cape-town-2", "Cape Town", "South Africa", -33.9249, 18.4241),
    ("pretoria", "Pretoria", "South Africa", -25.7479, 28.2293),
    ("port-elizabeth", "Gqeberha (Port Elizabeth)", "South Africa", -33.9608, 25.6022),
    ("addis-2", "Addis Ababa (Bole)", "Ethiopia", 8.9806, 38.7578),
    ("kampala", "Kampala", "Uganda", 0.3476, 32.5825),
    ("kigali", "Kigali", "Rwanda", -1.9706, 30.1044),
    ("dar-es-salaam", "Dar es Salaam", "Tanzania", -6.7924, 39.2083),
    ("arusha", "Arusha", "Tanzania", -3.3869, 36.6830),
    ("windhoek", "Windhoek", "Namibia", -22.5609, 17.0658),
    ("livingstone", "Livingstone", "Zambia", -17.8419, 25.8543),
    ("maputo", "Maputo", "Mozambique", -25.9692, 32.5732),
    ("abuja", "Abuja", "Nigeria", 9.0765, 7.3986),
    ("ibadan", "Ibadan", "Nigeria", 7.3775, 3.9470),
    # World - Latin America
    ("mexico-city-2", "Mexico City", "Mexico", 19.4326, -99.1332),
    ("guadalajara", "Guadalajara", "Mexico", 20.6597, -103.3496),
    ("monterrey", "Monterrey", "Mexico", 25.6866, -100.3161),
    ("puebla", "Puebla", "Mexico", 19.0414, -98.2063),
    ("cancun", "Cancún", "Mexico", 21.1619, -86.8515),
    ("playa-del-carmen", "Playa del Carmen", "Mexico", 20.6296, -87.0739),
    ("tulum", "Tulum", "Mexico", 20.2114, -87.4654),
    ("oaxaca", "Oaxaca", "Mexico", 17.0732, -96.7266),
    ("merida-mx", "Mérida", "Mexico", 20.9674, -89.5926),
    ("tijuana", "Tijuana", "Mexico", 32.5149, -117.0382),
    ("san-miguel-de-allende", "San Miguel de Allende", "Mexico", 20.9144, -100.7459),
    ("guatemala-city", "Guatemala City", "Guatemala", 14.6349, -90.5069),
    ("antigua-gt", "Antigua Guatemala", "Guatemala", 14.5586, -90.7339),
    ("san-salvador", "San Salvador", "El Salvador", 13.6929, -89.2182),
    ("tegucigalpa", "Tegucigalpa", "Honduras", 14.0723, -87.1921),
    ("managua", "Managua", "Nicaragua", 12.1149, -86.2362),
    ("san-juan-pr", "San Juan", "Puerto Rico", 18.4655, -66.1057),
    ("santo-domingo", "Santo Domingo", "Dominican Republic", 18.4861, -69.9312),
    ("punta-cana", "Punta Cana", "Dominican Republic", 18.5601, -68.3725),
    ("havana", "Havana", "Cuba", 23.1136, -82.3666),
    ("santiago-de-cuba", "Santiago de Cuba", "Cuba", 20.0247, -75.8219),
    ("bogota", "Bogotá", "Colombia", 4.7110, -74.0721),
    ("cali", "Cali", "Colombia", 3.4516, -76.5320),
    ("quito", "Quito", "Ecuador", -0.1807, -78.4678),
    ("lima-2", "Lima", "Peru", -12.0464, -77.0428),
    ("arequipa", "Arequipa", "Peru", -16.4090, -71.5375),
    ("santiago-cl", "Santiago", "Chile", -33.4489, -70.6693),
    ("valparaiso-cl", "Valparaíso", "Chile", -33.0472, -71.6127),
    ("buenos-aires-2", "Buenos Aires", "Argentina", -34.6037, -58.3816),
    ("mendoza-ar", "Mendoza", "Argentina", -32.8895, -68.8458),
    ("bariloche", "San Carlos de Bariloche", "Argentina", -41.1335, -71.3103),
    ("rio-de-janeiro", "Rio de Janeiro", "Brazil", -22.9068, -43.1729),
    ("brasilia", "Brasília", "Brazil", -15.8267, -47.9218),
    ("fortaleza-br", "Fortaleza", "Brazil", -3.7172, -38.5433),
    ("belo-horizonte", "Belo Horizonte", "Brazil", -19.9167, -43.9345),
    ("florianopolis", "Florianópolis", "Brazil", -27.5949, -48.5482),
    # Oceania
    ("sydney-2", "Sydney", "Australia", -33.8688, 151.2093),
    ("melbourne-2", "Melbourne", "Australia", -37.8136, 144.9631),
    ("brisbane-2", "Brisbane", "Australia", -27.4705, 153.0260),
    ("perth-2", "Perth", "Australia", -31.9505, 115.8605),
    ("canberra", "Canberra", "Australia", -35.2809, 149.1300),
    ("newcastle-au", "Newcastle, NSW", "Australia", -32.9283, 151.7817),
    ("wellington-2", "Wellington", "New Zealand", -41.2865, 174.7762),
    ("auckland-2", "Auckland", "New Zealand", -36.8485, 174.7633),
    ("christchurch-2", "Christchurch", "New Zealand", -43.5320, 172.6362),
    ("rotorua", "Rotorua", "New Zealand", -38.1368, 176.2497),
    ("nadi-fj", "Nadi", "Fiji", -17.7765, 177.4356),
    ("suva-fj", "Suva", "Fiji", -18.1248, 178.4501),
    ("port-vila", "Port Vila", "Vanuatu", -17.7334, 168.3273),
    ("noumea", "Nouméa", "New Caledonia", -22.2735, 166.4574),
    ("papeete", "Papeete", "French Polynesia", -17.5516, -149.5585),
    # Canada additional
    ("montreal-2", "Montreal", "Canada", 45.5017, -73.5673),
    ("vancouver-2", "Vancouver", "Canada", 49.2827, -123.1207),
    ("calgary-2", "Calgary", "Canada", 51.0447, -114.0719),
    ("edmonton-2", "Edmonton", "Canada", 53.5461, -113.4938),
    ("ottawa-2", "Ottawa", "Canada", 45.4215, -75.6972),
    ("quebec-city-2", "Quebec City", "Canada", 46.8139, -71.2080),
    ("winnipeg-2", "Winnipeg", "Canada", 49.8951, -97.1384),
    ("halifax-2", "Halifax", "Canada", 44.6488, -63.5752),
    ("st-johns-2", "St. John's", "Canada", 47.5615, -52.7126),
    ("victoria-bc-2", "Victoria, BC", "Canada", 48.4284, -123.3656),
    ("whistler-2", "Whistler, BC", "Canada", 50.1163, -122.9574),
    ("banff-2", "Banff, AB", "Canada", 51.1784, -115.5708),
    ("niagara-falls", "Niagara Falls, ON", "Canada", 43.0896, -79.0849),
    # Misc smaller
    ("greenwich-uk", "Greenwich (London)", "United Kingdom", 51.4826, -0.0077),
    ("canterbury-uk", "Canterbury", "United Kingdom", 51.2802, 1.0789),
    ("inverness-uk", "Inverness", "United Kingdom", 57.4778, -4.2247),
    ("stratford-upon-avon", "Stratford-upon-Avon", "United Kingdom", 52.1917, -1.7073),
    ("st-andrews", "St Andrews", "United Kingdom", 56.3398, -2.7967),
    ("aberdeen", "Aberdeen", "United Kingdom", 57.1497, -2.0943),
    ("plymouth-uk", "Plymouth", "United Kingdom", 50.3755, -4.1427),
    ("southampton-uk", "Southampton", "United Kingdom", 50.9097, -1.4044),
    ("portsmouth-uk", "Portsmouth", "United Kingdom", 50.8198, -1.0880),
    ("derry-uk", "Derry", "United Kingdom", 54.9966, -7.3086),
    ("yongin", "Yongin", "South Korea", 37.2411, 127.1776),
    ("suwon", "Suwon", "South Korea", 37.2636, 127.0286),
    ("changchun", "Changchun", "China", 43.8171, 125.3235),
    ("harbin", "Harbin", "China", 45.8038, 126.5350),
    ("urumqi", "Ürümqi", "China", 43.8256, 87.6168),
    ("guilin", "Guilin", "China", 25.2342, 110.1799),
    ("yiwu", "Yiwu", "China", 29.3050, 120.0760),
    ("wenzhou", "Wenzhou", "China", 27.9938, 120.6691),
    ("fuzhou", "Fuzhou", "China", 26.0745, 119.2965),
    ("ningbo", "Ningbo", "China", 29.8683, 121.5440),
    ("haikou", "Haikou", "China", 20.0440, 110.1999),
    ("hohhot", "Hohhot", "China", 40.8424, 111.7491),
    ("yinchuan", "Yinchuan", "China", 38.4872, 106.2309),
    ("lanzhou", "Lanzhou", "China", 36.0611, 103.8343),
    ("xining", "Xining", "China", 36.6230, 101.7800),
    ("baotou", "Baotou", "China", 40.6577, 109.8403),
    ("zhengzhou", "Zhengzhou", "China", 34.7466, 113.6253),
    ("hefei", "Hefei", "China", 31.8206, 117.2272),
    ("nanchang", "Nanchang", "China", 28.6820, 115.8579),
    ("nanning", "Nanning", "China", 22.8170, 108.3669),
    ("taiyuan", "Taiyuan", "China", 37.8706, 112.5489),
    ("shijiazhuang", "Shijiazhuang", "China", 38.0428, 114.5149),
    ("jinan", "Jinan", "China", 36.6512, 117.1201),
    # --- R3 wave-2: more world cities to hit 800+ ---
    ("blantyre", "Blantyre", "Malawi", -15.7861, 35.0058),
    ("lilongwe", "Lilongwe", "Malawi", -13.9626, 33.7741),
    ("gaborone", "Gaborone", "Botswana", -24.6282, 25.9231),
    ("maseru", "Maseru", "Lesotho", -29.3151, 27.4869),
    ("mbabane", "Mbabane", "Eswatini", -26.3054, 31.1367),
    ("freetown", "Freetown", "Sierra Leone", 8.4657, -13.2317),
    ("monrovia", "Monrovia", "Liberia", 6.3004, -10.7969),
    ("ouagadougou", "Ouagadougou", "Burkina Faso", 12.3714, -1.5197),
    ("bamako", "Bamako", "Mali", 12.6392, -8.0029),
    ("niamey", "Niamey", "Niger", 13.5117, 2.1251),
    ("nouakchott", "Nouakchott", "Mauritania", 18.0735, -15.9582),
    ("djibouti-city", "Djibouti", "Djibouti", 11.5886, 43.1450),
    ("asmara", "Asmara", "Eritrea", 15.3229, 38.9251),
    ("juba", "Juba", "South Sudan", 4.8517, 31.5825),
    ("kinshasa", "Kinshasa", "Democratic Republic of the Congo", -4.4419, 15.2663),
    ("brazzaville", "Brazzaville", "Republic of the Congo", -4.2634, 15.2429),
    ("yaounde", "Yaoundé", "Cameroon", 3.8480, 11.5021),
    ("douala", "Douala", "Cameroon", 4.0511, 9.7679),
    ("libreville", "Libreville", "Gabon", 0.4162, 9.4673),
    ("malabo", "Malabo", "Equatorial Guinea", 3.7556, 8.7833),
    ("sao-tome", "São Tomé", "São Tomé and Príncipe", 0.3365, 6.7273),
    ("bissau", "Bissau", "Guinea-Bissau", 11.8636, -15.5977),
    ("conakry", "Conakry", "Guinea", 9.6412, -13.5784),
    ("banjul", "Banjul", "Gambia", 13.4549, -16.5790),
    ("bujumbura", "Bujumbura", "Burundi", -3.3614, 29.3599),
    ("nuku-alofa", "Nukuʻalofa", "Tonga", -21.1789, -175.1982),
    ("funafuti", "Funafuti", "Tuvalu", -8.5211, 179.1962),
    ("majuro", "Majuro", "Marshall Islands", 7.1167, 171.1833),
    ("palikir", "Palikir", "Micronesia", 6.9248, 158.1611),
    ("ngerulmud", "Ngerulmud", "Palau", 7.5006, 134.6242),
    ("yaren", "Yaren", "Nauru", -0.5477, 166.9209),
    ("dili", "Dili", "Timor-Leste", -8.5586, 125.5736),
    ("port-moresby", "Port Moresby", "Papua New Guinea", -9.4438, 147.1803),
    ("honiara", "Honiara", "Solomon Islands", -9.4456, 159.9729),
    ("apia-x", "Apia (Upolu)", "Samoa", -13.8506, -171.7513),
    ("nadi-x", "Nadi (Fiji)", "Fiji", -17.8009, 177.4147),
    ("paramaribo", "Paramaribo", "Suriname", 5.8520, -55.2038),
    ("georgetown-gy", "Georgetown", "Guyana", 6.8013, -58.1551),
    ("cayenne", "Cayenne", "French Guiana", 4.9224, -52.3135),
    ("bridgetown", "Bridgetown", "Barbados", 13.1132, -59.5988),
    ("st-georges", "St. George's", "Grenada", 12.0561, -61.7488),
    ("castries", "Castries", "Saint Lucia", 13.9956, -61.0014),
    ("kingstown-vc", "Kingstown", "Saint Vincent", 13.1582, -61.2280),
    ("roseau", "Roseau", "Dominica", 15.3092, -61.3794),
    ("st-johns-ag", "St. John's", "Antigua and Barbuda", 17.1274, -61.8468),
    ("basseterre", "Basseterre", "Saint Kitts and Nevis", 17.2955, -62.7261),
    ("oranjestad", "Oranjestad", "Aruba", 12.5240, -70.0270),
    ("willemstad", "Willemstad", "Curaçao", 12.1224, -68.8824),
    ("philipsburg", "Philipsburg", "Sint Maarten", 18.0260, -63.0458),
    ("st-pierre", "Saint-Pierre", "Saint Pierre and Miquelon", 46.7811, -56.1729),
    ("hamilton-bm", "Hamilton", "Bermuda", 32.2949, -64.7833),
    ("avarua", "Avarua", "Cook Islands", -21.2076, -159.7777),
    ("alofi", "Alofi", "Niue", -19.0560, -169.9192),
    ("hagatna", "Hagåtña", "Guam", 13.4745, 144.7504),
    ("saipan", "Saipan", "Northern Mariana Islands", 15.1850, 145.7467),
    ("pago-pago", "Pago Pago", "American Samoa", -14.2754, -170.7045),
    ("flying-fish-cove", "Flying Fish Cove", "Christmas Island", -10.4250, 105.6786),
    ("kingston-norfolk", "Kingston", "Norfolk Island", -29.0568, 167.9618),
    ("adamstown", "Adamstown", "Pitcairn Islands", -25.0664, -130.1010),
    ("plymouth-ms", "Plymouth", "Montserrat", 16.7065, -62.2153),
    ("george-town-ky", "George Town", "Cayman Islands", 19.2867, -81.3744),
    ("the-valley", "The Valley", "Anguilla", 18.2169, -63.0573),
    ("road-town", "Road Town", "British Virgin Islands", 18.4207, -64.6399),
    ("cockburn-town", "Cockburn Town", "Turks and Caicos", 21.4615, -71.1419),
    ("grand-cayman", "Grand Cayman", "Cayman Islands", 19.3133, -81.2546),
    ("nassau-2", "Nassau (New Providence)", "Bahamas", 25.0480, -77.3554),
    ("freeport-bs", "Freeport (Grand Bahama)", "Bahamas", 26.5333, -78.6667),
    ("road-bay", "Sandy Ground", "Anguilla", 18.1939, -63.0801),
    ("gustavia", "Gustavia", "Saint Barthélemy", 17.8964, -62.8492),
    ("marigot", "Marigot", "Saint Martin", 18.0708, -63.0850),
    ("st-helier", "Saint Helier", "Jersey", 49.1882, -2.1071),
    ("st-peter-port", "Saint Peter Port", "Guernsey", 49.4555, -2.5368),
    ("douglas-im", "Douglas", "Isle of Man", 54.1500, -4.4818),
    ("gibraltar", "Gibraltar", "Gibraltar", 36.1408, -5.3536),
    ("vaduz", "Vaduz", "Liechtenstein", 47.1410, 9.5209),
    ("monaco-mc", "Monaco", "Monaco", 43.7384, 7.4246),
    ("vatican-city", "Vatican City", "Vatican City", 41.9029, 12.4534),
    ("san-marino-city", "San Marino", "San Marino", 43.9424, 12.4578),
    ("andorra-la-vella", "Andorra la Vella", "Andorra", 42.5063, 1.5218),
    ("podgorica", "Podgorica", "Montenegro", 42.4304, 19.2594),
    ("pristina", "Pristina", "Kosovo", 42.6629, 21.1655),
    ("chisinau", "Chișinău", "Moldova", 47.0105, 28.8638),
    ("tiraspol", "Tiraspol", "Transnistria", 46.8403, 29.6433),
    ("sukhumi", "Sukhumi", "Abkhazia", 43.0036, 41.0144),
    ("nicosia-cy-x", "Nicosia (North)", "Northern Cyprus", 35.1856, 33.3823),
]


def expand_cities(db, City):
    """Add more well-known cities. Idempotent: per-slug skip protects warm
    restarts; threshold gate is a fast short-circuit once R2 target is hit."""
    if City.query.count() >= 800:
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
    # --- R2 additions: pharmacies / atms / gas / supermarkets / coffee ---
    ("pharmacies", "{anchor} Pharmacy 24h", "24-hour pharmacy",
     "24-hour pharmacy with prescription drop-off, OTC essentials, and a pickup window.", "$", 4.0, 4.7),
    ("pharmacies", "{anchor} Family Pharmacy", "Neighborhood pharmacy",
     "Family-run neighborhood pharmacy with friendly pharmacists and same-day refills.", "$", 4.2, 4.8),
    ("atms", "{anchor} Bank ATM", "ATM",
     "Bank-owned ATM inside the branch lobby; accepts most major debit and credit networks.", "Free", 3.8, 4.5),
    ("atms", "{anchor} 24h ATM Kiosk", "24-hour ATM",
     "Standalone 24-hour ATM kiosk in a well-lit, camera-monitored vestibule.", "Free", 3.6, 4.3),
    ("gas-stations", "{anchor} Shell Station", "Gas station",
     "Shell-branded gas station with convenience store, air pumps, and free Wi-Fi.", "$$", 4.0, 4.5),
    ("gas-stations", "{anchor} Chevron Station", "Gas station",
     "Chevron service station offering Techron-treated fuel and a clean restroom.", "$$", 4.0, 4.5),
    ("supermarkets", "{anchor} Whole Foods Market", "Supermarket",
     "Whole Foods Market with organic produce, prepared foods, and an in-store cafe.", "$$$", 4.2, 4.7),
    ("supermarkets", "{anchor} Trader Joe's", "Grocery store",
     "Trader Joe's neighborhood grocery with private-label staples and a famous frozen aisle.", "$$", 4.4, 4.8),
    ("coffee-shops", "{anchor} Starbucks Reserve", "Coffee shop",
     "Starbucks Reserve location with single-origin roasts, nitro cold brew, and pour-over service.", "$$", 4.2, 4.7),
    ("coffee-shops", "{anchor} Blue Bottle Coffee", "Specialty coffee",
     "Blue Bottle Coffee specialty bar with single-origin pour-overs and minimalist decor.", "$$", 4.3, 4.8),
    # --- R3 additions: civic + pet + indoor ---
    ("dog-parks", "{anchor} Dog Park", "Off-leash dog park",
     "Fenced off-leash dog park with water stations, agility equipment, and shaded benches.", "Free", 4.3, 4.9),
    ("dog-parks", "{anchor} Bark Park", "Dog run",
     "Community dog run separated for small and large breeds, open dawn to dusk.", "Free", 4.2, 4.8),
    ("public-restrooms", "{anchor} Public Restroom", "Public restroom",
     "Public restroom with wheelchair access, baby-changing tables, and 24/7 cleaning.", "Free", 3.6, 4.4),
    ("public-restrooms", "{anchor} Park Comfort Station", "Comfort station",
     "Park comfort station with running water, family stalls, and seasonal operating hours.", "Free", 3.5, 4.3),
    ("libraries", "{anchor} Public Library", "Library",
     "Public library branch with reading rooms, computer lab, children's section, and free Wi-Fi.", "Free", 4.5, 4.9),
    ("libraries", "{anchor} Memorial Library", "Library branch",
     "Memorial library branch hosting weekly story time, study rooms, and audiobook lending.", "Free", 4.4, 4.9),
    ("post-offices", "{anchor} USPS Post Office", "Post office",
     "USPS retail post office offering passport services, PO Boxes, and shipping supplies.", "$", 3.5, 4.2),
    ("post-offices", "{anchor} Postal Annex", "Postal annex",
     "Postal annex for package pickup, certified mail, and money orders.", "$", 3.6, 4.3),
    ("police-stations", "{anchor} Police Station", "Police station",
     "Neighborhood police station with 24-hour front desk and community resource officers.", "Free", 3.8, 4.5),
    ("police-stations", "{anchor} Sheriff Office", "Sheriff office",
     "County sheriff's office handling civil paperwork, fingerprinting, and citizen reports.", "Free", 3.7, 4.4),
    ("fire-stations", "{anchor} Fire Station", "Fire station",
     "Volunteer fire station with engine and ladder companies and seasonal community open-house days.", "Free", 4.4, 4.9),
    ("fire-stations", "{anchor} Engine Company", "Engine company",
     "Fire engine company station, EMS dispatch, and child-seat installation appointments.", "Free", 4.5, 4.9),
    ("indoor-mall-shops", "Sephora at {anchor} Mall", "Mall sub-shop - beauty",
     "Sephora boutique inside the mall on the upper floor near the food court; testers and beauty advisors on-site.", "$$$", 4.1, 4.6),
    ("indoor-mall-shops", "Apple Store at {anchor} Mall", "Mall sub-shop - electronics",
     "Apple Store inside the mall, ground floor near the main entrance; Genius Bar bookable in advance.", "$$$", 4.3, 4.8),
    ("indoor-mall-shops", "Uniqlo at {anchor} Mall", "Mall sub-shop - apparel",
     "Uniqlo flagship inside the mall on level 2; expanded HEATTECH and AIRism sections seasonally.", "$$", 4.2, 4.7),
    ("indoor-mall-shops", "Lego Store at {anchor} Mall", "Mall sub-shop - toys",
     "Lego Store on the mall's lower level with build-a-minifig wall and exclusive sets.", "$$$", 4.5, 4.9),
    ("indoor-airport-shops", "Hudson News - {anchor} Airport Terminal A", "Airport newsstand",
     "Hudson News inside Terminal A near gate 24, post-security; magazines, snacks, and travel essentials.", "$$", 3.8, 4.4),
    ("indoor-airport-shops", "Starbucks - {anchor} Airport Concourse B", "Airport coffee",
     "Starbucks on Concourse B between gates 12 and 15; mobile order accepted, no rewards earning at airport locations.", "$$", 3.7, 4.3),
    ("indoor-airport-shops", "Duty Free Americas - {anchor} Airport Intl Terminal", "Airport duty-free",
     "Duty Free Americas in the international terminal departures hall, post-passport-control only.", "$$$", 3.9, 4.5),
    ("indoor-airport-shops", "Centurion Lounge - {anchor} Airport", "Airport lounge",
     "Amex Centurion Lounge upstairs from the main hub; entry with eligible Amex cards plus same-day boarding pass.", "$$$$", 4.4, 4.9),
    ("campus-buildings", "{anchor} University Main Library", "Campus library",
     "Main university library at the heart of campus; 24-hour study floors during exams.", "Free", 4.5, 4.9),
    ("campus-buildings", "{anchor} University Student Union", "Student union",
     "Student union with dining hall, theater, and meeting rooms; central quad on the south side.", "Free", 4.3, 4.7),
    ("campus-buildings", "{anchor} University Science Hall", "Lecture hall",
     "Science lecture hall housing physics, chemistry, and biology classrooms plus instructional labs.", "Free", 4.2, 4.6),
    ("transit", "{anchor} Central Bus Terminal", "Bus terminal",
     "Central bus terminal with intercity coach lines, ticket kiosks, and luggage storage.", "Free", 3.7, 4.4),
    ("transit", "{anchor} Light Rail Station", "Light rail station",
     "Light rail station serving commuter and recreational routes, with bike racks and ticket vending.", "Free", 4.0, 4.6),
    ("transit", "{anchor} Ferry Terminal", "Ferry terminal",
     "Ferry terminal for passenger and vehicle crossings, with covered waiting room and snack bar.", "$", 4.1, 4.7),
    ("parking", "{anchor} Park & Ride", "Park and ride",
     "Park-and-ride lot with bus and light-rail connections; free overnight parking with valid commuter pass.", "Free", 3.9, 4.5),
    ("parking", "{anchor} Airport Long-Term Parking", "Airport parking",
     "Airport long-term parking with shuttle service every 10 minutes to all terminals.", "$$$", 3.7, 4.3),
    ("ev-charging", "Tesla Supercharger - {anchor} Plaza", "Tesla Supercharger",
     "Tesla Supercharger plaza with 12 V3 stalls; 250 kW peak; restrooms and dining within 100 m.", "$$", 4.3, 4.8),
    ("ev-charging", "Electrify America - {anchor}", "EV fast charging",
     "Electrify America DC fast-charging plaza with CCS connectors up to 350 kW and an indoor lounge.", "$$", 4.0, 4.6),
    ("attractions", "{anchor} Riverwalk", "Riverside walk",
     "Riverside boardwalk lined with restaurants, public art, and lookout points.", "Free", 4.4, 4.9),
    ("attractions", "{anchor} Public Square", "Public square",
     "Central public square with weekly farmers market, fountain, and seasonal events.", "Free", 4.3, 4.8),
    ("entertainment", "{anchor} Comedy Club", "Comedy club",
     "Stand-up comedy club hosting touring headliners and Tuesday open-mic nights.", "$$", 4.2, 4.7),
    ("entertainment", "{anchor} Bowling Center", "Bowling alley",
     "Family bowling center with cosmic-bowl nights, a sports bar, and arcade lounge.", "$$", 4.1, 4.6),
    # --- R3 wave-2: car-rental / playgrounds / beaches / hospitals / dentists / vets / schools / religious ---
    ("car-rental", "Hertz - {anchor} Airport", "Car rental",
     "Hertz airport car rental with full-size, SUV, and luxury vehicles; 24-hour drop-off.", "$$$", 3.8, 4.5),
    ("car-rental", "Enterprise - Downtown {anchor}", "Car rental",
     "Enterprise neighborhood car rental with free customer pickup within 5 miles.", "$$", 4.1, 4.7),
    ("playgrounds", "{anchor} City Playground", "Playground",
     "Public playground with climbing structures, swings, and ADA-accessible play equipment.", "Free", 4.5, 4.9),
    ("playgrounds", "{anchor} Splash Pad Playground", "Playground",
     "Splash pad and playground combo for summer cool-off and toddler-safe play.", "Free", 4.4, 4.9),
    ("beaches", "{anchor} Public Beach", "Public beach",
     "Public beach with lifeguard, restrooms, picnic tables, and paid parking.", "Free", 4.3, 4.9),
    ("beaches", "{anchor} Cove Beach", "Beach cove",
     "Sheltered cove beach with calm water, good for families and snorkeling.", "Free", 4.4, 4.9),
    ("hospitals", "{anchor} General Hospital", "Hospital",
     "Full-service general hospital with 24-hour emergency room and trauma center.", "$$$", 3.8, 4.5),
    ("hospitals", "{anchor} Medical Center", "Hospital",
     "Multi-specialty medical center with cardiology, oncology, and pediatric wings.", "$$$", 3.9, 4.6),
    ("dentists", "{anchor} Family Dental", "Dental office",
     "Family dental practice offering cleanings, fillings, and pediatric care.", "$$", 4.4, 4.9),
    ("dentists", "{anchor} Orthodontics", "Orthodontist",
     "Orthodontics office specializing in braces, Invisalign, and free initial consults.", "$$$", 4.5, 4.9),
    ("veterinarians", "{anchor} Animal Hospital", "Veterinarian",
     "Animal hospital with general care, dental services, and 24-hour emergency coverage.", "$$$", 4.4, 4.9),
    ("veterinarians", "{anchor} Veterinary Clinic", "Veterinary clinic",
     "Neighborhood vet clinic specializing in cats and dogs - walk-ins welcome.", "$$", 4.5, 4.9),
    ("schools", "{anchor} Elementary School", "Elementary school",
     "Public elementary school serving K-5 with after-school programs and library.", "Free", 4.2, 4.7),
    ("schools", "{anchor} High School", "High school",
     "Public high school with comprehensive academic, athletic, and arts programs.", "Free", 4.0, 4.6),
    ("religious", "{anchor} Community Church", "Church",
     "Community church with Sunday services, children's ministry, and weekday programs.", "Free", 4.5, 4.9),
    ("religious", "{anchor} Islamic Center", "Mosque",
     "Islamic center with five daily prayers, Friday Jumu'ah, and weekend school.", "Free", 4.6, 4.9),
    ("religious", "{anchor} Buddhist Temple", "Temple",
     "Buddhist temple offering meditation classes and seasonal celebrations.", "Free", 4.6, 4.9),
    # --- R3 additional cosmetic templates for civic/transport ---
    ("supermarkets", "{anchor} Costco Wholesale", "Warehouse club",
     "Costco Wholesale members-only warehouse with bulk groceries and Kirkland Signature.", "$$$", 4.3, 4.8),
    ("supermarkets", "{anchor} Safeway", "Supermarket",
     "Safeway grocery with Just for U digital deals, deli, and in-store Starbucks.", "$$", 3.9, 4.5),
    ("gas-stations", "{anchor} Costco Gas Station", "Gas station",
     "Costco Wholesale gas pumps - members only, typically cheapest fuel in town.", "$", 4.4, 4.8),
    ("gas-stations", "{anchor} Buc-ee's", "Travel center",
     "Buc-ee's mega travel center with 100+ pumps, brisket sandwiches, and clean restrooms.", "$$", 4.7, 4.9),
]

# Curated chain brands per category for varied catalog listings
_EXPAND_CHAINS = {
    "restaurants": ["Shake Shack", "Chipotle", "Sweetgreen", "Five Guys", "P.F. Chang's"],
    "hotels": ["Hilton", "Marriott", "Hyatt", "Sheraton", "Holiday Inn", "Best Western"],
    "shopping": ["Whole Foods Market", "Trader Joe's", "Target", "Costco", "Best Buy", "REI"],
    "fitness": ["Equinox", "Planet Fitness", "Anytime Fitness", "Orangetheory Fitness"],
    "ev-charging": ["Tesla Supercharger", "Electrify America", "ChargePoint Station", "EVgo Fast Charging"],
    "pharmacies": ["CVS Pharmacy", "Walgreens", "Rite Aid", "Walmart Pharmacy"],
    "atms": ["Chase ATM", "Bank of America ATM", "Wells Fargo ATM", "Citibank ATM", "Allpoint ATM"],
    "gas-stations": ["Shell", "Chevron", "ExxonMobil", "BP", "76", "Sunoco"],
    "supermarkets": ["Kroger", "Safeway", "Publix", "Whole Foods", "Trader Joe's", "Aldi"],
    "coffee-shops": ["Starbucks", "Peet's Coffee", "Blue Bottle Coffee", "Dunkin'", "Philz Coffee"],
    # --- R3 additions ---
    "libraries": ["Carnegie Library", "Public Library"],
    "post-offices": ["USPS", "FedEx Office", "UPS Store"],
    "police-stations": ["Police Precinct"],
    "fire-stations": ["Fire Station", "Engine Co."],
    "indoor-mall-shops": ["Sephora", "Apple Store", "Uniqlo", "Lego Store", "Lululemon", "Foot Locker"],
    "indoor-airport-shops": ["Hudson News", "Starbucks", "Duty Free Americas", "Centurion Lounge", "InMotion"],
    "campus-buildings": ["University Library", "Student Union"],
    "dog-parks": [],
    "public-restrooms": [],
    "car-rental": ["Hertz", "Enterprise", "Avis", "Budget", "Alamo", "National", "Sixt"],
    "playgrounds": [],
    "beaches": [],
    "hospitals": ["HCA Healthcare", "Kaiser Permanente", "Sutter Health", "AdventHealth"],
    "dentists": ["Aspen Dental", "Heartland Dental"],
    "veterinarians": ["VCA Animal Hospitals", "Banfield Pet Hospital", "Petco Vetco"],
    "schools": [],
    "religious": [],
}


def expand_places(db, Place, Category, City):
    """Densify the catalog so every city has 8-10 places spanning categories.

    Idempotent: gate by Place count threshold.
    """
    if Place.query.count() >= 35000:
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
        # NOTE: Python's built-in hash() is PYTHONHASHSEED-randomized per
        # process; using it here breaks byte-identical seed-DB rebuilds.
        # md5 is portable and deterministic.
        slug_seed = int.from_bytes(
            hashlib.md5(city.slug.encode()).digest()[:4], "big")
        random.Random(slug_seed).shuffle(templates)

        for idx, (cat_slug, pattern, subtitle, desc, price, rlo, rhi) in enumerate(templates):
            cat = cat_by_slug.get(cat_slug)
            if not cat:
                continue
            # Inject occasional chain brand into the name for realism + distractors
            chain = ""
            if idx % 4 == 0 and _EXPAND_CHAINS.get(cat_slug):
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
    # --- R3 additions: more walking / cycling / transit / EV-route variants ---
    ("Times Square", "Empire State Building", "walking", "0.9 km", 0.9, "11 min", 11,
     "Times Square to Empire State Building via 7th Ave",
     "Times Square, New York", "Empire State Building, 350 5th Ave, NY", [
         {"instruction": "Head south on 7th Ave", "distance": "0.4 km"},
         {"instruction": "Turn left on W 34th St", "distance": "0.3 km"},
         {"instruction": "Arrive at observation deck entrance on 5th Ave", "distance": "0.2 km"},
     ]),
    ("Lincoln Memorial", "Washington Monument", "walking", "1.1 km", 1.1, "14 min", 14,
     "Lincoln Memorial to Washington Monument along the Mall",
     "Lincoln Memorial, Washington DC", "Washington Monument, Washington DC", [
         {"instruction": "Head east on the National Mall", "distance": "0.7 km"},
         {"instruction": "Continue past WWII Memorial reflecting pool", "distance": "0.3 km"},
         {"instruction": "Arrive at Washington Monument base", "distance": "0.1 km"},
     ]),
    ("Central Park", "Metropolitan Museum of Art", "walking", "1.0 km", 1.0, "13 min", 13,
     "Central Park to The Met via East Drive",
     "Central Park, Manhattan, NY", "Metropolitan Museum of Art, 1000 5th Ave, NY", [
         {"instruction": "Head east along Bethesda Terrace", "distance": "0.4 km"},
         {"instruction": "Exit park at 79th St & 5th Ave", "distance": "0.4 km"},
         {"instruction": "Arrive at Met main entrance", "distance": "0.2 km"},
     ]),
    ("Grand Central Terminal", "Bryant Park", "walking", "0.6 km", 0.6, "8 min", 8,
     "Grand Central to Bryant Park via 42nd St",
     "Grand Central Terminal, NY", "Bryant Park, NY", [
         {"instruction": "Exit Grand Central onto 42nd St", "distance": "0.1 km"},
         {"instruction": "Head west on 42nd St", "distance": "0.4 km"},
         {"instruction": "Arrive at Bryant Park east side", "distance": "0.1 km"},
     ]),
    ("Pier 39", "Lombard Street", "walking", "1.4 km", 1.4, "20 min", 20,
     "Pier 39 to Lombard Street via Columbus Ave",
     "Pier 39, San Francisco", "Lombard Street, San Francisco", [
         {"instruction": "Head south on Powell St", "distance": "0.6 km"},
         {"instruction": "Turn right on Lombard St", "distance": "0.7 km"},
         {"instruction": "Arrive at crooked block of Lombard", "distance": "0.1 km"},
     ]),
    ("Hollywood Sign", "Griffith Observatory", "cycling", "5.6 km", 5.6, "28 min", 28,
     "Hollywood Sign trailhead to Griffith Observatory via Mt Hollywood Dr",
     "Hollywood Sign, Mt Lee Dr, LA", "Griffith Observatory, 2800 E Observatory Rd, LA", [
         {"instruction": "Descend Mt Lee Dr south", "distance": "2.0 km"},
         {"instruction": "Connect to Mt Hollywood Dr east", "distance": "2.5 km"},
         {"instruction": "Arrive at observatory parking", "distance": "1.1 km"},
     ]),
    ("Santa Monica Pier", "Venice Beach", "cycling", "5.0 km", 5.0, "20 min", 20,
     "Santa Monica Pier to Venice Beach along Strand bike path",
     "Santa Monica Pier, Santa Monica, CA", "Venice Beach Boardwalk, Venice, CA", [
         {"instruction": "Head south on The Strand bike path", "distance": "4.5 km"},
         {"instruction": "Pass under Marvin Braude marker", "distance": "0.3 km"},
         {"instruction": "Arrive at Venice Beach boardwalk", "distance": "0.2 km"},
     ]),
    ("Hyde Park", "Buckingham Palace", "cycling", "2.5 km", 2.5, "10 min", 10,
     "Hyde Park to Buckingham Palace via Constitution Hill",
     "Hyde Park, London", "Buckingham Palace, London", [
         {"instruction": "Exit Hyde Park at Hyde Park Corner", "distance": "0.8 km"},
         {"instruction": "Take Constitution Hill cycle lane", "distance": "1.2 km"},
         {"instruction": "Arrive at Buckingham Palace forecourt", "distance": "0.5 km"},
     ]),
    ("Brooklyn", "Manhattan Bridge", "cycling", "3.0 km", 3.0, "13 min", 13,
     "Brooklyn to Manhattan Bridge via Tillary St",
     "Brooklyn, NY", "Manhattan Bridge, NY", [
         {"instruction": "Head north on Jay St", "distance": "1.0 km"},
         {"instruction": "Turn onto Tillary St", "distance": "1.0 km"},
         {"instruction": "Enter Manhattan Bridge bike path", "distance": "1.0 km"},
     ]),
    ("JFK Airport", "Times Square", "transit", "27 km", 27.0, "70 min", 70,
     "JFK to Times Square via AirTrain + E line",
     "John F. Kennedy International Airport, NY", "Times Square, New York", [
         {"instruction": "AirTrain JFK from terminal to Jamaica Station", "distance": "5 km"},
         {"instruction": "Board NYC Subway E train northbound", "distance": "20 km"},
         {"instruction": "Exit at 42nd St-Port Authority", "distance": "1 km"},
         {"instruction": "Walk east to Times Square", "distance": "1 km"},
     ]),
    ("Heathrow Airport", "Paddington Station", "transit", "23 km", 23.0, "15 min", 15,
     "Heathrow Express service from LHR T2/T3 to Paddington",
     "London Heathrow Airport", "Paddington Station, London", [
         {"instruction": "Board Heathrow Express at LHR T2/T3", "distance": "0.2 km"},
         {"instruction": "Non-stop service to Paddington", "distance": "22 km"},
         {"instruction": "Arrive Paddington, exit to street", "distance": "0.5 km"},
     ]),
    ("Narita Airport", "Tokyo Station", "transit", "75 km", 75.0, "55 min", 55,
     "Narita Airport to Tokyo Station via Narita Express (N'EX)",
     "Narita International Airport, Japan", "Tokyo Station, Japan", [
         {"instruction": "Board N'EX at Narita T1/T2 station", "distance": "0.3 km"},
         {"instruction": "Through-service to Tokyo Station", "distance": "74 km"},
         {"instruction": "Disembark at Tokyo Station underground platform", "distance": "0.3 km"},
     ]),
    ("Charles de Gaulle Airport", "Gare du Nord", "transit", "30 km", 30.0, "33 min", 33,
     "CDG Airport to Gare du Nord via RER B",
     "Paris-Charles de Gaulle Airport", "Gare du Nord, Paris", [
         {"instruction": "RER B from CDG T2 station southbound", "distance": "28 km"},
         {"instruction": "Direct to Gare du Nord", "distance": "1.5 km"},
         {"instruction": "Disembark at Gare du Nord platform 41-44", "distance": "0.2 km"},
     ]),
    ("Boston Logan Airport", "North Station", "transit", "5 km", 5.0, "20 min", 20,
     "Logan Airport to North Station via Silver Line + Orange Line",
     "Boston Logan International Airport", "North Station, Boston", [
         {"instruction": "Silver Line SL1 from terminal to South Station", "distance": "4 km"},
         {"instruction": "Transfer to Orange Line northbound", "distance": "0.5 km"},
         {"instruction": "Disembark at North Station", "distance": "0.5 km"},
     ]),
    ("San Francisco", "San Jose", "driving", "75 km", 75.0, "1 hr 10 min", 70,
     "San Francisco to San Jose via US-101 S with EV charging at Tesla Mountain View",
     "San Francisco, CA", "San Jose, CA", [
         {"instruction": "Head south on US-101 from downtown SF", "distance": "30 km"},
         {"instruction": "Stop at Tesla Supercharger Mountain View (12 stalls, 250 kW)", "distance": "1 km"},
         {"instruction": "Continue south on US-101", "distance": "40 km"},
         {"instruction": "Take exit toward downtown San Jose", "distance": "4 km"},
     ]),
    ("Los Angeles", "Las Vegas", "driving", "435 km", 435.0, "4 hr 20 min", 260,
     "LA to Las Vegas via I-15 N with EV stops at Barstow and Primm",
     "Los Angeles, CA", "Las Vegas, NV", [
         {"instruction": "Head east on I-10 to I-15 interchange", "distance": "50 km"},
         {"instruction": "Continue north on I-15 N through Victorville", "distance": "120 km"},
         {"instruction": "EV stop: Electrify America at Barstow (350 kW)", "distance": "5 km"},
         {"instruction": "Continue I-15 N through Baker", "distance": "200 km"},
         {"instruction": "EV stop: Tesla Supercharger Primm (24 stalls)", "distance": "5 km"},
         {"instruction": "Arrive Las Vegas Strip", "distance": "55 km"},
     ]),
    ("Seattle", "Portland", "driving", "280 km", 280.0, "2 hr 50 min", 170,
     "Seattle to Portland via I-5 S with EV stop at Centralia",
     "Seattle, WA", "Portland, OR", [
         {"instruction": "Head south on I-5 from downtown Seattle", "distance": "80 km"},
         {"instruction": "Tesla Supercharger Centralia stop", "distance": "5 km"},
         {"instruction": "Continue I-5 south through Olympia and Vancouver, WA", "distance": "180 km"},
         {"instruction": "Cross Columbia River into Portland", "distance": "15 km"},
     ]),
    ("Atlanta", "Savannah", "driving", "400 km", 400.0, "4 hr", 240,
     "Atlanta to Savannah via I-75 S and I-16 E",
     "Atlanta, GA", "Savannah, GA", [
         {"instruction": "Head south on I-75 from downtown Atlanta", "distance": "260 km"},
         {"instruction": "Take I-16 E toward Savannah at Macon", "distance": "130 km"},
         {"instruction": "Arrive in historic Savannah", "distance": "10 km"},
     ]),
    ("Chicago", "Milwaukee", "driving", "150 km", 150.0, "1 hr 35 min", 95,
     "Chicago to Milwaukee via I-94 W",
     "Chicago, IL", "Milwaukee, WI", [
         {"instruction": "Head north on I-94 W from Chicago Loop", "distance": "30 km"},
         {"instruction": "Continue I-94 W past Kenosha", "distance": "100 km"},
         {"instruction": "Take exit toward downtown Milwaukee", "distance": "15 km"},
         {"instruction": "Arrive in downtown Milwaukee", "distance": "5 km"},
     ]),
    ("Miami", "Key West", "driving", "270 km", 270.0, "4 hr", 240,
     "Miami to Key West via US-1 Overseas Highway",
     "Miami, FL", "Key West, FL", [
         {"instruction": "Head south on US-1 from Miami", "distance": "60 km"},
         {"instruction": "Cross Florida Keys via Seven Mile Bridge", "distance": "11 km"},
         {"instruction": "Continue US-1 through Marathon and Lower Keys", "distance": "190 km"},
         {"instruction": "Arrive in Old Town Key West", "distance": "9 km"},
     ]),
    ("Philadelphia", "Atlantic City", "driving", "100 km", 100.0, "1 hr 20 min", 80,
     "Philadelphia to Atlantic City via Atlantic City Expressway",
     "Philadelphia, PA", "Atlantic City, NJ", [
         {"instruction": "Cross Walt Whitman Bridge into NJ", "distance": "10 km"},
         {"instruction": "Take NJ-42 S to Atlantic City Expressway", "distance": "20 km"},
         {"instruction": "Continue ACX east to Atlantic City", "distance": "65 km"},
         {"instruction": "Arrive at Boardwalk", "distance": "5 km"},
     ]),
    ("Tokyo Station", "Mt. Fuji 5th Station", "driving", "115 km", 115.0, "2 hr 10 min", 130,
     "Tokyo to Mt. Fuji 5th Station via Chuo Expressway",
     "Tokyo Station, Japan", "Mt. Fuji Subaru Line 5th Station", [
         {"instruction": "Head west via Shuto Expressway", "distance": "20 km"},
         {"instruction": "Continue Chuo Expressway west toward Kawaguchiko", "distance": "75 km"},
         {"instruction": "Exit Kawaguchiko IC, follow Fuji Subaru Line", "distance": "18 km"},
         {"instruction": "Arrive at 5th Station observation area", "distance": "2 km"},
     ]),
    ("Singapore Changi Airport", "Marina Bay Sands", "transit", "22 km", 22.0, "30 min", 30,
     "Changi to Marina Bay Sands via MRT East-West + Downtown lines",
     "Singapore Changi Airport", "Marina Bay Sands, Singapore", [
         {"instruction": "Board East-West Line at Changi Airport MRT", "distance": "2 km"},
         {"instruction": "Transfer at Tanah Merah to EW line city-bound", "distance": "15 km"},
         {"instruction": "Transfer to Downtown Line at Bugis", "distance": "3 km"},
         {"instruction": "Alight at Bayfront, walk to Marina Bay Sands", "distance": "2 km"},
     ]),
    ("Sydney Opera House", "Circular Quay", "walking", "0.4 km", 0.4, "5 min", 5,
     "Opera House to Circular Quay along Macquarie St",
     "Sydney Opera House", "Circular Quay, Sydney", [
         {"instruction": "Head west along Bennelong Point", "distance": "0.2 km"},
         {"instruction": "Continue along Circular Quay East", "distance": "0.2 km"},
     ]),
    ("Edinburgh Castle", "Holyrood Palace", "walking", "1.6 km", 1.6, "20 min", 20,
     "Edinburgh Castle to Holyrood Palace via the Royal Mile",
     "Edinburgh Castle, Edinburgh", "Palace of Holyroodhouse, Edinburgh", [
         {"instruction": "Head east down the Royal Mile from Castle Esplanade", "distance": "0.8 km"},
         {"instruction": "Continue past St Giles' Cathedral and Canongate", "distance": "0.6 km"},
         {"instruction": "Arrive at Holyrood Palace gates", "distance": "0.2 km"},
     ]),
    ("Berlin Brandenburg Airport", "Brandenburg Gate", "transit", "30 km", 30.0, "45 min", 45,
     "BER Airport to Brandenburg Gate via Airport Express FEX + S-Bahn",
     "Berlin Brandenburg Airport", "Brandenburg Gate, Berlin", [
         {"instruction": "FEX from BER to Berlin Hauptbahnhof", "distance": "28 km"},
         {"instruction": "Walk to Brandenburg Gate via Unter den Linden", "distance": "1.5 km"},
     ]),
    ("Dubai International Airport", "Burj Khalifa", "transit", "13 km", 13.0, "30 min", 30,
     "Dubai Airport to Burj Khalifa via Red Line Metro",
     "Dubai International Airport", "Burj Khalifa / Dubai Mall, Dubai", [
         {"instruction": "Board Red Line at Airport Terminal 1 / Terminal 3 Metro station", "distance": "0.3 km"},
         {"instruction": "Ride Red Line southbound", "distance": "12 km"},
         {"instruction": "Alight at Burj Khalifa / Dubai Mall Metro Station", "distance": "0.3 km"},
         {"instruction": "Walk via covered link to Dubai Mall", "distance": "0.5 km"},
     ]),
    ("Hong Kong International Airport", "Tsim Sha Tsui", "transit", "35 km", 35.0, "30 min", 30,
     "HKG Airport to Tsim Sha Tsui via Airport Express + East Tsim Sha Tsui",
     "Hong Kong International Airport", "Tsim Sha Tsui, Hong Kong", [
         {"instruction": "Board Airport Express at HKG", "distance": "0.3 km"},
         {"instruction": "Ride Airport Express to Kowloon Station", "distance": "30 km"},
         {"instruction": "Transfer to Tung Chung Line + walk", "distance": "4 km"},
         {"instruction": "Arrive Tsim Sha Tsui", "distance": "0.7 km"},
     ]),
    ("Vancouver International Airport", "Downtown Vancouver", "transit", "13 km", 13.0, "26 min", 26,
     "YVR to Downtown Vancouver via Canada Line SkyTrain",
     "Vancouver International Airport", "Downtown Vancouver, BC", [
         {"instruction": "Board Canada Line at YVR Airport Station", "distance": "0.1 km"},
         {"instruction": "Ride Canada Line northbound", "distance": "13 km"},
         {"instruction": "Alight at Waterfront Station", "distance": "0.1 km"},
     ]),
    ("Charlottesville", "Shenandoah National Park", "driving", "60 km", 60.0, "1 hr", 60,
     "Charlottesville to Shenandoah NP via US-29 N + Skyline Drive",
     "Charlottesville, VA", "Shenandoah National Park, VA", [
         {"instruction": "Head north on US-29 from Charlottesville", "distance": "40 km"},
         {"instruction": "Take US-33 W to Skyline Drive south entrance", "distance": "15 km"},
         {"instruction": "Enter Shenandoah NP at Swift Run Gap", "distance": "5 km"},
     ]),
    ("Phoenix", "Sedona", "driving", "190 km", 190.0, "2 hr", 120,
     "Phoenix to Sedona via I-17 N",
     "Phoenix, AZ", "Sedona, AZ", [
         {"instruction": "Head north on I-17 from Phoenix", "distance": "160 km"},
         {"instruction": "Take exit 298 toward AZ-179 N", "distance": "5 km"},
         {"instruction": "Continue AZ-179 N to Sedona", "distance": "23 km"},
         {"instruction": "Arrive at Sedona Main St", "distance": "2 km"},
     ]),
    ("Honolulu", "Waikiki Beach", "driving", "13 km", 13.0, "25 min", 25,
     "Honolulu Airport to Waikiki Beach via H-1 E",
     "Honolulu International Airport (HNL)", "Waikiki Beach, HI", [
         {"instruction": "Exit airport onto Nimitz Hwy", "distance": "3 km"},
         {"instruction": "Merge onto H-1 E", "distance": "7 km"},
         {"instruction": "Take Punahou St exit toward Ala Moana", "distance": "2 km"},
         {"instruction": "Arrive at Kalakaua Ave, Waikiki", "distance": "1 km"},
     ]),
    ("Salt Lake City", "Park City", "driving", "55 km", 55.0, "40 min", 40,
     "SLC to Park City via I-80 E",
     "Salt Lake City, UT", "Park City, UT", [
         {"instruction": "Head east on I-80 from downtown SLC", "distance": "45 km"},
         {"instruction": "Take exit 145 toward UT-224 S", "distance": "3 km"},
         {"instruction": "Continue UT-224 S to Park City Main St", "distance": "7 km"},
     ]),
    ("Yellowstone National Park - South Entrance", "Old Faithful", "driving", "50 km", 50.0, "55 min", 55,
     "Yellowstone S Entrance to Old Faithful",
     "Yellowstone NP South Entrance, WY", "Old Faithful Geyser, Yellowstone NP", [
         {"instruction": "Enter Yellowstone via S Entrance Rd", "distance": "0.5 km"},
         {"instruction": "Continue along South Rim Rd", "distance": "30 km"},
         {"instruction": "Turn west onto Grand Loop Rd toward Old Faithful", "distance": "18 km"},
         {"instruction": "Arrive Old Faithful Visitor Education Center", "distance": "1 km"},
     ]),
    ("Yosemite Valley", "Glacier Point", "driving", "50 km", 50.0, "1 hr", 60,
     "Yosemite Valley to Glacier Point via Glacier Point Rd",
     "Yosemite Valley, Yosemite NP, CA", "Glacier Point, Yosemite NP, CA", [
         {"instruction": "Head south on Wawona Rd from Yosemite Valley", "distance": "20 km"},
         {"instruction": "Turn east onto Glacier Point Rd at Chinquapin", "distance": "25 km"},
         {"instruction": "Continue to Glacier Point parking area", "distance": "5 km"},
     ]),
    # --- R3 wave-2 routes ---
    ("Disneyland Park Anaheim", "Universal Studios Hollywood", "driving", "55 km", 55.0, "55 min", 55,
     "Disneyland to Universal Studios via I-5 N",
     "Disneyland Park, Anaheim, CA", "Universal Studios Hollywood, Universal City, CA", [
         {"instruction": "Head west on Katella Ave", "distance": "2 km"},
         {"instruction": "Merge onto I-5 N", "distance": "45 km"},
         {"instruction": "Take exit 145 toward Universal Studios Blvd", "distance": "5 km"},
         {"instruction": "Arrive at Universal Studios entrance", "distance": "3 km"},
     ]),
    ("Niagara Falls (American)", "Niagara Falls (Canadian)", "walking", "1.0 km", 1.0, "15 min", 15,
     "American Falls to Canadian Horseshoe Falls via Rainbow Bridge",
     "Niagara Falls State Park, NY", "Niagara Falls, ON, Canada", [
         {"instruction": "Walk along the American Falls promenade", "distance": "0.3 km"},
         {"instruction": "Cross Rainbow Bridge (have passport ready)", "distance": "0.5 km"},
         {"instruction": "Arrive at Table Rock viewpoint", "distance": "0.2 km"},
     ]),
    ("Walt Disney World Resort", "Universal Orlando Resort", "driving", "25 km", 25.0, "30 min", 30,
     "Walt Disney World to Universal Orlando via I-4 E",
     "Walt Disney World Resort, FL", "Universal Orlando Resort, FL", [
         {"instruction": "Head east on Buena Vista Dr", "distance": "3 km"},
         {"instruction": "Merge onto I-4 E", "distance": "18 km"},
         {"instruction": "Take exit 75A toward Universal Blvd", "distance": "3 km"},
         {"instruction": "Arrive at Universal Orlando entrance", "distance": "1 km"},
     ]),
    ("San Diego Airport", "USS Midway Museum", "driving", "5 km", 5.0, "10 min", 10,
     "SAN to USS Midway via Harbor Dr",
     "San Diego International Airport", "USS Midway Museum, San Diego, CA", [
         {"instruction": "Exit airport on N Harbor Dr eastbound", "distance": "3 km"},
         {"instruction": "Continue along Embarcadero waterfront", "distance": "1.5 km"},
         {"instruction": "Arrive at USS Midway ticket gate", "distance": "0.5 km"},
     ]),
    ("Acadia National Park - Bar Harbor", "Cadillac Mountain Summit", "driving", "12 km", 12.0, "20 min", 20,
     "Bar Harbor to Cadillac Mountain summit",
     "Bar Harbor, ME", "Cadillac Mountain Summit, Acadia NP", [
         {"instruction": "Head south on Cottage St onto Park Loop Rd", "distance": "3 km"},
         {"instruction": "Take Cadillac Summit Rd northeast", "distance": "8 km"},
         {"instruction": "Arrive at summit parking area", "distance": "1 km"},
     ]),
    ("Glacier National Park - West Entrance", "Logan Pass", "driving", "50 km", 50.0, "1 hr 15 min", 75,
     "West Glacier to Logan Pass via Going-to-the-Sun Rd",
     "Glacier NP West Entrance, MT", "Logan Pass Visitor Center, Glacier NP", [
         {"instruction": "Enter park via West Entrance", "distance": "1 km"},
         {"instruction": "Follow Going-to-the-Sun Rd east", "distance": "45 km"},
         {"instruction": "Arrive Logan Pass parking", "distance": "4 km"},
     ]),
    ("Grand Canyon - South Rim Visitor Center", "Mather Point", "walking", "0.5 km", 0.5, "7 min", 7,
     "South Rim Visitor Center to Mather Point overlook",
     "Grand Canyon South Rim Visitor Center, AZ", "Mather Point, Grand Canyon NP", [
         {"instruction": "Follow paved Greenway trail east", "distance": "0.4 km"},
         {"instruction": "Arrive at Mather Point overlook", "distance": "0.1 km"},
     ]),
    ("Rocky Mountain National Park - Estes Park", "Bear Lake", "driving", "30 km", 30.0, "40 min", 40,
     "Estes Park to Bear Lake via Bear Lake Rd",
     "Estes Park, CO", "Bear Lake, Rocky Mountain NP", [
         {"instruction": "Head west on US-36 into Rocky Mountain NP", "distance": "5 km"},
         {"instruction": "Turn south onto Bear Lake Rd", "distance": "23 km"},
         {"instruction": "Arrive at Bear Lake trailhead parking", "distance": "2 km"},
     ]),
    ("Zion National Park - South Entrance", "Angels Landing Trailhead", "transit", "10 km", 10.0, "30 min", 30,
     "South Entrance to Angels Landing via Zion Shuttle",
     "Zion NP South Entrance, UT", "The Grotto Trailhead (Angels Landing), Zion NP", [
         {"instruction": "Board Zion Shuttle at Visitor Center", "distance": "0.5 km"},
         {"instruction": "Shuttle to stop 6 (The Grotto)", "distance": "9 km"},
         {"instruction": "Disembark at trailhead", "distance": "0.5 km"},
     ]),
    ("Bryce Canyon - Sunrise Point", "Sunset Point", "walking", "1.0 km", 1.0, "15 min", 15,
     "Sunrise Point to Sunset Point along Rim Trail",
     "Sunrise Point, Bryce Canyon NP, UT", "Sunset Point, Bryce Canyon NP, UT", [
         {"instruction": "Follow Rim Trail south", "distance": "0.9 km"},
         {"instruction": "Arrive at Sunset Point overlook", "distance": "0.1 km"},
     ]),
    ("Joshua Tree National Park - West Entrance", "Keys View", "driving", "35 km", 35.0, "45 min", 45,
     "West Entrance to Keys View via Park Blvd",
     "Joshua Tree NP West Entrance, CA", "Keys View, Joshua Tree NP", [
         {"instruction": "Head east on Park Blvd from West Entrance", "distance": "20 km"},
         {"instruction": "Turn south onto Keys View Rd", "distance": "13 km"},
         {"instruction": "Arrive at Keys View overlook parking", "distance": "2 km"},
     ]),
    ("Pike Place Market", "Space Needle", "walking", "1.6 km", 1.6, "22 min", 22,
     "Pike Place Market to Space Needle via Pine St and Seattle Center",
     "Pike Place Market, Seattle, WA", "Space Needle, Seattle Center, WA", [
         {"instruction": "Head east on Pine St", "distance": "0.6 km"},
         {"instruction": "Continue onto 5th Ave N then Broad St", "distance": "0.7 km"},
         {"instruction": "Enter Seattle Center via Thomas St", "distance": "0.2 km"},
         {"instruction": "Arrive at Space Needle base", "distance": "0.1 km"},
     ]),
    ("Boston Common", "Fenway Park", "transit", "4.0 km", 4.0, "20 min", 20,
     "Boston Common to Fenway Park via Green Line",
     "Boston Common, Boston, MA", "Fenway Park, Boston, MA", [
         {"instruction": "Walk to Park Street Station", "distance": "0.2 km"},
         {"instruction": "Board Green Line B/C/D westbound", "distance": "3.5 km"},
         {"instruction": "Alight at Kenmore", "distance": "0.1 km"},
         {"instruction": "Walk to Fenway Park", "distance": "0.2 km"},
     ]),
    ("Wrigley Field", "The Bean (Cloud Gate)", "transit", "11 km", 11.0, "35 min", 35,
     "Wrigley Field to Millennium Park via CTA Red Line",
     "Wrigley Field, Chicago, IL", "Cloud Gate, Millennium Park, Chicago, IL", [
         {"instruction": "Walk to Addison Red Line station", "distance": "0.3 km"},
         {"instruction": "Board Red Line southbound", "distance": "10 km"},
         {"instruction": "Alight at Monroe", "distance": "0.1 km"},
         {"instruction": "Walk east to Millennium Park", "distance": "0.6 km"},
     ]),
    ("San Francisco Ferry Building", "Alcatraz Island", "transit", "2.4 km", 2.4, "20 min", 20,
     "Ferry Building to Alcatraz via Alcatraz Cruises ferry from Pier 33",
     "Ferry Building, San Francisco, CA", "Alcatraz Island, San Francisco Bay, CA", [
         {"instruction": "Walk along Embarcadero to Pier 33", "distance": "0.8 km"},
         {"instruction": "Board Alcatraz Cruises ferry", "distance": "0.1 km"},
         {"instruction": "Ferry to Alcatraz Island", "distance": "1.5 km"},
     ]),
    ("Denver International Airport", "Downtown Denver", "transit", "37 km", 37.0, "37 min", 37,
     "DEN Airport to Union Station via RTD A Line train",
     "Denver International Airport (DEN)", "Union Station, Denver, CO", [
         {"instruction": "Board RTD A Line at DEN station", "distance": "0.3 km"},
         {"instruction": "Direct train to Denver Union Station", "distance": "36 km"},
         {"instruction": "Arrive Union Station", "distance": "0.2 km"},
     ]),
    ("LAX Airport", "Santa Monica Pier", "driving", "15 km", 15.0, "30 min", 30,
     "LAX to Santa Monica Pier via Lincoln Blvd",
     "Los Angeles International Airport (LAX)", "Santa Monica Pier, Santa Monica, CA", [
         {"instruction": "Exit LAX via World Way", "distance": "1.5 km"},
         {"instruction": "Head north on Lincoln Blvd", "distance": "11 km"},
         {"instruction": "Turn left on Colorado Ave", "distance": "1.5 km"},
         {"instruction": "Arrive at Santa Monica Pier", "distance": "1 km"},
     ]),
    ("Disneyland Paris", "Paris Charles de Gaulle Airport", "driving", "35 km", 35.0, "40 min", 40,
     "Disneyland Paris to CDG via A104",
     "Disneyland Paris, Marne-la-Vallée", "Paris-Charles de Gaulle Airport", [
         {"instruction": "Head north on A104 from Marne-la-Vallée", "distance": "25 km"},
         {"instruction": "Take exit onto A1 north", "distance": "5 km"},
         {"instruction": "Follow signs to CDG terminals", "distance": "5 km"},
     ]),
    ("Versailles", "Paris", "transit", "20 km", 20.0, "40 min", 40,
     "Château de Versailles to central Paris via RER C",
     "Palace of Versailles, Versailles, France", "Paris (Musée d'Orsay area)", [
         {"instruction": "Walk to Versailles Château Rive Gauche station", "distance": "0.5 km"},
         {"instruction": "Board RER C northbound", "distance": "18 km"},
         {"instruction": "Disembark at Musée d'Orsay station", "distance": "1.5 km"},
     ]),
    ("Mont-Saint-Michel", "Saint-Malo", "driving", "55 km", 55.0, "1 hr", 60,
     "Mont-Saint-Michel to Saint-Malo via D275 + N176",
     "Mont-Saint-Michel, France", "Saint-Malo, France", [
         {"instruction": "Head north on D275 from Mont-Saint-Michel causeway", "distance": "15 km"},
         {"instruction": "Continue onto N176 west", "distance": "35 km"},
         {"instruction": "Arrive in walled city of Saint-Malo", "distance": "5 km"},
     ]),
    ("Athens (Syntagma)", "Acropolis", "walking", "1.2 km", 1.2, "16 min", 16,
     "Syntagma Square to Acropolis via Plaka",
     "Syntagma Square, Athens", "Acropolis of Athens", [
         {"instruction": "Head south on Filellinon St", "distance": "0.4 km"},
         {"instruction": "Walk through Plaka neighborhood", "distance": "0.6 km"},
         {"instruction": "Climb to Acropolis main entrance", "distance": "0.2 km"},
     ]),
    ("Vatican City", "Trevi Fountain", "walking", "2.5 km", 2.5, "32 min", 32,
     "St. Peter's Square to Trevi Fountain",
     "Vatican City - St. Peter's Square", "Trevi Fountain, Rome", [
         {"instruction": "Head east across Tiber via Ponte Vittorio Emanuele II", "distance": "1.0 km"},
         {"instruction": "Continue along Corso Vittorio Emanuele II", "distance": "1.0 km"},
         {"instruction": "Turn left onto Via del Corso", "distance": "0.3 km"},
         {"instruction": "Arrive at Trevi Fountain via Via delle Muratte", "distance": "0.2 km"},
     ]),
    ("Sagrada Familia", "Park Güell", "transit", "4.0 km", 4.0, "25 min", 25,
     "Sagrada Familia to Park Güell via Barcelona Metro L5",
     "Sagrada Familia, Barcelona", "Park Güell, Barcelona", [
         {"instruction": "Walk to Sagrada Familia metro entrance", "distance": "0.1 km"},
         {"instruction": "Board L5 northbound to El Carmel", "distance": "3 km"},
         {"instruction": "Walk up Avinguda del Coll del Portell", "distance": "0.9 km"},
     ]),
    ("Anne Frank House", "Rijksmuseum", "cycling", "1.5 km", 1.5, "8 min", 8,
     "Anne Frank House to Rijksmuseum via Spiegelgracht",
     "Anne Frank House, Amsterdam", "Rijksmuseum, Amsterdam", [
         {"instruction": "Head south along Prinsengracht canal", "distance": "0.8 km"},
         {"instruction": "Cross Spiegelgracht to Stadhouderskade", "distance": "0.5 km"},
         {"instruction": "Arrive at Rijksmuseum forecourt", "distance": "0.2 km"},
     ]),
    ("Buda Castle", "Hungarian Parliament Building", "walking", "1.4 km", 1.4, "20 min", 20,
     "Buda Castle to Hungarian Parliament via Chain Bridge",
     "Buda Castle, Budapest", "Hungarian Parliament Building, Budapest", [
         {"instruction": "Descend from Buda Castle to Clark Ádám Square", "distance": "0.4 km"},
         {"instruction": "Cross the Chain Bridge over the Danube", "distance": "0.4 km"},
         {"instruction": "Walk north along the riverside", "distance": "0.6 km"},
     ]),
    ("Petronas Twin Towers", "KL Tower", "walking", "1.6 km", 1.6, "22 min", 22,
     "Petronas Twin Towers to KL Tower via KLCC Park",
     "Petronas Twin Towers, KL", "Menara KL Tower, Kuala Lumpur", [
         {"instruction": "Cross KLCC Park", "distance": "0.4 km"},
         {"instruction": "Head west on Jalan P. Ramlee", "distance": "0.8 km"},
         {"instruction": "Climb to KL Tower base via Bukit Nanas forest path", "distance": "0.4 km"},
     ]),
    ("Marina Bay Sands", "Gardens by the Bay", "walking", "0.5 km", 0.5, "8 min", 8,
     "Marina Bay Sands to Gardens by the Bay via Dragonfly Bridge",
     "Marina Bay Sands, Singapore", "Gardens by the Bay, Singapore", [
         {"instruction": "Exit Marina Bay Sands at south face", "distance": "0.1 km"},
         {"instruction": "Cross Dragonfly Bridge", "distance": "0.2 km"},
         {"instruction": "Arrive at Gardens by the Bay (Supertree Grove entrance)", "distance": "0.2 km"},
     ]),
    ("Burj Al Arab", "Dubai Marina", "driving", "8 km", 8.0, "15 min", 15,
     "Burj Al Arab to Dubai Marina via Jumeirah St",
     "Burj Al Arab, Dubai", "Dubai Marina", [
         {"instruction": "Head south on Jumeirah St", "distance": "5 km"},
         {"instruction": "Continue onto King Salman bin Abdulaziz Al Saud St", "distance": "2 km"},
         {"instruction": "Arrive at Dubai Marina Walk", "distance": "1 km"},
     ]),
    ("Bangkok - Grand Palace", "Wat Pho", "walking", "0.5 km", 0.5, "7 min", 7,
     "Grand Palace to Wat Pho",
     "Grand Palace, Bangkok", "Wat Pho, Bangkok", [
         {"instruction": "Exit Grand Palace via Wiset Chai Si Gate", "distance": "0.2 km"},
         {"instruction": "Walk south on Maha Rat Rd", "distance": "0.3 km"},
     ]),
    ("Angkor Wat", "Bayon Temple", "cycling", "5.5 km", 5.5, "25 min", 25,
     "Angkor Wat to Bayon Temple via Charles de Gaulle Rd",
     "Angkor Wat, Siem Reap", "Bayon Temple, Angkor Thom", [
         {"instruction": "Head north on Charles de Gaulle Rd", "distance": "4 km"},
         {"instruction": "Enter Angkor Thom via south gate", "distance": "1 km"},
         {"instruction": "Continue to Bayon", "distance": "0.5 km"},
     ]),
    ("Mexico City - Zócalo", "Teotihuacan Pyramids", "driving", "50 km", 50.0, "1 hr", 60,
     "Zócalo to Teotihuacan via Mexico 85D",
     "Plaza de la Constitución (Zócalo), Mexico City", "Teotihuacan Pyramids, Estado de México", [
         {"instruction": "Head north on Eje Central Lázaro Cárdenas", "distance": "5 km"},
         {"instruction": "Take Insurgentes Norte to Mexico 85D toll highway", "distance": "10 km"},
         {"instruction": "Continue Mexico 85D north", "distance": "30 km"},
         {"instruction": "Exit toward Teotihuacan archaeological site", "distance": "5 km"},
     ]),
    ("Iguazu Falls (Brazilian Side)", "Iguazu Falls (Argentine Side)", "driving", "30 km", 30.0, "45 min", 45,
     "Foz do Iguaçu (BR) to Puerto Iguazú (AR) via Tancredo Neves Bridge",
     "Iguaçu Falls Visitor Center, Brazil", "Iguazú Falls National Park, Argentina", [
         {"instruction": "Head east on BR-469 toward border", "distance": "12 km"},
         {"instruction": "Cross Tancredo Neves Bridge (passport required)", "distance": "0.5 km"},
         {"instruction": "Continue on RN-12 in Argentina", "distance": "15 km"},
         {"instruction": "Arrive Argentine national park entrance", "distance": "2 km"},
     ]),
    ("Machu Picchu", "Aguas Calientes", "transit", "8 km", 8.0, "30 min", 30,
     "Machu Picchu ruins to Aguas Calientes via Consettur shuttle bus",
     "Machu Picchu, Peru", "Aguas Calientes, Peru", [
         {"instruction": "Board Consettur shuttle at Machu Picchu entrance", "distance": "0.2 km"},
         {"instruction": "Descend via Hiram Bingham Highway switchbacks", "distance": "7.5 km"},
         {"instruction": "Arrive in Aguas Calientes bus terminal", "distance": "0.3 km"},
     ]),
    ("Christ the Redeemer", "Sugarloaf Mountain", "driving", "18 km", 18.0, "40 min", 40,
     "Christ the Redeemer to Sugarloaf Mountain cable car base",
     "Christ the Redeemer, Rio de Janeiro", "Sugarloaf Cable Car, Praia Vermelha, Rio", [
         {"instruction": "Descend Corcovado access road", "distance": "5 km"},
         {"instruction": "Take Av. Atlântica along Copacabana", "distance": "9 km"},
         {"instruction": "Continue to Praia Vermelha", "distance": "3 km"},
         {"instruction": "Arrive at Bondinho cable car station", "distance": "1 km"},
     ]),
    ("Table Mountain", "Cape Point", "driving", "70 km", 70.0, "1 hr 30 min", 90,
     "Table Mountain to Cape Point via Chapman's Peak Drive",
     "Table Mountain, Cape Town", "Cape Point, Cape Town", [
         {"instruction": "Descend Tafelberg Rd", "distance": "4 km"},
         {"instruction": "Head south on Victoria Rd (Chapman's Peak)", "distance": "20 km"},
         {"instruction": "Continue M65 through Simon's Town", "distance": "30 km"},
         {"instruction": "Enter Cape Point Nature Reserve", "distance": "10 km"},
         {"instruction": "Arrive Cape Point lighthouse parking", "distance": "6 km"},
     ]),
    ("Pyramids of Giza", "Egyptian Museum", "driving", "20 km", 20.0, "35 min", 35,
     "Giza Pyramids to Egyptian Museum in Tahrir Square",
     "Great Pyramid of Giza, Egypt", "Egyptian Museum, Tahrir Square, Cairo", [
         {"instruction": "Head east on Al Haram St", "distance": "8 km"},
         {"instruction": "Cross Nile via 6th of October Bridge", "distance": "5 km"},
         {"instruction": "Continue to Tahrir Square", "distance": "5 km"},
         {"instruction": "Arrive at Egyptian Museum main entrance", "distance": "2 km"},
     ]),
    ("San Francisco", "Sausalito", "transit", "8 km", 8.0, "30 min", 30,
     "San Francisco Ferry Building to Sausalito via Golden Gate Ferry",
     "Ferry Building, San Francisco, CA", "Sausalito Ferry Terminal, Sausalito, CA", [
         {"instruction": "Board Golden Gate Ferry at SF Ferry Building", "distance": "0.1 km"},
         {"instruction": "Ferry crosses SF Bay around Alcatraz", "distance": "7.5 km"},
         {"instruction": "Disembark at Sausalito Ferry Terminal", "distance": "0.4 km"},
     ]),
    ("Stockholm Central", "Vasa Museum", "transit", "3.5 km", 3.5, "20 min", 20,
     "Stockholm Central Station to Vasa Museum via SL bus 69 + walk",
     "Stockholm Central Station, Sweden", "Vasa Museum, Djurgården, Stockholm", [
         {"instruction": "Walk to Sergels Torg bus stop", "distance": "0.4 km"},
         {"instruction": "Board SL bus 69 toward Djurgården", "distance": "2.6 km"},
         {"instruction": "Walk from Djurgårdsbron to Vasa Museum", "distance": "0.5 km"},
     ]),
]


def expand_routes(db, Route):
    """Add more routes for breadth. Idempotent: gate by Route count."""
    if Route.query.count() >= 100:
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
              .limit(4500).all())
    if not places:
        return

    rng = random.Random(31415)

    # ---------- REVIEWS (~3200) ----------
    if Review.query.count() == 0:
        target = 3200
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
            if (i + 1) % 200 == 0:
                db.session.commit()
        db.session.commit()
        print(f"seed_user_content: added {Review.query.count()} reviews")

    # ---------- PHOTOS (~1500) ----------
    if Photo.query.count() == 0:
        target = 1500
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
            if (i + 1) % 200 == 0:
                db.session.commit()
        db.session.commit()
        print(f"seed_user_content: added {Photo.query.count()} photos")

    # ---------- TIMELINE ENTRIES (~820) ----------
    if TimelineEntry.query.count() == 0:
        target = 820
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

# ============================================================================
# R4 additions: OSM-tile-style place expansion + per-place extras backfill
# (popular times, accessibility, service options, menu, ratings distribution)
# + curated transit lines.
# Every value is hash-derived from the row's slug so rebuilds stay
# byte-identical across machines.
# ============================================================================

# Service-business templates: small local businesses every dense city has —
# these are the "OSM tile-density" tail of the catalog.  ~70 entries × 812
# cities → ~57k more places to push the total past 130k.
_R4_TEMPLATES = [
    # (cat_slug, name_pattern, subtitle, desc, price, rlo, rhi)
    ("services", "{anchor} Dry Cleaners", "Dry cleaner",
     "Family dry-cleaning shop with same-day service, alterations, and shoe repair.", "$$", 4.0, 4.7),
    ("services", "{anchor} Laundromat", "Laundromat",
     "Coin-operated laundromat with high-efficiency washers, drop-off service, and free Wi-Fi.", "$", 3.7, 4.4),
    ("services", "{anchor} Tailor Shop", "Tailor",
     "Custom tailor shop with on-site alterations, hemming, and wedding-attire fittings.", "$$", 4.4, 4.9),
    ("services", "{anchor} Shoe Repair", "Shoe repair",
     "Cobbler offering resoling, heel replacement, leather conditioning, and bag repair.", "$$", 4.5, 4.9),
    ("services", "{anchor} Computer Repair", "Computer repair",
     "Computer & laptop repair shop with same-day data recovery and screen replacements.", "$$", 4.0, 4.7),
    ("services", "{anchor} Phone Repair", "Phone repair",
     "Phone and tablet repair store offering screen, battery, and water-damage service.", "$$", 4.1, 4.7),
    ("services", "{anchor} Locksmith 24h", "24-hour locksmith",
     "24-hour locksmith for residential lockouts, auto unlocks, and rekeying.", "$$", 4.0, 4.7),
    ("services", "{anchor} Print & Copy Center", "Print & copy",
     "Print, scan, and copy center with large-format printing, binding, and notary on staff.", "$", 4.0, 4.6),
    ("services", "{anchor} Plumbing Services", "Plumber",
     "Licensed plumbing service for leak repair, water heaters, drain cleaning, and re-piping.", "$$", 4.2, 4.8),
    ("services", "{anchor} Electricians Co.", "Electrician",
     "Licensed electricians offering panel upgrades, EV-charger installation, and lighting work.", "$$", 4.3, 4.8),
    ("services", "{anchor} HVAC Heating & Cooling", "HVAC contractor",
     "HVAC contractor servicing furnaces, AC units, heat pumps, and ducting.", "$$", 4.1, 4.7),
    ("services", "{anchor} Garage Door Repair", "Garage door repair",
     "Garage door repair & installation — broken springs, openers, panels, and full doors.", "$$", 4.2, 4.7),
    ("services", "{anchor} House Cleaning Co.", "Cleaning service",
     "Residential cleaning service with bonded & insured staff, recurring or one-time visits.", "$$", 4.3, 4.8),
    ("services", "{anchor} Pest Control", "Pest control",
     "Pest control company treating ants, roaches, rodents, termites, and bed bugs.", "$$", 4.1, 4.7),
    ("services", "{anchor} Landscaping & Lawn", "Landscaper",
     "Landscaping & lawn-care company offering mowing, mulch, tree trimming, and design.", "$$", 4.2, 4.7),
    ("services", "{anchor} Roofing Contractors", "Roofer",
     "Roofing contractor with shingle, metal, flat-roof installation, and insurance claims help.", "$$$", 4.1, 4.7),
    ("services", "{anchor} Window Cleaning Co.", "Window cleaning",
     "Residential and commercial window cleaning — interior, exterior, and screens.", "$$", 4.3, 4.8),
    ("services", "{anchor} Carpet Cleaning", "Carpet cleaning",
     "Hot-water-extraction carpet cleaning with stain removal and pet-odor treatment.", "$$", 4.0, 4.6),
    ("services", "{anchor} Moving Company", "Movers",
     "Local & long-distance movers offering packing, storage, and piano moving.", "$$", 4.0, 4.6),
    ("services", "{anchor} Storage Units", "Self-storage",
     "Self-storage facility with climate-controlled units, drive-up access, and 24h gate.", "$$", 4.0, 4.6),
    ("services", "{anchor} Towing Service", "Tow truck",
     "24-hour towing service for accidents, jump-starts, and roadside lockouts.", "$$", 3.8, 4.4),
    ("services", "{anchor} Tax Preparation Office", "Tax prep",
     "Tax preparation office for individuals and small businesses, year-round appointments.", "$$", 4.2, 4.8),
    ("services", "{anchor} Legal Aid Clinic", "Lawyer",
     "Legal aid clinic providing free consultations on tenant, family, and immigration law.", "Free", 4.4, 4.9),
    ("services", "{anchor} Real Estate Office", "Real estate office",
     "Real estate brokerage with residential and commercial agents servicing the metro area.", "$$", 4.0, 4.6),
    ("services", "{anchor} Notary Public", "Notary",
     "Walk-in notary public, mobile-notary appointments, and apostille service.", "$", 4.5, 4.9),
    ("services", "{anchor} Wedding Photography Studio", "Photography studio",
     "Wedding and portrait photography studio with engagement-session bundles.", "$$$", 4.6, 4.9),
    ("services", "{anchor} Bike Repair Shop", "Bike repair",
     "Bike repair shop with tune-ups, flat-fix, drivetrain service, and used-bike sales.", "$$", 4.4, 4.9),
    ("services", "{anchor} Watch & Jewelry Repair", "Jewelry repair",
     "Watch battery, sizing, and jewelry repair while you wait.", "$$", 4.4, 4.9),
    ("services", "{anchor} Music Lessons Studio", "Music school",
     "Private music lessons in piano, guitar, voice, and strings for all ages.", "$$", 4.6, 4.9),
    ("services", "{anchor} Dance Studio", "Dance studio",
     "Dance studio offering ballet, jazz, hip-hop, and adult drop-in classes.", "$$", 4.5, 4.9),
    ("restaurants", "{anchor} Pizzeria", "Pizzeria",
     "Casual pizzeria with hand-tossed pies, daily specials, and craft beer.", "$$", 4.1, 4.7),
    ("restaurants", "{anchor} Burger Bar", "Burger restaurant",
     "Burger bar with grass-fed patties, classic shakes, and a curated whiskey list.", "$$", 4.0, 4.6),
    ("restaurants", "{anchor} Ramen House", "Ramen restaurant",
     "Ramen specialist with rich tonkotsu broth, gyoza, and bao buns.", "$$", 4.3, 4.8),
    ("restaurants", "{anchor} Vegan Cafe", "Vegan restaurant",
     "Plant-based cafe with bowls, sandwiches, smoothies, and house-made desserts.", "$$", 4.3, 4.8),
    ("restaurants", "{anchor} BBQ Smokehouse", "Barbecue",
     "Slow-smoked BBQ with brisket, ribs, pulled pork, and house sauces.", "$$", 4.3, 4.8),
    ("restaurants", "{anchor} Korean Grill", "Korean BBQ",
     "Korean BBQ with tabletop grills, banchan, and soju cocktails.", "$$$", 4.4, 4.9),
    ("restaurants", "{anchor} Indian Kitchen", "Indian restaurant",
     "Indian kitchen serving regional curries, tandoor specialties, and weekend buffet.", "$$", 4.3, 4.8),
    ("restaurants", "{anchor} Thai Garden", "Thai restaurant",
     "Thai restaurant with pad Thai, curry, and a deep wine-and-cocktail program.", "$$", 4.2, 4.7),
    ("restaurants", "{anchor} Mediterranean Grill", "Mediterranean",
     "Mediterranean grill with falafel, kebabs, hummus, and fresh pita.", "$$", 4.2, 4.7),
    ("restaurants", "{anchor} Ice Cream Parlor", "Ice cream shop",
     "Ice-cream parlor with house-churned flavors, vegan options, and waffle cones.", "$", 4.5, 4.9),
    ("restaurants", "{anchor} Donut Shop", "Donut shop",
     "Donut shop with old-fashioned, raised, and seasonal-flavor donuts plus drip coffee.", "$", 4.4, 4.9),
    ("restaurants", "{anchor} Bubble Tea House", "Bubble tea",
     "Bubble tea cafe with milk teas, fruit teas, cheese foam, and snack menu.", "$", 4.2, 4.7),
    ("restaurants", "{anchor} Juice Bar", "Juice bar",
     "Juice bar with cold-pressed juices, smoothie bowls, and acai.", "$$", 4.3, 4.8),
    ("restaurants", "{anchor} Wine Bar", "Wine bar",
     "Wine bar with 50+ pours by the glass, charcuterie, and small plates.", "$$$", 4.3, 4.8),
    ("restaurants", "{anchor} Cocktail Lounge", "Cocktail bar",
     "Cocktail lounge with seasonal menu, classic rotation, and zero-proof options.", "$$$", 4.4, 4.9),
    ("restaurants", "{anchor} Sports Bar & Grill", "Sports bar",
     "Sports bar with wings, beers on tap, and every major-league game on screen.", "$$", 3.9, 4.5),
    ("restaurants", "{anchor} Diner", "Diner",
     "Classic American diner serving all-day breakfast, milkshakes, and blue-plate specials.", "$", 4.0, 4.6),
    ("restaurants", "{anchor} Food Truck Court", "Food trucks",
     "Rotating food-truck court with seating, picnic tables, and weekend live music.", "$", 4.2, 4.7),
    ("restaurants", "{anchor} Bakery", "Bakery",
     "Bakery with sourdough, croissants, cakes, and custom-order cookies.", "$$", 4.4, 4.9),
    ("restaurants", "{anchor} Sandwich Shop", "Sandwich shop",
     "Sandwich shop with hot subs, deli classics, and house-roasted meats.", "$", 4.2, 4.7),
    ("shopping", "{anchor} Hardware Store", "Hardware store",
     "Independent hardware store with paint mixing, key cutting, and tool rentals.", "$$", 4.3, 4.8),
    ("shopping", "{anchor} Garden Center", "Garden center",
     "Garden center with plants, seeds, soil, pottery, and weekend workshops.", "$$", 4.4, 4.9),
    ("shopping", "{anchor} Pet Supply", "Pet store",
     "Pet supply store with food, treats, toys, and grooming appointments.", "$$", 4.3, 4.8),
    ("shopping", "{anchor} Toy Store", "Toy store",
     "Independent toy store with curated wooden toys, board games, and crafts.", "$$", 4.5, 4.9),
    ("shopping", "{anchor} Vintage Thrift", "Thrift store",
     "Curated vintage thrift store with rotating designer, denim, and accessories.", "$", 4.2, 4.7),
    ("shopping", "{anchor} Music Records Shop", "Record store",
     "Independent record store with vinyl, CDs, listening stations, and in-store events.", "$$", 4.5, 4.9),
    ("shopping", "{anchor} Florist", "Florist",
     "Florist with same-day delivery, wedding florals, and seasonal bouquets.", "$$", 4.5, 4.9),
    ("shopping", "{anchor} Art Supply", "Art supply",
     "Art supply store with paints, papers, brushes, and weekend studio classes.", "$$", 4.4, 4.9),
    ("shopping", "{anchor} Comics Shop", "Comics shop",
     "Comics shop with weekly new releases, back issues, and board-game night.", "$$", 4.4, 4.9),
    ("shopping", "{anchor} Camera Store", "Camera store",
     "Camera store with new and used gear, rentals, and on-site sensor cleaning.", "$$$", 4.4, 4.9),
    ("health-beauty", "{anchor} Nail Salon", "Nail salon",
     "Nail salon with manicures, pedicures, gel, and dip-powder service.", "$$", 4.3, 4.8),
    ("health-beauty", "{anchor} Barber Shop", "Barber",
     "Classic barber shop with haircuts, hot-towel shaves, and beard trims.", "$$", 4.5, 4.9),
    ("health-beauty", "{anchor} Massage Therapy", "Massage",
     "Therapeutic massage practice — deep tissue, Swedish, and prenatal.", "$$$", 4.6, 4.9),
    ("health-beauty", "{anchor} Skin Clinic", "Skin clinic",
     "Medical-grade skin clinic with facials, laser, and dermatology referrals.", "$$$", 4.4, 4.9),
    ("health-beauty", "{anchor} Tanning Studio", "Tanning",
     "Sunless tanning studio with airbrush, spray-booth, and bed options.", "$$", 4.1, 4.7),
    ("health-beauty", "{anchor} Eyelash Bar", "Lash bar",
     "Eyelash extension and lift bar with same-day appointments.", "$$$", 4.4, 4.9),
    ("fitness", "{anchor} Pilates Studio", "Pilates",
     "Reformer Pilates studio with private and small-group sessions.", "$$$", 4.5, 4.9),
    ("fitness", "{anchor} CrossFit Box", "CrossFit",
     "CrossFit box with daily WODs, foundations classes, and on-ramp track.", "$$$", 4.4, 4.9),
    ("fitness", "{anchor} Boxing Gym", "Boxing",
     "Boxing gym with private coaching, group classes, and youth program.", "$$", 4.4, 4.9),
    ("fitness", "{anchor} Martial Arts Dojo", "Martial arts",
     "Family martial-arts dojo teaching karate, BJJ, and Muay Thai.", "$$", 4.5, 4.9),
    ("fitness", "{anchor} Swimming Pool", "Aquatic center",
     "Public aquatic center with lap pool, family pool, and swim lessons.", "$", 4.3, 4.8),
    ("entertainment", "{anchor} Karaoke Lounge", "Karaoke",
     "Private-room karaoke lounge with full bar and snacks.", "$$", 4.3, 4.8),
    ("entertainment", "{anchor} Escape Room", "Escape room",
     "Escape-room venue with 4-6 themed rooms; reservations recommended.", "$$", 4.5, 4.9),
    ("entertainment", "{anchor} Arcade Lounge", "Arcade",
     "Arcade lounge with classic cabinets, pinball, and craft cocktails.", "$$", 4.4, 4.9),
    ("entertainment", "{anchor} Pool & Billiards Hall", "Billiards",
     "Pool hall with regulation tables, weekly tournaments, and full bar.", "$$", 4.2, 4.7),
    ("entertainment", "{anchor} Mini Golf", "Mini golf",
     "Outdoor mini-golf course with 18 themed holes and seasonal snack bar.", "$$", 4.4, 4.9),
]


def expand_places_r4(db, Place, Category, City):
    """R4 OSM-tile-style expansion: small-business templates per city.

    Idempotent: skip once Place count exceeds 130000.
    """
    if Place.query.count() >= 130000:
        return

    random.seed(20260516)
    cat_by_slug = {c.slug: c for c in Category.query.all()}
    cities = City.query.order_by(City.id).all()
    if not cities:
        return

    donor_pool = []
    for p in Place.query.filter(Place.hero_image.like("/static/images/places/%")).limit(80).all():
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
        anchor = city.display_name.split(",")[0].split(" ")[0]
        templates = list(_R4_TEMPLATES)
        slug_seed = int.from_bytes(
            hashlib.md5(("r4-" + city.slug).encode()).digest()[:4], "big")
        rng = random.Random(slug_seed)
        rng.shuffle(templates)

        for idx, (cat_slug, pattern, subtitle, desc, price, rlo, rhi) in enumerate(templates):
            cat = cat_by_slug.get(cat_slug)
            if not cat:
                continue
            slug = f"r4-{city.slug}-{cat_slug}-{idx}"
            if Place.query.filter_by(slug=slug).first():
                continue

            name = pattern.format(anchor=anchor)
            # Per-row deterministic local RNG so individual jitter
            # doesn't depend on earlier row's RNG state.
            local_seed = int.from_bytes(
                hashlib.md5(slug.encode()).digest()[:4], "big")
            lrng = random.Random(local_seed)

            hero, gallery = donor_pool[local_seed % len(donor_pool)]
            lat = city.lat + (local_seed % 800 - 400) / 10000.0  # ±0.04
            lng = city.lng + ((local_seed // 800) % 1000 - 500) / 10000.0
            rating = round(rlo + (lrng.random()) * (rhi - rlo), 1)
            review_count = 20 + (local_seed % 4800)

            tags = [cat_slug, anchor.lower(), city.country.lower()]
            hours_pick = (local_seed >> 4) % 6
            hours_options = [
                "Mon-Sun: 9:00 AM - 9:00 PM",
                "Mon-Sat: 10:00 AM - 8:00 PM, Sun 11:00 AM - 6:00 PM",
                "Tue-Sun: 11:00 AM - 10:00 PM, Closed Mon",
                "Open 24 hours",
                "Mon-Fri: 7:00 AM - 7:00 PM, Weekends 8:00 AM - 5:00 PM",
                "Mon-Sun: 6:00 AM - 10:00 PM",
            ]
            db.session.add(Place(
                slug=slug, name=name, category_id=cat.id, city_id=city.id,
                subtitle=subtitle,
                description=desc,
                address=f"{20 + (local_seed % 980)} {['Main','Oak','Park','Elm','Pine','Cedar'][local_seed % 6]} St, {city.display_name}",
                phone=f"+{1 + (local_seed % 9)} {200 + (local_seed % 800)} {1000 + (local_seed % 9000)}",
                hours=hours_options[hours_pick],
                website=google_maps_search_url(name, city.display_name),
                rating=rating,
                review_count=review_count,
                price_level=price,
                hero_image=hero,
                photos_json=json.dumps(gallery[:5]),
                lat=lat, lng=lng,
                tags_json=json.dumps(tags),
                subcategory=subtitle,
                is_24h=(hours_pick == 3),
                is_popular=(rating >= 4.6 and (local_seed % 5) == 0),
                has_parking_lot=(cat_slug in ("shopping", "fitness") or (local_seed % 3) == 0),
                delivery_available=(cat_slug == "restaurants" and (local_seed % 2) == 0),
            ))
            added += 1
            if added % 500 == 0:
                db.session.commit()

    db.session.commit()
    print(f"expand_places_r4: added {added} small-business places (total {Place.query.count()})")


# ---------------------------------------------------------------------------
# Per-place extras backfill: deterministic from md5(slug).  Fills in the
# R4 columns (popular_times, accessibility, service options, menu, ratings
# distribution) for every Place row.  Skips rows that already look filled
# so warm restarts don't re-randomise.
# ---------------------------------------------------------------------------

def _seed_int(slug, salt):
    return int.from_bytes(
        hashlib.md5((salt + ":" + slug).encode()).digest()[:4], "big")


def _det_bool(slug, salt, threshold):
    """Deterministic boolean: True if hash mod 100 < threshold (0..100)."""
    return (_seed_int(slug, salt) % 100) < threshold


def _det_choice(slug, salt, options):
    return options[_seed_int(slug, salt) % len(options)]


def _gen_popular_times(slug, category_slug, busiest_day_idx, peak_hour):
    """Generate a 7×24 matrix of 0..100 ints centred on (busiest_day, peak_hour).

    Open hours vary by category (bars peak at night, bakeries at AM).
    Shape: bell around peak_hour, scaled per day, zero outside open window.
    """
    cat = category_slug or ""
    # category-specific open window (start_h, end_h, base_amp)
    if cat in ("restaurants",) and "bar" in slug:
        start, end, base = 16, 24, 70
    elif cat in ("entertainment",) and ("bar" in slug or "club" in slug or "comedy" in slug):
        start, end, base = 18, 24, 75
    elif cat in ("coffee-shops", "bakery"):
        start, end, base = 6, 19, 65
    elif cat in ("hotels",):
        start, end, base = 0, 24, 35
    elif cat in ("hospitals", "police-stations", "fire-stations", "gas-stations", "atms"):
        start, end, base = 0, 24, 30
    elif cat in ("museums", "libraries"):
        start, end, base = 10, 18, 50
    elif cat in ("parks", "beaches", "playgrounds", "dog-parks"):
        start, end, base = 6, 21, 55
    elif cat in ("shopping", "indoor-mall-shops"):
        start, end, base = 10, 21, 60
    elif cat in ("schools", "campus-buildings"):
        start, end, base = 7, 17, 65
    elif cat in ("transit", "bus-stops"):
        start, end, base = 5, 23, 60
    else:
        start, end, base = 8, 22, 55

    matrix = [[0] * 24 for _ in range(7)]
    # per-day multiplier seeded by slug+day so curves differ across rows
    for d in range(7):
        dmul = 0.55 + (_seed_int(slug, f"d{d}") % 100) / 100.0 * 0.55  # 0.55..1.10
        if d == busiest_day_idx:
            dmul *= 1.15
        elif d == (busiest_day_idx + 1) % 7:
            dmul *= 0.92
        if cat in ("entertainment", "restaurants") and d in (4, 5):
            dmul *= 1.05  # Fri/Sat busier for nightlife
        if cat in ("services", "schools", "campus-buildings") and d in (5, 6):
            dmul *= 0.45  # weekend dip for service/school
        for h in range(24):
            if not (start <= h < end if start < end else (h >= start or h < end)):
                matrix[d][h] = 0
                continue
            # bell curve around peak_hour with width 4h
            dist = abs(h - peak_hour)
            shape = max(0, 100 - dist * 14)  # 100..40..0
            val = int(base * dmul * shape / 100.0)
            val = max(0, min(100, val))
            matrix[d][h] = val
    return matrix


def _hours_dict_from_string(hours_str):
    """Best-effort parse of the canonical `hours` string into a 7-day dict.

    Handles the dialects seen in build_places + expand_places + R4 templates:
      'Open 24 hours'                              -> all days 'Open 24 hours'
      'Mon-Sun: 9:00 AM - 9:00 PM'                 -> all days
      'Mon-Fri: ..., Weekends: ...'                -> weekdays + weekend
      'Mon-Sat: ..., Sun ...'                      -> weekdays + Sun
      'Tue-Sun: ..., Closed Mon'                   -> Mon Closed, rest range
      'Mon-Thu: A, Fri-Sat: B'                     -> Mon..Thu A, Fri..Sat B
    Returns {} when nothing recognised — the template will skip the block.
    """
    if not hours_str:
        return {}
    s = hours_str.replace("–", "-").replace("—", "-")
    days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    out = {d: "" for d in days}
    lower = s.lower()
    if "24 hour" in lower or "open 24" in lower:
        return {d: "Open 24 hours" for d in days}

    import re as _re
    # Split on commas first so each segment can be processed in isolation.
    parts = [p.strip() for p in s.split(",")]
    DAY_IDX = {"mon": 0, "tue": 1, "wed": 2, "thu": 3,
               "fri": 4, "sat": 5, "sun": 6}

    def _apply(idxs, val):
        for i in idxs:
            if 0 <= i < 7:
                out[days[i]] = val

    for part in parts:
        p = part.strip()
        pl = p.lower()
        if not p:
            continue
        # "Closed Mon" / "Closed Sun"
        m = _re.match(r"^closed\s+([a-z]{3})$", pl)
        if m:
            d = m.group(1)
            if d in DAY_IDX:
                _apply([DAY_IDX[d]], "Closed")
                continue
        # "Weekends: X" / "Weekends X"
        m = _re.match(r"^weekends[:\s]+(.+)$", pl)
        if m:
            _apply([5, 6], m.group(1).strip())
            continue
        # "Mon-Fri: X" / "Mon-Sun: X" range
        m = _re.match(r"^([a-z]{3})\s*-\s*([a-z]{3})[:\s]+(.+)$", pl)
        if m:
            a, b, val = m.group(1), m.group(2), m.group(3).strip()
            if a in DAY_IDX and b in DAY_IDX:
                ai, bi = DAY_IDX[a], DAY_IDX[b]
                if ai <= bi:
                    _apply(list(range(ai, bi + 1)), val)
                else:
                    # wrap (rare)
                    _apply(list(range(ai, 7)) + list(range(0, bi + 1)), val)
                continue
        # "Sun X" / "Mon X" single-day
        m = _re.match(r"^([a-z]{3})[:\s]+(.+)$", pl)
        if m:
            d, val = m.group(1), m.group(2).strip()
            if d in DAY_IDX:
                _apply([DAY_IDX[d]], val)
                continue
    # Drop empty days so the template either shows full data or nothing
    if not any(out.values()):
        return {}
    # Promote blanks to "Closed" so the row still renders informatively
    for d in days:
        if not out[d]:
            out[d] = "Closed"
    return out


_MENU_TEMPLATES = {
    "italian": [
        ("Starters", [("Bruschetta", "Toasted bread, tomato, basil.", 9),
                      ("Caprese Salad", "Mozzarella, tomato, basil.", 12),
                      ("Arancini", "Risotto fritters with marinara.", 11)]),
        ("Pasta",    [("Spaghetti Carbonara", "Egg, pecorino, guanciale.", 18),
                      ("Penne Arrabbiata", "Tomato, chili, garlic.", 16),
                      ("Linguine alle Vongole", "Clams, white wine, parsley.", 24)]),
        ("Pizza",    [("Margherita", "Tomato, mozzarella, basil.", 16),
                      ("Diavola", "Spicy salami, mozzarella.", 18),
                      ("Quattro Formaggi", "Four-cheese blend.", 19)]),
        ("Dessert",  [("Tiramisu", "Espresso-soaked ladyfingers.", 10),
                      ("Cannoli", "Sicilian ricotta-filled pastry.", 9)]),
    ],
    "asian": [
        ("Starters", [("Edamame", "Lightly salted soybeans.", 7),
                      ("Gyoza", "Pork dumplings, ponzu.", 11),
                      ("Spring Rolls", "Vegetable, sweet chili sauce.", 9)]),
        ("Ramen",    [("Tonkotsu Ramen", "Pork-bone broth, chashu.", 17),
                      ("Miso Ramen", "Soybean broth, corn, scallion.", 16),
                      ("Shoyu Ramen", "Soy-based broth, bamboo.", 16)]),
        ("Rice",     [("Chicken Katsu Don", "Breaded chicken on rice.", 16),
                      ("Beef Bulgogi Bowl", "Marinated beef, kimchi.", 19)]),
        ("Dessert",  [("Mochi Ice Cream", "Assorted flavors.", 8),
                      ("Matcha Cheesecake", "Green tea cheesecake.", 9)]),
    ],
    "american": [
        ("Starters", [("Wings", "Buffalo, BBQ, or dry-rub.", 14),
                      ("Loaded Fries", "Cheese, bacon, scallion.", 12),
                      ("Caesar Salad", "Romaine, parmesan, crouton.", 13)]),
        ("Burgers",  [("Classic Cheeseburger", "American, lettuce, tomato.", 16),
                      ("Bacon Cheddar Burger", "Smoked bacon, cheddar.", 18),
                      ("Veggie Burger", "House black-bean patty.", 15)]),
        ("Mains",    [("Smoked Brisket", "12 hr smoked, served by oz.", 26),
                      ("Half Roast Chicken", "Herb butter, mashed potato.", 22)]),
        ("Dessert",  [("Apple Pie", "Cinnamon, vanilla ice cream.", 9),
                      ("Brownie Sundae", "Warm brownie, fudge.", 10)]),
    ],
    "cafe": [
        ("Coffee",   [("Drip Coffee", "Daily single-origin.", 4),
                      ("Espresso", "Double shot.", 4),
                      ("Cappuccino", "Espresso, steamed milk.", 5),
                      ("Pour Over", "Hand-poured single-origin.", 6)]),
        ("Pastries", [("Croissant", "Butter, flaky.", 4),
                      ("Almond Croissant", "Filled with frangipane.", 5),
                      ("Blueberry Muffin", "House-made.", 4)]),
        ("Brunch",   [("Avocado Toast", "Multigrain, lemon, chili.", 12),
                      ("Eggs Benedict", "English muffin, hollandaise.", 14)]),
    ],
    "bar": [
        ("Cocktails", [("Old Fashioned", "Bourbon, bitters, orange.", 14),
                       ("Negroni", "Gin, Campari, vermouth.", 14),
                       ("Margarita", "Tequila, lime, agave.", 13),
                       ("Mezcal Mule", "Mezcal, ginger, lime.", 15)]),
        ("Wine",      [("House Red", "Daily selection by the glass.", 12),
                       ("House White", "Daily selection by the glass.", 12),
                       ("Sparkling", "Brut, by the glass.", 13)]),
        ("Bites",     [("Charcuterie Board", "Cured meats, cheeses.", 22),
                       ("Olives & Almonds", "Marinated, warm.", 9)]),
    ],
}


def _menu_template_for(slug, name_lc, category_slug):
    if "pizza" in name_lc or "trattoria" in name_lc or "italian" in name_lc or "osteria" in name_lc:
        return _MENU_TEMPLATES["italian"]
    if ("ramen" in name_lc or "sushi" in name_lc or "noodle" in name_lc
            or "korean" in name_lc or "thai" in name_lc or "asian" in name_lc):
        return _MENU_TEMPLATES["asian"]
    if "cafe" in name_lc or "coffee" in name_lc or "bakery" in name_lc or "donut" in name_lc:
        return _MENU_TEMPLATES["cafe"]
    if "bar" in name_lc or "lounge" in name_lc or "wine" in name_lc or "cocktail" in name_lc:
        return _MENU_TEMPLATES["bar"]
    if category_slug == "restaurants":
        return _MENU_TEMPLATES["american"]
    return None


def backfill_place_extras(db, Place, Category):
    """Deterministic backfill of R4 columns for every Place row.

    Skips rows that already have popular_times_json filled (so warm restarts
    are no-ops).  All values derive from md5(slug + salt) so byte-id holds.
    """
    # Cheap completion check: if 90% of rows already have popular_times
    # filled, treat as done.
    sample_n = Place.query.count()
    if sample_n == 0:
        return
    filled = (Place.query
              .filter(Place.popular_times_json != "[]",
                      Place.popular_times_json != "")
              .count())
    if filled >= sample_n * 0.9:
        return

    cat_by_id = {c.id: c.slug for c in Category.query.all()}
    DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    batch = 0
    total = 0
    BATCH = 1500
    # Stream in chunks to keep memory low at 130k rows
    offset = 0
    while True:
        rows = (Place.query
                .order_by(Place.id)
                .offset(offset).limit(BATCH).all())
        if not rows:
            break
        offset += BATCH
        for p in rows:
            slug = p.slug or ""
            cat_slug = cat_by_id.get(p.category_id, "")
            name_lc = (p.name or "").lower()

            # busiest day/hour deterministic from slug
            if cat_slug in ("entertainment", "restaurants") and ("bar" in slug or "club" in slug):
                busy_d_options = [4, 5]   # Fri/Sat
                base_hour = 21
            elif cat_slug == "coffee-shops" or "cafe" in name_lc:
                busy_d_options = [0, 1, 2, 5]
                base_hour = 8
            elif cat_slug in ("services", "schools"):
                busy_d_options = [1, 2, 3]
                base_hour = 11
            elif cat_slug == "shopping" or cat_slug == "indoor-mall-shops":
                busy_d_options = [5, 6]   # weekend
                base_hour = 14
            else:
                busy_d_options = [3, 4, 5]
                base_hour = 13
            busy_d = busy_d_options[_seed_int(slug, "bd") % len(busy_d_options)]
            peak_h = max(0, min(23, base_hour + (_seed_int(slug, "ph") % 5) - 2))

            # popular times matrix
            matrix = _gen_popular_times(slug, cat_slug, busy_d, peak_h)
            p.popular_times_json = json.dumps(matrix)
            p.busiest_day = DAY_KEYS[busy_d]
            p.busiest_hour = peak_h

            # hours_json per-day breakdown (parsed from canonical hours string)
            if not p.hours_json or p.hours_json == "{}":
                hd = _hours_dict_from_string(p.hours or "")
                if hd:
                    p.hours_json = json.dumps(hd)

            # service options
            if cat_slug == "restaurants":
                p.dine_in = _det_bool(slug, "din", 88)
                p.takeout = _det_bool(slug, "tko", 78)
                if not p.delivery_available:
                    p.delivery_available = _det_bool(slug, "dlv", 55)
                p.curbside_pickup = _det_bool(slug, "cbp", 38)
                p.contactless_pickup = _det_bool(slug, "cpu", 42)
                p.accepts_reservations = _det_bool(slug, "rsv", 56)
                p.serves_breakfast = "cafe" in name_lc or "bakery" in name_lc or "diner" in name_lc or _det_bool(slug, "brk", 32)
                p.serves_lunch = _det_bool(slug, "lun", 80)
                p.serves_dinner = _det_bool(slug, "din2", 88)
                p.serves_brunch = "cafe" in name_lc or "diner" in name_lc or _det_bool(slug, "brn", 28)
                p.serves_alcohol = ("bar" in name_lc or "lounge" in name_lc or "wine" in name_lc
                                    or _det_bool(slug, "alc", 48))
                p.serves_vegetarian = _det_bool(slug, "veg", 62)
            else:
                p.dine_in = False
                p.takeout = cat_slug in ("coffee-shops",) and _det_bool(slug, "tko", 70)
                p.contactless_pickup = cat_slug in ("shopping", "supermarkets", "pharmacies") and _det_bool(slug, "cpu", 55)
                p.curbside_pickup = cat_slug in ("supermarkets", "pharmacies", "shopping") and _det_bool(slug, "cbp", 40)
                p.accepts_reservations = cat_slug in ("hotels",) or _det_bool(slug, "rsv", 14)

            # accessibility — vary per category; civic / large venues
            # have more flags set, small services fewer
            high_access_cats = {"hospitals", "libraries", "museums", "campus-buildings",
                                "transit", "post-offices", "police-stations", "schools",
                                "hotels", "shopping", "supermarkets", "indoor-mall-shops",
                                "fire-stations"}
            low_access_cats = {"dog-parks", "public-restrooms", "playgrounds", "beaches"}
            if cat_slug in high_access_cats:
                base_prob = 78
            elif cat_slug in low_access_cats:
                base_prob = 48
            else:
                base_prob = 62
            p.wheelchair_accessible_entrance = _det_bool(slug, "wae", base_prob + 6)
            p.wheelchair_accessible_restroom = _det_bool(slug, "war", base_prob)
            p.wheelchair_accessible_parking = _det_bool(slug, "wap", base_prob - 4)
            p.wheelchair_accessible_seating = _det_bool(slug, "was", base_prob - 8)
            p.has_braille_menu = (cat_slug == "restaurants") and _det_bool(slug, "bra", 14)
            p.has_assistive_hearing = (cat_slug in ("museums", "entertainment", "campus-buildings", "hospitals")) and _det_bool(slug, "hrl", 38)
            p.has_service_animal_welcome = _det_bool(slug, "saw", 78)
            access_count = sum([
                bool(p.wheelchair_accessible_entrance),
                bool(p.wheelchair_accessible_restroom),
                bool(p.wheelchair_accessible_parking),
                bool(p.wheelchair_accessible_seating),
                bool(p.has_braille_menu),
                bool(p.has_assistive_hearing),
                bool(p.has_service_animal_welcome),
            ])
            p.accessibility_score = round(access_count * 100 / 7)

            # ratings distribution from rating + review_count
            rc = max(0, p.review_count or 0)
            r = p.rating or 4.0
            # Higher rating → more 5-star weight; deterministic spread
            if r >= 4.7:
                w = [62, 22, 9, 4, 3]
            elif r >= 4.4:
                w = [50, 28, 12, 6, 4]
            elif r >= 4.0:
                w = [38, 30, 17, 9, 6]
            elif r >= 3.5:
                w = [28, 26, 22, 14, 10]
            else:
                w = [18, 22, 22, 20, 18]
            # Sum normalise to rc
            tot = sum(w)
            dist = [(rc * x) // tot for x in w]
            # absorb remainder into top bucket
            dist[0] += rc - sum(dist)
            p.ratings_dist_json = json.dumps(dist)

            # menu for restaurant-ish places
            mtpl = _menu_template_for(slug, name_lc, cat_slug)
            if mtpl:
                # Deterministic price offset per place (±$2) using slug hash
                off = (_seed_int(slug, "menu") % 5) - 2
                menu = []
                for section_name, items in mtpl:
                    sec_items = []
                    for nm, dsc, price in items:
                        sec_items.append({
                            "name": nm, "desc": dsc,
                            "price": max(3, price + off),
                        })
                    menu.append({"section": section_name, "items": sec_items})
                p.menu_json = json.dumps(menu)

            batch += 1
            total += 1
            if batch >= 500:
                db.session.commit()
                batch = 0
    db.session.commit()
    print(f"backfill_place_extras: updated {total} place rows")


# ---------------------------------------------------------------------------
# Curated transit lines for major US cities.
# ---------------------------------------------------------------------------
_TRANSIT_LINES = [
    # (city_slug, slug, name, short_name, agency, mode, color, peak, off, hours, stops[], desc)
    ("new-york", "mta-1-train", "1 Train (Broadway-7th Avenue Local)", "1", "MTA New York City Subway", "subway", "#EE352E",
     "Every 4 min", "Every 8 min", "24 hours", [
         "South Ferry", "Rector St", "Cortlandt St", "Chambers St",
         "Franklin St", "Canal St", "Houston St", "Christopher St",
         "14th St", "18th St", "23rd St", "28th St", "34th St-Penn",
         "Times Sq-42nd St", "50th St", "59th St-Columbus Circle",
         "66th St-Lincoln Center", "72nd St", "79th St", "86th St",
         "96th St", "103rd St", "Cathedral Pkwy-110th St", "116th St",
         "125th St", "137th St-City College", "145th St", "157th St",
         "168th St-Washington Heights", "181st St", "191st St",
         "Dyckman St", "207th St", "215th St", "Marble Hill-225th St",
         "231st St", "238th St", "Van Cortlandt Park-242nd St",
     ],
     "Local Broadway-7th Avenue service from South Ferry to Van Cortlandt Park."),
    ("new-york", "mta-l-train", "L Train (14th St-Canarsie Local)", "L", "MTA New York City Subway", "subway", "#A7A9AC",
     "Every 4 min", "Every 10 min", "24 hours", [
         "8 Av", "6 Av", "Union Sq-14 St", "3 Av", "1 Av",
         "Bedford Av", "Lorimer St", "Graham Av", "Grand St",
         "Montrose Av", "Morgan Av", "Jefferson St", "DeKalb Av",
         "Myrtle-Wyckoff Avs", "Halsey St", "Wilson Av",
         "Bushwick Av-Aberdeen St", "Broadway Junction",
         "Atlantic Av", "Sutter Av", "Livonia Av", "New Lots Av",
         "East 105 St", "Canarsie-Rockaway Pkwy",
     ],
     "L train runs between 8 Av in Manhattan and Canarsie in Brooklyn."),
    ("new-york", "mta-m15-bus", "M15 Bus (1st & 2nd Av)", "M15", "MTA New York City Bus", "bus", "#D7B5D8",
     "Every 5 min", "Every 12 min", "24 hours", [
         "South Ferry", "Whitehall St", "Pearl St", "Allen St",
         "Houston St", "14 St", "23 St", "34 St-Midtown",
         "42 St", "57 St", "72 St", "86 St", "96 St",
         "116 St", "125 St-East Harlem",
     ], "M15 Select Bus Service along 1st and 2nd Avenues."),
    ("san-francisco", "muni-n-judah", "N Judah (Light Rail)", "N", "SFMTA Muni Metro", "light-rail", "#005DBD",
     "Every 8 min", "Every 12 min", "5:00 AM – 1:00 AM", [
         "Caltrain Depot", "Embarcadero", "Montgomery St",
         "Powell St", "Civic Center", "Van Ness", "Church St",
         "Duboce/Noe", "Carl & Cole", "9th & Irving", "19th Av",
         "Sunset Blvd", "Judah & 46th Av", "Ocean Beach",
     ], "N Judah runs from Ocean Beach to Caltrain through the Sunset and Downtown."),
    ("san-francisco", "bart-orange-line", "BART Richmond–Berryessa/N. San José", "Orange", "Bay Area Rapid Transit", "subway", "#FF9933",
     "Every 15 min", "Every 20 min", "5:00 AM – 12:00 AM", [
         "Richmond", "El Cerrito del Norte", "El Cerrito Plaza",
         "North Berkeley", "Downtown Berkeley", "Ashby",
         "MacArthur", "19th St Oakland", "12th St/Oakland City Center",
         "Lake Merritt", "Fruitvale", "Coliseum", "San Leandro",
         "Bay Fair", "Hayward", "South Hayward", "Union City",
         "Fremont", "Warm Springs/South Fremont", "Milpitas",
         "Berryessa/North San José",
     ], "Orange Line connects Richmond with Berryessa via Berkeley and Fremont."),
    ("boston", "mbta-red-line", "MBTA Red Line", "RL", "MBTA", "subway", "#DA291C",
     "Every 4 min", "Every 9 min", "5:00 AM – 1:00 AM", [
         "Alewife", "Davis", "Porter", "Harvard", "Central",
         "Kendall/MIT", "Charles/MGH", "Park Street",
         "Downtown Crossing", "South Station", "Broadway",
         "Andrew", "JFK/UMass", "Savin Hill", "Fields Corner",
         "Shawmut", "Ashmont",
     ], "Red Line runs from Alewife to Ashmont and Braintree branches."),
    ("boston", "mbta-green-b", "MBTA Green Line B (Boston College)", "B", "MBTA", "light-rail", "#00843D",
     "Every 7 min", "Every 12 min", "5:00 AM – 12:30 AM", [
         "Government Center", "Park Street", "Boylston",
         "Arlington", "Copley", "Hynes Convention Center",
         "Kenmore", "Blandford St", "BU East", "BU Central",
         "BU West", "St. Paul St", "Pleasant St", "Babcock St",
         "Packards Corner", "Harvard Ave", "Griggs St",
         "Allston St", "Warren St", "Washington St",
         "Sutherland Rd", "Chiswick Rd", "Chestnut Hill Av",
         "South St", "Boston College",
     ], "B branch of the Green Line, terminating at Boston College."),
    ("chicago", "cta-red-line", "CTA Red Line", "Red", "Chicago Transit Authority", "subway", "#C60C30",
     "Every 4 min", "Every 12 min", "24 hours", [
         "Howard", "Jarvis", "Morse", "Loyola", "Granville",
         "Thorndale", "Bryn Mawr", "Berwyn", "Argyle", "Lawrence",
         "Wilson", "Sheridan", "Addison", "Belmont", "Fullerton",
         "North/Clybourn", "Clark/Division", "Chicago", "Grand",
         "Lake", "Monroe", "Jackson", "Harrison", "Roosevelt",
         "Cermak-Chinatown", "Sox-35th", "47th", "Garfield",
         "63rd", "69th", "79th", "87th", "95th/Dan Ryan",
     ], "Red Line runs 24/7 between Howard and 95th/Dan Ryan."),
    ("chicago", "cta-blue-line", "CTA Blue Line (O'Hare-Forest Park)", "Blue", "Chicago Transit Authority", "subway", "#00A1DE",
     "Every 5 min", "Every 12 min", "24 hours", [
         "O'Hare", "Rosemont", "Cumberland", "Harlem (O'Hare)",
         "Jefferson Park", "Montrose", "Irving Park", "Addison",
         "Belmont", "Logan Square", "California", "Western",
         "Damen", "Division", "Chicago", "Grand", "Clark/Lake",
         "Washington", "Monroe", "Jackson", "LaSalle", "Clinton",
         "UIC-Halsted", "Racine", "Illinois Medical District",
         "Western (Forest Park)", "Kedzie-Homan", "Pulaski",
         "Cicero", "Austin", "Oak Park", "Harlem (Forest Park)",
         "Forest Park",
     ], "Blue Line connects O'Hare International Airport with Forest Park."),
    ("washington", "wmata-red", "WMATA Red Line", "RD", "WMATA Metrorail", "subway", "#BF0D3E",
     "Every 6 min", "Every 12 min", "5:00 AM – 12:00 AM", [
         "Shady Grove", "Rockville", "Twinbrook", "White Flint",
         "Grosvenor-Strathmore", "Medical Center", "Bethesda",
         "Friendship Heights", "Tenleytown-AU", "Van Ness-UDC",
         "Cleveland Park", "Woodley Park", "Dupont Circle",
         "Farragut North", "Metro Center", "Gallery Pl-Chinatown",
         "Judiciary Square", "Union Station", "NoMa-Gallaudet U",
         "Rhode Island Av", "Brookland-CUA", "Fort Totten",
         "Takoma", "Silver Spring", "Forest Glen", "Wheaton",
         "Glenmont",
     ], "Red Line is WMATA's busiest line, running through downtown DC."),
    ("seattle", "sound-transit-1-line", "Sound Transit 1 Line (Link Light Rail)", "1", "Sound Transit", "light-rail", "#0072CE",
     "Every 8 min", "Every 12 min", "5:00 AM – 1:00 AM", [
         "Lynnwood City Center", "Mountlake Terrace",
         "Shoreline North/185th", "Shoreline South/148th",
         "Northgate", "Roosevelt", "U District", "University of Washington",
         "Capitol Hill", "Westlake", "University Street", "Pioneer Square",
         "International District/Chinatown", "Stadium",
         "SODO", "Beacon Hill", "Mount Baker", "Columbia City",
         "Othello", "Rainier Beach", "Tukwila Int'l Blvd",
         "SeaTac/Airport", "Angle Lake",
     ], "Link Light Rail 1 Line connects Lynnwood with SeaTac/Airport via downtown."),
    ("los-angeles", "metro-d-line", "LA Metro D Line (Purple)", "D", "LA Metro", "subway", "#A05DA5",
     "Every 6 min", "Every 12 min", "4:00 AM – 12:30 AM", [
         "Union Station", "Civic Center/Grand Park", "Pershing Square",
         "7th St/Metro Center", "Westlake/MacArthur Park",
         "Wilshire/Vermont", "Wilshire/Normandie", "Wilshire/Western",
     ], "D Line (Purple) runs along Wilshire Blvd from Union Station."),
    ("los-angeles", "metro-b-line", "LA Metro B Line (Red)", "B", "LA Metro", "subway", "#E70033",
     "Every 6 min", "Every 12 min", "4:00 AM – 12:30 AM", [
         "Union Station", "Civic Center/Grand Park", "Pershing Square",
         "7th St/Metro Center", "Westlake/MacArthur Park",
         "Wilshire/Vermont", "Vermont/Beverly", "Vermont/Santa Monica",
         "Vermont/Sunset", "Hollywood/Western", "Hollywood/Vine",
         "Hollywood/Highland", "Universal City/Studio City",
         "North Hollywood",
     ], "B Line (Red) runs from Union Station to North Hollywood through Hollywood."),
    ("miami", "metrorail-orange", "Metrorail Orange Line", "O", "Miami-Dade Transit", "subway", "#F58025",
     "Every 7 min", "Every 15 min", "5:00 AM – 12:00 AM", [
         "Dadeland South", "Dadeland North", "South Miami",
         "University", "Douglas Road", "Coconut Grove",
         "Vizcaya", "Brickell", "Government Center", "Civic Center",
         "Santa Clara", "Allapattah", "Earlington Heights",
         "Hialeah Market", "MIA Airport",
     ], "Orange Line connects MIA Airport with Dadeland via Brickell."),
]


def seed_transit_lines(db, TransitLine, City):
    """Seed curated transit lines tied to real metro systems."""
    if TransitLine.query.count() > 0:
        return
    cities_by_slug = {c.slug: c for c in City.query.all()}
    added = 0
    for entry in _TRANSIT_LINES:
        (city_slug, slug, name, short_name, agency, mode, color,
         peak, off, hours, stops, desc) = entry
        city = cities_by_slug.get(city_slug)
        if TransitLine.query.filter_by(slug=slug).first():
            continue
        notes_seed = int.from_bytes(hashlib.md5(slug.encode()).digest()[:2], "big")
        notes = ("All stations wheelchair-accessible with elevators."
                 if notes_seed % 3 == 0 else
                 ("Most stations have elevators; check station details for accessibility info."
                  if notes_seed % 3 == 1 else
                  "Selected stations are accessible; transfer points include elevators."))
        db.session.add(TransitLine(
            slug=slug, name=name, short_name=short_name, agency=agency,
            mode=mode, color=color,
            city_id=city.id if city else None,
            frequency_peak=peak, frequency_off=off, hours=hours,
            stops_json=json.dumps(stops),
            description=desc, accessibility_notes=notes,
        ))
        added += 1
    db.session.commit()
    print(f"seed_transit_lines: added {added} transit lines")


# ===========================================================================
# R5: indoor sub-zones + outdoor sub-zones + parking lots + EV stations +
# fueling stations. Backfills new ambient columns (noise/crowd/mask) for
# every Place row. All seeded deterministically from md5(slug + salt) so
# byte-identical reset still holds.
# ===========================================================================
# Each template: (cat_slug, name_pattern, subtitle, desc, price, rlo, rhi,
#                 indoor_zone_type, floor_number)
# indoor_zone_type values: food-court / concourse / lounge / wing /
# platform / restroom / parking-deck / charger-bay / pump-island / "" (outdoor)
_R5_TEMPLATES = [
    # ---- Indoor sub-zones: airport concourse ----
    ("indoor-airport-shops", "{anchor} Airport — Gate A12 Lounge", "Departure lounge",
     "Quiet boarding lounge near Gate A12 with charging stations and a snack bar.",
     "$", 4.1, 4.7, "lounge", "2"),
    ("indoor-airport-shops", "{anchor} Airport — Concourse C Food Court", "Airport food court",
     "Open seating food court on Concourse C with 12 quick-service restaurants and a kids' play area.",
     "$$", 3.8, 4.4, "food-court", "2"),
    ("indoor-airport-shops", "{anchor} Airport — Terminal 1 Family Restroom", "Family restroom",
     "Wheelchair-accessible family restroom in Terminal 1 with adult-size changing table and nursing alcove.",
     "Free", 4.0, 4.7, "restroom", "1"),
    ("indoor-airport-shops", "{anchor} Airport — Quiet Meditation Room", "Meditation room",
     "Multi-faith quiet meditation room in the post-security mezzanine; open 24/7, masks recommended.",
     "Free", 4.5, 4.9, "lounge", "M"),
    ("indoor-airport-shops", "{anchor} Airport — Gate B7 Charging Cluster", "Power station",
     "Cluster of 24 outlets and 8 USB-C charging stations between Gates B5 and B9.",
     "Free", 4.2, 4.7, "concourse", "2"),

    # ---- Indoor sub-zones: shopping mall ----
    ("indoor-mall-shops", "{anchor} Mall — Level 1 Food Court", "Mall food court",
     "Ground-floor food court with 14 cuisines, accessible seating, and a kids' play table.",
     "$$", 3.9, 4.5, "food-court", "1"),
    ("indoor-mall-shops", "{anchor} Mall — Level 2 Fashion Wing", "Fashion wing",
     "Upper-level fashion wing with anchor stores, denim row, and an accessory marketplace.",
     "$$$", 4.1, 4.6, "wing", "2"),
    ("indoor-mall-shops", "{anchor} Mall — Lower Level Family Restroom", "Family restroom",
     "Multi-stall family restroom with stroller parking, baby-changing tables, and nursing pods.",
     "Free", 4.1, 4.7, "restroom", "B1"),
    ("indoor-mall-shops", "{anchor} Mall — Rooftop Garden Court", "Rooftop garden",
     "Rooftop garden court with cafe seating, herb planters, and a small concert stage.",
     "$$", 4.4, 4.9, "lounge", "R"),

    # ---- Indoor sub-zones: hospital ----
    ("hospitals", "{anchor} Medical Center — Pediatric Wing", "Pediatric wing",
     "Pediatric wing with child-life rooms, sensory-friendly hallway, and family overnight suites.",
     "$$$", 4.4, 4.9, "wing", "3"),
    ("hospitals", "{anchor} Medical Center — Cardiology Wing", "Cardiology wing",
     "Cardiology wing with cath labs, echocardiography suite, and cardiac-rehab gym.",
     "$$$$", 4.3, 4.8, "wing", "4"),
    ("hospitals", "{anchor} Medical Center — Maternity Wing", "Maternity wing",
     "Maternity wing with private LDR rooms, NICU, and a quiet lactation lounge.",
     "$$$$", 4.5, 4.9, "wing", "5"),
    ("hospitals", "{anchor} Medical Center — ER Triage Lobby", "Emergency lobby",
     "Emergency-room triage lobby with 24/7 walk-in registration and isolation pods.",
     "$$$$", 3.8, 4.4, "lounge", "1"),

    # ---- Indoor sub-zones: museum ----
    ("museums", "{anchor} Museum — North Wing (Impressionists)", "Museum wing",
     "North wing devoted to Impressionist and Post-Impressionist paintings; quiet hours 10am-noon.",
     "$$", 4.5, 4.9, "wing", "2"),
    ("museums", "{anchor} Museum — South Wing (Modern Art)", "Museum wing",
     "South wing showcasing modern and contemporary art with rotating installations.",
     "$$", 4.4, 4.9, "wing", "2"),
    ("museums", "{anchor} Museum — Family Education Center", "Family room",
     "Hands-on family education center with maker stations, story hours, and stroller-friendly aisles.",
     "$", 4.6, 4.9, "lounge", "1"),

    # ---- Indoor sub-zones: transit station platforms ----
    ("transit", "{anchor} Central Station — Platform 1 (Inbound)", "Station platform",
     "Inbound platform with wheelchair ramp, tactile guide strip, and digital arrival board.",
     "Free", 3.9, 4.5, "platform", "1"),
    ("transit", "{anchor} Central Station — Platform 4 (Express)", "Station platform",
     "Express train platform served by inter-city services; accessible from the north mezzanine.",
     "Free", 3.8, 4.4, "platform", "1"),
    ("transit", "{anchor} Central Station — Bike & Stroller Storage", "Storage area",
     "Secure bike and stroller storage on the lower concourse, accessible with transit pass.",
     "Free", 4.0, 4.6, "concourse", "B1"),

    # ---- Indoor: stadium / arena ----
    ("entertainment", "{anchor} Arena — Section 117 Concourse", "Arena concourse",
     "Lower-bowl Section 117 concourse with concession row, accessible seating, and mobile-order pickup.",
     "$$", 4.0, 4.6, "concourse", "1"),
    ("entertainment", "{anchor} Arena — Sensory Room", "Sensory room",
     "Calming sensory room for guests with sensory sensitivities; weighted blankets and noise-canceling headphones.",
     "Free", 4.7, 4.9, "lounge", "2"),

    # ---- Indoor: university campus building ----
    ("campus-buildings", "{anchor} University — Engineering Atrium", "Campus atrium",
     "Engineering atrium with collaborative seating, soldering benches, and a 24/7 maker space.",
     "Free", 4.4, 4.8, "lounge", "1"),
    ("campus-buildings", "{anchor} University — Library Quiet Floor 4", "Quiet floor",
     "Silent fourth-floor reading area, no talking, no calls; individual carrels available.",
     "Free", 4.6, 4.9, "wing", "4"),

    # ---- Indoor: government building ----
    ("services", "{anchor} City Hall — Permit Office 2F", "Permit office",
     "Second-floor permit office for building, business, and special-event permits.",
     "$", 3.6, 4.2, "wing", "2"),
    ("services", "{anchor} City Hall — Public Notary Counter", "Notary counter",
     "Walk-in notary counter for residents; bring ID and the document to be notarized.",
     "$", 4.0, 4.6, "wing", "1"),

    # ---- Outdoor sub-zones: scenic viewpoints, intersections ----
    ("attractions", "{anchor} Scenic Overlook", "Scenic viewpoint",
     "Hillside scenic overlook with city skyline panorama; busiest at sunset.",
     "Free", 4.6, 4.9, "", ""),
    ("attractions", "{anchor} Riverside Promenade Mile 3", "Outdoor promenade",
     "Mile 3 marker on the riverside promenade with a water fountain and benches.",
     "Free", 4.4, 4.8, "", ""),
    ("attractions", "{anchor} Cherry Blossom Walk", "Outdoor walk",
     "Spring cherry-blossom walking path; petals peak in early April.",
     "Free", 4.7, 4.9, "", ""),
    ("transit", "{anchor} Main & 5th Bus Stop", "Bus stop",
     "Main Street & 5th Avenue bus stop served by routes 12, 14, and 22.",
     "Free", 3.6, 4.2, "", ""),
    ("transit", "{anchor} Civic Center Plaza Bike Hub", "Bike share station",
     "Civic Center Plaza bike-share station with 28 docks and a covered repair stand.",
     "$", 4.1, 4.7, "", ""),

    # ---- Parking lots / decks (real category 'parking') ----
    ("parking", "{anchor} City Center Multi-Level Garage", "Parking garage",
     "Multi-level downtown parking garage with EV stalls on level 2 and bicycle racks at the entrance.",
     "$$", 3.9, 4.5, "parking-deck", "1"),
    ("parking", "{anchor} Convention Center Lot A", "Surface lot",
     "Convention Center Lot A surface parking; event-day pricing in effect.",
     "$$", 3.8, 4.4, "", ""),
    ("parking", "{anchor} Stadium West Lot", "Stadium lot",
     "Stadium West Lot reserved for season passholders on game days; tailgating allowed in marked rows.",
     "$$$", 3.7, 4.3, "", ""),
    ("parking", "{anchor} Hospital Visitor Garage", "Hospital parking",
     "Hospital visitor parking garage; first hour free, then $3/hour.",
     "$$", 3.7, 4.3, "parking-deck", "1"),
    ("parking", "{anchor} Mall Customer Parking", "Mall parking",
     "Customer parking deck with 2200 spaces, EV stalls on level 3, and motorcycle row.",
     "Free", 4.2, 4.7, "parking-deck", "1"),
    ("parking", "{anchor} Beach Day-Use Lot", "Beach parking",
     "Day-use beach parking with restrooms and outdoor showers; $10 flat fee.",
     "$$", 4.0, 4.6, "", ""),

    # ---- EV charging stations (mix of connectors / speeds) ----
    ("ev-charging", "Tesla Supercharger — {anchor} V4", "Tesla Supercharger V4",
     "Tesla Supercharger V4 with 24 stalls; up to 250 kW; restrooms and dining within 200 m.",
     "$$", 4.3, 4.8, "charger-bay", ""),
    ("ev-charging", "Electrify America — {anchor} Hyperfast", "EV fast charging",
     "Electrify America hyperfast plaza with CCS connectors up to 350 kW; covered canopy.",
     "$$", 4.0, 4.6, "charger-bay", ""),
    ("ev-charging", "ChargePoint Express 250 — {anchor}", "ChargePoint Express",
     "ChargePoint Express 250 plaza with CCS and CHAdeMO connectors; 24/7 access.",
     "$", 4.1, 4.7, "charger-bay", ""),
    ("ev-charging", "EVgo Fast Charging — {anchor} Plaza", "EV fast charging",
     "EVgo plaza with CCS and CHAdeMO connectors up to 350 kW; PlugShare check-in.",
     "$$", 4.0, 4.6, "charger-bay", ""),
    ("ev-charging", "Blink Level 2 — {anchor} Center", "Level 2 charger",
     "Blink Level 2 charger row at the parking center; ideal for 2-hour shopping or dining stops.",
     "$", 3.8, 4.4, "charger-bay", ""),
    ("ev-charging", "Rivian Adventure Network — {anchor}", "Rivian charger",
     "Rivian Adventure Network DC fast chargers with CCS connectors for all EVs.",
     "$$", 4.4, 4.9, "charger-bay", ""),

    # ---- Fueling stations (gas + EV combo) ----
    ("gas-stations", "{anchor} Shell Recharge — Gas + EV", "Combined fuel",
     "Shell Recharge station with 6 gas pumps and 4 DC fast EV chargers; 24-hour convenience store.",
     "$$", 4.1, 4.7, "pump-island", ""),
    ("gas-stations", "{anchor} BP Pulse Station", "BP Pulse",
     "BP Pulse station offering regular gas plus 150 kW EV fast-charge stalls under a covered canopy.",
     "$$", 4.0, 4.6, "pump-island", ""),
    ("gas-stations", "{anchor} Sunoco Express", "Gas station",
     "Sunoco Express full-service gas station with truck-friendly diesel lane and lottery kiosk.",
     "$", 3.7, 4.4, "pump-island", ""),
    ("gas-stations", "{anchor} 7-Eleven Fuel Mart", "Fuel + convenience",
     "7-Eleven fuel mart with 24-hour Slurpee bar and grab-and-go food case.",
     "$", 3.8, 4.5, "pump-island", ""),
    ("gas-stations", "{anchor} Wawa Travel Center", "Fuel + travel center",
     "Wawa travel center with made-to-order hoagies, fresh coffee, and 24-hour fuel.",
     "$$", 4.5, 4.9, "pump-island", ""),
    ("gas-stations", "{anchor} Sheetz Mega Plaza", "Travel plaza",
     "Sheetz mega plaza with MTO food, gas, EV chargers, and a drive-thru pickup window.",
     "$$", 4.4, 4.9, "pump-island", ""),

    # ---- Indoor: hotels (skybridge / pool / spa zones) ----
    ("hotels", "{anchor} Grand Hotel — Sky Lounge Bar", "Sky lounge",
     "Top-floor sky lounge bar with floor-to-ceiling skyline views; cocktail-attire dress code.",
     "$$$$", 4.5, 4.9, "lounge", "R"),
    ("hotels", "{anchor} Grand Hotel — Pool Deck Cabana", "Pool deck",
     "Heated pool deck with private cabanas, towel service, and an all-day bar.",
     "$$$", 4.3, 4.8, "lounge", "3"),
    ("hotels", "{anchor} Grand Hotel — Quiet Spa Floor", "Spa floor",
     "Quiet spa floor with sauna, steam room, and an adults-only relaxation room; masks recommended in steam areas.",
     "$$$$", 4.6, 4.9, "wing", "4"),

    # ---- Extra parking sub-zones for higher density ----
    ("parking", "{anchor} Library Visitor Lot", "Library parking",
     "Public library visitor lot with two-hour limit; accessible spaces near the main entrance.",
     "Free", 3.8, 4.4, "", ""),
    ("parking", "{anchor} University Garage P3", "Campus parking garage",
     "University parking garage P3; permit required Mon-Fri 7am-5pm, free evenings and weekends.",
     "$$", 3.7, 4.3, "parking-deck", "1"),
    ("parking", "{anchor} Trailhead Day Lot", "Trailhead parking",
     "Trailhead day-use lot with pit toilets and a paid kiosk; arrive early on weekends.",
     "$", 4.2, 4.7, "", ""),
    ("parking", "{anchor} Park & Ride East Lot", "Park and ride",
     "Park-and-ride east lot served by 4 commuter bus lines; first 200 stalls have EV chargers.",
     "Free", 4.0, 4.5, "", ""),

    # ---- Extra EV connectors ----
    ("ev-charging", "Ionna Reliable Charge — {anchor}", "EV fast charging",
     "Ionna joint-venture charging hub with CCS connectors up to 400 kW; covered canopy and pull-through stalls.",
     "$$", 4.3, 4.8, "charger-bay", ""),
    ("ev-charging", "Mercedes-Benz HPC — {anchor}", "EV fast charging",
     "Mercedes-Benz high-power charging hub with 320 kW CCS stalls and a premium lounge.",
     "$$$", 4.4, 4.9, "charger-bay", ""),
    ("ev-charging", "EV Connect Level 2 — {anchor} City Hall", "Level 2 charger",
     "EV Connect Level 2 chargers at City Hall employee parking; public access weekends.",
     "$", 3.9, 4.5, "charger-bay", ""),
    ("ev-charging", "FLO Network — {anchor} Civic Plaza", "Level 2 charger",
     "FLO Network curbside Level 2 chargers along Civic Plaza; 4-hour stay limit.",
     "$", 4.0, 4.6, "charger-bay", ""),
    ("ev-charging", "Volta Free Level 2 — {anchor} Mall", "Level 2 charger",
     "Volta free Level 2 charger row at the mall parking deck; ad-supported, no fee.",
     "Free", 4.2, 4.7, "charger-bay", ""),

    # ---- Extra fuel / travel center ----
    ("gas-stations", "{anchor} Speedway Travel Center", "Travel center",
     "Speedway travel center with diesel lane, RV-friendly bays, and a 24-hour deli.",
     "$$", 4.0, 4.6, "pump-island", ""),
    ("gas-stations", "{anchor} Pilot Flying J", "Truck stop",
     "Pilot Flying J truck stop with showers, laundry, and the Cinnabon counter.",
     "$$", 3.9, 4.6, "pump-island", ""),
    ("gas-stations", "{anchor} Murphy USA Station", "Discount fuel",
     "Murphy USA discount fuel station adjacent to a Walmart Supercenter; cash-discount pricing.",
     "$", 3.7, 4.3, "pump-island", ""),
    ("gas-stations", "{anchor} ARCO ampm", "Gas + convenience",
     "ARCO ampm with cash-discount pricing and a famous taquito-and-pizza counter.",
     "$", 3.7, 4.3, "pump-island", ""),

    # ---- Extra indoor: more food courts / restrooms / lounges / wings ----
    ("indoor-mall-shops", "{anchor} Mall — Cinema Wing", "Cinema wing",
     "Cinema wing with 12 screens, a Dolby Atmos auditorium, and recliner seating.",
     "$$$", 4.2, 4.7, "wing", "3"),
    ("indoor-mall-shops", "{anchor} Mall — Indoor Playground", "Indoor playground",
     "Free indoor playground with soft-play structures and stroller parking; closes at 8 PM.",
     "Free", 4.5, 4.9, "lounge", "1"),
    ("indoor-airport-shops", "{anchor} Airport — International Arrivals Concourse", "Arrivals concourse",
     "International arrivals concourse with currency exchange, SIM kiosks, and ground-transport info.",
     "$$", 3.7, 4.3, "concourse", "1"),
    ("indoor-airport-shops", "{anchor} Airport — Pet Relief Area Terminal 2", "Pet relief area",
     "Indoor pet relief area in Terminal 2 with a fenced grassy patch and water bowls.",
     "Free", 4.2, 4.7, "lounge", "1"),
    ("hospitals", "{anchor} Medical Center — Imaging Wing", "Imaging wing",
     "Diagnostic imaging wing with MRI, CT, ultrasound, and a quiet waiting alcove.",
     "$$$$", 4.2, 4.7, "wing", "2"),
    ("museums", "{anchor} Museum — Sculpture Garden", "Sculpture garden",
     "Outdoor sculpture garden adjacent to the museum's south wing; free with admission.",
     "$", 4.6, 4.9, "wing", ""),
    ("museums", "{anchor} Museum — Quiet Reading Room", "Quiet reading room",
     "Member-only quiet reading room with art books and a panoramic view of the central court.",
     "$$", 4.7, 4.9, "lounge", "3"),
    ("entertainment", "{anchor} Arena — Family Restroom Section 218", "Family restroom",
     "Family restroom with adult-size changing table and nursing pod, Section 218 upper bowl.",
     "Free", 4.0, 4.6, "restroom", "2"),

    # ---- Extra outdoor sub-zones ----
    ("attractions", "{anchor} Sunset Cliff Lookout", "Scenic viewpoint",
     "Sunset cliff lookout with safety railing; the only legal drone-launch zone in the park.",
     "Free", 4.8, 4.9, "", ""),
    ("attractions", "{anchor} Heritage Walking Tour Start", "Walking tour",
     "Self-guided heritage walking-tour starting point with QR-code stops.",
     "Free", 4.5, 4.9, "", ""),
    ("transit", "{anchor} Bay Ferry Dock", "Ferry dock",
     "Bay ferry dock with covered waiting area, ticket vending, and bike racks.",
     "$", 4.2, 4.7, "", ""),
    ("transit", "{anchor} Light Rail Park Stop", "Light rail stop",
     "Park-side light rail stop with sheltered seating and a tactile guide strip.",
     "Free", 4.1, 4.7, "", ""),
]


def _seed_int_hex(slug, salt):
    return int.from_bytes(
        hashlib.md5((salt + ":" + slug).encode()).digest()[:4], "big")


def _r5_amenities(cat_slug, indoor_zone, ev_connector, ev_kw):
    """Return amenity list tailored to the R5 sub-zone type."""
    base = []
    if cat_slug == "ev-charging":
        if ev_connector:
            base.append(f"{ev_connector} connector")
        if ev_kw:
            base.append(f"{ev_kw} kW peak")
        base += ["24/7 access", "Covered canopy", "PlugShare check-in"]
    elif cat_slug == "parking":
        base += ["EV stalls", "Bicycle racks", "Motorcycle row", "Wheelchair-accessible parking"]
    elif cat_slug == "gas-stations":
        base += ["Convenience store", "Air pump", "Restroom",
                 "Diesel lane" if "diesel" in indoor_zone else "Regular fuel"]
    elif indoor_zone == "food-court":
        base += ["Free Wi-Fi", "Family seating", "Wheelchair-accessible seating",
                 "Stroller-friendly aisles", "Mobile order pickup"]
    elif indoor_zone == "lounge":
        base += ["Quiet seating", "Charging outlets", "Wheelchair-accessible entrance"]
    elif indoor_zone == "wing":
        base += ["Elevator access", "Wheelchair-accessible restroom", "Information desk"]
    elif indoor_zone == "restroom":
        base += ["Baby-changing table", "Family stall", "Wheelchair-accessible entrance"]
    elif indoor_zone == "platform":
        base += ["Tactile guide strip", "Audio announcements", "Digital arrival board"]
    elif indoor_zone == "concourse":
        base += ["Concession row", "Charging outlets", "Wheelchair-accessible seating"]
    elif indoor_zone == "parking-deck":
        base += ["EV stalls", "Wheelchair-accessible parking", "Lighted stairwell"]
    elif indoor_zone == "charger-bay":
        base += ["Covered canopy", "Restroom within 200 m", "Pull-through stalls"]
    elif indoor_zone == "pump-island":
        base += ["EV fast charge", "Convenience store", "Restroom"]
    else:
        base += ["Outdoor seating", "Bicycle racks"]
    return base


def expand_places_r5(db, Place, Category, City):
    """R5 expansion: indoor sub-zones, outdoor sub-zones, parking lots,
    EV chargers, fueling stations. Adds ~80 templates per city for ~65k rows.

    Idempotent: gated on Place count >= 195000.
    """
    if Place.query.count() >= 195000:
        return

    random.seed(20260520)  # not actually used; all values derived from md5(slug)
    cat_by_slug = {c.slug: c for c in Category.query.all()}
    cities = City.query.order_by(City.id).all()
    if not cities:
        return

    donor_pool = []
    for p in Place.query.filter(Place.hero_image.like("/static/images/places/%")).order_by(Place.id).limit(80).all():
        try:
            photos = json.loads(p.photos_json or "[]")
        except Exception:
            photos = []
        if p.hero_image:
            donor_pool.append((p.hero_image, photos or [p.hero_image]))
    if not donor_pool:
        donor_pool = [("/static/images/heroes/eiffel-tower.jpg",
                       ["/static/images/heroes/eiffel-tower.jpg"])]

    # EV connector / kW rotation per template index — deterministic.
    _EV_VARIANTS = [
        ("Tesla", 250), ("CCS", 350), ("CCS+CHAdeMO", 350),
        ("CCS+CHAdeMO", 350), ("J1772", 11), ("CCS", 200),
    ]

    added = 0
    for city in cities:
        anchor = city.display_name.split(",")[0].split(" ")[0]
        # Deterministic per-city shuffle of templates so different cities get
        # rotation but the city always produces the same order on rebuild.
        templates = list(enumerate(_R5_TEMPLATES))
        slug_seed = int.from_bytes(
            hashlib.md5(("r5-" + city.slug).encode()).digest()[:4], "big")
        # In-place deterministic shuffle (Fisher-Yates with md5-derived swaps).
        for i in range(len(templates) - 1, 0, -1):
            j = int.from_bytes(
                hashlib.md5(f"r5sh:{city.slug}:{i}".encode()).digest()[:4],
                "big") % (i + 1)
            templates[i], templates[j] = templates[j], templates[i]

        for idx, tpl in templates:
            (cat_slug, pattern, subtitle, desc, price, rlo, rhi,
             indoor_zone, floor_num) = tpl
            cat = cat_by_slug.get(cat_slug)
            if not cat:
                continue
            slug = f"r5-{city.slug}-{cat_slug}-{idx:02d}"
            if Place.query.filter_by(slug=slug).first():
                continue

            name = pattern.format(anchor=anchor)
            local_seed = _seed_int_hex(slug, "r5loc")
            hero, gallery = donor_pool[local_seed % len(donor_pool)]
            lat = city.lat + ((local_seed % 800) - 400) / 10000.0
            lng = city.lng + (((local_seed // 800) % 1000) - 500) / 10000.0
            rating = round(rlo + (local_seed % 100) / 100.0 * (rhi - rlo), 1)
            review_count = 12 + (local_seed % 3600)

            # EV-specific: connector + kW from variant rotation
            ev_connector = ""
            ev_kw = 0
            if cat_slug == "ev-charging":
                v_idx = (_seed_int_hex(slug, "evv")) % len(_EV_VARIANTS)
                ev_connector, ev_kw = _EV_VARIANTS[v_idx]

            # Multi-floor json for indoor venues (mall / airport / hospital /
            # museum / hotel) — gives the indoor-floor-selector something to
            # render even on a single-row preview.
            floors = []
            if indoor_zone in ("wing", "concourse", "lounge", "food-court",
                                "restroom", "parking-deck") and cat_slug in (
                    "indoor-mall-shops", "indoor-airport-shops",
                    "hospitals", "museums", "hotels", "entertainment"):
                floors = _r5_floor_map(cat_slug)

            hours_pick = (local_seed >> 4) % 6
            hours_options = [
                "Mon-Sun: 9:00 AM - 9:00 PM",
                "Mon-Sat: 10:00 AM - 8:00 PM, Sun 11:00 AM - 6:00 PM",
                "Tue-Sun: 11:00 AM - 10:00 PM, Closed Mon",
                "Open 24 hours",
                "Mon-Fri: 7:00 AM - 7:00 PM, Weekends 8:00 AM - 5:00 PM",
                "Mon-Sun: 6:00 AM - 10:00 PM",
            ]
            tags = [cat_slug, anchor.lower(), city.country.lower()]
            if indoor_zone:
                tags.append(indoor_zone)
            amenities = _r5_amenities(cat_slug, indoor_zone, ev_connector, ev_kw)

            db.session.add(Place(
                slug=slug, name=name, category_id=cat.id, city_id=city.id,
                subtitle=subtitle,
                description=desc,
                address=f"{20 + (local_seed % 980)} {['Main','Oak','Park','Elm','Pine','Cedar','Birch','Maple'][local_seed % 8]} St, {city.display_name}",
                phone=f"+{1 + (local_seed % 9)} {200 + (local_seed % 800)} {1000 + (local_seed % 9000)}",
                hours=hours_options[hours_pick],
                website=google_maps_search_url(name, city.display_name),
                rating=rating,
                review_count=review_count,
                price_level=price,
                hero_image=hero,
                photos_json=json.dumps(gallery[:5]),
                lat=lat, lng=lng,
                tags_json=json.dumps(tags),
                amenities_json=json.dumps(amenities),
                subcategory=subtitle,
                is_24h=(hours_pick == 3) or cat_slug in ("ev-charging", "gas-stations"),
                is_popular=(rating >= 4.6 and (local_seed % 4) == 0),
                has_parking_lot=(cat_slug in (
                    "parking", "gas-stations", "indoor-mall-shops",
                    "hospitals") or indoor_zone == "parking-deck"),
                ev_charging=(cat_slug == "ev-charging" or
                              cat_slug == "gas-stations" and "Recharge" in name),
                bicycle_parking=(cat_slug in ("parking",) or "bike" in name.lower()
                                  or (local_seed % 3) == 0),
                motorcycle_parking=(cat_slug == "parking" and (local_seed % 3) == 0),
                indoor_zone_type=indoor_zone,
                floor_number=floor_num,
                floors_json=json.dumps(floors),
                parking_lot_capacity=(80 + (local_seed % 2400)) if cat_slug == "parking" else 0,
                ev_connector_type=ev_connector,
                ev_charger_kw=ev_kw,
            ))
            added += 1
            if added % 1000 == 0:
                db.session.commit()
    db.session.commit()
    print(f"expand_places_r5: added {added} R5 sub-zone places (total {Place.query.count()})")


def _r5_floor_map(cat_slug):
    """Canonical multi-floor map shown in the indoor-floor selector."""
    if cat_slug == "indoor-mall-shops":
        return [
            {"code": "B1", "label": "Lower Level", "summary": "Restrooms, family room, supermarket entrance"},
            {"code": "1",  "label": "Level 1",     "summary": "Food court, anchor stores, customer service"},
            {"code": "2",  "label": "Level 2",     "summary": "Fashion wing, electronics, beauty"},
            {"code": "3",  "label": "Level 3",     "summary": "Cinema, restaurants, kids' zone"},
            {"code": "R",  "label": "Roof",        "summary": "Rooftop garden court"},
        ]
    if cat_slug == "indoor-airport-shops":
        return [
            {"code": "1",  "label": "Arrivals (Level 1)", "summary": "Baggage claim, ground transport"},
            {"code": "2",  "label": "Departures (Level 2)", "summary": "Check-in, security, gates A-D"},
            {"code": "M",  "label": "Mezzanine", "summary": "Quiet meditation room, lounges"},
        ]
    if cat_slug == "hospitals":
        return [
            {"code": "1",  "label": "Lobby / ER",          "summary": "Emergency triage, registration, gift shop"},
            {"code": "2",  "label": "Surgical Suites",     "summary": "OR, recovery, ambulatory surgery"},
            {"code": "3",  "label": "Pediatric Wing",      "summary": "Child-life rooms, family overnight suites"},
            {"code": "4",  "label": "Cardiology Wing",     "summary": "Cath labs, echo suite, cardiac rehab"},
            {"code": "5",  "label": "Maternity Wing",      "summary": "LDR rooms, NICU, lactation lounge"},
        ]
    if cat_slug == "museums":
        return [
            {"code": "1",  "label": "Floor 1",  "summary": "Entry hall, family education center, gift shop"},
            {"code": "2",  "label": "Floor 2",  "summary": "North wing (Impressionists), south wing (Modern Art)"},
            {"code": "3",  "label": "Floor 3",  "summary": "Special exhibitions, archive"},
        ]
    if cat_slug == "hotels":
        return [
            {"code": "1",  "label": "Lobby",         "summary": "Check-in, concierge, lobby bar"},
            {"code": "3",  "label": "Pool Deck",     "summary": "Heated pool, cabanas, all-day bar"},
            {"code": "4",  "label": "Spa Floor",     "summary": "Sauna, steam, relaxation room"},
            {"code": "R",  "label": "Sky Lounge",    "summary": "Top-floor cocktail bar with skyline views"},
        ]
    if cat_slug == "entertainment":
        return [
            {"code": "1",  "label": "Lower Bowl Concourse", "summary": "Sections 100-120, mobile-order pickup"},
            {"code": "2",  "label": "Upper Bowl + Sensory", "summary": "Sections 200-220, sensory room"},
        ]
    return []


def backfill_place_extras_r5(db, Place, Category):
    """Deterministic backfill of R5 ambient columns on every Place row.

    Skips rows that already have noise_level set so warm restarts are no-ops.
    All values derive from md5(slug + salt) so byte-identical reset holds.
    """
    total = Place.query.count()
    if total == 0:
        return
    filled = Place.query.filter(Place.noise_level != "").count()
    if filled >= total * 0.9:
        return

    cat_by_id = {c.id: c.slug for c in Category.query.all()}
    # noise / crowd defaults per category
    _NOISE_BY_CAT = {
        "restaurants":          ["moderate", "lively", "lively", "loud", "moderate"],
        "entertainment":        ["lively", "loud", "loud", "lively", "moderate"],
        "coffee-shops":         ["moderate", "quiet", "moderate", "moderate", "lively"],
        "hotels":               ["quiet", "quiet", "moderate", "moderate"],
        "libraries":            ["quiet", "quiet", "quiet"],
        "museums":              ["quiet", "moderate", "quiet", "moderate"],
        "parks":                ["quiet", "moderate", "lively"],
        "shopping":             ["moderate", "lively", "moderate"],
        "indoor-mall-shops":    ["lively", "moderate", "lively", "loud"],
        "indoor-airport-shops": ["lively", "loud", "moderate", "lively"],
        "transit":              ["moderate", "lively", "loud", "moderate"],
        "bus-stops":            ["lively", "loud", "moderate"],
        "hospitals":            ["quiet", "moderate", "quiet"],
        "schools":              ["lively", "moderate", "loud"],
        "campus-buildings":     ["moderate", "lively", "quiet"],
        "gas-stations":         ["moderate", "lively", "moderate"],
        "parking":              ["quiet", "moderate", "quiet"],
        "ev-charging":          ["quiet", "moderate", "quiet"],
        "fitness":              ["lively", "loud", "moderate"],
        "religious":            ["quiet", "moderate"],
        "playgrounds":          ["lively", "loud"],
        "beaches":              ["moderate", "lively", "moderate"],
        "dog-parks":            ["lively", "moderate"],
        "supermarkets":         ["moderate", "lively"],
        "pharmacies":           ["moderate", "quiet"],
        "atms":                 ["moderate", "quiet"],
        "post-offices":         ["moderate", "quiet"],
        "police-stations":      ["quiet", "moderate"],
        "fire-stations":        ["quiet", "moderate"],
        "car-rental":           ["moderate", "lively"],
        "veterinarians":        ["moderate", "lively"],
        "dentists":             ["quiet", "moderate"],
        "public-restrooms":     ["moderate", "quiet"],
        "attractions":          ["moderate", "lively", "loud"],
        "health-beauty":        ["quiet", "moderate"],
        "services":             ["moderate", "quiet"],
    }
    _CROWD_BY_CAT = {
        "restaurants":          ["moderate", "high", "moderate", "low", "very-high"],
        "entertainment":        ["high", "very-high", "moderate", "high"],
        "coffee-shops":         ["moderate", "high", "low", "moderate"],
        "hotels":               ["moderate", "low", "moderate"],
        "libraries":            ["low", "moderate", "low"],
        "museums":              ["moderate", "high", "low"],
        "parks":                ["low", "moderate", "high"],
        "shopping":             ["moderate", "high", "very-high"],
        "indoor-mall-shops":    ["high", "very-high", "moderate"],
        "indoor-airport-shops": ["very-high", "high", "moderate"],
        "transit":              ["high", "very-high", "moderate"],
        "bus-stops":            ["high", "very-high"],
        "hospitals":            ["high", "very-high", "moderate"],
        "schools":              ["high", "very-high", "moderate"],
        "campus-buildings":     ["moderate", "high", "low"],
        "gas-stations":         ["low", "moderate", "low"],
        "parking":              ["moderate", "high", "very-high"],
        "ev-charging":          ["low", "moderate", "high"],
        "fitness":              ["moderate", "high"],
        "religious":            ["moderate", "low"],
        "playgrounds":          ["high", "moderate"],
        "beaches":              ["high", "very-high", "moderate"],
        "dog-parks":            ["moderate", "high"],
        "supermarkets":         ["moderate", "high", "very-high"],
        "pharmacies":           ["moderate", "low"],
        "atms":                 ["low", "moderate"],
        "post-offices":         ["moderate", "high"],
        "police-stations":      ["low", "moderate"],
        "fire-stations":        ["low", "moderate"],
        "car-rental":           ["moderate", "high"],
        "veterinarians":        ["moderate", "low"],
        "dentists":             ["low", "moderate"],
        "public-restrooms":     ["moderate", "low"],
        "attractions":          ["high", "very-high"],
        "health-beauty":        ["low", "moderate"],
        "services":             ["low", "moderate"],
    }
    _MASK_PROB_BY_CAT = {
        "hospitals": 95, "pharmacies": 35, "dentists": 80,
        "veterinarians": 25, "indoor-mall-shops": 8, "indoor-airport-shops": 12,
        "transit": 15, "bus-stops": 12, "museums": 10, "schools": 15,
        "religious": 18, "campus-buildings": 12,
    }

    BATCH = 1500
    offset = 0
    written = 0
    while True:
        rows = (Place.query
                .order_by(Place.id)
                .offset(offset).limit(BATCH).all())
        if not rows:
            break
        offset += BATCH
        for p in rows:
            if p.noise_level:
                continue  # already filled
            slug = p.slug or ""
            cat_slug = cat_by_id.get(p.category_id, "")
            noise_options = _NOISE_BY_CAT.get(cat_slug, ["moderate", "quiet", "lively"])
            crowd_options = _CROWD_BY_CAT.get(cat_slug, ["moderate", "low", "high"])
            p.noise_level = noise_options[_seed_int(slug, "n5n") % len(noise_options)]
            p.crowd_level = crowd_options[_seed_int(slug, "n5c") % len(crowd_options)]
            mask_prob = _MASK_PROB_BY_CAT.get(cat_slug, 4)
            p.mask_required = (_seed_int(slug, "n5m") % 100) < mask_prob
            written += 1
            if written % 2000 == 0:
                db.session.commit()
    db.session.commit()
    print(f"backfill_place_extras_r5: filled noise/crowd/mask on {written} place rows")


# ---------------------------------------------------------------------------
# R5 routes: walking indoor routes, EV-route charging stops, multi-modal.
# ---------------------------------------------------------------------------
_R5_ROUTES = [
    # (origin_query, dest_query, mode, distance, duration, summary, steps)
    ("LAX Terminal 1", "LAX Tom Bradley International",
     "walking", "0.4 mi", "8 min",
     "Indoor walking route via the post-security connector tunnel.", [
        {"instruction": "Head east through the Terminal 1 mezzanine", "distance": "150 m"},
        {"instruction": "Take the moving walkway through the connector", "distance": "300 m"},
        {"instruction": "Follow signs to Tom Bradley International (TBIT)", "distance": "100 m"},
        {"instruction": "Arrive at TBIT departures level 3", "distance": "30 m"},
     ]),
    ("JFK Terminal 4", "JFK Terminal 5",
     "walking", "0.6 mi", "12 min",
     "Indoor walking route via the AirTrain post-security walkway.",
     [{"instruction": "Take AirTrain Terminal-4 stop", "distance": "150 m"},
      {"instruction": "Transfer at JFK Federal Circle", "distance": "Air"},
      {"instruction": "AirTrain to Terminal 5", "distance": "Air"},
      {"instruction": "Walk into Terminal 5 arrivals", "distance": "120 m"}]),
    ("San Francisco", "Reno",
     "driving", "220 mi", "3h 45min",
     "EV route from San Francisco to Reno via I-80 E with charging stop at Truckee.",
     [{"instruction": "Take I-80 E from SF", "distance": "60 mi"},
      {"instruction": "EV stop: Electrify America Vacaville (350 kW)", "distance": "5 km"},
      {"instruction": "Continue on I-80 E through Sierra Nevada", "distance": "120 mi"},
      {"instruction": "EV stop: Tesla Supercharger Truckee (V3)", "distance": "5 km"},
      {"instruction": "Arrive in Reno via I-580 N", "distance": "35 mi"}]),
    ("Boston", "Cape Cod",
     "driving", "75 mi", "1h 35min",
     "EV route from Boston to Cape Cod with mid-route fast charge at Plymouth.",
     [{"instruction": "Take I-93 S out of Boston", "distance": "12 mi"},
      {"instruction": "Merge onto MA-3 S toward Cape Cod", "distance": "30 mi"},
      {"instruction": "EV stop: Electrify America Plymouth (350 kW)", "distance": "5 km"},
      {"instruction": "Continue on US-6 across the Sagamore Bridge", "distance": "25 mi"},
      {"instruction": "Arrive in Cape Cod", "distance": "3 mi"}]),
    ("Chicago Union Station", "O'Hare International Airport",
     "transit", "18 mi", "55 min",
     "Multi-modal transit route from Union Station to O'Hare via CTA Blue Line.",
     [{"instruction": "Walk from Union Station to Clinton Blue Line stop", "distance": "0.3 mi"},
      {"instruction": "Board CTA Blue Line toward O'Hare", "distance": "—"},
      {"instruction": "Stay on Blue Line for 22 stops (~45 min)", "distance": "—"},
      {"instruction": "Exit at O'Hare terminal station", "distance": "—"},
      {"instruction": "Follow signs to your departure terminal", "distance": "0.2 mi"}]),
    ("Seattle Convention Center", "Pike Place Market",
     "walking", "0.7 mi", "14 min",
     "Accessibility-route-preferred walk with curb cuts and elevators only.",
     [{"instruction": "Exit Convention Center via south-side elevator", "distance": "50 m"},
      {"instruction": "Cross Pike St at marked crosswalk with curb ramp", "distance": "30 m"},
      {"instruction": "Continue west on Pike St (sidewalk, level grade)", "distance": "650 m"},
      {"instruction": "Cross 1st Ave using audible signal", "distance": "30 m"},
      {"instruction": "Enter Pike Place Market via the accessible north entrance", "distance": "40 m"}]),
    ("San Francisco", "Los Angeles",
     "driving", "382 mi", "5h 50min",
     "Two-stop EV route SF to LA via I-5 S with fast-charge plazas at Kettleman City and Tejon Ranch.",
     [{"instruction": "Take US-101 S out of SF to I-5 S", "distance": "40 mi"},
      {"instruction": "Continue south on I-5 through Central Valley", "distance": "160 mi"},
      {"instruction": "EV stop: Tesla Supercharger Kettleman City (V3, 250 kW)", "distance": "5 km"},
      {"instruction": "Continue south on I-5 across the Grapevine", "distance": "100 mi"},
      {"instruction": "EV stop: Electrify America Tejon Ranch (350 kW)", "distance": "5 km"},
      {"instruction": "Continue I-5 S into LA", "distance": "75 mi"}]),
    ("Penn Station", "MetLife Stadium",
     "transit", "8 mi", "40 min",
     "Group-meetup transit route via NJ Transit train to Secaucus Junction and Meadowlands shuttle.",
     [{"instruction": "Board NJ Transit train at Penn Station NY", "distance": "—"},
      {"instruction": "Transfer at Secaucus Junction", "distance": "—"},
      {"instruction": "Take Meadowlands Sports Complex shuttle", "distance": "—"},
      {"instruction": "Arrive at MetLife Stadium", "distance": "—"}]),
]


def expand_routes_r5(db, Route):
    """Add curated R5 routes (indoor walking, EV stops, multi-modal,
    accessibility-preferred). Idempotent: gated on route count >= 108."""
    if Route.query.count() >= 108:
        return
    added = 0
    for entry in _R5_ROUTES:
        origin_q, dest_q, mode, dist_label, dur_label, summary, steps = entry
        if Route.query.filter_by(
                origin_query=origin_q, destination_query=dest_q, mode=mode).first():
            continue
        # Parse km from distance label (best-effort)
        try:
            if "mi" in dist_label:
                km = float(dist_label.split()[0]) * 1.609
            else:
                km = float(dist_label.split()[0])
        except (ValueError, IndexError):
            km = 0.0
        # Parse minutes from duration label
        dur_min = 0
        try:
            if "h" in dur_label:
                parts = dur_label.replace("min", "").split("h")
                dur_min = int(parts[0]) * 60 + int(parts[1].strip() or 0)
            else:
                dur_min = int(dur_label.split()[0])
        except (ValueError, IndexError):
            dur_min = 0
        db.session.add(Route(
            origin_query=origin_q, destination_query=dest_q,
            origin_name=origin_q, destination_name=dest_q,
            mode=mode, distance=dist_label, distance_km=round(km, 2),
            duration=dur_label, duration_min=dur_min,
            steps_json=json.dumps(steps),
            summary=summary,
            origin_address=origin_q, destination_address=dest_q,
        ))
        added += 1
    db.session.commit()
    print(f"expand_routes_r5: added {added} R5 routes (total {Route.query.count()})")


def backfill_transit_delays(db, TransitLine):
    """Deterministic realtime-style delay backfill on every TransitLine row.

    Skips rows that already have last_update set so warm restarts are no-ops.
    """
    rows = TransitLine.query.order_by(TransitLine.id).all()
    if not rows:
        return
    filled = sum(1 for r in rows if r.last_update)
    if filled >= len(rows) * 0.9:
        return
    _REASONS = [
        "On schedule",
        "Signal problem at next station",
        "Construction near terminal",
        "Heavy passenger volume",
        "Earlier train ahead",
        "Track work in progress",
        "Weather slowdown",
        "Crew change at terminal",
    ]
    for r in rows:
        if r.last_update:
            continue
        seed = _seed_int(r.slug, "delay")
        # 35% on-schedule, otherwise delay 1-12 min
        is_on_time = (seed % 100) < 35
        if is_on_time:
            r.current_delay_min = 0
            r.delay_reason = "On schedule"
        else:
            r.current_delay_min = 1 + (seed % 12)
            r.delay_reason = _REASONS[1 + ((seed >> 4) % (len(_REASONS) - 1))]
        # last_update is a fixed-string snapshot (no datetime.now); the
        # tens-of-minutes part is deterministic from slug.
        r.last_update = f"{1 + ((seed >> 8) % 12)} min ago"
    db.session.commit()
    print(f"backfill_transit_delays: updated {len(rows)} transit lines")



# ---------------------------------------------------------------------------
# R6 expansion: cross-page density. ~120 templates × 812 cities = ~97k places
# bringing the Place table from ~200k to ~280k+. Categories mix high-traffic
# everyday venues (groceries, drugstores, dental, vet, fitness) with
# experience-rich destinations (food halls, breweries, performance venues)
# so cross-page tasks (search -> place -> /menu -> /photos -> /reviews) all
# land on rows with rich content rather than stubs.
# ---------------------------------------------------------------------------
_R6_TEMPLATES = [
    # ---- Restaurants — more concrete sub-styles for menu/booking flows ----
    ("restaurants", "{anchor} Harbor Seafood House", "Seafood restaurant",
     "Waterfront seafood house with raw bar, daily oyster selection, and a 4-course tasting menu.",
     "$$$", 4.2, 4.8, "", ""),
    ("restaurants", "{anchor} Smokestack BBQ", "BBQ joint",
     "Slow-smoked Texas-style BBQ with brisket, burnt ends, and house-made sides; counter service.",
     "$$", 4.3, 4.8, "", ""),
    ("restaurants", "{anchor} Garden Vegan Kitchen", "Vegan restaurant",
     "Plant-based kitchen with seasonal bowls, house-made cashew cheese, and zero-waste sourcing.",
     "$$", 4.4, 4.9, "", ""),
    ("restaurants", "{anchor} Late-Night Diner", "24-hour diner",
     "Classic American diner open 24 hours; pancakes, milkshakes, and a counter that fills after midnight.",
     "$", 4.0, 4.6, "", ""),
    ("restaurants", "{anchor} Dim Sum Palace", "Dim sum",
     "Cart-service dim sum palace with weekend brunch lines and a 60-item menu.",
     "$$", 4.3, 4.8, "", ""),
    ("restaurants", "{anchor} Pho House", "Vietnamese",
     "Family-run pho house with bone-broth simmered overnight and a build-your-own herb plate.",
     "$", 4.4, 4.9, "", ""),
    ("restaurants", "{anchor} Greek Taverna", "Greek",
     "Taverna with charcoal-grilled meats, mezze platters, and patio seating under string lights.",
     "$$", 4.3, 4.8, "", ""),
    ("restaurants", "{anchor} Curry House", "Indian",
     "South Indian curry house with house-ground spices, dosas, and a weekday lunch thali.",
     "$$", 4.2, 4.7, "", ""),
    ("restaurants", "{anchor} Korean BBQ Counter", "Korean BBQ",
     "Tabletop Korean BBQ with banchan parade, marinated short ribs, and soju cocktails.",
     "$$$", 4.3, 4.8, "", ""),
    ("restaurants", "{anchor} Pasta Workshop", "Italian",
     "Open-kitchen pasta workshop where every shape is rolled, cut, and finished to order.",
     "$$$", 4.5, 4.9, "", ""),

    # ---- Coffee shops ----
    ("coffee-shops", "{anchor} Third Wave Roasters", "Specialty coffee",
     "Third-wave specialty roaster with single-origin pour-overs and a cupping bar.",
     "$$", 4.4, 4.9, "", ""),
    ("coffee-shops", "{anchor} Cafe Latte Bar", "Cafe",
     "Neighborhood cafe specialising in latte art and house-baked pastries; laptop-friendly hours.",
     "$", 4.2, 4.7, "", ""),
    ("coffee-shops", "{anchor} Drive-Thru Espresso", "Espresso drive-thru",
     "Drive-thru espresso stand on the morning commute; quick lane and bike window.",
     "$", 3.9, 4.4, "", ""),
    ("coffee-shops", "{anchor} Co-Working Brewbar", "Co-working cafe",
     "Co-working cafe with bottomless drip, private call booths, and day-pass desks.",
     "$$", 4.1, 4.6, "", ""),
    ("coffee-shops", "{anchor} Tea House", "Tea house",
     "Loose-leaf tea house with 80+ teas, matcha service, and quiet reading benches.",
     "$$", 4.5, 4.9, "", ""),

    # ---- Coffee chains — populate chain_brand so "same chain" surfaces ----
    ("coffee-shops", "Starbucks Reserve — {anchor} Roastery", "Coffee chain",
     "Starbucks Reserve roastery with a 4-bar coffee experience and small-lot tastings.",
     "$$", 4.0, 4.6, "", ""),
    ("coffee-shops", "Blue Bottle Coffee — {anchor}", "Coffee chain",
     "Blue Bottle Coffee shop with single-origin pour-overs and minimalist ceramic mugs.",
     "$$", 4.2, 4.7, "", ""),
    ("coffee-shops", "Peet's Coffee — {anchor} Avenue", "Coffee chain",
     "Peet's Coffee location with dark roasts and a community brew bar.",
     "$", 4.0, 4.6, "", ""),
    ("coffee-shops", "Dunkin' — {anchor} Plaza", "Coffee chain",
     "Dunkin' donut and coffee shop with a drive-thru and 24-hour weekend service.",
     "$", 3.9, 4.4, "", ""),

    # ---- Supermarkets ----
    ("supermarkets", "{anchor} Whole Foods Market", "Organic grocery",
     "Organic grocery with a hot bar, in-house bakery, and a curbside pickup lane.",
     "$$", 4.1, 4.7, "", ""),
    ("supermarkets", "{anchor} Trader Joe's", "Specialty grocery",
     "Specialty grocery with private-label snacks, frozen meals, and a $3 wine wall.",
     "$", 4.5, 4.9, "", ""),
    ("supermarkets", "{anchor} Costco Wholesale", "Warehouse club",
     "Membership warehouse club with bulk grocery, electronics, and a gas station.",
     "$", 4.4, 4.9, "", ""),
    ("supermarkets", "{anchor} Safeway", "Grocery chain",
     "Full-service Safeway grocery with deli, pharmacy, and a Starbucks counter.",
     "$$", 3.9, 4.4, "", ""),
    ("supermarkets", "{anchor} Asian Market", "Asian grocery",
     "Pan-Asian grocery with fresh produce, live seafood tanks, and a hot-food counter.",
     "$$", 4.3, 4.8, "", ""),

    # ---- Pharmacies ----
    ("pharmacies", "{anchor} CVS Pharmacy", "Pharmacy chain",
     "CVS Pharmacy with 24-hour prescriptions, MinuteClinic, and a photo center.",
     "$$", 3.8, 4.4, "", ""),
    ("pharmacies", "{anchor} Walgreens", "Pharmacy chain",
     "Walgreens drugstore with 24-hour pharmacy, beauty aisle, and a balcony patio.",
     "$$", 3.7, 4.3, "", ""),
    ("pharmacies", "{anchor} Compounding Pharmacy", "Compounding pharmacy",
     "Independent compounding pharmacy for custom dosages, pet meds, and topical creams.",
     "$$", 4.4, 4.9, "", ""),

    # ---- Dentists / vets / urgent care — high-traffic 'real life' venues ----
    ("dentists", "{anchor} Smile Studio Dental", "Dental office",
     "General and cosmetic dentistry with sedation options, digital X-rays, and a kids' room.",
     "$$$", 4.4, 4.9, "", ""),
    ("dentists", "{anchor} Family Dentistry", "Family dentistry",
     "Family dentist accepting most insurance; weekend appointments and emergency slots.",
     "$$", 4.3, 4.8, "", ""),
    ("dentists", "{anchor} Orthodontics", "Orthodontist",
     "Orthodontist offering invisible aligners, traditional braces, and free consultations.",
     "$$$", 4.5, 4.9, "", ""),
    ("veterinarians", "{anchor} Animal Hospital", "Animal hospital",
     "Full-service veterinary hospital with surgery, dental, and 24-hour emergency intake.",
     "$$$", 4.4, 4.9, "", ""),
    ("veterinarians", "{anchor} Cat Specialty Vet", "Cat-only vet",
     "Cat-only veterinary clinic with quiet exam rooms and a feline-only boarding floor.",
     "$$$", 4.6, 4.9, "", ""),
    ("hospitals", "{anchor} Urgent Care Center", "Urgent care",
     "Walk-in urgent care for non-emergencies; X-ray, labs, and most insurance accepted.",
     "$$", 4.0, 4.6, "", ""),

    # ---- Fitness ----
    ("fitness", "{anchor} CrossFit Box", "CrossFit gym",
     "CrossFit affiliate with daily group WODs, open-gym hours, and a coaching team.",
     "$$$", 4.4, 4.9, "", ""),
    ("fitness", "{anchor} Yoga & Pilates Studio", "Yoga studio",
     "Heated yoga and Pilates studio with vinyasa, yin, and a Saturday community class.",
     "$$", 4.5, 4.9, "", ""),
    ("fitness", "{anchor} Climbing Gym", "Climbing gym",
     "Indoor climbing gym with bouldering, top-rope routes, and a kids' learn-to-climb area.",
     "$$$", 4.5, 4.9, "", ""),
    ("fitness", "{anchor} Boxing Club", "Boxing gym",
     "Boxing club with heavy bags, sparring ring, and beginner classes.",
     "$$", 4.4, 4.9, "", ""),
    ("fitness", "{anchor} Lap Pool & Aquatics", "Aquatic center",
     "Aquatic center with a 25 m lap pool, family pool, and accessible chair lift.",
     "$$", 4.3, 4.8, "", ""),

    # ---- Parks & Nature ----
    ("parks", "{anchor} River Greenway Trailhead", "Greenway trail",
     "River greenway trailhead with paved path, water fountains, and a bike-share dock.",
     "Free", 4.5, 4.9, "", ""),
    ("parks", "{anchor} Botanical Garden", "Botanical garden",
     "Botanical garden with native plant collections, seasonal exhibits, and a tea pavilion.",
     "$$", 4.6, 4.9, "", ""),
    ("parks", "{anchor} Off-Leash Dog Park", "Dog park",
     "Off-leash dog park with shaded benches, separate small-dog area, and a wash station.",
     "Free", 4.3, 4.8, "", ""),
    ("parks", "{anchor} Skate Plaza", "Skate park",
     "Public skate plaza with bowl, street section, and lights on until 10 PM.",
     "Free", 4.4, 4.9, "", ""),

    # ---- Attractions / sightseeing ----
    ("attractions", "{anchor} Observatory Deck", "Observation deck",
     "Indoor-outdoor observation deck with telescopes, audio guide, and a glass-floor section.",
     "$$$", 4.5, 4.9, "", ""),
    ("attractions", "{anchor} Aquarium", "Aquarium",
     "Aquarium with a Pacific reef tunnel, touch tide-pool, and behind-the-scenes tours.",
     "$$$", 4.4, 4.9, "", ""),
    ("attractions", "{anchor} Zoo", "Zoo",
     "Family zoo with a giraffe-feeding deck, primate house, and a zip-line over the lagoon.",
     "$$$", 4.3, 4.8, "", ""),
    ("attractions", "{anchor} Historic Lighthouse", "Lighthouse",
     "Working historic lighthouse with a 100-step climb to the lamp room.",
     "$", 4.5, 4.9, "", ""),

    # ---- Entertainment ----
    ("entertainment", "{anchor} Indie Cinema", "Movie theater",
     "Indie cinema showing first-run, foreign, and revival films; reclining seats.",
     "$$", 4.4, 4.9, "", ""),
    ("entertainment", "{anchor} Comedy Cellar", "Comedy club",
     "Below-grade comedy club with nightly stand-up sets and a two-drink minimum.",
     "$$$", 4.5, 4.9, "", ""),
    ("entertainment", "{anchor} Live Music Hall", "Music venue",
     "Mid-size live music hall hosting touring bands; balcony reserved seating and a pit area.",
     "$$$", 4.5, 4.9, "", ""),
    ("entertainment", "{anchor} Escape Room Co.", "Escape room",
     "Escape-room venue with 6 themed rooms; team sizes 2-8, online booking required.",
     "$$$", 4.6, 4.9, "", ""),

    # ---- Shopping ----
    ("shopping", "{anchor} Independent Bookstore", "Bookstore",
     "Independent bookstore with curated staff picks, author events, and an espresso bar.",
     "$$", 4.6, 4.9, "", ""),
    ("shopping", "{anchor} Vinyl Records", "Record store",
     "Vinyl record store with new pressings, used bins, and an in-store listening booth.",
     "$$", 4.5, 4.9, "", ""),
    ("shopping", "{anchor} Outdoor Outfitter", "Outdoor gear",
     "Outdoor gear shop with rental skis, paddleboards, and an in-house boot fitter.",
     "$$$", 4.4, 4.9, "", ""),
    ("shopping", "{anchor} Vintage Thrift", "Thrift store",
     "Curated vintage thrift store with hand-picked denim, leather, and vintage tees.",
     "$$", 4.3, 4.8, "", ""),

    # ---- Health & beauty ----
    ("health-beauty", "{anchor} Day Spa", "Day spa",
     "Day spa with massage suites, sauna, eucalyptus steam room, and bridal packages.",
     "$$$$", 4.5, 4.9, "", ""),
    ("health-beauty", "{anchor} Nail Salon", "Nail salon",
     "Nail salon with gel, dip, and natural-nail manicures; same-day appointments welcome.",
     "$$", 4.3, 4.8, "", ""),
    ("health-beauty", "{anchor} Barbershop", "Barbershop",
     "Classic barbershop with straight-razor shaves, beard trims, and walk-in service.",
     "$$", 4.5, 4.9, "", ""),
    ("health-beauty", "{anchor} Tattoo Studio", "Tattoo parlor",
     "Tattoo studio with appointment-only sessions, flash days, and a guest-artist calendar.",
     "$$$", 4.6, 4.9, "", ""),

    # ---- Services ----
    ("services", "{anchor} Bike Repair Co-Op", "Bike repair",
     "Member-supported bike repair co-op with stand rentals, tune-ups, and used parts.",
     "$", 4.5, 4.9, "", ""),
    ("services", "{anchor} Print & Copy Shop", "Print shop",
     "Print and copy shop with same-day binding, posters, and shipping kiosk.",
     "$$", 4.0, 4.5, "", ""),
    ("services", "{anchor} Laundromat & Drop-Off", "Laundromat",
     "Self-service laundromat with drop-off wash-and-fold and free Wi-Fi.",
     "$", 3.9, 4.4, "", ""),
    ("services", "{anchor} Locksmith 24/7", "Locksmith",
     "Mobile locksmith providing 24-hour emergency lockout service for home, auto, and office.",
     "$$", 4.4, 4.9, "", ""),

    # ---- Libraries ----
    ("libraries", "{anchor} Public Library Branch", "Public library",
     "Public library branch with children's storytime, a maker lab, and 12 quiet study rooms.",
     "Free", 4.6, 4.9, "", ""),
    ("libraries", "{anchor} Law Library", "Law library",
     "Reference law library open to the public; secondary sources and reading rooms.",
     "Free", 4.4, 4.9, "", ""),

    # ---- Schools / campus ----
    ("schools", "{anchor} Montessori Academy", "Montessori school",
     "Montessori academy for ages 3-12 with mixed-age classrooms and a garden program.",
     "$$$$", 4.5, 4.9, "", ""),
    ("campus-buildings", "{anchor} University — Student Union", "Student union",
     "Student union with a food court, study lounges, a game room, and event ballrooms.",
     "$", 4.3, 4.8, "lounge", "1"),
    ("campus-buildings", "{anchor} University — Performing Arts Center", "Performing arts",
     "Campus performing arts center with a 1200-seat theater and rehearsal halls.",
     "$$", 4.6, 4.9, "wing", "1"),

    # ---- Religious ----
    ("religious", "{anchor} Community Church", "Church",
     "Community church with weekend services, choir loft, and a neighborhood food pantry.",
     "Free", 4.5, 4.9, "", ""),
    ("religious", "{anchor} Mosque", "Mosque",
     "Neighborhood mosque with daily prayers, Friday khutbah, and a Quran-study program.",
     "Free", 4.6, 4.9, "", ""),
    ("religious", "{anchor} Temple", "Temple",
     "Hindu temple with daily aarti, monthly puja calendar, and community kitchen.",
     "Free", 4.7, 4.9, "", ""),
    ("religious", "{anchor} Synagogue", "Synagogue",
     "Reform synagogue with Shabbat services, religious school, and a small library.",
     "Free", 4.6, 4.9, "", ""),

    # ---- ATMs / banks ----
    ("atms", "{anchor} Chase ATM Branch", "ATM",
     "Chase ATM with cardless cash, deposit envelopes, and 24-hour drive-up access.",
     "Free", 3.8, 4.3, "", ""),
    ("atms", "{anchor} Bank of America Drive-Up", "ATM",
     "Bank of America drive-up ATM with stacked-bill deposits and a withdrawals quick-cash button.",
     "Free", 3.7, 4.3, "", ""),

    # ---- Car rental ----
    ("car-rental", "Hertz — {anchor} Airport", "Car rental",
     "Hertz rental counter at the airport with gold-club fast-lane and EV options.",
     "$$", 3.8, 4.4, "", ""),
    ("car-rental", "Enterprise Rent-A-Car — {anchor} Downtown", "Car rental",
     "Enterprise downtown branch with free pickup, weekend specials, and a moving-truck lot.",
     "$$", 4.1, 4.7, "", ""),
    ("car-rental", "Turo Host Garage — {anchor}", "Peer-to-peer car rental",
     "Turo peer-to-peer host garage; instant book, contactless key handoff, and EV listings.",
     "$$", 4.5, 4.9, "", ""),

    # ---- Public restrooms ----
    ("public-restrooms", "{anchor} Park Public Restroom", "Public restroom",
     "Public restroom inside the city park with baby-changing station and a 24/7 attendant.",
     "Free", 3.7, 4.3, "", ""),
    ("public-restrooms", "{anchor} Transit Hub Restroom", "Transit restroom",
     "Transit-hub public restroom open during station hours; wheelchair-accessible stall.",
     "Free", 3.6, 4.2, "", ""),

    # ---- Beaches ----
    ("beaches", "{anchor} North Beach Lifeguard Tower 5", "Lifeguard tower",
     "Lifeguard tower 5 on the north beach with rip-current advisories and a first-aid kit.",
     "Free", 4.4, 4.9, "", ""),
    ("beaches", "{anchor} Pier Beach Volleyball Courts", "Volleyball courts",
     "Pier beach with 8 volleyball courts, equipment rental, and tournament Sundays.",
     "Free", 4.5, 4.9, "", ""),

    # ---- Hotels — more variety for chain + better-rated tests ----
    ("hotels", "Marriott — {anchor} Downtown", "Hotel chain",
     "Marriott downtown hotel with executive lounge, rooftop bar, and a Bonvoy desk.",
     "$$$$", 4.2, 4.7, "", ""),
    ("hotels", "Hilton Garden Inn — {anchor}", "Hotel chain",
     "Hilton Garden Inn with a 24-hour pavilion pantry and indoor pool.",
     "$$$", 4.1, 4.7, "", ""),
    ("hotels", "Holiday Inn Express — {anchor} North", "Hotel chain",
     "Holiday Inn Express north branch with free breakfast and a small fitness room.",
     "$$", 4.0, 4.6, "", ""),
    ("hotels", "Hyatt Place — {anchor}", "Hotel chain",
     "Hyatt Place with a 24-hour gallery menu, free Wi-Fi, and meeting rooms.",
     "$$$", 4.1, 4.7, "", ""),
    ("hotels", "{anchor} Boutique Inn", "Boutique hotel",
     "Boutique inn in a converted historic building with 18 rooms and a courtyard bar.",
     "$$$$", 4.6, 4.9, "", ""),

    # ---- Bus stops ----
    ("bus-stops", "{anchor} University Loop Bus Stop", "Bus stop",
     "University loop bus stop with sheltered seating, route map, and a real-time arrival board.",
     "Free", 3.7, 4.3, "", ""),
    ("bus-stops", "{anchor} Riverside Express Stop", "Bus stop",
     "Riverside express bus stop served by commuter routes during peak hours only.",
     "Free", 3.6, 4.2, "", ""),

    # ---- Transit hubs ----
    ("transit", "{anchor} Greyhound Station", "Bus terminal",
     "Greyhound intercity bus terminal with overnight bays, package counter, and ticket kiosks.",
     "$", 3.5, 4.1, "", ""),
    ("transit", "{anchor} Amtrak Station", "Train station",
     "Amtrak station with regional and long-distance service, Quik-Trak kiosks, and an enclosed waiting room.",
     "$", 3.9, 4.5, "", ""),

    # ---- Police / fire / post ----
    ("police-stations", "{anchor} Precinct 12 Station", "Police precinct",
     "Precinct 12 police station with public lobby, records counter, and a 24-hour desk.",
     "Free", 3.7, 4.3, "", ""),
    ("fire-stations", "{anchor} Fire Station 7", "Fire station",
     "Fire station 7 with truck bays, open-house Saturdays, and CPR class sign-ups.",
     "Free", 4.5, 4.9, "", ""),
    ("post-offices", "{anchor} Downtown Post Office", "Post office",
     "Downtown post office with passport applications, PO boxes, and Saturday hours.",
     "$", 3.6, 4.2, "", ""),

    # ---- Playgrounds ----
    ("playgrounds", "{anchor} Adventure Playground", "Adventure playground",
     "Adventure playground with rope climbing structures, ziplines, and a sand-and-water area.",
     "Free", 4.5, 4.9, "", ""),
    ("playgrounds", "{anchor} Inclusive Sensory Playground", "Inclusive playground",
     "Inclusive sensory playground with wheelchair-accessible equipment and quiet sensory pods.",
     "Free", 4.7, 4.9, "", ""),

    # ---- Dog parks ----
    ("dog-parks", "{anchor} Riverside Dog Park", "Dog park",
     "Riverside dog park with a separate small-dog area, water fountains, and shaded benches.",
     "Free", 4.4, 4.9, "", ""),

    # ---- More EV chargers + parking variety to feed parking-ev tasks ----
    ("ev-charging", "Tesla Destination Charger — {anchor} Hotel Row", "Tesla destination",
     "Tesla Destination Charger at hotel row; guest-only J1772 ports during stay.",
     "$", 4.1, 4.6, "charger-bay", ""),
    ("ev-charging", "Wallbox Public Network — {anchor}", "Wallbox public",
     "Wallbox Public Network 22 kW chargers in the city employee lot; weekends public.",
     "$", 4.0, 4.5, "charger-bay", ""),
    ("parking", "{anchor} Convention Lot B Overflow", "Surface lot",
     "Convention center overflow lot B; opens game days and conventions with shuttle.",
     "$$", 3.7, 4.3, "", ""),
    ("parking", "{anchor} Garage 7 EV Roof Level", "Parking garage",
     "Garage 7 roof level dedicated EV charging row; 60 stalls with CCS connectors.",
     "$$", 4.1, 4.7, "parking-deck", "R"),
    ("parking", "{anchor} Stadium Tailgate Lot", "Tailgate lot",
     "Stadium tailgate lot opens 4 hours before kickoff; pull-through RV spaces.",
     "$$$", 4.0, 4.6, "", ""),

    # ---- Food halls / breweries (for cross-page menu+booking flows) ----
    ("restaurants", "{anchor} Food Hall — Central Stalls", "Food hall",
     "Central food hall housing 18 stalls — tacos, pho, pizza, dosas, and shave ice.",
     "$$", 4.3, 4.8, "food-court", "1"),
    ("restaurants", "{anchor} Riverside Brewery", "Brewery",
     "Riverside brewery with 12 taps, beer-garden patio, and a wood-fired pizza oven.",
     "$$", 4.4, 4.9, "", ""),
    ("restaurants", "{anchor} Cidery & Tasting Room", "Cidery",
     "Cidery tasting room with single-orchard varietals, flights, and farm-fresh charcuterie.",
     "$$", 4.5, 4.9, "", ""),
    ("restaurants", "{anchor} Wine Country Tasting Room", "Wine tasting",
     "In-town tasting room pouring 8 of the region's small-batch wineries; reservations welcome.",
     "$$$", 4.6, 4.9, "", ""),

    # ---- More museums ----
    ("museums", "{anchor} Children's Museum", "Children's museum",
     "Children's museum with hands-on exhibits, a climbable city block, and a sensory-friendly hour.",
     "$$", 4.6, 4.9, "wing", "1"),
    ("museums", "{anchor} Natural History Museum", "Natural history",
     "Natural history museum with dinosaur hall, mineral gallery, and a planetarium.",
     "$$$", 4.5, 4.9, "wing", "1"),
    ("museums", "{anchor} Science Center", "Science center",
     "Hands-on science center with an IMAX dome, lightning show, and a butterfly atrium.",
     "$$$", 4.5, 4.9, "wing", "1"),

    # ---- More schools / education ----
    ("schools", "{anchor} High School", "High school",
     "Public high school with AP courses, JROTC, and a 1000-seat auditorium.",
     "Free", 3.9, 4.5, "", ""),
    ("schools", "{anchor} Community College", "Community college",
     "Community college campus with workforce training, transfer programs, and a culinary arts kitchen.",
     "$$", 4.2, 4.7, "", ""),

    # ---- Cinema / events ----
    ("entertainment", "{anchor} Drive-In Theater", "Drive-in theater",
     "Drive-in theater open spring through fall; double features and FM-radio audio.",
     "$$", 4.6, 4.9, "", ""),
    ("entertainment", "{anchor} Bowling Alley", "Bowling alley",
     "32-lane bowling alley with cosmic lanes Fridays, arcade, and a 16-seat sports bar.",
     "$$", 4.2, 4.7, "", ""),
]
# ~120 templates above — slug index is per-city deterministic.


def expand_places_r6(db, Place, Category, City):
    """R6 expansion: cross-page density (everyday venues + chains).

    Idempotent: gated on Place count >= 275000.  Aims to add ~80-100k
    rows so the table sits comfortably above 280k.
    """
    if Place.query.count() >= 275000:
        return

    cat_by_slug = {c.slug: c for c in Category.query.all()}
    cities = City.query.order_by(City.id).all()
    if not cities:
        return

    # Re-use donor image pool from existing places.
    donor_pool = []
    for p in (Place.query
              .filter(Place.hero_image.like("/static/images/places/%"))
              .order_by(Place.id).limit(80).all()):
        try:
            photos = json.loads(p.photos_json or "[]")
        except Exception:
            photos = []
        if p.hero_image:
            donor_pool.append((p.hero_image, photos or [p.hero_image]))
    if not donor_pool:
        donor_pool = [("/static/images/heroes/eiffel-tower.jpg",
                       ["/static/images/heroes/eiffel-tower.jpg"])]

    # Brand extraction: when the template name starts with a known
    # brand prefix, populate chain_brand so the place_detail page's
    # "From the same chain" rail can find siblings.
    _CHAINS = (
        "Starbucks Reserve", "Blue Bottle Coffee", "Peet's Coffee", "Dunkin'",
        "Whole Foods Market", "Trader Joe's", "Costco Wholesale", "Safeway",
        "CVS Pharmacy", "Walgreens",
        "Hertz", "Enterprise Rent-A-Car", "Turo",
        "Marriott", "Hilton Garden Inn", "Holiday Inn Express", "Hyatt Place",
        "Tesla Destination Charger", "Wallbox Public Network",
    )

    added = 0
    for city in cities:
        anchor = city.display_name.split(",")[0].split(" ")[0]
        templates = list(enumerate(_R6_TEMPLATES))
        # Fisher-Yates deterministic shuffle keyed by city slug.
        for i in range(len(templates) - 1, 0, -1):
            j = int.from_bytes(
                hashlib.md5(f"r6sh:{city.slug}:{i}".encode()).digest()[:4],
                "big") % (i + 1)
            templates[i], templates[j] = templates[j], templates[i]

        for idx, tpl in templates:
            (cat_slug, pattern, subtitle, desc, price, rlo, rhi,
             indoor_zone, floor_num) = tpl
            cat = cat_by_slug.get(cat_slug)
            if not cat:
                continue
            slug = f"r6-{city.slug}-{cat_slug}-{idx:02d}"
            if Place.query.filter_by(slug=slug).first():
                continue

            name = pattern.format(anchor=anchor)
            local_seed = _seed_int_hex(slug, "r6loc")
            hero, gallery = donor_pool[local_seed % len(donor_pool)]
            lat = city.lat + ((local_seed % 800) - 400) / 10000.0
            lng = city.lng + (((local_seed // 800) % 1000) - 500) / 10000.0
            rating = round(rlo + (local_seed % 100) / 100.0 * (rhi - rlo), 1)
            review_count = 18 + (local_seed % 4200)

            # Resolve chain_brand from the rendered name (preserves the
            # original prefix even after the {anchor} substitution).
            chain = ""
            for brand in _CHAINS:
                if name.startswith(brand):
                    chain = brand
                    break

            hours_pick = (local_seed >> 4) % 6
            hours_options = [
                "Mon-Sun: 9:00 AM - 9:00 PM",
                "Mon-Sat: 10:00 AM - 8:00 PM, Sun 11:00 AM - 6:00 PM",
                "Tue-Sun: 11:00 AM - 10:00 PM, Closed Mon",
                "Open 24 hours",
                "Mon-Fri: 7:00 AM - 7:00 PM, Weekends 8:00 AM - 5:00 PM",
                "Mon-Sun: 6:00 AM - 10:00 PM",
            ]
            tags = [cat_slug, anchor.lower(), city.country.lower()]
            if indoor_zone:
                tags.append(indoor_zone)
            if chain:
                tags.append(chain.lower().replace(" ", "-"))

            db.session.add(Place(
                slug=slug, name=name, category_id=cat.id, city_id=city.id,
                subtitle=subtitle,
                description=desc,
                address=f"{15 + (local_seed % 985)} {['Cedar','Maple','Spruce','Birch','Walnut','Chestnut','Hickory','Sycamore'][local_seed % 8]} St, {city.display_name}",
                phone=f"+{1 + (local_seed % 9)} {200 + (local_seed % 800)} {1000 + (local_seed % 9000)}",
                hours=hours_options[hours_pick],
                website=google_maps_search_url(name, city.display_name),
                rating=rating,
                review_count=review_count,
                price_level=price,
                hero_image=hero,
                photos_json=json.dumps(gallery[:5]),
                lat=lat, lng=lng,
                tags_json=json.dumps(tags),
                subcategory=subtitle,
                chain_brand=chain,
                is_24h=(hours_pick == 3),
                is_popular=(rating >= 4.6 and (local_seed % 4) == 0),
                has_parking_lot=(cat_slug in ("supermarkets", "hotels",
                                              "shopping", "fitness",
                                              "hospitals", "schools",
                                              "religious", "entertainment",
                                              "car-rental", "parking")
                                 or (local_seed % 3) == 0),
                ev_charging=(cat_slug == "ev-charging"
                              or (cat_slug == "hotels" and "Marriott" in name)
                              or (cat_slug == "supermarkets" and "Whole Foods" in name)),
                bicycle_parking=(local_seed % 2) == 0,
                indoor_zone_type=indoor_zone,
                floor_number=floor_num,
                parking_lot_capacity=(60 + (local_seed % 1600)) if cat_slug == "parking" else 0,
                delivery_available=(cat_slug == "restaurants" and (local_seed % 2) == 0),
                dine_in=(cat_slug in ("restaurants", "coffee-shops")),
                takeout=(cat_slug in ("restaurants", "coffee-shops",
                                       "supermarkets")),
                accepts_reservations=(cat_slug == "restaurants" and (local_seed % 3) == 0),
                serves_breakfast=(cat_slug in ("restaurants", "coffee-shops")
                                   and (local_seed % 2) == 0),
                serves_lunch=(cat_slug == "restaurants"),
                serves_dinner=(cat_slug == "restaurants"),
                serves_alcohol=(cat_slug == "restaurants" and (local_seed % 3) == 0),
                serves_vegetarian=(cat_slug == "restaurants" and (local_seed % 2) == 0),
            ))
            added += 1
            if added % 1500 == 0:
                db.session.commit()
    db.session.commit()
    print(f"expand_places_r6: added {added} R6 places (total {Place.query.count()})")


# ---------------------------------------------------------------------------
# R6 edge banners — backfill closure flags + accessibility warnings on a
# deterministic minority of rows so each edge case is observable but the
# overall site doesn't look broken.  All gating is by md5(slug) so the
# same rows get flagged across rebuilds.
# ---------------------------------------------------------------------------
def backfill_place_edges_r6(db, Place):
    """Deterministically flag a small fraction of places with R6 edge
    banners: permanently closed, temporarily closed (with reopen ETA),
    accessibility warning, indoor-floor-unmapped.

    Idempotent: skip rows that already carry a banner.
    """
    # If the column doesn't exist yet (schema older than R6), bail.
    if not hasattr(Place, "is_closed_permanently"):
        return

    BATCH = 2000
    offset = 0
    flagged = {"perm": 0, "temp": 0, "a11y": 0, "unmapped": 0}
    while True:
        rows = (Place.query
                .order_by(Place.id)
                .offset(offset).limit(BATCH).all())
        if not rows:
            break
        offset += BATCH
        for p in rows:
            if (p.is_closed_permanently or p.is_temporarily_closed
                    or p.accessibility_warning or p.indoor_floor_unmapped):
                continue
            slug = p.slug or ""
            seed = _seed_int_hex(slug, "r6edge")
            bucket = seed % 1000
            # ~0.4% permanently closed (≈ ~1k rows on a 280k table)
            if bucket < 4:
                p.is_closed_permanently = True
                reasons = [
                    "Business has ceased operations.",
                    "Lease expired; the location has shut down.",
                    "Owners retired; this branch is closed for good.",
                    "Operation moved to a new address.",
                ]
                p.closure_reason = reasons[(seed >> 4) % len(reasons)]
                flagged["perm"] += 1
            # ~1.2% temporarily closed with a reopen ETA
            elif bucket < 16:
                p.is_temporarily_closed = True
                tmp_reasons = [
                    "Closed for renovation.",
                    "Closed for staff training.",
                    "Closed after fire damage; cleanup in progress.",
                    "Seasonal closure.",
                    "Inventory transition between owners.",
                ]
                p.closure_reason = tmp_reasons[(seed >> 4) % len(tmp_reasons)]
                # Reopen window 3-90 days out, deterministic
                days_out = 3 + ((seed >> 8) % 88)
                reopen = MIRROR_REFERENCE_DATE + timedelta(days=days_out)
                p.reopen_eta = f"Reopens {reopen.strftime('%b %d, %Y')}"
                flagged["temp"] += 1
            # ~2.5% have an accessibility warning visible at the top
            elif bucket < 41:
                a11y_warnings = [
                    "Entrance has a 3-step front stoop; no step-free entry yet.",
                    "Wheelchair ramp is around the side; ask staff for the keyed gate.",
                    "Upstairs dining only; main floor is reservations counter.",
                    "Restroom is on a different floor with no elevator.",
                    "Tactile signage not yet installed at the front desk.",
                    "Service-animal access is restricted to the patio area.",
                ]
                p.accessibility_warning = a11y_warnings[(seed >> 4) % len(a11y_warnings)]
                flagged["a11y"] += 1
            # ~1.6% multi-floor venues missing indoor floor plans
            elif bucket < 57 and (p.indoor_zone_type in ("wing", "concourse",
                                                          "food-court", "lounge",
                                                          "parking-deck")):
                p.indoor_floor_unmapped = True
                flagged["unmapped"] += 1
        db.session.commit()
    print(
        "backfill_place_edges_r6: flagged "
        f"{flagged['perm']} permanently closed, "
        f"{flagged['temp']} temporarily closed, "
        f"{flagged['a11y']} accessibility warnings, "
        f"{flagged['unmapped']} unmapped floor plans"
    )


def backfill_transit_no_service_r6(db, TransitLine):
    """Deterministically suspend service on ~15% of transit lines so the
    realtime dashboard surfaces a 'no service after hours' banner.

    Idempotent: only updates lines whose delay_reason currently isn't a
    no-service marker.  Safe to call alongside backfill_transit_delays.
    """
    rows = TransitLine.query.order_by(TransitLine.id).all()
    if not rows:
        return
    NO_SERVICE_PHRASES = [
        "No service — after hours",
        "No service — overnight maintenance window",
        "No service — special event closure",
    ]
    flagged = 0
    for r in rows:
        if (r.delay_reason or "").lower().startswith("no service"):
            continue
        seed = _seed_int_hex(r.slug or r.name or str(r.id), "r6nosvc")
        if (seed % 100) < 15:  # ~15% suspended
            r.delay_reason = NO_SERVICE_PHRASES[(seed >> 4) % len(NO_SERVICE_PHRASES)]
            r.current_delay_min = 0  # not "delayed", flat-suspended
            r.last_update = f"{2 + ((seed >> 8) % 25)} min ago"
            flagged += 1
    db.session.commit()
    print(f"backfill_transit_no_service_r6: suspended {flagged} transit lines")


# ---------------------------------------------------------------------------
# R7: SEO + locale expansion — additional venue templates that bring the
# Place table from ~290k (R6 cap) to 400k+.  Each template renders an
# extra row per city; with 812 cities × ~140 templates we land ~113k more
# rows.  All R7 templates are designed so the resulting Place rows have
# enough metadata (price_level, category, lat/lng, rating, openingHours-
# compatible hours string) to populate the SEO JSON-LD blocks added on
# place_detail.html.
# ---------------------------------------------------------------------------
_R7_TEMPLATES = [
    # ---- More restaurant sub-styles ----
    ("restaurants", "{anchor} Neapolitan Pizzeria", "Pizzeria",
     "Wood-fired Neapolitan pizzeria certified by the AVPN with imported tipo-00 flour and San Marzano tomatoes.",
     "$$", 4.4, 4.9, "", ""),
    ("restaurants", "{anchor} Hot Pot House", "Hot pot",
     "Family-style hot pot with bone-broth, mala, and tomato bases; weekend lunch combos.",
     "$$", 4.3, 4.8, "", ""),
    ("restaurants", "{anchor} Crawfish Boil Shack", "Cajun",
     "Cajun seafood shack with crawfish boils by the pound, gumbo, and beignets for dessert.",
     "$$", 4.2, 4.7, "", ""),
    ("restaurants", "{anchor} Ethiopian Mesob", "Ethiopian",
     "Communal-platter Ethiopian restaurant with injera, vegetarian combo, and honey wine.",
     "$$", 4.5, 4.9, "", ""),
    ("restaurants", "{anchor} Peruvian Cevicheria", "Peruvian",
     "Modern cevicheria with leche de tigre, anticuchos, and a pisco-forward cocktail list.",
     "$$$", 4.4, 4.9, "", ""),
    ("restaurants", "{anchor} Filipino Kamayan", "Filipino",
     "Banana-leaf kamayan feast with lechon, lumpia, and ube halo-halo; reservations encouraged.",
     "$$$", 4.5, 4.9, "", ""),
    ("restaurants", "{anchor} Caribbean Jerk House", "Caribbean",
     "Jerk-spiced Caribbean kitchen with oxtail, curry goat, and rum-based punches.",
     "$$", 4.3, 4.8, "", ""),
    ("restaurants", "{anchor} Halal Cart", "Street food",
     "Halal lunch cart with chicken-over-rice, gyro plates, and white sauce by the bottle.",
     "$", 4.2, 4.7, "", ""),
    ("restaurants", "{anchor} Brazilian Churrascaria", "Brazilian",
     "All-you-can-eat churrascaria with passador service, salad bar, and caipirinha pitchers.",
     "$$$", 4.3, 4.8, "", ""),
    ("restaurants", "{anchor} Modern Israeli", "Mediterranean",
     "Modern Israeli kitchen with hummus, sabich, lamb shawarma, and tahini soft-serve.",
     "$$", 4.5, 4.9, "", ""),
    ("restaurants", "{anchor} Oyster Bar", "Seafood",
     "Marble-counter oyster bar with East Coast and West Coast lineups, mignonette, and bubbles.",
     "$$$", 4.4, 4.9, "", ""),
    ("restaurants", "{anchor} Cantonese Roast Hall", "Cantonese",
     "Cantonese roast hall hanging crispy-skin pork and char siu in the window since 1992.",
     "$$", 4.4, 4.8, "", ""),
    ("restaurants", "{anchor} Gluten-Free Bakery Cafe", "Bakery",
     "Dedicated gluten-free bakery and cafe with breakfast plates and a kids menu.",
     "$$", 4.4, 4.9, "", ""),
    ("restaurants", "{anchor} Plant-Based Burger Joint", "Burger joint",
     "Plant-based burger joint with house-pressed patties, smash style, and oat-milk shakes.",
     "$$", 4.2, 4.7, "", ""),
    ("restaurants", "{anchor} Late-Night Wing Spot", "Wings",
     "Late-night wing spot with 20 sauces, dry rubs, blue-cheese ranch, and karaoke Tuesdays.",
     "$", 4.0, 4.5, "", ""),

    # ---- Hotels — chain heavy for SEO/JSON-LD Hotel schema ----
    ("hotels", "Marriott {anchor} Downtown", "Hotel chain",
     "Full-service Marriott in the central business district with a rooftop bar and 14 meeting rooms.",
     "$$$", 4.1, 4.7, "lobby", "G"),
    ("hotels", "Hilton Garden Inn {anchor} Riverside", "Hotel chain",
     "Mid-scale Hilton Garden Inn with riverside views, a 24-hour pantry, and an indoor pool.",
     "$$", 4.0, 4.6, "lobby", "G"),
    ("hotels", "Holiday Inn Express {anchor} Airport", "Hotel chain",
     "Airport-corridor Holiday Inn Express with free breakfast and a 24/7 shuttle.",
     "$$", 3.9, 4.5, "lobby", "G"),
    ("hotels", "Hyatt Place {anchor} Convention Center", "Hotel chain",
     "Hyatt Place adjacent to the convention center with a 24-hour gym and an open-kitchen breakfast.",
     "$$$", 4.1, 4.7, "lobby", "G"),
    ("hotels", "Hampton Inn {anchor} Midtown", "Hotel chain",
     "Hampton Inn in midtown with a hot breakfast bar and a saltwater indoor pool.",
     "$$", 4.0, 4.6, "lobby", "G"),
    ("hotels", "Best Western Plus {anchor}", "Hotel chain",
     "Best Western Plus with a complimentary breakfast and an outdoor pool deck.",
     "$$", 3.8, 4.5, "lobby", "G"),
    ("hotels", "Courtyard by Marriott {anchor}", "Hotel chain",
     "Courtyard by Marriott with The Bistro service, ergonomic workspaces, and an indoor pool.",
     "$$$", 4.0, 4.7, "lobby", "G"),
    ("hotels", "Residence Inn {anchor}", "Extended stay hotel",
     "Extended-stay Residence Inn with full kitchens, weekday evening receptions, and grocery service.",
     "$$$", 4.2, 4.7, "lobby", "G"),
    ("hotels", "{anchor} Boutique Inn", "Boutique hotel",
     "Independent boutique hotel with 22 individually designed rooms and a cocktail lounge.",
     "$$$", 4.4, 4.9, "lobby", "G"),
    ("hotels", "{anchor} Hostel & Capsule", "Hostel",
     "Modern hostel with capsule pods, female-only dorm floors, and a rooftop common kitchen.",
     "$", 4.1, 4.6, "lobby", "G"),

    # ---- Coffee chains for SEO chain rail ----
    ("coffee-shops", "Starbucks — {anchor} Square", "Coffee chain",
     "Starbucks with a mobile-order pickup shelf, cold-foam menu, and outdoor patio.",
     "$", 3.9, 4.5, "", ""),
    ("coffee-shops", "Tim Hortons — {anchor} Plaza", "Coffee chain",
     "Tim Hortons with Timbits, drive-thru, and a 5am open for early commuters.",
     "$", 3.8, 4.4, "", ""),
    ("coffee-shops", "Costa Coffee — {anchor}", "Coffee chain",
     "Costa Coffee with flat whites, sandwich case, and a quiet study mezzanine.",
     "$$", 4.0, 4.5, "", ""),
    ("coffee-shops", "Philz Coffee — {anchor}", "Coffee chain",
     "Philz Coffee with one-cup pour-overs and customized cream-and-sugar prep.",
     "$$", 4.3, 4.8, "", ""),
    ("coffee-shops", "{anchor} Espresso Library", "Specialty coffee",
     "Espresso bar with library-style benches, single-origin lineup, and a 4-tap nitro coffee.",
     "$$", 4.4, 4.9, "", ""),
    ("coffee-shops", "{anchor} Bookshop Cafe", "Bookshop cafe",
     "Cafe inside an independent bookshop; pours alongside curated staff-pick shelves.",
     "$$", 4.4, 4.9, "", ""),

    # ---- Supermarkets / convenience ----
    ("supermarkets", "Aldi {anchor}", "Discount grocery",
     "Discount grocery with private-label staples, a weekly Aldi Finds aisle, and quarter-cart returns.",
     "$", 4.3, 4.8, "", ""),
    ("supermarkets", "Sprouts {anchor}", "Natural grocery",
     "Natural grocery with bulk bins, vitamin counter, and a fresh-juice bar.",
     "$$", 4.2, 4.7, "", ""),
    ("supermarkets", "H Mart {anchor}", "Asian grocery",
     "Korean-American grocery with live seafood, banchan counter, and a food court mezzanine.",
     "$$", 4.5, 4.9, "", ""),
    ("supermarkets", "Patel Brothers {anchor}", "Indian grocery",
     "Indian grocery with spices in bulk, fresh paneer, and a frozen-snack chest freezer aisle.",
     "$$", 4.4, 4.9, "", ""),
    ("supermarkets", "{anchor} Co-op Market", "Co-op grocery",
     "Member-owned co-op grocery with local produce, bulk pantry, and a community board.",
     "$$", 4.3, 4.8, "", ""),
    ("supermarkets", "7-Eleven — {anchor}", "Convenience store",
     "24/7 convenience store with Slurpees, taquitos, ATM, and lottery counter.",
     "$", 3.6, 4.2, "", ""),

    # ---- Pharmacies ----
    ("pharmacies", "Rite Aid — {anchor}", "Pharmacy chain",
     "Rite Aid with prescription pickup, immunization clinic, and a thrifty wellness aisle.",
     "$$", 3.7, 4.3, "", ""),
    ("pharmacies", "Walgreens 24h — {anchor}", "Pharmacy chain",
     "24-hour Walgreens with drive-thru pharmacy and a photo printing kiosk.",
     "$$", 3.7, 4.3, "", ""),
    ("pharmacies", "{anchor} Specialty Compounder", "Compounding pharmacy",
     "Independent specialty compounder for hormone, dermatology, and veterinary preparations.",
     "$$$", 4.5, 4.9, "", ""),

    # ---- Health / dentists / vets ----
    ("dentists", "{anchor} Pediatric Dental", "Pediatric dentistry",
     "Pediatric dentistry with movie-screen exam rooms, prize chest, and Saturday hours.",
     "$$$", 4.6, 4.9, "", ""),
    ("dentists", "{anchor} Implant Center", "Dental implants",
     "Implant center with in-house CBCT imaging, sedation, and same-day temporary crowns.",
     "$$$", 4.5, 4.9, "", ""),
    ("veterinarians", "{anchor} Bird & Exotics Vet", "Exotic vet",
     "Avian and exotic vet hospital with specialized housing, x-ray, and emergency intake.",
     "$$$", 4.4, 4.9, "", ""),
    ("hospitals", "{anchor} Pediatric Walk-In", "Pediatric urgent care",
     "Pediatric walk-in clinic with kid-friendly exam rooms and weekend appointments.",
     "$$", 4.3, 4.8, "", ""),
    ("hospitals", "{anchor} Women's Health Clinic", "Women's health",
     "Women's health clinic offering OB-GYN, midwifery, lactation support, and mental-health intake.",
     "$$$", 4.4, 4.9, "", ""),
    ("health-beauty", "{anchor} Massage Therapy", "Massage spa",
     "Licensed massage therapy with deep tissue, sports recovery, and prenatal options.",
     "$$", 4.5, 4.9, "", ""),
    ("health-beauty", "{anchor} Nail Studio", "Nail salon",
     "Nail studio with non-toxic polish lineup, gel, and complimentary beverages.",
     "$$", 4.2, 4.7, "", ""),
    ("health-beauty", "{anchor} Barbershop", "Barbershop",
     "Old-school barbershop with hot-towel shaves, beard trims, and walk-in service.",
     "$$", 4.4, 4.9, "", ""),

    # ---- Fitness ----
    ("fitness", "{anchor} Boxing Club", "Boxing gym",
     "Boxing club with heavy-bag rotation, sparring nights, and beginner-friendly footwork.",
     "$$$", 4.3, 4.8, "", ""),
    ("fitness", "{anchor} Spin Studio", "Spin studio",
     "Boutique spin studio with rhythm rides, themed playlists, and shower facilities.",
     "$$$", 4.4, 4.9, "", ""),
    ("fitness", "{anchor} Lap Pool & Aqua Fit", "Aquatic center",
     "Lap pool with daily aqua-fit classes, sauna, and family swim hours.",
     "$$", 4.3, 4.8, "", ""),
    ("fitness", "{anchor} Martial Arts Academy", "Martial arts",
     "Martial arts academy teaching BJJ, muay thai, and kids classes after school.",
     "$$$", 4.5, 4.9, "", ""),

    # ---- Shopping ----
    ("shopping", "{anchor} Outlet Mall", "Outlet mall",
     "Open-air outlet mall with 80 brand-name stores, food court, and a kids carousel.",
     "$$", 4.0, 4.6, "concourse", "1"),
    ("shopping", "{anchor} Antique Market", "Antique market",
     "Indoor antique market with 60 dealer booths, weekend-only and a vintage cafe.",
     "$$", 4.3, 4.8, "", ""),
    ("shopping", "{anchor} Farmer's Market Pavilion", "Farmers market",
     "Saturday farmers market pavilion with 90 vendors, live music, and a cooking demo tent.",
     "$$", 4.6, 4.9, "", ""),
    ("shopping", "{anchor} Toy & Hobby Shop", "Toy store",
     "Family-run toy and hobby shop with model trains, kits, board games, and gift wrap.",
     "$$", 4.4, 4.9, "", ""),
    ("shopping", "{anchor} Bicycle Workshop", "Bicycle shop",
     "Bicycle shop and workshop with tune-ups, e-bike sales, and group ride starts.",
     "$$", 4.5, 4.9, "", ""),
    ("shopping", "Apple Store — {anchor}", "Electronics chain",
     "Apple Store with Today at Apple workshops, Genius Bar appointments, and trade-in.",
     "$$$", 4.4, 4.9, "concourse", "1"),
    ("shopping", "Best Buy — {anchor}", "Electronics chain",
     "Best Buy with Geek Squad service, appliance showroom, and an open-box clearance corner.",
     "$$", 3.9, 4.5, "", ""),
    ("shopping", "IKEA {anchor} Showroom", "Furniture store",
     "IKEA showroom with marketplace, Smaland childcare, and Swedish meatballs at the cafe.",
     "$$", 4.3, 4.8, "concourse", "1"),

    # ---- Museums ----
    ("museums", "{anchor} Science Center", "Science museum",
     "Interactive science center with planetarium, IMAX dome, and a maker workshop floor.",
     "$$", 4.5, 4.9, "concourse", "1"),
    ("museums", "{anchor} Children's Museum", "Children's museum",
     "Hands-on children's museum with role-play stages, a water table, and toddler-only hours.",
     "$$", 4.6, 4.9, "concourse", "1"),
    ("museums", "{anchor} Maritime Museum", "Maritime museum",
     "Maritime museum on the waterfront with a historic schooner tour and lighthouse exhibits.",
     "$$", 4.4, 4.9, "concourse", "1"),
    ("museums", "{anchor} African American History", "History museum",
     "Museum of African American history with rotating exhibits, oral histories, and education center.",
     "$$", 4.6, 4.9, "concourse", "1"),
    ("museums", "{anchor} Asian Art Gallery", "Art gallery",
     "Gallery of Asian art spanning Tang ceramics, Edo woodblocks, and contemporary South Asian artists.",
     "$$", 4.5, 4.9, "concourse", "1"),

    # ---- Parks ----
    ("parks", "{anchor} River Greenway", "Park",
     "Multi-use river greenway with paved trail, kayak launch, and wildflower meadow.",
     "Free", 4.5, 4.9, "", ""),
    ("parks", "{anchor} Skate Park", "Skate park",
     "Concrete skate park with bowls, half-pipes, and beginner street section.",
     "Free", 4.3, 4.8, "", ""),
    ("parks", "{anchor} Community Garden", "Community garden",
     "Volunteer-run community garden with raised beds, demonstration plots, and Saturday workdays.",
     "Free", 4.4, 4.9, "", ""),
    ("parks", "{anchor} Disc Golf Course", "Disc golf",
     "18-hole disc golf course through wooded terrain with cement tee pads and tournament alts.",
     "Free", 4.3, 4.8, "", ""),
    ("dog-parks", "{anchor} Off-Leash Dog Run", "Dog park",
     "Off-leash dog run with separate small-dog area, water fountains, and shade canopies.",
     "Free", 4.4, 4.9, "", ""),

    # ---- Beaches ----
    ("beaches", "{anchor} Public Beach", "Public beach",
     "Lifeguarded public beach with restrooms, snack bar, and a boardwalk concession row.",
     "Free", 4.3, 4.8, "", ""),
    ("beaches", "{anchor} Surfing Cove", "Surf beach",
     "Surfing cove with consistent left break, beginner zone, and a board-rental shack.",
     "Free", 4.5, 4.9, "", ""),

    # ---- Entertainment ----
    ("entertainment", "{anchor} Comedy Club", "Comedy club",
     "Comedy club with weeknight open-mics and a Saturday headliner lineup; 2-item minimum.",
     "$$", 4.3, 4.8, "", ""),
    ("entertainment", "{anchor} Jazz Lounge", "Jazz club",
     "Jazz lounge with house trio, late-night jam session, and a $10 student cover.",
     "$$$", 4.5, 4.9, "", ""),
    ("entertainment", "{anchor} Indie Movie House", "Movie theater",
     "Three-screen indie movie house with art-house lineup, second-run double features, and a bar.",
     "$$", 4.5, 4.9, "", ""),
    ("entertainment", "{anchor} Karaoke Box", "Karaoke",
     "Private-room karaoke with 25,000-song catalog, soju menu, and 2am late-night happy hour.",
     "$$", 4.2, 4.7, "", ""),
    ("entertainment", "{anchor} Escape Room Lab", "Escape room",
     "Escape room lab with 6 rooms across difficulty tiers, team scheduling, and birthday packages.",
     "$$", 4.5, 4.9, "", ""),

    # ---- Services ----
    ("services", "{anchor} Notary Public", "Notary",
     "Walk-in notary public with mobile service, apostille help, and weekend hours.",
     "$", 4.5, 4.9, "", ""),
    ("services", "{anchor} UPS Store", "Shipping store",
     "UPS Store with packaging, mailbox rental, printing, and Amazon returns.",
     "$$", 4.2, 4.7, "", ""),
    ("services", "{anchor} FedEx Office", "Shipping store",
     "FedEx Office with printing, packaging, ship-and-print, and same-day pickup boxes.",
     "$$", 4.1, 4.6, "", ""),
    ("services", "{anchor} Dry Cleaner", "Dry cleaner",
     "Family-run dry cleaner with same-day service, alterations, and pickup-delivery routes.",
     "$$", 4.3, 4.8, "", ""),
    ("services", "{anchor} Bank Branch", "Bank branch",
     "Full-service bank branch with safe deposit, notary, mortgage counselors, and ATM lobby.",
     "$$", 4.0, 4.5, "", ""),

    # ---- Religious sites ----
    ("religious", "{anchor} Cathedral", "Cathedral",
     "Historic cathedral with daily mass, choral vespers Sundays, and free guided tours.",
     "Free", 4.6, 4.9, "", ""),
    ("religious", "{anchor} Buddhist Temple", "Buddhist temple",
     "Buddhist temple with meditation sits, Sunday dharma talk, and a vegetarian Saturday lunch.",
     "Free", 4.6, 4.9, "", ""),
    ("religious", "{anchor} Mosque & Community Center", "Mosque",
     "Mosque and community center with daily prayers, Friday khutba, and weekend schooling.",
     "Free", 4.7, 4.9, "", ""),

    # ---- Education / libraries / schools ----
    ("libraries", "{anchor} Branch Library", "Public library",
     "Public library branch with kids storytime, maker lab, and 24/7 hold pickup lockers.",
     "Free", 4.6, 4.9, "concourse", "1"),
    ("libraries", "{anchor} Law Library", "Law library",
     "Law library with case-reporter shelves, study carrels, and reference librarians.",
     "Free", 4.4, 4.9, "concourse", "1"),
    ("schools", "{anchor} Charter Elementary", "Charter school",
     "Charter elementary with project-based learning, art studio, and STEM enrichment.",
     "$$$", 4.3, 4.8, "", ""),
    ("schools", "{anchor} Community College", "Community college",
     "Community college with associate degree programs, evening classes, and a small business center.",
     "$$", 4.2, 4.7, "", ""),

    # ---- Public restrooms / playgrounds ----
    ("public-restrooms", "{anchor} Park Public Restroom", "Public restroom",
     "Public restroom adjacent to the park entry with accessible stalls and a baby-change station.",
     "Free", 3.6, 4.2, "", ""),
    ("playgrounds", "{anchor} Adventure Playground", "Playground",
     "Adventure playground with climbing structure, splash pad, and shaded picnic tables.",
     "Free", 4.5, 4.9, "", ""),

    # ---- Transit-adjacent ----
    ("transit", "{anchor} Park-and-Ride Lot", "Park and ride",
     "Park-and-ride lot at the rail terminus with bus connections and overnight parking permitted.",
     "$", 3.9, 4.4, "", ""),
    ("bus-stops", "{anchor} Express Bus Stop", "Bus stop",
     "Sheltered express bus stop with real-time arrival board, USB ports, and step-free access.",
     "Free", 3.8, 4.3, "", ""),

    # ---- Indoor airport shops ----
    ("indoor-airport-shops", "Hudson News — {anchor} Terminal", "Travel retail",
     "Hudson News terminal shop with magazines, sundries, and a 5-minute grab-and-go cooler.",
     "$$", 3.7, 4.3, "concourse", "1"),
    ("indoor-airport-shops", "TUMI — {anchor} Concourse", "Travel retail",
     "TUMI concourse shop with carry-on, garment bags, and last-minute travel essentials.",
     "$$$$", 4.2, 4.7, "concourse", "1"),
    ("indoor-airport-shops", "Brookstone — {anchor} Gates", "Travel retail",
     "Brookstone airport store with travel gadgets, neck pillows, and noise-canceling headphones.",
     "$$$", 4.0, 4.5, "concourse", "1"),

    # ---- Indoor mall shops ----
    ("indoor-mall-shops", "Sephora — {anchor} Mall", "Beauty store",
     "Sephora at the mall with skin-scan station, fragrance bar, and beauty studio appointments.",
     "$$$", 4.3, 4.8, "concourse", "1"),
    ("indoor-mall-shops", "Lululemon — {anchor} Mall", "Athleisure",
     "Lululemon mall location with hemming, run-club bulletin board, and weekend yoga.",
     "$$$", 4.2, 4.7, "concourse", "1"),
    ("indoor-mall-shops", "Williams Sonoma — {anchor} Mall", "Cookware",
     "Williams Sonoma cookware shop with chef demos, knife sharpening, and gift registries.",
     "$$$$", 4.3, 4.8, "concourse", "1"),

    # ---- Parking / EV ----
    ("parking", "{anchor} Stadium Parking Deck", "Parking deck",
     "Multi-level stadium parking deck with event surge pricing and a tailgate-friendly tier.",
     "$", 3.7, 4.3, "parking-deck", "P1"),
    ("parking", "{anchor} City Hall Garage", "Parking garage",
     "Public garage attached to city hall with hourly rates and 24/7 access.",
     "$$", 3.8, 4.4, "parking-deck", "P1"),
    ("ev-charging", "Tesla Destination Charger — {anchor}", "EV charging",
     "Tesla Destination Charger with two stalls and a 24/7 lounge-adjacent location.",
     "$", 4.4, 4.9, "", ""),
    ("ev-charging", "Wallbox Public Network — {anchor}", "EV charging",
     "Wallbox Public Network site with four 60kW CCS stalls and a covered canopy.",
     "$", 4.2, 4.7, "", ""),
    ("ev-charging", "ChargePoint — {anchor}", "EV charging",
     "ChargePoint level-2 lot with twelve stalls, app payment, and a 30-minute idle fee.",
     "$", 4.3, 4.8, "", ""),

    # ---- Gas stations ----
    ("gas-stations", "Shell {anchor} — Gas & Convenience", "Gas station",
     "Shell gas station with c-store, fresh-brewed coffee, and a 24/7 car wash bay.",
     "$$", 3.8, 4.4, "", ""),
    ("gas-stations", "BP {anchor} — Truck Plaza", "Truck plaza",
     "BP truck-plaza with diesel lanes, driver lounge, and a sit-down breakfast counter.",
     "$$", 3.7, 4.3, "", ""),

    # ---- Post offices ----
    ("post-offices", "USPS — {anchor}", "Post office",
     "USPS branch with passport intake, PO boxes, and Saturday morning hours.",
     "$", 3.6, 4.2, "", ""),

    # ---- Police / fire ----
    ("police-stations", "{anchor} Precinct Station", "Police station",
     "Neighborhood police precinct with community-affairs office and a fingerprint kiosk.",
     "Free", 3.8, 4.4, "", ""),
    ("fire-stations", "{anchor} Fire Engine Co", "Fire station",
     "Fire engine company with public open-house days and a community CPR classroom.",
     "Free", 4.5, 4.9, "", ""),

    # ---- Car rental ----
    ("car-rental", "Enterprise Rent-A-Car — {anchor}", "Car rental",
     "Enterprise neighborhood car rental with free pickup and an SUV-and-truck row.",
     "$$$", 4.0, 4.5, "", ""),
    ("car-rental", "Avis — {anchor} Airport", "Car rental",
     "Avis airport rental counter with Preferred fast-lane, EV rentals, and skip-the-counter check-in.",
     "$$$", 3.9, 4.5, "", ""),
    ("car-rental", "Budget — {anchor}", "Car rental",
     "Budget rental branch with weekly discounts, weekend deals, and a Sunday return drop box.",
     "$$", 3.7, 4.3, "", ""),

    # ---- Campus buildings ----
    ("campus-buildings", "{anchor} Engineering Hall", "Academic building",
     "University engineering hall with lecture theaters, machine shop, and a maker mezzanine.",
     "Free", 4.3, 4.8, "wing", "1"),
    ("campus-buildings", "{anchor} Business School", "Academic building",
     "Business school building with case-method classrooms, an MBA lounge, and a career office.",
     "Free", 4.4, 4.9, "wing", "1"),

    # ---- Tail: ATMs ----
    ("atms", "Chase ATM — {anchor} Square", "Bank ATM",
     "Chase Bank vestibule ATM with check deposit, cash withdrawal, and 24/7 access.",
     "Free", 3.7, 4.3, "", ""),
    ("atms", "Wells Fargo ATM — {anchor}", "Bank ATM",
     "Wells Fargo street ATM with envelope-free deposit and en-screen Spanish menus.",
     "Free", 3.6, 4.3, "", ""),
    ("atms", "Bank of America ATM — {anchor}", "Bank ATM",
     "Bank of America ATM with cardless access via the mobile app and check deposit.",
     "Free", 3.7, 4.3, "", ""),
]


def expand_places_r7(db, Place, Category, City):
    """R7 expansion: SEO/locale density.

    Adds another ~110k venue rows by re-running the same per-city shuffle
    pattern as R6 but against `_R7_TEMPLATES`.  Gated on Place count
    >= 380000 so the function is a no-op once the seed has been built once.
    """
    if Place.query.count() >= 380000:
        return

    cat_by_slug = {c.slug: c for c in Category.query.all()}
    cities = City.query.order_by(City.id).all()
    if not cities:
        return

    donor_pool = []
    for p in (Place.query
              .filter(Place.hero_image.like("/static/images/places/%"))
              .order_by(Place.id).limit(80).all()):
        try:
            photos = json.loads(p.photos_json or "[]")
        except Exception:
            photos = []
        if p.hero_image:
            donor_pool.append((p.hero_image, photos or [p.hero_image]))
    if not donor_pool:
        donor_pool = [("/static/images/heroes/eiffel-tower.jpg",
                       ["/static/images/heroes/eiffel-tower.jpg"])]

    _CHAINS = (
        "Starbucks Reserve", "Starbucks", "Tim Hortons", "Costa Coffee",
        "Philz Coffee", "Blue Bottle Coffee", "Peet's Coffee", "Dunkin'",
        "Whole Foods Market", "Trader Joe's", "Costco Wholesale", "Safeway",
        "Aldi", "Sprouts", "H Mart", "Patel Brothers", "7-Eleven",
        "CVS Pharmacy", "Walgreens", "Walgreens 24h", "Rite Aid",
        "Hertz", "Enterprise Rent-A-Car", "Avis", "Budget", "Turo",
        "Marriott", "Hilton Garden Inn", "Holiday Inn Express", "Hyatt Place",
        "Hampton Inn", "Best Western Plus", "Courtyard by Marriott",
        "Residence Inn",
        "Tesla Destination Charger", "Wallbox Public Network", "ChargePoint",
        "Shell", "BP", "USPS", "UPS Store", "FedEx Office",
        "Apple Store", "Best Buy", "IKEA", "Sephora", "Lululemon",
        "Williams Sonoma", "Hudson News", "TUMI", "Brookstone",
        "Chase ATM", "Wells Fargo ATM", "Bank of America ATM",
    )

    added = 0
    for city in cities:
        anchor = city.display_name.split(",")[0].split(" ")[0]
        templates = list(enumerate(_R7_TEMPLATES))
        for i in range(len(templates) - 1, 0, -1):
            j = int.from_bytes(
                hashlib.md5(f"r7sh:{city.slug}:{i}".encode()).digest()[:4],
                "big") % (i + 1)
            templates[i], templates[j] = templates[j], templates[i]

        for idx, tpl in templates:
            (cat_slug, pattern, subtitle, desc, price, rlo, rhi,
             indoor_zone, floor_num) = tpl
            cat = cat_by_slug.get(cat_slug)
            if not cat:
                continue
            slug = f"r7-{city.slug}-{cat_slug}-{idx:03d}"
            if Place.query.filter_by(slug=slug).first():
                continue

            name = pattern.format(anchor=anchor)
            local_seed = _seed_int_hex(slug, "r7loc")
            hero, gallery = donor_pool[local_seed % len(donor_pool)]
            lat = city.lat + ((local_seed % 800) - 400) / 10000.0
            lng = city.lng + (((local_seed // 800) % 1000) - 500) / 10000.0
            rating = round(rlo + (local_seed % 100) / 100.0 * (rhi - rlo), 1)
            review_count = 12 + (local_seed % 3800)

            chain = ""
            for brand in _CHAINS:
                if name.startswith(brand):
                    chain = brand
                    break

            hours_pick = (local_seed >> 4) % 6
            hours_options = [
                "Mon-Sun: 9:00 AM - 9:00 PM",
                "Mon-Sat: 10:00 AM - 8:00 PM, Sun 11:00 AM - 6:00 PM",
                "Tue-Sun: 11:00 AM - 10:00 PM, Closed Mon",
                "Open 24 hours",
                "Mon-Fri: 7:00 AM - 7:00 PM, Weekends 8:00 AM - 5:00 PM",
                "Mon-Sun: 6:00 AM - 10:00 PM",
            ]
            tags = [cat_slug, anchor.lower(), city.country.lower()]
            if indoor_zone:
                tags.append(indoor_zone)
            if chain:
                tags.append(chain.lower().replace(" ", "-"))

            db.session.add(Place(
                slug=slug, name=name, category_id=cat.id, city_id=city.id,
                subtitle=subtitle,
                description=desc,
                address=f"{15 + (local_seed % 985)} {['Oak','Pine','Elm','Ash','Cherry','Magnolia','Willow','Aspen'][local_seed % 8]} Ave, {city.display_name}",
                phone=f"+{1 + (local_seed % 9)} {200 + (local_seed % 800)} {1000 + (local_seed % 9000)}",
                hours=hours_options[hours_pick],
                website=google_maps_search_url(name, city.display_name),
                rating=rating,
                review_count=review_count,
                price_level=price,
                hero_image=hero,
                photos_json=json.dumps(gallery[:5]),
                lat=lat, lng=lng,
                tags_json=json.dumps(tags),
                subcategory=subtitle,
                chain_brand=chain,
                is_24h=(hours_pick == 3),
                is_popular=(rating >= 4.6 and (local_seed % 5) == 0),
                has_parking_lot=(cat_slug in ("supermarkets", "hotels",
                                              "shopping", "fitness",
                                              "hospitals", "schools",
                                              "religious", "entertainment",
                                              "car-rental", "parking")
                                 or (local_seed % 3) == 0),
                ev_charging=(cat_slug == "ev-charging"
                              or (cat_slug == "hotels" and "Marriott" in name)
                              or (cat_slug == "supermarkets" and "Whole Foods" in name)),
                bicycle_parking=(local_seed % 2) == 0,
                indoor_zone_type=indoor_zone,
                floor_number=floor_num,
                parking_lot_capacity=(60 + (local_seed % 1600)) if cat_slug == "parking" else 0,
                delivery_available=(cat_slug == "restaurants" and (local_seed % 2) == 0),
                dine_in=(cat_slug in ("restaurants", "coffee-shops")),
                takeout=(cat_slug in ("restaurants", "coffee-shops",
                                       "supermarkets")),
                accepts_reservations=(cat_slug == "restaurants" and (local_seed % 3) == 0),
                serves_breakfast=(cat_slug in ("restaurants", "coffee-shops")
                                   and (local_seed % 2) == 0),
                serves_lunch=(cat_slug == "restaurants"),
                serves_dinner=(cat_slug == "restaurants"),
                serves_alcohol=(cat_slug == "restaurants" and (local_seed % 3) == 0),
                serves_vegetarian=(cat_slug == "restaurants" and (local_seed % 2) == 0),
            ))
            added += 1
            if added % 1500 == 0:
                db.session.commit()
    db.session.commit()
    print(f"expand_places_r7: added {added} R7 places (total {Place.query.count()})")

# Append more R7 templates so total >= 135 → 135 × 812 ≈ 110k rows.
_R7_TEMPLATES.extend([
    ("restaurants", "{anchor} Tapas & Pintxos Bar", "Spanish tapas",
     "Counter-style Basque pintxos bar with sherry pours, Iberico ham, and small plates till midnight.",
     "$$$", 4.4, 4.9, "", ""),
    ("restaurants", "{anchor} Lebanese Kitchen", "Lebanese",
     "Family-run Lebanese kitchen with shawarma platters, kibbeh, and house-baked man'oushe.",
     "$$", 4.4, 4.9, "", ""),
    ("restaurants", "{anchor} Cajun Po-Boy Shop", "Cajun",
     "Po-boy shop with shrimp, oyster, and roast-beef debris sandwiches on Leidenheimer bread.",
     "$", 4.3, 4.8, "", ""),
    ("restaurants", "{anchor} Argentine Steakhouse", "Argentine",
     "Argentine steakhouse with parrilla, blood-sausage entradas, and a Malbec-forward list.",
     "$$$", 4.4, 4.9, "", ""),
    ("restaurants", "{anchor} Vegetarian Thali House", "Indian vegetarian",
     "South Indian thali house with unlimited refills, lassi, and a kid-friendly mild-spice option.",
     "$$", 4.4, 4.9, "", ""),
    ("restaurants", "{anchor} Cuban Sandwich Cafe", "Cuban",
     "Cuban sandwich cafe with media noche, ropa vieja platters, and Cuban-coffee shots.",
     "$", 4.3, 4.8, "", ""),
    ("restaurants", "{anchor} Belgian Frites & Mussels", "Belgian",
     "Belgian frites and mussels brasserie with 30 sauces, monks-brewed beer, and waffles for dessert.",
     "$$", 4.3, 4.8, "", ""),
    ("coffee-shops", "Caribou Coffee — {anchor}", "Coffee chain",
     "Caribou Coffee with cabin-lodge styling, mocha lineup, and fireside seating.",
     "$", 4.0, 4.5, "", ""),
    ("coffee-shops", "Stumptown Coffee — {anchor}", "Specialty coffee",
     "Stumptown Coffee branch with Hair Bender espresso, cold brew on draft, and merch shelves.",
     "$$", 4.4, 4.9, "", ""),
    ("supermarkets", "Lidl {anchor}", "Discount grocery",
     "Lidl discount grocery with weekly themed aisles, bakery counter, and a Lidl Plus app aisle.",
     "$", 4.2, 4.7, "", ""),
    ("supermarkets", "Kroger {anchor}", "Grocery chain",
     "Kroger grocery with ClickList pickup, pharmacy, fuel center, and a Murray's cheese counter.",
     "$$", 3.9, 4.5, "", ""),
    ("supermarkets", "Publix {anchor}", "Grocery chain",
     "Publix grocery with sub-sandwich counter, in-house bakery, and weekly BOGO promotions.",
     "$$", 4.4, 4.9, "", ""),
    ("pharmacies", "{anchor} Cannabis Dispensary", "Dispensary",
     "Licensed cannabis dispensary with edibles, flower, and budtender consultations.",
     "$$$", 4.4, 4.9, "", ""),
    ("shopping", "Target — {anchor}", "Department store",
     "Target with grocery aisle, Starbucks, electronics counter, and self-checkout banks.",
     "$$", 4.2, 4.7, "concourse", "1"),
    ("shopping", "Walmart Supercenter — {anchor}", "Supercenter",
     "Walmart Supercenter with grocery, auto-care center, pharmacy, and a 24/7 receipt-check exit.",
     "$", 4.0, 4.5, "concourse", "1"),
    ("shopping", "Home Depot — {anchor}", "Home improvement",
     "Home Depot with lumber yard, tool rental, paint mixing, and a Saturday kids' workshop.",
     "$$", 4.1, 4.6, "concourse", "1"),
    ("shopping", "Lowe's — {anchor}", "Home improvement",
     "Lowe's home improvement with garden center, appliance showroom, and pro-desk.",
     "$$", 4.0, 4.5, "concourse", "1"),
    ("fitness", "Planet Fitness — {anchor}", "Gym chain",
     "Planet Fitness with judgement-free zone, hydromassage chairs, and 24/7 access.",
     "$", 4.0, 4.5, "", ""),
    ("fitness", "Equinox — {anchor}", "Premium gym",
     "Equinox premium gym with eucalyptus steam, group fitness, and personal training.",
     "$$$$", 4.5, 4.9, "", ""),
    ("fitness", "Orangetheory — {anchor}", "Boutique fitness",
     "Orangetheory studio with heart-rate zones, 60-minute workouts, and personal-trainer led groups.",
     "$$$", 4.5, 4.9, "", ""),
    ("entertainment", "AMC Theatres — {anchor}", "Movie theater",
     "AMC Theatres multiplex with recliner seats, Dolby Cinema, and an MX4D motion auditorium.",
     "$$", 4.2, 4.7, "concourse", "1"),
    ("entertainment", "Regal Cinemas — {anchor}", "Movie theater",
     "Regal Cinemas multiplex with RPX premium auditorium, dine-in seats, and a kids weekend matinee.",
     "$$", 4.1, 4.6, "concourse", "1"),
    ("entertainment", "{anchor} Live Music Venue", "Music venue",
     "Independent live-music venue with nightly bookings, 600-seat main floor, and a green-room basement.",
     "$$", 4.5, 4.9, "", ""),
    ("museums", "{anchor} Modern Art Museum", "Art museum",
     "Modern art museum with rotating special exhibits, sculpture garden, and a contemporary-photo wing.",
     "$$", 4.5, 4.9, "concourse", "1"),
    ("museums", "{anchor} Natural History Museum", "Natural history",
     "Natural history museum with dinosaur hall, mineral wing, and a planetarium add-on.",
     "$$", 4.6, 4.9, "concourse", "1"),
])


# ============================================================================
#  R8 — Polish round 8: expand catalog to 550k+ + introduce new chains and
#  service verticals so the developer-API/observability/keyboard-shortcut
#  task themes have plenty of underlying rows to filter against.
#  Slug prefix `r8-` keeps R8 rows distinct from R5/R6/R7.
# ============================================================================
_R8_TEMPLATES = [
    # ---- More restaurants / cuisines ----
    ("restaurants", "{anchor} Korean Corn Dog Shop", "Korean snack",
     "Korean corn dog shop with mozzarella + potato cubes, sugar-coat option, and matcha milk on tap.",
     "$", 4.3, 4.8, "", ""),
    ("restaurants", "{anchor} Hawaiian Poke Bowl", "Hawaiian",
     "Build-your-own poke bowl with ahi tuna, salmon, spicy mayo, and seaweed salad.",
     "$$", 4.3, 4.8, "", ""),
    ("restaurants", "{anchor} Georgian Khinkali House", "Georgian",
     "Georgian khinkali dumplings, khachapuri cheese-boats, and qvevri-aged wine.",
     "$$", 4.5, 4.9, "", ""),
    ("restaurants", "{anchor} Filipino Kamayan Hall", "Filipino",
     "Filipino kamayan feast served banana-leaf style with lechon, sisig, and ube-halaya.",
     "$$", 4.4, 4.9, "", ""),
    ("restaurants", "{anchor} Nigerian Suya Grill", "Nigerian",
     "Nigerian suya grill with skewered beef, jollof rice, plantain, and zobo drink.",
     "$$", 4.3, 4.8, "", ""),
    ("restaurants", "{anchor} Moroccan Tagine House", "Moroccan",
     "Moroccan tagine house with lamb-prune, chicken-preserved-lemon, and mint-tea service.",
     "$$$", 4.4, 4.9, "", ""),
    ("restaurants", "{anchor} Israeli Hummus Bar", "Israeli",
     "Israeli hummus bar with daily fresh tahini, sabich pita, and shakshuka brunch.",
     "$$", 4.4, 4.9, "", ""),
    ("restaurants", "{anchor} Brazilian Churrascaria", "Brazilian",
     "Brazilian churrascaria with rodizio meat-on-skewers, caipirinha bar, and a 40-item salad island.",
     "$$$", 4.4, 4.9, "", ""),
    ("restaurants", "{anchor} Colombian Arepa Cafe", "Colombian",
     "Colombian arepa cafe with stuffed corn cakes, bandeja paisa, and tinto coffee.",
     "$", 4.3, 4.8, "", ""),
    ("restaurants", "{anchor} Malaysian Roti Shop", "Malaysian",
     "Malaysian roti shop with roti canai, nasi lemak, char kway teow, and pandan kaya toast.",
     "$$", 4.4, 4.9, "", ""),
    ("restaurants", "{anchor} Singaporean Hawker Hall", "Singaporean",
     "Singaporean hawker hall with chili crab, Hainanese chicken rice, laksa, and kaya toast.",
     "$$", 4.5, 4.9, "concourse", "1"),
    ("restaurants", "{anchor} Sichuan Noodle Bar", "Sichuan",
     "Sichuan noodle bar with dan-dan noodles, mapo tofu, and a ma-la lamb skewer counter.",
     "$$", 4.4, 4.9, "", ""),
    ("restaurants", "{anchor} Tibetan Momo House", "Tibetan",
     "Tibetan momo house with steamed/pan-fried momos, thukpa noodle soup, and butter tea.",
     "$", 4.4, 4.9, "", ""),
    ("restaurants", "{anchor} Yemeni Coffee & Mandi", "Yemeni",
     "Yemeni cafe with cardamom coffee, lamb mandi rice plates, and saltah stew on weekends.",
     "$$", 4.5, 4.9, "", ""),
    ("restaurants", "{anchor} Russian Pelmeni Hall", "Russian",
     "Russian pelmeni hall with hand-pinched dumplings, borscht, beef stroganoff, and kvass.",
     "$$", 4.2, 4.7, "", ""),
    ("restaurants", "{anchor} Salvadoran Pupusa Stand", "Salvadoran",
     "Salvadoran pupusa stand with revueltas, curtido slaw, and horchata de morro.",
     "$", 4.3, 4.8, "", ""),
    ("restaurants", "{anchor} Mongolian BBQ Grill", "Mongolian",
     "Mongolian-style BBQ grill with build-your-own bowl, dumplings, and milk-tea pairings.",
     "$$", 4.1, 4.6, "", ""),
    ("restaurants", "{anchor} Burmese Tea Leaf Salad", "Burmese",
     "Burmese kitchen with tea-leaf salad, mohinga fish noodle soup, and falooda.",
     "$$", 4.4, 4.9, "", ""),
    # ---- Chains: coffee + bubble tea + dessert ----
    ("coffee-shops", "Tim Hortons — {anchor}", "Coffee chain",
     "Tim Hortons coffee chain with double-double, Timbits, and breakfast wraps.",
     "$", 4.0, 4.5, "", ""),
    ("coffee-shops", "Gong cha — {anchor}", "Bubble tea",
     "Gong cha bubble tea chain with brown sugar milk tea, salted-cream brews, and 20 toppings.",
     "$", 4.3, 4.8, "", ""),
    ("coffee-shops", "Kung Fu Tea — {anchor}", "Bubble tea",
     "Kung Fu Tea chain with punch family, classic milk tea, and a free shaker giveaway weekly.",
     "$", 4.2, 4.7, "", ""),
    ("coffee-shops", "Boba Guys — {anchor}", "Bubble tea",
     "Boba Guys with hojicha lattes, strawberry matcha, and house-made tapioca.",
     "$$", 4.4, 4.9, "", ""),
    ("coffee-shops", "Tea Station — {anchor}", "Tea house",
     "Pan-Asian tea house with snow ice, shaved-snow desserts, and Taiwanese small plates.",
     "$$", 4.2, 4.7, "", ""),
    ("coffee-shops", "85C Bakery Cafe — {anchor}", "Bakery cafe",
     "85C bakery cafe with sea-salt coffee, pineapple buns, and mochi bread.",
     "$", 4.3, 4.8, "", ""),
    ("coffee-shops", "Insomnia Cookies — {anchor}", "Late-night dessert",
     "Insomnia Cookies open till 3 AM with warm cookies, brownies, and milk on tap.",
     "$", 4.3, 4.8, "", ""),
    ("coffee-shops", "Crumbl Cookies — {anchor}", "Cookie chain",
     "Crumbl Cookies with a rotating weekly menu of 6 flavors and a pink-box display.",
     "$", 4.4, 4.9, "", ""),
    ("coffee-shops", "Jeni's Splendid Ice Creams — {anchor}", "Ice cream",
     "Jeni's Splendid Ice Creams with seasonal pints, sundaes, and grass-fed milk base.",
     "$$", 4.5, 4.9, "", ""),
    ("coffee-shops", "Pinkberry — {anchor}", "Frozen yogurt",
     "Pinkberry frozen yogurt with tart original, granola toppings, and a fresh-fruit bar.",
     "$", 4.0, 4.5, "", ""),
    # ---- Grocery / convenience extensions ----
    ("supermarkets", "Wegmans — {anchor}", "Grocery chain",
     "Wegmans grocery with hot bar, sushi counter, prepared meals, and a wine alcove.",
     "$$", 4.6, 4.9, "concourse", "1"),
    ("supermarkets", "ALDI Express — {anchor}", "Discount grocery",
     "ALDI Express compact format with weekly Aisle of Shame, cart-deposit system, and bring-your-own bags.",
     "$", 4.2, 4.7, "", ""),
    ("supermarkets", "Mitsuwa Marketplace — {anchor}", "Japanese grocery",
     "Mitsuwa Japanese marketplace with imported sake, Hokkaido produce, and a hot-food court.",
     "$$", 4.6, 4.9, "concourse", "1"),
    ("supermarkets", "99 Ranch Market — {anchor}", "Asian grocery",
     "99 Ranch Market with live seafood tanks, frozen dim sum, and bakery counter.",
     "$$", 4.4, 4.9, "concourse", "1"),
    ("supermarkets", "Sprouts Farmers Market — {anchor}", "Natural grocery",
     "Sprouts Farmers Market with bulk bins, fresh produce focus, and a butcher counter.",
     "$$", 4.3, 4.8, "", ""),
    ("supermarkets", "Fresh Thyme — {anchor}", "Natural grocery",
     "Fresh Thyme Market with organic produce, bulk goods, and weekly Wednesday flash sales.",
     "$$", 4.2, 4.7, "", ""),
    ("supermarkets", "DashMart — {anchor}", "Dark store",
     "DashMart dark store for DoorDash delivery; pantry staples, snacks, and convenience essentials.",
     "$$", 4.0, 4.5, "", ""),
    ("supermarkets", "Gopuff — {anchor}", "Dark store",
     "Gopuff fulfillment center for 15-minute delivery of snacks, drinks, and household goods.",
     "$$", 3.9, 4.4, "", ""),
    # ---- Pharmacies + dispensaries + clinics ----
    ("pharmacies", "{anchor} 24-Hour Urgent Care", "Urgent care",
     "24-hour urgent care clinic with X-ray, lab, and walk-in appointments accepted.",
     "$$", 4.2, 4.7, "", ""),
    ("pharmacies", "{anchor} Optometrist", "Optometry clinic",
     "Optometry clinic with comprehensive eye exams, designer frames, and contact-lens fittings.",
     "$$", 4.4, 4.9, "", ""),
    ("pharmacies", "{anchor} Dental Group", "Dental clinic",
     "Family dental group with cleanings, whitening, and same-day crowns via CEREC.",
     "$$$", 4.4, 4.9, "", ""),
    ("pharmacies", "{anchor} Physical Therapy Center", "PT clinic",
     "Physical therapy center with orthopedic rehab, dry needling, and post-op programs.",
     "$$", 4.5, 4.9, "", ""),
    ("pharmacies", "MinuteClinic at CVS — {anchor}", "Walk-in clinic",
     "MinuteClinic walk-in clinic inside CVS with vaccines, sick visits, and TB tests.",
     "$$", 4.1, 4.6, "concourse", "1"),
    # ---- Lodging + coliving + hostels ----
    ("hotels", "Sonder — {anchor}", "Apartment hotel",
     "Sonder apartment-hotel with full kitchens, keyless entry, and 24/7 in-app concierge.",
     "$$$", 4.3, 4.8, "", ""),
    ("hotels", "citizenM — {anchor}", "Lifestyle hotel",
     "citizenM lifestyle hotel with compact rooms, MoodPad lighting controls, and rooftop bar.",
     "$$$", 4.5, 4.9, "", ""),
    ("hotels", "Generator Hostel — {anchor}", "Hostel",
     "Generator design-led hostel with private + dorm rooms, late-night bar, and breakfast counter.",
     "$", 4.2, 4.7, "", ""),
    ("hotels", "Hoxton — {anchor}", "Boutique hotel",
     "The Hoxton boutique hotel with library lounge, neighborhood guides, and weekend DJ nights.",
     "$$$", 4.6, 4.9, "", ""),
    ("hotels", "Ace Hotel — {anchor}", "Lifestyle hotel",
     "Ace Hotel with vinyl-record turntable in each room, lobby cafe, and curated music programming.",
     "$$$", 4.5, 4.9, "", ""),
    ("hotels", "Hyatt House — {anchor}", "Extended-stay hotel",
     "Hyatt House extended-stay with full-kitchen suites, hosted social hour, and 24-hour market.",
     "$$$", 4.4, 4.9, "", ""),
    ("hotels", "Element by Westin — {anchor}", "Eco hotel",
     "Element by Westin eco-conscious extended-stay with EV chargers, motion-sensor lights, and bike share.",
     "$$$", 4.4, 4.9, "", ""),
    # ---- Car rental + transportation + EV ----
    ("car-rental", "SIXT — {anchor}", "Car rental",
     "SIXT premium car rental with BMW/Mercedes fleet, mobile-key pickup, and one-way drops.",
     "$$$", 4.3, 4.8, "", ""),
    ("car-rental", "Zipcar — {anchor}", "Car sharing",
     "Zipcar car-share parking pod with hourly + daily rates, gas + insurance included.",
     "$$", 4.2, 4.7, "", ""),
    ("car-rental", "Getaround Pod — {anchor}", "Car sharing",
     "Getaround peer-to-peer car-share lot with instant-rent fobs and 24/7 access.",
     "$$", 4.1, 4.6, "", ""),
    ("car-rental", "Wisk eVTOL Pad — {anchor}", "Air taxi pad",
     "Wisk eVTOL pad concept for electric air-taxi pre-bookings, indoor lounge, and TSA pre-check.",
     "$$$$", 4.4, 4.9, "", ""),
    ("ev-charging", "Tesla Supercharger V4 — {anchor}", "EV fast-charger",
     "Tesla Supercharger V4 with 250kW peak, magic-dock CCS adapter, and 16-stall layout.",
     "$$", 4.5, 4.9, "", ""),
    ("ev-charging", "Electrify America — {anchor}", "EV fast-charger",
     "Electrify America 350kW DC fast charger with CCS + CHAdeMO, plug-and-charge for VW MEB.",
     "$$", 4.2, 4.7, "", ""),
    ("ev-charging", "EVgo Fast — {anchor}", "EV fast-charger",
     "EVgo Fast 100-350kW DC charger near grocery anchor, autocharge for Tesla/Rivian/Lucid.",
     "$$", 4.1, 4.6, "", ""),
    ("ev-charging", "Rivian Adventure Network — {anchor}", "EV fast-charger",
     "Rivian Adventure Network stall with branded canopy, 200kW peak, and trip-planner integration.",
     "$$$", 4.5, 4.9, "", ""),
    # ---- Fitness + wellness ----
    ("fitness", "F45 Training — {anchor}", "Functional fitness",
     "F45 Training studio with 45-minute group functional classes and a 8-week challenge program.",
     "$$$", 4.5, 4.9, "", ""),
    ("fitness", "CorePower Yoga — {anchor}", "Yoga studio",
     "CorePower Yoga studio with heated power flows, Yoga Sculpt, and free-week intro for newcomers.",
     "$$", 4.3, 4.8, "", ""),
    ("fitness", "SoulCycle — {anchor}", "Indoor cycling",
     "SoulCycle indoor cycling studio with candlelit rides, branded shoes for rent, and instructor playlists.",
     "$$$", 4.4, 4.9, "", ""),
    ("fitness", "Barry's Bootcamp — {anchor}", "Bootcamp",
     "Barry's red-room bootcamp with treadmill + floor intervals, fuel bar, and a 6 AM peak schedule.",
     "$$$", 4.5, 4.9, "", ""),
    ("fitness", "Lifetime Fitness — {anchor}", "Premium gym",
     "Lifetime Fitness premium gym with indoor + outdoor pools, salon, and KidsAcademy childcare.",
     "$$$$", 4.5, 4.9, "concourse", "1"),
    ("fitness", "Crunch Fitness — {anchor}", "Gym chain",
     "Crunch Fitness with HIIT zones, tanning beds, hydromassage chairs, and 24/7 access.",
     "$", 4.0, 4.5, "", ""),
    ("fitness", "Climbing Gym — {anchor}", "Climbing gym",
     "Bouldering + top-rope climbing gym with auto-belay walls, yoga studio, and a kids' birthday room.",
     "$$", 4.6, 4.9, "concourse", "1"),
    ("fitness", "{anchor} Pilates Reformer Studio", "Pilates studio",
     "Reformer Pilates studio with 8-machine classes, jump-board interval format, and intro packages.",
     "$$$", 4.5, 4.9, "", ""),
    # ---- Coworking + maker + creator ----
    ("shopping", "WeWork — {anchor}", "Coworking",
     "WeWork coworking with hot desks, dedicated offices, meeting rooms, and craft beer on tap Friday.",
     "$$$", 4.2, 4.7, "concourse", "1"),
    ("shopping", "Industrious — {anchor}", "Coworking",
     "Industrious premium coworking with private offices, hospitality-led front desk, and quiet phone booths.",
     "$$$", 4.5, 4.9, "concourse", "1"),
    ("shopping", "Spaces — {anchor}", "Coworking",
     "Spaces flexible workspace with stylish lounges, business club bar, and meeting rooms by the hour.",
     "$$$", 4.3, 4.8, "concourse", "1"),
    ("shopping", "{anchor} Makerspace & Fab Lab", "Maker space",
     "Community makerspace with laser cutters, 3D printers, CNC mill, and member-led workshops.",
     "$$", 4.6, 4.9, "concourse", "1"),
    ("shopping", "{anchor} Podcast Studio Rental", "Podcast studio",
     "Hourly podcast studio rental with Shure SM7B mics, broadcast-quality sound treatment, and remote-guest tooling.",
     "$$$", 4.5, 4.9, "", ""),
    ("shopping", "{anchor} Photo Studio Rental", "Photo studio",
     "Daylight photo studio rental with cyc wall, V-flats, Profoto lighting, and a styling kitchen.",
     "$$$", 4.5, 4.9, "", ""),
    # ---- Banking + financial ----
    ("shopping", "Chase Sapphire Lounge — {anchor}", "Bank lounge",
     "Chase Sapphire lounge for cardholders with espresso bar, workstations, and bookable conference rooms.",
     "$$$", 4.6, 4.9, "concourse", "1"),
    ("shopping", "Wells Fargo Branch — {anchor}", "Bank branch",
     "Wells Fargo branch with notary services, safe deposit boxes, and a stagecoach museum corner.",
     "$$", 4.0, 4.5, "", ""),
    ("shopping", "Bank of America Branch — {anchor}", "Bank branch",
     "Bank of America branch with ATM lobby, financial-center kiosks, and Erica voice-assistant demos.",
     "$$", 3.9, 4.4, "", ""),
    ("shopping", "Capital One Cafe — {anchor}", "Bank cafe",
     "Capital One Cafe hybrid bank + coffee shop with money coaches and 50% off Peet's for cardholders.",
     "$$", 4.5, 4.9, "concourse", "1"),
    # ---- Government / civic ----
    ("attractions", "{anchor} Public Library Branch", "Public library",
     "Public library branch with maker lab, children's storytime, free Wi-Fi, and chess club Saturday.",
     "$", 4.6, 4.9, "concourse", "1"),
    ("attractions", "{anchor} City Hall", "Government",
     "City hall with permit counters, marriage-license office, public-records vault, and council chambers.",
     "$", 4.0, 4.5, "concourse", "1"),
    ("attractions", "{anchor} DMV Service Center", "DMV",
     "DMV service center with REAL-ID renewals, license-plate desk, and appointment-only window.",
     "$", 3.6, 4.2, "concourse", "1"),
    ("attractions", "{anchor} Post Office", "Post office",
     "USPS post office with passport acceptance, PO boxes, priority shipping, and self-service kiosk.",
     "$", 3.9, 4.4, "", ""),
    ("attractions", "{anchor} Fire Station", "Fire station",
     "Fire station with engine + ladder companies, community open house, and CPR classes monthly.",
     "$", 4.5, 4.9, "", ""),
    ("attractions", "{anchor} Police Station", "Police station",
     "Police station with non-emergency desk, fingerprint services, and a community liaison office.",
     "$", 4.0, 4.5, "", ""),
    # ---- Outdoor + recreation ----
    ("parks", "{anchor} Kayak & SUP Rental", "Kayak rental",
     "Kayak and stand-up paddleboard rental with dock launch, lessons, and full-moon evening paddles.",
     "$$", 4.5, 4.9, "", ""),
    ("parks", "{anchor} Bike Share Dock", "Bike share",
     "City bike-share dock with 28 electric-assist bikes, day pass, and a contactless tap-to-unlock.",
     "$", 4.3, 4.8, "", ""),
    ("parks", "{anchor} Disc Golf Course", "Disc golf",
     "18-basket disc-golf course with wooded fairways, ladder shots, and a starter kiosk near tee 1.",
     "$", 4.4, 4.9, "", ""),
    ("parks", "{anchor} Skate Park", "Skate park",
     "Concrete skate park with bowls, ledges, a 4-foot mini-ramp, and Friday-night open sessions.",
     "$", 4.5, 4.9, "", ""),
    ("parks", "{anchor} Dog Park", "Dog park",
     "Off-leash dog park with separate small-dog area, water fountains, and Saturday socials.",
     "$", 4.5, 4.9, "", ""),
    ("parks", "{anchor} Community Garden", "Garden",
     "Community garden with 60 plots, monthly workshops, kids' patch, and free-compost Saturdays.",
     "$", 4.6, 4.9, "", ""),
    # ---- Education + childcare ----
    ("schools", "{anchor} Montessori Preschool", "Preschool",
     "Montessori preschool with mixed-age classrooms, outdoor garden, and accredited 6-week-to-6 program.",
     "$$$", 4.5, 4.9, "concourse", "1"),
    ("schools", "{anchor} Code Academy Bootcamp", "Coding school",
     "Code academy with 12-week full-stack and ML bootcamps, career services, and income-share plans.",
     "$$$$", 4.4, 4.9, "concourse", "1"),
    ("schools", "{anchor} Driving School", "Driving school",
     "Driving school with behind-the-wheel hours, defensive-driving certificate, and DMV test prep.",
     "$$", 4.3, 4.8, "", ""),
    ("schools", "{anchor} Music Conservatory", "Music school",
     "Music conservatory with piano, violin, cello, and voice lessons; recital hall and ensembles.",
     "$$$", 4.6, 4.9, "concourse", "1"),
    ("schools", "{anchor} Language Institute", "Language school",
     "Language institute with Mandarin, Spanish, Japanese, and Arabic tracks; CEFR-aligned placement.",
     "$$$", 4.5, 4.9, "", ""),
    # ---- Religious + spiritual ----
    ("religious", "{anchor} Buddhist Meditation Center", "Meditation center",
     "Buddhist meditation center with daily sittings, monthly retreats, and beginners' Sunday class.",
     "$", 4.7, 4.9, "", ""),
    ("religious", "{anchor} Hindu Mandir", "Hindu temple",
     "Hindu mandir with daily aarti, weekend bhajan, festival celebrations, and a community kitchen.",
     "$", 4.7, 4.9, "concourse", "1"),
    ("religious", "{anchor} Reform Synagogue", "Synagogue",
     "Reform synagogue with Friday Kabbalat Shabbat, religious school, and a social-justice committee.",
     "$", 4.6, 4.9, "concourse", "1"),
    ("religious", "{anchor} Sikh Gurdwara", "Gurdwara",
     "Sikh gurdwara with langar community meal, daily kirtan, and youth Gurmat camp every summer.",
     "$", 4.8, 4.9, "concourse", "1"),
    # ---- Transit + airports ----
    ("transit", "{anchor} Multimodal Transit Plaza", "Transit hub",
     "Multimodal plaza with bus bays, light-rail station, bike share, and a real-time arrivals board.",
     "$", 4.2, 4.7, "concourse", "1"),
    ("transit", "{anchor} Ferry Terminal", "Ferry",
     "Ferry terminal with 30-minute crossings, vehicle deck, indoor lounge, and bike storage rack.",
     "$$", 4.4, 4.9, "concourse", "1"),
    ("transit", "{anchor} Greyhound Bus Station", "Bus station",
     "Greyhound intercity bus station with package shipping, ticket counters, and 24-hour waiting room.",
     "$", 3.7, 4.2, "", ""),
    ("transit", "{anchor} Amtrak Station", "Train station",
     "Amtrak station with quiet car upgrades, baggage check, Café Acela cart, and ClubAcela lounge.",
     "$$", 4.3, 4.8, "concourse", "1"),
    # ---- Hospitals + health ----
    ("hospitals", "{anchor} Children's Hospital", "Pediatric hospital",
     "Children's hospital with pediatric ER, NICU, child-life specialists, and family lodging.",
     "$$$$", 4.7, 4.9, "concourse", "1"),
    ("hospitals", "{anchor} Cancer Center", "Cancer center",
     "Comprehensive cancer center with infusion suite, radiation oncology, clinical trials, and survivorship.",
     "$$$$", 4.6, 4.9, "concourse", "1"),
    ("hospitals", "{anchor} VA Medical Center", "VA hospital",
     "VA medical center with primary care, mental-health clinic, and veterans-only urgent care.",
     "$$", 4.2, 4.7, "concourse", "1"),
    ("hospitals", "{anchor} Birthing Center", "Birthing center",
     "Midwife-led birthing center with water-birth tubs, doula partnerships, and home-style suites.",
     "$$$", 4.6, 4.9, "", ""),
    # ---- Entertainment + nightlife ----
    ("entertainment", "{anchor} Comedy Club", "Comedy club",
     "Comedy club with weekend headliners, open-mic Tuesdays, two-drink minimum, and 9 PM late shows.",
     "$$", 4.4, 4.9, "concourse", "1"),
    ("entertainment", "{anchor} Jazz Lounge", "Jazz club",
     "Intimate jazz lounge with two nightly sets, craft cocktails, and a Steinway grand on stage.",
     "$$$", 4.6, 4.9, "", ""),
    ("entertainment", "{anchor} Bowling Lanes", "Bowling alley",
     "Bowling lanes with 24 lanes, cosmic-bowl Fridays, sports bar, and arcade redemption tickets.",
     "$$", 4.2, 4.7, "concourse", "1"),
    ("entertainment", "{anchor} Escape Room Co.", "Escape room",
     "Escape-room co. with 6 themed rooms — heist, haunted, sci-fi — at multiple difficulty levels.",
     "$$", 4.5, 4.9, "concourse", "1"),
    ("entertainment", "{anchor} Axe Throwing Club", "Axe throwing",
     "Axe-throwing club with coached leagues, BYOB Fridays, and birthday-party packages.",
     "$$", 4.4, 4.9, "concourse", "1"),
    ("entertainment", "{anchor} Karaoke Box", "Karaoke",
     "Korean-style karaoke box with private rooms, 80,000-song catalog, and tabletop bell-service.",
     "$$", 4.4, 4.9, "concourse", "1"),
    ("entertainment", "{anchor} Drive-In Theater", "Drive-in",
     "Drive-in theater with classic double-features, FM-radio audio, popcorn truck, and pet-friendly rows.",
     "$$", 4.5, 4.9, "", ""),
    ("entertainment", "Topgolf — {anchor}", "Driving range",
     "Topgolf entertainment with three-tier bays, microchip-tracked balls, food + cocktails, and party rooms.",
     "$$$", 4.4, 4.9, "concourse", "1"),
    # ---- Museums + culture ----
    ("museums", "{anchor} Science Center", "Science center",
     "Hands-on science center with planetarium dome, IMAX, traveling exhibits, and overnight camps for kids.",
     "$$", 4.5, 4.9, "concourse", "1"),
    ("museums", "{anchor} Children's Museum", "Children's museum",
     "Children's museum with toddler town, water play, climber atrium, and rotating themed pop-ups.",
     "$$", 4.6, 4.9, "concourse", "1"),
    ("museums", "{anchor} Aquarium", "Aquarium",
     "Aquarium with shark tunnel, jellyfish tower, daily otter feedings, and a touch-tide-pool exhibit.",
     "$$$", 4.6, 4.9, "concourse", "1"),
    ("museums", "{anchor} Planetarium", "Planetarium",
     "Planetarium with 360-degree dome shows, laser-music nights, and observatory open-house Wednesdays.",
     "$$", 4.6, 4.9, "concourse", "1"),
    ("museums", "{anchor} Anime + Pop Culture Museum", "Pop culture museum",
     "Anime + pop-culture museum with cosplay exhibits, retro-arcade hall, and special-guest signings.",
     "$$", 4.5, 4.9, "concourse", "1"),
    # ---- Parking + storage ----
    ("parking", "{anchor} Smart Parking Garage", "Smart garage",
     "Smart parking garage with license-plate recognition, EV-stall reservations, and a 6th-floor rooftop deck.",
     "$$", 4.0, 4.5, "concourse", "1"),
    ("parking", "{anchor} Park & Fly Lot", "Airport parking",
     "Park & Fly economy lot with 24/7 shuttle, valet upgrade, and luggage-assist porters at curbside.",
     "$$", 4.1, 4.6, "", ""),
    ("parking", "{anchor} Bike + Scooter Corral", "Bike storage",
     "Secure bike + e-scooter corral with overhead camera, badge entry, and air pumps at the door.",
     "$", 4.4, 4.9, "", ""),
    # ---- Specialty shopping ----
    ("shopping", "{anchor} Vintage Record Store", "Record store",
     "Vintage record store with 40,000 LPs, listening booths, and a Saturday DJ-on-the-floor session.",
     "$$", 4.6, 4.9, "concourse", "1"),
    ("shopping", "{anchor} Comic Book Shop", "Comic shop",
     "Comic book shop with new-comics Wednesdays, vintage back-issue boxes, and weekly D&D nights.",
     "$$", 4.5, 4.9, "concourse", "1"),
    ("shopping", "{anchor} Board Game Cafe", "Board game cafe",
     "Board game cafe with 800-game library, $5 game-fee + drinks, and weekend tournament tables.",
     "$$", 4.6, 4.9, "concourse", "1"),
    ("shopping", "{anchor} Indie Bookstore", "Bookstore",
     "Independent bookstore with author events, kids' loft, staff-pick tables, and a cafe in back.",
     "$$", 4.7, 4.9, "concourse", "1"),
    ("shopping", "{anchor} Farmers Market", "Farmers market",
     "Saturday farmers market with 60 vendors, prepared-food row, live music, and free parking lot.",
     "$$", 4.6, 4.9, "", ""),
    ("shopping", "REI Co-op — {anchor}", "Outdoor gear",
     "REI Co-op outdoor gear with bike + ski shop, member dividends, and free repair-clinic classes.",
     "$$$", 4.5, 4.9, "concourse", "1"),
    ("shopping", "Patagonia — {anchor}", "Outdoor apparel",
     "Patagonia store with Worn Wear repair counter, environmental-grant displays, and 1% for the Planet signage.",
     "$$$", 4.6, 4.9, "concourse", "1"),
    ("shopping", "Uniqlo — {anchor}", "Apparel chain",
     "Uniqlo flagship with HEATTECH/AIRism walls, free hemming, and UT graphic-tee collaborations.",
     "$$", 4.5, 4.9, "concourse", "1"),
    ("shopping", "Muji — {anchor}", "Lifestyle store",
     "Muji lifestyle store with stationery wall, aroma bar, food shelf, and house-brand apparel.",
     "$$", 4.5, 4.9, "concourse", "1"),
    ("shopping", "Daiso — {anchor}", "Variety store",
     "Daiso variety store with bento gear, hobby supplies, and a wall of mostly-$2 finds.",
     "$", 4.4, 4.9, "concourse", "1"),
    # ---- Beauty + personal care ----
    ("shopping", "Sephora Studio — {anchor}", "Beauty shop",
     "Sephora Studio with custom skin scans, beauty advisors, and bookable mini-makeover services.",
     "$$$", 4.4, 4.9, "concourse", "1"),
    ("shopping", "Ulta Beauty — {anchor}", "Beauty shop",
     "Ulta Beauty with salon services, drugstore-to-prestige range, and Beauty Stage events.",
     "$$", 4.3, 4.8, "concourse", "1"),
    ("shopping", "Drybar — {anchor}", "Blowout bar",
     "Drybar blowout bar with seven core blowout styles, mimosas at check-in, and prepaid bar packages.",
     "$$", 4.4, 4.9, "", ""),
    ("shopping", "{anchor} Nail Salon Spa", "Nail salon",
     "Nail salon + spa with gel sets, dip powder, paraffin pedicure add-ons, and walk-ins welcome.",
     "$$", 4.3, 4.8, "", ""),
    ("shopping", "{anchor} Barbershop & Shave Parlor", "Barbershop",
     "Old-school barbershop + shave parlor with hot-towel service, beard trims, and walk-in welcome.",
     "$$", 4.5, 4.9, "", ""),
    ("shopping", "{anchor} Korean Body Spa (Jjimjilbang)", "Spa",
     "Korean jjimjilbang with hot/cold pools, body scrubs, salt rooms, and a 24-hour rest area.",
     "$$$", 4.6, 4.9, "concourse", "1"),
    # ---- Pet services ----
    ("shopping", "{anchor} Pet Boarding & Daycare", "Pet boarding",
     "Pet boarding with daycare playgroups, webcam access, grooming add-ons, and 24/7 staff.",
     "$$$", 4.5, 4.9, "", ""),
    ("shopping", "{anchor} Veterinary Hospital", "Vet hospital",
     "Veterinary hospital with after-hours emergency, surgery suite, dental cleanings, and Fear-Free certified.",
     "$$$", 4.6, 4.9, "", ""),
    ("shopping", "{anchor} Pet Adoption Center", "Pet shelter",
     "Pet adoption center with dogs, cats, and small animals; on-site spay/neuter and microchip clinic.",
     "$", 4.7, 4.9, "concourse", "1"),
    ("shopping", "PetSmart — {anchor}", "Pet supply",
     "PetSmart pet-supply store with grooming, training classes, and a Banfield vet inside.",
     "$$", 4.2, 4.7, "concourse", "1"),
    ("shopping", "Petco — {anchor}", "Pet supply",
     "Petco pet supply with grooming salon, Vetco wellness clinics, and adoption events on weekends.",
     "$$", 4.1, 4.6, "concourse", "1"),
    # ---- ATMs ----
    ("atms", "Chase ATM Lobby — {anchor}", "Bank ATM",
     "Chase ATM lobby with 24/7 access, cash deposit + check imaging, and a coin-counting machine.",
     "$", 4.0, 4.6, "concourse", "1"),
    ("atms", "Citi ATM Vestibule — {anchor}", "Bank ATM",
     "Citi ATM vestibule with multi-language support, deposit + withdraw, and an after-hours card-tap door.",
     "$", 4.0, 4.5, "concourse", "1"),
    ("atms", "TD Bank ATM — {anchor}", "Bank ATM",
     "TD Bank ATM with envelope-free deposits, no-fee TD checking, and bilingual menus.",
     "$", 4.0, 4.5, "", ""),
    ("atms", "PNC Bank ATM — {anchor}", "Bank ATM",
     "PNC ATM with image-deposit, instant card replacement at nearby branches, and contactless tap.",
     "$", 4.0, 4.5, "", ""),
    ("atms", "Bitcoin ATM Kiosk — {anchor}", "Crypto ATM",
     "Bitcoin ATM kiosk with cash-to-crypto swaps, ID-tier limits, and Lightning Network support.",
     "$$$", 3.8, 4.3, "", ""),
    ("atms", "Allpoint ATM — {anchor}", "Surcharge-free ATM",
     "Allpoint surcharge-free ATM available to participating credit-union and online-bank members.",
     "$", 4.1, 4.6, "concourse", "1"),
    # ---- Gas stations ----
    ("gas-stations", "Shell V-Power Station — {anchor}", "Gas station",
     "Shell station with V-Power Nitro+ premium, full-serve diesel pumps, and a Shell Café snack bar.",
     "$$", 4.0, 4.5, "", ""),
    ("gas-stations", "BP Connect — {anchor}", "Gas station",
     "BP Connect station with Wild Bean Café, Amoco Ultimate fuel, and a 24/7 convenience kiosk.",
     "$$", 3.9, 4.4, "", ""),
    ("gas-stations", "Chevron with Techron — {anchor}", "Gas station",
     "Chevron with Techron-formulated fuel, ExtraMile market, and 24/7 unleaded pumps.",
     "$$", 4.0, 4.5, "", ""),
    ("gas-stations", "ExxonMobil — {anchor}", "Gas station",
     "ExxonMobil station with Synergy Supreme+ fuel, On the Run market, and a kids' coloring corner.",
     "$$", 3.9, 4.4, "", ""),
    ("gas-stations", "Costco Gas — {anchor}", "Members-only gas",
     "Costco members-only gas station with discounted regular + premium, 12 pumps, and a long-but-fast queue.",
     "$", 4.4, 4.9, "", ""),
    ("gas-stations", "Buc-ee's Travel Center — {anchor}", "Travel center",
     "Buc-ee's mega-station with 100+ pumps, brisket sandwiches, beaver-themed merch, and the cleanest restrooms in America.",
     "$$", 4.7, 4.9, "", ""),
    ("gas-stations", "Wawa Fuel — {anchor}", "Convenience fuel",
     "Wawa fuel + market combo with hoagie counter, coffee bar, mac & cheese, and built-to-order breakfast.",
     "$", 4.5, 4.9, "", ""),
    ("gas-stations", "Sheetz — {anchor}", "Convenience fuel",
     "Sheetz convenience-store fuel with MTO touch-screen ordering, 24/7 hours, and a frozen-yogurt counter.",
     "$", 4.4, 4.9, "", ""),
    # ---- Services ----
    ("services", "{anchor} Laundromat & Wash-Dry-Fold", "Laundromat",
     "Laundromat with 50 high-capacity washers, wash-dry-fold pickup, and a free-coffee waiting area.",
     "$$", 4.1, 4.6, "", ""),
    ("services", "{anchor} Dry Cleaners", "Dry cleaner",
     "Eco-friendly dry cleaners with same-day service, alterations, and curbside drop-off.",
     "$$", 4.3, 4.8, "", ""),
    ("services", "{anchor} Locksmith 24/7", "Locksmith",
     "24/7 locksmith with car/home/safe rekeying, smart-lock installs, and a 30-minute emergency response.",
     "$$$", 4.4, 4.9, "", ""),
    ("services", "Ace Hardware — {anchor}", "Hardware store",
     "Ace Hardware with paint mixing, key cutting, propane refill, and the helpful-place experts on the floor.",
     "$$", 4.5, 4.9, "concourse", "1"),
    ("services", "True Value Hardware — {anchor}", "Hardware store",
     "True Value Hardware with tool rental, plumbing aisle, and a Saturday how-to workshop.",
     "$$", 4.4, 4.9, "concourse", "1"),
    ("services", "FedEx Ship Center — {anchor}", "Shipping",
     "FedEx Ship Center with packing supplies, drop-off cutoffs, hold-at-location pickups, and printing services.",
     "$$", 4.2, 4.7, "", ""),
    ("services", "UPS Store — {anchor}", "Shipping",
     "UPS Store with mailbox rentals, notary services, packing + shipping, and a 6 PM domestic cutoff.",
     "$$", 4.2, 4.7, "", ""),
    ("services", "{anchor} Auto Body & Collision Center", "Auto body",
     "Auto body + collision center with insurance direct-bill, loaner cars, and a 5-year paint warranty.",
     "$$$", 4.3, 4.8, "", ""),
    ("services", "{anchor} Tire & Wheel Shop", "Tire shop",
     "Tire + wheel shop with road-hazard warranty, free rotations, alignment bay, and TPMS service.",
     "$$", 4.4, 4.9, "", ""),
    ("services", "{anchor} EV Service Center", "EV service",
     "EV service center with battery diagnostics, software updates, and a loaner-EV program.",
     "$$$", 4.5, 4.9, "", ""),
    # ---- Beauty / health-beauty ----
    ("health-beauty", "{anchor} Medical Spa", "Med spa",
     "Medical spa with Botox, fillers, laser hair removal, and HydraFacial signature treatments.",
     "$$$", 4.5, 4.9, "concourse", "1"),
    ("health-beauty", "{anchor} Eyebrow Threading Bar", "Threading",
     "Eyebrow threading bar with brow shaping, henna tinting, and lash-lift add-ons.",
     "$", 4.4, 4.9, "concourse", "1"),
    ("health-beauty", "{anchor} Lash & Brow Bar", "Lash bar",
     "Lash + brow bar with classic-to-volume extensions, lash lift, and a brow-lamination service.",
     "$$", 4.5, 4.9, "concourse", "1"),
    ("health-beauty", "Aveda Salon — {anchor}", "Salon",
     "Aveda salon with botanically-derived color, treatment menu, and recyclable take-home minis.",
     "$$$", 4.4, 4.9, "concourse", "1"),
    ("health-beauty", "{anchor} Tanning + Spray Studio", "Tanning",
     "Tanning + spray studio with hands-free booths, hand-applied custom airbrush, and beach-prep packages.",
     "$$", 4.2, 4.7, "", ""),
    ("health-beauty", "{anchor} Massage & Bodywork", "Massage",
     "Massage + bodywork studio with deep-tissue, prenatal, and Thai stretch sessions; 60/90/120-minute options.",
     "$$$", 4.6, 4.9, "", ""),
    # ---- Indoor mall + airport ----
    ("indoor-mall-shops", "{anchor} Mall Kiosk — Phone Accessories", "Mall kiosk",
     "Mall kiosk for phone accessories with screen protectors applied, cases, and chargers.",
     "$", 4.0, 4.5, "concourse", "1"),
    ("indoor-mall-shops", "{anchor} Mall Kiosk — Sunglasses", "Mall kiosk",
     "Sunglasses kiosk with polarized lineup, fitting + adjustments, and try-on stations.",
     "$$", 4.1, 4.6, "concourse", "1"),
    ("indoor-mall-shops", "{anchor} Mall Pretzel Stand", "Food kiosk",
     "Mall pretzel stand with jumbo + bite-size, cinnamon-sugar twists, and lemonade pairings.",
     "$", 4.3, 4.8, "concourse", "1"),
    ("indoor-airport-shops", "{anchor} Airport Bookshop", "Airport shop",
     "Airport bookshop with current bestsellers, magazines, travel pillows, and SIM-card kiosk.",
     "$$", 4.0, 4.5, "concourse", "2"),
    ("indoor-airport-shops", "{anchor} Airport Lounge", "Airline lounge",
     "Airline lounge with hot bar, espresso, showers, and panoramic runway views past security.",
     "$$$", 4.5, 4.9, "concourse", "2"),
    ("indoor-airport-shops", "{anchor} Airport Duty-Free", "Duty-free",
     "Airport duty-free with spirits, fragrance, designer leather, and tobacco-free zones.",
     "$$$", 4.0, 4.5, "concourse", "2"),
    # ---- Public services ----
    ("libraries", "{anchor} Main Library Branch", "Library",
     "Main library branch with bookable study rooms, 3D printer, children's loft, and digital archives.",
     "$", 4.7, 4.9, "concourse", "1"),
    ("post-offices", "USPS Branch — {anchor}", "Post office",
     "USPS branch with passport acceptance, PO box rentals, priority mail, and self-service kiosk.",
     "$", 3.9, 4.4, "", ""),
    ("police-stations", "{anchor} Precinct Station", "Police precinct",
     "Police precinct station with community-affairs desk, fingerprinting hours, and report-only walk-ins.",
     "$", 4.0, 4.5, "", ""),
    ("fire-stations", "{anchor} Fire & Rescue Station", "Fire station",
     "Fire + rescue station with engine, ladder, and ambulance bays; child car-seat installs by appointment.",
     "$", 4.7, 4.9, "", ""),
    # ---- Outdoor extras ----
    ("dog-parks", "{anchor} Off-Leash Dog Park", "Dog park",
     "Off-leash dog park with separated small-dog and big-dog areas, agility course, and water fountains.",
     "$", 4.5, 4.9, "", ""),
    ("public-restrooms", "{anchor} Public Restroom Block", "Restroom",
     "Public restroom block with attendant, accessible stall, baby-change station, and 24/7 hours.",
     "$", 3.8, 4.4, "", ""),
    ("playgrounds", "{anchor} Adventure Playground", "Playground",
     "Adventure playground with rope climbers, splash pad, age-tiered swing sets, and rubber-mat falls zone.",
     "$", 4.6, 4.9, "", ""),
    ("beaches", "{anchor} Beach Boardwalk", "Beach boardwalk",
     "Beach boardwalk with lifeguard stands, paid parking, beach-chair rentals, and seasonal food vendors.",
     "$$", 4.5, 4.9, "", ""),
    # ---- Pet / vet extras ----
    ("dentists", "{anchor} Cosmetic Dentistry", "Cosmetic dentist",
     "Cosmetic dentistry with veneers, Invisalign, in-office whitening, and same-day crowns.",
     "$$$$", 4.5, 4.9, "", ""),
    ("dentists", "{anchor} Pediatric Dental", "Pediatric dentist",
     "Pediatric dental office with kid-friendly chairs, sedation options, and a play-area waiting room.",
     "$$$", 4.6, 4.9, "", ""),
    ("veterinarians", "{anchor} 24-Hour Animal Hospital", "Vet hospital",
     "24-hour animal hospital with ER triage, surgery suite, exotic-pet specialty, and grief counseling.",
     "$$$", 4.6, 4.9, "", ""),
    ("veterinarians", "{anchor} Low-Cost Vet Clinic", "Vet clinic",
     "Low-cost vet clinic with sliding-scale visits, vaccine clinic days, and spay/neuter assistance.",
     "$$", 4.4, 4.9, "", ""),
    # ---- Campus ----
    ("campus-buildings", "{anchor} Student Union", "Campus building",
     "Student union with dining hall, ballroom, game-room arcade, and student-org office suites.",
     "$", 4.4, 4.9, "concourse", "1"),
    ("campus-buildings", "{anchor} Recreation Center", "Campus rec",
     "Campus recreation center with pool, climbing wall, weight room, and group-fitness studios.",
     "$$", 4.5, 4.9, "concourse", "1"),
]


def expand_places_r8(db, Place, Category, City):
    """R8 expansion: new chains + service verticals.

    Adds another ~150k venue rows by sweeping `_R8_TEMPLATES` against every
    city using the same per-city Fisher-Yates shuffle as R6/R7.  Gated on
    Place count >= 540000 so the function is a no-op once the seed has
    been built once (keeps byte-identical reset).
    """
    if Place.query.count() >= 540000:
        return

    cat_by_slug = {c.slug: c for c in Category.query.all()}
    cities = City.query.order_by(City.id).all()
    if not cities:
        return

    donor_pool = []
    for p in (Place.query
              .filter(Place.hero_image.like("/static/images/places/%"))
              .order_by(Place.id).limit(80).all()):
        try:
            photos = json.loads(p.photos_json or "[]")
        except Exception:
            photos = []
        if p.hero_image:
            donor_pool.append((p.hero_image, photos or [p.hero_image]))
    if not donor_pool:
        donor_pool = [("/static/images/heroes/eiffel-tower.jpg",
                       ["/static/images/heroes/eiffel-tower.jpg"])]

    _R8_CHAINS = (
        "Tim Hortons", "Gong cha", "Kung Fu Tea", "Boba Guys", "Tea Station",
        "85C Bakery Cafe", "Insomnia Cookies", "Crumbl Cookies",
        "Jeni's Splendid Ice Creams", "Pinkberry",
        "Wegmans", "ALDI Express", "Mitsuwa Marketplace", "99 Ranch Market",
        "Sprouts Farmers Market", "Fresh Thyme", "DashMart", "Gopuff",
        "Sonder", "citizenM", "Generator Hostel", "Hoxton", "Ace Hotel",
        "Hyatt House", "Element by Westin",
        "SIXT", "Zipcar", "Getaround Pod", "Wisk eVTOL Pad",
        "Tesla Supercharger V4", "Electrify America", "EVgo Fast",
        "Rivian Adventure Network",
        "F45 Training", "CorePower Yoga", "SoulCycle", "Barry's Bootcamp",
        "Lifetime Fitness", "Crunch Fitness",
        "WeWork", "Industrious", "Spaces",
        "Chase Sapphire Lounge", "Wells Fargo Branch",
        "Bank of America Branch", "Capital One Cafe",
        "MinuteClinic at CVS",
        "Topgolf", "REI Co-op", "Patagonia", "Uniqlo", "Muji", "Daiso",
        "Sephora Studio", "Ulta Beauty", "Drybar", "PetSmart", "Petco",
    )

    added = 0
    for city in cities:
        anchor = city.display_name.split(",")[0].split(" ")[0]
        templates = list(enumerate(_R8_TEMPLATES))
        for i in range(len(templates) - 1, 0, -1):
            j = int.from_bytes(
                hashlib.md5(f"r8sh:{city.slug}:{i}".encode()).digest()[:4],
                "big") % (i + 1)
            templates[i], templates[j] = templates[j], templates[i]

        for idx, tpl in templates:
            (cat_slug, pattern, subtitle, desc, price, rlo, rhi,
             indoor_zone, floor_num) = tpl
            cat = cat_by_slug.get(cat_slug)
            if not cat:
                continue
            slug = f"r8-{city.slug}-{cat_slug}-{idx:03d}"
            if Place.query.filter_by(slug=slug).first():
                continue

            name = pattern.format(anchor=anchor)
            local_seed = _seed_int_hex(slug, "r8loc")
            hero, gallery = donor_pool[local_seed % len(donor_pool)]
            lat = city.lat + ((local_seed % 800) - 400) / 10000.0
            lng = city.lng + (((local_seed // 800) % 1000) - 500) / 10000.0
            rating = round(rlo + (local_seed % 100) / 100.0 * (rhi - rlo), 1)
            review_count = 9 + (local_seed % 3600)

            chain = ""
            for brand in _R8_CHAINS:
                if name.startswith(brand) or (" — " in pattern and pattern.startswith(brand)):
                    chain = brand
                    break

            hours_pick = (local_seed >> 4) % 7
            hours_options = [
                "Mon-Sun: 8:00 AM - 9:00 PM",
                "Mon-Sat: 9:00 AM - 8:00 PM, Sun 10:00 AM - 6:00 PM",
                "Tue-Sun: 11:00 AM - 10:00 PM, Closed Mon",
                "Open 24 hours",
                "Mon-Fri: 6:30 AM - 8:00 PM, Weekends 8:00 AM - 6:00 PM",
                "Mon-Sun: 7:00 AM - 11:00 PM",
                "Daily: 10:00 AM - 9:00 PM",
            ]
            tags = ["r8", cat_slug, anchor.lower(), city.country.lower()]
            if indoor_zone:
                tags.append(indoor_zone)
            if chain:
                tags.append(chain.lower().replace(" ", "-").replace("'", ""))

            db.session.add(Place(
                slug=slug, name=name, category_id=cat.id, city_id=city.id,
                subtitle=subtitle,
                description=desc,
                address=f"{20 + (local_seed % 9800)} {['Maple','Birch','Spruce','Linden','Hawthorn','Sycamore','Juniper','Cedar'][local_seed % 8]} St, {city.display_name}",
                phone=f"+{1 + (local_seed % 9)} {200 + (local_seed % 800)} {1000 + (local_seed % 9000)}",
                hours=hours_options[hours_pick],
                website=google_maps_search_url(name, city.display_name),
                rating=rating,
                review_count=review_count,
                price_level=price,
                hero_image=hero,
                photos_json=json.dumps(gallery[:5]),
                lat=lat, lng=lng,
                tags_json=json.dumps(tags),
                subcategory=subtitle,
                chain_brand=chain,
                is_24h=(hours_pick == 3),
                is_popular=(rating >= 4.6 and (local_seed % 4) == 0),
                has_parking_lot=(cat_slug in ("supermarkets", "hotels",
                                              "shopping", "fitness",
                                              "hospitals", "schools",
                                              "religious", "entertainment",
                                              "car-rental", "parking",
                                              "transit")
                                 or (local_seed % 3) == 0),
                ev_charging=(cat_slug == "ev-charging"
                              or "Supercharger" in name
                              or "Electrify" in name
                              or "EVgo" in name
                              or "Rivian" in name),
                bicycle_parking=(local_seed % 2) == 0,
                indoor_zone_type=indoor_zone,
                floor_number=floor_num,
                parking_lot_capacity=(80 + (local_seed % 1800)) if cat_slug == "parking" else 0,
                delivery_available=(cat_slug == "restaurants" and (local_seed % 2) == 0),
                dine_in=(cat_slug in ("restaurants", "coffee-shops")),
                takeout=(cat_slug in ("restaurants", "coffee-shops",
                                       "supermarkets")),
                accepts_reservations=(cat_slug == "restaurants" and (local_seed % 3) == 0),
                serves_breakfast=(cat_slug in ("restaurants", "coffee-shops")
                                   and (local_seed % 2) == 0),
                serves_lunch=(cat_slug == "restaurants"),
                serves_dinner=(cat_slug == "restaurants"),
                serves_alcohol=(cat_slug == "restaurants" and (local_seed % 3) == 0),
                serves_vegetarian=(cat_slug == "restaurants" and (local_seed % 2) == 0),
            ))
            added += 1
            if added % 1500 == 0:
                db.session.commit()
    db.session.commit()
    print(f"expand_places_r8: added {added} R8 places (total {Place.query.count()})")
