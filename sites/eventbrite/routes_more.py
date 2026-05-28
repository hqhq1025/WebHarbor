"""Extended routes, models, and seeds for the Eventbrite mirror.

Loaded by app.py *after* routes.py via _load_module. All new ORM models live
here; they are created via db.create_all() on first boot, which means the
sqlite schema in instance_seed/eventbrite.db includes these tables. Each new
seed_*() function is gated at the function level so /reset/eventbrite remains
byte-identical.

This module also augments the Event/Organizer models with an `image_filename`
column-like accessor that maps to a static/images/ filename selected
deterministically from the event slug / organizer slug.
"""
# Globals from app.py: app, db, login_manager, bcrypt,
#   User, Organizer, Event, TicketTier, SavedEvent, Follow, Order, OrderItem,
#   IssuedTicket, Review, HelpArticle, NewsletterSignup, DraftEvent,
#   CATEGORIES, CITIES, CAT_MAP, CITY_MAP, REFUND_POLICIES,
#   slugify, short_code, score_event, tokenize, parse_iso_date,
#   fmt_dt, fmt_dt_short, fmt_time, event_gradient, organizer_gradient,
#   BASE_DIR.


# ─── New constants ───────────────────────────────────────────────────────────

# Subcategories per category — used for the /d/<city>/<cat>/<subcat>/ pages.
SUBCATEGORY_INDEX = {
    'music':        [('jazz', 'Jazz'), ('rock', 'Rock'), ('edm', 'EDM'),
                     ('hip-hop', 'Hip Hop'), ('latin', 'Latin'), ('folk', 'Folk'),
                     ('classical', 'Classical'), ('country', 'Country'),
                     ('rnb', 'R&B'), ('pop', 'Pop'), ('metal', 'Metal'),
                     ('reggae', 'Reggae'), ('festival', 'Festival')],
    'business':     [('career', 'Career'), ('startups', 'Startups'),
                     ('marketing', 'Marketing'), ('finance', 'Finance'),
                     ('real-estate', 'Real Estate'), ('leadership', 'Leadership'),
                     ('networking', 'Networking')],
    'food-drink':   [('wine', 'Wine'), ('beer', 'Beer'), ('spirits', 'Spirits'),
                     ('tasting', 'Tasting'), ('cooking-class', 'Cooking Class'),
                     ('food-festival', 'Food Festival'), ('vegan', 'Vegan')],
    'arts':         [('theater', 'Theater'), ('comedy', 'Comedy'),
                     ('visual-arts', 'Visual Arts'), ('dance', 'Dance'),
                     ('literary', 'Literary'), ('opera', 'Opera'),
                     ('musicals', 'Musicals')],
    'holiday':      [('halloween', 'Halloween'), ('july-4th', 'July 4th'),
                     ('christmas', 'Christmas'), ('new-year', 'New Year'),
                     ('pride', 'Pride')],
    'health':       [('yoga', 'Yoga'), ('mental-health', 'Mental Health'),
                     ('nutrition', 'Nutrition'), ('meditation', 'Meditation'),
                     ('fitness-class', 'Fitness Class'),
                     ('wellness', 'Wellness')],
    'hobbies':      [('crafts', 'Crafts'), ('games', 'Games'),
                     ('photography', 'Photography'), ('drawing', 'Drawing'),
                     ('knitting', 'Knitting')],
    'family':       [('education', 'Education'),
                     ('kids-activities', 'Kids Activities'),
                     ('parenting', 'Parenting'), ('teens', 'Teens')],
    'sports':       [('basketball', 'Basketball'), ('running', 'Running'),
                     ('cycling', 'Cycling'), ('soccer', 'Soccer'),
                     ('pickleball', 'Pickleball'), ('climbing', 'Climbing'),
                     ('volleyball', 'Volleyball')],
    'travel':       [('hiking', 'Hiking'), ('camping', 'Camping'),
                     ('bike-tour', 'Bike Tour'), ('birding', 'Birding'),
                     ('stargazing', 'Stargazing')],
    'charity':      [('gala', 'Gala'), ('fundraiser', 'Fundraiser'),
                     ('volunteer', 'Volunteer'), ('drive', 'Drive'),
                     ('5k', '5K Run')],
    'spirituality': [('tarot', 'Tarot'), ('astrology', 'Astrology'),
                     ('crystals', 'Crystals'), ('reiki', 'Reiki'),
                     ('sound-bath', 'Sound Bath')],
    'community':    [('mixer', 'Mixer'), ('festival', 'Festival'),
                     ('pride', 'Pride'), ('newcomers', 'Newcomers'),
                     ('block-party', 'Block Party')],
    'fashion':      [('sample-sale', 'Sample Sale'), ('trunk-show', 'Trunk Show'),
                     ('pop-up', 'Pop-Up'), ('bridal', 'Bridal')],
    'film':         [('premiere', 'Premiere'),
                     ('outdoor-screening', 'Outdoor Screening'),
                     ('documentary', 'Documentary'), ('festival', 'Festival')],
    'home':         [('gardening', 'Gardening'), ('plants', 'Plants'),
                     ('interior-design', 'Interior Design'), ('diy', 'DIY')],
    'auto':         [('cars', 'Cars'), ('boats', 'Boats'),
                     ('aviation', 'Aviation'), ('motorcycles', 'Motorcycles')],
    'school':       [('college-prep', 'College Prep'), ('pta', 'PTA'),
                     ('robotics', 'Robotics'),
                     ('resource-fair', 'Resource Fair')],
}

# Neighborhood pages per city. Maps city_slug -> [(slug, name, blurb), ...].
NEIGHBORHOODS = {
    'ny--new-york': [
        ('brooklyn',  'Brooklyn',  'From Williamsburg DJ sets to Bushwick block parties.'),
        ('manhattan', 'Manhattan', 'Midtown comedy clubs, Soho mixers, and Lower East Side music.'),
        ('queens',    'Queens',    'Astoria food crawls and LIC art openings.'),
        ('bronx',     'The Bronx', 'Hip hop history walks and family festivals.'),
        ('staten-island', 'Staten Island', 'Ferry rides, outdoor concerts, neighborhood pop-ups.'),
    ],
    'ca--los-angeles': [
        ('hollywood',  'Hollywood',  'Marquee music venues, premieres, and rooftop parties.'),
        ('downtown',   'Downtown LA', 'Arts District openings, food halls, after-work mixers.'),
        ('venice',     'Venice',     'Boardwalk yoga, beach pop-ups, and indie film nights.'),
        ('silver-lake','Silver Lake', 'Indie shows, vinyl pop-ups, and creative workshops.'),
        ('santa-monica','Santa Monica','Beachside fitness, sunset walks, and craft markets.'),
    ],
    'il--chicago': [
        ('wicker-park','Wicker Park','Indie shows, vintage markets, and craft cocktail bars.'),
        ('the-loop',   'The Loop',   'Business networking, theatre, and rooftop happy hours.'),
        ('pilsen',     'Pilsen',     'Galleries, taquerías, and live music.'),
        ('lakeview',   'Lakeview',   'Venue-heavy nights and yoga studios.'),
    ],
    'tx--austin': [
        ('east-austin', 'East Austin', 'Live music venues and BBQ pop-ups.'),
        ('downtown',    'Downtown',    'SXSW spillover, rooftop bars, conferences.'),
        ('south-congress','South Congress','Vintage shopping and food festivals.'),
    ],
    'ca--san-francisco': [
        ('mission',    'Mission',    'Indie venues, dive bars, food crawls.'),
        ('soma',       'SoMa',       'Conferences, demo nights, and rooftop mixers.'),
        ('haight',     'Haight',     'Vintage shows and music nostalgia.'),
        ('marina',     'Marina',     'Outdoor fitness and waterfront brunch.'),
    ],
    'wa--seattle': [
        ('capitol-hill', 'Capitol Hill', 'Venue-heavy nightlife and pride events.'),
        ('ballard',      'Ballard',      'Maritime mixers, breweries, and folk shows.'),
        ('downtown',     'Downtown',     'Convention center talks and Pike Place tours.'),
    ],
    'ma--boston': [
        ('cambridge',  'Cambridge', 'University talks, tech meetups, indie shows.'),
        ('back-bay',   'Back Bay',  'Brownstone walks and gallery openings.'),
        ('allston',    'Allston',   'College-radio favorites and DIY shows.'),
    ],
    'co--denver': [
        ('rino',      'RiNo',     'Street murals, brewery nights, and rooftop concerts.'),
        ('lodo',      'LoDo',     'Downtown nightlife and Rockies game nights.'),
        ('cap-hill',  'Cap Hill', 'Indie shows and queer-friendly mixers.'),
    ],
    'ga--atlanta': [
        ('midtown',     'Midtown',     'Music venues and high-rise rooftop parties.'),
        ('little-five', 'Little Five Points', 'Punk shows, vintage shopping, and tattoo culture.'),
        ('buckhead',    'Buckhead',    'Upscale shopping, galleries, and dining events.'),
    ],
    'fl--miami': [
        ('south-beach', 'South Beach', 'Beach pool parties, drag brunches, fashion nights.'),
        ('wynwood',     'Wynwood',     'Street art, gallery hops, and creative meetups.'),
        ('downtown',    'Downtown',    'Conferences, business mixers, and waterfront.'),
    ],
    'or--portland': [
        ('pearl',       'Pearl District', 'Galleries and design studios.'),
        ('hawthorne',   'Hawthorne',      'Vinyl shops and indie shows.'),
        ('mississippi', 'Mississippi Ave', 'Brewery tours and family festivals.'),
    ],
}

# Country / region landing pages (US-centric).
REGIONS = [
    ('northeast', 'Northeast', ['ny--new-york', 'ma--boston', 'pa--philadelphia',
                                'md--baltimore', 'dc--washington']),
    ('midwest',   'Midwest',   ['il--chicago', 'mi--detroit', 'mn--minneapolis']),
    ('south',     'South',     ['ga--atlanta', 'fl--miami', 'tx--houston',
                                'tx--austin', 'tn--nashville', 'la--new-orleans',
                                'nc--raleigh']),
    ('west',      'West',      ['ca--san-francisco', 'ca--los-angeles',
                                'ca--san-diego', 'wa--seattle', 'or--portland',
                                'co--denver', 'az--phoenix', 'nv--las-vegas']),
]


# ─── New SQLAlchemy models ───────────────────────────────────────────────────

class CartItem(db.Model):
    """Multi-event cart. Each row is one (user, tier, qty) line item."""
    __tablename__ = 'cart_items'
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    event_id  = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    tier_id   = db.Column(db.Integer, db.ForeignKey('ticket_tiers.id'), nullable=False)
    qty       = db.Column(db.Integer, default=1)
    added_at  = db.Column(db.DateTime, default=datetime.utcnow)


class PromoCode(db.Model):
    __tablename__ = 'promo_codes'
    id           = db.Column(db.Integer, primary_key=True)
    code         = db.Column(db.String(40), unique=True, nullable=False, index=True)
    description  = db.Column(db.String(200), default='')
    percent_off  = db.Column(db.Integer, default=0)
    dollar_off   = db.Column(db.Float, default=0.0)
    min_total    = db.Column(db.Float, default=0.0)
    valid_from   = db.Column(db.DateTime, default=datetime.utcnow)
    valid_to     = db.Column(db.DateTime, default=datetime.utcnow)


class OrganizerReview(db.Model):
    __tablename__ = 'organizer_reviews'
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    organizer_id  = db.Column(db.Integer, db.ForeignKey('organizers.id'), nullable=False, index=True)
    rating        = db.Column(db.Integer, default=5)
    body          = db.Column(db.Text, default='')
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)


class Report(db.Model):
    """Generic report — for events and organizers (target_type column)."""
    __tablename__ = 'reports'
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    target_type   = db.Column(db.String(30), nullable=False)   # 'event' | 'organizer'
    target_id     = db.Column(db.Integer, nullable=False)
    reason        = db.Column(db.String(60), default='other')
    body          = db.Column(db.Text, default='')
    contact_email = db.Column(db.String(120), default='')
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)


class Waitlist(db.Model):
    """Sign-up for "notify me when on sale" / sold-out."""
    __tablename__ = 'waitlist'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    event_id   = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False, index=True)
    email      = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CategorySubscription(db.Model):
    __tablename__ = 'category_subscriptions'
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_slug = db.Column(db.String(40), nullable=False)
    city_slug    = db.Column(db.String(60), default='')   # '' = anywhere
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)


class OrganizerEmailSubscription(db.Model):
    """Email-only subscription for an organizer (lighter than Follow)."""
    __tablename__ = 'org_email_subs'
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    organizer_id = db.Column(db.Integer, db.ForeignKey('organizers.id'), nullable=False, index=True)
    email        = db.Column(db.String(120), nullable=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)


class Invite(db.Model):
    __tablename__ = 'invites'
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    event_id     = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False, index=True)
    recipient_emails = db.Column(db.Text, default='[]')   # JSON list of email strings
    message      = db.Column(db.Text, default='')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)


class EventQuestion(db.Model):
    """Public Q&A on the event detail page."""
    __tablename__ = 'event_questions'
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    event_id     = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False, index=True)
    question     = db.Column(db.Text, nullable=False)
    answer       = db.Column(db.Text, default='')
    author_name  = db.Column(db.String(120), default='')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)


class RSVPVote(db.Model):
    __tablename__ = 'rsvp_votes'
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    event_id     = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False, index=True)
    response     = db.Column(db.String(10), default='maybe')   # yes | maybe | no
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'event_id', name='uq_rsvp'),)


class GiftTransfer(db.Model):
    __tablename__ = 'gift_transfers'
    id           = db.Column(db.Integer, primary_key=True)
    ticket_id    = db.Column(db.Integer, db.ForeignKey('issued_tickets.id'), nullable=False, index=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_email = db.Column(db.String(120), nullable=False)
    recipient_name  = db.Column(db.String(120), default='')
    message      = db.Column(db.Text, default='')
    status       = db.Column(db.String(20), default='pending')   # pending | accepted
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)


class GroupSplit(db.Model):
    """Split a cart total between multiple attendees by email."""
    __tablename__ = 'group_splits'
    id           = db.Column(db.Integer, primary_key=True)
    order_id     = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, index=True)
    payer_emails = db.Column(db.Text, default='[]')  # JSON list of email strings
    per_person   = db.Column(db.Float, default=0.0)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)


class BlogAuthor(db.Model):
    __tablename__ = 'blog_authors'
    id    = db.Column(db.Integer, primary_key=True)
    slug  = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name  = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(120), default='')
    bio   = db.Column(db.Text, default='')


class BlogPost(db.Model):
    __tablename__ = 'blog_posts'
    id           = db.Column(db.Integer, primary_key=True)
    slug         = db.Column(db.String(160), unique=True, nullable=False, index=True)
    title        = db.Column(db.String(240), nullable=False)
    excerpt      = db.Column(db.String(400), default='')
    body         = db.Column(db.Text, default='')
    tag          = db.Column(db.String(60), default='', index=True)
    cover_image  = db.Column(db.String(120), default='')   # filename in static/images/
    author_id    = db.Column(db.Integer, db.ForeignKey('blog_authors.id'), nullable=False)
    published_at = db.Column(db.DateTime, default=datetime.utcnow)
    author       = db.relationship('BlogAuthor')


class ShareEmail(db.Model):
    """A 'share via email' submission."""
    __tablename__ = 'share_emails'
    id        = db.Column(db.Integer, primary_key=True)
    event_id  = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False, index=True)
    sender_email   = db.Column(db.String(120), default='')
    recipient_email = db.Column(db.String(120), nullable=False)
    note      = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ─── Image helpers (real images under static/images/) ───────────────────────

_IMAGES_DIR = os.path.join(BASE_DIR, 'static', 'images')


def _list_images_for_category(cat_slug):
    """Return sorted list of image filenames in static/images/ that match the
    `evt_<category>_*.jpg` naming. Cached per-process."""
    cache_key = '_eb_img_cache'
    cache = app.config.setdefault(cache_key, {})
    if cat_slug in cache:
        return cache[cat_slug]
    if not os.path.isdir(_IMAGES_DIR):
        cache[cat_slug] = []
        return []
    prefix = f'evt_{cat_slug}_'
    found = sorted(f for f in os.listdir(_IMAGES_DIR) if f.startswith(prefix) and f.endswith('.jpg'))
    cache[cat_slug] = found
    return found


def event_image_filename(ev):
    """Deterministically choose a static/images/ filename for ev based on
    category + slug hash. Falls back to '' if no images on disk."""
    pool = _list_images_for_category(ev.category_slug)
    if not pool:
        return ''
    idx = int(hashlib.md5((ev.slug or '').encode()).hexdigest()[:8], 16) % len(pool)
    return pool[idx]


def event_image_url(ev):
    fn = event_image_filename(ev)
    return url_for('static', filename='images/' + fn) if fn else ''


def organizer_image_filename(o):
    if not os.path.isdir(_IMAGES_DIR):
        return ''
    pool = sorted(f for f in os.listdir(_IMAGES_DIR) if f.startswith('org_texture_'))
    if not pool: return ''
    idx = int(hashlib.md5((o.slug or '').encode()).hexdigest()[:8], 16) % len(pool)
    return pool[idx]


def organizer_image_url(o):
    fn = organizer_image_filename(o)
    return url_for('static', filename='images/' + fn) if fn else ''


def city_image_url(city_slug):
    fn = f'city_{city_slug}.jpg'
    if os.path.isfile(os.path.join(_IMAGES_DIR, fn)):
        return url_for('static', filename='images/' + fn)
    return ''


def hero_image_url(name):
    """Hero banner like 'hero_summer_festival'."""
    fn = f'{name}.jpg'
    if os.path.isfile(os.path.join(_IMAGES_DIR, fn)):
        return url_for('static', filename='images/' + fn)
    return ''


def category_hero_image_url(cat_slug):
    pool = _list_images_for_category(cat_slug)
    if not pool: return ''
    return url_for('static', filename='images/' + pool[0])


# Expose to templates.
@app.context_processor
def _inject_images():
    return dict(
        event_image_url=event_image_url,
        organizer_image_url=organizer_image_url,
        city_image_url=city_image_url,
        hero_image_url=hero_image_url,
        category_hero_image_url=category_hero_image_url,
        subcategories_for=lambda cs: SUBCATEGORY_INDEX.get(cs, []),
        all_subcategory_index=SUBCATEGORY_INDEX,
        neighborhoods_for=lambda cs: NEIGHBORHOODS.get(cs, []),
        all_regions=REGIONS,
    )


# ─── Helper: cart summary for templates ──────────────────────────────────────

def _user_cart_lines(user):
    if not user.is_authenticated:
        return []
    rows = CartItem.query.filter_by(user_id=user.id).all()
    out = []
    for r in rows:
        ev = Event.query.get(r.event_id)
        tier = TicketTier.query.get(r.tier_id)
        if not ev or not tier: continue
        out.append({
            'cart_id': r.id, 'event': ev, 'tier': tier, 'qty': r.qty,
            'line_total': tier.price * r.qty,
        })
    return out


@app.context_processor
def _inject_cart():
    if current_user.is_authenticated:
        try:
            n = CartItem.query.filter_by(user_id=current_user.id).count()
        except Exception:
            n = 0
        return dict(cart_count=n)
    return dict(cart_count=0)


# ─── Category landing ────────────────────────────────────────────────────────

@app.route('/c/<cat_slug>/')
@app.route('/c/<cat_slug>')
def category_landing(cat_slug):
    if cat_slug not in CAT_MAP:
        abort(404)
    cat_name, color = CAT_MAP[cat_slug]
    today = datetime.utcnow()
    q = (Event.query.filter_by(category_slug=cat_slug, is_online=False)
                    .filter(Event.start_dt >= today))
    upcoming = q.order_by(Event.start_dt.asc()).limit(36).all()
    popular_organizers = (db.session.query(Organizer, db.func.count(Event.id).label('n'))
                          .join(Event, Event.organizer_id == Organizer.id)
                          .filter(Event.category_slug == cat_slug)
                          .group_by(Organizer.id)
                          .order_by(db.desc('n')).limit(10).all())
    subcategories = SUBCATEGORY_INDEX.get(cat_slug, [])
    # Top cities for this category
    by_city = {}
    for ev in upcoming:
        by_city.setdefault(ev.city_slug, []).append(ev)
    return render_template('category_landing.html',
        cat_slug=cat_slug, cat_name=cat_name, color=color,
        upcoming=upcoming, popular_organizers=popular_organizers,
        subcategories=subcategories, by_city=by_city,
    )


@app.route('/c/<cat_slug>/<sub_slug>/')
@app.route('/c/<cat_slug>/<sub_slug>')
def subcategory_landing(cat_slug, sub_slug):
    if cat_slug not in CAT_MAP:
        abort(404)
    subs = SUBCATEGORY_INDEX.get(cat_slug, [])
    sub_name = dict(subs).get(sub_slug)
    if not sub_name:
        abort(404)
    today = datetime.utcnow()
    # Match by Event.subcategory == sub_name OR by tags
    q = (Event.query.filter_by(category_slug=cat_slug)
                    .filter(Event.start_dt >= today))
    all_evs = q.order_by(Event.start_dt.asc()).limit(200).all()
    events = [e for e in all_evs if e.subcategory.lower().startswith(sub_name.lower()[:4])]
    if not events:
        events = all_evs[:24]
    return render_template('subcategory_landing.html',
        cat_slug=cat_slug, cat_name=CAT_MAP[cat_slug][0],
        sub_slug=sub_slug, sub_name=sub_name,
        events=events, subcategories=subs,
    )


# ─── Date-range landing (today / this-weekend / this-week / this-month) ──────

def _date_filter_window(label, today):
    if label == 'today':
        s = today.replace(hour=0, minute=0, second=0, microsecond=0)
        return s, s + timedelta(days=1)
    if label == 'tomorrow':
        s = (today + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return s, s + timedelta(days=1)
    if label == 'this-weekend':
        ws = today + timedelta(days=(5 - today.weekday()) % 7)
        ws = ws.replace(hour=0, minute=0, second=0, microsecond=0)
        return ws, ws + timedelta(days=3)
    if label == 'this-week':
        ws = today.replace(hour=0, minute=0, second=0, microsecond=0)
        return ws, ws + timedelta(days=7)
    if label == 'this-month':
        ws = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_m = (ws.replace(day=28) + timedelta(days=4)).replace(day=1)
        return ws, next_m
    if label == 'next-week':
        ws = today + timedelta(days=7-today.weekday())
        ws = ws.replace(hour=0, minute=0, second=0, microsecond=0)
        return ws, ws + timedelta(days=7)
    return today, today + timedelta(days=30)

DATE_LABELS = {
    'today':         'Events today',
    'tomorrow':      'Events tomorrow',
    'this-weekend':  'This weekend',
    'this-week':     'This week',
    'this-month':    'This month',
    'next-week':     'Next week',
}

@app.route('/events/<label>/')
@app.route('/events/<label>')
def date_landing(label):
    if label not in DATE_LABELS:
        abort(404)
    today = datetime.utcnow()
    start, end = _date_filter_window(label, today)
    events = (Event.query.filter(Event.start_dt >= start, Event.start_dt < end)
                       .order_by(Event.start_dt.asc()).limit(150).all())
    return render_template('date_landing.html',
        label=label, label_name=DATE_LABELS[label],
        events=events, date_labels=DATE_LABELS,
        start=start, end=end,
    )


# ─── Free events hub ─────────────────────────────────────────────────────────

@app.route('/free/')
@app.route('/free')
def free_events():
    today = datetime.utcnow()
    city = request.args.get('city', '')
    q = Event.query.filter(Event.start_dt >= today)
    if city and city in CITY_MAP:
        q = q.filter_by(city_slug=city)
    upcoming = q.order_by(Event.start_dt.asc()).limit(400).all()
    events = [e for e in upcoming if e.is_free()][:80]
    return render_template('free_events.html', events=events, city=city)


# ─── Online events hub (proper landing, not just `online_landing`) ───────────

@app.route('/online/')
@app.route('/online')
def online_hub():
    today = datetime.utcnow()
    q = Event.query.filter_by(is_online=True).filter(Event.start_dt >= today)
    upcoming = q.order_by(Event.start_dt.asc()).limit(120).all()
    by_cat = {}
    for ev in upcoming:
        by_cat.setdefault(ev.category_slug, []).append(ev)
    return render_template('online_hub.html', upcoming=upcoming, by_cat=by_cat)


# ─── Country / region landing ────────────────────────────────────────────────

@app.route('/country/us/')
@app.route('/country/us')
def country_us():
    return render_template('country_us.html', regions=REGIONS, all_cities=CITIES)


@app.route('/region/<region_slug>/')
@app.route('/region/<region_slug>')
def region_landing(region_slug):
    region = next((r for r in REGIONS if r[0] == region_slug), None)
    if not region:
        abort(404)
    rs, name, city_slugs = region
    today = datetime.utcnow()
    events = (Event.query.filter(Event.city_slug.in_(city_slugs),
                                   Event.start_dt >= today)
                        .order_by(Event.start_dt.asc()).limit(60).all())
    return render_template('region_landing.html',
        region_slug=rs, region_name=name,
        cities=[c for c in CITIES if c[0] in city_slugs],
        events=events,
    )


# ─── Neighborhood pages ──────────────────────────────────────────────────────

@app.route('/d/<city_slug>/n/<n_slug>/')
@app.route('/d/<city_slug>/n/<n_slug>')
def neighborhood_landing(city_slug, n_slug):
    if city_slug not in CITY_MAP:
        abort(404)
    hoods = NEIGHBORHOODS.get(city_slug, [])
    n = next((h for h in hoods if h[0] == n_slug), None)
    if not n:
        abort(404)
    slug, name, blurb = n
    today = datetime.utcnow()
    # Heuristic: filter by venue_address containing the neighborhood name.
    q = Event.query.filter_by(city_slug=city_slug, is_online=False).filter(Event.start_dt >= today)
    candidates = q.order_by(Event.start_dt.asc()).limit(400).all()
    nameL = name.lower()
    events = [e for e in candidates if nameL in (e.venue_address or '').lower() or
                                       nameL in (e.venue_name or '').lower()]
    if not events:
        events = candidates[:18]
    return render_template('neighborhood.html',
        city_slug=city_slug, city_name=CITY_MAP[city_slug][0],
        n_slug=slug, n_name=name, blurb=blurb,
        events=events, all_neighborhoods=hoods,
    )


# ─── Trending / top picks ────────────────────────────────────────────────────

@app.route('/trending/')
@app.route('/trending')
def trending_hub():
    today = datetime.utcnow()
    city = request.args.get('city') or 'ny--new-york'
    soon = today + timedelta(days=30)
    base = (Event.query.filter(Event.start_dt >= today, Event.start_dt <= soon)
                       .filter_by(city_slug=city, is_online=False)
                       .order_by(Event.is_featured.desc(), Event.start_dt.asc())
                       .limit(80).all())
    # rank by sold ratio
    def _ratio(e):
        cap = e.total_capacity()
        return (e.total_sold() / cap) if cap else 0.0
    base.sort(key=lambda e: -_ratio(e))
    return render_template('trending.html',
        city=city, events=base[:24], top_picks=base[24:48],
    )


# ─── Organizer sub-pages ─────────────────────────────────────────────────────

@app.route('/o/<slug>/about')
def organizer_about(slug):
    o = Organizer.query.filter_by(slug=slug).first_or_404()
    reviews = OrganizerReview.query.filter_by(organizer_id=o.id).order_by(OrganizerReview.created_at.desc()).limit(20).all()
    avg = (sum(r.rating for r in reviews) / len(reviews)) if reviews else 0
    return render_template('organizer_about.html', o=o, reviews=reviews, avg=avg,
                            follower_count=o.follower_count())


@app.route('/o/<slug>/past')
def organizer_past(slug):
    o = Organizer.query.filter_by(slug=slug).first_or_404()
    past = (Event.query.filter_by(organizer_id=o.id)
                       .filter(Event.start_dt < datetime.utcnow())
                       .order_by(Event.start_dt.desc()).all())
    return render_template('organizer_past.html', o=o, past=past,
                            follower_count=o.follower_count())


@app.route('/o/<slug>/followers')
def organizer_followers(slug):
    o = Organizer.query.filter_by(slug=slug).first_or_404()
    follows = Follow.query.filter_by(organizer_id=o.id).order_by(Follow.followed_at.desc()).limit(60).all()
    # Pull user objects in one go
    user_ids = [f.user_id for f in follows]
    users = User.query.filter(User.id.in_(user_ids)).all() if user_ids else []
    return render_template('organizer_followers.html', o=o, users=users,
                            follower_count=o.follower_count())


# ─── Event "tab" pages (Schedule / Speakers / FAQ / Refund) ──────────────────

@app.route('/e/<slug>/schedule')
def event_schedule(slug):
    ev = Event.query.filter_by(slug=slug).first_or_404()
    return render_template('event_schedule.html', ev=ev)


@app.route('/e/<slug>/speakers')
def event_speakers(slug):
    ev = Event.query.filter_by(slug=slug).first_or_404()
    return render_template('event_speakers.html', ev=ev)


@app.route('/e/<slug>/faq')
def event_faq(slug):
    ev = Event.query.filter_by(slug=slug).first_or_404()
    return render_template('event_faq.html', ev=ev)


@app.route('/e/<slug>/refund')
def event_refund(slug):
    ev = Event.query.filter_by(slug=slug).first_or_404()
    refund_label = dict(REFUND_POLICIES).get(ev.refund_policy, ev.refund_policy)
    return render_template('event_refund.html', ev=ev, refund_label=refund_label)


# ─── Help center: per-section + search ───────────────────────────────────────

@app.route('/help/section/<name>')
def help_section(name):
    name = name.replace('-', ' ').title()
    arts = HelpArticle.query.filter(HelpArticle.section.ilike(name)).order_by(HelpArticle.title).all()
    if not arts:
        # try fuzzier match
        arts = HelpArticle.query.filter(HelpArticle.section.ilike(f'%{name}%')).all()
    if not arts:
        abort(404)
    return render_template('help_section.html', section_name=arts[0].section, articles=arts)


@app.route('/help/search')
def help_search():
    q = (request.args.get('q') or '').strip()
    arts = []
    if q:
        qL = f'%{q.lower()}%'
        arts = HelpArticle.query.filter(
            db.or_(HelpArticle.title.ilike(qL), HelpArticle.body.ilike(qL))
        ).limit(40).all()
    return render_template('help_search.html', q=q, articles=arts)


# ─── Organize hub ────────────────────────────────────────────────────────────

ORGANIZE_PAGES = [
    ('how-it-works', 'How Eventbrite Works',
     'A two-minute walkthrough of creating, promoting, and running an event on Eventbrite.'),
    ('pricing',       'Pricing',
     'Free events are free. Paid events: 3.7% + $1.79 per ticket. No monthly fee. No minimums.'),
    ('features',      'Features',
     'Multi-tier ticketing, scheduled sales, custom checkout questions, embedded checkout, attendee tools.'),
    ('promote',       'Promote your event',
     'Push your event to people most likely to attend with built-in email, Boost ads, and partner integrations.'),
    ('spotlight',     'Spotlight features',
     'Get top-of-feed placement in the cities and categories your audience already browses.'),
    ('music-tools',   'Tools for music organizers',
     'Genre tagging, presales, BO Listening Room, fan profiles, mailing-list sync, fast bag-check check-in.'),
    ('boost',         'Boost ads',
     'Self-serve ad placement across Eventbrite and partner social networks, with budget caps and attribution.'),
    ('salesforce',    'Salesforce integration',
     'Two-way sync with Salesforce — opportunities for VIP/sponsor tiers, attendee fields as Contacts.'),
    ('event-marketing-platform', 'Event marketing platform',
     'Run lifecycle campaigns from invite to follow-up — segmentation, A/B copy, automated reminders.'),
]


@app.route('/organize/')
@app.route('/organize')
def organize_hub():
    return render_template('organize_hub.html', pages=ORGANIZE_PAGES)


@app.route('/organize/<page>')
def organize_page(page):
    p = next((x for x in ORGANIZE_PAGES if x[0] == page), None)
    if not p:
        abort(404)
    slug, title, blurb = p
    return render_template('organize_page.html',
        slug=slug, title=title, blurb=blurb, pages=ORGANIZE_PAGES,
    )


# ─── Blog ────────────────────────────────────────────────────────────────────

@app.route('/blog/')
@app.route('/blog')
def blog_index():
    tag = request.args.get('tag', '')
    q = BlogPost.query
    if tag:
        q = q.filter_by(tag=tag)
    posts = q.order_by(BlogPost.published_at.desc()).limit(40).all()
    tags = [t for (t,) in db.session.query(BlogPost.tag).distinct().all() if t]
    return render_template('blog_index.html', posts=posts, tag=tag, tags=tags)


@app.route('/blog/p/<slug>')
def blog_post(slug):
    p = BlogPost.query.filter_by(slug=slug).first_or_404()
    related = BlogPost.query.filter(BlogPost.tag == p.tag, BlogPost.id != p.id).limit(4).all()
    return render_template('blog_post.html', p=p, related=related)


@app.route('/blog/author/<slug>')
def blog_author(slug):
    a = BlogAuthor.query.filter_by(slug=slug).first_or_404()
    posts = BlogPost.query.filter_by(author_id=a.id).order_by(BlogPost.published_at.desc()).all()
    return render_template('blog_author.html', a=a, posts=posts)


@app.route('/blog/tag/<tag>')
def blog_tag(tag):
    posts = BlogPost.query.filter_by(tag=tag).order_by(BlogPost.published_at.desc()).all()
    tags = [t for (t,) in db.session.query(BlogPost.tag).distinct().all() if t]
    return render_template('blog_index.html', posts=posts, tag=tag, tags=tags)


# ─── Topic hubs (charity / group / conferences / brand) ──────────────────────

@app.route('/causes/')
@app.route('/causes')
def causes_hub():
    today = datetime.utcnow()
    events = (Event.query.filter_by(category_slug='charity')
                       .filter(Event.start_dt >= today)
                       .order_by(Event.start_dt.asc()).limit(36).all())
    return render_template('causes_hub.html', events=events)


@app.route('/conferences/')
@app.route('/conferences')
def conferences_hub():
    today = datetime.utcnow()
    events = (Event.query.filter_by(format='Conference')
                       .filter(Event.start_dt >= today)
                       .order_by(Event.start_dt.asc()).limit(36).all())
    return render_template('conferences_hub.html', events=events)


@app.route('/groups/')
@app.route('/groups')
def groups_hub():
    today = datetime.utcnow()
    events = (Event.query.filter(Event.start_dt >= today)
                       .filter(db.or_(Event.format == 'Networking', Event.category_slug == 'community'))
                       .order_by(Event.start_dt.asc()).limit(36).all())
    return render_template('groups_hub.html', events=events)


@app.route('/spotlight/')
@app.route('/spotlight')
def spotlight_hub():
    today = datetime.utcnow()
    events = (Event.query.filter(Event.is_featured == True, Event.start_dt >= today)
                       .order_by(Event.start_dt.asc()).limit(36).all())
    return render_template('spotlight_hub.html', events=events)


# ─── Static company / mobile / press ─────────────────────────────────────────

@app.route('/mobile')
def mobile_app():
    return render_template('mobile_app.html')

@app.route('/press')
def press_page():
    return render_template('press.html')

@app.route('/investors')
def investors_page():
    return render_template('investors.html')

@app.route('/careers')
def careers_page():
    return render_template('careers.html')

@app.route('/sitemap')
def sitemap_page():
    cities_sample = CITIES
    return render_template('sitemap.html',
        cities=cities_sample, categories=CATEGORIES,
        subcat_index=SUBCATEGORY_INDEX,
    )

@app.route('/about')
def about_page():
    return render_template('about.html')


# ─── POST handlers ───────────────────────────────────────────────────────────

@app.route('/cart')
@login_required
def cart_view():
    lines = _user_cart_lines(current_user)
    total = sum(l['line_total'] for l in lines)
    return render_template('cart.html', lines=lines, total=total)


@app.route('/cart/add', methods=['POST'])
@login_required
def cart_add():
    try:
        tier_id = int(request.form.get('tier_id') or 0)
        qty     = max(1, min(10, int(request.form.get('qty') or 1)))
    except (TypeError, ValueError):
        flash('Invalid quantity.', 'error')
        return redirect(request.referrer or url_for('index'))
    tier = TicketTier.query.get_or_404(tier_id)
    if qty > tier.remaining():
        flash('Not enough tickets remaining.', 'error')
        return redirect(request.referrer or url_for('event_detail', slug=tier.event.slug))
    existing = CartItem.query.filter_by(user_id=current_user.id, tier_id=tier_id).first()
    if existing:
        existing.qty = min(10, existing.qty + qty)
    else:
        db.session.add(CartItem(user_id=current_user.id, event_id=tier.event_id,
                                tier_id=tier_id, qty=qty))
    db.session.commit()
    flash(f'Added {qty} × {tier.name} to your cart.', 'success')
    return redirect(url_for('cart_view'))


@app.route('/cart/remove/<int:cart_id>', methods=['POST'])
@login_required
def cart_remove(cart_id):
    c = CartItem.query.get_or_404(cart_id)
    if c.user_id != current_user.id:
        abort(403)
    db.session.delete(c); db.session.commit()
    flash('Removed from cart.', 'success')
    return redirect(url_for('cart_view'))


@app.route('/checkout/<slug>/promo', methods=['POST'])
@login_required
def apply_promo(slug):
    ev = Event.query.filter_by(slug=slug).first_or_404()
    code = (request.form.get('code') or '').strip().upper()
    p = PromoCode.query.filter_by(code=code).first()
    cart = session.get('eb_cart')
    if not p:
        flash('Promo code not found.', 'error')
    elif cart and cart.get('event_slug') == slug:
        if cart['total'] < p.min_total:
            flash(f'Order total must be at least ${p.min_total:.2f} to use this code.', 'error')
        else:
            if p.percent_off:
                disc = cart['total'] * (p.percent_off / 100.0)
            else:
                disc = p.dollar_off
            disc = min(disc, cart['total'])
            cart['discount'] = disc
            cart['promo_code'] = code
            cart['total_after_discount'] = cart['total'] - disc
            session['eb_cart'] = cart
            flash(f'Applied {code}: −${disc:.2f}', 'success')
    return redirect(url_for('checkout_payment', slug=slug))


@app.route('/o/<slug>/review', methods=['POST'])
@login_required
def review_organizer(slug):
    o = Organizer.query.filter_by(slug=slug).first_or_404()
    try:
        rating = int(request.form.get('rating') or 5)
        rating = max(1, min(5, rating))
    except ValueError:
        rating = 5
    body = (request.form.get('body') or '').strip()[:2000]
    db.session.add(OrganizerReview(user_id=current_user.id, organizer_id=o.id,
                                    rating=rating, body=body))
    db.session.commit()
    flash('Review posted.', 'success')
    return redirect(url_for('organizer_about', slug=slug))


@app.route('/e/<slug>/report', methods=['GET', 'POST'])
def report_event(slug):
    ev = Event.query.filter_by(slug=slug).first_or_404()
    if request.method == 'POST':
        reason = (request.form.get('reason') or 'other').strip()[:60]
        body   = (request.form.get('body')   or '').strip()[:2000]
        email  = (request.form.get('contact_email') or '').strip()[:120]
        uid    = current_user.id if current_user.is_authenticated else None
        db.session.add(Report(user_id=uid, target_type='event', target_id=ev.id,
                              reason=reason, body=body, contact_email=email))
        db.session.commit()
        flash('Report submitted — thanks for letting us know.', 'success')
        return redirect(url_for('event_detail', slug=slug))
    return render_template('report_event.html', ev=ev)


@app.route('/o/<slug>/report', methods=['GET', 'POST'])
def report_organizer(slug):
    o = Organizer.query.filter_by(slug=slug).first_or_404()
    if request.method == 'POST':
        reason = (request.form.get('reason') or 'other').strip()[:60]
        body   = (request.form.get('body')   or '').strip()[:2000]
        email  = (request.form.get('contact_email') or '').strip()[:120]
        uid    = current_user.id if current_user.is_authenticated else None
        db.session.add(Report(user_id=uid, target_type='organizer', target_id=o.id,
                              reason=reason, body=body, contact_email=email))
        db.session.commit()
        flash('Report submitted — thanks.', 'success')
        return redirect(url_for('organizer_profile', slug=slug))
    return render_template('report_organizer.html', o=o)


@app.route('/e/<slug>/share', methods=['POST'])
def share_event_email(slug):
    ev = Event.query.filter_by(slug=slug).first_or_404()
    sender    = (request.form.get('sender_email') or '').strip()[:120]
    recipient = (request.form.get('recipient_email') or '').strip()[:120]
    note      = (request.form.get('note') or '').strip()[:2000]
    if not recipient or '@' not in recipient:
        flash('Recipient email required.', 'error')
        return redirect(url_for('event_detail', slug=slug))
    db.session.add(ShareEmail(event_id=ev.id, sender_email=sender,
                              recipient_email=recipient, note=note))
    db.session.commit()
    flash(f'Email sent to {recipient}.', 'success')
    return redirect(url_for('event_detail', slug=slug))


@app.route('/e/<slug>/notify', methods=['POST'])
def waitlist_event(slug):
    ev = Event.query.filter_by(slug=slug).first_or_404()
    email = (request.form.get('email') or '').strip()[:120]
    if not email and current_user.is_authenticated:
        email = current_user.email
    if not email:
        flash('Email required.', 'error')
        return redirect(url_for('event_detail', slug=slug))
    uid = current_user.id if current_user.is_authenticated else None
    db.session.add(Waitlist(user_id=uid, event_id=ev.id, email=email))
    db.session.commit()
    flash('We\'ll email you when tickets go on sale.', 'success')
    return redirect(url_for('event_detail', slug=slug))


@app.route('/category/<cat_slug>/subscribe', methods=['POST'])
@login_required
def subscribe_category(cat_slug):
    if cat_slug not in CAT_MAP:
        abort(404)
    city = (request.form.get('city') or '').strip()
    if CategorySubscription.query.filter_by(user_id=current_user.id,
            category_slug=cat_slug, city_slug=city).first():
        flash('Already subscribed.', 'success')
    else:
        db.session.add(CategorySubscription(user_id=current_user.id,
            category_slug=cat_slug, city_slug=city))
        db.session.commit()
        flash(f'Subscribed to {CAT_MAP[cat_slug][0]} updates.', 'success')
    return redirect(request.referrer or url_for('category_landing', cat_slug=cat_slug))


@app.route('/o/<slug>/subscribe-emails', methods=['POST'])
def subscribe_organizer_email(slug):
    o = Organizer.query.filter_by(slug=slug).first_or_404()
    email = (request.form.get('email') or '').strip()[:120]
    if not email and current_user.is_authenticated:
        email = current_user.email
    if not email or '@' not in email:
        flash('Email required.', 'error')
        return redirect(url_for('organizer_profile', slug=slug))
    uid = current_user.id if current_user.is_authenticated else None
    db.session.add(OrganizerEmailSubscription(user_id=uid, organizer_id=o.id, email=email))
    db.session.commit()
    flash(f'Subscribed to {o.name} email updates.', 'success')
    return redirect(url_for('organizer_profile', slug=slug))


@app.route('/e/<slug>/invite', methods=['GET', 'POST'])
@login_required
def invite_friends(slug):
    ev = Event.query.filter_by(slug=slug).first_or_404()
    if request.method == 'POST':
        raw = (request.form.get('emails') or '').strip()
        emails = [e.strip() for e in re.split(r'[,\n;]+', raw) if '@' in e]
        message = (request.form.get('message') or '').strip()[:2000]
        if not emails:
            flash('Add at least one valid email.', 'error')
            return render_template('invite_friends.html', ev=ev)
        db.session.add(Invite(user_id=current_user.id, event_id=ev.id,
                              recipient_emails=json.dumps(emails[:20]),
                              message=message))
        db.session.commit()
        flash(f'Invited {len(emails)} friends.', 'success')
        return redirect(url_for('event_detail', slug=slug))
    return render_template('invite_friends.html', ev=ev)


@app.route('/e/<slug>/qa', methods=['POST'])
def event_qa(slug):
    ev = Event.query.filter_by(slug=slug).first_or_404()
    text = (request.form.get('question') or '').strip()
    if not text:
        flash('Question can\'t be blank.', 'error')
        return redirect(url_for('event_detail', slug=slug))
    uid  = current_user.id if current_user.is_authenticated else None
    name = current_user.name if current_user.is_authenticated else (request.form.get('name') or 'Anonymous').strip()[:120]
    db.session.add(EventQuestion(user_id=uid, event_id=ev.id, question=text[:2000], author_name=name))
    db.session.commit()
    flash('Question submitted. The organizer will respond soon.', 'success')
    return redirect(url_for('event_detail', slug=slug))


@app.route('/e/<slug>/rsvp', methods=['POST'])
@login_required
def event_rsvp(slug):
    ev = Event.query.filter_by(slug=slug).first_or_404()
    response = (request.form.get('response') or 'maybe').strip().lower()
    if response not in {'yes', 'maybe', 'no'}:
        response = 'maybe'
    existing = RSVPVote.query.filter_by(user_id=current_user.id, event_id=ev.id).first()
    if existing:
        existing.response = response
    else:
        db.session.add(RSVPVote(user_id=current_user.id, event_id=ev.id, response=response))
    db.session.commit()
    flash(f'RSVP updated: {response.title()}.', 'success')
    return redirect(url_for('event_detail', slug=slug))


@app.route('/tickets/<code>/gift', methods=['GET', 'POST'])
@login_required
def gift_transfer(code):
    o = Order.query.filter_by(code=code, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        try:
            ticket_id = int(request.form.get('ticket_id') or 0)
        except ValueError:
            ticket_id = 0
        recipient_email = (request.form.get('recipient_email') or '').strip()[:120]
        recipient_name  = (request.form.get('recipient_name')  or '').strip()[:120]
        message         = (request.form.get('message')         or '').strip()[:2000]
        t = IssuedTicket.query.filter_by(id=ticket_id, order_id=o.id).first()
        if not t:
            flash('Pick a ticket to gift.', 'error')
        elif not recipient_email or '@' not in recipient_email:
            flash('Recipient email required.', 'error')
        else:
            db.session.add(GiftTransfer(ticket_id=t.id, from_user_id=current_user.id,
                                         recipient_email=recipient_email,
                                         recipient_name=recipient_name,
                                         message=message))
            t.attendee_email = recipient_email
            t.attendee_name  = recipient_name or t.attendee_name
            db.session.commit()
            flash(f'Ticket transferred to {recipient_email}.', 'success')
            return redirect(url_for('order_confirmation', code=code))
    return render_template('gift_transfer.html', order=o)


@app.route('/order/<code>/split', methods=['GET', 'POST'])
@login_required
def group_split(code):
    o = Order.query.filter_by(code=code, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        raw = (request.form.get('emails') or '').strip()
        emails = [e.strip() for e in re.split(r'[,\n;]+', raw) if '@' in e]
        if not emails:
            flash('At least one email required.', 'error')
        else:
            per = (o.total / max(1, len(emails) + 1))
            db.session.add(GroupSplit(order_id=o.id,
                                       payer_emails=json.dumps(emails[:20]),
                                       per_person=per))
            db.session.commit()
            flash(f'Split request sent. ${per:.2f}/person.', 'success')
            return redirect(url_for('order_confirmation', code=code))
    return render_template('group_split.html', order=o)


@app.route('/saved/<int:event_id>/export-ics', methods=['POST', 'GET'])
@login_required
def saved_export_ics(event_id):
    s = SavedEvent.query.filter_by(user_id=current_user.id, event_id=event_id).first_or_404()
    ev = Event.query.get_or_404(event_id)
    return redirect(url_for('event_ics', slug=ev.slug))


# ─── Seeders (idempotent) ────────────────────────────────────────────────────

_PROMO_CODES = [
    ('WELCOME10', '10% off your first event ticket', 10, 0.0,  0.0),
    ('SUMMER25',  '$25 off summer events over $100', 0,  25.0, 100.0),
    ('FREESHIP',  '$0 fee on free events',           0,  0.0,  0.0),
    ('VIP15',     '15% off VIP tier purchases',      15, 0.0,  50.0),
    ('STUDENT',   'Student discount: 20% off',       20, 0.0,  0.0),
    ('LOCAL5',    '$5 off when you spend $30+',      0,  5.0,  30.0),
    ('FOODIE',    '10% off food & drink events',     10, 0.0,  0.0),
    ('AUSTIN50',  '$50 off Austin SXSW-week events', 0, 50.0, 150.0),
    ('OFFLINE20', '20% off in-person events',        20, 0.0,  40.0),
    ('NEWYORK',   '$10 off NY events',               0, 10.0,  25.0),
]

_BLOG_AUTHORS = [
    ('jules-park',   'Jules Park',     'Editor at Eventbrite',
     'Jules covers nightlife, music, and the people who keep cities humming after dark.'),
    ('mira-okafor',  'Mira Okafor',    'Senior Writer',
     'Mira writes about creators, indie venues, and the economics of local events.'),
    ('theo-brennan', 'Theo Brennan',   'Tech & Product Reporter',
     'Theo covers the marketing tools, AI features, and partnerships that shape event-tech.'),
    ('cyril-okafor', 'Cyril Okafor',   'Contributor',
     'Cyril is a frequent contributor on community organizing and grassroots fundraising.'),
    ('lila-moon',    'Lila Moon',      'Music Editor',
     'Lila is a former touring musician and now covers the live music industry.'),
]

_BLOG_POSTS = [
    ('how-to-promote-your-first-event', 'How to promote your first event on Eventbrite',
     'A practical guide to building buzz before doors open — pre-sale email lists, social, partner cross-promotion, and post-launch reminders.',
     'organizing', 'jules-park'),
    ('pricing-tickets-2026', 'How we priced our 2026 ticket tiers',
     'Inside the math behind early bird, GA, VIP, and the rarely-discussed "Group of 4" tier.',
     'organizing', 'theo-brennan'),
    ('the-art-of-the-rooftop', 'The art of the rooftop party',
     'Why a rooftop is more than a venue — it\'s a permission slip. A short feature on the rise of the rooftop in NYC nightlife.',
     'music', 'lila-moon'),
    ('what-an-ai-summit-actually-feels-like', 'What an AI summit actually feels like',
     'A field report from this year\'s AI Product Summit — what worked, what didn\'t, what the hallway track looked like.',
     'tech', 'theo-brennan'),
    ('community-organizing-1', 'Community organizing 101: starting a monthly meetup',
     'Step-by-step from idea to your first 25 attendees — venue, pricing, promotion, and the soft skills nobody talks about.',
     'community', 'cyril-okafor'),
    ('drag-brunch-explained', 'Drag brunch, explained',
     'How the drag brunch became one of the most popular Eventbrite categories in 2026 — and why organizers love it.',
     'culture', 'mira-okafor'),
    ('best-cities-for-events-2026', 'The 10 best cities for events in 2026',
     'We ranked the top US cities by event density, venue diversity, and creator support. Spoiler: Nashville is rising fast.',
     'industry', 'jules-park'),
    ('refund-policy-guide', 'A plain-English guide to refund policies',
     'Strict, moderate, flexible, any — what they actually mean, and how to pick the right one for your event.',
     'organizing', 'jules-park'),
    ('boost-ads-roi', 'How Eventbrite Boost ads compare on ROI',
     'A comparison of Boost ads vs Facebook ads vs newsletter promotion for three NYC organizers.',
     'tech', 'theo-brennan'),
    ('sxsw-week-survival', 'SXSW-week survival guide for Austin events',
     'For organizers running an event during SXSW week — coordinating with the festival, parking, sound, and what to do when it rains.',
     'organizing', 'mira-okafor'),
    ('best-yoga-cities-2026', 'Where to find the best outdoor yoga, summer 2026',
     'From Hudson River Park to Griffith Observatory — a curated tour of public yoga sessions.',
     'health', 'jules-park'),
    ('block-party-from-scratch', 'How to throw a block party from scratch',
     'Permits, sound, insurance, food vendors, and what to do if the cops show up.',
     'community', 'cyril-okafor'),
    ('jazz-revival-2026', 'The 2026 jazz revival, by the numbers',
     'Jazz events on Eventbrite grew 47% YoY. We break down why.',
     'music', 'lila-moon'),
    ('charity-galas-changing', 'The charity gala is changing',
     'A new generation of cause-events is leaning interactive, hybrid, and a lot less black-tie.',
     'industry', 'cyril-okafor'),
    ('online-events-second-wave', 'Online events: the second wave',
     'Post-pandemic online events have matured — fewer one-off webinars, more recurring micro-conferences.',
     'tech', 'theo-brennan'),
    ('food-festival-economics', 'Food festival economics, 2026',
     'Vendor margins, ticket-vs-bites pricing, and how to break even on your first event.',
     'food', 'mira-okafor'),
    ('vinyl-night-resurgence', 'The vinyl-night resurgence',
     'Why nine NYC venues run a recurring vinyl night — and what makes them work.',
     'music', 'lila-moon'),
    ('mental-health-event-guide', 'Running mental-health-first events',
     'A guide to event design that prioritizes attendee well-being — quiet rooms, opt-out moments, trauma-aware staff.',
     'health', 'jules-park'),
    ('volunteer-management-2026', 'Volunteer management for community organizers',
     'How to find, train, and retain volunteers — and the legal stuff nobody warns you about.',
     'community', 'cyril-okafor'),
    ('best-conferences-2026', 'The conferences worth flying for in 2026',
     'Our editors\' picks of the conferences worth the airfare — across tech, food, design, and music.',
     'industry', 'theo-brennan'),
]


def seed_extra():
    """Idempotent seed of: promo codes, blog authors/posts, sample organizer
    reviews, a handful of Q&A and waitlist signups. Gated at function level."""
    if PromoCode.query.count() > 0:
        return

    # 1) Promo codes
    today = datetime(2026, 5, 27, 12, 0, 0)
    for (code, desc, pct, dol, mt) in _PROMO_CODES:
        db.session.add(PromoCode(
            code=code, description=desc, percent_off=pct, dollar_off=dol,
            min_total=mt, valid_from=today - timedelta(days=30),
            valid_to=today + timedelta(days=180),
        ))

    # 2) Blog authors
    author_objs = {}
    for (slug, name, title, bio) in _BLOG_AUTHORS:
        a = BlogAuthor(slug=slug, name=name, title=title, bio=bio)
        db.session.add(a)
        author_objs[slug] = a
    db.session.flush()

    # 3) Blog posts
    cover_pool = []
    if os.path.isdir(_IMAGES_DIR):
        cover_pool = sorted(f for f in os.listdir(_IMAGES_DIR)
                            if f.startswith('hero_') and f.endswith('.jpg'))
    for i, (slug, title, excerpt, tag, author_slug) in enumerate(_BLOG_POSTS):
        cover = cover_pool[i % len(cover_pool)] if cover_pool else ''
        body  = (excerpt + '\n\n' +
                 'We\'ve seen a remarkable shift in how organizers approach this space.  '
                 'Three factors stand out: better tooling, more affordable venues outside '
                 'the traditional hubs, and audience appetite for in-person community after '
                 'years of pandemic-induced online fatigue.\n\n'
                 'In our reporting we talked to organizers in five cities about what\'s '
                 'working in 2026 and what they\'re experimenting with. The common thread: '
                 'a willingness to start small, iterate fast, and let the audience tell you '
                 'what they actually want.\n\n'
                 'Three takeaways: 1) lean into recurring events instead of one-off blowouts, '
                 '2) treat your email list like a community, not a megaphone, and 3) measure '
                 'the things that matter — repeat attendance, not just first-time signups.')
        db.session.add(BlogPost(
            slug=slug, title=title, excerpt=excerpt, body=body, tag=tag,
            cover_image=cover,
            author_id=author_objs[author_slug].id,
            published_at=today - timedelta(days=(i + 1) * 4),
        ))

    # 4) Sample organizer reviews — only on named/verified organizers
    r = _seeded_random('org-reviews')
    benchmark_users = User.query.filter(User.email.like('%@test.com')).all()
    if benchmark_users:
        bodies = [
            'Tickets were easy to manage and the team was super responsive.',
            'Great atmosphere, well-run check-in.',
            'Loved every show. Will go again.',
            'Sound quality was excellent and the venue layout was clear.',
            'Refund process was handled fairly when my plans changed.',
            'A bit cramped for a sold-out event, but worth it for the lineup.',
            'The volunteer team was friendly and professional.',
            'Couldn\'t hear the speakers from the back row — recommend mid-house seats.',
            'Best Eventbrite experience I\'ve had this year.',
        ]
        verified_orgs = Organizer.query.filter_by(verified=True).limit(15).all()
        for o in verified_orgs:
            for _ in range(r.choice([2, 3, 4])):
                u = r.choice(benchmark_users)
                rating = r.choice([5, 5, 4, 5, 5, 4, 3])
                db.session.add(OrganizerReview(
                    user_id=u.id, organizer_id=o.id, rating=rating,
                    body=r.choice(bodies),
                    created_at=today - timedelta(days=r.randint(2, 60)),
                ))

    # 5) Sample Q&A on a handful of curated events
    featured_evs = Event.query.filter(Event.is_featured == True).limit(20).all()
    sample_qa = [
        ('Is there parking on site?',
         'Limited street parking. We recommend rideshare or transit.'),
        ('Can I bring a guest?',
         'Each ticket admits one. Add a second ticket at checkout if you\'d like to bring someone.'),
        ('What\'s the age policy?',
         'See the event header for the age restriction. We card at the door for 21+ events.'),
        ('Will the event be recorded?',
         'Not by default — the organizer will note recording on the event page if it\'s planned.'),
        ('Is the venue wheelchair-accessible?',
         'Yes. Reach out at least 7 days ahead with specific accommodation requests.'),
    ]
    for ev in featured_evs:
        for q, a in r.sample(sample_qa, k=r.choice([2, 3])):
            db.session.add(EventQuestion(
                user_id=None, event_id=ev.id,
                question=q, answer=a, author_name='Anonymous',
                created_at=today - timedelta(days=r.randint(2, 40)),
            ))

    # 6) Sample waitlist signups on sold-out / featured events
    soldout = []
    for ev in featured_evs:
        if ev.is_sold_out():
            soldout.append(ev)
    for ev in (soldout[:5] or featured_evs[:5]):
        for i in range(r.choice([4, 6, 8])):
            db.session.add(Waitlist(
                user_id=None, event_id=ev.id,
                email=f'fan{i}@example.com',
                created_at=today - timedelta(days=r.randint(1, 14)),
            ))

    db.session.commit()


# ─── Priority seeders (reviews / invites / category-subs / org-email-subs /
#     newsletter). Each is gated by its own table's row count so this stays
#     idempotent and byte-identical across /reset. ─────────────────────────────

_REVIEW_BODIES = [
    ('Genuinely one of the best events I\'ve been to this year. The lineup delivered and the venue felt intimate without being cramped.', 5),
    ('Easy entry, clear signage, friendly staff. The opener was a pleasant surprise.', 5),
    ('Sound was excellent and the crowd was into it. Will absolutely come back next time.', 5),
    ('Worth the ticket. A bit of a wait at the bar but everything else was smooth.', 4),
    ('Speakers were sharp and the Q&A actually got into the weeds. Great use of an evening.', 5),
    ('I had high hopes and they were met. The food pairings made it for me.', 5),
    ('Great atmosphere. Pacing was a touch slow in the middle but ended strong.', 4),
    ('Check-in was instant and the staff were warmly welcoming. Loved the after-hours mingling.', 5),
    ('Good event overall — I would mention the venue runs a little warm so dress light.', 4),
    ('A solid showing. The headliner alone was worth the price of admission.', 5),
    ('Very well organized. Real attention to detail from the program to the goody bag.', 5),
    ('Fun, friendly, and a good mix of people. Made several new connections.', 4),
    ('Decent night out, though I wish the set lists ran a bit longer. Still recommend.', 3),
    ('Loved the curation. Each act fit the vibe and the venue choice was perfect.', 5),
    ('Was hesitant to buy but glad I did. The Q&A alone was worth coming for.', 5),
]


def seed_priorities():
    """Seed sample rows for the priority-flow tables (reviews, invites,
    category_subscriptions, org_email_subs, newsletter, reports). Each table
    is gated by its own row count to stay idempotent."""
    today = datetime(2026, 5, 27, 12, 0, 0)
    r = _seeded_random('eb-priorities')

    benchmark_users = User.query.filter(User.email.like('%@test.com')).order_by(User.id).all()

    # 1) Reviews on past events that the benchmark users attended.
    if Review.query.count() == 0 and benchmark_users:
        # Pick past confirmed orders, leave a review per ~70% of them.
        past_orders = (Order.query
                       .filter(Order.user_id.in_([u.id for u in benchmark_users]),
                               Order.status == 'confirmed')
                       .join(Event, Event.id == Order.event_id)
                       .filter(Event.start_dt < today)
                       .order_by(Order.created_at.desc())
                       .limit(30).all())
        seen_pairs = set()
        for o in past_orders:
            if r.random() < 0.30:
                continue
            pair = (o.user_id, o.event_id)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            body, rating = r.choice(_REVIEW_BODIES)
            db.session.add(Review(
                user_id=o.user_id, event_id=o.event_id,
                rating=rating, body=body,
                created_at=o.event.start_dt + timedelta(days=r.randint(1, 9)),
            ))

    # 2) Category subscriptions — every benchmark user subscribes to 2-3 of
    #    their interest categories.
    if CategorySubscription.query.count() == 0:
        for u in benchmark_users:
            interests = u.get_interests() or ['music']
            picks = interests[:r.choice([2, 3])]
            for cat in picks:
                if cat in CAT_MAP:
                    db.session.add(CategorySubscription(
                        user_id=u.id, category_slug=cat,
                        city_slug=r.choice(['', u.city.lower().replace(' ', '-')
                                             if u.city else '']),
                        created_at=today - timedelta(days=r.randint(2, 80)),
                    ))

    # 3) Organizer email subscriptions — sprinkle across verified orgs.
    if OrganizerEmailSubscription.query.count() == 0:
        verified_orgs = Organizer.query.filter_by(verified=True).order_by(Organizer.id).limit(10).all()
        if not verified_orgs:
            verified_orgs = Organizer.query.order_by(Organizer.id).limit(10).all()
        sample_emails = [
            'fan.lila@example.com', 'jules.t@example.com', 'mike.b@example.com',
            'priya.s@example.com', 'nora.r@example.com', 'kai.l@example.com',
            'wren.k@example.com', 'sam.h@example.com',
        ]
        for o in verified_orgs[:6]:
            n = r.choice([1, 2, 3])
            for em in r.sample(sample_emails, k=n):
                db.session.add(OrganizerEmailSubscription(
                    user_id=None, organizer_id=o.id, email=em,
                    created_at=today - timedelta(days=r.randint(1, 45)),
                ))
        # plus one each from a benchmark user
        for u in benchmark_users[:2]:
            o = r.choice(verified_orgs)
            db.session.add(OrganizerEmailSubscription(
                user_id=u.id, organizer_id=o.id, email=u.email,
                created_at=today - timedelta(days=r.randint(1, 30)),
            ))

    # 4) Newsletter signups.
    if NewsletterSignup.query.count() == 0:
        seed_emails = [
            'reader1@example.com', 'reader2@example.com', 'jules.t@example.com',
            'priya.s@example.com', 'nora.r@example.com', 'kai.l@example.com',
            'wren.k@example.com', 'sam.h@example.com', 'mike.b@example.com',
            'fan.lila@example.com', 'tobi.o@example.com', 'devon.r@example.com',
        ]
        for em in seed_emails:
            db.session.add(NewsletterSignup(
                email=em, created_at=today - timedelta(days=r.randint(1, 60)),
            ))

    # 5) Invites — each benchmark user has invited friends to ~1-2 upcoming
    #    events they saved.
    if Invite.query.count() == 0:
        invite_msgs = [
            'Come hang with me — should be a fun night.',
            'Booked this one and grabbing a group. Join?',
            'Was hoping you\'d be in for this — let me know!',
            'Heard good things about the lineup. Want to come along?',
            '',
        ]
        contact_pool = [
            'friend1@example.com', 'friend2@example.com', 'pal@example.com',
            'crew.alex@example.com', 'crew.jay@example.com', 'crew.sam@example.com',
        ]
        for u in benchmark_users:
            saved = (SavedEvent.query.filter_by(user_id=u.id)
                                   .order_by(SavedEvent.id.asc()).limit(8).all())
            if not saved: continue
            picks = r.sample(saved, k=min(len(saved), r.choice([1, 2])))
            for s in picks:
                recipients = r.sample(contact_pool, k=r.choice([2, 3]))
                db.session.add(Invite(
                    user_id=u.id, event_id=s.event_id,
                    recipient_emails=json.dumps(recipients),
                    message=r.choice(invite_msgs),
                    created_at=today - timedelta(days=r.randint(1, 30)),
                ))

    # 6) Reports — a small handful of benign event/organizer reports so the
    #    table isn't empty.
    if Report.query.count() == 0:
        evs = Event.query.order_by(Event.id).limit(40).all()
        orgs = Organizer.query.order_by(Organizer.id).limit(40).all()
        if evs and orgs:
            samples = [
                ('event',     evs[3].id,  'spam',       'Promo links in the description look like spam.'),
                ('event',     evs[11].id, 'inaccurate', 'Event description says doors at 7, marketing says 6.'),
                ('event',     evs[24].id, 'other',      'Refund policy seems inconsistent with the FAQ.'),
                ('organizer', orgs[2].id, 'spam',       'Repeated promotional emails after I unsubscribed.'),
                ('organizer', orgs[7].id, 'other',      'Cancelled an event without notifying ticket holders.'),
            ]
            for (tt, tid, reason, body) in samples:
                db.session.add(Report(
                    user_id=None, target_type=tt, target_id=tid,
                    reason=reason, body=body,
                    contact_email='reporter@example.com',
                    created_at=today - timedelta(days=r.randint(1, 30)),
                ))

    db.session.commit()


# Hook into module-level seed. Called from app.py via:  seed_extra()
