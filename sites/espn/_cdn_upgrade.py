"""espn: replace articles.image with real upstream a.espncdn.com photo URLs
mined from /datadrive/harvest/snapshots/espn_com/_image_urls.jsonl (2146 URLs).

Pipeline:
  1. Filter URLs — keep a.espncdn.com /photo/2026/* (article heroes),
     /media/motion/*.jpg (video posters), and stitcher artwork (collection/event
     thumbs).  Drop tracking/doubleclick/zero-byte combiner icons (<50x50).
  2. Download with Mozilla UA + Referer https://www.espn.com/. Reject <8KB.
  3. Save under static/images/cdn_espn/<sha1>.<ext>.
  4. Round-robin assign by md5(article.id) → pool, write to instance/espn.db.
  5. Verify top-image duplicate <5%.
"""
import os, sys, re, json, time, hashlib, socket, sqlite3, collections
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
SNAP = "/datadrive/harvest/snapshots/espn_com/_image_urls.jsonl"
DB   = os.path.join(BASE, "instance", "espn.db")
ROOT = os.path.join(BASE, "static", "images", "cdn_espn")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"
HEADERS = {"User-Agent": UA, "Accept": "image/avif,image/webp,*/*", "Accept-Language": "en-US,en;q=0.9", "Referer": "https://www.espn.com/"}
MIN_BYTES = 8 * 1024
TIMEOUT = 12
PARALLEL = 16
socket.setdefaulttimeout(TIMEOUT)


def classify(u):
    """Return 'photo' / 'motion' / 'stitcher' / None."""
    u = u.replace("&amp;", "&")
    p = urlparse(u)
    host = (p.hostname or "").lower()
    path = p.path
    if "doubleclick" in u or "/securemetrics" in u or "tracking" in u:
        return None
    if not ("espncdn" in host or "espn.com/i/" in u):
        return None
    if path.startswith("/photo/"):
        # /photo/2026/MMDD/r12345_1296x729_16-9.jpg — article hero
        if "1296x729" in path or "576x324" in path:
            return "photo"
        return None
    if path.startswith("/media/motion/") and path.endswith(".jpg"):
        return "motion"
    if "/stitcher/sports/" in path:
        return "stitcher"
    if "/stitcher/artwork/" in path and "16x9" in path:
        return "stitcher"
    return None


def collect_urls():
    out, seen = [], set()
    counts = collections.Counter()
    with open(SNAP) as f:
        for line in f:
            try:
                j = json.loads(line)
            except Exception:
                continue
            u = j.get("url", "").replace("&amp;", "&")
            if not u or u in seen:
                continue
            kind = classify(u)
            if not kind:
                continue
            seen.add(u)
            out.append(u)
            counts[kind] += 1
    print(f"[filter] {dict(counts)} total={len(out)}")
    return out


def safe_ext(u):
    p = urlparse(u).path.lower()
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        if ext in p:
            return ".jpg" if ext == ".jpeg" else ext
    return ".jpg"


def download(url):
    h = hashlib.sha1(url.encode()).hexdigest()[:16]
    ext = safe_ext(url)
    out_path = os.path.join(ROOT, h + ext)
    if os.path.exists(out_path) and os.path.getsize(out_path) >= MIN_BYTES:
        return url, out_path, "cached"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read()
            ct = (resp.headers.get("Content-Type") or "").lower()
        if len(data) < MIN_BYTES:
            return url, None, f"too_small:{len(data)}"
        if not any(x in ct for x in ("image/jpeg", "image/png", "image/webp", "image/gif", "image/avif", "image/jpg")):
            return url, None, f"bad_ct:{ct[:30]}"
        with open(out_path, "wb") as f:
            f.write(data)
        return url, out_path, "ok"
    except Exception as e:
        return url, None, f"err:{type(e).__name__}"


def run_download(urls):
    os.makedirs(ROOT, exist_ok=True)
    print(f"[download] queued: {len(urls)}")
    ok, bad = [], collections.Counter()
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=PARALLEL) as ex:
        futs = [ex.submit(download, u) for u in urls]
        for i, f in enumerate(as_completed(futs)):
            url, path, status = f.result()
            if status in ("ok", "cached") and path:
                ok.append(path)
            else:
                bad[status.split(":")[0]] += 1
            if (i + 1) % 50 == 0:
                print(f"  [{i+1}/{len(urls)}] ok={len(ok)} bad={dict(bad)} t={time.time()-t0:.0f}s")
    print(f"[download] DONE ok={len(ok)} bad={dict(bad)} t={time.time()-t0:.0f}s")
    return ok


def to_static_url(path):
    rel = os.path.relpath(path, os.path.join(BASE, "static"))
    return "/static/" + rel.replace(os.sep, "/")


def assign_round_robin(ids, pool, salt=""):
    n = len(pool)
    out = {}
    for i in ids:
        key = f"{i}{salt}".encode()
        idx = int(hashlib.md5(key).hexdigest(), 16) % n
        out[i] = pool[idx]
    return out


def update_db(paths):
    if not paths:
        print("[db] no images downloaded — abort")
        sys.exit(1)
    pool = sorted({to_static_url(p) for p in paths})
    print(f"[db] pool size: {len(pool)}")

    con = sqlite3.connect(DB)
    cur = con.cursor()
    ids = [r[0] for r in cur.execute("SELECT id FROM articles").fetchall()]
    print(f"[db] articles rows: {len(ids)}")

    img_map = assign_round_robin(ids, pool, salt="")
    cur.executemany(
        "UPDATE articles SET image = ? WHERE id = ?",
        [(img_map[i], i) for i in ids],
    )
    con.commit()

    images = [r[0] for r in cur.execute("SELECT image FROM articles WHERE image IS NOT NULL").fetchall()]
    top = collections.Counter(images).most_common(1)[0]
    pct = top[1] / len(images) * 100
    distinct = len(set(images))
    print(f"[verify] articles.image top {top[1]}/{len(images)} = {pct:.2f}%  distinct={distinct}")
    if pct >= 5.0:
        print("[verify] FAIL: dup >= 5%")
        sys.exit(2)
    con.close()
    print("[verify] PASS")


def main():
    urls = collect_urls()
    paths = run_download(urls)
    update_db(paths)


if __name__ == "__main__":
    main()
