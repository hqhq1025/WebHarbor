"""Backfill R10 taxonomy fields onto sites/github/tasks.jsonl.

Reads tasks.jsonl in place, classifies each row deterministically from
``ques`` text plus URL slug, and rewrites the file with six new fields
merged in:

- capability
- task_template
- surface_pattern
- item_key
- start_variant
- composition_pattern

Determinism: rule order is fixed, no randomness; md5(ques+id) breaks ties.

Run:  python3 _recompute_taxonomy.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
TASKS = HERE / "tasks.jsonl"

# Match GitHub owner/repo references both inside backticks and as bare slugs.
REPO_RE = re.compile(r"\b([A-Za-z0-9][\w.\-]{0,38})/([A-Za-z0-9][\w.\-]{0,99})\b")
USER_RE = re.compile(r"/sponsors/([A-Za-z0-9\-]+)|@([A-Za-z0-9\-]+)")
API_RE = re.compile(r"/api/([A-Za-z0-9_\-/.]+)")
HELP_RE = re.compile(r"/help/([A-Za-z0-9\-]+)")
TOPIC_RE = re.compile(r"/topics?/([A-Za-z0-9\-]+)")
SECURITY_RE = re.compile(r"/security/([A-Za-z0-9_\-/]+)")
TRENDING_RE = re.compile(r"/trending(?:/([A-Za-z0-9\-]+))?")


def md5_hex(*parts: str) -> str:
    h = hashlib.md5()
    for p in parts:
        h.update(p.encode("utf-8"))
    return h.hexdigest()


# Common English / GitHub stopwords that REPO_RE might falsely match (e.g.
# "owner/repo" in instructions). The first capture-group element must look
# like a real owner: not all-lowercase short word and not pure noise.
_REPO_BLOCKLIST_OWNERS = {
    "owner",
    "user",
    "org",
    "and",
    "the",
    "a",
    "an",
    "your",
    "my",
    "this",
}


def find_item_key(q: str) -> str:
    """Pull out the most specific entity slug mentioned, else 'none'."""
    for m in REPO_RE.finditer(q):
        owner, repo = m.group(1), m.group(2)
        if owner.lower() in _REPO_BLOCKLIST_OWNERS:
            continue
        if repo.lower() in {"repo", "branches", "settings", "issues", "pulls"}:
            continue
        if "/" not in owner and "." not in repo:
            return f"repo:{owner}/{repo}"
        return f"repo:{owner}/{repo}"
    if m := USER_RE.search(q):
        return f"user:{m.group(1) or m.group(2)}"
    if m := TOPIC_RE.search(q):
        return f"topic:{m.group(1)}"
    if m := SECURITY_RE.search(q):
        return f"security:{m.group(1).rstrip('/')}"
    if m := API_RE.search(q):
        return f"api:{m.group(1).rstrip('/')}"
    if m := HELP_RE.search(q):
        return f"help:{m.group(1)}"
    if m := TRENDING_RE.search(q):
        return "trending:" + (m.group(1) or "all")
    return "none"


# ----- task_template ---------------------------------------------------------
TEMPLATE_RULES = [
    # state-changing first
    (r"\bset (the )?open pr limit|\benable\b|\bdisable\b|\bturn (on|off)\b|\brevoke\b", "set-security-config"),
    (r"\bgrouped dependabot|dependabot version updates", "set-dependabot-config"),
    (r"\bmerge|create a pull request|open (a |an )?(issue|pull request|pr)", "submit-form"),
    (r"\bsubscribe|notification|watch this repo", "subscribe-repo"),
    (r"\bstar this repo|unstar\b", "star-repo"),
    (r"\bsponsor\b|/sponsors/", "sponsor-tiers"),
    # navigation + listing templates
    (r"\bbranches?\b|/branches", "list-branches"),
    (r"\bdefault branch\b", "read-default-branch"),
    (r"\breleases?\b|/releases", "list-releases"),
    (r"\btags?\b|latest-tag", "list-tags"),
    (r"\bactions?\b|/actions|workflow", "list-actions"),
    (r"\bpulls?\b|/pulls|pull request", "list-pulls"),
    (r"\bissues?\b", "list-issues"),
    (r"\bdiscussions?\b", "list-discussions"),
    (r"\btrending\b|/trending", "view-trending"),
    (r"\bfile finder\b|press `t`|press 't'", "file-finder"),
    (r"\badvanced (search )?syntax|advanced-search|with more than \d+ stars\b", "advanced-search"),
    (r"\bsearch for|find (an? |the |a list of )?(open[- ]source )?(repo|repository|project|topics?)\b|find (a )?\w+ (repo|repository|project)", "search-repos"),
    (r"\b/topics?/|topic\b", "browse-topic"),
    (r"\b/api/|openapi", "api-endpoint"),
    (r"\b/help/|glossary", "read-help-page"),
    (r"\bsidebar|more from @|related by topic\b", "sidebar-pick"),
    (r"\bbreadcrumb\b", "read-breadcrumb"),
    (r"\bcontributors?\b", "list-contributors"),
    (r"\bcommits?\b|/commits", "list-commits"),
    (r"\bcode security|secret scanning", "view-security-settings"),
    (r"\b\.rss\b", "view-rss-feed"),
    (r"\b/profile|account/edit|affiliation", "account-profile"),
]

# ----- surface_pattern -------------------------------------------------------
SURFACE_RULES = [
    (r"/branches", "branches-list"),
    (r"/releases", "releases-page"),
    (r"/tags|latest-tag", "tags-page"),
    (r"/actions", "actions-runs"),
    (r"/pulls", "pr-list"),
    (r"/issues", "issue-list"),
    (r"/discussions", "discussion-list"),
    (r"/trending", "trending-list"),
    (r"/sponsors", "sponsors-page"),
    (r"/security|secret-scanning|code security", "security-settings"),
    (r"/api/|openapi", "api-endpoint"),
    (r"/help/|glossary", "help-page"),
    (r"/topics?/", "topic-page"),
    (r"file finder|press `?t`?", "file-finder-modal"),
    (r"advanced[- ]search|search/advanced", "advanced-search-form"),
    (r"search for|search the", "search-bar"),
    (r"sidebar|more from @|related by topic", "sidebar-block"),
    (r"breadcrumb", "breadcrumb"),
    (r"contributors|/contributors", "contributors-page"),
    (r"commits|/commits", "commits-page"),
    (r"\.rss", "rss-feed"),
    (r"/profile|account/edit", "account-form"),
    (r"\b[A-Za-z0-9.\-]+/[A-Za-z0-9.\-]+\b", "repo-home"),
]

# ----- start_variant ---------------------------------------------------------
START_RULES = [
    (r"^\s*(visit|open|go to|navigate to)\s+`?/?[a-z0-9.\-]+/[a-z0-9.\-]+/branches", "branches"),
    (r"^\s*(visit|open|go to)\s+`?/?[a-z0-9.\-]+/[a-z0-9.\-]+/releases", "releases"),
    (r"^\s*(visit|open|go to)\s+`?/?[a-z0-9.\-]+/[a-z0-9.\-]+/actions", "actions"),
    (r"^\s*(visit|open|go to)\s+`?/?[a-z0-9.\-]+/[a-z0-9.\-]+/pulls", "pulls"),
    (r"^\s*(visit|open|go to)\s+`?/?[a-z0-9.\-]+/[a-z0-9.\-]+/issues", "issues"),
    (r"^\s*(visit|open|go to)\s+`?/?[a-z0-9.\-]+/[a-z0-9.\-]+/discussions", "discussions"),
    (r"^\s*(visit|open|go to)\s+`?/trending", "trending"),
    (r"^\s*(visit|open|go to)\s+`?/sponsors", "sponsors"),
    (r"^\s*(visit|open|go to)\s+`?/security|secret-scanning", "security"),
    (r"^\s*(visit|open|go to)\s+`?/api/|openapi", "api"),
    (r"^\s*(visit|open|go to)\s+`?/help/|glossary", "help"),
    (r"^\s*(visit|open|go to)\s+`?/topics?/", "topic"),
    (r"^\s*(visit|open|go to|on)\s+`?/?[a-z0-9.\-]+/[a-z0-9.\-]+`?", "repo-home"),
    (r"^\s*search\b|^\s*use the github search|^\s*find ", "search-bar"),
    (r"^\s*(log ?in|after logging in|sign in)", "login"),
    (r"^\s*(visit|open|go to)\s+`?/?[a-z0-9.\-]+/[a-z0-9.\-]+/settings", "settings"),
    (r"^\s*on `?[a-z0-9.\-]+/[a-z0-9.\-]+`?'?s? settings", "settings"),
]


def first_match(rules, text):
    for pat, label in rules:
        if re.search(pat, text, re.IGNORECASE):
            return label
    return None


def capability_for(q: str, template: str) -> str:
    ql = q.lower()
    if template in {
        "set-security-config",
        "set-dependabot-config",
        "submit-form",
        "subscribe-repo",
        "star-repo",
    } or re.search(r"\b(set the|enable|disable|turn (on|off)|revoke|merge|create|click 'subscribe')\b", ql):
        return "state-changing"
    if template in {"search-repos", "advanced-search", "browse-topic", "view-trending"}:
        return "search-filter"
    if template in {"sidebar-pick", "file-finder"}:
        return "cross-page-nav"
    if re.search(r"\b(count|how many|total|number of|maximum|minimum|ratio|compare|average)\b", ql):
        return "computational"
    hops = len(re.findall(r"\b(then|after|next|navigate|go to|click|open|pick|press)\b", ql))
    if hops >= 2:
        return "cross-page-nav"
    return "data-extraction"


def composition_for(q: str, template: str, capability: str) -> str:
    ql = q.lower()
    hops = len(re.findall(r"\b(then|after|next|navigate|go to|click|open|pick|press)\b", ql))
    if "log in" in ql or "logged in as" in ql or "after logging in" in ql:
        return "login-then-action"
    if template == "file-finder":
        return "key-shortcut-then-read"
    if template == "sidebar-pick":
        return "sidebar-pick"
    if re.search(r"\b(first|top|most|highest|pick|select)\b", ql) and template in {
        "search-repos",
        "advanced-search",
        "browse-topic",
        "view-trending",
    }:
        return "filter-then-pick"
    if re.search(r"\b(paginate|page 2|next page)\b", ql):
        return "paginate-then-read"
    if hops >= 3 or capability == "cross-page-nav":
        return "2-hop-nav"
    if hops >= 2:
        return "2-hop-nav"
    return "single-page-lookup"


def classify(row: dict) -> dict:
    q = row["ques"]
    template = first_match(TEMPLATE_RULES, q) or "read-detail-field"
    surface = first_match(SURFACE_RULES, q) or "repo-home"
    start = first_match(START_RULES, q) or "repo-home"
    capability = capability_for(q, template)
    item_key = find_item_key(q)
    if item_key == "none":
        item_key = "rowhash:" + md5_hex(row["id"], q)[:10]
    composition = composition_for(q, template, capability)
    return {
        "capability": capability,
        "task_template": template,
        "surface_pattern": surface,
        "item_key": item_key,
        "start_variant": start,
        "composition_pattern": composition,
    }


def main() -> None:
    rows = [json.loads(line) for line in TASKS.read_text().splitlines() if line.strip()]
    out_lines = []
    for row in rows:
        merged = {**row, **classify(row)}
        out_lines.append(json.dumps(merged, ensure_ascii=False))
    TASKS.write_text("\n".join(out_lines) + "\n")
    print(f"rewrote {len(out_lines)} rows -> {TASKS}")


if __name__ == "__main__":
    main()
