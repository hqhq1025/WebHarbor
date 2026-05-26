"""Extra listing blueprints to bring the craigslist mirror up to 400+ rows.

Kept in a separate module so the dense ~260-row catalog doesn't drown the
hand-curated SPECIAL_LISTINGS / TARGET_NEAR_MISSES sections in seed_data.py.

Each entry is a dict with keys:
    category_slug, title, price, condition, description, details (dict)
Optional keys: bedrooms, sqft, compensation, company, employment_type

Areas / neighborhoods are filled in by seed_data.py at build time via a
deterministic round-robin so we don't have to hand-pin every row.
"""

# Bay Area neighborhoods grouped by craigslist area code. Picked from real
# place names so search / map filters look realistic.
NEIGHBORHOODS_BY_AREA = {
    "san francisco": [
        "mission district", "soma", "richmond district", "sunset", "nob hill",
        "north beach", "marina", "haight", "castro", "dogpatch",
        "bernal heights", "potrero hill", "bayview", "excelsior", "inner sunset",
        "nopa", "lower haight", "glen park",
    ],
    "east bay": [
        "oakland", "berkeley", "alameda", "emeryville", "richmond", "hayward",
        "fremont", "walnut creek", "concord", "dublin", "pleasanton",
        "livermore", "san leandro", "castro valley", "rockridge",
        "oakland temescal", "oakland lake merritt", "west oakland",
    ],
    "south bay": [
        "san jose", "sunnyvale", "santa clara", "mountain view", "cupertino",
        "milpitas", "campbell", "los gatos", "saratoga", "gilroy",
    ],
    "peninsula": [
        "palo alto", "menlo park", "redwood city", "san mateo", "foster city",
        "burlingame", "daly city", "south san francisco", "half moon bay",
    ],
    "north bay": [
        "san rafael", "novato", "santa rosa", "petaluma", "mill valley",
        "sausalito", "vallejo", "napa", "sonoma",
    ],
    "santa cruz": [
        "santa cruz", "aptos", "capitola", "scotts valley", "soquel",
        "watsonville",
    ],
}


def _g(category_slug, title, price, condition, description, **details):
    return {
        "category_slug": category_slug,
        "title": title,
        "price": price,
        "condition": condition,
        "description": description,
        "details": details,
    }


def _h(category_slug, title, price, bedrooms, sqft, description, **details):
    return {
        "category_slug": category_slug,
        "title": title,
        "price": price,
        "condition": "new",
        "bedrooms": bedrooms,
        "sqft": sqft,
        "description": description,
        "details": details,
    }


def _j(category_slug, title, compensation, company, employment_type, description, **details):
    return {
        "category_slug": category_slug,
        "title": title,
        "price": None,
        "condition": "",
        "compensation": compensation,
        "company": company,
        "employment_type": employment_type,
        "description": description,
        "details": details,
    }


BULK_RECORDS = [
    # ---------------- for_sale: furniture (+10) ----------------
    _g("furniture", "Mid-century walnut sideboard", 360, "excellent", "Restored mid-century sideboard with three drawers and two cabinets. Smoke-free home.", material="walnut", length="62 in", delivery="pickup or local delivery"),
    _g("furniture", "IKEA Hemnes 6-drawer dresser", 175, "good", "White Hemnes dresser, drawers slide cleanly. Top has a small water ring.", material="pine", color="white", delivery="buyer pickup"),
    _g("furniture", "Leather recliner armchair", 240, "good", "Brown leather recliner, manual lever, scuff on right arm.", material="leather", color="brown", delivery="pickup only"),
    _g("furniture", "Gray sectional sofa with chaise", 520, "good", "5-seat sectional with reversible chaise. Pet free, smoke free.", material="polyester", color="gray", delivery="pickup, can help load"),
    _g("furniture", "Solid oak farmhouse dining table", 410, "excellent", "Seats six. Refinished top last winter, no chairs included.", material="oak", length="72 in", delivery="pickup only"),
    _g("furniture", "Pair of mid-century nightstands", 220, "good", "Matching walnut nightstands with single drawer each.", material="walnut", quantity="2", delivery="pickup"),
    _g("furniture", "Tall white wardrobe cabinet", 145, "fair", "Tall white wardrobe with shelf and hanging rod. Door hinge needs tightening.", material="MDF", color="white", delivery="buyer pickup"),
    _g("furniture", "Linen tufted ottoman storage bench", 95, "good", "Beige tufted ottoman with interior storage. Doubles as bench seating.", material="linen", color="beige", delivery="pickup only"),
    _g("furniture", "Crate and Barrel Lounge II loveseat", 480, "excellent", "Charcoal Lounge II loveseat, slipcovered, recently washed.", material="cotton blend", color="charcoal", delivery="pickup only"),
    _g("furniture", "Reclaimed wood console table", 260, "good", "Narrow console table, perfect behind a sofa or in an entryway.", material="reclaimed pine", length="60 in", delivery="pickup only"),

    # ---------------- for_sale: electronics (+12) ----------------
    _g("electronics", "LG 55 inch 4K OLED TV", 540, "good", "OLED55C9. Includes original remote, no stand mount.", size="55 in", resolution="3840x2160", ports="HDMI x4"),
    _g("electronics", "PlayStation 5 disc edition", 380, "excellent", "PS5 disc with one DualSense and two games.", included="console controller cables", region="US"),
    _g("electronics", "MacBook Pro 14 inch M2", 1450, "excellent", "M2 Pro 16GB / 512GB. Battery cycles under 80, original box.", cpu="M2 Pro", ram="16 GB", storage="512 GB SSD"),
    _g("electronics", "Dell XPS 13 laptop", 620, "good", "i7 / 16GB / 512GB. New battery installed last month.", cpu="i7-1185G7", ram="16 GB", storage="512 GB"),
    _g("electronics", "Sony A7C mirrorless camera body", 980, "good", "Full-frame body only, shutter count under 8k.", mount="Sony E", sensor="full frame", included="battery charger"),
    _g("electronics", "Canon EF 24-70 f/2.8L II zoom", 850, "good", "Sharp pro zoom with hood and pouch. Light barrel wear.", mount="Canon EF", aperture="f/2.8", included="hood pouch"),
    _g("electronics", "Apple Watch Series 9 GPS 45mm", 280, "excellent", "Midnight aluminum with sport loop. Always-on display.", size="45 mm", connectivity="GPS", included="charger"),
    _g("electronics", "Kindle Paperwhite 11th gen", 75, "good", "11th gen Paperwhite, no ads. Comes with leather cover.", storage="8 GB", included="cover cable"),
    _g("electronics", "Sonos Beam Gen 2 soundbar", 240, "excellent", "Lightly used Beam Gen 2, original packaging.", connectivity="HDMI eARC wifi", color="black"),
    _g("electronics", "DJI Mini 3 drone fly more combo", 510, "excellent", "Mini 3 with three batteries, smart controller, and case.", battery="3 included", controller="smart RC", weight="249 g"),
    _g("electronics", "Reolink 4-camera POE security kit", 340, "good", "Four 5MP POE cameras, NVR, and cables. Reset to factory.", channels="4", resolution="5 MP", storage="2 TB included"),
    _g("electronics", "Vintage Technics SL-1200 turntable", 720, "good", "Silver SL-1200 MK2, recently serviced, new cartridge.", drive="direct", color="silver", included="dust cover cartridge"),

    # ---------------- for_sale: bikes (+6) ----------------
    _g("bikes", "Specialized Rockhopper 29er", 540, "good", "Hardtail mountain bike, large frame, recent tune-up.", frame="large", brakes="hydraulic disc", wheel_size="29 in"),
    _g("bikes", "Rad Power RadCity electric bike", 1100, "excellent", "Class 2 e-bike, 750W hub motor, includes second battery.", frame="step-through", motor="750 W", battery="2 included"),
    _g("bikes", "Trek Domane SL5 road bike", 1850, "excellent", "Carbon endurance road bike, 56cm, Shimano 105 group.", frame="56 cm", brakes="hydraulic disc", groupset="Shimano 105"),
    _g("bikes", "Surly Cross-Check gravel build", 880, "good", "Steel cross-check, 56cm, Salsa bars, fenders included.", frame="56 cm", brakes="cantilever", wheel_size="700c"),
    _g("bikes", "Electra Townie cruiser, step-through", 290, "good", "Comfortable cruiser, internal 7-speed, fenders and basket.", frame="medium", brakes="coaster", wheel_size="26 in"),
    _g("bikes", "Kids 16 inch Cleary Hedgehog", 160, "good", "Cleary Hedgehog 16, ages 4-6, freewheel rear, hand brake.", frame="kids", brakes="rim", wheel_size="16 in"),

    # ---------------- for_sale: cars_trucks (+6) ----------------
    _g("cars_trucks", "2014 Toyota Camry LE sedan", 8450, "good", "Single owner Camry LE, recent timing belt, current registration.", make="Toyota", model="Camry LE", mileage="118000", title_status="clean", transmission="automatic"),
    _g("cars_trucks", "2010 Subaru Outback 2.5i", 6300, "good", "Outback wagon with new tires and head gasket replaced at 165k.", make="Subaru", model="Outback", mileage="172000", title_status="clean", transmission="automatic"),
    _g("cars_trucks", "2017 Toyota Prius Two", 12400, "excellent", "Hybrid Prius, single owner, dealer-maintained, hybrid battery healthy.", make="Toyota", model="Prius", mileage="84000", title_status="clean", transmission="automatic"),
    _g("cars_trucks", "2008 Ford F-150 XLT supercab", 9200, "fair", "Work truck with bed liner and tow package, body shows age.", make="Ford", model="F-150 XLT", mileage="194000", title_status="clean", transmission="automatic"),
    _g("cars_trucks", "2015 Nissan Leaf SV", 5400, "good", "Leaf SV with 24 kWh pack, 80 mile range, includes EVSE.", make="Nissan", model="Leaf SV", mileage="76000", title_status="clean", range="80 mi"),
    _g("cars_trucks", "2019 Mazda CX-5 Touring AWD", 17500, "excellent", "CX-5 Touring AWD, leather, dealer service records, like new tires.", make="Mazda", model="CX-5 Touring", mileage="58000", title_status="clean", transmission="automatic"),

    # ---------------- for_sale: appliances (+7) ----------------
    _g("appliances", "Samsung french door refrigerator", 620, "good", "30 cu ft french door fridge, water and ice. Light dent on side panel.", capacity="30 cu ft", color="stainless", delivery="curbside available"),
    _g("appliances", "Bosch 800 series dishwasher", 420, "excellent", "Bosch 800 dishwasher, third rack, runs whisper quiet.", color="stainless", noise="44 dB", delivery="pickup only"),
    _g("appliances", "Whirlpool over-the-range microwave", 95, "good", "Stainless OTR microwave, mounting hardware included.", capacity="1.7 cu ft", color="stainless", delivery="pickup only"),
    _g("appliances", "GE 30 inch gas range", 380, "good", "Five-burner gas range, convection oven, knobs all turn smoothly.", fuel="gas", width="30 in", delivery="curbside available"),
    _g("appliances", "Breville Barista Express espresso", 360, "excellent", "Breville Barista Express with built-in grinder, descaled monthly.", color="stainless", included="tamper portafilters", delivery="pickup only"),
    _g("appliances", "KitchenAid Artisan stand mixer", 240, "good", "Empire red 5 qt stand mixer, includes whisk dough hook paddle.", color="empire red", capacity="5 qt", included="whisk hook paddle"),
    _g("appliances", "Vitamix A2300 blender", 290, "excellent", "Vitamix A2300 with tamper, no chips on container.", capacity="64 oz", motor="2.2 hp", included="tamper book"),

    # ---------------- for_sale: free (+2) ----------------
    _g("free", "Free wood pallets", 0, "used", "Stack of clean hardwood pallets, take as many as you can carry.", quantity="12 pallets", pickup="alley", cross_streets="Folsom and 18th"),
    _g("free", "Free terracotta planter pots", 0, "used", "Assorted terracotta pots, 6 to 14 inch. Some have minor chips.", quantity="20 pots", pickup="curb", cross_streets="Telegraph and 49th"),

    # ---------------- for_sale: musical (+4) ----------------
    _g("musical", "Fender Player Stratocaster, sunburst", 580, "excellent", "Player series Strat in sunburst, includes gig bag and cable.", instrument="electric guitar", color="sunburst", included="gig bag cable"),
    _g("musical", "Yamaha P-125 digital piano", 460, "good", "88 weighted keys, sustain pedal, stand. Sounds great with headphones.", keys="88", weight="weighted", included="pedal stand"),
    _g("musical", "Pearl 5-piece drum kit", 540, "good", "Pearl Export 5-piece kit with cymbals, stands, and stool.", pieces="5", included="cymbals stands stool", color="wine red"),
    _g("musical", "Student violin 4/4 with case", 180, "good", "Full-size student violin, fresh bow rehair, hard case included.", size="4/4", included="case bow rosin"),

    # ---------------- for_sale: sporting (+3) ----------------
    _g("sporting", "Tandem sit-on-top kayak with paddles", 540, "good", "10 ft tandem sit-on-top kayak, two paddles, two PFDs.", length="10 ft", capacity="2 person", included="paddles PFDs"),
    _g("sporting", "REI Half Dome 4 tent", 180, "excellent", "4-person REI Half Dome, used three trips, includes footprint.", capacity="4 person", weight="7 lb", included="footprint"),
    _g("sporting", "9 foot soft top surfboard", 240, "good", "Beginner-friendly 9 ft soft top, leash included, no dings.", length="9 ft", included="leash", color="blue"),

    # ---------------- for_sale: tools (+2) ----------------
    _g("tools", "DeWalt 20V cordless drill kit", 145, "good", "DeWalt 20V drill, impact driver, two batteries, charger, bag.", brand="DeWalt", voltage="20 V", included="2 batteries charger bag"),
    _g("tools", "Ridgid table saw with stand", 320, "good", "10 inch portable table saw with folding stand and miter gauge.", brand="Ridgid", size="10 in", included="stand miter gauge"),

    # ---------------- housing: apartments (+28) ----------------
    _h("apartments", "Sunny Castro one bedroom with bay window", 3150, 1, 720, "Top floor 1BR in classic Castro Victorian, bay window, restored hardwood.", laundry="in-building", parking="street", pet_policy="cats ok", lease="12 months"),
    _h("apartments", "Modern Soma loft 1BR", 3400, 1, 760, "Exposed brick loft with concrete floors, in-unit laundry, no pets.", laundry="in-unit", parking="garage extra", pet_policy="no pets", lease="12 months"),
    _h("apartments", "Mission 2BR top floor with deck", 4200, 2, 1050, "Two bedroom flat with private deck and updated kitchen.", laundry="in-unit", parking="street", pet_policy="dogs ok", lease="12 months"),
    _h("apartments", "Inner Sunset garden 1BR", 2850, 1, 680, "Quiet garden apartment with private entrance and shared yard.", laundry="shared", parking="street", pet_policy="cats ok", lease="12 months"),
    _h("apartments", "Marina junior 1BR steps to Chestnut", 2950, 1, 540, "Junior one bedroom near restaurants, fresh paint, no parking.", laundry="coin", parking="none", pet_policy="no pets", lease="12 months"),
    _h("apartments", "North Beach studio above cafe", 2150, 0, 380, "Studio with view of Washington Square Park, walk-up.", laundry="laundromat next door", parking="none", pet_policy="no pets", lease="month-to-month"),
    _h("apartments", "Bernal Heights 2BR with views", 3650, 2, 980, "Two bedroom with private patio and panoramic city view.", laundry="in-unit", parking="driveway", pet_policy="dogs ok", lease="12 months"),
    _h("apartments", "Potrero Hill 1BR with parking", 3050, 1, 640, "Updated one bedroom with assigned parking and shared roof deck.", laundry="in-building", parking="included", pet_policy="cats ok", lease="12 months"),
    _h("apartments", "Hayes Valley designer studio", 2780, 0, 500, "Renovated studio with new appliances, walk to Patricia's Green.", laundry="shared", parking="none", pet_policy="cats ok", lease="12 months"),
    _h("apartments", "Glen Park cozy 1BR near BART", 2680, 1, 620, "Tree-lined street, 5 minute walk to Glen Park BART.", laundry="shared", parking="street", pet_policy="no pets", lease="12 months"),
    _h("apartments", "Berkeley north side 2BR", 3450, 2, 940, "Two bedroom near Gourmet Ghetto, hardwood floors, dishwasher.", laundry="in-unit", parking="off street", pet_policy="cats ok", lease="12 months"),
    _h("apartments", "Oakland Adams Point 1BR with view", 2450, 1, 700, "Lake Merritt view 1BR, secure building, fitness room.", laundry="in-building", parking="garage extra", pet_policy="cats ok", lease="12 months"),
    _h("apartments", "Rockridge 1BR near College Ave", 2780, 1, 720, "Walk to College Ave shops, dishwasher and disposal.", laundry="in-building", parking="street", pet_policy="cats ok", lease="12 months"),
    _h("apartments", "Alameda Marina district 2BR", 3250, 2, 1020, "Two bedroom near the marina, large windows, in-unit washer dryer.", laundry="in-unit", parking="included", pet_policy="dogs ok", lease="12 months"),
    _h("apartments", "Fremont Centerville 2BR garden", 2750, 2, 980, "Garden style two bedroom near BART, pool in complex.", laundry="in-unit", parking="2 spots", pet_policy="cats ok", lease="12 months"),
    _h("apartments", "Walnut Creek 1BR near downtown", 2380, 1, 700, "Walk to Broadway Plaza, in-building gym and pool.", laundry="in-building", parking="garage included", pet_policy="cats ok", lease="12 months"),
    _h("apartments", "Concord 2BR with patio", 2480, 2, 900, "Two bedroom apartment with private patio, on-site management.", laundry="in-unit", parking="2 spots", pet_policy="dogs ok", lease="12 months"),
    _h("apartments", "Hayward 1BR near BART", 2150, 1, 660, "One bedroom near South Hayward BART, gated parking.", laundry="in-building", parking="gated", pet_policy="no pets", lease="12 months"),
    _h("apartments", "San Jose downtown 1BR with gym", 2580, 1, 720, "Modern 1BR in downtown San Jose, gym and pool on site.", laundry="in-unit", parking="garage included", pet_policy="cats ok", lease="12 months"),
    _h("apartments", "Sunnyvale 2BR townhome style", 3450, 2, 1100, "Two-story townhome style 2BR with private entrance.", laundry="in-unit", parking="2 spots", pet_policy="dogs ok", lease="12 months"),
    _h("apartments", "Mountain View 1BR walk to Castro St", 3050, 1, 720, "One bedroom apartment, short walk to Castro Street shops.", laundry="in-building", parking="garage", pet_policy="cats ok", lease="12 months"),
    _h("apartments", "Cupertino 2BR near Apple campus", 3680, 2, 1050, "Two bedroom near Apple Park, recently updated kitchen.", laundry="in-unit", parking="2 spots", pet_policy="cats ok", lease="12 months"),
    _h("apartments", "Milpitas 2BR with balcony", 2780, 2, 950, "Two bedroom with balcony, pool and tennis court.", laundry="in-unit", parking="2 spots", pet_policy="cats ok", lease="12 months"),
    _h("apartments", "Palo Alto downtown 1BR", 3850, 1, 700, "Walk to University Ave, secured entry, on-site laundry.", laundry="shared", parking="street", pet_policy="no pets", lease="12 months"),
    _h("apartments", "Menlo Park 2BR cottage", 4250, 2, 1200, "Detached two bedroom cottage with private yard.", laundry="in-unit", parking="driveway", pet_policy="dogs ok", lease="12 months"),
    _h("apartments", "Redwood City 1BR near Caltrain", 2680, 1, 680, "One bedroom near Redwood City Caltrain, dishwasher included.", laundry="in-building", parking="included", pet_policy="cats ok", lease="12 months"),
    _h("apartments", "San Rafael 1BR with hill view", 2350, 1, 650, "Sunny 1BR with hill views, secured entry, off-street parking.", laundry="shared", parking="off street", pet_policy="cats ok", lease="12 months"),
    _h("apartments", "Santa Cruz beach side 1BR", 2580, 1, 640, "Walk to the beach, one bedroom with parking spot.", laundry="shared", parking="off street", pet_policy="no pets", lease="9 months"),

    # ---------------- housing: rooms_shares (+10) ----------------
    _h("rooms_shares", "Room in Berkeley grad house", 1180, 1, 130, "Private room in a three-bedroom shared with grad students.", utilities="included", bath="shared", move_in="July 1"),
    _h("rooms_shares", "Mission shared loft, private room", 1450, 1, 160, "Private room in a converted Mission loft, two shared baths.", utilities="split", bath="shared", move_in="June 15"),
    _h("rooms_shares", "Master bedroom in Alameda house", 1620, 1, 220, "Master with attached bath in a 3BR house. Quiet street.", utilities="split", bath="private", move_in="June 1"),
    _h("rooms_shares", "Sunny room near Lake Merritt", 1280, 1, 140, "Bright room in a craftsman home, shared kitchen and yard.", utilities="included", bath="shared", move_in="June 1"),
    _h("rooms_shares", "Furnished room in Sunnyvale townhome", 1380, 1, 150, "Furnished room with desk and twin bed, near Caltrain.", utilities="included", bath="shared", move_in="July 1"),
    _h("rooms_shares", "Room in West Oakland artist house", 1150, 1, 135, "Room in a shared house with garage studio space.", utilities="split", bath="shared", move_in="June 15"),
    _h("rooms_shares", "Private room in Palo Alto family home", 1580, 1, 165, "Quiet room in a family home, shared kitchen, near Stanford.", utilities="included", bath="shared", move_in="August 1"),
    _h("rooms_shares", "Room with deck in San Jose house", 1240, 1, 150, "Private room with shared deck and backyard.", utilities="split", bath="shared", move_in="June 1"),
    _h("rooms_shares", "Cozy room in Santa Cruz beach house", 1320, 1, 140, "Walk to the beach, shared kitchen and living room.", utilities="split", bath="shared", move_in="July 15"),
    _h("rooms_shares", "Bedroom in Hayward apartment", 1080, 1, 130, "Shared 2BR apartment, near BART, quiet roommate.", utilities="split", bath="shared", move_in="June 1"),

    # ---------------- housing: sublets (+6) ----------------
    _h("sublets", "Summer sublet, fully furnished Mission studio", 2400, 0, 480, "June through August sublet, fully furnished with linens and kitchenware.", furnishings="fully furnished", duration="3 months", utilities="included"),
    _h("sublets", "Short term Berkeley 1BR sublet", 2200, 1, 620, "Two month sublet during summer, walking distance to campus.", furnishings="furnished", duration="2 months", utilities="included"),
    _h("sublets", "Furnished Oakland room for traveling nurse", 1800, 1, 200, "Three month sublet for travel professionals, parking included.", furnishings="furnished", duration="3 months", utilities="included"),
    _h("sublets", "South Bay corporate sublet 1BR", 3200, 1, 700, "Furnished 1BR ideal for relocation, monthly billing.", furnishings="fully furnished", duration="1-6 months", utilities="included"),
    _h("sublets", "Mountain View summer sublet, 2BR", 3850, 2, 980, "Two bedroom summer sublet near Caltrain, dog ok.", furnishings="furnished", duration="3 months", utilities="split"),
    _h("sublets", "Sausalito houseboat sublet", 2950, 1, 540, "Unique houseboat sublet, four week minimum, no smoking.", furnishings="fully furnished", duration="1-3 months", utilities="included"),

    # ---------------- housing: parking (+4) ----------------
    _g("parking", "Garage space, North Beach", 320, "new", "Single garage space near Washington Square. Standard sedan fits comfortably.", availability="available now", access="24/7", size="standard"),
    _g("parking", "Covered parking, Oakland Lake Merritt", 220, "new", "Covered parking spot near 19th Street BART. First month free with annual lease.", availability="June 1", access="key card", size="standard"),
    _g("parking", "Driveway space in Berkeley", 175, "new", "Single driveway space, suitable for compact car.", availability="July 1", access="open", size="compact"),
    _g("parking", "South Bay storage spot for RV", 280, "new", "Outdoor RV storage spot, gated lot, security cameras.", availability="now", access="gated", size="35 ft"),

    # ---------------- housing: office_commercial (+3) ----------------
    _g("office_commercial", "Coworking desk in Mission studio", 380, "new", "Dedicated desk in a 6-person studio, 24/7 access, fast internet.", availability="now", access="24/7", size="dedicated desk"),
    _g("office_commercial", "Small private office, Oakland", 950, "new", "Furnished private office for 2 people, downtown Oakland.", availability="July 1", access="24/7", size="180 sqft"),
    _g("office_commercial", "Retail bay on Solano Ave", 2850, "new", "Walk-in retail bay on Solano Avenue, 700 sqft, kitchenette in back.", availability="August 1", access="business hours", size="700 sqft"),

    # ---------------- jobs: software (+9) ----------------
    _j("software", "Senior backend engineer, payments", "$185k - $215k", "Northstar Payments", "full-time", "Lead backend services for payments rails. Python, Go, Postgres.", remote="hybrid", stack="Python Go Postgres", equity="0.05%"),
    _j("software", "Frontend engineer for design tools", "$165k - $190k", "Brushwork", "full-time", "Build collaborative design tools in React and Canvas APIs.", remote="remote first", stack="React TypeScript Canvas", equity="0.10%"),
    _j("software", "Mobile engineer, iOS", "$170k - $200k", "Foglight Health", "full-time", "Ship features in Swift for a health tracking iOS app.", remote="hybrid", stack="Swift SwiftUI", equity="0.05%"),
    _j("software", "Full-stack engineer, hybrid", "$155k - $180k", "Civic Track", "full-time", "Full-stack work across Django and Next.js for civic dashboards.", remote="hybrid", stack="Django Next.js Postgres", equity="0.15%"),
    _j("software", "Site reliability engineer", "$175k - $205k", "Cargolane", "full-time", "Own observability and on-call rotation for logistics platform.", remote="hybrid", stack="Kubernetes Terraform AWS", equity="0.10%"),
    _j("software", "Data engineer, batch and streaming", "$170k - $195k", "Beacon Energy", "full-time", "Build pipelines for energy market data using Spark and Kafka.", remote="hybrid", stack="Spark Kafka Snowflake", equity="0.05%"),
    _j("software", "Machine learning engineer, vision", "$190k - $230k", "Sightcraft", "full-time", "Train and ship computer vision models for industrial inspection.", remote="hybrid", stack="PyTorch CUDA Triton", equity="0.20%"),
    _j("software", "Security engineer, application", "$180k - $210k", "Saltbox Identity", "full-time", "Threat model and pen-test internal services.", remote="remote", stack="Python Go Kubernetes", equity="0.10%"),
    _j("software", "QA automation engineer", "$130k - $155k", "Lumen Edu", "full-time", "Author end-to-end browser tests and CI infrastructure.", remote="hybrid", stack="Playwright TypeScript", equity="0.02%"),

    # ---------------- jobs: customer_service (+7) ----------------
    _j("customer_service", "Tier 1 support agent, remote", "$24 - $28 per hour", "Tidepool Tools", "full-time", "Answer customer email and chat for a SaaS product.", schedule="weekday daytime", shift="9am-5pm", benefits="medical dental"),
    _j("customer_service", "Customer success manager", "$95k - $115k", "Marigold Analytics", "full-time", "Own renewals and adoption for mid-market accounts.", remote="hybrid", territory="west coast", quota="$800k ARR"),
    _j("customer_service", "Bilingual support specialist Spanish", "$26 - $30 per hour", "Vista Mobile", "full-time", "Phone and chat support in English and Spanish.", schedule="rotating weekends", languages="Spanish English"),
    _j("customer_service", "Billing operations specialist", "$28 per hour", "Cliffside Insurance", "full-time", "Resolve billing disputes and post payments.", schedule="weekday daytime", system="Salesforce"),
    _j("customer_service", "Chat support agent, evenings", "$22 per hour", "Birchwood Outdoors", "part-time", "Evening chat coverage for outdoor gear retailer.", schedule="evenings", shift="4pm-10pm"),
    _j("customer_service", "Concierge desk associate", "$26 per hour", "Cobalt Building Services", "full-time", "Front desk concierge in a downtown commercial building.", schedule="weekday daytime", uniform="provided"),
    _j("customer_service", "Onboarding specialist, fintech", "$80k - $95k", "Northwave Bank", "full-time", "Walk new business customers through account opening.", remote="hybrid", certification="not required"),

    # ---------------- jobs: food_bev_hosp (+8) ----------------
    _j("food_bev_hosp", "Server for new wine bar, evenings", "$22 plus tips", "Hearth and Vine", "part-time", "Evening server shifts at a new neighborhood wine bar.", shift="5pm-11pm", experience="1 year", benefits="meals"),
    _j("food_bev_hosp", "Head bartender for cocktail lounge", "$28 plus tips", "Moonlit Co", "full-time", "Build and execute cocktail menu for a downtown lounge.", shift="evenings", experience="3 years", benefits="health stipend"),
    _j("food_bev_hosp", "Sous chef, farm to table", "$72k - $82k", "Wildwood Kitchen", "full-time", "Run prep and dinner service alongside chef de cuisine.", shift="afternoons", experience="4 years", benefits="medical dental"),
    _j("food_bev_hosp", "Prep cook, weekday mornings", "$25 per hour", "Public Square Cafe", "full-time", "AM prep cook position, fast paced cafe kitchen.", shift="6am-2pm", experience="1 year", benefits="meals transit"),
    _j("food_bev_hosp", "Dishwasher, weekend nights", "$22 per hour", "Salt and Stem", "part-time", "Weekend night dish pit, can earn tips share.", shift="5pm-12am", experience="none", benefits="meals"),
    _j("food_bev_hosp", "Host for popular brunch spot", "$24 per hour plus tips", "Sunday Best", "full-time", "Manage seating and reservations Thursday through Sunday.", shift="9am-3pm", experience="1 year", benefits="meals"),
    _j("food_bev_hosp", "Barista lead, multi-location", "$26 per hour", "Two Birds Coffee", "full-time", "Lead barista shifts and train new hires.", shift="6am-2pm", experience="2 years", benefits="medical"),
    _j("food_bev_hosp", "Front of house manager", "$72k - $85k", "Carbon Smokehouse", "full-time", "Manage 12-person FOH team across dinner service.", shift="evenings", experience="3 years management", benefits="medical dental PTO"),

    # ---------------- jobs: general_labor (+6) ----------------
    _j("general_labor", "Warehouse picker packer, day shift", "$24 per hour", "Foglight Logistics", "full-time", "Day shift picker packer in a temperature-controlled warehouse.", shift="7am-3pm", lifting="40 lb"),
    _j("general_labor", "Day laborer, drywall demo", "$26 per hour cash", "Bay Demo Crew", "part-time", "Demo crew for residential drywall and tile.", shift="8am-4pm", lifting="60 lb"),
    _j("general_labor", "Landscaper crew member", "$24 per hour", "Stonehill Gardens", "full-time", "Crew member for residential landscape maintenance.", shift="7am-3pm", lifting="50 lb"),
    _j("general_labor", "Delivery driver helper, weekends", "$22 per hour plus tips", "Riverside Movers", "part-time", "Helper for weekend furniture deliveries.", shift="Sat Sun", lifting="75 lb"),
    _j("general_labor", "Event setup crew", "$25 per hour", "Lantern Events", "part-time", "Setup and breakdown for weekend events.", shift="varies weekends", lifting="50 lb"),
    _j("general_labor", "Gardener for residential clients", "$26 per hour", "Common Ground Yards", "full-time", "Routine gardening and seasonal cleanup at residential homes.", shift="weekday daytime", lifting="40 lb"),

    # ---------------- jobs: healthcare (+7) ----------------
    _j("healthcare", "Registered nurse, ED", "$78 per hour", "Bayhill Medical Center", "full-time", "ED registered nurse, 12-hour shifts, every third weekend.", schedule="3x12", license="CA RN", setting="emergency"),
    _j("healthcare", "Certified nursing assistant", "$28 per hour", "Cypress Senior Care", "full-time", "CNA position in a skilled nursing facility, AM shift.", schedule="6am-2pm", license="CNA", setting="skilled nursing"),
    _j("healthcare", "Medical assistant, primary care", "$32 per hour", "Bayside Family Clinic", "full-time", "MA for primary care clinic, EHR experience required.", schedule="M-F daytime", license="MA certificate", setting="primary care"),
    _j("healthcare", "Dental hygienist, two days", "$58 per hour", "Mariposa Dental", "part-time", "RDH two days per week, modern office.", schedule="Tue Thu", license="CA RDH", setting="general dental"),
    _j("healthcare", "Phlebotomist, mornings", "$30 per hour", "Bridge Diagnostics", "part-time", "Morning phlebotomy shifts in a busy clinical lab.", schedule="5am-11am", license="CPT-1", setting="clinical lab"),
    _j("healthcare", "Optician for retail eyewear", "$32 per hour", "Lens and Frame Co", "full-time", "Help customers fit and select eyewear.", schedule="weekday daytime", license="apprentice ok", setting="retail"),
    _j("healthcare", "Clinical lab technician", "$42 per hour", "Bayview Pathology", "full-time", "Lab technician, evening shift, blood and microbiology samples.", schedule="2pm-10pm", license="CLT", setting="pathology lab"),

    # ---------------- jobs: education (+6) ----------------
    _j("education", "Substitute teacher, K-8", "$220 per day", "Coastside Unified", "contract", "Day-to-day substitute teaching across K-8 schools.", credential="emergency permit ok", grade="K-8", setting="public school"),
    _j("education", "Preschool aide", "$23 per hour", "Sunrise Childrens Center", "full-time", "Preschool aide supporting lead teacher in mixed-age class.", credential="12 ECE units", grade="preschool", setting="preschool"),
    _j("education", "ESL teacher for adult learners", "$45 per hour", "Bay Community College", "part-time", "Evening adult ESL classes, beginner and intermediate levels.", credential="MA TESOL preferred", grade="adult", setting="community college"),
    _j("education", "After-school program coordinator", "$28 per hour", "Lighthouse Youth", "full-time", "Coordinate after-school enrichment at two elementary sites.", credential="bachelor degree", grade="elementary", setting="after school"),
    _j("education", "Math intervention specialist", "$45 per hour", "Bay Math Project", "contract", "Pull-out math support for 4th and 5th graders.", credential="CA multiple subject", grade="4-5", setting="public school"),
    _j("education", "Music teacher, elementary", "$38 per hour", "Crescendo Learning", "part-time", "Teach general music classes K-5 at private school.", credential="music bachelor degree", grade="K-5", setting="private school"),

    # ---------------- jobs: sales (+7) ----------------
    _j("sales", "SDR for B2B SaaS", "$70k - $85k OTE", "Whetstone Analytics", "full-time", "Outbound SDR role, books meetings for AE team.", quota="80 meetings per quarter", remote="hybrid"),
    _j("sales", "Account executive, mid-market", "$140k - $180k OTE", "Plumeria CRM", "full-time", "Close mid-market deals in the $20k-$80k ACV range.", quota="$1.2M ARR", remote="hybrid"),
    _j("sales", "Real estate agent, residential", "commission only", "Bay Door Realty", "contract", "Residential listing agent role, leads provided.", license="CA DRE required", territory="east bay"),
    _j("sales", "Retail sales lead at outdoor store", "$26 per hour", "Trailhead Outfitters", "full-time", "Lead retail floor shifts at outdoor gear store.", schedule="Wed-Sun", commission="2%"),
    _j("sales", "Auto sales associate", "$60k - $120k OTE", "Highway 101 Honda", "full-time", "New and used car sales, leads from showroom traffic.", schedule="Tue-Sat", commission="tiered"),
    _j("sales", "B2B field sales, restaurant supply", "$80k - $120k OTE", "Crestline Foodservice", "full-time", "Sell foodservice supplies to restaurants in the East Bay.", quota="$1.5M annual", territory="east bay"),
    _j("sales", "Jewelry consultant, downtown SF", "$28 per hour plus commission", "Halcyon Jewelry", "part-time", "Greet customers and consult on engagement and custom work.", schedule="Tue-Sat", commission="3%"),

    # ---------------- jobs: skilled_trade (+6) ----------------
    _j("skilled_trade", "Licensed electrician, residential", "$58 per hour", "Bayline Electric", "full-time", "Residential service electrician, panel upgrades, EV chargers.", license="C-10", vehicle="provided", benefits="medical dental"),
    _j("skilled_trade", "Plumber, commercial service", "$62 per hour", "Bayflow Plumbing", "full-time", "Commercial plumbing service tech, on-call rotation.", license="C-36", vehicle="provided", benefits="medical dental"),
    _j("skilled_trade", "HVAC service technician", "$54 per hour", "Coastline HVAC", "full-time", "Service tech for residential and light commercial HVAC.", license="EPA 608", vehicle="provided", benefits="medical dental"),
    _j("skilled_trade", "Welder, structural steel", "$48 per hour", "Foundry Iron Works", "full-time", "Structural steel welder, certified MIG and stick.", license="AWS certified", shift="6am-2pm"),
    _j("skilled_trade", "Finish carpenter", "$52 per hour", "Birch Lane Builders", "full-time", "Finish carpenter for high-end residential remodels.", license="no", vehicle="own", benefits="health stipend"),
    _j("skilled_trade", "Auto mechanic, foreign cars", "$48 per hour", "Garage 19", "full-time", "Service tech with diagnostic experience on European cars.", license="ASE preferred", shift="weekday daytime"),

    # ---------------- services: automotive_services (+10) ----------------
    _g("automotive_services", "Mobile mechanic, oil change at your driveway", 85, "new", "Mobile mechanic for oil changes and minor repairs at your home.", service="oil change", coverage="bay area", insured="yes"),
    _g("automotive_services", "Tire rotation and balance", 60, "new", "Tire rotation and balance at our shop, walk-ins welcome.", service="tire rotation", duration="30 min"),
    _g("automotive_services", "Brake pad replacement, front", 220, "new", "Front brake pad replacement, lifetime pads, 2-year labor warranty.", service="brakes front", warranty="2 year"),
    _g("automotive_services", "Smog check, certified station", 55, "new", "STAR certified smog check, gas and diesel vehicles welcome.", service="smog check", certification="STAR"),
    _g("automotive_services", "Full detail with clay bar", 280, "new", "Interior and exterior detail with clay bar and wax.", service="detail", duration="4 hours"),
    _g("automotive_services", "Paintless dent removal", 180, "new", "Mobile paintless dent removal, most door dings done in under an hour.", service="dent removal", coverage="east bay"),
    _g("automotive_services", "Windshield replacement, OEM glass", 380, "new", "Mobile windshield replacement, OEM glass with warranty.", service="windshield", warranty="lifetime"),
    _g("automotive_services", "Transmission service", 240, "new", "Transmission fluid and filter service, includes inspection.", service="transmission", duration="2 hours"),
    _g("automotive_services", "EV battery diagnostic", 180, "new", "Specialized EV diagnostic, traction battery health report.", service="EV diagnostic", duration="90 min"),
    _g("automotive_services", "Pre-purchase inspection", 145, "new", "150-point pre-purchase inspection at our shop or your seller.", service="pre purchase", duration="90 min"),

    # ---------------- services: computer_services (+8) ----------------
    _g("computer_services", "PC virus and malware removal", 95, "new", "Remote or on-site malware removal, includes 30-day follow up.", service="malware removal", warranty="30 day"),
    _g("computer_services", "Home wifi mesh installation", 180, "new", "Install and tune mesh wifi for whole-home coverage.", service="wifi install", duration="2 hours"),
    _g("computer_services", "Smart home setup, hub and devices", 240, "new", "Setup smart home hub, lights, locks, and thermostat.", service="smart home", duration="3 hours"),
    _g("computer_services", "Printer setup and troubleshooting", 80, "new", "On-site printer install and network troubleshooting.", service="printer setup", duration="1 hour"),
    _g("computer_services", "Cloud backup and data migration", 165, "new", "Configure cloud backup and migrate files from old device.", service="data migration", duration="2 hours"),
    _g("computer_services", "Custom PC builds for gaming and work", 320, "new", "Custom PC builds, parts cost not included.", service="custom build", warranty="1 year labor"),
    _g("computer_services", "Network rewiring and ethernet drops", 280, "new", "Add ethernet drops to one or two rooms in your home.", service="network wiring", duration="half day"),
    _g("computer_services", "Mac OS reinstall and tune up", 110, "new", "Fresh Mac OS install with data backup and restore.", service="mac tune up", duration="2 hours"),

    # ---------------- services: creative_services (+10) ----------------
    _g("creative_services", "Family portrait photographer", 350, "new", "One-hour family portrait session at a park or your home.", service="portrait session", duration="1 hour", deliverables="30 edited"),
    _g("creative_services", "Wedding videographer, full day", 2400, "new", "Full day wedding video coverage with edited highlight film.", service="wedding video", duration="8 hours", deliverables="highlight film"),
    _g("creative_services", "Logo design for small business", 480, "new", "Logo design package with three concepts and revisions.", service="logo design", revisions="3 rounds", deliverables="vector files"),
    _g("creative_services", "Brand identity and style guide", 1800, "new", "Brand identity package with logo, color, and type system.", service="brand identity", revisions="3 rounds", deliverables="style guide"),
    _g("creative_services", "Custom watercolor pet portrait", 180, "new", "Custom watercolor pet portrait from a photo you provide.", service="pet portrait", duration="2 weeks", deliverables="11x14 print"),
    _g("creative_services", "Web design for small business", 2200, "new", "Single page small business website with up to five sections.", service="web design", revisions="2 rounds", deliverables="responsive site"),
    _g("creative_services", "Voiceover for explainer videos", 280, "new", "Professional voiceover for explainer or training videos.", service="voiceover", duration="up to 5 minutes", deliverables="WAV files"),
    _g("creative_services", "Animator for short social videos", 580, "new", "15 second animated explainer video for social media.", service="animation", duration="15 seconds", deliverables="MP4 files"),
    _g("creative_services", "Copywriter for landing pages", 320, "new", "Conversion copywriting for one product or service landing page.", service="copywriting", revisions="2 rounds", deliverables="Google doc"),
    _g("creative_services", "Instagram content batch shoot", 480, "new", "Half-day shoot producing two weeks of Instagram content.", service="content shoot", duration="4 hours", deliverables="40 edited"),

    # ---------------- services: household_services (+12) ----------------
    _g("household_services", "Standard house cleaning, weekly", 140, "new", "Weekly standard house cleaning for two bedroom homes.", service="standard clean", frequency="weekly", supplies="provided"),
    _g("household_services", "Deep cleaning, one time", 320, "new", "One-time deep clean for two bedroom apartments, includes baseboards.", service="deep clean", duration="5 hours", supplies="provided"),
    _g("household_services", "Move out cleaning service", 380, "new", "Move out clean including oven and fridge interior.", service="move out clean", duration="6 hours", supplies="provided"),
    _g("household_services", "Window cleaning, inside and out", 220, "new", "Window cleaning service for single story homes.", service="window clean", height="up to 2 story", supplies="provided"),
    _g("household_services", "Gutter cleaning and tune up", 260, "new", "Gutter clearing and tune up for single story homes.", service="gutter clean", duration="2 hours"),
    _g("household_services", "Pressure washing, driveway and patio", 240, "new", "Pressure wash driveway, walkways, and patio surfaces.", service="pressure wash", duration="3 hours"),
    _g("household_services", "Lawn mowing and edging, biweekly", 95, "new", "Biweekly lawn mow and edge for small to medium yards.", service="lawn care", frequency="biweekly", area="up to 1500 sqft"),
    _g("household_services", "Pest control, quarterly service", 165, "new", "Quarterly pest control service, exterior perimeter and entry points.", service="pest control", frequency="quarterly", coverage="exterior"),
    _g("household_services", "Interior painting, single room", 480, "new", "Paint one bedroom or living room, includes light prep and one coat.", service="painting", duration="1 day", coverage="walls only"),
    _g("household_services", "Handyman, two hour minimum", 95, "new", "Handyman services, drywall patch, fixtures, mounting.", service="handyman", minimum="2 hours", hourly="$95"),
    _g("household_services", "Closet and pantry organizer", 220, "new", "Professional organizer for closets and pantries.", service="organizing", duration="3 hours", deliverables="labels included"),
    _g("household_services", "Pet sitter, weekend visits", 65, "new", "Weekend pet sitting visits, twice daily walks and feeding.", service="pet sitting", duration="weekend", frequency="twice daily"),

    # ---------------- services: labor_move (+8) ----------------
    _g("labor_move", "Two movers and a box truck", 165, "new", "Two movers and a 26 foot box truck for local moves.", crew="2 people", rate="$165 per hour", truck="26 ft box"),
    _g("labor_move", "Piano moving specialists", 480, "new", "Piano moving specialists with proper equipment and insurance.", crew="3 people", rate="flat $480 upright", insured="yes"),
    _g("labor_move", "Junk hauling and dump runs", 280, "new", "Full service junk hauling and dump runs for one truck loads.", crew="2 people", rate="$280 per load", truck="dump trailer"),
    _g("labor_move", "Cross-bay moving service", 220, "new", "East bay to peninsula moving with packing supplies included.", crew="3 people", rate="$220 per hour", truck="20 ft truck"),
    _g("labor_move", "Last minute moving labor", 95, "new", "Same day moving labor for stairs and loading help.", crew="2 people", rate="$95 per hour", truck="not included"),
    _g("labor_move", "Storage unit loading help", 110, "new", "Help loading and organizing storage units, two hour minimum.", crew="2 people", rate="$110 per hour", truck="not included"),
    _g("labor_move", "Office move specialists", 380, "new", "Weekend office moves including IT equipment.", crew="4 people", rate="$380 per hour", truck="2 trucks"),
    _g("labor_move", "Senior moving and downsizing", 175, "new", "Compassionate senior moves with sorting and packing help.", crew="3 people", rate="$175 per hour", truck="20 ft truck"),

    # ---------------- services: lessons (+9) ----------------
    _g("lessons", "Piano lessons for adults, beginner", 70, "new", "Adult beginner piano lessons in studio or online.", format="in person or online", rate="$70 per hour", subjects="classical jazz"),
    _g("lessons", "Guitar lessons, all levels", 60, "new", "Acoustic and electric guitar lessons for all levels.", format="in person or online", rate="$60 per hour", subjects="acoustic electric"),
    _g("lessons", "Voice lessons for musical theatre", 80, "new", "Voice lessons specializing in musical theatre repertoire.", format="in person", rate="$80 per hour", subjects="musical theatre"),
    _g("lessons", "Spanish conversation classes", 50, "new", "Spanish conversation classes in small groups or one-on-one.", format="online", rate="$50 per hour", subjects="Spanish"),
    _g("lessons", "Mandarin tutoring for kids", 55, "new", "Mandarin tutoring for elementary kids, fun and patient.", format="in person or online", rate="$55 per hour", subjects="Mandarin"),
    _g("lessons", "Drawing and sketching lessons", 65, "new", "Drawing and sketching for teens and adults, materials list provided.", format="in person", rate="$65 per hour", subjects="drawing"),
    _g("lessons", "Beginner yoga, private sessions", 90, "new", "Private beginner yoga sessions in your home or local park.", format="in person", rate="$90 per hour", subjects="hatha vinyasa"),
    _g("lessons", "Swim lessons, kids 4-10", 75, "new", "Private swim lessons for kids ages 4-10 at community pools.", format="in person", rate="$75 per half hour", subjects="swim safety"),
    _g("lessons", "Salsa dance classes, beginner", 45, "new", "Beginner salsa dance classes, drop-in or 4-week series.", format="in person", rate="$45 per class", subjects="salsa"),

    # ---------------- community: events (+8) ----------------
    _g("events", "Saturday farmers market in Oakland", 0, "new", "Weekly Saturday farmers market with 30 plus vendors.", date="Saturday", time="9:00 AM", bring="reusable bags"),
    _g("events", "Friday art walk in the Mission", 0, "new", "Monthly Friday night gallery and studio art walk.", date="Friday", time="6:00 PM", bring="comfortable shoes"),
    _g("events", "Open mic night at corner cafe", 0, "new", "Weekly open mic night, sign up at 7:00 PM.", date="Thursday", time="7:30 PM", bring="instrument"),
    _g("events", "Trivia night at neighborhood pub", 0, "new", "Wednesday trivia night, teams up to six.", date="Wednesday", time="7:00 PM", bring="team name"),
    _g("events", "Book club kickoff for summer reads", 0, "new", "Kickoff meeting for summer book club, free coffee.", date="Saturday", time="10:00 AM", bring="this months book"),
    _g("events", "Sunday community bike ride", 0, "new", "Casual Sunday community bike ride, 12 miles flat.", date="Sunday", time="9:00 AM", bring="bike helmet water"),
    _g("events", "Saturday Bay Trail hike", 0, "new", "Group hike along the Bay Trail, 5 miles.", date="Saturday", time="8:00 AM", bring="water snacks"),
    _g("events", "Gardening workshop, balcony herbs", 0, "new", "Hands on workshop for growing herbs on a balcony.", date="Sunday", time="11:00 AM", bring="empty pot"),

    # ---------------- community: volunteers (+6) ----------------
    _g("volunteers", "Food bank sorting shift", 0, "new", "Two hour shift sorting and packing groceries at food bank.", date="Saturday", time="9:00 AM", skills="able to lift 25 lb"),
    _g("volunteers", "Beach cleanup at Ocean Beach", 0, "new", "Saturday morning beach cleanup, gloves and bags provided.", date="Saturday", time="9:30 AM", skills="able to walk 2 miles"),
    _g("volunteers", "Animal shelter dog walkers", 0, "new", "Weekend dog walking volunteers, basic dog handling training required.", date="Saturday Sunday", time="varies", skills="dog handling"),
    _g("volunteers", "Hospital greeter volunteer", 0, "new", "Greet and direct patients in hospital lobby.", date="weekly", time="weekday daytime", skills="friendly customer service"),
    _g("volunteers", "Reading tutor for elementary kids", 0, "new", "Volunteer one hour per week tutoring reading at after-school program.", date="Tuesday Thursday", time="3:30 PM", skills="patient with kids"),
    _g("volunteers", "Soup kitchen meal service", 0, "new", "Help serve evening meals at downtown soup kitchen.", date="Wednesday", time="5:00 PM", skills="food handler card preferred"),

    # ---------------- community: artists (+8) ----------------
    _g("artists", "Seeking life drawing model", 120, "new", "Weekly life drawing session seeks model, 2 hour session.", budget="$120", format="in person", deadline="June 1"),
    _g("artists", "Mural artist for cafe wall", 1800, "new", "Looking for muralist for 12x8 ft cafe interior wall.", budget="$1800", format="acrylic", deadline="July 15"),
    _g("artists", "Gallery sitting trade, Mission", 0, "new", "Trade gallery sitting hours for studio space access.", budget="trade", format="weekly shift", deadline="June 15"),
    _g("artists", "Band seeks drummer for indie set", 0, "new", "Indie rock band looking for steady drummer for weekend sets.", budget="paid gigs", format="band practice weekly", deadline="ongoing"),
    _g("artists", "Painter swap, monthly meetups", 0, "new", "Painters swap meetup, share critique and supplies.", budget="free", format="monthly", deadline="ongoing"),
    _g("artists", "Indie film seeks DP for shorts", 0, "new", "Indie short film project seeks director of photography.", budget="deferred pay", format="weekend shoots", deadline="June 30"),
    _g("artists", "Podcast guest, queer history", 0, "new", "Independent podcast seeks guests for queer history series.", budget="unpaid", format="remote recording", deadline="rolling"),
    _g("artists", "Illustrator collab for chapbook", 220, "new", "Illustrator collaboration for a poetry chapbook, six pieces.", budget="$220", format="ink and digital", deadline="August 1"),

    # ---------------- community: classes (+11) ----------------
    _g("classes", "Beginner pottery wheel class", 220, "new", "Six week beginner pottery wheel class, materials included.", duration="6 weeks", capacity="8 students", level="beginner"),
    _g("classes", "Ceramics handbuilding workshop", 160, "new", "Two day ceramics handbuilding workshop, no experience required.", duration="2 days", capacity="10 students", level="beginner"),
    _g("classes", "Floor loom weaving series", 280, "new", "Four week floor loom weaving series.", duration="4 weeks", capacity="6 students", level="beginner"),
    _g("classes", "Conversational French, evenings", 240, "new", "Six week conversational French class for adult learners.", duration="6 weeks", capacity="12 students", level="intermediate"),
    _g("classes", "Coding for kids, Scratch basics", 180, "new", "Four week Scratch coding class for kids 8-12.", duration="4 weeks", capacity="10 students", level="beginner"),
    _g("classes", "Adult ballet, beginner welcome", 160, "new", "Adult beginner ballet, drop in or 8 week series.", duration="8 weeks", capacity="20 students", level="beginner"),
    _g("classes", "Yoga teacher training info session", 0, "new", "Free info session for 200 hour yoga teacher training cohort.", duration="2 hours", capacity="open", level="info session"),
    _g("classes", "Plein air drawing class", 140, "new", "Outdoor plein air drawing, three weekend sessions.", duration="3 weeks", capacity="10 students", level="all levels"),
    _g("classes", "Smartphone photography workshop", 120, "new", "One day smartphone photography workshop in the city.", duration="1 day", capacity="12 students", level="all levels"),
    _g("classes", "Beginner jewelry making, silver", 260, "new", "Three session beginner silversmithing class.", duration="3 weeks", capacity="6 students", level="beginner"),
    _g("classes", "Hand tools woodworking basics", 320, "new", "Four week hand tool woodworking for absolute beginners.", duration="4 weeks", capacity="6 students", level="beginner"),

    # ---------------- community: groups (+6) ----------------
    _g("groups", "Saturday morning hiking group", 0, "new", "Weekly Saturday morning hikes around the Bay Area, 5-10 miles.", schedule="Saturday weekly", capacity="open", level="all levels"),
    _g("groups", "Mission book club", 0, "new", "Monthly book club focused on contemporary fiction.", schedule="first Monday monthly", capacity="12", level="all readers"),
    _g("groups", "New parents support group", 0, "new", "Weekly support group for new parents with infants.", schedule="Thursday weekly", capacity="open", level="parents 0-12 mo"),
    _g("groups", "Oakland running club, easy pace", 0, "new", "Weekly easy pace 5k run from Lake Merritt.", schedule="Tuesday weekly", capacity="open", level="beginner friendly"),
    _g("groups", "Board game night, eurogames", 0, "new", "Weekly board game night focused on eurogames.", schedule="Friday weekly", capacity="20", level="all levels"),
    _g("groups", "Mandarin and English language exchange", 0, "new", "Weekly language exchange meetup for Mandarin and English learners.", schedule="Wednesday weekly", capacity="open", level="all levels"),

    # ---------------- community: lost_found (+6) ----------------
    _g("lost_found", "Lost tabby cat near Dolores Park", 0, "new", "Female tabby, white chest, microchipped, very shy. Reward offered.", lost_or_found="lost", area_lost="dolores park", reward="$200"),
    _g("lost_found", "Found gray cat near 24th BART", 0, "new", "Friendly gray cat, no collar, found near 24th Street BART.", lost_or_found="found", area_found="24th and mission", scanned="no chip"),
    _g("lost_found", "Lost wedding band, Ocean Beach", 0, "new", "Gold wedding band lost in the sand near Sloat. Sentimental value.", lost_or_found="lost", area_lost="ocean beach", reward="$300"),
    _g("lost_found", "Found house keys at Lake Merritt", 0, "new", "Set of keys on a green carabiner, found by the pergola.", lost_or_found="found", area_found="lake merritt", contact_pref="email"),
    _g("lost_found", "Lost iPhone at Ferry Building", 0, "new", "Black iPhone in clear case, lost Saturday at the Ferry Building.", lost_or_found="lost", area_lost="ferry building", reward="$150"),
    _g("lost_found", "Found prescription glasses, BART", 0, "new", "Wire-frame prescription glasses found on Pittsburg-Bay Point train.", lost_or_found="found", area_found="BART pittsburg line", scanned="case has name"),
]


# ----- benchmark user extras -----
# Each entry: (user_email, listing_title_keyword, note)
BULK_SAVES = [
    ("ben.k@test.com", "Marin commuter bike", "thinking about an upgrade"),
    ("ben.k@test.com", "Standing desk frame", "for the home office"),
    ("ben.k@test.com", "LG 55 inch 4K OLED", "compare with my current TV"),
    ("carla.m@test.com", "Berkeley north side 2BR", "tour next weekend"),
    ("carla.m@test.com", "Bosch 800 series dishwasher", "for the kitchen remodel"),
    ("carla.m@test.com", "Yamaha P-125 digital piano", "for the kids"),
    ("david.p@test.com", "2017 Toyota Prius Two", "ask about service records"),
    ("david.p@test.com", "Palo Alto downtown 1BR", "shortlist"),
    ("alice.j@test.com", "Mission 2BR top floor with deck", "weekend tour"),
    ("alice.j@test.com", "Mid-century walnut sideboard", "matches the entry"),
]


# Conversation chains. Each entry:
#   (user_email, listing_title_keyword, sender_name, sender_email, body,
#    direction, hours_ago, is_read)
# `user_email = None` means the message is anonymous (no inbox owner).
BULK_MESSAGES = [
    # Thread 1: Alice -> Ben re: Marin commuter bike (Ben is owner of conversation? we attach to Alice and Ben mailboxes)
    ("alice.j@test.com", "Marin commuter bike", "Alice Johnson", "alice.j@test.com",
     "Hi, is the Marin commuter still available? I would love to test ride this weekend.", "outbound", 48, True),
    ("ben.k@test.com", "Marin commuter bike", "Alice Johnson", "alice.j@test.com",
     "Hi, is the Marin commuter still available? I would love to test ride this weekend.", "inbound", 48, True),
    ("ben.k@test.com", "Marin commuter bike", "Ben Kim", "ben.k@test.com",
     "Hi Alice, yes it is. I am free Saturday after 10am at the Rockridge BART parking lot.", "outbound", 40, True),
    ("alice.j@test.com", "Marin commuter bike", "Ben Kim", "ben.k@test.com",
     "Hi Alice, yes it is. I am free Saturday after 10am at the Rockridge BART parking lot.", "inbound", 40, True),
    ("alice.j@test.com", "Marin commuter bike", "Alice Johnson", "alice.j@test.com",
     "Perfect, see you at 10:30. Cash on hand if it rides well.", "outbound", 30, True),
    ("ben.k@test.com", "Marin commuter bike", "Alice Johnson", "alice.j@test.com",
     "Perfect, see you at 10:30. Cash on hand if it rides well.", "inbound", 30, False),

    # Thread 2: Carla -> David re: 2017 Toyota Prius Two
    ("carla.m@test.com", "2017 Toyota Prius Two", "Carla Martinez", "carla.m@test.com",
     "Hi, do you have the service records and is the title in hand?", "outbound", 36, True),
    ("david.p@test.com", "2017 Toyota Prius Two", "Carla Martinez", "carla.m@test.com",
     "Hi, do you have the service records and is the title in hand?", "inbound", 36, True),
    ("david.p@test.com", "2017 Toyota Prius Two", "David Patel", "david.p@test.com",
     "Yes to both. Dealer service every 10k. Title is clean in my name.", "outbound", 28, True),
    ("carla.m@test.com", "2017 Toyota Prius Two", "David Patel", "david.p@test.com",
     "Yes to both. Dealer service every 10k. Title is clean in my name.", "inbound", 28, True),
    ("carla.m@test.com", "2017 Toyota Prius Two", "Carla Martinez", "carla.m@test.com",
     "Would you take 11800 if I come pre-approved on Saturday?", "outbound", 22, True),
    ("david.p@test.com", "2017 Toyota Prius Two", "Carla Martinez", "carla.m@test.com",
     "Would you take 11800 if I come pre-approved on Saturday?", "inbound", 22, False),

    # Thread 3: Alice -> Carla re: Berkeley north side 2BR
    ("alice.j@test.com", "Berkeley north side 2BR", "Alice Johnson", "alice.j@test.com",
     "Hi, is the Berkeley 2BR still available for June 15 move in?", "outbound", 24, True),
    ("carla.m@test.com", "Berkeley north side 2BR", "Alice Johnson", "alice.j@test.com",
     "Hi, is the Berkeley 2BR still available for June 15 move in?", "inbound", 24, True),
    ("carla.m@test.com", "Berkeley north side 2BR", "Carla Martinez", "carla.m@test.com",
     "It is. Showings Saturday 11am and Sunday 1pm. Bring a checkbook and ID.", "outbound", 18, True),
    ("alice.j@test.com", "Berkeley north side 2BR", "Carla Martinez", "carla.m@test.com",
     "It is. Showings Saturday 11am and Sunday 1pm. Bring a checkbook and ID.", "inbound", 18, False),

    # Thread 4: Ben re: Standing desk frame buyer
    ("ben.k@test.com", "Standing desk frame", "Priya Iyer", "priya@example.test",
     "Hi, is the standing desk still available? I can pickup tomorrow evening.", "inbound", 14, False),
    ("ben.k@test.com", "Standing desk frame", "Ben Kim", "ben.k@test.com",
     "Yes, available. I am in Berkeley off Shattuck. Anytime after 6pm.", "outbound", 12, True),

    # Thread 5: David re: Palo Alto downtown 1BR
    ("david.p@test.com", "Palo Alto downtown 1BR", "Maya Reed", "maya@example.test",
     "Hello, I am relocating in July, is the unit still listed?", "inbound", 9, False),
    ("david.p@test.com", "Palo Alto downtown 1BR", "David Patel", "david.p@test.com",
     "Yes, still available July 1. Happy to schedule a virtual tour first.", "outbound", 7, True),
]
