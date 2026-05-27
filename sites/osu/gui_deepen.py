#!/usr/bin/env python3
"""Generate GUI deepen tasks for the OSU mirror.

Produces 1500+ deterministic GUI tasks across the 30+ new surfaces added in
the vanilla-deepen pass. Each task is tagged ``[gui-deepen-v1]`` and uses the
id prefix ``Ohio State University--gui_<page>_<NNN>``. Tasks are appended to
tasks.jsonl after the existing curated benchmark tasks (Ids 0–19).
"""
from __future__ import annotations

import json
import os
from collections import OrderedDict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_FILE = os.path.join(BASE_DIR, 'tasks.jsonl')

WEB_NAME = 'Ohio State University'
WEB_URL = 'http://localhost:40015/'
UPSTREAM = 'https://www.osu.edu/'


def build_tasks():
    from app import (app, College, Department, Program, NewsArticle, Event,
                     ResearchCenter, Faculty, AthleticTeam, AthleticGame,
                     AthleticRosterMember, AlumniChapter, GivingFund,
                     FinancialAidType, FinancialAidForm, CollegeLeader,
                     HistoryMilestone, DiversityProgram, CampusService,
                     LibraryBranch, DiningLocation, DiningMenuItem,
                     StudentLifeCategory, AdmissionsPathway)

    tasks: list[dict] = []

    def add(page: str, idx: int, q: str):
        tid = f"{WEB_NAME}--gui_{page}_{idx:03d}"
        tasks.append({
            "web_name": WEB_NAME,
            "id": tid,
            "ques": q,
            "web": WEB_URL,
            "upstream_url": UPSTREAM,
            "tags": [page, "[gui-deepen-v1]"],
        })

    with app.app_context():
        # ── colleges (16 × 4 = 64) ─────────────────────────────────────
        colleges = College.query.order_by(College.name).all()
        i = 1
        for c in colleges:
            add("college_detail", i,
                f"Open the Ohio State College page for '{c.name}' "
                f"(at /academics/colleges/{c.slug}) and report the dean's name listed on the page.")
            i += 1
            add("college_detail", i,
                f"On the Ohio State '{c.name}' college page, report the founding year shown in the header.")
            i += 1
            add("college_detail", i,
                f"From the Ohio State '{c.name}' college page, list the first department shown in the 'Departments & Schools' section.")
            i += 1
            add("college_detail", i,
                f"On the Ohio State college page for '{c.name}', report the undergraduate enrollment shown in the stat bar.")
            i += 1

        # ── admissions level (5 × 6 = 30) ─────────────────────────────
        i = 1
        for lvl in ['undergraduate', 'graduate', 'transfer', 'international', 'pathways']:
            paths = AdmissionsPathway.query.filter_by(level=lvl).all()
            for p in paths[:6]:
                add("admissions_pathway", i,
                    f"On Ohio State's '{lvl}' admissions page (/admissions/{lvl}), open the pathway '{p.name}' and report its deadline.")
                i += 1

        # ── admissions visit / apply / virtual-tour (24) ──────────────
        i = 1
        for label, prompt in [
            ('visit', "Visit Ohio State page"),
            ('virtual-tour', "Virtual Tour"),
            ('apply', "Apply page"),
        ]:
            for fld in ['Full Name', 'Email', 'Tour Date', 'Group Size',
                        'Citizenship', 'Intended Program', 'Personal Statement',
                        'High School']:
                add("admissions_forms", i,
                    f"On the Ohio State admissions {label} page (/admissions/{label}), confirm the {fld} input field is present.")
                i += 1

        # ── financial aid types (18 × 3 = 54) ─────────────────────────
        i = 1
        for t in FinancialAidType.query.order_by(FinancialAidType.name).all():
            add("financial_aid_type", i,
                f"Open Ohio State financial-aid type '{t.name}' (at /financial-aid/types/{t.slug}) and report the listed award range.")
            i += 1
            add("financial_aid_type", i,
                f"On the Ohio State '{t.name}' financial-aid type page, report the deadline shown.")
            i += 1
            add("financial_aid_type", i,
                f"From the Ohio State '{t.name}' page, report the category badge (Scholarship/Grant/Loan/Work-Study).")
            i += 1

        # ── financial aid forms (8 × 4 = 32) ──────────────────────────
        i = 1
        for f in FinancialAidForm.query.order_by(FinancialAidForm.name).all():
            add("financial_aid_form", i,
                f"Open the Ohio State financial-aid form '{f.name}' (/financial-aid/forms/{f.slug}) and report the audience listed.")
            i += 1
            add("financial_aid_form", i,
                f"On the Ohio State form page '{f.name}', report the submission window.")
            i += 1
            add("financial_aid_form", i,
                f"On the Ohio State '{f.name}' form page, fill name 'Pat Buckeye', email 'pat@example.com', family income 60000, dependents 2, submit and report the confirmation #.")
            i += 1
            add("financial_aid_form", i,
                f"On the Ohio State '{f.name}' form page, confirm the 'Family Adjusted Gross Income' input is present.")
            i += 1

        # ── student life categories (10 × 4 = 40) ─────────────────────
        i = 1
        for c in StudentLifeCategory.query.order_by(StudentLifeCategory.name).all():
            add("student_life_category", i,
                f"Open the Ohio State student-life category '{c.name}' (/student-life/{c.slug}) and report the contact email shown.")
            i += 1
            add("student_life_category", i,
                f"On Ohio State student-life category '{c.name}', report the tagline shown under the title.")
            i += 1
            add("student_life_category", i,
                f"From the Ohio State student-life page, confirm that '{c.name}' is one of the listed categories.")
            i += 1
            add("student_life_category", i,
                f"On the Ohio State '{c.name}' page, report the first paragraph of the 'About' section first sentence.")
            i += 1

        # ── library branches (13 × 4 = 52) ────────────────────────────
        i = 1
        for b in LibraryBranch.query.order_by(LibraryBranch.name).all():
            add("library_branch", i,
                f"Open the Ohio State library branch '{b.name}' (at /library/{b.slug}) and report the head librarian's name.")
            i += 1
            add("library_branch", i,
                f"On the Ohio State library page for '{b.name}', report the phone number listed.")
            i += 1
            add("library_branch", i,
                f"On the Ohio State '{b.name}' library page, report the hours shown.")
            i += 1
            add("library_branch", i,
                f"On the Ohio State '{b.name}' library page, report the collection size (volumes).")
            i += 1

        # ── library study-room reserve (10) ───────────────────────────
        for k, prompt in enumerate([
            "Reserve a study room at the Thompson Library for date 2026-06-20.",
            "On the Ohio State library study-room reservation form, confirm the 'Duration (hours)' field is present.",
            "On the Ohio State /library/study-room/reserve page, list one branch shown in the branches list.",
            "Submit a study-room reservation for the Science & Engineering Library with name 'Sam Buckeye' and date 2026-07-12 — report the confirmation #.",
            "On the Ohio State study-room reservation page, confirm the 'Preferred Room #' field is present.",
            "On the Ohio State library study-room page, list one of the listed reservation policies.",
            "Reserve a study room at the Cartoon Library on 2026-08-01 — does the form accept the submission?",
            "On Ohio State's library study-room reservation page, confirm the 'Start Time' field accepts text.",
            "On Ohio State's library study-room reservation page, confirm the 'Purpose' field is optional.",
            "Open Ohio State /library/study-room/reserve and report the page heading shown.",
        ], 1):
            add("library_reserve", k, prompt)

        # ── dining locations (12 × 4 = 48) ────────────────────────────
        i = 1
        for d in DiningLocation.query.order_by(DiningLocation.name).all():
            add("dining_location", i,
                f"Open Ohio State dining location '{d.name}' (at /dining/{d.slug}) and report the cuisine type shown.")
            i += 1
            add("dining_location", i,
                f"On the Ohio State '{d.name}' dining page, report the hours of operation.")
            i += 1
            add("dining_location", i,
                f"On the Ohio State dining page for '{d.name}', report the seat count shown.")
            i += 1
            add("dining_location", i,
                f"On Ohio State dining '{d.name}' page, list the first menu item under any meal heading.")
            i += 1

        # ── dining menu by date (12) ──────────────────────────────────
        i = 1
        for d in DiningLocation.query.order_by(DiningLocation.name).all():
            add("dining_menu", i,
                f"On the Ohio State dining menu page for '{d.name}' on 2026-06-15 (at /dining/menu/{d.slug}/2026-06-15), list the first menu item shown.")
            i += 1

        # ── dining_order POST + GET (10) ──────────────────────────────
        for k, prompt in enumerate([
            "On Ohio State /dining/order, submit an order for 'Buckeye Burger' at Traditions at Scott — report the confirmation #.",
            "On Ohio State /dining/order, confirm the 'Pickup Time' field is present.",
            "On Ohio State /dining/order, confirm the 'Special Instructions' field is present.",
            "Open Ohio State /dining/order and report the dining location dropdown's first option label.",
            "On Ohio State /dining/order, submit an order with quantity 3 of any item — report the resulting confirmation #.",
            "Open Ohio State /dining/order and report the first menu item option shown in the Menu Item dropdown.",
            "On Ohio State /dining/order, can a user choose more than one dining location at a time? (Yes/No)",
            "On Ohio State /dining/order, what payment methods are listed in the 'How It Works' panel?",
            "On Ohio State /dining/order, confirm the 'Quantity' input accepts numbers from 1 to 6.",
            "On Ohio State /dining/order, what is the minimum required wait time before pickup?",
        ], 1):
            add("dining_order", k, prompt)

        # ── athletics: teams × {schedule, roster, stats, tickets} ─────
        teams = AthleticTeam.query.order_by(AthleticTeam.name).all()
        i = 1
        for t in teams:
            add("athletics_schedule", i,
                f"Open the Ohio State {t.sport} schedule for '{t.name}' (at /athletics/buckeyes/{t.slug}/schedule) and report the first opponent listed.")
            i += 1
        i = 1
        for t in teams:
            add("athletics_roster", i,
                f"Open the Ohio State {t.sport} roster for '{t.name}' (at /athletics/buckeyes/{t.slug}/roster) and report the player wearing jersey number 1.")
            i += 1
        i = 1
        for t in teams:
            add("athletics_stats", i,
                f"Open the Ohio State {t.sport} team stats page for '{t.name}' (at /athletics/buckeyes/{t.slug}/stats) and report the number of wins shown.")
            i += 1
        i = 1
        for t in teams:
            add("athletics_team_overview", i,
                f"On Ohio State '{t.name}' team page (at /athletics/{t.slug}), report the head coach.")
            i += 1

        # ── athletics tickets (sports list × 2 = 36, plus 20 game purchases)
        sports = sorted({t.sport for t in teams})
        i = 1
        for s in sports:
            add("athletics_tickets", i,
                f"On Ohio State /athletics/tickets?sport={s}, report the venue of the first home game listed.")
            i += 1
            add("athletics_tickets", i,
                f"On Ohio State /athletics/tickets?sport={s}, list the TV network for the first home game.")
            i += 1
        # ticket purchases: 20 specific games
        games = AthleticGame.query.filter(AthleticGame.home_away == 'Home').limit(30).all()
        i = 1
        for g in games[:20]:
            t = AthleticTeam.query.get(g.team_id)
            add("athletics_ticket_buy", i,
                f"On Ohio State /athletics/tickets/{g.id} (game vs. {g.opponent}), submit a ticket purchase for 'Pat Buckeye', section 30A, quantity 2 — report the total price.")
            i += 1

        # ── alumni chapters (20 × 4 = 80) ─────────────────────────────
        chapters = AlumniChapter.query.order_by(AlumniChapter.region).all()
        i = 1
        for c in chapters:
            add("alumni_chapter", i,
                f"Open Ohio State alumni chapter '{c.region}' (at /alumni/chapter/{c.slug}) and report the chapter president's name.")
            i += 1
            add("alumni_chapter", i,
                f"On Ohio State alumni chapter '{c.region}', report the founding year shown.")
            i += 1
            add("alumni_chapter", i,
                f"On Ohio State alumni chapter '{c.region}', report the 'Next Event' shown in the orange callout.")
            i += 1
            add("alumni_chapter", i,
                f"On Ohio State alumni chapter '{c.region}', submit a join form for 'Pat Buckeye' with email pat@example.com, grad year 2020, degree BA — report the membership #.")
            i += 1

        # ── giving funds (12 × 4 = 48) ────────────────────────────────
        i = 1
        for f in GivingFund.query.order_by(GivingFund.name).all():
            add("giving_fund", i,
                f"Open Ohio State giving fund '{f.name}' (at /giving/{f.slug}) and report the goal amount shown.")
            i += 1
            add("giving_fund", i,
                f"On Ohio State giving fund '{f.name}', report the minimum-gift amount.")
            i += 1
            add("giving_fund", i,
                f"On Ohio State giving fund '{f.name}', report the purpose badge shown at the top.")
            i += 1
            add("giving_fund", i,
                f"On Ohio State giving fund '{f.name}', submit a gift of ${f.minimum_gift} from 'Pat Buckeye' (pat@example.com) — report the receipt #.")
            i += 1

        # ── leadership (12 × 3 = 36) ──────────────────────────────────
        leaders = CollegeLeader.query.order_by(CollegeLeader.rank).all()
        i = 1
        for l in leaders:
            add("leader_detail", i,
                f"Open Ohio State leader page for '{l.name}' (at /about/leadership/{l.slug}) and report the title shown.")
            i += 1
            add("leader_detail", i,
                f"On Ohio State leader page for '{l.name}', report the contact email listed.")
            i += 1
            add("leader_detail", i,
                f"On Ohio State leader page for '{l.name}', confirm the leader's rank number ({l.rank}) is shown.")
            i += 1

        # ── history (20) ──────────────────────────────────────────────
        i = 1
        for m in HistoryMilestone.query.order_by(HistoryMilestone.year).all():
            add("about_history", i,
                f"On Ohio State /about/history, find the milestone for the year {m.year} and report its title.")
            i += 1

        # ── diversity programs (12 × 2 = 24) ──────────────────────────
        i = 1
        for p in DiversityProgram.query.order_by(DiversityProgram.name).all():
            add("about_diversity", i,
                f"On Ohio State /about/diversity, find the program '{p.name}' and report the audience listed.")
            i += 1
            add("about_diversity", i,
                f"On Ohio State /about/diversity, find the program '{p.name}' and report the director listed.")
            i += 1

        # ── campus services (21 × 3 = 63) ─────────────────────────────
        services = CampusService.query.order_by(CampusService.name).all()
        i = 1
        for s in services:
            add("service_detail", i,
                f"Open Ohio State service page for '{s.name}' (at /services/{s.slug}) and report the phone number.")
            i += 1
            add("service_detail", i,
                f"On Ohio State service page for '{s.name}', report the listed location.")
            i += 1
            add("service_detail", i,
                f"On Ohio State service page for '{s.name}', submit a service request from 'Pat Buckeye' (pat@example.com) with description 'Need help' — report the ticket #.")
            i += 1

        # ── faculty contact (40 × 2 = 80) ─────────────────────────────
        faculty = Faculty.query.order_by(Faculty.name).limit(40).all()
        i = 1
        for f in faculty:
            add("contact_faculty", i,
                f"Open Ohio State /contact-faculty/{f.slug} and confirm the recipient is '{f.name}'.")
            i += 1
            add("contact_faculty", i,
                f"On Ohio State /contact-faculty/{f.slug}, submit a message from 'Pat Buckeye' (pat@example.com), subject 'Question', message 'Office hours?' — report the reference #.")
            i += 1

        # ── transcript / info request (20) ────────────────────────────
        for k, prompt in enumerate([
            "On Ohio State /transcript/request, submit a request from 'Pat Buckeye' (pat@example.com), student id .buckeye.1, electronic delivery to 'Self' — report the ticket #.",
            "On Ohio State /transcript/request, confirm the 'Delivery Method' selector is present.",
            "On Ohio State /transcript/request, report the price of an Express delivery.",
            "On Ohio State /transcript/request, report the price of an Electronic transcript.",
            "On Ohio State /transcript/request, report the price of a Mailed transcript.",
            "On Ohio State /transcript/request, confirm the 'Student ID' input is required.",
            "On Ohio State /info/request, submit an inquiry from 'Pat Buckeye' (pat@example.com) with program interest 'Computer Science and Engineering' — report the reference #.",
            "On Ohio State /info/request, confirm the 'Home State / Country' selector contains 'Ohio'.",
            "On Ohio State /info/request, list one item promised in the 'What You'll Receive' panel.",
            "On Ohio State /transcript/request, report the office name shown in the header.",
            "On Ohio State /info/request, report the page heading text.",
            "On Ohio State /info/request, confirm the 'Program of Interest' input accepts text.",
            "On Ohio State /info/request, confirm the 'Email' field is required.",
            "On Ohio State /transcript/request, list one delivery method option that is NOT 'electronic'.",
            "On Ohio State /info/request, list any 3 states/countries shown in the dropdown.",
            "On Ohio State /info/request, submit a request from 'International Buckeye' (intl@example.com) with home country 'International' — report the reference #.",
            "On Ohio State /transcript/request, submit a request for 'Pat Buckeye' (pat@example.com) with student id .pat.1 and Express delivery — report the ticket #.",
            "On Ohio State /transcript/request, confirm a FERPA-style consent disclaimer is shown.",
            "On Ohio State /info/request, confirm the form posts to the 'info_request' route.",
            "On Ohio State /info/request, report the gradient color used in the page header.",
        ], 1):
            add("requests", k, prompt)

        # ── buckeye link / buckeyeid / search (30) ────────────────────
        for k, prompt in enumerate([
            "On Ohio State /buckeye-link, what is the main address listed in the header?",
            "On Ohio State /buckeye-link, what is the listed phone number?",
            "On Ohio State /buckeye-link, list one service shown under 'Academic'.",
            "On Ohio State /buckeye-link, list one service shown under 'Wellness'.",
            "On Ohio State /buckeye-link, list one service shown under 'Administrative'.",
            "On Ohio State /buckeye-link, list one service shown under 'Technology'.",
            "On Ohio State /buckeye-link, list one service shown under 'Career'.",
            "On Ohio State /buckeye-link, click the 'Transcripts' tile and confirm it navigates to /transcript/request.",
            "On Ohio State /buckeye-link, click the 'Financial Aid' tile and confirm it navigates to /financial-aid.",
            "On Ohio State /buckeye-link, click the 'BuckID' tile and confirm it navigates to /buckeyeid.",
            "On Ohio State /buckeyeid, report the listed phone number for the BuckID Office.",
            "On Ohio State /buckeyeid, list the BuckID Office hours for Mon–Thu.",
            "On Ohio State /buckeyeid, what is the replacement-card fee shown on the page?",
            "On Ohio State /buckeyeid, what mobile wallet integrations are mentioned?",
            "On Ohio State /buckeyeid, list one place a BuckeyeID is accepted.",
            "On Ohio State search page, query 'cancer' and report whether any news articles appear.",
            "On Ohio State search page, query 'cybersecurity' and report whether any programs appear.",
            "On Ohio State search page, query 'football' and report whether any athletics results appear.",
            "On Ohio State search page, query 'astronomy' and report whether any departments appear.",
            "On Ohio State search page, query 'jazz' and report whether any results are returned.",
            "On Ohio State /services, filter by category 'Wellness' and report how many results are shown.",
            "On Ohio State /services, filter by category 'Academic' and report how many results are shown.",
            "On Ohio State /services, filter by category 'Administrative' and report how many results are shown.",
            "On Ohio State /services, report the first service shown when no filter is applied.",
            "On Ohio State /financial-aid/types, filter by 'Grant' and report how many grants are listed.",
            "On Ohio State /financial-aid/types, filter by 'Loan' and report how many loans are listed.",
            "On Ohio State /financial-aid/forms, filter by 'Graduate' and report how many forms are listed.",
            "On Ohio State /alumni page, report the total number of chapters listed.",
            "On Ohio State /giving page, report the first giving fund displayed.",
            "On Ohio State /library page, report how many library branches are shown in the directory.",
        ], 1):
            add("links_and_filters", k, prompt)

        # ── about hubs detail (15) ────────────────────────────────────
        for k, prompt in enumerate([
            "Open Ohio State /about/leadership and report the 'President' (rank 1) listed.",
            "Open Ohio State /about/leadership and report the 'Athletic Director' shown.",
            "Open Ohio State /about/leadership and report the 'EVP for Research, Innovation, and Knowledge' shown.",
            "Open Ohio State /about/history and report the title of the 1870 milestone.",
            "Open Ohio State /about/history and report the title of the 1922 milestone.",
            "Open Ohio State /about/history and report the title of the 2024 milestone.",
            "Open Ohio State /about/history and report the title of the 1862 milestone.",
            "Open Ohio State /about/history and confirm a milestone exists for 1898 (Carmen Ohio).",
            "Open Ohio State /about/diversity and confirm the 'Multicultural Center' is listed.",
            "Open Ohio State /about/diversity and confirm 'LGBTQ Student Services' is listed.",
            "Open Ohio State /about/diversity and confirm 'Bell National Resource Center' is listed.",
            "Open Ohio State /about and report the 'undergrad_count' stat shown.",
            "Open Ohio State /about and report the 'research_expenditure' stat shown ($ in billions).",
            "Open Ohio State /about and report the 'national_titles' stat shown.",
            "Open Ohio State /about and report the 'campuses' stat shown.",
        ], 1):
            add("about_hubs", k, prompt)

        # ── athletic_game detail (home games × 2 questions = ~200) ────
        i = 1
        for g in AthleticGame.query.filter(AthleticGame.home_away == 'Home').order_by(AthleticGame.id).all():
            t = AthleticTeam.query.get(g.team_id)
            add("athletics_game_tv", i,
                f"On Ohio State /athletics/tickets/{g.id} ({t.name} vs. {g.opponent}), report the TV broadcaster shown.")
            i += 1
            add("athletics_game_venue", i,
                f"On Ohio State /athletics/tickets/{g.id} ({t.name} vs. {g.opponent}), report the venue shown.")
            i += 1
            if i > 200:
                break

        # ── athletic roster member by team (random samples = 80) ──────
        i = 1
        for t in teams:
            members = AthleticRosterMember.query.filter_by(team_id=t.id).limit(3).all()
            for m in members:
                add("athletics_roster_detail", i,
                    f"On Ohio State /athletics/buckeyes/{t.slug}/roster, find roster member '{m.name}' and report their hometown.")
                i += 1

        # ── more program / department GET questions (200) ────────────
        progs = Program.query.order_by(Program.name).limit(100).all()
        i = 1
        for p in progs:
            add("program_credits", i,
                f"Open Ohio State program page for '{p.name}' (at /programs/{p.slug}) and report the credit-hour requirement shown.")
            i += 1
            add("program_deadline", i,
                f"On Ohio State program page for '{p.name}', report the application deadline shown.")
            i += 1

        # ── department detail (60 × 2 = 120) ─────────────────────────
        depts = Department.query.order_by(Department.name).limit(60).all()
        i = 1
        for d in depts:
            add("department_chair", i,
                f"Open Ohio State department page for '{d.name}' (at /departments/{d.slug}) and report the department chair.")
            i += 1
            add("department_phone", i,
                f"On Ohio State department page for '{d.name}', report the phone number shown.")
            i += 1

        # ── news article detail (40 × 2 = 80) ────────────────────────
        i = 1
        for a in NewsArticle.query.order_by(NewsArticle.published_date.desc()).limit(40).all():
            add("news_author", i,
                f"Open Ohio State news article '{a.title}' (at /news/{a.slug}) and report the author byline shown.")
            i += 1
            add("news_category", i,
                f"On Ohio State news article '{a.title}', report the article category shown.")
            i += 1

        # ── events (30 × 2 = 60) ─────────────────────────────────────
        i = 1
        for e in Event.query.order_by(Event.start_datetime).limit(30).all():
            add("event_organizer", i,
                f"Open Ohio State event '{e.title}' (at /events/{e.id}) and report the organizer listed.")
            i += 1
            add("event_location", i,
                f"On Ohio State event page '{e.title}', report the location shown.")
            i += 1

        # ── research centers (20 × 2 = 40) ───────────────────────────
        i = 1
        for r in ResearchCenter.query.order_by(ResearchCenter.name).limit(20).all():
            add("research_director", i,
                f"Open Ohio State research center '{r.name}' (at /research/{r.slug}) and report the director listed.")
            i += 1
            add("research_focus", i,
                f"On Ohio State research center page '{r.name}', report one of the focus areas listed.")
            i += 1

        # ── faculty profile (60 × 2 = 120) — beyond contact form ─────
        all_faculty = Faculty.query.order_by(Faculty.name).limit(60).all()
        i = 1
        for f in all_faculty:
            add("faculty_title", i,
                f"Open Ohio State faculty profile for '{f.name}' (at /faculty/{f.slug}) and report the title shown.")
            i += 1
            add("faculty_email", i,
                f"On Ohio State faculty page for '{f.name}', report the email address listed.")
            i += 1

    return tasks


def main():
    # Load existing tasks (preserve curated 0–19 if present).
    existing: list[dict] = []
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if line:
                    existing.append(json.loads(line))

    # Keep curated tasks where id does NOT start with 'Ohio State University--gui_'
    curated = [t for t in existing
               if not t.get('id', '').startswith(f'{WEB_NAME}--gui_')]

    # Build fresh deepen tasks.
    deepen = build_tasks()

    # De-duplicate by id (preserve order).
    seen = set()
    out = []
    for t in curated + deepen:
        tid = t.get('id')
        if tid in seen:
            continue
        seen.add(tid)
        out.append(t)

    with open(TASKS_FILE, 'w', encoding='utf-8') as fh:
        for t in out:
            fh.write(json.dumps(t, ensure_ascii=False) + '\n')

    print(f'curated={len(curated)} deepen={len(deepen)} total={len(out)}')


if __name__ == '__main__':
    main()
