#!/usr/bin/env python3
"""Bulk download images for sites/smartasset.

Sources:
- Authors (12)   → pravatar.cc/300?img=1..12
- Advisors (153) → randomuser.me/api/portraits/{men|women}/0..99.jpg
- States (51)    → Wikipedia REST summary thumbnail (top metro city)
- Articles (80)  → curated Pexels finance/business stock photos
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "sites", "smartasset", "static", "images")
BASE = os.path.abspath(BASE)

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def fetch(url, dest, timeout=15, retries=2):
    """GET url to dest. Returns True on success."""
    if os.path.exists(dest) and os.path.getsize(dest) > 500:
        return True
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                if r.status != 200:
                    last_err = f"HTTP {r.status}"
                    continue
                data = r.read()
            if len(data) < 500:
                last_err = f"tiny {len(data)}"
                continue
            with open(dest, "wb") as f:
                f.write(data)
            return True
        except Exception as e:
            last_err = repr(e)
            time.sleep(0.3 * (attempt + 1))
    print(f"  ! FAIL {url} -> {dest}: {last_err}", file=sys.stderr)
    return False


# ─────────────── Author headshots (pravatar) ────────────────────
AUTHORS = [
    "rebecca-lake", "jeff-white", "lauren-perez", "susannah-snider",
    "mark-henricks", "liz-smith", "patrick-villanova", "amanda-dixon",
    "hunter-kuffel", "ben-geier", "becca-stanek", "eric-reed",
]


def download_authors():
    tasks = []
    # pravatar offers ~70 unique real photos; use 1..12
    for i, slug in enumerate(AUTHORS, start=1):
        url = f"https://i.pravatar.cc/400?img={i}"
        dest = os.path.join(BASE, "authors", f"{slug}.jpg")
        tasks.append((url, dest))
    return tasks


# ─────────────── Advisor headshots (randomuser.me) ──────────────
def download_advisors():
    """153 advisors. Distribute across men/0..99 + women/0..99."""
    tasks = []
    # Mirror the deterministic numbering used by seed_data: 51 states x 3.
    # We do not depend on actual names; we just need a stable per-index URL.
    for idx in range(1, 200):  # generate a bit more than 153 for headroom
        # alternate men/women, cycle 0..99
        gender = "men" if idx % 2 == 0 else "women"
        n = (idx * 13 + 7) % 100  # deterministic spread
        url = f"https://randomuser.me/api/portraits/{gender}/{n}.jpg"
        dest = os.path.join(BASE, "advisors", f"advisor-{idx:03d}.jpg")
        tasks.append((url, dest))
    return tasks


# ─────────────── State landmarks (Wikipedia) ────────────────────
STATES = [
    ("Alabama", "Birmingham, Alabama"),
    ("Alaska", "Anchorage"),
    ("Arizona", "Phoenix, Arizona"),
    ("Arkansas", "Little Rock, Arkansas"),
    ("California", "Los Angeles"),
    ("Colorado", "Denver"),
    ("Connecticut", "Stamford, Connecticut"),
    ("Delaware", "Wilmington, Delaware"),
    ("Florida", "Miami"),
    ("Georgia", "Atlanta"),
    ("Hawaii", "Honolulu"),
    ("Idaho", "Boise, Idaho"),
    ("Illinois", "Chicago"),
    ("Indiana", "Indianapolis"),
    ("Iowa", "Des Moines, Iowa"),
    ("Kansas", "Kansas City, Kansas"),
    ("Kentucky", "Louisville, Kentucky"),
    ("Louisiana", "New Orleans"),
    ("Maine", "Portland, Maine"),
    ("Maryland", "Baltimore"),
    ("Massachusetts", "Boston"),
    ("Michigan", "Detroit"),
    ("Minnesota", "Minneapolis"),
    ("Mississippi", "Jackson, Mississippi"),
    ("Missouri", "Kansas City, Missouri"),
    ("Montana", "Billings, Montana"),
    ("Nebraska", "Omaha, Nebraska"),
    ("Nevada", "Las Vegas"),
    ("New Hampshire", "Manchester, New Hampshire"),
    ("New Jersey", "Newark, New Jersey"),
    ("New Mexico", "Albuquerque, New Mexico"),
    ("New York", "New York City"),
    ("North Carolina", "Charlotte, North Carolina"),
    ("North Dakota", "Fargo, North Dakota"),
    ("Ohio", "Columbus, Ohio"),
    ("Oklahoma", "Oklahoma City"),
    ("Oregon", "Portland, Oregon"),
    ("Pennsylvania", "Philadelphia"),
    ("Rhode Island", "Providence, Rhode Island"),
    ("South Carolina", "Charleston, South Carolina"),
    ("South Dakota", "Sioux Falls, South Dakota"),
    ("Tennessee", "Nashville, Tennessee"),
    ("Texas", "Houston"),
    ("Utah", "Salt Lake City"),
    ("Vermont", "Burlington, Vermont"),
    ("Virginia", "Virginia Beach, Virginia"),
    ("Washington", "Seattle"),
    ("West Virginia", "Charleston, West Virginia"),
    ("Wisconsin", "Milwaukee"),
    ("Wyoming", "Cheyenne, Wyoming"),
    ("District of Columbia", "Washington, D.C."),
]


def state_slug(name):
    return name.lower().replace(" ", "-")


def download_states():
    """For each state, query Wikipedia summary, grab thumbnail."""
    tasks = []
    for state_name, query in STATES:
        slug = state_slug(state_name)
        dest = os.path.join(BASE, "states", f"{slug}.jpg")
        tasks.append((("STATE", query), dest))
    return tasks


def resolve_state(query):
    """Fetch wikipedia summary thumbnail URL for query."""
    encoded = urllib.parse.quote(query.replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        thumb = data.get("thumbnail", {}).get("source") or \
                data.get("originalimage", {}).get("source")
        return thumb
    except Exception as e:
        print(f"  ! state resolve fail {query}: {e}", file=sys.stderr)
        return None


# ─────────────── Article hero images (Pexels) ───────────────────
# Curated Pexels static URLs — finance/business/lifestyle stock.
# Use w=800 thumbnails for smaller payload.
PEXELS_PHOTOS = [
    # Money / finance
    "https://images.pexels.com/photos/164527/pexels-photo-164527.jpeg",
    "https://images.pexels.com/photos/210600/pexels-photo-210600.jpeg",
    "https://images.pexels.com/photos/259027/pexels-photo-259027.jpeg",
    "https://images.pexels.com/photos/259165/pexels-photo-259165.jpeg",
    "https://images.pexels.com/photos/259200/pexels-photo-259200.jpeg",
    "https://images.pexels.com/photos/590016/pexels-photo-590016.jpeg",
    "https://images.pexels.com/photos/590020/pexels-photo-590020.jpeg",
    "https://images.pexels.com/photos/730547/pexels-photo-730547.jpeg",
    "https://images.pexels.com/photos/870902/pexels-photo-870902.jpeg",
    "https://images.pexels.com/photos/259209/pexels-photo-259209.jpeg",
    # Charts / business
    "https://images.pexels.com/photos/186461/pexels-photo-186461.jpeg",
    "https://images.pexels.com/photos/187041/pexels-photo-187041.jpeg",
    "https://images.pexels.com/photos/277430/pexels-photo-277430.jpeg",
    "https://images.pexels.com/photos/265087/pexels-photo-265087.jpeg",
    "https://images.pexels.com/photos/342945/pexels-photo-342945.jpeg",
    "https://images.pexels.com/photos/590022/pexels-photo-590022.jpeg",
    "https://images.pexels.com/photos/95916/pexels-photo-95916.jpeg",
    "https://images.pexels.com/photos/210990/pexels-photo-210990.jpeg",
    "https://images.pexels.com/photos/265125/pexels-photo-265125.jpeg",
    "https://images.pexels.com/photos/669619/pexels-photo-669619.jpeg",
    # House / mortgage
    "https://images.pexels.com/photos/106399/pexels-photo-106399.jpeg",
    "https://images.pexels.com/photos/280222/pexels-photo-280222.jpeg",
    "https://images.pexels.com/photos/323780/pexels-photo-323780.jpeg",
    "https://images.pexels.com/photos/259588/pexels-photo-259588.jpeg",
    "https://images.pexels.com/photos/210617/pexels-photo-210617.jpeg",
    "https://images.pexels.com/photos/259593/pexels-photo-259593.jpeg",
    "https://images.pexels.com/photos/8728382/pexels-photo-8728382.jpeg",
    "https://images.pexels.com/photos/1396122/pexels-photo-1396122.jpeg",
    "https://images.pexels.com/photos/2098624/pexels-photo-2098624.jpeg",
    "https://images.pexels.com/photos/1029599/pexels-photo-1029599.jpeg",
    # Retirement / lifestyle
    "https://images.pexels.com/photos/63622/pexels-photo-63622.jpeg",
    "https://images.pexels.com/photos/839011/pexels-photo-839011.jpeg",
    "https://images.pexels.com/photos/1156685/pexels-photo-1156685.jpeg",
    "https://images.pexels.com/photos/2566581/pexels-photo-2566581.jpeg",
    "https://images.pexels.com/photos/1471843/pexels-photo-1471843.jpeg",
    "https://images.pexels.com/photos/1170979/pexels-photo-1170979.jpeg",
    "https://images.pexels.com/photos/1153369/pexels-photo-1153369.jpeg",
    "https://images.pexels.com/photos/1170979/pexels-photo-1170979.jpeg",
    "https://images.pexels.com/photos/3768131/pexels-photo-3768131.jpeg",
    "https://images.pexels.com/photos/8108065/pexels-photo-8108065.jpeg",
    # Office / desk
    "https://images.pexels.com/photos/210607/pexels-photo-210607.jpeg",
    "https://images.pexels.com/photos/1181263/pexels-photo-1181263.jpeg",
    "https://images.pexels.com/photos/3184292/pexels-photo-3184292.jpeg",
    "https://images.pexels.com/photos/3184465/pexels-photo-3184465.jpeg",
    "https://images.pexels.com/photos/4386339/pexels-photo-4386339.jpeg",
    "https://images.pexels.com/photos/518543/pexels-photo-518543.jpeg",
    "https://images.pexels.com/photos/3760067/pexels-photo-3760067.jpeg",
    "https://images.pexels.com/photos/3760790/pexels-photo-3760790.jpeg",
    "https://images.pexels.com/photos/3760069/pexels-photo-3760069.jpeg",
    "https://images.pexels.com/photos/4386292/pexels-photo-4386292.jpeg",
    # Calculator / tax / paperwork
    "https://images.pexels.com/photos/6863253/pexels-photo-6863253.jpeg",
    "https://images.pexels.com/photos/6694543/pexels-photo-6694543.jpeg",
    "https://images.pexels.com/photos/4386371/pexels-photo-4386371.jpeg",
    "https://images.pexels.com/photos/4386336/pexels-photo-4386336.jpeg",
    "https://images.pexels.com/photos/4386324/pexels-photo-4386324.jpeg",
    "https://images.pexels.com/photos/4386431/pexels-photo-4386431.jpeg",
    "https://images.pexels.com/photos/3943728/pexels-photo-3943728.jpeg",
    "https://images.pexels.com/photos/5466787/pexels-photo-5466787.jpeg",
    "https://images.pexels.com/photos/6694880/pexels-photo-6694880.jpeg",
    "https://images.pexels.com/photos/7821485/pexels-photo-7821485.jpeg",
    # Insurance / family / car
    "https://images.pexels.com/photos/3760529/pexels-photo-3760529.jpeg",
    "https://images.pexels.com/photos/3815585/pexels-photo-3815585.jpeg",
    "https://images.pexels.com/photos/4173251/pexels-photo-4173251.jpeg",
    "https://images.pexels.com/photos/3760267/pexels-photo-3760267.jpeg",
    "https://images.pexels.com/photos/1051838/pexels-photo-1051838.jpeg",
    "https://images.pexels.com/photos/1456291/pexels-photo-1456291.jpeg",
    "https://images.pexels.com/photos/2533266/pexels-photo-2533266.jpeg",
    "https://images.pexels.com/photos/733872/pexels-photo-733872.jpeg",
    "https://images.pexels.com/photos/3933062/pexels-photo-3933062.jpeg",
    "https://images.pexels.com/photos/802221/pexels-photo-802221.jpeg",
    # Credit cards / banking
    "https://images.pexels.com/photos/259200/pexels-photo-259200.jpeg",
    "https://images.pexels.com/photos/210742/pexels-photo-210742.jpeg",
    "https://images.pexels.com/photos/4968382/pexels-photo-4968382.jpeg",
    "https://images.pexels.com/photos/210746/pexels-photo-210746.jpeg",
    "https://images.pexels.com/photos/1546166/pexels-photo-1546166.jpeg",
    "https://images.pexels.com/photos/2988232/pexels-photo-2988232.jpeg",
    "https://images.pexels.com/photos/2988233/pexels-photo-2988233.jpeg",
    "https://images.pexels.com/photos/4968382/pexels-photo-4968382.jpeg",
    "https://images.pexels.com/photos/210600/pexels-photo-210600.jpeg",
    "https://images.pexels.com/photos/8927637/pexels-photo-8927637.jpeg",
    # Generic finance/abstract
    "https://images.pexels.com/photos/534216/pexels-photo-534216.jpeg",
    "https://images.pexels.com/photos/669621/pexels-photo-669621.jpeg",
    "https://images.pexels.com/photos/534204/pexels-photo-534204.jpeg",
    "https://images.pexels.com/photos/6770610/pexels-photo-6770610.jpeg",
    "https://images.pexels.com/photos/6694886/pexels-photo-6694886.jpeg",
    "https://images.pexels.com/photos/4386367/pexels-photo-4386367.jpeg",
    "https://images.pexels.com/photos/7723533/pexels-photo-7723533.jpeg",
    "https://images.pexels.com/photos/6694540/pexels-photo-6694540.jpeg",
    "https://images.pexels.com/photos/7821485/pexels-photo-7821485.jpeg",
    "https://images.pexels.com/photos/6863183/pexels-photo-6863183.jpeg",
]


def download_articles():
    tasks = []
    for i, raw_url in enumerate(PEXELS_PHOTOS):
        url = f"{raw_url}?auto=compress&cs=tinysrgb&w=800"
        dest = os.path.join(BASE, "articles", f"article-{i+1:03d}.jpg")
        tasks.append((url, dest))
    return tasks


# ─────────────── Cities (Pexels reuse) ──────────────────────────
CITIES = [
    # (name, query / state)
    ("new-york-ny", "New York City"),
    ("los-angeles-ca", "Los Angeles"),
    ("chicago-il", "Chicago"),
    ("houston-tx", "Houston"),
    ("phoenix-az", "Phoenix, Arizona"),
    ("philadelphia-pa", "Philadelphia"),
    ("san-antonio-tx", "San Antonio"),
    ("san-diego-ca", "San Diego"),
    ("dallas-tx", "Dallas"),
    ("austin-tx", "Austin, Texas"),
    ("san-jose-ca", "San Jose, California"),
    ("fort-worth-tx", "Fort Worth, Texas"),
    ("jacksonville-fl", "Jacksonville, Florida"),
    ("columbus-oh", "Columbus, Ohio"),
    ("charlotte-nc", "Charlotte, North Carolina"),
    ("indianapolis-in", "Indianapolis"),
    ("san-francisco-ca", "San Francisco"),
    ("seattle-wa", "Seattle"),
    ("denver-co", "Denver"),
    ("washington-dc", "Washington, D.C."),
    ("boston-ma", "Boston"),
    ("nashville-tn", "Nashville, Tennessee"),
    ("oklahoma-city-ok", "Oklahoma City"),
    ("el-paso-tx", "El Paso, Texas"),
    ("portland-or", "Portland, Oregon"),
    ("las-vegas-nv", "Las Vegas"),
    ("memphis-tn", "Memphis, Tennessee"),
    ("detroit-mi", "Detroit"),
    ("baltimore-md", "Baltimore"),
    ("milwaukee-wi", "Milwaukee"),
    ("albuquerque-nm", "Albuquerque, New Mexico"),
    ("tucson-az", "Tucson, Arizona"),
    ("fresno-ca", "Fresno, California"),
    ("sacramento-ca", "Sacramento, California"),
    ("kansas-city-mo", "Kansas City, Missouri"),
    ("mesa-az", "Mesa, Arizona"),
    ("atlanta-ga", "Atlanta"),
    ("omaha-ne", "Omaha, Nebraska"),
    ("colorado-springs-co", "Colorado Springs"),
    ("raleigh-nc", "Raleigh, North Carolina"),
    ("miami-fl", "Miami"),
    ("long-beach-ca", "Long Beach, California"),
    ("virginia-beach-va", "Virginia Beach, Virginia"),
    ("oakland-ca", "Oakland, California"),
    ("minneapolis-mn", "Minneapolis"),
    ("tulsa-ok", "Tulsa, Oklahoma"),
    ("arlington-tx", "Arlington, Texas"),
    ("tampa-fl", "Tampa, Florida"),
    ("new-orleans-la", "New Orleans"),
    ("wichita-ks", "Wichita, Kansas"),
]


def download_cities():
    tasks = []
    for slug, query in CITIES:
        dest = os.path.join(BASE, "cities", f"{slug}.jpg")
        tasks.append((("STATE", query), dest))  # reuse wikipedia resolver
    return tasks


# ─────────────── Driver ─────────────────────────────────────────
def main():
    all_tasks = []
    all_tasks += download_authors()
    all_tasks += download_advisors()
    all_tasks += download_articles()

    # State + city tasks need Wikipedia resolution first
    pending_lookup = download_states() + download_cities()

    print(f"Plan: {len(all_tasks)} direct + {len(pending_lookup)} wiki-lookup")

    # Resolve wiki URLs first (sequential, polite)
    resolved = []
    for (kind, query), dest in pending_lookup:
        url = resolve_state(query)
        if url:
            resolved.append((url, dest))
        time.sleep(0.15)
    print(f"Resolved {len(resolved)}/{len(pending_lookup)} wiki entries")
    all_tasks += resolved

    # Download in parallel
    ok = fail = 0
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(fetch, url, dest): (url, dest)
                for url, dest in all_tasks}
        for fut in as_completed(futs):
            if fut.result():
                ok += 1
            else:
                fail += 1
            if (ok + fail) % 25 == 0:
                print(f"  progress: {ok} ok / {fail} fail")
    print(f"FINAL: {ok} ok / {fail} fail / {len(all_tasks)} total")


if __name__ == "__main__":
    main()
