#!/usr/bin/env python3
"""extract_facets.py — Feature C: extract filter facets from listing pages.

Scans snapshots/<site>/<page>/full.html for sidebar/filter blocks and dumps
each facet group as a JSON line.

Heuristics for facet container detection:
  - elements whose class/id contains: facet, filter, refine, refinement, refinements
  - aside / [role=complementary]
  - section/div headers (h2/h3/h4) followed by ul/ol of inputs

For each facet container we extract:
  - group_label: legend or nearest heading
  - group_id: id or first slug found in class
  - type: checkbox|radio|select|range|list (inferred from input types found)
  - options: [{label, value, count, url_param}]

Outputs snapshots/<site>/_facets.jsonl

Usage:
  python3 extract_facets.py <site>
  python3 extract_facets.py --all
"""
import argparse
import html as htmllib
import json
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()

ATTR_RE = re.compile(r'([a-zA-Z_:][\w:.-]*)\s*=\s*"([^"]*)"|([a-zA-Z_:][\w:.-]*)\s*=\s*\'([^\']*)\'')


def parse_attrs(attr_str: str) -> dict:
    out: dict = {}
    for m in ATTR_RE.finditer(attr_str):
        if m.group(1):
            out[m.group(1).lower()] = htmllib.unescape(m.group(2))
        elif m.group(3):
            out[m.group(3).lower()] = htmllib.unescape(m.group(4))
    return out


def strip_tags(s: str) -> str:
    txt = re.sub(r"<[^>]+>", " ", s)
    txt = htmllib.unescape(txt)
    return re.sub(r"\s+", " ", txt).strip()


# Find sidebar-ish blocks: open tag matched to its close. Greedy enough but
# capped. We don't do full DOM parsing — for speed use heuristic block grab.
FACET_OPEN_RE = re.compile(
    r'<(div|section|aside|nav|form|fieldset|details|ul)\b([^>]*\b(?:class|id|aria-label|data-test|data-testid|role)\s*=\s*"[^"]*(?:facet|filter|refine|refinement|search-filter|sidebar-filter|facets|filters)[^"]*"[^>]*)>',
    re.IGNORECASE)

# Containers that look like filter-bar but aren't real facets — skip
SKIP_CLASS_RE = re.compile(
    r'\b(?:filter-bar|filterbar|filter-tag|filter-chip|filter-summary|'
    r'breadcrumb|pagination|paginat|footer|header-nav|site-nav|topnav)\b',
    re.IGNORECASE)

INPUT_RE = re.compile(r'<input\b([^>]*?)/?>', re.IGNORECASE)
LABEL_RE = re.compile(r'<label\b([^>]*?)>(.*?)</label>', re.IGNORECASE | re.DOTALL)
A_RE = re.compile(r'<a\b([^>]*?)>(.*?)</a>', re.IGNORECASE | re.DOTALL)
SELECT_RE = re.compile(r'<select\b([^>]*?)>(.*?)</select>', re.IGNORECASE | re.DOTALL)
OPTION_RE = re.compile(r'<option\b([^>]*?)>(.*?)</option>', re.IGNORECASE | re.DOTALL)
LEGEND_RE = re.compile(r'<legend\b[^>]*>(.*?)</legend>', re.IGNORECASE | re.DOTALL)
HEADING_RE = re.compile(r'<(h[1-6]|summary)\b[^>]*>(.*?)</\1>', re.IGNORECASE | re.DOTALL)
COUNT_RE = re.compile(r'[\(\[\s]\s*(\d{1,7})\s*[\)\]\s]?\s*$')


def slice_balanced(html: str, start: int, tag: str, max_len: int = 80_000) -> tuple[int, str]:
    """Crude balanced-tag scanner. Returns (end_index, inner_html). Limited."""
    open_pat = re.compile(rf'<{tag}\b', re.IGNORECASE)
    close_pat = re.compile(rf'</{tag}\s*>', re.IGNORECASE)
    depth = 1
    pos = start
    end_limit = min(start + max_len, len(html))
    while pos < end_limit and depth > 0:
        o = open_pat.search(html, pos, end_limit)
        c = close_pat.search(html, pos, end_limit)
        if not c:
            return end_limit, html[start:end_limit]
        if o and o.start() < c.start():
            depth += 1
            pos = o.end()
        else:
            depth -= 1
            pos = c.end()
            if depth == 0:
                return pos, html[start:c.start()]
    return pos, html[start:pos]


def detect_group_label(attrs: dict, inner: str) -> str | None:
    leg = LEGEND_RE.search(inner)
    if leg:
        t = strip_tags(leg.group(1))
        if t: return t[:80]
    head = HEADING_RE.search(inner)
    if head:
        t = strip_tags(head.group(2))
        if t: return t[:80]
    for k in ("aria-label", "data-test", "data-testid", "data-facet", "data-section"):
        if attrs.get(k):
            return attrs[k][:80]
    return None


def detect_group_id(attrs: dict) -> str | None:
    if attrs.get("id"):
        return attrs["id"][:80]
    cls = attrs.get("class", "")
    for tok in cls.split():
        low = tok.lower()
        if any(k in low for k in ("facet-", "filter-", "refine-")):
            return tok[:80]
    return None


def extract_options(inner: str, base_url: str = "") -> tuple[list[dict], str]:
    """Pull options from input[checkbox|radio]+labels, select+options, or <a> lists."""
    options = []
    typ = "list"

    # Input-based (checkbox/radio)
    # Build a label-map: label[for=ID] -> text
    label_map = {}
    for m in LABEL_RE.finditer(inner):
        a = parse_attrs(m.group(1))
        if a.get("for"):
            label_map[a["for"]] = strip_tags(m.group(2))

    checkbox_count = radio_count = 0
    for m in INPUT_RE.finditer(inner):
        a = parse_attrs(m.group(1))
        t = (a.get("type") or "").lower()
        if t not in ("checkbox", "radio"):
            continue
        if t == "checkbox": checkbox_count += 1
        if t == "radio": radio_count += 1
        label = label_map.get(a.get("id", ""))
        if not label:
            # try wrapping label heuristic — look 200 chars back
            idx = m.start()
            snippet = inner[max(0, idx - 200):idx]
            lab_m = LABEL_RE.search(snippet + m.group(0) + "</label>")
            if lab_m:
                label = strip_tags(lab_m.group(2))
        if not label and a.get("aria-label"):
            label = a["aria-label"]
        if not label and a.get("value"):
            label = a["value"]
        if not label:
            continue
        count = None
        cm = COUNT_RE.search(label)
        if cm:
            try:
                count = int(cm.group(1))
                label = COUNT_RE.sub("", label).strip()
            except Exception:
                pass
        options.append({
            "label": label[:80],
            "value": a.get("value"),
            "count": count,
            "url_param": f"{a.get('name')}={a.get('value')}" if a.get("name") and a.get("value") else None,
            "checked": "checked" in a,
        })

    if checkbox_count > radio_count and checkbox_count > 0:
        typ = "checkbox"
    elif radio_count > 0:
        typ = "radio"

    # Select-based
    if not options:
        for sm in SELECT_RE.finditer(inner):
            sa = parse_attrs(sm.group(1))
            for om in OPTION_RE.finditer(sm.group(2)):
                oa = parse_attrs(om.group(1))
                text = strip_tags(om.group(2))
                if not text:
                    continue
                options.append({
                    "label": text[:80],
                    "value": oa.get("value", text),
                    "count": None,
                    "url_param": f"{sa.get('name')}={oa.get('value', text)}" if sa.get("name") else None,
                    "checked": "selected" in oa,
                })
            if options:
                typ = "select"
                break

    # Anchor-list based (filter links like /search?cat=foo)
    if not options:
        link_opts = []
        for am in A_RE.finditer(inner):
            aa = parse_attrs(am.group(1))
            text = strip_tags(am.group(2))
            href = aa.get("href")
            if not text or not href:
                continue
            count = None
            cm = COUNT_RE.search(text)
            if cm:
                try:
                    count = int(cm.group(1))
                    text = COUNT_RE.sub("", text).strip()
                except Exception:
                    pass
            qs = urllib.parse.urlparse(href).query
            link_opts.append({
                "label": text[:80],
                "value": None,
                "count": count,
                "url_param": qs[:120] if qs else None,
                "href": href[:200],
            })
        if 2 <= len(link_opts) <= 80:
            options = link_opts
            typ = "list"

    # Range — heuristic: name contains 'min' AND another 'max'
    names = [o.get("url_param") or "" for o in options]
    if any("min" in n.lower() for n in names) and any("max" in n.lower() for n in names):
        typ = "range"

    # Dedup by label
    seen = set()
    deduped = []
    for o in options:
        key = (o.get("label"), o.get("value"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(o)
    return deduped[:100], typ


def process_page(page_dir: Path) -> list[dict]:
    full_path = page_dir / "full.html"
    md_path = page_dir / "metadata.json"
    if not full_path.exists():
        return []
    try:
        html = full_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    url = ""
    if md_path.exists():
        try:
            url = json.loads(md_path.read_text()).get("url", "")
        except Exception:
            pass

    results = []
    consumed_until = 0
    for m in FACET_OPEN_RE.finditer(html):
        if m.start() < consumed_until:
            continue
        tag = m.group(1)
        attrs = parse_attrs(m.group(2))
        # Skip filter-bars / breadcrumbs / pagination / global nav chrome
        cls_id = (attrs.get("class", "") + " " + attrs.get("id", ""))
        if SKIP_CLASS_RE.search(cls_id):
            continue
        end, inner = slice_balanced(html, m.end(), tag, max_len=120_000)
        consumed_until = end
        opts, typ = extract_options(inner)
        if len(opts) < 2:
            continue
        label = detect_group_label(attrs, inner)
        # Spec: skip if group_label empty AND has < 5 options
        if not label and len(opts) < 5:
            continue
        results.append({
            "page": page_dir.name,
            "url": url,
            "group_label": label,
            "group_id": detect_group_id(attrs),
            "type": typ,
            "container_tag": tag,
            "container_class": attrs.get("class", "")[:120],
            "options": opts,
            "option_count": len(opts),
        })
    return results


def process_site(site_dir: Path):
    all_facets = []
    page_count = 0
    pages_with_facets = 0
    listing_pages_scanned = 0
    listing_pages_with_facets = 0
    LISTING_HINTS = ("search", "browse", "category", "list", "shop", "filter",
                     "results", "collection", "products", "catalog", "directory",
                     "find", "explore",
                     # R02 carmax bug fix: add domain-specific listing names
                     "cars", "vehicles", "inventory", "items", "rooms",
                     "jobs", "courses", "events", "tickets", "movies",
                     "shows", "deals", "listings", "stays", "flights",
                     "hotels", "restaurants", "rentals", "homes")
    for page_dir in sorted(site_dir.iterdir()):
        if not page_dir.is_dir():
            continue
        page_count += 1
        name = page_dir.name.lower()
        is_listing = any(h in name for h in LISTING_HINTS)
        if is_listing:
            listing_pages_scanned += 1
        facets = process_page(page_dir)
        if facets:
            pages_with_facets += 1
            if is_listing:
                listing_pages_with_facets += 1
        all_facets.extend(facets)
    out_path = site_dir / "_facets.jsonl"
    with out_path.open("w") as f:
        for fc in all_facets:
            f.write(json.dumps(fc, ensure_ascii=False) + "\n")
    # R01 fix: distinguish "no facet UI on site" vs "extractor miss".
    # If we scanned ≥2 listing-ish pages and got 0 facets, write a hint file
    # so downstream knows it's a real-site property, not a tool bug.
    if listing_pages_scanned >= 2 and listing_pages_with_facets == 0:
        (site_dir / "_facets_hint.json").write_text(json.dumps({
            "no_facets_detected": True,
            "listing_pages_scanned": listing_pages_scanned,
            "hint": "site likely uses link-based nav (e.g. /category/<slug>) or "
                    "React-modal filters (no URL params, no sidebar checkboxes). "
                    "Confirm by inspecting any listing page's full.html.",
        }, indent=2))
    return page_count, pages_with_facets, len(all_facets), sum(f["option_count"] for f in all_facets)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site", nargs="?")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    sites = [ROOT / args.site] if args.site else sorted(p for p in ROOT.iterdir() if p.is_dir())
    print(f"{'site':<28} {'pgs':>5} {'wfac':>5} {'grps':>5} {'opts':>6}")
    print("-" * 60)
    for site_dir in sites:
        if not site_dir.is_dir():
            continue
        pgs, wf, g, o = process_site(site_dir)
        print(f"{site_dir.name:<28} {pgs:>5} {wf:>5} {g:>5} {o:>6}")


if __name__ == "__main__":
    main()
