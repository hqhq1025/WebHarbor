# Cambridge Dictionary

## 基础设施能力

Cambridge Dictionary 镜像适合做精确词典、同义词、翻译、语法和小游戏任务。它有 1,821 个词条、grammar topics、shop items、quizzes、saved words、search history、dictionary、thesaurus、translation、grammar、Plus games、shop 和语言切换。难点不在大规模导航，而在区分 definition、example、translation、grammar rule，并完成小交互。

## 适合泛化的任务族

- 查词：定义、UK IPA、US IPA、例句、义项数量。
- 翻译：中文、法语、西语、德语 UI。
- Thesaurus：词或短语的同义表达。
- Grammar：规则页和例句。
- Plus：image quiz、grammar quiz、word scramble。
- Shop 浏览。

## 站点特化场景

- 比较 UK/US 发音适合做精确抽取。
- 找 word/phrase/idiom 相关项能考察 thesaurus 导航。
- 语法转换任务可以要求 direct 到 indirect 或 active 到 passive 示例。
- 语言切换是 UI 状态任务，不是纯内容检索。

## 逐任务建议

| ID | 原始任务意图 | 基于 WebHarbor 的造题建议 |
| --- | --- | --- |
| Cambridge Dictionary--0 | 在 Cambridge Dictionary 中完成 详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--1 | 在 Cambridge Dictionary 中完成 详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--2 | 在 Cambridge Dictionary 中完成 详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--3 | 在 Cambridge Dictionary 中完成 详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--4 | 在 Cambridge Dictionary 中完成 详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--5 | 在 Cambridge Dictionary 中完成 详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--6 | 在 Cambridge Dictionary 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--7 | 在 Cambridge Dictionary 中完成 详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--8 | 在 Cambridge Dictionary 中完成 排序/Top N。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--9 | 在 Cambridge Dictionary 中完成 详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--10 | 在 Cambridge Dictionary 中完成 详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--11 | 在 Cambridge Dictionary 中完成 详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--12 | 在 Cambridge Dictionary 中完成 详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--13 | 在 Cambridge Dictionary 中完成 路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--14 | 在 Cambridge Dictionary 中完成 详情页抽取、路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--15 | 在 Cambridge Dictionary 中完成 详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--16 | 在 Cambridge Dictionary 中完成 详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--17 | 在 Cambridge Dictionary 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--18 | 在 Cambridge Dictionary 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--19 | 在 Cambridge Dictionary 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--20 | 在 Cambridge Dictionary 中完成 详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--21 | 在 Cambridge Dictionary 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--22 | 在 Cambridge Dictionary 中完成 详情页抽取、路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--23 | 在 Cambridge Dictionary 中完成 详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--24 | 在 Cambridge Dictionary 中完成 详情页抽取、路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--25 | 在 Cambridge Dictionary 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--26 | 在 Cambridge Dictionary 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--27 | 在 Cambridge Dictionary 中完成 详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--28 | 在 Cambridge Dictionary 中完成 排序/Top N。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--29 | 在 Cambridge Dictionary 中完成 评分/评论、路线/距离/附近、站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。这是站点特化交互，适合保留为 targeted benchmark，并要求页面出现可验证完成状态。 |
| Cambridge Dictionary--30 | 在 Cambridge Dictionary 中完成 详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--31 | 在 Cambridge Dictionary 中完成 详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--32 | 在 Cambridge Dictionary 中完成 价格/数值阈值、评分/评论、比较推理、详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--33 | 在 Cambridge Dictionary 中完成 详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--34 | 在 Cambridge Dictionary 中完成 价格/数值阈值、详情页抽取、路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。 |
| Cambridge Dictionary--35 | 在 Cambridge Dictionary 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--36 | 在 Cambridge Dictionary 中完成 详情页抽取、路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--37 | 在 Cambridge Dictionary 中完成 价格/数值阈值、详情页抽取、路线/距离/附近、表格/榜单。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。 |
| Cambridge Dictionary--38 | 在 Cambridge Dictionary 中完成 评分/评论、状态操作、路线/距离/附近、站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 继续造题时可以替换同类实体，并要求 agent 完成操作后回到确认页核对状态。适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。 |
| Cambridge Dictionary--39 | 在 Cambridge Dictionary 中完成 排序/Top N、详情页抽取、路线/距离/附近、站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。 |
| Cambridge Dictionary--40 | 在 Cambridge Dictionary 中完成 价格/数值阈值、详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--41 | 在 Cambridge Dictionary 中完成 排序/Top N。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |
| Cambridge Dictionary--42 | 在 Cambridge Dictionary 中完成 路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。 |

## 扩容前需要补的基础设施

- 词条页增加稳定 summary 区，统一 IPA/definition 的抽取位置。
- Quiz 需要 deterministic final-score confirmation。
- 扩充 thesaurus phrase 词条。
- 如果要大量语言切换任务，需要扩充 UI 语言覆盖。
