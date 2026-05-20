#!/usr/bin/env python3
"""Reverse-generate structured WebHarbor tasks from deterministic DB fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from structured_task_runtime import SITE_ORDER, WEB_URLS, UPSTREAM_URLS, UPSTREAM_LOGIN_URLS, json_dump_line, load_site_app, stable_task_id


SUPPORTED_SITES = [
    "allrecipes",
    "amazon",
    "apple",
    "arxiv",
    "booking",
    "cambridge_dictionary",
    "coursera",
    "espn",
    "github",
    "google_flights",
    "google_map",
    "huggingface",
    "wolfram_alpha",
]
ROOT = Path(__file__).resolve().parents[1]
PERSONA_REGISTRY = ROOT / "configs" / "auth_personas.json"

WEB_NAMES = {
    "allrecipes": "Allrecipes",
    "amazon": "Amazon",
    "apple": "Apple",
    "arxiv": "arXiv",
    "booking": "Booking",
    "cambridge_dictionary": "Cambridge Dictionary",
    "coursera": "Coursera",
    "espn": "ESPN",
    "github": "GitHub",
    "google_flights": "Google Flights",
    "google_map": "Google Maps",
    "huggingface": "Hugging Face",
    "wolfram_alpha": "Wolfram Alpha",
}

BOOKING_FAMILY = "hotel_search_with_amenity_filters"
FLIGHTS_FAMILY = "one_way_cheapest_flight"
DEFAULT_FAMILIES = {
    "allrecipes": "recipe_detail_lookup",
    "amazon": "product_search_with_filters",
    "apple": "product_detail_lookup",
    "arxiv": "paper_metadata_lookup",
    "booking": BOOKING_FAMILY,
    "cambridge_dictionary": "dictionary_entry_lookup",
    "coursera": "course_search_detail_lookup",
    "espn": "team_standings_lookup",
    "github": "repository_search_detail_lookup",
    "google_flights": FLIGHTS_FAMILY,
    "google_map": "place_search_detail_lookup",
    "huggingface": "repository_search_detail_lookup",
    "wolfram_alpha": "topic_example_lookup",
}

IDENTIFY_FAMILIES = {
    "allrecipes": "recipe_identify_by_constraints",
    "amazon": "product_identify_by_constraints",
    "apple": "product_identify_by_constraints",
    "arxiv": "paper_identify_by_constraints",
    "booking": "property_identify_by_constraints",
    "cambridge_dictionary": "word_identify_by_constraints",
    "coursera": "course_identify_by_constraints",
    "espn": "team_identify_by_constraints",
    "github": "repository_identify_by_constraints",
    "google_flights": "flight_identify_by_constraints",
    "google_map": "place_identify_by_constraints",
    "huggingface": "repository_identify_by_constraints",
    "wolfram_alpha": "topic_identify_by_constraints",
}

MUTATION_FAMILIES = {
    "allrecipes": "recipe_box_save",
    "amazon": "cart_add_product",
    "apple": "cart_add_product",
    "arxiv": "library_add_paper",
    "booking": "saved_property_add",
    "cambridge_dictionary": "saved_word_add",
    "coursera": "saved_course_add",
    "espn": "favorite_team_add",
    "github": "repo_star_add",
    "google_flights": "tracked_flight_add",
    "google_map": "saved_place_add",
    "huggingface": "repo_like_add",
    "wolfram_alpha": "favorite_topic_add",
}
MULTI_MUTATION_FAMILIES = {
    "allrecipes": "recipe_box_save_multiple",
    "amazon": "cart_add_multiple_products",
    "apple": "bag_add_multiple_products",
    "arxiv": "library_add_multiple_papers",
    "booking": "bag_add_multiple_stays",
    "cambridge_dictionary": "saved_words_add_multiple",
    "coursera": "saved_courses_add_multiple",
    "espn": "favorite_teams_add_multiple",
    "github": "repo_star_add_multiple",
    "google_flights": "tracked_flights_add_multiple",
    "google_map": "saved_places_add_multiple",
    "huggingface": "repo_like_add_multiple",
    "wolfram_alpha": "favorite_topics_add_multiple",
}


def load_personas() -> dict[str, list[dict[str, Any]]]:
    return json.loads(PERSONA_REGISTRY.read_text(encoding="utf-8"))


def personas_for_site(site: str) -> list[dict[str, Any]]:
    personas = load_personas().get(site, [])
    if not personas:
        raise ValueError(f"no auth personas configured for {site}")
    return personas


def persona_for_site(site: str, offset: int = 0, persona_index: int | None = None) -> dict[str, Any]:
    personas = personas_for_site(site)
    index = offset if persona_index is None else persona_index
    return personas[index % len(personas)]


def _base(site: str, family: str, target_label: str, instruction: str, target_entity: dict[str, Any],
          constraints: dict[str, Any], expected: dict[str, Any], must_appear: list[str],
          fields: list[str], difficulty: int = 5) -> dict[str, Any]:
    return {
        "web_name": WEB_NAMES[site],
        "id": stable_task_id(site, family, target_label),
        "ques": instruction,
        "web": WEB_URLS[site],
        "upstream_url": UPSTREAM_URLS[site],
        "site": site,
        "task_family": family,
        "start_url": WEB_URLS[site],
        "instruction": instruction,
        "target_entity": target_entity,
        "constraints": constraints,
        "expected_answer": expected,
        "validation": {
            "db_predicate": f"{site}.{target_entity['kind']}_matches_constraints",
            "must_appear": [str(x) for x in must_appear if x not in (None, "")],
            "visible_evidence_fields": fields,
            "require_unique_match": False,
        },
        "stability": {
            "fixture_fixed": True,
            "request_random": False,
            "session_state": False,
            "date_anchor": False,
            "real_time_risk": False,
        },
        "difficulty": difficulty,
    }




def _identify_spec(detail: dict[str, Any], family: str, identity: str, instruction: str,
                   constraints: dict[str, Any], difficulty: int | None = None) -> dict[str, Any]:
    """Convert a detail task into an entity-identification task.

    The prompt should not reveal the target identity. The DB validator checks that
    the feature constraints uniquely identify the original target entity.
    """
    site = detail["site"]
    spec = dict(detail)
    spec["id"] = stable_task_id(site, family, identity)
    spec["task_family"] = family
    spec["ques"] = instruction
    spec["instruction"] = instruction
    spec["constraints"] = {"target_selection": "identify_by_constraints", **constraints}
    spec["expected_answer"] = {"identity": identity}
    spec["validation"] = dict(detail["validation"])
    spec["validation"]["must_appear"] = [identity]
    spec["validation"]["visible_evidence_fields"] = ["identity"]
    spec["validation"]["require_unique_match"] = True
    spec["validation"]["answer_kind"] = "entity_identity"
    if difficulty is not None:
        spec["difficulty"] = difficulty
    return spec


def _bool_word(value: bool) -> str:
    return "yes" if value else "no"




def _actor(email: str = "alice.j@test.com", password: str = "TestPass123!", user_id: int | None = None,
           display_name: str | None = None, persona: str | None = None) -> dict[str, Any]:
    actor = {"email": email, "password": password}
    if user_id is not None:
        actor["user_id"] = user_id
    if display_name:
        actor["display_name"] = display_name
    if persona:
        actor["persona"] = persona
    return actor


def _actor_from_persona(persona: dict[str, Any]) -> dict[str, Any]:
    return _actor(
        persona["email"],
        persona["password"],
        user_id=int(persona["user_id"]),
        display_name=persona.get("display_name"),
        persona=persona.get("persona"),
    )


def _mutation_spec(site: str, family: str, target_label: str, instruction: str,
                   actor: dict[str, Any], target_entity: dict[str, Any],
                   operation: dict[str, Any], before_predicate: str,
                   after_predicate: str, expected: dict[str, Any],
                   difficulty: int = 7) -> dict[str, Any]:
    return {
        "web_name": WEB_NAMES[site],
        "id": stable_task_id(site, family, target_label),
        "ques": instruction,
        "web": WEB_URLS[site],
        "upstream_url": UPSTREAM_URLS[site],
        "site": site,
        "task_family": family,
        "start_url": WEB_URLS[site],
        "instruction": instruction,
        "actor": actor,
        "login": {
            "required": True,
            "strategy": "ui_credentials",
            "login_url": UPSTREAM_LOGIN_URLS[site],
            "post_login_assertion": "authenticated user session is active",
        },
        "target_entity": target_entity,
        "operation": operation,
        "constraints": {"target_selection": "state_mutation", **operation},
        "expected_answer": expected,
        "state_transition": {
            "before": {"db_predicate": before_predicate},
            "after": {"db_predicate": after_predicate},
        },
        "validation": {
            "db_predicate": after_predicate,
            "answer_kind": "state_transition",
            "must_appear": [str(v) for v in expected.values() if v not in (None, "")],
            "visible_evidence_fields": list(expected),
            "require_unique_match": False,
        },
        "stability": {
            "fixture_fixed": True,
            "request_random": False,
            "session_state": True,
            "date_anchor": False,
            "real_time_risk": False,
        },
        "difficulty": difficulty,
    }


def _multi_mutation_spec(site: str, family: str, target_label: str, instruction: str,
                         actor: dict[str, Any], target_entities: list[dict[str, Any]],
                         operation: dict[str, Any], before_predicate: str,
                         after_predicate: str, expected: dict[str, Any],
                         difficulty: int = 8) -> dict[str, Any]:
    spec = _mutation_spec(
        site,
        family,
        target_label,
        instruction,
        actor,
        target_entities[0],
        operation,
        before_predicate,
        after_predicate,
        expected,
        difficulty,
    )
    spec["target_entities"] = target_entities
    spec["validation"]["must_appear"] = [
        str(item.get("name") or item.get("title") or item.get("full_name") or item.get("flight_number") or item.get("id"))
        for item in target_entities
    ]
    spec["validation"]["visible_evidence_fields"] = ["items"]
    return spec


def _first_user(app, email: str = "alice.j@test.com"):
    return app.User.query.filter_by(email=email).first() or app.User.query.order_by(app.User.id).first()


def _first_absent(app, entity_cls, mutation_cls, user_id: int, fk_name: str, extra_filter=None):
    for obj in entity_cls.query.order_by(entity_cls.id).limit(500).all():
        q = mutation_cls.query.filter_by(user_id=user_id)
        if extra_filter is not None:
            q = extra_filter(q, obj)
        else:
            q = q.filter(getattr(mutation_cls, fk_name) == obj.id)
        if q.first() is None:
            return obj
    raise RuntimeError(f"no absent target found for {entity_cls.__name__}")


def _allrecipes_specs() -> list[dict[str, Any]]:
    app = load_site_app("allrecipes", fresh_instance=True).module
    with app.app.app_context():
        r = app.Recipe.query.order_by(app.Recipe.review_count.desc(), app.Recipe.avg_rating.desc()).first()
        expected = {
            "title": r.title,
            "rating": r.avg_rating,
            "review_count": r.review_count,
            "total_time": r.total_time,
            "servings": r.servings,
            "calories": r.calories,
            "author": r.author_name,
        }
        instruction = (
            f"On Allrecipes, search for the recipe {r.title!r}, open its detail page, "
            "and answer with the recipe title, rating, review count, total time, servings, calories, and author."
        )
        return [_base("allrecipes", DEFAULT_FAMILIES["allrecipes"], r.title, instruction,
                      {"kind": "recipe", "title": r.title, "slug": r.slug},
                      {"query": r.title, "sort": "review_count_desc"}, expected,
                      [r.title, f"{r.avg_rating:g}", r.review_count, r.total_time, r.servings, r.calories, r.author_name],
                      list(expected), 4)]


def _amazon_specs() -> list[dict[str, Any]]:
    app = load_site_app("amazon", fresh_instance=True).module
    with app.app.app_context():
        p = app.Product.query.filter_by(is_prime=True, free_shipping=True).order_by(app.Product.rating.desc(), app.Product.review_count.desc()).first()
        expected = {
            "product_name": p.name,
            "brand": p.brand,
            "category": p.category_slug,
            "price": p.price,
            "rating": p.rating,
            "review_count": p.review_count,
            "condition": p.condition,
            "free_shipping": p.free_shipping,
            "free_returns": p.free_returns,
        }
        instruction = (
            f"On Amazon, search for {p.name!r}. Use or verify filters for brand {p.brand}, "
            f"category {p.category_slug}, Prime/free shipping, and rating at least {p.rating:.1f}. "
            "Open the matching product page and answer with product name, brand, category, price, rating, review count, condition, shipping, and returns."
        )
        return [_base("amazon", DEFAULT_FAMILIES["amazon"], p.name, instruction,
                      {"kind": "product", "name": p.name, "slug": p.slug, "field": "brand", "brand": p.brand},
                      {"query": p.name, "brand": p.brand, "category": p.category_slug, "min_rating": p.rating,
                       "prime": True, "free_shipping": True, "verified_field": "brand"}, expected,
                      [p.name, p.brand, p.category_slug, f"${p.price:g}", f"{p.rating:g}", p.review_count, p.condition],
                      list(expected), 6)]


def _apple_specs() -> list[dict[str, Any]]:
    app = load_site_app("apple", fresh_instance=True).module
    with app.app.app_context():
        p = app.Product.query.order_by(app.Product.is_new.desc(), app.Product.price.desc()).first()
        specs = json.loads(p.specs or "{}")
        expected = {
            "product_name": p.name,
            "category": p.category,
            "subtitle": p.subtitle,
            "price": p.price,
            "monthly_price": p.monthly_price,
            "display": specs.get("display", ""),
            "chip": specs.get("chip", p.chip_family or ""),
            "in_stock": p.in_stock,
        }
        instruction = (
            f"On Apple, search or browse to {p.name!r}, open its product detail page, "
            "and answer with product name, category, subtitle, full price, monthly price, display, chip, and stock status."
        )
        return [_base("apple", DEFAULT_FAMILIES["apple"], p.name, instruction,
                      {"kind": "product", "name": p.name, "slug": p.slug},
                      {"query": p.name, "category": p.category, "min_price": p.price}, expected,
                      [p.name, p.category, p.subtitle, f"${p.price:g}", f"{p.monthly_price:g}", expected["chip"]],
                      list(expected), 4)]


def _arxiv_specs() -> list[dict[str, Any]]:
    app = load_site_app("arxiv", fresh_instance=True).module
    with app.app.app_context():
        p = app.Paper.query.filter_by(arxiv_id="2604.08523").first() or app.Paper.query.filter_by(primary_subject_code="cs.CL").order_by(app.Paper.arxiv_id.desc()).first()
        authors = json.loads(p.authors_json or "[]")
        expected = {
            "arxiv_id": p.arxiv_id,
            "title": p.title,
            "primary_subject": p.primary_subject,
            "submitted_date": p.submitted_date,
            "author_count": p.n_authors,
            "first_author": authors[0] if authors else "",
        }
        instruction = (
            f"On arXiv, search for paper ID {p.arxiv_id}, open the abstract page, "
            "and answer with arXiv ID, title, primary subject, submitted date, author count, first author, and download count."
        )
        return [_base("arxiv", DEFAULT_FAMILIES["arxiv"], p.arxiv_id, instruction,
                      {"kind": "paper", "arxiv_id": p.arxiv_id},
                      {"query": p.arxiv_id, "primary_subject_code": p.primary_subject_code}, expected,
                      [p.arxiv_id, p.title, p.primary_subject, p.submitted_date, expected["first_author"]],
                      list(expected), 4)]


def _booking_specs() -> list[dict]:
    app = load_site_app("booking", fresh_instance=True).module
    with app.app.app_context():
        city = app.City.query.filter_by(key="barcelona").first()
        target = app.Property.query.filter_by(name="Praktik Èssens").first()
        if city is None or target is None:
            raise RuntimeError("missing Booking Barcelona/Praktik fixture")
        constraints = {
            "city": city.display,
            "checkin": "2026-06-12",
            "checkout": "2026-06-15",
            "adults": 2,
            "rooms": 1,
            "amenities": ["breakfast_included", "free_wifi"],
            "min_rating": 8.0,
            "min_price": 50,
            "max_price": 500,
            "verified_field": "brand",
        }
        instruction = (
            "On Booking, search in Barcelona for June 12, 2026 to June 15, 2026 "
            "for 2 adults and 1 room. Use filters for breakfast included, free WiFi, "
            "rating at least 8, and nightly price between $50 and $500. Open the "
            "Praktik Èssens hotel detail page and answer with hotel name, rating, "
            "review count, nightly price, stars, property type, and distance from the "
            "center. Make sure the search/filter/sort flow uses or verifies the "
            "property field 'brand', then answer from visible page evidence."
        )
        expected = {
            "property_name": target.name,
            "rating": target.rating,
            "review_count": target.review_count,
            "nightly_price": target.price_per_night,
            "stars": target.stars,
            "property_type": target.property_type,
            "distance_from_center_km": target.distance_from_center,
            "brand": target.brand,
        }
        spec = _base("booking", BOOKING_FAMILY, target.name, instruction,
                     {"kind": "property", "name": target.name, "field": "brand", "brand": target.brand},
                     constraints, expected,
                     [target.name, f"{target.rating:.1f}", str(target.review_count), f"${target.price_per_night:.0f}",
                      f"{target.stars} stars", target.property_type, f"{target.distance_from_center:g} km", target.brand],
                     list(expected), 7)
        spec["validation"]["db_predicate"] = "booking.property_matches_constraints"
        spec["stability"]["date_anchor"] = True
        return [spec]


def _cambridge_specs() -> list[dict[str, Any]]:
    app = load_site_app("cambridge_dictionary", fresh_instance=True).module
    with app.app.app_context():
        w = app.Word.query.filter_by(headword="sustainability").first() or app.Word.query.first()
        defs = json.loads(w.definitions_json or "[]")
        expected = {
            "headword": w.headword,
            "part_of_speech": w.pos,
            "level": w.level,
            "uk_phonetic": w.phonetic_uk,
            "us_phonetic": w.phonetic_us,
            "first_definition": defs[0]["definition"] if defs else "",
        }
        instruction = (
            f"On Cambridge Dictionary, look up {w.headword!r} and answer with the headword, "
            "part of speech, CEFR level, UK phonetic, US phonetic, and first definition."
        )
        return [_base("cambridge_dictionary", DEFAULT_FAMILIES["cambridge_dictionary"], w.headword, instruction,
                      {"kind": "word", "headword": w.headword, "slug": w.slug},
                      {"query": w.headword, "level": w.level}, expected,
                      [w.headword, w.pos, w.level, w.phonetic_uk, w.phonetic_us, expected["first_definition"][:40]],
                      list(expected), 3)]


def _coursera_specs() -> list[dict[str, Any]]:
    app = load_site_app("coursera", fresh_instance=True).module
    with app.app.app_context():
        c = app.Course.query.order_by(app.Course.rating.desc(), app.Course.review_count.desc()).first()
        partner_name = c.partner.name if getattr(c, "partner", None) else ""
        expected = {
            "course_title": c.title,
            "partner": partner_name,
            "level": c.level,
            "rating": c.rating,
            "review_count": c.review_count,
            "duration": c.duration_text,
            "instructor": c.instructor,
            "certificate": c.has_certificate,
        }
        instruction = (
            f"On Coursera, search for {c.title!r}, open the course detail page, "
            "and answer with course title, partner, level, rating, review count, duration, instructor, and certificate availability."
        )
        return [_base("coursera", DEFAULT_FAMILIES["coursera"], c.title, instruction,
                      {"kind": "course", "title": c.title, "slug": c.slug},
                      {"query": c.title, "level": c.level, "min_rating": c.rating}, expected,
                      [c.title, partner_name, c.level, f"{c.rating:g}", c.review_count, c.duration_text, c.instructor],
                      list(expected), 4)]


def _espn_specs() -> list[dict[str, Any]]:
    app = load_site_app("espn", fresh_instance=True).module
    with app.app.app_context():
        t = app.Team.query.filter_by(sport_slug="nba").order_by(app.Team.standing_rank.asc(), app.Team.wins.desc()).first()
        expected = {
            "team": t.full_name,
            "sport": t.sport_slug,
            "abbreviation": t.abbreviation,
            "wins": t.wins,
            "losses": t.losses,
            "win_pct": t.win_pct,
            "standing_rank": t.standing_rank,
            "streak": t.streak,
        }
        instruction = (
            f"On ESPN, open the NBA standings or team page for {t.full_name} and answer with "
            "team name, sport, abbreviation, wins, losses, win percentage, standings rank, and streak."
        )
        return [_base("espn", DEFAULT_FAMILIES["espn"], t.full_name, instruction,
                      {"kind": "team", "full_name": t.full_name, "slug": t.slug},
                      {"sport": t.sport_slug, "sort": "standing_rank"}, expected,
                      [t.full_name, t.abbreviation, t.wins, t.losses, f"{t.win_pct:g}", t.standing_rank, t.streak],
                      list(expected), 4)]


def _github_specs() -> list[dict[str, Any]]:
    app = load_site_app("github", fresh_instance=True).module
    with app.app.app_context():
        r = app.Repository.query.order_by(app.Repository.stars_count.desc()).first()
        expected = {
            "repository": r.full_name,
            "description": r.description,
            "language": r.language,
            "license": r.license,
            "stars": r.stars_count,
            "forks": r.forks_count,
            "open_issues": r.open_issues_count,
            "default_branch": r.default_branch,
        }
        instruction = (
            f"On GitHub, search for repository {r.full_name!r}, open its repository page, "
            "and answer with repository full name, description, language, license, stars, forks, open issues, and default branch."
        )
        return [_base("github", DEFAULT_FAMILIES["github"], r.full_name, instruction,
                      {"kind": "repository", "full_name": r.full_name},
                      {"query": r.full_name, "language": r.language, "license": r.license, "min_stars": r.stars_count}, expected,
                      [r.full_name, r.language, r.license, r.stars_count, r.forks_count, r.open_issues_count, r.default_branch],
                      list(expected), 5)]


def _google_flights_specs() -> list[dict]:
    app = load_site_app("google_flights", fresh_instance=True).module
    with app.app.app_context():
        rows = (
            app.db.session.query(app.Flight.origin_id, app.Flight.destination_id, app.Flight.departure_date)
            .group_by(app.Flight.origin_id, app.Flight.destination_id, app.Flight.departure_date)
            .having(app.db.func.count(app.Flight.id) >= 2)
            .order_by(app.Flight.origin_id, app.Flight.destination_id, app.Flight.departure_date)
            .all()
        )
        if not rows:
            raise RuntimeError("no multi-option Google Flights route fixture")
        origin_id, destination_id, dep_date = rows[0]
        target = (app.Flight.query
                  .filter_by(origin_id=origin_id, destination_id=destination_id, departure_date=dep_date)
                  .order_by(app.Flight.price.asc(), app.Flight.duration_minutes.asc(), app.Flight.id.asc())
                  .first())
        origin = target.origin
        destination = target.destination
        constraints = {
            "origin": origin.iata,
            "destination": destination.iata,
            "depart": dep_date.isoformat(),
            "passengers": 1,
            "trip_type": "one-way",
            "cabin": "Economy",
            "sort": "price",
        }
        instruction = (
            f"On Google Flights, search one-way flights from {origin.iata} to {destination.iata} "
            f"on {dep_date.strftime('%B %-d, %Y')} for 1 adult in Economy. Sort by price, "
            "open the cheapest matching flight detail page, and answer with flight number, airline, departure time, arrival time, stops, duration, price, and aircraft."
        )
        expected = {
            "flight_number": target.flight_number,
            "airline": target.airline,
            "origin": origin.iata,
            "destination": destination.iata,
            "departure_date": dep_date.isoformat(),
            "departure_time": target.departure_time,
            "arrival_time": target.arrival_time,
            "stops": target.stops,
            "duration": target.duration_str,
            "price": target.price,
            "aircraft": target.aircraft,
        }
        spec = _base("google_flights", FLIGHTS_FAMILY, target.flight_number, instruction,
                     {"kind": "flight", "flight_number": target.flight_number, "id": target.id},
                     constraints, expected,
                     [target.flight_number, target.airline, target.departure_time, target.arrival_time, f"${target.price:.0f}", target.aircraft],
                     list(expected), 6)
        spec["validation"]["db_predicate"] = "google_flights.flight_matches_constraints"
        spec["stability"]["date_anchor"] = True
        return [spec]


def _google_map_specs() -> list[dict[str, Any]]:
    app = load_site_app("google_map", fresh_instance=True).module
    with app.app.app_context():
        p = app.Place.query.order_by(app.Place.review_count.desc(), app.Place.rating.desc()).first()
        city = p.city.display_name if getattr(p, "city", None) and hasattr(p.city, "display_name") else (p.city.name if getattr(p, "city", None) and hasattr(p.city, "name") else "")
        category = p.category.name if getattr(p, "category", None) else ""
        expected = {
            "place_name": p.name,
            "category": category,
            "city": city,
            "rating": p.rating,
            "review_count": p.review_count,
            "address": p.address,
            "price_level": p.price_level,
            "parking_lot": p.has_parking_lot,
        }
        instruction = (
            f"On Google Maps, search for {p.name!r}, open the place detail page, "
            "and answer with place name, category, city, rating, review count, address, price level, and whether it has a parking lot."
        )
        return [_base("google_map", DEFAULT_FAMILIES["google_map"], p.name, instruction,
                      {"kind": "place", "name": p.name, "slug": p.slug},
                      {"query": p.name, "min_rating": p.rating, "category": category}, expected,
                      [p.name, category, city, f"{p.rating:g}", p.review_count, p.address, p.price_level],
                      list(expected), 5)]


def _huggingface_specs() -> list[dict[str, Any]]:
    app = load_site_app("huggingface", fresh_instance=True).module
    with app.app.app_context():
        r = app.Repository.query.order_by(app.Repository.downloads.desc(), app.Repository.likes_count.desc()).first()
        task = app.db.session.get(app.Task, r.task_id) if getattr(r, "task_id", None) else None
        task_name = task.display if task is not None else ""
        expected = {
            "repository": r.slug,
            "repo_type": r.repo_type,
            "task": task_name,
            "library": r.library,
            "license": r.license_display,
            "downloads": r.downloads,
            "likes": r.likes_count,
            "status": r.status,
        }
        instruction = (
            f"On Hugging Face, search for repository {r.slug!r}, open its repository page, "
            "and answer with repository slug, repo type, task, library, license, downloads, likes, and status."
        )
        return [_base("huggingface", DEFAULT_FAMILIES["huggingface"], r.slug, instruction,
                      {"kind": "repository", "slug": r.slug, "repo_type": r.repo_type},
                      {"query": r.slug, "repo_type": r.repo_type, "library": r.library}, expected,
                      [r.slug, r.repo_type, task_name, r.library, r.license_display, r.downloads, r.likes_count, r.status],
                      list(expected), 5)]


def _wolfram_specs() -> list[dict[str, Any]]:
    app = load_site_app("wolfram_alpha", fresh_instance=True).module
    with app.app.app_context():
        t = app.Topic.query.filter_by(slug="algebra").first() or app.Topic.query.first()
        examples = json.loads(t.examples or "[]")
        first = examples[0] if examples else {}
        expected = {
            "topic": t.name,
            "description": t.description,
            "first_example_query": first.get("query", ""),
            "first_example_result": first.get("result", ""),
            "is_featured": t.is_featured,
        }
        instruction = (
            f"On Wolfram Alpha, open the topic page for {t.name!r} and answer with topic name, "
            "description, first example query, first example result, and whether it is featured."
        )
        return [_base("wolfram_alpha", DEFAULT_FAMILIES["wolfram_alpha"], t.name, instruction,
                      {"kind": "topic", "name": t.name, "slug": t.slug},
                      {"topic": t.name, "example_type": first.get("type", "")}, expected,
                      [t.name, t.description[:40], first.get("query", ""), first.get("result", "")],
                      list(expected), 3)]


def _page(items, offset: int, limit: int):
    return list(items)[offset:offset + limit]


def _quantity_for(index: int, profile: str) -> int:
    if profile == "ones":
        return 1
    if profile == "increasing":
        return index + 1
    if profile == "mixed":
        return 1 + (index % 2)
    raise ValueError(f"unsupported quantity profile: {profile}")


def _combination_window(items: list[Any], item_count: int, offset: int, limit: int):
    if item_count < 2 or item_count > 4:
        raise ValueError("--item-count must be between 2 and 4")
    selected = []
    seen = 0

    def walk(start: int, current: list[Any]):
        nonlocal seen, selected
        if len(selected) >= limit:
            return
        if len(current) == item_count:
            if seen >= offset:
                selected.append(list(current))
            seen += 1
            return
        remaining = item_count - len(current)
        for idx in range(start, len(items) - remaining + 1):
            current.append(items[idx])
            walk(idx + 1, current)
            current.pop()
            if len(selected) >= limit:
                return

    walk(0, [])
    return selected


def _raise_if_empty(site: str, family: str, specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not specs:
        raise RuntimeError(f"no structured tasks generated for {site}/{family}")
    return specs


def _allrecipes_detail_for(r) -> dict[str, Any]:
    expected = {
        "title": r.title,
        "rating": r.avg_rating,
        "review_count": r.review_count,
        "total_time": r.total_time,
        "servings": r.servings,
        "calories": r.calories,
        "author": r.author_name,
    }
    instruction = (
        f"On Allrecipes, search for the recipe {r.title!r}, open its detail page, "
        "and answer with the recipe title, rating, review count, total time, servings, calories, and author."
    )
    return _base("allrecipes", DEFAULT_FAMILIES["allrecipes"], r.title, instruction,
                 {"kind": "recipe", "title": r.title, "slug": r.slug},
                 {"query": r.title, "sort": "review_count_desc"}, expected,
                 [r.title, f"{r.avg_rating:g}", r.review_count, r.total_time, r.servings, r.calories, r.author_name],
                 list(expected), 4)


def _amazon_detail_for(p) -> dict[str, Any]:
    expected = {
        "product_name": p.name,
        "brand": p.brand,
        "category": p.category_slug,
        "price": p.price,
        "rating": p.rating,
        "review_count": p.review_count,
        "condition": p.condition,
        "free_shipping": p.free_shipping,
        "free_returns": p.free_returns,
    }
    instruction = (
        f"On Amazon, search for {p.name!r}. Use or verify filters for brand {p.brand}, "
        f"category {p.category_slug}, Prime/free shipping, and rating at least {p.rating:.1f}. "
        "Open the matching product page and answer with product name, brand, category, price, rating, review count, condition, shipping, and returns."
    )
    return _base("amazon", DEFAULT_FAMILIES["amazon"], p.name, instruction,
                 {"kind": "product", "name": p.name, "slug": p.slug, "field": "brand", "brand": p.brand},
                 {"query": p.name, "brand": p.brand, "category": p.category_slug, "min_rating": p.rating,
                  "prime": True, "free_shipping": True, "verified_field": "brand"}, expected,
                 [p.name, p.brand, p.category_slug, f"${p.price:g}", f"{p.rating:g}", p.review_count, p.condition],
                 list(expected), 6)


def _apple_detail_for(p) -> dict[str, Any]:
    specs = json.loads(p.specs or "{}")
    expected = {
        "product_name": p.name,
        "category": p.category,
        "subtitle": p.subtitle,
        "price": p.price,
        "monthly_price": p.monthly_price,
        "display": specs.get("display", ""),
        "chip": specs.get("chip", p.chip_family or ""),
        "in_stock": p.in_stock,
    }
    instruction = (
        f"On Apple, search or browse to {p.name!r}, open its product detail page, "
        "and answer with product name, category, subtitle, full price, monthly price, display, chip, and stock status."
    )
    return _base("apple", DEFAULT_FAMILIES["apple"], p.name, instruction,
                 {"kind": "product", "name": p.name, "slug": p.slug},
                 {"query": p.name, "category": p.category, "min_price": p.price}, expected,
                 [p.name, p.category, p.subtitle, f"${p.price:g}", f"{p.monthly_price:g}", expected["chip"]],
                 list(expected), 4)


def _arxiv_detail_for(p) -> dict[str, Any]:
    authors = json.loads(p.authors_json or "[]")
    expected = {
        "arxiv_id": p.arxiv_id,
        "title": p.title,
        "primary_subject": p.primary_subject,
        "submitted_date": p.submitted_date,
        "author_count": p.n_authors,
        "first_author": authors[0] if authors else "",
    }
    instruction = (
        f"On arXiv, search for paper ID {p.arxiv_id}, open the abstract page, "
        "and answer with arXiv ID, title, primary subject, submitted date, author count, and first author."
    )
    return _base("arxiv", DEFAULT_FAMILIES["arxiv"], p.arxiv_id, instruction,
                 {"kind": "paper", "arxiv_id": p.arxiv_id},
                 {"query": p.arxiv_id, "primary_subject_code": p.primary_subject_code}, expected,
                 [p.arxiv_id, p.title, p.primary_subject, p.submitted_date, expected["first_author"]],
                 list(expected), 4)


def _booking_detail_for(target, city_display: str = "Barcelona") -> dict[str, Any]:
    constraints = {
        "city": city_display,
        "checkin": "2026-06-12",
        "checkout": "2026-06-15",
        "adults": 2,
        "rooms": 1,
        "amenities": ["breakfast_included", "free_wifi"],
        "min_rating": 8.0,
        "min_price": 50,
        "max_price": 500,
        "verified_field": "brand",
    }
    instruction = (
        f"On Booking, search in {city_display} for June 12, 2026 to June 15, 2026 "
        "for 2 adults and 1 room. Use filters for breakfast included, free WiFi, "
        "rating at least 8, and nightly price between $50 and $500. Open the "
        f"{target.name} hotel detail page and answer with hotel name, rating, "
        "review count, nightly price, stars, property type, and distance from the "
        "center. Make sure the search/filter/sort flow uses or verifies the "
        "property field 'brand', then answer from visible page evidence."
    )
    expected = {
        "property_name": target.name,
        "rating": target.rating,
        "review_count": target.review_count,
        "nightly_price": target.price_per_night,
        "stars": target.stars,
        "property_type": target.property_type,
        "distance_from_center_km": target.distance_from_center,
        "brand": target.brand,
    }
    spec = _base("booking", BOOKING_FAMILY, target.name, instruction,
                 {"kind": "property", "name": target.name, "field": "brand", "brand": target.brand},
                 constraints, expected,
                 [target.name, f"{target.rating:.1f}", str(target.review_count), f"${target.price_per_night:.0f}",
                  f"{target.stars} stars", target.property_type, f"{target.distance_from_center:g} km", target.brand],
                 list(expected), 7)
    spec["validation"]["db_predicate"] = "booking.property_matches_constraints"
    spec["stability"]["date_anchor"] = True
    return spec


def _cambridge_detail_for(w) -> dict[str, Any]:
    defs = json.loads(w.definitions_json or "[]")
    expected = {
        "headword": w.headword,
        "part_of_speech": w.pos,
        "level": w.level,
        "uk_phonetic": w.phonetic_uk,
        "us_phonetic": w.phonetic_us,
        "first_definition": defs[0]["definition"] if defs else "",
    }
    instruction = (
        f"On Cambridge Dictionary, look up {w.headword!r} and answer with the headword, "
        "part of speech, CEFR level, UK phonetic, US phonetic, and first definition."
    )
    return _base("cambridge_dictionary", DEFAULT_FAMILIES["cambridge_dictionary"], w.headword, instruction,
                 {"kind": "word", "headword": w.headword, "slug": w.slug},
                 {"query": w.headword, "level": w.level}, expected,
                 [w.headword, w.pos, w.level, w.phonetic_uk, w.phonetic_us, expected["first_definition"][:40]],
                 list(expected), 3)


def _coursera_detail_for(c) -> dict[str, Any]:
    partner_name = c.partner.name if getattr(c, "partner", None) else ""
    expected = {
        "course_title": c.title,
        "partner": partner_name,
        "level": c.level,
        "rating": c.rating,
        "review_count": c.review_count,
        "duration": c.duration_text,
        "instructor": c.instructor,
        "certificate": c.has_certificate,
    }
    instruction = (
        f"On Coursera, search for {c.title!r}, open the course detail page, "
        "and answer with course title, partner, level, rating, review count, duration, instructor, and certificate availability."
    )
    return _base("coursera", DEFAULT_FAMILIES["coursera"], c.title, instruction,
                 {"kind": "course", "title": c.title, "slug": c.slug},
                 {"query": c.title, "level": c.level, "min_rating": c.rating}, expected,
                 [c.title, partner_name, c.level, f"{c.rating:g}", c.review_count, c.duration_text, c.instructor],
                 list(expected), 4)


def _espn_detail_for(t) -> dict[str, Any]:
    expected = {
        "team": t.full_name,
        "sport": t.sport_slug,
        "abbreviation": t.abbreviation,
        "wins": t.wins,
        "losses": t.losses,
        "win_pct": t.win_pct,
        "standing_rank": t.standing_rank,
        "streak": t.streak,
    }
    instruction = (
        f"On ESPN, open the {t.sport_slug.upper()} standings or team page for {t.full_name} and answer with "
        "team name, sport, abbreviation, wins, losses, win percentage, standings rank, and streak."
    )
    return _base("espn", DEFAULT_FAMILIES["espn"], t.full_name, instruction,
                 {"kind": "team", "full_name": t.full_name, "slug": t.slug},
                 {"sport": t.sport_slug, "sort": "standing_rank"}, expected,
                 [t.full_name, t.abbreviation, t.wins, t.losses, f"{t.win_pct:g}", t.standing_rank, t.streak],
                 list(expected), 4)


def _github_detail_for(r) -> dict[str, Any]:
    expected = {
        "repository": r.full_name,
        "description": r.description,
        "language": r.language,
        "license": r.license,
        "stars": r.stars_count,
        "forks": r.forks_count,
        "open_issues": r.open_issues_count,
        "default_branch": r.default_branch,
    }
    instruction = (
        f"On GitHub, search for repository {r.full_name!r}, open its repository page, "
        "and answer with repository full name, description, language, license, stars, forks, open issues, and default branch."
    )
    return _base("github", DEFAULT_FAMILIES["github"], r.full_name, instruction,
                 {"kind": "repository", "full_name": r.full_name},
                 {"query": r.full_name, "language": r.language, "license": r.license, "min_stars": r.stars_count}, expected,
                 [r.full_name, r.language, r.license, r.stars_count, r.forks_count, r.open_issues_count, r.default_branch],
                 list(expected), 5)


def _google_flights_detail_for(target) -> dict[str, Any]:
    origin = target.origin
    destination = target.destination
    dep_date = target.departure_date
    constraints = {
        "origin": origin.iata,
        "destination": destination.iata,
        "depart": dep_date.isoformat(),
        "passengers": 1,
        "trip_type": "one-way",
        "cabin": "Economy",
        "sort": "price",
    }
    instruction = (
        f"On Google Flights, search one-way flights from {origin.iata} to {destination.iata} "
        f"on {dep_date.strftime('%B %-d, %Y')} for 1 adult in Economy. Sort by price, "
        "open the cheapest matching flight detail page, and answer with flight number, airline, departure time, arrival time, stops, duration, price, and aircraft."
    )
    expected = {
        "flight_number": target.flight_number,
        "airline": target.airline,
        "origin": origin.iata,
        "destination": destination.iata,
        "departure_date": dep_date.isoformat(),
        "departure_time": target.departure_time,
        "arrival_time": target.arrival_time,
        "stops": target.stops,
        "duration": target.duration_str,
        "price": target.price,
        "aircraft": target.aircraft,
    }
    spec = _base("google_flights", FLIGHTS_FAMILY, target.flight_number, instruction,
                 {"kind": "flight", "flight_number": target.flight_number, "id": target.id},
                 constraints, expected,
                 [target.flight_number, target.airline, target.departure_time, target.arrival_time, f"${target.price:.0f}", target.aircraft],
                 list(expected), 6)
    spec["validation"]["db_predicate"] = "google_flights.flight_matches_constraints"
    spec["stability"]["date_anchor"] = True
    return spec


def _google_map_detail_for(p) -> dict[str, Any]:
    city = p.city.display_name if getattr(p, "city", None) and hasattr(p.city, "display_name") else (p.city.name if getattr(p, "city", None) and hasattr(p.city, "name") else "")
    category = p.category.name if getattr(p, "category", None) else ""
    expected = {
        "place_name": p.name,
        "category": category,
        "city": city,
        "rating": p.rating,
        "review_count": p.review_count,
        "address": p.address,
        "price_level": p.price_level,
        "parking_lot": p.has_parking_lot,
    }
    instruction = (
        f"On Google Maps, search for {p.name!r}, open the place detail page, "
        "and answer with place name, category, city, rating, review count, address, price level, and whether it has a parking lot."
    )
    return _base("google_map", DEFAULT_FAMILIES["google_map"], p.name, instruction,
                 {"kind": "place", "name": p.name, "slug": p.slug},
                 {"query": p.name, "min_rating": p.rating, "category": category}, expected,
                 [p.name, category, city, f"{p.rating:g}", p.review_count, p.address, p.price_level],
                 list(expected), 5)


def _huggingface_detail_for(r, app) -> dict[str, Any]:
    task = app.db.session.get(app.Task, r.task_id) if getattr(r, "task_id", None) else None
    task_name = task.display if task is not None else ""
    expected = {
        "repository": r.slug,
        "repo_type": r.repo_type,
        "task": task_name,
        "library": r.library,
        "license": r.license_display,
        "downloads": r.downloads,
        "likes": r.likes_count,
        "status": r.status,
    }
    instruction = (
        f"On Hugging Face, search for repository {r.slug!r}, open its repository page, "
        "and answer with repository slug, repo type, task, library, license, downloads, likes, and status."
    )
    return _base("huggingface", DEFAULT_FAMILIES["huggingface"], r.slug, instruction,
                 {"kind": "repository", "slug": r.slug, "repo_type": r.repo_type},
                 {"query": r.slug, "repo_type": r.repo_type, "library": r.library}, expected,
                 [r.slug, r.repo_type, task_name, r.library, r.license_display, r.downloads, r.likes_count, r.status],
                 list(expected), 5)


def _wolfram_detail_for(t) -> dict[str, Any]:
    examples = json.loads(t.examples or "[]")
    first = examples[0] if examples else {}
    expected = {
        "topic": t.name,
        "description": t.description,
        "first_example_query": first.get("query", ""),
        "first_example_result": first.get("result", ""),
        "is_featured": t.is_featured,
    }
    instruction = (
        f"On Wolfram Alpha, open the topic page for {t.name!r} and answer with topic name, "
        "description, first example query, first example result, and whether it is featured."
    )
    return _base("wolfram_alpha", DEFAULT_FAMILIES["wolfram_alpha"], t.name, instruction,
                 {"kind": "topic", "name": t.name, "slug": t.slug},
                 {"topic": t.name, "example_type": first.get("type", "")}, expected,
                 [t.name, t.description[:40], first.get("query", ""), first.get("result", "")],
                 list(expected), 3)


def _allrecipes_detail_specs(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("allrecipes", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Recipe.query.order_by(app.Recipe.review_count.desc(), app.Recipe.avg_rating.desc(), app.Recipe.id.asc()).all()
        return _raise_if_empty("allrecipes", DEFAULT_FAMILIES["allrecipes"], [_allrecipes_detail_for(r) for r in _page(rows, offset, limit)])


def _amazon_detail_specs(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("amazon", fresh_instance=True).module
    with app.app.app_context():
        rows = (app.Product.query.filter_by(is_prime=True, free_shipping=True)
                .order_by(app.Product.rating.desc(), app.Product.review_count.desc(), app.Product.id.asc()).all())
        return _raise_if_empty("amazon", DEFAULT_FAMILIES["amazon"], [_amazon_detail_for(p) for p in _page(rows, offset, limit)])


def _apple_detail_specs(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("apple", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Product.query.order_by(app.Product.is_new.desc(), app.Product.price.desc(), app.Product.id.asc()).all()
        return _raise_if_empty("apple", DEFAULT_FAMILIES["apple"], [_apple_detail_for(p) for p in _page(rows, offset, limit)])


def _arxiv_detail_specs(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("arxiv", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Paper.query.order_by(app.Paper.arxiv_id.desc(), app.Paper.id.asc()).all()
        return _raise_if_empty("arxiv", DEFAULT_FAMILIES["arxiv"], [_arxiv_detail_for(p) for p in _page(rows, offset, limit)])


def _booking_detail_specs(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("booking", fresh_instance=True).module
    with app.app.app_context():
        city = app.City.query.filter_by(key="barcelona").first()
        if city is None:
            raise RuntimeError("missing Booking Barcelona fixture")
        rows = (app.Property.query.filter_by(city_id=city.id)
                .filter(app.Property.breakfast_included.is_(True), app.Property.has_wifi.is_(True))
                .filter(app.Property.rating >= 8.0, app.Property.price_per_night >= 50, app.Property.price_per_night <= 500)
                .order_by(app.Property.rating.desc(), app.Property.review_count.desc(), app.Property.id.asc()).all())
        rows = sorted(rows, key=lambda p: (0 if p.name == "Praktik Èssens" else 1, -p.rating, -p.review_count, p.id))
        return _raise_if_empty("booking", BOOKING_FAMILY, [_booking_detail_for(p, city.display) for p in _page(rows, offset, limit)])


def _cambridge_detail_specs(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("cambridge_dictionary", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Word.query.order_by(app.Word.headword.asc(), app.Word.id.asc()).all()
        return _raise_if_empty("cambridge_dictionary", DEFAULT_FAMILIES["cambridge_dictionary"], [_cambridge_detail_for(w) for w in _page(rows, offset, limit)])


def _coursera_detail_specs(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("coursera", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Course.query.order_by(app.Course.rating.desc(), app.Course.review_count.desc(), app.Course.id.asc()).all()
        return _raise_if_empty("coursera", DEFAULT_FAMILIES["coursera"], [_coursera_detail_for(c) for c in _page(rows, offset, limit)])


def _espn_detail_specs(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("espn", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Team.query.order_by(app.Team.sport_slug.asc(), app.Team.standing_rank.asc(), app.Team.wins.desc(), app.Team.id.asc()).all()
        return _raise_if_empty("espn", DEFAULT_FAMILIES["espn"], [_espn_detail_for(t) for t in _page(rows, offset, limit)])


def _github_detail_specs(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("github", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Repository.query.order_by(app.Repository.stars_count.desc(), app.Repository.id.asc()).all()
        return _raise_if_empty("github", DEFAULT_FAMILIES["github"], [_github_detail_for(r) for r in _page(rows, offset, limit)])


def _google_flights_detail_specs(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("google_flights", fresh_instance=True).module
    with app.app.app_context():
        rows = (
            app.db.session.query(app.Flight.origin_id, app.Flight.destination_id, app.Flight.departure_date)
            .group_by(app.Flight.origin_id, app.Flight.destination_id, app.Flight.departure_date)
            .having(app.db.func.count(app.Flight.id) >= 2)
            .order_by(app.Flight.origin_id, app.Flight.destination_id, app.Flight.departure_date)
            .all()
        )
        specs: list[dict[str, Any]] = []
        for origin_id, destination_id, dep_date in _page(rows, offset, limit):
            target = (app.Flight.query
                      .filter_by(origin_id=origin_id, destination_id=destination_id, departure_date=dep_date)
                      .order_by(app.Flight.price.asc(), app.Flight.duration_minutes.asc(), app.Flight.id.asc())
                      .first())
            if target is not None:
                specs.append(_google_flights_detail_for(target))
        return _raise_if_empty("google_flights", FLIGHTS_FAMILY, specs)


def _google_map_detail_specs(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("google_map", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Place.query.order_by(app.Place.review_count.desc(), app.Place.rating.desc(), app.Place.id.asc()).all()
        return _raise_if_empty("google_map", DEFAULT_FAMILIES["google_map"], [_google_map_detail_for(p) for p in _page(rows, offset, limit)])


def _huggingface_detail_specs(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("huggingface", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Repository.query.order_by(app.Repository.downloads.desc(), app.Repository.likes_count.desc(), app.Repository.id.asc()).all()
        return _raise_if_empty("huggingface", DEFAULT_FAMILIES["huggingface"], [_huggingface_detail_for(r, app) for r in _page(rows, offset, limit)])


def _wolfram_detail_specs(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("wolfram_alpha", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Topic.query.order_by(app.Topic.is_featured.desc(), app.Topic.name.asc(), app.Topic.id.asc()).all()
        return _raise_if_empty("wolfram_alpha", DEFAULT_FAMILIES["wolfram_alpha"], [_wolfram_detail_for(t) for t in _page(rows, offset, limit)])


def _allrecipes_identify_specs() -> list[dict[str, Any]]:
    d = _allrecipes_specs()[0]
    e = d["expected_answer"]
    constraints = {
        "rating": e["rating"],
        "review_count": e["review_count"],
        "total_time": e["total_time"],
        "servings": e["servings"],
        "calories": e["calories"],
        "author": e["author"],
    }
    instruction = (
        "On Allrecipes, find the recipe whose detail page shows rating "
        f"{e['rating']}, {e['review_count']} reviews, total time {e['total_time']}, "
        f"servings {e['servings']}, {e['calories']} calories, and author {e['author']}. "
        "Answer only with the recipe title."
    )
    return [_identify_spec(d, IDENTIFY_FAMILIES["allrecipes"], e["title"], instruction, constraints, 6)]


def _amazon_identify_specs() -> list[dict[str, Any]]:
    d = _amazon_specs()[0]
    e = d["expected_answer"]
    constraints = {
        "brand": e["brand"],
        "category": e["category"],
        "price": e["price"],
        "rating": e["rating"],
        "review_count": e["review_count"],
        "condition": e["condition"],
        "free_shipping": e["free_shipping"],
        "free_returns": e["free_returns"],
    }
    instruction = (
        "On Amazon, identify the product in category "
        f"{e['category']} from brand {e['brand']} whose detail page shows price ${e['price']:g}, "
        f"rating {e['rating']}, {e['review_count']} reviews, condition {e['condition']}, "
        f"free shipping {_bool_word(e['free_shipping'])}, and free returns {_bool_word(e['free_returns'])}. "
        "Answer only with the product name."
    )
    return [_identify_spec(d, IDENTIFY_FAMILIES["amazon"], e["product_name"], instruction, constraints, 7)]


def _apple_identify_specs() -> list[dict[str, Any]]:
    d = _apple_specs()[0]
    e = d["expected_answer"]
    constraints = {
        "category": e["category"],
        "subtitle": e["subtitle"],
        "price": e["price"],
        "monthly_price": e["monthly_price"],
        "display": e["display"],
        "chip": e["chip"],
        "in_stock": e["in_stock"],
    }
    instruction = (
        "On Apple, identify the product in category "
        f"{e['category']} with subtitle {e['subtitle']!r}, full price ${e['price']:g}, "
        f"monthly price ${e['monthly_price']:g}, display {e['display']}, chip {e['chip']}, "
        f"and in-stock status {_bool_word(e['in_stock'])}. Answer only with the product name."
    )
    return [_identify_spec(d, IDENTIFY_FAMILIES["apple"], e["product_name"], instruction, constraints, 6)]


def _arxiv_identify_specs() -> list[dict[str, Any]]:
    d = _arxiv_specs()[0]
    e = d["expected_answer"]
    constraints = {
        "primary_subject": e["primary_subject"],
        "submitted_date": e["submitted_date"],
        "author_count": e["author_count"],
        "first_author": e["first_author"],
    }
    instruction = (
        "On arXiv, identify the paper in primary subject "
        f"{e['primary_subject']} submitted on {e['submitted_date']} with {e['author_count']} authors "
        f"and first author {e['first_author']}. Answer only with the paper title."
    )
    return [_identify_spec(d, IDENTIFY_FAMILIES["arxiv"], e["title"], instruction, constraints, 6)]


def _booking_identify_specs() -> list[dict[str, Any]]:
    d = _booking_specs()[0]
    e = d["expected_answer"]
    constraints = {
        "city": "Barcelona",
        "amenities": ["breakfast_included", "free_wifi"],
        "rating": e["rating"],
        "review_count": e["review_count"],
        "nightly_price": e["nightly_price"],
        "stars": e["stars"],
        "property_type": e["property_type"],
        "distance_from_center_km": e["distance_from_center_km"],
        "brand": e["brand"],
    }
    instruction = (
        "On Booking, search Barcelona stays and identify the property with breakfast included and free WiFi, "
        f"rating {e['rating']}, {e['review_count']} reviews, nightly price ${e['nightly_price']:g}, "
        f"{e['stars']} stars, property type {e['property_type']}, {e['distance_from_center_km']:g} km from the center, "
        f"and brand {e['brand']}. Answer only with the property name."
    )
    spec = _identify_spec(d, IDENTIFY_FAMILIES["booking"], e["property_name"], instruction, constraints, 8)
    spec["stability"]["date_anchor"] = True
    return [spec]


def _cambridge_identify_specs() -> list[dict[str, Any]]:
    d = _cambridge_specs()[0]
    e = d["expected_answer"]
    constraints = {
        "part_of_speech": e["part_of_speech"],
        "level": e["level"],
        "uk_phonetic": e["uk_phonetic"],
        "us_phonetic": e["us_phonetic"],
        "first_definition": e["first_definition"],
    }
    instruction = (
        "On Cambridge Dictionary, identify the headword whose entry is a "
        f"{e['part_of_speech']} at level {e['level']}, has UK phonetic {e['uk_phonetic']}, "
        f"US phonetic {e['us_phonetic']}, and first definition {e['first_definition']!r}. "
        "Answer only with the headword."
    )
    return [_identify_spec(d, IDENTIFY_FAMILIES["cambridge_dictionary"], e["headword"], instruction, constraints, 5)]


def _coursera_identify_specs() -> list[dict[str, Any]]:
    d = _coursera_specs()[0]
    e = d["expected_answer"]
    constraints = {
        "partner": e["partner"],
        "level": e["level"],
        "rating": e["rating"],
        "review_count": e["review_count"],
        "duration": e["duration"],
        "instructor": e["instructor"],
        "certificate": e["certificate"],
    }
    instruction = (
        "On Coursera, identify the course from partner "
        f"{e['partner']} at level {e['level']} with rating {e['rating']}, {e['review_count']} reviews, "
        f"duration {e['duration']}, instructor {e['instructor']}, and certificate availability {_bool_word(e['certificate'])}. "
        "Answer only with the course title."
    )
    return [_identify_spec(d, IDENTIFY_FAMILIES["coursera"], e["course_title"], instruction, constraints, 6)]


def _espn_identify_specs() -> list[dict[str, Any]]:
    d = _espn_specs()[0]
    e = d["expected_answer"]
    constraints = {
        "sport": e["sport"],
        "abbreviation": e["abbreviation"],
        "wins": e["wins"],
        "losses": e["losses"],
        "win_pct": e["win_pct"],
        "standing_rank": e["standing_rank"],
        "streak": e["streak"],
    }
    instruction = (
        "On ESPN, identify the team in sport "
        f"{e['sport']} with abbreviation {e['abbreviation']}, record {e['wins']}-{e['losses']}, "
        f"win percentage {e['win_pct']}, standings rank {e['standing_rank']}, and streak {e['streak']}. "
        "Answer only with the team name."
    )
    return [_identify_spec(d, IDENTIFY_FAMILIES["espn"], e["team"], instruction, constraints, 5)]


def _github_identify_specs() -> list[dict[str, Any]]:
    d = _github_specs()[0]
    e = d["expected_answer"]
    constraints = {
        "description": e["description"],
        "language": e["language"],
        "license": e["license"],
        "stars": e["stars"],
        "forks": e["forks"],
        "open_issues": e["open_issues"],
        "default_branch": e["default_branch"],
    }
    instruction = (
        "On GitHub, identify the repository whose page description is "
        f"{e['description']!r}, language {e['language']}, license {e['license']}, "
        f"{e['stars']} stars, {e['forks']} forks, {e['open_issues']} open issues, "
        f"and default branch {e['default_branch']}. Answer only with owner/repository."
    )
    return [_identify_spec(d, IDENTIFY_FAMILIES["github"], e["repository"], instruction, constraints, 6)]


def _google_flights_identify_specs() -> list[dict[str, Any]]:
    d = _google_flights_specs()[0]
    e = d["expected_answer"]
    constraints = {
        "origin": e["origin"],
        "destination": e["destination"],
        "departure_date": e["departure_date"],
        "airline": e["airline"],
        "departure_time": e["departure_time"],
        "arrival_time": e["arrival_time"],
        "stops": e["stops"],
        "duration": e["duration"],
        "price": e["price"],
        "aircraft": e["aircraft"],
    }
    instruction = (
        "On Google Flights, identify the one-way flight from "
        f"{e['origin']} to {e['destination']} on {e['departure_date']} operated by {e['airline']}, "
        f"departing {e['departure_time']}, arriving {e['arrival_time']}, with {e['stops']} stops, "
        f"duration {e['duration']}, price ${e['price']:g}, and aircraft {e['aircraft']}. "
        "Answer only with the flight number."
    )
    spec = _identify_spec(d, IDENTIFY_FAMILIES["google_flights"], e["flight_number"], instruction, constraints, 7)
    spec["stability"]["date_anchor"] = True
    return [spec]


def _google_map_identify_specs() -> list[dict[str, Any]]:
    d = _google_map_specs()[0]
    e = d["expected_answer"]
    constraints = {
        "category": e["category"],
        "city": e["city"],
        "rating": e["rating"],
        "review_count": e["review_count"],
        "address": e["address"],
        "price_level": e["price_level"],
        "parking_lot": e["parking_lot"],
    }
    instruction = (
        "On Google Maps, identify the place in category "
        f"{e['category']} in {e['city']} with rating {e['rating']}, {e['review_count']} reviews, "
        f"address {e['address']!r}, price level {e['price_level']}, and parking lot {_bool_word(e['parking_lot'])}. "
        "Answer only with the place name."
    )
    return [_identify_spec(d, IDENTIFY_FAMILIES["google_map"], e["place_name"], instruction, constraints, 6)]


def _huggingface_identify_specs() -> list[dict[str, Any]]:
    d = _huggingface_specs()[0]
    e = d["expected_answer"]
    constraints = {
        "repo_type": e["repo_type"],
        "task": e["task"],
        "library": e["library"],
        "license": e["license"],
        "downloads": e["downloads"],
        "likes": e["likes"],
        "status": e["status"],
    }
    instruction = (
        "On Hugging Face, identify the repository with repo type "
        f"{e['repo_type']}, task {e['task']}, library {e['library']}, license {e['license']}, "
        f"{e['downloads']} downloads, {e['likes']} likes, and status {e['status']}. "
        "Answer only with the repository slug."
    )
    return [_identify_spec(d, IDENTIFY_FAMILIES["huggingface"], e["repository"], instruction, constraints, 6)]


def _wolfram_identify_specs() -> list[dict[str, Any]]:
    d = _wolfram_specs()[0]
    e = d["expected_answer"]
    constraints = {
        "first_example_query": e["first_example_query"],
        "first_example_result": e["first_example_result"],
        "is_featured": e["is_featured"],
    }
    instruction = (
        "On Wolfram Alpha, identify the topic whose first example query is "
        f"{e['first_example_query']!r}, whose first example result is {e['first_example_result']!r}, "
        f"and whose featured status is {_bool_word(e['is_featured'])}. Answer only with the topic name."
    )
    return [_identify_spec(d, IDENTIFY_FAMILIES["wolfram_alpha"], e["topic"], instruction, constraints, 5)]


def _allrecipes_identify_from_detail(d: dict[str, Any]) -> dict[str, Any]:
    e = d["expected_answer"]
    constraints = {
        "rating": e["rating"],
        "review_count": e["review_count"],
        "total_time": e["total_time"],
        "servings": e["servings"],
        "calories": e["calories"],
        "author": e["author"],
    }
    instruction = (
        "On Allrecipes, find the recipe whose detail page shows rating "
        f"{e['rating']}, {e['review_count']} reviews, total time {e['total_time']}, "
        f"servings {e['servings']}, {e['calories']} calories, and author {e['author']}. "
        "Answer only with the recipe title."
    )
    return _identify_spec(d, IDENTIFY_FAMILIES["allrecipes"], e["title"], instruction, constraints, 6)


def _amazon_identify_from_detail(d: dict[str, Any]) -> dict[str, Any]:
    e = d["expected_answer"]
    constraints = {
        "brand": e["brand"],
        "category": e["category"],
        "price": e["price"],
        "rating": e["rating"],
        "review_count": e["review_count"],
        "condition": e["condition"],
        "free_shipping": e["free_shipping"],
        "free_returns": e["free_returns"],
    }
    instruction = (
        "On Amazon, identify the product in category "
        f"{e['category']} from brand {e['brand']} whose detail page shows price ${e['price']:g}, "
        f"rating {e['rating']}, {e['review_count']} reviews, condition {e['condition']}, "
        f"free shipping {_bool_word(e['free_shipping'])}, and free returns {_bool_word(e['free_returns'])}. "
        "Answer only with the product name."
    )
    return _identify_spec(d, IDENTIFY_FAMILIES["amazon"], e["product_name"], instruction, constraints, 7)


def _apple_identify_from_detail(d: dict[str, Any]) -> dict[str, Any]:
    e = d["expected_answer"]
    constraints = {
        "category": e["category"],
        "subtitle": e["subtitle"],
        "price": e["price"],
        "monthly_price": e["monthly_price"],
        "display": e["display"],
        "chip": e["chip"],
        "in_stock": e["in_stock"],
    }
    instruction = (
        "On Apple, identify the product in category "
        f"{e['category']} with subtitle {e['subtitle']!r}, full price ${e['price']:g}, "
        f"monthly price ${e['monthly_price']:g}, display {e['display']}, chip {e['chip']}, "
        f"and in-stock status {_bool_word(e['in_stock'])}. Answer only with the product name."
    )
    return _identify_spec(d, IDENTIFY_FAMILIES["apple"], e["product_name"], instruction, constraints, 6)


def _arxiv_identify_from_detail(d: dict[str, Any]) -> dict[str, Any]:
    e = d["expected_answer"]
    constraints = {
        "primary_subject": e["primary_subject"],
        "submitted_date": e["submitted_date"],
        "author_count": e["author_count"],
        "first_author": e["first_author"],
    }
    instruction = (
        "On arXiv, identify the paper in primary subject "
        f"{e['primary_subject']} submitted on {e['submitted_date']} with {e['author_count']} authors "
        f"and first author {e['first_author']}. Answer only with the paper title."
    )
    return _identify_spec(d, IDENTIFY_FAMILIES["arxiv"], e["title"], instruction, constraints, 6)


def _booking_identify_from_detail(d: dict[str, Any]) -> dict[str, Any]:
    e = d["expected_answer"]
    constraints = {
        "city": d["constraints"]["city"],
        "amenities": ["breakfast_included", "free_wifi"],
        "rating": e["rating"],
        "review_count": e["review_count"],
        "nightly_price": e["nightly_price"],
        "stars": e["stars"],
        "property_type": e["property_type"],
        "distance_from_center_km": e["distance_from_center_km"],
        "brand": e["brand"],
    }
    instruction = (
        f"On Booking, search {d['constraints']['city']} stays and identify the property with breakfast included and free WiFi, "
        f"rating {e['rating']}, {e['review_count']} reviews, nightly price ${e['nightly_price']:g}, "
        f"{e['stars']} stars, property type {e['property_type']}, {e['distance_from_center_km']:g} km from the center, "
        f"and brand {e['brand']}. Answer only with the property name."
    )
    spec = _identify_spec(d, IDENTIFY_FAMILIES["booking"], e["property_name"], instruction, constraints, 8)
    spec["stability"]["date_anchor"] = True
    return spec


def _cambridge_identify_from_detail(d: dict[str, Any]) -> dict[str, Any]:
    e = d["expected_answer"]
    constraints = {
        "part_of_speech": e["part_of_speech"],
        "level": e["level"],
        "uk_phonetic": e["uk_phonetic"],
        "us_phonetic": e["us_phonetic"],
        "first_definition": e["first_definition"],
    }
    instruction = (
        "On Cambridge Dictionary, identify the headword whose entry is a "
        f"{e['part_of_speech']} at level {e['level']}, has UK phonetic {e['uk_phonetic']}, "
        f"US phonetic {e['us_phonetic']}, and first definition {e['first_definition']!r}. "
        "Answer only with the headword."
    )
    return _identify_spec(d, IDENTIFY_FAMILIES["cambridge_dictionary"], e["headword"], instruction, constraints, 5)


def _coursera_identify_from_detail(d: dict[str, Any]) -> dict[str, Any]:
    e = d["expected_answer"]
    constraints = {
        "partner": e["partner"],
        "level": e["level"],
        "rating": e["rating"],
        "review_count": e["review_count"],
        "duration": e["duration"],
        "instructor": e["instructor"],
        "certificate": e["certificate"],
    }
    instruction = (
        "On Coursera, identify the course from partner "
        f"{e['partner']} at level {e['level']} with rating {e['rating']}, {e['review_count']} reviews, "
        f"duration {e['duration']}, instructor {e['instructor']}, and certificate availability {_bool_word(e['certificate'])}. "
        "Answer only with the course title."
    )
    return _identify_spec(d, IDENTIFY_FAMILIES["coursera"], e["course_title"], instruction, constraints, 6)


def _espn_identify_from_detail(d: dict[str, Any]) -> dict[str, Any]:
    e = d["expected_answer"]
    constraints = {
        "sport": e["sport"],
        "abbreviation": e["abbreviation"],
        "wins": e["wins"],
        "losses": e["losses"],
        "win_pct": e["win_pct"],
        "standing_rank": e["standing_rank"],
        "streak": e["streak"],
    }
    instruction = (
        "On ESPN, identify the team in sport "
        f"{e['sport']} with abbreviation {e['abbreviation']}, record {e['wins']}-{e['losses']}, "
        f"win percentage {e['win_pct']}, standings rank {e['standing_rank']}, and streak {e['streak']}. "
        "Answer only with the team name."
    )
    return _identify_spec(d, IDENTIFY_FAMILIES["espn"], e["team"], instruction, constraints, 5)


def _github_identify_from_detail(d: dict[str, Any]) -> dict[str, Any]:
    e = d["expected_answer"]
    constraints = {
        "description": e["description"],
        "language": e["language"],
        "license": e["license"],
        "stars": e["stars"],
        "forks": e["forks"],
        "open_issues": e["open_issues"],
        "default_branch": e["default_branch"],
    }
    instruction = (
        "On GitHub, identify the repository whose page description is "
        f"{e['description']!r}, language {e['language']}, license {e['license']}, "
        f"{e['stars']} stars, {e['forks']} forks, {e['open_issues']} open issues, "
        f"and default branch {e['default_branch']}. Answer only with owner/repository."
    )
    return _identify_spec(d, IDENTIFY_FAMILIES["github"], e["repository"], instruction, constraints, 6)


def _google_flights_identify_from_detail(d: dict[str, Any]) -> dict[str, Any]:
    e = d["expected_answer"]
    constraints = {
        "origin": e["origin"],
        "destination": e["destination"],
        "departure_date": e["departure_date"],
        "airline": e["airline"],
        "departure_time": e["departure_time"],
        "arrival_time": e["arrival_time"],
        "stops": e["stops"],
        "duration": e["duration"],
        "price": e["price"],
        "aircraft": e["aircraft"],
    }
    instruction = (
        "On Google Flights, identify the one-way flight from "
        f"{e['origin']} to {e['destination']} on {e['departure_date']} operated by {e['airline']}, "
        f"departing {e['departure_time']}, arriving {e['arrival_time']}, with {e['stops']} stops, "
        f"duration {e['duration']}, price ${e['price']:g}, and aircraft {e['aircraft']}. "
        "Answer only with the flight number."
    )
    spec = _identify_spec(d, IDENTIFY_FAMILIES["google_flights"], e["flight_number"], instruction, constraints, 7)
    spec["stability"]["date_anchor"] = True
    return spec


def _google_map_identify_from_detail(d: dict[str, Any]) -> dict[str, Any]:
    e = d["expected_answer"]
    constraints = {
        "category": e["category"],
        "city": e["city"],
        "rating": e["rating"],
        "review_count": e["review_count"],
        "address": e["address"],
        "price_level": e["price_level"],
        "parking_lot": e["parking_lot"],
    }
    instruction = (
        "On Google Maps, identify the place in category "
        f"{e['category']} in {e['city']} with rating {e['rating']}, {e['review_count']} reviews, "
        f"address {e['address']!r}, price level {e['price_level']}, and parking lot {_bool_word(e['parking_lot'])}. "
        "Answer only with the place name."
    )
    return _identify_spec(d, IDENTIFY_FAMILIES["google_map"], e["place_name"], instruction, constraints, 6)


def _huggingface_identify_from_detail(d: dict[str, Any]) -> dict[str, Any]:
    e = d["expected_answer"]
    constraints = {
        "repo_type": e["repo_type"],
        "task": e["task"],
        "library": e["library"],
        "license": e["license"],
        "downloads": e["downloads"],
        "likes": e["likes"],
        "status": e["status"],
    }
    instruction = (
        "On Hugging Face, identify the repository with repo type "
        f"{e['repo_type']}, task {e['task']}, library {e['library']}, license {e['license']}, "
        f"{e['downloads']} downloads, {e['likes']} likes, and status {e['status']}. "
        "Answer only with the repository slug."
    )
    return _identify_spec(d, IDENTIFY_FAMILIES["huggingface"], e["repository"], instruction, constraints, 6)


def _wolfram_identify_from_detail(d: dict[str, Any]) -> dict[str, Any]:
    e = d["expected_answer"]
    constraints = {
        "first_example_query": e["first_example_query"],
        "first_example_result": e["first_example_result"],
        "is_featured": e["is_featured"],
    }
    instruction = (
        "On Wolfram Alpha, identify the topic whose first example query is "
        f"{e['first_example_query']!r}, whose first example result is {e['first_example_result']!r}, "
        f"and whose featured status is {_bool_word(e['is_featured'])}. Answer only with the topic name."
    )
    return _identify_spec(d, IDENTIFY_FAMILIES["wolfram_alpha"], e["topic"], instruction, constraints, 5)


IDENTIFY_FROM_DETAIL = {
    "allrecipes": _allrecipes_identify_from_detail,
    "amazon": _amazon_identify_from_detail,
    "apple": _apple_identify_from_detail,
    "arxiv": _arxiv_identify_from_detail,
    "booking": _booking_identify_from_detail,
    "cambridge_dictionary": _cambridge_identify_from_detail,
    "coursera": _coursera_identify_from_detail,
    "espn": _espn_identify_from_detail,
    "github": _github_identify_from_detail,
    "google_flights": _google_flights_identify_from_detail,
    "google_map": _google_map_identify_from_detail,
    "huggingface": _huggingface_identify_from_detail,
    "wolfram_alpha": _wolfram_identify_from_detail,
}


def _allrecipes_mutation_specs() -> list[dict[str, Any]]:
    app = load_site_app("allrecipes", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        r = _first_absent(app, app.Recipe, app.RecipeBoxItem, user.id, "recipe_id")
        instruction = f"Sign in as {user.email} and save the recipe {r.title!r} to your Recipe Box. Then answer with the saved recipe title."
        return [_mutation_spec("allrecipes", MUTATION_FAMILIES["allrecipes"], r.title, instruction, _actor(user.email),
                               {"kind": "recipe", "id": r.id, "title": r.title, "slug": r.slug},
                               {"action": "save_to_recipe_box", "quantity": 1},
                               "allrecipes.recipe_box_item_absent", "allrecipes.recipe_box_item_exists",
                               {"identity": r.title, "saved": True}, 7)]


def _amazon_mutation_specs() -> list[dict[str, Any]]:
    app = load_site_app("amazon", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        p = _first_absent(app, app.Product, app.CartItem, user.id, "product_id")
        instruction = f"Sign in as {user.email} and add {p.name!r} to the Amazon cart with quantity 1. Then answer with the cart item name and quantity."
        return [_mutation_spec("amazon", MUTATION_FAMILIES["amazon"], p.name, instruction, _actor(user.email),
                               {"kind": "product", "id": p.id, "name": p.name, "slug": p.slug},
                               {"action": "add_to_cart", "quantity": 1},
                               "amazon.cart_item_absent", "amazon.cart_item_quantity",
                               {"identity": p.name, "quantity": 1}, 7)]


def _apple_mutation_specs() -> list[dict[str, Any]]:
    app = load_site_app("apple", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        p = _first_absent(app, app.Product, app.CartItem, user.id, "product_id")
        instruction = f"Sign in as {user.email} and add {p.name!r} to your Apple bag with quantity 1. Then answer with the bag item name and quantity."
        return [_mutation_spec("apple", MUTATION_FAMILIES["apple"], p.name, instruction, _actor(user.email),
                               {"kind": "product", "id": p.id, "name": p.name, "slug": p.slug},
                               {"action": "add_to_cart", "quantity": 1},
                               "apple.cart_item_absent", "apple.cart_item_quantity",
                               {"identity": p.name, "quantity": 1}, 7)]


def _arxiv_mutation_specs() -> list[dict[str, Any]]:
    app = load_site_app("arxiv", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        p = _first_absent(app, app.Paper, app.LibraryItem, user.id, "paper_id")
        instruction = f"Sign in as {user.email} and add arXiv paper {p.arxiv_id} to your library. Then answer with the paper ID and library status."
        return [_mutation_spec("arxiv", MUTATION_FAMILIES["arxiv"], p.arxiv_id, instruction, _actor(user.email),
                               {"kind": "paper", "id": p.id, "arxiv_id": p.arxiv_id, "title": p.title},
                               {"action": "add_to_library", "folder": "General"},
                               "arxiv.library_item_absent", "arxiv.library_item_exists",
                               {"identity": p.arxiv_id, "saved": True}, 7)]


def _booking_mutation_specs() -> list[dict[str, Any]]:
    app = load_site_app("booking", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app, "sophie.m@test.com")
        p = _first_absent(app, app.Property, app.SavedProperty, user.id, "property_id")
        instruction = f"Sign in as {user.email} and save the Booking property {p.name!r}. Then answer with the saved property name."
        return [_mutation_spec("booking", MUTATION_FAMILIES["booking"], p.name, instruction, _actor(user.email),
                               {"kind": "property", "id": p.id, "name": p.name, "slug": p.slug},
                               {"action": "save_property", "list_name": "Saved properties"},
                               "booking.saved_property_absent", "booking.saved_property_exists",
                               {"identity": p.name, "saved": True}, 7)]


def _cambridge_mutation_specs() -> list[dict[str, Any]]:
    app = load_site_app("cambridge_dictionary", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        w = _first_absent(app, app.Word, app.SavedWord, user.id, "word_id")
        instruction = f"Sign in as {user.email} and save the Cambridge Dictionary word {w.headword!r}. Then answer with the saved headword."
        return [_mutation_spec("cambridge_dictionary", MUTATION_FAMILIES["cambridge_dictionary"], w.headword, instruction, _actor(user.email),
                               {"kind": "word", "id": w.id, "headword": w.headword, "slug": w.slug},
                               {"action": "save_word"},
                               "cambridge_dictionary.saved_word_absent", "cambridge_dictionary.saved_word_exists",
                               {"identity": w.headword, "saved": True}, 6)]


def _coursera_mutation_specs() -> list[dict[str, Any]]:
    app = load_site_app("coursera", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        c = _first_absent(app, app.Course, app.SavedCourse, user.id, "course_id")
        instruction = f"Sign in as {user.email} and save the Coursera course {c.title!r} to your wishlist. Then answer with the saved course title."
        return [_mutation_spec("coursera", MUTATION_FAMILIES["coursera"], c.title, instruction, _actor(user.email),
                               {"kind": "course", "id": c.id, "title": c.title, "slug": c.slug},
                               {"action": "save_course"},
                               "coursera.saved_course_absent", "coursera.saved_course_exists",
                               {"identity": c.title, "saved": True}, 7)]


def _espn_mutation_specs() -> list[dict[str, Any]]:
    app = load_site_app("espn", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        def extra(q, obj): return q.filter_by(item_type="team", item_id=obj.id)
        t = _first_absent(app, app.Team, app.UserFavorite, user.id, "item_id", extra_filter=extra)
        instruction = f"Sign in as {user.email} and add {t.full_name} to your ESPN favorites. Then answer with the favorite team name."
        return [_mutation_spec("espn", MUTATION_FAMILIES["espn"], t.full_name, instruction, _actor(user.email),
                               {"kind": "team", "id": t.id, "full_name": t.full_name, "slug": t.slug},
                               {"action": "favorite_team", "item_type": "team"},
                               "espn.favorite_team_absent", "espn.favorite_team_exists",
                               {"identity": t.full_name, "favorited": True}, 6)]


def _github_mutation_specs() -> list[dict[str, Any]]:
    app = load_site_app("github", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app, "alice.j@test.com")
        r = _first_absent(app, app.Repository, app.Star, user.id, "repo_id")
        instruction = f"Sign in as {user.email} and star the GitHub repository {r.full_name}. Then answer with the starred repository full name."
        return [_mutation_spec("github", MUTATION_FAMILIES["github"], r.full_name, instruction, _actor(user.email),
                               {"kind": "repository", "id": r.id, "full_name": r.full_name},
                               {"action": "star_repository"},
                               "github.repo_star_absent", "github.repo_star_exists",
                               {"identity": r.full_name, "starred": True}, 7)]


def _google_flights_mutation_specs() -> list[dict[str, Any]]:
    app = load_site_app("google_flights", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        f = _first_absent(app, app.Flight, app.TrackedFlight, user.id, "flight_id")
        instruction = f"Sign in as {user.email} and track flight {f.flight_number} from {f.origin.iata} to {f.destination.iata}. Then answer with the tracked flight number."
        return [_mutation_spec("google_flights", MUTATION_FAMILIES["google_flights"], f.flight_number, instruction, _actor(user.email),
                               {"kind": "flight", "id": f.id, "flight_number": f.flight_number},
                               {"action": "track_flight"},
                               "google_flights.tracked_flight_absent", "google_flights.tracked_flight_exists",
                               {"identity": f.flight_number, "tracked": True}, 7)]


def _google_map_mutation_specs() -> list[dict[str, Any]]:
    app = load_site_app("google_map", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        default_list = app.SavedList.query.filter_by(user_id=user.id, is_default=True).first() or app.SavedList.query.filter_by(user_id=user.id).first()
        def extra(q, obj): return q.filter_by(place_id=obj.id)
        p = _first_absent(app, app.Place, app.SavedPlace, user.id, "place_id", extra_filter=extra)
        instruction = f"Sign in as {user.email} and save the Google Maps place {p.name!r} to your saved places. Then answer with the saved place name."
        return [_mutation_spec("google_map", MUTATION_FAMILIES["google_map"], p.name, instruction, _actor(user.email),
                               {"kind": "place", "id": p.id, "name": p.name, "slug": p.slug, "list_id": default_list.id if default_list else None},
                               {"action": "save_place", "list_id": default_list.id if default_list else None},
                               "google_map.saved_place_absent", "google_map.saved_place_exists",
                               {"identity": p.name, "saved": True}, 7)]


def _huggingface_mutation_specs() -> list[dict[str, Any]]:
    app = load_site_app("huggingface", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        r = _first_absent(app, app.Repository, app.Like, user.id, "repo_id")
        instruction = f"Sign in as {user.email} and like the Hugging Face repository {r.slug}. Then answer with the liked repository slug."
        return [_mutation_spec("huggingface", MUTATION_FAMILIES["huggingface"], r.slug, instruction, _actor(user.email),
                               {"kind": "repository", "id": r.id, "slug": r.slug, "repo_type": r.repo_type},
                               {"action": "like_repository"},
                               "huggingface.repo_like_absent", "huggingface.repo_like_exists",
                               {"identity": r.slug, "liked": True}, 7)]


def _wolfram_mutation_specs() -> list[dict[str, Any]]:
    app = load_site_app("wolfram_alpha", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        t = _first_absent(app, app.Topic, app.Favorite, user.id, "topic_id")
        instruction = f"Sign in as {user.email} and add the Wolfram Alpha topic {t.name!r} to favorites. Then answer with the favorite topic name."
        return [_mutation_spec("wolfram_alpha", MUTATION_FAMILIES["wolfram_alpha"], t.name, instruction, _actor(user.email),
                               {"kind": "topic", "id": t.id, "name": t.name, "slug": t.slug},
                               {"action": "favorite_topic"},
                               "wolfram_alpha.favorite_topic_absent", "wolfram_alpha.favorite_topic_exists",
                               {"identity": t.name, "favorited": True}, 6)]


def _absent_page(rows, mutation_cls, user_id: int, fk_name: str, offset: int, limit: int, extra_filter=None):
    selected = []
    skipped = 0
    for obj in rows:
        q = mutation_cls.query.filter_by(user_id=user_id)
        if extra_filter is not None:
            q = extra_filter(q, obj)
        else:
            q = q.filter(getattr(mutation_cls, fk_name) == obj.id)
        if q.first() is not None:
            continue
        if skipped < offset:
            skipped += 1
            continue
        selected.append(obj)
        if len(selected) >= limit:
            break
    return selected


def _allrecipes_mutation_for(user, r) -> dict[str, Any]:
    instruction = f"Sign in as {user.email} and save the recipe {r.title!r} to your Recipe Box. Then answer with the saved recipe title."
    return _mutation_spec("allrecipes", MUTATION_FAMILIES["allrecipes"], r.title, instruction, _actor(user.email),
                          {"kind": "recipe", "id": r.id, "title": r.title, "slug": r.slug},
                          {"action": "save_to_recipe_box", "quantity": 1},
                          "allrecipes.recipe_box_item_absent", "allrecipes.recipe_box_item_exists",
                          {"identity": r.title, "saved": True}, 7)


def _amazon_mutation_for(user, p) -> dict[str, Any]:
    instruction = f"Sign in as {user.email} and add {p.name!r} to the Amazon cart with quantity 1. Then answer with the cart item name and quantity."
    return _mutation_spec("amazon", MUTATION_FAMILIES["amazon"], p.name, instruction, _actor(user.email),
                          {"kind": "product", "id": p.id, "name": p.name, "slug": p.slug},
                          {"action": "add_to_cart", "quantity": 1},
                          "amazon.cart_item_absent", "amazon.cart_item_quantity",
                          {"identity": p.name, "quantity": 1}, 7)


def _apple_mutation_for(user, p) -> dict[str, Any]:
    instruction = f"Sign in as {user.email} and add {p.name!r} to your Apple bag with quantity 1. Then answer with the bag item name and quantity."
    return _mutation_spec("apple", MUTATION_FAMILIES["apple"], p.name, instruction, _actor(user.email),
                          {"kind": "product", "id": p.id, "name": p.name, "slug": p.slug},
                          {"action": "add_to_cart", "quantity": 1},
                          "apple.cart_item_absent", "apple.cart_item_quantity",
                          {"identity": p.name, "quantity": 1}, 7)


def _arxiv_mutation_for(user, p) -> dict[str, Any]:
    instruction = f"Sign in as {user.email} and add arXiv paper {p.arxiv_id} to your library. Then answer with the paper ID and library status."
    return _mutation_spec("arxiv", MUTATION_FAMILIES["arxiv"], p.arxiv_id, instruction, _actor(user.email),
                          {"kind": "paper", "id": p.id, "arxiv_id": p.arxiv_id, "title": p.title},
                          {"action": "add_to_library", "folder": "General"},
                          "arxiv.library_item_absent", "arxiv.library_item_exists",
                          {"identity": p.arxiv_id, "saved": True}, 7)


def _booking_mutation_for(user, p) -> dict[str, Any]:
    instruction = f"Sign in as {user.email} and save the Booking property {p.name!r}. Then answer with the saved property name."
    return _mutation_spec("booking", MUTATION_FAMILIES["booking"], p.name, instruction, _actor(user.email),
                          {"kind": "property", "id": p.id, "name": p.name, "slug": p.slug},
                          {"action": "save_property", "list_name": "Saved properties"},
                          "booking.saved_property_absent", "booking.saved_property_exists",
                          {"identity": p.name, "saved": True}, 7)


def _cambridge_mutation_for(user, w) -> dict[str, Any]:
    instruction = f"Sign in as {user.email} and save the Cambridge Dictionary word {w.headword!r}. Then answer with the saved headword."
    return _mutation_spec("cambridge_dictionary", MUTATION_FAMILIES["cambridge_dictionary"], w.headword, instruction, _actor(user.email),
                          {"kind": "word", "id": w.id, "headword": w.headword, "slug": w.slug},
                          {"action": "save_word"},
                          "cambridge_dictionary.saved_word_absent", "cambridge_dictionary.saved_word_exists",
                          {"identity": w.headword, "saved": True}, 6)


def _coursera_mutation_for(user, c) -> dict[str, Any]:
    instruction = f"Sign in as {user.email} and save the Coursera course {c.title!r} to your wishlist. Then answer with the saved course title."
    return _mutation_spec("coursera", MUTATION_FAMILIES["coursera"], c.title, instruction, _actor(user.email),
                          {"kind": "course", "id": c.id, "title": c.title, "slug": c.slug},
                          {"action": "save_course"},
                          "coursera.saved_course_absent", "coursera.saved_course_exists",
                          {"identity": c.title, "saved": True}, 7)


def _espn_mutation_for(user, t) -> dict[str, Any]:
    instruction = f"Sign in as {user.email} and add {t.full_name} to your ESPN favorites. Then answer with the favorite team name."
    return _mutation_spec("espn", MUTATION_FAMILIES["espn"], t.full_name, instruction, _actor(user.email),
                          {"kind": "team", "id": t.id, "full_name": t.full_name, "slug": t.slug},
                          {"action": "favorite_team", "item_type": "team"},
                          "espn.favorite_team_absent", "espn.favorite_team_exists",
                          {"identity": t.full_name, "favorited": True}, 6)


def _github_mutation_for(user, r) -> dict[str, Any]:
    instruction = f"Sign in as {user.email} and star the GitHub repository {r.full_name}. Then answer with the starred repository full name."
    return _mutation_spec("github", MUTATION_FAMILIES["github"], r.full_name, instruction, _actor(user.email),
                          {"kind": "repository", "id": r.id, "full_name": r.full_name},
                          {"action": "star_repository"},
                          "github.repo_star_absent", "github.repo_star_exists",
                          {"identity": r.full_name, "starred": True}, 7)


def _google_flights_mutation_for(user, f) -> dict[str, Any]:
    instruction = f"Sign in as {user.email} and track flight {f.flight_number} from {f.origin.iata} to {f.destination.iata}. Then answer with the tracked flight number."
    return _mutation_spec("google_flights", MUTATION_FAMILIES["google_flights"], f.flight_number, instruction, _actor(user.email),
                          {"kind": "flight", "id": f.id, "flight_number": f.flight_number},
                          {"action": "track_flight"},
                          "google_flights.tracked_flight_absent", "google_flights.tracked_flight_exists",
                          {"identity": f.flight_number, "tracked": True}, 7)


def _google_map_mutation_for(user, p, list_id) -> dict[str, Any]:
    instruction = f"Sign in as {user.email} and save the Google Maps place {p.name!r} to your saved places. Then answer with the saved place name."
    return _mutation_spec("google_map", MUTATION_FAMILIES["google_map"], p.name, instruction, _actor(user.email),
                          {"kind": "place", "id": p.id, "name": p.name, "slug": p.slug, "list_id": list_id},
                          {"action": "save_place", "list_id": list_id},
                          "google_map.saved_place_absent", "google_map.saved_place_exists",
                          {"identity": p.name, "saved": True}, 7)


def _huggingface_mutation_for(user, r) -> dict[str, Any]:
    instruction = f"Sign in as {user.email} and like the Hugging Face repository {r.slug}. Then answer with the liked repository slug."
    return _mutation_spec("huggingface", MUTATION_FAMILIES["huggingface"], r.slug, instruction, _actor(user.email),
                          {"kind": "repository", "id": r.id, "slug": r.slug, "repo_type": r.repo_type},
                          {"action": "like_repository"},
                          "huggingface.repo_like_absent", "huggingface.repo_like_exists",
                          {"identity": r.slug, "liked": True}, 7)


def _wolfram_mutation_for(user, t) -> dict[str, Any]:
    instruction = f"Sign in as {user.email} and add the Wolfram Alpha topic {t.name!r} to favorites. Then answer with the favorite topic name."
    return _mutation_spec("wolfram_alpha", MUTATION_FAMILIES["wolfram_alpha"], t.name, instruction, _actor(user.email),
                          {"kind": "topic", "id": t.id, "name": t.name, "slug": t.slug},
                          {"action": "favorite_topic"},
                          "wolfram_alpha.favorite_topic_absent", "wolfram_alpha.favorite_topic_exists",
                          {"identity": t.name, "favorited": True}, 6)


def _allrecipes_mutation_batch(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("allrecipes", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        rows = app.Recipe.query.order_by(app.Recipe.review_count.desc(), app.Recipe.id.asc()).all()
        targets = _absent_page(rows, app.RecipeBoxItem, user.id, "recipe_id", offset, limit)
        return _raise_if_empty("allrecipes", MUTATION_FAMILIES["allrecipes"], [_allrecipes_mutation_for(user, r) for r in targets])


def _amazon_mutation_batch(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("amazon", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        rows = app.Product.query.order_by(app.Product.rating.desc(), app.Product.review_count.desc(), app.Product.id.asc()).all()
        targets = _absent_page(rows, app.CartItem, user.id, "product_id", offset, limit)
        return _raise_if_empty("amazon", MUTATION_FAMILIES["amazon"], [_amazon_mutation_for(user, p) for p in targets])


def _amazon_multi_cart_for(products, persona: dict[str, Any], quantity_profile: str) -> dict[str, Any]:
    actor = _actor_from_persona(persona)
    items = []
    lines = []
    expected_items = []
    for idx, product in enumerate(products):
        quantity = _quantity_for(idx, quantity_profile)
        unit_price = round(float(product.price), 2)
        line_total = round(unit_price * quantity, 2)
        item = {
            "kind": "product",
            "id": product.id,
            "name": product.name,
            "slug": product.slug,
            "quantity": quantity,
            "unit_price": unit_price,
            "line_total": line_total,
        }
        items.append(item)
        expected_items.append({"identity": product.name, "product_id": product.id, "quantity": quantity, "unit_price": unit_price, "line_total": line_total})
        lines.append(f"{idx + 1}. {product.name}, quantity {quantity}")
    subtotal = round(sum(item["line_total"] for item in items), 2)
    instruction = (
        f"Sign in as {persona['display_name']} using {persona['email']}. "
        "Add these products to the Amazon cart:\n"
        + "\n".join(lines)
        + "\nThen open the cart and answer with each item name, quantity, unit price, line total, and the cart subtotal."
    )
    label = "__".join(product.slug for product in products)
    return _multi_mutation_spec(
        "amazon",
        MULTI_MUTATION_FAMILIES["amazon"],
        label,
        instruction,
        actor,
        items,
        {
            "action": "cart_add_multiple_products",
            "item_count": len(items),
            "quantity_profile": quantity_profile,
            "before_policy": "absent",
        },
        "amazon.cart_items_absent",
        "amazon.cart_items_quantities",
        {"items": expected_items, "cart_count_delta": sum(item["quantity"] for item in items), "subtotal": subtotal},
        8,
    )


def _label_for_entity(entity: dict[str, Any]) -> str:
    return str(entity.get("name") or entity.get("title") or entity.get("full_name") or entity.get("headword")
               or entity.get("arxiv_id") or entity.get("flight_number") or entity.get("slug") or entity.get("id"))


def _generic_multi_for(site: str, family: str, action: str, entities: list[dict[str, Any]],
                       persona: dict[str, Any], before_predicate: str, after_predicate: str,
                       instruction_noun: str, answer_noun: str, extra_operation: dict[str, Any] | None = None) -> dict[str, Any]:
    actor = _actor_from_persona(persona)
    labels = [_label_for_entity(entity) for entity in entities]
    lines = [f"{idx + 1}. {label}" for idx, label in enumerate(labels)]
    instruction = (
        f"Sign in as {persona['display_name']} using {persona['email']}. "
        f"{instruction_noun}:\n" + "\n".join(lines) + f"\nThen answer with the {answer_noun}."
    )
    operation = {
        "action": action,
        "item_count": len(entities),
        "before_policy": "absent",
        **(extra_operation or {}),
    }
    expected_items = []
    for label, entity in zip(labels, entities):
        expected_item = {"identity": label, "id": entity.get("id")}
        for key in ("quantity", "unit_price", "line_total", "check_in", "check_out", "adults", "rooms", "room_type", "item_total"):
            if key in entity:
                expected_item[key] = entity[key]
        expected_items.append(expected_item)
    subtotal = round(sum(float(item.get("line_total", item.get("item_total", 0)) or 0) for item in expected_items), 2)
    expected: dict[str, Any] = {"items": expected_items}
    if subtotal:
        expected["subtotal"] = subtotal
    return _multi_mutation_spec(
        site,
        family,
        "__".join(str(entity.get("slug") or entity.get("id")) for entity in entities),
        instruction,
        actor,
        entities,
        operation,
        before_predicate,
        after_predicate,
        expected,
        8,
    )


def _multi_batch_from_rows(site: str, rows: list[Any], row_to_entity, mutation_cls, fk_name: str,
                           family: str, action: str, before_predicate: str, after_predicate: str,
                           instruction_noun: str, answer_noun: str, limit: int, offset: int,
                           item_count: int, persona_index: int | None = None, extra_filter=None,
                           extra_operation: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    personas = personas_for_site(site)
    candidates = []
    skipped = 0
    for combo in _combination_window(rows, item_count, 0, len(rows) ** min(item_count, 3)):
        persona = personas[(offset + len(candidates)) % len(personas)] if persona_index is None else personas[persona_index % len(personas)]
        user_id = int(persona["user_id"])
        has_existing = False
        for obj in combo:
            q = mutation_cls.query.filter_by(user_id=user_id)
            if extra_filter is not None:
                q = extra_filter(q, obj)
            else:
                q = q.filter(getattr(mutation_cls, fk_name) == obj.id)
            if q.first() is not None:
                has_existing = True
                break
        if has_existing:
            continue
        if skipped < offset:
            skipped += 1
            continue
        entities = [row_to_entity(obj) for obj in combo]
        candidates.append(_generic_multi_for(
            site, family, action, entities, persona, before_predicate, after_predicate,
            instruction_noun, answer_noun, extra_operation=extra_operation,
        ))
        if len(candidates) >= limit:
            break
    return _raise_if_empty(site, family, candidates)


def _amazon_multi_cart_batch(limit: int, offset: int, item_count: int, quantity_profile: str,
                             persona_index: int | None = None) -> list[dict[str, Any]]:
    app = load_site_app("amazon", fresh_instance=True).module
    with app.app.app_context():
        personas = personas_for_site("amazon")
        products = (app.Product.query.filter_by(is_prime=True, free_shipping=True)
                    .order_by(app.Product.rating.desc(), app.Product.review_count.desc(), app.Product.id.asc()).all())
        candidates = []
        skipped = 0
        for combo in _combination_window(products, item_count, 0, len(products) ** item_count):
            persona = personas[(offset + len(candidates)) % len(personas)] if persona_index is None else personas[persona_index % len(personas)]
            user_id = int(persona["user_id"])
            existing = {
                row.product_id for row in app.CartItem.query.filter_by(user_id=user_id).all()
            }
            if any(product.id in existing for product in combo):
                continue
            if skipped < offset:
                skipped += 1
                continue
            candidates.append(_amazon_multi_cart_for(combo, persona, quantity_profile))
            if len(candidates) >= limit:
                break
        return _raise_if_empty("amazon", MULTI_MUTATION_FAMILIES["amazon"], candidates)


def _allrecipes_multi_batch(limit: int, offset: int, item_count: int, quantity_profile: str,
                            persona_index: int | None = None) -> list[dict[str, Any]]:
    app = load_site_app("allrecipes", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Recipe.query.order_by(app.Recipe.review_count.desc(), app.Recipe.id.asc()).all()
        return _multi_batch_from_rows("allrecipes", rows, lambda r: {"kind": "recipe", "id": r.id, "title": r.title, "slug": r.slug},
                                      app.RecipeBoxItem, "recipe_id", MULTI_MUTATION_FAMILIES["allrecipes"],
                                      "save_multiple_to_recipe_box", "allrecipes.recipe_box_items_absent",
                                      "allrecipes.recipe_box_items_exist", "Save these recipes to your Recipe Box",
                                      "saved recipe titles", limit, offset, item_count, persona_index)


def _apple_multi_batch(limit: int, offset: int, item_count: int, quantity_profile: str,
                       persona_index: int | None = None) -> list[dict[str, Any]]:
    app = load_site_app("apple", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Product.query.order_by(
            (app.Product.category == "accessories").desc(),
            app.Product.price.asc(),
            app.Product.id.asc(),
        ).all()
        return _multi_batch_from_rows("apple", rows, lambda p: {"kind": "product", "id": p.id, "name": p.name, "slug": p.slug, "quantity": 1, "unit_price": round(float(p.price), 2), "line_total": round(float(p.price), 2)},
                                      app.CartItem, "product_id", MULTI_MUTATION_FAMILIES["apple"],
                                      "bag_add_multiple_products", "apple.cart_items_absent",
                                      "apple.cart_items_quantities", "Add these products to your Apple bag",
                                      "bag item names, quantities, line totals, subtotal, estimated tax, and total", limit, offset, item_count, persona_index)


def _arxiv_multi_batch(limit: int, offset: int, item_count: int, quantity_profile: str,
                       persona_index: int | None = None) -> list[dict[str, Any]]:
    app = load_site_app("arxiv", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Paper.query.order_by(app.Paper.arxiv_id.desc(), app.Paper.id.asc()).all()
        return _multi_batch_from_rows("arxiv", rows, lambda p: {"kind": "paper", "id": p.id, "arxiv_id": p.arxiv_id, "title": p.title},
                                      app.LibraryItem, "paper_id", MULTI_MUTATION_FAMILIES["arxiv"],
                                      "library_add_multiple_papers", "arxiv.library_items_absent",
                                      "arxiv.library_items_exist", "Add these arXiv papers to your library",
                                      "paper IDs", limit, offset, item_count, persona_index)


def _booking_multi_batch(limit: int, offset: int, item_count: int, quantity_profile: str,
                         persona_index: int | None = None) -> list[dict[str, Any]]:
    app = load_site_app("booking", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Property.query.order_by(app.Property.rating.desc(), app.Property.review_count.desc(), app.Property.id.asc()).all()
        personas = personas_for_site("booking")
        candidates = []
        skipped = 0
        for combo in _combination_window(rows, item_count, 0, len(rows) ** min(item_count, 3)):
            persona = personas[(offset + len(candidates)) % len(personas)] if persona_index is None else personas[persona_index % len(personas)]
            user_id = int(persona["user_id"])
            existing = {row.property_id for row in app.CartItem.query.filter_by(user_id=user_id).all()}
            if any(prop.id in existing for prop in combo):
                continue
            if skipped < offset:
                skipped += 1
                continue
            entities = [
                {
                    "kind": "property",
                    "id": p.id,
                    "name": p.name,
                    "slug": p.slug,
                    "check_in": "2026-06-12",
                    "check_out": "2026-06-15",
                    "adults": 2,
                    "rooms": 1,
                    "room_type": "Standard Double Room",
                    "item_total": round(float(p.discounted_price) * 3 * 1, 2),
                }
                for p in combo
            ]
            labels = [entity["name"] for entity in entities]
            instruction = (
                f"Sign in as {persona['display_name']} using {persona['email']}. "
                "Add these Booking stays to your booking bag for June 12, 2026 to June 15, 2026, 2 adults, and 1 room:\n"
                + "\n".join(f"{idx + 1}. {name}" for idx, name in enumerate(labels))
                + "\nThen open the booking bag and answer with the property names, dates, rooms/adults, item totals, subtotal, taxes and fees, and total."
            )
            expected_items = [
                {
                    "identity": entity["name"],
                    "id": entity["id"],
                    "property_id": entity["id"],
                    "check_in": entity["check_in"],
                    "check_out": entity["check_out"],
                    "adults": entity["adults"],
                    "rooms": entity["rooms"],
                    "room_type": entity["room_type"],
                    "item_total": entity["item_total"],
                }
                for entity in entities
            ]
            subtotal = round(sum(item["item_total"] for item in expected_items), 2)
            taxes = round(subtotal * 0.12, 2)
            total = round(subtotal + taxes, 2)
            candidates.append(_multi_mutation_spec(
                "booking",
                MULTI_MUTATION_FAMILIES["booking"],
                "__".join(entity["slug"] for entity in entities),
                instruction,
                _actor_from_persona(persona),
                entities,
                {"action": "bag_add_multiple_stays", "item_count": len(entities), "before_policy": "absent"},
                "booking.cart_items_absent",
                "booking.cart_items_exist",
                {"items": expected_items, "subtotal": subtotal, "taxes": taxes, "total": total},
                8,
            ))
            if len(candidates) >= limit:
                break
        return _raise_if_empty("booking", MULTI_MUTATION_FAMILIES["booking"], candidates)


def _cambridge_multi_batch(limit: int, offset: int, item_count: int, quantity_profile: str,
                           persona_index: int | None = None) -> list[dict[str, Any]]:
    app = load_site_app("cambridge_dictionary", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Word.query.order_by(app.Word.headword.asc(), app.Word.id.asc()).all()
        return _multi_batch_from_rows("cambridge_dictionary", rows, lambda w: {"kind": "word", "id": w.id, "headword": w.headword, "slug": w.slug},
                                      app.SavedWord, "word_id", MULTI_MUTATION_FAMILIES["cambridge_dictionary"],
                                      "saved_words_add_multiple", "cambridge_dictionary.saved_words_absent",
                                      "cambridge_dictionary.saved_words_exist", "Save these Cambridge Dictionary words",
                                      "saved headwords", limit, offset, item_count, persona_index)


def _coursera_multi_batch(limit: int, offset: int, item_count: int, quantity_profile: str,
                          persona_index: int | None = None) -> list[dict[str, Any]]:
    app = load_site_app("coursera", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Course.query.order_by(app.Course.rating.desc(), app.Course.review_count.desc(), app.Course.id.asc()).all()
        return _multi_batch_from_rows("coursera", rows, lambda c: {"kind": "course", "id": c.id, "title": c.title, "slug": c.slug},
                                      app.SavedCourse, "course_id", MULTI_MUTATION_FAMILIES["coursera"],
                                      "saved_courses_add_multiple", "coursera.saved_courses_absent",
                                      "coursera.saved_courses_exist", "Save these Coursera courses to your wishlist",
                                      "saved course titles", limit, offset, item_count, persona_index)


def _espn_multi_batch(limit: int, offset: int, item_count: int, quantity_profile: str,
                      persona_index: int | None = None) -> list[dict[str, Any]]:
    app = load_site_app("espn", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Team.query.order_by(app.Team.sport_slug.asc(), app.Team.standing_rank.asc(), app.Team.id.asc()).all()
        def extra(q, obj): return q.filter_by(item_type="team", item_id=obj.id)
        return _multi_batch_from_rows("espn", rows, lambda t: {"kind": "team", "id": t.id, "full_name": t.full_name, "slug": t.slug},
                                      app.UserFavorite, "item_id", MULTI_MUTATION_FAMILIES["espn"],
                                      "favorite_teams_add_multiple", "espn.favorite_teams_absent",
                                      "espn.favorite_teams_exist", "Add these teams to your ESPN favorites",
                                      "favorite team names", limit, offset, item_count, persona_index,
                                      extra_filter=extra, extra_operation={"item_type": "team"})


def _github_multi_batch(limit: int, offset: int, item_count: int, quantity_profile: str,
                        persona_index: int | None = None) -> list[dict[str, Any]]:
    app = load_site_app("github", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Repository.query.order_by(app.Repository.stars_count.desc(), app.Repository.id.asc()).all()
        return _multi_batch_from_rows("github", rows, lambda r: {"kind": "repository", "id": r.id, "full_name": r.full_name},
                                      app.Star, "repo_id", MULTI_MUTATION_FAMILIES["github"],
                                      "repo_star_add_multiple", "github.repo_stars_absent",
                                      "github.repo_stars_exist", "Star these GitHub repositories",
                                      "starred repository full names", limit, offset, item_count, persona_index)


def _google_flights_multi_batch(limit: int, offset: int, item_count: int, quantity_profile: str,
                                persona_index: int | None = None) -> list[dict[str, Any]]:
    app = load_site_app("google_flights", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Flight.query.order_by(app.Flight.departure_date.asc(), app.Flight.price.asc(), app.Flight.id.asc()).limit(5000).all()
        return _multi_batch_from_rows("google_flights", rows, lambda f: {"kind": "flight", "id": f.id, "flight_number": f.flight_number},
                                      app.TrackedFlight, "flight_id", MULTI_MUTATION_FAMILIES["google_flights"],
                                      "tracked_flights_add_multiple", "google_flights.tracked_flights_absent",
                                      "google_flights.tracked_flights_exist", "Track these Google Flights",
                                      "tracked flight numbers", limit, offset, item_count, persona_index)


def _google_map_multi_batch(limit: int, offset: int, item_count: int, quantity_profile: str,
                            persona_index: int | None = None) -> list[dict[str, Any]]:
    app = load_site_app("google_map", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Place.query.order_by(app.Place.review_count.desc(), app.Place.rating.desc(), app.Place.id.asc()).all()
        default_lists = {}
        def extra(q, obj): return q.filter_by(place_id=obj.id)
        specs = _multi_batch_from_rows("google_map", rows, lambda p: {"kind": "place", "id": p.id, "name": p.name, "slug": p.slug},
                                       app.SavedPlace, "place_id", MULTI_MUTATION_FAMILIES["google_map"],
                                       "saved_places_add_multiple", "google_map.saved_places_absent",
                                       "google_map.saved_places_exist", "Save these Google Maps places",
                                       "saved place names", limit, offset, item_count, persona_index,
                                       extra_filter=extra)
        return specs


def _huggingface_multi_batch(limit: int, offset: int, item_count: int, quantity_profile: str,
                             persona_index: int | None = None) -> list[dict[str, Any]]:
    app = load_site_app("huggingface", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Repository.query.order_by(app.Repository.downloads.desc(), app.Repository.likes_count.desc(), app.Repository.id.asc()).all()
        return _multi_batch_from_rows("huggingface", rows, lambda r: {"kind": "repository", "id": r.id, "slug": r.slug, "repo_type": r.repo_type},
                                      app.Like, "repo_id", MULTI_MUTATION_FAMILIES["huggingface"],
                                      "repo_like_add_multiple", "huggingface.repo_likes_absent",
                                      "huggingface.repo_likes_exist", "Like these Hugging Face repositories",
                                      "liked repository slugs", limit, offset, item_count, persona_index)


def _wolfram_multi_batch(limit: int, offset: int, item_count: int, quantity_profile: str,
                         persona_index: int | None = None) -> list[dict[str, Any]]:
    app = load_site_app("wolfram_alpha", fresh_instance=True).module
    with app.app.app_context():
        rows = app.Topic.query.order_by(app.Topic.is_featured.desc(), app.Topic.name.asc(), app.Topic.id.asc()).all()
        return _multi_batch_from_rows("wolfram_alpha", rows, lambda t: {"kind": "topic", "id": t.id, "name": t.name, "slug": t.slug},
                                      app.Favorite, "topic_id", MULTI_MUTATION_FAMILIES["wolfram_alpha"],
                                      "favorite_topics_add_multiple", "wolfram_alpha.favorite_topics_absent",
                                      "wolfram_alpha.favorite_topics_exist", "Add these Wolfram Alpha topics to favorites",
                                      "favorite topic names", limit, offset, item_count, persona_index)


def _apple_mutation_batch(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("apple", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        rows = app.Product.query.order_by(app.Product.is_new.desc(), app.Product.price.desc(), app.Product.id.asc()).all()
        targets = _absent_page(rows, app.CartItem, user.id, "product_id", offset, limit)
        return _raise_if_empty("apple", MUTATION_FAMILIES["apple"], [_apple_mutation_for(user, p) for p in targets])


def _arxiv_mutation_batch(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("arxiv", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        rows = app.Paper.query.order_by(app.Paper.arxiv_id.desc(), app.Paper.id.asc()).all()
        targets = _absent_page(rows, app.LibraryItem, user.id, "paper_id", offset, limit)
        return _raise_if_empty("arxiv", MUTATION_FAMILIES["arxiv"], [_arxiv_mutation_for(user, p) for p in targets])


def _booking_mutation_batch(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("booking", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app, "sophie.m@test.com")
        rows = app.Property.query.order_by(app.Property.rating.desc(), app.Property.review_count.desc(), app.Property.id.asc()).all()
        targets = _absent_page(rows, app.SavedProperty, user.id, "property_id", offset, limit)
        return _raise_if_empty("booking", MUTATION_FAMILIES["booking"], [_booking_mutation_for(user, p) for p in targets])


def _cambridge_mutation_batch(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("cambridge_dictionary", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        rows = app.Word.query.order_by(app.Word.headword.asc(), app.Word.id.asc()).all()
        targets = _absent_page(rows, app.SavedWord, user.id, "word_id", offset, limit)
        return _raise_if_empty("cambridge_dictionary", MUTATION_FAMILIES["cambridge_dictionary"], [_cambridge_mutation_for(user, w) for w in targets])


def _coursera_mutation_batch(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("coursera", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        rows = app.Course.query.order_by(app.Course.rating.desc(), app.Course.review_count.desc(), app.Course.id.asc()).all()
        targets = _absent_page(rows, app.SavedCourse, user.id, "course_id", offset, limit)
        return _raise_if_empty("coursera", MUTATION_FAMILIES["coursera"], [_coursera_mutation_for(user, c) for c in targets])


def _espn_mutation_batch(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("espn", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        def extra(q, obj): return q.filter_by(item_type="team", item_id=obj.id)
        rows = app.Team.query.order_by(app.Team.sport_slug.asc(), app.Team.standing_rank.asc(), app.Team.id.asc()).all()
        targets = _absent_page(rows, app.UserFavorite, user.id, "item_id", offset, limit, extra_filter=extra)
        return _raise_if_empty("espn", MUTATION_FAMILIES["espn"], [_espn_mutation_for(user, t) for t in targets])


def _github_mutation_batch(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("github", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app, "alice.j@test.com")
        rows = app.Repository.query.order_by(app.Repository.stars_count.desc(), app.Repository.id.asc()).all()
        targets = _absent_page(rows, app.Star, user.id, "repo_id", offset, limit)
        return _raise_if_empty("github", MUTATION_FAMILIES["github"], [_github_mutation_for(user, r) for r in targets])


def _google_flights_mutation_batch(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("google_flights", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        rows = app.Flight.query.order_by(app.Flight.departure_date.asc(), app.Flight.price.asc(), app.Flight.id.asc()).limit(5000).all()
        targets = _absent_page(rows, app.TrackedFlight, user.id, "flight_id", offset, limit)
        return _raise_if_empty("google_flights", MUTATION_FAMILIES["google_flights"], [_google_flights_mutation_for(user, f) for f in targets])


def _google_map_mutation_batch(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("google_map", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        default_list = app.SavedList.query.filter_by(user_id=user.id, is_default=True).first() or app.SavedList.query.filter_by(user_id=user.id).first()
        def extra(q, obj): return q.filter_by(place_id=obj.id)
        rows = app.Place.query.order_by(app.Place.review_count.desc(), app.Place.rating.desc(), app.Place.id.asc()).all()
        targets = _absent_page(rows, app.SavedPlace, user.id, "place_id", offset, limit, extra_filter=extra)
        list_id = default_list.id if default_list else None
        return _raise_if_empty("google_map", MUTATION_FAMILIES["google_map"], [_google_map_mutation_for(user, p, list_id) for p in targets])


def _huggingface_mutation_batch(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("huggingface", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        rows = app.Repository.query.order_by(app.Repository.downloads.desc(), app.Repository.likes_count.desc(), app.Repository.id.asc()).all()
        targets = _absent_page(rows, app.Like, user.id, "repo_id", offset, limit)
        return _raise_if_empty("huggingface", MUTATION_FAMILIES["huggingface"], [_huggingface_mutation_for(user, r) for r in targets])


def _wolfram_mutation_batch(limit: int, offset: int) -> list[dict[str, Any]]:
    app = load_site_app("wolfram_alpha", fresh_instance=True).module
    with app.app.app_context():
        user = _first_user(app)
        rows = app.Topic.query.order_by(app.Topic.is_featured.desc(), app.Topic.name.asc(), app.Topic.id.asc()).all()
        targets = _absent_page(rows, app.Favorite, user.id, "topic_id", offset, limit)
        return _raise_if_empty("wolfram_alpha", MUTATION_FAMILIES["wolfram_alpha"], [_wolfram_mutation_for(user, t) for t in targets])


DETAIL_GENERATORS = {
    "allrecipes": _allrecipes_specs,
    "amazon": _amazon_specs,
    "apple": _apple_specs,
    "arxiv": _arxiv_specs,
    "booking": _booking_specs,
    "cambridge_dictionary": _cambridge_specs,
    "coursera": _coursera_specs,
    "espn": _espn_specs,
    "github": _github_specs,
    "google_flights": _google_flights_specs,
    "google_map": _google_map_specs,
    "huggingface": _huggingface_specs,
    "wolfram_alpha": _wolfram_specs,
}

IDENTIFY_GENERATORS = {
    "allrecipes": _allrecipes_identify_specs,
    "amazon": _amazon_identify_specs,
    "apple": _apple_identify_specs,
    "arxiv": _arxiv_identify_specs,
    "booking": _booking_identify_specs,
    "cambridge_dictionary": _cambridge_identify_specs,
    "coursera": _coursera_identify_specs,
    "espn": _espn_identify_specs,
    "github": _github_identify_specs,
    "google_flights": _google_flights_identify_specs,
    "google_map": _google_map_identify_specs,
    "huggingface": _huggingface_identify_specs,
    "wolfram_alpha": _wolfram_identify_specs,
}

MUTATION_GENERATORS = {
    "allrecipes": _allrecipes_mutation_specs,
    "amazon": _amazon_mutation_specs,
    "apple": _apple_mutation_specs,
    "arxiv": _arxiv_mutation_specs,
    "booking": _booking_mutation_specs,
    "cambridge_dictionary": _cambridge_mutation_specs,
    "coursera": _coursera_mutation_specs,
    "espn": _espn_mutation_specs,
    "github": _github_mutation_specs,
    "google_flights": _google_flights_mutation_specs,
    "google_map": _google_map_mutation_specs,
    "huggingface": _huggingface_mutation_specs,
    "wolfram_alpha": _wolfram_mutation_specs,
}

BATCH_DETAIL_GENERATORS = {
    "allrecipes": _allrecipes_detail_specs,
    "amazon": _amazon_detail_specs,
    "apple": _apple_detail_specs,
    "arxiv": _arxiv_detail_specs,
    "booking": _booking_detail_specs,
    "cambridge_dictionary": _cambridge_detail_specs,
    "coursera": _coursera_detail_specs,
    "espn": _espn_detail_specs,
    "github": _github_detail_specs,
    "google_flights": _google_flights_detail_specs,
    "google_map": _google_map_detail_specs,
    "huggingface": _huggingface_detail_specs,
    "wolfram_alpha": _wolfram_detail_specs,
}

BATCH_MUTATION_GENERATORS = {
    "allrecipes": _allrecipes_mutation_batch,
    "amazon": _amazon_mutation_batch,
    "apple": _apple_mutation_batch,
    "arxiv": _arxiv_mutation_batch,
    "booking": _booking_mutation_batch,
    "cambridge_dictionary": _cambridge_mutation_batch,
    "coursera": _coursera_mutation_batch,
    "espn": _espn_mutation_batch,
    "github": _github_mutation_batch,
    "google_flights": _google_flights_mutation_batch,
    "google_map": _google_map_mutation_batch,
    "huggingface": _huggingface_mutation_batch,
    "wolfram_alpha": _wolfram_mutation_batch,
}

MULTI_MUTATION_GENERATORS = {
    "allrecipes": _allrecipes_multi_batch,
    "amazon": _amazon_multi_cart_batch,
    "apple": _apple_multi_batch,
    "arxiv": _arxiv_multi_batch,
    "booking": _booking_multi_batch,
    "cambridge_dictionary": _cambridge_multi_batch,
    "coursera": _coursera_multi_batch,
    "espn": _espn_multi_batch,
    "github": _github_multi_batch,
    "google_flights": _google_flights_multi_batch,
    "google_map": _google_map_multi_batch,
    "huggingface": _huggingface_multi_batch,
    "wolfram_alpha": _wolfram_multi_batch,
}


def families_for_site(site: str) -> list[str]:
    if site not in SUPPORTED_SITES:
        raise ValueError(f"unsupported site: {site}")
    families = [DEFAULT_FAMILIES[site], IDENTIFY_FAMILIES[site], MUTATION_FAMILIES[site]]
    if site in MULTI_MUTATION_FAMILIES:
        families.append(MULTI_MUTATION_FAMILIES[site])
    return families


def _validate_window(limit: int, offset: int) -> None:
    if limit < 1:
        raise ValueError("--limit must be >= 1")
    if offset < 0:
        raise ValueError("--offset must be >= 0")


def generate(site: str, family: str | None, limit: int = 1, offset: int = 0,
             item_count: int = 2, quantity_profile: str = "mixed",
             persona_index: int | None = None) -> list[dict[str, Any]]:
    if site not in SUPPORTED_SITES:
        raise ValueError(f"unsupported site: {site}")
    _validate_window(limit, offset)
    selected = family or DEFAULT_FAMILIES[site]
    if selected == DEFAULT_FAMILIES[site]:
        return BATCH_DETAIL_GENERATORS[site](limit, offset)
    if selected == IDENTIFY_FAMILIES[site]:
        details = BATCH_DETAIL_GENERATORS[site](limit, offset)
        specs = [IDENTIFY_FROM_DETAIL[site](detail) for detail in details]
        return _raise_if_empty(site, selected, specs)
    if selected == MUTATION_FAMILIES[site]:
        return BATCH_MUTATION_GENERATORS[site](limit, offset)
    if site in MULTI_MUTATION_FAMILIES and selected == MULTI_MUTATION_FAMILIES[site]:
        return MULTI_MUTATION_GENERATORS[site](limit, offset, item_count, quantity_profile, persona_index)
    raise ValueError(f"unsupported {site} family: {family}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-sites", action="store_true", help="print sites supported by this reverse generator")
    parser.add_argument("--list-families", action="store_true", help="print supported families for --site")
    parser.add_argument("--site", choices=SUPPORTED_SITES)
    parser.add_argument("--family", default=None)
    parser.add_argument("--limit", type=int, default=1, help="maximum number of specs to emit")
    parser.add_argument("--offset", type=int, default=0, help="stable candidate offset before applying --limit")
    parser.add_argument("--item-count", type=int, default=2, help="number of entities in multi-entity mutation tasks")
    parser.add_argument("--quantity-profile", choices=["ones", "mixed", "increasing"], default="mixed")
    parser.add_argument("--persona-index", type=int, default=None, help="fixed persona index for authenticated tasks")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.list_sites:
        print("\n".join(SUPPORTED_SITES))
        return 0
    if args.list_families:
        if not args.site:
            parser.error("--site is required with --list-families")
        print("\n".join(families_for_site(args.site)))
        return 0
    if not args.site or not args.output:
        parser.error("--site and --output are required unless --list-sites/--list-families is used")

    specs = generate(
        args.site,
        args.family,
        limit=args.limit,
        offset=args.offset,
        item_count=args.item_count,
        quantity_profile=args.quantity_profile,
        persona_index=args.persona_index,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json_dump_line(spec) for spec in specs), encoding="utf-8")
    print(f"wrote {len(specs)} structured task(s) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
