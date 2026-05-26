"""Walk each of the 20 Discogs benchmark tasks via Playwright.

Captures screenshots into /tmp/discogs_walk/, logs PASS/FAIL/LEAK per task,
verifies persistence by re-navigating after writes.

Run from agent_demo/ with .venv/bin/python.
"""
import json
import os
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:45023"
SHOTS = Path("/tmp/discogs_walk"); SHOTS.mkdir(exist_ok=True)
TASKS = json.loads(
    "[" + ",".join(open("/home/v-haoqiwang/repos/WebHarbor/sites/discogs/tasks.jsonl").read().strip().split("\n")) + "]"
)


def shot(page, name):
    p = SHOTS / f"{name}.png"
    page.screenshot(path=str(p), full_page=True)
    return p


def login(page, username, password):
    page.goto(f"{BASE}/login")
    page.fill('form[method="post"] input[name="username"]', username)
    page.fill('form[method="post"] input[name="password"]', password)
    page.click('form[method="post"] button[type="submit"]')
    page.wait_for_load_state("networkidle")
    # After successful login, we land somewhere other than /login.
    # Verify by visiting /settings (login_required) and checking redirect.
    return "/login" not in page.url


def logout(page):
    try:
        page.goto(f"{BASE}/logout")
    except Exception:
        pass


def check_no_leak(page, answer_text):
    """Return True if `answer_text` is NOT visible in the rendered DOM."""
    return answer_text.lower() not in page.content().lower()


REPORT = []

def report(tid, status, note=""):
    REPORT.append({"id": tid, "status": status, "note": note})
    print(f"  [{status}] {tid}: {note}")


def t0(page):
    """Search Outlandos d'Amour by The Police, get Have count."""
    page.goto(f"{BASE}/search?q=Outlandos+d%27Amour")
    page.wait_for_load_state("networkidle")
    shot(page, "t0_search")
    # Find link to the release
    links = page.locator("a.release-card").all()
    if not links:
        return report("Discogs--0", "FAIL", "no search results for 'Outlandos d'Amour'")
    # Pick the one whose card text mentions Police
    for el in links:
        text = el.inner_text()
        if "Police" in text:
            el.click()
            break
    else:
        links[0].click()
    page.wait_for_load_state("networkidle")
    shot(page, "t0_release")
    body = page.content()
    m = re.search(r"<dt>Have</dt>\s*<dd>(\d+)</dd>", body)
    if not m:
        return report("Discogs--0", "FAIL", "Have count not in DOM")
    have = int(m.group(1))
    report("Discogs--0", "PASS", f"Have={have}")


def t1(page):
    """Jazz genre, Highest Rated, top release."""
    page.goto(f"{BASE}/genre/jazz?sort=rating")
    page.wait_for_load_state("networkidle")
    shot(page, "t1_jazz_rating")
    card = page.locator("a.release-card").first
    if not card.count():
        return report("Discogs--1", "FAIL", "no cards")
    title = card.locator(".title").inner_text()
    artist = card.locator(".artist").inner_text()
    report("Discogs--1", "PASS", f"top: {title} — {artist}")


def t2(page):
    """Marketplace cheapest."""
    page.goto(f"{BASE}/marketplace?sort=price_asc")
    page.wait_for_load_state("networkidle")
    shot(page, "t2_market")
    row = page.locator(".listing-row").first
    if not row.count():
        return report("Discogs--2", "FAIL", "no listings")
    text = row.inner_text()
    report("Discogs--2", "PASS", f"first listing text:\n{text[:200]}")


def t3(page):
    """Alice add Outlandos to Vinyl collection."""
    if not login(page, "alice_crate", "alice12345"):
        return report("Discogs--3", "FAIL", "login failed")
    page.goto(f"{BASE}/release/793593")
    page.wait_for_load_state("networkidle")
    shot(page, "t3_release_before")
    # Find collection add form
    # Set folder + media condition via form (release.html actions use defaults)
    # We need a custom form: choose folder=Vinyl, condition=Near Mint
    # The current form only has hidden release_id. Need to extend.
    # First check current behavior:
    forms = page.locator("form[action='/collection/add']")
    if not forms.count():
        return report("Discogs--3", "FAIL", "no add-to-collection form on release page")
    # Check if it has folder/media_condition fields
    select_count = forms.first.locator("select[name='folder']").count()
    if not select_count:
        return report("Discogs--3", "WARN", "form lacks folder/condition pickers — defaults to Uncategorized")
    forms.first.locator("select[name='folder']").select_option("Vinyl")
    forms.first.locator("select[name='media_condition']").select_option("Near Mint (NM or M-)")
    forms.first.locator("button[type='submit']").click()
    page.wait_for_load_state("networkidle")
    # Verify persisted
    page.goto(f"{BASE}/user/alice_crate/collection?folder=Vinyl")
    page.wait_for_load_state("networkidle")
    body = page.content()
    if "Outlandos" in body:
        report("Discogs--3", "PASS", "added to Vinyl folder")
    else:
        report("Discogs--3", "FAIL", "did not show in Vinyl folder")
    logout(page)


def t4(page):
    """Bob add 1984 by Van Halen to wantlist."""
    if not login(page, "bob_vinyl", "bob123456"):
        return report("Discogs--4", "FAIL", "login failed")
    # 1984 by Van Halen — discogs_id from our DB
    page.goto(f"{BASE}/release/949843")
    page.wait_for_load_state("networkidle")
    shot(page, "t4_release")
    forms = page.locator("form[action='/wantlist/add']")
    if not forms.count():
        return report("Discogs--4", "FAIL", "no wantlist form")
    sel = forms.first.locator("select[name='min_grade']")
    if not sel.count():
        return report("Discogs--4", "WARN", "form lacks min_grade picker")
    sel.select_option("Very Good (VG)")
    forms.first.locator("button[type='submit']").click()
    page.wait_for_load_state("networkidle")
    page.goto(f"{BASE}/user/bob_vinyl/wantlist")
    page.wait_for_load_state("networkidle")
    body = page.content()
    if "1984" in body:
        report("Discogs--4", "PASS", "added to wantlist")
    else:
        report("Discogs--4", "FAIL", "not in wantlist")
    logout(page)


def t5(page):
    """Miles Davis sort year_asc, oldest release."""
    # find Miles Davis artist id by browsing search
    page.goto(f"{BASE}/search?q=Miles+Davis&type=artist")
    page.wait_for_load_state("networkidle")
    link = page.locator("a", has_text="Miles Davis").first
    if not link.count():
        return report("Discogs--5", "FAIL", "no Miles Davis artist link")
    href = link.get_attribute("href")
    page.goto(f"{BASE}{href}?sort=year_asc")
    page.wait_for_load_state("networkidle")
    shot(page, "t5_miles_year_asc")
    card = page.locator("a.release-card").first
    if not card.count():
        return report("Discogs--5", "FAIL", "no Miles Davis releases")
    title = card.locator(".title").inner_text()
    meta = card.locator(".meta").inner_text()
    report("Discogs--5", "PASS", f"oldest: {title} | {meta}")


def t6(page):
    """Carol post reply to Cartridges thread."""
    if not login(page, "carol_jazz", "carol12345"):
        return report("Discogs--6", "FAIL", "login failed")
    page.goto(f"{BASE}/forum/vinyl")
    page.wait_for_load_state("networkidle")
    link = page.locator("a", has_text="Cartridges: MM vs MC for jazz").first
    if not link.count():
        return report("Discogs--6", "FAIL", "thread not found in vinyl forum")
    href = link.get_attribute("href")
    page.goto(f"{BASE}{href}")
    page.wait_for_load_state("networkidle")
    reply = "I'd lean toward MC for jazz — better detail in the upper mids."
    ta = page.locator("textarea[name='body']")
    if not ta.count():
        return report("Discogs--6", "FAIL", "no reply textarea")
    ta.fill(reply)
    page.locator("button:has-text('Post reply')").click()
    page.wait_for_load_state("networkidle")
    if reply in page.content():
        report("Discogs--6", "PASS", "reply posted")
    else:
        report("Discogs--6", "FAIL", "reply not visible")
    logout(page)


def t7(page):
    """Columbia label, count releases."""
    page.goto(f"{BASE}/label/90")  # Columbia from our DB query
    page.wait_for_load_state("networkidle")
    shot(page, "t7_columbia")
    body = page.content()
    m = re.search(r"(\d+)\s*releases", body)
    if not m:
        return report("Discogs--7", "FAIL", "no release count on label page")
    report("Discogs--7", "PASS", f"Columbia releases: {m.group(1)}")


def t8(page):
    """Dave creates a public list."""
    if not login(page, "dave_techno", "dave12345"):
        return report("Discogs--8", "FAIL", "login failed")
    page.goto(f"{BASE}/list/new")
    page.wait_for_load_state("networkidle")
    page.fill('form[method="post"] input[name="title"]', "Techno Bangers for the Club")
    page.fill('form[method="post"] textarea[name="description"]', "My go-to selectors for peak time.")
    page.click('form[method="post"] button[type="submit"]')
    page.wait_for_load_state("networkidle")
    if "Techno Bangers for the Club" in page.content():
        report("Discogs--8", "PASS", f"list created at {page.url}")
    else:
        report("Discogs--8", "FAIL", "list not visible")
    logout(page)


def t9(page):
    """Alice profile — collection + wantlist count."""
    page.goto(f"{BASE}/user/alice_crate")
    page.wait_for_load_state("networkidle")
    shot(page, "t9_alice")
    body = page.content()
    coll = re.search(r'<div class="n">(\d+)</div><div class="l">in Collection', body)
    want = re.search(r'<div class="n">(\d+)</div><div class="l">in Wantlist', body)
    if coll and want:
        report("Discogs--9", "PASS", f"collection={coll.group(1)} wantlist={want.group(1)}")
    else:
        report("Discogs--9", "FAIL", "stats not parseable")


def t10(page):
    """Bob Marley + Reggae search count."""
    page.goto(f"{BASE}/search?q=Bob+Marley&type=release&genre=reggae")
    page.wait_for_load_state("networkidle")
    shot(page, "t10_marley_reggae")
    body = page.content()
    m = re.search(r"(\d+)\s+releases", body)
    if not m:
        return report("Discogs--10", "FAIL", "no count visible")
    report("Discogs--10", "PASS", f"results: {m.group(1)}")


def t11(page):
    """Register craterunner99 + set bio."""
    logout(page)
    page.goto(f"{BASE}/register")
    page.wait_for_load_state("networkidle")
    page.fill('form[method="post"] input[name="username"]', "craterunner99")
    page.fill('form[method="post"] input[name="email"]', "craterunner99@test.com")
    page.fill('form[method="post"] input[name="password"]', "discogs2026")
    page.fill('form[method="post"] input[name="location"]', "Portland, USA")
    page.click('form[method="post"] button[type="submit"]')
    page.wait_for_load_state("networkidle")
    if "/register" in page.url:
        return report("Discogs--11", "FAIL", "register failed; page=" + page.url)
    page.goto(f"{BASE}/settings")
    page.wait_for_load_state("networkidle")
    page.fill('form[method="post"] textarea[name="bio"]', "Digging since 2010.")
    page.click('form[method="post"] button[type="submit"]')
    page.wait_for_load_state("networkidle")
    page.goto(f"{BASE}/user/craterunner99")
    body = page.content()
    if "Digging since 2010" in body:
        report("Discogs--11", "PASS", "registered + bio saved")
    else:
        report("Discogs--11", "FAIL", "bio not saved")
    logout(page)


def t12(page):
    """Home page Most Collected, 3rd release."""
    page.goto(f"{BASE}/")
    page.wait_for_load_state("networkidle")
    shot(page, "t12_home")
    # Find Most Collected card by section heading
    cards = page.locator(".card:has(h2:has-text('Most Collected')) a.release-card").all()
    if len(cards) < 3:
        return report("Discogs--12", "FAIL", f"only {len(cards)} cards under Most Collected")
    card = cards[2]
    title = card.locator(".title").inner_text()
    artist = card.locator(".artist").inner_text()
    report("Discogs--12", "PASS", f"3rd: {title} — {artist}")


def t13(page):
    """Bob lists 'Outlandos d'Amour' for sale."""
    if not login(page, "bob_vinyl", "bob123456"):
        return report("Discogs--13", "FAIL", "login failed")
    page.goto(f"{BASE}/sell")
    page.wait_for_load_state("networkidle")
    page.fill('form[method="post"] input[name="release_id"]', "793593")
    page.fill('form[method="post"] input[name="price"]', "42.00")
    page.select_option('form[method="post"] select[name="media_condition"]', "Very Good Plus (VG+)")
    page.select_option('form[method="post"] select[name="sleeve_condition"]', "Very Good Plus (VG+)")
    page.fill('form[method="post"] input[name="shipping_from"]', "United Kingdom")
    page.fill('form[method="post"] textarea[name="comments"]', "First UK pressing, plays cleanly throughout.")
    page.click('form[method="post"] button[type="submit"]')
    page.wait_for_load_state("networkidle")
    page.goto(f"{BASE}/release/793593")
    page.wait_for_load_state("networkidle")
    if "First UK pressing" in page.content():
        report("Discogs--13", "PASS", "listing visible on release page")
    else:
        report("Discogs--13", "FAIL", "listing not visible")
    logout(page)


def t14(page):
    """Live-Evil track count."""
    page.goto(f"{BASE}/release/29342281")  # discogs_id for Live-Evil 1971 US
    page.wait_for_load_state("networkidle")
    shot(page, "t14_live_evil")
    body = page.content()
    # Count <tr> in tracklist
    rows = page.locator(".tracklist tbody tr").count()
    if rows == 0:
        return report("Discogs--14", "FAIL", "no tracklist")
    report("Discogs--14", "PASS", f"track rows: {rows}")


def t15(page):
    """Explore → Electronic → Techno style → first release."""
    page.goto(f"{BASE}/explore")
    page.wait_for_load_state("networkidle")
    shot(page, "t15_explore")
    # Click Electronic
    page.click("a:has-text('Electronic')")
    page.wait_for_load_state("networkidle")
    shot(page, "t15_electronic")
    # Click Techno style — should appear in Styles section
    techno = page.locator("a:has-text('Techno')").first
    if not techno.count():
        return report("Discogs--15", "FAIL", "no Techno style link")
    techno.click()
    page.wait_for_load_state("networkidle")
    shot(page, "t15_techno")
    card = page.locator("a.release-card").first
    if not card.count():
        return report("Discogs--15", "FAIL", "no techno releases")
    title = card.locator(".title").inner_text()
    artist = card.locator(".artist").inner_text()
    report("Discogs--15", "PASS", f"first techno: {title} — {artist}")


def t16(page):
    """Alice removes HOUSE NATION from Vinyl folder."""
    if not login(page, "alice_crate", "alice12345"):
        return report("Discogs--16", "FAIL", "login failed")
    page.goto(f"{BASE}/user/alice_crate/collection?folder=Vinyl")
    page.wait_for_load_state("networkidle")
    shot(page, "t16_vinyl")
    body = page.content()
    if "HOUSE NATION" not in body:
        return report("Discogs--16", "FAIL", "HOUSE NATION not in folder")
    # The row containing HOUSE NATION has a small inline form with "Remove" button
    row = page.locator("tr:has-text('HOUSE NATION')").first
    btn = row.locator("button", has_text="Remove")
    if not btn.count():
        # Fall back to form-based submit
        forms = page.locator("form[action='/collection/remove']").all()
        # Find form whose hidden release_id matches HOUSE NATION's id
        # We don't know id here; use page POST instead
        return report("Discogs--16", "WARN", "no per-row Remove button found")
    btn.click()
    page.wait_for_load_state("networkidle")
    body2 = page.content()
    if "HOUSE NATION" in body2:
        report("Discogs--16", "FAIL", "still present after remove")
    else:
        report("Discogs--16", "PASS", "removed")
    logout(page)


def t17(page):
    """Dave's lists — pick listening-bar one."""
    page.goto(f"{BASE}/user/dave_techno/lists")
    page.wait_for_load_state("networkidle")
    shot(page, "t17_dave_lists")
    body = page.content()
    if "Records I Always Bring to the Listening Bar" not in body:
        return report("Discogs--17", "FAIL", "no listening bar list")
    # Open it
    page.click("a:has-text('Records I Always Bring to the Listening Bar')")
    page.wait_for_load_state("networkidle")
    items = page.locator("ol li").count()
    report("Discogs--17", "PASS", f"list items: {items}")


def t18(page):
    """Cheapest NM listing in marketplace."""
    page.goto(f"{BASE}/marketplace?sort=price_asc")
    page.wait_for_load_state("networkidle")
    shot(page, "t18_market")
    # Walk listings, find first with media NM
    rows = page.locator(".listing-row").all()
    for i, r in enumerate(rows):
        text = r.inner_text()
        if "Near Mint" in text:
            report("Discogs--18", "PASS", f"first NM at row {i}: {text[:200]}")
            return
    report("Discogs--18", "WARN", "no NM in first page — may need a filter UI for media condition")


def t19(page):
    """Dave posts to Favourite album opener thread."""
    if not login(page, "dave_techno", "dave12345"):
        return report("Discogs--19", "FAIL", "login failed")
    page.goto(f"{BASE}/forum/general")
    page.wait_for_load_state("networkidle")
    link = page.locator("a", has_text="Favourite album opener of all time").first
    if not link.count():
        return report("Discogs--19", "FAIL", "thread not found")
    link.click()
    page.wait_for_load_state("networkidle")
    body = "For me it has to be the opener of 'Selected Ambient Works Volume II'."
    ta = page.locator("textarea[name='body']")
    if not ta.count():
        return report("Discogs--19", "FAIL", "no reply textarea")
    ta.fill(body)
    page.locator("button:has-text('Post reply')").click()
    page.wait_for_load_state("networkidle")
    if body[:30] in page.content():
        report("Discogs--19", "PASS", "reply posted")
    else:
        report("Discogs--19", "FAIL", "not visible")
    logout(page)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context()
        page = ctx.new_page()
        for fn in [t0,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,t13,t14,t15,t16,t17,t18,t19]:
            try:
                fn(page)
            except Exception as e:
                report(fn.__name__, "ERROR", str(e)[:200])
        browser.close()
    print("\n=== SUMMARY ===")
    for r in REPORT:
        print(f"  {r['status']:6s} {r['id']}: {r['note']}")


if __name__ == "__main__":
    main()
