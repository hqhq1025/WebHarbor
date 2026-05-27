"""Seed data builder for the apartments.com mirror.

Deterministic synthesis of 400+ buildings across 20+ US metros, plus floor
plans, units, schools, POIs, reviews, neighborhood data, and renters-guide
articles. Driven by a stable md5-based hash so reseeding produces byte-
identical SQLite — this is required for the /reset/<site> invariant.

Each seed_*() function is idempotent at the function level: it early-returns
if its primary table is already populated. Per-row gates are insufficient
because even a no-op `db.session.commit()` bumps SQLite metadata.
"""
import hashlib
import json
import os
import re
from datetime import date, datetime, timedelta

from app import (db, User, City, Neighborhood, Building, FloorPlan, Unit,
                 School, BuildingSchool, POI, Review, SavedSearch, Favorite,
                 TourRequest, Article, Newsletter, PropertyLead)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(BASE_DIR, "static", "images", "buildings")


# ─── Deterministic helpers ────────────────────────────────────────────────────


def _h(*parts):
    return int(hashlib.md5("|".join(map(str, parts)).encode()).hexdigest(), 16)


def _pick(seq, *parts):
    return seq[_h(*parts) % len(seq)] if seq else None


def _r(lo, hi, *parts):
    """Deterministic integer in [lo, hi]."""
    return lo + (_h(*parts) % (hi - lo + 1))


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


# ─── Real metro & neighborhood data ────────────────────────────────────────


# 22 metros, each with a list of real neighborhoods + street name pool +
# rent multiplier (1.0 = national average ~ $1700 1BR), state, ZIP prefix,
# (lat, lng) bounding box for synthetic coords.
METROS = [
    {
        "name": "New York", "state": "NY", "state_full": "New York",
        "slug": "new-york-ny", "is_featured": True, "mult": 2.4,
        "blurb": "From Manhattan high-rises to Brooklyn brownstones, NYC has the country's deepest rental market.",
        "zip_prefix": "100",
        "bbox": (40.55, -74.10, 40.92, -73.70),
        "nbhds": [
            ("Upper East Side", "uptown classic with parks, museums, and pre-war doorman buildings"),
            ("Upper West Side", "leafy streets steps from Central Park and Lincoln Center"),
            ("Midtown East", "high-rise glass towers near the UN and Grand Central"),
            ("Midtown West", "Hell's Kitchen energy with Hudson Yards growth"),
            ("Chelsea", "art galleries, the High Line, and boutique shopping"),
            ("Greenwich Village", "tree-lined townhouses and NYU campus life"),
            ("SoHo", "cast-iron lofts and luxury retail flagships"),
            ("Tribeca", "celebrity-favored low-rises and riverside parks"),
            ("Financial District", "skyline views, ferries to Brooklyn, and rapid commutes"),
            ("Lincoln Square", "performing arts district with Hudson River vistas"),
            ("East Harlem", "fast-changing residential corridor along 5th Avenue"),
            ("Williamsburg", "Brooklyn waterfront with skyline views and a food scene"),
            ("Long Island City", "Queens river-facing high-rises with E/M/7 access"),
            ("Park Slope", "Brooklyn brownstones and Prospect Park"),
            ("Brooklyn Heights", "promenade views and historic limestone rowhouses"),
        ],
        "streets": ["5th Ave", "Park Ave", "Madison Ave", "Lexington Ave", "Riverside Blvd",
                    "Columbus Cir", "W 21st St", "W 53rd St", "W 57th St", "W 66th St",
                    "E 64th St", "E 57th St", "E 90th St", "Mission St", "Leonard St"],
    },
    {
        "name": "Los Angeles", "state": "CA", "state_full": "California",
        "slug": "los-angeles-ca", "is_featured": True, "mult": 1.85,
        "blurb": "Beach, hills, and Downtown high-rises — LA's rental footprint is enormous and stylistically diverse.",
        "zip_prefix": "900",
        "bbox": (33.80, -118.50, 34.30, -118.15),
        "nbhds": [
            ("Downtown LA", "Walkable Arts District, civic core, and high-rise SoFi towers"),
            ("South Park", "DTLA residential pocket adjacent to Crypto.com Arena"),
            ("Hollywood", "Walk-of-Fame energy with restored historic apartment blocks"),
            ("West Hollywood", "Sunset Strip nightlife with boutique low-rises"),
            ("Santa Monica", "beachfront living with the Promenade and Big Blue Bus"),
            ("Venice", "boardwalk and canals; a counterculture-leaning rental scene"),
            ("Mid-Wilshire", "K-town adjacent corridor with mid-century courtyards"),
            ("Koreatown", "dense, food-forward, fast-rising in rent"),
            ("Silver Lake", "hipster reservoir-adjacent neighborhood"),
            ("Echo Park", "lake views and indie venues"),
            ("Brentwood", "leafy Westside enclave near UCLA"),
            ("Westwood", "UCLA-adjacent with student-heavy mid-rises"),
            ("Culver City", "Sony Pictures lot and tech-fueled new construction"),
            ("Pasadena", "Craftsman charm and Old Town"),
            ("Long Beach", "harbor city with diverse waterfront stock"),
        ],
        "streets": ["S Figueroa St", "S Grand Ave", "Rochester Ave", "Sunset Blvd", "Wilshire Blvd",
                    "Hollywood Blvd", "Pico Blvd", "Olympic Blvd", "Westwood Blvd", "Santa Monica Blvd",
                    "Beverly Blvd", "Melrose Ave", "Vermont Ave", "Western Ave", "La Brea Ave"],
    },
    {
        "name": "Chicago", "state": "IL", "state_full": "Illinois",
        "slug": "chicago-il", "is_featured": True, "mult": 1.15,
        "blurb": "Lakefront high-rises, brick walk-ups in Wicker Park, and a transit-rich downtown.",
        "zip_prefix": "606",
        "bbox": (41.65, -87.85, 42.05, -87.55),
        "nbhds": [
            ("Streeterville", "Lake Michigan views and Northwestern hospital corridor"),
            ("Lake Shore East", "modern high-rises east of Michigan Ave"),
            ("River North", "art galleries and converted lofts"),
            ("Gold Coast", "historic mansions and Oak Street boutiques"),
            ("West Loop", "restaurant row and Google's Midwest HQ"),
            ("South Loop", "Museum Campus and waterfront parks"),
            ("Lincoln Park", "DePaul, Lincoln Park Zoo, and brick three-flats"),
            ("Lakeview", "Wrigley Field neighborhood with vintage walk-ups"),
            ("Wicker Park", "indie music, vintage shopping, milkbar coffee"),
            ("Logan Square", "boulevards and farm-to-table dining"),
            ("Old Town", "Second City and Wells Street nightlife"),
            ("Hyde Park", "U Chicago and Promontory Point"),
            ("Bucktown", "Bloomingdale Trail adjacent loft living"),
            ("Fulton Market", "former meatpacking turned tech & dining HQ"),
            ("Edgewater", "lakefront vintage at lower rents"),
        ],
        "streets": ["E Illinois St", "E Randolph St", "E Grand Ave", "N Michigan Ave", "W Wacker Dr",
                    "N Clark St", "N Wells St", "S State St", "W Washington Blvd", "W Madison St",
                    "S Wacker Dr", "N LaSalle Dr", "W Fulton Mkt", "N Halsted St", "S Lake Shore Dr"],
    },
    {
        "name": "Houston", "state": "TX", "state_full": "Texas",
        "slug": "houston-tx", "is_featured": True, "mult": 0.85,
        "blurb": "Sprawling neighborhoods, energy-corridor estates, and a fast-growing condo market inside the Loop.",
        "zip_prefix": "770",
        "bbox": (29.55, -95.65, 29.95, -95.25),
        "nbhds": [
            ("Downtown Houston", "high-rises along Discovery Green"),
            ("Midtown", "walkable bars, breweries, and METRORail"),
            ("Montrose", "art museum district and queer cultural anchor"),
            ("River Oaks", "estate neighborhood with luxury rentals nearby"),
            ("The Heights", "historic bungalows and craft beer"),
            ("Galleria", "shopping-mall-adjacent towers"),
            ("Memorial", "wooded corridor close to the Energy Corridor"),
            ("Museum District", "museums, Hermann Park, and Rice University"),
            ("EaDo", "east of downtown lofts and breweries"),
            ("Upper Kirby", "boutique food and mid-rise rental stock"),
        ],
        "streets": ["Westheimer Rd", "Memorial Dr", "Allen Pkwy", "Main St", "Smith St",
                    "Travis St", "Louisiana St", "Bagby St", "Bissonnet St", "Richmond Ave"],
    },
    {
        "name": "Philadelphia", "state": "PA", "state_full": "Pennsylvania",
        "slug": "philadelphia-pa", "is_featured": False, "mult": 1.00,
        "blurb": "Federal-style row houses, brick trinities, and walkable historic neighborhoods.",
        "zip_prefix": "191",
        "bbox": (39.87, -75.28, 40.13, -74.95),
        "nbhds": [
            ("Center City", "Rittenhouse, City Hall, and Avenue of the Arts"),
            ("Old City", "cobblestones, galleries, and Independence Hall"),
            ("Fishtown", "music venues and walk-ups along Frankford"),
            ("Northern Liberties", "lofts, beer gardens, and pet-friendly stock"),
            ("Society Hill", "Federal-era brick rowhouses"),
            ("Graduate Hospital", "young-professional South of South corridor"),
            ("University City", "Penn, Drexel, and Cira Center"),
            ("Bella Vista", "Italian Market and South Philly walk-ups"),
            ("Manayunk", "Schuylkill river towns with main-street shopping"),
            ("Queen Village", "South Street access and historic blocks"),
        ],
        "streets": ["Walnut St", "Chestnut St", "Market St", "Spruce St", "Pine St",
                    "Locust St", "Broad St", "Arch St", "Race St", "Vine St"],
    },
    {
        "name": "Phoenix", "state": "AZ", "state_full": "Arizona",
        "slug": "phoenix-az", "is_featured": True, "mult": 0.90,
        "blurb": "Desert-modern homes, mountain-preserve lots, and a wave of master-planned communities.",
        "zip_prefix": "850",
        "bbox": (33.30, -112.30, 33.70, -111.85),
        "nbhds": [
            ("Downtown Phoenix", "ASU urban campus and light rail spine"),
            ("Roosevelt Row", "arts district with murals and First Fridays"),
            ("Arcadia", "Camelback views and mid-century citrus groves"),
            ("Biltmore", "luxury resorts and high-end mid-rises"),
            ("Camelback East", "executive corridor north of the freeway"),
            ("Tempe", "ASU students and Mill Avenue energy"),
            ("Scottsdale", "Old Town nightlife and golf-resort lifestyle"),
            ("Ahwatukee", "South Mountain hikes and family suburbs"),
            ("Desert Ridge", "master-planned shopping and dining"),
            ("North Mountain", "preserves, parks, and affordable mid-rises"),
        ],
        "streets": ["Central Ave", "Camelback Rd", "Indian School Rd", "McDowell Rd", "Thomas Rd",
                    "Van Buren St", "Washington St", "Roosevelt St", "Bethany Home Rd", "Glendale Ave"],
    },
    {
        "name": "San Antonio", "state": "TX", "state_full": "Texas",
        "slug": "san-antonio-tx", "is_featured": False, "mult": 0.78,
        "blurb": "Spanish-colonial bungalows, hill-country acreage, and an affordable inner-loop housing stock.",
        "zip_prefix": "782",
        "bbox": (29.30, -98.65, 29.65, -98.30),
        "nbhds": [
            ("Downtown", "River Walk and Alamo Plaza"),
            ("Pearl District", "former brewery turned dining destination"),
            ("Alamo Heights", "leafy enclave with top schools"),
            ("Stone Oak", "master-planned hill country suburbs"),
            ("Southtown", "King William historic district and galleries"),
            ("Olmos Park", "century-old mansions and parkland"),
            ("Government Hill", "fast-changing arts corridor"),
            ("Medical Center", "hospital campus with student-heavy stock"),
        ],
        "streets": ["Broadway", "St Mary's St", "Houston St", "Alamo St", "Commerce St",
                    "Market St", "Travis St", "Pecan St", "Crockett St", "Bowie St"],
    },
    {
        "name": "San Diego", "state": "CA", "state_full": "California",
        "slug": "san-diego-ca", "is_featured": True, "mult": 1.55,
        "blurb": "Coastal canyons, mid-century gems, and ocean-view properties from La Jolla to Coronado.",
        "zip_prefix": "921",
        "bbox": (32.65, -117.30, 33.10, -116.95),
        "nbhds": [
            ("Gaslamp Quarter", "downtown nightlife and ballpark proximity"),
            ("Little Italy", "European-style market and high-rises"),
            ("Hillcrest", "queer cultural anchor and Balboa Park edge"),
            ("North Park", "craft beer, Mission Revival cottages"),
            ("South Park", "small-town feel inside the city"),
            ("La Jolla", "ocean cliffs, UCSD, and Torrey Pines"),
            ("Pacific Beach", "boardwalk and Mission Bay"),
            ("Mission Hills", "vintage Spanish bungalows"),
            ("Banker's Hill", "highrise pockets adjacent to Balboa Park"),
            ("Point Loma", "harbor views and military housing"),
        ],
        "streets": ["India St", "5th Ave", "6th Ave", "Park Blvd", "University Ave",
                    "Adams Ave", "El Cajon Blvd", "Convoy St", "Camino del Rio", "Garnet Ave"],
    },
    {
        "name": "Dallas", "state": "TX", "state_full": "Texas",
        "slug": "dallas-tx", "is_featured": True, "mult": 0.95,
        "blurb": "Park Cities estates, Uptown high-rises, and master-planned suburbs.",
        "zip_prefix": "752",
        "bbox": (32.65, -96.95, 32.95, -96.65),
        "nbhds": [
            ("Uptown", "boulevard towers and the McKinney Avenue trolley"),
            ("Downtown", "Klyde Warren Park and arts district"),
            ("Deep Ellum", "live music and Edison brick lofts"),
            ("Bishop Arts", "shopping village in Oak Cliff"),
            ("Lakewood", "White Rock Lake bungalows"),
            ("Highland Park", "trophy-block estates and shopping"),
            ("Knox-Henderson", "boutique retail and bars"),
            ("Lower Greenville", "M Streets adjacent walk-ups"),
            ("Trinity Groves", "industrial-chic west of downtown"),
            ("Las Colinas", "Irving lakeside corporate corridor"),
        ],
        "streets": ["McKinney Ave", "Cole Ave", "Lemmon Ave", "Cedar Springs Rd", "Mockingbird Ln",
                    "Greenville Ave", "Knox St", "Henderson Ave", "Elm St", "Main St"],
    },
    {
        "name": "Austin", "state": "TX", "state_full": "Texas",
        "slug": "austin-tx", "is_featured": True, "mult": 1.20,
        "blurb": "Hill-country sunsets, lakefront retreats, and a thriving tech-fueled market.",
        "zip_prefix": "787",
        "bbox": (30.15, -97.95, 30.55, -97.55),
        "nbhds": [
            ("Downtown Austin", "Rainey Street high-rises and Lady Bird Lake"),
            ("Rainey Street", "former bungalow row turned bar district"),
            ("South Congress", "SoCo shopping and live music"),
            ("Bouldin Creek", "South Austin walk-ups"),
            ("East Austin", "food trucks, breweries, mixed-density growth"),
            ("Hyde Park", "century-old bungalows near UT"),
            ("Mueller", "redeveloped airport master-plan"),
            ("Zilker", "park access and ACL festival adjacent"),
            ("North Loop", "vintage shops and craft coffee"),
            ("Domain", "north Austin retail and tech HQ corridor"),
        ],
        "streets": ["Davis St", "S 1st St", "S Congress Ave", "E 6th St", "Cesar Chavez St",
                    "Guadalupe St", "Lamar Blvd", "Burnet Rd", "Manor Rd", "Riverside Dr"],
    },
    {
        "name": "San Francisco", "state": "CA", "state_full": "California",
        "slug": "san-francisco-ca", "is_featured": True, "mult": 2.20,
        "blurb": "Victorian charm meets Pacific views across the city's distinctive hills.",
        "zip_prefix": "941",
        "bbox": (37.70, -122.51, 37.83, -122.36),
        "nbhds": [
            ("SoMa", "South of Market lofts, museums, tech HQs"),
            ("Mission", "burritos, murals, and 24th Street"),
            ("Mission Bay", "biotech corridor and Chase Center"),
            ("Hayes Valley", "boutiques and Patricia's Green"),
            ("Pacific Heights", "Victorian mansions and views"),
            ("Nob Hill", "cable cars and Grace Cathedral"),
            ("Russian Hill", "Lombard Street and bay vistas"),
            ("North Beach", "Italian cafés and City Lights Books"),
            ("Castro", "historic queer enclave and weekend markets"),
            ("Marina", "Crissy Field views and yuppie bar scene"),
            ("Sunset", "fog-belt residential and ocean access"),
            ("Richmond", "Geary corridor and Golden Gate Park edge"),
        ],
        "streets": ["Market St", "Mission St", "Van Ness Ave", "Folsom St", "Howard St",
                    "Minna St", "Geary Blvd", "Divisadero St", "Valencia St", "Polk St"],
    },
    {
        "name": "Seattle", "state": "WA", "state_full": "Washington",
        "slug": "seattle-wa", "is_featured": True, "mult": 1.55,
        "blurb": "Floating homes, midcentury treasures, and water-and-mountain views in equal measure.",
        "zip_prefix": "981",
        "bbox": (47.50, -122.45, 47.75, -122.20),
        "nbhds": [
            ("Downtown Seattle", "Pike Place adjacent towers"),
            ("Capitol Hill", "queer cultural anchor and Cal Anderson Park"),
            ("Ballard", "fishing-village charm with brewpubs"),
            ("Fremont", "center-of-the-universe quirk along the canal"),
            ("Queen Anne", "Space Needle views and historic homes"),
            ("South Lake Union", "Amazon HQ and trolley line"),
            ("Wallingford", "craftsman bungalows and 45th Street"),
            ("Belltown", "downtown-adjacent condos and nightlife"),
            ("West Seattle", "Alki Beach and ferries"),
            ("Magnolia", "bluff-top single-family and discovery park"),
        ],
        "streets": ["Russell Ave NW", "Dexter Ave N", "5th Ave", "1st Ave", "4th Ave",
                    "Pine St", "Pike St", "Stewart St", "Mercer St", "Westlake Ave N"],
    },
    {
        "name": "Denver", "state": "CO", "state_full": "Colorado",
        "slug": "denver-co", "is_featured": True, "mult": 1.15,
        "blurb": "Mile-high mountain access, modernist new builds, and a walkable urban core.",
        "zip_prefix": "802",
        "bbox": (39.60, -105.10, 39.85, -104.85),
        "nbhds": [
            ("LoDo", "Lower Downtown brick lofts near Union Station"),
            ("RiNo", "River North arts district murals and breweries"),
            ("Capitol Hill", "Victorian rowhouses and shops"),
            ("Cherry Creek", "high-end retail and modern mid-rises"),
            ("Highlands", "32nd Ave restaurants and Sloan's Lake"),
            ("Five Points", "historic jazz corridor"),
            ("Wash Park", "lake-fronted walkable neighborhood"),
            ("Stapleton (Central Park)", "redeveloped airport master-plan"),
            ("Lincoln Park", "Auraria campus adjacent lofts"),
            ("Baker", "antique row and craftsman homes"),
        ],
        "streets": ["17th St", "Larimer St", "Blake St", "Wazee St", "Wynkoop St",
                    "Champa St", "Stout St", "Welton St", "Broadway", "Colfax Ave"],
    },
    {
        "name": "Boston", "state": "MA", "state_full": "Massachusetts",
        "slug": "boston-ma", "is_featured": True, "mult": 1.85,
        "blurb": "Brownstones, river views, and walkable historic neighborhoods with elite universities.",
        "zip_prefix": "021",
        "bbox": (42.25, -71.20, 42.45, -70.95),
        "nbhds": [
            ("Back Bay", "brownstones along Commonwealth Ave"),
            ("Beacon Hill", "gas lamps and cobblestones"),
            ("South End", "Victorian rowhouses and SoWa Open Market"),
            ("North End", "Italian cafés and historic streets"),
            ("Fenway", "ballpark adjacent and student-heavy"),
            ("Seaport", "Innovation District towers and harbor"),
            ("Cambridge", "Harvard and MIT townie favorites"),
            ("Allston", "BU adjacent budget rentals"),
            ("Brookline", "JFK-era residential close to the Green Line"),
            ("Jamaica Plain", "Pondside neighborhood and arts scene"),
        ],
        "streets": ["Commonwealth Ave", "Newbury St", "Boylston St", "Tremont St", "Beacon St",
                    "Charles St", "Mass Ave", "Huntington Ave", "Washington St", "Atlantic Ave"],
    },
    {
        "name": "Atlanta", "state": "GA", "state_full": "Georgia",
        "slug": "atlanta-ga", "is_featured": True, "mult": 1.05,
        "blurb": "Buckhead estates, intown bungalows, and walkable BeltLine-adjacent townhouses.",
        "zip_prefix": "303",
        "bbox": (33.65, -84.55, 33.90, -84.30),
        "nbhds": [
            ("Midtown", "Piedmont Park and the High Museum"),
            ("Buckhead", "luxury high-rises and Phipps Plaza"),
            ("Old Fourth Ward", "BeltLine Eastside Trail loft conversions"),
            ("Inman Park", "Victorian rowhouses and Krog Street Market"),
            ("Virginia-Highland", "leafy walkable village"),
            ("West End", "historic district and Mercedes-Benz Stadium edge"),
            ("Downtown Atlanta", "central business district towers"),
            ("Westside", "Westside Provisions and TopGolf adjacent"),
            ("Decatur", "small-city square with strong schools"),
            ("Castleberry Hill", "arts district lofts"),
        ],
        "streets": ["Peachtree St", "Piedmont Rd", "West Paces Ferry Rd", "Roswell Rd",
                    "Marietta St", "Spring St", "Juniper St", "Edgewood Ave", "Highland Ave",
                    "Ponce de Leon Ave"],
    },
    {
        "name": "Miami", "state": "FL", "state_full": "Florida",
        "slug": "miami-fl", "is_featured": True, "mult": 1.65,
        "blurb": "Waterfront condos, palm-lined streets, and an international design scene.",
        "zip_prefix": "331",
        "bbox": (25.65, -80.35, 25.90, -80.10),
        "nbhds": [
            ("Brickell", "Manhattan-style towers and Biscayne views"),
            ("Downtown Miami", "Bayfront Park and condo skyline"),
            ("Edgewater", "Margaret Pace Park waterfront"),
            ("Wynwood", "murals and brewery-led growth"),
            ("Coconut Grove", "leafy bayside village"),
            ("Coral Gables", "Mediterranean architecture and Miracle Mile"),
            ("Mid-Beach", "Collins Avenue resorts and condos"),
            ("South Beach", "Art Deco and Ocean Drive"),
            ("Little Havana", "Cuban heritage and Calle Ocho"),
            ("Aventura", "shopping mall adjacent high-rises"),
        ],
        "streets": ["Brickell Bay Dr", "S Bayshore Dr", "Biscayne Blvd Way", "Biscayne Blvd",
                    "Alton Rd", "Collins Ave", "Ocean Dr", "Washington Ave", "SW 27th Ave",
                    "Coral Way"],
    },
    {
        "name": "Washington", "state": "DC", "state_full": "District of Columbia",
        "slug": "washington-dc", "is_featured": True, "mult": 1.75,
        "blurb": "Federal-style row houses, leafy embassy quarters, and a tightly-held historic market.",
        "zip_prefix": "200",
        "bbox": (38.80, -77.12, 38.99, -76.91),
        "nbhds": [
            ("Dupont Circle", "embassy row and walkable cafés"),
            ("Logan Circle", "P Street rowhouses and 14th Street boutiques"),
            ("U Street", "historic Black Broadway corridor"),
            ("Adams Morgan", "diverse food scene and 18th Street"),
            ("Capitol Hill", "row houses near the Capitol"),
            ("Georgetown", "cobblestone streets and Potomac views"),
            ("NoMa", "near Union Station mid-rises"),
            ("Foggy Bottom", "GW University and State Department"),
            ("Penn Quarter", "Capital One Arena and dining"),
            ("Shaw", "Howard adjacent rowhouses"),
        ],
        "streets": ["Connecticut Ave NW", "Massachusetts Ave NW", "K St NW", "P St NW",
                    "14th St NW", "U St NW", "M St NW", "Pennsylvania Ave SE",
                    "Wisconsin Ave NW", "Florida Ave NW"],
    },
    {
        "name": "Portland", "state": "OR", "state_full": "Oregon",
        "slug": "portland-or", "is_featured": True, "mult": 1.10,
        "blurb": "Craftsman bungalows, Pearl District lofts, and forested west-hills properties.",
        "zip_prefix": "972",
        "bbox": (45.45, -122.75, 45.60, -122.50),
        "nbhds": [
            ("Pearl District", "former rail yard turned brick lofts"),
            ("Downtown Portland", "Tom McCall waterfront and PSU"),
            ("Northwest District", "23rd Avenue shopping village"),
            ("Alphabet District", "Tree-lined NW residential"),
            ("Hawthorne", "vintage shops and bungalows"),
            ("Mississippi Avenue", "renovated commercial corridor"),
            ("Alberta Arts", "monthly art walk and small businesses"),
            ("Sellwood", "antique row and Oaks Park"),
            ("Belmont", "café-lined SE residential"),
            ("Goose Hollow", "Stadium-adjacent and MAX-served"),
        ],
        "streets": ["NW 23rd Ave", "SE Hawthorne Blvd", "SE Division St", "NW Lovejoy St",
                    "N Mississippi Ave", "NE Alberta St", "SE Belmont St", "NW Glisan St",
                    "NW Everett St", "SW Morrison St"],
    },
    {
        "name": "Nashville", "state": "TN", "state_full": "Tennessee",
        "slug": "nashville-tn", "is_featured": False, "mult": 1.00,
        "blurb": "Belle Meade estates, restored East Nashville cottages, and a fast-growing condo skyline.",
        "zip_prefix": "372",
        "bbox": (36.05, -86.95, 36.30, -86.65),
        "nbhds": [
            ("Downtown", "Broadway honky-tonks and Bridgestone Arena"),
            ("Gulch", "high-rise growth and Frothy Monkey"),
            ("Germantown", "century-old brick rowhouses"),
            ("East Nashville", "restored cottages and Five Points"),
            ("12 South", "boutique shopping village"),
            ("Sylvan Park", "leafy bungalows and Richland Park"),
            ("Belmont-Hillsboro", "Belmont University adjacent"),
            ("SoBro", "south of Broadway lofts"),
            ("Wedgewood-Houston", "art galleries and breweries"),
            ("West End", "Vanderbilt corridor"),
        ],
        "streets": ["Broadway", "Demonbreun St", "Church St", "Charlotte Ave", "West End Ave",
                    "Music Row", "Belmont Blvd", "12th Ave S", "Gallatin Pike", "Eastland Ave"],
    },
    {
        "name": "Charlotte", "state": "NC", "state_full": "North Carolina",
        "slug": "charlotte-nc", "is_featured": False, "mult": 1.00,
        "blurb": "Tree-lined Myers Park estates, Uptown condos, and lake-access homes north of the city.",
        "zip_prefix": "282",
        "bbox": (35.15, -80.95, 35.35, -80.70),
        "nbhds": [
            ("Uptown", "First/Third Ward banking towers"),
            ("South End", "rail trail and breweries"),
            ("NoDa", "arts district and live music"),
            ("Plaza Midwood", "vintage shops and bungalows"),
            ("Dilworth", "century-old Craftsman homes"),
            ("Myers Park", "estate neighborhoods and Queens U"),
            ("Elizabeth", "Pecan Avenue tree canopy"),
            ("Wesley Heights", "trolley-line cottages"),
            ("Optimist Park", "fast-growing post-industrial"),
            ("Ballantyne", "south Charlotte master-planned"),
        ],
        "streets": ["Tryon St", "Trade St", "Stonewall St", "Caldwell St", "Davidson St",
                    "Camden Rd", "South Blvd", "Park Rd", "Providence Rd", "Selwyn Ave"],
    },
    {
        "name": "Tampa", "state": "FL", "state_full": "Florida",
        "slug": "tampa-fl", "is_featured": False, "mult": 0.95,
        "blurb": "Hyde Park bungalows, Davis Islands waterfront homes, and a fast-growing downtown condo market.",
        "zip_prefix": "336",
        "bbox": (27.90, -82.55, 28.10, -82.35),
        "nbhds": [
            ("Downtown", "Tampa Riverwalk and Sparkman Wharf"),
            ("Channelside", "Amalie Arena adjacent towers"),
            ("Hyde Park", "Victorian bungalows and SoHo"),
            ("Ybor City", "historic Cuban district and cobblestones"),
            ("Davis Islands", "private airport and waterfront residential"),
            ("Westshore", "business district mid-rises"),
            ("Seminole Heights", "craft beer and bungalow revival"),
            ("South Tampa", "Bayshore and MacDill access"),
            ("Carrollwood", "north Tampa established suburbia"),
            ("Riverside Heights", "near downtown bungalows"),
        ],
        "streets": ["Bayshore Blvd", "Kennedy Blvd", "Dale Mabry Hwy", "Nebraska Ave",
                    "Florida Ave", "Howard Ave", "Armenia Ave", "Channelside Dr",
                    "7th Ave", "Westshore Blvd"],
    },
    {
        "name": "Minneapolis", "state": "MN", "state_full": "Minnesota",
        "slug": "minneapolis-mn", "is_featured": False, "mult": 0.95,
        "blurb": "Lake-district bungalows, Mill District condos, and a stable single-family market.",
        "zip_prefix": "554",
        "bbox": (44.85, -93.40, 45.10, -93.15),
        "nbhds": [
            ("North Loop", "Mill City converted brick warehouses"),
            ("Downtown", "Nicollet Mall and the skyway system"),
            ("Uptown", "Lake Bde Maka Ska adjacent"),
            ("Northeast", "arts district and craft breweries"),
            ("Loring Park", "downtown's residential pocket"),
            ("Lyndale", "south-side walkability"),
            ("Whittier", "Eat Street corridor"),
            ("Linden Hills", "leafy 44th Street village"),
            ("Cedar-Riverside", "U of M's West Bank"),
            ("Mill District", "river-fronting condos"),
        ],
        "streets": ["Nicollet Ave", "Hennepin Ave", "Marquette Ave", "Lyndale Ave",
                    "Lake St", "Washington Ave", "1st Ave N", "4th St N", "Park Ave",
                    "Stevens Ave"],
    },
]


# Buildings per metro distribution -> totals around 420
BLDG_PER_METRO = {
    "New York": 36, "Los Angeles": 32, "Chicago": 28, "Houston": 18,
    "Philadelphia": 16, "Phoenix": 18, "San Antonio": 14, "San Diego": 18,
    "Dallas": 20, "Austin": 22, "San Francisco": 26, "Seattle": 24,
    "Denver": 18, "Boston": 22, "Atlanta": 20, "Miami": 24,
    "Washington": 22, "Portland": 18, "Nashville": 16, "Charlotte": 14,
    "Tampa": 16, "Minneapolis": 14,
}


# Local building photo files (slug stems) — populated by harvest step.
PHOTO_SLUGS = []
if os.path.isdir(PHOTOS_DIR):
    PHOTO_SLUGS = sorted(
        f[:-4] for f in os.listdir(PHOTOS_DIR) if f.endswith(".jpg")
    )
# Group by metro prefix so seeded buildings get city-coherent photos.
PHOTO_BY_METRO = {
    "nyc": [s for s in PHOTO_SLUGS if s.startswith("nyc-")],
    "la":  [s for s in PHOTO_SLUGS if s.startswith("la-")],
    "chi": [s for s in PHOTO_SLUGS if s.startswith("chi-")],
    "aus": [s for s in PHOTO_SLUGS if s.startswith("aus-")],
    "sf":  [s for s in PHOTO_SLUGS if s.startswith("sf-")],
    "sea": [s for s in PHOTO_SLUGS if s.startswith("sea-")],
    "mia": [s for s in PHOTO_SLUGS if s.startswith("mia-")],
}
METRO_PHOTO_KEY = {
    "New York": "nyc", "Los Angeles": "la", "Chicago": "chi", "Austin": "aus",
    "San Francisco": "sf", "Seattle": "sea", "Miami": "mia",
    # Others fall back to mixed pool:
}
DEFAULT_PHOTO_POOL = PHOTO_SLUGS or ["nyc-aro-1"]


def _photos_for(city, idx):
    """Pick a deterministic ordered list of 12-18 photo URLs for a building."""
    pool = PHOTO_BY_METRO.get(METRO_PHOTO_KEY.get(city, ""), DEFAULT_PHOTO_POOL)
    if not pool:
        pool = DEFAULT_PHOTO_POOL
    n = 12 + (_h("photos", city, idx) % 7)
    out = []
    for i in range(n):
        slug = pool[(_h("photo", city, idx, i) % len(pool))]
        out.append(f"/static/images/buildings/{slug}.jpg")
    return out


# ─── Building-name building blocks ───────────────────────────────────────────


NAME_PREFIXES = [
    "The", "One", "The", "The", "", "", "The", "Park", "The"
]
NAME_BASES = [
    "Maxwell", "Aldyn", "Ascent", "Vantage", "Beacon", "Atlas", "Lumen",
    "Solstice", "Meridian", "Crescent", "Helios", "Aria", "Vista",
    "Cascade", "Element", "Modera", "Avalon", "Aspen", "Edge", "Skyline",
    "Pacific", "Harbor", "Reserve", "Foundry", "Citizen", "Boulevard",
    "Rowan", "Crest", "Liberty", "Sterling", "Camden", "Lincoln", "Madison",
    "Wynwood", "Riverside", "Highline", "Westgate", "Eastline", "Northshore",
    "Southview", "Mosaic", "Lyric", "Symphony", "Prism", "Halcyon",
    "Junction", "Lofts", "Yards", "Quarter", "Commons", "Heights", "Place",
    "Tower", "Vue", "Bend", "Ridge", "Walk", "Hub", "Standard", "Anthem",
]


AMENITY_POOL = [
    "Resort-Style Pool", "Rooftop Sun Deck", "24-Hour Fitness Center",
    "Yoga Studio", "Co-working Lounge", "Pet Spa", "Bike Storage",
    "EV Charging Stations", "Package Lockers", "Concierge", "Business Center",
    "Outdoor Grills", "Fire Pit", "Dog Park", "Game Room", "Theater Room",
    "Sauna", "Steam Room", "Children's Playroom", "Library Lounge",
    "Pickleball Court", "Tennis Court", "Basketball Half-Court",
    "Golf Simulator", "Wine Cellar", "Recording Studio", "Maker Space",
    "Sky Lounge", "Skybridge", "Garden Courtyard",
]


CONTACT_PHONES = [
    "(212) 555-0140", "(212) 555-0182", "(323) 555-0118", "(415) 555-0220",
    "(312) 555-0144", "(305) 555-0172", "(206) 555-0188", "(512) 555-0166",
    "(202) 555-0119", "(720) 555-0149", "(404) 555-0177", "(617) 555-0151",
    "(214) 555-0195", "(602) 555-0188", "(503) 555-0124", "(615) 555-0166",
    "(704) 555-0143", "(813) 555-0119", "(612) 555-0107", "(619) 555-0188",
    "(713) 555-0152", "(210) 555-0124", "(215) 555-0177",
]


PROP_MANAGERS = [
    "Greystar Real Estate Partners", "Equity Residential", "AvalonBay Communities",
    "Camden Property Trust", "Bozzuto", "The Bozzuto Group", "TF Cornerstone",
    "Related Companies", "Lincoln Property Company", "Cushman & Wakefield",
    "JLL Residential", "Alliance Residential", "Trammell Crow Residential",
    "Mill Creek Residential", "Pinnacle Property Management", "FPI Management",
    "Riverstone Residential",
]


PROP_TYPES = ["Apartment", "Apartment", "Apartment", "Condo", "Townhouse"]


# ─── Seed functions ──────────────────────────────────────────────────────────


def seed_cities():
    if City.query.count() > 0:
        return
    cities = []
    for m in METROS:
        c = City(
            slug=m["slug"], name=m["name"], state=m["state"],
            state_full=m["state_full"], blurb=m["blurb"],
            hero_image=f"/static/images/buildings/{(PHOTO_SLUGS[_h('hero', m['name']) % max(1, len(PHOTO_SLUGS))]) if PHOTO_SLUGS else 'nyc-aldyn-1'}.jpg",
            avg_rent_studio=int(1500 * m["mult"]),
            avg_rent_1br=int(1900 * m["mult"]),
            avg_rent_2br=int(2700 * m["mult"]),
            avg_rent_3br=int(3600 * m["mult"]),
            is_featured=m["is_featured"],
        )
        cities.append(c)
        db.session.add(c)
    db.session.flush()

    # neighborhoods
    for m in METROS:
        city = City.query.filter_by(slug=m["slug"]).first()
        for name, blurb in m["nbhds"]:
            n = Neighborhood(
                city_id=city.id,
                slug=_slug(name),
                name=name,
                blurb=f"{name} — {blurb}.",
                walk_score=_r(55, 99, "ws", m["name"], name),
                transit_score=_r(35, 99, "ts", m["name"], name),
                bike_score=_r(40, 95, "bs", m["name"], name),
                sound_score=_r(40, 95, "ss", m["name"], name),
                avg_rent=int(2200 * m["mult"]),
            )
            db.session.add(n)
    db.session.commit()


def _make_address(m, idx):
    """Stable street address inside metro bounding box."""
    street = _pick(m["streets"], "street", m["name"], idx)
    num = 100 + (_h("num", m["name"], idx) % 9700)
    return f"{num} {street}"


def _make_zip(m, idx):
    return f"{m['zip_prefix']}{_r(0, 99, 'zip', m['name'], idx):02d}"


def _make_coords(m, idx):
    lat0, lng0, lat1, lng1 = m["bbox"]
    h = _h("lat", m["name"], idx)
    lat = lat0 + ((h % 10000) / 10000.0) * (lat1 - lat0)
    h = _h("lng", m["name"], idx)
    lng = lng0 + ((h % 10000) / 10000.0) * (lng1 - lng0)
    return round(lat, 6), round(lng, 6)


def _make_building_name(m, idx):
    if _h("namemode", m["name"], idx) % 5 == 0:
        # Address-style name like "1214 Fifth Avenue"
        street = _pick(m["streets"], "street", m["name"], idx)
        num = 100 + (_h("num", m["name"], idx) % 9700)
        return f"{num} {street}"
    base = _pick(NAME_BASES, "base", m["name"], idx)
    prefix = _pick(NAME_PREFIXES, "pre", m["name"], idx)
    suffix_pool = ["", "", "Residences", "Apartments", "Lofts", "Tower", "at " + m["name"]]
    suffix = _pick(suffix_pool, "suf", m["name"], idx)
    name = " ".join(p for p in [prefix, base, suffix] if p).strip()
    return name


def seed_buildings():
    if Building.query.count() > 0:
        return

    # Quick lookups: city.id + neighborhoods for each metro.
    city_map = {c.name: c for c in City.query.all()}

    for m in METROS:
        city = city_map[m["name"]]
        nbhds = Neighborhood.query.filter_by(city_id=city.id).all()
        if not nbhds:
            continue
        count = BLDG_PER_METRO.get(m["name"], 12)
        for i in range(count):
            name = _make_building_name(m, i)
            address = _make_address(m, i)
            zipc = _make_zip(m, i)
            lat, lng = _make_coords(m, i)
            nbhd = nbhds[_h("nbhd", m["name"], i) % len(nbhds)]
            slug_base = f"{_slug(name)}-{m['slug']}-{i:03d}"
            mult = m["mult"]
            # Bed/rent envelopes vary by building type.
            t_roll = _h("type", m["name"], i) % 10
            if t_roll == 0:
                prop_type = "Townhouse"
                beds_min, beds_max = 2, 4
            elif t_roll == 1:
                prop_type = "Condo"
                beds_min, beds_max = 1, 3
            else:
                prop_type = "Apartment"
                beds_min = 0 if _h("hasstudio", m["name"], i) % 2 == 0 else 1
                beds_max = max(beds_min + 1, 2 + (_h("bmx", m["name"], i) % 3))

            rent_low = int((1100 + _r(0, 700, "rl", m["name"], i)) * mult)
            rent_high = int(rent_low * (1.6 + (_r(0, 80, "rh", m["name"], i) / 100.0)))

            sqft_low = 380 + (_h("sqfl", m["name"], i) % 240)
            sqft_high = sqft_low + 500 + (_h("sqfh", m["name"], i) % 900)

            stories = 4 + (_h("st", m["name"], i) % 50)
            year_built = 1965 + (_h("yb", m["name"], i) % 60)
            total_units = max(8, _r(40, 480, "tu", m["name"], i))

            walk_score = 35 + (_h("ws", m["name"], i) % 64)
            transit_score = 30 + (_h("tx", m["name"], i) % 69)
            bike_score = 30 + (_h("bs", m["name"], i) % 64)
            sound_score = 30 + (_h("so", m["name"], i) % 65)

            is_luxury = (_h("lx", m["name"], i) % 5 == 0)
            is_new = (_h("nw", m["name"], i) % 8 == 0)

            # Amenity selection (8-15)
            n_amen = 8 + (_h("amen", m["name"], i) % 8)
            amens = []
            for k in range(n_amen):
                a = AMENITY_POOL[_h("am", m["name"], i, k) % len(AMENITY_POOL)]
                if a not in amens:
                    amens.append(a)

            # Discrete flags drawn from amenity selection + extra rolls.
            has_pool = "Resort-Style Pool" in amens or (_h("pool", m["name"], i) % 3 == 0)
            has_gym = "24-Hour Fitness Center" in amens or (_h("gym", m["name"], i) % 2 == 0)
            has_rooftop = "Rooftop Sun Deck" in amens or "Sky Lounge" in amens
            has_ev = "EV Charging Stations" in amens or (_h("ev", m["name"], i) % 4 == 0)
            has_parking = (_h("park", m["name"], i) % 5 != 0)
            has_doorman = is_luxury or (_h("dm", m["name"], i) % 6 == 0)
            has_dog_park = "Dog Park" in amens or (_h("dp", m["name"], i) % 5 == 0)
            has_concierge = "Concierge" in amens or is_luxury
            has_business_center = "Business Center" in amens or (_h("bc", m["name"], i) % 3 == 0)
            has_storage = (_h("sg", m["name"], i) % 3 == 0)
            has_elevator = stories >= 4
            has_laundry_in_unit = (_h("lun", m["name"], i) % 6 != 0)
            is_furnished = (_h("furn", m["name"], i) % 12 == 0)

            is_student = (_h("stu", m["name"], i) % 18 == 0)
            is_senior = (_h("sen", m["name"], i) % 22 == 0) and not is_student
            is_military = (_h("mil", m["name"], i) % 25 == 0) and not (is_student or is_senior)

            pets = (_h("pet", m["name"], i) % 10 != 0)
            dogs_allowed = pets and (_h("dogs", m["name"], i) % 6 != 0)
            cats_allowed = pets and (_h("cats", m["name"], i) % 7 != 0)
            dog_weight_limit = (40 + (_h("dwl", m["name"], i) % 60)) if dogs_allowed else 0

            lease_terms = []
            lease_pool = ["6 months", "9 months", "12 months", "13 months", "15 months", "Month-to-month"]
            for k in range(2 + (_h("lt", m["name"], i) % 3)):
                lt = lease_pool[_h("lpk", m["name"], i, k) % len(lease_pool)]
                if lt not in lease_terms:
                    lease_terms.append(lt)

            gallery = _photos_for(m["name"], i)
            hero = gallery[0]

            listed = datetime(2026, 5, 27) - timedelta(days=_h("ld", m["name"], i) % 120)

            description = (
                f"{name} sits at {address} in {m['name']}'s {nbhd.name} neighborhood. "
                f"This {stories}-story {prop_type.lower()} community was built in {year_built} "
                f"and offers {total_units} residences ranging from "
                f"{'studios' if beds_min == 0 else f'{beds_min}-bedroom'} to {beds_max}-bedroom homes. "
                f"Residents enjoy {', '.join(amens[:4])}, and views over the surrounding area. "
                f"{nbhd.blurb}"
            )

            rating_avg = round(3.4 + (_h("ra", m["name"], i) % 16) / 10.0, 1)
            review_count = 4 + (_h("rc", m["name"], i) % 28)

            b = Building(
                slug=slug_base,
                name=name,
                address=address,
                city=m["name"], state=m["state"], zip=zipc,
                neighborhood=nbhd.name, neighborhood_id=nbhd.id,
                latitude=lat, longitude=lng,
                property_type=prop_type, year_built=year_built,
                total_units=total_units, stories=stories,
                rent_min=rent_low, rent_max=rent_high,
                beds_min=beds_min, beds_max=beds_max,
                sqft_min=sqft_low, sqft_max=sqft_high,
                description=description, hero_image=hero,
                gallery_images=json.dumps(gallery),
                walk_score=walk_score, transit_score=transit_score,
                bike_score=bike_score, sound_score=sound_score,
                pet_friendly=pets, cats_allowed=cats_allowed, dogs_allowed=dogs_allowed,
                dog_weight_limit=dog_weight_limit,
                pet_deposit=(300 + (_h("pd", m["name"], i) % 400)) if pets else 0,
                pet_rent=(25 + (_h("pr", m["name"], i) % 50)) if pets else 0,
                has_parking=has_parking,
                parking_type=("Garage" if has_parking and (_h("pt", m["name"], i) % 2 == 0) else "Surface" if has_parking else ""),
                parking_fee=(_r(0, 350, "pf", m["name"], i)) if has_parking else 0,
                has_pool=has_pool, has_gym=has_gym, has_doorman=has_doorman,
                has_elevator=has_elevator, has_rooftop=has_rooftop,
                has_ev_charging=has_ev,
                has_laundry_in_unit=has_laundry_in_unit,
                has_concierge=has_concierge,
                has_business_center=has_business_center,
                has_dog_park=has_dog_park, has_storage=has_storage,
                is_furnished=is_furnished,
                is_student_housing=is_student, is_senior_housing=is_senior,
                is_military_housing=is_military, is_luxury=is_luxury,
                amenities=json.dumps(amens),
                lease_terms=json.dumps(lease_terms),
                deposit=int(rent_low * (0.5 + (_h("dep", m["name"], i) % 5) / 10.0)),
                app_fee=35 + (_h("af", m["name"], i) % 65),
                admin_fee=150 + (_h("adm", m["name"], i) % 200),
                property_manager=_pick(PROP_MANAGERS, "pm", m["name"], i),
                contact_phone=_pick(CONTACT_PHONES, "cp", m["name"], i),
                contact_email=f"leasing@{_slug(name) or 'community'}.com",
                tour_url=f"https://example.com/tour/{slug_base}",
                has_3d_tour=(_h("tour", m["name"], i) % 2 == 0),
                rating_avg=rating_avg, review_count=review_count,
                listed_at=listed, is_new=is_new,
            )
            db.session.add(b)
    db.session.commit()


def seed_floor_plans_units():
    if FloorPlan.query.count() > 0:
        return
    for b in Building.query.all():
        n_plans = 5 + (_h("plans", b.slug) % 8)  # 5-12 plans
        plans_to_make = []
        # Build beds set so the range of plans hits beds_min..beds_max.
        beds_set = list(range(b.beds_min, b.beds_max + 1))
        if not beds_set:
            beds_set = [b.beds_min]
        per_bed = max(1, n_plans // len(beds_set))
        for bed in beds_set:
            for j in range(per_bed):
                plans_to_make.append((bed, j))
        # Fill any remainder
        while len(plans_to_make) < n_plans:
            plans_to_make.append((beds_set[len(plans_to_make) % len(beds_set)], 99))
        plans_to_make = plans_to_make[:n_plans]

        plan_objs = []
        for k, (bed, j) in enumerate(plans_to_make):
            label = "S" if bed == 0 else f"{bed}BR"
            variant = chr(ord("A") + (_h("var", b.slug, k) % 6))
            name = f"Plan {label}-{variant}"
            slug = _slug(name) + f"-{k}"
            sqft_low_b = max(380, b.sqft_min + (_h("psqfl", b.slug, k) % 220) - 100)
            if bed == 0:
                sqft_lo = 400 + (_h("psl", b.slug, k) % 220)
                sqft_hi = sqft_lo + 60 + (_h("psh", b.slug, k) % 120)
            else:
                sqft_lo = 500 + bed * 250 + (_h("psl2", b.slug, k) % 140)
                sqft_hi = sqft_lo + 80 + (_h("psh2", b.slug, k) % 200)
            # Plan rent within the building envelope, scaled by beds.
            anchor = b.rent_min if bed == b.beds_min else b.rent_min + (b.rent_max - b.rent_min) * (bed - b.beds_min) // max(1, (b.beds_max - b.beds_min))
            rent_lo = max(b.rent_min, anchor - (_h("pra", b.slug, k) % 300))
            rent_hi = min(b.rent_max, anchor + 200 + (_h("prb", b.slug, k) % 400))
            if rent_hi < rent_lo:
                rent_hi = rent_lo + 100
            avail = 1 + (_h("pav", b.slug, k) % 6)
            baths = 1.0 if bed <= 1 else (1.5 if bed == 2 else 2.0)
            fp = FloorPlan(
                building_id=b.id, slug=slug, name=name,
                beds=bed, baths=baths,
                sqft_min=sqft_lo, sqft_max=sqft_hi,
                rent_min=rent_lo, rent_max=rent_hi,
                available_count=avail,
                plan_image=f"/static/icons/floorplan-{label.lower()}.svg",
                description=f"{label} floor plan with {sqft_lo}-{sqft_hi} sf, {baths:g} bath, and modern finishes.",
            )
            db.session.add(fp)
            plan_objs.append(fp)
        db.session.flush()

        # Units: 6-30 per building, distributed across plans.
        n_units = 6 + (_h("units", b.slug) % 25)
        for u in range(n_units):
            fp = plan_objs[_h("upu", b.slug, u) % len(plan_objs)]
            unit_floor = 1 + (_h("uf", b.slug, u) % max(1, b.stories))
            # Unit numbers like "1204", "PH-A", "GFloor-3"
            if unit_floor >= b.stories and (_h("ph", b.slug, u) % 4 == 0):
                unit_number = f"PH-{chr(ord('A') + (u % 8))}"
            else:
                unit_number = f"{unit_floor:02d}{(u + 1):02d}"
            sqft = fp.sqft_min + (_h("usqf", b.slug, u) % max(1, fp.sqft_max - fp.sqft_min + 1))
            rent = fp.rent_min + (_h("ur", b.slug, u) % max(1, fp.rent_max - fp.rent_min + 1))
            deposit = max(500, int(rent * (0.5 + (_h("ud", b.slug, u) % 5) / 10.0)))
            # available_date within next 90 days of fixed seed-anchor 2026-05-27
            offset_days = _h("uad", b.slug, u) % 90
            avail_date = (date(2026, 5, 27) + timedelta(days=offset_days)).isoformat()
            ltrm = ["12 months", "9 months", "13 months"]
            unit_lease = [ltrm[_h("ult", b.slug, u, k) % len(ltrm)] for k in range(2)]
            unit_lease = list(dict.fromkeys(unit_lease))
            view_pool = ["Skyline", "Courtyard", "Park", "Garden", "Pool", "City", "Water"]
            view = view_pool[_h("uv", b.slug, u) % len(view_pool)]
            is_featured = (_h("uft", b.slug, u) % 8 == 0)

            unit = Unit(
                building_id=b.id, floor_plan_id=fp.id,
                unit_number=unit_number, floor=unit_floor,
                beds=fp.beds, baths=fp.baths, sqft=sqft,
                rent=rent, deposit=deposit,
                available_date=avail_date,
                lease_terms=json.dumps(unit_lease),
                is_available=True, is_featured=is_featured, view=view,
            )
            db.session.add(unit)
    db.session.commit()


def seed_schools():
    if School.query.count() > 0:
        return
    school_name_pool_elem = ["Lincoln Elementary", "Roosevelt Elementary",
                             "Jefferson Elementary", "Washington Elementary",
                             "Madison Elementary", "Hamilton Elementary",
                             "Adams Elementary", "Kennedy Elementary",
                             "Riverside Elementary", "Cesar Chavez Elementary",
                             "Maya Angelou Elementary", "Harriet Tubman Elementary"]
    school_name_pool_mid = ["Lincoln Middle School", "Roosevelt Middle School",
                            "Eastside Middle School", "Westside Middle School",
                            "Liberty Middle School", "Magnolia Middle School",
                            "Hillcrest Middle School", "Crestview Middle School"]
    school_name_pool_high = ["Central High School", "North High School",
                             "South High School", "East High School", "West High School",
                             "Lincoln High School", "Liberty High School",
                             "Mission High School", "Pacific High School",
                             "Cosmopolitan High School"]

    for m in METROS:
        n_per_metro = 6
        for i in range(n_per_metro):
            if i < 3:
                pool = school_name_pool_elem; level = "Elementary"; grades = "K-5"; sc = 380
            elif i < 5:
                pool = school_name_pool_mid; level = "Middle"; grades = "6-8"; sc = 620
            else:
                pool = school_name_pool_high; level = "High"; grades = "9-12"; sc = 1450
            name = pool[_h("sname", m["name"], i) % len(pool)] + f" — {m['name']}"
            slug = _slug(name) + f"-{m['state'].lower()}-{i}"
            rating = 5 + (_h("sr", m["name"], i) % 6)  # 5-10
            stype_pool = ["Public", "Public", "Public", "Charter", "Private"]
            stype = stype_pool[_h("sty", m["name"], i) % len(stype_pool)]
            district = f"{m['name']} {('Unified' if m['state'] == 'CA' else 'Public Schools')}"
            ratio = round(12 + (_h("sratio", m["name"], i) % 12) / 1.5, 1)
            s = School(
                slug=slug, name=name, grade_level=level, grades=grades,
                type=stype, rating=rating, district=district,
                city=m["name"], state=m["state"],
                student_count=sc + (_h("sc", m["name"], i) % 220),
                student_teacher_ratio=ratio,
                description=f"{name} serves grades {grades} in the {district}. "
                            f"GreatSchools-style rating: {rating}/10.",
            )
            db.session.add(s)
    db.session.commit()


def seed_building_relations():
    """Each building gets 3-5 nearby schools and 8-15 POIs."""
    if BuildingSchool.query.count() > 0 and POI.query.count() > 0:
        return

    # Cache schools by metro
    schools_by_metro = {}
    for s in School.query.all():
        schools_by_metro.setdefault((s.city, s.state), []).append(s)

    GROCERY = ["Trader Joe's", "Whole Foods Market", "Safeway", "Kroger",
               "Sprouts Farmers Market", "Erewhon", "Publix", "Ralphs",
               "H-E-B", "Wegmans"]
    PARKS = ["Riverside Park", "Town Square", "Memorial Park", "Civic Center Park",
             "Greenway Park", "Lakeside Park", "Promenade Park",
             "Veterans Memorial Park"]
    RESTAUR = ["Sweetgreen", "Joe's Coffee", "Tartine Bakery", "Shake Shack",
               "Roberta's Pizza", "Blue Bottle Coffee", "Le Pain Quotidien",
               "Tacos El Pastor", "Pho 24", "Hai Di Lao"]
    TRANSIT = ["MetroBus stop", "Light Rail station", "Subway stop",
               "Commuter Rail station", "Streetcar stop", "BRT stop"]

    for b in Building.query.all():
        schs = schools_by_metro.get((b.city, b.state), [])
        if schs:
            # 3-5 schools sampled deterministically
            n = 3 + (_h("nsch", b.slug) % 3)
            picks = []
            for i in range(n):
                s = schs[_h("psch", b.slug, i) % len(schs)]
                if s.id in picks:
                    continue
                picks.append(s.id)
                bs = BuildingSchool(building_id=b.id, school_id=s.id,
                                    distance_mi=round(0.2 + (_h("d", b.slug, i) % 28) / 10.0, 1))
                db.session.add(bs)

        # POIs
        n_pois = 8 + (_h("npoi", b.slug) % 8)
        for i in range(n_pois):
            cat_roll = _h("cat", b.slug, i) % 10
            if cat_roll < 3:
                cat = "Restaurant"; nm = RESTAUR[_h("rn", b.slug, i) % len(RESTAUR)]
            elif cat_roll < 5:
                cat = "Grocery"; nm = GROCERY[_h("gn", b.slug, i) % len(GROCERY)]
            elif cat_roll < 7:
                cat = "Park"; nm = PARKS[_h("pn", b.slug, i) % len(PARKS)]
            elif cat_roll < 9:
                cat = "Transit"; nm = TRANSIT[_h("tn", b.slug, i) % len(TRANSIT)]
            else:
                cat = "Coffee"; nm = ["Starbucks", "Blue Bottle", "Stumptown",
                                      "Philz Coffee", "La Colombe"][_h("cn", b.slug, i) % 5]
            dist = round((1 + (_h("pd2", b.slug, i) % 24)) / 10.0, 1)
            walk = max(2, int(dist * 18))
            db.session.add(POI(building_id=b.id, name=nm, category=cat,
                               distance_mi=dist, walk_min=walk))
    db.session.commit()


REVIEW_TITLES = [
    "Love living here", "Great location and amenities", "Solid value for the area",
    "Beautiful building, attentive staff", "Quiet community, fast maintenance",
    "Five stars for the gym", "Comfortable and modern", "A little pricey but worth it",
    "Excellent property managers", "Smooth move-in experience",
    "Pet-friendly and welcoming", "Wonderful neighborhood",
    "Best apartment we've had", "Convenient and well-kept",
    "Friendly neighbors and clean halls",
]


REVIEW_BODIES = [
    "We moved in 8 months ago and the leasing team has been outstanding. "
    "Maintenance requests are handled within 24 hours, the gym is well-stocked, "
    "and the rooftop is a perfect spot to wind down.",
    "Location is incredible — we walk to coffee, groceries, and the train. "
    "The unit is spacious for the price and the finishes feel fresh.",
    "The building is well-managed and the amenities are clean and never crowded. "
    "Our pets are welcome and there's even a dog park out back.",
    "Quiet neighbors, secure entry, and a responsive concierge. "
    "Only minor gripe is that parking can fill up on weekends.",
    "Renewed our lease this year and have no complaints. "
    "The pool deck is a daily perk in summer.",
    "Energy efficient and quiet apartments. The HVAC keeps temps stable "
    "and we love the in-unit washer/dryer.",
    "Great place for young professionals — community events, package lockers, "
    "and a co-working lounge make remote work easy.",
]


def seed_reviews():
    if Review.query.count() > 0:
        return
    for b in Building.query.all():
        n = max(5, b.review_count or 5)
        # cap at 30
        n = min(30, n)
        for i in range(n):
            r = Review(
                building_id=b.id,
                author_name=f"Resident #{_h('ranum', b.slug, i) % 9000 + 1000}",
                rating=max(3, min(5, round(b.rating_avg + ((_h('rsk', b.slug, i) % 7 - 3) / 5.0)))),
                rating_value=3 + (_h("rv", b.slug, i) % 3),
                rating_location=4 + (_h("rl", b.slug, i) % 2),
                rating_office_staff=3 + (_h("ro", b.slug, i) % 3),
                rating_maintenance=3 + (_h("rm", b.slug, i) % 3),
                rating_amenities=3 + (_h("ram", b.slug, i) % 3),
                title=REVIEW_TITLES[_h("rt", b.slug, i) % len(REVIEW_TITLES)],
                body=REVIEW_BODIES[_h("rb", b.slug, i) % len(REVIEW_BODIES)],
                created_at=datetime(2026, 5, 27) - timedelta(days=_h("rd", b.slug, i) % 720),
            )
            db.session.add(r)
    db.session.commit()


ARTICLE_TITLES = [
    ("Renters Guide", "How to read an apartment lease without missing critical clauses"),
    ("Renters Guide", "Security deposit basics: what landlords can and can't charge"),
    ("Renters Guide", "A 14-day moving checklist for first-time renters"),
    ("Renters Guide", "How to budget for rent, utilities, and the surprise costs"),
    ("Renters Guide", "Renters insurance: how it works, what it covers"),
    ("Renters Guide", "The hidden costs of pet-friendly apartments — and how to negotiate them"),
    ("Renters Guide", "Studio vs 1-bedroom: when each makes financial sense"),
    ("Renters Guide", "Co-signers and guarantors: a renter's playbook"),
    ("Renters Guide", "How to spot a rental scam before you wire anything"),
    ("Renters Guide", "The polite, effective email that gets your lease renewed at a good rate"),
    ("Moving Tips", "30 things to do the week before moving day"),
    ("Moving Tips", "How to pack a kitchen so nothing breaks"),
    ("Moving Tips", "Hiring movers vs DIY: a real cost comparison"),
    ("Moving Tips", "Moving with kids: making the transition smoother"),
    ("Moving Tips", "Moving with pets across state lines"),
    ("Moving Tips", "What to do in your first 24 hours in a new apartment"),
    ("Moving Tips", "Should you tip the movers? (And how much)"),
    ("Roommates", "How to write a roommate agreement that prevents fights"),
    ("Roommates", "Splitting bills fairly when one roommate makes more"),
    ("Roommates", "What to do when a roommate moves out mid-lease"),
    ("Roommates", "Living with friends without ruining the friendship"),
    ("Market Trends", "Where rents are falling fastest in 2026"),
    ("Market Trends", "The case for renting in 2026 vs buying"),
    ("Market Trends", "Build-to-rent neighborhoods: what they actually are"),
    ("Market Trends", "Why luxury rental concessions are back"),
    ("Market Trends", "Pet rent, parking fees, and the rise of nickel-and-diming"),
    ("Decorating", "Renter-friendly upgrades that earn the deposit back"),
    ("Decorating", "Five lighting moves that change a small apartment"),
    ("Decorating", "How to soundproof a wall without drilling"),
    ("Decorating", "The IKEA hacks property managers will let slide"),
    ("Decorating", "Decorating a studio so it feels like multiple rooms"),
    ("Decorating", "Apartment plants that thrive with low light"),
    ("Neighborhoods", "How to choose a neighborhood when you're moving sight unseen"),
    ("Neighborhoods", "Walk score, transit score, bike score: how to actually use them"),
    ("Neighborhoods", "How to evaluate school zones if you don't have kids — yet"),
    ("Neighborhoods", "Up-and-coming neighborhoods to watch in the Sun Belt"),
    ("Neighborhoods", "Quiet city living: how to find a building that isn't loud"),
    ("Pet Owners", "What dog-friendly really means in 2026 building listings"),
    ("Pet Owners", "Apartment breed restrictions, explained"),
    ("Pet Owners", "Cat-friendly apartments: questions to ask"),
    ("Pet Owners", "Pet rent vs pet deposit: which is worse for your wallet"),
    ("Student Housing", "A college freshman's apartment-search timeline"),
    ("Student Housing", "Subletting over the summer: the basics"),
    ("Student Housing", "How to evaluate by-the-bed pricing"),
    ("Senior Living", "What 55+ communities actually require"),
    ("Senior Living", "Aging-in-place apartment features to look for"),
    ("Military", "BAH basics for first-time PCS renters"),
    ("Military", "Reading a lease's military clause"),
    ("Affordability", "Income-restricted housing: how the math works"),
    ("Affordability", "Negotiating rent during a soft market"),
    ("Affordability", "The 50/30/20 rule when rent eats 40% of income"),
]


def seed_articles():
    if Article.query.count() > 0:
        return
    for i, (cat, title) in enumerate(ARTICLE_TITLES):
        slug = _slug(title)[:180] + f"-{i:03d}"
        summary = (
            f"{title.split(':')[0].rstrip('.')} — practical answers, real numbers, "
            f"and a checklist you can use today."
        )
        body = (
            f"# {title}\n\n"
            f"_{summary}_\n\n"
            "Renting an apartment in 2026 is a fast-moving negotiation, "
            "and a few details up front save a lot of money later. This guide walks "
            "through the question step by step.\n\n"
            "## Why it matters\n\n"
            "Every renter encounters this. Treating it as a checklist — not a vibe — "
            "means you walk into a lease signing without surprises.\n\n"
            "## What to ask\n\n"
            "* Lease length and renewal terms\n"
            "* Total move-in cost (deposit, app fee, admin fee, first month)\n"
            "* Pet policy, including monthly pet rent\n"
            "* Parking fees and EV charging availability\n"
            "* Utility responsibilities (which are included)\n\n"
            "## A worked example\n\n"
            "Take a 1-bedroom at $2,200/month with a 12-month lease. A common "
            "move-in is first month + deposit ($2,200) + app fee ($75) + admin fee "
            "($200), so $4,675 out the door. Knowing that lets you compare "
            "apples-to-apples with the studio across the street.\n\n"
            "## Bottom line\n\n"
            "Get specifics in writing. The leasing office expects it, and good "
            "operators have the answers ready."
        )
        a = Article(
            slug=slug, title=title, summary=summary, body=body,
            category=cat,
            hero_image=f"/static/images/buildings/{DEFAULT_PHOTO_POOL[i % len(DEFAULT_PHOTO_POOL)]}.jpg" if DEFAULT_PHOTO_POOL else "",
            author="Apartments.com Editorial",
            published_at=datetime(2026, 5, 27) - timedelta(days=(i * 3) + 1),
            reading_time_min=4 + (i % 6),
        )
        db.session.add(a)
    db.session.commit()


def seed_database():
    """Top-level seeder — runs all sub-seeders in dependency order.

    Each sub-seeder is itself idempotent (early-return on populated state).
    The outer gate makes this cheap to call repeatedly.

    A final VACUUM defragments the file so byte-identity holds across
    /reset/<site>: SQLite's b-tree page allocator is otherwise sensitive to
    free-list state from any prior transactions in the session.
    """
    if City.query.count() > 0 and Building.query.count() > 0 and FloorPlan.query.count() > 0:
        return
    seed_cities()
    seed_buildings()
    seed_floor_plans_units()
    seed_schools()
    seed_building_relations()
    seed_reviews()
    seed_articles()


def _deterministic_pbkdf2_hash(email, pw="Password123!"):
    """Build a werkzeug-compatible pbkdf2:sha256 hash with a deterministic salt.

    Format: pbkdf2:sha256:1$<salt>$<hex>. Iterations are intentionally low
    (1) so the seed step stays fast and idempotent — the hash is also the
    storage format check_password reads back via wz_check.
    """
    salt = hashlib.md5(email.encode()).hexdigest()[:8]
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 1).hex()
    return f"pbkdf2:sha256:1${salt}${h}"


def seed_benchmark_users():
    """Insert the four canonical benchmark users for task scenarios.

    Idempotent: early-returns if any of them already exist.
    Uses deterministic pbkdf2 hashes so the seed DB stays byte-identical.
    """
    if User.query.filter_by(email='alice.j@test.com').first():
        return

    users = [
        ("alice.j@test.com", "Alice Johnson", "(212) 555-0144", 3400, 2),
        ("bob.k@test.com",   "Bob Kim",       "(415) 555-0188",  2200, 1),
        ("carla.r@test.com", "Carla Reyes",   "(305) 555-0177",  4500, 2),
        ("dan.p@test.com",   "Dan Park",      "(206) 555-0199",  1800, 0),
    ]
    created = {}
    seed_dt = datetime(2026, 5, 27, 12, 0, 0)
    for email, name, phone, budget, beds in users:
        u = User(email=email, name=name, phone=phone,
                 budget_max=budget, beds_min=beds,
                 receive_alerts=True, created_at=seed_dt)
        u.password_hash = _deterministic_pbkdf2_hash(email)
        db.session.add(u)
        created[email] = u
    db.session.flush()

    # Saved searches + favorites + tour requests for benchmark scenarios.
    alice = created["alice.j@test.com"]
    bob = created["bob.k@test.com"]
    carla = created["carla.r@test.com"]
    dan = created["dan.p@test.com"]

    # Pick a deterministic set of buildings to favorite per user
    all_blds = Building.query.order_by(Building.id).all()
    if all_blds:
        for u, k in [(alice, 0), (bob, 1), (carla, 2), (dan, 3)]:
            for j in range(3):
                b = all_blds[(_h("favbld", u.email, j) % len(all_blds))]
                db.session.add(Favorite(user_id=u.id, building_id=b.id,
                                        created_at=datetime(2026, 5, 27)
                                                   - timedelta(days=j + k)))

    # Saved searches
    db.session.add(SavedSearch(user_id=alice.id, name="2BR Brooklyn under $4000",
                               query_string="city=New York&beds=2&price_max=4000",
                               created_at=datetime(2026, 5, 20)))
    db.session.add(SavedSearch(user_id=bob.id, name="SF pet-friendly 1BR",
                               query_string="city=San Francisco&beds=1&pet=any",
                               created_at=datetime(2026, 5, 21)))
    db.session.add(SavedSearch(user_id=carla.id, name="Miami luxury 2BR EV",
                               query_string="city=Miami&beds=2&mode=luxury&amenity=ev_charging",
                               created_at=datetime(2026, 5, 22)))
    db.session.add(SavedSearch(user_id=dan.id, name="Seattle studio walkable",
                               query_string="city=Seattle&beds=studio",
                               created_at=datetime(2026, 5, 23)))
    db.session.commit()
