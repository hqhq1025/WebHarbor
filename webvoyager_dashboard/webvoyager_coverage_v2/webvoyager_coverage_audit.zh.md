# WebVoyager 原题到 WebHarbor 造题能力覆盖审计

- 原题数：`643`
- 覆盖状态：`{"full": 501, "full_rewrite": 132, "missing": 8, "partial": 2}`
- 能力标签：`{"calculation": 93, "compare_pair": 51, "current_or_external": 134, "date_time": 204, "detail_lookup": 451, "download_upload_share": 4, "login_auth": 5, "multi_filter": 258, "quiz_or_interactive": 16, "route_or_directions": 28, "set_count": 149, "sort_extreme": 129, "state_action": 32}`
- 缺口：`{"download_upload_share_not_oracle_safe": 4, "missing_capability:current_or_external": 2, "missing_capability:download_upload_share": 4, "missing_capability:login_auth": 1, "missing_capability:quiz_or_interactive": 1, "needs_seeded_snapshot_rewrite": 2, "requires_stable_snapshot_rewrite": 132, "unsupported_surface:external_twitter_login": 1, "unsupported_surface:external_youtube_page": 1, "unsupported_surface:horse racing results": 1, "unsupported_surface:podcasts": 1}`

## 站点覆盖矩阵

| 站点 | 题数 | full | full_rewrite | partial | missing | 主要缺口 | 可用 family |
|---|---:|---:|---:|---:|---:|---|---|
| allrecipes | 45 | 44 | 1 | 0 | 0 | requires_stable_snapshot_rewrite:1 | hard_multistage_readonly, recipe_any_k, recipe_compare_pair, recipe_detail_extract, recipe_exists_with_constraints, shopping_list_state_dbdiff |
| amazon | 41 | 41 | 0 | 0 | 0 | 无 | cart_add_state_dbdiff, hard_multistage_readonly, product_compare_pair, product_exists_with_filters, product_top_k_visible |
| apple | 43 | 24 | 19 | 0 | 0 | requires_stable_snapshot_rewrite:19 | apple_product_compare_pair, apple_product_spec_extract, apple_support_extract, apple_trade_in_lookup, hard_multistage_readonly |
| arxiv | 43 | 22 | 19 | 0 | 2 | requires_stable_snapshot_rewrite:19, download_upload_share_not_oracle_safe:2, missing_capability:download_upload_share:2 | hard_multistage_readonly, library_star_state_dbdiff, paper_compare_pair, paper_count_by_category_date, paper_detail_extract, paper_exists_with_filters |
| bbc_news | 42 | 11 | 27 | 2 | 2 | requires_stable_snapshot_rewrite:27, missing_capability:current_or_external:2, needs_seeded_snapshot_rewrite:2, missing_capability:quiz_or_interactive:1, unsupported_surface:horse racing results:1 | article_compare_pair, article_detail_extract, article_exists_with_filters, article_top_k_visible, hard_multistage_readonly, reading_bookmark_state_dbdiff |
| booking | 44 | 44 | 0 | 0 | 0 | 无 | booking_cart_state_dbdiff, hard_multistage_readonly, hotel_any_k, hotel_compare_pair, hotel_exists_with_filters, hotel_top_k_visible |
| cambridge_dictionary | 43 | 43 | 0 | 0 | 0 | 无 | pronunciation_extract, quiz_action_probe, translation_extract, word_compare_pair, word_definition_lookup |
| coursera | 42 | 41 | 1 | 0 | 0 | requires_stable_snapshot_rewrite:1 | course_compare_pair, course_detail_extract, course_exists_with_filters, hard_multistage_readonly, specialization_subcourse_set, wishlist_state_dbdiff |
| espn | 44 | 19 | 25 | 0 | 0 | requires_stable_snapshot_rewrite:25 | favorite_state_dbdiff, game_detail_extract, game_leader_detail_extract, hard_multistage_readonly, player_stat_extract, scoreboard_fixed_date_set, standings_lookup, team_schedule_extract |
| github | 41 | 30 | 11 | 0 | 0 | requires_stable_snapshot_rewrite:11 | hard_multistage_readonly, repo_compare_pair, repo_detail_extract, repo_exists_with_qualifiers, repo_social_state_dbdiff, repo_top_k_visible |
| google_flights | 42 | 41 | 1 | 0 | 0 | requires_stable_snapshot_rewrite:1 | flight_cart_state_dbdiff, flight_compare_pair, flight_detail_extract, flight_exists_with_filters, flight_top_k_visible, hard_multistage_readonly |
| google_map | 41 | 40 | 0 | 0 | 1 | download_upload_share_not_oracle_safe:1, missing_capability:download_upload_share:1 | directions_distance_time, place_any_k, place_compare_pair, place_exists_with_filters, save_place_state_dbdiff |
| google_search | 43 | 24 | 17 | 0 | 2 | requires_stable_snapshot_rewrite:17, missing_capability:login_auth:1, unsupported_surface:external_twitter_login:1, unsupported_surface:external_youtube_page:1 | bookmark_state_dbdiff, knowledge_panel_extract, serp_answer_lookup, serp_compare_pair, serp_top_k_visible |
| huggingface | 43 | 33 | 9 | 0 | 1 | requires_stable_snapshot_rewrite:9, download_upload_share_not_oracle_safe:1, missing_capability:download_upload_share:1 | hard_multistage_readonly, hf_mock_inference, hf_repo_compare_pair, hf_repo_detail_extract, hf_repo_exists_with_filters, hf_state_dbdiff |
| wolfram_alpha | 46 | 44 | 2 | 0 | 0 | requires_stable_snapshot_rewrite:2 | computation_compare_pair, computation_exact_lookup, computation_variant_lookup, hard_multistage_readonly, pod_extract, saved_query_state_dbdiff |

## 缺口样例

### `download_upload_share_not_oracle_safe`
- `ArXiv--18` `arxiv` `missing`: Download the paper 'Dense Passage Retrieval for Open-Domain Question Answering'. How many formulas are in the article and which one is the loss function?
- `ArXiv--41` `arxiv` `missing`: Find the button to share arxiv non-profit store and follow the QR code to share the shop. Then add arXiv Forever short sleeve (XL) to your cart.
- `Google Map--31` `google_map` `missing`: First search New York's Central Park Zoo on Google Map, and then find the way to share the map. What is the generated sharing link?
- `Huggingface--9` `huggingface` `missing`: Find the most download machine translation model on Huggingface which focuses on English and Japanese (en-ja) and report the evaluation metrics stated for it.

### `missing_capability:current_or_external`
- `BBC News--29` `bbc_news` `partial`: Visit BBC News Audio and find out which podcast episode is currently featured as the "New Releases".
- `BBC News--39` `bbc_news` `missing`: Check the Horse Racing results in Sport section, browse all the games that took place yesterday and see which one had the highest number of runners.

### `missing_capability:download_upload_share`
- `ArXiv--18` `arxiv` `missing`: Download the paper 'Dense Passage Retrieval for Open-Domain Question Answering'. How many formulas are in the article and which one is the loss function?
- `ArXiv--41` `arxiv` `missing`: Find the button to share arxiv non-profit store and follow the QR code to share the shop. Then add arXiv Forever short sleeve (XL) to your cart.
- `Google Map--31` `google_map` `missing`: First search New York's Central Park Zoo on Google Map, and then find the way to share the map. What is the generated sharing link?
- `Huggingface--9` `huggingface` `missing`: Find the most download machine translation model on Huggingface which focuses on English and Japanese (en-ja) and report the evaluation metrics stated for it.

### `missing_capability:login_auth`
- `Google Search--15` `google_search` `missing`: Please try to log in to twitter with email: webagenttest@testmail.com and password: test123456. Let me know if the login was successful.

### `missing_capability:quiz_or_interactive`
- `BBC News--41` `bbc_news` `partial`: Find Golf in BBC News, check the Leaderboard at this point in Women's Majors and count which country has the most players in the top 20? Which player has the best score amongst the Australian players and in what place.

### `needs_seeded_snapshot_rewrite`
- `BBC News--29` `bbc_news` `partial`: Visit BBC News Audio and find out which podcast episode is currently featured as the "New Releases".
- `BBC News--39` `bbc_news` `missing`: Check the Horse Racing results in Sport section, browse all the games that took place yesterday and see which one had the highest number of runners.

### `requires_stable_snapshot_rewrite`
- `Allrecipes--17` `allrecipes` `full_rewrite`: Find the Easy Vegetarian Spinach Lasagna recipe on Allrecipes and tell me what the latest review says.
- `Apple--0` `apple` `full_rewrite`: Compare the prices of the latest models of MacBook Air available on Apple's website.
- `Apple--3` `apple` `full_rewrite`: Find the latest model of the iPhone and compare the price and screen size between the pro and pro max.
- `Apple--5` `apple` `full_rewrite`: Check the release date and price for the latest version of the iPhone.
- `Apple--6` `apple` `full_rewrite`: Find AirPods on Apple and how many types are currently available.
- `Apple--8` `apple` `full_rewrite`: Identify and list the specifications of the latest iPad model released by Apple, including its storage options, processor type, and display features.
- `Apple--9` `apple` `full_rewrite`: Check the Apple Store for the availability of the latest iPhone model and schedule an in-store pickup at the nearest Apple Store for January 10, 2024.
- `Apple--10` `apple` `full_rewrite`: Find information on the latest (as of today's date) MacBook model, including its key features such as processor type, memory size, and storage capacity.

### `unsupported_surface:external_twitter_login`
- `Google Search--15` `google_search` `missing`: Please try to log in to twitter with email: webagenttest@testmail.com and password: test123456. Let me know if the login was successful.

### `unsupported_surface:external_youtube_page`
- `Google Search--8` `google_search` `missing`: Find the video on YouTube: 'Oscars 2023: Must-See Moments!'. Tell me who the first comment displayed under that video belongs to, and how many thumbs up and replies it has.

### `unsupported_surface:horse racing results`
- `BBC News--39` `bbc_news` `missing`: Check the Horse Racing results in Sport section, browse all the games that took place yesterday and see which one had the highest number of runners.

### `unsupported_surface:podcasts`
- `BBC News--18` `bbc_news` `missing`: Visit BBC News Audio, What are the best PodCasts for 2023? List 2 of them.

## 判定规则

- `full`: 当前 train/smoke family 能覆盖题目的主要能力，且 DB/oracle 可批量生成同类任务。
- `full_rewrite`: 当前能力可覆盖，但 WebVoyager 原题有 latest/current/today 这类不稳定措辞，生成时要改成 seeded snapshot 或绝对日期。
- `partial`: 可覆盖主要 read-only 或状态子任务，但缺少某个 WebVoyager 原题要求，例如 live/current、外部站、真实下载、share link、quiz、复杂 count。
- `missing`: 当前 WebHarbor mirror 或 oracle 不支持该题型，硬造会变成不可验证或不稳定任务。