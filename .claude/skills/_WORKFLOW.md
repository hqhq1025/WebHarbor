# WebHarbor Pipeline — Master Workflow

11 skills + 26 harvest tools / 49 gotchas / 12 phases. **Read this first** before starting any new mirror or polish pass.

## 一图流

```
Phase 0  harvest-real-components ─ 26 tools / 15 dims
            ↓
Phase 1  clone-website ─ Flask scaffold (USES harvest fragments)
            ↓
Phase 2  design-tasks ─ benchmark task spec
            ↓
Phase 3  evolve-env ─ implement to support tasks
            ↓
Phase 4  harden-env ─ 49 gotchas + difficulty
            ↓
Phase 5  seed-database ─ idempotent + asset workflow
   └─ Phase 5b  scrape-real-images ─ Wikipedia FIRST / Tavily LAST
   └─ Phase 5c  image diversity gate (top-dup ≤ 5%)
            ↓
Phase 6  document-site-gui ─ v3 yaml + md, with v2 surface taxonomy
            ↓
Phase 7  verify-site-gui ─ 9 categories of bug hunt
            ↓
Phase 8  perf-optimize ─ 10 categories of fix (median TTFB <50ms)
            ↓
Phase 9  ship (HF repack + .assets-revision + docker prod)
```

## Phase-by-phase

### Phase 0 — `harvest-real-components` (跑全 14 维度 = 真站快照)

**Triggers**: 任何新 site / 重大视觉升级 / "现在 mirror 看着不像" feedback

**Tools** (under `~/repos/WebHarbor/tools/harvest/` — 26 scripts):

| Group | Scripts |
|---|---|
| Capture (3) | `harvest.py` `harvest_spider.py` `harvest_retry.py` |
| Dimension extractors (15) | `extract_sitemap.py` `extract_forms.py` `extract_facets.py` `extract_image_urls.py` `extract_sprites.py` `extract_audio_urls.py` `extract_video_urls.py` `extract_icons.py` `extract_animations.py` `extract_code_blocks.py` `extract_metadata_extruct.py` `extract_api_endpoints.py` `extract_server_state.py` `extract_websockets.py` `extract_nav_graph.py` |
| Reprocessors (2) | `reprocess_structured.py` `content_extract.py` (trafilatura) |
| Helpers (6) | `infer_cdn_pattern.py` `index_site.py` `index_pool.py` `search_local.py` (SearXNG) `download_samples.py` `audit_dimensions.py` |

**Outputs to**: `~/webvoyager-analysis/real_components/snapshots/<site>/<page>/`
- `full.html` + `full.png` + `nav.html` + `page-header.html` + assets/
- `_image_urls.jsonl` `_buttons.jsonl` `_forms.jsonl` `_facets.jsonl` `_nav_graph.json` `_footer_links.jsonl` `_icons.jsonl` `_sprites.json` `_audio_urls.jsonl` `_video_urls.jsonl` `_animations.jsonl` `_code_blocks.jsonl`
- `_extruct_index.json` (microdata/RDFa/JSON-LD/microformat/DublinCore — 124k records across 96 sites)
- `_api_endpoints.jsonl` `_server_state.json` (SPA `__NEXT_DATA__` / Apollo / etc)
- `_sitemap_urls.jsonl` `_robots.txt`
- `structured.json` `article.json` `breadcrumbs.json` `feed.xml` `content.md`

**Skills file**: `harvest-real-components/SKILL.md`

---

### Phase 1 — `clone-website`

Now uses Phase 0's harvest data:
- Real card markup ← harvest `full.html` fragments
- Real nav structure ← `_nav_graph.json`
- Real footer columns ← `_footer_links.jsonl`
- Real SVG sprites ← `sprites/` dir
- Real favicon ← `_icons.jsonl`
- Real CSS variables ← harvest `assets/*.css`

**Skill file**: `clone-website/SKILL.md` (+ 真扒上游 mandatory ≥50%)

---

### Phase 2 — `design-tasks`

Now uses harvest sitemap + facets:
- Real URL slug patterns ← `_sitemap_urls.jsonl`
- Real filter options ← `_facets.jsonl`
- Real button labels for task wording ← `_buttons.jsonl`

WebVoyager schema, ≤5 task per 5-token prefix, GUI-only.

---

### Phase 3 — `evolve-env`

Implement routes/handlers/templates needed to support Phase 2 tasks.

---

### Phase 4 — `harden-env` (49 gotchas + difficulty)

See `harden-env/gotchas.md` — 49 gotchas accumulated through 2026-05 sessions.

Key clusters:
- §1-12 Seed/byte-id (bcrypt salt, index order, datetime.utcnow, schema drift)
- §13-23 Asset/scrape (apt-pin, HF, Wikipedia, RSS, throttle)
- §24-28 GUI-only task quality (API trap, in-memory dict, template share, entry break, dup)
- §29-33 Container/runtime (test-client seed copy, image util, race, circular import, hub URL inventory)
- §34-36 Image (utilization, POST family, MarketingPage schema)
- §37-43 Pattern (subagent stall, image_path remap, pbkdf2, SVG fallback, R8 keyboard, image dup, h-overflow)
- §44-49 Latest (perf 4 categories + Werkzeug, docker port loss, instance_seed drift, missing CSS, neg-margin, parallel-fix regression)

---

### Phase 5 — `seed-database` (+ scrape-real-images + image diversity gate)

#### 5a. Idempotent seed (`seed-database`)
- byte-id reset invariant
- 4 benchmark users + PINNED bcrypt
- HF asset workflow

#### 5b. Real images (`scrape-real-images`)

**Source priority (NEW 2026-05-27)**:
1. Wikipedia REST `/page/summary/<Title>` → `.thumbnail.source` (覆盖 60-80% 真实 entity)
2. Wikimedia Commons `api.php?list=allimages`
3. Domain CDNs (GitHub avatars / YouTube thumb / Amazon CDN / Open Library / TED CDN)
4. RSS feed thumbnails
5. Harvested `_image_urls.jsonl` (Phase 0 output — real upstream URLs)
6. Tavily as LAST RESORT (月配额 1000 query 省着用)
7. SVG initials fallback when Wikipedia miss

Gotchas:
- `upload.wikimedia.org` 403 on UA containing "WebHarbor" → use Mozilla UA
- Prefer `thumbnail.source` over `original.source` (CDN cached, 429 tolerant)
- pageimage miss on abstract topics → fallback `prop=images`
- per-worker `requests.Session()` for parallel
- 8KB threshold filter
- Commit DB + write bytes every entity (not at end) — subagents stall

#### 5c. Diversity gate

```python
def assert_image_diversity(db_path, table, column, threshold=0.05):
    top_n = collections.Counter(rows).most_common(1)[0][1]
    assert top_n / len(rows) < threshold
```

调用在每个 seed_<feature>() 结尾。CI 也跑。

---

### Phase 6 — `document-site-gui`

v3 schema 双件: `site_docs/<slug>.md` (人读) + `site_specs/<slug>.yaml` (canonical structured)

**v2 surface taxonomy** (2026-05-27):
- 4 surface kinds: Page / Modal / In-place View / State
- 6 transitions: page_navigate / state_change / view_change / open_modal / close_modal / submit_modal

每页 8 子块: 页面构成 / 信息展示 / GUI 元素 / 状态变体 / URL 参数 / 错误边缘 / 隐式副作用 / 跳转出口

GUI-only 硬约束: 键盘 hotkey 不进 atomic skills。

---

### Phase 7 — `verify-site-gui` (9 bug categories)

Playwright real Chromium walks yaml.pages. 9 categories:

1. **真 404** — yaml 承诺路由 app 没实现
2. **真 5xx** — handler crash
3. **缺 nav / a11y landmark**
4. **modal trigger 缺失**
5. **横向 overflow** (gotcha #43)
6. **元素 bbox 重叠** (collision detection)
7. **feature silent-fail** (gotcha #49 — silent POST, login asymmetry, fetch no-catch)
8. **缺失 static 资源** (CSS/JS/icon)
9. **placeholder text** ("WebHarbor benchmark" 等 agent-instruction 漏出)

7 种假阳性 + DB-introspection slug map + PER_SLUG overrides 应 obey.

---

### Phase 8 — `perf-optimize` (10 categories)

5 原始 + 5 新（F-J）:

| # | 类 | 实际案例 |
|---|---|---|
| A | Composite SQL index | google_map 596ms → 4ms (150×) |
| B | Context-processor cache | google_map context proc 60ms → 0.01ms |
| C | List page LIMIT + pagination | coursera /search 48.5MB → 75KB (645×) |
| D | N+1 → eager loading | github 99ms → 2.5ms |
| E | Cache-Control + lazy-load + body | 全 36 站 |
| F | Route-level HTML cache | apple /shop 176ms → 4ms (44×) |
| G | SQLite LIKE → range comparison | cambridge 74ms → 5ms (15×) |
| H | db.create_all() 不加 new index 陷阱 | arxiv (30 min lesson) |
| I | inject_globals cache (max/count) | arxiv 100ms → 0.01ms |
| J | baseline median not max | 29/32 sites OK after re-measure |

**Werkzeug trap**: `headers.setdefault('Cache-Control', ...)` is no-op for static. Must direct assignment.

---

### Phase 9 — Ship

- HF dataset repack (`scripts/extract_assets.sh /tmp <site> --push`) + bump `.assets-revision`
- Docker recreate (NOT restart — port mapping loss per gotcha #45)
- NSG verify

## Subagent dispatching rules

Based on 2026-05 session learnings:

1. **Max 3 sites per agent** for deep work (deepen / docs / perf). Beyond that stalls common.
2. **Single-site for delicate work** (DB schema change / breaking API change).
3. **Parallel safe across sites**: image scrape / static-only edits / template updates.
4. **Parallel UNSAFE same-site**: 同站多 fixer 写 app.py + template → race + feature regression (gotcha #49).
5. **Image scrape agent**: 周期 `db.session.commit()` + `Path.write_bytes()` 每 entity，don't batch — subagent stall 概率高。
6. **Verify after fix**: 每 subagent 完成前必须 playwright smoke test 主交互。

## Concurrency safety

- per-site git rebase: 多 agent 同时 push 同 fork 是 OK 的（git pull --rebase 自动 merge），但同 file 同段同时改 → race。
- docker cp + control plane `/restart/<site>`：每站独立，无 race。
- `/reset/<site>` 重 worker → cache 自动清。

## Recent session impact (2026-05-26 ~ 2026-05-28)

- 36 docker sites running (1 corrupted: eventbrite)
- ~100 commits pushed to hqhq1025/WebHarbor:main
- 8 perf wins: 12-150× TTFB / 645× size on coursera /search
- 26 image dup columns / 5 batches / 1500+ entities / **0 Tavily call** (all Wikipedia/Wikimedia/RSS/CDN)
- 13 + 6 in-flight harvest-based upgrades (real CDN images / real nav/footer/buttons / real JSON-LD entity / real favicon / real SVG sprite / real text copy / real form options / real audio-video URL / real SPA state)
- 49 gotchas accumulated
- 11 skills + 26 harvest tools

## Skill index (alphabetical)

| Skill | Phase | Use when |
|---|---|---|
| clone-website | 1 | Starting new mirror |
| design-tasks | 2 | Writing tasks |
| document-site-gui | 6 | After deepen, before verify |
| evolve-env | 3 | Implementing routes |
| harden-env | 4 | All 49 gotchas reference |
| harvest-real-components | 0 | Before any new site |
| perf-optimize | 8 | Sites work but slow |
| review-env | (audit) | Pre-PR checklist |
| scrape-real-images | 5b | Replace placeholder images |
| seed-database | 5a | Finalize seed + HF workflow |
| verify-site-gui | 7 | Pre-ship visibility audit |
