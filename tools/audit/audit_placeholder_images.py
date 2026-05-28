#!/usr/bin/env python3
"""Audit placeholder / broken images on a running WebHarbor mirror.

Crawls all yaml-declared pages on a site via Playwright, collects every <img>
src + inline SVG-initials, classifies each as:

  real        — non-placeholder CDN (m.media-amazon.com, image.tmdb.org,
                upload.wikimedia.org, github avatar CDN, ...)
  placeholder — static placeholder asset (/static/images/placeholder*.png,
                /static/images/default*.png, /static/avatars/default*.svg,
                inline <svg> with <text>initials</text>, 1x1 gif)
  broken      — HEAD returns 4xx/5xx, or content-length < 200 bytes (likely
                broken transparent gif)
  suspect     — content-length 200-2048 bytes (possibly an icon misused
                as a hero image)

Outputs JSON report to site_specs/_audit/<slug>_images.json with per-page +
per-column counts. Columns are inferred from URL path: image src that
contains a slug found in instance/<site>.db lets us map back to the row.

Run:
  python3 tools/audit/audit_placeholder_images.py <site> [--port 43xxx]

Fix workflow:
  1. Look at top columns with placeholder_rate > 30% → those are scrape-real-images
     Phase 5b targets.
  2. Broken (4xx) images → either /static asset missing OR upstream CDN URL
     stale → re-scrape from Wikipedia (Phase 5b).
  3. Suspect (200-2048 byte) → check if the actual file is a 1x1 transparent
     gif used by lazy-load JS; if so, the LCP image is missing.
"""
from __future__ import annotations
import argparse
import asyncio
import json
import re
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright

# ---------- classification ---------- #

REAL_CDN_HOSTS = re.compile(
    r'^(m\.media-amazon\.com|image\.tmdb\.org|upload\.wikimedia\.org|'
    r'cdn\.cnn\.com|images\.unsplash\.com|i\.ytimg\.com|i\.scdn\.co|'
    r'static-cdn\.jtvnw\.net|avatars\.githubusercontent\.com|'
    r'pbs\.twimg\.com|substackcdn\.com|ichef\.bbci\.co\.uk|'
    r'media\.cnn\.com|cdn\.openai\.com|huggingface\.co|'
    r'cf\.geekdo-images\.com|images\.fandom\.com|static\.wikia\.nocookie\.net|'
    r'(content-images|img2)\.carmax\.com|d3v0sicl0wapov\.cloudfront\.net|'
    r'images\.ctfassets\.net|nba-cdn\.2k\.com|cdn\.nba\.com|'
    r'(www\.)?recreation\.gov|images\.apple\.com)', re.I)

PLACEHOLDER_PATH_PATTERNS = [
    r'/static/images?/placeholder',
    r'/static/images?/default[-_]',
    r'/static/avatars?/default',
    r'/static/icons?/missing',
    r'/static/img/no[-_]image',
    r'placeholder\.(png|svg|jpg)$',
    r'default[-_]avatar',
    r'fallback[-_]image',
]
PLACEHOLDER_PATH_RE = re.compile('|'.join(PLACEHOLDER_PATH_PATTERNS), re.I)

INLINE_SVG_INITIALS_RE = re.compile(
    r'<svg[^>]*>.*?<text[^>]*>([A-Z]{1,3})</text>.*?</svg>', re.I | re.S)

# SVG class markers that indicate a procedural illustration (NOT an initials
# placeholder). When the audit's playwright evaluator finds an <svg> with
# <text> inside, it normally tags it as a placeholder ("inline-svg-text:X").
# But some sites legitimately render procedural artwork using <text> as a
# label (e.g. drugs_com's pill renderer embosses the imprint code on the
# rendered pill). Whitelist by class so we don't false-positive these.
#
# Each entry is a substring that must appear in the SVG's class attribute.
ILLUSTRATION_SVG_CLASS_MARKERS = (
    'pill-svg',                # drugs_com — procedural pill renderer with
                               # 3D gradients, shadows, embossed imprint.
)


def classify_src(src: str, content_length: int | None, status: int | None) -> str:
    """Return one of: real / placeholder / broken / suspect."""
    if src.startswith('data:'):
        # data: URLs are typically 1x1 transparent placeholders for lazy-load
        if 'svg' in src[:200] and 'text' in src[:500]:
            return 'placeholder'  # SVG initials inline
        if len(src) < 200:
            return 'placeholder'  # tiny base64 1x1
        return 'real'  # large embedded data: image is unusual but real
    if status and (status >= 400):
        return 'broken'
    if PLACEHOLDER_PATH_RE.search(src):
        return 'placeholder'
    if content_length is not None:
        if content_length < 200:
            return 'broken'
        if content_length < 2048:
            return 'suspect'
    host = urlparse(src).netloc
    if REAL_CDN_HOSTS.match(host):
        return 'real'
    # Unknown host — check if it's a host we recognize as the local mirror
    if host.startswith('localhost') or host.startswith('127.0.0.1') or host.startswith('20.225.'):
        # local /static path — already handled by PLACEHOLDER_PATH_RE, else real
        return 'real'
    # External unknown host — treat as real unless tiny
    return 'real'


# ---------- HEAD probe ---------- #

def head_probe(url: str, timeout: int = 4) -> tuple[int | None, int | None]:
    """Return (status, content_length). None on connect error."""
    try:
        req = urllib.request.Request(url, method='HEAD',
                                      headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            cl = r.headers.get('Content-Length')
            return r.status, int(cl) if cl else None
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return None, None


# ---------- yaml loader ---------- #

def load_yaml_pages(slug: str) -> list[str]:
    """Load page URLs from site_specs/<slug>.yaml; minimal parse."""
    yaml_path = Path(f'/home/v-haoqiwang/webvoyager-analysis/site_specs/{slug}.yaml')
    if not yaml_path.exists():
        # fall back to common entry pages
        return ['/', '/about']
    text = yaml_path.read_text()
    # naive: pages: list of `- url: /foo` lines
    urls = re.findall(r'^\s*-?\s*url(?:_pattern)?:\s*[\'"]?([^\'"\n]+)', text, re.M)
    # dedupe + strip placeholder routes
    seen = []
    for u in urls:
        if u not in seen:
            seen.append(u.strip())
    return seen[:25]  # cap at 25 pages — audit not bulk


# ---------- per-site sweep ---------- #

async def audit_site(slug: str, port: int) -> dict:
    base = f'http://localhost:{port}'
    pages = load_yaml_pages(slug)
    if not pages:
        pages = ['/']

    findings: dict = {
        'slug': slug,
        'port': port,
        'pages_checked': 0,
        'images_total': 0,
        'real': 0,
        'placeholder': 0,
        'broken': 0,
        'suspect': 0,
        'top_placeholders': defaultdict(int),  # src → count
        'top_broken': defaultdict(int),
        'per_page': [],
    }

    seen_srcs: dict[str, tuple[int | None, int | None]] = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={'width': 1280, 'height': 800})

        for page_url in pages:
            full_url = urljoin(base, page_url)
            if '<' in full_url:  # unresolved placeholder
                continue
            page = await ctx.new_page()
            try:
                resp = await page.goto(full_url, timeout=20000, wait_until='domcontentloaded')
                if not resp or resp.status >= 400:
                    await page.close()
                    continue
            except Exception:
                await page.close()
                continue

            srcs = await page.evaluate("""() => {
                const imgs = Array.from(document.querySelectorAll('img'))
                    .map(i => i.currentSrc || i.src).filter(s => s);
                const svgs = Array.from(document.querySelectorAll('svg'))
                    .filter(s => s.querySelector('text'))
                    .map(s => {
                        const cls = s.getAttribute('class') || '';
                        const txt = s.querySelector('text')?.textContent || '';
                        // Encode class so classify_src can whitelist
                        // procedural illustration SVGs.
                        return 'inline-svg-text:' + cls + '|' + txt;
                    });
                return [...imgs, ...svgs];
            }""")

            page_summary = {'url': page_url, 'images': len(srcs),
                            'real': 0, 'placeholder': 0, 'broken': 0, 'suspect': 0}

            for src in srcs:
                findings['images_total'] += 1
                if src.startswith('inline-svg-text:'):
                    # Format: inline-svg-text:<class>|<text>
                    payload = src[len('inline-svg-text:'):]
                    svg_class, _, svg_text = payload.partition('|')
                    if any(m in svg_class for m in ILLUSTRATION_SVG_CLASS_MARKERS):
                        # Procedural illustration (e.g. drugs_com pill renderer),
                        # not an initials placeholder.
                        kind = 'real'
                    else:
                        kind = 'placeholder'
                        findings['top_placeholders'][('inline-svg-text:' + svg_text)[:80]] += 1
                else:
                    if src not in seen_srcs:
                        seen_srcs[src] = head_probe(src if src.startswith('http') else urljoin(base, src))
                    status, cl = seen_srcs[src]
                    kind = classify_src(src, cl, status)
                    if kind == 'placeholder':
                        findings['top_placeholders'][src[:120]] += 1
                    elif kind == 'broken':
                        findings['top_broken'][src[:120]] += 1
                findings[kind] += 1
                page_summary[kind] += 1

            findings['per_page'].append(page_summary)
            findings['pages_checked'] += 1
            await page.close()

        await browser.close()

    findings['top_placeholders'] = dict(sorted(findings['top_placeholders'].items(),
                                                 key=lambda kv: -kv[1])[:10])
    findings['top_broken'] = dict(sorted(findings['top_broken'].items(),
                                          key=lambda kv: -kv[1])[:10])
    if findings['images_total']:
        findings['placeholder_rate'] = round(
            (findings['placeholder'] + findings['broken']) / findings['images_total'], 3)
    else:
        findings['placeholder_rate'] = 0.0
    return findings


# ---------- main ---------- #

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('site', help='Site slug (e.g. imdb)')
    ap.add_argument('--port', type=int, default=None)
    args = ap.parse_args()

    # Default external port = internal port + 3000; lookup if not given
    if not args.port:
        try:
            import urllib.request as ur
            health = json.loads(ur.urlopen('http://localhost:8311/health', timeout=3).read())
            internal = health['sites'][args.site]['port']
            args.port = internal + 3000
        except Exception:
            print(f'ERR: cannot resolve port for {args.site}; pass --port')
            sys.exit(2)

    findings = asyncio.run(audit_site(args.site, args.port))

    out = Path(f'/home/v-haoqiwang/webvoyager-analysis/site_specs/_audit/{args.site}_images.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(findings, indent=2))

    print(f"\n{args.site:20s}  pages={findings['pages_checked']:3d}  "
          f"images={findings['images_total']:4d}  real={findings['real']:4d}  "
          f"placeholder={findings['placeholder']:4d}  broken={findings['broken']:4d}  "
          f"suspect={findings['suspect']:4d}  "
          f"rate={findings['placeholder_rate']*100:.1f}%")


if __name__ == '__main__':
    main()
