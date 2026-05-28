#!/usr/bin/env python3
"""Detect missing composite indexes — gotcha #H catcher.

Loads a site's Flask app, walks every SQLAlchemy model's `__table_args__`,
extracts Index() declarations, then checks `sqlite_master` to see which
ones are actually present in the live `instance/<site>.db`.

Background (perf-optimize SKILL §H, repeated 6× in 2026-05-28 session):
`db.create_all()` only does `CREATE TABLE IF NOT EXISTS`. When a new Index
declaration is added to `__table_args__` on an EXISTING table, `create_all`
silently skips it — `sqlite_master` shows no such index, SQLite plans
queries with the bare single-column index + TEMP B-TREE sort.

Real impact: 459k-row HuggingFace `Repository.query.order_by(downloads desc)`
ran in 633ms vs 4.5ms after adding the missing composite (141× speedup).

Run:
    python3 tools/audit/check_indexes.py <site>

Output: 2-section markdown showing declared-but-missing vs orphaned indexes,
plus copy-paste boot snippet to fix the missing ones.
"""
from __future__ import annotations
import argparse
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

WEBHARBOR = Path('/home/v-haoqiwang/repos/WebHarbor')


def db_path(site: str) -> Path:
    DB_NAME = {'huggingface': 'hf', 'github': 'github_mirror', 'google_map': 'gmaps'}
    name = DB_NAME.get(site, site)
    return WEBHARBOR / 'sites' / site / 'instance' / f'{name}.db'


def declared_indexes(site: str) -> dict[str, list[str]]:
    """Parse app.py for Index() declarations in __table_args__.

    Returns {index_name: [column_names]} from STATIC parsing — doesn't
    import the Flask app (avoids dependency hell + side effects).
    """
    import re
    out: dict[str, list[str]] = {}
    for py_path in (WEBHARBOR / 'sites' / site).rglob('*.py'):
        try:
            txt = py_path.read_text()
        except Exception:
            continue
        # match Index('ix_name', Model.col, Model.col2.desc(), ...)
        for m in re.finditer(
            r"""Index\(\s*['"]([a-zA-Z0-9_]+)['"]\s*,\s*([^)]+?)\)""",
            txt, re.DOTALL,
        ):
            name = m.group(1)
            cols_raw = m.group(2)
            # extract column refs like Repository.downloads or Repository.downloads.desc()
            cols = re.findall(r'([A-Z][a-zA-Z]+\.[a-z_]+)', cols_raw)
            if not cols:
                # fallback to bare names
                cols = re.findall(r"[a-z_]+", cols_raw)
            out[name] = cols
    return out


def actual_indexes(site: str) -> dict[str, list[str]]:
    """Read sqlite_master for actual indexes + their column lists."""
    p = db_path(site)
    if not p.exists():
        return {}
    c = sqlite3.connect(str(p))
    out: dict[str, list[str]] = {}
    for name, tbl in c.execute(
        "SELECT name, tbl_name FROM sqlite_master "
        "WHERE type='index' AND name NOT LIKE 'sqlite_%'"
    ):
        # PRAGMA index_info gives the columns
        cols = [r[2] for r in c.execute(f'PRAGMA index_info("{name}")')]
        out[name] = cols
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('site')
    args = ap.parse_args()

    declared = declared_indexes(args.site)
    actual = actual_indexes(args.site)

    declared_names = set(declared.keys())
    actual_names = set(actual.keys())

    missing = declared_names - actual_names
    orphaned = actual_names - declared_names

    print(f'# {args.site} index audit\n')
    print(f'declared: {len(declared)}  /  actual: {len(actual)}  /  '
          f'**missing**: {len(missing)}  /  orphaned: {len(orphaned)}\n')

    if missing:
        print('## ⚠️ Declared but MISSING (gotcha #H bites!)\n')
        for name in sorted(missing):
            cols = declared[name]
            print(f'- `{name}` — columns: {cols}')
        print('\n### Fix: add to `_ensure_indexes()` boot block:\n')
        print('```python')
        print('def _ensure_indexes():')
        for name in sorted(missing):
            cols = declared[name]
            cols_src = ', '.join(cols)
            print(f"    Index({name!r}, {cols_src}).create(checkfirst=True, bind=db.engine)")
        print("    db.session.execute(text('ANALYZE'))")
        print('')
        print('with app.app_context():')
        print('    _ensure_indexes()')
        print('```\n')

    if orphaned:
        print('## Orphaned (in DB but not declared in app.py) — usually fine, but check\n')
        for name in sorted(orphaned)[:20]:
            cols = actual[name]
            print(f'- `{name}` — columns: {cols}')
        if len(orphaned) > 20:
            print(f'  ...and {len(orphaned)-20} more')

    if not missing and not orphaned:
        print('✅ All declared indexes present, no orphans.')

    sys.exit(1 if missing else 0)


if __name__ == '__main__':
    main()
