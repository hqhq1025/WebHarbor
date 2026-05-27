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

`~/webvoyager-analysis/real_components/harvest.py` — Playwright 单页采集器。

```bash
cd ~/webvoyager-analysis/real_components
python3 harvest.py <site_slug> <page_name> "<URL>"
```

参数：
- `<site_slug>`：域名 snake_case（`bestbuy_com` / `akc_org` / `us.megabus.com` → `megabus_com`）
- `<page_name>`：页面意图 slug（`home` / `search` / `pdp` / `cart` / `checkout` / `account` / `compare` / `article` / `dashboard`）
- `<URL>`：完整 URL（必须 https://）

每次产出 `~/webvoyager-analysis/real_components/snapshots/<site>/<page_name>/`：
- `full.html` + `full.png` — 整页
- `page-header.html` + `.png`、`nav.html`、`hero.html`、`main.html`、`footer.html` — 主要 section
- `card-<sel>-<n>.html` + `.png` — 首 3 个 card-like 元素
- `metadata.json` — 索引 + bbox + selector + 时间戳

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
| **Cookie/consent overlay 挡内容** | harvester 自动找 `#onetrust-accept-btn-handler` / `button[id*='accept']` 一键关掉 |
| **Lazy-load section 没出现** | harvester 已自动 scroll-to-bottom 再 scroll-to-top 一遍触发 |
| **`<header>` / `<nav>` / `<main>` 缺失（纯 div 站）** | 已补 `[class*='header']` / `[class*='nav']` / `[class*='hero']` fallback |
| **SPA 全部空 div + 慢 JS** | timeout 30s + wait 2.5s + lazy-load scroll。若仍空，加 `--no-headless` 手动看 |
| **大站 full.html 3+ MB** | 不进 git，本地保存。catalog 引用相对路径 |
| **Cloudflare/Akamai bot wall** | 浏览器 UA 通常能过；卡住就 `--no-headless` 跑（人手解 captcha） |
| **图片 src 是 CDN 链接，复刻时 404** | 单独 `curl --referer https://<site>/ <img-url>` 下载到 `sites/<slug>/static/images/` |

## 经验

- **抓 10 页 / 站 → 真组件库**：5-7 min 跑完，磁盘 ~50 MB，价值远超时间成本
- **同一站建议同一时间集中抓**：避免 A/B test 改版让多次抓的结构不一致
- **headless = True 默认**：CI / 后台跑都行。仅在调反爬 / cookie wall 时切 `--no-headless`
- **不要 commit snapshots 到 WebHarbor 仓**：放 `~/webvoyager-analysis/real_components/snapshots/`，与 site_docs / site_specs 同层独立工作区
- **catalog 是最高 ROI**：跨站 5 个 product card 比较后能抽出"标准 product card" template，多站复用
