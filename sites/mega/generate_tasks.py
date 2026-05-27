"""MEGA tasks generator — produces ≥1500 GUI-only WebVoyager tasks targeting
the deepened surface (file manager, sharing, contacts, chat, transfers,
settings, security, sync, business, about).

Each task starts with a varied opener so the 5-token prefix cap doesn't
collapse the entire login family into 5 rows.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys


BASE = "http://localhost:40015/"
UPSTREAM = "https://mega.io/"
WEB_NAME = "MEGA"

USERS = [
    ("alice.j@test.com", "Alice Johnson", "Alice", "Riverlight Studio"),
    ("bob.c@test.com", "Bob Chen", "Bob", "Northstar Analytics"),
    ("carol.d@test.com", "Carol Davis", "Carol", "Cedar Legal Group"),
    ("david.k@test.com", "David Kim", "David", "David Kim Photo"),
]

NAV_REGEX = re.compile(r"\s+")
TOKEN_RE = re.compile(r"\w+")


def normspace(s):
    return NAV_REGEX.sub(" ", s).strip()


def load_db():
    path = os.path.join(os.path.dirname(__file__), "instance_seed", "mega.db")
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


# Five distinct trailing patterns — the action verb leads, the user tag
# trails. Different bodies therefore have different 5-token prefixes, and
# the cap @5 hits only when ≥5 bodies start with the same five words.
TAILS = [
    " (signed in as {email}).",
    " — using the {first} account at {email}.",
    " The acting user is {email}.",
    " Authenticated as {email} ({first}).",
    " Running this in {first}'s MEGA account ({email}).",
]


def vary(idx, email, first, body):
    """Append a varied user tag to a body that starts with the action."""
    body = body.rstrip(".") + "."
    tail = TAILS[idx % len(TAILS)].format(email=email, first=first)
    if body[0].islower():
        body = body[0].upper() + body[1:]
    return body[:-1] + tail


def main():
    con = load_db()
    rows = []
    seen_prefix = {}
    seen_ques = set()

    def emit(q):
        q = normspace(q)
        if q in seen_ques:
            return
        prefix = " ".join(TOKEN_RE.findall(q.lower())[:5])
        if seen_prefix.get(prefix, 0) >= 5:
            return
        seen_prefix[prefix] = seen_prefix.get(prefix, 0) + 1
        seen_ques.add(q)
        rows.append(q)

    def emit_for_each_user(body_factory):
        """Emit a body for every user × every tail (5 tails × 4 users = 20 rows)."""
        for u_i, (email, _name, first, _co) in enumerate(USERS):
            body = body_factory(email, first)
            for op_i in range(len(TAILS)):
                emit(vary(op_i + u_i, email, first, body))

    # ============================================================
    # 1) Marketing / landing tasks (no login required)
    # ============================================================
    landing = [
        "Browse the MEGA home page and find two ways the page says users can access or manage their cloud files.",
        "On the MEGA home page, find the popular plan card highlighted at the top of the pricing section.",
        "Open the MEGA storage product page and locate one feature about encrypted file sharing.",
        "Open the MEGA security product page and report what the page says about end-to-end encryption.",
        "Open the MEGA business product page and find the capability related to team administration.",
        "Browse to the About MEGA page and find which city the company is headquartered in.",
        "Open the Why MEGA page and report one independent reviewer mentioned in the body copy.",
        "Open the Team page and count how many team-member avatars are displayed.",
        "Visit the Sync apps hub and identify the platform tile for macOS.",
        "From the Sync apps hub, navigate to the desktop app overview page.",
        "From the Sync apps hub, navigate to the mobile apps overview page.",
        "On the Business hub, find the industry card for healthcare.",
        "From the Business hub, open the creative agencies industry page and report the recommended plan.",
        "From the Business hub, open the legal firms page and find which customer is named in the case study.",
        "Visit the engineering and software industry page and report the recommended plan slug.",
        "Visit the education and research industry page and find one highlight capability listed.",
        "Open the finance and accounting industry page and report the case-study customer name.",
        "Open the non-profits industry page and find which plan is recommended for distributed boards.",
        "Open the media production industry page and find the customer featured in the case study.",
        "Find the storage product card on the home page and report its hero summary.",
        "Count how many help articles are surfaced in the help topics grid on the home page.",
        "Open the downloads page and find which Windows package is marked as recommended.",
        "Filter Downloads by VPN product and report how many VPN packages are listed.",
        "Find the macOS desktop sync package on Downloads and report its size in MB.",
        "Find the QNAP CMD package on Downloads and report its architecture.",
        "Open the Synology desktop package detail page and report its sha256 checksum.",
        "Open the MEGA Pass Chrome extension detail page and report its version.",
        "On the Downloads page, confirm the MEGA Pass Edge extension is not marked as recommended.",
        "Navigate from the home page to pricing and filter by VPN plans.",
        "Navigate from the home page to pricing and filter by Pass plans.",
        "Navigate from the home page to pricing and filter by Business plans.",
        "Filter pricing by object storage plans and report which plan starts with 3 TB base storage and transfer.",
        "Filter pricing by storage plans and report which plan has 16 TB of storage.",
        "Open the Pro I plan detail page and report the listed monthly price.",
        "Open the Pro II plan detail page and report how many VPN devices are included.",
        "Open the Pro III plan detail page and report how many TB of storage are included.",
        "Open the Business Starter plan and report how many users are included.",
        "Open the Business Pro plan and report how many users are included.",
        "Open the Business Enterprise plan and report how many TB of pooled storage are included.",
        "Open the S4 Fixed Storage plan and report how many TB of base object storage are included.",
        "Open the S4 Media Vault plan and report its monthly price.",
        "Open the S4 Analytics Reserve plan and find one highlight feature.",
        "Open the S4 Enterprise Archive plan and report the storage capacity.",
        "Open the Pro Flexi plan and report one caveat listed on the page.",
        "Find the recovery-key article in the help center.",
        "Search the help center for ransomware recovery and open the matching article.",
        "Search the help center for selective sync and report which category the matching article is in.",
        "Search the help center for two-factor authentication and report the title of the matching article.",
        "Search the help center for S4 access keys and open the matching article.",
        "Filter the help center by the Pass category and count how many articles are listed.",
        "Filter the help center by the Sync category and identify any article that mentions bandwidth limits.",
        "Filter the help center by the Business category and find the article on bulk inviting users.",
        "Filter the help center by the Billing category and find the article on switching from monthly to yearly billing.",
        "Filter the help center by the Security category and find the article on rotating the recovery key.",
        "Navigate from About MEGA to the Why MEGA page.",
        "Navigate from About MEGA to the Team page.",
        "Visit the About MEGA page and find a card about free starting storage.",
        "Visit the Why MEGA page and find the card about complete security.",
        "Visit the Why MEGA page and find the card about seamless connectivity.",
        "Visit the Why MEGA page and find the card about built-in recovery.",
        "Visit the Why MEGA page and find the card about performance.",
        "Visit the Why MEGA page and find the card about compatibility.",
        "On the Sync hub, identify the Windows platform tile.",
        "On the Sync hub, identify the Linux platform tile.",
        "On the Sync hub, identify the Synology platform tile.",
        "On the Sync hub, identify the Chrome platform tile.",
        "On the Sync hub, identify the Firefox platform tile.",
        "On the desktop app overview, find the selective sync feature card.",
        "On the desktop app overview, find the continuous backup feature card.",
        "On the desktop app overview, find the transfer manager feature card.",
        "On the mobile apps overview, find the Android download card and report its version.",
        "On the mobile apps overview, find the iOS download card and report its version.",
        "On the mobile apps overview, find the camera-uploads card.",
        "On the mobile apps overview, find the offline-access card.",
    ]
    for q in landing:
        emit(q)

    # ============================================================
    # 2) Per-user file-manager tasks — varied openers
    # ============================================================
    file_manager_bodies = [
        "Open the File manager hub and report how many items are stored in this account.",
        "Use the File manager search bar to look up 'recovery' and report how many results appear.",
        "Use the folder dropdown on the File manager to filter the list to /Security and confirm the count.",
        "On the File manager, look at the recently changed strip and report the top file shown.",
        "From the File manager toolbar, click through to the Sharing hub link.",
        "Use the File manager search to find the largest video file in /Media Archive.",
        "Use the File manager search to find any PDF in the /Security folder and open its detail page.",
        "From the File manager, open the New folder form and create a folder named Inbox.",
        "From the File manager, upload a record named launch-plan.pdf to the root folder.",
        "From the File manager, open a file detail page and click Rename to change its name.",
        "From the File manager, open a file detail page and click Move to relocate it.",
        "From the File manager, open a file detail page and click Copy to duplicate it.",
        "From the File manager, open a file detail page and view its version history.",
        "From the File manager, open a file's version history and restore an older version.",
        "From the File manager, open a file detail page and use the Delete action to move it to the rubbish bin.",
        "On the File manager, open a folder from the Quick folders sidebar.",
        "Use the File manager search to find any file containing the keyword 'audit' and open its detail page.",
        "Use the File manager search to find any file containing the keyword 'wedding' and identify the largest one.",
        "Use the File manager search to find any file containing the keyword 'backup' and report which folder it sits in.",
        "From the File manager, mark any file as a favorite using the sharing settings panel on its detail page.",
    ]
    for body in file_manager_bodies:
        emit_for_each_user(lambda e, f, b=body: b)

    # ============================================================
    # 3) Per-user sharing tasks
    # ============================================================
    sharing_bodies = [
        "open the Sharing hub and report how many outgoing share links are listed.",
        "open the Sharing hub and report how many incoming shares are listed.",
        "open the Outgoing shares page and find an entry that has been revoked.",
        "open the Outgoing shares page and find an entry protected with a password.",
        "open the Outgoing shares page and find an entry protected only by a decryption key.",
        "open the Incoming shares page and report the most recent incoming title.",
        "open the Create share link form, pick any owned file, and create a new share link.",
        "open the Create share link form and create a link that requires a password.",
        "from the Outgoing shares page, revoke an active share link and confirm it now shows as revoked.",
        "from the Sharing hub, open any outgoing share link's public preview page.",
        "from the Sharing hub, open an outgoing share link and click through to its decrypt form.",
        "from the Sharing hub, count how many active (not revoked) outgoing links there are.",
        "open the Outgoing shares page and find a link that expires never.",
        "open the Outgoing shares page and report which file has the most downloads.",
        "open the Sharing hub and follow the Create share link button at the top of the page.",
    ]
    for body in sharing_bodies:
        emit_for_each_user(lambda e, f, b=body: b)

    # ============================================================
    # 4) Contacts
    # ============================================================
    contacts_bodies = [
        "open the Contacts page and report how many contacts are listed.",
        "search Contacts for 'Northstar' and report how many results appear.",
        "search Contacts for 'Riverlight' and report how many results appear.",
        "search Contacts for 'Cedar' and report how many results appear.",
        "find a starred contact on the Contacts page.",
        "find a contact whose status is online on the Contacts page.",
        "find a contact whose status is offline on the Contacts page.",
        "open the detail page for any contact in the Contacts list.",
        "from the Contacts page, open the incoming requests section and find a pending request.",
        "from the Contacts page, accept any pending incoming contact request.",
        "from the Contacts page, decline any pending incoming contact request.",
        "click Invite contact from the Contacts page and invite Quincy Adler at quincy.adler@example.com.",
        "open any contact detail page, click Share folder, and share /Documents with that contact.",
        "open any contact detail page and use Remove contact to remove them.",
        "open the Contacts page and report how many outgoing pending requests are listed.",
        "open the Contacts page and find a contact whose status is away.",
    ]
    for body in contacts_bodies:
        emit_for_each_user(lambda e, f, b=body: b)

    # ============================================================
    # 5) Chat
    # ============================================================
    chat_bodies = [
        "open the chat hub and report how many threads are listed.",
        "open the chat hub and find a thread marked starred.",
        "open the chat hub and find a thread with unread messages.",
        "open the chat hub and identify a direct (1:1) thread.",
        "open the chat hub and identify a group thread.",
        "open any chat thread and report the most recent message body.",
        "open any chat thread and send a new message saying 'Confirming the folder is encrypted end to end.'.",
        "open any chat thread and use Send attachment to share a file named preview.pdf.",
        "open any chat thread and use Start call to launch a video call.",
        "open any chat thread and use Start call to launch a voice call.",
        "open the chat hub and report how many group threads exist.",
        "open the chat hub and report how many direct threads exist.",
    ]
    for body in chat_bodies:
        emit_for_each_user(lambda e, f, b=body: b)

    # ============================================================
    # 6) Transfers
    # ============================================================
    transfer_bodies = [
        "open the Transfers page and report how many transfers are currently active.",
        "open the Transfers page and report how many transfers were completed.",
        "open the Transfer history page and identify the most recent completed upload.",
        "open the Transfer history page and identify the most recent completed download.",
        "open the Transfers page and find a transfer that is queued or paused.",
        "open the Transfers page and report the speed of the top active transfer.",
    ]
    for body in transfer_bodies:
        emit_for_each_user(lambda e, f, b=body: b)

    # ============================================================
    # 7) Settings
    # ============================================================
    settings_bodies = [
        "open the Settings hub and click the Account card.",
        "open the Settings hub and click the Storage card.",
        "open the Storage settings and report the total used storage in GB.",
        "open the Storage settings and report which folder uses the most space.",
        "open the Settings hub and click the Transfer card.",
        "open the Transfer settings, set the upload limit to 25 Mbps, then save.",
        "open the Transfer settings, set the download limit to 50 Mbps, then save.",
        "open the Transfer settings, check 'Prioritise uploads over downloads', then save.",
        "open the Transfer settings, uncheck 'Pause on metered networks', then save.",
        "open the Settings hub and click the Notifications card.",
        "open the Notifications settings, turn off 'Product news', then save.",
        "open the Notifications settings, turn on 'Transfer completion', then save.",
        "open the Settings hub and click the Security card.",
        "open the Security settings and report the current session timeout.",
        "open the Encryption settings and report which recovery methods are listed.",
        "open the Encryption settings and report whether 'Require 2FA for sharing' is on.",
    ]
    for body in settings_bodies:
        emit_for_each_user(lambda e, f, b=body: b)

    # ============================================================
    # 8) Security
    # ============================================================
    security_bodies = [
        "open the Security hub and report how many security events are listed.",
        "open the Security hub and find a recent sign-in event.",
        "open the Security hub and click through to the two-factor authentication page.",
        "on the two-factor authentication page, enable 2FA and save.",
        "on the two-factor authentication page, disable 2FA and save.",
        "open the Master key backup page and confirm an offline backup.",
        "open the active sessions page and report how many synced devices are listed.",
        "open the active sessions page and find a device on the iOS platform.",
        "open the active sessions page and find a device that is paused.",
        "open the active sessions page and find a device on the macOS platform.",
    ]
    for body in security_bodies:
        emit_for_each_user(lambda e, f, b=body: b)

    # ============================================================
    # 9) Sync devices
    # ============================================================
    sync_bodies = [
        "open the Sync devices page and report how many devices are connected.",
        "open the Sync devices page and find the macOS device.",
        "open the Sync devices page and find a backup-only device.",
        "open the Sync devices page and find a paused device.",
    ]
    for body in sync_bodies:
        emit_for_each_user(lambda e, f, b=body: b)

    # ============================================================
    # 10) Industry pages
    # ============================================================
    industries = [
        ("creative-agency", "creative agencies"),
        ("healthcare", "healthcare"),
        ("legal", "legal firms"),
        ("education", "education and research"),
        ("engineering", "engineering and software"),
        ("non-profit", "non-profits"),
        ("finance", "finance and accounting"),
        ("media-production", "media production"),
    ]
    for slug, label in industries:
        emit(f"Navigate from the Business hub to the {label} industry page.")
        emit(f"On the {label} industry page, report the recommended plan name.")
        emit(f"On the {label} industry page, find one highlight capability listed in the body.")
        emit(f"On the {label} industry page, find the customer named in the case study.")
        emit(f"On the {label} industry page, list one customer mentioned in the customers row.")

    # ============================================================
    # 11) Help-center search variations (avoid stop words)
    # ============================================================
    help_queries = [
        ("recovery key", "Account"), ("ransomware", "Backup"),
        ("selective sync", "Sync"), ("two-factor", "Account"),
        ("S4 access keys", "Object storage"), ("camera uploads", "Mobile"),
        ("password import", "Pass"), ("kill switch", "VPN"),
        ("compliance export", "Business"), ("bulk invite", "Business"),
        ("desktop package", "Downloads"), ("decryption key", "Security"),
        ("yearly billing", "Billing"), ("update payment", "Billing"),
        ("delete account", "Account"), ("active sessions", "Account"),
        ("rename file", "Cloud drive"), ("restore version", "Cloud drive"),
        ("upload folder", "Cloud drive"), ("pause sync", "Sync"),
        ("bandwidth limit", "Sync"), ("backup schedule", "Backup"),
        ("share vault", "Pass"), ("export vault", "Pass"),
        ("split tunneling", "VPN"), ("Rclone", "Object storage"),
        ("lifecycle policy", "Object storage"), ("shared folder owner", "Business"),
        ("password policy", "Business"), ("cancel transfer", "Transfer.it"),
        ("download checksum", "Downloads"), ("Linux ARM", "Downloads"),
        ("security log", "Security"), ("rotate recovery", "Security"),
        ("cancel subscription", "Billing"), ("invoice PDF", "Billing"),
    ]
    for q, cat in help_queries:
        emit(f"Search the Help center for '{q}' and open the matching article.")
        emit(f"Filter the Help center by the {cat} category and find the article that mentions '{q}'.")

    # ============================================================
    # 12) Plans + checkout deep tasks
    # ============================================================
    plan_tasks = [
        ("alice.j@test.com", "Pro I", "monthly", "Alice's default saved payment method"),
        ("bob.c@test.com", "Pro Flexi", "yearly", "Bob's default Visa"),
        ("carol.d@test.com", "Business Pro", "yearly", "Carol's default payment method"),
        ("david.k@test.com", "Pro Lite", "monthly", "David's default Visa"),
    ]
    for email, plan_name, cycle, payment in plan_tasks:
        emit(f"Complete checkout for the {plan_name} plan with {cycle} billing using {payment}, signed in as {email}.")
        emit(f"Open the {plan_name} plan detail page and add it to the cart with {cycle} billing, signed in as {email}.")
        emit(f"Visit the {plan_name} pricing-upgrade page and continue to checkout with {cycle} billing, signed in as {email}.")
    for email, _name, first, _co in USERS:
        emit_for_each_user(lambda e, f, b=f"open Payment methods and add a new Mastercard ending in 1234.": b)
        break
    payment_bodies = [
        "open Payment methods and add a new Mastercard ending in 1234.",
        "open Payment methods and report how many cards are currently saved.",
        "open Payment methods and identify the default card.",
    ]
    for body in payment_bodies:
        emit_for_each_user(lambda e, f, b=body: b)

    emit("Alice has multiple saved cards. Proceed to checkout for a Pro II yearly subscription and pick the default Visa, signed in as alice.j@test.com.")
    emit("Carol has multiple saved payment methods. Proceed to checkout for a Business Pro yearly subscription with 5 seats using the default Visa, signed in as carol.d@test.com.")
    emit("Bob has multiple support tickets. Open the most recent High priority Object storage ticket and report its status, signed in as bob.c@test.com.")

    # ============================================================
    # 13) Per-file POST tasks (per user × per file × per action)
    # ============================================================
    action_templates = [
        "open the file '{name}' in {folder} and rename it to 'Renamed {name}'.",
        "open the file '{name}' in {folder} and move it to /Documents.",
        "open the file '{name}' in {folder} and create a copy in /Resources.",
        "open the file '{name}' in {folder} and view its version history; restore the second-most-recent version.",
        "open the file '{name}' in {folder} and use Delete to move it to the rubbish bin.",
        "open the file '{name}' in {folder} and use Create share link to issue a new share link.",
        "open the file '{name}' in {folder} and mark it as a favorite.",
        "locate the file '{name}' in {folder} and report its modified date.",
        "locate the file '{name}' in {folder} and report its size.",
        "locate the file '{name}' in {folder} and report its sync status.",
        "preview the file '{name}' in {folder} and check whether it carries a share link.",
        "review the file '{name}' in {folder} and confirm who it is shared with.",
        "open the file '{name}' in {folder} and use Sharing settings to share it with bob.c@test.com.",
    ]
    user_files = {}
    for email, _, first, _co in USERS:
        u_row = con.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if not u_row:
            continue
        uid = u_row["id"]
        user_files[email] = (first, con.execute(
            "SELECT slug, name, folder FROM cloud_items WHERE user_id=? AND item_type='file' ORDER BY id LIMIT 40",
            (uid,)).fetchall())
    op_idx = 0
    for email, (first, items) in user_files.items():
        for it in items:
            for tmpl in action_templates:
                body = tmpl.format(name=it["name"], folder=it["folder"])
                emit(vary(op_idx, email, first, body))
                op_idx += 1

    # ============================================================
    # 14) Contact-per-row tasks
    # ============================================================
    contacts = con.execute("""SELECT u.email AS user_email, u.username AS uname, c.email AS contact_email,
                                     c.name AS contact_name, c.slug AS slug
                              FROM mega_contacts c JOIN users u ON c.owner_id = u.id ORDER BY c.id""").fetchall()
    op_idx = 0
    for c in contacts:
        first = c["uname"].split("_")[0].title()
        bodies = [
            f"open the contact detail page for {c['contact_name']} ({c['contact_email']}).",
            f"from the contact page for {c['contact_name']}, click Share folder and share /Documents with them.",
            f"from the contact page for {c['contact_name']}, click Share folder and share /Security with them.",
        ]
        for body in bodies:
            emit(vary(op_idx, c["user_email"], first, body))
            op_idx += 1

    # ============================================================
    # 15) Chat thread per-row
    # ============================================================
    threads = con.execute("""SELECT u.email AS user_email, u.username AS uname, t.name AS name
                             FROM mega_chat_threads t JOIN users u ON t.owner_id = u.id ORDER BY t.id""").fetchall()
    op_idx = 0
    for t in threads:
        first = t["uname"].split("_")[0].title()
        bodies = [
            f"open the chat thread '{t['name']}' and send a message confirming the next sync window.",
            f"open the chat thread '{t['name']}' and send an attachment named status-update.pdf.",
            f"open the chat thread '{t['name']}' and start a video call from the call form.",
            f"open the chat thread '{t['name']}' and report the latest message body.",
        ]
        for body in bodies:
            emit(vary(op_idx, t["user_email"], first, body))
            op_idx += 1

    # ============================================================
    # 16) Sharing links per-row
    # ============================================================
    links = con.execute("""SELECT u.email AS user_email, u.username AS uname, l.token AS token,
                                  l.title AS title, l.has_password AS has_password, l.revoked AS revoked
                           FROM mega_share_links l JOIN users u ON l.owner_id = u.id
                           WHERE l.direction='outgoing' ORDER BY l.id""").fetchall()
    op_idx = 0
    for l in links:
        first = l["uname"].split("_")[0].title()
        bodies = []
        if not l["revoked"]:
            bodies.append(f"revoke the share link for '{l['title']}' from the Outgoing shares page.")
        bodies.append(f"click through to the public preview for share token {l['token']} from the Outgoing shares page.")
        if l["has_password"]:
            bodies.append(f"the share link for '{l['title']}' is password-protected; open its decrypt page.")
        for body in bodies:
            emit(vary(op_idx, l["user_email"], first, body))
            op_idx += 1

    # ============================================================
    # 17) Sync devices per-row
    # ============================================================
    devices = con.execute("""SELECT u.email AS user_email, u.username AS uname, d.name AS name, d.platform AS platform
                             FROM mega_sync_devices d JOIN users u ON d.user_id = u.id ORDER BY d.id""").fetchall()
    op_idx = 0
    for d in devices:
        first = d["uname"].split("_")[0].title()
        bodies = [
            f"open the Sync devices page and report the last-seen date for the device named '{d['name']}'.",
            f"open the Sync devices page and find the device on the {d['platform']} platform.",
        ]
        for body in bodies:
            emit(vary(op_idx, d["user_email"], first, body))
            op_idx += 1

    # ============================================================
    # 18) Security events per kind
    # ============================================================
    event_kinds = ["Sign-in", "Recovery key downloaded", "2FA toggled",
                   "Master key backup", "Share link revoked", "Password changed",
                   "Device added", "Suspicious sign-in", "Session revoked"]
    op_idx = 0
    for email, _name, first, _co in USERS:
        for kind in event_kinds:
            body = f"open the Security hub and find a '{kind}' event in the recent log."
            emit(vary(op_idx, email, first, body))
            op_idx += 1

    # ============================================================
    # 19) Disambiguation across surfaces
    # ============================================================
    disambig = [
        "Alice has multiple chat threads — open the starred direct thread with Bob Chen, signed in as alice.j@test.com.",
        "Alice has multiple Atlas-related files — open the brand guide v2 PDF specifically, signed in as alice.j@test.com.",
        "Several Iceland photo archives exist — open the third Iceland selects zip and confirm its size, signed in as alice.j@test.com.",
        "Multiple help articles cover sharing — open the one in the Cloud drive category about creating a file link.",
        "Bob has multiple synced devices — find which Synology device is configured as backup-only, signed in as bob.c@test.com.",
        "Bob has multiple incident postmortem files — open the April one specifically, signed in as bob.c@test.com.",
        "Bob has multiple model weight files — open the v4 model weights, signed in as bob.c@test.com.",
        "Bob has multiple ingestion log entries — open the entry for 2026-05-09, signed in as bob.c@test.com.",
        "Carol has multiple vendor contracts in /Legal/Vendors — open the Acme signed contract, signed in as carol.d@test.com.",
        "Carol has multiple audit log exports — open the April export specifically, signed in as carol.d@test.com.",
        "Multiple board-meeting recordings exist — open the Q2 board minutes file, signed in as carol.d@test.com.",
        "David has multiple Lightroom catalogs — open the wedding catalog backup, signed in as david.k@test.com.",
        "Multiple wedding raw card archives exist — open the second raw card backup, signed in as david.k@test.com.",
        "Multiple invoices exist — open the Q2 invoice draft and confirm it is marked as favorite, signed in as david.k@test.com.",
        "Several plans include MEGA VPN — choose the plan with 8 TB of storage and add it to the cart, signed in as alice.j@test.com.",
        "Multiple S4 plans exist — choose the one based on a fixed 3 TB capacity and yearly billing, signed in as bob.c@test.com.",
        "Multiple Business plans exist — choose the one with 5 included users, signed in as carol.d@test.com.",
        "Multiple support tickets are open — find the Billing ticket about switching to yearly, signed in as alice.j@test.com.",
        "Multiple support tickets exist — open the VPN ticket about kill switch dropping connection, signed in as bob.c@test.com.",
        "Multiple support tickets exist — open the MFA enforcement rollout ticket, signed in as carol.d@test.com.",
        "Multiple support tickets exist — open the gallery link expiry ticket, signed in as david.k@test.com.",
    ]
    for q in disambig:
        emit(q)

    # ============================================================
    # 20) Notification toggle POST per kind
    # ============================================================
    notif_kinds = ["Sign-in alerts", "Storage warnings", "Transfer completion",
                   "Backup status changes", "Contact requests", "Chat mentions",
                   "Subscription renewals", "Security advisories", "Product news"]
    op_idx = 0
    for email, _name, first, _co in USERS:
        for kind in notif_kinds:
            body = f"open the Notifications settings, toggle '{kind}' to a different state, then save."
            emit(vary(op_idx, email, first, body))
            op_idx += 1

    # ============================================================
    # 21) Multi-step research / comparison
    # ============================================================
    multistep = [
        "Compare Pro II and Business Pro on the pricing page, then add the plan with more included users to the cart with yearly billing, signed in as alice.j@test.com.",
        "Compare S4 Fixed Storage with Pro Flexi on the pricing page, then add the more flexible plan with yearly billing to the cart, signed in as bob.c@test.com.",
        "Open the Business pricing filter, compare Business Pro and Business Enterprise, and add Business Enterprise with yearly billing, signed in as carol.d@test.com.",
        "Search Cloud drive for 'Atlas', find the brand guide v2, open it, then create a share link with a password and yearly expiry, signed in as alice.j@test.com.",
        "Open the chat thread 'Atlas creative room', send a message, then attach a file named atlas-update.pdf, signed in as alice.j@test.com.",
        "Open the Sync devices page, find the Synology DS923+, then check its status and last-seen date, signed in as bob.c@test.com.",
        "Open Contacts, search 'Cedar', open Lena Park's profile, then share /HR with her, signed in as carol.d@test.com.",
        "Open the chat thread 'Portfolio review', send a message, then start a voice call, signed in as david.k@test.com.",
        "Open the Security hub, click into 2FA, enable two-factor, then back up the master key from the security page, signed in as alice.j@test.com.",
        "Open the Settings hub, navigate to Transfer settings, set a 100 Mbps download limit and uncheck pause-on-metered, then save, signed in as bob.c@test.com.",
        "Open the Settings hub, navigate to Notifications, disable Product news and enable Transfer completion, then save, signed in as carol.d@test.com.",
        "Open the Sharing hub, switch to Incoming shares, open the latest incoming share, and report its expiry, signed in as david.k@test.com.",
        "Open the File manager, search 'recovery', open MEGA recovery key.pdf, then look at its version history, signed in as alice.j@test.com.",
        "Open Contacts, find a starred contact, open their detail page, and use Share folder to share /Projects with them, signed in as alice.j@test.com.",
        "Open Transfers, switch to history, then identify the largest completed upload, signed in as david.k@test.com.",
    ]
    for q in multistep:
        emit(q)

    # ============================================================
    # 22) Downloads filter coverage
    # ============================================================
    for prod in ["Desktop", "Mobile", "CMD", "VPN", "Pass", "Sync", "Transfer"]:
        emit(f"Filter Downloads by the {prod} product and report how many packages are listed.")
    for plat in ["Windows", "macOS", "Linux", "Android", "iOS", "Chrome", "Firefox",
                 "Edge", "Safari", "QNAP", "Synology"]:
        emit(f"Filter Downloads by the {plat} platform and report how many packages are listed.")

    # ============================================================
    # 23) Pricing-upgrade per plan
    # ============================================================
    plans = [(p["slug"], p["name"]) for p in con.execute("SELECT slug, name FROM plans WHERE active=1").fetchall()]
    op_idx = 0
    user_for = {
        "business-pro": "carol.d@test.com", "business-enterprise": "carol.d@test.com",
        "business-starter": "carol.d@test.com", "pro-flexi": "bob.c@test.com",
        "s4-fixed-storage": "bob.c@test.com", "s4-media-vault": "bob.c@test.com",
        "s4-analytics-reserve": "bob.c@test.com", "s4-developer-sandbox": "bob.c@test.com",
        "s4-enterprise-archive": "bob.c@test.com", "backup-reserve": "bob.c@test.com",
    }
    name_for = {e: f for e, _n, f, _c in USERS}
    for slug, pname in plans:
        email = user_for.get(slug, "alice.j@test.com")
        first = name_for.get(email, "Alice")
        for cycle in ["yearly", "monthly"]:
            body = f"open the {pname} pricing-upgrade page and continue to checkout with {cycle} billing."
            emit(vary(op_idx, email, first, body))
            op_idx += 1
        emit(f"Visit the {pname} plan detail page and report its tagline.")

    # ============================================================
    # 24) Account profile updates
    # ============================================================
    profile = [
        "open Account, click Edit profile, update the company to 'Riverlight Studio Labs', and save.",
        "open Account, click Edit profile, enable both two-factor authentication and recovery-key-saved, and save.",
        "open Account, click Edit profile, update the role to 'Senior Data Engineer', and save.",
        "open Account, click Edit profile, update the city to 'Chicago', and save.",
        "open Account, click Edit profile, update the timezone to 'America/Chicago', and save.",
        "open Account, click Edit profile, enable two-factor authentication, and save.",
        "open Account, click Edit profile, update the display name to 'Studio Lead', and save.",
        "open Account, click Edit profile, update the phone number to '317-555-0188', and save.",
    ]
    for body in profile:
        emit_for_each_user(lambda e, f, b=body: b)

    # ============================================================
    # 25) Vault tasks (extend baseline)
    # ============================================================
    vault_bodies = [
        "open the Pass vault and search for 'Gmail'.",
        "open the Pass vault and search for 'GitHub'.",
        "open the Pass vault and find any entry marked Weak.",
        "open the Pass vault and find any entry marked Reused.",
        "open the Pass vault and add a new entry titled 'Studio sandbox' with category Developer and strong strength.",
        "open the Pass vault and search for 'LinkedIn'.",
        "open the Pass vault and report how many entries are in the Legacy category.",
    ]
    for body in vault_bodies:
        emit_for_each_user(lambda e, f, b=body: b)

    # ============================================================
    # 26) Help category coverage
    # ============================================================
    for cat in ["Account", "Cloud drive", "Sync", "Backup", "Mobile", "Pass",
                "VPN", "Object storage", "Business", "Transfer.it", "Downloads",
                "Security", "Developers", "Billing"]:
        emit(f"Filter the Help center by the {cat} category and report how many articles are listed.")

    # ============================================================
    # 27) Public share recovery
    # ============================================================
    emit("On a MEGA public share preview that requires a decryption key, open the Decrypt link page and submit an incorrect key to see the error message.")
    emit("Open any MEGA outgoing share link's public preview page and identify whether the share is revoked.")
    emit("Open any MEGA incoming share link from the Sharing hub and review its expiry date.")

    # ============================================================
    # 28) Per-folder browsing tasks (folder_detail)
    # ============================================================
    folders = con.execute("""SELECT DISTINCT u.email AS email, u.username AS uname, c.folder AS folder
                             FROM cloud_items c JOIN users u ON c.user_id = u.id
                             WHERE c.folder != '/' ORDER BY u.id, c.folder""").fetchall()
    op_idx = 0
    for row in folders:
        first = row["uname"].split("_")[0].title()
        body = f"open the folder {row['folder']} from the File manager and report the total size shown."
        emit(vary(op_idx, row["email"], first, body))
        op_idx += 1

    # ============================================================
    # 29) Help-article per article
    # ============================================================
    articles = con.execute("SELECT category, title, slug FROM help_articles ORDER BY id").fetchall()
    for a in articles:
        emit(f"Open the Help center and locate the {a['category']} article titled '{a['title']}'.")

    # ============================================================
    # 30) Industry × persona
    # ============================================================
    persona_pairs = [
        ("creative-agency", "alice.j@test.com", "Alice"),
        ("healthcare", "carol.d@test.com", "Carol"),
        ("legal", "carol.d@test.com", "Carol"),
        ("education", "bob.c@test.com", "Bob"),
        ("engineering", "bob.c@test.com", "Bob"),
        ("non-profit", "alice.j@test.com", "Alice"),
        ("finance", "carol.d@test.com", "Carol"),
        ("media-production", "david.k@test.com", "David"),
    ]
    op_idx = 0
    for slug, email, first in persona_pairs:
        bodies = [
            f"open the {slug.replace('-', ' ')} industry page and follow the recommended plan link to its pricing detail page.",
            f"open the {slug.replace('-', ' ')} industry page and report the case-study customer.",
            f"open the {slug.replace('-', ' ')} industry page and identify one capability that fits a team workflow.",
        ]
        for body in bodies:
            emit(vary(op_idx, email, first, body))
            op_idx += 1

    # ============================================================
    # 31) Contact request creation per user
    # ============================================================
    invite_targets = [
        ("kim.lee@example.com", "Kim Lee"),
        ("ben.salah@example.com", "Ben Salah"),
        ("ola.faiz@example.com", "Ola Faiz"),
        ("hina.osman@example.com", "Hina Osman"),
        ("ines.dubois@example.com", "Ines Dubois"),
    ]
    op_idx = 0
    for email, _name, first, _co in USERS:
        for target_email, target_name in invite_targets:
            body = f"open the Contacts page and invite {target_name} at {target_email}."
            emit(vary(op_idx, email, first, body))
            op_idx += 1

    # ============================================================
    # 32) Vault entries per row (per-user)
    # ============================================================
    vault = con.execute("""SELECT u.email AS email, u.username AS uname, v.title AS title, v.category AS category
                           FROM vault_items v JOIN users u ON v.user_id = u.id ORDER BY v.id""").fetchall()
    op_idx = 0
    for v in vault:
        first = v["uname"].split("_")[0].title()
        body = f"open the Pass vault and find the {v['category']} entry titled '{v['title']}'."
        emit(vary(op_idx, v["email"], first, body))
        op_idx += 1

    # ============================================================
    # 33) Support tickets per row
    # ============================================================
    tickets = con.execute("""SELECT u.email AS email, u.username AS uname, t.subject AS subject, t.ticket_number AS num, t.priority AS pri
                             FROM support_tickets t JOIN users u ON t.user_id = u.id ORDER BY t.id""").fetchall()
    op_idx = 0
    for t in tickets:
        first = t["uname"].split("_")[0].title()
        emit(vary(op_idx, t["email"], first, f"open the support ticket numbered {t['num']} and report its status."))
        emit(vary(op_idx + 1, t["email"], first, f"find the {t['pri']} priority ticket about '{t['subject'][:40]}'."))
        op_idx += 2

    # ============================================================
    # 34) Orders per row
    # ============================================================
    orders = con.execute("""SELECT u.email AS email, u.username AS uname, o.order_number AS num, o.billing_cycle AS cycle
                            FROM subscription_orders o JOIN users u ON o.user_id = u.id ORDER BY o.id""").fetchall()
    op_idx = 0
    for o in orders:
        first = o["uname"].split("_")[0].title()
        emit(vary(op_idx, o["email"], first, f"open the order {o['num']} from the Account page and report its total."))
        emit(vary(op_idx + 1, o["email"], first, f"open the order {o['num']} and confirm its billing cycle is {o['cycle']}."))
        op_idx += 2

    # ============================================================
    # 35) Per-help-article extra variants
    # ============================================================
    arts = con.execute("SELECT category, title, slug FROM help_articles ORDER BY id").fetchall()
    for a in arts:
        emit(f"In the Help center, search for keywords from '{a['title']}' and open the matching article in the {a['category']} category.")
        emit(f"Within the {a['category']} category of the Help center, open the article titled '{a['title']}' and report its applies-to field.")

    # ============================================================
    # 36) Per-product-page tasks
    # ============================================================
    pages = con.execute("SELECT title, slug, section FROM product_pages ORDER BY id").fetchall()
    for p in pages:
        emit(f"Open the {p['title']} product page (in the {p['section']} section) and report its summary.")
        emit(f"On the {p['title']} product page, find one highlight that fits a small team workflow.")
        emit(f"From the home page, navigate to the {p['title']} product page through the feature grid.")

    # ============================================================
    # 37) Per-download package tasks
    # ============================================================
    downloads = con.execute("SELECT product, platform, package_name, version FROM downloads ORDER BY id").fetchall()
    for d in downloads:
        emit(f"Open Downloads, find the {d['product']} package for {d['platform']} named '{d['package_name']}', and report its version.")
        emit(f"In Downloads, locate the {d['product']} package for {d['platform']} and open its detail page to read its notes.")

    # ============================================================
    # 38) Per-folder per-user secondary tasks
    # ============================================================
    folders2 = con.execute("""SELECT DISTINCT u.email AS email, u.username AS uname, c.folder AS folder
                              FROM cloud_items c JOIN users u ON c.user_id = u.id
                              WHERE c.folder != '/' ORDER BY u.id, c.folder""").fetchall()
    op_idx = 0
    for row in folders2:
        first = row["uname"].split("_")[0].title()
        emit(vary(op_idx, row["email"], first, f"browse the {row['folder']} folder and identify the largest file inside it."))
        emit(vary(op_idx + 1, row["email"], first, f"browse the {row['folder']} folder and count how many files it contains."))
        op_idx += 2

    # ============================================================
    # 39) Pricing combinations
    # ============================================================
    audiences = ["individual", "business"]
    categories2 = ["storage", "vpn", "pass", "business", "objectstorage"]
    for a in audiences:
        for c in categories2:
            for billing in ["monthly", "yearly"]:
                emit(f"Open Pricing with audience {a}, product category {c}, and billing {billing} selected; report how many plans are listed.")

    # ============================================================
    # 40) Cross-feature navigation tasks
    # ============================================================
    nav_pairs = [
        ("File manager", "Sharing hub"),
        ("Sharing hub", "Contacts"),
        ("Contacts", "Chat hub"),
        ("Chat hub", "Transfers"),
        ("Transfers", "Settings hub"),
        ("Settings hub", "Security hub"),
        ("Security hub", "Sync devices"),
        ("Sync devices", "File manager"),
        ("Account", "Settings hub"),
        ("Settings hub", "Encryption settings"),
        ("Pricing", "Business hub"),
        ("Business hub", "Pricing"),
        ("Sync hub", "Downloads"),
        ("Downloads", "Sync hub"),
    ]
    op_idx = 0
    for src, dst in nav_pairs:
        for email, _name, first, _co in USERS:
            body = f"navigate from {src} to {dst} using the in-page links."
            emit(vary(op_idx, email, first, body))
            op_idx += 1

    # ============================================================
    # 41) Search the global search bar
    # ============================================================
    search_terms = [
        "Atlas", "wedding", "vendor", "recovery", "Iceland", "Synology",
        "rclone", "audit", "backup", "ransomware", "compliance",
        "GitHub", "Gmail", "Adobe", "Stripe", "S4", "transfer",
    ]
    op_idx = 0
    for term in search_terms:
        for email, _name, first, _co in USERS:
            body = f"use the global search bar at the top of MEGA to search for '{term}' and report how many sections appear in the results."
            emit(vary(op_idx, email, first, body))
            op_idx += 1

    # ============================================================
    # 42) Bonus: file metadata read-only tasks
    # ============================================================
    op_idx = 0
    for email, (first, items) in user_files.items():
        for it in items[:30]:
            emit(vary(op_idx, email, first, f"open the file '{it['name']}' in {it['folder']} and confirm whether it is currently shared."))
            emit(vary(op_idx + 1, email, first, f"open the file '{it['name']}' in {it['folder']} and report its content summary."))
            op_idx += 2

    # ============================================================
    # Compose final JSONL
    # ============================================================
    for i, q in enumerate(rows):
        sys.stdout.write(json.dumps({
            "web_name": WEB_NAME, "id": f"MEGA--{i}", "ques": q,
            "web": BASE, "upstream_url": UPSTREAM,
        }, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
