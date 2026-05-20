#!/usr/bin/env python3
"""Validate a structured task spec against WebHarbor DB oracle predicates."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from structured_task_runtime import load_site_app


_APP_CACHE: dict[str, Any] = {}


def _fail(message: str) -> None:
    raise SystemExit(message)


def _eq(actual: Any, expected: Any, field: str, reasons: list[str]) -> None:
    if expected is None:
        return
    if isinstance(actual, float) or isinstance(expected, float):
        try:
            if abs(float(actual) - float(expected)) <= 1e-9:
                return
        except Exception:
            pass
    if actual != expected:
        reasons.append(f"{field}!={expected!r} (actual {actual!r})")


def _load(site: str):
    if site not in _APP_CACHE:
        _APP_CACHE[site] = load_site_app(site, fresh_instance=True).module
    return _APP_CACHE[site]



def _expected_identity(spec: dict[str, Any]) -> str | None:
    value = spec.get("expected_answer", {}).get("identity")
    return str(value) if value is not None else None


def _assert_identity(spec: dict[str, Any], actual: Any) -> None:
    expected = _expected_identity(spec)
    if expected is not None and str(actual) != expected:
        _fail(f"identity mismatch: expected {expected!r}, DB target is {actual!r}")


def _is_identify(spec: dict[str, Any]) -> bool:
    return spec.get("validation", {}).get("answer_kind") == "entity_identity"


def _assert_unique_count(site: str, count: int, identity: str) -> None:
    if count != 1:
        _fail(f"{site} identify constraints are not unique for {identity!r}: matched {count} rows")


def _generic_entity_validate(site: str, model_name: str, lookup: dict[str, Any], spec: dict[str, Any], field_map: dict[str, str]) -> None:
    app = _load(site)
    constraints = spec.get("constraints", {})
    expected = spec.get("expected_answer", {})
    with app.app.app_context():
        model = getattr(app, model_name)
        q = model.query
        for field, value in lookup.items():
            q = q.filter(getattr(model, field) == value)
        obj = q.first()
        if obj is None:
            _fail(f"{site} {model_name} not found for {lookup}")
        identity_attr = {"Recipe": "title", "Team": "full_name", "Repository": "full_name"}.get(model_name)
        if identity_attr:
            _assert_identity(spec, getattr(obj, identity_attr))
        reasons: list[str] = []
        for expected_field, attr in field_map.items():
            if expected_field in expected:
                _eq(getattr(obj, attr), expected[expected_field], expected_field, reasons)
        if _is_identify(spec):
            q_unique = model.query
            matched_fields = 0
            for constraint_field, attr in field_map.items():
                if constraint_field in constraints and hasattr(model, attr):
                    q_unique = q_unique.filter(getattr(model, attr) == constraints[constraint_field])
                    matched_fields += 1
            if matched_fields:
                identity = str(getattr(obj, identity_attr)) if identity_attr else repr(lookup)
                _assert_unique_count(site, q_unique.count(), identity)
        # Common optional constraint checks.
        if "min_rating" in constraints and hasattr(obj, "rating") and obj.rating < float(constraints["min_rating"]):
            reasons.append(f"rating<{constraints['min_rating']}")
        if "min_rating" in constraints and hasattr(obj, "avg_rating") and obj.avg_rating < float(constraints["min_rating"]):
            reasons.append(f"avg_rating<{constraints['min_rating']}")
        if reasons:
            _fail(f"{site} target does not satisfy constraints: {', '.join(reasons)}")


def _allrecipes_validate(spec: dict[str, Any]) -> None:
    target = spec.get("target_entity", {})
    _generic_entity_validate("allrecipes", "Recipe", {"slug": target.get("slug")}, spec, {
        "title": "title",
        "rating": "avg_rating",
        "review_count": "review_count",
        "total_time": "total_time",
        "servings": "servings",
        "calories": "calories",
        "author": "author_name",
    })


def _amazon_validate(spec: dict[str, Any]) -> None:
    target = spec.get("target_entity", {})
    app = _load("amazon")
    c = spec.get("constraints", {})
    e = spec.get("expected_answer", {})
    with app.app.app_context():
        p = app.Product.query.filter_by(slug=target.get("slug")).first()
        if p is None:
            _fail("Amazon product not found")
        _assert_identity(spec, p.name)
        reasons: list[str] = []
        for k, attr in {"product_name": "name", "brand": "brand", "category": "category_slug", "price": "price", "rating": "rating", "review_count": "review_count", "condition": "condition", "free_shipping": "free_shipping", "free_returns": "free_returns"}.items():
            _eq(getattr(p, attr), e.get(k), k, reasons)
        if c.get("prime") and not p.is_prime:
            reasons.append("prime")
        if c.get("free_shipping") and not p.free_shipping:
            reasons.append("free_shipping")
        if c.get("brand") and p.brand != c["brand"]:
            reasons.append("brand")
        if _is_identify(spec):
            q = app.Product.query
            field_map = {
                "brand": "brand",
                "category": "category_slug",
                "price": "price",
                "rating": "rating",
                "review_count": "review_count",
                "condition": "condition",
                "free_shipping": "free_shipping",
                "free_returns": "free_returns",
            }
            for key, attr in field_map.items():
                if key in c:
                    q = q.filter(getattr(app.Product, attr) == c[key])
            _assert_unique_count("amazon", q.count(), p.name)
        if reasons:
            _fail(f"Amazon product does not satisfy constraints: {', '.join(reasons)}")


def _apple_validate(spec: dict[str, Any]) -> None:
    target = spec.get("target_entity", {})
    app = _load("apple")
    e = spec.get("expected_answer", {})
    with app.app.app_context():
        p = app.Product.query.filter_by(slug=target.get("slug")).first()
        if p is None:
            _fail("Apple product not found")
        _assert_identity(spec, p.name)
        specs = json.loads(p.specs or "{}")
        reasons: list[str] = []
        checks = {
            "product_name": p.name,
            "category": p.category,
            "subtitle": p.subtitle,
            "price": p.price,
            "monthly_price": p.monthly_price,
            "display": specs.get("display", ""),
            "chip": specs.get("chip", p.chip_family or ""),
            "in_stock": p.in_stock,
        }
        for k, actual in checks.items():
            _eq(actual, e.get(k), k, reasons)
        if _is_identify(spec):
            q = app.Product.query
            for key, attr in {"category": "category", "subtitle": "subtitle", "price": "price",
                              "monthly_price": "monthly_price", "in_stock": "in_stock"}.items():
                if key in spec.get("constraints", {}):
                    q = q.filter(getattr(app.Product, attr) == spec["constraints"][key])
            _assert_unique_count("apple", q.count(), p.name)
        if reasons:
            _fail(f"Apple product does not satisfy constraints: {', '.join(reasons)}")


def _arxiv_validate(spec: dict[str, Any]) -> None:
    target = spec.get("target_entity", {})
    app = _load("arxiv")
    e = spec.get("expected_answer", {})
    with app.app.app_context():
        p = app.Paper.query.filter_by(arxiv_id=target.get("arxiv_id")).first()
        if p is None:
            _fail("arXiv paper not found")
        _assert_identity(spec, p.title)
        authors = json.loads(p.authors_json or "[]")
        checks = {"arxiv_id": p.arxiv_id, "title": p.title, "primary_subject": p.primary_subject,
                  "submitted_date": p.submitted_date, "author_count": p.n_authors,
                  "first_author": authors[0] if authors else ""}
        reasons: list[str] = []
        for k, actual in checks.items():
            _eq(actual, e.get(k), k, reasons)
        if _is_identify(spec):
            c = spec.get("constraints", {})
            q = app.Paper.query
            for key, attr in {"primary_subject": "primary_subject", "submitted_date": "submitted_date",
                              "author_count": "n_authors"}.items():
                if key in c:
                    q = q.filter(getattr(app.Paper, attr) == c[key])
            if "first_author" in c:
                q = q.filter(app.Paper.authors_json.like(f'%"{c["first_author"]}"%'))
            _assert_unique_count("arxiv", q.count(), p.title)
        if reasons:
            _fail(f"arXiv paper does not satisfy constraints: {', '.join(reasons)}")


def _booking_validate(spec: dict[str, Any]) -> None:
    app = _load("booking")
    constraints = spec.get("constraints", {})
    expected = spec.get("expected_answer", {})
    target = spec.get("target_entity", {})
    target_name = target.get("name") or expected.get("property_name")
    if not target_name:
        _fail("missing Booking target property name")

    with app.app.app_context():
        prop = app.Property.query.filter_by(name=target_name).first()
        if prop is None:
            _fail(f"Booking property {target_name!r} not found")
        _assert_identity(spec, prop.name)
        city_name = constraints.get("city")
        if city_name and (prop.city is None or prop.city.display.lower() != str(city_name).lower()):
            _fail(f"{prop.name} does not satisfy city={city_name!r}")

        reasons = []
        amenities = set(constraints.get("amenities", []))
        if "breakfast_included" in amenities and not prop.breakfast_included:
            reasons.append("breakfast_included")
        if "free_wifi" in amenities and not prop.has_wifi:
            reasons.append("free_wifi")
        min_rating = constraints.get("min_rating")
        if min_rating is not None and prop.rating < float(min_rating):
            reasons.append(f"rating<{min_rating}")
        min_price = constraints.get("min_price")
        if min_price is not None and prop.price_per_night < float(min_price):
            reasons.append(f"price<{min_price}")
        max_price = constraints.get("max_price")
        if max_price is not None and prop.price_per_night > float(max_price):
            reasons.append(f"price>{max_price}")
        verified_field = constraints.get("verified_field")
        if verified_field and not hasattr(prop, str(verified_field)):
            reasons.append(f"missing verified field {verified_field}")
        expected_brand = expected.get("brand") or target.get("brand")
        if expected_brand is not None and prop.brand != expected_brand:
            reasons.append(f"brand!={expected_brand}")
        if _is_identify(spec):
            q = app.Property.query
            if city_name:
                q = q.join(app.City).filter(app.City.display == city_name)
            for key, attr in {"rating": "rating", "review_count": "review_count", "nightly_price": "price_per_night",
                              "stars": "stars", "property_type": "property_type",
                              "distance_from_center_km": "distance_from_center", "brand": "brand"}.items():
                if key in constraints:
                    q = q.filter(getattr(app.Property, attr) == constraints[key])
            amenities_unique = set(constraints.get("amenities", []))
            if "breakfast_included" in amenities_unique:
                q = q.filter(app.Property.breakfast_included.is_(True))
            if "free_wifi" in amenities_unique:
                q = q.filter(app.Property.has_wifi.is_(True))
            _assert_unique_count("booking", q.count(), prop.name)
        if reasons:
            _fail(f"Booking property {prop.name!r} does not satisfy constraints: {', '.join(reasons)}")


def _cambridge_dictionary_validate(spec: dict[str, Any]) -> None:
    target = spec.get("target_entity", {})
    app = _load("cambridge_dictionary")
    e = spec.get("expected_answer", {})
    with app.app.app_context():
        w = app.Word.query.filter_by(slug=target.get("slug")).first()
        if w is None:
            _fail("Cambridge word not found")
        _assert_identity(spec, w.headword)
        defs = json.loads(w.definitions_json or "[]")
        checks = {"headword": w.headword, "part_of_speech": w.pos, "level": w.level,
                  "uk_phonetic": w.phonetic_uk, "us_phonetic": w.phonetic_us,
                  "first_definition": defs[0]["definition"] if defs else ""}
        reasons: list[str] = []
        for k, actual in checks.items():
            _eq(actual, e.get(k), k, reasons)
        if _is_identify(spec):
            c = spec.get("constraints", {})
            q = app.Word.query
            for key, attr in {"part_of_speech": "pos", "level": "level", "uk_phonetic": "phonetic_uk",
                              "us_phonetic": "phonetic_us"}.items():
                if key in c:
                    q = q.filter(getattr(app.Word, attr) == c[key])
            if "first_definition" in c:
                q = q.filter(app.Word.definitions_json.like(f'%{c["first_definition"]}%'))
            _assert_unique_count("cambridge_dictionary", q.count(), w.headword)
        if reasons:
            _fail(f"Cambridge word does not satisfy constraints: {', '.join(reasons)}")


def _coursera_validate(spec: dict[str, Any]) -> None:
    target = spec.get("target_entity", {})
    app = _load("coursera")
    e = spec.get("expected_answer", {})
    with app.app.app_context():
        c = app.Course.query.filter_by(slug=target.get("slug")).first()
        if c is None:
            _fail("Coursera course not found")
        _assert_identity(spec, c.title)
        partner = c.partner.name if getattr(c, "partner", None) else ""
        checks = {"course_title": c.title, "partner": partner, "level": c.level, "rating": c.rating,
                  "review_count": c.review_count, "duration": c.duration_text, "instructor": c.instructor,
                  "certificate": c.has_certificate}
        reasons: list[str] = []
        for k, actual in checks.items():
            _eq(actual, e.get(k), k, reasons)
        if _is_identify(spec):
            cst = spec.get("constraints", {})
            q = app.Course.query
            for key, attr in {"level": "level", "rating": "rating", "review_count": "review_count",
                              "duration": "duration_text", "instructor": "instructor",
                              "certificate": "has_certificate"}.items():
                if key in cst:
                    q = q.filter(getattr(app.Course, attr) == cst[key])
            if "partner" in cst:
                q = q.join(app.Partner).filter(app.Partner.name == cst["partner"])
            _assert_unique_count("coursera", q.count(), c.title)
        if reasons:
            _fail(f"Coursera course does not satisfy constraints: {', '.join(reasons)}")


def _espn_validate(spec: dict[str, Any]) -> None:
    target = spec.get("target_entity", {})
    _generic_entity_validate("espn", "Team", {"slug": target.get("slug")}, spec, {
        "team": "full_name", "sport": "sport_slug", "abbreviation": "abbreviation", "wins": "wins",
        "losses": "losses", "win_pct": "win_pct", "standing_rank": "standing_rank", "streak": "streak",
    })


def _github_validate(spec: dict[str, Any]) -> None:
    target = spec.get("target_entity", {})
    _generic_entity_validate("github", "Repository", {"full_name": target.get("full_name")}, spec, {
        "repository": "full_name", "description": "description", "language": "language", "license": "license",
        "stars": "stars_count", "forks": "forks_count", "open_issues": "open_issues_count", "default_branch": "default_branch",
    })


def _google_flights_validate(spec: dict[str, Any]) -> None:
    app = _load("google_flights")
    constraints = spec.get("constraints", {})
    expected = spec.get("expected_answer", {})
    flight_number = spec.get("target_entity", {}).get("flight_number") or expected.get("flight_number")
    if not flight_number:
        _fail("missing Google Flights target flight_number")

    with app.app.app_context():
        origin = app.Airport.query.filter_by(iata=str(constraints.get("origin", "")).upper()).first()
        dest = app.Airport.query.filter_by(iata=str(constraints.get("destination", "")).upper()).first()
        if origin is None or dest is None:
            _fail("Google Flights origin/destination constraint did not resolve")
        depart = constraints.get("depart") or constraints.get("departure_date")
        dep_d = datetime.strptime(depart, "%Y-%m-%d").date() if depart else None

        candidates = app.Flight.query.filter(app.Flight.origin_id == origin.id, app.Flight.destination_id == dest.id)
        if dep_d is not None:
            candidates = candidates.filter(app.db.func.strftime("%m-%d", app.Flight.departure_date) == f"{dep_d.month:02d}-{dep_d.day:02d}")
        if constraints.get("sort") == "price":
            candidates = candidates.order_by(app.Flight.price.asc(), app.Flight.duration_minutes.asc(), app.Flight.id.asc())
        rows = candidates.all()
        if not rows:
            _fail("Google Flights constraints produced no candidates")
        flight = next((f for f in rows if f.flight_number == flight_number), None)
        if flight is None:
            _fail(f"Google Flights flight {flight_number!r} does not satisfy route/date constraints")
        _assert_identity(spec, flight.flight_number)
        if constraints.get("sort") == "price" and rows[0].flight_number != flight_number:
            _fail(f"Google Flights flight {flight_number!r} is not the cheapest matching flight")
        if expected.get("price") is not None and float(expected["price"]) != float(flight.price):
            _fail(f"Google Flights price mismatch for {flight_number!r}")
        if _is_identify(spec):
            q = candidates
            duration = constraints.get("duration")
            if duration:
                hours = minutes = 0
                parts = str(duration).replace("h", "h ").replace("m", "m ").split()
                for i, part in enumerate(parts):
                    if part == "h" and i > 0:
                        hours = int(parts[i - 1])
                    elif part == "m" and i > 0:
                        minutes = int(parts[i - 1])
                    elif part.endswith("h"):
                        hours = int(part[:-1])
                    elif part.endswith("m"):
                        minutes = int(part[:-1])
                q = q.filter(app.Flight.duration_minutes == hours * 60 + minutes)
            for key, attr in {"airline": "airline", "departure_time": "departure_time", "arrival_time": "arrival_time",
                              "stops": "stops", "price": "price",
                              "aircraft": "aircraft"}.items():
                if key in constraints:
                    q = q.filter(getattr(app.Flight, attr) == constraints[key])
            _assert_unique_count("google_flights", q.count(), flight.flight_number)


def _google_map_validate(spec: dict[str, Any]) -> None:
    target = spec.get("target_entity", {})
    app = _load("google_map")
    e = spec.get("expected_answer", {})
    with app.app.app_context():
        p = app.Place.query.filter_by(slug=target.get("slug")).first()
        if p is None:
            _fail("Google Maps place not found")
        _assert_identity(spec, p.name)
        city = p.city.display_name if getattr(p, "city", None) and hasattr(p.city, "display_name") else (p.city.name if getattr(p, "city", None) and hasattr(p.city, "name") else "")
        category = p.category.name if getattr(p, "category", None) else ""
        checks = {"place_name": p.name, "category": category, "city": city, "rating": p.rating,
                  "review_count": p.review_count, "address": p.address, "price_level": p.price_level,
                  "parking_lot": p.has_parking_lot}
        reasons: list[str] = []
        for k, actual in checks.items():
            _eq(actual, e.get(k), k, reasons)
        if _is_identify(spec):
            c = spec.get("constraints", {})
            q = app.Place.query
            if "category" in c:
                q = q.join(app.Category).filter(app.Category.name == c["category"])
            if "city" in c:
                q = q.join(app.City).filter(app.City.display_name == c["city"])
            for key, attr in {"rating": "rating", "review_count": "review_count", "address": "address",
                              "price_level": "price_level", "parking_lot": "has_parking_lot"}.items():
                if key in c:
                    q = q.filter(getattr(app.Place, attr) == c[key])
            _assert_unique_count("google_map", q.count(), p.name)
        if reasons:
            _fail(f"Google Maps place does not satisfy constraints: {', '.join(reasons)}")


def _huggingface_validate(spec: dict[str, Any]) -> None:
    target = spec.get("target_entity", {})
    app = _load("huggingface")
    e = spec.get("expected_answer", {})
    with app.app.app_context():
        r = app.Repository.query.filter_by(slug=target.get("slug")).first()
        if r is None:
            _fail("Hugging Face repository not found")
        _assert_identity(spec, r.slug)
        task = app.db.session.get(app.Task, r.task_id) if getattr(r, "task_id", None) else None
        checks = {"repository": r.slug, "repo_type": r.repo_type, "task": task.display if task else "",
                  "library": r.library, "license": r.license_display, "downloads": r.downloads,
                  "likes": r.likes_count, "status": r.status}
        reasons: list[str] = []
        for k, actual in checks.items():
            _eq(actual, e.get(k), k, reasons)
        if _is_identify(spec):
            c = spec.get("constraints", {})
            q = app.Repository.query
            for key, attr in {"repo_type": "repo_type", "library": "library", "license": "license_display",
                              "downloads": "downloads", "likes": "likes_count", "status": "status"}.items():
                if key in c:
                    q = q.filter(getattr(app.Repository, attr) == c[key])
            if "task" in c:
                q = q.join(app.Task).filter(app.Task.display == c["task"])
            _assert_unique_count("huggingface", q.count(), r.slug)
        if reasons:
            _fail(f"Hugging Face repository does not satisfy constraints: {', '.join(reasons)}")


def _wolfram_alpha_validate(spec: dict[str, Any]) -> None:
    target = spec.get("target_entity", {})
    app = _load("wolfram_alpha")
    e = spec.get("expected_answer", {})
    with app.app.app_context():
        t = app.Topic.query.filter_by(slug=target.get("slug")).first()
        if t is None:
            _fail("Wolfram topic not found")
        _assert_identity(spec, t.name)
        examples = json.loads(t.examples or "[]")
        first = examples[0] if examples else {}
        checks = {"topic": t.name, "description": t.description, "first_example_query": first.get("query", ""),
                  "first_example_result": first.get("result", ""), "is_featured": t.is_featured}
        reasons: list[str] = []
        for k, actual in checks.items():
            _eq(actual, e.get(k), k, reasons)
        if _is_identify(spec):
            c = spec.get("constraints", {})
            matches = []
            for candidate in app.Topic.query.all():
                if "is_featured" in c and candidate.is_featured != c["is_featured"]:
                    continue
                candidate_examples = json.loads(candidate.examples or "[]")
                candidate_first = candidate_examples[0] if candidate_examples else {}
                if "first_example_query" in c and candidate_first.get("query", "") != c["first_example_query"]:
                    continue
                if "first_example_result" in c and candidate_first.get("result", "") != c["first_example_result"]:
                    continue
                matches.append(candidate)
            _assert_unique_count("wolfram_alpha", len(matches), t.name)
        if reasons:
            _fail(f"Wolfram topic does not satisfy constraints: {', '.join(reasons)}")


def _mutation_lookup(app, spec: dict[str, Any]):
    site = spec["site"]
    if spec.get("target_entities"):
        return _multi_mutation_lookup(app, spec)
    target = spec.get("target_entity", {})
    actor = spec.get("actor", {})
    email = actor.get("email")
    user = app.User.query.filter_by(email=email).first()
    if user is None:
        _fail(f"mutation actor not found: {email}")
    kind = target.get("kind")
    target_id = target.get("id")
    if target_id is None:
        _fail("mutation target missing id")

    if site == "allrecipes":
        return user, app.RecipeBoxItem.query.filter_by(user_id=user.id, recipe_id=target_id).first()
    if site == "amazon":
        return user, app.CartItem.query.filter_by(user_id=user.id, product_id=target_id).first()
    if site == "apple":
        return user, app.CartItem.query.filter_by(user_id=user.id, product_id=target_id).first()
    if site == "arxiv":
        return user, app.LibraryItem.query.filter_by(user_id=user.id, paper_id=target_id).first()
    if site == "booking":
        return user, app.SavedProperty.query.filter_by(user_id=user.id, property_id=target_id).first()
    if site == "cambridge_dictionary":
        return user, app.SavedWord.query.filter_by(user_id=user.id, word_id=target_id).first()
    if site == "coursera":
        return user, app.SavedCourse.query.filter_by(user_id=user.id, course_id=target_id).first()
    if site == "espn":
        return user, app.UserFavorite.query.filter_by(user_id=user.id, item_type="team", item_id=target_id).first()
    if site == "github":
        return user, app.Star.query.filter_by(user_id=user.id, repo_id=target_id).first()
    if site == "google_flights":
        return user, app.TrackedFlight.query.filter_by(user_id=user.id, flight_id=target_id).first()
    if site == "google_map":
        return user, app.SavedPlace.query.filter_by(user_id=user.id, place_id=target_id).first()
    if site == "huggingface":
        return user, app.Like.query.filter_by(user_id=user.id, repo_id=target_id).first()
    if site == "wolfram_alpha":
        return user, app.Favorite.query.filter_by(user_id=user.id, topic_id=target_id).first()
    _fail(f"unsupported mutation site: {site}")


def _multi_mutation_lookup(app, spec: dict[str, Any]):
    site = spec["site"]
    actor = spec.get("actor", {})
    email = actor.get("email")
    user = app.User.query.filter_by(email=email).first()
    if user is None:
        _fail(f"mutation actor not found: {email}")
    targets = spec.get("target_entities") or []
    if not targets:
        _fail("multi mutation target_entities missing")
    rows = []
    model = fk = None
    if site == "allrecipes":
        model, fk = app.RecipeBoxItem, "recipe_id"
    elif site == "amazon":
        model, fk = app.CartItem, "product_id"
    elif site == "apple":
        model, fk = app.CartItem, "product_id"
    elif site == "arxiv":
        model, fk = app.LibraryItem, "paper_id"
    elif site == "booking":
        model, fk = app.CartItem, "property_id"
    elif site == "cambridge_dictionary":
        model, fk = app.SavedWord, "word_id"
    elif site == "coursera":
        model, fk = app.SavedCourse, "course_id"
    elif site == "github":
        model, fk = app.Star, "repo_id"
    elif site == "google_flights":
        model, fk = app.TrackedFlight, "flight_id"
    elif site == "huggingface":
        model, fk = app.Like, "repo_id"
    elif site == "wolfram_alpha":
        model, fk = app.Favorite, "topic_id"
    if model is not None:
        for target in targets:
            row = model.query.filter_by(user_id=user.id).filter(getattr(model, fk) == target.get("id")).first()
            rows.append((target, row))
        return user, rows
    if site == "espn":
        for target in targets:
            row = app.UserFavorite.query.filter_by(user_id=user.id, item_type="team", item_id=target.get("id")).first()
            rows.append((target, row))
        return user, rows
    if site == "google_map":
        for target in targets:
            row = app.SavedPlace.query.filter_by(user_id=user.id, place_id=target.get("id")).first()
            rows.append((target, row))
        return user, rows
    _fail(f"unsupported multi mutation site: {site}")


def _mutation_validate(spec: dict[str, Any], phase: str) -> None:
    site = spec.get("site")
    app = _load(site)
    expected = spec.get("expected_answer", {})
    operation = spec.get("operation", {})
    with app.app.app_context():
        user, row = _mutation_lookup(app, spec)
        if spec.get("target_entities"):
            _multi_mutation_validate_rows(spec, row, phase)
            return
        if phase == "before":
            if row is not None:
                _fail(f"before state failed: mutation row already exists for {site}")
            return
        if phase == "after":
            if row is None:
                _fail(f"after state failed: expected mutation row for {site}")
            quantity = operation.get("quantity")
            if quantity is not None and hasattr(row, "quantity") and row.quantity != quantity:
                _fail(f"after state failed: expected quantity {quantity}, got {row.quantity}")
            return
        # spec phase: actor and target exist; before must be absent in fresh DB.
        if row is not None:
            _fail(f"spec state failed: mutation row already exists for {site}")


def _multi_mutation_validate_rows(spec: dict[str, Any], rows: list[tuple[dict[str, Any], Any]], phase: str) -> None:
    site = spec["site"]
    _validate_expected_totals(spec)
    if phase in {"before", "spec"}:
        existing = [target for target, row in rows if row is not None]
        if existing:
            first = existing[0]
            _fail(f"{site} before state failed: product_id={first.get('id')} already exists")
        return
    if phase == "after":
        for target, row in rows:
            if row is None:
                _fail(f"{site} state mismatch: item_id={target.get('id')} expected quantity={target.get('quantity', 1)} actual=missing")
            if hasattr(row, "quantity") and int(row.quantity) != int(target.get("quantity", 1)):
                _fail(f"{site} state mismatch: item_id={target.get('id')} expected quantity={target.get('quantity', 1)} actual={row.quantity}")
            if "line_total" in target:
                unit_price = getattr(row, "unit_price", None)
                if unit_price is None and hasattr(row, "product") and row.product is not None:
                    unit_price = getattr(row.product, "price", None)
                if unit_price is not None:
                    actual_line = round(float(unit_price) * int(getattr(row, "quantity", target.get("quantity", 1))), 2)
                    if abs(actual_line - float(target["line_total"])) > 0.01:
                        _fail(f"{site} state mismatch: item_id={target.get('id')} field=line_total expected={target['line_total']} actual={actual_line}")
            for field in ("check_in", "check_out", "adults", "rooms", "room_type"):
                if field in target and hasattr(row, field) and str(getattr(row, field)) != str(target[field]):
                    _fail(f"{site} state mismatch: item_id={target.get('id')} field={field} expected={target[field]} actual={getattr(row, field)}")
        return


def _validate_expected_totals(spec: dict[str, Any]) -> None:
    expected = spec.get("expected_answer", {})
    items = expected.get("items") or []
    if not items:
        return
    line_sum = 0.0
    saw_money = False
    for item in items:
        if "unit_price" in item and "quantity" in item and "line_total" in item:
            saw_money = True
            calc = round(float(item["unit_price"]) * int(item["quantity"]), 2)
            if abs(calc - float(item["line_total"])) > 0.01:
                _fail(f"{spec['site']} expected total mismatch: item={item.get('identity')} line_total={item['line_total']} calculated={calc}")
            line_sum += float(item["line_total"])
        elif "item_total" in item:
            saw_money = True
            line_sum += float(item["item_total"])
    if saw_money and "subtotal" in expected:
        subtotal = round(line_sum, 2)
        if abs(subtotal - float(expected["subtotal"])) > 0.01:
            _fail(f"{spec['site']} expected subtotal mismatch: expected={expected['subtotal']} calculated={subtotal}")


VALIDATORS = {
    "allrecipes.recipe_matches_constraints": _allrecipes_validate,
    "amazon.product_matches_constraints": _amazon_validate,
    "apple.product_matches_constraints": _apple_validate,
    "arxiv.paper_matches_constraints": _arxiv_validate,
    "booking.property_matches_constraints": _booking_validate,
    "cambridge_dictionary.word_matches_constraints": _cambridge_dictionary_validate,
    "coursera.course_matches_constraints": _coursera_validate,
    "espn.team_matches_constraints": _espn_validate,
    "github.repository_matches_constraints": _github_validate,
    "google_flights.flight_matches_constraints": _google_flights_validate,
    "google_map.place_matches_constraints": _google_map_validate,
    "huggingface.repository_matches_constraints": _huggingface_validate,
    "wolfram_alpha.topic_matches_constraints": _wolfram_alpha_validate,
}


def validate(spec: dict[str, Any], phase: str = "spec") -> None:
    if spec.get("validation", {}).get("answer_kind") == "state_transition":
        _mutation_validate(spec, phase)
        return
    predicate = spec.get("validation", {}).get("db_predicate")
    validator = VALIDATORS.get(predicate)
    if validator is None:
        _fail(f"unsupported structured task predicate: site={spec.get('site')!r}, predicate={predicate!r}")
    validator(spec)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True, help="JSON spec or one-line JSONL file")
    parser.add_argument("--phase", choices=["spec", "before", "after"], default="spec",
                        help="for state mutation tasks, validate spec/before/after DB state")
    args = parser.parse_args()
    text = args.spec.read_text(encoding="utf-8").strip()
    specs = [json.loads(line) for line in text.splitlines() if line.strip()]
    if not specs:
        print(f"empty spec file: {args.spec}", file=sys.stderr)
        return 1
    try:
        for index, spec in enumerate(specs, start=1):
            try:
                validate(spec, phase=args.phase)
            except SystemExit as exc:
                if exc.code and isinstance(exc.code, str):
                    task_id = spec.get("id", f"{args.spec}:{index}")
                    print(f"{task_id}: {exc.code}", file=sys.stderr)
                    return 1
                raise
    except SystemExit as exc:
        if exc.code and isinstance(exc.code, str):
            print(exc.code, file=sys.stderr)
            return 1
        raise
    if len(specs) == 1:
        print(f"validated {specs[0].get('id', args.spec)}")
    else:
        print(f"validated {len(specs)} task(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
