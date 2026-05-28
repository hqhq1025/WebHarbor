# tools/harvest — 真站 Harvest 工具集（v8 / 26 工具 / 15 维度）

WebHarbor 真站采集套件，与 `.claude/skills/harvest-real-components/SKILL.md` 配套使用。

## 工具一览

### 抓取（3）
- `harvest.py` — 单 URL Playwright 抓（HTML + fragments + structured + xhr + locales + headers）
- `harvest_spider.py` — BFS 多页爬 + SQLite checkpoint resume
- `harvest_retry.py` — 单页手动 retry

### 维度抽取器（15）
| 工具 | 维度 |
|---|---|
| extract_sitemap.py | 6 Session/sitemap |
| extract_forms.py | 5 表单 |
| extract_facets.py | 4 过滤面板 |
| extract_image_urls.py | 3 图像 |
| extract_sprites.py | 3 SVG sprite |
| extract_audio_urls.py | 7 音频 |
| extract_video_urls.py | 8 视频 |
| extract_icons.py | 9 图标 |
| extract_animations.py | 10 动画 |
| extract_code_blocks.py | 11 代码 |
| extract_metadata_extruct.py | 12 全语义层 (extruct OSS) |
| extract_api_endpoints.py | 13 API endpoints |
| extract_server_state.py | 14 SSR/SPA state |
| extract_websockets.py | 15 WebSocket/SSE |
| extract_nav_graph.py | 4 跳转 |

### 重处理（2）
- `reprocess_structured.py` — 离线 JSON-LD / state / article / BreadcrumbList
- `content_extract.py` — trafilatura wrapper

### 助手（6）
- `infer_cdn_pattern.py` — 推 CDN 模板
- `index_site.py` — 重生 `_index.json`
- `index_pool.py` — image URL SQLite FTS5 池
- `search_local.py` — SearXNG localhost wrapper
- `download_samples.py` — 真样本下载验证（magic-byte 校验）
- `audit_dimensions.py` — 跨 96 站 15 维度 markdown 覆盖表

## 安装依赖

```bash
pip install --break-system-packages \
    playwright extruct curl_cffi ultimate-sitemap-parser \
    warcio trafilatura
playwright install chromium
```

## 默认 snapshots 路径

工具默认写到 `~/webvoyager-analysis/real_components/snapshots/<site>/<page>/`。
建议在大磁盘（如 `/datadrive/harvest/`）建实际目录，软链回去：

```bash
mkdir -p /datadrive/harvest/snapshots
ln -s /datadrive/harvest/snapshots ~/webvoyager-analysis/real_components/snapshots
```

## 工作流（单站）

```bash
SITE=allrecipes_com
URL=https://www.allrecipes.com/

# 1. 抓 home + 关键 page
python3 harvest.py $SITE home "$URL"

# 2. 站级 6 老维度
python3 extract_sitemap.py $SITE
python3 extract_forms.py $SITE
python3 extract_facets.py $SITE
python3 extract_image_urls.py $SITE
python3 extract_sprites.py $SITE
python3 extract_nav_graph.py $SITE
python3 reprocess_structured.py $SITE
python3 content_extract.py --all snapshots/$SITE

# 3. R01+ 新维度
python3 extract_audio_urls.py $SITE
python3 extract_video_urls.py $SITE
python3 extract_icons.py $SITE
python3 extract_animations.py $SITE
python3 extract_code_blocks.py $SITE
python3 extract_metadata_extruct.py $SITE
python3 extract_api_endpoints.py $SITE
python3 extract_server_state.py $SITE
python3 extract_websockets.py $SITE

# 4. helper
python3 infer_cdn_pattern.py $SITE --top-cdns 5
python3 index_site.py $SITE
python3 download_samples.py $SITE --per-dim 2
```

## 跨站 audit

```bash
python3 audit_dimensions.py > /tmp/coverage.md
```

输出 markdown 表：每站 × 15 维度 × `pages / extruct / forms / facets / nav_nodes / images / sprites / sitemap / audio / video / icons / anim / code / api_calls / state_kb / ws_streams`。

## 反爬 fallback 链（harvest.py 自动）

1. Playwright Chrome 131 stealth + UA + sec-ch-ua + webdriver-undef（默认）
2. HTTP/2 protocol error → curl --http1.1
3. bot_block 检测命中 → **curl_cffi chrome131** TLS+JA3（drugs.com Akamai 验证通）
4. 仍 block → Web Archive (wayback.html)
5. 仍 block → 写 `FALLBACK_NEEDED.md`，下游 agent 用 Exa MCP 拿 markdown

## 30 轮迭代历史

详见同 repo 的 `.claude/skills/LESSONS-2026-05-R01.md` 到 `LESSONS-2026-05-R11-R30.md`。
51 patches / 11 新工具 / 6 → 15 维度演化全程。
