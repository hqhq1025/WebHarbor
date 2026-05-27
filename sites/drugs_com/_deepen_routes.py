"""Drugs.com deepening — models, routes, seed, task generator (part 2)."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from flask import (
    abort, current_app, flash, jsonify, redirect, render_template,
    request, url_for,
)
from flask_login import current_user, login_required

from _deepen import (
    GLOSSARY_TERMS, FORUM_CATEGORIES, FORUM_TOPICS_RAW, HEALTH_NEWS_RAW,
    DRUG_RECALLS_RAW, PHARMACIES_RAW, ALICE_REFILL_REMINDERS,
    BOB_REFILL_REMINDERS, SIDE_EFFECT_REPORTS_RAW, MIRROR_REFERENCE_DATE,
)


def register_deepening(app, db):
    """Register all new models, routes, and seed hooks on the given app/db."""
    from app import (
        User, Drug, DrugClass, Condition, DrugReview, slugify,
    )
    from sqlalchemy import text as _sql_text

    def normalize_seed_db_layout():
        """Re-emit indexes in alpha order + VACUUM so rebuilds match byte-for-byte."""
        conn = db.engine.connect()
        idx_rows = conn.execute(_sql_text(
            "SELECT name, sql FROM sqlite_master WHERE type='index' AND name LIKE 'ix_%'"
        )).fetchall()
        for name, _ in idx_rows:
            conn.execute(_sql_text(f"DROP INDEX IF EXISTS {name}"))
        for name, sql in sorted(idx_rows, key=lambda r: r[0]):
            if sql:
                conn.execute(_sql_text(sql))
        conn.execute(_sql_text("VACUUM"))
        conn.commit()

    # ------------------------------------------------------------------
    # Models
    # ------------------------------------------------------------------
    class GlossaryTerm(db.Model):
        __tablename__ = "glossary_term"
        id = db.Column(db.Integer, primary_key=True)
        slug = db.Column(db.String(120), unique=True, nullable=False)
        term = db.Column(db.String(120), nullable=False)
        definition = db.Column(db.Text, nullable=False)
        letter = db.Column(db.String(2), index=True)

    class ForumCategory(db.Model):
        __tablename__ = "forum_category"
        id = db.Column(db.Integer, primary_key=True)
        slug = db.Column(db.String(80), unique=True, nullable=False)
        name = db.Column(db.String(120), nullable=False)
        description = db.Column(db.Text)
        topic_count = db.Column(db.Integer, default=0)

    class ForumTopic(db.Model):
        __tablename__ = "forum_topic"
        id = db.Column(db.Integer, primary_key=True)
        category_id = db.Column(db.Integer, db.ForeignKey("forum_category.id"), nullable=False)
        user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        slug = db.Column(db.String(200), unique=True, nullable=False)
        title = db.Column(db.String(255), nullable=False)
        body = db.Column(db.Text, nullable=False)
        reply_count = db.Column(db.Integer, default=0)
        view_count = db.Column(db.Integer, default=0)
        created_at = db.Column(db.DateTime, nullable=False)
        category = db.relationship("ForumCategory", backref="topics")
        user = db.relationship("User", foreign_keys=[user_id])

    class ForumPost(db.Model):
        __tablename__ = "forum_post"
        id = db.Column(db.Integer, primary_key=True)
        topic_id = db.Column(db.Integer, db.ForeignKey("forum_topic.id"), nullable=False)
        user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        body = db.Column(db.Text, nullable=False)
        created_at = db.Column(db.DateTime, nullable=False)
        helpful_count = db.Column(db.Integer, default=0)
        topic = db.relationship("ForumTopic", backref="posts")
        user = db.relationship("User", foreign_keys=[user_id])

    class RefillReminder(db.Model):
        __tablename__ = "refill_reminder"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        drug_id = db.Column(db.Integer, db.ForeignKey("drug.id"), nullable=False)
        days_supply = db.Column(db.Integer, default=30)
        frequency = db.Column(db.String(40), default="daily")
        next_refill_at = db.Column(db.DateTime, nullable=False)
        pharmacy_id = db.Column(db.Integer, db.ForeignKey("pharmacy.id"))
        created_at = db.Column(db.DateTime, nullable=False)
        drug = db.relationship("Drug")
        user = db.relationship("User", foreign_keys=[user_id])

    class HealthNews(db.Model):
        __tablename__ = "health_news"
        id = db.Column(db.Integer, primary_key=True)
        slug = db.Column(db.String(200), unique=True, nullable=False)
        title = db.Column(db.String(255), nullable=False)
        category = db.Column(db.String(80), index=True)
        body = db.Column(db.Text)
        published_at = db.Column(db.DateTime, nullable=False)
        is_featured = db.Column(db.Boolean, default=False)

    class DrugRecall(db.Model):
        __tablename__ = "drug_recall"
        id = db.Column(db.Integer, primary_key=True)
        slug = db.Column(db.String(200), unique=True, nullable=False)
        drug_name = db.Column(db.String(200), nullable=False)
        lot_number = db.Column(db.String(80))
        severity = db.Column(db.String(40))
        reason = db.Column(db.Text)
        recalled_at = db.Column(db.DateTime, nullable=False)
        is_subscribed = db.Column(db.Boolean, default=False)

    class Pharmacy(db.Model):
        __tablename__ = "pharmacy"
        id = db.Column(db.Integer, primary_key=True)
        slug = db.Column(db.String(120), unique=True, nullable=False)
        name = db.Column(db.String(200), nullable=False)
        chain = db.Column(db.String(80))
        address = db.Column(db.String(200))
        city = db.Column(db.String(80))
        state = db.Column(db.String(20))
        zip_code = db.Column(db.String(20))
        phone = db.Column(db.String(40))
        hours = db.Column(db.String(200))

    class SideEffectReport(db.Model):
        __tablename__ = "side_effect_report"
        id = db.Column(db.Integer, primary_key=True)
        drug_id = db.Column(db.Integer, db.ForeignKey("drug.id"), nullable=False)
        user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        severity = db.Column(db.String(40))
        body = db.Column(db.Text, nullable=False)
        created_at = db.Column(db.DateTime, nullable=False)
        drug = db.relationship("Drug")
        user = db.relationship("User", foreign_keys=[user_id])

    class ContactPharmacistMsg(db.Model):
        __tablename__ = "contact_pharmacist_msg"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
        pharmacist_name = db.Column(db.String(120))
        topic = db.Column(db.String(120))
        body = db.Column(db.Text)
        created_at = db.Column(db.DateTime, nullable=False)
        answered = db.Column(db.Boolean, default=False)

    class DosageCalculation(db.Model):
        __tablename__ = "dosage_calculation"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
        drug_id = db.Column(db.Integer, db.ForeignKey("drug.id"), nullable=False)
        weight_kg = db.Column(db.Float)
        age_years = db.Column(db.Integer)
        result_mg = db.Column(db.Float)
        created_at = db.Column(db.DateTime, nullable=False)

    class SavedComparison(db.Model):
        __tablename__ = "saved_comparison"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        drug_a_id = db.Column(db.Integer, db.ForeignKey("drug.id"), nullable=False)
        drug_b_id = db.Column(db.Integer, db.ForeignKey("drug.id"), nullable=False)
        note = db.Column(db.Text, default="")
        created_at = db.Column(db.DateTime, nullable=False)

    # Stash models on app for use elsewhere
    app.extensions["deepen_models"] = {
        "GlossaryTerm": GlossaryTerm,
        "ForumCategory": ForumCategory,
        "ForumTopic": ForumTopic,
        "ForumPost": ForumPost,
        "RefillReminder": RefillReminder,
        "HealthNews": HealthNews,
        "DrugRecall": DrugRecall,
        "Pharmacy": Pharmacy,
        "SideEffectReport": SideEffectReport,
        "ContactPharmacistMsg": ContactPharmacistMsg,
        "DosageCalculation": DosageCalculation,
        "SavedComparison": SavedComparison,
    }

    # ------------------------------------------------------------------
    # Seed function
    # ------------------------------------------------------------------
    def seed_deepening():
        """Add deepening-table rows. Gated on each table being empty.

        normalize_seed_db_layout() runs ONLY when at least one seed was added
        this boot — calling it on a stable DB would introduce byte drift via
        VACUUM repagination. First boot after a fresh build seeds + normalizes
        once; subsequent boots are no-ops and leave bytes untouched.
        """
        ref = MIRROR_REFERENCE_DATE
        changed = False

        if GlossaryTerm.query.count() == 0:
            for idx, (slug, definition) in enumerate(GLOSSARY_TERMS):
                term = slug.replace("-", " ").title()
                letter = slug[0].upper()
                db.session.add(GlossaryTerm(
                    slug=slug, term=term, definition=definition, letter=letter,
                ))
            db.session.commit()
            changed = True

        if ForumCategory.query.count() == 0:
            for slug, name, desc in FORUM_CATEGORIES:
                db.session.add(ForumCategory(slug=slug, name=name, description=desc))
            db.session.commit()
            changed = True

        if ForumTopic.query.count() == 0:
            cat_by_slug = {c.slug: c for c in ForumCategory.query.all()}
            users = User.query.order_by(User.id).all()
            for idx, (cat_slug, title, body) in enumerate(FORUM_TOPICS_RAW):
                cat = cat_by_slug.get(cat_slug)
                if not cat:
                    continue
                user = users[idx % len(users)] if users else None
                if not user:
                    continue
                topic_slug = f"{cat_slug}-{slugify(title)[:80]}-{idx:04d}"
                created = ref - timedelta(days=(120 - idx))
                topic = ForumTopic(
                    category_id=cat.id, user_id=user.id, slug=topic_slug,
                    title=title, body=body, view_count=50 + idx * 7,
                    reply_count=0, created_at=created,
                )
                db.session.add(topic)
            db.session.flush()
            # Add 2-4 replies per topic (deterministic)
            topics = ForumTopic.query.order_by(ForumTopic.id).all()
            for ti, topic in enumerate(topics):
                n_replies = 2 + (ti % 3)  # 2..4
                for ri in range(n_replies):
                    u = users[(ti + ri + 1) % len(users)]
                    body = (
                        f"In my experience, {topic.title.lower().split()[0]} responds differently "
                        f"by individual — your healthcare provider should review your specific case. "
                        f"Reply {ri+1} on this thread."
                    )
                    db.session.add(ForumPost(
                        topic_id=topic.id, user_id=u.id, body=body,
                        helpful_count=(ti * 3 + ri) % 17,
                        created_at=topic.created_at + timedelta(hours=6 * (ri + 1)),
                    ))
                topic.reply_count = n_replies
            # Recompute category topic counts
            for cat in ForumCategory.query.all():
                cat.topic_count = ForumTopic.query.filter_by(category_id=cat.id).count()
            db.session.commit()
            changed = True

        if Pharmacy.query.count() == 0:
            for slug, name, chain, addr, city, state, zip_code, phone, hours in PHARMACIES_RAW:
                db.session.add(Pharmacy(
                    slug=slug, name=name, chain=chain, address=addr,
                    city=city, state=state, zip_code=zip_code,
                    phone=phone, hours=hours,
                ))
            db.session.commit()
            changed = True

        if RefillReminder.query.count() == 0:
            drug_by_slug = {d.slug: d for d in Drug.query.all()}
            pharms = Pharmacy.query.order_by(Pharmacy.id).all()
            users = {u.username: u for u in User.query.all()}
            for username, reminders in [
                ("alice_j", ALICE_REFILL_REMINDERS),
                ("bob_c", BOB_REFILL_REMINDERS),
            ]:
                u = users.get(username)
                if not u:
                    continue
                for idx, (slug, days_supply, freq, offset) in enumerate(reminders):
                    drug = drug_by_slug.get(slug)
                    if not drug:
                        continue
                    db.session.add(RefillReminder(
                        user_id=u.id, drug_id=drug.id,
                        days_supply=days_supply, frequency=freq,
                        next_refill_at=ref + timedelta(days=offset),
                        pharmacy_id=pharms[idx % len(pharms)].id if pharms else None,
                        created_at=ref - timedelta(days=30 - offset),
                    ))
            db.session.commit()
            changed = True

        if HealthNews.query.count() == 0:
            for slug, title, cat, body, offset in HEALTH_NEWS_RAW:
                db.session.add(HealthNews(
                    slug=slug, title=title, category=cat, body=body,
                    published_at=ref - timedelta(days=offset),
                    is_featured=(offset <= 12),
                ))
            db.session.commit()
            changed = True

        if DrugRecall.query.count() == 0:
            for slug, name, lot, sev, reason, offset in DRUG_RECALLS_RAW:
                db.session.add(DrugRecall(
                    slug=slug, drug_name=name, lot_number=lot,
                    severity=sev, reason=reason,
                    recalled_at=ref - timedelta(days=offset),
                ))
            db.session.commit()
            changed = True

        if SideEffectReport.query.count() == 0:
            drug_by_slug = {d.slug: d for d in Drug.query.all()}
            user_by_name = {u.username: u for u in User.query.all()}
            for slug, sev, body, offset, uname in SIDE_EFFECT_REPORTS_RAW:
                d = drug_by_slug.get(slug)
                u = user_by_name.get(uname)
                if not d or not u:
                    continue
                db.session.add(SideEffectReport(
                    drug_id=d.id, user_id=u.id, severity=sev,
                    body=body, created_at=ref - timedelta(days=offset),
                ))
            db.session.commit()
            changed = True

        # Re-normalize SQLite layout ONLY when we just added rows (otherwise
        # VACUUM on a stable DB would repaginate and break byte-id reset).
        if changed:
            try:
                normalize_seed_db_layout()
            except Exception:
                pass

    app.extensions["seed_deepening"] = seed_deepening

    # ------------------------------------------------------------------
    # Helpers shared by routes
    # ------------------------------------------------------------------
    def _ctx_dropdowns():
        cats = ForumCategory.query.order_by(ForumCategory.id).all()
        return {"forum_categories": cats}

    # ------------------------------------------------------------------
    # Routes — Glossary
    # ------------------------------------------------------------------
    @app.route("/glossary")
    @app.route("/glossary/")
    @app.route("/glossary.html")
    def glossary_index():
        letter = (request.args.get("letter") or "").upper()
        q = GlossaryTerm.query
        if letter:
            q = q.filter(GlossaryTerm.letter == letter)
        terms = q.order_by(GlossaryTerm.slug).all()
        letters = sorted({t.letter for t in GlossaryTerm.query.all()})
        return render_template(
            "glossary_index.html", terms=terms, letters=letters, active_letter=letter,
        )

    @app.route("/glossary/<term>")
    @app.route("/glossary/<term>.html")
    def glossary_term(term):
        t = GlossaryTerm.query.filter_by(slug=term).first()
        if not t:
            abort(404)
        related = (
            GlossaryTerm.query
            .filter(GlossaryTerm.letter == t.letter, GlossaryTerm.id != t.id)
            .order_by(GlossaryTerm.slug)
            .limit(6)
            .all()
        )
        return render_template("glossary_term.html", term=t, related=related)

    # ------------------------------------------------------------------
    # Routes — Forum
    # ------------------------------------------------------------------
    @app.route("/forum")
    @app.route("/forum/")
    @app.route("/forum.html")
    def forum_index():
        cats = ForumCategory.query.order_by(ForumCategory.id).all()
        recent = (
            ForumTopic.query.order_by(ForumTopic.created_at.desc()).limit(12).all()
        )
        return render_template("forum_index.html", categories=cats, recent_topics=recent)

    @app.route("/forum/category/<slug>")
    @app.route("/forum/category/<slug>/")
    @app.route("/forum/category/<slug>.html")
    def forum_category(slug):
        cat = ForumCategory.query.filter_by(slug=slug).first_or_404()
        topics = (
            ForumTopic.query.filter_by(category_id=cat.id)
            .order_by(ForumTopic.created_at.desc()).all()
        )
        return render_template("forum_category.html", category=cat, topics=topics)

    @app.route("/forum/topic/<int:topic_id>")
    @app.route("/forum/topic/<int:topic_id>/")
    @app.route("/forum/topic/<int:topic_id>.html")
    def forum_topic(topic_id):
        topic = ForumTopic.query.get_or_404(topic_id)
        posts = (
            ForumPost.query.filter_by(topic_id=topic.id)
            .order_by(ForumPost.created_at).all()
        )
        return render_template("forum_topic.html", topic=topic, posts=posts)

    @app.route("/forum/new", methods=["GET", "POST"])
    @app.route("/forum/post/new", methods=["GET", "POST"])
    def forum_new_topic():
        cats = ForumCategory.query.order_by(ForumCategory.id).all()
        if request.method == "POST":
            cat_id = request.form.get("category_id", type=int)
            title = (request.form.get("title") or "").strip()
            body = (request.form.get("body") or "").strip()
            cat = ForumCategory.query.get(cat_id) if cat_id else None
            if not cat or not title or not body:
                flash("Category, title, and body are required.", "error")
                return render_template(
                    "forum_new_topic.html", categories=cats, error=True,
                )
            base = slugify(title)[:80] or "topic"
            slug = f"{cat.slug}-{base}-{int(datetime.utcnow().timestamp())}"
            topic = ForumTopic(
                category_id=cat.id, user_id=current_user.id,
                slug=slug, title=title, body=body,
                created_at=datetime.utcnow(),
            )
            db.session.add(topic)
            cat.topic_count = (cat.topic_count or 0) + 1
            db.session.commit()
            flash("Topic posted.", "success")
            return redirect(url_for("forum_topic", topic_id=topic.id))
        return render_template("forum_new_topic.html", categories=cats)

    @app.route("/forum/topic/<int:topic_id>/reply", methods=["POST"])
    def forum_reply(topic_id):
        topic = ForumTopic.query.get_or_404(topic_id)
        body = (request.form.get("body") or "").strip()
        if not body:
            flash("Reply body cannot be empty.", "error")
            return redirect(url_for("forum_topic", topic_id=topic.id))
        post = ForumPost(
            topic_id=topic.id, user_id=current_user.id, body=body,
            created_at=datetime.utcnow(),
        )
        db.session.add(post)
        topic.reply_count = (topic.reply_count or 0) + 1
        db.session.commit()
        flash("Reply posted.", "success")
        return redirect(url_for("forum_topic", topic_id=topic.id))

    @app.route("/forum/post/<int:post_id>/helpful", methods=["POST"])
    def forum_post_helpful(post_id):
        post = ForumPost.query.get_or_404(post_id)
        post.helpful_count = (post.helpful_count or 0) + 1
        db.session.commit()
        return redirect(url_for("forum_topic", topic_id=post.topic_id))

    @app.route("/forum/topic/<int:topic_id>/delete", methods=["POST"])
    def forum_topic_delete(topic_id):
        topic = ForumTopic.query.get_or_404(topic_id)
        if topic.user_id != current_user.id:
            abort(403)
        ForumPost.query.filter_by(topic_id=topic.id).delete()
        cat_id = topic.category_id
        db.session.delete(topic)
        cat = ForumCategory.query.get(cat_id)
        if cat:
            cat.topic_count = ForumTopic.query.filter_by(category_id=cat.id).count()
        db.session.commit()
        flash("Topic deleted.", "success")
        return redirect(url_for("forum_index"))

    # ------------------------------------------------------------------
    # Routes — Refill reminders
    # ------------------------------------------------------------------
    @app.route("/myaccount")
    @app.route("/myaccount/")
    def myaccount_hub():
        reminders = (
            RefillReminder.query.filter_by(user_id=current_user.id)
            .order_by(RefillReminder.next_refill_at).all()
        )
        topics = (
            ForumTopic.query.filter_by(user_id=current_user.id)
            .order_by(ForumTopic.created_at.desc()).limit(5).all()
        )
        reviews = (
            DrugReview.query.filter_by(user_id=current_user.id)
            .order_by(DrugReview.created_at.desc()).limit(5).all()
        )
        return render_template(
            "myaccount_hub.html",
            reminders=reminders, my_topics=topics, my_reviews=reviews,
        )

    @app.route("/myaccount/medications")
    @app.route("/myaccount/medications/")
    def myaccount_medications():
        from app import SavedDrug  # avoid circular
        saved = (
            SavedDrug.query.filter_by(user_id=current_user.id)
            .order_by(SavedDrug.id).all()
        )
        return render_template("myaccount_medications.html", saved=saved)

    @app.route("/myaccount/refill-reminders")
    @app.route("/myaccount/refill-reminders/")
    def refill_reminders():
        reminders = (
            RefillReminder.query.filter_by(user_id=current_user.id)
            .order_by(RefillReminder.next_refill_at).all()
        )
        return render_template("refill_reminders.html", reminders=reminders)

    @app.route("/myaccount/refill-reminders/new", methods=["GET", "POST"])
    def refill_reminder_new():
        from app import SavedDrug
        if request.method == "POST":
            drug_id = request.form.get("drug_id", type=int)
            days_supply = request.form.get("days_supply", type=int) or 30
            frequency = request.form.get("frequency") or "daily"
            pharmacy_id = request.form.get("pharmacy_id", type=int)
            next_offset = request.form.get("days_until_refill", type=int) or 30
            drug = Drug.query.get(drug_id) if drug_id else None
            if not drug:
                flash("Pick a medication.", "error")
                drugs = (
                    SavedDrug.query.filter_by(user_id=current_user.id).all()
                )
                pharms = Pharmacy.query.order_by(Pharmacy.name).all()
                return render_template(
                    "refill_reminder_new.html",
                    saved_drugs=[s.drug for s in drugs],
                    pharmacies=pharms, error=True,
                )
            db.session.add(RefillReminder(
                user_id=current_user.id, drug_id=drug.id,
                days_supply=days_supply, frequency=frequency,
                pharmacy_id=pharmacy_id,
                next_refill_at=datetime.utcnow() + timedelta(days=next_offset),
                created_at=datetime.utcnow(),
            ))
            db.session.commit()
            flash(f"Refill reminder set for {drug.generic_name}.", "success")
            return redirect(url_for("refill_reminders"))
        drugs = SavedDrug.query.filter_by(user_id=current_user.id).all()
        pharms = Pharmacy.query.order_by(Pharmacy.name).all()
        return render_template(
            "refill_reminder_new.html",
            saved_drugs=[s.drug for s in drugs], pharmacies=pharms,
        )

    @app.route("/myaccount/refill-reminders/<int:rid>/delete", methods=["POST"])
    def refill_reminder_delete(rid):
        r = RefillReminder.query.get_or_404(rid)
        if r.user_id != current_user.id:
            abort(403)
        drug_name = r.drug.generic_name if r.drug else "reminder"
        db.session.delete(r)
        db.session.commit()
        flash(f"Refill reminder for {drug_name} removed.", "success")
        return redirect(url_for("refill_reminders"))

    @app.route("/myaccount/refill-reminders/<int:rid>/edit", methods=["GET", "POST"])
    def refill_reminder_edit(rid):
        r = RefillReminder.query.get_or_404(rid)
        if r.user_id != current_user.id:
            abort(403)
        if request.method == "POST":
            r.days_supply = request.form.get("days_supply", type=int) or r.days_supply
            r.frequency = request.form.get("frequency") or r.frequency
            r.pharmacy_id = request.form.get("pharmacy_id", type=int)
            offset = request.form.get("days_until_refill", type=int)
            if offset is not None:
                r.next_refill_at = datetime.utcnow() + timedelta(days=offset)
            db.session.commit()
            flash("Refill reminder updated.", "success")
            return redirect(url_for("refill_reminders"))
        pharms = Pharmacy.query.order_by(Pharmacy.name).all()
        return render_template("refill_reminder_edit.html", reminder=r, pharmacies=pharms)

    # ------------------------------------------------------------------
    # Routes — Recalls
    # ------------------------------------------------------------------
    @app.route("/recalls")
    @app.route("/recalls/")
    @app.route("/recalls.html")
    def recalls_index():
        severity = request.args.get("severity")
        q = DrugRecall.query
        if severity:
            q = q.filter(DrugRecall.severity == severity)
        recalls = q.order_by(DrugRecall.recalled_at.desc()).all()
        return render_template("recalls_index.html", recalls=recalls, active_severity=severity)

    @app.route("/recalls/<slug>")
    @app.route("/recalls/<slug>.html")
    def recall_detail(slug):
        recall = DrugRecall.query.filter_by(slug=slug).first_or_404()
        return render_template("recall_detail.html", recall=recall)

    @app.route("/recalls/subscribe", methods=["POST"])
    def recalls_subscribe():
        email = (request.form.get("email") or "").strip()
        if not email or "@" not in email:
            flash("Please provide a valid email address.", "error")
            return redirect(url_for("recalls_index"))
        flash(f"Subscribed {email} to drug recall alerts.", "success")
        return redirect(url_for("recalls_index"))

    # ------------------------------------------------------------------
    # Routes — Pharmacy finder
    # ------------------------------------------------------------------
    @app.route("/pharmacy")
    @app.route("/pharmacy/")
    @app.route("/pharmacies")
    @app.route("/find-pharmacy")
    def pharmacy_finder():
        zip_code = (request.args.get("zip") or "").strip()
        chain = request.args.get("chain") or ""
        q = Pharmacy.query
        if zip_code:
            q = q.filter(Pharmacy.zip_code.like(f"{zip_code[:3]}%"))
        if chain:
            q = q.filter(Pharmacy.chain == chain)
        pharms = q.order_by(Pharmacy.name).all()
        chains = sorted({p.chain for p in Pharmacy.query.all() if p.chain})
        return render_template(
            "pharmacy_finder.html",
            pharmacies=pharms, chains=chains,
            active_zip=zip_code, active_chain=chain,
        )

    @app.route("/pharmacy/<slug>")
    @app.route("/pharmacy/<slug>.html")
    def pharmacy_detail(slug):
        p = Pharmacy.query.filter_by(slug=slug).first_or_404()
        return render_template("pharmacy_detail.html", pharmacy=p)

    @app.route("/contact-pharmacist", methods=["GET", "POST"])
    @app.route("/pharmacist-on-call", methods=["GET", "POST"])
    def contact_pharmacist():
        if request.method == "POST":
            topic = (request.form.get("topic") or "").strip()
            body = (request.form.get("body") or "").strip()
            name = (request.form.get("name") or "").strip() or "Anonymous"
            if not topic or not body:
                flash("Topic and message are required.", "error")
                return render_template(
                    "contact_pharmacist.html", error=True,
                )
            db.session.add(ContactPharmacistMsg(
                user_id=(current_user.id if current_user.is_authenticated else None),
                pharmacist_name=name, topic=topic, body=body,
                created_at=datetime.utcnow(),
            ))
            db.session.commit()
            flash("Your question has been sent. A pharmacist will reply within 24 hours.", "success")
            return redirect(url_for("contact_pharmacist"))
        return render_template("contact_pharmacist.html")

    # ------------------------------------------------------------------
    # Routes — Side effect reports
    # ------------------------------------------------------------------
    @app.route("/report-side-effect", methods=["GET", "POST"])
    @app.route("/report-side-effect.html", methods=["GET", "POST"])
    def report_side_effect():
        drugs = Drug.query.order_by(Drug.generic_name).all()
        if request.method == "POST":
            drug_id = request.form.get("drug_id", type=int)
            severity = request.form.get("severity") or "mild"
            body = (request.form.get("body") or "").strip()
            drug = Drug.query.get(drug_id) if drug_id else None
            if not drug or not body:
                flash("Pick a drug and describe the side effect.", "error")
                return render_template(
                    "report_side_effect.html", drugs=drugs, error=True,
                )
            db.session.add(SideEffectReport(
                drug_id=drug.id, user_id=current_user.id,
                severity=severity, body=body,
                created_at=datetime.utcnow(),
            ))
            db.session.commit()
            flash("Thank you. Your report has been recorded.", "success")
            return redirect(url_for("report_side_effect_thanks"))
        return render_template("report_side_effect.html", drugs=drugs)

    @app.route("/report-side-effect/thanks")
    def report_side_effect_thanks():
        return render_template("report_side_effect_thanks.html")

    @app.route("/side-effects/reports")
    @app.route("/side-effects/reports.html")
    def side_effect_reports():
        reports = (
            SideEffectReport.query.order_by(SideEffectReport.created_at.desc())
            .limit(50).all()
        )
        return render_template("side_effect_reports.html", reports=reports)

    # ------------------------------------------------------------------
    # Routes — Health news (separate from news)
    # ------------------------------------------------------------------
    @app.route("/health-news")
    @app.route("/health-news/")
    @app.route("/health-news.html")
    def health_news_index():
        cat = request.args.get("category")
        q = HealthNews.query
        if cat:
            q = q.filter(HealthNews.category == cat)
        articles = q.order_by(HealthNews.published_at.desc()).all()
        categories = sorted({a.category for a in HealthNews.query.all() if a.category})
        return render_template(
            "health_news_index.html",
            articles=articles, categories=categories, active_cat=cat,
        )

    @app.route("/health-news/<slug>")
    @app.route("/health-news/<slug>.html")
    def health_news_article(slug):
        a = HealthNews.query.filter_by(slug=slug).first_or_404()
        related = (
            HealthNews.query.filter(
                HealthNews.category == a.category, HealthNews.id != a.id
            )
            .order_by(HealthNews.published_at.desc()).limit(5).all()
        )
        return render_template(
            "health_news_article.html", article=a, related=related,
        )

    # ------------------------------------------------------------------
    # Routes — Dosage calculator
    # ------------------------------------------------------------------
    @app.route("/dosage-calculator")
    @app.route("/dosage-calculator/")
    @app.route("/dosage-calculator.html")
    def dosage_calculator_index():
        drugs = (
            Drug.query.filter(
                Drug.generic_name.in_([
                    "acetaminophen", "ibuprofen", "amoxicillin", "warfarin",
                    "levothyroxine", "metformin", "atorvastatin", "lisinopril",
                    "sertraline", "gabapentin", "prednisone", "azithromycin",
                ])
            ).order_by(Drug.generic_name).all()
        )
        return render_template("dosage_calculator_index.html", drugs=drugs)

    @app.route("/dosage-calculator/<slug>", methods=["GET", "POST"])
    @app.route("/dosage-calculator/<slug>.html", methods=["GET", "POST"])
    def dosage_calculator(slug):
        drug = Drug.query.filter_by(slug=slug).first_or_404()
        result = None
        if request.method == "POST":
            try:
                weight = float(request.form.get("weight_kg") or 0)
                age = int(request.form.get("age_years") or 0)
                indication = request.form.get("indication") or "general"
            except (TypeError, ValueError):
                weight, age, indication = 0.0, 0, "general"
            # Simple per-kg dosing approximation for benchmark purposes.
            per_kg = {
                "acetaminophen": 15.0, "ibuprofen": 10.0,
                "amoxicillin": 25.0, "warfarin": 0.1, "levothyroxine": 0.0017,
                "metformin": 20.0, "atorvastatin": 0.3, "lisinopril": 0.1,
                "sertraline": 0.7, "gabapentin": 30.0, "prednisone": 1.0,
                "azithromycin": 10.0,
            }.get(slug, 5.0)
            mg = round(weight * per_kg, 2)
            result = {
                "mg_per_dose": mg,
                "doses_per_day": 3 if slug in ("amoxicillin", "ibuprofen") else 2,
                "weight_kg": weight, "age_years": age,
                "indication": indication,
            }
            db.session.add(DosageCalculation(
                user_id=(current_user.id if current_user.is_authenticated else None),
                drug_id=drug.id, weight_kg=weight, age_years=age,
                result_mg=mg, created_at=datetime.utcnow(),
            ))
            db.session.commit()
        return render_template("dosage_calculator.html", drug=drug, result=result)

    @app.route("/dosage-calculator/<slug>/save", methods=["POST"])
    def dosage_calculator_save(slug):
        drug = Drug.query.filter_by(slug=slug).first_or_404()
        try:
            weight = float(request.form.get("weight_kg") or 0)
            age = int(request.form.get("age_years") or 0)
            mg = float(request.form.get("result_mg") or 0)
        except (TypeError, ValueError):
            flash("Invalid input.", "error")
            return redirect(url_for("dosage_calculator", slug=slug))
        db.session.add(DosageCalculation(
            user_id=(current_user.id if current_user.is_authenticated else None),
            drug_id=drug.id, weight_kg=weight, age_years=age,
            result_mg=mg, created_at=datetime.utcnow(),
        ))
        db.session.commit()
        flash("Dose calculation saved to your profile.", "success")
        return redirect(url_for("dosage_calculator", slug=slug))

    # ------------------------------------------------------------------
    # Routes — Condition drugs / breastfeeding / comparison
    # ------------------------------------------------------------------
    @app.route("/condition/<slug>/drugs")
    @app.route("/condition/<slug>/drugs.html")
    def condition_drugs(slug):
        from app import DrugCondition
        cond = Condition.query.filter_by(slug=slug).first_or_404()
        drug_ids = [
            dc.drug_id for dc in DrugCondition.query.filter_by(condition_id=cond.id).all()
        ]
        drugs = (
            Drug.query.filter(Drug.id.in_(drug_ids))
            .order_by(Drug.avg_rating.desc().nullslast(), Drug.generic_name)
            .all()
        )
        return render_template(
            "condition_drugs.html", condition=cond, drugs=drugs, total=len(drugs),
        )

    @app.route("/breastfeeding/<slug>")
    @app.route("/breastfeeding/<slug>.html")
    @app.route("/<slug>/breastfeeding")
    @app.route("/<slug>/breastfeeding.html")
    def drug_breastfeeding(slug):
        drug = Drug.query.filter_by(slug=slug).first_or_404()
        # Categories derived from pregnancy_risk for benchmark coherence.
        risk = drug.pregnancy_risk or ""
        cat = "L3 - Moderately safe"  # default
        if any(s in risk.upper() for s in ("CATEGORY A", " A ")):
            cat = "L1 - Safest"
        elif "CATEGORY B" in risk.upper() or risk.upper().startswith("B"):
            cat = "L2 - Safer"
        elif "CATEGORY D" in risk.upper() or risk.upper().startswith("D"):
            cat = "L4 - Possibly hazardous"
        elif "CATEGORY X" in risk.upper() or risk.upper().startswith("X"):
            cat = "L5 - Contraindicated"
        return render_template(
            "drug_breastfeeding.html", drug=drug, lactation_category=cat,
        )

    @app.route("/comparison/<drug_a_slug>-vs-<drug_b_slug>")
    @app.route("/comparison/<drug_a_slug>-vs-<drug_b_slug>.html")
    def drug_comparison(drug_a_slug, drug_b_slug):
        a = Drug.query.filter_by(slug=drug_a_slug).first_or_404()
        b = Drug.query.filter_by(slug=drug_b_slug).first_or_404()
        return render_template("drug_comparison.html", drug_a=a, drug_b=b)

    @app.route("/comparison/save", methods=["POST"])
    def comparison_save():
        a_slug = request.form.get("drug_a_slug") or ""
        b_slug = request.form.get("drug_b_slug") or ""
        note = (request.form.get("note") or "").strip()
        a = Drug.query.filter_by(slug=a_slug).first()
        b = Drug.query.filter_by(slug=b_slug).first()
        if not a or not b:
            flash("Could not save — pick two valid drugs.", "error")
            return redirect(url_for("compare_drugs"))
        db.session.add(SavedComparison(
            user_id=current_user.id, drug_a_id=a.id, drug_b_id=b.id,
            note=note, created_at=datetime.utcnow(),
        ))
        db.session.commit()
        flash(f"Saved comparison: {a.generic_name} vs {b.generic_name}.", "success")
        return redirect(url_for("myaccount_hub"))

    # ------------------------------------------------------------------
    # Routes — Pill identifier wizard (multi-step)
    # ------------------------------------------------------------------
    @app.route("/pill-identifier/wizard")
    @app.route("/pill-identifier/wizard/")
    @app.route("/pill-identifier/wizard.html")
    def pill_id_wizard():
        return render_template("pill_id_wizard_step1.html")

    @app.route("/pill-identifier/wizard/step2", methods=["POST"])
    def pill_id_wizard_step2():
        from app import DrugImage
        imprint = (request.form.get("imprint") or "").strip()
        candidates = (
            DrugImage.query.filter(DrugImage.imprint.like(f"%{imprint}%")).limit(60).all()
            if imprint else []
        )
        shapes = sorted({c.shape for c in candidates if c.shape})
        return render_template(
            "pill_id_wizard_step2.html",
            imprint=imprint, candidates=candidates, shapes=shapes,
        )

    @app.route("/pill-identifier/wizard/step3", methods=["POST"])
    def pill_id_wizard_step3():
        from app import DrugImage
        imprint = (request.form.get("imprint") or "").strip()
        shape = (request.form.get("shape") or "").strip()
        q = DrugImage.query
        if imprint:
            q = q.filter(DrugImage.imprint.like(f"%{imprint}%"))
        if shape:
            q = q.filter(DrugImage.shape == shape)
        candidates = q.limit(60).all()
        colors = sorted({c.color for c in candidates if c.color})
        return render_template(
            "pill_id_wizard_step3.html",
            imprint=imprint, shape=shape,
            candidates=candidates, colors=colors,
        )

    @app.route("/pill-identifier/wizard/finish", methods=["POST"])
    def pill_id_wizard_finish():
        from app import DrugImage
        imprint = (request.form.get("imprint") or "").strip()
        shape = (request.form.get("shape") or "").strip()
        color = (request.form.get("color") or "").strip()
        q = DrugImage.query
        if imprint:
            q = q.filter(DrugImage.imprint.like(f"%{imprint}%"))
        if shape:
            q = q.filter(DrugImage.shape == shape)
        if color:
            q = q.filter(DrugImage.color == color)
        candidates = q.limit(40).all()
        # Group by drug
        seen = []
        for c in candidates:
            if c.drug and c.drug.slug not in [s.slug for s in seen]:
                seen.append(c.drug)
        return render_template(
            "pill_id_wizard_finish.html",
            imprint=imprint, shape=shape, color=color,
            candidates=candidates, matched_drugs=seen,
        )

    # ------------------------------------------------------------------
    # Routes — Save / unsave medication helpers
    # ------------------------------------------------------------------
    @app.route("/<slug>/save-medication", methods=["POST"])
    def save_medication(slug):
        from app import SavedDrug
        drug = Drug.query.filter_by(slug=slug).first_or_404()
        existing = SavedDrug.query.filter_by(
            user_id=current_user.id, drug_id=drug.id
        ).first()
        if existing:
            flash(f"{drug.generic_name} is already on your med list.", "info")
        else:
            db.session.add(SavedDrug(
                user_id=current_user.id, drug_id=drug.id,
                created_at=datetime.utcnow(),
            ))
            db.session.commit()
            flash(f"{drug.generic_name} added to your med list.", "success")
        return redirect(url_for("drug_detail", slug=drug.slug))

    @app.route("/myaccount/medications/<int:saved_id>/remove", methods=["POST"])
    def myaccount_med_remove(saved_id):
        from app import SavedDrug
        sd = SavedDrug.query.get_or_404(saved_id)
        if sd.user_id != current_user.id:
            abort(403)
        name = sd.drug.generic_name if sd.drug else "medication"
        db.session.delete(sd)
        db.session.commit()
        flash(f"{name} removed from your med list.", "success")
        return redirect(url_for("myaccount_medications"))
