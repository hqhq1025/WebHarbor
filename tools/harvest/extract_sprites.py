#!/usr/bin/env python3
"""extract_sprites.py — Feature J: extract inline SVG sprite definitions.

Modern sites bundle their icon set as one big inline SVG sprite:

  <svg style="display:none">
    <symbol id="icon-cart-24" viewBox="0 0 24 24"><path d="..."/></symbol>
    <symbol id="icon-search-24" viewBox="0 0 24 24"><path d="..."/></symbol>
    ...
  </svg>

…and reference it everywhere with `<use href="#icon-cart-24"/>`. Without
extracting those <symbol> bodies we can never render the cart / search /
profile icons in the WebHarbor mirror — `<use>` references would resolve to
nothing.

This script walks every full.html under snapshots/<site>/, pulls each
<symbol> out, wraps it in a standalone <svg>, and writes it to
snapshots/<site>/sprites/<id>.svg. It also writes a manifest
snapshots/<site>/_sprites.json:

  {
    "site": "ebay_com",
    "n_symbols": 412,
    "n_pages_with_sprites": 7,
    "symbols": [
      {"id": "icon-cart-24", "viewBox": "0 0 24 24",
       "file": "sprites/icon-cart-24.svg",
       "sha1": "ab12…", "size": 487, "use_count": 14,
       "source_pages": ["home", "cart", "checkout"]}
    ],
    "use_refs_unmatched": ["#ggl-icon"]   # <use href=...> with no matching <symbol>
  }

Usage:
  python3 extract_sprites.py <site>
  python3 extract_sprites.py --all
  python3 extract_sprites.py --all --quiet
"""
import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()

# <symbol …>…</symbol>  — non-greedy body, case-insensitive, dot-matches-newline.
SYMBOL_RE = re.compile(r"<symbol\b([^>]*)>(.*?)</symbol\s*>", re.IGNORECASE | re.DOTALL)

# attribute readers — handle both " and ' quoting
ATTR_RE = re.compile(
    r"""\b([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE
)

# <use href="#id"/> and <use xlink:href="#id"/>
USE_RE = re.compile(
    r"""<use\b[^>]*?\b(?:xlink:)?href\s*=\s*["']#([^"']+)["']""",
    re.IGNORECASE,
)

SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


def safe_filename(name: str) -> str:
    """Map a symbol id to a filesystem-safe filename stem (capped to 80 chars)."""
    s = SAFE_NAME.sub("_", name).strip("._-")
    return (s or "unnamed")[:80]


def parse_attrs(attr_string: str) -> dict:
    """Parse an HTML/SVG attribute blob into a dict. Lowercases keys."""
    out = {}
    for m in ATTR_RE.finditer(attr_string):
        key = m.group(1).lower()
        val = m.group(2) if m.group(2) is not None else m.group(3)
        out[key] = val
    return out


def iter_symbols(html: str):
    """Yield (id, viewBox, preserveAspectRatio, body) for each <symbol> in html."""
    for m in SYMBOL_RE.finditer(html):
        attrs = parse_attrs(m.group(1))
        sym_id = attrs.get("id")
        if not sym_id:
            continue
        viewbox = attrs.get("viewbox") or "0 0 24 24"
        par = attrs.get("preserveaspectratio")
        body = m.group(2).strip()
        if not body:
            # empty <symbol/> — no visual content, skip
            continue
        yield sym_id, viewbox, par, body


def iter_use_refs(html: str):
    """Yield each #id from <use href="#id"> / <use xlink:href="#id">."""
    for m in USE_RE.finditer(html):
        yield m.group(1)


def wrap_symbol_as_svg(viewbox: str, par: str | None, body: str,
                       source_page: str) -> str:
    """Wrap a <symbol> body as a standalone <svg> we can render."""
    attrs = [
        'xmlns="http://www.w3.org/2000/svg"',
        'xmlns:xlink="http://www.w3.org/1999/xlink"',
        f'viewBox="{viewbox}"',
    ]
    if par:
        attrs.append(f'preserveAspectRatio="{par}"')
    attrs.append(f'data-source-page="{source_page}"')
    return f"<svg {' '.join(attrs)}>{body}</svg>"


def process_site(site_dir: Path, quiet: bool = False) -> dict:
    """Walk every page under site_dir, extract <symbol> defs into sprites/."""
    sprites_dir = site_dir / "sprites"
    sprites_dir.mkdir(exist_ok=True)

    # id -> {"viewBox": ..., "preserveAspectRatio": ..., "body": ..., "sha1": ...,
    #         "source_pages": set(), "first_page": ...}
    symbols: dict[str, dict] = {}
    use_refs: dict[str, int] = defaultdict(int)
    pages_with_symbols = 0

    page_dirs = sorted(
        p for p in site_dir.iterdir()
        if p.is_dir() and p.name != "sprites"
    )

    for page_dir in page_dirs:
        full_path = page_dir / "full.html"
        if not full_path.exists():
            continue
        try:
            html = full_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        page_had_symbol = False
        for sym_id, viewbox, par, body in iter_symbols(html):
            page_had_symbol = True
            sha = hashlib.sha1(body.encode("utf-8", "ignore")).hexdigest()
            existing = symbols.get(sym_id)
            if existing is None:
                symbols[sym_id] = {
                    "viewBox": viewbox,
                    "preserveAspectRatio": par,
                    "body": body,
                    "sha1": sha,
                    "source_pages": {page_dir.name},
                    "first_page": page_dir.name,
                }
            else:
                existing["source_pages"].add(page_dir.name)
                # Different bodies for the same id (rare) — keep the first,
                # but note the divergence so a human can spot it.
                if existing["sha1"] != sha:
                    existing.setdefault("variant_sha1s", set()).add(sha)

        for ref in iter_use_refs(html):
            use_refs[ref] += 1

        if page_had_symbol:
            pages_with_symbols += 1

    # write each symbol once
    written = 0
    manifest_symbols = []
    for sym_id in sorted(symbols):
        info = symbols[sym_id]
        out_path = sprites_dir / f"{safe_filename(sym_id)}.svg"
        svg = wrap_symbol_as_svg(
            info["viewBox"], info["preserveAspectRatio"],
            info["body"], info["first_page"],
        )
        # idempotent: only rewrite if content differs
        new_bytes = svg.encode("utf-8")
        if not out_path.exists() or out_path.read_bytes() != new_bytes:
            out_path.write_bytes(new_bytes)
            written += 1
        entry = {
            "id": sym_id,
            "viewBox": info["viewBox"],
            "file": f"sprites/{out_path.name}",
            "sha1": info["sha1"],
            "size": len(new_bytes),
            "use_count": use_refs.get(sym_id, 0),
            "source_pages": sorted(info["source_pages"]),
        }
        if info["preserveAspectRatio"]:
            entry["preserveAspectRatio"] = info["preserveAspectRatio"]
        if "variant_sha1s" in info:
            entry["variant_sha1s"] = sorted(info["variant_sha1s"])
        manifest_symbols.append(entry)

    unmatched = sorted(ref for ref in use_refs if ref not in symbols)

    manifest = {
        "site": site_dir.name,
        "n_symbols": len(symbols),
        "n_pages_with_sprites": pages_with_symbols,
        "n_pages_scanned": len(page_dirs),
        "n_use_refs": sum(use_refs.values()),
        "n_use_refs_unmatched": len(unmatched),
        "symbols": manifest_symbols,
        "use_refs_unmatched": unmatched[:200],  # cap for readability
    }
    (site_dir / "_sprites.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False)
    )

    if not quiet:
        print(
            f"{site_dir.name:<30} "
            f"pages={pages_with_symbols:>3}/{len(page_dirs):<3} "
            f"symbols={len(symbols):>4} "
            f"new_files={written:>4} "
            f"use_refs={sum(use_refs.values()):>4} "
            f"unmatched={len(unmatched):>3}"
        )

    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("site", nargs="?", help="single site name under snapshots/")
    ap.add_argument("--all", action="store_true",
                    help="process every site under snapshots/")
    ap.add_argument("--quiet", action="store_true",
                    help="only print summary line per site")
    args = ap.parse_args()

    if not args.site and not args.all:
        ap.error("pass a site name or --all")

    if args.all:
        sites = sorted(p for p in ROOT.iterdir() if p.is_dir())
    else:
        site_dir = ROOT / args.site
        if not site_dir.is_dir():
            print(f"[error] no such site: {site_dir}", file=sys.stderr)
            return 1
        sites = [site_dir]

    grand_total_symbols = 0
    grand_total_sites_with_sprites = 0
    for site_dir in sites:
        manifest = process_site(site_dir, quiet=args.quiet)
        grand_total_symbols += manifest["n_symbols"]
        if manifest["n_symbols"]:
            grand_total_sites_with_sprites += 1

    if args.all:
        print(
            f"\n[total] {grand_total_sites_with_sprites}/{len(sites)} sites "
            f"have sprites, {grand_total_symbols} symbols extracted"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
