"""Routes for the Eventbrite mirror. Loaded by app.py via _load_module."""
# Globals: app, db, login_manager, bcrypt, User, Organizer, Event, TicketTier,
# SavedEvent, Follow, Order, OrderItem, IssuedTicket, Review, HelpArticle,
# NewsletterSignup, DraftEvent, CATEGORIES, CITIES, CAT_MAP, CITY_MAP,
# REFUND_POLICIES, slugify, short_code, score_event, tokenize, parse_iso_date,
# fmt_dt, fmt_dt_short, fmt_time, event_gradient, organizer_gradient.


def _login_required_or_redirect():
    """Helper that returns a redirect if not logged in; else None."""
    if not current_user.is_authenticated:
        return redirect(url_for('login', next=request.path))
    return None


# ─── Auth ─────────────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        pw    = request.form.get('password') or ''
        u = User.query.filter_by(email=email).first()
        if u and u.check_password(pw):
            login_user(u, remember=True)
            nxt = request.args.get('next') or url_for('index')
            return redirect(nxt)
        error = 'Email or password is incorrect.'
    return render_template('login.html', error=error)


@app.route('/signup', methods=['GET', 'POST'])
@app.route('/register', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        name  = (request.form.get('name')  or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        pw    = request.form.get('password') or ''
        if not (name and email and len(pw) >= 6):
            error = 'Name, email, and password (6+ chars) required.'
        elif User.query.filter_by(email=email).first():
            error = 'An account with that email already exists.'
        else:
            u = User(email=email, name=name)
            u.set_password(pw)
            db.session.add(u); db.session.commit()
            login_user(u)
            return redirect(url_for('index'))
    return render_template('signup.html', error=error)


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()
    return redirect(url_for('index'))


# ─── Home / city / category landing ───────────────────────────────────────────

def _featured_events(n=12, city_slug=None, category_slug=None):
    q = Event.query
    if city_slug:
        q = q.filter_by(city_slug=city_slug)
    if category_slug:
        q = q.filter_by(category_slug=category_slug)
    q = q.filter(Event.start_dt >= datetime.utcnow())
    q = q.order_by(Event.is_featured.desc(), Event.start_dt.asc())
    return q.limit(n).all()


@app.route('/')
def index():
    city_slug = request.args.get('city') or request.cookies.get('eb_city') or 'ny--new-york'
    city_name, _, _, _ = CITY_MAP.get(city_slug, ('New York','NY',0,0))
    today = datetime.utcnow()
    weekend_start = today + timedelta(days=(5 - today.weekday()) % 7)
    weekend_end   = weekend_start + timedelta(days=2)
    weekend_events = (Event.query
                       .filter(Event.city_slug==city_slug, Event.is_online==False,
                               Event.start_dt >= weekend_start.replace(hour=0,minute=0),
                               Event.start_dt <= weekend_end.replace(hour=23,minute=59))
                       .order_by(Event.start_dt.asc()).limit(8).all())
    featured = _featured_events(12, city_slug=city_slug)
    online_events = (Event.query.filter_by(is_online=True)
                       .filter(Event.start_dt >= today)
                       .order_by(Event.start_dt.asc()).limit(8).all())
    popular_cities = CITIES[:14]
    resp = make_response(render_template(
        'index.html', city_slug=city_slug, city_name=city_name,
        weekend_events=weekend_events, featured_events=featured,
        online_events=online_events, popular_cities=popular_cities,
    ))
    resp.set_cookie('eb_city', city_slug, max_age=30*86400)
    return resp


@app.route('/d/<city_slug>/')
@app.route('/d/<city_slug>/all-events/')
@app.route('/d/<city_slug>/<sub>/')
def city_landing(city_slug, sub=None):
    if city_slug == 'online':
        return online_landing(sub or 'all-events')
    if city_slug not in CITY_MAP:
        abort(404)
    city_name, state, _, _ = CITY_MAP[city_slug]
    category_slug = None
    sub_label = None
    if sub:
        # e.g. music--events or this-weekend or free
        if sub == 'this-weekend':
            sub_label = 'This Weekend'
        elif sub == 'free':
            sub_label = 'Free Events'
        elif sub == 'popular':
            sub_label = 'Popular'
        elif sub.endswith('--events'):
            slug = sub[:-len('--events')]
            if slug in CAT_MAP:
                category_slug = slug
                sub_label = CAT_MAP[slug][0]
    q = Event.query.filter_by(city_slug=city_slug, is_online=False)
    q = q.filter(Event.start_dt >= datetime.utcnow())
    if category_slug:
        q = q.filter_by(category_slug=category_slug)
    if sub == 'free':
        # subquery via tickets: events whose min price is 0
        # done in python for simplicity
        all_evs = q.order_by(Event.start_dt.asc()).all()
        events = [e for e in all_evs if e.is_free()]
    elif sub == 'this-weekend':
        today = datetime.utcnow()
        ws = today + timedelta(days=(5 - today.weekday()) % 7)
        we = ws + timedelta(days=2)
        events = q.filter(Event.start_dt >= ws.replace(hour=0,minute=0),
                          Event.start_dt <= we.replace(hour=23,minute=59))\
                  .order_by(Event.start_dt.asc()).all()
    else:
        events = q.order_by(Event.start_dt.asc()).limit(120).all()
    return render_template('city.html',
        city_slug=city_slug, city_name=city_name, state=state,
        sub=sub, sub_label=sub_label, events=events,
        category_slug=category_slug,
    )


@app.route('/d/online/')
@app.route('/d/online/<sub>/')
def online_landing(sub='all-events'):
    category_slug = None
    sub_label = 'Online events'
    if sub.endswith('--events'):
        slug = sub[:-len('--events')]
        if slug in CAT_MAP:
            category_slug = slug
            sub_label = f'Online {CAT_MAP[slug][0]} events'
    q = Event.query.filter_by(is_online=True).filter(Event.start_dt >= datetime.utcnow())
    if category_slug:
        q = q.filter_by(category_slug=category_slug)
    events = q.order_by(Event.start_dt.asc()).limit(120).all()
    return render_template('city.html',
        city_slug='online', city_name='Online', state='',
        sub=sub, sub_label=sub_label, events=events,
        category_slug=category_slug,
    )


# ─── Search with facets ──────────────────────────────────────────────────────

@app.route('/search')
def search():
    q = (request.args.get('q') or '').strip()
    city = request.args.get('city') or ''
    cat  = request.args.get('category') or ''
    fmt  = request.args.get('format') or ''
    price_filter = request.args.get('price') or ''        # free|paid
    venue_filter = request.args.get('venue') or ''        # online|in-person
    lang = request.args.get('language') or ''
    date_filter = request.args.get('when') or ''          # today|tomorrow|this-weekend|this-week|this-month|custom
    date_from = parse_iso_date(request.args.get('from'))
    date_to   = parse_iso_date(request.args.get('to'))
    max_price = request.args.get('max_price')
    sort = request.args.get('sort') or 'date'

    query = Event.query
    if city: query = query.filter_by(city_slug=city)
    if cat:  query = query.filter_by(category_slug=cat)
    if fmt:  query = query.filter_by(format=fmt)
    if venue_filter == 'online':    query = query.filter_by(is_online=True)
    elif venue_filter == 'in-person': query = query.filter_by(is_online=False)
    if lang: query = query.filter_by(language=lang)

    today = datetime.utcnow()
    if date_filter == 'today':
        s = today.replace(hour=0,minute=0,second=0)
        e = s + timedelta(days=1)
        query = query.filter(Event.start_dt >= s, Event.start_dt < e)
    elif date_filter == 'tomorrow':
        s = (today + timedelta(days=1)).replace(hour=0,minute=0,second=0)
        e = s + timedelta(days=1)
        query = query.filter(Event.start_dt >= s, Event.start_dt < e)
    elif date_filter == 'this-weekend':
        ws = today + timedelta(days=(5 - today.weekday()) % 7)
        we = ws + timedelta(days=2)
        query = query.filter(Event.start_dt >= ws.replace(hour=0,minute=0),
                             Event.start_dt <= we.replace(hour=23,minute=59))
    elif date_filter == 'this-week':
        ws = today.replace(hour=0,minute=0,second=0)
        we = ws + timedelta(days=7)
        query = query.filter(Event.start_dt >= ws, Event.start_dt < we)
    elif date_filter == 'this-month':
        ws = today.replace(day=1, hour=0,minute=0,second=0)
        next_m = (ws.replace(day=28) + timedelta(days=4)).replace(day=1)
        query = query.filter(Event.start_dt >= ws, Event.start_dt < next_m)
    if date_from:
        query = query.filter(Event.start_dt >= datetime.combine(date_from, dtime.min))
    if date_to:
        query = query.filter(Event.start_dt <= datetime.combine(date_to, dtime.max))

    events = query.filter(Event.start_dt >= today).order_by(Event.start_dt.asc()).limit(500).all()

    # token-overlap scoring on q
    if q:
        toks = tokenize(q)
        scored = [(score_event(e, toks), e) for e in events]
        scored = [(s, e) for (s, e) in scored if s > 0]
        scored.sort(key=lambda x: (-x[0], x[1].start_dt))
        events = [e for _, e in scored]

    # price filter (post-query because requires tickets relation)
    if price_filter == 'free':
        events = [e for e in events if e.is_free()]
    elif price_filter == 'paid':
        events = [e for e in events if not e.is_free()]
    if max_price:
        try:
            mp = float(max_price)
            events = [e for e in events if e.tickets and e.min_price() <= mp]
        except ValueError:
            pass

    if sort == 'price':
        events.sort(key=lambda e: e.min_price())
    elif sort == 'price-desc':
        events.sort(key=lambda e: -e.max_price())
    # sort=date is the default order

    # facet counts (over the filtered-by-q events, ignoring current category)
    cat_counts = {}
    for e in events:
        cat_counts[e.category_slug] = cat_counts.get(e.category_slug, 0) + 1

    return render_template('search.html',
        q=q, events=events[:80], total=len(events),
        city=city, cat=cat, fmt=fmt, lang=lang, when=date_filter,
        date_from=date_from, date_to=date_to,
        price=price_filter, venue=venue_filter, max_price=max_price, sort=sort,
        cat_counts=cat_counts,
    )


# ─── Event detail ────────────────────────────────────────────────────────────

@app.route('/e/<slug>')
@app.route('/e/<slug>/')
def event_detail(slug):
    ev = Event.query.filter_by(slug=slug).first()
    if not ev: abort(404)
    related = (Event.query.filter(Event.category_slug == ev.category_slug,
                                  Event.id != ev.id,
                                  Event.start_dt >= datetime.utcnow())
                          .order_by(Event.start_dt.asc()).limit(6).all())
    is_saved = False
    is_following = False
    if current_user.is_authenticated:
        is_saved = SavedEvent.query.filter_by(user_id=current_user.id, event_id=ev.id).first() is not None
        is_following = Follow.query.filter_by(user_id=current_user.id, organizer_id=ev.organizer_id).first() is not None
    reviews = (Review.query.filter_by(event_id=ev.id)
                          .order_by(Review.created_at.desc()).limit(10).all())
    return render_template('event_detail.html',
        ev=ev, related=related, is_saved=is_saved,
        is_following=is_following, reviews=reviews,
        refund_label=dict(REFUND_POLICIES).get(ev.refund_policy, ev.refund_policy),
    )


@app.route('/e/<slug>/ics')
def event_ics(slug):
    ev = Event.query.filter_by(slug=slug).first()
    if not ev: abort(404)
    def f(dt): return dt.strftime('%Y%m%dT%H%M%S')
    loc = 'Online' if ev.is_online else f'{ev.venue_name}, {ev.venue_address}'
    body = (
        'BEGIN:VCALENDAR\r\n'
        'VERSION:2.0\r\n'
        'PRODID:-//Eventbrite WebHarbor mirror//EN\r\n'
        'BEGIN:VEVENT\r\n'
        f'UID:{ev.slug}@webharbor.eventbrite\r\n'
        f'DTSTAMP:{f(datetime.utcnow())}Z\r\n'
        f'DTSTART:{f(ev.start_dt)}\r\n'
        f'DTEND:{f(ev.end_dt)}\r\n'
        f'SUMMARY:{(ev.title or "").replace(chr(10),"  ")}\r\n'
        f'LOCATION:{loc}\r\n'
        f'DESCRIPTION:{(ev.summary or "").replace(chr(10),"  ")}\r\n'
        'END:VEVENT\r\nEND:VCALENDAR\r\n'
    )
    resp = make_response(body)
    resp.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    resp.headers['Content-Disposition'] = f'attachment; filename="{ev.slug}.ics"'
    return resp


# ─── Save event / follow organizer ───────────────────────────────────────────

@app.route('/api/save/<int:event_id>', methods=['POST'])
@login_required
def save_event(event_id):
    ev = Event.query.get_or_404(event_id)
    s = SavedEvent.query.filter_by(user_id=current_user.id, event_id=ev.id).first()
    if s:
        db.session.delete(s); db.session.commit()
        return jsonify(saved=False)
    else:
        db.session.add(SavedEvent(user_id=current_user.id, event_id=ev.id))
        db.session.commit()
        return jsonify(saved=True)


@app.route('/save/<int:event_id>', methods=['POST'])
@login_required
def save_event_form(event_id):
    save_event(event_id)
    flash('Saved to your collection.', 'success')
    return redirect(request.referrer or url_for('event_detail', slug=Event.query.get(event_id).slug))


@app.route('/o/<slug>/follow', methods=['POST'])
@login_required
def follow_organizer(slug):
    o = Organizer.query.filter_by(slug=slug).first_or_404()
    f = Follow.query.filter_by(user_id=current_user.id, organizer_id=o.id).first()
    if f:
        db.session.delete(f); db.session.commit()
        following = False
    else:
        db.session.add(Follow(user_id=current_user.id, organizer_id=o.id))
        db.session.commit()
        following = True
    if request.headers.get('Accept', '').startswith('application/json') or request.is_json:
        return jsonify(following=following, follower_count=o.follower_count())
    flash(('Following ' if following else 'Unfollowed ') + o.name, 'success')
    return redirect(request.referrer or url_for('organizer_profile', slug=slug))


# ─── Organizer profile ───────────────────────────────────────────────────────

@app.route('/o/<slug>')
@app.route('/o/<slug>/')
def organizer_profile(slug):
    o = Organizer.query.filter_by(slug=slug).first_or_404()
    upcoming = (Event.query.filter_by(organizer_id=o.id)
                .filter(Event.start_dt >= datetime.utcnow())
                .order_by(Event.start_dt.asc()).all())
    past = (Event.query.filter_by(organizer_id=o.id)
            .filter(Event.start_dt < datetime.utcnow())
            .order_by(Event.start_dt.desc()).limit(20).all())
    is_following = False
    if current_user.is_authenticated:
        is_following = Follow.query.filter_by(user_id=current_user.id, organizer_id=o.id).first() is not None
    return render_template('organizer.html',
        o=o, upcoming=upcoming, past=past, is_following=is_following,
        follower_count=o.follower_count(),
    )


# ─── Checkout ────────────────────────────────────────────────────────────────

def _read_qty(tier_id, max_q):
    raw = request.form.get(f'qty_{tier_id}', '0')
    try: q = int(raw)
    except Exception: q = 0
    return max(0, min(q, max_q))


@app.route('/checkout/<slug>', methods=['GET', 'POST'])
@login_required
def checkout(slug):
    ev = Event.query.filter_by(slug=slug).first_or_404()
    if request.method == 'POST':
        items = []
        total = 0.0
        for t in ev.tickets:
            q = _read_qty(t.id, min(t.max_per_order, t.remaining()))
            if q > 0:
                items.append((t.id, q, t.price, t.name))
                total += q * t.price
        if not items:
            flash('Select at least one ticket.', 'error')
            return redirect(url_for('checkout', slug=slug))
        session['eb_cart'] = {
            'event_slug': slug,
            'items': items,
            'total': total,
        }
        return redirect(url_for('checkout_attendees', slug=slug))
    return render_template('checkout_select.html', ev=ev)


@app.route('/checkout/<slug>/attendees', methods=['GET', 'POST'])
@login_required
def checkout_attendees(slug):
    ev = Event.query.filter_by(slug=slug).first_or_404()
    cart = session.get('eb_cart')
    if not cart or cart.get('event_slug') != slug:
        return redirect(url_for('checkout', slug=slug))
    attendee_slots = []
    for tier_id, q, price, name in cart['items']:
        for i in range(q):
            attendee_slots.append((tier_id, i+1, name, price))
    if request.method == 'POST':
        attendees = []
        for idx, (tier_id, i, name, price) in enumerate(attendee_slots):
            a_name  = (request.form.get(f'name_{idx}')  or '').strip()
            a_email = (request.form.get(f'email_{idx}') or '').strip()
            if not (a_name and a_email):
                flash('Please fill in name and email for each attendee.', 'error')
                return render_template('checkout_attendees.html',
                    ev=ev, cart=cart, slots=attendee_slots, attendees=request.form)
            attendees.append({'tier_id': tier_id, 'name': a_name, 'email': a_email})
        # custom Q&A
        qa_answer = request.form.get('qa_dietary', '').strip()
        session['eb_attendees'] = attendees
        session['eb_qa'] = {'dietary': qa_answer}
        return redirect(url_for('checkout_payment', slug=slug))
    return render_template('checkout_attendees.html',
        ev=ev, cart=cart, slots=attendee_slots, attendees={})


@app.route('/checkout/<slug>/payment', methods=['GET', 'POST'])
@login_required
def checkout_payment(slug):
    ev = Event.query.filter_by(slug=slug).first_or_404()
    cart = session.get('eb_cart')
    attendees = session.get('eb_attendees', [])
    qa = session.get('eb_qa', {})
    if not cart or cart.get('event_slug') != slug or not attendees:
        return redirect(url_for('checkout', slug=slug))
    if request.method == 'POST':
        # Transactional commit with per-tier availability re-check
        order = Order(code=short_code(10), user_id=current_user.id, event_id=ev.id,
                      total=cart['total'], status='confirmed',
                      contact_name=request.form.get('billing_name') or current_user.name,
                      contact_email=request.form.get('billing_email') or current_user.email,
                      contact_phone=request.form.get('billing_phone') or '',
                      notes=json.dumps(qa))
        db.session.add(order); db.session.flush()
        for tier_id, q, price, name in cart['items']:
            t = TicketTier.query.get(tier_id)
            if t.remaining() < q:
                db.session.rollback()
                flash(f'Not enough tickets remaining for {t.name}. Please reduce quantity.', 'error')
                return redirect(url_for('checkout', slug=slug))
            t.sold += q
            db.session.add(OrderItem(order_id=order.id, tier_id=tier_id, qty=q, unit_price=price))
        # issue per-attendee tickets
        for a in attendees:
            db.session.add(IssuedTicket(order_id=order.id, tier_id=a['tier_id'],
                                        code=short_code(12),
                                        attendee_name=a['name'], attendee_email=a['email']))
        db.session.commit()
        session.pop('eb_cart', None)
        session.pop('eb_attendees', None)
        session.pop('eb_qa', None)
        return redirect(url_for('order_confirmation', code=order.code))
    return render_template('checkout_payment.html', ev=ev, cart=cart, attendees=attendees)


@app.route('/order/<code>')
@login_required
def order_confirmation(code):
    o = Order.query.filter_by(code=code, user_id=current_user.id).first_or_404()
    return render_template('order_confirmation.html', order=o, ev=o.event)


@app.route('/order/<code>/cancel', methods=['POST'])
@login_required
def cancel_order(code):
    o = Order.query.filter_by(code=code, user_id=current_user.id).first_or_404()
    if o.status == 'confirmed':
        # restore tier sold counts
        for item in o.items:
            t = TicketTier.query.get(item.tier_id)
            if t:
                t.sold = max(0, t.sold - item.qty)
        o.status = 'cancelled'
        db.session.commit()
        flash(f'Order {o.code} cancelled.', 'success')
    return redirect(url_for('my_tickets'))


# ─── Account / dashboards ────────────────────────────────────────────────────

@app.route('/account')
@login_required
def account():
    return render_template('account.html')


@app.route('/account/edit', methods=['GET', 'POST'])
@login_required
def account_edit():
    if request.method == 'POST':
        current_user.name  = (request.form.get('name')  or current_user.name).strip()
        current_user.phone = (request.form.get('phone') or '').strip()
        current_user.city  = (request.form.get('city')  or current_user.city).strip()
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('account'))
    return render_template('account_edit.html')


@app.route('/account/interests', methods=['GET', 'POST'])
@login_required
def account_interests():
    if request.method == 'POST':
        picks = request.form.getlist('interests')
        current_user.interests = json.dumps(picks[:18])
        db.session.commit()
        flash('Interests updated.', 'success')
        return redirect(url_for('account_interests'))
    return render_template('account_interests.html')


@app.route('/tickets')
@login_required
def my_tickets():
    orders = (Order.query.filter_by(user_id=current_user.id)
                       .order_by(Order.created_at.desc()).all())
    return render_template('my_tickets.html', orders=orders)


@app.route('/saved')
@login_required
def my_saved():
    saves = (SavedEvent.query.filter_by(user_id=current_user.id)
                            .order_by(SavedEvent.saved_at.desc()).all())
    return render_template('my_saved.html', saves=saves)


@app.route('/following')
@login_required
def my_following():
    follows = (Follow.query.filter_by(user_id=current_user.id)
                          .order_by(Follow.followed_at.desc()).all())
    return render_template('my_following.html', follows=follows)


@app.route('/likes')
@login_required
def my_likes():
    return redirect(url_for('my_saved'))


# ─── Reviews ─────────────────────────────────────────────────────────────────

@app.route('/e/<slug>/review', methods=['POST'])
@login_required
def submit_review(slug):
    ev = Event.query.filter_by(slug=slug).first_or_404()
    try:
        rating = int(request.form.get('rating') or 5)
        rating = max(1, min(5, rating))
    except ValueError:
        rating = 5
    body = (request.form.get('body') or '').strip()[:2000]
    db.session.add(Review(user_id=current_user.id, event_id=ev.id,
                          rating=rating, body=body))
    db.session.commit()
    flash('Review posted.', 'success')
    return redirect(url_for('event_detail', slug=slug))


# ─── Calendar view ───────────────────────────────────────────────────────────

@app.route('/calendar')
def calendar_view():
    y = request.args.get('year', type=int)
    m = request.args.get('month', type=int)
    city = request.args.get('city') or 'ny--new-york'
    today = datetime.utcnow()
    y = y or today.year
    m = m or today.month
    first = datetime(y, m, 1)
    nxt_m = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    events = (Event.query.filter(Event.city_slug==city,
                                  Event.start_dt >= first,
                                  Event.start_dt <  nxt_m)
                       .order_by(Event.start_dt.asc()).all())
    # group by day
    days = {}
    for e in events:
        days.setdefault(e.start_dt.day, []).append(e)
    # build a 6x7 grid
    import calendar as cal
    cal.setfirstweekday(cal.SUNDAY)
    weeks = cal.monthcalendar(y, m)
    months_ago = (first - timedelta(days=1)).replace(day=1)
    months_next = nxt_m
    return render_template('calendar.html',
        weeks=weeks, days=days, year=y, month=m,
        month_name=cal.month_name[m], city=city,
        prev_year=months_ago.year, prev_month=months_ago.month,
        next_year=months_next.year, next_month=months_next.month,
    )


# ─── Create-event flow (stub) ────────────────────────────────────────────────

@app.route('/create')
@login_required
def create_intro():
    return render_template('create_intro.html')


def _get_or_make_draft():
    d = DraftEvent.query.filter_by(user_id=current_user.id).order_by(DraftEvent.updated_at.desc()).first()
    if not d:
        d = DraftEvent(user_id=current_user.id, step=1)
        db.session.add(d); db.session.commit()
    return d


@app.route('/create/basics', methods=['GET', 'POST'])
@login_required
def create_basics():
    d = _get_or_make_draft()
    if request.method == 'POST':
        d.title = (request.form.get('title') or '').strip()
        d.summary = (request.form.get('summary') or '').strip()
        d.category_slug = request.form.get('category_slug') or 'music'
        d.city_slug = request.form.get('city_slug') or 'ny--new-york'
        d.is_online = bool(request.form.get('is_online'))
        d.venue_name = (request.form.get('venue_name') or '').strip()
        d.step = max(d.step, 2)
        d.updated_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for('create_details'))
    return render_template('create_basics.html', d=d)


@app.route('/create/details', methods=['GET', 'POST'])
@login_required
def create_details():
    d = _get_or_make_draft()
    if request.method == 'POST':
        try:
            s_date = request.form.get('start_date')
            s_time = request.form.get('start_time') or '19:00'
            e_date = request.form.get('end_date') or s_date
            e_time = request.form.get('end_time') or '21:00'
            d.start_dt = datetime.strptime(f'{s_date} {s_time}', '%Y-%m-%d %H:%M')
            d.end_dt   = datetime.strptime(f'{e_date} {e_time}', '%Y-%m-%d %H:%M')
        except Exception:
            flash('Invalid date/time', 'error')
            return redirect(url_for('create_details'))
        d.description = (request.form.get('description') or '').strip()
        d.step = max(d.step, 3)
        d.updated_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for('create_tickets'))
    return render_template('create_details.html', d=d)


@app.route('/create/tickets', methods=['GET', 'POST'])
@login_required
def create_tickets():
    d = _get_or_make_draft()
    if request.method == 'POST':
        tiers = []
        for i in range(6):
            name = (request.form.get(f'tname_{i}') or '').strip()
            if not name: continue
            try: price = float(request.form.get(f'tprice_{i}') or 0)
            except ValueError: price = 0.0
            try: cap = int(request.form.get(f'tcap_{i}') or 50)
            except ValueError: cap = 50
            tiers.append({'name': name, 'price': price, 'capacity': cap})
        d.tickets_json = json.dumps(tiers)
        d.step = max(d.step, 4)
        d.updated_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for('create_publish'))
    return render_template('create_tickets.html', d=d, tiers=json.loads(d.tickets_json or '[]'))


@app.route('/create/publish', methods=['GET', 'POST'])
@login_required
def create_publish():
    d = _get_or_make_draft()
    if request.method == 'POST':
        flash('Draft saved. Real publish disabled in mirror.', 'success')
        return redirect(url_for('account'))
    return render_template('create_publish.html', d=d, tiers=json.loads(d.tickets_json or '[]'))


# ─── Help center ─────────────────────────────────────────────────────────────

@app.route('/help')
@app.route('/help/')
def help_index():
    articles = HelpArticle.query.order_by(HelpArticle.section, HelpArticle.title).all()
    sections = {}
    for a in articles:
        sections.setdefault(a.section, []).append(a)
    return render_template('help_index.html', sections=sections)


@app.route('/help/<slug>')
def help_article(slug):
    a = HelpArticle.query.filter_by(slug=slug).first_or_404()
    return render_template('help_article.html', a=a)


# ─── Newsletter ──────────────────────────────────────────────────────────────

@app.route('/newsletter', methods=['POST'])
def newsletter_signup():
    em = (request.form.get('email') or '').strip().lower()
    if em and '@' in em:
        if not NewsletterSignup.query.filter_by(email=em).first():
            db.session.add(NewsletterSignup(email=em))
            db.session.commit()
        flash('Thanks — keep an eye on your inbox!', 'success')
    else:
        flash('Please provide a valid email.', 'error')
    return redirect(request.referrer or url_for('index'))


# ─── Misc / health ───────────────────────────────────────────────────────────

@app.route('/_health')
def health():
    return jsonify(ok=True, site='eventbrite',
                   events=Event.query.count(),
                   organizers=Organizer.query.count())


@app.errorhandler(404)
def _404(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def _500(e):
    return render_template('500.html'), 500
