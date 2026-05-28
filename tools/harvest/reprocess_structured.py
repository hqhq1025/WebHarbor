#!/usr/bin/env python3
"""reprocess_structured.py — re-extract structured data from existing snapshots.

For every snapshots/<site>/<page>/full.html, runs extract_structured() +
trafilatura, writes structured.json + article.json. Uses already-saved HTML
so no Chromium re-launch needed.

Usage:
  python3 reprocess_structured.py             # process all snapshots
  python3 reprocess_structured.py <site>      # one site only
  python3 reprocess_structured.py --skip-articles
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from harvest import extract_structured

try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()


def _flatten_jsonld_objects(blob):
    """Yield every dict in a JSON-LD blob (handles top-level list, @graph)."""
    if isinstance(blob, list):
        for item in blob:
            yield from _flatten_jsonld_objects(item)
    elif isinstance(blob, dict):
        yield blob
        graph = blob.get("@graph")
        if graph:
            yield from _flatten_jsonld_objects(graph)


def extract_breadcrumbs(jsonld_blocks) -> list[dict] | None:
    """Feature F: find Schema.org BreadcrumbList and return flat items list."""
    for blob in jsonld_blocks:
        for obj in _flatten_jsonld_objects(blob):
            t = obj.get("@type")
            if isinstance(t, list):
                t_match = any(x == "BreadcrumbList" for x in t)
            else:
                t_match = (t == "BreadcrumbList")
            if not t_match:
                continue
            items = obj.get("itemListElement") or []
            if not isinstance(items, list):
                continue
            out = []
            for it in items:
                if not isinstance(it, dict):
                    continue
                pos = it.get("position")
                item = it.get("item")
                if isinstance(item, dict):
                    name = item.get("name") or it.get("name")
                    url = item.get("@id") or item.get("url")
                else:
                    name = it.get("name")
                    url = it.get("item") if isinstance(it.get("item"), str) else it.get("@id")
                if name or url:
                    out.append({
                        "position": pos,
                        "name": name,
                        "url": url,
                    })
            if out:
                return out
    return None


def process_page(page_dir: Path, skip_articles=False):
    full_path = page_dir / "full.html"
    if not full_path.exists():
        return None
    try:
        html = full_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    structured = extract_structured(html)
    if structured["jsonld"] or structured["state"] or structured["meta"]:
        (page_dir / "structured.json").write_text(
            json.dumps(structured, ensure_ascii=False, indent=2),
            encoding="utf-8")

    # Feature F: BreadcrumbList -> breadcrumbs.json
    bc_ok = False
    if structured["jsonld"]:
        crumbs = extract_breadcrumbs(structured["jsonld"])
        if crumbs:
            (page_dir / "breadcrumbs.json").write_text(
                json.dumps({"items": crumbs}, ensure_ascii=False, indent=2),
                encoding="utf-8")
            bc_ok = True

    article_ok = False
    if HAS_TRAFILATURA and not skip_articles:
        url = ""
        md_path = page_dir / "metadata.json"
        if md_path.exists():
            try:
                url = json.loads(md_path.read_text()).get("url", "")
            except Exception:
                pass
        try:
            text = trafilatura.extract(html, url=url, output_format="json",
                                        with_metadata=True, include_images=True,
                                        favor_precision=True)
            if text:
                article = json.loads(text)
                if article.get("text") and len(article["text"]) > 200:
                    (page_dir / "article.json").write_text(
                        json.dumps(article, ensure_ascii=False, indent=2),
                        encoding="utf-8")
                    article_ok = True
        except Exception:
            pass

    return (len(structured["jsonld"]), bool(structured["state"]),
            bool(structured["meta"]), article_ok, bc_ok)


def process_site(site_dir: Path, skip_articles=False):
    total = jsonld_pages = state_pages = meta_pages = article_pages = bc_pages = 0
    jsonld_total = 0
    for page_dir in site_dir.iterdir():
        if not page_dir.is_dir():
            continue
        result = process_page(page_dir, skip_articles)
        if result is None:
            continue
        total += 1
        jl, st, mt, ar, bc = result
        jsonld_total += jl
        if jl > 0: jsonld_pages += 1
        if st: state_pages += 1
        if mt: meta_pages += 1
        if ar: article_pages += 1
        if bc: bc_pages += 1
    return total, jsonld_pages, jsonld_total, state_pages, meta_pages, article_pages, bc_pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site", nargs="?")
    ap.add_argument("--skip-articles", action="store_true")
    args = ap.parse_args()

    sites = [ROOT / args.site] if args.site else sorted(p for p in ROOT.iterdir() if p.is_dir())
    print(f"{'site':<28} {'pgs':>5} {'jl-pg':>5} {'jl-tot':>6} {'state':>5} {'meta':>5} {'art':>5} {'bc':>4}")
    print("-" * 75)
    for site_dir in sites:
        if not site_dir.is_dir():
            continue
        n, jp, jt, sp, mp, ap_, bc = process_site(site_dir, args.skip_articles)
        if n > 0:
            print(f"{site_dir.name:<28} {n:>5} {jp:>5} {jt:>6} {sp:>5} {mp:>5} {ap_:>5} {bc:>4}")


if __name__ == "__main__":
    main()
