#!/usr/bin/env python3
"""NBA deepen — routes + POST endpoints exposing _deepen_extend.py tables.

Imported once at the bottom of app.py. Defines lightweight SQLAlchemy models
for deepen tables (no FK enforcement; column types match the raw schema) and
registers 25+ new GET routes and 17+ new POST routes covering player career,
gamelog, splits, endorsements, news; team news/video/tickets/store; game
boxscore/play-by-play/shot-chart/four-factors; draft year landing,
prospects, lottery, picks; awards year, all-star, celebrity game, voting;
stats leaders by category, team-leaders by team+category; playoffs year,
bracket, finals; fantasy leagues/teams/lineup edit; account follows,
alerts, saved games, mock drafts, wishlist, ticket orders, video catalogue
and a video detail page.

Image utilisation: every new surface that has a natural image slot pulls
from player headshots, team logos, article images, or product images.
"""
import hashlib
from datetime import datetime, timedelta

from flask import (
    abort, flash, redirect, render_template, request, url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import text

# Imports defer to app to avoid circular: app is fully constructed by the
# time this module is imported at the bottom of app.py.
from app import (
    Article, CartItem, Favorite, Game, Order, OrderItem, Player, Product,
    Team, TicketRequest, User,
    MIRROR_REFERENCE_DATE, app, db, get_or_404, slugify, stat_value,
)


# ── helpers ────────────────────────────────────────────────────────────────

REF_DATE = MIRROR_REFERENCE_DATE


def _rows(sql, **params):
    res = db.session.execute(text(sql), params).mappings().all()
    return [dict(r) for r in res]


def _row(sql, **params):
    res = db.session.execute(text(sql), params).mappings().first()
    return dict(res) if res else None


def _exec(sql, **params):
    db.session.execute(text(sql), params)
    db.session.commit()


def _team(slug):
    return Team.query.filter_by(slug=slug).first()


def _player(slug):
    return Player.query.filter_by(slug=slug).first()


def _player_headshot(slug):
    p = _player(slug)
    return p.image if p else "/static/images/league/nba-logo.svg"


def _team_logo(slug):
    t = _team(slug)
    return t.logo if t else "/static/images/league/nba-logo.svg"


def _team_name(slug):
    t = _team(slug)
    return t.full_name if t else slug.replace("-", " ").title()


def _player_name(slug):
    p = _player(slug)
    return p.name if p else slug.replace("-", " ").title()


def _h(key, mod, offset=0):
    return offset + int.from_bytes(hashlib.md5(key.encode()).digest()[:4], "big") % mod


# ── PLAYER deeper surfaces ─────────────────────────────────────────────────

@app.route("/players/<slug>/career")
def player_career(slug):
    player = get_or_404(Player, slug)
    splits = _rows(
        "SELECT * FROM player_splits WHERE player_slug=:s ORDER BY id",
        s=slug,
    )
    endorsements = _rows(
        "SELECT * FROM player_endorsements WHERE player_slug=:s ORDER BY id",
        s=slug,
    )
    leaderboards = _rows(
        "SELECT category, rank, value FROM stat_leaderboards "
        "WHERE player_slug=:s ORDER BY category",
        s=slug,
    )
    return render_template(
        "player_career.html",
        player=player,
        splits=splits,
        endorsements=endorsements,
        leaderboards=leaderboards,
        stat_value=stat_value,
    )


@app.route("/players/<slug>/gamelog")
@app.route("/players/<slug>/gamelog/<int:year>")
def player_gamelog(slug, year=2026):
    player = get_or_404(Player, slug)
    logs = _rows(
        "SELECT * FROM player_gamelogs WHERE player_slug=:s "
        "ORDER BY game_date DESC",
        s=slug,
    )
    return render_template(
        "player_gamelog.html", player=player, logs=logs, year=year,
        team_name=_team_name,
    )


@app.route("/players/<slug>/splits")
def player_splits(slug):
    player = get_or_404(Player, slug)
    splits = _rows(
        "SELECT * FROM player_splits WHERE player_slug=:s ORDER BY split_kind",
        s=slug,
    )
    return render_template("player_splits.html", player=player, splits=splits)


@app.route("/players/<slug>/news")
def player_news_page(slug):
    player = get_or_404(Player, slug)
    items = _rows(
        "SELECT * FROM player_news_items WHERE player_slug=:s "
        "ORDER BY published_at DESC",
        s=slug,
    )
    return render_template("player_news.html", player=player, items=items)


@app.route("/players/<slug>/shoes")
def player_shoes(slug):
    player = get_or_404(Player, slug)
    endorsements = _rows(
        "SELECT * FROM player_endorsements WHERE player_slug=:s ORDER BY id",
        s=slug,
    )
    return render_template(
        "player_shoes.html", player=player, endorsements=endorsements,
    )


# ── TEAM deeper surfaces ───────────────────────────────────────────────────

@app.route("/teams/<slug>/news")
def team_news(slug):
    team = get_or_404(Team, slug)
    items = _rows(
        "SELECT * FROM team_news_items WHERE team_slug=:s "
        "ORDER BY published_at DESC",
        s=slug,
    )
    return render_template("team_news.html", team=team, items=items)


@app.route("/teams/<slug>/video")
def team_video(slug):
    team = get_or_404(Team, slug)
    team_clips = _rows(
        "SELECT * FROM videos WHERE team_slug=:s ORDER BY published_at DESC",
        s=slug,
    )
    player_clips = _rows(
        "SELECT v.* FROM videos v JOIN players p ON v.player_slug=p.slug "
        "WHERE p.team_id=:tid ORDER BY v.published_at DESC LIMIT 40",
        tid=team.id,
    )
    return render_template(
        "team_video.html", team=team,
        team_clips=team_clips, player_clips=player_clips,
    )


@app.route("/teams/<slug>/tickets")
def team_tickets(slug):
    team = get_or_404(Team, slug)
    games = Game.query.filter(
        ((Game.home_team_id == team.id) | (Game.away_team_id == team.id))
        & (Game.status == "Scheduled")
    ).order_by(Game.game_date).all()
    return render_template(
        "team_tickets.html", team=team, games=games,
    )


@app.route("/teams/<slug>/store")
def team_store(slug):
    team = get_or_404(Team, slug)
    products = Product.query.filter_by(team_slug=slug).all()
    return render_template("team_store.html", team=team, products=products)


@app.route("/teams/<slug>/stats/advanced")
def team_stats_advanced(slug):
    team = get_or_404(Team, slug)
    ff = _rows(
        "SELECT gf.*, g.id AS gid, ht.slug AS home_slug, at.slug AS away_slug "
        "FROM game_four_factors gf JOIN games g ON gf.game_id=g.id "
        "JOIN teams ht ON ht.id=g.home_team_id "
        "JOIN teams at ON at.id=g.away_team_id "
        "WHERE gf.team_slug=:s ORDER BY g.game_date DESC LIMIT 25",
        s=slug,
    )
    return render_template("team_stats_advanced.html", team=team, ff=ff)


# ── GAME deeper surfaces ───────────────────────────────────────────────────

@app.route("/games/<int:game_id>/box")
def game_box(game_id):
    game = db.session.get(Game, game_id) or abort(404)
    rows = _rows(
        "SELECT * FROM game_boxscores WHERE game_id=:g ORDER BY id",
        g=game_id,
    )
    return render_template(
        "game_box.html", game=game, rows=rows, team_name=_team_name,
        team_logo=_team_logo,
    )


@app.route("/games/<int:game_id>/play-by-play")
def game_pbp(game_id):
    game = db.session.get(Game, game_id) or abort(404)
    events = _rows(
        "SELECT * FROM game_playbyplay WHERE game_id=:g ORDER BY id",
        g=game_id,
    )
    return render_template(
        "game_pbp.html", game=game, events=events, team_name=_team_name,
        team_logo=_team_logo,
    )


@app.route("/games/<int:game_id>/shot-chart")
def game_shotchart(game_id):
    game = db.session.get(Game, game_id) or abort(404)
    shots = _rows(
        "SELECT * FROM game_shots WHERE game_id=:g ORDER BY id",
        g=game_id,
    )
    return render_template(
        "game_shotchart.html", game=game, shots=shots, team_name=_team_name,
        team_logo=_team_logo,
    )


@app.route("/games/<int:game_id>/four-factors")
def game_four_factors(game_id):
    game = db.session.get(Game, game_id) or abort(404)
    rows = _rows(
        "SELECT * FROM game_four_factors WHERE game_id=:g ORDER BY id",
        g=game_id,
    )
    return render_template(
        "game_four_factors.html", game=game, rows=rows, team_name=_team_name,
        team_logo=_team_logo,
    )


# ── DRAFT, AWARDS, ALL-STAR ────────────────────────────────────────────────

@app.route("/draft/<int:year>")
def draft_year(year):
    prospects = _rows(
        "SELECT * FROM draft_prospects WHERE year=:y ORDER BY mock_rank",
        y=year,
    )
    picks = _rows(
        "SELECT * FROM draft_picks WHERE year=:y ORDER BY round, pick_no",
        y=year,
    )
    lottery = _rows(
        "SELECT * FROM lottery_results WHERE year=:y ORDER BY seed",
        y=year,
    )
    return render_template(
        "draft_year.html", year=year,
        prospects=prospects, picks=picks, lottery=lottery,
        team_name=_team_name, team_logo=_team_logo,
    )


@app.route("/draft/<int:year>/prospects")
def draft_prospects(year):
    prospects = _rows(
        "SELECT * FROM draft_prospects WHERE year=:y ORDER BY mock_rank",
        y=year,
    )
    return render_template(
        "draft_prospects.html", year=year, prospects=prospects,
    )


@app.route("/draft/<int:year>/lottery")
def draft_lottery(year):
    lottery = _rows(
        "SELECT * FROM lottery_results WHERE year=:y ORDER BY seed",
        y=year,
    )
    return render_template(
        "draft_lottery.html", year=year, lottery=lottery,
        team_name=_team_name, team_logo=_team_logo,
    )


@app.route("/draft/<int:year>/picks")
def draft_picks(year):
    picks = _rows(
        "SELECT dp.*, p.name AS prospect_name FROM draft_picks dp "
        "LEFT JOIN draft_prospects p ON p.slug=dp.prospect_slug "
        "WHERE dp.year=:y ORDER BY dp.round, dp.pick_no",
        y=year,
    )
    return render_template(
        "draft_picks.html", year=year, picks=picks,
        team_name=_team_name, team_logo=_team_logo,
    )


@app.route("/awards")
def awards_index():
    years = [r["year"] for r in _rows(
        "SELECT DISTINCT year FROM awards ORDER BY year DESC"
    )]
    return render_template("awards_index.html", years=years)


@app.route("/awards/<int:year>")
def awards_year(year):
    rows = _rows(
        "SELECT * FROM awards WHERE year=:y ORDER BY slug",
        y=year,
    )
    return render_template(
        "awards_year.html", year=year, awards=rows,
        team_name=_team_name, team_logo=_team_logo,
        player_name=_player_name, player_headshot=_player_headshot,
    )


@app.route("/all-star")
def allstar_index():
    return redirect(url_for("allstar_year", year=2026))


@app.route("/all-star/<int:year>")
def allstar_year(year):
    east_votes = _rows(
        "SELECT player_slug, COUNT(*) AS votes FROM allstar_votes "
        "WHERE year=:y AND conference='East' GROUP BY player_slug "
        "ORDER BY votes DESC",
        y=year,
    )
    west_votes = _rows(
        "SELECT player_slug, COUNT(*) AS votes FROM allstar_votes "
        "WHERE year=:y AND conference='West' GROUP BY player_slug "
        "ORDER BY votes DESC",
        y=year,
    )
    celebs = _rows(
        "SELECT * FROM celebrity_allstar WHERE year=:y ORDER BY id",
        y=year,
    )
    return render_template(
        "allstar_year.html", year=year, east=east_votes, west=west_votes,
        celebs=celebs, player_name=_player_name, player_headshot=_player_headshot,
    )


@app.route("/all-star/<int:year>/voting")
def allstar_voting(year):
    players = Player.query.order_by(Player.ppg.desc()).limit(40).all()
    east = [p for p in players if p.team and p.team.conference == "East"][:20]
    west = [p for p in players if p.team and p.team.conference == "West"][:20]
    return render_template(
        "allstar_voting.html", year=year, east=east, west=west,
    )


@app.route("/all-star/<int:year>/celebrity-game")
def allstar_celebrity_game(year):
    celebs = _rows(
        "SELECT * FROM celebrity_allstar WHERE year=:y ORDER BY id",
        y=year,
    )
    return render_template(
        "allstar_celebrity.html", year=year, celebs=celebs,
    )


# ── STATS leaders ──────────────────────────────────────────────────────────

@app.route("/stats/leaders/<category>")
def stats_leaders_category(category):
    if category not in {"ppg", "rpg", "apg", "spg", "bpg", "fg_pct", "three_pct"}:
        abort(404)
    rows = _rows(
        "SELECT rank, player_slug, team_slug, value FROM stat_leaderboards "
        "WHERE category=:c ORDER BY rank",
        c=category,
    )
    return render_template(
        "stats_leaders_category.html", category=category, rows=rows,
        player_name=_player_name, player_headshot=_player_headshot,
    )


@app.route("/stats/team-leaders/<team_slug>/<category>")
def stats_team_leaders(team_slug, category):
    team = get_or_404(Team, team_slug)
    if category not in {"ppg", "rpg", "apg", "spg", "bpg", "fg_pct", "three_pct"}:
        abort(404)
    players = Player.query.filter_by(team_id=team.id).all()
    field_map = {"ppg": "ppg", "rpg": "rpg", "apg": "apg",
                 "spg": "spg", "bpg": "bpg",
                 "fg_pct": "fg_pct", "three_pct": "three_pct"}
    field = field_map[category]
    players_sorted = sorted(players, key=lambda p: -getattr(p, field))
    return render_template(
        "stats_team_leaders.html", team=team, category=category,
        players=players_sorted, stat_value=stat_value,
    )


# ── PLAYOFFS year/bracket/finals ───────────────────────────────────────────

@app.route("/playoffs/<int:year>")
def playoffs_year(year):
    teams = Team.query.all()
    return render_template(
        "playoffs_year.html", year=year, teams=teams,
    )


@app.route("/playoffs/<int:year>/bracket")
def playoffs_bracket(year):
    teams = Team.query.all()
    return render_template(
        "playoffs_bracket.html", year=year, teams=teams,
    )


@app.route("/playoffs/<int:year>/finals")
def playoffs_finals(year):
    teams = Team.query.all()
    return render_template(
        "playoffs_finals.html", year=year, teams=teams,
    )


# ── VIDEO catalogue ────────────────────────────────────────────────────────

@app.route("/video")
def video_index():
    kind = request.args.get("kind", "")
    sql = "SELECT * FROM videos"
    params = {}
    if kind:
        sql += " WHERE kind=:k"
        params["k"] = kind
    sql += " ORDER BY views DESC LIMIT 80"
    items = _rows(sql, **params)
    kinds = sorted({r["kind"] for r in _rows("SELECT DISTINCT kind FROM videos")})
    return render_template(
        "video_index.html", videos=items, kinds=kinds, kind=kind,
    )


@app.route("/video/<slug>")
def video_detail(slug):
    video = _row("SELECT * FROM videos WHERE slug=:s", s=slug)
    if not video:
        abort(404)
    related = _rows(
        "SELECT * FROM videos WHERE kind=:k AND slug!=:s ORDER BY views DESC LIMIT 8",
        k=video["kind"], s=slug,
    )
    return render_template("video_detail.html", video=video, related=related)


# ── FANTASY ────────────────────────────────────────────────────────────────

@app.route("/fantasy/leagues")
def fantasy_leagues():
    leagues = _rows("SELECT * FROM fantasy_leagues ORDER BY id")
    return render_template("fantasy_leagues.html", leagues=leagues)


@app.route("/fantasy/league/<slug>")
def fantasy_league_detail(slug):
    league = _row("SELECT * FROM fantasy_leagues WHERE slug=:s", s=slug)
    if not league:
        abort(404)
    teams = _rows(
        "SELECT * FROM fantasy_teams WHERE league_slug=:s "
        "ORDER BY pts_for DESC",
        s=slug,
    )
    return render_template(
        "fantasy_league_detail.html", league=league, teams=teams,
    )


@app.route("/fantasy/team/<slug>")
def fantasy_team_detail(slug):
    team = _row("SELECT * FROM fantasy_teams WHERE slug=:s", s=slug)
    if not team:
        abort(404)
    roster = _rows(
        "SELECT fr.*, p.name AS player_name, p.position AS player_pos, "
        "p.image AS player_image, (t.city || ' ' || t.name) AS team_name "
        "FROM fantasy_rosters fr LEFT JOIN players p ON p.slug=fr.player_slug "
        "LEFT JOIN teams t ON t.id=p.team_id WHERE fr.team_slug=:s ORDER BY fr.id",
        s=slug,
    )
    return render_template(
        "fantasy_team_detail.html", team=team, roster=roster,
    )


@app.route("/fantasy/team/<slug>/lineup", methods=["GET", "POST"])
@login_required
def fantasy_lineup_edit(slug):
    team = _row("SELECT * FROM fantasy_teams WHERE slug=:s", s=slug)
    if not team:
        abort(404)
    if request.method == "POST":
        for key, val in request.form.items():
            if key.startswith("locked_"):
                lid = int(key.split("_", 1)[1])
                locked = 1 if val in {"1", "on", "true"} else 0
                _exec(
                    "UPDATE fantasy_lineups SET locked=:l, submitted_at=:t "
                    "WHERE id=:i",
                    l=locked, t=REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000"),
                    i=lid,
                )
        flash("Fantasy lineup saved.", "success")
        return redirect(url_for("fantasy_team_detail", slug=slug))
    lineups = _rows(
        "SELECT fl.*, p.name AS player_name, p.position AS player_pos, "
        "p.image AS player_image FROM fantasy_lineups fl "
        "LEFT JOIN players p ON p.slug=fl.player_slug "
        "WHERE fl.team_slug=:s ORDER BY fl.id",
        s=slug,
    )
    return render_template(
        "fantasy_lineup.html", team=team, lineups=lineups,
    )


# ── MY ACCOUNT extras ──────────────────────────────────────────────────────

@app.route("/account/follows")
@login_required
def my_follows():
    follows = _rows(
        "SELECT * FROM follows WHERE user_id=:u ORDER BY created_at DESC",
        u=current_user.id,
    )
    enriched = []
    for f in follows:
        ts = f["target_slug"]
        if f["kind"] == "team":
            t = _team(ts)
            enriched.append({**f, "label": t.full_name if t else ts,
                             "image": t.logo if t else "/static/images/league/nba-logo.svg",
                             "link": url_for("team_detail", slug=ts) if t else "#"})
        else:
            p = _player(ts)
            enriched.append({**f, "label": p.name if p else ts,
                             "image": p.image if p else "/static/images/league/nba-logo.svg",
                             "link": url_for("player_detail", slug=ts) if p else "#"})
    return render_template("my_follows.html", follows=enriched)


@app.route("/account/alerts")
@login_required
def my_alerts():
    alerts = _rows(
        "SELECT * FROM alerts WHERE user_id=:u ORDER BY id",
        u=current_user.id,
    )
    return render_template("my_alerts.html", alerts=alerts)


@app.route("/account/saved-games")
@login_required
def my_saved_games():
    saved = _rows(
        "SELECT sg.*, g.game_date, g.status, g.home_score, g.away_score, "
        "ht.slug AS home_slug, ht.name AS home_name, ht.logo AS home_logo, "
        "at.slug AS away_slug, at.name AS away_name, at.logo AS away_logo "
        "FROM saved_games sg JOIN games g ON sg.game_id=g.id "
        "JOIN teams ht ON ht.id=g.home_team_id "
        "JOIN teams at ON at.id=g.away_team_id "
        "WHERE sg.user_id=:u ORDER BY g.game_date",
        u=current_user.id,
    )
    return render_template("my_saved_games.html", saved=saved)


@app.route("/account/mock-drafts")
@login_required
def my_mock_drafts():
    rows = _rows(
        "SELECT md.*, dp.name AS prospect_name, dp.image AS prospect_image "
        "FROM mock_drafts md "
        "LEFT JOIN draft_prospects dp ON dp.slug=md.prospect_slug "
        "WHERE md.user_id=:u ORDER BY md.year DESC, md.pick_no",
        u=current_user.id,
    )
    return render_template("my_mock_drafts.html", rows=rows)


@app.route("/account/wishlist")
@login_required
def my_wishlist():
    rows = _rows(
        "SELECT sw.*, p.name AS product_name, p.image AS product_image, "
        "p.price AS product_price FROM store_wishlist sw "
        "LEFT JOIN products p ON p.slug=sw.product_slug "
        "WHERE sw.user_id=:u ORDER BY sw.id",
        u=current_user.id,
    )
    return render_template("my_wishlist.html", rows=rows)


@app.route("/account/ticket-orders")
@login_required
def my_ticket_orders():
    rows = _rows(
        "SELECT to_.*, g.game_date, ht.slug AS home_slug, ht.name AS home_name, "
        "ht.logo AS home_logo, at.slug AS away_slug, at.name AS away_name, "
        "at.logo AS away_logo "
        "FROM ticket_orders to_ JOIN games g ON to_.game_id=g.id "
        "JOIN teams ht ON ht.id=g.home_team_id "
        "JOIN teams at ON at.id=g.away_team_id "
        "WHERE to_.user_id=:u ORDER BY g.game_date",
        u=current_user.id,
    )
    return render_template("my_ticket_orders.html", rows=rows)


# ── POST actions ───────────────────────────────────────────────────────────

@app.route("/follow/team/<slug>", methods=["POST"])
@login_required
def follow_team(slug):
    team = get_or_404(Team, slug)
    existing = _row(
        "SELECT id FROM follows WHERE user_id=:u AND kind='team' AND target_slug=:s",
        u=current_user.id, s=slug,
    )
    if existing:
        _exec("DELETE FROM follows WHERE id=:i", i=existing["id"])
        flash("Unfollowed team.", "info")
    else:
        _exec(
            "INSERT INTO follows (user_id, kind, target_slug, target_id, "
            "alert_on, created_at) VALUES (:u, 'team', :s, :tid, 1, :t)",
            u=current_user.id, s=slug, tid=team.id,
            t=REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000"),
        )
        flash(f"Following {team.full_name}.", "success")
    return redirect(request.referrer or url_for("team_detail", slug=slug))


@app.route("/follow/player/<slug>", methods=["POST"])
@login_required
def follow_player(slug):
    player = get_or_404(Player, slug)
    existing = _row(
        "SELECT id FROM follows WHERE user_id=:u AND kind='player' AND target_slug=:s",
        u=current_user.id, s=slug,
    )
    if existing:
        _exec("DELETE FROM follows WHERE id=:i", i=existing["id"])
        flash("Unfollowed player.", "info")
    else:
        _exec(
            "INSERT INTO follows (user_id, kind, target_slug, target_id, "
            "alert_on, created_at) VALUES (:u, 'player', :s, :pid, 1, :t)",
            u=current_user.id, s=slug, pid=player.id,
            t=REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000"),
        )
        flash(f"Following {player.name}.", "success")
    return redirect(request.referrer or url_for("player_detail", slug=slug))


@app.route("/alerts/<int:alert_id>/toggle", methods=["POST"])
@login_required
def alert_toggle(alert_id):
    row = _row("SELECT * FROM alerts WHERE id=:i AND user_id=:u",
               i=alert_id, u=current_user.id)
    if not row:
        abort(404)
    _exec("UPDATE alerts SET active=:a WHERE id=:i",
          a=0 if row["active"] else 1, i=alert_id)
    flash("Alert updated.", "success")
    return redirect(url_for("my_alerts"))


@app.route("/alerts/add", methods=["POST"])
@login_required
def alert_add():
    kind = request.form.get("kind", "tipoff")
    target_slug = request.form.get("target_slug", "")
    label = request.form.get("label", "").strip() or f"Alert: {target_slug}"
    _exec(
        "INSERT INTO alerts (user_id, kind, target_slug, label, active, created_at) "
        "VALUES (:u, :k, :s, :l, 1, :t)",
        u=current_user.id, k=kind, s=target_slug, l=label,
        t=REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000"),
    )
    flash("Alert created.", "success")
    return redirect(url_for("my_alerts"))


@app.route("/all-star/<int:year>/vote", methods=["POST"])
@login_required
def allstar_vote(year):
    conference = request.form.get("conference", "East")
    position = request.form.get("position", "F")
    player_slug = request.form.get("player_slug", "")
    if not player_slug:
        flash("Choose a player to vote.", "error")
        return redirect(url_for("allstar_voting", year=year))
    _exec(
        "INSERT INTO allstar_votes (user_id, year, conference, position, "
        "player_slug, created_at) VALUES (:u, :y, :c, :p, :s, :t)",
        u=current_user.id, y=year, c=conference, p=position, s=player_slug,
        t=REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000"),
    )
    flash("All-Star vote submitted.", "success")
    return redirect(url_for("allstar_year", year=year))


@app.route("/awards/<int:year>/vote", methods=["POST"])
@login_required
def award_vote(year):
    award_slug = request.form.get("award_slug", "mvp")
    first = request.form.get("first_slug", "")
    second = request.form.get("second_slug", "")
    third = request.form.get("third_slug", "")
    _exec(
        "INSERT INTO award_votes (user_id, year, award_slug, first_slug, "
        "second_slug, third_slug, created_at) "
        "VALUES (:u, :y, :a, :f, :s, :th, :t)",
        u=current_user.id, y=year, a=award_slug, f=first, s=second, th=third,
        t=REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000"),
    )
    flash("Awards ballot submitted.", "success")
    return redirect(url_for("awards_year", year=year))


@app.route("/draft/<int:year>/mock", methods=["POST"])
@login_required
def mock_draft_submit(year):
    for k, v in request.form.items():
        if k.startswith("pick_") and v:
            try:
                pick_no = int(k.split("_", 1)[1])
            except ValueError:
                continue
            _exec(
                "INSERT INTO mock_drafts (user_id, year, pick_no, prospect_slug, "
                "submitted_at) VALUES (:u, :y, :n, :s, :t)",
                u=current_user.id, y=year, n=pick_no, s=v,
                t=REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000"),
            )
    flash("Mock draft submitted.", "success")
    return redirect(url_for("my_mock_drafts"))


@app.route("/tickets/buy", methods=["POST"])
@login_required
def ticket_buy():
    game_id = int(request.form.get("game_id", "0") or 0)
    game = db.session.get(Game, game_id)
    if not game:
        abort(404)
    section = request.form.get("section", "Lower Bowl")
    row_label = request.form.get("row_label", "1")
    seats = max(1, int(request.form.get("seats", "2")))
    price_each = float(request.form.get("price_each", str(game.ticket_price)))
    total = round(price_each * seats + 8.5, 2)
    conf_no = f"NBA-TIX-{current_user.id:02d}{game_id:03d}{_h(f'tix{current_user.id}{game_id}', 999):03d}"
    _exec(
        "INSERT INTO ticket_orders (user_id, game_id, section, row_label, seats, "
        "price_each, total, confirmation, created_at) "
        "VALUES (:u, :g, :s, :r, :se, :p, :t, :c, :ts)",
        u=current_user.id, g=game_id, s=section, r=row_label, se=seats,
        p=price_each, t=total, c=conf_no,
        ts=REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000"),
    )
    flash(f"Tickets confirmed — {conf_no}.", "success")
    return redirect(url_for("my_ticket_orders"))


@app.route("/games/<int:game_id>/save", methods=["POST"])
@login_required
def save_game(game_id):
    game = db.session.get(Game, game_id) or abort(404)
    note = request.form.get("note", "").strip() or "Saved for later"
    _exec(
        "INSERT INTO saved_games (user_id, game_id, note, created_at) "
        "VALUES (:u, :g, :n, :t)",
        u=current_user.id, g=game.id, n=note,
        t=REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000"),
    )
    flash("Game saved.", "success")
    return redirect(request.referrer or url_for("my_saved_games"))


@app.route("/wishlist/add/<slug>", methods=["POST"])
@login_required
def wishlist_add(slug):
    product = get_or_404(Product, slug)
    existing = _row(
        "SELECT id FROM store_wishlist WHERE user_id=:u AND product_slug=:s",
        u=current_user.id, s=slug,
    )
    if existing:
        flash("Already on your wishlist.", "info")
    else:
        note = request.form.get("note", "").strip()
        _exec(
            "INSERT INTO store_wishlist (user_id, product_slug, note, created_at) "
            "VALUES (:u, :s, :n, :t)",
            u=current_user.id, s=slug, n=note,
            t=REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000"),
        )
        flash(f"Added {product.name} to your wishlist.", "success")
    return redirect(request.referrer or url_for("my_wishlist"))


@app.route("/wishlist/remove/<slug>", methods=["POST"])
@login_required
def wishlist_remove(slug):
    _exec(
        "DELETE FROM store_wishlist WHERE user_id=:u AND product_slug=:s",
        u=current_user.id, s=slug,
    )
    flash("Removed from wishlist.", "info")
    return redirect(url_for("my_wishlist"))


@app.route("/articles/<slug>/comment", methods=["POST"])
@login_required
def article_comment(slug):
    body = request.form.get("body", "").strip()
    if body:
        _exec(
            "INSERT INTO article_comments (user_id, article_slug, body, upvotes, "
            "created_at) VALUES (:u, :s, :b, 0, :t)",
            u=current_user.id, s=slug, b=body,
            t=REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000"),
        )
        flash("Comment posted.", "success")
    return redirect(url_for("article_detail", slug=slug))


@app.route("/video/<slug>/like", methods=["POST"])
@login_required
def video_like(slug):
    existing = _row(
        "SELECT id FROM video_likes WHERE user_id=:u AND video_slug=:s",
        u=current_user.id, s=slug,
    )
    if existing:
        _exec("DELETE FROM video_likes WHERE id=:i", i=existing["id"])
        flash("Removed like.", "info")
    else:
        _exec(
            "INSERT INTO video_likes (user_id, video_slug, created_at) "
            "VALUES (:u, :s, :t)",
            u=current_user.id, s=slug,
            t=REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000"),
        )
        flash("Liked highlight.", "success")
    return redirect(url_for("video_detail", slug=slug))


@app.route("/video/<slug>/share", methods=["POST"])
@login_required
def video_share(slug):
    channel = request.form.get("channel", "email")
    recipient = request.form.get("recipient", "").strip()
    note = request.form.get("note", "").strip()
    _exec(
        "INSERT INTO highlight_shares (user_id, video_slug, channel, recipient, "
        "note, created_at) VALUES (:u, :s, :c, :r, :n, :t)",
        u=current_user.id, s=slug, c=channel, r=recipient, n=note,
        t=REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000"),
    )
    flash(f"Highlight shared via {channel}.", "success")
    return redirect(url_for("video_detail", slug=slug))


@app.route("/account/preferences", methods=["GET", "POST"])
@login_required
def preferences():
    if request.method == "POST":
        hide = 1 if request.form.get("hide_scores") in {"1", "on", "true"} else 0
        tz = request.form.get("timezone", "America/Los_Angeles")
        email_news = 1 if request.form.get("email_news") in {"1", "on", "true"} else 0
        push = 1 if request.form.get("push_alerts") in {"1", "on", "true"} else 0
        quality = request.form.get("league_pass_quality", "Auto")
        existing = _row(
            "SELECT id FROM user_preferences WHERE user_id=:u",
            u=current_user.id,
        )
        if existing:
            _exec(
                "UPDATE user_preferences SET hide_scores=:h, timezone=:tz, "
                "email_news=:e, push_alerts=:p, league_pass_quality=:q, "
                "updated_at=:t WHERE user_id=:u",
                h=hide, tz=tz, e=email_news, p=push, q=quality,
                t=REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000"),
                u=current_user.id,
            )
        else:
            _exec(
                "INSERT INTO user_preferences (user_id, hide_scores, timezone, "
                "email_news, push_alerts, league_pass_quality, updated_at) "
                "VALUES (:u, :h, :tz, :e, :p, :q, :t)",
                u=current_user.id, h=hide, tz=tz, e=email_news, p=push, q=quality,
                t=REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000"),
            )
        flash("Preferences updated.", "success")
        return redirect(url_for("preferences"))
    prefs = _row(
        "SELECT * FROM user_preferences WHERE user_id=:u",
        u=current_user.id,
    ) or {"hide_scores": 0, "timezone": "America/Los_Angeles",
          "email_news": 1, "push_alerts": 1, "league_pass_quality": "Auto"}
    return render_template("preferences.html", prefs=prefs)


@app.route("/account/ticket-orders/<int:order_id>/cancel", methods=["POST"])
@login_required
def ticket_cancel(order_id):
    row = _row(
        "SELECT * FROM ticket_orders WHERE id=:i AND user_id=:u",
        i=order_id, u=current_user.id,
    )
    if not row:
        abort(404)
    _exec("DELETE FROM ticket_orders WHERE id=:i", i=order_id)
    flash(f"Ticket order {row['confirmation']} cancelled.", "info")
    return redirect(url_for("my_ticket_orders"))
