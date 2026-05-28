---
name: harvest-real-components
description: "Phase 0 (pre-clone): harvest real HTML/CSS/screenshot fragments from a target website to build a real-component reference library before writing the WebHarbor Flask mirror. Captures full page, per-section (header/nav/main/hero/footer), and card-like fragments via Playwright + Chromium. Outputs to ~/webvoyager-analysis/real_components/snapshots/<site>/<page>/. Later phases (clone-website, design-tasks, verify-site-gui) reference these snapshots to avoid AI-generated 'generic' UI and to preserve real visual identity. Triggers: '抓真组件', '真站采集', 'harvest components', '看看真站长啥样', '复刻前先抓', 'real components'."
---

# Harvest Real Components — Pre-Clone Reference Capture

把要复刻的真站每个关键页面用真 Chromium 打开，拉回 HTML 片段 + 截图 + 元数据。**写 Flask mirror 之前就做**，让后续 clone/design/verify 阶段都有"真站长这样"的视觉与结构参考。

## 复刻一个站需要 **14 维度** 数据（v7 框架，2026-05-27 R01+R02 大改）

| Pillar | 内容 | 工具产出 |
|---|---|---|
| **1. 样式** | HTML + CSS + JS + 视觉组件 | harvest.py → `full.html` + `full.png` + assets + section/card fragments |
| **2. 文字** | JSON-LD/state/OG + clean body + breadcrumb + feed | harvest.py + reprocess_structured.py → `structured.json` + `article.json` + `breadcrumbs.json` + `feed.xml` |
| **3. 图像** | 真图 URL + sprite + favicon | extract_image_urls.py + extract_sprites.py → `_image_urls.jsonl` + `sprites/` + `_sprites.json` |
| **4. 跳转** | link graph + button catalog + footer | extract_nav_graph.py → `_nav_graph.json` + `_buttons.jsonl` + `_footer_links.jsonl` |
| **5. 表单** | `<form>` 字段/类型/选项/验证 | extract_forms.py → `_forms.jsonl` |
| **6. Session/协议** | HTTP 头 + cookies + xhr + locales + sitemap + final_url/redirected/spa_404_shell/waf_challenge | harvest.py + extract_sitemap.py → metadata.json + `xhr_calls.jsonl` + `locales.json` + `_robots.txt` + `_sitemap_urls.jsonl` |
| **7. 音频** (R01 新) | audio/source/mp3/ogg/wav/m4a/aac/flac/opus + JSON-LD AudioObject | extract_audio_urls.py → `_audio_urls.jsonl`（9/96 站 / 200 URL） |
| **8. 视频** (R01 新) | video/source/iframe embed (YT/Vimeo/Twitch/Bilibili) + mp4/webm/m3u8/mpd + JSON-LD VideoObject + og:video | extract_video_urls.py → `_video_urls.jsonl`（56/96 / 2,668 URL） |
| **9. 图标** (R01 新) | link rel=*icon* / apple-touch / mask-icon / manifest / msapplication-* / og:image | extract_icons.py → `_icons.jsonl`（91/96 / 4,129） |
| **10. 动画** (R01 新, R02 修) | GIF/APNG `<img>` + `<video autoplay loop>` + Lottie + css `url(*.gif)` —— webp 默认静态不计 anim | extract_animations.py → `_animations.jsonl`（66/96 / 574） |
| **11. 代码** (R01 新, R02 加 pre-bare) | `<pre><code>` + bare `<pre>` + inline `<code>` + `<script src>` + 源文件 a[href] + Gist/CodePen/CodeSandbox/Replit/JSFiddle | extract_code_blocks.py → `_code_blocks.jsonl`（95/96 / 37,526） |
| **12. 全语义层** (R01 新+extruct OSS) | microdata + RDFa + microformat + DublinCore — 之前 reprocess_structured.py 漏 80%+ | extract_metadata_extruct.py → `extruct.json` + `_extruct_index.json`（**96/96 / 124,339 records** — imdb 20091 RDFa / hulu 5263 / nike 5105 / fandom 301 microdata + 3063 RDFa） |
| **13. API endpoints** (R02 新) | XHR/fetch calls 聚合 + 分类（app_internal / 3rd_party / beacon） — SPA 站 entity 全在这 | extract_api_endpoints.py → `_api_endpoints.jsonl` + `_api_endpoints_index.json`（21/96 站 / 5,457 calls — drugs 2086 / carmax 742 / bbc 503 / coursera 157） |
| **14. SSR/SPA state** (R02 新) | `__NEXT_DATA__` / `__APOLLO_STATE__` / `__SERVER_DATA__` / `__INITIAL_STATE__` / `__NUXT__` / `__SVELTEKIT_DATA__` / `__REMIX_CONTEXT__` / `__PRELOADED_STATE__` / `window.__data` | extract_server_state.py → per-page `server_state.json` + `_server_state_index.json`（28/96 站 / **32.7 MB total** — imdb 9.9MB / hulu 5.5MB / theverge 2.6MB / marriott 2.4MB / nba 1.9MB / nike 1.8MB / ted 1.4MB / apple 1.3MB Next.js） |

每跑一站 = 14 维度全捕获。`audit_dimensions.py` 跨 96 站统计完整覆盖率。

**OSS 集成（R01 lesson 后）**：
- ✅ **extruct** (pip) — 已封装 `extract_metadata_extruct.py`，96 站 100% 命中 124k records
- ✅ **curl_cffi** (pip) — drugs.com Akamai 墙验证已通（chrome131 impersonate），待集成 harvest.py fallback
- ✅ **ultimate-sitemap-parser** (pip) — 待包成 extract_sitemap.py 备选 backend
- ✅ **warcio** (pip) — 待集成 harvest.py --warc flag
- 推荐进阶：**browsertrix-crawler / crawl4ai / SingleFile CLI**
- 候选清单：`/home/v-haoqiwang/.claude/workspace/harvest-iteration/findings/OPEN_SOURCE_SCRAPERS.md`

**14 维度 site-property-N/A 区分**（不是所有维度对所有站都适用）：
- **JSON-LD 缺失**：cambridge / apple 部分 / arxiv — 不是 bug，靠 og:* meta + 半结构 HTML（extruct 已补 RDFa/DC 把这块填回）
- **BreadcrumbList 缺失**：BBC / 多数 news / Apple marketing — 不是 bug
- **inline SVG sprite 缺失**：apple 用 use_refs / cambridge 用 PNG — 不是 bug
- **facets 缺失**：news 站 / link-nav 站 / React-modal 站 — extract_facets.py 现在写 `_facets_hint.json` 区分"漏抓"vs"真站特性"
- **forms 仅 1**：read-only 站 BBC/wikipedia — 不是 bug
- **sitemap 0**：amazon（robots 不暴露）/ arxiv（用 OAI-PMH） — `_sitemap_index.json` 列候选与各自 status
- **audio 0**：非词典/non-podcast 站基本不发 audio；bandcamp/soundcloud 流媒体走 XHR/blob URL 抽不到（**待加 xhr-mode**）
- **API/state 维度仅 SPA 站有**：MPA/SSR-only 站（github/wikipedia/craigslist html）天然少 XHR 与 SSR JSON blob — 不是 bug

## 何时使用

- **Phase 0 — 任何新 P1+ site 复刻之前必做**
- **Site polish / 视觉升级时**：旧 mirror 看着不像，回去看真站现在长啥样
- **Benchmark 任务设计时**：写 facet/form 类任务前确认真站实际选项

**不要用于**：已 deepen 完的旧 site（用 [[document-site-gui]]）/ 运行时验证（用 [[verify-site-gui]]）/ 任务设计（用 [[design-tasks]]）。

## 工作流位置

```
[harvest-real-components] (Phase 0)  ⬅ 此 skill
        ↓
clone-website (Phase 1)
        ↓
design-tasks (Phase 2)
        ↓
evolve-env (Phase 3)
        ↓
harden-env (Phase 4)
        ↓
seed-database (Phase 5)
        ↓
document-site-gui ⬇ 出 yaml/md
        ↓
verify-site-gui (Phase 6)
```

## 工具

`~/webvoyager-analysis/real_components/harvest.py` — Playwright 单页采集器（v2，2026-05 Round 1 实战升级）。

```bash
cd ~/webvoyager-analysis/real_components
python3 harvest.py <site_slug> <page_name> "<URL>" \
    [--no-headless] [--timeout 30] [--settle 2500] [--scrolls 5] \
    [--ua USER_AGENT] [--no-fallback]
```

v2 默认就装的 anti-bot 套件：
- 真 Chrome 131 Windows UA（破 Cloudflare "Just a moment..."）
- 1366×768 viewport + `en-US` locale + `Accept-Language` + `sec-ch-ua` 头
- `--disable-blink-features=AutomationControlled` Chromium launch arg
- `navigator.webdriver = undefined` init script
- 多步 scroll（默认 5 次 × 500ms）触发 lazy-load
- Cookie kill: 已含 `Accept all` / `I agree` / `Got it` text-based 触发

v2 自动检测的失败状态（写入 metadata.json）：
- `not_found: true` — HTTP 4xx/5xx 或 body 有 "Page Not Found" / "404 - Not Found" 等 soft-404 字面
- `not_found_reason: "HTTP 404" | "body contains 'Page Not Found'" | "title contains '<phrase>'"` (R01 加 title-level 探测)
- `bot_block: true` — body 含 "Access Denied"/"errors.edgesuite.net"/"Checking your connection"/"challenges.cloudflare.com"/"Pardon Our Interruption"/"unusual traffic"/"captcha-delivery" 等
- `bot_block_reason: "body contains '...'"` —— v2.1 加，让人秒看出哪种墙
- `bot_block_reason: "auth_required_shell: status=4xx body=2.3KB title='Sign in'"` (R01 加：小 body + 4xx + auth-y title 升 bot_block，覆盖 amazon checkout/account/orders 漏判)
- `interstitial: true` — body < 5KB 又没明确 block phrase；或 title 是字面 URL（Google reCaptcha 模式：title=`https://www.google.com/search?q=...&sei=...`）
- `http2_error: true` — Chromium `ERR_HTTP2_PROTOCOL_ERROR`（自动用 curl HTTP/1.1 fallback）
- `fallback_used: "curl_http1" | "exa_hint"` — 留 `FALLBACK_NEEDED.md` 让 agent 后续走 Exa MCP 抓 markdown 存 `content.md`
- `final_url: "..."` + `redirected: true` + `redirect_to: "..."` (R01 加：silent 302→login 现在能被下游识别，allrecipes `/cook/<id>` / amazon `/your-orders` 案例)

**v2.1 关键修复**（2026-05 R2 phys_org 案例后）：`detect_failure` 不再 short-circuit。**bot_block 检测优先于 status**，所以 Akamai/CF 的 403 + "Checking your connection" body 会正确标 bot_block（之前会被错标成 not_found）。bot_block 触发 Exa fallback hint；not_found 不触发（真 404 没必要走 Exa）。

## 配套工具（v4 stack，2026-05 — 14 个工具覆盖 6 pillars）

`~/webvoyager-analysis/real_components/` 下完整工具集：

| 工具 | Pillar | 作用 |
|---|---|---|
| `harvest.py` v3.3 (R01) | 1+2+3+6 | 单 URL Playwright 抓 → HTML + fragments + assets + structured.json + xhr_calls.jsonl + locales.json + response_headers/cookies + **final_url/redirected**(R01 新) + feed.xml |
| `harvest_spider.py` | all | BFS 多页爬 + per-host fail-fast + SQLite checkpoint resume |
| `harvest_retry.py` | helper | 单页手动 retry |
| `extract_sitemap.py` (R01 加 default 200) | **6** | 拉 /robots.txt + /sitemap.xml(.gz) → 全量 entity URL 分类。`--max-sub-sitemaps` 默认 30→**200**（booking 案例 275 sub-indexes） |
| `extract_forms.py` | **5** | 每个 `<form>` 字段 / 选项 / 验证 → `_forms.jsonl` |
| `extract_facets.py` (R01 加 hint) | 4 | 侧栏 filter facet + 选项 + URL param 映射 → `_facets.jsonl` + `_facets_hint.json`（0 facets 时区分"漏抓"vs"真站特性"）|
| `extract_image_urls.py` | 3 | 抽 `<img src>` → `_image_urls.jsonl` |
| `extract_sprites.py` | 3 | 抽 inline SVG `<symbol id=X>` → `sprites/<id>.svg` |
| `extract_audio_urls.py` (R01 新) | **7** | `<audio>` / `<source>` / mp3 ogg wav m4a aac flac opus / JSON-LD AudioObject → `_audio_urls.jsonl` |
| `extract_video_urls.py` (R01 新) | **8** | `<video>` / `<source>` / iframe embed (YT/Vimeo/Twitch/Bilibili) / mp4 webm m3u8 mpd / JSON-LD VideoObject → `_video_urls.jsonl` |
| `extract_icons.py` (R01 新) | **9** | link rel="*icon*" / apple-touch-icon / mask-icon / manifest icons / msapplication-* / og:image → `_icons.jsonl` |
| `extract_animations.py` (R01 新) | **10** | GIF/WebP/APNG img + `<video autoplay loop>` + Lottie + css url(*.gif) → `_animations.jsonl` |
| `extract_code_blocks.py` (R01 新) | **11** | `<pre><code>` + script[src] + 源文件 a[href] + Gist/CodePen/CodeSandbox/Replit/JSFiddle iframe → `_code_blocks.jsonl` |
| `extract_nav_graph.py` | 4 | link graph + button catalog + footer-only links |
| `reprocess_structured.py` | 2 | 离线从 `full.html` 抽 JSON-LD / state / article / BreadcrumbList |
| `content_extract.py` | 2 | trafilatura wrapper 单页抽 clean body |
| `index_pool.py` | 3 | 聚所有 image URL 入 SQLite FTS5 |
| `infer_cdn_pattern.py` | 3 | URLs 推 CDN 模板 |
| `index_site.py` | helper | 扫每页 metadata.json → `_index.json` 汇总 |
| `search_local.py` | helper | SearXNG localhost:8888 wrapper，无 quota 替代 Tavily |
| `download_samples.py` (R01 新) | helper | 从 audio/video/icon/anim/image jsonl 各下 N 个真样本到 `_proof_samples/<dim>/`，证明可达 |
| `audit_dimensions.py` (R01 新) | helper | 扫所有 snapshots/ 输出 11 维度 × N 站的 markdown 覆盖表 |

## v4 实战 stats（A-K 11 features 全跑过 96 站）

| Feature | 工具 | 全 96 站成果 |
|---|---|---|
| A. sitemap.xml | `extract_sitemap.py` | **412,087 URLs / 53 sites**（bbc/youtube/coursera 10k cap；43 站没 sitemap） |
| B. forms | `extract_forms.py` | **1,503 forms / 5,381 fields / 84 站**（github 50 forms / amazon 19） |
| C. facets | `extract_facets.py` | **146 groups / 31 站**（bestbuy 21 / akc 17 / newegg 16） |
| D. response_headers + cookies | harvest.py v3.2 | 7 关键 header + 47 cookies (etsy 测) 每次入 metadata.json |
| E. RSS/Atom feeds | harvest.py v3.2 | 自动 HTML-link 发现 + 5 conventional paths probe（theverge 命中 `/rss/index.xml`） |
| F. BreadcrumbList | `reprocess_structured.py` | JSON-LD BreadcrumbList → `breadcrumbs.json`，提供 entity 路径 |
| G. --expand-tabs | harvest.py v3.2 | 展开 tab/accordion/details/aria-expanded false → `full_expanded.html` |
| H. XHR/fetch capture | harvest.py v3.2 | etsy 39 / bbc 87 / theverge 228 calls → `xhr_calls.jsonl` |
| I. i18n hreflang | harvest.py v3.2 | etsy 29 locales / bbc 2 → `locales.json` |
| J. SVG sprites | `extract_sprites.py` | **4,026 symbols / 16 sites**（yelp 2363 / fandom 490） |
| K. footer-only nav | `extract_nav_graph.py` | `_footer_links.jsonl` 单独 dump 真站底部目录 |

reprocess 实战：90+ 站现有 snapshots **零网络调用** 离线 reprocess → **801 structured.json + 764 article.json**（carmax 125 JSON-LD / landwatch 41）。

下游用法：写 site_specs / seed_data 时**直接读 `structured.json` 的 og:image / jsonld[0].image / state.next_data.props.pageProps**，比解 HTML 准确百倍。`_sitemap_urls.jsonl` 喂 spider 做 entity-driven 深爬。`_forms.jsonl` 给 benchmark 任务设计 ground-truth 字段。

每次产出 `~/webvoyager-analysis/real_components/snapshots/<site>/<page_name>/`：
- `full.html` + `full.png` + `full_expanded.html`（若 --expand-tabs）
- `page-header.html`、`nav.html`、`hero.html`、`main.html`、`footer.html`、`container.html`、`wrap.html`、`sidebar.html`、`card-*.html`
- `metadata.json`（v3.2: 含 response_headers + cookies + feed_found + locale_count + xhr_count + jsonld_count）
- `structured.json` / `article.json` / `breadcrumbs.json` / `locales.json` / `xhr_calls.jsonl`
- `assets/{css_*,js_*,favicon,manifest.json}` / `feed.xml`
- `sprites/<id>.svg`（若有 inline sprite）
- `FALLBACK_NEEDED.md` / `wayback.html` / `content.md`（bot_block 时）

每站根目录还有：`_index.json` / `_image_urls.jsonl` / `_forms.jsonl` / `_facets.jsonl` / `_nav_graph.json` / `_buttons.jsonl` / `_footer_links.jsonl` / `_sprites.json` / `_sitemap_urls.jsonl` / `_sitemap_index.json` / `_robots.txt`。

## 单站采集建议（10 页 / 站）

每个 P1+ 候选站至少抓这 10 页（缺哪个跳哪个）：

| Page | 用途 |
|---|---|
| `home` | 首屏 hero、主 nav、品类入口、card 风格 |
| `search` | 过滤栏、结果 card grid、排序 chip、分页 |
| `category` | category landing 的 hero + 子分类卡 + 推荐 |
| `pdp` / `detail` | 详情页主区 + 媒体轮播 + 规格表 + 评论 + 推荐 |
| `cart` / `compare` / `wishlist` | 列表型集合 |
| `checkout` | 多步表单 + 进度指示 |
| `account` / `dashboard` | 侧栏 nav + 信息卡 |
| `signin` / `signup` | 表单 + 第三方登录按钮 + 错误状态 |
| `help` / `faq` | 文档站结构 |
| `404` | 错误页结构 |

## 批量执行（subagent）

派 1 agent 抓 1 站（10 页 ≈ 5 min），并行 5 站 / 25 min 收 50 页。

```
任务：用 harvest.py 抓 <site_slug> 站点的 10 个核心 page。

候选 URL（不一定全都好用，404 就跳过，agent 自己用 Tavily 找替代 URL）：
- home: https://www.<site>.com/
- search: https://www.<site>.com/search?q=...
- ...

每页跑 python3 ~/webvoyager-analysis/real_components/harvest.py <site_slug> <page_name> "<URL>"

完成后报告 metadata.json 里 fragments 数量 + 任何抓不到的页面。
```

## 之后怎么用

### 1. 写 clone-website 时

打开 `snapshots/<site>/home/full.png` 看色调、间距、layout；打开 `nav.html` 看真实菜单 taxonomy；打开 `card-*.html` 看 card 必有字段（image / title / link / 价格 / 评分 / badge）。把这些视觉信号转成 Jinja + tailwind。

### 2. 写 site_specs yaml 时

对每个 page 的 `elements:` 字段，对照真站 snapshot 列出真实 GUI 元素。避免凭空想象。

### 3. 沉淀跨站 catalog

每收 5+ 站同类型 component（product card / filter sidebar / checkout wizard），在 `catalog/<archetype>.md` 写对照表（站 / 字段集 / accent color / 风格差异），让未来 clone-website 直接抄。

## 已知陷阱

| 陷阱 | 缓解 |
|---|---|
| **Cookie/consent overlay 挡内容** | harvester 自动找 `#onetrust-accept-btn-handler` / `button[id*='accept']` / `Accept all` / `I agree` / `Got it` text-based 一键关掉 |
| **Lazy-load section 没出现** | harvester 自动 5 次 scroll-by-viewport-height（v2 升级，原 1 次只能拿到 30%） |
| **`<header>` / `<nav>` / `<main>` 缺失（纯 div 站，phys.org / fandom / discogs / google-maps）** | 已补 `[class*='header']` / `[class*='nav']` / `[id*='content']` / `[id='page']` / `[class*='page-wrap']` 兜底；card 选择器加 `[jscontroller]` 给 Google SPA |
| **SPA 全部空 div + 慢 JS** | timeout 30s + settle 2.5s + 5 次 lazy-load scroll。Maps/Flights canvas 类 SPA 仍只能拿 full.html，section 提取意义不大 |
| **大站 full.html 3+ MB / full.png 1+ MB 截图超时** | 自动 try/except 退化到 viewport-only（v2 加） |
| **Akamai/AWS-WAF 边缘墙**（apartments.com / drugs.com / mayoclinic.org / amazon.com 部分页面） | Azure datacenter IP 被 IP-class 拉黑；stealth/UA/xvfb 全无效。v2 自动检测 `bot_block=true` + 写 `FALLBACK_NEEDED.md`，agent 接着跑 `mcp__exa__crawling_exa` 拿 markdown 存 `content.md` |
| **Cloudflare Turnstile**（phys.org / discogs 部分 routes / 各类后端 API）| body `<title>Just a moment...</title>` + `script src="https://challenges.cloudflare.com/..."`。HTTP 状态可能是 403 或 200。v2.1 修了 detect_failure 优先级让它正确触发 bot_block + Exa hint |
| **HTTP/2 protocol error**（nba.com 全站 / 偶发其它）| v2 catch `ERR_HTTP2_PROTOCOL_ERROR` 自动 fallback `curl --http1.1`（HTML-only，无截图）。但 R2 发现：v2 stealth UA + Chrome 131 headers 让 NBA HTTP/2 也通了 0 次 fallback —— 可能是 NBA 后端对老 UA 才发 HTTP/2 |
| **Captcha shell**（amazon 部分页面）| body < 50KB + "Are you a robot" → `bot_block=true`，走 Exa fallback |
| **Soft 404**（status 200 + `<h1>404 - Not Found</h1>` / `<title>Page Not Found</title>`，RT / SmartAsset / NBA `/tickets`）| v2.1 加 SOFT_404_PHRASES 扫 body 前 50KB，标 `not_found=true` + `not_found_reason: "body contains 'Page Not Found'"` |
| **404 chrome 被当真实数据**（bbc 失效 article / arxiv subscribe）| v2 status≥400 → `not_found=true` 标记；agent 后续可弃这页或换 URL |
| **Google SERP interstitial**（results/images/news/videos/shopping/maps_search 6 个变体）| Google 发送 ~6.6 KB 重定向 stub，HTTP 200，title 是字面 URL `https://www.google.com/search?q=...&sei=...`。v2.1 检测"title startswith http"→ `bot_block` + `interstitial` 都 true。短期没好办法，long-term 需 residential proxy |
| **图片 src 是 CDN 链接，复刻时 404** | 单独 `curl --referer https://<site>/ <img-url>` 下载到 `sites/<slug>/static/images/` |

## 经验

- **抓 10 页 / 站 → 真组件库**：5-7 min 跑完，磁盘 ~50 MB，价值远超时间成本
- **同一站建议同一时间集中抓**：避免 A/B test 改版让多次抓的结构不一致
- **headless = True 默认**：CI / 后台跑都行。仅在调反爬 / cookie wall 时切 `--no-headless`
- **不要 commit snapshots 到 WebHarbor 仓**：放 `~/webvoyager-analysis/real_components/snapshots/`，与 site_docs / site_specs 同层独立工作区
- **catalog 是最高 ROI**：跨站 5 个 product card 比较后能抽出"标准 product card" template，多站复用

## Round 1 (36 站) 实战数据（2026-05）

总成绩：~335 page，~1 GB，6 个并行 agent × 6 站，平均每 batch ~5 min wall clock。

| 类别 | 站 | 状态 |
|---|---|---|
| ✅ 满分 | github / apple / coursera / huggingface / wolfram / cambridge / berkeley / osu / phet / ted / espn / imdb / rotten_tomatoes / smartasset / boardgamegeek / mega / recreation_gov / booking / compass / carmax / eventbrite (8/11) / allrecipes (8/10) | 50+ 真 fragment / 站 |
| ⚠️ Akamai 全 403 | **apartments_com / drugs_com / mayoclinic_org** | 11/12 页全 block；需 Exa 抓 markdown |
| ⚠️ HTTP/2 error | **nba_com** | 全 11 页 ERR_HTTP2_PROTOCOL_ERROR；v2 用 curl --http1.1 拿 HTML |
| ⚠️ Captcha shell | **amazon_com** (7/10) | 44KB shell；偶尔过 cart/category/deals |
| ⚠️ Google interstitial | **google search SERPs**（6 个变体）| home / advanced / preferences 过；results/images/news/videos/shopping/maps_search 被拦 |
| ⚠️ SPA canvas / div soup | **google_maps / phys_org / fandom / discogs / craigslist** | section 选择器命中率低；v2 加 `container` / `wrap` / `[jscontroller]` 兜底
