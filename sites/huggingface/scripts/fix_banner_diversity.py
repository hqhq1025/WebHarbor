"""Diversify repositories.banner_url.

Before this fix, 41493/456380 (9%) repositories shared the same
`/static/images/repos/model_sd3_03.png`, and only 11 distinct images were
in rotation across all 456k rows — every banner image was reused ~41k times.

This re-maps each repository to a real upstream image already on disk under
`static/images/{models,datasets,spaces}/`, picked deterministically from the
slug hash. That pool is ~428 distinct real-upstream images (originally
downloaded by scripts/wave2_real_images.py), giving each banner a top-frequency
well under 5%.

Writes to instance_seed/hf.db; caller is expected to `cp` it onto
instance/hf.db (byte-id reset) and into the running container afterwards.
"""
from __future__ import annotations

import collections
import hashlib
import pathlib
import shutil
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SEED_DB = ROOT / "instance_seed" / "hf.db"
INSTANCE_DB = ROOT / "instance" / "hf.db"
IMG_ROOT = ROOT / "static" / "images"

KIND_DIRS = {"model": "models", "dataset": "datasets", "space": "spaces"}


def build_pool() -> dict[str, list[str]]:
    pool: dict[str, list[str]] = {}
    for kind, sub in KIND_DIRS.items():
        d = IMG_ROOT / sub
        files = sorted(p.name for p in d.glob("*") if p.is_file() and p.stat().st_size >= 4096)
        if len(files) < 30:
            raise SystemExit(f"pool for {kind} too small: {len(files)} (<30)")
        pool[kind] = [f"/static/images/{sub}/{f}" for f in files]
        print(f"pool[{kind}] = {len(files)} files")
    return pool


def remap(con: sqlite3.Connection, pool: dict[str, list[str]]) -> None:
    rows = con.execute("SELECT id, slug, repo_type FROM repositories").fetchall()
    print(f"remapping {len(rows)} rows...")
    updates: list[tuple[str, int]] = []
    for rid, slug, repo_type in rows:
        bucket = pool.get(repo_type) or pool["model"]
        h = int(hashlib.md5(slug.encode("utf-8")).hexdigest()[:8], 16)
        new = bucket[h % len(bucket)]
        updates.append((new, rid))
    con.executemany("UPDATE repositories SET banner_url = ? WHERE id = ?", updates)
    con.commit()


def verify(con: sqlite3.Connection) -> None:
    total = con.execute("SELECT COUNT(*) FROM repositories").fetchone()[0]
    top = con.execute(
        "SELECT banner_url, COUNT(*) c FROM repositories "
        "GROUP BY banner_url ORDER BY c DESC LIMIT 5"
    ).fetchall()
    distinct = con.execute("SELECT COUNT(DISTINCT banner_url) FROM repositories").fetchone()[0]
    top_url, top_count = top[0]
    pct = top_count / total
    print(f"total={total} distinct_banners={distinct}")
    print("top 5:")
    for u, c in top:
        print(f"  {c:>6} ({c/total:.1%}) {u}")
    if pct >= 0.05:
        raise SystemExit(f"FAIL: top banner is {pct:.1%} (>=5%) — diversity too low")
    print(f"OK: top banner is {pct:.2%} (<5%)")


def main() -> int:
    if not SEED_DB.exists():
        raise SystemExit(f"seed db missing: {SEED_DB}")
    pool = build_pool()
    con = sqlite3.connect(SEED_DB)
    try:
        remap(con, pool)
        verify(con)
    finally:
        con.close()
    # byte-id reset onto instance
    if INSTANCE_DB.exists():
        shutil.copy2(SEED_DB, INSTANCE_DB)
        print(f"copied {SEED_DB} -> {INSTANCE_DB}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
