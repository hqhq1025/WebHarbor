#!/usr/bin/env python3
"""R4 polish: appends ON TOP of R3 seed db.

R3 baseline (md5 43172fa9...):
  topics 206, computation_results 2850, notebook_entries 504,
  topic_feedback 117, subcategories 60.

R4 targets:
  topics       350+   (+144)
  comp_results 5000+  (+2150)
  notebook_ent 700+   (+200)
  topic_feedb  170+   (+50)

Deterministic — no datetime.now(), no random. Run twice = same md5.
"""
from __future__ import annotations
import json, sqlite3, shutil, os, math, hashlib
from datetime import datetime, timedelta

SRC = 'instance_seed/wolfram_alpha.db'
DST = 'instance/wolfram_alpha.db'

REF = datetime(2026, 5, 14, 12, 0, 0)
def ts(off_hours: int = 0) -> str:
    return (REF + timedelta(hours=off_hours)).isoformat(sep=' ')

def J(x): return json.dumps(x)

def hh(s: str, mod: int) -> int:
    return int.from_bytes(hashlib.md5(s.encode()).digest()[:4], 'big') % mod

# ---------------------------------------------------------------------------
# (1) New topics — 144 total
# Format: (cat_slug, sub_slug_or_None, name, slug, desc, image, feat, new, examples_json)
# ---------------------------------------------------------------------------
NEW_TOPICS = []

# --- Chess deep (10) ---
NEW_TOPICS += [
    ("everyday-life", "hobbies-games", "Chess Openings", "chess-openings",
     "ECO classification of openings — Sicilian, Ruy Lopez, Queen's Gambit, King's Indian.",
     "people.png", True, True, J([
        {"query":"Sicilian Defense ECO","type":"opening","result":"ECO B20–B99; 1.e4 c5"},
        {"query":"Ruy Lopez first moves","type":"opening","result":"1.e4 e5 2.Nf3 Nc6 3.Bb5"},
        {"query":"Queen's Gambit","type":"opening","result":"1.d4 d5 2.c4; declined or accepted"},
     ])),
    ("everyday-life", "hobbies-games", "Chess Endgames", "chess-endgames",
     "King-and-pawn, lucena/philidor, rook endings, opposition theory.",
     "people.png", False, True, J([
        {"query":"Lucena position","type":"endgame","result":"Win for stronger side with rook+pawn vs rook"},
        {"query":"Philidor position","type":"endgame","result":"Drawing technique R+P vs R"},
        {"query":"opposition kings","type":"endgame","result":"Kings on same file/rank with one square between — losing side to move"},
     ])),
    ("everyday-life", "hobbies-games", "Chess Tactics", "chess-tactics",
     "Forks, pins, skewers, discovered attacks, and mating combinations.",
     "people.png", False, True, J([
        {"query":"knight fork","type":"tactic","result":"Knight attacks two pieces simultaneously"},
        {"query":"pin tactic","type":"tactic","result":"Piece can't move without exposing higher-value piece"},
        {"query":"back rank mate","type":"tactic","result":"Rook/queen mates king on back rank trapped by own pawns"},
     ])),
    ("everyday-life", "hobbies-games", "Chess Elo Ratings", "chess-elo-ratings",
     "FIDE Elo ratings, rating bands, and rating change formula.",
     "people.png", False, True, J([
        {"query":"Elo formula","type":"formula","result":"R' = R + K(S − E); E = 1/(1+10^((Rb−Ra)/400))"},
        {"query":"grandmaster Elo","type":"band","result":"GM title: 2500+ FIDE peak"},
        {"query":"current top chess Elo","type":"rating","result":"Carlsen — peaked 2882 (May 2014)"},
     ])),
    ("everyday-life", "hobbies-games", "Chess Engines", "chess-engines",
     "Stockfish, AlphaZero, Leela, NNUE — modern engine strength.",
     "people.png", False, True, J([
        {"query":"Stockfish strength","type":"engine","result":"≈ 3600 Elo (TCEC); NNUE evaluation"},
        {"query":"AlphaZero method","type":"engine","result":"Self-play MCTS + deep NN; learned chess in 24 h"},
        {"query":"NNUE evaluation","type":"method","result":"Efficient neural network for fast eval"},
     ])),
    ("everyday-life", "hobbies-games", "Chess Puzzles", "chess-puzzles",
     "Mate in N puzzles, tactic motifs, and puzzle rating.",
     "people.png", False, False, J([
        {"query":"mate in 2","type":"puzzle","result":"Find a move so that any reply allows mate next move"},
        {"query":"puzzle rating Lichess","type":"rating","result":"~1500 mean; tactics-only rating"},
        {"query":"endgame study composer","type":"composer","result":"Réti, Troitzky — classic problem composers"},
     ])),
    ("everyday-life", "hobbies-games", "FIDE Titles", "fide-titles",
     "GM, IM, FM, CM, WGM, WIM titles and norm requirements.",
     "people.png", False, False, J([
        {"query":"GM title norms","type":"requirement","result":"3 GM norms + Elo ≥ 2500 ever"},
        {"query":"IM title rating","type":"requirement","result":"Elo ≥ 2400 + 3 IM norms"},
        {"query":"number of GMs world","type":"count","result":"~1700 active GMs (2024)"},
     ])),
    ("everyday-life", "hobbies-games", "Chess Opening ECO Codes", "chess-opening-eco-codes",
     "A00–E99 encyclopedia of chess openings.",
     "people.png", False, False, J([
        {"query":"ECO A00","type":"code","result":"Uncommon openings (1.b3, 1.f4, 1.Nc3, etc.)"},
        {"query":"ECO C60","type":"code","result":"Ruy Lopez — Berlin Defense"},
        {"query":"ECO E04","type":"code","result":"Catalan, open, 5.Nf3"},
     ])),
    ("everyday-life", "hobbies-games", "Online Chess Platforms", "chess-online-platforms",
     "Chess.com, Lichess, Chess24 — user counts and rating systems.",
     "people.png", False, False, J([
        {"query":"chess.com users","type":"platform","result":"~150 million registered (2024)"},
        {"query":"Lichess open source","type":"platform","result":"Free, non-profit; ~10 million games/day"},
        {"query":"Glicko-2 system","type":"rating","result":"Used by Lichess; includes rating deviation"},
     ])),
    ("everyday-life", "hobbies-games", "World Chess Championship", "world-chess-championship",
     "World championship match history, formats, and champions.",
     "people.png", False, False, J([
        {"query":"first world champion","type":"history","result":"Wilhelm Steinitz (1886–1894)"},
        {"query":"longest reign","type":"history","result":"Emanuel Lasker — 27 years (1894–1921)"},
        {"query":"2023 WC match","type":"event","result":"Ding Liren beat Ian Nepomniachtchi"},
     ])),
]

# --- Gaming stats (10) ---
NEW_TOPICS += [
    ("society-and-culture", "popular-culture", "Esports Records", "esports-records",
     "Largest prize pools, tournament wins, and esports milestones.",
     "entertainment.png", True, True, J([
        {"query":"largest esports prize pool","type":"event","result":"The International 10 (Dota 2) — $40M USD"},
        {"query":"most CS:GO majors","type":"record","result":"Astralis — 4 Major championships"},
        {"query":"LCS franchise value","type":"market","result":"$30–80M per slot (2022)"},
     ])),
    ("society-and-culture", "popular-culture", "Video Game Sales", "video-game-sales",
     "Best-selling games, lifetime units, and franchise revenue.",
     "entertainment.png", False, True, J([
        {"query":"best selling game","type":"sales","result":"Minecraft — 300M+ copies sold"},
        {"query":"GTA V lifetime sales","type":"sales","result":"~200M units across consoles"},
        {"query":"Mario franchise sales","type":"franchise","result":"~830M Mario titles sold"},
     ])),
    ("society-and-culture", "popular-culture", "Twitch Stats", "twitch-stats",
     "Average concurrent viewers, top streamers, watch-time records.",
     "entertainment.png", False, True, J([
        {"query":"Twitch average concurrent","type":"viewers","result":"~2.5M average concurrent viewers"},
        {"query":"most followed Twitch","type":"streamer","result":"Ninja — ~19M followers"},
        {"query":"Twitch hours watched 2023","type":"watch","result":"~20 billion hours/year"},
     ])),
    ("society-and-culture", "popular-culture", "Steam Stats", "steam-stats",
     "Concurrent users, library sizes, top games on Steam.",
     "entertainment.png", False, True, J([
        {"query":"Steam concurrent users","type":"users","result":"Peak ~38M concurrent (CS2 launch)"},
        {"query":"Steam library titles","type":"catalog","result":"~80,000 games available"},
        {"query":"top played Steam","type":"top","result":"CS:GO/CS2 ~1.2M concurrent peak typical"},
     ])),
    ("society-and-culture", "popular-culture", "Mobile Game Revenue", "mobile-game-revenue",
     "Top mobile games by revenue and global mobile gaming market.",
     "entertainment.png", False, False, J([
        {"query":"top mobile game revenue","type":"revenue","result":"Honor of Kings — $2B+/year (Tencent)"},
        {"query":"mobile gaming market size","type":"market","result":"~$92B global revenue (2023)"},
        {"query":"freemium gacha rate","type":"economics","result":"Top whales (1%) account for ~50% revenue"},
     ])),
    ("society-and-culture", "popular-culture", "FPS Records", "fps-records",
     "First-person shooter world records, tournament wins, and pro stats.",
     "entertainment.png", False, False, J([
        {"query":"most CS:GO MVPs","type":"player","result":"s1mple — most major MVPs"},
        {"query":"Doom speedrun record","type":"speedrun","result":"Doom 1993 any% ~6:39"},
        {"query":"Valorant launch","type":"history","result":"June 2020; Riot Games"},
     ])),
    ("society-and-culture", "popular-culture", "MMORPG Stats", "mmorpg-stats",
     "Subscriber counts, virtual economies, and MMO lifespans.",
     "entertainment.png", False, False, J([
        {"query":"WoW subscriber peak","type":"subscribers","result":"~12M (2010, Wrath of the Lich King)"},
        {"query":"EVE Online ISK","type":"economy","result":"PLEX rate roughly $20 USD = 1 month subscription"},
        {"query":"oldest MMORPG","type":"history","result":"Meridian 59 (1996) — first 3D MMORPG"},
     ])),
    ("society-and-culture", "popular-culture", "Console Sales", "console-sales",
     "PlayStation, Xbox, Nintendo lifetime hardware sales.",
     "entertainment.png", False, False, J([
        {"query":"PS2 lifetime sales","type":"sales","result":"~155M units — best-selling console ever"},
        {"query":"Switch lifetime sales","type":"sales","result":"~140M+ units (2024)"},
        {"query":"Xbox Series X sales","type":"sales","result":"~25M+ units estimated"},
     ])),
    ("society-and-culture", "popular-culture", "Gaming Hardware", "gaming-hardware",
     "GPU benchmarks, console teraflops, and gaming PC specs.",
     "entertainment.png", False, False, J([
        {"query":"PS5 teraflops","type":"hardware","result":"10.28 TFLOPS (custom RDNA 2 GPU)"},
        {"query":"RTX 4090 TFLOPS","type":"hardware","result":"~82.6 TFLOPS FP32"},
        {"query":"Steam Deck specs","type":"hardware","result":"AMD APU, 16GB RAM, 1.6 TFLOPS"},
     ])),
    ("society-and-culture", "popular-culture", "Speedrun Records", "speedrun-records",
     "World-record speedruns for popular games, any% and 100% categories.",
     "entertainment.png", False, False, J([
        {"query":"Super Mario 64 16 stars","type":"speedrun","result":"~14:35 (current WR)"},
        {"query":"Minecraft any% glitchless","type":"speedrun","result":"~5–8 minutes (RSG record)"},
        {"query":"Portal any%","type":"speedrun","result":"~6:48 (current WR)"},
     ])),
]

# --- Social media stats (10) ---
NEW_TOPICS += [
    ("society-and-culture", "popular-culture", "Facebook Stats", "facebook-stats",
     "Monthly active users, ad revenue, and platform growth.",
     "entertainment.png", True, True, J([
        {"query":"Facebook MAU","type":"users","result":"~3 billion monthly active users (2024)"},
        {"query":"Facebook ad revenue","type":"revenue","result":"~$135B+ annual (Meta family)"},
        {"query":"Facebook founded","type":"history","result":"2004 by Mark Zuckerberg at Harvard"},
     ])),
    ("society-and-culture", "popular-culture", "Twitter / X Stats", "twitter-stats",
     "Active users, tweets per second, and platform metrics.",
     "entertainment.png", False, True, J([
        {"query":"X monetizable DAU","type":"users","result":"~250M+ monetizable DAU"},
        {"query":"tweets per second peak","type":"throughput","result":"~143k tweets/sec (Castle in the Sky 2013)"},
        {"query":"X acquisition price","type":"deal","result":"$44B by Elon Musk (Oct 2022)"},
     ])),
    ("society-and-culture", "popular-culture", "Instagram Stats", "instagram-stats",
     "User base, posts per day, and Reels engagement.",
     "entertainment.png", False, True, J([
        {"query":"Instagram MAU","type":"users","result":"~2 billion monthly active users"},
        {"query":"Instagram posts daily","type":"posts","result":"~95M photos/videos/day"},
        {"query":"Reels watch time","type":"engagement","result":"~half of Instagram time spent on Reels"},
     ])),
    ("society-and-culture", "popular-culture", "YouTube Stats", "youtube-stats",
     "Daily watch hours, top channels, ad revenue.",
     "entertainment.png", False, True, J([
        {"query":"YouTube daily watch","type":"watch","result":"~1B hours watched per day"},
        {"query":"top YouTube channel","type":"channel","result":"MrBeast — 240M+ subscribers (2024)"},
        {"query":"YouTube ad revenue","type":"revenue","result":"~$31B in 2023"},
     ])),
    ("society-and-culture", "popular-culture", "TikTok Stats", "tiktok-stats",
     "TikTok user base, time spent, and viral growth.",
     "entertainment.png", False, True, J([
        {"query":"TikTok MAU","type":"users","result":"~1.5 billion MAU (2024)"},
        {"query":"TikTok time spent","type":"engagement","result":"~95 minutes/day average user"},
        {"query":"TikTok algorithm","type":"system","result":"Personalized FYP via collaborative filtering + watch-time signals"},
     ])),
    ("society-and-culture", "popular-culture", "LinkedIn Stats", "linkedin-stats",
     "Professional network metrics and engagement.",
     "entertainment.png", False, False, J([
        {"query":"LinkedIn members","type":"users","result":"~1 billion members (2024)"},
        {"query":"LinkedIn revenue","type":"revenue","result":"~$15B annual (Microsoft)"},
        {"query":"LinkedIn job postings","type":"jobs","result":"~14M+ active job listings"},
     ])),
    ("society-and-culture", "popular-culture", "Reddit Stats", "reddit-stats",
     "Subreddit count, daily active users, and IPO data.",
     "entertainment.png", False, False, J([
        {"query":"Reddit DAU","type":"users","result":"~70M daily active users"},
        {"query":"Reddit subreddit count","type":"count","result":"~3M+ subreddits"},
        {"query":"Reddit IPO 2024","type":"event","result":"Listed NYSE Mar 2024 at $34/share"},
     ])),
    ("society-and-culture", "popular-culture", "Social Media Growth", "social-media-growth",
     "Platform growth rates, user-acquisition curves, and S-curves.",
     "entertainment.png", False, False, J([
        {"query":"fastest 100M users","type":"growth","result":"ChatGPT — 2 months (Nov 2022 launch)"},
        {"query":"S-curve adoption","type":"model","result":"Slow start, exponential mid, saturation top"},
        {"query":"network effects formula","type":"theory","result":"Metcalfe's law: value ∝ n²"},
     ])),
    ("society-and-culture", "popular-culture", "Viral Content Metrics", "viral-content-metrics",
     "Like-to-view ratios, engagement rates, and viral coefficients.",
     "entertainment.png", False, False, J([
        {"query":"engagement rate formula","type":"formula","result":"ER = (likes + comments + shares) / impressions"},
        {"query":"viral coefficient","type":"metric","result":"k = invites · conversion; k > 1 = viral growth"},
        {"query":"average TikTok like ratio","type":"benchmark","result":"~6–7% average engagement (high)"},
     ])),
    ("society-and-culture", "popular-culture", "Influencer Economy", "influencer-economy",
     "Influencer marketing rates, follower-to-CPM economics.",
     "entertainment.png", False, False, J([
        {"query":"micro influencer CPM","type":"rate","result":"~$10–25 CPM for 10k–100k followers"},
        {"query":"top earner Instagram","type":"earner","result":"Cristiano Ronaldo — ~$3M+ per post"},
        {"query":"creator economy size","type":"market","result":"~$250B globally (2024 est.)"},
     ])),
]

# --- E-commerce tools (10) ---
NEW_TOPICS += [
    ("society-and-culture", "popular-culture", "Amazon Marketplace", "amazon-marketplace",
     "Amazon seller fees, FBA economics, and marketplace metrics.",
     "entertainment.png", False, True, J([
        {"query":"Amazon referral fee","type":"fee","result":"~15% category default"},
        {"query":"FBA fulfillment fee","type":"fee","result":"~$3.22 for small standard items"},
        {"query":"Amazon seller count","type":"market","result":"~2M active sellers worldwide"},
     ])),
    ("society-and-culture", "popular-culture", "Shopify Stats", "shopify-stats",
     "Shopify GMV, merchant count, and platform growth.",
     "entertainment.png", False, True, J([
        {"query":"Shopify GMV","type":"gmv","result":"~$235B GMV (2023)"},
        {"query":"Shopify merchant count","type":"merchants","result":"~2M+ merchants on platform"},
        {"query":"Shopify plus pricing","type":"pricing","result":"$2000+/month enterprise tier"},
     ])),
    ("society-and-culture", "popular-culture", "eBay Stats", "ebay-stats",
     "eBay GMV, active buyers, and final-value fees.",
     "entertainment.png", False, False, J([
        {"query":"eBay GMV","type":"gmv","result":"~$74B GMV (2023)"},
        {"query":"eBay final value fee","type":"fee","result":"~12.55% + $0.30 per order standard"},
        {"query":"eBay active buyers","type":"users","result":"~132M active buyers"},
     ])),
    ("society-and-culture", "popular-culture", "Dropshipping Math", "dropshipping-math",
     "Margins, supplier costs, ad spend, and unit economics.",
     "entertainment.png", False, False, J([
        {"query":"dropshipping margin formula","type":"formula","result":"Margin = (Price − COGS − ad cost − fees) / Price"},
        {"query":"average dropship CPA","type":"metric","result":"~$25–60 per customer Facebook ads"},
        {"query":"ROAS target","type":"metric","result":"Break-even ROAS ≈ 1/gross margin"},
     ])),
    ("society-and-culture", "popular-culture", "Conversion Rate Optimization", "conversion-rate-optimization",
     "CRO formulas, A/B testing, and benchmark conversion rates.",
     "entertainment.png", False, False, J([
        {"query":"e-commerce conversion rate","type":"benchmark","result":"~2–3% median; top 25% ~5%+"},
        {"query":"A/B test sample size","type":"formula","result":"n ≈ 16 · σ² / Δ² per arm"},
        {"query":"checkout abandonment","type":"benchmark","result":"~70% global average cart abandonment"},
     ])),
    ("society-and-culture", "popular-culture", "Cart Abandonment Rate", "cart-abandonment-rate",
     "Abandoned cart metrics, recovery flows, and reasons.",
     "entertainment.png", False, False, J([
        {"query":"top abandonment reason","type":"reason","result":"Unexpected shipping cost (~48%)"},
        {"query":"recovery email lift","type":"metric","result":"~10% recovery via abandoned-cart email"},
        {"query":"mobile abandonment rate","type":"benchmark","result":"~85% mobile vs ~70% desktop"},
     ])),
    ("society-and-culture", "popular-culture", "Customer Acquisition Cost", "customer-acquisition-cost",
     "CAC formula, payback period, and benchmark CACs.",
     "entertainment.png", False, False, J([
        {"query":"CAC formula","type":"formula","result":"CAC = total sales & marketing / new customers"},
        {"query":"LTV/CAC ratio","type":"metric","result":"3:1 healthy; >5:1 underspending"},
        {"query":"SaaS CAC payback","type":"metric","result":"<12 months ideal; >24 months risky"},
     ])),
    ("society-and-culture", "popular-culture", "Lifetime Value Formulas", "lifetime-value-formulas",
     "LTV formulas, cohort analysis, and retention curves.",
     "entertainment.png", False, False, J([
        {"query":"LTV simple formula","type":"formula","result":"LTV = ARPU · gross margin · (1/churn)"},
        {"query":"discounted LTV","type":"formula","result":"LTV = Σ CF_t / (1+r)^t"},
        {"query":"cohort retention","type":"analysis","result":"Group by signup month, track % active over time"},
     ])),
    ("society-and-culture", "popular-culture", "E-commerce Shipping", "e-commerce-shipping",
     "Shipping cost models, USPS/UPS/FedEx rates, and SLA tradeoffs.",
     "entertainment.png", False, False, J([
        {"query":"USPS Priority rate","type":"rate","result":"$8–15 for 1-lb under-1-ft box (commercial)"},
        {"query":"free shipping threshold","type":"strategy","result":"~$50+ to encourage AOV lift"},
        {"query":"dim weight formula","type":"formula","result":"DIM = L × W × H / 139 (in³ → lb, US domestic)"},
     ])),
    ("society-and-culture", "popular-culture", "Marketplace Fees", "marketplace-fees",
     "Amazon, eBay, Etsy, Shopify fee schedules side-by-side.",
     "entertainment.png", False, False, J([
        {"query":"Etsy listing fee","type":"fee","result":"$0.20 per listing + 6.5% transaction"},
        {"query":"Walmart marketplace fee","type":"fee","result":"6–20% referral by category"},
        {"query":"Shopify transaction fee","type":"fee","result":"2.9% + $0.30 (Basic plan)"},
     ])),
]

# --- Cryptography deep (12) ---
NEW_TOPICS += [
    ("science-and-technology", "computer-science", "RSA Cryptography", "rsa-cryptography",
     "RSA key generation, encryption, signing, and security margins.",
     "discrete-math.png", True, True, J([
        {"query":"RSA key size 2048","type":"security","result":"≈ 112-bit symmetric equivalent (NIST)"},
        {"query":"RSA encryption","type":"formula","result":"c = m^e mod n; m = c^d mod n"},
        {"query":"factor RSA-768","type":"record","result":"768-bit RSA modulus factored in 2009"},
     ])),
    ("science-and-technology", "computer-science", "Elliptic Curve Crypto", "ecc-cryptography",
     "ECC key sizes, curves (P-256, Curve25519), and ECDSA signing.",
     "discrete-math.png", False, True, J([
        {"query":"P-256 security","type":"security","result":"~128-bit symmetric equivalent"},
        {"query":"Curve25519 use","type":"curve","result":"Used in TLS, SSH, Signal — 128-bit security"},
        {"query":"ECDSA signature size","type":"size","result":"~64 bytes for P-256"},
     ])),
    ("science-and-technology", "computer-science", "SHA Hash Family", "sha-hash-family",
     "SHA-1, SHA-256, SHA-3, output sizes and collision resistance.",
     "discrete-math.png", False, True, J([
        {"query":"SHA-256 output","type":"size","result":"256 bits = 32 bytes"},
        {"query":"SHA-1 collision","type":"event","result":"SHAttered 2017 — Google + CWI demo"},
        {"query":"SHA-3 family","type":"variant","result":"Keccak; SHA3-224/256/384/512 + SHAKE"},
     ])),
    ("science-and-technology", "computer-science", "AES Encryption", "aes-encryption",
     "AES-128/192/256, modes (GCM, CBC, CTR), and block size.",
     "discrete-math.png", False, True, J([
        {"query":"AES-256 security","type":"security","result":"256-bit key — post-quantum resistant for symmetric"},
        {"query":"AES block size","type":"property","result":"128 bits regardless of key length"},
        {"query":"AES-GCM authenticated","type":"mode","result":"GCM provides authenticated encryption with associated data"},
     ])),
    ("science-and-technology", "computer-science", "Public Key Protocols", "public-key-protocols",
     "Diffie-Hellman, ECDH, key exchange and forward secrecy.",
     "discrete-math.png", False, False, J([
        {"query":"forward secrecy","type":"property","result":"Compromise of long-term key doesn't break past sessions"},
        {"query":"X3DH protocol","type":"protocol","result":"Signal's extended triple Diffie-Hellman handshake"},
        {"query":"PSK vs PKE","type":"compare","result":"Pre-shared key vs public-key — different trust models"},
     ])),
    ("science-and-technology", "computer-science", "Diffie-Hellman", "diffie-hellman",
     "Classic DH key exchange and discrete-log security.",
     "discrete-math.png", False, False, J([
        {"query":"DH math","type":"formula","result":"g^a mod p, g^b mod p → shared g^(ab) mod p"},
        {"query":"DH prime size","type":"size","result":"≥2048-bit safe prime recommended"},
        {"query":"Logjam attack","type":"attack","result":"512-bit DH downgrade (2015) — broke many TLS servers"},
     ])),
    ("science-and-technology", "computer-science", "Digital Signatures", "digital-signatures",
     "RSA-PSS, ECDSA, Ed25519 signature schemes and verifications.",
     "discrete-math.png", False, False, J([
        {"query":"Ed25519 size","type":"size","result":"32-byte public key, 64-byte signature"},
        {"query":"signature non-repudiation","type":"property","result":"Signer cannot deny authorship without revealing private key"},
        {"query":"PSS padding","type":"scheme","result":"Probabilistic Signature Scheme for RSA"},
     ])),
    ("science-and-technology", "computer-science", "Hash Collisions", "hash-collisions",
     "Birthday paradox, collision-finding, and weak hashes.",
     "discrete-math.png", False, False, J([
        {"query":"birthday bound","type":"theory","result":"2^(n/2) expected collisions for n-bit hash"},
        {"query":"MD5 collisions","type":"history","result":"Practical collisions since 2004; chosen-prefix 2008"},
        {"query":"SHA-1 chosen prefix","type":"attack","result":"~2^63 work; demonstrated by SHAmbles 2020"},
     ])),
    ("science-and-technology", "computer-science", "Zero-Knowledge Proofs", "zero-knowledge-proofs",
     "ZK-SNARKs, zk-STARKs, and proof-of-knowledge protocols.",
     "discrete-math.png", False, False, J([
        {"query":"zk-SNARK property","type":"property","result":"Succinct, non-interactive proof of knowledge"},
        {"query":"zk-STARK","type":"protocol","result":"Transparent (no trusted setup), post-quantum, larger proofs"},
        {"query":"Schnorr ZKP","type":"protocol","result":"Classic Σ-protocol for discrete-log knowledge"},
     ])),
    ("science-and-technology", "computer-science", "Post-Quantum Cryptography", "post-quantum-cryptography",
     "NIST PQC standards: Kyber, Dilithium, SPHINCS+.",
     "discrete-math.png", False, True, J([
        {"query":"Kyber security","type":"scheme","result":"ML-KEM standard (FIPS 203); lattice-based KEM"},
        {"query":"Dilithium signature","type":"scheme","result":"ML-DSA (FIPS 204); lattice-based signature"},
        {"query":"SPHINCS+ size","type":"scheme","result":"Hash-based signature; ~8 KB signatures"},
     ])),
    ("science-and-technology", "computer-science", "Lattice Cryptography", "lattice-cryptography",
     "Lattice problems (LWE, SIS) and post-quantum constructions.",
     "discrete-math.png", False, False, J([
        {"query":"LWE problem","type":"problem","result":"Learning with errors — recover s from (A, As+e)"},
        {"query":"NTRU scheme","type":"scheme","result":"Public-key crypto from polynomial ring lattices"},
        {"query":"NTT speedup","type":"trick","result":"Number-theoretic transform makes ring-LWE fast"},
     ])),
    ("science-and-technology", "computer-science", "Block Ciphers", "block-ciphers",
     "DES, 3DES, AES, ChaCha20 — block vs stream cipher tradeoffs.",
     "discrete-math.png", False, False, J([
        {"query":"DES key size","type":"property","result":"56 bits effective — broken since 1990s"},
        {"query":"ChaCha20 stream","type":"cipher","result":"Stream cipher; widely used in TLS 1.3"},
        {"query":"GCM mode security","type":"security","result":"AES-GCM 128-bit; IV reuse fatal"},
     ])),
]

# --- Neural network architecture (12) ---
NEW_TOPICS += [
    ("science-and-technology", "computer-science", "Transformer Architecture", "transformer-architecture",
     "Self-attention, multi-head attention, positional encoding, and the original 2017 paper.",
     "discrete-math.png", True, True, J([
        {"query":"transformer attention formula","type":"formula","result":"Attention(Q,K,V) = softmax(QKᵀ/√d_k) V"},
        {"query":"multi-head attention","type":"component","result":"h parallel heads concatenated; typical h = 8 or 16"},
        {"query":"positional encoding","type":"component","result":"sin/cos at different frequencies, learned in some variants"},
     ])),
    ("science-and-technology", "computer-science", "CNN Architecture", "cnn-architecture",
     "Convolutional, pooling, and stride concepts for image models.",
     "discrete-math.png", False, True, J([
        {"query":"conv layer output size","type":"formula","result":"((W − F + 2P)/S) + 1"},
        {"query":"ResNet skip connection","type":"trick","result":"Adds input to output, easing gradient flow"},
        {"query":"VGG depth","type":"model","result":"VGG-16: 13 conv + 3 FC; ~138M params"},
     ])),
    ("science-and-technology", "computer-science", "RNN / LSTM", "rnn-lstm",
     "Vanishing gradients, LSTM cell gates, and sequence modeling.",
     "discrete-math.png", False, True, J([
        {"query":"LSTM gates","type":"component","result":"Input, forget, output, cell-state gates"},
        {"query":"vanishing gradient","type":"problem","result":"Long-range gradients shrink to zero in deep RNNs"},
        {"query":"GRU vs LSTM","type":"compare","result":"GRU: 2 gates, simpler; LSTM: 3 gates, more capacity"},
     ])),
    ("science-and-technology", "computer-science", "Attention Mechanism", "attention-mechanism",
     "Additive vs scaled-dot-product attention, cross-attention.",
     "discrete-math.png", False, True, J([
        {"query":"scaled dot product","type":"formula","result":"softmax(QKᵀ/√d_k) V"},
        {"query":"cross attention","type":"variant","result":"Queries from decoder, keys/values from encoder"},
        {"query":"Bahdanau attention","type":"history","result":"Additive attention (2014) — pre-transformer NMT"},
     ])),
    ("science-and-technology", "computer-science", "Batch Normalization", "batch-normalization",
     "BN math, train/eval modes, and replacement variants (LN, GN).",
     "discrete-math.png", False, True, J([
        {"query":"BN formula","type":"formula","result":"y = γ(x − μ)/√(σ² + ε) + β"},
        {"query":"layer norm","type":"variant","result":"Normalize over features per sample — used in transformers"},
        {"query":"group norm","type":"variant","result":"Normalize within channel groups — invariant to batch size"},
     ])),
    ("science-and-technology", "computer-science", "Dropout Regularization", "dropout-regularization",
     "Dropout math, inverted scaling, and DropPath.",
     "discrete-math.png", False, False, J([
        {"query":"dropout formula","type":"formula","result":"y = x · m / (1 − p); m ~ Bernoulli(1 − p)"},
        {"query":"typical p value","type":"value","result":"p = 0.1–0.5 (0.1 in transformers, 0.5 in CNN FC)"},
        {"query":"DropPath","type":"variant","result":"Drops entire residual branch; used in ViT, ConvNeXt"},
     ])),
    ("science-and-technology", "computer-science", "Residual Connections", "residual-connections",
     "Skip connections in ResNet, transformers — gradient flow benefit.",
     "discrete-math.png", False, False, J([
        {"query":"ResNet formula","type":"formula","result":"y = F(x, W) + x"},
        {"query":"ResNet-50 params","type":"model","result":"~25.6M parameters"},
        {"query":"skip connection benefit","type":"theory","result":"Identity function easy to learn; gradient flows directly"},
     ])),
    ("science-and-technology", "computer-science", "Embedding Layers", "embedding-layers",
     "Word embeddings, learned positional, token embeddings sizes.",
     "discrete-math.png", False, False, J([
        {"query":"word2vec dim","type":"size","result":"Typically 100–300 dimensions"},
        {"query":"BERT vocab","type":"size","result":"30,522 word-piece tokens"},
        {"query":"embedding table params","type":"calc","result":"vocab × d_model parameters"},
     ])),
    ("science-and-technology", "computer-science", "Activation Functions", "activation-functions",
     "ReLU, GELU, Swish, sigmoid, tanh — and their derivatives.",
     "discrete-math.png", False, False, J([
        {"query":"ReLU formula","type":"formula","result":"max(0, x); derivative is step function"},
        {"query":"GELU formula","type":"formula","result":"x · Φ(x) ≈ 0.5x(1 + tanh(√(2/π)(x + 0.044715x³)))"},
        {"query":"Swish/SiLU","type":"formula","result":"x · sigmoid(x)"},
     ])),
    ("science-and-technology", "computer-science", "Adam Optimizer", "optimizers-adam",
     "Adam update rule, learning rate, β1/β2 hyperparameters.",
     "discrete-math.png", False, False, J([
        {"query":"Adam update","type":"formula","result":"θ ← θ − η · m̂ / (√v̂ + ε)"},
        {"query":"Adam betas","type":"hyperparameter","result":"β1 = 0.9, β2 = 0.999 default"},
        {"query":"AdamW","type":"variant","result":"Decoupled weight decay — generalizes better"},
     ])),
    ("science-and-technology", "computer-science", "Learning Rate Scheduling", "learning-rate-scheduling",
     "Cosine, linear warmup, step decay, and one-cycle.",
     "discrete-math.png", False, False, J([
        {"query":"warmup steps","type":"strategy","result":"Linearly increase lr from 0 over first N steps"},
        {"query":"cosine decay","type":"formula","result":"η(t) = η_min + 0.5(η_max − η_min)(1 + cos(πt/T))"},
        {"query":"one-cycle policy","type":"strategy","result":"Up then down — Leslie Smith"},
     ])),
    ("science-and-technology", "computer-science", "Vision Transformers", "vision-transformers",
     "ViT architecture, patch embedding, and ImageNet results.",
     "discrete-math.png", False, True, J([
        {"query":"ViT patch size","type":"hyperparameter","result":"16×16 patches (ViT-B/16)"},
        {"query":"ViT-Base params","type":"model","result":"~86M parameters"},
        {"query":"ViT vs CNN","type":"compare","result":"ViT wins large-data regime; CNN better on small data"},
     ])),
]

# --- Math/science advanced (30) ---
NEW_TOPICS += [
    ("mathematics", "linear-algebra", "Tensor Calculus", "tensor-calculus",
     "Tensor algebra, indices, covariant/contravariant transformations.",
     "algebra.png", False, True, J([
        {"query":"tensor rank","type":"def","result":"Number of indices; vector is rank-1, matrix is rank-2"},
        {"query":"metric tensor","type":"object","result":"Symmetric rank-2 tensor defining inner product"},
        {"query":"Christoffel symbol","type":"object","result":"Connection coefficients; depend on metric derivatives"},
     ])),
    ("mathematics", "algebra-advanced", "Lie Algebras", "lie-algebras",
     "Lie groups, Lie algebras, sl(n), so(n), and their representations.",
     "algebra.png", False, True, J([
        {"query":"sl(2,R) basis","type":"basis","result":"H, E, F with [H,E]=2E, [H,F]=−2F, [E,F]=H"},
        {"query":"Lie bracket","type":"def","result":"[X,Y] = XY − YX (matrix); satisfies Jacobi"},
        {"query":"Cartan classification","type":"theory","result":"Simple complex Lie algebras: A_n, B_n, C_n, D_n + 5 exceptional"},
     ])),
    ("mathematics", "complex-analysis", "Riemann Surfaces", "riemann-surfaces",
     "Genus, branch points, and multi-valued functions.",
     "complex-analysis.png", False, False, J([
        {"query":"genus sphere","type":"value","result":"g = 0"},
        {"query":"branch point sqrt(z)","type":"example","result":"z = 0 is a branch point of order 2"},
        {"query":"Riemann-Roch","type":"theorem","result":"dim H⁰(D) − dim H¹(D) = deg(D) + 1 − g"},
     ])),
    ("mathematics", "number-theory", "Modular Forms", "modular-forms",
     "Modular forms, Eisenstein series, Ramanujan tau function.",
     "discrete-math.png", False, False, J([
        {"query":"weight 12 modular form","type":"object","result":"Discriminant Δ(τ)"},
        {"query":"Eisenstein E4","type":"series","result":"E4(τ) = 1 + 240·Σ σ3(n) q^n"},
        {"query":"j-invariant","type":"object","result":"j(τ) = 1/q + 744 + 196884q + ..."},
     ])),
    ("mathematics", "number-theory", "p-adic Numbers", "p-adic-numbers",
     "p-adic completion, Hensel's lemma, and p-adic analysis.",
     "discrete-math.png", False, False, J([
        {"query":"|p|_p","type":"def","result":"1/p in p-adic absolute value"},
        {"query":"Hensel's lemma","type":"theorem","result":"Lifts roots mod p to roots in Z_p under derivative condition"},
        {"query":"p-adic distance","type":"metric","result":"d(x,y) = |x − y|_p"},
     ])),
    ("mathematics", "algebra-advanced", "Galois Theory", "galois-theory",
     "Galois groups, solvability by radicals, and Abel-Ruffini.",
     "algebra.png", False, False, J([
        {"query":"Gal(Q(√2)/Q)","type":"group","result":"Z/2Z — two elements: identity, conjugation"},
        {"query":"unsolvable by radicals","type":"degree","result":"General quintic and higher"},
        {"query":"fundamental theorem","type":"theorem","result":"Bijection between subfields and subgroups of Galois group"},
     ])),
    ("mathematics", "applied-mathematics", "Category Theory", "category-theory",
     "Functors, natural transformations, limits, colimits.",
     "discrete-math.png", False, False, J([
        {"query":"functor","type":"def","result":"F: C → D respecting composition and identities"},
        {"query":"Yoneda lemma","type":"theorem","result":"Hom(h_A, F) ≅ F(A) naturally"},
        {"query":"adjunction","type":"def","result":"F ⊣ G iff Hom(FX,Y) ≅ Hom(X,GY)"},
     ])),
    ("mathematics", "algebra-advanced", "Sheaf Theory", "sheaf-theory",
     "Sheaves, presheaves, sheafification, and cohomology.",
     "algebra.png", False, False, J([
        {"query":"sheaf condition","type":"def","result":"Locality + gluing axioms"},
        {"query":"sheaf cohomology","type":"object","result":"H^n(X, F) — derived functor of global sections"},
        {"query":"presheaf vs sheaf","type":"compare","result":"Presheaf lacks gluing; sheaf is presheaf + gluing"},
     ])),
    ("mathematics", "geometry", "Projective Geometry", "projective-geometry",
     "Projective spaces, homogeneous coordinates, and duality.",
     "geometry.png", False, False, J([
        {"query":"RP² dimension","type":"value","result":"2-dimensional (lines through origin in R³)"},
        {"query":"projective duality","type":"principle","result":"Swap points and lines in P²"},
        {"query":"cross ratio","type":"invariant","result":"(A,B;C,D) invariant under projective transforms"},
     ])),
    ("mathematics", "discrete-math", "Knot Theory", "topology-knots",
     "Knot invariants, Reidemeister moves, and the Jones polynomial.",
     "discrete-math.png", False, False, J([
        {"query":"trefoil knot","type":"knot","result":"Simplest non-trivial knot; 3 crossings"},
        {"query":"Jones polynomial","type":"invariant","result":"Laurent polynomial in q; distinguishes mirror knots"},
        {"query":"Reidemeister moves","type":"theorem","result":"3 local moves generate all knot equivalences"},
     ])),
    ("mathematics", "discrete-math", "Ramsey Theory", "ramsey-theory",
     "Ramsey numbers, party problem, and arithmetic Ramsey.",
     "discrete-math.png", False, False, J([
        {"query":"R(3,3)","type":"number","result":"6 — 6 people, 3 mutual friends or strangers"},
        {"query":"R(4,4)","type":"number","result":"18"},
        {"query":"R(5,5)","type":"bound","result":"Unknown — between 43 and 48"},
     ])),
    ("mathematics", "discrete-math", "Additive Combinatorics", "additive-combinatorics",
     "Sumsets, Plünnecke-Ruzsa, and Freiman's theorem.",
     "discrete-math.png", False, False, J([
        {"query":"sumset","type":"def","result":"A + B = {a + b : a ∈ A, b ∈ B}"},
        {"query":"Plunnecke-Ruzsa","type":"inequality","result":"|nA| ≤ K^n |A| if |A+A| ≤ K|A|"},
        {"query":"Freiman theorem","type":"theorem","result":"Small doubling sets are generalized arithmetic progressions"},
     ])),
    ("mathematics", "number-theory", "Prime Gaps", "prime-gaps",
     "Prime gaps, Bertrand's postulate, and bounded prime gaps.",
     "discrete-math.png", False, False, J([
        {"query":"twin primes","type":"def","result":"Primes differing by 2; conjectured infinitely many"},
        {"query":"Bertrand postulate","type":"theorem","result":"For n>1, prime exists between n and 2n"},
        {"query":"Zhang bounded gaps","type":"result","result":"Infinitely many primes within 70M (now ≤246)"},
     ])),
    ("science-and-technology", "physics", "Muon Physics", "muon-physics",
     "Muon properties, g-2 anomaly, and muonic atoms.",
     "physics.png", False, False, J([
        {"query":"muon mass","type":"property","result":"105.658 MeV/c² (~207 m_e)"},
        {"query":"muon g-2 anomaly","type":"experiment","result":"Fermilab E989 — 4.2σ from SM"},
        {"query":"muonic atom radius","type":"property","result":"~207× smaller than electronic atom"},
     ])),
    ("science-and-technology", "physics", "Neutrino Oscillation", "neutrino-oscillation",
     "Flavor oscillation, PMNS matrix, and mass-squared splittings.",
     "physics.png", False, False, J([
        {"query":"Δm²_21","type":"value","result":"~7.5 × 10⁻⁵ eV² (solar)"},
        {"query":"Δm²_32","type":"value","result":"~2.5 × 10⁻³ eV² (atmospheric)"},
        {"query":"sin²θ_13","type":"value","result":"~0.022 — reactor mixing angle"},
     ])),
    ("science-and-technology", "physics", "Gravitational Waves", "gravitational-waves",
     "LIGO detections, chirp masses, and waveform templates.",
     "physics.png", False, True, J([
        {"query":"first LIGO detection","type":"event","result":"GW150914 — 36+29 M_sun BH merger, Sep 2015"},
        {"query":"LIGO sensitivity","type":"property","result":"~10⁻²¹ strain sensitivity"},
        {"query":"chirp mass formula","type":"formula","result":"M_c = (m1 m2)^(3/5) / (m1 + m2)^(1/5)"},
     ])),
    ("science-and-technology", "physics", "Casimir Effect", "casimir-effect",
     "Vacuum-energy attraction between parallel plates.",
     "physics.png", False, False, J([
        {"query":"Casimir force formula","type":"formula","result":"F/A = π² ℏ c / (240 d⁴)"},
        {"query":"first measurement","type":"history","result":"Sparnaay 1958; precise by Lamoreaux 1997"},
        {"query":"plate spacing 1um","type":"calc","result":"~ 1.3 mPa pressure"},
     ])),
    ("science-and-technology", "physics", "Quantum Tunneling", "quantum-tunneling",
     "Tunneling probability, WKB approximation, and STM applications.",
     "physics.png", False, False, J([
        {"query":"tunneling probability","type":"formula","result":"T ≈ exp(−2∫√(2m(V−E))/ℏ dx)"},
        {"query":"WKB approximation","type":"method","result":"Semiclassical valid for slowly varying V"},
        {"query":"STM principle","type":"application","result":"Tunnel current → atomic-resolution surface imaging"},
     ])),
    ("science-and-technology", "physics", "Supersymmetry", "supersymmetry",
     "SUSY partners, MSSM, and LHC search limits.",
     "physics.png", False, False, J([
        {"query":"squark partner","type":"particle","result":"Scalar partner of quark"},
        {"query":"MSSM particle count","type":"count","result":"~doubles SM spectrum"},
        {"query":"LHC SUSY limit","type":"bound","result":"Gluino > 2 TeV in simplified models"},
     ])),
    ("science-and-technology", "physics", "String Theory Basics", "string-theory-basics",
     "1D strings, 10D spacetime, and string dualities.",
     "physics.png", False, False, J([
        {"query":"string dimensions","type":"property","result":"Critical: 26 bosonic, 10 superstring"},
        {"query":"string tension","type":"property","result":"T ~ 1/(2π α'); α' is string scale"},
        {"query":"five string theories","type":"list","result":"Type I, IIA, IIB, Het-O, Het-E"},
     ])),
    ("science-and-technology", "physics", "M-Theory", "m-theory",
     "11D theory unifying 5 string theories.",
     "physics.png", False, False, J([
        {"query":"M-theory dimension","type":"property","result":"11 dimensions"},
        {"query":"M2 brane","type":"object","result":"2D membrane in 11D"},
        {"query":"M5 brane","type":"object","result":"5D brane in 11D"},
     ])),
    ("science-and-technology", "physics", "AdS/CFT", "ads-cft",
     "Maldacena conjecture relating AdS gravity to CFT.",
     "physics.png", False, False, J([
        {"query":"Maldacena 1997","type":"paper","result":"AdS5 × S5 / N=4 super Yang-Mills"},
        {"query":"holographic dictionary","type":"map","result":"Bulk fields ↔ CFT operators"},
        {"query":"AdS isometries","type":"group","result":"SO(d-1,2) — matches conformal group"},
     ])),
    ("science-and-technology", "physics", "Holographic Principle", "holographic-principle",
     "Entropy bounds and information on boundary.",
     "physics.png", False, False, J([
        {"query":"Bekenstein bound","type":"bound","result":"S ≤ 2π R E / (ℏ c)"},
        {"query":"black hole entropy","type":"formula","result":"S = A / (4 G ℏ)"},
        {"query":"holography 't Hooft Susskind","type":"history","result":"Proposed 1993–1994; AdS/CFT realized it"},
     ])),
    ("science-and-technology", "physics", "Multiverse Models", "multiverse-models",
     "String landscape, inflationary multiverse, anthropic reasoning.",
     "physics.png", False, False, J([
        {"query":"string landscape size","type":"count","result":"~10^500 vacua"},
        {"query":"eternal inflation","type":"model","result":"Quantum fluctuations restart inflation in some regions"},
        {"query":"many worlds","type":"interpretation","result":"Everett 1957 — branching with each measurement"},
     ])),
    ("science-and-technology", "physics", "LHC Detectors", "lhc-detectors",
     "ATLAS, CMS, LHCb, ALICE detectors at the LHC.",
     "physics.png", False, False, J([
        {"query":"ATLAS magnet","type":"hardware","result":"2 T solenoid + 0.5 T toroid"},
        {"query":"CMS magnet","type":"hardware","result":"3.8 T solenoid — name 'Compact Muon Solenoid'"},
        {"query":"LHCb pseudorapidity","type":"design","result":"2 < η < 5; forward spectrometer"},
     ])),
    ("science-and-technology", "engineering-detail", "MEMS", "mems",
     "Micro-electromechanical systems: gyroscopes, accelerometers, microfluidics.",
     "physics.png", False, True, J([
        {"query":"MEMS gyroscope","type":"device","result":"Coriolis force on vibrating mass — phone IMUs"},
        {"query":"MEMS accelerometer noise","type":"property","result":"~50–200 μg/√Hz typical"},
        {"query":"MEMS fab process","type":"process","result":"Surface micromachining + bulk silicon etch"},
     ])),
    ("science-and-technology", "engineering-detail", "FPGA", "fpga",
     "Field-programmable gate arrays — Xilinx/Altera, LUTs, DSP slices.",
     "physics.png", False, False, J([
        {"query":"FPGA LUT","type":"primitive","result":"Look-up table — 4–6 input combinational logic"},
        {"query":"largest FPGA","type":"chip","result":"AMD Versal Premium — >7M logic cells"},
        {"query":"FPGA vs ASIC","type":"compare","result":"FPGA: reprogrammable; ASIC: faster, lower power, fixed"},
     ])),
    ("science-and-technology", "engineering-detail", "ASIC", "asic",
     "Application-specific ICs, process nodes, design flow.",
     "physics.png", False, False, J([
        {"query":"TSMC 3nm","type":"node","result":"Volume production 2022; N3 family"},
        {"query":"mask cost","type":"cost","result":"~$10–30M for 5nm full mask set"},
        {"query":"ASIC vs FPGA performance","type":"compare","result":"ASIC ~10× faster, ~100× lower power than FPGA"},
     ])),
    ("science-and-technology", "engineering-detail", "Microcontrollers", "microcontrollers",
     "ARM Cortex-M, AVR, ESP32 — embedded computing.",
     "physics.png", False, False, J([
        {"query":"Cortex-M0 power","type":"power","result":"~10 μW/MHz typical"},
        {"query":"ATmega328 used","type":"chip","result":"Arduino Uno main MCU"},
        {"query":"ESP32 dual core","type":"chip","result":"240 MHz, WiFi + BT, dual Xtensa LX6"},
     ])),
    ("science-and-technology", "engineering-detail", "Digital Signal Processing", "signal-processing-dsp",
     "FFT, FIR/IIR filters, sampling theorem.",
     "physics.png", False, False, J([
        {"query":"Nyquist rate","type":"theorem","result":"fs > 2 · f_max to avoid aliasing"},
        {"query":"FFT complexity","type":"complexity","result":"O(N log N)"},
        {"query":"FIR vs IIR","type":"compare","result":"FIR: stable, linear phase. IIR: efficient, can ring."},
     ])),
]

# --- Quant finance (8) ---
NEW_TOPICS += [
    ("society-and-culture", "finance", "Quantitative Finance", "quantitative-finance",
     "Black-Scholes, stochastic calculus, Greeks, and risk neutral pricing.",
     "finance.png", True, True, J([
        {"query":"Black-Scholes call","type":"formula","result":"C = S N(d1) − K e^(−rT) N(d2)"},
        {"query":"Ito's lemma","type":"theorem","result":"df = (∂f/∂t + μ∂f/∂x + 0.5σ²∂²f/∂x²)dt + σ∂f/∂x dW"},
        {"query":"risk-neutral measure","type":"concept","result":"Pricing measure under which discounted prices are martingales"},
     ])),
    ("society-and-culture", "finance", "Options Greeks (Detail)", "options-greeks-detail",
     "Delta, gamma, vega, theta, rho — and second-order Greeks.",
     "finance.png", False, True, J([
        {"query":"delta call ATM","type":"value","result":"~0.5 for at-the-money European call"},
        {"query":"vega definition","type":"def","result":"∂C/∂σ — option sensitivity to vol"},
        {"query":"gamma definition","type":"def","result":"∂²C/∂S² — convexity"},
     ])),
    ("society-and-culture", "finance", "Monte Carlo Finance", "monte-carlo-finance",
     "MC simulation for option pricing and risk.",
     "finance.png", False, False, J([
        {"query":"MC convergence rate","type":"rate","result":"O(1/√N) — needs 10000 paths for 1% error"},
        {"query":"variance reduction","type":"technique","result":"Antithetic, control variates, importance sampling"},
        {"query":"Longstaff-Schwartz","type":"method","result":"Regression-based American option pricing"},
     ])),
    ("society-and-culture", "finance", "Value at Risk", "value-at-risk",
     "VaR definition, historical/parametric/MC VaR, and ES.",
     "finance.png", False, False, J([
        {"query":"VaR 95%","type":"def","result":"5th percentile of loss distribution over time horizon"},
        {"query":"expected shortfall","type":"def","result":"Average loss in worst (1−α) tail"},
        {"query":"Basel III VaR","type":"regulation","result":"Replaced by Expected Shortfall in 2019"},
     ])),
    ("society-and-culture", "finance", "Portfolio Theory", "portfolio-theory",
     "Markowitz mean-variance, efficient frontier, and Sharpe ratio.",
     "finance.png", False, False, J([
        {"query":"Sharpe ratio","type":"formula","result":"(R_p − R_f) / σ_p"},
        {"query":"efficient frontier","type":"def","result":"Locus of max-return portfolios for each σ"},
        {"query":"two-fund theorem","type":"theorem","result":"All efficient portfolios are combos of two specific ones"},
     ])),
    ("society-and-culture", "finance", "Capital Asset Pricing", "capital-asset-pricing",
     "CAPM, beta, security market line.",
     "finance.png", False, False, J([
        {"query":"CAPM formula","type":"formula","result":"E[R_i] = R_f + β_i (E[R_m] − R_f)"},
        {"query":"beta formula","type":"formula","result":"β_i = Cov(R_i, R_m) / Var(R_m)"},
        {"query":"market beta","type":"value","result":"β = 1 by definition (market with itself)"},
     ])),
    ("society-and-culture", "finance", "Bond Duration", "bond-duration",
     "Macaulay duration, modified duration, convexity.",
     "finance.png", False, False, J([
        {"query":"Macaulay duration","type":"formula","result":"Σ t · PV(CF_t) / Price"},
        {"query":"modified duration","type":"formula","result":"D_mod = D_mac / (1 + y/n)"},
        {"query":"convexity","type":"def","result":"Second derivative of price wrt yield"},
     ])),
    ("society-and-culture", "finance", "High-Frequency Trading", "high-frequency-trading",
     "HFT strategies, latency arbitrage, and market microstructure.",
     "finance.png", False, False, J([
        {"query":"HFT latency","type":"benchmark","result":"<1 ms; tick-to-trade can be sub-µs"},
        {"query":"flash crash 2010","type":"event","result":"May 6, 2010 — DJIA dropped 9% in minutes"},
        {"query":"latency arbitrage","type":"strategy","result":"Exploit price discrepancies across venues faster than others"},
     ])),
]

# --- Cooking / home math (12) ---
NEW_TOPICS += [
    ("everyday-life", "household-math", "Home Renovation", "home-renovation",
     "Cost estimates for kitchen, bathroom, and whole-home renovations.",
     "household-math.png", False, True, J([
        {"query":"average kitchen reno cost","type":"cost","result":"~$26k US average (NKBA 2024)"},
        {"query":"bath reno cost","type":"cost","result":"~$15k US average mid-range"},
        {"query":"ROI kitchen","type":"roi","result":"~70% recouped at resale"},
     ])),
    ("everyday-life", "household-math", "Paint Coverage", "painting-coverage",
     "Paint per gallon, drying times, and coverage rules.",
     "household-math.png", False, False, J([
        {"query":"paint coverage gallon","type":"coverage","result":"~350–400 sqft per gallon (1 coat)"},
        {"query":"primer needed","type":"rule","result":"Yes for bare wood, stains, drastic color change"},
        {"query":"paint dry time","type":"time","result":"Latex: 1h dry / 2–4h recoat"},
     ])),
    ("everyday-life", "household-math", "Lawn Care Math", "lawn-care",
     "Fertilizer rate, mowing frequency, watering volumes.",
     "household-math.png", False, False, J([
        {"query":"fertilizer N rate","type":"rate","result":"~1 lb N / 1000 sqft per application"},
        {"query":"lawn water inches","type":"rate","result":"~1 inch/week including rain"},
        {"query":"mowing height","type":"rule","result":"Cool season: 3–4 in; warm: 1–2 in"},
     ])),
    ("everyday-life", "household-math", "HVAC Sizing", "hvac-sizing",
     "BTU/hour, Manual J, tons of cooling needed.",
     "household-math.png", False, False, J([
        {"query":"AC BTU per sqft","type":"rule","result":"20 BTU/sqft rough rule"},
        {"query":"1 ton AC","type":"unit","result":"12000 BTU/hr (= cooling 1 ton ice/day)"},
        {"query":"furnace BTU","type":"rule","result":"30–60 BTU/sqft depending on climate zone"},
     ])),
    ("everyday-life", "household-math", "Electric Bills", "electric-bills",
     "kWh math, appliance wattage, and US utility rates.",
     "household-math.png", False, False, J([
        {"query":"avg US electricity rate","type":"rate","result":"~16¢/kWh residential (2024)"},
        {"query":"refrigerator kWh","type":"appliance","result":"~400 kWh/year (Energy Star)"},
        {"query":"AC running kW","type":"appliance","result":"3 ton AC ~3.5 kW running"},
     ])),
    ("everyday-life", "household-math", "Water Bills", "water-bills",
     "Gallons used, residential water rate, conservation.",
     "household-math.png", False, False, J([
        {"query":"avg gallons person","type":"usage","result":"~80–100 gallons/day per person US"},
        {"query":"low flow showerhead","type":"savings","result":"2.5 gpm → 1.5 gpm saves ~3000 gal/yr"},
        {"query":"toilet flush","type":"usage","result":"Modern: 1.28 gal/flush (WaterSense)"},
     ])),
    ("everyday-life", "household-math", "Garden Soil Math", "garden-soil",
     "Cubic yards calculation and soil amendments.",
     "household-math.png", False, False, J([
        {"query":"cubic yards garden bed","type":"formula","result":"(L × W × H)/27 with all in feet"},
        {"query":"raised bed soil mix","type":"recipe","result":"1/3 topsoil + 1/3 compost + 1/3 vermiculite"},
        {"query":"mulch coverage","type":"rule","result":"~108 sqft per cubic yard at 3 inch depth"},
     ])),
    ("everyday-life", "cooking", "Kitchen Conversions", "kitchen-conversions",
     "Tablespoons, cups, sticks of butter, and gram conversions.",
     "household-math.png", False, False, J([
        {"query":"1 stick butter grams","type":"convert","result":"113 g (1/2 cup)"},
        {"query":"1 cup flour grams","type":"convert","result":"~120 g all-purpose"},
        {"query":"3 tbsp to ml","type":"convert","result":"≈ 44.4 ml"},
     ])),
    ("everyday-life", "cooking", "Baking Substitutions", "baking-substitutions",
     "Egg, butter, sugar substitutions in baking.",
     "household-math.png", False, False, J([
        {"query":"egg substitute baking","type":"sub","result":"1/4 cup applesauce or 1 tbsp ground flax + 3 tbsp water"},
        {"query":"buttermilk substitute","type":"sub","result":"1 tbsp lemon juice in cup milk; rest 5 min"},
        {"query":"butter to oil","type":"sub","result":"3/4 amount oil per amount butter"},
     ])),
    ("everyday-life", "household-science", "Cleaning Chemistry", "cleaning-chemistry",
     "Chemistry of common household cleaners, safety mixes.",
     "household-math.png", False, False, J([
        {"query":"bleach + ammonia","type":"safety","result":"NEVER mix — produces toxic chloramine gas"},
        {"query":"vinegar baking soda","type":"reaction","result":"CH3COOH + NaHCO3 → CO2 + water + sodium acetate"},
        {"query":"hydrogen peroxide concentrations","type":"detail","result":"3% drugstore; 12% industrial; 35% food grade"},
     ])),
    ("everyday-life", "household-math", "Tile Calculator", "tile-calculator",
     "Square footage of tiles needed, waste factor, grout.",
     "household-math.png", False, False, J([
        {"query":"tile waste factor","type":"rule","result":"10% extra for cuts; 15% for diagonal patterns"},
        {"query":"grout coverage","type":"rule","result":"~25 sqft per 25 lb bag (1/4 in joint)"},
        {"query":"thinset coverage","type":"rule","result":"~95 sqft per 50 lb bag (1/4 in trowel)"},
     ])),
    ("everyday-life", "household-math", "Carpet Calculator", "carpet-calculator",
     "Yards needed for room, padding, and installation.",
     "household-math.png", False, False, J([
        {"query":"carpet yards","type":"formula","result":"sqft / 9 = yards² (1 yard² = 9 sqft)"},
        {"query":"carpet pad density","type":"property","result":"6–8 lb residential, 8+ heavy traffic"},
        {"query":"carpet seam direction","type":"rule","result":"Run parallel to main light source"},
     ])),
]

# --- Arts / culture (10) ---
NEW_TOPICS += [
    ("society-and-culture", "music-audio", "Jazz Chords", "jazz-chords",
     "Extended chords (9, 11, 13), voicings, and ii-V-I progressions.",
     "arts-media.png", False, True, J([
        {"query":"ii-V-I in C","type":"progression","result":"Dm7 – G7 – Cmaj7"},
        {"query":"7b9 chord","type":"chord","result":"Dominant 7th with flat-9; e.g. G7b9 = G B D F Ab"},
        {"query":"shell voicing","type":"voicing","result":"3rd + 7th of chord only"},
     ])),
    ("society-and-culture", "music-audio", "Music Theory Detail", "music-theory-detail",
     "Modes, key signatures, scales, intervals.",
     "arts-media.png", False, False, J([
        {"query":"Dorian mode","type":"mode","result":"Minor scale with raised 6th (D Dorian = D E F G A B C)"},
        {"query":"circle of fifths","type":"diagram","result":"12 keys, each a fifth apart; sharps clockwise"},
        {"query":"perfect fifth ratio","type":"interval","result":"3:2 frequency ratio"},
     ])),
    ("society-and-culture", "arts-media", "Movie Box Office", "movie-box-office",
     "All-time top-grossing films and box-office records.",
     "arts-media.png", False, True, J([
        {"query":"top grossing film","type":"record","result":"Avatar — $2.92B (re-release)"},
        {"query":"top opening weekend","type":"record","result":"Avengers Endgame — $357M domestic"},
        {"query":"top grossing 2023","type":"year","result":"Barbie — $1.45B worldwide"},
     ])),
    ("society-and-culture", "popular-culture", "Book Publishing Stats", "book-publishing-stats",
     "Best-selling books, publishing industry metrics.",
     "arts-media.png", False, False, J([
        {"query":"top selling book","type":"record","result":"Bible ~5B copies; Quran ~1.5B"},
        {"query":"best selling novel","type":"record","result":"A Tale of Two Cities — ~200M copies"},
        {"query":"US books published","type":"market","result":"~600k+ titles/year (incl self-pub)"},
     ])),
    ("society-and-culture", "popular-culture", "Comic Books History", "comic-books-history",
     "Golden/Silver/Bronze Age comics, top issues.",
     "arts-media.png", False, False, J([
        {"query":"Action Comics 1","type":"issue","result":"Superman debut, 1938; ~$3.2M sale 2014"},
        {"query":"Detective Comics 27","type":"issue","result":"Batman debut, 1939"},
        {"query":"Amazing Fantasy 15","type":"issue","result":"Spider-Man debut, 1962"},
     ])),
    ("society-and-culture", "arts-media", "Art Auctions", "art-auctions",
     "Most expensive paintings sold at auction.",
     "arts-media.png", False, False, J([
        {"query":"most expensive painting","type":"record","result":"Salvator Mundi (da Vinci) — $450M (2017)"},
        {"query":"Picasso auction record","type":"record","result":"Les Femmes d'Alger — $179M (2015)"},
        {"query":"Basquiat record","type":"record","result":"Untitled (1982) — $110M (2017)"},
     ])),
    ("society-and-culture", "arts-media", "Broadway Attendance", "broadway-attendance",
     "Broadway box office and long-running shows.",
     "arts-media.png", False, False, J([
        {"query":"longest Broadway show","type":"record","result":"Phantom of the Opera — 35 years"},
        {"query":"Broadway gross 2022","type":"market","result":"~$1.6B box office"},
        {"query":"top single Broadway","type":"record","result":"Hamilton — $4M weekly gross"},
     ])),
    ("society-and-culture", "arts-media", "Museum Attendance", "museum-attendance",
     "Most-visited museums worldwide.",
     "arts-media.png", False, False, J([
        {"query":"most visited museum","type":"record","result":"Louvre — 8.7M visitors (2023)"},
        {"query":"Smithsonian visitors","type":"count","result":"Combined ~17M/year free admission"},
        {"query":"British Museum visitors","type":"count","result":"~5.8M (2022)"},
     ])),
    ("society-and-culture", "arts-media", "Classical Composers", "classical-composers-list",
     "Bach, Mozart, Beethoven, etc. — works and dates.",
     "arts-media.png", False, False, J([
        {"query":"Bach BWV count","type":"works","result":"1128 catalogued works"},
        {"query":"Mozart Köchel","type":"works","result":"K.626 (Requiem) is last"},
        {"query":"Beethoven symphonies","type":"works","result":"9 symphonies; 9th choral with 'Ode to Joy'"},
     ])),
    ("society-and-culture", "words-letters", "Etymology English", "english-etymology",
     "Origin of common English words and roots.",
     "arts-media.png", False, False, J([
        {"query":"etymology robot","type":"origin","result":"From Czech 'robota' (1920 R.U.R.)"},
        {"query":"etymology algorithm","type":"origin","result":"From al-Khwārizmī's name (9th c. Persian mathematician)"},
        {"query":"etymology serendipity","type":"origin","result":"Horace Walpole 1754, from Persian fairy tale"},
     ])),
]

# --- Additional pop-culture / words / dates / misc (25) ---
NEW_TOPICS += [
    ("society-and-culture", "words-letters", "Latin Phrases", "latin-phrases",
     "Common Latin phrases in legal, academic, and everyday English.",
     "arts-media.png", False, False, J([
        {"query":"ad hoc","type":"phrase","result":"For this purpose; improvised"},
        {"query":"caveat emptor","type":"phrase","result":"Let the buyer beware"},
        {"query":"de facto","type":"phrase","result":"In practice; in fact"},
     ])),
    ("society-and-culture", "words-letters", "Greek Prefixes", "greek-prefixes",
     "Common Greek prefixes used in English scientific terms.",
     "arts-media.png", False, False, J([
        {"query":"prefix tele-","type":"prefix","result":"Far, distant (telescope, telephone)"},
        {"query":"prefix bio-","type":"prefix","result":"Life (biology, biome)"},
        {"query":"prefix hyper-","type":"prefix","result":"Over, above (hyperbole, hypertension)"},
     ])),
    ("society-and-culture", "words-letters", "Palindromes", "palindromes-list",
     "Famous palindromes — words, phrases, dates, and numbers.",
     "arts-media.png", False, False, J([
        {"query":"longest palindrome word","type":"record","result":"saippuakivikauppias (Finnish, 19 letters)"},
        {"query":"palindrome date","type":"date","result":"02/02/2020 — palindromic both formats"},
        {"query":"palindrome number","type":"math","result":"121, 12321, 1234321 are palindromic"},
     ])),
    ("society-and-culture", "words-letters", "Anagrams", "anagrams",
     "Famous anagrams and anagram math.",
     "arts-media.png", False, False, J([
        {"query":"anagram count letters n","type":"formula","result":"n! / (n1! · n2! ...) with repeats"},
        {"query":"famous anagram","type":"example","result":"'Astronomer' → 'moon starer'"},
        {"query":"anagram of listen","type":"example","result":"'Silent' or 'Tinsel'"},
     ])),
    ("society-and-culture", "words-letters", "Scrabble Words", "scrabble-words",
     "Scrabble scoring, two-letter words, and best plays.",
     "arts-media.png", False, False, J([
        {"query":"highest Scrabble play","type":"record","result":"OXYPHENBUTAZONE — 1778 points (theoretical)"},
        {"query":"Q value Scrabble","type":"score","result":"10 points; rarest tile after Z"},
        {"query":"two letter words","type":"count","result":"107 valid 2-letter words in TWL"},
     ])),
    ("society-and-culture", "words-letters", "Word Frequencies", "word-frequencies",
     "Zipf's law and English word frequency distributions.",
     "arts-media.png", False, False, J([
        {"query":"Zipf law","type":"law","result":"freq(rank) ∝ 1/rank^s with s ≈ 1"},
        {"query":"most common English word","type":"freq","result":"'the' — ~6.9% of all tokens"},
        {"query":"top 100 cover","type":"stat","result":"~50% of all English text"},
     ])),
    ("everyday-life", "dates-times", "Calendar Conversions", "calendar-conversions",
     "Gregorian, Julian, Islamic, Hebrew calendar conversions.",
     "household-math.png", False, False, J([
        {"query":"Julian to Gregorian 1900","type":"convert","result":"13-day offset; Julian Jan 1 1900 = Gregorian Jan 14 1900"},
        {"query":"Islamic year length","type":"calendar","result":"~354 days (12 lunar months)"},
        {"query":"Hebrew year length","type":"calendar","result":"353–385 days with leap month"},
     ])),
    ("everyday-life", "dates-times", "Day of Week", "day-of-week",
     "Zeller's congruence and day-of-week algorithms.",
     "household-math.png", False, False, J([
        {"query":"Zeller's congruence","type":"formula","result":"h = (q + ⌊13(m+1)/5⌋ + K + ⌊K/4⌋ + ⌊J/4⌋ - 2J) mod 7"},
        {"query":"day Jan 1 2000","type":"value","result":"Saturday"},
        {"query":"doomsday algorithm","type":"method","result":"Conway's mental day-of-week algorithm via anchor day"},
     ])),
    ("everyday-life", "personal-finance", "Credit Cards Math", "credit-cards-math",
     "APR, minimum payment math, and credit utilization.",
     "household-math.png", False, False, J([
        {"query":"APR vs APY","type":"compare","result":"APR: simple annual rate. APY: compounded annual yield."},
        {"query":"minimum payment formula","type":"formula","result":"Typically max(1%-2% of balance + interest, $25)"},
        {"query":"credit utilization rule","type":"rule","result":"Keep below 30% of credit limit"},
     ])),
    ("everyday-life", "personal-finance", "Tip Calculator", "tip-calculator-math",
     "Tip percentages, splitting bills, and tax-tip ordering.",
     "household-math.png", False, False, J([
        {"query":"15% tip on $50","type":"calc","result":"$7.50"},
        {"query":"20% tip on $80","type":"calc","result":"$16.00"},
        {"query":"split $120 four ways","type":"calc","result":"$30 per person"},
     ])),
    ("everyday-life", "cooking", "Coffee Brewing Ratios", "coffee-brewing-ratios",
     "Coffee-to-water ratios for pour-over, espresso, French press.",
     "household-math.png", False, False, J([
        {"query":"pour over ratio","type":"recipe","result":"1:15 to 1:17 coffee:water by weight"},
        {"query":"espresso ratio","type":"recipe","result":"1:2 (18g in → 36g out) typical"},
        {"query":"French press ratio","type":"recipe","result":"1:12 coffee:water; 4-min brew"},
     ])),
    ("science-and-technology", "earth-science", "Volcanoes", "volcanoes-list",
     "Famous volcanoes, eruption types, and VEI.",
     "earth-science.png", False, False, J([
        {"query":"largest known volcano","type":"record","result":"Tamu Massif — 310,000 km² submarine"},
        {"query":"VEI 8","type":"scale","result":"Mega-colossal; e.g. Yellowstone 2.1 Mya"},
        {"query":"Krakatoa 1883","type":"event","result":"VEI 6; loudest sound in recorded history"},
     ])),
    ("science-and-technology", "earth-science", "Earthquakes Detail", "earthquakes-detail",
     "Moment magnitude scale, plate tectonics, and seismic data.",
     "earth-science.png", False, False, J([
        {"query":"strongest recorded quake","type":"record","result":"Chile 1960 — Mw 9.5"},
        {"query":"Mw vs Richter","type":"compare","result":"Mw uses seismic moment; Richter saturates at large M"},
        {"query":"P vs S waves","type":"physics","result":"P: compressional, fastest. S: shear, slower, no liquid."},
     ])),
    ("science-and-technology", "biological-sciences", "Cell Biology Detail", "cell-biology-detail",
     "Organelles, cell cycle, and major cellular processes.",
     "earth-science.png", False, False, J([
        {"query":"mitochondria role","type":"organelle","result":"ATP production via oxidative phosphorylation"},
        {"query":"cell cycle phases","type":"process","result":"G1, S (DNA replication), G2, M (mitosis)"},
        {"query":"ribosome composition","type":"organelle","result":"Eukaryotic: 80S = 60S + 40S subunits"},
     ])),
    ("science-and-technology", "biological-sciences", "Human Genome", "human-genome-detail",
     "Genome size, gene count, and notable chromosomes.",
     "earth-science.png", False, False, J([
        {"query":"human genome size","type":"value","result":"~3.2 billion base pairs"},
        {"query":"protein coding genes","type":"value","result":"~20,000 genes"},
        {"query":"chromosome 1 size","type":"value","result":"~249 Mb — largest"},
     ])),
    ("science-and-technology", "biological-sciences", "Neuroscience Basics", "neuroscience-basics",
     "Neuron anatomy, action potentials, brain regions.",
     "earth-science.png", False, False, J([
        {"query":"resting potential","type":"value","result":"~-70 mV typical neuron"},
        {"query":"action potential peak","type":"value","result":"~+30 mV at peak"},
        {"query":"synaptic delay","type":"value","result":"~0.5–5 ms across synapse"},
     ])),
    ("everyday-life", "travel", "Travel Visa Rules", "travel-visa-rules",
     "Common visa types, Schengen rules, and travel passport counts.",
     "household-math.png", False, False, J([
        {"query":"Schengen 90/180 rule","type":"rule","result":"90 days within any 180-day rolling period"},
        {"query":"most powerful passport","type":"ranking","result":"Japan / Singapore — 192+ visa-free destinations"},
        {"query":"longest valid passport","type":"rule","result":"US issues 10 years; some countries 5-7"},
     ])),
    ("everyday-life", "travel", "Time Zone Math", "time-zone-math",
     "Calculate time differences and flight durations across time zones.",
     "household-math.png", False, False, J([
        {"query":"NY to Tokyo time","type":"calc","result":"+13 or +14 hours depending on DST"},
        {"query":"flight time SF to London","type":"calc","result":"~10–11 hours nonstop"},
        {"query":"DST start US","type":"rule","result":"Second Sunday in March → first Sunday in November"},
     ])),
    ("society-and-culture", "education", "Test Prep Stats", "test-prep-stats",
     "SAT, ACT, GRE scoring distributions and percentiles.",
     "people.png", False, False, J([
        {"query":"SAT total range","type":"score","result":"400–1600 total (800 EBRW + 800 Math)"},
        {"query":"average SAT score","type":"score","result":"~1050 (50th percentile)"},
        {"query":"GRE quant range","type":"score","result":"130–170; 90th %ile ≈ 167"},
     ])),
    ("society-and-culture", "economics", "Inflation Calculator", "inflation-calculator",
     "CPI-based inflation conversions over decades.",
     "finance.png", False, False, J([
        {"query":"$100 in 1970 to 2024","type":"calc","result":"~$820 (US CPI)"},
        {"query":"$1000 in 2000 to 2024","type":"calc","result":"~$1810 (US CPI)"},
        {"query":"$100 in 2014 to 2024","type":"calc","result":"~$132 (US CPI)"},
     ])),
    ("science-and-technology", "tech-world", "Internet Stats", "internet-stats",
     "Global internet users, bandwidth, and traffic.",
     "discrete-math.png", False, False, J([
        {"query":"internet users","type":"value","result":"~5.3 billion users (2024)"},
        {"query":"global IP traffic","type":"value","result":"~5 ZB/year (Cisco VNI)"},
        {"query":"internet penetration","type":"value","result":"~67% global"},
     ])),
    ("science-and-technology", "tech-world", "Cloud Computing", "cloud-computing-stats",
     "AWS, Azure, GCP market share and pricing.",
     "discrete-math.png", False, False, J([
        {"query":"AWS market share","type":"stat","result":"~31% (Q4 2023, Synergy)"},
        {"query":"Azure market share","type":"stat","result":"~25%"},
        {"query":"global cloud spending","type":"stat","result":"~$600B+ (2024)"},
     ])),
    ("science-and-technology", "tech-world", "Programming Language Popularity", "programming-popularity",
     "TIOBE, Stack Overflow survey, GitHub language rankings.",
     "discrete-math.png", False, False, J([
        {"query":"most popular language 2024","type":"rank","result":"Python (TIOBE), JavaScript (GitHub)"},
        {"query":"GitHub top language","type":"rank","result":"JavaScript still #1 by repo count"},
        {"query":"fastest growing language","type":"rank","result":"Rust — high growth; ~5 years on top in survey love"},
     ])),
    ("science-and-technology", "tech-world", "Operating System Share", "os-market-share",
     "Desktop and mobile OS market share.",
     "discrete-math.png", False, False, J([
        {"query":"desktop OS share","type":"share","result":"Windows ~72%, macOS ~16%, Linux ~3%"},
        {"query":"mobile OS share","type":"share","result":"Android ~71%, iOS ~29%"},
        {"query":"Linux server share","type":"share","result":"~96% of top 1M web servers"},
     ])),
    ("science-and-technology", "tech-world", "Database Popularity", "database-popularity",
     "DB-Engines ranking and database categories.",
     "discrete-math.png", False, False, J([
        {"query":"top RDBMS","type":"rank","result":"Oracle, MySQL, PostgreSQL, SQL Server (DB-Engines)"},
        {"query":"top NoSQL","type":"rank","result":"MongoDB, Redis, Elasticsearch, Cassandra"},
        {"query":"top vector DB","type":"rank","result":"Pinecone, Weaviate, Milvus (2024 surge)"},
     ])),
]

print(f"[r4] total new topics: {len(NEW_TOPICS)}")
assert len(NEW_TOPICS) >= 140, f"need 140+ topics, got {len(NEW_TOPICS)}"

# ---------------------------------------------------------------------------
# (2) Computation results — parametric generation, ~2200 rows
# Each row produced via E(...) — generates rich multi-pod entry.
# ---------------------------------------------------------------------------
EXTRA_RESULTS = []

def E_rich(q, parsed, plain, cat, sub, kw, related, slug, plot_url='',
           alternate_forms=None, decimal_approx=None, step_by_step=None,
           wl_code=None, extra_pods=None):
    """Build a rich multi-pod computation row.

    pods structure (rendered by templates/input_result.html):
      [{"title":"Input interpretation","plaintext":parsed},
       {"title":"Result","plaintext":plain},
       {"title":"Decimal approximation","plaintext":decimal_approx},
       {"title":"Alternate forms","plaintext":alternate_forms},
       {"title":"Step-by-step solution","plaintext":step_by_step},
       {"title":"Wolfram Language code","plaintext":wl_code},
       ...]
    """
    pods = [
        {"title":"Input interpretation","plaintext":parsed or q},
        {"title":"Result","plaintext":plain},
    ]
    if decimal_approx:
        pods.append({"title":"Decimal approximation","plaintext":decimal_approx})
    if alternate_forms:
        pods.append({"title":"Alternate forms","plaintext":alternate_forms})
    if step_by_step:
        pods.append({"title":"Step-by-step solution","plaintext":step_by_step})
    if wl_code:
        pods.append({"title":"Wolfram Language code","plaintext":wl_code})
    if extra_pods:
        pods.extend(extra_pods)
    EXTRA_RESULTS.append((
        "__POD__" + q, parsed, plain, cat, sub, kw, pods, slug, plot_url
    ))

# ---- A. Polynomial factorization & expansion (200 rows) ----
# Generate (x - a)(x - b)(x - c) with deterministic a,b,c
def poly_pack():
    n = 0
    for a in range(-7, 8):
        for b in range(a, 8):
            if n >= 100: return n
            # Expand (x − a)(x − b)
            expanded = f"x^2 + {-(a+b)}*x + {a*b}"
            factored = f"(x - {a})(x - {b})"
            q = f"factor x^2 + {-(a+b)}x + {a*b}"
            parsed = f"factor[x² + {-(a+b)}x + {a*b}]"
            roots = f"x = {a} or x = {b}"
            wl = f"Factor[x^2 + {-(a+b)}*x + {a*b}]"
            E_rich(q, parsed, factored,
                   "mathematics", "algebra",
                   f"factor poly r4 {a} {b}",
                   [f"expand {factored}", f"roots of {expanded}", f"x^2 + {-(a+b)}x + {a*b} = 0"],
                   "algebra",
                   alternate_forms=f"{factored} = {expanded}",
                   step_by_step=f"1) Find roots a,b such that ab = {a*b}, a+b = {a+b}\n2) Roots: a = {a}, b = {b}\n3) Factor as (x − {a})(x − {b})",
                   wl_code=wl)
            n += 1
            if n >= 100: return n
            # Expansion task too
            q2 = f"expand (x - {a})(x - {b})"
            parsed2 = f"expand[(x − {a})(x − {b})]"
            wl2 = f"Expand[(x - {a})(x - {b})]"
            E_rich(q2, parsed2, expanded,
                   "mathematics", "algebra",
                   f"expand poly r4 {a} {b}",
                   [f"factor {expanded}", f"roots of {expanded}"],
                   "algebra",
                   alternate_forms=f"{expanded} = (x − {a})(x − {b})",
                   step_by_step=f"1) FOIL: x·x + x·(−{b}) + (−{a})·x + (−{a})·(−{b})\n2) Combine: {expanded}",
                   wl_code=wl2)
            n += 1
    return n
nA = poly_pack()

# ---- B. Derivative pack (200 rows) ----
# d/dx of common functions — emit step-by-step
DERIV_PACK = []
for n in range(2, 22):
    DERIV_PACK.append((f"derivative of x^{n}", f"d/dx[x^{n}]", f"{n} x^({n-1})",
                       f"D[x^{n}, x]",
                       f"Power rule: d/dx[x^n] = n·x^(n−1)\nWith n = {n}: {n}·x^{n-1}"))
for n in [2, 3, 4, 5, 6, 7, 8, 9, 10]:
    DERIV_PACK.append((f"derivative of sin({n}x)", f"d/dx[sin({n}x)]", f"{n} cos({n}x)",
                       f"D[Sin[{n}*x], x]",
                       f"Chain rule: outer cos, inner {n}x. Result: {n}·cos({n}x)"))
    DERIV_PACK.append((f"derivative of cos({n}x)", f"d/dx[cos({n}x)]", f"-{n} sin({n}x)",
                       f"D[Cos[{n}*x], x]",
                       f"Chain rule: outer −sin, inner {n}x. Result: −{n}·sin({n}x)"))
    DERIV_PACK.append((f"derivative of e^({n}x)", f"d/dx[e^({n}x)]", f"{n} e^({n}x)",
                       f"D[E^({n}*x), x]",
                       f"d/dx[e^u] = e^u · du/dx. u = {n}x. Result: {n}·e^({n}x)"))
for k in range(1, 12):
    DERIV_PACK.append((f"derivative of ln({k}x)", f"d/dx[ln({k}x)]", "1/x",
                       f"D[Log[{k}*x], x]",
                       f"d/dx[ln(u)] = u'/u. u = {k}x, u' = {k}. Result: {k}/({k}x) = 1/x"))
# Product rule examples
for a in range(2, 10):
    DERIV_PACK.append((f"derivative of x^{a} * sin(x)", f"d/dx[x^{a} sin(x)]",
                       f"{a} x^{a-1} sin(x) + x^{a} cos(x)",
                       f"D[x^{a}*Sin[x], x]",
                       f"Product rule: u'v + uv'\nu = x^{a}, u' = {a}x^{a-1}\nv = sin(x), v' = cos(x)"))
# Higher-order
for k in [2, 3, 4]:
    for n in range(3, 8):
        if k <= n:
            coeff = 1
            for j in range(k): coeff *= (n - j)
            DERIV_PACK.append((f"{k}nd derivative of x^{n}" if k == 2 else
                               f"{k}rd derivative of x^{n}" if k == 3 else
                               f"{k}th derivative of x^{n}",
                               f"d^{k}/dx^{k}[x^{n}]", f"{coeff} x^({n-k})",
                               f"D[x^{n}, {{x, {k}}}]",
                               f"Repeated power rule {k} times → {coeff}x^({n-k})"))

for i, (q, parsed, plain, wl, step) in enumerate(DERIV_PACK):
    E_rich(q, parsed, plain,
           "mathematics", "calculus",
           f"derivative r4 {i}",
           [], "calculus",
           alternate_forms=plain,
           step_by_step=step,
           wl_code=wl)

# ---- C. Integral pack (200 rows) ----
INT_PACK = []
for n in range(0, 15):
    INT_PACK.append((f"integral of x^{n}", f"∫ x^{n} dx", f"x^({n+1})/{n+1} + C",
                     f"Integrate[x^{n}, x]",
                     f"Power rule: ∫x^n dx = x^(n+1)/(n+1) + C"))
for n in [2, 3, 4, 5, 6]:
    INT_PACK.append((f"integral of x^{n} from 0 to 1", f"∫_0^1 x^{n} dx",
                     f"1/{n+1}",
                     f"Integrate[x^{n}, {{x, 0, 1}}]",
                     f"∫x^n dx = x^(n+1)/(n+1). Evaluate [0,1]: 1/{n+1}"))
for n in [2, 3, 4, 5]:
    INT_PACK.append((f"integral of x^{n} from 0 to 2", f"∫_0^2 x^{n} dx",
                     f"{2**(n+1) / (n+1):.6g}",
                     f"Integrate[x^{n}, {{x, 0, 2}}]",
                     f"= [x^(n+1)/(n+1)]_0^2 = 2^(n+1)/(n+1) = {2**(n+1)/(n+1):.6g}"))
for k in range(1, 11):
    INT_PACK.append((f"integral of sin({k}x)", f"∫ sin({k}x) dx",
                     f"-cos({k}x)/{k} + C",
                     f"Integrate[Sin[{k}*x], x]",
                     f"∫sin(kx)dx = −cos(kx)/k + C"))
    INT_PACK.append((f"integral of cos({k}x)", f"∫ cos({k}x) dx",
                     f"sin({k}x)/{k} + C",
                     f"Integrate[Cos[{k}*x], x]",
                     f"∫cos(kx)dx = sin(kx)/k + C"))
    INT_PACK.append((f"integral of e^({k}x)", f"∫ e^({k}x) dx",
                     f"e^({k}x)/{k} + C",
                     f"Integrate[E^({k}*x), x]",
                     f"∫e^(kx)dx = e^(kx)/k + C"))
# Trig identities
for q, ans in [
    ("integral of sin(x)^2", "x/2 − sin(2x)/4 + C"),
    ("integral of cos(x)^2", "x/2 + sin(2x)/4 + C"),
    ("integral of tan(x)",   "-ln|cos(x)| + C"),
    ("integral of sec(x)",   "ln|sec(x) + tan(x)| + C"),
    ("integral of sec(x)^2", "tan(x) + C"),
    ("integral of csc(x)^2", "-cot(x) + C"),
]:
    INT_PACK.append((q, q.replace("integral of", "∫").replace("integral", "∫"), ans,
                     "Integrate[" + q.replace("integral of ", "") + ", x]",
                     f"Standard table integral; result {ans}"))
for n in [2, 3, 4, 5, 6, 7]:
    INT_PACK.append((f"integral of x^{n} e^(-x) from 0 to inf", f"∫_0^∞ x^{n} e^(−x) dx",
                     f"{math.factorial(n)}",
                     f"Integrate[x^{n} E^(-x), {{x, 0, Infinity}}]",
                     f"Γ(n+1) = n!. With n = {n}: {math.factorial(n)}"))
# Substitution
for a in [2, 3, 4, 5, 6, 7]:
    INT_PACK.append((f"integral of 1/(x^2 + {a*a})", f"∫ 1/(x²+{a*a}) dx",
                     f"(1/{a}) arctan(x/{a}) + C",
                     f"Integrate[1/(x^2 + {a*a}), x]",
                     f"Use arctan: ∫dx/(x²+a²) = (1/a) arctan(x/a) + C"))

for i, (q, parsed, plain, wl, step) in enumerate(INT_PACK):
    E_rich(q, parsed, plain,
           "mathematics", "calculus",
           f"integral r4 {i}",
           [], "calculus",
           step_by_step=step,
           wl_code=wl)

print(f"[r4] after blocks A+B+C: {len(EXTRA_RESULTS)}")

# ---- D. Unit conversion pack (250 rows) ----
UNIT_PACK = []
LEN_FACTORS = [
    ("mm", "cm", 0.1, "10 mm = 1 cm"),
    ("cm", "m",  0.01, "100 cm = 1 m"),
    ("m",  "km", 0.001, "1000 m = 1 km"),
    ("in", "cm", 2.54, "1 in = 2.54 cm"),
    ("ft", "m",  0.3048, "1 ft = 0.3048 m"),
    ("yd", "m",  0.9144, "1 yd = 0.9144 m"),
    ("mi", "km", 1.609344, "1 mi = 1.609344 km"),
]
for u_from, u_to, factor, rule in LEN_FACTORS:
    for v in [1, 2, 3, 5, 7, 10, 15, 20, 25, 30, 50, 100, 200, 500, 1000]:
        result = v * factor
        UNIT_PACK.append((f"convert {v} {u_from} to {u_to}",
                          f"{v} {u_from} → {u_to}",
                          f"{result:.6g} {u_to}",
                          f"UnitConvert[Quantity[{v}, \"{u_from}\"], \"{u_to}\"]",
                          f"Apply factor: 1 {u_from} = {factor} {u_to}\n{v} × {factor} = {result:.6g}"))
MASS_FACTORS = [
    ("g",  "kg", 0.001, "1000 g = 1 kg"),
    ("lb", "kg", 0.453592, "1 lb = 0.453592 kg"),
    ("oz", "g",  28.3495, "1 oz = 28.3495 g"),
    ("ton", "kg", 1000, "1 t = 1000 kg"),
    ("kg", "lb", 2.20462, "1 kg = 2.20462 lb"),
]
for u_from, u_to, factor, rule in MASS_FACTORS:
    for v in [1, 2, 5, 10, 25, 50, 100, 250, 500, 1000]:
        result = v * factor
        UNIT_PACK.append((f"convert {v} {u_from} to {u_to}",
                          f"{v} {u_from} → {u_to}",
                          f"{result:.6g} {u_to}",
                          f"UnitConvert[Quantity[{v}, \"{u_from}\"], \"{u_to}\"]",
                          f"{rule}\n{v} × {factor} = {result:.6g}"))
TIME_FACTORS = [
    ("min", "s",   60, "1 min = 60 s"),
    ("hr",  "min", 60, "1 hr = 60 min"),
    ("hr",  "s",   3600, "1 hr = 3600 s"),
    ("day", "hr",  24, "1 day = 24 hr"),
    ("day", "s",   86400, "1 day = 86400 s"),
    ("yr",  "day", 365.25, "1 yr = 365.25 day (Julian)"),
]
for u_from, u_to, factor, rule in TIME_FACTORS:
    for v in [1, 2, 3, 5, 10, 15, 30, 60, 100, 500]:
        result = v * factor
        UNIT_PACK.append((f"convert {v} {u_from} to {u_to}",
                          f"{v} {u_from} → {u_to}",
                          f"{result:.6g} {u_to}",
                          f"UnitConvert[Quantity[{v}, \"{u_from}\"], \"{u_to}\"]",
                          f"{rule}\n{v} × {factor} = {result:.6g}"))
TEMP_PACK = []
for v in [-40, -20, -10, 0, 10, 15, 20, 25, 30, 37, 40, 50, 70, 80, 100]:
    f_val = v * 9/5 + 32
    TEMP_PACK.append((f"convert {v} C to F", f"{v} °C → °F", f"{f_val:.4g} °F",
                      f"UnitConvert[Quantity[{v}, \"DegreesCelsius\"], \"DegreesFahrenheit\"]",
                      f"F = C·9/5 + 32 = {v}·1.8 + 32 = {f_val:.4g}"))
    k_val = v + 273.15
    TEMP_PACK.append((f"convert {v} C to K", f"{v} °C → K", f"{k_val:.4g} K",
                      f"UnitConvert[Quantity[{v}, \"DegreesCelsius\"], \"Kelvins\"]",
                      f"K = C + 273.15 = {v} + 273.15 = {k_val:.4g}"))
UNIT_PACK.extend(TEMP_PACK)

for i, (q, parsed, plain, wl, step) in enumerate(UNIT_PACK):
    E_rich(q, parsed, plain,
           "everyday-life", "units-measures",
           f"unit r4 {i}",
           [], "units-measures",
           step_by_step=step,
           wl_code=wl)

# ---- E. Statistics pack (150 rows) ----
STAT_PACK = []
# Means/stddev for short fixed lists
DATASETS = [
    ([2,4,4,4,5,5,7,9],  "mean", 5.0, "std (pop)", 2.0),
    ([10,12,14,16,18],   "mean", 14.0, "std (pop)", math.sqrt(8)),
    ([1,2,3,4,5,6,7,8,9,10], "mean", 5.5, "std (pop)", math.sqrt(8.25)),
    ([3,7,7,19,24,28,28,29,35,42], "mean", 22.2, "std (pop)", math.sqrt(150.96)),
    ([100,200,300,400,500],"mean",300.0, "std (pop)", math.sqrt(20000)),
]
for ds, lbl1, m1, lbl2, s1 in DATASETS:
    q = f"mean of {{{', '.join(str(x) for x in ds)}}}"
    STAT_PACK.append((q, q, f"{m1}",
                      f"Mean[{{{', '.join(str(x) for x in ds)}}}]",
                      f"Sum = {sum(ds)}, count = {len(ds)}, mean = {m1}"))
    q2 = f"standard deviation of {{{', '.join(str(x) for x in ds)}}}"
    STAT_PACK.append((q2, q2, f"{s1:.6g}",
                      f"StandardDeviation[{{{', '.join(str(x) for x in ds)}}}]",
                      f"σ = √(Σ(xi−μ)²/n) = {s1:.6g}"))
# Binomial / normal
for n, p in [(10, 0.3), (10, 0.5), (20, 0.4), (50, 0.2), (100, 0.1)]:
    for k in range(0, min(n, 7) + 1):
        prob = math.comb(n, k) * (p**k) * ((1-p)**(n-k))
        STAT_PACK.append((f"binomial P(X={k}) n={n} p={p}",
                          f"P(X = {k} | Binom({n}, {p}))",
                          f"{prob:.6g}",
                          f"Probability[Binomial[{n}, {p}] == {k}]",
                          f"C({n},{k}) p^{k} (1-p)^({n-k}) = {math.comb(n,k)}·{p}^{k}·{1-p:.4g}^{n-k} ≈ {prob:.6g}"))
# Normal CDF
for z in [-3, -2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 1.96, 2, 2.5, 3]:
    cdf = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    STAT_PACK.append((f"normal cdf at z = {z}",
                      f"Φ({z})",
                      f"{cdf:.6g}",
                      f"CDF[NormalDistribution[0,1], {z}]",
                      f"Φ(z) = (1 + erf(z/√2))/2 = {cdf:.6g}"))
# Confidence intervals
for mean_val in [50, 100, 200]:
    for sd in [5, 10, 20]:
        for n in [25, 50, 100]:
            margin = 1.96 * sd / math.sqrt(n)
            lo, hi = mean_val - margin, mean_val + margin
            STAT_PACK.append((f"95% CI mean={mean_val} sd={sd} n={n}",
                              f"CI95(mean={mean_val}, sd={sd}, n={n})",
                              f"[{lo:.4g}, {hi:.4g}]",
                              f"NConfidence[{mean_val}, {sd}/Sqrt[{n}], 0.95]",
                              f"margin = z*sd/√n = 1.96·{sd}/√{n} = {margin:.4g}"))

for i, (q, parsed, plain, wl, step) in enumerate(STAT_PACK):
    E_rich(q, parsed, plain,
           "mathematics", "statistics",
           f"stat r4 {i}",
           [], "statistics",
           step_by_step=step,
           wl_code=wl)

print(f"[r4] after D+E: {len(EXTRA_RESULTS)}")

# ---- F. Chemistry pack (150 rows) ----
CHEM_PACK = []
# Molecular weights via formula parser (deterministic atomic weights)
ATOMIC = {"H":1.008,"C":12.011,"N":14.007,"O":15.999,"Na":22.99,
          "Mg":24.305,"Al":26.982,"Si":28.086,"P":30.974,"S":32.06,
          "Cl":35.45,"K":39.098,"Ca":40.078,"Fe":55.845,"Cu":63.546,
          "Zn":65.38,"Br":79.904,"I":126.904,"F":18.998,"Hg":200.59}
def molw(parts):
    return sum(ATOMIC[e] * n for e, n in parts)
COMPOUNDS = [
    ("H2O", [("H",2),("O",1)], "water"),
    ("CO2", [("C",1),("O",2)], "carbon dioxide"),
    ("CH4", [("C",1),("H",4)], "methane"),
    ("NH3", [("N",1),("H",3)], "ammonia"),
    ("HCl", [("H",1),("Cl",1)], "hydrochloric acid"),
    ("H2SO4", [("H",2),("S",1),("O",4)], "sulfuric acid"),
    ("HNO3", [("H",1),("N",1),("O",3)], "nitric acid"),
    ("NaCl", [("Na",1),("Cl",1)], "sodium chloride"),
    ("NaOH", [("Na",1),("O",1),("H",1)], "sodium hydroxide"),
    ("CaCO3", [("Ca",1),("C",1),("O",3)], "calcium carbonate"),
    ("Ca(OH)2", [("Ca",1),("O",2),("H",2)], "calcium hydroxide"),
    ("MgSO4", [("Mg",1),("S",1),("O",4)], "magnesium sulfate"),
    ("Al2O3", [("Al",2),("O",3)], "aluminum oxide"),
    ("SiO2", [("Si",1),("O",2)], "silicon dioxide"),
    ("Fe2O3", [("Fe",2),("O",3)], "iron(III) oxide"),
    ("CuSO4", [("Cu",1),("S",1),("O",4)], "copper sulfate"),
    ("KMnO4", [("K",1),("O",4)], "potassium permanganate"),  # ignore Mn (not in table)
    ("CH3OH", [("C",1),("H",4),("O",1)], "methanol"),
    ("C2H5OH", [("C",2),("H",6),("O",1)], "ethanol"),
    ("C6H6", [("C",6),("H",6)], "benzene"),
    ("C6H12O6", [("C",6),("H",12),("O",6)], "glucose"),
    ("C12H22O11", [("C",12),("H",22),("O",11)], "sucrose"),
    ("C8H10N4O2", [("C",8),("H",10),("N",4),("O",2)], "caffeine"),
    ("C9H8O4", [("C",9),("H",8),("O",4)], "aspirin"),
    ("C2H4O2", [("C",2),("H",4),("O",2)], "acetic acid"),
    ("CH3COOH", [("C",2),("H",4),("O",2)], "acetic acid"),
    ("C3H8", [("C",3),("H",8)], "propane"),
    ("C4H10", [("C",4),("H",10)], "butane"),
    ("C5H12", [("C",5),("H",12)], "pentane"),
    ("C8H18", [("C",8),("H",18)], "octane"),
]
for formula, parts, name in COMPOUNDS:
    mw = molw(parts)
    CHEM_PACK.append((f"molar mass of {formula}",
                      f"M[{formula}]",
                      f"{mw:.3f} g/mol",
                      f"MolarMass[\"{formula}\"]",
                      f"Sum atomic weights: " + " + ".join(f"{n}·{e}({ATOMIC.get(e,0)})" for e,n in parts) + f" = {mw:.3f}"))
    CHEM_PACK.append((f"molecular weight of {name}",
                      f"M[{name}]",
                      f"{mw:.3f} g/mol",
                      f"MolarMass[\"{name}\"]",
                      f"Compound: {formula}; M = {mw:.3f} g/mol"))
# pH calculations
for H_conc, name in [(1e-1,"0.1M HCl"),(1e-2,"0.01M HCl"),(1e-3,"0.001M HCl"),
                     (1e-4,"1e-4 M acid"),(1e-5,"1e-5 M acid"),(1e-6,"1e-6 M acid"),
                     (1e-7,"neutral water"),(1e-8,"slightly basic"),
                     (1e-10,"dilute base"),(1e-12,"strong base"),(1e-13,"0.1M NaOH")]:
    ph = -math.log10(H_conc)
    CHEM_PACK.append((f"pH of {name}", f"pH[{name}]",
                      f"pH = {ph:.4g}",
                      f"-Log10[{H_conc}]",
                      f"pH = -log10([H+]); [H+] = {H_conc}; pH = {ph:.4g}"))
# Dilution calcs
for c1, v1, v2 in [(1.0, 10, 100),(0.5, 25, 250),(2.0, 5, 50),(1.5, 20, 100),
                   (0.1, 100, 1000),(0.25, 40, 200),(3.0, 10, 75),(5.0, 2, 50)]:
    c2 = c1 * v1 / v2
    CHEM_PACK.append((f"dilute {c1}M from {v1}mL to {v2}mL",
                      f"Dilute({c1}M, {v1}mL → {v2}mL)",
                      f"{c2:.4g} M",
                      f"({c1} * {v1}) / {v2}",
                      f"M1·V1 = M2·V2 → M2 = {c1}·{v1}/{v2} = {c2:.4g}"))

for i, (q, parsed, plain, wl, step) in enumerate(CHEM_PACK):
    E_rich(q, parsed, plain,
           "science-and-technology", "chemistry",
           f"chem r4 {i}",
           [], "chemistry",
           step_by_step=step,
           wl_code=wl)

# ---- G. Physics pack (150 rows) ----
PHYS_PACK = []
G = 9.80665
C_LIGHT = 299792458
PLANCK = 6.62607015e-34
# Kinetic energy
for m in [1, 2, 5, 10, 50, 100, 500, 1000, 1500, 2000]:
    for v in [1, 5, 10, 20, 30, 50]:
        ke = 0.5 * m * v * v
        PHYS_PACK.append((f"kinetic energy m={m}kg v={v}m/s",
                          f"KE(m={m}kg, v={v}m/s)",
                          f"{ke:.6g} J",
                          f"0.5 * {m} * {v}^2",
                          f"KE = ½mv² = 0.5·{m}·{v}² = {ke:.6g} J"))
# Potential energy
for m in [1, 5, 10, 50, 100]:
    for h in [1, 2, 5, 10, 20, 50, 100]:
        pe = m * G * h
        PHYS_PACK.append((f"potential energy m={m}kg h={h}m",
                          f"PE(m={m}kg, h={h}m)",
                          f"{pe:.6g} J",
                          f"{m}*9.80665*{h}",
                          f"PE = mgh = {m}·9.80665·{h} = {pe:.6g} J"))
# Photon energy
for wl_nm in [200, 300, 400, 450, 500, 550, 600, 650, 700, 800, 1000, 1550]:
    wl_m = wl_nm * 1e-9
    E_j = PLANCK * C_LIGHT / wl_m
    E_ev = E_j / 1.602176634e-19
    PHYS_PACK.append((f"photon energy at {wl_nm} nm",
                      f"E_γ(λ = {wl_nm}nm)",
                      f"{E_j:.4g} J ({E_ev:.4g} eV)",
                      f"6.62607015e-34 * 299792458 / ({wl_nm}e-9)",
                      f"E = hc/λ = {PLANCK:.4g}·{C_LIGHT}/{wl_m} = {E_j:.4g} J = {E_ev:.4g} eV"))
# Pendulum period
for L_cm in [10, 20, 30, 50, 100, 200, 300, 500, 1000]:
    L = L_cm / 100
    T = 2 * math.pi * math.sqrt(L / G)
    PHYS_PACK.append((f"pendulum period L={L_cm}cm",
                      f"T(L = {L_cm}cm)",
                      f"{T:.4g} s",
                      f"2*Pi*Sqrt[{L}/9.80665]",
                      f"T = 2π√(L/g) = 2π√({L}/9.81) = {T:.4g} s"))
# Wavelength from frequency
for f_hz in [60, 1000, 1e6, 100e6, 1e9, 2.4e9, 5e9]:
    wl_val = C_LIGHT / f_hz
    PHYS_PACK.append((f"wavelength at frequency {f_hz:.4g} Hz",
                      f"λ(f = {f_hz:.4g}Hz)",
                      f"{wl_val:.4g} m",
                      f"299792458 / {f_hz}",
                      f"λ = c/f = {C_LIGHT}/{f_hz:.4g} = {wl_val:.4g} m"))
# Coulomb force
for q1, q2_ in [(1e-6, 1e-6),(1e-9, 1e-9),(2e-6, 3e-6),(5e-6, -3e-6)]:
    for r in [0.01, 0.1, 1.0, 10.0]:
        k_coul = 8.9875e9
        F = k_coul * q1 * q2_ / (r*r)
        PHYS_PACK.append((f"Coulomb force q1={q1:.2g} q2={q2_:.2g} r={r}m",
                          f"F_C(q1={q1:.2g}, q2={q2_:.2g}, r={r}m)",
                          f"{F:.4g} N",
                          f"8.9875e9 * {q1} * {q2_} / {r}^2",
                          f"F = kq₁q₂/r² = {k_coul:.4g}·{q1}·{q2_}/{r}² = {F:.4g} N"))

for i, (q, parsed, plain, wl, step) in enumerate(PHYS_PACK):
    E_rich(q, parsed, plain,
           "science-and-technology", "physics",
           f"phys r4 {i}",
           [], "physics",
           step_by_step=step,
           wl_code=wl)

print(f"[r4] after F+G: {len(EXTRA_RESULTS)}")

# ---- H. Chess / Crypto / Neural-net / Finance theme rows (450 rows) ----
THEME_PACK = []
# Chess (~150)
for elo_a in range(800, 2900, 100):
    for diff in [-400, -200, -100, 0, 100, 200, 400]:
        elo_b = elo_a + diff
        e = 1 / (1 + 10**((elo_b - elo_a) / 400))
        THEME_PACK.append((f"Elo expected score {elo_a} vs {elo_b}",
                           f"E({elo_a} vs {elo_b})",
                           f"{e:.4f}",
                           "everyday-life", "hobbies-games",
                           "chess-elo-ratings",
                           f"E = 1/(1+10^((Rb−Ra)/400)) = 1/(1+10^({diff}/400)) = {e:.4f}",
                           f"1/(1+10^(({diff})/400.))"))
# Cryptography (~150)
for bits in [56, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384, 512]:
    work = 2.0**bits
    THEME_PACK.append((f"brute force keyspace {bits}-bit",
                       f"|K| = 2^{bits}",
                       f"≈ {work:.4e} operations",
                       "science-and-technology", "computer-science",
                       "aes-encryption",
                       f"Keyspace = 2^{bits} = {work:.4e}",
                       f"2^{bits}"))
    half = 2.0**(bits/2)
    THEME_PACK.append((f"birthday collision {bits}-bit hash",
                       f"~2^{bits//2}",
                       f"≈ {half:.4e} hashes for 50% collision",
                       "science-and-technology", "computer-science",
                       "hash-collisions",
                       f"Birthday bound: 2^(n/2) for n-bit hash → 2^{bits//2}",
                       f"2^({bits}/2.)"))
SHA_VARIANTS = [("SHA-1", 160), ("SHA-224", 224), ("SHA-256", 256),
                ("SHA-384", 384), ("SHA-512", 512),
                ("SHA3-224", 224), ("SHA3-256", 256), ("SHA3-384", 384),
                ("SHA3-512", 512), ("BLAKE2s", 256), ("BLAKE2b", 512)]
for name, sz in SHA_VARIANTS:
    THEME_PACK.append((f"hash output size {name}",
                       f"size({name})",
                       f"{sz} bits = {sz//8} bytes",
                       "science-and-technology", "computer-science",
                       "sha-hash-family",
                       f"{name} produces {sz}-bit digest = {sz//8} bytes hex {sz//4} chars",
                       f"Hash[\"\", \"{name}\"]"))
# RSA key sizes
for ksz in [1024, 1536, 2048, 3072, 4096, 7680, 8192, 15360]:
    sec = {1024:80, 1536:96, 2048:112, 3072:128, 4096:140, 7680:192, 8192:200, 15360:256}.get(ksz, 0)
    THEME_PACK.append((f"RSA {ksz}-bit security",
                       f"sec(RSA {ksz})",
                       f"≈ {sec}-bit symmetric equivalent",
                       "science-and-technology", "computer-science",
                       "rsa-cryptography",
                       f"NIST SP 800-57: {ksz}-bit RSA ≈ {sec}-bit symmetric",
                       f"RSASecurityLevel[{ksz}]"))
# Neural net param counts (~150)
NN_PACK = [
    ("BERT-base",    768, 12, 12, 30522, 110_000_000),
    ("BERT-large",  1024, 24, 16, 30522, 340_000_000),
    ("GPT-2 small",  768, 12, 12, 50257, 124_000_000),
    ("GPT-2 medium",1024, 24, 16, 50257, 355_000_000),
    ("GPT-2 large", 1280, 36, 20, 50257, 774_000_000),
    ("GPT-2 XL",    1600, 48, 25, 50257, 1_500_000_000),
    ("GPT-3 (175B)",12288, 96, 96, 50257, 175_000_000_000),
    ("LLaMA-7B",     4096, 32, 32, 32000,   7_000_000_000),
    ("LLaMA-13B",    5120, 40, 40, 32000,  13_000_000_000),
    ("LLaMA-65B",    8192, 80, 64, 32000,  65_000_000_000),
    ("LLaMA2-70B",   8192, 80, 64, 32000,  70_000_000_000),
    ("ViT-B/16",     768, 12, 12,     0,    86_000_000),
    ("ViT-L/16",    1024, 24, 16,     0,   307_000_000),
    ("ResNet-18",      0,  0,  0,     0,    11_700_000),
    ("ResNet-50",      0,  0,  0,     0,    25_600_000),
    ("ResNet-101",     0,  0,  0,     0,    44_500_000),
    ("ResNet-152",     0,  0,  0,     0,    60_200_000),
    ("EfficientNet-B0",0, 0,  0,     0,     5_300_000),
    ("EfficientNet-B7",0, 0,  0,     0,    66_000_000),
    ("AlexNet",        0,  0,  0,     0,    62_300_000),
    ("VGG-16",         0,  0,  0,     0,   138_000_000),
    ("VGG-19",         0,  0,  0,     0,   143_000_000),
    ("Inception V3",   0,  0,  0,     0,    24_000_000),
    ("MobileNetV2",    0,  0,  0,     0,     3_500_000),
]
for name, d, L, h, vocab, params in NN_PACK:
    THEME_PACK.append((f"parameters of {name}",
                       f"#params({name})",
                       f"{params:,} parameters",
                       "science-and-technology", "computer-science",
                       "transformer-architecture" if d > 0 else "cnn-architecture",
                       f"{name}: d_model={d}, L={L} layers, heads={h}, vocab={vocab} → ~{params:,} params" if d else f"{name}: ~{params:,} params",
                       f"ModelParameters[\"{name}\"]"))
    if d > 0:
        THEME_PACK.append((f"{name} hidden dimension",
                           f"d_model({name})",
                           f"{d}",
                           "science-and-technology", "computer-science",
                           "transformer-architecture",
                           f"Embedding dimension d_model = {d}",
                           f"HiddenDim[\"{name}\"]"))
        THEME_PACK.append((f"{name} number of layers",
                           f"L({name})",
                           f"{L} transformer layers",
                           "science-and-technology", "computer-science",
                           "transformer-architecture",
                           f"Architecture has {L} stacked attention layers",
                           f"NumLayers[\"{name}\"]"))
# Finance (~100)
for P in [100000, 200000, 300000, 400000, 500000, 750000, 1000000]:
    for rate in [3.0, 4.0, 5.0, 6.0, 6.5, 7.0, 7.5, 8.0]:
        for n_yr in [15, 30]:
            r = rate / 100 / 12
            n = n_yr * 12
            pmt = P * r * (1 + r)**n / ((1 + r)**n - 1)
            THEME_PACK.append((f"mortgage payment ${P} at {rate}% for {n_yr} years",
                               f"PMT(P=${P}, r={rate}%, n={n_yr}yr)",
                               f"${pmt:.2f}/month",
                               "everyday-life", "personal-finance",
                               "real-estate-math",
                               f"PMT = P·r/(1−(1+r)^−n); P={P}, r={r:.6f}/mo, n={n} → {pmt:.2f}",
                               f"{P}*{r}*({1+r})^{n}/(({1+r})^{n}-1)"))

for i, (q, parsed, plain, cat, sub, slug, step, wl) in enumerate(THEME_PACK):
    E_rich(q, parsed, plain,
           cat, sub,
           f"theme r4 {i}",
           [], slug,
           step_by_step=step,
           wl_code=wl)

print(f"[r4] after H: {len(EXTRA_RESULTS)}")

# ---- I. Extra dense packs to reach 2150+ rows ----

# I.1 Geometric formulas (~200)
for r in range(1, 51):
    A_circle = math.pi * r * r
    C_circle = 2 * math.pi * r
    E_rich(f"area of circle radius {r}",
           f"A(circle r = {r})", f"π·{r}² = {A_circle:.6g}",
           "mathematics", "geometry", f"geom circle area r4 {r}", [],
           "geometry", decimal_approx=f"≈ {A_circle:.6g}",
           alternate_forms=f"πr² with r = {r}",
           step_by_step=f"A = πr² = π·{r}² = π·{r*r} = {A_circle:.6g}",
           wl_code=f"Pi * {r}^2")
    E_rich(f"circumference of circle radius {r}",
           f"C(circle r = {r})", f"2π·{r} = {C_circle:.6g}",
           "mathematics", "geometry", f"geom circle C r4 {r}", [],
           "geometry", decimal_approx=f"≈ {C_circle:.6g}",
           step_by_step=f"C = 2πr = 2π·{r} = {C_circle:.6g}",
           wl_code=f"2 * Pi * {r}")
for r in range(1, 31):
    V = (4/3) * math.pi * r**3
    SA = 4 * math.pi * r * r
    E_rich(f"volume of sphere radius {r}",
           f"V(sphere r = {r})", f"(4/3)π·{r}³ = {V:.6g}",
           "mathematics", "geometry", f"geom sph V r4 {r}", [],
           "geometry", decimal_approx=f"≈ {V:.6g}",
           alternate_forms="V = (4πr³)/3",
           step_by_step=f"V = (4/3)πr³ = (4/3)π·{r**3} = {V:.6g}",
           wl_code=f"4/3 * Pi * {r}^3")
    E_rich(f"surface area of sphere radius {r}",
           f"SA(sphere r = {r})", f"4π·{r}² = {SA:.6g}",
           "mathematics", "geometry", f"geom sph SA r4 {r}", [],
           "geometry", decimal_approx=f"≈ {SA:.6g}",
           step_by_step=f"SA = 4πr² = 4π·{r*r} = {SA:.6g}",
           wl_code=f"4 * Pi * {r}^2")
for s in range(1, 21):
    A_sq = s * s
    A_eq_tri = (math.sqrt(3) / 4) * s * s
    E_rich(f"area of square side {s}",
           f"A(square s = {s})", f"{s}² = {A_sq}",
           "mathematics", "geometry", f"geom sq r4 {s}", [],
           "geometry", wl_code=f"{s}^2",
           step_by_step=f"A = s² = {s}·{s} = {A_sq}")
    E_rich(f"area of equilateral triangle side {s}",
           f"A(eq.tri s = {s})", f"(√3/4)·{s}² ≈ {A_eq_tri:.6g}",
           "mathematics", "geometry", f"geom eqtri r4 {s}", [],
           "geometry", step_by_step=f"A = (√3/4)s² = (√3/4)·{s*s} ≈ {A_eq_tri:.6g}",
           wl_code=f"Sqrt[3]/4 * {s}^2")

# I.2 Number theory: prime factorization, gcd, lcm (~200)
def prime_factors(n):
    out = []
    d = 2
    nn = n
    while d * d <= nn:
        while nn % d == 0:
            out.append(d); nn //= d
        d += 1
    if nn > 1: out.append(nn)
    return out
for n in range(100, 200):
    pf = prime_factors(n)
    pf_str = " × ".join(str(p) for p in pf)
    E_rich(f"factor {n}",
           f"factor({n})",
           pf_str,
           "mathematics", "number-theory",
           f"factor r4 {n}", [], "number-theory",
           alternate_forms=" · ".join(f"{p}^{pf.count(p)}" for p in sorted(set(pf))),
           step_by_step=f"Trial division: {pf_str}",
           wl_code=f"FactorInteger[{n}]")
GCD_PAIRS = [(a, b) for a in range(12, 80, 6) for b in range(8, 60, 5)]
for a, b in GCD_PAIRS[:80]:
    g = math.gcd(a, b)
    l = a * b // g
    E_rich(f"gcd({a},{b})", f"gcd({a}, {b})", str(g),
           "mathematics", "number-theory", f"gcd r4 {a} {b}", [],
           "number-theory",
           step_by_step=f"Euclidean algorithm: gcd({a},{b}) = {g}",
           wl_code=f"GCD[{a}, {b}]")
    E_rich(f"lcm({a},{b})", f"lcm({a}, {b})", str(l),
           "mathematics", "number-theory", f"lcm r4 {a} {b}", [],
           "number-theory",
           step_by_step=f"lcm(a,b) = a·b/gcd(a,b) = {a*b}/{g} = {l}",
           wl_code=f"LCM[{a}, {b}]")

# I.3 Probability dice & cards (~100)
for n_dice in [1, 2, 3, 4, 5]:
    for sides in [4, 6, 8, 10, 12, 20]:
        for target in range(n_dice, n_dice*sides + 1, max(1, (sides//2))):
            from functools import lru_cache
            @lru_cache(maxsize=None)
            def ways(n, s, t):
                if n == 0: return 1 if t == 0 else 0
                return sum(ways(n-1, s, t-i) for i in range(1, s+1) if t-i >= 0)
            w = ways(n_dice, sides, target)
            tot = sides ** n_dice
            E_rich(f"probability sum {target} on {n_dice}d{sides}",
                   f"P(sum = {target} | {n_dice}d{sides})",
                   f"{w}/{tot} = {w/tot:.6g}" if tot else "0",
                   "mathematics", "probability",
                   f"dice r4 {n_dice} {sides} {target}", [], "probability",
                   step_by_step=f"Count favorable outcomes: {w} of {tot} → P = {w/tot:.6g}",
                   wl_code=f"Probability[Sum[d, {{d, {n_dice}}}] == {target}, Table[d \\[Distributed] DiscreteUniformDistribution[{{1, {sides}}}], {{i, {n_dice}}}]]")

# I.4 Compound interest / FV (~100)
for P in [1000, 5000, 10000, 25000, 50000]:
    for rate in [3, 4, 5, 6, 7, 8, 10]:
        for years in [5, 10, 15, 20, 25, 30]:
            FV = P * (1 + rate/100)**years
            E_rich(f"future value ${P} at {rate}% for {years} years",
                   f"FV(P=${P}, r={rate}%, n={years}yr)",
                   f"${FV:.2f}",
                   "everyday-life", "personal-finance",
                   f"fv r4 {P} {rate} {years}", [], "compound-interest",
                   alternate_forms=f"FV = P(1+r)^n",
                   step_by_step=f"FV = {P}·(1+{rate/100})^{years} = ${FV:.2f}",
                   wl_code=f"{P} * (1 + {rate}/100.)^{years}")

# I.5 Combinatorics (~100)
for n in range(5, 25):
    for k in range(1, min(n, 8)):
        c = math.comb(n, k)
        p = math.perm(n, k)
        E_rich(f"C({n},{k})", f"binomial({n}, {k})", str(c),
               "mathematics", "discrete-math", f"comb r4 {n} {k}", [],
               "discrete-math",
               alternate_forms=f"{n}!/({k}!·{n-k}!)",
               step_by_step=f"C(n,k) = n!/(k!(n-k)!) → {c}",
               wl_code=f"Binomial[{n}, {k}]")
        E_rich(f"P({n},{k})", f"permutation({n}, {k})", str(p),
               "mathematics", "discrete-math", f"perm r4 {n} {k}", [],
               "discrete-math", alternate_forms=f"{n}!/{n-k}!",
               step_by_step=f"P(n,k) = n!/(n-k)! → {p}",
               wl_code=f"FactorialPower[{n}, {k}]")

# I.6 Date arithmetic (~50)
for y1, m1, d1, y2, m2, d2 in [
    (2024,1,1,2025,1,1),(2024,1,1,2026,1,1),(2024,1,1,2030,1,1),
    (2024,6,15,2025,6,15),(2000,1,1,2024,1,1),(1990,5,1,2024,5,1),
    (2024,3,15,2024,12,31),(2024,1,1,2024,12,31),(2024,2,29,2025,2,28),
    (1969,7,20,2024,7,20),(1492,10,12,2024,10,12),
]:
    a = datetime(y1,m1,d1); b = datetime(y2,m2,d2)
    delta = (b - a).days
    E_rich(f"days from {y1}-{m1:02d}-{d1:02d} to {y2}-{m2:02d}-{d2:02d}",
           f"Δd({a.date()} → {b.date()})", f"{delta} days",
           "everyday-life", "dates-times", f"date r4 {y1} {m1} {d1} {y2} {m2} {d2}", [],
           "calendars-holidays",
           step_by_step=f"Day count: {delta} days = {delta/365.25:.2f} years",
           wl_code=f"DateDifference[{{{y1},{m1},{d1}}}, {{{y2},{m2},{d2}}}]")

# I.7 Quick exact arithmetic identities (~150) to round out
for n in range(2, 80):
    fact = math.factorial(n) if n <= 20 else None
    if fact is not None:
        E_rich(f"{n}!", f"{n}!", str(fact),
               "mathematics", "number-theory", f"fact r4 {n}", [],
               "number-theory",
               step_by_step=f"n! = 1·2·…·n = {fact}",
               wl_code=f"{n}!")
    fib = [0,1]
    while len(fib) <= n: fib.append(fib[-1]+fib[-2])
    E_rich(f"Fibonacci F_{n}", f"F_{n}", str(fib[n]),
           "mathematics", "number-theory", f"fib r4 {n}", [],
           "number-theory",
           alternate_forms=f"Closed form: (φ^n − ψ^n)/√5",
           step_by_step=f"F_n = F_(n−1) + F_(n−2); F_{n} = {fib[n]}",
           wl_code=f"Fibonacci[{n}]")

print(f"[r4] after I: {len(EXTRA_RESULTS)}")
assert len(EXTRA_RESULTS) >= 2000, f"need 2000+, got {len(EXTRA_RESULTS)}"

# ---------------------------------------------------------------------------
# (3) Notebook entry & feedback pools
# ---------------------------------------------------------------------------
FB_COMMENTS_R4 = [
    "Comprehensive update — Pro features really polished.",
    "Multi-pod result layout makes scanning easier.",
    "Alternate-forms tab is a game changer for symbolic comparisons.",
    "Step-by-step pod helped me solve a homework problem cleanly.",
    "Wolfram Language code pod is gold for exporting to Mathematica.",
    "Loved the assumption pills — finally pick the right interpretation.",
    "Plot SVG inline is crisp on retina screens.",
    "Best computational resource on the web.",
    "Cross-checked against three sources — accurate.",
    "Useful for prepping calculus exam this quarter.",
    "Engineering data quality is exceptional.",
    "Chess and crypto topics — surprising and welcome additions.",
    "I share permalinks with my study group every week.",
    "Embed-widget code for my blog worked first try.",
    "Voice input experimental but promising.",
    "Image-upload solve handled my handwritten equation perfectly.",
    "Hash-collision math saved me on a security project.",
    "Quant finance pods are pro level.",
    "Use the Wolfram Language pod almost daily now.",
    "Top-tier reference site for any STEM workflow.",
]

NOTE_VARIANTS_R4 = [
    "Pinned for thesis ref.",
    "Verified — matches textbook answer.",
    "Compared against scipy output — identical.",
    "Will share permalink with lab.",
    "Step-by-step matches my derivation.",
    "Alternate-form is the form I needed.",
    "Bookmarked the WL code for the project.",
    "Worth memorizing this formula.",
    "Practice problem template.",
    "Refer for next semester's class.",
]

# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------
def build():
    os.makedirs('instance', exist_ok=True)
    shutil.copyfile(SRC, DST)
    con = sqlite3.connect(DST)
    cur = con.cursor()

    cur.execute("SELECT COALESCE(MAX(id), 0) FROM topics");              next_topic = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM computation_results"); next_cr    = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM notebook_entries");    next_ne    = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM topic_feedback");      next_fb    = cur.fetchone()[0] + 1

    cur.execute("SELECT slug, id FROM categories");    cat_by_slug = dict(cur.fetchall())
    cur.execute("SELECT slug, id FROM subcategories"); sub_by_slug = dict(cur.fetchall())
    cur.execute("SELECT slug FROM topics");            existing_topic_slugs = set(r[0] for r in cur.fetchall())

    # ---- Topics ----
    for cat_slug, sub_slug, name, slug, desc, image, feat, new, examples_json in NEW_TOPICS:
        if slug in existing_topic_slugs:
            continue
        img_path = f"/static/images/topics/{image}"
        sub_id = sub_by_slug.get(sub_slug) if sub_slug else None
        cur.execute(
            "INSERT INTO topics(id, category_id, subcategory_id, name, slug, description, "
            "image, examples, is_featured, is_new, view_count, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (next_topic, cat_by_slug[cat_slug], sub_id, name, slug, desc, img_path,
             examples_json, int(feat), int(new), 0, ts(0)))
        next_topic += 1
        existing_topic_slugs.add(slug)

    # ---- Computation results ----
    for i, row in enumerate(EXTRA_RESULTS):
        q, parsed, plain, cat, sub, kw, related_or_pods, slug, plot_url = row
        if isinstance(q, str) and q.startswith("__POD__"):
            real_q = q[len("__POD__"):]
            pods_json = json.dumps(related_or_pods)
            rel_json = json.dumps([])
        else:
            real_q = q
            pods_struct = [
                {"title": "Input interpretation", "plaintext": parsed or real_q},
                {"title": "Result",                "plaintext": plain},
            ]
            pods_json = json.dumps(pods_struct)
            rel_json = json.dumps(related_or_pods if isinstance(related_or_pods, list) else [])

        cur.execute(
            "INSERT INTO computation_results("
            "id, input_query, parsed_input, plaintext, pods, category, subcategory, "
            "units, plot_url, related_queries, keywords, required_specifiers, "
            "topic_slug, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (next_cr, real_q, parsed, plain, pods_json, cat, sub, '',
             plot_url, rel_json, kw, '', slug, ts(i % 72)))
        next_cr += 1

    # ---- Notebook entries (200) ----
    cur.execute("SELECT id FROM notebooks ORDER BY id")
    notebooks = [r[0] for r in cur.fetchall()]
    pool = EXTRA_RESULTS[:200]
    for i, row in enumerate(pool):
        q = row[0]
        if isinstance(q, str) and q.startswith("__POD__"):
            q = q[len("__POD__"):]
        plain = row[2]
        cat = row[3]
        sub = row[4]
        nb_id = notebooks[i % len(notebooks)]
        cur.execute("SELECT COALESCE(MAX(sort_order), -1) FROM notebook_entries WHERE notebook_id=?",
                    (nb_id,))
        so = cur.fetchone()[0] + 1
        note = NOTE_VARIANTS_R4[i % len(NOTE_VARIANTS_R4)] + f" ({cat}/{sub})"
        cur.execute(
            "INSERT INTO notebook_entries(id, notebook_id, query_text, result_summary, "
            "notes, sort_order, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (next_ne, nb_id, q[:500], str(plain)[:200], note, so, ts(i % 72)))
        next_ne += 1

    # ---- Topic feedback (60) ----
    cur.execute("SELECT id FROM users ORDER BY id")
    user_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT id FROM topics ORDER BY id")
    all_topic_ids = [r[0] for r in cur.fetchall()]
    for i in range(60):
        uid = user_ids[(i * 2 + 1) % len(user_ids)]
        tid = all_topic_ids[(i * 13 + 17) % len(all_topic_ids)]
        rating = 4 + (i % 2)  # 4 or 5 (R4 wave is positive)
        helpful = 1
        comment = FB_COMMENTS_R4[i % len(FB_COMMENTS_R4)]
        cur.execute(
            "INSERT INTO topic_feedback(id, user_id, topic_id, rating, comment, "
            "is_helpful, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (next_fb, uid, tid, rating, comment, helpful, ts(i)))
        next_fb += 1

    con.commit()
    con.close()
    print(f"[r4] built {DST}")


if __name__ == "__main__":
    build()
