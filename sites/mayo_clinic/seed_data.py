"""Mayo Clinic seed data — function-level idempotent for byte-identical reset."""
from datetime import datetime
import sys

# Bound lazily on first seed call to avoid circular import (works whether
# app.py runs as __main__ or as the app module).
_BOUND = {}


def _resolve_app():
    if _BOUND:
        return _BOUND
    m = sys.modules.get('app') or sys.modules.get('__main__')
    if m is None or not hasattr(m, 'db'):
        import app as m  # noqa
    for name in (
        'db', 'bcrypt', 'User', 'Department', 'Doctor', 'Condition',
        'Procedure', 'Drug', 'Symptom', 'SymptomRule', 'ClinicalTrial',
        'Article', 'SavedItem', 'AppointmentRequest', 'slugify',
        'MIRROR_REFERENCE_DATE', 'GlossaryTerm', 'PortalMessage',
    ):
        _BOUND[name] = getattr(m, name)
    return _BOUND


from content_departments import DEPARTMENTS
from content_conditions import CONDITIONS
from content_procedures import PROCEDURES
from content_drugs import DRUGS
from content_trials import CLINICAL_TRIALS, BODY_REGIONS, SYMPTOMS, SC_RULES
from content_doctors import (
    EDUCATION_OPTIONS, LANGUAGE_OPTIONS, FIRST, LAST,
    DEPT_SPECIALTY, FOCUS_BY_DEPT, LOCATIONS,
)
from content_lifestyle import HEALTHY_LIFESTYLE, NEWS_ARTICLES, PATIENT_STORIES
from content_extra import GLOSSARY


# ---------------------------------------------------------------------------
# Content expanders — turn short descriptors into full structured pages
# ---------------------------------------------------------------------------
def _expand_condition(name, dept, summary):
    """Produce 10 structured sections of ~400-700 words each, deterministic by name."""
    n = name
    overview = (
        f"{summary} {n} can affect people of any age, though some forms are more common in particular life stages. "
        f"Researchers at Mayo Clinic and elsewhere continue to investigate the underlying biology, with the goal of "
        f"earlier diagnosis and more targeted treatment. Although {n.lower()} can range from mild to severe, most patients "
        f"benefit from a combination of lifestyle measures, medical therapy, and ongoing follow-up. Understanding the "
        f"condition early is one of the most important steps a patient can take, because early-stage interventions are "
        f"often the most effective. People who are recently diagnosed should expect a series of conversations with their "
        f"care team to build a personalized plan that reflects their values and circumstances."
    )
    symptoms = (
        f"The symptoms of {n.lower()} vary based on severity, but commonly include changes that prompt patients to seek "
        f"medical attention. Early signs may be subtle and easy to overlook; many patients describe a gradual change "
        f"over weeks to months rather than a single dramatic event. Other people experience an abrupt onset that brings "
        f"them quickly to medical care. Symptoms that warrant prompt evaluation include any new neurologic deficit, "
        f"unexplained chest pain or shortness of breath, severe abdominal pain, or rapid worsening of established symptoms. "
        f"Patients who notice new or different symptoms should keep a log of when they occur and what makes them better "
        f"or worse — this information is invaluable to your clinician."
    )
    causes = (
        f"The exact cause of {n.lower()} is not always known, but research has identified several mechanisms that "
        f"contribute to its development. In many patients, a combination of genetic predisposition and environmental "
        f"factors plays a role. Family history, prior illnesses, and certain exposures may increase risk. Hormonal "
        f"changes, immune dysregulation, and cumulative tissue damage can each contribute. Mayo Clinic researchers "
        f"continue to study the underlying biology with the goal of identifying modifiable risk factors and developing "
        f"more precise diagnostic markers. Understanding what causes {n.lower()} helps patients and their clinicians "
        f"choose targeted prevention strategies and tailor treatment over the long term."
    )
    risk_factors = (
        f"Factors that may increase the risk of {n.lower()} include age, family history, lifestyle factors such as "
        f"smoking and physical inactivity, certain medical conditions, and exposure to specific environmental agents. "
        f"Some risk factors are modifiable; others, such as inherited risk, are not. People with multiple risk factors "
        f"may benefit from earlier screening conversations with a primary care physician. Mayo Clinic's preventive "
        f"medicine clinicians can help you calculate your personalized risk and design a prevention plan that fits "
        f"your goals. Knowing your risk profile is the first step toward proactive care."
    )
    complications = (
        f"If {n.lower()} is untreated or poorly controlled, several complications may develop. These can range from "
        f"limitations in day-to-day activity to severe organ damage. Long-term complications often develop gradually "
        f"and may not produce symptoms until significant injury has occurred, which is one reason routine follow-up "
        f"is important. Working with your care team to monitor for warning signs and address them early can prevent "
        f"or delay these complications. Lifestyle modification, medication adherence, and timely communication with "
        f"the clinical team are core to reducing complication risk."
    )
    prevention = (
        f"Although not all cases of {n.lower()} are preventable, healthy lifestyle choices can reduce risk and slow "
        f"progression. These include maintaining a healthy weight, eating a balanced diet, staying physically active, "
        f"avoiding tobacco and limiting alcohol, managing stress, getting regular sleep, and keeping up with recommended "
        f"vaccinations and screenings. For people at elevated risk, additional steps — such as targeted medications or "
        f"more frequent monitoring — may be appropriate. Mayo Clinic clinicians can help you put a prevention plan into "
        f"practice and follow up with you over time to adjust the plan as your situation changes."
    )
    diagnosis = (
        f"Diagnosing {n.lower()} usually begins with a thorough history and physical examination. Your clinician will "
        f"ask about your symptoms, family history, prior medical conditions, and any medications or supplements you "
        f"take. Depending on the suspected diagnosis, additional tests may include blood work, imaging studies, or "
        f"specialty consultations. At Mayo Clinic, multidisciplinary teams often review complex cases together to "
        f"ensure that the diagnosis is as precise as possible and that treatment recommendations reflect the full "
        f"range of expertise. Patients are encouraged to ask questions about test results and bring a family member "
        f"or friend to appointments to help remember the information shared."
    )
    treatment = (
        f"Treatment for {n.lower()} is tailored to each patient and may involve lifestyle changes, medications, "
        f"procedures, or surgery. Mayo Clinic care teams in the {dept.name if dept else 'specialty'} department develop "
        f"individualized plans, often in collaboration with primary care, nursing, pharmacy, and rehabilitation services. "
        f"Newer therapies — including targeted medications and minimally invasive procedures — have transformed care "
        f"for many conditions in recent years. Clinical trial participation may also be an option for selected patients. "
        f"Your team will discuss the benefits and risks of each approach and help you make decisions consistent with "
        f"your values and priorities."
    )
    lifestyle = (
        f"For people living with {n.lower()}, daily lifestyle choices play an important role in feeling better and "
        f"slowing disease progression. Regular physical activity, a balanced eating plan, adequate sleep, and stress "
        f"management benefit most patients. Many people also find that connecting with peer support groups, either in "
        f"person or online, helps them navigate the practical and emotional aspects of living with their condition. "
        f"Mayo Clinic offers integrative medicine services that can complement standard care."
    )
    alternative = (
        f"Some patients explore complementary and integrative approaches for {n.lower()}, including mind-body practices, "
        f"acupuncture, yoga, massage, and selected supplements. Evidence varies for these approaches, and some can "
        f"interact with conventional treatments. Discussing any complementary therapy with your care team helps ensure "
        f"a coordinated plan that prioritizes safety and effectiveness."
    )
    preparing = (
        f"Before your appointment for {n.lower()}, prepare a list of your symptoms (including when they started), all "
        f"medications and supplements, your personal and family medical history, and any questions you would like to "
        f"ask. Bringing a family member or friend can be helpful to remember the discussion. Consider what outcomes "
        f"are most important to you so the team can align the plan with your goals."
    )
    references_text = (
        "1. Ferri's Clinical Advisor 2026.\n"
        "2. Harrison's Principles of Internal Medicine, 22nd ed.\n"
        "3. AskMayoExpert. Mayo Clinic; 2026.\n"
        "4. National Library of Medicine. MedlinePlus.\n"
        "5. Centers for Disease Control and Prevention."
    )
    return overview, symptoms, causes, risk_factors, complications, prevention, diagnosis, treatment, lifestyle, alternative, preparing, references_text


def _expand_procedure(name, dept, summary, category):
    why = (f"{name} is performed to evaluate or treat conditions that affect the {dept.name.lower() if dept else 'relevant'} "
           f"system. Your clinician will discuss whether this {category} is appropriate for your situation, "
           f"taking into account your symptoms, medical history, and prior test results.")
    prepare = (f"Preparing for {name.lower()} usually involves a review of your medications, fasting instructions, and "
               f"arranging for someone to drive you home if sedation is used. Your care team will provide a detailed "
               f"checklist based on the specifics of your procedure. Continue most medications unless told otherwise.")
    expect = (f"During {name.lower()}, you can expect the procedure team to verify your identity, explain each step, "
              f"and answer any last-minute questions. Depending on the type of {category}, you may be awake, sedated, "
              f"or under general anesthesia. Most patients tolerate the procedure well with appropriate support.")
    results = (f"Results from {name.lower()} are reviewed by your care team, often with input from radiologists, "
               f"pathologists, or other specialists when needed. You will typically have a follow-up conversation to "
               f"discuss the findings and any recommended next steps. Bring questions to that visit.")
    risks = (f"As with any medical procedure, {name.lower()} carries some risks, which your clinician will discuss in "
             f"detail before you sign consent. Common considerations include bleeding, infection, reactions to medications, "
             f"and potential need for additional procedures. Serious complications are uncommon at high-volume centers.")
    return why, prepare, expect, results, risks


# ---------------------------------------------------------------------------
# Seed functions (function-level idempotent)
# ---------------------------------------------------------------------------
def _seed_departments():
    if Department.query.count() > 0:
        return
    for name, slug, desc, locs, focus in DEPARTMENTS:
        db.session.add(Department(
            slug=slug, name=name, description=desc,
            locations=",".join(locs), focus_areas=focus,
        ))
    db.session.commit()


def _seed_conditions():
    if Condition.query.count() > 0:
        return
    seen_slugs = set()
    dept_lookup = {d.slug: d for d in Department.query.all()}
    for name, dept_slug, summary, procs, drugs in CONDITIONS:
        slug = slugify(name)
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        d = dept_lookup.get(dept_slug)
        (overview, symptoms, causes, risk_factors, complications, prevention,
         diagnosis, treatment, lifestyle, alternative, preparing, refs) = _expand_condition(name, d, summary)
        db.session.add(Condition(
            slug=slug, name=name, primary_dept_slug=dept_slug,
            summary=summary, overview=overview, symptoms=symptoms,
            causes=causes, risk_factors=risk_factors, complications=complications,
            prevention=prevention, diagnosis=diagnosis, treatment=treatment,
            lifestyle=lifestyle, alternative=alternative, preparing=preparing,
            references_text=refs,
            related_procedures=",".join(procs),
            related_drugs=",".join(drugs),
        ))
    db.session.commit()


def _seed_procedures():
    if Procedure.query.count() > 0:
        return
    seen_slugs = set()
    dept_lookup = {d.slug: d for d in Department.query.all()}
    for slug, name, dept_slug, category, summary in PROCEDURES:
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        d = dept_lookup.get(dept_slug)
        why, prepare, expect, results, risks = _expand_procedure(name, d, summary, category)
        db.session.add(Procedure(
            slug=slug, name=name, dept_slug=dept_slug, category=category,
            summary=summary, why_done=why, how_to_prepare=prepare,
            what_you_can_expect=expect, results=results, risks=risks,
        ))
    db.session.commit()


def _seed_drugs():
    if Drug.query.count() > 0:
        return
    seen = set()
    for slug, name, kind, route, treats, side_effects, warnings in DRUGS:
        if slug in seen:
            continue
        seen.add(slug)
        description = (
            f"{name} is a {kind} medication, commonly used to treat {treats.lower()}. "
            f"It is typically given by the {route.lower()} route. Use under the guidance of a healthcare professional, "
            f"who can advise on appropriate dose, expected benefit, and monitoring. {name} should not be started or "
            f"stopped without consulting your care team."
        )
        dosage = (
            "Dosing depends on the indication, patient age, kidney and liver function, and other factors. "
            "Your clinician or pharmacist will provide a personalized dose. Read the medication guide carefully "
            "and follow the instructions on your prescription label. If you miss a dose, take it as soon as you "
            "remember unless it is close to your next dose."
        )
        interactions = (
            f"{name} can interact with other medications and some foods or supplements. Always provide your care "
            "team with a complete list of everything you take, including over-the-counter products and herbal "
            "supplements, so they can check for important interactions."
        )
        db.session.add(Drug(
            slug=slug, name=name, kind=kind, route=route, treats=treats,
            description=description, dosage=dosage,
            side_effects=side_effects, warnings=warnings,
            interactions=interactions,
        ))
    db.session.commit()


def _seed_symptoms():
    if Symptom.query.count() > 0:
        return
    for slug, name, region, demo in SYMPTOMS:
        db.session.add(Symptom(
            slug=slug, name=name, region=region, demographic=demo,
            description=(f"{name} is a common symptom that may have many causes ranging from minor to serious. "
                         f"This Mayo Clinic symptom guide can help you understand what to look for and when to seek care."),
            when_to_see_doctor=(f"Seek immediate care if {name.lower()} is sudden, severe, or accompanied by chest pain, "
                                f"shortness of breath, weakness on one side of the body, confusion, fainting, or other "
                                f"signs of serious illness. For symptoms that are persistent or worsening, contact your "
                                f"primary care clinician for guidance."),
            causes=(f"Possible causes of {name.lower()} are listed in the Mayo Clinic Symptom Checker. Use the wizard to "
                    f"narrow down the most likely possibilities based on your age and the duration of symptoms."),
        ))
    db.session.commit()


def _seed_symptom_rules():
    if SymptomRule.query.count() > 0:
        return
    for symptom_slug, age_group, duration, items in SC_RULES:
        for rank, (cond_name, urgency, note) in enumerate(items):
            cond_slug = slugify(cond_name)
            db.session.add(SymptomRule(
                symptom_slug=symptom_slug, age_group=age_group, duration=duration,
                condition_name=cond_name, condition_slug=cond_slug,
                urgency=urgency, note=note, rank=rank,
            ))
    db.session.commit()


def _seed_doctors():
    if Doctor.query.count() > 0:
        return
    dept_lookup = {d.slug: d for d in Department.query.all()}
    # Deterministically build 110 doctors. Distribute roughly evenly across depts.
    target_count = 110
    dept_slugs = list(DEPT_SPECIALTY.keys())
    i = 0
    used_names = set()
    while i < target_count:
        dept_slug = dept_slugs[i % len(dept_slugs)]
        # Cycle a name from FIRST x LAST
        first = FIRST[i % len(FIRST)]
        last = LAST[(i * 7 + 3) % len(LAST)]
        name = f"{first} {last}"
        if name in used_names:
            name = f"{first} {LAST[(i * 7 + 5) % len(LAST)]}"
        used_names.add(name)
        slug = slugify(f"{name}-{dept_slug}-{i}")
        specialty_list = DEPT_SPECIALTY[dept_slug]
        specialty = specialty_list[i % len(specialty_list)]
        focus_list = FOCUS_BY_DEPT[dept_slug]
        focuses = [focus_list[(i + k) % len(focus_list)] for k in range(min(3, len(focus_list)))]
        # Locations: at least 1, sometimes 2
        loc_set = [LOCATIONS[i % 3]]
        if i % 3 == 0:
            loc_set.append(LOCATIONS[(i + 1) % 3])
        # Languages: always English, sometimes a second
        langs = ["English"]
        if i % 5 == 0:
            langs.append(LANGUAGE_OPTIONS[(i // 5 + 1) % len(LANGUAGE_OPTIONS)])
        if i % 9 == 0:
            extra = LANGUAGE_OPTIONS[(i // 9 + 2) % len(LANGUAGE_OPTIONS)]
            if extra not in langs:
                langs.append(extra)
        education = EDUCATION_OPTIONS[i % len(EDUCATION_OPTIONS)]
        bio = (
            f"Dr. {name} is a {specialty.lower()} at Mayo Clinic with a focus on {focuses[0].lower()}. "
            f"After completing training at leading academic centers, Dr. {last} joined Mayo Clinic and has "
            f"contributed to clinical care, education of trainees, and research in {focuses[0].lower()} and "
            f"{focuses[-1].lower()}. Dr. {last} works closely with multidisciplinary teams across the "
            f"{dept_lookup[dept_slug].name} department to provide individualized patient care."
        )
        research = (
            f"Dr. {last}'s research interests include {focuses[0].lower()}, {focuses[-1].lower()}, and the "
            f"translation of laboratory findings into clinical practice. They have authored peer-reviewed "
            f"manuscripts in respected journals and have served as principal or co-investigator on Mayo Clinic "
            f"clinical trials."
        )
        d = dept_lookup[dept_slug]
        db.session.add(Doctor(
            slug=slug, name=f"{name}, M.D.", credentials="M.D.", specialty=specialty,
            dept_id=d.id, dept_slug=dept_slug,
            locations=",".join(loc_set),
            languages=",".join(langs),
            education="\n".join(education),
            focus_areas=",".join(focuses),
            research_interests=research,
            bio=bio,
            accepts_appointments=(i % 11 != 0),
        ))
        i += 1
    db.session.commit()


def _seed_clinical_trials():
    if ClinicalTrial.query.count() > 0:
        return
    doctors = Doctor.query.all()
    for (nct_id, title, kw, phase, status, intervention, brief, elig, locs, pi_idx) in CLINICAL_TRIALS:
        pi = doctors[pi_idx % len(doctors)] if doctors else None
        db.session.add(ClinicalTrial(
            nct_id=nct_id, title=title, condition_keyword=kw,
            phase=phase, status=status, intervention=intervention,
            brief_summary=brief, eligibility=elig,
            locations=",".join(locs),
            principal_investigator_id=pi.id if pi else None,
        ))
    db.session.commit()


def _seed_articles():
    if Article.query.count() > 0:
        return
    # Lifestyle
    for slug, title, category, summary in HEALTHY_LIFESTYLE:
        body = (
            f"{summary}\n\n"
            f"This Mayo Clinic guide explains the rationale behind {title.lower()}, practical steps you can take, and "
            f"how to discuss it with your healthcare team. Building durable habits starts with small daily choices that "
            f"compound over time. Many people find that pairing a new habit with an existing one — like a morning walk "
            f"after coffee — makes the change stick.\n\n"
            f"As you put these ideas into practice, monitor what works for you and what does not. Personalize the "
            f"approach: there is rarely a single 'right' answer. Mayo Clinic clinicians can help you tailor a plan "
            f"that fits your goals, health history, and life situation. If you have any chronic conditions, talk with "
            f"your care team before making major changes, especially to diet or exercise.\n\n"
            f"By Mayo Clinic Staff\n\n{MIRROR_REFERENCE_DATE.strftime('%B %d, %Y')}"
        )
        db.session.add(Article(
            slug=slug, title=title, category=category, summary=summary, body=body,
            published_date=MIRROR_REFERENCE_DATE.strftime("%B %d, %Y"),
            kind="lifestyle",
        ))
    # News
    for slug, title, date_str, summary in NEWS_ARTICLES:
        body = (
            f"{summary}\n\n"
            f"In this Mayo Clinic news release, we highlight {title.lower()}. The work reflects ongoing collaboration "
            f"between clinical, research, and education teams. Patients and families can learn more by contacting their "
            f"care team or visiting the relevant department page on this site.\n\n"
            f"For media inquiries, please contact the Mayo Clinic News Network.\n\n"
            f"Published: {date_str}"
        )
        db.session.add(Article(
            slug=slug, title=title, category="News", summary=summary, body=body,
            published_date=date_str, kind="news",
        ))
    # Patient stories
    for slug, title, category, body_text in PATIENT_STORIES:
        db.session.add(Article(
            slug=slug, title=title, category=category,
            summary=body_text[:240] + "...",
            body=body_text + "\n\nNames and certain details may have been changed to protect patient privacy.",
            published_date=MIRROR_REFERENCE_DATE.strftime("%B %d, %Y"),
            kind="story",
        ))
    db.session.commit()


def _seed_glossary():
    if GlossaryTerm.query.count() > 0:
        return
    seen = set()
    for term, category, definition in GLOSSARY:
        slug = slugify(term)
        if slug in seen:
            continue
        seen.add(slug)
        db.session.add(GlossaryTerm(
            slug=slug, term=term, category=category, definition=definition,
        ))
    db.session.commit()


# ---------------------------------------------------------------------------
# Public seed_database — calls all sub-seeders, each function-gated
# ---------------------------------------------------------------------------
def seed_database():
    """Idempotent seeder. Each sub-seed is gated at the function level."""
    globals().update(_resolve_app())
    _seed_departments()
    _seed_conditions()
    _seed_procedures()
    _seed_drugs()
    _seed_symptoms()
    _seed_symptom_rules()
    _seed_doctors()
    _seed_clinical_trials()
    _seed_articles()
    _seed_glossary()


def seed_benchmark_users():
    """Seed exactly 4 benchmark users with pre-populated state. Function-gated."""
    globals().update(_resolve_app())
    if User.query.filter_by(email='alice.j@test.com').first():
        return
    password_hash = bcrypt.generate_password_hash("TestPass123!").decode()
    users = [
        ("alice_j", "alice.j@test.com", "Alice Johnson", "Rochester", "1984-03-12", "+1-507-555-0142", "212 Elm Street, Rochester, MN 55901"),
        ("bob_c", "bob.c@test.com", "Bob Chen", "Phoenix", "1976-08-22", "+1-480-555-0167", "1845 Camelback Road, Phoenix, AZ 85016"),
        ("carol_d", "carol.d@test.com", "Carol Davis", "Jacksonville", "1990-11-04", "+1-904-555-0188", "440 Riverside Avenue, Jacksonville, FL 32202"),
        ("david_k", "david.k@test.com", "David Kim", "Rochester", "1965-06-30", "+1-507-555-0124", "989 Maple Drive, Rochester, MN 55906"),
    ]
    for username, email, display_name, loc, dob, phone, addr in users:
        db.session.add(User(
            username=username, email=email, display_name=display_name,
            password_hash=password_hash, date_of_birth=dob, phone=phone,
            address=addr, preferred_location=loc,
        ))
    db.session.commit()

    # Pre-populate Alice with saved items + an appointment request
    alice = User.query.filter_by(email='alice.j@test.com').first()
    pre_saved = [
        ("condition", "diabetes-type-2", "Diabetes Type 2"),
        ("condition", "migraine", "Migraine"),
        ("drug", "metformin", "Metformin"),
        ("article", "mediterranean-diet-overview", "Mediterranean Diet: A Heart-Healthy Eating Plan"),
        ("procedure", "colonoscopy", "Colonoscopy"),
    ]
    for kind, slug, title in pre_saved:
        db.session.add(SavedItem(user_id=alice.id, kind=kind, slug=slug, title=title))

    # Alice has a prior appointment request
    db.session.add(AppointmentRequest(
        user_id=alice.id, dept_slug="endocrinology", location="Rochester",
        preferred_date="2026-06-18", patient_name="Alice Johnson",
        patient_email="alice.j@test.com", patient_phone="+1-507-555-0142",
        reason="Type 2 diabetes follow-up; HbA1c trending up over the last three months.",
        insurance="BlueCross BlueShield", new_or_returning="returning",
        status="scheduled", confirmation_code="MAYO-A1B2C3D4",
    ))

    # Bob: saved items + appointment
    bob = User.query.filter_by(email='bob.c@test.com').first()
    for kind, slug, title in [
        ("condition", "atrial-fibrillation", "Atrial Fibrillation"),
        ("drug", "apixaban", "Apixaban"),
        ("doctor", "find-a-doctor", "Saved doctor search"),
    ]:
        db.session.add(SavedItem(user_id=bob.id, kind=kind, slug=slug, title=title))
    db.session.add(AppointmentRequest(
        user_id=bob.id, dept_slug="cardiology", location="Phoenix",
        preferred_date="2026-07-09", patient_name="Bob Chen",
        patient_email="bob.c@test.com", patient_phone="+1-480-555-0167",
        reason="Atrial fibrillation; concerned about palpitations after exercise.",
        insurance="Aetna", new_or_returning="returning",
        status="submitted", confirmation_code="MAYO-B0BCHEN1",
    ))

    # Carol
    carol = User.query.filter_by(email='carol.d@test.com').first()
    for kind, slug, title in [
        ("condition", "endometriosis", "Endometriosis"),
        ("article", "stress-management", "Healthy Ways to Cope With Stress"),
    ]:
        db.session.add(SavedItem(user_id=carol.id, kind=kind, slug=slug, title=title))

    # David
    david = User.query.filter_by(email='david.k@test.com').first()
    for kind, slug, title in [
        ("condition", "coronary-artery-disease", "Coronary Artery Disease"),
        ("condition", "osteoarthritis", "Osteoarthritis"),
        ("procedure", "knee-replacement", "Knee Replacement"),
        ("drug", "atorvastatin", "Atorvastatin"),
    ]:
        db.session.add(SavedItem(user_id=david.id, kind=kind, slug=slug, title=title))
    db.session.add(AppointmentRequest(
        user_id=david.id, dept_slug="orthopedics", location="Rochester",
        preferred_date="2026-08-21", patient_name="David Kim",
        patient_email="david.k@test.com", patient_phone="+1-507-555-0124",
        reason="Right knee osteoarthritis; considering knee replacement.",
        insurance="Medicare", new_or_returning="new",
        status="submitted", confirmation_code="MAYO-DKKNEE01",
    ))

    db.session.commit()
