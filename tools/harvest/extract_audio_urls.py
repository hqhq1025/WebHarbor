#!/usr/bin/env python3
"""extract_audio_urls.py — Feature L: audio asset dimension.

Scans snapshots/<site>/<page>/full.html for audio resources missed by
image-only extractors:
  - <audio src="..."> / <audio>...<source src="...">
  - <a href="...mp3|ogg|wav|m4a|aac|flac|opus|webm">
  - <link rel="enclosure" href="...">  (RSS feed enclosures sometimes inline)
  - inline data-src="..." with audio mime hints
  - JSON-LD AudioObject (#sound / #audio / #pronunciation)

R01 trigger: dictionary_cambridge_org per-word page ships .mp3/.ogg pronunciation
audio with no images_real coverage. R02+ likely BBC sounds, NPR, podcast,
linguistic dictionaries all benefit.

Output: snapshots/<site>/_audio_urls.jsonl  (one JSON per audio URL)

Usage:
  python3 extract_audio_urls.py <site>
  python3 extract_audio_urls.py --all
"""
import argparse
import json
import re
import sys
from pathlib import Path
import urllib.parse

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()

AUDIO_EXTS = (".mp3", ".ogg", ".wav", ".m4a", ".aac", ".flac", ".opus")
AUDIO_EXT_RE = re.compile(
    r'\b([\w./:%?=&#~-]+?\.(?:mp3|ogg|wav|m4a|aac|flac|opus))(?:\b|["\'])',
    re.IGNORECASE,
)
AUDIO_TAG_RE = re.compile(r'<audio[^>]*?>(.*?)</audio>', re.IGNORECASE | re.DOTALL)
AUDIO_ATTR_RE = re.compile(r'<audio\b[^>]*?src\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
SOURCE_RE = re.compile(r'<source\b[^>]*?src\s*=\s*["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)
LINK_HREF_RE = re.compile(r'<(?:a|link)\b[^>]*?href\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
JSONLD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def normalize(url: str, base: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith(("http://", "https://", "data:")):
        return url
    return urllib.parse.urljoin(base, url)


def is_audio_url(url: str) -> bool:
    if not url:
        return False
    u = url.lower().split("?", 1)[0].split("#", 1)[0]
    return u.endswith(AUDIO_EXTS)


def extract_jsonld_audio(html: str) -> list[str]:
    out: list[str] = []
    for m in JSONLD_RE.finditer(html):
        blob = m.group(1).strip()
        try:
            data = json.loads(blob)
        except Exception:
            continue
        stack = [data]
        while stack:
            obj = stack.pop()
            if isinstance(obj, list):
                stack.extend(obj)
                continue
            if not isinstance(obj, dict):
                continue
            t = obj.get("@type", "")
            if isinstance(t, list):
                t = " ".join(t)
            if "AudioObject" in str(t) or "PodcastEpisode" in str(t):
                url = obj.get("contentUrl") or obj.get("url")
                if url:
                    out.append(str(url))
            for v in obj.values():
                if isinstance(v, (dict, list)):
                    stack.append(v)
    return out


def extract_page(page_dir: Path, base_url: str = "") -> list[dict]:
    html_path = page_dir / "full.html"
    if not html_path.exists():
        return []
    html = html_path.read_text(encoding="utf-8", errors="ignore")
    # canonical base (og:url > base href > arg base_url)
    base = base_url
    m = re.search(r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)', html, re.IGNORECASE)
    if m:
        base = m.group(1)
    found: dict[str, dict] = {}

    def add(url: str, source: str):
        url = normalize(url, base or base_url)
        if not url or not (url.startswith("http") or url.startswith("data:")):
            return
        if url in found:
            return
        found[url] = {
            "url": url,
            "page": page_dir.name,
            "source": source,
            "ext": (re.search(r'\.([a-z0-9]+)(?:\?|#|$)', url.lower()) or ["", ""])[1] if not url.startswith("data:") else "data",
        }

    for m in AUDIO_ATTR_RE.finditer(html):
        add(m.group(1), "audio[src]")
    for m in SOURCE_RE.finditer(html):
        u = m.group(1)
        # Only include source[src] that looks audio (avoid <video><source>)
        if is_audio_url(u):
            add(u, "audio>source")
    for m in LINK_HREF_RE.finditer(html):
        u = m.group(1)
        if is_audio_url(u):
            add(u, "a/link[href]")
    for m in AUDIO_EXT_RE.finditer(html):
        add(m.group(1), "inline-string")
    for u in extract_jsonld_audio(html):
        add(u, "jsonld:AudioObject")

    return list(found.values())


def process_site(site_dir: Path) -> tuple[int, int, dict[str, int]]:
    all_records: list[dict] = []
    pages_scanned = 0
    pages_with_audio = 0
    ext_counts: dict[str, int] = {}
    # naive base_url guess from slug
    base_url = f"https://{site_dir.name.replace('_', '.')}/"
    for page_dir in sorted(site_dir.iterdir()):
        if not page_dir.is_dir():
            continue
        pages_scanned += 1
        records = extract_page(page_dir, base_url=base_url)
        if records:
            pages_with_audio += 1
        for r in records:
            ext_counts[r["ext"]] = ext_counts.get(r["ext"], 0) + 1
        all_records.extend(records)
    out = site_dir / "_audio_urls.jsonl"
    with out.open("w") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return pages_scanned, pages_with_audio, ext_counts


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
    print(f"{'site':<30} {'pgs':>5} {'wAud':>5} {'urls':>6}  top exts")
    print("-" * 70)
    grand = 0
    for site_dir in targets:
        if not site_dir.exists():
            print(f"{site_dir.name:<30}  MISSING")
            continue
        pgs, wa, exts = process_site(site_dir)
        n = sum(exts.values())
        grand += n
        top = ", ".join(f"{k}={v}" for k, v in sorted(exts.items(), key=lambda kv: -kv[1])[:5])
        print(f"{site_dir.name:<30} {pgs:>5} {wa:>5} {n:>6}  {top}")
    print(f"\nGrand total audio URLs: {grand}")


if __name__ == "__main__":
    main()
