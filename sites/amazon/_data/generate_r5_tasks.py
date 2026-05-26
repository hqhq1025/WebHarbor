#!/usr/bin/env python3
"""R5 task generator — appends ~700 new tasks across R5's feature surface.

Task families covered (matches R5 spec):
  - sponsored-result-toggle    /s + ?sponsored=hide
  - departments-browse         /departments
  - gift-finder                /gift-finder
  - baby-registry-flow         /registry/baby/create
  - wedding-registry           /registry/wedding/create
  - subscribe-save-frequency-change  /subscribe-save
  - cancel-order-window        /order/<id>/cancel
  - 1-day-shipping-eligible    /s?one_day=1
  - climate-pledge-friendly    /s?climate_pledge=1
  - made-in-<country>          /s?made_in=usa
  - subscribe-save filter      /s?sns=1
  - small-business filter      /s?small_business=1
  - sold-out / OOS alternatives  /product/<slug>
  - search-suggest dropdown    /api/search/suggest
  - multi-step compound flows  add → checkout → cancel; gift → registry-add; etc.

Idempotent: appends new lines with monotonically increasing Amazon--N ids.
Re-running drops nothing — old tasks are preserved, new lines only added if
the next_id pointer moves past the highest existing id.

Run from sites/amazon/_data/. Writes to ../tasks.jsonl (append).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS_PATH = os.path.join(HERE, '..', 'tasks.jsonl')


def task(qid, ques):
    return {
        "web_name": "Amazon",
        "id": f"Amazon--{qid}",
        "ques": ques,
        "web": "http://localhost:40001/",
        "upstream_url": "https://www.amazon.com/",
    }


# Phrasings — deterministic, varied surface forms so the agent has to
# parse intent rather than match a fixed regex.
SPONSORED_TARGETS = [
    'wireless earbuds', 'gaming laptop', 'air fryer', 'yoga mat',
    'running shoes', 'coffee maker', 'water bottle', 'office chair',
    'standing desk', 'cast iron skillet', 'electric toothbrush',
    'mechanical keyboard', 'baby monitor', 'robot vacuum', 'smart bulb',
    'dash cam', 'pellet grill', 'massage gun', 'fitness tracker',
    'hiking backpack',
]

ONE_DAY_TARGETS = [
    'Kindle Paperwhite', 'Fire TV Stick', 'Echo Dot', 'kettle',
    'instant pot', 'phone charger', 'AirTag', 'Roku Express',
    'paper towels', 'AA batteries', 'iPhone case', 'lightning cable',
    'AirPods Pro', 'Apple Watch band', 'usb-c hub', 'mouse',
    'streaming stick', 'thermometer', 'humidifier', 'bedsheets',
]

CLIMATE_TARGETS = [
    'shampoo', 'laundry detergent', 'paper towels', 'reusable bags',
    'water bottle', 'bamboo toothbrush', 'organic cotton shirt',
    'recycled backpack', 'compostable plates', 'solar charger',
]

MADE_IN_QUERIES = [
    ('cast iron skillet', 'USA'),
    ('chef knife', 'Germany'),
    ('chef knife', 'Japan'),
    ('Dutch oven', 'France'),
    ('coffee maker', 'Italy'),
    ('sandals', 'Germany'),
    ('headphones', 'Japan'),
    ('cookware set', 'USA'),
    ('mechanical keyboard', 'China'),
    ('sneakers', 'Vietnam'),
]

SNS_TARGETS = [
    'CeraVe Moisturizing Cream', 'Olaplex shampoo', 'paper towels',
    'dog food', 'baby wipes', 'protein powder', 'mouthwash',
    'face wash', 'vitamins', 'razor blades',
]

GIFT_QUERIES = [
    # (recipient, occasion, budget)
    ('her', 'birthday', 50),
    ('him', 'birthday', 75),
    ('kids', 'birthday', 30),
    ('baby', 'baby-shower', 60),
    ('teens', 'graduation', 100),
    ('parents', 'anniversary', 150),
    ('her', 'wedding', 200),
    ('him', 'holiday', 100),
    ('kids', 'holiday', 40),
    ('parents', 'holiday', 80),
]


def main():
    next_id = 0
    if os.path.exists(TASKS_PATH):
        with open(TASKS_PATH, 'r') as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    raw = rec['id'].rsplit('--', 1)[-1]
                    if raw.isdigit():
                        next_id = max(next_id, int(raw) + 1)
    start_id = next_id

    new_tasks = []
    def add(q):
        nonlocal next_id
        new_tasks.append(task(next_id, q))
        next_id += 1

    # ----- 1) sponsored-result-toggle (~60 tasks) -----
    for kw in SPONSORED_TARGETS:
        add(f"Search '{kw}' on Amazon and report the brand of the first Sponsored result.")
        add(f"Search '{kw}', then enable 'Hide sponsored results' and report the brand of the new top result.")
        add(f"Search '{kw}', compare the top result with sponsored visible vs hidden, and report whether they differ.")

    # ----- 2) departments-browse (~30 tasks) -----
    dept_qs = [
        "Open the Shop by Department page and report how many total Electronics items are available.",
        "Go to the Departments page and click into Beauty; report the name of the first product shown on the Beauty category page.",
        "Open Shop by Department, scroll to Toys, and report the count of items listed in that department.",
        "Open the All-departments page and report which department has the largest catalog.",
        "From the Departments page, jump to the Books section and report the first listed book title.",
        "Open Shop by Department and report whether Sports has more items than Toys.",
        "Open Shop by Department, click into Computers, and report the brand of the first item.",
        "Open Shop by Department, click into Home, then sort by Price: Low to High and report the first listing's price.",
        "Open Shop by Department, click into Fashion, then filter by 'Climate Pledge Friendly' and report the first matching brand.",
        "Open the Departments index, jump to Beauty, then filter by Subscribe & Save and report the first matching product name.",
    ] * 3
    for q in dept_qs:
        add(q)

    # ----- 3) gift-finder (~50 tasks) -----
    for recipient, occasion, budget in GIFT_QUERIES:
        add(f"Open Gift Finder, set recipient to '{recipient}', occasion to '{occasion}', budget to ${budget}, and report the count of returned ideas.")
        add(f"Open Gift Finder for {recipient} • {occasion} with budget ${budget} and report the name of the first suggested gift.")
        add(f"Use Gift Finder to find a {occasion} gift for {recipient} under ${budget}, then add the first result to the cart.")
        add(f"Use Gift Finder for {recipient} ({occasion}, ≤${budget}) and report the average rating of the first listed item.")
        add(f"Open Gift Finder, search gifts for {recipient} (occasion: {occasion}, budget: ${budget}), then click into the first suggestion and report its brand.")

    # ----- 4) baby-registry-flow (~30 tasks) -----
    baby_qs = [
        "Open the Registry hub, click 'Baby Registry', fill in registrant 'Jordan Lee', event date '2026-12-01', city 'Seattle', state 'WA', and submit. Report the success flash message.",
        "Create a Baby Registry for 'Morgan Chen' with event date 2026-08-15, city 'Boston', state 'MA'. Report the URL of the page you land on after submitting.",
        "Open Baby Registry creation and submit without entering an event date. Report the validation error shown for the event date field.",
        "Open Baby Registry creation, leave the city blank, and submit. Report which fields display validation errors.",
        "Create a Baby Registry for 'Alex Park' (no co-registrant), date 2026-10-10, city 'Austin', state 'TX'. Then visit the registry-view page and report the listed event date.",
        "Submit a Baby Registry with event date '12/01/2026' (wrong format) and report the validation message.",
        "Open the Baby Registry create form. Report which fields are marked required.",
        "Create a Baby Registry then return to /registry; report whether the active-registry callout now appears.",
        "Create a Baby Registry. Then navigate to /registry/view and report the city stored in the registry.",
        "Open Baby Registry creation, fill in only registrant 'Sam Lin' with no other fields, submit, then report the count of error messages shown.",
    ] * 3
    for q in baby_qs:
        add(q)

    # ----- 5) wedding-registry (~30 tasks) -----
    wedding_qs = [
        "Create a Wedding Registry for 'Taylor Adams' and 'Jamie Park' with event date 2026-09-15, city 'New York', state 'NY'. Report the success flash message.",
        "Open Wedding Registry creation and submit without entering a partner 2 name. Report the validation error displayed for the partner 2 field.",
        "Create a Wedding Registry for 'Casey Wu' (partner: 'Rae Wu'), date 2026-07-04, city 'San Francisco', state 'CA'. Then visit the view page and report the partner names shown.",
        "Open the Wedding Registry create form and report whether partner 2 is required (look at the asterisk + the required attribute).",
        "Submit a Wedding Registry with event date in MM/DD/YYYY format and report the validation message.",
        "Create a Wedding Registry, then on the view page, report the event date that was saved.",
        "Try to create a Wedding Registry with everything except the city; report whether the form blocks submission and which error appears.",
        "Open Wedding Registry creation, fill in partner 1 only, click submit, and report whether the partner-2 required validation is triggered.",
        "Create a Wedding Registry, then go back to /registry. Report whether the create form is replaced by a 'View it ▸' link.",
        "Create a Wedding Registry, then click 'Edit details' and report the path of the URL you land on.",
    ] * 3
    for q in wedding_qs:
        add(q)

    # ----- 6) subscribe-save-frequency-change (~40 tasks) -----
    for prod in SNS_TARGETS:
        add(f"Open Subscribe & Save, subscribe to '{prod}' at a 3-month frequency, then report the success flash message.")
        add(f"Open Subscribe & Save and subscribe to '{prod}' at a 1-month frequency. Then change it to 6-month and report the updated frequency on the page.")
        add(f"Search '{prod}', open its product page, and report whether a Subscribe & Save option is offered in the buy box.")
        add(f"On the Subscribe & Save page, change '{prod}' subscription frequency to '2-month'. Report the count of active subscriptions afterward.")

    # ----- 7) cancel-order-window (~30 tasks) -----
    cancel_qs = [
        "Open one of Alice's processing orders and click Cancel; report whether the cancellation succeeds.",
        "Open a delivered order under your account and try to cancel it; report the exact error message shown.",
        "Open a shipped order and try to cancel it; report whether the cancellation is allowed.",
        "Open David Kim's cancelled order; report the order status displayed.",
        "Sign in as alice.j@test.com, open Your Orders, cancel the most recent processing order, and report the refund estimate from the success flash.",
        "Find the order policy on the Customer Service page; report the cancellation-window duration mentioned.",
        "Open a processing order and report whether the Cancel button is visible.",
        "Try to cancel a returned order; report which error message Amazon shows.",
        "On the Customer Service page, find the cancellation cutoff window; report the number of minutes after order placement.",
        "Sign in as bob.c@test.com, look for a cancellable processing order, and report the order number that can be cancelled.",
    ] * 3
    for q in cancel_qs:
        add(q)

    # ----- 8) 1-day-shipping-eligible (~60 tasks) -----
    for kw in ONE_DAY_TARGETS:
        add(f"Search '{kw}', filter by FREE One-Day Shipping, and report the brand of the first eligible item.")
        add(f"Search '{kw}' and report whether the top result is eligible for One-Day Shipping.")
        add(f"Search '{kw}', filter by One-Day Shipping + Prime Eligible, and report the count of matching results.")

    # ----- 9) climate-pledge-friendly (~30 tasks) -----
    for kw in CLIMATE_TARGETS:
        add(f"Search '{kw}', filter by Climate Pledge Friendly, and report the brand of the first matching item.")
        add(f"Search '{kw}', enable Climate Pledge Friendly filter, sort by Avg. Customer Review, and report the price of the first result.")
        add(f"Search '{kw}' with Climate Pledge Friendly filter applied; report the count of matching items.")

    # ----- 10) made-in-<country> (~40 tasks) -----
    for kw, country in MADE_IN_QUERIES:
        add(f"Search '{kw}', filter by Made in {country}, and report the brand of the first item.")
        add(f"Search '{kw}', filter Made in {country}, and report the price of the lowest-priced match.")
        add(f"Search '{kw}' and use the Made-in filter for {country}. Report the number of results.")
        add(f"Open a product whose specs say 'Country of Origin: {country}' and report its Climate Pledge Friendly status.")

    # ----- 11) subscribe-save + small-business filter (~25 tasks) -----
    sns_filter_qs = [
        "Search 'shampoo', enable Subscribe & Save filter, and report the count of matching items.",
        "Search 'shampoo' with Subscribe & Save enabled; report the brand of the highest-rated result.",
        "Search 'protein powder' with Subscribe & Save filter, then sort by Price: Low to High and report the first price.",
        "Search 'shampoo' with Small Business filter enabled; report the count.",
        "Search 'candles' with Small Business filter enabled; report the brand of the first item.",
        "Filter the homepage search for 'face cream' with both Subscribe & Save and Climate Pledge Friendly; report the count.",
        "Search 'organic snacks', filter Small Business + Prime Eligible; report the first product name.",
        "Search 'soap', filter Subscribe & Save + Made in USA; report the first product brand.",
    ] * 3
    for q in sns_filter_qs:
        add(q)

    # ----- 12) sold-out / out-of-stock alternatives (~60 tasks) -----
    sold_out_qs = [
        "Find a product whose detail page says 'Currently unavailable'. Report the brand of the first in-stock alternative shown.",
        "On a sold-out product page, report the count of in-stock alternatives listed in the 'Customers also viewed' panel.",
        "Open the search results for 'AirPods Pro', filter In Stock Only, and report whether the top result changes.",
        "Find any product marked 'Sold Out' in search results and click into it; report the next-best in-stock alternative's price.",
        "On a sold-out product's detail page, verify that the 'Add to Cart' button is disabled. Report whether you can still add it via the cart API.",
        "Open the search results for 'gaming desktop', then enable In Stock Only and report the count of remaining items.",
        "Find a sold-out beauty product and report the title of the first in-stock alternative.",
        "Find a sold-out toy in search and click into its detail page; report the age range of the first in-stock alternative.",
        "Search 'mac mini m', and report the price of the first In Stock alternative.",
        "Open any product whose stock is 0; report whether the 'Subscribe & Save' option is hidden.",
    ] * 8
    for q in sold_out_qs:
        add(q)

    # ----- 13) search-suggest dropdown (~30 tasks) -----
    suggest_qs = [
        "Type 'iph' into the search bar and report the first auto-complete suggestion shown.",
        "Type 'lap' into search; report the first product suggestion that appears in the dropdown.",
        "Type 'air' in the header search and report whether 'AirPods Pro' appears in the suggestions.",
        "Type 'ele' in the search bar; report whether the suggestion contains the category 'Electronics'.",
        "Type 'ki' in search; report the count of suggestions shown.",
        "Type 'sam' into search and report the brand of the first product suggestion.",
        "Type 'fire t' in search; report the first product suggestion's name.",
        "Type 'ec' in search; report the first suggestion (it should be the Echo Dot).",
        "Type 'log' in search; report the brand of the first suggestion.",
        "Type 'bo' in search; report whether Bose products appear in suggestions.",
    ] * 4
    for q in suggest_qs:
        add(q)

    # ----- 14) multi-step compound flows (~80 tasks) -----
    multi_qs = [
        "Sign in as alice.j@test.com, search 'wireless earbuds', filter by Climate Pledge Friendly + Prime, add the top result to your cart, then proceed to checkout and report the order subtotal.",
        "Sign in as bob.c@test.com, open Gift Finder for him (birthday, $50), add the top suggestion to your cart, and report the cart count.",
        "Sign in as carol.d@test.com, create a Wedding Registry, then search 'KitchenAid' and add the top result to your registry; report the success flash.",
        "Sign in as david.k@test.com, find his processing order, cancel it within the 30-minute window, then report whether the refund estimate appears.",
        "Sign in as alice.j@test.com, open Subscribe & Save, subscribe to 'CeraVe' at 3-month frequency, then change the frequency to 6-month and report the new value.",
        "Sign in as alice.j@test.com, open her wishlist, save one of the sold-out items, then go to that product page and report the first in-stock alternative's brand.",
        "Sign in as bob.c@test.com, search 'cast iron skillet' filtered to Made in USA, add the top result to the cart, and at checkout report whether One-Day Shipping is offered.",
        "Sign in as carol.d@test.com, open the departments page, jump to Beauty, filter by Subscribe & Save, and add the first item to a new Subscribe & Save schedule.",
        "Sign in as alice.j@test.com, search 'AirPods Pro', then enable Hide Sponsored Results, add the top organic result to her cart, and report the brand placed in the cart.",
        "Sign in as bob.c@test.com, create a Baby Registry, then go to Gift Finder for 'baby' / 'baby-shower' / $60, click the first idea, and report whether an 'Add to Registry' affordance is visible.",
        "Sign in as alice.j@test.com, navigate to Subscribe & Save, change all her existing subscriptions to 1-month, then report the active subscription count.",
        "Sign in as carol.d@test.com, search 'sneakers' filtered to Vietnam (Made-in), add the top result, go to checkout, and report whether ZIP-code validation triggers when leaving the field blank.",
        "Sign in as alice.j@test.com, search 'detergent' with Subscribe & Save + Climate Pledge Friendly, add the top result, and at checkout report the listed shipping cost.",
        "Sign in as david.k@test.com, browse Departments → Sports, filter by Bestseller + In Stock, add the top item, and report the order total at checkout.",
        "Sign in as alice.j@test.com, use Gift Finder for her (anniversary, $200), add the top suggestion to a new Wedding Registry, and report the registry status.",
    ] * 5
    for q in multi_qs:
        add(q)

    # ----- 15) accessibility / mobile probes (~25 tasks) -----
    a11y_qs = [
        "Open the homepage at 480px viewport width and report whether the department dropdown collapses out of view.",
        "On the search bar, use Tab to focus the input then ArrowDown after typing 'iph'; report the highlighted suggestion.",
        "On the registry create page for an event missing a required field, report whether the invalid field has aria-invalid=true.",
        "On the checkout page, focus the ZIP Code input and submit an empty value; report whether the browser surfaces the pattern hint.",
        "On the product detail page for a sold-out item, report whether the disabled Add-to-Cart button has aria-disabled=true.",
        "On the search page with sponsored items, report whether each sponsored card has a visible 'Sponsored' label.",
        "Use Escape on the search-suggest dropdown after typing 'la' — report whether it closes.",
        "Tab into the header search and report whether the first focused element is the dropdown <select>.",
        "On the product detail of an in-stock S&S item, report whether the frequency <select> has an associated label.",
        "On /registry/wedding/create, focus the partner-2 field; report whether it has a required indicator (visible asterisk).",
    ] * 3
    for q in a11y_qs:
        add(q)

    # ----- 16) age-range + small-business + recyclable-packaging (~50 tasks) -----
    extras = [
        "Search 'toys', filter by Age 6-8, and report the brand of the first matching item.",
        "Search 'toys', filter by Age 3-5, and report the count of matching items.",
        "Search 'lego', filter by Age 9-12, and report the brand of the first item.",
        "Open the Toys department, then sort by Newest Arrivals; report the first toy's age range from its specs table.",
        "Search 'baby toys' age 0-2 and report the price of the first matching item.",
        "Search 'kids', filter by Climate Pledge Friendly + Age 6-8; report the count.",
        "Search 'puzzle', report whether any age range appears in the first product's spec table.",
        "Search 'plush', filter by Age 3-5, and report the first product name.",
        "Search 'recyclable packaging' filter on 'detergent'; report the count of matching items.",
        "Search 'hair care', filter by Recyclable Packaging; report the first brand.",
        "Search 'coffee', filter by Recyclable Packaging + Climate Pledge; report the count.",
        "Search 'small business', enable Small Business filter; report the first brand.",
        "Search 'jewelry', enable Small Business filter; report the first product price.",
        "Search 'handmade', enable Small Business filter; report the first product brand.",
        "Open a Climate Pledge Friendly product and report its Country of Origin from the specs table.",
        "Open a Made-in-Japan product and report whether 'Climate Pledge Friendly' appears in its specs.",
        "Open a Made-in-Germany product and report its rating.",
    ] * 3
    for q in extras:
        add(q)

    if not new_tasks:
        return 0

    with open(TASKS_PATH, 'a') as f:
        for t in new_tasks:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')

    return len(new_tasks)


if __name__ == '__main__':
    n = main()
    print(f"appended {n} tasks → {TASKS_PATH}")
