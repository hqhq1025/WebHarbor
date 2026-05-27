"""Phase 2 seeders: File: namespace, forum threads/posts, article comments,
sitenotices, user blocks, follows, watchlist seeds, wiki subscriptions,
and additional bot/reader/editor users.

All function-level idempotent. Imported from seed_data.py lazily.
"""
import json
import os
import re
import random
from datetime import datetime, timedelta
from pathlib import Path


BASE_TS = datetime(2026, 5, 1, 12, 0, 0)


# --- Procedural data sources ---

MCU_FILE_LABELS = [
    ("Iron Man Poster", "2008 Theatrical"),
    ("Iron Man 2 Poster", "2010"),
    ("Iron Man 3 Poster", "2013"),
    ("Thor Poster", "2011"),
    ("Thor Dark World Poster", "2013"),
    ("Thor Ragnarok Poster", "2017"),
    ("Thor Love Thunder Poster", "2022"),
    ("Captain America First Avenger", "2011"),
    ("Captain America Winter Soldier", "2014"),
    ("Captain America Civil War", "2016"),
    ("Captain America Brave New World", "2025"),
    ("Avengers Poster 2012", "Phase One Finale"),
    ("Avengers Age of Ultron", "2015"),
    ("Avengers Infinity War", "2018"),
    ("Avengers Endgame", "2019"),
    ("Guardians of the Galaxy", "2014"),
    ("Guardians Vol 2", "2017"),
    ("Guardians Vol 3", "2023"),
    ("Doctor Strange", "2016"),
    ("Doctor Strange Multiverse of Madness", "2022"),
    ("Black Panther", "2018"),
    ("Black Panther Wakanda Forever", "2022"),
    ("Spider-Man Homecoming", "2017"),
    ("Spider-Man Far From Home", "2019"),
    ("Spider-Man No Way Home", "2021"),
    ("Spider-Man Brand New Day", "2026"),
    ("Ant-Man", "2015"),
    ("Ant-Man Wasp Quantumania", "2023"),
    ("Captain Marvel", "2019"),
    ("The Marvels", "2023"),
    ("Eternals", "2021"),
    ("Shang-Chi", "2021"),
    ("Black Widow Movie", "2021"),
    ("Deadpool Wolverine", "2024"),
    ("Fantastic Four First Steps", "2025"),
    ("WandaVision Promo", "Disney+ 2021"),
    ("Falcon Winter Soldier Promo", "Disney+ 2021"),
    ("Loki Series Promo", "Disney+ 2021"),
    ("Hawkeye Series Promo", "Disney+ 2021"),
    ("Moon Knight Promo", "Disney+ 2022"),
    ("Ms Marvel Promo", "Disney+ 2022"),
    ("She-Hulk Promo", "Disney+ 2022"),
    ("Echo Promo", "Disney+ 2024"),
    ("Agatha All Along Promo", "Disney+ 2024"),
    ("Daredevil Born Again", "Disney+ 2025"),
    ("Ironheart Promo", "Disney+ 2025"),
    ("Secret Invasion Promo", "Disney+ 2023"),
    ("Mjolnir Replica", "Property of Asgard"),
    ("Stormbreaker Concept", "Forged on Nidavellir"),
    ("Vibranium Shield", "Captain America"),
    ("Infinity Gauntlet Replica", "Six stones"),
    ("Iron Man Mark I Concept", "Cave Build"),
    ("Iron Man Mark XLVI", "Civil War"),
    ("Iron Spider Suit", "Stark tech"),
    ("Web Shooters", "Peter Parker"),
    ("Eye of Agamotto", "Time Stone"),
    ("Cloak of Levitation", "Sanctum"),
    ("Wakanda Throne", "Royal Palace"),
    ("Kamar-Taj Library", "Mystic Arts"),
    ("Avengers Tower Logo", "Stark Industries"),
    ("Avengers Compound Sign", "Upstate NY"),
    ("Quinjet Concept", "Avengers Transport"),
    ("Stark Tower NYC", "Skyscraper"),
    ("Sanctum Sanctorum", "177A Bleecker St"),
    ("Wakandan Border Tribe", "Vibranium"),
    ("Asgard Bifrost", "Realm Eternal"),
    ("Sokovia Battlefield", "Age of Ultron"),
    ("Battle of Earth Site", "Endgame"),
    ("New Asgard Norway", "Refugee Settlement"),
    ("Titan Surface", "Thanos Homeworld"),
    ("Knowhere Mining", "Celestial Skull"),
    ("Concept Art - Avengers", "Pre-production"),
    ("Storyboard - Endgame Battle", "VFX"),
    ("Production Still - Civil War", "Behind the Scenes"),
    ("Costume Sketch - Captain America", "Phase 1"),
    ("Set Photo - Wakanda", "Atlanta"),
    ("Premiere Photo - Avengers", "Hollywood"),
    ("Comic-Con Panel 2019", "Hall H"),
    ("D23 Reveal Slate", "Phase 5/6/7"),
    ("Box Office Chart MCU", "All-Time"),
    ("Stan Lee Cameo Compilation", "Generations of Cameos"),
]

SW_FILE_LABELS = [
    ("A New Hope Poster", "1977"),
    ("Empire Strikes Back Poster", "1980"),
    ("Return of the Jedi Poster", "1983"),
    ("Phantom Menace Poster", "1999"),
    ("Attack of the Clones Poster", "2002"),
    ("Revenge of the Sith Poster", "2005"),
    ("Force Awakens Poster", "2015"),
    ("Last Jedi Poster", "2017"),
    ("Rise of Skywalker Poster", "2019"),
    ("Rogue One Poster", "2016"),
    ("Solo Poster", "2018"),
    ("Mandalorian Promo", "Disney+ 2019"),
    ("Mandalorian S2", "Disney+ 2020"),
    ("Boba Fett Series Promo", "Disney+ 2021"),
    ("Obi-Wan Series Promo", "Disney+ 2022"),
    ("Andor Promo", "Disney+ 2022"),
    ("Andor S2 Promo", "Disney+ 2025"),
    ("Ahsoka Promo", "Disney+ 2023"),
    ("Acolyte Promo", "Disney+ 2024"),
    ("Skeleton Crew Promo", "Disney+ 2024"),
    ("Bad Batch Promo", "Disney+ 2021"),
    ("Clone Wars Animated", "TV 2008-2020"),
    ("Rebels Animated", "TV 2014-2018"),
    ("Resistance Animated", "TV 2018-2020"),
    ("Visions Animated", "Anthology"),
    ("Lightsaber Anakin Replica", "Padawan-built"),
    ("Lightsaber Luke Replica", "Skywalker Saga"),
    ("Lightsaber Mace Replica", "Purple Crystal"),
    ("Lightsaber Darth Maul", "Double-blade"),
    ("Stormtrooper Helmet White", "Imperial"),
    ("Stormtrooper Helmet First Order", "Black trim"),
    ("Boba Fett Helmet T-visor", "Mandalorian"),
    ("Darth Vader Helmet", "Sith Lord"),
    ("Kylo Ren Helmet", "Crackled vader homage"),
    ("X-wing Model", "Red Squadron"),
    ("Y-wing Model", "Gold Squadron"),
    ("TIE Fighter Model", "Imperial swarm"),
    ("Death Star Model", "Galactic Weapon"),
    ("Millennium Falcon Concept", "Smuggler ship"),
    ("Star Destroyer Wedge", "Capital ship"),
    ("AT-AT Walker", "Hoth assault"),
    ("Speeder Bike", "Endor chase"),
    ("Tatooine Sands", "Outer Rim"),
    ("Dagobah Swamp", "Jedi training"),
    ("Hoth Ice Caves", "Rebel base"),
    ("Endor Forest", "Ewok village"),
    ("Coruscant Cityscape", "Galactic capital"),
    ("Naboo Theed Palace", "Royal"),
    ("Mustafar Lava", "Vader citadel"),
    ("Mos Eisley Cantina", "Wretched hive"),
    ("Jedi Temple Coruscant", "Order destroyed"),
    ("Death Star Throne", "Emperor's chamber"),
    ("Starkiller Base", "First Order weapon"),
    ("Exegol", "Sith homeworld"),
    ("Ahch-To", "First Jedi Temple"),
    ("Crait Salt Flats", "Last Jedi battle"),
    ("Geonosis Arena", "Clone Wars start"),
    ("Concept Art Ralph McQuarrie", "Original trilogy"),
    ("Storyboard Empire Strikes Back", "Cinematic"),
    ("Trailer Frame Force Awakens", "Marketing"),
    ("Premiere Empire Strikes Back 1980", "Historic"),
    ("Comic-Con Star Wars Panel", "Hall H"),
    ("Lucasfilm Logo", "Brand mark"),
    ("Skywalker Saga Box Set", "9-film collection"),
    ("Galaxy's Edge Theme Park", "Disney"),
    ("LEGO Star Wars Diorama", "Cultural"),
    ("Cosplay Group Convention", "501st Legion"),
]

GS_FILE_LABELS = [
    ("Genshin Impact Promo Art", "v1.0 Launch 2020"),
    ("Genshin Impact 1.1 Promo", "Childe"),
    ("Genshin Impact 1.2 Promo", "Dragonspine"),
    ("Genshin Impact 2.0 Inazuma", "Major update"),
    ("Genshin Impact 2.5 Yae Miko", "Electro 5-star"),
    ("Genshin Impact 3.0 Sumeru", "Dendro nation"),
    ("Genshin Impact 4.0 Fontaine", "Hydro nation"),
    ("Genshin Impact 5.0 Natlan", "Pyro nation"),
    ("Genshin Impact 4.6 Arlecchino", "Fatui Harbinger"),
    ("HoYoverse Logo", "Studio brand"),
    ("Mihoyo Tech Otaku", "Technology"),
    ("Liyue Concept Painting", "Chinese inspired"),
    ("Mondstadt Concept Painting", "Germanic inspired"),
    ("Inazuma Concept Painting", "Japanese inspired"),
    ("Sumeru Concept Painting", "Persian Indian"),
    ("Fontaine Concept Painting", "French inspired"),
    ("Natlan Concept Painting", "Mesoamerican"),
    ("Snezhnaya Concept Sketch", "Russian inspired"),
    ("Khaenri'ah Lore", "Fallen civilization"),
    ("Zhongli Splash Art", "Geo Archon"),
    ("Venti Splash Art", "Anemo Archon"),
    ("Raiden Splash Art", "Electro Archon"),
    ("Nahida Splash Art", "Dendro Archon"),
    ("Furina Splash Art", "Hydro Archon"),
    ("Mavuika Splash Art", "Pyro Archon"),
    ("Tsaritsa Concept", "Cryo Archon"),
    ("Traveler Lumine", "Outlander"),
    ("Traveler Aether", "Outlander"),
    ("Paimon Mascot", "Emergency food"),
    ("Anemo Vision", "Resonance element"),
    ("Geo Vision", "Resonance element"),
    ("Electro Vision", "Resonance element"),
    ("Hydro Vision", "Resonance element"),
    ("Pyro Vision", "Resonance element"),
    ("Cryo Vision", "Resonance element"),
    ("Dendro Vision", "Resonance element"),
    ("Wolfsgravestone Weapon", "Claymore"),
    ("Staff of Homa Weapon", "Polearm"),
    ("Aqua Simulacra Weapon", "Bow"),
    ("Skyward Atlas", "Catalyst"),
    ("Mistsplitter Reforged", "Sword"),
    ("Mondstadt Cathedral", "Favonius HQ"),
    ("Liyue Harbor", "Trading port"),
    ("Inazuma Tenshukaku", "Shogun's palace"),
    ("Sumeru Akademiya", "Six Darshans"),
    ("Fontaine Court of Justice", "Hydro tribunal"),
    ("Natlan Volcano", "Stadium of the Sacred Flame"),
    ("Dragonspine Peak", "Snow region"),
    ("The Chasm", "Underground"),
    ("Enkanomiya", "Sub-Inazuma"),
    ("Sea of Bygone Eras", "Old Iktomi"),
    ("Lantern Rite Festival", "Liyue annual"),
    ("Windblume Festival", "Mondstadt annual"),
    ("Irodori Festival", "Inazuma"),
    ("Sabzeruz Festival", "Sumeru"),
    ("Concert 2022 Melodies", "Symphony"),
    ("Concert 2023 Symphony", "Live orchestra"),
    ("Concert 2024 Orchestra", "Crossover"),
    ("HoYoFAIR 2024 Showcase", "Community"),
    ("Genshin Anniversary 1st", "September 2021"),
    ("Genshin Anniversary 3rd", "Tianqiu Treasure"),
    ("Genshin Anniversary 5th", "Natlan reveal"),
]


def _slugify_filename(text):
    s = "".join(c if c.isalnum() or c in "._-" else "_" for c in text)
    return s


def seed_files():
    from app import db, Wiki, FileAsset
    if FileAsset.query.count() > 0:
        return
    plans = [
        ("mcu", MCU_FILE_LABELS),
        ("starwars", SW_FILE_LABELS),
        ("genshin", GS_FILE_LABELS),
    ]
    uploaders = ["WikiBot", "StarkFan42", "LucasCanon", "HoYoLore",
                 "InfinityScribe", "EnabranTain", "ShinyCelestia", "AliceJ",
                 "BobK", "CarolS", "DanR"]
    for wiki_slug, items in plans:
        w = Wiki.query.filter_by(slug=wiki_slug).first()
        for idx, (label, sub) in enumerate(items):
            fn = f"{wiki_slug}_file_{_slugify_filename(label.lower().replace(' ', '_'))}.jpg"
            uploader = uploaders[(idx + hash(wiki_slug)) % len(uploaders)]
            uploaded_at = BASE_TS - timedelta(days=(idx * 7) % 800 + 5)
            f = FileAsset(
                wiki_id=w.id,
                filename=fn,
                display_name=label,
                description=f"{label}. {sub}. Uploaded for {w.name} archive.",
                license="Fair use",
                uploader_id=None,
                uploader_label=uploader,
                bytes_size=120_000 + (idx * 1037) % 800_000,
                width=800,
                height=600,
                uploaded_at=uploaded_at,
                mime_type="image/jpeg",
            )
            db.session.add(f)
    db.session.commit()
    # Now link uploaders to users where matchable
    from app import User
    for f in FileAsset.query.all():
        u = User.query.filter_by(username=f.uploader_label).first()
        if u:
            f.uploader_id = u.id
    db.session.commit()


def seed_extra_users():
    """Add ~80 background contributors so Active Users / Top Editors aren't sparse."""
    from app import db, User
    if User.query.filter_by(username="EditorEcho_001").first():
        return
    seeds = []
    base_names = [
        "EditorEcho", "ContribCat", "WikiBee", "LoreLizard", "PageDragon",
        "ScrollSage", "QuillFox", "CategoryCrane", "InfoboxIbis", "DiffDeer",
        "TalkOwl", "TemplateTiger", "HistoryHare", "DraftDeer", "NewbiePanda",
        "AccountantBat", "RollbackRobin", "BureaucratBeagle", "SysopSquirrel", "BotBird",
    ]
    for name in base_names:
        for k in range(4):  # 80 total
            username = f"{name}_{k:03d}"
            color = f"#{random.Random(name + str(k)).randint(0, 0xffffff):06x}"
            joined = BASE_TS - timedelta(days=200 + (hash(username) % 1500))
            u = User(
                email=f"{username.lower()}@reader.test",
                username=username,
                bio=f"Background contributor — {name.replace('_', ' ')} role.",
                groups="autoconfirmed" if k > 0 else "autoconfirmed,rollback",
                avatar_color=color,
                joined=joined,
                home_wiki=["mcu", "starwars", "genshin", ""][k],
            )
            u.set_password("Reader_Password_2024!")
            seeds.append(u)
            db.session.add(u)
    db.session.commit()


def seed_forum_threads():
    from app import db, Wiki, ForumThread, ForumPost, slugify
    if ForumThread.query.count() > 0:
        return
    THREADS = {
        "mcu": [
            ("General", "What is your favorite MCU phase?",
             "I keep going back and forth between Phase One and the Infinity Saga. Phase Three was a masterclass in payoff. Phase Four had Loki and Moon Knight but felt scattered. What say you?"),
            ("Theories", "Did Endgame actually create a multiverse?",
             "If Steve went back without erasing the alternate timelines, those branches still exist. Loki S2 confirmed branching is the default until pruned. Discuss the timeline math."),
            ("News", "Doomsday and Secret Wars release plan",
             "Marvel slated Avengers: Doomsday for Dec 2026 and Secret Wars for May 2027 at SDCC 2024. RDJ returning as Doom is the casting bombshell of the decade."),
            ("Lore", "Why didn't Iron Man build a Mark 86?",
             "Stark canonically built 85 suits. The Mark 85 was bleeding-edge nanotech and got destroyed in Endgame. Could Riri Williams be considered the spiritual Mark 86?"),
            ("Off-topic", "Best MCU soundtrack moments",
             "Captain America: Civil War's airport scene with Henry Jackman, vs The Avengers theme by Silvestri — which scored you harder?"),
            ("Theories", "Mutants in the MCU: how soon?",
             "Ms Marvel revealed Kamala has 'mutation' in her genes. The Marvels teased the X-Men theme. Are we getting mutants in Phase 6 or earlier?"),
            ("News", "Daredevil: Born Again reaction megathread",
             "Episode 1 dropped. Charlie Cox is back, Wilson Fisk is mayor. Spoiler-tagged comments please."),
            ("Help", "How do I add an infobox to a new MCU character?",
             "I'm trying to create a page for a side character. The infobox isn't rendering — what do I put in `infobox_kind`? Documentation page Help:Infoboxes is light."),
            ("Lore", "Vision's white form: still Vision?",
             "The 'White Vision' in WandaVision is debated as canonically the original Vision. The mind stone copy died, this is the body. Where does that leave him post-WandaVision?"),
            ("General", "Vote: best Avengers fight scene",
             "Top contenders: Battle of NY (2012), Lagos airport (Civil War), Wakanda Infinity War, NY Endgame portal. Cast your vote and reason."),
            ("Theories", "Will Tony Stark return via variant?",
             "RDJ is now Doom. Could the multiverse give us back a variant Iron Man? Or is Tony's death truly final?"),
            ("News", "Robert Downey Jr cast as Doctor Doom",
             "SDCC 2024 confirmed RDJ as Victor Von Doom. This is the wildest casting since Heath Ledger as Joker."),
            ("Off-topic", "MCU and Star Wars crossover discussion",
             "Both are Disney IPs. Could we ever see a crossover? Multiverse rules say it's possible."),
            ("Lore", "Wakanda's vibranium economy",
             "Black Panther established Wakanda as the wealthiest tech-economy on earth. How did they maintain isolation for so long?"),
            ("Help", "How do I revert a vandalism edit?",
             "Someone added 'Iron Man dies at age 5' to the Tony Stark article. Where is the revert button?"),
            ("Theories", "The Watcher Uatu's role in Phase 5/6",
             "What If's Uatu broke his oath. The Multiverse Saga is heading toward Secret Wars. Will Uatu be the narrator/Watcher of the climax?"),
            ("News", "Captain America 4 box office discussion",
             "Brave New World's opening weekend numbers came in lower than projected. Where does the franchise go from here?"),
            ("General", "Favorite MCU villain ranking",
             "Thanos #1 in most polls, but Loki, Killmonger, and Hela have arguments. Defend your top 3."),
            ("Lore", "Why is the Quantum Realm so plot-convenient?",
             "Ant-Man's Quantum Realm has been used for time travel (Endgame) and to access Kang (Quantumania). Is it ever going to be properly bounded?"),
            ("Off-topic", "MCU posters: best of all time",
             "I'd put the Endgame teaser poster (silhouettes against ash) at #1. Iron Man 3 burning suits is up there. What else?"),
            ("Theories", "Is Mephisto ever coming?",
             "Years of fan theories — WandaVision, Loki, even Hawkeye. Will Mephisto ever actually appear?"),
            ("News", "Doctor Doom recasting reaction",
             "What does it mean for the Doom mythology now that he's literally Tony Stark's actor?"),
            ("General", "Most underrated MCU film",
             "I'll say Eternals. Bold cosmic worldbuilding, divisive critics. Defend yours."),
            ("Lore", "Iron Man's AI assistants ranked",
             "JARVIS > Friday > Karen > EDITH. Disagree?"),
            ("Off-topic", "Stan Lee cameos all-time favorite",
             "Mine is Guardians of the Galaxy Vol 2 — he's literally a Watcher informant. Yours?"),
            ("Help", "How to find what links to a specific article?",
             "I want to know which articles link to Mjolnir. Is there a tool?"),
            ("Theories", "Doom and Kang: how do they connect?",
             "The Kang Dynasty was rumored to be re-titled Doomsday. Will Kang come back via variant or be fully replaced?"),
            ("News", "Disney+ MCU release schedule 2026",
             "Daredevil Born Again S2, Ironheart, Wonder Man, Vision Quest — packed year."),
            ("Lore", "Multiverse pruning ethics",
             "The TVA prunes timelines. Loki S2 made him the One Who Remains. Is pruning still happening?"),
            ("General", "What's your MCU rewatch order?",
             "Release order, chronological, character-arc-focused? Share your strategy."),
        ],
        "starwars": [
            ("Lore", "How did Palpatine come back in Rise of Skywalker?",
             "The film never gives a clean answer. The novelization says cloning + essence transfer. Is that canon or hand-waving?"),
            ("Theories", "Is Grogu a member of Yoda's species?",
             "Yes, but the species itself has never been named in canon despite Lucas's explicit ban on naming it."),
            ("News", "Mandalorian Season 4 cast leaks",
             "Pedro Pascal returns; Esposito and Bo-Katan confirmed. Production began Sept 2025."),
            ("General", "Best lightsaber duel of all time",
             "Anakin vs Obi-Wan on Mustafar, or Luke vs Vader on Bespin? Make your case."),
            ("Lore", "Mortis trilogy of Clone Wars: canon impact",
             "Father/Son/Daughter — the gods of the Force. Filoni canonised it. How does it tie into The Acolyte's High Republic?"),
            ("News", "Andor S2 reception megathread",
             "Tony Gilroy delivered. The Ghorman Massacre arc is among the best Star Wars storytelling ever."),
            ("Theories", "Snoke creation: how many clones?",
             "Rise of Skywalker showed Snoke vats. Were there multiple? Did Palpatine use Snoke 2.0 etc.?"),
            ("Lore", "The Jedi Code vs Sith Code",
             "Two opposing philosophies. Discuss real-world philosophical parallels (stoicism, etc.)."),
            ("Off-topic", "Star Wars LEGO sets — must-buys",
             "Razor Crest UCS, Death Star II, Millennium Falcon UCS. What else deserves the wallet hit?"),
            ("Help", "Categories cleanup: Jedi vs Sith vs Force-user",
             "Some articles are double-tagged. What's the correct hierarchy?"),
            ("General", "Best Star Wars TV show ranking",
             "Andor #1, Clone Wars #2, Rebels #3 for me. Where does Mandalorian land?"),
            ("Lore", "Mandalorian Creed clarifications",
             "The Children of the Watch vs main Mandalorian culture: who's right? Bo-Katan vs Din's argument is unresolved."),
            ("News", "Skeleton Crew reaction",
             "Goonies-in-space worked better than I expected. Jude Law was excellent."),
            ("Theories", "What is the Mortis God's connection to Force-sensitive families?",
             "The Skywalker bloodline is implied to be special. Mortis suggests the Force chooses dynasties."),
            ("Off-topic", "Star Wars conventions worth attending",
             "Star Wars Celebration is the big one. Any others?"),
            ("General", "Most underrated Star Wars character",
             "I'll nominate Mon Mothma. Andor S2 elevated her to S-tier."),
            ("Lore", "Imperial vs First Order military doctrine",
             "Where did they differ? The First Order seemed structurally similar but smaller."),
            ("News", "Ahsoka Season 2 release window",
             "Filming wrapped Q2 2026. Disney+ targeting Q4 2026."),
            ("Theories", "Force ghost limits",
             "Why can some Jedi return as Force ghosts (Yoda, Obi-Wan) but not all (Mace)? Discuss."),
            ("Lore", "The High Republic era lore dump",
             "Acolyte was set in the High Republic. The novels (Light of the Jedi etc.) expanded it. Worth reading?"),
            ("General", "Best Star Wars game of the past decade",
             "Jedi Survivor, Squadrons, or Battlefront 2? Defend yours."),
            ("Off-topic", "Disneyland's Galaxy's Edge experience",
             "Worth the price? Smuggler's Run vs Rise of the Resistance ranking."),
            ("News", "Mandalorian and Grogu film 2026 trailer reaction",
             "The theatrical sequel to The Mandalorian. Reactions?"),
            ("Help", "Adding a Wookieepedia-style infobox to a custom character",
             "I want to add a character not yet in the seed. Where do I document the infobox fields?"),
            ("Lore", "Sith Lord ranking: power-scaling",
             "Sidious > Vader > Maul > Tyranus > Plagueis (debatable). Disagree?"),
            ("Theories", "Will Knights of Ren ever get their own film?",
             "Filoni's master plan is mostly TV. Will Knights of Ren get a side-story?"),
            ("Off-topic", "Most quotable Star Wars line",
             "'I have a bad feeling about this' appears in every film. What's your favorite?"),
            ("Lore", "Jakku salvage operations economy",
             "Rey's livelihood was salvage. How sustainable was that?"),
            ("General", "Star Wars books worth your time",
             "Thrawn trilogy (canon), Heir to the Empire (Legends), Master & Apprentice."),
            ("News", "Lucasfilm slate post-2027",
             "What films were announced at SDCC 2025?"),
        ],
        "genshin": [
            ("Lore", "Is Khaenri'ah ever coming back?",
             "Hinted at in many quests. Dainsleif and Pierro are remnants. Will we get a Khaenri'ah region?"),
            ("Theories", "Celestia's role in Teyvat's future",
             "The Heavenly Principles run Teyvat. Will the player overthrow them?"),
            ("News", "Genshin 5.0 Natlan reaction",
             "Mavuika reveal, the Sacred Flame, new movement combat. Tribal lore on fire."),
            ("General", "Favorite playable character ranking",
             "Hu Tao, Raiden, Nahida, Zhongli are my top 4. Defend yours."),
            ("Lore", "What are the Hexenzirkel?",
             "Mondstadt's witch coven. Caribert lore. Discuss member identities."),
            ("News", "5.0 livestream news megathread",
             "Mavuika kit, Citlali kit, Skirk teaser. Banner schedule."),
            ("Theories", "Is the Tsaritsa really evil?",
             "She's collected Visions but the lore implies she has a higher purpose against Celestia."),
            ("Off-topic", "Best soundtrack region",
             "Liyue vs Sumeru vs Inazuma — which OST is your driving music?"),
            ("Help", "Pulling guide for limited 5-star characters",
             "I'm AR 50 with 90 wishes saved. Who should I prioritise from current banners?"),
            ("Lore", "Sustainer of Heavenly Principles — who?",
             "We saw Lumine's twin captured. The Sustainer in the prologue movie. Identity confirmed?"),
            ("General", "Most beautiful region visually",
             "Inazuma's lightning at night vs Fontaine's underwater vs Natlan's volcanic vista."),
            ("News", "HoYoFAIR 2025 highlights",
             "Annual community art festival. Best fanart of the year."),
            ("Theories", "Paimon's true identity",
             "Tweets and fan theories: Paimon = Unknown God? Paimon = future Sustainer? Discuss."),
            ("Lore", "Fontaine's Hydro vs Pneuma/Ousia",
             "The Fontaine reaction system tied to the law/justice metaphor. Explain to me like I'm a new player."),
            ("Off-topic", "Genshin and Honkai Star Rail crossover",
             "Both HoYoverse games. Will they ever crossover in lore?"),
            ("General", "Hu Tao build advice",
             "Pyro DPS main. Bond of Life vs traditional Vape — which?"),
            ("Theories", "The Abyss Order's goal",
             "They want Teyvat 'returned' to its original state. What does that even mean?"),
            ("Lore", "Inazuma vision hunt: who lost what?",
             "Document which characters lost their Visions to the Raiden Shogun's decree."),
            ("News", "5.5 banner predictions",
             "Skirk theorised. Confirmed by leakers? Sources?"),
            ("Off-topic", "Cosplay convention community",
             "Anime Expo, Anime NYC, ChinaJoy — what's the best Genshin cosplay scene?"),
            ("Help", "Optimal team comps for Spiral Abyss 12-3",
             "I keep timing out at Floor 12 Chamber 3. Comp suggestions?"),
            ("Lore", "Pierro and the original Khaenri'ah",
             "He's the First Harbinger and pre-cataclysm survivor. What was his original purpose?"),
            ("General", "Best Limited 4-star character ever printed",
             "Bennett. Period. Disagree?"),
            ("News", "5.7 Skirk teaser confirmation",
             "Voice actress hints, splash art leaks, weapon datamines."),
            ("Theories", "Where is Eikon, the Sky Lord?",
             "Hinted across regions. Tied to ascension of Archons. Discuss."),
            ("Lore", "Funerary parlor lore in Liyue",
             "Hu Tao's Wangsheng Funeral Parlor — how does it tie into Liyue's adeptus tradition?"),
            ("Off-topic", "Best Genshin fanart 2025",
             "Share your finds. WataMote, miHoYo official, indie artists."),
            ("Help", "How do I report a vandalised infobox?",
             "Someone put 'Raiden Shogun is actually Furina' on Raiden's page. Where's the report button?"),
            ("General", "Region with the best food in lore",
             "Liyue (Chinese cuisine), Mondstadt (Western pub fare), Inazuma (Japanese), or Sumeru (curry+street food)?"),
            ("Lore", "How does the Vision system actually work?",
             "A Vision is granted by an Archon when someone has strong ambition. But what physical mechanism?"),
        ],
    }
    POSTERS = [
        "WikiBot", "StarkFan42", "LucasCanon", "HoYoLore",
        "InfinityScribe", "EnabranTain", "ShinyCelestia", "AliceJ",
        "BobK", "CarolS", "DanR", "EditorEcho_001", "ContribCat_001",
        "WikiBee_002", "PageDragon_001",
    ]
    REPLIES = [
        "Solid take. I disagree on point 2 but the rest is spot on.",
        "I've been waiting for someone to write this up. Thanks!",
        "Source? Specifically the part about the timeline branching.",
        "Counterpoint: you're underrating the emotional weight of the prequels.",
        "Great thread. Pinning this for newcomers.",
        "Marking as resolved — covered in the Help page.",
        "Came here to say the same thing. Up-voted.",
        "Read the Reddit megathread from last year — different take.",
        "Long-time editor here: the canonical source agrees with OP.",
        "Lol, every time this thread comes back I have new opinions.",
        "Don't forget the novelisation contradicts the film here.",
        "Bookmarking. Will reply with sources when I'm back from work.",
        "The wiki article on this contradicts what you're saying. Compare?",
        "Mod note: please use [[Article Name]] syntax for in-thread refs.",
        "I'll add a paragraph to the main article reflecting this.",
    ]
    for wiki_slug, threads in THREADS.items():
        w = Wiki.query.filter_by(slug=wiki_slug).first()
        for i, (cat, title, body) in enumerate(threads):
            author = POSTERS[i % len(POSTERS)]
            created = BASE_TS - timedelta(days=(i * 5) % 365 + 1)
            t = ForumThread(
                wiki_id=w.id, category=cat, title=title, slug=slugify(title),
                body=body, author_label=author, created_at=created,
                updated_at=created + timedelta(days=(i % 4)),
                view_count=140 + (i * 37) % 2000,
                is_pinned=(i < 2), is_locked=(i == 29 and wiki_slug == "mcu"),
            )
            db.session.add(t); db.session.flush()
            # First post (the OP body)
            db.session.add(ForumPost(
                thread_id=t.id, user_id=None, author_label=author,
                body=body, timestamp=created))
            # Replies: 4..12 each
            n_reply = 4 + (i % 9)
            for k in range(n_reply):
                reply_author = POSTERS[(i + k + 3) % len(POSTERS)]
                rt = created + timedelta(hours=k * 7 + 2)
                db.session.add(ForumPost(
                    thread_id=t.id, user_id=None, author_label=reply_author,
                    body=REPLIES[(i * 3 + k) % len(REPLIES)],
                    timestamp=rt,
                    likes=(i + k) % 8))
    db.session.commit()
    # Link author_id where possible
    from app import User
    for t in ForumThread.query.all():
        u = User.query.filter_by(username=t.author_label).first()
        if u:
            t.author_id = u.id
    for p in ForumPost.query.all():
        u = User.query.filter_by(username=p.author_label).first()
        if u:
            p.user_id = u.id
    db.session.commit()


def seed_article_comments():
    from app import db, Wiki, Article, ArticleComment
    if ArticleComment.query.count() > 0:
        return
    POSTERS = ["AliceJ", "BobK", "CarolS", "DanR", "InfinityScribe",
                "LucasCanon", "HoYoLore", "EnabranTain",
                "EditorEcho_001", "ContribCat_002", "PageDragon_003"]
    COMMENTS = [
        "Solid article. The bio section feels comprehensive.",
        "I came here for the infobox and was not disappointed.",
        "Should we link this to the related characters page?",
        "Excellent summary. Citation 3 needs an update though.",
        "Reading this for the 4th time and still finding new details.",
        "Did anyone else notice the ref to the 2008 origin?",
        "This page should be featured.",
        "The trivia section could use 2 more entries.",
        "Wonderful job by the editors who built this out.",
        "I disagree about the 'legacy' framing. The character isn't done.",
        "Quick question: does the infobox match the live source?",
        "Found a typo in the Appearances list — fixed.",
        "This article single-handedly converted me to the canon side.",
        "Great work. Will reference this in my next thread.",
        "Updated the categories — feel free to revert if wrong.",
    ]
    REPLIES = [
        "Agreed.",
        "Updated. Thanks for catching that.",
        "I disagree — see the wiki style guide.",
        "Good catch. Will fix.",
        "+1, this is correct.",
        "Sourced from the novelisation. Will add.",
    ]
    # Add comments to a sampling of articles (every 3rd article gets ~3-7 comments)
    articles = Article.query.all()
    for idx, a in enumerate(articles):
        if idx % 3 != 0:
            continue
        n = 3 + (idx % 5)
        for k in range(n):
            author = POSTERS[(idx + k) % len(POSTERS)]
            ts = BASE_TS - timedelta(days=((idx + k) * 4) % 200 + 1)
            c = ArticleComment(
                article_id=a.id, author_label=author,
                body=COMMENTS[(idx + k * 7) % len(COMMENTS)],
                timestamp=ts,
                likes=(idx + k) % 12,
            )
            db.session.add(c); db.session.flush()
            # 50% chance of a reply
            if k % 2 == 0:
                rt = ts + timedelta(hours=6 + k)
                db.session.add(ArticleComment(
                    article_id=a.id, parent_id=c.id,
                    author_label=POSTERS[(idx + k + 4) % len(POSTERS)],
                    body=REPLIES[(idx + k) % len(REPLIES)],
                    timestamp=rt,
                    likes=(idx + k * 3) % 6,
                ))
    db.session.commit()
    # Link user_id
    from app import User
    for c in ArticleComment.query.all():
        u = User.query.filter_by(username=c.author_label).first()
        if u:
            c.user_id = u.id
    db.session.commit()


def seed_notices():
    from app import db, Wiki, Notice
    if Notice.query.count() > 0:
        return
    NOTES = [
        (None, "Welcome to Fandom",
         "Welcome to the Fandom hub mirror. Sign in to edit, watch pages, and join the discussions on any wiki."),
        ("mcu", "Phase 6 announcement — Avengers Doomsday",
         "Marvel Studios confirmed Avengers Doomsday for December 2026 at SDCC. Multiverse Saga editors: please update related pages."),
        ("mcu", "Featured article voting open",
         "Cast your vote for the next featured MCU article. Visit the Community Portal for the form."),
        ("starwars", "Andor Season 2 wrapped",
         "Production has finished on Andor S2. Editors: please move spoilers behind tags until air date."),
        ("starwars", "Wookieepedia 22 anniversary",
         "We have been canonising the galaxy since 2005. Thank you to all editors past and present."),
        ("genshin", "Version 5.0 Natlan released",
         "The Pyro nation Natlan is now live in the live game. Wiki coverage is in progress — coordinate at the Community Portal."),
        ("genshin", "Featured character poll closes Friday",
         "Vote for the next featured character at Special:Polls."),
    ]
    for wiki_slug, title, body in NOTES:
        wiki_id = None
        if wiki_slug:
            w = Wiki.query.filter_by(slug=wiki_slug).first()
            if w:
                wiki_id = w.id
        n = Notice(wiki_id=wiki_id, title=title, body=body, is_active=True,
                   created_at=BASE_TS - timedelta(days=10 + len(title) % 30))
        db.session.add(n)
    db.session.commit()


def seed_follows_subs_watch():
    """Establish initial follow/subscription/watch links."""
    from app import db, User, Wiki, Article, WatchItem, UserFollow, WikiSubscription
    if WatchItem.query.count() > 0:
        return
    alice = User.query.filter_by(username="AliceJ").first()
    bob = User.query.filter_by(username="BobK").first()
    carol = User.query.filter_by(username="CarolS").first()
    dan = User.query.filter_by(username="DanR").first()
    wikibot = User.query.filter_by(username="WikiBot").first()
    if not alice:
        return
    # Each main user watches 5 featured articles of their home wiki
    home = {alice: "mcu", bob: "starwars", carol: "genshin"}
    for u, slug in home.items():
        w = Wiki.query.filter_by(slug=slug).first()
        arts = Article.query.filter_by(wiki_id=w.id).limit(5).all()
        for a in arts:
            db.session.add(WatchItem(user_id=u.id, article_id=a.id))
    # Dan watches 3 across all wikis
    for w in Wiki.query.all():
        a = Article.query.filter_by(wiki_id=w.id).first()
        if a:
            db.session.add(WatchItem(user_id=dan.id, article_id=a.id))
    # Follow graph
    db.session.add(UserFollow(follower_id=alice.id, followee_id=wikibot.id))
    db.session.add(UserFollow(follower_id=bob.id, followee_id=wikibot.id))
    db.session.add(UserFollow(follower_id=carol.id, followee_id=wikibot.id))
    db.session.add(UserFollow(follower_id=alice.id, followee_id=bob.id))
    db.session.add(UserFollow(follower_id=dan.id, followee_id=alice.id))
    # Wiki subs
    for u, slug in home.items():
        w = Wiki.query.filter_by(slug=slug).first()
        db.session.add(WikiSubscription(user_id=u.id, wiki_id=w.id))
    db.session.commit()


def seed_protections():
    from app import db, Article, Protection, User
    if Protection.query.count() > 0:
        return
    # Protect 3 high-traffic articles on each wiki
    bob = User.query.filter_by(username="BobK").first()
    bob_id = bob.id if bob else None
    for art in Article.query.filter(Article.view_count > 5000).limit(9).all():
        db.session.add(Protection(
            article_id=art.id, level="autoconfirmed",
            reason="High-traffic page; previous edit warring.",
            set_by_id=bob_id, set_at=BASE_TS - timedelta(days=60),
        ))
    db.session.commit()


def seed_phase2_all():
    """One-shot entry point — call this from seed_data.seed_database()."""
    seed_extra_users()
    seed_files()
    seed_forum_threads()
    seed_article_comments()
    seed_notices()
    seed_follows_subs_watch()
    seed_protections()
