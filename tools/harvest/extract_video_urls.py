#!/usr/bin/env python3
"""extract_video_urls.py — Feature M: video asset dimension.

Catalogs all video resources referenced in snapshots/<site>/<page>/full.html:
  - <video src="..."> / <video><source src="...">
  - <iframe src="youtube.com|youtu.be|vimeo.com|dailymotion|twitch.tv|bilibili">
  - .mp4, .webm, .mov, .m4v, .m3u8 (HLS manifest), .mpd (DASH manifest)
  - JSON-LD VideoObject (#video)
  - og:video / og:video:url / twitter:player

Goal: prove the dimension exists. Output URLs only — no downloads.

Output: snapshots/<site>/_video_urls.jsonl

Usage:
  python3 extract_video_urls.py <site>
  python3 extract_video_urls.py --all
"""
import argparse
import json
import re
import urllib.parse
from pathlib import Path

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()

VIDEO_EXTS = (".mp4", ".webm", ".mov", ".m4v", ".m3u8", ".mpd", ".ts", ".ogv", ".avi", ".mkv")
VIDEO_EXT_RE = re.compile(
    r'\b([\w./:%?=&#~-]+?\.(?:mp4|webm|mov|m4v|m3u8|mpd|ts|ogv|avi|mkv))(?:\b|["\'])',
    re.IGNORECASE,
)
VIDEO_ATTR_RE = re.compile(r'<video\b[^>]*?src\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
SOURCE_RE = re.compile(r'<source\b[^>]*?src\s*=\s*["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)
IFRAME_RE = re.compile(r'<iframe\b[^>]*?src\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
META_RE = re.compile(
    r'<meta\b[^>]+(?:property|name)\s*=\s*["\']([^"\']+)["\'][^>]+content\s*=\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)
JSONLD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)

EMBED_HOSTS = ("youtube.com", "youtu.be", "youtube-nocookie.com",
               "vimeo.com", "player.vimeo.com",
               "dailymotion.com", "twitch.tv", "bilibili.com",
               "wistia.com", "loom.com", "ted.com/embed")


def normalize(url: str, base: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith(("http://", "https://", "data:")):
        return url
    # R02 compass fix: schemeless absolute URL like "videos.ctfassets.net/..."
    # R03 huggingface fix: tighten — require TLD whitelist
    # R04 google_maps fix: also require URL to end with a known video ext
    # OR be a known embed host. Random JS strings like "google.com/maps/..."
    # in inline scripts must NOT be promoted to schemeless URLs.
    if "/" in url:
        first = url.split("/", 1)[0]
        if first.count(".") >= 2:
            tld = first.rsplit(".", 1)[-1].lower()
            COMMON_TLDS = {"com", "net", "org", "io", "co", "edu", "gov",
                           "uk", "de", "jp", "cn", "fr", "tv", "cc", "me",
                           "ai", "app", "dev", "ly", "to", "us", "in"}
            if tld in COMMON_TLDS:
                # R04 fix: only promote if path ends with video ext or first
                # segment is a known media CDN. Otherwise leave to urljoin.
                lower = url.lower()
                if is_video_url(lower) or is_embed(lower) or any(
                        cdn in first for cdn in (
                            "ctfassets", "cloudfront", "akamaized",
                            "cloudflarestream", "cdn.", "cdnjs",
                            "fastly", "videocdn", "vidcdn", "vid.", "media.",
                            "stream.", "play.", "videos.",
                        )):
                    return "https://" + url
    return urllib.parse.urljoin(base, url)


def is_video_url(url: str) -> bool:
    if not url:
        return False
    u = url.lower().split("?", 1)[0].split("#", 1)[0]
    return u.endswith(VIDEO_EXTS)


def is_embed(url: str) -> bool:
    u = url.lower()
    return any(h in u for h in EMBED_HOSTS)


def extract_jsonld_video(html: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for m in JSONLD_RE.finditer(html):
        try:
            data = json.loads(m.group(1).strip())
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
                t = " ".join(map(str, t))
            if "VideoObject" in str(t) or "Movie" in str(t) or "TVEpisode" in str(t):
                for k in ("contentUrl", "embedUrl", "url"):
                    v = obj.get(k)
                    if v:
                        out.append((str(v), f"jsonld:{t}:{k}"))
            for v in obj.values():
                if isinstance(v, (dict, list)):
                    stack.append(v)
    return out


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

    def add(url: str, source: str, kind: str):
        url = normalize(url, base or base_url)
        if not url or not (url.startswith("http") or url.startswith("data:")):
            return
        if url in found:
            return
        found[url] = {
            "url": url[:500],
            "page": page_dir.name,
            "source": source,
            "kind": kind,
        }

    for m in VIDEO_ATTR_RE.finditer(html):
        add(m.group(1), "video[src]", "file")
    for m in SOURCE_RE.finditer(html):
        u = m.group(1)
        if is_video_url(u):
            add(u, "video>source", "file")
    for m in IFRAME_RE.finditer(html):
        u = m.group(1)
        if is_embed(u):
            add(u, "iframe[src]", "embed")
    for m in VIDEO_EXT_RE.finditer(html):
        add(m.group(1), "inline-string", "file")
    for m in META_RE.finditer(html):
        prop, content = m.group(1).lower(), m.group(2)
        if "video" in prop or prop == "twitter:player":
            if is_video_url(content) or is_embed(content):
                add(content, f"meta:{prop}", "embed" if is_embed(content) else "file")
    for url, source in extract_jsonld_video(html):
        add(url, source, "embed" if is_embed(url) else "file")

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
    out = site_dir / "_video_urls.jsonl"
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
    print(f"{'site':<30} {'pgs':>5} {'wVid':>5} {'urls':>6}  embed/file")
    print("-" * 70)
    grand = 0
    for site_dir in targets:
        if not site_dir.exists():
            print(f"{site_dir.name:<30}  MISSING")
            continue
        pgs, wv, kinds = process_site(site_dir)
        n = sum(kinds.values())
        grand += n
        kk = " ".join(f"{k}={v}" for k, v in sorted(kinds.items()))
        print(f"{site_dir.name:<30} {pgs:>5} {wv:>5} {n:>6}  {kk}")
    print(f"\nGrand total video URLs: {grand}")


if __name__ == "__main__":
    main()
