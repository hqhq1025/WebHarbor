---
name: verify-site-gui
description: "Run Playwright in real Chromium against a WebHarbor mirror's yaml spec to verify every promised page/modal/element is actually reachable and visible. Catches dead routes, broken modals, missing nav landmarks, and other visibility bugs after deepen/polish rounds. Outputs per-page JSON reports; bug fixes land in `sites/<slug>/{app.py, templates/*.html}`. Use after any deepen pass, before declaring a site done, or when site_specs/<slug>.yaml diverges from runtime. Triggers: '验证页面', '可见性', 'playwright check', '页面真能跳吗', 'verify site', 'walk yaml'."
---

# Verify Site GUI — Playwright-based YAML ↔ Runtime Conformance

把 `site_specs/<slug>.yaml` 当作"site 应该提供什么"的合同，开真 Chromium 一页一页打开验证：实际 HTTP 通吗？模态触发器在哪？nav 出现没？JS 有错吗？把发现的 visibility bug 直接修在 `sites/<slug>/{app.py, templates/*.html}`，commit + push fork。

## 何时使用

- **Deepen 收尾**：任何 GUI-deepen / clone-website 大改动之后，确认 yaml 路线图与运行时一致
- **Pre-PR / 上 HF 资源前**：发布前 sanity check
- **Bug hunt**：用户反馈"我点不到 X" / "这页打不开"，先跑 verify 看 yaml 怎么说的
- **Schema 漂移检测**：yaml 是 polish 时写的，多轮 deepen 后 app/模板可能漂移

不要用于：写 yaml（用 [[document-site-gui]]）/ 加 deepen 内容（用 [[clone-website]]/[[evolve-env]]） / 任务质量审计（用 [[design-tasks]]）/ byte-id 验证（用 [[seed-database]]）。

## 工作流位置

```
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
verify-site-gui (Phase 6) ⬅ 此 skill
   ↓
（如果发现 bug → 修 → 再来一遍）
   ↓
declare done / ship
```

## Harness 一份

放在 `~/webvoyager-analysis/site_specs/_verify_playwright.py`（团队共享，不进 WebHarbor 仓库 — 与其它 docs 工具同步约定）。

每跑一站做下面 5 步：

1. **起 Flask app** 在唯一端口（`50000 + SITE_IDX[slug]`），threaded=True 防 stall 级联
2. **DB-introspection 抓真 slug**：扫 `instance/<site>.db` 每个表的 slug-like 列（`slug` / `permalink` / `handle` / `code` / `tt_id` ...），存成 placeholder → 真值的 map
3. **真 Chromium 浏览**（headless）：
   - `page.goto(url)` 每个 yaml 里的 page URL（先用 DB slug map 替换 placeholder）
   - 收 HTTP status / title / body length / JS console errors
   - 检查 nav 元素 visible (`[role=navigation], .top-header, .navbar, ...`)
   - modal 检查：找 opened_from page，扫触发器存在性 (`[data-bs-toggle="modal"]`)
4. **写报告** 到 `site_specs/_verify/<slug>_pw.json`：每页 status + issue + ... + 全局 summary
5. **打印一行总结**：`<slug>: yaml_pages=N checked=M ok=X 404=Y 5xx=Z exc=W`

## 必备 harness 设定（踩过坑的）

| 设定 | 为啥 | 不这样会怎样 |
|---|---|---|
| **Flask `threaded=True`** | 单线程 Flask 第一个慢请求会卡死 chromium 并发后续 request | 整批 ERR_CONNECTION_REFUSED 假阳性 |
| **`stderr=DEVNULL`** on subprocess | dev server stderr PIPE 满了会死锁 | app 进程没了报告全是 "exception" |
| **playwright `route` abort css/font/image/xhr** | chromium 并发资源 fetch 把 app 打死 | 同上 |
| **`goto timeout = 20s`**（不是默认 30s 也不是激进 10s） | search 页可能 50MB HTML，domcontentloaded 解析慢；过小会假超时 | 假阳性 |
| **wait-for-port 120 次循环 × 0.5s = 60s** | github 等大站 seed-at-import 18s 起步 | app 还没起来就开始测，全 404 |
| **port = 50000 + SITE_IDX** 唯一映射 | 并发跑多站不撞 | 端口冲突随机失败 |
| **DB slug map + PER_SLUG overrides + URL-prefix-aware lookup** | 通用 `<slug>="1"` 假阳性 60-90% | 假 404 满天飞 |

## DB-introspection + PER_SLUG override 模式

```python
# 1. 自动从 instance/<site>.db 扫所有 slug-like 列
table_map = {}    # table_name → first slug
col_map = {}      # column_name → first value
ID_LIKE = ("slug", "permalink", "handle", "url_slug", "tt_id", "nm_id",
           "code", "icao", "iata", "tag", "token", "arxiv_id", "username",
           "name", "lang_code", "region_code", "city_slug", "line_slug",
           "topic")

# 2. URL → slug 优先级：
#    a. PER_SLUG[site] hardcoded override（处理 enum / 特殊格式 ID）
#    b. URL-prefix-aware lookup：/spaces/<x> → spaces 表的 slug
#    c. 通用 col_map / table_map fallback
#    d. OVERRIDES 全局默认（icao=B738 / iata=JFK / lang_code=en）
#    e. 最后才是 "1"

# 3. PER_SLUG 例子（每站手工 1-3 条搞定 80% 假阳性）：
PER_SLUG = {
    "osu": {"level": "undergraduate"},   # /admissions/<level> 是 enum 不是 slug
    "carmax": {"stock": "C0000542"},     # <stock> 是 CXXXXXXX 格式
    "nba": {"series_slug": "cavaliers-vs-pistons"},  # 需要 a-vs-b 格式
    "imdb": {"tt_id": "tt0017136", "nm_id": "nm0000006"},
    "wolfram_alpha": {"cr_id": "186"},   # seed 从 id 186 开始（不是 1）
    "phet_simulations": {"code": "af"},   # 真存在的语言代码（不是默认 AA）

    # 多 placeholder + URL-prefix override 模式（2026-05 P0 批 5 站实战）
    # 用 _url_overrides 让不同 URL 前缀走不同 slug 源，避免一刀切
    "eventbrite": {
        "region_slug": "northeast", "cat_slug": "music", "label": "this-weekend",
        "n_slug": "manhattan", "name": "your-account",
        "_url_overrides": {"/d/": "music", "/help/section/": "your-account",
                           "/organize/": "pricing"},
    },
    "smartasset": {
        # 真 bug：harness 把 author slug "amanda-dixon" 误填到 article/compare/wizard URL
        "_url_overrides": {"/smartreads/": "15-states-that-dont-tax-retirement-income",
                           "/compare/": "roth-ira-vs-401k",
                           "/advisor-match/": "retirement_status"},
        "hub": "banking", "page_slug": "best-savings-accounts", "step": "retirement_status",
    },
    "apartments_com": {
        # 链式 placeholder /<state>/<city_slug>/<building_slug>/...
        # 若不指定，harness 会用同一 slug 填所有 placeholder → /atlanta-ga/atlanta-ga/atlanta-ga/
        "state": "ny", "city_slug": "new-york-ny", "nbhd_slug": "upper-east-side",
        "building_slug": "mosaic-new-york-ny-000", "plan_slug": "plan-1br-a-0",
        "slug": "apartments-with-pool", "topic": "applying",
        "_url_overrides": {"/help/": "applying", "/glossary/": "administrative-fee"},
    },
    "mayo_clinic": {
        # 18 个 URL-prefix override 覆盖 conditions/procedures/drugs/depts/...
        "_url_overrides": {"/clinical-trials/": "NCT05123456",
                           "/healthy-lifestyle/": "nutrition",
                           "/diseases-conditions/": "diabetes-type-2",
                           "/tests-procedures/": "blood-test",
                           "/drugs-supplements/": "aspirin"},
    },
    "fandom": {
        # MediaWiki Namespace: 前缀（Category:/User:/File:/Talk:）走专门 slug
        "_url_overrides": {"Category:": "Avengers", "User:": "alice", "Talk:": "Iron_Man",
                           "File:": "iron-man.jpg", "Help:": "Editing",
                           "/Forum/Thread/": "1", "/Poll/": "1"},
        "bad_title": "DoesNotExist_PageXYZ", "cat_slug": "Avengers",
    },
}
```

## 4 种发现 + 对应的 fix

### 1. 真 404 — yaml 承诺路由但 app 没实现

**症状**：harness 用真实 DB slug 替换 placeholder 后仍 404；多个 URL 同样模式都 404。

**fix**：要么补 route + template（最常见），要么修 yaml 把这页删掉（route 不该承诺）。

**真案例**：
- `apple` yaml 写 `/buy/iphone/<model>` 但 `apple_deepen.py` 注册在 `/shop/buy-iphone/<model>` → 加 4 个 alias route 重定向到现成 handler
- `google_map` yaml 写 `/transit/stop/<slug>` 但 app 真没这个 route → 加 route + 模板 或 改 yaml
- `eventbrite` yaml 承诺 `help_index.section_link → help_section`，模板里 5 个 section h2 是死文本不是链接 → 改 `<h2>` 为 `<a href="/help/section/{slug}">`（commit `7f2cdf3`）

### 2. 真 5xx — handler crash

**症状**：单 URL 持续 500，curl 复现，stderr 有 traceback。

**fix**：根因修。常见：
- None-safe sort key 缺失（`'<' not supported between NoneType and ...`）— espn `sport_stats()` 真案例
- 注释/换行错误吞掉 def — huggingface `_section_slug` NameError 真案例（一行 def 跟注释连在一起）
- 表/列缺失（`no such column: ...`）— 通常是 schema drift 没 normalize

### 3. 缺 nav / a11y landmark

**症状**：harness 报 `;no_nav` — 找不到 `[role="navigation"]` / `.navbar` / `.top-header` 等任一。

**fix**：base.html / 侧栏给 `<nav>` 或 `<aside>` 加 `role="navigation"` 属性。

**真案例**：google_map `_rail.html` 缺 `role="navigation"`，`base.html` 缺 `<header role="banner">` — commit 670eb99 修了；smartasset `calculator_print.html` 加 `<header role="banner">` — commit `6e5e4c8`。

### 4. modal trigger 缺失

**症状**：yaml `modals.X.opened_from` 指向 page Y，但 page Y 的 HTML 里没 `[data-bs-toggle="modal"]` / `[data-toggle="modal"]` / "Sign in" 按钮等 modal 触发器文案。

**fix**：模板里加触发器 `<button data-bs-toggle="modal" data-bs-target="#X">...</button>` 或对应 JS。或确认 yaml 是不是把"原生 confirm()"误写成 modal — 真案例 compass `collection_detail` 删 collection 用 native `confirm()` 但 yaml 说 modal → commit 60a2b31 改成 HTML modal w/ `cancel_btn` + `confirm_delete_btn`。

### 5. byte-identical reset 被非确定性打破

**症状**：每次 `rm -rf instance && python3 app.py` 产生的 `instance/<site>.db` md5 都不同 → reset 后与 `instance_seed/` 不匹配 → benchmark 的 reset invariant 失效。

**3 个常见非确定源 + fix**（2026-05 fandom 实战，commit `dc5b676`）：
- **bcrypt random salt**：`User.password_hash` 每次 seed 重算 → 用 **pinned salt** `$2b$10$WebHarborSeedSalt22BC.` 或用 fandom 的 `assign_pinned_password()` helper 走固定盐
- **builtin `hash()` 受 `PYTHONHASHSEED` 影响**：seed_phase2 里用 `hash(filename)` 决定 uploader / joined_date → 换 **`_stable_hash()`** md5-based 替代
- **`datetime.utcnow()` 默认值**：`User.created_at = utcnow` 在 row-create 时间运行 → 显式设 `BASE_TS = datetime(2026, 5, 27, 12, 0, 0)`；对 `WatchItem.since` / `UserFollow.since` / `WikiSubscription.since` 同样处理

apartments_com 早就有 `_normalize_seed_db_layout()` + `_deterministic_pbkdf2_hash(email)` 解决这个；compass 也是同 pattern。新站 clone 完一定先跑 byte-id 测，撞上立即套这套 fix。

### 6. python3 app.py 标杆循环 import

**症状**：`cd sites/<slug> && python3 app.py` 报 `ImportError: cannot import name 'db' from partially initialized module 'app'` 或 seed_database 跑两次。

**根因**：app.py 作 `__main__` 加载时，`from seed_data import seed_database` 又 `from app import db, ...` → 启动 app.py 第二个 module instance，俩 SQLAlchemy() 实例。

**fix**：app.py 顶部加：
```python
import sys
sys.modules.setdefault('app', sys.modules[__name__])
```
让 `from app import ...` 拿到当前模块。fandom + apartments_com 都套了这个（apartments commit `850465d`）。新站务必早装。

## 7 种假阳性（必须先排除真 bug）

每个 site 平均 5-15 个 404 中往往只有 0-2 个真 bug，其它是 harness 的"假 slug"问题：

1. **`<slug>=1` 但 DB 没 id=1** — wolfram seed 从 186 起步
2. **URL placeholder 是 enum 不是 slug** — `/admissions/<level>` ∈ {undergrad/grad/transfer/intl}
3. **特殊格式 ID** — carmax `<stock>=C0000542` / google_flights `<icao>=B738`
4. **复合 slug 格式** — nba `<series_slug>=cavaliers-vs-pistons`（必须 a-vs-b）
5. **URL-prefix-aware 错表** — huggingface 把 model slug 塞进 `/spaces/...` 路径；smartasset 把 author `amanda-dixon` 误填到 `/smartreads/<slug>` —— 用 `_url_overrides` 修
6. **YAML "或" / "[optional]" 段没处理** — `/foo 或 /bar` / `/cars[/<x>]`
7. **POST-only 路由测 GET** — phys_org `/article/<slug>/comment` 是 405（intentional）；eventbrite `/checkout/<slug>/promo`, `/order/<code>/cancel`, `/tickets/<code>/gift` 同理

**新增 2 种 yaml-level 假阳性（2026-05 加进 harness）**：

8. **`template: null` 的 download endpoint** — yaml 标 `template: null` 表示无渲染（POST-only 或 ICS/PDF/CSV/ZIP 直接 download）。Playwright 撞 `Content-Type: text/calendar` 等会抛 "Download is starting" exception。harness 现在用 `urllib` fallback 测 status；同时 walker 应过滤 `template: null`。
9. **`id: not_found / page_404 / error_404 / fallback_404` 的 404 fallback 页** — yaml 故意把"任意未匹配 URL → 404"也列成一个 page（apartments_com `page_404`，fandom `article_missing`）。harness walker 应按 id 模式过滤。

**排除流程**：
- 看 harness 输出 status + issue
- `grep '@app.route' sites/<site>/**/*.py` 确认 route 是否真注册
- 直接 `curl http://127.0.0.1:<port>/<url>` 复现
- 用真实 DB 值（`sqlite3 instance/<site>.db 'select slug from <table> limit 1'`）替换试

## 单站执行步骤

```bash
# 1. 跑 harness — 第 3 arg 是 max_pages（默认 40，跑全 yaml 用 80）
cd ~/webvoyager-analysis
python3 site_specs/_verify_playwright.py <slug>           # 默认 max_pages=40
python3 site_specs/_verify_playwright.py <slug> 50034 80  # 跑全 77 页 mayo

# 2. 看报告
cat site_specs/_verify/<slug>_pw.json | jq '.summary'
cat site_specs/_verify/<slug>_pw.json | jq '.pages[] | select(.issue)'

# 3. 对每个 issue 分类：harness 假阳性 vs 真 bug
#    - grep '@app.route' 确认路由
#    - curl 复现
#    - 看 stderr (subprocess 跑 site 时加 stderr=PIPE 临时调试)

# 4. 真 bug 修在 sites/<slug>/
#    - 加 route + template
#    - 加 role="navigation"
#    - 加 modal trigger
#    - 修 handler crash

# 5. 重跑 harness 验证
python3 site_specs/_verify_playwright.py <slug>

# 6. byte-id reset 必过
cd ~/repos/WebHarbor
cp sites/<slug>/instance_seed/*.db sites/<slug>/instance/ 2>/dev/null
md5sum sites/<slug>/instance/*.db sites/<slug>/instance_seed/*.db

# 7. commit + push fork
git -C ~/repos/WebHarbor add sites/<slug>/
git -C ~/repos/WebHarbor commit -m "<slug>: fix visibility bugs (... issues)"
git -C ~/repos/WebHarbor push fork main
```

## 批量执行（≥3 站，subagent）

派出 batch=5 站/agent，6 个 agent 跑 29 站。**不要 1 agent ≥6 站**（playwright + flask 内存吃紧 + 200k+ tokens 容易 stall）。

派发 prompt 模板：

```
5 站可见性验证 + 修复：<slug1>/<slug2>/<slug3>/<slug4>/<slug5>

**Harness**: python3 ~/webvoyager-analysis/site_specs/_verify_playwright.py <slug>

每站工作流：
1. 跑 harness → 读 ~/webvoyager-analysis/site_specs/_verify/<slug>_pw.json
2. 排查每个 issue：harness 假阳性（多数） vs 真 site bug
   - grep '@app.route' 确认路由
   - 直接 curl 复现
   - 用真 DB slug 替换试
3. 真 bug 修在 sites/<slug>/{app.py, templates/*.html}
4. 重跑 harness 验证
5. byte-id reset 双 md5 一致
6. cd ~/repos/WebHarbor && git commit per-site "<slug>: fix visibility bugs" && git push fork main

**约束**：
- ≤30 min/站
- byte-id 必过
- 不动 PINNED bcrypt / MIRROR_REFERENCE_DATE / normalize_seed_db_layout
- max_pages=40 限制（headless chrome 内存吃紧）
- harness 改进可写回 site_specs/_verify_playwright.py（共享 tooling）

**报告**：每站 ≤150 字（before/after + 真 bug + commit hash）总 ≤800 字。
```

`run_in_background: true`。

## 已知 harness 限制

- **modal trigger 启发式**：找 `[data-bs-toggle="modal"]` / `data-toggle="modal"` / "Sign in" 文字。多步 modal / 需 auth 上下文的 modal / 纯 JS 触发 modal 会漏报。手动 spot-check 几个就好。
- **POST-only 路由测 GET 显示 405**：harness 是 GET-only。yaml 里这些通常 `template: '(redirect)'` 标记着，可以从 page 列表里过滤掉。
- **max_pages=40**：playwright headless chrome 每页 ~50MB，跑全 yaml 80+ 页内存吃紧。先抽 40 个具代表性的，剩余 follow-up。
- **跨 agent harness 编辑 race**：多 subagent 同时跑会 race 改 `_verify_playwright.py`。建议先冻结 harness，等批次跑完再升级。
- **slug enum vs slug**：harness 没法区分 `<level>` 是枚举还是 slug。靠 PER_SLUG override 手工补。

## 经验总结

- **真 bug 率 ~0.5%** — 一轮 29 站 × 30 页 ≈ 1000 检验点 ≈ 5 个真 bug。其余都是 harness 假阳性。
- **6 个真 bug 类型** 都在本 skill §"6 种发现"里：missing route / handler crash / nav landmark / modal trigger / byte-id reset broken / circular import。
- **harness 升级路径** 早就有形：每跑一批就会发现 1-2 个改进点（threaded / abort assets / wait_for_port / PER_SLUG / `或` 处理 / download fallback / template:null filter / max_pages CLI arg）。改完写回共享 harness。
- **per-site PER_SLUG + `_url_overrides` 是最高 ROI 的 fix**：手工写 1-3 个 PER_SLUG 条目能消掉一个 site 80%+ 的假阳性。多 placeholder URL 必须用 `_url_overrides`。
- **commit 粒度 per-site**：每站一个 commit，message `<slug>: fix visibility bugs (N route / M template)`，便于回滚和 audit。
- **agent 派发陷阱**：Agent tool **没有 SendMessage** —— "spawn 一个 agent 让它给另一个 agent 发消息"行不通，新 agent 会把消息当成自己的任务从头跑（产生 dual agents 同改一个 site）。要 inject 新指令只能等当前 agent 完成或 TaskStop 重派。
- **worktree baseRef 陷阱**：默认 `worktree.baseRef = fresh` fork 自 `origin/<default>`。若本地 main 有未 push 的工作（如刚 merge 5 个 P0 site），worktree 看不到。两条出路：(a) 不用 worktree 让 agent 直接读 main；(b) 改 baseRef 或先 push origin。

## 索引

每 verify pass 完成后在 `~/webvoyager-analysis/site_specs/_verify/README.md` 写一行：

```markdown
| <slug> | <date> | yaml_pages | OK | 404 | 5xx | real-bugs | commit |
```
