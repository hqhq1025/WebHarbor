---
name: perf-optimize
description: "Phase 7: Make WebHarbor mirror sites fast. Profile each site's slowest endpoints with cProfile, then apply 5 categories of fixes (composite SQL indexes, context-processor caching, list pagination, eager-loading to kill N+1, Cache-Control headers + image lazy-loading). Use after deepen/seed when sites work but feel slow, or when verify-site-gui's Playwright TTFB > 200ms on any page. Real numbers: this approach brought google_map 596ms → 4ms (150×), huggingface 661ms → 5ms (130×), coursera /search 48MB → 75KB (645×). Triggers: '加载慢', '页面慢', 'perf', 'slow page', 'optimize', 'TTFB'."
---

# Perf Optimize — Make WebHarbor mirrors fast

让 36 个 mirror 站每个 endpoint TTFB < 50ms / 首页 body < 200KB / list page 真分页。基于 2026-05-27 一轮实践：4 站 TTFB 从 99-661ms 降到 2-30ms（**12-150× 提升**），coursera /search 48.5MB → 75KB。

## 何时使用

- **deepen 收尾后** — Phase 7（在 verify-site-gui Phase 6 之后、发布之前）
- 用户反馈"网站加载慢 / 切页跳转慢"
- `verify-site-gui` harness 报某 page TTFB > 200ms
- 准备给真人 demo / record video 前的最后清理

不要用于：写新 feature（用 [[clone-website]]/[[evolve-env]]）、修 broken page（用 [[verify-site-gui]]）、改前端布局（用 [[harden-env]] gotchas §43）。

## 工作流位置

```
clone-website (1)
   ↓
design-tasks (2)
   ↓
evolve-env (3)
   ↓
harden-env (4)
   ↓
seed-database (5)
   ↓
document-site-gui ⬇
   ↓
verify-site-gui (6)
   ↓
perf-optimize (7) ⬅ 此 skill
   ↓
declare done / ship
```

## 一份 baseline harness

放在 `~/webvoyager-analysis/site_specs/_verify/_perf_baseline.py`：

```python
import urllib.request, time, json, pathlib

def measure(port, urls):
    out = []
    for url in urls:
        # warm + 3 runs，取 median
        for _ in range(1): urllib.request.urlopen(f"http://localhost:{port}{url}", timeout=10).read()
        ts = []
        for _ in range(3):
            t0 = time.time()
            r = urllib.request.urlopen(f"http://localhost:{port}{url}", timeout=20)
            body = r.read()
            ts.append(time.time() - t0)
        out.append({"url": url, "ttft": sorted(ts)[1], "size": len(body), "status": r.status})
    return out

# 36 sites × 5-10 urls = ~300 measurements，5 min 跑完
# 排序 TTFB desc → 找 top 10 worst 优先修
```

输出 `_perf_baseline.json`：per-site median/p95/max TTFB + body size + slow URL list。

## profile 单个 endpoint

```python
import cProfile, pstats, io
from app import app
c = app.test_client()
# warm
c.get('/')
pr = cProfile.Profile()
pr.enable()
for _ in range(5):
    c.get('/path-to-slow-page')
pr.disable()
s = io.StringIO()
pstats.Stats(pr, stream=s).sort_stats('cumulative').print_stats(30)
print(s.getvalue())
```

看 top 30 cumulative time 的 function。常见嫌疑：
- `sqlalchemy.orm.Query.*` 多个 query 累计
- `Jinja2.Template.render` template 渲染太重
- `re.sub` / `json.loads` 大 blob parse

## 5 类 fix（按收益从大到小）

### A. Composite SQL index

**典型问题**：list page 用 `Model.query.filter_by(featured=True).order_by(Model.popularity.desc()).limit(20)`，DB 表 100k+ rows，已有 single-col index 但没有覆盖 `(featured, popularity)` → 全表 scan。

**Fix**:
```python
# 加 model class 内
__table_args__ = (
    db.Index('ix_repository_repo_type_likes_count', 'repo_type', 'likes_count'),
    db.Index('ix_place_is_popular_rating', 'is_popular', 'rating'),
)
```

**byte-id 安全**：所有新 index 用 `ix_` 前缀让 `normalize_seed_db_layout()` re-emit alpha order 时 stable。

**实际收益**：google_map 加 2 个 composite index → 5 个 hot query 各 117ms → 1-2ms，**150× 提升**。

### B. Context-processor / inject_globals 缓存

**典型问题**：`@app.context_processor` 每 request 都跑 `Model.query.all()` 拉 categories / nav data。每 request 多花 30-100ms。

**Fix**:
```python
_CACHE = None
def _cached_nav_categories():
    global _CACHE
    if _CACHE is None:
        _CACHE = Category.query.order_by(Category.id).all()
    return _CACHE

@app.context_processor
def inject_globals():
    return {"nav_categories": _cached_nav_categories()}
```

`/reset/<site>` 会重启 worker，cache 自动重置。

**实际收益**：google_map context_processor 60ms → 0.01ms (cached)。

### C. List page 真分页 (LIMIT + OFFSET)

**典型问题**：`/search` 返回所有 23,000 个 Course 一次 serialize 进 HTML → 48.5MB body / 2.7s。

**Fix**:
```python
PAGE_SIZE = 24
page = int(request.args.get('page', 1))
q = Course.query.order_by(Course.popularity.desc())
total = q.count()
items = q.limit(PAGE_SIZE).offset((page - 1) * PAGE_SIZE).all()
n_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
return render_template('search.html', items=items, page=page, n_pages=n_pages, total=total)
```

模板加 prev/next + page numbers strip:
```jinja
<nav class="pagination">
  {% if page > 1 %}<a href="?page={{ page-1 }}">Prev</a>{% endif %}
  {% for p in range(max(1, page-2), min(n_pages, page+2)+1) %}
    <a href="?page={{ p }}" {% if p==page %}class="active"{% endif %}>{{ p }}</a>
  {% endfor %}
  {% if page < n_pages %}<a href="?page={{ page+1 }}">Next</a>{% endif %}
</nav>
```

**实际收益**：coursera /search 48.5MB → 75KB / 2.73s → 0.07s, **645×/39× 提升**。

### D. N+1 query → eager loading

**典型问题**：
```python
repos = Repository.query.limit(20).all()
for r in repos:
    print(r.author.username)   # 21 queries!
```

**Fix**:
```python
from sqlalchemy.orm import joinedload, load_only

repos = (Repository.query
    .options(joinedload(Repository.author).load_only(Author.username))
    .limit(20).all())   # 1 query
```

特别小心：`joinedload` 用在 large parent table 上会 cartesian explode。这种情况换 `selectinload(Repository.author)` —— 2 query 但 row 数正确。

**注意陷阱**：scoring/IDF 类用 `joinedload` on 23k rows 会拖慢 1.5s+。**只在最终 `.limit(20)` 后面用 `joinedload`**，不要在 `query.all()` 全表 scan 时用。

### E. Static cache + image lazy-load + body size

#### Cache-Control headers
```python
@app.after_request
def add_static_cache(resp):
    if request.path.startswith('/static/'):
        resp.headers['Cache-Control'] = 'public, max-age=86400, immutable'  # 直接赋值
    return resp
```

⚠️ **Werkzeug 陷阱**（gotcha #44）：Flask 静态 blueprint 预先 set `Cache-Control: no-cache`，`headers.setdefault(...)` 是 no-op。**必须 direct 赋值**才覆盖。

#### Image lazy-load (全 site)
```bash
for s in sites/*/; do
  find $s/templates -name '*.html' -exec sed -i \
    's/<img \(src=\)/<img loading="lazy" decoding="async" \1/g' {} \;
done
```

#### 图片宽高（防 layout shift）
```html
<img loading="lazy" width="240" height="160" src="...">
```

#### 控制 body 大小
- list page LIMIT 24
- 不要 inline base64 / inline SVG 巨型 blob
- 不要在 template loop 渲染 JSON column blob

## 验证

```bash
# 1. baseline measurement
python3 site_specs/_verify/_perf_baseline.py

# 2. per-route verify (after each fix)
for i in 1 2 3; do
  curl -s -o /dev/null -w "%{time_starttransfer}s %{size_download}\n" \
    http://localhost:43010/models
done

# 3. cache header verify
curl -I http://localhost:43010/static/css/main.css | grep Cache-Control
# 期望: Cache-Control: public, max-age=86400, immutable

# 4. image lazy ratio (homepage)
curl -s http://localhost:43010/ | python3 -c "
import sys
h = sys.stdin.read()
imgs = h.count('<img')
lazy = h.count('loading=\"lazy\"')
print(f'{lazy}/{imgs} = {lazy/imgs:.1%}' if imgs else 'no imgs')
"
# 期望: ≥ 90%
```

## 单站 fix flow

```bash
SITE=huggingface
PORT=43010

# 1. profile
docker exec wh-r10 python3 -c "
import sys; sys.path.insert(0, '/opt/WebSyn/$SITE')
import cProfile, pstats, io
from app import app
c = app.test_client(); c.get('/')
pr = cProfile.Profile(); pr.enable()
for _ in range(5): c.get('/')
pr.disable()
s = io.StringIO()
pstats.Stats(pr, stream=s).sort_stats('cumulative').print_stats(20)
print(s.getvalue())
"

# 2. identify top bottleneck → apply 5 类 fix 之一

# 3. local fix on app.py / model / template

# 4. byte-id safe deploy (index changes need DB rebuild on instance/)
cd ~/repos/WebHarbor
# if index added: cold-rebuild instance/ via app boot
docker exec wh-r10 python3 -c "
import sys; sys.path.insert(0, '/opt/WebSyn/$SITE')
import os; os.remove('/opt/WebSyn/$SITE/instance/$SITE.db')
from app import app
with app.app_context():
    from app import db
    db.create_all()
    # re-run seed if needed
"
# copy resulting instance/ back to seed
docker exec wh-r10 cp /opt/WebSyn/$SITE/instance/$SITE.db /opt/WebSyn/$SITE/instance_seed/

# 5. verify md5
docker exec wh-r10 md5sum /opt/WebSyn/$SITE/instance/$SITE.db /opt/WebSyn/$SITE/instance_seed/$SITE.db

# 6. docker cp app.py + sync
docker cp sites/$SITE/app.py wh-r10:/opt/WebSyn/$SITE/
docker cp sites/$SITE/instance_seed/*.db wh-r10:/opt/WebSyn/$SITE/instance_seed/
docker cp sites/$SITE/instance/*.db wh-r10:/opt/WebSyn/$SITE/instance/
curl -X POST http://localhost:8311/restart/$SITE

# 7. re-measure
for i in 1 2 3; do
  curl -s -o /dev/null -w "%{time_starttransfer}s\n" http://localhost:$PORT/
done
```

## 防止再发生

- deepen / clone-website subagent prompt 加：
  ```
  新加 list page handler 必须有 LIMIT + pagination
  新加 model query in context_processor 必须 cache
  新加 SQL pattern 检查是否需要 composite index
  ```
- verify-site-gui harness 每次 run 跑 perf baseline + 比较前次。退化 > 2× 报警
- CI 加 `_perf_baseline.py` smoke：median TTFB > 100ms / total body > 500KB 都报警

## 2026-05-27 实测收益

| Site | Top endpoint | Before | After | 提升 |
|---|---|---:|---:|---:|
| google_map | / | 596ms | 4ms | **150×** |
| huggingface | / | 661ms | 5ms | **130×** |
| github | / | 99ms | 2.5ms | 40× |
| google_flights | / | 344ms | 30ms | 12× |
| coursera | /search | 2730ms / 48.5MB | 70ms / 75KB | **39× / 645×** |

总：4 大-DB 站 + 1 search killer 修后，全 36 站 median TTFB < 30ms，无 > 100ms 异常。

## 已知陷阱

- **不要在 N+1 高发 query 上盲加 joinedload** — cartesian explode 可能让性能更差。先 EXPLAIN QUERY PLAN 看 SQLite 实际执行。
- **不要在 search 类全表 scan 上加 joinedload** — IDF 算法+eager join 1.5s+。改成 LIMIT 完再 joinedload。
- **加 composite index 后必须 cold-rebuild DB** — 只 ALTER 加 index 但不重 seed 也行，但 byte-id reset 会因为 index alpha-order 不一致而 fail。正确流程：rebuild instance/ → cp 到 instance_seed/ → 双 md5 一致。
- **context_processor cache 不能用 mutable default arg** — 用 module-level `_CACHE = None` + lazy fill。
- **`/reset/<site>` 会破坏 cache** — 这是 by-design（test 间隔离）。生产监控考虑 hit ratio。

## 索引

每次 perf pass 完成后在 `~/webvoyager-analysis/site_specs/_verify/_perf_baseline.md` 写一行：

```markdown
| 2026-05-27 | <slug> | <endpoint> | <before>ms | <after>ms | <commit> |
```
