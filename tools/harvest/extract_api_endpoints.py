#!/usr/bin/env python3
"""extract_api_endpoints.py — Feature R: XHR/fetch API endpoint catalog.

Aggregates snapshots/<site>/<page>/xhr_calls.jsonl across all pages and:
  - dedups by (method, base URL)
  - classifies: app_internal (same host as page) / 3rd_party / beacon (analytics)
  - keeps a sample of post_data_first_200 per (method, base) for schema hints

Triggered by R02 eventbrite finding: SPA sites bury entity data in 28+ XHR
base endpoints (api/search, api/nearby_cities, api/v3/promoted/events). Same
pattern on craigslist (/jsonsearch), compass (/api/v3), coursera (/api/v1).

Output: snapshots/<site>/_api_endpoints.jsonl + _api_endpoints_index.json

Usage:
  python3 extract_api_endpoints.py <site>
  python3 extract_api_endpoints.py --all
"""
import argparse
import json
import re
import urllib.parse
from collections import defaultdict
from pathlib import Path

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()

BEACON_HOSTS = (
    "google-analytics", "googletagmanager", "doubleclick", "facebook.net",
    "facebook.com/tr", "fbevents", "googleadservices", "bing.com/action",
    "scorecardresearch", "nielsen", "krxd.net", "tealiumiq", "segment.io",
    "amplitude.com", "mixpanel.com", "branch.io", "newrelic.com",
    "optimizely.com", "adservice.google", "linkedin.com/li.lms",
    "bat.bing", "cookielaw", "onetrust", "criteo", "rubiconproject",
    "outbrain.com", "taboola.com", "datadoghq.com", "sentry.io",
)


def is_beacon(host: str) -> bool:
    h = host.lower()
    return any(b in h for b in BEACON_HOSTS)


# Slug → real host map for known multi-segment slugs (where simple
# underscore→dot replacement gets the wrong eTLD+1).
SLUG_HOST_MAP = {
    "google_com_search":  "google.com",
    "google_com_flights": "google.com",
    "google_com_maps":    "google.com",
    "dictionary_cambridge_org": "cambridge.org",  # dictionary is subdomain
    "hacker_news": "ycombinator.com",
    "bbc_com": "bbc.com",
    "bbc_co_uk": "bbc.co.uk",
}


def slug_to_host(slug: str) -> str:
    if slug in SLUG_HOST_MAP:
        return SLUG_HOST_MAP[slug]
    return slug.replace("_", ".")


# R03 google fix: classify by eTLD+1 (publicsuffix-style) so google.com vs
# clients6.google.com counts as same_org instead of 3rd_party.
# Small whitelist of multi-part TLDs that matter for our 96 sites.
MULTI_TLDS = {
    "co.uk", "ac.uk", "gov.uk", "com.au", "co.jp", "co.kr", "com.br",
    "com.cn", "com.hk", "com.tw", "co.nz", "co.in", "or.jp", "ne.jp",
}


def etld1(host: str) -> str:
    """Crude eTLD+1: takes last 2 segments, unless last 2 match a known multi-TLD."""
    h = (host or "").lower().strip(".")
    parts = h.split(".")
    if len(parts) < 2:
        return h
    last2 = ".".join(parts[-2:])
    if len(parts) >= 3 and last2 in MULTI_TLDS:
        return ".".join(parts[-3:])
    return last2


def url_base(url: str) -> str:
    """Strip query + last numeric/uuid path segment for grouping."""
    p = urllib.parse.urlparse(url)
    path = p.path
    # collapse numeric IDs and UUIDs in path
    path = re.sub(r'/\d+(?=/|$)', '/{n}', path)
    path = re.sub(r'/[0-9a-f]{8,}(?=/|$)', '/{id}', path)
    return f"{p.scheme}://{p.netloc}{path}"


def process_site(site_dir: Path) -> dict:
    site_host = slug_to_host(site_dir.name)
    grouped: dict = defaultdict(lambda: {"count": 0, "pages": set(), "sample_post": None, "resource_types": set()})
    total = 0
    pages_scanned = 0
    pages_with_xhr = 0
    for page_dir in sorted(site_dir.iterdir()):
        if not page_dir.is_dir() or page_dir.name.startswith('_'):
            continue
        pages_scanned += 1
        xhr_path = page_dir / "xhr_calls.jsonl"
        if not xhr_path.exists():
            continue
        page_had_one = False
        with xhr_path.open() as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                url = rec.get("url") or ""
                method = (rec.get("method") or "GET").upper()
                if not url.startswith(("http://", "https://")):
                    continue
                page_had_one = True
                total += 1
                base = url_base(url)
                key = f"{method} {base}"
                g = grouped[key]
                g["count"] += 1
                g["pages"].add(page_dir.name)
                g["resource_types"].add(rec.get("resource_type") or "")
                if not g["sample_post"] and rec.get("post_data_first_200"):
                    g["sample_post"] = rec["post_data_first_200"][:200]
        if page_had_one:
            pages_with_xhr += 1

    records = []
    counts = {"app_internal": 0, "same_org": 0, "3rd_party": 0, "beacon": 0}
    site_etld1 = etld1(site_host)
    for key, g in sorted(grouped.items(), key=lambda kv: -kv[1]["count"]):
        method, base = key.split(" ", 1)
        host = urllib.parse.urlparse(base).hostname or ""
        host_etld1 = etld1(host)
        if is_beacon(host):
            cls = "beacon"
        elif host == site_host or host.endswith("." + site_host.lstrip("www.")):
            cls = "app_internal"
        elif host_etld1 == site_etld1 and site_etld1:
            # R03 fix: google.com vs clients6.google.com → same_org
            cls = "same_org"
        else:
            cls = "3rd_party"
        counts[cls] += 1
        records.append({
            "method": method,
            "base": base,
            "host": host,
            "host_etld1": host_etld1,
            "class": cls,
            "call_count": g["count"],
            "page_count": len(g["pages"]),
            "pages": sorted(g["pages"])[:5],
            "resource_types": sorted([r for r in g["resource_types"] if r]),
            "sample_post_first_200": g["sample_post"],
        })

    out = site_dir / "_api_endpoints.jsonl"
    with out.open("w") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    index = {
        "pages_scanned": pages_scanned,
        "pages_with_xhr": pages_with_xhr,
        "total_calls": total,
        "unique_endpoints": len(records),
        "counts": counts,
    }
    (site_dir / "_api_endpoints_index.json").write_text(json.dumps(index, indent=2))
    return index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site", nargs="?")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    if args.all:
        targets = [d for d in sorted(ROOT.iterdir()) if d.is_dir()]
    elif args.site:
        targets = [ROOT / args.site]
    else:
        ap.error("provide <site> or --all")
        return
    print(f"{'site':<30} {'pgs':>4} {'wXhr':>4} {'calls':>6} {'uniq':>5} {'app':>4} {'org':>4} {'3rd':>4} {'beac':>4}")
    print("-" * 85)
    grand = 0
    for site_dir in targets:
        if not site_dir.exists():
            print(f"{site_dir.name:<30}  MISSING"); continue
        idx = process_site(site_dir)
        c = idx['counts']
        grand += idx['total_calls']
        print(f"{site_dir.name:<30} {idx['pages_scanned']:>4} {idx['pages_with_xhr']:>4} "
              f"{idx['total_calls']:>6} {idx['unique_endpoints']:>5} "
              f"{c.get('app_internal', 0):>4} {c.get('same_org', 0):>4} "
              f"{c.get('3rd_party', 0):>4} {c.get('beacon', 0):>4}")
    print(f"\nGrand total XHR calls: {grand}")


if __name__ == "__main__":
    main()
