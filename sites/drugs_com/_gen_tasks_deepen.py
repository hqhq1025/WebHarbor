#!/usr/bin/env python3
"""Generate ~1500 GUI tasks for drugs_com deepening.

Tasks are emitted with ids of the form `Drugs--gui_<page>_<NNN>` so they
can be quickly filtered by surface. Source data is read straight from
instance_seed/drugs_com.db so tasks are always answerable against the
shipped DB.

Question text is short, action-oriented, and asks for a single 1-5 token
answer (token cap @ 5) per the design-tasks skill.
"""
from __future__ import annotations
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "instance_seed", "drugs_com.db")
WEB = "http://localhost:40015/"
UPSTREAM = "https://www.drugs.com/"
NAME = "Drugs.com"


def emit(tasks, ques, page, idx):
    tid = f"Drugs--gui_{page}_{idx:04d}"
    tasks.append({
        "web_name": NAME,
        "id": tid,
        "ques": ques,
        "web": WEB,
        "upstream_url": UPSTREAM,
    })


def main():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    drugs = c.execute(
        "SELECT slug, generic_name, availability, csa_schedule, pregnancy_risk, "
        "brand_names_json, drug_class_id, avg_rating, review_count "
        "FROM drug ORDER BY id"
    ).fetchall()
    classes = {row[0]: row[1] for row in c.execute(
        "SELECT id, name FROM drug_class ORDER BY id"
    ).fetchall()}
    conditions = c.execute(
        "SELECT slug, name FROM condition ORDER BY name LIMIT 200"
    ).fetchall()
    interactions = c.execute(
        "SELECT a.slug, b.slug, di.severity "
        "FROM drug_interaction di "
        "JOIN drug a ON di.drug_a_id = a.id "
        "JOIN drug b ON di.drug_b_id = b.id "
        "ORDER BY di.id LIMIT 200"
    ).fetchall()
    glossary = c.execute(
        "SELECT slug, term FROM glossary_term ORDER BY slug"
    ).fetchall()
    forum_cats = c.execute(
        "SELECT slug, name FROM forum_category ORDER BY id"
    ).fetchall()
    forum_topics = c.execute(
        "SELECT id, slug, title, category_id FROM forum_topic ORDER BY id"
    ).fetchall()
    forum_cat_by_id = {row[0]: row[1] for row in c.execute(
        "SELECT id, slug FROM forum_category"
    ).fetchall()}
    recalls = c.execute(
        "SELECT slug, drug_name, severity, lot_number FROM drug_recall ORDER BY id"
    ).fetchall()
    pharmacies = c.execute(
        "SELECT slug, name, chain, city, state FROM pharmacy ORDER BY id"
    ).fetchall()
    news = c.execute(
        "SELECT slug, title, category FROM health_news ORDER BY id"
    ).fetchall()
    drug_class_rows = c.execute(
        "SELECT slug, name FROM drug_class ORDER BY id"
    ).fetchall()
    pill_imprints = c.execute(
        "SELECT DISTINCT imprint, shape, color FROM drug_image "
        "WHERE imprint IS NOT NULL AND imprint != '' ORDER BY imprint LIMIT 60"
    ).fetchall()
    side_effect_reports = c.execute(
        "SELECT d.slug, ser.severity FROM side_effect_report ser "
        "JOIN drug d ON ser.drug_id = d.id ORDER BY ser.id"
    ).fetchall()
    refill_drugs = c.execute(
        "SELECT d.slug, rr.frequency FROM refill_reminder rr "
        "JOIN drug d ON rr.drug_id = d.id ORDER BY rr.id"
    ).fetchall()

    conn.close()

    tasks = []

    # --------------------------------------------------------------
    # 1. Drug detail — drug class (1050 → cap at 300)
    # --------------------------------------------------------------
    idx = 0
    for slug, gname, avail, csa, preg, brands_j, cls_id, rating, rc in drugs[:300]:
        cls = classes.get(cls_id)
        if not cls:
            continue
        ques = (
            f"Open the drug detail page for {gname} (/{slug}) on Drugs.com "
            f"and report the drug class shown on the page."
        )
        emit(tasks, ques, "drug_class", idx)
        idx += 1

    # --------------------------------------------------------------
    # 2. Drug detail — availability (Rx/OTC) (cap 150)
    # --------------------------------------------------------------
    idx = 0
    for slug, gname, avail, csa, preg, *_ in drugs[:150]:
        ques = (
            f"On the {gname} drug detail page (/{slug}), is the medication "
            f"available as Rx, OTC, or both? Report exactly the availability text."
        )
        emit(tasks, ques, "drug_availability", idx)
        idx += 1

    # --------------------------------------------------------------
    # 3. Drug detail — CSA schedule (controlled substances) cap 80
    # --------------------------------------------------------------
    idx = 0
    for slug, gname, avail, csa, *_ in drugs[:160]:
        if not csa or csa == "Not a controlled drug":
            # Still 80 controlled questions for variety
            if idx >= 80:
                continue
        ques = (
            f"Open /{slug} on Drugs.com and report the CSA schedule listed "
            f"for {gname}."
        )
        emit(tasks, ques, "drug_csa", idx)
        idx += 1
        if idx >= 80:
            break

    # --------------------------------------------------------------
    # 4. Drug pregnancy page (cap 80)
    # --------------------------------------------------------------
    idx = 0
    for slug, gname, *_ in drugs[:80]:
        ques = (
            f"Open the pregnancy safety page for {gname} (/pregnancy/{slug}) "
            f"and report the pregnancy category or risk shown."
        )
        emit(tasks, ques, "drug_pregnancy", idx)
        idx += 1

    # --------------------------------------------------------------
    # 5. Drug breastfeeding page (cap 60)
    # --------------------------------------------------------------
    idx = 0
    for slug, gname, *_ in drugs[:60]:
        ques = (
            f"Open /breastfeeding/{slug} on Drugs.com and report the lactation "
            f"category shown for {gname}."
        )
        emit(tasks, ques, "drug_breastfeeding", idx)
        idx += 1

    # --------------------------------------------------------------
    # 6. Drug dosage / side-effects / interactions / warnings pages (cap 100 each)
    # --------------------------------------------------------------
    for page_key, page_path, q_suffix in [
        ("drug_dosage", "/<slug>/dosage", "report the typical adult dose listed on the dosage page"),
        ("drug_sfx", "/<slug>/side-effects", "report a common side effect listed for adults"),
        ("drug_interactions_page", "/<slug>/interactions", "report how many major interactions are listed"),
        ("drug_warnings", "/<slug>/warnings", "report whether a boxed warning is present"),
    ]:
        idx = 0
        for slug, gname, *_ in drugs[:100]:
            ques = (
                f"Open {page_path.replace('<slug>', slug)} on Drugs.com and "
                f"{q_suffix} for {gname}."
            )
            emit(tasks, ques, page_key, idx)
            idx += 1

    # --------------------------------------------------------------
    # 7. Drug interaction checker (cap 100)
    # --------------------------------------------------------------
    idx = 0
    for a_slug, b_slug, sev in interactions[:100]:
        ques = (
            f"Use the Drug Interaction Checker at /drug-interactions to check "
            f"the interaction between {a_slug} and {b_slug}. Report the severity level."
        )
        emit(tasks, ques, "interactions", idx)
        idx += 1

    # --------------------------------------------------------------
    # 8. Condition detail (cap 120)
    # --------------------------------------------------------------
    idx = 0
    for slug, name in conditions[:120]:
        ques = (
            f"Open the condition page /condition/{slug} on Drugs.com and "
            f"report how many treatment drugs are listed for {name}."
        )
        emit(tasks, ques, "condition", idx)
        idx += 1

    # --------------------------------------------------------------
    # 9. Condition drugs (cap 80)
    # --------------------------------------------------------------
    idx = 0
    for slug, name in conditions[:80]:
        ques = (
            f"Open /condition/{slug}/drugs and report the top-rated drug listed "
            f"for {name}."
        )
        emit(tasks, ques, "condition_drugs", idx)
        idx += 1

    # --------------------------------------------------------------
    # 10. Drug class browse (cap 60)
    # --------------------------------------------------------------
    idx = 0
    for slug, name in drug_class_rows[:60]:
        ques = (
            f"Open /drug-classes/{slug} and report how many drugs are listed "
            f"in the {name} class."
        )
        emit(tasks, ques, "drug_class_browse", idx)
        idx += 1

    # --------------------------------------------------------------
    # 11. Glossary (cap 60)
    # --------------------------------------------------------------
    idx = 0
    for slug, term in glossary[:60]:
        ques = (
            f"Open /glossary/{slug} on Drugs.com and report the first-sentence "
            f"definition of '{term}'."
        )
        emit(tasks, ques, "glossary", idx)
        idx += 1

    # --------------------------------------------------------------
    # 12. Forum browse — category (cap 30)
    # --------------------------------------------------------------
    idx = 0
    for slug, name in forum_cats:
        ques = (
            f"Open /forum/category/{slug} and report how many topics are listed "
            f"in the '{name}' forum category."
        )
        emit(tasks, ques, "forum_category", idx)
        idx += 1

    # --------------------------------------------------------------
    # 13. Forum topic detail (cap 50)
    # --------------------------------------------------------------
    idx = 0
    for tid, slug, title, cat_id in forum_topics[:50]:
        ques = (
            f"Open /forum/topic/{tid} on Drugs.com and report how many replies "
            f"the topic '{title[:60]}' has."
        )
        emit(tasks, ques, "forum_topic", idx)
        idx += 1

    # --------------------------------------------------------------
    # 14. Recalls (cap 25)
    # --------------------------------------------------------------
    idx = 0
    for slug, name, sev, lot in recalls:
        ques = (
            f"Open /recalls/{slug} on Drugs.com and report the recall severity "
            f"class for {name}."
        )
        emit(tasks, ques, "recall", idx)
        idx += 1

    # --------------------------------------------------------------
    # 15. Pharmacies (cap 20)
    # --------------------------------------------------------------
    idx = 0
    for slug, name, chain, city, state in pharmacies:
        ques = (
            f"Open /pharmacy/{slug} and report the city where {name} is located."
        )
        emit(tasks, ques, "pharmacy", idx)
        idx += 1

    # --------------------------------------------------------------
    # 16. Health news (cap 30)
    # --------------------------------------------------------------
    idx = 0
    for slug, title, cat in news:
        ques = (
            f"Open /health-news/{slug} on Drugs.com and report the category "
            f"of the article '{title[:60]}'."
        )
        emit(tasks, ques, "health_news", idx)
        idx += 1

    # --------------------------------------------------------------
    # 17. Pill identifier wizard (cap 30)
    # --------------------------------------------------------------
    idx = 0
    for imprint, shape, color in pill_imprints[:30]:
        ques = (
            f"Use the pill identifier wizard at /pill-identifier/wizard. "
            f"Enter imprint '{imprint}', then pick shape '{shape}' and color "
            f"'{color}'. Report how many matching drug names are shown."
        )
        emit(tasks, ques, "pill_wizard", idx)
        idx += 1

    # --------------------------------------------------------------
    # 18. Side effect reports (community, cap 15)
    # --------------------------------------------------------------
    idx = 0
    for slug, sev in side_effect_reports:
        ques = (
            f"Open /side-effects/reports and find a community report for "
            f"{slug}. Report its severity."
        )
        emit(tasks, ques, "side_effect_report", idx)
        idx += 1

    # --------------------------------------------------------------
    # 19. Drug comparison head-to-head (cap 60)
    # --------------------------------------------------------------
    pairs = [(drugs[i][0], drugs[i+1][0]) for i in range(0, 120, 2)]
    idx = 0
    for a, b in pairs[:60]:
        ques = (
            f"Open /comparison/{a}-vs-{b} on Drugs.com and report which of "
            f"the two has the higher average user rating."
        )
        emit(tasks, ques, "comparison", idx)
        idx += 1

    # --------------------------------------------------------------
    # 20. Search (cap 60) — search drug names
    # --------------------------------------------------------------
    idx = 0
    for slug, gname, *_ in drugs[:60]:
        ques = (
            f"Use the search bar to search for '{gname}'. Click the top result "
            f"and report its drug class."
        )
        emit(tasks, ques, "search", idx)
        idx += 1

    # --------------------------------------------------------------
    # 21. Dosage calculator (cap 12)
    # --------------------------------------------------------------
    idx = 0
    for slug in ["acetaminophen", "ibuprofen", "amoxicillin", "warfarin",
                 "levothyroxine", "metformin", "atorvastatin", "lisinopril",
                 "sertraline", "gabapentin", "prednisone", "azithromycin"]:
        ques = (
            f"Open /dosage-calculator/{slug}, enter weight 70 kg and age 35, "
            f"and report the suggested mg per dose."
        )
        emit(tasks, ques, "dosage_calc", idx)
        idx += 1

    # --------------------------------------------------------------
    # 22. Drug FAQ / reviews / monograph / images aliases (cap 50 each)
    # --------------------------------------------------------------
    for page_key, page_path, q_suffix in [
        ("drug_faq", "/<slug>/faq", "report the number of FAQ entries shown"),
        ("drug_reviews", "/<slug>/reviews", "report the highest user rating shown"),
        ("drug_monograph", "/<slug>/monograph", "report the heading of the first section"),
        ("drug_images", "/<slug>/images", "report how many pill images are listed"),
    ]:
        idx = 0
        for slug, gname, *_ in drugs[:50]:
            ques = (
                f"Open {page_path.replace('<slug>', slug)} on Drugs.com and "
                f"{q_suffix} for {gname}."
            )
            emit(tasks, ques, page_key, idx)
            idx += 1

    # --------------------------------------------------------------
    # 23. Drug price guide (cap 50)
    # --------------------------------------------------------------
    idx = 0
    for slug, gname, *_ in drugs[:50]:
        ques = (
            f"Open the price guide /{slug}/price-guide on Drugs.com and "
            f"report the lowest listed cash price for a 30-day supply of {gname}."
        )
        emit(tasks, ques, "drug_prices", idx)
        idx += 1

    # --------------------------------------------------------------
    # 24. Auth flows (myaccount, refill reminders, my-med-list, my-reviews) cap 5 each
    # --------------------------------------------------------------
    auth_tasks = [
        ("auth_myacct", "Sign in as alice_j (TestPass123!) and open /myaccount. Report how many refill reminders are listed."),
        ("auth_myacct", "Open /myaccount/medications as alice_j and report how many saved medications she has."),
        ("auth_myacct", "Open /myaccount/refill-reminders as alice_j and report the drug name with the earliest upcoming refill date."),
        ("auth_myacct", "Open /myaccount/refill-reminders/new and add a reminder for atorvastatin with daily frequency and 30-day supply. Report the success flash message."),
        ("auth_myacct", "Open /myaccount/refill-reminders as alice_j, click delete on one reminder, confirm, and report the success flash message."),
        ("auth_med_list", "Open the ibuprofen drug page and click 'Save medication'. Report the success flash message."),
        ("auth_med_list", "On /myaccount/medications, remove one medication and report the success flash message."),
        ("auth_med_list", "On the metformin drug detail page click 'Save medication', then open /myaccount/medications and report the new total saved count."),
        ("auth_review", "Open /ibuprofen/reviews/new, submit a 9/10 review titled 'works great', and report the success flash message."),
        ("auth_review", "Open /account/reviews and report how many reviews alice_j has authored."),
        ("auth_forum", "Open /forum/new and post a topic in the 'side-effects' category titled 'Test post' with any body. Report the slug of the new topic from the redirect URL."),
        ("auth_forum", "Open /forum/topic/1 and add a reply 'Thanks for sharing'. Report the success flash message."),
        ("auth_forum", "Open /forum/post/1/helpful (POST) and report the updated helpful count for post 1."),
        ("auth_contact", "Open /contact-pharmacist, choose topic 'dosing', enter a question, submit, and report the success flash message."),
        ("auth_report", "Open /report-side-effect, select 'metformin', severity 'mild', describe an effect, submit, and report the success page heading."),
        ("auth_subscribe", "Open /recalls and submit your email to subscribe to recall alerts. Report the success flash message."),
        ("auth_dosage", "Open /dosage-calculator/ibuprofen, enter weight 60 and age 30, click Save to profile. Report the mg per dose result."),
        ("auth_comparison", "Open /comparison/ibuprofen-vs-naproxen, add the note 'discussed', click Save comparison, and report the success flash."),
    ]
    for i, (page_key, ques) in enumerate(auth_tasks):
        emit(tasks, ques, page_key, i)

    # --------------------------------------------------------------
    # 25. Top-level navigation / static pages (cap 25)
    # --------------------------------------------------------------
    nav_tasks = [
        ("nav", "Open the Drugs.com homepage and report the section header text above the featured drugs."),
        ("nav", "Open the Drugs A-Z page and report how many letters of the alphabet are shown in the navigation strip."),
        ("nav", "Open /drug-classes and report how many drug classes are shown on the first page."),
        ("nav", "Open /conditions and report how many conditions are listed under 'D'."),
        ("nav", "Open /pill-identifier and report the placeholder text in the imprint input."),
        ("nav", "Open /drug-interactions and report the heading text shown on the page."),
        ("nav", "Open /interaction-checker (alias) and verify it shows the same form. Report the submit button label."),
        ("nav", "Open /compare-drugs.html and report which two drugs are compared by default if any."),
        ("nav", "Open /news and report how many news categories are available in the filter."),
        ("nav", "Open /news/category/fda-alerts and report the title of the most recent article."),
        ("nav", "Open /health-news and report how many health-news articles are shown."),
        ("nav", "Open /health-news/category/clinical-trials (with active category) and report the count of articles."),
        ("nav", "Open /recalls and report how many recalls are listed."),
        ("nav", "Open /recalls?severity=Class+I and report how many Class I recalls are listed."),
        ("nav", "Open /pharmacy and report how many pharmacy chains appear in the chain dropdown."),
        ("nav", "Open /forum and report how many forum categories are listed."),
        ("nav", "Open /glossary?letter=A and report how many glossary terms start with the letter A."),
        ("nav", "Open /side-effects (checker) and report the heading of the page."),
        ("nav", "Open /symptom-checker and report how many symptom options are visible in the first form group."),
        ("nav", "Open /warnings and report the page title."),
        ("nav", "Open /dosage-guide and report the page H1 text."),
        ("nav", "Open /pregnancy-safety and report the page H1 text."),
        ("nav", "Open /emergency-info and report the page H1 text."),
        ("nav", "Open /about and report which year the copyright in the footer starts from."),
        ("nav", "Open /sitemap.html and report how many top-level sitemap categories are listed."),
    ]
    for i, (page_key, ques) in enumerate(nav_tasks):
        emit(tasks, ques, page_key, i)

    # --------------------------------------------------------------
    # 26. Special functional spot-checks (cap 30)
    # --------------------------------------------------------------
    extra = [
        "Open /api/autocomplete?q=ibu and report how many suggestions are returned for 'ibu'.",
        "Open /api/autocomplete?q=met and report the first suggestion label.",
        "Open /search?q=statin and report the top-ranked drug in results.",
        "Open /search?q=blood+pressure and report the top-ranked drug.",
        "Open /search?q=diabetes and report the top-ranked drug.",
        "Open /search?q=anxiety and report the top-ranked drug.",
        "Open /search?q=fluoroquinolone and report how many drugs match.",
        "Open /search?q=NSAID and report the top result.",
        "Open /search?q=migraine and report the top result.",
        "Open /search?q=insomnia and report the top result.",
        "Open /drug-classes/statins and report the description shown for the class.",
        "Open /drug-classes/benzodiazepines and report how many drugs are in this class.",
        "Open /drug-classes/fluoroquinolones and report the description shown for the class.",
        "Open /drug-classes/macrolides and report any drug name listed in the class.",
        "Open /drug-classes/penicillins and report any drug name listed in the class.",
        "Open /condition/hypertension and report how many drugs are listed for hypertension.",
        "Open /condition/diabetes and report how many drugs are listed for diabetes.",
        "Open /condition/depression and report any drug name listed for depression.",
        "Open /condition/anxiety and report any drug name listed for anxiety.",
        "Open /condition/asthma and report any drug name listed for asthma.",
        "Open /condition/hypertension/drugs and report the highest-rated drug listed.",
        "Open /condition/diabetes/drugs and report the highest-rated drug listed.",
        "Open /condition/depression/drugs and report the first drug in the list.",
        "Open /forum/category/general and report how many topics are in 'General Discussion'.",
        "Open /forum/category/side-effects and report how many topics are in 'Side Effects'.",
        "Open /forum/category/pregnancy-breastfeeding and report any topic title.",
        "Open the contact-pharmacist form and report the available topic options in the dropdown.",
        "Open the report-side-effect form and report which severity options are available.",
        "Open the dosage-calculator index and report how many calculators are listed.",
        "Open /pill-identifier/wizard and report what step number is shown for imprint entry.",
    ]
    for i, ques in enumerate(extra):
        emit(tasks, ques, "spot_check", i)

    # --------------------------------------------------------------
    # 27. Reviews + side-effects + warning page composite (cap 50)
    # --------------------------------------------------------------
    idx = 0
    for slug, gname, *_ in drugs[:50]:
        ques = (
            f"Open /{slug}/reviews on Drugs.com. Report how many reviews were "
            f"submitted for {gname}."
        )
        emit(tasks, ques, "reviews_count", idx)
        idx += 1

    # --------------------------------------------------------------
    # 28. Brand-name lookup tasks (cap 60)
    # --------------------------------------------------------------
    idx = 0
    for slug, gname, _, _, _, brands_j, *_ in drugs[:200]:
        try:
            brands = json.loads(brands_j or "[]")
        except Exception:
            brands = []
        if not brands:
            continue
        brand = brands[0]
        ques = (
            f"On the drug page /{slug}, what is the generic name behind the "
            f"brand '{brand}'?"
        )
        emit(tasks, ques, "brand_lookup", idx)
        idx += 1
        if idx >= 60:
            break

    # --------------------------------------------------------------
    # 29. Drug-vs-drug interaction lookup via slug pages (cap 50)
    # --------------------------------------------------------------
    idx = 0
    for a_slug, b_slug, sev in interactions[:50]:
        ques = (
            f"Open /{a_slug}/interactions on Drugs.com. Find {b_slug} in the "
            f"interactions list and report the severity label shown."
        )
        emit(tasks, ques, "drug_interaction_lookup", idx)
        idx += 1

    return tasks


if __name__ == "__main__":
    tasks = main()
    out = os.path.join(HERE, "tasks.jsonl")
    with open(out, "w") as f:
        for t in tasks:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"Wrote {len(tasks)} tasks to {out}")
