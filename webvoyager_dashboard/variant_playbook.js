window.TASK_VARIANT_PLAYBOOK = {
  allrecipes: {
    title: "Allrecipes",
    thesis: "Allrecipes 适合做“带约束的内容检索 + 详情抽取 + 轻量状态操作”。它的题目最好围绕食材、饮食标签、时间、营养、评分、评论和购物清单展开。",
    variants: [
      {
        name: "多条件菜谱检索",
        infrastructure: "Recipe 模型有 rating、review_count、prep/cook/total time、calories、servings、ingredient_count、dietary_tags、dish_type、meal_type、cuisine、main_ingredient、feature_tags；/search 和 /category 支持这些过滤维度。",
        knobs: ["菜系", "主食材", "饮食标签", "评分阈值", "评论数阈值", "准备/烹饪/总时间", "热量", "份数", "食材数量"],
        examples: [
          "找一道评分 4.5+、评论数 200+、准备时间 30 分钟以内的素食晚餐，并给出标题、准备时间和评分。",
          "找一道含 spinach 但不含 mushroom 的 vegetarian lasagna，回答食材中支持这个判断的两项。",
          "找一道低碳早餐，要求碳水低于 8g，并返回菜名、总时间和每份碳水。"
        ],
        verification: "答案应来自搜索结果和 recipe detail；至少包含菜名 + 触发约束的页面字段。营养类题要从 Nutrition Facts 读取。",
        risks: "不要只靠标题匹配；如果约束在 UI 中不可见，需要先补详情页字段。"
      },
      {
        name: "详情页证据抽取",
        infrastructure: "recipe_detail 页面展示 ingredients、directions、nutrition、reviews、latest_review_text、servings、prep/cook/total time。",
        knobs: ["第 N 个食材", "前 N 步做法", "最新评论", "某个营养字段", "烤箱温度", "保存方式"],
        examples: [
          "打开 Banana Banana Bread，列出前 5 个食材和总时间。",
          "找到 Easy Vegetarian Spinach Lasagna，回答最新评论说了什么。",
          "找一道 fried fish 菜谱，并回答每份 Iron 含量。"
        ],
        verification: "让答案包含字段名和值，例如 `Iron: 15mg`、`Prep Time: 20 mins`，避免纯摘要。",
        risks: "长答案容易不好评估，建议限制为 1 到 3 个字段。"
      },
      {
        name: "集合/栏目导航",
        infrastructure: "站点有 Dinners、Occasions、Allstars、popular-1960s collection、category pages。",
        knobs: ["栏目名", "列表位置", "节日分类", "推荐菜谱数量", "栏目下的二级 section"],
        examples: [
          "进入 The Most Popular Recipes of the 1960s，回答第二道菜的准备时间和总时间。",
          "在 Occasions 中列出 6 个 holiday recipe section。",
          "从 Dinners 页面挑 3 道推荐晚餐，并回答每道菜的标题。"
        ],
        verification: "答案应包含栏目路径和列表位置，防止 agent 直接搜索答案。",
        risks: "如果列表排序会随机，先固定排序或只问稳定位置。"
      },
      {
        name: "购物清单与 meal plan 状态任务",
        infrastructure: "有 login/register、recipe-box、meal-plan、shopping-list，以及 form POST 和 API endpoints。",
        knobs: ["清单名称", "菜谱名称", "加入哪一天/哪一餐", "加入食材还是自定义 item", "保存到 recipe box"],
        examples: [
          "找到 Easy Quinoa Salad，创建名为 `weekday quinoa` 的购物清单，把该菜谱食材加入清单，并返回清单里的前三项。",
          "把 Baked Dijon Salmon 加入 Friday dinner 的 meal plan，然后打开 meal plan 核对。",
          "保存一道 gluten-free brownie 到 recipe box，并返回 recipe box 中显示的标题。"
        ],
        verification: "必须回到 shopping-list、meal-plan 或 recipe-box 页面核对状态；任务答案应包含确认页中的名称。",
        risks: "需要账号态或 session 态稳定；批量 RL 前要验证 reset 会清理用户状态。"
      }
    ]
  },
  amazon: {
    title: "Amazon",
    thesis: "Amazon 适合做电商 benchmark：复杂筛选、规格抽取、变体选择、评论理解、购物车和政策阅读都能覆盖。",
    variants: [
      {
        name: "商品搜索 + 多重筛选",
        infrastructure: "Product 模型支持 price、rating、review_count、brand、condition、is_prime、is_deal、free_shipping、free_returns、variant_options、feature_tags、release_date；/search 和 /c/<slug> 会应用过滤和排序。",
        knobs: ["品类", "品牌", "价格区间", "评分", "评论数", "成色", "颜色/尺码/容量", "是否免运费/免费退货", "feature tags"],
        examples: [
          "找一个 4 星以上、$40-$60、带背光的人体工学键盘，并保存评论数超过 500 的那个。",
          "找 waterproof、size 6、4 星以上的 women's hiking boots，回答第一件商品名和价格。",
          "找 6-8 outlets、$25 以下、4 星以上的 surge protector，回答 outlet 数和评分。"
        ],
        verification: "答案应包含商品名、价格和至少一个筛选字段。不要只回答搜索词命中的标题。",
        risks: "部分规格只在标题或 feature_tags 中，最好补结构化 facts 表。"
      },
      {
        name: "排序和 Top N 比较",
        infrastructure: "_apply_sort 支持 price_asc、price_desc、rating、reviews、newest、bestseller；商品卡展示价格、评分、评论数。",
        knobs: ["排序方式", "Top N 数量", "比较字段", "类别", "筛选组合"],
        examples: [
          "搜索 climbing gear，按价格从高到低排序，回答前三个商品名和价格。",
          "找便携空调，比较前三个结果的价格和适用房间面积。",
          "找 2024 fiction book，按评分排序，回答评分最高且评论数超过 50 的标题。"
        ],
        verification: "要求返回排序依据和 Top N 的字段，便于自动判断。",
        risks: "排序任务要避免首页随机推荐，必须从搜索/分类结果页开始。"
      },
      {
        name: "变体和购物车动作",
        infrastructure: "商品详情有 variant_options，匿名 session cart 和登录 cart 都可用；/cart/add/<id> 和 /api/cart/add 支持加购。",
        knobs: ["颜色", "尺码", "容量", "数量", "成色", "是否直接 checkout"],
        examples: [
          "找到 Blue iPhone 12 Pro 128GB 并加入购物车，最后返回购物车中的变体文本。",
          "找黑色 size 7 的 men's running shoes，价格低于 $50，加入购物车并核对数量。",
          "找 purple yoga mat，确认颜色总数、退货政策和配送政策，再加入购物车。"
        ],
        verification: "必须打开 cart/bag 页面核对商品名、数量和变体。",
        risks: "如果变体 UI 只是前端状态，需要确保 form POST 把变体写入 cart。"
      },
      {
        name: "政策、评论和附加服务",
        infrastructure: "Product detail 展示 reviews、top_review、return/free return、protection plan、delivery/condition 信息。",
        knobs: ["Top review", "退货方式", "保护计划价格", "免运费", "免费退货", "成色"],
        examples: [
          "查某件 Mens Rhinestone Skull Graphic Shirt 的免费退货政策，并回答退货步骤。",
          "找一个 100+ reviews 且 4+ stars 的 Ride On Car，回答 Top review 标题。",
          "查 PS4 的 2-year protection plan 费用。"
        ],
        verification: "答案要包含政策页或详情页上的原字段，不接受泛泛描述。",
        risks: "政策任务非常适合 targeted benchmark，但要保证每个商品都有对应政策字段。"
      }
    ]
  },
  apple: {
    title: "Apple",
    thesis: "Apple 适合做产品比较、配置报价、技术规格、支持文档、trade-in 和取货任务。它的题目应该强调 Apple 站点特有的产品层级和支持路径。",
    variants: [
      {
        name: "产品族比较",
        infrastructure: "Product 模型有 category、price、screen_size、chip_family、ram、ssd、color_options、storage_options、release_year、feature_tags；还有 compare/category pages。",
        knobs: ["产品线", "代际", "价格", "屏幕尺寸", "芯片", "颜色", "存储", "重量", "电池"],
        examples: [
          "比较 iPhone 14 Pro 和 iPhone 15 Pro 的价格、芯片和 GPU 核心数。",
          "列出最新 iMac 的颜色选项，并回答起售价。",
          "比较 Apple Watch Series 和 Watch SE 的起售价差。"
        ],
        verification: "答案应包含两到三个明确字段，不要只写“更好/更贵”。",
        risks: "latest 需要绑定镜像日期；否则建议使用明确型号。"
      },
      {
        name: "配置与价格差",
        infrastructure: "有 configure/<slug>、compute_configured_price、cart/add form、storage/memory/color/connectivity 选项。",
        knobs: ["芯片", "内存", "存储", "屏幕尺寸", "联网方式", "配件排除项", "是否加入 bag"],
        examples: [
          "配置 16-inch MacBook Pro、M3 Max、64GB、1TB，回答最终价格。",
          "计算 14-inch MacBook Pro 最便宜基础款升级到最高配置的价差。",
          "配置 iPad mini 64GB Wi-Fi + Cellular，不加 engraving、Pencil、Smart Folio，回答总价。"
        ],
        verification: "要求返回配置摘要和最终价格；最好核对 bag 中的配置。",
        risks: "配置页面要显示每个选项的价格 delta。"
      },
      {
        name: "支持文档和维修路径",
        infrastructure: "SupportArticle、support/repair、forgot-password、iOS feature article、trade-in support 等页面。",
        knobs: ["支持主题", "设备", "软件版本", "兼容性", "维修方式", "忘记密码步骤"],
        examples: [
          "查 iOS 17 的新功能，并确认 iPhone 12 是否兼容。",
          "列出 Apple Repair 页面提到的两种维修方式。",
          "查忘记 Apple ID password 时最快的重置方式。"
        ],
        verification: "答案应来自支持文章，并包含页面中的具体选项或步骤。",
        risks: "支持文档任务比商品搜索更 targeted，适合保留少量高质量题。"
      },
      {
        name: "Trade-in、Pickup 和配件生态",
        infrastructure: "有 TradeInValue、trade-in pages、store pickup、accessories、Vision Pro、Apple Pencil、AirPods、HomePod。",
        knobs: ["旧设备型号", "设备状态", "ZIP", "门店", "配件类别", "颜色/型号"],
        examples: [
          "查 iPhone 13 Pro Max good condition 的 trade-in value。",
          "搜索 Smart Folio for iPad，查 90038 附近最近可取货门店。",
          "列出 Apple Vision Pro 三个配件及用途。"
        ],
        verification: "答案应包含具体 trade-in value、门店名或配件名。",
        risks: "pickup 任务要保证门店排序和库存状态稳定。"
      }
    ]
  }
};

Object.assign(window.TASK_VARIANT_PLAYBOOK, {
  arxiv: {
    title: "ArXiv",
    thesis: "ArXiv 适合做研究检索、论文详情抽取、帮助文档和站点元信息任务。它有论文元数据、分类、版本、帮助页、商店和 library/export 状态流。",
    variants: [
      { name: "分类与日期窗口检索", infrastructure: "Paper 表包含 primary_subject_code、submitted/announce date、authors、abstract；搜索页支持 query、category、searchtype 和日期筛选。", knobs: ["分类", "关键词", "标题/摘要字段", "日期范围", "作者数量", "是否 HTML 可读"], examples: ["搜索 cs.CL 最近论文，返回标题、作者和摘要。", "查询 Graph Neural Networks 在指定日期范围内的论文数，并统计作者超过 5 人的数量。", "比较 quantum computing 在 quant-ph 与 all archives 的结果数。"], verification: "答案要包含搜索范围、结果数、论文标题或日期。", risks: "latest/week/yesterday 必须绑定镜像日期；外部 Cornell 页面需要镜像后再用。" },
      { name: "论文详情和版本历史", infrastructure: "paper detail 暴露 authors、abstract、figures/tables/formulas、versions、pdf/html/source 入口。", knobs: ["论文标题", "版本号", "图表/公式数量", "loss function", "HTML/PDF 可用性", "作者单位"], examples: ["查 GPT-4 Technical Report 的 v3 提交时间。", "打开 Dense Passage Retrieval，回答公式数量和哪个是 loss function。", "找 graph neural networks 论文并回答第一作者单位。"], verification: "要求返回论文标题、版本/字段名和值。", risks: "内容型任务应限制字段数量，不要要求长摘要。" },
      { name: "帮助文档和 taxonomy", infrastructure: "Help、submission guidelines、category taxonomy、about、leadership team 等页面已镜像。", knobs: ["帮助主题", "分类体系", "提交规则", "图格式", "订阅方式", "人员名单"], examples: ["查未公告投稿如何 withdraw。", "列出 Economics 包含的分类和缩写。", "查提交论文时支持哪些 figure formats。"], verification: "答案要来自帮助页或 taxonomy 页，包含精确条目。", risks: "文档任务要避免离开本地镜像。" },
      { name: "商店与状态流", infrastructure: "store、merchandise、library、starred、citation export、cart-like store actions 可用。", knobs: ["商品类型", "尺码", "加入购物车", "保存论文", "导出格式"], examples: ["浏览 arXiv store，回答 merchandise 类型数。", "把 arXiv Forever short sleeve XL 加入购物车。", "保存一篇论文到 library 并导出 BibTeX。"], verification: "需要确认页或状态页显示商品/论文/导出项。", risks: "商店动作要验证 reset 后状态清理。" }
    ]
  },
  bbc_news: {
    title: "BBC News",
    thesis: "BBC News 适合栏目导航、文章理解、体育/市场表格和音频内容任务。它的挑战在于把开放摘要变成可评估的结构化答案。",
    variants: [
      { name: "栏目头条和文章摘要", infrastructure: "Article、Category、section pages、search、story detail 已有；文章含标题、日期、作者、图片和正文摘要。", knobs: ["栏目", "地区", "主题", "文章日期", "是否要作者", "摘要长度"], examples: ["进入 Technology 的 AI 栏目，回答头条标题和涉及公司。", "在 Africa news 中找最近文章，总结前三个主题。", "找 climate change simple guide，回答人类活动原因。"], verification: "答案包含标题、栏目、日期或具体句子。", risks: "latest/recent 要绑定镜像日期；开放摘要要限制为 2-3 点。" },
      { name: "体育表格和排行榜", infrastructure: "BBC Sport 页面包含 golf leaderboard、football tournament、calendar、horse racing results。", knobs: ["运动项目", "日期", "排行榜列", "球队/球员", "Top N", "国家"], examples: ["查 Women's Majors 前 20 里哪个国家最多，并找澳大利亚最佳球员。", "查 Scottish Premiership 队伍数量和 Hibernian 最近比赛开始时间。", "查 horse racing 昨天哪场 runners 最多。"], verification: "答案要包含表格名、行名和数值。", risks: "体育表格需要稳定列名；图片不是主要评估依据。" },
      { name: "音频、文化、旅行和市场数据", infrastructure: "Audio/podcasts、Culture、Travel、Market Data、Specialist pages 已有。", knobs: ["内容栏目", "榜单位置", "节目/书/电影", "城市", "数据来源"], examples: ["进入 BBC Audio，列出两个 2023 推荐 podcast。", "在 Market Data 中回答数据来自哪家公司。", "在 Travel SpeciaList 中列出出现的城市。"], verification: "答案要包含页面栏目和可见条目。", risks: "文化/旅行摘要题要限制输出字段，避免难评估。" }
    ]
  },
  booking: {
    title: "Booking",
    thesis: "Booking 适合做参数化旅行任务：城市、日期、人数、房间、设施、评分、价格、距离、品牌、货币和预订状态都能组合。",
    variants: [
      { name: "酒店搜索和设施筛选", infrastructure: "Property、City、Landmark、Review、search filters、amenity flags、stars/rating/price、dates/adults/rooms 都已实现。", knobs: ["城市/国家/地标", "日期", "成人/儿童", "房间数", "价格", "评分", "星级", "设施"], examples: ["找 Paris 5 晚、评分 8+、免费 WiFi 的酒店。", "找 Lisbon 机场接送、8.5+、早餐、6 晚的酒店。", "找 Sydney 停车和 WiFi、评分 8+ 的酒店。"], verification: "答案包含酒店名、价格/评分和触发筛选的设施。", risks: "生成前要确认筛选组合有结果。" },
      { name: "排序、距离和 facet 计数", infrastructure: "支持 price/rating/stars/distance/beach distance 排序，支持 brand counts 和 filter counts。", knobs: ["排序方式", "Top N", "品牌 facet", "海滩/地标距离", "结果数量"], examples: ["Barcelona 搜索后按 distance from beach 排序，并要求 WiFi+breakfast。", "London 应用 Breakfast + Fitness filters 后回答剩余酒店数。", "Rio 查看 Brands filter，回答最多和最少的品牌。"], verification: "答案要包含 count、排序依据或 facet 名称。", risks: "距离题要确保城市/地标解析不误匹配。" },
      { name: "预订和货币任务", infrastructure: "Bag、checkout、booking confirmation、payment methods、currency switch、saved properties 可用。", knobs: ["币种", "房型", "日期", "是否 checkout", "是否收藏", "支付方式"], examples: ["把 Los Angeles 带早餐和机场接送的房间加入 bag 并确认。", "Berlin 三晚价格同时回答 USD 和 CNY。", "Shenzhen 搜索后切换成人民币并回答价格。"], verification: "必须在 bag/confirmation 或货币切换后的页面核对。", risks: "确认页需要保留可读摘要，便于评估动作是否成功。" },
      { name: "客服、评论和文章", infrastructure: "help、customer service、property reviews、travel articles 已有。", knobs: ["客服问题", "评论分类", "文章主题", "地点推荐"], examples: ["客服 cancellation 问答：如何知道订单已取消。", "Hokkaido 酒店评论里哪些类别大于 9，哪些小于 9。", "从 travel article 中总结三个提到的地点。"], verification: "答案来自 help/review/article 页面中的可见文本。", risks: "文章总结要限制条目数量。" }
    ]
  },
  cambridge_dictionary: {
    title: "Cambridge Dictionary",
    thesis: "Cambridge Dictionary 适合精确字段抽取：发音、定义、例句、翻译、同义词、语法规则和小游戏结果。",
    variants: [
      { name: "词条精确抽取", infrastructure: "Words 表含 definition、UK/US pronunciation、examples、multiple meanings；word detail 页面可读。", knobs: ["单词", "UK/US IPA", "定义", "例句", "义项数量", "是否多义"], examples: ["查 sustainability 的 UK/US IPA 和定义。", "查 dog 的三个不同义项。", "查 meticulous 的 US IPA 和一个例句。"], verification: "答案要包含字段名和值，例如 UK: /.../，Def: ...。", risks: "不要让答案过长，最好限制 1-3 个字段。" },
      { name: "翻译和 thesaurus", infrastructure: "Translation、Thesaurus、language switch 已实现。", knobs: ["目标语言", "词/短语", "同义词数量", "UI 语言"], examples: ["查 ephemeral 的 Spanish translation。", "搜索 feel giddy 的 thesaurus synonyms。", "把首页语言切换成 Deutsch。"], verification: "答案要包含翻译词或 synonym 列表。", risks: "语言切换任务要验证页面 UI 确实变化。" },
      { name: "Grammar 和 Plus 互动", infrastructure: "Grammar topics、quizzes、word scramble、image quiz、shop 页面可用。", knobs: ["语法主题", "例句类型", "quiz 类型", "最终分数", "shop item 数量"], examples: ["查 present perfect simple 的 affirmative/negative/interrogative 示例。", "完成 Animals easy image quiz 并回答分数。", "浏览 shop 并列出三个商品。"], verification: "语法题要返回规则名和例句；quiz 题要返回最终分数或完成状态。", risks: "Quiz 需要 deterministic scoring。" }
    ]
  },
  coursera: {
    title: "Coursera",
    thesis: "Coursera 适合课程发现、specialization 拆解、module 检索、讲师/合作方和评价分布计算。",
    variants: [
      { name: "课程搜索与筛选", infrastructure: "Course 模型含 topic、level、course_type、duration_weeks/hours、rating、partner、certificate、free/new 等字段；search_courses 支持筛选和排序。", knobs: ["主题", "难度", "课程类型", "持续时间", "评分", "是否免费", "机构"], examples: ["找 beginner、1-3 months、大学提供的 3D printing 课程。", "找 AI ethics、少于 20 小时、4+ stars 的课程。", "搜索 Data Analysis，筛 Beginner 和 1-3 months，回答结果数。"], verification: "答案包含课程名、机构、时长或筛选结果数。", risks: "筛选结果数要在 UI 上稳定显示。" },
      { name: "Specialization 和 module 深读", infrastructure: "SubCourse、CourseModule、course detail、review distribution、instructor pages 可用。", knobs: ["specialization", "包含课程", "module 名", "quiz/video 数", "skills", "learning outcomes"], examples: ["找到 Beginner Spanish Specialization，列出所有子课程。", "查 Space Safety module 2 有几个视频和名称。", "找 Introduction to AI 中包含 Ethical Considerations 的 module。"], verification: "答案应包含课程页上的 module 或 sub-course 名称。", risks: "module 表要保持稳定排序。" },
      { name: "合作方、学位和商业页面", infrastructure: "Partners、Degrees、Coursera Plus、Business、Teams 页面已实现。", knobs: ["国家", "partner 类型", "degree 类型", "deadline", "价格", "优势"], examples: ["列出 Australia 的 Coursera partners。", "浏览 online degrees，列三个 Bachelor programs。", "比较 Coursera for Business 和 Teams 的优势。"], verification: "答案包含 partner/program 名称或价格字段。", risks: "商业页是文案抽取，建议限制输出条数。" }
    ]
  },
  espn: {
    title: "ESPN",
    thesis: "ESPN 适合体育表格和跨表推理，尤其是赛程、比分、standings、roster、stats、injury、transactions、depth chart。",
    variants: [
      { name: "比分、赛程和比赛详情", infrastructure: "Game、GamePlayerStat、scoreboard、schedule、game detail、team schedule 可用。", knobs: ["运动", "日期", "球队", "最新/固定比赛", "top scorer/rebounder/assists", "highlight"], examples: ["查 2023-12-25 NBA 全部比分。", "查 Lakers 最近一场比赛比分和 top scorer。", "找 loser high 高于 winner high 的昨天 NBA matchup。"], verification: "答案要包含日期、双方球队、比分和球员统计字段。", risks: "latest/yesterday 要绑定镜像日期。" },
      { name: "Standings、BPI 和球队列表", infrastructure: "Conference、Division、Team、PowerIndex、standings pages 已有。", knobs: ["联盟", "conference", "division", "排名字段", "球队名关键字"], examples: ["NBA Eastern Conference standings。", "NBA BPI 第一和最后。", "NHL 各 conference/division 顶部和底部球队。"], verification: "答案包含表格分区和行名。", risks: "表格需要明确列名，否则自动评估困难。" },
      { name: "Roster、Stats、Depth Chart 和 Injuries", infrastructure: "Player、PlayerStat、DepthChartEntry、injuries、roster、team stats 页面可用。", knobs: ["球队", "位置", "统计项", "体重/薪资", "伤病状态"], examples: ["找 Celtics roster 最高薪球员。", "算 Anthony Davis GP percentage，并判断是否有人相同。", "查 Jets depth chart 中 2ND position 的 injured players。"], verification: "答案包含球员名、球队、位置和数值。", risks: "需要稳定 season 和统计口径。" },
      { name: "文章、交易、票务和 ESPN+ 页面", infrastructure: "Article、Transaction、Tickets、ESPN+ 页面可用。", knobs: ["栏目", "交易时间窗", "球队", "文章主题", "票价", "工具名"], examples: ["找 NBA 最近一周 transactions。", "查 Lakers 下一场比赛并进入 ticket 页面找最低票价。", "浏览 ESPN+ 页面总结 tools。"], verification: "答案包含文章标题、交易行、票价或工具名。", risks: "票务页要保证价格稳定。" }
    ]
  },
  github: {
    title: "GitHub",
    thesis: "GitHub 适合 repo 搜索、qualifier、commit/release/contributor、issues、pricing 和状态动作。",
    variants: [
      { name: "Repo 搜索和 qualifiers", infrastructure: "Repository、Topic、User、search parser 支持 language、stars、created、pushed、topic、license、sort 等 qualifier。", knobs: ["关键词", "语言", "stars/forks", "created/pushed 日期", "topic", "license", "sort"], examples: ["找 climate change data visualization 中 stars 最多的 repo。", "找最近 2 天更新、Python、decision trees 的 ML repo。", "找 created after 2023-12-29 的 JavaScript repo 并按 stars 排序。"], verification: "答案包含 repo full name、stars 或 qualifier 证据。", risks: "日期 qualifier 要绑定站点 today。" },
      { name: "Repo 子页面：commit/release/contributor/wiki/issues", infrastructure: "Repo detail、commits、commit detail、releases、contributors、wiki、issues、pulls 已实现。", knobs: ["repo slug", "commit 数量", "changed files", "release version", "top contributors", "closed issues"], examples: ["查 ALBERT repo 最近 commit 改了哪些文件。", "查 Vuex latest stable release 和发布日期。", "查 angular/angular 最近关闭的三个 issue。"], verification: "答案包含子页面字段，不接受只返回 repo 名。", risks: "要确保目标 repo 的 fixture 足够丰富。" },
      { name: "GitHub 产品页和状态操作", infrastructure: "Pricing、Copilot、Skills、Resources、Sign up、star/watch/fork/follow/create issue/create repo。", knobs: ["plan", "价格", "feature", "course", "email", "star/watch/fork action"], examples: ["比较 Free 和 Pro 私有仓库上限。", "查 Copilot Individual 年费和功能。", "进入 Sign up 检查 test123@gmail.com 是否已存在。"], verification: "状态动作要返回确认消息或状态页；价格题要有 plan 名和数值。", risks: "账号动作要使用测试账号和可 reset 状态。"}
    ]
  },
  google_flights: {
    title: "Google Flights",
    thesis: "Google Flights 是最适合大规模参数化造题的站点，航线、日期、舱位、经停、价格、排放、图表和 booking options 都能组合。",
    variants: [
      { name: "航线日期搜索", infrastructure: "Flight 表有 126,872 条数据，Airport 表支持 IATA/city resolve；/flights 支持 from/to/depart/return/passengers/class。", knobs: ["出发地", "目的地", "出发日期", "返程日期", "单程/往返", "乘客", "舱位"], examples: ["JFK 到 Heathrow，Jan 22，找最低单程票。", "Chicago 到 London，Dec 20 出发 Dec 23 返回。", "Tel Aviv 到 Venice，First Class，指定日期往返。"], verification: "答案包含航空公司、时间、价格、经停和日期。", risks: "生成前必须查航班表确认组合有结果。" },
      { name: "排序、筛选和比较", infrastructure: "支持 max_stops、class、min/max price、airline、sort=price/duration/departure/emissions。", knobs: ["排序方式", "经停上限", "价格上限", "航空公司", "排放", "飞行时长"], examples: ["Calgary 到 New York，找最低 CO2 航班。", "New York 到 London，只看 nonstop。", "Stockholm 到 Toronto，按最短总时长排序。"], verification: "答案包含排序依据和所选航班字段。", risks: "比较题应限制候选数量，避免长答案。" },
      { name: "Price graph、Date grid、Booking options", infrastructure: "有 price_graph、date_grid、price_insights、flight_detail、booking options。", knobs: ["月份范围", "日期网格", "价格趋势", "booking provider", "最低 provider"], examples: ["Dublin 到 Athens 后查看未来两个月 price graph。", "Lisbon 到 Singapore business class，打开 booking options 找最便宜 provider。", "Johannesburg 到 Toronto，分析未来一个月价格趋势。"], verification: "答案应包含图表趋势或 provider 名/价格。", risks: "图表需要稳定数据标签，避免只靠视觉判断。"}
    ]
  },
  google_map: {
    title: "Google Map",
    thesis: "Google Map 适合附近搜索、地点详情、路线、营业时间、评论和地图操作。",
    variants: [
      { name: "附近地点和类别搜索", infrastructure: "Place、City、Category、search、nearby APIs 支持地点、ZIP、城市、类别、评分、状态和基础信息。", knobs: ["城市/ZIP/地标", "类别", "评分阈值", "营业时间", "品牌", "设施"], examples: ["Seattle 找 5 家评分 >4.8 的 beauty salons。", "90028 附近找 Apple Stores。", "30309 附近找 5 家 pizza 并按评分排序。"], verification: "答案包含地点名、评分和地址/距离。", risks: "地点名歧义要走 disambiguation。"},
      { name: "路线和距离", infrastructure: "Directions、Route 表、from/to/mode 支持 driving/walking/transit 等路线展示。", knobs: ["起点", "终点", "交通方式", "路线细节", "距离/时间"], examples: ["Central Park Zoo 到 Broadway Theater 最少步行时间。", "SFO 到 Union Square driving route。", "Miami 到 New Orleans 路线详情。"], verification: "答案包含路线方式、时间、距离或关键道路。", risks: "长路线答案要限制步骤数量。"},
      { name: "地点详情、评论和设置/分享", infrastructure: "Place detail 有 reviews、accessibility、amenities、basic info；有 share、print、settings、saved lists。", knobs: ["评论星级", "无障碍", "设施", "分享链接", "打印动作", "设置页面选项"], examples: ["Denver Airport 评价中哪个星级比例最低，并列出 accessibility/amenities。", "Central Park Zoo 生成分享链接。", "查 Google Map search settings 有哪些选项。"], verification: "答案包含详情页字段或操作后生成的链接/状态。", risks: "分享/打印任务需要浏览器权限和确认状态。"}
    ]
  },
  google_search: {
    title: "Google Search",
    thesis: "Google Search 适合受控 SERP 推理、知识卡、垂直搜索、PAA、related queries 和缓存外页阅读，但要严格处理实时性。",
    variants: [
      { name: "知识卡和事实检索", infrastructure: "Topic、KnowledgeFact、SearchResult、PAA、RelatedQuery 支持知识卡和结果列表。", knobs: ["实体", "事实字段", "来源类型", "是否知识卡", "是否 PAA"], examples: ["查 Mount Kilimanjaro elevation。", "查 Tom Brady 单赛季 touchdowns 最高年份。", "查 Trump kids 名字。"], verification: "答案必须出现在知识卡或结果页，包含字段名和值。", risks: "如果页面没显示答案 token，需要补数据或改题。"},
      { name: "垂直搜索和缓存外页", infrastructure: "支持 images/videos/news/maps/shopping/books/finance verticals 和 external_cache snapshots。", knobs: ["垂直类别", "缓存页面", "来源网站", "评论/榜单/文章字段"], examples: ["打开 YouTube 缓存页，回答某视频第一条评论信息。", "查 Inception 的 IMDb 和 Metacritic 分数。", "找一篇解释英美英语区别的文章并总结差异。"], verification: "答案要来自缓存页或垂直搜索结果，不接受真实外网实时结果。", risks: "外部缓存不全时不要造任务。"},
      { name: "趋势/当前值任务", infrastructure: "TrendingTerm、News vertical、topic snapshots 可用，但不是实时 Web。", knobs: ["城市", "月份", "新闻主题", "榜单", "快照日期"], examples: ["浏览 Columbus 月度 trending searches。", "找 New York City 本月前三个 trending topics。", "查 Lakers 最新新闻标题。"], verification: "答案应绑定快照日期和页面列表。", risks: "所有 current/latest 任务必须显示快照日期。"}
    ]
  },
  huggingface: {
    title: "Hugging Face",
    thesis: "Hugging Face 适合模型/数据集/Spaces 发现、文档参数、Inference API、Dataset Viewer 和 pricing 任务。",
    variants: [
      { name: "资源搜索和模型卡抽取", infrastructure: "Repository、Author、Task、search filters 支持 repo_type、task、license、library、language、modality、downloads、likes、updated。", knobs: ["资源类型", "task", "license", "library", "语言", "更新时间", "downloads/likes 排序"], examples: ["找 cc-by-sa-4.0 中 likes 最高的模型。", "找 recipe generation 模型，回答 size 和 tensor type。", "找 2022 更新且 1M+ downloads 的 NER 模型。"], verification: "答案包含 repo slug、筛选字段和模型卡字段。", risks: "搜索结果排序和更新时间要稳定显示。"},
      { name: "Docs、Inference API 和 Spaces", infrastructure: "Docs、repo detail inference widgets、api/inference、Spaces chat、blog、pricing 已有。", knobs: ["文档主题", "参数名", "默认值", "prompt", "Space 问题", "pricing plan"], examples: ["查 LlamaTokenizer 的 spaces_between_special_tokens 类型和默认值。", "用 Inference API 算两句话相似度。", "打开 argilla/notux-chat-ui 问 which team trained you。"], verification: "答案来自文档参数、API 返回或 Space 回复。", risks: "Inference 输出要可复现或按性质评估。"},
      { name: "Dataset Viewer、Papers 和部署状态", infrastructure: "Dataset viewer、papers、collections、deployment cart、endpoints、discussions 可用。", knobs: ["dataset row", "message field", "paper upvotes", "related model/data", "deploy hardware", "endpoint state"], examples: ["打开 ai2lumos/lumos_complex_qa_plan_onetime Dataset Viewer，回答第一条 message.user content。", "查看 Daily Papers 第一篇标题、upvotes 和相关模型/数据。", "把模型加入 deploy cart 并核对硬件配置。"], verification: "答案包含行号、字段名或部署确认状态。", risks: "Dataset Viewer 需要分页和筛选控件支持更多任务。"}
    ]
  },
  wolfram_alpha: {
    title: "Wolfram Alpha",
    thesis: "Wolfram Alpha 适合预计算型数学、科学、单位、材料、日期和健康估算任务。它不是任意计算引擎，造题必须围绕 computation_results 或先扩充 seed。",
    variants: [
      { name: "数学和符号计算", infrastructure: "ComputationResult 按 query_text 存预计算结果；/input 会匹配 query 并展示 pods。", knobs: ["表达式", "变量值", "精度", "积分/导数/矩阵/级数/几何", "是否比较两个 pod"], examples: ["计算 derivative of x^2 when x=5.6。", "求 6x6 Hilbert matrix determinant。", "求 1000 到 1200 之间所有 prime numbers。"], verification: "答案必须与预计算 pod 一致，数学表达式要归一化。", risks: "未 seed 的 query 不应生成任务。"},
      { name: "科学、材料和单位换算", infrastructure: "已有材料电阻率/导热系数、化学摩尔换算、地磁、发电量、天文等结果。", knobs: ["材料", "温度", "化学物质质量", "地点/日期", "单位", "比较对象"], examples: ["比较 Copper 和 Aluminum 的 thermal conductivity。", "把 15kg sulfuric acid 转成 moles 并给元素百分比。", "查 Diablo Canyon 2 在 2010 的年发电量。"], verification: "答案包含单位和值。", risks: "单位必须写清，避免只答数字。"},
      { name: "生活/健康/日期估算和 notebook 状态", infrastructure: "有个人健康、日期差、货币历史值、notebooks、saved queries、favorites。", knobs: ["年龄/身高/体重", "运动参数", "日期范围", "SPF/地点", "是否保存 query", "notebook 名称"], examples: ["计算 50 岁男性 resting HR 60 的 Heart Rate Reserve。", "计算 2024-02-12 到 2050-08-09 相差天数。", "把多个计算保存到 notebook 并核对条目。"], verification: "答案包含输入条件、结果和单位；状态任务要到 notebook 页面核对。", risks: "天气、金融、太阳暴晒等 current 数据要显示快照日期。"}
    ]
  }
});
