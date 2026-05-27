#!/usr/bin/env python3
"""Deepen seed data — fills the tables added in the vanilla-deepen pass.

All data is static / deterministic. Idempotent: gated on each table being
empty. Loaded once by app.py after seed_data.seed().
"""
from datetime import datetime, timedelta


GUI_REFERENCE_DATE = datetime(2026, 5, 12, 12, 0, 0)


def _slug(text):
    import re
    s = re.sub(r'[^a-zA-Z0-9\s-]', '', text or '')
    return re.sub(r'\s+', '-', s.strip().lower())


def seed_extended():
    from app import (
        db, College,
        StudentLifeCategory, LibraryBranch, DiningLocation, DiningMenuItem,
        AthleticTeam, AthleticGame, AthleticRosterMember,
        AlumniChapter, GivingFund,
        FinancialAidType, FinancialAidForm,
        CollegeLeader, HistoryMilestone, DiversityProgram,
        CampusService, AdmissionsPathway,
    )

    # ─── Student Life Categories ─────────────────────────────────────────
    if not StudentLifeCategory.query.first():
        slc_data = [
            ('Housing & Residence Life', '🏠', 'housing@osu.edu',
             'Live where you learn — 38 residence halls on the Columbus campus.',
             'Housing options include traditional residence halls, suite-style '
             'living, learning communities, and on-campus apartments. First- and '
             'second-year students are required to live on campus.'),
            ('Recreation & Wellness', '🏋', 'rpac@osu.edu',
             'The 568,000 sq ft RPAC anchors Buckeye fitness life.',
             'Eight pools, four gyms, an indoor track, a climbing wall, and 250+ '
             'weekly group fitness classes serve more than 60,000 active members.'),
            ('Student Organizations', '🤝', 'orgs@osu.edu',
             'Over 1,400 registered student organizations.',
             'From the Undergraduate Student Government and Mock Trial to the '
             'Anime Club and Buckeyethon, you can find — or start — a club for '
             'almost anything.'),
            ('Greek Life', '🏛', 'greek@osu.edu',
             '63 fraternities and sororities, 5,000+ Buckeye Greeks.',
             'The Interfraternity Council, Panhellenic Council, National Pan-'
             'Hellenic Council, and Multicultural Greek Council govern Greek life.'),
            ('Multicultural Center', '🌍', 'mcc@osu.edu',
             'Programs and dialogues that build cultural competency.',
             'The Multicultural Center is the campus hub for diversity, equity, '
             'inclusion, and intercultural learning.'),
            ('Wellness & Counseling', '🧠', 'ccs@osu.edu',
             'Buckeyes thrive when their minds and bodies thrive.',
             'The Office of Student Life Counseling and Consultation Service '
             'provides individual, group, and crisis counseling at no cost.'),
            ('Buckeyes Care', '❤', 'studentadvocacy@osu.edu',
             'Confidential support, advocacy, and resources.',
             'Student Advocacy Center, Sexual Civility & Empowerment, '
             'and Buckeye Peer Access connect students with help.'),
            ('Civic & Community Engagement', '🏙', 'engage@osu.edu',
             '1.4 million service hours by Buckeyes every year.',
             'The Office of Student Life Civic Engagement coordinates service '
             'projects, alternative break trips, and voter registration drives.'),
            ('Spirit & Traditions', '🅾', 'traditions@osu.edu',
             'Mirror Lake Jump, Skull Session, Senior Tackle, Block O.',
             'Buckeye traditions stretch from 1898 (the Carmen Ohio) to today, '
             'celebrated each fall at the Homecoming festival.'),
            ('Off-Campus Living', '🏘', 'offcampus@osu.edu',
             'Resources for the 60% of Buckeyes who live off-campus.',
             'Search rentals, find roommates, learn tenant rights, and access '
             'safe-ride programs through Off-Campus & Commuter Student Services.'),
        ]
        for name, icon, contact, tagline, body in slc_data:
            db.session.add(StudentLifeCategory(
                name=name, slug=_slug(name), icon=icon,
                contact_email=contact, tagline=tagline,
                description=tagline + ' ' + body[:120], body=body,
            ))
        db.session.flush()

    # ─── Library Branches ────────────────────────────────────────────────
    if not LibraryBranch.query.first():
        lib_data = [
            ('Thompson Library', '1858 Neil Avenue Mall, Columbus, OH 43210',
             '(614) 292-OSUL', '24 hours during the semester',
             'Damon Jaggars', 5800000, True,
             'The William Oxley Thompson Memorial Library is the flagship of '
             'the University Libraries — 11 floors, 2,000 study seats, and 5.8 '
             'million volumes. It anchors the south end of The Oval.'),
            ('Science & Engineering Library', '175 W. 18th Avenue, Columbus, OH 43210',
             '(614) 292-2925', 'Mon–Fri 8a–10p, Sat–Sun 11a–8p',
             'Brian Leaf', 1200000, True,
             '18th Avenue Library houses science, technology, engineering, and '
             'math collections in a 235,000-sq-ft facility shared with the '
             'Math Tower.'),
            ('Health Sciences Library', '376 W. 10th Avenue, Columbus, OH 43210',
             '(614) 292-9810', 'Mon–Thu 7a–midnight, Fri 7a–8p',
             'Michelle Kraft', 380000, True,
             'Prior Health Sciences Library serves the seven health-sciences '
             'colleges and the Wexner Medical Center.'),
            ('Cartoon Library & Museum', '1813 N. High Street, Columbus, OH 43210',
             '(614) 292-0538', 'Tue–Fri 1p–5p',
             'Jenny Robb', 450000, False,
             'The Billy Ireland Cartoon Library & Museum holds the world\'s '
             'largest collection of original cartoon and comic art — 450,000 '
             'original cartoons and 36,000 books.'),
            ('Music & Dance Library', '1813 N. College Road, Columbus, OH 43210',
             '(614) 688-8389', 'Mon–Thu 8a–10p, Fri 8a–5p',
             'Sean Ferguson', 200000, True,
             'The Music & Dance Library on the second floor of the 18th Avenue '
             'Library serves the School of Music and the Department of Dance.'),
            ('Architecture Library', '275 W. Woodruff Avenue, Columbus, OH 43210',
             '(614) 292-6184', 'Mon–Thu 9a–10p, Fri 9a–5p',
             'Daniel Dotson', 90000, True,
             'Knowlton Hall\'s Architecture Library supports the Knowlton School '
             'of Architecture, Landscape Architecture, and City & Regional Planning.'),
            ('Geology Library', '275 Mendenhall Lab, 125 S. Oval Mall, Columbus, OH 43210',
             '(614) 292-2428', 'Mon–Fri 8a–5p',
             'Mary Scott', 165000, False,
             'Orton Memorial Library of Geology dates to 1893 and is the '
             'oldest library on campus, named for OSU\'s second president.'),
            ('Veterinary Medicine Library', '210 Sisson Hall, 1900 Coffey Road, Columbus, OH 43210',
             '(614) 292-3043', 'Mon–Fri 8a–6p',
             'Erica Schwartz', 65000, True,
             'The veterinary medicine library is the only dedicated vet-med '
             'library in Ohio and one of 28 in North America.'),
            ('Newark Campus Library', '1219 University Drive, Newark, OH 43055',
             '(740) 366-9242', 'Mon–Thu 8a–9p, Fri 8a–5p',
             'Eric Schnell', 75000, True,
             'The Newark Campus Library serves OSU Newark and Central Ohio '
             'Technical College in a shared learning center.'),
            ('Mansfield Campus Library', '1760 University Drive, Mansfield, OH 44906',
             '(419) 755-4360', 'Mon–Thu 8a–9p, Fri 8a–5p',
             'Betsy Blankenship', 60000, True,
             'Bromfield Library and Information Commons serves OSU Mansfield '
             'and North Central State College.'),
            ('Lima Campus Library', '4240 Campus Drive, Lima, OH 45804',
             '(419) 995-8237', 'Mon–Thu 8a–9p, Fri 8a–5p',
             'Tina Schneider', 50000, True,
             'The Galvin Hall Library serves OSU Lima and Rhodes State College.'),
            ('Marion Campus Library', '1465 Mount Vernon Avenue, Marion, OH 43302',
             '(740) 725-6240', 'Mon–Thu 8a–9p, Fri 8a–5p',
             'Robert Brookhart', 55000, True,
             'The Morrill Hall Library serves OSU Marion and Marion Technical College.'),
            ('Wooster Campus Library', '1680 Madison Avenue, Wooster, OH 44691',
             '(330) 263-3771', 'Mon–Fri 8a–5p',
             'Connie Britton', 45000, False,
             'The Pounden Library at OARDC supports research at the OSU '
             'Wooster campus and the Ohio Agricultural Research & Development Center.'),
        ]
        for (name, addr, phone, hours, head, size, rooms, desc) in lib_data:
            db.session.add(LibraryBranch(
                name=name, slug=_slug(name),
                address=addr, phone=phone, hours=hours,
                head_librarian=head, collection_size=size,
                has_study_rooms=rooms, description=desc,
            ))
        db.session.flush()

    # ─── Dining Locations + Menu Items ──────────────────────────────────
    if not DiningLocation.query.first():
        dining_data = [
            ('Traditions at Scott', '160 W. Woodruff Avenue', 'Daily 7a–9p',
             'All-you-care-to-eat', True, 540,
             'The largest dining hall on campus, serving Scott Quad in north campus.'),
            ('Traditions at Kennedy', '116 W. 11th Avenue', 'Daily 7a–9p',
             'All-you-care-to-eat', True, 480,
             'Kennedy Commons traditions dining hall serves the south residential area.'),
            ('Traditions at Morrill', '1900 Cannon Drive', 'Daily 7a–10p',
             'All-you-care-to-eat', True, 600,
             'Morrill Tower\'s 24-hour-style dining center, popular with night-owl Buckeyes.'),
            ('Marketplace on Neil', '1810 Cannon Drive', 'Daily 11a–8p',
             'Food court', True, 360,
             'Buffalo Wild Wings, Sushi Don, Hibachi-San, and a build-your-own pasta bar.'),
            ('Mirror Lake Eatery', '243 W. 17th Avenue', 'Mon–Fri 7a–8p',
             'Cafe', True, 180,
             'Quick-service grill, salad bar, and Buckeye coffee bar overlooking the lake.'),
            ('Berry Cafe', '154 W. 12th Avenue', 'Mon–Fri 7a–4p',
             'Cafe', True, 120,
             'Berry Cafe in Houck Commons serves Lavazza coffee, paninis, and grab-and-go.'),
            ('Curl Market', '124 W. 11th Avenue', 'Daily 11a–11p',
             'Convenience + grill', True, 60,
             'Curl Market combines a c-store with hot food, late-night pizza, and burgers.'),
            ('Oxley\'s by the Numbers', '1739 N. High Street', 'Mon–Sat 11a–11p',
             'Pub', False, 200,
             'A pub-style restaurant in the Blackwell Inn featuring craft beer and Ohio fare.'),
            ('Sloopy\'s Diner', '1739 N. High Street', 'Daily 7a–10p',
             'American diner', True, 110,
             'A throwback diner in the Ohio Union serving breakfast all day.'),
            ('Espress-OH', '1739 N. High Street', 'Mon–Fri 7a–8p',
             'Coffee bar', True, 40,
             'Ohio Union coffee bar serving Crimson Cup beans and fresh pastries.'),
            ('Woody\'s Tavern', '1739 N. High Street', 'Mon–Sat 11a–midnight',
             'Sports bar', False, 220,
             'Named for Woody Hayes — Ohio Union\'s gameday-vibes sports bar.'),
            ('The Eatery at Houck', '111 W. 12th Avenue', 'Mon–Fri 11a–7p',
             'Salad + grill', True, 95,
             'Build-your-own salad station and certified gluten-free grill.'),
        ]
        locations = []
        for (name, loc, hours, cuisine, mp, seats, desc) in dining_data:
            d = DiningLocation(
                name=name, slug=_slug(name), location=loc, hours=hours,
                cuisine=cuisine, accepts_meal_plan=mp, seats=seats,
                description=desc,
            )
            db.session.add(d)
            locations.append(d)
        db.session.flush()

        menu_pool = [
            ('Buckeye Burger', 'Quarter-pound beef on a brioche bun with Buckeye sauce.',
             'Lunch', 8.95, 720, False, False),
            ('Garden Veggie Wrap', 'Hummus, cucumber, peppers, sprouts in a spinach wrap.',
             'Lunch', 7.5, 380, True, True),
            ('Scarlet Caesar Salad', 'Romaine, parmesan, croutons, lemon-anchovy dressing.',
             'Lunch', 6.95, 320, False, False),
            ('Brutus Breakfast Skillet', 'Eggs, hash browns, sausage, cheddar, peppers.',
             'Breakfast', 7.25, 640, False, False),
            ('Steel-Cut Oats Bar', 'Steel-cut oats with fruit, nuts, and brown sugar.',
             'Breakfast', 4.5, 290, True, True),
            ('Stir-Fry Bowl', 'Wok-fired vegetables and tofu over jasmine rice.',
             'Dinner', 9.5, 540, True, True),
            ('Margherita Pizza', '12-inch pie with fresh mozzarella, basil, San Marzano.',
             'Lunch', 10.95, 820, True, False),
            ('Carmen Ohio Chicken', 'Buttermilk-brined chicken sandwich with pickles.',
             'Lunch', 8.5, 660, False, False),
            ('Maple Buckeye Sundae', 'Vanilla bean ice cream with maple-buckeye fudge.',
             'Snack', 4.25, 480, True, False),
            ('Lake Erie Walleye', 'Pan-seared walleye, lemon butter, seasonal greens.',
             'Dinner', 13.95, 480, False, False),
        ]
        for loc in locations:
            for i, item in enumerate(menu_pool):
                if i % 2 == (loc.id % 2):
                    pass  # serve all
                name, desc, meal, price, cal, veg, vegan = item
                db.session.add(DiningMenuItem(
                    location_id=loc.id, name=name, description=desc,
                    meal=meal, price=price, calories=cal,
                    is_vegetarian=veg, is_vegan=vegan,
                ))
        db.session.flush()

    # ─── Athletic Games + Roster ─────────────────────────────────────────
    if not AthleticGame.query.first():
        opponents_pool = [
            ('Michigan Wolverines', 'Ann Arbor, MI'),
            ('Penn State Nittany Lions', 'University Park, PA'),
            ('Wisconsin Badgers', 'Madison, WI'),
            ('Iowa Hawkeyes', 'Iowa City, IA'),
            ('Michigan State Spartans', 'East Lansing, MI'),
            ('Indiana Hoosiers', 'Bloomington, IN'),
            ('Purdue Boilermakers', 'West Lafayette, IN'),
            ('Minnesota Golden Gophers', 'Minneapolis, MN'),
            ('Nebraska Cornhuskers', 'Lincoln, NE'),
            ('Maryland Terrapins', 'College Park, MD'),
            ('Rutgers Scarlet Knights', 'Piscataway, NJ'),
            ('Illinois Fighting Illini', 'Champaign, IL'),
            ('Northwestern Wildcats', 'Evanston, IL'),
            ('UCLA Bruins', 'Los Angeles, CA'),
        ]
        teams = AthleticTeam.query.order_by(AthleticTeam.id).all()
        base_date = GUI_REFERENCE_DATE
        for ti, team in enumerate(teams):
            for gi in range(8):
                op_idx = (ti * 7 + gi) % len(opponents_pool)
                opp, opp_loc = opponents_pool[op_idx]
                home = (gi % 2 == 0)
                game_date = base_date + timedelta(days=(ti * 9 + gi * 7))
                if home:
                    venue = team.home_venue
                    result = ['W 28-17', 'W 41-21', 'L 17-24', 'W 35-3',
                              'W 24-7', 'L 13-20', 'W 31-14', 'W 17-10'][gi]
                else:
                    venue = opp_loc
                    result = ['L 21-24', 'W 28-14', 'W 34-17', 'L 10-13',
                              'W 24-21', 'W 17-3', 'L 14-20', 'W 27-17'][gi]
                tv = ['FOX', 'BTN', 'ESPN', 'ABC', 'CBS', 'NBC', 'FS1',
                      'Peacock'][gi]
                db.session.add(AthleticGame(
                    team_id=team.id, opponent=opp, home_away=('Home' if home else 'Away'),
                    game_date=game_date, venue=venue, result=result, tv=tv,
                ))
        db.session.flush()

    if not AthleticRosterMember.query.first():
        first_names = ['Marcus', 'Tre', 'Cade', 'Devin', 'Jaylen', 'Quinn',
                       'Brennan', 'Sonny', 'Will', 'Donovan', 'Carnell', 'Tyleik',
                       'Cody', 'Lathan', 'Denzel', 'Kaden', 'Emeka', 'Jeremiah',
                       'Aliyah', 'Jacy', 'Cotie', 'Rebeka', 'Taylor', 'Kennedy']
        last_names = ['Williams', 'Henderson', 'Stover', 'Brown', 'Johnson',
                      'Ewers', 'Jackson', 'Styles', 'Howard', 'Jackson-Davis',
                      'Tate', 'Williams', 'Simon', 'Ransom', 'Burke', 'Saunders',
                      'Egbuka', 'Smith', 'Mitchell', 'Sheldon', 'McCabe', 'Mikulasikova',
                      'Mikesell', 'Cambridge']
        positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'DE', 'DT', 'LB', 'CB', 'S',
                     'G', 'F', 'C', 'P', 'GK', 'D', 'M', 'F']
        years = ['Freshman', 'Sophomore', 'Junior', 'Senior', 'Graduate']
        hometowns = ['Columbus, OH', 'Cleveland, OH', 'Cincinnati, OH',
                     'Toledo, OH', 'Akron, OH', 'Dayton, OH', 'Pittsburgh, PA',
                     'Detroit, MI', 'Indianapolis, IN', 'Chicago, IL']
        teams = AthleticTeam.query.order_by(AthleticTeam.id).all()
        for ti, team in enumerate(teams):
            for ri in range(14):
                fn = first_names[(ti * 5 + ri) % len(first_names)]
                ln = last_names[(ti * 3 + ri * 2) % len(last_names)]
                pos = positions[(ti + ri) % len(positions)]
                yr = years[ri % len(years)]
                ht_in = 66 + ((ti * 5 + ri * 3) % 16)
                wt = 150 + ((ti * 11 + ri * 7) % 110)
                jersey = str(((ti * 13 + ri * 11) % 98) + 1)
                hometown = hometowns[(ti * 2 + ri) % len(hometowns)]
                height_str = f'{ht_in // 12}\'{ht_in % 12}"'
                db.session.add(AthleticRosterMember(
                    team_id=team.id, name=f'{fn} {ln}', jersey_number=jersey,
                    position=pos, year=yr, hometown=hometown,
                    height=height_str, weight=f'{wt} lbs',
                ))
        db.session.flush()

    # ─── Alumni Chapters ─────────────────────────────────────────────────
    if not AlumniChapter.query.first():
        chapters = [
            ('Central Ohio Buckeyes', 'Columbus', 'OH', 'Jennifer M. Adams', 18500, 1923,
             'Annual Block Party at the Schottenstein Center on August 10.',
             'The flagship chapter in OSU\'s home market — events at the Ohio '
             'Union, watch parties at Standard Hall, and a thriving Young Alumni network.'),
            ('Cleveland Buckeyes', 'Cleveland', 'OH', 'Robert Hayes', 9800, 1908,
             'Fall game-watch at Punch Bowl Social, every Saturday at 11a.',
             'Cleveland alumni serve Cuyahoga, Lake, Lorain, and Geauga counties.'),
            ('Cincinnati Buckeyes', 'Cincinnati', 'OH', 'Marissa Lopez', 7200, 1912,
             'Reds vs. Indians road trip, July 15.',
             'Queen City Buckeyes meet at Mt. Adams Bar & Grill for the Game.'),
            ('NYC Buckeyes', 'New York', 'NY', 'David Chen', 12400, 1934,
             'Empire State Building lighting Scarlet & Gray for Beat Michigan week.',
             'The largest out-of-state chapter — Times Square watch parties at '
             'Stout NYC and Madison Square Garden basketball outings.'),
            ('Los Angeles Buckeyes', 'Los Angeles', 'CA', 'Sandra Park', 8600, 1928,
             'Pasadena Rose Bowl pre-game tailgate.',
             'Beach Buckeyes meet at Surly Goat in West Hollywood for the Game.'),
            ('Chicago Buckeyes', 'Chicago', 'IL', 'Michael O\'Brien', 9100, 1919,
             'Wrigley Field Buckeyes Day, August 24.',
             'Chicago is home to OSU\'s second-largest alumni population — '
             'Lincoln Park watch parties at Trace.'),
            ('DC Buckeyes', 'Washington', 'DC', 'Aisha Williams', 7400, 1925,
             'Capitol Hill networking reception, October 12.',
             'Beltway Buckeyes connect government, policy, and political alumni.'),
            ('Atlanta Buckeyes', 'Atlanta', 'GA', 'James Thornton', 5300, 1930,
             'Peach Bowl watch party at Stats Brewpub.',
             'Atlanta alumni gather monthly at Hudson Grille in Sandy Springs.'),
            ('Dallas-Fort Worth Buckeyes', 'Dallas', 'TX', 'Kara Patel', 4900, 1947,
             'Texas-Ohio State Day at AT&T Stadium parking lot (October 18).',
             'DFW Buckeyes meet at The Londoner Pub in Addison.'),
            ('Boston Buckeyes', 'Boston', 'MA', 'Mark Sullivan', 4200, 1936,
             'Faneuil Hall scarlet-and-gray meetup, November 1.',
             'Boston Buckeyes pack the Pour House Boston for every football Saturday.'),
            ('San Francisco Bay Area Buckeyes', 'San Francisco', 'CA', 'Linda Tran', 6100, 1940,
             'Buckeye Brunch at Sam\'s Anchor Cafe, September 14.',
             'Bay Area Buckeyes draw alumni from tech, biotech, and finance.'),
            ('Seattle Buckeyes', 'Seattle', 'WA', 'Ethan Cooper', 3800, 1948,
             'Pike Place Market crab feast, May 18.',
             'Pacific Northwest Buckeyes meet at the Hawks Nest in Pioneer Square.'),
            ('Detroit Buckeyes', 'Detroit', 'MI', 'Ashley Kim', 4500, 1922,
             'Beat-Michigan rally at Hop Cat Royal Oak.',
             'Detroit Buckeyes have the most-spirited rivalry-week events.'),
            ('Pittsburgh Buckeyes', 'Pittsburgh', 'PA', 'Brian Mitchell', 3600, 1929,
             'PNC Park Buckeyes Night, July 27.',
             'Steel City Buckeyes meet at Carson City Saloon on the South Side.'),
            ('Phoenix Buckeyes', 'Phoenix', 'AZ', 'Diana Reyes', 3200, 1965,
             'Spring Training Buckeyes outing at Goodyear Ballpark.',
             'Sun Belt Buckeyes draw retirees and remote workers across the Valley.'),
            ('Denver Buckeyes', 'Denver', 'CO', 'Patrick Mullen', 3000, 1958,
             'Coors Field Buckeye Outing, August 12.',
             'Mile-High Buckeyes meet at the View House for football Saturdays.'),
            ('Charlotte Buckeyes', 'Charlotte', 'NC', 'Stephanie Brooks', 2800, 1961,
             'Knights game alumni outing, June 8.',
             'Carolina Buckeyes gather at Whiskey Warehouse for the Game.'),
            ('Tampa Bay Buckeyes', 'Tampa', 'FL', 'Carlos Ramirez', 3400, 1955,
             'Outback Bowl pre-party at Yuengling Brewery.',
             'Florida\'s west coast Buckeyes welcome snowbird alumni.'),
            ('Houston Buckeyes', 'Houston', 'TX', 'Olivia Garcia', 3500, 1968,
             'Astros Buckeye Night, May 27.',
             'Energy-corridor Buckeyes pack End Zone Sports Bar for football.'),
            ('London Buckeyes', 'London', 'UK', 'Henry Pemberton', 1100, 1985,
             'Pre-NFL-game alumni reception at the Drayton Court.',
             'The international flagship chapter — events at the Sherlock Holmes Pub.'),
        ]
        for (region, city, state, pres, members, founded, nev, desc) in chapters:
            db.session.add(AlumniChapter(
                region=region, slug=_slug(region), city=city, state=state,
                president=pres, members=members, founded_year=founded,
                next_event=nev, description=desc,
            ))
        db.session.flush()

    # ─── Giving Funds ────────────────────────────────────────────────────
    if not GivingFund.query.first():
        colleges = {c.name: c.id for c in College.query.all()}
        funds = [
            ('Buckeye Scholars Endowment', 'Scholarship', 50000000, 32400000, None,
             10, 'The flagship need-based scholarship fund — every gift is '
                 'matched 1:1 by the President\'s Match through 2027.'),
            ('Pelotonia Cancer Research Fund', 'Cancer Research', 100000000, 86200000,
             colleges.get('Medicine'), 25,
             '100% of every dollar funds cutting-edge cancer research at the '
             'James Cancer Hospital and Solove Research Institute.'),
            ('Library Excellence Fund', 'Libraries', 5000000, 3100000, None, 25,
             'Supports rare book acquisitions, digital preservation, and the '
             '24/5 hours at Thompson Library.'),
            ('Athletics Buckeye Club', 'Athletics', 20000000, 14800000, None, 100,
             'Joining the Buckeye Club at Bronze level or higher unlocks ticket '
             'priority for football and basketball.'),
            ('Faculty Excellence Fund', 'Faculty Support', 30000000, 19500000, None, 50,
             'Endows distinguished professorships and recruits world-class faculty.'),
            ('Student Emergency Fund', 'Student Support', 2000000, 1240000, None, 10,
             'One-time grants for Buckeyes facing housing, food, or unexpected expenses.'),
            ('Veterans Education Fund', 'Veterans', 4000000, 2680000, None, 50,
             'Tuition support for student veterans not covered by the GI Bill.'),
            ('Land-Grant Mission Fund', 'OSU Extension', 8000000, 5320000, None, 25,
             'Funds OSU Extension and 4-H programs in all 88 Ohio counties.'),
            ('Wexner Medical Center Cardiology Fund', 'Medical Research', 15000000, 8400000,
             colleges.get('Medicine'), 50,
             'Heart-disease research and patient-care endowment at the Ross Heart Hospital.'),
            ('College of Engineering Innovation Fund', 'Engineering', 12000000, 7560000,
             colleges.get('Engineering'), 25,
             'Capital projects, lab equipment, and undergraduate research stipends.'),
            ('Fisher Global Business Fund', 'Business', 6000000, 3920000,
             colleges.get('Fisher College of Business'), 25,
             'International immersions and the Fisher Honors program for MBA candidates.'),
            ('Stone Lab Naturalist Fund', 'Environment', 1500000, 980000,
             colleges.get('Arts and Sciences'), 25,
             'Funds the Stone Laboratory on Lake Erie — the oldest freshwater '
             'biological field station in the United States.'),
        ]
        for (name, purpose, goal, raised, cid, mg, desc) in funds:
            db.session.add(GivingFund(
                name=name, slug=_slug(name), purpose=purpose,
                goal_amount=goal, raised_amount=raised, college_id=cid,
                description=desc, minimum_gift=mg,
            ))
        db.session.flush()

    # ─── Financial Aid Types ─────────────────────────────────────────────
    if not FinancialAidType.query.first():
        aid_types = [
            ('Land-Grant Opportunity Scholarship', 'Scholarship',
             'Ohio resident, first-generation, Pell-eligible, top 10% class rank',
             'Full tuition + fees', 'February 1',
             'The signature Land-Grant Scholarship covers tuition, mandatory '
             'fees, and a stipend for room and board.'),
            ('Eminence Fellows Program', 'Scholarship',
             'Top 1% nationally, demonstrated leadership and service',
             'Full tuition + study abroad + $3,000 enrichment', 'November 1',
             'Eminence Fellows are admitted in cohorts of 25 — the most '
             'prestigious undergraduate scholarship at Ohio State.'),
            ('Morrill Scholarship', 'Scholarship',
             'Underrepresented minority, demonstrated leadership',
             'Up to full tuition', 'February 1',
             'Named for the Morrill Land-Grant Act — supports diversity in '
             'higher education with renewable awards.'),
            ('Maximus Scholarship', 'Scholarship',
             'Top 5% class rank, 1370+ SAT or 30+ ACT',
             'Up to full tuition', 'February 1',
             'Merit award for top Ohio applicants — renewable for four years.'),
            ('Provost Scholarship', 'Scholarship',
             'Top 10% class rank, 1300+ SAT or 28+ ACT',
             '$5,500/year', 'February 1',
             'A renewable academic merit award available to incoming '
             'first-year students.'),
            ('Trustee Scholarship', 'Scholarship',
             'Top 25% class rank, 1240+ SAT or 26+ ACT',
             '$3,000/year', 'February 1',
             'A renewable academic merit award available to incoming '
             'first-year students.'),
            ('Buckeye Opportunity Program', 'Grant',
             'Pell-eligible, Ohio resident, full-time enrollment',
             'Bridges all unmet need', 'March 1',
             'Ohio State guarantees that all Pell-eligible Ohio residents '
             'graduate from OSU debt-free at the undergraduate tuition level.'),
            ('Federal Pell Grant', 'Grant', 'Pell-eligible per FAFSA',
             'Up to $7,395/year', 'October 1 (FAFSA opens)',
             'The federal need-based grant — apply via FAFSA each year.'),
            ('FSEOG', 'Grant', 'Highest Pell need, FAFSA-eligible',
             'Up to $4,000/year', 'October 1 (FAFSA opens)',
             'Federal Supplemental Educational Opportunity Grant.'),
            ('Ohio College Opportunity Grant', 'Grant',
             'Ohio resident, lowest income tier',
             'Up to $4,400/year', 'October 1 (FAFSA opens)',
             'State of Ohio need-based grant — automatic via FAFSA.'),
            ('Federal Direct Subsidized Loan', 'Loan',
             'Pell-eligible, FAFSA-eligible undergraduate',
             '$3,500–$5,500/year', 'October 1 (FAFSA opens)',
             'Government pays the interest while you are enrolled at least half-time.'),
            ('Federal Direct Unsubsidized Loan', 'Loan',
             'Any FAFSA filer',
             '$5,500–$7,500/year (UG), up to $20,500/year (Grad)', 'October 1',
             'Interest accrues from disbursement — available regardless of need.'),
            ('Parent PLUS Loan', 'Loan',
             'Credit-approved parent of a dependent undergraduate',
             'Up to cost of attendance', 'October 1 (FAFSA opens)',
             'A federal loan in the parent\'s name — disbursed to the student account.'),
            ('Federal Work-Study', 'Work-Study',
             'Pell-eligible, FAFSA-eligible',
             'Up to $3,200/year', 'October 1 (FAFSA opens)',
             'Part-time on-campus jobs with FWS funding — typically 10–15 hours/week.'),
            ('University Honors Scholarship', 'Scholarship',
             'Admitted Honors student',
             '$2,500/year', 'February 1',
             'Renewable scholarship for incoming Honors Program students.'),
            ('National Buckeye Scholarship', 'Scholarship',
             'Out-of-state resident, top 30% class rank',
             '$15,500/year', 'February 1',
             'Renewable merit award for top non-Ohio applicants.'),
            ('Distinction Scholarship', 'Scholarship',
             'High school valedictorian or salutatorian',
             '$2,000/year', 'February 1',
             'Renewable merit award for top of class.'),
            ('Buckeye Loan Repayment Award', 'Loan',
             'Eligible OSU graduates in public service',
             '$5,000/year for up to 3 years', 'July 1',
             'Loan-repayment assistance for OSU alumni in qualifying public-service careers.'),
        ]
        for (name, cat, elig, rng, dl, desc) in aid_types:
            db.session.add(FinancialAidType(
                name=name, slug=_slug(name), category=cat,
                eligibility=elig, award_range=rng, deadline=dl,
                description=desc,
            ))
        db.session.flush()

    if not FinancialAidForm.query.first():
        forms = [
            ('Free Application for Federal Student Aid (FAFSA)', 'Undergraduate',
             'October 1 – Closes for priority on March 1',
             'The FAFSA determines eligibility for all federal aid and most '
             'OSU institutional aid. OSU\'s school code is 003090.'),
            ('Ohio State Scholarship Application', 'Undergraduate',
             'October 1 – February 1',
             'The OSU Scholarship Application unlocks 600+ donor-funded awards. '
             'Required for consideration for many merit scholarships.'),
            ('CSS Profile (Optional)', 'Undergraduate',
             'October 1 – March 1',
             'OSU does not require the CSS Profile; some students complete it '
             'for outside scholarship organizations.'),
            ('Graduate FAFSA', 'Graduate',
             'October 1 – March 1',
             'Graduate students complete the FAFSA for federal loan eligibility.'),
            ('GA / TA / GRA Funding Form', 'Graduate',
             'Varies by program',
             'Most graduate students are funded via Graduate Associate '
             '(GA / TA / GRA) appointments coordinated by their academic program.'),
            ('International Financial Statement', 'International',
             'Same deadline as admission application',
             'International applicants must document ability to fund first-year '
             'cost of attendance.'),
            ('Transfer Aid Worksheet', 'Transfer',
             'Rolling — submit with application',
             'Transfer applicants supply prior-school aid summary so '
             'institutional aid can be evaluated.'),
            ('Special Circumstances Appeal', 'Undergraduate',
             'Any time',
             'Submit if family income has dropped, lost employment, or had '
             'extraordinary medical expenses after FAFSA filing.'),
        ]
        for (name, aud, win, desc) in forms:
            db.session.add(FinancialAidForm(
                name=name, slug=_slug(name), audience=aud,
                submit_window=win, description=desc,
            ))
        db.session.flush()

    # ─── College Leaders + Milestones + Diversity Programs ──────────────
    if not CollegeLeader.query.first():
        leaders = [
            ('Walter "Ted" Carter, Jr.', 'President', 1, 'president@osu.edu',
             'Walter "Ted" Carter, Jr. became the 17th president of The Ohio '
             'State University on January 1, 2024. A retired three-star admiral, '
             'Carter previously served as president of the University of Nebraska System.'),
            ('Karla Zadnik', 'Acting Executive Vice President and Provost', 2,
             'provost@osu.edu',
             'Karla Zadnik serves as acting EVPP and is the Glenn A. Fry Professor '
             'of Optometry and Physiological Optics.'),
            ('Peter Mohler', 'EVP for Research, Innovation, and Knowledge', 3,
             'research@osu.edu',
             'Dr. Peter Mohler leads OSU\'s $1.3B annual research enterprise.'),
            ('Melissa Gilliam', 'EVP and Provost-Designate', 4, 'provost-elect@osu.edu',
             'Dr. Melissa Gilliam will join Ohio State as the next executive '
             'vice president and provost in summer 2025.'),
            ('Mike Papadakis', 'Senior Vice President and Chief Financial Officer', 5,
             'cfo@osu.edu',
             'Mike Papadakis oversees all finance and administration functions '
             'across the university and Wexner Medical Center.'),
            ('Ross Bjork', 'Athletic Director', 6, 'athletics@osu.edu',
             'Ross Bjork became the 11th director of athletics in January 2024.'),
            ('John "Jack" Stanford', 'SVP for Student Life', 7, 'studentlife@osu.edu',
             'Dr. Jack Stanford oversees housing, dining, recreation, and the Ohio Union.'),
            ('James Schuler', 'SVP for Talent, Culture & Human Resources', 8,
             'hr@osu.edu',
             'James Schuler leads HR strategy across the largest single-campus '
             'university workforce in the United States.'),
            ('Hal Paz', 'EVP for Health Sciences', 9, 'healthsciences@osu.edu',
             'Dr. Hal Paz oversees the seven health-sciences colleges and the '
             'Wexner Medical Center.'),
            ('Patti Patrick', 'VP for Communications', 10, 'communications@osu.edu',
             'Patti Patrick leads Ohio State\'s strategic communications.'),
            ('David Harrison', 'VP for Government Affairs', 11, 'govaffairs@osu.edu',
             'David Harrison connects Ohio State with city, state, and federal partners.'),
            ('Susan Olesik', 'Dean of the Graduate School', 12, 'gradschool@osu.edu',
             'Dr. Susan Olesik is the Dow Professor in Analytical Chemistry and '
             'dean of the Graduate School.'),
        ]
        for (name, title, rank, email, bio) in leaders:
            db.session.add(CollegeLeader(
                name=name, slug=_slug(name), title=title, rank=rank,
                email=email, bio=bio,
            ))
        db.session.flush()

    if not HistoryMilestone.query.first():
        milestones = [
            (1862, 'Morrill Land-Grant Act Signed',
             'President Lincoln signed the Morrill Act, granting federal land '
             'for the establishment of public colleges teaching agriculture, '
             'mechanic arts, and military tactics.'),
            (1870, 'Ohio Agricultural and Mechanical College Founded',
             'Ohio chartered a new institution under the Morrill Act, on '
             'farmland north of Columbus purchased from William Neil.'),
            (1873, 'First Class Begins',
             '24 students arrived for the inaugural class — all male, free of charge.'),
            (1875, 'Edward Orton Inaugurated as First President',
             'Geologist Edward Orton became OSU\'s first president and served until 1881.'),
            (1878, 'Name Changes to The Ohio State University',
             'The Ohio General Assembly renamed the institution to reflect its '
             'expanding role as a comprehensive university.'),
            (1879, 'First Graduates',
             'Six men received the Bachelor of Science — the first OSU degrees.'),
            (1888, 'First Female Graduate',
             'Bertha Lamme became the first woman to earn a degree at OSU.'),
            (1890, 'Second Morrill Act Funds Land-Grant Mission',
             'The Second Morrill Act provided federal funds to expand land-grant '
             'institutions, including OSU Extension across all 88 Ohio counties.'),
            (1898, 'Carmen Ohio Composed',
             'Senior Fred A. Cornell wrote the alma mater "Carmen Ohio" on a '
             'train ride back from a football loss at Michigan.'),
            (1922, 'Ohio Stadium Opens',
             'The 66,210-seat Horseshoe was dedicated for the season opener — '
             'OSU football has played there ever since.'),
            (1934, 'Jesse Owens Enrolls',
             'Future Olympic champion Jesse Owens enrolled at Ohio State and '
             'broke three world records and tied a fourth in 45 minutes at the '
             '1935 Big Ten meet.'),
            (1953, 'Wexner Medical Center Founded',
             'The first University Hospital opened — predecessor to today\'s '
             'Wexner Medical Center, one of the nation\'s top academic medical centers.'),
            (1958, 'Faculty Senate Established',
             'OSU adopted its current shared-governance model with the founding '
             'of the University Senate.'),
            (1968, 'College of Veterinary Medicine Receives First NIH Center Grant',
             'OSU veterinarians began landmark large-animal cardiovascular research.'),
            (1986, 'Wexner Center for the Arts Opens',
             'The Wexner Center, designed by Peter Eisenman, was the first '
             'major public building of the deconstructivist style.'),
            (1998, 'James Cancer Hospital Opens',
             'Arthur G. James Cancer Hospital opened, becoming an NCI-Designated '
             'Comprehensive Cancer Center in 2001.'),
            (2002, 'Football National Championship',
             'OSU defeated Miami 31-24 in double overtime to win the 2002 BCS title.'),
            (2014, 'Football National Championship',
             'The Buckeyes defeated Oregon 42-20 to win the inaugural '
             'College Football Playoff title.'),
            (2018, 'Pelotonia Surpasses $200M Raised',
             'The annual Pelotonia bike ride passed the $200M raised mark for '
             'cancer research at the James.'),
            (2024, 'College Football Playoff National Championship',
             'OSU defeated Notre Dame 34-23 to win the 2024 CFP National Championship — '
             'the program\'s 9th national title.'),
        ]
        for (yr, title, desc) in milestones:
            db.session.add(HistoryMilestone(year=yr, title=title, description=desc))
        db.session.flush()

    if not DiversityProgram.query.first():
        dprogs = [
            ('Office of Diversity and Inclusion', 'All Students',
             'James L. Moore III, VP for Diversity & Inclusion',
             'ODI partners with each college to advance access, opportunity, '
             'and inclusive excellence university-wide.'),
            ('Multicultural Center', 'All Students',
             'Indra Leyva-Santiago, Director',
             'The Multicultural Center is the campus hub for diversity '
             'programming, dialogue, and intercultural learning.'),
            ('Bell National Resource Center', 'African American Male Students',
             'James L. Moore III, Founding Director',
             'The Todd Anthony Bell National Resource Center on the African '
             'American Male — the only one of its kind in U.S. higher education.'),
            ('Hale Black Cultural Center', 'African American Students',
             'Larry Williamson, Director',
             'The Frank W. Hale, Jr. Black Cultural Center serves as a home '
             'away from home for Black Buckeyes since 1989.'),
            ('LGBTQ Student Services', 'LGBTQ Students',
             'Casey Hayward, Director',
             'Programming, training, and direct support for LGBTQ-identifying '
             'students, faculty, and staff.'),
            ('Disability Services', 'Students with Disabilities',
             'Scottie Gibbs, Director',
             'Reasonable accommodations and disability-related advocacy.'),
            ('First-Generation Student Services', 'First-Generation College Students',
             'Lola Bauer, Director',
             'Holistic support for the 18% of incoming Buckeyes who are first '
             'in their family to attend college.'),
            ('Women\'s Place', 'Women Faculty and Staff',
             'Kelsey Beavers, Director',
             'A central hub for women\'s policy, advocacy, and gender-equity '
             'research at OSU.'),
            ('Latinx Cultural Center', 'Latinx Students',
             'Nuray Coronado, Director',
             'Programs and community celebrating Latinx culture, heritage, '
             'and identity.'),
            ('Asian American & Pacific Islander Cultural Center', 'AAPI Students',
             'James Wong, Coordinator',
             'AAPI student services and programming since 2018.'),
            ('Native American Indigenous Cultural Center', 'Indigenous Students',
             'Marti Chaatsmith, Coordinator',
             'Cultural programs honoring the Indigenous heritage of the lands '
             'on which Ohio State stands.'),
            ('Veterans Education', 'Student Veterans',
             'Adam Lima, Director',
             'A central office for the 1,800+ Buckeyes using military '
             'education benefits.'),
        ]
        for (name, aud, director, desc) in dprogs:
            db.session.add(DiversityProgram(
                name=name, slug=_slug(name), audience=aud,
                director=director, description=desc,
            ))
        db.session.flush()

    # ─── Campus Services ─────────────────────────────────────────────────
    if not CampusService.query.first():
        services = [
            ('BuckeyeID Card Office', 'Identity', '(614) 292-0400',
             '3040 Ohio Union, 1739 N. High Street',
             'Issues the official BuckeyeID — the campus ID, library card, '
             'meal plan key, and access pass to residence halls and the RPAC.'),
            ('IT Service Desk', 'Technology', '(614) 688-4357',
             'Baker Systems Engineering 022',
             '24/7 help with email, BuckeyeMail, Carmen, OnBase, and university '
             'computing accounts.'),
            ('Counseling and Consultation Service (CCS)', 'Wellness',
             '(614) 292-5766', '4th Floor, Younkin Success Center',
             'Free individual, group, and crisis counseling for OSU students.'),
            ('Student Health Services', 'Wellness', '(614) 292-4321',
             'Wilce Student Health Center, 1875 Millikin Road',
             'Primary care, sports medicine, women\'s health, dermatology, and '
             'travel medicine for OSU students.'),
            ('Career Services', 'Career', '(614) 688-3898',
             'Younkin Success Center, 1640 Neil Avenue',
             'Career counseling, interview prep, and the BuckeyeCareers online '
             'job board.'),
            ('Dennis Learning Center', 'Academic', '(614) 688-4011',
             '250B Younkin Success Center',
             'Academic coaching, tutoring, and study-skills programs.'),
            ('Office of Student Life Tutoring', 'Academic', '(614) 247-3711',
             'Younkin Success Center, ground floor',
             'Free tutoring for 100+ undergraduate courses.'),
            ('Writing Center', 'Academic', '(614) 688-4291',
             '4120A Smith Lab',
             'One-on-one consultations for writers at every stage and skill level.'),
            ('Math and Statistics Learning Center', 'Academic', '(614) 688-4661',
             '440 Cockins Hall',
             'Drop-in tutoring for first-year math, calculus, and statistics courses.'),
            ('Office of Student Life Buckeye Food Alliance', 'Wellness',
             '(614) 247-1284', 'Lincoln Tower B0190',
             'Campus food pantry — free groceries for students with food insecurity.'),
            ('Office of International Affairs', 'International', '(614) 292-6101',
             'Enarson Classroom Building, 2009 Millikin Road',
             'Immigration advising, study abroad, and international student services.'),
            ('Office of the University Registrar', 'Administrative', '(614) 292-9330',
             'Lincoln Tower, 1800 Cannon Drive',
             'Registration, transcripts, enrollment verification, and graduation services.'),
            ('Bursar Office', 'Administrative', '(614) 292-1056',
             'Lincoln Tower, 1800 Cannon Drive',
             'Tuition billing, payments, refunds, and 1098-T tax forms.'),
            ('Buckeye Link', 'Administrative', '(614) 292-0300',
             'Student Academic Services Building, 281 W. Lane Ave',
             'One-stop shop for financial aid, registration, transcripts, '
             'and Buckeye ID matters.'),
            ('Office of Distance Education and eLearning', 'Academic',
             '(614) 292-8860', '154 W. 12th Avenue',
             'Online programs, course design, and digital learning tools.'),
            ('Office of Disability Services', 'Wellness', '(614) 292-3307',
             '098 Baker Hall',
             'Disability documentation, classroom accommodations, and assistive technology.'),
            ('Student Conduct', 'Administrative', '(614) 292-0748',
             '33 W. 11th Avenue',
             'Investigates academic misconduct, code of student conduct '
             'violations, and the disciplinary process.'),
            ('Department of Public Safety', 'Safety', '(614) 292-2121',
             '901 Woody Hayes Drive',
             'University Police Division — 24/7 sworn officers serving the OSU community.'),
            ('Office of Off-Campus and Commuter Student Services', 'Student Life',
             '(614) 292-0100', '3106 Ohio Union',
             'Off-campus housing search, roommate matching, and commuter services.'),
            ('Buckeye Wireless Help', 'Technology', '(614) 688-4357',
             'BO22 Baker Systems',
             'eduroam, OSU Wireless, and gaming-console-on-residential-network support.'),
            ('Recreation and Wellness Center', 'Recreation', '(614) 292-7671',
             '337 Annie & John Glenn Avenue',
             'The RPAC — recreational sports, group fitness, intramural sports, '
             'and wellness programming.'),
        ]
        for (name, cat, phone, loc, desc) in services:
            db.session.add(CampusService(
                name=name, slug=_slug(name), category=cat,
                phone=phone, location=loc, description=desc,
            ))
        db.session.flush()

    # ─── Admissions Pathways ─────────────────────────────────────────────
    if not AdmissionsPathway.query.first():
        pathways = [
            # Undergraduate
            ('undergraduate', 'First-Year Application', '1370+ SAT or 30+ ACT (test-optional through 2026)',
             'Common App or Coalition App with OSU supplement. Counselor recommendation, transcript, optional essay.',
             'February 1', 60),
            ('undergraduate', 'Honors & Scholars Admission',
             'Top 5% class rank, demonstrated leadership',
             'Submit the Honors & Scholars supplement by November 1 for early consideration.',
             'November 1', 60),
            ('undergraduate', 'Regional Campus Admission',
             '2.0+ GPA, evidence of college readiness',
             'Apply directly to Lima, Mansfield, Marion, Newark, or Wooster — option to change campus after one year.',
             'Rolling', 60),
            ('undergraduate', 'Buckeye Bound (Pre-Admission)',
             'Ohio high school junior, 3.0+ GPA',
             'Conditional admission offered at participating Ohio high schools — confirm enrollment by May 1 of senior year.',
             'February 1', 0),
            ('undergraduate', 'Test-Optional Pathway',
             'No SAT or ACT score required for fall 2025–2026',
             'Submit application without standardized test scores — academic record and rigor will be primary evaluation.',
             'February 1', 60),
            # Graduate
            ('graduate', 'Master\'s Application',
             'Bachelor\'s degree from regionally accredited institution',
             'Submit through the Graduate & Professional Admissions portal. GRE varies by program.',
             'Varies by program', 70),
            ('graduate', 'Doctoral Application',
             '3.0+ undergrad GPA, research experience, three recommendations',
             'Submit by program-specific deadline. Most PhD programs are fully funded with GA appointments.',
             'December 1', 70),
            ('graduate', 'Graduate Certificate',
             'Bachelor\'s degree',
             'Short-format graduate credential — typically 12–18 credit hours.',
             'Rolling', 70),
            ('graduate', 'Combined Bachelor\'s/Master\'s',
             'OSU junior with 3.4+ GPA',
             'Apply during junior year to count graduate credits toward both degrees.',
             'February 1', 0),
            ('graduate', 'Non-Degree Graduate',
             'Bachelor\'s degree, specific course interest',
             'Take graduate courses without admission to a degree program.',
             'Rolling', 70),
            # Transfer
            ('transfer', 'Ohio Public Institution Transfer',
             '24+ transferable credits, 2.0+ GPA',
             'Use Transferology to map your credits before applying.',
             'May 1 (fall) / Nov 1 (spring)', 60),
            ('transfer', 'Out-of-State Transfer',
             '24+ transferable credits, 2.5+ GPA',
             'Submit official transcripts and a one-page personal statement.',
             'May 1', 60),
            ('transfer', 'Community College 2+2 Pathway',
             'AA / AS from approved community college',
             'Guaranteed junior standing if degree completed before transfer.',
             'May 1', 60),
            ('transfer', 'Buckeye Transfer Pathway',
             '30+ Ohio community college credits, 2.5+ GPA',
             'Direct path from Columbus State, Cuyahoga CC, Cincinnati State, '
             'Sinclair, Owens, and others.',
             'May 1', 0),
            # International
            ('international', 'International First-Year',
             'Equivalent of U.S. high school diploma, English proficiency',
             'Submit application with TOEFL 79+ / IELTS 6.5+ / Duolingo 110+.',
             'February 1', 70),
            ('international', 'International Transfer',
             'Equivalent of U.S. associate degree',
             'WES or ECE credential evaluation required for credits earned outside the U.S.',
             'May 1', 70),
            ('international', 'International Graduate',
             'Bachelor\'s degree equivalent, TOEFL 79+',
             'Submit through Graduate & Professional Admissions with credential evaluation.',
             'Varies by program', 70),
            # Pathways
            ('pathways', 'OSU Academy (College Credit Plus)',
             'Ohio high school student in grades 9–12',
             'Take OSU courses for both high school and college credit at no cost.',
             'Rolling', 0),
            ('pathways', 'Adult Learners (60+ Years)',
             'Ohio resident age 60+',
             'Audit OSU courses tuition-free under the Program 60 plan.',
             'Rolling', 0),
            ('pathways', 'Buckeye Returns',
             'Former OSU student with no degree yet',
             'Streamlined re-enrollment for students who left OSU and want to finish their degree.',
             'Rolling', 0),
        ]
        for (level, name, req, desc, dl, fee) in pathways:
            db.session.add(AdmissionsPathway(
                level=level, name=name, slug=_slug(level + ' ' + name),
                description=desc, requirements=req,
                deadline=dl, application_fee=fee,
            ))
        db.session.flush()

    db.session.commit()
