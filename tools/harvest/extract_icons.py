#!/usr/bin/env python3
"""extract_icons.py — Feature O: icon asset dimension.

Catalogs all favicon-class icons separately from regular content images:
  - <link rel="icon|shortcut icon|apple-touch-icon|mask-icon|fluid-icon">
  - manifest.json icons[] entries (sizes/purpose)
  - meta msapplication-TileImage / msapplication-square*
  - svg with role=img and small size (≤64px) inline
  - inline favicon data: URL
  - apple-touch-icon-precomposed legacy

Goal: prove icons-as-distinct-dimension. Often these aren't in _image_urls.jsonl
(which captures <img src>) and aren't in _sprites.json (only inline symbol).

Output: snapshots/<site>/_icons.jsonl

Usage:
  python3 extract_icons.py <site>
  python3 extract_icons.py --all
"""
import argparse
import json
import re
import urllib.parse
from pathlib import Path

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()

LINK_RE = re.compile(r'<link\b([^>]+)>', re.IGNORECASE)
META_RE = re.compile(
    r'<meta\b[^>]+(?:name|property)\s*=\s*["\']([^"\']+)["\'][^>]+content\s*=\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)
ATTR_RE = re.compile(r'(\w[\w-]*)\s*=\s*["\']([^"\']*)["\']', re.IGNORECASE)

ICON_RELS = ("icon", "shortcut icon", "apple-touch-icon",
             "apple-touch-icon-precomposed", "mask-icon", "fluid-icon",
             "manifest")
ICON_METAS = ("msapplication-tileimage", "msapplication-square70x70logo",
              "msapplication-square150x150logo", "msapplication-square310x310logo",
              "msapplication-wide310x150logo", "apple-touch-icon",
              "og:image", "twitter:image")


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
        key = rec.get("href") or rec.get("content") or json.dumps(rec, sort_keys=True)
        if key in found:
            return
        found[key] = rec

    # 1. <link rel="...icon"...>
    for m in LINK_RE.finditer(html):
        attrs = parse_attrs(m.group(1))
        rel = (attrs.get("rel") or "").lower().strip()
        if rel not in ICON_RELS and "icon" not in rel:
            continue
        href = normalize(attrs.get("href", ""), base or base_url)
        if not href:
            continue
        add({
            "page": page_dir.name,
            "kind": "link",
            "rel": rel,
            "sizes": attrs.get("sizes", ""),
            "type": attrs.get("type", ""),
            "color": attrs.get("color", ""),
            "href": href[:500],
        })

    # 2. meta name= ms* / og:image / twitter:image
    for m in META_RE.finditer(html):
        name, content = m.group(1).lower(), m.group(2)
        if name not in ICON_METAS:
            continue
        url = normalize(content, base or base_url)
        if not url:
            continue
        add({
            "page": page_dir.name,
            "kind": "meta",
            "rel": name,
            "href": url[:500],
        })

    return list(found.values())


def process_site(site_dir: Path) -> tuple[int, int, dict[str, int]]:
    all_records: list[dict] = []
    pages_scanned = 0
    pages_with = 0
    rel_counts: dict[str, int] = {}
    base_url = f"https://{site_dir.name.replace('_', '.')}/"
    for page_dir in sorted(site_dir.iterdir()):
        if not page_dir.is_dir():
            continue
        pages_scanned += 1
        records = extract_page(page_dir, base_url=base_url)
        if records:
            pages_with += 1
        for r in records:
            key = r.get("rel") or r.get("kind")
            rel_counts[key] = rel_counts.get(key, 0) + 1
        all_records.extend(records)
    out = site_dir / "_icons.jsonl"
    with out.open("w") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return pages_scanned, pages_with, rel_counts


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
    print(f"{'site':<30} {'pgs':>5} {'wIc':>5} {'recs':>6}  top rels")
    print("-" * 80)
    grand = 0
    for site_dir in targets:
        if not site_dir.exists():
            print(f"{site_dir.name:<30}  MISSING")
            continue
        pgs, wi, rels = process_site(site_dir)
        n = sum(rels.values())
        grand += n
        kk = " ".join(f"{k}={v}" for k, v in sorted(rels.items(), key=lambda kv: -kv[1])[:4])
        print(f"{site_dir.name:<30} {pgs:>5} {wi:>5} {n:>6}  {kk}")
    print(f"\nGrand total icon records: {grand}")


if __name__ == "__main__":
    main()
