#!/usr/bin/env python3
"""Retry state + city image fetches, throttled to avoid Wikipedia 429."""
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

# Reuse lists
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from download_smartasset_images import STATES, CITIES, state_slug


def fetch(url, dest, timeout=20):
    if os.path.exists(dest) and os.path.getsize(dest) > 500:
        return True
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
        if len(data) < 500:
            return False
        with open(dest, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        print(f"  ! FAIL {url[:80]}: {e}", file=sys.stderr)
        return False


def resolve(query, retries=3):
    encoded = urllib.parse.quote(query.replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode("utf-8"))
            # Use thumbnail URL as-is (Wikipedia gives 330px which is fine)
            thumb = (data.get("thumbnail") or {}).get("source")
            if not thumb:
                thumb = (data.get("originalimage") or {}).get("source")
            return thumb
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            return None
        except Exception:
            return None
    return None


def main():
    # Build tasks for missing state + city files
    tasks = []  # (query, dest)
    for state_name, query in STATES:
        slug = state_slug(state_name)
        dest = os.path.join(BASE, "states", f"{slug}.jpg")
        if not os.path.exists(dest) or os.path.getsize(dest) < 500:
            tasks.append((query, dest))
    for city_slug, query in CITIES:
        dest = os.path.join(BASE, "cities", f"{city_slug}.jpg")
        if not os.path.exists(dest) or os.path.getsize(dest) < 500:
            tasks.append((query, dest))

    print(f"Need to fetch: {len(tasks)} images")

    # Throttled resolution (1 req/sec to be safe)
    resolved = []
    for i, (query, dest) in enumerate(tasks):
        url = resolve(query)
        if url:
            resolved.append((url, dest))
        time.sleep(1.0)
        if (i + 1) % 10 == 0:
            print(f"  resolved {i+1}/{len(tasks)}")

    print(f"Resolved {len(resolved)}/{len(tasks)}")

    # Now download throttled (avoid 429)
    ok = fail = 0
    for u, d in resolved:
        if fetch(u, d):
            ok += 1
        else:
            fail += 1
        time.sleep(0.5)
    print(f"DOWNLOADED: {ok}/{len(resolved)} ({fail} fail)")


if __name__ == "__main__":
    main()
