#!/usr/bin/env python3
from __future__ import annotations

import collections
import html
import json
import os
from pathlib import Path


BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
WV_ROOT = Path(os.environ.get("WEBVOYAGER_ROOT", ROOT.parent / "WebVoyager")).expanduser()
WV = WV_ROOT / "data"
OUT = BASE / "webvoyager_coverage.html"
JSON_OUT = BASE / "webvoyager_coverage.json"

CAPS = {
    "查找检索": ["find", "search", "look up", "locate", "retrieve", "identify", "discover"],
    "浏览导航": ["browse", "visit", "open", "go to"],
    "筛选排序": ["filter", "sort", "cheapest", "lowest", "highest", "top", "under", "above", "between", "at least", "more than", "less than"],
    "比较计算": ["compare", "difference", "calculate", "how much", "percentage", "compute"],
    "状态操作": ["add", "save", "book", "reserve", "login", "sign up", "create", "select", "checkout"],
    "摘要问答": ["summarize", "summary", "tell me", "answer", "provide", "list", "show"],
    "地图路线": ["route", "directions", "nearest", "near", "walking", "drive", "parking"],
    "文档详情": ["docs", "documentation", "support", "help", "wiki", "abstract", "definition", "pronunciation", "review", "policy", "ingredients"],
    "时效/实时": ["latest", "current", "today", "yesterday", "recent", "within the last", "past week", "real-time", "now"],
}


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def classify(q: str) -> list[str]:
    low = q.lower()
    return [name for name, words in CAPS.items() if any(w in low for w in words)] or ["其他"]


def site_summary(site: str, rows: list[dict], answer_by_id: dict) -> dict:
    cap_counter = collections.Counter()
    answer_counter = collections.Counter()
    length = []
    examples = []
    real_time = []
    stateful = []
    for row in rows:
        q = row["ques"]
        caps = classify(q)
        cap_counter.update(caps)
        ans = answer_by_id.get(row["id"], {})
        answer_counter.update([ans.get("type", "unknown")])
        length.append(len(q))
        if len(examples) < 6:
            examples.append({"id": row["id"], "question": q, "answer_type": ans.get("type", "unknown")})
        if "时效/实时" in caps and len(real_time) < 6:
            real_time.append({"id": row["id"], "question": q})
        if "状态操作" in caps and len(stateful) < 6:
            stateful.append({"id": row["id"], "question": q})
    return {
        "site": site,
        "count": len(rows),
        "answer_types": dict(answer_counter),
        "capabilities": dict(cap_counter),
        "avg_question_len": round(sum(length) / len(length), 1),
        "examples": examples,
        "real_time_examples": real_time,
        "stateful_examples": stateful,
    }


def render(payload: dict) -> str:
    rows = ""
    for s in payload["sites"]:
        caps = "<br>".join(f"{k}: {v}" for k, v in sorted(s["capabilities"].items(), key=lambda x: -x[1]))
        ans = ", ".join(f"{k}: {v}" for k, v in s["answer_types"].items())
        rows += f"<tr><td>{html.escape(s['site'])}</td><td>{s['count']}</td><td>{html.escape(ans)}</td><td>{s['avg_question_len']}</td><td>{caps}</td></tr>"
    cards = ""
    for s in payload["sites"]:
        examples = "".join(f"<li><code>{e['id']}</code> {html.escape(e['question'])} <span class='tag'>{e['answer_type']}</span></li>" for e in s["examples"])
        rt = "".join(f"<li><code>{e['id']}</code> {html.escape(e['question'])}</li>" for e in s["real_time_examples"]) or "<li>无明显时效题样例</li>"
        st = "".join(f"<li><code>{e['id']}</code> {html.escape(e['question'])}</li>" for e in s["stateful_examples"]) or "<li>无明显状态操作题样例</li>"
        cards += f"""
        <section class="doc-section audit-site">
          <h2>{html.escape(s['site'])}</h2>
          <div class="doc-grid compact">
            <div class="doc-card"><h3>题数</h3><p>{s['count']}</p></div>
            <div class="doc-card"><h3>Golden</h3><p>{s['answer_types'].get('golden', 0)}</p></div>
            <div class="doc-card"><h3>Possible</h3><p>{s['answer_types'].get('possible', 0)}</p></div>
          </div>
          <h3>原题样例</h3>
          <ul>{examples}</ul>
          <h3>时效/实时风险样例</h3>
          <ul>{rt}</ul>
          <h3>状态操作样例</h3>
          <ul>{st}</ul>
        </section>
        """
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>WebVoyager 原始任务覆盖审计</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <main class="doc-main">
    <article class="doc-article">
      <a class="doc-back" href="index.html#variant-playbook">返回 Dashboard</a>
      <p class="eyebrow">WebVoyager Coverage</p>
      <h1>WebVoyager 原始 benchmark 考了什么</h1>
      <p class="doc-lede">这页统计 WebVoyager 原始 643 条任务覆盖了哪些站点、哪些能力、哪些答案口径，以及哪些题有时效/实时风险或状态操作要求。它用来判断 WebHarbor 继续造数据时应该补覆盖，还是扩难度。</p>
      <section class="doc-section">
        <h2>总览</h2>
        <div class="doc-grid compact">
          <div class="doc-card"><h3>任务数</h3><p>{payload['total']}</p></div>
          <div class="doc-card"><h3>站点数</h3><p>{len(payload['sites'])}</p></div>
          <div class="doc-card"><h3>Golden</h3><p>{payload['answer_types'].get('golden', 0)}</p></div>
          <div class="doc-card"><h3>Possible</h3><p>{payload['answer_types'].get('possible', 0)}</p></div>
        </div>
      </section>
      <section class="doc-section">
        <h2>站点能力矩阵</h2>
        <div class="doc-table-wrap">
          <table class="doc-table">
            <thead><tr><th>站点</th><th>题数</th><th>答案口径</th><th>平均题长</th><th>能力标签计数</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
      </section>
      {cards}
    </article>
  </main>
</body>
</html>"""


def main() -> None:
    tasks = load_jsonl(WV / "WebVoyager_data.jsonl")
    ref = json.loads((WV / "reference_answer.json").read_text())
    answer_by_id = {}
    for site, obj in ref.items():
        for ans in obj["answers"]:
            answer_by_id[f"{site}--{ans['id']}"] = ans
    grouped = collections.defaultdict(list)
    for task in tasks:
        grouped[task["web_name"]].append(task)
    sites = [site_summary(site, rows, answer_by_id) for site, rows in sorted(grouped.items())]
    answer_types = collections.Counter(answer_by_id.get(t["id"], {}).get("type", "unknown") for t in tasks)
    payload = {"total": len(tasks), "answer_types": dict(answer_types), "sites": sites}
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    OUT.write_text(render(payload))
    print(f"wrote {OUT} and {JSON_OUT}")


if __name__ == "__main__":
    main()
