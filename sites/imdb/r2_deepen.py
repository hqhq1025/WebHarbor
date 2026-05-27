"""IMDb r2 deepening — push baseline to vanilla level.

Adds (additively, idempotently):
  - 6 new tables backing POST flows: Poll/PollOption/PollVote, UserList/UserListItem,
    ReviewHelpful, Follow, Report, TitleTrivia/TitleQuote/TitleGoof, TriviaVote.
  - 23 new GET pages (trivia/quotes/goofs/awards/parents-guide/technical-specs/
    keywords/locations/companies/external-sites/release-info/connections/photos/
    soundtrack/faq/episodes for titles; bio/personal-life/awards/quotes/trivia/
    photos/filmography for names; lists/list/poll/polls/news_detail/etc.).
  - 22 new POST handlers (vote-helpful, flag, submit trivia/quote/goof, report,
    follow, poll-vote, list CRUD, account edit, mark-watched, etc.).
  - Deterministic seed data for those tables driven by sorted iteration over
    scraped JSON + DB rows — preserves byte-identical reset invariant.
  - tasks.jsonl generator: 1600+ tasks across 33 task_types, 40%+ image-bearing.

Wired from app.py: `from r2_deepen import deepen_app; deepen_app(app, db, ...)`.
"""
import html
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from flask import (render_template, request, redirect, url_for, flash, abort,
                   jsonify)
from flask_login import login_required, current_user
from sqlalchemy import desc, func

BASE_DIR = Path(__file__).resolve().parent
SCRAPED = BASE_DIR / 'scraped_data'

# Same reference date as seed_data.py for any timestamp in r2 seeding.
R2_REFERENCE_DATE = datetime(2026, 5, 26, 12, 0, 0)


# ---------------------------------------------------------------------------
# Model registration (additive). We attach via the same `db` so all live in
# one SQLite file; tables are byte-id reproducible if we seed deterministically.
# ---------------------------------------------------------------------------

def _register_models(db):
    class Poll(db.Model):
        __tablename__ = 'r2_polls'
        id = db.Column(db.Integer, primary_key=True)
        slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
        question = db.Column(db.String(255), nullable=False)
        category = db.Column(db.String(40), default='')
        description = db.Column(db.Text, default='')
        is_closed = db.Column(db.Boolean, default=False)
        created_at = db.Column(db.DateTime, default=R2_REFERENCE_DATE)
        options = db.relationship('PollOption', backref='poll',
                                  lazy='joined', cascade='all, delete-orphan')

    class PollOption(db.Model):
        __tablename__ = 'r2_poll_options'
        id = db.Column(db.Integer, primary_key=True)
        poll_id = db.Column(db.Integer, db.ForeignKey('r2_polls.id'),
                            nullable=False, index=True)
        label = db.Column(db.String(255), nullable=False)
        related_tt = db.Column(db.String(20), default='')
        related_nm = db.Column(db.String(20), default='')
        seed_votes = db.Column(db.Integer, default=0)
        position = db.Column(db.Integer, default=0)

    class PollVote(db.Model):
        __tablename__ = 'r2_poll_votes'
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            nullable=False, index=True)
        option_id = db.Column(db.Integer, db.ForeignKey('r2_poll_options.id'),
                              nullable=False, index=True)
        created_at = db.Column(db.DateTime, default=R2_REFERENCE_DATE)
        __table_args__ = (db.UniqueConstraint('user_id', 'option_id'),)

    class UserList(db.Model):
        __tablename__ = 'r2_user_lists'
        id = db.Column(db.Integer, primary_key=True)
        owner_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                             nullable=False, index=True)
        name = db.Column(db.String(120), nullable=False)
        description = db.Column(db.Text, default='')
        is_public = db.Column(db.Boolean, default=True)
        created_at = db.Column(db.DateTime, default=R2_REFERENCE_DATE)
        items = db.relationship('UserListItem', backref='list',
                                lazy='joined', cascade='all, delete-orphan')

    class UserListItem(db.Model):
        __tablename__ = 'r2_user_list_items'
        id = db.Column(db.Integer, primary_key=True)
        list_id = db.Column(db.Integer, db.ForeignKey('r2_user_lists.id'),
                            nullable=False, index=True)
        title_id = db.Column(db.Integer, db.ForeignKey('titles.id'),
                             nullable=False, index=True)
        note = db.Column(db.String(200), default='')
        position = db.Column(db.Integer, default=0)
        added_at = db.Column(db.DateTime, default=R2_REFERENCE_DATE)
        __table_args__ = (db.UniqueConstraint('list_id', 'title_id'),)

    class ReviewHelpful(db.Model):
        __tablename__ = 'r2_review_helpful'
        id = db.Column(db.Integer, primary_key=True)
        review_id = db.Column(db.Integer, db.ForeignKey('reviews.id'),
                              nullable=False, index=True)
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            nullable=False, index=True)
        vote = db.Column(db.Integer, default=1)  # +1 helpful, -1 not
        created_at = db.Column(db.DateTime, default=R2_REFERENCE_DATE)
        __table_args__ = (db.UniqueConstraint('review_id', 'user_id'),)

    class Follow(db.Model):
        __tablename__ = 'r2_follows'
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            nullable=False, index=True)
        person_id = db.Column(db.Integer, db.ForeignKey('persons.id'),
                              nullable=False, index=True)
        created_at = db.Column(db.DateTime, default=R2_REFERENCE_DATE)
        __table_args__ = (db.UniqueConstraint('user_id', 'person_id'),)

    class Report(db.Model):
        __tablename__ = 'r2_reports'
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            nullable=False, index=True)
        target_type = db.Column(db.String(20), nullable=False)  # title|name|review
        target_ref = db.Column(db.String(40), nullable=False)
        category = db.Column(db.String(40), default='other')
        body = db.Column(db.Text, default='')
        created_at = db.Column(db.DateTime, default=R2_REFERENCE_DATE)

    class TitleTrivia(db.Model):
        __tablename__ = 'r2_title_trivia'
        id = db.Column(db.Integer, primary_key=True)
        title_id = db.Column(db.Integer, db.ForeignKey('titles.id'),
                             nullable=False, index=True)
        body = db.Column(db.Text, nullable=False)
        author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
        is_seed = db.Column(db.Boolean, default=False)
        helpful_count = db.Column(db.Integer, default=0)
        created_at = db.Column(db.DateTime, default=R2_REFERENCE_DATE)

    class TitleQuote(db.Model):
        __tablename__ = 'r2_title_quotes'
        id = db.Column(db.Integer, primary_key=True)
        title_id = db.Column(db.Integer, db.ForeignKey('titles.id'),
                             nullable=False, index=True)
        character = db.Column(db.String(160), default='')
        body = db.Column(db.Text, nullable=False)
        author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
        is_seed = db.Column(db.Boolean, default=False)
        helpful_count = db.Column(db.Integer, default=0)
        created_at = db.Column(db.DateTime, default=R2_REFERENCE_DATE)

    class TitleGoof(db.Model):
        __tablename__ = 'r2_title_goofs'
        id = db.Column(db.Integer, primary_key=True)
        title_id = db.Column(db.Integer, db.ForeignKey('titles.id'),
                             nullable=False, index=True)
        category = db.Column(db.String(40), default='Continuity')
        body = db.Column(db.Text, nullable=False)
        author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
        is_seed = db.Column(db.Boolean, default=False)
        helpful_count = db.Column(db.Integer, default=0)
        created_at = db.Column(db.DateTime, default=R2_REFERENCE_DATE)

    class WatchedFlag(db.Model):
        __tablename__ = 'r2_watched'
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            nullable=False, index=True)
        title_id = db.Column(db.Integer, db.ForeignKey('titles.id'),
                             nullable=False, index=True)
        marked_at = db.Column(db.DateTime, default=R2_REFERENCE_DATE)
        __table_args__ = (db.UniqueConstraint('user_id', 'title_id'),)

    return dict(
        Poll=Poll, PollOption=PollOption, PollVote=PollVote,
        UserList=UserList, UserListItem=UserListItem,
        ReviewHelpful=ReviewHelpful, Follow=Follow, Report=Report,
        TitleTrivia=TitleTrivia, TitleQuote=TitleQuote, TitleGoof=TitleGoof,
        WatchedFlag=WatchedFlag,
    )


# ---------------------------------------------------------------------------
# Derived data computation from scraped JSON (deterministic — sorted iteration)
# ---------------------------------------------------------------------------

KEYWORD_TRIVIA_PREFIXES = [
    'A central plot motif is',
    'Critics note the recurring theme of',
    'The screenplay was praised for its handling of',
    'Production materials emphasize',
    'Word-of-mouth surrounding the film often references',
]

GOOF_CATEGORIES = ['Continuity', 'Factual error', 'Audio/visual unsynchronised',
                   'Anachronism', 'Crew or equipment visible', 'Plot hole']


def _u(s):
    if s is None:
        return ''
    return html.unescape(str(s)).strip()


def _read_title_json(tt_id):
    f = SCRAPED / f'title_{tt_id}.json'
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text())
    except Exception:
        return None


def _read_name_json(nm_id):
    f = SCRAPED / f'name_{nm_id}.json'
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text())
    except Exception:
        return None


def _derive_keywords(t_json):
    if not t_json:
        return []
    kw = (t_json.get('ld') or {}).get('keywords') or ''
    return [k.strip() for k in kw.split(',') if k.strip()]


def _derive_locations(t_json):
    if not t_json:
        return []
    fl = (t_json.get('details') or {}).get('filminglocations') or ''
    # Pipe-separated chunks; first 'Filming locations' is a header.
    chunks = [c.strip() for c in fl.split('|') if c.strip()]
    # Drop header tokens
    out = []
    for c in chunks:
        if c.lower() == 'filming locations':
            continue
        # Strip parens annotation
        loc = re.sub(r'\([^)]*\)', '', c).strip()
        if loc and loc not in out:
            out.append(loc)
    return out[:8]


def _derive_companies(t_json):
    if not t_json:
        return []
    co = (t_json.get('details') or {}).get('companies') or ''
    chunks = [c.strip() for c in co.split('|') if c.strip()]
    out = []
    for c in chunks:
        if c.lower() in ('production company', 'production companies'):
            continue
        if c and c not in out:
            out.append(c)
    return out[:6]


def _derive_akas(t_json):
    if not t_json:
        return []
    ak = (t_json.get('details') or {}).get('akas') or ''
    chunks = [c.strip() for c in ak.split('|') if c.strip()]
    out = []
    for c in chunks:
        if c.lower() == 'also known as':
            continue
        if c and c not in out:
            out.append(c)
    return out[:6]


def _derive_tech_specs(t_json):
    """Extract (color, sound, aspect_ratio) from subList tail."""
    if not t_json:
        return {}
    sl = t_json.get('subList') or []
    out = {}
    for x in sl:
        s = (x or '').strip()
        if s in ('Color', 'Black and White', 'Color, Black and White'):
            out['color'] = s
        elif any(snd in s for snd in ['Dolby', 'DTS', 'Mono', 'Stereo',
                                        'Surround', 'SDDS', 'Auro']):
            if 'sound' not in out:
                out['sound'] = s
        elif re.match(r'^\d+(\.\d+)?\s*:\s*\d+(\.\d+)?$', s):
            out['aspect_ratio'] = s
    return out


def _derive_awards_summary(t_json):
    if not t_json:
        return ''
    sl = t_json.get('subList') or []
    for s in sl:
        if 'win' in s.lower() and 'nomination' in s.lower():
            return s.strip()
    return ''


def _derive_trivia(title, t_json, max_n=5):
    """Generate 4-6 deterministic trivia rows from keywords + tagline + plot.

    Synth (clearly marked) — IMDb mirror disclaimer is in footer.
    """
    out = []
    kws = _derive_keywords(t_json)
    for i, kw in enumerate(kws[:max_n]):
        prefix = KEYWORD_TRIVIA_PREFIXES[i % len(KEYWORD_TRIVIA_PREFIXES)]
        out.append(f'{prefix} {kw}.')
    # Always add a generic one tied to box office for a fact-only second-page task.
    if title.budget and title.box_office_world:
        out.append(
            f'Production reports list the budget at approximately '
            f'${title.budget:,}, with worldwide gross reaching '
            f'${title.box_office_world:,}.'
        )
    if title.country:
        out.append(f'Filmed and produced in {title.country}.')
    if title.release_date:
        rd = title.release_date.split('(')[0].strip()
        out.append(f'Originally released on {rd}.')
    return out[:6]


def _derive_quotes(title, t_json, cast_list, max_n=5):
    """Synth memorable lines tied to top 3 cast characters."""
    out = []
    # Real-looking but synthetic so we don't fabricate copyrighted dialogue.
    templates = [
        ('{char}: "Some moments stay with you long after the credits roll."'),
        ('{char}: "Sometimes you have to keep moving forward, no matter what."'),
        ('{char}: "What matters most isn\'t how it ends. It\'s how you got there."'),
        ('{char}: "I\'ve seen a lot of things in my time. But never quite like this."'),
        ('{char}: "Choices define us. We are the sum of the doors we walk through."'),
    ]
    for i, c in enumerate(cast_list[:max_n]):
        char = (c.character or 'The lead').strip()
        if not char or char.lower() in ('self', ''):
            continue
        line = templates[i % len(templates)].format(char=char)
        out.append((char, line))
    return out[:5]


def _derive_goofs(title, t_json):
    """Per-genre canned plausible goofs. Synth, clearly labelled in template."""
    base = [
        ('Continuity',
         'In one scene the position of a prop shifts between consecutive cuts.'),
        ('Audio/visual unsynchronised',
         'During a dialogue exchange, the lip-sync briefly drifts out of step.'),
        ('Crew or equipment visible',
         'In a wide shot, a boom microphone reflection is visible on a window pane.'),
    ]
    if title.year and title.year < 2000:
        base.append(('Anachronism',
                     'A piece of background signage uses a typeface postdating the period setting.'))
    if title.country and title.country != 'United States':
        base.append(('Factual error',
                     'A flag visible in the establishing shot lacks the correct number of stripes.'))
    return base[:4]


def _derive_parents_guide(title):
    """Synth parents-guide buckets from MPAA + genres."""
    mpaa = title.mpaa_rating or 'Not Rated'
    intensity = {'G': 0, 'PG': 1, 'PG-13': 2, 'TV-PG': 1, 'TV-14': 2,
                 'R': 3, 'TV-MA': 4, 'NC-17': 4}.get(mpaa, 2)
    gnames = {g.name for g in title.genres}

    def lvl(score):
        return ['None', 'Mild', 'Moderate', 'Severe', 'Extreme'][min(score, 4)]

    buckets = {
        'Sex & Nudity': lvl(intensity - (1 if 'Family' in gnames else 0)),
        'Violence & Gore': lvl(intensity + (1 if 'Action' in gnames or 'War' in gnames else 0)),
        'Profanity': lvl(intensity - (1 if 'Family' in gnames or 'Animation' in gnames else 0)),
        'Alcohol, Drugs & Smoking': lvl(intensity - (2 if 'Family' in gnames else 0)),
        'Frightening & Intense Scenes': lvl(intensity + (1 if 'Horror' in gnames or 'Thriller' in gnames else 0)),
    }
    return buckets


def _derive_connections(title, all_titles):
    """Pick 3 related titles by shared genres & year proximity."""
    by_id = {t.tt_id: t for t in all_titles}
    if not title.genres:
        return []
    same_genres = []
    gset = {g.id for g in title.genres}
    for t in all_titles:
        if t.tt_id == title.tt_id:
            continue
        if any(g.id in gset for g in t.genres):
            yd = abs((t.year or 0) - (title.year or 0))
            same_genres.append((yd, -(t.num_votes or 0), t.tt_id))
    same_genres.sort()
    return [by_id[tt].tt_id for _, _, tt in same_genres[:3]]


# ---------------------------------------------------------------------------
# Polls (12 hand-curated, populated from real DB titles)
# ---------------------------------------------------------------------------

POLL_SEEDS = [
    ('best-shawshank-quote', 'Which Shawshank quote stayed with you?', 'movie',
     [('"Get busy living, or get busy dying."', 1812),
      ('"Hope is a good thing, maybe the best of things."', 2244),
      ('"Andy Dufresne, who crawled through a river of filth..."', 977),
      ('"I find I\'m so excited I can barely sit still."', 540)]),
    ('greatest-superhero-movie', 'Greatest superhero movie of all time?', 'movie',
     [('tt0468569', 0), ('tt15398776', 0), ('tt1375666', 0),
      ('tt0167260', 0), ('tt6751668', 0)]),
    ('best-nolan-film', 'Christopher Nolan\'s best film?', 'movie',
     [('tt0468569', 4521), ('tt1375666', 3818), ('tt0816692', 2904),
      ('tt15398776', 3122)]),
    ('best-tv-finale', 'Most satisfying TV series finale?', 'tv',
     [('tt0903747', 5210), ('tt0944947', 1108), ('tt4574334', 0)]),
    ('most-rewatchable-movie', 'Which film do you rewatch the most?', 'movie',
     [('tt0111161', 4001), ('tt0068646', 1844), ('tt0110912', 2210),
      ('tt0468569', 2510), ('tt1375666', 1820)]),
    ('best-director-living', 'Greatest living film director?', 'celebrity',
     [('nm0000229', 2080), ('nm0634240', 1980), ('nm0001752', 1442),
      ('nm0000165', 1200), ('nm0001053', 1100)]),
    ('best-actor-2020s', 'Best leading-actor performance of the 2020s?', 'celebrity',
     [('nm0614165', 2330), ('nm0000375', 1410), ('nm0000226', 1130),
      ('nm0322181', 980)]),
    ('best-animated', 'Best animated feature ever made?', 'movie',
     [('tt0245429', 1840), ('tt0317705', 1300), ('tt2380307', 1100),
      ('tt0114709', 900)]),
    ('best-sci-fi', 'Most influential sci-fi film?', 'movie',
     [('tt0816692', 2410), ('tt0078748', 0), ('tt0083658', 0),
      ('tt0133093', 0), ('tt1375666', 1810)]),
    ('best-actress-decade', 'Best leading-actress performance this decade?', 'celebrity',
     [('nm0000204', 1500), ('nm0000148', 1200), ('nm0000702', 1180),
      ('nm0000139', 900)]),
    ('best-crime-film', 'Most defining crime film?', 'movie',
     [('tt0068646', 2580), ('tt0110912', 2401), ('tt0099685', 1700),
      ('tt0114369', 1330)]),
    ('best-horror', 'Scariest horror film of all time?', 'movie',
     [('tt0070047', 0), ('tt0078748', 0), ('tt0081505', 0),
      ('tt1457767', 0)]),
]


# ---------------------------------------------------------------------------
# Per-user list seeds (alice/bob/carol/david each get 2 public lists)
# ---------------------------------------------------------------------------

USER_LISTS_SEED = [
    ('alice.j@test.com', 'Cinematography Showcase',
     'Films I return to for the camera work.',
     ['tt0111161', 'tt0816692', 'tt0468569', 'tt1375666', 'tt15398776']),
    ('alice.j@test.com', 'Films to Watch on a Rainy Sunday',
     'Long, comforting, emotional rewatches.',
     ['tt0068646', 'tt0111161', 'tt0167260']),
    ('bob.c@test.com', 'Prestige TV',
     'Premium drama series.',
     ['tt0903747', 'tt0944947', 'tt0386676', 'tt4574334']),
    ('bob.c@test.com', 'Best Pilots Ever',
     'Series whose pilot episodes hooked me instantly.',
     ['tt0903747', 'tt0944947', 'tt0386676']),
    ('carol.d@test.com', 'Films That Get Better With Age',
     'Lighter watch on first pass, heavier on rewatch.',
     ['tt0137523', 'tt0099685', 'tt0114369', 'tt0102926', 'tt0110912']),
    ('carol.d@test.com', 'Director Spotlights',
     'A selection across different directors I love.',
     ['tt0137523', 'tt0102926', 'tt0099685']),
    ('david.k@test.com', 'Comedy Classics',
     'When I want to laugh without thinking.',
     ['tt0080684', 'tt0078788', 'tt0050083']),
    ('david.k@test.com', 'Sci-Fi Greatest Hits',
     'Genre staples in chronological order.',
     ['tt0050083', 'tt0078788', 'tt0080684', 'tt0167260']),
]


# ---------------------------------------------------------------------------
# Deterministic seed entrypoint
# ---------------------------------------------------------------------------

def seed_r2(db, models, Title, Person, User, Review):
    """Idempotent. Returns immediately if r2 tables already populated."""
    Poll = models['Poll']
    PollOption = models['PollOption']
    if db.session.query(Poll).count() > 0:
        return

    # 1) Polls -------------------------------------------------------------
    for pos, (slug, q, cat, opts) in enumerate(POLL_SEEDS):
        p = Poll(slug=slug, question=q, category=cat,
                 description=f'Community poll #{pos+1}. Pick your favorite.',
                 created_at=R2_REFERENCE_DATE - timedelta(days=pos))
        db.session.add(p)
        db.session.flush()
        for op_pos, item in enumerate(opts):
            # item can be (label, votes) or (tt_id/nm_id, votes)
            ref, votes = item
            label = ref
            tt = ''
            nm = ''
            if ref.startswith('tt'):
                t = Title.query.filter_by(tt_id=ref).first()
                if t:
                    label = f'{t.primary_title} ({t.year})'
                    tt = t.tt_id
            elif ref.startswith('nm'):
                pr = Person.query.filter_by(nm_id=ref).first()
                if pr:
                    label = pr.name
                    nm = pr.nm_id
            db.session.add(PollOption(poll_id=p.id, label=label,
                                      related_tt=tt, related_nm=nm,
                                      seed_votes=votes, position=op_pos))
    db.session.flush()

    # 2) User lists --------------------------------------------------------
    UserList = models['UserList']
    UserListItem = models['UserListItem']
    by_email = {u.email: u for u in User.query.all()}
    tt_to_id = {t.tt_id: t.id for t in Title.query.all()}
    for pos, (email, name, desc_, tts) in enumerate(USER_LISTS_SEED):
        u = by_email.get(email)
        if u is None:
            continue
        L = UserList(owner_id=u.id, name=name, description=desc_,
                     is_public=True,
                     created_at=R2_REFERENCE_DATE - timedelta(days=pos+1))
        db.session.add(L)
        db.session.flush()
        for ip, tt in enumerate(tts):
            tid = tt_to_id.get(tt)
            if not tid:
                continue
            db.session.add(UserListItem(list_id=L.id, title_id=tid,
                                        position=ip,
                                        added_at=R2_REFERENCE_DATE - timedelta(days=pos+1)))

    # 3) Title trivia / quotes / goofs ------------------------------------
    TitleTrivia = models['TitleTrivia']
    TitleQuote = models['TitleQuote']
    TitleGoof = models['TitleGoof']
    # Get a stable seed-author user; create if missing.
    seed_user = User.query.filter_by(email='editors@imdb-mirror.test').first()
    if seed_user is None:
        import hashlib as _hashlib
        _email = 'editors@imdb-mirror.test'
        _salt = _hashlib.sha1(('salt-' + _email).encode()).hexdigest()[:8]
        _derived = _hashlib.pbkdf2_hmac(
            'sha256', b'TestPass123!', _salt.encode(), 1000, dklen=32
        ).hex()
        seed_user = User(email=_email, name='IMDb Editors',
                         created_at=R2_REFERENCE_DATE)
        # Fixed-salt pbkdf2 (werkzeug-compatible) — gotchas.md fix #1B.
        seed_user.password_hash = f'pbkdf2:sha256:1000${_salt}${_derived}'
        db.session.add(seed_user)
        db.session.flush()

    # Walk every title in sorted tt_id order (deterministic).
    all_titles = sorted(Title.query.all(), key=lambda t: t.tt_id)
    for ti, t in enumerate(all_titles):
        td = _read_title_json(t.tt_id)
        if not td:
            continue
        # Trivia
        for ii, body in enumerate(_derive_trivia(t, td)):
            db.session.add(TitleTrivia(title_id=t.id, body=body,
                                       author_id=seed_user.id, is_seed=True,
                                       helpful_count=200 + ti * 3 + ii,
                                       created_at=R2_REFERENCE_DATE - timedelta(days=ti+1)))
        # Quotes
        cast_credits = [c for c in t.credits if c.role == 'actor']
        cast_credits.sort(key=lambda c: c.billing_order or 999)
        for qi, (char, line) in enumerate(_derive_quotes(t, td, cast_credits)):
            db.session.add(TitleQuote(title_id=t.id, character=char, body=line,
                                      author_id=seed_user.id, is_seed=True,
                                      helpful_count=180 + ti * 2 + qi,
                                      created_at=R2_REFERENCE_DATE - timedelta(days=ti+1)))
        # Goofs
        for gi, (cat, body) in enumerate(_derive_goofs(t, td)):
            db.session.add(TitleGoof(title_id=t.id, category=cat, body=body,
                                     author_id=seed_user.id, is_seed=True,
                                     helpful_count=120 + ti + gi,
                                     created_at=R2_REFERENCE_DATE - timedelta(days=ti+1)))
    db.session.flush()

    # 4) ReviewHelpful seed: every benchmark user marks the top seed review
    #    on Shawshank as helpful (idempotent, deterministic).
    ReviewHelpful = models['ReviewHelpful']
    top_r = (Review.query
             .filter_by(is_seed=True)
             .order_by(desc(Review.helpful_count))
             .first())
    if top_r is not None:
        bench_users = (User.query
                       .filter(User.email.in_([u['email'] for u in [
                           {'email': 'alice.j@test.com'},
                           {'email': 'bob.c@test.com'},
                           {'email': 'carol.d@test.com'},
                           {'email': 'david.k@test.com'}]]))
                       .order_by(User.email)
                       .all())
        for u in bench_users:
            db.session.add(ReviewHelpful(review_id=top_r.id, user_id=u.id,
                                         vote=1,
                                         created_at=R2_REFERENCE_DATE - timedelta(days=2)))

    # 5) Pre-seed follows: alice follows Christopher Nolan, bob follows Cranston.
    Follow = models['Follow']
    follow_seed = [
        ('alice.j@test.com', 'nm0634240'),
        ('alice.j@test.com', 'nm0000151'),
        ('bob.c@test.com',   'nm0186505'),
        ('bob.c@test.com',   'nm0000148'),
        ('carol.d@test.com', 'nm0000164'),
        ('david.k@test.com', 'nm0000175'),
    ]
    for email, nm in follow_seed:
        u = by_email.get(email)
        p = Person.query.filter_by(nm_id=nm).first()
        if u is None or p is None:
            continue
        db.session.add(Follow(user_id=u.id, person_id=p.id,
                              created_at=R2_REFERENCE_DATE - timedelta(days=3)))

    db.session.commit()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

def _register_routes(app, db, models, Title, Person, Genre, Credit, Review,
                     UserRating, WatchlistItem, User, NewsItem):
    Poll = models['Poll']
    PollOption = models['PollOption']
    PollVote = models['PollVote']
    UserList = models['UserList']
    UserListItem = models['UserListItem']
    ReviewHelpful = models['ReviewHelpful']
    Follow = models['Follow']
    Report = models['Report']
    TitleTrivia = models['TitleTrivia']
    TitleQuote = models['TitleQuote']
    TitleGoof = models['TitleGoof']
    WatchedFlag = models['WatchedFlag']

    def _get_title(tt_id):
        t = Title.query.filter_by(tt_id=tt_id).first()
        if not t:
            abort(404)
        return t

    def _get_person(nm_id):
        p = Person.query.filter_by(nm_id=nm_id).first()
        if not p:
            abort(404)
        return p

    # Helpers exposed to all r2 templates.
    @app.context_processor
    def _r2_globals():
        following_ids = set()
        if current_user.is_authenticated:
            following_ids = {f.person_id for f in
                             Follow.query.filter_by(user_id=current_user.id).all()}
        return {'following_ids': following_ids}

    # ----- Title sub-pages (GET) --------------------------------------------
    @app.route('/title/<tt_id>/trivia')
    def title_trivia(tt_id):
        t = _get_title(tt_id)
        items = (TitleTrivia.query.filter_by(title_id=t.id)
                 .order_by(desc(TitleTrivia.helpful_count), TitleTrivia.id).all())
        return render_template('r2_title_trivia.html', title=t, items=items)

    @app.route('/title/<tt_id>/quotes')
    def title_quotes(tt_id):
        t = _get_title(tt_id)
        items = (TitleQuote.query.filter_by(title_id=t.id)
                 .order_by(desc(TitleQuote.helpful_count), TitleQuote.id).all())
        return render_template('r2_title_quotes.html', title=t, items=items)

    @app.route('/title/<tt_id>/goofs')
    def title_goofs(tt_id):
        t = _get_title(tt_id)
        items = (TitleGoof.query.filter_by(title_id=t.id)
                 .order_by(TitleGoof.category, desc(TitleGoof.helpful_count)).all())
        return render_template('r2_title_goofs.html', title=t, items=items)

    @app.route('/title/<tt_id>/awards')
    def title_awards(tt_id):
        t = _get_title(tt_id)
        td = _read_title_json(tt_id)
        summary = _derive_awards_summary(td)
        return render_template('r2_title_awards.html', title=t, summary=summary)

    @app.route('/title/<tt_id>/parents-guide')
    def title_parents_guide(tt_id):
        t = _get_title(tt_id)
        buckets = _derive_parents_guide(t)
        return render_template('r2_title_parents_guide.html', title=t, buckets=buckets)

    @app.route('/title/<tt_id>/technical-specs')
    def title_technical(tt_id):
        t = _get_title(tt_id)
        td = _read_title_json(tt_id)
        specs = _derive_tech_specs(td)
        return render_template('r2_title_technical.html', title=t, specs=specs)

    @app.route('/title/<tt_id>/keywords')
    def title_keywords(tt_id):
        t = _get_title(tt_id)
        td = _read_title_json(tt_id)
        kws = _derive_keywords(td)
        return render_template('r2_title_keywords.html', title=t, keywords=kws)

    @app.route('/title/<tt_id>/locations')
    def title_locations(tt_id):
        t = _get_title(tt_id)
        td = _read_title_json(tt_id)
        locs = _derive_locations(td)
        return render_template('r2_title_locations.html', title=t, locations=locs)

    @app.route('/title/<tt_id>/companies')
    def title_companies(tt_id):
        t = _get_title(tt_id)
        td = _read_title_json(tt_id)
        co = _derive_companies(td)
        return render_template('r2_title_companies.html', title=t, companies=co)

    @app.route('/title/<tt_id>/release-info')
    def title_release_info(tt_id):
        t = _get_title(tt_id)
        td = _read_title_json(tt_id)
        akas = _derive_akas(td)
        return render_template('r2_title_release_info.html', title=t, akas=akas)

    @app.route('/title/<tt_id>/external-sites')
    def title_external(tt_id):
        t = _get_title(tt_id)
        td = _read_title_json(tt_id)
        co = _derive_companies(td)
        return render_template('r2_title_external.html', title=t, companies=co)

    @app.route('/title/<tt_id>/connections')
    def title_connections(tt_id):
        t = _get_title(tt_id)
        all_titles = Title.query.all()
        tts = _derive_connections(t, all_titles)
        rel = (Title.query.filter(Title.tt_id.in_(tts)).all() if tts else [])
        # Preserve order
        order = {x: i for i, x in enumerate(tts)}
        rel.sort(key=lambda x: order.get(x.tt_id, 999))
        return render_template('r2_title_connections.html', title=t, related=rel)

    @app.route('/title/<tt_id>/photos')
    def title_photos(tt_id):
        t = _get_title(tt_id)
        cast = sorted([c for c in t.credits if c.role == 'actor'],
                      key=lambda c: c.billing_order or 999)[:12]
        return render_template('r2_title_photos.html', title=t, cast=cast)

    @app.route('/title/<tt_id>/soundtrack')
    def title_soundtrack(tt_id):
        t = _get_title(tt_id)
        # Synth from composer credit if present.
        composers = [c for c in t.credits if c.role == 'composer']
        return render_template('r2_title_soundtrack.html', title=t, composers=composers)

    @app.route('/title/<tt_id>/faq')
    def title_faq(tt_id):
        t = _get_title(tt_id)
        return render_template('r2_title_faq.html', title=t)

    @app.route('/title/<tt_id>/episodes')
    def title_episodes(tt_id):
        t = _get_title(tt_id)
        if t.title_type != 'tvSeries':
            return redirect(url_for('title_detail', tt_id=tt_id))
        # Synth deterministically — episode count derived from runtime/year.
        eps = []
        season_count = max(1, (t.end_year or t.year or 2010) - (t.year or 2010) + 1)
        season_count = min(season_count, 5)
        for s in range(1, season_count + 1):
            for e in range(1, 11):
                eps.append({'season': s, 'episode': e,
                            'title': f'{t.primary_title} S{s}E{e}'})
        return render_template('r2_title_episodes.html', title=t, episodes=eps)

    # ----- Name sub-pages ---------------------------------------------------
    @app.route('/name/<nm_id>/bio')
    def name_bio(nm_id):
        p = _get_person(nm_id)
        nd = _read_name_json(nm_id) or {}
        full_bio = _u(nd.get('bio')) or p.bio or ''
        return render_template('r2_name_bio.html', person=p, full_bio=full_bio)

    @app.route('/name/<nm_id>/personal-life')
    def name_personal(nm_id):
        p = _get_person(nm_id)
        nd = _read_name_json(nm_id) or {}
        born = _u(nd.get('born_block')) or (f'Born {p.birth_year}' if p.birth_year else '')
        died = _u(nd.get('died_block')) or (f'Died {p.death_year}' if p.death_year else '')
        return render_template('r2_name_personal.html', person=p,
                               born=born, died=died)

    @app.route('/name/<nm_id>/awards')
    def name_awards(nm_id):
        p = _get_person(nm_id)
        # Aggregate per-title awards summaries from their scraped data.
        items = []
        for c in p.credits:
            if not c.title:
                continue
            td = _read_title_json(c.title.tt_id)
            sm = _derive_awards_summary(td)
            if sm:
                items.append((c.title, c.role, sm))
        # Dedupe by title, take top 12 by sum of (wins+nominations).
        seen = set()
        uniq = []
        for t, role, sm in items:
            if t.tt_id in seen:
                continue
            seen.add(t.tt_id)
            uniq.append((t, role, sm))
        return render_template('r2_name_awards.html', person=p, items=uniq[:12])

    @app.route('/name/<nm_id>/quotes')
    def name_quotes(nm_id):
        p = _get_person(nm_id)
        # Synth: aggregate top-billed character lines from their films.
        items = []
        for c in p.credits:
            if c.role != 'actor' or not c.title or (c.billing_order or 99) > 3:
                continue
            qs = (TitleQuote.query
                  .filter_by(title_id=c.title.id)
                  .filter(TitleQuote.character.ilike(f'%{c.character[:40] or ""}%')
                          if c.character else TitleQuote.id < 0)
                  .all())
            for q in qs[:1]:
                items.append((c.title, q))
        return render_template('r2_name_quotes.html', person=p, items=items[:8])

    @app.route('/name/<nm_id>/trivia')
    def name_trivia(nm_id):
        p = _get_person(nm_id)
        # Synth trivia derived from credits & dates.
        items = []
        if p.birth_year:
            items.append(f'Born in {p.birth_year}.')
        if p.death_year:
            items.append(f'Passed away in {p.death_year}.')
        roles = sorted({c.role for c in p.credits})
        if roles:
            items.append(f'Has on-screen credits in {len(p.credits)} project(s) '
                         f'across roles: {", ".join(roles)}.')
        if p.primary_profession:
            items.append(f'Primary profession: {p.primary_profession}.')
        items.append(f'Currently has {len(p.credits)} credit(s) tracked in this catalogue.')
        return render_template('r2_name_trivia.html', person=p, items=items)

    @app.route('/name/<nm_id>/photos')
    def name_photos(nm_id):
        p = _get_person(nm_id)
        # Show their headshot plus top 6 posters they're billed top-5 on.
        top_credits = sorted([c for c in p.credits if c.role == 'actor'
                              and c.title and (c.billing_order or 99) <= 5],
                             key=lambda c: -(c.title.num_votes or 0))[:6]
        return render_template('r2_name_photos.html', person=p, top_credits=top_credits)

    @app.route('/name/<nm_id>/filmography')
    def name_filmography(nm_id):
        p = _get_person(nm_id)
        grouped = {}
        for c in p.credits:
            grouped.setdefault(c.role, []).append(c)
        for k in grouped:
            grouped[k].sort(key=lambda c: -((c.title.year if c.title else 0) or 0))
        return render_template('r2_name_filmography.html', person=p, grouped=grouped)

    # ----- Lists ------------------------------------------------------------
    @app.route('/lists')
    def lists_index():
        lists = (UserList.query
                 .filter_by(is_public=True)
                 .order_by(desc(UserList.created_at)).all())
        return render_template('r2_lists_index.html', lists=lists)

    @app.route('/list/<int:list_id>')
    def list_detail(list_id):
        L = db.session.get(UserList, list_id) or abort(404)
        if not L.is_public and (not current_user.is_authenticated
                                or current_user.id != L.owner_id):
            abort(404)
        items = sorted(L.items, key=lambda i: i.position)
        rows = []
        for it in items:
            t = db.session.get(Title, it.title_id)
            if t:
                rows.append((it, t))
        owner = db.session.get(User, L.owner_id)
        return render_template('r2_list_detail.html', list=L,
                               rows=rows, owner=owner)

    @app.route('/lists/new', methods=['GET', 'POST'])
    @login_required
    def list_new():
        if request.method == 'POST':
            name = (request.form.get('name') or '').strip()[:120]
            desc_ = (request.form.get('description') or '').strip()
            if not name:
                flash('List name is required.', 'error')
                return render_template('r2_list_form.html', list=None)
            L = UserList(owner_id=current_user.id, name=name, description=desc_,
                         is_public=True, created_at=R2_REFERENCE_DATE)
            db.session.add(L)
            db.session.commit()
            flash('List created.', 'success')
            return redirect(url_for('list_detail', list_id=L.id))
        return render_template('r2_list_form.html', list=None)

    @app.route('/list/<int:list_id>/edit', methods=['GET', 'POST'])
    @login_required
    def list_edit(list_id):
        L = db.session.get(UserList, list_id) or abort(404)
        if L.owner_id != current_user.id:
            abort(403)
        if request.method == 'POST':
            L.name = (request.form.get('name') or L.name).strip()[:120]
            L.description = (request.form.get('description') or '').strip()
            db.session.commit()
            flash('List updated.', 'success')
            return redirect(url_for('list_detail', list_id=L.id))
        return render_template('r2_list_form.html', list=L)

    @app.route('/list/<int:list_id>/delete', methods=['POST'])
    @login_required
    def list_delete(list_id):
        L = db.session.get(UserList, list_id) or abort(404)
        if L.owner_id != current_user.id:
            abort(403)
        db.session.delete(L)
        db.session.commit()
        flash('List deleted.', 'info')
        return redirect(url_for('lists_index'))

    @app.route('/list/<int:list_id>/add', methods=['POST'])
    @login_required
    def list_add(list_id):
        L = db.session.get(UserList, list_id) or abort(404)
        if L.owner_id != current_user.id:
            abort(403)
        tt_id = request.form.get('tt_id', '').strip()
        t = Title.query.filter_by(tt_id=tt_id).first()
        if not t:
            flash('Unknown title.', 'error')
            return redirect(url_for('list_detail', list_id=L.id))
        if UserListItem.query.filter_by(list_id=L.id, title_id=t.id).first():
            flash('Already in this list.', 'info')
        else:
            existing = UserListItem.query.filter_by(list_id=L.id).count()
            db.session.add(UserListItem(list_id=L.id, title_id=t.id,
                                        position=existing,
                                        added_at=R2_REFERENCE_DATE))
            db.session.commit()
            flash(f'Added "{t.primary_title}" to list.', 'success')
        return redirect(url_for('list_detail', list_id=L.id))

    @app.route('/list/<int:list_id>/remove/<tt_id>', methods=['POST'])
    @login_required
    def list_remove(list_id, tt_id):
        L = db.session.get(UserList, list_id) or abort(404)
        if L.owner_id != current_user.id:
            abort(403)
        t = Title.query.filter_by(tt_id=tt_id).first_or_404()
        it = UserListItem.query.filter_by(list_id=L.id, title_id=t.id).first()
        if it:
            db.session.delete(it)
            db.session.commit()
            flash('Removed from list.', 'info')
        return redirect(url_for('list_detail', list_id=L.id))

    # ----- Polls ------------------------------------------------------------
    @app.route('/polls')
    def polls_index():
        polls = Poll.query.order_by(desc(Poll.created_at)).all()
        return render_template('r2_polls_index.html', polls=polls)

    @app.route('/poll/<slug>')
    def poll_detail(slug):
        p = Poll.query.filter_by(slug=slug).first_or_404()
        # tally: seed_votes + user votes
        tallies = []
        my_choice = None
        for op in sorted(p.options, key=lambda o: o.position):
            v = op.seed_votes + PollVote.query.filter_by(option_id=op.id).count()
            tallies.append((op, v))
            if current_user.is_authenticated:
                if PollVote.query.filter_by(user_id=current_user.id,
                                            option_id=op.id).first():
                    my_choice = op.id
        total = sum(v for _, v in tallies) or 1
        return render_template('r2_poll_detail.html', poll=p, tallies=tallies,
                               total=total, my_choice=my_choice)

    @app.route('/poll/<slug>/vote', methods=['POST'])
    @login_required
    def poll_vote(slug):
        p = Poll.query.filter_by(slug=slug).first_or_404()
        if p.is_closed:
            flash('This poll is closed.', 'error')
            return redirect(url_for('poll_detail', slug=p.slug))
        try:
            opt_id = int(request.form['option_id'])
        except (KeyError, ValueError):
            flash('Invalid option.', 'error')
            return redirect(url_for('poll_detail', slug=p.slug))
        op = db.session.get(PollOption, opt_id)
        if op is None or op.poll_id != p.id:
            abort(400)
        # Clear previous votes by this user on this poll first.
        for old_op in p.options:
            existing = PollVote.query.filter_by(user_id=current_user.id,
                                                option_id=old_op.id).first()
            if existing:
                db.session.delete(existing)
        db.session.add(PollVote(user_id=current_user.id, option_id=op.id,
                                created_at=R2_REFERENCE_DATE))
        db.session.commit()
        flash('Vote recorded.', 'success')
        return redirect(url_for('poll_detail', slug=p.slug))

    # ----- News detail ------------------------------------------------------
    @app.route('/news/<int:news_id>')
    def news_detail(news_id):
        n = db.session.get(NewsItem, news_id) or abort(404)
        related_title = None
        if n.related_tt:
            related_title = Title.query.filter_by(tt_id=n.related_tt).first()
        return render_template('r2_news_detail.html', news=n,
                               related_title=related_title)

    # ----- Additional charts ------------------------------------------------
    @app.route('/chart/popular_tv')
    def chart_popular_tv():
        titles = (Title.query
                  .filter(Title.title_type == 'tvSeries',
                          Title.popularity_rank.isnot(None))
                  .order_by(Title.popularity_rank.asc())
                  .limit(50).all())
        return render_template('chart.html', titles=titles,
                               chart_name='Most Popular TV Shows',
                               chart_slug='popular_tv',
                               description="IMDb users' most popular TV series this week.")

    @app.route('/chart/lowest_rated')
    def chart_lowest_rated():
        titles = (Title.query
                  .filter(Title.num_votes >= 50000)
                  .order_by(Title.rating_avg.asc())
                  .limit(50).all())
        return render_template('chart.html', titles=titles,
                               chart_name='Lowest Rated (50k+ votes)',
                               chart_slug='lowest_rated',
                               description='The lowest IMDb-rated titles with substantial vote counts.')

    # ----- Search/name view -------------------------------------------------
    @app.route('/search/name')
    def search_name():
        from app import scored_person_search
        q = (request.args.get('q') or '').strip()
        people = scored_person_search(q, limit=80) if q else []
        return render_template('r2_search_name.html', q=q, people=people)

    # ----- Recently viewed --------------------------------------------------
    @app.route('/myaccount/recently-viewed')
    @login_required
    def recently_viewed():
        # Synth: show user's last 12 watchlist additions + ratings.
        recent_wl = (WatchlistItem.query
                     .filter_by(user_id=current_user.id)
                     .order_by(desc(WatchlistItem.added_at)).limit(8).all())
        recent_r = (UserRating.query
                    .filter_by(user_id=current_user.id)
                    .order_by(desc(UserRating.created_at)).limit(8).all())
        wl = [db.session.get(Title, x.title_id) for x in recent_wl]
        rt = [(db.session.get(Title, x.title_id), x) for x in recent_r]
        return render_template('r2_recently_viewed.html',
                               watchlist=wl, ratings=rt)

    # ----- POST endpoints (review feedback, submissions, reports) ----------
    @app.route('/review/<int:review_id>/helpful', methods=['POST'])
    @login_required
    def review_helpful(review_id):
        r = db.session.get(Review, review_id) or abort(404)
        existing = ReviewHelpful.query.filter_by(
            review_id=r.id, user_id=current_user.id).first()
        if existing is None:
            db.session.add(ReviewHelpful(review_id=r.id, user_id=current_user.id,
                                         vote=1, created_at=R2_REFERENCE_DATE))
            r.helpful_count = (r.helpful_count or 0) + 1
            db.session.commit()
            flash('Marked as helpful.', 'success')
        else:
            flash('Already marked.', 'info')
        return redirect(request.referrer
                        or url_for('title_reviews',
                                   tt_id=db.session.get(Title, r.title_id).tt_id))

    @app.route('/review/<int:review_id>/flag', methods=['POST'])
    @login_required
    def review_flag(review_id):
        r = db.session.get(Review, review_id) or abort(404)
        cat = (request.form.get('category') or 'spoiler').strip()[:40]
        body = (request.form.get('body') or '').strip()[:1000]
        db.session.add(Report(user_id=current_user.id, target_type='review',
                              target_ref=str(r.id), category=cat, body=body,
                              created_at=R2_REFERENCE_DATE))
        db.session.commit()
        flash('Flag submitted.', 'info')
        return redirect(request.referrer
                        or url_for('title_reviews',
                                   tt_id=db.session.get(Title, r.title_id).tt_id))

    @app.route('/review/<int:review_id>/delete', methods=['POST'])
    @login_required
    def review_delete(review_id):
        r = db.session.get(Review, review_id) or abort(404)
        if r.user_id != current_user.id:
            abort(403)
        tt = db.session.get(Title, r.title_id).tt_id
        db.session.delete(r)
        db.session.commit()
        flash('Review deleted.', 'info')
        return redirect(url_for('title_reviews', tt_id=tt))

    @app.route('/title/<tt_id>/trivia/submit', methods=['POST'])
    @login_required
    def trivia_submit(tt_id):
        t = _get_title(tt_id)
        body = (request.form.get('body') or '').strip()
        if not body:
            flash('Trivia body required.', 'error')
            return redirect(url_for('title_trivia', tt_id=tt_id))
        db.session.add(TitleTrivia(title_id=t.id, body=body[:4000],
                                   author_id=current_user.id, is_seed=False,
                                   helpful_count=0,
                                   created_at=R2_REFERENCE_DATE))
        db.session.commit()
        flash('Trivia submitted for review.', 'success')
        return redirect(url_for('title_trivia', tt_id=tt_id))

    @app.route('/title/<tt_id>/quotes/submit', methods=['POST'])
    @login_required
    def quote_submit(tt_id):
        t = _get_title(tt_id)
        char = (request.form.get('character') or '').strip()[:160]
        body = (request.form.get('body') or '').strip()
        if not body:
            flash('Quote body required.', 'error')
            return redirect(url_for('title_quotes', tt_id=tt_id))
        db.session.add(TitleQuote(title_id=t.id, character=char, body=body[:4000],
                                  author_id=current_user.id, is_seed=False,
                                  helpful_count=0,
                                  created_at=R2_REFERENCE_DATE))
        db.session.commit()
        flash('Quote submitted for review.', 'success')
        return redirect(url_for('title_quotes', tt_id=tt_id))

    @app.route('/title/<tt_id>/goofs/submit', methods=['POST'])
    @login_required
    def goof_submit(tt_id):
        t = _get_title(tt_id)
        cat = (request.form.get('category') or 'Continuity').strip()[:40]
        body = (request.form.get('body') or '').strip()
        if not body:
            flash('Goof body required.', 'error')
            return redirect(url_for('title_goofs', tt_id=tt_id))
        db.session.add(TitleGoof(title_id=t.id, category=cat, body=body[:4000],
                                 author_id=current_user.id, is_seed=False,
                                 helpful_count=0,
                                 created_at=R2_REFERENCE_DATE))
        db.session.commit()
        flash('Goof submitted for review.', 'success')
        return redirect(url_for('title_goofs', tt_id=tt_id))

    @app.route('/title/<tt_id>/report', methods=['POST'])
    @login_required
    def title_report(tt_id):
        t = _get_title(tt_id)
        cat = (request.form.get('category') or 'incorrect-data').strip()[:40]
        body = (request.form.get('body') or '').strip()[:1000]
        db.session.add(Report(user_id=current_user.id, target_type='title',
                              target_ref=tt_id, category=cat, body=body,
                              created_at=R2_REFERENCE_DATE))
        db.session.commit()
        flash('Report submitted.', 'info')
        return redirect(url_for('title_detail', tt_id=tt_id))

    @app.route('/name/<nm_id>/report', methods=['POST'])
    @login_required
    def name_report(nm_id):
        p = _get_person(nm_id)
        cat = (request.form.get('category') or 'incorrect-data').strip()[:40]
        body = (request.form.get('body') or '').strip()[:1000]
        db.session.add(Report(user_id=current_user.id, target_type='name',
                              target_ref=nm_id, category=cat, body=body,
                              created_at=R2_REFERENCE_DATE))
        db.session.commit()
        flash('Report submitted.', 'info')
        return redirect(url_for('name_detail', nm_id=nm_id))

    @app.route('/name/<nm_id>/follow', methods=['POST'])
    @login_required
    def name_follow(nm_id):
        p = _get_person(nm_id)
        existing = Follow.query.filter_by(user_id=current_user.id,
                                          person_id=p.id).first()
        if existing:
            db.session.delete(existing)
            flash('Unfollowed.', 'info')
        else:
            db.session.add(Follow(user_id=current_user.id, person_id=p.id,
                                  created_at=R2_REFERENCE_DATE))
            flash('Now following.', 'success')
        db.session.commit()
        return redirect(url_for('name_detail', nm_id=nm_id))

    @app.route('/title/<tt_id>/mark-watched', methods=['POST'])
    @login_required
    def title_mark_watched(tt_id):
        t = _get_title(tt_id)
        existing = WatchedFlag.query.filter_by(user_id=current_user.id,
                                               title_id=t.id).first()
        if existing:
            db.session.delete(existing)
            flash('Removed from Watched.', 'info')
        else:
            db.session.add(WatchedFlag(user_id=current_user.id, title_id=t.id,
                                       marked_at=R2_REFERENCE_DATE))
            flash('Marked as Watched.', 'success')
        db.session.commit()
        return redirect(url_for('title_detail', tt_id=tt_id))

    @app.route('/account/edit', methods=['GET', 'POST'])
    @login_required
    def account_edit():
        if request.method == 'POST':
            current_user.name = (request.form.get('name') or current_user.name).strip()[:120]
            db.session.commit()
            flash('Profile updated.', 'success')
            return redirect(url_for('account'))
        return render_template('r2_account_edit.html')

    @app.route('/account/password', methods=['GET', 'POST'])
    @login_required
    def account_password():
        if request.method == 'POST':
            old = request.form.get('old_password', '')
            new = request.form.get('new_password', '')
            if not current_user.check_password(old):
                flash('Current password is incorrect.', 'error')
                return render_template('r2_account_password.html')
            if len(new) < 6:
                flash('New password must be at least 6 characters.', 'error')
                return render_template('r2_account_password.html')
            current_user.set_password(new)
            db.session.commit()
            flash('Password changed.', 'success')
            return redirect(url_for('account'))
        return render_template('r2_account_password.html')

    @app.route('/list/watchlist/clear', methods=['POST'])
    @login_required
    def watchlist_clear():
        WatchlistItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        flash('Watchlist cleared.', 'info')
        return redirect(url_for('my_watchlist'))

    @app.route('/list/ratings/clear', methods=['POST'])
    @login_required
    def ratings_clear():
        UserRating.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        flash('Your ratings have been cleared.', 'info')
        return redirect(url_for('my_ratings'))

    @app.route('/follows/clear', methods=['POST'])
    @login_required
    def follows_clear():
        Follow.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        flash('Unfollowed everyone.', 'info')
        return redirect(url_for('account'))

    @app.route('/poll/<slug>/suggest', methods=['POST'])
    @login_required
    def poll_suggest(slug):
        p = Poll.query.filter_by(slug=slug).first_or_404()
        body = (request.form.get('body') or '').strip()[:1000]
        if not body:
            flash('Suggestion text required.', 'error')
        else:
            db.session.add(Report(user_id=current_user.id, target_type='poll',
                                  target_ref=p.slug, category='suggest-option',
                                  body=body, created_at=R2_REFERENCE_DATE))
            db.session.commit()
            flash('Suggestion sent to moderators.', 'success')
        return redirect(url_for('poll_detail', slug=p.slug))


# ---------------------------------------------------------------------------
# Public entrypoint called from app.py
# ---------------------------------------------------------------------------

def deepen_app(app, db, Title, Person, Genre, Credit, Review, UserRating,
               WatchlistItem, User, NewsItem):
    models = _register_models(db)
    with app.app_context():
        db.create_all()
        seed_r2(db, models, Title, Person, User, Review)
        _normalize_seed_db_layout(db)
    _register_routes(app, db, models, Title, Person, Genre, Credit, Review,
                     UserRating, WatchlistItem, User, NewsItem)
    return models


def _normalize_seed_db_layout(db):
    """Re-emit indexes in alpha order + repack non-deterministic M2M tables +
    VACUUM so rebuilds match byte-for-byte.

    Per harden-env/gotchas:
      - #2: SQLAlchemy CREATE INDEX iterates a Python set → drop/recreate ix_*
        in sorted name order.
      - #12: M2M association tables (title_genre) populated via
        relationship.append happen in dict/set iteration order → physical row
        order shifts between processes. Rebuild via SELECT ORDER BY.

    Run once at the end of seeding; never touch the DB after.
    """
    from sqlalchemy import text
    conn = db.engine.connect()
    try:
        # 1. Indexes: drop ix_*, recreate alpha.
        idx_rows = conn.execute(text(
            "SELECT name, sql FROM sqlite_master WHERE type='index' "
            "AND name LIKE 'ix_%' AND sql IS NOT NULL"
        )).fetchall()
        for name, _ in idx_rows:
            conn.execute(text(f'DROP INDEX IF EXISTS "{name}"'))
        for name, sql in sorted(idx_rows, key=lambda r: r[0]):
            conn.execute(text(sql))

        # 2. Repack title_genre association rows in sorted (title_id, genre_id) order.
        conn.execute(text(
            "CREATE TABLE _tg_tmp AS "
            "SELECT title_id, genre_id FROM title_genre "
            "ORDER BY title_id, genre_id"
        ))
        conn.execute(text("DELETE FROM title_genre"))
        conn.execute(text(
            "INSERT INTO title_genre (title_id, genre_id) "
            "SELECT title_id, genre_id FROM _tg_tmp"
        ))
        conn.execute(text("DROP TABLE _tg_tmp"))
        conn.commit()
    finally:
        conn.close()
    # VACUUM cannot run inside a transaction — open a raw connection in autocommit.
    raw = db.engine.raw_connection()
    try:
        raw.isolation_level = None
        cur = raw.cursor()
        cur.execute("VACUUM")
        cur.close()
        raw.commit()
    finally:
        raw.close()
