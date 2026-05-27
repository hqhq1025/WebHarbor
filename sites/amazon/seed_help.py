#!/usr/bin/env python3
"""R11 help-content + seller-feedback seed.

Populates HelpCategory / HelpArticle / OrderFeedback tables. Idempotent:
each seeder early-returns when target rows already exist so the byte-identical
/reset invariant holds (md5-derived numeric defaults, REFERENCE_DATE only).

Real categories sourced from amazon.com/gp/help/customer/display.html (May 2026):
  - Your Orders, Returns & Refunds, Manage Prime, Payment Settings,
    Carrier Info, Account Settings, Devices & Content, Shopping on Amazon.
"""
import hashlib
from datetime import datetime, timedelta

REFERENCE_DATE = datetime(2026, 4, 15)


def _md5_int(s, mod):
    return int(hashlib.md5(s.encode()).hexdigest()[:8], 16) % mod


CATEGORIES = [
    ('your-orders', 'Your Orders', '\U0001F4E6',
     'Track or cancel orders, view receipts, change addresses', 10),
    ('returns-refunds', 'Returns & Refunds', '\U0001F501',
     'Exchange or return items, check refund status', 20),
    ('manage-prime', 'Manage Prime', '\U0001F451',
     'Cancel or view Prime benefits, billing and renewal', 30),
    ('payment-settings', 'Payment Settings', '\U0001F4B3',
     'Add or edit payment methods, gift cards, balance', 40),
    ('shipping-delivery', 'Shipping & Delivery', '\U0001F69A',
     'Carrier info, shipping rates, international shipping', 50),
    ('account-settings', 'Account Settings', '\U0001F511',
     'Change email or password, login & security, addresses', 60),
    ('devices-content', 'Devices & Digital Services', '\U0001F4F1',
     'Kindle, Fire TV, Alexa, Echo, digital content', 70),
    ('shopping-amazon', 'Shopping on Amazon', '\U0001F6CD',
     'Browse, deals, lists, gift cards, business buying', 80),
]


# (category_slug, article_slug, title, summary, body)
ARTICLES = [
    # Your Orders
    ('your-orders', 'find-a-missing-package-that-shows-as-delivered',
     'Find a Missing Package That Shows as Delivered',
     "If your tracking shows the order as delivered but you can't find it, "
     "follow these steps before contacting us.",
     "Verify the shipping address in Your Orders.\n"
     "Look for a notice of attempted delivery.\n"
     "Look around the delivery location for your package.\n"
     "See if someone else accepted the delivery, unless you have a "
     "signature confirmation.\n"
     "Check your mailbox or wherever else you receive mail. "
     "Some packages travel through multiple carriers.\n"
     "Wait 48 hours — in rare cases packages may say delivered up to 48 "
     "hours before arrival."),
    ('your-orders', 'track-your-package',
     'Track Your Package',
     "Track the status of any order in Your Orders, including packages still "
     "in transit and packages already delivered.",
     "Go to Your Orders. Find the order you want to track and select Track "
     "Package. Carrier and shipping details are shown for each shipment."),
    ('your-orders', 'cancel-items-or-orders',
     'Cancel Items or Orders',
     "You can cancel items or orders that haven't entered the shipping process.",
     "Go to Your Orders. Select the order you want to cancel. Select "
     "Cancel items. Select Cancel checked items. After you submit the "
     "cancellation, we'll send you a confirmation email."),
    ('your-orders', 'change-your-order-information',
     'Change Your Order Information',
     "You can update the shipping address, payment method, and more on "
     "orders that haven't entered the shipping process.",
     "Go to Your Orders. Locate the order. Select Change next to the "
     "field you want to edit. Make your change and select Save."),
    ('your-orders', 'where-is-my-stuff',
     "Where's My Stuff?",
     "Quickly find an order, see its status, or report a problem.",
     "Visit Your Orders to see all orders placed in the last 6 months. "
     "Filter by year to see older orders. Each order card shows the "
     "delivery estimate, payment method, and a Track Package button."),

    # Returns & Refunds
    ('returns-refunds', 'about-our-returns-policies',
     'About Our Returns Policies',
     "Most new, unopened items sold and fulfilled by Amazon can be returned "
     "within 30 days of delivery for a full refund.",
     "Items shipped from Amazon.com, including warehouse deals, can be "
     "returned within 30 days of receipt of shipment in most cases. Some "
     "products have different policies or requirements associated with them."),
    ('returns-refunds', 'return-items-you-ordered',
     'Return Items You Ordered',
     "You can return many items sold on Amazon.com.",
     "Go to Your Orders. Choose the order and select Return or Replace "
     "Items. Select the item that you want to return, and select an option "
     "from the Reason for return menu. Choose how to process your return."),
    ('returns-refunds', 'refunds',
     'Refunds',
     "Refunds are issued to the original form of payment within 3–5 business "
     "days after the return is processed.",
     "If you haven't received your refund, check Your Orders to see whether "
     "the return has been received. Refunds to Amazon.com Gift Card balance "
     "are issued immediately. Credit card refunds may take up to 10 days."),
    ('returns-refunds', 'replace-a-damaged-defective-or-broken-item',
     'Replace a Damaged, Defective, or Broken Item',
     "If you receive an item that is damaged, defective, or broken, you can "
     "request a replacement.",
     "Go to Your Orders. Choose the order and select Return or Replace "
     "Items. Select the item, choose 'Item defective or doesn't work' as the "
     "reason, and select Replace. You'll be guided through the rest."),
    ('returns-refunds', 'free-returns',
     'Free Returns',
     "Many items qualify for free return shipping with an Amazon.com label.",
     "Look for 'Free Returns' on the product detail page. If your item is "
     "eligible, you can print a free return shipping label from Your Orders."),

    # Manage Prime
    ('manage-prime', 'about-amazon-prime',
     'About Amazon Prime',
     "Amazon Prime is a paid membership that offers fast free shipping, "
     "Prime Video, Prime Music, and exclusive Prime savings.",
     "Prime members get unlimited free Two-Day shipping, free Same-Day "
     "delivery on eligible items, Prime Video, Prime Music, Prime Reading, "
     "and exclusive Prime Day savings."),
    ('manage-prime', 'end-your-amazon-prime-membership',
     'End Your Amazon Prime Membership',
     "You can end your Prime membership at any time.",
     "Visit Manage Your Prime Membership. Select End Membership on the "
     "left. Follow the prompts. We will refund the full Prime fee if you "
     "haven't used your Prime benefits since your latest charge."),
    ('manage-prime', 'amazon-prime-price',
     'Amazon Prime Price',
     "The cost of Amazon Prime as of May 2026.",
     "Annual: $139/year. Monthly: $14.99/month. Prime Student: $7.49/month "
     "or $69/year after a 6-month free trial. Prime Access (qualifying "
     "government assistance): $6.99/month."),
    ('manage-prime', 'share-amazon-prime-benefits',
     'Share Amazon Prime Benefits',
     "Use Amazon Household to share eligible Prime benefits with one other "
     "adult and up to four teens and four children.",
     "Go to Manage Your Household. Invite an adult to your Household to "
     "share Prime shipping, Prime Video, and digital content."),

    # Payment Settings
    ('payment-settings', 'add-a-payment-method',
     'Add a Payment Method to Your Account',
     "Add a credit or debit card, checking account, or other supported "
     "payment method.",
     "Go to Your Payments. Select Add a payment method. Enter the card "
     "details and billing address. Select Add your card."),
    ('payment-settings', 'check-your-gift-card-balance',
     'Check Your Gift Card Balance',
     "View the balance of all gift cards applied to your account.",
     "Visit Your Account, then select Gift Cards. Your current balance is "
     "shown at the top of the page along with all redemption history."),
    ('payment-settings', 'pay-with-points',
     'Pay with Points',
     "Use your Amazon rewards points to pay for all or part of eligible "
     "orders during checkout.",
     "At checkout, if you have eligible reward points, you'll see a slider "
     "under your payment method that lets you apply points to your order. "
     "Each point is worth $0.01."),
    ('payment-settings', 'about-amazon-currency-converter',
     'About the Amazon Currency Converter',
     "When you place an international order, Amazon converts the price to "
     "your local currency at the time of checkout.",
     "The Amazon Currency Converter lets you see prices and pay in your "
     "local currency on amazon.com. The exchange rate is set at the time "
     "of order placement and displayed on the order summary."),

    # Shipping & Delivery
    ('shipping-delivery', 'about-shipping-rates',
     'About Shipping Rates',
     "Shipping rates depend on the shipping speed and the destination.",
     "Standard shipping is free on eligible orders over $35. Prime members "
     "receive free Two-Day shipping with no minimum, and free Same-Day on "
     "eligible items. Two-Day shipping for non-Prime is $9.99."),
    ('shipping-delivery', 'find-a-missing-item-from-your-package',
     'Find a Missing Item from Your Package',
     "If your package arrived but an item is missing, contact us within 30 "
     "days.",
     "Check the packing slip for shipment details. Some orders ship in "
     "multiple boxes. Check Your Orders for separate tracking numbers. If "
     "still missing, request a refund or replacement."),
    ('shipping-delivery', 'international-shipping',
     'International Shipping',
     "Amazon Global ships millions of products to over 100 countries.",
     "Look for 'Ships internationally' on the product detail page. Customs "
     "fees and import taxes may apply and are calculated at checkout."),
    ('shipping-delivery', 'amazon-day-delivery',
     'Amazon Day Delivery',
     "Pick a day of the week to receive all your Prime orders.",
     "Choose Amazon Day at checkout. We'll deliver everything on the day "
     "you pick. Add items to your Amazon Day delivery up to 2 days before."),
    ('shipping-delivery', 'shipping-carrier-info',
     'Carrier Contact Information',
     "Phone numbers and websites for the carriers that deliver Amazon "
     "packages.",
     "UPS: 1-800-742-5877. USPS: 1-800-275-8777. FedEx: 1-800-463-3339. "
     "Amazon Logistics: 1-877-251-0253. Tracking URLs are available in "
     "Your Orders for each shipment."),

    # Account Settings
    ('account-settings', 'change-your-email-or-password',
     'Change Your Account Email or Password',
     "Update the email address or password for your Amazon account.",
     "Go to Your Account. Select Login & security. Next to Email or "
     "Password, select Edit. Enter the new information and Save."),
    ('account-settings', 'two-step-verification',
     'About Two-Step Verification',
     "Add a second sign-in step to your Amazon account for extra security.",
     "Go to Login & security. Next to Two-Step Verification, select Edit. "
     "Choose to receive codes via SMS or an authenticator app."),
    ('account-settings', 'manage-your-addresses',
     'Manage Your Addresses',
     "Add, edit, or delete shipping addresses on your account.",
     "Go to Your Addresses. Select Add address, or select Edit on an "
     "existing one. Mark an address as your default to use it automatically."),
    ('account-settings', 'close-your-amazon-account',
     'Close Your Amazon Account',
     "Permanently close your account and request deletion of your personal "
     "information.",
     "Go to Close Your Amazon Account. Review the consequences. Submit "
     "your request. Closing an account is permanent and cannot be undone."),

    # Devices & Content
    ('devices-content', 'kindle-e-reader-help',
     'Kindle E-Reader Help',
     "Get help with your Kindle, including setup, syncing books, and "
     "troubleshooting.",
     "Go to Manage Your Content and Devices. Select your Kindle from the "
     "Devices tab. From there you can deregister, change name, or update."),
    ('devices-content', 'alexa-and-echo-devices',
     'Alexa and Echo Devices',
     "Set up, troubleshoot, and manage settings for your Echo and other "
     "Alexa-enabled devices.",
     "Use the Alexa app to set up new devices, manage routines, and view "
     "settings. To factory reset an Echo, hold the action button for 25 "
     "seconds."),
    ('devices-content', 'fire-tv-help',
     'Fire TV Help',
     "Set up Fire TV, troubleshoot common issues, and manage your apps.",
     "From Settings, you can manage installed apps, network, and display "
     "options. To restart, hold Select and Play for 5 seconds."),

    # Shopping on Amazon
    ('shopping-amazon', 'find-deals-and-coupons',
     'Find Deals and Coupons',
     "Browse Today's Deals, sign up for daily deal alerts, and clip "
     "manufacturer coupons.",
     "Visit Today's Deals to see Lightning Deals and Deals of the Day. "
     "Many products display a clip-able coupon on the product detail page."),
    ('shopping-amazon', 'about-amazon-business',
     'About Amazon Business',
     "Amazon Business offers business-only pricing, bulk discounts, and "
     "tax-exempt purchasing.",
     "Create a free Amazon Business account to access millions of "
     "business-only products and benefits, including business-only "
     "pricing and quantity discounts."),
    ('shopping-amazon', 'amazon-fresh-and-whole-foods',
     'Amazon Fresh and Whole Foods',
     "Order groceries from Amazon Fresh or Whole Foods Market for delivery "
     "or pickup.",
     "Prime members get free 2-hour grocery delivery on eligible orders. "
     "Visit Amazon Fresh or Whole Foods Market on Amazon to start shopping."),
    ('shopping-amazon', 'create-a-wish-list-or-registry',
     'Create a Wish List or Registry',
     "Save items to a Wish List for yourself or create a Gift Registry for "
     "weddings, baby showers, and more.",
     "From any product page, select Add to List. Manage your lists from "
     "Account & Lists in the top right."),
]


def seed_help_content(db, HelpCategory, HelpArticle):
    """Seed HelpCategory + HelpArticle tables."""
    if HelpCategory.query.count() > 0:
        return 0
    cat_by_slug = {}
    for slug, name, icon, blurb, sort_order in CATEGORIES:
        c = HelpCategory(slug=slug, name=name, icon=icon, blurb=blurb,
                         sort_order=sort_order)
        db.session.add(c)
        db.session.flush()
        cat_by_slug[slug] = c
    for cat_slug, art_slug, title, summary, body in ARTICLES:
        cat = cat_by_slug[cat_slug]
        # md5-derived helpful_count for byte-identical reset
        helpful = 50 + _md5_int(art_slug, 950)
        db.session.add(HelpArticle(
            category_id=cat.id, slug=art_slug, title=title,
            summary=summary, body=body,
            helpful_count=helpful,
            updated_at=REFERENCE_DATE - timedelta(days=_md5_int(art_slug, 200)),
        ))
    db.session.commit()
    return len(ARTICLES)


def seed_order_feedback(db, Order, OrderFeedback):
    """Seed seller feedback on a deterministic subset of delivered orders.

    Idempotent: skips when any feedback already exists.
    """
    if OrderFeedback.query.count() > 0:
        return 0
    delivered = (Order.query.filter_by(status='delivered')
                 .order_by(Order.id).all())
    sellers = ['Amazon.com', 'Amazon Warehouse', 'AnkerDirect',
               'Sony', 'iRobot', 'Apple Store', 'Logitech US']
    comments = [
        'Item arrived earlier than the estimate. Packaging was great.',
        'Exactly as described. Would order from this seller again.',
        'Shipping was fast. Box was a bit dented but item was fine.',
        'No issues at all. Five stars.',
        'Great communication and quick delivery.',
        'Product is genuine and works perfectly.',
    ]
    added = 0
    for idx, order in enumerate(delivered):
        # Only feedback every 3rd delivered order, deterministic
        if _md5_int(order.order_number, 3) != 0:
            continue
        rating = 4 + _md5_int(order.order_number + 'r', 2)  # 4 or 5
        seller = sellers[_md5_int(order.order_number + 's', len(sellers))]
        comment = comments[_md5_int(order.order_number + 'c', len(comments))]
        db.session.add(OrderFeedback(
            order_id=order.id, user_id=order.user_id,
            seller_name=seller, rating=rating, comment=comment,
            created_at=REFERENCE_DATE - timedelta(days=_md5_int(
                order.order_number + 'd', 30)),
        ))
        added += 1
    db.session.commit()
    return added


def run_help(db, HelpCategory, HelpArticle, Order, OrderFeedback):
    """Top-level entry point — called from app.py main block after run_extras."""
    seed_help_content(db, HelpCategory, HelpArticle)
    seed_order_feedback(db, Order, OrderFeedback)
