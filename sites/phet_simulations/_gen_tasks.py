#!/usr/bin/env python3
"""Generate 1500+ GUI tasks for the deepened PhET mirror.

All tasks are natural-language questions referencing pages and content
visible only through the GUI navigation. No API endpoints; no JSON.
"""
import json
import sys
sys.path.insert(0, '.')

import app

OUT = "tasks.jsonl"
WEB = "http://localhost:40015/"
UPSTREAM = "https://phet.colorado.edu/"

records = []


def add(page_key, ques):
    nnn = sum(1 for r in records if r["page"] == page_key) + 1
    rec = {
        "web_name": "PhET Interactive Simulations",
        "id": f"PhetSimulations--gui_{page_key}_{nnn:03d}",
        "ques": ques,
        "web": WEB,
        "upstream_url": UPSTREAM,
        "page": page_key,
    }
    records.append(rec)


with app.app.app_context():
    sims = app.Simulation.query.order_by(app.Simulation.title).all()
    subjects = app.Subject.query.order_by(app.Subject.name).all()
    grades = app.GradeLevel.query.order_by(app.GradeLevel.sort_order).all()
    langs = app.Language.query.order_by(app.Language.name).all()
    plans = app.LessonPlan.query.order_by(app.LessonPlan.title).all()
    tips = app.TeacherTip.query.order_by(app.TeacherTip.title).all()
    news = app.NewsArticle.query.order_by(app.NewsArticle.published_date.desc()).all()
    papers = app.ResearchPaper.query.order_by(app.ResearchPaper.title).all()
    sponsors = app.Sponsor.query.order_by(app.Sponsor.name).all()
    workshops = app.Workshop.query.order_by(app.Workshop.held_on.desc()).all()
    members = app.TeamMember.query.order_by(app.TeamMember.name).all()
    faqs = app.FAQItem.query.all()

    # ---- home / catalogue ----
    add("home", "Open the PhET homepage and report how many simulations are in the catalogue.")
    add("home", "On the PhET homepage, list the titles of the new simulations shown in the 'New' shelf.")
    add("home", "On the PhET homepage, list the simulation titles in the 'most played' shelf.")
    add("home", "On the homepage, report the number of supported languages displayed in the stats area.")
    add("home", "On the homepage, click the brand logo and confirm you land back on the home page.")

    # ---- simulations browse ----
    for s in subjects:
        add("subject", f"Go to the Simulations category page for {s.name} and report how many simulations are listed.")
        add("subject", f"On the {s.name} category page, list the title of the first three simulations shown.")
    for g in grades:
        add("grade", f"Open the grade band hub for {g.name} and report how many simulations are listed for that grade.")
        add("grade", f"On the {g.name} grade band page, list the titles of the first three featured lesson plans.")
        add("grade", f"On the {g.name} grade band page, report the age range shown in the banner.")

    # ---- simulation detail ----
    chosen_sims = sims[:120]
    for s in chosen_sims:
        add("sim_detail", f"Open the {s.title} simulation detail page and report how many translations it has.")
        add("sim_detail", f"On the {s.title} simulation page, list the topics shown in the 'Topics' section.")
        add("sim_detail", f"On the {s.title} simulation page, report the simulation version number.")
        add("sim_detail", f"From the {s.title} simulation page, open its accessibility detail page and list the supported accessibility features.")

    # ---- search ----
    queries = [
        "gravity", "fractions", "circuits", "atoms", "energy",
        "waves", "Newton", "evolution", "tectonics", "chemistry",
        "balancing", "ph scale", "Hooke", "Faraday", "pendulum",
        "neuron", "DNA", "moon", "climate", "diffusion",
    ]
    for q in queries:
        add("search", f"Use the site search to find simulations matching '{q}' and report how many results there are.")
        add("search", f"Search for '{q}' on the PhET site and list the first three simulation titles in the results.")

    # ---- translations ----
    for l in langs[:30]:
        add("translation", f"Open the {l.name} translation hub and report how many simulations have been translated into {l.name}.")
        add("translation", f"On the translations index, find {l.name} and report its native-name spelling.")

    # ---- lesson plans ----
    for p in plans[:200]:
        add("lesson_plan", f"Open the lesson plan titled '{p.title}' and report its duration in minutes.")
        add("lesson_plan", f"On the lesson plan '{p.title}', report the grade band it targets.")
        add("lesson_plan", f"On the lesson plan page for '{p.title}', report who authored it.")
    for g in grades:
        for sub in subjects:
            add("lesson_plan_filter", f"On the Lesson Plans page, filter by grade '{g.name}' and subject '{sub.name}' and report how many plans match.")

    # ---- teacher tips ----
    for t in tips[:80]:
        add("teacher_tip", f"Open the teacher tip titled '{t.title}' and report its category.")
        add("teacher_tip", f"On the teacher tip '{t.title}' page, report how many upvotes it has.")
    cats = sorted({t.category for t in tips})
    for c in cats:
        add("teacher_tip_filter", f"On the Teacher Tips page, filter by category '{c}' and list the first three tip titles.")

    # ---- classroom mode ----
    add("classroom_mode", "Open the Classroom Mode page and list the four featured simulations available for sessions.")
    add("classroom_mode", "On the Classroom Mode page, report how many on-boarding steps are described in the feature row.")
    add("classroom_mode_setup", "From the Classroom Mode page, navigate to the new-session setup screen and report the default expected-student count.")
    add("classroom_mode_setup", "On the Classroom Mode setup page, list the three numbered steps shown.")

    # ---- accessibility ----
    add("accessibility_policy", "Open the Accessibility policy page and report the page's main heading.")
    for s in sims[:80]:
        add("accessibility_sim", f"Open the per-simulation accessibility detail for '{s.title}' and list the supported accessibility features.")

    # ---- about / team / history ----
    add("about", "Open the About page and report the total number of activities listed in the stats.")
    add("about", "On the About page, report the total number of subjects shown.")
    add("about_team", "Open the Our Team page and list the team groupings displayed (e.g., leadership, engineering).")
    add("about_history", "Open the PhET history timeline and list every milestone year shown.")
    add("about_history", "On the history timeline, find the 2002 milestone and report its title.")
    for m in members:
        add("team_member", f"Open the team member detail page for {m.name} and report their role.")

    # ---- donate / sponsors ----
    add("donate", "Open the Donate page and list the preset donation amounts shown on the form.")
    add("donate", "On the Donate page, report the four 'What your gift funds' bullet items.")
    add("sponsors", "Open the Sponsors page and report how many principal sponsors are listed.")
    add("sponsors", "On the Sponsors page, list all sponsors under the 'sustaining' tier.")
    for sp in sponsors:
        add("sponsor_detail", f"Open the sponsor detail page for '{sp.name}' and report its tier.")

    # ---- research ----
    add("research", "Open the Research publications page and report how many publications are listed in total.")
    add("research", "On the Research page, list the year filter options shown across the top.")
    for p in papers:
        add("research_paper", f"Open the research paper '{p.title}' and report the venue it was published in.")
        add("research_paper", f"On the research paper page for '{p.title}', report the citation count.")

    # ---- news ----
    add("news", "Open the News page and list the category filter pills shown at the top.")
    for n in news[:40]:
        add("news_detail", f"Open the news article '{n.title}' and report its category.")
        add("news_detail", f"On the news article '{n.title}', report the author's name.")

    # ---- workshops ----
    add("workshops", "Open the Workshops page and report how many upcoming workshops are listed.")
    add("workshops", "On the Workshops page, list the dates of all past workshops shown.")
    for w in workshops:
        add("workshop_detail", f"Open the workshop detail page for '{w.title}' and report the duration in minutes.")
        add("workshop_detail", f"On the workshop page for '{w.title}', report how many seats are left.")

    # ---- FAQ ----
    add("faq", "Open the FAQ page and list the category tabs shown.")
    cats_faq = sorted({f.category for f in faqs})
    for c in cats_faq:
        add("faq_filter", f"On the FAQ page, filter by category '{c}' and list every question shown.")

    # ---- contact / newsletter ----
    add("contact", "Open the Contact page and list the topic options shown in the topic dropdown.")
    add("contact", "On the Contact page, report the email address shown for general inquiries.")
    add("newsletter", "Open the Newsletter subscription page and list the role options shown in the role dropdown.")

    # ---- favorites / popular ----
    add("popular", "Open the Most Popular simulations page and report the title in the #1 ranking position.")
    add("popular", "On the Most Popular page, report the play-count number shown for the top-ranked simulation.")
    add("popular", "On the Most Popular page, list the available time-period filter pills.")
    add("my_favorites", "Sign in, navigate to the My Favorites page, and report how many simulations are saved.")

    # ---- report bug / inaccessibility ----
    for s in sims[:20]:
        add("report_bug", f"From the {s.title} simulation page, navigate to the bug report form and list the severity options.")
        add("report_inacc", f"From the {s.title} accessibility detail page, navigate to the inaccessibility report form and list the issue-type options.")

    # ---- topic hubs ----
    topic_hubs = ["gravity", "fractions", "energy", "circuits", "atoms",
                  "molecules", "dna", "balancing", "buoyancy", "kinematics"]
    for t in topic_hubs:
        add("topic_hub", f"Open the topic hub for '{t}' and report how many simulations are listed.")

    # ---- account ----
    add("account_register", "Open the Register page and list every required form field shown.")
    add("account_login", "Open the Sign-in page and list every form field shown.")

# Write
with open(OUT, 'w', encoding='utf-8') as f:
    for r in records:
        r_out = {k: v for k, v in r.items() if k != 'page'}
        f.write(json.dumps(r_out, ensure_ascii=False) + '\n')

print(f"Wrote {len(records)} tasks to {OUT}")

# Bucket distribution
from collections import Counter
ctr = Counter(r['page'] for r in records)
for k, v in ctr.most_common():
    print(f"  {k:25}  {v}")
