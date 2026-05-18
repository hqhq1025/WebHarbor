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


def run_script(*args):
    return subprocess.run([str(PYTHON), *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def read_first(path):
    return json.loads(Path(path).read_text(encoding="utf-8").splitlines()[0])


def test_list_families_exposes_mutation_for_every_site():
    for site in SITES:
        result = run_script("scripts/generate_structured_tasks.py", "--site", site, "--list-families")
        assert result.returncode == 0, result.stderr
        assert MUTATION_FAMILIES[site] in result.stdout.split()


def test_mutation_family_includes_actor_login_and_state_transition(tmp_path):
    for site in SITES:
        out = tmp_path / f"{site}.mutation.jsonl"
        result = run_script(
            "scripts/generate_structured_tasks.py",
            "--site", site,
            "--family", MUTATION_FAMILIES[site],
            "--output", str(out),
        )
        assert result.returncode == 0, f"{site} mutation generator failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        spec = read_first(out)
        assert spec["task_family"] == MUTATION_FAMILIES[site]
        assert spec["actor"]["email"]
        assert spec["actor"]["password"] == "TestPass123!"
        assert spec["login"]["required"] is True
        assert spec["login"]["strategy"] == "ui_credentials"
        assert spec["state_transition"]["before"]["db_predicate"].startswith(f"{site}.")
        assert spec["state_transition"]["after"]["db_predicate"].startswith(f"{site}.")
        assert spec["validation"]["answer_kind"] == "state_transition"

        before = run_script("scripts/validate_structured_task.py", "--spec", str(out), "--phase", "before")
        assert before.returncode == 0, f"{site} before validation failed\nSTDOUT:\n{before.stdout}\nSTDERR:\n{before.stderr}\nSPEC:\n{json.dumps(spec, ensure_ascii=False, indent=2)}"


def test_mutation_after_phase_fails_before_agent_action(tmp_path):
    site = "amazon"
    out = tmp_path / "amazon.mutation.jsonl"
    result = run_script(
        "scripts/generate_structured_tasks.py",
        "--site", site,
        "--family", MUTATION_FAMILIES[site],
        "--output", str(out),
    )
    assert result.returncode == 0, result.stderr
    after = run_script("scripts/validate_structured_task.py", "--spec", str(out), "--phase", "after")
    assert after.returncode != 0
    assert "after" in after.stderr.lower() or "expected" in after.stderr.lower()
