window.MUTATION_TASK_AUDIT = {
  "generated_at": "2026-05-19T08:19:13.201218+00:00",
  "sample_limit": 5,
  "site_count": 13,
  "total_specs": 65,
  "sites": [
    {
      "site": "allrecipes",
      "web_name": "Allrecipes",
      "family": "recipe_box_save",
      "count": 5,
      "login_url": "https://www.allrecipes.com/account/signin/",
      "login_real_url": true,
      "before": {
        "phase": "before",
        "ok": true,
        "stdout": "Seeded 26 recipes in 14 categories\nSeeded 4 benchmark users: alice.j, bob.c, carol.d, david.k\nSeeded 5 Popular-1960s collection recipes\nvalidated 5 task(s)",
        "stderr": ""
      },
      "after": {
        "phase": "after",
        "ok": false,
        "stdout": "Seeded 26 recipes in 14 categories\nSeeded 4 benchmark users: alice.j, bob.c, carol.d, david.k\nSeeded 5 Popular-1960s collection recipes",
        "stderr": "allrecipes.recipe_box_save.world_s_best_lasagna: after state failed: expected mutation row for allrecipes"
      },
      "tasks": [
        {
          "id": "allrecipes.recipe_box_save.world_s_best_lasagna",
          "instruction": "Sign in as alice.j@test.com and save the recipe \"World's Best Lasagna\" to your Recipe Box. Then answer with the saved recipe title.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.allrecipes.com/account/signin/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "recipe",
            "id": 2,
            "title": "World's Best Lasagna",
            "slug": "worlds-best-lasagna"
          },
          "operation": {
            "action": "save_to_recipe_box",
            "quantity": 1
          },
          "expected_answer": {
            "identity": "World's Best Lasagna",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "allrecipes.recipe_box_item_absent"
            },
            "after": {
              "db_predicate": "allrecipes.recipe_box_item_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "allrecipes.recipe_box_save.good_old_fashioned_pancakes",
          "instruction": "Sign in as alice.j@test.com and save the recipe 'Good Old-Fashioned Pancakes' to your Recipe Box. Then answer with the saved recipe title.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.allrecipes.com/account/signin/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "recipe",
            "id": 6,
            "title": "Good Old-Fashioned Pancakes",
            "slug": "pancakes"
          },
          "operation": {
            "action": "save_to_recipe_box",
            "quantity": 1
          },
          "expected_answer": {
            "identity": "Good Old-Fashioned Pancakes",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "allrecipes.recipe_box_item_absent"
            },
            "after": {
              "db_predicate": "allrecipes.recipe_box_item_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "allrecipes.recipe_box_save.banana_banana_bread",
          "instruction": "Sign in as alice.j@test.com and save the recipe 'Banana Banana Bread' to your Recipe Box. Then answer with the saved recipe title.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.allrecipes.com/account/signin/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "recipe",
            "id": 7,
            "title": "Banana Banana Bread",
            "slug": "banana-bread"
          },
          "operation": {
            "action": "save_to_recipe_box",
            "quantity": 1
          },
          "expected_answer": {
            "identity": "Banana Banana Bread",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "allrecipes.recipe_box_item_absent"
            },
            "after": {
              "db_predicate": "allrecipes.recipe_box_item_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "allrecipes.recipe_box_save.chocolate_chip_cookies",
          "instruction": "Sign in as alice.j@test.com and save the recipe 'Chocolate Chip Cookies' to your Recipe Box. Then answer with the saved recipe title.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.allrecipes.com/account/signin/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "recipe",
            "id": 22,
            "title": "Chocolate Chip Cookies",
            "slug": "chocolate-chip-cookies"
          },
          "operation": {
            "action": "save_to_recipe_box",
            "quantity": 1
          },
          "expected_answer": {
            "identity": "Chocolate Chip Cookies",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "allrecipes.recipe_box_item_absent"
            },
            "after": {
              "db_predicate": "allrecipes.recipe_box_item_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "allrecipes.recipe_box_save.chicken_pot_pie",
          "instruction": "Sign in as alice.j@test.com and save the recipe 'Chicken Pot Pie' to your Recipe Box. Then answer with the saved recipe title.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.allrecipes.com/account/signin/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "recipe",
            "id": 5,
            "title": "Chicken Pot Pie",
            "slug": "chicken-pot-pie"
          },
          "operation": {
            "action": "save_to_recipe_box",
            "quantity": 1
          },
          "expected_answer": {
            "identity": "Chicken Pot Pie",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "allrecipes.recipe_box_item_absent"
            },
            "after": {
              "db_predicate": "allrecipes.recipe_box_item_exists"
            }
          },
          "difficulty": 7
        }
      ]
    },
    {
      "site": "amazon",
      "web_name": "Amazon",
      "family": "cart_add_product",
      "count": 5,
      "login_url": "https://www.amazon.com/ap/signin",
      "login_real_url": true,
      "before": {
        "phase": "before",
        "ok": true,
        "stdout": "Seeded 43 products, 8 categories\nvalidated 5 task(s)",
        "stderr": ""
      },
      "after": {
        "phase": "after",
        "ok": false,
        "stdout": "Seeded 43 products, 8 categories",
        "stderr": "amazon.cart_add_product.harry_potter_and_the_sorcerer_s_stone_book_1: after state failed: expected mutation row for amazon"
      },
      "tasks": [
        {
          "id": "amazon.cart_add_product.harry_potter_and_the_sorcerer_s_stone_book_1",
          "instruction": "Sign in as alice.j@test.com and add \"Harry Potter and the Sorcerer's Stone (Book 1)\" to the Amazon cart with quantity 1. Then answer with the cart item name and quantity.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.amazon.com/ap/signin",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "product",
            "id": 27,
            "name": "Harry Potter and the Sorcerer's Stone (Book 1)",
            "slug": "harry-potter-and-the-sorcerers-stone-book-1"
          },
          "operation": {
            "action": "add_to_cart",
            "quantity": 1
          },
          "expected_answer": {
            "identity": "Harry Potter and the Sorcerer's Stone (Book 1)",
            "quantity": 1
          },
          "state_transition": {
            "before": {
              "db_predicate": "amazon.cart_item_absent"
            },
            "after": {
              "db_predicate": "amazon.cart_item_quantity"
            }
          },
          "difficulty": 7
        },
        {
          "id": "amazon.cart_add_product.atomic_habits_an_easy_proven_way_to_build_good_habits",
          "instruction": "Sign in as alice.j@test.com and add 'Atomic Habits: An Easy & Proven Way to Build Good Habits' to the Amazon cart with quantity 1. Then answer with the cart item name and quantity.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.amazon.com/ap/signin",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "product",
            "id": 25,
            "name": "Atomic Habits: An Easy & Proven Way to Build Good Habits",
            "slug": "atomic-habits-an-easy-proven-way-to-build-good-habits"
          },
          "operation": {
            "action": "add_to_cart",
            "quantity": 1
          },
          "expected_answer": {
            "identity": "Atomic Habits: An Easy & Proven Way to Build Good Habits",
            "quantity": 1
          },
          "state_transition": {
            "before": {
              "db_predicate": "amazon.cart_item_absent"
            },
            "after": {
              "db_predicate": "amazon.cart_item_quantity"
            }
          },
          "difficulty": 7
        },
        {
          "id": "amazon.cart_add_product.where_the_crawdads_sing",
          "instruction": "Sign in as alice.j@test.com and add 'Where the Crawdads Sing' to the Amazon cart with quantity 1. Then answer with the cart item name and quantity.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.amazon.com/ap/signin",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "product",
            "id": 28,
            "name": "Where the Crawdads Sing",
            "slug": "where-the-crawdads-sing"
          },
          "operation": {
            "action": "add_to_cart",
            "quantity": 1
          },
          "expected_answer": {
            "identity": "Where the Crawdads Sing",
            "quantity": 1
          },
          "state_transition": {
            "before": {
              "db_predicate": "amazon.cart_item_absent"
            },
            "after": {
              "db_predicate": "amazon.cart_item_quantity"
            }
          },
          "difficulty": 7
        },
        {
          "id": "amazon.cart_add_product.yeti_rambler_20_oz_tumbler_with_magslider_lid",
          "instruction": "Sign in as alice.j@test.com and add 'YETI Rambler 20 oz Tumbler with MagSlider Lid' to the Amazon cart with quantity 1. Then answer with the cart item name and quantity.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.amazon.com/ap/signin",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "product",
            "id": 35,
            "name": "YETI Rambler 20 oz Tumbler with MagSlider Lid",
            "slug": "yeti-rambler-20-oz-tumbler-with-magslider-lid"
          },
          "operation": {
            "action": "add_to_cart",
            "quantity": 1
          },
          "expected_answer": {
            "identity": "YETI Rambler 20 oz Tumbler with MagSlider Lid",
            "quantity": 1
          },
          "state_transition": {
            "before": {
              "db_predicate": "amazon.cart_item_absent"
            },
            "after": {
              "db_predicate": "amazon.cart_item_quantity"
            }
          },
          "difficulty": 7
        },
        {
          "id": "amazon.cart_add_product.lego_classic_large_creative_brick_box_10698",
          "instruction": "Sign in as alice.j@test.com and add 'LEGO Classic Large Creative Brick Box 10698' to the Amazon cart with quantity 1. Then answer with the cart item name and quantity.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.amazon.com/ap/signin",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "product",
            "id": 41,
            "name": "LEGO Classic Large Creative Brick Box 10698",
            "slug": "lego-classic-large-creative-brick-box-10698"
          },
          "operation": {
            "action": "add_to_cart",
            "quantity": 1
          },
          "expected_answer": {
            "identity": "LEGO Classic Large Creative Brick Box 10698",
            "quantity": 1
          },
          "state_transition": {
            "before": {
              "db_predicate": "amazon.cart_item_absent"
            },
            "after": {
              "db_predicate": "amazon.cart_item_quantity"
            }
          },
          "difficulty": 7
        }
      ]
    },
    {
      "site": "apple",
      "web_name": "Apple",
      "family": "cart_add_product",
      "count": 5,
      "login_url": "https://account.apple.com/sign-in",
      "login_real_url": true,
      "before": {
        "phase": "before",
        "ok": true,
        "stdout": "Seeded 55 products\nSeeded 14 trade-in values\nSeeded 5 support articles\nSeeded 4 benchmark users (alice, bob, carol, david) with addresses, payments, orders, and cart items.\nvalidated 5 task(s)",
        "stderr": ""
      },
      "after": {
        "phase": "after",
        "ok": false,
        "stdout": "Seeded 55 products\nSeeded 14 trade-in values\nSeeded 5 support articles\nSeeded 4 benchmark users (alice, bob, carol, david) with addresses, payments, orders, and cart items.",
        "stderr": "apple.cart_add_product.apple_vision_pro: after state failed: expected mutation row for apple"
      },
      "tasks": [
        {
          "id": "apple.cart_add_product.apple_vision_pro",
          "instruction": "Sign in as alice.j@test.com and add 'Apple Vision Pro' to your Apple bag with quantity 1. Then answer with the bag item name and quantity.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://account.apple.com/sign-in",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "product",
            "id": 47,
            "name": "Apple Vision Pro",
            "slug": "apple-vision-pro"
          },
          "operation": {
            "action": "add_to_cart",
            "quantity": 1
          },
          "expected_answer": {
            "identity": "Apple Vision Pro",
            "quantity": 1
          },
          "state_transition": {
            "before": {
              "db_predicate": "apple.cart_item_absent"
            },
            "after": {
              "db_predicate": "apple.cart_item_quantity"
            }
          },
          "difficulty": 7
        },
        {
          "id": "apple.cart_add_product.macbook_pro_16",
          "instruction": "Sign in as alice.j@test.com and add 'MacBook Pro 16\"' to your Apple bag with quantity 1. Then answer with the bag item name and quantity.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://account.apple.com/sign-in",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "product",
            "id": 8,
            "name": "MacBook Pro 16\"",
            "slug": "macbook-pro-16"
          },
          "operation": {
            "action": "add_to_cart",
            "quantity": 1
          },
          "expected_answer": {
            "identity": "MacBook Pro 16\"",
            "quantity": 1
          },
          "state_transition": {
            "before": {
              "db_predicate": "apple.cart_item_absent"
            },
            "after": {
              "db_predicate": "apple.cart_item_quantity"
            }
          },
          "difficulty": 7
        },
        {
          "id": "apple.cart_add_product.macbook_pro_14",
          "instruction": "Sign in as alice.j@test.com and add 'MacBook Pro 14\"' to your Apple bag with quantity 1. Then answer with the bag item name and quantity.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://account.apple.com/sign-in",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "product",
            "id": 7,
            "name": "MacBook Pro 14\"",
            "slug": "macbook-pro-14"
          },
          "operation": {
            "action": "add_to_cart",
            "quantity": 1
          },
          "expected_answer": {
            "identity": "MacBook Pro 14\"",
            "quantity": 1
          },
          "state_transition": {
            "before": {
              "db_predicate": "apple.cart_item_absent"
            },
            "after": {
              "db_predicate": "apple.cart_item_quantity"
            }
          },
          "difficulty": 7
        },
        {
          "id": "apple.cart_add_product.macbook_air_15",
          "instruction": "Sign in as alice.j@test.com and add 'MacBook Air 15\"' to your Apple bag with quantity 1. Then answer with the bag item name and quantity.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://account.apple.com/sign-in",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "product",
            "id": 24,
            "name": "MacBook Air 15\"",
            "slug": "macbook-air-15"
          },
          "operation": {
            "action": "add_to_cart",
            "quantity": 1
          },
          "expected_answer": {
            "identity": "MacBook Air 15\"",
            "quantity": 1
          },
          "state_transition": {
            "before": {
              "db_predicate": "apple.cart_item_absent"
            },
            "after": {
              "db_predicate": "apple.cart_item_quantity"
            }
          },
          "difficulty": 7
        },
        {
          "id": "apple.cart_add_product.iphone_17_pro_max",
          "instruction": "Sign in as alice.j@test.com and add 'iPhone 17 Pro Max' to your Apple bag with quantity 1. Then answer with the bag item name and quantity.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://account.apple.com/sign-in",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "product",
            "id": 2,
            "name": "iPhone 17 Pro Max",
            "slug": "iphone-17-pro-max"
          },
          "operation": {
            "action": "add_to_cart",
            "quantity": 1
          },
          "expected_answer": {
            "identity": "iPhone 17 Pro Max",
            "quantity": 1
          },
          "state_transition": {
            "before": {
              "db_predicate": "apple.cart_item_absent"
            },
            "after": {
              "db_predicate": "apple.cart_item_quantity"
            }
          },
          "difficulty": 7
        }
      ]
    },
    {
      "site": "arxiv",
      "web_name": "arXiv",
      "family": "library_add_paper",
      "count": 5,
      "login_url": "https://arxiv.org/login",
      "login_real_url": true,
      "before": {
        "phase": "before",
        "ok": true,
        "stdout": "[+] Seeded 20 categories\n  [+] Seeded 1589 papers\n  [+] Created demo user (demo@arxiv.local / demodemo)\n  [+] Seeded 4 benchmark users (alice/bob/carol/david)\nvalidated 5 task(s)",
        "stderr": ""
      },
      "after": {
        "phase": "after",
        "ok": false,
        "stdout": "[+] Seeded 20 categories\n  [+] Seeded 1589 papers\n  [+] Created demo user (demo@arxiv.local / demodemo)\n  [+] Seeded 4 benchmark users (alice/bob/carol/david)",
        "stderr": "arxiv.library_add_paper.2604_09004: after state failed: expected mutation row for arxiv"
      },
      "tasks": [
        {
          "id": "arxiv.library_add_paper.2604_09004",
          "instruction": "Sign in as alice.j@test.com and add arXiv paper 2604.09004 to your library. Then answer with the paper ID and library status.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://arxiv.org/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "paper",
            "id": 436,
            "arxiv_id": "2604.09004",
            "title": "Climate Change Modeling on Terrestrial Exoplanets Using 3D Circulation Models"
          },
          "operation": {
            "action": "add_to_library",
            "folder": "General"
          },
          "expected_answer": {
            "identity": "2604.09004",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "arxiv.library_item_absent"
            },
            "after": {
              "db_predicate": "arxiv.library_item_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "arxiv.library_add_paper.2604_09003",
          "instruction": "Sign in as alice.j@test.com and add arXiv paper 2604.09003 to your library. Then answer with the paper ID and library status.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://arxiv.org/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "paper",
            "id": 435,
            "arxiv_id": "2604.09003",
            "title": "Gravitational Wave Background from Primordial Black Hole Mergers"
          },
          "operation": {
            "action": "add_to_library",
            "folder": "General"
          },
          "expected_answer": {
            "identity": "2604.09003",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "arxiv.library_item_absent"
            },
            "after": {
              "db_predicate": "arxiv.library_item_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "arxiv.library_add_paper.2604_09002",
          "instruction": "Sign in as alice.j@test.com and add arXiv paper 2604.09002 to your library. Then answer with the paper ID and library status.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://arxiv.org/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "paper",
            "id": 434,
            "arxiv_id": "2604.09002",
            "title": "Multi-messenger Observations of Gravitational Wave Sources"
          },
          "operation": {
            "action": "add_to_library",
            "folder": "General"
          },
          "expected_answer": {
            "identity": "2604.09002",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "arxiv.library_item_absent"
            },
            "after": {
              "db_predicate": "arxiv.library_item_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "arxiv.library_add_paper.2604_09001",
          "instruction": "Sign in as alice.j@test.com and add arXiv paper 2604.09001 to your library. Then answer with the paper ID and library status.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://arxiv.org/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "paper",
            "id": 433,
            "arxiv_id": "2604.09001",
            "title": "Gravitational Wave Parameter Estimation Using Neural Posterior Estimation"
          },
          "operation": {
            "action": "add_to_library",
            "folder": "General"
          },
          "expected_answer": {
            "identity": "2604.09001",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "arxiv.library_item_absent"
            },
            "after": {
              "db_predicate": "arxiv.library_item_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "arxiv.library_add_paper.2604_08548",
          "instruction": "Sign in as alice.j@test.com and add arXiv paper 2604.08548 to your library. Then answer with the paper ID and library status.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://arxiv.org/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "paper",
            "id": 432,
            "arxiv_id": "2604.08548",
            "title": "ETCH-X: Robustify Expressive Body Fitting to Clothed Humans with Composable Datasets"
          },
          "operation": {
            "action": "add_to_library",
            "folder": "General"
          },
          "expected_answer": {
            "identity": "2604.08548",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "arxiv.library_item_absent"
            },
            "after": {
              "db_predicate": "arxiv.library_item_exists"
            }
          },
          "difficulty": 7
        }
      ]
    },
    {
      "site": "booking",
      "web_name": "Booking",
      "family": "saved_property_add",
      "count": 5,
      "login_url": "https://www.booking.com/signin.html",
      "login_real_url": true,
      "before": {
        "phase": "before",
        "ok": true,
        "stdout": "[migrate] seeded 68 landmarks\nSeeded: 33 cities, 279 properties, 1277 reviews\n  [+] Ensured amenity combos for task filters\n[+] Seeded benchmark users: Sophie, Kenji, Emma, Carlos\n  [+] Ensured amenity combos for task filters\nvalidated 5 task(s)",
        "stderr": ""
      },
      "after": {
        "phase": "after",
        "ok": false,
        "stdout": "[migrate] seeded 68 landmarks\nSeeded: 33 cities, 279 properties, 1277 reviews\n  [+] Ensured amenity combos for task filters\n[+] Seeded benchmark users: Sophie, Kenji, Emma, Carlos\n  [+] Ensured amenity combos for task filters",
        "stderr": "booking.saved_property_add.tribe_amsterdam_city: after state failed: expected mutation row for booking"
      },
      "tasks": [
        {
          "id": "booking.saved_property_add.tribe_amsterdam_city",
          "instruction": "Sign in as sophie.m@test.com and save the Booking property 'Tribe Amsterdam City'. Then answer with the saved property name.",
          "actor": {
            "email": "sophie.m@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.booking.com/signin.html",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "property",
            "id": 100,
            "name": "Tribe Amsterdam City",
            "slug": "tribe-amsterdam-city-amsterdam"
          },
          "operation": {
            "action": "save_property",
            "list_name": "Saved properties"
          },
          "expected_answer": {
            "identity": "Tribe Amsterdam City",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "booking.saved_property_absent"
            },
            "after": {
              "db_predicate": "booking.saved_property_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "booking.saved_property_add.voco_dubai_the_palm_by_ihg",
          "instruction": "Sign in as sophie.m@test.com and save the Booking property 'voco Dubai The Palm by IHG'. Then answer with the saved property name.",
          "actor": {
            "email": "sophie.m@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.booking.com/signin.html",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "property",
            "id": 10,
            "name": "voco Dubai The Palm by IHG",
            "slug": "voco-dubai-the-palm-by-ihg-dubai"
          },
          "operation": {
            "action": "save_property",
            "list_name": "Saved properties"
          },
          "expected_answer": {
            "identity": "voco Dubai The Palm by IHG",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "booking.saved_property_absent"
            },
            "after": {
              "db_predicate": "booking.saved_property_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "booking.saved_property_add.spark_by_hilton_vienna_donaustadt",
          "instruction": "Sign in as sophie.m@test.com and save the Booking property 'Spark by Hilton Vienna Donaustadt'. Then answer with the saved property name.",
          "actor": {
            "email": "sophie.m@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.booking.com/signin.html",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "property",
            "id": 174,
            "name": "Spark by Hilton Vienna Donaustadt",
            "slug": "spark-by-hilton-vienna-donaustadt-vienna"
          },
          "operation": {
            "action": "save_property",
            "list_name": "Saved properties"
          },
          "expected_answer": {
            "identity": "Spark by Hilton Vienna Donaustadt",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "booking.saved_property_absent"
            },
            "after": {
              "db_predicate": "booking.saved_property_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "booking.saved_property_add.chelsea_hotel_toronto",
          "instruction": "Sign in as sophie.m@test.com and save the Booking property 'Chelsea Hotel Toronto'. Then answer with the saved property name.",
          "actor": {
            "email": "sophie.m@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.booking.com/signin.html",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "property",
            "id": 252,
            "name": "Chelsea Hotel Toronto",
            "slug": "chelsea-hotel-toronto-toronto"
          },
          "operation": {
            "action": "save_property",
            "list_name": "Saved properties"
          },
          "expected_answer": {
            "identity": "Chelsea Hotel Toronto",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "booking.saved_property_absent"
            },
            "after": {
              "db_predicate": "booking.saved_property_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "booking.saved_property_add.fairmont_singapore",
          "instruction": "Sign in as sophie.m@test.com and save the Booking property 'Fairmont Singapore'. Then answer with the saved property name.",
          "actor": {
            "email": "sophie.m@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.booking.com/signin.html",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "property",
            "id": 20,
            "name": "Fairmont Singapore",
            "slug": "fairmont-singapore-singapore"
          },
          "operation": {
            "action": "save_property",
            "list_name": "Saved properties"
          },
          "expected_answer": {
            "identity": "Fairmont Singapore",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "booking.saved_property_absent"
            },
            "after": {
              "db_predicate": "booking.saved_property_exists"
            }
          },
          "difficulty": 7
        }
      ]
    },
    {
      "site": "cambridge_dictionary",
      "web_name": "Cambridge Dictionary",
      "family": "saved_word_add",
      "count": 5,
      "login_url": "https://login.sso.cambridge.org/",
      "login_real_url": true,
      "before": {
        "phase": "before",
        "ok": true,
        "stdout": "Database seeded.\nBenchmark users seeded.\nvalidated 5 task(s)",
        "stderr": ""
      },
      "after": {
        "phase": "after",
        "ok": false,
        "stdout": "Database seeded.\nBenchmark users seeded.",
        "stderr": "cambridge_dictionary.saved_word_add.ambiguous: after state failed: expected mutation row for cambridge_dictionary"
      },
      "tasks": [
        {
          "id": "cambridge_dictionary.saved_word_add.ambiguous",
          "instruction": "Sign in as alice.j@test.com and save the Cambridge Dictionary word 'ambiguous'. Then answer with the saved headword.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://login.sso.cambridge.org/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "word",
            "id": 27,
            "headword": "ambiguous",
            "slug": "ambiguous"
          },
          "operation": {
            "action": "save_word"
          },
          "expected_answer": {
            "identity": "ambiguous",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "cambridge_dictionary.saved_word_absent"
            },
            "after": {
              "db_predicate": "cambridge_dictionary.saved_word_exists"
            }
          },
          "difficulty": 6
        },
        {
          "id": "cambridge_dictionary.saved_word_add.ameliorate",
          "instruction": "Sign in as alice.j@test.com and save the Cambridge Dictionary word 'ameliorate'. Then answer with the saved headword.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://login.sso.cambridge.org/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "word",
            "id": 11,
            "headword": "ameliorate",
            "slug": "ameliorate"
          },
          "operation": {
            "action": "save_word"
          },
          "expected_answer": {
            "identity": "ameliorate",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "cambridge_dictionary.saved_word_absent"
            },
            "after": {
              "db_predicate": "cambridge_dictionary.saved_word_exists"
            }
          },
          "difficulty": 6
        },
        {
          "id": "cambridge_dictionary.saved_word_add.concatenate",
          "instruction": "Sign in as alice.j@test.com and save the Cambridge Dictionary word 'concatenate'. Then answer with the saved headword.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://login.sso.cambridge.org/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "word",
            "id": 13,
            "headword": "concatenate",
            "slug": "concatenate"
          },
          "operation": {
            "action": "save_word"
          },
          "expected_answer": {
            "identity": "concatenate",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "cambridge_dictionary.saved_word_absent"
            },
            "after": {
              "db_predicate": "cambridge_dictionary.saved_word_exists"
            }
          },
          "difficulty": 6
        },
        {
          "id": "cambridge_dictionary.saved_word_add.cryptocurrency",
          "instruction": "Sign in as alice.j@test.com and save the Cambridge Dictionary word 'cryptocurrency'. Then answer with the saved headword.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://login.sso.cambridge.org/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "word",
            "id": 15,
            "headword": "cryptocurrency",
            "slug": "cryptocurrency"
          },
          "operation": {
            "action": "save_word"
          },
          "expected_answer": {
            "identity": "cryptocurrency",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "cambridge_dictionary.saved_word_absent"
            },
            "after": {
              "db_predicate": "cambridge_dictionary.saved_word_exists"
            }
          },
          "difficulty": 6
        },
        {
          "id": "cambridge_dictionary.saved_word_add.dog",
          "instruction": "Sign in as alice.j@test.com and save the Cambridge Dictionary word 'dog'. Then answer with the saved headword.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://login.sso.cambridge.org/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "word",
            "id": 8,
            "headword": "dog",
            "slug": "dog"
          },
          "operation": {
            "action": "save_word"
          },
          "expected_answer": {
            "identity": "dog",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "cambridge_dictionary.saved_word_absent"
            },
            "after": {
              "db_predicate": "cambridge_dictionary.saved_word_exists"
            }
          },
          "difficulty": 6
        }
      ]
    },
    {
      "site": "coursera",
      "web_name": "Coursera",
      "family": "saved_course_add",
      "count": 5,
      "login_url": "https://www.coursera.org/login",
      "login_real_url": true,
      "before": {
        "phase": "before",
        "ok": true,
        "stdout": "Seeded 74 courses, 48 partners\nSeeded benchmark users: ['alice.j@test.com', 'bob.c@test.com', 'carol.d@test.com', 'david.k@test.com']\n  + seeded testimonials on 65 courses\n  + added Gautam Kaul second course\nvalidated 5 task(s)",
        "stderr": ""
      },
      "after": {
        "phase": "after",
        "ok": false,
        "stdout": "Seeded 74 courses, 48 partners\nSeeded benchmark users: ['alice.j@test.com', 'bob.c@test.com', 'carol.d@test.com', 'david.k@test.com']\n  + seeded testimonials on 65 courses\n  + added Gautam Kaul second course",
        "stderr": "coursera.saved_course_add.machine_learning_specialization: after state failed: expected mutation row for coursera"
      },
      "tasks": [
        {
          "id": "coursera.saved_course_add.machine_learning_specialization",
          "instruction": "Sign in as alice.j@test.com and save the Coursera course 'Machine Learning Specialization' to your wishlist. Then answer with the saved course title.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.coursera.org/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "course",
            "id": 35,
            "title": "Machine Learning Specialization",
            "slug": "machine-learning-specialization"
          },
          "operation": {
            "action": "save_course"
          },
          "expected_answer": {
            "identity": "Machine Learning Specialization",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "coursera.saved_course_absent"
            },
            "after": {
              "db_predicate": "coursera.saved_course_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "coursera.saved_course_add.the_science_of_well_being",
          "instruction": "Sign in as alice.j@test.com and save the Coursera course 'The Science of Well-Being' to your wishlist. Then answer with the saved course title.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.coursera.org/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "course",
            "id": 72,
            "title": "The Science of Well-Being",
            "slug": "the-science-of-well-being"
          },
          "operation": {
            "action": "save_course"
          },
          "expected_answer": {
            "identity": "The Science of Well-Being",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "coursera.saved_course_absent"
            },
            "after": {
              "db_predicate": "coursera.saved_course_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "coursera.saved_course_add.introduction_to_psychology",
          "instruction": "Sign in as alice.j@test.com and save the Coursera course 'Introduction to Psychology' to your wishlist. Then answer with the saved course title.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.coursera.org/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "course",
            "id": 3,
            "title": "Introduction to Psychology",
            "slug": "introduction-to-psychology"
          },
          "operation": {
            "action": "save_course"
          },
          "expected_answer": {
            "identity": "Introduction to Psychology",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "coursera.saved_course_absent"
            },
            "after": {
              "db_predicate": "coursera.saved_course_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "coursera.saved_course_add.master_of_computer_science",
          "instruction": "Sign in as alice.j@test.com and save the Coursera course 'Master of Computer Science' to your wishlist. Then answer with the saved course title.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.coursera.org/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "course",
            "id": 55,
            "title": "Master of Computer Science",
            "slug": "master-computer-science-uiuc"
          },
          "operation": {
            "action": "save_course"
          },
          "expected_answer": {
            "identity": "Master of Computer Science",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "coursera.saved_course_absent"
            },
            "after": {
              "db_predicate": "coursera.saved_course_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "coursera.saved_course_add.python_for_everybody",
          "instruction": "Sign in as alice.j@test.com and save the Coursera course 'Python for Everybody' to your wishlist. Then answer with the saved course title.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.coursera.org/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "course",
            "id": 14,
            "title": "Python for Everybody",
            "slug": "python-for-everybody"
          },
          "operation": {
            "action": "save_course"
          },
          "expected_answer": {
            "identity": "Python for Everybody",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "coursera.saved_course_absent"
            },
            "after": {
              "db_predicate": "coursera.saved_course_exists"
            }
          },
          "difficulty": 7
        }
      ]
    },
    {
      "site": "espn",
      "web_name": "ESPN",
      "family": "favorite_team_add",
      "count": 5,
      "login_url": "https://www.espn.com/login",
      "login_real_url": true,
      "before": {
        "phase": "before",
        "ok": true,
        "stdout": "validated 5 task(s)",
        "stderr": ""
      },
      "after": {
        "phase": "after",
        "ok": false,
        "stdout": "",
        "stderr": "espn.favorite_team_add.baltimore_orioles: after state failed: expected mutation row for espn"
      },
      "tasks": [
        {
          "id": "espn.favorite_team_add.baltimore_orioles",
          "instruction": "Sign in as alice.j@test.com and add Baltimore Orioles to your ESPN favorites. Then answer with the favorite team name.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.espn.com/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "team",
            "id": 95,
            "full_name": "Baltimore Orioles",
            "slug": "baltimore-orioles"
          },
          "operation": {
            "action": "favorite_team",
            "item_type": "team"
          },
          "expected_answer": {
            "identity": "Baltimore Orioles",
            "favorited": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "espn.favorite_team_absent"
            },
            "after": {
              "db_predicate": "espn.favorite_team_exists"
            }
          },
          "difficulty": 6
        },
        {
          "id": "espn.favorite_team_add.kansas_city_royals",
          "instruction": "Sign in as alice.j@test.com and add Kansas City Royals to your ESPN favorites. Then answer with the favorite team name.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.espn.com/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "team",
            "id": 103,
            "full_name": "Kansas City Royals",
            "slug": "kansas-city-royals"
          },
          "operation": {
            "action": "favorite_team",
            "item_type": "team"
          },
          "expected_answer": {
            "identity": "Kansas City Royals",
            "favorited": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "espn.favorite_team_absent"
            },
            "after": {
              "db_predicate": "espn.favorite_team_exists"
            }
          },
          "difficulty": 6
        },
        {
          "id": "espn.favorite_team_add.houston_astros",
          "instruction": "Sign in as alice.j@test.com and add Houston Astros to your ESPN favorites. Then answer with the favorite team name.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.espn.com/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "team",
            "id": 105,
            "full_name": "Houston Astros",
            "slug": "houston-astros"
          },
          "operation": {
            "action": "favorite_team",
            "item_type": "team"
          },
          "expected_answer": {
            "identity": "Houston Astros",
            "favorited": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "espn.favorite_team_absent"
            },
            "after": {
              "db_predicate": "espn.favorite_team_exists"
            }
          },
          "difficulty": 6
        },
        {
          "id": "espn.favorite_team_add.atlanta_braves",
          "instruction": "Sign in as alice.j@test.com and add Atlanta Braves to your ESPN favorites. Then answer with the favorite team name.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.espn.com/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "team",
            "id": 110,
            "full_name": "Atlanta Braves",
            "slug": "atlanta-braves"
          },
          "operation": {
            "action": "favorite_team",
            "item_type": "team"
          },
          "expected_answer": {
            "identity": "Atlanta Braves",
            "favorited": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "espn.favorite_team_absent"
            },
            "after": {
              "db_predicate": "espn.favorite_team_exists"
            }
          },
          "difficulty": 6
        },
        {
          "id": "espn.favorite_team_add.milwaukee_brewers",
          "instruction": "Sign in as alice.j@test.com and add Milwaukee Brewers to your ESPN favorites. Then answer with the favorite team name.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://www.espn.com/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "team",
            "id": 118,
            "full_name": "Milwaukee Brewers",
            "slug": "milwaukee-brewers"
          },
          "operation": {
            "action": "favorite_team",
            "item_type": "team"
          },
          "expected_answer": {
            "identity": "Milwaukee Brewers",
            "favorited": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "espn.favorite_team_absent"
            },
            "after": {
              "db_predicate": "espn.favorite_team_exists"
            }
          },
          "difficulty": 6
        }
      ]
    },
    {
      "site": "github",
      "web_name": "GitHub",
      "family": "repo_star_add",
      "count": 5,
      "login_url": "https://github.com/login",
      "login_real_url": true,
      "before": {
        "phase": "before",
        "ok": true,
        "stdout": "Database seeded successfully.\nvalidated 5 task(s)",
        "stderr": ""
      },
      "after": {
        "phase": "after",
        "ok": false,
        "stdout": "Database seeded successfully.",
        "stderr": "github.repo_star_add.torvalds_linux: after state failed: expected mutation row for github"
      },
      "tasks": [
        {
          "id": "github.repo_star_add.torvalds_linux",
          "instruction": "Sign in as alice.j@test.com and star the GitHub repository torvalds/linux. Then answer with the starred repository full name.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://github.com/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "repository",
            "id": 2,
            "full_name": "torvalds/linux"
          },
          "operation": {
            "action": "star_repository"
          },
          "expected_answer": {
            "identity": "torvalds/linux",
            "starred": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "github.repo_star_absent"
            },
            "after": {
              "db_predicate": "github.repo_star_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "github.repo_star_add.microsoft_vscode",
          "instruction": "Sign in as alice.j@test.com and star the GitHub repository microsoft/vscode. Then answer with the starred repository full name.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://github.com/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "repository",
            "id": 1,
            "full_name": "microsoft/vscode"
          },
          "operation": {
            "action": "star_repository"
          },
          "expected_answer": {
            "identity": "microsoft/vscode",
            "starred": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "github.repo_star_absent"
            },
            "after": {
              "db_predicate": "github.repo_star_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "github.repo_star_add.huggingface_transformers",
          "instruction": "Sign in as alice.j@test.com and star the GitHub repository huggingface/transformers. Then answer with the starred repository full name.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://github.com/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "repository",
            "id": 9,
            "full_name": "huggingface/transformers"
          },
          "operation": {
            "action": "star_repository"
          },
          "expected_answer": {
            "identity": "huggingface/transformers",
            "starred": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "github.repo_star_absent"
            },
            "after": {
              "db_predicate": "github.repo_star_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "github.repo_star_add.golang_go",
          "instruction": "Sign in as alice.j@test.com and star the GitHub repository golang/go. Then answer with the starred repository full name.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://github.com/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "repository",
            "id": 6,
            "full_name": "golang/go"
          },
          "operation": {
            "action": "star_repository"
          },
          "expected_answer": {
            "identity": "golang/go",
            "starred": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "github.repo_star_absent"
            },
            "after": {
              "db_predicate": "github.repo_star_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "github.repo_star_add.kubernetes_kubernetes",
          "instruction": "Sign in as alice.j@test.com and star the GitHub repository kubernetes/kubernetes. Then answer with the starred repository full name.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://github.com/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "repository",
            "id": 8,
            "full_name": "kubernetes/kubernetes"
          },
          "operation": {
            "action": "star_repository"
          },
          "expected_answer": {
            "identity": "kubernetes/kubernetes",
            "starred": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "github.repo_star_absent"
            },
            "after": {
              "db_predicate": "github.repo_star_exists"
            }
          },
          "difficulty": 7
        }
      ]
    },
    {
      "site": "google_flights",
      "web_name": "Google Flights",
      "family": "tracked_flight_add",
      "count": 5,
      "login_url": "https://accounts.google.com/",
      "login_real_url": true,
      "before": {
        "phase": "before",
        "ok": true,
        "stdout": "Seeded 93 airports and 126872 flights.\nBenchmark users seeded: alice, bob, carol, david\nvalidated 5 task(s)",
        "stderr": ""
      },
      "after": {
        "phase": "after",
        "ok": false,
        "stdout": "Seeded 93 airports and 126872 flights.\nBenchmark users seeded: alice, bob, carol, david",
        "stderr": "google_flights.tracked_flight_add.aa9009: after state failed: expected mutation row for google_flights"
      },
      "tasks": [
        {
          "id": "google_flights.tracked_flight_add.aa9009",
          "instruction": "Sign in as alice.j@test.com and track flight AA9009 from TLV to VCE. Then answer with the tracked flight number.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://accounts.google.com/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "flight",
            "id": 125137,
            "flight_number": "AA9009"
          },
          "operation": {
            "action": "track_flight"
          },
          "expected_answer": {
            "identity": "AA9009",
            "tracked": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "google_flights.tracked_flight_absent"
            },
            "after": {
              "db_predicate": "google_flights.tracked_flight_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "google_flights.tracked_flight_add.ib3614",
          "instruction": "Sign in as alice.j@test.com and track flight IB3614 from TLV to VCE. Then answer with the tracked flight number.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://accounts.google.com/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "flight",
            "id": 125131,
            "flight_number": "IB3614"
          },
          "operation": {
            "action": "track_flight"
          },
          "expected_answer": {
            "identity": "IB3614",
            "tracked": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "google_flights.tracked_flight_absent"
            },
            "after": {
              "db_predicate": "google_flights.tracked_flight_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "google_flights.tracked_flight_add.qr6421",
          "instruction": "Sign in as alice.j@test.com and track flight QR6421 from TLV to VCE. Then answer with the tracked flight number.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://accounts.google.com/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "flight",
            "id": 125134,
            "flight_number": "QR6421"
          },
          "operation": {
            "action": "track_flight"
          },
          "expected_answer": {
            "identity": "QR6421",
            "tracked": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "google_flights.tracked_flight_absent"
            },
            "after": {
              "db_predicate": "google_flights.tracked_flight_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "google_flights.tracked_flight_add.ba7003",
          "instruction": "Sign in as alice.j@test.com and track flight BA7003 from TLV to VCE. Then answer with the tracked flight number.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://accounts.google.com/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "flight",
            "id": 125124,
            "flight_number": "BA7003"
          },
          "operation": {
            "action": "track_flight"
          },
          "expected_answer": {
            "identity": "BA7003",
            "tracked": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "google_flights.tracked_flight_absent"
            },
            "after": {
              "db_predicate": "google_flights.tracked_flight_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "google_flights.tracked_flight_add.lh6184",
          "instruction": "Sign in as alice.j@test.com and track flight LH6184 from TLV to VCE. Then answer with the tracked flight number.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://accounts.google.com/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "flight",
            "id": 125129,
            "flight_number": "LH6184"
          },
          "operation": {
            "action": "track_flight"
          },
          "expected_answer": {
            "identity": "LH6184",
            "tracked": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "google_flights.tracked_flight_absent"
            },
            "after": {
              "db_predicate": "google_flights.tracked_flight_exists"
            }
          },
          "difficulty": 7
        }
      ]
    },
    {
      "site": "google_map",
      "web_name": "Google Maps",
      "family": "saved_place_add",
      "count": 5,
      "login_url": "https://accounts.google.com/",
      "login_real_url": true,
      "before": {
        "phase": "before",
        "ok": true,
        "stdout": "Seeded 440 places\nSeeded 81 task-specific places and 9 routes.\nBenchmark users seeded: alice.j, bob.c, carol.d, david.k\nvalidated 5 task(s)",
        "stderr": ""
      },
      "after": {
        "phase": "after",
        "ok": false,
        "stdout": "Seeded 440 places\nSeeded 81 task-specific places and 9 routes.\nBenchmark users seeded: alice.j, bob.c, carol.d, david.k",
        "stderr": "google_map.saved_place_add.buckingham_palace: after state failed: expected mutation row for google_map"
      },
      "tasks": [
        {
          "id": "google_map.saved_place_add.buckingham_palace",
          "instruction": "Sign in as alice.j@test.com and save the Google Maps place 'Buckingham Palace' to your saved places. Then answer with the saved place name.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://accounts.google.com/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "place",
            "id": 19,
            "name": "Buckingham Palace",
            "slug": "buckingham-palace",
            "list_id": 1
          },
          "operation": {
            "action": "save_place",
            "list_id": 1
          },
          "expected_answer": {
            "identity": "Buckingham Palace",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "google_map.saved_place_absent"
            },
            "after": {
              "db_predicate": "google_map.saved_place_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "google_map.saved_place_add.brooklyn_bridge",
          "instruction": "Sign in as alice.j@test.com and save the Google Maps place 'Brooklyn Bridge' to your saved places. Then answer with the saved place name.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://accounts.google.com/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "place",
            "id": 5,
            "name": "Brooklyn Bridge",
            "slug": "brooklyn-bridge",
            "list_id": 1
          },
          "operation": {
            "action": "save_place",
            "list_id": 1
          },
          "expected_answer": {
            "identity": "Brooklyn Bridge",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "google_map.saved_place_absent"
            },
            "after": {
              "db_predicate": "google_map.saved_place_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "google_map.saved_place_add.galleria_vittorio_emanuele_ii",
          "instruction": "Sign in as alice.j@test.com and save the Google Maps place 'Galleria Vittorio Emanuele II' to your saved places. Then answer with the saved place name.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://accounts.google.com/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "place",
            "id": 127,
            "name": "Galleria Vittorio Emanuele II",
            "slug": "galleria-vittorio-emanuele",
            "list_id": 1
          },
          "operation": {
            "action": "save_place",
            "list_id": 1
          },
          "expected_answer": {
            "identity": "Galleria Vittorio Emanuele II",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "google_map.saved_place_absent"
            },
            "after": {
              "db_predicate": "google_map.saved_place_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "google_map.saved_place_add.main_square_rynek_główny",
          "instruction": "Sign in as alice.j@test.com and save the Google Maps place 'Main Square (Rynek Główny)' to your saved places. Then answer with the saved place name.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://accounts.google.com/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "place",
            "id": 136,
            "name": "Main Square (Rynek Główny)",
            "slug": "market-square-krakow",
            "list_id": 1
          },
          "operation": {
            "action": "save_place",
            "list_id": 1
          },
          "expected_answer": {
            "identity": "Main Square (Rynek Główny)",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "google_map.saved_place_absent"
            },
            "after": {
              "db_predicate": "google_map.saved_place_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "google_map.saved_place_add.cn_tower",
          "instruction": "Sign in as alice.j@test.com and save the Google Maps place 'CN Tower' to your saved places. Then answer with the saved place name.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://accounts.google.com/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "place",
            "id": 110,
            "name": "CN Tower",
            "slug": "cn-tower",
            "list_id": 1
          },
          "operation": {
            "action": "save_place",
            "list_id": 1
          },
          "expected_answer": {
            "identity": "CN Tower",
            "saved": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "google_map.saved_place_absent"
            },
            "after": {
              "db_predicate": "google_map.saved_place_exists"
            }
          },
          "difficulty": 7
        }
      ]
    },
    {
      "site": "huggingface",
      "web_name": "Hugging Face",
      "family": "repo_like_add",
      "count": 5,
      "login_url": "https://huggingface.co/login",
      "login_real_url": true,
      "before": {
        "phase": "before",
        "ok": true,
        "stdout": "Seeding database...\n  ✓ 39 tasks\n  ✓ 84 authors\n  ✓ 140 repositories\n  ✓ 12 discussions\n  ✓ 1 collections\nSeeding benchmark users...\n  ✓ 4 benchmark users created\n  ✓ Likes, collections, endpoints, discussions seeded\nvalidated 5 task(s)",
        "stderr": ""
      },
      "after": {
        "phase": "after",
        "ok": false,
        "stdout": "Seeding database...\n  ✓ 39 tasks\n  ✓ 84 authors\n  ✓ 140 repositories\n  ✓ 12 discussions\n  ✓ 1 collections\nSeeding benchmark users...\n  ✓ 4 benchmark users created\n  ✓ Likes, collections, endpoints, discussions seeded",
        "stderr": "huggingface.repo_like_add.dslim_bert_base_ner_2022: after state failed: expected mutation row for huggingface"
      },
      "tasks": [
        {
          "id": "huggingface.repo_like_add.dslim_bert_base_ner_2022",
          "instruction": "Sign in as alice.j@test.com and like the Hugging Face repository dslim/bert-base-NER-2022. Then answer with the liked repository slug.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://huggingface.co/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "repository",
            "id": 79,
            "slug": "dslim/bert-base-NER-2022",
            "repo_type": "model"
          },
          "operation": {
            "action": "like_repository"
          },
          "expected_answer": {
            "identity": "dslim/bert-base-NER-2022",
            "liked": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "huggingface.repo_like_absent"
            },
            "after": {
              "db_predicate": "huggingface.repo_like_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "huggingface.repo_like_add.stabilityai_stable_video_diffusion_xt_2",
          "instruction": "Sign in as alice.j@test.com and like the Hugging Face repository stabilityai/stable-video-diffusion-xt-2. Then answer with the liked repository slug.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://huggingface.co/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "repository",
            "id": 58,
            "slug": "stabilityai/stable-video-diffusion-xt-2",
            "repo_type": "model"
          },
          "operation": {
            "action": "like_repository"
          },
          "expected_answer": {
            "identity": "stabilityai/stable-video-diffusion-xt-2",
            "liked": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "huggingface.repo_like_absent"
            },
            "after": {
              "db_predicate": "huggingface.repo_like_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "huggingface.repo_like_add.dreamfusion_ai_dreamfusion_sd_v1",
          "instruction": "Sign in as alice.j@test.com and like the Hugging Face repository dreamfusion-ai/dreamfusion-sd-v1. Then answer with the liked repository slug.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://huggingface.co/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "repository",
            "id": 61,
            "slug": "dreamfusion-ai/dreamfusion-sd-v1",
            "repo_type": "model"
          },
          "operation": {
            "action": "like_repository"
          },
          "expected_answer": {
            "identity": "dreamfusion-ai/dreamfusion-sd-v1",
            "liked": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "huggingface.repo_like_absent"
            },
            "after": {
              "db_predicate": "huggingface.repo_like_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "huggingface.repo_like_add.coqui_xtts_v2",
          "instruction": "Sign in as alice.j@test.com and like the Hugging Face repository coqui/XTTS-v2. Then answer with the liked repository slug.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://huggingface.co/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "repository",
            "id": 26,
            "slug": "coqui/XTTS-v2",
            "repo_type": "model"
          },
          "operation": {
            "action": "like_repository"
          },
          "expected_answer": {
            "identity": "coqui/XTTS-v2",
            "liked": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "huggingface.repo_like_absent"
            },
            "after": {
              "db_predicate": "huggingface.repo_like_exists"
            }
          },
          "difficulty": 7
        },
        {
          "id": "huggingface.repo_like_add.qwen_qwen2_5_7b_instruct",
          "instruction": "Sign in as alice.j@test.com and like the Hugging Face repository Qwen/Qwen2.5-7B-Instruct. Then answer with the liked repository slug.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://huggingface.co/login",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "repository",
            "id": 9,
            "slug": "Qwen/Qwen2.5-7B-Instruct",
            "repo_type": "model"
          },
          "operation": {
            "action": "like_repository"
          },
          "expected_answer": {
            "identity": "Qwen/Qwen2.5-7B-Instruct",
            "liked": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "huggingface.repo_like_absent"
            },
            "after": {
              "db_predicate": "huggingface.repo_like_exists"
            }
          },
          "difficulty": 7
        }
      ]
    },
    {
      "site": "wolfram_alpha",
      "web_name": "Wolfram Alpha",
      "family": "favorite_topic_add",
      "count": 5,
      "login_url": "https://user.wolfram.com/",
      "login_real_url": true,
      "before": {
        "phase": "before",
        "ok": true,
        "stdout": "Database seeded.\nBenchmark users seeded.\nvalidated 5 task(s)",
        "stderr": ""
      },
      "after": {
        "phase": "after",
        "ok": false,
        "stdout": "Database seeded.\nBenchmark users seeded.",
        "stderr": "wolfram_alpha.favorite_topic_add.astronomy: after state failed: expected mutation row for wolfram_alpha"
      },
      "tasks": [
        {
          "id": "wolfram_alpha.favorite_topic_add.astronomy",
          "instruction": "Sign in as alice.j@test.com and add the Wolfram Alpha topic 'Astronomy' to favorites. Then answer with the favorite topic name.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://user.wolfram.com/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "topic",
            "id": 11,
            "name": "Astronomy",
            "slug": "astronomy"
          },
          "operation": {
            "action": "favorite_topic"
          },
          "expected_answer": {
            "identity": "Astronomy",
            "favorited": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "wolfram_alpha.favorite_topic_absent"
            },
            "after": {
              "db_predicate": "wolfram_alpha.favorite_topic_exists"
            }
          },
          "difficulty": 6
        },
        {
          "id": "wolfram_alpha.favorite_topic_add.chemistry",
          "instruction": "Sign in as alice.j@test.com and add the Wolfram Alpha topic 'Chemistry' to favorites. Then answer with the favorite topic name.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://user.wolfram.com/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "topic",
            "id": 10,
            "name": "Chemistry",
            "slug": "chemistry"
          },
          "operation": {
            "action": "favorite_topic"
          },
          "expected_answer": {
            "identity": "Chemistry",
            "favorited": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "wolfram_alpha.favorite_topic_absent"
            },
            "after": {
              "db_predicate": "wolfram_alpha.favorite_topic_exists"
            }
          },
          "difficulty": 6
        },
        {
          "id": "wolfram_alpha.favorite_topic_add.finance",
          "instruction": "Sign in as alice.j@test.com and add the Wolfram Alpha topic 'Finance' to favorites. Then answer with the favorite topic name.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://user.wolfram.com/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "topic",
            "id": 17,
            "name": "Finance",
            "slug": "finance"
          },
          "operation": {
            "action": "favorite_topic"
          },
          "expected_answer": {
            "identity": "Finance",
            "favorited": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "wolfram_alpha.favorite_topic_absent"
            },
            "after": {
              "db_predicate": "wolfram_alpha.favorite_topic_exists"
            }
          },
          "difficulty": 6
        },
        {
          "id": "wolfram_alpha.favorite_topic_add.personal_health",
          "instruction": "Sign in as alice.j@test.com and add the Wolfram Alpha topic 'Personal Health' to favorites. Then answer with the favorite topic name.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://user.wolfram.com/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "topic",
            "id": 19,
            "name": "Personal Health",
            "slug": "personal-health"
          },
          "operation": {
            "action": "favorite_topic"
          },
          "expected_answer": {
            "identity": "Personal Health",
            "favorited": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "wolfram_alpha.favorite_topic_absent"
            },
            "after": {
              "db_predicate": "wolfram_alpha.favorite_topic_exists"
            }
          },
          "difficulty": 6
        },
        {
          "id": "wolfram_alpha.favorite_topic_add.physics",
          "instruction": "Sign in as alice.j@test.com and add the Wolfram Alpha topic 'Physics' to favorites. Then answer with the favorite topic name.",
          "actor": {
            "email": "alice.j@test.com",
            "password": "TestPass123!"
          },
          "login": {
            "required": true,
            "strategy": "ui_credentials",
            "login_url": "https://user.wolfram.com/",
            "post_login_assertion": "authenticated user session is active"
          },
          "target_entity": {
            "kind": "topic",
            "id": 9,
            "name": "Physics",
            "slug": "physics"
          },
          "operation": {
            "action": "favorite_topic"
          },
          "expected_answer": {
            "identity": "Physics",
            "favorited": true
          },
          "state_transition": {
            "before": {
              "db_predicate": "wolfram_alpha.favorite_topic_absent"
            },
            "after": {
              "db_predicate": "wolfram_alpha.favorite_topic_exists"
            }
          },
          "difficulty": 6
        }
      ]
    }
  ],
  "summary": {
    "before_pass": 13,
    "after_expected_fail": 13,
    "real_login_url": 13
  }
};
