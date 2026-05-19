#!/usr/bin/env python3
"""Rewrite manual review Markdown into readable Chinese source documents."""
from __future__ import annotations

import os
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "manual_review"
WEBVOYAGER_ROOT = Path(os.environ.get("WEBVOYAGER_ROOT", ROOT.parent.parent / "WebVoyager")).expanduser()

SITE_TEXT = {
    "allrecipes": ("Allrecipes", "Allrecipes 镜像适合做菜谱检索和轻量状态操作。当前 seed DB 有 222 条菜谱、9,629 条评论、14 个分类，并支持 recipe box、meal plan、shopping list 等状态流。页面覆盖搜索、分类、菜谱详情、最新评论、营养信息、食材、做法、1960s collection、Dinners、Occasions、Allstars 等入口。造题时不要只问单点事实，应该把饮食标签、食材、菜系、评分、评论数、准备/烹饪/总时间、热量、份数、营养、最新评论和集合导航组合起来。", ["多条件菜谱检索：饮食标签、食材、时间、评分、评论数一起约束。", "详情页证据抽取：食材、步骤、营养、最新评论、份数、温度、保存方式。", "集合和栏目导航：Dinners、Occasions、1960s collection、Allstars、分类页。", "状态操作：保存到 recipe box、创建购物清单、把菜谱食材加入清单、加入 meal plan。", "比较选择：按热量、评论数、准备时间、总时间在多个候选中做选择。"], ["具体烹饪规划：在时间预算内选一道晚餐，加入周五晚餐，再创建购物清单。", "营养对比：同一主食材下找不同热量区间的菜谱，比较热量、碳水和蛋白质。", "评论敏感推荐：找高分菜谱并引用最新或最高赞评论。", "节日/场景浏览：从 Occasions 进入，找特定节日栏目和代表菜谱。"], ["把评分、评论数、时间、热量、饮食标签、食材数量等高级筛选显式放到 UI。", "增加购物清单和 meal plan 的稳定确认页，方便评估状态是否真的改变。", "把营养信息统一成结构化表格。", "补更多集合页，减少任务对搜索框的依赖。"]),
    "amazon": ("Amazon", "Amazon 是当前最适合做电商任务的镜像之一。它有 407 个商品、8,146 条评论、购物车、愿望单、订单、地址、支付方式、退货、checkout、商品详情、分类页、搜索、筛选、排序、Top review、变体、成色、免运费、免费退货和 feature tags。适合做从搜索、筛选、读详情到加购、保存和查政策的完整购物任务。", ["结构化商品检索：价格、评分、评论数、品牌、成色、免运费、免费退货、颜色、尺码、年份、标签。", "商品详情抽取：保护计划、退货政策、变体数量、配送政策、Top review、规格。", "购物动作流：选准变体后加购物车、保存愿望单、进入 checkout、重新下单、发起退货。", "比较购物：按价格、评分、评论数选 Top N 或最便宜候选。", "分类浏览：Deals、Bestsellers、Kindle Store、Prime、子分类页。"], ["模糊搜索后筛选：搜索结果里有干扰项，agent 必须应用筛选并读规格。", "变体正确性：加购前必须确认颜色、尺码、容量、成色。", "政策理解：免费退货、保护计划、配送和退货步骤。", "评论驱动购买：先找商品，再总结 Top review 或负面评论。"], ["详情页增加稳定的商品事实表，避免尺寸、电池、接口、屏幕等规格只藏在标题里。", "购物车增加清晰的变体和数量摘要，方便评估动作任务。", "减少首页随机性，或记录 seed random state。", "补负面评论、关键问答和评论筛选，支持更丰富的评论理解任务。"]),
    "apple": ("Apple", "Apple 镜像覆盖产品、支持、trade-in、配置、购物和取货。它有 80 个产品、trade-in value、support articles、购物车、wishlist、地址、支付、产品配置、搜索、类别页、维修支持、pickup、compare、Apple Music、Vision Pro 和配件页。它的强项不是大目录搜索，而是产品比较、配置价格、支持文档、trade-in 和 Apple 特有导航。", ["产品比较：价格、屏幕、芯片、颜色、存储、重量、电池、视频规格、slogan。", "配置和购物：型号、芯片、内存、存储、颜色、联网方式、最终价格和加购。", "支持文档：维修方式、忘记密码、系统兼容、Watch 更新。", "Trade-in：旧设备型号和状态对应回收价值。", "门店取货：ZIP 搜索、最近门店和库存状态。"], ["Apple support 问答可以考察非电商导航和精确抽取。", "配置和价格差任务适合做高难度 targeted benchmark。", "跨代产品比较能测试多页面综合。", "配件生态任务适合覆盖 Vision Pro、Pencil、Folio、AirPods、HomePod。"], ["加一个稳定的镜像日期，或避免生成任务使用 latest。", "配置流程需要清晰的最终价格和选项摘要。", "所有产品类别都应有统一 tech spec 表。", "Pickup 结果应有稳定排序和可验证库存状态。"]),
    "arxiv": ("ArXiv", "ArXiv 镜像适合做研究网站任务。它有 1,721 篇论文、分类、library/star/export 状态、评论、alerts、搜索、高级搜索、分类 taxonomy、论文详情、HTML/PDF/source 入口、帮助页、商店、博客、新闻、作者页和引用导出。造题时应把论文元数据和站点运营页面结合起来。", ["按分类、日期、标题、摘要、journal ref 检索论文。", "从论文详情抽取作者、摘要、提交日期、版本、图表/公式数量、作者单位和格式入口。", "帮助文档任务：撤稿、多语言摘要、图格式、订阅邮件。", "站点元信息：新闻、博客、领导团队、Cornell 链接、商店。", "状态任务：保存到 library、star、导出引用、加入商店购物车。"], ["限定分类 vs 全站搜索的结果对比。", "日期窗口计数：某分类某日期范围内满足条件的论文数。", "版本历史：查 v2/v3 提交日期并与 v1 对比。", "HTML/PDF/source 可用性判断。"], ["加显式镜像日期，所有 latest/yesterday/week 任务都以它为准。", "外部 Cornell 页面需要镜像，否则避免离开本地环境。", "搜索结果页应稳定显示 count。", "如果扩展论文 HTML 阅读任务，需要更多 HTML 内容样本。"]),
    "bbc_news": ("BBC News", "BBC News 镜像适合做新闻栏目导航、文章阅读和体育/市场数据任务。它有 360 篇文章、55 个分类、搜索、体育页、排行榜、市场数据、音频/播客、文化、旅行、世界地区、科技、AI、天气、reading list、digest 和 bookmarks。新闻类任务要避免过度依赖“最新”，最好绑定栏目、标题、日期或表格。", ["栏目导航：World、Asia、Africa、Business、Technology、AI、Travel、Culture、Sport、Weather。", "文章抽取：标题、作者、日期、地区、要点、首图、主题。", "体育数据：排行榜、赛程、球队、比赛开始时间、赛马 runners。", "音频/播客：featured、new releases、best podcasts。", "市场数据来源和 attribution。"], ["栏目到头条再到摘要，是稳定的中等难度任务。", "图片理解任务可用，但要先保证图片资产完整。", "体育表格计数/排序比开放新闻摘要更容易评估。", "Reading list/digest 可以扩展成状态任务。"], ["增加站点当前日期和时间。", "文章页显示 author/date/section/region chips。", "修复缺失图片后再扩大视觉任务。", "体育表格需要稳定 ID 和列名。"]),
    "booking": ("Booking", "Booking 是高价值任务生成环境。它有 325 个房源、1,289 条评论、33 个城市、68 个地标、booking/cart/checkout、收藏、支付方式、评论、城市/类别/房型页、搜索、货币切换、设施、品牌、距离排序、海滩距离、地标距离、文章、Genius/deals 和客服内容。它能覆盖目的地、日期、人数、房间数、设施、评分、价格、距离、品牌、货币和预订动作。", ["酒店搜索：目的地、日期、成人/儿童、房间数。", "设施筛选：早餐、WiFi、空调、停车、健身房、Spa、泳池、机场接送、宠物友好、自行车。", "排序/排名：价格、评分、星级、中心距离、海滩距离、地标距离、评论数。", "货币任务：USD/CNY/EUR/GBP/JPY 对比。", "客服和旅行文章任务。", "状态流：加入 bag、checkout、取消/重新预订、收藏房源。"], ["Find and book 任务应该要求最终确认号，而不只返回酒店名。", "Filter count 任务适合自动评估。", "评论分类分数适合做细粒度详情页任务。", "品牌 facet 任务能测试侧栏筛选理解。"], ["修复 Booking gallery 缺图。", "每次筛选后显示稳定 result count。", "预订确认页应有机器可读摘要。", "日期解析要明确年份，避免 WebVoyager 原题里的省略年份歧义。"]),
    "cambridge_dictionary": ("Cambridge Dictionary", "Cambridge Dictionary 镜像适合做精确词典、同义词、翻译、语法和小游戏任务。它有 1,821 个词条、grammar topics、shop items、quizzes、saved words、search history、dictionary、thesaurus、translation、grammar、Plus games、shop 和语言切换。难点不在大规模导航，而在区分 definition、example、translation、grammar rule，并完成小交互。", ["查词：定义、UK IPA、US IPA、例句、义项数量。", "翻译：中文、法语、西语、德语 UI。", "Thesaurus：词或短语的同义表达。", "Grammar：规则页和例句。", "Plus：image quiz、grammar quiz、word scramble。", "Shop 浏览。"], ["比较 UK/US 发音适合做精确抽取。", "找 word/phrase/idiom 相关项能考察 thesaurus 导航。", "语法转换任务可以要求 direct 到 indirect 或 active 到 passive 示例。", "语言切换是 UI 状态任务，不是纯内容检索。"], ["词条页增加稳定 summary 区，统一 IPA/definition 的抽取位置。", "Quiz 需要 deterministic final-score confirmation。", "扩充 thesaurus phrase 词条。", "如果要大量语言切换任务，需要扩充 UI 语言覆盖。"]),
}

# Add compact metadata for the remaining sites to keep this script readable.
SITE_TEXT.update({
    "coursera": ("Coursera", "Coursera 镜像适合做课程发现、项目拆解、讲师/合作方和评价分布任务。它有 239 门课程、981 个 course modules、243 个 sub-courses、1,440 条评论、49 个 partners、enrollments、saved courses、搜索筛选、详情页、讲师页、合作方页、degrees、professional certificates、Coursera Plus、Business/Teams 和 review distribution。", ["按主题、level、duration、course type、partner/institution 搜课。", "Specialization 拆解：包含课程、skills、outcomes。", "讲师/合作方查询和相关课程。", "评论分布计算：四舍五入百分比、最高/最低星级。", "Degree/program 浏览：学校、deadline、bachelor/master 列表。", "Business/Teams/Plus 方案比较。"], ["找包含某 module 的课程很适合考察详情页阅读。", "按国家或类型查 partner 可以覆盖 partner directory。", "Review percentage 任务能测试表格阅读和算术。", "保存/注册课程任务需要先补确认页。"], ["所有筛选组合都显示稳定 result count。", "课程页的 modules/videos 用一致表格渲染。", "扩展 saved/enrolled 动作前先补确认状态。", "UI 展示的 duration 与底层 weeks/hours 要一致。"]),
    "espn": ("ESPN", "ESPN 镜像适合做体育表格、赛程、比分、球员/球队数据和文章摘要任务。它有 1,789 条 game-player stats、1,197 名球员、316 场比赛、285 篇文章、142 支球队、standings、division、conference、schedule、scoreboard、team pages、roster、stats、injury、transaction、depth chart、power index、tickets 和 search。文字/表格任务比视觉任务更稳，因为首页部分图标还缺图。", ["按 sport、team、date 查比分和赛程。", "Standings 和 power index 排名。", "球员统计：得分、篮板、助攻、生涯出场、体重、薪资、伤病。", "球队页：roster、stats、transactions、depth chart、schedule、next game。", "体育文章：按 section 找头条、判断 league、做短摘要。"], ["跨表推理最有价值：赛程 + standings，game detail + player stats，roster + salary/position。", "固定日期 scoreboard 比 latest 更好评估。", "搜索 entity count 可以覆盖球队/联盟/球员多类型搜索。"], ["修复 ESPN league/team 图片后再做视觉任务。", "加镜像日期和时区。", "Standings/stat 页面需要稳定表格 ID 和列名。", "Ticket 任务需要更稳定的价格页。"]),
    "github": ("GitHub", "GitHub 镜像适合做 repo 搜索、qualifier、commit/release/contributor、pricing 和 issue/action 流。它有 685 个 repositories、626 个 topics、576 个 users、3,076 个 issues、stars、watches、follows、repo pages、commits、releases、contributors、wiki、issues、pulls、pricing、marketplace、skills、resources、search syntax，以及 star/watch/fork/follow/create issue/create repo 等状态操作。", ["带 qualifiers 的仓库搜索和排序。", "Contributor、commit、changed files 抽取。", "Topic 和 trending 浏览。", "Pricing/product 页面比较。", "状态操作：star、watch、follow、fork、create issue、create repo。", "Issue 搜索、评论、close/reopen。"], ["query + qualifier + sort 的 repo 搜索能测试搜索语法。", "最近 commit 改了哪些文件是很好的 targeted repo 任务。", "Top contributors 任务能考察 repo 子页面。", "Pricing delta 任务覆盖非 repo 页面。"], ["加 seeded today，使 date qualifiers 有稳定参照。", "如果要大量 PR/release/file-tree 任务，需要补更多 fixture。", "Star/fork/watch/issue 后需要明确确认区。", "搜索 facet count 必须跟当前过滤结果一致。"]),
    "google_flights": ("Google Flights", "Google Flights 是最适合大规模参数化造题的环境。它有 126,872 条航班、93 个机场、booking、tracked flights、price alerts、saved searches、payment methods、route resolution、one-way/round-trip、日期、乘客、舱位、stops、价格、航空公司、按价格/时长/起飞/排放排序、price graph、date grid、price insights、destination/explore、checkout 和 booking detail。", ["航线 + 日期 + 舱位 + stop 搜索。", "按最低价、最快、最低排放、起飞时间排序。", "Round-trip 与 one-way 比较。", "价格区间和航空公司筛选。", "详情页抽取：航空公司、时长、stop、排放、booking options。", "Explore/destination、price graph、date grid。", "状态流：track flight、price alert、saved search、booking。"], ["比较两个航班时要求价格、时长和 stop 一起回答。", "排放维度是 Google Flights 的特化价值。", "Booking options 页适合高难度 targeted 流程。", "Price graph/date grid 可以测试非列表 UI 理解。"], ["搜索结果页增加 result count 和 filter chips。", "Price graph 加稳定数据标签。", "Track/saved/search/booking 动作需要确认页。", "造题前要用 route inventory 校验航线存在。"]),
    "google_map": ("Google Map", "Google Map 镜像适合做本地搜索、附近点、路线、营业时间、评论和地点详情任务。它有 963 个 places、105 个 cities、categories、place details、reviews、photos、saved lists、trips、timeline、directions、search、nearby APIs、route data、category/city pages、settings 和 account flows。", ["按 ZIP、地址、路口、地标做附近搜索。", "地点类别 + 评分 + 营业时间筛选。", "两个地点或城市之间的 directions。", "停车、EV charging、公交站、服务商查询。", "地点详情：基础信息、评论、无障碍、设施。", "保存列表、trip、timeline 动作。"], ["Nearest to X 是地图站点最有价值的任务。", "Open now 但不是 24h 的任务能测试营业时间逻辑。", "Route detail 任务测试 directions UI。", "Share/print map 是非搜索型特化操作。"], ["UI 加显式 radius 和排序控件。", "模糊地名需要稳定 disambiguation 页面。", "路线步骤、距离、时间需要稳定标签。", "save/share/print/trip 动作需要确认页。"]),
    "google_search": ("Google Search", "Google Search 镜像适合做受控 SERP 推理，但也是风险最高的站点。它有 170 个 topics、1,170 条 search results、647 个 related queries、575 个 knowledge facts、319 个 PAA questions、bookmarks、collections、alerts、history，以及 images/videos/news/maps/shopping/books/finance 垂直搜索和 external-cache snapshots。WebVoyager 原题中很多 Google 任务依赖实时网页或外站，造题时必须显式快照。", ["从 knowledge panel 或 snippet 找事实。", "选择正确来源并打开 cached external page 抽取字段。", "使用 images/news/videos/shopping/books/finance 垂直搜索。", "PAA 和 related queries 探索。", "Bookmark/history/collection 状态任务。", "Cached external-page 阅读任务。"], ["在干扰结果中选择正确来源最适合 SERP benchmark。", "打开缓存外页抽取细节比只读 snippet 更有针对性。", "Google apps/advanced/settings 能覆盖站点特化 UI。", "Twitter/Reddit/YouTube/login/current stats 类任务必须单独审计。"], ["Knowledge panel 事实题要把 answer token 明确显示在页面上。", "所有 current/latest 任务都要快照日期和值。", "扩充 YouTube/Reddit/Twitter/GitHub 类 external cache。", "SERP topic 增加 source/date badge。"]),
    "huggingface": ("Hugging Face", "Hugging Face 镜像覆盖模型、数据集、Spaces、文档、论文、博客、部署和讨论。它有 678 个 repositories、277 个 authors、39 个 tasks、repo detail、files、commits、discussions、collections、deployment cart、endpoints、pricing、enterprise、blog、papers、docs、classroom、dataset viewer、chat、Inference API，以及 license/library/task/language/modality 筛选。", ["模型/数据集/Space 发现：task、license、library、language、modality、downloads、likes、updated。", "Model card 抽取：size、tensor type、framework、metrics、tags、language。", "Docs 查找：Transformers、TRL、PEFT、Trainer、tokenizer API。", "Inference API：文本生成、句子相似度、embedding。", "Space/chat 交互。", "Dataset viewer 行/字段抽取。", "Deployment cart、endpoints、pricing。"], ["网页上的 Inference API 任务很有价值。", "打开 Space 并提问可以测试嵌入式 app 行为。", "查文档参数和默认值能测试 docs 导航。", "Dataset viewer 第一行/指定字段任务非常适合结构化评估。"], ["搜索结果页的更新时间和排序要显式稳定。", "扩充 docs 页面和代码片段。", "Inference API 输出要可复现，或按性质评估。", "Dataset viewer 需要分页/筛选控件来支持更多行级任务。"]),
    "wolfram_alpha": ("Wolfram Alpha", "Wolfram Alpha 镜像本质上是预计算答案环境。它有 163 条 computation_results、categories、subcategories、topics、favorites、saved queries、notebooks、history、examples、input/result、Pro/pricing/products/about，以及 notebook/favorite 状态流。它不能现场做任意符号计算，造题必须围绕已 seed 的 computation_results，或先扩充 seed DB。", ["数学计算：导数、积分、化简、矩阵、级数、几何、曲线长度、旋转圆锥曲线。", "物理/工程/材料：电阻率、导热系数、抛体、摆、地磁、发电量。", "单位/化学：摩尔转换、元素质量百分比。", "日期、人口、金融比较。", "健康/日常估算：晒伤、减重、热量、心率储备、代谢属性。", "Notebook/favorite/saved query 状态流。"], ["计算并抽取精确值适合 golden task。", "比较两个 result pods 是 Wolfram 特化价值。", "把多个计算保存进 notebook 可以扩展成高价值 action task。", "曲线绘图任务可用，但要保证图像稳定。"], ["建立 seed-generation 流程，否则新题只能围绕现有 163 条 query。", "数学表达式需要归一化展示和参考答案。", "结果 pod 加机器可读行和 label。", "避免实时天气/金融，除非页面显示快照日期。"]),
})

WEBVOYAGER_NAME = {
    "huggingface": "Huggingface",
    "wolfram_alpha": "Wolfram Alpha",
    "google_map": "Google Map",
    "google_search": "Google Search",
    "google_flights": "Google Flights",
    "bbc_news": "BBC News",
    "cambridge_dictionary": "Cambridge Dictionary",
}

def load_rows_from_review_data(slug: str):
    display = WEBVOYAGER_NAME.get(slug, SITE_TEXT[slug][0])
    wv = WEBVOYAGER_ROOT / "data" / "WebVoyager_data.jsonl"
    rows = []
    for line in wv.read_text().splitlines():
        obj = json.loads(line)
        if obj.get("web_name") == display:
            rows.append((obj["id"], obj["ques"], ""))
    return sorted(rows, key=lambda x: int(x[0].split("--")[-1]))

def has_any(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)

def dims_for(question: str) -> list[str]:
    lower = question.lower()
    dims: list[str] = []
    checks = [
        ("价格/数值阈值", ["price", "$", "under", "between", "above", "less than", "more than", "at least", "cheapest", "lowest", "highest"]),
        ("评分/评论", ["rating", "star", "review", "reviews", "score"]),
        ("日期/时效", ["latest", "current", "today", "yesterday", "recent", "within", "past", "date", "released", "updated"]),
        ("排序/Top N", ["sort", "top", "first", "three", "five", "list", "rank", "leader"]),
        ("状态操作", ["cart", "wishlist", "save", "checkout", "book", "add", "register", "login", "star", "watch", "fork", "shopping list", "meal plan", "reserve"]),
        ("比较推理", ["compare", "difference", "what about", "which one", "same as"]),
        ("详情页抽取", ["detail", "spec", "abstract", "author", "policy", "docs", "wiki", "support", "module", "instructor", "ingredients", "definition", "pronunciation", "example", "features", "summary"]),
        ("路线/距离/附近", ["near", "nearest", "closest", "distance", "route", "directions", "walking", "drive", "from ", " to "]),
        ("表格/榜单", ["standings", "leaderboard", "schedule", "roster", "stats", "depth chart", "table"]),
        ("站点特化交互", ["inference", "space", "dataset viewer", "api", "quiz", "game", "print", "share", "translate", "language", "price graph"]),
    ]
    for label, words in checks:
        if has_any(lower, words):
            dims.append(label)
    return dims[:4] or ["页面导航", "答案抽取"]

def zh_intent(slug: str, question: str) -> str:
    site = SITE_TEXT[slug][0]
    dims = "、".join(dims_for(question))
    return f"在 {site} 中完成 {dims}。重点不是背答案，而是让 agent 找到正确页面、处理约束，并从页面上抽取可验证结果。"

def zh_recommendation(slug: str, question: str) -> str:
    lower = question.lower()
    dims = dims_for(question)
    bits: list[str] = []
    if "状态操作" in dims:
        bits.append("继续造题时可以替换同类实体，并要求 agent 完成操作后回到确认页核对状态。")
    if "价格/数值阈值" in dims or "评分/评论" in dims or "排序/Top N" in dims:
        bits.append("适合参数化阈值、排序方式和候选数量，答案要包含名称、关键数值和排序依据。")
    if "详情页抽取" in dims:
        bits.append("新题应要求打开详情页或文档页，抽取一到三个明确字段，避免只读搜索结果。")
    if "日期/时效" in dims:
        bits.append("涉及“最新/当前/最近”的任务要绑定镜像日期，或者改成固定日期窗口，避免答案漂移。")
    if "路线/距离/附近" in dims:
        bits.append("适合替换地点、路线、日期或距离阈值，但生成前要确认数据里确实存在可达结果。")
    if "表格/榜单" in dims:
        bits.append("适合做表格过滤、排名和聚合题，评估时要求列名、行名和数值一起返回。")
    if "站点特化交互" in dims:
        bits.append("这是站点特化交互，适合保留为 targeted benchmark，并要求页面出现可验证完成状态。")
    site_specific = {
        "wolfram_alpha": "Wolfram Alpha 题必须先确认 computation_results 里有预计算答案，再扩展同类计算。",
        "google_search": "Google Search 题应优先使用已缓存页面或已 seed 的知识卡，少用真实实时网页。",
        "google_flights": "Google Flights 题生成前要先用航班表校验航线、日期、舱位和经停条件。",
        "google_map": "Google Map 题要处理地点消歧义，并让答案包含地点名、距离或路线依据。",
        "booking": "Booking 题适合从城市、日期、设施和价格组合生成，但要先确认筛选后有结果。",
        "github": "GitHub 题应明确 qualifier、排序和目标子页，例如 releases、commits、contributors 或 issues。",
        "huggingface": "Hugging Face 题应明确资源类型和筛选条件，并要求打开模型卡、文档或 Dataset Viewer 核对字段。",
        "cambridge_dictionary": "词典题应限制要抽取的字段，例如 UK/US IPA、定义、例句、翻译或 grammar 例句。",
    }
    if slug in site_specific:
        bits.append(site_specific[slug])
    if not bits:
        bits.append("可以保留原任务的核心路径，把实体换成同类数据，并增加一个可验证字段提升评估稳定性。")
    bits = bits[:3]
    return "".join(bits)

for slug, (title, infra, good, targeted, gaps) in SITE_TEXT.items():
    rows = load_rows_from_review_data(slug)
    out = [f"# {title}", "", "## 基础设施能力", "", infra, "", "## 适合泛化的任务族", ""]
    out.extend(f"- {item}" for item in good)
    out.extend(["", "## 站点特化场景", ""])
    out.extend(f"- {item}" for item in targeted)
    out.extend(["", "## 逐任务建议", "", "| ID | 原始任务意图 | 基于 WebHarbor 的造题建议 |", "| --- | --- | --- |"])
    for task_id, intent, rec in rows:
        out.append(f"| {task_id} | {zh_intent(slug, intent)} | {zh_recommendation(slug, intent)} |")
    out.extend(["", "## 扩容前需要补的基础设施", ""])
    out.extend(f"- {item}" for item in gaps)
    (BASE / f"{slug}.md").write_text("\n".join(out) + "\n")

(BASE / "README.md").write_text("""# WebHarbor × WebVoyager 人工任务设计审阅

这个目录是人工审阅稿，用来说明如何基于当前 WebHarbor 基础设施继续设计 WebVoyager 风格任务。这里不是 `tasks.jsonl` 的机械展开：每个站点文件都记录这个镜像真正支持什么、哪些原始 WebVoyager 任务适合作为种子、以及如何继续造出既有泛化性又有站点针对性的任务。

## 审阅模板

- 基础设施能力：当前镜像已经暴露了哪些页面、数据和状态流。
- 适合泛化的任务族：可以迁移到新实体、新筛选条件、新日期或新类别的任务模式。
- 站点特化场景：这个 app 独有、适合作为 targeted benchmark 的交互。
- 逐任务建议：每条原始 WebVoyager 任务对应一条具体扩展建议。
- 扩容前 gap：大规模造题前应该补的页面、数据或校验能力。
""")

print(f"localized {len(SITE_TEXT)} site files")
