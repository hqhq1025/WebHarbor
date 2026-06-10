"""Wave 2 entity-driven image harvest for the huggingface mirror.

For top-N entities (by likes_count), download a real image from upstream
huggingface.co and save into static/images/{models,datasets,spaces}/.

Sources, in order:
  1. og:image (social-thumbnail) — `https://cdn-thumbnails.huggingface.co/social-thumbnails/{kind}/{slug}.png`
  2. org/user avatar — `/api/organizations/{owner}/overview` -> avatarUrl,
     fallback `/api/users/{owner}/overview`
  3. First <img src> in the rendered README HTML

The DB is NOT modified. Images are placed at
  static/images/{models|datasets|spaces}/<owner>__<name>.jpg
re-encoded to <=200KB JPEG.
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "instance_seed" / "hf.db"
IMG_ROOT = ROOT / "static" / "images"

KIND_TO_DIR = {"model": "models", "dataset": "datasets", "space": "spaces"}
KIND_TO_THUMB_SEG = {"model": "models", "dataset": "datasets", "space": "spaces"}

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
MIN_BYTES = 5 * 1024
MAX_BYTES = 200 * 1024
TIMEOUT = 20


def http_get(url: str, accept: str = "*/*") -> tuple[int, bytes, dict]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": accept, "Accept-Encoding": "identity"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = r.read()
            return r.status, data, dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, b"", dict(getattr(e, "headers", {}) or {})
    except Exception:
        return 0, b"", {}


# ------------------- source discovery -------------------


def thumbnail_url(kind: str, slug: str) -> str:
    seg = KIND_TO_THUMB_SEG[kind]
    return f"https://cdn-thumbnails.huggingface.co/social-thumbnails/{seg}/{slug}.png"


_OG_RE = re.compile(
    rb'<meta\s+property="og:image"\s+content="([^"]+)"', re.IGNORECASE
)
_FIRST_IMG_RE = re.compile(
    rb'<img[^>]+src="(https?://[^"]+\.(?:png|jpe?g|webp|gif))"', re.IGNORECASE
)


def parse_og_image(html: bytes) -> str | None:
    m = _OG_RE.search(html)
    return m.group(1).decode("utf-8", "ignore") if m else None


def parse_first_img(html: bytes) -> str | None:
    m = _FIRST_IMG_RE.search(html)
    return m.group(1).decode("utf-8", "ignore") if m else None


_AVATAR_CACHE: dict[str, str | None] = {}


def org_avatar_url(owner: str) -> str | None:
    if owner in _AVATAR_CACHE:
        return _AVATAR_CACHE[owner]
    for path in (f"/api/organizations/{owner}/overview", f"/api/users/{owner}/overview"):
        status, data, _ = http_get(f"https://huggingface.co{path}", accept="application/json")
        if status == 200 and data:
            try:
                import json
                blob = json.loads(data.decode("utf-8", "ignore"))
                url = blob.get("avatarUrl") or blob.get("avatar_url")
                if url:
                    _AVATAR_CACHE[owner] = url
                    return url
            except Exception:
                pass
    _AVATAR_CACHE[owner] = None
    return None


# ------------------- image processing -------------------


def reencode(data: bytes) -> bytes | None:
    """Open image, convert to JPEG within MAX_BYTES."""
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:
        return None
    if im.mode in ("P", "RGBA", "LA"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        if im.mode == "P":
            im = im.convert("RGBA")
        bg.paste(im, mask=im.split()[-1] if "A" in im.mode else None)
        im = bg
    elif im.mode != "RGB":
        im = im.convert("RGB")
    # max dim 1200
    max_side = 1200
    if max(im.size) > max_side:
        r = max_side / max(im.size)
        im = im.resize((int(im.size[0] * r), int(im.size[1] * r)), Image.LANCZOS)
    # iterate quality
    for q in (88, 80, 72, 64, 56, 48, 40):
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=q, optimize=True, progressive=True)
        if buf.tell() <= MAX_BYTES:
            return buf.getvalue()
    # last resort: downscale further
    im = im.resize((im.size[0] // 2, im.size[1] // 2), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=70, optimize=True, progressive=True)
    return buf.getvalue() if buf.tell() <= MAX_BYTES else None


def download_image(url: str) -> bytes | None:
    status, data, headers = http_get(url, accept="image/*")
    if status != 200 or not data:
        return None
    ctype = (headers.get("Content-Type") or headers.get("content-type") or "").lower()
    if "image" not in ctype and not data[:4] in (b"\x89PNG", b"\xff\xd8\xff\xe0", b"\xff\xd8\xff\xe1"):
        # accept anyway if Pillow can decode
        pass
    if len(data) < MIN_BYTES and "svg" not in ctype:
        # very small raster -> skip
        return None
    return data


# ------------------- per-entity worker -------------------


def safe_filename(slug: str) -> str:
    return slug.replace("/", "__").replace(":", "_") + ".jpg"


def harvest_entity(kind: str, slug: str) -> tuple[str, str]:
    """Return (slug, status). status in {'ok-og','ok-readme','ok-avatar','exists','fail-page','fail-img'}."""
    out_dir = IMG_ROOT / KIND_TO_DIR[kind]
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / safe_filename(slug)
    if dest.exists() and dest.stat().st_size >= MIN_BYTES:
        return slug, "exists"

    owner = slug.split("/", 1)[0]

    # source 1: predictable og:image / social-thumbnail
    raw = download_image(thumbnail_url(kind, slug))
    src = "og"

    # source 2: parse page for og:image / first README img
    if not raw:
        status, page, _ = http_get(f"https://huggingface.co/{slug}", accept="text/html")
        if status == 200 and page:
            og = parse_og_image(page)
            if og:
                raw = download_image(og)
                src = "og"
            if not raw:
                first = parse_first_img(page)
                if first:
                    raw = download_image(first)
                    src = "readme"
        else:
            # page 404 -> try avatar as best-effort
            pass

    # source 3: org avatar fallback
    if not raw:
        av = org_avatar_url(owner)
        if av:
            raw = download_image(av)
            src = "avatar"

    if not raw:
        return slug, "fail-img"

    out = reencode(raw)
    if not out or len(out) < MIN_BYTES:
        return slug, "fail-img"
    dest.write_bytes(out)
    return slug, f"ok-{src}"


# ------------------- main -------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", type=int, default=200)
    ap.add_argument("--datasets", type=int, default=100)
    ap.add_argument("--spaces", type=int, default=100)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--throttle", type=float, default=0.15, help="sleep between submits")
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    plan = []
    for kind, n in (("model", args.models), ("dataset", args.datasets), ("space", args.spaces)):
        for (slug,) in con.execute(
            "SELECT slug FROM repositories WHERE repo_type=? ORDER BY likes_count DESC LIMIT ?",
            (kind, n),
        ):
            plan.append((kind, slug))
    con.close()
    print(f"plan: {len(plan)} entities ({args.models}m + {args.datasets}d + {args.spaces}s)", flush=True)

    stats: Counter[str] = Counter()
    fails: dict[str, list[str]] = {"model": [], "dataset": [], "space": []}
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {}
        for i, (kind, slug) in enumerate(plan):
            futs[ex.submit(harvest_entity, kind, slug)] = (kind, slug)
            time.sleep(args.throttle)
        done = 0
        for f in as_completed(futs):
            kind, slug = futs[f]
            try:
                _, status = f.result()
            except Exception as e:
                status = f"fail-exc:{type(e).__name__}"
            stats[f"{kind}:{status}"] += 1
            if status.startswith("fail"):
                fails[kind].append(slug)
            done += 1
            if done % 25 == 0 or done == len(plan):
                print(f"  {done}/{len(plan)}  {dict(stats)}", flush=True)
    print(f"done in {time.time() - t0:.1f}s", flush=True)
    print("\n== final stats ==")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    for kind, lst in fails.items():
        if lst:
            print(f"\nfailed {kind} ({len(lst)}): {lst[:8]}{' ...' if len(lst) > 8 else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
