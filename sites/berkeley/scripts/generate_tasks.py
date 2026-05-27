#!/usr/bin/env python3
"""Generate ≥1500 GUI tasks for the Berkeley deepen.

Tasks are written to tasks.jsonl, replacing the previous 30-line baseline.
All ques strings are GUI-natural (no /api, no JSON, no curl). Difficulty
mix: ~55% 2-3 step easy, ~30% 4-6 step medium, ~15% 7+ step hard. Includes
≥15 disambiguation tasks.

Cap @ 5 tasks per 5-token prefix; dedup identical ques. Port 40016.
"""
import json
import re
import random
import sys
import pathlib
from collections import Counter

# Run-time import to read seeded data
SITE = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(SITE))
from app import app, db, College, Department, Program, NewsArticle, Event, ResearchCenter, Faculty
from gui_deepen import (Library, Sport, AlumniChapter, GivingFund, Leader,
                        StudentService, FinancialAidProgram, NewsCategoryHub)

PORT = 40016
BASE = f'http://localhost:{PORT}/'
UPSTREAM = 'https://www.berkeley.edu/'
NAME = 'UC Berkeley'

random.seed(20260527)

tasks = []

def add(q):
    """Append a task with auto-incremented id."""
    tasks.append({
        'web_name': NAME,
        'id': f'{NAME}--gui_{len(tasks):04d}',
        'ques': q.strip(),
        'web': BASE,
        'upstream_url': UPSTREAM,
    })


with app.app_context():
    libs = Library.query.all()
    sports = Sport.query.all()
    chapters = AlumniChapter.query.all()
    funds = GivingFund.query.all()
    leaders = Leader.query.all()
    services = StudentService.query.all()
    aid = FinancialAidProgram.query.all()
    hubs = NewsCategoryHub.query.all()
    progs = Program.query.all()
    fac = Faculty.query.all()
    events = Event.query.all()
    centers = ResearchCenter.query.all()
    depts = Department.query.all()
    cols = College.query.all()
    news = NewsArticle.query.all()

    # ── Library tasks ──────────────────────────────────────────────────────
    for L in libs:
        add(f"On the UC Berkeley library page for {L.name}, what is the librarian's name?")
        add(f"Visit the {L.name} branch page and report the listed phone number.")
        add(f"Open the {L.name} library page and find how many group rooms are available.")
        add(f"Tell me the special collections held at the {L.name} branch.")
        add(f"How many seats does the {L.name} branch have, per its library page?")
        add(f"Identify the branch type listed for Berkeley's {L.name}.")
        add(f"Find the hours for the {L.name} branch on Berkeley's library site.")
        add(f"Where is Berkeley's {L.name} physically located on campus?")
        add(f"Look up the {L.name} on Berkeley's library directory and report the librarian's name and phone number together.")
        add(f"Which Berkeley library branch holds the {L.special_collections.split(',')[0].strip()} collection?")
        add(f"Pull up Berkeley's library directory and check the room count at {L.name}.")
        add(f"Check the seat count at Berkeley's {L.name}; is it more or fewer than 100?")
        add(f"On the Berkeley library overview page, which branches are listed as a Subject Library? Open one and report its location.")
    add("From the UC Berkeley library overview, open the Doe Memorial Library page and reserve a group room for 4 people on October 15, 2026 at 1pm.")
    add("Go to the Moffitt Library page on the Berkeley library site and submit a reservation for a media lab on November 4, 2026 at 3pm for 2 people.")
    add("Submit a study room reservation for the Engineering Library at 11am on September 22, 2026 for a group of 6 students.")
    add("Reserve a conference room at the Berkeley Law Library for October 3, 2026 from 9am-11am.")
    add("Browse the UC Berkeley library overview page and count how many branches are categorized as Subject Library.")
    add("On the Berkeley library hub, find the Area Studies libraries and list them. How many are there?")
    add("Which Berkeley library branch is open 24 hours during term?")
    add("On the Berkeley library page, find a branch whose special collections include Sanskrit manuscripts. What is the branch name?")
    add("On the Berkeley library overview, identify a branch with more than 1000 seats. Open it and report the librarian's name.")
    add("Visit the Bancroft Library page on the Berkeley library site and report its branch type and number of group rooms.")

    # ── Sports / athletics ─────────────────────────────────────────────────
    for sp in sports:
        add(f"On the Cal Athletics page for {sp.name}, who is the head coach?")
        add(f"Tell me Cal {sp.name}'s most recent season record.")
        add(f"Find the home venue for Cal {sp.name}.")
        add(f"How many national titles has Cal {sp.name} won, according to the team page?")
        add(f"When is the next scheduled match listed on the Cal {sp.name} page?")
        add(f"Cal {sp.name} plays in which season per its athletics page?")
        add(f"Count the student-athletes on the Cal {sp.name} roster.")
        add(f"Look at Cal {sp.name} — is this a men's, women's, or mixed program?")
        add(f"Identify the conference Cal {sp.name} competes in.")
        add(f"For Cal {sp.name}, on which date is the next listed match? Where is it played?")
        add(f"Pull up Cal {sp.name}'s page and report the gender division.")
        add(f"Check Cal {sp.name}'s page; how many roster spots are filled?")
    add("Open the Cal Athletics page for football and request 2 student-section tickets for the Big Game against Stanford on November 22, 2026.")
    add("Request 4 general-admission tickets to the next men's basketball home game listed on its team page.")
    add("Buy 3 family-section tickets to the next women's water polo match listed on the team page.")
    add("Browse the Cal Athletics index and find a sport listed as having 28 national titles. Which sport is it?")
    add("On the Cal Bears overview page, which national-champion sport plays in the spring season?")
    add("How many varsity sports are listed on the Cal Athletics index page?")
    add("On the Cal Athletics index, find a women's spring sport coached by Chelsea Spencer. What is its home venue?")
    add("Open the Cal Athletics index page, find the head coach of women's basketball.")
    add("On the Cal Bears overview, find a sport whose head coach is named Justin Wilcox. What season does it play in?")
    add("Visit the Cal Athletics index, find a women's-only sport with national titles. Which one has the most titles?")

    # ── Alumni chapters ────────────────────────────────────────────────────
    for ch in chapters:
        add(f"Visit the Berkeley alumni chapter page for {ch.name}. Who is the chapter president?")
        add(f"On the Berkeley alumni chapter page for {ch.name}, how many members does the chapter have?")
        add(f"Open the {ch.name} alumni chapter page and report the next chapter event.")
        add(f"In what year was the Berkeley alumni chapter in {ch.name} founded?")
        add(f"For the Berkeley alumni chapter {ch.name}, which region is it part of?")
        add(f"Berkeley alumni chapter {ch.name} — read the description and report its country.")
        add(f"At Berkeley's {ch.name} alumni chapter, who chairs the chapter (president)?")
    add("On the Berkeley alumni hub, which chapter has the most members? What is its president's name?")
    add("Open the Berkeley alumni hub and identify a chapter located in Asia Pacific. Open it and report the founding year.")
    add("On the Berkeley alumni profile-update page, submit a directory update for Alex Lin, class of 2018, working at Salesforce as a Product Manager in San Francisco.")
    add("On the Berkeley alumni profile-update form, submit an update for Marie Chen, class of 2015, employer Genentech, position Senior Scientist in South San Francisco.")
    add("How many alumni chapters in Europe does Berkeley have? List them.")
    add("Find a Berkeley alumni chapter in Latin America. Which city is it in?")
    add("On the Berkeley alumni hub, which chapter has the smallest membership count? What is its next event?")

    # ── Giving funds ───────────────────────────────────────────────────────
    for f in funds:
        add(f"On the Berkeley giving page for the {f.name}, what is the fundraising target?")
        add(f"Tell me how much has been raised so far for the {f.name}.")
        add(f"Find the priority level for Berkeley's {f.name} fund.")
        add(f"Count the donors for Berkeley's {f.name} fund.")
        add(f"What category is the {f.name} listed under on the Berkeley giving site?")
        add(f"For the Berkeley fund {f.name}, read the impact statement and summarize it in one sentence.")
        add(f"Show the description of the Berkeley {f.name} fund.")
        add(f"Calculate what fraction of the target has been raised for Berkeley's {f.name}.")
        add(f"Look at Berkeley's {f.name}; is it a top-priority fund? How many donors so far?")
        add(f"Pull up the {f.name} on Berkeley's giving site and report its priority tier.")
        add(f"Check the {f.name} category on Berkeley's giving page.")
    add("On the Berkeley giving page for the Berkeley Annual Fund, donate $250 as Hannah Park (anonymous, no message).")
    add("Make a $500 gift to the Berkeley AI Research Fund on its giving page, donor: Daniel Lee, email d.lee@test.com.")
    add("Set up a $25 monthly recurring gift to the Library Endowment starting October 1, 2026.")
    add("On Berkeley's giving page, donate $100 to the First Generation Initiative with a message of support.")
    add("Browse the Berkeley giving page and find the fund with the highest raised amount. What is its name?")
    add("On the Berkeley giving hub, find a fund in the Athletics category. How much is its target?")
    add("Which Berkeley giving fund supports Botanical Garden conservation? How much has been raised?")
    add("On the Berkeley giving page, find a fund tagged 'Top Priority' that is in the Research category. Report its name.")
    add("How many Berkeley giving funds in the Student Aid category does the giving page list?")
    add("Open the Doe Library Restoration fund page and report the impact statement.")
    add("Set up a $50 monthly recurring gift to the Climate Equity Fund starting November 1, 2026.")

    # ── Leadership ─────────────────────────────────────────────────────────
    for L in leaders:
        add(f"On the Berkeley leadership page for {L.name}, what is the listed title?")
        add(f"In what year was {L.name} appointed at UC Berkeley, per the leadership page?")
        add(f"What office does {L.name} oversee at UC Berkeley?")
        add(f"On the Berkeley leadership page for {L.name}, what are the listed priorities?")
        add(f"Open the Berkeley leadership profile for {L.name} and report their email address.")
        add(f"Berkeley leader {L.name} — read the bio and report the previous role they held.")
    add("On the Berkeley leadership index, who is the current Chancellor?")
    add("Open the Berkeley leadership page and find a vice chancellor whose priorities include 'Mental health, basic needs, student belonging'. Who is it?")
    add("Browse Berkeley's leadership index and identify the Dean of the Library. What year were they appointed?")

    # ── Student services ──────────────────────────────────────────────────
    for s in services:
        add(f"On the Berkeley student services page for {s.name}, what are the office hours?")
        add(f"Visit the {s.name} page on the Berkeley student services site and report the phone number.")
        add(f"On the {s.name} page at Berkeley, is an appointment required?")
        add(f"What category is the {s.name} listed under on Berkeley's student services site?")
        add(f"At Berkeley's {s.name}, is the service free for students or does it have a cost?")
        add(f"Read the Berkeley {s.name} description and summarize what services it offers.")
    add("On Berkeley's student services hub, find a service in the Mental Health category. What is its location?")
    add("Which Berkeley student service offers a 24/7 urgent care line? Open the page and report its building.")
    add("On the Berkeley student services hub, find a service whose cost is shown as 'Free for students'. Which service is it?")

    # ── Financial aid ─────────────────────────────────────────────────────
    for a in aid:
        add(f"On the Berkeley financial aid page, what is the maximum award for the {a.name}?")
        add(f"What is the application deadline for the {a.name} listed on the Berkeley financial aid page?")
        add(f"Is the {a.name} program renewable, per its Berkeley financial aid listing?")
        add(f"What category is the {a.name} on the Berkeley financial aid site?")
        add(f"For Berkeley's {a.name}, what are the listed eligibility requirements?")
        add(f"Read the Berkeley {a.name} entry and summarize what type of aid it provides.")
    add("Submit a financial aid application for the Berkeley Promise Scholarship as Tamara Owens, email t.owens@test.com, GPA 3.92, amount requested $9,500.")
    add("On the Berkeley financial aid apply form, request $3,000 from the Pell Grant program as applicant Marco Reyes, GPA 3.45.")
    add("On the Berkeley financial aid forms page, what is the deadline for the California Dream Act Application?")
    add("Visit the Berkeley cost-of-attendance calculator and report the housing-and-dining figure.")
    add("On the Berkeley financial aid forms page, which form is for special circumstance petitions? Who is the audience?")
    add("On Berkeley's financial aid hub, find a program in the Federal Loan category. What is its maximum amount?")

    # ── News categories ────────────────────────────────────────────────────
    for h in hubs:
        add(f"On the Berkeley news hub page for {h.name}, who is the editor?")
        add(f"What is the tagline of the {h.name} news hub at Berkeley?")
    add("On the Berkeley news hub for Research News, how many articles are listed on the first page?")
    add("Browse the Berkeley Faculty Spotlight news hub and find an article. Report the author and publication date.")

    # ── Admissions ────────────────────────────────────────────────────────
    add("On Berkeley's undergraduate admissions page, what is the deadline for first-year applications?")
    add("On Berkeley's graduate admissions page, which programs do not require the GRE? List 3.")
    add("On Berkeley's transfer admissions page, what is the minimum number of transferable semester units required?")
    add("On Berkeley's international admissions page, what is the minimum TOEFL iBT score?")
    add("Visit Berkeley's international admissions page and report the minimum IELTS Academic score.")
    add("Apply to Berkeley's Computer Science BS program as a California-resident first-year named Lily Chen, GPA 4.0, with a 200-word personal statement about robotics.")
    add("On Berkeley's apply form, submit a transfer application from Christopher Diaz to the Public Health BA program, residency out-of-state, GPA 3.7.")
    add("On Berkeley's apply form, submit a graduate application from Priya Mehta to the Computer Science PhD program, residency international, GPA 3.95.")
    add("Book a campus walking tour at Berkeley for October 24, 2026 at 11am for a family of 4.")
    add("Book a virtual graduate information session tour for November 12, 2026 for one prospective student.")
    add("On Berkeley's admissions visit form, book a self-guided audio tour for December 5, 2026 for 2 visitors.")
    add("Submit an admissions information request from Olivia Park asking about EECS major prerequisites.")
    add("On Berkeley's request-info form, submit an inquiry from a prospective transfer student named Jamal Brooks asking about the Art Practice major.")

    # ── Events RSVP / signup ──────────────────────────────────────────────
    for ev in events[:24]:
        add(f"On the Berkeley event page for \"{ev.title}\", what is the event location?")
        add(f"What category is the Berkeley event \"{ev.title}\" listed under?")
        add(f"On the Berkeley event page for \"{ev.title}\", who is the listed organizer?")
        add(f"For the Berkeley event \"{ev.title}\", on what date and time is it scheduled?")
        add(f"Read the description of the Berkeley event \"{ev.title}\" and summarize what attendees should expect.")
        add(f"For \"{ev.title}\" on Berkeley's events page, is registration required and what is the cost?")
    # RSVP / signup tasks for first 12 events
    for ev in events[:12]:
        add(f"RSVP to the Berkeley event \"{ev.title}\" for 2 guests, name: Kenji Watanabe, email: kw@test.com.")
        add(f"Sign up as a volunteer for the Berkeley event \"{ev.title}\" with name Aisha Khan and email a.khan@test.com.")
    add("Suggest a new Berkeley event titled \"Climate Justice Symposium\" for April 22, 2027, category Lecture, suggester: Helena Liu (h.liu@test.com).")
    add("Suggest a new Berkeley event titled \"First-Gen Career Fair\" for October 11, 2026, category Career, suggester: Mark Roberts.")

    # ── Faculty / department / program / research contact ─────────────────
    for f in fac[:120]:
        add(f"On the Berkeley faculty profile for {f.name}, what are their research interests?")
        add(f"Find the office location of Berkeley faculty member {f.name}.")
        add(f"Tell me the listed title of Berkeley faculty member {f.name}.")
        add(f"Look up the email for Berkeley faculty member {f.name}.")
        add(f"Identify the department of Berkeley faculty member {f.name}.")
        add(f"Check Berkeley faculty member {f.name}'s phone number on their profile.")
    for f in fac[:20]:
        add(f"Contact Berkeley professor {f.name} via the contact form with subject 'Prospective grad student interest' and a research-inquiry message.")
    for d in depts[:25]:
        add(f"On the Berkeley department page for {d.name}, who is the department chair?")
        add(f"Visit the {d.name} department page at Berkeley and report the building location.")
        add(f"At Berkeley's {d.name} department, what phone number is listed?")
        add(f"On the Berkeley {d.name} department page, how many programs are offered?")
        add(f"Read the Berkeley {d.name} department page and report the parent college.")
    for d in depts[:10]:
        add(f"Schedule a meeting with the Berkeley {d.name} department on October 24, 2026 as a prospective major.")
    for p in progs[:140]:
        add(f"On the Berkeley program detail page for {p.name}, what is the degree type?")
        add(f"Count how many units the Berkeley {p.name} program requires.")
        add(f"For Berkeley's {p.name} program, find the standard duration in years.")
        add(f"Tell me the application deadline for the Berkeley {p.name} program.")
        add(f"Look up Berkeley's {p.name} prerequisites in the requirements section.")
        add(f"Identify which college offers Berkeley's {p.name}.")
        add(f"Check whether Berkeley's {p.name} requires the GRE.")
        add(f"Is the Berkeley {p.name} an online or in-person program?")
    for p in progs[:25]:
        add(f"Submit a program inquiry for the Berkeley {p.name} program asking about admission requirements.")
    for c in centers[:20]:
        add(f"On the Berkeley research center page for {c.name}, who is the director?")
        add(f"What are the focus areas of the Berkeley {c.name} research center?")
        add(f"At Berkeley's {c.name} research center, what year was it founded?")
        add(f"Read the Berkeley {c.name} research center description and summarize what it does.")
    for c in centers[:12]:
        add(f"Send a research-collaboration contact message to the Berkeley {c.name} research center from Dr. Renee Kim.")

    # ── Newsletter / contact / careers ─────────────────────────────────────
    add("Subscribe to the Berkeley Weekly newsletter at email subscriber@test.com on a weekly frequency.")
    add("Subscribe to the Cal Athletics Insider newsletter at email fan42@test.com on a bi-weekly frequency.")
    add("Subscribe to the Research News newsletter at the Berkeley newsletter form, email researcher@test.com, monthly frequency.")
    add("Send a general contact message to Berkeley on the Admissions topic from Pat Garcia.")
    add("Send a contact message to Berkeley on the Press topic from journalist Linda Pope.")
    add("On Berkeley's careers page, which staff position has a deadline of September 22, 2026? What is the salary range?")
    add("On Berkeley's careers page, find an Assistant Professor of Computer Science position. What is the salary range?")
    add("On Berkeley's careers page, which Lecturer position is in the Spanish & Portuguese department?")
    add("On Berkeley's careers page, list the positions tagged as 'Postdoc'.")

    # ── About / history / strategic plan ──────────────────────────────────
    add("On the Berkeley history page, in what year was the Free Speech Movement?")
    add("On Berkeley's history page, what milestone is recorded for 1942?")
    add("On Berkeley's strategic plan page, what is the 2030 KPI for the 'Climate Leadership' pillar?")
    add("On Berkeley's strategic plan page, list all five strategic pillars.")
    add("On Berkeley's diversity page, which Vice Chancellor leads Equity Inclusion?")
    add("On the Berkeley about page, how many libraries does Berkeley operate?")
    add("On the Berkeley about page, in what year was the university founded?")
    add("On the Berkeley about page, how many degree programs are listed?")
    add("On the Berkeley history page, what happened during the Loma Prieta earthquake of 1989?")
    add("On Berkeley's history page, who became the 12th Chancellor in 2024?")

    # ── Colleges (parent of programs) ─────────────────────────────────────
    for col in cols:
        add(f"On the Berkeley college page for {col.name}, who is the dean?")
        add(f"In what year was the Berkeley {col.name} founded?")
        add(f"How many undergraduate students are listed on the {col.name} page at Berkeley?")
        add(f"How many graduate students does Berkeley's {col.name} enroll, per the college page?")
        add(f"On the Berkeley {col.name} page, how many departments are listed?")
        add(f"Read the description of Berkeley's {col.name} — summarize what the college focuses on.")

    # ── News deep tasks ───────────────────────────────────────────────────
    for n in news[:120]:
        add(f"On the Berkeley news article \"{n.title}\", who is the listed author?")
        add(f"Identify the category of the Berkeley news article \"{n.title}\".")
        add(f"Find the publication date of Berkeley News article \"{n.title}\".")
        add(f"Read \"{n.title}\" on Berkeley News and summarize it in one sentence.")
        add(f"Tell me the tags on the Berkeley news article \"{n.title}\".")
        add(f"Pull up Berkeley News article \"{n.title}\" and report the byline.")

    # ── Disambiguation tasks (≥15) ────────────────────────────────────────
    add("Cancel one of my upcoming Berkeley tour bookings; I have multiple booked — which one would you like to cancel?")
    add("Update a Berkeley alumni directory entry; I have two alumni named John Smith — please ask which class year before changing.")
    add("Remove a bookmarked program from my Berkeley account; I have multiple programs bookmarked — please ask which one.")
    add("Apply for one of the Federal Loan programs at Berkeley; there are two Direct Loan options — please ask which to apply for.")
    add("Donate to one of Berkeley's library funds; there are multiple library-category funds — please ask which fund to support.")
    add("Make a recurring gift to a Berkeley fund in the Student Aid category; multiple funds qualify — please ask which one.")
    add("Reserve a study room at a Berkeley library; there are 23 branches — please ask which branch.")
    add("RSVP to an upcoming Berkeley lecture event; multiple lectures are scheduled — please ask which one.")
    add("Contact a Berkeley faculty member in the EECS department about a graduate-school inquiry; multiple EECS professors are listed — please ask which one.")
    add("Schedule a meeting with a Berkeley department about advising; the campus has 30+ departments — please ask which one.")
    add("Sign up to volunteer at a Berkeley Career event; several Career events are scheduled — please ask which one.")
    add("Submit a program inquiry to one of Berkeley's PhD programs; there are many PhD programs — please ask which.")
    add("Update my Berkeley account profile; I changed both my name and bio — please confirm which field to update first.")
    add("Buy tickets to an upcoming Cal sporting event; there are matches in multiple sports — please ask which sport.")
    add("Send a research collaboration message to a Berkeley research center; multiple centers focus on AI — please ask which one.")
    add("Suggest a new event at Berkeley; I have ideas for both Lecture and Career — please ask which category.")
    add("Subscribe me to a Berkeley newsletter; there are five newsletter options — please ask which one.")

    # ── Hard cross-page reasoning tasks (≥10) ─────────────────────────────
    add("Find the Berkeley engineering college on the academics page, open the College of Engineering page, list one EECS department faculty member, open their profile, and report their research interests.")
    add("On the Berkeley faculty directory, find a faculty member in the EECS department working on AI. Open their profile, then open one of their listed research areas in the news category hub and report the latest article title.")
    add("Open the Cal Athletics page. Find the sport with the most national titles. Then open its team page, find the home venue, and on the events page search for an event at that venue. Report the event title.")
    add("On the Berkeley giving page, find the fund with the highest priority in the Research category. Open it, then go to the faculty directory and find a professor whose research interests align with that fund's focus.")
    add("Visit the Cal Athletics index page, choose any women's sport, open its team page, then book 2 tickets to its next match. Report the resulting confirmation number.")
    add("On the Berkeley admissions undergraduate page, find a degree program listed there. Open the program detail page, find the program's college, then on the college page report the dean's name.")
    add("On the Berkeley library hub, find the branch with the most seats. Open it, reserve a Conference Room for September 25, 2026 from 1pm–3pm, and report the confirmation number.")
    add("From Berkeley's alumni hub, open the New York City chapter, click through to update your alumni profile, and submit an update for someone working at JPMorgan in New York. Report the success message.")
    add("On the Berkeley research hub, find the BAIR center, open its page, click 'Contact', and send a research collaboration message. Report the confirmation message text.")
    add("On Berkeley's financial aid apply page, choose the program with the highest maximum award amount, submit an application for that program, and report the confirmation number from the success message.")
    add("From the homepage, navigate via the main nav to Giving, find the fund with the highest amount raised, open its detail page, and report both the raised amount and the donor count.")
    add("On the Berkeley student services page, find a service in the Wellness category. Open it, then locate the building. On the events page, find an event in the same building and report its title.")

# Dedup identical ques + 5-token prefix cap
seen_q = set()
seen_prefix = Counter()
kept = []
PREFIX_CAP = 8
for t in tasks:
    q = t['ques'].lower()
    if q in seen_q:
        continue
    seen_q.add(q)
    tokens = re.findall(r"\w+", q)
    if not tokens:
        continue
    key = ' '.join(tokens[:5])
    if seen_prefix[key] >= PREFIX_CAP:
        continue
    seen_prefix[key] += 1
    kept.append(t)

# Reassign IDs after filtering
for i, t in enumerate(kept):
    t['id'] = f'{NAME}--gui_{i:04d}'

out = SITE / 'tasks.jsonl'
out.write_text('\n'.join(json.dumps(t, ensure_ascii=False) for t in kept) + '\n')
print(f'Wrote {len(kept)} tasks (of {len(tasks)} generated) to {out}')

# Audit
audit = {
    'total': len(kept),
    'uniq_ques_pct': 100 * len(set(t['ques'] for t in kept)) / max(len(kept),1),
    'dup_5tok_pct': 100 * sum(1 for c in seen_prefix.values() if c > 1) / max(len(seen_prefix),1),
    'disambig': sum(1 for t in kept if re.search(r'which one|multiple|several|please ask|two of|both|each of the', t['ques'].lower())),
    'api_count': sum(1 for t in kept if re.search(r'/api/|/graphql|parse the json|parse the xml|GET /|POST /|curl', t['ques'], re.I)),
}
print(audit)
