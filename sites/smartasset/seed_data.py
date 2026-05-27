"""SmartAsset seed data — deterministic, idempotent.

Every seed function early-returns when its target rows are already present
so the byte-identical reset invariant holds (no commits when populated).
"""
from datetime import datetime, date, timedelta

from seed_extras_data import EXTRA_ARTICLES
from seed_glossary_data import CITIES, GLOSSARY, REVIEWS, PROMOS

PINNED_BCRYPT = "$2b$12$RwAC/sfwDHtccU//A20fde.uKkZK4Ptnjjyua2l2ktwI6uysAp3Ou"
SEED_DATE = datetime(2026, 1, 1, 12, 0, 0)


# ─── States ─────────────────────────────────────────────────────────

STATES = [
    # (name, abbr, type, top_rate, flat_rate, prop_tax%, sales%, median_home, median_income, COLI, top_metro)
    ("Alabama", "AL", "bracket", 5.0, 0.0, 0.40, 4.0, 230000, 56929, 88.0, "Birmingham"),
    ("Alaska", "AK", "none", 0.0, 0.0, 1.04, 0.0, 320000, 86631, 125.8, "Anchorage"),
    ("Arizona", "AZ", "flat", 2.5, 2.5, 0.62, 5.6, 425000, 72581, 108.4, "Phoenix"),
    ("Arkansas", "AR", "bracket", 4.4, 0.0, 0.61, 6.5, 200000, 56335, 89.0, "Little Rock"),
    ("California", "CA", "bracket", 13.3, 0.0, 0.75, 7.25, 760000, 91905, 142.2, "Los Angeles"),
    ("Colorado", "CO", "flat", 4.4, 4.4, 0.51, 2.9, 580000, 87598, 118.5, "Denver"),
    ("Connecticut", "CT", "bracket", 6.99, 0.0, 1.79, 6.35, 380000, 90213, 113.1, "Stamford"),
    ("Delaware", "DE", "bracket", 6.6, 0.0, 0.57, 0.0, 340000, 79325, 100.8, "Wilmington"),
    ("Florida", "FL", "none", 0.0, 0.0, 0.86, 6.0, 410000, 69303, 102.0, "Miami"),
    ("Georgia", "GA", "flat", 5.39, 5.39, 0.92, 4.0, 330000, 74664, 90.8, "Atlanta"),
    ("Hawaii", "HI", "bracket", 11.0, 0.0, 0.32, 4.0, 845000, 92458, 184.2, "Honolulu"),
    ("Idaho", "ID", "flat", 5.695, 5.695, 0.67, 6.0, 460000, 70214, 105.9, "Boise"),
    ("Illinois", "IL", "flat", 4.95, 4.95, 2.08, 6.25, 280000, 78433, 92.1, "Chicago"),
    ("Indiana", "IN", "flat", 3.0, 3.0, 0.84, 7.0, 225000, 67173, 91.4, "Indianapolis"),
    ("Iowa", "IA", "flat", 3.8, 3.8, 1.50, 6.0, 215000, 70571, 89.5, "Des Moines"),
    ("Kansas", "KS", "bracket", 5.58, 0.0, 1.34, 6.5, 220000, 69747, 87.4, "Kansas City"),
    ("Kentucky", "KY", "flat", 4.0, 4.0, 0.83, 6.0, 210000, 60183, 88.0, "Louisville"),
    ("Louisiana", "LA", "flat", 3.0, 3.0, 0.56, 4.45, 215000, 57852, 89.0, "New Orleans"),
    ("Maine", "ME", "bracket", 7.15, 0.0, 1.24, 5.5, 360000, 71139, 113.0, "Portland"),
    ("Maryland", "MD", "bracket", 5.75, 0.0, 1.05, 6.0, 410000, 98461, 124.0, "Baltimore"),
    ("Massachusetts", "MA", "flat", 5.0, 5.0, 1.14, 6.25, 575000, 96505, 135.0, "Boston"),
    ("Michigan", "MI", "flat", 4.25, 4.25, 1.38, 6.0, 240000, 68505, 90.0, "Detroit"),
    ("Minnesota", "MN", "bracket", 9.85, 0.0, 1.11, 6.875, 340000, 84313, 97.2, "Minneapolis"),
    ("Mississippi", "MS", "flat", 4.4, 4.4, 0.75, 7.0, 175000, 52985, 84.5, "Jackson"),
    ("Missouri", "MO", "bracket", 4.7, 0.0, 0.98, 4.225, 235000, 65920, 88.5, "Kansas City"),
    ("Montana", "MT", "flat", 5.9, 5.9, 0.74, 0.0, 480000, 66341, 102.9, "Billings"),
    ("Nebraska", "NE", "bracket", 5.2, 0.0, 1.63, 5.5, 245000, 71722, 90.9, "Omaha"),
    ("Nevada", "NV", "none", 0.0, 0.0, 0.55, 6.85, 470000, 71646, 110.5, "Las Vegas"),
    ("New Hampshire", "NH", "none", 0.0, 0.0, 1.93, 0.0, 460000, 90845, 109.1, "Manchester"),
    ("New Jersey", "NJ", "bracket", 10.75, 0.0, 2.23, 6.625, 510000, 96346, 113.5, "Newark"),
    ("New Mexico", "NM", "bracket", 5.9, 0.0, 0.67, 4.875, 295000, 58722, 92.0, "Albuquerque"),
    ("New York", "NY", "bracket", 10.9, 0.0, 1.40, 4.0, 575000, 81386, 148.2, "New York City"),
    ("North Carolina", "NC", "flat", 4.25, 4.25, 0.80, 4.75, 340000, 70804, 99.0, "Charlotte"),
    ("North Dakota", "ND", "bracket", 2.5, 0.0, 0.98, 5.0, 260000, 73959, 92.0, "Fargo"),
    ("Ohio", "OH", "bracket", 3.5, 0.0, 1.53, 5.75, 220000, 69680, 92.5, "Columbus"),
    ("Oklahoma", "OK", "bracket", 4.75, 0.0, 0.89, 4.5, 215000, 61364, 86.5, "Oklahoma City"),
    ("Oregon", "OR", "bracket", 9.9, 0.0, 0.93, 0.0, 510000, 76362, 119.0, "Portland"),
    ("Pennsylvania", "PA", "flat", 3.07, 3.07, 1.49, 6.0, 280000, 73170, 96.5, "Philadelphia"),
    ("Rhode Island", "RI", "bracket", 5.99, 0.0, 1.40, 7.0, 415000, 81854, 113.0, "Providence"),
    ("South Carolina", "SC", "bracket", 6.2, 0.0, 0.57, 6.0, 320000, 63623, 95.0, "Charleston"),
    ("South Dakota", "SD", "none", 0.0, 0.0, 1.17, 4.5, 260000, 69457, 89.8, "Sioux Falls"),
    ("Tennessee", "TN", "none", 0.0, 0.0, 0.67, 7.0, 320000, 65254, 90.0, "Nashville"),
    ("Texas", "TX", "none", 0.0, 0.0, 1.68, 6.25, 305000, 73035, 96.5, "Houston"),
    ("Utah", "UT", "flat", 4.55, 4.55, 0.57, 4.85, 520000, 86833, 102.9, "Salt Lake City"),
    ("Vermont", "VT", "bracket", 8.75, 0.0, 1.83, 6.0, 360000, 74014, 117.0, "Burlington"),
    ("Virginia", "VA", "bracket", 5.75, 0.0, 0.82, 5.3, 380000, 87249, 101.5, "Virginia Beach"),
    ("Washington", "WA", "none", 0.0, 0.0, 0.87, 6.5, 600000, 91306, 117.5, "Seattle"),
    ("West Virginia", "WV", "bracket", 4.82, 0.0, 0.57, 6.0, 165000, 55217, 84.5, "Charleston"),
    ("Wisconsin", "WI", "bracket", 7.65, 0.0, 1.61, 5.0, 270000, 72458, 95.0, "Milwaukee"),
    ("Wyoming", "WY", "none", 0.0, 0.0, 0.58, 4.0, 320000, 72495, 92.2, "Cheyenne"),
    ("District of Columbia", "DC", "bracket", 10.75, 0.0, 0.57, 6.0, 690000, 101027, 152.1, "Washington"),
]


# ─── Categories ─────────────────────────────────────────────────────

CATEGORIES = [
    ("Retirement", "retirement", "Plan a comfortable retirement: 401(k)s, IRAs, Social Security, RMDs."),
    ("Taxes", "taxes", "Federal, state and local tax guidance for individuals and households."),
    ("Investing", "investing", "Markets, asset allocation, ETFs, capital gains, and long-term portfolios."),
    ("Mortgage", "mortgage", "Home buying, refinancing, PMI, closing costs and amortization."),
    ("Banking", "banking", "Savings, CDs, money-market accounts, and high-yield checking."),
    ("Personal Finance", "personal-finance", "Budgeting, debt payoff, credit and net-worth strategy."),
    ("Credit Cards", "credit-cards", "Rewards, balance transfers, APR, credit utilization."),
    ("Insurance", "insurance", "Life, health, auto and homeowners insurance basics."),
    ("Estate Planning", "estate-planning", "Wills, trusts, beneficiaries, and inheritance taxes."),
    ("Financial Advisor", "financial-advisor", "How fiduciary advisors work and how to choose one."),
]


# ─── Authors ────────────────────────────────────────────────────────

AUTHORS = [
    ("Rebecca Lake", "rebecca-lake", "Senior Writer, Personal Finance", "CEPF",
     "Charleston, SC", "rebeccalake",
     "Rebecca Lake has been writing about personal finance, retirement, and investing for over a decade. Her work has appeared in U.S. News, Investopedia, and Business Insider. She holds the CEPF designation and lives in coastal South Carolina with her two children."),
    ("Jeff White", "jeff-white", "Lead Investing Reporter", "CEPF",
     "Boston, MA", "jeffwhitefp",
     "Jeff White is an award-winning financial journalist whose coverage focuses on markets, retirement accounts, and portfolio strategy. Before joining SmartAsset, Jeff spent six years at a wirehouse advisory firm and now writes full-time from Boston."),
    ("Lauren Perez", "lauren-perez", "Mortgage & Banking Editor", "CEPF",
     "Brooklyn, NY", "lperezfin",
     "Lauren Perez edits SmartAsset's mortgage and banking coverage. She has reported on housing affordability and lending for the Wall Street Journal and Bloomberg, and is currently completing her CFP coursework."),
    ("Susannah Snider", "susannah-snider", "Managing Editor, Financial Education", "CFP",
     "Washington, DC", "susannahsnider",
     "Susannah Snider is the managing editor of SmartAsset's financial education hub. A Certified Financial Planner, Susannah previously led personal finance coverage at U.S. News & World Report and writes about retirement, taxes, and family financial planning."),
    ("Mark Henricks", "mark-henricks", "Retirement Columnist", "",
     "Austin, TX", "markhenricks",
     "Mark Henricks has written about personal finance for The New York Times, BusinessWeek, and CBS MarketWatch. His SmartAsset column focuses on the practical mechanics of retirement income planning."),
    ("Liz Smith", "liz-smith", "Tax & Estate Writer", "CPA",
     "Chicago, IL", "lizsmithcpa",
     "Liz Smith is a CPA and former tax-firm partner who now covers federal tax policy, estate planning, and high-net-worth strategy for SmartAsset."),
    ("Patrick Villanova", "patrick-villanova", "Senior Investing Writer", "CEPF",
     "Newark, NJ", "pvillanovafp",
     "Patrick Villanova focuses on investment products, index funds, and asset allocation. He has covered markets for over eight years and previously reported for NJ.com."),
    ("Amanda Dixon", "amanda-dixon", "Personal Finance Editor", "",
     "Atlanta, GA", "amandadixonfp",
     "Amanda Dixon manages SmartAsset's personal finance section, covering budgeting, debt payoff, and credit. She holds a journalism degree from the University of Georgia."),
    ("Hunter Kuffel", "hunter-kuffel", "Mortgage Reporter", "CEPF",
     "Charlotte, NC", "hunterkuffel",
     "Hunter Kuffel writes about mortgages, refinancing, and the home-buying process for first-time buyers."),
    ("Ben Geier", "ben-geier", "Investing Reporter", "CEPF",
     "Brooklyn, NY", "bengeierfp",
     "Ben Geier covers markets, ETFs, and asset allocation. He previously reported on financial markets for Fortune."),
    ("Becca Stanek", "becca-stanek", "Banking Reporter", "",
     "Indianapolis, IN", "beccastanek",
     "Becca Stanek covers savings accounts, CDs and high-yield deposit products for SmartAsset."),
    ("Eric Reed", "eric-reed", "Tax Policy Columnist", "JD",
     "Chicago, IL", "ericreedfp",
     "Eric Reed is a journalist and former litigation attorney whose SmartAsset column covers federal tax policy and IRS rulemaking."),
]


# ─── Advisors ───────────────────────────────────────────────────────

# Per state, generate 2-3 advisors deterministically using fixed templates.
ADVISOR_FIRMS = [
    "Beacon Pointe Advisors", "Mariner Wealth Advisors", "Mercer Advisors",
    "Creative Planning", "Edelman Financial Engines", "Carson Group",
    "Hightower Advisors", "Cerity Partners", "Wealth Enhancement Group",
    "Pathstone", "Aspiriant", "Brown Brothers Harriman",
    "Fisher Investments", "Robertson Stephens", "Tiedemann Advisors",
    "Bessemer Trust", "Northern Trust", "Bartlett Wealth Management",
    "Plante Moran Financial Advisors", "Captrust",
]

ADVISOR_NAMES = [
    ("James", "Mitchell"), ("Sarah", "Chen"), ("Michael", "Patel"),
    ("Jennifer", "Rodriguez"), ("David", "Kim"), ("Linda", "Thompson"),
    ("Robert", "Williams"), ("Patricia", "Garcia"), ("Christopher", "Lee"),
    ("Barbara", "Anderson"), ("Daniel", "Martinez"), ("Susan", "Walker"),
    ("Matthew", "Brown"), ("Karen", "Wright"), ("Anthony", "Davis"),
    ("Helen", "Hall"), ("Joshua", "Wilson"), ("Emily", "Young"),
    ("Andrew", "Harris"), ("Margaret", "Clark"), ("Kevin", "Lewis"),
    ("Donna", "Robinson"), ("Brian", "Hill"), ("Carol", "Adams"),
    ("Steven", "Baker"), ("Nancy", "Gonzalez"), ("Edward", "Nelson"),
    ("Sandra", "Carter"), ("Mark", "Mitchell"), ("Lisa", "Perez"),
    ("Joseph", "Roberts"), ("Sharon", "Turner"), ("Thomas", "Phillips"),
    ("Karen", "Campbell"), ("Charles", "Parker"), ("Donna", "Evans"),
    ("Paul", "Edwards"), ("Cynthia", "Collins"), ("George", "Stewart"),
    ("Ruth", "Sanchez"), ("Larry", "Morris"), ("Diana", "Rogers"),
    ("Jeffrey", "Reed"), ("Lauren", "Cook"), ("Ryan", "Morgan"),
    ("Helen", "Bell"), ("Jacob", "Murphy"), ("Janet", "Bailey"),
    ("Gary", "Rivera"), ("Catherine", "Cooper"),
]
SPECIALTIES = ["Retirement", "Tax", "Estate", "Investment",
               "Wealth Management", "Education"]


# ─── Articles ──────────────────────────────────────────────────────

# (title, dek, body_template, category_slug, related_calc, tags)
ARTICLES_SPEC = [
    # Retirement (12)
    ("How Much Should You Have Saved by Age 40?",
     "Benchmarks for retirement savings at each decade — and how to catch up if you're behind.",
     "401k", "retirement", "401k,retirement,fidelity-rule"),
    ("Roth IRA vs Traditional IRA: A Side-by-Side Comparison",
     "When tax-free growth beats up-front tax deductions, and when it doesn't.",
     "roth", "retirement", "roth,ira,retirement,taxes"),
    ("The Rule of 55: Withdrawing from Your 401(k) Early",
     "How the Rule of 55 lets you tap retirement savings without the 10% penalty.",
     "rule55", "retirement", "401k,early-withdrawal,rule-of-55"),
    ("Required Minimum Distributions (RMDs) Explained",
     "When RMDs kick in, how to calculate them, and the penalty for missing one.",
     "rmd", "retirement", "rmd,retirement,taxes"),
    ("How Social Security Benefits Are Calculated",
     "The AIME, PIA, and bend points that determine your monthly check.",
     "ss", "retirement", "social-security,retirement"),
    ("The 4% Rule for Retirement Withdrawals",
     "Where the rule came from, how it has held up, and modern alternatives.",
     "fourpct", "retirement", "withdrawal-rate,safemax,bengen"),
    ("Average Retirement Savings by Age in 2026",
     "Fresh Fed survey data on what households really have saved at every age band.",
     "savings_by_age", "retirement", "retirement,benchmarks"),
    ("Should You Pay Off Your Mortgage Before Retirement?",
     "The opportunity-cost math behind one of retirement's biggest decisions.",
     "mortgage_pay_off", "retirement", "mortgage,retirement"),
    ("15 States That Don't Tax Retirement Income",
     "Where your 401(k), IRA, and pension dollars stretch furthest.",
     "no_tax_retire", "retirement", "states,taxes,retirement"),
    ("How to Use a 457(b) Plan",
     "The retirement vehicle for state and local government employees.",
     "457b", "retirement", "457b,retirement,public-sector"),
    ("Catch-Up Contributions in 2026",
     "Higher 401(k) and IRA limits for savers age 50+.",
     "catchup", "retirement", "catch-up,limits,2026"),
    ("Should You Take Social Security at 62?",
     "The trade-off between starting early and the 8% delayed-retirement credit.",
     "ss62", "retirement", "social-security,age-62"),

    # Taxes (10)
    ("Federal Income Tax Brackets for 2025-2026",
     "Updated bracket thresholds for single, married, and head-of-household filers.",
     "brackets", "taxes", "federal-tax,brackets,2026"),
    ("How the Standard Deduction Works",
     "Take the standard deduction — or itemize? Here's how to decide.",
     "std_ded", "taxes", "standard-deduction,itemized"),
    ("Capital Gains Tax: Long-Term vs Short-Term",
     "How holding period changes your effective tax rate by 17 percentage points.",
     "cap_gains", "taxes", "capital-gains,investing,taxes"),
    ("The SALT Deduction Cap: What's Changing in 2026",
     "The state and local tax deduction is back in flux.",
     "salt", "taxes", "salt,deduction,2026"),
    ("How to File a Tax Extension",
     "The four-step process to push your filing deadline to October.",
     "extension", "taxes", "extension,deadline"),
    ("Self-Employed Tax Deductions You Shouldn't Miss",
     "From home office to QBI, the deductions freelancers leave on the table.",
     "se_deductions", "taxes", "self-employed,1099,qbi"),
    ("State Income Tax Rates Ranked",
     "All 50 states and DC, ranked by top marginal income tax rate.",
     "state_ranks", "taxes", "states,income-tax,ranking"),
    ("How Property Taxes Are Calculated",
     "Assessed value, millage rates, and the appeals process.",
     "prop_tax_calc", "taxes", "property-tax,homeowners"),
    ("Tax-Loss Harvesting Explained",
     "How realized losses can offset gains — and the wash-sale trap.",
     "tlh", "taxes", "tax-loss,harvesting,investing"),
    ("Marginal vs Effective Tax Rate",
     "Why your top bracket is not what you actually pay.",
     "marginal_vs_eff", "taxes", "marginal,effective,rates"),

    # Investing (10)
    ("Asset Allocation by Age: A Starter Framework",
     "From 110-minus-age to glide paths — how to set your stock/bond split.",
     "alloc", "investing", "asset-allocation,age-based"),
    ("Index Funds vs ETFs: What's the Difference?",
     "Structure, taxes, trading costs and intraday liquidity.",
     "index_etf", "investing", "etfs,index-funds"),
    ("Dollar-Cost Averaging vs Lump-Sum Investing",
     "Vanguard's research on which actually wins more often.",
     "dca", "investing", "dca,lump-sum"),
    ("Sequence of Returns Risk Explained",
     "Why the order of returns matters more than the average in retirement.",
     "sorr", "investing", "sequence-risk,retirement"),
    ("Bond Ladders: Building Predictable Income",
     "How a five-rung ladder can replace a portion of your bond allocation.",
     "bond_ladder", "investing", "bonds,ladders"),
    ("Treasury Bills, Notes, and Bonds: A Plain-English Guide",
     "Maturities, yields, and where each fits in a portfolio.",
     "treasuries", "investing", "treasuries,bills,bonds"),
    ("Dividend Investing: Yield vs Growth",
     "Why a stable 3% dividend can beat a flashy 9% one over a decade.",
     "div_investing", "investing", "dividends,yield"),
    ("How Compound Interest Really Works",
     "The Rule of 72 and the eight-figure power of starting early.",
     "compound", "investing", "compound-interest,rule-of-72"),
    ("Robo-Advisors vs Human Advisors",
     "What you get — and don't — from each.",
     "robo_vs_human", "investing", "robo,advisor"),
    ("Inflation and Your Portfolio",
     "How inflation rewires the risk-return calculation for every asset class.",
     "inflation_port", "investing", "inflation,portfolio"),

    # Mortgage (10)
    ("How Much House Can You Really Afford?",
     "DTI, the 28/36 rule, and the bank's math vs the budget that lets you sleep at night.",
     "afford", "mortgage", "affordability,dti"),
    ("PMI: When You Pay It, and How to Drop It",
     "Private mortgage insurance from 78% LTV onward.",
     "pmi", "mortgage", "pmi,ltv,mortgage"),
    ("FHA vs Conventional Loans",
     "Credit score floors, down payment minimums, and mortgage insurance.",
     "fha_conv", "mortgage", "fha,conventional"),
    ("15-Year vs 30-Year Mortgages",
     "The interest savings vs cash-flow tradeoff over a real $300k loan.",
     "term_compare", "mortgage", "15-year,30-year"),
    ("Closing Costs: What's Actually in That Stack",
     "Origination, title, recording, transfer tax, and escrow setup.",
     "closing", "mortgage", "closing-costs"),
    ("How to Refinance Your Mortgage in 2026",
     "When the rate drop justifies the closing costs.",
     "refi_2026", "mortgage", "refinance,rates"),
    ("Adjustable-Rate Mortgages: Pros and Pitfalls",
     "How ARMs work, the caps, and who they're actually for.",
     "arm", "mortgage", "arm,arms,5-1"),
    ("Down Payment Strategies for First-Time Buyers",
     "Beyond the 20% myth: programs, gifts, and the down-payment trade-off.",
     "down_payment", "mortgage", "first-time,down-payment"),
    ("Biweekly Mortgage Payments: Worth It?",
     "How an extra payment a year can shave 4-7 years off a 30-year loan.",
     "biweekly", "mortgage", "biweekly,payoff"),
    ("Should You Buy Mortgage Points?",
     "Breakeven math on a one-point buydown at current rates.",
     "points", "mortgage", "points,buydown"),

    # Banking (8)
    ("High-Yield Savings vs Money Market Accounts",
     "APYs, liquidity, FDIC coverage, and the gotchas.",
     "hysa_mm", "banking", "hysa,mmf,savings"),
    ("CDs vs Treasury Bills",
     "Two safe places to park cash — and which is winning the yield race in 2026.",
     "cd_tbill", "banking", "cd,tbill"),
    ("Building a CD Ladder",
     "A rolling 3-month / 6-month / 12-month strategy.",
     "cd_ladder", "banking", "cd,ladder"),
    ("Best No-Fee Checking Accounts",
     "Accounts with zero monthly fees, no minimums, and free overdraft buffers.",
     "checking", "banking", "checking,no-fee"),
    ("Emergency Fund: How Many Months?",
     "Three, six or twelve? It depends on income stability.",
     "emergency", "banking", "emergency-fund"),
    ("FDIC Insurance Limits Explained",
     "What's covered, what isn't, and how to structure $1M across accounts.",
     "fdic", "banking", "fdic,insurance"),
    ("How to Open an IRA at a Bank vs Brokerage",
     "Investment menu, fees, and what banks usually don't tell you.",
     "ira_bank", "banking", "ira,bank,brokerage"),
    ("APY vs APR: Why They're Different",
     "Compounding, and the math that flips a savings account from 3% to 3.04%.",
     "apy_apr", "banking", "apy,apr"),

    # Personal Finance (8)
    ("Debt Snowball vs Avalanche: Which Is Faster?",
     "Behavioral wins vs interest-saving wins.",
     "snowball", "personal-finance", "debt-payoff,snowball"),
    ("How to Build Credit From Scratch",
     "Secured cards, authorized-user status, and the three credit bureaus.",
     "build_credit", "personal-finance", "credit-score,bureaus"),
    ("Understanding Your Credit Score",
     "FICO factors and how to move 50 points in 90 days.",
     "fico", "personal-finance", "credit-score"),
    ("Building a Monthly Budget That Sticks",
     "Why zero-based budgets out-perform 50/30/20 for most households.",
     "budget", "personal-finance", "budget,zero-based"),
    ("Calculating Your Net Worth",
     "Assets minus liabilities — and the line items most people forget.",
     "net_worth_guide", "personal-finance", "net-worth"),
    ("Should You Lease or Buy Your Next Car?",
     "Three-year cost-of-ownership math.",
     "lease_buy", "personal-finance", "car,lease"),
    ("The True Cost of Owning a Home",
     "Beyond P&I: maintenance, insurance, taxes, opportunity cost.",
     "true_cost", "personal-finance", "homeowner,total-cost"),
    ("How to Save for a Down Payment in Five Years",
     "A month-by-month plan for $80k toward a $400k home.",
     "dp_savings", "personal-finance", "down-payment,savings"),

    # Credit Cards (6)
    ("Best Rewards Credit Cards for 2026",
     "Travel, cash-back, and category bonuses — what's earning right now.",
     "cc_rewards", "credit-cards", "rewards,cards,2026"),
    ("Balance Transfers: When They're Worth It",
     "3% fee vs 18 months at 0% APR — the breakeven calc.",
     "bt", "credit-cards", "balance-transfer"),
    ("How Credit Utilization Affects Your Score",
     "30% is fine. 10% is better. Here's why.",
     "util", "credit-cards", "utilization"),
    ("Travel Cards vs Cash-Back: Which Pays More?",
     "Points-per-dollar math on a $40k household spend.",
     "travel_cb", "credit-cards", "travel,cash-back"),
    ("Annual Fees: When the Math Works",
     "How a $695 card can pay for itself in two trips.",
     "annual_fee", "credit-cards", "annual-fee,premium"),
    ("Credit Card APRs Explained",
     "Purchase APR, cash advance APR, penalty APR — and how they compound.",
     "cc_apr", "credit-cards", "apr,interest"),

    # Insurance (5)
    ("How Much Life Insurance Do You Actually Need?",
     "The DIME method and why most online calculators undershoot.",
     "life_ins", "insurance", "life-insurance,dime"),
    ("Term vs Whole Life Insurance",
     "Why the financial planning community is overwhelmingly on Team Term.",
     "term_whole", "insurance", "term,whole-life"),
    ("Homeowners Insurance: Replacement Cost vs Actual Cash Value",
     "The clause that determines whether you can rebuild after a fire.",
     "rcv_acv", "insurance", "homeowners,rcv,acv"),
    ("Health Insurance Open Enrollment 2026",
     "What's changed on the marketplace this year.",
     "open_enroll", "insurance", "health,enrollment"),
    ("Disability Insurance: The Most Overlooked Policy",
     "Why short-term + long-term combined is the standard recommendation.",
     "disability", "insurance", "disability,insurance"),

    # Estate (5)
    ("Wills vs Living Trusts: Which Do You Need?",
     "Probate, privacy, and the cost trade-off.",
     "wills_trusts", "estate-planning", "wills,trusts,probate"),
    ("Federal Estate Tax: 2026 Exemption Update",
     "The $13.99M individual exemption and what changes after 2025.",
     "estate_tax", "estate-planning", "estate-tax,exemption"),
    ("Beneficiary Designations: The Silent Estate Killer",
     "Why your TOD beat your will, every time.",
     "beneficiary", "estate-planning", "beneficiary,tod,pod"),
    ("Setting Up a 529 College Savings Plan",
     "Tax-advantaged growth and the new 529-to-Roth rollover.",
     "529", "estate-planning", "529,college"),
    ("Power of Attorney: Durable vs Springing",
     "Why most planners now recommend the durable kind.",
     "poa", "estate-planning", "poa,estate"),

    # Financial Advisor (6)
    ("What a Fiduciary Financial Advisor Actually Does",
     "The legal duty, the fee structures, and the screening questions.",
     "fiduciary", "financial-advisor", "fiduciary,advisor"),
    ("How Advisor Fees Work: AUM vs Flat vs Hourly",
     "1% of $1M is $10k a year — is it worth it?",
     "advisor_fees", "financial-advisor", "advisor-fees,aum"),
    ("Robo-Advisor or Human Advisor: A Decision Tree",
     "When the algorithm beats the human, and when it doesn't.",
     "robo_human", "financial-advisor", "robo,human-advisor"),
    ("How to Choose a Financial Advisor",
     "Ten questions to ask before signing the engagement letter.",
     "choose_advisor", "financial-advisor", "advisor,choose"),
    ("The Difference Between a CFP, CFA, and ChFC",
     "Three respected designations — but each signals something different.",
     "designations", "financial-advisor", "cfp,cfa,chfc"),
    ("When to Fire Your Financial Advisor",
     "Five performance and process signals you should not ignore.",
     "fire_advisor", "financial-advisor", "advisor,fire"),
]


# ─── Helper: deterministic article body builder ─────────────────────

_BODY_TEMPLATES = {
    "default": (
        "When it comes to {topic}, the right approach depends on your goals, "
        "tax situation, and time horizon. This guide walks through the core "
        "concepts in plain English.\n\n"
        "## Why It Matters\n\n"
        "Most households who get {topic} right end up with measurably better "
        "outcomes — a larger nest egg, a lower tax bill, or a more comfortable "
        "retirement. Conversely, the cost of getting it wrong compounds.\n\n"
        "## How It Works\n\n"
        "At its core, {topic} comes down to three variables: time, contribution, "
        "and rate of return. Each plays a different role:\n\n"
        "- **Time** is the most powerful lever — and the one you can't buy back.\n"
        "- **Contribution** is the one you control most directly month to month.\n"
        "- **Rate of return** is the one you should worry about least, once your "
        "  asset allocation is set.\n\n"
        "## A Worked Example\n\n"
        "Consider a household earning $90,000 in {state_focus}. With a "
        "{rate}% expected real return, contributing 12% of pay over 30 years, "
        "the math points to a portfolio in the mid-six figures by retirement.\n\n"
        "Use the calculator below to plug in your own numbers — the result is "
        "deterministic and will not change between page loads.\n\n"
        "## What to Watch For\n\n"
        "The single biggest mistake we see is people optimizing the wrong "
        "variable. The size of the gap is almost always determined by your "
        "savings rate, not your asset allocation. Increase the rate by two "
        "percentage points and you'll often outperform a 'better' portfolio.\n\n"
        "## Bottom Line\n\n"
        "Get the basics of {topic} right, automate the contributions, and "
        "review once a year. The compounding does the rest. SmartAsset's "
        "free advisor matching tool can pair you with a vetted fiduciary who "
        "can review your full plan in a free introductory call."
    ),
}


def _body_for(title, related_calc, tags):
    topic = title.lower().rstrip("?").rstrip(".")
    state_focus = "Texas" if "TX" in tags else ("California" if "CA" in tags else "the U.S.")
    rate = "6.5"
    return _BODY_TEMPLATES["default"].format(topic=topic,
                                              state_focus=state_focus,
                                              rate=rate)


def _calc_slug_for(short):
    """Map shorthand → real calc slug if it matches one, else empty."""
    mapping = {
        "401k": "401k", "roth": "ira", "rmd": "retirement",
        "ss": "retirement", "fourpct": "retirement", "savings_by_age": "retirement",
        "mortgage_pay_off": "mortgage", "no_tax_retire": "retirement",
        "457b": "retirement", "catchup": "401k", "ss62": "retirement",
        "rule55": "401k",
        "brackets": "income-tax", "std_ded": "income-tax",
        "cap_gains": "capital-gains", "salt": "income-tax",
        "extension": "income-tax", "se_deductions": "income-tax",
        "state_ranks": "state-tax", "prop_tax_calc": "property-tax",
        "tlh": "capital-gains", "marginal_vs_eff": "income-tax",
        "alloc": "investment", "index_etf": "investment",
        "dca": "investment", "sorr": "retirement",
        "bond_ladder": "investment", "treasuries": "investment",
        "div_investing": "investment", "compound": "savings",
        "robo_vs_human": "investment", "inflation_port": "inflation",
        "afford": "affordability", "pmi": "mortgage",
        "fha_conv": "mortgage", "term_compare": "mortgage",
        "closing": "closing-costs", "refi_2026": "refinance",
        "arm": "mortgage", "down_payment": "affordability",
        "biweekly": "mortgage", "points": "mortgage",
        "hysa_mm": "savings", "cd_tbill": "cd",
        "cd_ladder": "cd", "checking": "savings",
        "emergency": "savings", "fdic": "savings",
        "ira_bank": "ira", "apy_apr": "savings",
        "snowball": "credit-card", "build_credit": "credit-card",
        "fico": "credit-card", "budget": "net-worth",
        "net_worth_guide": "net-worth", "lease_buy": "auto-loan",
        "true_cost": "mortgage", "dp_savings": "savings",
        "cc_rewards": "credit-card", "bt": "credit-card",
        "util": "credit-card", "travel_cb": "credit-card",
        "annual_fee": "credit-card", "cc_apr": "credit-card",
        "life_ins": "net-worth", "term_whole": "net-worth",
        "rcv_acv": "property-tax", "open_enroll": "paycheck",
        "disability": "paycheck",
        "wills_trusts": "net-worth", "estate_tax": "income-tax",
        "beneficiary": "retirement", "529": "savings",
        "poa": "net-worth",
        "fiduciary": "retirement", "advisor_fees": "retirement",
        "robo_human": "investment", "choose_advisor": "retirement",
        "designations": "retirement", "fire_advisor": "retirement",
    }
    return mapping.get(short, "")


# ─── Seed functions ─────────────────────────────────────────────────

def seed_database(db, User, Author, Category, Article, State, Advisor, bcrypt):
    """Seed everything except the per-test benchmark users.

    Gated as a whole — if the State table already has rows, we early-return.
    """
    if State.query.count() > 0:
        return

    # States
    for (name, abbr, kind, top, flat, prop, sales, mh, mi, coli, metro) in STATES:
        slug = name.lower().replace(" ", "-")
        st = State(name=name, abbr=abbr, slug=slug, income_tax_type=kind,
                   state_income_top_rate=top, state_income_flat_rate=flat,
                   property_tax_rate=prop, sales_tax_rate=sales,
                   median_home_price=mh, median_household_income=mi,
                   cost_of_living_index=coli, top_metro=metro,
                   overview=_state_overview(name, metro, kind, top, prop, mh))
        db.session.add(st)

    # Categories
    for (name, slug, blurb) in CATEGORIES:
        db.session.add(Category(name=name, slug=slug, blurb=blurb))

    # Authors
    for (name, slug, title, creds, loc, twitter, bio) in AUTHORS:
        db.session.add(Author(name=name, slug=slug, title=title,
                                credentials=creds, location=loc,
                                twitter=twitter,
                                linkedin=f"https://linkedin.com/in/{slug}",
                                bio=bio))

    db.session.flush()  # gets IDs assigned

    # Articles
    cat_by_slug = {c.slug: c for c in Category.query.all()}
    authors = Author.query.order_by(Author.id).all()
    base = date(2026, 5, 26)
    all_articles = list(ARTICLES_SPEC) + EXTRA_ARTICLES
    for i, (title, dek, short, cat_slug, tags) in enumerate(all_articles):
        cat = cat_by_slug[cat_slug]
        author = authors[i % len(authors)]
        slug = _slugify(title)
        body = _body_for(title, short, tags)
        related_calc = _calc_slug_for(short)
        # Cycle through 85 real Pexels article images
        hero = f"/static/images/articles/article-{(i % 85) + 1:03d}.jpg"
        pub = base - timedelta(days=i * 2)
        a = Article(title=title, slug=slug, dek=dek, body=body,
                     hero_image=hero, category_id=cat.id,
                     author_id=author.id, published_at=pub,
                     reading_minutes=4 + (i % 6),
                     view_count=18000 - (i * 47) % 14000,
                     related_calc=related_calc, tags=tags)
        db.session.add(a)

    # Advisors — 2-3 per state, deterministic
    state_rows = State.query.order_by(State.id).all()
    seq = 0
    for st in state_rows:
        for k in range(3):  # 3 advisors / state = 153 total
            seq += 1
            first, last = ADVISOR_NAMES[seq % len(ADVISOR_NAMES)]
            firm = ADVISOR_FIRMS[seq % len(ADVISOR_FIRMS)]
            spec = SPECIALTIES[seq % len(SPECIALTIES)]
            creds = ["CFP", "CFA", "ChFC", "CPA", "CFP, CPA"][seq % 5]
            name = f"{first} {last}"
            slug = f"{first.lower()}-{last.lower()}-{st.abbr.lower()}-{k+1}"
            years = 8 + (seq * 7) % 25
            aum = 50 + (seq * 23) % 950  # $50M..$1B
            min_assets = [50_000, 100_000, 250_000, 500_000][seq % 4]
            rating = round(4.2 + ((seq * 17) % 80) / 100.0, 2)
            review_count = 12 + (seq * 11) % 250
            city = st.top_metro
            bio = (f"{name} is a {creds} advisor at {firm} serving "
                   f"{city} and the greater {st.name} area. With "
                   f"{years} years of experience advising clients on "
                   f"{spec.lower()} planning, {first} leads a practice "
                   f"managing approximately ${aum}M in client assets.")
            db.session.add(Advisor(name=name, slug=slug, firm=firm,
                                    city=city, state_abbr=st.abbr,
                                    credentials=creds,
                                    years_experience=years,
                                    aum_millions=aum,
                                    min_assets=min_assets,
                                    fee_structure="Fee-only" if seq % 3 else "Fee-based",
                                    specialty=spec, bio=bio,
                                    fiduciary=True,
                                    rating=rating,
                                    review_count=review_count))

    db.session.commit()


def seed_benchmark_users(db, User, bcrypt):
    """4 fixed benchmark personas used by tasks.jsonl. Idempotent."""
    if User.query.filter_by(email="alice.j@test.com").first():
        return
    rows = [
        ("alice.j@test.com", "Alice Johnson", "NY", "10024"),
        ("bob.smith@test.com", "Bob Smith", "TX", "78704"),
        ("carol.lee@test.com", "Carol Lee", "CA", "94110"),
        ("david.kim@test.com", "David Kim", "IL", "60601"),
    ]
    for email, name, state, zip_code in rows:
        db.session.add(User(email=email, name=name, state=state,
                              zip_code=zip_code,
                              password_hash=PINNED_BCRYPT,
                              joined_at=SEED_DATE))
    db.session.commit()


# ─── Helpers ────────────────────────────────────────────────────────

def _slugify(s):
    import re
    s = re.sub(r"[^a-zA-Z0-9\s\-]", "", s or "").strip().lower()
    return re.sub(r"\s+", "-", s) or "x"


def _state_overview(name, metro, kind, top, prop, median_home):
    kind_phrase = {
        "none": "no state income tax",
        "flat": f"a flat {top:.2f}% state income tax",
        "bracket": f"a progressive state income tax topping out at {top:.2f}%",
    }[kind]
    return (
        f"{name} has {kind_phrase} and an average effective property tax "
        f"rate of {prop:.2f}%. The median home price across the state is "
        f"around ${median_home:,}, with the {metro} metro driving much of "
        f"the activity. SmartAsset's state-level calculators apply the "
        f"correct rates automatically when you enter your home or income "
        f"details on any tool below."
    )


# ─── Extras: glossary, cities, reviews, promos ────────────────────

def seed_extras(db, GlossaryTerm, City, Review, Promo):
    """Seed glossary, cities, reviews, promos. Function-level idempotent."""
    # Glossary
    if GlossaryTerm.query.count() == 0:
        for term, short_def, long_def, related_calc, related_cat in GLOSSARY:
            letter = (term[0] if term else "Z").upper()
            if not ("A" <= letter <= "Z"):
                letter = "Z"
            db.session.add(GlossaryTerm(
                term=term, slug=_slugify(term), letter=letter,
                short_def=short_def, long_def=long_def,
                related_calc=related_calc, related_category=related_cat,
            ))
        db.session.commit()

    # Cities
    if City.query.count() == 0:
        for (name, abbr, pop, mh, mr, mi, coli, walk, ptax, overview) in CITIES:
            slug = f"{_slugify(name)}-{abbr.lower()}"
            db.session.add(City(
                name=name, slug=slug, state_abbr=abbr, population=pop,
                median_home_price=mh, median_rent=mr,
                median_household_income=mi, cost_of_living_index=coli,
                walk_score=walk, avg_property_tax_rate=ptax,
                crime_index=round(50 + (pop % 30), 1),
                overview=overview,
            ))
        db.session.commit()

    # Reviews
    if Review.query.count() == 0:
        for (name, kind, overall, fees, mn, pros, cons, body, hq, founded) in REVIEWS:
            slug = f"{_slugify(name)}-review"
            db.session.add(Review(
                name=name, slug=slug, kind=kind, overall_rating=overall,
                fees=fees, minimum=mn, pros=pros, cons=cons,
                body=body, headquarters=hq, founded_year=founded,
            ))
        db.session.commit()

    # Promos
    if Promo.query.count() == 0:
        for code, desc, pct in PROMOS:
            db.session.add(Promo(code=code, description=desc,
                                   discount_pct=pct, active=True))
        db.session.commit()
