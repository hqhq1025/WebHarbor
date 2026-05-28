#!/usr/bin/env python3
"""extract_animations.py — Feature P: animation/motion asset dimension.

Catalogs animated assets that often aren't captured by static image extractors:
  - <img src="*.gif">
  - <video autoplay loop> hero motion loops
  - lottie player JSON URLs (script[type=application/json]/.lottie/.json with lottie magic)
  - css background-image: url(*.gif|*.webp|*.svg) (animated SVG)
  - apng / animated webp hints
  - CSS keyframes animation refs (linked sheets - just list css files mentioning @keyframes)

Goal: prove animation dimension exists.

Output: snapshots/<site>/_animations.jsonl

Usage:
  python3 extract_animations.py <site>
  python3 extract_animations.py --all
"""
import argparse
import json
import re
import urllib.parse
from pathlib import Path

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()

ANIM_EXTS = (".gif", ".apng", ".webp", ".lottie")  # webp may be still or anim
# R02 coursera fix: NOT all webp are animated. Be conservative — img webp by
# default = static; only mark anim if filename hints (animated/loop/anim) or
# served from a CDN known for anim sequences. Plain *.webp is treated as image.
WEBP_ANIM_HINTS = ("animated", "loop", "anim", "motion", "cinemagraph")
IMG_GIF_RE = re.compile(r'<img\b[^>]*?src\s*=\s*["\']([^"\']+?\.(?:gif|apng))', re.IGNORECASE)
IMG_WEBP_RE = re.compile(r'<img\b[^>]*?src\s*=\s*["\']([^"\']+?\.webp)', re.IGNORECASE)
VIDEO_LOOP_RE = re.compile(
    r'<video\b[^>]*?(?:autoplay|loop)[^>]*>(.*?)</video>',
    re.IGNORECASE | re.DOTALL,
)
SOURCE_SRC_RE = re.compile(r'<source\b[^>]*?src\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
LOTTIE_REF_RE = re.compile(
    r'(?:data-(?:src|lottie)|src)\s*=\s*["\']([^"\']+?\.(?:json|lottie))(?:["\'])',
    re.IGNORECASE,
)
LOTTIE_PLAYER_RE = re.compile(r'<(?:lottie-player|dotlottie-player|lord-icon)\b([^>]*?)>', re.IGNORECASE)
CSS_URL_RE = re.compile(r'url\((["\']?)([^)"\']+?\.(?:gif|webp|apng))\1\)', re.IGNORECASE)
ATTR_RE = re.compile(r'(\w[\w-]*)\s*=\s*["\']([^"\']*)["\']', re.IGNORECASE)


def parse_attrs(s: str) -> dict:
    return {m.group(1).lower(): m.group(2) for m in ATTR_RE.finditer(s)}


def normalize(url: str, base: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith(("http://", "https://", "data:")):
        return url
    return urllib.parse.urljoin(base, url)


def extract_page(page_dir: Path, base_url: str = "") -> list[dict]:
    html_path = page_dir / "full.html"
    if not html_path.exists():
        return []
    html = html_path.read_text(encoding="utf-8", errors="ignore")
    base = base_url
    m = re.search(r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)', html, re.IGNORECASE)
    if m:
        base = m.group(1)
    found: dict[str, dict] = {}

    def add(rec: dict):
        key = rec.get("url") or json.dumps(rec, sort_keys=True)
        if key in found:
            return
        found[key] = rec

    # img src gif / apng (always animated)
    for m in IMG_GIF_RE.finditer(html):
        url = normalize(m.group(1), base or base_url)
        ext = url.lower().rsplit(".", 1)[-1][:5]
        add({"page": page_dir.name, "kind": "img", "ext": ext, "url": url[:500]})
    # img src webp — only count if URL hints animation (anti-false-positive)
    for m in IMG_WEBP_RE.finditer(html):
        url = normalize(m.group(1), base or base_url)
        low = url.lower()
        if any(h in low for h in WEBP_ANIM_HINTS):
            add({"page": page_dir.name, "kind": "img", "ext": "webp", "url": url[:500]})

    # video autoplay loop — motion loop hero
    for m in VIDEO_LOOP_RE.finditer(html):
        body = m.group(1)
        for sm in SOURCE_SRC_RE.finditer(body):
            url = normalize(sm.group(1), base or base_url)
            add({"page": page_dir.name, "kind": "video-loop", "ext": "mp4_loop", "url": url[:500]})

    # lottie player refs
    for m in LOTTIE_PLAYER_RE.finditer(html):
        attrs = parse_attrs(m.group(1))
        src = attrs.get("src") or attrs.get("data-src") or attrs.get("path")
        if src:
            url = normalize(src, base or base_url)
            add({"page": page_dir.name, "kind": "lottie-player", "ext": "json", "url": url[:500]})
    for m in LOTTIE_REF_RE.finditer(html):
        url = normalize(m.group(1), base or base_url)
        if "lottie" in url.lower() or "anim" in url.lower():
            add({"page": page_dir.name, "kind": "lottie-ref", "ext": "json", "url": url[:500]})

    # css background-image url(.gif|.webp|.apng) in inline styles
    for m in CSS_URL_RE.finditer(html):
        url = normalize(m.group(2), base or base_url)
        ext = url.lower().rsplit(".", 1)[-1][:5]
        add({"page": page_dir.name, "kind": "css-bg", "ext": ext, "url": url[:500]})

    return list(found.values())


def process_site(site_dir: Path) -> tuple[int, int, dict[str, int]]:
    all_records: list[dict] = []
    pages_scanned = 0
    pages_with = 0
    kind_counts: dict[str, int] = {}
    base_url = f"https://{site_dir.name.replace('_', '.')}/"
    for page_dir in sorted(site_dir.iterdir()):
        if not page_dir.is_dir():
            continue
        pages_scanned += 1
        records = extract_page(page_dir, base_url=base_url)
        if records:
            pages_with += 1
        for r in records:
            kind_counts[r["kind"]] = kind_counts.get(r["kind"], 0) + 1
        all_records.extend(records)
    out = site_dir / "_animations.jsonl"
    with out.open("w") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return pages_scanned, pages_with, kind_counts


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
    print(f"{'site':<30} {'pgs':>5} {'wAn':>5} {'recs':>6}  top kinds")
    print("-" * 80)
    grand = 0
    for site_dir in targets:
        if not site_dir.exists():
            print(f"{site_dir.name:<30}  MISSING")
            continue
        pgs, wa, kinds = process_site(site_dir)
        n = sum(kinds.values())
        grand += n
        kk = " ".join(f"{k}={v}" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1])[:3])
        print(f"{site_dir.name:<30} {pgs:>5} {wa:>5} {n:>6}  {kk}")
    print(f"\nGrand total animation records: {grand}")


if __name__ == "__main__":
    main()
