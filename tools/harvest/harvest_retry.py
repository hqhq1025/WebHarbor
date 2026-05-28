#!/usr/bin/env python3
"""harvest_retry.py — retry harvest with anti-bot mitigations.

Differences from harvest.py:
 - Real Chrome UA (latest desktop) instead of generic 'Chrome/120'
 - sec-ch-ua headers, Accept-Language
 - Disable navigator.webdriver
 - Longer wait_for_load_state
 - networkidle wait_until

Usage: same args as harvest.py.
"""
import argparse, asyncio, json, re, sys
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()

SECTION_SELECTORS = [
    ("header, [class*='header' i][class*='global' i], [class*='site-header' i], [class*='top-bar' i]", "page-header"),
    ("nav[aria-label], nav[role='navigation'], nav, [class*='primary-nav' i], [class*='main-nav' i]", "nav"),
    ("main, [role='main'], [id*='main-content' i]", "main"),
    ("[class*='hero' i]:not([class*='hero-image-only' i])", "hero"),
    ("[class*='sidebar' i], aside", "sidebar"),
    ("[role='banner']", "banner-role"),
    ("[role='contentinfo']", "footer-role"),
    ("footer, [class*='footer' i][class*='global' i], [class*='site-footer' i]", "footer"),
]
CARD_HINTS = [
    "[class*='card' i]:not([class*='card-deck' i])",
    "[class*='product-tile' i], [class*='product-card' i]",
    "[class*='listing' i]:not([class*='listing-page' i])",
    "[data-testid*='card' i]",
    "article",
]
COOKIE_KILL = [
    "#onetrust-accept-btn-handler",
    "button[id*='accept' i]",
    "button[class*='accept-cookies' i]",
    "button[aria-label*='accept' i]",
    "[data-testid*='accept-cookies' i]",
    "button[id*='sp-cc-accept']",  # amazon
]

REAL_CHROME_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

async def harvest(site, page_name, url, headless=True):
    out_dir = ROOT / site / page_name
    out_dir.mkdir(parents=True, exist_ok=True)
    captured = {"site": site, "page_name": page_name, "url": url,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "fragments": [], "status": None, "title": None,
                "harvester": "retry-v2"}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        ctx = await browser.new_context(
            user_agent=REAL_CHROME_UA,
            viewport={"width": 1440, "height": 900},
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Linux"',
            },
        )
        # Mask webdriver
        await ctx.add_init_script(
            """Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
               Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
               Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});"""
        )
        page = await ctx.new_page()
        try:
            try:
                response = await page.goto(url, wait_until="networkidle", timeout=45000)
            except Exception:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            captured["status"] = response.status if response else None
            await page.wait_for_timeout(4000)

            for sel in COOKIE_KILL:
                try:
                    btn = await page.query_selector(sel)
                    if btn and await btn.is_visible():
                        await btn.click()
                        await page.wait_for_timeout(700)
                        break
                except Exception:
                    pass

            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1500)
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(900)
            except Exception:
                pass

            captured["title"] = await page.title()
            full_html = await page.content()
            (out_dir / "full.html").write_text(full_html, encoding="utf-8")
            await page.screenshot(path=str(out_dir / "full.png"), full_page=True)
            captured["fragments"].append({"id": "full", "html": "full.html", "png": "full.png", "selector": "html"})

            seen = set()
            for selector, tag in SECTION_SELECTORS:
                try:
                    els = await page.query_selector_all(selector)
                except Exception:
                    continue
                for idx, el in enumerate(els[:3]):
                    box = await el.bounding_box()
                    if not box or box["height"] < 30 or box["width"] < 200:
                        continue
                    fid = f"{tag}_{idx}" if idx else tag
                    if fid in seen:
                        continue
                    seen.add(fid)
                    h = await el.evaluate("(n)=>n.outerHTML")
                    if len(h) < 100:
                        continue
                    (out_dir / f"{fid}.html").write_text(h[:200000], encoding="utf-8")
                    try:
                        await el.screenshot(path=str(out_dir / f"{fid}.png"))
                    except Exception:
                        pass
                    captured["fragments"].append({"id": fid, "html": f"{fid}.html",
                                                  "png": f"{fid}.png" if (out_dir/f"{fid}.png").exists() else None,
                                                  "selector": selector, "bbox": box})
            for selector in CARD_HINTS:
                try:
                    els = await page.query_selector_all(selector)
                except Exception:
                    continue
                for idx, el in enumerate(els[:3]):
                    if not await el.is_visible():
                        continue
                    box = await el.bounding_box()
                    if not box or box["height"] < 50 or box["width"] < 80:
                        continue
                    safe = re.sub(r"[^a-z0-9]+", "-", selector.lower())[:32].strip("-")
                    fid = f"card-{safe}-{idx}"
                    if fid in seen:
                        continue
                    seen.add(fid)
                    h = await el.evaluate("(n)=>n.outerHTML")
                    (out_dir / f"{fid}.html").write_text(h[:50000], encoding="utf-8")
                    try:
                        await el.screenshot(path=str(out_dir / f"{fid}.png"))
                    except Exception:
                        pass
                    captured["fragments"].append({"id": fid, "html": f"{fid}.html",
                                                  "png": f"{fid}.png" if (out_dir/f"{fid}.png").exists() else None,
                                                  "selector": selector, "bbox": box})
            (out_dir / "metadata.json").write_text(json.dumps(captured, indent=2), encoding="utf-8")
        finally:
            await browser.close()
    print(f"[{site}/{page_name}] retry captured {len(captured['fragments'])} fragments")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site"); ap.add_argument("page_name"); ap.add_argument("url")
    ap.add_argument("--no-headless", action="store_true")
    a = ap.parse_args()
    asyncio.run(harvest(a.site, a.page_name, a.url, headless=not a.no_headless))

if __name__ == "__main__":
    main()
