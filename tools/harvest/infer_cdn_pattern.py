#!/usr/bin/env python3
"""infer_cdn_pattern.py — infer CDN URL templates from a list of real URLs.

Given a bunch of URLs scraped from one site (e.g., all the i.etsystatic.com
URLs we found in snapshots), tokenize them and find a template via longest-
common-subsequence-style analysis.

Usage:
  python3 infer_cdn_pattern.py <site>      # infer from snapshots/<site>/_image_urls.jsonl
  python3 infer_cdn_pattern.py --cdn <cdn_host>   # infer from any pool URL matching CDN
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()


def tokenize_path(url):
    """Split URL path into placeholder-friendly tokens.
    Replace hex hashes / digits / opaque strings with placeholders."""
    parsed = re.match(r'https?://([^/]+)(.*)', url)
    if not parsed:
        return None, []
    host, path = parsed.groups()
    # Split on / and split off query
    if "?" in path:
        path, _ = path.split("?", 1)
    parts = [p for p in path.split("/") if p]
    return host, parts


def classify_token(tok):
    """Return canonical placeholder name for a token."""
    if re.fullmatch(r'[0-9a-f]{32,}', tok):
        return "{hash32}"
    if re.fullmatch(r'[0-9a-f]{16,32}', tok):
        return "{hash}"
    if re.fullmatch(r'[0-9a-f]{8,16}', tok):
        return "{short_hash}"
    if re.fullmatch(r'\d{6,}', tok):
        return "{id}"
    if re.fullmatch(r'\d+x\d+', tok):
        return "{WxH}"
    if re.fullmatch(r'\d+', tok):
        return "{n}"
    if re.fullmatch(r'\d+px', tok):
        return "{px}"
    if re.fullmatch(r'[a-z]+_[a-z]+', tok.lower()):
        return tok  # keep readable
    if re.search(r'\.(jpg|jpeg|png|webp|gif|svg)$', tok, re.IGNORECASE):
        m = re.match(r'(.*?)\.(jpg|jpeg|png|webp|gif|svg)$', tok, re.IGNORECASE)
        base = m.group(1)
        ext = m.group(2).lower()
        if re.fullmatch(r'[0-9a-f]+', base):
            return "{hash}.{ext}".replace("{ext}", ext)
        return "{name}." + ext
    return tok  # literal


def infer_template(urls, max_examples=200):
    """Infer template from a list of same-CDN URLs.
    Returns (template_str, n_used, n_total_urls_seen)."""
    if not urls:
        return None, 0, 0
    samples = urls[:max_examples]
    paths = []
    for url in samples:
        host, parts = tokenize_path(url)
        if host:
            paths.append((host, parts))
    if not paths:
        return None, 0, len(urls)

    # Group by depth (number of path segments)
    by_depth = defaultdict(list)
    for h, p in paths:
        by_depth[len(p)].append(p)
    if not by_depth:
        return None, 0, len(urls)
    # Pick the depth with most samples
    most_depth = max(by_depth.keys(), key=lambda d: len(by_depth[d]))
    group = by_depth[most_depth]

    host = paths[0][0]
    # For each position, classify each sample's token, pick most common pattern
    template_parts = []
    for i in range(most_depth):
        classified = [classify_token(p[i]) for p in group]
        c = Counter(classified)
        most_common, count = c.most_common(1)[0]
        # If >70% same literal token, use literal; else placeholder
        if count / len(classified) > 0.7:
            template_parts.append(most_common)
        else:
            # Use most common placeholder (or fallback)
            placeholders = [t for t in classified if t.startswith("{")]
            if placeholders:
                template_parts.append(Counter(placeholders).most_common(1)[0][0])
            else:
                template_parts.append("{var}")
    template = f"https://{host}/" + "/".join(template_parts)
    return template, len(group), len(urls)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site", nargs="?")
    ap.add_argument("--cdn", default=None, help="filter by CDN host")
    ap.add_argument("--top-cdns", type=int, default=5, help="show templates for top N CDNs")
    args = ap.parse_args()

    if not args.site:
        print("Usage: infer_cdn_pattern.py <site>", file=sys.stderr)
        return 1

    urls_file = ROOT / args.site / "_image_urls.jsonl"
    if not urls_file.exists():
        print(f"missing: {urls_file}", file=sys.stderr)
        return 1

    rows = [json.loads(line) for line in urls_file.read_text().splitlines() if line.strip()]
    urls = [r.get("url", "") for r in rows if r.get("url", "").startswith(("http://", "https://"))]

    # Group by CDN host
    by_cdn = defaultdict(list)
    for u in urls:
        host = u.split("/")[2] if "://" in u else ""
        by_cdn[host].append(u)

    if args.cdn:
        cdns = [args.cdn] if args.cdn in by_cdn else []
    else:
        cdns = [h for h, _ in sorted(by_cdn.items(), key=lambda x: -len(x[1]))[:args.top_cdns]]

    print(f"\n=== {args.site} inferred CDN templates ===\n")
    for cdn in cdns:
        urls_cdn = by_cdn[cdn]
        template, used, total = infer_template(urls_cdn)
        if template:
            print(f"[{cdn}]  ({total} URLs, depth={used})")
            print(f"  template: {template}")
            print(f"  examples:")
            for ex in urls_cdn[:2]:
                print(f"    {ex[:120]}")
            print()


if __name__ == "__main__":
    sys.exit(main() or 0)
