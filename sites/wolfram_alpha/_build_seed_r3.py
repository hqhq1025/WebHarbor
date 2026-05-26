#!/usr/bin/env python3
"""R3 polish: appends ON TOP of R2 seed db (instance_seed/wolfram_alpha.db).

R2 baseline (md5 86654d8...):
  categories 4, subcategories 60, topics 116, computation_results 1314,
  notebook_entries 204, topic_feedback 67.

R3 targets:
  topics       200+  (+90)
  comp_results 2800+ (+1500)
  notebook_ent 500+  (+300)
  topic_feedb  100+  (+50)

Deterministic — no datetime.now(), no random. Run twice = same md5.
"""
from __future__ import annotations
import json, sqlite3, shutil, os, math
from datetime import datetime, timedelta

SRC = 'instance_seed/wolfram_alpha.db'
DST = 'instance/wolfram_alpha.db'

REF = datetime(2026, 5, 1, 12, 0, 0)
def ts(off_hours: int = 0) -> str:
    return (REF + timedelta(hours=off_hours)).isoformat(sep=' ')

def J(x): return json.dumps(x)

# ---------------------------------------------------------------------------
# (1) New topics — 90 — all NEW slugs (verified not in R1+R2 set)
# ---------------------------------------------------------------------------
# Format: (cat_slug, sub_slug_or_None, name, slug, desc, image, feat, new, examples_json)
NEW_TOPICS = [
    # --- Finance / Markets / Money (10) ---
    ("society-and-culture", "finance", "Stock Markets", "stock-markets",
     "Major stock exchanges, indices (S&P 500, Dow, Nasdaq), and equity statistics.",
     "finance.png", True, True, J([
        {"query":"AAPL stock price","type":"stock","result":"Apple Inc. (AAPL) — last close $187.32 (NASDAQ)"},
        {"query":"S&P 500 components","type":"index","result":"500 large-cap US equities (≈80% US market cap)"},
        {"query":"Dow Jones constituents","type":"index","result":"30 blue-chip US stocks; price-weighted"},
     ])),
    ("society-and-culture", "finance", "Dividend Yields", "dividends",
     "Dividend yields, payout ratios, and dividend-growth metrics.",
     "finance.png", False, True, J([
        {"query":"dividend yield AAPL","type":"yield","result":"≈ 0.51% trailing twelve months"},
        {"query":"highest dividend Dow stocks","type":"yield","result":"Verizon, Dow Inc., Chevron — 4-7%"},
        {"query":"average S&P 500 yield","type":"yield","result":"≈ 1.5% (historical median 2%)"},
     ])),
    ("society-and-culture", "finance", "Bond Markets", "bonds",
     "Treasury yields, corporate bonds, yield curves, and bond pricing.",
     "finance.png", False, False, J([
        {"query":"10 year Treasury yield","type":"yield","result":"≈ 4.25% (recent)"},
        {"query":"yield curve","type":"curve","result":"Plot of yields vs maturity; inverted curve often precedes recession"},
        {"query":"bond price coupon 5% yield 6%","type":"price","result":"Trades below par (discount bond)"},
     ])),
    ("society-and-culture", "finance", "ETFs & Mutual Funds", "etfs-funds",
     "Index funds, ETFs, expense ratios, and fund-flow trends.",
     "finance.png", False, True, J([
        {"query":"SPY expense ratio","type":"etf","result":"0.0945% (SPDR S&P 500 ETF)"},
        {"query":"largest ETF by AUM","type":"etf","result":"VOO / SPY / IVV — each tracking S&P 500"},
        {"query":"index fund vs active fund","type":"compare","result":"Index funds typically beat 80%+ of active funds over 15 years"},
     ])),
    ("society-and-culture", "finance", "Options Pricing", "options",
     "Black-Scholes pricing, Greeks, calls and puts, and option strategies.",
     "finance.png", False, False, J([
        {"query":"call option price Black-Scholes","type":"option","result":"C = S N(d1) − K e^(−rT) N(d2)"},
        {"query":"delta of at-the-money call","type":"greek","result":"≈ 0.5"},
        {"query":"put-call parity","type":"identity","result":"C − P = S − K e^(−rT)"},
     ])),
    ("society-and-culture", "finance", "Forex / Currencies", "forex",
     "Currency pairs, exchange rates, and FX-market mechanics.",
     "finance.png", False, False, J([
        {"query":"USD to JPY rate","type":"rate","result":"≈ 150.2 JPY per 1 USD"},
        {"query":"EUR to USD rate","type":"rate","result":"≈ 1.085 USD per 1 EUR"},
        {"query":"largest forex pair","type":"market","result":"EUR/USD — ~24% of daily FX volume"},
     ])),
    ("society-and-culture", "finance", "Inflation & CPI", "inflation",
     "Consumer Price Index history, real vs nominal values, and currency debasement.",
     "finance.png", False, False, J([
        {"query":"US inflation 2023","type":"cpi","result":"4.1% annual (CPI-U all items)"},
        {"query":"hyperinflation Weimar","type":"history","result":"Up to 29,500% monthly inflation, 1923"},
        {"query":"real return 7% nominal 3% inflation","type":"real","result":"≈ 3.88% real return"},
     ])),
    ("society-and-culture", "finance", "Taxes (US)", "taxes-us",
     "Federal income tax brackets, capital gains, and standard deductions.",
     "finance.png", False, False, J([
        {"query":"US top marginal tax 2024","type":"bracket","result":"37% (income above ~$609k single)"},
        {"query":"long-term capital gains rate","type":"rate","result":"0% / 15% / 20% depending on income"},
        {"query":"standard deduction single 2024","type":"deduction","result":"$14,600"},
     ])),
    ("society-and-culture", "finance", "Insurance Math", "insurance-math",
     "Life expectancy, actuarial present values, and premium pricing.",
     "finance.png", False, False, J([
        {"query":"actuarial present value annuity","type":"actuarial","result":"a_x = Σ v^k · _kp_x"},
        {"query":"life insurance term vs whole","type":"compare","result":"Term: pure protection. Whole: protection + cash value"},
        {"query":"premium loading factor","type":"pricing","result":"Premium = expected loss × (1 + loading)"},
     ])),
    ("society-and-culture", "finance", "Real Estate Math", "real-estate-math",
     "Cap rates, cash-on-cash returns, and property valuation metrics.",
     "finance.png", False, False, J([
        {"query":"cap rate NOI $30k value $500k","type":"cap","result":"Cap rate = 6%"},
        {"query":"cash-on-cash return","type":"return","result":"Annual pre-tax cash flow ÷ total cash invested"},
        {"query":"GRM property price $300k rent $30k","type":"grm","result":"Gross rent multiplier = 10"},
     ])),

    # --- Sports stats (10) ---
    ("society-and-culture", "sports-society", "Olympic Records", "olympics-records",
     "Olympic gold medals, world records, and athletic performance data.",
     "people.png", True, True, J([
        {"query":"100m world record","type":"record","result":"Usain Bolt — 9.58 s (Berlin 2009)"},
        {"query":"marathon world record","type":"record","result":"Kelvin Kiptum — 2:00:35 (Chicago 2023)"},
        {"query":"most Olympic golds","type":"record","result":"Michael Phelps — 23 golds (28 total medals)"},
     ])),
    ("society-and-culture", "sports-society", "World Cup", "world-cup",
     "FIFA World Cup champions, top scorers, and tournament records.",
     "people.png", False, True, J([
        {"query":"most World Cup wins","type":"team","result":"Brazil — 5 titles (1958, 1962, 1970, 1994, 2002)"},
        {"query":"top World Cup scorer","type":"player","result":"Miroslav Klose — 16 goals (Germany, 4 tournaments)"},
        {"query":"2022 World Cup champion","type":"event","result":"Argentina — defeated France in final (penalties)"},
     ])),
    ("society-and-culture", "sports-society", "NBA Stats", "nba-stats",
     "NBA scoring records, championships, and individual performance.",
     "people.png", False, False, J([
        {"query":"NBA all-time scoring leader","type":"record","result":"LeBron James — 40,000+ points (active)"},
        {"query":"most NBA championships","type":"team","result":"Celtics — 18; Lakers — 17"},
        {"query":"highest scoring game NBA","type":"record","result":"Wilt Chamberlain — 100 points (1962)"},
     ])),
    ("society-and-culture", "sports-society", "NFL Stats", "nfl-stats",
     "NFL super bowl champions, MVPs, and franchise records.",
     "people.png", False, False, J([
        {"query":"most Super Bowl wins","type":"team","result":"Patriots and Steelers — 6 each"},
        {"query":"most Super Bowl MVPs","type":"player","result":"Tom Brady — 5 SB MVPs (7 SB wins)"},
        {"query":"single-season passing record","type":"record","result":"Peyton Manning — 5,477 yards (2013)"},
     ])),
    ("society-and-culture", "sports-society", "MLB Stats", "mlb-stats",
     "Major League Baseball career records, World Series, and Cy Young awards.",
     "people.png", False, False, J([
        {"query":"all-time home run leader","type":"record","result":"Barry Bonds — 762 career HRs"},
        {"query":"most MLB championships","type":"team","result":"New York Yankees — 27 World Series titles"},
        {"query":"perfect game pitches","type":"record","result":"Don Larsen — 1956 WS Game 5 (only WS perfect game)"},
     ])),
    ("society-and-culture", "sports-society", "Tennis Records", "tennis-records",
     "Grand Slam titles, ATP/WTA rankings, and tennis match records.",
     "people.png", False, False, J([
        {"query":"most Grand Slams men","type":"record","result":"Djokovic (24), Nadal (22), Federer (20)"},
        {"query":"most Grand Slams women","type":"record","result":"Margaret Court — 24; Serena Williams — 23"},
        {"query":"longest tennis match","type":"record","result":"Isner vs Mahut — 11h 5m, Wimbledon 2010"},
     ])),
    ("society-and-culture", "sports-society", "Marathon Records", "marathon-records",
     "Marathon world records, major-marathon courses, and pacing data.",
     "people.png", False, False, J([
        {"query":"men marathon world record","type":"record","result":"Kelvin Kiptum — 2:00:35 (Chicago 2023)"},
        {"query":"women marathon world record","type":"record","result":"Tigist Assefa — 2:11:53 (Berlin 2023)"},
        {"query":"Boston Marathon distance","type":"event","result":"42.195 km (26.219 miles); since 1897"},
     ])),
    ("society-and-culture", "sports-society", "Cricket Records", "cricket-records",
     "Cricket centuries, World Cups, and Test/ODI/T20 records.",
     "people.png", False, False, J([
        {"query":"most ODI runs","type":"record","result":"Sachin Tendulkar — 18,426 runs"},
        {"query":"highest Test score","type":"record","result":"Brian Lara — 400* vs England 2004"},
        {"query":"most Cricket World Cups","type":"team","result":"Australia — 6 (1987, 1999, 2003, 2007, 2015, 2023)"},
     ])),
    ("society-and-culture", "sports-society", "Formula 1", "formula-1",
     "Formula 1 champions, lap records, and circuit data.",
     "people.png", False, False, J([
        {"query":"most F1 championships","type":"record","result":"Schumacher and Hamilton — 7 each"},
        {"query":"fastest F1 lap Monza","type":"record","result":"Lewis Hamilton — 1:18.887 (2020 qualifying)"},
        {"query":"F1 race weekend format","type":"format","result":"Practice, qualifying, race; ~305 km race distance"},
     ])),
    ("society-and-culture", "sports-society", "Chess Tournaments", "chess-tournaments",
     "World Chess Championships, top GM tournaments, and chess records.",
     "people.png", False, False, J([
        {"query":"current world chess champion","type":"title","result":"Ding Liren (since April 2023)"},
        {"query":"highest rated player ever","type":"rating","result":"Magnus Carlsen — 2882 FIDE (May 2014)"},
        {"query":"longest chess match","type":"record","result":"Nikolić vs Arsović — 269 moves, 1989"},
     ])),

    # --- Medical / drugs / health (10) ---
    ("everyday-life", "personal-health", "Common Medications", "medications",
     "Brand and generic names, dosing, and indications for top US drugs.",
     "personal-health.png", True, True, J([
        {"query":"acetaminophen max daily","type":"drug","result":"4 g/day adult; toxicity above 10 g acute"},
        {"query":"ibuprofen typical dose","type":"drug","result":"200–400 mg every 6 h; max 1200 mg OTC"},
        {"query":"aspirin low-dose cardiac","type":"drug","result":"81 mg daily for cardiovascular prevention"},
     ])),
    ("everyday-life", "personal-health", "Vaccines", "vaccines",
     "Recommended vaccines, efficacy rates, and schedules.",
     "personal-health.png", False, False, J([
        {"query":"MMR vaccine efficacy","type":"vaccine","result":"≈ 97% measles, 88% mumps, 97% rubella (2 doses)"},
        {"query":"flu vaccine efficacy","type":"vaccine","result":"40–60% in well-matched years"},
        {"query":"COVID-19 mRNA efficacy original","type":"vaccine","result":"≈ 95% Pfizer (BNT162b2), 94% Moderna"},
     ])),
    ("everyday-life", "personal-health", "Vitamins (Detail)", "vitamins-detail",
     "RDA, food sources, and deficiency symptoms for major vitamins.",
     "personal-health.png", False, False, J([
        {"query":"vitamin D RDA adult","type":"rda","result":"600 IU (15 µg)/day; 800 IU age 70+"},
        {"query":"vitamin B12 RDA","type":"rda","result":"2.4 µg/day adult"},
        {"query":"vitamin K function","type":"function","result":"Blood clotting; bone metabolism"},
     ])),
    ("everyday-life", "personal-health", "Antibiotics", "antibiotics",
     "Major antibiotic classes, mechanisms, and resistance issues.",
     "personal-health.png", False, False, J([
        {"query":"penicillin mechanism","type":"mechanism","result":"Inhibits bacterial cell wall (transpeptidase)"},
        {"query":"broad spectrum antibiotic","type":"drug","result":"Amoxicillin, doxycycline, ciprofloxacin"},
        {"query":"antibiotic resistance MRSA","type":"resistance","result":"Methicillin-resistant Staphylococcus aureus"},
     ])),
    ("everyday-life", "personal-health", "Hormones", "hormones",
     "Endocrine system hormones, normal ranges, and biological roles.",
     "personal-health.png", False, False, J([
        {"query":"insulin function","type":"hormone","result":"Lowers blood glucose; from pancreas β-cells"},
        {"query":"cortisol normal range","type":"hormone","result":"Morning 6–23 µg/dL; evening lower"},
        {"query":"TSH normal range","type":"hormone","result":"0.4–4.0 mIU/L (varies by lab)"},
     ])),
    ("everyday-life", "personal-health", "Blood Tests", "blood-tests",
     "Common lab values, normal ranges, and clinical significance.",
     "personal-health.png", False, False, J([
        {"query":"fasting glucose normal","type":"lab","result":"70–99 mg/dL (3.9–5.5 mmol/L)"},
        {"query":"LDL cholesterol target","type":"lab","result":"< 100 mg/dL desirable; < 70 high-risk"},
        {"query":"hemoglobin normal adult male","type":"lab","result":"13.5–17.5 g/dL"},
     ])),
    ("everyday-life", "personal-health", "Pediatric Health", "pediatrics",
     "Growth percentiles, milestones, and pediatric dosing.",
     "personal-health.png", False, False, J([
        {"query":"average newborn weight","type":"reference","result":"≈ 3.3 kg (7.3 lb); 2.5–4.5 kg normal range"},
        {"query":"baby first word age","type":"milestone","result":"Around 12 months (range 9–14)"},
        {"query":"infant dosing acetaminophen","type":"dose","result":"10–15 mg/kg every 4–6 h, max 5 doses/day"},
     ])),
    ("everyday-life", "personal-health", "Mental Health", "mental-health",
     "Diagnostic criteria, prevalence, and treatment statistics.",
     "personal-health.png", False, False, J([
        {"query":"depression prevalence US","type":"prevalence","result":"≈ 8.4% adults annually (NIMH)"},
        {"query":"anxiety lifetime risk","type":"prevalence","result":"≈ 31% adults at some point in life"},
        {"query":"SSRI typical onset","type":"treatment","result":"4–6 weeks for full antidepressant effect"},
     ])),
    ("everyday-life", "personal-health", "First Aid", "first-aid",
     "CPR ratios, choking response, and bleeding control.",
     "personal-health.png", False, False, J([
        {"query":"CPR compression rate","type":"emergency","result":"100–120 compressions/min, 5–6 cm depth"},
        {"query":"Heimlich abdominal thrusts","type":"emergency","result":"5 back blows + 5 abdominal thrusts cycle"},
        {"query":"recovery position","type":"emergency","result":"Lateral, head tilted to keep airway open"},
     ])),
    ("everyday-life", "personal-health", "Pregnancy Math", "pregnancy",
     "Gestational age, due dates, and pregnancy-related calculations.",
     "personal-health.png", False, False, J([
        {"query":"pregnancy weeks duration","type":"duration","result":"40 weeks from LMP; 38 from conception"},
        {"query":"first trimester end","type":"timeline","result":"End of week 13"},
        {"query":"folic acid pregnancy dose","type":"supplement","result":"400–800 µg/day; prevents neural tube defects"},
     ])),

    # --- Legal / IP / Government (8) ---
    ("society-and-culture", "politics", "US Law Basics", "us-law",
     "US legal system structure, courts, and key constitutional doctrines.",
     "people.png", False, False, J([
        {"query":"US Supreme Court justices","type":"court","result":"9 justices; lifetime appointments by President"},
        {"query":"Bill of Rights","type":"doc","result":"First 10 amendments to US Constitution (1791)"},
        {"query":"Miranda warning origin","type":"case","result":"Miranda v. Arizona (1966)"},
     ])),
    ("society-and-culture", "politics", "Contract Law", "contract-law",
     "Offer, acceptance, consideration, and contract remedies.",
     "people.png", False, False, J([
        {"query":"elements of a contract","type":"doctrine","result":"Offer, acceptance, consideration, capacity, legality"},
        {"query":"statute of frauds","type":"doctrine","result":"Some contracts must be in writing (real estate, >1yr)"},
        {"query":"liquidated damages","type":"doctrine","result":"Pre-agreed damages; enforceable if reasonable estimate"},
     ])),
    ("society-and-culture", "politics", "Copyright Law", "copyright",
     "Copyright duration, fair use, and the public domain.",
     "people.png", False, False, J([
        {"query":"US copyright duration","type":"term","result":"Life + 70 years (individual); 95 years (corporate)"},
        {"query":"fair use four factors","type":"doctrine","result":"Purpose, nature, amount, market effect"},
        {"query":"public domain entry year","type":"calendar","result":"Works pre-1929 are in US public domain (2024)"},
     ])),
    ("society-and-culture", "politics", "Patent Law", "patents",
     "Patent types, term lengths, and patent-application requirements.",
     "people.png", False, False, J([
        {"query":"US utility patent term","type":"term","result":"20 years from filing date"},
        {"query":"design patent term","type":"term","result":"15 years from grant (US, since May 2015)"},
        {"query":"patentability requirements","type":"doctrine","result":"Novelty, non-obviousness, utility, subject matter"},
     ])),
    ("society-and-culture", "politics", "Trademark Law", "trademarks",
     "Trademark classes, the Lanham Act, and trademark duration.",
     "people.png", False, False, J([
        {"query":"US trademark renewal","type":"term","result":"Initial 10 years; renewable indefinitely"},
        {"query":"trademark vs trade dress","type":"compare","result":"Trademark: names/logos. Trade dress: overall product look"},
        {"query":"registered trademark symbol","type":"symbol","result":"® (registered); ™ (unregistered)"},
     ])),
    ("society-and-culture", "politics", "Criminal Law", "criminal-law",
     "Felonies, misdemeanors, and elements of criminal liability.",
     "people.png", False, False, J([
        {"query":"mens rea","type":"doctrine","result":"Guilty mind; required mental state for crime"},
        {"query":"actus reus","type":"doctrine","result":"Guilty act; physical element of crime"},
        {"query":"beyond reasonable doubt","type":"standard","result":"Highest evidentiary standard; criminal cases"},
     ])),
    ("society-and-culture", "politics", "Constitutional Amendments", "amendments",
     "US Constitutional amendments and their dates of ratification.",
     "people.png", False, False, J([
        {"query":"13th Amendment","type":"amendment","result":"Abolished slavery (1865)"},
        {"query":"19th Amendment","type":"amendment","result":"Women's right to vote (1920)"},
        {"query":"22nd Amendment","type":"amendment","result":"Presidential term limits (1951) — max 2 terms"},
     ])),
    ("society-and-culture", "politics", "International Law", "international-law",
     "Treaties, UN Charter, Geneva Conventions, and ICJ proceedings.",
     "people.png", False, False, J([
        {"query":"Geneva Conventions","type":"treaty","result":"4 treaties (1864–1949); rules of war + civilians"},
        {"query":"UN founding year","type":"event","result":"1945; current 193 member states"},
        {"query":"ICJ location","type":"court","result":"The Hague, Netherlands (Peace Palace)"},
     ])),

    # --- Music theory (6) ---
    ("everyday-life", "music-audio", "Musical Scales", "musical-scales",
     "Major and minor scales, modes, and pentatonic systems.",
     "household-science.png", False, True, J([
        {"query":"C major scale notes","type":"scale","result":"C D E F G A B"},
        {"query":"A minor natural scale","type":"scale","result":"A B C D E F G"},
        {"query":"D Dorian mode","type":"mode","result":"D E F G A B C — minor with raised 6th"},
     ])),
    ("everyday-life", "music-audio", "Chord Progressions", "chord-progressions",
     "Common chord progressions, tension-resolution, and key signatures.",
     "household-science.png", False, False, J([
        {"query":"I-IV-V-I progression","type":"progression","result":"In C: C–F–G–C; classic resolution"},
        {"query":"ii-V-I jazz","type":"progression","result":"In C: Dm7–G7–Cmaj7; foundational jazz turn"},
        {"query":"12-bar blues","type":"progression","result":"I–I–I–I–IV–IV–I–I–V–IV–I–V"},
     ])),
    ("everyday-life", "music-audio", "Musical Intervals", "intervals",
     "Half-steps, perfect/major/minor intervals, and frequency ratios.",
     "household-science.png", False, False, J([
        {"query":"perfect fifth ratio","type":"interval","result":"3:2 frequency ratio; 7 semitones"},
        {"query":"octave ratio","type":"interval","result":"2:1; 12 semitones"},
        {"query":"major third semitones","type":"interval","result":"4 semitones (e.g., C to E)"},
     ])),
    ("everyday-life", "music-audio", "Key Signatures", "key-signatures",
     "Sharps, flats, the circle of fifths, and key relationships.",
     "household-science.png", False, False, J([
        {"query":"G major key signature","type":"key","result":"1 sharp: F#"},
        {"query":"F major key signature","type":"key","result":"1 flat: Bb"},
        {"query":"order of sharps","type":"key","result":"F C G D A E B"},
     ])),
    ("everyday-life", "music-audio", "Tempo & Rhythm", "tempo",
     "BPM ranges, time signatures, and common rhythmic patterns.",
     "household-science.png", False, False, J([
        {"query":"andante tempo","type":"tempo","result":"76–108 BPM (walking pace)"},
        {"query":"allegro tempo","type":"tempo","result":"120–168 BPM"},
        {"query":"common time signature","type":"meter","result":"4/4 (most popular music)"},
     ])),
    ("everyday-life", "music-audio", "Orchestral Instruments", "orchestral-instruments",
     "Instrument ranges, families, and seating arrangements.",
     "household-science.png", False, False, J([
        {"query":"violin range","type":"range","result":"G3 to E7 (open G to high notes)"},
        {"query":"piccolo range","type":"range","result":"D5 to C8; highest woodwind"},
        {"query":"orchestra string sections","type":"section","result":"Violin I & II, viola, cello, contrabass"},
     ])),

    # --- Linguistics (6) ---
    ("society-and-culture", "linguistics", "Phonetics & IPA", "phonetics-ipa",
     "International Phonetic Alphabet, consonants, vowels, and articulation.",
     "linguistics.png", False, False, J([
        {"query":"IPA voiceless dental fricative","type":"ipa","result":"θ (as in 'thin')"},
        {"query":"IPA schwa","type":"ipa","result":"ə (unstressed central vowel)"},
        {"query":"voiced bilabial stop","type":"ipa","result":"[b]"},
     ])),
    ("society-and-culture", "linguistics", "Language Families", "language-families",
     "Indo-European, Sino-Tibetan, Afroasiatic, and other major language families.",
     "linguistics.png", False, False, J([
        {"query":"largest language family","type":"family","result":"Indo-European — ~3.2 billion speakers"},
        {"query":"Romance languages","type":"family","result":"Spanish, French, Italian, Portuguese, Romanian, Catalan"},
        {"query":"Sino-Tibetan family","type":"family","result":"Chinese, Tibetan, Burmese; ~1.5 B speakers"},
     ])),
    ("society-and-culture", "linguistics", "Grammar & Syntax", "grammar-syntax",
     "Parts of speech, sentence structure, and grammatical features.",
     "linguistics.png", False, False, J([
        {"query":"SVO word order languages","type":"syntax","result":"English, Mandarin, French, Russian"},
        {"query":"SOV word order","type":"syntax","result":"Japanese, Korean, Turkish, Hindi"},
        {"query":"declensions in Latin","type":"morphology","result":"5 noun declensions"},
     ])),
    ("society-and-culture", "linguistics", "Writing Systems", "writing-systems",
     "Alphabets, abugidas, abjads, syllabaries, and logographic systems.",
     "linguistics.png", False, False, J([
        {"query":"alphabet vs abjad","type":"system","result":"Alphabet: vowels + consonants. Abjad: consonants only (Arabic)"},
        {"query":"Chinese characters total","type":"system","result":"≈ 50,000+ characters; ~3,500 for literacy"},
        {"query":"oldest writing system","type":"history","result":"Sumerian cuneiform — c. 3200 BC"},
     ])),
    ("society-and-culture", "linguistics", "Word Frequencies", "word-frequencies",
     "Most common English words and Zipf's law in language.",
     "linguistics.png", False, False, J([
        {"query":"most common English word","type":"frequency","result":"the (≈ 7% of all tokens)"},
        {"query":"Zipf's law","type":"law","result":"f(n) ∝ 1/n — rank-frequency relationship"},
        {"query":"COCA corpus size","type":"corpus","result":"≈ 1 billion words (Corpus of Contemporary American English)"},
     ])),
    ("society-and-culture", "linguistics", "Translation Pairs", "translation-pairs",
     "Common phrases across languages for greetings, food, and numbers.",
     "linguistics.png", False, False, J([
        {"query":"hello in Spanish","type":"phrase","result":"Hola"},
        {"query":"thank you in Japanese","type":"phrase","result":"ありがとう (arigatō)"},
        {"query":"one in Mandarin","type":"number","result":"一 (yī)"},
     ])),

    # --- Engineering details (8) ---
    ("science-and-technology", "engineering-detail", "Electrical Engineering", "electrical-engineering",
     "Circuits, signals, Ohm's law, AC power, and electronic components.",
     "physics.png", False, True, J([
        {"query":"Kirchhoff's voltage law","type":"law","result":"Sum of voltage drops around any closed loop = 0"},
        {"query":"RMS voltage 120V AC","type":"signal","result":"170 V peak; 339 V peak-to-peak"},
        {"query":"capacitor energy 100uF 12V","type":"energy","result":"E = ½ C V² = 7.2 mJ"},
     ])),
    ("science-and-technology", "engineering-detail", "Mechanical Engineering", "mechanical-engineering",
     "Statics, dynamics, stress, strain, and machine elements.",
     "physics.png", False, False, J([
        {"query":"stress beam load 1000N area 0.01m^2","type":"stress","result":"σ = 100 kPa"},
        {"query":"Young's modulus steel","type":"property","result":"≈ 200 GPa"},
        {"query":"factor of safety civil","type":"design","result":"Typically 1.5–4 (steel beams: ~1.5–2)"},
     ])),
    ("science-and-technology", "engineering-detail", "Civil Engineering Detail", "civil-engineering-detail",
     "Structural analysis, concrete strength, and load-bearing calculations.",
     "physics.png", False, False, J([
        {"query":"concrete compressive strength","type":"material","result":"Typical 20–40 MPa (3-6 ksi)"},
        {"query":"steel yield strength A36","type":"material","result":"250 MPa (36 ksi)"},
        {"query":"dead load office floor","type":"load","result":"Self-weight, typically 2.4–3.6 kPa"},
     ])),
    ("science-and-technology", "engineering-detail", "Aerospace Engineering", "aerospace",
     "Lift, drag, thrust, orbital mechanics, and aircraft design.",
     "physics.png", False, False, J([
        {"query":"lift coefficient airfoil","type":"aero","result":"CL ≈ 0.5–1.5 cruise; up to ~2.5 high-lift"},
        {"query":"orbital velocity LEO","type":"orbit","result":"≈ 7.8 km/s at 400 km altitude"},
        {"query":"specific impulse rocket","type":"rocket","result":"Chemical: 250–450 s; Ion: 1500–5000 s"},
     ])),
    ("science-and-technology", "engineering-detail", "Chemical Engineering", "chemical-engineering",
     "Mass balance, energy balance, distillation, and reaction kinetics.",
     "physics.png", False, False, J([
        {"query":"ideal gas law application","type":"thermo","result":"PV = nRT; R = 8.314 J/(mol·K)"},
        {"query":"distillation reflux ratio","type":"process","result":"R = L/D; higher R → better separation, more energy"},
        {"query":"Arrhenius equation","type":"kinetics","result":"k = A exp(−Ea/RT)"},
     ])),
    ("science-and-technology", "engineering-detail", "Heat Transfer", "heat-transfer",
     "Conduction, convection, radiation, and thermal resistance.",
     "physics.png", False, False, J([
        {"query":"Fourier's law","type":"law","result":"q = −k ∇T (conduction)"},
        {"query":"Stefan-Boltzmann law","type":"law","result":"q = σ T⁴ (radiation; σ = 5.67×10⁻⁸ W/m²K⁴)"},
        {"query":"convective heat transfer coefficient air","type":"value","result":"5–25 W/(m²·K) natural; 25–250 forced"},
     ])),
    ("science-and-technology", "engineering-detail", "Fluid Mechanics", "fluid-mechanics",
     "Bernoulli, Reynolds number, pipe flow, and viscosity.",
     "physics.png", False, False, J([
        {"query":"Bernoulli equation","type":"equation","result":"P + ½ρv² + ρgh = const"},
        {"query":"Reynolds number transition","type":"value","result":"Re ≈ 2300 (pipe flow); turbulent above ~4000"},
        {"query":"water viscosity 20C","type":"property","result":"≈ 1.002 × 10⁻³ Pa·s"},
     ])),
    ("science-and-technology", "engineering-detail", "Control Systems", "control-systems",
     "PID controllers, transfer functions, and stability analysis.",
     "physics.png", False, False, J([
        {"query":"PID controller","type":"controller","result":"u(t) = Kp·e + Ki·∫e dt + Kd·de/dt"},
        {"query":"transfer function first order","type":"system","result":"H(s) = K/(τs + 1)"},
        {"query":"Routh-Hurwitz stability","type":"criterion","result":"All Routh array first column entries > 0 ⇒ stable"},
     ])),

    # --- Materials science (5) ---
    ("science-and-technology", "materials-science", "Alloys", "alloys",
     "Common alloys: steel, brass, bronze, aluminum alloys, and their properties.",
     "physics.png", False, False, J([
        {"query":"composition brass","type":"alloy","result":"≈ 70% Cu, 30% Zn (cartridge brass C26000)"},
        {"query":"stainless steel 304","type":"alloy","result":"18% Cr, 8% Ni; austenitic, corrosion resistant"},
        {"query":"aluminum 6061","type":"alloy","result":"Al + Mg, Si; structural use, weldable"},
     ])),
    ("science-and-technology", "materials-science", "Polymers", "polymers",
     "Common polymers, glass-transition temperatures, and applications.",
     "physics.png", False, False, J([
        {"query":"polyethylene Tg","type":"polymer","result":"HDPE: −125°C; LDPE: −110°C"},
        {"query":"PTFE properties","type":"polymer","result":"Non-stick, melts ~327°C, very chemically inert"},
        {"query":"density polystyrene","type":"polymer","result":"≈ 1.04–1.06 g/cm³"},
     ])),
    ("science-and-technology", "materials-science", "Ceramics", "ceramics",
     "Ceramic materials: oxides, carbides, nitrides, and their properties.",
     "physics.png", False, False, J([
        {"query":"alumina hardness","type":"property","result":"Mohs 9; HV ≈ 1800"},
        {"query":"zirconia phase transition","type":"property","result":"~1170°C monoclinic ↔ tetragonal"},
        {"query":"silicon carbide melting point","type":"property","result":"≈ 2730°C (decomposes)"},
     ])),
    ("science-and-technology", "materials-science", "Semiconductors", "semiconductors",
     "Si, Ge, GaAs band gaps and semiconductor device physics.",
     "physics.png", False, True, J([
        {"query":"silicon band gap","type":"property","result":"1.12 eV at 300 K"},
        {"query":"gallium arsenide band gap","type":"property","result":"1.42 eV; direct band gap"},
        {"query":"intrinsic carrier silicon","type":"property","result":"n_i ≈ 1.0 × 10¹⁰ /cm³ at 300 K"},
     ])),
    ("science-and-technology", "materials-science", "Composites", "composites",
     "Fiber-reinforced composites, carbon fiber, glass fiber properties.",
     "physics.png", False, False, J([
        {"query":"carbon fiber tensile strength","type":"property","result":"3500–7000 MPa (T-300 to T-1100)"},
        {"query":"fiberglass density","type":"property","result":"≈ 1.5–2.0 g/cm³"},
        {"query":"composite rule of mixtures","type":"theory","result":"E_c = V_f · E_f + V_m · E_m"},
     ])),

    # --- Astronomy more (6) ---
    ("science-and-technology", "astronomy", "Galaxies", "galaxies",
     "Galaxy types, the Milky Way, Andromeda, and galaxy classification.",
     "astronomy.png", False, False, J([
        {"query":"Milky Way diameter","type":"galaxy","result":"≈ 100,000 light-years (87,400 ly stellar disk)"},
        {"query":"Andromeda distance","type":"galaxy","result":"≈ 2.537 million light-years"},
        {"query":"galaxy types Hubble","type":"classification","result":"Elliptical, spiral, barred spiral, irregular"},
     ])),
    ("science-and-technology", "astronomy", "Nebulae", "nebulae",
     "Emission, reflection, planetary, and dark nebulae.",
     "astronomy.png", False, False, J([
        {"query":"Crab Nebula","type":"nebula","result":"Supernova remnant (1054 AD); 6500 ly away"},
        {"query":"Orion Nebula","type":"nebula","result":"M42; 1344 ly; visible naked-eye in Orion's sword"},
        {"query":"Ring Nebula","type":"nebula","result":"M57; planetary nebula in Lyra; 2300 ly"},
     ])),
    ("science-and-technology", "astronomy", "Telescopes", "telescopes",
     "Famous telescopes (Hubble, JWST), their mirrors, and missions.",
     "astronomy.png", False, False, J([
        {"query":"Hubble mirror diameter","type":"telescope","result":"2.4 m"},
        {"query":"JWST mirror diameter","type":"telescope","result":"6.5 m (segmented)"},
        {"query":"largest ground telescope","type":"telescope","result":"GTC (10.4 m) — Roque de los Muchachos, La Palma"},
     ])),
    ("science-and-technology", "astronomy", "Satellites & Probes", "satellites-probes",
     "Iconic space missions: Voyager, Cassini, Mars rovers.",
     "astronomy.png", False, False, J([
        {"query":"Voyager 1 distance","type":"probe","result":"≈ 24 billion km from Sun (2024); in interstellar space"},
        {"query":"Cassini mission","type":"probe","result":"Saturn orbiter 2004–2017; Grand Finale dive 2017"},
        {"query":"Perseverance rover","type":"rover","result":"NASA, Mars Jezero Crater 2021–present; sample caching"},
     ])),
    ("science-and-technology", "astronomy", "Solar System Bodies", "solar-system-bodies",
     "Planets, dwarf planets, moons, and asteroids in our solar system.",
     "astronomy.png", False, False, J([
        {"query":"largest moon","type":"moon","result":"Ganymede (Jupiter) — 5268 km diameter"},
        {"query":"dwarf planets","type":"object","result":"Pluto, Eris, Makemake, Haumea, Ceres (5 official)"},
        {"query":"asteroid belt","type":"region","result":"2.2–3.2 AU; >1 million bodies > 1 km"},
     ])),
    ("science-and-technology", "astronomy", "Cosmology", "cosmology",
     "Big Bang, cosmic microwave background, and dark matter/energy.",
     "astronomy.png", False, False, J([
        {"query":"age of universe","type":"cosmology","result":"≈ 13.787 billion years (Planck 2018)"},
        {"query":"CMB temperature","type":"cosmology","result":"2.7255 K (FIRAS COBE)"},
        {"query":"dark matter fraction","type":"cosmology","result":"≈ 27% of universe (rest: 68% dark energy, 5% ordinary matter)"},
     ])),

    # --- World data: geography expansion (8) ---
    ("society-and-culture", "geography", "Major Cities", "major-cities",
     "World's largest cities by population and metropolitan area.",
     "geography.png", False, True, J([
        {"query":"largest city by population","type":"city","result":"Tokyo metro — ≈ 37 million"},
        {"query":"population New York City","type":"city","result":"8.34 million (2022)"},
        {"query":"population Mumbai","type":"city","result":"≈ 20.4 million metro"},
     ])),
    ("society-and-culture", "geography", "Mountains", "mountains",
     "Highest peaks, mountain ranges, and altitude data.",
     "geography.png", False, False, J([
        {"query":"tallest mountain","type":"peak","result":"Mount Everest — 8848.86 m (29031.7 ft)"},
        {"query":"tallest in North America","type":"peak","result":"Denali — 6190 m (20310 ft)"},
        {"query":"K2 height","type":"peak","result":"8611 m; 2nd-tallest, hardest 8000er to climb"},
     ])),
    ("society-and-culture", "geography", "Rivers", "rivers",
     "Longest rivers, drainage basins, and river-system data.",
     "geography.png", False, False, J([
        {"query":"longest river","type":"river","result":"Nile — 6650 km (Amazon ≈ 6400 km; debated)"},
        {"query":"Mississippi length","type":"river","result":"≈ 3766 km"},
        {"query":"Yangtze length","type":"river","result":"≈ 6300 km — longest in Asia"},
     ])),
    ("society-and-culture", "geography", "Lakes & Seas", "lakes-seas",
     "Largest freshwater lakes, inland seas, and depth measurements.",
     "geography.png", False, False, J([
        {"query":"largest freshwater lake by surface","type":"lake","result":"Lake Superior — 82100 km²"},
        {"query":"deepest lake","type":"lake","result":"Lake Baikal — 1642 m (Russia)"},
        {"query":"Caspian Sea","type":"lake","result":"Largest landlocked body — 371000 km²"},
     ])),
    ("society-and-culture", "geography", "Oceans", "oceans",
     "Five oceans, depths, and oceanographic measurements.",
     "geography.png", False, False, J([
        {"query":"deepest ocean point","type":"ocean","result":"Mariana Trench — Challenger Deep ≈ 10935 m"},
        {"query":"Pacific Ocean area","type":"ocean","result":"≈ 165 million km² (largest)"},
        {"query":"average ocean depth","type":"ocean","result":"≈ 3688 m"},
     ])),
    ("society-and-culture", "geography", "Deserts", "deserts",
     "Largest deserts, ice deserts, and desert ecosystems.",
     "geography.png", False, False, J([
        {"query":"largest desert","type":"desert","result":"Antarctica (polar, 14.2 M km²); Sahara largest hot (~9.2 M km²)"},
        {"query":"Sahara temperature record","type":"desert","result":"58°C (136°F) — Aziziya, Libya 1922 (disputed)"},
        {"query":"Atacama rainfall","type":"desert","result":"< 15 mm/year average; some places no rain on record"},
     ])),
    ("society-and-culture", "geography", "Islands", "islands",
     "Largest islands, archipelagos, and island nations.",
     "geography.png", False, False, J([
        {"query":"largest island","type":"island","result":"Greenland — 2,166,086 km²"},
        {"query":"Japan four main islands","type":"island","result":"Honshu, Hokkaido, Kyushu, Shikoku"},
        {"query":"most islands country","type":"country","result":"Sweden — ≈ 267,570 islands"},
     ])),
    ("society-and-culture", "geography", "Time Zones", "time-zones",
     "World time zones, UTC offsets, and DST schedules.",
     "geography.png", False, False, J([
        {"query":"number of time zones","type":"system","result":"24 standard hourly + ~9 half/quarter-hour zones"},
        {"query":"UTC offset Tokyo","type":"tz","result":"UTC+9 (JST, no DST)"},
        {"query":"UTC offset India","type":"tz","result":"UTC+5:30 (IST)"},
     ])),

    # --- Programming languages (5) ---
    ("science-and-technology", "computer-science", "Python", "python",
     "Python language features, syntax, libraries, and Pythonisms.",
     "discrete-math.png", False, True, J([
        {"query":"Python list comprehension","type":"syntax","result":"[x**2 for x in range(10)]"},
        {"query":"Python pip","type":"tool","result":"Package installer; pip install <package>"},
        {"query":"Python GIL","type":"feature","result":"Global Interpreter Lock; one thread runs Python bytecode at a time"},
     ])),
    ("science-and-technology", "computer-science", "JavaScript", "javascript",
     "JavaScript syntax, modern ES features, and DOM.",
     "discrete-math.png", False, False, J([
        {"query":"JavaScript arrow function","type":"syntax","result":"const fn = (x) => x * 2;"},
        {"query":"JavaScript async/await","type":"feature","result":"async fn(){ const r = await fetch(url); }"},
        {"query":"JavaScript event loop","type":"runtime","result":"Single-threaded; task + microtask queues"},
     ])),
    ("science-and-technology", "computer-science", "Rust", "rust",
     "Rust ownership, borrowing, lifetimes, and zero-cost abstractions.",
     "discrete-math.png", False, False, J([
        {"query":"Rust ownership rules","type":"rule","result":"1 owner; transfers via move; references borrow"},
        {"query":"Rust lifetimes","type":"feature","result":"&'a T — annotates how long references live"},
        {"query":"Rust cargo build","type":"tool","result":"cargo build / cargo run / cargo test"},
     ])),
    ("science-and-technology", "computer-science", "Go", "go-lang",
     "Go syntax, goroutines, channels, and standard library.",
     "discrete-math.png", False, False, J([
        {"query":"Go goroutine","type":"concurrency","result":"go fn() — launches a lightweight thread"},
        {"query":"Go channel","type":"concurrency","result":"ch := make(chan int); ch <- v; v := <-ch"},
        {"query":"Go module init","type":"tool","result":"go mod init example.com/m"},
     ])),
    ("science-and-technology", "computer-science", "Machine Learning", "machine-learning",
     "ML basics: supervised, unsupervised, gradient descent, and metrics.",
     "discrete-math.png", False, True, J([
        {"query":"gradient descent","type":"algorithm","result":"θ_{n+1} = θ_n − η ∇L(θ_n)"},
        {"query":"overfitting","type":"concept","result":"Model fits training noise; high variance"},
        {"query":"F1 score","type":"metric","result":"F1 = 2 · (precision · recall)/(precision + recall)"},
     ])),

    # --- Biology more (5) ---
    ("science-and-technology", "biological-sciences", "Cell Biology", "cell-biology",
     "Organelles, cell types, and cellular processes.",
     "life-sciences.png", False, False, J([
        {"query":"mitochondrion function","type":"organelle","result":"ATP production via oxidative phosphorylation"},
        {"query":"size red blood cell","type":"cell","result":"≈ 7.5 µm diameter, biconcave disk"},
        {"query":"nucleus function","type":"organelle","result":"DNA storage, transcription, ribosome assembly"},
     ])),
    ("science-and-technology", "biological-sciences", "Genetics", "genetics",
     "DNA, genes, alleles, and Mendelian inheritance.",
     "life-sciences.png", False, False, J([
        {"query":"human chromosome count","type":"genetics","result":"23 pairs (46 total); XX female, XY male"},
        {"query":"DNA base pairs human genome","type":"genetics","result":"≈ 3.2 billion base pairs"},
        {"query":"Mendel's first law","type":"law","result":"Law of segregation — alleles separate at gamete formation"},
     ])),
    ("science-and-technology", "biological-sciences", "Taxonomy", "taxonomy",
     "Linnaean classification, kingdoms, and binomial nomenclature.",
     "life-sciences.png", False, False, J([
        {"query":"Linnaean rank order","type":"taxonomy","result":"Domain > Kingdom > Phylum > Class > Order > Family > Genus > Species"},
        {"query":"five kingdoms","type":"taxonomy","result":"Animalia, Plantae, Fungi, Protista, Monera (Whittaker)"},
        {"query":"binomial name human","type":"taxonomy","result":"Homo sapiens"},
     ])),
    ("science-and-technology", "biological-sciences", "Ecology", "ecology-detail",
     "Food chains, ecosystems, biomes, and biodiversity.",
     "life-sciences.png", False, False, J([
        {"query":"trophic levels","type":"ecology","result":"Producer → primary, secondary, tertiary consumer → decomposer"},
        {"query":"world biome count","type":"ecology","result":"~5 major (forest, grassland, desert, tundra, aquatic)"},
        {"query":"species extinction rate","type":"ecology","result":"~1000× background rate; 6th mass extinction debate"},
     ])),
    ("science-and-technology", "biological-sciences", "Evolution", "evolution",
     "Natural selection, speciation, and evolutionary milestones.",
     "life-sciences.png", False, False, J([
        {"query":"Darwin Origin year","type":"history","result":"1859 — On the Origin of Species"},
        {"query":"Cambrian explosion","type":"era","result":"~540 Mya; rapid diversification of animal phyla"},
        {"query":"human chimp DNA similarity","type":"genetics","result":"≈ 98.8% identical"},
     ])),

    # --- Weather (3) ---
    ("science-and-technology", "weather", "Hurricanes", "hurricanes",
     "Hurricane categories, formation, and historical storms.",
     "weather.png", False, False, J([
        {"query":"Cat 5 hurricane wind","type":"intensity","result":"≥ 252 km/h (157 mph) sustained"},
        {"query":"Atlantic hurricane season","type":"season","result":"June 1 – November 30 (peak Sept)"},
        {"query":"deadliest US hurricane","type":"event","result":"Galveston 1900 — 6000–12000 deaths"},
     ])),
    ("science-and-technology", "weather", "Tornadoes", "tornadoes",
     "Enhanced Fujita scale, tornado alley, and tornado frequency.",
     "weather.png", False, False, J([
        {"query":"EF5 tornado wind speed","type":"intensity","result":"≥ 200 mph (322 km/h)"},
        {"query":"tornado alley","type":"region","result":"South Dakota → Texas through plains; spring peak"},
        {"query":"avg US tornadoes per year","type":"stat","result":"≈ 1200 (most in any country)"},
     ])),
    ("science-and-technology", "weather", "Climate Zones", "climate-zones",
     "Köppen climate classification: tropical, dry, temperate, continental, polar.",
     "weather.png", False, False, J([
        {"query":"Koppen tropical rainforest","type":"climate","result":"Af — mean monthly temp ≥ 18°C; precip ≥ 60mm all months"},
        {"query":"Mediterranean climate","type":"climate","result":"Csa — hot dry summer, mild wet winter (Cs)"},
        {"query":"tundra climate","type":"climate","result":"ET — warmest month avg 0–10°C; very short summer"},
     ])),
]

assert len(NEW_TOPICS) == 90, f"expected 90 topics, got {len(NEW_TOPICS)}"

# Sanity: assert all new slugs are unique among themselves
_seen = set()
for t in NEW_TOPICS:
    s = t[3]
    assert s not in _seen, f"duplicate new slug: {s}"
    _seen.add(s)

# ---------------------------------------------------------------------------
# (2) Computation results — bulk additions (target 1500+)
# ---------------------------------------------------------------------------
EXTRA_RESULTS: list[tuple] = []

def E(q, parsed, ans, cat, sub, kw, related, slug, plot_url=''):
    EXTRA_RESULTS.append((q, parsed, ans, cat, sub, kw, related, slug, plot_url))

# --- (A) Math word problems — 200 ---
# Distance-rate-time, age, mixture, work, money, percent

# Rate-time-distance (40)
RTD = [
    (60, 3, 'a car travels at {r} mph for {t} hours'),
    (45, 5, 'a train averages {r} km/h for {t} hours'),
    (80, 2.5, 'a bus moves at {r} km/h for {t} hours'),
    (15, 4, 'a cyclist rides at {r} km/h for {t} hours'),
    (5, 6, 'a hiker walks at {r} km/h for {t} hours'),
    (25, 1.5, 'a runner moves at {r} km/h for {t} hours'),
    (120, 4, 'a plane flies at {r} km/h for {t} hours'),
    (35, 2, 'a delivery van averages {r} mph for {t} hours'),
    (95, 3, 'an Amtrak train at {r} mph for {t} hours'),
    (12, 1.25, 'a kayaker paddles at {r} km/h for {t} hours'),
]
for r, t, tmpl in RTD:
    d = r * t
    q = f"if {tmpl.format(r=r, t=t)}, what is the distance?"
    E(q, f"d = r·t = {r}·{t}", f"{d:g}",
      "everyday-life", "household-math",
      f"distance rate time {r} {t}",
      [f"if a car travels {d:g} units at {r} units, time?"],
      "fraction-percent")
# inverse: solve for time given distance and rate
for r, t, tmpl in RTD:
    d = r * t
    q = f"how long to travel {d:g} units at {r} units per hour?"
    E(q, f"t = d/r = {d:g}/{r}", f"{t:g} hours",
      "everyday-life", "household-math",
      f"time distance rate inverse {d:g} {r}",
      [], "fraction-percent")
# solve for rate
for r, t, tmpl in RTD:
    d = r * t
    q = f"average speed to cover {d:g} units in {t:g} hours?"
    E(q, f"r = d/t = {d:g}/{t:g}", f"{r:g} per hour",
      "everyday-life", "household-math",
      f"speed average rate {d:g} {t:g}",
      [], "fraction-percent")
# meeting/closing problems (10)
MEET = [
    (60, 40, 100, 'two cars'),
    (50, 30, 200, 'two trains'),
    (15, 10, 50, 'two cyclists'),
    (5, 4, 27, 'two hikers'),
    (80, 70, 300, 'two planes'),
    (35, 25, 120, 'two motorcycles'),
    (90, 60, 450, 'two trains'),
    (22, 18, 120, 'two boats'),
    (45, 55, 200, 'two trucks'),
    (75, 25, 300, 'two vehicles'),
]
for v1, v2, dist, desc in MEET:
    t = dist / (v1 + v2)
    q = f"{desc} start {dist} apart and approach at {v1} and {v2}. When meet?"
    E(q, f"t = {dist}/({v1}+{v2})", f"{t:.3f} hours",
      "everyday-life", "household-math",
      f"meeting problem {v1} {v2} {dist}",
      [], "fraction-percent")

# Age problems (30)
AGE = [
    ('Alice is twice as old as Bob; in 10 yr Alice is 1.5× Bob age', 'A=2B, A+10=1.5(B+10)', 'A=10, B=5'),
    ('John is 3 yr older than Jane; sum of ages 23', 'J = K+3, J+K=23', 'J=13, Jane=10'),
    ('Mom is 30 years older than child; in 5 yr Mom is 4× child', 'M=C+30, M+5=4(C+5)', 'M=35, C=5'),
    ('father is 4× son; in 20 yr father is 2× son', 'F=4S, F+20=2(S+20)', 'F=40, S=10'),
    ('Anna is half Ben age; in 15 yr Anna is 2/3 Ben', 'A=B/2, A+15=2/3(B+15)', 'A=15, B=30'),
    ('grandma is 50 older; in 10 yr grandma is 6× grandchild', 'G=C+50, G+10=6(C+10)', 'G=50, C=0; problem invalid'),
    ('Peter is 5 years older than Sara; in 3 yr ratio 7:6', 'P=S+5, (P+3)/(S+3)=7/6', 'P=32, S=27'),
    ('Tom is 2× Jerry; difference is 9', 'T=2J, T-J=9', 'T=18, J=9'),
    ('Lucy is 4 less than 3× Mark; sum 28', 'L=3M-4, L+M=28', 'L=20, M=8'),
    ('twins age sum 28; one age', 'twin', 'each 14'),
]
for tmpl, parsed, ans in AGE:
    q = "age problem: " + tmpl
    E(q, parsed, ans,
      "everyday-life", "household-math",
      f"age word problem {tmpl[:30]}",
      [], "fraction-percent")
# generate 20 more parametrized age problems
for k in range(20):
    a = 5 + k
    b = 2 * a - 1
    q = f"age problem: Alice age {a}, Bob age {b}, total"
    E(q, f"A+B", f"{a+b}",
      "everyday-life", "household-math",
      f"age sum {a} {b}",
      [], "fraction-percent")

# Mixture/work problems (20)
for x, y in [(2,3),(3,5),(4,5),(6,8),(5,10),(2,7),(3,6),(4,9),(6,12),(10,15)]:
    rate = 1/x + 1/y
    t = 1 / rate
    q = f"work problem: A finishes in {x}h, B finishes in {y}h. Together?"
    E(q, f"1/T = 1/{x} + 1/{y}", f"T ≈ {t:.4f} hours",
      "everyday-life", "household-math",
      f"work problem combined rate {x} {y}",
      [], "fraction-percent")
# mixture
for w1, c1, w2, c2 in [(10,20,5,50),(20,10,30,40),(15,25,5,75),(8,30,2,80),(12,15,8,55),
                       (25,10,15,40),(40,5,10,60),(6,20,4,80),(18,30,12,70),(20,18,5,90)]:
    avg = (w1*c1 + w2*c2)/(w1+w2)
    q = f"mixture: {w1}L at {c1}% and {w2}L at {c2}%. Final percent?"
    E(q, f"({w1}·{c1}+{w2}·{c2})/({w1}+{w2})", f"{avg:.2f}%",
      "everyday-life", "household-math",
      f"mixture problem {w1} {c1} {w2} {c2}",
      [], "fraction-percent")

# Money / percent problems (60)
SALES = [(100,10),(200,15),(50,20),(75,25),(120,30),(40,5),(80,40),(150,35),
         (60,12),(90,18),(250,22),(45,7),(110,10),(28,15),(180,28),(35,20),
         (140,17),(95,33),(72,8),(63,11)]
for orig, pct in SALES:
    final = orig * (1 - pct/100)
    save = orig - final
    q = f"{pct}% off ${orig}?"
    E(q, f"${orig} × (1 − {pct}%)", f"Sale price ${final:.2f}, save ${save:.2f}",
      "society-and-culture", "finance",
      f"discount sale {orig} {pct} percent",
      [f"{pct+5}% off ${orig}"], "finance")
# tip problems
for bill, tip_pct in [(40,15),(50,18),(60,20),(75,15),(100,20),(35,18),(28,15),
                     (120,20),(85,18),(150,20),(45,15),(95,20),(67,18),(110,15),
                     (38,20),(125,18),(56,20),(82,15),(99,18),(70,20)]:
    tip = bill * tip_pct / 100
    total = bill + tip
    q = f"{tip_pct}% tip on ${bill}"
    E(q, f"${bill} × {tip_pct}%", f"Tip ${tip:.2f}, total ${total:.2f}",
      "society-and-culture", "finance",
      f"tip {bill} {tip_pct}",
      [], "finance")
# percent change
for old, new in [(100,120),(80,100),(150,120),(50,75),(200,160),(40,52),(90,108),
                 (60,45),(125,100),(250,300),(30,42),(180,144),(75,90),(65,52),
                 (250,200),(35,42),(140,168),(45,36),(220,275),(85,68)]:
    chg = (new - old)/old * 100
    direction = "increase" if chg > 0 else "decrease"
    q = f"percent change from {old} to {new}"
    E(q, f"({new}−{old})/{old} × 100", f"{abs(chg):.2f}% {direction}",
      "society-and-culture", "finance",
      f"percent change {old} {new}",
      [], "finance")

# --- (B) Unit conversion natural language — 200 ---
# format: "how many <unit2> in <n> <unit1>" / "convert <n> <unit1> to <unit2>"
import math as _m
LEN_NL = [
    (1, 'mile', 'kilometers', 1.609344),
    (3, 'miles', 'kilometers', 1.609344),
    (5, 'miles', 'kilometers', 1.609344),
    (10, 'miles', 'kilometers', 1.609344),
    (26.2, 'miles', 'kilometers', 1.609344),
    (1, 'kilometer', 'miles', 0.621371),
    (5, 'kilometers', 'miles', 0.621371),
    (42.195, 'kilometers', 'miles', 0.621371),
    (100, 'kilometers', 'miles', 0.621371),
    (1, 'foot', 'inches', 12),
    (3, 'feet', 'inches', 12),
    (6, 'feet', 'inches', 12),
    (1, 'yard', 'feet', 3),
    (1, 'yard', 'meters', 0.9144),
    (1, 'meter', 'feet', 3.28084),
    (1.83, 'meters', 'feet', 3.28084),
    (100, 'meters', 'feet', 3.28084),
    (1, 'inch', 'centimeters', 2.54),
    (12, 'inches', 'centimeters', 2.54),
    (24, 'inches', 'centimeters', 2.54),
    (1, 'centimeter', 'inches', 0.393701),
    (30, 'centimeters', 'inches', 0.393701),
    (100, 'centimeters', 'meters', 0.01),
    (1, 'nautical mile', 'kilometers', 1.852),
    (1, 'light year', 'kilometers', 9.461e12),
    (1, 'AU', 'kilometers', 149597870.7),
    (1, 'parsec', 'light years', 3.262),
    (1, 'mil', 'inches', 0.001),
    (1, 'angstrom', 'meters', 1e-10),
    (1, 'fathom', 'meters', 1.8288),
]
for n, u1, u2, k in LEN_NL:
    v = n * k
    if v >= 1e6 or v <= 1e-3:
        s = f"{v:.4g}"
    else:
        s = f"{v:.4f}"
    q1 = f"how many {u2} in {n} {u1}"
    E(q1, f"{n} {u1}", f"{s} {u2}",
      "science-and-technology", "units-measures",
      f"convert nl {n} {u1} {u2}",
      [f"{n+1} {u1} in {u2}"], "units-measures")
    q2 = f"convert {n} {u1} to {u2}"
    E(q2, f"{n} {u1} → {u2}", f"≈ {s} {u2}",
      "science-and-technology", "units-measures",
      f"convert {n} {u1} to {u2}",
      [], "units-measures")

MASS_NL = [
    (1, 'kilogram', 'pounds', 2.20462),
    (5, 'kilograms', 'pounds', 2.20462),
    (70, 'kilograms', 'pounds', 2.20462),
    (100, 'kilograms', 'pounds', 2.20462),
    (1, 'pound', 'kilograms', 0.453592),
    (5, 'pounds', 'kilograms', 0.453592),
    (150, 'pounds', 'kilograms', 0.453592),
    (1, 'pound', 'ounces', 16),
    (1, 'ounce', 'grams', 28.3495),
    (8, 'ounces', 'grams', 28.3495),
    (16, 'ounces', 'grams', 28.3495),
    (1, 'gram', 'milligrams', 1000),
    (1, 'kilogram', 'grams', 1000),
    (1, 'stone', 'pounds', 14),
    (1, 'ton', 'kilograms', 907.185),
    (1, 'metric ton', 'kilograms', 1000),
    (1, 'carat', 'milligrams', 200),
    (1, 'troy ounce', 'grams', 31.1035),
    (1, 'grain', 'milligrams', 64.7989),
    (1, 'slug', 'kilograms', 14.5939),
]
for n, u1, u2, k in MASS_NL:
    v = n * k
    s = f"{v:.4f}" if v < 1e6 else f"{v:.4g}"
    q1 = f"how many {u2} in {n} {u1}"
    E(q1, f"{n} {u1}", f"{s} {u2}",
      "science-and-technology", "units-measures",
      f"mass convert {n} {u1} {u2}",
      [], "units-measures")
    q2 = f"convert {n} {u1} to {u2}"
    E(q2, f"{n} {u1} → {u2}", f"≈ {s} {u2}",
      "science-and-technology", "units-measures",
      f"convert {n} {u1} to {u2}",
      [], "units-measures")

VOL_NL = [
    (1, 'gallon', 'liters', 3.78541),
    (5, 'gallons', 'liters', 3.78541),
    (10, 'gallons', 'liters', 3.78541),
    (1, 'liter', 'gallons', 0.264172),
    (1, 'liter', 'milliliters', 1000),
    (1, 'cubic meter', 'liters', 1000),
    (1, 'fluid ounce', 'milliliters', 29.5735),
    (1, 'pint', 'milliliters', 473.176),
    (1, 'quart', 'milliliters', 946.353),
    (1, 'barrel oil', 'liters', 158.987),
    (1, 'cup', 'milliliters', 236.588),
    (1, 'cup', 'fluid ounces', 8),
    (1, 'tablespoon', 'teaspoons', 3),
    (1, 'tablespoon', 'milliliters', 14.7868),
    (1, 'teaspoon', 'milliliters', 4.92892),
    (1, 'cubic foot', 'liters', 28.3168),
    (1, 'cubic inch', 'milliliters', 16.3871),
    (1, 'imperial gallon', 'liters', 4.54609),
    (1, 'gill', 'milliliters', 118.294),
    (1, 'acre-foot', 'liters', 1233481.84),
]
for n, u1, u2, k in VOL_NL:
    v = n * k
    s = f"{v:.4f}" if v < 1e6 else f"{v:.4g}"
    q1 = f"how many {u2} in {n} {u1}"
    E(q1, f"{n} {u1}", f"{s} {u2}",
      "science-and-technology", "units-measures",
      f"volume convert {n} {u1} {u2}",
      [], "units-measures")

# Speed conversions
SPEED_NL = [
    (60, 'mph', 'kmh', 1.60934),
    (100, 'kmh', 'mph', 0.621371),
    (1, 'mach', 'mph', 767.269),
    (1, 'mach', 'kmh', 1234.8),
    (1, 'knot', 'mph', 1.15078),
    (1, 'knot', 'kmh', 1.852),
    (1, 'mps', 'kmh', 3.6),
    (1, 'mps', 'mph', 2.23694),
    (10, 'mph', 'mps', 0.44704),
    (30, 'mph', 'mps', 0.44704),
    (50, 'mph', 'kmh', 1.60934),
    (200, 'kmh', 'mph', 0.621371),
    (100, 'mps', 'kmh', 3.6),
    (333, 'mps', 'mph', 2.23694),
    (1, 'speed of light', 'mph', 670616629),
]
for n, u1, u2, k in SPEED_NL:
    v = n * k
    s = f"{v:.4g}" if v >= 1e6 or v < 0.01 else f"{v:.4f}"
    q = f"convert {n} {u1} to {u2}"
    E(q, f"{n} {u1}", f"≈ {s} {u2}",
      "science-and-technology", "units-measures",
      f"speed {n} {u1} {u2}",
      [], "units-measures")

# Energy
ENERGY_NL = [
    (1, 'kcal', 'joules', 4184),
    (100, 'kcal', 'joules', 4184),
    (1, 'kWh', 'joules', 3.6e6),
    (1, 'eV', 'joules', 1.602e-19),
    (1, 'BTU', 'joules', 1055.06),
    (1, 'erg', 'joules', 1e-7),
    (1, 'foot-pound', 'joules', 1.35582),
    (1, 'horsepower-hour', 'joules', 2.6845e6),
    (1, 'kilojoule', 'kcal', 0.239006),
    (1, 'megaton TNT', 'joules', 4.184e15),
]
for n, u1, u2, k in ENERGY_NL:
    v = n * k
    s = f"{v:.4g}"
    q = f"convert {n} {u1} to {u2}"
    E(q, f"{n} {u1}", f"≈ {s} {u2}",
      "science-and-technology", "units-measures",
      f"energy {n} {u1} {u2}",
      [], "units-measures")

print(f"[r3] after conversions: {len(EXTRA_RESULTS)}")

# --- (C) Plot custom function — 60 ---
PLOT_FNS = [
    ('sin(x)','from -2pi to 2pi','Wave; amplitude 1, period 2π, range [−1,1]'),
    ('cos(x)','from 0 to 4pi','Wave; amplitude 1, period 2π, range [−1,1]'),
    ('tan(x)','from -pi to pi','Periodic with vertical asymptotes at x=±π/2'),
    ('x^2','from -5 to 5','Parabola opening upward, vertex at origin'),
    ('x^3','from -3 to 3','Cubic; odd symmetry; inflection at origin'),
    ('1/x','from -3 to 3 excluding 0','Hyperbola; asymptotes at axes'),
    ('e^x','from -2 to 4','Exponential growth; passes through (0,1)'),
    ('ln(x)','from 0.1 to 10','Logarithm; vertical asymptote at x=0; passes (1,0)'),
    ('sqrt(x)','from 0 to 16','Increases as x^(1/2)'),
    ('|x|','from -5 to 5','V-shape; minimum at origin'),
    ('x^2 - 4','from -3 to 3','Parabola shifted down 4'),
    ('sin(x)*cos(x)','from 0 to 2pi','Beats pattern; equals sin(2x)/2'),
    ('e^(-x)','from 0 to 5','Exponential decay'),
    ('e^(-x^2)','from -3 to 3','Gaussian (bell curve)'),
    ('1/(1+x^2)','from -5 to 5','Lorentzian; max 1 at x=0'),
    ('sin(x)/x','from -10 to 10','Sinc function; lim → 1 at 0'),
    ('cos(2x)','from 0 to pi','Compressed cosine; period π'),
    ('sin(x)^2','from 0 to 2pi','Always non-negative; mean 1/2'),
    ('floor(x)','from -3 to 3','Step function; jumps at integers'),
    ('ceil(x)','from -3 to 3','Step function from above'),
    ('x sin(1/x)','from -1 to 1','Oscillates and dampens to 0'),
    ('1/log(x)','from 1.5 to 10','Reciprocal logarithm; decreasing'),
    ('arcsin(x)','from -1 to 1','Inverse sine; range [−π/2, π/2]'),
    ('arctan(x)','from -10 to 10','Inverse tangent; range (−π/2, π/2)'),
    ('cosh(x)','from -3 to 3','Hyperbolic cosine; even, ≥ 1'),
    ('sinh(x)','from -3 to 3','Hyperbolic sine; odd, unbounded'),
    ('x^2 + sin(x)','from -5 to 5','Parabola with oscillation'),
    ('sin(x) + cos(2x)','from 0 to 2pi','Sum of harmonics'),
    ('e^(-x) sin(2x)','from 0 to 6','Damped sinusoid'),
    ('e^x - e^(-x)','from -2 to 2','2 sinh(x); odd'),
    ('x^4 - 4x^2','from -3 to 3','Quartic with local min/max'),
    ('Floor[x]','floor 0..5','Same as floor(x); step function'),
    ('mod(x,2)','from 0 to 8','Sawtooth, period 2'),
    ('Bessel J_0(x)','from 0 to 20','Oscillating, decaying amplitude'),
    ('zeta(s)','s 2..10','Riemann zeta; ζ(2)=π²/6'),
    ('gamma(x)','from 0.1 to 5','Generalises factorial'),
    ('erf(x)','from -3 to 3','S-shaped; → ±1 at infinities'),
    ('Heaviside step','from -2 to 2','0 for x<0, 1 for x>0'),
    ('triangle wave','from -2 to 2','Periodic ramp up/down'),
    ('square wave','from -2 to 2','±1 alternating'),
    ('sawtooth wave','from 0 to 4','Linear rises then drops'),
    ('logistic 1/(1+e^-x)','from -6 to 6','S-curve; range (0,1)'),
    ('softplus log(1+e^x)','from -3 to 3','Smooth ReLU'),
    ('ReLU max(0,x)','from -3 to 3','Piecewise linear; 0 for negative'),
    ('parabolic 3x^2 - 2x + 1','from -2 to 2','Opens upward; vertex near x=1/3'),
    ('cubic x^3 - 3x','from -3 to 3','Local extrema at x = ±1'),
    ('sin(pi x)','from 0 to 4','Period 2 wave'),
    ('cos(pi x/2)','from 0 to 4','Period 4 wave'),
    ('logarithmic spiral parametric','t 0..6pi','Spiral; r = e^(t/5)'),
    ('cardioid r = 1 + cos theta','theta 0..2pi','Heart-shaped polar curve'),
    ('rose r = cos(3 theta)','theta 0..2pi','3-petal rose'),
    ('lemniscate r^2 = cos(2 theta)','theta','Figure-eight curve'),
    ('lissajous x=sin(3t), y=sin(2t)','t 0..2pi','Lissajous figure 3:2'),
    ('parametric circle','t 0..2pi','Unit circle x=cos t, y=sin t'),
    ('parametric ellipse','t 0..2pi','x=3 cos t, y=2 sin t'),
    ('parametric helix','t 0..6pi','3D spiral'),
    ('contour x^2 + y^2','levels','Concentric circles'),
    ('contour x^2 - y^2','levels','Hyperbolas'),
    ('3d surface z = sin(x) cos(y)','x,y','Eggcrate pattern'),
    ('3d paraboloid z = x^2 + y^2','x,y','Bowl shape'),
]
for fn, rng, desc in PLOT_FNS:
    q = f"plot {fn} {rng}"
    E(q, f"Plot[{fn}, {rng}]",
      f"Plot generated. {desc}",
      "mathematics", "calculus",
      f"plot graph {fn}",
      [f"plot {fn} larger range"], "calculus",
      plot_url=f"/static/images/plots/{fn[:20].replace(' ','_')}.png")

# --- (D) Wolfram Language code generation — 80 ---
WL_CODES = [
    ("Wolfram Language solve x^2-4=0","Solve[x^2 - 4 == 0, x]","{{x -> -2}, {x -> 2}}"),
    ("Wolfram Language plot sin(x)","Plot[Sin[x], {x, 0, 2 Pi}]","Plot rendered"),
    ("Wolfram Language integrate x^2","Integrate[x^2, x]","x^3/3"),
    ("Wolfram Language D[x^3,x]","D[x^3, x]","3 x^2"),
    ("Wolfram Language Table[i^2,{i,1,5}]","Table[i^2, {i,1,5}]","{1, 4, 9, 16, 25}"),
    ("Wolfram Language NIntegrate","NIntegrate[E^(-x^2), {x, -Infinity, Infinity}]","≈ 1.7724538509 (= sqrt(π))"),
    ("Wolfram Language Sum[1/n^2]","Sum[1/n^2, {n, 1, Infinity}]","Pi^2/6"),
    ("Wolfram Language Limit","Limit[Sin[x]/x, x -> 0]","1"),
    ("Wolfram Language Series","Series[Exp[x], {x, 0, 5}]","1 + x + x^2/2 + x^3/6 + x^4/24 + x^5/120 + O[x]^6"),
    ("Wolfram Language MatrixForm","{{1,2},{3,4}} // MatrixForm","Displays as matrix grid"),
    ("Wolfram Language Det","Det[{{1,2},{3,4}}]","-2"),
    ("Wolfram Language Inverse","Inverse[{{1,2},{3,4}}]","{{-2, 1}, {3/2, -1/2}}"),
    ("Wolfram Language Eigenvalues","Eigenvalues[{{4,1},{2,3}}]","{5, 2}"),
    ("Wolfram Language Eigenvectors","Eigenvectors[{{4,1},{2,3}}]","{{1, 1}, {-1, 2}}"),
    ("Wolfram Language FindRoot","FindRoot[Cos[x] == x, {x, 0.5}]","{x -> 0.739085}"),
    ("Wolfram Language DSolve","DSolve[y'[t] + y[t] == 0, y, t]","y[t] -> C[1] E^(-t)"),
    ("Wolfram Language NDSolve","NDSolve[{y'[t] == -y[t], y[0]==1}, y, {t, 0, 5}]","InterpolatingFunction object"),
    ("Wolfram Language Prime[100]","Prime[100]","541"),
    ("Wolfram Language PrimeQ[97]","PrimeQ[97]","True"),
    ("Wolfram Language FactorInteger","FactorInteger[360]","{{2,3},{3,2},{5,1}}"),
    ("Wolfram Language GCD","GCD[48, 36]","12"),
    ("Wolfram Language LCM","LCM[12, 18]","36"),
    ("Wolfram Language Mod","Mod[10, 3]","1"),
    ("Wolfram Language ContinuedFraction","ContinuedFraction[Pi, 10]","{3, 7, 15, 1, 292, 1, 1, 1, 2, 1}"),
    ("Wolfram Language N[Pi, 20]","N[Pi, 20]","3.1415926535897932385"),
    ("Wolfram Language Rationalize","Rationalize[0.142857, 0.001]","1/7"),
    ("Wolfram Language Simplify","Simplify[(x^2 - 1)/(x - 1)]","1 + x"),
    ("Wolfram Language Expand","Expand[(x + 1)^4]","1 + 4 x + 6 x^2 + 4 x^3 + x^4"),
    ("Wolfram Language Factor","Factor[x^3 - 1]","(-1 + x) (1 + x + x^2)"),
    ("Wolfram Language Collect","Collect[(x+1)(x+2), x]","2 + 3 x + x^2"),
    ("Wolfram Language Mean","Mean[{1,2,3,4,5}]","3"),
    ("Wolfram Language Median","Median[{1,3,5,7,9}]","5"),
    ("Wolfram Language StandardDeviation","StandardDeviation[{1,2,3,4,5}]","Sqrt[5/2] ≈ 1.5811"),
    ("Wolfram Language Variance","Variance[{2, 4, 4, 4, 5, 5, 7, 9}]","32/7 ≈ 4.5714"),
    ("Wolfram Language RandomReal","RandomReal[]","Pseudo-random real ∈ (0,1)"),
    ("Wolfram Language RandomInteger","RandomInteger[{1, 100}]","Pseudo-random integer 1..100"),
    ("Wolfram Language Range","Range[1, 10]","{1, 2, 3, 4, 5, 6, 7, 8, 9, 10}"),
    ("Wolfram Language Map","Map[f, {1,2,3}]","{f[1], f[2], f[3]}"),
    ("Wolfram Language Apply","Apply[Plus, {1,2,3,4}]","10"),
    ("Wolfram Language Fold","Fold[Plus, 0, {1,2,3,4}]","10"),
    ("Wolfram Language Nest","Nest[#^2 &, 2, 4]","65536"),
    ("Wolfram Language Module","Module[{x=5}, x^2]","25"),
    ("Wolfram Language Sort","Sort[{3,1,4,1,5,9,2,6,5}]","{1, 1, 2, 3, 4, 5, 5, 6, 9}"),
    ("Wolfram Language Reverse","Reverse[{1,2,3,4}]","{4, 3, 2, 1}"),
    ("Wolfram Language Length","Length[{a, b, c, d}]","4"),
    ("Wolfram Language Total","Total[{1,2,3,4,5}]","15"),
    ("Wolfram Language StringJoin","StringJoin[\"Wolfram\",\"Alpha\"]","\"WolframAlpha\""),
    ("Wolfram Language StringLength","StringLength[\"WolframAlpha\"]","11"),
    ("Wolfram Language Characters","Characters[\"abc\"]","{\"a\", \"b\", \"c\"}"),
    ("Wolfram Language IntegerDigits","IntegerDigits[12345]","{1, 2, 3, 4, 5}"),
    ("Wolfram Language BaseForm","BaseForm[255, 16]","ff_16"),
    ("Wolfram Language NumberForm","NumberForm[1234567, 6]","1.23457*10^6"),
    ("Wolfram Language Round","Round[2.7]","3"),
    ("Wolfram Language Floor","Floor[2.9]","2"),
    ("Wolfram Language Ceiling","Ceiling[2.1]","3"),
    ("Wolfram Language Min Max","{Min[{1,2,3}], Max[{1,2,3}]}","{1, 3}"),
    ("Wolfram Language Reduce","Reduce[x^2 + y^2 == 1 && y > 0, y]","y == Sqrt[1-x^2]"),
    ("Wolfram Language Solve system","Solve[{x+y==5, x-y==1}, {x,y}]","{{x -> 3, y -> 2}}"),
    ("Wolfram Language LinearSolve","LinearSolve[{{1,2},{3,4}}, {5,11}]","{1, 2}"),
    ("Wolfram Language MatrixPower","MatrixPower[{{1,1},{0,1}}, 5]","{{1,5},{0,1}}"),
    ("Wolfram Language Transpose","Transpose[{{1,2},{3,4}}]","{{1,3},{2,4}}"),
    ("Wolfram Language Dot","{1,2,3} . {4,5,6}","32"),
    ("Wolfram Language Cross","Cross[{1,0,0}, {0,1,0}]","{0, 0, 1}"),
    ("Wolfram Language Norm","Norm[{3, 4}]","5"),
    ("Wolfram Language Power Mod","PowerMod[2, 100, 1000]","376"),
    ("Wolfram Language Fibonacci","Fibonacci[20]","6765"),
    ("Wolfram Language Factorial","Factorial[10]","3628800"),
    ("Wolfram Language Binomial","Binomial[10, 3]","120"),
    ("Wolfram Language Pi as N","Pi // N","3.14159"),
    ("Wolfram Language Tan","Tan[Pi/3]","Sqrt[3]"),
    ("Wolfram Language Sin Pi/4","Sin[Pi/4]","1/Sqrt[2]"),
    ("Wolfram Language Cos 60 degrees","Cos[60 Degree]","1/2"),
    ("Wolfram Language ExpToTrig","ExpToTrig[E^(I x)]","Cos[x] + I Sin[x]"),
    ("Wolfram Language ComplexExpand","ComplexExpand[Re[Exp[I x]]]","Cos[x]"),
    ("Wolfram Language LaplaceTransform","LaplaceTransform[Sin[t], t, s]","1/(1 + s^2)"),
    ("Wolfram Language InverseLaplaceTransform","InverseLaplaceTransform[1/(s^2+1), s, t]","Sin[t]"),
    ("Wolfram Language FourierTransform","FourierTransform[Exp[-x^2], x, k]","E^(-k^2/4)/Sqrt[2]"),
    ("Wolfram Language Manipulate","Manipulate[Plot[Sin[a x], {x,0,2 Pi}], {a, 1, 5}]","Interactive widget"),
    ("Wolfram Language PolarPlot","PolarPlot[1 + Cos[theta], {theta, 0, 2 Pi}]","Cardioid rendered"),
    ("Wolfram Language Plot3D","Plot3D[Sin[x y], {x,-3,3}, {y,-3,3}]","3D surface rendered"),
    ("Wolfram Language ContourPlot","ContourPlot[x^2+y^2, {x,-2,2}, {y,-2,2}]","Concentric circles rendered"),
]
for q, parsed, ans in WL_CODES:
    E(q, parsed, ans,
      "science-and-technology", "computer-science",
      "wolfram language code " + parsed[:40].lower(),
      [], "machine-learning")

print(f"[r3] after plots+WL: {len(EXTRA_RESULTS)}")

# --- (E) Historical facts — 100 events ---
HISTORY = [
    ("when did World War 1 start","July 28, 1914"),
    ("when did World War 1 end","November 11, 1918"),
    ("when did World War 2 start","September 1, 1939"),
    ("when did World War 2 end","September 2, 1945"),
    ("when did Roman Empire fall","476 AD (Western Empire)"),
    ("Declaration of Independence year","July 4, 1776"),
    ("French Revolution year","1789–1799"),
    ("American Civil War years","1861–1865"),
    ("when did Berlin Wall fall","November 9, 1989"),
    ("when did Soviet Union dissolve","December 26, 1991"),
    ("when was the printing press invented","≈ 1440 by Johannes Gutenberg"),
    ("when did Magna Carta sign","June 15, 1215"),
    ("when was Christopher Columbus voyage","1492 (Bahamas landfall Oct 12)"),
    ("when did Galileo confirm heliocentrism","1610 — Sidereus Nuncius"),
    ("when did first manned moon landing happen","July 20, 1969 (Apollo 11)"),
    ("when did first man-made satellite launch","October 4, 1957 (Sputnik 1)"),
    ("when did Yuri Gagarin orbit Earth","April 12, 1961"),
    ("when did first email send","1971 by Ray Tomlinson"),
    ("when was the World Wide Web invented","1989 by Tim Berners-Lee"),
    ("when did SpaceX first launch","March 24, 2006 (Falcon 1)"),
    ("when did first iPhone release","June 29, 2007"),
    ("when was Facebook founded","February 4, 2004"),
    ("when did COVID-19 pandemic begin","Late December 2019 (Wuhan); WHO PHEIC Jan 30 2020"),
    ("when did Treaty of Versailles sign","June 28, 1919"),
    ("when did Industrial Revolution begin","≈ 1760 in Britain"),
    ("when was Napoleon defeated at Waterloo","June 18, 1815"),
    ("when did Hiroshima bombing occur","August 6, 1945"),
    ("when did Nagasaki bombing occur","August 9, 1945"),
    ("when was United Nations founded","October 24, 1945"),
    ("when did Cold War end","1989–1991 (varies; Berlin Wall to Soviet dissolution)"),
    ("when did Tiananmen Square protests occur","April–June 1989 (massacre June 4)"),
    ("when did 9/11 happen","September 11, 2001"),
    ("when did Wright brothers first flight","December 17, 1903 (Kitty Hawk)"),
    ("when did Titanic sink","April 15, 1912"),
    ("when did Mona Lisa get painted","1503–1519 by Leonardo da Vinci"),
    ("when did Shakespeare die","April 23, 1616"),
    ("when did Beethoven die","March 26, 1827"),
    ("when did Einstein publish relativity","Special: 1905; General: 1915"),
    ("when did Curie discover radium","1898"),
    ("when did Mendel publish heredity work","1866"),
    ("when did Darwin publish Origin of Species","November 24, 1859"),
    ("when did Mars Curiosity rover land","August 6, 2012"),
    ("when did Apollo 13 happen","April 1970 (launched 11th, returned 17th)"),
    ("when did first telephone call happen","March 10, 1876 by Alexander Graham Bell"),
    ("when was electricity discovered","Late 1700s; Benjamin Franklin's kite 1752"),
    ("when did Mahatma Gandhi die","January 30, 1948 (assassinated)"),
    ("when did Martin Luther King speech occur","August 28, 1963 ('I Have a Dream')"),
    ("when did Cuban Missile Crisis happen","October 1962 (13 days)"),
    ("when did Berlin airlift happen","June 1948 – May 1949"),
    ("when did Korean War occur","1950–1953"),
    ("when did Vietnam War end","April 30, 1975 (Fall of Saigon)"),
    ("when did Indian independence","August 15, 1947"),
    ("when did Chinese Communist Party form","July 23, 1921"),
    ("when did Mao proclaim PRC","October 1, 1949"),
    ("when did Tutankhamun tomb get discovered","November 4, 1922 by Howard Carter"),
    ("when was Stonehenge built","≈ 3000–2000 BC"),
    ("when did Black Death peak","1346–1353 AD"),
    ("when was the Spanish Flu","1918–1919"),
    ("when did Crimean War occur","1853–1856"),
    ("when did Spanish-American War occur","1898"),
    ("when did Boxer Rebellion occur","1899–1901"),
    ("when did Russian Revolution occur","1917 (February + October)"),
    ("when did Suez Canal open","November 17, 1869"),
    ("when did Panama Canal open","August 15, 1914"),
    ("when did Eiffel Tower complete","March 31, 1889"),
    ("when did Statue of Liberty arrive","June 17, 1885 (dedicated Oct 28 1886)"),
    ("when did Great Wall complete","Multiple eras; most current Ming dynasty 1368–1644"),
    ("when did pyramids of Giza complete","≈ 2560 BC"),
    ("when did Bastille fall","July 14, 1789"),
    ("when did Cuban Revolution succeed","January 1, 1959"),
    ("when did Iranian Revolution occur","1978–1979"),
    ("when did Apartheid end","1994 (with first multiracial election; Mandela elected)"),
    ("when did Nelson Mandela become president","May 10, 1994"),
    ("when did Holocaust occur","1933–1945"),
    ("when did Anne Frank die","≈ February 1945 (Bergen-Belsen)"),
    ("when did Pearl Harbor attack","December 7, 1941"),
    ("when did Normandy D-Day land","June 6, 1944"),
    ("when did Christopher Columbus first voyage end","March 15, 1493"),
    ("when did Magellan circumnavigation end","September 6, 1522 (Elcano completed)"),
    ("when did Pope Francis become pope","March 13, 2013"),
    ("when did Queen Elizabeth II die","September 8, 2022"),
    ("when did King Charles III coronation","May 6, 2023"),
    ("when did Bitcoin whitepaper appear","October 31, 2008"),
    ("when did first Bitcoin block mine","January 3, 2009 (Genesis block)"),
    ("when did Tesla Motors found","July 1, 2003"),
    ("when did Amazon found","July 5, 1994"),
    ("when did Google found","September 4, 1998"),
    ("when did Apple Inc found","April 1, 1976"),
    ("when did Microsoft found","April 4, 1975"),
    ("when did GitHub launch","April 10, 2008"),
    ("when did YouTube launch","February 14, 2005"),
    ("when did Twitter launch","March 21, 2006"),
    ("when did Wikipedia launch","January 15, 2001"),
    ("when did the Concorde retire","November 26, 2003"),
    ("when did the Space Shuttle retire","July 21, 2011 (Atlantis final landing)"),
    ("when did ISS first crew arrive","November 2, 2000 (Expedition 1)"),
    ("when did James Webb Space Telescope launch","December 25, 2021"),
    ("when did Hubble Space Telescope launch","April 24, 1990"),
    ("when did Voyager 1 launch","September 5, 1977"),
    ("when did first cell phone call","April 3, 1973 (Martin Cooper)"),
    ("when did first text message send","December 3, 1992 (Vodafone UK)"),
    ("when did first commercial web browser release","1993 (NCSA Mosaic)"),
    ("when did Bitcoin reach $1","February 9, 2011"),
    ("when was Suez Canal blocked Ever Given","March 23–29, 2021"),
]
for q, ans in HISTORY:
    E(q, q, ans,
      "society-and-culture", "history",
      f"history fact {q[5:30].lower()}",
      [], "ancient-history")

# --- (F) Real-world lookups: weather/stock/population (100) ---
# Weather
WEATHER_CITIES = [
    ('New York','22°C / 72°F, partly cloudy, humidity 60%, wind 12 km/h SW'),
    ('Los Angeles','24°C / 75°F, sunny, humidity 45%, wind 8 km/h W'),
    ('Chicago','15°C / 59°F, overcast, humidity 65%, wind 18 km/h N'),
    ('Houston','28°C / 82°F, thunderstorms forecast, humidity 78%, wind 15 km/h S'),
    ('Phoenix','35°C / 95°F, clear, humidity 18%, wind 10 km/h SE'),
    ('Philadelphia','20°C / 68°F, light rain, humidity 70%, wind 14 km/h E'),
    ('San Antonio','30°C / 86°F, sunny, humidity 55%, wind 12 km/h SE'),
    ('San Diego','21°C / 70°F, marine layer, humidity 72%, wind 8 km/h W'),
    ('Dallas','27°C / 81°F, scattered clouds, humidity 50%, wind 14 km/h S'),
    ('Austin','29°C / 84°F, hot, humidity 48%, wind 10 km/h SE'),
    ('London','13°C / 55°F, light rain, humidity 80%, wind 14 km/h W'),
    ('Paris','17°C / 63°F, cloudy, humidity 70%, wind 12 km/h W'),
    ('Berlin','14°C / 57°F, overcast, humidity 75%, wind 10 km/h NW'),
    ('Madrid','25°C / 77°F, sunny, humidity 35%, wind 9 km/h S'),
    ('Rome','22°C / 72°F, partly sunny, humidity 55%, wind 8 km/h W'),
    ('Tokyo','19°C / 66°F, clear, humidity 60%, wind 11 km/h N'),
    ('Shanghai','23°C / 73°F, hazy, humidity 72%, wind 12 km/h E'),
    ('Beijing','18°C / 64°F, smog, humidity 45%, wind 14 km/h NW'),
    ('Hong Kong','27°C / 81°F, humid, humidity 78%, wind 18 km/h E'),
    ('Seoul','17°C / 63°F, clear, humidity 55%, wind 10 km/h W'),
    ('Singapore','30°C / 86°F, tropical, humidity 82%, wind 8 km/h S'),
    ('Mumbai','31°C / 88°F, hot and humid, humidity 75%, wind 14 km/h SW'),
    ('Delhi','35°C / 95°F, dusty, humidity 25%, wind 16 km/h NW'),
    ('Bangkok','33°C / 91°F, thunderstorms, humidity 78%, wind 10 km/h S'),
    ('Dubai','38°C / 100°F, very hot, humidity 30%, wind 18 km/h NE'),
    ('Sydney','21°C / 70°F, sunny, humidity 60%, wind 22 km/h SE'),
    ('Melbourne','17°C / 63°F, cool, humidity 65%, wind 16 km/h W'),
    ('Mexico City','22°C / 72°F, mild, humidity 55%, wind 8 km/h E'),
    ('Buenos Aires','19°C / 66°F, partly cloudy, humidity 70%, wind 12 km/h NE'),
    ('Sao Paulo','24°C / 75°F, warm, humidity 65%, wind 10 km/h SE'),
    ('Cairo','27°C / 81°F, dry, humidity 35%, wind 14 km/h N'),
    ('Johannesburg','18°C / 64°F, cool, humidity 50%, wind 11 km/h E'),
    ('Lagos','29°C / 84°F, humid, humidity 80%, wind 10 km/h SW'),
    ('Moscow','8°C / 46°F, overcast, humidity 78%, wind 14 km/h NW'),
    ('Istanbul','19°C / 66°F, partly cloudy, humidity 60%, wind 16 km/h N'),
    ('Toronto','12°C / 54°F, cool, humidity 65%, wind 18 km/h W'),
    ('Vancouver','11°C / 52°F, drizzle, humidity 82%, wind 12 km/h SW'),
    ('San Francisco','17°C / 63°F, foggy morning, humidity 75%, wind 14 km/h W'),
    ('Boston','15°C / 59°F, fall feel, humidity 60%, wind 16 km/h NE'),
    ('Atlanta','25°C / 77°F, humid, humidity 70%, wind 8 km/h SW'),
]
for city, wx in WEATHER_CITIES:
    q = f"weather in {city}"
    E(q, f"weather {city}", wx,
      "science-and-technology", "weather",
      f"weather city {city.lower()}",
      [f"weather {city} tomorrow"], "weather")

# Stocks (40)
STOCKS = [
    ('AAPL','Apple','187.32','+1.21','market cap $2.88 T'),
    ('MSFT','Microsoft','420.16','+2.45','market cap $3.12 T'),
    ('GOOGL','Alphabet','165.78','-0.84','market cap $2.05 T'),
    ('AMZN','Amazon','185.93','+0.67','market cap $1.93 T'),
    ('META','Meta Platforms','492.55','+5.21','market cap $1.26 T'),
    ('TSLA','Tesla','205.18','-3.42','market cap $652 B'),
    ('NVDA','Nvidia','875.42','+12.36','market cap $2.15 T'),
    ('BRK.B','Berkshire Hathaway','410.50','+1.85','market cap $895 B'),
    ('JPM','JPMorgan Chase','200.31','+0.58','market cap $575 B'),
    ('V','Visa','280.16','+0.92','market cap $568 B'),
    ('JNJ','Johnson & Johnson','156.78','-0.34','market cap $377 B'),
    ('WMT','Walmart','62.45','+0.21','market cap $503 B'),
    ('PG','Procter & Gamble','167.20','+0.45','market cap $394 B'),
    ('MA','Mastercard','452.89','+1.12','market cap $420 B'),
    ('UNH','UnitedHealth','526.43','-2.31','market cap $483 B'),
    ('HD','Home Depot','355.78','+1.32','market cap $354 B'),
    ('BAC','Bank of America','39.85','+0.18','market cap $314 B'),
    ('XOM','ExxonMobil','115.32','+0.78','market cap $462 B'),
    ('PFE','Pfizer','28.15','-0.21','market cap $159 B'),
    ('KO','Coca-Cola','62.50','+0.15','market cap $269 B'),
    ('PEP','PepsiCo','174.20','+0.34','market cap $239 B'),
    ('DIS','Disney','98.45','+1.23','market cap $179 B'),
    ('NFLX','Netflix','620.55','+8.45','market cap $266 B'),
    ('INTC','Intel','22.34','-0.45','market cap $94 B'),
    ('AMD','AMD','156.89','+2.16','market cap $253 B'),
    ('CSCO','Cisco','49.78','+0.12','market cap $200 B'),
    ('ORCL','Oracle','142.55','+0.85','market cap $392 B'),
    ('IBM','IBM','188.20','+0.34','market cap $173 B'),
    ('CRM','Salesforce','280.16','+1.78','market cap $271 B'),
    ('ADBE','Adobe','490.50','+2.32','market cap $217 B'),
    ('NKE','Nike','78.20','-0.45','market cap $116 B'),
    ('MCD','McDonald\'s','275.40','+0.55','market cap $198 B'),
    ('SBUX','Starbucks','82.30','-0.21','market cap $93 B'),
    ('COST','Costco','870.55','+3.42','market cap $387 B'),
    ('CVX','Chevron','155.20','+0.45','market cap $292 B'),
    ('LMT','Lockheed Martin','455.30','+1.18','market cap $109 B'),
    ('GS','Goldman Sachs','488.55','+1.78','market cap $158 B'),
    ('MS','Morgan Stanley','100.42','+0.32','market cap $164 B'),
    ('CAT','Caterpillar','345.20','+2.45','market cap $170 B'),
    ('BA','Boeing','175.50','-1.25','market cap $107 B'),
]
for sym, name, price, chg, cap in STOCKS:
    q = f"{sym} stock price"
    chg_s = "+" if chg.startswith('+') else "-"
    E(q, f"NYSE/NASDAQ:{sym}",
      f"{name} ({sym}) — ${price} ({chg}) — {cap}",
      "society-and-culture", "finance",
      f"stock {sym} {name.lower()}",
      [f"{sym} historical chart"], "stock-markets")

# Population (20)
POP_PLACES = [
    ('Tokyo','37.4 million metro (2023)'),
    ('Delhi','32.9 million metro (2023)'),
    ('Shanghai','29.2 million metro (2023)'),
    ('Sao Paulo','22.8 million metro'),
    ('Mexico City','22.3 million metro'),
    ('Cairo','22.2 million metro'),
    ('Mumbai','20.9 million metro'),
    ('Beijing','21.8 million metro'),
    ('Dhaka','22.0 million metro'),
    ('Osaka','19.0 million metro'),
    ('New York','19.8 million metro (≈8.3 M city)'),
    ('Karachi','17.0 million metro'),
    ('Buenos Aires','15.4 million metro'),
    ('Chongqing','17.0 million metro'),
    ('Istanbul','15.8 million metro'),
    ('Kolkata','15.6 million metro'),
    ('Manila','14.3 million metro'),
    ('Lagos','15.6 million metro'),
    ('Rio de Janeiro','13.7 million metro'),
    ('Tianjin','14.0 million metro'),
]
for city, pop in POP_PLACES:
    q = f"population of {city}"
    E(q, f"population[{city}]", pop,
      "society-and-culture", "geography",
      f"population city {city.lower()}",
      [f"{city} area"], "major-cities")

print(f"[r3] after world data: {len(EXTRA_RESULTS)}")

# --- (G) Step-by-step solutions — 80 ---
# These computation_results have multiple pods with step-by-step content
STEP_PROBLEMS = [
    ("solve 2x + 5 = 13 step by step",
     "2x + 5 = 13",
     "x = 4",
     [
        ("Step 1 - Subtract 5", "2x + 5 - 5 = 13 - 5"),
        ("Step 2 - Simplify",   "2x = 8"),
        ("Step 3 - Divide by 2", "x = 4"),
     ],
     "algebra"),
    ("solve 3x - 7 = 14 step by step",
     "3x - 7 = 14",
     "x = 7",
     [
        ("Step 1 - Add 7",      "3x - 7 + 7 = 14 + 7"),
        ("Step 2 - Simplify",   "3x = 21"),
        ("Step 3 - Divide by 3","x = 7"),
     ],
     "algebra"),
    ("solve 5x + 3 = 23 step by step",
     "5x + 3 = 23",
     "x = 4",
     [
        ("Step 1 - Subtract 3","5x = 20"),
        ("Step 2 - Divide by 5","x = 4"),
     ],
     "algebra"),
    ("factor x^2 - 5x + 6 step by step",
     "x^2 - 5x + 6",
     "(x - 2)(x - 3)",
     [
        ("Step 1 - Find roots","x = 2, x = 3 by Vieta or quadratic"),
        ("Step 2 - Write as factors","(x - 2)(x - 3)"),
     ],
     "algebra"),
    ("factor x^2 - 9 step by step",
     "x^2 - 9",
     "(x - 3)(x + 3)",
     [
        ("Step 1 - Recognize difference of squares","a² − b² with a=x, b=3"),
        ("Step 2 - Apply formula","(x − 3)(x + 3)"),
     ],
     "algebra"),
    ("solve x^2 - 4x + 3 = 0 step by step",
     "x^2 - 4x + 3 = 0",
     "x = 1 or x = 3",
     [
        ("Step 1 - Factor","(x − 1)(x − 3) = 0"),
        ("Step 2 - Zero product","x − 1 = 0 or x − 3 = 0"),
        ("Step 3 - Solve","x = 1 or x = 3"),
     ],
     "algebra"),
    ("solve 2x^2 - 8 = 0 step by step",
     "2x^2 - 8 = 0",
     "x = ±2",
     [
        ("Step 1 - Add 8","2x² = 8"),
        ("Step 2 - Divide by 2","x² = 4"),
        ("Step 3 - Square root","x = ±2"),
     ],
     "algebra"),
    ("solve quadratic x^2 + 5x + 6 = 0 step by step",
     "x^2 + 5x + 6 = 0",
     "x = -2 or x = -3",
     [
        ("Step 1 - Identify a,b,c","a=1, b=5, c=6"),
        ("Step 2 - Discriminant","Δ = 25 - 24 = 1"),
        ("Step 3 - Quadratic formula","x = (-5 ± 1)/2"),
        ("Step 4 - Roots","x = -2 or x = -3"),
     ],
     "algebra"),
    ("differentiate x^3 step by step",
     "d/dx [x^3]",
     "3 x^2",
     [
        ("Step 1 - Power rule","d/dx [x^n] = n x^(n-1)"),
        ("Step 2 - Apply n=3","3 x^(3-1) = 3 x^2"),
     ],
     "calculus"),
    ("differentiate sin(x) cos(x) step by step",
     "d/dx [sin(x) cos(x)]",
     "cos²(x) − sin²(x) = cos(2x)",
     [
        ("Step 1 - Product rule","f'g + fg'"),
        ("Step 2 - Compute","cos(x)cos(x) + sin(x)(-sin(x))"),
        ("Step 3 - Simplify","cos²(x) − sin²(x)"),
        ("Step 4 - Identity","= cos(2x)"),
     ],
     "calculus"),
    ("integrate x^2 step by step",
     "∫ x^2 dx",
     "x^3/3 + C",
     [
        ("Step 1 - Power rule","∫ x^n dx = x^(n+1)/(n+1) + C"),
        ("Step 2 - n=2","x^3/3 + C"),
     ],
     "calculus"),
    ("integrate sin(x) step by step",
     "∫ sin(x) dx",
     "-cos(x) + C",
     [
        ("Step 1 - Standard","∫ sin(x) dx = −cos(x) + C"),
     ],
     "calculus"),
    ("compute 25% of 80 step by step",
     "25% × 80",
     "20",
     [
        ("Step 1 - Convert percent","25% = 0.25"),
        ("Step 2 - Multiply","0.25 × 80 = 20"),
     ],
     "finance"),
    ("convert 5 km to miles step by step",
     "5 km → miles",
     "≈ 3.107 miles",
     [
        ("Step 1 - Conversion factor","1 km = 0.621371 mi"),
        ("Step 2 - Multiply","5 × 0.621371"),
        ("Step 3 - Result","≈ 3.1069 mi"),
     ],
     "units-measures"),
    ("convert 100 F to C step by step",
     "100 F → C",
     "37.78 °C",
     [
        ("Step 1 - Formula","C = (F − 32) × 5/9"),
        ("Step 2 - Substitute","(100 − 32) × 5/9"),
        ("Step 3 - Calculate","68 × 5/9 ≈ 37.78"),
     ],
     "units-measures"),
    ("solve 3(x - 2) = 12 step by step",
     "3(x-2) = 12",
     "x = 6",
     [
        ("Step 1 - Distribute","3x - 6 = 12"),
        ("Step 2 - Add 6","3x = 18"),
        ("Step 3 - Divide","x = 6"),
     ],
     "algebra"),
    ("simplify (x^2 - 4)/(x - 2) step by step",
     "(x^2 - 4)/(x - 2)",
     "x + 2 (with x ≠ 2)",
     [
        ("Step 1 - Factor numerator","(x − 2)(x + 2)"),
        ("Step 2 - Cancel common factor","x + 2 (x ≠ 2)"),
     ],
     "algebra"),
    ("compute mean {2,4,4,6,8,10} step by step",
     "mean of {2,4,4,6,8,10}",
     "5.667",
     [
        ("Step 1 - Sum","2+4+4+6+8+10 = 34"),
        ("Step 2 - Count","n = 6"),
        ("Step 3 - Divide","34/6 ≈ 5.667"),
     ],
     "statistics"),
    ("compute standard deviation {1,2,3,4,5} step by step",
     "σ of {1,2,3,4,5}",
     "σ ≈ 1.4142",
     [
        ("Step 1 - Mean","(1+2+3+4+5)/5 = 3"),
        ("Step 2 - Deviations²","4+1+0+1+4 = 10"),
        ("Step 3 - Variance","10/5 = 2"),
        ("Step 4 - σ","√2 ≈ 1.4142"),
     ],
     "statistics"),
    ("find slope between (1,2) and (5,10) step by step",
     "slope (1,2)(5,10)",
     "m = 2",
     [
        ("Step 1 - Formula","m = (y₂ − y₁)/(x₂ − x₁)"),
        ("Step 2 - Substitute","(10 − 2)/(5 − 1)"),
        ("Step 3 - Result","8/4 = 2"),
     ],
     "algebra"),
]
# duplicate 4× with slightly varied numbers to reach 80
STEP_BANK = list(STEP_PROBLEMS)
for k, base in enumerate(STEP_PROBLEMS[:20]):
    # variant: rename query slightly
    q, parsed, ans, steps, slug = base
    new_q = q.replace('step by step', 'with steps')
    STEP_BANK.append((new_q, parsed, ans, steps, slug))
# more numeric variants
for n in range(20):
    a = 2 + n
    b = 6 + n
    c = a * 3 + b
    q = f"solve {a}x + {b} = {c} step by step"
    parsed = f"{a}x + {b} = {c}"
    ans = f"x = 3"
    steps = [
        (f"Step 1 - Subtract {b}", f"{a}x = {c - b}"),
        (f"Step 2 - Divide by {a}", f"x = {(c - b) // a}"),
    ]
    STEP_BANK.append((q, parsed, ans, steps, "algebra"))
for n in range(20):
    a = 2 + n
    q = f"differentiate x^{a+1} step by step"
    parsed = f"d/dx [x^{a+1}]"
    ans = f"{a+1} x^{a}"
    steps = [
        ("Step 1 - Power rule", "d/dx [x^n] = n x^(n-1)"),
        (f"Step 2 - n={a+1}", f"{a+1} x^{a}"),
    ]
    STEP_BANK.append((q, parsed, ans, steps, "calculus"))

for q, parsed, ans, steps, slug in STEP_BANK:
    # build pods JSON manually so it carries multi-pod content
    pods = [{"title": "Input interpretation", "plaintext": parsed}]
    for stitle, scontent in steps:
        pods.append({"title": stitle, "plaintext": scontent})
    pods.append({"title": "Result", "plaintext": ans})
    pods.append({"title": "Step-by-step (Pro)", "plaintext": "Unlock complete step-by-step on Wolfram|Alpha Pro."})
    # Embed pods directly via E with a special handler: stuff JSON-encoded into 'related'
    # we'll handle "step" rows specially in the writer
    EXTRA_RESULTS.append(("__STEP__" + q, parsed, ans,
                          "mathematics", slug if slug in ('algebra','calculus','statistics') else 'algebra',
                          "step by step " + parsed.lower(),
                          pods,  # placeholder: store pods structure here
                          slug, ''))

print(f"[r3] after step-by-step: {len(EXTRA_RESULTS)}")

# --- (H) Image / audio inputs (50) ---
IMAGE_QS = [
    ("identify plant from image", "image[leaf shape, veins, color]", "Image-based plant ID requires Pro. Suggested: oak, maple, fern based on common shapes."),
    ("identify animal from photo", "image[fur, posture]", "Cat (likely Felis catus). Common breeds: domestic shorthair, Maine Coon, Siamese."),
    ("read math from image", "OCR(math handwriting)", "Detected: x^2 + 2x + 1. Solution: (x+1)^2."),
    ("identify constellation in night sky", "image[stars, position]", "Detected: Orion. Notable: Belt of 3 stars (Mintaka, Alnilam, Alnitak)."),
    ("identify food from image", "image[shape, color]", "Detected: pizza slice. Estimated 285 kcal/slice."),
    ("identify chemical structure", "image[atoms, bonds]", "Detected: benzene ring (C6H6). Aromatic; common in many drugs."),
    ("identify musical notation from image", "OCR(staff)", "Detected: C major scale, treble clef."),
    ("identify dog breed from image", "image[breed features]", "Suggested: Golden Retriever. Lifespan 10–12 years; weight 25–34 kg."),
    ("identify bird from image", "image[plumage, beak]", "Suggested: American Robin (Turdus migratorius). Common N. America."),
    ("identify rock from image", "image[texture, color]", "Suggested: granite. Igneous, composed of quartz, feldspar, mica."),
    ("identify fingerprint pattern", "image[ridge pattern]", "Detected: loop pattern. ~65% of fingerprints."),
    ("read license plate from image", "OCR(alphanumeric)", "Detected: 'ABC-1234'. Format suggests US state plate."),
    ("identify currency from image", "image[design, denomination]", "Detected: 100 USD note (Benjamin Franklin)."),
    ("identify logo from image", "image[brand mark]", "Trademark image lookup unavailable in this mirror; example: Apple, Nike, Google."),
    ("count objects in image", "image[discrete objects]", "Estimated: 12 distinct objects detected (people, animals, items)."),
    ("identify gemstone from image", "image[crystal, color, cut]", "Suggested: emerald. Cubic, green; Mohs ≈ 7.5–8."),
    ("identify mushroom from image", "image[cap, gills, stem]", "Suggested: Agaricus bisporus (common button mushroom). NOT for raw foraging guidance."),
    ("identify insect from image", "image[legs, wings, body]", "Suggested: honey bee (Apis mellifera). 6 legs, 2 wing pairs, fuzzy body."),
    ("identify cloud type", "image[cloud shape]", "Suggested: cumulonimbus. Thunderstorm-producing; reaches stratosphere."),
    ("read barcode", "image[barcode bars]", "Detected: UPC-A '012345678905'. Standard US grocery code."),
]
for q, parsed, ans in IMAGE_QS:
    E(q, parsed, ans,
      "science-and-technology", "computer-science",
      "image input " + q[:30].lower(),
      [], "machine-learning")

AUDIO_QS = [
    ("identify song from audio clip", "audio[melody, tempo]", "Audio fingerprinting requires Pro. Suggested format: 15-30 sec clip."),
    ("identify bird call", "audio[frequency, pattern]", "Suggested: American Robin (carolling pattern, 2 kHz peak)."),
    ("transcribe audio to text", "audio[speech]", "Transcription requires Pro. Standard format: WAV/MP3."),
    ("identify musical key from audio", "audio[pitch class]", "Suggested: C major (most common in pop). Verify via chord analysis."),
    ("detect tempo BPM from audio", "audio[beat detection]", "Estimated tempo: 120 BPM (common pop/dance range)."),
    ("identify language spoken", "audio[phonemes]", "Suggested: English (American). Accent: Midwest US."),
    ("analyze speech frequency", "audio[FFT]", "Typical voice range: 85–255 Hz (male), 165–255 Hz (female)."),
    ("identify instrument", "audio[timbre]", "Suggested: piano (broad harmonic series, sharp attack)."),
    ("noise level dB", "audio[amplitude]", "Estimated: 65 dB (conversational)."),
    ("identify alarm sound", "audio[pattern]", "Suggested: smoke alarm (continuous 3-beep pattern, 3.2 kHz)."),
    ("audio FFT spectrum", "audio[FFT]", "Returns frequency-magnitude plot. Peaks indicate dominant frequencies."),
    ("identify accent in speech", "audio[phonetics]", "Suggested: British (Received Pronunciation). Confidence 72%."),
    ("estimate room reverberation", "audio[RT60]", "Estimated: 0.5 s (typical living room). Long for concert hall (1.5–2 s)."),
    ("audio signal-to-noise ratio", "audio[SNR]", "Typical SNR: 50–60 dB (good recording); 30 dB (acceptable)."),
    ("identify gunshot from audio", "audio[transient]", "Sharp impulse, 140–175 dB peak; broad spectrum."),
    ("baby cry vs adult speech", "audio[fundamental]", "Baby cry: 300–600 Hz fundamental; adult speech: 80–250 Hz."),
    ("siren type emergency", "audio[pattern]", "Possibilities: yelp, wail, hi-lo, electronic (varies by service)."),
    ("identify whale song", "audio[low frequency]", "Suggested: humpback whale (20 Hz – 9 kHz, structured song)."),
    ("convert audio to MIDI", "audio→MIDI", "Pro feature: pitch tracking + onset detection produces MIDI events."),
    ("analyze song chord progression", "audio[harmonic]", "Detected I-V-vi-IV (very common in pop, '4-chord song')."),
    ("frequency of pure tone 440Hz", "audio[440 Hz]", "A4 = 440 Hz (concert pitch, ISO 16)."),
    ("frequency 60Hz hum", "audio[60 Hz]", "Power-line hum (60 Hz in US; 50 Hz in EU)."),
    ("estimate audio duration", "audio[length]", "Standard pop song: 3–4 min; classical symphony: 30–60 min."),
    ("identify dialect Spanish", "audio[phonemes]", "Suggested: Castilian Spanish (vs Latin American). 'th' sound for c/z."),
    ("emergency siren US vs Europe", "audio[pattern]", "US: yelp/wail; Europe: bi-tonal (e.g., 'two-tone' nee-naw)."),
    ("voice male vs female", "audio[fundamental]", "Male: 85–180 Hz; female: 165–255 Hz fundamental."),
    ("audio waveform shape", "audio[waveform]", "Sine, square, triangle, sawtooth — fundamental shapes in synthesis."),
    ("classify music genre", "audio[features]", "Returns: pop, rock, classical, jazz, electronic, hip-hop probabilities."),
    ("identify dog bark vs howl", "audio[envelope]", "Bark: short impulses; howl: long sustained tones."),
    ("frequency of middle C", "audio[C4]", "261.626 Hz (equal temperament)."),
]
for q, parsed, ans in AUDIO_QS:
    E(q, parsed, ans,
      "science-and-technology", "computer-science",
      "audio input " + q[:30].lower(),
      [], "machine-learning")

print(f"[r3] after image/audio: {len(EXTRA_RESULTS)}")

# --- (I) Finance / sports / drugs / music / linguistics fact rows (300) ---

# More stock/finance
FIN_EXTRA = [
    ("dividend yield MSFT", "0.73% TTM"),
    ("dividend yield JNJ", "3.05% TTM"),
    ("dividend yield XOM", "3.40% TTM"),
    ("PE ratio AAPL", "27.5 (TTM)"),
    ("PE ratio MSFT", "33.8 (TTM)"),
    ("PE ratio TSLA", "62.4 (TTM)"),
    ("PE ratio S&P 500 average", "≈ 22 (long-term mean ≈ 16)"),
    ("EBITDA margin Apple", "≈ 32%"),
    ("free cash flow Microsoft 2023", "≈ $59 B"),
    ("Sharpe ratio definition", "(return − risk-free) / σ"),
    ("Sortino ratio definition", "(return − target)/downside σ"),
    ("Treynor ratio", "(return − risk-free)/β"),
    ("Jensen's alpha", "actual return − CAPM expected"),
    ("CAPM formula", "E[R] = R_f + β (R_m − R_f)"),
    ("WACC formula", "(E/V)·Re + (D/V)·Rd·(1−Tc)"),
    ("Black-Scholes put", "P = K e^(−rT) N(−d2) − S N(−d1)"),
    ("Black-Scholes d1", "(ln(S/K) + (r + σ²/2)T)/(σ√T)"),
    ("annuity present value", "PV = PMT × (1 − (1+r)^−n)/r"),
    ("annuity future value", "FV = PMT × ((1+r)^n − 1)/r"),
    ("loan amortization formula", "M = P r(1+r)^n / ((1+r)^n − 1)"),
    ("Rule of 72 doubling time", "≈ 72/r years"),
    ("Rule of 114 tripling time", "≈ 114/r years"),
    ("S&P 500 historical CAGR 30yr", "≈ 9.7%"),
    ("Nasdaq Composite 10yr CAGR", "≈ 14.5%"),
    ("US gov bond 10yr 30yr CAGR", "≈ 4–5%"),
    ("inflation US average 100yr", "≈ 3.2% annual"),
    ("inflation US 1970-1979", "≈ 7.4% annual"),
    ("inflation US 2010-2019", "≈ 1.8% annual"),
    ("FAANG companies", "Facebook (Meta), Apple, Amazon, Netflix, Google (Alphabet)"),
    ("Big Tech market cap top 5", "Apple, Microsoft, Alphabet, Amazon, Nvidia — combined ~$10+ T"),
]
for q, ans in FIN_EXTRA:
    E(q, q, ans,
      "society-and-culture", "finance",
      f"finance {q[:30].lower()}",
      [], "stock-markets")

# Sports records
SPORTS_FACTS = [
    ("Wimbledon men 2023 winner","Carlos Alcaraz"),
    ("US Open women 2023 winner","Coco Gauff"),
    ("Australian Open 2024 men","Jannik Sinner"),
    ("French Open 2024 men","Carlos Alcaraz"),
    ("Super Bowl LVIII winner","Kansas City Chiefs"),
    ("Super Bowl LVII winner","Kansas City Chiefs"),
    ("NBA Finals 2024 winner","Boston Celtics"),
    ("NBA Finals 2023 winner","Denver Nuggets"),
    ("World Series 2023 winner","Texas Rangers"),
    ("World Series 2022 winner","Houston Astros"),
    ("Stanley Cup 2024 winner","Florida Panthers"),
    ("Stanley Cup 2023 winner","Vegas Golden Knights"),
    ("WNBA Finals 2023 winner","Las Vegas Aces"),
    ("Champions League 2023-24 winner","Real Madrid"),
    ("Premier League 2023-24 champion","Manchester City"),
    ("La Liga 2023-24 champion","Real Madrid"),
    ("Bundesliga 2023-24 champion","Bayer Leverkusen"),
    ("Serie A 2023-24 champion","Inter Milan"),
    ("Ligue 1 2023-24 champion","Paris Saint-Germain"),
    ("Copa America 2024 winner","Argentina"),
    ("Euro 2024 winner","Spain"),
    ("Cricket World Cup 2023 winner","Australia"),
    ("Rugby World Cup 2023 winner","South Africa"),
    ("Tour de France 2024 winner","Tadej Pogačar"),
    ("Masters 2024 winner","Scottie Scheffler"),
    ("PGA Championship 2024 winner","Xander Schauffele"),
    ("US Open Golf 2024 winner","Bryson DeChambeau"),
    ("Open Championship 2024 winner","Xander Schauffele"),
    ("Indianapolis 500 2024 winner","Josef Newgarden"),
    ("Daytona 500 2024 winner","William Byron"),
    ("Kentucky Derby 2024 winner","Mystik Dan"),
    ("Olympic 100m gold 2024","Noah Lyles"),
    ("Olympic 200m gold 2024","Letsile Tebogo"),
    ("most gymnastics medals Simone Biles","11 Olympic medals total (7 gold)"),
    ("most NHL goals Wayne Gretzky","894 career"),
    ("most NHL points","Wayne Gretzky — 2857"),
    ("Pelé career goals official","~767 (FIFA recognized)"),
    ("most ATP Grand Slams","Novak Djokovic — 24"),
    ("most WTA Grand Slams open era","Serena Williams — 23"),
    ("most NBA MVP awards","Kareem Abdul-Jabbar — 6"),
]
for q, ans in SPORTS_FACTS:
    E(q, q, ans,
      "society-and-culture", "sports-society",
      f"sport fact {q[:30].lower()}",
      [], "olympics-records")

# Drug facts
DRUG_FACTS = [
    ("ibuprofen common doses","200, 400, 600, 800 mg"),
    ("acetaminophen brand names","Tylenol, Panadol; generic paracetamol"),
    ("aspirin daily low dose","81 mg (cardiovascular prevention)"),
    ("amoxicillin typical dose","500 mg every 8h adult"),
    ("metformin typical dose","500–1000 mg twice daily"),
    ("lisinopril typical dose","10–40 mg daily"),
    ("atorvastatin typical dose","10–80 mg daily"),
    ("simvastatin typical dose","5–40 mg daily"),
    ("omeprazole typical dose","20 mg daily"),
    ("amlodipine typical dose","5–10 mg daily"),
    ("sertraline typical dose","50–200 mg daily"),
    ("fluoxetine typical dose","20–80 mg daily"),
    ("escitalopram typical dose","10–20 mg daily"),
    ("hydrochlorothiazide dose","12.5–50 mg daily"),
    ("metoprolol dose","25–100 mg twice daily"),
    ("losartan dose","25–100 mg daily"),
    ("warfarin INR target","2–3 (atrial fibrillation, DVT)"),
    ("levothyroxine dose","Weight-based; ~1.6 µg/kg/day"),
    ("insulin types","Rapid, short, intermediate, long-acting"),
    ("metoclopramide dose","10 mg every 6h (max 5 days)"),
    ("ondansetron dose","4–8 mg every 8h for nausea"),
    ("ciprofloxacin dose","500 mg every 12h"),
    ("doxycycline dose","100 mg twice daily"),
    ("azithromycin Z-pack","500 mg day 1, 250 mg days 2-5"),
    ("ranitidine status","Withdrawn (NDMA contamination)"),
    ("loratadine dose","10 mg once daily"),
    ("cetirizine dose","10 mg once daily"),
    ("diphenhydramine dose","25–50 mg every 6h"),
    ("prednisone taper","Standard varies; e.g., 40-30-20-10-5 mg over 5+ days"),
    ("naproxen dose","220–500 mg every 12h"),
]
for q, ans in DRUG_FACTS:
    E(q, q, ans,
      "everyday-life", "personal-health",
      f"drug fact {q[:30].lower()}",
      [], "medications")

# Music theory facts
MUSIC_FACTS = [
    ("C major scale notes","C D E F G A B"),
    ("D major scale notes","D E F# G A B C#"),
    ("E major scale notes","E F# G# A B C# D#"),
    ("F major scale notes","F G A Bb C D E"),
    ("G major scale notes","G A B C D E F#"),
    ("A major scale notes","A B C# D E F# G#"),
    ("B major scale notes","B C# D# E F# G# A#"),
    ("C minor natural notes","C D Eb F G Ab Bb"),
    ("D minor natural notes","D E F G A Bb C"),
    ("A minor natural notes","A B C D E F G"),
    ("E minor natural notes","E F# G A B C D"),
    ("circle of fifths order","C G D A E B F# C# G# D# A# F"),
    ("major chord intervals","root, major 3rd, perfect 5th"),
    ("minor chord intervals","root, minor 3rd, perfect 5th"),
    ("diminished chord intervals","root, minor 3rd, diminished 5th"),
    ("augmented chord intervals","root, major 3rd, augmented 5th"),
    ("dominant 7th chord","root, M3, P5, m7"),
    ("major 7th chord","root, M3, P5, M7"),
    ("minor 7th chord","root, m3, P5, m7"),
    ("perfect fifth semitones","7"),
    ("major third semitones","4"),
    ("minor third semitones","3"),
    ("octave semitones","12"),
    ("Picardy third","Final minor-key chord with major 3rd"),
    ("V-I cadence","Authentic cadence; strongest resolution"),
    ("IV-I cadence","Plagal cadence; 'Amen' cadence"),
    ("relative minor of C major","A minor"),
    ("parallel minor of C major","C minor"),
    ("Mixolydian mode","Major scale with lowered 7th"),
    ("Locrian mode","Diatonic mode starting on the 7th degree"),
]
for q, ans in MUSIC_FACTS:
    E(q, q, ans,
      "everyday-life", "music-audio",
      f"music theory {q[:30].lower()}",
      [], "musical-scales")

# Linguistics facts
LING_FACTS = [
    ("hello in French","Bonjour"),
    ("hello in German","Hallo / Guten Tag"),
    ("hello in Italian","Ciao / Salve"),
    ("hello in Mandarin","你好 (nǐ hǎo)"),
    ("hello in Russian","Здравствуйте (Zdravstvuyte)"),
    ("hello in Arabic","مرحبا (marhaba)"),
    ("hello in Korean","안녕하세요 (annyeonghaseyo)"),
    ("hello in Hindi","नमस्ते (namaste)"),
    ("hello in Portuguese","Olá / Bom dia"),
    ("hello in Dutch","Hallo / Goedendag"),
    ("hello in Swedish","Hej"),
    ("hello in Greek","Γεια σου (Yia sou)"),
    ("hello in Turkish","Merhaba"),
    ("hello in Vietnamese","Xin chào"),
    ("hello in Thai","สวัสดี (sawatdi)"),
    ("thank you in French","Merci"),
    ("thank you in German","Danke"),
    ("thank you in Spanish","Gracias"),
    ("thank you in Italian","Grazie"),
    ("thank you in Mandarin","谢谢 (xièxie)"),
    ("thank you in Korean","감사합니다 (gamsahamnida)"),
    ("thank you in Russian","Спасибо (spasibo)"),
    ("yes in Mandarin","是 (shì)"),
    ("no in Mandarin","不 (bù)"),
    ("number 1 in Japanese","一 (ichi)"),
    ("number 2 in Japanese","二 (ni)"),
    ("number 3 in Japanese","三 (san)"),
    ("good morning in Spanish","Buenos días"),
    ("good night in French","Bonne nuit"),
    ("goodbye in Italian","Arrivederci"),
]
for q, ans in LING_FACTS:
    E(q, q, ans,
      "society-and-culture", "linguistics",
      f"translation {q[:30].lower()}",
      [], "translation-pairs")

# Astronomy more facts
ASTRO_FACTS = [
    ("distance Earth to Sun","1 AU = 149,597,870.7 km"),
    ("distance Earth to Moon","384,400 km (average)"),
    ("distance Sun to Proxima Centauri","4.24 light-years"),
    ("distance Milky Way center","≈ 26,000 light-years (8 kpc)"),
    ("diameter Mercury","4879 km"),
    ("diameter Venus","12,104 km"),
    ("diameter Earth","12,742 km (mean)"),
    ("diameter Mars","6779 km"),
    ("diameter Jupiter","139,820 km"),
    ("diameter Saturn","116,460 km"),
    ("diameter Uranus","50,724 km"),
    ("diameter Neptune","49,244 km"),
    ("mass Earth","5.972 × 10²⁴ kg"),
    ("mass Sun","1.989 × 10³⁰ kg"),
    ("mass Jupiter","1.898 × 10²⁷ kg"),
    ("orbital period Earth","365.256 days"),
    ("orbital period Mercury","87.97 days"),
    ("orbital period Venus","224.7 days"),
    ("orbital period Mars","687 days"),
    ("orbital period Jupiter","11.86 years"),
    ("rotation period Earth","23h 56m 4.1s (sidereal)"),
    ("rotation period Jupiter","9h 55m 30s"),
    ("rotation period Venus","243 days (retrograde)"),
    ("temperature Sun core","≈ 15.7 million K"),
    ("temperature Sun surface","≈ 5772 K"),
    ("number planets","8 (Pluto reclassified 2006)"),
    ("number Jupiter moons","95 confirmed (as of 2024)"),
    ("number Saturn rings","≈ 7 major (A, B, C, D, E, F, G)"),
    ("escape velocity Mars","5.03 km/s"),
    ("first satellite orbit","Sputnik 1, October 4, 1957"),
]
for q, ans in ASTRO_FACTS:
    E(q, q, ans,
      "science-and-technology", "astronomy",
      f"astronomy {q[:30].lower()}",
      [], "solar-system-bodies")

print(f"[r3] after fact rows: {len(EXTRA_RESULTS)}")

# --- (J) Math fillers to reach 1500+: factorizations, primes, sqrt, powers ---
# Factor numbers 420..600
def _factor(n):
    out, d = [], 2
    while d*d <= n:
        while n % d == 0:
            out.append(d); n //= d
        d += 1
    if n > 1:
        out.append(n)
    from collections import Counter
    c = Counter(out)
    return " × ".join(f"{p}^{e}" if e > 1 else f"{p}" for p, e in sorted(c.items()))

for n in range(420, 600):
    E(f"factor {n}", str(n), f"{n} = {_factor(n)}",
      "mathematics", "number-theory",
      f"factor {n}",
      [f"factor {n+1}"], "number-theory")

# More GCDs
GCD_R3 = [(a, b) for a in (12,18,24,36,48,60,72,84,96,108,120,144,168,180,210,252,360)
                  for b in (15,21,28,35,45,55,63,77,99,121,135,165,195,231)]
for a, b in GCD_R3:
    g = math.gcd(a, b)
    E(f"gcd({a},{b})", f"gcd[{a},{b}]", str(g),
      "mathematics", "number-theory",
      f"gcd r3 {a} {b}",
      [], "number-theory")

# Square roots 100..200 (selected)
for n in [100,101,103,107,109,113,121,127,131,137,139,144,149,151,157,163,
          167,169,173,179,181,191,193,196,197,199]:
    v = math.sqrt(n)
    E(f"sqrt({n})", f"√{n}", f"≈ {v:.10f}",
      "mathematics", "algebra",
      f"sqrt r3 {n}",
      [], "algebra")

# Higher powers
for a in [2,3,4,5,6,7,8]:
    for b in [10,12,14,16,18,20]:
        E(f"{a}^{b}", f"{a}^{b}", str(a**b),
          "mathematics", "algebra",
          f"pow r3 {a} {b}",
          [], "algebra")

# Logarithms
for n in [2,3,5,7,10,15,20,25,30,50,75,100,150,200,250,500,1000,5000,10000,100000]:
    E(f"log({n})", f"log10({n})", f"≈ {math.log10(n):.6f}",
      "mathematics", "algebra",
      f"log r3 {n}", [], "famous-constants")
    E(f"ln({n})", f"ln({n})", f"≈ {math.log(n):.6f}",
      "mathematics", "algebra",
      f"ln r3 {n}", [], "famous-constants")

# Trig angle values 0..180 step 15
TRIG_R3 = []
for deg in range(0, 361, 15):
    rad = math.radians(deg)
    TRIG_R3.append((f"sin({deg} degrees)", f"sin({deg}°)", f"{math.sin(rad):.6f}"))
    TRIG_R3.append((f"cos({deg} degrees)", f"cos({deg}°)", f"{math.cos(rad):.6f}"))
for q, parsed, ans in TRIG_R3:
    E(q, parsed, ans,
      "mathematics", "trigonometry",
      f"trig r3 {q.lower()}", [], "trigonometry")

print(f"[r3] total computation rows: {len(EXTRA_RESULTS)}")
assert len(EXTRA_RESULTS) >= 1500, f"need 1500+, got {len(EXTRA_RESULTS)}"


# ---------------------------------------------------------------------------
# (3) Feedback / notebook entry comment pools
# ---------------------------------------------------------------------------
FB_COMMENTS_R3 = [
    "Excellent reference — comprehensive coverage.",
    "Used this in my classroom; students engaged immediately.",
    "Compared three sources; this one was the most accurate.",
    "Layout makes it easy to scan results quickly.",
    "Great for prep before standardized exams.",
    "Saved this to my notebook for next week's lecture.",
    "Wish there were more step-by-step explanations — but data is solid.",
    "Top-tier authoritative content.",
    "Loved the related-queries feature; followed three links.",
    "Highly accurate; verified against published sources.",
    "Beats Googling — gets straight to the calculation.",
    "Crisp UI, fast response.",
    "Excellent for cross-referencing units and constants.",
    "Pro-quality data presentation.",
    "My students bookmark this for homework.",
    "Useful in my Materials Science research.",
    "Quick answers; very useful for clinical questions.",
    "Wolfram is unbeatable for symbolic manipulation.",
    "I keep coming back to this page.",
    "Perfect quick-reference card.",
]

NOTE_VARIANTS = [
    "Key reference for this domain.",
    "Cross-check this value with primary sources.",
    "Use in midterm prep.",
    "Bookmark for future research.",
    "Excellent quick-lookup.",
    "Compare to my hand calculation.",
    "Verified against published tables.",
    "Add this to the cheat sheet.",
    "Standard formula; worth memorizing.",
    "Useful for exam practice.",
]

# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------
def build():
    os.makedirs('instance', exist_ok=True)
    shutil.copyfile(SRC, DST)
    con = sqlite3.connect(DST)
    cur = con.cursor()

    cur.execute("SELECT COALESCE(MAX(id), 0) FROM topics");             next_topic = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM computation_results"); next_cr   = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM notebook_entries");    next_ne   = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM topic_feedback");      next_fb   = cur.fetchone()[0] + 1

    cur.execute("SELECT slug, id FROM categories");    cat_by_slug = dict(cur.fetchall())
    cur.execute("SELECT slug, id FROM subcategories"); sub_by_slug = dict(cur.fetchall())
    cur.execute("SELECT slug FROM topics");            existing_topic_slugs = set(r[0] for r in cur.fetchall())

    # ---- Topics ----
    for cat_slug, sub_slug, name, slug, desc, image, feat, new, examples_json in NEW_TOPICS:
        assert slug not in existing_topic_slugs, f"topic slug collides: {slug}"
        img_path = f"/static/images/topics/{image}"
        sub_id = sub_by_slug.get(sub_slug) if sub_slug else None
        cur.execute(
            "INSERT INTO topics(id, category_id, subcategory_id, name, slug, description, "
            "image, examples, is_featured, is_new, view_count, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (next_topic, cat_by_slug[cat_slug], sub_id, name, slug, desc, img_path,
             examples_json, int(feat), int(new), 0, ts(0)))
        next_topic += 1

    # ---- Computation results ----
    for i, row in enumerate(EXTRA_RESULTS):
        q, parsed, plain, cat, sub, kw, related, slug, plot_url = row
        # Step-by-step rows: q starts with __STEP__; related field carries pods list
        if isinstance(q, str) and q.startswith("__STEP__"):
            real_q = q[len("__STEP__"):]
            pods_list = related  # list of dicts
            pods_json = json.dumps(pods_list)
            rel_json = json.dumps([])
        else:
            real_q = q
            pods_struct = [
                {"title": "Input interpretation", "plaintext": parsed or real_q},
                {"title": "Result",                "plaintext": plain},
            ]
            pods_json = json.dumps(pods_struct)
            rel_json = json.dumps(related if isinstance(related, list) else [])

        cur.execute(
            "INSERT INTO computation_results("
            "id, input_query, parsed_input, plaintext, pods, category, subcategory, "
            "units, plot_url, related_queries, keywords, required_specifiers, "
            "topic_slug, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (next_cr, real_q, parsed, plain, pods_json, cat, sub, '',
             plot_url, rel_json, kw, '', slug, ts(i % 48)))
        next_cr += 1

    # ---- Notebook entries (300) ----
    cur.execute("SELECT id, title FROM notebooks ORDER BY id")
    notebooks = cur.fetchall()
    pool = EXTRA_RESULTS[:300]
    for i, row in enumerate(pool):
        q = row[0]
        if isinstance(q, str) and q.startswith("__STEP__"):
            q = q[len("__STEP__"):]
        plain = row[2]
        cat = row[3]
        sub = row[4]
        nb_id, _ = notebooks[i % len(notebooks)]
        cur.execute("SELECT COALESCE(MAX(sort_order), -1) FROM notebook_entries WHERE notebook_id=?",
                    (nb_id,))
        so = cur.fetchone()[0] + 1
        note = NOTE_VARIANTS[i % len(NOTE_VARIANTS)] + f" ({cat}/{sub})"
        cur.execute(
            "INSERT INTO notebook_entries(id, notebook_id, query_text, result_summary, "
            "notes, sort_order, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (next_ne, nb_id, q[:500], str(plain)[:200], note, so, ts(i % 48)))
        next_ne += 1

    # ---- Topic feedback (50) ----
    cur.execute("SELECT id FROM users ORDER BY id")
    user_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT id FROM topics ORDER BY id")
    all_topic_ids = [r[0] for r in cur.fetchall()]
    for i in range(50):
        uid = user_ids[(i * 3) % len(user_ids)]
        tid = all_topic_ids[(i * 7 + 11) % len(all_topic_ids)]
        rating = 3 + ((i * 5) % 3)
        helpful = 1 if rating >= 4 else 0
        comment = FB_COMMENTS_R3[i % len(FB_COMMENTS_R3)]
        cur.execute(
            "INSERT INTO topic_feedback(id, user_id, topic_id, rating, comment, "
            "is_helpful, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (next_fb, uid, tid, rating, comment, helpful, ts(i)))
        next_fb += 1

    con.commit()
    con.close()
    print(f"[r3] built {DST}")


if __name__ == "__main__":
    build()
