"""Single-threaded retry pass for failed Wikipedia Commons downloads.

The first pass tripped Wikimedia's bot rate-limiter on ~340 files. Wait, then
retry slowly with one request per second.
"""
import os
import sys
import json
import time
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
IMG_ROOT = os.path.join(BASE, "static", "images")
CATALOG_FILE = os.path.join(BASE, "_image_catalog.json")

UA = "WebHarbor-Mirror-Builder/1.0 (https://github.com/aiming-lab/WebHarbor; contact: webharbor@example.org) Python-urllib/3.12"


def safe_basename(title):
    base = title.replace(" ", "_").replace("/", "_").replace("%2C", ",")
    base = "".join(c for c in base if c.isalnum() or c in "._-")
    return (base or "img.jpg")[:200]


def fetch(subdir, title):
    fname = safe_basename(title)
    dest = os.path.join(IMG_ROOT, subdir, fname)
    if os.path.exists(dest) and os.path.getsize(dest) > 5000:
        return "skip"
    width = "" if title.lower().endswith(".svg") else "&width=800"
    url = (
        "https://commons.wikimedia.org/w/index.php?title=Special:FilePath/"
        + urllib.parse.quote(title.replace(" ", "_")) + width
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=25) as r:
            ct = r.headers.get("Content-Type", "")
            data = r.read()
        if not ct.startswith("image/") and "svg" not in ct:
            return "bad-ct"
        if len(data) < 5000:
            return "tiny"
        tmp = dest + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, dest)
        return "ok"
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return "429"
        if e.code == 404:
            return "404"
        return f"http{e.code}"
    except Exception as e:
        return f"err:{type(e).__name__}"


def main():
    with open(CATALOG_FILE) as f:
        catalog = json.load(f)
    jobs = []
    for subdir, titles in catalog.items():
        for t in titles:
            if t.startswith(("_from:", "_html:")):
                continue
            fname = safe_basename(t)
            dest = os.path.join(IMG_ROOT, subdir, fname)
            if not (os.path.exists(dest) and os.path.getsize(dest) > 5000):
                jobs.append((subdir, t))
    print(f"retry jobs: {len(jobs)}", flush=True)
    counts = {}
    sleeps = 0
    started = time.time()
    for i, (sub, t) in enumerate(jobs):
        res = fetch(sub, t)
        counts[res] = counts.get(res, 0) + 1
        # adaptive delay: when we see a 429, back off significantly
        if res == "429":
            sleeps += 1
            wait = min(30, 5 + sleeps * 2)
            time.sleep(wait)
        else:
            sleeps = max(0, sleeps - 1)
            time.sleep(1.1)
        if (i + 1) % 50 == 0:
            el = time.time() - started
            print(f"  progress {i+1}/{len(jobs)} ({el:.0f}s) {counts}", flush=True)
    print(f"RETRY DONE {counts} in {time.time()-started:.0f}s", flush=True)


if __name__ == "__main__":
    main()
