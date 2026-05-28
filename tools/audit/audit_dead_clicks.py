#!/usr/bin/env python3
"""Audit dead clickable elements on a running WebHarbor mirror.

Discovers all clickable elements per page (button, a, [role=button],
input[type=submit|button], [onclick]) and probes each for behavior:

  navigates   — URL changed after click
  modal       — a Bootstrap/HTML modal became visible
  dom_mutated — page content changed but URL did not (likely XHR/fetch)
  no_effect   — nothing observable changed → DEAD
  js_error    — uncaught console error fired

Output JSON report to site_specs/_audit/<slug>_clicks.json with per-page
dead_click_rate + a short textual list of the dead elements (selector +
visible text + parent tag).

Run:
  python3 tools/audit/audit_dead_clicks.py <site> [--port 43xxx] [--max-pages 10]

Fix workflow:
  1. Pure cosmetic dead `<a href="#">` / `<a href="javascript:void(0)">` →
     either remove the link OR wire it to a real route.
  2. `<button>` with no onclick and not in a `<form>` → add an `<a>` wrapper
     to make it navigate, OR register a fetch+POST handler in app.py, OR
     replace with `<span>` (it's not actually a button).
  3. `<form action="">` / `<form>` with empty action → set action to the
     current route or a real handler endpoint.
  4. Modal trigger that opens nothing → either fix `data-bs-target` attribute,
     OR add the missing `#X` modal HTML.

Don't fix `<button>` inside a `<form>` that has an action — those are valid
form submits and will show up as 'navigates' or 'dom_mutated' here.
"""
from __future__ import annotations
import argparse
import asyncio
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright


def load_yaml_pages(slug: str) -> list[str]:
    yaml_path = Path(f'/home/v-haoqiwang/webvoyager-analysis/site_specs/{slug}.yaml')
    if not yaml_path.exists():
        return ['/', '/about']
    text = yaml_path.read_text()
    urls = re.findall(r'^\s*-?\s*url(?:_pattern)?:\s*[\'"]?([^\'"\n]+)', text, re.M)
    seen = []
    for u in urls:
        u = u.strip()
        if '<' in u or u in seen:
            continue
        seen.append(u)
    return seen[:15]  # 15 pages cap — clicks are slow


async def probe_clickables(page) -> list[dict]:
    """Return [{selector_index, text, tag, href, onclick, has_form_parent, ...}]."""
    return await page.evaluate("""() => {
        const sels = ['button', 'a', '[role=button]', 'input[type=submit]',
                       'input[type=button]', '[onclick]'];
        const seen = new Set();
        const out = [];
        let idx = 0;
        sels.forEach(sel => {
            document.querySelectorAll(sel).forEach(el => {
                if (seen.has(el)) return;
                seen.add(el);
                const rect = el.getBoundingClientRect();
                if (rect.width < 4 || rect.height < 4) return;  // invisible
                if (window.getComputedStyle(el).pointerEvents === 'none') return;
                const text = (el.innerText || el.value || el.getAttribute('aria-label') || '').trim().slice(0, 60);
                const href = el.getAttribute('href') || '';
                const onclick = el.getAttribute('onclick') || '';
                const inForm = !!el.closest('form');
                const formAction = el.closest('form')?.getAttribute('action') || '';
                out.push({
                    idx: idx++,
                    tag: el.tagName,
                    text,
                    href,
                    onclick,
                    in_form: inForm,
                    form_action: formAction,
                });
            });
        });
        return out;
    }""")


async def click_and_classify(page, idx: int, base_url: str) -> str:
    """Return classification for clicking the idx-th candidate."""
    # snapshot before
    url_before = page.url
    dom_hash_before = await page.evaluate(
        '() => document.body.innerText.length + ":" + document.body.children.length')

    errors_before = []
    try:
        # click via evaluated index (we serialized order so it matches)
        await page.evaluate(f"""(idx) => {{
            const sels = ['button', 'a', '[role=button]', 'input[type=submit]',
                          'input[type=button]', '[onclick]'];
            const seen = new Set();
            const candidates = [];
            sels.forEach(sel => {{
                document.querySelectorAll(sel).forEach(el => {{
                    if (seen.has(el)) return;
                    seen.add(el);
                    const r = el.getBoundingClientRect();
                    if (r.width < 4 || r.height < 4) return;
                    if (window.getComputedStyle(el).pointerEvents === 'none') return;
                    candidates.push(el);
                }});
            }});
            const t = candidates[idx];
            if (t) t.click();
        }}""", idx)
        await page.wait_for_timeout(400)
    except Exception as e:
        # `<a href=...>` synchronously navigates inside t.click(), tearing down
        # the JS execution context before evaluate() can return → playwright
        # raises "Execution context was destroyed, most likely because of a
        # navigation". That is a *successful* navigation, not a JS runtime
        # error. Treat it as such; wait for the navigation to settle and
        # fall through to the URL-change branch below.
        msg = str(e)
        if 'Execution context was destroyed' in msg or 'navigation' in msg.lower():
            try:
                await page.wait_for_load_state('domcontentloaded', timeout=4000)
            except Exception:
                pass
        else:
            return 'js_error'

    # URL change check FIRST — avoid racing the new page's execution context
    # if click triggered nav. Without this guard, the subsequent
    # `page.evaluate` for has_modal can throw "Execution context destroyed"
    # mid-navigation and get mis-bucketed as js_error.
    if page.url != url_before:
        try:
            await page.go_back(timeout=4000, wait_until='domcontentloaded')
            await page.wait_for_timeout(150)
        except Exception:
            pass
        return 'navigates'

    # check modal opened — wrapped in try because late-arriving navigation
    # teardown can still throw here even after the URL check above
    try:
        has_modal = await page.evaluate(
            "() => Array.from(document.querySelectorAll('.modal.show, [role=dialog]:not([hidden]), .modal-open')).length > 0")
    except Exception as e:
        if 'Execution context was destroyed' in str(e) or 'navigation' in str(e).lower():
            try:
                await page.wait_for_load_state('domcontentloaded', timeout=2000)
                await page.go_back(timeout=4000, wait_until='domcontentloaded')
            except Exception:
                pass
            return 'navigates'
        return 'js_error'
    if has_modal:
        # close it for next probe (Esc)
        try:
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(150)
        except Exception:
            pass
        return 'modal'

    dom_hash_after = await page.evaluate(
        '() => document.body.innerText.length + ":" + document.body.children.length')
    if dom_hash_after != dom_hash_before:
        return 'dom_mutated'

    return 'no_effect'


# ---------- per-site sweep ---------- #

async def audit_site(slug: str, port: int, max_pages: int) -> dict:
    base = f'http://localhost:{port}'
    pages = load_yaml_pages(slug)[:max_pages]

    findings: dict = {
        'slug': slug,
        'port': port,
        'pages_checked': 0,
        'clickables_total': 0,
        'navigates': 0,
        'modal': 0,
        'dom_mutated': 0,
        'no_effect': 0,
        'js_error': 0,
        'dead_examples': [],
        'per_page': [],
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={'width': 1280, 'height': 800})

        # collect console errors per page
        for page_url in pages:
            full_url = urljoin(base, page_url)
            page = await ctx.new_page()
            console_errs: list[str] = []
            page.on('pageerror', lambda exc: console_errs.append(str(exc)[:120]))
            try:
                resp = await page.goto(full_url, timeout=20000, wait_until='domcontentloaded')
                if not resp or resp.status >= 400:
                    await page.close()
                    continue
            except Exception:
                await page.close()
                continue

            candidates = await probe_clickables(page)
            # cap per page to avoid runaway
            candidates = candidates[:40]
            page_summary = {'url': page_url, 'clickables': len(candidates),
                            'navigates': 0, 'modal': 0, 'dom_mutated': 0,
                            'no_effect': 0, 'js_error': 0}

            for c in candidates:
                # heuristic shortcut: <a href="#"> / javascript:void / no in_form & no onclick & button
                if c['tag'] == 'A' and c['href'] in ('#', '', 'javascript:void(0)', 'javascript:;'):
                    kind = 'no_effect'
                elif c['tag'] == 'BUTTON' and not c['in_form'] and not c['onclick']:
                    # try actually clicking — could be a JS handler bound at runtime
                    try:
                        kind = await click_and_classify(page, c['idx'], full_url)
                    except Exception:
                        kind = 'js_error'
                else:
                    # only sample non-trivial clickables to keep run fast
                    try:
                        kind = await click_and_classify(page, c['idx'], full_url)
                    except Exception:
                        kind = 'js_error'

                findings[kind] += 1
                page_summary[kind] += 1
                if kind == 'no_effect' and len(findings['dead_examples']) < 30:
                    findings['dead_examples'].append({
                        'page': page_url, 'tag': c['tag'],
                        'text': c['text'], 'href': c['href'][:50],
                    })

            findings['clickables_total'] += len(candidates)
            findings['per_page'].append(page_summary)
            findings['pages_checked'] += 1
            await page.close()

        await browser.close()

    if findings['clickables_total']:
        findings['dead_click_rate'] = round(
            findings['no_effect'] / findings['clickables_total'], 3)
    else:
        findings['dead_click_rate'] = 0.0
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('site')
    ap.add_argument('--port', type=int, default=None)
    ap.add_argument('--max-pages', type=int, default=10)
    args = ap.parse_args()

    if not args.port:
        try:
            import urllib.request as ur
            health = json.loads(ur.urlopen('http://localhost:8311/health', timeout=3).read())
            internal = health['sites'][args.site]['port']
            args.port = internal + 3000
        except Exception:
            print(f'ERR: cannot resolve port for {args.site}; pass --port')
            sys.exit(2)

    findings = asyncio.run(audit_site(args.site, args.port, args.max_pages))

    out = Path(f'/home/v-haoqiwang/webvoyager-analysis/site_specs/_audit/{args.site}_clicks.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(findings, indent=2))

    print(f"\n{args.site:20s}  pages={findings['pages_checked']:3d}  "
          f"clickables={findings['clickables_total']:4d}  "
          f"nav={findings['navigates']:3d}  modal={findings['modal']:3d}  "
          f"mut={findings['dom_mutated']:3d}  DEAD={findings['no_effect']:3d}  "
          f"err={findings['js_error']:3d}  "
          f"dead_rate={findings['dead_click_rate']*100:.1f}%")


if __name__ == '__main__':
    main()
