# Google Search

## 基础设施能力

Google Search 镜像适合做受控 SERP 推理，但也是风险最高的站点。它有 170 个 topics、1,170 条 search results、647 个 related queries、575 个 knowledge facts、319 个 PAA questions、bookmarks、collections、alerts、history，以及 images/videos/news/maps/shopping/books/finance 垂直搜索和 external-cache snapshots。WebVoyager 原题中很多 Google 任务依赖实时网页或外站，造题时必须显式快照。

## 适合泛化的任务族

- 从 knowledge panel 或 snippet 找事实。
- 选择正确来源并打开 cached external page 抽取字段。
- 使用 images/news/videos/shopping/books/finance 垂直搜索。
- PAA 和 related queries 探索。
- Bookmark/history/collection 状态任务。
- Cached external-page 阅读任务。

## 站点特化场景

- 在干扰结果中选择正确来源最适合 SERP benchmark。
- 打开缓存外页抽取细节比只读 snippet 更有针对性。
- Google apps/advanced/settings 能覆盖站点特化 UI。
- Twitter/Reddit/YouTube/login/current stats 类任务必须单独审计。

## 逐任务建议

| ID | 原始任务意图 | 基于 WebHarbor 的造题建议 |
| --- | --- | --- |
| Google Search--0 | 在 Google Search 中完成 日期/时效。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--1 | 在 Google Search 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--2 | 在 Google Search 中完成 日期/时效。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--3 | 在 Google Search 中完成 评分/评论、排序/Top N。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--4 | 在 Google Search 中完成 站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 这是站点特化交互，适合保留为 targeted benchmark，并要求页面出现可验证完成状态。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--5 | 在 Google Search 中完成 评分/评论、日期/时效、站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。这是站点特化交互，适合保留为 targeted benchmark，并要求页面出现可验证完成状态。 |
| Google Search--6 | 在 Google Search 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--7 | 在 Google Search 中完成 详情页抽取、路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--8 | 在 Google Search 中完成 价格/数值阈值、排序/Top N。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--9 | 在 Google Search 中完成 评分/评论。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--10 | 在 Google Search 中完成 排序/Top N。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--11 | 在 Google Search 中完成 路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--12 | 在 Google Search 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--13 | 在 Google Search 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--14 | 在 Google Search 中完成 路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--15 | 在 Google Search 中完成 状态操作、路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 继续造题时可以替换同类实体，并要求 agent 完成操作后回到确认页核对状态。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--16 | 在 Google Search 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--17 | 在 Google Search 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--18 | 在 Google Search 中完成 日期/时效。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--19 | 在 Google Search 中完成 日期/时效、排序/Top N。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--20 | 在 Google Search 中完成 日期/时效。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--21 | 在 Google Search 中完成 价格/数值阈值、排序/Top N。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--22 | 在 Google Search 中完成 排序/Top N。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--23 | 在 Google Search 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--24 | 在 Google Search 中完成 评分/评论、状态操作、路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 继续造题时可以替换同类实体，并要求 agent 完成操作后回到确认页核对状态。适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。 |
| Google Search--25 | 在 Google Search 中完成 日期/时效。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--26 | 在 Google Search 中完成 日期/时效。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--27 | 在 Google Search 中完成 日期/时效。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--28 | 在 Google Search 中完成 评分/评论。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--29 | 在 Google Search 中完成 日期/时效、站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。这是站点特化交互，适合保留为 targeted benchmark，并要求页面出现可验证完成状态。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--30 | 在 Google Search 中完成 日期/时效、排序/Top N。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--31 | 在 Google Search 中完成 评分/评论。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--32 | 在 Google Search 中完成 日期/时效。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--33 | 在 Google Search 中完成 日期/时效、路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--34 | 在 Google Search 中完成 日期/时效、路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--35 | 在 Google Search 中完成 日期/时效、路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--36 | 在 Google Search 中完成 日期/时效、路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--37 | 在 Google Search 中完成 日期/时效、排序/Top N、路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。 |
| Google Search--38 | 在 Google Search 中完成 日期/时效、比较推理。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--39 | 在 Google Search 中完成 排序/Top N。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--40 | 在 Google Search 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--41 | 在 Google Search 中完成 日期/时效。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |
| Google Search--42 | 在 Google Search 中完成 价格/数值阈值、比较推理、路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。 |

## 扩容前需要补的基础设施

- Knowledge panel 事实题要把 answer token 明确显示在页面上。
- 所有 current/latest 任务都要快照日期和值。
- 扩充 YouTube/Reddit/Twitter/GitHub 类 external cache。
- SERP topic 增加 source/date badge。
