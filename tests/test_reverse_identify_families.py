import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


def run_script(*args):
    return subprocess.run([str(PYTHON), *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def read_first(path):
    return json.loads(Path(path).read_text(encoding="utf-8").splitlines()[0])


def test_list_families_exposes_detail_and_identify_for_every_site():
    for site in SITES:
        result = run_script("scripts/generate_structured_tasks.py", "--site", site, "--list-families")
        assert result.returncode == 0, result.stderr
        families = result.stdout.split()
        assert DETAIL_FAMILIES[site] in families
        assert IDENTIFY_FAMILIES[site] in families


def test_identify_family_does_not_leak_target_in_question_and_validates(tmp_path):
    for site in SITES:
        out = tmp_path / f"{site}.identify.jsonl"
        result = run_script(
            "scripts/generate_structured_tasks.py",
            "--site", site,
            "--family", IDENTIFY_FAMILIES[site],
            "--output", str(out),
        )
        assert result.returncode == 0, f"{site} identify generator failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        spec = read_first(out)
        assert spec["task_family"] == IDENTIFY_FAMILIES[site]
        assert spec["constraints"]["target_selection"] == "identify_by_constraints"
        assert spec["validation"]["require_unique_match"] is True
        assert spec["validation"].get("answer_kind") == "entity_identity"
        assert spec["expected_answer"]["identity"]
        leaked = [v for v in spec["target_entity"].values() if isinstance(v, str) and len(v) >= 4 and v in spec["instruction"]]
        # Slugs/ids can be opaque route identifiers; human-visible names should not be in the prompt.
        human_keys = {"name", "title", "full_name", "slug", "headword", "arxiv_id", "flight_number"}
        leaked_human = [spec["target_entity"][k] for k in human_keys & spec["target_entity"].keys()
                        if isinstance(spec["target_entity"][k], str) and spec["target_entity"][k] in spec["instruction"]]
        assert not leaked_human, f"{site} identify question leaks target: {leaked_human}\n{spec['instruction']}"

        val = run_script("scripts/validate_structured_task.py", "--spec", str(out))
        assert val.returncode == 0, f"{site} identify validator failed\nSTDOUT:\n{val.stdout}\nSTDERR:\n{val.stderr}\nSPEC:\n{json.dumps(spec, ensure_ascii=False, indent=2)}"


def test_identify_validator_rejects_wrong_identity(tmp_path):
    site = "amazon"
    out = tmp_path / "amazon.identify.jsonl"
    result = run_script(
        "scripts/generate_structured_tasks.py",
        "--site", site,
        "--family", IDENTIFY_FAMILIES[site],
        "--output", str(out),
    )
    assert result.returncode == 0, result.stderr
    spec = read_first(out)
    spec["expected_answer"]["identity"] = "Echo Dot (5th Gen) Smart Speaker with Alexa"
    bad = tmp_path / "amazon.bad.json"
    bad.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    val = run_script("scripts/validate_structured_task.py", "--spec", str(bad))
    assert val.returncode != 0
    assert "identity" in val.stderr.lower() or "unique" in val.stderr.lower()
