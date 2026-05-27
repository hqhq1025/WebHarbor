---
name: harvest-real-components
description: "Phase 0 (pre-clone): harvest real HTML/CSS/screenshot fragments from a target website to build a real-component reference library before writing the WebHarbor Flask mirror. Captures full page, per-section (header/nav/main/hero/footer), and card-like fragments via Playwright + Chromium. Outputs to ~/webvoyager-analysis/real_components/snapshots/<site>/<page>/. Later phases (clone-website, design-tasks, verify-site-gui) reference these snapshots to avoid AI-generated 'generic' UI and to preserve real visual identity. Triggers: '抓真组件', '真站采集', 'harvest components', '看看真站长啥样', '复刻前先抓', 'real components'."
---

# Harvest Real Components — Pre-Clone Reference Capture

把要复刻的真站每个关键页面用真 Chromium 打开，拉回 HTML 片段 + 截图 + 元数据。**写 Flask mirror 之前就做**，让后续 clone/design/verify 阶段都有"真站长这样"的视觉与结构参考。

## 何时使用

- **Phase 0 — 任何新 P1+ site 复刻之前必做**
- **Site polish / 视觉升级时**：旧 mirror 看着不像，回去看真站现在长啥样
- **写跨站公共 partial 之前**：`_product_card.html` / `_filter_sidebar.html` / `_breadcrumb.html` 等

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
- `not_found_reason: "HTTP 404" | "body contains 'Page Not Found'"`
- `bot_block: true` — body 含 "Access Denied"/"errors.edgesuite.net"/"Checking your connection"/"challenges.cloudflare.com"/"Pardon Our Interruption"/"unusual traffic"/"captcha-delivery" 等
- `bot_block_reason: "body contains '...'"` —— v2.1 加，让人秒看出哪种墙
- `interstitial: true` — body < 5KB 又没明确 block phrase；或 title 是字面 URL（Google reCaptcha 模式：title=`https://www.google.com/search?q=...&sei=...`）
- `http2_error: true` — Chromium `ERR_HTTP2_PROTOCOL_ERROR`（自动用 curl HTTP/1.1 fallback）
- `fallback_used: "curl_http1" | "exa_hint"` — 留 `FALLBACK_NEEDED.md` 让 agent 后续走 Exa MCP 抓 markdown 存 `content.md`

**v2.1 关键修复**（2026-05 R2 phys_org 案例后）：`detect_failure` 不再 short-circuit。**bot_block 检测优先于 status**，所以 Akamai/CF 的 403 + "Checking your connection" body 会正确标 bot_block（之前会被错标成 not_found）。bot_block 触发 Exa fallback hint；not_found 不触发（真 404 没必要走 Exa）。

## 配套工具

`~/webvoyager-analysis/real_components/index_site.py` — 扫 `snapshots/<site>/<page>/metadata.json`，写 `_index.json` 汇总：

```bash
python3 index_site.py <site>      # 单站
python3 index_site.py --all       # 全站

# 输出格式：
# <site>: pages=N ok=X bot_block=Y not_found=Z http2=W frags=F size=SMB
```

每次 harvest 后跑一遍 `--all`，立刻看到哪些站需要 Round 2 重抓。

每次产出 `~/webvoyager-analysis/real_components/snapshots/<site>/<page_name>/`：
- `full.html` + `full.png` — 整页
- `page-header.html`、`nav.html`、`hero.html`、`main.html`、`footer.html`、`container.html`、`wrap.html`、`sidebar.html`
- `card-<sel>-<n>.html` — 首 3 个 card-like 元素
- `metadata.json` — 索引 + bbox + selector + flags + 时间戳
- `FALLBACK_NEEDED.md` —（若 blocked）告诉 agent 后续怎么走 Exa

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
