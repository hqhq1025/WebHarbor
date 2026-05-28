# tools/audit/ — runtime UI-quality audits

Per-site Playwright crawlers that quantify two failure modes the existing
verify-site-gui (Phase 7) doesn't catch by walking yaml:

| Tool | Detects | Fix Phase |
|---|---|---|
| `audit_placeholder_images.py` | `<img>` + inline SVG-initials with placeholder / broken / suspect classification | scrape-real-images (5b) |
| `audit_dead_clicks.py` | `<button>` / `<a>` / `[onclick]` that fire no observable effect (no nav, no modal, no DOM mutation) | evolve-env (3) — add handler or remove element |

Both tools share these conventions:
- Read yaml pages from `site_specs/<slug>.yaml` (cap 15-25 pages — audit not bulk).
- Look up site's external port via control-plane `:8311/health` (internal `+3000`).
- Output JSON report to `site_specs/_audit/<slug>_{images,clicks}.json`.
- Print 1-line summary so batch runs aggregate nicely.

## When to use

- After clone-website / scrape-real-images pass to verify image coverage isn't
  still 30%+ placeholder.
- After deepen / R10 polish round to verify newly-added buttons aren't decorative.
- Before opening PR or bumping `.assets-revision` — same trust gate as verify-site-gui.
- When user reports "this site has too many gray boxes" or "I can't actually click
  these buttons".

## Quick start

```bash
# Single site
python3 tools/audit/audit_placeholder_images.py imdb
python3 tools/audit/audit_dead_clicks.py imdb

# Batch all
for s in $(curl -s http://localhost:8311/health | jq -r '.sites|keys[]'); do
  python3 tools/audit/audit_placeholder_images.py "$s" || true
  python3 tools/audit/audit_dead_clicks.py "$s" || true
done | tee /tmp/audit-summary.txt
```

Then aggregate:

```bash
# Worst placeholder rate
ls site_specs/_audit/*_images.json | xargs -I{} jq -r '"\(.slug)\t\(.placeholder_rate)\t\(.placeholder)/\(.images_total)"' {} | sort -k2 -nr | head -10

# Worst dead-click rate
ls site_specs/_audit/*_clicks.json | xargs -I{} jq -r '"\(.slug)\t\(.dead_click_rate)\t\(.no_effect)/\(.clickables_total)"' {} | sort -k2 -nr | head -10
```

## Classification — placeholder images

| Class | How detected |
|---|---|
| `real` | host in known-good CDN list (m.media-amazon, image.tmdb, upload.wikimedia, github avatars, etc.) |
| `placeholder` | URL matches `/static/images/placeholder*`, `/static/avatars/default*`, ends `placeholder.{png,svg,jpg}`, OR inline `<svg><text>XX</text></svg>` initials, OR `data:` URL <200 bytes |
| `broken` | HEAD returns ≥400 status, OR content-length <200 bytes (transparent 1x1 gif) |
| `suspect` | content-length 200–2048 bytes (likely an icon misused as a hero image) |

`placeholder_rate = (placeholder + broken) / total`. Sites with >30% rate get
priority on the next scrape-real-images Phase 5b pass.

## Classification — dead clicks

| Class | How detected |
|---|---|
| `navigates` | `page.url` changed after click |
| `modal` | `.modal.show / [role=dialog]:not([hidden])` became visible |
| `dom_mutated` | URL unchanged but body innerText.length / child count changed |
| `no_effect` | None of the above happened → DEAD |
| `js_error` | Uncaught `pageerror` fired during click |

Also short-circuits the common dead patterns without actually clicking:
- `<a href="#">` / `<a href="javascript:void(0)">` / `<a href="javascript:;">` →
  immediately classified `no_effect`.

`dead_click_rate = no_effect / total clickables`. Sites with >20% rate need
either handler wiring (evolve-env) or element removal.

## Common fix paths

After audit JSON is written:

### Placeholder images

1. Look at `top_placeholders` map in the report. If the top src is
   `static/images/placeholder.png` repeated 50 times across 5 pages → the
   row's `image_url` column is NULL for all those entities → dispatch
   scrape-real-images Phase 5b with that column on the priority list.
2. If the top src is an inline SVG initials pattern → same as above
   (entity row has NULL image_url and template's `{% if not row.image %}`
   branch is generating the SVG).
3. If `top_broken` lists external CDN URLs → those URLs went stale upstream
   (e.g. tmdb.org rotated their CDN host). Re-scrape from Wikipedia.

### Dead clicks

1. Look at `dead_examples` list. For each:
   - `text="Add to cart" tag=BUTTON` and not in a form → add a `<form>` wrapper
     with the right `action="/cart/add"` POST handler.
   - `text="See more" tag=A href="#"` → either replace `href="#"` with the
     real route, OR convert to `<button>` styling and add a JS scroll handler.
   - `text="Like" tag=BUTTON` (no form) → typically a fetch+POST; verify the
     fetch handler is registered in app.py (often missing → gotcha #49).
2. Re-run audit after fix; `no_effect` count should drop.
3. Some `no_effect` are legitimate decorative buttons (e.g. carousel chrome
   without auto-rotate). For those, add `aria-disabled="true"` or remove.

## Subagent dispatch rules

- **Parallel safe across sites** — each audit hits one running mirror.
- **Single playwright instance per agent** — concurrent Chromium contexts in
  one process leak memory fast.
- **Max 6 sites per agent** for audit (faster than verify because no fix step).
- **Cap pages per site**: defaults are 25 (images) and 15 (clicks). Don't go
  higher; both tools click-walk and slow ~1s/element.

## Limitations

- Playwright only — JS-disabled content not audited.
- HEAD probe assumes CDN supports HEAD (most do); if HEAD 405, the image gets
  `status=None` and we fall back to host-list classification.
- Modal detection uses Bootstrap selectors (`.modal.show, [role=dialog]`);
  custom modal systems may miss. Add to `probe_clickables` JS if a mirror uses
  another pattern.
- Dead-click detection clicks each element ONCE — chained interactions
  (button → wait → button) aren't modeled.
