#!/usr/bin/env python3
"""download_samples.py — Asset downloader proof-of-capability.

Reads _audio_urls.jsonl / _video_urls.jsonl / _icons.jsonl / _animations.jsonl /
_image_urls.jsonl and downloads up to N samples per dimension into
snapshots/<site>/_proof_samples/<dim>/.

Goal: prove we can actually fetch the catalogued resources. Not for bulk archival.

Output: snapshots/<site>/_proof_samples/<dim>/<hash>.<ext>

Usage:
  python3 download_samples.py <site> [--per-dim 3] [--ua "..."]
  python3 download_samples.py --all [--per-dim 3]
"""
import argparse
import hashlib
import json
import os
import subprocess
import urllib.parse
from pathlib import Path

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()

DEFAULT_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

DIM_FILES = {
    "audio": "_audio_urls.jsonl",
    "video": "_video_urls.jsonl",
    "icon":  "_icons.jsonl",
    "anim":  "_animations.jsonl",
    "image": "_image_urls.jsonl",
}


def extract_url(rec: dict, dim: str) -> str:
    if dim == "icon":
        return rec.get("href") or ""
    return rec.get("url") or rec.get("src") or ""


def is_fetchable(url: str) -> bool:
    return bool(url) and (url.startswith("http://") or url.startswith("https://"))


def is_embed_skip(url: str) -> bool:
    """Skip player embeds for video (we can't download an iframe's stream simply)."""
    u = url.lower()
    return any(h in u for h in ("youtube.com/embed", "player.vimeo.com",
                                  "youtube-nocookie", "youtube.com/watch"))


def url_to_path(url: str, out_dir: Path) -> Path:
    h = hashlib.md5(url.encode()).hexdigest()[:12]
    parsed = urllib.parse.urlparse(url)
    ext = os.path.splitext(parsed.path)[1][:6] or ".bin"
    return out_dir / f"{h}{ext}"


def download(url: str, out_path: Path, referer: str, ua: str, max_bytes: int = 5_000_000) -> bool:
    if out_path.exists():
        return True
    try:
        result = subprocess.run(
            ["curl", "-sSLm", "20",
             "--max-filesize", str(max_bytes),
             "-r", f"0-{max_bytes-1}",  # Range request — partial OK for huge videos
             "-A", ua,
             "-H", f"Referer: {referer}",
             "-o", str(out_path), url],
            capture_output=True, timeout=25,
        )
        if not out_path.exists() or out_path.stat().st_size <= 100:
            if out_path.exists():
                out_path.unlink()
            return False
        # R03 imdb fix: validate content isn't an XML/HTML error response
        # (S3 MissingKey, CDN access denied, soft-404 pages served with 200 OK).
        # Read first 32 bytes and reject if starts with text-like markers.
        with out_path.open("rb") as fh:
            head = fh.read(32)
        if not head:
            out_path.unlink()
            return False
        lo = head.lstrip()[:16].lower()
        # Reject XML / HTML / JSON error blobs
        if (lo.startswith(b"<?xml") or lo.startswith(b"<!doctype")
                or lo.startswith(b"<html") or lo.startswith(b"<error")
                or lo.startswith(b'{"error') or lo.startswith(b'{"message')
                or lo.startswith(b'{"code') or b"missingkey" in head.lower()
                or b"accessdenied" in head.lower()):
            out_path.unlink()
            return False
        return True
    except Exception:
        return False


def process_site(site_dir: Path, per_dim: int, ua: str) -> dict:
    referer = f"https://{site_dir.name.replace('_', '.')}/"
    out_root = site_dir / "_proof_samples"
    out_root.mkdir(exist_ok=True)
    results: dict[str, dict] = {}

    # R02 fix: per-dimension max-bytes (video can be ≥10MB, others stay small)
    DIM_MAX_BYTES = {
        "audio": 5_000_000,
        "video": 20_000_000,  # was 5MB → 20MB; ESPN .mp4 typically 10-15MB
        "icon":  500_000,
        "anim":  5_000_000,
        "image": 2_000_000,
    }

    for dim, fname in DIM_FILES.items():
        p = site_dir / fname
        if not p.exists():
            results[dim] = {"have_jsonl": False, "tried": 0, "ok": 0}
            continue
        out_dim = out_root / dim
        out_dim.mkdir(exist_ok=True)
        # R02 fix: collect MORE candidates than per_dim, then download until
        # we hit per_dim successes. Avoids 0/N when top candidates are ads,
        # hot-link blocked, or signed URLs that already expired.
        # Also prefer same-origin (page URL netloc) for image dim to dodge
        # ad-network tracking pixels (drugs_com case).
        candidate_limit = per_dim * 8
        candidates: list[str] = []
        seen: set[str] = set()
        same_origin: list[str] = []
        other_origin: list[str] = []
        host = site_dir.name.replace("_", ".")
        with p.open() as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                u = extract_url(rec, dim)
                if not is_fetchable(u):
                    continue
                if dim == "video" and is_embed_skip(u):
                    continue
                if u in seen:
                    continue
                seen.add(u)
                # rank: same-origin first (image dim especially)
                if host in u:
                    same_origin.append(u)
                else:
                    other_origin.append(u)
                if len(seen) >= candidate_limit:
                    break
        candidates = same_origin + other_origin
        tried = 0
        ok = 0
        fails: list[str] = []
        cap = DIM_MAX_BYTES.get(dim, 5_000_000)
        for url in candidates:
            if ok >= per_dim:
                break
            tried += 1
            out_path = url_to_path(url, out_dim)
            if download(url, out_path, referer, ua, max_bytes=cap):
                ok += 1
            else:
                fails.append(url[:120])
        results[dim] = {
            "have_jsonl": True,
            "available_unique": len(seen),
            "tried": tried,
            "ok": ok,
            "max_bytes": cap,
            "fails": fails[:3],
            "out_dir": str(out_dim),
        }

    # write a manifest
    (out_root / "manifest.json").write_text(json.dumps(results, indent=2))
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--per-dim", type=int, default=3, help="samples per dimension")
    ap.add_argument("--ua", default=DEFAULT_UA)
    args = ap.parse_args()
    if args.all:
        targets = [d for d in sorted(ROOT.iterdir()) if d.is_dir()]
    elif args.site:
        targets = [ROOT / args.site]
    else:
        ap.error("provide <site> or --all")
        return
    print(f"{'site':<30} {'audio':>10} {'video':>10} {'icon':>10} {'anim':>10} {'image':>10}")
    print("-" * 80)
    for site_dir in targets:
        if not site_dir.exists():
            print(f"{site_dir.name:<30}  MISSING")
            continue
        r = process_site(site_dir, args.per_dim, args.ua)
        def fmt(d):
            x = r.get(d, {})
            if not x.get("have_jsonl"):
                return "n/a"
            return f"{x['ok']}/{x['tried']}"
        print(f"{site_dir.name:<30} {fmt('audio'):>10} {fmt('video'):>10} {fmt('icon'):>10} {fmt('anim'):>10} {fmt('image'):>10}")


if __name__ == "__main__":
    main()
