"""apple: replace product.image / product.hero_image with real upstream CDN URLs
mined from /datadrive/harvest/snapshots/apple_com/_image_urls.jsonl (3054 URLs).

Pipeline:
  1. Filter URLs — keep is1-ssl.mzstatic.com (thumbs), www.apple.com/v/ (banners),
     store.storeimages.cdn-apple.com (heroes). Drop securemetrics/tracking/data
     URIs / R0lGOD GIF stubs.
  2. Download with Mozilla UA + Referer https://www.apple.com/.  Reject <8KB.
  3. Save under static/images/cdn_apple/<thumb|hero>/<sha1>.<ext>.
  4. Round-robin assign by md5(product.id) → pool, write to instance/apple_store.db.
  5. Verify top-image duplicate <5%.
"""
import os, sys, re, json, time, hashlib, socket, sqlite3, collections
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
SNAP = "/datadrive/harvest/snapshots/apple_com/_image_urls.jsonl"
DB   = os.path.join(BASE, "instance", "apple_store.db")
ROOT = os.path.join(BASE, "static", "images", "cdn_apple")
THUMB_DIR = os.path.join(ROOT, "thumb")
HERO_DIR  = os.path.join(ROOT, "hero")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"
HEADERS = {"User-Agent": UA, "Accept": "image/avif,image/webp,*/*", "Accept-Language": "en-US,en;q=0.9", "Referer": "https://www.apple.com/"}
MIN_BYTES = 8 * 1024
TIMEOUT = 12
PARALLEL = 16
socket.setdefaulttimeout(TIMEOUT)


THUMB_HOSTS = {"is1-ssl.mzstatic.com"}
HERO_HOSTS  = {"www.apple.com", "store.storeimages.cdn-apple.com", "rtlimages.apple.com", "digitalassets-retail.cdn-apple.com"}
DROP_HOSTS  = {"securemetrics.apple.com"}


def categorize(u):
    """Return 'thumb' / 'hero' / None."""
    u = u.replace("&amp;", "&")
    try:
        p = urlparse(u)
    except Exception:
        return None, u
    host = (p.hostname or "").lower()
    path = p.path
    if host in DROP_HOSTS:
        return None, u
    # drop GIF placeholder data-like URLs and odd shop/mdp params
    if "R0lGOD" in u or "&quot;" in u or path.endswith("/"):
        return None, u
    if host in THUMB_HOSTS and "/image/thumb/" in path:
        return "thumb", u
    if host == "www.apple.com" and (path.startswith("/v/") or path.startswith("/assets-www/")):
        # only real image extensions
        if not re.search(r"\.(jpg|jpeg|png|webp)(?:\?|$)", path, re.I):
            return None, u
        return "hero", u
    if host == "store.storeimages.cdn-apple.com":
        return "hero", u
    if host == "rtlimages.apple.com":
        return "hero", u
    if host == "digitalassets-retail.cdn-apple.com":
        return "hero", u
    return None, u


def collect_urls():
    urls = {"thumb": [], "hero": []}
    seen = set()
    with open(SNAP) as f:
        for line in f:
            try:
                j = json.loads(line)
            except Exception:
                continue
            u = j.get("url", "").replace("&amp;", "&")
            if not u or u in seen:
                continue
            kind, u2 = categorize(u)
            if not kind:
                continue
            seen.add(u)
            urls[kind].append(u)
    return urls


def safe_ext(u):
    p = urlparse(u).path.lower()
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        if ext in p:
            return ".jpg" if ext == ".jpeg" else ext
    return ".jpg"


def download(args):
    kind, url = args
    h = hashlib.sha1(url.encode()).hexdigest()[:16]
    ext = safe_ext(url)
    out_dir = THUMB_DIR if kind == "thumb" else HERO_DIR
    out_path = os.path.join(out_dir, h + ext)
    if os.path.exists(out_path) and os.path.getsize(out_path) >= MIN_BYTES:
        return kind, url, out_path, "cached"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read()
            ct = (resp.headers.get("Content-Type") or "").lower()
        if len(data) < MIN_BYTES:
            return kind, url, None, f"too_small:{len(data)}"
        if not any(x in ct for x in ("image/jpeg", "image/png", "image/webp", "image/gif", "image/avif", "image/jpg")):
            return kind, url, None, f"bad_ct:{ct[:30]}"
        with open(out_path, "wb") as f:
            f.write(data)
        return kind, url, out_path, "ok"
    except Exception as e:
        return kind, url, None, f"err:{type(e).__name__}"


def run_download(url_map):
    os.makedirs(THUMB_DIR, exist_ok=True)
    os.makedirs(HERO_DIR, exist_ok=True)
    tasks = [(k, u) for k, lst in url_map.items() for u in lst]
    print(f"[download] queued: thumb={len(url_map['thumb'])} hero={len(url_map['hero'])} total={len(tasks)}")
    ok, bad = {"thumb": [], "hero": []}, collections.Counter()
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=PARALLEL) as ex:
        futs = [ex.submit(download, t) for t in tasks]
        for i, f in enumerate(as_completed(futs)):
            kind, url, path, status = f.result()
            if status in ("ok", "cached") and path:
                ok[kind].append(path)
            else:
                bad[status.split(":")[0]] += 1
            if (i + 1) % 200 == 0:
                print(f"  [{i+1}/{len(tasks)}] thumb={len(ok['thumb'])} hero={len(ok['hero'])} bad={dict(bad)} t={time.time()-t0:.0f}s")
    print(f"[download] DONE thumb={len(ok['thumb'])} hero={len(ok['hero'])} bad={dict(bad)} t={time.time()-t0:.0f}s")
    return ok


def to_static_url(path):
    rel = os.path.relpath(path, os.path.join(BASE, "static"))
    return "/static/" + rel.replace(os.sep, "/")


def assign_round_robin(ids, pool, salt=""):
    """md5(id+salt) → pool index. Returns dict id→path."""
    n = len(pool)
    out = {}
    for i in ids:
        key = f"{i}{salt}".encode()
        idx = int(hashlib.md5(key).hexdigest(), 16) % n
        out[i] = pool[idx]
    return out


def update_db(ok):
    if not ok["thumb"] or not ok["hero"]:
        print(f"[db] pool too small thumb={len(ok['thumb'])} hero={len(ok['hero'])}")
        sys.exit(1)
    thumb_urls = sorted(to_static_url(p) for p in ok["thumb"])
    hero_urls  = sorted(to_static_url(p) for p in ok["hero"])
    print(f"[db] pool sizes: thumb={len(thumb_urls)} hero={len(hero_urls)}")

    con = sqlite3.connect(DB)
    cur = con.cursor()
    ids = [r[0] for r in cur.execute("SELECT id FROM product").fetchall()]
    print(f"[db] product rows: {len(ids)}")

    img_map  = assign_round_robin(ids, thumb_urls, salt="")
    hero_map = assign_round_robin(ids, hero_urls,  salt="h")

    cur.executemany(
        "UPDATE product SET image = ?, hero_image = ? WHERE id = ?",
        [(img_map[i], hero_map[i], i) for i in ids],
    )
    con.commit()

    # verify
    images = [r[0] for r in cur.execute("SELECT image FROM product").fetchall()]
    heroes = [r[0] for r in cur.execute("SELECT hero_image FROM product").fetchall()]
    c_img = collections.Counter(images).most_common(1)[0]
    c_h   = collections.Counter(heroes).most_common(1)[0]
    pct_img = c_img[1] / len(images) * 100
    pct_h   = c_h[1] / len(heroes) * 100
    print(f"[verify] image top {c_img[1]}/{len(images)} = {pct_img:.2f}%  distinct={len(set(images))}")
    print(f"[verify] hero  top {c_h[1]}/{len(heroes)} = {pct_h:.2f}%  distinct={len(set(heroes))}")
    if pct_img >= 5.0 or pct_h >= 5.0:
        print("[verify] FAIL: dup >= 5%")
        sys.exit(2)
    con.close()
    print("[verify] PASS")


def main():
    url_map = collect_urls()
    print(f"[filter] thumb={len(url_map['thumb'])} hero={len(url_map['hero'])}")
    ok = run_download(url_map)
    update_db(ok)


if __name__ == "__main__":
    main()
