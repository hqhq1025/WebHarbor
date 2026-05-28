#!/usr/bin/env python3
"""index_site.py — generate ~/webvoyager-analysis/real_components/snapshots/<site>/_index.json

Walks all <site>/<page>/metadata.json under snapshots/<site>/ and aggregates:
  - per-page status + flags + fragment count
  - per-site totals
  - quick way to grep for bot_block / not_found / interstitial / http2_error

Usage:
  python3 index_site.py <site>          # one site
  python3 index_site.py --all           # all sites
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()


def index_one(site_dir: Path) -> dict:
    pages = []
    for page_dir in sorted(p for p in site_dir.iterdir() if p.is_dir()):
        md_path = page_dir / "metadata.json"
        if not md_path.exists():
            continue
        try:
            md = json.loads(md_path.read_text())
        except Exception:
            continue
        frags = md.get("fragments", [])
        pages.append({
            "page": page_dir.name,
            "url": md.get("url"),
            "status": md.get("status"),
            "title": md.get("title"),
            "fragments": len(frags) - 1 if frags else 0,  # exclude `full`
            "not_found": md.get("not_found", False),
            "bot_block": md.get("bot_block", False),
            "interstitial": md.get("interstitial", False),
            "http2_error": md.get("http2_error", False),
            "fallback_used": md.get("fallback_used"),
            "has_content_md": (page_dir / "content.md").exists(),
            "size_kb": sum(f.stat().st_size for f in page_dir.iterdir() if f.is_file()) // 1024,
        })
    totals = {
        "total_pages": len(pages),
        "ok_pages": sum(1 for p in pages if not (p["not_found"] or p["bot_block"])),
        "not_found": sum(1 for p in pages if p["not_found"]),
        "bot_block": sum(1 for p in pages if p["bot_block"]),
        "interstitial": sum(1 for p in pages if p["interstitial"]),
        "http2_error": sum(1 for p in pages if p["http2_error"]),
        "with_fallback": sum(1 for p in pages if p["has_content_md"]),
        "total_fragments": sum(p["fragments"] for p in pages),
        "total_size_kb": sum(p["size_kb"] for p in pages),
    }
    return {"site": site_dir.name, "totals": totals, "pages": pages}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site", nargs="?", help="site slug, or --all")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    if args.all:
        sites = sorted(p for p in ROOT.iterdir() if p.is_dir())
    elif args.site:
        sites = [ROOT / args.site]
    else:
        print("Usage: index_site.py <site> | --all", file=sys.stderr)
        return 1

    for site_dir in sites:
        if not site_dir.exists():
            print(f"[skip] {site_dir.name} — no snapshots dir", file=sys.stderr)
            continue
        idx = index_one(site_dir)
        (site_dir / "_index.json").write_text(json.dumps(idx, indent=2))
        t = idx["totals"]
        print(f"{site_dir.name}: pages={t['total_pages']} ok={t['ok_pages']} "
              f"bot_block={t['bot_block']} not_found={t['not_found']} "
              f"http2={t['http2_error']} frags={t['total_fragments']} "
              f"size={t['total_size_kb']/1024:.1f}MB")


if __name__ == "__main__":
    sys.exit(main() or 0)
