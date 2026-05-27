#!/usr/bin/env python3
"""
Replace placeholder map-snippet images in place_galleries.json with real Wikipedia
photos for each place.

Strategy:
- For every slug in place_galleries.json
  1. Search Wikipedia for the page (slug -> title-cased name)
  2. Fetch the page's image list (action=parse, prop=images)
  3. Resolve image File: pages to direct URLs (only JPEG/PNG >=600px wide)
  4. Download top 3-4 distinct images, save as
     static/images/places/<slug>/wiki_NN.jpg
  5. Assign one distinct image per section in place_galleries.json
- On any failure for a slug, keep its existing images and record the slug in a
  fallback report.
"""
import json
import os
import pathlib
import sys
import time
from typing import List, Optional, Tuple

import requests

UA = {
    "User-Agent": "WebHarborBuilder/1.0 (research site mirror; haoqiwang@unc.edu)"
}

ROOT = pathlib.Path(__file__).parent
GAL_JSON = ROOT / "place_galleries.json"
IMG_ROOT = ROOT / "static" / "images" / "places"
REPORT = ROOT / "scrape_real_place_photos.report.json"

API = "https://en.wikipedia.org/w/api.php"

SKIP_TOKENS = (
    "icon",
    "logo",
    "commons-logo",
    "wiki.png",
    "wikimedia",
    "flag_of_",
    "question_book",
    "edit-clear",
    "padlock",
    "symbol_",
    "arrow_",
    "translation",
    "disambig",
    "-logo.",
    "_logo.",
    "red_pog",
    "green_pog",
    "blue_pog",
    "location_dot",
    "globe",
    "wikidata",
    "pictograms",
    "wikisource",
    "wiktionary",
    "osm_location_map",
    "speakerlink",
    "ambox",
    "redirect_arrow",
    "increase2",
    "decrease",
    "yes_check",
    "x_mark",
    "office-book",
    "search_question",
    "scale_of_justice",
)


def _get_json(params: dict, retries: int = 5) -> dict:
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(API, params=params, headers=UA, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last = e
            time.sleep(0.6 * (attempt + 1))
    raise RuntimeError(f"API failed after {retries} retries: {last}")


def slug_to_query(slug: str) -> str:
    return slug.replace("-", " ")


def search_page(query: str) -> Optional[str]:
    data = _get_json({
        "action": "query", "format": "json", "list": "search",
        "srsearch": query, "srlimit": 3,
    })
    hits = data.get("query", {}).get("search", [])
    return hits[0]["title"] if hits else None


def lead_image_filename(page_title: str) -> Optional[str]:
    """Return the page's primary infobox image filename, if any."""
    data = _get_json({
        "action": "query", "format": "json", "titles": page_title,
        "prop": "pageimages", "piprop": "name",
    })
    for p in data.get("query", {}).get("pages", {}).values():
        nm = p.get("pageimage")
        if nm:
            return nm
    return None


def page_image_filenames(page_title: str) -> List[str]:
    data = _get_json({
        "action": "parse", "format": "json", "page": page_title,
        "prop": "images",
    })
    out = []
    for img in data.get("parse", {}).get("images", []):
        low = img.lower()
        if not (low.endswith(".jpg") or low.endswith(".jpeg") or low.endswith(".png")):
            continue
        if any(tok in low for tok in SKIP_TOKENS):
            continue
        out.append(img)
    return out


def resolve_image(filename: str, min_w: int = 500, thumb_w: int = 1024) -> Optional[Tuple[str, int, int, str]]:
    """Return (thumb_url, original_w, original_h, mime) — using a width-capped
    thumbnail to avoid 100MB originals."""
    data = _get_json({
        "action": "query", "format": "json", "titles": f"File:{filename}",
        "prop": "imageinfo", "iiprop": "url|size|mime",
        "iiurlwidth": thumb_w,
    })
    for p in data.get("query", {}).get("pages", {}).values():
        ii = p.get("imageinfo", [])
        if not ii:
            continue
        info = ii[0]
        mime = info.get("mime", "")
        if mime not in ("image/jpeg", "image/png"):
            continue
        w = info.get("width", 0)
        h = info.get("height", 0)
        if w < min_w:
            continue
        # Skip true panoramas / extreme portrait but keep typical landscape variation
        if h == 0 or w / h > 6 or h / w > 4:
            continue
        thumb = info.get("thumburl") or info.get("url")
        return thumb, w, h, mime
    return None


def download(url: str, dest: pathlib.Path, min_bytes: int = 8000, max_bytes: int = 20_000_000, retries: int = 3) -> bool:
    """Stream download with a hard cap to avoid mega-files."""
    for attempt in range(retries):
        try:
            with requests.get(url, headers=UA, timeout=30, stream=True) as r:
                if r.status_code != 200:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                chunks = []
                total = 0
                ok = True
                for chunk in r.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > max_bytes:
                        ok = False
                        break
                    chunks.append(chunk)
                if not ok:
                    return False
                if total < min_bytes:
                    return False
                dest.write_bytes(b"".join(chunks))
                return True
        except Exception:
            time.sleep(0.5 * (attempt + 1))
    return False


def fetch_real_photos(slug: str, want: int = 4) -> List[str]:
    """Return list of relative paths actually downloaded for this slug."""
    name = slug_to_query(slug)
    candidates: List[Tuple[str, str, str]] = []  # (filename, url, ext)

    # Try multiple search queries until enough candidates
    for q in (name, f"{name} landmark", f"{name} attraction"):
        try:
            page = search_page(q)
        except Exception as e:
            print(f"  search fail {slug!r} q={q!r}: {e}", file=sys.stderr)
            continue
        if not page:
            continue
        # Lead image first (infobox/pageimage)
        ordered = []
        try:
            lead = lead_image_filename(page)
        except Exception:
            lead = None
        if lead:
            ordered.append(lead)
        try:
            files = page_image_filenames(page)
        except Exception as e:
            print(f"  page imgs fail {page!r}: {e}", file=sys.stderr)
            continue
        for fn in files:
            if fn == lead:
                continue
            ordered.append(fn)
        for fn in ordered:
            time.sleep(0.05)
            try:
                info = resolve_image(fn)
            except Exception:
                continue
            if not info:
                continue
            url, w, h, mime = info
            ext = ".jpg" if mime == "image/jpeg" else ".png"
            candidates.append((fn, url, ext))
            if len(candidates) >= want * 2:
                break
        if len(candidates) >= want:
            break

    if not candidates:
        return []

    out_dir = IMG_ROOT / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    saved: List[str] = []
    seen_urls = set()
    for i, (fn, url, ext) in enumerate(candidates):
        if url in seen_urls:
            continue
        seen_urls.add(url)
        dest = out_dir / f"wiki_{len(saved):02d}{ext}"
        if download(url, dest):
            saved.append(f"/static/images/places/{slug}/{dest.name}")
            if len(saved) >= want:
                break
        time.sleep(0.15)
    return saved


def main():
    galleries = json.loads(GAL_JSON.read_text())
    n_total = len(galleries)
    report = {"ok": [], "partial": [], "fail": []}

    only = set(sys.argv[1:])  # optional slug filter for testing

    for idx, (slug, sections) in enumerate(galleries.items(), 1):
        if only and slug not in only:
            continue
        n_sections = len(sections)
        print(f"[{idx}/{n_total}] {slug} (sections={n_sections}) ", end="", flush=True)
        t0 = time.time()
        photos = fetch_real_photos(slug, want=max(3, n_sections))
        dt = time.time() - t0
        if len(photos) >= n_sections:
            # one distinct image per section
            for i, sec in enumerate(sections):
                sec["images"] = [photos[i % len(photos)]]
            report["ok"].append({"slug": slug, "n_photos": len(photos), "secs": dt})
            print(f"OK n={len(photos)} {dt:.1f}s")
        elif photos:
            # not enough — cycle what we have across sections
            for i, sec in enumerate(sections):
                sec["images"] = [photos[i % len(photos)]]
            report["partial"].append({"slug": slug, "n_photos": len(photos), "needed": n_sections, "secs": dt})
            print(f"PARTIAL n={len(photos)}/{n_sections} {dt:.1f}s")
        else:
            for sec in sections:
                sec.setdefault("_no_real_photo", True)
            report["fail"].append({"slug": slug, "secs": dt})
            print(f"FAIL {dt:.1f}s")

        # Throttle between places
        time.sleep(0.4)

        # Periodic save so we don't lose progress
        if idx % 20 == 0:
            GAL_JSON.write_text(json.dumps(galleries, indent=2, ensure_ascii=False))
            REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    GAL_JSON.write_text(json.dumps(galleries, indent=2, ensure_ascii=False))
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print(f"\nDONE: ok={len(report['ok'])} partial={len(report['partial'])} fail={len(report['fail'])}")


if __name__ == "__main__":
    main()
