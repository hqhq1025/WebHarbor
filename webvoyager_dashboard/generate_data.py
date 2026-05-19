#!/usr/bin/env python3
"""Generate static data for the WebHarbor/WebVoyager dashboard.

The script reads the live local clones plus, when available, the running
`webharbor-audit` Docker container. It writes `data.js` for the static UI.
"""
from __future__ import annotations

import collections
import json
import os
import pathlib
import re
import sqlite3
import subprocess
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
WV_ROOT = pathlib.Path(os.environ.get("WEBVOYAGER_ROOT", ROOT.parent / "WebVoyager")).expanduser()
OUT = pathlib.Path(__file__).resolve().parent / "data.js"

SITES_ORDER = [
    "allrecipes",
    "amazon",
    "apple",
    "arxiv",
    "bbc_news",
    "booking",
    "github",
    "google_flights",
    "google_map",
    "google_search",
    "huggingface",
    "wolfram_alpha",
    "cambridge_dictionary",
    "coursera",
    "espn",
]

DISPLAY_TO_SLUG = {
    "Allrecipes": "allrecipes",
    "Amazon": "amazon",
    "Apple": "apple",
    "ArXiv": "arxiv",
    "BBC News": "bbc_news",
    "Booking": "booking",
    "GitHub": "github",
    "Google Flights": "google_flights",
    "Google Map": "google_map",
    "Google Search": "google_search",
    "Huggingface": "huggingface",
    "Wolfram Alpha": "wolfram_alpha",
    "Cambridge Dictionary": "cambridge_dictionary",
    "Coursera": "coursera",
    "ESPN": "espn",
}

SLUG_TO_DISPLAY = {v: k for k, v in DISPLAY_TO_SLUG.items()}

ACTION_PATTERNS = {
    "find": r"\b(find|locate|look up|search for|discover)\b",
    "search": r"\b(search|browse)\b",
    "answer": r"\b(answer|tell|show|provide|list|retrieve)\b",
    "filter_sort": r"\b(filter|sort|priced|rating|stars|cheapest|lowest|highest|top|within|between|above|under|less than|more than)\b",
    "compare": r"\b(compare|difference|how much more|versus|vs\.?)\b",
    "book_buy": r"\b(book|add to cart|add to bag|checkout|purchase|order)\b",
    "save_state": r"\b(save|create|wishlist|shopping list|recipe box|library|star|track|login)\b",
    "plan": r"\b(plan|directions|route|nearest|closest|trip)\b",
    "compute": r"\b(calculate|compute|derivative|integral|solve|convert|translate)\b",
    "use_tool": r"\b(use|inference api|generate|select)\b",
}

DOMAIN_PATTERNS = {
    "shopping": r"\b(price|cart|bag|buy|checkout|product|used|condition|review|rating|stars|save|wishlist)\b",
    "travel": r"\b(hotel|flight|airport|room|stay|booking|trip|journey|return|one-way|round trip|destination)\b",
    "research": r"\b(paper|author|abstract|arxiv|citation|repository|model|dataset|license|stars|commit)\b",
    "knowledge": r"\b(score|date|bio|definition|translate|news|article|dictionary|wolfram|calculate)\b",
    "local_maps": r"\b(map|near|nearest|directions|walking|bus stop|parking|locations|intersection)\b",
}

CONSTRAINT_PATTERNS = [
    r"\b\d+(\.\d+)?\b",
    r"\b(after|before|within|between|above|under|less than|more than|greater than|at least|at most|nearest|closest|cheapest|lowest|highest|top)\b",
    r"\b(rating|stars|reviews|price|date|size|color|license|language|updated|released|non-stop|breakfast|wifi|airport shuttle)\b",
]


def run(cmd: list[str], cwd: pathlib.Path | None = None, timeout: int = 12) -> str:
    try:
        return subprocess.check_output(
            cmd, cwd=str(cwd) if cwd else None, stderr=subprocess.DEVNULL, text=True, timeout=timeout
        ).strip()
    except Exception:
        return ""


def docker_exec(script: str, timeout: int = 20) -> str:
    return run(["docker", "exec", "webharbor-audit", "sh", "-lc", script], timeout=timeout)


def load_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def classify_task(question: str) -> dict:
    q = question.lower()
    actions = [name for name, pat in ACTION_PATTERNS.items() if re.search(pat, q)]
    domains = [name for name, pat in DOMAIN_PATTERNS.items() if re.search(pat, q)]
    if not domains:
        domains = ["general"]
    constraints = 0
    for pat in CONSTRAINT_PATTERNS:
        constraints += len(re.findall(pat, q))
    requires_state = bool(re.search(ACTION_PATTERNS["book_buy"] + "|" + ACTION_PATTERNS["save_state"], q))
    requires_navigation = bool(re.search(r"\b(browse|go to|open|select|click|filter|sort|checkout|book|create|add)\b", q))
    complexity = min(10, 1 + len(actions) + min(4, constraints) + (2 if requires_state else 0) + (1 if requires_navigation else 0))
    return {
        "actions": actions or ["answer"],
        "domains": domains,
        "constraint_count": constraints,
        "requires_state": requires_state,
        "requires_navigation": requires_navigation,
        "complexity": complexity,
    }


def repo_meta(path: pathlib.Path) -> dict:
    return {
        "path": str(path),
        "commit": run(["git", "log", "-1", "--oneline", "--decorate"], cwd=path),
        "branch": run(["git", "branch", "--show-current"], cwd=path),
        "status": run(["git", "status", "--short"], cwd=path),
        "size": run(["du", "-sh", str(path)]).split("\t")[0] if path.exists() else "",
    }


def code_metrics(slug: str) -> dict:
    sdir = ROOT / "sites" / slug
    app = sdir / "app.py"
    txt = app.read_text(errors="ignore") if app.exists() else ""
    return {
        "routes": len(re.findall(r"@app\.route\(", txt)),
        "models": len(re.findall(r"^class\s+\w+\([^)]*db\.Model[^)]*\):", txt, re.M)),
        "forms": len(re.findall(r"^class\s+\w+\([^)]*Form[^)]*\):", txt, re.M)),
        "templates": len(list((sdir / "templates").glob("*.html"))) if (sdir / "templates").exists() else 0,
        "app_lines": txt.count("\n") + 1 if txt else 0,
        "has_health": (sdir / "_health.py").exists(),
        "has_js": (sdir / "static" / "js" / "main.js").exists(),
    }


def live_health() -> dict:
    raw = run(["curl", "-s", "http://localhost:8311/health"], timeout=8)
    if not raw:
        return {"ok": False, "sites": {}}
    try:
        return json.loads(raw)
    except Exception:
        return {"ok": False, "sites": {}, "raw": raw}


def docker_db_stats() -> dict:
    script = r'''
python3 - <<'PY'
import json, pathlib, sqlite3
root=pathlib.Path("/opt/WebSyn")
out={}
for site in sorted([p for p in root.iterdir() if p.is_dir()]):
    dbs=list((site/"instance_seed").glob("*.db"))
    if not dbs:
        continue
    db=dbs[0]
    con=sqlite3.connect(str(db))
    tables=[r[0] for r in con.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")]
    counts={}
    for t in tables:
        try:
            counts[t]=con.execute('select count(*) from "%s"' % t.replace('"','""')).fetchone()[0]
        except Exception:
            pass
    con.close()
    out[site.name]={"db_file": db.name, "db_bytes": db.stat().st_size, "tables": len(tables), "counts": counts}
print(json.dumps(out))
PY
'''
    raw = docker_exec(script)
    try:
        return json.loads(raw)
    except Exception:
        return {}


def docker_asset_stats() -> dict:
    script = r'''
python3 - <<'PY'
import json, pathlib, os
root=pathlib.Path("/opt/WebSyn")
out={}
for site in sorted([p for p in root.iterdir() if p.is_dir()]):
    item={}
    for rel in ["static/images", "static/external_cache"]:
        p=site/rel
        total=0; files=0
        if p.exists():
            for f in p.rglob("*"):
                if f.is_file():
                    files+=1
                    total+=f.stat().st_size
        item[rel.replace("/","_")]={"bytes": total, "files": files}
    out[site.name]=item
print(json.dumps(out))
PY
'''
    raw = docker_exec(script)
    try:
        return json.loads(raw)
    except Exception:
        return {}


def image_tag(path: pathlib.Path) -> str:
    try:
        return path.relative_to(pathlib.Path(__file__).resolve().parent).as_posix()
    except Exception:
        return str(path)


def load_browser_audit() -> dict:
    path = ROOT / "audit_screens" / "audit-summary.json"
    if not path.exists():
        return {"homes": [], "scenarios": []}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {"homes": [], "scenarios": []}


def main() -> None:
    webharbor_tasks = []
    for p in (ROOT / "sites").glob("*/tasks.jsonl"):
        for obj in load_jsonl(p):
            obj["slug"] = p.parent.name
            webharbor_tasks.append(obj)

    wv_tasks = load_jsonl(WV_ROOT / "data" / "WebVoyager_data.jsonl")
    wv_by_id = {t["id"]: t for t in wv_tasks}
    wh_by_id = {t["id"]: t for t in webharbor_tasks}
    reference = json.loads((WV_ROOT / "data" / "reference_answer.json").read_text())

    answer_by_id: dict[str, dict] = {}
    for site, obj in reference.items():
        for ans in obj.get("answers", []):
            answer_by_id[f"{site}--{ans['id']}"] = ans

    tasks = []
    for task in sorted(webharbor_tasks, key=lambda x: (SITES_ORDER.index(x["slug"]), int(x["id"].split("--")[-1]))):
        ans = answer_by_id.get(task["id"], {})
        derived = classify_task(task["ques"])
        tasks.append({
            "id": task["id"],
            "site": task["web_name"],
            "slug": task["slug"],
            "index": int(task["id"].split("--")[-1]),
            "question": task["ques"],
            "local_url": task["web"],
            "upstream_url": task["upstream_url"],
            "original_web": wv_by_id.get(task["id"], {}).get("web", ""),
            "answer_type": ans.get("type", "unknown"),
            "answer": ans.get("ans", ""),
            "answer_length": len(str(ans.get("ans", ""))),
            "question_length": len(task["ques"]),
            **derived,
        })

    browser_audit = load_browser_audit()
    home_by_slug = {h["site"]: h for h in browser_audit.get("homes", [])}
    scenario_by_name = {s["name"]: s for s in browser_audit.get("scenarios", [])}
    health = live_health()
    db_stats = docker_db_stats()
    asset_stats = docker_asset_stats()

    site_summaries = []
    for i, slug in enumerate(SITES_ORDER):
        display = SLUG_TO_DISPLAY[slug]
        site_tasks = [t for t in tasks if t["slug"] == slug]
        answers = collections.Counter(t["answer_type"] for t in site_tasks)
        actions = collections.Counter(a for t in site_tasks for a in t["actions"])
        domains = collections.Counter(d for t in site_tasks for d in t["domains"])
        db = db_stats.get(slug, {})
        counts = db.get("counts", {})
        top_tables = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:8]
        home = home_by_slug.get(slug, {})
        live = health.get("sites", {}).get(slug, {})
        assets = asset_stats.get(slug, {})
        local_port = 43000 + i
        site_summaries.append({
            "slug": slug,
            "display": display,
            "task_count": len(site_tasks),
            "golden": answers.get("golden", 0),
            "possible": answers.get("possible", 0),
            "avg_complexity": round(sum(t["complexity"] for t in site_tasks) / len(site_tasks), 2),
            "avg_question_length": round(sum(t["question_length"] for t in site_tasks) / len(site_tasks), 1),
            "state_tasks": sum(1 for t in site_tasks if t["requires_state"]),
            "navigation_tasks": sum(1 for t in site_tasks if t["requires_navigation"]),
            "actions": dict(actions.most_common()),
            "domains": dict(domains.most_common()),
            "code": code_metrics(slug),
            "db": {
                "db_file": db.get("db_file", ""),
                "db_bytes": db.get("db_bytes", 0),
                "tables": db.get("tables", 0),
                "top_tables": top_tables,
            },
            "assets": assets,
            "browser": home,
            "health": live,
            "docker_port": live.get("port", 40000 + i),
            "local_port": local_port,
            "local_url": f"http://localhost:{local_port}/",
            "task_file": f"sites/{slug}/tasks.jsonl",
            "screenshot": f"assets/audit_screens/{slug}-home.png" if (ROOT / "audit_screens" / f"{slug}-home.png").exists() else "",
        })

    docker_info = {
        "container": run(["docker", "ps", "--filter", "name=webharbor-audit", "--format", "{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}"]),
        "image": run(["docker", "image", "inspect", "battalion7244/webharbor:latest", "--format", "{{.Id}}|{{.Size}}|{{.Created}}"]),
        "health": health,
    }

    all_actions = collections.Counter(a for t in tasks for a in t["actions"])
    all_domains = collections.Counter(d for t in tasks for d in t["domains"])
    answer_types = collections.Counter(t["answer_type"] for t in tasks)
    complexity_hist = collections.Counter(str(t["complexity"]) for t in tasks)
    stateful = sum(1 for t in tasks if t["requires_state"])
    navigational = sum(1 for t in tasks if t["requires_navigation"])

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repos": {
            "webharbor": repo_meta(ROOT),
            "webvoyager": repo_meta(WV_ROOT),
        },
        "infra": {
            "docker": docker_info,
            "sites": site_summaries,
            "control_plane": {
                "local": "http://localhost:8311",
                "container": "http://localhost:8101",
                "endpoints": ["/health", "POST /reset/<site>", "POST /reset-all", "POST /restart/<site>"],
            },
            "task_alignment": {
                "webharbor_tasks": len(webharbor_tasks),
                "webvoyager_tasks": len(wv_tasks),
                "ids_equal": set(wh_by_id) == set(wv_by_id),
                "question_diffs": sum(1 for k in set(wh_by_id) & set(wv_by_id) if wh_by_id[k]["ques"] != wv_by_id[k]["ques"]),
                "upstream_diffs": sum(1 for k in set(wh_by_id) & set(wv_by_id) if wh_by_id[k]["upstream_url"] != wv_by_id[k]["web"]),
            },
            "browser_scenarios": list(scenario_by_name.values()),
        },
        "metrics": {
            "task_count": len(tasks),
            "site_count": len(site_summaries),
            "answer_types": dict(answer_types),
            "actions": dict(all_actions.most_common()),
            "domains": dict(all_domains.most_common()),
            "complexity_histogram": dict(sorted(complexity_hist.items(), key=lambda kv: int(kv[0]))),
            "stateful_tasks": stateful,
            "navigational_tasks": navigational,
            "avg_complexity": round(sum(t["complexity"] for t in tasks) / len(tasks), 2),
            "avg_question_length": round(sum(t["question_length"] for t in tasks) / len(tasks), 1),
        },
        "tasks": tasks,
        "reference_notices": {site: obj.get("notice", "") for site, obj in reference.items()},
    }

    OUT.write_text("window.WEBVOYAGER_DASHBOARD_DATA = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n")
    print(f"wrote {OUT} with {len(tasks)} tasks and {len(site_summaries)} sites")


if __name__ == "__main__":
    main()
