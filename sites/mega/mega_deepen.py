"""MEGA mirror deepen pack — file-manager / sharing / contacts / chat / transfers
/ settings / security / sync / business / about.

This module is structured per gotchas.md §31 (APPEND-ONLY blueprint style) and §32
(late-import: never `from app import ...` at module top). Register with
`mega_deepen.register_deepen(app, db)` after the original `seed_database()` runs.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta

from flask import (
    abort, flash, redirect, render_template, request, session, url_for
)
from flask_login import current_user, login_required


# ----- late-bound references resolved at register time -----
_BOUND = {}


def _b(name):
    return _BOUND[name]


# ----- deterministic image picker -----
AVATAR_POOL = [
    "icon-user-blur-strong.png", "Business-img-1.png", "Business-img-2.png",
    "Business-img-3.png", "Business-img-4.png", "Business-img-5.png",
    "Business-img-6.png", "MEGA-Cloud-Access-files-on-the-go.png",
    "MEGA-Mobile-Offline-access-to-your-data.png", "free-today-evolving-with-you.png",
    "Your-privacy-is-our-priority-1.png", "pro-privacy.png", "proprivacy.png",
    "One-account-more-control.png", "Seamless-connectivity.png",
    "icon-magic-wand.png", "img-use-it.png",
]
CHAT_THUMB_POOL = [
    "share-1.png", "share-2.5.png", "share-3.png", "MEGA-icon-message-call.png",
    "MEGA-icon-cloud.png", "MEGA-icon-lock.png", "MEGA-icon-zap.png",
    "transfer-it-hero-1.png", "pass-hero.png", "Backup-2.png", "Backup-3.png",
]
EXT_THUMB = {
    "pdf": "Feature-3.png", "docx": "Accordian-1.png", "doc": "Accordian-1.png",
    "txt": "Accordian-1.png", "md": "img-generous-2.png",
    "xlsx": "Backup-img-4.png", "xls": "Backup-img-4.png", "csv": "Backup-img-4.png",
    "pptx": "Feature-1.png", "key": "Feature-1.png",
    "zip": "objects.png", "rar": "objects.png", "tar": "objects.png", "gz": "objects.png",
    "mp4": "share-1.png", "mov": "share-2.5.png", "wav": "share-3.png",
    "mp3": "share-3.png", "m4a": "share-3.png",
    "png": "img-compatibility.png", "jpg": "img-compatibility.png",
    "jpeg": "img-compatibility.png", "gif": "img-compatibility.png",
    "psd": "img-compatibility.png", "indd": "img-compatibility.png",
    "json": "img-performance.png", "parquet": "img-performance.png",
    "bin": "img-performance.png", "sh": "img-performance.png",
    "lrcat": "Backup-2.png", "folder": "MEGA-icon-cloud.png",
}
INDUSTRY_HERO = {
    "creative-agency": "Business-img-1.png", "healthcare": "Business-img-2.png",
    "legal": "Business-img-3.png", "education": "Business-img-4.png",
    "engineering": "Business-img-5.png", "non-profit": "Business-img-6.png",
    "finance": "Business-img-2.png", "media-production": "Business-img-1.png",
}
PLATFORM_ICON = {
    "Windows": "Windows-1.png", "macOS": "MacOS-1.png",
    "Linux": "DA-img-3.png", "Android": "Android-1.png",
    "iOS": "iOS-1.png", "Web": "transfer-it-hero-1.png",
    "QNAP": "20230215_Mega_icons_upd_00017.png",
    "Synology": "Synology-logo.png", "Chrome": "icon-Chrome.png",
    "Firefox": "firefox_logo_platform.png", "Edge": "icon-Microsoft-Edge.png",
    "Safari": "icon-devices.png",
}
PLAN_ICON_BY_CATEGORY = {
    "storage": "MEGA-icon-cloud.png", "vpn": "Picture-3vpn.png",
    "pass": "password-icon.png", "business": "Business-img-1.png",
    "objectstorage": "True-Nas-Community-edition.png",
}


def pick_avatar(seed_key: str) -> str:
    h = int(hashlib.md5(seed_key.encode()).hexdigest()[:8], 16)
    return AVATAR_POOL[h % len(AVATAR_POOL)]


def pick_chat_thumb(seed_key: str) -> str:
    h = int(hashlib.md5(("chat-" + seed_key).encode()).hexdigest()[:8], 16)
    return CHAT_THUMB_POOL[h % len(CHAT_THUMB_POOL)]


def ext_thumb(name: str, item_type: str = "file") -> str:
    if item_type == "folder":
        return EXT_THUMB["folder"]
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return EXT_THUMB.get(ext, "Feature-1.png")


def slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")


# ----- Reference datetimes — pinned for byte-identical seed (gotchas §3) -----
SEED_REF = datetime(2026, 5, 12, 0, 0, 0)


def register_deepen(app, db):
    """Late-bind app + db, define new models + seed + routes."""

    # Re-import app symbols at call time, never at module top (gotchas §32).
    import app as app_module  # noqa: F401

    # ---------- Models ----------
    class Contact(db.Model):
        __tablename__ = "mega_contacts"
        id = db.Column(db.Integer, primary_key=True)
        owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
        email = db.Column(db.String(140), nullable=False, index=True)
        name = db.Column(db.String(120), nullable=False)
        slug = db.Column(db.String(140), nullable=False, index=True)
        company = db.Column(db.String(120), default="")
        avatar = db.Column(db.String(160), default="")
        status = db.Column(db.String(40), default="offline")
        starred = db.Column(db.Boolean, default=False)
        added_at = db.Column(db.String(20), default="2026-04-01")
        note = db.Column(db.String(240), default="")
        shared_folders_count = db.Column(db.Integer, default=0)

    class ContactRequest(db.Model):
        __tablename__ = "mega_contact_requests"
        id = db.Column(db.Integer, primary_key=True)
        sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
        recipient_email = db.Column(db.String(140), nullable=False, index=True)
        recipient_name = db.Column(db.String(120), default="")
        message = db.Column(db.String(280), default="")
        status = db.Column(db.String(30), default="pending")
        direction = db.Column(db.String(20), default="outgoing")
        created_at = db.Column(db.String(20), default="2026-05-01")

    class ShareLink(db.Model):
        __tablename__ = "mega_share_links"
        id = db.Column(db.Integer, primary_key=True)
        owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
        item_id = db.Column(db.Integer, db.ForeignKey("cloud_items.id"), nullable=False, index=True)
        token = db.Column(db.String(24), unique=True, nullable=False, index=True)
        decryption_key = db.Column(db.String(40), default="")
        has_password = db.Column(db.Boolean, default=False)
        password_pin = db.Column(db.String(40), default="")
        expiry = db.Column(db.String(20), default="")
        downloads = db.Column(db.Integer, default=0)
        revoked = db.Column(db.Boolean, default=False)
        direction = db.Column(db.String(20), default="outgoing")
        created_at = db.Column(db.String(20), default="2026-05-01")
        title = db.Column(db.String(180), default="")

    class ChatThread(db.Model):
        __tablename__ = "mega_chat_threads"
        id = db.Column(db.Integer, primary_key=True)
        owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
        slug = db.Column(db.String(140), nullable=False, index=True)
        name = db.Column(db.String(180), nullable=False)
        kind = db.Column(db.String(30), default="direct")
        avatar = db.Column(db.String(160), default="")
        last_message_at = db.Column(db.String(20), default="")
        unread = db.Column(db.Integer, default=0)
        starred = db.Column(db.Boolean, default=False)
        member_emails = db.Column(db.String(400), default="")

    class ChatMessage(db.Model):
        __tablename__ = "mega_chat_messages"
        id = db.Column(db.Integer, primary_key=True)
        thread_id = db.Column(db.Integer, db.ForeignKey("mega_chat_threads.id"), nullable=False, index=True)
        sender_email = db.Column(db.String(140), nullable=False)
        body = db.Column(db.Text, default="")
        attachment_name = db.Column(db.String(180), default="")
        created_at = db.Column(db.String(20), default="")

    class Transfer(db.Model):
        __tablename__ = "mega_transfers"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
        file_name = db.Column(db.String(220), nullable=False)
        direction = db.Column(db.String(20), default="upload")
        size_mb = db.Column(db.Float, default=0)
        status = db.Column(db.String(30), default="completed")
        device = db.Column(db.String(120), default="")
        completed_at = db.Column(db.String(20), default="")
        speed_mbps = db.Column(db.Float, default=0)

    class SecurityEvent(db.Model):
        __tablename__ = "mega_security_events"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
        kind = db.Column(db.String(60), nullable=False)
        detail = db.Column(db.String(240), default="")
        ip_address = db.Column(db.String(64), default="")
        location = db.Column(db.String(120), default="")
        device = db.Column(db.String(120), default="")
        at = db.Column(db.String(20), default="")

    class SyncDevice(db.Model):
        __tablename__ = "mega_sync_devices"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
        name = db.Column(db.String(160), nullable=False)
        platform = db.Column(db.String(60), default="Windows")
        client_version = db.Column(db.String(40), default="5.12.1")
        sync_root = db.Column(db.String(220), default="")
        last_seen = db.Column(db.String(20), default="")
        status = db.Column(db.String(30), default="connected")
        backup_only = db.Column(db.Boolean, default=False)
        icon = db.Column(db.String(160), default="")

    class FileVersion(db.Model):
        __tablename__ = "mega_file_versions"
        id = db.Column(db.Integer, primary_key=True)
        item_id = db.Column(db.Integer, db.ForeignKey("cloud_items.id"), nullable=False, index=True)
        version_number = db.Column(db.Integer, default=1)
        size_mb = db.Column(db.Float, default=0)
        modified_at = db.Column(db.String(20), default="")
        actor_email = db.Column(db.String(140), default="")
        note = db.Column(db.String(240), default="")
        current = db.Column(db.Boolean, default=False)

    class BusinessIndustry(db.Model):
        __tablename__ = "mega_business_industries"
        id = db.Column(db.Integer, primary_key=True)
        slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
        title = db.Column(db.String(160), nullable=False)
        tagline = db.Column(db.String(280), default="")
        body = db.Column(db.Text, default="")
        hero_image = db.Column(db.String(160), default="")
        customer_logos = db.Column(db.Text, default="[]")
        highlight_features = db.Column(db.Text, default="[]")
        case_study = db.Column(db.Text, default="")
        recommended_plan_slug = db.Column(db.String(60), default="business-pro")

    class NotificationPref(db.Model):
        __tablename__ = "mega_notification_prefs"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
        kind = db.Column(db.String(80), nullable=False)
        enabled = db.Column(db.Boolean, default=True)
        channel = db.Column(db.String(20), default="email")

    class TransferSetting(db.Model):
        __tablename__ = "mega_transfer_settings"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
        upload_limit_mbps = db.Column(db.Integer, default=0)
        download_limit_mbps = db.Column(db.Integer, default=0)
        max_parallel = db.Column(db.Integer, default=6)
        priority_uploads = db.Column(db.Boolean, default=False)
        pause_on_metered = db.Column(db.Boolean, default=True)

    class SecuritySetting(db.Model):
        __tablename__ = "mega_security_settings"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
        master_key_backed_up_at = db.Column(db.String(20), default="")
        last_2fa_change = db.Column(db.String(20), default="")
        recovery_methods = db.Column(db.String(120), default="recovery-key")
        session_timeout_minutes = db.Column(db.Integer, default=120)
        require_2fa_for_sharing = db.Column(db.Boolean, default=False)

    _BOUND.update(dict(
        Contact=Contact, ContactRequest=ContactRequest, ShareLink=ShareLink,
        ChatThread=ChatThread, ChatMessage=ChatMessage, Transfer=Transfer,
        SecurityEvent=SecurityEvent, SyncDevice=SyncDevice, FileVersion=FileVersion,
        BusinessIndustry=BusinessIndustry, NotificationPref=NotificationPref,
        TransferSetting=TransferSetting, SecuritySetting=SecuritySetting,
        db=db, app=app,
    ))

    db.create_all()

    # ---------- Seed (idempotent — checks for existing rows) ----------
    if BusinessIndustry.query.count() == 0:
        _seed_industries(db, BusinessIndustry)
    User = app_module.User
    if Contact.query.count() == 0:
        _seed_per_user_extras(
            db, User, Contact, ContactRequest, ShareLink, ChatThread, ChatMessage,
            Transfer, SecurityEvent, SyncDevice, FileVersion,
            NotificationPref, TransferSetting, SecuritySetting,
            app_module.CloudItem,
        )

    # ---------- Routes ----------
    _register_routes(
        app, db, app_module.CloudItem, app_module.User, app_module.Plan,
        Contact, ContactRequest, ShareLink, ChatThread, ChatMessage, Transfer,
        SecurityEvent, SyncDevice, FileVersion, BusinessIndustry,
        NotificationPref, TransferSetting, SecuritySetting,
    )


# ============================================================================
# Seeding helpers (deterministic, byte-identical across rebuilds)
# ============================================================================

INDUSTRIES = [
    ("creative-agency", "Creative agencies", "Encrypted delivery rooms, secure client previews, and ransomware-safe archives for studios.",
     ["Riverlight Studio", "Atlas Brand Lab", "Northern Lights Co."],
     ["Branded delivery rooms", "Encrypted preview links", "Project archive retention", "Backup-grade redundancy"],
     "Riverlight Studio cut review time in half by replacing scattered Dropbox links with MEGA share rooms.",
     "business-pro"),
    ("healthcare", "Healthcare", "Zero-knowledge storage for patient documents, imaging, and HIPAA-grade workflow audits.",
     ["Cedar Health Network", "Aurora Imaging", "Greenpine Clinic Group"],
     ["BAA-ready storage", "Audit-grade access logs", "Encrypted patient transfers", "Per-device revocation"],
     "Cedar Health Network ships imaging studies to specialists with one-time, decryption-key-gated links.",
     "business-enterprise"),
    ("legal", "Legal firms", "Encrypted matter rooms, signed-document retention, and external-counsel collaboration.",
     ["Cedar Legal Group", "BlueRiver Counsel", "Northstar Litigation"],
     ["Matter-level access control", "Signature-ready retention", "Auditor exports", "Per-collaborator revocation"],
     "Cedar Legal moved external-counsel sharing into MEGA folders with expiry-enforced links.",
     "business-pro"),
    ("education", "Education and research", "Encrypted course archives, large-dataset sharing, and student submission flows.",
     ["Lakeside University", "Polar Coding Academy", "Cascade STEM Foundation"],
     ["Course archive retention", "Large dataset transfer", "External collaborator controls", "Student submission folders"],
     "Lakeside University swapped FTP submissions for MEGA upload folders that link directly to grading rooms.",
     "business-pro"),
    ("engineering", "Engineering and software", "Source archives, design files, and CI artifact backups with encrypted transfer.",
     ["Northstar Analytics", "Highline Robotics", "Carbon Forge Engineering"],
     ["CI artifact storage", "Design file versioning", "On-call file sharing", "S4 object storage compatibility"],
     "Northstar Analytics archives nightly snapshots to MEGA S4 with Rclone and rotates quarterly.",
     "pro-flexi"),
    ("non-profit", "Non-profits", "Affordable encrypted collaboration for distributed boards, volunteer teams, and donors.",
     ["Greenline Foundation", "Habitat for Open Source", "Quiet Forest Trust"],
     ["Discounted Business plans", "Volunteer access controls", "Donor disclosure tools", "Board recording archive"],
     "Greenline Foundation runs distributed board meetings with MEGA recordings and shared decks.",
     "business-starter"),
    ("finance", "Finance and accounting", "Audit-grade retention, secure exports, and external-auditor collaboration rooms.",
     ["Northwind CPA", "Riverlight Finance", "Carbon Forge Treasury"],
     ["Audit-grade retention", "Encrypted export bundles", "Audit collaborator rooms", "Compliance summary export"],
     "Northwind CPA shares year-end audit packages through encrypted folders with auto-revoking links.",
     "business-pro"),
    ("media-production", "Media production", "Encrypted ingest, large media archives, and external-edit collaboration.",
     ["Riverlight Studio", "Open Lens Productions", "Skyline Postworks"],
     ["Large media ingest", "Per-project edit rooms", "Color grade review links", "S4 archive lifecycle"],
     "Riverlight Studio's Atlas launch reel hit air after delivery through a MEGA encrypted edit room.",
     "business-enterprise"),
]


def _seed_industries(db, BusinessIndustry):
    for slug, title, tagline, logos, features, case, plan in INDUSTRIES:
        body = (
            f"{title} on MEGA combine zero-knowledge encryption with workflow tools their teams already use. "
            f"Mirror pages keep the same content framing as mega.io while running locally with deterministic data."
        )
        db.session.add(BusinessIndustry(
            slug=slug, title=title, tagline=tagline, body=body,
            hero_image=INDUSTRY_HERO.get(slug, "Business-img-1.png"),
            customer_logos=json.dumps(logos, sort_keys=True),
            highlight_features=json.dumps(features, sort_keys=True),
            case_study=case, recommended_plan_slug=plan,
        ))
    db.session.commit()


# Deterministic generator for per-user records.
CONTACT_DIRECTORY = [
    # (email, name, company, status, starred_with, note)
    ("mira.lin@northstar.example", "Mira Lin", "Northstar Analytics", "online", True, "Atlas analytics liaison."),
    ("toby.green@cedarlegal.example", "Toby Green", "Cedar Legal Group", "offline", True, "Vendor contract review owner."),
    ("hank.ito@riverlight.example", "Hank Ito", "Riverlight Studio", "away", False, "Sound design freelancer."),
    ("lena.park@cedarlegal.example", "Lena Park", "Cedar Legal Group", "online", False, "Compliance lead."),
    ("ravi.shah@northstar.example", "Ravi Shah", "Northstar Analytics", "offline", False, "Data eng partner."),
    ("ola.svensson@riverlight.example", "Ola Svensson", "Riverlight Studio", "online", True, "Studio producer."),
    ("kim.tang@davidkimphoto.example", "Kim Tang", "David Kim Photo", "online", False, "Second shooter."),
    ("priya.nair@northstar.example", "Priya Nair", "Northstar Analytics", "online", False, "ML engineer."),
    ("evan.brooks@cedarlegal.example", "Evan Brooks", "Cedar Legal Group", "offline", False, "Operations analyst."),
    ("zoe.may@riverlight.example", "Zoe May", "Riverlight Studio", "away", True, "Color grading lead."),
    ("noah.alvarez@northstar.example", "Noah Alvarez", "Northstar Analytics", "online", False, "DevOps on-call."),
    ("amelia.ren@cedarlegal.example", "Amelia Ren", "Cedar Legal Group", "offline", True, "External counsel."),
    ("sam.holm@riverlight.example", "Sam Holm", "Riverlight Studio", "online", False, "Motion designer."),
    ("ines.dubois@cedarlegal.example", "Ines Dubois", "Cedar Legal Group", "online", False, "Privacy reviewer."),
    ("jay.okafor@northstar.example", "Jay Okafor", "Northstar Analytics", "away", False, "Data quality lead."),
    ("rae.donato@riverlight.example", "Rae Donato", "Riverlight Studio", "offline", False, "Production coordinator."),
    ("oren.koval@northstar.example", "Oren Koval", "Northstar Analytics", "offline", True, "Forecasting researcher."),
    ("kira.akiyama@davidkimphoto.example", "Kira Akiyama", "David Kim Photo", "online", True, "Studio retoucher."),
    ("milo.wenders@cedarlegal.example", "Milo Wenders", "Cedar Legal Group", "online", False, "Lit support."),
    ("eva.shore@riverlight.example", "Eva Shore", "Riverlight Studio", "offline", False, "Account director."),
]

INCOMING_REQUESTS = [
    ("ana.howard@partners.example", "Ana Howard", "Wants to share Atlas Q3 review folder.", "pending"),
    ("max.lutz@partners.example", "Max Lutz", "Audit collaboration request for FY26 documents.", "pending"),
    ("ina.peers@external.example", "Ina Peers", "Requesting access to wedding gallery for review.", "accepted"),
    ("dion.albert@external.example", "Dion Albert", "Vendor onboarding contact request.", "pending"),
]
OUTGOING_REQUESTS = [
    ("paula.norris@partners.example", "Paula Norris", "Following up on contract review pipeline."),
    ("hans.becker@partners.example", "Hans Becker", "Connecting on Q3 audit transfer."),
    ("emma.lin@external.example", "Emma Lin", "Inviting you to collaborate on Atlas press kit."),
]


def _seed_per_user_extras(db, User, Contact, ContactRequest, ShareLink, ChatThread,
                          ChatMessage, Transfer, SecurityEvent, SyncDevice,
                          FileVersion, NotificationPref, TransferSetting,
                          SecuritySetting, CloudItem):
    users = User.query.filter(User.email.in_([
        "alice.j@test.com", "bob.c@test.com", "carol.d@test.com", "david.k@test.com",
    ])).all()
    if not users:
        return
    by_email = {u.email: u for u in users}

    NOTIF_KINDS = [
        ("Sign-in alerts", True), ("Share-link downloads", True),
        ("Storage warnings", True), ("Transfer completion", False),
        ("Backup status changes", True), ("Contact requests", True),
        ("Chat mentions", True), ("Subscription renewals", True),
        ("Security advisories", True), ("Product news", False),
    ]
    # ---- Per-user blocks ----
    contacts_per_user = {
        "alice.j@test.com": [
            ("bob.c@test.com", "Bob Chen", "Northstar Analytics", "online", True, "Atlas analytics partner.", "2026-03-12"),
            ("carol.d@test.com", "Carol Davis", "Cedar Legal Group", "online", True, "Vendor contract review.", "2026-02-04"),
            ("david.k@test.com", "David Kim", "David Kim Photo", "away", False, "Wedding deliveries.", "2026-04-18"),
        ] + [(d[0], d[1], d[2], d[3], d[4], d[5], "2026-04-22") for d in CONTACT_DIRECTORY[:9]],
        "bob.c@test.com": [
            ("alice.j@test.com", "Alice Johnson", "Riverlight Studio", "online", True, "Studio collaborator.", "2026-03-12"),
            ("carol.d@test.com", "Carol Davis", "Cedar Legal Group", "online", True, "Compliance liaison.", "2026-02-19"),
        ] + [(d[0], d[1], d[2], d[3], d[4], d[5], "2026-04-12") for d in CONTACT_DIRECTORY[3:11]],
        "carol.d@test.com": [
            ("alice.j@test.com", "Alice Johnson", "Riverlight Studio", "online", True, "Studio MSA owner.", "2026-02-04"),
            ("bob.c@test.com", "Bob Chen", "Northstar Analytics", "online", True, "Compliance partner.", "2026-02-19"),
        ] + [(d[0], d[1], d[2], d[3], d[4], d[5], "2026-04-30") for d in CONTACT_DIRECTORY[5:14]],
        "david.k@test.com": [
            ("alice.j@test.com", "Alice Johnson", "Riverlight Studio", "online", True, "Portfolio partner.", "2026-04-18"),
        ] + [(d[0], d[1], d[2], d[3], d[4], d[5], "2026-05-02") for d in CONTACT_DIRECTORY[6:14]],
    }
    for u in users:
        for email, name, company, status, starred, note, added in contacts_per_user[u.email]:
            db.session.add(Contact(
                owner_id=u.id, email=email, name=name, slug=slugify(email),
                company=company, avatar=pick_avatar(email),
                status=status, starred=starred, added_at=added,
                note=note, shared_folders_count=(2 if starred else 0),
            ))

    # Contact requests
    for u in users:
        for i, (email, name, msg, status) in enumerate(INCOMING_REQUESTS):
            db.session.add(ContactRequest(
                sender_id=u.id, recipient_email=email, recipient_name=name,
                message=msg, status=status, direction="incoming",
                created_at=f"2026-05-0{(i % 9) + 1}",
            ))
        for i, (email, name, msg) in enumerate(OUTGOING_REQUESTS):
            db.session.add(ContactRequest(
                sender_id=u.id, recipient_email=email, recipient_name=name,
                message=msg, status="pending", direction="outgoing",
                created_at=f"2026-05-1{(i % 9)}",
            ))

    # Share links — derived from existing CloudItems for each user
    for u in users:
        items = CloudItem.query.filter_by(user_id=u.id).filter(CloudItem.item_type == "file").order_by(CloudItem.id).limit(12).all()
        for i, item in enumerate(items):
            token = hashlib.md5(f"{u.id}-{item.slug}".encode()).hexdigest()[:14].upper()
            db.session.add(ShareLink(
                owner_id=u.id, item_id=item.id, token=token,
                decryption_key=hashlib.md5(token.encode()).hexdigest()[:22],
                has_password=(i % 3 == 0),
                password_pin=("MEGA-" + token[:6]) if (i % 3 == 0) else "",
                expiry=("2026-06-30" if (i % 2) else ""),
                downloads=(i * 3 + 1),
                revoked=(i == 11),
                direction="outgoing",
                created_at=f"2026-05-{((i % 12) + 1):02d}",
                title=item.name,
            ))
        # Incoming shared links from other users' files
        for j, item in enumerate(items[:5]):
            token = hashlib.md5(f"in-{u.id}-{item.slug}".encode()).hexdigest()[:14].upper()
            db.session.add(ShareLink(
                owner_id=u.id, item_id=item.id, token=token,
                decryption_key=hashlib.md5(("in" + token).encode()).hexdigest()[:22],
                expiry="2026-07-15", downloads=j + 2, direction="incoming",
                created_at=f"2026-04-{((j % 28) + 1):02d}",
                title="Shared with you: " + item.name,
            ))

    # Chat threads + messages
    THREAD_SPECS = {
        "alice.j@test.com": [
            ("Atlas creative room", "group", ["bob.c@test.com", "carol.d@test.com", "ola.svensson@riverlight.example"], 3, True),
            ("Bob Chen", "direct", ["bob.c@test.com"], 1, True),
            ("Carol Davis", "direct", ["carol.d@test.com"], 0, False),
            ("Studio team", "group", ["ola.svensson@riverlight.example", "zoe.may@riverlight.example", "sam.holm@riverlight.example"], 2, False),
            ("Yearbook pipeline", "group", ["rae.donato@riverlight.example", "hank.ito@riverlight.example"], 0, False),
            ("David Kim", "direct", ["david.k@test.com"], 1, False),
        ],
        "bob.c@test.com": [
            ("Northstar on-call", "group", ["noah.alvarez@northstar.example", "ravi.shah@northstar.example", "priya.nair@northstar.example"], 2, True),
            ("Carol Davis", "direct", ["carol.d@test.com"], 0, False),
            ("Alice Johnson", "direct", ["alice.j@test.com"], 1, True),
            ("S4 migration", "group", ["carol.d@test.com", "ravi.shah@northstar.example"], 1, False),
            ("Forecast research", "group", ["priya.nair@northstar.example", "oren.koval@northstar.example"], 0, False),
        ],
        "carol.d@test.com": [
            ("Compliance circle", "group", ["lena.park@cedarlegal.example", "amelia.ren@cedarlegal.example"], 1, True),
            ("Alice Johnson", "direct", ["alice.j@test.com"], 0, True),
            ("Bob Chen", "direct", ["bob.c@test.com"], 1, False),
            ("Vendor reviews", "group", ["toby.green@cedarlegal.example", "evan.brooks@cedarlegal.example"], 2, False),
            ("FY26 audit", "group", ["amelia.ren@cedarlegal.example", "milo.wenders@cedarlegal.example"], 0, False),
        ],
        "david.k@test.com": [
            ("Wedding clients", "group", ["alice.j@test.com", "kira.akiyama@davidkimphoto.example"], 0, True),
            ("Alice Johnson", "direct", ["alice.j@test.com"], 1, False),
            ("Second shooter", "direct", ["kim.tang@davidkimphoto.example"], 0, False),
            ("Portfolio review", "group", ["alice.j@test.com", "kira.akiyama@davidkimphoto.example"], 1, False),
        ],
    }
    SAMPLE_BODIES = [
        "Quick check — the encrypted folder is in place.",
        "Uploaded the new selects to the shared room.",
        "Heads up: I revoked the old share link.",
        "Need a fresh decryption key for the audit drop.",
        "Can you confirm two-factor is still required for that folder?",
        "Backup ran clean overnight on Synology.",
        "Color grade preview is ready for review.",
        "S4 cost model updated for Q3 forecast.",
        "Re-signed the vendor contract; check the matter room.",
        "Master key backup confirmed for new device.",
    ]
    for u in users:
        for ti, (name, kind, members, unread, starred) in enumerate(THREAD_SPECS[u.email]):
            slug = slugify(f"{u.username}-{name}")
            thread = ChatThread(
                owner_id=u.id, slug=slug, name=name, kind=kind,
                avatar=pick_chat_thumb(name + u.email),
                last_message_at=f"2026-05-{((10 + ti) % 28) + 1:02d}",
                unread=unread, starred=starred,
                member_emails=",".join(members),
            )
            db.session.add(thread)
            db.session.flush()
            # 5 messages per thread (deterministic)
            for mi in range(5):
                idx = (ti * 7 + mi * 3) % len(SAMPLE_BODIES)
                sender = u.email if mi % 2 == 0 else (members[0] if members else u.email)
                db.session.add(ChatMessage(
                    thread_id=thread.id, sender_email=sender,
                    body=SAMPLE_BODIES[idx],
                    attachment_name=("Atlas-summary.pdf" if mi == 2 else ""),
                    created_at=f"2026-05-{((mi + ti) % 28) + 1:02d}",
                ))

    # Transfers — per user from CloudItems
    for u in users:
        items = CloudItem.query.filter_by(user_id=u.id).filter(CloudItem.item_type == "file").order_by(CloudItem.id).limit(15).all()
        for i, item in enumerate(items):
            direction = "upload" if i % 2 == 0 else "download"
            status = "completed" if i % 5 else ("paused" if i % 7 == 0 else "queued")
            db.session.add(Transfer(
                user_id=u.id, file_name=item.name, direction=direction,
                size_mb=item.size_mb, status=status,
                device=("MacBook Pro" if i % 3 == 0 else ("Synology DS923+" if i % 3 == 1 else "iPhone 15 Pro")),
                completed_at=f"2026-05-{((i % 28) + 1):02d}",
                speed_mbps=round(8.0 + (i * 1.7) % 40, 1),
            ))

    # Security events
    EVENT_KINDS = [
        ("Sign-in", "Web client sign-in"), ("Sign-in", "Desktop app sign-in"),
        ("Recovery key downloaded", "User downloaded recovery key"),
        ("2FA toggled", "Two-factor enabled"),
        ("Master key backup", "Backup completed"),
        ("Share link revoked", "Link auto-expired"),
        ("Password changed", "User updated account password"),
        ("Device added", "New device session"),
        ("Suspicious sign-in", "Unfamiliar IP — verification required"),
        ("Session revoked", "User ended remote session"),
    ]
    LOCS = ["Indianapolis, IN", "Chicago, IL", "Auckland, NZ", "Toronto, ON", "Berlin, DE"]
    DEVS = ["MacBook Pro", "iPhone 15 Pro", "Windows 11 desktop", "Linux workstation", "Synology DS923+"]
    for u in users:
        for i, (kind, detail) in enumerate(EVENT_KINDS):
            db.session.add(SecurityEvent(
                user_id=u.id, kind=kind, detail=detail,
                ip_address=f"203.0.113.{(i * 13 + u.id) % 250}",
                location=LOCS[(i + u.id) % len(LOCS)],
                device=DEVS[(i + u.id) % len(DEVS)],
                at=f"2026-05-{((i + 1) % 28) + 1:02d}",
            ))

    # Sync devices
    SYNC_PROFILES = {
        "alice.j@test.com": [
            ("MacBook Pro studio", "macOS", "5.12.1", "/Users/alice/MEGA", "connected", False),
            ("iPhone 15 Pro", "iOS", "14.8", "Camera Uploads", "connected", False),
            ("Studio NAS", "Synology", "1.7.2", "/volume1/MEGA", "connected", True),
            ("Backup laptop", "Windows", "5.12.1", "C:/Users/alice/MEGA", "paused", True),
        ],
        "bob.c@test.com": [
            ("Linux workstation", "Linux", "5.12.1", "/home/bob/MEGA", "connected", False),
            ("Synology DS923+", "Synology", "1.7.2", "/volume1/MEGA", "connected", True),
            ("Pixel 8 Pro", "Android", "14.8", "Camera Uploads", "connected", False),
        ],
        "carol.d@test.com": [
            ("Conference Room Mac", "macOS", "5.12.1", "/Users/Shared/MEGA", "connected", False),
            ("Cedar Legal laptop", "Windows", "5.12.1", "C:/Users/carol/MEGA", "connected", False),
            ("Cedar Legal NAS", "Synology", "1.7.2", "/volume1/legal-archive", "connected", True),
            ("iPad Pro", "iOS", "14.8", "Documents", "connected", False),
        ],
        "david.k@test.com": [
            ("Mac Studio", "macOS", "5.12.1", "/Users/david/MEGA", "connected", False),
            ("MacBook Air travel", "macOS", "5.12.1", "/Users/david/MEGA-Air", "paused", False),
            ("iPhone 15 Pro", "iOS", "14.8", "Camera Uploads", "connected", False),
            ("QNAP archive", "QNAP", "1.7.2", "/share/MEGA", "connected", True),
        ],
    }
    for u in users:
        for name, plat, ver, root, status, backup in SYNC_PROFILES[u.email]:
            db.session.add(SyncDevice(
                user_id=u.id, name=name, platform=plat, client_version=ver,
                sync_root=root, last_seen=f"2026-05-{(u.id * 3 + len(name)) % 28 + 1:02d}",
                status=status, backup_only=backup,
                icon=PLATFORM_ICON.get(plat, "DA-img-2.png"),
            ))

    # File versions — 4 versions for each user's first 6 items
    for u in users:
        items = CloudItem.query.filter_by(user_id=u.id).filter(CloudItem.item_type == "file").order_by(CloudItem.id).limit(6).all()
        for item in items:
            for v in range(4, 0, -1):
                db.session.add(FileVersion(
                    item_id=item.id, version_number=v,
                    size_mb=max(0.1, round(item.size_mb * (0.7 + 0.1 * v), 2)),
                    modified_at=f"2026-{((v % 4) + 1):02d}-{((v * 7) % 28) + 1:02d}",
                    actor_email=u.email,
                    note=("Restored from backup" if v == 2 else ("Saved from desktop sync" if v == 3 else "Edited in web client")),
                    current=(v == 4),
                ))

    # Notification prefs + transfer/security settings
    for u in users:
        for kind, default in NOTIF_KINDS:
            db.session.add(NotificationPref(
                user_id=u.id, kind=kind, enabled=default,
                channel="email" if kind != "Chat mentions" else "push",
            ))
        db.session.add(TransferSetting(
            user_id=u.id, upload_limit_mbps=0, download_limit_mbps=0,
            max_parallel=6, priority_uploads=False, pause_on_metered=True,
        ))
        db.session.add(SecuritySetting(
            user_id=u.id, master_key_backed_up_at=("2026-01-15" if u.email == "alice.j@test.com" else ""),
            last_2fa_change="2026-02-10", recovery_methods="recovery-key,authenticator",
            session_timeout_minutes=120, require_2fa_for_sharing=(u.email in {"carol.d@test.com", "alice.j@test.com"}),
        ))

    db.session.commit()


# ============================================================================
# Routes — split into a separate function for readability
# ============================================================================

def _register_routes(app, db, CloudItem, User, Plan, Contact, ContactRequest,
                     ShareLink, ChatThread, ChatMessage, Transfer, SecurityEvent,
                     SyncDevice, FileVersion, BusinessIndustry, NotificationPref,
                     TransferSetting, SecuritySetting):

    # ------ helpers ------
    def _get_item_or_404(slug):
        return CloudItem.query.filter_by(user_id=current_user.id, slug=slug).first_or_404()

    def _link_owned(token):
        return ShareLink.query.filter_by(token=token).first_or_404()

    @app.context_processor
    def inject_deepen_globals():
        ctx = {"deepen_industries": BusinessIndustry.query.order_by(BusinessIndustry.id).limit(8).all()}
        if current_user.is_authenticated:
            ctx["unread_chats"] = (ChatThread.query.filter_by(owner_id=current_user.id)
                                   .filter(ChatThread.unread > 0).count())
            ctx["pending_contact_requests"] = ContactRequest.query.filter_by(
                sender_id=current_user.id, direction="incoming", status="pending"
            ).count()
        return ctx

    # ---------------- File manager hub & folder detail ----------------

    @app.route("/file-manager")
    @login_required
    def file_manager():
        q = request.args.get("q", "")
        folder = request.args.get("folder", "")
        items = CloudItem.query.filter_by(user_id=current_user.id).all()
        if folder:
            items = [i for i in items if i.folder == folder]
        if q:
            tokens = [t for t in re.split(r"\W+", q.lower()) if len(t) > 1]
            items = [i for i in items if any(t in (i.name + " " + i.folder + " " + (i.content_summary or "")).lower() for t in tokens)]
        items = sorted(items, key=lambda i: (i.folder, i.item_type != "folder", i.name.lower()))
        folders = sorted({i.folder for i in CloudItem.query.filter_by(user_id=current_user.id).all()})
        recent = (CloudItem.query.filter_by(user_id=current_user.id)
                  .filter(CloudItem.item_type == "file")
                  .order_by(CloudItem.modified_at.desc()).limit(6).all())
        return render_template(
            "file_manager.html", items=items, folders=folders, q=q, folder=folder,
            recent=recent, ext_thumb=ext_thumb,
        )

    @app.route("/file-manager/folder/<path:folder_slug>")
    @login_required
    def folder_detail(folder_slug):
        folder = "/" + folder_slug.strip("/")
        items = CloudItem.query.filter_by(user_id=current_user.id, folder=folder).all()
        items = sorted(items, key=lambda i: (i.item_type != "folder", i.name.lower()))
        if not items:
            abort(404)
        bytes_total = sum((i.size_mb or 0) for i in items)
        return render_template("folder_detail.html", folder=folder, items=items,
                               bytes_total=bytes_total, ext_thumb=ext_thumb)

    @app.route("/file-manager/file/<slug>")
    @login_required
    def file_manager_file(slug):
        return redirect(url_for("file_detail", slug=slug), code=301)

    # ---------------- File operations (POST) ----------------

    @app.route("/file/<slug>/rename", methods=["GET", "POST"])
    @login_required
    def file_rename(slug):
        item = _get_item_or_404(slug)
        if request.method == "POST":
            new_name = request.form.get("name", "").strip()
            if not new_name:
                flash("New file name is required.", "error")
            else:
                item.name = new_name
                item.modified_at = "2026-05-12"
                db.session.commit()
                flash(f"Renamed to {new_name}.", "success")
                return redirect(url_for("file_detail", slug=item.slug))
        return render_template("file_rename.html", item=item)

    @app.route("/file/<slug>/move", methods=["GET", "POST"])
    @login_required
    def file_move(slug):
        item = _get_item_or_404(slug)
        folders = sorted({i.folder for i in CloudItem.query.filter_by(user_id=current_user.id).all()})
        if request.method == "POST":
            dest = request.form.get("folder", "").strip()
            if not dest:
                flash("Choose a destination folder.", "error")
            else:
                item.folder = dest
                item.modified_at = "2026-05-12"
                db.session.commit()
                flash(f"Moved {item.name} to {dest}.", "success")
                return redirect(url_for("file_detail", slug=item.slug))
        return render_template("file_move.html", item=item, folders=folders)

    @app.route("/file/<slug>/copy", methods=["GET", "POST"])
    @login_required
    def file_copy(slug):
        item = _get_item_or_404(slug)
        folders = sorted({i.folder for i in CloudItem.query.filter_by(user_id=current_user.id).all()})
        if request.method == "POST":
            dest = request.form.get("folder", "").strip()
            new_name = request.form.get("new_name", "").strip() or ("Copy of " + item.name)
            if not dest:
                flash("Pick a destination folder.", "error")
            else:
                copy = CloudItem(
                    user_id=current_user.id, name=new_name,
                    slug=slugify(f"{dest}-{new_name}-{current_user.id}-copy-{item.id}"),
                    item_type=item.item_type, folder=dest, extension=item.extension,
                    size_mb=item.size_mb, modified_at="2026-05-12",
                    sync_status="Synced", content_summary=("Copy of " + (item.content_summary or "")),
                )
                db.session.add(copy)
                db.session.commit()
                flash(f"Copied {item.name} to {dest}.", "success")
                return redirect(url_for("file_detail", slug=copy.slug))
        return render_template("file_copy.html", item=item, folders=folders)

    @app.route("/file/<slug>/delete", methods=["GET", "POST"])
    @login_required
    def file_delete(slug):
        item = _get_item_or_404(slug)
        if request.method == "POST":
            db.session.delete(item)
            db.session.commit()
            flash(f"Deleted {item.name}.", "success")
            return redirect(url_for("file_manager"))
        return render_template("file_delete.html", item=item)

    @app.route("/file/<slug>/version-history")
    @login_required
    def file_version_history(slug):
        item = _get_item_or_404(slug)
        versions = (FileVersion.query.filter_by(item_id=item.id)
                    .order_by(FileVersion.version_number.desc()).all())
        return render_template("file_version_history.html", item=item, versions=versions)

    @app.route("/file/<slug>/version/<int:version_id>/restore", methods=["POST"])
    @login_required
    def file_version_restore(slug, version_id):
        item = _get_item_or_404(slug)
        version = FileVersion.query.filter_by(id=version_id, item_id=item.id).first_or_404()
        FileVersion.query.filter_by(item_id=item.id).update({"current": False})
        version.current = True
        item.size_mb = version.size_mb
        item.modified_at = "2026-05-12"
        db.session.commit()
        flash(f"Restored version {version.version_number} of {item.name}.", "success")
        return redirect(url_for("file_version_history", slug=item.slug))

    # ---------------- Sharing hub ----------------

    @app.route("/sharing")
    @login_required
    def sharing_hub():
        outgoing = ShareLink.query.filter_by(owner_id=current_user.id, direction="outgoing").order_by(ShareLink.id.desc()).all()
        incoming = ShareLink.query.filter_by(owner_id=current_user.id, direction="incoming").order_by(ShareLink.id.desc()).all()
        return render_template("sharing_hub.html", outgoing=outgoing, incoming=incoming)

    @app.route("/sharing/outgoing")
    @login_required
    def sharing_outgoing():
        links = ShareLink.query.filter_by(owner_id=current_user.id, direction="outgoing").order_by(ShareLink.id.desc()).all()
        return render_template("sharing_outgoing.html", links=links)

    @app.route("/sharing/incoming")
    @login_required
    def sharing_incoming():
        links = ShareLink.query.filter_by(owner_id=current_user.id, direction="incoming").order_by(ShareLink.id.desc()).all()
        return render_template("sharing_incoming.html", links=links)

    @app.route("/sharing/link/<token>")
    def share_link_public(token):
        link = _link_owned(token)
        item = CloudItem.query.get(link.item_id)
        unlocked = session.get(f"link_unlocked_{token}") or (not link.has_password and not link.decryption_key)
        return render_template("sharing_link_public.html", link=link, item=item, unlocked=unlocked)

    @app.route("/sharing/link/<token>/decrypt", methods=["GET", "POST"])
    def share_link_decrypt(token):
        link = _link_owned(token)
        if request.method == "POST":
            key = request.form.get("decryption_key", "").strip()
            pin = request.form.get("password", "").strip()
            key_ok = (not link.decryption_key) or (key and key == link.decryption_key)
            pin_ok = (not link.has_password) or (pin and pin == link.password_pin)
            if key_ok and pin_ok and not link.revoked:
                session[f"link_unlocked_{token}"] = True
                link.downloads = (link.downloads or 0) + 1
                db.session.commit()
                flash("Link unlocked.", "success")
                return redirect(url_for("share_link_public", token=token))
            flash("Decryption key or password did not match.", "error")
        return render_template("sharing_link_decrypt.html", link=link)

    @app.route("/sharing/link/create", methods=["GET", "POST"])
    @login_required
    def share_link_create():
        slug = request.args.get("item") or request.form.get("item_slug")
        item = None
        if slug:
            item = CloudItem.query.filter_by(user_id=current_user.id, slug=slug).first()
        items = CloudItem.query.filter_by(user_id=current_user.id).filter(CloudItem.item_type == "file").order_by(CloudItem.name).all()
        if request.method == "POST":
            if not item:
                flash("Pick an item to share.", "error")
            else:
                token = hashlib.md5(f"create-{current_user.id}-{item.slug}-{datetime.utcnow().timestamp()}".encode()).hexdigest()[:14].upper()
                link = ShareLink(
                    owner_id=current_user.id, item_id=item.id, token=token,
                    decryption_key=hashlib.md5(token.encode()).hexdigest()[:22],
                    has_password=bool(request.form.get("has_password")),
                    password_pin=(request.form.get("password_pin", "")[:40] if request.form.get("has_password") else ""),
                    expiry=request.form.get("expiry", "")[:20],
                    direction="outgoing", created_at="2026-05-12", title=item.name,
                )
                db.session.add(link)
                db.session.commit()
                flash("Share link created.", "success")
                return redirect(url_for("share_link_public", token=token))
        return render_template("sharing_link_create.html", item=item, items=items)

    @app.route("/sharing/link/<token>/revoke", methods=["POST"])
    @login_required
    def share_link_revoke(token):
        link = ShareLink.query.filter_by(token=token, owner_id=current_user.id).first_or_404()
        link.revoked = True
        db.session.commit()
        flash("Share link revoked.", "success")
        return redirect(url_for("sharing_outgoing"))

    @app.route("/sharing/folder/<int:item_id>")
    @login_required
    def shared_folder_detail(item_id):
        item = CloudItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
        if item.item_type != "folder":
            abort(404)
        children = CloudItem.query.filter_by(user_id=current_user.id, folder="/" + item.name).all()
        link = ShareLink.query.filter_by(item_id=item.id, owner_id=current_user.id).first()
        return render_template("shared_folder_detail.html", item=item, children=children, link=link)

    # ---------------- Contacts ----------------

    @app.route("/contacts")
    @login_required
    def contacts_list():
        q = request.args.get("q", "").strip().lower()
        contacts = Contact.query.filter_by(owner_id=current_user.id).order_by(Contact.starred.desc(), Contact.name).all()
        if q:
            contacts = [c for c in contacts if q in (c.name + c.email + c.company).lower()]
        incoming = ContactRequest.query.filter_by(sender_id=current_user.id, direction="incoming").order_by(ContactRequest.id.desc()).all()
        outgoing = ContactRequest.query.filter_by(sender_id=current_user.id, direction="outgoing").order_by(ContactRequest.id.desc()).all()
        return render_template("contacts.html", contacts=contacts, q=q,
                               incoming=incoming, outgoing=outgoing)

    @app.route("/contact/<email_slug>")
    @login_required
    def contact_detail(email_slug):
        c = Contact.query.filter_by(owner_id=current_user.id, slug=email_slug).first_or_404()
        shared_links = ShareLink.query.filter_by(owner_id=current_user.id, direction="outgoing").order_by(ShareLink.id.desc()).limit(6).all()
        return render_template("contact_detail.html", contact=c, shared_links=shared_links)

    @app.route("/contacts/add", methods=["GET", "POST"])
    @login_required
    def contacts_add():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            name = request.form.get("name", "").strip() or email.split("@")[0].title()
            company = request.form.get("company", "").strip()
            if not email or "@" not in email:
                flash("Enter a valid email address.", "error")
            else:
                db.session.add(Contact(
                    owner_id=current_user.id, email=email, name=name, slug=slugify(email),
                    company=company, avatar=pick_avatar(email),
                    status="invited", added_at="2026-05-12",
                    note=request.form.get("note", "")[:240],
                ))
                db.session.add(ContactRequest(
                    sender_id=current_user.id, recipient_email=email, recipient_name=name,
                    message=request.form.get("message", "")[:280], status="pending",
                    direction="outgoing", created_at="2026-05-12",
                ))
                db.session.commit()
                flash(f"Invited {email}.", "success")
                return redirect(url_for("contact_detail", email_slug=slugify(email)))
        return render_template("contacts_add.html")

    @app.route("/contact/<email_slug>/share-folder", methods=["GET", "POST"])
    @login_required
    def contact_share_folder(email_slug):
        c = Contact.query.filter_by(owner_id=current_user.id, slug=email_slug).first_or_404()
        folders = sorted({i.folder for i in CloudItem.query.filter_by(user_id=current_user.id).all() if i.folder != "/"})
        if request.method == "POST":
            folder = request.form.get("folder", "").strip()
            if folder not in folders:
                flash("Choose a folder you own.", "error")
            else:
                c.shared_folders_count = (c.shared_folders_count or 0) + 1
                db.session.commit()
                flash(f"Shared {folder} with {c.name}.", "success")
                return redirect(url_for("contact_detail", email_slug=c.slug))
        return render_template("contact_share_folder.html", contact=c, folders=folders)

    @app.route("/contact/<email_slug>/remove", methods=["POST"])
    @login_required
    def contact_remove(email_slug):
        c = Contact.query.filter_by(owner_id=current_user.id, slug=email_slug).first_or_404()
        name = c.name
        db.session.delete(c)
        db.session.commit()
        flash(f"Removed {name} from contacts.", "success")
        return redirect(url_for("contacts_list"))

    @app.route("/contacts/request/<int:request_id>/respond", methods=["POST"])
    @login_required
    def contact_request_respond(request_id):
        req = ContactRequest.query.filter_by(id=request_id, sender_id=current_user.id).first_or_404()
        action = request.form.get("action", "")
        if action not in {"accept", "decline"}:
            flash("Choose accept or decline.", "error")
        else:
            req.status = "accepted" if action == "accept" else "declined"
            db.session.commit()
            flash(f"Contact request {req.status}.", "success")
        return redirect(url_for("contacts_list"))

    # ---------------- Chat ----------------

    @app.route("/chat")
    @login_required
    def chat_hub():
        threads = ChatThread.query.filter_by(owner_id=current_user.id).order_by(ChatThread.starred.desc(), ChatThread.last_message_at.desc()).all()
        return render_template("chat_hub.html", threads=threads)

    @app.route("/chat/<slug>", methods=["GET", "POST"])
    @login_required
    def chat_thread(slug):
        thread = ChatThread.query.filter_by(owner_id=current_user.id, slug=slug).first_or_404()
        if request.method == "POST":
            body = request.form.get("body", "").strip()
            if not body:
                flash("Type a message to send.", "error")
            else:
                db.session.add(ChatMessage(
                    thread_id=thread.id, sender_email=current_user.email,
                    body=body[:2000], created_at="2026-05-12",
                ))
                thread.last_message_at = "2026-05-12"
                db.session.commit()
                flash("Message sent.", "success")
                return redirect(url_for("chat_thread", slug=thread.slug))
        messages = ChatMessage.query.filter_by(thread_id=thread.id).order_by(ChatMessage.id).all()
        return render_template("chat_thread.html", thread=thread, messages=messages)

    @app.route("/chat/<slug>/upload", methods=["POST"])
    @login_required
    def chat_upload(slug):
        thread = ChatThread.query.filter_by(owner_id=current_user.id, slug=slug).first_or_404()
        name = request.form.get("name", "").strip()
        if not name:
            flash("Attachment file name is required.", "error")
        else:
            db.session.add(ChatMessage(
                thread_id=thread.id, sender_email=current_user.email,
                body=f"Shared file: {name}", attachment_name=name,
                created_at="2026-05-12",
            ))
            thread.last_message_at = "2026-05-12"
            db.session.commit()
            flash(f"Sent attachment {name}.", "success")
        return redirect(url_for("chat_thread", slug=thread.slug))

    @app.route("/chat/<slug>/call", methods=["GET", "POST"])
    @login_required
    def chat_call(slug):
        thread = ChatThread.query.filter_by(owner_id=current_user.id, slug=slug).first_or_404()
        if request.method == "POST":
            kind = request.form.get("call_kind", "voice")
            db.session.add(ChatMessage(
                thread_id=thread.id, sender_email=current_user.email,
                body=f"Started a {kind} call.", created_at="2026-05-12",
            ))
            thread.last_message_at = "2026-05-12"
            db.session.commit()
            flash(f"{kind.title()} call started.", "success")
            return redirect(url_for("chat_thread", slug=thread.slug))
        return render_template("chat_call.html", thread=thread)

    # ---------------- Transfers ----------------

    @app.route("/transfers")
    @login_required
    def transfers_list():
        transfers = (Transfer.query.filter_by(user_id=current_user.id)
                     .order_by(Transfer.completed_at.desc()).all())
        active = [t for t in transfers if t.status in {"queued", "paused"}]
        return render_template("transfers.html", transfers=transfers, active=active)

    @app.route("/transfers/history")
    @login_required
    def transfers_history():
        transfers = (Transfer.query.filter_by(user_id=current_user.id, status="completed")
                     .order_by(Transfer.completed_at.desc()).all())
        return render_template("transfers_history.html", transfers=transfers)

    # ---------------- Settings ----------------

    @app.route("/settings")
    @login_required
    def settings_hub():
        return render_template("settings_hub.html")

    @app.route("/settings/account")
    @login_required
    def settings_account():
        return render_template("settings_account.html")

    @app.route("/settings/storage")
    @login_required
    def settings_storage():
        items = CloudItem.query.filter_by(user_id=current_user.id).all()
        total = sum(i.size_mb or 0 for i in items) / 1024
        by_folder = {}
        for i in items:
            by_folder[i.folder] = by_folder.get(i.folder, 0) + (i.size_mb or 0)
        breakdown = sorted(by_folder.items(), key=lambda kv: -kv[1])[:10]
        return render_template("settings_storage.html", total_gb=total, breakdown=breakdown)

    @app.route("/settings/transfer", methods=["GET", "POST"])
    @login_required
    def settings_transfer():
        cfg = TransferSetting.query.filter_by(user_id=current_user.id).first()
        if not cfg:
            cfg = TransferSetting(user_id=current_user.id)
            db.session.add(cfg)
            db.session.commit()
        if request.method == "POST":
            cfg.upload_limit_mbps = int(request.form.get("upload_limit_mbps") or 0)
            cfg.download_limit_mbps = int(request.form.get("download_limit_mbps") or 0)
            cfg.max_parallel = max(1, int(request.form.get("max_parallel") or 1))
            cfg.priority_uploads = bool(request.form.get("priority_uploads"))
            cfg.pause_on_metered = bool(request.form.get("pause_on_metered"))
            db.session.commit()
            flash("Transfer preferences updated.", "success")
            return redirect(url_for("settings_transfer"))
        return render_template("settings_transfer.html", cfg=cfg)

    @app.route("/settings/security")
    @login_required
    def settings_security():
        cfg = SecuritySetting.query.filter_by(user_id=current_user.id).first()
        events = (SecurityEvent.query.filter_by(user_id=current_user.id)
                  .order_by(SecurityEvent.at.desc()).limit(10).all())
        return render_template("settings_security.html", cfg=cfg, events=events)

    @app.route("/settings/encryption")
    @login_required
    def settings_encryption():
        cfg = SecuritySetting.query.filter_by(user_id=current_user.id).first()
        return render_template("settings_encryption.html", cfg=cfg)

    @app.route("/settings/notifications", methods=["GET", "POST"])
    @login_required
    def settings_notifications():
        prefs = NotificationPref.query.filter_by(user_id=current_user.id).order_by(NotificationPref.id).all()
        if request.method == "POST":
            enabled_kinds = set(request.form.getlist("enabled"))
            for p in prefs:
                p.enabled = p.kind in enabled_kinds
            db.session.commit()
            flash("Notification preferences updated.", "success")
            return redirect(url_for("settings_notifications"))
        return render_template("settings_notifications.html", prefs=prefs)

    # ---------------- Security ----------------

    @app.route("/security")
    @login_required
    def security_hub():
        cfg = SecuritySetting.query.filter_by(user_id=current_user.id).first()
        events = (SecurityEvent.query.filter_by(user_id=current_user.id)
                  .order_by(SecurityEvent.at.desc()).limit(20).all())
        return render_template("security_hub.html", cfg=cfg, events=events)

    @app.route("/security/2fa", methods=["GET", "POST"])
    @login_required
    def security_2fa():
        if request.method == "POST":
            current_user.two_factor_enabled = bool(request.form.get("enable"))
            cfg = SecuritySetting.query.filter_by(user_id=current_user.id).first()
            if cfg:
                cfg.last_2fa_change = "2026-05-12"
            db.session.add(SecurityEvent(
                user_id=current_user.id, kind="2FA toggled",
                detail=("Two-factor enabled" if current_user.two_factor_enabled else "Two-factor disabled"),
                ip_address="203.0.113.99", location="Indianapolis, IN",
                device="Web client", at="2026-05-12",
            ))
            db.session.commit()
            flash("Two-factor authentication preference saved.", "success")
            return redirect(url_for("security_2fa"))
        return render_template("security_2fa.html")

    @app.route("/security/master-key/backup", methods=["GET", "POST"])
    @login_required
    def security_master_key_backup():
        cfg = SecuritySetting.query.filter_by(user_id=current_user.id).first()
        if request.method == "POST":
            current_user.recovery_key_saved = True
            if cfg:
                cfg.master_key_backed_up_at = "2026-05-12"
            db.session.add(SecurityEvent(
                user_id=current_user.id, kind="Master key backup",
                detail="User backed up master recovery key",
                ip_address="203.0.113.99", location="Indianapolis, IN",
                device="Web client", at="2026-05-12",
            ))
            db.session.commit()
            flash("Master key backup completed.", "success")
            return redirect(url_for("security_hub"))
        return render_template("security_master_key_backup.html", cfg=cfg)

    @app.route("/security/sessions")
    @login_required
    def security_sessions():
        events = (SecurityEvent.query.filter_by(user_id=current_user.id, kind="Sign-in")
                  .order_by(SecurityEvent.at.desc()).all())
        devices = SyncDevice.query.filter_by(user_id=current_user.id).all()
        return render_template("security_sessions.html", events=events, devices=devices)

    # ---------------- Sync ----------------

    @app.route("/sync")
    def sync_hub():
        return render_template("sync_hub.html",
                               desktop_devices=PLATFORM_ICON,
                               authed=current_user.is_authenticated)

    @app.route("/sync/desktop")
    def sync_desktop():
        return render_template("sync_desktop.html",
                               authed=current_user.is_authenticated)

    @app.route("/sync/mobile")
    def sync_mobile():
        return render_template("sync_mobile.html",
                               authed=current_user.is_authenticated)

    @app.route("/sync/devices")
    @login_required
    def sync_devices():
        devices = SyncDevice.query.filter_by(user_id=current_user.id).order_by(SyncDevice.id).all()
        return render_template("sync_devices.html", devices=devices)

    # ---------------- Business ----------------

    @app.route("/business")
    def business_hub():
        industries = BusinessIndustry.query.order_by(BusinessIndustry.id).all()
        business_plans = Plan.query.filter_by(audience="business", active=True).order_by(Plan.monthly_price).all()
        return render_template("business_hub.html", industries=industries, plans=business_plans)

    @app.route("/business/<slug>")
    def business_industry(slug):
        ind = BusinessIndustry.query.filter_by(slug=slug).first_or_404()
        plan = Plan.query.filter_by(slug=ind.recommended_plan_slug).first()
        return render_template("business_industry.html", industry=ind, plan=plan)

    # ---------------- Pricing extras ----------------

    @app.route("/pricing/<slug>")
    def pricing_plan(slug):
        return redirect(url_for("plan_detail", slug=slug), code=301)

    @app.route("/pricing/<slug>/upgrade", methods=["GET", "POST"])
    @login_required
    def pricing_upgrade(slug):
        plan = Plan.query.filter_by(slug=slug, active=True).first_or_404()
        if request.method == "POST":
            session["checkout_plan"] = plan.slug
            session["billing_cycle"] = request.form.get("billing_cycle", "yearly")
            session["seats"] = max(1, int(request.form.get("seats", plan.users_included or 1) or 1))
            flash(f"{plan.name} added to cart with {session['billing_cycle']} billing.", "success")
            return redirect(url_for("checkout"))
        return render_template("pricing_upgrade.html", plan=plan)

    # ---------------- About ----------------

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/about/why-mega")
    def about_why_mega():
        return render_template("about_why.html")

    @app.route("/about/team")
    def about_team():
        return render_template("about_team.html",
                               sample_avatars=[pick_avatar(f"team-{i}") for i in range(8)])

    # ---------------- File icon helper available everywhere ----------------
    app.jinja_env.globals["ext_thumb"] = ext_thumb
    app.jinja_env.globals["platform_icon"] = lambda p: PLATFORM_ICON.get(p, "DA-img-2.png")
    app.jinja_env.globals["plan_icon"] = lambda cat: PLAN_ICON_BY_CATEGORY.get(cat, "MEGA-icon-cloud.png")
