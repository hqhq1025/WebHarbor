#!/usr/bin/env python3
"""extract_sitemap.py — Feature A: harvest robots.txt + sitemap.xml(.gz) tree.

Fetches robots.txt for a site, finds Sitemap: directives, recursively fetches
each sitemap (handles .gz), extracts all <loc> URLs, categorizes by URL shape,
and dumps into the site's snapshot dir.

Outputs in snapshots/<site>/:
  _robots.txt
  _sitemap_index.json   — {sitemaps_found, urls_total, by_category}
  _sitemap_urls.jsonl   — one URL per line, with category guess

Usage:
  python3 extract_sitemap.py <site> <base_url>
  python3 extract_sitemap.py --all
"""
import argparse
import gzip
import io
import json
import re
import subprocess
import sys
import urllib.parse
from collections import Counter
from pathlib import Path

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Built-in site->base-url table for batch run. Slug = snapshot dir name.
SITE_BASE = {
    "airbnb_com": "https://www.airbnb.com",
    "akc_org": "https://www.akc.org",
    "allrecipes_com": "https://www.allrecipes.com",
    "amazon_com": "https://www.amazon.com",
    "amtrak_com": "https://www.amtrak.com",
    "apartments_com": "https://www.apartments.com",
    "apple_com": "https://www.apple.com",
    "arxiv_org": "https://arxiv.org",
    "bandcamp_com": "https://bandcamp.com",
    "bbc_com": "https://www.bbc.com",
    "behance_net": "https://www.behance.net",
    "berkeley_edu": "https://www.berkeley.edu",
    "bestbuy_com": "https://www.bestbuy.com",
    "bhphotovideo_com": "https://www.bhphotovideo.com",
    "boardgamegeek_com": "https://boardgamegeek.com",
    "booking_com": "https://www.booking.com",
    "carmax_com": "https://www.carmax.com",
    "carnival_com": "https://www.carnival.com",
    "cars_com": "https://www.cars.com",
    "chess_com": "https://www.chess.com",
    "compass_com": "https://www.compass.com",
    "costco_com": "https://www.costco.com",
    "coursera_org": "https://www.coursera.org",
    "craigslist_org": "https://www.craigslist.org",
    "dictionary_cambridge_org": "https://dictionary.cambridge.org",
    "discogs_com": "https://www.discogs.com",
    "doordash_com": "https://www.doordash.com",
    "dribbble_com": "https://dribbble.com",
    "drugs_com": "https://www.drugs.com",
    "ebay_com": "https://www.ebay.com",
    "espn_com": "https://www.espn.com",
    "etsy_com": "https://www.etsy.com",
    "eventbrite_com": "https://www.eventbrite.com",
    "expedia_com": "https://www.expedia.com",
    "fandom_com": "https://www.fandom.com",
    "flickr_com": "https://www.flickr.com",
    "github_com": "https://github.com",
    "google_com_flights": "https://www.google.com/travel/flights",
    "google_com_maps": "https://www.google.com/maps",
    "google_com_search": "https://www.google.com",
    "hacker_news": "https://news.ycombinator.com",
    "healthline_com": "https://www.healthline.com",
    "huggingface_co": "https://huggingface.co",
    "hulu_com": "https://www.hulu.com",
    "ign_com": "https://www.ign.com",
    "ikea_com": "https://www.ikea.com",
    "imdb_com": "https://www.imdb.com",
    "imgur_com": "https://imgur.com",
    "irs_gov": "https://www.irs.gov",
    "kayak_com": "https://www.kayak.com",
    "landwatch_com": "https://www.landwatch.com",
    "marriott_com": "https://www.marriott.com",
    "mayoclinic_org": "https://www.mayoclinic.org",
    "mdn": "https://developer.mozilla.org",
    "mega_io": "https://mega.io",
    "microcenter_com": "https://www.microcenter.com",
    "nba_com": "https://www.nba.com",
    "netflix_com": "https://www.netflix.com",
    "newegg_com": "https://www.newegg.com",
    "nike_com": "https://www.nike.com",
    "nytimes_com": "https://www.nytimes.com",
    "osu_edu": "https://www.osu.edu",
    "pexels_com": "https://www.pexels.com",
    "phet_colorado_edu": "https://phet.colorado.edu",
    "phys_org": "https://phys.org",
    "pinterest_com": "https://www.pinterest.com",
    "realtor_com": "https://www.realtor.com",
    "recreation_gov": "https://www.recreation.gov",
    "reddit_com": "https://www.reddit.com",
    "redfin_com": "https://www.redfin.com",
    "remax_com": "https://www.remax.com",
    "rottentomatoes_com": "https://www.rottentomatoes.com",
    "sephora_com": "https://www.sephora.com",
    "smartasset_com": "https://smartasset.com",
    "soundcloud_com": "https://soundcloud.com",
    "spotify_com": "https://open.spotify.com",
    "target_com": "https://www.target.com",
    "techcrunch_com": "https://techcrunch.com",
    "ted_com": "https://www.ted.com",
    "theverge_com": "https://www.theverge.com",
    "ticketmaster_com": "https://www.ticketmaster.com",
    "trip_com": "https://www.trip.com",
    "tripadvisor_com": "https://www.tripadvisor.com",
    "twitch_tv": "https://www.twitch.tv",
    "united_com": "https://www.united.com",
    "unsplash_com": "https://unsplash.com",
    "usps_com": "https://www.usps.com",
    "versus_com": "https://versus.com",
    "vimeo_com": "https://vimeo.com",
    "wayfair_com": "https://www.wayfair.com",
    "webmd_com": "https://www.webmd.com",
    "wikipedia_org": "https://en.wikipedia.org",
    "wolframalpha_com": "https://www.wolframalpha.com",
    "yelp_com": "https://www.yelp.com",
    "youtube_com": "https://www.youtube.com",
    "zillow_com": "https://www.zillow.com",
}

CATEGORY_RULES = [
    ("product", re.compile(r"/(?:dp|gp/product|p|product|products|item|itm)/", re.I)),
    ("movie",   re.compile(r"/title/tt\d|/movie/|/movies/|/film/", re.I)),
    ("tv",      re.compile(r"/tv/|/series/|/show/|/episode/", re.I)),
    ("article", re.compile(r"/(?:news|article|articles|story|stories|blog|posts?)/", re.I)),
    ("category",re.compile(r"/(?:category|categories|c|browse|department|departments|topic|topics|section)/", re.I)),
    ("search",  re.compile(r"/(?:search|find|s/|results?)\b", re.I)),
    ("user",    re.compile(r"/(?:user|users|u|profile|profiles|member|members|author|authors|@[\w-])/", re.I)),
    ("wiki",    re.compile(r"/wiki/|/wikipedia/", re.I)),
    ("music",   re.compile(r"/(?:release|releases|master|masters|artist|artists|album|albums|track|label)/", re.I)),
    ("hf",      re.compile(r"/(?:models|datasets|spaces|papers)/", re.I)),
    ("recipe",  re.compile(r"/(?:recipe|recipes)/", re.I)),
    ("course",  re.compile(r"/(?:course|courses|specializations?|learn|learning|tutorial)/", re.I)),
    ("repo",    re.compile(r"github\.com/[^/]+/[^/]+/?$", re.I)),
    ("event",   re.compile(r"/(?:event|events|e/)\b", re.I)),
    ("game",    re.compile(r"/(?:game|games|boardgame|boardgames)/", re.I)),
    ("listing", re.compile(r"/(?:listing|listings|homes?|properties|apartments?|cars?)/", re.I)),
    ("video",   re.compile(r"/(?:video|videos|watch|v/)\b", re.I)),
    ("help",    re.compile(r"/(?:help|support|faq|docs?|documentation)/", re.I)),
    ("auth",    re.compile(r"/(?:login|signin|sign-in|register|signup|sign-up|account|accounts)/", re.I)),
    ("legal",   re.compile(r"/(?:privacy|terms|legal|policy|policies|cookie)\b", re.I)),
    ("about",   re.compile(r"/(?:about|company|contact|press|careers?)\b", re.I)),
]


def categorize(url: str) -> str:
    path = urllib.parse.urlparse(url).path
    full = url
    for label, rx in CATEGORY_RULES:
        if rx.search(full):
            return label
    if path in ("", "/"):
        return "home"
    if path.endswith((".jpg", ".png", ".webp", ".gif", ".svg", ".pdf")):
        return "asset"
    return "other"


def curl_bytes(url: str, ua: str, timeout: int = 20,
               max_size: int = 30_000_000) -> tuple[bytes | None, int]:
    """Fetch URL. Returns (body, http_code). body is None on transport error or
    HTTP >= 400. http_code is 0 if no response was received."""
    try:
        r = subprocess.run(
            ["curl", "-sSL", "-A", ua,
             "-H", "Accept: application/xml,text/xml,text/plain,*/*",
             "-H", "Accept-Language: en-US,en;q=0.9",
             "--max-time", str(timeout),
             "--max-filesize", str(max_size),
             "-w", "\n__HTTP_CODE__%{http_code}",
             url],
            capture_output=True, timeout=timeout + 5,
        )
        out = r.stdout or b""
        marker = b"\n__HTTP_CODE__"
        code = 0
        if marker in out:
            body, _, tail = out.rpartition(marker)
            try:
                code = int(tail.strip() or 0)
            except ValueError:
                code = 0
            out = body
        if r.returncode != 0 and code == 0:
            return None, 0
        if code >= 400:
            return None, code
        # R03 espn/imdb fix: reject 202/204 (queued/no-content) and empty body.
        # extract_sitemap should not count these as valid sitemaps.
        if code in (202, 204):
            return None, code
        if not out or len(out.strip()) < 32:
            return None, code
        return (out or None), code
    except Exception:
        return None, 0


def maybe_gunzip(data: bytes, url: str) -> bytes:
    if url.endswith(".gz") or data[:2] == b"\x1f\x8b":
        try:
            return gzip.decompress(data)
        except Exception:
            return data
    return data


SITEMAP_LOC_RE = re.compile(rb"<loc>\s*([^<]+?)\s*</loc>", re.IGNORECASE)
SITEMAP_TAG_RE = re.compile(rb"<sitemap[\s>]", re.IGNORECASE)


def parse_sitemap(data: bytes) -> tuple[list[str], list[str]]:
    """Return (child_sitemap_urls, page_urls). Regex-based — tolerant of malformed XML."""
    sitemaps, pages = [], []
    is_index = bool(SITEMAP_TAG_RE.search(data[:4000]))
    for m in SITEMAP_LOC_RE.finditer(data):
        url = m.group(1).decode("utf-8", errors="ignore").strip()
        if not url or not url.startswith(("http://", "https://")):
            continue
        if is_index and url.endswith((".xml", ".xml.gz", ".gz")):
            sitemaps.append(url)
        else:
            pages.append(url)
    # Heuristic fallback: if we found nothing matching index pattern, treat
    # every .xml/.gz loc as a sub-sitemap.
    if not pages and not sitemaps:
        for m in SITEMAP_LOC_RE.finditer(data):
            url = m.group(1).decode("utf-8", errors="ignore").strip()
            if url.endswith((".xml", ".xml.gz", ".gz")):
                sitemaps.append(url)
            elif url.startswith(("http://", "https://")):
                pages.append(url)
    return sitemaps, pages


def parse_robots(text: str, base_url: str) -> list[str]:
    sitemaps = []
    for line in text.splitlines():
        line = line.strip()
        if line.lower().startswith("sitemap:"):
            url = line.split(":", 1)[1].strip()
            url = urllib.parse.urljoin(base_url, url)
            if url:
                sitemaps.append(url)
    return sitemaps


def run_site(site: str, base_url: str, ua: str = DEFAULT_UA,
             max_sub_sitemaps: int = 200, max_urls: int = 20_000):
    out_dir = ROOT / site
    out_dir.mkdir(parents=True, exist_ok=True)

    robots_url = urllib.parse.urljoin(base_url, "/robots.txt")
    robots_bytes, robots_code = curl_bytes(robots_url, ua, timeout=12)
    robots_text = (robots_bytes or b"").decode("utf-8", errors="ignore")
    (out_dir / "_robots.txt").write_text(robots_text, encoding="utf-8")

    sitemaps_in_robots = parse_robots(robots_text, base_url) if robots_text else []

    # Always probe common defaults too — robots-listed sitemaps frequently 404
    # (e.g. github.com/sitemap.xml.gz, arxiv.org/sitemap.xml.gz), and some sites
    # don't advertise their sitemap in robots.txt at all.
    default_candidates = [
        urllib.parse.urljoin(base_url, p) for p in
        ("/sitemap.xml", "/sitemap_index.xml", "/sitemap.xml.gz",
         "/sitemap-index.xml", "/wp-sitemap.xml")
    ]
    seed_sitemaps = list(sitemaps_in_robots)
    for cand in default_candidates:
        if cand not in seed_sitemaps:
            seed_sitemaps.append(cand)

    seen_sitemaps: set[str] = set()
    sitemap_fetch_status: dict[str, int] = {}   # url -> http_code (0 on transport err)
    page_urls: list[tuple[str, str]] = []  # (url, source_sitemap)
    queue = list(seed_sitemaps)
    sub_count = 0  # attempted
    sub_valid = 0  # ok + had urls or sub-indexes

    while queue and sub_count < max_sub_sitemaps and len(page_urls) < max_urls:
        sm_url = queue.pop(0)
        if sm_url in seen_sitemaps:
            continue
        seen_sitemaps.add(sm_url)
        sub_count += 1
        data, code = curl_bytes(sm_url, ua, timeout=20)
        sitemap_fetch_status[sm_url] = code
        if not data:
            continue
        data = maybe_gunzip(data, sm_url)
        # R07 fix: reject HTML masquerading as sitemap (bandcamp/phet/wolfram/imgur
        # all have /sitemap.xml returning HTML 200). Sitemap MUST contain either
        # <urlset> or <sitemapindex>.
        head = data[:4096].lower()
        if b"<urlset" not in head and b"<sitemapindex" not in head:
            sitemap_fetch_status[sm_url] = -1  # mark as 'not-a-sitemap'
            continue
        sub_valid += 1
        children, pages = parse_sitemap(data)
        for child in children:
            if child not in seen_sitemaps and len(queue) + sub_count < max_sub_sitemaps + 5:
                queue.append(child)
        for u in pages:
            page_urls.append((u, sm_url))
            if len(page_urls) >= max_urls:
                break

    # Dedup pages, preserve order
    seen_pages: set[str] = set()
    deduped: list[tuple[str, str]] = []
    for u, src in page_urls:
        if u in seen_pages:
            continue
        seen_pages.add(u)
        deduped.append((u, src))

    by_category: Counter = Counter()
    with (out_dir / "_sitemap_urls.jsonl").open("w") as f:
        for u, src in deduped:
            cat = categorize(u)
            by_category[cat] += 1
            f.write(json.dumps({"url": u, "category": cat, "from": src},
                                ensure_ascii=False) + "\n")

    index = {
        "site": site,
        "base_url": base_url,
        "robots_url": robots_url,
        "robots_http_code": robots_code,
        "robots_sitemaps": sitemaps_in_robots,
        "default_candidates_tried": [c for c in default_candidates
                                     if c not in sitemaps_in_robots],
        "sitemaps_found": sorted(seen_sitemaps),
        "sitemap_http_codes": sitemap_fetch_status,
        "sub_sitemaps_fetched": sub_count,
        "sub_sitemaps_valid": sub_valid,  # R07: only counts those containing <urlset>/<sitemapindex>
        "urls_total": len(deduped),
        "by_category": dict(by_category.most_common()),
        "capped_sub_sitemaps": sub_count >= max_sub_sitemaps,
        "capped_urls": len(deduped) >= max_urls,
    }
    (out_dir / "_sitemap_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site", nargs="?")
    ap.add_argument("base_url", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--ua", default=DEFAULT_UA)
    ap.add_argument("--max-sub-sitemaps", type=int, default=200,
                    help="walk up to N sub-sitemaps (R01 bug fix: booking nests 275 indexes)")
    ap.add_argument("--max-urls", type=int, default=20_000)
    args = ap.parse_args()

    if args.all:
        targets = list(SITE_BASE.items())
    elif args.site and args.base_url:
        targets = [(args.site, args.base_url)]
    elif args.site and args.site in SITE_BASE:
        targets = [(args.site, SITE_BASE[args.site])]
    else:
        ap.error("provide <site> <base_url>, or --all, or a known site slug")

    print(f"{'site':<28} {'sm':>4} {'urls':>6}  top categories")
    print("-" * 80)
    for site, base in targets:
        try:
            idx = run_site(site, base, ua=args.ua,
                            max_sub_sitemaps=args.max_sub_sitemaps,
                            max_urls=args.max_urls)
        except Exception as e:
            print(f"{site:<28}  ERROR  {e}")
            continue
        top = ", ".join(f"{k}={v}" for k, v in list(idx["by_category"].items())[:5])
        print(f"{site:<28} {idx['sub_sitemaps_fetched']:>4} {idx['urls_total']:>6}  {top}")


if __name__ == "__main__":
    main()
