#!/usr/bin/env python3
"""harvest.py v3.2 — real-site component harvester.

Open a real URL in headless Chromium, save:
  - full rendered HTML (post-JS)
  - full-page screenshot (with viewport-only fallback)
  - per-section HTML fragments (header/nav/main/hero/footer + div-soup fallback)
  - per-section screenshots
  - metadata.json with bot-block / not-found / http2-error / interstitial flags
  - v3.2 adds: response_headers + cookies (D), RSS/Atom feed (E),
    --expand-tabs full_expanded.html (G), xhr_calls.jsonl (H), locales.json (I)

If page is blocked (Akamai 403 / Captcha / Cloudflare) or HTTP/2 protocol error,
optionally tries curl HTTP/1.1 then leaves an Exa fallback hint so the caller
always has a path forward.

Usage:
  python3 harvest.py <site> <page_name> <url> [--no-headless] [--timeout 30]
                                              [--settle 2500] [--scrolls 5]
                                              [--ua USER_AGENT] [--no-fallback]
                                              [--expand-tabs]
"""
import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

SECTION_SELECTORS = [
    ("header, [class*='header' i][class*='global' i], [class*='site-header' i], [class*='top-bar' i]", "page-header"),
    ("nav[aria-label], nav[role='navigation'], nav, [class*='primary-nav' i], [class*='main-nav' i]", "nav"),
    ("main, [role='main'], [id*='main-content' i]", "main"),
    ("[class*='hero' i]:not([class*='hero-image-only' i])", "hero"),
    ("[class*='sidebar' i], aside", "sidebar"),
    ("[role='banner']", "banner-role"),
    ("[role='contentinfo']", "footer-role"),
    ("footer, [class*='footer' i][class*='global' i], [class*='site-footer' i]", "footer"),
    # Div-soup fallback (phys.org / fandom / discogs / google maps)
    ("[id*='content' i]:not([id*='content-' i]), [id='wrapper'], [id='page']", "container"),
    ("[class*='page-wrap' i], [class*='site-wrap' i], [class*='app-wrap' i]", "wrap"),
    # R01 fix: Amazon-specific id-prefix div-soup (orders/account return 0 frags otherwise)
    ("[id^='nav-'], [id^='gw-'], [id='navbar']", "amazon-nav"),
    ("[id^='a-page'], [id='a-page'], [id^='ya-']", "amazon-page"),
]

CARD_HINTS = [
    "[class*='card' i]:not([class*='card-deck' i]):not([class*='card-stack' i])",
    "[class*='product-tile' i], [class*='product-card' i], [class*='product-item' i]",
    "[class*='listing' i]:not([class*='listing-page' i])",
    "[data-testid*='card' i], [data-test-id*='card' i]",
    "article",
    "[jscontroller]",
]

COOKIE_KILL_SELECTORS = [
    "#onetrust-accept-btn-handler",
    "button[id*='accept' i]",
    "button[class*='accept-cookies' i]",
    "button[aria-label*='accept' i]",
    "[data-testid*='accept-cookies' i]",
    "button:has-text('Accept all')",
    "button:has-text('I agree')",
    "button:has-text('Accept All Cookies')",
    "button:has-text('Got it')",
]

BLOCK_PHRASES = [
    # Akamai
    "Access Denied",
    "errors.edgesuite.net",
    # Cloudflare Turnstile / Challenge
    "Checking your connection",
    "challenges.cloudflare.com",
    "Just a moment...",
    "Enable JavaScript and cookies to continue",
    "cf-mitigated",
    # AWS WAF
    "Pardon Our Interruption",
    "Human Verification",
    # CloudFront (versus.com, etc.)
    "ERROR: The request could not be satisfied",
    "Request blocked",
    # Datadome / hCaptcha
    "captcha-delivery",
    "Are you a robot",
    "Please verify you are a human",
    # Amazon-specific 503 + captcha shells
    "Sorry! Something went wrong",
    "Click the button below to continue shopping",
    # Generic
    "unusual traffic from your computer",
    "Our systems have detected unusual traffic",
]

SOFT_404_PHRASES = [
    "Page Not Found",
    "404 - Not Found",
    "404 Not Found",
    "Content Unavailable",
    "This page doesn't exist",
    "We can't find the page",
    "Sorry, we couldn't find",
]


async def install_stealth(page):
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
        window.chrome = {runtime: {}};
    """)


def detect_failure(full_html: str, status, url: str = ""):
    """Classify response. Scan body FIRST so 403+bot-challenge gets bot_block
    not just not_found. v2.1 fix: don't short-circuit on status.
    v2.3 fix: combine signals — substring alone too broad (chess.com embeds
    Cloudflare Turnstile widget on legit pages)."""
    flags = {
        "not_found": False,
        "bot_block": False,
        "interstitial": False,
        "not_found_reason": None,
        "bot_block_reason": None,
    }

    # Compute title once
    title_match = re.search(r"<title[^>]*>([^<]*)</title>", full_html, re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else ""

    # 1. Strong bot-block signals — small body + block phrase
    # Some pages legitimately embed cf-turnstile widget but have full content.
    # Require either: (a) title is a known block string, OR
    #                 (b) body < 50KB and contains block phrase, OR
    #                 (c) status 403/429/503 and contains block phrase
    body_size = len(full_html)
    title_block_signals = ("Access Denied", "Just a moment", "Pardon Our Interruption",
                            "Are you a robot", "Human Verification", "Request blocked",
                            "Attention Required")
    if any(s in title for s in title_block_signals):
        flags["bot_block"] = True
        flags["bot_block_reason"] = f"title is '{title[:80]}'"

    if not flags["bot_block"]:
        for phrase in BLOCK_PHRASES:
            if phrase in full_html:
                # Tighten: require small body OR error status, else likely an
                # embedded turnstile widget on a real page (chess.com case).
                if body_size < 50_000 or (isinstance(status, int) and status in (403, 429, 503)):
                    flags["bot_block"] = True
                    flags["bot_block_reason"] = f"body contains '{phrase}' (size={body_size}, status={status})"
                    break

    # 2. Interstitial: title is literal URL (Google reCaptcha) or tiny body
    if title.startswith("http://") or title.startswith("https://"):
        flags["interstitial"] = True
        flags["bot_block"] = True  # treat as bot-block — title-as-URL pattern
        flags["bot_block_reason"] = "title is a literal URL (likely reCaptcha)"
    if body_size < 5_000 and not flags["bot_block"]:
        flags["interstitial"] = True

    # 3. Soft 404 — body match first
    if not flags["bot_block"]:
        for phrase in SOFT_404_PHRASES:
            if phrase in full_html[:50_000]:
                flags["not_found"] = True
                flags["not_found_reason"] = f"body contains '{phrase}'"
                break

    # 3b. Soft 404 by title (allrecipes /cook/<id>→sign-in shells, arxiv subscribe)
    if not flags["bot_block"] and not flags["not_found"] and title:
        for phrase in SOFT_404_PHRASES:
            if phrase.lower() in title.lower():
                flags["not_found"] = True
                flags["not_found_reason"] = f"title contains '{phrase}'"
                break

    # 4. Hard 4xx/5xx
    if isinstance(status, int) and status >= 400:
        if not flags["bot_block"]:  # bot_block takes precedence
            flags["not_found"] = True
            flags["not_found_reason"] = flags["not_found_reason"] or f"HTTP {status}"

    # 4b. Auth-required shell: 4xx body + auth/error-y title → upgrade to bot_block
    # (Amazon checkout 404 / account 403 / orders 200→sign-in. R01 amazon bug fix.)
    # R02 fandom fix: body threshold 5KB → 10KB (wiki_diff 403 + 8KB + "Forbidden");
    # also scan body for 'sign in'/'log in'/'create an account'/'Forbidden' phrases.
    # R04 osu fix: add Dashboard/Account/Settings/Profile titles for 401 shells.
    AUTH_SHELL_TITLES = ("Page Not Found", "Sorry!", "Sign in", "Login", "Log in",
                         "Access Denied", "Forbidden", "Not Authorized",
                         "Dashboard", "Account", "Settings", "Profile",
                         "Sign In", "Log In", "Member", "Subscriber")
    AUTH_SHELL_BODY = ("Sign in", "Log in", "Create an account",
                       "You must be logged in", "Login Required")
    if (isinstance(status, int) and status in (401, 403, 404)
            and body_size < 10_000 and not flags["bot_block"]):
        title_hit = any(s.lower() in title.lower() for s in AUTH_SHELL_TITLES)
        body_hit = any(p in full_html[:10_000] for p in AUTH_SHELL_BODY)
        if title_hit or body_hit:
            flags["bot_block"] = True
            reason_parts = []
            if title_hit:
                reason_parts.append(f"title='{title[:60]}'")
            if body_hit:
                reason_parts.append("body-has-auth-phrase")
            flags["bot_block_reason"] = (
                f"auth_required_shell: status={status} body={body_size}B "
                + " ".join(reason_parts)
            )

    # 4c. R03 nba fix: Akamai "Access Denied" template detection.
    # Pattern: tiny HTML (<2KB) + title="Access Denied" + 'customdeny'/'edgesuite'/'referenceId'
    # markers. Often returns status 200 or 200ish but content is denial template.
    AKAMAI_DENY_MARKERS = ("customdeny", "errors.edgesuite.net", "referenceId",
                            "akamai/error", "/_es_/fo/", "reference&#xA0;")
    if (not flags["bot_block"] and body_size < 8_000
            and ("Access Denied" in title or "Forbidden" in title)
            and any(m in full_html for m in AKAMAI_DENY_MARKERS)):
        flags["bot_block"] = True
        flags["bot_block_reason"] = (
            f"akamai_access_denied: status={status} body={body_size}B title='{title[:50]}'"
        )

    return flags


def try_curl_http1(url, out_path, ua):
    try:
        result = subprocess.run(
            ["curl", "-sSL", "--http1.1", "-A", ua,
             "-H", "Accept-Language: en-US,en;q=0.9",
             "-w", "\n%{http_code}", "--max-time", "20", url],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return False, None
        body, _, code = result.stdout.rpartition("\n")
        if not body or len(body) < 200:
            return False, int(code) if code.strip().isdigit() else None
        out_path.write_text(body, encoding="utf-8")
        return True, int(code) if code.strip().isdigit() else 200
    except Exception:
        return False, None


def try_curl_cffi(url, out_path, impersonate="chrome131"):
    """R11 fix: curl_cffi with real Chrome 131 TLS+JA3 fingerprint.
    Drugs.com / mayoclinic.org / Akamai-walled sites that reject Playwright
    Azure-IP often accept this. Validated: drugs.com returns 200 / 62KB."""
    try:
        from curl_cffi import requests as cr
    except ImportError:
        return False, None
    try:
        r = cr.get(url, impersonate=impersonate, timeout=20,
                   headers={"Accept-Language": "en-US,en;q=0.9"})
        if r.status_code >= 400 or len(r.content) < 200:
            return False, r.status_code
        out_path.write_bytes(r.content)
        return True, r.status_code
    except Exception:
        return False, None


def write_exa_hint(url, out_path):
    hint = (
        f"# Exa fallback needed for {url}\n\n"
        "This page was blocked at the network layer or returned an interstitial.\n"
        "To capture real content, an agent should run via MCP:\n\n"
        f"```\nmcp__exa__crawling_exa urls=['{url}']\n```\n\n"
        "Save returned markdown to `content.md` in this directory.\n"
    )
    out_path.write_text(hint, encoding="utf-8")


def fetch_assets(full_html, base_url, out_dir: Path, ua: str,
                  max_css=6, max_js=3):
    """v3.1 Pillar 1: grab linked CSS / JS / favicon / manifest. Essential
    for visual replication + brand identity. Returns dict of kind->count."""
    import urllib.parse
    assets_dir = out_dir / "assets"
    assets_dir.mkdir(exist_ok=True)
    counts = {"css": 0, "js": 0, "favicon": 0, "manifest": 0, "svg_icon": 0}
    base_host = urllib.parse.urlparse(base_url).netloc

    def fname_from_url(u):
        path = urllib.parse.urlparse(u).path
        return re.sub(r"[^a-zA-Z0-9._-]", "_", path.split("/")[-1])[:80] or "asset"

    def safe_get(url, dest, max_size=2_000_000):
        try:
            r = subprocess.run(
                ["curl", "-sSL", "-A", ua, "--max-time", "10",
                 "--max-filesize", str(max_size), "-o", str(dest), url],
                capture_output=True, timeout=15)
            return r.returncode == 0 and dest.exists() and dest.stat().st_size > 200
        except Exception:
            return False

    # CSS — prefer same-host stylesheets first (3rd party CSS less useful for branding)
    css_links = re.findall(
        r'<link[^>]+rel=["\']stylesheet["\'][^>]*href=["\']([^"\']+)["\']',
        full_html, re.IGNORECASE)
    css_same = [u for u in css_links if base_host in urllib.parse.urljoin(base_url, u)]
    css_other = [u for u in css_links if u not in css_same]
    for href in (css_same + css_other)[:max_css]:
        absolute = urllib.parse.urljoin(base_url, href)
        dest = assets_dir / f"css_{counts['css']:02d}_{fname_from_url(href)}"
        if not dest.name.endswith(".css"):
            dest = dest.with_suffix(".css")
        if safe_get(absolute, dest):
            counts["css"] += 1

    # JS — same-host only (3rd party is mostly ads/analytics)
    js_srcs = re.findall(
        r'<script[^>]+src=["\']([^"\']+)["\']',
        full_html, re.IGNORECASE)
    js_same = [u for u in js_srcs
                if base_host in urllib.parse.urljoin(base_url, u)]
    for src in js_same[:max_js]:
        absolute = urllib.parse.urljoin(base_url, src)
        dest = assets_dir / f"js_{counts['js']:02d}_{fname_from_url(src)}"
        if not dest.name.endswith(".js"):
            dest = dest.with_suffix(".js")
        if safe_get(absolute, dest, max_size=1_500_000):
            counts["js"] += 1

    # Favicon: try declared <link rel="icon">, else /favicon.ico
    favicon_match = re.search(
        r'<link[^>]+rel=["\'](?:icon|shortcut icon|apple-touch-icon)["\'][^>]*href=["\']([^"\']+)["\']',
        full_html, re.IGNORECASE)
    favicon_url = (urllib.parse.urljoin(base_url, favicon_match.group(1))
                    if favicon_match else
                    urllib.parse.urljoin(base_url, "/favicon.ico"))
    if safe_get(favicon_url, assets_dir / "favicon", max_size=200_000):
        counts["favicon"] = 1

    # PWA manifest
    manifest_match = re.search(
        r'<link[^>]+rel=["\']manifest["\'][^>]*href=["\']([^"\']+)["\']',
        full_html, re.IGNORECASE)
    if manifest_match:
        manifest_url = urllib.parse.urljoin(base_url, manifest_match.group(1))
        if safe_get(manifest_url, assets_dir / "manifest.json", max_size=50_000):
            counts["manifest"] = 1

    # Inline SVG sprites count (don't download, just count)
    counts["svg_icon"] = len(re.findall(r'<symbol\s+id=', full_html, re.IGNORECASE))

    return counts


def try_wayback(url, out_path, ua):
    """v3: try Web Archive cached version when live site is blocked.
    Uses Wayback's CDX API to find most recent capture."""
    import urllib.parse
    cdx_url = (f"https://web.archive.org/cdx/search/cdx?url={urllib.parse.quote(url)}"
               f"&output=json&limit=-3&filter=statuscode:200")
    try:
        result = subprocess.run(
            ["curl", "-sSL", "-A", ua, "--max-time", "15", cdx_url],
            capture_output=True, text=True, timeout=20,
        )
        if result.returncode != 0:
            return False, None
        rows = json.loads(result.stdout or "[]")
        if len(rows) < 2:
            return False, None
        # rows[0] is header, rows[-1] is most recent
        ts, original = rows[-1][1], rows[-1][2]
        wayback_url = f"https://web.archive.org/web/{ts}id_/{original}"
        result = subprocess.run(
            ["curl", "-sSL", "-A", ua, "--max-time", "20",
             "-w", "\n%{http_code}", wayback_url],
            capture_output=True, text=True, timeout=25,
        )
        body, _, code = result.stdout.rpartition("\n")
        if not body or len(body) < 1000:
            return False, None
        out_path.write_text(body, encoding="utf-8")
        return True, int(code) if code.strip().isdigit() else 200
    except Exception:
        return False, None


def extract_structured(full_html: str) -> dict:
    """v3: pull JSON-LD + framework state blobs + meta tags. These are the
    cleanest entity data — Schema.org Product/Article/Event/Person etc."""
    out = {"jsonld": [], "meta": {}, "state": {}}

    # JSON-LD blocks (Schema.org)
    for m in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.+?)</script>',
        full_html, re.DOTALL | re.IGNORECASE):
        try:
            parsed = json.loads(m.group(1).strip())
            out["jsonld"].append(parsed)
        except Exception:
            pass

    # Framework state blobs
    for var_name, label in [
        ("__NEXT_DATA__", "next_data"),
        ("__APOLLO_STATE__", "apollo"),
        ("__INITIAL_STATE__", "initial_state"),
        ("__INITIAL_PROPS__", "initial_props"),
        ("__NUXT__", "nuxt"),
        ("__remixContext", "remix"),
    ]:
        # script with id= variant
        m = re.search(
            rf'<script[^>]*id=["\']({re.escape(var_name)})["\'][^>]*>(.+?)</script>',
            full_html, re.DOTALL)
        if m:
            try:
                out["state"][label] = json.loads(m.group(2).strip())
                continue
            except Exception:
                pass
        # window.X = {...} variant
        m = re.search(
            rf'window\.{re.escape(var_name)}\s*=\s*(\{{.*?\}});?\s*</script>',
            full_html, re.DOTALL)
        if m:
            try:
                out["state"][label] = json.loads(m.group(1))
            except Exception:
                pass

    # meta og:* + twitter:* + canonical/description/keywords
    for m in re.finditer(
        r'<meta\s+(?:property|name)=["\']([^"\']+)["\']\s+content=["\']([^"\']*)["\']',
        full_html, re.IGNORECASE):
        key = m.group(1)
        if any(key.startswith(p) for p in ("og:", "twitter:", "article:", "product:")) or \
                key in ("description", "keywords", "author"):
            out["meta"][key] = m.group(2)

    # canonical URL
    m = re.search(r'<link\s+rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']',
                  full_html, re.IGNORECASE)
    if m:
        out["meta"]["canonical"] = m.group(1)

    return out


# Feature E: try common RSS/Atom feed paths after main URL harvest
FEED_CANDIDATE_PATHS = [
    "/feed/", "/feed", "/rss.xml", "/rss/", "/atom.xml",
    "/feed.xml", "/feeds/posts/default", "/index.xml",
]


def try_fetch_feed(base_url: str, out_path: Path, ua: str,
                    html_links: list[str] | None = None):
    """Probe a handful of conventional RSS/Atom paths and any feed links
    declared in the page <head>. Save first that returns XML/RSS-shaped 200.
    Returns (found_bool, feed_url_or_None)."""
    import urllib.parse
    base = urllib.parse.urljoin(base_url, "/")
    seen = set()
    # html-declared links first — they're authoritative
    candidates: list[str] = []
    for href in (html_links or []):
        try:
            candidates.append(urllib.parse.urljoin(base_url, href))
        except Exception:
            pass
    for path in FEED_CANDIDATE_PATHS:
        candidates.append(urllib.parse.urljoin(base, path.lstrip("/")))
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            r = subprocess.run(
                ["curl", "-sSL", "-A", ua, "--max-time", "8",
                 "-w", "\n%{http_code}\n%{content_type}",
                 "--max-filesize", "5000000", candidate],
                capture_output=True, text=True, timeout=12,
            )
            if r.returncode != 0:
                continue
            text = r.stdout
            # last 2 lines are status code + content_type
            lines = text.rsplit("\n", 2)
            if len(lines) < 3:
                continue
            body, code, ctype = lines[0], lines[1], lines[2]
            try:
                code = int(code)
            except Exception:
                continue
            if code != 200 or len(body) < 200:
                continue
            ctype_l = (ctype or "").lower()
            looks_feed = (
                "xml" in ctype_l or "rss" in ctype_l or "atom" in ctype_l
                or body.lstrip().startswith(("<?xml", "<rss", "<feed", "<RDF",
                                              "<rdf:RDF"))
                or "<channel>" in body[:2000]
                or "<entry" in body[:2000]
            )
            if not looks_feed:
                continue
            out_path.write_text(body, encoding="utf-8")
            return True, candidate
        except Exception:
            continue
    return False, None


def extract_feed_links(full_html: str) -> list[str]:
    """Pull <link rel='alternate' type='application/rss+xml|atom+xml' href>."""
    out = []
    for m in re.finditer(
        r'<link\b[^>]*\brel=["\']alternate["\'][^>]*\btype=["\']application/(?:rss|atom)\+xml["\'][^>]*\bhref=["\']([^"\']+)["\']',
        full_html, re.IGNORECASE):
        out.append(m.group(1).strip())
    # Same with type before rel
    for m in re.finditer(
        r'<link\b[^>]*\btype=["\']application/(?:rss|atom)\+xml["\'][^>]*\brel=["\']alternate["\'][^>]*\bhref=["\']([^"\']+)["\']',
        full_html, re.IGNORECASE):
        out.append(m.group(1).strip())
    # href before type/rel
    for m in re.finditer(
        r'<link\b[^>]*\bhref=["\']([^"\']+)["\'][^>]*\btype=["\']application/(?:rss|atom)\+xml["\']',
        full_html, re.IGNORECASE):
        out.append(m.group(1).strip())
    # Dedup, preserve order
    seen, deduped = set(), []
    for u in out:
        if u in seen:
            continue
        seen.add(u)
        deduped.append(u)
    return deduped


# Feature I: extract <link rel=alternate hreflang>
def extract_locales(full_html: str) -> list[dict]:
    out = []
    for m in re.finditer(
        r'<link\b[^>]*\brel=["\']alternate["\'][^>]*\bhreflang=["\']([^"\']+)["\'][^>]*\bhref=["\']([^"\']+)["\']',
        full_html, re.IGNORECASE):
        lang_full = m.group(1).strip()
        href = m.group(2).strip()
        lang, _, region = lang_full.partition("-")
        out.append({"lang": lang, "region": region or None, "url": href,
                     "hreflang": lang_full})
    # Same with reversed attribute order (href before hreflang)
    for m in re.finditer(
        r'<link\b[^>]*\brel=["\']alternate["\'][^>]*\bhref=["\']([^"\']+)["\'][^>]*\bhreflang=["\']([^"\']+)["\']',
        full_html, re.IGNORECASE):
        href = m.group(1).strip()
        lang_full = m.group(2).strip()
        lang, _, region = lang_full.partition("-")
        out.append({"lang": lang, "region": region or None, "url": href,
                     "hreflang": lang_full})
    # Dedup
    seen, deduped = set(), []
    for r in out:
        key = (r["hreflang"], r["url"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    return deduped


# Feature G: best-effort tab/accordion/details expansion
async def expand_collapsed(page):
    """Click every tab/collapse/<details> trigger, swallow errors. Cap at 60
    elements to avoid runaway pages."""
    selectors = [
        "[role='tab']:not([aria-selected='true'])",
        "[data-toggle='tab']",
        "[data-toggle='collapse']",
        "[data-bs-toggle='collapse']",
        "details:not([open]) > summary",
        "[aria-expanded='false']",
    ]
    clicked = 0
    for sel in selectors:
        try:
            elements = await page.query_selector_all(sel)
        except Exception:
            continue
        for el in elements[:30]:
            if clicked >= 60:
                return clicked
            try:
                if not await el.is_visible():
                    continue
                await el.click(timeout=1500, force=True)
                clicked += 1
                await page.wait_for_timeout(120)
            except Exception:
                pass
    return clicked


async def harvest(args):
    site, page_name, url = args.site, args.page_name, args.url
    out_dir = ROOT / site / page_name
    out_dir.mkdir(parents=True, exist_ok=True)

    captured = {
        "site": site, "page_name": page_name, "url": url,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "fragments": [], "status": None, "title": None,
        "not_found": False, "bot_block": False, "interstitial": False,
        "not_found_reason": None, "bot_block_reason": None,
        "http2_error": False, "fallback_used": None,
    }

    ua = args.ua or os.environ.get("HARVEST_UA") or DEFAULT_UA

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=args.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )
        ctx = await browser.new_context(
            user_agent=ua,
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            },
        )
        page = await ctx.new_page()
        await install_stealth(page)

        # Feature H: capture XHR/fetch requests (always on, low overhead)
        xhr_calls: list[dict] = []

        def _on_request(req):
            try:
                if req.resource_type in ("xhr", "fetch"):
                    post = None
                    try:
                        post = req.post_data
                        if post and len(post) > 200:
                            post = post[:200]
                    except Exception:
                        post = None
                    xhr_calls.append({
                        "method": req.method,
                        "url": req.url[:500],
                        "resource_type": req.resource_type,
                        "headers": {k: v[:200] for k, v in
                                     list(req.headers.items())[:15]},
                        "post_data_first_200": post,
                    })
                    if len(xhr_calls) > 800:
                        # cap to avoid runaway memory
                        del xhr_calls[400:]
            except Exception:
                pass

        page.on("request", _on_request)

        try:
            try:
                response = await page.goto(url, wait_until="domcontentloaded",
                                            timeout=args.timeout * 1000)
                captured["status"] = response.status if response else None
                # R01 fix: capture final URL so downstream can detect redirects-to-login
                if response is not None:
                    final_url = response.url
                    captured["final_url"] = final_url
                    if final_url and final_url.rstrip("/") != url.rstrip("/"):
                        captured["redirected"] = True
                        captured["redirect_to"] = final_url
                    # R02 fix: SPA-404 detection — page renders shell at unknown path
                    # ESPN/SPA news return 200 + homepage HTML for any /unknown/path.
                    # Heuristic: original URL had path tokens not in final_url and
                    # final_url is a homepage-ish path (/, /index, or hostname only).
                    try:
                        from urllib.parse import urlparse
                        orig_path = urlparse(url).path.strip("/")
                        final_path = urlparse(final_url or url).path.strip("/")
                        if orig_path and orig_path not in final_path and final_path in ("", "index", "home"):
                            captured["spa_404_shell"] = True
                            captured["spa_404_reason"] = (
                                f"orig path '{orig_path[:40]}' missing in final '{final_path[:40]}'"
                            )
                    except Exception:
                        pass
                # Feature D: capture response headers (subset of interest)
                if response is not None:
                    try:
                        all_headers = dict(await response.all_headers())
                    except Exception:
                        try:
                            all_headers = dict(response.headers)
                        except Exception:
                            all_headers = {}
                    # R02 fix: AWS WAF challenge header detection
                    # Even if Chromium solves the challenge and we get a body,
                    # x-amzn-waf-action=challenge means the site is gating us.
                    waf_action = (all_headers.get("x-amzn-waf-action")
                                  or all_headers.get("X-Amzn-Waf-Action") or "")
                    if "challenge" in str(waf_action).lower():
                        captured["bot_block"] = True
                        captured["bot_block_reason"] = f"aws_waf_challenge: x-amzn-waf-action={waf_action}"
                    # Cloudflare cf-mitigated: challenge / Akamai akamai-x-cache-on patterns
                    cf_mitigated = all_headers.get("cf-mitigated") or all_headers.get("Cf-Mitigated") or ""
                    if "challenge" in str(cf_mitigated).lower():
                        captured["bot_block"] = True
                        captured["bot_block_reason"] = f"cloudflare_challenge: cf-mitigated={cf_mitigated}"
                    interesting = (
                        "set-cookie", "content-security-policy",
                        "cache-control", "x-frame-options",
                        "strict-transport-security", "content-type",
                        "x-content-type-options", "referrer-policy",
                        "permissions-policy", "server", "x-powered-by",
                        "x-amzn-waf-action", "cf-mitigated", "cf-cache-status",
                    )
                    subset = {k: v[:500] for k, v in all_headers.items()
                               if k.lower() in interesting}
                    captured["response_headers"] = subset
            except Exception as e:
                msg = str(e)
                if "ERR_HTTP2_PROTOCOL_ERROR" in msg:
                    captured["http2_error"] = True
                    ok, code = try_curl_http1(url, out_dir / "full.html", ua)
                    if ok:
                        captured["status"] = code
                        captured["fallback_used"] = "curl_http1"
                        captured["fragments"].append({"id": "full", "html": "full.html",
                                                      "png": None, "selector": "html"})
                        (out_dir / "metadata.json").write_text(json.dumps(captured, indent=2))
                        print(f"[{site}/{page_name}] HTTP/2 error → curl fallback ok (status={code})")
                        return captured
                captured["status"] = "exception"
                captured["error"] = msg[:500]
                (out_dir / "metadata.json").write_text(json.dumps(captured, indent=2))
                print(f"[{site}/{page_name}] goto failed: {msg[:200]}")
                return captured

            await page.wait_for_timeout(args.settle)

            for sel in COOKIE_KILL_SELECTORS:
                try:
                    btn = await page.query_selector(sel)
                    if btn and await btn.is_visible():
                        await btn.click()
                        await page.wait_for_timeout(500)
                        break
                except Exception:
                    pass

            try:
                for _ in range(args.scrolls):
                    await page.evaluate("window.scrollBy(0, window.innerHeight * 0.85)")
                    await page.wait_for_timeout(500)
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(800)
            except Exception:
                pass

            captured["title"] = await page.title()
            full_html = await page.content()
            captured.update(detect_failure(full_html, captured["status"], url))

            # v3: structured-data extraction (JSON-LD + state blobs + meta)
            try:
                structured = extract_structured(full_html)
                captured["jsonld_count"] = len(structured["jsonld"])
                captured["state_keys"] = list(structured["state"].keys())
                captured["meta_keys"] = list(structured["meta"].keys())
                if structured["jsonld"] or structured["state"] or structured["meta"]:
                    (out_dir / "structured.json").write_text(
                        json.dumps(structured, ensure_ascii=False, indent=2),
                        encoding="utf-8")
            except Exception as e:
                print(f"[{site}/{page_name}] structured extract warn: {e}")

            # v3.1 Pillar 1: grab CSS / JS / favicon / manifest
            try:
                asset_counts = fetch_assets(full_html, url, out_dir, ua)
                captured["assets"] = asset_counts
            except Exception as e:
                print(f"[{site}/{page_name}] assets fetch warn: {e}")

            (out_dir / "full.html").write_text(full_html, encoding="utf-8")

            # Feature D: cookies after page load
            try:
                cookies = await ctx.cookies()
                captured["cookies"] = [
                    {"name": c.get("name"),
                     "value": (c.get("value", "") or "")[:40],
                     "domain": c.get("domain"),
                     "path": c.get("path"),
                     "expires": c.get("expires"),
                     "httpOnly": c.get("httpOnly"),
                     "secure": c.get("secure"),
                     "sameSite": c.get("sameSite")}
                    for c in cookies[:60]
                ]
            except Exception as e:
                print(f"[{site}/{page_name}] cookies capture warn: {e}")

            # Feature I: i18n hreflang
            try:
                locales = extract_locales(full_html)
                if len(locales) >= 2:
                    with (out_dir / "locales.json").open("w") as fh:
                        json.dump({"items": locales}, fh,
                                   ensure_ascii=False, indent=2)
                    captured["locale_count"] = len(locales)
            except Exception as e:
                print(f"[{site}/{page_name}] locales warn: {e}")

            # Feature E: try common RSS/Atom feed paths + html-declared
            try:
                html_feed_links = extract_feed_links(full_html)
                ok_f, feed_url = try_fetch_feed(url, out_dir / "feed.xml", ua,
                                                  html_links=html_feed_links)
                captured["feed_found"] = ok_f
                captured["feed_url"] = feed_url
                if html_feed_links:
                    captured["feed_html_candidates"] = html_feed_links[:10]
            except Exception as e:
                print(f"[{site}/{page_name}] feed probe warn: {e}")
                captured["feed_found"] = False
                captured["feed_url"] = None

            # Feature G: optionally expand tabs/accordions/details and recapture
            if getattr(args, "expand_tabs", False):
                try:
                    clicked = await expand_collapsed(page)
                    if clicked:
                        await page.wait_for_timeout(500)
                        try:
                            expanded_html = await page.content()
                            (out_dir / "full_expanded.html").write_text(
                                expanded_html, encoding="utf-8")
                            captured["expanded_clicks"] = clicked
                            captured["expanded_size"] = len(expanded_html)
                        except Exception:
                            pass
                except Exception as e:
                    print(f"[{site}/{page_name}] expand-tabs warn: {e}")

            # v3: if blocked, try Web Archive BEFORE writing Exa hint
            if captured.get("bot_block") and not args.no_fallback:
                # R11 fix: try curl_cffi chrome131 impersonate FIRST (drugs.com
                # case — Azure-IP Akamai accepts real Chrome TLS fingerprint).
                ok, code = try_curl_cffi(url, out_dir / "full.html")
                if ok:
                    captured["fallback_used"] = "curl_cffi_chrome131"
                    captured["curl_cffi_status"] = code
                    # Re-read body & re-detect to clear bot_block if real content
                    try:
                        cffi_html = (out_dir / "full.html").read_text(encoding="utf-8")
                        if len(cffi_html) > 5_000:
                            captured["bot_block"] = False
                            captured["bot_block_reason"] = None
                            captured["status"] = code
                            print(f"[{site}/{page_name}] curl_cffi recovered "
                                  f"{len(cffi_html)} bytes — bot_block cleared")
                    except Exception:
                        pass
                # If still blocked, try Web Archive
                if captured.get("bot_block"):
                    ok, code = try_wayback(url, out_dir / "wayback.html", ua)
                if ok:
                    captured["fallback_used"] = "wayback"
                    captured["wayback_status"] = code
                    # Re-run structured extraction on wayback HTML
                    try:
                        wb_html = (out_dir / "wayback.html").read_text(encoding="utf-8")
                        wb_struct = extract_structured(wb_html)
                        if wb_struct["jsonld"] or wb_struct["state"]:
                            (out_dir / "structured_wayback.json").write_text(
                                json.dumps(wb_struct, ensure_ascii=False, indent=2))
                    except Exception:
                        pass

            full_png = None
            try:
                await asyncio.wait_for(
                    page.screenshot(path=str(out_dir / "full.png"), full_page=True),
                    timeout=args.timeout)
                full_png = "full.png"
            except Exception:
                try:
                    await page.screenshot(path=str(out_dir / "full.png"), full_page=False)
                    full_png = "full.png"
                except Exception:
                    pass
            captured["fragments"].append({"id": "full", "html": "full.html",
                                          "png": full_png, "selector": "html"})

            seen = set()
            for selector, tag in SECTION_SELECTORS:
                try:
                    elements = await page.query_selector_all(selector)
                except Exception:
                    continue
                for idx, el in enumerate(elements[:3]):
                    try:
                        box = await el.bounding_box()
                    except Exception:
                        continue
                    if not box or box["height"] < 30 or box["width"] < 200:
                        continue
                    frag_id = f"{tag}_{idx}" if idx else tag
                    if frag_id in seen:
                        continue
                    seen.add(frag_id)
                    try:
                        inner_html = await el.evaluate("(node) => node.outerHTML")
                    except Exception:
                        continue
                    if len(inner_html) < 100:
                        continue
                    (out_dir / f"{frag_id}.html").write_text(inner_html[:200000], encoding="utf-8")
                    try:
                        await asyncio.wait_for(
                            el.screenshot(path=str(out_dir / f"{frag_id}.png")),
                            timeout=15)
                    except Exception:
                        pass
                    captured["fragments"].append({
                        "id": frag_id,
                        "html": f"{frag_id}.html",
                        "png": f"{frag_id}.png" if (out_dir / f"{frag_id}.png").exists() else None,
                        "selector": selector,
                        "bbox": box,
                    })

            for selector in CARD_HINTS:
                try:
                    elements = await page.query_selector_all(selector)
                except Exception:
                    continue
                for idx, el in enumerate(elements[:3]):
                    try:
                        if not await el.is_visible():
                            continue
                        box = await el.bounding_box()
                    except Exception:
                        continue
                    if not box or box["height"] < 50 or box["width"] < 80:
                        continue
                    safe = re.sub(r"[^a-z0-9]+", "-", selector.lower())[:32].strip("-")
                    frag_id = f"card-{safe}-{idx}"
                    if frag_id in seen:
                        continue
                    seen.add(frag_id)
                    try:
                        inner_html = await el.evaluate("(node) => node.outerHTML")
                    except Exception:
                        continue
                    (out_dir / f"{frag_id}.html").write_text(inner_html[:50000], encoding="utf-8")
                    try:
                        await asyncio.wait_for(
                            el.screenshot(path=str(out_dir / f"{frag_id}.png")),
                            timeout=10)
                    except Exception:
                        pass
                    captured["fragments"].append({
                        "id": frag_id,
                        "html": f"{frag_id}.html",
                        "png": f"{frag_id}.png" if (out_dir / f"{frag_id}.png").exists() else None,
                        "selector": selector,
                        "bbox": box,
                    })

            if (captured["bot_block"] or captured["interstitial"]) and not args.no_fallback:
                # Only write Exa hint if Wayback already failed
                if captured.get("fallback_used") != "wayback":
                    write_exa_hint(url, out_dir / "FALLBACK_NEEDED.md")
                    captured["fallback_used"] = "exa_hint"

            # Feature H: dump captured XHR/fetch calls
            # R03 nba fix: always write file (even empty) so downstream can
            # distinguish "listener ran but 0 captured" vs "tool never ran".
            try:
                with (out_dir / "xhr_calls.jsonl").open("w") as fh:
                    for call in xhr_calls[:500]:
                        fh.write(json.dumps(call, ensure_ascii=False) + "\n")
                captured["xhr_count"] = len(xhr_calls)
            except Exception as e:
                print(f"[{site}/{page_name}] xhr dump warn: {e}")

            (out_dir / "metadata.json").write_text(json.dumps(captured, indent=2))
        finally:
            await browser.close()

    flags = []
    if captured["not_found"]: flags.append("NOT_FOUND")
    if captured["bot_block"]: flags.append("BOT_BLOCK")
    if captured["interstitial"]: flags.append("INTERSTITIAL")
    if captured["http2_error"]: flags.append("HTTP2_ERROR")
    flag_str = f" [{','.join(flags)}]" if flags else ""
    real_frags = len(captured["fragments"]) - 1
    print(f"[{site}/{page_name}] captured {real_frags} fragments → {out_dir}{flag_str}")
    return captured


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site")
    ap.add_argument("page_name")
    ap.add_argument("url")
    ap.add_argument("--no-headless", dest="headless", action="store_false")
    ap.set_defaults(headless=True)
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--settle", type=int, default=2500)
    ap.add_argument("--scrolls", type=int, default=5)
    ap.add_argument("--ua", default=None)
    ap.add_argument("--no-fallback", action="store_true")
    ap.add_argument("--expand-tabs", action="store_true",
                     help="After settle, click tabs/accordions/details and save "
                          "full_expanded.html")
    args = ap.parse_args()
    asyncio.run(harvest(args))


if __name__ == "__main__":
    main()
