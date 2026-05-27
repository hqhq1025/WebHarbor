"""
Rotten Tomatoes mirror — extension models + routes for the deepening pass.

Defines new SQLAlchemy models that share the `db` from `app` plus all new
routes (TV shows, critics, lists, news, podcasts, sweepstakes, polls, awards,
photos, want-to-see / watched, review interactions, comments). Imported by
app.py before `db.create_all()` so SQLAlchemy picks up every new table.
"""
from datetime import datetime, timedelta

from flask import (render_template, request, redirect, url_for, flash, jsonify,
                   abort)
from flask_login import login_required, current_user
from sqlalchemy import func


def register(app, db, base_models):
    """Bind new models + routes onto the existing app/db."""
    User = base_models["User"]
    Movie = base_models["Movie"]
    Person = base_models["Person"]
    AudienceReview = base_models["AudienceReview"]
    CriticReview = base_models["CriticReview"]
    Genre = base_models["Genre"]
    MovieCast = base_models["MovieCast"]

    # ─── new models ─────────────────────────────────────────

    class TVShow(db.Model):
        __tablename__ = "tv_shows"
        id = db.Column(db.Integer, primary_key=True)
        slug = db.Column(db.String(150), unique=True, index=True, nullable=False)
        title = db.Column(db.String(200), nullable=False, index=True)
        year_start = db.Column(db.Integer, default=0)
        year_end = db.Column(db.Integer, default=0)
        network = db.Column(db.String(80), default="")
        tomatometer = db.Column(db.Integer, default=0)
        audience_score = db.Column(db.Integer, default=0)
        certified_fresh = db.Column(db.Boolean, default=False)
        synopsis = db.Column(db.Text, default="")
        poster = db.Column(db.String(300), default="")
        genre_text = db.Column(db.String(200), default="")
        seasons = db.relationship("Season", backref="show", lazy=True,
                                  cascade="all, delete-orphan",
                                  order_by="Season.number")

    class Season(db.Model):
        __tablename__ = "tv_seasons"
        id = db.Column(db.Integer, primary_key=True)
        tv_id = db.Column(db.Integer, db.ForeignKey("tv_shows.id"), nullable=False)
        number = db.Column(db.Integer, nullable=False)
        title = db.Column(db.String(120), default="")
        year = db.Column(db.Integer, default=0)
        synopsis = db.Column(db.Text, default="")
        episode_count = db.Column(db.Integer, default=0)
        episodes = db.relationship("Episode", backref="season", lazy=True,
                                   cascade="all, delete-orphan",
                                   order_by="Episode.number")

    class Episode(db.Model):
        __tablename__ = "tv_episodes"
        id = db.Column(db.Integer, primary_key=True)
        season_id = db.Column(db.Integer, db.ForeignKey("tv_seasons.id"), nullable=False)
        number = db.Column(db.Integer, nullable=False)
        title = db.Column(db.String(200), default="")
        synopsis = db.Column(db.Text, default="")
        air_date = db.Column(db.String(20), default="")
        tomatometer = db.Column(db.Integer, default=0)

    class Critic(db.Model):
        __tablename__ = "critics"
        id = db.Column(db.Integer, primary_key=True)
        slug = db.Column(db.String(150), unique=True, index=True, nullable=False)
        name = db.Column(db.String(150), nullable=False, index=True)
        publication = db.Column(db.String(150), default="")
        bio = db.Column(db.Text, default="")
        photo = db.Column(db.String(300), default="")
        top_critic = db.Column(db.Boolean, default=False)

    class CriticFollow(db.Model):
        __tablename__ = "critic_follows"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
        critic_id = db.Column(db.Integer, db.ForeignKey("critics.id"), nullable=False)
        __table_args__ = (db.UniqueConstraint("user_id", "critic_id", name="uq_user_critic"),)

    class MovieList(db.Model):
        __tablename__ = "movie_lists"
        id = db.Column(db.Integer, primary_key=True)
        slug = db.Column(db.String(150), unique=True, index=True, nullable=False)
        title = db.Column(db.String(200), nullable=False)
        description = db.Column(db.Text, default="")
        owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
        is_public = db.Column(db.Boolean, default=True)
        tag = db.Column(db.String(50), default="")
        created_at = db.Column(db.DateTime)
        items = db.relationship("MovieListItem", backref="list", lazy=True,
                                cascade="all, delete-orphan",
                                order_by="MovieListItem.order")

    class MovieListItem(db.Model):
        __tablename__ = "movie_list_items"
        id = db.Column(db.Integer, primary_key=True)
        list_id = db.Column(db.Integer, db.ForeignKey("movie_lists.id"), nullable=False)
        movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), nullable=False)
        order = db.Column(db.Integer, default=0)
        __table_args__ = (db.UniqueConstraint("list_id", "movie_id", name="uq_list_movie"),)
        movie = db.relationship("Movie", lazy="joined")

    class NewsArticle(db.Model):
        __tablename__ = "news_articles"
        id = db.Column(db.Integer, primary_key=True)
        slug = db.Column(db.String(200), unique=True, index=True, nullable=False)
        title = db.Column(db.String(300), nullable=False)
        summary = db.Column(db.Text, default="")
        body = db.Column(db.Text, default="")
        author = db.Column(db.String(120), default="")
        author_slug = db.Column(db.String(120), default="")
        image = db.Column(db.String(300), default="")
        category = db.Column(db.String(60), default="Movies", index=True)
        published_at = db.Column(db.DateTime)
        tag_movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), nullable=True)

    class NewsComment(db.Model):
        __tablename__ = "news_comments"
        id = db.Column(db.Integer, primary_key=True)
        news_id = db.Column(db.Integer, db.ForeignKey("news_articles.id"), nullable=False)
        user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
        text = db.Column(db.Text, default="")
        created_at = db.Column(db.DateTime)

    class Podcast(db.Model):
        __tablename__ = "podcasts"
        id = db.Column(db.Integer, primary_key=True)
        slug = db.Column(db.String(150), unique=True, index=True, nullable=False)
        title = db.Column(db.String(200), nullable=False)
        host = db.Column(db.String(200), default="")
        description = db.Column(db.Text, default="")
        image = db.Column(db.String(300), default="")
        episodes = db.relationship("PodcastEpisode", backref="podcast", lazy=True,
                                   cascade="all, delete-orphan",
                                   order_by="PodcastEpisode.number.desc()")

    class PodcastEpisode(db.Model):
        __tablename__ = "podcast_episodes"
        id = db.Column(db.Integer, primary_key=True)
        podcast_id = db.Column(db.Integer, db.ForeignKey("podcasts.id"), nullable=False)
        number = db.Column(db.Integer, default=0)
        title = db.Column(db.String(300), default="")
        description = db.Column(db.Text, default="")
        duration_min = db.Column(db.Integer, default=0)
        published_at = db.Column(db.DateTime)

    class PodcastSubscribe(db.Model):
        __tablename__ = "podcast_subscribes"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
        podcast_id = db.Column(db.Integer, db.ForeignKey("podcasts.id"), nullable=False)
        __table_args__ = (db.UniqueConstraint("user_id", "podcast_id", name="uq_user_podcast"),)

    class Sweepstakes(db.Model):
        __tablename__ = "sweepstakes"
        id = db.Column(db.Integer, primary_key=True)
        slug = db.Column(db.String(150), unique=True, index=True, nullable=False)
        title = db.Column(db.String(300), nullable=False)
        prize = db.Column(db.String(300), default="")
        description = db.Column(db.Text, default="")
        image = db.Column(db.String(300), default="")
        ends_on = db.Column(db.String(20), default="")

    class SweepstakesEntry(db.Model):
        __tablename__ = "sweepstakes_entries"
        id = db.Column(db.Integer, primary_key=True)
        sweepstake_id = db.Column(db.Integer, db.ForeignKey("sweepstakes.id"), nullable=False)
        user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
        entered_at = db.Column(db.DateTime)
        __table_args__ = (db.UniqueConstraint("sweepstake_id", "user_id", name="uq_sweep_user"),)

    class Poll(db.Model):
        __tablename__ = "polls"
        id = db.Column(db.Integer, primary_key=True)
        slug = db.Column(db.String(150), unique=True, index=True, nullable=False)
        question = db.Column(db.String(300), nullable=False)
        ends_on = db.Column(db.String(20), default="")
        options = db.relationship("PollOption", backref="poll", lazy=True,
                                  cascade="all, delete-orphan",
                                  order_by="PollOption.id")

    class PollOption(db.Model):
        __tablename__ = "poll_options"
        id = db.Column(db.Integer, primary_key=True)
        poll_id = db.Column(db.Integer, db.ForeignKey("polls.id"), nullable=False)
        text = db.Column(db.String(200), nullable=False)
        votes = db.Column(db.Integer, default=0)

    class PollVote(db.Model):
        __tablename__ = "poll_votes"
        id = db.Column(db.Integer, primary_key=True)
        poll_id = db.Column(db.Integer, db.ForeignKey("polls.id"), nullable=False)
        option_id = db.Column(db.Integer, db.ForeignKey("poll_options.id"), nullable=False)
        user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
        __table_args__ = (db.UniqueConstraint("poll_id", "user_id", name="uq_poll_user"),)

    class WantToSee(db.Model):
        __tablename__ = "want_to_see"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
        movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), nullable=False)
        added_at = db.Column(db.DateTime)
        __table_args__ = (db.UniqueConstraint("user_id", "movie_id", name="uq_user_movie_wts"),)

    class Watched(db.Model):
        __tablename__ = "watched"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
        movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), nullable=False)
        added_at = db.Column(db.DateTime)
        __table_args__ = (db.UniqueConstraint("user_id", "movie_id", name="uq_user_movie_w"),)

    class ReviewHelpful(db.Model):
        __tablename__ = "review_helpful"
        id = db.Column(db.Integer, primary_key=True)
        review_id = db.Column(db.Integer, db.ForeignKey("audience_reviews.id"), nullable=False)
        user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
        helpful = db.Column(db.Boolean, default=True)
        __table_args__ = (db.UniqueConstraint("review_id", "user_id", name="uq_review_helpful_user"),)

    class ReviewReport(db.Model):
        __tablename__ = "review_reports"
        id = db.Column(db.Integer, primary_key=True)
        review_id = db.Column(db.Integer, db.ForeignKey("audience_reviews.id"), nullable=False)
        user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
        reason = db.Column(db.String(100), default="")
        reported_at = db.Column(db.DateTime)

    class Photo(db.Model):
        __tablename__ = "photos"
        id = db.Column(db.Integer, primary_key=True)
        movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), nullable=True)
        tv_id = db.Column(db.Integer, db.ForeignKey("tv_shows.id"), nullable=True)
        image = db.Column(db.String(300), nullable=False)
        caption = db.Column(db.String(400), default="")
        kind = db.Column(db.String(40), default="still")
        order = db.Column(db.Integer, default=0)

    class Award(db.Model):
        __tablename__ = "awards"
        id = db.Column(db.Integer, primary_key=True)
        year = db.Column(db.Integer, nullable=False, index=True)
        category = db.Column(db.String(120), nullable=False)
        movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), nullable=True)
        person_id = db.Column(db.Integer, db.ForeignKey("persons.id"), nullable=True)
        winner = db.Column(db.Boolean, default=False)

    class CriticReview_relMixin:
        pass

    # Add a relationship from NewsComment → User so templates can iterate
    # `comment.user.name` without an extra query.
    NewsComment.user = db.relationship("User", lazy="joined")

    # Expose models so the seeder can reach them.
    models = dict(
        TVShow=TVShow, Season=Season, Episode=Episode,
        Critic=Critic, CriticFollow=CriticFollow,
        MovieList=MovieList, MovieListItem=MovieListItem,
        NewsArticle=NewsArticle, NewsComment=NewsComment,
        Podcast=Podcast, PodcastEpisode=PodcastEpisode,
        PodcastSubscribe=PodcastSubscribe,
        Sweepstakes=Sweepstakes, SweepstakesEntry=SweepstakesEntry,
        Poll=Poll, PollOption=PollOption, PollVote=PollVote,
        WantToSee=WantToSee, Watched=Watched,
        ReviewHelpful=ReviewHelpful, ReviewReport=ReviewReport,
        Photo=Photo, Award=Award,
    )

    # ─── helpers ────────────────────────────────────────────

    def _redirect_back(default):
        return redirect(request.referrer or default)

    def _user_state(movie_id):
        """Return (in_watchlist, in_want_to_see, in_watched, user_rating)."""
        from app import WatchlistItem, UserRating
        if not current_user.is_authenticated:
            return False, False, False, None
        in_wl = WatchlistItem.query.filter_by(
            user_id=current_user.id, movie_id=movie_id).first() is not None
        in_wts = WantToSee.query.filter_by(
            user_id=current_user.id, movie_id=movie_id).first() is not None
        in_watched = Watched.query.filter_by(
            user_id=current_user.id, movie_id=movie_id).first() is not None
        rating = UserRating.query.filter_by(
            user_id=current_user.id, movie_id=movie_id).first()
        return in_wl, in_wts, in_watched, rating

    # ─── new routes: pages ──────────────────────────────────

    @app.route("/m/<slug>/reviews")
    def movie_reviews_tab(slug):
        which = request.args.get("type", "all")  # all | top_critics | audience
        movie = Movie.query.filter_by(slug=slug).first_or_404()
        critic = CriticReview.query.filter_by(movie_id=movie.id).order_by(CriticReview.id).all()
        audience = AudienceReview.query.filter_by(movie_id=movie.id).order_by(AudienceReview.review_date.desc()).all()
        # Build top_critic lookup: critic name → is_top
        top_lookup = {c.name: c.top_critic for c in Critic.query.all()}
        return render_template("movie_reviews_tab.html", movie=movie,
                               critic_reviews=critic, audience_reviews=audience,
                               top_lookup=top_lookup, which=which)

    @app.route("/m/<slug>/cast")
    def movie_cast_page(slug):
        movie = Movie.query.filter_by(slug=slug).first_or_404()
        cast = MovieCast.query.filter_by(movie_id=movie.id).order_by(MovieCast.billing_order).all()
        actors = [c for c in cast if c.role_type == "actor"]
        directors = [c for c in cast if c.role_type == "director"]
        return render_template("movie_cast_page.html", movie=movie,
                               actors=actors, directors=directors)

    @app.route("/m/<slug>/photos")
    def movie_photos_page(slug):
        movie = Movie.query.filter_by(slug=slug).first_or_404()
        photos = Photo.query.filter_by(movie_id=movie.id).order_by(Photo.order, Photo.id).all()
        return render_template("movie_photos_page.html", movie=movie, photos=photos)

    @app.route("/tv/<slug>")
    def tv_detail(slug):
        tv = TVShow.query.filter_by(slug=slug).first_or_404()
        return render_template("tv_detail.html", tv=tv)

    @app.route("/tv/<slug>/s<int:n>")
    def tv_season(slug, n):
        tv = TVShow.query.filter_by(slug=slug).first_or_404()
        season = Season.query.filter_by(tv_id=tv.id, number=n).first_or_404()
        return render_template("tv_season.html", tv=tv, season=season)

    @app.route("/tv/<slug>/s<int:s>/e<int:e>")
    def tv_episode(slug, s, e):
        tv = TVShow.query.filter_by(slug=slug).first_or_404()
        season = Season.query.filter_by(tv_id=tv.id, number=s).first_or_404()
        ep = Episode.query.filter_by(season_id=season.id, number=e).first_or_404()
        return render_template("tv_episode.html", tv=tv, season=season, ep=ep)

    @app.route("/browse/tv/")
    def browse_tv():
        sort = request.args.get("sort", "popular")
        q = TVShow.query
        if sort == "newest":
            q = q.order_by(TVShow.year_start.desc(), TVShow.title)
        elif sort == "tomatometer":
            q = q.order_by(TVShow.tomatometer.desc(), TVShow.title)
        elif sort == "audience":
            q = q.order_by(TVShow.audience_score.desc(), TVShow.title)
        else:
            q = q.order_by(TVShow.audience_score.desc(), TVShow.tomatometer.desc())
        return render_template("browse_tv.html", shows=q.all(), current_sort=sort)

    @app.route("/critics/")
    def critics_index():
        top_only = request.args.get("top", "") == "1"
        q = Critic.query
        if top_only:
            q = q.filter_by(top_critic=True)
        critics = q.order_by(Critic.name).all()
        return render_template("critics_index.html", critics=critics, top_only=top_only)

    @app.route("/critics/<slug>")
    def critic_detail(slug):
        critic = Critic.query.filter_by(slug=slug).first_or_404()
        reviews = CriticReview.query.filter_by(critic_name=critic.name, publication=critic.publication).all()
        is_following = False
        if current_user.is_authenticated:
            is_following = CriticFollow.query.filter_by(
                user_id=current_user.id, critic_id=critic.id).first() is not None
        return render_template("critic_detail.html", critic=critic,
                               reviews=reviews, is_following=is_following)

    @app.route("/list/<slug>")
    def list_detail(slug):
        lst = MovieList.query.filter_by(slug=slug).first_or_404()
        return render_template("list_detail.html", list=lst)

    @app.route("/lists/")
    def lists_index():
        # Public lists only on the index page
        lists = MovieList.query.filter_by(is_public=True).order_by(MovieList.id).all()
        return render_template("lists_index.html", lists=lists)

    @app.route("/news/")
    def news_index():
        cat = request.args.get("category", "")
        q = NewsArticle.query
        if cat:
            q = q.filter_by(category=cat)
        items = q.order_by(NewsArticle.published_at.desc()).all()
        cats = ["Movies", "TV", "Awards", "Box Office", "Streaming", "Trailers", "Interviews"]
        return render_template("news_index.html", articles=items, categories=cats, current_cat=cat)

    @app.route("/news/<slug>")
    def news_detail(slug):
        art = NewsArticle.query.filter_by(slug=slug).first_or_404()
        comments = NewsComment.query.filter_by(news_id=art.id).order_by(NewsComment.created_at.desc()).all()
        tag_movie = Movie.query.get(art.tag_movie_id) if art.tag_movie_id else None
        return render_template("news_detail.html", article=art, comments=comments, tag_movie=tag_movie)

    @app.route("/podcasts/")
    def podcasts_index():
        items = Podcast.query.order_by(Podcast.title).all()
        return render_template("podcasts_index.html", podcasts=items)

    @app.route("/podcasts/<slug>")
    def podcast_detail(slug):
        pod = Podcast.query.filter_by(slug=slug).first_or_404()
        episodes = PodcastEpisode.query.filter_by(podcast_id=pod.id).order_by(PodcastEpisode.number.desc()).all()
        subscribed = False
        if current_user.is_authenticated:
            subscribed = PodcastSubscribe.query.filter_by(
                user_id=current_user.id, podcast_id=pod.id).first() is not None
        return render_template("podcast_detail.html", podcast=pod, episodes=episodes, subscribed=subscribed)

    @app.route("/sweepstakes/")
    def sweepstakes_index():
        items = Sweepstakes.query.order_by(Sweepstakes.ends_on, Sweepstakes.id).all()
        return render_template("sweepstakes_index.html", sweepstakes=items)

    @app.route("/sweepstakes/<slug>")
    def sweepstakes_detail(slug):
        sw = Sweepstakes.query.filter_by(slug=slug).first_or_404()
        entered = False
        entry_count = SweepstakesEntry.query.filter_by(sweepstake_id=sw.id).count()
        if current_user.is_authenticated:
            entered = SweepstakesEntry.query.filter_by(
                sweepstake_id=sw.id, user_id=current_user.id).first() is not None
        return render_template("sweepstakes_detail.html",
                               sweepstake=sw, entered=entered, entry_count=entry_count)

    @app.route("/polls/")
    def polls_index():
        polls = Poll.query.order_by(Poll.id).all()
        return render_template("polls_index.html", polls=polls)

    @app.route("/polls/<slug>")
    def poll_detail(slug):
        poll = Poll.query.filter_by(slug=slug).first_or_404()
        already_voted = False
        if current_user.is_authenticated:
            already_voted = PollVote.query.filter_by(
                poll_id=poll.id, user_id=current_user.id).first() is not None
        total_votes = sum(o.votes for o in poll.options) or 1
        return render_template("poll_detail.html", poll=poll,
                               already_voted=already_voted, total_votes=total_votes)

    @app.route("/awards/")
    def awards_index():
        years = sorted({a.year for a in Award.query.all()}, reverse=True)
        return render_template("awards_index.html", years=years)

    @app.route("/awards/<int:year>")
    def awards_year(year):
        items = Award.query.filter_by(year=year).order_by(Award.category, Award.id).all()
        if not items:
            abort(404)
        # Group by category
        grouped = {}
        for a in items:
            grouped.setdefault(a.category, []).append(a)
        return render_template("awards_year.html", year=year, grouped=grouped)

    @app.route("/theatrical/in-theaters")
    def hub_in_theaters():
        movies = Movie.query.filter_by(in_theaters=True)\
            .order_by(Movie.audience_score.desc()).limit(40).all()
        return render_template("hub_movies.html",
                               title="In Theaters", hub_kind="in_theaters",
                               movies=movies)

    @app.route("/theatrical/coming-soon")
    def hub_coming_soon():
        movies = Movie.query.filter(Movie.year >= 2026)\
            .order_by(Movie.year, Movie.title).limit(40).all()
        return render_template("hub_movies.html",
                               title="Coming Soon to Theaters", hub_kind="coming_soon",
                               movies=movies)

    @app.route("/streaming/now")
    def hub_streaming_now():
        movies = Movie.query.filter(Movie.streaming_platform != "")\
            .order_by(Movie.tomatometer.desc()).limit(40).all()
        return render_template("hub_movies.html",
                               title="Streaming Now", hub_kind="streaming_now",
                               movies=movies)

    @app.route("/streaming/coming-soon")
    def hub_streaming_coming():
        movies = Movie.query.filter(Movie.year >= 2025)\
            .filter(Movie.streaming_platform != "")\
            .order_by(Movie.year.desc(), Movie.title).limit(40).all()
        return render_template("hub_movies.html",
                               title="Coming Soon to Streaming", hub_kind="streaming_coming_soon",
                               movies=movies)

    @app.route("/myaccount")
    @login_required
    def myaccount_hub():
        return redirect(url_for("account"))

    @app.route("/myaccount/want-to-see")
    @login_required
    def myaccount_wts():
        items = WantToSee.query.filter_by(user_id=current_user.id)\
            .order_by(WantToSee.added_at.desc()).all()
        movies = [Movie.query.get(i.movie_id) for i in items]
        movies = [m for m in movies if m is not None]
        return render_template("myaccount_wts.html", movies=movies)

    @app.route("/myaccount/watched")
    @login_required
    def myaccount_watched():
        items = Watched.query.filter_by(user_id=current_user.id)\
            .order_by(Watched.added_at.desc()).all()
        movies = [Movie.query.get(i.movie_id) for i in items]
        movies = [m for m in movies if m is not None]
        return render_template("myaccount_watched.html", movies=movies)

    @app.route("/myaccount/follows")
    @login_required
    def myaccount_follows():
        follows = CriticFollow.query.filter_by(user_id=current_user.id).all()
        critics = [Critic.query.get(f.critic_id) for f in follows]
        critics = [c for c in critics if c is not None]
        return render_template("myaccount_follows.html", critics=critics)

    @app.route("/myaccount/lists")
    @login_required
    def myaccount_lists():
        lists = MovieList.query.filter_by(owner_id=current_user.id)\
            .order_by(MovieList.created_at.desc()).all()
        return render_template("myaccount_lists.html", lists=lists)

    @app.route("/myaccount/podcasts")
    @login_required
    def myaccount_podcasts():
        subs = PodcastSubscribe.query.filter_by(user_id=current_user.id).all()
        podcasts = [Podcast.query.get(s.podcast_id) for s in subs]
        podcasts = [p for p in podcasts if p is not None]
        return render_template("myaccount_podcasts.html", podcasts=podcasts)

    @app.route("/myaccount/sweepstakes")
    @login_required
    def myaccount_sweeps():
        entries = SweepstakesEntry.query.filter_by(user_id=current_user.id)\
            .order_by(SweepstakesEntry.entered_at.desc()).all()
        sweeps = [Sweepstakes.query.get(e.sweepstake_id) for e in entries]
        sweeps = [s for s in sweeps if s is not None]
        return render_template("myaccount_sweeps.html", sweepstakes=sweeps)

    # ─── new routes: POST actions (17 total) ────────────────

    @app.route("/m/<slug>/want-to-see", methods=["POST"])
    @login_required
    def wts_add(slug):
        movie = Movie.query.filter_by(slug=slug).first_or_404()
        if not WantToSee.query.filter_by(user_id=current_user.id, movie_id=movie.id).first():
            db.session.add(WantToSee(user_id=current_user.id, movie_id=movie.id,
                                     added_at=datetime.utcnow()))
            db.session.commit()
            flash(f'Added "{movie.title}" to your Want to See list.', "success")
        return _redirect_back(url_for("movie_detail", slug=slug))

    @app.route("/m/<slug>/want-to-see/remove", methods=["POST"])
    @login_required
    def wts_remove(slug):
        movie = Movie.query.filter_by(slug=slug).first_or_404()
        row = WantToSee.query.filter_by(user_id=current_user.id, movie_id=movie.id).first()
        if row:
            db.session.delete(row)
            db.session.commit()
            flash(f'Removed "{movie.title}" from your Want to See list.', "success")
        return _redirect_back(url_for("movie_detail", slug=slug))

    @app.route("/m/<slug>/watched", methods=["POST"])
    @login_required
    def watched_add(slug):
        movie = Movie.query.filter_by(slug=slug).first_or_404()
        if not Watched.query.filter_by(user_id=current_user.id, movie_id=movie.id).first():
            db.session.add(Watched(user_id=current_user.id, movie_id=movie.id,
                                    added_at=datetime.utcnow()))
            db.session.commit()
            flash(f'Marked "{movie.title}" as watched.', "success")
        return _redirect_back(url_for("movie_detail", slug=slug))

    @app.route("/m/<slug>/watched/remove", methods=["POST"])
    @login_required
    def watched_remove(slug):
        movie = Movie.query.filter_by(slug=slug).first_or_404()
        row = Watched.query.filter_by(user_id=current_user.id, movie_id=movie.id).first()
        if row:
            db.session.delete(row)
            db.session.commit()
            flash(f'Removed "{movie.title}" from watched.', "success")
        return _redirect_back(url_for("movie_detail", slug=slug))

    @app.route("/review/<int:review_id>/helpful", methods=["POST"])
    @login_required
    def review_helpful(review_id):
        review = AudienceReview.query.get_or_404(review_id)
        helpful = request.form.get("helpful", "true").lower() == "true"
        existing = ReviewHelpful.query.filter_by(
            review_id=review_id, user_id=current_user.id).first()
        if existing:
            existing.helpful = helpful
        else:
            db.session.add(ReviewHelpful(review_id=review_id,
                                          user_id=current_user.id,
                                          helpful=helpful))
        db.session.commit()
        flash("Thanks for the feedback.", "success")
        return _redirect_back(url_for("movie_detail", slug=review.movie.slug))

    @app.route("/review/<int:review_id>/report", methods=["POST"])
    @login_required
    def review_report(review_id):
        review = AudienceReview.query.get_or_404(review_id)
        reason = (request.form.get("reason") or "inappropriate").strip()[:80]
        if not ReviewReport.query.filter_by(review_id=review_id, user_id=current_user.id).first():
            db.session.add(ReviewReport(review_id=review_id,
                                         user_id=current_user.id,
                                         reason=reason,
                                         reported_at=datetime.utcnow()))
            db.session.commit()
        flash("Review reported. Thank you.", "success")
        return _redirect_back(url_for("movie_detail", slug=review.movie.slug))

    @app.route("/news/<slug>/comment", methods=["POST"])
    @login_required
    def news_comment(slug):
        art = NewsArticle.query.filter_by(slug=slug).first_or_404()
        text = (request.form.get("text") or "").strip()
        if len(text) < 1:
            flash("Comment cannot be empty.", "danger")
            return redirect(url_for("news_detail", slug=slug))
        db.session.add(NewsComment(news_id=art.id, user_id=current_user.id,
                                    text=text, created_at=datetime.utcnow()))
        db.session.commit()
        flash("Comment posted.", "success")
        return redirect(url_for("news_detail", slug=slug))

    @app.route("/news/comment/<int:comment_id>/delete", methods=["POST"])
    @login_required
    def news_comment_delete(comment_id):
        c = NewsComment.query.get_or_404(comment_id)
        if c.user_id != current_user.id:
            flash("You can only delete your own comments.", "danger")
            return _redirect_back("/")
        slug = NewsArticle.query.get(c.news_id).slug
        db.session.delete(c)
        db.session.commit()
        flash("Comment deleted.", "success")
        return redirect(url_for("news_detail", slug=slug))

    @app.route("/polls/<slug>/vote", methods=["POST"])
    @login_required
    def poll_vote(slug):
        poll = Poll.query.filter_by(slug=slug).first_or_404()
        if PollVote.query.filter_by(poll_id=poll.id, user_id=current_user.id).first():
            flash("You have already voted in this poll.", "info")
            return redirect(url_for("poll_detail", slug=slug))
        try:
            option_id = int(request.form.get("option_id"))
        except (TypeError, ValueError):
            flash("Invalid choice.", "danger")
            return redirect(url_for("poll_detail", slug=slug))
        opt = PollOption.query.get_or_404(option_id)
        if opt.poll_id != poll.id:
            flash("Invalid choice.", "danger")
            return redirect(url_for("poll_detail", slug=slug))
        opt.votes = (opt.votes or 0) + 1
        db.session.add(PollVote(poll_id=poll.id, option_id=opt.id, user_id=current_user.id))
        db.session.commit()
        flash("Your vote has been recorded.", "success")
        return redirect(url_for("poll_detail", slug=slug))

    @app.route("/sweepstakes/<slug>/enter", methods=["POST"])
    @login_required
    def sweepstakes_enter(slug):
        sw = Sweepstakes.query.filter_by(slug=slug).first_or_404()
        if SweepstakesEntry.query.filter_by(sweepstake_id=sw.id, user_id=current_user.id).first():
            flash("You have already entered this sweepstakes.", "info")
        else:
            db.session.add(SweepstakesEntry(sweepstake_id=sw.id,
                                             user_id=current_user.id,
                                             entered_at=datetime.utcnow()))
            db.session.commit()
            flash(f'Entry submitted for "{sw.title}". Good luck!', "success")
        return redirect(url_for("sweepstakes_detail", slug=slug))

    @app.route("/critics/<slug>/follow", methods=["POST"])
    @login_required
    def critic_follow(slug):
        critic = Critic.query.filter_by(slug=slug).first_or_404()
        if not CriticFollow.query.filter_by(user_id=current_user.id, critic_id=critic.id).first():
            db.session.add(CriticFollow(user_id=current_user.id, critic_id=critic.id))
            db.session.commit()
            flash(f"You are now following {critic.name}.", "success")
        return redirect(url_for("critic_detail", slug=slug))

    @app.route("/critics/<slug>/unfollow", methods=["POST"])
    @login_required
    def critic_unfollow(slug):
        critic = Critic.query.filter_by(slug=slug).first_or_404()
        row = CriticFollow.query.filter_by(user_id=current_user.id, critic_id=critic.id).first()
        if row:
            db.session.delete(row)
            db.session.commit()
            flash(f"Unfollowed {critic.name}.", "success")
        return redirect(url_for("critic_detail", slug=slug))

    @app.route("/podcasts/<slug>/subscribe", methods=["POST"])
    @login_required
    def podcast_subscribe(slug):
        pod = Podcast.query.filter_by(slug=slug).first_or_404()
        if not PodcastSubscribe.query.filter_by(user_id=current_user.id, podcast_id=pod.id).first():
            db.session.add(PodcastSubscribe(user_id=current_user.id, podcast_id=pod.id))
            db.session.commit()
            flash(f'Subscribed to "{pod.title}".', "success")
        return redirect(url_for("podcast_detail", slug=slug))

    @app.route("/podcasts/<slug>/unsubscribe", methods=["POST"])
    @login_required
    def podcast_unsubscribe(slug):
        pod = Podcast.query.filter_by(slug=slug).first_or_404()
        row = PodcastSubscribe.query.filter_by(user_id=current_user.id, podcast_id=pod.id).first()
        if row:
            db.session.delete(row)
            db.session.commit()
            flash(f'Unsubscribed from "{pod.title}".', "success")
        return redirect(url_for("podcast_detail", slug=slug))

    @app.route("/lists/create", methods=["POST"])
    @login_required
    def list_create():
        title = (request.form.get("title") or "").strip()
        desc = (request.form.get("description") or "").strip()
        is_public = request.form.get("is_public", "1") == "1"
        if len(title) < 2:
            flash("List title must be at least 2 characters.", "danger")
            return _redirect_back(url_for("myaccount_lists"))
        # Slug = "<user_id>_<safe_title>"
        safe = "".join(ch.lower() if ch.isalnum() else "_" for ch in title)[:80].strip("_")
        slug = f"u{current_user.id}_{safe}"
        # Make unique if collision
        base = slug
        n = 1
        while MovieList.query.filter_by(slug=slug).first():
            n += 1
            slug = f"{base}_{n}"
        lst = MovieList(slug=slug, title=title, description=desc,
                        owner_id=current_user.id, is_public=is_public,
                        tag="user", created_at=datetime.utcnow())
        db.session.add(lst)
        db.session.commit()
        flash(f'List "{title}" created.', "success")
        return redirect(url_for("list_detail", slug=slug))

    @app.route("/lists/<slug>/delete", methods=["POST"])
    @login_required
    def list_delete(slug):
        lst = MovieList.query.filter_by(slug=slug).first_or_404()
        if lst.owner_id != current_user.id:
            flash("You can only delete your own lists.", "danger")
            return redirect(url_for("list_detail", slug=slug))
        db.session.delete(lst)
        db.session.commit()
        flash("List deleted.", "success")
        return redirect(url_for("myaccount_lists"))

    @app.route("/lists/<slug>/add/<int:movie_id>", methods=["POST"])
    @login_required
    def list_add_movie(slug, movie_id):
        lst = MovieList.query.filter_by(slug=slug).first_or_404()
        movie = Movie.query.get_or_404(movie_id)
        if lst.owner_id != current_user.id:
            flash("You can only edit your own lists.", "danger")
            return redirect(url_for("list_detail", slug=slug))
        if MovieListItem.query.filter_by(list_id=lst.id, movie_id=movie.id).first():
            flash(f'"{movie.title}" is already in this list.', "info")
        else:
            next_order = (db.session.query(func.max(MovieListItem.order))
                          .filter_by(list_id=lst.id).scalar() or 0) + 1
            db.session.add(MovieListItem(list_id=lst.id, movie_id=movie.id, order=next_order))
            db.session.commit()
            flash(f'Added "{movie.title}" to "{lst.title}".', "success")
        return redirect(url_for("list_detail", slug=slug))

    @app.route("/lists/<slug>/remove/<int:movie_id>", methods=["POST"])
    @login_required
    def list_remove_movie(slug, movie_id):
        lst = MovieList.query.filter_by(slug=slug).first_or_404()
        if lst.owner_id != current_user.id:
            flash("You can only edit your own lists.", "danger")
            return redirect(url_for("list_detail", slug=slug))
        row = MovieListItem.query.filter_by(list_id=lst.id, movie_id=movie_id).first()
        if row:
            db.session.delete(row)
            db.session.commit()
            flash("Movie removed from list.", "success")
        return redirect(url_for("list_detail", slug=slug))

    # Stash for use elsewhere
    app.config["RT_EXT_MODELS"] = models

    @app.route("/about")
    def about_page():
        return render_template("about.html")

    @app.route("/shop")
    @app.route("/store")
    def shop_page():
        return render_template("shop.html")

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("404.html"), 404

    return models
