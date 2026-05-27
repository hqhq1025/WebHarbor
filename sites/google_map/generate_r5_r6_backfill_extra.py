"""Augment R5 / R6 backfill with extra tasks so each round ≥200.

Idempotent via id high-water mark + task_type filter (skips if r5 task
count already >= target).  Run after generate_r4_r5_r6_backfill_tasks.py.
"""
import hashlib
import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent
TASKS_FILE = BASE / "tasks.jsonl"
DB = BASE / "instance_seed" / "gmaps.db"
WEB = "http://localhost:40008/"
UPSTREAM = "https://www.google.com/maps/"


def fetch_slugs(cat_slug, limit=24):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "SELECT slug FROM place "
        "WHERE category_id=(SELECT id FROM category WHERE slug=?) "
        "AND slug LIKE 'r5-%' "
        "ORDER BY slug LIMIT ?",
        (cat_slug, limit),
    )
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows


def next_id():
    n = 0
    with TASKS_FILE.open() as f:
        for line in f:
            try:
                tid = json.loads(line).get("id", "")
                if "--" in tid:
                    n = max(n, int(tid.split("--")[1]) + 1)
            except (json.JSONDecodeError, ValueError):
                pass
    return n


def count_round(prefix):
    n = 0
    with TASKS_FILE.open() as f:
        for line in f:
            try:
                tt = json.loads(line).get("task_type", "")
                if tt.startswith(prefix):
                    n += 1
            except json.JSONDecodeError:
                pass
    return n


def gen_extra_r5():
    out = []
    ev = fetch_slugs("ev-charging", 24)
    gas = fetch_slugs("gas-stations", 24)
    park = fetch_slugs("parking", 24)
    for s in ev:
        out.append((f"Open /charging/{s}/connectors and report whether J1772 is listed as Present.",
                    "r5-ev-connectors"))
        out.append((f"Open /charging/{s} and report the idle fee per minute charged after charging completes.",
                    "r5-ev-charging-detail"))
    for s in gas:
        out.append((f"Open /gas-station/{s} and report whether a convenience store and car wash are available.",
                    "r5-gas-station-detail"))
        out.append((f"Open /gas-station/{s}/price-history and report the Midgrade price for Day -3.",
                    "r5-gas-station-price-history"))
    for s in park:
        out.append((f"Open /parking-lot/{s}/realtime and report the peak hour (highest occupancy %).",
                    "r5-parking-lot-realtime"))
        out.append((f"Open /parking-lot/{s} and report the monthly pass price along with the lot type.",
                    "r5-parking-lot-detail"))
    return out


# Additional R6 anchors so we comfortably clear ≥200
R6_EXTRA_SLUGS = [
    "san-francisco-pier-39", "new-york-ny-bryant-park",
    "new-york-ny-madison-square-garden", "new-york-ny-fifth-avenue",
    "chicago-il-the-bean", "chicago-il-shedd-aquarium",
    "chicago-il-art-institute-of-chicago", "boston-quincy-market",
    "boston-boston-public-garden", "boston-museum-of-fine-arts",
    "los-angeles-getty-center", "los-angeles-venice-beach",
    "seattle-museum-of-pop-culture", "seattle-chihuly-garden-and-glass",
    "san-francisco-painted-ladies", "san-francisco-coit-tower",
    "washington-dc-national-mall", "washington-dc-smithsonian-national-museum-of-natural-history",
    "philadelphia-independence-hall", "miami-fl-vizcaya-museum-and-gardens",
    "denver-denver-art-museum", "portland-pittock-mansion",
    "atlanta-ga-piedmont-park", "houston-tx-houston-museum-of-natural-science",
    "dallas-tx-the-sixth-floor-museum", "phoenix-desert-botanical-garden",
]


def _sphere_id(slug):
    return hashlib.md5(f"sphere:{slug}".encode()).hexdigest()[:12]


def gen_extra_r6():
    out = []
    for s in R6_EXTRA_SLUGS:
        out.append((f"Open /street-view/{s}/panorama and report the field-of-view value shown.",
                    "r6-streetview-panorama"))
        out.append((f"Open the Street View timeline /street-view/{s}/timeline and report the oldest capture year listed.",
                    "r6-streetview-timeline"))
        out.append((f"Open /photosphere/{_sphere_id(s)} and report the resolution given for the photosphere.",
                    "r6-photosphere-detail"))
    return out


def main():
    if count_round("r5-") >= 240 and count_round("r6-") >= 240:
        print("[skip] r5 and r6 already saturated")
        return
    extra = gen_extra_r5() + gen_extra_r6()
    print(f"r5 currently {count_round('r5-')}, r6 currently {count_round('r6-')}")
    print(f"appending: r5 +{sum(1 for _,t in extra if t.startswith('r5-'))}, "
          f"r6 +{sum(1 for _,t in extra if t.startswith('r6-'))}")
    nid = next_id()
    with TASKS_FILE.open("a") as f:
        for q, tt in extra:
            row = {
                "web_name": "Google Map",
                "id": f"Google Map--{nid}",
                "ques": q,
                "web": WEB,
                "upstream_url": UPSTREAM,
                "task_type": tt,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            nid += 1
    print(f"final r5 {count_round('r5-')}, r6 {count_round('r6-')}")


if __name__ == "__main__":
    main()
