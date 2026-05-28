#!/usr/bin/env python3
"""Survey 0-row tables across a site's mirror DB + classify state (gotcha #59).

For each empty table, grep app code + templates to determine whether it's:
  - state 1: complete stub (no routes / handlers / templates reference it)
  - state 2: partial (routes + handler + template exist, but no seed + no GUI entry)
  - state 3: fully working (refs everywhere, just no synthetic seed)

State 1 → needs full implementation
State 2 → needs seed gate + GUI entry (eventbrite/recreation_gov pattern, fast)
State 3 → optional demo seed (rotten_tomatoes pattern)

Output to stdout as Markdown table for inclusion in deepen-agent prompts.

Run:
    python3 tools/audit/survey_zero_row_tables.py <site> [--db-name <name>]
"""
from __future__ import annotations
import argparse
import re
import sqlite3
import subprocess
import sys
from pathlib import Path


WEBHARBOR = Path('/home/v-haoqiwang/repos/WebHarbor')


def find_db(site: str, db_name: str | None) -> Path:
    base = WEBHARBOR / 'sites' / site / 'instance'
    if db_name:
        p = base / f'{db_name}.db'
        if p.exists(): return p
        raise FileNotFoundError(p)
    for name in [site, 'hf', f'{site}_mirror', 'gmaps']:
        p = base / f'{name}.db'
        if p.exists():
            try:
                if sqlite3.connect(str(p)).execute("SELECT name FROM sqlite_master LIMIT 1").fetchone():
                    return p
            except sqlite3.Error:
                pass
    raise FileNotFoundError(f'no DB for {site}')


def zero_row_tables(db: Path) -> list[str]:
    c = sqlite3.connect(str(db))
    tables = [r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'alembic_%'"
    )]
    zeros = []
    for t in tables:
        try:
            n = c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            if n == 0:
                zeros.append(t)
        except sqlite3.Error:
            pass
    return zeros


def grep_refs(site: str, table: str) -> dict[str, int]:
    """Count references to `table` in app code vs templates."""
    site_dir = WEBHARBOR / 'sites' / site
    counts = {'py': 0, 'html': 0, 'examples': []}
    if not site_dir.exists():
        return counts
    # Search Python files
    pat = re.escape(table)
    try:
        out = subprocess.run(
            ['grep', '-rln', '--include=*.py', pat, str(site_dir)],
            capture_output=True, text=True, timeout=30,
        )
        counts['py'] = len([l for l in out.stdout.splitlines() if l])
    except subprocess.SubprocessError:
        pass
    try:
        out = subprocess.run(
            ['grep', '-rln', '--include=*.html', pat, str(site_dir / 'templates')],
            capture_output=True, text=True, timeout=30,
        )
        counts['html'] = len([l for l in out.stdout.splitlines() if l])
        examples = [l.split('sites/' + site + '/')[-1] for l in out.stdout.splitlines() if l]
        counts['examples'] = examples[:3]
    except subprocess.SubprocessError:
        pass
    return counts


def classify(refs: dict[str, int]) -> tuple[str, str]:
    total = refs['py'] + refs['html']
    if total == 0:
        return ('state-1', 'stub — no refs, full implementation needed')
    if refs['html'] == 0 and refs['py'] >= 1:
        return ('state-2a', 'handler exists but no template UI — surface in nav/template')
    if refs['py'] >= 1 and refs['html'] >= 1 and total <= 3:
        return ('state-2b', 'partial wiring — likely missing seed gate + secondary UI entry')
    return ('state-3', 'fully wired — needs demo seed only')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('site')
    ap.add_argument('--db-name')
    args = ap.parse_args()

    try:
        db = find_db(args.site, args.db_name)
    except FileNotFoundError as e:
        print(f'ERR: {e}', file=sys.stderr)
        sys.exit(2)

    zeros = zero_row_tables(db)
    print(f'## {args.site} — {len(zeros)} zero-row tables\n')
    if not zeros:
        print('_No zero-row tables. Site is fully seeded._')
        return

    print('| Table | py refs | html refs | State | Hint |')
    print('|---|---:|---:|---|---|')
    for t in zeros:
        refs = grep_refs(args.site, t)
        state, hint = classify(refs)
        print(f'| `{t}` | {refs["py"]} | {refs["html"]} | **{state}** | {hint} |')

    print('\n### Classification legend (gotcha #59)\n')
    print('- **state-1**: full stub. Need route + handler + template + seed.')
    print('- **state-2a**: handler exists, no template — add UI entry.')
    print('- **state-2b**: partial — add seed gate (`if Table.query.count() == 0`) + secondary entry.')
    print('- **state-3**: full wire — only synthetic seed needed.')


if __name__ == '__main__':
    main()
