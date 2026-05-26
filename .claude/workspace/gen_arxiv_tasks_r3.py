"""Generate R3 task additions for arxiv mirror.

Produces ~260 new tasks covering:
  - /year/<year> and /year/<year>/<code> sub-pages
  - /catchup, /catchup/<code>
  - /find/grp_<group> landings
  - /a/<author>/recent feeds
  - /help/<page> sub-page lookups
  - author-by-affiliation, paper-by-grant-funding, similar-paper,
    latex-source-download, find-by-coauthor-network, multi-step
  - Library / starred / export / comment surfaces (new authenticated)

Appends to tasks.jsonl preserving the existing 153 entries.
"""
import json
import os
from pathlib import Path

BASE = Path("/home/v-haoqiwang/repos/WebHarbor/sites/arxiv")
TASKS_FILE = BASE / "tasks.jsonl"

WEB = "http://localhost:40003/"
UPSTREAM = "https://arxiv.org/"

existing_lines = []
existing_ques = set()
if TASKS_FILE.exists():
    with open(TASKS_FILE) as fh:
        for line in fh:
            line = line.rstrip()
            if not line:
                continue
            d = json.loads(line)
            existing_lines.append(line)
            existing_ques.add(d.get("ques", ""))

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
        "web": WEB,
        "upstream_url": UPSTREAM,
    })
    next_id += 1


# --- /year/<year> + /year/<year>/<code> ---
for y in [2024, 2025, 2026]:
    add(f"Browse arXiv's year {y} index page. How many month buckets appear, and which month has the most entries?")
    for code in ["cs", "math", "stat", "physics", "eess"]:
        add(f"Open the arXiv year-{y} index filtered to {code}. Report the total number of entries shown.")
        add(f"On the arXiv /year/{y}/{code} page, pick any month and report the title of the very first paper listed.")
add("From the year 2026 view, navigate to year 2024 using the 'Other years' link. Report the new total entries.")
add("On the year 2025 view filtered to cs, report which months are missing entries (0-entry months not shown).")

# --- /catchup ---
add("Open the arXiv catchup page (default 7-day window). Report the total number of entries listed.")
add("Open /catchup and switch the window to 14 days using the 14d link. Report the new total.")
add("Open /catchup and switch the window to 30 days. What is the earliest submitted_date shown across the listing?")
for code in ["cs", "math", "stat", "physics"]:
    add(f"Open /catchup/{code} with a 7-day window. Report how many papers are listed.")
    add(f"On /catchup/{code} (7d), open the first paper in the listing and report its arxiv_id.")
add("From the catchup page, page forward to page 2 (if available). Report the arxiv_id of the first paper on that page.")

# --- /find/grp_<group> ---
for grp in ["cs", "math", "physics", "stat", "eess", "q-bio", "q-fin", "econ"]:
    add(f"Open the arXiv group landing /find/grp_{grp}. Report the number of archives listed and the total paper count.")
add("Open /find/grp_physics and click into 'astro-ph' from the table. Report the number of papers shown on that archive page.")
add("From /find/grp_math, navigate into the math-ph archive. What is the total entry count there?")
add("From /find/grp_cs, click the 'catchup' link next to cs. Confirm the page lands on /catchup/cs.")

# --- /a/<author>/recent ---
ranked_authors = [
    "Yann LeCun", "Geoffrey Hinton", "Yoshua Bengio", "Ilya Sutskever",
    "Andrew Ng", "Jeff Dean", "Fei-Fei Li", "Pieter Abbeel",
    "Sergey Levine", "Chelsea Finn", "Ian Goodfellow", "Christopher Manning",
    "Percy Liang", "Tamara Broderick",
]
for name in ranked_authors:
    add(f"Open the /a/{name}/recent feed on arXiv. Report how many submissions are shown.")
    add(f"On /a/{name}/recent, open the top paper and report its primary subject code.")
add("From an /a/<author>/recent page, click 'all submissions'. Confirm the route changes to /author/<name>.")
add("From an /a/<author>/recent page, click 'search author'. Report how many results the author search returns.")

# --- /help/<page> deep ---
for page in [
    "getting-started", "submit", "withdraw", "non-english", "figures",
    "subscribe", "store", "categories", "search", "downloads", "authors",
    "api", "faq", "contact", "members", "privacy", "copyright",
    "accessibility", "status", "who", "donate",
]:
    add(f"Open /help/{page} on the arXiv mirror. Quote one sentence (verbatim) from the body of that help page.")
add("On the /help/api page, copy the example API path shown in the <pre> block. What is the path?")
add("On /help/figures, list the figure formats arXiv accepts.")
add("On /help/non-english, what separator does arXiv require between multi-language abstracts?")
add("On /help/faq, find the question about peer review. What is the answer in one sentence?")
add("On /help/status, what is the current operational status indicator color?")

# --- Author-by-affiliation ---
for affil, hint in [
    ("MIT CSAIL", "alice_j"),
    ("Stanford AI Lab", "bob_c"),
    ("UC Berkeley Statistics", "carol_d"),
    ("Caltech Physics", "david_k"),
    ("Example University", "demouser"),
]:
    add(f"Find the user whose affiliation is '{affil}'. Report their username.")
add("Log in as alice.j@test.com / test1234, open Account, and confirm the affiliation 'MIT CSAIL' is shown.")
add("On the comments section of any paper that has author affiliations, locate one commenter whose affiliation contains 'Berkeley'. Report their full name.")

# --- Paper-by-grant-funding ---
add("Search arXiv abstracts for the phrase 'supported by' and report the arxiv_id of the top scored result.")
add("Use advanced search to find a paper whose abstract mentions 'NSF Award' (case-insensitive). Report its title.")
add("Use the basic search box to look up 'NIH grant' and report the number of search results.")
add("Search abstracts for 'ERC Advanced Grant' and report whether any paper is returned.")
add("Search abstracts for 'DARPA' and report the title of the highest-scored result.")

# --- find-replicate-of / similar-paper ---
add("Open arXiv:2104.08821 (SimCSE). On the abstract page, the 'related' section should suggest follow-up papers. Report the title of the second related paper.")
add("Open any paper in cs.CL. Use the 'Current browse context' sidebar to navigate to 'new' for the same subject. Report the new page's top arxiv_id.")
add("On the abstract page of arXiv:2303.08774, click into the listing for its primary subject ('recent'). Report the number of total entries listed in the listing header.")
add("Open arXiv:2412.03134 and report the next/prev navigation targets shown in the sidebar's browse context.")

# --- latex-source-download ---
add("Open arXiv:2412.03134 and click the 'TeX Source' link in the sidebar. Confirm the URL pattern is /e-print/<arxiv_id>.")
add("Open any paper page and click 'Other Formats'. Report the title of the page that loads.")
add("Open any paper page and click 'HTML (experimental)'. Report what you see at the top of the rendered page.")
add("From /abs/2104.08821, copy the BibTeX entry into the export form: visit /export, paste, and submit. Report the assigned export ID prefix.")

# --- coauthor-network ---
add("On the abstract page of arXiv:2104.08821, click the first author's name. From that author page, click any co-author (a different author from the same paper). Report that co-author's submission count.")
add("Pick any paper with ≥3 authors. Click each author in turn and report how many papers each has on arXiv (according to the author page).")
add("Find an author who appears on more than 2 papers in your local mirror. Report the author name and the number of papers.")

# --- Multi-step ---
add("Log in as alice.j@test.com / test1234, open Library, switch to the 'NLP' folder, and report how many papers are saved there.")
add("Log in as bob.c@test.com / test1234, open Starred Papers, and report the arxiv_id of the most recently starred paper.")
add("Log in as carol.d@test.com / test1234, go to Exports, open the ML Theory BibTeX export, and report the number of papers it contains.")
add("Log in as demouser / demodemo, add arXiv:2104.08821 to the Reading List folder, then open the library and confirm it appears.")
add("Log in as david.k@test.com / test1234, open Alerts, and report which category codes you are subscribed to.")
add("Log in as any benchmark user (test1234 password), open /catchup, then bookmark the first paper. Confirm it lands in the Reading List folder.")
add("Visit /find/grp_physics → click 'astro-ph' → click 'new' → bookmark the first result. After logging in, confirm it appears in /library.")

# --- Comment-thread (now that we have reply chains) ---
add("Open any paper that has multiple comments. Locate a comment whose title starts with 'Re:'. Report which user the @mention is addressed to.")
add("Open a paper with at least 3 comments. Report how many distinct usernames have commented.")
add("Find a paper with at least one 5-star comment. Report the paper's arxiv_id and the commenter's username.")
add("Find a comment whose body starts with 'On '. Report which paper it is attached to (arxiv_id).")

# --- New: archive listings with abstract-collapse interaction ---
add("Open a paper whose abstract is longer than ~720 characters. Click 'Read more ↓' and report the visible label after expansion.")
add("On any /abs page, hover over the sticky author/affiliation strip. What is shown for the second author's affiliation?")

# --- Library folder ops ---
add("Log in as alice.j@test.com / test1234. Create a new library folder named 'Probe Folder', then rename it to 'Probe Folder v2'. Report the folder list shown afterwards.")
add("Log in as bob.c@test.com / test1234. Move any paper from 'Favorites' to 'To Review'. Confirm the move via the library view.")

# --- Alerts and account settings ---
add("Log in as a test user, add an alert for category 'q-fin.RM'. Confirm the alert appears in /alerts.")
add("From the Account page, edit your bio to include the phrase 'WebHarbor reviewer'. Save and report the updated bio.")

# --- Store / blog ---
add("Open the arXiv blog index. Report the slug of the first post listed.")
add("Open the arXiv store. Report the price (or first item title) of the top-listed item.")

# --- API ---
add("Hit /api/stats and report the total number of papers exposed.")
add("Hit /api/papers/cs.AI and report the number of papers returned.")
add("Hit /api/papers/quant-ph and report the arxiv_id of the first paper in the response.")

# Save
with open(TASKS_FILE, "w") as fh:
    for line in existing_lines:
        fh.write(line + "\n")
    for t in new_tasks:
        fh.write(json.dumps(t, ensure_ascii=False) + "\n")

print(f"added {len(new_tasks)} new tasks; total now = {len(existing_lines) + len(new_tasks)}")
