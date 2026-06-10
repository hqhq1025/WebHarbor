"""Faster, more resilient downloader with per-request timeout and dedup.
Reads catalog produced by _fetch_images.py harvest. Writes to static/images/<sub>/.
"""
import os
import sys
import json
import time
import socket
import hashlib
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = os.path.dirname(os.path.abspath(__file__))
IMG_ROOT = os.path.join(BASE, "static", "images")
CATALOG_FILE = os.path.join(BASE, "_image_catalog.json")

UA = "WebHarbor-Mirror-Builder/1.0 (https://github.com/aiming-lab/WebHarbor; contact: webharbor@example.org) Python-urllib/3.12"
HEADERS = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}

socket.setdefaulttimeout(20)


def safe_basename(title):
    base = title.replace(" ", "_").replace("/", "_").replace("%2C", ",")
    base = "".join(c for c in base if c.isalnum() or c in "._-")
    return (base or "img.jpg")[:200]


def download(args):
    subdir, title = args
    fname = safe_basename(title)
    dest = os.path.join(IMG_ROOT, subdir, fname)
    if os.path.exists(dest) and os.path.getsize(dest) > 5000:
        return ("skip", subdir, title)
    width = "" if title.lower().endswith(".svg") else "&width=800"
    url = (
        "https://commons.wikimedia.org/w/index.php?title=Special:FilePath/"
        + urllib.parse.quote(title.replace(" ", "_")) + width
    )
    last_err = ""
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=25) as r:
                ct = r.headers.get("Content-Type", "")
                content = r.read()
            if not ct.startswith("image/") and "svg" not in ct:
                return ("bad-ct", subdir, title)
            if len(content) < 5000:
                return ("tiny", subdir, title)
            tmp = dest + ".tmp"
            with open(tmp, "wb") as f:
                f.write(content)
            os.replace(tmp, dest)
            return ("ok", subdir, title)
        except Exception as e:
            last_err = f"{type(e).__name__}:{e}"
            time.sleep(1.5 + attempt * 2)
    return ("err", subdir, f"{title} :: {last_err}")


def main():
    with open(CATALOG_FILE) as f:
        catalog = json.load(f)
    jobs = []
    for subdir, titles in catalog.items():
        os.makedirs(os.path.join(IMG_ROOT, subdir), exist_ok=True)
        for t in titles:
            if t.startswith(("_from:", "_html:")):
                continue
            jobs.append((subdir, t))
    print(f"jobs: {len(jobs)}", flush=True)
    counts = {"ok": 0, "skip": 0, "err": 0, "tiny": 0, "bad-ct": 0}
    started = time.time()
    err_samples = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = [ex.submit(download, j) for j in jobs]
        for i, fut in enumerate(as_completed(futures)):
            try:
                status, sub, title = fut.result(timeout=60)
            except Exception:
                counts["err"] += 1
                continue
            counts[status] = counts.get(status, 0) + 1
            if status == "err" and len(err_samples) < 5:
                err_samples.append(title)
            if (i + 1) % 100 == 0:
                el = time.time() - started
                print(f"  progress {i+1}/{len(jobs)} ({el:.0f}s) {counts}", flush=True)
    print(f"DONE {counts} in {time.time()-started:.0f}s", flush=True)
    for s in err_samples:
        print("  ERR:", s, flush=True)


if __name__ == "__main__":
    main()
