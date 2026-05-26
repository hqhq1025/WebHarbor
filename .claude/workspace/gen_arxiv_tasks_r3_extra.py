"""Second R3 task generation pass — adds ~100 more tasks to reach 400+."""
import json
from pathlib import Path

BASE = Path("/home/v-haoqiwang/repos/WebHarbor/sites/arxiv")
TASKS_FILE = BASE / "tasks.jsonl"
WEB = "http://localhost:40003/"
UPSTREAM = "https://arxiv.org/"

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
        "web": WEB,
        "upstream_url": UPSTREAM,
    })
    next_id += 1


# --- Cross-listing and subject-area depth ---
sub_pairs = [
    ("cs.SY", "eess.SY"), ("cs.NA", "math.NA"), ("stat.ML", "cs.LG"),
    ("cs.LG", "stat.ML"), ("eess.SY", "cs.SY"),
]
for a, b in sub_pairs:
    add(f"Open /list/{a}/recent and confirm at least one cross-listed paper from {b} appears in the entries. Report its arxiv_id.")

# --- Submission-history / versions ---
add("Find a paper that has more than one version listed in its submission history. Report the arxiv_id and the date of v2.")
add("On any /abs page, identify the date the 'first version uploaded' was, and compare it to the latest version date.")

# --- Filter and sort exhaustively ---
for code, label in [("cs.AI", "Artificial Intelligence"),
                    ("cs.CL", "Computation and Language"),
                    ("cs.CV", "Computer Vision"),
                    ("cs.LG", "Machine Learning"),
                    ("math.AG", "Algebraic Geometry"),
                    ("math.PR", "Probability"),
                    ("physics.optics", "Optics"),
                    ("astro-ph.CO", "Cosmology"),
                    ("quant-ph", "Quantum Physics")]:
    add(f"Open the recent listing for {code} ({label}). How many entries are shown on the first page?")
    add(f"On the {code} recent listing, scroll to find a paper submitted on the most recent announce day. Report its title.")

# --- Search filter combos ---
add("Use advanced search to find papers in cs.CL submitted in 2025 mentioning 'tokenizer'. Report the count.")
add("Use advanced search to look up papers with at least 5 authors. Report any one matching arxiv_id.")
add("Use advanced search to find papers with a DOI populated. Report the first DOI displayed.")
add("Search title for 'diffusion' and sort by submission date (newest first). Report the arxiv_id of the very first hit.")
add("Search abstract for 'reinforcement learning' and count results returned.")

# --- Sort variants ---
add("On any /list/cs.LG/recent listing, use the 'announce_date' grouping to identify how many distinct announce days appear on page 1.")

# --- Library folder operations (full) ---
add("Log in as carol.d / test1234, open the Library, switch to 'Diffusion' folder and report how many papers are in that folder.")
add("Log in as david.k / test1234, open the Library, then create a new folder 'Quantum Theory'. Report the success message.")
add("Log in as bob.c / test1234. From the library, remove any one paper from the 'Vision' folder. Confirm the count decreases by 1.")
add("Log in as alice.j / test1234. From /library, look at the 'NLP' folder. List the paper titles in the order shown.")

# --- Starred ops ---
add("Log in as a test user. Star arXiv:2104.08821, then unstar it. Confirm the starred count returns to its original value.")
add("Log in as alice.j / test1234. Go to /starred and report the arxiv_ids of all starred papers.")
add("Log in as carol.d / test1234. Open the abstract page of a paper in the ML Theory folder and click 'Star Paper'. Report the new starred count.")

# --- Export ops ---
add("Log in as carol.d / test1234. Open the Exports list. Report how many exports she currently has and their statuses.")
add("Log in as carol.d / test1234. Open the most recent ready Export and download the BibTeX file. Report the first entry's @article key.")
add("Log in as bob.c / test1234. Open his RIS export and report the export's format and paper_count.")
add("Log in as any user. From /export, create a new BibTeX export of any 2 papers. Report the assigned export_id.")
add("Log in as carol.d / test1234. Open one of her exports and reorder the items. Report the order before and after.")

# --- Comments user-side ---
add("Log in as alice.j / test1234. Open any paper that you commented on (your username appears under the comment). Post a follow-up comment with title 'Quick note'. Confirm it appears at the bottom of the list.")
add("Log in as bob.c / test1234. Find any of his own comments and delete it. Confirm the comment list shortens by 1.")
add("On the abstract page of a paper with at least 2 comments, report the comment titles in the order they appear.")
add("Find a paper with at least 4 comments. Report the average rating of the comments (numeric average of the 'rating' field).")

# --- Alerts CRUD ---
add("Log in as a benchmark user. Subscribe to alerts for 'q-bio.NC'. Confirm the alert shows up on /alerts.")
add("Log in as a benchmark user. Subscribe to alerts for 'astro-ph.SR', then delete the alert. Report the alert count before and after.")

# --- Account management ---
add("Log in as demouser / demodemo. Open the Edit Account page and report the placeholder shown for the bio field.")
add("Log in as alice.j / test1234. Visit /account/password and try changing the password to 'wrong' (≤8 chars). Report the validation error message shown.")

# --- More /year coverage ---
for y in [2022, 2023, 2024, 2025, 2026]:
    add(f"Open /year/{y}/quant-ph and report the total entries shown for quant-ph in {y}.")

# --- /catchup with archive variants ---
for code in ["cs.AI", "cs.CL", "cs.CV", "math.NA", "astro-ph.HE"]:
    add(f"Open /catchup/{code} with a 14-day window. Report how many papers are listed.")

# --- /find/grp navigation + sub-archive count ---
add("From /find/grp_physics, sort the archives mentally by paper count and report the largest. Compare your answer to what the table shows.")
add("From /find/grp_q-bio, click each archive (q-bio only has one). Report the total entry count for the q-bio archive.")
add("From /find/grp_cs, click 'recent' next to cs. Confirm the route is /list/cs/recent.")

# --- author/recent edge cases ---
add("Open /a/Alice/recent. The author 'Alice' may not exist in the local mirror; report what the page shows.")
add("Open /a/Yann LeCun/recent and the /author/Yann LeCun page in two tabs. Compare the entry counts.")

# --- Help search interaction ---
add("From /help (no sub-page), use the sidebar to navigate into 'API' and report the heading shown.")
add("From /help/api, follow any link back to /api/stats. Confirm the JSON response contains a 'total_papers' field.")

# --- Misc UI / asset ---
add("On the homepage, locate the 'Subjects' directory. How many top-level groups are listed?")
add("Open the index and report the value of total_papers shown.")
add("Open /category_taxonomy and report the number of subject area cards shown.")
add("Open /about and report the first paragraph's first sentence.")
add("Open /news and report the title of the most recent news item.")

# --- Direct-route abstract ---
add("Open /abs/2412.03134 and report the figures_count value shown in the metadata.")
add("Open /abs/2104.08821 and report the value of journal_ref.")
add("Open /abs/2303.08774 and report the n_authors count from the underlying record (by clicking through the author list).")

# Save
with open(TASKS_FILE, "w") as fh:
    for line in existing_lines:
        fh.write(line + "\n")
    for t in new_tasks:
        fh.write(json.dumps(t, ensure_ascii=False) + "\n")

print(f"added {len(new_tasks)} more tasks; total now = {len(existing_lines) + len(new_tasks)}")
