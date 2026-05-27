#!/usr/bin/env python3
"""Generate R11 GUI tasks for /orders + /help. Appends to tasks.jsonl.

Tasks reference the benchmark users (alice.j@test.com etc., PINNED password
'TestPass123!') and the deterministic seeded help categories / articles.
Auth-required tasks include the credentials inline so the agent can log in;
help-browse tasks are unauthenticated (real amazon.com /gp/help is public).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS_FILE = os.path.join(HERE, 'tasks.jsonl')

ALICE = ('alice.j@test.com', 'TestPass123!')

ORDERS_TASKS = [
    # --- /orders hub navigation & filter ---
    ("Sign in as {alice} (password {pw}) and open Your Orders. Report how many orders are shown under the 'All orders' filter.",),
    ("Sign in as {alice} (password {pw}) and open Your Orders. Click the 'Not yet shipped' filter and report how many orders match.",),
    ("Sign in as {alice} (password {pw}) and open Your Orders. Click the 'Delivered' filter and report how many orders match.",),
    ("Sign in as {alice} (password {pw}) and open Your Orders. Click the 'Cancelled' filter and report how many orders match.",),
    ("Sign in as {alice} (password {pw}) and open Your Orders. Filter by year 2026 and report how many orders were placed in that year.",),
    ("Sign in as {alice} (password {pw}) and open Your Orders. Use the 'Search all orders' box to search for 'Sony' and report how many orders contain a Sony product.",),
    ("Sign in as {alice} (password {pw}) and open Your Orders. Use the 'Search all orders' box to search for 'Echo' and report the order numbers of matching orders.",),
    ("Sign in as {alice} (password {pw}) and open Your Orders. Search for 'Atomic Habits' and report how many orders contain that title.",),
    ("Sign in as {alice} (password {pw}) and open Your Orders. Report the total amount of the most recent order.",),
    ("Sign in as {alice} (password {pw}) and open Your Orders. Report the status of the most recent order.",),

    # --- Order detail / track / invoice ---
    ("Sign in as {alice} (password {pw}), open Your Orders, click the most recent order's 'View order details', and report the shipping address (street line).",),
    ("Sign in as {alice} (password {pw}), open Your Orders, click 'Track package' on the most recent order, and report the carrier name shown.",),
    ("Sign in as {alice} (password {pw}), open Your Orders, click 'Track package' on the most recent order, and report the tracking ID.",),
    ("Sign in as {alice} (password {pw}), open Your Orders, click 'View invoice' on the most recent order, and report the grand total on the invoice.",),
    ("Sign in as {alice} (password {pw}), open Your Orders, click 'View invoice' on the most recent order, and report the payment method (e.g. Visa ending 4242).",),
    ("Sign in as {alice} (password {pw}), open Your Orders, click 'View invoice' on the most recent order, and report the estimated tax amount.",),

    # --- Buy it again ---
    ("Sign in as {alice} (password {pw}) and open the 'Buy It Again' page from Your Orders. Report how many products are listed.",),
    ("Sign in as {alice} (password {pw}), open 'Buy It Again', and report the name of the most recently purchased product.",),
    ("Sign in as {alice} (password {pw}), open 'Buy It Again', find the Roomba and click 'Add to cart'. Report whether the cart count increased.",),
    ("Sign in as {alice} (password {pw}), open 'Buy It Again', and report which product shows the highest 'Bought N times' count.",),

    # --- Leave seller feedback ---
    ("Sign in as {alice} (password {pw}), open the most recent delivered order, click 'Leave seller feedback', leave a 5-star rating with comment 'Excellent seller!', and confirm the success flash appears.",),
    ("Sign in as {alice} (password {pw}), open Your Orders, find a delivered order, click 'Leave seller feedback' and report what seller name is pre-filled.",),
    ("Sign in as {alice} (password {pw}), open Your Orders, find a delivered order, click 'Leave seller feedback' — report whether the 5-star option is selected by default.",),

    # --- Cancel / return flow ---
    ("Sign in as {alice} (password {pw}), open Your Orders, filter by 'Not yet shipped', and try to cancel the most recent processing order. Report the flash message shown.",),
    ("Sign in as {alice} (password {pw}), open Your Orders, filter by 'Delivered', open the first delivered order, click 'Return or replace items', and report how many return-reason options are available in the dropdown.",),

    # --- Cross-user / Bob ---
    ("Sign in as bob.c@test.com (password TestPass123!) and open Your Orders. Report how many orders Bob has.",),
    ("Sign in as bob.c@test.com (password TestPass123!) and open Your Orders. Report the total of Bob's processing order.",),
    ("Sign in as bob.c@test.com (password TestPass123!), open Your Orders, click 'Track package' on a shipped/delivered order and report the first event in the shipment timeline.",),

    # --- Cross-user / Carol & David ---
    ("Sign in as carol.d@test.com (password TestPass123!) and open Your Orders. Report which year filters are available.",),
    ("Sign in as david.k@test.com (password TestPass123!) and open Your Orders. Click the 'Cancelled' filter and report how many orders are listed.",),
]

HELP_TASKS = [
    # --- /help index ---
    ("Open Customer Service at /help and report how many top-level help topic categories are shown.",),
    ("Open /help and list the names of the help topic categories.",),
    ("Open /help and search for 'refund'. Report how many articles match.",),
    ("Open /help and search for 'tracking'. Report the title of the top result.",),
    ("Open /help and search for 'gift card'. Report whether any articles are returned.",),
    ("Open /help and report how many 'Popular help articles' are shown in the popular section.",),

    # --- Category browse ---
    ("Open /help, click the 'Your Orders' category, and report how many articles it contains.",),
    ("Open /help, click 'Returns & Refunds', and report the title of the first article listed.",),
    ("Open /help, click 'Manage Prime', and report how many articles it contains.",),
    ("Open /help, click 'Payment Settings', and report whether 'Pay with Points' is listed there.",),
    ("Open /help, click 'Shipping & Delivery', and report the article that lists carrier phone numbers.",),
    ("Open /help, click 'Account Settings', and report whether 'Two-Step Verification' is listed there.",),
    ("Open /help, click 'Devices & Digital Services', and report how many articles it contains.",),
    ("Open /help, click 'Shopping on Amazon', and report whether 'About Amazon Business' is listed.",),

    # --- Article detail ---
    ("Open /help and read the article 'Track Your Package'. Report what page Amazon directs you to start tracking.",),
    ("Open /help and read 'About Our Returns Policies'. Report the standard return window in days.",),
    ("Open /help and read 'Amazon Prime Price'. Report the monthly Prime price.",),
    ("Open /help and read 'Carrier Contact Information'. Report the UPS phone number.",),
    ("Open /help and read 'About Shipping Rates'. Report the free-standard-shipping minimum order amount.",),
    ("Open /help and read 'Refunds'. Report how many business days a refund to original payment typically takes.",),
    ("Open /help, open any article, and report whether a 'helpful' count is shown.",),
    ("Open the article 'Two-Step Verification' under Account Settings and report which two methods Amazon lists for receiving codes.",),

    # --- Contact us ---
    ("Open /help/contact and report which three contact methods are offered.",),
    ("Open /help/contact, choose Chat, fill in topic 'order', message 'Package missing', submit, and report the ticket number shown in the success banner.",),
    ("Open /help/contact, choose Email, fill in any email, topic 'prime', message 'Cancel my Prime', submit, and report whether a success banner appears.",),
    ("Open /help/contact, choose Phone, fill in phone '555-0123', topic 'returns', window 'Today, 9am – 12pm', submit, and report the ticket number shown.",),
    ("Open /help/contact?method=phone and report what callback-window options are listed in the dropdown.",),
    ("Open /help/contact?method=email and report what topic options are listed in the topic dropdown.",),

    # --- Cross-link from Help to Orders ---
    ("Open /help, find the 'Where's My Stuff?' article under Your Orders, and report whether it mentions Your Orders.",),
    ("Open /help/category/your-orders and click any article. Report whether the article shows a 'Last updated' date.",),
]


def fmt(template):
    return template.format(alice=ALICE[0], pw=ALICE[1])


def main():
    lines = []
    for i, (q,) in enumerate(ORDERS_TASKS, start=1):
        lines.append({
            'web_name': 'Amazon',
            'id': f'Amazon--orders_{i:03d}',
            'ques': fmt(q),
            'web': 'http://localhost:40001/',
            'upstream_url': 'https://www.amazon.com/',
        })
    for i, (q,) in enumerate(HELP_TASKS, start=1):
        lines.append({
            'web_name': 'Amazon',
            'id': f'Amazon--help_{i:03d}',
            'ques': fmt(q),
            'web': 'http://localhost:40001/',
            'upstream_url': 'https://www.amazon.com/',
        })
    # Filter out any IDs already present (idempotent append)
    existing_ids = set()
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    existing_ids.add(json.loads(line)['id'])
                except Exception:
                    pass
    new_lines = [l for l in lines if l['id'] not in existing_ids]
    with open(TASKS_FILE, 'a') as f:
        for l in new_lines:
            f.write(json.dumps(l, ensure_ascii=False) + '\n')
    print(f'Appended {len(new_lines)} new tasks ({len(lines) - len(new_lines)} already existed)')


if __name__ == '__main__':
    main()
