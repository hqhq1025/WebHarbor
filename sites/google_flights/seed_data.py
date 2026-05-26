"""
Seed data for Google Flights mirror.
Loads airports + generates a large catalog of flights between them.
"""
import json
import random
import os
from datetime import date, timedelta, datetime
from pathlib import Path
from sqlalchemy import text, inspect as _sa_inspect

BASE_DIR = Path(__file__).parent

# Pinned reference timestamp used for every created_at / cancelled_at / updated_at
# field that the seed path writes. Required so a rebuild on machine B at a
# different wall-clock time yields the same byte sequence as the shipped seed DB.
# See ~/repos/WebHarbor/.claude/skills/harden-env/gotchas.md #3.
MIRROR_REFERENCE_DATE = datetime(2026, 5, 12, 12, 0, 0)

# Pinned bcrypt hash for the canonical benchmark password 'TestPass123!'.
# bcrypt.generate_password_hash() mixes a fresh salt every call, which breaks
# byte-identical rebuild (gotcha #1). seed_benchmark_users() reuses this string
# verbatim instead of calling set_password / generate_password_hash.
PINNED_PASSWORD_HASH = '$2b$12$RwAC/sfwDHtccU//A20fde.uKkZK4Ptnjjyua2l2ktwI6uysAp3Ou'


def normalize_seed_db_layout(db):
    """Re-emit indexes in alpha order + VACUUM so rebuilds match byte-for-byte.
    SQLAlchemy emits CREATE INDEX from `Table.indexes`, a Python set whose iteration
    order depends on object id() — so the schema text inside sqlite_schema shifts
    every rebuild even when row data is identical. Drop + reinsert in sorted name
    order + VACUUM so the SQLite page bytes are stable across processes.

    Also freezes all rebuild-volatile timestamp columns to MIRROR_REFERENCE_DATE.
    Every `Column(DateTime, default=datetime.utcnow)` fires at row insert and would
    otherwise capture wall-clock time per build (gotcha #3). We sweep the affected
    columns to MIRROR_REFERENCE_DATE after seed, except booking.booked_at /
    booking.cancelled_at which are pinned with deliberate offsets (so the Trips
    listing sorts sensibly).
    """
    conn = db.engine.connect()

    # 1. Freeze volatile timestamps. Skip the booking table — those columns are
    # already set with deliberate per-row offsets in app.py:_make_booking.
    pinned = MIRROR_REFERENCE_DATE.isoformat(sep=' ')
    freeze_targets = [
        ('user', 'created_at'),
        ('flight', 'created_at'),
        ('cart_item', 'added_at'),
        ('booking_item', None),  # no timestamp column
        ('tracked_flight', 'added_at'),
        ('review', 'created_at'),
        ('price_alert', 'created_at'),
        ('saved_search', 'created_at'),
        ('payment_methods', 'created_at'),
    ]
    for table, col in freeze_targets:
        if not col:
            continue
        try:
            conn.execute(text(f"UPDATE {table} SET {col} = :ts"), {'ts': pinned})
        except Exception:
            # Column may not exist on every table (forward-compat).
            pass
    conn.commit()

    # 2. Normalize CREATE INDEX order.
    idx_rows = conn.execute(text(
        "SELECT name, sql FROM sqlite_master WHERE type='index' AND name LIKE 'ix_%'"
    )).fetchall()
    for name, _ in idx_rows:
        conn.execute(text(f"DROP INDEX IF EXISTS {name}"))
    for name, sql in sorted(idx_rows, key=lambda r: r[0]):
        if sql:
            conn.execute(text(sql))
    conn.execute(text("VACUUM"))
    conn.commit()


# (iata, city_slug, city, country, airport_name, region, is_popular)
AIRPORTS = [
    # North America - US
    ('JFK', 'new-york', 'New York', 'United States', 'John F. Kennedy International', 'North America', True),
    ('LGA', 'new-york', 'New York', 'United States', 'LaGuardia', 'North America', True),
    ('EWR', 'new-york', 'New York', 'United States', 'Newark Liberty International', 'North America', True),
    ('LAX', 'los-angeles', 'Los Angeles', 'United States', 'Los Angeles International', 'North America', True),
    ('ORD', 'chicago', 'Chicago', 'United States', "O'Hare International", 'North America', True),
    ('SFO', 'san-francisco', 'San Francisco', 'United States', 'San Francisco International', 'North America', True),
    ('MIA', 'miami', 'Miami', 'United States', 'Miami International', 'North America', True),
    ('LAS', 'las-vegas', 'Las Vegas', 'United States', 'Harry Reid International', 'North America', True),
    ('SEA', 'seattle', 'Seattle', 'United States', 'Seattle-Tacoma International', 'North America', True),
    ('BOS', 'boston', 'Boston', 'United States', 'Logan International', 'North America', True),
    ('ATL', 'atlanta', 'Atlanta', 'United States', 'Hartsfield-Jackson International', 'North America', True),
    ('DFW', 'dallas', 'Dallas', 'United States', 'Dallas/Fort Worth International', 'North America', True),
    ('DEN', 'denver', 'Denver', 'United States', 'Denver International', 'North America', True),
    ('HNL', 'honolulu', 'Honolulu', 'United States', 'Daniel K. Inouye International', 'North America', True),
    # Europe
    ('LHR', 'london', 'London', 'United Kingdom', 'Heathrow', 'Europe', True),
    ('LGW', 'london', 'London', 'United Kingdom', 'Gatwick', 'Europe', True),
    ('CDG', 'paris', 'Paris', 'France', 'Charles de Gaulle', 'Europe', True),
    ('FCO', 'rome', 'Rome', 'Italy', 'Leonardo da Vinci-Fiumicino', 'Europe', True),
    ('BCN', 'barcelona', 'Barcelona', 'Spain', 'El Prat', 'Europe', True),
    ('MAD', 'madrid', 'Madrid', 'Spain', 'Adolfo Suarez Madrid-Barajas', 'Europe', True),
    ('AMS', 'amsterdam', 'Amsterdam', 'Netherlands', 'Schiphol', 'Europe', True),
    ('BER', 'berlin', 'Berlin', 'Germany', 'Brandenburg', 'Europe', True),
    ('MUC', 'munich', 'Munich', 'Germany', 'Franz Josef Strauss', 'Europe', True),
    ('VIE', 'vienna', 'Vienna', 'Austria', 'Vienna International', 'Europe', True),
    ('PRG', 'prague', 'Prague', 'Czech Republic', 'Vaclav Havel', 'Europe', True),
    ('ZRH', 'zurich', 'Zurich', 'Switzerland', 'Zurich', 'Europe', True),
    ('CPH', 'copenhagen', 'Copenhagen', 'Denmark', 'Kastrup', 'Europe', True),
    ('ARN', 'stockholm', 'Stockholm', 'Sweden', 'Arlanda', 'Europe', True),
    ('OSL', 'oslo', 'Oslo', 'Norway', 'Gardermoen', 'Europe', True),
    ('DUB', 'dublin', 'Dublin', 'Ireland', 'Dublin', 'Europe', True),
    ('LIS', 'lisbon', 'Lisbon', 'Portugal', 'Humberto Delgado', 'Europe', True),
    ('ATH', 'athens', 'Athens', 'Greece', 'Eleftherios Venizelos', 'Europe', True),
    ('IST', 'istanbul', 'Istanbul', 'Turkey', 'Istanbul Airport', 'Europe', True),
    ('KEF', 'reykjavik', 'Reykjavik', 'Iceland', 'Keflavik', 'Europe', True),
    ('VCE', 'venice', 'Venice', 'Italy', 'Marco Polo', 'Europe', True),
    ('FLR', 'florence', 'Florence', 'Italy', 'Peretola', 'Europe', False),
    ('MXP', 'milan', 'Milan', 'Italy', 'Malpensa', 'Europe', True),
    ('EDI', 'edinburgh', 'Edinburgh', 'United Kingdom', 'Edinburgh', 'Europe', False),
    ('BRU', 'brussels', 'Brussels', 'Belgium', 'Brussels Airport', 'Europe', False),
    ('BUD', 'budapest', 'Budapest', 'Hungary', 'Ferenc Liszt International', 'Europe', False),
    ('WAW', 'warsaw', 'Warsaw', 'Poland', 'Chopin', 'Europe', False),
    ('HEL', 'helsinki', 'Helsinki', 'Finland', 'Vantaa', 'Europe', False),
    # Asia
    ('HND', 'tokyo', 'Tokyo', 'Japan', 'Haneda', 'Asia', True),
    ('NRT', 'tokyo', 'Tokyo', 'Japan', 'Narita International', 'Asia', True),
    ('KIX', 'osaka', 'Osaka', 'Japan', 'Kansai International', 'Asia', True),
    ('ITM', 'kyoto', 'Kyoto', 'Japan', 'Osaka International (Itami)', 'Asia', False),
    ('ICN', 'seoul', 'Seoul', 'South Korea', 'Incheon International', 'Asia', True),
    ('PEK', 'beijing', 'Beijing', 'China', 'Beijing Capital International', 'Asia', True),
    ('PVG', 'shanghai', 'Shanghai', 'China', 'Pudong International', 'Asia', True),
    ('HKG', 'hong-kong', 'Hong Kong', 'Hong Kong', 'Hong Kong International', 'Asia', True),
    ('TPE', 'taipei', 'Taipei', 'Taiwan', 'Taoyuan International', 'Asia', True),
    ('BKK', 'bangkok', 'Bangkok', 'Thailand', 'Suvarnabhumi', 'Asia', True),
    ('SIN', 'singapore', 'Singapore', 'Singapore', 'Changi', 'Asia', True),
    ('KUL', 'kuala-lumpur', 'Kuala Lumpur', 'Malaysia', 'Kuala Lumpur International', 'Asia', True),
    ('CGK', 'jakarta', 'Jakarta', 'Indonesia', 'Soekarno-Hatta International', 'Asia', False),
    ('DPS', 'bali', 'Bali', 'Indonesia', 'Ngurah Rai International', 'Asia', True),
    ('MNL', 'manila', 'Manila', 'Philippines', 'Ninoy Aquino International', 'Asia', False),
    ('HAN', 'hanoi', 'Hanoi', 'Vietnam', 'Noi Bai International', 'Asia', False),
    ('BOM', 'mumbai', 'Mumbai', 'India', 'Chhatrapati Shivaji International', 'Asia', True),
    ('DEL', 'delhi', 'Delhi', 'India', 'Indira Gandhi International', 'Asia', True),
    # Middle East
    ('DXB', 'dubai', 'Dubai', 'UAE', 'Dubai International', 'Middle East', True),
    ('AUH', 'abu-dhabi', 'Abu Dhabi', 'UAE', 'Abu Dhabi International', 'Middle East', True),
    ('DOH', 'doha', 'Doha', 'Qatar', 'Hamad International', 'Middle East', True),
    ('TLV', 'tel-aviv', 'Tel Aviv', 'Israel', 'Ben Gurion', 'Middle East', True),
    # Africa
    ('CAI', 'cairo', 'Cairo', 'Egypt', 'Cairo International', 'Africa', True),
    ('RAK', 'marrakech', 'Marrakech', 'Morocco', 'Menara', 'Africa', True),
    ('CPT', 'cape-town', 'Cape Town', 'South Africa', 'Cape Town International', 'Africa', True),
    ('NBO', 'nairobi', 'Nairobi', 'Kenya', 'Jomo Kenyatta International', 'Africa', False),
    # Oceania
    ('SYD', 'sydney', 'Sydney', 'Australia', 'Kingsford Smith', 'Oceania', True),
    ('MEL', 'melbourne', 'Melbourne', 'Australia', 'Tullamarine', 'Oceania', True),
    ('AKL', 'auckland', 'Auckland', 'New Zealand', 'Auckland', 'Oceania', True),
    # Canada
    ('YYZ', 'toronto', 'Toronto', 'Canada', 'Pearson International', 'North America', True),
    ('YVR', 'vancouver', 'Vancouver', 'Canada', 'Vancouver International', 'North America', True),
    ('YUL', 'montreal', 'Montreal', 'Canada', 'Pierre Elliott Trudeau International', 'North America', True),
    # Latin America
    ('MEX', 'mexico-city', 'Mexico City', 'Mexico', 'Benito Juarez International', 'Latin America', True),
    ('CUN', 'cancun', 'Cancun', 'Mexico', 'Cancun International', 'Latin America', True),
    ('GIG', 'rio-de-janeiro', 'Rio de Janeiro', 'Brazil', 'Galeao International', 'Latin America', True),
    ('GRU', 'sao-paulo', 'Sao Paulo', 'Brazil', 'Guarulhos International', 'Latin America', True),
    ('EZE', 'buenos-aires', 'Buenos Aires', 'Argentina', 'Ezeiza International', 'Latin America', True),
    ('LIM', 'lima', 'Lima', 'Peru', 'Jorge Chavez International', 'Latin America', True),
    ('SCL', 'santiago', 'Santiago', 'Chile', 'Arturo Merino Benitez International', 'Latin America', True),
    ('HAV', 'havana', 'Havana', 'Cuba', 'Jose Marti International', 'Latin America', False),
    ('SJU', 'san-juan', 'San Juan', 'Puerto Rico', 'Luis Munoz Marin International', 'Latin America', False),
    ('PUJ', 'punta-cana', 'Punta Cana', 'Dominican Republic', 'Punta Cana International', 'Latin America', True),
    ('NAS', 'nassau', 'Nassau', 'Bahamas', 'Lynden Pindling International', 'Latin America', False),
    # Additional airports needed by run_tasks
    ('YYC', 'calgary', 'Calgary', 'Canada', 'Calgary International', 'North America', True),
    ('PNQ', 'pune', 'Pune', 'India', 'Pune Airport', 'Asia', False),
    ('PHX', 'phoenix', 'Phoenix', 'United States', 'Phoenix Sky Harbor International', 'North America', True),
    ('MAN', 'manchester', 'Manchester', 'United Kingdom', 'Manchester Airport', 'Europe', True),
    ('FRA', 'frankfurt', 'Frankfurt', 'Germany', 'Frankfurt Airport', 'Europe', True),
    ('JNB', 'johannesburg', 'Johannesburg', 'South Africa', 'O.R. Tambo International', 'Africa', True),
    ('FCA', 'kalispell', 'Kalispell', 'United States', 'Glacier Park International', 'North America', False),
    ('CTS', 'sapporo', 'Sapporo', 'Japan', 'New Chitose Airport', 'Asia', True),
    # --------------------------------------------------------------
    # Phase 2 expansion: extend catalogue to 150+ airports for broader
    # benchmark coverage. New entries appended at the end so existing
    # auto-increment airport.id values stay stable (flight catalogue
    # references airport rows via Airport.query lookup by IATA, so new
    # entries do not invalidate any existing flight row).
    # --------------------------------------------------------------
    # US — secondary hubs and large regional airports
    ('IAH', 'houston', 'Houston', 'United States', 'George Bush Intercontinental', 'North America', True),
    ('HOU', 'houston', 'Houston', 'United States', 'William P. Hobby', 'North America', False),
    ('MCO', 'orlando', 'Orlando', 'United States', 'Orlando International', 'North America', True),
    ('FLL', 'fort-lauderdale', 'Fort Lauderdale', 'United States', 'Fort Lauderdale-Hollywood International', 'North America', False),
    ('TPA', 'tampa', 'Tampa', 'United States', 'Tampa International', 'North America', False),
    ('BWI', 'baltimore', 'Baltimore', 'United States', 'Baltimore/Washington International Thurgood Marshall', 'North America', False),
    ('DCA', 'washington', 'Washington', 'United States', 'Ronald Reagan Washington National', 'North America', True),
    ('IAD', 'washington', 'Washington', 'United States', 'Washington Dulles International', 'North America', True),
    ('PHL', 'philadelphia', 'Philadelphia', 'United States', 'Philadelphia International', 'North America', True),
    ('MSP', 'minneapolis', 'Minneapolis', 'United States', 'Minneapolis-Saint Paul International', 'North America', True),
    ('DTW', 'detroit', 'Detroit', 'United States', 'Detroit Metropolitan Wayne County', 'North America', True),
    ('SLC', 'salt-lake-city', 'Salt Lake City', 'United States', 'Salt Lake City International', 'North America', True),
    ('SAN', 'san-diego', 'San Diego', 'United States', 'San Diego International', 'North America', True),
    ('PDX', 'portland', 'Portland', 'United States', 'Portland International', 'North America', True),
    ('AUS', 'austin', 'Austin', 'United States', 'Austin-Bergstrom International', 'North America', True),
    ('CLT', 'charlotte', 'Charlotte', 'United States', 'Charlotte Douglas International', 'North America', True),
    ('BNA', 'nashville', 'Nashville', 'United States', 'Nashville International', 'North America', True),
    # Europe — secondary cities
    ('GVA', 'geneva', 'Geneva', 'Switzerland', 'Geneva Airport', 'Europe', True),
    ('NCE', 'nice', 'Nice', 'France', 'Cote d Azur', 'Europe', True),
    ('LYS', 'lyon', 'Lyon', 'France', 'Saint Exupery', 'Europe', False),
    ('HAM', 'hamburg', 'Hamburg', 'Germany', 'Hamburg Airport', 'Europe', False),
    ('DUS', 'dusseldorf', 'Dusseldorf', 'Germany', 'Dusseldorf Airport', 'Europe', False),
    ('CGN', 'cologne', 'Cologne', 'Germany', 'Cologne Bonn', 'Europe', False),
    ('NAP', 'naples', 'Naples', 'Italy', 'Naples International', 'Europe', True),
    ('BLQ', 'bologna', 'Bologna', 'Italy', 'Guglielmo Marconi', 'Europe', False),
    ('VRN', 'verona', 'Verona', 'Italy', 'Verona Villafranca', 'Europe', False),
    ('KRK', 'krakow', 'Krakow', 'Poland', 'John Paul II International', 'Europe', False),
    ('OTP', 'bucharest', 'Bucharest', 'Romania', 'Henri Coanda International', 'Europe', False),
    ('SOF', 'sofia', 'Sofia', 'Bulgaria', 'Sofia Airport', 'Europe', False),
    ('RIX', 'riga', 'Riga', 'Latvia', 'Riga International', 'Europe', False),
    ('TLL', 'tallinn', 'Tallinn', 'Estonia', 'Lennart Meri Tallinn', 'Europe', False),
    ('AGP', 'malaga', 'Malaga', 'Spain', 'Malaga-Costa del Sol', 'Europe', True),
    ('PMI', 'palma', 'Palma de Mallorca', 'Spain', 'Palma de Mallorca', 'Europe', False),
    ('OPO', 'porto', 'Porto', 'Portugal', 'Francisco Sa Carneiro', 'Europe', False),
    ('GLA', 'glasgow', 'Glasgow', 'United Kingdom', 'Glasgow International', 'Europe', False),
    # Asia — major secondary hubs
    ('CAN', 'guangzhou', 'Guangzhou', 'China', 'Baiyun International', 'Asia', True),
    ('CTU', 'chengdu', 'Chengdu', 'China', 'Shuangliu International', 'Asia', True),
    ('SHA', 'shanghai', 'Shanghai', 'China', 'Hongqiao International', 'Asia', False),
    ('KHH', 'kaohsiung', 'Kaohsiung', 'Taiwan', 'Kaohsiung International', 'Asia', False),
    ('HKT', 'phuket', 'Phuket', 'Thailand', 'Phuket International', 'Asia', True),
    ('CNX', 'chiang-mai', 'Chiang Mai', 'Thailand', 'Chiang Mai International', 'Asia', False),
    ('KTM', 'kathmandu', 'Kathmandu', 'Nepal', 'Tribhuvan International', 'Asia', False),
    ('BLR', 'bangalore', 'Bangalore', 'India', 'Kempegowda International', 'Asia', True),
    ('MAA', 'chennai', 'Chennai', 'India', 'Chennai International', 'Asia', True),
    ('HYD', 'hyderabad', 'Hyderabad', 'India', 'Rajiv Gandhi International', 'Asia', False),
    ('DAC', 'dhaka', 'Dhaka', 'Bangladesh', 'Hazrat Shahjalal International', 'Asia', False),
    ('CMB', 'colombo', 'Colombo', 'Sri Lanka', 'Bandaranaike International', 'Asia', False),
    ('PUS', 'busan', 'Busan', 'South Korea', 'Gimhae International', 'Asia', False),
    # Middle East
    ('RUH', 'riyadh', 'Riyadh', 'Saudi Arabia', 'King Khalid International', 'Middle East', True),
    ('JED', 'jeddah', 'Jeddah', 'Saudi Arabia', 'King Abdulaziz International', 'Middle East', True),
    ('AMM', 'amman', 'Amman', 'Jordan', 'Queen Alia International', 'Middle East', False),
    ('BEY', 'beirut', 'Beirut', 'Lebanon', 'Rafic Hariri International', 'Middle East', False),
    ('KWI', 'kuwait-city', 'Kuwait City', 'Kuwait', 'Kuwait International', 'Middle East', False),
    # Africa
    ('CMN', 'casablanca', 'Casablanca', 'Morocco', 'Mohammed V International', 'Africa', True),
    ('ADD', 'addis-ababa', 'Addis Ababa', 'Ethiopia', 'Bole International', 'Africa', True),
    ('LOS', 'lagos', 'Lagos', 'Nigeria', 'Murtala Muhammed International', 'Africa', False),
    ('ACC', 'accra', 'Accra', 'Ghana', 'Kotoka International', 'Africa', False),
    # Oceania
    ('BNE', 'brisbane', 'Brisbane', 'Australia', 'Brisbane Airport', 'Oceania', True),
    ('PER', 'perth', 'Perth', 'Australia', 'Perth Airport', 'Oceania', True),
    ('ADL', 'adelaide', 'Adelaide', 'Australia', 'Adelaide Airport', 'Oceania', False),
    ('CHC', 'christchurch', 'Christchurch', 'New Zealand', 'Christchurch International', 'Oceania', False),
    ('NAN', 'nadi', 'Nadi', 'Fiji', 'Nadi International', 'Oceania', False),
    # Latin America
    ('BOG', 'bogota', 'Bogota', 'Colombia', 'El Dorado International', 'Latin America', True),
    ('UIO', 'quito', 'Quito', 'Ecuador', 'Mariscal Sucre International', 'Latin America', False),
    ('PTY', 'panama-city', 'Panama City', 'Panama', 'Tocumen International', 'Latin America', True),
    ('SJO', 'san-jose-cr', 'San Jose', 'Costa Rica', 'Juan Santamaria International', 'Latin America', False),
    ('BSB', 'brasilia', 'Brasilia', 'Brazil', 'Brasilia International', 'Latin America', False),
    ('MDE', 'medellin', 'Medellin', 'Colombia', 'Jose Maria Cordova International', 'Latin America', False),
    ('AEP', 'buenos-aires', 'Buenos Aires', 'Argentina', 'Jorge Newbery (Aeroparque)', 'Latin America', False),
    ('GUA', 'guatemala-city', 'Guatemala City', 'Guatemala', 'La Aurora International', 'Latin America', False),
    # Canada additions
    ('YOW', 'ottawa', 'Ottawa', 'Canada', 'Macdonald-Cartier International', 'North America', False),
    ('YHZ', 'halifax', 'Halifax', 'Canada', 'Stanfield International', 'North America', False),
    ('YEG', 'edmonton', 'Edmonton', 'Canada', 'Edmonton International', 'North America', False),
    # ------------------------------------------------------------------
    # R2 expansion - 199 additional airports sourced from OpenFlights
    # airports.dat (jpatokal/openflights). Appended so existing
    # autoincrement airport.id values stay stable. All flagged
    # is_popular=False so the popular-hub flight catalog stays untouched.
    # Brings the total catalog from 166 to ~365 airports.
    # ------------------------------------------------------------------
    ('ABQ', 'albuquerque', 'Albuquerque', 'United States', 'Albuquerque International Sunport', 'North America', False),
    ('ABV', 'abuja', 'Abuja', 'Nigeria', 'Nnamdi Azikiwe International Airport', 'Africa', False),
    ('AER', 'sochi', 'Sochi', 'Russia', 'Sochi International Airport', 'Europe', False),
    ('AGT', 'ciudad-del-este', 'Ciudad del Este', 'Paraguay', 'Guarani International Airport', 'Latin America', False),
    ('ALA', 'alma-ata', 'Alma-ata', 'Kazakhstan', 'Almaty Airport', 'Asia', False),
    ('ALC', 'alicante', 'Alicante', 'Spain', 'Alicante International Airport', 'Europe', False),
    ('ALG', 'algier', 'Algier', 'Algeria', 'Houari Boumediene Airport', 'Africa', False),
    ('AMD', 'ahmedabad', 'Ahmedabad', 'India', 'Sardar Vallabhbhai Patel International Airport', 'Asia', False),
    ('ANC', 'anchorage', 'Anchorage', 'United States', 'Ted Stevens Anchorage International Airport', 'North America', False),
    ('APW', 'faleolo', 'Faleolo', 'Samoa', 'Faleolo International Airport', 'Oceania', False),
    ('ASU', 'asuncion', 'Asuncion', 'Paraguay', 'Silvio Pettirossi International Airport', 'Latin America', False),
    ('AUA', 'oranjestad', 'Oranjestad', 'Aruba', 'Queen Beatrix International Airport', 'Latin America', False),
    ('BAH', 'bahrain', 'Bahrain', 'Bahrain', 'Bahrain International Airport', 'Middle East', False),
    ('BDA', 'bermuda', 'Bermuda', 'Bermuda', 'L.F. Wade International Airport', 'Latin America', False),
    ('BEG', 'belgrade', 'Belgrade', 'Serbia', 'Belgrade Nikola Tesla Airport', 'Europe', False),
    ('BEL', 'belem', 'Belem', 'Brazil', 'Val de Cans/Julio Cezar Ribeiro International Airport', 'Latin America', False),
    ('BFS', 'belfast', 'Belfast', 'United Kingdom', 'Belfast International Airport', 'Europe', False),
    ('BGI', 'bridgetown', 'Bridgetown', 'Barbados', 'Sir Grantley Adams International Airport', 'Latin America', False),
    ('BGO', 'bergen', 'Bergen', 'Norway', 'Bergen Airport Flesland', 'Europe', False),
    ('BGW', 'baghdad', 'Baghdad', 'Iraq', 'Baghdad International Airport', 'Middle East', False),
    ('BHX', 'birmingham', 'Birmingham', 'United Kingdom', 'Birmingham International Airport', 'Europe', False),
    ('BIO', 'bilbao', 'Bilbao', 'Spain', 'Bilbao Airport', 'Europe', False),
    ('BOD', 'bordeaux', 'Bordeaux', 'France', 'Bordeaux-Merignac Airport', 'Europe', False),
    ('BOI', 'boise', 'Boise', 'United States', 'Boise Air Terminal/Gowen Field', 'North America', False),
    ('BRE', 'bremen', 'Bremen', 'Germany', 'Bremen Airport', 'Europe', False),
    ('BRN', 'bern', 'Bern', 'Switzerland', 'Bern Belp Airport', 'Europe', False),
    ('BRS', 'bristol', 'Bristol', 'United Kingdom', 'Bristol Airport', 'Europe', False),
    ('BSL', 'mulhouse', 'Mulhouse', 'France', 'EuroAirport Basel-Mulhouse-Freiburg Airport', 'Europe', False),
    ('BTS', 'bratislava', 'Bratislava', 'Slovakia', 'M. R. tefanik Airport', 'Europe', False),
    ('BUF', 'buffalo', 'Buffalo', 'United States', 'Buffalo Niagara International Airport', 'North America', False),
    ('BUR', 'burbank', 'Burbank', 'United States', 'Bob Hope Airport', 'North America', False),
    ('CCS', 'caracas', 'Caracas', 'Venezuela', 'Simon Bolivar International Airport', 'Latin America', False),
    ('CCU', 'kolkata', 'Kolkata', 'India', 'Netaji Subhash Chandra Bose International Airport', 'Asia', False),
    ('CHS', 'charleston', 'Charleston', 'United States', 'Charleston Air Force Base-International Airport', 'North America', False),
    ('CIA', 'rome-cia', 'Rome', 'Italy', 'CiampinoG. B. Pastine International Airport', 'Europe', False),
    ('CJU', 'cheju', 'Cheju', 'South Korea', 'Jeju International Airport', 'Asia', False),
    ('CKG', 'chongqing', 'Chongqing', 'China', 'Chongqing Jiangbei International Airport', 'Asia', False),
    ('CLE', 'cleveland', 'Cleveland', 'United States', 'Cleveland Hopkins International Airport', 'North America', False),
    ('CLO', 'cali', 'Cali', 'Colombia', 'Alfonso Bonilla Aragon International Airport', 'Latin America', False),
    ('CMH', 'columbus', 'Columbus', 'United States', 'John Glenn Columbus International Airport', 'North America', False),
    ('CNS', 'cairns', 'Cairns', 'Australia', 'Cairns International Airport', 'Oceania', False),
    ('COK', 'kochi', 'Kochi', 'India', 'Cochin International Airport', 'Asia', False),
    ('CSX', 'changcha', 'Changcha', 'China', 'Changsha Huanghua International Airport', 'Asia', False),
    ('CTA', 'catania', 'Catania', 'Italy', 'Catania-Fontanarossa Airport', 'Europe', False),
    ('CTG', 'cartagena', 'Cartagena', 'Colombia', 'Rafael Nunez International Airport', 'Latin America', False),
    ('CUR', 'willemstad', 'Willemstad', 'Curacao', 'Hato International Airport', 'Latin America', False),
    ('CWB', 'curitiba', 'Curitiba', 'Brazil', 'Afonso Pena Airport', 'Latin America', False),
    ('CWL', 'cardiff', 'Cardiff', 'United Kingdom', 'Cardiff International Airport', 'Europe', False),
    ('DAD', 'danang', 'Danang', 'Vietnam', 'Da Nang International Airport', 'Asia', False),
    ('DAR', 'dar-es-salaam', 'Dar Es Salaam', 'Tanzania', 'Julius Nyerere International Airport', 'Africa', False),
    ('DBV', 'dubrovnik', 'Dubrovnik', 'Croatia', 'Dubrovnik Airport', 'Europe', False),
    ('DKR', 'dakar', 'Dakar', 'Senegal', 'Leopold Sedar Senghor International Airport', 'Africa', False),
    ('DLC', 'dalian', 'Dalian', 'China', 'Zhoushuizi Airport', 'Asia', False),
    ('DME', 'moscow', 'Moscow', 'Russia', 'Domodedovo International Airport', 'Europe', False),
    ('DMK', 'bangkok-dmk', 'Bangkok', 'Thailand', 'Don Mueang International Airport', 'Asia', False),
    ('DRW', 'darwin', 'Darwin', 'Australia', 'Darwin International Airport', 'Oceania', False),
    ('DUD', 'dunedin', 'Dunedin', 'New Zealand', 'Dunedin Airport', 'Oceania', False),
    ('EBB', 'entebbe', 'Entebbe', 'Uganda', 'Entebbe International Airport', 'Africa', False),
    ('ELP', 'el-paso', 'El Paso', 'United States', 'El Paso International Airport', 'North America', False),
    ('EVN', 'yerevan', 'Yerevan', 'Armenia', 'Zvartnots International Airport', 'Europe', False),
    ('FAI', 'fairbanks', 'Fairbanks', 'United States', 'Fairbanks International Airport', 'North America', False),
    ('FAO', 'faro', 'Faro', 'Portugal', 'Faro Airport', 'Europe', False),
    ('FOR', 'fortaleza', 'Fortaleza', 'Brazil', 'Pinto Martins International Airport', 'Latin America', False),
    ('FUK', 'fukuoka', 'Fukuoka', 'Japan', 'Fukuoka Airport', 'Asia', False),
    ('GBE', 'gaberone', 'Gaberone', 'Botswana', 'Sir Seretse Khama International Airport', 'Africa', False),
    ('GCM', 'georgetown', 'Georgetown', 'Cayman Islands', 'Owen Roberts International Airport', 'Latin America', False),
    ('GDL', 'guadalajara', 'Guadalajara', 'Mexico', 'Don Miguel Hidalgo Y Costilla International Airport', 'Latin America', False),
    ('GMP', 'seoul-gmp', 'Seoul', 'South Korea', 'Gimpo International Airport', 'Asia', False),
    ('GOI', 'goa', 'Goa', 'India', 'Dabolim Airport', 'Asia', False),
    ('GOT', 'gothenborg', 'Gothenborg', 'Sweden', 'Gothenburg-Landvetter Airport', 'Europe', False),
    ('GYE', 'guayaquil', 'Guayaquil', 'Ecuador', 'Jose Joaquin de Olmedo International Airport', 'Latin America', False),
    ('HBA', 'hobart', 'Hobart', 'Australia', 'Hobart International Airport', 'Oceania', False),
    ('HGH', 'hangzhou', 'Hangzhou', 'China', 'Hangzhou Xiaoshan International Airport', 'Asia', False),
    ('HKD', 'hakodate', 'Hakodate', 'Japan', 'Hakodate Airport', 'Asia', False),
    ('HRB', 'harbin', 'Harbin', 'China', 'Taiping Airport', 'Asia', False),
    ('HRE', 'harare', 'Harare', 'Zimbabwe', 'Robert Gabriel Mugabe International Airport', 'Africa', False),
    ('IBZ', 'ibiza', 'Ibiza', 'Spain', 'Ibiza Airport', 'Europe', False),
    ('IKA', 'tehran', 'Tehran', 'Iran', 'Imam Khomeini International Airport', 'Middle East', False),
    ('IND', 'indianapolis', 'Indianapolis', 'United States', 'Indianapolis International Airport', 'North America', False),
    ('ISB', 'islamabad', 'Islamabad', 'Pakistan', 'New Islamabad International Airport', 'Asia', False),
    ('IXC', 'chandigarh', 'Chandigarh', 'India', 'Chandigarh Airport', 'Asia', False),
    ('JAX', 'jacksonville', 'Jacksonville', 'United States', 'Jacksonville International Airport', 'North America', False),
    ('KBP', 'kiev', 'Kiev', 'Ukraine', 'Boryspil International Airport', 'Europe', False),
    ('KGL', 'kigali', 'Kigali', 'Rwanda', 'Kigali International Airport', 'Africa', False),
    ('KHI', 'karachi', 'Karachi', 'Pakistan', 'Jinnah International Airport', 'Asia', False),
    ('KIN', 'kingston', 'Kingston', 'Jamaica', 'Norman Manley International Airport', 'Latin America', False),
    ('KJA', 'krasnoyarsk', 'Krasnoyarsk', 'Russia', 'Yemelyanovo Airport', 'Europe', False),
    ('KMG', 'kunming', 'Kunming', 'China', 'Kunming Changshui International Airport', 'Asia', False),
    ('KOA', 'kona', 'Kona', 'United States', 'Ellison Onizuka Kona International At Keahole Airport', 'North America', False),
    ('KUN', 'kaunas', 'Kaunas', 'Lithuania', 'Kaunas International Airport', 'Europe', False),
    ('KZN', 'kazan', 'Kazan', 'Russia', 'Kazan International Airport', 'Europe', False),
    ('LAD', 'luanda', 'Luanda', 'Angola', 'Quatro de Fevereiro Airport', 'Africa', False),
    ('LBA', 'leeds', 'Leeds', 'United Kingdom', 'Leeds Bradford Airport', 'Europe', False),
    ('LED', 'st-petersburg', 'St. Petersburg', 'Russia', 'Pulkovo Airport', 'Europe', False),
    ('LGB', 'long-beach', 'Long Beach', 'United States', 'Long Beach /Daugherty Field/ Airport', 'North America', False),
    ('LHE', 'lahore', 'Lahore', 'Pakistan', 'Alama Iqbal International Airport', 'Asia', False),
    ('LIH', 'lihue', 'Lihue', 'United States', 'Lihue Airport', 'North America', False),
    ('LJU', 'ljubljana', 'Ljubljana', 'Slovenia', 'Ljubljana Joze Pucnik Airport', 'Europe', False),
    ('LPA', 'gran-canaria', 'Gran Canaria', 'Spain', 'Gran Canaria Airport', 'Europe', False),
    ('LPB', 'la-paz', 'La Paz', 'Bolivia', 'El Alto International Airport', 'Latin America', False),
    ('LPL', 'liverpool', 'Liverpool', 'United Kingdom', 'Liverpool John Lennon Airport', 'Europe', False),
    ('LTN', 'london-ltn', 'London', 'United Kingdom', 'London Luton Airport', 'Europe', False),
    ('LWO', 'lvov', 'Lvov', 'Ukraine', 'Lviv International Airport', 'Europe', False),
    ('MAO', 'manaus', 'Manaus', 'Brazil', 'Eduardo Gomes International Airport', 'Latin America', False),
    ('MBJ', 'montego-bay', 'Montego Bay', 'Jamaica', 'Sangster International Airport', 'Latin America', False),
    ('MCI', 'kansas-city', 'Kansas City', 'United States', 'Kansas City International Airport', 'North America', False),
    ('MCT', 'muscat', 'Muscat', 'Oman', 'Muscat International Airport', 'Middle East', False),
    ('MEM', 'memphis', 'Memphis', 'United States', 'Memphis International Airport', 'North America', False),
    ('MFM', 'macau', 'Macau', 'Macau', 'Macau International Airport', 'Asia', False),
    ('MKE', 'milwaukee', 'Milwaukee', 'United States', 'General Mitchell International Airport', 'North America', False),
    ('MLA', 'malta', 'Malta', 'Malta', 'Malta International Airport', 'Europe', False),
    ('MPL', 'montpellier', 'Montpellier', 'France', 'Montpellier-Mediterranee Airport', 'Europe', False),
    ('MPM', 'maputo', 'Maputo', 'Mozambique', 'Maputo Airport', 'Africa', False),
    ('MRS', 'marseille', 'Marseille', 'France', 'Marseille Provence Airport', 'Europe', False),
    ('MRU', 'plaisance', 'Plaisance', 'Mauritius', 'Sir Seewoosagur Ramgoolam International Airport', 'Africa', False),
    ('MTY', 'monterrey', 'Monterrey', 'Mexico', 'General Mariano Escobedo International Airport', 'Latin America', False),
    ('MVD', 'montevideo', 'Montevideo', 'Uruguay', 'Carrasco International /General C L Berisso Airport', 'Latin America', False),
    ('MYR', 'myrtle-beach', 'Myrtle Beach', 'United States', 'Myrtle Beach International Airport', 'North America', False),
    ('NCL', 'newcastle', 'Newcastle', 'United Kingdom', 'Newcastle Airport', 'Europe', False),
    ('NGO', 'nagoya', 'Nagoya', 'Japan', 'Chubu Centrair International Airport', 'Asia', False),
    ('NKG', 'nanjing', 'Nanjing', 'China', 'Nanjing Lukou Airport', 'Asia', False),
    ('NOU', 'noumea', 'Noumea', 'New Caledonia', 'La Tontouta International Airport', 'Oceania', False),
    ('NTE', 'nantes', 'Nantes', 'France', 'Nantes Atlantique Airport', 'Europe', False),
    ('NUE', 'nuernberg', 'Nuernberg', 'Germany', 'Nuremberg Airport', 'Europe', False),
    ('OAK', 'oakland', 'Oakland', 'United States', 'Metropolitan Oakland International Airport', 'North America', False),
    ('OGG', 'kahului', 'Kahului', 'United States', 'Kahului Airport', 'North America', False),
    ('OKA', 'okinawa', 'Okinawa', 'Japan', 'Naha Airport', 'Asia', False),
    ('OKC', 'oklahoma-city', 'Oklahoma City', 'United States', 'Will Rogers World Airport', 'North America', False),
    ('OMA', 'omaha', 'Omaha', 'United States', 'Eppley Airfield', 'North America', False),
    ('ONT', 'ontario', 'Ontario', 'United States', 'Ontario International Airport', 'North America', False),
    ('OOL', 'coolangatta', 'Coolangatta', 'Australia', 'Gold Coast Airport', 'Oceania', False),
    ('OVB', 'novosibirsk', 'Novosibirsk', 'Russia', 'Tolmachevo Airport', 'Europe', False),
    ('PAP', 'port-au-prince', 'Port-au-prince', 'Haiti', 'Toussaint Louverture International Airport', 'Latin America', False),
    ('PIT', 'pittsburgh', 'Pittsburgh', 'United States', 'Pittsburgh International Airport', 'North America', False),
    ('PMO', 'palermo', 'Palermo', 'Italy', 'FalconeBorsellino Airport', 'Europe', False),
    ('PNH', 'phnom-penh', 'Phnom-penh', 'Cambodia', 'Phnom Penh International Airport', 'Asia', False),
    ('POA', 'porto-alegre', 'Porto Alegre', 'Brazil', 'Salgado Filho Airport', 'Latin America', False),
    ('POM', 'port-moresby', 'Port Moresby', 'Papua New Guinea', 'Port Moresby Jacksons International Airport', 'Oceania', False),
    ('POS', 'port-of-spain', 'Port-of-spain', 'Trinidad and Tobago', 'Piarco International Airport', 'Latin America', False),
    ('PSA', 'pisa', 'Pisa', 'Italy', 'Pisa International Airport', 'Europe', False),
    ('PVD', 'providence', 'Providence', 'United States', 'Theodore Francis Green State Airport', 'North America', False),
    ('PVR', 'puerto-vallarta', 'Puerto Vallarta', 'Mexico', 'Licenciado Gustavo Diaz Ordaz International Airport', 'Latin America', False),
    ('RDU', 'raleigh-durham', 'Raleigh-durham', 'United States', 'Raleigh Durham International Airport', 'North America', False),
    ('REC', 'recife', 'Recife', 'Brazil', 'Guararapes - Gilberto Freyre International Airport', 'Latin America', False),
    ('RGN', 'yangon', 'Yangon', 'Myanmar', 'Yangon International Airport', 'Asia', False),
    ('RIC', 'richmond', 'Richmond', 'United States', 'Richmond International Airport', 'North America', False),
    ('ROT', 'rotorua', 'Rotorua', 'New Zealand', 'Rotorua Regional Airport', 'Oceania', False),
    ('SAT', 'san-antonio', 'San Antonio', 'United States', 'San Antonio International Airport', 'North America', False),
    ('SAV', 'savannah', 'Savannah', 'United States', 'Savannah Hilton Head International Airport', 'North America', False),
    ('SDQ', 'santo-domingo', 'Santo Domingo', 'Dominican Republic', 'Las Americas International Airport', 'Latin America', False),
    ('SEZ', 'mahe', 'Mahe', 'Seychelles', 'Seychelles International Airport', 'Africa', False),
    ('SGN', 'ho-chi-minh-city', 'Ho Chi Minh City', 'Vietnam', 'Tan Son Nhat International Airport', 'Asia', False),
    ('SHJ', 'sharjah', 'Sharjah', 'United Arab Emirates', 'Sharjah International Airport', 'Middle East', False),
    ('SJC', 'san-jose', 'San Jose', 'United States', 'Norman Y. Mineta San Jose International Airport', 'North America', False),
    ('SJD', 'san-jose-del-cabo', 'San Jose Del Cabo', 'Mexico', 'Los Cabos International Airport', 'Latin America', False),
    ('SKP', 'skopje', 'Skopje', 'Macedonia', 'Skopje Alexander the Great Airport', 'Europe', False),
    ('SMF', 'sacramento', 'Sacramento', 'United States', 'Sacramento International Airport', 'North America', False),
    ('SNA', 'santa-ana', 'Santa Ana', 'United States', 'John Wayne Airport-Orange County Airport', 'North America', False),
    ('SPU', 'split', 'Split', 'Croatia', 'Split Airport', 'Europe', False),
    ('SSA', 'salvador', 'Salvador', 'Brazil', 'Deputado Luiz Eduardo Magalhaes International Airport', 'Latin America', False),
    ('STL', 'st-louis', 'St. Louis', 'United States', 'St Louis Lambert International Airport', 'North America', False),
    ('STN', 'london-stn', 'London', 'United Kingdom', 'London Stansted Airport', 'Europe', False),
    ('STR', 'stuttgart', 'Stuttgart', 'Germany', 'Stuttgart Airport', 'Europe', False),
    ('STT', 'st-thomas', 'St. Thomas', 'Virgin Islands', 'Cyril E. King Airport', 'Latin America', False),
    ('SVO', 'moscow-svo', 'Moscow', 'Russia', 'Sheremetyevo International Airport', 'Europe', False),
    ('SVQ', 'sevilla', 'Sevilla', 'Spain', 'Sevilla Airport', 'Europe', False),
    ('TAO', 'qingdao', 'Qingdao', 'China', 'Liuting Airport', 'Asia', False),
    ('TAS', 'tashkent', 'Tashkent', 'Uzbekistan', 'Tashkent International Airport', 'Asia', False),
    ('TBS', 'tbilisi', 'Tbilisi', 'Georgia', 'Tbilisi International Airport', 'Europe', False),
    ('TFS', 'tenerife', 'Tenerife', 'Spain', 'Tenerife South Airport', 'Europe', False),
    ('TIA', 'tirana', 'Tirana', 'Albania', 'Tirana International Airport Mother Teresa', 'Europe', False),
    ('TIJ', 'tijuana', 'Tijuana', 'Mexico', 'General Abelardo L. Rodriguez International Airport', 'Latin America', False),
    ('TLS', 'toulouse', 'Toulouse', 'France', 'Toulouse-Blagnac Airport', 'Europe', False),
    ('TNR', 'antananarivo', 'Antananarivo', 'Madagascar', 'Ivato Airport', 'Africa', False),
    ('TRD', 'trondheim', 'Trondheim', 'Norway', 'Trondheim Airport Vaernes', 'Europe', False),
    ('TRV', 'trivandrum', 'Trivandrum', 'India', 'Trivandrum International Airport', 'Asia', False),
    ('TSA', 'taipei-tsa', 'Taipei', 'Taiwan', 'Taipei Songshan Airport', 'Asia', False),
    ('TSN', 'tianjin', 'Tianjin', 'China', 'Tianjin Binhai International Airport', 'Asia', False),
    ('TUN', 'tunis', 'Tunis', 'Tunisia', 'Tunis Carthage International Airport', 'Africa', False),
    ('TUS', 'tucson', 'Tucson', 'United States', 'Tucson International Airport', 'North America', False),
    ('TXL', 'berlin-txl', 'Berlin', 'Germany', 'Berlin-Tegel Airport', 'Europe', False),
    ('ULN', 'ulan-bator', 'Ulan Bator', 'Mongolia', 'Chinggis Khaan International Airport', 'Asia', False),
    ('VLC', 'valencia', 'Valencia', 'Spain', 'Valencia Airport', 'Europe', False),
    ('VNO', 'vilnius', 'Vilnius', 'Lithuania', 'Vilnius International Airport', 'Europe', False),
    ('VTE', 'vientiane', 'Vientiane', 'Laos', 'Wattay International Airport', 'Asia', False),
    ('VVI', 'santa-cruz', 'Santa Cruz', 'Bolivia', 'Viru Viru International Airport', 'Latin America', False),
    ('VVO', 'vladivostok', 'Vladivostok', 'Russia', 'Vladivostok International Airport', 'Europe', False),
    ('WDH', 'windhoek', 'Windhoek', 'Namibia', 'Hosea Kutako International Airport', 'Africa', False),
    ('WLG', 'wellington', 'Wellington', 'New Zealand', 'Wellington International Airport', 'Oceania', False),
    ('WUH', 'wuhan', 'Wuhan', 'China', 'Wuhan Tianhe International Airport', 'Asia', False),
    ('XMN', 'xiamen', 'Xiamen', 'China', 'Xiamen Gaoqi International Airport', 'Asia', False),
    ('YQB', 'quebec', 'Quebec', 'Canada', 'Quebec Jean Lesage International Airport', 'North America', False),
    ('YQR', 'regina', 'Regina', 'Canada', 'Regina International Airport', 'North America', False),
    ('YWG', 'winnipeg', 'Winnipeg', 'Canada', 'Winnipeg / James Armstrong Richardson International Airport', 'North America', False),
    ('YXE', 'saskatoon', 'Saskatoon', 'Canada', 'Saskatoon John G. Diefenbaker International Airport', 'North America', False),
    ('ZAG', 'zagreb', 'Zagreb', 'Croatia', 'Zagreb Airport', 'Europe', False),
    ('ZQN', 'queenstown-international', 'Queenstown International', 'New Zealand', 'Queenstown International Airport', 'Oceania', False),
    ('XIY', 'xi-an', 'Xian', 'China', 'Xian Xianyang International Airport', 'Asia', False),
    ('PPT', 'papeete', 'Papeete', 'French Polynesia', 'Faaa International Airport', 'Oceania', False),
]

AIRLINES = [
    ('American Airlines', 'AA', 'american'),
    ('Delta', 'DL', 'delta'),
    ('United', 'UA', 'united'),
    ('JetBlue', 'B6', 'jetblue'),
    ('Southwest', 'WN', 'southwest'),
    ('Alaska Airlines', 'AS', 'alaska'),
    ('Spirit', 'NK', 'spirit'),
    ('Frontier', 'F9', 'frontier'),
    ('British Airways', 'BA', 'british'),
    ('Lufthansa', 'LH', 'lufthansa'),
    ('Air France', 'AF', 'airfrance'),
    ('KLM', 'KL', 'klm'),
    ('Emirates', 'EK', 'emirates'),
    ('Qatar Airways', 'QR', 'qatar'),
    ('Etihad', 'EY', 'etihad'),
    ('Singapore Airlines', 'SQ', 'singapore'),
    ('Cathay Pacific', 'CX', 'cathay'),
    ('ANA', 'NH', 'ana'),
    ('Japan Airlines', 'JL', 'jal'),
    ('Turkish Airlines', 'TK', 'turkish'),
    ('Air Canada', 'AC', 'aircanada'),
    ('Iberia', 'IB', 'iberia'),
    ('Qantas', 'QF', 'qantas'),
]

AIRCRAFT = [
    'Boeing 737-800', 'Boeing 737 MAX 8', 'Boeing 777-300ER', 'Boeing 787-9 Dreamliner',
    'Airbus A320', 'Airbus A321', 'Airbus A330-300', 'Airbus A350-900', 'Airbus A380',
    'Embraer E190', 'Bombardier CRJ-900',
]


# Distance-based price and duration rough lookup (city -> city -> minutes, base_price)
def estimate_flight(origin, destination):
    """Return (duration_minutes, base_price) estimate based on region and distance."""
    same = origin[5] == destination[5]  # region
    # Very rough continent base
    base = 120
    if origin[5] == 'North America' and destination[5] == 'North America':
        base = 180
    elif origin[5] == 'Europe' and destination[5] == 'Europe':
        base = 120
    elif origin[5] == 'Asia' and destination[5] == 'Asia':
        base = 200
    elif (origin[5], destination[5]) in [('North America', 'Europe'), ('Europe', 'North America')]:
        base = 480
    elif (origin[5], destination[5]) in [('North America', 'Asia'), ('Asia', 'North America')]:
        base = 780
    elif (origin[5], destination[5]) in [('Europe', 'Asia'), ('Asia', 'Europe')]:
        base = 600
    elif 'Oceania' in (origin[5], destination[5]):
        base = 900
    elif 'Africa' in (origin[5], destination[5]):
        base = 540
    elif 'Middle East' in (origin[5], destination[5]):
        base = 480
    elif 'Latin America' in (origin[5], destination[5]):
        base = 360
    else:
        base = 300

    duration = base + random.randint(-30, 60)
    # Price: roughly $0.5 per minute for economy
    if duration < 200:
        price = random.uniform(89, 380)
    elif duration < 400:
        price = random.uniform(240, 520)
    elif duration < 600:
        price = random.uniform(420, 890)
    elif duration < 800:
        price = random.uniform(620, 1280)
    else:
        price = random.uniform(840, 1680)
    return duration, round(price, 0)


DESCRIPTIONS = {
    'new-york': "The city that never sleeps, home to Times Square, Central Park, and the Statue of Liberty.",
    'los-angeles': "Hollywood glamour, Pacific beaches, and year-round sunshine in California's largest city.",
    'chicago': "The Windy City blends deep-dish pizza, jazz history, and a stunning lakefront skyline.",
    'san-francisco': "Golden Gate views, cable cars, and tech culture wrapped in California cool.",
    'miami': "Art Deco beaches, Latin flavor, and a nightlife scene that stretches till dawn.",
    'las-vegas': "Neon-lit Strip casinos, world-class shows, and desert adventures all in one.",
    'seattle': "Coffee capital, Space Needle, and waterfront vistas in the Pacific Northwest.",
    'boston': "Colonial history meets college-town energy on the Atlantic coast.",
    'atlanta': "The heart of the South - civil rights history, soul food, and a buzzing airport.",
    'dallas': "Big Texas skyline, BBQ, and JFK history near the heart of the Lone Star State.",
    'denver': "Mile-high views, craft beer, and the gateway to the Rocky Mountains.",
    'honolulu': "Waikiki Beach, Pearl Harbor, and Hawaiian aloha on Oahu's south shore.",
    'london': "Big Ben, royal palaces, and the world's most cosmopolitan city.",
    'paris': "The City of Light — Eiffel Tower, Louvre, and unforgettable boulevards.",
    'rome': "The Eternal City — Colosseum, Vatican, and three thousand years of history.",
    'barcelona': "Gaudi architecture, tapas, and the Mediterranean all in one city.",
    'madrid': "Royal palaces, world-class museums, and vibrant nightlife in Spain's capital.",
    'amsterdam': "Canal-lined streets, Dutch masters, and legendary bike culture.",
    'berlin': "Cold War history, techno clubs, and one of Europe's most creative capitals.",
    'munich': "Bavarian beer halls, BMW heritage, and the gateway to the Alps.",
    'vienna': "Imperial palaces, Mozart concerts, and Europe's most elegant coffee culture.",
    'prague': "Medieval castles, Charles Bridge, and a fairytale old town.",
    'zurich': "Alpine lakes, Swiss precision, and old-town charm on the Limmat river.",
    'copenhagen': "Scandinavian design, Tivoli Gardens, and the birthplace of hygge.",
    'stockholm': "Island-hopping in the Baltic, Viking history, and Nordic cool.",
    'oslo': "Fjords, the Munch museum, and Norway's stylish capital.",
    'dublin': "Literary pubs, Trinity College, and Irish hospitality at its finest.",
    'lisbon': "Pastel-colored hills, ancient trams, and Portugal's sunny capital.",
    'athens': "The cradle of democracy — Acropolis, ancient temples, and Greek island access.",
    'istanbul': "Where Europe meets Asia — Hagia Sophia, Grand Bazaar, and Bosphorus views.",
    'reykjavik': "Northern Lights, geothermal spas, and Iceland's gateway city.",
    'tokyo': "Neon-lit streets, centuries-old temples, and cutting-edge cuisine.",
    'osaka': "Japan's kitchen — street food, Osaka Castle, and Universal Studios.",
    'kyoto': "Ancient temples, geisha districts, and the soul of traditional Japan.",
    'seoul': "K-pop energy, palaces, and Korean BBQ in a hyper-modern metropolis.",
    'beijing': "The Forbidden City, Great Wall access, and the capital of imperial China.",
    'shanghai': "Futuristic skyline, Bund promenade, and the gateway to modern China.",
    'hong-kong': "Victoria Harbour skyline, dim sum, and East-meets-West energy.",
    'taipei': "Night markets, Taipei 101, and the ultimate street food destination.",
    'bangkok': "Golden temples, floating markets, and Thailand's electric capital.",
    'singapore': "Marina Bay Sands, hawker centers, and the Garden City of Asia.",
    'kuala-lumpur': "Petronas Towers, night markets, and Malaysia's multicultural hub.",
    'jakarta': "Indonesia's sprawling capital with rich history and vibrant markets.",
    'bali': "Tropical beaches, ancient temples, and Indonesia's island paradise.",
    'manila': "Historic Intramuros, colorful jeepneys, and the Philippine capital.",
    'hanoi': "Ancient quarter, pho, and Vietnam's elegant French-colonial capital.",
    'mumbai': "Bollywood glamour, colonial architecture, and India's financial heart.",
    'delhi': "Red Fort, India Gate, and the historic capital of India.",
    'dubai': "Burj Khalifa, desert safaris, and the Middle East's futuristic metropolis.",
    'abu-dhabi': "Sheikh Zayed Mosque, Louvre Abu Dhabi, and UAE's elegant capital.",
    'doha': "Futuristic skyline, Museum of Islamic Art, and the Gulf's cultural capital.",
    'tel-aviv': "Mediterranean beaches, Bauhaus architecture, and Israel's cosmopolitan city.",
    'cairo': "Pyramids of Giza, Egyptian Museum, and the cradle of ancient civilization.",
    'marrakech': "Souks, palaces, and the Red City of Morocco.",
    'cape-town': "Table Mountain, wine country, and Africa's most scenic city.",
    'nairobi': "Gateway to safaris and the commercial heart of East Africa.",
    'sydney': "Opera House, Harbour Bridge, and Bondi Beach in Australia's largest city.",
    'melbourne': "Coffee culture, street art, and Australia's cultural capital.",
    'auckland': "City of Sails — harbors, volcanoes, and New Zealand's largest city.",
    'toronto': "CN Tower, diverse neighborhoods, and Canada's biggest city.",
    'vancouver': "Mountains meet the sea in Canada's Pacific coast gem.",
    'montreal': "French flair, old-world charm, and North America's most European city.",
    'mexico-city': "Aztec ruins, world-class food, and Mexico's vibrant capital.",
    'cancun': "White sand beaches, Mayan ruins, and Caribbean turquoise waters.",
    'rio-de-janeiro': "Christ the Redeemer, Copacabana, and Brazil's most famous city.",
    'sao-paulo': "South America's largest metropolis — food, art, and nonstop energy.",
    'buenos-aires': "Tango, steak, and Argentina's elegant Paris of the South.",
    'lima': "Colonial plazas, world-class ceviche, and Peru's Pacific capital.",
    'santiago': "Andes views, wine country, and Chile's vibrant capital.",
    'havana': "Vintage cars, salsa music, and Caribbean colonial charm.",
    'san-juan': "Old San Juan's blue cobblestones and Puerto Rico's sunny capital.",
    'punta-cana': "All-inclusive resorts and white sand beaches in the Dominican Republic.",
    'nassau': "Pink sand beaches, crystal waters, and the capital of the Bahamas.",
    'calgary': "Gateway to the Canadian Rockies, home of the Calgary Stampede.",
    'pune': "A vibrant city in Maharashtra known for its educational institutions and IT industry.",
    'phoenix': "Desert sun, golf courses, and the gateway to the Grand Canyon.",
    'manchester': "Industrial heritage, football culture, and a thriving music scene in northern England.",
    'frankfurt': "Germany's financial hub, with a stunning skyline and gateway to Europe.",
    'johannesburg': "South Africa's largest city, a gateway to safari and rich cultural experiences.",
    'kalispell': "Gateway to Glacier National Park and Montana's stunning wilderness.",
    'sapporo': "Snow festivals, ramen, and the gateway to Hokkaido's ski resorts.",
    'venice': "Gondolas, St. Mark's Square, and Italy's most romantic city on water.",
    'florence': "Renaissance art, Tuscan cuisine, and the birthplace of the Renaissance.",
    'milan': "Fashion capital, Duomo cathedral, and northern Italy's stylish powerhouse.",
    'edinburgh': "Medieval castle, festival city, and the capital of Scotland.",
    'brussels': "EU headquarters, chocolate shops, and the heart of Belgium.",
    'budapest': "Thermal baths, Parliament, and the Pearl of the Danube.",
    'warsaw': "Rebuilt old town, WWII history, and Poland's resilient capital.",
    'helsinki': "Design capital, Baltic harbor, and Finland's elegant gateway.",
    # Phase 2 expansion cities — concise blurbs so destination pages still
    # render real copy for the new airport slugs.
    'houston': "Space City — NASA Mission Control, Tex-Mex, and the gateway to the Gulf Coast.",
    'orlando': "Theme-park capital of the world — Disney, Universal, and year-round Florida sunshine.",
    'fort-lauderdale': "Sunny canals, beachfront promenades, and the cruise capital of South Florida.",
    'tampa': "Gulf-coast beaches, Cuban sandwiches, and Florida's bayfront big city.",
    'baltimore': "Inner Harbor, crab cakes, and Maryland's historic port on the Chesapeake.",
    'washington': "Monuments, museums, and the political heart of the United States.",
    'philadelphia': "Liberty Bell, cheesesteaks, and the birthplace of American independence.",
    'minneapolis': "Twin Cities arts scene, Mississippi headwaters, and Mall of America just south.",
    'detroit': "Motor City — Motown, riverfront revival, and the heart of American auto history.",
    'salt-lake-city': "Mountain views, Mormon heritage, and the gateway to Utah's national parks.",
    'san-diego': "Pacific beaches, perfect weather, and California's southernmost big city.",
    'portland': "Coffee, food trucks, and laid-back creativity in the Pacific Northwest.",
    'austin': "Live-music capital, BBQ, and the booming heart of the Texas tech scene.",
    'charlotte': "Banking hub, NASCAR Hall of Fame, and the Queen City of the Carolinas.",
    'nashville': "Country-music capital, honky-tonks, and Tennessee's vibrant downtown.",
    'geneva': "Lake Geneva views, Swiss chocolate, and a global diplomatic capital.",
    'nice': "French Riviera promenade, sun-drenched beaches, and Cote d'Azur charm.",
    'lyon': "Gastronomic capital of France, Roman ruins, and Beaujolais wine country.",
    'hamburg': "Maritime heritage, the Reeperbahn, and Germany's stylish port city.",
    'dusseldorf': "Rhine-side promenades, fashion week energy, and German design culture.",
    'cologne': "Twin-spired cathedral, Carnival celebrations, and Rhine river charm.",
    'naples': "Birthplace of pizza, Vesuvius views, and the soul of southern Italy.",
    'bologna': "Medieval porticoes, Italy's culinary capital, and ancient university charm.",
    'verona': "Roman arena, Romeo and Juliet's balcony, and Venetian-Alpine elegance.",
    'krakow': "Wawel Castle, medieval old town, and Poland's cultural heart.",
    'bucharest': "Belle Epoque palaces, Communist-era boulevards, and Romania's lively capital.",
    'sofia': "Roman ruins, Orthodox cathedrals, and the gateway to the Balkans.",
    'riga': "Art Nouveau facades, medieval old town, and Latvia's Baltic capital.",
    'tallinn': "Medieval old town, cobblestone alleys, and Estonia's UNESCO-listed capital.",
    'malaga': "Andalusian sunshine, Picasso's birthplace, and the Costa del Sol's gateway.",
    'palma': "Gothic cathedral, Mediterranean marina, and the heart of Mallorca.",
    'porto': "Port wine cellars, Douro river views, and Portugal's northern jewel.",
    'glasgow': "Victorian architecture, music venues, and Scotland's largest city.",
    'guangzhou': "Pearl River metropolis, Cantonese cuisine, and southern China's trade hub.",
    'chengdu': "Spicy Sichuan food, giant pandas, and the laid-back capital of western China.",
    'kaohsiung': "Taiwan's southern harbor city, lantern-lit waterfront, and night-market culture.",
    'phuket': "Thailand's largest island — beaches, Buddhist temples, and Andaman sunsets.",
    'chiang-mai': "Ancient temples, mountain trekking, and the laid-back gateway to northern Thailand.",
    'kathmandu': "Himalayan gateway, Buddhist stupas, and Nepal's ancient capital.",
    'bangalore': "India's Silicon Valley — tech campuses, craft beer, and pleasant year-round weather.",
    'chennai': "South India's coastal capital — Marina Beach, Tamil culture, and ancient temples.",
    'hyderabad': "Biryani, the Charminar, and India's pearl-trading historic capital.",
    'dhaka': "Bustling Bangladesh capital — rickshaws, Mughal forts, and riverside life.",
    'colombo': "Indian Ocean port, colonial architecture, and Sri Lanka's energetic capital.",
    'busan': "South Korea's beach city — seafood markets, hot springs, and seaside temples.",
    'riyadh': "Modern skyscrapers meet desert heritage in Saudi Arabia's fast-changing capital.",
    'jeddah': "Red Sea gateway to Mecca — corniche promenade and historic Al-Balad district.",
    'amman': "Roman ruins, hillside neighborhoods, and Jordan's hospitable capital.",
    'beirut': "Mediterranean nightlife, layered history, and Lebanon's resilient capital.",
    'kuwait-city': "Gulf skyline, traditional souks, and Kuwait's coastal capital.",
    'casablanca': "Atlantic-coast metropolis — Hassan II Mosque and Morocco's economic heart.",
    'addis-ababa': "Highland capital, Ethiopian coffee culture, and the headquarters of the African Union.",
    'lagos': "West Africa's largest city — Afrobeats, Atlantic beaches, and nonstop energy.",
    'accra': "Atlantic capital of Ghana — Cape Coast access, vibrant markets, and rich history.",
    'brisbane': "River city, sunny South Bank, and the gateway to Australia's Gold Coast.",
    'perth': "Indian Ocean beaches, swan river, and Australia's sunny west-coast capital.",
    'adelaide': "Wine country, festivals, and South Australia's relaxed garden city.",
    'christchurch': "Garden City of New Zealand — gateway to the Southern Alps and Banks Peninsula.",
    'nadi': "Fiji's main island gateway — beach resorts, coral reefs, and South Pacific welcome.",
    'bogota': "Andean capital — colonial La Candelaria, world-class museums, and Colombian energy.",
    'quito': "Highest official capital in the world — Spanish colonial old town in the Andes.",
    'panama-city': "Modern skyline meeting the Panama Canal and colonial Casco Viejo.",
    'san-jose-cr': "Costa Rica's mountain capital — gateway to rainforests, volcanoes, and pura vida.",
    'brasilia': "Mid-century modernist capital — Oscar Niemeyer's UNESCO-listed planned city.",
    'medellin': "City of Eternal Spring — innovative urban transit and vibrant Paisa culture.",
    'guatemala-city': "Central American capital — gateway to Mayan ruins and volcanic highlands.",
    'ottawa': "Canada's capital — Parliament Hill, Rideau Canal, and bilingual charm.",
    'halifax': "Atlantic-coast harbor, maritime history, and Nova Scotia's friendly capital.",
    'edmonton': "Festival City of Canada — North Saskatchewan river valley and the West Edmonton Mall.",
}


def seed_all(db, Airport, Flight):
    # Pull augmented metadata (icao/lat/lng/tz) and the R3 + R4 extra-airport
    # lists. R4 adds another ~450 airports from OpenFlights airports.dat so the
    # catalog reaches 1200+ for broader benchmark coverage.
    try:
        from airport_extras import AIRPORT_META, EXTRA_AIRPORTS
    except ImportError:
        AIRPORT_META = {}
        EXTRA_AIRPORTS = []
    try:
        from airport_extras import R4_EXTRA_AIRPORTS
    except ImportError:
        R4_EXTRA_AIRPORTS = []

    # 1. Airports
    slug_to_airport_ids = {}
    for (iata, slug, city, country, name, region, popular) in AIRPORTS:
        gallery_dir = BASE_DIR / 'static' / 'images' / 'destinations' / slug
        gallery = []
        if gallery_dir.exists():
            for f in sorted(gallery_dir.glob('img_*.*')):
                if f.stat().st_size > 10000 and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                    gallery.append(f"/static/images/destinations/{slug}/{f.name}")
        image = gallery[0] if gallery else ''
        meta = AIRPORT_META.get(iata)
        icao, lat, lng, tz = (meta if meta else ('', None, None, ''))
        airport = Airport(
            iata=iata,
            icao=icao,
            city_slug=slug,
            city=city,
            country=country,
            name=name,
            region=region,
            is_popular=popular,
            latitude=lat,
            longitude=lng,
            timezone=tz,
            image=image,
            gallery_json=json.dumps(gallery),
            description=DESCRIPTIONS.get(slug, f"Explore {city}, {country}."),
        )
        db.session.add(airport)
        slug_to_airport_ids.setdefault(slug, []).append(iata)

    # R3: append OpenFlights-sourced regional / international airports.
    for entry in EXTRA_AIRPORTS:
        (iata, slug, city, country, name, region, popular,
         icao, lat, lng, tz) = entry
        gallery_dir = BASE_DIR / 'static' / 'images' / 'destinations' / slug
        gallery = []
        if gallery_dir.exists():
            for f in sorted(gallery_dir.glob('img_*.*')):
                if f.stat().st_size > 10000 and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                    gallery.append(f"/static/images/destinations/{slug}/{f.name}")
        image = gallery[0] if gallery else ''
        airport = Airport(
            iata=iata,
            icao=icao,
            city_slug=slug,
            city=city,
            country=country,
            name=name,
            region=region,
            is_popular=popular,
            latitude=lat,
            longitude=lng,
            timezone=tz,
            image=image,
            gallery_json=json.dumps(gallery),
            description=DESCRIPTIONS.get(slug, f"Explore {city}, {country}."),
        )
        db.session.add(airport)
        slug_to_airport_ids.setdefault(slug, []).append(iata)

    # R4: append another 450 OpenFlights airports for total 1200+.
    for entry in R4_EXTRA_AIRPORTS:
        (iata, slug, city, country, name, region, popular,
         icao, lat, lng, tz) = entry
        gallery_dir = BASE_DIR / 'static' / 'images' / 'destinations' / slug
        gallery = []
        if gallery_dir.exists():
            for f in sorted(gallery_dir.glob('img_*.*')):
                if f.stat().st_size > 10000 and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                    gallery.append(f"/static/images/destinations/{slug}/{f.name}")
        image = gallery[0] if gallery else ''
        airport = Airport(
            iata=iata,
            icao=icao,
            city_slug=slug,
            city=city,
            country=country,
            name=name,
            region=region,
            is_popular=popular,
            latitude=lat,
            longitude=lng,
            timezone=tz,
            image=image,
            gallery_json=json.dumps(gallery),
            description=DESCRIPTIONS.get(slug, f"Explore {city}, {country}."),
        )
        db.session.add(airport)
        slug_to_airport_ids.setdefault(slug, []).append(iata)
    db.session.commit()

    # Build iata -> Airport
    airport_by_iata = {a.iata: a for a in Airport.query.all()}

    # 2. Flight catalog: generate routes between popular airports
    random.seed(42)
    popular_airports = [a for a in Airport.query.filter_by(is_popular=True).all()]
    # Map iata -> raw tuple so estimate_flight works. Include R4 airports too
    # so make_flight_dict() can resolve any seeded IATA, not just the AIRPORTS
    # tuple set. The shape mirrors AIRPORTS rows: (iata, slug, city, country,
    # name, region, popular).
    raw_by_iata = {t[0]: t for t in AIRPORTS}
    for entry in EXTRA_AIRPORTS:
        raw_by_iata.setdefault(entry[0], entry[:7])
    for entry in R4_EXTRA_AIRPORTS:
        raw_by_iata.setdefault(entry[0], entry[:7])
    today = date.today()

    flights_count = 0
    seen_flight_numbers = set()

    # Build up ~40 popular routes out of top US airports
    us_hubs = ['JFK', 'LGA', 'EWR', 'LAX', 'ORD', 'SFO', 'MIA', 'ATL',
               'DFW', 'SEA', 'BOS', 'DEN', 'LAS']
    intl_dests = ['LHR', 'LGW', 'CDG', 'FCO', 'BCN', 'AMS', 'BER', 'MAD', 'ZRH', 'DUB', 'IST',
                  'HND', 'NRT', 'ICN', 'PEK', 'PVG', 'HKG', 'SIN', 'BKK', 'DXB', 'DOH',
                  'SYD', 'MEL', 'YYZ', 'YVR', 'MEX', 'CUN', 'GIG', 'EZE', 'LIM',
                  'HNL', 'ATH', 'LIS', 'PRG', 'CPH', 'ARN', 'DPS', 'KIX', 'CPT', 'RAK',
                  'VCE', 'MXP', 'VIE']

    # US hub -> US hub
    us_pairs = []
    for i in range(len(us_hubs)):
        for j in range(len(us_hubs)):
            if i != j:
                us_pairs.append((us_hubs[i], us_hubs[j]))
    # US hub -> intl
    intl_pairs = [(h, d) for h in us_hubs for d in intl_dests]
    # Intl -> intl (limited)
    intl_intl = [
        ('LHR', 'CDG'), ('LHR', 'BCN'), ('LHR', 'FCO'), ('LHR', 'AMS'),
        ('CDG', 'FCO'), ('CDG', 'BCN'), ('CDG', 'MAD'), ('CDG', 'AMS'),
        ('FCO', 'ATH'), ('FCO', 'IST'), ('BCN', 'MAD'),
        ('LHR', 'DXB'), ('CDG', 'DXB'), ('AMS', 'DXB'),
        ('DXB', 'HND'), ('DXB', 'BKK'), ('DXB', 'SIN'),
        ('SIN', 'BKK'), ('SIN', 'HKG'), ('HND', 'ICN'),
        ('HND', 'HKG'), ('HKG', 'BKK'), ('ICN', 'PEK'),
        ('SYD', 'MEL'), ('SYD', 'AKL'),
        ('GIG', 'EZE'), ('EZE', 'SCL'),
        ('LIS', 'SIN'), ('LIS', 'LHR'), ('LIS', 'CDG'),
    ]

    all_pairs = us_pairs + intl_pairs + intl_intl

    def make_flight(origin_iata, dest_iata, departure_date, airline_idx=None):
        """Build a single Flight from the raw tuples."""
        if origin_iata not in raw_by_iata or dest_iata not in raw_by_iata:
            return None
        if origin_iata not in airport_by_iata or dest_iata not in airport_by_iata:
            return None
        origin_raw = raw_by_iata[origin_iata]
        dest_raw = raw_by_iata[dest_iata]
        duration, base_price = estimate_flight(origin_raw, dest_raw)
        if airline_idx is None:
            airline_idx = random.randint(0, len(AIRLINES) - 1)
        airline_name, airline_code, airline_slug = AIRLINES[airline_idx]
        fn = f"{airline_code}{random.randint(10, 99999)}"
        while fn in seen_flight_numbers:
            fn = f"{airline_code}{random.randint(10, 99999)}"
        seen_flight_numbers.add(fn)

        depart_h = random.choice([5, 6, 7, 8, 9, 10, 11, 13, 15, 16, 17, 18, 19, 20, 22])
        depart_m = random.choice([0, 15, 30, 45])
        dep_str = f"{depart_h:02d}:{depart_m:02d}"
        total_minutes = depart_h * 60 + depart_m + duration
        arr_day_offset = total_minutes // (24 * 60)
        arr_hm = total_minutes % (24 * 60)
        arr_h = arr_hm // 60
        arr_m = arr_hm % 60
        arr_str = f"{arr_h:02d}:{arr_m:02d}"
        arrival_date = departure_date + timedelta(days=arr_day_offset)

        stops = random.choice([0, 0, 0, 1, 1, 2]) if duration > 240 else random.choice([0, 0, 1])
        co2 = int(duration * 0.9) + random.randint(-20, 30)
        co2_vs = random.choice([-20, -15, -10, -5, 0, 0, 5, 10, 15, 20, 25])

        price = base_price
        price_premium = round(price * 1.5, 0)
        price_business = round(price * 3, 0)
        price_first = round(price * 5, 0)

        return Flight(
            flight_number=fn,
            airline=airline_name,
            airline_code=airline_code,
            airline_logo=f"/static/images/airlines/{airline_slug}.png",
            origin_id=airport_by_iata[origin_iata].id,
            destination_id=airport_by_iata[dest_iata].id,
            departure_date=departure_date,
            departure_time=dep_str,
            arrival_date=arrival_date,
            arrival_time=arr_str,
            duration_minutes=duration,
            stops=stops,
            aircraft=random.choice(AIRCRAFT),
            cabin_class='Economy',
            price=price,
            price_premium=price_premium,
            price_business=price_business,
            price_first=price_first,
            co2_emissions_kg=co2,
            co2_vs_typical=co2_vs,
            baggage_free=random.choice([0, 1, 1, 2]),
            legroom_inches=random.choice([30, 31, 32, 33]),
            wifi=random.choice([True, True, True, False]),
            power=random.choice([True, True, False]),
            entertainment=random.choice([True, True, True, False]),
            rating=round(random.uniform(3.8, 4.9), 1),
            meal_service=random.choice([
                'Full meal service', 'Full meal service', 'Snack box',
                'Multi-course dining', 'Complimentary meals and drinks',
                'Buy on board', 'Hot meal included',
            ]) if duration > 180 else random.choice(['Snack box', 'Buy on board', 'Complimentary snack']),
            seat_type=random.choice([
                'Standard seat', 'Standard seat', 'Recliner seat',
            ]),
            seat_pitch=random.choice(['31 in', '31 in', '32 in', '32 in', '33 in', '34 in']),
        )

    # Faster sibling: returns a plain dict so the caller can bulk-INSERT without
    # paying SQLAlchemy ORM construction + descriptor overhead. Output keys
    # match the Flight column names exactly so the dict is a drop-in for
    # `INSERT INTO flight (...) VALUES (:...)`.
    def make_flight_dict(origin_iata, dest_iata, departure_date):
        if origin_iata not in raw_by_iata or dest_iata not in raw_by_iata:
            return None
        if origin_iata not in airport_by_iata or dest_iata not in airport_by_iata:
            return None
        origin_raw = raw_by_iata[origin_iata]
        dest_raw = raw_by_iata[dest_iata]
        duration, base_price = estimate_flight(origin_raw, dest_raw)
        airline_idx = random.randint(0, len(AIRLINES) - 1)
        airline_name, airline_code, airline_slug = AIRLINES[airline_idx]
        fn = f"{airline_code}{random.randint(10, 99999)}"
        while fn in seen_flight_numbers:
            fn = f"{airline_code}{random.randint(10, 99999)}"
        seen_flight_numbers.add(fn)
        depart_h = random.choice([5, 6, 7, 8, 9, 10, 11, 13, 15, 16, 17, 18, 19, 20, 22])
        depart_m = random.choice([0, 15, 30, 45])
        total_minutes = depart_h * 60 + depart_m + duration
        arr_day_offset = total_minutes // (24 * 60)
        arr_hm = total_minutes % (24 * 60)
        stops = random.choice([0, 0, 0, 1, 1, 2]) if duration > 240 else random.choice([0, 0, 1])
        co2 = int(duration * 0.9) + random.randint(-20, 30)
        co2_vs = random.choice([-20, -15, -10, -5, 0, 0, 5, 10, 15, 20, 25])
        price = base_price
        return {
            'flight_number': fn,
            'airline': airline_name,
            'airline_code': airline_code,
            'airline_logo': f"/static/images/airlines/{airline_slug}.png",
            'origin_id': airport_by_iata[origin_iata].id,
            'destination_id': airport_by_iata[dest_iata].id,
            'departure_date': departure_date,
            'departure_time': f"{depart_h:02d}:{depart_m:02d}",
            'arrival_date': departure_date + timedelta(days=arr_day_offset),
            'arrival_time': f"{arr_hm // 60:02d}:{arr_hm % 60:02d}",
            'duration_minutes': duration,
            'stops': stops,
            'stop_cities': '',
            'aircraft': random.choice(AIRCRAFT),
            'cabin_class': 'Economy',
            'price': price,
            'price_premium': round(price * 1.5, 0),
            'price_business': round(price * 3, 0),
            'price_first': round(price * 5, 0),
            'co2_emissions_kg': co2,
            'co2_vs_typical': co2_vs,
            'baggage_free': random.choice([0, 1, 1, 2]),
            'baggage_included': True,
            'return_date': None,
            'legroom_inches': random.choice([30, 31, 32, 33]),
            'wifi': random.choice([True, True, True, False]),
            'power': random.choice([True, True, False]),
            'entertainment': random.choice([True, True, True, False]),
            'meal_service': (random.choice([
                'Full meal service', 'Full meal service', 'Snack box',
                'Multi-course dining', 'Complimentary meals and drinks',
                'Buy on board', 'Hot meal included',
            ]) if duration > 180
              else random.choice(['Snack box', 'Buy on board', 'Complimentary snack'])),
            'seat_type': random.choice([
                'Standard seat', 'Standard seat', 'Recliner seat',
            ]),
            'seat_pitch': random.choice(['31 in', '31 in', '32 in', '32 in', '33 in', '34 in']),
            'rating': round(random.uniform(3.8, 4.9), 1),
            'is_best': False,
            'is_cheapest': False,
            'is_fastest': False,
            'created_at': MIRROR_REFERENCE_DATE,
        }

    # Additional intl -> intl and reverse routes needed by tasks
    task_extra_pairs = [
        ('DUB', 'ATH'), ('TLV', 'VCE'), ('HND', 'SYD'), ('GIG', 'LAX'),
        ('BOM', 'YVR'), ('DXB', 'FCO'), ('EZE', 'AMS'), ('BKK', 'MAD'),
        ('CPT', 'SIN'), ('AKL', 'HNL'), ('ARN', 'YYZ'), ('PVG', 'YVR'),
        ('CAI', 'YUL'), ('HEL', 'DEL'), ('EZE', 'PEK'), ('OSL', 'DXB'),
        ('PRG', 'HND'), ('PRG', 'CTS'), ('SEA', 'HND'), ('HKG', 'FCA'),
        ('MEX', 'FRA'), ('JNB', 'YYZ'), ('YYC', 'JFK'), ('PNQ', 'JFK'),
        ('EDI', 'MAN'), ('PHX', 'MIA'),
        # R3: new pairs needed for the expanded review/task suite. These get
        # sparse coverage (6-9 dates) which is plenty for benchmark questions
        # like "find the cheapest fare on route X" without bloating the catalog.
        ('JFK', 'TLV'), ('JFK', 'OPO'), ('JFK', 'BOM'), ('JFK', 'DEL'),
        ('JFK', 'GRU'), ('JFK', 'GVA'), ('JFK', 'MUC'), ('JFK', 'RUH'),
        ('JFK', 'SAN'), ('JFK', 'PDX'), ('JFK', 'PHX'), ('JFK', 'AUS'),
        ('JFK', 'NAS'), ('JFK', 'PUJ'), ('JFK', 'SJU'),
        ('LAX', 'PVR'), ('LAX', 'SJD'), ('LAX', 'GDL'), ('LAX', 'CDG'),
        ('LAX', 'NRT'), ('LAX', 'PEK'), ('LAX', 'HKG'),
        ('SFO', 'NRT'), ('SFO', 'PEK'), ('SFO', 'AMS'), ('SFO', 'BCN'),
        ('SFO', 'FCO'), ('SFO', 'BER'), ('SFO', 'SYD'), ('SFO', 'AKL'),
        ('SFO', 'PVG'),
        ('ORD', 'NRT'), ('ORD', 'AMS'), ('ORD', 'DUB'), ('ORD', 'BCN'),
        ('ORD', 'CUN'), ('ORD', 'MEX'), ('ORD', 'GRU'),
        ('BOS', 'AMS'), ('BOS', 'DUB'), ('BOS', 'LHR'), ('BOS', 'CDG'),
        ('DFW', 'LHR'), ('DFW', 'CDG'), ('DFW', 'CUN'), ('DFW', 'MCO'),
        ('ATL', 'CDG'), ('ATL', 'AMS'), ('ATL', 'CUN'), ('ATL', 'PUJ'),
        ('ATL', 'DEN'), ('ATL', 'MIA'),
        # Return-leg reciprocals for round-trip "manage" / "rebook" task scenarios
        ('LHR', 'JFK'), ('CDG', 'JFK'), ('HND', 'JFK'), ('NRT', 'JFK'),
        ('DXB', 'JFK'), ('FRA', 'MEX'),
        # Capacity for "explore by budget" / "calendar cheapest day" tasks
        ('JFK', 'CUN'), ('JFK', 'GIG'), ('JFK', 'LIM'), ('LAX', 'GIG'),
        ('LAX', 'EZE'), ('MIA', 'GIG'), ('MIA', 'EZE'), ('MIA', 'BOG'),
        ('MIA', 'PTY'), ('MIA', 'SJO'), ('MIA', 'GUA'), ('MIA', 'CUN'),
        ('MIA', 'CDG'), ('MIA', 'LHR'), ('MIA', 'MAD'), ('MIA', 'FCO'),
    ]
    for pair in task_extra_pairs:
        if pair not in all_pairs:
            all_pairs.append(pair)

    # Catalog density: cover every (month, day) for POPULAR pairs (both
    # endpoints flagged is_popular) so adjacent-day searches on major routes
    # don't return empty. Less popular pairs keep a smaller sparse window —
    # we don't need 365-day coverage on routes nobody benchmarks.
    #
    # Performance: SQLAlchemy ORM is ~50x slower than raw SQL executemany
    # for ~5k+ rows. We build dicts via the Flight() constructor (so all
    # defaults & computed values match) then INSERT via raw SQL.
    from sqlalchemy import inspect as _sa_inspect
    flight_cols = [c.name for c in _sa_inspect(Flight).columns if c.name != 'id']
    insert_sql = (
        "INSERT INTO flight (" + ",".join(flight_cols) + ") VALUES ("
        + ",".join(":" + c for c in flight_cols) + ")"
    )

    def _flight_to_row(f):
        return {c: getattr(f, c) for c in flight_cols}

    # Tier the catalog so total stays in the low tens of thousands:
    #   Top tier: hub-to-hub between major US/intl airports — full leap year
    #     (so adjacent-day searches always hit something on a real route).
    #   Sparse tier: everything else — 6-9 random dates spread over the year.
    TOP_TIER_HUBS = {'JFK', 'LGA', 'EWR', 'LAX', 'ORD', 'SFO', 'BOS', 'SEA',
                     'ATL', 'MIA', 'DFW', 'LHR', 'LGW', 'CDG', 'AMS', 'FRA',
                     'FCO', 'BCN', 'MAD', 'DXB', 'DOH', 'HND', 'NRT', 'ICN',
                     'HKG', 'SIN', 'BKK', 'SYD', 'YYZ', 'YVR'}
    top_tier_pairs = [
        (o, d) for (o, d) in all_pairs
        if o in airport_by_iata and d in airport_by_iata
        and o in TOP_TIER_HUBS and d in TOP_TIER_HUBS
    ]
    sparse_pairs = [
        (o, d) for (o, d) in all_pairs
        if (o, d) not in top_tier_pairs
        and o in airport_by_iata and d in airport_by_iata
    ]

    catalog_anchor = date(2024, 1, 1)
    catalog_rows = []

    # Top-tier: every day for two full years (2024-01-01 → 2025-12-31, 731
    # days including a leap day) so adjacent-day and "next-month" searches in
    # both years hit something on a real route. R4 extends from 366 → 731
    # days for ~115k more top-tier rows, bringing flight catalogue past 200k.
    TOP_TIER_DAYS = 731
    print(f"[seed] top-tier loop: {len(top_tier_pairs)} pairs × {TOP_TIER_DAYS} days")
    _pair_idx = 0
    for origin_iata, dest_iata in top_tier_pairs:
        _pair_idx += 1
        for d_offset in range(TOP_TIER_DAYS):
            dep = catalog_anchor + timedelta(days=d_offset)
            row = make_flight_dict(origin_iata, dest_iata, dep)
            if row:
                catalog_rows.append(row)
                flights_count += 1
        if len(catalog_rows) >= 5000:
            db.session.execute(text(insert_sql), catalog_rows)
            db.session.commit()
            catalog_rows = []
    print(f"[seed] top-tier done, flights so far ~{flights_count}")

    # R4 future-month coverage: a curated set of mega-hub pairs gets a 2026
    # window so "fly out next month" tasks (current date 2026-05-26) resolve.
    # Keep this list short — only the busiest international routes — to avoid
    # exploding the catalogue.
    R4_FUTURE_PAIRS = [
        ('JFK', 'LHR'), ('LHR', 'JFK'), ('JFK', 'CDG'), ('CDG', 'JFK'),
        ('JFK', 'HND'), ('HND', 'JFK'), ('JFK', 'NRT'), ('JFK', 'DXB'),
        ('LAX', 'HND'), ('LAX', 'NRT'), ('LAX', 'SYD'), ('SFO', 'NRT'),
        ('SFO', 'SYD'), ('ORD', 'LHR'), ('ORD', 'CDG'), ('BOS', 'LHR'),
        ('LHR', 'CDG'), ('CDG', 'AMS'), ('AMS', 'JFK'), ('FRA', 'JFK'),
        ('DXB', 'LHR'), ('DXB', 'BKK'), ('SIN', 'LHR'), ('HKG', 'LHR'),
    ]
    future_anchor = date(2026, 1, 1)
    for origin_iata, dest_iata in R4_FUTURE_PAIRS:
        if origin_iata not in airport_by_iata or dest_iata not in airport_by_iata:
            continue
        for d_offset in range(365):  # full 2026
            dep = future_anchor + timedelta(days=d_offset)
            row = make_flight_dict(origin_iata, dest_iata, dep)
            if row:
                catalog_rows.append(row)
                flights_count += 1
        if len(catalog_rows) >= 5000:
            db.session.execute(text(insert_sql), catalog_rows)
            db.session.commit()
            catalog_rows = []

    # Sparse pairs: 6-9 random dates per pair so they're not totally empty
    # but don't bloat the catalog
    for origin_iata, dest_iata in sparse_pairs:
        for offset in random.sample(range(0, 366), k=random.choice([6, 7, 8, 9])):
            dep = catalog_anchor + timedelta(days=offset)
            row = make_flight_dict(origin_iata, dest_iata, dep)
            if row:
                catalog_rows.append(row)
                flights_count += 1
        if len(catalog_rows) >= 3000:
            db.session.execute(text(insert_sql), catalog_rows)
            db.session.commit()
            catalog_rows = []

    if catalog_rows:
        db.session.execute(text(insert_sql), catalog_rows)
        db.session.commit()

    # ----------------------------------------------------------------
    # Task-required flights: generate flights for exact route+date
    # combinations that run_tasks.py expects.
    # ----------------------------------------------------------------
    TASK_ROUTES = [
        # (origin, dest, dates_list, needs_nonstop, needs_first_class, max_price_economy)
        ('EDI', 'MAN', ['2024-12-28'], False, False, None),
        ('ORD', 'CDG', ['2024-02-17'], False, False, None),
        ('JFK', 'LHR', ['2024-01-22', '2023-12-26', '2023-12-25', '2024-01-10'], True, False, None),
        ('YYC', 'JFK', ['2024-01-01'], False, False, None),
        ('ORD', 'LHR', ['2023-12-20'], False, False, None),
        ('TLV', 'VCE', ['2023-12-19'], False, True, None),
        ('PHX', 'MIA', ['2023-12-25'], False, True, 260),  # first class ~5x -> 1300
        ('DUB', 'ATH', ['2023-12-30'], False, False, None),
        ('PNQ', 'JFK', ['2024-01-15'], False, False, None),
        ('JFK', 'HND', ['2024-01-25', '2024-02-10', '2024-01-10', '2024-01-15'], True, False, None),
        ('JFK', 'NRT', ['2024-02-12'], True, False, None),
        ('JFK', 'CDG', ['2023-12-27'], False, False, None),
        ('LHR', 'CDG', ['2024-01-25'], False, False, None),
        ('SFO', 'BER', ['2024-03-05'], False, False, None),
        ('HND', 'SYD', ['2024-02-25'], False, False, None),
        ('GIG', 'LAX', ['2024-03-15'], False, False, None),
        ('BOM', 'YVR', ['2024-02-28'], False, False, None),
        ('DXB', 'FCO', ['2024-03-01'], True, False, None),
        ('EZE', 'AMS', ['2024-03-10'], False, False, None),
        ('BKK', 'MAD', ['2024-02-26'], False, False, 190),  # economy <=1000 -> base~190
        ('JNB', 'YYZ', ['2024-03-30'], False, False, None),
        ('SEA', 'CDG', ['2024-02-27'], False, False, None),
        ('MEX', 'FRA', ['2024-03-05'], True, False, None),
        ('CPT', 'SIN', ['2024-03-20'], False, False, None),
        ('AKL', 'HNL', ['2024-03-25'], False, False, None),
        ('ARN', 'YYZ', ['2024-03-03'], False, False, None),
        ('PVG', 'YVR', ['2024-02-27'], False, False, None),
        ('LIS', 'SIN', ['2024-03-15'], False, False, None),
        ('CAI', 'YUL', ['2024-02-21'], False, False, None),
        ('HEL', 'DEL', ['2024-03-28'], False, False, 190),  # economy <=1000
        ('EZE', 'PEK', ['2024-02-28'], False, False, None),
        ('OSL', 'DXB', ['2024-03-08'], False, False, None),
        ('PRG', 'HND', ['2024-03-20'], False, False, None),
        ('PRG', 'CTS', ['2024-03-20'], False, False, None),
        ('SEA', 'HND', ['2024-05-01'], False, False, None),
        ('HKG', 'FCA', ['2024-03-08'], False, False, None),
    ]

    # Refresh airport lookup after new airports were added
    airport_by_iata = {a.iata: a for a in Airport.query.all()}

    # Multi-airport-city expansion: when a task targets one airport (e.g. HND
    # in JFK→HND), the agent searching by city (`to=Tokyo`) expects to see
    # comparable inventory across BOTH Tokyo airports. Without this expansion,
    # a city search returns 22 HND flights vs 1 NRT catalog flight on the task
    # date — visibly skewed. Same problem for NYC (JFK/LGA/EWR) and London
    # (LHR/LGW). Expand TASK_ROUTES so every sibling-airport variant of each
    # task gets the same dense seeding on the same dates.
    CITY_SIBLINGS = {
        'JFK': ['LGA', 'EWR'], 'LGA': ['JFK', 'EWR'], 'EWR': ['JFK', 'LGA'],
        'LHR': ['LGW'], 'LGW': ['LHR'],
        'HND': ['NRT'], 'NRT': ['HND'],
    }

    def _expand_siblings(routes):
        expanded = []
        seen = set()
        for entry in routes:
            origin, dest = entry[0], entry[1]
            origin_options = [origin] + CITY_SIBLINGS.get(origin, [])
            dest_options = [dest] + CITY_SIBLINGS.get(dest, [])
            for o in origin_options:
                for d in dest_options:
                    if o == d:
                        continue
                    key = (o, d, tuple(entry[2]))
                    if key in seen:
                        continue
                    seen.add(key)
                    new_entry = (o, d) + tuple(entry[2:])
                    expanded.append(new_entry)
        return expanded

    TASK_ROUTES = _expand_siblings(TASK_ROUTES)

    # ----------------------------------------------------------------
    # Per-task seeding: density + diversity matter for benchmark realism.
    # The "Best" composite sort in app.py balances price/duration/stops, so
    # the cheapest flight is no longer top-1 by default — but the *data*
    # also needs to make answers non-obvious:
    #   - 22 flights per task route+date (was 8): forces scrolling/sorting
    #   - Realistic stops mix (~50% nonstop / 35% 1-stop / 15% 2-stop on
    #     long-haul; same-region stays mostly nonstop) so "non-stop only"
    #     filters actually do work
    #   - Wider price spread, with the cheapest deliberately given a
    #     longer duration / more stops so it scores poorly on "Best" —
    #     agent must explicitly switch to "Cheapest" sort to find it
    #   - Independent CO2 variance (airline efficiency * aircraft type)
    #     so lowest-CO2 ≠ cheapest ≠ shortest
    #   - Exactly one flight per route+date marked is_best=True, chosen as
    #     a balanced compromise (mid-price, low stops, mid-duration) — so
    #     `sort=best` top-1 is NOT trivially the answer to any single goal
    # ----------------------------------------------------------------
    for origin_iata, dest_iata, dates, needs_nonstop, needs_first, max_eco_price in TASK_ROUTES:
        if origin_iata not in airport_by_iata or dest_iata not in airport_by_iata:
            continue
        # Estimate route distance/duration to decide stops mix and price spread
        if origin_iata in raw_by_iata and dest_iata in raw_by_iata:
            base_duration, base_price = estimate_flight(
                raw_by_iata[origin_iata], raw_by_iata[dest_iata]
            )
        else:
            base_duration, base_price = 240, 400

        for date_str in dates:
            dep_date = date(int(date_str[:4]), int(date_str[5:7]), int(date_str[8:10]))
            POOL_SIZE = 22

            # Decide stops mix per route. Include some 3-stop flights on
            # medium/long-haul routes so "≤2 stops" filter tasks (e.g., task
            # 38 OSL→DXB) actually have distractors to filter out.
            if needs_nonstop:
                # Tasks that explicitly assert nonstop must still have many,
                # but enough 1/2 stops that the filter is non-trivial.
                stops_pool = ([0] * 12) + ([1] * 7) + ([2] * 3)
            elif base_duration < 180:
                # Short-haul: mostly nonstop in reality
                stops_pool = ([0] * 16) + ([1] * 5) + ([2] * 1)
            elif base_duration < 480:
                # Medium-haul: balanced mix + a 3-stop distractor
                stops_pool = ([0] * 10) + ([1] * 7) + ([2] * 3) + ([3] * 2)
            else:
                # Long-haul: stops are common, include a couple of 3-stops
                stops_pool = ([0] * 8) + ([1] * 8) + ([2] * 4) + ([3] * 2)
            random.shuffle(stops_pool)

            generated = []
            for i in range(POOL_SIZE):
                f = make_flight(origin_iata, dest_iata, dep_date)
                if f is None:
                    continue

                # Apply stops from the diversified pool (overrides random in make_flight)
                f.stops = stops_pool[i] if i < len(stops_pool) else random.choice([0, 1])

                # Price spread. For budget-cap tasks (max_eco_price set), split
                # the pool into two halves: ANSWERS below the cap and DISTRACTORS
                # well above it. Without distractors, "≤ $X" filter tasks become
                # no-ops (every result already passes) and the agent never has
                # to apply the price filter. The distractor multiplier (~5.5–9x
                # of max_eco_price) is tuned so that user-task thresholds like
                # "First Class ≤ $1320" or "Economy ≤ $1000" land squarely
                # between the answer and distractor tiers.
                if max_eco_price is not None:
                    if i < POOL_SIZE // 2:
                        f.price = round(
                            random.uniform(max_eco_price * 0.40, max_eco_price * 0.95), 0
                        )
                    else:
                        f.price = round(
                            random.uniform(max_eco_price * 5.5, max_eco_price * 9.0), 0
                        )
                else:
                    spread = random.uniform(0.55, 1.65)
                    f.price = round(base_price * spread, 0)

                # Penalize the cheapest tier with extra duration / stops to push
                # it down in "best" composite sort — agent must apply "Cheapest"
                # sort explicitly to find lowest fare.
                if i < 3:  # candidate cheap rows
                    f.price = round(f.price * 0.78, 0)
                    f.duration_minutes = int(f.duration_minutes * random.uniform(1.15, 1.35))
                    f.stops = max(f.stops, random.choice([1, 1, 2]))

                # Recompute fare tiers from the new economy price
                f.price_premium = round(f.price * 1.55, 0)
                f.price_business = round(f.price * 3.1, 0)
                f.price_first = round(f.price * 5.0, 0)

                # Decouple CO2 from duration so lowest-CO2 isn't a duration proxy.
                # Airline efficiency factor + aircraft factor.
                airline_factor = random.uniform(0.78, 1.22)
                aircraft_factor = random.choice([0.85, 0.95, 1.0, 1.1, 1.18])
                f.co2_emissions_kg = max(40, int(f.duration_minutes * 0.85 * airline_factor * aircraft_factor))
                f.co2_vs_typical = random.choice([-25, -18, -12, -8, -3, 0, 4, 9, 14, 20])

                # Ensure first class price exists (already does, but be explicit)
                if needs_first and f.price_first <= 0:
                    f.price_first = round(f.price * 5, 0)

                f.is_best = False
                generated.append(f)
                db.session.add(f)
                flights_count += 1

            # Pick one balanced "Best" flight: NOT the cheapest, NOT the most
            # expensive, NOT the longest, NOT the most stops. Prefer a row with
            # 0 or 1 stops, mid-tier price, mid-tier duration.
            if generated:
                eligible = [g for g in generated if g.stops <= 1]
                if not eligible:
                    eligible = generated
                # Sort by composite distance from "ideal balanced" point
                if eligible:
                    prices = sorted(g.price for g in eligible)
                    durations = sorted(g.duration_minutes for g in eligible)
                    p_mid = prices[len(prices) // 2]
                    d_mid = durations[len(durations) // 2]
                    eligible.sort(key=lambda g: (
                        abs(g.price - p_mid) / max(1, p_mid)
                        + abs(g.duration_minutes - d_mid) / max(1, d_mid)
                        + g.stops * 0.15
                    ))
                    eligible[0].is_best = True
        # Commit per outer route so the ORM identity map / autoflush stays
        # small. Without this, 200k+ catalogue flights plus ~30k task-route
        # ORM inserts pile up in one transaction and the loop runs O(N) per
        # add. Per-route commit keeps the loop linear and rebuild stays at
        # ~30s instead of stalling for many minutes (observed in R4 push to
        # 200k+ flights).
        db.session.commit()

    db.session.commit()

    # ----------------------------------------------------------------
    # Round-trip pairing: for every WebVoyager round-trip route, add
    # reciprocal (return) inventory on the return date AND populate
    # Flight.return_date on the outbound row so detail pages can show
    # paired legs and "total round-trip duration" questions can be answered.
    # ----------------------------------------------------------------
    # (outbound_origin, outbound_dest, outbound_date, return_date)
    ROUND_TRIP_PAIRS = [
        # EDI <-> MAN: same-day round trip on Dec 28
        ('EDI', 'MAN', '2024-12-28', '2024-12-28'),
        # NYC (JFK) <-> London (LHR) round trips
        ('JFK', 'LHR', '2023-12-25', '2023-12-28'),
        ('JFK', 'LHR', '2023-12-26', '2023-12-29'),
        ('JFK', 'LHR', '2024-01-10', '2024-01-17'),
        # NYC (JFK) <-> Tokyo round trips
        ('JFK', 'HND', '2024-01-25', '2024-02-15'),
        ('JFK', 'HND', '2024-02-10', '2024-02-18'),
        ('JFK', 'NRT', '2024-02-12', '2024-02-26'),
        # SFO <-> Berlin round trip
        ('SFO', 'BER', '2024-03-05', '2024-03-12'),
        # PHX <-> MIA round trip
        ('PHX', 'MIA', '2023-12-25', '2023-12-28'),
        # DXB <-> FCO round trip
        ('DXB', 'FCO', '2024-03-01', '2024-03-08'),
        # MEX <-> FRA round trip
        ('MEX', 'FRA', '2024-03-05', '2024-03-15'),
        # BKK <-> MAD round trip
        ('BKK', 'MAD', '2024-02-26', '2024-02-28'),
        # EZE <-> PEK round trip
        ('EZE', 'PEK', '2024-02-28', '2024-03-03'),
        # GIG <-> LAX round trip
        ('GIG', 'LAX', '2024-03-15', '2024-03-22'),
        # ARN <-> YYZ round trip
        ('ARN', 'YYZ', '2024-03-03', '2024-03-10'),
        # OSL <-> DXB round trip
        ('OSL', 'DXB', '2024-03-08', '2024-03-15'),
    ]

    # Same sibling-airport expansion as TASK_ROUTES — keeps return-leg
    # inventory balanced when a city has multiple airports.
    _expanded_round_trip = []
    _seen_round = set()
    for out_o, out_d, out_date_str, ret_date_str in ROUND_TRIP_PAIRS:
        for o in [out_o] + CITY_SIBLINGS.get(out_o, []):
            for d in [out_d] + CITY_SIBLINGS.get(out_d, []):
                if o == d:
                    continue
                key = (o, d, out_date_str, ret_date_str)
                if key in _seen_round:
                    continue
                _seen_round.add(key)
                _expanded_round_trip.append((o, d, out_date_str, ret_date_str))
    ROUND_TRIP_PAIRS = _expanded_round_trip

    for out_o, out_d, out_date_str, ret_date_str in ROUND_TRIP_PAIRS:
        if out_o not in airport_by_iata or out_d not in airport_by_iata:
            continue
        out_date = date(int(out_date_str[:4]), int(out_date_str[5:7]), int(out_date_str[8:10]))
        ret_date = date(int(ret_date_str[:4]), int(ret_date_str[5:7]), int(ret_date_str[8:10]))

        # 1) Generate reciprocal return flights (dest -> origin) on the return date
        for i in range(6):
            rf = make_flight(out_d, out_o, ret_date)
            if rf is not None:
                db.session.add(rf)
                flights_count += 1

        # 2) Populate return_date on existing outbound rows so detail page can
        # display "round trip" label and join the return leg.
        out_o_id = airport_by_iata[out_o].id
        out_d_id = airport_by_iata[out_d].id
        outbound_rows = Flight.query.filter_by(
            origin_id=out_o_id,
            destination_id=out_d_id,
            departure_date=out_date,
        ).all()
        for row in outbound_rows:
            row.return_date = ret_date

    db.session.commit()

    # ----------------------------------------------------------------
    # Populate Flight.stop_cities for every row where stops > 0.
    # Pick a plausible layover IATA from a pool of hub airports.
    # ----------------------------------------------------------------
    # Pick a plausible layover IATA from a pool of hub airports.
    # ----------------------------------------------------------------
    # Populating stop_cities via ORM iteration with relationship lookups was
    # an N+1 query nightmare (10k+ flights × 1 query each for f.origin.iata).
    # Drop to a single CASE-based UPDATE: deterministic hub picked from
    # flight.id so the displayed layover is stable. This finishes in <1 sec
    # vs ~minutes for the ORM version.
    HUBS = ['LHR', 'CDG', 'AMS', 'FRA', 'DXB', 'DOH', 'IST', 'ICN',
            'HKG', 'SIN', 'BKK', 'NRT', 'ATL', 'ORD', 'DFW', 'LAX',
            'JFK', 'MIA', 'YYZ', 'MEX']
    case_when_1 = " ".join(
        f"WHEN (id % {len(HUBS)}) = {i} THEN '{h}'" for i, h in enumerate(HUBS)
    )
    case_when_2 = " ".join(
        f"WHEN (id % {len(HUBS)}) = {i} THEN '{HUBS[i]},{HUBS[(i + 7) % len(HUBS)]}'"
        for i in range(len(HUBS))
    )
    db.session.execute(text(f"""
        UPDATE flight
           SET stop_cities = CASE
                {case_when_1}
                ELSE 'LHR'
           END
         WHERE stops = 1 AND (stop_cities IS NULL OR stop_cities = '')
    """))
    db.session.execute(text(f"""
        UPDATE flight
           SET stop_cities = CASE
                {case_when_2}
                ELSE 'LHR,CDG'
           END
         WHERE stops >= 2 AND (stop_cities IS NULL OR stop_cities = '')
    """))
    db.session.commit()

    # Mark best / cheapest / fastest. With 250k+ flights, partitioning the
    # whole table by (route, date) takes minutes. Restrict the work to task
    # routes (TASK_ROUTES + reciprocal returns) — they're what the benchmark
    # tests. Catalog routes get ordered at query time via the composite
    # "Best" score in the search route; they don't need stored flags.
    db.session.execute(text(
        "UPDATE flight SET is_best=0, is_cheapest=0, is_fastest=0"
    ))
    db.session.commit()

    task_routes_set = set()
    for o, d, *_ in TASK_ROUTES:
        if o in airport_by_iata and d in airport_by_iata:
            task_routes_set.add((airport_by_iata[o].id, airport_by_iata[d].id))
    for o, d, _, _ in ROUND_TRIP_PAIRS:
        if d in airport_by_iata and o in airport_by_iata:
            task_routes_set.add((airport_by_iata[d].id, airport_by_iata[o].id))

    if task_routes_set:
        db.session.execute(text(
            "CREATE TEMP TABLE _task_routes (origin_id INT, destination_id INT)"
        ))
        db.session.execute(
            text("INSERT INTO _task_routes (origin_id, destination_id) VALUES (:o, :d)"),
            [{"o": o, "d": d} for (o, d) in task_routes_set],
        )
        db.session.commit()

        for col, order in [('is_cheapest', 'price ASC'),
                           ('is_fastest', 'duration_minutes ASC')]:
            db.session.execute(text(f"""
                WITH ranked AS (
                    SELECT f.id,
                           ROW_NUMBER() OVER (
                               PARTITION BY f.origin_id, f.destination_id, f.departure_date
                               ORDER BY {order}, f.id ASC
                           ) AS rn
                      FROM flight f
                      JOIN _task_routes t
                        ON f.origin_id = t.origin_id
                       AND f.destination_id = t.destination_id
                )
                UPDATE flight SET {col} = 1
                 WHERE id IN (SELECT id FROM ranked WHERE rn = 1)
            """))

        db.session.execute(text("""
            WITH grouped AS (
                SELECT f.origin_id, f.destination_id, f.departure_date,
                       AVG(f.price)            AS avg_p,
                       AVG(f.duration_minutes) AS avg_d
                  FROM flight f
                  JOIN _task_routes t
                    ON f.origin_id = t.origin_id
                   AND f.destination_id = t.destination_id
                 GROUP BY f.origin_id, f.destination_id, f.departure_date
            ),
            scored AS (
                SELECT f.id, f.origin_id, f.destination_id, f.departure_date,
                       f.is_cheapest, f.is_fastest, f.stops,
                       ABS(f.price - g.avg_p) / NULLIF(g.avg_p, 0)
                       + ABS(f.duration_minutes - g.avg_d) / NULLIF(g.avg_d, 0)
                       + f.stops * 0.15 AS score
                  FROM flight f
                  JOIN grouped g
                    ON f.origin_id = g.origin_id
                   AND f.destination_id = g.destination_id
                   AND f.departure_date = g.departure_date
            ),
            ranked AS (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY origin_id, destination_id, departure_date
                           ORDER BY (CASE WHEN is_cheapest=0 AND is_fastest=0 AND stops<=1 THEN 0
                                          WHEN is_cheapest=0 THEN 1
                                          ELSE 2 END),
                                    score ASC,
                                    id ASC
                       ) AS rn
                  FROM scored
            )
            UPDATE flight SET is_best = 1
             WHERE id IN (SELECT id FROM ranked WHERE rn = 1)
        """))
        db.session.execute(text("DROP TABLE _task_routes"))
    db.session.commit()

    print(f"Seeded {Airport.query.count()} airports and {Flight.query.count()} flights.")
