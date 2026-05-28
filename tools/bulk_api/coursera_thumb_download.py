#!/usr/bin/env python3
"""Download coursera real thumbs harvested in
real_components/snapshots/coursera_org/_image_urls.jsonl into
sites/coursera/static/images/courses/real/<slug>.jpg.

The harvest JSONL has 6876 rows covering 269 unique page slugs (after
stripping the `_<8-hex>` suffix attached by the spider).  We keep one image
per slug (largest / most hero-like), filter <8KB icons, resize to <=600px,
JPEG q85.  Skips slugs already present on disk, and slugs absent from the
courses table (no point downloading thumbs for courses that don't exist).

Run from WebHarbor repo root:
    python3 tools/bulk_api/coursera_thumb_download.py
"""

from __future__ import annotations

import io
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from collections import Counter

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    sys.exit("PIL/Pillow is required: pip install Pillow")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HARVEST = "/home/v-haoqiwang/webvoyager-analysis/real_components/snapshots/coursera_org/_image_urls.jsonl"
DB = os.path.join(REPO_ROOT, "sites/coursera/instance/coursera.db")
OUT_DIR = os.path.join(REPO_ROOT, "sites/coursera/static/images/courses/real")

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
MIN_BYTES = 8 * 1024      # constraint #58 in task brief
MAX_SIDE = 600
SLEEP_SEC = 0.3
TIMEOUT = 8
CAP = 800                  # hard upper bound on downloads
BAIL_AFTER_CONSECUTIVE_FAILS = 10

PAGE_HASH_RE = re.compile(r"^(.+)_[0-9a-f]{6,12}$")
TINY_WH_RE = re.compile(r"[?&](?:w|h|width|height)=(\d{1,2})\b")  # w=28 etc.

JUNK_HOSTS = (
    "bat.bing.net", "googletagmanager", "google-analytics", "doubleclick",
    "facebook.com/tr", "linkedin.com/px", "/pixel", "/beacon",
)


def slug_from_page(p: str) -> str:
    m = PAGE_HASH_RE.match(p)
    return m.group(1) if m else p


def is_junk(u: str) -> bool:
    ul = u.lower()
    return any(j in ul for j in JUNK_HOSTS) or ul.endswith(".gif")


def url_score(u: str) -> int:
    """Heuristic: bigger hero/thumbnail > tiny icon/logo."""
    s = 0
    ul = u.lower()
    if "1200x1200" in ul or "1080x1080" in ul or "1200x800" in ul:
        s += 100
    if "thumbnail" in ul:
        s += 50
    if "hero" in ul or "cover" in ul:
        s += 40
    # tiny dims (w=28, h=45) → almost certainly partner logo
    if TINY_WH_RE.search(ul):
        s -= 40
    if "icon" in ul or "logo" in ul or "/logos/" in ul:
        s -= 80
    # instructor headshots are deadly: they look fine but aren't course art
    if "coursera-instructor-photos" in ul or "instructor" in ul or "headshot" in ul or "avatar" in ul:
        s -= 100
    if "partner" in ul:
        s -= 30
    if "university-assets" in ul:
        s -= 15
    if "coursera-course-photos" in ul:
        s += 40
    if "ctfassets.net" in ul:  # contentful CMS, used for hero modules
        s += 35
    if "d15cw65ipctsrr.cloudfront.net" in ul:  # coursera-specializations cdn
        s += 25
    if "imageproxy" in ul:
        s -= 3
    if re.search(r"\.svg($|\?)", ul):
        s -= 50
    return s


def load_groups() -> dict[str, list[str]]:
    g: dict[str, list[str]] = {}
    with open(HARVEST) as f:
        for line in f:
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            slug = slug_from_page(e.get("page", ""))
            if not slug:
                continue
            url = e.get("url")
            if url:
                g.setdefault(slug, []).append(url)
    return g


def db_slugs() -> set[str]:
    con = sqlite3.connect(DB)
    try:
        return {r[0] for r in con.execute("SELECT slug FROM courses")}
    finally:
        con.close()


def existing_slugs() -> set[str]:
    if not os.path.isdir(OUT_DIR):
        return set()
    out = set()
    for f in os.listdir(OUT_DIR):
        if f.endswith((".jpg", ".jpeg", ".png", ".webp")):
            out.add(os.path.splitext(f)[0])
    return out


def fetch_resize(url: str) -> tuple[bytes | None, str]:
    """Return (bytes, reason). bytes is None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            cl = int(r.headers.get("Content-Length", 0) or 0)
            if cl and cl < MIN_BYTES:
                return None, "too_small_header"
            data = r.read()
    except urllib.error.HTTPError as e:
        return None, f"http_{e.code}"
    except urllib.error.URLError as e:
        return None, f"urlerr_{type(e.reason).__name__}"
    except (TimeoutError, ConnectionError) as e:
        return None, f"conn_{type(e).__name__}"
    if len(data) < MIN_BYTES:
        return None, "too_small_body"
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as e:  # noqa: BLE001
        return None, f"decode_{type(e).__name__}"
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    try:
        img.convert("RGB").save(buf, "JPEG", quality=85)
    except Exception as e:  # noqa: BLE001
        return None, f"encode_{type(e).__name__}"
    return buf.getvalue(), "ok"


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    groups = load_groups()
    have_db = db_slugs()
    have_disk = existing_slugs()

    candidates: list[tuple[str, list[str]]] = []  # (slug, ranked_urls)
    skip_existing = 0
    skip_no_db = 0
    skip_no_url = 0
    for slug, urls in groups.items():
        if slug in have_disk:
            skip_existing += 1
            continue
        if slug not in have_db:
            skip_no_db += 1
            continue
        # dedupe + drop trackers, score, keep top 5 to allow fallback
        clean = [u for u in dict.fromkeys(urls) if not is_junk(u)]
        ranked = sorted(clean, key=url_score, reverse=True)[:5]
        if not ranked:
            skip_no_url += 1
            continue
        candidates.append((slug, ranked))

    print(f"harvest groups        : {len(groups)}")
    print(f"  skip already-on-disk: {skip_existing}")
    print(f"  skip not-in-db      : {skip_no_db}")
    print(f"  skip no-url         : {skip_no_url}")
    print(f"  candidates          : {len(candidates)}")
    if len(candidates) > CAP:
        print(f"  capping to {CAP}")
        candidates = candidates[:CAP]

    ok = 0
    fail = Counter()
    consec_fail = 0
    t_total = 0.0
    n_attempts = 0
    bailed = False

    for i, (slug, urls) in enumerate(candidates, 1):
        data: bytes | None = None
        last_reason = "no_url"
        for u in urls:
            t0 = time.time()
            data, last_reason = fetch_resize(u)
            t_total += time.time() - t0
            n_attempts += 1
            if data is not None:
                break
            time.sleep(SLEEP_SEC)
        if data is None:
            fail[last_reason] += 1
            consec_fail += 1
            if i % 10 == 0 or i == len(candidates):
                print(f"  [{i}/{len(candidates)}] {slug}  FAIL {last_reason}")
            if consec_fail >= BAIL_AFTER_CONSECUTIVE_FAILS:
                print(f"!! bail: {consec_fail} consecutive failures")
                bailed = True
                break
            time.sleep(SLEEP_SEC)
            continue
        path = os.path.join(OUT_DIR, f"{slug}.jpg")
        with open(path, "wb") as f:
            f.write(data)
        ok += 1
        consec_fail = 0
        if i <= 5 or i % 25 == 0 or i == len(candidates):
            print(f"  [{i}/{len(candidates)}] {slug}  OK ({len(data)//1024}KB)")
        time.sleep(SLEEP_SEC)

    print()
    print("== summary ==")
    print(f"  attempts (incl retries): {n_attempts}")
    print(f"  ok                     : {ok}")
    print(f"  failed slugs           : {sum(fail.values())}  {dict(fail)}")
    if n_attempts:
        print(f"  avg time / attempt     : {t_total / n_attempts:.2f}s")
    print(f"  bailed                 : {bailed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
