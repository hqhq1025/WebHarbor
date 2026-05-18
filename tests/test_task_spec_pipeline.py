import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "bin" / "python"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)


def run_script(*args):
    return subprocess.run(
        [str(PYTHON), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def test_booking_reverse_generator_emits_structured_praktik_spec(tmp_path):
    out = tmp_path / "booking_specs.jsonl"
    result = run_script(
        "scripts/generate_structured_tasks.py",
        "--site", "booking",
        "--family", "hotel_search_with_amenity_filters",
        "--output", str(out),
    )
    assert result.returncode == 0, result.stderr
    specs = read_jsonl(out)
    spec = next(item for item in specs if item["target_entity"]["name"] == "Praktik Èssens")

    assert spec["web_name"] == "Booking"
    assert spec["target_entity"] == {
        "kind": "property",
        "name": "Praktik Èssens",
        "field": "brand",
        "brand": "Independent",
    }
    assert spec["constraints"]["city"] == "Barcelona"
    assert spec["constraints"]["amenities"] == ["breakfast_included", "free_wifi"]
    assert spec["constraints"]["min_rating"] == 8.0
    assert spec["constraints"]["min_price"] == 50
    assert spec["constraints"]["max_price"] == 500
    assert spec["expected_answer"]["property_name"] == "Praktik Èssens"
    assert spec["expected_answer"]["rating"] == 8.9
    assert spec["expected_answer"]["review_count"] == 83
    assert spec["expected_answer"]["nightly_price"] == 83.0
    assert spec["expected_answer"]["brand"] == "Independent"
    assert "Praktik Èssens" in spec["validation"]["must_appear"]
    assert "8.9" in spec["validation"]["must_appear"]
    assert "83" in spec["validation"]["must_appear"]
    assert spec["validation"]["db_predicate"] == "booking.property_matches_constraints"
    assert spec["stability"]["fixture_fixed"] is True


def test_booking_validator_rejects_hotel_brick_for_praktik_spec(tmp_path):
    out = tmp_path / "booking_specs.jsonl"
    assert run_script("scripts/generate_structured_tasks.py", "--site", "booking", "--output", str(out)).returncode == 0
    spec = next(item for item in read_jsonl(out) if item["target_entity"]["name"] == "Praktik Èssens")
    spec_path = tmp_path / "praktik.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")

    ok = run_script("scripts/validate_structured_task.py", "--spec", str(spec_path))
    assert ok.returncode == 0, ok.stderr
    assert "validated" in ok.stdout

    bad = dict(spec)
    bad["expected_answer"] = dict(spec["expected_answer"], property_name="Hotel Brick Barcelona")
    bad["target_entity"] = dict(spec["target_entity"], name="Hotel Brick Barcelona")
    bad_path = tmp_path / "brick.json"
    bad_path.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
    result = run_script("scripts/validate_structured_task.py", "--spec", str(bad_path))
    assert result.returncode != 0
    assert "does not satisfy" in result.stderr


def test_google_flights_generator_emits_valid_cheapest_route_spec(tmp_path):
    out = tmp_path / "flight_specs.jsonl"
    result = run_script(
        "scripts/generate_structured_tasks.py",
        "--site", "google_flights",
        "--family", "one_way_cheapest_flight",
        "--output", str(out),
    )
    assert result.returncode == 0, result.stderr
    specs = read_jsonl(out)
    assert specs
    spec = specs[0]
    assert spec["web_name"] == "Google Flights"
    assert spec["target_entity"]["kind"] == "flight"
    assert spec["constraints"]["trip_type"] == "one-way"
    assert spec["constraints"]["sort"] == "price"
    assert spec["expected_answer"]["flight_number"]
    assert spec["expected_answer"]["price"] > 0
    assert spec["validation"]["db_predicate"] == "google_flights.flight_matches_constraints"

    spec_path = tmp_path / "flight.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    ok = run_script("scripts/validate_structured_task.py", "--spec", str(spec_path))
    assert ok.returncode == 0, ok.stderr
