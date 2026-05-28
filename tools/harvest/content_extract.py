#!/usr/bin/env python3
"""content_extract.py — readability/trafilatura wrapper for article body extraction.

Given a `full.html` saved by harvest.py, produces structured article fields:
  {title, author, date, body_text, body_markdown, hero_image, byline, sitename,
   categories, tags, language, comments, links}

Use case: news/blog/article sites where we want clean body text + meta, not raw
HTML. Powers design-tasks seed (real article body) and document-site-gui.

Usage:
  python3 content_extract.py <snapshot_dir>     # extract one
  python3 content_extract.py --all              # extract all snapshots/<site>/<page>/full.html
"""
import argparse
import json
import sys
from pathlib import Path

import trafilatura

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()


def extract_one(snapshot_dir: Path):
    full_html_path = snapshot_dir / "full.html"
    if not full_html_path.exists():
        return None
    html = full_html_path.read_text(encoding="utf-8", errors="ignore")
    md_path = snapshot_dir / "metadata.json"
    url = ""
    if md_path.exists():
        try:
            url = json.loads(md_path.read_text()).get("url", "")
        except Exception:
            pass

    # Extract clean article
    text = trafilatura.extract(html, url=url, output_format="json",
                                with_metadata=True, include_images=True,
                                include_links=True, include_comments=False,
                                favor_precision=True)
    if not text:
        return None
    try:
        result = json.loads(text)
    except Exception:
        return None

    out_path = snapshot_dir / "article.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="snapshot dir (e.g. snapshots/bbc_com/article)")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    if args.all:
        targets = [p for site_dir in ROOT.iterdir() if site_dir.is_dir()
                    for p in site_dir.iterdir() if p.is_dir()]
    elif args.path:
        targets = [Path(args.path)]
    else:
        print("Usage: content_extract.py <snapshot_dir> | --all", file=sys.stderr)
        return 1

    ok, fail = 0, 0
    for d in targets:
        try:
            r = extract_one(d)
            if r and r.get("text"):
                ok += 1
                if len(targets) == 1:
                    print(f"title: {r.get('title','')}")
                    print(f"author: {r.get('author','')}")
                    print(f"date: {r.get('date','')}")
                    print(f"body chars: {len(r.get('text',''))}")
            else:
                fail += 1
        except Exception:
            fail += 1
    print(f"extract: ok={ok} fail={fail}")


if __name__ == "__main__":
    sys.exit(main() or 0)
