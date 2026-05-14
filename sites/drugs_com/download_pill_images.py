"""Download public-domain pill images from NLM DailyMed for seeded drugs.

The NLM RxImages API (``rximage.nlm.nih.gov``) has been retired, so this
script falls back to the still-live DailyMed v2 web service, which exposes
the same public-domain SPL pill photographs at:

    https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?drug_name=NAME
    https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/<setid>/media.json

For each seeded drug (read directly from ``instance_seed/drugs_com.db`` via
``sqlite3``, no Flask import), the script searches DailyMed by generic
name, walks the SPLs in order, and writes the first JPEG it finds to
``static/images/pills/<slug>.jpg``. Existing files are skipped so the
script is rerunnable.

Run from this directory:

    uv run python download_pill_images.py
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance_seed", "drugs_com.db")
OUT_DIR = os.path.join(BASE_DIR, "static", "images", "pills")

DM_SEARCH = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json"
DM_MEDIA = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{setid}/media.json"

USER_AGENT = "WebHarbor-drugs.com mirror seed (public domain DailyMed images)"
TIMEOUT = 20
SLP = 0.4  # be polite to NLM

# Drug names the user explicitly called out, plus we'll also pick up every
# row in the DB. Brand-name aliases let us retry when a generic search
# returns nothing useful.
BRAND_ALIASES: dict[str, list[str]] = {
    "ibuprofen": ["Advil", "Motrin"],
    "acetaminophen": ["Tylenol"],
    "sildenafil": ["Viagra"],
    "semaglutide": ["Ozempic", "Wegovy"],
    "atorvastatin": ["Lipitor"],
    "alprazolam": ["Xanax"],
    "zolpidem": ["Ambien"],
    "sertraline": ["Zoloft"],
    "duloxetine": ["Cymbalta"],
    "metformin": ["Glucophage"],
    "omeprazole": ["Prilosec"],
    "loratadine": ["Claritin"],
    "amoxicillin": ["Amoxil"],
    "azithromycin": ["Zithromax"],
    "ciprofloxacin": ["Cipro"],
    "doxycycline": ["Vibramycin"],
    "warfarin": ["Coumadin"],
    "lisinopril": ["Prinivil", "Zestril"],
    "metoprolol": ["Lopressor", "Toprol"],
    "amlodipine": ["Norvasc"],
    "hydrochlorothiazide": ["Microzide"],
    "gabapentin": ["Neurontin"],
    "clonazepam": ["Klonopin"],
    "cyclobenzaprine": ["Flexeril"],
    "tramadol": ["Ultram"],
    "prednisone": ["Deltasone"],
}


def http_get_json(url: str) -> dict | None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
        print(f"  ! GET {url} failed: {e}", file=sys.stderr)
        return None


def http_get_bytes(url: str) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"  ! GET {url} failed: {e}", file=sys.stderr)
        return None


def find_image_url_for(name: str) -> str | None:
    """Search DailyMed for `name` and return the first JPEG URL we can find.

    Walks up to a handful of SPLs because the top hit often has no image
    (e.g. oral suspensions) while a downstream tablet SPL does.
    """
    qs = urllib.parse.urlencode({"drug_name": name, "pagesize": 8})
    search = http_get_json(f"{DM_SEARCH}?{qs}")
    if not search:
        return None
    for spl in search.get("data", []):
        setid = spl.get("setid")
        if not setid:
            continue
        time.sleep(SLP)
        media = http_get_json(DM_MEDIA.format(setid=setid))
        if not media:
            continue
        for m in media.get("data", {}).get("media", []) or []:
            if m.get("mime_type", "").startswith("image/jpeg"):
                # Skip "structure diagram" style images when we can — they
                # look like chemistry sketches, not pills.
                nm = (m.get("name") or "").lower()
                if "-str" in nm or "struct" in nm or "logo" in nm:
                    continue
                url = m.get("url")
                if url:
                    return url
        # Fall back to any JPEG if we couldn't find a non-structure one.
        for m in media.get("data", {}).get("media", []) or []:
            if m.get("mime_type", "").startswith("image/jpeg") and m.get("url"):
                return m["url"]
    return None


def download_for_drug(slug: str, generic_name: str) -> bool:
    out_path = os.path.join(OUT_DIR, f"{slug}.jpg")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        print(f"= {slug}: already present, skipping")
        return True

    names: list[str] = [generic_name]
    names.extend(BRAND_ALIASES.get(slug, []))

    for candidate in names:
        print(f"  ? searching DailyMed for {candidate!r}")
        url = find_image_url_for(candidate)
        time.sleep(SLP)
        if not url:
            continue
        data = http_get_bytes(url)
        if not data or len(data) < 2000:
            # Tiny payload likely an HTML error page.
            continue
        with open(out_path, "wb") as f:
            f.write(data)
        print(f"+ {slug}: saved {len(data):,} bytes from {url}")
        return True

    print(f"- {slug}: no image found")
    return False


def main() -> int:
    if not os.path.exists(DB_PATH):
        print(f"DB not found: {DB_PATH}", file=sys.stderr)
        return 1
    os.makedirs(OUT_DIR, exist_ok=True)

    con = sqlite3.connect(DB_PATH)
    try:
        rows = con.execute("SELECT slug, generic_name FROM drug ORDER BY slug").fetchall()
    finally:
        con.close()

    print(f"Found {len(rows)} drugs in DB. Output dir: {OUT_DIR}")
    ok = 0
    for slug, generic_name in rows:
        try:
            if download_for_drug(slug, generic_name):
                ok += 1
        except Exception as e:  # noqa: BLE001 - keep going on any single failure
            print(f"  ! {slug}: unexpected {type(e).__name__}: {e}", file=sys.stderr)
    print(f"\nDone. {ok}/{len(rows)} drugs have a local pill image.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
