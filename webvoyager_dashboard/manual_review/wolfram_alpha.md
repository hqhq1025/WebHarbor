# Wolfram Alpha

## 基础设施能力

Wolfram Alpha 镜像本质上是预计算答案环境。它有 163 条 computation_results、categories、subcategories、topics、favorites、saved queries、notebooks、history、examples、input/result、Pro/pricing/products/about，以及 notebook/favorite 状态流。它不能现场做任意符号计算，造题必须围绕已 seed 的 computation_results，或先扩充 seed DB。

## 适合泛化的任务族

- 数学计算：导数、积分、化简、矩阵、级数、几何、曲线长度、旋转圆锥曲线。
- 物理/工程/材料：电阻率、导热系数、抛体、摆、地磁、发电量。
- 单位/化学：摩尔转换、元素质量百分比。
- 日期、人口、金融比较。
- 健康/日常估算：晒伤、减重、热量、心率储备、代谢属性。
- Notebook/favorite/saved query 状态流。

## 站点特化场景

- 计算并抽取精确值适合 golden task。
- 比较两个 result pods 是 Wolfram 特化价值。
- 把多个计算保存进 notebook 可以扩展成高价值 action task。
- 曲线绘图任务可用，但要保证图像稳定。

## 逐任务建议

| ID | 原始任务意图 | 基于 WebHarbor 的造题建议 |
| --- | --- | --- |
| Wolfram Alpha--0 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--1 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--2 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--3 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--4 | 在 Wolfram Alpha 中完成 比较推理。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--5 | 在 Wolfram Alpha 中完成 路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--6 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--7 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--8 | 在 Wolfram Alpha 中完成 路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--9 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--10 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--11 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--12 | 在 Wolfram Alpha 中完成 路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--13 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--14 | 在 Wolfram Alpha 中完成 比较推理。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--15 | 在 Wolfram Alpha 中完成 价格/数值阈值。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--16 | 在 Wolfram Alpha 中完成 日期/时效、路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--17 | 在 Wolfram Alpha 中完成 价格/数值阈值。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--18 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--19 | 在 Wolfram Alpha 中完成 路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--20 | 在 Wolfram Alpha 中完成 路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--21 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--22 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--23 | 在 Wolfram Alpha 中完成 路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--24 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--25 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--26 | 在 Wolfram Alpha 中完成 路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--27 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--28 | 在 Wolfram Alpha 中完成 路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--29 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--30 | 在 Wolfram Alpha 中完成 路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--31 | 在 Wolfram Alpha 中完成 日期/时效。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--32 | 在 Wolfram Alpha 中完成 价格/数值阈值、站点特化交互。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。这是站点特化交互，适合保留为 targeted benchmark，并要求页面出现可验证完成状态。Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--33 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--34 | 在 Wolfram Alpha 中完成 比较推理、路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--35 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--36 | 在 Wolfram Alpha 中完成 路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--37 | 在 Wolfram Alpha 中完成 价格/数值阈值。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--38 | 在 Wolfram Alpha 中完成 路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--39 | 在 Wolfram Alpha 中完成 路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--40 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--41 | 在 Wolfram Alpha 中完成 状态操作。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 继续造题时可以替换同类实体，并要求 agent 完成操作后回到确认页核对状态。Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--42 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--43 | 在 Wolfram Alpha 中完成 路线/距离/附近。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | 适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--44 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |
| Wolfram Alpha--45 | 在 Wolfram Alpha 中完成 页面导航、答案抽取。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。 | Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。 |

## 扩容前需要补的基础设施

- 建立 seed-generation 流程，否则新题只能围绕现有 163 条 query。
- 数学表达式需要归一化展示和参考答案。
- 结果 pod 加机器可读行和 label。
- 避免实时天气/金融，除非页面显示快照日期。
