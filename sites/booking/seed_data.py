"""Seed data for booking.com mirror — real scraped hotels + curated content."""
import json
from pathlib import Path


def get_image_map():
    p = Path(__file__).parent / 'image_map.json'
    with open(p) as f:
        return json.load(f)


def get_hotel_data():
    p = Path(__file__).parent / 'hotel_data.json'
    with open(p) as f:
        return json.load(f)


# Destination categories
DESTINATION_CATEGORIES = [
    {'slug': 'city-breaks', 'name': 'City breaks', 'description': 'Culture, food, and vibrant nightlife', 'icon': 'city'},
    {'slug': 'beach', 'name': 'Beach destinations', 'description': 'Sun, sand, and surf', 'icon': 'beach'},
    {'slug': 'ski', 'name': 'Ski resorts', 'description': 'Snow-capped mountains and alpine adventure', 'icon': 'ski'},
    {'slug': 'nature', 'name': 'Nature & outdoors', 'description': 'Escape into the wild', 'icon': 'tree'},
    {'slug': 'luxury', 'name': 'Luxury stays', 'description': 'Five-star service and world-class amenities', 'icon': 'crown'},
    {'slug': 'family', 'name': 'Family-friendly', 'description': 'Trips the whole family will love', 'icon': 'family'},
    {'slug': 'romantic', 'name': 'Romantic getaways', 'description': 'Perfect for couples', 'icon': 'heart'},
    {'slug': 'business', 'name': 'Business travel', 'description': 'Work-friendly stays', 'icon': 'briefcase'},
]

# Property type categories
PROPERTY_TYPES = [
    {'slug': 'hotels', 'name': 'Hotels', 'description': 'Traditional hotel comforts', 'icon': 'building'},
    {'slug': 'apartments', 'name': 'Apartments', 'description': 'Home-like spaces with kitchens', 'icon': 'apartment'},
    {'slug': 'resorts', 'name': 'Resorts', 'description': 'All-inclusive luxury', 'icon': 'palm'},
    {'slug': 'villas', 'name': 'Villas', 'description': 'Private homes for groups', 'icon': 'villa'},
    {'slug': 'b-and-bs', 'name': 'Bed and Breakfasts', 'description': 'Cosy, personal stays', 'icon': 'bed'},
    {'slug': 'hostels', 'name': 'Hostels', 'description': 'Budget-friendly social stays', 'icon': 'hostel'},
    {'slug': 'guesthouses', 'name': 'Guest Houses', 'description': 'Family-run hospitality', 'icon': 'home'},
    {'slug': 'cabins', 'name': 'Cabins', 'description': 'Rustic getaways', 'icon': 'cabin'},
]

# City base info with real content
CITY_INFO = {
    'nyc': {
        'display': 'New York',
        'slug': 'new-york',
        'country': 'United States',
        'country_code': 'us',
        'description': 'The city that never sleeps. Iconic skyline, world-class museums, Broadway shows, and endless food.',
        'lat': 40.7128,
        'lng': -74.0060,
        'properties_count': 4827,
        'average_rating': 8.2,
    },
    'paris': {
        'display': 'Paris',
        'slug': 'paris',
        'country': 'France',
        'country_code': 'fr',
        'description': 'The City of Light. Art, romance, and timeless Parisian charm along the Seine.',
        'lat': 48.8566,
        'lng': 2.3522,
        'properties_count': 6512,
        'average_rating': 8.4,
    },
    'london': {
        'display': 'London',
        'slug': 'london',
        'country': 'United Kingdom',
        'country_code': 'gb',
        'description': 'Historic royal heritage meets cutting-edge culture in this global capital.',
        'lat': 51.5074,
        'lng': -0.1278,
        'properties_count': 5931,
        'average_rating': 8.3,
    },
    'tokyo': {
        'display': 'Tokyo',
        'slug': 'tokyo',
        'country': 'Japan',
        'country_code': 'jp',
        'description': 'Dazzling neon, ancient temples, Michelin-starred ramen, and unmatched hospitality.',
        'lat': 35.6762,
        'lng': 139.6503,
        'properties_count': 7245,
        'average_rating': 8.6,
    },
    'dubai': {
        'display': 'Dubai',
        'slug': 'dubai',
        'country': 'United Arab Emirates',
        'country_code': 'ae',
        'description': 'Futuristic skyline, seven-star luxury, and desert adventure in the heart of the Gulf.',
        'lat': 25.2048,
        'lng': 55.2708,
        'properties_count': 3104,
        'average_rating': 8.5,
    },
    'rome': {
        'display': 'Rome',
        'slug': 'rome',
        'country': 'Italy',
        'country_code': 'it',
        'description': 'Walk through 2,000 years of history. From the Colosseum to fresh pasta in hidden trattorias.',
        'lat': 41.9028,
        'lng': 12.4964,
        'properties_count': 4512,
        'average_rating': 8.4,
    },
    'barcelona': {
        'display': 'Barcelona',
        'slug': 'barcelona',
        'country': 'Spain',
        'country_code': 'es',
        'description': 'Gaudí masterpieces, Mediterranean beaches, and the best tapas on the Catalan coast.',
        'lat': 41.3851,
        'lng': 2.1734,
        'properties_count': 3876,
        'average_rating': 8.3,
    },
    'bali': {
        'display': 'Bali',
        'slug': 'bali',
        'country': 'Indonesia',
        'country_code': 'id',
        'description': 'Island of the Gods. Rice terraces, sacred temples, surf beaches and wellness retreats.',
        'lat': -8.4095,
        'lng': 115.1889,
        'properties_count': 8203,
        'average_rating': 8.7,
    },
    'amsterdam': {
        'display': 'Amsterdam',
        'slug': 'amsterdam',
        'country': 'Netherlands',
        'country_code': 'nl',
        'description': 'Canals, cycling, world-class museums, and a liberal vibe in the heart of Europe.',
        'lat': 52.3676,
        'lng': 4.9041,
        'properties_count': 2345,
        'average_rating': 8.4,
    },
    'singapore': {
        'display': 'Singapore',
        'slug': 'singapore',
        'country': 'Singapore',
        'country_code': 'sg',
        'description': 'A garden city-state blending cutting-edge architecture, street food, and pristine nature.',
        'lat': 1.3521,
        'lng': 103.8198,
        'properties_count': 1876,
        'average_rating': 8.5,
    },
    'maldives': {
        'display': 'Maldives',
        'slug': 'maldives',
        'country': 'Maldives',
        'country_code': 'mv',
        'description': 'Crystal-clear waters, overwater bungalows, and unparalleled tropical luxury.',
        'lat': 3.2028,
        'lng': 73.2207,
        'properties_count': 643,
        'average_rating': 9.1,
    },
    'bangkok': {
        'display': 'Bangkok',
        'slug': 'bangkok',
        'country': 'Thailand',
        'country_code': 'th',
        'description': 'Bustling street food, ornate temples, and the finest rooftop bars in Southeast Asia.',
        'lat': 13.7563,
        'lng': 100.5018,
        'properties_count': 5734,
        'average_rating': 8.3,
    },
    'hongkong': {
        'display': 'Hong Kong',
        'slug': 'hong-kong',
        'country': 'Hong Kong',
        'country_code': 'hk',
        'description': 'East meets West — dizzying skyline, Michelin dim sum, and hidden hiking trails.',
        'lat': 22.3193,
        'lng': 114.1694,
        'properties_count': 2154,
        'average_rating': 8.4,
    },
    'istanbul': {
        'display': 'Istanbul',
        'slug': 'istanbul',
        'country': 'Turkey',
        'country_code': 'tr',
        'description': 'Where Europe meets Asia. Byzantine mosques, Ottoman palaces, and the Grand Bazaar.',
        'lat': 41.0082,
        'lng': 28.9784,
        'properties_count': 4892,
        'average_rating': 8.5,
    },
    'sydney': {
        'display': 'Sydney',
        'slug': 'sydney',
        'country': 'Australia',
        'country_code': 'au',
        'description': 'Iconic harbour, stunning beaches, and a laid-back cosmopolitan lifestyle.',
        'lat': -33.8688,
        'lng': 151.2093,
        'properties_count': 2987,
        'average_rating': 8.5,
    },
    'losangeles': {
        'display': 'Los Angeles',
        'slug': 'los-angeles',
        'country': 'United States',
        'country_code': 'us',
        'description': 'Hollywood, sunshine, Pacific beaches, and some of the best food scenes in the US.',
        'lat': 34.0522,
        'lng': -118.2437,
        'properties_count': 3542,
        'average_rating': 8.2,
    },
    'berlin': {
        'display': 'Berlin',
        'slug': 'berlin',
        'country': 'Germany',
        'country_code': 'de',
        'description': 'Layered history, world-class museums, and one of Europe\'s most vibrant nightlife scenes.',
        'lat': 52.5200,
        'lng': 13.4050,
        'properties_count': 3254,
        'average_rating': 8.4,
    },
    'prague': {
        'display': 'Prague',
        'slug': 'prague',
        'country': 'Czech Republic',
        'country_code': 'cz',
        'description': 'Fairy-tale cobblestone streets, Gothic cathedrals, and world-famous beer.',
        'lat': 50.0755,
        'lng': 14.4378,
        'properties_count': 2765,
        'average_rating': 8.5,
    },
    'vienna': {
        'display': 'Vienna',
        'slug': 'vienna',
        'country': 'Austria',
        'country_code': 'at',
        'description': 'Imperial palaces, classical music, and the city of coffee culture.',
        'lat': 48.2082,
        'lng': 16.3738,
        'properties_count': 2198,
        'average_rating': 8.6,
    },
    'venice': {
        'display': 'Venice',
        'slug': 'venice',
        'country': 'Italy',
        'country_code': 'it',
        'description': 'Floating city of canals, gondolas, and Renaissance art.',
        'lat': 45.4408,
        'lng': 12.3155,
        'properties_count': 1843,
        'average_rating': 8.6,
    },
    'santorini': {
        'display': 'Santorini',
        'slug': 'santorini',
        'country': 'Greece',
        'country_code': 'gr',
        'description': 'Whitewashed villages perched on volcanic cliffs with sunsets to remember.',
        'lat': 36.3932,
        'lng': 25.4615,
        'properties_count': 876,
        'average_rating': 8.9,
    },
    'mexicocity': {
        'display': 'Mexico City',
        'slug': 'mexico-city',
        'country': 'Mexico',
        'country_code': 'mx',
        'description': 'Vibrant colours, world-renowned cuisine, and a thriving contemporary art scene.',
        'lat': 19.4326,
        'lng': -99.1332,
        'properties_count': 3421,
        'average_rating': 8.5,
    },
    'rio': {
        'display': 'Rio de Janeiro',
        'slug': 'rio-de-janeiro',
        'country': 'Brazil',
        'country_code': 'br',
        'description': 'Copacabana, Christ the Redeemer, samba rhythms, and unforgettable beaches.',
        'lat': -22.9068,
        'lng': -43.1729,
        'properties_count': 2876,
        'average_rating': 8.3,
    },
    'jakarta': {
        'display': 'Jakarta',
        'slug': 'jakarta',
        'country': 'Indonesia',
        'country_code': 'id',
        'description': 'Indonesia\'s sprawling capital offers vibrant street food, colonial architecture, and modern shopping.',
        'lat': -6.2088,
        'lng': 106.8456,
        'properties_count': 3421,
        'average_rating': 8.0,
    },
    'ohio': {
        'display': 'Ohio',
        'slug': 'ohio',
        'country': 'United States',
        'country_code': 'us',
        'description': 'The Buckeye State offers charming cities, rolling hills, and heartland hospitality.',
        'lat': 40.4173,
        'lng': -82.9071,
        'properties_count': 1200,
        'average_rating': 7.9,
    },
    'varanasi': {
        'display': 'Varanasi',
        'slug': 'varanasi',
        'country': 'India',
        'country_code': 'in',
        'description': 'One of the oldest living cities in the world. Sacred ghats, the Kashi Vishwanath Temple, and spiritual heritage.',
        'lat': 25.3176,
        'lng': 82.9739,
        'properties_count': 890,
        'average_rating': 8.1,
    },
    'chennai': {
        'display': 'Chennai',
        'slug': 'chennai',
        'country': 'India',
        'country_code': 'in',
        'description': 'Gateway to South India with stunning temples, Marina Beach, and a rich cultural heritage.',
        'lat': 13.0827,
        'lng': 80.2707,
        'properties_count': 1540,
        'average_rating': 8.0,
    },
    'chicago': {
        'display': 'Chicago',
        'slug': 'chicago',
        'country': 'United States',
        'country_code': 'us',
        'description': 'Windy City: world-class architecture, deep-dish pizza, blues music, and lakefront parks. Downtown area includes the Magnificent Mile and Millennium Park.',
        'lat': 41.8781,
        'lng': -87.6298,
        'properties_count': 2876,
        'average_rating': 8.3,
    },
    'lisbon': {
        'display': 'Lisbon',
        'slug': 'lisbon',
        'country': 'Portugal',
        'country_code': 'pt',
        'description': 'Pastel-coloured neighbourhoods, pastel de nata, tram 28, and stunning viewpoints over the Tagus.',
        'lat': 38.7223,
        'lng': -9.1393,
        'properties_count': 2430,
        'average_rating': 8.5,
    },
    'melbourne': {
        'display': 'Melbourne',
        'slug': 'melbourne',
        'country': 'Australia',
        'country_code': 'au',
        'description': 'Australia\'s cultural capital. Laneway cafes, street art, world-class sport and dining.',
        'lat': -37.8136,
        'lng': 144.9631,
        'properties_count': 2100,
        'average_rating': 8.4,
    },
    'toronto': {
        'display': 'Toronto',
        'slug': 'toronto',
        'country': 'Canada',
        'country_code': 'ca',
        'description': 'Canada\'s largest city. CN Tower, diverse neighbourhoods, downtown waterfront, and multicultural food.',
        'lat': 43.6532,
        'lng': -79.3832,
        'properties_count': 2560,
        'average_rating': 8.3,
    },
    'shenzhen': {
        'display': 'Shenzhen',
        'slug': 'shenzhen',
        'country': 'China',
        'country_code': 'cn',
        'description': 'China\'s Silicon Valley. Futuristic skyline, tech innovation, and vibrant nightlife.',
        'lat': 22.5431,
        'lng': 114.0579,
        'properties_count': 3200,
        'average_rating': 8.2,
    },
    'sapporo': {
        'display': 'Sapporo',
        'slug': 'sapporo',
        'country': 'Japan',
        'country_code': 'jp',
        'description': 'Gateway to Hokkaido. Famous for ramen, beer, ski resorts, and the annual snow festival.',
        'lat': 43.0618,
        'lng': 141.3545,
        'properties_count': 1540,
        'average_rating': 8.7,
    },
}


# Hotel inventory - properties with real data from scraping
# Extra manual entries fill in cities where scraping was thin
EXTRA_HOTELS = [
    # NYC
    {'name': 'The Plaza New York', 'type': 'Hotel', 'neighborhood': 'Midtown Manhattan', 'city_key': 'nyc', 'stars': 5},
    {'name': 'Standard High Line', 'type': 'Hotel', 'neighborhood': 'Meatpacking District', 'city_key': 'nyc', 'stars': 4},
    # Paris
    {'name': 'Le Bristol Paris', 'type': 'Hotel', 'neighborhood': '8th arr.', 'city_key': 'paris', 'stars': 5},
    {'name': 'Hôtel de Crillon', 'type': 'Hotel', 'neighborhood': '8th arr.', 'city_key': 'paris', 'stars': 5},
    {'name': 'Hotel Fabric', 'type': 'Hotel', 'neighborhood': '11th arr.', 'city_key': 'paris', 'stars': 4},
    {'name': 'Le Marais Suites', 'type': 'Apartment', 'neighborhood': 'Le Marais', 'city_key': 'paris', 'stars': 4},
    # London
    {'name': 'The Savoy', 'type': 'Hotel', 'neighborhood': 'Covent Garden', 'city_key': 'london', 'stars': 5},
    {'name': 'Claridge\'s', 'type': 'Hotel', 'neighborhood': 'Mayfair', 'city_key': 'london', 'stars': 5},
    # Tokyo
    {'name': 'Park Hyatt Tokyo', 'type': 'Hotel', 'neighborhood': 'Shinjuku', 'city_key': 'tokyo', 'stars': 5},
    {'name': 'Aman Tokyo', 'type': 'Hotel', 'neighborhood': 'Otemachi', 'city_key': 'tokyo', 'stars': 5},
    # Rome
    {'name': 'Hotel de Russie', 'type': 'Hotel', 'neighborhood': 'Piazza del Popolo', 'city_key': 'rome', 'stars': 5},
    {'name': 'Hotel Eden', 'type': 'Hotel', 'neighborhood': 'Via Veneto', 'city_key': 'rome', 'stars': 5},
    {'name': 'Casa Trastevere', 'type': 'Apartment', 'neighborhood': 'Trastevere', 'city_key': 'rome', 'stars': 4},
    {'name': 'Domus Aventina', 'type': 'Bed and Breakfast', 'neighborhood': 'Aventine Hill', 'city_key': 'rome', 'stars': 3},
    # Maldives
    {'name': 'Soneva Jani', 'type': 'Resort', 'neighborhood': 'Noonu Atoll', 'city_key': 'maldives', 'stars': 5},
    {'name': 'Conrad Maldives Rangali Island', 'type': 'Resort', 'neighborhood': 'South Ari Atoll', 'city_key': 'maldives', 'stars': 5},
    {'name': 'Anantara Kihavah Villas', 'type': 'Villa', 'neighborhood': 'Baa Atoll', 'city_key': 'maldives', 'stars': 5},
    {'name': 'Velaa Private Island', 'type': 'Resort', 'neighborhood': 'Noonu Atoll', 'city_key': 'maldives', 'stars': 5},
    {'name': 'Four Seasons Maldives at Kuda Huraa', 'type': 'Resort', 'neighborhood': 'North Male Atoll', 'city_key': 'maldives', 'stars': 5},
    # Singapore
    {'name': 'Marina Bay Sands', 'type': 'Hotel', 'neighborhood': 'Marina Bay', 'city_key': 'singapore', 'stars': 5},
    {'name': 'Raffles Singapore', 'type': 'Hotel', 'neighborhood': 'Civic District', 'city_key': 'singapore', 'stars': 5},
    {'name': 'The Fullerton Hotel Singapore', 'type': 'Hotel', 'neighborhood': 'Downtown Core', 'city_key': 'singapore', 'stars': 5},
    {'name': 'Hotel G Singapore', 'type': 'Hotel', 'neighborhood': 'Bugis', 'city_key': 'singapore', 'stars': 4},
    # Bali (extras - only 2 scraped)
    {'name': 'Four Seasons Sayan', 'type': 'Resort', 'neighborhood': 'Ubud', 'city_key': 'bali', 'stars': 5},
    {'name': 'The Mulia Nusa Dua', 'type': 'Resort', 'neighborhood': 'Nusa Dua', 'city_key': 'bali', 'stars': 5},
    {'name': 'COMO Uma Ubud', 'type': 'Resort', 'neighborhood': 'Ubud', 'city_key': 'bali', 'stars': 5},
    {'name': 'Alila Seminyak', 'type': 'Hotel', 'neighborhood': 'Seminyak', 'city_key': 'bali', 'stars': 5},
    {'name': 'The Udaya Resort Ubud', 'type': 'Resort', 'neighborhood': 'Ubud', 'city_key': 'bali', 'stars': 5},
    # Dubai
    {'name': 'Burj Al Arab Jumeirah', 'type': 'Hotel', 'neighborhood': 'Jumeirah', 'city_key': 'dubai', 'stars': 5},
    {'name': 'Atlantis The Palm', 'type': 'Resort', 'neighborhood': 'Palm Jumeirah', 'city_key': 'dubai', 'stars': 5},
    # Barcelona
    {'name': 'Hotel Arts Barcelona', 'type': 'Hotel', 'neighborhood': 'Port Olimpic', 'city_key': 'barcelona', 'stars': 5},
    {'name': 'W Barcelona', 'type': 'Hotel', 'neighborhood': 'Barceloneta', 'city_key': 'barcelona', 'stars': 5},
    # Amsterdam
    {'name': 'Waldorf Astoria Amsterdam', 'type': 'Hotel', 'neighborhood': 'Canal Ring', 'city_key': 'amsterdam', 'stars': 5},
    {'name': 'The Dylan Amsterdam', 'type': 'Hotel', 'neighborhood': 'Canal Ring', 'city_key': 'amsterdam', 'stars': 5},
    # Jakarta
    {'name': 'The Ritz-Carlton Jakarta', 'type': 'Hotel', 'neighborhood': 'Mega Kuningan', 'city_key': 'jakarta', 'stars': 5},
    {'name': 'Mandarin Oriental Jakarta', 'type': 'Hotel', 'neighborhood': 'Thamrin', 'city_key': 'jakarta', 'stars': 5},
    {'name': 'Hotel Indonesia Kempinski', 'type': 'Hotel', 'neighborhood': 'Bundaran HI', 'city_key': 'jakarta', 'stars': 5},
    {'name': 'Gran Melia Jakarta', 'type': 'Hotel', 'neighborhood': 'Kuningan', 'city_key': 'jakarta', 'stars': 5},
    {'name': 'Artotel Thamrin Jakarta', 'type': 'Hotel', 'neighborhood': 'Thamrin', 'city_key': 'jakarta', 'stars': 3},
    {'name': 'RedDoorz Plus Menteng', 'type': 'Hotel', 'neighborhood': 'Menteng', 'city_key': 'jakarta', 'stars': 2},
    # Ohio
    {'name': 'The Ritz-Carlton Cleveland', 'type': 'Hotel', 'neighborhood': 'Downtown Cleveland', 'city_key': 'ohio', 'stars': 5},
    {'name': 'Hilton Columbus Downtown', 'type': 'Hotel', 'neighborhood': 'Downtown Columbus', 'city_key': 'ohio', 'stars': 4},
    {'name': 'Hotel Brexton Cincinnati', 'type': 'Hotel', 'neighborhood': 'Over-the-Rhine', 'city_key': 'ohio', 'stars': 4},
    {'name': 'Comfort Inn Ohio', 'type': 'Hotel', 'neighborhood': 'Columbus', 'city_key': 'ohio', 'stars': 3},
    {'name': 'Holiday Inn Express Dayton', 'type': 'Hotel', 'neighborhood': 'Dayton', 'city_key': 'ohio', 'stars': 3},
    # Varanasi (near Kashi Vishwanath)
    {'name': 'BrijRama Palace', 'type': 'Hotel', 'neighborhood': 'Darbhanga Ghat', 'city_key': 'varanasi', 'stars': 5},
    {'name': 'Taj Nadesar Palace', 'type': 'Hotel', 'neighborhood': 'Nadesar', 'city_key': 'varanasi', 'stars': 5},
    {'name': 'Ramada Plaza Varanasi', 'type': 'Hotel', 'neighborhood': 'The Mall Road', 'city_key': 'varanasi', 'stars': 4},
    {'name': 'Hotel Surya Varanasi', 'type': 'Hotel', 'neighborhood': 'Cantonment', 'city_key': 'varanasi', 'stars': 3},
    {'name': 'Kashi Vishwanath Guest House', 'type': 'Guest House', 'neighborhood': 'Kashi Vishwanath', 'city_key': 'varanasi', 'stars': 2},
    # Chennai
    {'name': 'ITC Grand Chola Chennai', 'type': 'Hotel', 'neighborhood': 'Guindy', 'city_key': 'chennai', 'stars': 5},
    {'name': 'Taj Coromandel Chennai', 'type': 'Hotel', 'neighborhood': 'Nungambakkam', 'city_key': 'chennai', 'stars': 5},
    {'name': 'Park Hyatt Chennai', 'type': 'Hotel', 'neighborhood': 'Velachery', 'city_key': 'chennai', 'stars': 5},
    {'name': 'The Raintree Hotel Chennai', 'type': 'Hotel', 'neighborhood': 'Anna Salai', 'city_key': 'chennai', 'stars': 4},
    {'name': 'Hotel Savera Chennai', 'type': 'Hotel', 'neighborhood': 'Mylapore', 'city_key': 'chennai', 'stars': 3},
    # Chicago (downtown)
    {'name': 'The Peninsula Chicago', 'type': 'Hotel', 'neighborhood': 'Downtown Chicago', 'city_key': 'chicago', 'stars': 5},
    {'name': 'Four Seasons Hotel Chicago', 'type': 'Hotel', 'neighborhood': 'Downtown Chicago', 'city_key': 'chicago', 'stars': 5},
    {'name': 'The Langham Chicago', 'type': 'Hotel', 'neighborhood': 'Downtown Chicago', 'city_key': 'chicago', 'stars': 5},
    {'name': 'Hyatt Regency Chicago', 'type': 'Hotel', 'neighborhood': 'Downtown Chicago', 'city_key': 'chicago', 'stars': 4},
    {'name': 'Palmer House Hilton', 'type': 'Hotel', 'neighborhood': 'Downtown Chicago', 'city_key': 'chicago', 'stars': 4},
    # Lisbon
    {'name': 'Four Seasons Hotel Ritz Lisbon', 'type': 'Hotel', 'neighborhood': 'Marques de Pombal', 'city_key': 'lisbon', 'stars': 5},
    {'name': 'Bairro Alto Hotel Lisbon', 'type': 'Hotel', 'neighborhood': 'Bairro Alto', 'city_key': 'lisbon', 'stars': 5},
    {'name': 'Pestana Palace Lisbon', 'type': 'Hotel', 'neighborhood': 'Alcantara', 'city_key': 'lisbon', 'stars': 5},
    {'name': 'Hotel Avenida Palace Lisbon', 'type': 'Hotel', 'neighborhood': 'Avenida da Liberdade', 'city_key': 'lisbon', 'stars': 4},
    {'name': 'Casa das Janelas Lisbon', 'type': 'Bed and Breakfast', 'neighborhood': 'Bairro Alto', 'city_key': 'lisbon', 'stars': 3},
    # Melbourne
    {'name': 'The Langham Melbourne', 'type': 'Hotel', 'neighborhood': 'Southbank', 'city_key': 'melbourne', 'stars': 5},
    {'name': 'Park Hyatt Melbourne', 'type': 'Hotel', 'neighborhood': 'East Melbourne', 'city_key': 'melbourne', 'stars': 5},
    {'name': 'Crown Towers Melbourne', 'type': 'Hotel', 'neighborhood': 'Southbank', 'city_key': 'melbourne', 'stars': 5},
    {'name': 'QT Melbourne', 'type': 'Hotel', 'neighborhood': 'CBD', 'city_key': 'melbourne', 'stars': 4},
    {'name': 'Novotel Melbourne', 'type': 'Hotel', 'neighborhood': 'CBD', 'city_key': 'melbourne', 'stars': 4},
    # Toronto (downtown)
    {'name': 'Shangri-La Hotel Toronto', 'type': 'Hotel', 'neighborhood': 'Downtown Toronto', 'city_key': 'toronto', 'stars': 5},
    {'name': 'Four Seasons Hotel Toronto', 'type': 'Hotel', 'neighborhood': 'Yorkville', 'city_key': 'toronto', 'stars': 5},
    {'name': 'Fairmont Royal York Toronto', 'type': 'Hotel', 'neighborhood': 'Downtown Toronto', 'city_key': 'toronto', 'stars': 5},
    {'name': 'The Ritz-Carlton Toronto', 'type': 'Hotel', 'neighborhood': 'Downtown Toronto', 'city_key': 'toronto', 'stars': 5},
    {'name': 'Chelsea Hotel Toronto', 'type': 'Hotel', 'neighborhood': 'Downtown Toronto', 'city_key': 'toronto', 'stars': 3},
    # Shenzhen
    {'name': 'The St. Regis Shenzhen', 'type': 'Hotel', 'neighborhood': 'Luohu', 'city_key': 'shenzhen', 'stars': 5},
    {'name': 'Four Seasons Shenzhen', 'type': 'Hotel', 'neighborhood': 'Futian', 'city_key': 'shenzhen', 'stars': 5},
    {'name': 'Grand Hyatt Shenzhen', 'type': 'Hotel', 'neighborhood': 'Luohu', 'city_key': 'shenzhen', 'stars': 5},
    {'name': 'Hilton Shenzhen Shekou', 'type': 'Hotel', 'neighborhood': 'Shekou', 'city_key': 'shenzhen', 'stars': 4},
    {'name': 'CitiGO Shenzhen', 'type': 'Hotel', 'neighborhood': 'Nanshan', 'city_key': 'shenzhen', 'stars': 3},
    # Sapporo (Hokkaido)
    {'name': 'JR Tower Hotel Nikko Sapporo', 'type': 'Hotel', 'neighborhood': 'Sapporo Station', 'city_key': 'sapporo', 'stars': 5},
    {'name': 'Cross Hotel Sapporo', 'type': 'Hotel', 'neighborhood': 'Odori', 'city_key': 'sapporo', 'stars': 4},
    {'name': 'Keio Plaza Hotel Sapporo', 'type': 'Hotel', 'neighborhood': 'Kita 5-jo', 'city_key': 'sapporo', 'stars': 4},
    {'name': 'Sapporo Grand Hotel', 'type': 'Hotel', 'neighborhood': 'Chuo-ku', 'city_key': 'sapporo', 'stars': 4},
    {'name': 'Dormy Inn Premium Sapporo', 'type': 'Hotel', 'neighborhood': 'Susukino', 'city_key': 'sapporo', 'stars': 3},
    # Extra Mexico City
    {'name': 'Polanco Boutique Hotel', 'type': 'Hotel', 'neighborhood': 'Polanco', 'city_key': 'mexicocity', 'stars': 4},
    {'name': 'Four Seasons Mexico City', 'type': 'Hotel', 'neighborhood': 'Reforma', 'city_key': 'mexicocity', 'stars': 5},
    {'name': 'St. Regis Mexico City', 'type': 'Hotel', 'neighborhood': 'Reforma', 'city_key': 'mexicocity', 'stars': 5},
    {'name': 'Condesa DF Mexico City', 'type': 'Hotel', 'neighborhood': 'Condesa', 'city_key': 'mexicocity', 'stars': 4},
    {'name': 'Hotel Carlota CDMX', 'type': 'Hotel', 'neighborhood': 'Juarez', 'city_key': 'mexicocity', 'stars': 3},
    # Extra Rome (budget options < $100)
    {'name': 'Hostel Roma Termini', 'type': 'Hostel', 'neighborhood': 'Termini', 'city_key': 'rome', 'stars': 1},
    {'name': 'Hotel Dina Rome', 'type': 'Hotel', 'neighborhood': 'Esquilino', 'city_key': 'rome', 'stars': 2},
    {'name': 'Hotel Grifo Rome', 'type': 'Hotel', 'neighborhood': 'Monti', 'city_key': 'rome', 'stars': 3},
    {'name': 'Pensione Roma Centro', 'type': 'Bed and Breakfast', 'neighborhood': 'Centro Storico', 'city_key': 'rome', 'stars': 2},
    # Extra Los Angeles (more for shuttle/breakfast combos)
    {'name': 'Hilton LAX', 'type': 'Hotel', 'neighborhood': 'LAX Area', 'city_key': 'losangeles', 'stars': 4},
    {'name': 'Marriott LAX Airport', 'type': 'Hotel', 'neighborhood': 'LAX Area', 'city_key': 'losangeles', 'stars': 4},
    # Extra Paris (more for Louvre / pool combos)
    {'name': 'Hotel Le Louvre Paris', 'type': 'Hotel', 'neighborhood': 'Louvre - Tuileries', 'city_key': 'paris', 'stars': 4},
    {'name': 'Melia Paris Louvre', 'type': 'Hotel', 'neighborhood': 'Louvre', 'city_key': 'paris', 'stars': 4},
    {'name': 'Hotel Nolinski Paris', 'type': 'Hotel', 'neighborhood': 'Louvre', 'city_key': 'paris', 'stars': 5},
    # Extra Singapore (near NUS)
    {'name': 'Capella Singapore', 'type': 'Resort', 'neighborhood': 'National University of Singapore', 'city_key': 'singapore', 'stars': 5},
    {'name': 'Park Avenue Rochester Singapore', 'type': 'Hotel', 'neighborhood': 'National University of Singapore', 'city_key': 'singapore', 'stars': 4},
    {'name': 'Faber Peak Hotel Singapore', 'type': 'Hotel', 'neighborhood': 'National University of Singapore', 'city_key': 'singapore', 'stars': 3},
]


# Featured destinations for homepage
TRENDING_DESTINATIONS = ['nyc', 'paris', 'london', 'tokyo', 'dubai', 'maldives', 'bali', 'singapore']

# Popular country trips
POPULAR_REGIONS = [
    {'name': 'Europe', 'countries': 12, 'properties': 87654},
    {'name': 'Asia', 'countries': 18, 'properties': 54321},
    {'name': 'North America', 'countries': 3, 'properties': 34567},
    {'name': 'Africa', 'countries': 24, 'properties': 23456},
    {'name': 'South America', 'countries': 12, 'properties': 19876},
    {'name': 'Oceania', 'countries': 14, 'properties': 12345},
]

# Offers / deals
OFFERS = [
    {
        'title': 'Getaway Deals',
        'subtitle': 'Promotions, deals, and special offers for you',
        'description': 'Save up to 15% on selected stays with our Getaway Deals. Hurry — offers end soon!',
        'cta': 'Find Deals',
        'badge': '-15%',
    },
    {
        'title': 'Genius Loyalty Programme',
        'subtitle': 'Save 10% or more at participating properties',
        'description': 'Sign in to unlock Genius benefits including discounts, free breakfasts, and room upgrades.',
        'cta': 'Sign in',
        'badge': 'GENIUS',
    },
    {
        'title': 'Seasonal Deals',
        'subtitle': 'Save on your dream holiday',
        'description': 'Book a seasonal stay at participating properties for extra savings.',
        'cta': 'Find Deals',
        'badge': '-25%',
    },
    {
        'title': 'Late Escape Deals',
        'subtitle': 'Save up to 15% with Late Escape Deals',
        'description': 'Last-minute trips with extra savings at participating properties worldwide.',
        'cta': 'Find Late Deals',
        'badge': 'LATE',
    },
]

# Amenity options
AMENITIES = [
    'Free WiFi', 'Swimming pool', 'Free parking', 'Spa & wellness', 'Fitness center',
    'Restaurant', 'Room service', 'Airport shuttle', 'Bar', 'Breakfast included',
    'Pet-friendly', 'Air conditioning', 'Family rooms', '24-hour front desk',
    'Non-smoking rooms', 'Beachfront', 'Sea view', 'Kitchen', 'Washing machine',
    'Balcony', 'Garden view', 'BBQ facilities', 'Tea/coffee maker', 'Hair dryer',
]


def build_hotel_description(name, city_name, stars, prop_type, amenities):
    """Generate a faithful booking-style description."""
    d = f"{name} is a "
    if stars == 5:
        d += "stunning luxury "
    elif stars == 4:
        d += "well-appointed "
    elif stars == 3:
        d += "comfortable "
    else:
        d += "cosy "
    d += f"{prop_type.lower()} in the heart of {city_name}. "
    d += f"With elegant decor, attentive service, and {', '.join(amenities[:3]).lower()}, "
    d += f"guests enjoy a refined travel experience. "
    d += f"The property offers rooms featuring modern amenities, high-speed WiFi, and comfortable bedding. "
    d += f"Located in a prime area, {name} is the perfect base for exploring everything {city_name} has to offer."
    return d
