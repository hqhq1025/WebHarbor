---
name: document-site-gui
description: "Produce comprehensive GUI-centric Chinese documentation for one or more WebHarbor mirror sites (sites/<slug>/). Outputs **two files per site**: (1) `site_docs/<slug>.md` — human-readable doc with page state variants (anon vs auth, empty vs populated, URL param combos, error/edge states, implicit side effects), mermaid navigation map labeled with Chinese GUI actions, and atomic GUI skills split into information-extraction + GUI-action (with visual feedback + DB diff) + multi-step composite flows. (2) `site_specs/<slug>.yaml` — canonical structured spec used by trajectory pipeline (build_graph / sample_shapes / write_tasks reads YAML, NOT MD). Both files written together. **GUI-only — no keyboard shortcuts / hotkeys.** Use when user asks to document a site's pages/buttons/navigation/atomic skills, especially after big polish rounds when existing docs are stale. Triggers: '梳理 GUI 页面', '原子技能/能力', '页面跳转图', '每个页面的按钮', '画 UI 骨架', 'document site', 'GUI skills'."
---

# Document Site GUI — Per-Site GUI-Centric Documentation

把一个 WebHarbor mirror site（`sites/<slug>/`）从用户 GUI 视角整理成**两份产物**：

- `~/webvoyager-analysis/site_docs/<slug>.md` — 人读的视觉化文档（8 子块 + mermaid + 原子技能表 + 备注）
- `~/webvoyager-analysis/site_specs/<slug>.yaml` — pipeline 用的 canonical structured spec（pages / edges / atomic_skills / notes）

**两份同步双写**：每次重写站点必须同时产出两份。pipeline 读 YAML，不再读 MD。

## 何时使用

- 用户要求"详细看看每个网站的页面 / 按钮 / 跳转 / 原子能力"
- 一个 site 经历了大改（10 轮 polish / R3-R10 deepening 之类），旧文档过时
- 给 SFT / agent 训练准备"页面有什么、能做什么 GUI 操作、有什么状态变体"的参考
- 多站批量整理（用 subagent 并行）

**不要用于**：纯后端 endpoint 清单（那是另一种风格）、新建站点（用 `clone-website` skill）、出题（用 `design-tasks` skill）。

## ⚠️ 动作空间硬约束：GUI-only

本 skill 产出的文档**只列 GUI 操作**：

允许：`click`（按钮 / 链接 / 心标 / tab / dropdown / 卡片）/ `type`（输入框）/ `submit`（表单）/ `select`（下拉框）/ `hover`（仅必要时展开子菜单）/ `scroll`（必要滚动）/ `back`（浏览器返回 / 站点返回按钮）。

**禁止**：`Cmd+K` / `j+k` / `g+s` / `?` / `/` 聚焦搜索 / `Esc` / `Tab` 等所有键盘快捷键。这些即使 site 实现了，也不进 atomic_skills，仅可在 §6 备注里列作"附带功能"。

详见 memory `feedback-gui-only-no-keyboard`。

## 产物结构

**每站产物两份**：

1. **`site_docs/<slug>.md`** — 人读视觉化文档，预期 50-150 KB
2. **`site_specs/<slug>.yaml`** — pipeline canonical spec，预期 10-30 KB

详细 schema 见 `~/webvoyager-analysis/site_specs/_SCHEMA.md`。

### MD 文档结构（人读）

固定 6 章，模板见 `~/webvoyager-analysis/site_docs/_TEMPLATE.md`：

1. **元信息**：Flask app 行数、模板数、DB、全局 nav 结构、鉴权范围、benchmark 账号、布局风格
2. **页面地图（Page Map）**：表格，每行 = 中文名 / URL / 模板 / 一句话用途 / 鉴权 / 状态变体数（粗估）
3. **每页 GUI 详解**：每个 page 一个 `### 3.x` 小节，内含 **8 子块**：
   - **3.x.1 页面构成**：从上到下分区（顶部 nav / hero / 主内容 / sidebar / footer），描述视觉块
   - **3.x.2 信息展示**：每区可见字段 + 数据来源（哪个 model 哪一列）
   - **3.x.3 GUI 可交互元素**：表格 — 元素 / 位置 / 类型（click/type/select/hover/scroll/back）/ 触发后（跳到哪页 + 后端做啥 + 视觉反馈）
   - **3.x.4 ⭐ 页面状态变体**：列出该 page 的不同 UI 状态（参见下方"状态维度清单"）
   - **3.x.5 ⭐ URL 参数维度**：query string / hash / path param 组合产生的不同页面
   - **3.x.6 ⭐ 错误 / 边缘状态**：404 / 表单验证错误 / 鉴权重定向 / 空数据 / stock-out / 时效失效
   - **3.x.7 ⭐ 隐式副作用**：访问该页面不经显式点击就发生的 DB 写入（view_count++、search_history、last_login 等）
   - **3.x.8 从这一页能跳哪里**：可达 page 列表（含状态变体之间的转换）
4. **mermaid 跳转图**：节点是 `<page>(<state>)` 对（如 `详情(anon)` / `详情(auth, saved)`），**边上写中文 GUI 动作**，**不写后端 endpoint**
5. **原子 GUI 技能（重点）**：
   - 5.1 信息提取（read-only）：所在页 + 状态 / 可见目标 / 提取字段
   - 5.2 GUI 动作（state-changing）：所在页 + 状态 / GUI 操作 / 视觉反馈 + DB diff / 引发的状态切换
   - 5.3 组合技能：多步骤 flow，给出具体点击序列（含状态切换示意）
6. **备注 / 已知坑**：装饰元素（`href="#"`）/ CSRF 例外 / 冻结时钟 / benchmark 账号 / 答案泄露防护 / 资源缺失 / 键盘 hotkey（已知但不进数据）

### 状态维度清单（用于 §3.x.4 页面状态变体）

每个 page 至少检查以下 4 类状态，把每种存在的组合写成一行"触发条件 → 视觉差异"：

| 状态维度 | 示例（详情页 /recipe/<slug>）|
|---|---|
| **登录态** | `(anon)`：心标按钮 → 点击弹"Sign in to save" modal；`(auth)`：心标可直接 toggle |
| **数据状态** | `(auth, not_saved)`：心标空心；`(auth, saved)`：心标实心 + 文字 "Saved" |
| **可用性** | `(in_stock)`：大蓝 Buy 按钮；`(out_of_stock)`：灰 "Notify me" |
| **时间敏感** | `(sale_active)`：红色折扣 banner；`(sale_ended)`：banner 消失 |

不是每个 page 都四种都有，但写文档时**至少检查**这 4 类。每个 page 列 1-6 个状态变体合理；超过 8 个考虑是不是参数空间爆炸了（filter 组合不要展开）。

### URL 参数维度（用于 §3.x.5）

同一 template 配不同 query string / hash 算独立"页面状态"：

| URL | 状态 |
|---|---|
| `/search?q=dessert` | 基础 |
| `/search?q=dessert&sort=time` | 加排序 |
| `/search?q=dessert&filter=veg` | 加筛选 |
| `/search?q=dessert&filter=veg&sort=time&page=2` | 多 facet + 分页 |
| `/recipe/<slug>#reviews` | 详情 + 锚点定位 reviews tab |
| `/recipe/<slug>?servings=8` | 详情 + servings 缩放 |

枚举所有该 page 支持的参数 + 写"参数组合产生什么视觉差异"。

### 错误 / 边缘状态（用于 §3.x.6）

每个 page 检查以下边缘场景，存在就列出：

| 场景 | 表现 |
|---|---|
| 404 不存在 slug | `/recipe/<bad-slug>` → 404 页 + 可能含"Did you mean ..." |
| 表单验证 | 注册时邮箱重复 / 密码太弱 → 红框 + 错误文案 |
| 鉴权重定向 | 匿名访问 `/account` → 跳 `/login?next=/account` |
| 空数据 | 空 wishlist → "Your wishlist is empty" + CTA |
| Stock-out | 无库存商品 → 灰按钮 + 替代品推荐 |
| 时效失效 | 过期 article → "This article has been archived" |
| Rate limit | 短时间多次点心标 → "Too many requests" toast |

### 隐式副作用清单（用于 §3.x.7）

很多 GET 也写 DB——这些 trajectory 看不见但影响后续状态：

| 副作用 | 触发 |
|---|---|
| `view_count += 1` | 每次访问详情页（arxiv / bbc / amazon 等普遍） |
| `SearchHistory` insert | 登录态访问 `/search?q=X`（cambridge / google_search） |
| `ReadingHistory` insert | 登录态访问 article（bbc_news） |
| `last_login` update | 任何 authed 请求 |
| `daily_visit_log` insert | 当日第一次访问 |

把这些标在文档里，让训练 SFT 时能正确判断"读完详情页后 DB 已经不一样了"。

## 工作流

### 准备

```bash
# 备份旧版（如果存在）
mkdir -p ~/webvoyager-analysis/site_docs/archive_v1
cp ~/webvoyager-analysis/site_docs/<slug>.md \
   ~/webvoyager-analysis/site_docs/archive_v1/<slug>.md 2>/dev/null || true

# 体量摸底
wc -l ~/repos/WebHarbor/sites/<slug>/app.py
ls ~/repos/WebHarbor/sites/<slug>/templates/*.html | wc -l
```

### 单站执行步骤（subagent 内部）

1. **拿全部路由（不要 Read 整个 app.py）**：
   ```bash
   grep -nE "^@app\.route|^def " ~/repos/WebHarbor/sites/<slug>/app.py
   ```
   把每条路由分类成 `page` / `action` / `api`，标 `@login_required` 与 `@csrf.exempt`。

2. **逐个 Read 每个 template**（GUI 视角真正信息源）：
   - 先读 `base.html` 看全局壳（nav 项、footer、modal 槽位、flash banner 槽）
   - 每个 page template 通读一次，识别：
     - 顶部到底部的 section 分区
     - 每个 `<form>` 的 action / method + 全部字段（label + name + type + 默认值）
     - 每个 `<button>` / `<a>` 的可见文字 + href / onclick
     - 每个 dropdown / tab / accordion / modal trigger
     - 每个图标按钮（心标、星标、share、bookmark、bell）的位置 + 触发动作
     - **`{% if current_user.is_authenticated %}` 等条件块** → 状态变体来源
     - **`{% if cart_count == 0 %}` / `{% if not results %}` 等数据条件** → 数据状态来源
   - 看 app.py 对应 view function 用 `Read` + `offset`/`limit` 只读那段，**不要全文 Read**
   - 注意 `request.args.get(...)` 调用 → URL 参数维度来源
   - 注意 `flash(...)` / `abort(...)` 调用 → 错误状态来源
   - 注意 view function 内的 `obj.view_count += 1` / `db.session.add(History(...))` → 隐式副作用来源

3. **写文档**：
   - 严格按 6 章模板的结构
   - 每页 **8 子块**（3.x.1 ~ 3.x.8）都要齐全（漏了一个就回去补）
   - mermaid 图节点用 `中文名(状态)` 格式，边写中文 GUI 动作
   - 原子技能两层至少写出 30+ / 20+，组合 flow 至少 5-10 条
   - 全程中文，专有名（endpoint、CSS class、Model 名、按钮标签）保留英文

4. **对比 `archive_v1/<slug>.md`**：找出 v1 没有而新版新增的 page / 按钮 / 子模块，在备注里列清单。

### 批量执行（≥3 站）

并行派 subagent，**每个 agent 负责 3 个站**（用户建议的 batch 大小）：

- 单个 agent 一站会浪费并发；
- 单 agent ≥4 站、或单 agent 跑超大站（app.py >10000 行）容易 stall（实测 Amazon 一次 stall）。

派发 prompt 模板：

```
你要为 WebHarbor 中 3 个站点（<slug1> / <slug2> / <slug3>）的当前最新源码按 GUI 用户视角重写中文文档：
- 写入 ~/webvoyager-analysis/site_docs/<slug1>.md
- 写入 ~/webvoyager-analysis/site_docs/<slug2>.md
- 写入 ~/webvoyager-analysis/site_docs/<slug3>.md
（覆盖旧版，备份在 archive_v1/*.md）

每站源码：~/repos/WebHarbor/sites/<slug>/{app.py, templates/*.html, static/, tasks.jsonl}

策略（避免 stall）：
1. 不 Read 整个 app.py。先 grep 拿全部路由。
2. 重点 Read 每个 template（GUI 信息源）。
3. 看 app.py view function 用 Read + offset/limit 只读那段。

⚠️ GUI-only：动作空间限 click/type/submit/select/hover/scroll/back，不要列键盘快捷键 / Cmd+K / 字母跳转。

严格按 ~/webvoyager-analysis/site_docs/_TEMPLATE.md 6 章 + 每页 8 子块：
  1 页面构成 / 2 信息展示 / 3 GUI 可交互元素 /
  4 ⭐ 状态变体（登录态/数据状态/可用性/时间敏感）/
  5 ⭐ URL 参数维度 /
  6 ⭐ 错误 / 边缘状态 /
  7 ⭐ 隐式副作用 /
  8 跳转出口

每份 50-100 KB。全中文。

每个 site 特别关注 [基于 git log 列出该站最近 commit 加了什么]：
- <slug1>: ...
- <slug2>: ...
- <slug3>: ...

只用 Read / Grep / Glob / Write / Edit，不执行 app。完成后报每文件路径 + page 数 + word count + v1 差异 + 每页状态变体平均数。
```

**run_in_background: true**。等到 task-notification 完成后再派下一批，或一次性把 15 站 / 5 个 agent 全派。

## 关键经验（来自一次完整 15 站重写）

### 避免 stall 的硬规则

- **不要 Read 整个 app.py 当上下文铺垫**。10000 行的 apple/app.py 会把 subagent 的 context 撑爆，最后假装"我有足够理解"然后停转。
- **Templates 才是 GUI 视角的信息源**。app.py 只用 grep + 局部 Read 切片。
- **单 agent 任务上限**：3 个中等站（app=3-6k 行）或 1 个大站（app=10k+ 行）。

### 模板风格的"GUI vs 后端"差异

v1 风格（错示范）：

```markdown
| Path | Method | Endpoint | Template | 类型 |
| `/login` | GET, POST | login | login.html | page+action |
```

v2 风格（GUI 视角 + 状态）：

```markdown
**3.5.1 页面构成**
- 顶部 nav：左 logo "Allrecipes"，右 "Sign In" 按钮
- 中央卡片：标题 "Sign In to Allrecipes"，下方 username + password 两个输入框
- 卡片底部：蓝色 "Sign In" 大按钮 + 小字 "Don't have an account? Sign up"

**3.5.3 GUI 可交互元素**
| 元素 | 位置 | 类型 | 触发后 |
| username 输入框 | 卡片中部 | type | 焦点 + 输入文本 |
| password 输入框 | 卡片中部 | type | 焦点 + 输入文本（密文）|
| "Sign In" 蓝按钮 | 卡片底部 | submit | 成功跳 /account（状态切到 auth）；失败 → (login, error_credentials) 状态 |
| "Sign up" 链接 | 卡片底部小字 | click | → /register |

**3.5.4 页面状态变体**
- (default)：空表单
- (next_query)：URL 带 ?next=/X → "Sign in to continue to X" 副标题
- (error_credentials)：提交错密码 → 红色 banner "Invalid email or password"
- (error_rate_limit)：5 次失败 → "Too many attempts. Try again in 5 minutes"

**3.5.5 URL 参数维度**
- /login → default
- /login?next=/account → 带回跳意图
- /login?reason=session_expired → 副标题 "Your session expired. Please sign in again."

**3.5.6 错误 / 边缘**
- error_credentials：上面已列
- error_rate_limit：上面已列
- 已登录访问：直接 302 跳 /account（不显示登录页）

**3.5.7 隐式副作用**
- 成功登录：last_login 字段 update；session 写 user_id；session_count += 1
```

### Mermaid 图的边标 + 状态节点差异

错示范：`index --> search ("POST /search")`

正确：`index(anon) -- "搜索框 type+Enter" --> search(empty)`、`search(populated) -- "点击第 1 卡片" --> detail(anon)`、`detail(anon) -- "点心标弹 modal" --> login_modal`、`login_modal -- "登录成功" --> detail(auth, not_saved)`

### 原子技能的粒度

- **信息提取技能**："从首页精选卡片读取标题/评分/烹饪时间" 这一粒度，**不是** "search_recipes API"
- **GUI 动作技能**：必须能写出"点哪个按钮 / 填什么字段 / 看见什么视觉反馈 / DB 哪张表 +1 / 引发哪个状态切换"
- **组合 flow**：以"匿名用户搜索 chicken 后保存第 3 个菜谱"这种用户故事粒度，列出具体每一步点击 + 状态切换

### 处理大改后的 site

1. 先 `git log --oneline sites/<slug>/` 看最近 10 个 commit
2. R3-R10 系列 commit message 通常列了新增模块（"add subscribe-save / registry / fresh"）
3. 把这些新模块当作"必须覆盖"的清单写进 subagent prompt
4. v1 / v2 对照能挖出新 page / 新交互 / 装饰链接演化

## 模板维护

`~/webvoyager-analysis/site_docs/_TEMPLATE.md` 是 GUI-centric 写作规范，新加 skill / 修改风格时同步更新它。

## 索引维护

`~/webvoyager-analysis/site_docs/README.md` 有总索引，每加完一站补一行：

```markdown
| <slug> | <upstream> | 400XX / 430XX | N GUI page | S 状态变体 | ✅ [<slug>.md](./<slug>.md) (X KB) |
```

## 已知陷阱

- **subagent stall**：若 600s 无进度，通常是 Read 太大单文件。重派时强调"不要 Read 整 app.py"。
- **archive_v1 双写**：覆盖前必须备份。
- **port realloc**：扩展站 merge 时 control_server.py 会重排 port，文档头的端口要根据当前 merge commit 校验。
- **imdb 之类被合掉的 site**：用户在主动重做的 site 暂不动它的 md。
- **byte-identical reset**：写文档时不要建议改动会破坏这个不变量的东西（如不要写"建议加 view_count 不每次 +1"）。
- **键盘快捷键不进数据**：即使源码里有 Cmd+K / j+k 实现，也只在 §6 备注里提一笔"附带功能，不纳入原子技能"。GUI-only 是硬约束，见 [[feedback-gui-only-no-keyboard]]。
- **状态枚举不要爆炸**：每个 page 列出本质上不同的状态即可（4-8 个），不要把 12 个 filter checkbox 的 2^12 组合都列。filter 组合在原子技能里用 "apply_filter(name=X)" 这种参数化技能表达。
