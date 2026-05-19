window.WEBVOYAGER_DASHBOARD_DATA = {
  "generated_at": "2026-05-13T03:19:39.251893+00:00",
  "repos": {
    "webharbor": {
      "path": "/home/v-haoqiwang/repos/WebHarbor",
      "commit": "3c408d8 (HEAD -> main, origin/main, origin/HEAD) init",
      "branch": "main",
      "status": "M sites/booking/templates/index.html\n?? audit_screens/\n?? webvoyager_dashboard/",
      "size": "50M"
    },
    "webvoyager": {
      "path": "/home/v-haoqiwang/repos/WebVoyager",
      "commit": "5a78967 (HEAD -> main, origin/main, origin/HEAD) change LICENSE",
      "branch": "main",
      "status": "",
      "size": "55M"
    }
  },
  "infra": {
    "docker": {
      "container": "webharbor-audit|battalion7244/webharbor:latest|Up 10 hours|0.0.0.0:8311->8101/tcp, [::]:8311->8101/tcp, 0.0.0.0:43000->40000/tcp, [::]:43000->40000/tcp, 0.0.0.0:43001->40001/tcp, [::]:43001->40001/tcp, 0.0.0.0:43002->40002/tcp, [::]:43002->40002/tcp, 0.0.0.0:43003->40003/tcp, [::]:43003->40003/tcp, 0.0.0.0:43004->40004/tcp, [::]:43004->40004/tcp, 0.0.0.0:43005->40005/tcp, [::]:43005->40005/tcp, 0.0.0.0:43006->40006/tcp, [::]:43006->40006/tcp, 0.0.0.0:43007->40007/tcp, [::]:43007->40007/tcp, 0.0.0.0:43008->40008/tcp, [::]:43008->40008/tcp, 0.0.0.0:43009->40009/tcp, [::]:43009->40009/tcp, 0.0.0.0:43010->40010/tcp, [::]:43010->40010/tcp, 0.0.0.0:43011->40011/tcp, [::]:43011->40011/tcp, 0.0.0.0:43012->40012/tcp, [::]:43012->40012/tcp, 0.0.0.0:43013->40013/tcp, [::]:43013->40013/tcp, 0.0.0.0:43014->40014/tcp, [::]:43014->40014/tcp",
      "image": "sha256:f45bb5a06e784d3e3dcea3d5e28092bac02c723cfc1e47b5e7330d964d848590|2759517357|2026-05-11T09:56:08.497001613-04:00",
      "health": {
        "ok": true,
        "sites": {
          "allrecipes": {
            "alive": true,
            "pid": 39,
            "port": 40000
          },
          "amazon": {
            "alive": true,
            "pid": 210,
            "port": 40001
          },
          "apple": {
            "alive": true,
            "pid": 41,
            "port": 40002
          },
          "arxiv": {
            "alive": true,
            "pid": 42,
            "port": 40003
          },
          "bbc_news": {
            "alive": true,
            "pid": 43,
            "port": 40004
          },
          "booking": {
            "alive": true,
            "pid": 993,
            "port": 40005
          },
          "cambridge_dictionary": {
            "alive": true,
            "pid": 51,
            "port": 40012
          },
          "coursera": {
            "alive": true,
            "pid": 52,
            "port": 40013
          },
          "espn": {
            "alive": true,
            "pid": 999,
            "port": 40014
          },
          "github": {
            "alive": true,
            "pid": 45,
            "port": 40006
          },
          "google_flights": {
            "alive": true,
            "pid": 46,
            "port": 40007
          },
          "google_map": {
            "alive": true,
            "pid": 47,
            "port": 40008
          },
          "google_search": {
            "alive": true,
            "pid": 48,
            "port": 40009
          },
          "huggingface": {
            "alive": true,
            "pid": 49,
            "port": 40010
          },
          "wolfram_alpha": {
            "alive": true,
            "pid": 50,
            "port": 40011
          }
        }
      }
    },
    "sites": [
      {
        "slug": "allrecipes",
        "display": "Allrecipes",
        "task_count": 45,
        "golden": 4,
        "possible": 41,
        "avg_complexity": 7.07,
        "avg_question_length": 158.0,
        "state_tasks": 10,
        "navigation_tasks": 3,
        "actions": {
          "find": 39,
          "filter_sort": 33,
          "answer": 22,
          "search": 12,
          "save_state": 10,
          "plan": 1
        },
        "domains": {
          "shopping": 28,
          "general": 17,
          "research": 16,
          "local_maps": 1
        },
        "code": {
          "routes": 41,
          "models": 7,
          "forms": 0,
          "templates": 19,
          "app_lines": 2830,
          "has_health": true,
          "has_js": true
        },
        "db": {
          "db_file": "allrecipes.db",
          "db_bytes": 1482752,
          "tables": 7,
          "top_tables": [
            [
              "review",
              9629
            ],
            [
              "recipe",
              222
            ],
            [
              "user",
              60
            ],
            [
              "recipe_box_item",
              17
            ],
            [
              "category",
              14
            ],
            [
              "meal_plan_item",
              14
            ],
            [
              "shopping_list",
              4
            ]
          ]
        },
        "assets": {
          "static_images": {
            "bytes": 87261655,
            "files": 323
          },
          "static_external_cache": {
            "bytes": 0,
            "files": 0
          }
        },
        "browser": {
          "site": "allrecipes",
          "url": "http://localhost:43000/",
          "title": "Home | Recipes, How-Tos, Videos and More",
          "chars": 1919,
          "links": 94,
          "forms": 1,
          "buttons": 16,
          "images": 21,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 0,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 4039,
          "viewportOverflow": false,
          "sampleText": "all recipes 🔍 Log In Sign Up All Recipes Dinners Breakfast Appetizers Desserts Chicken Pasta Salads Soups Seafood Baking Healthy Occasions Collections About Waffles This waffle recipe is the only one you'll need to make homemade waffles wi",
          "networkFailures": [],
          "badResponses": [],
          "consoleErrors": [
            {
              "type": "error",
              "text": "Failed to load resource: the server responded with a status of 404 (NOT FOUND)"
            }
          ]
        },
        "health": {
          "alive": true,
          "pid": 39,
          "port": 40000
        },
        "docker_port": 40000,
        "local_port": 43000,
        "local_url": "http://localhost:43000/",
        "task_file": "sites/allrecipes/tasks.jsonl",
        "screenshot": "assets/audit_screens/allrecipes-home.png"
      },
      {
        "slug": "amazon",
        "display": "Amazon",
        "task_count": 41,
        "golden": 1,
        "possible": 40,
        "avg_complexity": 7.02,
        "avg_question_length": 128.8,
        "state_tasks": 8,
        "navigation_tasks": 14,
        "actions": {
          "filter_sort": 32,
          "find": 31,
          "search": 13,
          "answer": 7,
          "save_state": 4,
          "book_buy": 4,
          "use_tool": 1,
          "compare": 1
        },
        "domains": {
          "general": 21,
          "shopping": 19,
          "research": 9,
          "travel": 3
        },
        "code": {
          "routes": 46,
          "models": 12,
          "forms": 8,
          "templates": 29,
          "app_lines": 1669,
          "has_health": true,
          "has_js": true
        },
        "db": {
          "db_file": "amazon_store.db",
          "db_bytes": 1847296,
          "tables": 12,
          "top_tables": [
            [
              "reviews",
              8146
            ],
            [
              "products",
              407
            ],
            [
              "users",
              35
            ],
            [
              "order_items",
              12
            ],
            [
              "orders",
              10
            ],
            [
              "categories",
              8
            ],
            [
              "payment_methods",
              8
            ],
            [
              "saved_addresses",
              8
            ]
          ]
        },
        "assets": {
          "static_images": {
            "bytes": 67346746,
            "files": 1388
          },
          "static_external_cache": {
            "bytes": 0,
            "files": 0
          }
        },
        "browser": {
          "site": "amazon",
          "url": "http://localhost:43001/",
          "title": "Amazon.com. Spend less. Smile more.",
          "chars": 3479,
          "links": 104,
          "forms": 1,
          "buttons": 1,
          "images": 50,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 0,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 3297,
          "viewportOverflow": false,
          "sampleText": "amazon. 📍 Deliver to United States All Electronics Books Home Fashion Beauty 🔍 EN 🌐 Hello, sign in Account & Lists ▾ Returns & Orders 🛒 0 Cart ☰ All Today's Deals Customer Service Registry Gift Cards Sell Electronics Computers Home & Ki",
          "networkFailures": [],
          "badResponses": [],
          "consoleErrors": []
        },
        "health": {
          "alive": true,
          "pid": 210,
          "port": 40001
        },
        "docker_port": 40001,
        "local_port": 43001,
        "local_url": "http://localhost:43001/",
        "task_file": "sites/amazon/tasks.jsonl",
        "screenshot": "assets/audit_screens/amazon-home.png"
      },
      {
        "slug": "apple",
        "display": "Apple",
        "task_count": 43,
        "golden": 7,
        "possible": 36,
        "avg_complexity": 2.95,
        "avg_question_length": 101.6,
        "state_tasks": 0,
        "navigation_tasks": 1,
        "actions": {
          "answer": 24,
          "find": 12,
          "compare": 7,
          "filter_sort": 3,
          "plan": 2,
          "search": 2,
          "compute": 1
        },
        "domains": {
          "general": 27,
          "shopping": 11,
          "research": 9,
          "knowledge": 4,
          "local_maps": 1
        },
        "code": {
          "routes": 72,
          "models": 11,
          "forms": 6,
          "templates": 34,
          "app_lines": 2337,
          "has_health": true,
          "has_js": true
        },
        "db": {
          "db_file": "apple_store.db",
          "db_bytes": 147456,
          "tables": 11,
          "top_tables": [
            [
              "product",
              80
            ],
            [
              "trade_in_value",
              21
            ],
            [
              "order",
              18
            ],
            [
              "order_item",
              18
            ],
            [
              "payment_methods",
              10
            ],
            [
              "saved_addresses",
              10
            ],
            [
              "support_article",
              5
            ],
            [
              "user",
              4
            ]
          ]
        },
        "assets": {
          "static_images": {
            "bytes": 601013060,
            "files": 3848
          },
          "static_external_cache": {
            "bytes": 0,
            "files": 0
          }
        },
        "browser": {
          "site": "apple",
          "url": "http://localhost:43002/",
          "title": "Apple",
          "chars": 1330,
          "links": 67,
          "forms": 0,
          "buttons": 1,
          "images": 6,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 26,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 4524,
          "viewportOverflow": false,
          "sampleText": "Store Mac iPad iPhone Watch AirPods Accessories Support iPhone 17 Pro All out Pro. Learn more Buy MacBook Neo Hello, Neo. Amazing Mac. Surprising price. Learn more Buy iPad Air Whoosh. Now supercharged by M4. Learn more Buy NEW Apple Watch ",
          "networkFailures": [],
          "badResponses": [],
          "consoleErrors": [
            {
              "type": "error",
              "text": "Failed to load resource: the server responded with a status of 404 (NOT FOUND)"
            }
          ]
        },
        "health": {
          "alive": true,
          "pid": 41,
          "port": 40002
        },
        "docker_port": 40002,
        "local_port": 43002,
        "local_url": "http://localhost:43002/",
        "task_file": "sites/apple/tasks.jsonl",
        "screenshot": "assets/audit_screens/apple-home.png"
      },
      {
        "slug": "arxiv",
        "display": "ArXiv",
        "task_count": 43,
        "golden": 16,
        "possible": 27,
        "avg_complexity": 3.0,
        "avg_question_length": 124.8,
        "state_tasks": 0,
        "navigation_tasks": 4,
        "actions": {
          "answer": 25,
          "find": 22,
          "search": 12,
          "filter_sort": 8,
          "use_tool": 1
        },
        "domains": {
          "research": 40,
          "knowledge": 10,
          "general": 2,
          "shopping": 1,
          "travel": 1
        },
        "code": {
          "routes": 54,
          "models": 9,
          "forms": 0,
          "templates": 29,
          "app_lines": 2504,
          "has_health": true,
          "has_js": true
        },
        "db": {
          "db_file": "arxiv.db",
          "db_bytes": 4009984,
          "tables": 9,
          "top_tables": [
            [
              "papers",
              1721
            ],
            [
              "library_items",
              29
            ],
            [
              "categories",
              20
            ],
            [
              "starred_papers",
              14
            ],
            [
              "export_items",
              12
            ],
            [
              "alerts",
              6
            ],
            [
              "exports",
              5
            ],
            [
              "users",
              5
            ]
          ]
        },
        "assets": {
          "static_images": {
            "bytes": 66933379,
            "files": 108
          },
          "static_external_cache": {
            "bytes": 0,
            "files": 0
          }
        },
        "browser": {
          "site": "arxiv",
          "url": "http://localhost:43003/",
          "title": "arXiv.org e-Print archive",
          "chars": 5688,
          "links": 266,
          "forms": 2,
          "buttons": 2,
          "images": 2,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 0,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 2146,
          "viewportOverflow": false,
          "sampleText": "Learn about arXiv becoming an independent nonprofit. We gratefully acknowledge support from the Simons Foundation, member institutions, and all contributors. Donate All fields Title Author Abstract arXiv ID Search Help | Advanced Search | N",
          "networkFailures": [],
          "badResponses": [],
          "consoleErrors": []
        },
        "health": {
          "alive": true,
          "pid": 42,
          "port": 40003
        },
        "docker_port": 40003,
        "local_port": 43003,
        "local_url": "http://localhost:43003/",
        "task_file": "sites/arxiv/tasks.jsonl",
        "screenshot": "assets/audit_screens/arxiv-home.png"
      },
      {
        "slug": "bbc_news",
        "display": "BBC News",
        "task_count": 42,
        "golden": 2,
        "possible": 40,
        "avg_complexity": 2.64,
        "avg_question_length": 111.4,
        "state_tasks": 1,
        "navigation_tasks": 4,
        "actions": {
          "find": 22,
          "answer": 19,
          "filter_sort": 8,
          "search": 5,
          "use_tool": 1,
          "plan": 1,
          "book_buy": 1
        },
        "domains": {
          "knowledge": 30,
          "general": 10,
          "research": 2,
          "shopping": 2
        },
        "code": {
          "routes": 46,
          "models": 10,
          "forms": 0,
          "templates": 22,
          "app_lines": 1939,
          "has_health": true,
          "has_js": true
        },
        "db": {
          "db_file": "bbc_news.db",
          "db_bytes": 1699840,
          "tables": 10,
          "top_tables": [
            [
              "articles",
              360
            ],
            [
              "categories",
              55
            ],
            [
              "reading_list_items",
              33
            ],
            [
              "digest_items",
              31
            ],
            [
              "bookmarks",
              20
            ],
            [
              "digests",
              8
            ],
            [
              "topic_subscriptions",
              8
            ],
            [
              "users",
              5
            ]
          ]
        },
        "assets": {
          "static_images": {
            "bytes": 278344612,
            "files": 2029
          },
          "static_external_cache": {
            "bytes": 0,
            "files": 0
          }
        },
        "browser": {
          "site": "bbc_news",
          "url": "http://localhost:43004/",
          "title": "BBC News - Breaking news, world news, video and analysis",
          "chars": 8245,
          "links": 144,
          "forms": 1,
          "buttons": 1,
          "images": 34,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 1,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 6441,
          "viewportOverflow": false,
          "sampleText": "B B C Home News Sport Business Innovation Culture Arts Travel Earth Audio Video Live Register Sign In News Home UK World Business Politics Tech Science Health Entertainment Earth In Pictures BBC Verify Weather War Home News Sport Business I",
          "networkFailures": [],
          "badResponses": [],
          "consoleErrors": []
        },
        "health": {
          "alive": true,
          "pid": 43,
          "port": 40004
        },
        "docker_port": 40004,
        "local_port": 43004,
        "local_url": "http://localhost:43004/",
        "task_file": "sites/bbc_news/tasks.jsonl",
        "screenshot": "assets/audit_screens/bbc_news-home.png"
      },
      {
        "slug": "booking",
        "display": "Booking",
        "task_count": 44,
        "golden": 2,
        "possible": 42,
        "avg_complexity": 6.95,
        "avg_question_length": 147.0,
        "state_tasks": 5,
        "navigation_tasks": 13,
        "actions": {
          "find": 31,
          "filter_sort": 24,
          "search": 18,
          "answer": 8,
          "book_buy": 3,
          "save_state": 2,
          "plan": 2,
          "compute": 1,
          "use_tool": 1
        },
        "domains": {
          "travel": 41,
          "shopping": 20,
          "local_maps": 7,
          "knowledge": 4,
          "general": 2
        },
        "code": {
          "routes": 53,
          "models": 12,
          "forms": 6,
          "templates": 34,
          "app_lines": 3381,
          "has_health": true,
          "has_js": true
        },
        "db": {
          "db_file": "booking.db",
          "db_bytes": 1282048,
          "tables": 12,
          "top_tables": [
            [
              "review",
              1289
            ],
            [
              "property",
              325
            ],
            [
              "landmark",
              68
            ],
            [
              "city",
              33
            ],
            [
              "booking",
              10
            ],
            [
              "booking_item",
              10
            ],
            [
              "payment_methods",
              10
            ],
            [
              "dest_category",
              8
            ]
          ]
        },
        "assets": {
          "static_images": {
            "bytes": 403797029,
            "files": 2725
          },
          "static_external_cache": {
            "bytes": 0,
            "files": 0
          }
        },
        "browser": {
          "site": "booking",
          "url": "http://localhost:43005/",
          "title": "Booking — Hotels, Homes, Flights, Car Hire & More",
          "chars": 4006,
          "links": 81,
          "forms": 2,
          "buttons": 1,
          "images": 20,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 16,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 5406,
          "viewportOverflow": false,
          "sampleText": "Booking.com Currency USD EUR GBP CNY JPY Help List your property Register Sign in Stays Flights Car rentals Attractions Airport taxis Find your next stay Search low prices on hotels, homes and much more... 1 adult 2 adults 3 adults 4 adults",
          "networkFailures": [],
          "badResponses": [],
          "consoleErrors": []
        },
        "health": {
          "alive": true,
          "pid": 993,
          "port": 40005
        },
        "docker_port": 40005,
        "local_port": 43005,
        "local_url": "http://localhost:43005/",
        "task_file": "sites/booking/tasks.jsonl",
        "screenshot": "assets/audit_screens/booking-home.png"
      },
      {
        "slug": "github",
        "display": "GitHub",
        "task_count": 41,
        "golden": 14,
        "possible": 27,
        "avg_complexity": 4.63,
        "avg_question_length": 116.7,
        "state_tasks": 0,
        "navigation_tasks": 16,
        "actions": {
          "find": 29,
          "filter_sort": 20,
          "answer": 16,
          "search": 7,
          "compare": 2,
          "use_tool": 1
        },
        "domains": {
          "research": 22,
          "shopping": 16,
          "general": 15,
          "knowledge": 2
        },
        "code": {
          "routes": 64,
          "models": 7,
          "forms": 7,
          "templates": 46,
          "app_lines": 3331,
          "has_health": true,
          "has_js": true
        },
        "db": {
          "db_file": "github_mirror.db",
          "db_bytes": 6266880,
          "tables": 9,
          "top_tables": [
            [
              "issue",
              3076
            ],
            [
              "repo_topics",
              1960
            ],
            [
              "repository",
              685
            ],
            [
              "topic",
              626
            ],
            [
              "user",
              576
            ],
            [
              "follows",
              29
            ],
            [
              "star",
              27
            ],
            [
              "issue_comment",
              15
            ]
          ]
        },
        "assets": {
          "static_images": {
            "bytes": 75318625,
            "files": 525
          },
          "static_external_cache": {
            "bytes": 0,
            "files": 0
          }
        },
        "browser": {
          "site": "github",
          "url": "http://localhost:43006/",
          "title": "GitHub: Let's build from here · GitHub",
          "chars": 2835,
          "links": 65,
          "forms": 1,
          "buttons": 3,
          "images": 8,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 0,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 4549,
          "viewportOverflow": false,
          "sampleText": "Product Open Source Resources Marketplace Pricing Sign in Sign up 📅 Today's date at this site: Wednesday, May 15, 2024 (2024-05-15). All \"recent\" / \"last N days\" filters are relative to this date. The complete developer platform to build, ",
          "networkFailures": [],
          "badResponses": [],
          "consoleErrors": []
        },
        "health": {
          "alive": true,
          "pid": 45,
          "port": 40006
        },
        "docker_port": 40006,
        "local_port": 43006,
        "local_url": "http://localhost:43006/",
        "task_file": "sites/github/tasks.jsonl",
        "screenshot": "assets/audit_screens/github-home.png"
      },
      {
        "slug": "google_flights",
        "display": "Google Flights",
        "task_count": 42,
        "golden": 0,
        "possible": 42,
        "avg_complexity": 6.81,
        "avg_question_length": 148.2,
        "state_tasks": 2,
        "navigation_tasks": 13,
        "actions": {
          "find": 30,
          "filter_sort": 20,
          "plan": 17,
          "answer": 13,
          "search": 10,
          "compare": 9,
          "use_tool": 5,
          "book_buy": 2
        },
        "domains": {
          "travel": 39,
          "shopping": 4,
          "general": 2,
          "local_maps": 1
        },
        "code": {
          "routes": 50,
          "models": 11,
          "forms": 0,
          "templates": 31,
          "app_lines": 2253,
          "has_health": true,
          "has_js": true
        },
        "db": {
          "db_file": "google_flights.db",
          "db_bytes": 33447936,
          "tables": 11,
          "top_tables": [
            [
              "flight",
              126872
            ],
            [
              "airport",
              93
            ],
            [
              "booking",
              12
            ],
            [
              "booking_item",
              12
            ],
            [
              "payment_methods",
              10
            ],
            [
              "price_alert",
              6
            ],
            [
              "tracked_flight",
              6
            ],
            [
              "user",
              4
            ]
          ]
        },
        "assets": {
          "static_images": {
            "bytes": 211973009,
            "files": 397
          },
          "static_external_cache": {
            "bytes": 0,
            "files": 0
          }
        },
        "browser": {
          "site": "google_flights",
          "url": "http://localhost:43007/",
          "title": "Flights | Google Flights",
          "chars": 2830,
          "links": 45,
          "forms": 1,
          "buttons": 14,
          "images": 17,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 5,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 3949,
          "viewportOverflow": false,
          "sampleText": "menu explore Explore flight Flights hotel Hotels holiday_village Vacation rentals Sign in Flights Find and book cheap flights worldwide and track prices sync_alt Round trip trending_flat One way multiple_stop Multi-city swap_horiz 1 adult 2",
          "networkFailures": [],
          "badResponses": [],
          "consoleErrors": []
        },
        "health": {
          "alive": true,
          "pid": 46,
          "port": 40007
        },
        "docker_port": 40007,
        "local_port": 43007,
        "local_url": "http://localhost:43007/",
        "task_file": "sites/google_flights/tasks.jsonl",
        "screenshot": "assets/audit_screens/google_flights-home.png"
      },
      {
        "slug": "google_map",
        "display": "Google Map",
        "task_count": 41,
        "golden": 9,
        "possible": 32,
        "avg_complexity": 3.73,
        "avg_question_length": 85.7,
        "state_tasks": 2,
        "navigation_tasks": 6,
        "actions": {
          "find": 31,
          "plan": 14,
          "search": 10,
          "answer": 7,
          "filter_sort": 5,
          "book_buy": 1,
          "save_state": 1
        },
        "domains": {
          "local_maps": 24,
          "general": 12,
          "travel": 5,
          "shopping": 4
        },
        "code": {
          "routes": 44,
          "models": 12,
          "forms": 0,
          "templates": 30,
          "app_lines": 2855,
          "has_health": true,
          "has_js": true
        },
        "db": {
          "db_file": "gmaps.db",
          "db_bytes": 1261568,
          "tables": 12,
          "top_tables": [
            [
              "place",
              963
            ],
            [
              "city",
              105
            ],
            [
              "trip_stop",
              38
            ],
            [
              "saved_place",
              37
            ],
            [
              "saved_list",
              20
            ],
            [
              "category",
              16
            ],
            [
              "trip",
              14
            ],
            [
              "route",
              10
            ]
          ]
        },
        "assets": {
          "static_images": {
            "bytes": 257445479,
            "files": 818
          },
          "static_external_cache": {
            "bytes": 0,
            "files": 0
          }
        },
        "browser": {
          "site": "google_map",
          "url": "http://localhost:43008/",
          "title": "Google Maps",
          "chars": 3768,
          "links": 41,
          "forms": 1,
          "buttons": 6,
          "images": 12,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 2,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 1000,
          "viewportOverflow": false,
          "sampleText": "menu bookmark Saved explore Explore directions Directions settings Settings help_outline Help menu search directions Explore, save, plan. Find great places to eat, stay, and visit around the world. Save favorites to your lists and build you",
          "networkFailures": [],
          "badResponses": [],
          "consoleErrors": [
            {
              "type": "error",
              "text": "Failed to load resource: the server responded with a status of 404 (NOT FOUND)"
            }
          ]
        },
        "health": {
          "alive": true,
          "pid": 47,
          "port": 40008
        },
        "docker_port": 40008,
        "local_port": 43008,
        "local_url": "http://localhost:43008/",
        "task_file": "sites/google_map/tasks.jsonl",
        "screenshot": "assets/audit_screens/google_map-home.png"
      },
      {
        "slug": "google_search",
        "display": "Google Search",
        "task_count": 43,
        "golden": 16,
        "possible": 27,
        "avg_complexity": 3.19,
        "avg_question_length": 87.1,
        "state_tasks": 2,
        "navigation_tasks": 2,
        "actions": {
          "find": 22,
          "answer": 22,
          "filter_sort": 9,
          "search": 8,
          "save_state": 2,
          "plan": 1,
          "use_tool": 1
        },
        "domains": {
          "general": 27,
          "knowledge": 10,
          "research": 3,
          "travel": 2,
          "shopping": 1
        },
        "code": {
          "routes": 55,
          "models": 15,
          "forms": 8,
          "templates": 47,
          "app_lines": 1847,
          "has_health": true,
          "has_js": true
        },
        "db": {
          "db_file": "google_search.db",
          "db_bytes": 675840,
          "tables": 15,
          "top_tables": [
            [
              "search_result",
              1170
            ],
            [
              "related_query",
              647
            ],
            [
              "knowledge_fact",
              575
            ],
            [
              "paa_question",
              319
            ],
            [
              "topic",
              170
            ],
            [
              "search_history",
              27
            ],
            [
              "alert",
              11
            ],
            [
              "collection",
              8
            ]
          ]
        },
        "assets": {
          "static_images": {
            "bytes": 389506924,
            "files": 815
          },
          "static_external_cache": {
            "bytes": 47377151,
            "files": 3586
          }
        },
        "browser": {
          "site": "google_search",
          "url": "http://localhost:43009/",
          "title": "Google",
          "chars": 210,
          "links": 17,
          "forms": 1,
          "buttons": 3,
          "images": 0,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 6,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 1000,
          "viewportOverflow": false,
          "sampleText": "Trending Doodles Images Sign in Google Google Search I'm Feeling Lucky Google offered in: Español Français Deutsch 日本語 中文 العربية United States About Advertising Business How Search works Privacy Terms Settings",
          "networkFailures": [],
          "badResponses": [],
          "consoleErrors": []
        },
        "health": {
          "alive": true,
          "pid": 48,
          "port": 40009
        },
        "docker_port": 40009,
        "local_port": 43009,
        "local_url": "http://localhost:43009/",
        "task_file": "sites/google_search/tasks.jsonl",
        "screenshot": "assets/audit_screens/google_search-home.png"
      },
      {
        "slug": "huggingface",
        "display": "Huggingface",
        "task_count": 43,
        "golden": 17,
        "possible": 26,
        "avg_complexity": 3.21,
        "avg_question_length": 130.6,
        "state_tasks": 4,
        "navigation_tasks": 10,
        "actions": {
          "answer": 24,
          "find": 18,
          "use_tool": 6,
          "filter_sort": 4,
          "search": 4,
          "save_state": 4,
          "compute": 1
        },
        "domains": {
          "research": 28,
          "general": 15,
          "knowledge": 3,
          "shopping": 1
        },
        "code": {
          "routes": 84,
          "models": 13,
          "forms": 8,
          "templates": 49,
          "app_lines": 2935,
          "has_health": true,
          "has_js": true
        },
        "db": {
          "db_file": "hf.db",
          "db_bytes": 1761280,
          "tables": 13,
          "top_tables": [
            [
              "repositories",
              678
            ],
            [
              "authors",
              277
            ],
            [
              "tasks",
              39
            ],
            [
              "collection_items",
              27
            ],
            [
              "discussions",
              20
            ],
            [
              "likes",
              20
            ],
            [
              "discussion_replies",
              12
            ],
            [
              "collections",
              8
            ]
          ]
        },
        "assets": {
          "static_images": {
            "bytes": 126297004,
            "files": 714
          },
          "static_external_cache": {
            "bytes": 0,
            "files": 0
          }
        },
        "browser": {
          "site": "huggingface",
          "url": "http://localhost:43010/",
          "title": "Hugging Face – The AI community building the future.",
          "chars": 3489,
          "links": 57,
          "forms": 1,
          "buttons": 0,
          "images": 18,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 0,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 4105,
          "viewportOverflow": false,
          "sampleText": "🤗 Hugging Face Models Datasets Spaces Papers Docs Blog Learn Enterprise Pricing Log In Sign Up 📅 Today is April 25, 2026. Please treat this as the reference date for any relative time expressions (\"today\", \"yesterday\", \"last week\", \"past ",
          "networkFailures": [],
          "badResponses": [],
          "consoleErrors": []
        },
        "health": {
          "alive": true,
          "pid": 49,
          "port": 40010
        },
        "docker_port": 40010,
        "local_port": 43010,
        "local_url": "http://localhost:43010/",
        "task_file": "sites/huggingface/tasks.jsonl",
        "screenshot": "assets/audit_screens/huggingface-home.png"
      },
      {
        "slug": "wolfram_alpha",
        "display": "Wolfram Alpha",
        "task_count": 46,
        "golden": 34,
        "possible": 12,
        "avg_complexity": 3.74,
        "avg_question_length": 90.4,
        "state_tasks": 2,
        "navigation_tasks": 1,
        "actions": {
          "answer": 26,
          "compute": 14,
          "filter_sort": 3,
          "compare": 2,
          "save_state": 1,
          "find": 1,
          "use_tool": 1,
          "book_buy": 1
        },
        "domains": {
          "general": 32,
          "knowledge": 12,
          "shopping": 2
        },
        "code": {
          "routes": 40,
          "models": 11,
          "forms": 0,
          "templates": 25,
          "app_lines": 1719,
          "has_health": true,
          "has_js": true
        },
        "db": {
          "db_file": "wolfram_alpha.db",
          "db_bytes": 360448,
          "tables": 11,
          "top_tables": [
            [
              "computation_results",
              163
            ],
            [
              "subcategories",
              28
            ],
            [
              "query_history",
              27
            ],
            [
              "notebook_entries",
              24
            ],
            [
              "topics",
              23
            ],
            [
              "saved_queries",
              20
            ],
            [
              "favorites",
              19
            ],
            [
              "notebooks",
              8
            ]
          ]
        },
        "assets": {
          "static_images": {
            "bytes": 47457466,
            "files": 169
          },
          "static_external_cache": {
            "bytes": 0,
            "files": 0
          }
        },
        "browser": {
          "site": "wolfram_alpha",
          "url": "http://localhost:43011/",
          "title": "WolframAlpha: Computational Intelligence",
          "chars": 1359,
          "links": 72,
          "forms": 1,
          "buttons": 2,
          "images": 3,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 14,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 1320,
          "viewportOverflow": false,
          "sampleText": "UPGRADE TO PRO ▾ APPS ▾ TOUR Sign in FROM THE MAKERS OF WOLFRAM LANGUAGE AND MATHEMATICA WolframAlpha ≡ ✱ NATURAL LANGUAGE ∫ Σ MATH INPUT ☉ ⌨ EXTENDED KEYBOARD ⊞ EXAMPLES ⬆ UPLOAD ⚄ RANDOM Compute expert-level answers using Wolfram’s breakt",
          "networkFailures": [],
          "badResponses": [],
          "consoleErrors": []
        },
        "health": {
          "alive": true,
          "pid": 50,
          "port": 40011
        },
        "docker_port": 40011,
        "local_port": 43011,
        "local_url": "http://localhost:43011/",
        "task_file": "sites/wolfram_alpha/tasks.jsonl",
        "screenshot": "assets/audit_screens/wolfram_alpha-home.png"
      },
      {
        "slug": "cambridge_dictionary",
        "display": "Cambridge Dictionary",
        "task_count": 43,
        "golden": 9,
        "possible": 34,
        "avg_complexity": 2.67,
        "avg_question_length": 122.0,
        "state_tasks": 1,
        "navigation_tasks": 4,
        "actions": {
          "find": 36,
          "search": 9,
          "answer": 9,
          "use_tool": 7,
          "filter_sort": 1,
          "save_state": 1,
          "compute": 1
        },
        "domains": {
          "knowledge": 40,
          "general": 3
        },
        "code": {
          "routes": 25,
          "models": 7,
          "forms": 5,
          "templates": 22,
          "app_lines": 2465,
          "has_health": true,
          "has_js": true
        },
        "db": {
          "db_file": "cambridge.db",
          "db_bytes": 5591040,
          "tables": 7,
          "top_tables": [
            [
              "words",
              1821
            ],
            [
              "saved_words",
              29
            ],
            [
              "search_history",
              23
            ],
            [
              "grammar_topics",
              8
            ],
            [
              "shop_items",
              8
            ],
            [
              "users",
              4
            ],
            [
              "quizzes",
              3
            ]
          ]
        },
        "assets": {
          "static_images": {
            "bytes": 7981094,
            "files": 73
          },
          "static_external_cache": {
            "bytes": 0,
            "files": 0
          }
        },
        "browser": {
          "site": "cambridge_dictionary",
          "url": "http://localhost:43012/",
          "title": "Cambridge Dictionary | Online Dictionary & Thesaurus | Cambridge Dictionary",
          "chars": 1578,
          "links": 42,
          "forms": 2,
          "buttons": 1,
          "images": 0,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 5,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 1659,
          "viewportOverflow": false,
          "sampleText": "Cambridge Dictionary Dictionary Thesaurus Translate Grammar Plus Shop Sign in Register English (UK) Deutsch Español Français Italiano 中文 日本語 Polski Português Nederlands Cambridge Dictionary Dictionary Thesaurus Translate Grammar Find the pe",
          "networkFailures": [],
          "badResponses": [],
          "consoleErrors": [
            {
              "type": "error",
              "text": "Failed to load resource: the server responded with a status of 404 (NOT FOUND)"
            }
          ]
        },
        "health": {
          "alive": true,
          "pid": 51,
          "port": 40012
        },
        "docker_port": 40012,
        "local_port": 43012,
        "local_url": "http://localhost:43012/",
        "task_file": "sites/cambridge_dictionary/tasks.jsonl",
        "screenshot": "assets/audit_screens/cambridge_dictionary-home.png"
      },
      {
        "slug": "coursera",
        "display": "Coursera",
        "task_count": 42,
        "golden": 2,
        "possible": 40,
        "avg_complexity": 3.74,
        "avg_question_length": 159.2,
        "state_tasks": 3,
        "navigation_tasks": 7,
        "actions": {
          "find": 24,
          "answer": 21,
          "search": 13,
          "filter_sort": 8,
          "save_state": 3
        },
        "domains": {
          "general": 35,
          "shopping": 6,
          "research": 2,
          "knowledge": 1
        },
        "code": {
          "routes": 28,
          "models": 8,
          "forms": 5,
          "templates": 20,
          "app_lines": 2773,
          "has_health": true,
          "has_js": true
        },
        "db": {
          "db_file": "coursera.db",
          "db_bytes": 991232,
          "tables": 8,
          "top_tables": [
            [
              "reviews",
              1440
            ],
            [
              "course_modules",
              981
            ],
            [
              "sub_courses",
              243
            ],
            [
              "courses",
              239
            ],
            [
              "partners",
              49
            ],
            [
              "users",
              25
            ],
            [
              "enrollments",
              20
            ],
            [
              "saved_courses",
              16
            ]
          ]
        },
        "assets": {
          "static_images": {
            "bytes": 96178043,
            "files": 626
          },
          "static_external_cache": {
            "bytes": 0,
            "files": 0
          }
        },
        "browser": {
          "site": "coursera",
          "url": "http://localhost:43013/",
          "title": "Coursera | Build Skills with Online Courses",
          "chars": 3839,
          "links": 88,
          "forms": 1,
          "buttons": 2,
          "images": 65,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 7,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 5000,
          "viewportOverflow": false,
          "sampleText": "Explore ▾ 🔍 Log In Join for Free Learn without limits Start, switch, or advance your career with more than 7,000 courses, Professional Certificates, and degrees from world-class universities and companies. Join for Free Try Coursera Plus L",
          "networkFailures": [],
          "badResponses": [],
          "consoleErrors": [
            {
              "type": "error",
              "text": "Failed to load resource: the server responded with a status of 404 (NOT FOUND)"
            }
          ]
        },
        "health": {
          "alive": true,
          "pid": 52,
          "port": 40013
        },
        "docker_port": 40013,
        "local_port": 43013,
        "local_url": "http://localhost:43013/",
        "task_file": "sites/coursera/tasks.jsonl",
        "screenshot": "assets/audit_screens/coursera-home.png"
      },
      {
        "slug": "espn",
        "display": "ESPN",
        "task_count": 44,
        "golden": 10,
        "possible": 34,
        "avg_complexity": 2.91,
        "avg_question_length": 107.4,
        "state_tasks": 0,
        "navigation_tasks": 2,
        "actions": {
          "answer": 21,
          "filter_sort": 15,
          "find": 13,
          "search": 5,
          "compute": 1
        },
        "domains": {
          "general": 32,
          "knowledge": 10,
          "shopping": 2
        },
        "code": {
          "routes": 47,
          "models": 15,
          "forms": 4,
          "templates": 36,
          "app_lines": 1368,
          "has_health": true,
          "has_js": true
        },
        "db": {
          "db_file": "espn.db",
          "db_bytes": 708608,
          "tables": 15,
          "top_tables": [
            [
              "game_player_stats",
              1789
            ],
            [
              "players",
              1197
            ],
            [
              "games",
              316
            ],
            [
              "articles",
              285
            ],
            [
              "teams",
              142
            ],
            [
              "power_index",
              62
            ],
            [
              "player_stats",
              58
            ],
            [
              "depth_chart",
              48
            ]
          ]
        },
        "assets": {
          "static_images": {
            "bytes": 36442898,
            "files": 426
          },
          "static_external_cache": {
            "bytes": 0,
            "files": 0
          }
        },
        "browser": {
          "site": "espn",
          "url": "http://localhost:43014/",
          "title": "ESPN - Sports News, Scores, Highlights - ESPN",
          "chars": 3328,
          "links": 111,
          "forms": 0,
          "buttons": 0,
          "images": 75,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 0,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 2833,
          "viewportOverflow": false,
          "sampleText": "📅 ESPN Today's date is April 10, 2024. Phrases like “today”, “yesterday”, “recent”, and “latest” on this site, please refer to this fixed date. NFL Scores NBA Scores MLB Scores NHL Scores SOCCER Scores COLLEGE FOOTBALL Scores MEN'S COLLEGE",
          "networkFailures": [],
          "badResponses": [],
          "consoleErrors": []
        },
        "health": {
          "alive": true,
          "pid": 999,
          "port": 40014
        },
        "docker_port": 40014,
        "local_port": 43014,
        "local_url": "http://localhost:43014/",
        "task_file": "sites/espn/tasks.jsonl",
        "screenshot": "assets/audit_screens/espn-home.png"
      }
    ],
    "control_plane": {
      "local": "http://localhost:8311",
      "container": "http://localhost:8101",
      "endpoints": [
        "/health",
        "POST /reset/<site>",
        "POST /reset-all",
        "POST /restart/<site>"
      ]
    },
    "task_alignment": {
      "webharbor_tasks": 643,
      "webvoyager_tasks": 643,
      "ids_equal": true,
      "question_diffs": 0,
      "upstream_diffs": 0
    },
    "browser_scenarios": [
      {
        "name": "amazon-search-xbox-green",
        "startUrl": "http://localhost:43001/",
        "ok": true,
        "resultCards": 0,
        "hasXbox": true,
        "hasGreen": true,
        "hasStars": true,
        "keyText": "amazon. 📍 Deliver to United States All Electronics Books Home Fashion Beauty 🔍 EN 🌐 Hello, sign in Account & Lists ▾ Returns & Orders 🛒 0 Cart ☰ All Today's Deals Customer Service Registry Gift Cards Sell Electronics Computers Home & Kitchen Fashion Books Beauty Sports Toys Department Electronics Computers Home & Kitchen Fashion Books Beauty Sports Toys Customer Reviews ★★★★☆ & Up ★★★☆☆ & Up ★★☆☆☆ & Up ★☆☆☆☆ & Up Clear rating filter Price — Go Brand Apply Condition New Used - Like New Used -",
        "finalUrl": "http://localhost:43001/search?dept=All&q=Xbox+Wireless+controller+green+rated+above+4+stars",
        "stats": {
          "title": "Xbox Wireless controller green rated above 4 stars - Amazon.com Search",
          "chars": 2202,
          "links": 66,
          "forms": 6,
          "buttons": 9,
          "images": 4,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 0,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 1857,
          "viewportOverflow": false,
          "sampleText": "amazon. 📍 Deliver to United States All Electronics Books Home Fashion Beauty 🔍 EN 🌐 Hello, sign in Account & Lists ▾ Returns & Orders 🛒 0 Cart ☰ All Today's Deals Customer Service Registry Gift Cards Sell Electronics Computers Home & Ki"
        },
        "networkFailures": [],
        "badResponses": [],
        "consoleErrors": []
      },
      {
        "name": "booking-search-paris-breakfast",
        "startUrl": "http://localhost:43005/",
        "ok": true,
        "hotelCards": 66,
        "hasParis": true,
        "hasBreakfast": true,
        "hasPrice": true,
        "keyText": "Booking.com Currency USD EUR GBP CNY JPY Help List your property Register Sign in Stays Flights Car rentals Attractions Airport taxis Search results 11 properties found for \"Paris\" Keyword / destination City Any New York, United States Paris, France London, United Kingdom Tokyo, Japan Dubai, United Arab Emirates Rome, Italy Barcelona, Spain Bali, Indonesia Amsterdam, Netherlands Singapore, Singapore Maldives, Maldives Bangkok, Thailand Hong Kong, Hong Kong Istanbul, Turkey Sydney, Australia Los Angeles, United States Berlin, Germany Prague, Czech Republic Vienna, Austria Venice, Italy Santorin",
        "finalUrl": "http://localhost:43005/search?q=Paris&checkin=2024-12-25&checkout=2024-12-26&adults=2&breakfast=1&sort=price_low",
        "stats": {
          "title": "Search results — Booking",
          "chars": 4294,
          "links": 52,
          "forms": 3,
          "buttons": 1,
          "images": 11,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 16,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 3788,
          "viewportOverflow": false,
          "sampleText": "Booking.com Currency USD EUR GBP CNY JPY Help List your property Register Sign in Stays Flights Car rentals Attractions Airport taxis Search results 11 properties found for \"Paris\" Keyword / destination City Any New York, United States Pari"
        },
        "networkFailures": [],
        "badResponses": [
          {
            "status": 404,
            "url": "http://localhost:43005/static/images/gallery/paris/paris_1.jpg"
          },
          {
            "status": 404,
            "url": "http://localhost:43005/static/images/gallery/bali/bali_1.jpg"
          },
          {
            "status": 404,
            "url": "http://localhost:43005/static/images/gallery/paris/paris_2.jpg"
          }
        ],
        "consoleErrors": [
          {
            "type": "error",
            "text": "Failed to load resource: the server responded with a status of 404 (NOT FOUND)"
          },
          {
            "type": "error",
            "text": "Failed to load resource: the server responded with a status of 404 (NOT FOUND)"
          },
          {
            "type": "error",
            "text": "Failed to load resource: the server responded with a status of 404 (NOT FOUND)"
          }
        ]
      },
      {
        "name": "google-flights-jfk-lhr",
        "startUrl": "http://localhost:43007/",
        "ok": true,
        "flightRows": 92,
        "hasJFK": true,
        "hasHeathrow": true,
        "hasPrice": true,
        "keyText": "menu explore Explore flight Flights hotel Hotels holiday_village Vacation rentals Sign in search Search Filters Stops Any number of stops Nonstop only 1 stop or fewer 2 stops or fewer Cabin class Any Economy Premium economy Business First class Price range Airline Any airline ANA Air Canada Air France Alaska Airlines American Airlines British Airways Cathay Pacific Delta Emirates Etihad Frontier Iberia Japan Airlines JetBlue KLM Lufthansa Qantas Qatar Airways Singapore Airlines Southwest Spirit Turkish Airlines United Apply filters Clear filters insights View price graph New York to London 46 results - sorted by Top flights - Economy Best Cheapest Sort by Top flights Price (low to high) Dura",
        "finalUrl": "http://localhost:43007/flights?from=JFK&to=Heathrow&depart=2024-01-22&return=&passengers=1&class=Economy&sort=best",
        "stats": {
          "title": "New York to London flights | Google Flights",
          "chars": 4965,
          "links": 71,
          "forms": 2,
          "buttons": 3,
          "images": 46,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 5,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 5833,
          "viewportOverflow": false,
          "sampleText": "menu explore Explore flight Flights hotel Hotels holiday_village Vacation rentals Sign in search Search Filters Stops Any number of stops Nonstop only 1 stop or fewer 2 stops or fewer Cabin class Any Economy Premium economy Business First c"
        },
        "networkFailures": [],
        "badResponses": [],
        "consoleErrors": []
      },
      {
        "name": "google-map-central-park-directions",
        "startUrl": "http://localhost:43008/directions?from=Central+Park+Zoo&to=Broadway+Theater&mode=walking",
        "ok": true,
        "hasRoute": true,
        "hasWalk": true,
        "keyText": "menu bookmark Saved explore Explore directions Directions settings Settings help_outline Help swap_vert search Get directions directions_car Drive directions_walk Walk directions_bus Transit directions_bike Bike Did you mean? 8 matches for \"Broadway Theater\" — pick a destination from Central Park Zoo Broadway Theatre ★ 4.7 (5,280) · Entertainment · 1681 Broadway, New York, NY 10019 0.7 mi Broadway Dim Sum ★ 4.7 (2,649) · Restaurants · 476 Park Ave, New York 3.5 mi Mokotowska Theater ★ 4.6 (2,436) · Entertainment · 157 Nowy Świat, Warsaw 4254.8 mi Calle Theater ★ 4.5 (2,333) · Entertainment · 403 Paseo del Prado, Madrid 3581.0 mi Via Theater ★ 4.7 (1,027) · Entertainment · 968 Via del Corso, ",
        "finalUrl": "http://localhost:43008/directions?from=Central+Park+Zoo&to=Broadway+Theater&mode=walking",
        "stats": {
          "title": "Directions - Google Maps",
          "chars": 1018,
          "links": 20,
          "forms": 1,
          "buttons": 5,
          "images": 0,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 0,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 1000,
          "viewportOverflow": false,
          "sampleText": "menu bookmark Saved explore Explore directions Directions settings Settings help_outline Help swap_vert search Get directions directions_car Drive directions_walk Walk directions_bus Transit directions_bike Bike Did you mean? 8 matches for "
        },
        "networkFailures": [],
        "badResponses": [],
        "consoleErrors": []
      },
      {
        "name": "github-search-climate-stars",
        "startUrl": "http://localhost:43006/search?q=climate+change+data+visualization&type=repositories",
        "ok": true,
        "repoCount": 132,
        "hasStars": true,
        "hasClimate": true,
        "keyText": "Product Open Source Resources Marketplace Pricing Sign in Sign up 📅 Today's date at this site: Wednesday, May 15, 2024 (2024-05-15). All \"recent\" / \"last N days\" filters are relative to this date. Search FILTER BY Repositories 34 Users Topics LANGUAGES Any — Python 14 JavaScript 7 TypeScript 7 C++ 3 Fortran 1 R 1 Go 1 LICENSE MIT 23 Apache-2.0 5 BSD-3-Clause 3 GPL-3.0 2 GPL-2.0 1 ADVANCED 100+ stars 1k+ stars 10k+ stars Pushed in 2024+ Not archived 34 results for \"climate change data visualization\" Sort by: Best match Most stars Fewest stars Most forks Fewest forks Recently updated Least recently updated climate-viz/climate-change-dashboard Interactive climate change data visualization dash",
        "finalUrl": "http://localhost:43006/search?q=climate+change+data+visualization&type=repositories",
        "stats": {
          "title": "Search · GitHub",
          "chars": 4567,
          "links": 132,
          "forms": 2,
          "buttons": 4,
          "images": 0,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 0,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 2745,
          "viewportOverflow": false,
          "sampleText": "Product Open Source Resources Marketplace Pricing Sign in Sign up 📅 Today's date at this site: Wednesday, May 15, 2024 (2024-05-15). All \"recent\" / \"last N days\" filters are relative to this date. Search FILTER BY Repositories 34 Users Top"
        },
        "networkFailures": [],
        "badResponses": [],
        "consoleErrors": []
      },
      {
        "name": "hf-search-sentiment-march2023",
        "startUrl": "http://localhost:43010/search?q=sentiment+analysis+updated+March+2023&type=model",
        "ok": true,
        "repoCards": 34,
        "hasSentiment": true,
        "hasDate": true,
        "keyText": "🤗 Hugging Face Models Datasets Spaces Papers Docs Blog Learn Enterprise Pricing Log In Sign Up Search All (8) Models Datasets Spaces Sort: Trending Most likes Most downloads Recently updated Recently created License: Any license Apache 2.0 MIT CC BY 4.0 CC BY-SA 4.0 CC BY-NC 4.0 OpenRAIL CreativeML OpenRAIL-M Llama 3.3 Community Gemma BSD 3-Clause GPL-3.0 Other Library: Any library Transformers Diffusers Safetensors PyTorch TensorFlow JAX ONNX GGUF sentence-transformers Transformers.js MLX PEFT timm Keras Flax PaddlePaddle 8 results for \"sentiment analysis updated March 2023\" cardiffnlp / twitter-roberta-base-sentiment-latest Text Classification • 130M • Updated Feb 10, 2024 ⬇ 2.9M ♥ 550 nl",
        "finalUrl": "http://localhost:43010/search?q=sentiment+analysis+updated+March+2023&type=model",
        "stats": {
          "title": "Search – Hugging Face",
          "chars": 1746,
          "links": 38,
          "forms": 5,
          "buttons": 1,
          "images": 8,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 0,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 1299,
          "viewportOverflow": false,
          "sampleText": "🤗 Hugging Face Models Datasets Spaces Papers Docs Blog Learn Enterprise Pricing Log In Sign Up Search All (8) Models Datasets Spaces Sort: Trending Most likes Most downloads Recently updated Recently created License: Any license Apache 2.0"
        },
        "networkFailures": [],
        "badResponses": [],
        "consoleErrors": []
      },
      {
        "name": "google-search-kilimanjaro",
        "startUrl": "http://localhost:43009/search?q=Mount+Kilimanjaro+elevation",
        "ok": true,
        "hasAnswer": false,
        "keyText": "Google Sign in Tools About 96,172,798 results (0.22 seconds) B www.britannica.com/place/Mount-Kilimanjaro https://www.britannica.com/place/Mount-Kilimanjaro Mount Kilimanjaro - Encyclopedia Britannica Britannica article covering the geography, geology and exploration history of Africa's tallest peak. ☆ Save N www.nationalgeographic.com/adventure/article/mount-kilimanjaro https://www.nationalgeographic.com/adventure/article/mount-kilimanjaro Mount Kilimanjaro - National Geographic National Geographic feature coverage of climbing routes, biodiversity and conservation efforts. ☆ Save P peakvisor.com/peak/kilimanjaro.html https://peakvisor.com/peak/kilimanjaro.html Kilimanjaro - PeakVisor Mounta",
        "finalUrl": "http://localhost:43009/search?q=Mount+Kilimanjaro+elevation",
        "stats": {
          "title": "Mount Kilimanjaro elevation - Google Search",
          "chars": 2620,
          "links": 44,
          "forms": 1,
          "buttons": 1,
          "images": 1,
          "brokenImages": 0,
          "brokenImageSamples": [],
          "emptyLinks": 0,
          "externalLinks": 0,
          "scrollWidth": 1440,
          "scrollHeight": 1883,
          "viewportOverflow": false,
          "sampleText": "Google Sign in Tools About 96,172,798 results (0.22 seconds) B www.britannica.com/place/Mount-Kilimanjaro https://www.britannica.com/place/Mount-Kilimanjaro Mount Kilimanjaro - Encyclopedia Britannica Britannica article covering the geograp"
        },
        "networkFailures": [],
        "badResponses": [],
        "consoleErrors": []
      }
    ]
  },
  "metrics": {
    "task_count": 643,
    "site_count": 15,
    "answer_types": {
      "possible": 500,
      "golden": 143
    },
    "actions": {
      "find": 361,
      "answer": 264,
      "filter_sort": 193,
      "search": 128,
      "plan": 38,
      "save_state": 28,
      "use_tool": 25,
      "compare": 21,
      "compute": 19,
      "book_buy": 12
    },
    "domains": {
      "general": 252,
      "research": 131,
      "knowledge": 126,
      "shopping": 117,
      "travel": 91,
      "local_maps": 34
    },
    "complexity_histogram": {
      "1": 57,
      "2": 122,
      "3": 129,
      "4": 72,
      "5": 80,
      "6": 48,
      "7": 49,
      "8": 44,
      "9": 24,
      "10": 18
    },
    "stateful_tasks": 40,
    "navigational_tasks": 100,
    "avg_complexity": 4.28,
    "avg_question_length": 121.3
  },
  "tasks": [
    {
      "id": "Allrecipes--0",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 0,
      "question": "Provide a recipe for vegetarian lasagna with more than 100 reviews and a rating of at least 4.5 stars suitable for 6 people.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Vegetarian Four Cheese Lasagna', 4.6-star, 181 reviews, Servings 8",
      "answer_length": 67,
      "question_length": 124,
      "actions": [
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 8,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Allrecipes--1",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 1,
      "question": "Find a recipe for a vegetarian lasagna that has at least a four-star rating and uses zucchini.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "\"Debbie's Vegetable Lasagna\", 4.7-star, include zucchini",
      "answer_length": 56,
      "question_length": 94,
      "actions": [
        "find",
        "filter_sort",
        "save_state"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 2,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Allrecipes--2",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 2,
      "question": "Find a recipe for a vegetarian lasagna under 600 calories per serving that has a prep time of less than 1 hour.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Easy Vegetarian Red Beans Lasagna', 496 Calories, prep time 20 mins",
      "answer_length": 68,
      "question_length": 111,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Allrecipes--3",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 3,
      "question": "Locate a recipe for vegan chocolate chip cookies with over 60 reviews and a rating of at least 4.5 stars on Allrecipes.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "golden",
      "answer": "'Vegan Chocolate Chip, Oatmeal, and Nut Cookies', 4.9 star, 67 viewers (> 60)",
      "answer_length": 77,
      "question_length": 119,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 6,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Allrecipes--4",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 4,
      "question": "Find a recipe for Baked Salmon that takes less than 30 minutes to prepare and has at least a 4 star rating based on user reviews.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Baked Dijon Salmon', 4.6-star, prep time 15 mins",
      "answer_length": 49,
      "question_length": 129,
      "actions": [
        "find",
        "filter_sort",
        "save_state"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 6,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 10
    },
    {
      "id": "Allrecipes--5",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 5,
      "question": "Search for a popular Pasta Sauce with more than 1000 reviews and a rating above 4 stars. Create a shopping list of ingredients for this recipe.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "\"World's Best Pasta Sauce!\", 4.7-star, 818 reviews, <Ingredients>",
      "answer_length": 65,
      "question_length": 143,
      "actions": [
        "find",
        "search",
        "answer",
        "filter_sort",
        "save_state"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 7,
      "requires_state": true,
      "requires_navigation": true,
      "complexity": 10
    },
    {
      "id": "Allrecipes--6",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 6,
      "question": "Search for a vegetarian lasagna recipe that has at least a four-star rating and over 500 reviews.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Spinach Lasagna', 4.7-star, 501 reviews",
      "answer_length": 40,
      "question_length": 97,
      "actions": [
        "find",
        "search",
        "filter_sort",
        "save_state"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 4,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 10
    },
    {
      "id": "Allrecipes--7",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 7,
      "question": "Find a popular recipe for a chocolate chip cookie and list the ingredients and preparation steps.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Best Chocolate Chip Cookies', <Ingredients>, <Preparation Steps>",
      "answer_length": 65,
      "question_length": 97,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Allrecipes--8",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 8,
      "question": "Search for a recipe for Beef Wellington on Allrecipes that has at least 200 reviews and an average rating of 4.5 stars or higher. List the main ingredients required for the dish.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Beef Wellington', <Ingredients>",
      "answer_length": 32,
      "question_length": 178,
      "actions": [
        "find",
        "search",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 6,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 9
    },
    {
      "id": "Allrecipes--9",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 9,
      "question": "Find a high-rated recipe for vegetarian lasagna, list the key ingredients required, and include the total preparation and cook time stated on the recipe.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Spicy Vegetarian Lasagna', <Ingredients>, prep time 30 mis, cook time 1 hour 10 mins",
      "answer_length": 85,
      "question_length": 153,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Allrecipes--10",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 10,
      "question": "Find The Most Popular Recipes of the 1960s, noting the recipe name, preparation time and total time of the second recipe in this collection.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "golden",
      "answer": "'Swedish Meatballs I', prep time 25 mins, total time 1 hour 25 mins",
      "answer_length": 67,
      "question_length": 140,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Allrecipes--11",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 11,
      "question": "Discover a suitable chocolate cupcake recipe on Allrecipes that has a preparation time of under 1 hour and at least 100 user reviews.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Chocolate Cupcake', 1261 reviews, prep time 15 mins",
      "answer_length": 52,
      "question_length": 133,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Allrecipes--12",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 12,
      "question": "Search for a popular cookie recipe on Allrecipes with more than 1000 reviews and a rating of 4.5 stars or better. Provide the list of ingredients needed.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Best Chocolate Chip Cookies', 4.6-star, 14493 reviews, <Ingredients>",
      "answer_length": 69,
      "question_length": 153,
      "actions": [
        "find",
        "search",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 6,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 9
    },
    {
      "id": "Allrecipes--13",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 13,
      "question": "Find a recipe with over 100 reviews for Fried Fish on Allrecipes, list the Full Nutrition Label and tell me the amount of Iron per Serving.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Crispy Fried Fish', Iron: 15mg",
      "answer_length": 31,
      "question_length": 139,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Allrecipes--14",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 14,
      "question": "Search for a recipe that includes \"chicken breast\" and \"quinoa\" with preparation time under 30 minutes on Allrecipes.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Slow Cooked Chicken Stew', prep time 20 mins",
      "answer_length": 45,
      "question_length": 117,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Allrecipes--15",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 15,
      "question": "Choose a dessert recipe on Allrecipes with a prep time of less than 30 minutes, has chocolate as an ingredient, and has a user rating of 4 stars or higher. Provide the name of the recipe, ingredients list, and step-by-step instructions.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Ultimate Chocolate Dessert', 4.7-star, prep time 15 mins",
      "answer_length": 57,
      "question_length": 236,
      "actions": [
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Allrecipes--16",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 16,
      "question": "Find a five-star rated chocolate chip cookie recipe that takes less than 1 hour to make on Allrecipes. Note how many reviews the recipe has and the main ingredients required.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Chocolate Chip Cookie Cups', 5.0-star, 3 reviews, total time 45 mins, <Ingredients>",
      "answer_length": 84,
      "question_length": 174,
      "actions": [
        "find",
        "filter_sort",
        "save_state"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 9
    },
    {
      "id": "Allrecipes--17",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 17,
      "question": "Find the Easy Vegetarian Spinach Lasagna recipe on Allrecipes and tell me what the latest review says.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "golden",
      "answer": "Easy to make and very delicious",
      "answer_length": 31,
      "question_length": 102,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Allrecipes--18",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 18,
      "question": "Find a recipe for a vegetarian lasagna that has over 300 reviews and an average rating of 4.5 or higher on Allrecipes.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Eggplant Lasagna', 4.7-star, 305 reviews",
      "answer_length": 41,
      "question_length": 118,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Allrecipes--19",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 19,
      "question": "Find a vegan lasagna recipe on Allrecipes that requires 10 ingredients or less and has feedback of more than 200 reviews. Provide a brief overview of the ingredient list and the total prep and cook time.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Vegan Lasagna II', 9 Ingredients, 4.2-star, prep time 30 mins, cook time 1 hour, <Ingredients>",
      "answer_length": 95,
      "question_length": 203,
      "actions": [
        "find",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Allrecipes--20",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 20,
      "question": "Find a recipe for a cauliflower pizza crust that has a preparation time of under 30 minutes and a rating of at least 4 stars on Allrecipes. Include the number of calories per serving.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Cauliflower Pizza Crust', 4.2 stars, Prep Time: 15 mins, 59 Calories per serving",
      "answer_length": 81,
      "question_length": 183,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 6,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Allrecipes--21",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 21,
      "question": "Locate a high-rated recipe for gluten-free brownies on Allrecipes with at least 50 reviews. List the main ingredients and the total time required for preparation and cooking.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Gluten-Free Fudge Brownies', 4.1 stars, 69 reviews, <Ingredients>, Prep Time: 15 mins, Total Time: 1 hr",
      "answer_length": 104,
      "question_length": 174,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Allrecipes--22",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 22,
      "question": "Find a recipe for a healthy avocado salad on Allrecipes that has a preparation time of less than 20 minutes and more than 30 user reviews. Include the nutritional information per serving.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Avocado Salad', 4.7 stars, 253 reviews, Prep Time: 15 mins, Nutrition Facts: 126 Calories, 10g Fat, 10g Carbs, 2g Protein",
      "answer_length": 122,
      "question_length": 187,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Allrecipes--23",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 23,
      "question": "Search Allrecipes for a baked lemon chicken recipe that has a prep time under 45 minutes, with at least a 4.5-star rating based on user reviews, and over 200 reviews. List the primary ingredients required.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Baked Chicken Schnitzel', 4.5 stars, 250 reviews, Prep Time: 20 mins, <Ingredients>",
      "answer_length": 84,
      "question_length": 205,
      "actions": [
        "search",
        "answer",
        "filter_sort",
        "save_state"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 8,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 10
    },
    {
      "id": "Allrecipes--24",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 24,
      "question": "Locate a recipe for an eggplant Parmesan on Allrecipes with a rating of at least 4.5 stars and over 50 reviews. Include the preparation time and the number of servings provided by the recipe.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Eggplant Parmesan', 4.5 stars, 2711 reviews, Prep Time: 25 mins, Servings: 10",
      "answer_length": 78,
      "question_length": 191,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 6,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Allrecipes--25",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 25,
      "question": "Find a popular quinoa salad recipe on Allrecipes with more than 500 reviews and a rating above 4 stars. Create a shopping list of ingredients for this recipe and include the total cooking and preparation time.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Easy Quinoa Salad', 4.8 stars, 1107 reviews, Prep Time: 20 mins, Cook Time: 15 mins, <Ingredients>",
      "answer_length": 99,
      "question_length": 209,
      "actions": [
        "find",
        "answer",
        "filter_sort",
        "save_state"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 7,
      "requires_state": true,
      "requires_navigation": true,
      "complexity": 10
    },
    {
      "id": "Allrecipes--26",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 26,
      "question": "Search for a high-protein vegetarian chili recipe on Allrecipes that has at least 50 reviews and a rating of 4 stars or higher. Provide the ingredient list, cooking time, and a brief description of the cooking steps.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'The Best Vegetarian Chili in the World', 4.7 stars, 1681 reviews, Cook Time: 1 hr, <Ingredients>, <Description: Cooking steps>",
      "answer_length": 127,
      "question_length": 216,
      "actions": [
        "find",
        "search",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 6,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 9
    },
    {
      "id": "Allrecipes--27",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 27,
      "question": "Locate a chicken curry recipe on Allrecipes that has been reviewed more than 30 times and has a rating of at least 4 stars. Provide a summary of the recipe including ingredients, preparation time, and cooking instructions.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Indian Chicken Curry (Murgh Kari)', 4.7 stars, 955 reviews, <Ingredients>, Prep Time: 20 mins, <cooking instructions>",
      "answer_length": 118,
      "question_length": 222,
      "actions": [
        "find",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 6,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Allrecipes--28",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 28,
      "question": "On Allrecipes, find a vegan brownie recipe that has at least 40 reviews and a rating of 4.5 or higher. Include the list of ingredients, total prep and cook time, and a brief overview of the preparation steps.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Vegan Brownies', 4.6 stars, 828 reviews, <Ingredients>, Prep Time: 15 mins, Cook Time: 30 mins, <preparation steps>",
      "answer_length": 116,
      "question_length": 208,
      "actions": [
        "find",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Allrecipes--29",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 29,
      "question": "Search for a Mediterranean-style grilled fish recipe on Allrecipes that includes ingredients like olives, has at least a 4-star rating, and more than 25 reviews. Detail the ingredients, cooking method, and total time required for preparation and cooking.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Branzino Mediterranean', 36 reviews, <Ingredients> include olive oil, <cooking method>, Prep Time: 15 mins, Cook Time: 25 mins, Total Time: 40 mins",
      "answer_length": 148,
      "question_length": 254,
      "actions": [
        "find",
        "search",
        "filter_sort",
        "save_state"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 6,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 10
    },
    {
      "id": "Allrecipes--30",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 30,
      "question": "Find a recipe for a vegan smoothie bowl on Allrecipes that includes bananas and leaves, has more than 20 reviews, and a rating of at least 4 stars. Provide a list of ingredients, preparation time, and a summary of the recipe steps.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Spinach and Banana Power Smoothie', 4.8 stars, 72 reviews, Ingredients: 1 cup plain soy milk, 3/4 cup packed fresh spinach leaves, 1 large banana, sliced; Prep Time: 10 mins; <steps>",
      "answer_length": 183,
      "question_length": 231,
      "actions": [
        "find",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 7,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Allrecipes--31",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 31,
      "question": "Search for a seafood paella recipe on Allrecipes with a minimum of 4.5 stars rating and at least 50 reviews. The recipe should include shrimp and mussels. Provide the ingredients, total time, and an overview of the preparation steps.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Easy Paella', 4.6 stars, 470 reviews, <Ingredients>, <preparation steps>, Total Time: 1 hr",
      "answer_length": 91,
      "question_length": 233,
      "actions": [
        "find",
        "search",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 6,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 9
    },
    {
      "id": "Allrecipes--32",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 32,
      "question": "Find a high-rated beef stew recipe on Allrecipes that requires a slow cooker and has at least 30 reviews. Detail the cooking time and the first five ingredients listed in the recipe.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Slow Cooker Beef Stew', 3994 reviews, Cook Time: 4 hrs, <Ingredients>",
      "answer_length": 70,
      "question_length": 182,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Allrecipes--33",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 33,
      "question": "Find a recipe for a low-carb breakfast on Allrecipes with at least 25 reviews. Show the Nutrition Facts and the total carbohydrate content per serving.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Low-Carb Bacon Spinach Egg Cups', 99 reviews, 237 Calories, 18g Fat, 4g Carbs, 17g Protein",
      "answer_length": 91,
      "question_length": 151,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Allrecipes--34",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 34,
      "question": "Locate a baked salmon recipe on Allrecipes that has at least 50 reviews and a rating of 4.5 stars or higher. Note the primary seasoning or herb used and the estimated cooking time.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Baked Salmon', 4.7 stars, 2339 reviews, Cook Time: 35 mins, <Ingredients>",
      "answer_length": 74,
      "question_length": 180,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 6,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Allrecipes--35",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 35,
      "question": "Search for an Italian-style meatball recipe on Allrecipes that has more than 100 reviews. Detail the type of meat used and the overall cooking time required.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Italian Turkey Meatballs', 4.7 stars, 234 reviews, Cook Time: 15 mins, meat:  1/2 pounds ground lean turkey",
      "answer_length": 108,
      "question_length": 157,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Allrecipes--36",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 36,
      "question": "Locate a recipe for an American apple pie on Allrecipes with a rating of at least 4 stars and more than 50 reviews. Note the maximum temperature mentioned in the Directions.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'All American Apple Pie', 4.6 stars, 490 reviews, 350 degrees F (175 degrees C)",
      "answer_length": 79,
      "question_length": 173,
      "actions": [
        "find",
        "filter_sort",
        "plan"
      ],
      "domains": [
        "shopping",
        "research",
        "local_maps"
      ],
      "constraint_count": 7,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Allrecipes--37",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 37,
      "question": "Search for a Greek salad recipe on Allrecipes that has a prep time of under 25 minutes and more than 15 reviews. Include the primary cheese used and the type of dressing recommended.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Greek Salad', 4.6 stars, 192 reviews, 1 cup crumbled feta cheese, ground black pepper to taste...",
      "answer_length": 98,
      "question_length": 182,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Allrecipes--38",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 38,
      "question": "Find a French ratatouille recipe on Allrecipes with a 4-star rating or higher and at least 15 reviews. Note the variety of vegetables included and the overall cooking time.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Ratatouille', 4.6 stars, 793 reviews, vegetables: 1 eggplant, cut into 1/2 inch cubes; 2 zucchini, sliced; 2 large tomatoes, chopped",
      "answer_length": 133,
      "question_length": 172,
      "actions": [
        "find",
        "filter_sort",
        "save_state"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 5,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 10
    },
    {
      "id": "Allrecipes--39",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 39,
      "question": "Locate a recipe for sushi rolls on Allrecipes with a minimum of 20 reviews. Show the Nutrition Facts and the main ingredients. Tell me how to store these rolls.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Smoked Salmon Sushi Roll', 78 reviews, Nutrition Facts (per serving): 291 Calories, 7g Fat, 45g Carbs, 11g Protein, <Ingredients>; You can refrigerate them in an airtight container for up to two days.",
      "answer_length": 201,
      "question_length": 160,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Allrecipes--40",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 40,
      "question": "Browse the about us section of Allrecipes for a brief introduction to The Allrecipes Allstars.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "golden",
      "answer": "The Allrecipes Allstars: Social media influencers, registered dietitians, grillmasters, and more seasoned home cooks make up our enthusiastic squad of 100+ brand ambassadors. This diverse, food-loving crew spans the U.S. geographically and represents many different cultures, ethnicities, and family makeups. Since 2011, the Allstars have created tens of thousands of original recipes, photos, and reviews plus shared their cooking expertise via flat and video content on our website, social media, plus more marketing channels.",
      "answer_length": 528,
      "question_length": 94,
      "actions": [
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 3
    },
    {
      "id": "Allrecipes--41",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 41,
      "question": "List 3 recommended dinner recipes in the Allrecipes Dinners section.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "Ground Beef-Spinach Casserole; Mexican Ground Beef Casserole; Retro Ground Beef Casserole with Biscuits",
      "answer_length": 103,
      "question_length": 68,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Allrecipes--42",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 42,
      "question": "Find a recipe for banana bread with more than 200 reviews and a rating of at least 4.0 stars on Allrecipes.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Banana Banana Bread', 4.7 stars, 12649 reviews",
      "answer_length": 47,
      "question_length": 107,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 7,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Allrecipes--43",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 43,
      "question": "Find a recipe for a vegan pumpkin pie on Allrecipes with a minimum four-star rating and a total cook time exceeding 1 hour.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "'Amazing Vegan Pumpkin Pie', 5.0 stars, Cook Time: 1 hr 55 mins",
      "answer_length": 63,
      "question_length": 123,
      "actions": [
        "find",
        "filter_sort",
        "save_state"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 2,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Allrecipes--44",
      "site": "Allrecipes",
      "slug": "allrecipes",
      "index": 44,
      "question": "List at least 6 holiday recipes sections mentioned in the Occasions section of Allrecipes.",
      "local_url": "http://localhost:40000/",
      "upstream_url": "https://www.allrecipes.com/",
      "original_web": "https://www.allrecipes.com/",
      "answer_type": "possible",
      "answer": "THANKSGIVING RECIPES; CHRISTMAS RECIPES; LUNAR NEW YEAR RECIPES; HANUKKAH RECIPES; PURIM RECIPES; MARDI GRAS RECIPES ...",
      "answer_length": 120,
      "question_length": 90,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Amazon--0",
      "site": "Amazon",
      "slug": "amazon",
      "index": 0,
      "question": "Search an Xbox Wireless controller with green color and rated above 4 stars.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Xbox Core Wireless Gaming Controller - Velocity Green; 4.7-star",
      "answer_length": 63,
      "question_length": 76,
      "actions": [
        "search",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Amazon--1",
      "site": "Amazon",
      "slug": "amazon",
      "index": 1,
      "question": "Search for women's golf polos in m size, priced between 50 to 75 dollars, and save the lowest priced among results.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "PUMA Golf 2019 Men's Rotation Polo; $50.00",
      "answer_length": 42,
      "question_length": 115,
      "actions": [
        "find",
        "search",
        "filter_sort",
        "save_state"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 5,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 10
    },
    {
      "id": "Amazon--2",
      "site": "Amazon",
      "slug": "amazon",
      "index": 2,
      "question": "Find a gaming desktop with Windows 11 Home, and the disk size should be 1TB.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "HP Victus 15L Gaming Desktop with Windows 11 Home and 1TB disk size",
      "answer_length": 67,
      "question_length": 76,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Amazon--3",
      "site": "Amazon",
      "slug": "amazon",
      "index": 3,
      "question": "Find climbing gears and sort the results by price high to low. Answer the first 3 results after sorting.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "First 3 results after sort",
      "answer_length": 26,
      "question_length": 104,
      "actions": [
        "find",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 8
    },
    {
      "id": "Amazon--4",
      "site": "Amazon",
      "slug": "amazon",
      "index": 4,
      "question": "Find the used Nintendo Switch Lite on Amazon then filter by 'Used - Good', tell me the cheapest one that is 'Used - Good'.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Nintendo Switch Lite - Blue; Used Good: $170",
      "answer_length": 44,
      "question_length": 122,
      "actions": [
        "find",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 6
    },
    {
      "id": "Amazon--5",
      "site": "Amazon",
      "slug": "amazon",
      "index": 5,
      "question": "Find a Blue iPhone 12 Pro 128gb and add to cart.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Apple iPhone 12 Pro, 128GB, Pacific Blue - Fully Unlocked (Renewed); Action: ADD_TO_CHART",
      "answer_length": 89,
      "question_length": 48,
      "actions": [
        "find",
        "book_buy"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 1,
      "requires_state": true,
      "requires_navigation": true,
      "complexity": 7
    },
    {
      "id": "Amazon--6",
      "site": "Amazon",
      "slug": "amazon",
      "index": 6,
      "question": "Browse black strollers within $100 to $200 on Amazon. Then find one Among these black strollers with over 20,000 reviews and a rating greater than 4 star.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Baby Trend Expedition Jogger, Dash Black; 22146 reviews; 4.7-star",
      "answer_length": 65,
      "question_length": 154,
      "actions": [
        "find",
        "search",
        "filter_sort",
        "save_state"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 9,
      "requires_state": true,
      "requires_navigation": true,
      "complexity": 10
    },
    {
      "id": "Amazon--7",
      "site": "Amazon",
      "slug": "amazon",
      "index": 7,
      "question": "Browse the women's hiking boots on Amazon and filter the results to show only those that are waterproof and have a rating of at least 4 stars and size 6.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Filter: 4-star, waterproof, size 6",
      "answer_length": 34,
      "question_length": 153,
      "actions": [
        "search",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 6,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 9
    },
    {
      "id": "Amazon--8",
      "site": "Amazon",
      "slug": "amazon",
      "index": 8,
      "question": "Find the cheapest Samsung-made Android tablet with screen between 10-10.9 inches on Amazon. Only answer the cheapest one.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Samsung Galaxy Tab S 10.5in 16GB Android Tablet - Titanium Gold (Renewed); $139.94",
      "answer_length": 82,
      "question_length": 121,
      "actions": [
        "find",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Amazon--9",
      "site": "Amazon",
      "slug": "amazon",
      "index": 9,
      "question": "Find a dog bed on Amazon that is washable and has a length of at least 30 inches.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Gulokoka Large Dog Bed for Crate Comfortable Washable Pet Mat for Dogs, Cats, Gray",
      "answer_length": 82,
      "question_length": 81,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Amazon--10",
      "site": "Amazon",
      "slug": "amazon",
      "index": 10,
      "question": "Find the cost of a 2-year protection for PS4 on Amazon.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Sony Playstation PS4 1TB Black Console; 2-Year Protection for $30.99",
      "answer_length": 68,
      "question_length": 55,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Amazon--11",
      "site": "Amazon",
      "slug": "amazon",
      "index": 11,
      "question": "Find a stainless steel kitchen sink with double bowls on Amazon. Sort the results and find the cheapest one with FREE delivery.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Transolid STDE33226-2 Kitchen Sink, Stainless Steel; $120.89",
      "answer_length": 60,
      "question_length": 127,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 5
    },
    {
      "id": "Amazon--12",
      "site": "Amazon",
      "slug": "amazon",
      "index": 12,
      "question": "Check reviews for a Ride On Car with 100+ reviews & 4+ stars rating on Amazon. Give me the top review about this Ride On Car.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Worth every penny",
      "answer_length": 17,
      "question_length": 125,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 7,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Amazon--13",
      "site": "Amazon",
      "slug": "amazon",
      "index": 13,
      "question": "Browse best selling black hoodies in mens size Big and Tall that is between $25 and $50 on Amazon.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "adidas Men's Essentials Fleece Hoodie; 500+ bought in past month",
      "answer_length": 64,
      "question_length": 98,
      "actions": [
        "search",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 8
    },
    {
      "id": "Amazon--14",
      "site": "Amazon",
      "slug": "amazon",
      "index": 14,
      "question": "Find the new surge protector on Amazon with 6 to 8 outlets under 25 dollars with customer reviews above 4+ stars.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Surge Protector Power Strip $15.99, 8 Outlets, 4.7-star",
      "answer_length": 55,
      "question_length": 113,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 8,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Amazon--15",
      "site": "Amazon",
      "slug": "amazon",
      "index": 15,
      "question": "Find a pair of mens running shoes in black, size 7, 4+ stars and under $50 and add them to my cart on Amazon.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Damyuan Men's Sport Gym Running Shoes Walking Shoes Casual Lace Up Lightweight; black, size 7, 4.0-star, $29.99",
      "answer_length": 111,
      "question_length": 109,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 6,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 8
    },
    {
      "id": "Amazon--16",
      "site": "Amazon",
      "slug": "amazon",
      "index": 16,
      "question": "Find the Return Policy for Mens Rhinestone Skull Graphic Shirt on Amazon. Color: Black, Size: XX-Large. If Free return is avaliable, tell me how to return this item.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "golden",
      "answer": "FREE Returns, 1. Go to Your Orders to start the return; 2. Print the return shipping label; 3. Ship it!",
      "answer_length": 103,
      "question_length": 165,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Amazon--17",
      "site": "Amazon",
      "slug": "amazon",
      "index": 17,
      "question": "Show me the list of baby products that are on sale and under 10 dollars on Amazon. Provide at least 2 on sale products",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Johnson's Baby Care Essentials Gift Set, $7.55; SWEET DOLPHIN 12 Pack Muslin Burp Cloths Large 100% Cotton Hand Washcloths for Baby, $9.98",
      "answer_length": 138,
      "question_length": 118,
      "actions": [
        "answer",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Amazon--18",
      "site": "Amazon",
      "slug": "amazon",
      "index": 18,
      "question": "Open Amazon's home page and tell me what the deal is that is going on at the moment, list the names of at least 2 items that are on offer and tell me what percent off they are.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Gevi Household V2.0 Countertop Nugget Ice Maker, 20% off; Osmo - Little Genius Starter Kit for iPad & iPhone, 7% off;",
      "answer_length": 117,
      "question_length": 176,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 5
    },
    {
      "id": "Amazon--19",
      "site": "Amazon",
      "slug": "amazon",
      "index": 19,
      "question": "Look for an English language book on roman empire history in the Amazon Kindle store. Sort by newests arrivals and look for a title that will be released within a month.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "THE HISTORY OF THE DECLINE AND FALL OF THE ROMAN EMPIRE (All 6 Volumes), released on January 10, 2024.",
      "answer_length": 102,
      "question_length": 169,
      "actions": [
        "filter_sort",
        "book_buy"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": true,
      "requires_navigation": true,
      "complexity": 9
    },
    {
      "id": "Amazon--20",
      "site": "Amazon",
      "slug": "amazon",
      "index": 20,
      "question": "Search for a wireless ergonomic keyboard with backlighting and a rating of at least 4 stars. The price should be between $40 to $60. Save the product with the 500+ customer reviews.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Logitech Wave Keys Wireless Ergonomic Keyboard, $57.99, 4.6 stars, 26005 ratings",
      "answer_length": 80,
      "question_length": 181,
      "actions": [
        "find",
        "search",
        "filter_sort",
        "save_state"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 10,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 10
    },
    {
      "id": "Amazon--21",
      "site": "Amazon",
      "slug": "amazon",
      "index": 21,
      "question": "Find a stainless steel, 12-cup programmable coffee maker on Amazon. The price range should be between $100 to $200. Report the one with the 4+ customer rating.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Braun BrewSense 12-Cup Drip Coffee Maker, Stainless Steel, 4.3 stars, $129.95",
      "answer_length": 77,
      "question_length": 159,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 7,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Amazon--22",
      "site": "Amazon",
      "slug": "amazon",
      "index": 22,
      "question": "Search for a set of non-stick, oven-safe cookware on Amazon. The set should include at least 10 pieces and be priced under $150.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "CAROTE 11pcs Nonstick Cookware Set, Non Stick, Oven Safe, $129.99 ($11.82 / Count)",
      "answer_length": 82,
      "question_length": 128,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Amazon--23",
      "site": "Amazon",
      "slug": "amazon",
      "index": 23,
      "question": "Look for a men's waterproof digital sports watch with a heart rate monitor on Amazon. It should be priced between $50 to $100.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Smartwatch for Men Android iPhone, Waterproof, Heart Rate, $54.99",
      "answer_length": 65,
      "question_length": 126,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Amazon--24",
      "site": "Amazon",
      "slug": "amazon",
      "index": 24,
      "question": "Browse for a compact air fryer on Amazon with a capacity of 2 to 3 quarts. It should have a digital display, auto shutoff and be priced under $100.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Dash DMAF360GBAQ02 Aircrisp® Pro Digital Air Fryer, Digital Display, Auto Shut Off, 3qt, $90.10",
      "answer_length": 95,
      "question_length": 147,
      "actions": [
        "search",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 8
    },
    {
      "id": "Amazon--25",
      "site": "Amazon",
      "slug": "amazon",
      "index": 25,
      "question": "Search for a queen-sized, hypoallergenic mattress topper on Amazon. It should have a memory foam material and be priced between $50 to $100.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "2 Inch 7-Zone Memory Foam Mattress Topper Queen with 100% Bamboo Rayon Cover, Cooling Gel-Infused Swirl Egg Crate Memory Foam, $99.99",
      "answer_length": 133,
      "question_length": 140,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Amazon--26",
      "site": "Amazon",
      "slug": "amazon",
      "index": 26,
      "question": "Find a portable Bluetooth speaker on Amazon with a water-resistant design, under $50. It should have a minimum battery life of 10 hours.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Portable Bluetooth Speaker, IPX7 Waterproof Wireless Speaker, 25W Super Bass 24H Playtime, $29.97",
      "answer_length": 97,
      "question_length": 136,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Amazon--27",
      "site": "Amazon",
      "slug": "amazon",
      "index": 27,
      "question": "Look for a USB-C hub on Amazon compatible with MacBook Pro, featuring at least 4 ports, including HDMI and SD card reader. The price should be under $50. Select the one after sorting by Best Sellers.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Hiearcool USB C Hub, USB C Multi-Port Adapter for MacBook Pro, 7IN1, include 4K HDMI USB3.0 and SD/TF Card Reader, $24.99",
      "answer_length": 121,
      "question_length": 199,
      "actions": [
        "filter_sort",
        "use_tool"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 6,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 8
    },
    {
      "id": "Amazon--28",
      "site": "Amazon",
      "slug": "amazon",
      "index": 28,
      "question": "Search for a yoga mat on Amazon that is at least 6mm thick, non-slip, and eco-friendly. The price should be under $50.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Retrospec Solana Yoga Mat 1\" Thick, Non Slip, $38.51",
      "answer_length": 52,
      "question_length": 118,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Amazon--29",
      "site": "Amazon",
      "slug": "amazon",
      "index": 29,
      "question": "Find a set of solar-powered garden lights on Amazon with a minimum pack of 10 lights. They should be LED and priced under $50.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "KelvinLux Solar Garden Lights Outdoor, 12 Packs, 12 LEDs, $35.99 ($3.00 / Count)",
      "answer_length": 80,
      "question_length": 126,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Amazon--30",
      "site": "Amazon",
      "slug": "amazon",
      "index": 30,
      "question": "Locate the highest-rated fiction book released in 2024 on Amazon, with a minimum of 50 customer reviews.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "The Women Library Binding – Large Print, March 1, 2024, 4.8 stars",
      "answer_length": 65,
      "question_length": 104,
      "actions": [
        "find",
        "filter_sort",
        "book_buy"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 5,
      "requires_state": true,
      "requires_navigation": true,
      "complexity": 10
    },
    {
      "id": "Amazon--31",
      "site": "Amazon",
      "slug": "amazon",
      "index": 31,
      "question": "Find a compact digital camera on Amazon with a zoom capability of at least 10x, rated 4 stars or higher, and priced between $100 to $300.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "5K Digital Camera for Photography Autofocus, 16X Digital Zoom, 5.0 stars,  $129.99",
      "answer_length": 82,
      "question_length": 137,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 6,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Amazon--32",
      "site": "Amazon",
      "slug": "amazon",
      "index": 32,
      "question": "Search for an electric kettle on Amazon with a capacity of at least 1.5 liters, made of stainless steel, and with a customer rating of 4 stars or above.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "COMFEE' Stainless Steel Electric Kettle, 1.7 Liter, 4.6 stars",
      "answer_length": 61,
      "question_length": 152,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 6,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Amazon--33",
      "site": "Amazon",
      "slug": "amazon",
      "index": 33,
      "question": "Search for a portable air conditioner on Amazon suitable for a room size of 300 sq ft, with energy efficiency rating, and compare the prices of the top three search results.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "price compare: 1) Shinco 10,000 BTU Portable Air Conditioner, $314.99; 2) Renogy 8,000 BTU Portable Air Conditioners, $283.09; 3) SereneLife Compact Freestanding Portable Air Conditioner, $247.54",
      "answer_length": 195,
      "question_length": 173,
      "actions": [
        "find",
        "search",
        "filter_sort",
        "compare"
      ],
      "domains": [
        "shopping",
        "travel"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 9
    },
    {
      "id": "Amazon--34",
      "site": "Amazon",
      "slug": "amazon",
      "index": 34,
      "question": "Find a beginner's acrylic paint set on Amazon, with at least 24 colors, suitable for canvas painting, and priced under $40.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Complete Acrylic Paint Set, 24х Rich Pigment Colors, for Painting Canvas, $16.97",
      "answer_length": 80,
      "question_length": 123,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Amazon--35",
      "site": "Amazon",
      "slug": "amazon",
      "index": 35,
      "question": "Find a men's leather wallet on Amazon with RFID blocking, at least 6 card slots, and priced below $50. Check if it's available for FREE delivery.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "STAY FINE Top Grain Leather Wallet for Men, RFID Blocking, Slim Billfold with 8 Card Slots, FREE delivery Friday, March 1",
      "answer_length": 121,
      "question_length": 145,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Amazon--36",
      "site": "Amazon",
      "slug": "amazon",
      "index": 36,
      "question": "Search for a children's science experiment kit on Amazon suitable for ages 8-13, with at least a 4-star rating and priced under $30.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "UNGLINGA 150 Experiments Science Kits for Kids Age 6-8-10-12-14, 4.6 stars, $29.99",
      "answer_length": 82,
      "question_length": 132,
      "actions": [
        "find",
        "search",
        "filter_sort",
        "save_state"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 7,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 10
    },
    {
      "id": "Amazon--37",
      "site": "Amazon",
      "slug": "amazon",
      "index": 37,
      "question": "Locate a queen-sized bedspread on Amazon with a floral pattern, and check if it's available in blue color.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "NEWLAKE Cotton Bedspread Quilt Sets-Reversible Patchwork Coverlet Set, Blue Classic Royal Pattern, Queen Size",
      "answer_length": 109,
      "question_length": 106,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Amazon--38",
      "site": "Amazon",
      "slug": "amazon",
      "index": 38,
      "question": "Find a bird feeder on Amazon suitable for small birds, with an anti-squirrel mechanism, and check if it's available with free shipping.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Bird Feeder for Outdoors Hanging, Squirrel Proof, FREE delivery Friday, March 1",
      "answer_length": 79,
      "question_length": 135,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Amazon--39",
      "site": "Amazon",
      "slug": "amazon",
      "index": 39,
      "question": "Locate a travel guide book on Amazon for Japan, published in 2024, with at least 20 customer reviews.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "Japan Travel Guide 2024: The Ultimate Route to Authentic Ramen and Beyond – Tips, Maps, and Must-Sees for Every Traveler, February 1, 2024, 38 ratings",
      "answer_length": 150,
      "question_length": 101,
      "actions": [
        "find",
        "book_buy"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 4,
      "requires_state": true,
      "requires_navigation": true,
      "complexity": 10
    },
    {
      "id": "Amazon--40",
      "site": "Amazon",
      "slug": "amazon",
      "index": 40,
      "question": "Locate a women's yoga mat in purple, with a thickness of at least 5mm, rated 4+ stars, and priced under $30 on Amazon. Check how many colors are available in total, and what is the return and delivery policy.",
      "local_url": "http://localhost:40001/",
      "upstream_url": "https://www.amazon.com/",
      "original_web": "https://www.amazon.com/",
      "answer_type": "possible",
      "answer": "ProsourceFit Extra Thick Yoga Pilates Exercise Mat, 1/2\", 4.6 stars, $21.99, 7 colors, FREE delivery Friday, March 1 on orders shipped by Amazon over $35",
      "answer_length": 153,
      "question_length": 208,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "travel",
        "research"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Apple--0",
      "site": "Apple",
      "slug": "apple",
      "index": 0,
      "question": "Compare the prices of the latest models of MacBook Air available on Apple's website.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "MacBook Air 13-inch M1 chip: from $999; 13-inch M2 chip: from $1099; 15-inch M2 chip: from $1299",
      "answer_length": 96,
      "question_length": 84,
      "actions": [
        "compare"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Apple--1",
      "site": "Apple",
      "slug": "apple",
      "index": 1,
      "question": "Research the new features of the iOS 17 on Apple support and check its compatibility with the iPhone 12.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "StandBy delivers a new full-screen experience; AirDrop makes it easier to share and connect; Enhancements to the keyboard;... compatible",
      "answer_length": 136,
      "question_length": 104,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Apple--2",
      "site": "Apple",
      "slug": "apple",
      "index": 2,
      "question": "Compare the prices and chips for the iPhone 14 Pro and iPhone 15 Pro models directly from Apple's website.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "14 Pro: Available at authorized resellers, A16 Bionic chip, 6-core CPU, 5-core GPU, 16-core Neural Engine; 15 Pro: Starting at $999, A17 Pro chip, 6-core CPU, 6-core GPU, 16-core Neural Engine",
      "answer_length": 192,
      "question_length": 106,
      "actions": [
        "compare"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Apple--3",
      "site": "Apple",
      "slug": "apple",
      "index": 3,
      "question": "Find the latest model of the iPhone and compare the price and screen size between the pro and pro max.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "iPhone 15 pro starts from $999, 6.1-inch screen; iPhone 15 pro max starts from $1199, 6.7-inch screen",
      "answer_length": 101,
      "question_length": 102,
      "actions": [
        "find",
        "filter_sort",
        "compare"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Apple--4",
      "site": "Apple",
      "slug": "apple",
      "index": 4,
      "question": "How much does it cost to buy a Macbook pro, 16-inch, Apple M3 Max chip with 16-core CPU, 40-core GPU, 64GB unified memory, 1TB SSD.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "$4,199.00 or $349.91/mo.per month for 12 mo.*",
      "answer_length": 45,
      "question_length": 131,
      "actions": [
        "answer"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Apple--5",
      "site": "Apple",
      "slug": "apple",
      "index": 5,
      "question": "Check the release date and price for the latest version of the iPhone.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "iPhone 15 ($799) or pro ($999) or pro Max ($1199); September 22, 2023",
      "answer_length": 69,
      "question_length": 70,
      "actions": [
        "answer"
      ],
      "domains": [
        "shopping",
        "knowledge"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Apple--6",
      "site": "Apple",
      "slug": "apple",
      "index": 6,
      "question": "Find AirPods on Apple and how many types are currently available.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "4",
      "answer_length": 1,
      "question_length": 65,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Apple--7",
      "site": "Apple",
      "slug": "apple",
      "index": 7,
      "question": "When and where the Apple Vision Pro will be released.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "Available early 2024 in the U.S.",
      "answer_length": 32,
      "question_length": 53,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Apple--8",
      "site": "Apple",
      "slug": "apple",
      "index": 8,
      "question": "Identify and list the specifications of the latest iPad model released by Apple, including its storage options, processor type, and display features.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "iPad Pro, storage options: 128GB, 256GB, 512GB, 1TB, 2TB; processor type: Apple M2 chip; display features: 11‑inch with Liquid Retina display, 12.9‑inch with Liquid Retina XDR display",
      "answer_length": 183,
      "question_length": 149,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Apple--9",
      "site": "Apple",
      "slug": "apple",
      "index": 9,
      "question": "Check the Apple Store for the availability of the latest iPhone model and schedule an in-store pickup at the nearest Apple Store for January 10, 2024.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "iPhone 15; Schedule an in-store pickup",
      "answer_length": 38,
      "question_length": 150,
      "actions": [
        "plan"
      ],
      "domains": [
        "research",
        "local_maps"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Apple--10",
      "site": "Apple",
      "slug": "apple",
      "index": 10,
      "question": "Find information on the latest (as of today's date) MacBook model, including its key features such as processor type, memory size, and storage capacity.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "Macbook Pro; processor type: Apple M3 chip, Apple M3 Pro chip, Apple M3 Max chip; memory size: 8GB, 16GB, 18GB, 24GB, 36GB, 48GB, 64GB, 96GB, 128GB; storage capacity: 512GB, 1TB, 2TB, 4TB, 8TB",
      "answer_length": 192,
      "question_length": 152,
      "actions": [
        "find"
      ],
      "domains": [
        "research",
        "knowledge"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Apple--11",
      "site": "Apple",
      "slug": "apple",
      "index": 11,
      "question": "Get information about the latest iPad model released by Apple, including its release date, base storage capacity, and starting price available on Apple's official website.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "sixth-generation iPad Pro 11‑inch, iPad Pro 12.9‑inch; release date: October 26, 2022; base storage capacity 128 GB, starting price $799",
      "answer_length": 136,
      "question_length": 171,
      "actions": [
        "answer"
      ],
      "domains": [
        "shopping",
        "research",
        "knowledge"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Apple--12",
      "site": "Apple",
      "slug": "apple",
      "index": 12,
      "question": "What Apple Repair ways are mentioned on apple website, answer 2 of them.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "golden",
      "answer": "Any 2 of 'Send your product to Apple', 'Find an Apple Authorized Service Provider', 'Visit a Genius at an Apple Store', 'Independent Repair Providers', 'Self Service Repair'",
      "answer_length": 173,
      "question_length": 72,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Apple--13",
      "site": "Apple",
      "slug": "apple",
      "index": 13,
      "question": "How many colors does the latest MacBook Air come in?",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "4, Silver, Starlight, Space Gray, and Midnight",
      "answer_length": 46,
      "question_length": 52,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Apple--14",
      "site": "Apple",
      "slug": "apple",
      "index": 14,
      "question": "Identify the upgrade options available for the cheapest base model of the MacBook Pro 14-inch with M3 chip, and calculate the total price difference from the base model to the maximum upgrade (no Pre-Installed Software) offered by Apple.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "Base model:$1599, difference: $1020",
      "answer_length": 35,
      "question_length": 237,
      "actions": [
        "filter_sort",
        "compare",
        "compute"
      ],
      "domains": [
        "shopping",
        "research",
        "knowledge"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Apple--15",
      "site": "Apple",
      "slug": "apple",
      "index": 15,
      "question": "On Apple's website, how many different types of keyboards are available when customizing your 14-inch MacBook Pro?",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "16",
      "answer_length": 2,
      "question_length": 114,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Apple--16",
      "site": "Apple",
      "slug": "apple",
      "index": 16,
      "question": "Find on Apple website how many types of AirPods (3rd generation) are available and what is the price difference.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "2 types, price difference $10",
      "answer_length": 29,
      "question_length": 112,
      "actions": [
        "find",
        "compare"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Apple--17",
      "site": "Apple",
      "slug": "apple",
      "index": 17,
      "question": "Search Apple for the accessory Smart Folio for iPad and check the closest pickup availability next to zip code 90038.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "golden",
      "answer": "Apple Tower Theatre",
      "answer_length": 19,
      "question_length": 117,
      "actions": [
        "search",
        "plan"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Apple--18",
      "site": "Apple",
      "slug": "apple",
      "index": 18,
      "question": "Check if there are trade-in offers for the latest model of iPhone.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "golden",
      "answer": "There are trade-in offers.",
      "answer_length": 26,
      "question_length": 66,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Apple--19",
      "site": "Apple",
      "slug": "apple",
      "index": 19,
      "question": "On Apple's website, what is the slogan for the Mac and what is the slogan for the Macbook pro.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "golden",
      "answer": "If you can dream it, Mac can do it; Mind-blowing. Head-turning",
      "answer_length": 62,
      "question_length": 94,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Apple--20",
      "site": "Apple",
      "slug": "apple",
      "index": 20,
      "question": "Check the price for an Apple iPhone 14 Plus with 256GB storage in Purple color.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "From $899 or $37.45/mo.per month for 24 mo.months",
      "answer_length": 49,
      "question_length": 79,
      "actions": [
        "answer"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Apple--21",
      "site": "Apple",
      "slug": "apple",
      "index": 21,
      "question": "Identify the available storage options for the latest iPad Pro on the Apple website.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "128GB, 256GB, 512GB, 1TB, and 2TB",
      "answer_length": 33,
      "question_length": 84,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Apple--22",
      "site": "Apple",
      "slug": "apple",
      "index": 22,
      "question": "Find out the trade-in value for an iPhone 13 Pro Max in good condition on the Apple website.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "iPhone 13 Pro Max, Up to $500",
      "answer_length": 29,
      "question_length": 92,
      "actions": [
        "find"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Apple--23",
      "site": "Apple",
      "slug": "apple",
      "index": 23,
      "question": "Determine the price difference between the latest series of Apple Watch and Apple Watch SE on the Apple website.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "Apple Watch SE From $249, Apple Watch Series 9 From $399",
      "answer_length": 56,
      "question_length": 112,
      "actions": [
        "filter_sort",
        "compare"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Apple--24",
      "site": "Apple",
      "slug": "apple",
      "index": 24,
      "question": "Find out the starting price for the most recent model of the iMac on the Apple website.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "$1299.00",
      "answer_length": 8,
      "question_length": 87,
      "actions": [
        "find"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Apple--25",
      "site": "Apple",
      "slug": "apple",
      "index": 25,
      "question": "On the Apple website, look up the processor for the latest model of the Apple TV.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "Apple TV 4K: A15 Bionic chip",
      "answer_length": 28,
      "question_length": 81,
      "actions": [
        "find"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Apple--26",
      "site": "Apple",
      "slug": "apple",
      "index": 26,
      "question": "Find the maximum video recording resolution supported by the latest iPad mini on the Apple website.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "4K video recording at 24 fps, 25 fps, 30 fps, or 60 fps",
      "answer_length": 55,
      "question_length": 99,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Apple--27",
      "site": "Apple",
      "slug": "apple",
      "index": 27,
      "question": "On Apple's website, check if the HomePod mini in store is available in multiple colors and list them.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "Available in multiple colors: Space Gray, Blue, Yellow, White, and Orange.",
      "answer_length": 74,
      "question_length": 101,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Apple--28",
      "site": "Apple",
      "slug": "apple",
      "index": 28,
      "question": "On the Apple website, find out if the Mac Mini can be configured with a GPU larger than 16-core.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "golden",
      "answer": "Yes. Mac mini Apple M2 Pro chip, Configurable to: 19-core GPU",
      "answer_length": 61,
      "question_length": 96,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Apple--29",
      "site": "Apple",
      "slug": "apple",
      "index": 29,
      "question": "On Apple's website, check the estimated battery life of the latest MacBook Air during web browsing in Tech Specs.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "Up to 15 hours wireless web",
      "answer_length": 27,
      "question_length": 113,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Apple--30",
      "site": "Apple",
      "slug": "apple",
      "index": 30,
      "question": "Check the storage options and prices for the latest iPad Pro models on Apple's website.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "11-inch, 128GB from $799, 256GB from $899, 512GB from $1099, 1TB from $1499, and 2TB from $1899.",
      "answer_length": 96,
      "question_length": 87,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Apple--31",
      "site": "Apple",
      "slug": "apple",
      "index": 31,
      "question": "On Apple's website, what is the slogan for the latest Apple Watch Series.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "golden",
      "answer": "Smarter. Brighter. Mightier.",
      "answer_length": 28,
      "question_length": 73,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Apple--32",
      "site": "Apple",
      "slug": "apple",
      "index": 32,
      "question": "Investigate the trade-in value for an iPhone 11 Pro Max on Apple's website.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "iPhone 11 Pro Max\tUp to $270",
      "answer_length": 28,
      "question_length": 75,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Apple--33",
      "site": "Apple",
      "slug": "apple",
      "index": 33,
      "question": "Look for the color options available for the newest iMac.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "Blue, Green, Pink, Silver, Yellow, Orange, Purple",
      "answer_length": 49,
      "question_length": 57,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Apple--34",
      "site": "Apple",
      "slug": "apple",
      "index": 34,
      "question": "Identify the size and weight for the Apple TV 4K and list the Siri Remote features introduced.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "Height: 1.2 inches (31 mm), Width: 3.66 inches (93 mm), Depth: 3.66 inches (93 mm); Siri Remote features",
      "answer_length": 104,
      "question_length": 94,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Apple--35",
      "site": "Apple",
      "slug": "apple",
      "index": 35,
      "question": "How many types of Apple Pencil are currently available on the Apple's website? Which one supports Wireless pairing and charging.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "3, Apple Pencil (2nd generation), Apple Pencil (USB-C), Apple Pencil (1st generation); Apple Pencil (2nd generation) supports Wireless pairing and charging.",
      "answer_length": 156,
      "question_length": 128,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Apple--36",
      "site": "Apple",
      "slug": "apple",
      "index": 36,
      "question": "Browse Apple Music on the entertainment section of the Apple's website, and see which singers' names are included in the pictures on this page.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "Lauren Daigle, Megan Moroney, Olivia Rodrigo ...",
      "answer_length": 48,
      "question_length": 143,
      "actions": [
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 3
    },
    {
      "id": "Apple--37",
      "site": "Apple",
      "slug": "apple",
      "index": 37,
      "question": "Compare the color options of iPhone 13 Pro, iPhone 14 Pro and iPhone 15 Pro.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "golden",
      "answer": "iPhone 13 pro: Alpine Green, Silver, Gold, Graphite, Sierra Blue; iPhone 14 pro: Deep Purple, Gold, Silver, Space Black; iPhone 15 pro: Natural Titanium, Blue Titanium, White Titanium, Black Titanium",
      "answer_length": 199,
      "question_length": 76,
      "actions": [
        "compare"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Apple--38",
      "site": "Apple",
      "slug": "apple",
      "index": 38,
      "question": "Explore accessories for Apple Vision Pro, list at least three accessories.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "Apple Vision Pro Battery; Apple Vision Pro Travel Case; ZEISS Optical Inserts ...",
      "answer_length": 81,
      "question_length": 74,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Apple--39",
      "site": "Apple",
      "slug": "apple",
      "index": 39,
      "question": "Find solutions on Apple's website if you forgot your Apple ID password.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "The fastest and easiest way to reset your password is with your iPhone or other trusted Apple device — one that you're already signed in to with your Apple ID, so that we know that it's yours.",
      "answer_length": 192,
      "question_length": 71,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Apple--40",
      "site": "Apple",
      "slug": "apple",
      "index": 40,
      "question": "Find information on Apple website, and tell me the device weight of Apple Vision Pro and list 5 Built-in Apps it supports.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "Device Weight, 21.2–22.9 ounces (600–650 g); Built‑in Apps: App Store, Encounter Dinosaurs, Files, Freeform, Keynote...",
      "answer_length": 119,
      "question_length": 122,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Apple--41",
      "site": "Apple",
      "slug": "apple",
      "index": 41,
      "question": "How much does it cost to buy an ipad mini with 64GB storage and Wi-Fi + Cellular connectivity? (no engraving, no apple pencil, no smart folio, no apple trade-in).",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "$649",
      "answer_length": 4,
      "question_length": 162,
      "actions": [
        "answer"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Apple--42",
      "site": "Apple",
      "slug": "apple",
      "index": 42,
      "question": "Find updates for Apple Watch Series 7,8,9 on Apple's website.",
      "local_url": "http://localhost:40002/",
      "upstream_url": "https://www.apple.com/",
      "original_web": "https://www.apple.com/",
      "answer_type": "possible",
      "answer": "see https://www.apple.com/watch/compare/, <summary>",
      "answer_length": 51,
      "question_length": 61,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "ArXiv--0",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 0,
      "question": "Search for the latest preprints about 'quantum computing'.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "Any paper related to quantum computing (latest)",
      "answer_length": 47,
      "question_length": 58,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ArXiv--1",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 1,
      "question": "Search for the latest research papers on quantum computing submitted to ArXiv within the last two days.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "Paper related to quantum computing (latest 2 days)",
      "answer_length": 50,
      "question_length": 103,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "ArXiv--2",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 2,
      "question": "Look up the most recent papers related to 'cs.CL', select one and show its abstract.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "cs.CL paper, <abstract>",
      "answer_length": 23,
      "question_length": 84,
      "actions": [
        "find",
        "answer",
        "use_tool"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 5
    },
    {
      "id": "ArXiv--3",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 3,
      "question": "Locate the most recent research paper about 'Algebraic Topology' under Mathematics published on ArXiv. Provide the title of the paper, the name of the authors, and the abstract.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "math.AT paper, <title>, <authors>, <abstract>",
      "answer_length": 45,
      "question_length": 177,
      "actions": [
        "find",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "ArXiv--4",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 4,
      "question": "Find the most recent research papers in Astrophysics of Galaxies. How many papers have been announced in the last day?",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "22 Dec 2023, 18 (real-time)",
      "answer_length": 27,
      "question_length": 118,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "ArXiv--5",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 5,
      "question": "Search papers about \"quantum computing\" which has been submitted to the Quantum Physics category on ArXiv. How many results in total. What if search in all archives?",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "23081 results, searching in archive quant-ph; 39482 results, search in all archives",
      "answer_length": 83,
      "question_length": 165,
      "actions": [
        "search"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "ArXiv--6",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 6,
      "question": "How many figures and tables are in the paper \"On the Sentence Embeddings from Pre-trained Language Models\"?",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "golden",
      "answer": "2 Figures, 8 Tables.",
      "answer_length": 20,
      "question_length": 107,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "ArXiv--7",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 7,
      "question": "Find the most recent paper submitted on machine learning in the Computer Science category posted on ArXiv.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "Latest cs.LG paper",
      "answer_length": 18,
      "question_length": 106,
      "actions": [
        "find"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "ArXiv--8",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 8,
      "question": "What is the latest news on ArXiv?",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "'Accessibility update: arXiv now offers papers in HTML format' (December 21, 2023)",
      "answer_length": 82,
      "question_length": 33,
      "actions": [
        "answer"
      ],
      "domains": [
        "research",
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "ArXiv--9",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 9,
      "question": "Find the latest research paper about neural networks published on ArXiv which has been submitted within the last week.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "Latest paper related to neural networks",
      "answer_length": 39,
      "question_length": 118,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "ArXiv--10",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 10,
      "question": "Visit ArXiv Help on how to withdraw an article if the submission is not yet announced.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "golden",
      "answer": "If your submission has not yet become publicly available you may delete or delay it. To do either of these things go to your user page and select either the Delete or Unsubmit icon.",
      "answer_length": 181,
      "question_length": 86,
      "actions": [
        "answer"
      ],
      "domains": [
        "research",
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "ArXiv--11",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 11,
      "question": "For Non-English submissions, do I need to provide a multi-language abstract, if need, answer the separator between the multiple abstracts.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "golden",
      "answer": "-----",
      "answer_length": 5,
      "question_length": 138,
      "actions": [
        "answer",
        "filter_sort"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "ArXiv--12",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 12,
      "question": "Find store in arXiv Help, tell me how many styles of arXiv Logo Shirt are available?",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "golden",
      "answer": "3",
      "answer_length": 1,
      "question_length": 84,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ArXiv--13",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 13,
      "question": "How many articles on ArXiv with 'SimCSE' in the title?",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "4",
      "answer_length": 1,
      "question_length": 54,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "ArXiv--14",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 14,
      "question": "On ArXiv, how many articles have 'SimCSE' in the article and are originally announced in October 2023?",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "golden",
      "answer": "3",
      "answer_length": 1,
      "question_length": 102,
      "actions": [
        "answer"
      ],
      "domains": [
        "research",
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "ArXiv--15",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 15,
      "question": "Searching Chinese Benchmark on ArXiv, how many papers announced in December 2023 mention being accepted for AAAI 2024?",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "2",
      "answer_length": 1,
      "question_length": 118,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ArXiv--16",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 16,
      "question": "Locate the latest research about gravitational waves that were uploaded to ArXiv this week and provide a brief summary of one article's main findings.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "Latest gravitational waves paper, <summary>",
      "answer_length": 43,
      "question_length": 150,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "research",
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ArXiv--17",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 17,
      "question": "Find the paper 'GPT-4 Technical Report', when was v3 submitted?",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "golden",
      "answer": "Mon, 27 Mar 2023 17:46:54 UTC",
      "answer_length": 29,
      "question_length": 63,
      "actions": [
        "find"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ArXiv--18",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 18,
      "question": "Download the paper 'Dense Passage Retrieval for Open-Domain Question Answering'. How many formulas are in the article and which one is the loss function?",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "golden",
      "answer": "2 formulas, the second one is loss function",
      "answer_length": 43,
      "question_length": 153,
      "actions": [
        "answer"
      ],
      "domains": [
        "research",
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 2
    },
    {
      "id": "ArXiv--19",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 19,
      "question": "Which university maintains and manages ArXiv. Accessing the university's website from ArXiv, how many underegraduate students are currently at the university.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "Cornell University, 16071 UNDERGRADUATE STUDENTS",
      "answer_length": 48,
      "question_length": 158,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "ArXiv--20",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 20,
      "question": "Find the latest paper on 'machine learning in the Statistics section of ArXiv and provide its abstract.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "stat.ML paper, <abstract>",
      "answer_length": 25,
      "question_length": 103,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ArXiv--21",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 21,
      "question": "Search for papers on 'neural networks for image processing' in the Computer Science category on ArXiv and report how many were submitted in the last week.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "cs paper related to 'neural networks for image processing',",
      "answer_length": 59,
      "question_length": 154,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ArXiv--22",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 22,
      "question": "Locate the ArXiv Help section and find instructions on how to subscribe to daily listing emails for new submissions in a specific category.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "To: arch-ive@arxiv.org \\n Subject: subscribe Your Full Name",
      "answer_length": 59,
      "question_length": 139,
      "actions": [
        "find"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "ArXiv--23",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 23,
      "question": "Determine how many articles with the keyword 'autonomous vehicles' were published in the 'Electrical Engineering and Systems Science' section of ArXiv yesterday.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "eess.SY paper related to autonomous vehicles",
      "answer_length": 44,
      "question_length": 161,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "ArXiv--24",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 24,
      "question": "Identify the most recent paper related to 'graph neural networks' on ArXiv and determine the affiliation of the first author.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "paper related to graph neural networks",
      "answer_length": 38,
      "question_length": 125,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "ArXiv--25",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 25,
      "question": "Browse the ArXiv store and let me know how many different types of merchandise are available.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "golden",
      "answer": "6, arXiv Logo Shirt, arXiv Logo Mug, arXiv is Open Science, Gift cards, arXiv Morning Mug, arXiv Forever",
      "answer_length": 104,
      "question_length": 93,
      "actions": [
        "search"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 3
    },
    {
      "id": "ArXiv--26",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 26,
      "question": "Search for papers related to 'climate change modeling' on ArXiv and find out how many have been published in the Earth and Planetary Astrophysics (astro-ph.EP) category in the last week.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "astro-ph.EP paper related to climate change modeling last week",
      "answer_length": 62,
      "question_length": 186,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ArXiv--27",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 27,
      "question": "On ArXiv, what categories does Economics include, and what are their abbreviations?",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "golden",
      "answer": "Econometrics (econ.EM), General Economics (econ.GN), and Theoretical Economics (econ.TH)",
      "answer_length": 88,
      "question_length": 83,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "ArXiv--28",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 28,
      "question": "Search 'Poly encoder' by title on ArXiv and check whether the articles in the search results provide HTML access.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "'Persona-Coded Poly-Encoder: Persona-Guided Multi-Stream Conversational Sentence Scoring', Access include: HTML (experimental)",
      "answer_length": 126,
      "question_length": 113,
      "actions": [
        "search",
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ArXiv--29",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 29,
      "question": "On ArXiv, search for papers with 'Neural Network Optimization' in the title published in 2023, and provide the number of such papers.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "240+ (search by title)",
      "answer_length": 22,
      "question_length": 133,
      "actions": [
        "find",
        "search",
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "ArXiv--30",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 30,
      "question": "Look up the submission guidelines on ArXiv for submitting a paper and tell me the formats for figures.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "golden",
      "answer": "Accepted figure formats: PostScript (PS, EPS) — requires LaTeX processing; JPEG, GIF, PNG or PDF figures — requires PDFLaTeX processing",
      "answer_length": 135,
      "question_length": 102,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ArXiv--31",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 31,
      "question": "Search ArXiv for papers with 'Graph Neural Networks' in the abstract that were submitted between Jan 1, 2024, and Jan 3, 2024, and determine how many of these papers have more than five authors.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "golden",
      "answer": "7 papers",
      "answer_length": 8,
      "question_length": 194,
      "actions": [
        "search",
        "filter_sort"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 6,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "ArXiv--32",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 32,
      "question": "Locate the latest paper on ArXiv within the 'Nonlinear Sciences - Chaotic Dynamics' category, summarize the abstract and note the submission date.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "latest nlin.CD paper, <abstract>, <date>",
      "answer_length": 40,
      "question_length": 146,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "research",
        "knowledge"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "ArXiv--33",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 33,
      "question": "Query ArXiv for the latest research article in the category of Systems and Control under Computer Science. Summarize the main objective or hypothesis presented in the paper and provide the names of the authors.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "eess.SY paper",
      "answer_length": 13,
      "question_length": 210,
      "actions": [
        "answer",
        "filter_sort"
      ],
      "domains": [
        "research",
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "ArXiv--34",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 34,
      "question": "Search for the most recent paper related to non-commutative geometry submitted by an author with the first name John. Provide the title and the abstract.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "Finite spectral triples for the fuzzy torus, Authors: John W. Barrett, James Gaunt, <abstract>",
      "answer_length": 94,
      "question_length": 153,
      "actions": [
        "find",
        "search",
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "ArXiv--35",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 35,
      "question": "Retrieve the latest research paper in Quantum Physics from ArXiv and provide the title, author(s), and date of submission.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "paper related to Quantum Physics",
      "answer_length": 32,
      "question_length": 122,
      "actions": [
        "answer"
      ],
      "domains": [
        "research",
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ArXiv--36",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 36,
      "question": "Search 'CVPR 2023' and 'CVPR2023' through journal ref on ArXiv to see how many results there are respectively.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "golden",
      "answer": "'CVPR 2023': 48 results; 'CVPR2023': 9 results",
      "answer_length": 46,
      "question_length": 110,
      "actions": [
        "search"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ArXiv--37",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 37,
      "question": "Find the names of people in ArXiv's Leadership Team.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "golden",
      "answer": "Ramin Zabih, Yoav Artzi, Stephanie Orphan, Steinn Sigurdsson, and Charles Frankston.",
      "answer_length": 84,
      "question_length": 52,
      "actions": [
        "find"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "ArXiv--38",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 38,
      "question": "Find the ArXiv Blog on the ArXiv website and summarize the content of its latest article.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "'Attention arXiv users: Re-implemented RSS', January 31, 2024, <summary>",
      "answer_length": 72,
      "question_length": 89,
      "actions": [
        "find"
      ],
      "domains": [
        "research",
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "ArXiv--39",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 39,
      "question": "Search the title 'GPT-4 Technical Report' and access this paper through HTML format. Read the paper on this page and tell me what is 'one of the main goals of developing such models' mentioned in the Introduction.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "golden",
      "answer": "One of the main goals of developing such models is to improve their ability to understand and generate natural language text, particularly in more complex and nuanced scenarios.",
      "answer_length": 177,
      "question_length": 213,
      "actions": [
        "search",
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "ArXiv--40",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 40,
      "question": "How many articles are there on each of the three most recent announce days in the Solar and Stellar Astrophysics section of ArXiv. Choose one at random and answer its title and when the first version was uploaded?",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "possible",
      "answer": "astro-ph.SR paper, latest 3 days",
      "answer_length": 32,
      "question_length": 213,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "ArXiv--41",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 41,
      "question": "Find the button to share arxiv non-profit store and follow the QR code to share the shop. Then add arXiv Forever short sleeve (XL) to your cart.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "golden",
      "answer": "QR code image, Action: add to chart",
      "answer_length": 35,
      "question_length": 144,
      "actions": [
        "find"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 3
    },
    {
      "id": "ArXiv--42",
      "site": "ArXiv",
      "slug": "arxiv",
      "index": 42,
      "question": "Find an article published between 1 January 2000 and 1 January 2005 that requires Support Vector Machines in the title and its Journey ref is ACL Workshop.",
      "local_url": "http://localhost:40003/",
      "upstream_url": "https://arxiv.org/",
      "original_web": "https://arxiv.org/",
      "answer_type": "golden",
      "answer": "'Using a Support-Vector Machine for Japanese-to-English Translation of Tense, Aspect, and Modality'",
      "answer_length": 99,
      "question_length": 155,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "travel",
        "knowledge"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "BBC News--0",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 0,
      "question": "Find a report on the BBC News website about recent developments in renewable energy technologies in the UK.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "<report> (about developments in renewable energy technologies in the UK)",
      "answer_length": 72,
      "question_length": 107,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "BBC News--1",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 1,
      "question": "Read the latest health-related news article published on BBC News and summarize the key points discussed.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "<summary> (about latest health-related article)",
      "answer_length": 47,
      "question_length": 105,
      "actions": [
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "BBC News--2",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 2,
      "question": "Read the latest article regarding the environmental impacts of deforestation published within the last two days.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "<article> (within the last 2 days)",
      "answer_length": 34,
      "question_length": 112,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "BBC News--3",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 3,
      "question": "Check the leaderboard for Golf's DP World Tour in the SPORT section, what was the name of the most recent tournament, and how many teams have a Total of -10 strokes.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "Mauritius Open; 5",
      "answer_length": 17,
      "question_length": 165,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "BBC News--4",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 4,
      "question": "Find the latest article regarding the economic implications of climate change in Europe as reported by BBC News and summarize the central points.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "<summary> (economic implications of climate change in Europe)",
      "answer_length": 61,
      "question_length": 145,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "BBC News--5",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 5,
      "question": "Find the article \"What is climate change? A really simple guide\" and use it to answer what human activities are causing climate change.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "golden",
      "answer": "This recent climate change has been caused by human activity, mainly the widespread use of fossil fuels - coal, oil and gas - in homes, factories and transport.",
      "answer_length": 160,
      "question_length": 135,
      "actions": [
        "find",
        "answer",
        "use_tool"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "BBC News--6",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 6,
      "question": "Find the top story from BBC News in the technology section for today.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "Latest news in Innovation - Technology",
      "answer_length": 38,
      "question_length": 69,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "BBC News--7",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 7,
      "question": "Find a AI-related story under Technology of Business. What is in the first picture in the story?",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "Analyse the first image in story.",
      "answer_length": 33,
      "question_length": 96,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "BBC News--8",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 8,
      "question": "Get a brief overview of the economic implications of the UK's latest trade deal posted on BBC News and the date when the article was published.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "CPTPP trade deal, <summary>; 16th July 2023",
      "answer_length": 43,
      "question_length": 143,
      "actions": [
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "BBC News--9",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 9,
      "question": "Find out which musician made the headlines in Music News.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "Taylor Swift",
      "answer_length": 12,
      "question_length": 57,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "BBC News--10",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 10,
      "question": "Identify the main headlines covering the UK's plan to tackle climate change on BBC News.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "News about UK's plan to tackle climate change",
      "answer_length": 45,
      "question_length": 88,
      "actions": [
        "plan"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "BBC News--11",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 11,
      "question": "Find out how many teams are in the Scottish Premiership of the Football Tournament and when did the Hibernian team's most recent match start?",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "12 teams, 15:00, 2 Jan 2024",
      "answer_length": 27,
      "question_length": 141,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "BBC News--12",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 12,
      "question": "Find a picture in the travel section that contains food, tell me what the food is called and what region it comes from.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "ramen, Tokyo",
      "answer_length": 12,
      "question_length": 119,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "BBC News--13",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 13,
      "question": "Search for recent news related to Trump and summarize the main points.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "<summary> (about Trump)",
      "answer_length": 23,
      "question_length": 70,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "BBC News--14",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 14,
      "question": "Find a news article on BBC News about the impact of the recent tech industry layoffs on the global economy. Summarize the key points and the name of the author, and provide the date of publication.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "<title>, <author>, <summary> (impact of the recent tech industry layoffs on the global economy)",
      "answer_length": 95,
      "question_length": 197,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "research",
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "BBC News--15",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 15,
      "question": "What does the current headline in Natural Wonders tell about.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "Name that whale! How AI aces animal spotting",
      "answer_length": 44,
      "question_length": 61,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "BBC News--16",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 16,
      "question": "Identify the most recent development or update in Brexit negotiations as reported on BBC News and report the key points and any stated impacts on European economies.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "<summary> (Brexit negotiations)",
      "answer_length": 31,
      "question_length": 165,
      "actions": [
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "BBC News--17",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 17,
      "question": "How many War related sections are currently in BBC News.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "2",
      "answer_length": 1,
      "question_length": 56,
      "actions": [
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "BBC News--18",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 18,
      "question": "Visit BBC News Audio, What are the best PodCasts for 2023? List 2 of them.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "2 of them: Believe in Magic, The Gift, Vishal, A Very British Cult, People Who Knew Me, History's Secret Heroes",
      "answer_length": 111,
      "question_length": 74,
      "actions": [
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "BBC News--19",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 19,
      "question": "Visit the Athletics calendar for the date of the next earliest game.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "17th - 18th February 2024",
      "answer_length": 25,
      "question_length": 68,
      "actions": [
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "BBC News--20",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 20,
      "question": "Find the latest article in the Green Living section on BBC News and provide a summary of its main points.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "Earth - Green Living, <article>, <summary>",
      "answer_length": 42,
      "question_length": 105,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "BBC News--21",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 21,
      "question": "Identify the top headline in the World News section on BBC News and describe the region it is related to.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "News - World, <headline>, <region>",
      "answer_length": 34,
      "question_length": 105,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "BBC News--22",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 22,
      "question": "Determine the current top business story on BBC News and give a brief overview of its economic implications.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "Business, <article>, <summary>, economic implications",
      "answer_length": 53,
      "question_length": 108,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "BBC News--23",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 23,
      "question": "Identify the latest health-related news on BBC News and summarize the main findings or recommendations.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "Innovation - Science & Health, <article>, <summary>",
      "answer_length": 51,
      "question_length": 103,
      "actions": [
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "BBC News--24",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 24,
      "question": "Search the latest article about space exploration on BBC News and summarize its key points.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "Search for space exploration, eg. SpaceX blasts private firm's lunar lander into orbit",
      "answer_length": 86,
      "question_length": 91,
      "actions": [
        "search"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "BBC News--25",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 25,
      "question": "Find the most recent sports analysis article on BBC News related to the English Premier League and summarize its key insights.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "Sport - Football - Leagues & Cups - Premier League, <article>",
      "answer_length": 61,
      "question_length": 126,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "BBC News--26",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 26,
      "question": "Locate the latest report on BBC News about the impact of recent natural disasters in Asia and summarize the key points and areas affected.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "Earth - Weather & Science, eg. Indonesia hit by some of strongest winds recorded",
      "answer_length": 80,
      "question_length": 138,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "BBC News--27",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 27,
      "question": "Find the most recent article on BBC News about archaeological discoveries and summarize the main findings and their significance.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "Archaeological discoveries: eg, Historical 10,000BC artefacts found on road project, Significant discoveries",
      "answer_length": 108,
      "question_length": 129,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "BBC News--28",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 28,
      "question": "Find the Market Data section on BBC News and tell me which company the data comes from.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "golden",
      "answer": "Business - Market Data, Source: Morningstar",
      "answer_length": 43,
      "question_length": 87,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "BBC News--29",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 29,
      "question": "Visit BBC News Audio and find out which podcast episode is currently featured as the \"New Releases\".",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "Audio - Podcasts - New Releases ...",
      "answer_length": 35,
      "question_length": 100,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "BBC News--30",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 30,
      "question": "In the Culture section, identify the latest film release reviewed and provide a brief summary of the review.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "Culture - Film & TV, <review>, <summary>",
      "answer_length": 40,
      "question_length": 108,
      "actions": [
        "answer"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "BBC News--31",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 31,
      "question": "Check the Sports section for the result of the most recent Manchester United football match.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "Sunday 11th February, Aston Villa 1:2 Manchester United",
      "answer_length": 55,
      "question_length": 92,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "BBC News--32",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 32,
      "question": "Find the artificial intelligence section, what is the top headline at this time, and which companies are involved?",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "Innovation - Artificial Intelligence, <headline>, <companies>",
      "answer_length": 61,
      "question_length": 114,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "BBC News--33",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 33,
      "question": "In the World News section, find the latest war situations of Middle East and provide a brief summary.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "News - Israel-Gaza War, <article>, <summary>",
      "answer_length": 44,
      "question_length": 101,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "BBC News--34",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 34,
      "question": "Find The SpeciaList section in Travel and browse the page to see which cities are mentioned.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "Sydney, New York, Tenerife ...",
      "answer_length": 30,
      "question_length": 92,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 4
    },
    {
      "id": "BBC News--35",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 35,
      "question": "In the Asia section, browse and identify the most recent report about technological advancements and summarize its content.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "News - World - Asia, <article>, <summary>",
      "answer_length": 41,
      "question_length": 123,
      "actions": [
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 3
    },
    {
      "id": "BBC News--36",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 36,
      "question": "Look up recent articles in the Africa news section in World, summarize what topics most of these news are about",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "News - World - Africa, <article>, <summary>",
      "answer_length": 43,
      "question_length": 111,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "BBC News--37",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 37,
      "question": "Identify the latest book review featured in the Culture section and provide the title and author of the book.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "Culture - Books, eg, Sloane Crosley: What to do when you lose a friend",
      "answer_length": 70,
      "question_length": 109,
      "actions": [
        "answer",
        "book_buy"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 0,
      "requires_state": true,
      "requires_navigation": true,
      "complexity": 6
    },
    {
      "id": "BBC News--38",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 38,
      "question": "Find news related to the storm in Weather section and indicate where and when the severe weather occurred.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "Earth - Weather & Science, article about severe weather, eg, You can't hear it, but this sound can reveal that a tornado is on its way",
      "answer_length": 134,
      "question_length": 106,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "BBC News--39",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 39,
      "question": "Check the Horse Racing results in Sport section, browse all the games that took place yesterday and see which one had the highest number of runners.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "eg, 2024-01-30: Chepstow Summer Sessions Handicap Chase, 13 runners",
      "answer_length": 67,
      "question_length": 148,
      "actions": [
        "search",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 5
    },
    {
      "id": "BBC News--40",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 40,
      "question": "Read and summarise a recent story on BBC News about people being injured or killed in wars.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "News - Israel-Gaza War, <article>",
      "answer_length": 33,
      "question_length": 91,
      "actions": [
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "BBC News--41",
      "site": "BBC News",
      "slug": "bbc_news",
      "index": 41,
      "question": "Find Golf in BBC News, check the Leaderboard at this point in Women's Majors and count which country has the most players in the top 20? Which player has the best score amongst the Australian players and in what place.",
      "local_url": "http://localhost:40004/",
      "upstream_url": "https://www.bbc.com/news/",
      "original_web": "https://www.bbc.com/news/",
      "answer_type": "possible",
      "answer": "Sport - Golf - Leaderboard - Women's Majors, most in top20: American, best in Australian: Grace Kim in 36",
      "answer_length": 105,
      "question_length": 218,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Booking--0",
      "site": "Booking",
      "slug": "booking",
      "index": 0,
      "question": "Find a Mexico hotel with deals for December 25-26.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Be Local",
      "answer_length": 8,
      "question_length": 50,
      "actions": [
        "find"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Booking--1",
      "site": "Booking",
      "slug": "booking",
      "index": 1,
      "question": "Find the cheapest available hotel room for a three night stay from 1st Jan in Jakarta. The room is for 2 adults, just answer the cheapest hotel room and the price.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "OYO 3755 Sweet Home, US$14",
      "answer_length": 26,
      "question_length": 163,
      "actions": [
        "find",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "travel"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Booking--2",
      "site": "Booking",
      "slug": "booking",
      "index": 2,
      "question": "Find a hotel in Ohio From December 20th to December 23th for 3 adults and 2 rooms.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Berlin Heritage Inn, US$549 for 3 adults and 2 rooms",
      "answer_length": 52,
      "question_length": 82,
      "actions": [
        "find"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Booking--3",
      "site": "Booking",
      "slug": "booking",
      "index": 3,
      "question": "Find a hotel with 4 star and above rating in Los Angeles for 3 days from Dec 18th.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Freehand Los Angeles",
      "answer_length": 20,
      "question_length": 82,
      "actions": [
        "find",
        "filter_sort",
        "save_state"
      ],
      "domains": [
        "shopping",
        "travel"
      ],
      "constraint_count": 4,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 10
    },
    {
      "id": "Booking--4",
      "site": "Booking",
      "slug": "booking",
      "index": 4,
      "question": "Search for the cheapest Hotel near Kashi Vishwanath Temple that offer breakfast from Dec 25th - Dec 26th.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Moonlight Residency, Breakfast included, US$14",
      "answer_length": 46,
      "question_length": 105,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "travel",
        "local_maps"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Booking--5",
      "site": "Booking",
      "slug": "booking",
      "index": 5,
      "question": "Search a hotel with free WiFi and air conditioning in Bali from Jan 1 to Jan 4, 2024.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Palasari Villa, free WiFi and air conditioning",
      "answer_length": 46,
      "question_length": 85,
      "actions": [
        "search"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Booking--6",
      "site": "Booking",
      "slug": "booking",
      "index": 6,
      "question": "Book one room which provides breakfast, and airport shuttle from Jan 22 to 25 in Los Angeles.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "La Quinta by Wyndham LAX",
      "answer_length": 24,
      "question_length": 93,
      "actions": [
        "book_buy"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 4,
      "requires_state": true,
      "requires_navigation": true,
      "complexity": 9
    },
    {
      "id": "Booking--7",
      "site": "Booking",
      "slug": "booking",
      "index": 7,
      "question": "Find a hotel room on January 3-6 that is closest to National University of Singapore and costs less than $500",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Fragrance Hotel - Ocean View",
      "answer_length": 28,
      "question_length": 109,
      "actions": [
        "find",
        "filter_sort",
        "plan"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Booking--8",
      "site": "Booking",
      "slug": "booking",
      "index": 8,
      "question": "Get the hotel with highest review score and free cancelation in Chennai for 20/12/2023 - 21/12/2023.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "OYO Flagship Valasaravakkam",
      "answer_length": 27,
      "question_length": 100,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "travel",
        "knowledge"
      ],
      "constraint_count": 7,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Booking--9",
      "site": "Booking",
      "slug": "booking",
      "index": 9,
      "question": "Find hotels for 2 adults in London with a price less than 250 dollars for four days starting from December 25. You must browse the page and offer at least 3 options.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "The Birds Nest Hostel; Umbrella Properties London Excel; Umbrella Properties London Woolwich",
      "answer_length": 92,
      "question_length": 165,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 7,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 9
    },
    {
      "id": "Booking--10",
      "site": "Booking",
      "slug": "booking",
      "index": 10,
      "question": "Find a well-reviewed hotel in Paris with available bookings suitable for a couple (2 adults) on Valentine's Day week, February 14-21, 2024, that offers free cancellation options.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Villa Alessandra",
      "answer_length": 16,
      "question_length": 178,
      "actions": [
        "find"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Booking--11",
      "site": "Booking",
      "slug": "booking",
      "index": 11,
      "question": "Reserve a hotel in downtown Chicago with a rating of 9 or higher for a stay from March 20-27, 2024, which offers free cancellation and includes a fitness center.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Pendry Chicago",
      "answer_length": 14,
      "question_length": 161,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "travel"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Booking--12",
      "site": "Booking",
      "slug": "booking",
      "index": 12,
      "question": "Find a hotel in Paris with a customer review score of 8 or higher, free Wi-Fi, and available for a 5-night stay starting on January 5th, 2024.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Mode Paris Aparthotel",
      "answer_length": 21,
      "question_length": 142,
      "actions": [
        "find"
      ],
      "domains": [
        "shopping",
        "travel",
        "knowledge"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Booking--13",
      "site": "Booking",
      "slug": "booking",
      "index": 13,
      "question": "Find and book a hotel in Paris with suitable accommodations for a family of four (two adults and two children) offering free cancellation for the dates of February 14-21, 2024.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Le Bellevue",
      "answer_length": 11,
      "question_length": 176,
      "actions": [
        "find",
        "book_buy"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 3,
      "requires_state": true,
      "requires_navigation": true,
      "complexity": 9
    },
    {
      "id": "Booking--14",
      "site": "Booking",
      "slug": "booking",
      "index": 14,
      "question": "Book a highly-rated hotel with a swimming pool and free WiFi near the Louvre Museum in Paris for the weekend of March 3-5, 2024.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Nolinski Paris",
      "answer_length": 14,
      "question_length": 128,
      "actions": [
        "book_buy"
      ],
      "domains": [
        "travel",
        "local_maps"
      ],
      "constraint_count": 4,
      "requires_state": true,
      "requires_navigation": true,
      "complexity": 9
    },
    {
      "id": "Booking--15",
      "site": "Booking",
      "slug": "booking",
      "index": 15,
      "question": "Find the highest-rated luxury hotel in Rome available for booking from January 10, 2024, to January 20, 2024, for 2 adults. Include the cost, amenities offered, and customer rating.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Rhinoceros; rating 9.2; cost US$5771; Amenities: air conditioning, free WiFi...",
      "answer_length": 79,
      "question_length": 181,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "travel"
      ],
      "constraint_count": 7,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Booking--16",
      "site": "Booking",
      "slug": "booking",
      "index": 16,
      "question": "Look for a hotel in Paris with a user rating of 9 or higher and available for a 5-night stay starting January 15, 2024. The hotel should also offer free Wi-Fi and breakfast included in the price. Provide the name, location, and price per night.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Zoku Paris; 48 Avenue de la Porte de Clichy, 17th arr., Paris; US$210 per night",
      "answer_length": 79,
      "question_length": 244,
      "actions": [
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "travel"
      ],
      "constraint_count": 8,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Booking--17",
      "site": "Booking",
      "slug": "booking",
      "index": 17,
      "question": "Find a hotel in Paris with a fitness center and a rating of 8 or higher available for a 5-night stay starting from February 14, 2024, and sort the results by best reviewed.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Villa-des-Prés",
      "answer_length": 14,
      "question_length": 172,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "travel"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 8
    },
    {
      "id": "Booking--18",
      "site": "Booking",
      "slug": "booking",
      "index": 18,
      "question": "Search a hotel in London with a user rating of 8 or higher for a stay between February 14th, 2024, and February 21st, 2024, suitable for a couple. Provide the name and a short description of the hotel.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Cromwell Serviced Apartments; Cromwell Serviced Apartments is an apartment featuring rooms with free Wifi and air conditioning in the center of London",
      "answer_length": 150,
      "question_length": 201,
      "actions": [
        "search",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "travel"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Booking--19",
      "site": "Booking",
      "slug": "booking",
      "index": 19,
      "question": "Look for a hotel with customer ratings above an 8.0 in Paris, France for a weekend stay from March 18, 2024, to March 20, 2024, and list top three suggestions based on user reviews.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Hôtel des Arts Montmartre; Bulgari Hotel Paris; Four Seasons Hotel George V Paris",
      "answer_length": 81,
      "question_length": 181,
      "actions": [
        "answer",
        "filter_sort"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 8,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Booking--20",
      "site": "Booking",
      "slug": "booking",
      "index": 20,
      "question": "Locate a hotel in Rome with a good rating (7 or above) that offers free cancellation and breakfast included, for a three-night stay from February 28 to March 2, 2024, for two adults.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "47 Boutique Hotel, 8.6 ratings, breakfast included, free cancellation",
      "answer_length": 69,
      "question_length": 182,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "travel"
      ],
      "constraint_count": 7,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Booking--21",
      "site": "Booking",
      "slug": "booking",
      "index": 21,
      "question": "Find a hotel in Sydney with a rating of 8 or higher, providing free Wi-Fi and parking, available for a four-night stay starting on March 10, 2024.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Lexie Suites, 9.1 ratings, free Wi-Fi and parking",
      "answer_length": 49,
      "question_length": 146,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "travel",
        "local_maps"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Booking--22",
      "site": "Booking",
      "slug": "booking",
      "index": 22,
      "question": "Search for a hotel in Amsterdam with a customer review score of 9 or higher, offering bicycle rentals, for a week-long stay from March 15 to March 22, 2024, for two adults.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "nhow Amsterdam Rai, 9.0 ratings, bicycle rentals",
      "answer_length": 48,
      "question_length": 172,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "shopping",
        "travel",
        "knowledge"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Booking--23",
      "site": "Booking",
      "slug": "booking",
      "index": 23,
      "question": "Identify a hotel in Tokyo with a spa and wellness center, rated 9 or above, with availability for a five-night stay starting on February 20, 2024. Check if free cancellation is offered.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "The Peninsula Tokyo, 9.2 ratings, Spa and Fitness center",
      "answer_length": 56,
      "question_length": 185,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Booking--24",
      "site": "Booking",
      "slug": "booking",
      "index": 24,
      "question": "Find a hotel in Barcelona for a stay from February 25-28, 2024. Please sort the results by distance from the beach and make sure they offer free Wi-Fi and breakfast.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Unite Hostel Barcelona, 8.2 ratings, 400m from beach, free Wi-Fi and breakfast",
      "answer_length": 78,
      "question_length": 165,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 8
    },
    {
      "id": "Booking--25",
      "site": "Booking",
      "slug": "booking",
      "index": 25,
      "question": "Search for a hotel in Lisbon with airport shuttle, rated 8.5 or above, available for a six-night stay from March 1 to March 7, 2024, for two adults, breakfast included.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "The Homeboat Company Parque das Nações-Lisboa, 9.5 ratings, airport shuttle, breakfast included",
      "answer_length": 95,
      "question_length": 168,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 7,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Booking--26",
      "site": "Booking",
      "slug": "booking",
      "index": 26,
      "question": "Check Booking.com for a 3-star hotel or higher in Paris with a guest rating above 8.0 and available parking for dates February 20-23, 2024.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "InterContinental Paris Le Grand, an IHG Hotel, US$2208, 8.6 ratings, 5-star, parking",
      "answer_length": 84,
      "question_length": 139,
      "actions": [
        "filter_sort",
        "save_state"
      ],
      "domains": [
        "shopping",
        "travel",
        "local_maps"
      ],
      "constraint_count": 7,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 9
    },
    {
      "id": "Booking--27",
      "site": "Booking",
      "slug": "booking",
      "index": 27,
      "question": "Locate a hotel in Melbourne offering free parking and free WiFi, for a stay from February 28 to March 4, 2024.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Nesuto Docklands, 8.9 ratings, free parking and free WiFi",
      "answer_length": 57,
      "question_length": 110,
      "actions": [
        "find"
      ],
      "domains": [
        "travel",
        "local_maps"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Booking--28",
      "site": "Booking",
      "slug": "booking",
      "index": 28,
      "question": "Find a hotel in Dubai with a swimming pool, for a week-long stay from February 22 to February 29, 2024.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Park Regis by Prince Dubai Islands, swimming pool",
      "answer_length": 49,
      "question_length": 103,
      "actions": [
        "find"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Booking--29",
      "site": "Booking",
      "slug": "booking",
      "index": 29,
      "question": "Search for a hotel in Toronto with a fitness center and a rating of 8+, available for a two-night stay from March 5 to March 7, 2024.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Fairmont Royal York Hotel, 8.3 ratings, fitness center",
      "answer_length": 54,
      "question_length": 133,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "travel"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Booking--30",
      "site": "Booking",
      "slug": "booking",
      "index": 30,
      "question": "Search for hotels in London from March 20 to March 23, 2024, on Booking. How many hotels are left after applying the Breakfast included and Fitness center filters?",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "After applying the Breakfast included and Fitness center: 228 hotels",
      "answer_length": 68,
      "question_length": 163,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Booking--31",
      "site": "Booking",
      "slug": "booking",
      "index": 31,
      "question": "Search for hotels in Rio de Janeiro from March 1-7, 2024, check the Brands filter to see which brand has the most hotels and which brand has the fewest.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Brands has the most hotels: Windsor, Rede Atlântico; Brands has the fewest hotels: Ramada",
      "answer_length": 89,
      "question_length": 152,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 8
    },
    {
      "id": "Booking--32",
      "site": "Booking",
      "slug": "booking",
      "index": 32,
      "question": "Look for hotels in Sydney from February 24 to February 27, 2024, on Booking. Once the Swimming Pool and Airport Shuttle filters are applied, what is the total number of hotels available?",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Swimming Pool and Airport Shuttle filters are applied: 1 hotel",
      "answer_length": 62,
      "question_length": 186,
      "actions": [
        "answer"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Booking--33",
      "site": "Booking",
      "slug": "booking",
      "index": 33,
      "question": "Find the Customer Service on the Booking website, browse the questions about cancellation, and tell me 'how do I know whether my booking has been cancelled'.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "golden",
      "answer": "After you cancel a booking with us, you should get an email confirming the cancellation. Make sure to check your inbox and spam/junk mail folders. If you don’t receive an email within 24 hours, contact the property to confirm they got your cancellation.",
      "answer_length": 253,
      "question_length": 157,
      "actions": [
        "find",
        "search",
        "answer"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 5
    },
    {
      "id": "Booking--34",
      "site": "Booking",
      "slug": "booking",
      "index": 34,
      "question": "Search for a hotel in Berlin available for a three-night stay from March 15 to March 18, 2024, for one adult. Tell me the price in USD and CNY for the three-night stay.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Hotel Adlon Kempinski Berlin, US$1185, CNY 8528",
      "answer_length": 47,
      "question_length": 168,
      "actions": [
        "find",
        "search",
        "answer"
      ],
      "domains": [
        "shopping",
        "travel"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Booking--35",
      "site": "Booking",
      "slug": "booking",
      "index": 35,
      "question": "Browse the booking website to get inspiration for your next trip, and summarize at least three places mentioned in one of the travel articles.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Ace Hotel, Downtown Los Angeles; The Hollywood Roosevelt; Hotel Indigo, an IHG Hotel",
      "answer_length": 84,
      "question_length": 142,
      "actions": [
        "search",
        "plan"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 5
    },
    {
      "id": "Booking--36",
      "site": "Booking",
      "slug": "booking",
      "index": 36,
      "question": "Search for a budget hotel in Rome under $100 per night for one adult from March 20 to March 23, 2024. Sort the results by price, identify if any of top three results offer breakfast.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "ROMA GONDOLA SRLS, US$81, no breakfast",
      "answer_length": 38,
      "question_length": 182,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "travel"
      ],
      "constraint_count": 8,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 9
    },
    {
      "id": "Booking--37",
      "site": "Booking",
      "slug": "booking",
      "index": 37,
      "question": "Search for a resort (not hotel) in Bali, detailing the available dates between March 20, 2024, and March 25, 2024, and checking any provided tour or cultural experiences.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Kappa Senses Ubud, resort, Activity include: Tour or class about local culture",
      "answer_length": 78,
      "question_length": 170,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Booking--38",
      "site": "Booking",
      "slug": "booking",
      "index": 38,
      "question": "Look up Vienna hotel options with availability for a 4-night stay from February 28 to March 4, 2024, with amenities that include a Parking, breakfast included, and a rating of 8+ on Booking.com.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "ARCOTEL Wimberger Wien, 8.2 ratings, Parking, breakfast included",
      "answer_length": 64,
      "question_length": 194,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "travel",
        "local_maps"
      ],
      "constraint_count": 7,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Booking--39",
      "site": "Booking",
      "slug": "booking",
      "index": 39,
      "question": "Find a pet-friendly hotel with parking available in downtown Toronto for the stay of February 24-26, 2024.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "One King West Hotel and Residence, pet-friendly hotel, parking",
      "answer_length": 62,
      "question_length": 106,
      "actions": [
        "find"
      ],
      "domains": [
        "travel",
        "local_maps"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Booking--40",
      "site": "Booking",
      "slug": "booking",
      "index": 40,
      "question": "I need to choose a hotel in Shenzhen, please select date (6 March to 8 March 2024) and click the search button. How much it costs when convert the price to Chinese Yuan on the page.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Four Seasons Hotel Shenzhen, US$522, CNY 3760",
      "answer_length": 45,
      "question_length": 181,
      "actions": [
        "search",
        "compute",
        "use_tool"
      ],
      "domains": [
        "shopping",
        "travel",
        "knowledge"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 9
    },
    {
      "id": "Booking--41",
      "site": "Booking",
      "slug": "booking",
      "index": 41,
      "question": "Browse Booking's homepage to find out which company it belongs to.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "golden",
      "answer": "Booking Holdings Inc.",
      "answer_length": 21,
      "question_length": 66,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 4
    },
    {
      "id": "Booking--42",
      "site": "Booking",
      "slug": "booking",
      "index": 42,
      "question": "Search for a hotel in Hokkaido for the period March 1 to March 7, 2024, with a rating of 9+, check out its user reviews, which categories are greater than 9 and which are less than 9?",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Heiseikan Shiosaitei Hanatsuki, 9.0 ratings, high: Staff 9.3, Facilities 9.0, Cleanliness 9.4, Comfort 9.3. low: Value for money 8.2, Location 8.7, Free WiFi 8.1",
      "answer_length": 161,
      "question_length": 183,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "travel"
      ],
      "constraint_count": 10,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Booking--43",
      "site": "Booking",
      "slug": "booking",
      "index": 43,
      "question": "Search for properties in Los Angeles, browse the results page to see what filters are available, list some of them.",
      "local_url": "http://localhost:40005/",
      "upstream_url": "https://www.booking.com/",
      "original_web": "https://www.booking.com/",
      "answer_type": "possible",
      "answer": "Breakfast Included, Wonderful: 9+, Fitness center ...",
      "answer_length": 53,
      "question_length": 115,
      "actions": [
        "find",
        "search",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 5
    },
    {
      "id": "GitHub--0",
      "site": "GitHub",
      "slug": "github",
      "index": 0,
      "question": "Search for an open-source project related to 'climate change data visualization' on GitHub and report the project with the most stars.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "golden",
      "answer": "resource-watch/resource-watch",
      "answer_length": 29,
      "question_length": 134,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 6
    },
    {
      "id": "GitHub--1",
      "site": "GitHub",
      "slug": "github",
      "index": 1,
      "question": "Search for an open-source repository for machine learning in Python, specifically focused on decision trees, updated within the last 2 days.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "google/yggdrasil-decision-forests",
      "answer_length": 33,
      "question_length": 140,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 8
    },
    {
      "id": "GitHub--2",
      "site": "GitHub",
      "slug": "github",
      "index": 2,
      "question": "Look for the trending Python repositories on GitHub with most stars.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "myshell-ai/OpenVoice",
      "answer_length": 20,
      "question_length": 68,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "GitHub--3",
      "site": "GitHub",
      "slug": "github",
      "index": 3,
      "question": "Find out how much more package storage the Enterprise version has over Team in GitHub Pricing.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "golden",
      "answer": "48GB",
      "answer_length": 4,
      "question_length": 94,
      "actions": [
        "find",
        "compare"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "GitHub--4",
      "site": "GitHub",
      "slug": "github",
      "index": 4,
      "question": "Find a popular JavaScript repository created in the last 30 days on GitHub with a Readme file.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "<repo> (use advanced search like 'javascript created:>2023-12-10 language:JavaScript')",
      "answer_length": 86,
      "question_length": 94,
      "actions": [
        "find"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "GitHub--5",
      "site": "GitHub",
      "slug": "github",
      "index": 5,
      "question": "Find a Python repository on GitHub that has been updated in the past 2 days and has at least 500 stars.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "<repo> (stars:\"> 500\" language:Python), then choose recently undated",
      "answer_length": 68,
      "question_length": 103,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "GitHub--6",
      "site": "GitHub",
      "slug": "github",
      "index": 6,
      "question": "Search for an open-source project related to 'cryptocurrency wallet' updated in the past 30 days and provide the top three contributors.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "blocknetdx/blocknet; laanwj, sipa, theuni",
      "answer_length": 41,
      "question_length": 136,
      "actions": [
        "find",
        "search",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 9
    },
    {
      "id": "GitHub--7",
      "site": "GitHub",
      "slug": "github",
      "index": 7,
      "question": "Find the official GitHub repository for ALBERT and show me what files the repo changed in the most recent commit.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "golden",
      "answer": "classifier_utils.py and squad_utils.py",
      "answer_length": 38,
      "question_length": 113,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "GitHub--8",
      "site": "GitHub",
      "slug": "github",
      "index": 8,
      "question": "Look up the latest stable release version of Vuex and find out when it was published.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "golden",
      "answer": "Latest v4.0.2 on Jun 17, 2021",
      "answer_length": 29,
      "question_length": 85,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "GitHub--9",
      "site": "GitHub",
      "slug": "github",
      "index": 9,
      "question": "Locate a repository on GitHub that was created in the last week and has 50 or more stars. Provide brief details about the project's purpose and its programming language.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "<repo> (stars:>=50 created:>=xxxx-xx-xx)",
      "answer_length": 40,
      "question_length": 169,
      "actions": [
        "find",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "GitHub--10",
      "site": "GitHub",
      "slug": "github",
      "index": 10,
      "question": "If I start using Copilot Individual, how much US dollars will it cost per year and what features does it have?",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "golden",
      "answer": "$100 per year; Code completions, Chat, and more for indie developers and freelancers.",
      "answer_length": 85,
      "question_length": 110,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "GitHub--11",
      "site": "GitHub",
      "slug": "github",
      "index": 11,
      "question": "Find a newly created open-source project on GitHub related to 'climate change' that has been initiated in January 2023; check the main programming language used and the project's description.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "TheAIDojo/AI-for-Climate-Change; Jupyter Notebook; Repository of notebooks and associated code that covers the fundamental concepts of deep learning and its application to climate science.",
      "answer_length": 188,
      "question_length": 191,
      "actions": [
        "find"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 5
    },
    {
      "id": "GitHub--12",
      "site": "GitHub",
      "slug": "github",
      "index": 12,
      "question": "Retrieve the latest release from the 'electron/electron' repository on GitHub and note down the release version number and date.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "v29.0.0-alpha.5, 19 hours ago (real-time release)",
      "answer_length": 49,
      "question_length": 128,
      "actions": [
        "answer"
      ],
      "domains": [
        "research",
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "GitHub--13",
      "site": "GitHub",
      "slug": "github",
      "index": 13,
      "question": "Identify the latest top-trending open-source project in the category of 'Machine Learning' on GitHub, and check the number of stars it has received.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "microsoft/ML-For-Beginners",
      "answer_length": 26,
      "question_length": 148,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 5
    },
    {
      "id": "GitHub--14",
      "site": "GitHub",
      "slug": "github",
      "index": 14,
      "question": "Locate the repository for the open-source project \"vscode\" and identify the top three contributors.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "bpasero; jrieken; mjbvz",
      "answer_length": 23,
      "question_length": 99,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 5
    },
    {
      "id": "GitHub--15",
      "site": "GitHub",
      "slug": "github",
      "index": 15,
      "question": "Locate a repository on GitHub related to 'quantum computing' that has been updated within the last week and has at least 50 stars. Provide a brief description of the project.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "desireevl/awesome-quantum-computing",
      "answer_length": 35,
      "question_length": 174,
      "actions": [
        "find",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "GitHub--16",
      "site": "GitHub",
      "slug": "github",
      "index": 16,
      "question": "Find the GitHub Skill section and how many courses are under the 'First day on GitHub' heading.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "golden",
      "answer": "3",
      "answer_length": 1,
      "question_length": 95,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "GitHub--17",
      "site": "GitHub",
      "slug": "github",
      "index": 17,
      "question": "Locate a C++ project on GitHub that has been recently updated in the last week and has at least 500 stars, then describe its main purpose.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "microsoft/terminal; The new Windows Terminal and the original Windows console host, all in the same place!",
      "answer_length": 106,
      "question_length": 138,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "GitHub--18",
      "site": "GitHub",
      "slug": "github",
      "index": 18,
      "question": "Identify and report the most popular (in terms of stars) open-source image processing tool on GitHub.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "golden",
      "answer": "OpenCV",
      "answer_length": 6,
      "question_length": 101,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 4
    },
    {
      "id": "GitHub--19",
      "site": "GitHub",
      "slug": "github",
      "index": 19,
      "question": "Look up the most recently updated Python repository on GitHub that is tagged with 'web scraping' and has over 100 stars.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "scrapy/scrapy",
      "answer_length": 13,
      "question_length": 120,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "GitHub--20",
      "site": "GitHub",
      "slug": "github",
      "index": 20,
      "question": "Open GitHub Copilot's FAQs to find the official answer to when Copilot chat can be used on mobile.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "golden",
      "answer": "'Chat in GitHub Mobile is coming soon.' OR 'We do not have a set timeline for making Copilot Chat available on mobile. We’ll continue to update this page with the latest information on new capabilities for various plans.'",
      "answer_length": 221,
      "question_length": 98,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 4
    },
    {
      "id": "GitHub--21",
      "site": "GitHub",
      "slug": "github",
      "index": 21,
      "question": "Find the Security topic in GitHub Resources and answer the role of GitHub Advanced Security.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "With AI-powered application security testing tools embedded in your development workflow, GitHub Advanced Security outperforms non-native add-ons by delivering 7x faster remediation rates for identified vulnerabilities.",
      "answer_length": 219,
      "question_length": 92,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "GitHub--22",
      "site": "GitHub",
      "slug": "github",
      "index": 22,
      "question": "Find an open-source repository on GitHub focused on natural language processing in Ruby, updated within the last week.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "<repo> (natural language processing language:Ruby)",
      "answer_length": 50,
      "question_length": 118,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 7
    },
    {
      "id": "GitHub--23",
      "site": "GitHub",
      "slug": "github",
      "index": 23,
      "question": "Find the wiki page of ohmyzsh on GitHub and tell me how to change the theme of zsh to agnoster.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "golden",
      "answer": "edit the .zshrc file and set the ZSH_THEME variable to \"agnoster\"",
      "answer_length": 65,
      "question_length": 95,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "GitHub--24",
      "site": "GitHub",
      "slug": "github",
      "index": 24,
      "question": "Locate the GitHub repository for the open-source project \"angular\" and identify the last three issues closed.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "recently closed issue in repo angular/angular: https://github.com/angular/angular/issues?q=is%3Aissue+is%3Aclosed",
      "answer_length": 113,
      "question_length": 109,
      "actions": [
        "find"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 3
    },
    {
      "id": "GitHub--25",
      "site": "GitHub",
      "slug": "github",
      "index": 25,
      "question": "Search for a 'virtual reality' related repository on GitHub updated in the last 10 days with at least 200 stars and summarize its main objective.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "<repo> (virtual reality stars:>=200), <summary>",
      "answer_length": 47,
      "question_length": 145,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "GitHub--26",
      "site": "GitHub",
      "slug": "github",
      "index": 26,
      "question": "Find the Resolve merge conflicts course in GitHub Skills and what actions learners will perform in this course.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "golden",
      "answer": "Create a pull request. Resolve a merge conflict. Create a merge conflict. Merge your pull request.",
      "answer_length": 98,
      "question_length": 111,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "GitHub--27",
      "site": "GitHub",
      "slug": "github",
      "index": 27,
      "question": "Find a Ruby repository on GitHub that has been updated in the past 3 days and has at least 1000 stars.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "<repo> (language:Ruby stars:>1000)",
      "answer_length": 34,
      "question_length": 102,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "GitHub--28",
      "site": "GitHub",
      "slug": "github",
      "index": 28,
      "question": "Identify the most starred JavaScript repositories on GitHub that were created after 2023-12-29.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "<repo> (language:JavaScript created:>2023-12-29), sort by Most stars",
      "answer_length": 68,
      "question_length": 95,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "GitHub--29",
      "site": "GitHub",
      "slug": "github",
      "index": 29,
      "question": "Compare the maximum number of private repositories allowed in the Free and Pro plans in GitHub Pricing.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "golden",
      "answer": "Unlimited",
      "answer_length": 9,
      "question_length": 103,
      "actions": [
        "compare"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "GitHub--30",
      "site": "GitHub",
      "slug": "github",
      "index": 30,
      "question": "Search for an open-source project related to 'blockchain technology' on GitHub updated in the past 15 days and list the top five contributors.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "eg, aptos-labs/aptos-core, contributors: davidiw, gregnazario, JoshLind, bmwill, rustielin",
      "answer_length": 90,
      "question_length": 142,
      "actions": [
        "find",
        "search",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 9
    },
    {
      "id": "GitHub--31",
      "site": "GitHub",
      "slug": "github",
      "index": 31,
      "question": "Find the official GitHub repository for TensorFlow and list the files changed in the last commit. Tell me the name of changed files, total additions and total deletion.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "Tensorflow latest commit",
      "answer_length": 24,
      "question_length": 168,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "GitHub--32",
      "site": "GitHub",
      "slug": "github",
      "index": 32,
      "question": "Discover the latest C# repository on GitHub related to 'game development' and having over 150 stars, and describe its main features.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "<repo> (game development language:C# stars:>150), <features>",
      "answer_length": 60,
      "question_length": 132,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "GitHub--33",
      "site": "GitHub",
      "slug": "github",
      "index": 33,
      "question": "Find Customer Stories on the GitHub page and list the 2 stories that appear on the web page.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "Philips builds and deploys digital health technology faster with innersource on GitHub. Shopify keeps pushing eCommerce forward with help from GitHub tools.",
      "answer_length": 156,
      "question_length": 92,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "GitHub--34",
      "site": "GitHub",
      "slug": "github",
      "index": 34,
      "question": "Search for an open-source project on GitHub related to 'Protein prediction' and identify the project with the highest number of forks.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "kexinhuang12345/DeepPurpose",
      "answer_length": 27,
      "question_length": 134,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 6
    },
    {
      "id": "GitHub--35",
      "site": "GitHub",
      "slug": "github",
      "index": 35,
      "question": "Check the latest release version of React and the date it was published on GitHub.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "golden",
      "answer": "18.2.0 (June 14, 2022)",
      "answer_length": 22,
      "question_length": 82,
      "actions": [
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "GitHub--36",
      "site": "GitHub",
      "slug": "github",
      "index": 36,
      "question": "Identify a new open-source project on GitHub related to 'AI agriculture' that created in 2022, and note its main programming language and description.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "<repo> (AI agriculture created:2022)",
      "answer_length": 36,
      "question_length": 150,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 4
    },
    {
      "id": "GitHub--37",
      "site": "GitHub",
      "slug": "github",
      "index": 37,
      "question": "List the 3 features mentioned in GitHub's Copilot product page.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "The AI coding assistant elevating developer workflows. Get AI-based suggestions in real time. Docs that feel tailored for you.",
      "answer_length": 126,
      "question_length": 63,
      "actions": [
        "answer"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "GitHub--38",
      "site": "GitHub",
      "slug": "github",
      "index": 38,
      "question": "Identify and report the most popular (by stars) open-source repo related to cybersecurity on GitHub.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "golden",
      "answer": "WerWolv/ImHex",
      "answer_length": 13,
      "question_length": 100,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 4
    },
    {
      "id": "GitHub--39",
      "site": "GitHub",
      "slug": "github",
      "index": 39,
      "question": "Browse the GitHub Trending and find out which developer is currently ranked first this month and the corresponding repository.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "possible",
      "answer": "find info on https://github.com/trending/developers",
      "answer_length": 51,
      "question_length": 126,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 4
    },
    {
      "id": "GitHub--40",
      "site": "GitHub",
      "slug": "github",
      "index": 40,
      "question": "Select Sign up on the GitHub homepage to see if email 'test123@gmail.com' already exists.",
      "local_url": "http://localhost:40006/",
      "upstream_url": "https://github.com/",
      "original_web": "https://github.com/",
      "answer_type": "golden",
      "answer": "Perform Action. email 'test123@gmail.com' already exists",
      "answer_length": 56,
      "question_length": 89,
      "actions": [
        "use_tool"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 3
    },
    {
      "id": "Google Flights--0",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 0,
      "question": "Book a journey with return option on same day from Edinburg to Manchester on December 28th and show me the lowest price option available.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Aer Lingus 11:40am - 4:45pm, $412 (real-time)",
      "answer_length": 45,
      "question_length": 137,
      "actions": [
        "answer",
        "filter_sort",
        "book_buy"
      ],
      "domains": [
        "shopping",
        "travel"
      ],
      "constraint_count": 2,
      "requires_state": true,
      "requires_navigation": true,
      "complexity": 9
    },
    {
      "id": "Google Flights--1",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 1,
      "question": "Show me the list of one-way flights today (February 17, 2024) from Chicago to Paris.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Air France 5:30 PM – 8:25 AM (+1), United 6:30 PM – 9:55 AM(+1), Delta 12:00 PM – 8:10 AM(+1)... (real-time)",
      "answer_length": 108,
      "question_length": 84,
      "actions": [
        "answer"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Google Flights--2",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 2,
      "question": "Find the lowest fare from all eligible one-way flights for 1 adult from JFK to Heathrow on Jan. 22.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Tap Air Portugal 10:00 PM – 5:30 PM(+1), $355 (real-time)",
      "answer_length": 57,
      "question_length": 99,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Google Flights--3",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 3,
      "question": "Search for the one-way flight available from Calgary to New York on Jan. 1st with the lowest carbon dioxide emissions.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "WestJet 9:55 AM – 4:34 PM, emission: 225 kg CO2, $704 (real-time)",
      "answer_length": 65,
      "question_length": 118,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Google Flights--4",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 4,
      "question": "Search for one-way flights from New York to London on Dec. 26th and filter the results to show only non-stop flights.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Norse Atlantic UK 6:10 PM – 6:00 AM(+1), $331, Nonstop (real-time)",
      "answer_length": 66,
      "question_length": 117,
      "actions": [
        "find",
        "search",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 7
    },
    {
      "id": "Google Flights--5",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 5,
      "question": "Find flights from Chicago to London on 20 December and return on 23 December.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Scandinavian Airlines 9:45 PM – 4:00 PM(+1), $1456 (real-time)",
      "answer_length": 62,
      "question_length": 77,
      "actions": [
        "find"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Google Flights--6",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 6,
      "question": "Search for a flight on December 19 and return on December 26 from Tel Aviv to Venice and Select First Class.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "flydubai, Emirates, and AccesRail, 12:40 PM - 8:34 PM(+1), $8991 (real-time)",
      "answer_length": 76,
      "question_length": 108,
      "actions": [
        "find",
        "search",
        "use_tool"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 7
    },
    {
      "id": "Google Flights--7",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 7,
      "question": "Find a round trip from Phoenix to Miami (Dec. 25th - Dec. 28th), show the First Class plane tickets for me that do not exceed $1320..",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "American Airlines, 5:44 AM – 1:25 PM, $1,247 (real-time)",
      "answer_length": 56,
      "question_length": 133,
      "actions": [
        "find",
        "answer",
        "plan"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Google Flights--8",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 8,
      "question": "Search a one-way filght from Dublin To Athens Greece for 1 Adult that leaves on December 30 and analyse the price graph for the next 2 months.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Analyse the picture of Price graph (real-time)",
      "answer_length": 46,
      "question_length": 142,
      "actions": [
        "search"
      ],
      "domains": [
        "shopping",
        "travel"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Google Flights--9",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 9,
      "question": "Find a one way economy flight from Pune to New York in Jan. 15th and show me how long it will take for flight transfer.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Air India, LOT, 3:55 PM – 8:35 PM(+1), transfer time: 18 hours 20 mins (real-time, Transfer time only.)",
      "answer_length": 103,
      "question_length": 119,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Google Flights--10",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 10,
      "question": "Locate the cheapest round-trip flights from New York to Tokyo leaving on January 25, 2024, and returning on February 15, 2024.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Air Canada, 9:15 AM – 4:50 PM(+1), $1169 (real-time)",
      "answer_length": 52,
      "question_length": 126,
      "actions": [
        "find",
        "filter_sort",
        "plan"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Google Flights--11",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 11,
      "question": "Compare the prices for round-trip flights from New York to Tokyo for a departure on February 10, 2024, and a return on February 24, 2024, and select the option with the least number of stops.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "United flight, 11:15 AM – 3:35 PM(+1), $1366, Nonstop (real-time)",
      "answer_length": 65,
      "question_length": 191,
      "actions": [
        "compare",
        "plan",
        "use_tool"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 9
    },
    {
      "id": "Google Flights--12",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 12,
      "question": "Find the best-priced round-trip flight from New York to London leaving on December 25, 2023, and returning on January 5, 2024, with one stop or fewer.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Norse Atlantic UK, 6:10 PM – 6:00 AM(+1), $757, Nonstop (real-time)",
      "answer_length": 67,
      "question_length": 150,
      "actions": [
        "find",
        "filter_sort",
        "plan"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Google Flights--13",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 13,
      "question": "Find the cheapest round-trip flight option from New York City to Tokyo for a departure on January 10, 2024, and a return on January 24, 2024.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Turkish Airlines, 8:00 PM – 8:30 AM(+2), $1142, 1 stop (real-time)",
      "answer_length": 66,
      "question_length": 141,
      "actions": [
        "find",
        "filter_sort",
        "plan"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Google Flights--14",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 14,
      "question": "Compare flight options and find the lowest round trip fare from New York to London departing on January 10, 2024, and returning on January 17, 2024.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Norse Atlantic UK, 6:10 PM – 6:00 AM(+1), $546 (real-time)",
      "answer_length": 58,
      "question_length": 148,
      "actions": [
        "find",
        "filter_sort",
        "compare",
        "plan"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 9
    },
    {
      "id": "Google Flights--15",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 15,
      "question": "Compare the prices and total duration of non-stop flights from New York to Tokyo Narita Airport departing on February 12th, 2024, and returning on February 26th, 2024.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Only one flight, United flight, 11:15 AM – 3:35 PM(+1), $1316 (real-time)",
      "answer_length": 73,
      "question_length": 167,
      "actions": [
        "compare"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Google Flights--16",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 16,
      "question": "Find the cheapest one-way flight from New York to Tokyo departing on January 15, 2024, and provide the airline and total flight duration.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Norse Atlantic UK, Air China, 6:10 PM – 1:40 PM(+2), $671, 2 stops (real-time)",
      "answer_length": 78,
      "question_length": 137,
      "actions": [
        "find",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Google Flights--17",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 17,
      "question": "Find the cheapest round-trip flight from New York to Paris leaving on December 27, 2023, and returning on January 10, 2024.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Scandinavian Airlines, 5:35 PM – 1:25 PM(+1), $608, 2 stops (real-time)",
      "answer_length": 71,
      "question_length": 123,
      "actions": [
        "find",
        "filter_sort",
        "plan"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Google Flights--18",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 18,
      "question": "Compare flight options from New York to Tokyo for a round trip leaving on January 25, 2024, and returning on February 15, 2024, for one adult. Prioritize the comparisons by the shortest travel time.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "United, 11:15 AM – 3:35 PM(+1), duration 14 hr 20 min, $1316 (real-time)",
      "answer_length": 72,
      "question_length": 198,
      "actions": [
        "compare",
        "plan"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Google Flights--19",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 19,
      "question": "Find the cheapest one-way flight from London to Paris, departing on January 25, 2024. Include the airline, total travel time, and layovers for the chosen flight.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "easyJet, 6:35 PM - 8:55 PM, $35, nonstop (real-time)",
      "answer_length": 52,
      "question_length": 161,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Google Flights--20",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 20,
      "question": "Book a round-trip flight from San Francisco to Berlin, departing on March 5, 2024, and returning on March 12, 2024, and find the option with the shortest total travel time.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Lufthansa United, 2:40 PM – 12:55 PM(+1), 13 hr 15 min",
      "answer_length": 54,
      "question_length": 172,
      "actions": [
        "find",
        "book_buy",
        "plan"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 4,
      "requires_state": true,
      "requires_navigation": true,
      "complexity": 10
    },
    {
      "id": "Google Flights--21",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 21,
      "question": "Locate the lowest-priced one-way flight from Tokyo to Sydney for an adult, departing on February 25, 2024, and include the flight duration and number of layovers.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Jetstar JAL, Qantas, 8:10 PM – 10:40 AM(+1), 12 hr 30 min, 1 stop",
      "answer_length": 65,
      "question_length": 162,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Google Flights--22",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 22,
      "question": "Find a round-trip flight from Rio de Janeiro to Los Angeles, leaving on March 15, 2024, and returning on March 22, 2024, and select the option with the least carbon dioxide emissions.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Gol, Aeromexico, 7:00 AM – 10:22 PM, 746 kg CO2",
      "answer_length": 47,
      "question_length": 183,
      "actions": [
        "find",
        "plan",
        "use_tool"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 9
    },
    {
      "id": "Google Flights--23",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 23,
      "question": "Search for a one-way flight from Mumbai to Vancouver on February 28, 2024, filtering the results to show only 1-stop flights.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Air Canada Lufthansa, 4:25 AM – 4:15 PM; Air India, Air Canada, 6:35 AM – 4:15 PM; ...(1 stop)",
      "answer_length": 94,
      "question_length": 125,
      "actions": [
        "find",
        "search",
        "answer"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Google Flights--24",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 24,
      "question": "Compare prices for economy class round-trip flights from Dubai to Rome, departing on March 1, 2024, and returning on March 8, 2024, and select the option with the fewest stops.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Etihad ITA, 2:25 AM – 5:45 AM, 6 hr 20 min, Nonstop",
      "answer_length": 51,
      "question_length": 176,
      "actions": [
        "compare",
        "plan",
        "use_tool"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 9
    },
    {
      "id": "Google Flights--25",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 25,
      "question": "Find a one-way business class flight from Buenos Aires to Amsterdam on March 10, 2024, and provide the details of the flight with the shortest duration.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "KLM, 4:25 PM – 9:40 AM(+1), 13 hr 15 min, EZE–AMS, Nonstop, $3912, 3251 kg CO2",
      "answer_length": 78,
      "question_length": 152,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Google Flights--26",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 26,
      "question": "Search for the cheapest round-trip flights from Bangkok to Madrid, leaving on February 26, 2024, and returning on February 28, 2024, and provide options under $1000.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Royal Jordanian, 2:20 AM – 2:05 PM",
      "answer_length": 34,
      "question_length": 165,
      "actions": [
        "find",
        "search",
        "answer",
        "filter_sort",
        "plan"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 7,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 10
    },
    {
      "id": "Google Flights--27",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 27,
      "question": "Locate a one-way flight from Johannesburg to Toronto on March 30, 2024, for one adult, and analyze the price trends for the following month.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "British Airways, American, 7:45 PM – 6:28 PM(+1), <analyze the price graph>",
      "answer_length": 75,
      "question_length": 140,
      "actions": [
        "find"
      ],
      "domains": [
        "shopping",
        "travel"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Google Flights--28",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 28,
      "question": "Find the best-priced round-trip flight from Seattle to Paris, departing on February 27, 2024, and returning on March 1, 2024, with a maximum of one stop.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Icelandair, 2:35 PM – 12:00 PM(+1), 1 stop, $1602",
      "answer_length": 49,
      "question_length": 153,
      "actions": [
        "find",
        "filter_sort",
        "plan"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Google Flights--29",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 29,
      "question": "Compare the prices and total travel time of non-stop flights from Mexico City to Frankfurt, departing on March 5, 2024, and returning on March 15, 2024.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Only one flight, Lufthansa, 9:00 PM – 2:40 PM(+1), 10 hr 40 min",
      "answer_length": 63,
      "question_length": 152,
      "actions": [
        "compare"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Google Flights--30",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 30,
      "question": "Find the most affordable one-way flight from Cape Town to Singapore, departing on March 20, 2024, and include the airline and total number of layovers.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Ethiopian, 2:35 PM – 2:50 PM(+1), 1 stop, $633",
      "answer_length": 46,
      "question_length": 151,
      "actions": [
        "find"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Google Flights--31",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 31,
      "question": "Find a one-way economy flight from Auckland to Honolulu on March 25, 2024, browse the full page and display a flight option with the most stops.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Qantas, Qatar Airways, AlaskaEmirates, Mar 25, 4:05 PM – 11:59 PM(+1), most: 3 stops",
      "answer_length": 84,
      "question_length": 144,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 6
    },
    {
      "id": "Google Flights--32",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 32,
      "question": "Search for round-trip flights from Stockholm to Toronto, departing on March 3, 2024, and returning on March 10, 2024, and sort the results to find the shortest total travel time.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Icelandair, 12:50 PM – 6:15 PM, 11 hr 25 min",
      "answer_length": 44,
      "question_length": 178,
      "actions": [
        "find",
        "search",
        "filter_sort",
        "plan"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 10
    },
    {
      "id": "Google Flights--33",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 33,
      "question": "Find a one-way flight from Shanghai to Vancouver on February 27, 2024, and compare the options based on carbon dioxide emissions.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Korean Air, 2:00 PM – 11:15 AM, 13 hr 15 min, 816 kg CO2; EVA AirAir Canada, 8:10 PM – 6:35 PM, 3,672 kg CO2; ...",
      "answer_length": 113,
      "question_length": 129,
      "actions": [
        "find",
        "compare"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Google Flights--34",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 34,
      "question": "Compare business class flight options from Lisbon to Singapore for a one-way trip on March 15, 2024, select one of the flights and see which websites offer its booking options. Which one is the cheapest.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Emirates, 8:45 PM – 9:15 PM(+1), booking options: Emirates, Gotogate, Martigo, Expedia, kiss&fly, eDreams ... cheapest: Gotogate",
      "answer_length": 128,
      "question_length": 203,
      "actions": [
        "filter_sort",
        "compare",
        "plan",
        "use_tool"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 9
    },
    {
      "id": "Google Flights--35",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 35,
      "question": "Find the lowest-priced one-way flight from Cairo to Montreal on February 21, 2024, including the total travel time and number of stops.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "EgyptAir, Lufthansa, Air Canada, 10:05 AM – 6:20 PM, 15 hr 15 min, 1 stop, $644",
      "answer_length": 79,
      "question_length": 135,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Google Flights--36",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 36,
      "question": "Search for round-trip flights from Helsinki to New Delhi, departing on March 28, 2024, and returning on April 4, 2024, and filter the results to show only flights under $1000.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Finnair, 6:00 PM – 6:05 AM(+1), $744 ...",
      "answer_length": 40,
      "question_length": 175,
      "actions": [
        "find",
        "search",
        "answer",
        "filter_sort",
        "plan"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 6,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 10
    },
    {
      "id": "Google Flights--37",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 37,
      "question": "Locate a round-trip flight from Buenos Aires to Beijing, leaving on February 28, 2024, and returning on March 3, 2024, check out one of the options and tell me if the airline for my return flight is the same as my departure flight.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Lufthansa, 5:50 PM – 9:30 AM(+2), return flight can be Lufthansa, 11:20 AM – 7:55 AM(+1), the same as departure flight",
      "answer_length": 118,
      "question_length": 231,
      "actions": [
        "find",
        "answer",
        "plan"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Google Flights--38",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 38,
      "question": "Compare the prices and flight durations for economy class flights from Oslo to Dubai, departing on March 8, 2024, and show the options with no more than two layovers.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Emirates, 2:10 PM – 11:55 PM, Nonstop ...",
      "answer_length": 41,
      "question_length": 166,
      "actions": [
        "answer",
        "filter_sort",
        "compare"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Google Flights--39",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 39,
      "question": "Find a one-way flight from Prague to a city in Japan on March 20, 2024, which city in Japan is cheaper to go to, Tokyo or a certain city in Hokkaido?",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Prague to Tokyo, British Airways, Air China, 7:05 AM – 1:40 PM(+1)",
      "answer_length": 66,
      "question_length": 149,
      "actions": [
        "find"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 5
    },
    {
      "id": "Google Flights--40",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 40,
      "question": "Browse destinations on the Google Flights homepage from Seattle, look at destinations on a map, and recommend some famous places to travel that are within a reasonable distance and price.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "Seattle to Las Vegas $21, Seattle to Los Angeles $42",
      "answer_length": 52,
      "question_length": 187,
      "actions": [
        "search",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "local_maps"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 6
    },
    {
      "id": "Google Flights--41",
      "site": "Google Flights",
      "slug": "google_flights",
      "index": 41,
      "question": "Choose one way business class ticket from Hong Kong to Glacier National Park on 8 March 2024, offering a 1 stop ticket.",
      "local_url": "http://localhost:40007/",
      "upstream_url": "https://www.google.com/travel/flights/",
      "original_web": "https://www.google.com/travel/flights/",
      "answer_type": "possible",
      "answer": "United, Operated by Skywest DBA United Express, 10:30 PM – 12:45 PM(+1), 1 stop",
      "answer_length": 79,
      "question_length": 119,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Google Map--0",
      "site": "Google Map",
      "slug": "google_map",
      "index": 0,
      "question": "Find 5 beauty salons with ratings greater than 4.8 in Seattle, WA.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Beehive Salon, Intermezzo Salon & Spa, Cindy's Beauty Salon, The Red Chair Salon, Ella and Oz Salon",
      "answer_length": 99,
      "question_length": 66,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Google Map--1",
      "site": "Google Map",
      "slug": "google_map",
      "index": 1,
      "question": "Tell me one bus stop that is nearest to the intersection of main street and Amherst street in Altavista.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "golden",
      "answer": "'Amherst and 7th' or 'Main Street Middle'",
      "answer_length": 41,
      "question_length": 104,
      "actions": [
        "answer",
        "plan"
      ],
      "domains": [
        "local_maps"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Google Map--2",
      "site": "Google Map",
      "slug": "google_map",
      "index": 2,
      "question": "Find Apple Stores close to zip code 90028",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Apple The Grove, Apple Beverly Center",
      "answer_length": 37,
      "question_length": 41,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Google Map--3",
      "site": "Google Map",
      "slug": "google_map",
      "index": 3,
      "question": "The least amount of walking from Central Park Zoo to the Broadway Theater in New York.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Approximately 20 min",
      "answer_length": 20,
      "question_length": 86,
      "actions": [
        "answer"
      ],
      "domains": [
        "local_maps"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Google Map--4",
      "site": "Google Map",
      "slug": "google_map",
      "index": 4,
      "question": "Plan a trip from Boston Logan Airport to North Station.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Drive via MA-1A S and take about 10 mins (based on real-time traffic conditions)",
      "answer_length": 80,
      "question_length": 55,
      "actions": [
        "plan"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Map--5",
      "site": "Google Map",
      "slug": "google_map",
      "index": 5,
      "question": "Search for a parking garage near Thalia Hall in Chicago that isn't open 24 hours.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "SP+ Parking in 1750 W 13th St, Chicago, IL 60608",
      "answer_length": 48,
      "question_length": 81,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "local_maps"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 5
    },
    {
      "id": "Google Map--6",
      "site": "Google Map",
      "slug": "google_map",
      "index": 6,
      "question": "Find all Uniqlo locations in Chicago, IL.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "UNIQLO State Street",
      "answer_length": 19,
      "question_length": 41,
      "actions": [
        "find"
      ],
      "domains": [
        "local_maps"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Map--7",
      "site": "Google Map",
      "slug": "google_map",
      "index": 7,
      "question": "Find bus stops in Alanson, MI",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "golden",
      "answer": "Alanson, MI (EZ-Mart) Bus Stop",
      "answer_length": 30,
      "question_length": 29,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Map--8",
      "site": "Google Map",
      "slug": "google_map",
      "index": 8,
      "question": "Find a place to climb within 2 miles of zip code 90028.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "golden",
      "answer": "Hollywood Boulders",
      "answer_length": 18,
      "question_length": 55,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Google Map--9",
      "site": "Google Map",
      "slug": "google_map",
      "index": 9,
      "question": "Find the art gallery that is nearest to Los Angeles Hindu Temple.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "golden",
      "answer": "'Honor Fraser Gallery' or 'Walter Maciel Gallery'.",
      "answer_length": 50,
      "question_length": 65,
      "actions": [
        "find",
        "plan"
      ],
      "domains": [
        "local_maps"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Google Map--10",
      "site": "Google Map",
      "slug": "google_map",
      "index": 10,
      "question": "Search for a park in the state of California called Castle Mountains National Monument and find out it's Basic Information.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "located in Barstow, CA 92311; open 24 hours; phone number is (760) 252-6100",
      "answer_length": 75,
      "question_length": 123,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Google Map--11",
      "site": "Google Map",
      "slug": "google_map",
      "index": 11,
      "question": "Locate a large store in Washington that has kids' and maternity products, also check if it has a parking lot.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Village Maternity with a wheelchair accessible parking lot",
      "answer_length": 58,
      "question_length": 109,
      "actions": [
        "find"
      ],
      "domains": [
        "local_maps"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Map--12",
      "site": "Google Map",
      "slug": "google_map",
      "index": 12,
      "question": "Find 5 places that serve burgers near 44012 zip code and sort these 5 places by highest rating.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Taki's Greek Kitchen - 4.7, Thai Chili - 4.7, Parker's Grille & Tavern - 4.5, Legacy Restaurant & Grille - 4.5, Jake's On the Lake - 4.5",
      "answer_length": 136,
      "question_length": 95,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "local_maps"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 8
    },
    {
      "id": "Google Map--13",
      "site": "Google Map",
      "slug": "google_map",
      "index": 13,
      "question": "Find a parking lot in Gloucester and book a ride from there to North Plymouth, view the map to understand the route better.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Drive via MA-3 N and I-93 N, about 1.5 hours (based on real-time traffic conditions).",
      "answer_length": 85,
      "question_length": 123,
      "actions": [
        "find",
        "book_buy",
        "plan"
      ],
      "domains": [
        "local_maps"
      ],
      "constraint_count": 0,
      "requires_state": true,
      "requires_navigation": true,
      "complexity": 7
    },
    {
      "id": "Google Map--14",
      "site": "Google Map",
      "slug": "google_map",
      "index": 14,
      "question": "Find motorcycle parking near Radio City Music Hall.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Rising Wolf Garage (should be motorcycle parking)",
      "answer_length": 49,
      "question_length": 51,
      "actions": [
        "find"
      ],
      "domains": [
        "local_maps"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Map--15",
      "site": "Google Map",
      "slug": "google_map",
      "index": 15,
      "question": "Find daytime only parking nearest to Madison Square Garden. Summarize what people are saying about it. ",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Quik Park; <reviews>",
      "answer_length": 20,
      "question_length": 103,
      "actions": [
        "find",
        "plan"
      ],
      "domains": [
        "local_maps"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Google Map--16",
      "site": "Google Map",
      "slug": "google_map",
      "index": 16,
      "question": "Find EV charging supported parking closest to Smithsonian museum.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "EVgo Charging Station",
      "answer_length": 21,
      "question_length": 65,
      "actions": [
        "find",
        "plan"
      ],
      "domains": [
        "local_maps"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Google Map--17",
      "site": "Google Map",
      "slug": "google_map",
      "index": 17,
      "question": "Search for locksmiths open now but not open 24 hours in Texas City.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Protech Key and Locksmith (UTC 12:30)",
      "answer_length": 37,
      "question_length": 67,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 5
    },
    {
      "id": "Google Map--18",
      "site": "Google Map",
      "slug": "google_map",
      "index": 18,
      "question": "Find a route between Chicago to Los Angeles, then print the route details.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Drive via I-80 W, about 29 hours",
      "answer_length": 32,
      "question_length": 74,
      "actions": [
        "find",
        "filter_sort",
        "plan"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Google Map--19",
      "site": "Google Map",
      "slug": "google_map",
      "index": 19,
      "question": "I will arrive Pittsburgh Airport soon. Provide the name of the Hilton hotel closest to the airport. Then, tell me the the walking time to the nearest supermarket from the hotel.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Hilton Garden Inn Pittsburgh Airport, walking time around 15min - 30min",
      "answer_length": 71,
      "question_length": 177,
      "actions": [
        "answer",
        "plan"
      ],
      "domains": [
        "travel",
        "local_maps"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Google Map--20",
      "site": "Google Map",
      "slug": "google_map",
      "index": 20,
      "question": "Find Tesla Destination Charger closest to the National Air and Space Museum.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Tesla Destination Charger, 1330 Maryland Ave SW, Washington, DC 20024",
      "answer_length": 69,
      "question_length": 76,
      "actions": [
        "find",
        "plan"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Google Map--21",
      "site": "Google Map",
      "slug": "google_map",
      "index": 21,
      "question": "Identify the nearest bus stop to the corner of Elm Street and Oak Street in Massachusetts.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "golden",
      "answer": "Elm Street & Oak Street, 18 Bay St, Amesbury, MA 01913",
      "answer_length": 54,
      "question_length": 90,
      "actions": [
        "plan"
      ],
      "domains": [
        "local_maps"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Google Map--22",
      "site": "Google Map",
      "slug": "google_map",
      "index": 22,
      "question": "Find a Best Buy store near zip code 33139.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Best Buy, 1131 5th St, Miami Beach, FL 33139",
      "answer_length": 44,
      "question_length": 42,
      "actions": [
        "find"
      ],
      "domains": [
        "shopping",
        "local_maps"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Google Map--23",
      "site": "Google Map",
      "slug": "google_map",
      "index": 23,
      "question": "Determine the shortest walking route from The Metropolitan Museum of Art to Times Square in New York.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "around 42 min (1.9 miles) via 7th Ave",
      "answer_length": 37,
      "question_length": 101,
      "actions": [
        "plan"
      ],
      "domains": [
        "local_maps"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Map--24",
      "site": "Google Map",
      "slug": "google_map",
      "index": 24,
      "question": "Plan a journey from San Francisco International Airport to Union Square via driving.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "via US-101 N, around 19 min (current traffic condition), 14.6 miles",
      "answer_length": 67,
      "question_length": 84,
      "actions": [
        "plan"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Map--25",
      "site": "Google Map",
      "slug": "google_map",
      "index": 25,
      "question": "Search for a parking facility near the Fox Theater in Detroit that closes at night.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Park Rite Parking, Closes 11 PM",
      "answer_length": 31,
      "question_length": 83,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "local_maps"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Google Map--26",
      "site": "Google Map",
      "slug": "google_map",
      "index": 26,
      "question": "Search for Los Angeles on Google Map, try to print the map as PDF and summarize the information on the map.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "golden",
      "answer": "<Action>, print PDF",
      "answer_length": 19,
      "question_length": 107,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "local_maps"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Google Map--27",
      "site": "Google Map",
      "slug": "google_map",
      "index": 27,
      "question": "Locate the Target stores in Atlanta, GA. How many results are shown on the map.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "8",
      "answer_length": 1,
      "question_length": 79,
      "actions": [
        "find"
      ],
      "domains": [
        "local_maps"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Map--28",
      "site": "Google Map",
      "slug": "google_map",
      "index": 28,
      "question": "Find the search settings for Google Map, what options are shown on that page?",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "golden",
      "answer": "Privacy & Safety: Activity, Content, More options; Other settings",
      "answer_length": 65,
      "question_length": 77,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "local_maps"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Google Map--29",
      "site": "Google Map",
      "slug": "google_map",
      "index": 29,
      "question": "Identify bus stops in Ypsilanti, MI, list three of them.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Ypsilanti Transit Center; Ellsworth + Michigan; YTC - Stop 5",
      "answer_length": 60,
      "question_length": 56,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Map--30",
      "site": "Google Map",
      "slug": "google_map",
      "index": 30,
      "question": "Locate a parking lot near the Brooklyn Bridge that open 24 hours. Review the user comments about it.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "2-68 Division St Garage, <reviews>",
      "answer_length": 34,
      "question_length": 100,
      "actions": [
        "find"
      ],
      "domains": [
        "shopping",
        "local_maps"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 4
    },
    {
      "id": "Google Map--31",
      "site": "Google Map",
      "slug": "google_map",
      "index": 31,
      "question": "First search New York's Central Park Zoo on Google Map, and then find the way to share the map. What is the generated sharing link?",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "golden",
      "answer": "share link, https://maps.app.goo.gl/Bnp4Q67dTHoFZ4Lx8",
      "answer_length": 53,
      "question_length": 131,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "local_maps"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Google Map--32",
      "site": "Google Map",
      "slug": "google_map",
      "index": 32,
      "question": "Search for plumbers available now but not open 24 hours in Orlando, FL.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Drain Genie Plumbing Services",
      "answer_length": 29,
      "question_length": 71,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 5
    },
    {
      "id": "Google Map--33",
      "site": "Google Map",
      "slug": "google_map",
      "index": 33,
      "question": "Check out Denver International Airport's information and tell me: 1) which level has the least proportion in reviews; 2) what are its Accessibility and Amenities.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "golden",
      "answer": "star 2 has the least proportion; Accessibility: Assistive hearing loop; Wheelchair accessible entrance; Wheelchair accessible parking lot; Wheelchair accessible restroom; Wheelchair accessible seating; Amenities: Baggage storage; Wi-Fi; Free Wi-Fi",
      "answer_length": 247,
      "question_length": 162,
      "actions": [
        "answer"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Google Map--34",
      "site": "Google Map",
      "slug": "google_map",
      "index": 34,
      "question": "Find a hiking trail within 2 miles of zip code 80202.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Speer Blvd Park ...",
      "answer_length": 19,
      "question_length": 53,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Google Map--35",
      "site": "Google Map",
      "slug": "google_map",
      "index": 35,
      "question": "Search for a natural reserve in Texas called Big Bend National Park and gather its Basic Information.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Big Bend National Park, TX; (432) 477-2251; 6PXX+WW Big Bend National Park, Texas; Tickets: $30 ...",
      "answer_length": 99,
      "question_length": 101,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Google Map--36",
      "site": "Google Map",
      "slug": "google_map",
      "index": 36,
      "question": "Identify 5 restaurants serving pizza near the 30309 zip code and rank them by their ratings.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Varasano's Pizzeria - Buckhead, 4.9; DaVinci's Pizzeria, 4.4; Mellow Mushroom Atlanta - Buckhead, 4.4; Vinny's N.Y. Pizza & Grill - Piedmont, 4.2; Gino's NY Pizza Bar, 4.0",
      "answer_length": 171,
      "question_length": 92,
      "actions": [
        "answer"
      ],
      "domains": [
        "local_maps"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Google Map--37",
      "site": "Google Map",
      "slug": "google_map",
      "index": 37,
      "question": "Locate a parking area in Salem and find a route from there to Marblehead, including map directions for better understanding.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Take Lafayette St and Pleasant St to Cross St in Marblehead, 14 min (3.9 mi); Drive to Rowland St, 1 min (0.1 mi)",
      "answer_length": 113,
      "question_length": 124,
      "actions": [
        "find",
        "plan"
      ],
      "domains": [
        "local_maps"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Google Map--38",
      "site": "Google Map",
      "slug": "google_map",
      "index": 38,
      "question": "Search for bicycle parking near the Empire State Building.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Bike Parking, 104 W 38th St, New York, NY 10018",
      "answer_length": 47,
      "question_length": 58,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "local_maps"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Google Map--39",
      "site": "Google Map",
      "slug": "google_map",
      "index": 39,
      "question": "Find a route from Miami to New Orleans, and provide the detailed route information.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Miami, Florida to New Orleans, Louisiana; Get on I-95 N from S Miami Ave, 5 min (1.4 mi); Follow Florida's Tpke, I-75 N and I-10 W to Carondelet St in New Orleans. Take exit 12B from US-90 BUS W, 12 hr 6 min (864 mi); Turn left onto Carondelet St, 3 min (0.6 mi)",
      "answer_length": 262,
      "question_length": 83,
      "actions": [
        "find",
        "answer",
        "plan"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Google Map--40",
      "site": "Google Map",
      "slug": "google_map",
      "index": 40,
      "question": "Find a restaurant in Boston that eats Boston lobster and asks for a rating of 4.6 or higher, and check out what a one-star review says.",
      "local_url": "http://localhost:40008/",
      "upstream_url": "https://www.google.com/maps/",
      "original_web": "https://www.google.com/maps/",
      "answer_type": "possible",
      "answer": "Boston Sail Loft, 4.6; one star review: Not sure about the rest of the seafood here since I left immediately after trying their AWFUL Chowder. I won't call it clam chowder since I didn't see a single piece of clam. This stuff was more like if you heated up half & Half then sprinkle dill and salt in it. It's too bad the tourist think this is how it's supposed to taste.",
      "answer_length": 370,
      "question_length": 135,
      "actions": [
        "find",
        "filter_sort",
        "save_state"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 2,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Google Search--0",
      "site": "Google Search",
      "slug": "google_search",
      "index": 0,
      "question": "Find the initial release date for Guardians of the Galaxy Vol. 3 the movie.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "golden",
      "answer": "May 5, 2023",
      "answer_length": 11,
      "question_length": 75,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Google Search--1",
      "site": "Google Search",
      "slug": "google_search",
      "index": 1,
      "question": "Find Kevin Durant's bio",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "Born on September 29, 1988; Professional basketball player for the Phoenix Suns now.",
      "answer_length": 84,
      "question_length": 23,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Search--2",
      "site": "Google Search",
      "slug": "google_search",
      "index": 2,
      "question": "Search for the latest news title about the NBA team the Los Angeles Lakers.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "News Title (real-time)",
      "answer_length": 22,
      "question_length": 75,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Google Search--3",
      "site": "Google Search",
      "slug": "google_search",
      "index": 3,
      "question": "Show me a list of comedy movies, sorted by user ratings. Show me the Top 5 movies.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "golden",
      "answer": "Life Is Beautiful, Back to the Future, The Intouchables, City Lights, Modern Times",
      "answer_length": 82,
      "question_length": 82,
      "actions": [
        "answer",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Google Search--4",
      "site": "Google Search",
      "slug": "google_search",
      "index": 4,
      "question": "Show most played games in Steam. And tell me the number of players in In game at this time",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "Counter-Strike 2, 602,898 players (real-time)",
      "answer_length": 45,
      "question_length": 90,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Search--5",
      "site": "Google Search",
      "slug": "google_search",
      "index": 5,
      "question": "find the score of the latest nba game played by the phoenix suns.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "Suns 120-107 Trail Blazers (real-time)",
      "answer_length": 38,
      "question_length": 65,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Search--6",
      "site": "Google Search",
      "slug": "google_search",
      "index": 6,
      "question": "Browse the monthly trending searches in Columbus.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "New Year's Eve parties, Christmas markets, january, comedy shows... (real-time)",
      "answer_length": 79,
      "question_length": 49,
      "actions": [
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 3
    },
    {
      "id": "Google Search--7",
      "site": "Google Search",
      "slug": "google_search",
      "index": 7,
      "question": "Find the software requirements for iPhones that support AirDrop's ability to continue transmitting over the web when out of range.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "golden",
      "answer": "IOS 17.1",
      "answer_length": 8,
      "question_length": 130,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Search--8",
      "site": "Google Search",
      "slug": "google_search",
      "index": 8,
      "question": "Find the video on YouTube: 'Oscars 2023: Must-See Moments!'. Tell me who the first comment displayed under that video belongs to, and how many thumbs up and replies it has.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "user: @melvinsmiley5295, 329 thumbs up and 2 replies (real-time)",
      "answer_length": 64,
      "question_length": 172,
      "actions": [
        "find",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Google Search--9",
      "site": "Google Search",
      "slug": "google_search",
      "index": 9,
      "question": "Show the rating of Prometheus movie on IMDb and Rotten Tomatoes.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "IMDb 7.0/10, Rotten Tomatoes 73%",
      "answer_length": 32,
      "question_length": 64,
      "actions": [
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Google Search--10",
      "site": "Google Search",
      "slug": "google_search",
      "index": 10,
      "question": "Find the no. 1 weekly charts ranked artist based on Billboard and tell me 10 most played song by this artist until now.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "Taylor Swift, 10 songs (different sources have different results)",
      "answer_length": 65,
      "question_length": 119,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Google Search--11",
      "site": "Google Search",
      "slug": "google_search",
      "index": 11,
      "question": "According to FlightAware, tell me the busiest airport last week and its total arrivals and departures last week.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "KATL, 13555 total arrivals and departures (real-time)",
      "answer_length": 53,
      "question_length": 112,
      "actions": [
        "answer"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Search--12",
      "site": "Google Search",
      "slug": "google_search",
      "index": 12,
      "question": "Find the year that Tom Brady had the most touchdowns in a single seasson.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "golden",
      "answer": "2007",
      "answer_length": 4,
      "question_length": 73,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Search--13",
      "site": "Google Search",
      "slug": "google_search",
      "index": 13,
      "question": "What are Jerry Trainor's upcoming projects?",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "Strange Planet, 2023",
      "answer_length": 20,
      "question_length": 43,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Google Search--14",
      "site": "Google Search",
      "slug": "google_search",
      "index": 14,
      "question": "Find the retired players the year before last named James Smith and tell me which club he has been a member of from 2020–2021.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "golden",
      "answer": "Yeovil Town",
      "answer_length": 11,
      "question_length": 126,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Google Search--15",
      "site": "Google Search",
      "slug": "google_search",
      "index": 15,
      "question": "Please try to log in to twitter with email: webagenttest@testmail.com and password: test123456. Let me know if the login was successful.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "golden",
      "answer": "Not successful",
      "answer_length": 14,
      "question_length": 136,
      "actions": [
        "save_state"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Google Search--16",
      "site": "Google Search",
      "slug": "google_search",
      "index": 16,
      "question": "How many members are there in the OpenAI community on Reddit, and what is the hottest news right now?",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "880K, ChatGPT will soon have real-time news access (real-time)",
      "answer_length": 62,
      "question_length": 101,
      "actions": [
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Google Search--17",
      "site": "Google Search",
      "slug": "google_search",
      "index": 17,
      "question": "Tell me the names of Trump's kids",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "golden",
      "answer": "Ivanka Trump, Barron Trump, Donald Trump Jr., Tiffany Trump, Eric Trump",
      "answer_length": 71,
      "question_length": 33,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Search--18",
      "site": "Google Search",
      "slug": "google_search",
      "index": 18,
      "question": "When and where the most recent World Cup was held, and which team was the winner?",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "golden",
      "answer": "Qatar; November 20 to December 18, 2022; Argentina",
      "answer_length": 50,
      "question_length": 81,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Google Search--19",
      "site": "Google Search",
      "slug": "google_search",
      "index": 19,
      "question": "What are the first 7 bits of the SHA of the Bert's latest commit on GitHub, and what exactly was changed in that commit.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "golden",
      "answer": "eedf571, Smaller BERT Models",
      "answer_length": 28,
      "question_length": 120,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Search--20",
      "site": "Google Search",
      "slug": "google_search",
      "index": 20,
      "question": "Find the release date for the latest \"Fast & Furious\" movie.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "golden",
      "answer": "April 4, 2025",
      "answer_length": 13,
      "question_length": 60,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Google Search--21",
      "site": "Google Search",
      "slug": "google_search",
      "index": 21,
      "question": "Show a list of the top 5 highest-grossing animated movies, sorted by box office earnings.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "golden",
      "answer": "The Lion King (2019); Frozen II (2019); The Super Mario Bros. Movie (2023); Frozen (2013); Incredibles 2 (2018)",
      "answer_length": 111,
      "question_length": 89,
      "actions": [
        "answer",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Google Search--22",
      "site": "Google Search",
      "slug": "google_search",
      "index": 22,
      "question": "Browse and list the top three trending topics this month in New York City.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "trending topics: 1.valentines day events; 2.fashion week; 3.job fairs; 4.march; 5.february",
      "answer_length": 90,
      "question_length": 74,
      "actions": [
        "search",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 6
    },
    {
      "id": "Google Search--23",
      "site": "Google Search",
      "slug": "google_search",
      "index": 23,
      "question": "Retrieve a short biography of LeBron James.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "<bio> LeBron James",
      "answer_length": 18,
      "question_length": 43,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Search--24",
      "site": "Google Search",
      "slug": "google_search",
      "index": 24,
      "question": "What is the name of the star system closest to the Solar System, and what are the discovered planets in it?",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "golden",
      "answer": "Alpha Centauri star system; Proxima Centauri b, Proxima Centauri c, and Proxima Centauri d",
      "answer_length": 90,
      "question_length": 107,
      "actions": [
        "save_state",
        "plan"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Google Search--25",
      "site": "Google Search",
      "slug": "google_search",
      "index": 25,
      "question": "Get the latest news headline about the English Premier League football club Manchester United.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "eg, Manchester United 1-2 Fulham: Alex Iwobi scores in added time for huge away win",
      "answer_length": 83,
      "question_length": 94,
      "actions": [
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Google Search--26",
      "site": "Google Search",
      "slug": "google_search",
      "index": 26,
      "question": "Identify the hardware requirements for using the latest version of Adobe Photoshop on a Mac.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "RAM 8 GB; Processor: Multicore Intel® or Apple Silicon processor (2 GHz or faster processor with SSE 4.2 or later) with 64-bit support; Operating system, macOS Big Sur (version 11.0) or later; Graphics card, GPU with Metal support, 1.5 GB of GPU memory ...",
      "answer_length": 256,
      "question_length": 92,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Google Search--27",
      "site": "Google Search",
      "slug": "google_search",
      "index": 27,
      "question": "Check the current air quality index in Paris.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "Current PM2.5 AQI\t43",
      "answer_length": 20,
      "question_length": 45,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Google Search--28",
      "site": "Google Search",
      "slug": "google_search",
      "index": 28,
      "question": "Check the IMDb and Metacritic scores of the movie \"Inception.\"",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "golden",
      "answer": "IMDb score 8.8, Metacritic score 74%.",
      "answer_length": 37,
      "question_length": 62,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Google Search--29",
      "site": "Google Search",
      "slug": "google_search",
      "index": 29,
      "question": "Find out the current world record for the men's 100m sprint.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "golden",
      "answer": "9.58s held by Usain Bolt of Jamaica",
      "answer_length": 35,
      "question_length": 60,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Search--30",
      "site": "Google Search",
      "slug": "google_search",
      "index": 30,
      "question": "Find the current number one artist on the Spotify Global Top 50 chart and list his/her top 10 songs as of now.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "real-time, Benson Boone; Beautiful Things, In The Stars, GHOST TOWN, To Love Someone, Before You, NIGHTS LIKE THESE, Sugar Sweet, ROOM FOR 2, Little Runaway, What Was",
      "answer_length": 166,
      "question_length": 110,
      "actions": [
        "find",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Google Search--31",
      "site": "Google Search",
      "slug": "google_search",
      "index": 31,
      "question": "Discover which year Cristiano Ronaldo scored the most goals in a single season.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "golden",
      "answer": "2014-15 season",
      "answer_length": 14,
      "question_length": 79,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Search--32",
      "site": "Google Search",
      "slug": "google_search",
      "index": 32,
      "question": "Find out where and when the most recent UEFA Champions League final was held, and which team won.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "Manchester City Football Club; June 10, 2023; Atatürk Olympic Stadium, Istanbul, Turkey",
      "answer_length": 87,
      "question_length": 97,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Search--33",
      "site": "Google Search",
      "slug": "google_search",
      "index": 33,
      "question": "Find and copy the SHA of the latest commit in the TensorFlow repository on GitHub, then find a textbox to paste and tell me what the SHA is.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "<SHA> of latest Tensorflow",
      "answer_length": 26,
      "question_length": 140,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Google Search--34",
      "site": "Google Search",
      "slug": "google_search",
      "index": 34,
      "question": "Determine the distance from Earth to Mars as of today's date.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "345,957,886 kilometers",
      "answer_length": 22,
      "question_length": 61,
      "actions": [
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Search--35",
      "site": "Google Search",
      "slug": "google_search",
      "index": 35,
      "question": "Look up the latest research paper related to black holes published in the journal \"Nature Astronomy\".",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "eg, 19 February 2024, The accretion of a solar mass per day by a 17-billion solar mass black hole",
      "answer_length": 97,
      "question_length": 101,
      "actions": [
        "find"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Google Search--36",
      "site": "Google Search",
      "slug": "google_search",
      "index": 36,
      "question": "Search for the most recent Nobel Prize winner in Physics and their contribution to the field.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "French-Swedish physicist Anne L'Huillier, French scientist Pierre Agostini, and Hungarian-born Frank Krausz. <summary>",
      "answer_length": 118,
      "question_length": 93,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Google Search--37",
      "site": "Google Search",
      "slug": "google_search",
      "index": 37,
      "question": "Find the current top 3 super-earth planets and give a brief introduction to them.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "Gliese 667Cc, Kepler-22b, Kepler-69c",
      "answer_length": 36,
      "question_length": 81,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Google Search--38",
      "site": "Google Search",
      "slug": "google_search",
      "index": 38,
      "question": "Search for the next visible solar eclipse in North America and its expected date, and what about the one after that.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "next: April 8, 2024. The one after that will take place on August 23, 2044.",
      "answer_length": 75,
      "question_length": 116,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Google Search--39",
      "site": "Google Search",
      "slug": "google_search",
      "index": 39,
      "question": "Identify the top-10 trending travel destination for 2024 through a blog, how many of them are in Asian.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "Tokyo, Japan; Seoul, South Korea; Halong Bay, Vietnam; Palawan Island, Philippines; Sapa, Vietnam; Bogota, Colombia; Pattaya, Thailand; Alajuela, Costa Rica; Phnom Penh, Cambodia; Kuala Lumpur, Malaysia. Asian: Tokyo, Japan; Seoul, South Korea; Halong Bay, Vietnam; Palawan Island, Philippines; Sapa, Vietnam; Kuala Lumpur, Malaysia; Phnom Penh, Cambodia",
      "answer_length": 354,
      "question_length": 103,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "travel"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Google Search--40",
      "site": "Google Search",
      "slug": "google_search",
      "index": 40,
      "question": "Look up the elevation of Mount Kilimanjaro on Google Search.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "golden",
      "answer": "19,341 feet (5,895 meters)",
      "answer_length": 26,
      "question_length": 60,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Google Search--41",
      "site": "Google Search",
      "slug": "google_search",
      "index": 41,
      "question": "Look up the current statistics of air pollution level in Los Angeles using Google Search.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "current air pollution level in Los Angeles",
      "answer_length": 42,
      "question_length": 89,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Google Search--42",
      "site": "Google Search",
      "slug": "google_search",
      "index": 42,
      "question": " Use Google Search to find an article that explains the major differences between American English and British English.",
      "local_url": "http://localhost:40009/",
      "upstream_url": "https://www.google.com/",
      "original_web": "https://www.google.com/",
      "answer_type": "possible",
      "answer": "The main difference between British English and American English is in pronunciation. Some words are also different in each variety of English, and there are also a few differences in the way they use grammar. Here are five of the most common grammatical differences between British and American English. 1. Present perfect and past simple; 2. got and gotten; 3. Verb forms with collective nouns; 4. have and take; 5. shall",
      "answer_length": 423,
      "question_length": 119,
      "actions": [
        "find",
        "search",
        "filter_sort",
        "use_tool"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Huggingface--0",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 0,
      "question": "Find a pre-trained natural language processing model on Hugging Face that can perform sentiment analysis, and make sure the model's last update is within March 2023.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "distilroberta-finetuned-financial-news-sentiment-analysis",
      "answer_length": 57,
      "question_length": 165,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Huggingface--1",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 1,
      "question": "Use the Huggingface Inference API to generate a short story about a dragon and a wizard.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "<story> (generated by Inference API)",
      "answer_length": 36,
      "question_length": 88,
      "actions": [
        "use_tool"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Huggingface--2",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 2,
      "question": "Discover three new and popular open-source NLP models for language translation released in the past month on Huggingface.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "<model 1>; <model 2>; <model 3>; (last month, recently created)",
      "answer_length": 63,
      "question_length": 121,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 5
    },
    {
      "id": "Huggingface--3",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 3,
      "question": "Look up a model with a license of cc-by-sa-4.0 with the most likes on Hugging face.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "replit/replit-code-v1-3b",
      "answer_length": 24,
      "question_length": 83,
      "actions": [
        "find"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Huggingface--4",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 4,
      "question": "Locate an open-source conversational AI model on Hugging Face, trained in English and list its main features and applications.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "TinyLlama/TinyLlama-1.1B-Chat-v1.0; TinyLlama can be plugged and played in many open-source projects built upon Llama. Besides, TinyLlama is compact with only 1.1B parameters; Applications: cater to a multitude of applications demanding a restricted computation and memory footprint.",
      "answer_length": 283,
      "question_length": 126,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 4
    },
    {
      "id": "Huggingface--5",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 5,
      "question": "Find a model released on Hugging Face for recipe generation. Retrieve the information of the model, including its name, model size and tensor type.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "flax-community/t5-recipe-generation; 223M params; F32",
      "answer_length": 53,
      "question_length": 147,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Huggingface--6",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 6,
      "question": "Find the model sentence-transformers/all-MiniLM-L6-v2 and use the Inference API on the webpage to get the similarity of the following two sentences: 'Tomorrow is Sunday', 'Eat a burger on Sunday'.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "golden",
      "answer": "0.550",
      "answer_length": 5,
      "question_length": 196,
      "actions": [
        "find",
        "use_tool"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Huggingface--7",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 7,
      "question": "Which is the most downloaded audio related dataset on Hugging face currently.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "golden",
      "answer": "autumnjohnson/ceti_audio",
      "answer_length": 24,
      "question_length": 77,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Huggingface--8",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 8,
      "question": "Retrieve an example of a pre-trained language model in natural language processing and identify the tasks it is specifically designed for, like translation or text summarization.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "microsoft/phi-2; Text generation",
      "answer_length": 32,
      "question_length": 178,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Huggingface--9",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 9,
      "question": "Find the most download machine translation model on Huggingface which focuses on English and Japanese (en-ja) and report the evaluation metrics stated for it.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "golden",
      "answer": "Helsinki-NLP/opus-mt-ja-en; BLEU 41.7\t; chr-F 0.589",
      "answer_length": 51,
      "question_length": 158,
      "actions": [
        "find"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Huggingface--10",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 10,
      "question": "Open space: argilla/notux-chat-ui and interact with it by asking it 'which team trained you'. What is its answer.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "golden",
      "answer": "Mistral AI team",
      "answer_length": 15,
      "question_length": 113,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 3
    },
    {
      "id": "Huggingface--11",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 11,
      "question": "Identify the latest updated image to video model available on Huggingface and summarize its main features.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "motexture/VSeq2VSeq; Text to video diffusion model with variable length frame conditioning for infinite length video generation.",
      "answer_length": 128,
      "question_length": 106,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Huggingface--12",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 12,
      "question": "Find the most recently updated machine learning model on Huggingface which focuses on Error Correction.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "Jaagup/errors_corrections_min3",
      "answer_length": 30,
      "question_length": 103,
      "actions": [
        "find"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Huggingface--13",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 13,
      "question": "Search for LLaMA in the huggingface doc, what type is the spaces_between_special_tokens parameter in LlamaTokenizer and what is its default value.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "golden",
      "answer": "bool, defaults to False",
      "answer_length": 23,
      "question_length": 146,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Huggingface--14",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 14,
      "question": "How much is the Pro account of Hugging face for a month and what are the features?",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "golden",
      "answer": "$9/month; Pro Account: Get a PRO badge on your profile, Early access to new features, Unlock Inference for PROs, Higher tier for AutoTrain",
      "answer_length": 138,
      "question_length": 82,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Huggingface--15",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 15,
      "question": "Identify the most downloaded models on Hugging face that use the PaddlePaddle library.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "junnyu/roformer_chinese_base",
      "answer_length": 28,
      "question_length": 86,
      "actions": [
        "save_state",
        "use_tool"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Huggingface--16",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 16,
      "question": "Find information on the latest (as of today's date) pre-trained language model on Huggingface suitable for text classification and briefly describe its intended use case and architecture.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "<model> (today, text classification)",
      "answer_length": 36,
      "question_length": 187,
      "actions": [
        "find",
        "use_tool"
      ],
      "domains": [
        "research",
        "knowledge"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Huggingface--17",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 17,
      "question": "Find the most recently updated open-source project related to natural language processing on the Huggingface platform. Provide the project's name, creator, and a brief description of its functionality.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "<model>; <creator>; <description> (recent, NLP)",
      "answer_length": 47,
      "question_length": 201,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 6
    },
    {
      "id": "Huggingface--18",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 18,
      "question": "Look up TRL's forward modelling in the hugging face documentation on how to add a margin to a loss.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "golden",
      "answer": "As in the Llama 2 paper, you can add a margin to the loss by adding a margin column to the dataset. The reward collator will automatically pass it through and the loss will be computed accordingly.",
      "answer_length": 197,
      "question_length": 99,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 3
    },
    {
      "id": "Huggingface--19",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 19,
      "question": "Explore and summarize the features of the most recent open-source NLP model released by Hugging Face for English text summarization.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "<model> (Most recent, English text summarization)",
      "answer_length": 49,
      "question_length": 132,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 3
    },
    {
      "id": "Huggingface--20",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 20,
      "question": "Locate a pre-trained natural language processing model on Hugging Face that specializes in named entity recognition (NER), confirm that the model was last updated in 2022 and has 1M+ downloads.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "golden",
      "answer": "ckiplab/bert-base-chinese-ner",
      "answer_length": 29,
      "question_length": 193,
      "actions": [
        "find"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Huggingface--21",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 21,
      "question": "Look up the tour about how to use the 'pipeline' feature in the Hugging Face Transformers library for sentiment analysis, and identify the default model it uses.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "golden",
      "answer": "from transformers import pipeline \\n classifier = pipeline(\"sentiment-analysis\") \\n classifier(\"We are very happy to show you the 🤗 Transformers library.\") ... distilbert/distilbert-base-uncased-finetuned-sst-2-english",
      "answer_length": 218,
      "question_length": 161,
      "actions": [
        "find",
        "save_state",
        "use_tool"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Huggingface--22",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 22,
      "question": "Identify the steps to convert a PyTorch model to TensorFlow using the Hugging Face Transformers library as described in their documentation.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "<summary> of https://huggingface.co/docs/transformers/main/en/add_tensorflow_model#4-model-implementation",
      "answer_length": 105,
      "question_length": 140,
      "actions": [
        "save_state",
        "compute"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Huggingface--23",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 23,
      "question": "Identify three innovative and widely recognized open-source NLP models for automatic speech recognition released in the past month on Huggingface.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "eg, openai/whisper-large-v3",
      "answer_length": 27,
      "question_length": 146,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 3
    },
    {
      "id": "Huggingface--24",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 24,
      "question": "Search for a model on Hugging Face with an Apache-2.0 license that has received the highest number of likes.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "golden",
      "answer": "mistralai/Mixtral-8x7B-Instruct-v0.1",
      "answer_length": 36,
      "question_length": 108,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Huggingface--25",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 25,
      "question": "In the Hugging Face documentation, find the tutorial on loading adapters with PEFT, tell me how to load in 8bit or 4bit.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "golden",
      "answer": "Add the load_in_8bit or load_in_4bit parameters to from_pretrained() and set device_map=\"auto\" to effectively distribute the model to your hardware. (Or use code)",
      "answer_length": 162,
      "question_length": 120,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Huggingface--26",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 26,
      "question": "Identify a model on Hugging Face designed for generating travel chats. Obtain information about the model, including its name, size and training framwork.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "PhilipTheGreat/DiabloGPT-small-Traveller, GPT2LMHeadModel, 510 MB",
      "answer_length": 65,
      "question_length": 154,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Huggingface--27",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 27,
      "question": "Determine the most downloaded dataset related to Text Retrieval in NLP on Hugging Face.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "golden",
      "answer": "nlphuji/mscoco_2014_5k_test_image_text_retrieval",
      "answer_length": 48,
      "question_length": 87,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Huggingface--28",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 28,
      "question": "Retrieve an example of a pre-trained model on Hugging Face that is optimized for question answering tasks and detail the languages it supports.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "eg, /roberta-base-squad2, language: English",
      "answer_length": 43,
      "question_length": 143,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Huggingface--29",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 29,
      "question": "Summarize the description of the recent open-source NLP model released on Hugging Face for medical summarization.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "<summary> of Falconsai/medical_summarization (T5 Large for Medical Text Summarization)",
      "answer_length": 86,
      "question_length": 113,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 3
    },
    {
      "id": "Huggingface--30",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 30,
      "question": "Identify the most downloaded English-Chinese (en-zh) machine translation model on Huggingface and report its latest performance metrics and usage guidelines.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "golden",
      "answer": "Helsinki-NLP/opus-mt-en-zh; testset, BLEU, chr-F: Tatoeba-test.eng.zho, 31.4, 0.268",
      "answer_length": 83,
      "question_length": 157,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Huggingface--31",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 31,
      "question": "Identify the latest machine learning model on Huggingface that specializes in detecting fake news, including the date of its last update.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "eg, Hawat/make-believe-fakenews-detection, Updated Jan 16 2024",
      "answer_length": 62,
      "question_length": 137,
      "actions": [
        "answer"
      ],
      "domains": [
        "research",
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Huggingface--32",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 32,
      "question": "On the Hugging Face website, search for the model 'GPT-J-6B' and find the 'temperature' parameter in its settings. What is the default value of this parameter?",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "golden",
      "answer": "\"temperature\": 1.0",
      "answer_length": 18,
      "question_length": 159,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Huggingface--33",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 33,
      "question": "List three hugging face docs. How many GitHub stars have they earned so far?",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "eg, Transformers - 119,672 stars, Diffusers - 20,775 stars, Datasets - 17,960 stars.",
      "answer_length": 84,
      "question_length": 76,
      "actions": [
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Huggingface--34",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 34,
      "question": "List the benefits of hugging face classroom mentioned on Hugging face website.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "Empower your students with state-of-the-art resources; Give your students unlimited access to modern machine learning tools; Easily manage your classroom ...",
      "answer_length": 157,
      "question_length": 78,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Huggingface--35",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 35,
      "question": "Find the latest Diffusion-related blog on Hugging Face, and read its intro or overview section to roughly summarize the content of the blog.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "eg, Accelerating SD Turbo and SDXL Turbo Inference with ONNX Runtime and Olive, Published January 15, 2024, <summary>",
      "answer_length": 117,
      "question_length": 140,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Huggingface--36",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 36,
      "question": "Summarize all the payment plans and their advantages in huggingface pricing.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "summary of https://huggingface.co/pricing",
      "answer_length": 41,
      "question_length": 76,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Huggingface--37",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 37,
      "question": "Browse the daily paper on Hugging Face. What is the title of the first article, how many upvotes has it received, and is there any related model or data release?",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "huggingface posts, https://huggingface.co/posts",
      "answer_length": 47,
      "question_length": 161,
      "actions": [
        "search"
      ],
      "domains": [
        "research",
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 3
    },
    {
      "id": "Huggingface--38",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 38,
      "question": "Investigate the 'transformers' library in the Hugging Face documentation, focusing on how to add new tokens to a tokenizer.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "golden",
      "answer": "use add_tokens method",
      "answer_length": 21,
      "question_length": 123,
      "actions": [
        "save_state"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": true,
      "requires_navigation": true,
      "complexity": 5
    },
    {
      "id": "Huggingface--39",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 39,
      "question": "Investigate in the Hugging Face documentation how to utilize the 'Trainer' API for training a model on a custom dataset, and note the configurable parameters of the Trainer class.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "Trainer example, https://huggingface.co/docs/evaluate/main/en/transformers_integrations#trainer",
      "answer_length": 95,
      "question_length": 179,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Huggingface--40",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 40,
      "question": "Check out Text Embeddings Inference in Hugging face's Doc to summarise the strengths of the toolkit.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "possible",
      "answer": "Streamlined Deployment; Efficient Resource Utilization; Dynamic Batching ...",
      "answer_length": 76,
      "question_length": 100,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Huggingface--41",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 41,
      "question": "What is the current Text-to-3D model with the highest number of downloads and tell me are there Spaces that use the model.",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "golden",
      "answer": "openai/shap-e; there are Spaces like hysts/Shap-E ...",
      "answer_length": 53,
      "question_length": 122,
      "actions": [
        "answer",
        "filter_sort",
        "use_tool"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Huggingface--42",
      "site": "Huggingface",
      "slug": "huggingface",
      "index": 42,
      "question": "Check the Dataset Viewer for ai2lumos/lumos_complex_qa_plan_onetime on Hugging face. what is the content corresponding to user in the first message?",
      "local_url": "http://localhost:40010/",
      "upstream_url": "https://huggingface.co/",
      "original_web": "https://huggingface.co/",
      "answer_type": "golden",
      "answer": "content: Please provide a reasonable subgoal-based plan to solve the given task.\\nTask: What was the opening date of the museum dedicated to the war that, after it occurred, Boston became one of the wealthiest international ports?; Initial Environment Description: None.",
      "answer_length": 270,
      "question_length": 148,
      "actions": [
        "answer"
      ],
      "domains": [
        "research"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Wolfram Alpha--0",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 0,
      "question": "derivative of x^2 when x=5.6",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "11.2",
      "answer_length": 4,
      "question_length": 28,
      "actions": [
        "compute"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Wolfram Alpha--1",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 1,
      "question": "Give a constraint on the set of inequalities for the inner region of the pentagram.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "possible",
      "answer": "2 a + 3 sqrt(5) x + 5 x>=sqrt(2 (5 + sqrt(5))) y AND 2 a + sqrt(50 + 22 sqrt(5)) y>=(5 + sqrt(5)) x AND sqrt(5) a + 2 sqrt(5) x + 2 sqrt(5 + 2 sqrt(5)) y <= a ... (Search inner region of the pentagram on Wolfram)",
      "answer_length": 212,
      "question_length": 83,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Wolfram Alpha--2",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 2,
      "question": "Calculate 3^71 and retain 5 significant figures in scientific notation.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "7.5095 * 10^33",
      "answer_length": 14,
      "question_length": 71,
      "actions": [
        "compute"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Wolfram Alpha--3",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 3,
      "question": "Let g(x) be the integral of x^2 cos(2x). Write the expression of g(x).",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "1/4 (2 x cos(2 x) + (-1 + 2 x^2) sin(2 x)) + Constant",
      "answer_length": 53,
      "question_length": 70,
      "actions": [
        "compute"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Wolfram Alpha--4",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 4,
      "question": "Pack 24 circles in a circle radius r. Compare Densest known packing and Square packing. Then tell me the radius of the inner circles.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "Densest known packing: 0.176939r; Square packing: 0.163961r",
      "answer_length": 59,
      "question_length": 133,
      "actions": [
        "answer",
        "compare"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Wolfram Alpha--5",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 5,
      "question": "Show the solution of y\"(z) + sin(y(z)) = 0 from wolframalpha.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "y(z) = ± 2 am(1/2 sqrt((c_1 + 2) (z + c_2)^2), 4/(c_1 + 2)), am(x, m) is the Jacobi amplitude function",
      "answer_length": 102,
      "question_length": 61,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Wolfram Alpha--6",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 6,
      "question": "Simplify x^5-20x^4+163x^3-676x^2+1424x-1209 so that it has fewer items.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "7 + 3 (-4 + x)^3 + (-4 + x)^5",
      "answer_length": 29,
      "question_length": 71,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Wolfram Alpha--7",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 7,
      "question": "Give the final angle and final length after 6s of a Spring pendulum with spring equilibrium length=0.12m, initial length=0.24m, initial angle=80deg, mass=1kg, spring constant=120 N/m .",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "-73.26° from vertical; 0.252 m",
      "answer_length": 30,
      "question_length": 184,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Wolfram Alpha--8",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 8,
      "question": "Give 12 lbs of 4-cyanoindole, converted to molar and indicate the percentage of C, H, N.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "possible",
      "answer": "approximately: 38.3 mol; 76.0% C; 4.3% H; 19.7% N",
      "answer_length": 49,
      "question_length": 88,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Wolfram Alpha--9",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 9,
      "question": "Annual energy production of Diablo Canyon 2 in 2010.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "9752 GW h/yr (gigawatt hours per year)",
      "answer_length": 38,
      "question_length": 52,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Wolfram Alpha--10",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 10,
      "question": "Give the geomagnetic field on June 20, 2023 in Oslo.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "geomagnetic field, total 51.5 uT;",
      "answer_length": 33,
      "question_length": 52,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Wolfram Alpha--11",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 11,
      "question": "Show the electrical resistivity of UNS A92024 and UNS G10800 at 20 degrees Celsius.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "UNS A92024: 4.9×10^-6 Ω cm (ohm centimeters) (at 20 °C); UNS G10800: 1.8×10^-5 Ω cm (ohm centimeters)",
      "answer_length": 101,
      "question_length": 83,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Wolfram Alpha--12",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 12,
      "question": "Which character in unicode 8900 to 8920 looks like a snowflake",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "8902 (U+22C6)",
      "answer_length": 13,
      "question_length": 62,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Wolfram Alpha--13",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 13,
      "question": "What is 10,000 US dollars worth now in 1980 and in 1970?",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "possible",
      "answer": "approximately: 36430; 77325",
      "answer_length": 27,
      "question_length": 56,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Wolfram Alpha--14",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 14,
      "question": "Compare the total Calories: whopper vs baconator vs big mac. Assume that each serving of food is 300g.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "possible",
      "answer": "approximately: Whopper, 657 Cal; Baconator, 902 Cal; Big Mac, 730 Cal",
      "answer_length": 69,
      "question_length": 102,
      "actions": [
        "compare"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Wolfram Alpha--15",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 15,
      "question": "Show the blood relationship fraction between you and your father's mother's sister's son.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "3.125%",
      "answer_length": 6,
      "question_length": 89,
      "actions": [
        "answer",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Wolfram Alpha--16",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 16,
      "question": "Weight lose for a male with current weight 90 kg, 40 year old, 175 cm. If he intakes 1500 calories every day, how long will it take to lose 17 kg.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "possible",
      "answer": "intake 1500 Cal/d for 3 months 12 days to lose 17 kg with a sedentary activity level",
      "answer_length": 84,
      "question_length": 146,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Wolfram Alpha--17",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 17,
      "question": "Show the average price of movie ticket in Providence, Nashville, Boise in 2023.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "Providence $13.81; Nashville $12.65; Boise $12.65",
      "answer_length": 49,
      "question_length": 79,
      "actions": [
        "answer"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Wolfram Alpha--18",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 18,
      "question": "Plot Albert Einstein curve with Parametric equations.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "possible",
      "answer": "show a Albert Einstein curve with parametric equations",
      "answer_length": 54,
      "question_length": 53,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Wolfram Alpha--19",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 19,
      "question": "Standing in the sun from 11:00 am with SPF 5 in Australia. Approximate time to sunburn for each skin type.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "possible",
      "answer": "<sunborn time> (real-time date)",
      "answer_length": 31,
      "question_length": 106,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Wolfram Alpha--20",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 20,
      "question": "Compute the integral of 3e^(2x) from x=0 to x=5.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "approximately 33038",
      "answer_length": 19,
      "question_length": 48,
      "actions": [
        "compute"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Wolfram Alpha--21",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 21,
      "question": "Calculate (1+0.1*i)^8 + (1−0.2*i)^8  where i is a complex number.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "approximately 0.717183 - 0.425258 i",
      "answer_length": 35,
      "question_length": 65,
      "actions": [
        "compute"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 6,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Wolfram Alpha--22",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 22,
      "question": "Determine the area of a regular hexagon with a side length of 7 cm.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "127.306 cm^2 or 147 \\sqrt(3) / 2",
      "answer_length": 32,
      "question_length": 67,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Wolfram Alpha--23",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 23,
      "question": "Calculate the population growth rate of Canada from 2020 to 2023 using Wolfram Alpha.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "mean population growth rate of Canada from 2020 to 2023 is 0.9998% per year",
      "answer_length": 75,
      "question_length": 85,
      "actions": [
        "compute"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Wolfram Alpha--24",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 24,
      "question": "Solve the differential equation y''(t) - 2y'(t) + 10y(t) = 0 and display its general solution.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "y(t) = c1 e^t sin(3t) + c2 e^t cos(3t)",
      "answer_length": 38,
      "question_length": 94,
      "actions": [
        "compute"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Wolfram Alpha--25",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 25,
      "question": "Calculate the final position and velocity of a projectile launched at 45 degrees with an initial speed of 30 m/s after 3 seconds.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "if g=9.81; x = 63.64m, y = 19.49m; Vx = 21.21 m/s, Vy = -8.22 m/s",
      "answer_length": 65,
      "question_length": 129,
      "actions": [
        "compute"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Wolfram Alpha--26",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 26,
      "question": "Convert 15 kilograms of sulfuric acid to moles and display the percentage composition of H, S, and O by weight.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "possible",
      "answer": "if no H2O, 153 moles, hydrogen (H), 32.69% for sulfur (S), and 65.25% for oxygen (O).",
      "answer_length": 85,
      "question_length": 111,
      "actions": [
        "compute"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Wolfram Alpha--27",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 27,
      "question": "Display the thermal conductivity of Copper (Cu) and Aluminum (Al) at 25 degrees Celsius.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "401.2 W/(m K); 236.9 W/(m K)",
      "answer_length": 28,
      "question_length": 88,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Wolfram Alpha--28",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 28,
      "question": "Identify the character in Unicode range 9632 to 9650 that represents a hollow parallelogram.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "9649 or U+25B1",
      "answer_length": 14,
      "question_length": 92,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Wolfram Alpha--29",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 29,
      "question": "Create a plot of cat curve using wolfram alpha.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "possible",
      "answer": "any cat curve",
      "answer_length": 13,
      "question_length": 47,
      "actions": [
        "save_state"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": true,
      "requires_navigation": true,
      "complexity": 5
    },
    {
      "id": "Wolfram Alpha--30",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 30,
      "question": "Calculate the estimated time to sunburn for different skin types when exposed to the sun at 1:00 pm with SPF 1 in Brazil.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "possible",
      "answer": "real-time, search query: sunburn 1:00 pm with SPF 1 in Brazil",
      "answer_length": 61,
      "question_length": 121,
      "actions": [
        "compute"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Wolfram Alpha--31",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 31,
      "question": "Using Wolfram Alpha, determine the current temperature and wind speed in Chicago, IL.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "possible",
      "answer": "real-time, search query: current temperature and wind speed in Chicago, IL.",
      "answer_length": 75,
      "question_length": 85,
      "actions": [
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Wolfram Alpha--32",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 32,
      "question": "Print all prime numbers between 1000 and 1200 using Wolfram alpha.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "1009, 1013, 1019, 1021, 1031, 1033, 1039, 1049, 1051, 1061, 1063, 1069, 1087, 1091, 1093, 1097, 1103, 1109, 1117, 1123, 1129, 1151, 1153, 1163, 1171, 1181, 1187, 1193.",
      "answer_length": 167,
      "question_length": 66,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Wolfram Alpha--33",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 33,
      "question": "Identify the electrical energy output of a hydroelectric power plant named Itaipu Dam in 2023 using Wolfram Alpha.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "89.5 TWh (terawatt hours)",
      "answer_length": 25,
      "question_length": 114,
      "actions": [
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Wolfram Alpha--34",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 34,
      "question": "Calculate the mass of Jupiter compared to Earth using Wolfram Alpha. Also, find the length of one day on Jupiter.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "317.8 times that of Earth, and the length of one day on Jupiter is approximately 9.925 hours",
      "answer_length": 92,
      "question_length": 113,
      "actions": [
        "find",
        "compute"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Wolfram Alpha--35",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 35,
      "question": "Calculate the determinant of a 6x6 Hilbert matrix.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "1/186313420339200000",
      "answer_length": 20,
      "question_length": 50,
      "actions": [
        "compute"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Wolfram Alpha--36",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 36,
      "question": "Determine the convergence or divergence of the series Σ (n=1 to ∞) of 1/(n^3 + 1).",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "converges",
      "answer_length": 9,
      "question_length": 82,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Wolfram Alpha--37",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 37,
      "question": "How many days are there between February 12, 2024 and August 9, 2050?",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "9675",
      "answer_length": 4,
      "question_length": 69,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Wolfram Alpha--38",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 38,
      "question": "Compute the length of a curve defined by y = 2x^3 - 3x^2 + 4x - 5 from x = 0 to x = 3.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "around 39.2",
      "answer_length": 11,
      "question_length": 86,
      "actions": [
        "compute"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Wolfram Alpha--39",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 39,
      "question": "Use Wolfram alpha to write the expression of the ellipse x^2 + 3 y^2 = 4 rotated 33 degrees counterclockwise.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "x^2(\\sin(\frac{2π}{15}) - 2) + 2xy \\cos(\frac{2π}{15}) + 4 = y^2(2 + \\sin(\frac{2π}{15}))",
      "answer_length": 86,
      "question_length": 109,
      "actions": [
        "use_tool"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 5,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Wolfram Alpha--40",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 40,
      "question": "Approximate amount of fat burned by a 28yo, 172cm tall, 70kg woman running for 30min at a pace of 6min/mile.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "around 0.078 kg",
      "answer_length": 15,
      "question_length": 108,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Wolfram Alpha--41",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 41,
      "question": "What is the approximate Heart Rate Reserve of a 50 year old man who has a heart rate of 60bpm at rest.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "110 bpm",
      "answer_length": 7,
      "question_length": 102,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Wolfram Alpha--42",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 42,
      "question": "What is the raw memory of a 100.2\" * 123.5\" true colour picture at 72 ppi?",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "192 MB",
      "answer_length": 6,
      "question_length": 74,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Wolfram Alpha--43",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 43,
      "question": "A polyominoes of order 6 means you have 6 identical squares to combine different shapes (2-sided). How many combinations are there? Looking at all the shapes in the result, how many of them have only 2 rows in total?",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "35; 12",
      "answer_length": 6,
      "question_length": 216,
      "actions": [
        "book_buy"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 4,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Wolfram Alpha--44",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 44,
      "question": "Solve the ODE, g' + cos(g) = 0, if there is a constant in the result, determine the value of the constant by the condition that g(0) = 1.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "possible",
      "answer": "g(x) = 2 cos^(-1)((sinh(x) (cos(1/2) - sin(1/2)) + cosh(x) (cos(1/2) - sin(1/2)) + sin(1/2) + cos(1/2))/(sqrt(2) sqrt(-(sin(1) - 1) sinh(2 x) - (sin(1) - 1) cosh(2 x) + 1 + sin(1)))) OR ...",
      "answer_length": 189,
      "question_length": 137,
      "actions": [
        "compute"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Wolfram Alpha--45",
      "site": "Wolfram Alpha",
      "slug": "wolfram_alpha",
      "index": 45,
      "question": "A 175cm tall, 85kg, 40yo man climbs 2500 steps at about 18cm per step and 40 steps per minute. summarise the Metabolic properties.",
      "local_url": "http://localhost:40011/",
      "upstream_url": "https://www.wolframalpha.com/",
      "original_web": "https://www.wolframalpha.com/",
      "answer_type": "golden",
      "answer": "energy expenditure | 2720 kJ (kilojoules); average energy expenditure per step | 1.1 kJ/step (kilojoules per step); fat burned | 0.0842 kg (kilograms); oxygen consumption | 129.9 L (liters); metabolic equivalent | 7 metabolic equivalents",
      "answer_length": 237,
      "question_length": 130,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Cambridge Dictionary--0",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 0,
      "question": "Look up the pronunciation and definition of the word \"sustainability\" on the Cambridge Dictionary.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "golden",
      "answer": "UK: /səˌsteɪ.nəˈbɪl.ə.ti/, US: /səˌsteɪ.nəˈbɪl.ə.t̬i/; the quality of being able to continue over a period of time",
      "answer_length": 114,
      "question_length": 98,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--1",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 1,
      "question": "Find the pronunciation, definition, and a sample sentence for the word 'serendipity'.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "UK: /ˌser.ənˈdɪp.ə.ti/, US: /ˌser.ənˈdɪp.ə.t̬i/; the fact of finding interesting or valuable things by chance; There is a real element of serendipity in archaeology.",
      "answer_length": 165,
      "question_length": 85,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--2",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 2,
      "question": "Look up the pronunciation, definition, and example sentence for the word \"ubiquitous\" in UK and US English.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "UK: /juːˈbɪk.wɪ.təs/, US: /juːˈbɪk.wə.t̬əs/; seeming to be everywhere; Leather is very much in fashion this season, as is the ubiquitous denim.",
      "answer_length": 143,
      "question_length": 107,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--3",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 3,
      "question": "Look up the definition, pronunciation, and examples of the word \"zeitgeist.\"",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "UK: /ˈtsaɪt.ɡaɪst/ or /ˈzaɪt.ɡaɪst/, US: /ˈtsaɪt.ɡaɪst/ or /ˈzaɪt.ɡaɪst/; the general set of ideas, beliefs, feelings, etc. that is typical of a particular period in history; Our methods of working, then, were facilitated and in some ways strongly encouraged by the technologies available to us, the products of a zeitgeist of convergence.",
      "answer_length": 339,
      "question_length": 76,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--4",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 4,
      "question": "Look for the British English pronunciation of the word \"innovate\" and write down the International Phonetic Alphabet (IPA) notation, then find one example sentence provided in the Cambridge Dictionary that uses this word.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "UK: /ˈɪn.ə.veɪt/; Above all, this proposal aims to correct the allocative inefficiencies of the existing patent system, while preserving the dynamic incentives to innovate.",
      "answer_length": 172,
      "question_length": 221,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--5",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 5,
      "question": "Learn the UK and US pronunciation of the word \"procrastination\", and find one example sentence that reflects its use in context.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "UK: /prəˌkræs.tɪˈneɪ.ʃən/, US: /proʊˌkræs.tɪˈneɪ.ʃən/; Vacillation and procrastination, out of fears of recession or otherwise, would run grave risks.",
      "answer_length": 150,
      "question_length": 128,
      "actions": [
        "find",
        "use_tool"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Cambridge Dictionary--6",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 6,
      "question": "Search for the word \"sustainability\" on the Cambridge Dictionary, what is the translation of sustainability into Chinese and French in the dictionary.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "golden",
      "answer": "可持续性; durabilité , viabilité",
      "answer_length": 28,
      "question_length": 150,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Cambridge Dictionary--7",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 7,
      "question": "Look up the meaning, pronunciation, and an example sentence of the word \"gestalt\" using the Cambridge Dictionary.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "UK: /ɡəˈʃtælt/, US: /ɡəˈʃtɑːlt/; something such as a structure or experience that, when considered as a whole, has qualities that are more than the total of all its parts; In the comic and cartoon mythoses, however, most gestalts have one default transformation.",
      "answer_length": 262,
      "question_length": 113,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--8",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 8,
      "question": "Find three different meanings of \"dog\" in Cambridge Dictionary.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "a common animal with four legs, especially kept by people as a pet or to hunt or guard things; a man who is unpleasant or not to be trusted; to follow someone closely and continuously",
      "answer_length": 183,
      "question_length": 63,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--9",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 9,
      "question": "Look up the British pronunciation of the word \"euphoria\" and find an example sentence using that word on the Cambridge Dictionary.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "UK: /juːˈfɔː.ri.ə/; They were in a state of euphoria for days after they won the prize.",
      "answer_length": 87,
      "question_length": 130,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--10",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 10,
      "question": "Look up the definition and pronunciation of the word \"impeccable\" and also find an example sentence using that word.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "UK: /ɪmˈpek.ə.bəl/, US: /ɪmˈpek.ə.bəl/; perfect, with no problems or bad parts; His English is impeccable.",
      "answer_length": 106,
      "question_length": 116,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--11",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 11,
      "question": "Look up the pronunciation and definition of the word \"ameliorate,\" and provide an example sentence using the word.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "UK: /əˈmiːl.jə.reɪt/, US: /əˈmiːl.jə.reɪt/; to make a bad or unpleasant situation better; Foreign aid is badly needed to ameliorate the effects of the drought.",
      "answer_length": 159,
      "question_length": 114,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Cambridge Dictionary--12",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 12,
      "question": "Find the pronunciation, definition, and a sample sentence for the word \"resilience\" in the Cambridge Dictionary.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "UK: /rɪˈzɪl.jəns/, US: /rɪˈzɪl.jəns/; the ability to be happy, successful, etc. again after something difficult or bad has happened; Trauma researchers emphasize the resilience of the human psyche.",
      "answer_length": 197,
      "question_length": 112,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--13",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 13,
      "question": "Find one word, one phase and one idiom related to euphoria in Cambridge Dictionary.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "beatitude; bed of roses; for fun",
      "answer_length": 32,
      "question_length": 83,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--14",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 14,
      "question": "Use the Cambridge Dictionary to find the pronunciation, definition, and one example sentence for the word \"concatenate\".",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "UK: /kənˈkæt.ə.neɪt/, US: /kənˈkæt̬.ə.neɪt/; to put things together as a connected series; The filename is a series of concatenated words with no spaces.",
      "answer_length": 153,
      "question_length": 120,
      "actions": [
        "find",
        "use_tool"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Cambridge Dictionary--15",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 15,
      "question": "Find the pronunciation and a sample sentence for the word \"pandemic.\"",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "UK: /pænˈdem.ɪk/, US: /pænˈdem.ɪk/; In some parts of the world malaria is still pandemic.",
      "answer_length": 89,
      "question_length": 69,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--16",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 16,
      "question": "Look up the definition of \"cryptocurrency\" on Cambridge Dictionary, provide the pronunciation, and use it in two example sentences that illustrate different contexts.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "UK: /ˈkrɪp.təʊˌkʌr.ən.si/, US: /ˈkrɪp.toʊˌkɝː.ən.si/; It is one of several prominent efforts to enable complex financial functions in a cryptocurrency; Vice versa, a cryptocurrency can be a legal tender, in which case it is not a virtual currency.",
      "answer_length": 247,
      "question_length": 166,
      "actions": [
        "find",
        "answer",
        "use_tool"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Cambridge Dictionary--17",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 17,
      "question": "How many meanings of \"unblemished\" are given in Cambridge Dictionary? Please browse the page and give the number directly.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "golden",
      "answer": "2",
      "answer_length": 1,
      "question_length": 122,
      "actions": [
        "search"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 3
    },
    {
      "id": "Cambridge Dictionary--18",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 18,
      "question": "Search for \"to behave well\" in Cambridge Dictionary's Thesaurus and see which synonyms the dictionary gives.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "golden",
      "answer": "behaves themselves; be on their best behaviour",
      "answer_length": 46,
      "question_length": 108,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Cambridge Dictionary--19",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 19,
      "question": "Try a Cambridge Dictionary translation and tell me which company provided the translation.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "golden",
      "answer": "Microsoft",
      "answer_length": 9,
      "question_length": 90,
      "actions": [
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--20",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 20,
      "question": "Look up the definition, pronunciation (both UK and US), and find one example sentence for the word \"altruism\" in the Cambridge Dictionary.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "UK: /ˈæl.tru.ɪ.zəm/, US: /ˈæl.tru.ɪ.zəm/; Def: willingness to do things that bring advantages to others, even if it results in disadvantage for yourself; She's not known for her altruism.",
      "answer_length": 187,
      "question_length": 138,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--21",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 21,
      "question": "Search for the word \"ephemeral\" on Cambridge Dictionary and find its translation into Spanish.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "golden",
      "answer": "efímero",
      "answer_length": 7,
      "question_length": 94,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Cambridge Dictionary--22",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 22,
      "question": "Use the Cambridge Dictionary to find the definition, UK pronunciation, and an example sentence for the word \"quintessential.\"",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "UK: /ˌkwɪn.tɪˈsen.ʃəl/, US:/ˌkwɪn.tɪˈsen.ʃəl/; Def: being the most typical example or most important part of something; Sheep's milk cheese is the quintessential Corsican cheese.",
      "answer_length": 178,
      "question_length": 125,
      "actions": [
        "find",
        "use_tool"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Cambridge Dictionary--23",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 23,
      "question": "Find the US English pronunciation of the word \"meticulous\" using the Cambridge Dictionary and note the International Phonetic Alphabet (IPA) notation, then find one example sentence provided in the dictionary using this word.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "US: /məˈtɪk.jə.ləs/; Many hours of meticulous preparation have gone into writing the book.",
      "answer_length": 90,
      "question_length": 225,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--24",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 24,
      "question": "Look up the definition and both UK and US pronunciation of the word \"reverie,\" and provide an example sentence using the word from Cambridge Dictionary.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "UK: /ˈrev.ər.i/, US:/ˈrev.ɚ.i/; He was lost in reverie until he suddenly heard someone behind him.",
      "answer_length": 98,
      "question_length": 152,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Cambridge Dictionary--25",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 25,
      "question": "Find two different meanings of the word \"harmony\" in the Cambridge Dictionary.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "Meaning 1: a pleasant musical sound made by different notes being played or sung at the same time; Meaning 2: a situation in which people are peaceful and agree with each other, or when things seem right or suitable together",
      "answer_length": 224,
      "question_length": 78,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--26",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 26,
      "question": "Search for the word \"nostalgia\" in the Cambridge Dictionary and report the translation of this word into Chinese.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "golden",
      "answer": "怀旧",
      "answer_length": 2,
      "question_length": 113,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Cambridge Dictionary--27",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 27,
      "question": "Look up the meaning, pronunciation, and an example sentence of the word \"solitude\" using the Cambridge Dictionary.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "UK: /ˈsɒl.ɪ.tʃuːd/, US: /ˈsɑː.lə.tuːd/; the situation of being alone without other people; After months of solitude at sea it felt strange to be in company.",
      "answer_length": 156,
      "question_length": 114,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--28",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 28,
      "question": "Search for \"feel giddy\" in Cambridge Dictionary's Thesaurus and list the synonyms the dictionary provides.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "golden",
      "answer": "Synonyms: feel dizzy; whirl; spin; reel",
      "answer_length": 39,
      "question_length": 106,
      "actions": [
        "find",
        "search",
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Cambridge Dictionary--29",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 29,
      "question": "Go to the Plus section of Cambridge Dictionary, find Image quizzes and do an easy quiz about Animals and tell me your final score.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "Action: finish an easy Image quiz about Animals",
      "answer_length": 47,
      "question_length": 130,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 4
    },
    {
      "id": "Cambridge Dictionary--30",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 30,
      "question": "Find the grammar for present perfect simple uses in English, including examples of affirmative, negative, and interrogative sentences, on the Cambridge Dictionary website.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "Present perfect simple: uses;  I’ve been there a couple of times before; We haven’t met before, have we?; Have you ever tried to write your name and address with your left hand?",
      "answer_length": 177,
      "question_length": 171,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--31",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 31,
      "question": "Look up the use of modal verbs in grammar section for expressing possibility (e.g., 'might', 'could', 'may') and find examples of their usage in sentences on the Cambridge Dictionary.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "She might sell her house; We could have lunch early; It may be possible for him to get home tonight.",
      "answer_length": 100,
      "question_length": 183,
      "actions": [
        "find",
        "use_tool"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Cambridge Dictionary--32",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 32,
      "question": "Search for the differences between \"fewer\" and \"less\" in grammar section, and provide examples illustrating their correct usage from the Cambridge Dictionary.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "Article: 'Less or fewer?'; I do less work at weekends than I used to; Better cycle routes would mean fewer cars and fewer accidents.",
      "answer_length": 132,
      "question_length": 158,
      "actions": [
        "find",
        "search",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Cambridge Dictionary--33",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 33,
      "question": "Find explanations and examples of the passive voice in Grammar on the Cambridge Dictionary website.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "Cambridge University Press published this book. (active); This book was published by Cambridge University Press. (passive)",
      "answer_length": 122,
      "question_length": 99,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--34",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 34,
      "question": "Use the Cambridge Dictionary to understand the rules for forming and using comparative and superlative adjectives in English Grammar, including example sentences.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "This car is more expensive than my last one; Joe used to be the slowest runner in the class.",
      "answer_length": 92,
      "question_length": 162,
      "actions": [
        "use_tool"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--35",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 35,
      "question": "Find the most common prepositions that consist of groups of words on the Cambridge Dictionary.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "ahead of; except for; instead of; owing to; apart from; in addition to ...",
      "answer_length": 74,
      "question_length": 94,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--36",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 36,
      "question": "Search for guidelines on using indirect speech in English, with examples of how to change direct speech to indirect speech, on the Cambridge Dictionary.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "Example: direct: ‘I’m tired,’ I said; indirect: I told them (that) I was tired.",
      "answer_length": 79,
      "question_length": 152,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Cambridge Dictionary--37",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 37,
      "question": "Use Cambridge Dictionary to understand the use of articles ('a', 'an', 'the') in English Grammar, including examples of usage with both countable and uncountable nouns.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "<understandings>, Countable nouns: I have a sister and a brother. That was an excellent meal. The lion roared. Uncountable nouns: I hope we have nice weather. The weather was awful last summer...",
      "answer_length": 195,
      "question_length": 168,
      "actions": [
        "use_tool"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Cambridge Dictionary--38",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 38,
      "question": "Go to the Plus section of Cambridge Dictionary, finish a recommended Grammar quiz without login and tell me your final score.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "Action: finish a recommended Grammar quiz",
      "answer_length": 41,
      "question_length": 125,
      "actions": [
        "answer",
        "save_state"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": true,
      "requires_navigation": true,
      "complexity": 6
    },
    {
      "id": "Cambridge Dictionary--39",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 39,
      "question": "Try the Word Scramble game in the Plus section, Can you beat the clock by unscrambling the letters to spell the word? (Just try the first example.)",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "Action: finish the Word Scramble game in the Plus section",
      "answer_length": 57,
      "question_length": 147,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Cambridge Dictionary--40",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 40,
      "question": "Look up the definition, pronunciation in UK English, and at least one example using the word 'mitigate'.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "UK: /ˈmɪt.ɪ.ɡeɪt/, US: /ˈmɪt̬.ə.ɡeɪt/; to make something less harmful, unpleasant, or bad; It is unclear how to mitigate the effects of tourism on the island.",
      "answer_length": 158,
      "question_length": 104,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Cambridge Dictionary--41",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 41,
      "question": "Find and browse Cambridge Dictionary Shop section, listing 3 items.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "possible",
      "answer": "Shop: Cambridge Dictionary organic cotton Hoodie; On top of the world organic cotton T shirt - white writing variety; Multitasking Mug",
      "answer_length": 134,
      "question_length": 67,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 5
    },
    {
      "id": "Cambridge Dictionary--42",
      "site": "Cambridge Dictionary",
      "slug": "cambridge_dictionary",
      "index": 42,
      "question": "Convert the Cambridge Dictionary homepage from English (UK) to Deutsch.",
      "local_url": "http://localhost:40012/",
      "upstream_url": "https://dictionary.cambridge.org/",
      "original_web": "https://dictionary.cambridge.org/",
      "answer_type": "golden",
      "answer": "Action: Click English (UK), change language to: Deutsch",
      "answer_length": 55,
      "question_length": 71,
      "actions": [
        "compute"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Coursera--0",
      "site": "Coursera",
      "slug": "coursera",
      "index": 0,
      "question": "Find a beginner-level online course about '3d printing' which lasts 1-3 months, and is provided by a renowned university.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Rapid Prototyping Using 3D Printing, Specialization",
      "answer_length": 51,
      "question_length": 121,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Coursera--1",
      "site": "Coursera",
      "slug": "coursera",
      "index": 1,
      "question": "Search for a beginner-level online course about Python programming, suitable for someone who has no programming experience on Coursera.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Python for Data Science, AI & Development",
      "answer_length": 41,
      "question_length": 135,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Coursera--2",
      "site": "Coursera",
      "slug": "coursera",
      "index": 2,
      "question": "Find a Beginner's Spanish Specialization on Coursera and show all the courses in this Specialization.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Learn Spanish: Basic Spanish Vocabulary, Specialization; Spanish Vocabulary: Meeting People; Spanish Vocabulary: Cultural Experience; Spanish Vocabulary: Sports, Travel, and the Home; Spanish Vocabulary: Careers and Social Events; Spanish Vocabulary Project",
      "answer_length": 257,
      "question_length": 101,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Coursera--3",
      "site": "Coursera",
      "slug": "coursera",
      "index": 3,
      "question": "Identify a new course or Specialization on Coursera related to Python Data Science, sort the courses by newest, what the first course is and which institution offers it.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Data Science with NumPy, Sets, and Dictionaries; Duke University",
      "answer_length": 64,
      "question_length": 169,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 3
    },
    {
      "id": "Coursera--4",
      "site": "Coursera",
      "slug": "coursera",
      "index": 4,
      "question": "Identify a course or Specialization on Coursera that helps business process management with with a rating 4.7.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Business Foundations, Specialization",
      "answer_length": 36,
      "question_length": 110,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Coursera--5",
      "site": "Coursera",
      "slug": "coursera",
      "index": 5,
      "question": "Identify a Specialization on Coursera that teaches C++ programming for beginners, provide the name and what the learning outcomes are.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Coding for Everyone: C and C++, Specialization; Outcomes: Learn in-demand skills from university and industry experts; Master a subject or tool with hands-on projects; Develop a deep understanding of key concepts; Earn a career certificate from University of California, Santa Cruz",
      "answer_length": 281,
      "question_length": 134,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Coursera--6",
      "site": "Coursera",
      "slug": "coursera",
      "index": 6,
      "question": "Identify a course on Coursera related to 'Artificial Intelligence for Healthcare' and note the course duration along with the number of quizzes in Assessments.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Fundamentals of Machine Learning for Healthcare; 14 hours (approximately); 19 quizzes",
      "answer_length": 85,
      "question_length": 159,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Coursera--7",
      "site": "Coursera",
      "slug": "coursera",
      "index": 7,
      "question": "Find a course on Coursera that teaches Reinforcement Learning for Intermediate with a rating of at least 4.5. Provide the name of the course, the institution offering it, and the number of reviews it has received.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Reinforcement Learning, Specialization; University of Alberta; 3.3K reviews",
      "answer_length": 75,
      "question_length": 213,
      "actions": [
        "find",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Coursera--8",
      "site": "Coursera",
      "slug": "coursera",
      "index": 8,
      "question": "Find a free course related to 'R for Data Science' available on Coursera. Scroll to find a course with the Free tag. What language the course is taught in?",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Introducción a Data Science: Programación Estadística con R; Taught in Spanish",
      "answer_length": 78,
      "question_length": 155,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Coursera--9",
      "site": "Coursera",
      "slug": "coursera",
      "index": 9,
      "question": "Identify a Coursera course on artificial intelligence ethics that has a duration of less than 20 hours to complete and has been rated 4+ stars by participants.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Artificial Intelligence: Ethics & Societal Challenges",
      "answer_length": 53,
      "question_length": 159,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Coursera--10",
      "site": "Coursera",
      "slug": "coursera",
      "index": 10,
      "question": "Locate an introductory course related to artificial intelligence on Coursera, ensuring it's suitable for beginners and contains at least one module discussing Ethical Considerations.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Introduction to Artificial Intelligence (AI)",
      "answer_length": 44,
      "question_length": 182,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Coursera--11",
      "site": "Coursera",
      "slug": "coursera",
      "index": 11,
      "question": "Search for a Specialization on Coursera about project management that is produced by a university, show a testimonial for this Specialization.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Project Management, Specialization; Felipe M. \"To be able to take courses at my own pace and rhythm has been an amazing experience. I can learn whenever it fits my schedule and mood.\"",
      "answer_length": 183,
      "question_length": 142,
      "actions": [
        "find",
        "search",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Coursera--12",
      "site": "Coursera",
      "slug": "coursera",
      "index": 12,
      "question": "Look for a Coursera course (not Specialization) that teaches Java programming basics.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Introduction to Java",
      "answer_length": 20,
      "question_length": 85,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Coursera--13",
      "site": "Coursera",
      "slug": "coursera",
      "index": 13,
      "question": "Look for a Specialization on Coursera that teaches Python programming, and identify the skills you will learn by taking this Specialization.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Python 3 Programming, Specialization; Learn Python 3 basics, from the basics to more advanced concepts like lists and functions; Practice and become skilled at solving problems and fixing errors in your code; Gain the ability to write programs that fetch data from internet APIs and extract useful information.",
      "answer_length": 310,
      "question_length": 140,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Coursera--14",
      "site": "Coursera",
      "slug": "coursera",
      "index": 14,
      "question": "Find a course on Coursera related to Introductory Project Management that includes modules on Agile methodology.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Agile Project Management",
      "answer_length": 24,
      "question_length": 112,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Coursera--15",
      "site": "Coursera",
      "slug": "coursera",
      "index": 15,
      "question": "Find a course on Coursera named 'Introduction to Mathematical Thinking' offered by Stanford, what is the percentage (rounded) of 5 star ratings in reviews and which level has the least percentage?.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "85%; 2-star",
      "answer_length": 11,
      "question_length": 197,
      "actions": [
        "find",
        "save_state"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 7
    },
    {
      "id": "Coursera--16",
      "site": "Coursera",
      "slug": "coursera",
      "index": 16,
      "question": "Identify a course on Coursera named 'Introduction to Finance: The Basics', who is the course instructor and what other courses does he/she teach.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Xi Yang; Introduction to Finance: The Role of Financial Markets",
      "answer_length": 63,
      "question_length": 145,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Coursera--17",
      "site": "Coursera",
      "slug": "coursera",
      "index": 17,
      "question": "How many results are there for a search on Coursera for Machine Learning, then filtered by Credit Eligible and 1-4 Years duration?",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "23",
      "answer_length": 2,
      "question_length": 130,
      "actions": [
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Coursera--18",
      "site": "Coursera",
      "slug": "coursera",
      "index": 18,
      "question": "Identify a Coursera course that teaches JavaScript, which is beginner-friendly and includes a certificate upon completion.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Programming with JavaScript",
      "answer_length": 27,
      "question_length": 122,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "Coursera--19",
      "site": "Coursera",
      "slug": "coursera",
      "index": 19,
      "question": "Identify a course on Coursera that provides an introduction to Psychology, list the instructor's name, the institution offering it, and how many hours it will approximately take to complete.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Instructor: Paul Bloom; Yale University; 14 hours",
      "answer_length": 49,
      "question_length": 190,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Coursera--20",
      "site": "Coursera",
      "slug": "coursera",
      "index": 20,
      "question": "Find an Intermediate-level online course on Coursera about 'Blockchain Technology' which lasts between 1 to 4 weeks, and is provided by a well-known institution. Also, note the course's main goals and the instructor's name.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Introduction to Supply Chain Finance & Blockchain Technology; New York Institute of Finance; Instructors: Oliver Belin, Jack Farmer; <summary of main goals>",
      "answer_length": 156,
      "question_length": 223,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 6
    },
    {
      "id": "Coursera--21",
      "site": "Coursera",
      "slug": "coursera",
      "index": 21,
      "question": "Search for an online course on Coursera about 'Digital Marketing', suitable for beginner-level learners. Specify the course duration, the main learning outcomes, and the institution offering the course.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Foundations of Digital Marketing and E-commerce; Google; Instructors: Google Career Certificates; <outcomes>; duration: 1 - 4 weeks or 25 hours (approximately)",
      "answer_length": 159,
      "question_length": 202,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Coursera--22",
      "site": "Coursera",
      "slug": "coursera",
      "index": 22,
      "question": "Identify a Specialization on Coursera that focuses on 'Human Resource', list the courses included in this Specialization, and the institution offering it.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Human Resource Management: HR for People Managers Specialization; University of Minnesota; Course 1: Preparing to Manage Human Resources; Course 2: Recruiting, Hiring, and Onboarding Employees; Course 3: Managing Employee Performance; Course 4: Managing Employee Compensation; Course 5: Human Resources Management Capstone: HR for People Managers",
      "answer_length": 346,
      "question_length": 154,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Coursera--23",
      "site": "Coursera",
      "slug": "coursera",
      "index": 23,
      "question": "Find a course on Coursera about 'Artificial Intelligence Ethics', which has a duration of less than 5 weeks and has been rated 4.5 stars or higher. Provide the course name and the instructor's name.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Artificial Intelligence: Ethics & Societal Challenges; Lund University; 4.6 stars; Instructors: Maria Hedlund, Lena Lindström, Erik Persson",
      "answer_length": 139,
      "question_length": 198,
      "actions": [
        "find",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping",
        "research"
      ],
      "constraint_count": 4,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Coursera--24",
      "site": "Coursera",
      "slug": "coursera",
      "index": 24,
      "question": "Locate an online course on Coursera related to 'Sustainability' that belongs to Physical Science and Engineering subject. The course should include a module on Measuring Sustainability. Note the course duration and the offering institution.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Introduction to Sustainability; University of Illinois at Urbana-Champaign; Instructors: Dr. Jonathan Tomkin; duration: Approx. 25 hours to complete, 3 weeks at 8 hours a week",
      "answer_length": 175,
      "question_length": 240,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Coursera--25",
      "site": "Coursera",
      "slug": "coursera",
      "index": 25,
      "question": "Find a course on Coursera about 'Relativity' for beginners. List the course's main topics and the estimated time (in hours) required to complete it.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Understanding Einstein: The Special Theory of Relativity; <topic>; Approx. 80 hours to complete",
      "answer_length": 95,
      "question_length": 148,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Coursera--26",
      "site": "Coursera",
      "slug": "coursera",
      "index": 26,
      "question": "Identify a Specialization on Coursera that offers an overview of 'Renewable Energy'. The Specialization should be beginner-level and include a course on Renewable Energy Futures. Note the instructor's name and the number of weeks required to complete the course if I spend 5 hours a week.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Renewable Energy Specialization; Instructors: Stephen R. Lawrence, Paul Komor; 2 months",
      "answer_length": 87,
      "question_length": 288,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Coursera--27",
      "site": "Coursera",
      "slug": "coursera",
      "index": 27,
      "question": "Search for a Specialization on Coursera about 'Data Visualization' that includes a project. Provide the name of the Specialization, the institution offering it, and the skills that will be developed by completing it.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Data Visualization with Tableau Specialization; University of California, Davis; <skills>",
      "answer_length": 89,
      "question_length": 216,
      "actions": [
        "find",
        "search",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "Coursera--28",
      "site": "Coursera",
      "slug": "coursera",
      "index": 28,
      "question": "Locate a Coursera Guided project related to 'Astrophysics' suitable for advanced learners. Mention the course duration, the institution offering it, and the main subjects covered in the course.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Explore Einstein's theories of Relativity using Wolfram; Coursera Project Network; 2 hours; <main subjects>",
      "answer_length": 107,
      "question_length": 193,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Coursera--29",
      "site": "Coursera",
      "slug": "coursera",
      "index": 29,
      "question": "Browse the Coursera website and find the price required for one year of Coursera Plus. How much is the discount? Then list 3 companies that work with Coursera.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "$399/year, discount: 59 / month * 12 - 399 = 309; Google, IBM, and Imperial College London ...",
      "answer_length": 94,
      "question_length": 159,
      "actions": [
        "find",
        "search",
        "answer"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 7
    },
    {
      "id": "Coursera--30",
      "site": "Coursera",
      "slug": "coursera",
      "index": 30,
      "question": "Locate the course 'Modern Art & Ideas' on Coursera offered by The Museum of Modern Art. Find out the percentage (rounded) of 3-star ratings in the reviews and note which star level has the lowest percentage.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "3 stars: 2.5%; 1 star has the lowest percentage",
      "answer_length": 47,
      "question_length": 207,
      "actions": [
        "find",
        "filter_sort",
        "save_state"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 9
    },
    {
      "id": "Coursera--31",
      "site": "Coursera",
      "slug": "coursera",
      "index": 31,
      "question": "Search for the course 'Exploring Quantum Physics' on Coursera, offered by the University of Maryland, College Park. Identify the percentage (rounded) of 5-star ratings in the reviews.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "52.6%",
      "answer_length": 5,
      "question_length": 183,
      "actions": [
        "find",
        "search",
        "save_state"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": true,
      "requires_navigation": false,
      "complexity": 8
    },
    {
      "id": "Coursera--32",
      "site": "Coursera",
      "slug": "coursera",
      "index": 32,
      "question": "Search for 'Data Analysis' courses on Coursera. Apply filters to find courses that are 'Beginner Level' and have a duration ranging from 1 to 3 months. Determine the total count of courses that match these specifications.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "568 results",
      "answer_length": 11,
      "question_length": 221,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Coursera--33",
      "site": "Coursera",
      "slug": "coursera",
      "index": 33,
      "question": "Find a beginner level Coursera course related to \"Internet of Things (IoT)\" with a high rating. Provide the course name, instructor's name, and a brief summary of the skills that will be taught.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Introduction and Programming with IoT Boards; Instructor: James Won-Ki HONG; <summary>",
      "answer_length": 86,
      "question_length": 194,
      "actions": [
        "find",
        "answer",
        "filter_sort"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "Coursera--34",
      "site": "Coursera",
      "slug": "coursera",
      "index": 34,
      "question": "Find the course on Coursera named 'Essentials of Global Health'. Determine the instructor of this course and summarize his bio, note if there are any additional courses he offers on Coursera.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Instructor: Richard Skolnik; <summary> of bio; no other course",
      "answer_length": 62,
      "question_length": 191,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Coursera--35",
      "site": "Coursera",
      "slug": "coursera",
      "index": 35,
      "question": "Find a Coursera course on Sustainable Agriculture practices, and detail the course's objectives and the background of the lead instructor.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Introduction to Sustainability; <objectives>; Instructor: Dr. Jonathan Tomkin",
      "answer_length": 77,
      "question_length": 138,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "Coursera--36",
      "site": "Coursera",
      "slug": "coursera",
      "index": 36,
      "question": "Browse Coursera, which universities offer Master of Advanced Study in Engineering degrees? Tell me what is the latest application deadline for this degree?",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Master of Advanced Study in Engineering; UC Berkeley College of Engineering; Fall 2024; March 1, 2024: Fall 2024 Priority Application Deadline; April 1, 2024: Fall 2024 Final Application Deadline",
      "answer_length": 195,
      "question_length": 155,
      "actions": [
        "search",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 4
    },
    {
      "id": "Coursera--37",
      "site": "Coursera",
      "slug": "coursera",
      "index": 37,
      "question": "Browse the Coursera homepage and list at least three free courses.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Business Analytics with Excel: Elementary to Advanced; Cybersecurity for Everyone; Financial Markets ...",
      "answer_length": 104,
      "question_length": 66,
      "actions": [
        "search",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 5
    },
    {
      "id": "Coursera--38",
      "site": "Coursera",
      "slug": "coursera",
      "index": 38,
      "question": "Browse Coursera, which universities and companies from Australia are partners of Coursera? List all of them.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "golden",
      "answer": "Macquarie University; The University of Melbourne; The University of Sydney; University of Western Australia; UNSW Sydney (The University of New South Wales)",
      "answer_length": 157,
      "question_length": 108,
      "actions": [
        "search",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 4
    },
    {
      "id": "Coursera--39",
      "site": "Coursera",
      "slug": "coursera",
      "index": 39,
      "question": "Find the Space Safety course offered by TUM on Coursera. How many videos are there in module 2? What is the name of each video?",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "golden",
      "answer": "6 videos; Introduction; Space Debris; Mitigation; Measurements; Protection; Atmospheric Re-entry",
      "answer_length": 96,
      "question_length": 127,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "Coursera--40",
      "site": "Coursera",
      "slug": "coursera",
      "index": 40,
      "question": "Browse Coursera for Business and Coursera for Teams and summarise some of their advantages.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "Coursera for Business: Strengthen critical skills with content you can trust; Develop, retain, and advance critical talent; Lower training costs without sacrificing quality; Track and measure skills to demonstrate ROI; Coursera for Teams: Upskill 5 to 125 employees; Unlimited access to 10,250+ learning opportunities; Program setup and launch tools; Analytics and benchmarking dashboard",
      "answer_length": 387,
      "question_length": 91,
      "actions": [
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 3
    },
    {
      "id": "Coursera--41",
      "site": "Coursera",
      "slug": "coursera",
      "index": 41,
      "question": "Browse online degrees section on Coursera and list 3 Bachelor's degree programmes.",
      "local_url": "http://localhost:40013/",
      "upstream_url": "https://www.coursera.org/",
      "original_web": "https://www.coursera.org/",
      "answer_type": "possible",
      "answer": "BSc Computer Science, University of London; Bachelor of Science in Cybersecurity Technology, University of Maryland Global Campus; Bachelor of Information Technology, Illinois Institute of Technology",
      "answer_length": 199,
      "question_length": 82,
      "actions": [
        "search",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 5
    },
    {
      "id": "ESPN--0",
      "site": "ESPN",
      "slug": "espn",
      "index": 0,
      "question": "Look up the current standings for the NBA Eastern Conference on ESPN.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "<standings> (NBA Eastern Conference)",
      "answer_length": 36,
      "question_length": 69,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "ESPN--1",
      "site": "ESPN",
      "slug": "espn",
      "index": 1,
      "question": "Check the latest articles on ESPN for updates on any trades that occurred in the NBA within the past 2 days.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "<article> (trades), maybe no article",
      "answer_length": 36,
      "question_length": 108,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "ESPN--2",
      "site": "ESPN",
      "slug": "espn",
      "index": 2,
      "question": "Show the scores and main highlight of the Milwaukee Bucks game that took place within the last 2 days on ESPN.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "<score> (Milwaukee Bucks vs xxx); <highlight>",
      "answer_length": 45,
      "question_length": 110,
      "actions": [
        "answer",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "ESPN--3",
      "site": "ESPN",
      "slug": "espn",
      "index": 3,
      "question": "Retrieve the final score from the most recent NBA game broadcast on ESPN, including the playing teams' names and the date of the match.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "<score> (most recent NBA game)",
      "answer_length": 30,
      "question_length": 135,
      "actions": [
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ESPN--4",
      "site": "ESPN",
      "slug": "espn",
      "index": 4,
      "question": "Check ESPN for the final scores of NBA games that were played yesterday.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "<score> (yesterday)",
      "answer_length": 19,
      "question_length": 72,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "ESPN--5",
      "site": "ESPN",
      "slug": "espn",
      "index": 5,
      "question": "Identify the top scorer in the NBA from the latest completed game and note down the points scored, the team they play for, and their position on the team.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "<player>; <PTS>; <team>; <position> (eg, James Harden; scored 35 points; LA Clippers; Shooting Guard (SG))",
      "answer_length": 106,
      "question_length": 154,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ESPN--6",
      "site": "ESPN",
      "slug": "espn",
      "index": 6,
      "question": "Find the result of the latest basketball game between the Los Angeles Lakers and the Boston Celtics, including the final score and top scorer from the match.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "Los Angeles Lakers vs Boston Celtics, 115 - 126; Kristaps Porzingis",
      "answer_length": 67,
      "question_length": 157,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "ESPN--7",
      "site": "ESPN",
      "slug": "espn",
      "index": 7,
      "question": "Retrieve the final score and a brief summary of the latest NBA game played by the Los Angeles Lakers as reported on ESPN.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "<score> (latest, Los Angeles Lakers vs xxx); <summary>",
      "answer_length": 54,
      "question_length": 121,
      "actions": [
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "ESPN--8",
      "site": "ESPN",
      "slug": "espn",
      "index": 8,
      "question": "Find information on ESPN about the top three scoring leaders in the NBA as of the last day of the regular season, and note which teams they play for.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "Joel Embiid (PHI) with 34.4 PPG, Luka Doncic (DAL) with 32.9 PPG, and Giannis Antetokounmpo (MIL) with 31.4 PPG.",
      "answer_length": 112,
      "question_length": 149,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "ESPN--9",
      "site": "ESPN",
      "slug": "espn",
      "index": 9,
      "question": "Search on ESPN for how many teams have Los Angeles in their name and how many of them are NBA.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "golden",
      "answer": "10 teams have Los Angeles in their name; 2 teams are NBA",
      "answer_length": 56,
      "question_length": 94,
      "actions": [
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "ESPN--10",
      "site": "ESPN",
      "slug": "espn",
      "index": 10,
      "question": "Check ESPN for the score and a brief recap of the latest college football championship game.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "<score>; <summary> (latest college football championship game)",
      "answer_length": 62,
      "question_length": 92,
      "actions": [
        "answer"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "ESPN--11",
      "site": "ESPN",
      "slug": "espn",
      "index": 11,
      "question": "How many NBA teams are there and list all the teams with 'New' in their name.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "golden",
      "answer": "30; New York Knicks; New Orleans Pelicans",
      "answer_length": 41,
      "question_length": 77,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "ESPN--12",
      "site": "ESPN",
      "slug": "espn",
      "index": 12,
      "question": "The first three Top Headlines in the current ESPN home page correspond to which sports leagues?",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "<League 1>; <League 2>; <League 3>",
      "answer_length": 34,
      "question_length": 95,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ESPN--13",
      "site": "ESPN",
      "slug": "espn",
      "index": 13,
      "question": "Identify today's top headline in the Basketball section of ESPN, and summarize the main points of that article.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "<headline>; <summary>",
      "answer_length": 21,
      "question_length": 111,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ESPN--14",
      "site": "ESPN",
      "slug": "espn",
      "index": 14,
      "question": "Find the latest news about NBA trades or player movements on ESPN and report the most recent trade deal OR player acquisition.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "News about NBA trades",
      "answer_length": 21,
      "question_length": 126,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "ESPN--15",
      "site": "ESPN",
      "slug": "espn",
      "index": 15,
      "question": "Check the scores of the NBA games played on December 25, 2023.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "golden",
      "answer": "(US Time) Bucks vs Knicks, 122 - 129; Warriors vs Nuggets, 114 - 120; Celtics vs Lakers, 126 - 115; 76ers vs Heat, 113 - 119; Mavericks vs Suns, 128 - 114",
      "answer_length": 154,
      "question_length": 62,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ESPN--16",
      "site": "ESPN",
      "slug": "espn",
      "index": 16,
      "question": "Check the schedule for the NBA game on December 25, 2023, and provide the teams that are playing and their current standings in their respective conferences.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "teams and current standings",
      "answer_length": 27,
      "question_length": 157,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "ESPN--17",
      "site": "ESPN",
      "slug": "espn",
      "index": 17,
      "question": "Check out the NBA Basketball Power Index 2023-24 to see which teams are in first place and which are in last place.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "golden",
      "answer": "Boston Celtics; San Antonio Spurs",
      "answer_length": 33,
      "question_length": 115,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ESPN--18",
      "site": "ESPN",
      "slug": "espn",
      "index": 18,
      "question": "How many sports leagues can you choose from on the ESPN home page?",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "golden",
      "answer": "31 (in ESPN America)",
      "answer_length": 20,
      "question_length": 66,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "ESPN--19",
      "site": "ESPN",
      "slug": "espn",
      "index": 19,
      "question": "Who has the highest salary in Boston Celtics Roster 2023-24?",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "golden",
      "answer": "Jrue Holiday",
      "answer_length": 12,
      "question_length": 60,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "ESPN--20",
      "site": "ESPN",
      "slug": "espn",
      "index": 20,
      "question": "Look up the current leaders in rebounds and assists in the NBA Western Conference on ESPN.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "For Western, rebounds: Domantas Sabonis; assists: Luka Doncic",
      "answer_length": 61,
      "question_length": 90,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "ESPN--21",
      "site": "ESPN",
      "slug": "espn",
      "index": 21,
      "question": "Show the scores and main highlight of the Denver Nuggets game that occurred within the last 3 days on ESPN.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "<score> within 3 days; <highlight>",
      "answer_length": 34,
      "question_length": 107,
      "actions": [
        "answer",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "ESPN--22",
      "site": "ESPN",
      "slug": "espn",
      "index": 22,
      "question": "Find the latest Team transactions in the NBA within the past week.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "Team transaction: eg, February 1, TRANSACTION: Dallas Mavericks, Assigned F Olivier-Maxence Proster to the Texas Legends of the G League.",
      "answer_length": 137,
      "question_length": 66,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "ESPN--23",
      "site": "ESPN",
      "slug": "espn",
      "index": 23,
      "question": "Find the result of the latest basketball game between the Miami Heat and the New York Knicks, including the final score and top rebounder from the match.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "NBA <score>, latest, Miami Heat - New York Knicks, eg, January 28, 2024, 109 - 125, Top rebounder: B. Adebayo, P. Achiuwa",
      "answer_length": 121,
      "question_length": 153,
      "actions": [
        "find",
        "filter_sort"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "ESPN--24",
      "site": "ESPN",
      "slug": "espn",
      "index": 24,
      "question": "Find the final score from the most recent NFL game broadcast on ESPN, including the teams' names and the date of the match.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "NFL <score>, latest, eg, January 29, 2024, Chiefs - Ravens, 17 - 10",
      "answer_length": 67,
      "question_length": 123,
      "actions": [
        "find"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ESPN--25",
      "site": "ESPN",
      "slug": "espn",
      "index": 25,
      "question": "Identify the player with the most assists in the latest NBA game and show me the assists, the team they play for, and their position.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "NBA game, latest, eg, February 2, 2024, Lakers - Celtics, 114 - 105, most assist: 14, D. Russell, position: PG, team: Los Angeles Lakers",
      "answer_length": 136,
      "question_length": 133,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "ESPN--26",
      "site": "ESPN",
      "slug": "espn",
      "index": 26,
      "question": "Find information on ESPN NBA schedule. Tell me yesterday's matchups in which the loser high was higher than the winner high.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "NBA game, yesterday, eg, January 26, 2024, Philadelphia - Indiana, 134 - 122, winner high 26 - loser high 31; Denver - New York, 122 - 84, winner high 26 - loser high 31; Chicago - Los Angeles, 141 - 132, winner high 29 - loser high 32",
      "answer_length": 235,
      "question_length": 124,
      "actions": [
        "find",
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ESPN--27",
      "site": "ESPN",
      "slug": "espn",
      "index": 27,
      "question": "Search on ESPN for how many teams have 'Golden' in their name and how many of them are in the NHL.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "golden",
      "answer": "30 teams in search results, 1 team Vegas Golden Knights (NHL)",
      "answer_length": 61,
      "question_length": 98,
      "actions": [
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "ESPN--28",
      "site": "ESPN",
      "slug": "espn",
      "index": 28,
      "question": "How many MLB teams are there and list all the teams with 'City' in their name.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "golden",
      "answer": "30 teams in search results, Kansas City Royals",
      "answer_length": 46,
      "question_length": 78,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "ESPN--29",
      "site": "ESPN",
      "slug": "espn",
      "index": 29,
      "question": "Identify today's top headline in the Soccer section of ESPN, and summarize the main points of that article.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "<headline> today",
      "answer_length": 16,
      "question_length": 107,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ESPN--30",
      "site": "ESPN",
      "slug": "espn",
      "index": 30,
      "question": "Check out the NHL Standings 2023-24 on ESPN to see which teams are at the top and which are at the bottom in Eastern and Western Conference. What about the situation in Division.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "NHL Standings 2023-24, top - bottom, Eastern Conference: New York Rangers - Columbus Blue Jackets; Western Conference: Vancouver Canucks - Chicago Blackhawks; Division: ATLANTIC, Boston Bruins - Montreal Canadiens; METROPOLITAN: New York Rangers - Columbus Blue Jackets; CENTRAL: Dallas Stars - Chicago Blackhawks; PACIFIC: Vancouver Canucks - San Jose Sharks",
      "answer_length": 359,
      "question_length": 178,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 3,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "ESPN--31",
      "site": "ESPN",
      "slug": "espn",
      "index": 31,
      "question": "Who has the heaviest weight among infielders in the New York Yankees Roster 2023-24?",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "golden",
      "answer": "Carlos Rodon, 255 lbs",
      "answer_length": 21,
      "question_length": 84,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ESPN--32",
      "site": "ESPN",
      "slug": "espn",
      "index": 32,
      "question": "Review yesterday's NHL game results on ESPN, focusing on teams' performance.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "NHL <score> yesterday",
      "answer_length": 21,
      "question_length": 76,
      "actions": [
        "answer"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "ESPN--33",
      "site": "ESPN",
      "slug": "espn",
      "index": 33,
      "question": "Locate the latest ESPN articles discussing potential MVP candidates in the NFL for 2023 season.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "Article, '2023 NFL MVP: Ranking five finalists, plus stats'",
      "answer_length": 59,
      "question_length": 95,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    },
    {
      "id": "ESPN--34",
      "site": "ESPN",
      "slug": "espn",
      "index": 34,
      "question": "Visit ESPN to view the Philadelphia 76ers' latest injuries.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "Philadelphia 76ers - Injuries, latest",
      "answer_length": 37,
      "question_length": 59,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "ESPN--35",
      "site": "ESPN",
      "slug": "espn",
      "index": 35,
      "question": "Browse ESPN to find out when the next game of the Los Angeles Lakers will start. Then navigate to the ticket purchasing website from ESPN, what is the cheapest ticket available.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "next game of Los Angeles Lakers, <price>",
      "answer_length": 40,
      "question_length": 177,
      "actions": [
        "find",
        "search",
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 6
    },
    {
      "id": "ESPN--36",
      "site": "ESPN",
      "slug": "espn",
      "index": 36,
      "question": "Search for Lionel Messi's last 5 games, which teams has he played for, and what are the results?",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "<games>; Inter Miami CF, <results>",
      "answer_length": 34,
      "question_length": 96,
      "actions": [
        "find",
        "search"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 4
    },
    {
      "id": "ESPN--37",
      "site": "ESPN",
      "slug": "espn",
      "index": 37,
      "question": "Check out LeBron James' Stats to see how many games he has played in his career so far.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "1471",
      "answer_length": 4,
      "question_length": 87,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "ESPN--38",
      "site": "ESPN",
      "slug": "espn",
      "index": 38,
      "question": "Check Los Angeles Lakers Stats 2023-24, calculate Anthony Davis' games played (GP) percentage, tell me if there are other players with the same games played percentage as Anthony Davis.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "54/58 = 93.1%, no other players, https://www.espn.com/nba/team/stats/_/name/lal/los-angeles-lakers",
      "answer_length": 98,
      "question_length": 185,
      "actions": [
        "answer",
        "compute"
      ],
      "domains": [
        "knowledge"
      ],
      "constraint_count": 2,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 5
    },
    {
      "id": "ESPN--39",
      "site": "ESPN",
      "slug": "espn",
      "index": 39,
      "question": "Check the New York Jets Depth Chart in the NFL section of ESPN and identify the players listed as injured in the 2ND position.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "check IR on https://www.espn.com/nfl/team/depth/_/name/nyj/new-york-jets",
      "answer_length": 72,
      "question_length": 126,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "ESPN--40",
      "site": "ESPN",
      "slug": "espn",
      "index": 40,
      "question": "Browse the ESPN+ page from ESPN for a brief summary of what ESPN+ Tools is used for.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "Bracket Predictor, Bracket Analyzer, Custom Dollar Value Generator",
      "answer_length": 66,
      "question_length": 84,
      "actions": [
        "search"
      ],
      "domains": [
        "shopping"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": true,
      "complexity": 3
    },
    {
      "id": "ESPN--41",
      "site": "ESPN",
      "slug": "espn",
      "index": 41,
      "question": "Find out which four teams the NFC North contains in the NFL on ESPN.",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "golden",
      "answer": "Chicago Bears, Detroit Lions, Green Bay Packers, and Minnesota Vikings",
      "answer_length": 70,
      "question_length": 68,
      "actions": [
        "find"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 2
    },
    {
      "id": "ESPN--42",
      "site": "ESPN",
      "slug": "espn",
      "index": 42,
      "question": "Check out NCAAM standings on ESPN, what are the teams with equal wins and losses in the America East Conference currently?",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "check America East Conference on https://www.espn.com/mens-college-basketball/standings",
      "answer_length": 87,
      "question_length": 122,
      "actions": [
        "answer"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 0,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 1
    },
    {
      "id": "ESPN--43",
      "site": "ESPN",
      "slug": "espn",
      "index": 43,
      "question": "Check out NCAAW recruiting on ESPN, what colleges are the top three players from?",
      "local_url": "http://localhost:40014/",
      "upstream_url": "https://www.espn.com/",
      "original_web": "https://www.espn.com/",
      "answer_type": "possible",
      "answer": "espnW Rankings Class of 2023, Judea Watkins from USC, Mikaylah Williams from LSU, Jadyn Donovan from Duke",
      "answer_length": 105,
      "question_length": 81,
      "actions": [
        "filter_sort"
      ],
      "domains": [
        "general"
      ],
      "constraint_count": 1,
      "requires_state": false,
      "requires_navigation": false,
      "complexity": 3
    }
  ],
  "reference_notices": {
    "Allrecipes": " note that review information is real-time",
    "Amazon": " Products results are related to time and location.",
    "Apple": "",
    "ArXiv": " real-time",
    "BBC News": " real time, answer based on American BBC",
    "Booking": " real-time, check task requirements, date and other requirements (may need sort)",
    "Cambridge Dictionary": " pronunciation (If there is no requirement to provide both US & UK pronunciations, one correct pronunciation is sufficient.) Examples should from Cambridge Dictionary if requested.",
    "Coursera": "",
    "ESPN": " real-time",
    "GitHub": " repos are real-time",
    "Google Flights": " real-time, round trip (only provide the departure flight is OK). Answers can from best options (or sort). Because the best options are in line with the user's needs, if you go through the sort you may get a very unreasonable flight (maybe long duration).",
    "Google Map": "",
    "Google Search": "",
    "Huggingface": " models are real-time",
    "Wolfram Alpha": ""
  }
};
