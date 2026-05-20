import json
import pytest
import subprocess
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)
pytestmark = pytest.mark.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
for site_packages in (ROOT / ".venv" / "lib").glob("python*/site-packages"):
    sys.path.insert(0, str(site_packages))
sys.path.insert(0, str(ROOT / "scripts"))
import generate_structured_tasks as generator  # noqa: E402
from structured_task_runtime import UPSTREAM_LOGIN_URLS, load_site_app  # noqa: E402
import validate_structured_task as validator  # noqa: E402

PYTHON = ROOT / ".venv" / "bin" / "python"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)

SITES = [
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
DETAIL_FAMILIES = {
    "allrecipes": "recipe_detail_lookup",
    "amazon": "product_search_with_filters",
    "apple": "product_detail_lookup",
    "arxiv": "paper_metadata_lookup",
    "booking": "hotel_search_with_amenity_filters",
    "cambridge_dictionary": "dictionary_entry_lookup",
    "coursera": "course_search_detail_lookup",
    "espn": "team_standings_lookup",
    "github": "repository_search_detail_lookup",
    "google_flights": "one_way_cheapest_flight",
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


def run_script(*args):
    return subprocess.run([str(PYTHON), *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_specs(specs, phase="spec"):
    validator._APP_CACHE.clear()
    for spec in specs:
        validator.validate(spec, phase=phase)


def test_limit_and_offset_emit_stable_distinct_amazon_detail_tasks(tmp_path):
    first = tmp_path / "amazon.first.jsonl"
    shifted = tmp_path / "amazon.shifted.jsonl"

    result = run_script(
        "scripts/generate_structured_tasks.py",
        "--site", "amazon",
        "--family", DETAIL_FAMILIES["amazon"],
        "--limit", "3",
        "--output", str(first),
    )
    assert result.returncode == 0, result.stderr
    first_specs = read_jsonl(first)
    assert len(first_specs) == 3
    assert len({spec["id"] for spec in first_specs}) == 3

    result = run_script(
        "scripts/generate_structured_tasks.py",
        "--site", "amazon",
        "--family", DETAIL_FAMILIES["amazon"],
        "--offset", "1",
        "--limit", "2",
        "--output", str(shifted),
    )
    assert result.returncode == 0, result.stderr
    shifted_specs = read_jsonl(shifted)
    assert [spec["id"] for spec in shifted_specs] == [spec["id"] for spec in first_specs[1:3]]


def test_validator_accepts_multi_line_jsonl(tmp_path):
    out = tmp_path / "amazon.batch.jsonl"
    gen = run_script(
        "scripts/generate_structured_tasks.py",
        "--site", "amazon",
        "--family", DETAIL_FAMILIES["amazon"],
        "--limit", "3",
        "--output", str(out),
    )
    assert gen.returncode == 0, gen.stderr
    val = run_script("scripts/validate_structured_task.py", "--spec", str(out))
    assert val.returncode == 0, val.stderr
    assert "validated 3 task(s)" in val.stdout


def test_all_supported_families_batch_generate_and_validate(tmp_path):
    for site in SITES:
        for family in (DETAIL_FAMILIES[site], IDENTIFY_FAMILIES[site], MUTATION_FAMILIES[site]):
            specs = generator.generate(site, family, limit=3)
            assert specs, f"{site}/{family} generated no specs"
            assert len(specs) <= 3
            assert len({spec["id"] for spec in specs}) == len(specs)
            if family == MUTATION_FAMILIES[site]:
                for spec in specs:
                    assert spec["login"]["login_url"] == UPSTREAM_LOGIN_URLS[site]
                    assert spec["login"]["login_url"].startswith("https://")
                    assert "localhost" not in spec["login"]["login_url"]
            phase = "before" if family == MUTATION_FAMILIES[site] else "spec"
            validate_specs(specs, phase=phase)


def test_batched_identify_specs_are_unique_and_do_not_leak_identity(tmp_path):
    for site in SITES:
        specs = generator.generate(site, IDENTIFY_FAMILIES[site], limit=3)
        assert specs
        for spec in specs:
            assert spec["validation"]["require_unique_match"] is True
            assert spec["validation"]["answer_kind"] == "entity_identity"
            identity = spec["expected_answer"]["identity"]
            assert identity not in spec["instruction"]
            validate_specs([spec])


def test_batched_mutation_after_phase_fails_before_agent_action(tmp_path):
    out = tmp_path / "amazon.mutation.jsonl"
    result = run_script(
        "scripts/generate_structured_tasks.py",
        "--site", "amazon",
        "--family", MUTATION_FAMILIES["amazon"],
        "--limit", "3",
        "--output", str(out),
    )
    assert result.returncode == 0, result.stderr
    before = run_script("scripts/validate_structured_task.py", "--spec", str(out), "--phase", "before")
    assert before.returncode == 0, before.stderr
    after = run_script("scripts/validate_structured_task.py", "--spec", str(out), "--phase", "after")
    assert after.returncode != 0
    assert "after" in after.stderr.lower()


def test_auth_persona_registry_matches_seed_users():
    for site in SITES:
        app = load_site_app(site, fresh_instance=True).module
        with app.app.app_context():
            personas = generator.personas_for_site(site)
            assert len(personas) >= 3
            for persona in personas[:3]:
                user = app.User.query.filter_by(id=persona["user_id"]).first()
                assert user is not None, f"{site} missing persona user_id={persona['user_id']}"
                assert getattr(user, "email", None) == persona["email"]
                assert persona["password"]


def test_amazon_multi_cart_generation_and_validation(tmp_path):
    out = tmp_path / "amazon.multi.jsonl"
    result = run_script(
        "scripts/generate_structured_tasks.py",
        "--site", "amazon",
        "--family", "cart_add_multiple_products",
        "--item-count", "2",
        "--quantity-profile", "mixed",
        "--limit", "3",
        "--output", str(out),
    )
    assert result.returncode == 0, result.stderr
    specs = read_jsonl(out)
    assert len(specs) == 3
    assert len({spec["id"] for spec in specs}) == 3
    for spec in specs:
        assert spec["task_family"] == "cart_add_multiple_products"
        assert len(spec["target_entities"]) == 2
        assert spec["operation"]["item_count"] == 2
        assert spec["operation"]["quantity_profile"] == "mixed"
        assert spec["actor"]["user_id"] in {2, 3, 4}
        assert spec["expected_answer"]["items"]
        assert spec["expected_answer"]["subtotal"] > 0
        for item in spec["expected_answer"]["items"]:
            assert item["unit_price"] > 0
            assert item["line_total"] == round(item["unit_price"] * item["quantity"], 2)
        assert all(item["quantity"] >= 1 for item in spec["target_entities"])

    before = run_script("scripts/validate_structured_task.py", "--spec", str(out), "--phase", "before")
    assert before.returncode == 0, before.stderr

    after = run_script("scripts/validate_structured_task.py", "--spec", str(out), "--phase", "after")
    assert after.returncode != 0
    assert "item_id" in after.stderr

    bad = specs[0]
    bad["expected_answer"] = dict(bad["expected_answer"], subtotal=bad["expected_answer"]["subtotal"] + 10)
    bad_path = tmp_path / "bad_subtotal.jsonl"
    bad_path.write_text(json.dumps(bad, ensure_ascii=False) + "\n", encoding="utf-8")
    bad_val = run_script("scripts/validate_structured_task.py", "--spec", str(bad_path), "--phase", "before")
    assert bad_val.returncode != 0
    assert "subtotal" in bad_val.stderr


def test_all_multi_mutation_families_generate_and_validate_before(tmp_path):
    for site, family in MULTI_MUTATION_FAMILIES.items():
        out = tmp_path / f"{site}.multi.jsonl"
        result = run_script(
            "scripts/generate_structured_tasks.py",
            "--site", site,
            "--family", family,
            "--item-count", "2",
            "--limit", "2",
            "--output", str(out),
        )
        assert result.returncode == 0, f"{site}/{family}\nSTDOUT:{result.stdout}\nSTDERR:{result.stderr}"
        specs = read_jsonl(out)
        assert specs
        for spec in specs:
            assert spec["task_family"] == family
            assert len(spec["target_entities"]) == 2
            assert spec["actor"]["user_id"]
            assert spec["operation"]["item_count"] == 2
        before = run_script("scripts/validate_structured_task.py", "--spec", str(out), "--phase", "before")
        assert before.returncode == 0, f"{site}/{family} before failed\n{before.stderr}"


def _write_one(tmp_path, spec):
    path = tmp_path / f"{spec['id']}.json"
    path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    return path
