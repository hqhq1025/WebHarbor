#!/usr/bin/env python3
"""Build structured review data from the hand-written manual review Markdown."""
from __future__ import annotations

import json
import pathlib
import re


BASE = pathlib.Path(__file__).resolve().parent
REVIEW_DIR = BASE / "manual_review"
OUT = BASE / "review_data.js"

SLUGS = [
    "allrecipes",
    "amazon",
    "apple",
    "arxiv",
    "bbc_news",
    "booking",
    "cambridge_dictionary",
    "coursera",
    "espn",
    "github",
    "google_flights",
    "google_map",
    "google_search",
    "huggingface",
    "wolfram_alpha",
]


def clean_lines(lines: list[str]) -> str:
    text = "\n".join(lines).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def parse_bullets(text: str) -> list[str]:
    items: list[str] = []
    current: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("- "):
            if current:
                items.append(" ".join(current).strip())
            current = [line[2:].strip()]
        elif current and line.startswith("  "):
            current.append(line.strip())
        elif current and not line:
            continue
    if current:
        items.append(" ".join(current).strip())
    return items


def parse_task_table(text: str) -> list[dict]:
    rows: list[dict] = []
    for line in text.splitlines():
        if not line.startswith("| "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in {"ID", "---"} or cells[0].startswith("---"):
            continue
        if not re.fullmatch(r"[A-Za-z ]+--\d+", cells[0]):
            continue
        rows.append({"id": cells[0], "intent": cells[1], "recommendation": cells[2]})
    return rows


def parse_site(path: pathlib.Path) -> dict:
    lines = path.read_text().splitlines()
    title = lines[0].lstrip("# ").strip()
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in lines[1:]:
        if line.startswith("## "):
            if current:
                sections[current] = clean_lines(buf)
            current = line[3:].strip()
            buf = []
        else:
            buf.append(line)
    if current:
        sections[current] = clean_lines(buf)

    def section(*names: str) -> str:
        for name in names:
            if name in sections:
                return sections[name]
        return ""

    return {
        "title": title,
        "slug": path.stem,
        "infrastructure": section("Infrastructure Affordances", "基础设施能力"),
        "goodFamilies": parse_bullets(section("Good Task Families", "适合泛化的任务族")),
        "targetedFamilies": parse_bullets(section("Targeted Task Families", "站点特化场景")),
        "tasks": parse_task_table(section("Per-Task Review And Expansion Advice", "逐任务建议")),
        "gaps": parse_bullets(section("Infrastructure Gaps Before Scaling", "扩容前需要补的基础设施")),
    }


def main() -> None:
    payload = {
        "sites": {slug: parse_site(REVIEW_DIR / f"{slug}.md") for slug in SLUGS},
    }
    OUT.write_text("window.MANUAL_REVIEW_DATA = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n")
    total = sum(len(site["tasks"]) for site in payload["sites"].values())
    print(f"wrote {OUT} with {len(payload['sites'])} sites and {total} task review rows")


if __name__ == "__main__":
    main()
