#!/usr/bin/env python3
"""Berkeley GUI deepen — adds 30+ templates, 20+ POST routes, image utilization.

Registered from app.py at startup. All models defined here; seed_extras() runs
once (gated on Library.query.count()==0). New routes are GUI-only — no /api,
no JSON. Forms render real HTML, POST handlers redirect with flash.
"""
from datetime import datetime, timedelta
import hashlib
import re

from flask import (render_template, request, redirect, url_for, flash,
                   abort, jsonify)
from flask_login import login_required, current_user

# These get bound in register(app, db)
db = None
app = None

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _slugify(text):
    if not text:
        return ''
    s = re.sub(r'[^a-zA-Z0-9\s-]', '', text)
    s = re.sub(r'[\s]+', '-', s.strip().lower())
    return s

def _det_idx(seed_text, n):
    """Deterministic 1..n from a string."""
    h = hashlib.md5(seed_text.encode()).hexdigest()
    return int(h[:8], 16) % n + 1

def campus_photo(slug):
    return f"campus_{_det_idx('cam_' + slug, 20):03d}.svg"

def headshot_photo(slug):
    return f"headshot_{_det_idx('hs_' + slug, 20):03d}.svg"

def banner_photo(slug):
    return f"banner_{_det_idx('ba_' + slug, 12):03d}.svg"

def fund_photo(slug):
    return f"fund_{_det_idx('fu_' + slug, 10):03d}.svg"

def library_photo(slug):
    # Real per-branch Wikimedia photos harvested 2026-05-27. Each slug has a
    # corresponding library-{slug}.jpg file in static/images/. Two unmatched
    # branches (east-asian, berkeley-business-long) fall back to copies of
    # doe / bancroft on disk so the slug → file mapping is total.
    return f"library-{slug}.jpg"

def sport_photo(slug):
    return f"sport_{_det_idx('sp_' + slug, 8):03d}.svg"


# ── Real Wikipedia photos (harvested 2026-05-27) ───────────────────────────
# Each map: slug → static/images/<file>.webp. Files were scraped from
# Wikipedia REST summary API (see scrape-real-images skill); fallback to the
# legacy *_photo() SVG only if the slug isn't covered. Replacing the broad
# SVG-pool placeholders cuts top-image duplication from 20-27 % down to ≤5 %.
SPORT_REAL_PHOTOS = {
    "football": "sport-football.webp",
    "basketball-men": "sport-basketball-men.webp",
    "basketball-women": "sport-basketball-women.webp",
    "baseball": "sport-baseball.webp",
    "softball": "sport-softball.webp",
    "volleyball": "sport-volleyball.webp",
    "volleyball-men": "sport-volleyball-men.webp",
    "soccer-men": "sport-soccer-men.webp",
    "soccer-women": "sport-soccer-women.webp",
    "swimming-men": "sport-swimming-men.webp",
    "swimming-women": "sport-swimming-women.webp",
    "water-polo-men": "sport-water-polo-men.webp",
    "water-polo-women": "sport-water-polo-women.webp",
    "tennis-men": "sport-tennis-men.webp",
    "tennis-women": "sport-tennis-women.webp",
    "golf-men": "sport-golf-men.webp",
    "golf-women": "sport-golf-women.webp",
    "track-field-men": "sport-track-field-men.webp",
    "track-field-women": "sport-track-field-women.webp",
    "cross-country-men": "sport-cross-country-men.webp",
    "cross-country-women": "sport-cross-country-women.webp",
    "field-hockey": "sport-field-hockey.webp",
    "lacrosse": "sport-lacrosse.webp",
    "rugby-men": "sport-rugby-men.webp",
    "rugby-women": "sport-rugby-women.webp",
    "rowing-men": "sport-rowing-men.webp",
    "rowing-women": "sport-rowing-women.webp",
    "gymnastics": "sport-gymnastics.webp",
}

ALUMNI_CHAPTER_REAL_PHOTOS = {
    "sf-bay-area": "chapter-sf-bay-area.webp",
    "los-angeles": "chapter-los-angeles.webp",
    "new-york-city": "chapter-new-york-city.webp",
    "boston": "chapter-boston.webp",
    "washington-dc": "chapter-washington-dc.webp",
    "chicago": "chapter-chicago.webp",
    "seattle": "chapter-seattle.webp",
    "portland": "chapter-portland.webp",
    "san-diego": "chapter-san-diego.webp",
    "sacramento": "chapter-sacramento.webp",
    "houston": "chapter-houston.webp",
    "dallas-fort-worth": "chapter-dallas-fort-worth.webp",
    "atlanta": "chapter-atlanta.webp",
    "miami": "chapter-miami.webp",
    "denver": "chapter-denver.webp",
    "phoenix": "chapter-phoenix.webp",
    "tokyo": "chapter-tokyo.webp",
    "london": "chapter-london.webp",
    "hong-kong": "chapter-hong-kong.webp",
    "singapore": "chapter-singapore.webp",
    "beijing": "chapter-beijing.webp",
    "mumbai": "chapter-mumbai.webp",
    "mexico-city": "chapter-mexico-city.webp",
    "sydney": "chapter-sydney.webp",
    "paris": "chapter-paris.webp",
}

GIVING_FUND_REAL_PHOTOS = {
    "annual-fund": "fund-annual-fund.webp",
    "undergrad-scholarship": "fund-undergrad-scholarship.webp",
    "graduate-fellowship": "fund-graduate-fellowship.webp",
    "first-gen-initiative": "fund-first-gen-initiative.webp",
    "library-endowment": "fund-library-endowment.webp",
    "doe-library-restoration": "fund-doe-library-restoration.webp",
    "climate-equity": "fund-climate-equity.webp",
    "ai-research": "fund-ai-research.webp",
    "cancer-research": "fund-cancer-research.webp",
    "athletics-excellence": "fund-athletics-excellence.webp",
    "memorial-stadium-endowment": "fund-memorial-stadium-endowment.webp",
    "cal-performances": "fund-cal-performances.webp",
    "botanical-garden": "fund-botanical-garden.webp",
    "public-service-internships": "fund-public-service-internships.webp",
    "disabled-students-program": "fund-disabled-students-program.webp",
}


def sport_real_photo(slug):
    return SPORT_REAL_PHOTOS.get(slug) or sport_photo(slug)


def chapter_real_photo(slug):
    return ALUMNI_CHAPTER_REAL_PHOTOS.get(slug) or campus_photo(slug)


def fund_real_photo(slug):
    return GIVING_FUND_REAL_PHOTOS.get(slug) or fund_photo(slug)


# Fixed snapshot reference date so seed-time expressions don't drift
SNAPSHOT_DT = datetime(2026, 5, 1, 9, 0, 0)


# ─── Module-level model placeholders (populated in register) ─────────────────

Library = None
Sport = None
AlumniChapter = None
GivingFund = None
Leader = None
StudentService = None
FinancialAidProgram = None
NewsCategoryHub = None

ApplicationSubmission = None
TourBooking = None
EventRSVP = None
EventSignupRow = None
Donation = None
ContactMessage = None
LibraryReservation = None
NewsletterSubscription = None
AppointmentBooking = None
ProgramInquiry = None
ScholarshipApplication = None
AlumniDirectoryUpdate = None
ResearchContact = None
EventSuggestion = None
GeneralContact = None
RecurringGift = None
TicketRequest = None


def _define_models(_db):
    global Library, Sport, AlumniChapter, GivingFund, Leader, StudentService
    global FinancialAidProgram, NewsCategoryHub
    global ApplicationSubmission, TourBooking, EventRSVP, EventSignupRow
    global Donation, ContactMessage, LibraryReservation, NewsletterSubscription
    global AppointmentBooking, ProgramInquiry, ScholarshipApplication
    global AlumniDirectoryUpdate, ResearchContact, EventSuggestion
    global GeneralContact, RecurringGift, TicketRequest

    class _Library(_db.Model):
        __tablename__ = 'libraries'
        id = _db.Column(_db.Integer, primary_key=True)
        name = _db.Column(_db.String(200), nullable=False)
        slug = _db.Column(_db.String(200), unique=True, nullable=False, index=True)
        branch_type = _db.Column(_db.String(80), default='Subject Library')
        location = _db.Column(_db.String(200), default='')
        hours = _db.Column(_db.String(200), default='Mon-Fri 9am-9pm, Sat 10am-6pm, Sun 12pm-6pm')
        phone = _db.Column(_db.String(40), default='')
        librarian = _db.Column(_db.String(150), default='')
        description = _db.Column(_db.Text, default='')
        photo = _db.Column(_db.String(120), default='')
        seat_count = _db.Column(_db.Integer, default=200)
        room_count = _db.Column(_db.Integer, default=8)
        special_collections = _db.Column(_db.String(500), default='')
    Library = _Library

    class _Sport(_db.Model):
        __tablename__ = 'sports'
        id = _db.Column(_db.Integer, primary_key=True)
        name = _db.Column(_db.String(120), nullable=False)
        slug = _db.Column(_db.String(120), unique=True, nullable=False, index=True)
        gender = _db.Column(_db.String(20), default='Mixed')
        season = _db.Column(_db.String(40), default='Fall')
        head_coach = _db.Column(_db.String(150), default='')
        home_venue = _db.Column(_db.String(150), default='')
        roster_size = _db.Column(_db.Integer, default=25)
        national_titles = _db.Column(_db.Integer, default=0)
        last_season_record = _db.Column(_db.String(50), default='')
        next_match = _db.Column(_db.String(200), default='')
        banner_photo = _db.Column(_db.String(120), default='')
        description = _db.Column(_db.Text, default='')
    Sport = _Sport

    class _AlumniChapter(_db.Model):
        __tablename__ = 'alumni_chapters'
        id = _db.Column(_db.Integer, primary_key=True)
        name = _db.Column(_db.String(150), nullable=False)
        slug = _db.Column(_db.String(150), unique=True, nullable=False, index=True)
        region = _db.Column(_db.String(80), default='')
        country = _db.Column(_db.String(80), default='USA')
        members_count = _db.Column(_db.Integer, default=200)
        president = _db.Column(_db.String(150), default='')
        founded_year = _db.Column(_db.Integer, default=1970)
        next_event = _db.Column(_db.String(250), default='')
        photo = _db.Column(_db.String(120), default='')
        description = _db.Column(_db.Text, default='')
    AlumniChapter = _AlumniChapter

    class _GivingFund(_db.Model):
        __tablename__ = 'giving_funds'
        id = _db.Column(_db.Integer, primary_key=True)
        name = _db.Column(_db.String(200), nullable=False)
        slug = _db.Column(_db.String(200), unique=True, nullable=False, index=True)
        category = _db.Column(_db.String(80), default='General Support')
        target_amount = _db.Column(_db.Integer, default=1000000)
        raised_amount = _db.Column(_db.Integer, default=250000)
        donor_count = _db.Column(_db.Integer, default=400)
        priority = _db.Column(_db.String(40), default='Standard')
        photo = _db.Column(_db.String(120), default='')
        description = _db.Column(_db.Text, default='')
        impact_statement = _db.Column(_db.Text, default='')
    GivingFund = _GivingFund

    class _Leader(_db.Model):
        __tablename__ = 'leaders'
        id = _db.Column(_db.Integer, primary_key=True)
        name = _db.Column(_db.String(150), nullable=False)
        slug = _db.Column(_db.String(200), unique=True, nullable=False, index=True)
        title = _db.Column(_db.String(200), default='')
        office = _db.Column(_db.String(80), default='Chancellor Office')
        bio = _db.Column(_db.Text, default='')
        email = _db.Column(_db.String(120), default='')
        phone = _db.Column(_db.String(40), default='')
        appointed_year = _db.Column(_db.Integer, default=2020)
        headshot = _db.Column(_db.String(120), default='')
        priorities = _db.Column(_db.String(500), default='')
    Leader = _Leader

    class _StudentService(_db.Model):
        __tablename__ = 'student_services'
        id = _db.Column(_db.Integer, primary_key=True)
        name = _db.Column(_db.String(200), nullable=False)
        slug = _db.Column(_db.String(200), unique=True, nullable=False, index=True)
        category = _db.Column(_db.String(60), default='Wellness')
        location = _db.Column(_db.String(200), default='')
        phone = _db.Column(_db.String(40), default='')
        hours = _db.Column(_db.String(200), default='Mon-Fri 9am-5pm')
        appointment_required = _db.Column(_db.Boolean, default=False)
        cost = _db.Column(_db.String(50), default='Free')
        photo = _db.Column(_db.String(120), default='')
        description = _db.Column(_db.Text, default='')
    StudentService = _StudentService

    class _FinancialAidProgram(_db.Model):
        __tablename__ = 'financial_aid_programs'
        id = _db.Column(_db.Integer, primary_key=True)
        name = _db.Column(_db.String(200), nullable=False)
        slug = _db.Column(_db.String(200), unique=True, nullable=False, index=True)
        category = _db.Column(_db.String(60), default='Grant')
        max_amount = _db.Column(_db.Integer, default=10000)
        application_deadline = _db.Column(_db.String(80), default='')
        eligibility = _db.Column(_db.Text, default='')
        renewable = _db.Column(_db.Boolean, default=True)
        description = _db.Column(_db.Text, default='')
        photo = _db.Column(_db.String(120), default='')
    FinancialAidProgram = _FinancialAidProgram

    class _NewsCategoryHub(_db.Model):
        __tablename__ = 'news_category_hubs'
        id = _db.Column(_db.Integer, primary_key=True)
        slug = _db.Column(_db.String(80), unique=True, nullable=False, index=True)
        name = _db.Column(_db.String(120), nullable=False)
        tagline = _db.Column(_db.String(300), default='')
        banner_photo = _db.Column(_db.String(120), default='')
        editor = _db.Column(_db.String(150), default='Berkeley News Staff')
        description = _db.Column(_db.Text, default='')
    NewsCategoryHub = _NewsCategoryHub

    # ── Write tables ──
    class _ApplicationSubmission(_db.Model):
        __tablename__ = 'application_submissions'
        id = _db.Column(_db.Integer, primary_key=True)
        applicant_name = _db.Column(_db.String(150), nullable=False)
        email = _db.Column(_db.String(120), nullable=False)
        program_slug = _db.Column(_db.String(200), nullable=False)
        admission_level = _db.Column(_db.String(40), default='undergrad')
        statement = _db.Column(_db.Text, default='')
        gpa = _db.Column(_db.String(20), default='')
        residency = _db.Column(_db.String(40), default='in-state')
        submitted_at = _db.Column(_db.DateTime, default=SNAPSHOT_DT)
    ApplicationSubmission = _ApplicationSubmission

    class _TourBooking(_db.Model):
        __tablename__ = 'tour_bookings'
        id = _db.Column(_db.Integer, primary_key=True)
        name = _db.Column(_db.String(150), nullable=False)
        email = _db.Column(_db.String(120), nullable=False)
        tour_date = _db.Column(_db.String(40), default='')
        tour_type = _db.Column(_db.String(60), default='Campus Walk')
        group_size = _db.Column(_db.Integer, default=1)
        notes = _db.Column(_db.Text, default='')
        booked_at = _db.Column(_db.DateTime, default=SNAPSHOT_DT)
    TourBooking = _TourBooking

    class _EventRSVP(_db.Model):
        __tablename__ = 'event_rsvps'
        id = _db.Column(_db.Integer, primary_key=True)
        event_id = _db.Column(_db.Integer, nullable=False)
        name = _db.Column(_db.String(150), nullable=False)
        email = _db.Column(_db.String(120), nullable=False)
        guest_count = _db.Column(_db.Integer, default=1)
        dietary = _db.Column(_db.String(100), default='')
        accessibility = _db.Column(_db.String(200), default='')
        rsvped_at = _db.Column(_db.DateTime, default=SNAPSHOT_DT)
    EventRSVP = _EventRSVP

    class _EventSignupRow(_db.Model):
        __tablename__ = 'event_signups'
        id = _db.Column(_db.Integer, primary_key=True)
        event_id = _db.Column(_db.Integer, nullable=False)
        name = _db.Column(_db.String(150), nullable=False)
        email = _db.Column(_db.String(120), nullable=False)
        signup_type = _db.Column(_db.String(40), default='attendee')
        notes = _db.Column(_db.Text, default='')
        signed_up_at = _db.Column(_db.DateTime, default=SNAPSHOT_DT)
    EventSignupRow = _EventSignupRow

    class _Donation(_db.Model):
        __tablename__ = 'donations'
        id = _db.Column(_db.Integer, primary_key=True)
        donor_name = _db.Column(_db.String(150), nullable=False)
        email = _db.Column(_db.String(120), nullable=False)
        fund_slug = _db.Column(_db.String(200), nullable=False)
        amount = _db.Column(_db.Integer, default=100)
        is_anonymous = _db.Column(_db.Boolean, default=False)
        message = _db.Column(_db.Text, default='')
        donated_at = _db.Column(_db.DateTime, default=SNAPSHOT_DT)
    Donation = _Donation

    class _ContactMessage(_db.Model):
        __tablename__ = 'contact_messages'
        id = _db.Column(_db.Integer, primary_key=True)
        faculty_slug = _db.Column(_db.String(200), nullable=False)
        sender_name = _db.Column(_db.String(150), nullable=False)
        sender_email = _db.Column(_db.String(120), nullable=False)
        subject = _db.Column(_db.String(200), default='')
        message = _db.Column(_db.Text, default='')
        purpose = _db.Column(_db.String(60), default='research_inquiry')
        sent_at = _db.Column(_db.DateTime, default=SNAPSHOT_DT)
    ContactMessage = _ContactMessage

    class _LibraryReservation(_db.Model):
        __tablename__ = 'library_reservations'
        id = _db.Column(_db.Integer, primary_key=True)
        library_slug = _db.Column(_db.String(200), nullable=False)
        name = _db.Column(_db.String(150), nullable=False)
        email = _db.Column(_db.String(120), nullable=False)
        room_type = _db.Column(_db.String(60), default='Study Room')
        reserve_date = _db.Column(_db.String(40), default='')
        time_slot = _db.Column(_db.String(40), default='')
        group_size = _db.Column(_db.Integer, default=1)
        reserved_at = _db.Column(_db.DateTime, default=SNAPSHOT_DT)
    LibraryReservation = _LibraryReservation

    class _NewsletterSubscription(_db.Model):
        __tablename__ = 'newsletter_subscriptions'
        id = _db.Column(_db.Integer, primary_key=True)
        email = _db.Column(_db.String(120), nullable=False)
        list_name = _db.Column(_db.String(80), default='berkeley-weekly')
        frequency = _db.Column(_db.String(20), default='weekly')
        subscribed_at = _db.Column(_db.DateTime, default=SNAPSHOT_DT)
    NewsletterSubscription = _NewsletterSubscription

    class _AppointmentBooking(_db.Model):
        __tablename__ = 'appointment_bookings'
        id = _db.Column(_db.Integer, primary_key=True)
        department_slug = _db.Column(_db.String(200), nullable=False)
        name = _db.Column(_db.String(150), nullable=False)
        email = _db.Column(_db.String(120), nullable=False)
        purpose = _db.Column(_db.String(200), default='')
        preferred_date = _db.Column(_db.String(40), default='')
        booked_at = _db.Column(_db.DateTime, default=SNAPSHOT_DT)
    AppointmentBooking = _AppointmentBooking

    class _ProgramInquiry(_db.Model):
        __tablename__ = 'program_inquiries'
        id = _db.Column(_db.Integer, primary_key=True)
        program_slug = _db.Column(_db.String(200), nullable=False)
        name = _db.Column(_db.String(150), nullable=False)
        email = _db.Column(_db.String(120), nullable=False)
        question = _db.Column(_db.Text, default='')
        sent_at = _db.Column(_db.DateTime, default=SNAPSHOT_DT)
    ProgramInquiry = _ProgramInquiry

    class _ScholarshipApplication(_db.Model):
        __tablename__ = 'scholarship_applications'
        id = _db.Column(_db.Integer, primary_key=True)
        program_slug = _db.Column(_db.String(200), nullable=False)
        applicant_name = _db.Column(_db.String(150), nullable=False)
        email = _db.Column(_db.String(120), nullable=False)
        statement = _db.Column(_db.Text, default='')
        amount_requested = _db.Column(_db.Integer, default=5000)
        gpa = _db.Column(_db.String(20), default='')
        submitted_at = _db.Column(_db.DateTime, default=SNAPSHOT_DT)
    ScholarshipApplication = _ScholarshipApplication

    class _AlumniDirectoryUpdate(_db.Model):
        __tablename__ = 'alumni_directory_updates'
        id = _db.Column(_db.Integer, primary_key=True)
        name = _db.Column(_db.String(150), nullable=False)
        email = _db.Column(_db.String(120), nullable=False)
        grad_year = _db.Column(_db.Integer, default=2020)
        employer = _db.Column(_db.String(200), default='')
        position = _db.Column(_db.String(200), default='')
        city = _db.Column(_db.String(120), default='')
        updated_at = _db.Column(_db.DateTime, default=SNAPSHOT_DT)
    AlumniDirectoryUpdate = _AlumniDirectoryUpdate

    class _ResearchContact(_db.Model):
        __tablename__ = 'research_contacts'
        id = _db.Column(_db.Integer, primary_key=True)
        center_slug = _db.Column(_db.String(200), nullable=False)
        name = _db.Column(_db.String(150), nullable=False)
        email = _db.Column(_db.String(120), nullable=False)
        message = _db.Column(_db.Text, default='')
        partnership_type = _db.Column(_db.String(60), default='research_collab')
        sent_at = _db.Column(_db.DateTime, default=SNAPSHOT_DT)
    ResearchContact = _ResearchContact

    class _EventSuggestion(_db.Model):
        __tablename__ = 'event_suggestions'
        id = _db.Column(_db.Integer, primary_key=True)
        suggester_name = _db.Column(_db.String(150), nullable=False)
        email = _db.Column(_db.String(120), nullable=False)
        title = _db.Column(_db.String(200), default='')
        description = _db.Column(_db.Text, default='')
        proposed_date = _db.Column(_db.String(40), default='')
        category = _db.Column(_db.String(40), default='Lecture')
        suggested_at = _db.Column(_db.DateTime, default=SNAPSHOT_DT)
    EventSuggestion = _EventSuggestion

    class _GeneralContact(_db.Model):
        __tablename__ = 'general_contacts'
        id = _db.Column(_db.Integer, primary_key=True)
        name = _db.Column(_db.String(150), nullable=False)
        email = _db.Column(_db.String(120), nullable=False)
        topic = _db.Column(_db.String(80), default='General Inquiry')
        message = _db.Column(_db.Text, default='')
        sent_at = _db.Column(_db.DateTime, default=SNAPSHOT_DT)
    GeneralContact = _GeneralContact

    class _RecurringGift(_db.Model):
        __tablename__ = 'recurring_gifts'
        id = _db.Column(_db.Integer, primary_key=True)
        donor_name = _db.Column(_db.String(150), nullable=False)
        email = _db.Column(_db.String(120), nullable=False)
        fund_slug = _db.Column(_db.String(200), nullable=False)
        monthly_amount = _db.Column(_db.Integer, default=50)
        start_date = _db.Column(_db.String(40), default='')
        setup_at = _db.Column(_db.DateTime, default=SNAPSHOT_DT)
    RecurringGift = _RecurringGift

    class _TicketRequest(_db.Model):
        __tablename__ = 'ticket_requests'
        id = _db.Column(_db.Integer, primary_key=True)
        sport_slug = _db.Column(_db.String(120), nullable=False)
        name = _db.Column(_db.String(150), nullable=False)
        email = _db.Column(_db.String(120), nullable=False)
        match_label = _db.Column(_db.String(200), default='')
        seat_section = _db.Column(_db.String(40), default='General')
        ticket_count = _db.Column(_db.Integer, default=1)
        requested_at = _db.Column(_db.DateTime, default=SNAPSHOT_DT)
    TicketRequest = _TicketRequest


# ─── Seed data tables ─────────────────────────────────────────────────────────

LIBRARY_DATA = [
    ('Doe Memorial Library', 'doe', 'Main Library', 'Doe Building, Memorial Glade', 'Mon-Thu 7am-12am, Fri 7am-10pm, Sat 9am-10pm, Sun 9am-12am', '510-642-3773', 'Elizabeth Dupuis', 1200, 24, 'Bancroft Library, Mark Twain Papers, Free Speech Movement Archive'),
    ('Moffitt Library', 'moffitt', 'Undergraduate', 'Memorial Glade, west of Doe', 'Open 24 hours during term', '510-642-8197', 'Susan Mikkelsen', 700, 12, 'Free Speech Cafe, Digital Humanities Lab'),
    ('Bancroft Library', 'bancroft', 'Special Collections', 'Doe Building, ground floor', 'Mon-Fri 10am-5pm', '510-642-3781', 'Theresa Salazar', 60, 4, 'California regional history, rare books'),
    ('Engineering Library (Kresge)', 'engineering-kresge', 'Subject Library', 'Bechtel Engineering Center, 110', 'Mon-Thu 9am-10pm, Fri 9am-6pm', '510-642-3366', 'Lisa Ngo', 240, 6, 'Engineering standards, IEEE Xplore, ASTM standards'),
    ('Mathematics Statistics Library', 'mathematics-statistics', 'Subject Library', 'Evans Hall, 100', 'Mon-Fri 9am-9pm, Sat 12pm-5pm', '510-642-3381', 'Anna Sackmann', 80, 3, 'Math Reviews print archive'),
    ('Bioscience Library', 'bioscience', 'Subject Library', 'Valley Life Sciences Building', 'Mon-Fri 9am-8pm, Sat 12pm-6pm', '510-642-2531', 'Becky Miller', 200, 5, 'Natural history field journals, marine biology archive'),
    ('Chemistry Chemical Engineering Library', 'chemistry', 'Subject Library', 'Hildebrand Hall, 100', 'Mon-Fri 9am-8pm', '510-643-9444', 'Kenneth Lyons', 150, 4, 'Beilstein Handbook, chemistry patents'),
    ('Earth Sciences Map Library', 'earth-sciences-maps', 'Subject Library', 'McCone Hall, 50', 'Mon-Fri 9am-5pm', '510-642-2997', 'Heiko Mueller', 80, 2, 'USGS topographic maps, climate data, geological surveys'),
    ('Physics Astronomy Library', 'physics-astronomy', 'Subject Library', 'LeConte Hall, 351', 'Mon-Fri 9am-7pm', '510-642-3122', 'Kortney Rupp', 100, 3, 'arXiv preprint archive, observatory logs'),
    ('Optometry Health Sciences Library', 'optometry-health-sciences', 'Subject Library', 'Minor Hall, 490', 'Mon-Fri 9am-5pm', '510-642-1020', 'Eve Saldana', 60, 2, 'Vision science journals, ophthalmology archives'),
    ('Public Health Library', 'public-health', 'Subject Library', 'University Hall, 230', 'Mon-Fri 10am-6pm', '510-642-2510', 'Debbie Jan', 70, 2, 'Epidemiology datasets, WHO reports'),
    ('Social Welfare Library', 'social-welfare', 'Subject Library', 'Haviland Hall, 227', 'Mon-Fri 10am-5pm', '510-642-4432', 'Toni Mendieta', 50, 2, 'Social work case files, policy archives'),
    ('Anthropology Library', 'anthropology', 'Subject Library', 'Kroeber Hall, 230', 'Mon-Fri 10am-7pm', '510-642-2400', 'Christina Velazquez Fidler', 60, 2, 'Ethnographic field notes, anthropology film archive'),
    ('Art History Classics Library', 'art-history-classics', 'Subject Library', 'Doe Building, 308', 'Mon-Fri 10am-7pm', '510-643-2273', 'Lynn Cunningham', 100, 3, 'Greek vase photography, Roman epigraphy archive'),
    ('Architecture Slide Library', 'architecture-slides', 'Subject Library', 'Wurster Hall, 280', 'Mon-Fri 10am-5pm', '510-643-1969', 'Maryly Snow', 40, 1, 'Architectural slide collection, urban planning history'),
    ('East Asian Library', 'east-asian', 'Area Studies', 'Starr Library, opposite Doe', 'Mon-Fri 9am-5pm, Sat 1pm-5pm', '510-642-2556', 'Peter Zhou', 180, 4, 'Chinese rare books, Japanese woodblock prints, Korean dynasty records'),
    ('South Southeast Asia Library', 'south-southeast-asia', 'Area Studies', 'Doe Building, 438', 'Mon-Fri 10am-5pm', '510-642-3095', 'Adnan Malik', 50, 2, 'Sanskrit manuscripts, Tibetan archive'),
    ('Institute of Governmental Studies', 'igs-public-policy', 'Subject Library', 'Moses Hall, 109', 'Mon-Fri 10am-5pm', '510-642-1472', 'Liladhar Pendse', 60, 2, 'California government documents, election archive'),
    ('Music Library', 'music', 'Subject Library', 'Morrison Hall, 240', 'Mon-Fri 9am-6pm', '510-642-2624', 'John Shepard', 80, 3, 'Music manuscripts, Mills College tape archive'),
    ('Northern Regional Library Facility', 'nrlf-storage', 'Storage', 'Richmond Field Station', 'Mon-Fri 9am-4pm, by request', '510-665-4525', 'Emily Stambaugh', 0, 0, 'High-density preservation storage, retrieval by request'),
    ('Berkeley Law Library', 'berkeley-law', 'Professional School', 'Boalt Hall, 1st floor', 'Mon-Fri 8am-11pm', '510-642-4044', 'Karen Beck', 350, 8, 'California legal history, Supreme Court briefs'),
    ('Berkeley Business Library (Long)', 'berkeley-business-long', 'Professional School', 'Haas School, F525', 'Mon-Fri 9am-8pm', '510-642-0370', 'Jim Church', 220, 5, 'Bloomberg terminals, IBISWorld industry reports'),
    ('Education Psychology Library', 'education-psychology', 'Subject Library', 'Tolman Hall, 2600', 'Mon-Fri 10am-6pm', '510-642-4208', 'Brian Quigley', 90, 3, 'Curriculum archive, educational testing collection'),
]

SPORT_DATA = [
    ('Football', 'football', 'Men', 'Fall', 'Justin Wilcox', 'California Memorial Stadium', 110, 5, '6-7 (2024)', 'Big Game vs. Stanford, Nov 22, 2026'),
    ('Basketball (Men)', 'basketball-men', 'Men', 'Winter', 'Mark Madsen', 'Haas Pavilion', 16, 2, '13-19 (2024-25)', 'vs. UCLA, Jan 17, 2027'),
    ('Basketball (Women)', 'basketball-women', 'Women', 'Winter', 'Charmin Smith', 'Haas Pavilion', 14, 0, '19-13 (2024-25)', 'vs. Stanford, Feb 28, 2027'),
    ('Baseball', 'baseball', 'Men', 'Spring', 'Mike Neu', 'Evans Diamond', 35, 2, '32-25 (2024)', 'vs. Oregon State, Apr 11, 2027'),
    ('Softball', 'softball', 'Women', 'Spring', 'Chelsea Spencer', 'Levine-Fricke Field', 22, 1, '34-22 (2024)', 'vs. Washington, May 2, 2027'),
    ('Volleyball', 'volleyball', 'Women', 'Fall', 'Sam Crosson', 'Haas Pavilion', 18, 1, '15-12 (2024)', 'vs. Stanford, Nov 8, 2026'),
    ('Volleyball (Men)', 'volleyball-men', 'Men', 'Spring', 'Sam Crosson', 'Haas Pavilion', 17, 0, '10-15 (2024)', 'vs. UCLA, Mar 14, 2027'),
    ('Soccer (Men)', 'soccer-men', 'Men', 'Fall', 'Leonard Griffin', 'Edwards Stadium', 28, 0, '8-7-3 (2024)', 'vs. Stanford, Oct 26, 2026'),
    ('Soccer (Women)', 'soccer-women', 'Women', 'Fall', 'Erica Walsh', 'Edwards Stadium', 26, 0, '11-6-2 (2024)', 'vs. UCLA, Nov 1, 2026'),
    ('Swimming Diving (Men)', 'swimming-men', 'Men', 'Winter', 'Dave Durden', 'Spieker Aquatics Complex', 32, 4, '7-2 (2024)', 'vs. Stanford, Jan 31, 2027'),
    ('Swimming Diving (Women)', 'swimming-women', 'Women', 'Winter', 'Teri McKeever', 'Spieker Aquatics Complex', 30, 4, '6-3 (2024)', 'NCAA Champs, Mar 18, 2027'),
    ('Water Polo (Men)', 'water-polo-men', 'Men', 'Fall', 'Kirk Everist', 'Spieker Aquatics Complex', 20, 14, '20-7 (2024)', 'vs. Stanford, Nov 15, 2026'),
    ('Water Polo (Women)', 'water-polo-women', 'Women', 'Spring', 'Coralie Simmons', 'Spieker Aquatics Complex', 18, 4, '24-8 (2024)', 'vs. USC, Apr 25, 2027'),
    ('Tennis (Men)', 'tennis-men', 'Men', 'Spring', 'Peter Wright', 'Hellman Tennis Complex', 12, 0, '13-12 (2024)', 'vs. Oregon, Apr 4, 2027'),
    ('Tennis (Women)', 'tennis-women', 'Women', 'Spring', 'Amanda Augustus', 'Hellman Tennis Complex', 10, 0, '17-9 (2024)', 'vs. UCLA, Mar 28, 2027'),
    ('Golf (Men)', 'golf-men', 'Men', 'Spring', 'Walter Chun', 'Tilden Park course', 10, 1, 'T-5 Pac-12', 'Pac-12 Championships, Apr 19, 2027'),
    ('Golf (Women)', 'golf-women', 'Women', 'Spring', 'Nancy McDaniel', 'Tilden Park course', 9, 0, 'T-7 Pac-12', 'Pac-12 Championships, Apr 20, 2027'),
    ('Track Field (Men)', 'track-field-men', 'Men', 'Spring', 'Robyne Johnson', 'Edwards Stadium', 65, 6, '3rd Pac-12 outdoor', 'Pac-12 Outdoor, May 14, 2027'),
    ('Track Field (Women)', 'track-field-women', 'Women', 'Spring', 'Robyne Johnson', 'Edwards Stadium', 62, 2, '5th Pac-12 outdoor', 'Pac-12 Outdoor, May 14, 2027'),
    ('Cross Country (Men)', 'cross-country-men', 'Men', 'Fall', 'Robyne Johnson', 'Strawberry Canyon', 18, 0, '4th Pac-12', 'NCAA West Regional, Nov 13, 2026'),
    ('Cross Country (Women)', 'cross-country-women', 'Women', 'Fall', 'Robyne Johnson', 'Strawberry Canyon', 18, 0, '6th Pac-12', 'NCAA West Regional, Nov 13, 2026'),
    ('Field Hockey', 'field-hockey', 'Women', 'Fall', 'Shellie Onstead', 'Maxwell Family Field', 25, 0, '12-7 (2024)', 'vs. Stanford, Oct 18, 2026'),
    ('Lacrosse', 'lacrosse', 'Women', 'Spring', 'Hilary Bowen', 'Maxwell Family Field', 30, 0, '8-9 (2024)', 'vs. USC, Mar 21, 2027'),
    ('Rugby (Men)', 'rugby-men', 'Men', 'Spring', 'Jack Clark', 'Witter Rugby Field', 50, 28, '13-1 (2024)', 'Varsity Cup Final, May 1, 2027'),
    ('Rugby (Women)', 'rugby-women', 'Women', 'Spring', 'Frankie Sands', 'Witter Rugby Field', 35, 5, '10-3 (2024)', 'CRC Championship, May 8, 2027'),
    ('Rowing (Men)', 'rowing-men', 'Men', 'Spring', 'Mike Teti', 'Briones Reservoir', 70, 16, '1st Pac-12', 'IRA Regatta, May 30, 2027'),
    ('Rowing (Women)', 'rowing-women', 'Women', 'Spring', 'Al Acosta', 'Briones Reservoir', 75, 5, '2nd Pac-12', 'NCAA Champs, May 29, 2027'),
    ('Gymnastics', 'gymnastics', 'Women', 'Winter', 'Justin Howell', 'Haas Pavilion', 17, 0, '8th Pac-12', 'Pac-12 Champs, Mar 21, 2027'),
]

ALUMNI_CHAPTER_DATA = [
    ('San Francisco Bay Area', 'sf-bay-area', 'West Coast', 'USA', 22000, 'Maria Hernandez', 1872, 'Big Game watch party at Local Edition SF, Nov 22 2026'),
    ('Los Angeles', 'los-angeles', 'West Coast', 'USA', 8800, 'Carlos Vega', 1888, 'LA alumni mixer at The Edmon, Sep 18 2026'),
    ('New York City', 'new-york-city', 'East Coast', 'USA', 6400, 'Priya Singh', 1895, 'Wall Street networking breakfast, Oct 7 2026'),
    ('Boston', 'boston', 'East Coast', 'USA', 2900, 'David O\'Brien', 1903, 'Cal vs. Harvard rowing reception, Sep 28 2026'),
    ('Washington DC', 'washington-dc', 'East Coast', 'USA', 3200, 'Rachel Adams', 1925, 'Public policy roundtable on Capitol Hill, Oct 21 2026'),
    ('Chicago', 'chicago', 'Midwest', 'USA', 2700, 'Tariq Johnson', 1928, 'Bears in the Midwest dinner at Maple & Ash, Nov 4 2026'),
    ('Seattle', 'seattle', 'West Coast', 'USA', 4100, 'Hyun Kim', 1932, 'Tech alumni summit at Amazon HQ, Oct 30 2026'),
    ('Portland', 'portland', 'West Coast', 'USA', 1900, 'Anna Wallace', 1948, 'Northwest hike + brunch at Forest Park, Sep 12 2026'),
    ('San Diego', 'san-diego', 'West Coast', 'USA', 3700, 'Esteban Reyes', 1955, 'Beach cleanup volunteer day, Sep 7 2026'),
    ('Sacramento', 'sacramento', 'West Coast', 'USA', 5200, 'Jennifer Park', 1880, 'Capitol policy lunch, Oct 15 2026'),
    ('Houston', 'houston', 'South', 'USA', 1800, 'Marcus Lee', 1962, 'Energy sector mixer at Hotel ZaZa, Oct 23 2026'),
    ('Dallas Fort Worth', 'dallas-fort-worth', 'South', 'USA', 1500, 'Sandra Cole', 1965, 'Texas Bears barbecue, Sep 26 2026'),
    ('Atlanta', 'atlanta', 'South', 'USA', 1200, 'Tyrone Mitchell', 1970, 'Atlanta startup founders panel, Nov 9 2026'),
    ('Miami', 'miami', 'South', 'USA', 900, 'Lucia Fernandez', 1975, 'Brunch at Sweet Liberty, Oct 11 2026'),
    ('Denver', 'denver', 'Mountain', 'USA', 1100, 'Mark Lambert', 1969, 'Hike + happy hour at Red Rocks, Sep 20 2026'),
    ('Phoenix', 'phoenix', 'Mountain', 'USA', 800, 'Kavita Gupta', 1981, 'Desert sunset reception, Oct 4 2026'),
    ('Tokyo', 'tokyo', 'Asia Pacific', 'Japan', 1300, 'Hiroshi Tanaka', 1958, 'Reception at the US Embassy Tokyo, Nov 12 2026'),
    ('London', 'london', 'Europe', 'United Kingdom', 1100, 'Charlotte Wells', 1962, 'High tea at the Goring Hotel, Oct 9 2026'),
    ('Hong Kong', 'hong-kong', 'Asia Pacific', 'Hong Kong', 950, 'Jason Wong', 1980, 'IFC rooftop reception, Nov 18 2026'),
    ('Singapore', 'singapore', 'Asia Pacific', 'Singapore', 720, 'Aisha Tan', 1992, 'Marina Bay networking dinner, Oct 22 2026'),
    ('Beijing', 'beijing', 'Asia Pacific', 'China', 880, 'Liu Wei', 1985, '798 Art District tour, Sep 24 2026'),
    ('Mumbai', 'mumbai', 'Asia Pacific', 'India', 650, 'Vikram Patel', 1990, 'Bombay alumni dinner at the Taj, Nov 6 2026'),
    ('Mexico City', 'mexico-city', 'Latin America', 'Mexico', 540, 'Diego Morales', 1972, 'Roma Norte cocktails, Oct 17 2026'),
    ('Sydney', 'sydney', 'Asia Pacific', 'Australia', 460, 'Olivia Brennan', 1988, 'Harbor brunch reception, Nov 1 2026'),
    ('Paris', 'paris', 'Europe', 'France', 380, 'Camille Dubois', 1995, 'Champ de Mars picnic, Sep 14 2026'),
]

GIVING_FUND_DATA = [
    ('Berkeley Annual Fund', 'annual-fund', 'General Support', 5000000, 4200000, 12000, 'Top Priority', 'Unrestricted gifts that the Chancellor directs to the campus\'s highest-priority needs each year.', 'Supports student emergency grants, faculty start-ups, and renovation projects with the greatest impact.'),
    ('Undergraduate Scholarship Fund', 'undergrad-scholarship', 'Student Aid', 8000000, 6300000, 9400, 'Top Priority', 'Endowed scholarships supporting need-based aid for California undergraduates.', 'Each $25,000 endowed scholarship funds one student in perpetuity.'),
    ('Graduate Fellowship Fund', 'graduate-fellowship', 'Student Aid', 6000000, 4800000, 5200, 'Top Priority', 'Multi-year fellowships for PhD students across disciplines.', 'Five-year fellowships at $42,000/year secure top doctoral candidates.'),
    ('First Generation Initiative', 'first-gen-initiative', 'Student Aid', 3000000, 2100000, 4800, 'High', 'Mentorship, summer-bridge programming, and emergency funds for first-generation students.', '40% of Berkeley undergraduates are first-generation; this fund covers wrap-around support.'),
    ('Library Endowment', 'library-endowment', 'Library', 2500000, 1900000, 3300, 'High', 'Acquisitions endowment for special collections and digital access.', 'Sustains subscriptions to JSTOR, Bloomberg, and Lexis-Nexis for all 23 branch libraries.'),
    ('Doe Library Restoration', 'doe-library-restoration', 'Library', 4000000, 1700000, 880, 'Standard', 'Seismic and HVAC upgrades to the 1911 Doe Memorial Library.', 'Preserves the 1.2 million volume collection and the iconic North Reading Room.'),
    ('Climate Equity Fund', 'climate-equity', 'Research', 10000000, 7500000, 6700, 'Top Priority', 'Interdisciplinary research at the intersection of climate, justice, and policy.', 'Funds 25 graduate researchers across 8 departments studying climate adaptation.'),
    ('Berkeley AI Research Fund', 'ai-research', 'Research', 12000000, 8800000, 4400, 'Top Priority', 'Supports BAIR Lab faculty research, GPU compute, and open-source tooling.', 'Open-sources research from Pieter Abbeel, Stuart Russell, and Sergey Levine\'s labs.'),
    ('Cancer Research Initiative', 'cancer-research', 'Research', 7500000, 5200000, 3800, 'High', 'Translational cancer biology research at the Helen Diller Family Comprehensive Cancer Center partnership.', 'Funds early-detection screening research and immunotherapy clinical trials.'),
    ('Athletics Excellence Fund', 'athletics-excellence', 'Athletics', 4500000, 3100000, 8200, 'Standard', 'Scholarships, training facilities, and travel for 30 varsity sports.', 'Equips student-athletes with academic tutoring and sports medicine resources.'),
    ('Memorial Stadium Endowment', 'memorial-stadium-endowment', 'Athletics', 6000000, 4400000, 5500, 'Standard', 'Maintains the seismic retrofit of Memorial Stadium and the Simpson Center.', 'Protects the home of Cal Football for future generations.'),
    ('Cal Performances Endowment', 'cal-performances', 'Arts', 2000000, 1300000, 2100, 'Standard', 'Brings world-class music, dance, and theater to Zellerbach Hall.', 'Subsidizes student tickets to $10 for major touring productions.'),
    ('Botanical Garden Conservation', 'botanical-garden', 'Public Service', 1500000, 980000, 1700, 'Standard', 'Plant conservation, accessible trails, and youth education at the UC Botanical Garden.', 'Stewards over 13,000 plant species, including 7 California natives at risk of extinction.'),
    ('Public Service Internship Fund', 'public-service-internships', 'Student Aid', 2200000, 1500000, 2600, 'High', 'Stipends for undergraduates pursuing unpaid public-service internships.', 'Underwrites $5,000 stipends for 300 students each summer.'),
    ('Disabled Students Program', 'disabled-students-program', 'Student Aid', 1800000, 1200000, 1900, 'High', 'Adaptive technology, sign language interpreters, and accessibility consulting.', 'Supports 2,400+ students with disabilities annually.'),
]

LEADER_DATA = [
    ('Rich Lyons', 'rich-lyons', 'Chancellor', 'Chancellor Office', 2024, 'Rich Lyons is the 12th Chancellor of UC Berkeley, the first alumnus to lead Berkeley as Chancellor. He previously served as Berkeley\'s Chief Innovation and Entrepreneurship Officer and as Dean of Haas School of Business.', 'chancellor@berkeley.edu', '510-642-7464', 'Equity and access, climate, innovation'),
    ('Benjamin Hermalin', 'benjamin-hermalin', 'Executive Vice Chancellor and Provost', 'Provost Office', 2023, 'Ben Hermalin is the chief academic officer responsible for budget, academic personnel, and operations.', 'evcp@berkeley.edu', '510-642-1961', 'Faculty excellence, academic budget, undergraduate education'),
    ('Stephen Sutton', 'stephen-sutton', 'Vice Chancellor for Student Affairs', 'Student Affairs', 2022, 'Stephen Sutton oversees student housing, dining, wellness, career services, and the dean of students office.', 'vcsa@berkeley.edu', '510-642-5212', 'Mental health, basic needs, student belonging'),
    ('Marc Fisher', 'marc-fisher', 'Vice Chancellor for Administration', 'Administration', 2021, 'Marc Fisher leads campus operations including facilities, capital projects, transportation, real estate, and emergency management.', 'admin@berkeley.edu', '510-642-6190', 'Sustainability operations, deferred maintenance, public safety'),
    ('Dania Matos', 'dania-matos', 'Vice Chancellor for Equity Inclusion', 'Equity Inclusion', 2022, 'Dania Matos leads diversity, equity, inclusion, and belonging across Berkeley\'s academic, administrative, and student-facing operations.', 'equity@berkeley.edu', '510-642-2795', 'Anti-racism strategy, faculty diversity, racial healing'),
    ('Khira Griscavage', 'khira-griscavage', 'Vice Chancellor for Research', 'Research', 2024, 'Khira Griscavage manages Berkeley\'s sponsored research enterprise, including 16 organized research units and the partnership with three national labs.', 'vcr@berkeley.edu', '510-642-8771', 'Research integrity, federal funding strategy, lab partnerships'),
    ('Julie Hooper', 'julie-hooper', 'Vice Chancellor for Communications', 'Communications', 2023, 'Julie Hooper leads marketing, public affairs, news, and brand strategy for the campus.', 'comms@berkeley.edu', '510-642-3734', 'Public narrative, brand visibility, crisis communications'),
    ('Hilary Brown', 'hilary-brown', 'Vice Chancellor for University Development Alumni Relations', 'Development', 2021, 'Hilary Brown leads fundraising and alumni engagement, including the Bear Necessities campaign for student support.', 'udar@berkeley.edu', '510-642-1212', 'Annual fund, planned giving, alumni engagement'),
    ('David Robinson', 'david-robinson', 'Chief Financial Officer', 'Finance', 2020, 'David Robinson oversees finance, budget, controller, and treasury operations.', 'cfo@berkeley.edu', '510-642-2127', 'Long-term budget, tuition policy, capital reserves'),
    ('Yvette Gullatt', 'yvette-gullatt', 'Vice Chancellor for Graduate Postdoctoral Studies', 'Graduate Division', 2022, 'Yvette Gullatt leads policy, admissions, and student services for over 12,000 graduate students.', 'gradservices@berkeley.edu', '510-642-7332', 'Graduate funding, postdoc career outcomes, diversity in graduate education'),
    ('Cathy Koshland', 'cathy-koshland', 'Faculty Athletics Representative', 'Athletics', 2019, 'Cathy Koshland represents the faculty on athletics matters, including academic eligibility and student-athlete welfare.', 'far@berkeley.edu', '510-642-3122', 'Student-athlete academics, NCAA compliance, name image likeness'),
    ('Yuriko Liu', 'yuriko-liu', 'Dean of the Library', 'Library', 2023, 'Yuriko Liu leads the 23-branch Berkeley Library system serving the entire UC system.', 'library-dean@berkeley.edu', '510-642-3773', 'Open access publishing, special collections preservation, digital scholarship'),
    ('Kathleen Frydl', 'kathleen-frydl', 'Vice Provost for Undergraduate Education', 'Undergraduate Education', 2024, 'Kathleen Frydl leads undergraduate curriculum, advising, the L&S College Writing Programs, and academic engagement.', 'vpue@berkeley.edu', '510-642-8378', 'Reading rhetoric, mentoring, transfer student success'),
    ('Bernard Lubega', 'bernard-lubega', 'Chief Information Officer', 'Information Technology', 2023, 'Bernard Lubega leads campus IT, including the integration of generative AI tools across campus operations.', 'cio@berkeley.edu', '510-642-3434', 'AI in administration, cybersecurity, network reliability'),
    ('Linda Rugg', 'linda-rugg', 'Associate Vice Chancellor for Research', 'Research', 2021, 'Linda Rugg leads research compliance, intellectual property, and the Berkeley research enterprise risk function.', 'avc-research@berkeley.edu', '510-643-7008', 'Research ethics, open science, faculty integrity'),
]

STUDENT_SERVICE_DATA = [
    ('University Health Services', 'health-services', 'Wellness', 'Tang Center, 2222 Bancroft Way', '510-642-2000', 'Mon-Fri 8am-5pm, urgent care 24/7', True, 'Free with SHIP, sliding scale otherwise', 'Primary care, mental health, urgent care, vaccinations, sexual health and pharmacy services for all students.'),
    ('Counseling Psychological Services', 'cps', 'Mental Health', 'Tang Center, 3rd floor', '510-642-9494', 'Mon-Fri 8am-5pm, crisis line 24/7', True, 'Free', 'Individual and group therapy, crisis support, psychiatric services, and outreach for student well-being.'),
    ('Disabled Students Program', 'dsp', 'Accessibility', '260 Cesar Chavez Center', '510-642-0518', 'Mon-Fri 8:30am-4:30pm', True, 'Free', 'Accommodations including note-takers, alternate-format texts, assistive technology, and exam proctoring.'),
    ('Career Center', 'career-center', 'Career', '2440 Bancroft Way', '510-642-1716', 'Mon-Fri 9am-5pm', False, 'Free', 'Job-search support, resume review, interview prep, employer events, and graduate-school counseling.'),
    ('Cal Dining', 'cal-dining', 'Food', 'Crossroads Dining Commons', '510-642-3811', 'Multiple dining halls, 7am-9pm', False, 'Meal plan or pay-as-you-go', 'On-campus dining with locally sourced food across 5 residential dining commons and 12 campus cafes.'),
    ('Cal Housing', 'cal-housing', 'Housing', '2610 Channing Way', '510-642-4108', 'Mon-Fri 9am-5pm', True, 'Varies by unit', 'On-campus residence halls, theme houses, family student housing, and off-campus housing referrals.'),
    ('Recreational Sports Facility', 'recsports', 'Recreation', 'RSF Building, Bancroft & Dana', '510-642-7796', '6am-11pm daily during term', False, 'Free for students', 'Two pools, fitness studios, climbing wall, group exercise, intramural sports, and outdoor adventure programs.'),
    ('Basic Needs Center', 'basic-needs', 'Wellness', '432 Eshleman Hall', '510-664-7050', 'Mon-Fri 10am-4pm', False, 'Free', 'Food pantry, emergency grants, CalFresh enrollment, and housing security advocacy for students in need.'),
    ('Ombuds Office', 'ombuds', 'Conflict Resolution', '102 Sproul Hall', '510-642-7823', 'Mon-Fri 9am-5pm', True, 'Free', 'Confidential, neutral consultation for conflicts with faculty, staff, or peers, plus problem-solving coaching.'),
    ('Office of the Registrar', 'registrar', 'Academic Services', '120 Sproul Hall', '510-664-9181', 'Mon-Fri 9am-12pm and 1pm-4pm', False, 'Free', 'Course enrollment, transcripts, diplomas, residency classification, and federal verification reports.'),
    ('PATH to Care Center', 'path-to-care', 'Support', '5 Durant Hall', '510-642-1988', 'Mon-Fri 8:30am-5pm, urgent line 24/7', True, 'Free', 'Confidential support for survivors of sexual violence, sexual harassment, dating violence, and stalking.'),
    ('Berkeley International Office', 'international-office', 'International', '1608 Fourth Street', '510-642-2818', 'Mon-Fri 8:30am-4:30pm', True, 'Free for F-1/J-1 students', 'Immigration advising, employment authorization, OPT/CPT support, and orientation for international students.'),
]

FINANCIAL_AID_DATA = [
    ('Cal Grant A', 'cal-grant-a', 'State Grant', 13752, 'Apr 1, 2027 (FAFSA + CADAA)', 'California resident, US citizen or eligible non-citizen, GPA 3.0+, family income below state cap.', True, 'Annual tuition grant for California residents at UC Berkeley, renewable for up to 4 years.'),
    ('Cal Grant B', 'cal-grant-b', 'State Grant', 17672, 'Apr 1, 2027 (FAFSA + CADAA)', 'California resident, family income below state low-income cap, GPA 2.0+.', True, 'Living-expense grant plus tuition support for very low-income California undergraduates.'),
    ('Pell Grant', 'pell-grant', 'Federal Grant', 7395, 'Mar 1, 2027 (FAFSA)', 'Demonstrated financial need, US citizen or eligible non-citizen, enrolled at least half-time.', True, 'Need-based federal grant for undergraduate students without a prior bachelor\'s degree.'),
    ('University Grant', 'university-grant', 'Institutional', 25000, 'Mar 1, 2027 (FAFSA + CADAA)', 'Demonstrated financial need beyond Pell and Cal Grant coverage.', True, 'Berkeley\'s institutional grant covering remaining need after federal and state aid.'),
    ('Middle Class Scholarship', 'middle-class-scholarship', 'State Grant', 5000, 'Mar 2, 2027 (CSAC)', 'California family income up to $217,000, US citizen, undergraduate at UC or CSU.', True, 'Helps middle-income California families offset tuition at UC and CSU campuses.'),
    ('Federal Work-Study', 'work-study', 'Work Award', 4500, 'Mar 1, 2027 (FAFSA)', 'Demonstrated financial need, US citizen or eligible non-citizen.', True, 'Part-time campus employment subsidized through federal work-study funds.'),
    ('Berkeley Undergraduate Dream Act', 'dream-act-aid', 'Institutional', 22000, 'Mar 2, 2027 (CADAA)', 'AB540 and CA Dream Act eligible undergraduate, demonstrated need.', True, 'Need-based institutional aid for AB540-eligible undocumented California students.'),
    ('Direct Subsidized Loan', 'subsidized-loan', 'Federal Loan', 5500, 'Mar 1, 2027 (FAFSA)', 'Undergraduate, demonstrated financial need, US citizen or eligible non-citizen.', False, 'Need-based federal loan with no interest while enrolled at least half-time.'),
    ('Direct Unsubsidized Loan', 'unsubsidized-loan', 'Federal Loan', 12500, 'Mar 1, 2027 (FAFSA)', 'Enrolled at least half-time, US citizen or eligible non-citizen.', False, 'Federal loan available regardless of need; interest accrues during enrollment.'),
    ('Berkeley Promise Scholarship', 'berkeley-promise', 'Institutional', 10000, 'Mar 2, 2027 (FAFSA + CADAA)', 'First-generation California resident with family income below $80,000.', True, 'Top-up grant for first-generation low-income California students at Berkeley.'),
]

NEWS_CATEGORY_HUB_DATA = [
    ('research', 'Research News', 'Discoveries from Berkeley\'s 16 organized research units and partner national labs.', 'A weekly look at breakthroughs in AI, climate, biomedicine, and the physical sciences.'),
    ('campus-life', 'Campus Life', 'Stories from Sproul Plaza, the residence halls, and across the 1,232-acre campus.', 'Student perspectives on life at Berkeley, from move-in week to Big Game traditions.'),
    ('faculty', 'Faculty Spotlight', 'Profiles of Berkeley\'s 1,629 senate faculty and 4,500 other instructors.', 'Faculty news, awards, retirements, and the research that shapes Berkeley\'s reputation.'),
    ('student', 'Student Stories', 'Voices and accomplishments of Berkeley\'s 44,000 undergraduate and graduate students.', 'First-generation grads, student athletes, undergraduate researchers, and everything in between.'),
    ('athletics', 'Athletics News', 'Updates from Cal\'s 30 varsity programs and 105 NCAA national titles.', 'Game recaps, recruiting news, and stories from the Cal Athletics community.'),
    ('science', 'Science Discoveries', 'Major findings from Berkeley\'s physical, biological, and computational sciences.', 'Long-form features on Berkeley science from the editors of UC Berkeley News.'),
    ('arts', 'Arts Culture', 'Coverage of BAMPFA, Cal Performances, the Hearst Museum, and student arts.', 'Reviews, interviews, and previews from Berkeley\'s rich arts scene.'),
    ('alumni', 'Alumni News', 'Profiles of Berkeley\'s 600,000 alumni making impact around the world.', 'Alumni accomplishments, reunions, and the Cal Alumni Association.'),
    ('global', 'Global Berkeley', 'Berkeley\'s research and partnerships across 100+ countries.', 'International perspectives, study abroad, and Berkeley\'s global research footprint.'),
    ('equity', 'Equity Inclusion', 'Berkeley\'s work on access, diversity, equity, inclusion, and belonging.', 'Stories about Berkeley\'s journey toward a more equitable campus and society.'),
]


def seed_extras():
    """Populate new tables idempotently. Called from app.py after main seed."""
    if Library.query.first():
        return

    # Libraries
    for row in LIBRARY_DATA:
        name, slug, branch_type, location, hours, phone, librarian, seat, room, special = row
        l = Library(name=name, slug=slug, branch_type=branch_type, location=location,
                    hours=hours, phone=phone, librarian=librarian, seat_count=seat,
                    room_count=room, special_collections=special, photo=library_photo(slug),
                    description=f"{name} is part of UC Berkeley's 23-branch library system. {special}.")
        db.session.add(l)

    # Sports
    for row in SPORT_DATA:
        name, slug, gender, season, coach, venue, roster, titles, record, next_m = row
        s = Sport(name=name, slug=slug, gender=gender, season=season, head_coach=coach,
                  home_venue=venue, roster_size=roster, national_titles=titles,
                  last_season_record=record, next_match=next_m,
                  banner_photo=sport_real_photo(slug),
                  description=f"Cal {name} competes in the Pac-12 Conference. Head Coach {coach} leads {roster} student-athletes at {venue}.")
        db.session.add(s)

    # Alumni chapters
    for row in ALUMNI_CHAPTER_DATA:
        name, slug, region, country, members, pres, founded, next_e = row
        c = AlumniChapter(name=name, slug=slug, region=region, country=country,
                          members_count=members, president=pres, founded_year=founded,
                          next_event=next_e, photo=chapter_real_photo(slug),
                          description=f"The {name} chapter brings together {members:,} Berkeley alumni in the region. President {pres} leads a volunteer board of 12 alumni.")
        db.session.add(c)

    # Giving funds
    for row in GIVING_FUND_DATA:
        name, slug, cat, target, raised, donors, priority, desc, impact = row
        f = GivingFund(name=name, slug=slug, category=cat, target_amount=target,
                       raised_amount=raised, donor_count=donors, priority=priority,
                       description=desc, impact_statement=impact,
                       photo=fund_real_photo(slug))
        db.session.add(f)

    # Leadership
    for row in LEADER_DATA:
        name, slug, title, office, appointed, bio, email, phone, priorities = row
        l = Leader(name=name, slug=slug, title=title, office=office,
                   appointed_year=appointed, bio=bio, email=email, phone=phone,
                   priorities=priorities, headshot=headshot_photo(slug))
        db.session.add(l)

    # Student services
    for row in STUDENT_SERVICE_DATA:
        name, slug, cat, loc, phone, hours, appt, cost, desc = row
        s = StudentService(name=name, slug=slug, category=cat, location=loc,
                           phone=phone, hours=hours, appointment_required=appt,
                           cost=cost, description=desc, photo=campus_photo(slug))
        db.session.add(s)

    # Financial aid programs
    for row in FINANCIAL_AID_DATA:
        name, slug, cat, amt, deadline, elig, renew, desc = row
        p = FinancialAidProgram(name=name, slug=slug, category=cat, max_amount=amt,
                                application_deadline=deadline, eligibility=elig,
                                renewable=renew, description=desc, photo=fund_photo(slug))
        db.session.add(p)

    # News category hubs
    for row in NEWS_CATEGORY_HUB_DATA:
        slug, name, tagline, desc = row
        hub = NewsCategoryHub(slug=slug, name=name, tagline=tagline, description=desc,
                              banner_photo=banner_photo(slug),
                              editor=f"{name} Editorial Team")
        db.session.add(hub)

    db.session.commit()


# ─── Routes ──────────────────────────────────────────────────────────────────

def register(_app, _db):
    """Wire models, routes, and seed into the host Flask app."""
    global app, db
    app = _app
    db = _db
    _define_models(_db)

    # Read existing models from the host app
    from app import (College, Department, Program, NewsArticle, Event,
                     ResearchCenter, Faculty, User, Bookmark)

    # ── GET hubs ────────────────────────────────────────────────────────────

    @_app.route('/library')
    def library_index():
        libs = Library.query.order_by(Library.name).all()
        return render_template('library.html', libraries=libs)

    @_app.route('/library/<slug>')
    def library_branch(slug):
        lib = Library.query.filter_by(slug=slug).first_or_404()
        siblings = Library.query.filter(Library.id != lib.id).order_by(Library.name).limit(6).all()
        return render_template('library_branch.html', lib=lib, siblings=siblings)

    @_app.route('/library/<slug>/reserve', methods=['GET', 'POST'])
    def library_reserve(slug):
        lib = Library.query.filter_by(slug=slug).first_or_404()
        if request.method == 'POST':
            r = LibraryReservation(
                library_slug=slug,
                name=request.form.get('name', '').strip(),
                email=request.form.get('email', '').strip(),
                room_type=request.form.get('room_type', 'Study Room'),
                reserve_date=request.form.get('reserve_date', ''),
                time_slot=request.form.get('time_slot', ''),
                group_size=int(request.form.get('group_size', 1) or 1),
            )
            db.session.add(r)
            db.session.commit()
            flash(f'Reservation submitted for {lib.name}. Confirmation #{r.id} sent to {r.email}.', 'success')
            return redirect(url_for('library_branch', slug=slug))
        return render_template('library_reserve.html', lib=lib)

    @_app.route('/athletics')
    def athletics_index():
        sports = Sport.query.order_by(Sport.name).all()
        return render_template('athletics.html', sports=sports)

    @_app.route('/athletics/cal-bears')
    def athletics_cal_bears():
        sports = Sport.query.order_by(Sport.national_titles.desc(), Sport.name).all()
        total_titles = sum(s.national_titles for s in sports)
        return render_template('athletics_cal_bears.html', sports=sports, total_titles=total_titles)

    @_app.route('/athletics/team/<slug>')
    def athletics_team(slug):
        sp = Sport.query.filter_by(slug=slug).first_or_404()
        in_season = Sport.query.filter(Sport.season == sp.season, Sport.id != sp.id).limit(6).all()
        return render_template('athletics_team.html', sp=sp, in_season=in_season)

    @_app.route('/athletics/team/<slug>/tickets', methods=['GET', 'POST'])
    def athletics_tickets(slug):
        sp = Sport.query.filter_by(slug=slug).first_or_404()
        if request.method == 'POST':
            r = TicketRequest(
                sport_slug=slug,
                name=request.form.get('name', '').strip(),
                email=request.form.get('email', '').strip(),
                match_label=request.form.get('match_label', sp.next_match),
                seat_section=request.form.get('seat_section', 'General'),
                ticket_count=int(request.form.get('ticket_count', 1) or 1),
            )
            db.session.add(r)
            db.session.commit()
            flash(f'Ticket request submitted for {sp.name}. Confirmation #{r.id}.', 'success')
            return redirect(url_for('athletics_team', slug=slug))
        return render_template('athletics_tickets.html', sp=sp)

    @_app.route('/alumni')
    def alumni_index():
        chapters = AlumniChapter.query.order_by(AlumniChapter.members_count.desc()).all()
        total_members = sum(c.members_count for c in chapters)
        return render_template('alumni.html', chapters=chapters, total_members=total_members)

    @_app.route('/alumni/chapter/<slug>')
    def alumni_chapter(slug):
        ch = AlumniChapter.query.filter_by(slug=slug).first_or_404()
        siblings = AlumniChapter.query.filter(AlumniChapter.region == ch.region,
                                              AlumniChapter.id != ch.id).limit(6).all()
        return render_template('alumni_chapter.html', ch=ch, siblings=siblings)

    @_app.route('/alumni/update-profile', methods=['GET', 'POST'])
    def alumni_update_profile():
        if request.method == 'POST':
            u = AlumniDirectoryUpdate(
                name=request.form.get('name', '').strip(),
                email=request.form.get('email', '').strip(),
                grad_year=int(request.form.get('grad_year', 2020) or 2020),
                employer=request.form.get('employer', ''),
                position=request.form.get('position', ''),
                city=request.form.get('city', ''),
            )
            db.session.add(u)
            db.session.commit()
            flash(f'Alumni directory updated for {u.name}. Thank you!', 'success')
            return redirect(url_for('alumni_index'))
        return render_template('alumni_update.html')

    @_app.route('/giving')
    def giving_index():
        funds = GivingFund.query.order_by(GivingFund.raised_amount.desc()).all()
        total_raised = sum(f.raised_amount for f in funds)
        total_donors = sum(f.donor_count for f in funds)
        return render_template('giving.html', funds=funds, total_raised=total_raised,
                               total_donors=total_donors)

    @_app.route('/giving/<slug>')
    def giving_fund(slug):
        f = GivingFund.query.filter_by(slug=slug).first_or_404()
        related = GivingFund.query.filter(GivingFund.category == f.category,
                                          GivingFund.id != f.id).limit(4).all()
        progress_pct = int(100 * f.raised_amount / max(f.target_amount, 1))
        return render_template('giving_fund.html', fund=f, related=related,
                               progress_pct=progress_pct)

    @_app.route('/giving/<slug>/donate', methods=['GET', 'POST'])
    def giving_donate(slug):
        f = GivingFund.query.filter_by(slug=slug).first_or_404()
        if request.method == 'POST':
            d = Donation(
                donor_name=request.form.get('donor_name', '').strip(),
                email=request.form.get('email', '').strip(),
                fund_slug=slug,
                amount=int(request.form.get('amount', 100) or 100),
                is_anonymous=request.form.get('is_anonymous') == '1',
                message=request.form.get('message', ''),
            )
            db.session.add(d)
            db.session.commit()
            flash(f'Thank you, {d.donor_name}! Your gift of ${d.amount} to {f.name} was received.', 'success')
            return redirect(url_for('giving_fund', slug=slug))
        return render_template('giving_donate.html', fund=f)

    @_app.route('/giving/recurring/setup', methods=['GET', 'POST'])
    def giving_recurring():
        funds = GivingFund.query.order_by(GivingFund.name).all()
        if request.method == 'POST':
            g = RecurringGift(
                donor_name=request.form.get('donor_name', '').strip(),
                email=request.form.get('email', '').strip(),
                fund_slug=request.form.get('fund_slug', 'annual-fund'),
                monthly_amount=int(request.form.get('monthly_amount', 50) or 50),
                start_date=request.form.get('start_date', ''),
            )
            db.session.add(g)
            db.session.commit()
            flash(f'Recurring monthly gift of ${g.monthly_amount} to {g.fund_slug} has been set up.', 'success')
            return redirect(url_for('giving_index'))
        return render_template('giving_recurring.html', funds=funds)

    @_app.route('/about/leadership')
    def leadership_index():
        leaders = Leader.query.order_by(Leader.appointed_year).all()
        return render_template('leadership.html', leaders=leaders)

    @_app.route('/about/leadership/<slug>')
    def leader_profile(slug):
        l = Leader.query.filter_by(slug=slug).first_or_404()
        colleagues = Leader.query.filter(Leader.office == l.office,
                                         Leader.id != l.id).limit(4).all()
        return render_template('leader_profile.html', leader=l, colleagues=colleagues)

    @_app.route('/about/diversity')
    def diversity():
        leaders = Leader.query.filter(Leader.office.in_(['Equity Inclusion', 'Student Affairs'])).all()
        return render_template('diversity.html', leaders=leaders)

    @_app.route('/students')
    def students_index():
        services = StudentService.query.order_by(StudentService.category, StudentService.name).all()
        categories = sorted(set(s.category for s in services))
        return render_template('students.html', services=services, categories=categories)

    @_app.route('/students/<slug>')
    def student_service(slug):
        s = StudentService.query.filter_by(slug=slug).first_or_404()
        related = StudentService.query.filter(StudentService.category == s.category,
                                              StudentService.id != s.id).limit(4).all()
        return render_template('student_service.html', service=s, related=related)

    @_app.route('/financial-aid')
    def financial_aid_index():
        progs = FinancialAidProgram.query.order_by(FinancialAidProgram.max_amount.desc()).all()
        return render_template('financial_aid.html', programs=progs)

    @_app.route('/financial-aid/forms')
    def financial_aid_forms():
        forms = [
            {'name': 'FAFSA', 'slug': 'fafsa', 'deadline': 'March 2, 2027', 'description': 'Free Application for Federal Student Aid; required for all federal and most institutional need-based aid.', 'audience': 'US citizens and eligible non-citizens'},
            {'name': 'California Dream Act Application', 'slug': 'cadaa', 'deadline': 'March 2, 2027', 'description': 'For AB540 students not eligible for FAFSA; opens access to Cal Grant and Berkeley Dream Act aid.', 'audience': 'AB540-eligible California students'},
            {'name': 'CSS Profile (graduate only)', 'slug': 'css-profile', 'deadline': 'February 15, 2027', 'description': 'Used by select Berkeley graduate professional schools for non-federal aid.', 'audience': 'Graduate students at participating schools'},
            {'name': 'Berkeley Need-Based Grant Verification', 'slug': 'need-verification', 'deadline': 'May 15, 2027', 'description': 'Submitted after FAFSA when Berkeley requests household documentation.', 'audience': 'Selected for verification by Berkeley Financial Aid'},
            {'name': 'Special Circumstance Petition', 'slug': 'special-circumstance', 'deadline': 'Rolling', 'description': 'For changes in family income, medical bills, or non-recurring expenses since FAFSA filing.', 'audience': 'Continuing students with new financial hardships'},
            {'name': 'Cal Grant GPA Verification', 'slug': 'cal-grant-gpa', 'deadline': 'March 2, 2027', 'description': 'Submitted by the high-school or community college to certify GPA for Cal Grant eligibility.', 'audience': 'New California undergraduates'},
        ]
        return render_template('financial_aid_forms.html', forms=forms)

    @_app.route('/financial-aid/cost-calculator')
    def financial_aid_calculator():
        # Reference cost-of-attendance numbers
        coa = {
            'in_state_tuition': 14250,
            'out_of_state_tuition': 46324,
            'housing_dining': 19438,
            'books_supplies': 1330,
            'transportation': 1192,
            'personal': 2208,
            'health_insurance': 4716,
        }
        return render_template('financial_aid_calculator.html', coa=coa)

    @_app.route('/financial-aid/apply', methods=['GET', 'POST'])
    def financial_aid_apply():
        progs = FinancialAidProgram.query.order_by(FinancialAidProgram.name).all()
        if request.method == 'POST':
            s = ScholarshipApplication(
                program_slug=request.form.get('program_slug', 'cal-grant-a'),
                applicant_name=request.form.get('applicant_name', '').strip(),
                email=request.form.get('email', '').strip(),
                statement=request.form.get('statement', ''),
                amount_requested=int(request.form.get('amount_requested', 5000) or 5000),
                gpa=request.form.get('gpa', ''),
            )
            db.session.add(s)
            db.session.commit()
            flash(f'Application submitted for {s.program_slug}. Confirmation #{s.id} sent to {s.email}.', 'success')
            return redirect(url_for('financial_aid_index'))
        return render_template('financial_aid_apply.html', programs=progs)

    @_app.route('/admissions/undergrad')
    def admissions_undergrad():
        progs = Program.query.filter(Program.degree_type.in_(['BA', 'BS'])).limit(20).all()
        return render_template('admissions_undergrad.html', programs=progs)

    @_app.route('/admissions/grad')
    def admissions_grad():
        progs = Program.query.filter(Program.degree_type.in_(['MA', 'MS', 'PhD', 'MPH', 'MBA', 'MEng', 'JD', 'MD'])).limit(20).all()
        return render_template('admissions_grad.html', programs=progs)

    @_app.route('/admissions/transfer')
    def admissions_transfer():
        return render_template('admissions_transfer.html')

    @_app.route('/admissions/international')
    def admissions_international():
        return render_template('admissions_international.html')

    @_app.route('/admissions/apply', methods=['GET', 'POST'])
    def admissions_apply():
        progs = Program.query.order_by(Program.name).limit(60).all()
        if request.method == 'POST':
            sub = ApplicationSubmission(
                applicant_name=request.form.get('applicant_name', '').strip(),
                email=request.form.get('email', '').strip(),
                program_slug=request.form.get('program_slug', ''),
                admission_level=request.form.get('admission_level', 'undergrad'),
                statement=request.form.get('statement', ''),
                gpa=request.form.get('gpa', ''),
                residency=request.form.get('residency', 'in-state'),
            )
            db.session.add(sub)
            db.session.commit()
            flash(f'Application submitted! Confirmation #{sub.id} sent to {sub.email}. You will hear back by March 2027.', 'success')
            return redirect(url_for('admissions'))
        return render_template('admissions_apply.html', programs=progs)

    @_app.route('/admissions/visit', methods=['GET', 'POST'])
    def admissions_visit():
        if request.method == 'POST':
            t = TourBooking(
                name=request.form.get('name', '').strip(),
                email=request.form.get('email', '').strip(),
                tour_date=request.form.get('tour_date', ''),
                tour_type=request.form.get('tour_type', 'Campus Walk'),
                group_size=int(request.form.get('group_size', 1) or 1),
                notes=request.form.get('notes', ''),
            )
            db.session.add(t)
            db.session.commit()
            flash(f'Tour booked for {t.tour_date}. Confirmation #{t.id} sent to {t.email}.', 'success')
            return redirect(url_for('admissions_visit'))
        return render_template('admissions_visit.html')

    @_app.route('/admissions/request-info', methods=['GET', 'POST'])
    def admissions_request_info():
        if request.method == 'POST':
            g = GeneralContact(
                name=request.form.get('name', '').strip(),
                email=request.form.get('email', '').strip(),
                topic='Admissions Info Request',
                message=request.form.get('message', ''),
            )
            db.session.add(g)
            db.session.commit()
            flash(f'Information request sent. We will email {g.email} within 3 business days.', 'success')
            return redirect(url_for('admissions'))
        return render_template('admissions_request_info.html')

    @_app.route('/news/category/<slug>')
    def news_category(slug):
        hub = NewsCategoryHub.query.filter_by(slug=slug).first_or_404()
        # match against NewsArticle.category by humanized name fallback
        cat_name = hub.name.replace(' News', '').replace(' Stories', '').replace(' Spotlight', '').replace(' Culture', '').replace(' Inclusion', '').replace(' Discoveries', '').strip()
        articles = NewsArticle.query.filter(NewsArticle.category.ilike(f'%{cat_name}%'))\
            .order_by(NewsArticle.published_date.desc()).limit(24).all()
        return render_template('news_category.html', hub=hub, articles=articles)

    @_app.route('/events/<int:event_id>/rsvp', methods=['GET', 'POST'])
    def event_rsvp(event_id):
        ev = db.session.get(Event, event_id) or abort(404)
        if request.method == 'POST':
            r = EventRSVP(
                event_id=event_id,
                name=request.form.get('name', '').strip(),
                email=request.form.get('email', '').strip(),
                guest_count=int(request.form.get('guest_count', 1) or 1),
                dietary=request.form.get('dietary', ''),
                accessibility=request.form.get('accessibility', ''),
            )
            db.session.add(r)
            db.session.commit()
            flash(f'RSVP confirmed for "{ev.title}". See you on {ev.start_datetime.strftime("%b %d, %Y")}.', 'success')
            return redirect(url_for('event_detail', event_id=event_id))
        return render_template('event_rsvp.html', event=ev)

    @_app.route('/events/<int:event_id>/signup', methods=['GET', 'POST'])
    def event_signup(event_id):
        ev = db.session.get(Event, event_id) or abort(404)
        if request.method == 'POST':
            s = EventSignupRow(
                event_id=event_id,
                name=request.form.get('name', '').strip(),
                email=request.form.get('email', '').strip(),
                signup_type=request.form.get('signup_type', 'attendee'),
                notes=request.form.get('notes', ''),
            )
            db.session.add(s)
            db.session.commit()
            flash(f'Signed up for "{ev.title}" as {s.signup_type}.', 'success')
            return redirect(url_for('event_detail', event_id=event_id))
        return render_template('event_signup.html', event=ev)

    @_app.route('/events/suggest', methods=['GET', 'POST'])
    def event_suggest():
        if request.method == 'POST':
            sug = EventSuggestion(
                suggester_name=request.form.get('suggester_name', '').strip(),
                email=request.form.get('email', '').strip(),
                title=request.form.get('title', ''),
                description=request.form.get('description', ''),
                proposed_date=request.form.get('proposed_date', ''),
                category=request.form.get('category', 'Lecture'),
            )
            db.session.add(sug)
            db.session.commit()
            flash(f'Event suggestion submitted. Our events team will review "{sug.title}" within 5 business days.', 'success')
            return redirect(url_for('events'))
        return render_template('event_suggest.html')

    @_app.route('/faculty/<slug>/contact', methods=['GET', 'POST'])
    def faculty_contact(slug):
        f = Faculty.query.filter_by(slug=slug).first_or_404()
        if request.method == 'POST':
            m = ContactMessage(
                faculty_slug=slug,
                sender_name=request.form.get('sender_name', '').strip(),
                sender_email=request.form.get('sender_email', '').strip(),
                subject=request.form.get('subject', ''),
                message=request.form.get('message', ''),
                purpose=request.form.get('purpose', 'research_inquiry'),
            )
            db.session.add(m)
            db.session.commit()
            flash(f'Message sent to {f.name}. Confirmation #{m.id} sent to {m.sender_email}.', 'success')
            return redirect(url_for('faculty_profile', slug=slug))
        return render_template('faculty_contact.html', member=f)

    @_app.route('/departments/<slug>/schedule-meeting', methods=['GET', 'POST'])
    def dept_meeting(slug):
        d = Department.query.filter_by(slug=slug).first_or_404()
        if request.method == 'POST':
            ab = AppointmentBooking(
                department_slug=slug,
                name=request.form.get('name', '').strip(),
                email=request.form.get('email', '').strip(),
                purpose=request.form.get('purpose', ''),
                preferred_date=request.form.get('preferred_date', ''),
            )
            db.session.add(ab)
            db.session.commit()
            flash(f'Meeting request submitted to {d.name}. Confirmation #{ab.id}.', 'success')
            return redirect(url_for('department_detail', slug=slug))
        return render_template('dept_meeting.html', dept=d)

    @_app.route('/programs/<slug>/inquire', methods=['GET', 'POST'])
    def program_inquire(slug):
        p = Program.query.filter_by(slug=slug).first_or_404()
        if request.method == 'POST':
            q = ProgramInquiry(
                program_slug=slug,
                name=request.form.get('name', '').strip(),
                email=request.form.get('email', '').strip(),
                question=request.form.get('question', ''),
            )
            db.session.add(q)
            db.session.commit()
            flash(f'Inquiry sent to the {p.name} admissions team. Confirmation #{q.id}.', 'success')
            return redirect(url_for('program_detail', slug=slug))
        return render_template('program_inquire.html', program=p)

    @_app.route('/research/<slug>/contact', methods=['GET', 'POST'])
    def research_contact(slug):
        c = ResearchCenter.query.filter_by(slug=slug).first_or_404()
        if request.method == 'POST':
            rc = ResearchContact(
                center_slug=slug,
                name=request.form.get('name', '').strip(),
                email=request.form.get('email', '').strip(),
                message=request.form.get('message', ''),
                partnership_type=request.form.get('partnership_type', 'research_collab'),
            )
            db.session.add(rc)
            db.session.commit()
            flash(f'Message sent to {c.name}. We will follow up to {rc.email}.', 'success')
            return redirect(url_for('research_center', slug=slug))
        return render_template('research_contact.html', center=c)

    @_app.route('/newsletter', methods=['GET', 'POST'])
    def newsletter():
        if request.method == 'POST':
            n = NewsletterSubscription(
                email=request.form.get('email', '').strip(),
                list_name=request.form.get('list_name', 'berkeley-weekly'),
                frequency=request.form.get('frequency', 'weekly'),
            )
            db.session.add(n)
            db.session.commit()
            flash(f'Subscribed {n.email} to {n.list_name}. Welcome!', 'success')
            return redirect(url_for('newsletter'))
        return render_template('newsletter.html')

    @_app.route('/contact', methods=['GET', 'POST'])
    def contact():
        if request.method == 'POST':
            g = GeneralContact(
                name=request.form.get('name', '').strip(),
                email=request.form.get('email', '').strip(),
                topic=request.form.get('topic', 'General Inquiry'),
                message=request.form.get('message', ''),
            )
            db.session.add(g)
            db.session.commit()
            flash(f'Message received. We will reply to {g.email} within 5 business days.', 'success')
            return redirect(url_for('contact'))
        return render_template('contact.html')

    @_app.route('/careers')
    def careers():
        positions = [
            {'title': 'Assistant Professor of Computer Science', 'department': 'Electrical Engineering & Computer Sciences', 'type': 'Faculty', 'deadline': '2026-11-15', 'salary': '$140,000 – $180,000', 'location': 'Soda Hall', 'slug': 'asst-prof-cs-2026'},
            {'title': 'Postdoctoral Scholar, Climate Equity', 'department': 'Goldman School of Public Policy', 'type': 'Postdoc', 'deadline': '2026-10-01', 'salary': '$68,000 – $82,000', 'location': 'GSPP', 'slug': 'postdoc-climate-equity'},
            {'title': 'Senior Research Software Engineer', 'department': 'Berkeley AI Research', 'type': 'Staff', 'deadline': '2026-09-30', 'salary': '$135,000 – $165,000', 'location': 'BAIR Commons', 'slug': 'senior-rse-bair'},
            {'title': 'Library Public Services Coordinator', 'department': 'Doe Library', 'type': 'Staff', 'deadline': '2026-09-15', 'salary': '$72,000 – $88,000', 'location': 'Doe Library', 'slug': 'library-public-services'},
            {'title': 'Lecturer in Spanish Literature', 'department': 'Department of Spanish & Portuguese', 'type': 'Lecturer', 'deadline': '2026-10-30', 'salary': '$66,000 – $78,000 per academic year', 'location': 'Dwinelle Hall', 'slug': 'lecturer-spanish-lit'},
            {'title': 'Director, First Generation Initiative', 'department': 'Centers for Educational Equity', 'type': 'Staff', 'deadline': '2026-09-22', 'salary': '$98,000 – $118,000', 'location': 'Cesar Chavez Student Center', 'slug': 'director-first-gen'},
            {'title': 'Assistant Athletic Trainer', 'department': 'Cal Athletics', 'type': 'Staff', 'deadline': '2026-08-31', 'salary': '$62,000 – $76,000', 'location': 'Haas Pavilion', 'slug': 'asst-athletic-trainer'},
            {'title': 'Curator, Bancroft Library', 'department': 'Bancroft Library', 'type': 'Staff', 'deadline': '2026-10-15', 'salary': '$96,000 – $114,000', 'location': 'Doe Building', 'slug': 'curator-bancroft'},
        ]
        return render_template('careers.html', positions=positions)

    @_app.route('/about/strategic-plan')
    def strategic_plan():
        pillars = [
            {'name': 'Access and Affordability', 'description': 'Make Berkeley accessible to every qualified Californian regardless of income.', 'kpi': '60% of in-state undergraduates receiving need-based aid by 2030.'},
            {'name': 'Research Excellence', 'description': 'Sustain Berkeley as the leading public research university by investing in faculty and infrastructure.', 'kpi': 'Reach $1.2B in annual research expenditures by 2030.'},
            {'name': 'Climate Leadership', 'description': 'Achieve campus carbon neutrality and lead California\'s climate research agenda.', 'kpi': 'Net-zero scope-1 emissions by 2028.'},
            {'name': 'Public Service', 'description': 'Expand internships, fellowships, and partnerships connecting Berkeley with California communities.', 'kpi': 'Place 1,000 undergrads per year in publicly funded internships.'},
            {'name': 'Belonging', 'description': 'Build an inclusive culture where every Berkeley community member can thrive.', 'kpi': 'Faculty composition matching California\'s demographics by 2032.'},
        ]
        return render_template('strategic_plan.html', pillars=pillars)

    @_app.route('/about/history')
    def about_history():
        milestones = [
            (1868, 'University of California chartered', 'Governor H. H. Haight signs the Organic Act on March 23.'),
            (1873, 'Move to Berkeley campus', 'University relocates from Oakland to the 1,232-acre Berkeley site.'),
            (1898, 'Hearst Memorial Mining Building dedicated', 'Phoebe Hearst funds the first of many campus buildings.'),
            (1942, 'Bevatron and Radiation Laboratory', 'Ernest Lawrence\'s cyclotron leads to a Nobel Prize.'),
            (1964, 'Free Speech Movement', 'Students lead a sit-in on Sproul Plaza for political speech rights.'),
            (1989, 'Loma Prieta earthquake', 'Memorial Stadium and several buildings sustain seismic damage.'),
            (2012, 'Memorial Stadium seismic retrofit complete', 'Hayward Fault crossing stabilized.'),
            (2024, 'Rich Lyons becomes 12th Chancellor', 'First Berkeley alumnus to serve as Chancellor.'),
        ]
        return render_template('about_history.html', milestones=milestones)

    @_app.route('/account/edit', methods=['GET', 'POST'])
    @login_required
    def account_edit():
        if request.method == 'POST':
            current_user.full_name = request.form.get('full_name', current_user.full_name).strip()
            current_user.bio = request.form.get('bio', '')
            db.session.commit()
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('account'))
        return render_template('account_edit.html')

    # Register a context-processor extending the base nav links
    @_app.context_processor
    def inject_deepen_globals():
        return {
            'gd_top_libraries': Library.query.order_by(Library.name).limit(6).all() if Library.query.first() else [],
            'gd_top_funds': GivingFund.query.order_by(GivingFund.raised_amount.desc()).limit(5).all() if GivingFund.query.first() else [],
        }
