"""Third R3 task generation pass — pushes total to 420+."""
import json
from pathlib import Path

BASE = Path("/home/v-haoqiwang/repos/WebHarbor/sites/arxiv")
TASKS_FILE = BASE / "tasks.jsonl"

existing_lines = []
existing_ques = set()
with open(TASKS_FILE) as fh:
    for line in fh:
        line = line.rstrip()
        if not line:
            continue
        existing_lines.append(line)
        existing_ques.add(json.loads(line).get("ques", ""))

next_id = len(existing_lines)
new_tasks = []


def add(q):
    global next_id
    if q in existing_ques:
        return
    existing_ques.add(q)
    new_tasks.append({
        "web_name": "ArXiv",
        "id": f"ArXiv--{next_id}",
        "ques": q,
        "web": "http://localhost:40003/",
        "upstream_url": "https://arxiv.org/",
    })
    next_id += 1


# --- Cross-page citation / DOI ---
add("Find any paper in the local mirror with a DOI starting '10.1103/'. Report its arxiv_id.")
add("Find a paper whose journal_ref mentions 'Phys. Rev.' Report the journal_ref string verbatim.")
add("Open advanced search and filter by 'journal_ref contains \"Nature\"'. How many results?")
add("Search abstracts for 'mass spectrum'. Open the top result and report its journal_ref.")

# --- Year + archive + advanced search compose ---
for code in ["cs.AI", "cs.CL", "cs.CV", "stat.ML", "math.NA"]:
    add(f"Use /year/2025/{code} to browse 2025 submissions. Open the first paper of January 2025 and report its title.")

# --- Catchup-derived task ---
add("On /catchup default, identify the arxiv_id of the most recently submitted paper (top of the list).")
add("On /catchup?days=30, open the very last paper on page 1 (lowest date in the window). Report its submitted_date.")

# --- Group landing depth ---
add("From /find/grp_physics, sum the paper counts of astro-ph, cond-mat, and quant-ph. Report the sum.")
add("From /find/grp_cs, what is the only archive listed and how many papers does it have?")

# --- Author chains ---
add("On the /author/Yann LeCun page (if any), pick the first paper and open its /abs page. Report the full list of co-authors shown.")
add("Find any paper authored by a person whose affiliation contains 'MIT'. Report the affiliated author's name.")
add("From the abstract page of arXiv:2412.03134, click into the third author's /author/ page and report how many other papers they appear on.")

# --- Comment-thread reply chain (R3 only) ---
add("Find a comment whose body begins with '@' (an at-mention). Report the username being mentioned and the parent paper's arxiv_id.")
add("Find a Re: titled comment. Report the original comment's title that it replied to.")
add("On a paper with at least 3 'Re:' comments, list the chain of usernames in order.")

# --- /export / library / starred composition ---
add("Log in as alice.j / test1234. Visit /export, create a BibTeX export of all papers in her 'NLP' folder, then download. Report the BibTeX cite-key of the first entry.")
add("Log in as bob.c / test1234. Add the top paper from /catchup/cs.CV to his 'Vision' folder. Confirm folder count increases by 1.")
add("Log in as carol.d / test1234. Open /starred and report which papers are starred (arxiv_ids).")
add("Log in as david.k / test1234. Open his alerts. Report each category code and the frequency.")

# --- Visual feature tests (collapsible abstract / sticky strip) ---
add("Open an /abs page whose abstract is short (<720 chars). Confirm that no 'Read more' button appears.")
add("On the /abs page of a paper with ≥3 affiliated authors, scroll down and confirm the sticky author/affiliation bar remains visible.")

# --- Pagination ---
add("On /list/cs.AI/recent?page=3, what arxiv_id appears in row [1] of page 3?")
add("On /list/math.AG/new?page=2, report the announce_day banner shown at the top.")

# --- More /help cross-link sanity ---
add("From /help/withdraw, follow the link to /help/submit and report the page title.")
add("From /help/store, click into /store and report the first item title.")
add("From /help/categories, click into /category_taxonomy and report the heading shown.")

# --- API JSON spot checks ---
add("Hit /api/papers/math.AG and report the JSON keys present on each paper entry.")
add("Hit /api/papers/hep-th and report how many entries are returned.")
add("Hit /api/stats and report the top-3 categories by paper count.")

# --- Latex-source download flow ---
add("Open arXiv:2104.08821, then click 'TeX Source'. Report the placeholder filename shown in the e-print response.")

# Save
with open(TASKS_FILE, "w") as fh:
    for line in existing_lines:
        fh.write(line + "\n")
    for t in new_tasks:
        fh.write(json.dumps(t, ensure_ascii=False) + "\n")

print(f"added {len(new_tasks)} more tasks; total now = {len(existing_lines) + len(new_tasks)}")
