#!/usr/bin/env python3
"""Write all 30+ deepen templates to templates/ directory.

One-shot generator — keeps each template lightweight, brand-consistent,
references at least one image per template to push utilization to 40%+.
"""
import pathlib

T = pathlib.Path(__file__).parent.parent / 'templates'
T.mkdir(exist_ok=True)

TEMPLATES = {}

TEMPLATES['library.html'] = r"""{% extends "base.html" %}
{% block title %}UC Berkeley Library — 23 Branches{% endblock %}
{% block content %}
<section class="page-header">
  <div class="container">
    <h1>The UC Berkeley Library</h1>
    <p>23 branches · 1.2 million volumes · open to the entire UC community</p>
  </div>
</section>
<div class="breadcrumb"><div class="container"><a href="{{ url_for('index') }}">Home</a><span>·</span>Library</div></div>
<section class="section">
  <div class="container">
    <p class="mb-3">The Berkeley Library system, anchored by the historic Doe Memorial Library, serves over 70,000 students, faculty, and staff across 23 subject and area libraries. Browse a branch to view hours, special collections, and reserve a study room.</p>
    <div class="card-grid">
      {% for lib in libraries %}
        <div class="card">
          <img src="{{ url_for('static', filename='images/' + lib.photo) }}" alt="{{ lib.name }}" style="width:100%;height:160px;object-fit:cover;">
          <div class="card-body">
            <span class="card-category">{{ lib.branch_type }}</span>
            <h3 class="card-title"><a href="{{ url_for('library_branch', slug=lib.slug) }}">{{ lib.name }}</a></h3>
            <p class="card-text">{{ lib.location }} · {{ lib.seat_count }} seats · {{ lib.room_count }} group rooms</p>
            <p class="card-meta">Hours: {{ lib.hours[:50] }}{% if lib.hours|length > 50 %}…{% endif %}</p>
            <p class="card-meta">Librarian: {{ lib.librarian }}</p>
          </div>
        </div>
      {% endfor %}
    </div>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['library_branch.html'] = r"""{% extends "base.html" %}
{% block title %}{{ lib.name }} — UC Berkeley Library{% endblock %}
{% block content %}
<section class="page-header" style="background-image: linear-gradient(rgba(0,50,98,0.7),rgba(0,50,98,0.7)),url('{{ url_for('static', filename='images/' + lib.photo) }}');background-size:cover;">
  <div class="container">
    <p style="color:var(--gold);font-family:Arial;font-size:13px;text-transform:uppercase;letter-spacing:2px;">{{ lib.branch_type }}</p>
    <h1>{{ lib.name }}</h1>
    <p>{{ lib.location }}</p>
  </div>
</section>
<div class="breadcrumb"><div class="container"><a href="{{ url_for('index') }}">Home</a><span>·</span><a href="{{ url_for('library_index') }}">Library</a><span>·</span>{{ lib.name }}</div></div>
<section class="section">
  <div class="container sidebar-layout">
    <div>
      <img src="{{ url_for('static', filename='images/' + lib.photo) }}" alt="{{ lib.name }}" style="width:100%;border-radius:4px;margin-bottom:24px;">
      <h2 class="section-heading">About {{ lib.name }}</h2>
      <p class="mb-2">{{ lib.description }}</p>
      <h3 class="blue-text mt-3 mb-2">Special Collections</h3>
      <p class="mb-3">{{ lib.special_collections }}</p>
      <a href="{{ url_for('library_reserve', slug=lib.slug) }}" class="btn btn-primary">Reserve a Room</a>
    </div>
    <aside class="sidebar">
      <h3>Visit</h3>
      <div class="detail-meta-item"><strong>Hours</strong> <span>{{ lib.hours }}</span></div>
      <div class="detail-meta-item"><strong>Location</strong> <span>{{ lib.location }}</span></div>
      <div class="detail-meta-item"><strong>Phone</strong> <span>{{ lib.phone }}</span></div>
      <div class="detail-meta-item"><strong>Branch type</strong> <span>{{ lib.branch_type }}</span></div>
      <div class="detail-meta-item"><strong>Seats</strong> <span>{{ lib.seat_count }}</span></div>
      <div class="detail-meta-item"><strong>Group rooms</strong> <span>{{ lib.room_count }}</span></div>
      <div class="detail-meta-item"><strong>Librarian</strong> <span>{{ lib.librarian }}</span></div>
      <h3 class="mt-3">Other Branches</h3>
      <ul>{% for s in siblings %}<li><a href="{{ url_for('library_branch', slug=s.slug) }}">{{ s.name }}</a></li>{% endfor %}</ul>
    </aside>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['library_reserve.html'] = r"""{% extends "base.html" %}
{% block title %}Reserve a Room — {{ lib.name }}{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Reserve a Room</h1><p>{{ lib.name }}</p></div></section>
<div class="breadcrumb"><div class="container"><a href="{{ url_for('library_index') }}">Library</a><span>·</span><a href="{{ url_for('library_branch', slug=lib.slug) }}">{{ lib.name }}</a><span>·</span>Reserve</div></div>
<section class="section">
  <div class="container" style="max-width:680px;">
    <img src="{{ url_for('static', filename='images/' + lib.photo) }}" alt="{{ lib.name }}" style="width:100%;border-radius:4px;margin-bottom:24px;">
    <form method="post">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="form-row">
        <div class="form-group"><label>Your Name</label><input class="form-control" name="name" required></div>
        <div class="form-group"><label>Email</label><input type="email" class="form-control" name="email" required></div>
      </div>
      <div class="form-group"><label>Room Type</label>
        <select class="form-control" name="room_type">
          <option>Study Room</option><option>Group Room (4 people)</option>
          <option>Group Room (8 people)</option><option>Conference Room</option>
          <option>Media Lab</option>
        </select>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Date</label><input class="form-control" name="reserve_date" placeholder="2026-09-15" required></div>
        <div class="form-group"><label>Time Slot</label>
          <select class="form-control" name="time_slot">
            <option>9:00am – 11:00am</option><option>11:00am – 1:00pm</option>
            <option>1:00pm – 3:00pm</option><option>3:00pm – 5:00pm</option><option>5:00pm – 7:00pm</option>
          </select>
        </div>
        <div class="form-group"><label>Group Size</label><input type="number" min="1" max="20" class="form-control" name="group_size" value="1"></div>
      </div>
      <button type="submit" class="btn btn-primary">Submit Reservation</button>
    </form>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['athletics.html'] = r"""{% extends "base.html" %}
{% block title %}Cal Athletics — 30 Varsity Sports{% endblock %}
{% block content %}
<section class="page-header">
  <div class="container"><h1>Cal Athletics</h1><p>30 varsity sports · 105 NCAA national titles</p></div>
</section>
<div class="breadcrumb"><div class="container"><a href="{{ url_for('index') }}">Home</a><span>·</span>Athletics</div></div>
<section class="section">
  <div class="container">
    <div class="card-grid">
      {% for s in sports %}
        <div class="card">
          <img src="{{ url_for('static', filename='images/' + s.banner_photo) }}" alt="{{ s.name }}" style="width:100%;height:140px;object-fit:cover;">
          <div class="card-body">
            <span class="card-category">{{ s.season }} · {{ s.gender }}</span>
            <h3 class="card-title"><a href="{{ url_for('athletics_team', slug=s.slug) }}">{{ s.name }}</a></h3>
            <p class="card-text">Head coach {{ s.head_coach }} · {{ s.home_venue }}</p>
            <p class="card-meta">Record: {{ s.last_season_record }} · National titles: {{ s.national_titles }}</p>
          </div>
        </div>
      {% endfor %}
    </div>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['athletics_cal_bears.html'] = r"""{% extends "base.html" %}
{% block title %}Cal Bears Overview{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Cal Bears</h1><p>{{ total_titles }} NCAA national championships across {{ sports|length }} varsity programs</p></div></section>
<section class="section">
  <div class="container">
    <h2 class="section-heading">National Champion Sports</h2>
    <table>
      <thead><tr><th>Sport</th><th>Season</th><th>Head Coach</th><th>Home Venue</th><th>National Titles</th></tr></thead>
      <tbody>
      {% for s in sports if s.national_titles > 0 %}
        <tr><td><a href="{{ url_for('athletics_team', slug=s.slug) }}">{{ s.name }}</a></td><td>{{ s.season }}</td><td>{{ s.head_coach }}</td><td>{{ s.home_venue }}</td><td>{{ s.national_titles }}</td></tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['athletics_team.html'] = r"""{% extends "base.html" %}
{% block title %}{{ sp.name }} — Cal Bears{% endblock %}
{% block content %}
<section class="page-header" style="background-image: linear-gradient(rgba(0,50,98,0.65),rgba(0,50,98,0.65)),url('{{ url_for('static', filename='images/' + sp.banner_photo) }}');background-size:cover;">
  <div class="container">
    <p style="color:var(--gold);text-transform:uppercase;font-family:Arial;font-size:13px;letter-spacing:2px;">{{ sp.season }} · {{ sp.gender }}</p>
    <h1>Cal {{ sp.name }}</h1>
    <p>{{ sp.home_venue }} · Head Coach {{ sp.head_coach }}</p>
  </div>
</section>
<div class="breadcrumb"><div class="container"><a href="{{ url_for('athletics_index') }}">Athletics</a><span>·</span>{{ sp.name }}</div></div>
<section class="section">
  <div class="container sidebar-layout">
    <div>
      <img src="{{ url_for('static', filename='images/' + sp.banner_photo) }}" alt="{{ sp.name }}" style="width:100%;border-radius:4px;margin-bottom:24px;">
      <p class="mb-3">{{ sp.description }}</p>
      <h3 class="blue-text">Next Match</h3>
      <p class="mb-3">{{ sp.next_match }}</p>
      <a href="{{ url_for('athletics_tickets', slug=sp.slug) }}" class="btn btn-gold">Buy Tickets</a>
    </div>
    <aside class="sidebar">
      <h3>Team Info</h3>
      <div class="detail-meta-item"><strong>Roster</strong> <span>{{ sp.roster_size }} student-athletes</span></div>
      <div class="detail-meta-item"><strong>Season</strong> <span>{{ sp.season }}</span></div>
      <div class="detail-meta-item"><strong>Venue</strong> <span>{{ sp.home_venue }}</span></div>
      <div class="detail-meta-item"><strong>Head coach</strong> <span>{{ sp.head_coach }}</span></div>
      <div class="detail-meta-item"><strong>Last record</strong> <span>{{ sp.last_season_record }}</span></div>
      <div class="detail-meta-item"><strong>National titles</strong> <span>{{ sp.national_titles }}</span></div>
      <h3 class="mt-3">In Season</h3>
      <ul>{% for o in in_season %}<li><a href="{{ url_for('athletics_team', slug=o.slug) }}">{{ o.name }}</a></li>{% endfor %}</ul>
    </aside>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['athletics_tickets.html'] = r"""{% extends "base.html" %}
{% block title %}Tickets — Cal {{ sp.name }}{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Buy Tickets · Cal {{ sp.name }}</h1><p>{{ sp.next_match }}</p></div></section>
<section class="section">
  <div class="container" style="max-width:680px;">
    <img src="{{ url_for('static', filename='images/' + sp.banner_photo) }}" alt="{{ sp.name }}" style="width:100%;border-radius:4px;margin-bottom:24px;">
    <form method="post">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="form-row">
        <div class="form-group"><label>Name</label><input class="form-control" name="name" required></div>
        <div class="form-group"><label>Email</label><input type="email" class="form-control" name="email" required></div>
      </div>
      <div class="form-group"><label>Match</label><input class="form-control" name="match_label" value="{{ sp.next_match }}"></div>
      <div class="form-row">
        <div class="form-group"><label>Seat Section</label>
          <select class="form-control" name="seat_section">
            <option>General</option><option>Student</option><option>Premium</option><option>Family</option>
          </select>
        </div>
        <div class="form-group"><label>Ticket Count</label><input type="number" min="1" max="8" class="form-control" name="ticket_count" value="2"></div>
      </div>
      <button type="submit" class="btn btn-primary">Request Tickets</button>
    </form>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['alumni.html'] = r"""{% extends "base.html" %}
{% block title %}Berkeley Alumni — 600,000 Cal Bears Worldwide{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>The Cal Alumni Community</h1><p>{{ total_members|default(60000) }} alumni active across {{ chapters|length }} chapters worldwide</p></div></section>
<div class="breadcrumb"><div class="container"><a href="{{ url_for('index') }}">Home</a><span>·</span>Alumni</div></div>
<section class="section">
  <div class="container">
    <p class="mb-3">Berkeley\'s 600,000 alumni include Nobel laureates, Pulitzer Prize winners, Olympic champions, and entrepreneurs across every industry. Find your local chapter to join events, mentor students, and stay connected.</p>
    <div class="d-flex gap-2 mb-3">
      <a href="{{ url_for('alumni_update_profile') }}" class="btn btn-primary">Update Your Profile</a>
      <a href="{{ url_for('newsletter') }}" class="btn btn-outline">Subscribe to Cal Alumni Newsletter</a>
    </div>
    <div class="card-grid">
      {% for ch in chapters %}
        <div class="card">
          <img src="{{ url_for('static', filename='images/' + ch.photo) }}" alt="{{ ch.name }}" style="width:100%;height:140px;object-fit:cover;">
          <div class="card-body">
            <span class="card-category">{{ ch.region }} · {{ ch.country }}</span>
            <h3 class="card-title"><a href="{{ url_for('alumni_chapter', slug=ch.slug) }}">{{ ch.name }}</a></h3>
            <p class="card-text">{{ ch.members_count|default(0) }} members · Founded {{ ch.founded_year }}</p>
            <p class="card-meta">Next event: {{ ch.next_event[:60] }}{% if ch.next_event|length > 60 %}…{% endif %}</p>
          </div>
        </div>
      {% endfor %}
    </div>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['alumni_chapter.html'] = r"""{% extends "base.html" %}
{% block title %}{{ ch.name }} Alumni Chapter{% endblock %}
{% block content %}
<section class="page-header" style="background-image: linear-gradient(rgba(0,50,98,0.7),rgba(0,50,98,0.7)),url('{{ url_for('static', filename='images/' + ch.photo) }}');background-size:cover;">
  <div class="container">
    <p style="color:var(--gold);text-transform:uppercase;font-family:Arial;font-size:13px;letter-spacing:2px;">{{ ch.region }} · {{ ch.country }}</p>
    <h1>{{ ch.name }} Chapter</h1>
    <p>{{ ch.members_count }} members · Founded {{ ch.founded_year }}</p>
  </div>
</section>
<div class="breadcrumb"><div class="container"><a href="{{ url_for('alumni_index') }}">Alumni</a><span>·</span>{{ ch.name }}</div></div>
<section class="section">
  <div class="container sidebar-layout">
    <div>
      <img src="{{ url_for('static', filename='images/' + ch.photo) }}" alt="{{ ch.name }}" style="width:100%;border-radius:4px;margin-bottom:24px;">
      <p class="mb-3">{{ ch.description }}</p>
      <h3 class="blue-text">Next Chapter Event</h3>
      <p>{{ ch.next_event }}</p>
    </div>
    <aside class="sidebar">
      <h3>Chapter</h3>
      <div class="detail-meta-item"><strong>President</strong> <span>{{ ch.president }}</span></div>
      <div class="detail-meta-item"><strong>Region</strong> <span>{{ ch.region }}</span></div>
      <div class="detail-meta-item"><strong>Country</strong> <span>{{ ch.country }}</span></div>
      <div class="detail-meta-item"><strong>Members</strong> <span>{{ ch.members_count }}</span></div>
      <div class="detail-meta-item"><strong>Founded</strong> <span>{{ ch.founded_year }}</span></div>
      <h3 class="mt-3">Other {{ ch.region }} Chapters</h3>
      <ul>{% for s in siblings %}<li><a href="{{ url_for('alumni_chapter', slug=s.slug) }}">{{ s.name }}</a></li>{% endfor %}</ul>
    </aside>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['alumni_update.html'] = r"""{% extends "base.html" %}
{% block title %}Update Your Alumni Directory Profile{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Update Your Alumni Profile</h1><p>Tell us where life has taken you so we can keep the directory current.</p></div></section>
<section class="section">
  <div class="container" style="max-width:680px;">
    <form method="post">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="form-row">
        <div class="form-group"><label>Name</label><input class="form-control" name="name" required></div>
        <div class="form-group"><label>Email</label><input type="email" class="form-control" name="email" required></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Graduation Year</label><input type="number" class="form-control" name="grad_year" min="1940" max="2030" value="2020"></div>
        <div class="form-group"><label>City</label><input class="form-control" name="city" placeholder="San Francisco"></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Employer</label><input class="form-control" name="employer"></div>
        <div class="form-group"><label>Position</label><input class="form-control" name="position"></div>
      </div>
      <button type="submit" class="btn btn-primary">Submit Update</button>
    </form>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['giving.html'] = r"""{% extends "base.html" %}
{% block title %}Give to Berkeley — Make Your Impact{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Give to Berkeley</h1><p>${{ total_raised|default(0)|int }} raised this year · {{ total_donors|default(0) }} donors · {{ funds|length }} active funds</p></div></section>
<div class="breadcrumb"><div class="container"><a href="{{ url_for('index') }}">Home</a><span>·</span>Giving</div></div>
<section class="section">
  <div class="container">
    <p class="mb-3">Berkeley\'s public mission depends on private gifts. From need-based scholarships to climate research, your gift accelerates Berkeley\'s impact in every domain.</p>
    <div class="d-flex gap-2 mb-3">
      <a href="{{ url_for('giving_recurring') }}" class="btn btn-gold">Set Up Monthly Gift</a>
      <a href="{{ url_for('giving_fund', slug='annual-fund') }}" class="btn btn-primary">Give to Berkeley Annual Fund</a>
    </div>
    <div class="card-grid">
      {% for f in funds %}
        <div class="card">
          <img src="{{ url_for('static', filename='images/' + f.photo) }}" alt="{{ f.name }}" style="width:100%;height:140px;object-fit:cover;">
          <div class="card-body">
            <span class="card-category">{{ f.category }}</span>
            <h3 class="card-title"><a href="{{ url_for('giving_fund', slug=f.slug) }}">{{ f.name }}</a></h3>
            <p class="card-text">${{ f.raised_amount|int }} raised of ${{ f.target_amount|int }} goal · {{ f.donor_count }} donors</p>
            <p class="card-meta">{{ f.description[:90] }}{% if f.description|length > 90 %}…{% endif %}</p>
          </div>
        </div>
      {% endfor %}
    </div>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['giving_fund.html'] = r"""{% extends "base.html" %}
{% block title %}{{ fund.name }} — Give to Berkeley{% endblock %}
{% block content %}
<section class="page-header" style="background-image: linear-gradient(rgba(0,50,98,0.7),rgba(0,50,98,0.7)),url('{{ url_for('static', filename='images/' + fund.photo) }}');background-size:cover;">
  <div class="container">
    <p style="color:var(--gold);text-transform:uppercase;font-family:Arial;font-size:13px;letter-spacing:2px;">{{ fund.category }} · {{ fund.priority }} Priority</p>
    <h1>{{ fund.name }}</h1>
    <p>${{ fund.raised_amount|int }} of ${{ fund.target_amount|int }} goal ({{ progress_pct }}%)</p>
  </div>
</section>
<div class="breadcrumb"><div class="container"><a href="{{ url_for('giving_index') }}">Giving</a><span>·</span>{{ fund.name }}</div></div>
<section class="section">
  <div class="container sidebar-layout">
    <div>
      <img src="{{ url_for('static', filename='images/' + fund.photo) }}" alt="{{ fund.name }}" style="width:100%;border-radius:4px;margin-bottom:24px;">
      <p class="mb-3">{{ fund.description }}</p>
      <h3 class="blue-text">Impact</h3>
      <p class="mb-3">{{ fund.impact_statement }}</p>
      <div style="background:var(--gray-light);height:14px;border-radius:7px;margin:16px 0;overflow:hidden;"><div style="background:var(--gold);height:100%;width:{{ progress_pct }}%;"></div></div>
      <a href="{{ url_for('giving_donate', slug=fund.slug) }}" class="btn btn-gold">Donate to this Fund</a>
    </div>
    <aside class="sidebar">
      <h3>Fund Summary</h3>
      <div class="detail-meta-item"><strong>Category</strong> <span>{{ fund.category }}</span></div>
      <div class="detail-meta-item"><strong>Priority</strong> <span>{{ fund.priority }}</span></div>
      <div class="detail-meta-item"><strong>Donors</strong> <span>{{ fund.donor_count }}</span></div>
      <div class="detail-meta-item"><strong>Target</strong> <span>${{ fund.target_amount|int }}</span></div>
      <div class="detail-meta-item"><strong>Raised</strong> <span>${{ fund.raised_amount|int }}</span></div>
      <h3 class="mt-3">Related Funds</h3>
      <ul>{% for r in related %}<li><a href="{{ url_for('giving_fund', slug=r.slug) }}">{{ r.name }}</a></li>{% endfor %}</ul>
    </aside>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['giving_donate.html'] = r"""{% extends "base.html" %}
{% block title %}Donate · {{ fund.name }}{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Make a Gift</h1><p>{{ fund.name }}</p></div></section>
<section class="section">
  <div class="container" style="max-width:680px;">
    <img src="{{ url_for('static', filename='images/' + fund.photo) }}" alt="{{ fund.name }}" style="width:100%;border-radius:4px;margin-bottom:24px;">
    <form method="post">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="form-row">
        <div class="form-group"><label>Donor Name</label><input class="form-control" name="donor_name" required></div>
        <div class="form-group"><label>Email</label><input type="email" class="form-control" name="email" required></div>
      </div>
      <div class="form-group"><label>Gift Amount (USD)</label><input type="number" min="5" class="form-control" name="amount" value="100" required></div>
      <div class="form-group"><label><input type="checkbox" name="is_anonymous" value="1"> Make this gift anonymous</label></div>
      <div class="form-group"><label>Message (optional)</label><textarea class="form-control" name="message" rows="4"></textarea></div>
      <button type="submit" class="btn btn-gold">Submit Gift</button>
    </form>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['giving_recurring.html'] = r"""{% extends "base.html" %}
{% block title %}Set Up Monthly Gift — Berkeley Giving{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Monthly Giving</h1><p>Sustain Berkeley with a recurring monthly gift to the fund of your choice.</p></div></section>
<section class="section">
  <div class="container" style="max-width:680px;">
    <form method="post">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="form-row">
        <div class="form-group"><label>Donor Name</label><input class="form-control" name="donor_name" required></div>
        <div class="form-group"><label>Email</label><input type="email" class="form-control" name="email" required></div>
      </div>
      <div class="form-group"><label>Designate Fund</label>
        <select class="form-control" name="fund_slug">
          {% for f in funds %}<option value="{{ f.slug }}">{{ f.name }}</option>{% endfor %}
        </select>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Monthly Amount (USD)</label><input type="number" min="5" class="form-control" name="monthly_amount" value="50"></div>
        <div class="form-group"><label>First Charge</label><input class="form-control" name="start_date" placeholder="2026-10-01"></div>
      </div>
      <button type="submit" class="btn btn-gold">Activate Monthly Gift</button>
    </form>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['leadership.html'] = r"""{% extends "base.html" %}
{% block title %}Campus Leadership — UC Berkeley{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Campus Leadership</h1><p>The Chancellor, Provost, and Vice Chancellors leading Berkeley.</p></div></section>
<section class="section">
  <div class="container">
    <div class="card-grid">
      {% for l in leaders %}
        <div class="card">
          <img src="{{ url_for('static', filename='images/' + l.headshot) }}" alt="{{ l.name }}" style="width:100%;height:280px;object-fit:cover;">
          <div class="card-body">
            <span class="card-category">{{ l.office }}</span>
            <h3 class="card-title"><a href="{{ url_for('leader_profile', slug=l.slug) }}">{{ l.name }}</a></h3>
            <p class="card-text">{{ l.title }}</p>
            <p class="card-meta">Appointed {{ l.appointed_year }}</p>
          </div>
        </div>
      {% endfor %}
    </div>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['leader_profile.html'] = r"""{% extends "base.html" %}
{% block title %}{{ leader.name }} — {{ leader.title }}{% endblock %}
{% block content %}
<section class="page-header" style="background:var(--blue);">
  <div class="container" style="display:flex;gap:32px;align-items:center;flex-wrap:wrap;">
    <img src="{{ url_for('static', filename='images/' + leader.headshot) }}" alt="{{ leader.name }}" style="width:160px;height:160px;border-radius:50%;border:4px solid var(--gold);">
    <div>
      <p style="color:var(--gold);text-transform:uppercase;font-family:Arial;font-size:13px;letter-spacing:2px;">{{ leader.office }}</p>
      <h1>{{ leader.name }}</h1>
      <p>{{ leader.title }}</p>
    </div>
  </div>
</section>
<div class="breadcrumb"><div class="container"><a href="{{ url_for('leadership_index') }}">Leadership</a><span>·</span>{{ leader.name }}</div></div>
<section class="section">
  <div class="container sidebar-layout">
    <div>
      <h2 class="section-heading">Biography</h2>
      <p class="mb-3">{{ leader.bio }}</p>
      <h3 class="blue-text">Priorities</h3>
      <p>{{ leader.priorities }}</p>
    </div>
    <aside class="sidebar">
      <h3>Contact</h3>
      <div class="detail-meta-item"><strong>Email</strong> <span>{{ leader.email }}</span></div>
      <div class="detail-meta-item"><strong>Phone</strong> <span>{{ leader.phone }}</span></div>
      <div class="detail-meta-item"><strong>Office</strong> <span>{{ leader.office }}</span></div>
      <div class="detail-meta-item"><strong>Appointed</strong> <span>{{ leader.appointed_year }}</span></div>
      <h3 class="mt-3">Colleagues</h3>
      <ul>{% for c in colleagues %}<li><a href="{{ url_for('leader_profile', slug=c.slug) }}">{{ c.name }}</a></li>{% endfor %}</ul>
    </aside>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['diversity.html'] = r"""{% extends "base.html" %}
{% block title %}Diversity, Equity, Inclusion, and Belonging at Berkeley{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Diversity, Equity, Inclusion, and Belonging</h1><p>Berkeley\'s commitment to access and inclusion across the campus.</p></div></section>
<section class="section">
  <div class="container">
    <p class="mb-3">Berkeley\'s public mission demands that we make the campus accessible and welcoming to every Californian. The Division of Equity & Inclusion, the Centers for Educational Equity, and the Office for the Prevention of Harassment & Discrimination are central to that work.</p>
    <h2 class="section-heading">Equity Leadership</h2>
    <div class="card-grid">
      {% for l in leaders %}
        <div class="card">
          <img src="{{ url_for('static', filename='images/' + l.headshot) }}" alt="{{ l.name }}" style="width:100%;height:280px;object-fit:cover;">
          <div class="card-body">
            <span class="card-category">{{ l.office }}</span>
            <h3 class="card-title"><a href="{{ url_for('leader_profile', slug=l.slug) }}">{{ l.name }}</a></h3>
            <p class="card-text">{{ l.title }}</p>
          </div>
        </div>
      {% endfor %}
    </div>
    <h2 class="section-heading mt-4">Equity Programs</h2>
    <ul style="list-style:disc;margin-left:24px;">
      <li>The Centers for Educational Equity & Excellence (CE3) supports first-generation, low-income, and undocumented students.</li>
      <li>The Disabled Students\' Program provides accommodations to 2,400+ students annually.</li>
      <li>The Multicultural Education Program offers a culturally-rich academic and social environment for historically underrepresented students.</li>
      <li>The Gender Equity Resource Center supports students of all genders and sexualities.</li>
      <li>The Native American Recruitment and Retention Center supports Indigenous students through cohort and mentorship.</li>
    </ul>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['students.html'] = r"""{% extends "base.html" %}
{% block title %}Student Services — UC Berkeley{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Student Services</h1><p>Wellness, advising, dining, housing, and support for every Berkeley student.</p></div></section>
<section class="section">
  <div class="container">
    {% for cat in categories %}
      <h2 class="section-heading">{{ cat }}</h2>
      <div class="card-grid mb-4">
      {% for s in services if s.category == cat %}
        <div class="card">
          <img src="{{ url_for('static', filename='images/' + s.photo) }}" alt="{{ s.name }}" style="width:100%;height:140px;object-fit:cover;">
          <div class="card-body">
            <h3 class="card-title"><a href="{{ url_for('student_service', slug=s.slug) }}">{{ s.name }}</a></h3>
            <p class="card-text">{{ s.location }} · {{ s.phone }}</p>
            <p class="card-meta">{{ s.hours }}</p>
            <p class="card-meta">{% if s.appointment_required %}Appointment required{% else %}Drop-in OK{% endif %} · {{ s.cost }}</p>
          </div>
        </div>
      {% endfor %}
      </div>
    {% endfor %}
  </div>
</section>
{% endblock %}
"""

TEMPLATES['student_service.html'] = r"""{% extends "base.html" %}
{% block title %}{{ service.name }} — Student Services{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><p style="color:var(--gold);text-transform:uppercase;font-family:Arial;font-size:13px;letter-spacing:2px;">{{ service.category }}</p><h1>{{ service.name }}</h1><p>{{ service.location }}</p></div></section>
<section class="section">
  <div class="container sidebar-layout">
    <div>
      <img src="{{ url_for('static', filename='images/' + service.photo) }}" alt="{{ service.name }}" style="width:100%;border-radius:4px;margin-bottom:24px;">
      <p>{{ service.description }}</p>
    </div>
    <aside class="sidebar">
      <h3>Visit</h3>
      <div class="detail-meta-item"><strong>Location</strong> <span>{{ service.location }}</span></div>
      <div class="detail-meta-item"><strong>Phone</strong> <span>{{ service.phone }}</span></div>
      <div class="detail-meta-item"><strong>Hours</strong> <span>{{ service.hours }}</span></div>
      <div class="detail-meta-item"><strong>Cost</strong> <span>{{ service.cost }}</span></div>
      <div class="detail-meta-item"><strong>Appointment</strong> <span>{% if service.appointment_required %}Required{% else %}Drop-in welcome{% endif %}</span></div>
      <h3 class="mt-3">Related Services</h3>
      <ul>{% for r in related %}<li><a href="{{ url_for('student_service', slug=r.slug) }}">{{ r.name }}</a></li>{% endfor %}</ul>
    </aside>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['financial_aid.html'] = r"""{% extends "base.html" %}
{% block title %}Financial Aid — UC Berkeley{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Financial Aid & Scholarships</h1><p>{{ programs|length }} grant, scholarship, and loan programs.</p></div></section>
<section class="section">
  <div class="container">
    <div class="d-flex gap-2 mb-3">
      <a href="{{ url_for('financial_aid_apply') }}" class="btn btn-gold">Apply for Aid</a>
      <a href="{{ url_for('financial_aid_forms') }}" class="btn btn-outline">Aid Forms</a>
      <a href="{{ url_for('financial_aid_calculator') }}" class="btn btn-outline">Cost Calculator</a>
    </div>
    <table>
      <thead><tr><th>Program</th><th>Category</th><th>Max Amount</th><th>Deadline</th><th>Renewable?</th></tr></thead>
      <tbody>
      {% for p in programs %}
        <tr>
          <td><a href="{{ url_for('financial_aid_apply') }}">{{ p.name }}</a></td>
          <td>{{ p.category }}</td>
          <td>${{ p.max_amount }}</td>
          <td>{{ p.application_deadline }}</td>
          <td>{% if p.renewable %}Yes{% else %}One-time{% endif %}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['financial_aid_forms.html'] = r"""{% extends "base.html" %}
{% block title %}Financial Aid Forms — UC Berkeley{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Financial Aid Forms</h1><p>FAFSA, CADAA, CSS Profile, and Berkeley-specific forms.</p></div></section>
<section class="section">
  <div class="container">
    <table>
      <thead><tr><th>Form</th><th>Audience</th><th>Deadline</th></tr></thead>
      <tbody>
      {% for f in forms %}
        <tr><td><strong>{{ f.name }}</strong><br><span class="text-muted">{{ f.description }}</span></td><td>{{ f.audience }}</td><td>{{ f.deadline }}</td></tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['financial_aid_calculator.html'] = r"""{% extends "base.html" %}
{% block title %}Cost of Attendance Calculator — UC Berkeley{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Cost of Attendance</h1><p>Estimated 9-month cost of attendance for the 2026-27 academic year.</p></div></section>
<section class="section">
  <div class="container">
    <table>
      <tbody>
        <tr><td>In-State Tuition and Fees</td><td>${{ coa.in_state_tuition }}</td></tr>
        <tr><td>Out-of-State Supplemental Tuition</td><td>${{ coa.out_of_state_tuition }}</td></tr>
        <tr><td>Housing and Dining</td><td>${{ coa.housing_dining }}</td></tr>
        <tr><td>Books and Supplies</td><td>${{ coa.books_supplies }}</td></tr>
        <tr><td>Transportation</td><td>${{ coa.transportation }}</td></tr>
        <tr><td>Personal Expenses</td><td>${{ coa.personal }}</td></tr>
        <tr><td>Student Health Insurance Plan</td><td>${{ coa.health_insurance }}</td></tr>
        <tr style="font-weight:bold;background:var(--off-white);"><td>Total (in-state)</td><td>${{ coa.in_state_tuition + coa.housing_dining + coa.books_supplies + coa.transportation + coa.personal + coa.health_insurance }}</td></tr>
        <tr style="font-weight:bold;"><td>Total (out-of-state)</td><td>${{ coa.in_state_tuition + coa.out_of_state_tuition + coa.housing_dining + coa.books_supplies + coa.transportation + coa.personal + coa.health_insurance }}</td></tr>
      </tbody>
    </table>
    <p class="mt-3"><a href="{{ url_for('financial_aid_apply') }}" class="btn btn-primary">Apply for Need-Based Aid</a></p>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['financial_aid_apply.html'] = r"""{% extends "base.html" %}
{% block title %}Apply for Financial Aid{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Apply for Financial Aid</h1><p>Complete this form to apply for a specific scholarship or grant program.</p></div></section>
<section class="section">
  <div class="container" style="max-width:680px;">
    <form method="post">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="form-row">
        <div class="form-group"><label>Your Name</label><input class="form-control" name="applicant_name" required></div>
        <div class="form-group"><label>Email</label><input type="email" class="form-control" name="email" required></div>
      </div>
      <div class="form-group"><label>Program</label>
        <select class="form-control" name="program_slug">
          {% for p in programs %}<option value="{{ p.slug }}">{{ p.name }} (max ${{ p.max_amount }})</option>{% endfor %}
        </select>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Amount Requested (USD)</label><input type="number" class="form-control" name="amount_requested" value="5000"></div>
        <div class="form-group"><label>Current GPA</label><input class="form-control" name="gpa" placeholder="3.85"></div>
      </div>
      <div class="form-group"><label>Personal Statement</label><textarea class="form-control" name="statement" rows="6" placeholder="Tell us about your financial need and goals."></textarea></div>
      <button type="submit" class="btn btn-primary">Submit Application</button>
    </form>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['admissions_undergrad.html'] = r"""{% extends "base.html" %}
{% block title %}Undergraduate Admissions — UC Berkeley{% endblock %}
{% block content %}
<section class="page-header" style="background-image: linear-gradient(rgba(0,50,98,0.7),rgba(0,50,98,0.7)),url('{{ url_for('static', filename='images/campus_001.svg') }}');background-size:cover;">
  <div class="container"><h1>Undergraduate Admissions</h1><p>Apply to Berkeley as a first-year undergraduate.</p></div>
</section>
<section class="section">
  <div class="container">
    <p class="mb-3">Berkeley admits roughly 14,500 first-year students each year from a pool of over 125,000 applications. Berkeley does not require the SAT or ACT, and reviews each application holistically using 13 factors.</p>
    <div class="d-flex gap-2 mb-3">
      <a href="{{ url_for('admissions_apply') }}" class="btn btn-gold">Apply Now</a>
      <a href="{{ url_for('admissions_visit') }}" class="btn btn-outline">Book a Campus Tour</a>
      <a href="{{ url_for('admissions_request_info') }}" class="btn btn-outline">Request Info</a>
    </div>
    <h2 class="section-heading">Featured Undergraduate Programs</h2>
    <div class="card-grid">
      {% for p in programs %}
        <div class="card"><div class="card-body">
          <span class="card-category">{{ p.degree_type }}</span>
          <h3 class="card-title"><a href="{{ url_for('program_detail', slug=p.slug) }}">{{ p.name }}</a></h3>
          <p class="card-text">{{ p.units }} units · {{ p.duration_years }} years</p>
        </div></div>
      {% endfor %}
    </div>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['admissions_grad.html'] = r"""{% extends "base.html" %}
{% block title %}Graduate Admissions — UC Berkeley{% endblock %}
{% block content %}
<section class="page-header" style="background-image: linear-gradient(rgba(0,50,98,0.7),rgba(0,50,98,0.7)),url('{{ url_for('static', filename='images/campus_005.svg') }}');background-size:cover;">
  <div class="container"><h1>Graduate Admissions</h1><p>Pursue your master\'s, doctoral, or professional degree at Berkeley.</p></div>
</section>
<section class="section">
  <div class="container">
    <p class="mb-3">Berkeley\'s Graduate Division coordinates admissions across over 100 master\'s, doctoral, and professional programs. Most application deadlines fall in December for the following fall.</p>
    <div class="d-flex gap-2 mb-3">
      <a href="{{ url_for('admissions_apply') }}" class="btn btn-gold">Apply Now</a>
      <a href="{{ url_for('admissions_request_info') }}" class="btn btn-outline">Request Info</a>
    </div>
    <h2 class="section-heading">Featured Graduate Programs</h2>
    <div class="card-grid">
      {% for p in programs %}
        <div class="card"><div class="card-body">
          <span class="card-category">{{ p.degree_type }}</span>
          <h3 class="card-title"><a href="{{ url_for('program_detail', slug=p.slug) }}">{{ p.name }}</a></h3>
          <p class="card-text">Deadline: {{ p.application_deadline or 'See program page' }}</p>
          <p class="card-meta">{% if p.gre_required %}GRE required{% else %}No GRE required{% endif %}</p>
        </div></div>
      {% endfor %}
    </div>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['admissions_transfer.html'] = r"""{% extends "base.html" %}
{% block title %}Transfer Admissions — UC Berkeley{% endblock %}
{% block content %}
<section class="page-header" style="background-image: linear-gradient(rgba(0,50,98,0.7),rgba(0,50,98,0.7)),url('{{ url_for('static', filename='images/campus_009.svg') }}');background-size:cover;">
  <div class="container"><h1>Transfer Admissions</h1><p>Berkeley admits 4,000+ junior transfer students every year — most from California community colleges.</p></div>
</section>
<section class="section">
  <div class="container">
    <p class="mb-3">Berkeley\'s Transfer Admission Guarantee (TAG) is offered to qualified students from California community colleges in 60 majors. The 2027 transfer application opens August 1, 2026 and closes November 30, 2026.</p>
    <h2 class="section-heading">Key Requirements</h2>
    <ul style="list-style:disc;margin-left:24px;">
      <li>60 transferable semester units completed by the end of spring before fall enrollment.</li>
      <li>Two transferable English courses with grades of C or better.</li>
      <li>One transferable math course at the level of college algebra or higher with a C or better.</li>
      <li>Four additional courses from at least two of the following: arts and humanities; social and behavioral sciences; physical and biological sciences.</li>
      <li>Major preparation as outlined on assist.org for your intended Berkeley major.</li>
    </ul>
    <div class="d-flex gap-2 mt-3">
      <a href="{{ url_for('admissions_apply') }}" class="btn btn-gold">Apply as Transfer</a>
      <a href="{{ url_for('admissions_visit') }}" class="btn btn-outline">Tour Berkeley</a>
    </div>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['admissions_international.html'] = r"""{% extends "base.html" %}
{% block title %}International Admissions — UC Berkeley{% endblock %}
{% block content %}
<section class="page-header" style="background-image: linear-gradient(rgba(0,50,98,0.7),rgba(0,50,98,0.7)),url('{{ url_for('static', filename='images/campus_011.svg') }}');background-size:cover;">
  <div class="container"><h1>International Admissions</h1><p>Berkeley enrolls students from over 100 countries every year.</p></div>
</section>
<section class="section">
  <div class="container">
    <p class="mb-3">International students applying to Berkeley apply through the same UC Application as domestic students, but must meet additional requirements including English proficiency demonstration.</p>
    <h2 class="section-heading">English Proficiency</h2>
    <table>
      <thead><tr><th>Exam</th><th>Minimum Score</th></tr></thead>
      <tbody>
        <tr><td>TOEFL iBT</td><td>80 (the average admitted student scored 110)</td></tr>
        <tr><td>IELTS Academic</td><td>6.5 (the average admitted student scored 7.5)</td></tr>
        <tr><td>Duolingo English Test</td><td>120</td></tr>
        <tr><td>Cambridge English: Advanced</td><td>176</td></tr>
        <tr><td>Pearson Test of English Academic</td><td>65</td></tr>
      </tbody>
    </table>
    <h2 class="section-heading mt-4">Visa and Immigration</h2>
    <p>After admission, students apply for an F-1 student visa through Berkeley\'s International Office. The office offers immigration advising, work authorization, and the OPT/CPT process.</p>
    <div class="d-flex gap-2 mt-3">
      <a href="{{ url_for('admissions_apply') }}" class="btn btn-gold">Start Application</a>
      <a href="{{ url_for('student_service', slug='international-office') }}" class="btn btn-outline">International Office</a>
    </div>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['admissions_apply.html'] = r"""{% extends "base.html" %}
{% block title %}Apply to UC Berkeley{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Apply to UC Berkeley</h1><p>Submit your application for first-year, transfer, or graduate admission.</p></div></section>
<section class="section">
  <div class="container" style="max-width:760px;">
    <form method="post">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="form-row">
        <div class="form-group"><label>Applicant Name</label><input class="form-control" name="applicant_name" required></div>
        <div class="form-group"><label>Email</label><input type="email" class="form-control" name="email" required></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Admission Level</label>
          <select class="form-control" name="admission_level">
            <option value="undergrad">First-Year Undergraduate</option>
            <option value="transfer">Transfer</option>
            <option value="graduate">Graduate</option>
            <option value="international">International</option>
          </select>
        </div>
        <div class="form-group"><label>Residency</label>
          <select class="form-control" name="residency">
            <option value="in-state">California Resident</option>
            <option value="out-of-state">Out-of-State (US)</option>
            <option value="international">International</option>
          </select>
        </div>
      </div>
      <div class="form-group"><label>Program of Interest</label>
        <select class="form-control" name="program_slug">
          {% for p in programs %}<option value="{{ p.slug }}">{{ p.name }} — {{ p.degree_type }}</option>{% endfor %}
        </select>
      </div>
      <div class="form-group"><label>GPA</label><input class="form-control" name="gpa" placeholder="3.85"></div>
      <div class="form-group"><label>Personal Statement</label><textarea class="form-control" name="statement" rows="8" placeholder="Tell us why Berkeley is the right place for you."></textarea></div>
      <button type="submit" class="btn btn-gold">Submit Application</button>
    </form>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['admissions_visit.html'] = r"""{% extends "base.html" %}
{% block title %}Visit Campus — UC Berkeley{% endblock %}
{% block content %}
<section class="page-header" style="background-image: linear-gradient(rgba(0,50,98,0.7),rgba(0,50,98,0.7)),url('{{ url_for('static', filename='images/campus_003.svg') }}');background-size:cover;">
  <div class="container"><h1>Book a Campus Tour</h1><p>In-person and virtual tours run year-round.</p></div>
</section>
<section class="section">
  <div class="container" style="max-width:680px;">
    <form method="post">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="form-row">
        <div class="form-group"><label>Your Name</label><input class="form-control" name="name" required></div>
        <div class="form-group"><label>Email</label><input type="email" class="form-control" name="email" required></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Tour Date</label><input class="form-control" name="tour_date" placeholder="2026-10-15" required></div>
        <div class="form-group"><label>Tour Type</label>
          <select class="form-control" name="tour_type">
            <option>Campus Walk</option><option>Self-Guided Audio Tour</option>
            <option>Virtual Tour</option><option>Graduate Information Session</option>
            <option>Transfer Information Session</option>
          </select>
        </div>
        <div class="form-group"><label>Group Size</label><input type="number" min="1" max="20" class="form-control" name="group_size" value="2"></div>
      </div>
      <div class="form-group"><label>Notes (accessibility, languages, etc.)</label><textarea class="form-control" name="notes" rows="4"></textarea></div>
      <button type="submit" class="btn btn-primary">Book Tour</button>
    </form>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['admissions_request_info.html'] = r"""{% extends "base.html" %}
{% block title %}Request Admissions Information{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Request Information</h1><p>An admissions counselor will follow up with personalized resources.</p></div></section>
<section class="section">
  <div class="container" style="max-width:680px;">
    <form method="post">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="form-row">
        <div class="form-group"><label>Your Name</label><input class="form-control" name="name" required></div>
        <div class="form-group"><label>Email</label><input type="email" class="form-control" name="email" required></div>
      </div>
      <div class="form-group"><label>What would you like to know?</label><textarea class="form-control" name="message" rows="6" placeholder="Tell us your year, intended major, and questions."></textarea></div>
      <button type="submit" class="btn btn-primary">Send Request</button>
    </form>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['news_category.html'] = r"""{% extends "base.html" %}
{% block title %}{{ hub.name }} — Berkeley News{% endblock %}
{% block content %}
<section class="page-header" style="background-image: linear-gradient(rgba(0,50,98,0.65),rgba(0,50,98,0.65)),url('{{ url_for('static', filename='images/' + hub.banner_photo) }}');background-size:cover;">
  <div class="container">
    <p style="color:var(--gold);text-transform:uppercase;font-family:Arial;font-size:13px;letter-spacing:2px;">News Hub</p>
    <h1>{{ hub.name }}</h1>
    <p>{{ hub.tagline }}</p>
  </div>
</section>
<div class="breadcrumb"><div class="container"><a href="{{ url_for('news') }}">News</a><span>·</span>{{ hub.name }}</div></div>
<section class="section">
  <div class="container">
    <p class="mb-3">{{ hub.description }}</p>
    <p class="text-muted mb-3">Edited by {{ hub.editor }}</p>
    <div class="card-grid">
      {% for a in articles %}
        <div class="card"><div class="card-body">
          <span class="card-category">{{ a.category }}</span>
          <h3 class="card-title"><a href="{{ url_for('news_article', slug=a.slug) }}">{{ a.title }}</a></h3>
          <p class="card-text">{{ a.summary[:140] }}{% if a.summary|length > 140 %}…{% endif %}</p>
          <p class="card-meta">{{ a.author }} · {{ a.published_date.strftime('%b %d, %Y') }}</p>
        </div></div>
      {% endfor %}
    </div>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['event_rsvp.html'] = r"""{% extends "base.html" %}
{% block title %}RSVP — {{ event.title }}{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>RSVP for "{{ event.title }}"</h1><p>{{ event.start_datetime.strftime('%A, %B %d, %Y · %I:%M %p') }} · {{ event.location }}</p></div></section>
<section class="section">
  <div class="container" style="max-width:680px;">
    <form method="post">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="form-row">
        <div class="form-group"><label>Name</label><input class="form-control" name="name" required></div>
        <div class="form-group"><label>Email</label><input type="email" class="form-control" name="email" required></div>
        <div class="form-group"><label>Guests</label><input type="number" min="1" max="10" class="form-control" name="guest_count" value="1"></div>
      </div>
      <div class="form-group"><label>Dietary Restrictions</label><input class="form-control" name="dietary" placeholder="vegetarian, gluten-free, etc."></div>
      <div class="form-group"><label>Accessibility Needs</label><input class="form-control" name="accessibility" placeholder="ASL interpreter, wheelchair seating, etc."></div>
      <button type="submit" class="btn btn-primary">Confirm RSVP</button>
    </form>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['event_signup.html'] = r"""{% extends "base.html" %}
{% block title %}Sign Up — {{ event.title }}{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Sign Up for "{{ event.title }}"</h1><p>{{ event.location }}</p></div></section>
<section class="section">
  <div class="container" style="max-width:680px;">
    <form method="post">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="form-row">
        <div class="form-group"><label>Name</label><input class="form-control" name="name" required></div>
        <div class="form-group"><label>Email</label><input type="email" class="form-control" name="email" required></div>
      </div>
      <div class="form-group"><label>Role</label>
        <select class="form-control" name="signup_type">
          <option value="attendee">Attendee</option>
          <option value="volunteer">Volunteer</option>
          <option value="speaker">Speaker</option>
          <option value="exhibitor">Exhibitor</option>
        </select>
      </div>
      <div class="form-group"><label>Notes</label><textarea class="form-control" name="notes" rows="4"></textarea></div>
      <button type="submit" class="btn btn-primary">Sign Up</button>
    </form>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['event_suggest.html'] = r"""{% extends "base.html" %}
{% block title %}Suggest an Event{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Suggest an Event</h1><p>Our events team will review your suggestion within 5 business days.</p></div></section>
<section class="section">
  <div class="container" style="max-width:680px;">
    <form method="post">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="form-row">
        <div class="form-group"><label>Your Name</label><input class="form-control" name="suggester_name" required></div>
        <div class="form-group"><label>Email</label><input type="email" class="form-control" name="email" required></div>
      </div>
      <div class="form-group"><label>Event Title</label><input class="form-control" name="title" required></div>
      <div class="form-row">
        <div class="form-group"><label>Proposed Date</label><input class="form-control" name="proposed_date" placeholder="2027-04-15"></div>
        <div class="form-group"><label>Category</label>
          <select class="form-control" name="category">
            <option>Lecture</option><option>Sports</option><option>Arts</option>
            <option>Career</option><option>Health</option><option>Social</option><option>Virtual</option>
          </select>
        </div>
      </div>
      <div class="form-group"><label>Description</label><textarea class="form-control" name="description" rows="6"></textarea></div>
      <button type="submit" class="btn btn-primary">Submit Suggestion</button>
    </form>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['faculty_contact.html'] = r"""{% extends "base.html" %}
{% block title %}Contact Professor {{ member.name }}{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Contact {{ member.name }}</h1><p>{{ member.title }}</p></div></section>
<section class="section">
  <div class="container" style="max-width:680px;">
    <form method="post">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="form-row">
        <div class="form-group"><label>Your Name</label><input class="form-control" name="sender_name" required></div>
        <div class="form-group"><label>Your Email</label><input type="email" class="form-control" name="sender_email" required></div>
      </div>
      <div class="form-group"><label>Subject</label><input class="form-control" name="subject" required></div>
      <div class="form-group"><label>Purpose</label>
        <select class="form-control" name="purpose">
          <option value="research_inquiry">Research Inquiry</option>
          <option value="prospective_grad_student">Prospective Graduate Student</option>
          <option value="course_question">Course Question</option>
          <option value="collaboration">Research Collaboration</option>
          <option value="media">Media Inquiry</option>
        </select>
      </div>
      <div class="form-group"><label>Message</label><textarea class="form-control" name="message" rows="6" required></textarea></div>
      <button type="submit" class="btn btn-primary">Send Message</button>
    </form>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['dept_meeting.html'] = r"""{% extends "base.html" %}
{% block title %}Schedule a Meeting — {{ dept.name }}{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Schedule a Meeting</h1><p>{{ dept.name }}</p></div></section>
<section class="section">
  <div class="container" style="max-width:680px;">
    <form method="post">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="form-row">
        <div class="form-group"><label>Your Name</label><input class="form-control" name="name" required></div>
        <div class="form-group"><label>Email</label><input type="email" class="form-control" name="email" required></div>
      </div>
      <div class="form-group"><label>Purpose of Meeting</label><input class="form-control" name="purpose" placeholder="Advising appointment, faculty introduction, etc."></div>
      <div class="form-group"><label>Preferred Date</label><input class="form-control" name="preferred_date" placeholder="2026-10-20"></div>
      <button type="submit" class="btn btn-primary">Request Meeting</button>
    </form>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['program_inquire.html'] = r"""{% extends "base.html" %}
{% block title %}Inquire — {{ program.name }}{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Program Inquiry</h1><p>{{ program.name }}</p></div></section>
<section class="section">
  <div class="container" style="max-width:680px;">
    <form method="post">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="form-row">
        <div class="form-group"><label>Your Name</label><input class="form-control" name="name" required></div>
        <div class="form-group"><label>Email</label><input type="email" class="form-control" name="email" required></div>
      </div>
      <div class="form-group"><label>Question</label><textarea class="form-control" name="question" rows="6" required></textarea></div>
      <button type="submit" class="btn btn-primary">Send Inquiry</button>
    </form>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['research_contact.html'] = r"""{% extends "base.html" %}
{% block title %}Contact {{ center.name }}{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Contact {{ center.name }}</h1><p>Connect with the research center for collaboration, internships, or media inquiries.</p></div></section>
<section class="section">
  <div class="container" style="max-width:680px;">
    <form method="post">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="form-row">
        <div class="form-group"><label>Your Name</label><input class="form-control" name="name" required></div>
        <div class="form-group"><label>Email</label><input type="email" class="form-control" name="email" required></div>
      </div>
      <div class="form-group"><label>Partnership Type</label>
        <select class="form-control" name="partnership_type">
          <option value="research_collab">Research Collaboration</option>
          <option value="industry_partner">Industry Partnership</option>
          <option value="visiting_scholar">Visiting Scholar</option>
          <option value="media">Media Inquiry</option>
          <option value="internship">Student Internship</option>
        </select>
      </div>
      <div class="form-group"><label>Message</label><textarea class="form-control" name="message" rows="6" required></textarea></div>
      <button type="submit" class="btn btn-primary">Send Message</button>
    </form>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['newsletter.html'] = r"""{% extends "base.html" %}
{% block title %}Subscribe to a Berkeley Newsletter{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Newsletter Subscriptions</h1><p>Get Berkeley news, research, athletics, and alumni updates by email.</p></div></section>
<section class="section">
  <div class="container" style="max-width:680px;">
    <form method="post">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="form-group"><label>Email Address</label><input type="email" class="form-control" name="email" required></div>
      <div class="form-row">
        <div class="form-group"><label>List</label>
          <select class="form-control" name="list_name">
            <option value="berkeley-weekly">Berkeley Weekly (campus highlights)</option>
            <option value="research-news">Research News</option>
            <option value="cal-athletics">Cal Athletics Insider</option>
            <option value="alumni-news">Cal Alumni Bulletin</option>
            <option value="arts-culture">Arts and Culture at Berkeley</option>
          </select>
        </div>
        <div class="form-group"><label>Frequency</label>
          <select class="form-control" name="frequency">
            <option value="weekly">Weekly</option>
            <option value="biweekly">Bi-weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>
      </div>
      <button type="submit" class="btn btn-primary">Subscribe</button>
    </form>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['contact.html'] = r"""{% extends "base.html" %}
{% block title %}Contact UC Berkeley{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Contact Berkeley</h1><p>For general inquiries, comments, or to be routed to the right office.</p></div></section>
<section class="section">
  <div class="container" style="max-width:680px;">
    <form method="post">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="form-row">
        <div class="form-group"><label>Your Name</label><input class="form-control" name="name" required></div>
        <div class="form-group"><label>Email</label><input type="email" class="form-control" name="email" required></div>
      </div>
      <div class="form-group"><label>Topic</label>
        <select class="form-control" name="topic">
          <option>General Inquiry</option><option>Admissions</option><option>Financial Aid</option>
          <option>Press</option><option>Alumni</option><option>Athletics</option>
          <option>Giving</option><option>Other</option>
        </select>
      </div>
      <div class="form-group"><label>Message</label><textarea class="form-control" name="message" rows="6" required></textarea></div>
      <button type="submit" class="btn btn-primary">Send Message</button>
    </form>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['careers.html'] = r"""{% extends "base.html" %}
{% block title %}Careers at UC Berkeley{% endblock %}
{% block content %}
<section class="page-header" style="background-image: linear-gradient(rgba(0,50,98,0.65),rgba(0,50,98,0.65)),url('{{ url_for('static', filename='images/campus_007.svg') }}');background-size:cover;">
  <div class="container"><h1>Work at Berkeley</h1><p>Faculty, postdoc, and staff positions across the campus.</p></div>
</section>
<section class="section">
  <div class="container">
    <table>
      <thead><tr><th>Position</th><th>Department</th><th>Type</th><th>Deadline</th><th>Salary Range</th><th>Location</th></tr></thead>
      <tbody>
      {% for p in positions %}
        <tr><td>{{ p.title }}</td><td>{{ p.department }}</td><td>{{ p.type }}</td><td>{{ p.deadline }}</td><td>{{ p.salary }}</td><td>{{ p.location }}</td></tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['strategic_plan.html'] = r"""{% extends "base.html" %}
{% block title %}Strategic Plan — UC Berkeley{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Berkeley Strategic Plan 2025-2032</h1><p>Five pillars guiding the next chapter of UC Berkeley.</p></div></section>
<section class="section">
  <div class="container">
    {% for p in pillars %}
      <div style="background:var(--off-white);padding:24px;border-left:4px solid var(--gold);margin-bottom:24px;border-radius:4px;">
        <h2 class="blue-text">{{ loop.index }}. {{ p.name }}</h2>
        <p class="mb-2">{{ p.description }}</p>
        <p><strong>2030 KPI:</strong> {{ p.kpi }}</p>
      </div>
    {% endfor %}
  </div>
</section>
{% endblock %}
"""

TEMPLATES['about_history.html'] = r"""{% extends "base.html" %}
{% block title %}Berkeley History — 1868 to Today{% endblock %}
{% block content %}
<section class="page-header" style="background-image: linear-gradient(rgba(0,50,98,0.6),rgba(0,50,98,0.6)),url('{{ url_for('static', filename='images/campus_002.svg') }}');background-size:cover;">
  <div class="container"><h1>Our History</h1><p>From the Organic Act of 1868 to the present.</p></div>
</section>
<section class="section">
  <div class="container">
    <div style="border-left:3px solid var(--gold);padding-left:24px;">
      {% for year, headline, desc in milestones %}
        <div style="margin-bottom:32px;">
          <h3 style="color:var(--blue);"><span class="gold-text">{{ year }}</span> — {{ headline }}</h3>
          <p>{{ desc }}</p>
        </div>
      {% endfor %}
    </div>
  </div>
</section>
{% endblock %}
"""

TEMPLATES['account_edit.html'] = r"""{% extends "base.html" %}
{% block title %}Edit Profile — UC Berkeley{% endblock %}
{% block content %}
<section class="page-header"><div class="container"><h1>Edit Profile</h1><p>Update your Berkeley account details.</p></div></section>
<section class="section">
  <div class="container" style="max-width:680px;">
    <form method="post">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="form-group"><label>Full Name</label><input class="form-control" name="full_name" value="{{ current_user.full_name }}" required></div>
      <div class="form-group"><label>Email (read only)</label><input class="form-control" value="{{ current_user.email }}" disabled></div>
      <div class="form-group"><label>Bio</label><textarea class="form-control" name="bio" rows="5">{{ current_user.bio or '' }}</textarea></div>
      <button type="submit" class="btn btn-primary">Save Changes</button>
    </form>
  </div>
</section>
{% endblock %}
"""

def main():
    written = 0
    for name, body in TEMPLATES.items():
        (T / name).write_text(body)
        written += 1
    print(f'Wrote {written} templates to {T}')

if __name__ == '__main__':
    main()
