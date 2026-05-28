#!/usr/bin/env python3
"""extract_image_urls.py — bridge from harvest-real-components → scrape-real-images.

Walks snapshots/<site>/<page>/full.html and pulls every <img src>, <source srcset>,
and CSS background-image URL out into snapshots/<site>/_image_urls.jsonl, one line
per image with context:

  {"page": "home", "url": "https://...", "alt": "Tony Stark",
   "context": "card-data-testid-card-0", "size_hint": null}

scrape-real-images can then iterate this manifest, pick out images for each entity
(by alt text or URL pattern), and download them with proper Referer.

Usage:
  python3 extract_image_urls.py <site>          # one site
  python3 extract_image_urls.py --all           # every site under snapshots/
"""
import argparse
import json
import re
import sys
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()

# img: <img src> + <img srcset>
IMG_RE = re.compile(r'<img\b([^>]*)>', re.IGNORECASE | re.DOTALL)
SRC_RE = re.compile(r'\bsrc=["\']([^"\']+)["\']', re.IGNORECASE)
SRCSET_RE = re.compile(r'\bsrcset=["\']([^"\']+)["\']', re.IGNORECASE)
ALT_RE = re.compile(r'\balt=["\']([^"\']+)["\']', re.IGNORECASE)
# <source srcset> inside <picture>
SOURCE_SRCSET_RE = re.compile(r'<source\b[^>]*\bsrcset=["\']([^"\']+)["\']', re.IGNORECASE)
# CSS background-image
BG_RE = re.compile(r'background-image\s*:\s*url\(["\']?([^"\')]+)["\']?\)', re.IGNORECASE)


def extract_from_html(html: str, base_url: str):
    """Yield (url, alt, kind) tuples."""
    # <img>
    for m in IMG_RE.finditer(html):
        attrs = m.group(1)
        alt_m = ALT_RE.search(attrs)
        alt = alt_m.group(1) if alt_m else ""
        src_m = SRC_RE.search(attrs)
        if src_m:
            url = urljoin(base_url, src_m.group(1))
            if not url.startswith(("data:", "javascript:")):
                yield url, alt, "img-src"
        srcset_m = SRCSET_RE.search(attrs)
        if srcset_m:
            for part in srcset_m.group(1).split(","):
                u = part.strip().split(" ", 1)[0]
                if u and not u.startswith("data:"):
                    yield urljoin(base_url, u), alt, "img-srcset"
    # <source>
    for m in SOURCE_SRCSET_RE.finditer(html):
        for part in m.group(1).split(","):
            u = part.strip().split(" ", 1)[0]
            if u and not u.startswith("data:"):
                yield urljoin(base_url, u), "", "source-srcset"
    # CSS bg
    for m in BG_RE.finditer(html):
        u = m.group(1)
        if not u.startswith("data:"):
            yield urljoin(base_url, u), "", "css-bg"


def is_real_image(url: str) -> bool:
    """Skip 1px trackers / pixel.gif / etc."""
    low = url.lower()
    if "1x1" in low or "pixel.gif" in low or "tracking" in low or "/spacer" in low:
        return False
    return True


def index_one(site_dir: Path):
    rows = []
    seen = set()  # de-dup URLs across pages
    for page_dir in sorted(p for p in site_dir.iterdir() if p.is_dir()):
        md_path = page_dir / "metadata.json"
        if not md_path.exists():
            continue
        try:
            md = json.loads(md_path.read_text())
        except Exception:
            continue
        base_url = md.get("url", "")
        full_html_path = page_dir / "full.html"
        if not full_html_path.exists():
            continue
        try:
            html = full_html_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for url, alt, kind in extract_from_html(html, base_url):
            if url in seen:
                continue
            if not is_real_image(url):
                continue
            seen.add(url)
            rows.append({
                "page": page_dir.name,
                "url": url,
                "alt": alt.strip(),
                "kind": kind,
                "from_full_html": full_html_path.name,
            })
    out_path = site_dir / "_image_urls.jsonl"
    with out_path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows), out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site", nargs="?")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    if args.all:
        sites = sorted(p for p in ROOT.iterdir() if p.is_dir())
    elif args.site:
        sites = [ROOT / args.site]
    else:
        print("Usage: extract_image_urls.py <site> | --all", file=sys.stderr)
        return 1

    for site_dir in sites:
        if not site_dir.exists():
            print(f"[skip] {site_dir.name}")
            continue
        n, out = index_one(site_dir)
        print(f"{site_dir.name}: {n} distinct image URLs → {out}")


if __name__ == "__main__":
    sys.exit(main() or 0)
