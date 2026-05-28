#!/usr/bin/env python3
"""Ohio State University mirror — Flask application."""
import os
import re
from datetime import datetime, timedelta
from math import ceil

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, jsonify, session, abort, g)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from flask_bcrypt import Bcrypt
from wtforms import StringField, PasswordField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'osu-mirror-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'osu.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please sign in to continue.'
login_manager.login_message_category = 'info'
csrf = CSRFProtect(app)

PER_PAGE = 20

# ─── Helpers ──────────────────────────────────────────────────────────────────

def slugify(text):
    if not text:
        return ''
    s = re.sub(r'[^a-zA-Z0-9\s-]', '', text)
    s = re.sub(r'[\s]+', '-', s.strip().lower())
    return s

# ─── Models ───────────────────────────────────────────────────────────────────

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150), nullable=False, default='')
    role = db.Column(db.String(30), default='student')
    bio = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookmarks = db.relationship('Bookmark', backref='user', lazy=True,
                                cascade='all, delete-orphan')

    def set_password(self, pw):
        self.password_hash = bcrypt.generate_password_hash(pw).decode('utf-8')

    def check_password(self, pw):
        return bcrypt.check_password_hash(self.password_hash, pw)


class College(db.Model):
    __tablename__ = 'colleges'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, default='')
    dean = db.Column(db.String(150), default='')
    founded_year = db.Column(db.Integer, default=1870)
    undergrad_count = db.Column(db.Integer, default=1000)
    grad_count = db.Column(db.Integer, default=500)
    campus = db.Column(db.String(100), default='Columbus')

    departments = db.relationship('Department', backref='college', lazy=True)
    programs = db.relationship('Program', backref='college', lazy=True)
    research_centers = db.relationship('ResearchCenter', backref='college', lazy=True)


class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'), nullable=False)
    description = db.Column(db.Text, default='')
    chair = db.Column(db.String(150), default='')
    phone = db.Column(db.String(30), default='')
    location = db.Column(db.String(200), default='')

    faculty = db.relationship('Faculty', backref='department', lazy=True)
    programs = db.relationship('Program', backref='department', lazy=True)


class Program(db.Model):
    __tablename__ = 'programs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300), nullable=False)
    slug = db.Column(db.String(300), unique=True, nullable=False, index=True)
    degree_type = db.Column(db.String(20), default='BA')
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    description = db.Column(db.Text, default='')
    requirements = db.Column(db.Text, default='')
    units = db.Column(db.Integer, default=120)
    duration_years = db.Column(db.Float, default=4.0)
    application_deadline = db.Column(db.String(80), default='')
    is_online = db.Column(db.Boolean, default=False)
    gre_required = db.Column(db.Boolean, default=False)


class NewsArticle(db.Model):
    __tablename__ = 'news_articles'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    slug = db.Column(db.String(300), unique=True, nullable=False, index=True)
    category = db.Column(db.String(50), default='Campus Life')
    author = db.Column(db.String(150), default='OSU News Staff')
    published_date = db.Column(db.DateTime, default=datetime.utcnow)
    content = db.Column(db.Text, default='')
    summary = db.Column(db.Text, default='')
    tags = db.Column(db.String(500), default='')
    view_count = db.Column(db.Integer, default=0)
    featured = db.Column(db.Boolean, default=False)


class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default='')
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=True)
    location = db.Column(db.String(300), default='')
    building = db.Column(db.String(200), default='')
    campus = db.Column(db.String(100), default='Columbus')
    category = db.Column(db.String(50), default='Lecture')
    organizer = db.Column(db.String(200), default='')
    registration_required = db.Column(db.Boolean, default=False)
    cost = db.Column(db.String(50), default='Free')


class ResearchCenter(db.Model):
    __tablename__ = 'research_centers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300), nullable=False)
    slug = db.Column(db.String(300), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, default='')
    director = db.Column(db.String(150), default='')
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'), nullable=True)
    focus_areas = db.Column(db.String(500), default='')
    url = db.Column(db.String(300), default='')
    founded_year = db.Column(db.Integer, default=2000)


class Faculty(db.Model):
    __tablename__ = 'faculty'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), default='Professor')
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    email = db.Column(db.String(120), default='')
    office = db.Column(db.String(200), default='')
    phone = db.Column(db.String(30), default='')
    research_interests = db.Column(db.String(500), default='')
    bio = db.Column(db.Text, default='')
    is_emeritus = db.Column(db.Boolean, default=False)


class AthleticTeam(db.Model):
    __tablename__ = 'athletic_teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    sport = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(20), default='Men')
    conference = db.Column(db.String(100), default='Big Ten')
    coach = db.Column(db.String(150), default='')
    home_venue = db.Column(db.String(200), default='')
    national_titles = db.Column(db.Integer, default=0)
    recent_record = db.Column(db.String(50), default='')


class Bookmark(db.Model):
    __tablename__ = 'bookmarks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    item_type = db.Column(db.String(50), nullable=False)
    item_id = db.Column(db.Integer, nullable=False)
    note = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ─── Extended catalog models (vanilla deepen) ────────────────────────────────

class StudentLifeCategory(db.Model):
    __tablename__ = 'student_life_categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    tagline = db.Column(db.String(300), default='')
    description = db.Column(db.Text, default='')
    icon = db.Column(db.String(50), default='')
    body = db.Column(db.Text, default='')
    contact_email = db.Column(db.String(120), default='')


class LibraryBranch(db.Model):
    __tablename__ = 'library_branches'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    address = db.Column(db.String(300), default='')
    phone = db.Column(db.String(40), default='')
    hours = db.Column(db.String(200), default='')
    description = db.Column(db.Text, default='')
    head_librarian = db.Column(db.String(150), default='')
    collection_size = db.Column(db.Integer, default=0)
    has_study_rooms = db.Column(db.Boolean, default=True)


class DiningLocation(db.Model):
    __tablename__ = 'dining_locations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    location = db.Column(db.String(200), default='')
    hours = db.Column(db.String(200), default='')
    cuisine = db.Column(db.String(100), default='')
    accepts_meal_plan = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text, default='')
    seats = db.Column(db.Integer, default=100)


class DiningMenuItem(db.Model):
    __tablename__ = 'dining_menu_items'
    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey('dining_locations.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(400), default='')
    meal = db.Column(db.String(30), default='Lunch')
    price = db.Column(db.Float, default=8.5)
    calories = db.Column(db.Integer, default=400)
    is_vegetarian = db.Column(db.Boolean, default=False)
    is_vegan = db.Column(db.Boolean, default=False)


class AthleticGame(db.Model):
    __tablename__ = 'athletic_games'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('athletic_teams.id'), nullable=False)
    opponent = db.Column(db.String(150), nullable=False)
    home_away = db.Column(db.String(10), default='Home')
    game_date = db.Column(db.DateTime, nullable=False)
    venue = db.Column(db.String(200), default='')
    result = db.Column(db.String(40), default='')
    tv = db.Column(db.String(40), default='')


class AthleticRosterMember(db.Model):
    __tablename__ = 'athletic_roster'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('athletic_teams.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    jersey_number = db.Column(db.String(8), default='')
    position = db.Column(db.String(50), default='')
    year = db.Column(db.String(20), default='Freshman')
    hometown = db.Column(db.String(150), default='')
    height = db.Column(db.String(20), default='')
    weight = db.Column(db.String(20), default='')


class AlumniChapter(db.Model):
    __tablename__ = 'alumni_chapters'
    id = db.Column(db.Integer, primary_key=True)
    region = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    city = db.Column(db.String(120), default='')
    state = db.Column(db.String(60), default='')
    president = db.Column(db.String(150), default='')
    members = db.Column(db.Integer, default=0)
    founded_year = db.Column(db.Integer, default=1990)
    next_event = db.Column(db.String(300), default='')
    description = db.Column(db.Text, default='')


class GivingFund(db.Model):
    __tablename__ = 'giving_funds'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    purpose = db.Column(db.String(120), default='Scholarship')
    goal_amount = db.Column(db.Integer, default=100000)
    raised_amount = db.Column(db.Integer, default=0)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'), nullable=True)
    description = db.Column(db.Text, default='')
    minimum_gift = db.Column(db.Integer, default=25)


class FinancialAidType(db.Model):
    __tablename__ = 'financial_aid_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    category = db.Column(db.String(50), default='Grant')
    eligibility = db.Column(db.String(400), default='')
    award_range = db.Column(db.String(120), default='')
    deadline = db.Column(db.String(120), default='March 1')
    description = db.Column(db.Text, default='')


class FinancialAidForm(db.Model):
    __tablename__ = 'financial_aid_forms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    audience = db.Column(db.String(100), default='Undergraduate')
    submit_window = db.Column(db.String(120), default='Oct 1 – March 1')
    description = db.Column(db.Text, default='')


class CollegeLeader(db.Model):
    __tablename__ = 'college_leaders'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(150), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), default='')
    bio = db.Column(db.Text, default='')
    rank = db.Column(db.Integer, default=10)
    email = db.Column(db.String(120), default='')


class HistoryMilestone(db.Model):
    __tablename__ = 'history_milestones'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')


class DiversityProgram(db.Model):
    __tablename__ = 'diversity_programs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    audience = db.Column(db.String(120), default='All Students')
    director = db.Column(db.String(150), default='')
    description = db.Column(db.Text, default='')


class CampusService(db.Model):
    __tablename__ = 'campus_services'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    category = db.Column(db.String(80), default='Academic')
    phone = db.Column(db.String(40), default='')
    location = db.Column(db.String(200), default='')
    description = db.Column(db.Text, default='')


class AdmissionsPathway(db.Model):
    __tablename__ = 'admissions_pathways'
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(40), nullable=False, index=True)  # undergrad/grad/transfer/international/pathways
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, default='')
    requirements = db.Column(db.Text, default='')
    deadline = db.Column(db.String(120), default='February 1')
    application_fee = db.Column(db.Integer, default=70)


# ─── Transactional / write tables ─────────────────────────────────────────────

class Application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    level = db.Column(db.String(40), default='undergraduate')
    program = db.Column(db.String(200), default='')
    citizenship = db.Column(db.String(80), default='United States')
    high_school = db.Column(db.String(200), default='')
    statement = db.Column(db.Text, default='')
    status = db.Column(db.String(30), default='submitted')
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)


class TourBooking(db.Model):
    __tablename__ = 'tour_bookings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    tour_date = db.Column(db.String(40), nullable=False)
    tour_type = db.Column(db.String(40), default='in-person')  # in-person | virtual
    group_size = db.Column(db.Integer, default=1)
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class EventRSVP(db.Model):
    __tablename__ = 'event_rsvps'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    guests = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LibraryRoomReservation(db.Model):
    __tablename__ = 'library_room_reservations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('library_branches.id'), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    room_number = db.Column(db.String(20), default='A101')
    reserve_date = db.Column(db.String(40), nullable=False)
    start_time = db.Column(db.String(10), default='13:00')
    duration_hours = db.Column(db.Integer, default=2)
    purpose = db.Column(db.String(300), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AlumniMembership(db.Model):
    __tablename__ = 'alumni_memberships'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('alumni_chapters.id'), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    graduation_year = db.Column(db.Integer, default=2020)
    degree = db.Column(db.String(120), default='BA')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Donation(db.Model):
    __tablename__ = 'donations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    fund_id = db.Column(db.Integer, db.ForeignKey('giving_funds.id'), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Integer, default=50)
    is_recurring = db.Column(db.Boolean, default=False)
    in_honor_of = db.Column(db.String(200), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class DiningOrder(db.Model):
    __tablename__ = 'dining_orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    location_id = db.Column(db.Integer, db.ForeignKey('dining_locations.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('dining_menu_items.id'), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    pickup_time = db.Column(db.String(10), default='12:00')
    quantity = db.Column(db.Integer, default=1)
    special_instructions = db.Column(db.String(300), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ContactInquiry(db.Model):
    __tablename__ = 'contact_inquiries'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), default='')
    message = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ServiceRequest(db.Model):
    __tablename__ = 'service_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    service_slug = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    request_type = db.Column(db.String(80), default='general')
    description = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TicketPurchase(db.Model):
    __tablename__ = 'ticket_purchases'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    game_id = db.Column(db.Integer, db.ForeignKey('athletic_games.id'), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    section = db.Column(db.String(40), default='30A')
    quantity = db.Column(db.Integer, default=2)
    total_price = db.Column(db.Integer, default=120)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TranscriptRequest(db.Model):
    __tablename__ = 'transcript_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    student_id = db.Column(db.String(40), default='')
    delivery = db.Column(db.String(20), default='electronic')
    recipient = db.Column(db.String(200), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class InfoRequest(db.Model):
    __tablename__ = 'info_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    program_interest = db.Column(db.String(200), default='')
    home_state = db.Column(db.String(60), default='Ohio')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class NewsComment(db.Model):
    __tablename__ = 'news_comments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    article_id = db.Column(db.Integer, db.ForeignKey('news_articles.id'), nullable=False)
    author_name = db.Column(db.String(150), default='Guest')
    body = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FinancialAidSubmission(db.Model):
    __tablename__ = 'financial_aid_submissions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    form_id = db.Column(db.Integer, db.ForeignKey('financial_aid_forms.id'), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    family_income = db.Column(db.Integer, default=60000)
    dependents = db.Column(db.Integer, default=2)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)


# ─── Forms ────────────────────────────────────────────────────────────────────

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 80)])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(2, 150)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(8, 100)])
    confirm = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])

class ProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(2, 150)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    bio = TextAreaField('Bio', validators=[Optional(), Length(max=1000)])

class BookmarkForm(FlaskForm):
    item_type = StringField('Type', validators=[DataRequired()])
    item_id = StringField('ID', validators=[DataRequired()])
    note = TextAreaField('Note', validators=[Optional(), Length(max=500)])

# ─── Login Manager ────────────────────────────────────────────────────────────

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ─── Context Processors ───────────────────────────────────────────────────────

@app.context_processor
def inject_globals():
    return {
        'now': datetime.utcnow(),
        'colleges': College.query.order_by(College.name).all(),
    }


# ─── SVG placeholder helper (image utilization) ───────────────────────────────

@app.context_processor
def inject_svg_helper():
    def svg_tile(label, kind='generic', w=320, h=180):
        # deterministic palette by hash
        h_int = abs(hash(f'{kind}:{label}')) % (10**8)
        palette = [
            ('#BB0000', '#fff'), ('#8B0000', '#fff'), ('#222b45', '#fff'),
            ('#2c4b6e', '#fff'), ('#3c6e47', '#fff'), ('#6e4c1e', '#fff'),
            ('#888', '#fff'), ('#444', '#fff'), ('#a02830', '#fff'),
            ('#1d3557', '#fff'),
        ]
        bg, fg = palette[h_int % len(palette)]
        text = (label or '?')[:18]
        initials = ''.join([w[0] for w in (label or 'O S U').split()[:3]]).upper()[:3]
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-label="{text}" '
            f'class="osu-tile osu-tile-{kind}">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>'
            f'<text x="{w//2}" y="{h//2 - 6}" fill="{fg}" font-size="{min(54, h//3)}" '
            f'font-family="Georgia, serif" font-weight="bold" text-anchor="middle">{initials}</text>'
            f'<text x="{w//2}" y="{h - 18}" fill="{fg}" font-size="13" '
            f'font-family="sans-serif" opacity="0.85" text-anchor="middle">{text}</text>'
            f'</svg>'
        )
    from markupsafe import Markup
    return {'svg_tile': lambda *a, **kw: Markup(svg_tile(*a, **kw))}

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    featured_news = NewsArticle.query.filter_by(featured=True).order_by(
        NewsArticle.published_date.desc()).limit(6).all()
    if len(featured_news) < 3:
        featured_news = NewsArticle.query.order_by(
            NewsArticle.published_date.desc()).limit(6).all()
    upcoming_events = Event.query.filter(
        Event.start_datetime >= datetime.utcnow()
    ).order_by(Event.start_datetime).limit(4).all()
    recent_research = ResearchCenter.query.limit(4).all()
    stats = {
        'fulbright_rank': 1,
        'undergrad_majors': 200,
        'grad_programs': 278,
        'varsity_sports': 36,
        'faculty_count': 7000,
        'undergrad_count': 46820,
        'grad_count': 14000,
        'degree_programs': 500,
        'buckeython_raised': 13,
        'extension_offices': 88,
        'campuses': 6,
        'research_expenditure': 1.3,
    }
    return render_template('index.html',
                           featured_news=featured_news,
                           upcoming_events=upcoming_events,
                           recent_research=recent_research,
                           stats=stats)


@app.route('/news')
def news():
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '')
    featured = request.args.get('featured', '')
    page = request.args.get('page', 1, type=int)

    query = NewsArticle.query
    if q:
        query = query.filter(
            db.or_(
                NewsArticle.title.ilike(f'%{q}%'),
                NewsArticle.summary.ilike(f'%{q}%'),
                NewsArticle.content.ilike(f'%{q}%'),
                NewsArticle.tags.ilike(f'%{q}%'),
            ))
    if category:
        query = query.filter(NewsArticle.category == category)
    if featured == '1':
        query = query.filter(NewsArticle.featured == True)

    query = query.order_by(NewsArticle.published_date.desc())
    total = query.count()
    articles = query.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()
    total_pages = ceil(total / PER_PAGE) if total else 1

    categories = ['Research', 'Campus Life', 'Faculty', 'Student', 'Athletics',
                  'Science', 'Health']
    return render_template('news.html',
                           articles=articles,
                           total=total,
                           page=page,
                           total_pages=total_pages,
                           categories=categories,
                           current_category=category,
                           q=q,
                           featured=featured)


@app.route('/news/<slug>')
def news_article(slug):
    article = NewsArticle.query.filter_by(slug=slug).first_or_404()
    article.view_count = (article.view_count or 0) + 1
    db.session.commit()
    related = NewsArticle.query.filter(
        NewsArticle.category == article.category,
        NewsArticle.id != article.id
    ).order_by(NewsArticle.published_date.desc()).limit(3).all()
    return render_template('news_article.html', article=article, related=related)


@app.route('/academics')
def academics():
    colleges = College.query.order_by(College.name).all()
    total_programs = Program.query.count()
    total_depts = Department.query.count()
    return render_template('academics.html',
                           colleges=colleges,
                           total_programs=total_programs,
                           total_depts=total_depts)


@app.route('/programs')
def programs():
    q = request.args.get('q', '').strip()
    college_slug = request.args.get('college', '')
    degree = request.args.get('degree', '')
    online = request.args.get('online', '')
    page = request.args.get('page', 1, type=int)

    query = Program.query
    if q:
        query = query.filter(
            db.or_(
                Program.name.ilike(f'%{q}%'),
                Program.description.ilike(f'%{q}%'),
            ))
    if college_slug:
        col = College.query.filter_by(slug=college_slug).first()
        if col:
            query = query.filter(Program.college_id == col.id)
    if degree:
        query = query.filter(Program.degree_type == degree)
    if online == '1':
        query = query.filter(Program.is_online == True)

    query = query.order_by(Program.name)
    total = query.count()
    progs = query.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()
    total_pages = ceil(total / PER_PAGE) if total else 1

    all_colleges = College.query.order_by(College.name).all()
    degree_types = ['BA', 'BS', 'MA', 'MS', 'PhD', 'MPH', 'MBA', 'JD', 'MD',
                    'PharmD', 'DVM', 'OD']
    return render_template('programs.html',
                           programs=progs,
                           total=total,
                           page=page,
                           total_pages=total_pages,
                           all_colleges=all_colleges,
                           degree_types=degree_types,
                           current_college=college_slug,
                           current_degree=degree,
                           online=online,
                           q=q)


@app.route('/programs/<slug>')
def program_detail(slug):
    program = Program.query.filter_by(slug=slug).first_or_404()
    related = Program.query.filter(
        Program.college_id == program.college_id,
        Program.id != program.id
    ).limit(4).all()
    return render_template('program_detail.html', program=program, related=related)


@app.route('/events')
def events():
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '')
    campus = request.args.get('campus', '')
    date_filter = request.args.get('date', 'upcoming')
    page = request.args.get('page', 1, type=int)
    now = datetime.utcnow()

    query = Event.query
    if q:
        query = query.filter(
            db.or_(
                Event.title.ilike(f'%{q}%'),
                Event.description.ilike(f'%{q}%'),
                Event.location.ilike(f'%{q}%'),
                Event.organizer.ilike(f'%{q}%'),
            ))
    if category:
        query = query.filter(Event.category == category)
    if campus:
        query = query.filter(Event.campus == campus)
    if date_filter == 'upcoming':
        query = query.filter(Event.start_datetime >= now)
        query = query.order_by(Event.start_datetime)
    elif date_filter == 'past':
        query = query.filter(Event.start_datetime < now)
        query = query.order_by(Event.start_datetime.desc())
    elif date_filter == 'today':
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59)
        query = query.filter(Event.start_datetime.between(today_start, today_end))
        query = query.order_by(Event.start_datetime)
    else:
        query = query.order_by(Event.start_datetime)

    total = query.count()
    evts = query.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()
    total_pages = ceil(total / PER_PAGE) if total else 1

    categories = ['Lecture', 'Sports', 'Arts', 'Career', 'Health', 'Social', 'Virtual']
    campuses = ['Columbus', 'Lima', 'Marion', 'Mansfield', 'Newark', 'Wooster']
    return render_template('events.html',
                           events=evts,
                           total=total,
                           page=page,
                           total_pages=total_pages,
                           categories=categories,
                           campuses=campuses,
                           current_category=category,
                           current_campus=campus,
                           date_filter=date_filter,
                           q=q)


@app.route('/events/<int:event_id>')
def event_detail(event_id):
    event = db.session.get(Event, event_id)
    if event is None:
        abort(404)
    related = Event.query.filter(
        Event.category == event.category,
        Event.id != event.id,
        Event.start_datetime >= datetime.utcnow()
    ).order_by(Event.start_datetime).limit(3).all()
    return render_template('event_detail.html', event=event, related=related)


@app.route('/research')
def research():
    centers = ResearchCenter.query.order_by(ResearchCenter.name).all()
    colleges = College.query.order_by(College.name).all()
    return render_template('research.html', centers=centers, colleges=colleges)


@app.route('/research/<slug>')
def research_center(slug):
    center = ResearchCenter.query.filter_by(slug=slug).first_or_404()
    related = ResearchCenter.query.filter(
        ResearchCenter.college_id == center.college_id,
        ResearchCenter.id != center.id
    ).limit(3).all()
    return render_template('research_center.html', center=center, related=related)


@app.route('/departments')
def departments():
    all_colleges = College.query.order_by(College.name).all()
    depts_by_college = {}
    for college in all_colleges:
        depts_by_college[college] = Department.query.filter_by(
            college_id=college.id).order_by(Department.name).all()
    return render_template('departments.html', depts_by_college=depts_by_college)


@app.route('/departments/<slug>')
def department_detail(slug):
    dept = Department.query.filter_by(slug=slug).first_or_404()
    faculty_list = Faculty.query.filter_by(department_id=dept.id).order_by(Faculty.name).all()
    dept_programs = Program.query.filter_by(department_id=dept.id).all()
    return render_template('department_detail.html',
                           dept=dept,
                           faculty_list=faculty_list,
                           programs=dept_programs)


@app.route('/admissions')
def admissions():
    undergrad_programs = Program.query.filter(
        Program.degree_type.in_(['BA', 'BS'])
    ).count()
    grad_programs = Program.query.filter(
        Program.degree_type.in_(['MA', 'MS', 'PhD', 'MPH', 'MBA', 'JD', 'MD',
                                  'PharmD', 'DVM', 'OD'])
    ).count()
    online_programs = Program.query.filter_by(is_online=True).count()
    return render_template('admissions.html',
                           undergrad_programs=undergrad_programs,
                           grad_programs=grad_programs,
                           online_programs=online_programs)


@app.route('/about')
def about():
    stats = {
        'fulbright_rank': 1,
        'undergrad_majors': 200,
        'grad_programs': 278,
        'varsity_sports': 36,
        'faculty_count': 7000,
        'undergrad_count': 46820,
        'grad_count': 14000,
        'degree_programs': 500,
        'founded': 1870,
        'acres': 1665,
        'campuses': 6,
        'alumni': 600000,
        'extension_offices': 88,
        'buckeython_raised': 13,
        'research_expenditure': 1.3,
        'national_titles': 15,
    }
    return render_template('about.html', stats=stats)


@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    results = {'programs': [], 'news': [], 'events': [], 'faculty': [],
               'research': [], 'athletics': []}
    total = 0
    if q:
        results['programs'] = Program.query.filter(
            db.or_(
                Program.name.ilike(f'%{q}%'),
                Program.description.ilike(f'%{q}%'),
            )).limit(10).all()
        results['news'] = NewsArticle.query.filter(
            db.or_(
                NewsArticle.title.ilike(f'%{q}%'),
                NewsArticle.summary.ilike(f'%{q}%'),
                NewsArticle.tags.ilike(f'%{q}%'),
            )).order_by(NewsArticle.published_date.desc()).limit(10).all()
        results['events'] = Event.query.filter(
            db.or_(
                Event.title.ilike(f'%{q}%'),
                Event.description.ilike(f'%{q}%'),
            )).limit(10).all()
        results['faculty'] = Faculty.query.filter(
            db.or_(
                Faculty.name.ilike(f'%{q}%'),
                Faculty.research_interests.ilike(f'%{q}%'),
                Faculty.bio.ilike(f'%{q}%'),
            )).limit(10).all()
        results['research'] = ResearchCenter.query.filter(
            db.or_(
                ResearchCenter.name.ilike(f'%{q}%'),
                ResearchCenter.description.ilike(f'%{q}%'),
                ResearchCenter.focus_areas.ilike(f'%{q}%'),
            )).limit(10).all()
        results['athletics'] = AthleticTeam.query.filter(
            db.or_(
                AthleticTeam.name.ilike(f'%{q}%'),
                AthleticTeam.sport.ilike(f'%{q}%'),
            )).limit(10).all()
        total = sum(len(v) for v in results.values())
    return render_template('search.html', q=q, results=results, total=total)


@app.route('/faculty')
def faculty():
    q = request.args.get('q', '').strip()
    dept_slug = request.args.get('dept', '')
    page = request.args.get('page', 1, type=int)

    query = Faculty.query
    if q:
        query = query.filter(
            db.or_(
                Faculty.name.ilike(f'%{q}%'),
                Faculty.research_interests.ilike(f'%{q}%'),
                Faculty.title.ilike(f'%{q}%'),
            ))
    if dept_slug:
        dept = Department.query.filter_by(slug=dept_slug).first()
        if dept:
            query = query.filter(Faculty.department_id == dept.id)

    query = query.order_by(Faculty.name)
    total = query.count()
    faculty_list = query.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()
    total_pages = ceil(total / PER_PAGE) if total else 1

    all_depts = Department.query.order_by(Department.name).all()
    return render_template('faculty.html',
                           faculty_list=faculty_list,
                           total=total,
                           page=page,
                           total_pages=total_pages,
                           all_depts=all_depts,
                           current_dept=dept_slug,
                           q=q)


@app.route('/faculty/<slug>')
def faculty_profile(slug):
    member = Faculty.query.filter_by(slug=slug).first_or_404()
    colleagues = []
    if member.department_id:
        colleagues = Faculty.query.filter(
            Faculty.department_id == member.department_id,
            Faculty.id != member.id
        ).limit(5).all()
    return render_template('faculty_profile.html', member=member, colleagues=colleagues)


@app.route('/athletics')
def athletics():
    teams = AthleticTeam.query.order_by(AthleticTeam.sport, AthleticTeam.name).all()
    men_teams = [t for t in teams if t.gender == 'Men']
    women_teams = [t for t in teams if t.gender == 'Women']
    coed_teams = [t for t in teams if t.gender == 'Co-ed']
    return render_template('athletics.html',
                           teams=teams,
                           men_teams=men_teams,
                           women_teams=women_teams,
                           coed_teams=coed_teams)


@app.route('/athletics/<slug>')
def athletics_team(slug):
    team = AthleticTeam.query.filter_by(slug=slug).first_or_404()
    related = AthleticTeam.query.filter(
        AthleticTeam.gender == team.gender,
        AthleticTeam.id != team.id
    ).limit(4).all()
    return render_template('athletics_team.html', team=team, related=related)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            flash('Welcome back, Buckeye!', 'success')
            return redirect(next_page or url_for('index'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower().strip()).first():
            flash('Email already registered.', 'danger')
        elif User.query.filter_by(username=form.username.data.strip()).first():
            flash('Username already taken.', 'danger')
        else:
            user = User(
                email=form.email.data.lower().strip(),
                username=form.username.data.strip(),
                full_name=form.full_name.data.strip(),
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Account created! Welcome to The Ohio State University.', 'success')
            return redirect(url_for('index'))
    return render_template('register.html', form=form)


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/account')
@login_required
def account():
    bookmarks = Bookmark.query.filter_by(user_id=current_user.id).order_by(
        Bookmark.created_at.desc()).all()
    bookmark_details = []
    for bm in bookmarks:
        detail = {'bookmark': bm, 'item': None, 'title': '', 'url': '#'}
        if bm.item_type == 'program':
            item = db.session.get(Program, bm.item_id)
            if item:
                detail['item'] = item
                detail['title'] = item.name
                detail['url'] = url_for('program_detail', slug=item.slug)
        elif bm.item_type == 'news':
            item = db.session.get(NewsArticle, bm.item_id)
            if item:
                detail['item'] = item
                detail['title'] = item.title
                detail['url'] = url_for('news_article', slug=item.slug)
        elif bm.item_type == 'event':
            item = db.session.get(Event, bm.item_id)
            if item:
                detail['item'] = item
                detail['title'] = item.title
                detail['url'] = url_for('event_detail', event_id=item.id)
        elif bm.item_type == 'faculty':
            item = db.session.get(Faculty, bm.item_id)
            if item:
                detail['item'] = item
                detail['title'] = item.name
                detail['url'] = url_for('faculty_profile', slug=item.slug)
        elif bm.item_type == 'research':
            item = db.session.get(ResearchCenter, bm.item_id)
            if item:
                detail['item'] = item
                detail['title'] = item.name
                detail['url'] = url_for('research_center', slug=item.slug)
        elif bm.item_type == 'athletics':
            item = db.session.get(AthleticTeam, bm.item_id)
            if item:
                detail['item'] = item
                detail['title'] = item.name
                detail['url'] = url_for('athletics_team', slug=item.slug)
        bookmark_details.append(detail)
    return render_template('account.html', bookmark_details=bookmark_details)


@app.route('/bookmark/add', methods=['POST'])
@login_required
def bookmark_add():
    item_type = request.form.get('item_type')
    item_id = request.form.get('item_id', type=int)
    note = request.form.get('note', '')
    if item_type and item_id:
        existing = Bookmark.query.filter_by(
            user_id=current_user.id, item_type=item_type, item_id=item_id
        ).first()
        if not existing:
            bm = Bookmark(user_id=current_user.id, item_type=item_type,
                          item_id=item_id, note=note)
            db.session.add(bm)
            db.session.commit()
            flash('Saved to bookmarks.', 'success')
        else:
            flash('Already bookmarked.', 'info')
    next_url = request.form.get('next') or request.referrer or url_for('account')
    return redirect(next_url)


@app.route('/bookmark/remove', methods=['POST'])
@login_required
def bookmark_remove():
    bookmark_id = request.form.get('bookmark_id', type=int)
    if bookmark_id:
        bm = db.session.get(Bookmark, bookmark_id)
        if bm and bm.user_id == current_user.id:
            db.session.delete(bm)
            db.session.commit()
            flash('Bookmark removed.', 'info')
    return redirect(request.referrer or url_for('account'))


# ─── New routes (admissions / aid / dining / library / alumni / giving etc) ──

@app.route('/academics/colleges/<slug>')
def college_detail(slug):
    college = College.query.filter_by(slug=slug).first_or_404()
    dept_list = Department.query.filter_by(college_id=college.id).order_by(Department.name).all()
    prog_list = Program.query.filter_by(college_id=college.id).order_by(Program.name).all()
    centers = ResearchCenter.query.filter_by(college_id=college.id).all()
    return render_template('college_detail.html', college=college,
                           dept_list=dept_list, prog_list=prog_list, centers=centers)


@app.route('/admissions/<level>', methods=['GET'])
def admissions_level(level):
    valid = {'undergraduate', 'graduate', 'transfer', 'international', 'pathways'}
    if level not in valid:
        abort(404)
    pathways = AdmissionsPathway.query.filter_by(level=level).order_by(
        AdmissionsPathway.name).all()
    return render_template('admissions_level.html', level=level, pathways=pathways)


@app.route('/admissions/visit', methods=['GET', 'POST'])
def admissions_visit():
    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        email = (request.form.get('email') or '').strip()
        tour_date = (request.form.get('tour_date') or '').strip()
        group_size = request.form.get('group_size', type=int) or 1
        if full_name and email and tour_date:
            b = TourBooking(full_name=full_name, email=email,
                            tour_date=tour_date, tour_type='in-person',
                            group_size=group_size,
                            notes=(request.form.get('notes') or '').strip(),
                            user_id=(current_user.id if current_user.is_authenticated else None))
            db.session.add(b)
            db.session.commit()
            flash(f'Campus visit booked for {tour_date}. Confirmation #{b.id} sent to {email}.', 'success')
            return redirect(url_for('admissions_visit'))
        flash('Please provide name, email, and a tour date.', 'danger')
    upcoming = TourBooking.query.filter_by(tour_type='in-person').count()
    return render_template('admissions_visit.html', upcoming=upcoming)


@app.route('/admissions/visits')
def admissions_visits_list():
    """List of upcoming campus tour bookings (public, anonymized last name)."""
    tour_type = (request.args.get('type') or '').strip().lower()
    query = TourBooking.query
    if tour_type in ('in-person', 'virtual'):
        query = query.filter_by(tour_type=tour_type)
    bookings = query.order_by(TourBooking.tour_date).limit(80).all()
    in_person_count = TourBooking.query.filter_by(tour_type='in-person').count()
    virtual_count = TourBooking.query.filter_by(tour_type='virtual').count()
    return render_template('admissions_visits_list.html',
                           bookings=bookings,
                           in_person_count=in_person_count,
                           virtual_count=virtual_count,
                           tour_type=tour_type)


@app.route('/admissions/virtual-tour', methods=['GET', 'POST'])
def admissions_virtual_tour():
    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        email = (request.form.get('email') or '').strip()
        tour_date = (request.form.get('tour_date') or '').strip()
        if full_name and email and tour_date:
            b = TourBooking(full_name=full_name, email=email,
                            tour_date=tour_date, tour_type='virtual',
                            group_size=1,
                            user_id=(current_user.id if current_user.is_authenticated else None))
            db.session.add(b)
            db.session.commit()
            flash(f'Virtual tour reserved for {tour_date}. Zoom link sent to {email}.', 'success')
            return redirect(url_for('admissions_virtual_tour'))
        flash('Please provide name, email, and a tour date.', 'danger')
    return render_template('admissions_virtual_tour.html')


@app.route('/admissions/apply', methods=['GET', 'POST'])
def admissions_apply():
    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        email = (request.form.get('email') or '').strip()
        level = (request.form.get('level') or 'undergraduate').strip()
        program = (request.form.get('program') or '').strip()
        if full_name and email and program:
            a = Application(full_name=full_name, email=email, level=level,
                            program=program,
                            citizenship=(request.form.get('citizenship') or 'United States').strip(),
                            high_school=(request.form.get('high_school') or '').strip(),
                            statement=(request.form.get('statement') or '').strip(),
                            user_id=(current_user.id if current_user.is_authenticated else None))
            db.session.add(a)
            db.session.commit()
            flash(f'Application submitted. Application #{a.id}. Decision letter by April 1.', 'success')
            return redirect(url_for('application_status', app_id=a.id))
        flash('Please complete all required fields.', 'danger')
    programs = Program.query.order_by(Program.name).limit(50).all()
    return render_template('admissions_apply.html', programs=programs)


@app.route('/admissions/applications', methods=['GET', 'POST'])
def admissions_applications():
    """Application status tracker — public listing with lookup by ID."""
    lookup_id = None
    if request.method == 'POST':
        lookup_id = request.form.get('lookup_id', type=int)
        if lookup_id:
            return redirect(url_for('application_status', app_id=lookup_id))
        flash('Enter a valid Application ID to look up status.', 'danger')

    status_filter = (request.args.get('status') or '').strip().lower()
    level_filter = (request.args.get('level') or '').strip().lower()
    query = Application.query
    if status_filter:
        query = query.filter(Application.status == status_filter)
    if level_filter:
        query = query.filter(Application.level == level_filter)
    apps = query.order_by(Application.submitted_at.desc()).limit(60).all()

    totals = {
        'all': Application.query.count(),
        'submitted': Application.query.filter_by(status='submitted').count(),
        'under-review': Application.query.filter_by(status='under-review').count(),
        'accepted': Application.query.filter_by(status='accepted').count(),
        'waitlisted': Application.query.filter_by(status='waitlisted').count(),
    }
    return render_template('admissions_applications.html',
                           apps=apps, totals=totals,
                           status_filter=status_filter,
                           level_filter=level_filter)


@app.route('/admissions/applications/<int:app_id>')
def application_status(app_id):
    a = db.session.get(Application, app_id)
    if a is None:
        abort(404)
    timeline = _build_application_timeline(a)
    return render_template('application_status.html', a=a, timeline=timeline)


def _build_application_timeline(a):
    """Synthesize a deterministic status timeline from submitted_at + status."""
    submit_dt = a.submitted_at or datetime.utcnow()
    steps = [
        ('submitted', submit_dt, 'Application received',
         'Your application and $70 fee were received by the Office of Admissions.'),
    ]
    if a.status in ('under-review', 'accepted', 'waitlisted', 'rejected'):
        steps.append(('under-review',
                      submit_dt + timedelta(days=14),
                      'Under faculty review',
                      'A program committee in {} is reviewing your file.'.format(
                          a.program or 'your program')))
    if a.status == 'accepted':
        steps.append(('accepted',
                      submit_dt + timedelta(days=42),
                      'Decision: Accepted',
                      'Congratulations! Your offer letter is in your account.'))
    if a.status == 'waitlisted':
        steps.append(('waitlisted',
                      submit_dt + timedelta(days=42),
                      'Decision: Waitlisted',
                      'Your application is on the waitlist. Updates by May 1.'))
    if a.status == 'rejected':
        steps.append(('rejected',
                      submit_dt + timedelta(days=42),
                      'Decision: Not admitted',
                      'Thank you for applying. Decision letter has been emailed.'))
    return steps


@app.route('/financial-aid')
def financial_aid():
    types = FinancialAidType.query.order_by(FinancialAidType.name).all()
    forms_list = FinancialAidForm.query.order_by(FinancialAidForm.name).all()
    return render_template('financial_aid.html', types=types, forms=forms_list)


@app.route('/financial-aid/types')
def financial_aid_types():
    category = request.args.get('category', '')
    query = FinancialAidType.query
    if category:
        query = query.filter(FinancialAidType.category == category)
    types = query.order_by(FinancialAidType.name).all()
    cats = ['Grant', 'Scholarship', 'Loan', 'Work-Study']
    return render_template('financial_aid_types.html', types=types,
                           categories=cats, current_category=category)


@app.route('/financial-aid/types/<slug>')
def financial_aid_type_detail(slug):
    aid = FinancialAidType.query.filter_by(slug=slug).first_or_404()
    return render_template('financial_aid_type_detail.html', aid=aid)


@app.route('/financial-aid/forms')
def financial_aid_forms():
    audience = request.args.get('audience', '')
    query = FinancialAidForm.query
    if audience:
        query = query.filter(FinancialAidForm.audience == audience)
    forms_list = query.order_by(FinancialAidForm.name).all()
    audiences = ['Undergraduate', 'Graduate', 'International', 'Transfer']
    return render_template('financial_aid_forms.html', forms=forms_list,
                           audiences=audiences, current_audience=audience)


@app.route('/financial-aid/forms/<slug>', methods=['GET', 'POST'])
def financial_aid_form_detail(slug):
    form = FinancialAidForm.query.filter_by(slug=slug).first_or_404()
    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        email = (request.form.get('email') or '').strip()
        if full_name and email:
            s = FinancialAidSubmission(
                form_id=form.id, full_name=full_name, email=email,
                family_income=request.form.get('family_income', type=int) or 0,
                dependents=request.form.get('dependents', type=int) or 0,
                user_id=(current_user.id if current_user.is_authenticated else None))
            db.session.add(s)
            db.session.commit()
            flash(f'{form.name} submitted. Confirmation #{s.id} sent to {email}.', 'success')
            return redirect(url_for('financial_aid_form_detail', slug=slug))
        flash('Name and email are required.', 'danger')
    return render_template('financial_aid_form_detail.html', form=form)


@app.route('/student-life')
def student_life():
    cats = StudentLifeCategory.query.order_by(StudentLifeCategory.name).all()
    return render_template('student_life.html', cats=cats)


@app.route('/student-life/<slug>')
def student_life_category(slug):
    cat = StudentLifeCategory.query.filter_by(slug=slug).first_or_404()
    return render_template('student_life_category.html', cat=cat)


@app.route('/athletics/buckeyes/<slug>')
def athletics_buckeyes_team(slug):
    AthleticTeam.query.filter_by(slug=slug).first_or_404()
    return redirect(url_for('athletics_team', slug=slug), code=301)


@app.route('/athletics/buckeyes/<slug>/schedule')
def athletics_schedule(slug):
    team = AthleticTeam.query.filter_by(slug=slug).first_or_404()
    games = AthleticGame.query.filter_by(team_id=team.id).order_by(
        AthleticGame.game_date).all()
    return render_template('athletics_schedule.html', team=team, games=games)


@app.route('/athletics/buckeyes/<slug>/roster')
def athletics_roster(slug):
    team = AthleticTeam.query.filter_by(slug=slug).first_or_404()
    roster = AthleticRosterMember.query.filter_by(team_id=team.id).order_by(
        AthleticRosterMember.jersey_number).all()
    return render_template('athletics_roster.html', team=team, roster=roster)


@app.route('/athletics/buckeyes/<slug>/stats')
def athletics_stats(slug):
    team = AthleticTeam.query.filter_by(slug=slug).first_or_404()
    games = AthleticGame.query.filter_by(team_id=team.id).all()
    wins = sum(1 for g in games if g.result and g.result.startswith('W'))
    losses = sum(1 for g in games if g.result and g.result.startswith('L'))
    home_games = sum(1 for g in games if g.home_away == 'Home')
    return render_template('athletics_stats.html', team=team,
                           wins=wins, losses=losses,
                           home_games=home_games, total_games=len(games))


@app.route('/athletics/tickets')
def athletics_tickets():
    sport = request.args.get('sport', '')
    query = AthleticGame.query.filter(AthleticGame.home_away == 'Home')
    if sport:
        team_ids = [t.id for t in AthleticTeam.query.filter(
            AthleticTeam.sport == sport).all()]
        query = query.filter(AthleticGame.team_id.in_(team_ids))
    games = query.order_by(AthleticGame.game_date).all()
    sports = sorted({t.sport for t in AthleticTeam.query.all()})
    return render_template('athletics_tickets.html', games=games,
                           sports=sports, current_sport=sport)


@app.route('/athletics/tickets/<int:game_id>', methods=['GET', 'POST'])
def athletics_ticket_detail(game_id):
    game = db.session.get(AthleticGame, game_id)
    if game is None:
        abort(404)
    team = db.session.get(AthleticTeam, game.team_id)
    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        email = (request.form.get('email') or '').strip()
        section = (request.form.get('section') or '30A').strip()
        qty = request.form.get('quantity', type=int) or 1
        if full_name and email and qty > 0:
            price_per = 60 if team.sport == 'Football' else 25
            t = TicketPurchase(game_id=game.id, full_name=full_name,
                               email=email, section=section, quantity=qty,
                               total_price=price_per * qty,
                               user_id=(current_user.id if current_user.is_authenticated else None))
            db.session.add(t)
            db.session.commit()
            flash(f'Tickets purchased. Confirmation #{t.id}. Total ${t.total_price}.', 'success')
            return redirect(url_for('athletics_ticket_detail', game_id=game.id))
        flash('Name, email, and quantity required.', 'danger')
    return render_template('athletics_ticket_detail.html', game=game, team=team)


@app.route('/library')
def library_index():
    branches = LibraryBranch.query.order_by(LibraryBranch.name).all()
    return render_template('library.html', branches=branches)


@app.route('/library/study-room/reserve', methods=['GET', 'POST'])
def library_study_room_reserve():
    branches = LibraryBranch.query.filter_by(has_study_rooms=True).order_by(
        LibraryBranch.name).all()
    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        branch_id = request.form.get('branch_id', type=int)
        reserve_date = (request.form.get('reserve_date') or '').strip()
        start_time = (request.form.get('start_time') or '13:00').strip()
        duration = request.form.get('duration_hours', type=int) or 2
        room = (request.form.get('room_number') or 'A101').strip()
        purpose = (request.form.get('purpose') or '').strip()
        if full_name and branch_id and reserve_date:
            r = LibraryRoomReservation(
                branch_id=branch_id, full_name=full_name,
                room_number=room, reserve_date=reserve_date,
                start_time=start_time, duration_hours=duration,
                purpose=purpose,
                user_id=(current_user.id if current_user.is_authenticated else None))
            db.session.add(r)
            db.session.commit()
            flash(f'Study room {room} reserved on {reserve_date} at {start_time}. '
                  f'Confirmation #{r.id}.', 'success')
            return redirect(url_for('library_study_room_reserve'))
        flash('Please complete all required fields.', 'danger')
    return render_template('library_study_room.html', branches=branches)


@app.route('/library/<slug>')
def library_branch(slug):
    branch = LibraryBranch.query.filter_by(slug=slug).first_or_404()
    return render_template('library_branch.html', branch=branch)


@app.route('/dining')
def dining_index():
    locations = DiningLocation.query.order_by(DiningLocation.name).all()
    return render_template('dining.html', locations=locations)


@app.route('/dining/order', methods=['GET', 'POST'])
def dining_order():
    locations = DiningLocation.query.order_by(DiningLocation.name).all()
    items = DiningMenuItem.query.order_by(DiningMenuItem.name).limit(60).all()
    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        item_id = request.form.get('item_id', type=int)
        location_id = request.form.get('location_id', type=int)
        qty = request.form.get('quantity', type=int) or 1
        pickup = (request.form.get('pickup_time') or '12:00').strip()
        if full_name and item_id and location_id:
            o = DiningOrder(location_id=location_id, item_id=item_id,
                            full_name=full_name, pickup_time=pickup,
                            quantity=qty,
                            special_instructions=(request.form.get('special_instructions') or '').strip(),
                            user_id=(current_user.id if current_user.is_authenticated else None))
            db.session.add(o)
            db.session.commit()
            flash(f'Order #{o.id} placed for pickup at {pickup}.', 'success')
            return redirect(url_for('dining_order'))
        flash('Name, item, and location are required.', 'danger')
    return render_template('dining_order.html', locations=locations, items=items)


@app.route('/dining/menu/<slug>/<date>')
def dining_menu(slug, date):
    location = DiningLocation.query.filter_by(slug=slug).first_or_404()
    items = DiningMenuItem.query.filter_by(location_id=location.id).order_by(
        DiningMenuItem.meal, DiningMenuItem.name).all()
    return render_template('dining_menu.html', location=location,
                           items=items, date=date)


@app.route('/dining/<slug>')
def dining_location(slug):
    location = DiningLocation.query.filter_by(slug=slug).first_or_404()
    items = DiningMenuItem.query.filter_by(location_id=location.id).order_by(
        DiningMenuItem.meal, DiningMenuItem.name).all()
    return render_template('dining_location.html', location=location, items=items)


@app.route('/buckeye-link')
def buckeye_link():
    services = CampusService.query.order_by(CampusService.category,
                                            CampusService.name).all()
    return render_template('buckeye_link.html', services=services)


@app.route('/buckeyeid')
def buckeyeid():
    return render_template('buckeyeid.html')


@app.route('/services')
def services_index():
    category = request.args.get('category', '')
    query = CampusService.query
    if category:
        query = query.filter(CampusService.category == category)
    services = query.order_by(CampusService.name).all()
    cats = sorted({s.category for s in CampusService.query.all()})
    return render_template('services.html', services=services,
                           categories=cats, current_category=category)


@app.route('/services/<slug>', methods=['GET', 'POST'])
def service_detail(slug):
    service = CampusService.query.filter_by(slug=slug).first_or_404()
    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        email = (request.form.get('email') or '').strip()
        rtype = (request.form.get('request_type') or 'general').strip()
        desc = (request.form.get('description') or '').strip()
        if full_name and email and desc:
            sr = ServiceRequest(
                service_slug=service.slug, full_name=full_name,
                email=email, request_type=rtype, description=desc,
                user_id=(current_user.id if current_user.is_authenticated else None))
            db.session.add(sr)
            db.session.commit()
            flash(f'Service request submitted. Ticket #{sr.id}.', 'success')
            return redirect(url_for('service_detail', slug=slug))
        flash('Please complete name, email, and description.', 'danger')
    return render_template('service_detail.html', service=service)


@app.route('/alumni')
def alumni_index():
    chapters = AlumniChapter.query.order_by(AlumniChapter.region).all()
    total_members = sum(c.members for c in chapters)
    return render_template('alumni.html', chapters=chapters,
                           total_members=total_members)


@app.route('/alumni/chapter/<slug>', methods=['GET', 'POST'])
def alumni_chapter(slug):
    chapter = AlumniChapter.query.filter_by(slug=slug).first_or_404()
    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        email = (request.form.get('email') or '').strip()
        grad_year = request.form.get('graduation_year', type=int) or 2020
        degree = (request.form.get('degree') or 'BA').strip()
        if full_name and email:
            m = AlumniMembership(
                chapter_id=chapter.id, full_name=full_name,
                email=email, graduation_year=grad_year, degree=degree,
                user_id=(current_user.id if current_user.is_authenticated else None))
            db.session.add(m)
            chapter.members = (chapter.members or 0) + 1
            db.session.commit()
            flash(f'Welcome to the {chapter.region} chapter! Membership #{m.id}.', 'success')
            return redirect(url_for('alumni_chapter', slug=slug))
        flash('Name and email required.', 'danger')
    return render_template('alumni_chapter.html', chapter=chapter)


@app.route('/giving')
def giving_index():
    funds = GivingFund.query.order_by(GivingFund.name).all()
    return render_template('giving.html', funds=funds)


@app.route('/giving/<slug>', methods=['GET', 'POST'])
def giving_fund(slug):
    fund = GivingFund.query.filter_by(slug=slug).first_or_404()
    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        email = (request.form.get('email') or '').strip()
        amount = request.form.get('amount', type=int) or fund.minimum_gift
        recurring = (request.form.get('is_recurring') == 'on')
        honor = (request.form.get('in_honor_of') or '').strip()
        if full_name and email and amount >= fund.minimum_gift:
            d = Donation(fund_id=fund.id, full_name=full_name, email=email,
                         amount=amount, is_recurring=recurring,
                         in_honor_of=honor,
                         user_id=(current_user.id if current_user.is_authenticated else None))
            db.session.add(d)
            fund.raised_amount = (fund.raised_amount or 0) + amount
            db.session.commit()
            flash(f'Thank you for your ${amount} gift! Receipt #{d.id}.', 'success')
            return redirect(url_for('giving_fund', slug=slug))
        flash(f'Minimum gift is ${fund.minimum_gift}.', 'danger')
    return render_template('giving_fund.html', fund=fund)


@app.route('/about/leadership')
def about_leadership():
    leaders = CollegeLeader.query.order_by(CollegeLeader.rank,
                                            CollegeLeader.name).all()
    return render_template('about_leadership.html', leaders=leaders)


@app.route('/about/leadership/<slug>')
def leader_detail(slug):
    leader = CollegeLeader.query.filter_by(slug=slug).first_or_404()
    return render_template('leader_detail.html', leader=leader)


@app.route('/about/history')
def about_history():
    milestones = HistoryMilestone.query.order_by(HistoryMilestone.year).all()
    return render_template('about_history.html', milestones=milestones)


@app.route('/about/diversity')
def about_diversity():
    programs = DiversityProgram.query.order_by(DiversityProgram.name).all()
    return render_template('about_diversity.html', programs=programs)


@app.route('/contact-faculty/<slug>', methods=['GET', 'POST'])
def contact_faculty(slug):
    member = Faculty.query.filter_by(slug=slug).first_or_404()
    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        email = (request.form.get('email') or '').strip()
        subject = (request.form.get('subject') or '').strip()
        message = (request.form.get('message') or '').strip()
        if full_name and email and message:
            c = ContactInquiry(faculty_id=member.id, full_name=full_name,
                               email=email, subject=subject, message=message,
                               user_id=(current_user.id if current_user.is_authenticated else None))
            db.session.add(c)
            db.session.commit()
            flash(f'Message sent to {member.name}. Reference #{c.id}.', 'success')
            return redirect(url_for('contact_faculty', slug=slug))
        flash('Name, email, and message are required.', 'danger')
    return render_template('contact_faculty.html', member=member)


@app.route('/events/<int:event_id>/rsvp', methods=['POST'])
def event_rsvp(event_id):
    event = db.session.get(Event, event_id)
    if event is None:
        abort(404)
    full_name = (request.form.get('full_name') or '').strip()
    email = (request.form.get('email') or '').strip()
    guests = request.form.get('guests', type=int) or 0
    if full_name and email:
        r = EventRSVP(event_id=event.id, full_name=full_name, email=email,
                      guests=guests,
                      user_id=(current_user.id if current_user.is_authenticated else None))
        db.session.add(r)
        db.session.commit()
        flash(f'RSVP confirmed for "{event.title}". Reference #{r.id}.', 'success')
    else:
        flash('Name and email required for RSVP.', 'danger')
    return redirect(url_for('event_detail', event_id=event.id))


@app.route('/transcript/request', methods=['GET', 'POST'])
def transcript_request():
    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        email = (request.form.get('email') or '').strip()
        student_id = (request.form.get('student_id') or '').strip()
        delivery = (request.form.get('delivery') or 'electronic').strip()
        recipient = (request.form.get('recipient') or '').strip()
        if full_name and email and student_id:
            t = TranscriptRequest(full_name=full_name, email=email,
                                  student_id=student_id, delivery=delivery,
                                  recipient=recipient,
                                  user_id=(current_user.id if current_user.is_authenticated else None))
            db.session.add(t)
            db.session.commit()
            flash(f'Transcript request submitted. Ticket #{t.id}.', 'success')
            return redirect(url_for('transcript_request'))
        flash('Name, email, and student ID required.', 'danger')
    return render_template('transcript_request.html')


@app.route('/info/request', methods=['GET', 'POST'])
def info_request():
    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        email = (request.form.get('email') or '').strip()
        program = (request.form.get('program_interest') or '').strip()
        state = (request.form.get('home_state') or 'Ohio').strip()
        if full_name and email:
            ir = InfoRequest(full_name=full_name, email=email,
                             program_interest=program, home_state=state,
                             user_id=(current_user.id if current_user.is_authenticated else None))
            db.session.add(ir)
            db.session.commit()
            flash(f'Information packet on the way to {email}. Reference #{ir.id}.', 'success')
            return redirect(url_for('info_request'))
        flash('Name and email required.', 'danger')
    return render_template('info_request.html')


@app.route('/news/<slug>/comment', methods=['POST'])
def news_comment(slug):
    article = NewsArticle.query.filter_by(slug=slug).first_or_404()
    author_name = (request.form.get('author_name') or '').strip()
    body = (request.form.get('body') or '').strip()
    if author_name and body:
        c = NewsComment(article_id=article.id, author_name=author_name,
                        body=body,
                        user_id=(current_user.id if current_user.is_authenticated else None))
        db.session.add(c)
        db.session.commit()
        flash('Comment posted.', 'success')
    else:
        flash('Name and comment body required.', 'danger')
    return redirect(url_for('news_article', slug=slug))


@app.route('/account/update', methods=['POST'])
@login_required
def account_update():
    full_name = (request.form.get('full_name') or '').strip()
    bio = (request.form.get('bio') or '').strip()
    if full_name:
        current_user.full_name = full_name
    if bio is not None:
        current_user.bio = bio
    db.session.commit()
    flash('Profile updated.', 'success')
    return redirect(url_for('account'))


@app.route('/_health')
def health():
    try:
        college_count = College.query.count()
        program_count = Program.query.count()
        return jsonify({
            'ok': True,
            'site': 'osu',
            'colleges': college_count,
            'programs': program_count,
        })
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)}), 500


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


# ─── Startup ──────────────────────────────────────────────────────────────────

# ─── Startup ──────────────────────────────────────────────────────────────────

def ensure_demo_data():
    """Seed activated tables with deterministic demo rows.

    Idempotent: each table is gated on COUNT()==0 so re-runs are no-ops.
    Not in instance_seed/ — runs at app startup after seed_extended().
    This populates list/status pages that real users would otherwise see empty.
    """
    base_dt = datetime(2026, 1, 15, 9, 0, 0)

    # ── applications (Application status tracker) ───────────────────────────
    if Application.query.count() == 0:
        apps_seed = [
            # (full_name, email, level, program, citizenship, high_school,
            #  status, days_after_base)
            ('Maya Patel', 'maya.patel@example.com', 'undergraduate',
             'Computer Science and Engineering', 'United States',
             'Upper Arlington High School', 'accepted', 2),
            ('Tyler Brennan', 'tyler.brennan@example.com', 'undergraduate',
             'Mechanical Engineering', 'United States',
             'Westerville North High School', 'accepted', 5),
            ('Wei Zhang', 'wei.zhang@example.com', 'graduate',
             'Statistics MS', 'China',
             'Tsinghua University', 'under-review', 8),
            ('Sofia Hernandez', 'sofia.hernandez@example.com', 'undergraduate',
             'Nursing', 'United States',
             'Hilliard Davidson High School', 'accepted', 11),
            ('Jamal Carter', 'jamal.carter@example.com', 'undergraduate',
             'Finance — Fisher College of Business', 'United States',
             'Cleveland Heights High School', 'waitlisted', 14),
            ('Aanya Iyer', 'aanya.iyer@example.com', 'international',
             'Electrical and Computer Engineering MS', 'India',
             'Delhi Public School', 'under-review', 17),
            ('Connor O\'Reilly', 'connor.oreilly@example.com', 'transfer',
             'Political Science', 'United States',
             'Columbus State Community College', 'submitted', 22),
            ('Hannah Kim', 'hannah.kim@example.com', 'undergraduate',
             'Marketing — Fisher College of Business', 'South Korea',
             'Daegu Foreign Language High School', 'accepted', 26),
            ('Marcus Johnson', 'marcus.johnson@example.com', 'graduate',
             'Public Health MPH', 'United States',
             'Howard University', 'under-review', 30),
            ('Olivia Schmidt', 'olivia.schmidt@example.com', 'undergraduate',
             'Architecture', 'United States',
             'Dublin Coffman High School', 'submitted', 35),
            ('Diego Ramirez', 'diego.ramirez@example.com', 'transfer',
             'Aerospace Engineering', 'Mexico',
             'Tecnológico de Monterrey', 'accepted', 41),
            ('Priya Singh', 'priya.singh@example.com', 'graduate',
             'Materials Science and Engineering PhD', 'India',
             'IIT Bombay', 'accepted', 48),
            ('Ethan Walker', 'ethan.walker@example.com', 'undergraduate',
             'Psychology', 'United States',
             'New Albany High School', 'submitted', 55),
            ('Grace Liu', 'grace.liu@example.com', 'international',
             'Biomedical Engineering', 'China',
             'Shanghai High School International Division',
             'under-review', 62),
        ]
        for (name, email, level, program, citizenship, hs, status,
             days) in apps_seed:
            db.session.add(Application(
                full_name=name, email=email, level=level, program=program,
                citizenship=citizenship, high_school=hs,
                statement=('I want to study {} at Ohio State because the '
                           'program is a top match for my goals.').format(
                               program.split(' ')[0]),
                status=status,
                submitted_at=base_dt + timedelta(days=days),
            ))

    # ── tour_bookings (Campus visit list) ───────────────────────────────────
    if TourBooking.query.count() == 0:
        tours_seed = [
            # (full_name, email, tour_date, tour_type, group_size, notes, days)
            ('Patel Family', 'maya.patel@example.com', '2026-06-14',
             'in-person', 4, 'Two parents and one sibling.', 1),
            ('Brennan Family', 'tyler.brennan@example.com', '2026-06-15',
             'in-person', 3, '', 3),
            ('Sofia Hernandez', 'sofia.hernandez@example.com', '2026-06-20',
             'in-person', 2, 'Interested in nursing facilities.', 5),
            ('Carter Family', 'jamal.carter@example.com', '2026-06-21',
             'virtual', 1, '', 7),
            ('Aanya Iyer', 'aanya.iyer@example.com', '2026-06-22',
             'virtual', 1, 'India time zone — please confirm 8 a.m. ET.', 9),
            ('O\'Reilly Family', 'connor.oreilly@example.com', '2026-06-28',
             'in-person', 5, 'Wheelchair accessibility requested.', 11),
            ('Kim Family', 'hannah.kim@example.com', '2026-07-02',
             'in-person', 4, '', 13),
            ('Marcus Johnson', 'marcus.johnson@example.com', '2026-07-05',
             'virtual', 1, 'Graduate program inquiry.', 15),
            ('Schmidt Family', 'olivia.schmidt@example.com', '2026-07-09',
             'in-person', 3, '', 17),
            ('Ramirez Family', 'diego.ramirez@example.com', '2026-07-12',
             'in-person', 2, 'Spanish-language tour guide if available.', 19),
            ('Walker Family', 'ethan.walker@example.com', '2026-07-14',
             'in-person', 4, '', 22),
            ('Liu Family', 'grace.liu@example.com', '2026-07-16',
             'virtual', 2, '', 24),
            ('Nguyen Family', 'thuy.nguyen@example.com', '2026-07-18',
             'in-person', 3, 'Interested in Honors program.', 27),
            ('Anderson Family', 'kate.anderson@example.com', '2026-07-22',
             'in-person', 2, '', 29),
            ('Park Family', 'minjun.park@example.com', '2026-07-25',
             'virtual', 1, '', 31),
            ('Williams Family', 'sara.williams@example.com', '2026-08-01',
             'in-person', 5, 'Twin daughters both applying.', 34),
        ]
        for (name, email, date, ttype, gsize, notes, days) in tours_seed:
            db.session.add(TourBooking(
                full_name=name, email=email, tour_date=date,
                tour_type=ttype, group_size=gsize, notes=notes,
                created_at=base_dt + timedelta(days=days),
            ))

    # ── event_rsvps (RSVP rollup on event_detail) ───────────────────────────
    if EventRSVP.query.count() == 0:
        event_ids = [e.id for e in
                     Event.query.order_by(Event.id).limit(20).all()]
        if event_ids:
            rsvp_names = [
                ('Maya Patel', 'maya.patel@example.com', 1),
                ('Tyler Brennan', 'tyler.brennan@example.com', 0),
                ('Sofia Hernandez', 'sofia.hernandez@example.com', 2),
                ('Jamal Carter', 'jamal.carter@example.com', 1),
                ('Aanya Iyer', 'aanya.iyer@example.com', 0),
                ('Connor O\'Reilly', 'connor.oreilly@example.com', 1),
                ('Hannah Kim', 'hannah.kim@example.com', 0),
                ('Marcus Johnson', 'marcus.johnson@example.com', 2),
                ('Olivia Schmidt', 'olivia.schmidt@example.com', 1),
                ('Diego Ramirez', 'diego.ramirez@example.com', 0),
                ('Priya Singh', 'priya.singh@example.com', 1),
                ('Ethan Walker', 'ethan.walker@example.com', 0),
                ('Grace Liu', 'grace.liu@example.com', 2),
                ('Thuy Nguyen', 'thuy.nguyen@example.com', 1),
                ('Kate Anderson', 'kate.anderson@example.com', 0),
                ('Minjun Park', 'minjun.park@example.com', 1),
                ('Sara Williams', 'sara.williams@example.com', 3),
                ('Logan Reed', 'logan.reed@example.com', 0),
                ('Eli Morgan', 'eli.morgan@example.com', 1),
                ('Naomi Bauer', 'naomi.bauer@example.com', 0),
            ]
            # Distribute: roughly 2-4 RSVPs per event for first 8 events
            offset = 0
            for ev_idx, ev_id in enumerate(event_ids[:10]):
                count = 3 + (ev_idx % 3)  # 3,4,5,3,4,5,...
                for i in range(count):
                    name, email, guests = rsvp_names[
                        (offset + i) % len(rsvp_names)]
                    db.session.add(EventRSVP(
                        event_id=ev_id, full_name=name, email=email,
                        guests=guests,
                        created_at=base_dt + timedelta(
                            days=ev_idx * 2, hours=i),
                    ))
                offset += count

    # ── library_room_reservations (Library reservations list) ───────────────
    if LibraryRoomReservation.query.count() == 0:
        branch_ids = [b.id for b in
                      LibraryBranch.query.filter_by(
                          has_study_rooms=True).order_by(
                              LibraryBranch.id).all()]
        if branch_ids:
            lib_seed = [
                # (name, room, date, start, dur, purpose, days)
                ('Maya Patel', 'A201', '2026-06-13', '10:00', 2,
                 'CSE 2231 study group', 0),
                ('Tyler Brennan', 'B105', '2026-06-13', '14:00', 2,
                 'Math 1151 problem set', 1),
                ('Wei Zhang', 'C310', '2026-06-14', '09:00', 3,
                 'Stat 5301 project meeting', 2),
                ('Sofia Hernandez', 'A202', '2026-06-15', '16:00', 2,
                 'NURS 3210 case study', 3),
                ('Jamal Carter', 'B107', '2026-06-16', '11:00', 2,
                 'BUSFIN 4221 group prep', 5),
                ('Aanya Iyer', 'C311', '2026-06-17', '13:00', 4,
                 'ECE 6712 lab report', 6),
                ('Connor O\'Reilly', 'A203', '2026-06-18', '15:00', 2,
                 'POL SCI 3115 thesis', 8),
                ('Hannah Kim', 'B108', '2026-06-19', '10:00', 3,
                 'BUS MGT 3230 marketing project', 10),
                ('Marcus Johnson', 'C312', '2026-06-20', '14:00', 2,
                 'PUBHLTH 6020 capstone', 12),
                ('Olivia Schmidt', 'A204', '2026-06-21', '09:00', 2,
                 'ARCH 2310 portfolio review', 13),
                ('Diego Ramirez', 'B109', '2026-06-22', '13:00', 3,
                 'AEROENG 4193 design build', 15),
                ('Priya Singh', 'C313', '2026-06-23', '10:00', 2,
                 'MSE 8001 lit review', 17),
                ('Ethan Walker', 'A205', '2026-06-24', '14:00', 2,
                 'PSYCH 3331 paper', 18),
                ('Grace Liu', 'B110', '2026-06-25', '11:00', 3,
                 'BME 5181 group project', 20),
                ('Thuy Nguyen', 'C314', '2026-06-26', '09:00', 2,
                 'Honors thesis writing', 22),
                ('Kate Anderson', 'A206', '2026-06-27', '15:00', 2,
                 'HIST 3700 reading group', 24),
                ('Minjun Park', 'B111', '2026-06-28', '10:00', 2,
                 '', 26),
                ('Sara Williams', 'C315', '2026-06-29', '13:00', 3,
                 'CSE 5523 final project', 28),
                ('Logan Reed', 'A207', '2026-06-30', '16:00', 2,
                 '', 30),
                ('Eli Morgan', 'B112', '2026-07-01', '11:00', 2,
                 'BIOLOGY 2100 study group', 31),
            ]
            for i, (name, room, date, start, dur, purpose, days) in enumerate(
                    lib_seed):
                db.session.add(LibraryRoomReservation(
                    branch_id=branch_ids[i % len(branch_ids)],
                    full_name=name, room_number=room,
                    reserve_date=date, start_time=start,
                    duration_hours=dur, purpose=purpose,
                    created_at=base_dt + timedelta(days=days),
                ))

    db.session.commit()


with app.app_context():
    fresh = not os.path.exists(os.path.join(BASE_DIR, 'instance', 'osu.db'))
    db.create_all()
    from seed_data import seed
    seed()
    from seed_extras2 import seed_extended
    seed_extended()
    ensure_demo_data()
    if fresh:
        from sqlalchemy import text
        conn = db.engine.connect()
        idx_rows = conn.execute(text(
            "SELECT name, sql FROM sqlite_master WHERE type='index' AND name LIKE 'ix_%'"
        )).fetchall()
        for name, _ in idx_rows:
            conn.execute(text(f"DROP INDEX IF EXISTS {name}"))
        for name, sql in sorted(idx_rows, key=lambda r: r[0]):
            if sql:
                conn.execute(text(sql))
        conn.execute(text("VACUUM"))
        conn.commit()
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=40015, debug=False)


# --- perf: long-term cache for /static/ assets (added 2026-05-27) ---
@app.after_request
def _add_static_cache_headers(resp):
    try:
        if request.path.startswith('/static/'):
            resp.headers['Cache-Control'] = 'public, max-age=86400, immutable'
    except Exception:
        pass
    return resp
# --- end perf ---

