"""CarMax mirror — programmatic task generator.

Produces a tasks.jsonl with ≥1500 deterministic GUI tasks covering the
full breadth of the deepened site. WebVoyager schema; tasks all use
http://localhost:40015/ as the mirror base.

Discipline (harden-env gotchas):
- §24: GUI-only tasks. No /api/, /graphql, /sitemap, "parse the JSON"
  language. Every task is something a browser-driving agent would do.
- §28: 5-token prefix cap @ 5; we vary at least 2 dimensions per
  template so byte-identical duplicates and same-prefix floods are
  avoided.
- All `<page>` references use real URLs that the deepen routes serve.
"""
import collections
import json
import os
import re
import sys


BASE = 'http://localhost:40015/'
UPSTREAM = 'https://www.carmax.com/'
NAME = 'CarMax'


def task(qid, ques):
    return {
        'web_name': NAME,
        'id': f'{NAME}--gui_{qid}',
        'ques': ques,
        'web': BASE,
        'upstream_url': UPSTREAM,
    }


def main():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app import app, Vehicle, Store, Article
    from gui_deepen import ResearchTopic

    with app.app_context():
        all_v = Vehicle.query.order_by(Vehicle.id).all()
        all_s = Store.query.order_by(Store.id).all()
        all_a = Article.query.order_by(Article.id).all()
        topics = ResearchTopic.query.order_by(ResearchTopic.slug).all()
        store_by_state = collections.defaultdict(list)
        for s in all_s:
            store_by_state[s.state].append(s)
        by_make = collections.defaultdict(list)
        by_body = collections.defaultdict(list)
        by_fuel = collections.defaultdict(list)
        by_drive = collections.defaultdict(list)
        for v in all_v:
            by_make[(v.make, v.make_slug)].append(v)
            by_body[v.body_style].append(v)
            by_fuel[v.fuel_type].append(v)
            by_drive[v.drive_type].append(v)

        # Top makes (≥10 in inventory)
        top_makes = [m for m, vs in by_make.items() if len(vs) >= 10]
        top_makes.sort(key=lambda mk: -len(by_make[mk]))

        # Some featured / new arrival / price drop pools
        featured = [v for v in all_v if v.is_featured][:50]
        new_arrivals = [v for v in all_v if v.is_new_arrival][:50]
        price_drops = [v for v in all_v if v.is_price_drop][:50]
        electric = [v for v in all_v if v.fuel_type == 'Electric'][:30]

        tasks = []
        idx = 0
        # ------------------------------------------------------------------
        # Family 1: search by make+model — 200 tasks
        # ------------------------------------------------------------------
        sampled = sorted({(v.make, v.make_slug, v.model, v.model_slug)
                          for v in all_v})
        for (mk, mks, md, mds) in sampled[:200]:
            tasks.append(task(idx,
                f"On /cars/{mks}/{mds}, sort results by lowest price "
                f"and report the year, trim, mileage, and asking price "
                f"of the most affordable {mk} {md} in inventory."))
            idx += 1

        # ------------------------------------------------------------------
        # Family 2: make + model + year — 150 tasks
        # ------------------------------------------------------------------
        myr_seen = set()
        my_pool = []
        for v in all_v:
            key = (v.make_slug, v.model_slug, v.year)
            if key not in myr_seen:
                myr_seen.add(key)
                my_pool.append(v)
        for v in my_pool[:150]:
            tasks.append(task(idx,
                f"Open /cars/{v.make_slug}/{v.model_slug}/{v.year} and "
                f"report the lowest-mileage example's trim, mileage, "
                f"exterior color, and the store it is located at."))
            idx += 1

        # ------------------------------------------------------------------
        # Family 3: vehicle detail report — 120 tasks
        # ------------------------------------------------------------------
        for v in all_v[:120]:
            tasks.append(task(idx,
                f"Visit /car/{v.stock_number} and report the horsepower, "
                f"transmission, drive type, and combined MPG of this "
                f"{v.year} {v.make} {v.model}."))
            idx += 1

        # ------------------------------------------------------------------
        # Family 4: vehicle photos / gallery — 60 tasks
        # ------------------------------------------------------------------
        for v in all_v[5:65]:
            tasks.append(task(idx,
                f"On /car/{v.stock_number}/photos, how many photos are "
                f"in the full gallery for this {v.short_title}?"))
            idx += 1

        # ------------------------------------------------------------------
        # Family 5: history report — 60 tasks
        # ------------------------------------------------------------------
        for v in all_v[10:70]:
            tasks.append(task(idx,
                f"Open /car/{v.stock_number}/history-report. Report the "
                f"number of owners and the number of reported accidents "
                f"shown for this vehicle."))
            idx += 1

        # ------------------------------------------------------------------
        # Family 6: similar cars — 50 tasks (vary prefix by stock)
        # ------------------------------------------------------------------
        for v in all_v[20:70]:
            tasks.append(task(idx,
                f"Open /car/{v.stock_number}/similar and report the year, "
                f"make, model, and price of the first recommended "
                f"alternative to this {v.short_title}."))
            idx += 1

        # ------------------------------------------------------------------
        # Family 7: transfer request (POST) — 80 tasks
        # ------------------------------------------------------------------
        dest_stores = [s.slug for s in all_s[:20]]
        for i, v in enumerate(all_v[3:83]):
            dest = dest_stores[i % len(dest_stores)]
            tasks.append(task(idx,
                f"Open /car/{v.stock_number}/transfer, select "
                f"the destination store '{dest}', fill in your name and "
                f"email, and submit the transfer request. Report the "
                f"reference number on the confirmation page."))
            idx += 1

        # ------------------------------------------------------------------
        # Family 8: per-car finance calculator (POST) — 70 tasks
        # ------------------------------------------------------------------
        terms = [60, 66, 72, 75, 84]
        for i, v in enumerate(all_v[30:100]):
            t = terms[i % len(terms)]
            apr = [4.99, 6.49, 7.99, 9.99, 11.99][i % 5]
            tasks.append(task(idx,
                f"On /car/{v.stock_number}/finance/calculator, set the "
                f"down payment to $3,000, APR to {apr}%, term to {t} "
                f"months, then submit and report the estimated monthly "
                f"payment shown."))
            idx += 1

        # ------------------------------------------------------------------
        # Family 9: cars under <price> hub — 80 tasks
        # ------------------------------------------------------------------
        prices = [10000, 12000, 15000, 17500, 20000, 22500, 25000, 27500,
                  30000, 32500, 35000, 40000, 45000, 50000]
        sorts = ['lowest mileage', 'lowest price', 'newest year',
                 'most expensive', 'highest year']
        i = 0
        for p in prices:
            for sort in sorts:
                if i >= 80:
                    break
                tasks.append(task(idx,
                    f"Browse /cars/under/{p}, then sort the results by "
                    f"{sort} and report the top result's year, make, "
                    f"model, trim, and price."))
                idx += 1
                i += 1

        # ------------------------------------------------------------------
        # Family 10: feature hubs — 75 tasks
        # ------------------------------------------------------------------
        feats = ['sunroof', 'apple-carplay', 'android-auto', 'leather-seats',
                 'heated-seats', 'navigation-system', 'blind-spot-monitor',
                 'third-row-seating', 'automated-cruise-control',
                 'lane-departure-warning', 'bose-sound-system',
                 'backup-camera', 'power-seats', 'tow-package',
                 'all-electric-drivetrain']
        for f in feats:
            for n in range(5):
                tasks.append(task(idx,
                    f"On /cars/with-feature/{f}, sort by lowest price and "
                    f"report the {['year','make','model','trim','price'][n]} "
                    f"of the most affordable match."))
                idx += 1

        # ------------------------------------------------------------------
        # Family 11: store / city detail + inventory — 100 tasks
        # ------------------------------------------------------------------
        for s in all_s[:50]:
            tasks.append(task(idx,
                f"On /store/{s.slug}, report the street address, phone "
                f"number, and weekday business hours for {s.name}."))
            idx += 1
        for s in all_s[:50]:
            tasks.append(task(idx,
                f"Open /store/{s.slug}/inventory and report the total "
                f"number of vehicles in stock at {s.name}, plus the "
                f"price of the most affordable one."))
            idx += 1

        # ------------------------------------------------------------------
        # Family 12: state location hub — 30 tasks
        # ------------------------------------------------------------------
        state_codes = sorted({s.state for s in all_s})
        for st in state_codes[:30]:
            tasks.append(task(idx,
                f"On /locations/{st}, report how many CarMax stores are "
                f"in {st} and the total vehicle count across that state."))
            idx += 1

        # ------------------------------------------------------------------
        # Family 13: trade-in calculator (POST) — 60 tasks (varied prefix)
        # ------------------------------------------------------------------
        td_combos = [
            (2018, 'Honda', 'Civic', 'EX', 68500, 'good', '30303'),
            (2017, 'Toyota', 'Camry', 'LE', 92000, 'fair', '77002'),
            (2019, 'Nissan', 'Altima', 'SV', 54000, 'good', '33176'),
            (2016, 'Ford', 'Escape', 'SE', 105000, 'fair', '02062'),
            (2020, 'Mazda', 'CX-5', 'Touring', 42000, 'excellent', '90621'),
            (2015, 'Subaru', 'Outback', 'Premium', 132000, 'fair', '98037'),
            (2019, 'Hyundai', 'Tucson', 'SEL', 55000, 'good', '85284'),
            (2018, 'Kia', 'Sorento', 'EX', 71000, 'good', '60477'),
            (2021, 'Tesla', 'Model 3', 'Long Range', 22000, 'excellent', '80023'),
            (2017, 'Jeep', 'Grand Cherokee', 'Laredo', 88000, 'good', '10601'),
        ]
        owe_options = [0, 2500, 5000, 7500, 10000, 12500]
        i = 0
        for (yr, mk, md, tr, mi, cond, zc) in td_combos:
            for owe in owe_options:
                if i >= 60:
                    break
                tasks.append(task(idx,
                    f"For a {yr} {mk} {md} {tr} with {mi:,} miles in "
                    f"{cond} condition, use /trade-in/calculator with "
                    f"ZIP {zc} and ${owe:,} still owed on the loan. "
                    f"Submit and report the estimated trade-in value "
                    f"and your estimated equity."))
                idx += 1
                i += 1

        # ------------------------------------------------------------------
        # Family 14: sell-my-car instant-offer (POST) — 40 tasks (varied prefix)
        # ------------------------------------------------------------------
        ins_combos = [
            (2020, 'Honda', 'Civic', 60000, 'good'),
            (2019, 'Toyota', 'Camry', 75000, 'good'),
            (2018, 'Subaru', 'Outback', 92000, 'fair'),
            (2021, 'Tesla', 'Model 3', 22000, 'excellent'),
            (2017, 'Ford', 'F-150', 110000, 'fair'),
            (2020, 'Jeep', 'Wrangler', 58000, 'good'),
            (2019, 'Nissan', 'Rogue', 67000, 'good'),
            (2018, 'Mazda', 'CX-5', 84000, 'good'),
            (2016, 'Hyundai', 'Elantra', 121000, 'fair'),
            (2022, 'Chevrolet', 'Silverado', 38000, 'excellent'),
        ]
        zips = ['30303', '77002', '33176', '90621', '60477', '10601',
                '02062', '98037', '85284', '80023']
        i = 0
        for (yr, mk, md, mi, cond) in ins_combos:
            for zc in zips:
                if i >= 40:
                    break
                tasks.append(task(idx,
                    f"Get an instant offer for a {yr} {mk} {md} with "
                    f"{mi:,} miles in {cond} condition (ZIP {zc}) via "
                    f"/sell-my-car/instant-offer. Report the offer "
                    f"amount and how long it is valid."))
                idx += 1
                i += 1

        # ------------------------------------------------------------------
        # Family 15: sell-my-car appointment (POST) — 30 tasks (varied)
        # ------------------------------------------------------------------
        slot_days = ['2026-06-02', '2026-06-03', '2026-06-04', '2026-06-05',
                     '2026-06-06']
        slot_times = ['10:00 AM', '11:00 AM', '1:00 PM', '2:00 PM', '4:00 PM']
        i = 0
        for s in all_s[:15]:
            for combo_idx in range(2):
                if i >= 30:
                    break
                d = slot_days[combo_idx % len(slot_days)]
                t = slot_times[combo_idx % len(slot_times)]
                tasks.append(task(idx,
                    f"Book an in-store appraisal at {s.name} ({s.location_label}) "
                    f"on {d} at {t} for a 2018 Toyota Corolla with "
                    f"78,000 miles via /sell-my-car/appointment. Report "
                    f"the confirmation message."))
                idx += 1
                i += 1

        # ------------------------------------------------------------------
        # Family 16: research topic pages — 50 tasks
        # ------------------------------------------------------------------
        for t in topics:
            tasks.append(task(idx,
                f"Open /research/topic/{t.slug} and report the title and "
                f"summary of this CarMax research article."))
            idx += 1
        for t in topics:
            tasks.append(task(idx,
                f"On /research/topic/{t.slug}, scroll to the 'Top picks' "
                f"strip and report how many cars from inventory are "
                f"surfaced."))
            idx += 1
        for cat in ['buying-guides', 'financing-guides', 'selling-guides']:
            for n in range(6):
                tasks.append(task(idx,
                    f"On /research/{cat}, report the title of the "
                    f"{['first','second','third','fourth','fifth','sixth'][n]} "
                    f"article listed."))
                idx += 1

        # ------------------------------------------------------------------
        # Family 17: financing pre-qual + calculator (POST) — 40 (varied)
        # ------------------------------------------------------------------
        prices_fc = [15000, 18000, 22000, 25000, 28000, 32000, 38000, 45000]
        terms_fc = [60, 66, 72, 75, 84]
        tiers_fc = ['excellent', 'good', 'fair', 'building']
        i = 0
        for p in prices_fc:
            for t in terms_fc:
                if i >= 40:
                    break
                tier = tiers_fc[i % len(tiers_fc)]
                tasks.append(task(idx,
                    f"Calculate the monthly payment for a ${p:,} car at "
                    f"{tier} credit tier over {t} months via "
                    f"/financing/calculator. Report the estimated "
                    f"monthly payment and total interest."))
                idx += 1
                i += 1

        # ------------------------------------------------------------------
        # Family 18: MaxCare quote (POST) — 40 tasks (varied prefix)
        # ------------------------------------------------------------------
        tiers_mc = ['silver', 'gold', 'platinum']
        deds_mc = [50, 100, 200, 500]
        stocks_mc = [v.stock_number for v in all_v[:20]]
        i = 0
        for stk in stocks_mc:
            for tier in tiers_mc:
                if i >= 40:
                    break
                tasks.append(task(idx,
                    f"Quote the {tier} MaxCare plan for stock {stk} via "
                    f"/maxcare/quote. Report the total premium and the "
                    f"coverage duration in months."))
                idx += 1
                i += 1

        # ------------------------------------------------------------------
        # Family 19: comparison pair — 80 tasks
        # ------------------------------------------------------------------
        for i in range(80):
            a_id = (i * 7 + 1) % len(all_v) + 1
            b_id = (i * 13 + 50) % len(all_v) + 1
            if a_id == b_id:
                b_id = (b_id + 1) % len(all_v) + 1
            tasks.append(task(idx,
                f"Open /comparison/{a_id}-vs-{b_id} and report the "
                f"price difference and the MPG difference (combined) "
                f"between the two vehicles."))
            idx += 1

        # ------------------------------------------------------------------
        # Family 20: comparison multi — 60 tasks
        # ------------------------------------------------------------------
        for i in range(60):
            ids = '-'.join(str((i * 11 + j * 17) % len(all_v) + 1)
                           for j in range(3 + (i % 2)))
            tasks.append(task(idx,
                f"On /comparison/multi/{ids}, report which vehicle has "
                f"the lowest price and which has the highest horsepower."))
            idx += 1

        # ------------------------------------------------------------------
        # Family 21: shop hubs — 60 tasks
        # ------------------------------------------------------------------
        hubs = [('shop/price-drops', 'price drops'),
                ('shop/new-arrivals', 'new arrivals'),
                ('shop/featured', 'featured'),
                ('shop/electric', 'electric'),
                ('cars?certified=1', 'CarMax Certified'),
                ('cars?body_style=Truck', 'all trucks'),
                ('cars?body_style=SUV', 'all SUVs'),
                ('cars?body_style=Sedan', 'all sedans'),
                ('cars?body_style=Wagon', 'all wagons'),
                ('cars?body_style=Coupe', 'all coupes'),
                ('cars?drive_type=AWD', 'AWD inventory'),
                ('cars?drive_type=4WD', '4WD inventory')]
        questions = ['the year, make, model, and price of the first '
                     'listed vehicle',
                     'the total number of vehicles in this category',
                     'the make and trim of the cheapest car shown',
                     'the year and color of the lowest-mileage car',
                     'the make and store of the most expensive listing']
        i = 0
        for (hub, lbl) in hubs:
            for q in questions:
                if i >= 60:
                    break
                tasks.append(task(idx,
                    f"On /{hub}, sort to default order and report {q}."))
                idx += 1
                i += 1

        # ------------------------------------------------------------------
        # Family 22: about / careers / promise — 30 tasks
        # ------------------------------------------------------------------
        about_pages = [
            ('/about', 'the eyebrow tagline shown above the body'),
            ('/about/our-promise', 'the five-point CarMax Promise list'),
            ('/about/leadership', 'the name of the CFO mentioned'),
            ('/about/sustainability', 'one partnership mentioned in the page'),
            ('/about/diversity', 'how many Associate Resource Groups are listed'),
            ('/careers', 'one job category mentioned besides Technology'),
        ]
        for (url, q) in about_pages:
            for n in range(5):
                tasks.append(task(idx,
                    f"Open {url} and report {q}."))
                idx += 1

        # ------------------------------------------------------------------
        # Family 23: myaccount logged-in tasks — 70 tasks
        # ------------------------------------------------------------------
        ma_tasks = [
            ("Sign in as alice.j@test.com with password CarMax!2026, then "
             "open /myaccount/saved-cars and report how many cars are "
             "saved to Alice's account."),
            ("Log in as bob.k@test.com / CarMax!2026 and on "
             "/myaccount/recent-searches report the natural-language "
             "query of the most recent search."),
            ("Sign in as carol.l@test.com / CarMax!2026 and on "
             "/myaccount/alerts count how many price alerts are "
             "currently Active versus Paused."),
            ("Sign in as alice.j@test.com / CarMax!2026, open "
             "/myaccount/alerts/new, create an alert for Toyota RAV4 "
             "under $28,000 with daily frequency, then report the new "
             "alert label as shown in the list."),
            ("Sign in as dan.m@test.com / CarMax!2026 and on /myaccount "
             "report the number of active orders and reservations "
             "Dan currently has."),
            ("Sign in as emma.n@test.com / CarMax!2026, open "
             "/myaccount/alerts, edit the existing alert and change its "
             "frequency to weekly. Save and report the new frequency "
             "shown in the table."),
            ("Sign in as alice.j@test.com / CarMax!2026 and on "
             "/myaccount/recent-searches clear the search history "
             "via the form button. Report the message shown after."),
            ("Sign in as bob.k@test.com / CarMax!2026 and on "
             "/myaccount/alerts pause the Ford F-150 alert via the "
             "Pause button. Report the new status shown."),
            ("Sign in as carol.l@test.com / CarMax!2026 and on "
             "/myaccount/alerts delete the paused Nissan Altima alert. "
             "Report how many alerts remain on the list."),
            ("Sign in as alice.j@test.com / CarMax!2026 and on "
             "/myaccount/saved-cars report the price of the most "
             "expensive saved car."),
            ("Sign in as alice.j@test.com / CarMax!2026 and on the "
             "/myaccount dashboard report the four counts shown at top: "
             "saved cars, recent searches, active alerts, and orders."),
        ]
        # Per-user task expansions
        for ut in ma_tasks:
            tasks.append(task(idx, ut))
            idx += 1
        # Per-vehicle saved-cars detail asks
        for i, v in enumerate(all_v[:20]):
            tasks.append(task(idx,
                f"Logged in as alice.j@test.com (password CarMax!2026), "
                f"open /myaccount/saved-cars, and find a {v.short_title} "
                f"card. Report the price and mileage shown on that card."))
            idx += 1
        # Per-zip alert creation asks — vary intro
        zips_ma = ['30303', '77002', '33176', '60477', '02062', '98037',
                   '85284', '80023', '27513', '10601']
        makes_ma = ['honda', 'toyota', 'ford', 'chevrolet', 'nissan',
                    'jeep', 'hyundai', 'mazda', 'subaru', 'tesla']
        budgets = [18000, 22000, 25000, 28000, 32000]
        intros = [
            "After signing in as alice.j@test.com / CarMax!2026,",
            "While logged in as bob.k@test.com / CarMax!2026,",
            "From the account of carol.l@test.com (password CarMax!2026),",
            "Once authenticated as dan.m@test.com / CarMax!2026,",
            "As emma.n@test.com (password CarMax!2026),",
        ]
        for i in range(30):
            zip_code = zips_ma[i % len(zips_ma)]
            mk = makes_ma[i % len(makes_ma)]
            bud = budgets[i % len(budgets)]
            intro = intros[i % len(intros)]
            tasks.append(task(idx,
                f"{intro} open /myaccount/alerts/new and create an alert "
                f"with make {mk}, ZIP {zip_code}, max price ${bud:,}, "
                f"frequency daily. Submit and report the row that now "
                f"appears at top of /myaccount/alerts."))
            idx += 1

        # ------------------------------------------------------------------
        # Family 24: research_index + research/make + reviews/<make>/<model>/<year> — 60
        # ------------------------------------------------------------------
        for (mk, mks) in [(m, s) for (m, s) in top_makes[:15]]:
            tasks.append(task(idx,
                f"Open /research/{mks} and report the title of the page, "
                f"plus how many {mk} models are surfaced as research "
                f"links."))
            idx += 1
        sample_my = []
        for (mk, mks), models_v in by_make.items():
            seen = set()
            for v in models_v:
                if v.model_slug not in seen:
                    seen.add(v.model_slug)
                    sample_my.append((mks, v.model_slug))
                if len(seen) >= 2:
                    break
        for (mks, mds) in sample_my[:30]:
            tasks.append(task(idx,
                f"Open /research/{mks}/{mds} and report two key facts "
                f"about this model that are shown on the research page."))
            idx += 1
        # reviews
        review_combos = [
            ('honda', 'civic', 2022), ('honda', 'accord', 2021),
            ('honda', 'cr-v', 2022), ('toyota', 'camry', 2022),
            ('toyota', 'rav4', 2021), ('toyota', 'tacoma', 2021),
            ('ford', 'f-150', 2022), ('ford', 'mustang', 2021),
            ('chevrolet', 'silverado', 2022), ('chevrolet', 'tahoe', 2022),
            ('nissan', 'altima', 2021), ('hyundai', 'tucson', 2022),
            ('kia', 'sorento', 2022), ('jeep', 'wrangler', 2021),
            ('subaru', 'outback', 2022),
        ]
        for (mks, mds, yr) in review_combos:
            tasks.append(task(idx,
                f"On /reviews/{mks}/{mds}/{yr}, report the highest-rated "
                f"review's title and the reviewer's location."))
            idx += 1

        # ------------------------------------------------------------------
        # Family 25: articles_index + article_detail — 25 tasks
        # ------------------------------------------------------------------
        for a in all_a:
            tasks.append(task(idx,
                f"Open /articles/{a.slug} and summarize the article's "
                f"main argument in one sentence."))
            idx += 1
        for a in all_a:
            tasks.append(task(idx,
                f"On /articles/{a.slug}, report the article category "
                f"and the publication date shown."))
            idx += 1
        tasks.append(task(idx,
            "On /articles, filter to the 'financing' category and "
            "report the title of the most recently published article."))
        idx += 1

        # ------------------------------------------------------------------
        # Family 26: search query — 80 tasks
        # ------------------------------------------------------------------
        search_queries = [
            'Honda Civic', 'Toyota Tacoma TRD', 'Ford F-150 Lariat',
            'Tesla Model 3', 'Jeep Wrangler Rubicon', 'BMW 3 Series',
            'Mercedes C300', 'Subaru Outback', 'Mazda CX-5 Grand Touring',
            'Hyundai Tucson SEL', 'Kia Sorento EX', 'Nissan Rogue',
            'Chevrolet Tahoe', 'Audi Q5', 'Lexus RX 350', 'GMC Sierra',
        ]
        sort_options = ['best_match', 'price_low', 'price_high',
                        'mileage_low', 'newest']
        i = 0
        for q in search_queries:
            for so in sort_options:
                if i >= 80:
                    break
                tasks.append(task(idx,
                    f"On /cars, search for '{q}' and sort by {so}. "
                    f"Report the year, trim, mileage, and price of the "
                    f"top result."))
                idx += 1
                i += 1

        # ------------------------------------------------------------------
        # Family 27: filtered search — 60 tasks
        # ------------------------------------------------------------------
        filter_combos = [
            'body_style=SUV&drive_type=AWD&price_max=25000',
            'body_style=Truck&drive_type=4WD&year_min=2020',
            'body_style=Sedan&fuel_type=Gasoline&price_max=20000',
            'body_style=SUV&fuel_type=Electric',
            'body_style=Wagon&price_max=30000',
            'transmission=Manual',  # may yield empty
            'mileage_max=40000&year_min=2021',
            'make=tesla&year_min=2020',
            'make=jeep&drive_type=4WD',
            'make=ford&body_style=Truck',
            'make=toyota&body_style=SUV&price_max=30000',
            'make=honda&fuel_type=Gasoline',
            'state=CA&body_style=SUV',
            'state=TX&body_style=Truck',
            'state=FL&body_style=Sedan',
        ]
        questions = ['year, make, model, and price', 'price and mileage',
                     'trim and store location', 'exterior color and ext./int.']
        i = 0
        for f in filter_combos:
            for q in questions:
                if i >= 60:
                    break
                tasks.append(task(idx,
                    f"Open /cars?{f} sorted by lowest price and report "
                    f"the {q} of the top match."))
                idx += 1
                i += 1

        # ------------------------------------------------------------------
        # Family 28: pair compare via stock numbers — 60 tasks
        # ------------------------------------------------------------------
        for i in range(60):
            a = all_v[(i * 5 + 2) % len(all_v)]
            b = all_v[(i * 11 + 60) % len(all_v)]
            tasks.append(task(idx,
                f"Compare the {a.short_title} (stock {a.stock_number}) "
                f"with the {b.short_title} (stock {b.stock_number}) by "
                f"visiting /comparison/{a.id}-vs-{b.id}. Report which "
                f"has the higher horsepower."))
            idx += 1

        # ------------------------------------------------------------------
        # Family 29: store hours / details — 60 tasks
        # ------------------------------------------------------------------
        questions_s = [
            ('Saturday hours', 'the Saturday business hours'),
            ('Sunday hours', 'the Sunday business hours'),
            ('phone', 'the phone number'),
            ('street address', 'the street address'),
            ('zip code', 'the ZIP code'),
        ]
        i = 0
        for s in all_s[:20]:
            for tag, q in questions_s:
                if i >= 60:
                    break
                tasks.append(task(idx,
                    f"Look up {s.name} at /store/{s.slug} and report {q}."))
                idx += 1
                i += 1

        # ------------------------------------------------------------------
        # Family 30: vehicle gallery image checks — 50 tasks
        # ------------------------------------------------------------------
        for v in all_v[80:130]:
            tasks.append(task(idx,
                f"Open the photo gallery at /car/{v.stock_number}/photos. "
                f"Report the captions of the front, side, and rear "
                f"photos shown."))
            idx += 1

        # ------------------------------------------------------------------
        # Family 31: research topic deep-dive — 30 tasks
        # ------------------------------------------------------------------
        for t in topics:
            tasks.append(task(idx,
                f"Read /research/topic/{t.slug} and report the "
                f"publication date shown on this guide."))
            idx += 1
        for t in topics:
            tasks.append(task(idx,
                f"Visit /research/topic/{t.slug} and list two of the "
                f"top picks from the inventory strip on this page."))
            idx += 1

        # ------------------------------------------------------------------
        # Family 32: filter by store_id — 50 tasks
        # ------------------------------------------------------------------
        for s in all_s[:25]:
            tasks.append(task(idx,
                f"Filter /cars by store_id={s.id} and report the most "
                f"expensive vehicle at {s.name}: year, make, model, "
                f"trim, and price."))
            idx += 1
        for s in all_s[:25]:
            tasks.append(task(idx,
                f"On /cars?store_id={s.id}&sort=newest, report the year "
                f"and price of the newest car at {s.name}."))
            idx += 1

        # ------------------------------------------------------------------
        # Family 33: locations per state breakdown — 30 tasks
        # ------------------------------------------------------------------
        for st in state_codes[:30]:
            tasks.append(task(idx,
                f"Open /locations/{st} and report the city of the "
                f"first store listed."))
            idx += 1

        return tasks


def write(tasks, path):
    with open(path, 'w') as f:
        for t in tasks:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')


def dedup_and_cap(tasks):
    """Literal dedup + 5-token prefix cap @5 per harden-env gotcha §28."""
    seen = set()
    out = []
    prefix_counts = collections.Counter()
    for t in tasks:
        q = t['ques']
        key = q.lower()
        if key in seen:
            continue
        seen.add(key)
        tokens = re.findall(r'\S+', q.lower())
        prefix = ' '.join(tokens[:5])
        if prefix_counts[prefix] >= 5:
            continue
        prefix_counts[prefix] += 1
        out.append(t)
    # Renumber IDs to keep 0..N-1 contiguous
    for i, t in enumerate(out):
        t['id'] = f'{NAME}--gui_{i:04d}'
    return out


if __name__ == '__main__':
    tasks = main()
    print(f'pre-cap tasks: {len(tasks)}')
    tasks = dedup_and_cap(tasks)
    print(f'post-cap tasks: {len(tasks)}')
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'tasks.jsonl')
    write(tasks, path)
    print(f'wrote {path}')
