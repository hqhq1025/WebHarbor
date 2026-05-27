"""Backfill R10 taxonomy fields onto sites/arxiv/tasks.jsonl.

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

ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})")
OLD_ID_RE = re.compile(r"\b(\d{7})\b")  # 0808163 style
CATEGORY_RE = re.compile(r"\b([a-z\-]+\.[A-Z]{2})\b")
ACM_RE = re.compile(r"/acm/([A-Z](?:\.\d+){1,3})", re.IGNORECASE)
GRP_RE = re.compile(r"/find/grp_([a-z\-]+)", re.IGNORECASE)
HELP_RE = re.compile(r"/help/([a-z0-9\-]+)", re.IGNORECASE)
API_RE = re.compile(r"/api/([a-z0-9_\-/]+)", re.IGNORECASE)
LIBRARY_RE = re.compile(r"/library(?:\?folder=([^\s\"']+))?", re.IGNORECASE)
USER_EMAIL_RE = re.compile(r"\b([a-z][a-z0-9_.]*@test\.com)\b", re.IGNORECASE)


def md5_hex(*parts: str) -> str:
    h = hashlib.md5()
    for p in parts:
        h.update(p.encode("utf-8"))
    return h.hexdigest()


def find_item_key(q: str) -> str:
    """Return the most specific entity slug mentioned, else 'none'."""
    if m := ARXIV_ID_RE.search(q):
        return m.group(1)
    if m := OLD_ID_RE.search(q):
        return m.group(1)
    if m := CATEGORY_RE.search(q):
        return m.group(1)
    if m := ACM_RE.search(q):
        return f"acm:{m.group(1)}"
    if m := GRP_RE.search(q):
        return f"grp:{m.group(1)}"
    if m := HELP_RE.search(q):
        return f"help:{m.group(1)}"
    if m := API_RE.search(q):
        return f"api:{m.group(1).rstrip('/')}"
    if m := LIBRARY_RE.search(q):
        folder = m.group(1) or "default"
        return f"library:{folder}"
    if m := USER_EMAIL_RE.search(q):
        return f"user:{m.group(1).lower()}"
    return "none"


# ----- task_template ---------------------------------------------------------
TEMPLATE_RULES = [
    # state-changing first: actions reshape DB regardless of phrasing
    (r"\bexport to (bib|csv|json|bibtex)\b|/exports?\b", "library-export"),
    (r"\bsubscribe|notification|alert\b", "alert-subscribe"),
    (r"\bstar(red)?\b|add to library|save (this )?paper", "library-save"),
    (r"/replace/|withdraw an article|submission form|submit a paper|/submit\b", "submit-replacement"),
    (r"\bcomment\b", "comment-post"),
    (r"\blog in|login|sign in|logged in as\b", "login-then-read"),
    # navigation-heavy templates
    (r"\bcit(ing|e|ation)\b", "citation-list"),
    (r"\bco-publication|co-paper|co-author\b", "coauthor-list"),
    (r"\b/papers/.+/related\b|same primary subject|related papers?", "related-papers"),
    (r"\bbibtex\b", "read-bibtex"),
    (r"\bjournal-ref|journal ref\b", "journal-ref-search"),
    (r"\bauthors? who also published\b", "coauthor-listing"),
    (r"\bauthor of|list (the )?authors", "list-authors"),
    (r"\babstract\b", "read-abstract"),
    (r"\bcite as\b", "read-citation-line"),
    (r"\b/acm/|acm class\b", "acm-class-listing"),
    (r"\b/find/grp_|group landing\b", "group-landing"),
    (r"\b/help/|help page\b", "read-help-page"),
    (r"\b/api/\b|api endpoint", "api-endpoint"),
    (r"\bsearch for|search the latest|look up|find (the )?(papers?|preprints?)", "search-by-keyword"),
    (r"\b(category|cs\.[A-Z]+|stat\.[A-Z]+|math\.[A-Z]+|eess\.[A-Z]+)\b", "browse-by-category"),
    (r"\bpaginate|page 2|next page\b", "paginate-listing"),
    (r"\baffiliation|account/edit|profile\b", "account-profile"),
]

# ----- surface_pattern -------------------------------------------------------
SURFACE_RULES = [
    (r"/abs/|abstract", "abs-page"),
    (r"/library", "library-page"),
    (r"/account|profile|affiliation", "account-form"),
    (r"/help/", "help-page"),
    (r"/api/", "api-endpoint"),
    (r"/acm/", "acm-class-page"),
    (r"/find/grp_", "group-landing"),
    (r"/replace/|/submit", "submission-form"),
    (r"citing|citation|/papers/.+/related", "citation-graph"),
    (r"bibtex|journal-ref", "metadata-block"),
    (r"co-publication|co-author|coauthor", "coauthor-listing"),
    (r"category|listing", "listing-page"),
    (r"export|/exports", "export-page"),
    (r"alert|subscription|notification", "alert-form"),
    (r"search", "search-result"),
]

# ----- start_variant ---------------------------------------------------------
START_RULES = [
    (r"^\s*(visit|open|go to|navigate to)\s+/abs/", "abs-page"),
    (r"^\s*(visit|open|go to)\s+/help/", "help-page"),
    (r"^\s*(visit|open|go to)\s+/api/", "api-endpoint"),
    (r"^\s*(visit|open|go to)\s+/acm/", "acm-class-page"),
    (r"^\s*(visit|open|go to)\s+/find/", "find-listing"),
    (r"^\s*(visit|open|go to)\s+/library", "library-page"),
    (r"^\s*(visit|open|go to)\s+/account", "account-page"),
    (r"^\s*(visit|open|go to)\s+/replace", "replace-form"),
    (r"^\s*(log ?in|after logging in|sign in)", "login"),
    (r"^\s*(from|on)\s+/abs/", "abs-page"),
    (r"^\s*(search|look up|find|look for)", "search-bar"),
    (r"^\s*go to arxiv:", "abs-page"),
]


def first_match(rules, text):
    for pat, label in rules:
        if re.search(pat, text, re.IGNORECASE):
            return label
    return None


def capability_for(q: str, template: str) -> str:
    ql = q.lower()
    if template in {
        "library-export",
        "library-save",
        "alert-subscribe",
        "submit-replacement",
        "comment-post",
    }:
        return "state-changing"
    if template == "search-by-keyword":
        return "search-filter"
    if template == "browse-by-category":
        return "search-filter"
    if template in {"citation-list", "coauthor-list", "coauthor-listing", "related-papers"}:
        return "cross-page-nav"
    if re.search(r"\b(count|how many|total|number of|ratio|compare|max|min|average)\b", ql):
        return "computational"
    if re.search(r"\bgo to|then (visit|open|click)|paginate|navigate\b", ql) and re.search(
        r"\breport|what|which|how many\b", ql
    ):
        # only treat as nav if there is clearly more than one hop
        hops = len(re.findall(r"\b(then|after|next|navigate|go to|click|open)\b", ql))
        if hops >= 2:
            return "cross-page-nav"
    return "data-extraction"


def composition_for(q: str, template: str, capability: str) -> str:
    ql = q.lower()
    hops = len(re.findall(r"\b(then|after|next|navigate to|go to|click|open)\b", ql))
    if template in {"login-then-read", "library-export", "library-save", "alert-subscribe"} or "log in" in ql or "logged in as" in ql:
        return "login-then-action"
    if re.search(r"\bpaginate|page 2|next page\b", ql):
        return "paginate-then-read"
    if template in {"search-by-keyword", "browse-by-category"} and re.search(r"\b(first|top|most|select one|pick)\b", ql):
        return "filter-then-pick"
    if hops >= 3 or capability == "cross-page-nav":
        return "2-hop-nav"
    if hops >= 2:
        return "2-hop-nav"
    return "single-page-lookup"


def classify(row: dict) -> dict:
    q = row["ques"]
    template = first_match(TEMPLATE_RULES, q) or "read-detail-field"
    surface = first_match(SURFACE_RULES, q) or "abs-page"
    start = first_match(START_RULES, q) or "abs-page"
    capability = capability_for(q, template)
    item_key = find_item_key(q)
    if item_key == "none":
        # md5-derived fallback so every row has a stable, distinct slug
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
