#!/usr/bin/env python3
"""extract_server_state.py — Feature S: SSR/SPA state blob dimension.

Scans snapshots/<site>/<page>/full.html for inline JSON state blobs that
modern SPA / SSR frameworks emit:
  - __NEXT_DATA__              (Next.js)
  - __APOLLO_STATE__           (Apollo Client)
  - __SERVER_DATA__            (custom SSR)
  - __INITIAL_STATE__          (Redux / Vuex hydration)
  - __NUXT__                   (Nuxt.js)
  - __SVELTEKIT_DATA__         (SvelteKit)
  - __REMIX_CONTEXT__          (Remix)
  - window.__data / __DATA / __PRELOADED_STATE__ / __ROUTER_DATA__
  - data-react-helmet payloads

R02 trigger: coursera, eventbrite, fandom all bury per-page entity payloads
in __NEXT_DATA__ (500KB+ Apollo state per page) that reprocess_structured.py
only partially captures via the generic 'state' field.

Output: snapshots/<site>/<page>/server_state.json (per page, when found)
        snapshots/<site>/_server_state_index.json (site aggregate)

Usage:
  python3 extract_server_state.py <site>
  python3 extract_server_state.py --all
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()

PATTERNS = [
    ("__NEXT_DATA__",
     re.compile(r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', re.DOTALL)),
    ("__APOLLO_STATE__",
     re.compile(r'__APOLLO_STATE__\s*=\s*(\{.*?\})\s*;?\s*<', re.DOTALL)),
    ("__SERVER_DATA__",
     re.compile(r'__SERVER_DATA__\s*=\s*(\{.*?\})\s*;?\s*<', re.DOTALL)),
    ("__INITIAL_STATE__",
     re.compile(r'__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;?\s*<', re.DOTALL)),
    ("__PRELOADED_STATE__",
     re.compile(r'__PRELOADED_STATE__\s*=\s*(\{.*?\})\s*;?\s*<', re.DOTALL)),
    ("__NUXT__",
     re.compile(r'window\.__NUXT__\s*=\s*(\{.*?\})\s*;?\s*</script>', re.DOTALL)),
    ("__SVELTEKIT_DATA__",
     re.compile(r'__sveltekit_data\s*=\s*(\{.*?\})\s*;', re.DOTALL)),
    ("__REMIX_CONTEXT__",
     re.compile(r'__remixContext\s*=\s*(\{.*?\})\s*;', re.DOTALL)),
    ("window.__data",
     re.compile(r'window\.__data\s*=\s*(\{.*?\})\s*;?\s*</script>', re.DOTALL)),
    # R04 google_flights fix: Google's WIZ_global_data + AF_initDataCallback
    # unlocks 750+ KB SSR across Search/Maps/Flights/News/Translate family
    ("WIZ_global_data",
     re.compile(r'window\.WIZ_global_data\s*=\s*(\{.*?\})\s*;?\s*</script>', re.DOTALL)),
]
# AF_initDataCallback is per-blob: multiple matches per page, collect all
AF_INIT_RE = re.compile(
    r'AF_initDataCallback\(\s*(\{[^)]*?\})\s*\)\s*;?',
    re.DOTALL,
)

# R04 osu fix: generic Laravel/Discourse/Rails inline JSON island.
# Matches <script type="application/json" id="X">{...}</script>.
# R05 RT fix: also support data-json="X" attribute (Nunjucks/Next.js island-mode).
# R06 kayak fix: attribute order-independent — match both `id=...type=...` and
# `type=...id=...`. Kayak uses `<script id="jsonData_R9DataStorage" type="application/json">`
# (1.24 MB SSR per page, 12 MB total — was completely missed).
JSON_ISLAND_RE = re.compile(
    r'<script\b(?=[^>]*\btype=["\']application/json["\'])(?=[^>]*\b(?:id|data-json|data-component|data-page)=["\']([^"\']+)["\'])[^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)
# Fallback: <script type="application/json"> without id/data-json (rare)
JSON_ISLAND_ANON_RE = re.compile(
    r'<script\b[^>]*?type=["\']application/json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)

# R05 bandcamp fix: HTML data-* attributes carrying JSON payloads.
# Matches data-X='{...}' or data-X="{...}" where value starts with { or [.
# Common: data-tralbum (bandcamp), data-react-props, data-product (Shopify),
# data-state, data-page-props.
DATA_ATTR_JSON_RE = re.compile(
    r'\bdata-([\w-]+)\s*=\s*["\'](\s*[{\[][^"\']{50,}[}\]]\s*)["\']',
    re.IGNORECASE,
)

# R06 chess_com fix: brand-namespace bootstrap pattern
# Matches: window.<brand> = window.<brand> || {}; window.<brand>.<key> = <JSON>;
# Example: chess.com uses `window.chesscom.userNavigationConfig = {...}` × 7/page
# Captures: (brand, key, json_body)
BRAND_NS_RE = re.compile(
    r'window\.([a-zA-Z][\w$]{2,30})\.([a-zA-Z][\w$]{2,40})\s*=\s*(\{[^;]{50,}?\}|\[[^;]{50,}?\])\s*;',
    re.DOTALL,
)

# R08 chess_com fix: JSON.parse("...") escape wrapper (Redux/Apollo/custom SSR
# dehydration). Inner is escaped JSON string.
JSON_PARSE_RE = re.compile(
    r'JSON\.parse\(\s*"((?:\\.|[^"\\])*)"\s*\)',
    re.DOTALL,
)


def try_parse(s: str) -> dict | None:
    s = s.strip().rstrip(';').strip()
    try:
        return json.loads(s)
    except Exception:
        # Try to find a valid JSON prefix
        depth = 0
        end = 0
        for i, c in enumerate(s):
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end:
            try:
                return json.loads(s[:end])
            except Exception:
                return None
        return None


def shape_summary(obj, depth=0, max_depth=3) -> dict:
    """Return shape (top-level keys + types) without full payload."""
    if depth >= max_depth:
        return {"_truncated": True}
    if isinstance(obj, dict):
        out = {}
        for k, v in list(obj.items())[:30]:
            if isinstance(v, dict):
                out[k] = {"_type": "dict", "_n_keys": len(v), "_keys": list(v.keys())[:10]}
            elif isinstance(v, list):
                out[k] = {"_type": "list", "_n": len(v)}
            else:
                out[k] = {"_type": type(v).__name__, "_size": len(str(v))}
        return out
    return {"_type": type(obj).__name__}


def process_page(page_dir: Path) -> dict:
    html_path = page_dir / "full.html"
    if not html_path.exists():
        return {}
    html = html_path.read_text(encoding="utf-8", errors="ignore")
    found = {}
    for name, pat in PATTERNS:
        m = pat.search(html)
        if not m:
            continue
        raw = m.group(1)
        parsed = try_parse(raw)
        found[name] = {
            "raw_size": len(raw),
            "parsed": parsed is not None,
            "top_keys": list(parsed.keys())[:30] if isinstance(parsed, dict) else None,
            "shape": shape_summary(parsed) if parsed else None,
        }
    # R04 google_flights fix: AF_initDataCallback collects ALL matches
    af_matches = list(AF_INIT_RE.finditer(html))
    if af_matches:
        total_raw = sum(len(m.group(1)) for m in af_matches)
        found["AF_initDataCallback"] = {
            "raw_size": total_raw,
            "blob_count": len(af_matches),
            "parsed": None,
            "top_keys": None,
            "shape": {"_n_blobs": len(af_matches), "_total_chars": total_raw},
        }
    # R04 osu fix: generic Laravel/Discourse/Rails inline JSON islands
    json_islands = list(JSON_ISLAND_RE.finditer(html))
    if json_islands:
        total_raw = sum(len(m.group(2)) for m in json_islands)
        found["inline_json_islands"] = {
            "raw_size": total_raw,
            "island_count": len(json_islands),
            "island_ids": [m.group(1) for m in json_islands[:20]],
            "parsed": None,
            "top_keys": None,
            "shape": {"_n_islands": len(json_islands), "_total_chars": total_raw},
        }
    # R05 bandcamp fix: data-* attribute JSON (data-tralbum, data-react-props, etc.)
    # Use raw HTML decoded for &quot;-escaped JSON values.
    import html as htmllib
    html_unescaped = htmllib.unescape(html)
    data_attrs = []
    for m in DATA_ATTR_JSON_RE.finditer(html_unescaped):
        attr = m.group(1)
        body = m.group(2).strip()
        if len(body) < 80:
            continue
        data_attrs.append((attr, body))
    if data_attrs:
        total_raw = sum(len(b) for _, b in data_attrs)
        found["data_attr_json"] = {
            "raw_size": total_raw,
            "attr_count": len(data_attrs),
            "attr_names": list({a for a, _ in data_attrs})[:20],
            "parsed": None,
            "top_keys": None,
            "shape": {"_n_attrs": len(data_attrs), "_total_chars": total_raw},
        }
    # R06 chess fix: brand-namespace bootstrap `window.<brand>.X = JSON;`
    brand_ns = []
    seen_keys = set()
    for m in BRAND_NS_RE.finditer(html):
        brand, key, body = m.group(1), m.group(2), m.group(3)
        # Skip common JS object setups (event handlers, ajax, etc.)
        if brand.lower() in ("location", "document", "navigator", "performance",
                              "history", "console", "screen", "addeventlistener"):
            continue
        if key.lower() in ("onload", "onerror", "onclick", "addeventlistener"):
            continue
        k = f"{brand}.{key}"
        if k in seen_keys:
            continue
        seen_keys.add(k)
        brand_ns.append((brand, key, body))
    if brand_ns:
        total_raw = sum(len(b) for _, _, b in brand_ns)
        found["brand_namespace_bootstrap"] = {
            "raw_size": total_raw,
            "assign_count": len(brand_ns),
            "keys": [f"{b}.{k}" for b, k, _ in brand_ns[:20]],
            "parsed": None,
            "top_keys": None,
            "shape": {"_n_assigns": len(brand_ns), "_total_chars": total_raw},
        }
    # R08 chess fix: JSON.parse("...") escape wrapper (Redux/Apollo/custom SSR
    # dehydration). Inner string is escaped JSON; parse after un-escaping.
    json_parse_blobs = []
    for m in JSON_PARSE_RE.finditer(html):
        inner = m.group(1)
        if len(inner) < 100:
            continue  # skip tiny `JSON.parse("true")` etc
        # Un-escape JS string
        try:
            unesc = bytes(inner, "utf-8").decode("unicode_escape")
        except Exception:
            unesc = inner
        json_parse_blobs.append(unesc)
    if json_parse_blobs:
        total_raw = sum(len(b) for b in json_parse_blobs)
        found["json_parse_blobs"] = {
            "raw_size": total_raw,
            "blob_count": len(json_parse_blobs),
            "parsed": None,
            "top_keys": None,
            "shape": {"_n_blobs": len(json_parse_blobs), "_total_chars": total_raw},
        }
    if found:
        # Save the full JSON to a per-page file for downstream use
        out = {}
        for name, pat in PATTERNS:
            m = pat.search(html)
            if m:
                parsed = try_parse(m.group(1))
                if parsed is not None:
                    out[name] = parsed
        if af_matches:
            out["AF_initDataCallback"] = [m.group(1)[:5000] for m in af_matches[:20]]
        if json_islands:
            out["inline_json_islands"] = {
                m.group(1): try_parse(m.group(2)) or m.group(2)[:5000]
                for m in json_islands[:30]
            }
        if data_attrs:
            out["data_attr_json"] = {
                attr: try_parse(body) or body[:5000]
                for attr, body in data_attrs[:30]
            }
        if brand_ns:
            out["brand_namespace_bootstrap"] = {
                f"{b}.{k}": try_parse(body) or body[:5000]
                for b, k, body in brand_ns[:30]
            }
        if json_parse_blobs:
            out["json_parse_blobs"] = [
                (try_parse(b) or b[:5000]) for b in json_parse_blobs[:30]
            ]
        (page_dir / "server_state.json").write_text(json.dumps(out, ensure_ascii=False))
    return found


def process_site(site_dir: Path) -> dict:
    pages_scanned = 0
    pages_with = 0
    type_counts = {}
    total_kb = 0
    for page_dir in sorted(site_dir.iterdir()):
        if not page_dir.is_dir() or page_dir.name.startswith('_'):
            continue
        pages_scanned += 1
        found = process_page(page_dir)
        if found:
            pages_with += 1
            for name, info in found.items():
                type_counts[name] = type_counts.get(name, 0) + 1
                total_kb += info["raw_size"] / 1024
    index = {
        "pages_scanned": pages_scanned,
        "pages_with_state": pages_with,
        "type_counts": type_counts,
        "total_raw_kb": round(total_kb, 1),
    }
    (site_dir / "_server_state_index.json").write_text(json.dumps(index, indent=2))
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
    print(f"{'site':<30} {'pgs':>4} {'wSt':>4} {'kb':>8}  top types")
    print("-" * 80)
    grand = 0.0
    for site_dir in targets:
        if not site_dir.exists():
            print(f"{site_dir.name:<30}  MISSING"); continue
        idx = process_site(site_dir)
        grand += idx['total_raw_kb']
        tt = " ".join(f"{k.strip('_')[:8]}={v}" for k, v in sorted(idx['type_counts'].items(), key=lambda kv: -kv[1])[:3])
        print(f"{site_dir.name:<30} {idx['pages_scanned']:>4} {idx['pages_with_state']:>4} {idx['total_raw_kb']:>8.1f}  {tt}")
    print(f"\nGrand total state JSON: {grand:.0f} KB")


if __name__ == "__main__":
    main()
