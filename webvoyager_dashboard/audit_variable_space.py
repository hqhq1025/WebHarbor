#!/usr/bin/env python3
"""Audit current WebHarbor data variables from the live container and source."""
from __future__ import annotations

import json
import pathlib
import re
import sqlite3
import subprocess
from collections import Counter
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "webvoyager_dashboard"
JSON_OUT = OUT_DIR / "variable_audit.json"
HTML_OUT = OUT_DIR / "variable_audit.html"
TMP_SQL = pathlib.Path("/tmp/webharbor_variable_audit_dbs")

DISPLAY = {
    "allrecipes": "Allrecipes",
    "amazon": "Amazon",
    "apple": "Apple",
    "arxiv": "ArXiv",
    "bbc_news": "BBC News",
    "booking": "Booking",
    "cambridge_dictionary": "Cambridge Dictionary",
    "coursera": "Coursera",
    "espn": "ESPN",
    "github": "GitHub",
    "google_flights": "Google Flights",
    "google_map": "Google Map",
    "google_search": "Google Search",
    "huggingface": "Hugging Face",
    "wolfram_alpha": "Wolfram Alpha",
}

PRIMARY_TABLES = {
    "allrecipes": ["recipe", "review", "category"],
    "amazon": ["products", "reviews", "categories"],
    "apple": ["product", "support_article", "trade_in_value"],
    "arxiv": ["papers", "categories"],
    "bbc_news": ["articles", "categories"],
    "booking": ["property", "city", "landmark", "review"],
    "cambridge_dictionary": ["words", "grammar_topics", "shop_items"],
    "coursera": ["courses", "course_modules", "sub_courses", "partners", "reviews"],
    "espn": ["games", "teams", "players", "player_stats", "articles", "transactions"],
    "github": ["repository", "user", "topic", "issue"],
    "google_flights": ["flight", "airport"],
    "google_map": ["place", "city", "route", "review", "category"],
    "google_search": ["topic", "search_result", "knowledge_fact", "paa_question"],
    "huggingface": ["repositories", "authors", "tasks", "discussions"],
    "wolfram_alpha": ["computation_results", "topics", "subcategories"],
}

STATE_TABLE_KEYWORDS = [
    "cart", "wishlist", "saved", "booking", "order", "history", "favorite",
    "notebook", "library", "star", "watch", "follow", "alert", "collection",
    "enrollment", "meal", "shopping", "timeline", "trip",
]

FILTER_NAME_HINTS = [
    "category", "type", "status", "rating", "price", "date", "year", "month",
    "city", "country", "brand", "license", "language", "task", "library",
    "sort", "color", "size", "stars", "review", "duration", "airline",
    "origin", "destination", "conference", "division", "position", "sport",
    "amenity", "wifi", "breakfast", "parking", "pool", "free", "tag",
]


def run(cmd: list[str], cwd: pathlib.Path | None = None) -> str:
    return subprocess.check_output(cmd, cwd=str(cwd) if cwd else None, text=True)


def extract_request_vars(site: str) -> dict:
    app = ROOT / "sites" / site / "app.py"
    txt = app.read_text(errors="ignore") if app.exists() else ""
    return {
        "args": sorted(set(re.findall(r"request\.args\.get\(['\"]([^'\"]+)", txt))),
        "forms": sorted(set(re.findall(r"request\.form\.get\(['\"]([^'\"]+)", txt))),
        "json": sorted(set(re.findall(r"(?:data|payload)\.get\(['\"]([^'\"]+)", txt))),
        "routes": len(re.findall(r"@app\.route\(", txt)),
        "random_hits": len(re.findall(r"\brandom\b|func\.random|_func\.random|shuffle\(", txt)),
        "date_hits": len(re.findall(r"datetime\.now|datetime\.utcnow|date\.today|utcnow\(|now\(", txt)),
        "session_hits": len(re.findall(r"\bsession\[|session\.get|session\.pop", txt)),
    }


def copy_dbs() -> dict[str, pathlib.Path]:
    TMP_SQL.mkdir(parents=True, exist_ok=True)
    raw = run([
        "docker", "exec", "webharbor-audit", "sh", "-lc",
        "find /opt/WebSyn -maxdepth 3 -type f -path '*/instance_seed/*.db' -print",
    ])
    out: dict[str, pathlib.Path] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = pathlib.PurePosixPath(line).parts
        site = parts[3]
        dest = TMP_SQL / f"{site}.db"
        subprocess.check_call(["docker", "cp", f"webharbor-audit:{line}", str(dest)])
        out[site] = dest
    return out


def sample_values(con: sqlite3.Connection, table: str, column: str) -> list:
    try:
        rows = con.execute(
            f'select distinct "{column}" from "{table}" '
            f'where "{column}" is not null and "{column}" != "" limit 8'
        ).fetchall()
        return [r[0] for r in rows]
    except Exception:
        return []


def numeric_range(con: sqlite3.Connection, table: str, column: str) -> dict | None:
    try:
        row = con.execute(f'select min("{column}"), max("{column}") from "{table}"').fetchone()
        if row and row[0] is not None and row[1] is not None and row[0] != row[1]:
            return {"min": row[0], "max": row[1]}
    except Exception:
        return None
    return None


def is_likely_filter(col: dict) -> bool:
    name = col["name"].lower()
    if any(h in name for h in FILTER_NAME_HINTS):
        return True
    if 1 < col["distinct"] <= 80 and col["non_null_ratio"] > 0.3:
        return True
    return False


def db_audit(site: str, db_path: pathlib.Path) -> dict:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    tables = []
    variables = []
    total_rows = 0

    table_names = [
        r["name"]
        for r in con.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")
    ]
    for table in table_names:
        row_count = con.execute(f'select count(*) c from "{table}"').fetchone()["c"]
        total_rows += row_count
        cols = []
        for c in con.execute(f'pragma table_info("{table}")'):
            name = c["name"]
            typ = c["type"] or ""
            try:
                distinct = con.execute(f'select count(distinct "{name}") c from "{table}"').fetchone()["c"] if row_count else 0
                non_null = con.execute(f'select count(*) c from "{table}" where "{name}" is not null and "{name}" != ""').fetchone()["c"] if row_count else 0
            except Exception:
                distinct = 0
                non_null = 0
            col = {
                "name": name,
                "type": typ,
                "distinct": distinct,
                "non_null": non_null,
                "non_null_ratio": round(non_null / row_count, 3) if row_count else 0,
                "sample": sample_values(con, table, name),
            }
            rng = numeric_range(con, table, name)
            if rng:
                col["range"] = rng
            cols.append(col)
            if table in PRIMARY_TABLES.get(site, []) and is_likely_filter(col):
                variables.append({
                    "table": table,
                    **col,
                    "kind": classify_variable(name, typ, distinct, row_count),
                })
        tables.append({
            "name": table,
            "rows": row_count,
            "columns": cols,
            "state_like": any(k in table.lower() for k in STATE_TABLE_KEYWORDS),
        })
    con.close()
    return {
        "total_rows": total_rows,
        "tables": tables,
        "variables": sorted(variables, key=lambda x: (x["table"], x["kind"], x["name"])),
    }


def classify_variable(name: str, typ: str, distinct: int, rows: int) -> str:
    lname = name.lower()
    if any(k in lname for k in ["price", "rating", "count", "score", "duration", "time", "year", "month", "day", "stars", "review", "rank", "stops", "emission"]):
        return "numeric_or_threshold"
    if any(k in lname for k in ["date", "created", "updated", "published", "submitted"]):
        return "date_or_time"
    if distinct <= 2:
        return "boolean_or_binary"
    if distinct <= 25:
        return "categorical_low"
    if distinct <= 120:
        return "categorical_mid"
    return "high_cardinality"


def estimate_combinations(variables: list[dict]) -> dict:
    usable = [v for v in variables if v["kind"] in {"boolean_or_binary", "categorical_low", "categorical_mid", "numeric_or_threshold", "date_or_time"}]
    by_kind = Counter(v["kind"] for v in usable)
    # conservative pair/triple counts, capped per variable at 20 values
    sizes = [max(1, min(20, v["distinct"])) for v in usable]
    pair = 0
    for i in range(len(sizes)):
        for j in range(i + 1, len(sizes)):
            pair += sizes[i] * sizes[j]
    triple = 0
    for i in range(len(sizes)):
        for j in range(i + 1, len(sizes)):
            for k in range(j + 1, len(sizes)):
                triple += sizes[i] * sizes[j] * sizes[k]
    return {
        "usable_variables": len(usable),
        "by_kind": dict(by_kind),
        "pair_space_capped": pair,
        "triple_space_capped": triple,
    }


def html_escape(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_html(payload: dict) -> str:
    site_cards = []
    for site in payload["sites"]:
        vars_top = site["variables"][:18]
        var_rows = "\n".join(
            f"<tr><td>{html_escape(v['table'])}</td><td>{html_escape(v['name'])}</td><td>{v['kind']}</td><td>{v['distinct']}</td><td>{html_escape(', '.join(map(str, v['sample'][:4])))}</td></tr>"
            for v in vars_top
        )
        state_tables = ", ".join(t["name"] for t in site["tables"] if t["state_like"]) or "无明显状态表"
        site_cards.append(f"""
        <section class="doc-section audit-site">
          <h2>{site['display']}</h2>
          <div class="doc-grid compact">
            <div class="doc-card"><h3>表数量</h3><p>{len(site['tables'])}</p></div>
            <div class="doc-card"><h3>总行数</h3><p>{site['total_rows']}</p></div>
            <div class="doc-card"><h3>可用变量</h3><p>{site['combination']['usable_variables']}</p></div>
            <div class="doc-card"><h3>二阶组合估计</h3><p>{site['combination']['pair_space_capped']}</p></div>
            <div class="doc-card"><h3>三阶组合估计</h3><p>{site['combination']['triple_space_capped']}</p></div>
            <div class="doc-card"><h3>状态表</h3><p>{html_escape(state_tables)}</p></div>
          </div>
          <h3>请求变量</h3>
          <p><strong>query args:</strong> {html_escape(', '.join(site['request_vars']['args']) or '无')}</p>
          <p><strong>form args:</strong> {html_escape(', '.join(site['request_vars']['forms']) or '无')}</p>
          <p><strong>json args:</strong> {html_escape(', '.join(site['request_vars']['json']) or '无')}</p>
          <h3>优先用于排列组合的字段</h3>
          <div class="doc-table-wrap">
            <table class="doc-table">
              <thead><tr><th>表</th><th>字段</th><th>类型</th><th>distinct</th><th>样例</th></tr></thead>
              <tbody>{var_rows}</tbody>
            </table>
          </div>
        </section>
        """)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>WebHarbor 变量空间审计</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <main class="doc-main">
    <article class="doc-article">
      <a class="doc-back" href="index.html#variant-playbook">返回 Dashboard</a>
      <p class="eyebrow">Variable Registry</p>
      <h1>WebHarbor 变量空间审计</h1>
      <p class="doc-lede">这页从当前运行的 WebHarbor seed DB、源码 request 参数和状态表中抽取变量。它用于判断哪些字段可以排列组合造题，哪些组合需要先做 DB 可行性验证。</p>
      <section class="doc-section">
        <h2>总体统计</h2>
        <div class="doc-grid compact">
          <div class="doc-card"><h3>站点</h3><p>{len(payload['sites'])}</p></div>
          <div class="doc-card"><h3>总表数</h3><p>{sum(len(s['tables']) for s in payload['sites'])}</p></div>
          <div class="doc-card"><h3>总行数</h3><p>{sum(s['total_rows'] for s in payload['sites'])}</p></div>
          <div class="doc-card"><h3>候选变量</h3><p>{sum(len(s['variables']) for s in payload['sites'])}</p></div>
        </div>
      </section>
      {''.join(site_cards)}
    </article>
  </main>
</body>
</html>"""


def main() -> None:
    dbs = copy_dbs()
    sites = []
    for site, db_path in sorted(dbs.items()):
        db = db_audit(site, db_path)
        req = extract_request_vars(site)
        comb = estimate_combinations(db["variables"])
        sites.append({
            "slug": site,
            "display": DISPLAY.get(site, site),
            **db,
            "request_vars": req,
            "combination": comb,
        })
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sites": sites,
    }
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    HTML_OUT.write_text(render_html(payload))
    print(f"wrote {JSON_OUT} and {HTML_OUT}")


if __name__ == "__main__":
    main()
