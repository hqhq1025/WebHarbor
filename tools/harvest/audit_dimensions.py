#!/usr/bin/env python3
"""audit_dimensions.py — Cross-site coverage report for the 10 harvest dimensions.

For each site_dir under snapshots/, count what we have:
  pages                — N page dirs
  styles               — pages with full.html
  text                 — pages with structured.json or article.json
  forms                — _forms.jsonl rows
  facets               — _facets.jsonl rows (or "no_facets_hint" if hint file present)
  nav                  — _nav_graph.json node count
  images               — _image_urls.jsonl rows
  sprites              — _sprites.json count
  sitemap              — _sitemap_urls.jsonl rows
  audio                — _audio_urls.jsonl rows
  video                — _video_urls.jsonl rows
  icons                — _icons.jsonl rows
  animations           — _animations.jsonl rows
  code                 — _code_blocks.jsonl rows

Output: markdown table to stdout.

Usage:
  python3 audit_dimensions.py [> coverage_report.md]
"""
import json
from pathlib import Path

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()


def count_lines(p: Path) -> int:
    if not p.exists():
        return 0
    try:
        return sum(1 for _ in p.open())
    except Exception:
        return 0


def count_dirs(d: Path) -> int:
    return sum(1 for c in d.iterdir() if c.is_dir() and not c.name.startswith("_"))


def count_pages_with(d: Path, fname: str) -> int:
    return sum(1 for c in d.iterdir()
               if c.is_dir() and not c.name.startswith("_") and (c / fname).exists())


def json_count(p: Path, key: str = "") -> int:
    if not p.exists():
        return 0
    try:
        data = json.loads(p.read_text())
        if key and isinstance(data, dict):
            v = data.get(key, [])
            if isinstance(v, list):
                return len(v)
            if isinstance(v, (int, float)):
                return int(v)
            return 0
        if isinstance(data, list):
            return len(data)
        if isinstance(data, dict):
            return len(data)
    except Exception:
        return 0
    return 0


def sprites_count(p: Path) -> int:
    """`_sprites.json` is a dict with `n_symbols` field — use that, not key count."""
    if not p.exists():
        return 0
    try:
        d = json.loads(p.read_text())
        return int(d.get("n_symbols", 0)) if isinstance(d, dict) else 0
    except Exception:
        return 0


def extruct_total(p: Path) -> int:
    """`_extruct_index.json` has 'totals' dict summing 5 syntaxes."""
    if not p.exists():
        return 0
    try:
        d = json.loads(p.read_text())
        return sum((d.get("totals") or {}).values())
    except Exception:
        return 0


def audit_site(site_dir: Path) -> dict:
    api_idx = site_dir / "_api_endpoints_index.json"
    state_idx = site_dir / "_server_state_index.json"
    ws_idx = site_dir / "_ws_streams_index.json"
    return {
        "site": site_dir.name,
        "pages": count_dirs(site_dir),
        "styles_html": count_pages_with(site_dir, "full.html"),
        "structured": count_pages_with(site_dir, "structured.json"),
        "article": count_pages_with(site_dir, "article.json"),
        "breadcrumb": count_pages_with(site_dir, "breadcrumbs.json"),
        "extruct": extruct_total(site_dir / "_extruct_index.json"),
        "forms": count_lines(site_dir / "_forms.jsonl"),
        "facets": count_lines(site_dir / "_facets.jsonl"),
        "facets_hint": (site_dir / "_facets_hint.json").exists(),
        "nav_nodes": json_count(site_dir / "_nav_graph.json", "nodes"),
        "images": count_lines(site_dir / "_image_urls.jsonl"),
        "sprites": sprites_count(site_dir / "_sprites.json"),
        "sitemap": count_lines(site_dir / "_sitemap_urls.jsonl"),
        "audio": count_lines(site_dir / "_audio_urls.jsonl"),
        "video": count_lines(site_dir / "_video_urls.jsonl"),
        "icons": count_lines(site_dir / "_icons.jsonl"),
        "anim": count_lines(site_dir / "_animations.jsonl"),
        "code": count_lines(site_dir / "_code_blocks.jsonl"),
        "api_calls": json_count(api_idx, "total_calls"),
        "state_kb": json_count(state_idx, "total_raw_kb"),
        "ws_streams": json_count(ws_idx, "total_records"),
    }


def main():
    cols = ["site", "pages", "structured", "extruct", "forms", "facets", "nav_nodes",
            "images", "sprites", "sitemap", "audio", "video", "icons", "anim", "code",
            "api_calls", "state_kb", "ws_streams"]
    rows = []
    for d in sorted(ROOT.iterdir()):
        if not d.is_dir():
            continue
        rows.append(audit_site(d))

    # Markdown table
    head = "| " + " | ".join(cols) + " |"
    sep  = "|" + "|".join(["---"] * len(cols)) + "|"
    print("# Harvest Dimension Coverage Audit")
    print(f"\nSnapshots: `{ROOT}`  total sites: {len(rows)}\n")
    print(head)
    print(sep)
    for r in rows:
        cells = []
        for c in cols:
            v = r.get(c, "")
            if c == "facets" and r.get("facets_hint") and v == 0:
                cells.append("0†")  # mark site-property N/A
            else:
                cells.append(str(v))
        print("| " + " | ".join(cells) + " |")
    print("\n*† = `_facets_hint.json` says site has no facet UI (link-nav or React-modal). Not an extractor miss.*")

    # Aggregate stats
    def col_sum(c): return sum(r.get(c, 0) or 0 for r in rows if isinstance(r.get(c), int))
    def col_hit(c): return sum(1 for r in rows if (r.get(c) or 0) > 0)
    print("\n## Totals & coverage\n")
    print("| dim | sites_hit / total | grand_total |")
    print("|---|---|---|")
    for c in ["structured", "extruct", "forms", "facets", "images", "sprites", "sitemap",
              "audio", "video", "icons", "anim", "code", "api_calls", "state_kb", "ws_streams"]:
        print(f"| {c} | {col_hit(c)} / {len(rows)} | {col_sum(c)} |")


if __name__ == "__main__":
    main()
