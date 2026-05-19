# Hugging Face

## 基础设施能力

Hugging Face 镜像覆盖模型、数据集、Spaces、文档、论文、博客、部署和讨论。它有 678 个 repositories、277 个 authors、39 个 tasks、repo detail、files、commits、discussions、collections、deployment cart、endpoints、pricing、enterprise、blog、papers、docs、classroom、dataset viewer、chat、Inference API，以及 license/library/task/language/modality 筛选。

## 适合泛化的任务族

- 模型/数据集/Space 发现：task、license、library、language、modality、downloads、likes、updated。
- Model card 抽取：size、tensor type、framework、metrics、tags、language。
- Docs 查找：Transformers、TRL、PEFT、Trainer、tokenizer API。
- Inference API：文本生成、句子相似度、embedding。
- Space/chat 交互。
- Dataset viewer 行/字段抽取。
- Deployment cart、endpoints、pricing。

## 站点特化场景

- 网页上的 Inference API 任务很有价值。
- 打开 Space 并提问可以测试嵌入式 app 行为。
- 查文档参数和默认值能测试 docs 导航。
- Dataset viewer 第一行/指定字段任务非常适合结构化评估。

## 逐任务建议

| ID | 原始任务意图 | 基于 WebHarbor 的造题建议 |
| --- | --- | --- |
| Huggingface--0 | 在 Hugging Face 中完成 日期/时效、站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。这是站点特化交互，适合保留为 targeted benchmark，并要求页面出现可验证完成状态。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--1 | 在 Hugging Face 中完成 路线/距离/附近、站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。这是站点特化交互，适合保留为 targeted benchmark，并要求页面出现可验证完成状态。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--2 | 在 Hugging Face 中完成 日期/时效、排序/Top N、站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。这是站点特化交互，适合保留为 targeted benchmark，并要求页面出现可验证完成状态。 |
| Huggingface--3 | 在 Hugging Face 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--4 | 在 Hugging Face 中完成 排序/Top N、详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--5 | 在 Hugging Face 中完成 日期/时效。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--6 | 在 Hugging Face 中完成 路线/距离/附近、站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。这是站点特化交互，适合保留为 targeted benchmark，并要求页面出现可验证完成状态。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--7 | 在 Hugging Face 中完成 日期/时效。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--8 | 在 Hugging Face 中完成 详情页抽取、站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。这是站点特化交互，适合保留为 targeted benchmark，并要求页面出现可验证完成状态。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--9 | 在 Hugging Face 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--10 | 在 Hugging Face 中完成 站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 这是站点特化交互，适合保留为 targeted benchmark，并要求页面出现可验证完成状态。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--11 | 在 Hugging Face 中完成 日期/时效、详情页抽取、路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。 |
| Huggingface--12 | 在 Hugging Face 中完成 日期/时效。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--13 | 在 Hugging Face 中完成 价格/数值阈值、详情页抽取、站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。这是站点特化交互，适合保留为 targeted benchmark，并要求页面出现可验证完成状态。 |
| Huggingface--14 | 在 Hugging Face 中完成 详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--15 | 在 Hugging Face 中完成 状态操作。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 继续造题时可以替换同类实体，并要求 agent 完成操作后回到确认页核对状态。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--16 | 在 Hugging Face 中完成 日期/时效、表格/榜单、站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。适合做表格过滤、排名和聚合题，评估时要求列名、行名和数值一起返回。这是站点特化交互，适合保留为 targeted benchmark，并要求页面出现可验证完成状态。 |
| Huggingface--17 | 在 Hugging Face 中完成 日期/时效、路线/距离/附近、站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。这是站点特化交互，适合保留为 targeted benchmark，并要求页面出现可验证完成状态。 |
| Huggingface--18 | 在 Hugging Face 中完成 状态操作、路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 继续造题时可以替换同类实体，并要求 agent 完成操作后回到确认页核对状态。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--19 | 在 Hugging Face 中完成 日期/时效、详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--20 | 在 Hugging Face 中完成 日期/时效、详情页抽取、站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。这是站点特化交互，适合保留为 targeted benchmark，并要求页面出现可验证完成状态。 |
| Huggingface--21 | 在 Hugging Face 中完成 路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--22 | 在 Hugging Face 中完成 路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--23 | 在 Hugging Face 中完成 日期/时效、排序/Top N。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--24 | 在 Hugging Face 中完成 价格/数值阈值。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--25 | 在 Hugging Face 中完成 路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--26 | 在 Hugging Face 中完成 评分/评论。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--27 | 在 Hugging Face 中完成 路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--28 | 在 Hugging Face 中完成 详情页抽取、站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。这是站点特化交互，适合保留为 targeted benchmark，并要求页面出现可验证完成状态。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--29 | 在 Hugging Face 中完成 日期/时效。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--30 | 在 Hugging Face 中完成 日期/时效。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--31 | 在 Hugging Face 中完成 日期/时效、详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--32 | 在 Hugging Face 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--33 | 在 Hugging Face 中完成 评分/评论、排序/Top N、状态操作、详情页抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 继续造题时可以替换同类实体，并要求 agent 完成操作后回到确认页核对状态。适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。 |
| Huggingface--34 | 在 Hugging Face 中完成 排序/Top N。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--35 | 在 Hugging Face 中完成 日期/时效、路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--36 | 在 Hugging Face 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--37 | 在 Hugging Face 中完成 排序/Top N。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--38 | 在 Hugging Face 中完成 状态操作、路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 继续造题时可以替换同类实体，并要求 agent 完成操作后回到确认页核对状态。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--39 | 在 Hugging Face 中完成 路线/距离/附近、站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。这是站点特化交互，适合保留为 targeted benchmark，并要求页面出现可验证完成状态。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--40 | 在 Hugging Face 中完成 路线/距离/附近、站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。这是站点特化交互，适合保留为 targeted benchmark，并要求页面出现可验证完成状态。Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。 |
| Huggingface--41 | 在 Hugging Face 中完成 价格/数值阈值、日期/时效、站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。这是站点特化交互，适合保留为 targeted benchmark，并要求页面出现可验证完成状态。 |
| Huggingface--42 | 在 Hugging Face 中完成 排序/Top N、路线/距离/附近、站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。这是站点特化交互，适合保留为 targeted benchmark，并要求页面出现可验证完成状态。 |

## 扩容前需要补的基础设施

- 搜索结果页的更新时间和排序要显式稳定。
- 扩充 docs 页面和代码片段。
- Inference API 输出要可复现，或按性质评估。
- Dataset viewer 需要分页/筛选控件来支持更多行级任务。
