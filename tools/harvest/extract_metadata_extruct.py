#!/usr/bin/env python3
"""extract_metadata_extruct.py — Feature Q: full semantic-data dimension.

Uses the `extruct` library to capture metadata syntaxes that our hand-rolled
`reprocess_structured.py` misses:
  - microdata (HTML5 itemtype/itemprop)
  - RDFa (vocab/typeof/property attributes — Cambridge dict alone has 202 items)
  - microformats (h-card, h-recipe, etc.)
  - Dublin Core meta tags
  - opengraph (redundant with reprocess, but kept for self-contained output)
  - JSON-LD (already covered, but reconciled here for completeness)

Run AFTER reprocess_structured.py to add full-syntax coverage.

Output: snapshots/<site>/<page>/extruct.json    (per page)
        snapshots/<site>/_extruct_index.json    (per-syntax site counts)

Usage:
  python3 extract_metadata_extruct.py <site>
  python3 extract_metadata_extruct.py --all
"""
import argparse
import json
import re
import sys
from pathlib import Path
import urllib.parse

try:
    import extruct  # type: ignore
except ImportError:
    print("ERROR: pip install --break-system-packages extruct", file=sys.stderr)
    sys.exit(2)

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()
SYNTAXES = ['microdata', 'json-ld', 'opengraph', 'rdfa', 'microformat', 'dublincore']


def guess_base_url(html: str, fallback: str) -> str:
    m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', html, re.IGNORECASE)
    if m: return m.group(1)
    m = re.search(r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)', html, re.IGNORECASE)
    if m: return m.group(1)
    return fallback


def process_page(page_dir: Path, fallback_base: str) -> dict:
    html_path = page_dir / "full.html"
    if not html_path.exists():
        return {}
    html = html_path.read_text(encoding="utf-8", errors="ignore")
    base = guess_base_url(html, fallback_base)
    try:
        data = extruct.extract(html, base_url=base, syntaxes=SYNTAXES, uniform=False)
    except Exception as e:
        return {"error": str(e)[:200]}
    # R05 fix: filter RDFa noise — xhtml/vocab# items (ARIA role=, h-* tailwind utility)
    # are not real semantic data, just HTML attribute artifacts. Drop them.
    # RDFa items shape: {"@id": "_:NXXX", "http://...xhtml/vocab#role": [...]}
    rdfa = data.get("rdfa") or []
    if rdfa:
        cleaned = []
        for item in rdfa:
            if not isinstance(item, dict):
                cleaned.append(item)
                continue
            # Check if all non-id keys are xhtml/vocab properties
            non_id_keys = [k for k in item.keys() if k != "@id"]
            if non_id_keys and all("xhtml/vocab" in k for k in non_id_keys):
                continue
            # Also check via @type if present
            t = item.get("@type", "")
            t_str = " ".join(map(str, t)) if isinstance(t, list) else str(t)
            if "xhtml/vocab" in t_str.lower():
                continue
            cleaned.append(item)
        data["rdfa"] = cleaned
    # microformat: drop Tailwind h-* false positives too
    mf = data.get("microformat") or []
    if mf:
        data["microformat"] = [
            m for m in mf
            if not (m.get("type") and isinstance(m["type"], list)
                    and all(t.startswith("h-") and len(t) < 12 for t in m["type"]))
        ]
    counts = {s: len(data.get(s, []) or []) for s in SYNTAXES}
    (page_dir / "extruct.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return counts


def process_site(site_dir: Path) -> dict:
    fallback_base = f"https://{site_dir.name.replace('_', '.')}/"
    site_totals = {s: 0 for s in SYNTAXES}
    page_count = 0
    pages_with = 0
    for page_dir in sorted(site_dir.iterdir()):
        if not page_dir.is_dir() or page_dir.name.startswith('_'):
            continue
        page_count += 1
        counts = process_page(page_dir, fallback_base)
        if any(counts.get(s, 0) for s in SYNTAXES):
            pages_with += 1
        for s in SYNTAXES:
            site_totals[s] += counts.get(s, 0)
    index = {"pages_scanned": page_count, "pages_with_meta": pages_with, "totals": site_totals}
    (site_dir / "_extruct_index.json").write_text(json.dumps(index, indent=2))
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
    print(f"{'site':<30} {'pgs':>4} {'wM':>3} " + " ".join(f"{s[:6]:>6}" for s in SYNTAXES))
    print("-" * 90)
    for site_dir in targets:
        if not site_dir.exists():
            print(f"{site_dir.name:<30}  MISSING")
            continue
        idx = process_site(site_dir)
        t = idx['totals']
        print(f"{site_dir.name:<30} {idx['pages_scanned']:>4} {idx['pages_with_meta']:>3} "
              + " ".join(f"{t[s]:>6}" for s in SYNTAXES))


if __name__ == "__main__":
    main()
