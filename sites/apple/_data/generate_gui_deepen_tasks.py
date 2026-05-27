"""Generate GUI deepen tasks for apple and append to tasks.jsonl."""
import json, hashlib, os

REPO_ROOT = "/home/v-haoqiwang/repos/WebHarbor/sites/apple"
WEB = "http://localhost:40002/"
UPSTREAM = "https://www.apple.com/"


def _id(slug, n):
    return f"Apple--gui_{slug}_{n:03d}"


def emit(slug, questions):
    """Yield task dicts for a page family."""
    seen = set()
    out = []
    for i, q in enumerate(questions):
        # Skip duplicates
        if q in seen:
            continue
        seen.add(q)
        out.append({
            "web_name": "Apple",
            "id": _id(slug, i + 1),
            "ques": q,
            "web": WEB,
            "upstream_url": UPSTREAM,
        })
    return out


# ---------------------------------------------------------------------------
# Per-family task templates.  Each family must yield >= 30 unique tasks.
# Every task references the GUI surface (no API / no JSON / no URL query strings).
# ---------------------------------------------------------------------------
TASKS = []


# 1) Buy iPhone configurators -------------------------------------------------
iphone_models = [
    ("iphone-17-pro-max", "iPhone 17 Pro Max", "Natural Titanium", "Blue Titanium", "256GB", "1TB"),
    ("iphone-17-pro",     "iPhone 17 Pro",     "White Titanium",   "Black Titanium","128GB", "512GB"),
    ("iphone-air",        "iPhone Air",        "Sky Blue",         "Gold",          "256GB", "1TB"),
    ("iphone-17",         "iPhone 17",         "Lavender",         "Mist Blue",     "128GB", "256GB"),
    ("iphone-16e",        "iPhone 16e",        "Black",            "White",         "128GB", "256GB"),
]
buy_iphone_qs = []
for slug, name, c1, c2, s1, s2 in iphone_models:
    buy_iphone_qs += [
        f"On the {name} buy page, list every color shown in the Color selector.",
        f"On the {name} buy page, report the starting price displayed in the hero.",
        f"On the {name} buy page, select the {s2} storage option and report the new total price.",
        f"On the {name} buy page, change the carrier to T-Mobile and report which carrier option is currently selected.",
        f"On the {name} buy page, switch the payment option to 'Buy now and pay the full price' and report the total shown in the sticky bar.",
        f"On the {name} buy page, select AppleCare+ with Theft & Loss and report the two-year price for that plan.",
        f"On the {name} buy page, choose the {c2} color and report the swatch color name displayed.",
    ]
buy_iphone_qs += [
    "Open the iPhone 17 Pro Max buy page and report the highest storage option shown in the Storage selector.",
    "Open the iPhone Air buy page and list every payment option presented in the Payment section.",
    "Open the iPhone 17 buy page and report the AppleCare+ monthly price for the basic AppleCare+ plan.",
    "Open the iPhone 16e buy page and report the chip name shown in the Tech Specs table.",
    "Open the iPhone 17 Pro buy page and report the battery life shown in the Tech Specs table.",
]
TASKS += emit("buy_iphone", buy_iphone_qs)


# 2) Buy Mac configurators ---------------------------------------------------
mac_models = [
    ("macbook-pro-16", "MacBook Pro 16\""),
    ("macbook-pro-14", "MacBook Pro 14\""),
    ("macbook-air-15", "MacBook Air 15\""),
    ("macbook-air-13", "MacBook Air 13\""),
    ("mac-mini",       "Mac mini"),
    ("imac",           "iMac"),
]
buy_mac_qs = []
for slug, name in mac_models:
    buy_mac_qs += [
        f"On the {name} buy page, list every chip option shown in the Chip selector.",
        f"On the {name} buy page, report the lowest base price shown.",
        f"On the {name} buy page, select the largest memory option and report the resulting total in the sticky bar.",
        f"On the {name} buy page, list every storage option in the Storage selector.",
        f"On the {name} buy page, list every keyboard option presented.",
    ]
buy_mac_qs += [
    "Open the MacBook Pro 16\" buy page and report the most expensive storage upgrade and its price delta.",
    "Open the MacBook Air 13\" buy page and report the lowest memory option in the Memory selector.",
    "Open the Mac mini buy page and report the price difference between 'No keyboard included' and 'Magic Keyboard with Touch ID — US English'.",
    "Open the iMac buy page and list every color swatch shown in the Color selector.",
    "Open the MacBook Pro 14\" buy page and report the battery life shown in the Tech Specs table.",
]
TASKS += emit("buy_mac", buy_mac_qs)


# 3) Buy iPad configurators --------------------------------------------------
ipad_models = [
    ("ipad-pro-13", "iPad Pro 13\""),
    ("ipad-pro-11", "iPad Pro 11\""),
    ("ipad-air",    "iPad Air"),
    ("ipad",        "iPad"),
]
buy_ipad_qs = []
for slug, name in ipad_models:
    buy_ipad_qs += [
        f"On the {name} buy page, list every storage option shown.",
        f"On the {name} buy page, report the price delta for the Wi-Fi + Cellular connectivity upgrade.",
        f"On the {name} buy page, list every accessory shown in the 'Add Apple Pencil and Magic Keyboard' section with its price.",
        f"On the {name} buy page, select the Wi-Fi + Cellular option and the largest storage, then report the new total price.",
        f"On the {name} buy page, list every color shown in the Color selector.",
        f"On the {name} buy page, check the Magic Keyboard accessory and report the new total in the sticky bar.",
    ]
buy_ipad_qs += [
    "Open the iPad Pro 13\" buy page and report the Magic Keyboard for iPad Pro 13\" accessory price.",
    "Open the iPad Air buy page and report the chip shown in the Tech Specs table.",
    "Open the iPad buy page and list every Apple Pencil option offered in the accessories section.",
    "Open the iPad Pro 11\" buy page and report the price delta from 256GB to 1TB.",
]
TASKS += emit("buy_ipad", buy_ipad_qs)


# 4) Buy Watch configurators --------------------------------------------------
watch_models = [
    ("ultra-3",   "Apple Watch Ultra 3"),
    ("series-11", "Apple Watch Series 11"),
    ("se-2",      "Apple Watch SE"),
]
buy_watch_qs = []
for slug, name in watch_models:
    buy_watch_qs += [
        f"On the {name} buy page, list every case option in the Case selector.",
        f"On the {name} buy page, list every band option in the Band selector.",
        f"On the {name} buy page, report all available connectivity options.",
        f"On the {name} buy page, select the case option with the highest price delta and report the new total in the sticky bar.",
        f"On the {name} buy page, list every AppleCare+ plan with its monthly price.",
        f"On the {name} buy page, report the chip shown in the Tech Specs table.",
        f"On the {name} buy page, choose the GPS + Cellular option (when offered) and report the new total in the sticky bar.",
        f"On the {name} buy page, choose the Titanium Milanese Loop band (if offered) and report the new total in the sticky bar.",
    ]
buy_watch_qs += [
    "Open the Apple Watch Series 11 buy page, switch to the 46mm Titanium Case — Natural option, then report the new total in the sticky bar.",
    "Open the Apple Watch Ultra 3 buy page and report whether GPS-only connectivity is offered.",
    "Open the Apple Watch SE buy page and report the price delta of the 44mm aluminum cases vs 40mm.",
    "Open the Apple Watch Series 11 buy page and report the battery life shown in the Tech Specs table.",
]
TASKS += emit("buy_watch", buy_watch_qs)


# 5) Compare iPhone -----------------------------------------------------------
compare_iphone_qs = [
    "Open the iPhone compare page and report the price of every iPhone model shown in the comparison table.",
    "Open the iPhone compare page and report which model has the largest display.",
    "Open the iPhone compare page and report which iPhone offers the longest video playback battery life.",
    "Open the iPhone compare page and report the chip used in iPhone 17 Pro vs iPhone 17.",
    "Open the iPhone compare page and report the max storage tier shown for iPhone 17 Pro Max.",
    "Open the iPhone compare page and click the Buy button for iPhone Air, then report the page title that loads.",
    "Open the iPhone compare page and report the weight column value for iPhone Air.",
    "Open the iPhone compare page and report the number of finishes column value for iPhone 17.",
    "Open the iPhone compare page and report the camera system text shown for iPhone 17 Pro Max.",
    "Open the iPhone compare page and click the Buy button for iPhone 17, then report the URL of the page that opens.",
    "Open the iPhone compare page and report the camera description for iPhone 16e.",
    "Open the iPhone compare page and list every iPhone model name shown in the header row.",
    "Open the iPhone compare page and report the price difference between iPhone 17 Pro Max and iPhone 16e.",
    "Open the iPhone compare page and report the battery row value for iPhone 17.",
    "Open the iPhone compare page and report the chip row value for iPhone 16e.",
    "Open the iPhone compare page and report the weight column value for iPhone 17 Pro Max.",
    "Open the iPhone compare page and find the cheapest model, then report its starting price.",
    "Open the iPhone compare page and click the link to 'Why people compare' section, then list the bullet points.",
    "Open the iPhone compare page and report which iPhone model shows '48MP Fusion + 48MP UW + 48MP Tele 8x' in the Camera column.",
    "Open the iPhone compare page and report the storage_top value for iPhone Air.",
    "Open the iPhone compare page and identify which models share the same starting price.",
    "Open the iPhone compare page and report the battery row value for iPhone Air.",
    "Open the iPhone compare page and report how many models are shown in the comparison.",
    "Open the iPhone compare page and report the chip row value for iPhone 17 Pro.",
    "Open the iPhone compare page and report the camera row value for iPhone Air.",
    "Open the iPhone compare page and report the display row value for iPhone 16e.",
    "Open the iPhone compare page and report the weight column value for iPhone 17.",
    "Open the iPhone compare page and report the storage_top column for iPhone 17 Pro.",
    "Open the iPhone compare page and report the storage_top column for iPhone 16e.",
    "Open the iPhone compare page and report the battery column value for iPhone 16e.",
    "Open the iPhone compare page and report the breadcrumb trail shown at the top.",
    "Open the iPhone compare page and report the camera column value for iPhone 17 Pro.",
]
TASKS += emit("compare_iphone", compare_iphone_qs)


# 6) Compare Mac --------------------------------------------------------------
compare_mac_qs = [
    "Open the Mac compare page and report the price of every Mac model shown.",
    "Open the Mac compare page and report which Mac has the highest base price.",
    "Open the Mac compare page and report the chip column value for MacBook Pro 16\".",
    "Open the Mac compare page and report the memory range for MacBook Air 13\".",
    "Open the Mac compare page and click the Buy button for MacBook Pro 14\", then report the page that opens.",
    "Open the Mac compare page and report which Mac has the largest maximum storage.",
    "Open the Mac compare page and report the weight column value for MacBook Air 15\".",
    "Open the Mac compare page and report the display column value for Mac mini.",
    "Open the Mac compare page and report the chip column value for iMac.",
    "Open the Mac compare page and report the battery column value for MacBook Pro 14\".",
    "Open the Mac compare page and report the storage range for MacBook Pro 16\".",
    "Open the Mac compare page and report the chip column value for MacBook Air 13\".",
    "Open the Mac compare page and list every Mac model name shown in the header row.",
    "Open the Mac compare page and click Buy for Mac mini and report the URL that opens.",
    "Open the Mac compare page and report the price of MacBook Air 13\".",
    "Open the Mac compare page and report the storage range for MacBook Air 13\".",
    "Open the Mac compare page and report the memory range for MacBook Pro 14\".",
    "Open the Mac compare page and report the battery column value for iMac.",
    "Open the Mac compare page and report the weight column value for MacBook Pro 16\".",
    "Open the Mac compare page and report how many models are shown.",
    "Open the Mac compare page and identify the cheapest Mac and its price.",
    "Open the Mac compare page and identify the most expensive Mac and its price.",
    "Open the Mac compare page and report the display value for iMac.",
    "Open the Mac compare page and report the chip column value for Mac mini.",
    "Open the Mac compare page and report the breadcrumb trail shown at the top.",
    "Open the Mac compare page and report the display value for MacBook Pro 14\".",
    "Open the Mac compare page and report which Mac shows 'sold separately' as the display.",
    "Open the Mac compare page and read the 'Why people compare' section and list its bullet points.",
    "Open the Mac compare page and click the Buy button for MacBook Air 15\", then report the page that opens.",
    "Open the Mac compare page and report the battery row value for Mac mini.",
    "Open the Mac compare page and report the storage range for Mac mini.",
    "Open the Mac compare page and report the weight value for iMac.",
]
TASKS += emit("compare_mac", compare_mac_qs)


# 7) Compare iPad -------------------------------------------------------------
compare_ipad_qs = [
    "Open the iPad compare page and report the starting price of every iPad model.",
    "Open the iPad compare page and report which iPad has the largest display.",
    "Open the iPad compare page and report which iPad mini chip is shown.",
    "Open the iPad compare page and report the weight value for iPad Pro 13\".",
    "Open the iPad compare page and report the weight value for iPad Pro 11\".",
    "Open the iPad compare page and report which iPads support Apple Pencil Pro.",
    "Open the iPad compare page and click the Buy button for iPad Pro 13\" and report the page that opens.",
    "Open the iPad compare page and report the chip column value for iPad Air.",
    "Open the iPad compare page and report the chip column value for iPad mini.",
    "Open the iPad compare page and report the storage_top column value for iPad.",
    "Open the iPad compare page and report the storage_top column value for iPad Pro 11\".",
    "Open the iPad compare page and report which iPad has the lowest starting price.",
    "Open the iPad compare page and report which iPad has the highest starting price.",
    "Open the iPad compare page and report the battery column value for iPad Air.",
    "Open the iPad compare page and report the pencil column value for iPad mini.",
    "Open the iPad compare page and click the Buy button for iPad and report the page that opens.",
    "Open the iPad compare page and list every iPad model shown in the header row.",
    "Open the iPad compare page and report the display column value for iPad mini.",
    "Open the iPad compare page and read the 'Why people compare' section bullet points.",
    "Open the iPad compare page and report the breadcrumb trail shown at the top.",
    "Open the iPad compare page and report the chip column value for iPad Pro 13\".",
    "Open the iPad compare page and report the display column value for iPad.",
    "Open the iPad compare page and report the pencil column value for iPad Pro 13\".",
    "Open the iPad compare page and report the weight column value for iPad mini.",
    "Open the iPad compare page and report the pencil column value for iPad Air.",
    "Open the iPad compare page and report the chip column value for iPad.",
    "Open the iPad compare page and report the battery column value for iPad Pro 11\".",
    "Open the iPad compare page and report whether iPad mini has a Buy button shown.",
    "Open the iPad compare page and report the weight column value for iPad.",
    "Open the iPad compare page and report the display column value for iPad Air.",
    "Open the iPad compare page and click the Buy button for iPad Pro 11\" and report the page that opens.",
]
TASKS += emit("compare_ipad", compare_ipad_qs)


# 8) Compare AirPods ----------------------------------------------------------
compare_airpods_qs = [
    "Open the AirPods compare page and report the price of every AirPods model shown.",
    "Open the AirPods compare page and report which model uses the H3 chip.",
    "Open the AirPods compare page and report which model offers clinical-grade hearing aid features.",
    "Open the AirPods compare page and report the noise control feature for AirPods Max.",
    "Open the AirPods compare page and report the battery row value for AirPods Pro 3.",
    "Open the AirPods compare page and report the battery row value for AirPods 4 (with ANC).",
    "Open the AirPods compare page and report the chip column value for AirPods 4.",
    "Open the AirPods compare page and report which AirPods support Personalised Spatial Audio.",
    "Open the AirPods compare page and report the transparency mode value for AirPods 4.",
    "Open the AirPods compare page and report the hearing aid features column for AirPods 4 (with ANC).",
    "Open the AirPods compare page and report which model is the cheapest, with its price.",
    "Open the AirPods compare page and report which model is the most expensive, with its price.",
    "Open the AirPods compare page and report the noise control column for AirPods 4 (with ANC).",
    "Open the AirPods compare page and read the 'Why people compare' section bullet points.",
    "Open the AirPods compare page and report the breadcrumb trail shown at the top.",
    "Open the AirPods compare page and report the noise control column for AirPods 4.",
    "Open the AirPods compare page and report the chip column value for AirPods Pro 3.",
    "Open the AirPods compare page and report the chip column value for AirPods Max.",
    "Open the AirPods compare page and report how many models are shown in the table.",
    "Open the AirPods compare page and report the transparency mode value for AirPods Pro 3.",
    "Open the AirPods compare page and report the transparency mode value for AirPods Max.",
    "Open the AirPods compare page and report the battery column value for AirPods Max.",
    "Open the AirPods compare page and report the spatial audio column value for AirPods Max.",
    "Open the AirPods compare page and list every AirPods model name shown in the header row.",
    "Open the AirPods compare page and report the hearing aid column value for AirPods Pro 3.",
    "Open the AirPods compare page and report the hearing aid column value for AirPods Max.",
    "Open the AirPods compare page and report the price of AirPods 4 (with ANC).",
    "Open the AirPods compare page and report whether AirPods 4 supports ANC.",
    "Open the AirPods compare page and report which AirPods model has the longest case battery life.",
    "Open the AirPods compare page and report the spatial audio column for AirPods Pro 3.",
    "Open the AirPods compare page and report the noise control column value for AirPods Pro 3.",
]
TASKS += emit("compare_airpods", compare_airpods_qs)


# 9) Financing calculator -----------------------------------------------------
financing_qs = [
    "Open the Apple Card monthly payment calculator and report the default product preselected in the dropdown.",
    "Open the financing calculator, choose 'MacBook Pro 16\"' and 24 months, then report the Apple Card 0% APR monthly payment displayed.",
    "Open the financing calculator, choose 'iPhone 17 Pro Max' and 24 months, then report the Apple Card 0% APR monthly payment displayed.",
    "Open the financing calculator, choose 'iPad Pro 13\"' and 24 months, then report the Apple Card 0% APR monthly payment.",
    "Open the financing calculator, choose 'AirPods Max' and 12 months, then report the Apple Card monthly payment displayed.",
    "Open the financing calculator and report the standard variable APR percentage shown on the right card.",
    "Open the financing calculator, change months to 36 with the default product, and report the Apple Card monthly payment shown.",
    "Open the financing calculator, change months to 6 with 'iPhone 17' selected, and report the Apple Card monthly payment shown.",
    "Open the financing calculator and report the final total shown in the 'Standard variable APR' card when 'iPhone 17 Pro' and 24 months are selected.",
    "Open the financing calculator and report the final total shown in the 'Apple Card Monthly Installments' card for default settings.",
    "Open the financing calculator and report the list of preset products shown in the dropdown.",
    "Open the financing calculator, choose 'Apple Watch Ultra 3' and 12 months, then report the Apple Card monthly payment.",
    "Open the financing calculator and report the breadcrumb trail at the top of the page.",
    "Open the financing calculator and report which related card links are listed in 'You may also like'.",
    "Open the financing calculator and report the headline shown in the hero.",
    "Open the financing calculator, set 'MacBook Air 13\"' and 18 months, then report the Apple Card monthly payment.",
    "Open the financing calculator, set 'iPad Air' and 24 months, then report the Apple Card monthly payment.",
    "Open the financing calculator and report the months options shown in the months dropdown.",
    "Open the financing calculator, set 'AirPods Pro 3' and 12 months, then report the standard variable APR monthly payment.",
    "Open the financing calculator, set 'Apple Watch SE' and 12 months, then report the Apple Card 0% APR final total.",
    "Open the financing calculator and report which product appears as the third option in the dropdown.",
    "Open the financing calculator and report the URL of the 'Apply for Apple Card' related link.",
    "Open the financing calculator, set 'iPhone Air' and 30 months, then report the Apple Card monthly payment.",
    "Open the financing calculator, set 'iPhone 17 Pro Max' and 30 months, then report the Apple Card monthly payment.",
    "Open the financing calculator and report the lowest months option available.",
    "Open the financing calculator and report the highest months option available.",
    "Open the financing calculator, set 'MacBook Pro 14\"' and 24 months, then report the Apple Card monthly payment.",
    "Open the financing calculator, set the custom price to $1500.00 and 24 months, then report the Apple Card monthly payment.",
    "Open the financing calculator, set custom price to $2000.00 and 12 months, then report the standard variable APR monthly payment.",
    "Open the financing calculator and report whether the 'Calculate' button is visible.",
    "Open the financing calculator and report what description appears under the 'Apple Card Monthly Installments' card heading.",
    "Open the financing calculator and report what description appears under the 'Standard variable APR' card heading.",
]
TASKS += emit("financing_calculator", financing_qs)


# 10) Business industry hubs --------------------------------------------------
industries = ["retail", "healthcare", "education-pro", "creative"]
biz_qs = []
for ind in industries:
    biz_qs += [
        f"Open the Apple at Work — {ind.replace('-', ' ').title()} page and report the headline shown in the hero.",
        f"Open the Apple at Work — {ind.replace('-', ' ').title()} page and list every use case shown on the page.",
        f"Open the Apple at Work — {ind.replace('-', ' ').title()} page and report the case study text shown.",
        f"Open the Apple at Work — {ind.replace('-', ' ').title()} page and list the recommended products shown in the grid.",
        f"Open the Apple at Work — {ind.replace('-', ' ').title()} page and report the URL of the 'Get a custom quote' button.",
        f"Open the Apple at Work — {ind.replace('-', ' ').title()} page and report the URL of the 'Apple Business Manager' link.",
        f"Open the Apple at Work — {ind.replace('-', ' ').title()} page and report the subheadline shown under the headline.",
    ]
biz_qs += [
    "Open the Apple at Work — Retail page and report the second use case bullet.",
    "Open the Apple at Work — Healthcare page and report the case study customer name.",
    "Open the Apple at Work — Creative page and report the breadcrumb trail at the top.",
    "Open the Apple at Work — Education Pro page and report which Mac is listed in the recommended products grid.",
]
TASKS += emit("business_industry", biz_qs)


# 11) Education students/educators -------------------------------------------
edu_students_qs = [
    "Open the Education Pricing for Students page and report the headline shown in the hero.",
    "Open the Education Pricing for Students page and report the Education Price of MacBook Air 13\".",
    "Open the Education Pricing for Students page and report the Education Price of MacBook Pro 16\".",
    "Open the Education Pricing for Students page and report how much you save on MacBook Pro 16\".",
    "Open the Education Pricing for Students page and report the Education Price of iPad Pro 11\".",
    "Open the Education Pricing for Students page and list every product shown in the savings table.",
    "Open the Education Pricing for Students page and report the regular price of iMac.",
    "Open the Education Pricing for Students page and report how much you save on iPad Air.",
    "Open the Education Pricing for Students page and read the 'Free gifts and add-ons' bullet list.",
    "Open the Education Pricing for Students page and report the URL of the 'Check eligibility' button.",
    "Open the Education Pricing for Students page and report the breadcrumb trail at the top.",
    "Open the Education Pricing for Students page and report the highest-savings row in the table.",
    "Open the Education Pricing for Students page and report which product saves $200.",
    "Open the Education Pricing for Students page and report which products save $100.",
    "Open the Education Pricing for Students page and report the Education Price of MacBook Air 15\".",
    "Open the Education Pricing for Students page and report the regular price of MacBook Pro 14\".",
    "Open the Education Pricing for Students page and report the Education Price of iPad Pro 13\".",
    "Open the Education Pricing for Students page and report the headline shown above the table.",
    "Open the Education Pricing for Students page and report the discount on the iPad Pro 13\" row.",
    "Open the Education Pricing for Students page and report the savings on MacBook Pro 14\".",
    "Open the Education Pricing for Students page and report the regular price of iPad Air.",
    "Open the Education Pricing for Students page and report the Education Price of iMac.",
    "Open the Education Pricing for Students page and click the 'Compare Mac models' button and report the page that opens.",
    "Open the Education Pricing for Students page and report the regular price of MacBook Air 13\".",
    "Open the Education Pricing for Educators page and list every product shown in the savings table.",
    "Open the Education Pricing for Educators page and report the educator-exclusive gifts list.",
    "Open the Education Pricing for Educators page and report the Education Price of iPad (10th gen).",
    "Open the Education Pricing for Educators page and report the savings on MacBook Pro 16\".",
    "Open the Education Pricing for Educators page and report the breadcrumb trail at the top.",
    "Open the Education Pricing for Educators page and report the highest savings row in the table.",
    "Open the Education Pricing for Educators page and report the URL of the 'Everyone Can Create' button.",
    "Open the Everyone Can Create page and list every curriculum module shown.",
    "Open the Everyone Can Create page and report the number of lessons in the Photo module.",
    "Open the Everyone Can Create page and report the grade range of the Video module.",
    "Open the Everyone Can Create page and report the free downloads with their sizes.",
    "Open the Everyone Can Create page and report the breadcrumb trail at the top.",
    "Open the Swift Playgrounds Curriculum page and list every track shown.",
    "Open the Swift Playgrounds Curriculum page and report the duration of the Develop in Swift — Fundamentals track.",
    "Open the Swift Playgrounds Curriculum page and report the audience of the Develop in Swift — Data Collections track.",
    "Open the Swift Playgrounds Curriculum page and report the outcome of the Develop in Swift — Tutorials track.",
]
TASKS += emit("education_portals", edu_students_qs)


# 12) Services hubs (tv+, music, arcade, news+, fitness+, icloud) -------------
services_qs = []
service_names = {
    "tv-plus":      "Apple TV+",
    "music":        "Apple Music",
    "arcade":       "Apple Arcade",
    "news-plus":    "Apple News+",
    "fitness-plus": "Apple Fitness+",
    "icloud":       "iCloud+",
}
for slug, label in service_names.items():
    services_qs += [
        f"Open the {label} hub page and report the monthly price displayed in the hero.",
        f"Open the {label} hub page and report the trial offer displayed in the hero.",
        f"Open the {label} hub page and list every highlight tile shown in the highlights grid.",
        f"Open the {label} hub page and list every bullet in the 'What's included' list.",
        f"Open the {label} hub page and report the tagline shown under the title.",
    ]
TASKS += emit("services_hubs", services_qs)


# 13) iCloud storage plans + Apple One ----------------------------------------
icloud_plans_qs = [
    "Open the iCloud+ storage plans page and list every plan tier with its monthly price.",
    "Open the iCloud+ storage plans page and report the monthly price of the 2TB plan.",
    "Open the iCloud+ storage plans page and report the monthly price of the 50GB plan.",
    "Open the iCloud+ storage plans page and report which plan is described as 'Family Sharing + HomeKit Secure Video unlimited cameras'.",
    "Open the iCloud+ storage plans page and report the monthly price of the 12TB plan.",
    "Open the iCloud+ storage plans page and report the note text for the 5GB plan.",
    "Open the iCloud+ storage plans page and report the note text for the 200GB plan.",
    "Open the iCloud+ storage plans page and report the note text for the 6TB plan.",
    "Open the iCloud+ storage plans page and report the breadcrumb trail at the top.",
    "Open the iCloud+ storage plans page and read the 'Why people compare' bullet list.",
    "Open the iCloud+ storage plans page and report how many plans are listed in total.",
    "Open the iCloud+ storage plans page and report the monthly price of the 6TB plan.",
    "Open the Apple One plans page and list every plan name with its monthly price.",
    "Open the Apple One plans page and report what services are included in the Premier plan.",
    "Open the Apple One plans page and report the iCloud+ tier included in the Family plan.",
    "Open the Apple One plans page and report the monthly price of the Individual plan.",
    "Open the Apple One plans page and report the monthly price of the Family plan.",
    "Open the Apple One plans page and report the monthly price of the Premier plan.",
    "Open the Apple One plans page and report how many family members the Family plan supports.",
    "Open the Apple One plans page and report the breadcrumb trail at the top.",
    "Open the Apple One plans page and click the Subscribe button on Premier and report the URL it opens.",
    "Open the Apple One plans page and list every service included in the Individual plan.",
    "Open the Apple One plans page and report which plan includes Apple Fitness+.",
    "Open the Apple One plans page and report which plan includes Apple News+.",
    "Open the iCloud+ storage plans page and report which plan has a $0.00 monthly price.",
    "Open the iCloud+ storage plans page and report the heading shown at the top of the page.",
    "Open the iCloud+ storage plans page and click the Subscribe button related to a plan and report the destination.",
    "Open the Apple One plans page and report the heading shown at the top of the page.",
    "Open the Apple One plans page and report which plan only supports a single person.",
    "Open the Apple One plans page and report the iCloud+ tier included in the Individual plan.",
    "Open the iCloud+ storage plans page and report the most expensive paid plan and its monthly price.",
    "Open the Apple One plans page and report the iCloud+ tier included in the Premier plan.",
]
TASKS += emit("icloud_and_apple_one", icloud_plans_qs)


# 14) Apple Card apply --------------------------------------------------------
apple_card_qs = [
    "Open the Apple Card apply page and report the headline shown in the hero.",
    "Open the Apple Card apply page and list every form field label shown.",
    "Open the Apple Card apply page and report the APR range mentioned under the form.",
    "Open the Apple Card apply page and list every product family eligible for Apple Card Monthly Installments.",
    "Open the Apple Card apply page and list every Why Apple Card highlight tile shown.",
    "Open the Apple Card apply page and report the description shown for the Daily Cash highlight tile.",
    "Open the Apple Card apply page and report the description shown for the Apple Card Savings highlight tile.",
    "Open the Apple Card apply page and report the description shown for the Monthly Installments highlight tile.",
    "Open the Apple Card apply page and submit the form with full name 'Sample User', SSN last 4 = 4242, income = 80000, then report the success banner shown.",
    "Open the Apple Card apply page and submit the form with an empty name, then report the validation banner that appears.",
    "Open the Apple Card apply page and report the breadcrumb trail at the top.",
    "Open the Apple Card apply page and report which input field requires exactly 4 digits.",
    "Open the Apple Card apply page and report what banner appears when SSN last 4 is 'abcd'.",
    "Open the Apple Card apply page and report the form action URL.",
    "Open the Apple Card apply page and report the privacy disclosure shown under the form.",
    "Open the Apple Card apply page and report the URL of the 'Apple Card' breadcrumb link.",
    "Open the Apple Card apply page and report the description shown for the Privacy & Security highlight tile.",
    "Open the Apple Card apply page and report the description shown for the Family Sharing highlight tile.",
    "Open the Apple Card apply page and report the heading shown above the highlights grid.",
    "Open the Apple Card apply page and report the heading shown above the Monthly Installments list.",
    "Open the Apple Card apply page and submit the form with full name 'Demo User', SSN last 4 = 9876, income = 50000, then report the success message.",
    "Open the Apple Card apply page and report the order of form fields top to bottom.",
    "Open the Apple Card apply page and submit the form with income left empty, then report the error banner.",
    "Open the Apple Card apply page and report whether the form uses POST or GET.",
    "Open the Apple Card apply page and report the months at 0% APR shown next to iPhone in the Monthly Installments list.",
    "Open the Apple Card apply page and report the months at 0% APR shown next to AirPods in the Monthly Installments list.",
    "Open the Apple Card apply page and report the months at 0% APR shown next to iPad in the Monthly Installments list.",
    "Open the Apple Card apply page and report the months at 0% APR shown next to Apple Watch in the Monthly Installments list.",
    "Open the Apple Card apply page and report the months at 0% APR shown next to Mac in the Monthly Installments list.",
    "Open the Apple Card apply page and report the colour and tone shown on the Continue button.",
    "Open the Apple Card apply page and submit the form with SSN last 4 = '12' (too short) and report the validation banner shown.",
    "Open the Apple Card apply page and report the link target of the breadcrumb 'Apple' link.",
]
TASKS += emit("apple_card_apply", apple_card_qs)


# 15) Support category/contact/genius bar -------------------------------------
support_qs = []
for slug in ["iphone", "mac", "ipad", "watch", "airpods", "tv-home", "services", "account"]:
    label = slug.replace('-', ' ').title()
    support_qs += [
        f"Open the {label} Support category page and list every top task tile shown.",
        f"Open the {label} Support category page and list every popular article shown.",
        f"Open the {label} Support category page and report the headline shown in the hero.",
    ]
support_qs += [
    "Open the Apple Support contact page and report the three primary contact channels listed.",
    "Open the Apple Support contact page and report the phone number listed in the 'Call us' card.",
    "Open the Apple Support contact page and report the average wait time listed for chat.",
    "Open the Apple Support contact page and list every product category link shown in the 'Or pick a product category' section.",
    "Open the Genius Bar booking page and list every Apple Store shown in the store dropdown.",
    "Open the Genius Bar booking page and list every reason for visit shown in the reason dropdown.",
    "Open the Genius Bar booking page and submit the form with store=Apple SoHo, reason='iPhone screen repair', slot='Today, 6:50 PM', then report the success message.",
    "Open the Genius Bar booking page and submit the form with no store selected, then report the validation banner.",
    "Open the Genius Bar booking page and report the headline shown in the hero.",
    "Open the Genius Bar booking page and report the breadcrumb trail at the top.",
    "Open the Apple Support contact page and report the URL of the 'Book a visit' link in the Genius Bar reservation card.",
    "Open the iPhone Support category page and report which task tile is shown first.",
    "Open the Mac Support category page and report the breadcrumb trail at the top.",
    "Open the iPad Support category page and report the article shown last in the popular articles list.",
    "Open the Watch Support category page and report the headline shown in the hero.",
    "Open the AirPods Support category page and report the second top task tile shown.",
    "Open the TV & Home Support category page and report the second popular article shown.",
    "Open the Services & Subscriptions support category page and list every top task tile shown.",
    "Open the Apple Account support category page and report the popular article shown first.",
    "Open the Apple Support contact page and report the heading text used over the contact channel cards.",
]
TASKS += emit("support_pages", support_qs)


# 16) Trade-in quote -----------------------------------------------------------
tradein_qs = []
for slug, model_name in [
    ("iphone-15-pro-max", "iPhone 15 Pro Max"),
    ("iphone-14-pro",     "iPhone 14 Pro"),
    ("iphone-15",         "iPhone 15"),
    ("iphone-13",         "iPhone 13"),
    ("iphone-12",         "iPhone 12"),
]:
    tradein_qs += [
        f"Open the trade-in quote page for {model_name} and report the Excellent condition quote.",
        f"Open the trade-in quote page for {model_name} and report the Good condition quote.",
        f"Open the trade-in quote page for {model_name} and report the Fair condition quote.",
    ]
for slug, model_name in [
    ("ipad-pro-13-m4", "iPad Pro 13\" (M4)"),
    ("ipad-air-m2",    "iPad Air (M2)"),
    ("ipad-mini-7",    "iPad mini (7th gen)"),
]:
    tradein_qs += [
        f"Open the trade-in quote page for {model_name} and report the Excellent condition quote.",
        f"Open the trade-in quote page for {model_name} and report the Good condition quote.",
    ]
for slug, model_name in [
    ("macbook-pro-16-m3", "MacBook Pro 16\" M3"),
    ("macbook-air-13-m3", "MacBook Air 13\" M3"),
    ("imac-m3",           "iMac (M3, 2023)"),
]:
    tradein_qs += [
        f"Open the trade-in quote page for {model_name} and report the Excellent condition quote.",
        f"Open the trade-in quote page for {model_name} and report the Good condition quote.",
    ]
tradein_qs += [
    "Open the trade-in quote page for Apple Watch Series 10 and report the Excellent condition quote.",
    "Open the trade-in quote page for Apple Watch Ultra 2 and report the Good condition quote.",
    "Open the trade-in quote page for Apple Watch SE (2nd gen) and report the Fair condition quote.",
    "Open the trade-in quote page for iPhone 15 Pro Max and click 'Start your trade-in' and report the page that opens.",
    "Open the trade-in quote page for iPad Pro 13\" (M4) and report the breadcrumb trail at the top.",
    "Open the trade-in quote page for iPhone 15 and report the headline.",
    "Open the trade-in quote page for MacBook Air 13\" M3 and report the highest quote shown.",
    "Open the trade-in quote page for iPhone 13 and report all three condition quotes.",
    "Open the trade-in quote page for Mac mini (M2) and report the Excellent condition quote.",
    "Open the trade-in quote page for iPhone 14 and report the Good condition quote.",
    "Open the trade-in quote page for Apple Watch Series 9 and report the Excellent condition quote.",
    "Open the trade-in quote page for iPad (10th gen) and report the Fair condition quote.",
]
TASKS += emit("trade_in_quote", tradein_qs)


# ---------------------------------------------------------------------------
# Append to tasks.jsonl with no duplicates
# ---------------------------------------------------------------------------
def main():
    path = os.path.join(REPO_ROOT, "tasks.jsonl")
    existing_ids = set()
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                existing_ids.add(json.loads(line)["id"])
            except (json.JSONDecodeError, KeyError):
                continue
    added = 0
    with open(path, 'a') as f:
        for t in TASKS:
            if t["id"] in existing_ids:
                continue
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
            added += 1
    print(f"Added {added} new tasks; total families generated: {len(TASKS)}")


if __name__ == "__main__":
    main()
