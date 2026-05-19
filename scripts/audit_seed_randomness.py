#!/usr/bin/env python3
"""Audit random/time/hash usage that can affect WebHarbor seed fixtures."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PATTERNS = {
    "random_call": re.compile(r"\brandom\.[A-Za-z_]+\("),
    "python_hash": re.compile(r"(?<!password_)\bhash\("),
    "sql_random": re.compile(r"func\.random\("),
    "utcnow": re.compile(r"datetime\.utcnow\("),
    "today": re.compile(r"\bdate\.today\("),
    "secrets": re.compile(r"\bsecrets\."),
}

IGNORE_PARTS = {"__pycache__", "instance", "instance_seed", ".cache"}


def classify(path: Path, line_no: int, line: str) -> str:
    rel = path.relative_to(ROOT)
    text = path.read_text(errors="ignore")
    before = "\n".join(text.splitlines()[: max(0, line_no - 1)])
    if path.name == "seed_data.py":
        return "seed-time"
    if "def seed_database" in before or "def seed_benchmark_users" in before:
        if "if __name__" not in before.split("def seed_database")[-1]:
            return "seed-time"
    if "order_by(func.random())" in line:
        return "runtime-display"
    if "secrets." in line or "token_hex" in line:
        return "security/runtime"
    if "date.today()" in line or "datetime.utcnow()" in line:
        return "time-dependent"
    if str(rel).endswith("_health.py") or "random_user" in line:
        return "test-helper"
    return "runtime-or-unknown"


def iter_python_files():
    for path in sorted((ROOT / "sites").rglob("*.py")):
        if any(part in IGNORE_PARTS for part in path.parts):
            continue
        yield path


def main():
    rows = []
    totals = defaultdict(lambda: defaultdict(int))
    for path in iter_python_files():
        rel = path.relative_to(ROOT)
        for idx, line in enumerate(path.read_text(errors="ignore").splitlines(), start=1):
            for kind, pattern in PATTERNS.items():
                if pattern.search(line):
                    stage = classify(path, idx, line)
                    rows.append((str(rel), idx, kind, stage, line.strip()))
                    site = rel.parts[1] if len(rel.parts) > 1 else rel.parts[0]
                    totals[site][kind] += 1
                    totals[site][f"stage:{stage}"] += 1

    print("# Seed Randomness Audit\n")
    print("## Summary by Site\n")
    print("| Site | random | hash | SQL random | utcnow | today | secrets | seed-time | runtime-display | time-dependent |")
    print("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for site in sorted(totals):
        t = totals[site]
        print(
            f"| {site} | {t['random_call']} | {t['python_hash']} | {t['sql_random']} | "
            f"{t['utcnow']} | {t['today']} | {t['secrets']} | "
            f"{t['stage:seed-time']} | {t['stage:runtime-display']} | {t['stage:time-dependent']} |"
        )

    print("\n## Detailed Findings\n")
    print("| File | Line | Kind | Stage | Code |")
    print("| --- | ---: | --- | --- | --- |")
    for rel, line_no, kind, stage, code in rows:
        escaped = code.replace("|", "\\|")
        print(f"| `{rel}` | {line_no} | {kind} | {stage} | `{escaped}` |")


if __name__ == "__main__":
    main()
