import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "bin" / "python"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)

EXPECTED_SITES = [
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


def run_script(*args):
    return subprocess.run(
        [str(PYTHON), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def read_first_jsonl(path):
    return json.loads(Path(path).read_text(encoding="utf-8").splitlines()[0])


def test_list_sites_reports_all_currently_supported_reverse_generators():
    result = run_script("scripts/generate_structured_tasks.py", "--list-sites")
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == EXPECTED_SITES


def test_each_supported_site_generates_and_validates_one_structured_task(tmp_path):
    for site in EXPECTED_SITES:
        out = tmp_path / f"{site}.jsonl"
        gen = run_script("scripts/generate_structured_tasks.py", "--site", site, "--output", str(out))
        assert gen.returncode == 0, f"{site} generator failed\nSTDOUT:\n{gen.stdout}\nSTDERR:\n{gen.stderr}"
        spec = read_first_jsonl(out)
        assert spec["site"] == site
        assert spec["target_entity"]["kind"]
        assert spec["constraints"]
        assert spec["expected_answer"]
        assert spec["validation"]["db_predicate"].startswith(f"{site}.")
        assert spec["validation"]["must_appear"]
        assert spec["stability"]["fixture_fixed"] is True

        val = run_script("scripts/validate_structured_task.py", "--spec", str(out))
        assert val.returncode == 0, f"{site} validator failed\nSTDOUT:\n{val.stdout}\nSTDERR:\n{val.stderr}\nSPEC:\n{json.dumps(spec, ensure_ascii=False, indent=2)}"
