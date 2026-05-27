# R10 Final Polish Plan

## Status
- Baseline: products 51935 / tasks 4811
- Targets: products 56000+ / tasks 5500+
- Must: byte-id reset (md5 stable across rebuilds)

## Quality polish (Phase A)
- [x] OG image: `/static/images/homepage/og-cover.jpg` 404 → copy a real homepage image
- [x] Favicon: `/favicon.ico` 404 → inline-SVG fallback or PNG
- [x] Opensearch: `/opensearch.xml` 404 → add descriptor
- [x] Alias routes for common business-line URLs:
  - `/freetime` -> `/kids/freetime` (301)
  - `/amazon-live` -> `/live-shopping` (301)
  - `/amazon-household` -> `/household` (301)
  - `/amazon-outlet` -> `/outlet` (301)
  - `/business` -> `/amazon-business` (301)
  - `/today-deals` -> `/todays-deals` (301)
  - `/c/pharmacy`, `/c/auto`, `/c/renewed`, `/c/outlet`, `/c/freetime` aliases
- [x] Form validation feedback on `address_form.html` + `payment_form.html`
  (currently no `{% for e in form.X.errors %}` blocks at all)

## Products (Phase B) — seed_r10.py
- Replay every prior template pool with R10_SUFFIXES (~38 fresh codenames, no
  overlap with R2-R9)
- R10_NEW_TEMPLATES (cross-category bundles):
  - Pharmacy+Pantry+SnS combo (HSA-eligible care kits)
  - Auto VIN-fit bundles (oil-change + filter + wiper combos)
  - Renewed-grade bundles (refurb laptop+sleeve+warranty)
  - Holiday/Seasonal long-tail (Spring/Summer/Fall/Winter)
  - Made-by-Amazon basics (private-label expansion)
- Target: 56000+ (idempotent floor 55500)

## Tasks (Phase C) — generate_r10_tasks.py
- 700+ cross-business multi-step tasks
- Patterns:
  - Pharmacy + Pantry + S&S "one-stop care kit" flow
  - Auto VIN-verify + browse + add-to-cart
  - Renewed-grade verify + return policy + add-to-cart
  - Household share + Subscribe-Save + Auto-Reorder
  - FreeTime band + Kids+ + parental approval
  - Live shopping + carousel deals + countdown

## Byte-identity (Phase D)
- Drop instance/amazon_store.db
- Rebuild seed twice via `python3 -c "from app import app"`
- md5 must match

## Constraints
- ONLY touch sites/amazon/
- No commit
- No 100MB+ uncached file outside instance_seed/ (already gitignored)
- Deterministic only — no datetime.now / random without seed
