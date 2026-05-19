# WebHarbor 造数据前的稳定性审计

这份文档回答一个问题：基于 WebHarbor 继续造 WebVoyager 风格数据时，哪些内容是固定的，哪些会随机，哪些会随日期或用户状态变化。结论会直接影响任务生成策略。

## 总体判断

WebHarbor 不是完全静态网页集合。它是 15 个 Flask 站点，每个站点有 SQLite seed DB、模板、静态资源、登录态/购物车/收藏等状态。`/reset/<site>` 会把 runtime DB 从 `instance_seed/` 还原，适合 rollout 训练。

稳定性分四类：

1. **固定 seed 数据**  
   SQLite 里的实体、字段、绝大多数详情页内容是固定的。最适合从这里反向生成任务。

2. **构建期随机，但 seed 后固定**  
   很多 `seed_data.py` 用 `random.seed(...)` 或随机生成评论、价格、图片、评分。只要 seed DB 不重建，这些值就是固定的。重新生成 assets/DB 后才会变。

3. **请求时随机**  
   首页推荐、相关内容、部分搜索结果 count/search time 会在每次请求变化。不能用来做精确答案，除非先固定逻辑。

4. **用户状态或时间状态**  
   登录、购物车、收藏、历史记录、notebook、booking、checkout 会随操作改变。它们适合做 action tasks，但必须依赖 `/reset` 清理状态。`datetime.utcnow()` / `date.today()` 会让“今天、最近、未来日期”相关任务漂移，除非站点有镜像日期锚点。

## 每站稳定性表

| Site | 固定部分 | 随机/变化部分 | 日期锚点 | 造题建议 |
| --- | --- | --- | --- | --- |
| Allrecipes | Recipe、Category、Review、Nutrition、Recipe Box/Meal Plan/Shopping List schema 固定 | 搜索排序内部有 deterministic shuffle；不是每次随机，但同 query 下顺序被人为打散 | 无强镜像日期；created_at 多为 seed/runtime 字段 | 适合从 recipe DB 反向生成约束题。不要依赖首页位置；可以依赖搜索结果和详情字段。 |
| Amazon | Product、Category、Review、Policy、Cart/Order/Wishlist schema 固定 | 首页 `order_by(random())` 每次刷新会换推荐；搜索内部按 query 做 deterministic shuffle；订单号和配送日期 runtime 随机 | 无强镜像日期 | 适合商品搜索、筛选、详情、加购。不要用首页 deal 的精确位置做 gold；首页题只能做开放题或先固定首页随机。 |
| Apple | Product、SupportArticle、TradeInValue、配置选项固定 | 购物车 session、订单号使用 secrets；部分日期用当前时间 | 无强镜像日期 | 适合产品比较、配置报价、support/trade-in。避免“latest”除非题面绑定明确型号。 |
| ArXiv | Paper、Category、versions、help/store/blog 大多固定 | view/download/star_count 在 seed 时随机；related papers 用 `func.random()`；export id runtime 随机 | 有 `mirror_today`，来自最大 submitted_date | 适合分类、日期窗口、版本、help 文档。不要用 related/random 推荐做精确题。 |
| BBC News | Article、Category、Sport/Market/Audio 内容大多固定 | must-read、related articles 用 `func.random()`；digest id 随机；seed 中部分发布时间随机 | 有局部 fixed/relative 逻辑，但仍有 `datetime.utcnow()` | 适合文章和体育表格。新闻“latest/recent”要绑定页面日期或固定文章标题。 |
| Booking | Property、City、Landmark、Review、amenity flags、currency rates 固定 | seed 期大量随机生成价格/评分/amenity/reviews，但 seed 后固定；购物车/booking/saved state runtime 变化；默认日期用 `date.today()` | 有一些 mirror date/当前年逻辑，但默认入住日期会随真实日期走 | 适合从 DB 反向生成酒店题。题面日期必须显式给出；不要依赖默认日期。 |
| Cambridge Dictionary | Word、GrammarTopic、ShopItem、Quiz schema 固定 | Word scramble 每次随机选词/洗牌；语言选择存在 session | 有 current_year，但不影响词条 | 适合词条/翻译/grammar 精确字段。Quiz/game 任务要接受交互随机或改成固定题。 |
| Coursera | Course、Partner、Module、SubCourse、Review 固定 | seed 里部分图片/评论可能随机；wishlist/enrollment/review state runtime 变化 | 有 current_year，课程 sort_date 固定 | 适合课程搜索、module、partner、review distribution。状态题需要 reset 后验证。 |
| ESPN | Sport、Team、Game、Player、Stats、Articles、Standings 固定 | 基本无请求时随机；seed_data 里有固定赛季/日期内容 | 有强镜像日期 banner：April 10, 2024 | 很适合固定日期体育表格/赛程/roster/stat 任务。latest/today 应按 banner 解读。 |
| GitHub | Repo、User、Topic、Issue、Commit、Pricing/Skills 固定 | 基本无请求时随机；登录态 star/watch/fork/follow 会变 | 有强镜像日期：May 15, 2024 | 适合 qualifier 搜索、commit/release/issues/pricing。日期任务应相对镜像日期。 |
| Google Flights | Airport、Flight、Booking/Track/SavedSearch schema 固定 | seed 中航班大规模随机生成，但 seed 后固定；tracking/booking/payment state runtime 变化 | 有 mirror/reference date 逻辑；部分 date overlay 会替换年份 | 最适合批量生成。必须先查询航班表确认 route/date/cabin/stops 有结果。 |
| Google Map | Place、City、Route、Review、Category 固定 | seed 时随机坐标/评分/评论/地址，但 seed 后固定；trip/save/timeline state runtime 变化 | 有大量 anchor/mirror date 辅助逻辑 | 适合附近搜索、路线、营业时间、评论。生成前要处理地点消歧义和 radius。 |
| Google Search | Topic、SearchResult、PAA、RelatedQuery、KnowledgeFact 固定 | 搜索结果 count/time 每次随机；Lucky/random topic/related topic 用 `func.random()`；history/bookmark state 会变 | 缺强全站日期锚点；很多原题是 current/latest | 风险最高。只适合从已 seed topic/cache 造题；current/latest 必须改成快照题。 |
| Hugging Face | Repo、Author、Task、Docs、Blog、Dataset Viewer 大多固定 | seed 用固定 random；注册头像 random；endpoint id runtime random | 有强镜像日期：April 25, 2026 | 适合模型/数据集/文档/API/Dataset Viewer。搜索更新时间要按镜像日期。 |
| Wolfram Alpha | ComputationResult、Topic、Category 固定 | SECRET_KEY runtime；notebook/favorite/history state 会变；少量 user seed 时间用 utcnow | 无强全站日期；部分 query 是 current/weather | 只能围绕已 seed computation_results 造计算题。实时天气/金融类要改成快照或补固定结果。 |

## 造数据策略

### 1. 任务应该从 DB 反向生成

不要先让模型写自然语言题，再去网页上碰答案。应先从 seed DB 找到答案实体，再生成题面。

例如 Booking：

1. 查询满足 `city=Paris AND breakfast=True AND rating>=9` 的 property。
2. 确认搜索 URL 能显示该 property。
3. 生成题面：`Find a Paris hotel...`
4. 期望答案记录 property name、rating、price、amenity。
5. Playwright 验证页面上能找到这些字段。

### 2. 每个任务要记录稳定性标签

建议给任务加这些标签：

- `fixture_fixed`: 答案完全来自 seed DB。
- `request_random`: 页面刷新会随机变化。
- `session_state`: 需要登录、购物车、收藏或历史。
- `date_anchor`: 依赖镜像日期。
- `real_time_risk`: 原题像实时网页，必须改成快照题。
- `asset_sensitive`: 依赖图片或视觉资源。

### 3. 先造高稳定、高产站点

第一阶段优先：

1. Google Flights
2. Booking
3. Amazon
4. Google Map
5. ESPN

这些站点的数据表丰富，任务可参数化，验证也相对明确。

第二阶段：

1. ArXiv
2. GitHub
3. Hugging Face
4. Coursera
5. Cambridge Dictionary
6. Allrecipes

这些适合内容检索和详情抽取，但需要更精细的字段验证。

第三阶段谨慎做：

1. Google Search
2. BBC News 的“latest/current”新闻题
3. Wolfram Alpha 的实时天气/金融题

这些题必须先快照化。

## 每条新任务的最小元数据

```json
{
  "site": "booking",
  "task_family": "hotel_search_with_amenity_filters",
  "start_url": "http://localhost:40005/",
  "instruction": "Find a Paris hotel ...",
  "expected_answer": {
    "property_name": "...",
    "rating": 9.1,
    "amenities": ["breakfast", "free WiFi"]
  },
  "validation": {
    "must_appear": ["...", "Breakfast included", "9.1"],
    "state_check": null
  },
  "stability": {
    "fixture_fixed": true,
    "request_random": false,
    "session_state": false,
    "date_anchor": true,
    "real_time_risk": false
  },
  "difficulty": 6
}
```

## 需要优先补的基础设施

1. 每个站点统一暴露 `mirror_today`。  
   GitHub/HF/ESPN 做得比较好，Amazon/Apple/Wolfram/Google Search 还不够统一。

2. 每个搜索结果页显示稳定 result count。  
   Booking、Coursera、GitHub、Google Search、ArXiv 都会受益。

3. 为状态型任务增加确认页。  
   cart、wishlist、saved search、notebook、booking、meal plan 都需要稳定摘要。

4. 建一个任务可行性验证器。  
   输入 task spec，自动跑 Playwright，检查目标字段是否可见、是否有 4xx、是否出现多答案。

5. 把请求时随机从 gold 任务中剥离。  
   首页随机推荐、related random、search count random 只能做开放探索题，不能做严格答案题。

## 当前最重要的判断

WebHarbor 可以造数据，但不能把所有页面当静态快照用。它更像一个小型可控互联网：DB 是固定世界，页面有一部分随机展示层，用户状态会随操作变化，日期有些站点固定、有些站点仍读真实当前时间。

造高质量数据的关键不是多写题，而是先给每个任务标出稳定性来源。只要这个边界建好，WebHarbor 可以从 WebVoyager 的 643 题扩成几千条可靠任务；如果忽略这个边界，数据会混入大量漂移题和不可复现题。

