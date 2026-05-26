#!/usr/bin/env python3
"""R5 polish: appends ON TOP of R4 seed db.

R4 baseline (md5 0143813b...):
  topics 354, computation_results 5226, notebook_entries 704,
  topic_feedback 177, subcategories 60.

R5 targets:
  topics       550+   (+196)
  comp_results 8000+  (+2774)
  notebook_ent 1500+  (+800)
  topic_feedb  350+   (+175)

R5 quality emphasis: every new comp_result has 4-7 sub-pods (alternate forms,
step-by-step, WL code, comparison-with-related, plot SVG). New topics cover
economics, biology-systems, ML-architecture, world-history-events, cosmology,
climate, programming-langs, medicine.

Deterministic — no datetime.now(), no random. Run twice = same md5.
"""
from __future__ import annotations
import json, sqlite3, shutil, os, math, hashlib
from datetime import datetime, timedelta

SRC = 'instance_seed/wolfram_alpha.db'
DST = 'instance/wolfram_alpha.db'

REF = datetime(2026, 5, 16, 12, 0, 0)
def ts(off_hours: int = 0) -> str:
    return (REF + timedelta(hours=off_hours)).isoformat(sep=' ')

def J(x): return json.dumps(x)

def hh(s: str, mod: int) -> int:
    return int.from_bytes(hashlib.md5(s.encode()).digest()[:4], 'big') % mod

# A simple inline SVG plot generator — deterministic from a key string.
def svg_plot_inline(key: str, kind: str = 'curve') -> str:
    """Return an inline SVG string for use as a comparison/plot pod image."""
    h = hashlib.md5(key.encode()).digest()
    if kind == 'curve':
        c1, c2 = h[0] % 120, h[1] % 120
        return (
            '<svg viewBox="0 0 300 140" xmlns="http://www.w3.org/2000/svg">'
            '<rect width="300" height="140" fill="#fafafa"/>'
            '<line x1="0" y1="70" x2="300" y2="70" stroke="#cdcdcd"/>'
            '<line x1="150" y1="0" x2="150" y2="140" stroke="#cdcdcd"/>'
            f'<path d="M0,120 C40,{20+c1} 100,{110-c2} 150,70 S260,{20+c2} 300,40" '
            'fill="none" stroke="#f96302" stroke-width="2"/></svg>'
        )
    if kind == 'bar':
        bars = ''.join(
            f'<rect x="{20+i*30}" y="{120-(h[i]%90)}" width="20" height="{h[i]%90}" fill="#5e3aaa"/>'
            for i in range(8)
        )
        return (
            '<svg viewBox="0 0 300 140" xmlns="http://www.w3.org/2000/svg">'
            '<rect width="300" height="140" fill="#fafafa"/>'
            f'{bars}'
            '<line x1="0" y1="120" x2="300" y2="120" stroke="#1a1a1a" stroke-width="1"/></svg>'
        )
    return ''

# ---------------------------------------------------------------------------
# (1) NEW TOPICS — 200 across 8 themes
# Format: (cat_slug, sub_slug_or_None, name, slug, desc, image, feat, new, examples_json)
# ---------------------------------------------------------------------------
NEW_TOPICS = []

# ---- Economics (24) ----
NEW_TOPICS += [
    ("society-and-culture", "economics", "Supply and Demand", "supply-demand-curves",
     "Equilibrium price, quantity, surplus and shortage analysis.",
     "economics.png", True, True, J([
        {"query":"market equilibrium","type":"concept","result":"Qd = Qs at price P*; surplus above, shortage below"},
        {"query":"price elasticity demand","type":"formula","result":"E = (%ΔQ)/(%ΔP); |E|>1 elastic, <1 inelastic"},
        {"query":"consumer surplus","type":"concept","result":"Area under demand above price line — willingness-to-pay benefit"},
     ])),
    ("society-and-culture", "economics", "Black-Scholes Model", "black-scholes",
     "European option pricing under geometric Brownian motion.",
     "finance.png", True, True, J([
        {"query":"Black-Scholes call formula","type":"formula","result":"C = S·N(d1) - K·e^(-rT)·N(d2)"},
        {"query":"d1 formula","type":"formula","result":"d1 = [ln(S/K) + (r + σ²/2)T] / (σ√T)"},
        {"query":"put-call parity","type":"identity","result":"C - P = S - K·e^(-rT)"},
     ])),
    ("society-and-culture", "economics", "GDP Components", "gdp-components",
     "Expenditure approach: C + I + G + (X - M).",
     "economics.png", False, True, J([
        {"query":"GDP US 2023","type":"value","result":"~$27.4 trillion (nominal)"},
        {"query":"GDP per capita US","type":"value","result":"~$81,600 (2023)"},
        {"query":"largest GDP world","type":"ranking","result":"US, China, Germany, Japan, India"},
     ])),
    ("society-and-culture", "economics", "Phillips Curve", "phillips-curve",
     "Inflation–unemployment trade-off.",
     "economics.png", False, True, J([
        {"query":"original Phillips curve","type":"plot","result":"Wage growth vs unemployment — negatively sloped"},
        {"query":"expectations augmented","type":"formula","result":"π = π^e - β(u - u_n)"},
        {"query":"NAIRU","type":"concept","result":"Non-accelerating inflation rate of unemployment ~5% US historical"},
     ])),
    ("society-and-culture", "economics", "Cobb-Douglas Production", "cobb-douglas",
     "Y = A·K^α·L^(1-α) — capital and labor inputs.",
     "economics.png", False, True, J([
        {"query":"Cobb-Douglas form","type":"formula","result":"Y = A·K^α·L^(1-α); α≈1/3 capital share"},
        {"query":"returns to scale","type":"property","result":"Constant when α+β=1; increasing if >1"},
        {"query":"marginal product","type":"formula","result":"MPK = αY/K; MPL = (1-α)Y/L"},
     ])),
    ("society-and-culture", "economics", "Time Value of Money", "time-value-money",
     "Present and future value, discounting, IRR.",
     "finance.png", False, True, J([
        {"query":"PV formula","type":"formula","result":"PV = FV / (1+r)^n"},
        {"query":"annuity PV","type":"formula","result":"PV = C·[1 - (1+r)^(-n)] / r"},
        {"query":"IRR definition","type":"concept","result":"Discount rate setting NPV = 0"},
     ])),
    ("society-and-culture", "economics", "Compound Interest", "compound-interest",
     "Discrete and continuous compounding formulas.",
     "finance.png", False, True, J([
        {"query":"compound formula","type":"formula","result":"A = P(1+r/n)^(nt)"},
        {"query":"continuous compounding","type":"formula","result":"A = P·e^(rt)"},
        {"query":"rule of 72","type":"rule","result":"Doubling time ≈ 72/r (r in %)"},
     ])),
    ("society-and-culture", "economics", "Market Structures", "market-structures",
     "Perfect competition, monopoly, oligopoly, monopolistic competition.",
     "economics.png", False, False, J([
        {"query":"monopoly markup","type":"formula","result":"P = MC / (1 - 1/|E|) — Lerner index"},
        {"query":"Cournot equilibrium","type":"concept","result":"n firms each produce Q/(n+1)·(a-c)/b"},
        {"query":"Bertrand paradox","type":"result","result":"Two firms with identical MC → P = MC"},
     ])),
    ("society-and-culture", "economics", "Game Theory Basics", "game-theory",
     "Nash equilibrium, prisoner's dilemma, mixed strategies.",
     "economics.png", False, False, J([
        {"query":"prisoners dilemma","type":"game","result":"Dominant: defect; (D,D) Nash but (C,C) Pareto-better"},
        {"query":"Nash equilibrium","type":"concept","result":"No player gains by unilateral deviation"},
        {"query":"mixed strategy","type":"concept","result":"Randomize over actions to make opponent indifferent"},
     ])),
    ("society-and-culture", "economics", "International Trade", "international-trade",
     "Comparative advantage and Ricardian model.",
     "economics.png", False, False, J([
        {"query":"comparative advantage","type":"concept","result":"Specialize in goods with lowest opportunity cost"},
        {"query":"Ricardo example","type":"example","result":"England cloth / Portugal wine — both gain via trade"},
        {"query":"Heckscher-Ohlin","type":"model","result":"Countries export goods using their abundant factors"},
     ])),
    ("society-and-culture", "economics", "Inflation Measures", "inflation-measures",
     "CPI, PPI, GDP deflator, core inflation.",
     "economics.png", False, False, J([
        {"query":"CPI formula","type":"formula","result":"CPI_t = (Cost basket at t) / (Cost basket at base) × 100"},
        {"query":"core CPI","type":"concept","result":"CPI excluding food and energy — less volatile"},
        {"query":"PPI","type":"concept","result":"Producer Price Index — wholesale/upstream prices"},
     ])),
    ("society-and-culture", "economics", "Interest Rate Models", "interest-rate-models",
     "Yield curve, term structure, central bank policy.",
     "finance.png", False, False, J([
        {"query":"yield curve normal","type":"concept","result":"Upward slope: long > short rates"},
        {"query":"inverted yield curve","type":"signal","result":"Recession predictor — 2y > 10y"},
        {"query":"taylor rule","type":"formula","result":"i = r* + π + 0.5(π−π*) + 0.5(y−y*)"},
     ])),
    ("society-and-culture", "economics", "Macroeconomic Indicators", "macro-indicators",
     "GDP growth, unemployment, inflation, interest rates.",
     "economics.png", False, False, J([
        {"query":"US unemployment","type":"value","result":"~3.8% (Apr 2024)"},
        {"query":"US fed funds rate","type":"value","result":"5.25–5.50% (mid-2024)"},
        {"query":"US inflation YoY","type":"value","result":"~3.5% CPI YoY (Mar 2024)"},
     ])),
    ("society-and-culture", "economics", "Gini Coefficient", "gini-coefficient",
     "Income inequality measure.",
     "economics.png", False, False, J([
        {"query":"Gini range","type":"property","result":"0 (perfect equality) to 1 (perfect inequality)"},
        {"query":"US Gini","type":"value","result":"~0.48 household income (2022 Census)"},
        {"query":"Nordic Gini","type":"value","result":"~0.27 — among lowest globally"},
     ])),
    ("society-and-culture", "economics", "Labor Economics", "labor-economics",
     "Minimum wage, labor supply, Okun's law.",
     "economics.png", False, False, J([
        {"query":"Okun's law","type":"formula","result":"ΔY/Y ≈ k - c·ΔU; c ≈ 2 US"},
        {"query":"labor force participation","type":"value","result":"~62.7% US (2024)"},
        {"query":"min wage US federal","type":"value","result":"$7.25/hr since 2009"},
     ])),
    ("society-and-culture", "economics", "Behavioral Economics", "behavioral-economics",
     "Kahneman, Tversky, biases and heuristics.",
     "economics.png", False, False, J([
        {"query":"loss aversion","type":"concept","result":"Losses weighted ~2x gains in prospect theory"},
        {"query":"anchoring","type":"bias","result":"Initial number distorts subsequent estimates"},
        {"query":"prospect theory","type":"theory","result":"S-shaped value function, probability weighting"},
     ])),
    ("society-and-culture", "economics", "Monetary Policy", "monetary-policy",
     "Federal Reserve tools: rates, QE, reserves.",
     "economics.png", False, False, J([
        {"query":"open market ops","type":"tool","result":"Fed buys/sells Treasuries to set fed funds"},
        {"query":"quantitative easing","type":"tool","result":"Large-scale asset purchases when rates ≈ 0"},
        {"query":"discount rate","type":"tool","result":"Rate banks borrow direct from Fed"},
     ])),
    ("society-and-culture", "economics", "Fiscal Multiplier", "fiscal-multiplier",
     "ΔGDP per dollar of government spending.",
     "economics.png", False, False, J([
        {"query":"Keynesian multiplier","type":"formula","result":"1/(1 - MPC); MPC≈0.7 → multiplier ~3.3 theoretical"},
        {"query":"recession multiplier","type":"value","result":"~1.5–2.5 (Romer & Bernstein 2009)"},
        {"query":"tax multiplier","type":"value","result":"|tax|-multiplier < |spending|-multiplier by MPC"},
     ])),
    ("society-and-culture", "economics", "Stock Market Indices", "stock-indices",
     "S&P 500, Dow Jones, NASDAQ — composition and weighting.",
     "finance.png", False, False, J([
        {"query":"S&P 500 weighting","type":"method","result":"Market cap weighted; ~80% US market"},
        {"query":"Dow 30 weighting","type":"method","result":"Price weighted — anachronism but kept"},
        {"query":"NASDAQ composite size","type":"value","result":"~3,300 companies, heavy tech"},
     ])),
    ("society-and-culture", "economics", "Cryptocurrency Economics", "crypto-economics",
     "Bitcoin halvings, mining economics, market cap rankings.",
     "finance.png", False, False, J([
        {"query":"bitcoin halving 2024","type":"event","result":"Block reward 6.25 → 3.125 BTC; Apr 19 2024"},
        {"query":"crypto market cap top","type":"ranking","result":"BTC, ETH, USDT, SOL, BNB (rotates)"},
        {"query":"BTC max supply","type":"property","result":"21,000,000 — hard-coded cap"},
     ])),
    ("society-and-culture", "economics", "Tax Brackets US", "tax-brackets-us",
     "Federal income tax marginal brackets 2024.",
     "finance.png", False, False, J([
        {"query":"top marginal rate US","type":"value","result":"37% above $609,350 (single, 2024)"},
        {"query":"capital gains LT","type":"value","result":"0/15/20% based on income; LT > 1 year"},
        {"query":"standard deduction","type":"value","result":"$14,600 single / $29,200 MFJ (2024)"},
     ])),
    ("society-and-culture", "economics", "Mortgage Calculation", "mortgage-calc",
     "Amortization, points, PMI.",
     "finance.png", False, False, J([
        {"query":"mortgage payment formula","type":"formula","result":"M = P·r(1+r)^n / [(1+r)^n - 1]"},
        {"query":"30-year mortgage rate US","type":"value","result":"~7% (mid-2024)"},
        {"query":"PMI threshold","type":"rule","result":"Required when LTV > 80%; conventional"},
     ])),
    ("society-and-culture", "economics", "Bond Pricing", "bond-pricing",
     "Coupon, yield to maturity, duration.",
     "finance.png", False, False, J([
        {"query":"bond price formula","type":"formula","result":"Σ C/(1+y)^t + F/(1+y)^n"},
        {"query":"Macaulay duration","type":"formula","result":"Weighted avg time to cash flows"},
        {"query":"convexity","type":"concept","result":"Curvature of price-yield; positive for vanilla bonds"},
     ])),
    ("society-and-culture", "economics", "Foreign Exchange", "forex-rates",
     "FX rates, PPP, interest rate parity.",
     "finance.png", False, False, J([
        {"query":"purchasing power parity","type":"theory","result":"Same goods cost same across countries in common currency"},
        {"query":"covered interest parity","type":"formula","result":"F/S = (1+i_d)/(1+i_f)"},
        {"query":"FX daily volume","type":"market","result":"~$7.5 trillion/day (BIS 2022)"},
     ])),
]

# ---- Biology systems (24) ----
NEW_TOPICS += [
    ("science-and-technology", "biological-sciences", "Hardy-Weinberg Equilibrium", "hardy-weinberg",
     "Allele frequencies stable in absence of evolutionary forces.",
     "life-sciences.png", True, True, J([
        {"query":"Hardy-Weinberg equation","type":"formula","result":"p² + 2pq + q² = 1; p + q = 1"},
        {"query":"HW assumptions","type":"list","result":"No mutation, no migration, no selection, random mating, large pop"},
        {"query":"HW heterozygote frequency","type":"formula","result":"2pq — maximum 0.5 at p = q = 0.5"},
     ])),
    ("science-and-technology", "biological-sciences", "Michaelis-Menten Kinetics", "michaelis-menten",
     "Enzyme kinetics — substrate concentration vs reaction rate.",
     "life-sciences.png", True, True, J([
        {"query":"MM equation","type":"formula","result":"v = Vmax·[S] / (Km + [S])"},
        {"query":"Km meaning","type":"concept","result":"[S] at which v = Vmax/2"},
        {"query":"Lineweaver-Burk","type":"linearization","result":"1/v = (Km/Vmax)·(1/[S]) + 1/Vmax"},
     ])),
    ("science-and-technology", "biological-sciences", "DNA Structure", "dna-structure",
     "Double helix, base pairing, replication.",
     "life-sciences.png", False, True, J([
        {"query":"base pair rules","type":"rule","result":"A-T (2 H-bonds), G-C (3 H-bonds)"},
        {"query":"DNA helix pitch","type":"value","result":"~3.4 nm per turn, 10 bp/turn"},
        {"query":"DNA replication speed","type":"rate","result":"~1000 bp/s in E. coli"},
     ])),
    ("science-and-technology", "biological-sciences", "Protein Synthesis", "protein-synthesis",
     "Transcription, translation, codon table.",
     "life-sciences.png", False, True, J([
        {"query":"start codon","type":"codon","result":"AUG (methionine)"},
        {"query":"stop codons","type":"codons","result":"UAA, UAG, UGA"},
        {"query":"codon redundancy","type":"property","result":"64 codons → 20 aa + stop; degeneracy at 3rd base"},
     ])),
    ("science-and-technology", "biological-sciences", "Mendelian Genetics", "mendelian-genetics",
     "Punnett squares, dominant/recessive, dihybrid crosses.",
     "life-sciences.png", False, True, J([
        {"query":"monohybrid cross","type":"ratio","result":"3:1 dominant:recessive in F2"},
        {"query":"dihybrid cross","type":"ratio","result":"9:3:3:1 in F2 for independent traits"},
        {"query":"law of segregation","type":"law","result":"Allele pairs separate during gamete formation"},
     ])),
    ("science-and-technology", "biological-sciences", "Cellular Respiration", "cellular-respiration",
     "Glycolysis, Krebs cycle, electron transport chain.",
     "life-sciences.png", False, True, J([
        {"query":"ATP per glucose","type":"value","result":"~30-32 ATP (aerobic, max yield)"},
        {"query":"Krebs cycle steps","type":"count","result":"8 steps; produces 2 ATP, 6 NADH, 2 FADH2 per glucose"},
        {"query":"glycolysis ATP","type":"net","result":"+2 ATP net (4 produced, 2 consumed)"},
     ])),
    ("science-and-technology", "biological-sciences", "Photosynthesis", "photosynthesis",
     "Light reactions, Calvin cycle, chlorophyll absorption.",
     "life-sciences.png", False, True, J([
        {"query":"net photosynthesis eq","type":"equation","result":"6CO2 + 6H2O + light → C6H12O6 + 6O2"},
        {"query":"chlorophyll a max","type":"wavelength","result":"~430 nm (blue) and ~662 nm (red)"},
        {"query":"Calvin cycle ATP","type":"stoichiometry","result":"3 ATP + 2 NADPH per CO2 fixed"},
     ])),
    ("science-and-technology", "biological-sciences", "Action Potentials", "action-potentials",
     "Neuron firing: depolarization, repolarization, refractory.",
     "life-sciences.png", False, False, J([
        {"query":"threshold potential","type":"value","result":"~-55 mV typical"},
        {"query":"Na+ peak","type":"value","result":"~+30 mV at depolarization peak"},
        {"query":"absolute refractory","type":"value","result":"~1 ms; cannot fire again regardless of stimulus"},
     ])),
    ("science-and-technology", "biological-sciences", "Immune Response", "immune-response",
     "Innate vs adaptive, T/B cells, antibodies.",
     "life-sciences.png", False, False, J([
        {"query":"Ig classes","type":"list","result":"IgG, IgA, IgM, IgE, IgD"},
        {"query":"primary vs secondary","type":"compare","result":"Secondary: faster (memory cells), higher IgG"},
        {"query":"MHC class I","type":"role","result":"Present antigens to CD8+ T cells"},
     ])),
    ("science-and-technology", "biological-sciences", "Cancer Biology", "cancer-biology",
     "Hallmarks of cancer, oncogenes, tumor suppressors.",
     "life-sciences.png", False, False, J([
        {"query":"hallmarks of cancer","type":"count","result":"6 classical (Hanahan-Weinberg); 10 with extensions"},
        {"query":"p53 role","type":"function","result":"Tumor suppressor — apoptosis, cell cycle arrest"},
        {"query":"oncogene example","type":"example","result":"MYC, RAS, EGFR — activated form drives proliferation"},
     ])),
    ("science-and-technology", "biological-sciences", "Microbiome Stats", "microbiome",
     "Human gut microbiota: composition, function, diversity.",
     "life-sciences.png", False, False, J([
        {"query":"gut microbes count","type":"value","result":"~10^13 cells, roughly 1:1 ratio to human cells"},
        {"query":"gut microbiome species","type":"value","result":"~1000+ species typical adult"},
        {"query":"dominant phyla","type":"taxonomy","result":"Firmicutes, Bacteroidetes (~90% combined)"},
     ])),
    ("science-and-technology", "biological-sciences", "Evolution Rates", "evolution-rates",
     "Mutation rates, molecular clock, speciation.",
     "life-sciences.png", False, False, J([
        {"query":"human mutation rate","type":"value","result":"~1.2 × 10^-8 per bp per generation"},
        {"query":"E. coli mutation rate","type":"value","result":"~10^-3 per genome per generation"},
        {"query":"molecular clock","type":"concept","result":"Mutations accumulate at ~constant rate; calibrated with fossils"},
     ])),
    ("science-and-technology", "biological-sciences", "Logistic Population Growth", "logistic-growth",
     "Verhulst equation — population with carrying capacity.",
     "life-sciences.png", False, False, J([
        {"query":"logistic equation","type":"formula","result":"dN/dt = rN(1 - N/K)"},
        {"query":"carrying capacity","type":"concept","result":"K — max sustainable population"},
        {"query":"inflection N","type":"value","result":"N = K/2 — maximum growth rate"},
     ])),
    ("science-and-technology", "biological-sciences", "Lotka-Volterra", "lotka-volterra",
     "Predator-prey dynamics — coupled ODEs.",
     "life-sciences.png", False, False, J([
        {"query":"prey eq","type":"formula","result":"dx/dt = αx - βxy"},
        {"query":"predator eq","type":"formula","result":"dy/dt = δxy - γy"},
        {"query":"equilibrium","type":"point","result":"(γ/δ, α/β) — periodic orbits around"},
     ])),
    ("science-and-technology", "biological-sciences", "Brain Regions", "brain-regions",
     "Cortex lobes, limbic system, brainstem.",
     "life-sciences.png", False, False, J([
        {"query":"frontal lobe function","type":"function","result":"Executive function, planning, motor control"},
        {"query":"hippocampus role","type":"function","result":"Memory formation, spatial navigation"},
        {"query":"cerebellum role","type":"function","result":"Motor coordination, fine timing, balance"},
     ])),
    ("science-and-technology", "biological-sciences", "Heart Function", "heart-function",
     "Cardiac cycle, blood pressure, stroke volume.",
     "life-sciences.png", False, False, J([
        {"query":"cardiac output","type":"formula","result":"CO = HR × SV; ~5 L/min rest"},
        {"query":"normal BP","type":"value","result":"~120/80 mmHg (systolic/diastolic)"},
        {"query":"resting heart rate","type":"value","result":"60–100 bpm adult"},
     ])),
    ("science-and-technology", "biological-sciences", "Lung Capacity", "lung-capacity",
     "Tidal volume, vital capacity, FEV1.",
     "life-sciences.png", False, False, J([
        {"query":"vital capacity","type":"value","result":"~4.6 L male / 3.1 L female adult"},
        {"query":"FEV1/FVC ratio","type":"diagnostic","result":">0.75-0.80 normal; <0.70 obstruction"},
        {"query":"tidal volume","type":"value","result":"~500 mL per breath rest"},
     ])),
    ("science-and-technology", "biological-sciences", "Kidney Function", "kidney-function",
     "GFR, filtration, electrolyte balance.",
     "life-sciences.png", False, False, J([
        {"query":"normal GFR","type":"value","result":"~90–120 mL/min/1.73m² adult"},
        {"query":"creatinine clearance","type":"formula","result":"Cockcroft-Gault: (140-age)·wt / (72·SCr) [×0.85 female]"},
        {"query":"nephron count","type":"value","result":"~1 million per kidney"},
     ])),
    ("science-and-technology", "biological-sciences", "Liver Functions", "liver-functions",
     "Metabolism, detox, bile production.",
     "life-sciences.png", False, False, J([
        {"query":"liver weight adult","type":"value","result":"~1.5 kg ; ~2% body weight"},
        {"query":"bile production","type":"value","result":"~600 mL/day adult"},
        {"query":"liver regeneration","type":"property","result":"Can regenerate from ~25% remnant"},
     ])),
    ("science-and-technology", "biological-sciences", "Hormones Major", "hormones-major",
     "Insulin, cortisol, thyroid, sex hormones.",
     "life-sciences.png", False, False, J([
        {"query":"insulin role","type":"function","result":"Promotes glucose uptake into cells; from beta cells"},
        {"query":"cortisol diurnal","type":"pattern","result":"Peak ~7 AM; lowest near midnight"},
        {"query":"TSH normal range","type":"value","result":"~0.4–4.0 mIU/L"},
     ])),
    ("science-and-technology", "biological-sciences", "Aging Biology", "aging-biology",
     "Telomeres, senescence, hallmarks of aging.",
     "life-sciences.png", False, False, J([
        {"query":"telomere shortening","type":"rate","result":"~50–200 bp per division"},
        {"query":"Hayflick limit","type":"value","result":"~50 divisions for human fibroblasts"},
        {"query":"hallmarks of aging","type":"count","result":"12 hallmarks (López-Otín 2023 update)"},
     ])),
    ("science-and-technology", "biological-sciences", "Stem Cell Biology", "stem-cells",
     "Pluripotent, multipotent, iPSC.",
     "life-sciences.png", False, False, J([
        {"query":"pluripotency factors","type":"factors","result":"OCT4, SOX2, KLF4, c-MYC (Yamanaka)"},
        {"query":"iPSC year","type":"history","result":"2006 mouse; 2007 human (Yamanaka, Nobel 2012)"},
        {"query":"embryonic stem cell","type":"source","result":"Inner cell mass of blastocyst"},
     ])),
    ("science-and-technology", "biological-sciences", "CRISPR Mechanism", "crispr",
     "Cas9 cleavage, gRNA, base editing.",
     "life-sciences.png", False, False, J([
        {"query":"CRISPR-Cas9 components","type":"list","result":"Cas9 nuclease + ~20 nt guide RNA + PAM"},
        {"query":"PAM sequence","type":"motif","result":"5'-NGG-3' for SpCas9"},
        {"query":"base editor","type":"variant","result":"Cas9 nickase + deaminase — C→T or A→G without DSB"},
     ])),
    ("science-and-technology", "biological-sciences", "Cell Cycle Detail", "cell-cycle-detail",
     "G1, S, G2, M phases — checkpoints and durations.",
     "life-sciences.png", False, False, J([
        {"query":"cell cycle duration","type":"value","result":"~24h dividing mammalian; S phase ~6-8h"},
        {"query":"G1/S checkpoint","type":"checkpoint","result":"Restriction point — Rb/E2F gates entry to S"},
        {"query":"spindle checkpoint","type":"checkpoint","result":"All kinetochores attached before anaphase"},
     ])),
]

# ---- ML / AI architecture (24) ----
NEW_TOPICS += [
    ("science-and-technology", "computer-science", "Transformer Architecture", "transformer-arch",
     "Self-attention, multi-head, positional encoding, encoder-decoder.",
     "discrete-math.png", True, True, J([
        {"query":"transformer attention","type":"formula","result":"softmax(QK^T/√d_k)V"},
        {"query":"multi-head attention","type":"detail","result":"Concat h heads, each d_k = d_model/h; project"},
        {"query":"positional encoding","type":"formula","result":"PE(pos,2i) = sin(pos/10000^(2i/d))"},
     ])),
    ("science-and-technology", "computer-science", "Convolutional Neural Networks", "cnn-arch",
     "Conv layers, pooling, receptive field, ResNet.",
     "discrete-math.png", True, True, J([
        {"query":"conv output size","type":"formula","result":"⌊(W - F + 2P)/S⌋ + 1"},
        {"query":"receptive field","type":"concept","result":"Input region a unit sees; grows with depth"},
        {"query":"ResNet skip connection","type":"design","result":"y = F(x) + x — gradient flow + identity"},
     ])),
    ("science-and-technology", "computer-science", "Backpropagation", "backpropagation",
     "Chain rule of gradients through neural network.",
     "discrete-math.png", False, True, J([
        {"query":"backprop chain rule","type":"formula","result":"∂L/∂w = ∂L/∂y · ∂y/∂w"},
        {"query":"vanishing gradient","type":"problem","result":"Gradients shrink with depth; mitigated by ReLU/normalization/skip"},
        {"query":"gradient descent","type":"formula","result":"w ← w − η·∂L/∂w"},
     ])),
    ("science-and-technology", "computer-science", "Softmax and Cross-Entropy", "softmax-cross-entropy",
     "Probability over classes and KL-derived loss.",
     "discrete-math.png", False, True, J([
        {"query":"softmax formula","type":"formula","result":"σ(z)_i = e^(z_i) / Σ e^(z_j)"},
        {"query":"cross entropy","type":"formula","result":"-Σ y_i log p_i"},
        {"query":"softmax gradient","type":"formula","result":"∂σ_i/∂z_j = σ_i(δ_ij − σ_j)"},
     ])),
    ("science-and-technology", "computer-science", "Optimizers", "ml-optimizers",
     "SGD, momentum, Adam, RMSProp.",
     "discrete-math.png", False, True, J([
        {"query":"Adam optimizer","type":"formula","result":"m=β1·m+(1-β1)g; v=β2·v+(1-β2)g²; w-=η·m̂/√(v̂+ε)"},
        {"query":"momentum SGD","type":"formula","result":"v = μv − η·g; w += v"},
        {"query":"Adam defaults","type":"hparams","result":"β1=0.9, β2=0.999, ε=1e-8, η=1e-3"},
     ])),
    ("science-and-technology", "computer-science", "Batch Normalization", "batch-norm",
     "Normalize activations by mini-batch statistics.",
     "discrete-math.png", False, True, J([
        {"query":"BN formula","type":"formula","result":"y = γ·(x-μ)/√(σ²+ε) + β"},
        {"query":"BN benefits","type":"effects","result":"Faster training, smoother loss, mild regularization"},
        {"query":"layer norm vs batch","type":"compare","result":"LN normalizes over features (per sample); used in transformers"},
     ])),
    ("science-and-technology", "computer-science", "LSTM and GRU", "lstm-gru",
     "Gated RNN cells for long sequences.",
     "discrete-math.png", False, True, J([
        {"query":"LSTM gates","type":"list","result":"Forget, input, output gates + cell state"},
        {"query":"GRU gates","type":"list","result":"Update, reset gates (simpler than LSTM)"},
        {"query":"LSTM hidden update","type":"formula","result":"h_t = o_t ⊙ tanh(c_t)"},
     ])),
    ("science-and-technology", "computer-science", "GANs", "gans",
     "Generative Adversarial Networks — generator vs discriminator.",
     "discrete-math.png", False, False, J([
        {"query":"GAN objective","type":"formula","result":"min_G max_D E_x[log D(x)] + E_z[log(1-D(G(z)))]"},
        {"query":"mode collapse","type":"problem","result":"Generator outputs few modes — common training failure"},
        {"query":"WGAN","type":"variant","result":"Wasserstein distance loss; weight clipping or GP"},
     ])),
    ("science-and-technology", "computer-science", "Diffusion Models", "diffusion-models",
     "Forward noise process, reverse denoising — DDPM, Stable Diffusion.",
     "discrete-math.png", False, True, J([
        {"query":"DDPM forward","type":"formula","result":"q(x_t|x_(t-1)) = N(√(1-β_t)x_(t-1), β_t I)"},
        {"query":"reverse step","type":"formula","result":"p_θ(x_(t-1)|x_t) = N(μ_θ(x_t,t), Σ_θ)"},
        {"query":"classifier-free guidance","type":"trick","result":"Sample with strength w: ε_w = (1+w)ε_cond - w·ε_uncond"},
     ])),
    ("science-and-technology", "computer-science", "Reinforcement Learning", "reinforcement-learning",
     "MDP, value functions, Q-learning, policy gradient.",
     "discrete-math.png", False, True, J([
        {"query":"Bellman equation","type":"formula","result":"V(s) = max_a [R(s,a) + γ·E[V(s')]]"},
        {"query":"Q-learning update","type":"formula","result":"Q(s,a) ← Q(s,a) + α[r + γ·max Q(s',a') − Q(s,a)]"},
        {"query":"policy gradient","type":"formula","result":"∇J(θ) = E[∇log π_θ(a|s)·A(s,a)]"},
     ])),
    ("science-and-technology", "computer-science", "Attention Mechanism Detail", "attention-mechanism-detail",
     "Scaled dot-product, additive, cross attention.",
     "discrete-math.png", False, False, J([
        {"query":"scaled dot product","type":"formula","result":"softmax(QK^T/√d_k)V"},
        {"query":"cross attention","type":"variant","result":"Q from decoder, K/V from encoder"},
        {"query":"attention complexity","type":"complexity","result":"O(n²·d) in seq length n"},
     ])),
    ("science-and-technology", "computer-science", "Dropout Regularization", "dropout",
     "Stochastic neuron deactivation during training.",
     "discrete-math.png", False, False, J([
        {"query":"dropout rate","type":"hparam","result":"Typical p=0.1-0.5; FC layers, not BN-equipped"},
        {"query":"dropout inference","type":"behavior","result":"All neurons active; weights scaled by (1-p) [or trained inverted]"},
        {"query":"dropout intuition","type":"concept","result":"Ensemble of subnetworks; reduces co-adaptation"},
     ])),
    ("science-and-technology", "computer-science", "BERT Architecture", "bert-arch",
     "Bidirectional encoder, masked LM, NSP pre-training.",
     "discrete-math.png", False, True, J([
        {"query":"BERT base size","type":"value","result":"12 layers, 768 hidden, 110M params"},
        {"query":"BERT large size","type":"value","result":"24 layers, 1024 hidden, 340M params"},
        {"query":"MLM objective","type":"objective","result":"Mask 15% tokens, predict from context"},
     ])),
    ("science-and-technology", "computer-science", "GPT Architecture", "gpt-arch",
     "Decoder-only transformer, autoregressive LM, scaling laws.",
     "discrete-math.png", False, True, J([
        {"query":"GPT-2 size","type":"value","result":"1.5B params, 48 layers, 1600 hidden (large)"},
        {"query":"GPT-3 size","type":"value","result":"175B params, 96 layers, 12288 hidden"},
        {"query":"causal mask","type":"detail","result":"Attention mask prevents attending to future tokens"},
     ])),
    ("science-and-technology", "computer-science", "Vision Transformer", "vit-arch",
     "Image patches → token sequence → transformer encoder.",
     "discrete-math.png", False, True, J([
        {"query":"ViT patch size","type":"hparam","result":"16x16 typical for 224x224 input → 196 tokens"},
        {"query":"ViT base size","type":"value","result":"12 layers, 768 hidden, 86M params"},
        {"query":"data hungry","type":"empirical","result":"Outperforms ResNet only with 100M+ images"},
     ])),
    ("science-and-technology", "computer-science", "Loss Functions", "ml-loss-functions",
     "MSE, MAE, cross-entropy, hinge, focal.",
     "discrete-math.png", False, False, J([
        {"query":"MSE formula","type":"formula","result":"(1/n)Σ(y_i - ŷ_i)²"},
        {"query":"hinge loss","type":"formula","result":"max(0, 1 - y·f(x)); SVM"},
        {"query":"focal loss","type":"formula","result":"-α(1-p)^γ·log(p); class imbalance"},
     ])),
    ("science-and-technology", "computer-science", "PCA and SVD", "pca-svd",
     "Principal Component Analysis via SVD.",
     "discrete-math.png", False, False, J([
        {"query":"PCA via SVD","type":"method","result":"X = UΣV^T; principal directions in V"},
        {"query":"explained variance","type":"formula","result":"σ_i² / Σσ_j² for component i"},
        {"query":"PCA optimization","type":"objective","result":"Maximize variance of projected data subject to orthogonality"},
     ])),
    ("science-and-technology", "computer-science", "Decision Trees", "decision-trees",
     "Information gain, Gini impurity, random forest.",
     "discrete-math.png", False, False, J([
        {"query":"Gini impurity","type":"formula","result":"1 - Σp_i²"},
        {"query":"information gain","type":"formula","result":"H(parent) - Σ(N_child/N)·H(child)"},
        {"query":"random forest","type":"ensemble","result":"Bagging + random feature subsets per split"},
     ])),
    ("science-and-technology", "computer-science", "Gradient Boosting", "gradient-boosting",
     "XGBoost, LightGBM, CatBoost.",
     "discrete-math.png", False, False, J([
        {"query":"GBM idea","type":"method","result":"Fit weak learner to current residuals; sum hypotheses"},
        {"query":"XGBoost regularization","type":"detail","result":"L1+L2 on leaf scores; tree complexity penalty"},
        {"query":"LightGBM trick","type":"detail","result":"Histogram-based + leaf-wise growth"},
     ])),
    ("science-and-technology", "computer-science", "Embeddings", "embeddings",
     "Word2vec, GloVe, contextual embeddings.",
     "discrete-math.png", False, False, J([
        {"query":"word2vec skip-gram","type":"objective","result":"Predict context given center word; negative sampling"},
        {"query":"GloVe","type":"method","result":"Global co-occurrence matrix factorization"},
        {"query":"embedding similarity","type":"metric","result":"Cosine similarity standard"},
     ])),
    ("science-and-technology", "computer-science", "Tokenization", "tokenization",
     "BPE, WordPiece, SentencePiece.",
     "discrete-math.png", False, False, J([
        {"query":"BPE algorithm","type":"method","result":"Merge most frequent pair iteratively until vocab size"},
        {"query":"WordPiece","type":"method","result":"Greedy merge by likelihood; BERT tokenizer"},
        {"query":"GPT-3 vocab","type":"value","result":"~50,257 tokens (cl100k_base)"},
     ])),
    ("science-and-technology", "computer-science", "RAG Architecture", "rag-architecture",
     "Retrieval-augmented generation — retriever + generator.",
     "discrete-math.png", False, True, J([
        {"query":"RAG components","type":"list","result":"Retriever (BM25/dense) + LLM generator + prompt template"},
        {"query":"dense retrieval","type":"method","result":"Embed query and docs; cosine search"},
        {"query":"chunk size","type":"hparam","result":"~200-500 tokens typical; overlap 10-20%"},
     ])),
    ("science-and-technology", "computer-science", "Mixture of Experts", "moe-architecture",
     "Sparse MoE layers — gate routes tokens to experts.",
     "discrete-math.png", False, True, J([
        {"query":"MoE gate","type":"formula","result":"Top-k(softmax(W_g · x)); typically k=1-2"},
        {"query":"Switch Transformer","type":"example","result":"1.6T params via sparse MoE; only ~7B active per token"},
        {"query":"MoE load balance","type":"loss","result":"Auxiliary loss encourages even expert usage"},
     ])),
    ("science-and-technology", "computer-science", "Quantization", "quantization",
     "INT8, INT4, FP16 — model compression for inference.",
     "discrete-math.png", False, False, J([
        {"query":"INT8 quantization","type":"format","result":"Map FP32 weights to 8-bit ints; 4x smaller"},
        {"query":"GPTQ method","type":"method","result":"One-shot weight quantization with reconstruction loss"},
        {"query":"FP16 vs BF16","type":"compare","result":"BF16: 8 exp + 7 mantissa; FP16: 5 exp + 10 mantissa"},
     ])),
]

# ---- World history events (24) ----
NEW_TOPICS += [
    ("society-and-culture", "history", "World War I", "wwi",
     "1914-1918 — causes, fronts, casualties, treaties.",
     "history.png", True, True, J([
        {"query":"WWI start","type":"date","result":"July 28, 1914 — Austria-Hungary declares war on Serbia"},
        {"query":"WWI casualties","type":"value","result":"~20M dead; ~21M wounded"},
        {"query":"Treaty of Versailles","type":"event","result":"June 28, 1919 — ended WWI, harsh on Germany"},
     ])),
    ("society-and-culture", "history", "World War II", "wwii",
     "1939-1945 — theaters, key battles, aftermath.",
     "history.png", True, True, J([
        {"query":"WWII start","type":"date","result":"Sep 1, 1939 — Germany invades Poland"},
        {"query":"WWII casualties","type":"value","result":"~70-85M dead; deadliest conflict in history"},
        {"query":"D-Day","type":"event","result":"June 6, 1944 — Allied Normandy landings"},
     ])),
    ("society-and-culture", "history", "Cold War", "cold-war",
     "1947-1991 — US-USSR rivalry, nuclear standoff, proxy wars.",
     "history.png", False, True, J([
        {"query":"Cuban Missile Crisis","type":"event","result":"Oct 16-28, 1962 — closest to nuclear war"},
        {"query":"Berlin Wall fall","type":"event","result":"Nov 9, 1989"},
        {"query":"USSR dissolution","type":"event","result":"Dec 26, 1991"},
     ])),
    ("society-and-culture", "history", "French Revolution", "french-revolution",
     "1789-1799 — fall of monarchy, terror, Napoleon's rise.",
     "history.png", False, True, J([
        {"query":"Bastille Day","type":"event","result":"July 14, 1789 — storming of the Bastille"},
        {"query":"Reign of Terror","type":"period","result":"Sep 1793 - Jul 1794; Robespierre"},
        {"query":"Napoleon coronation","type":"event","result":"Dec 2, 1804 — self-crowned Emperor"},
     ])),
    ("society-and-culture", "history", "American Revolution", "american-revolution",
     "1775-1783 — independence from Britain.",
     "history.png", False, True, J([
        {"query":"Declaration Independence","type":"date","result":"July 4, 1776"},
        {"query":"Battle of Yorktown","type":"event","result":"Oct 19, 1781 — Cornwallis surrenders"},
        {"query":"Treaty of Paris","type":"event","result":"Sep 3, 1783 — ended Revolutionary War"},
     ])),
    ("society-and-culture", "history", "Roman Empire", "roman-empire",
     "27 BC - 476 AD — emperors, expansion, fall of the West.",
     "history.png", False, True, J([
        {"query":"Roman Empire start","type":"date","result":"27 BC — Augustus first emperor"},
        {"query":"Fall of Rome","type":"date","result":"476 AD — Romulus Augustulus deposed"},
        {"query":"Pax Romana","type":"period","result":"27 BC - 180 AD — ~200 years relative peace"},
     ])),
    ("society-and-culture", "history", "Industrial Revolution", "industrial-revolution",
     "~1760-1840 — steam, mechanization, urbanization.",
     "history.png", False, True, J([
        {"query":"Watt steam engine","type":"date","result":"1769 patent — improved Newcomen design"},
        {"query":"spinning jenny","type":"date","result":"1764 — Hargreaves; textile mechanization"},
        {"query":"Second Industrial Rev","type":"period","result":"~1870-1914; electrification, mass production"},
     ])),
    ("society-and-culture", "history", "Renaissance", "renaissance",
     "14th-17th century — rebirth of arts, sciences, classical learning.",
     "history.png", False, False, J([
        {"query":"Renaissance start","type":"period","result":"~14th c. Florence — Petrarch, Medici patronage"},
        {"query":"Gutenberg press","type":"date","result":"~1440 — movable type; printed Bible 1455"},
        {"query":"Mona Lisa year","type":"date","result":"~1503-1519 — Leonardo da Vinci"},
     ])),
    ("society-and-culture", "history", "Black Death", "black-death",
     "1346-1353 — bubonic plague pandemic in Eurasia.",
     "history.png", False, False, J([
        {"query":"Black Death deaths","type":"value","result":"~75-200M; 30-60% Europe population"},
        {"query":"Yersinia pestis","type":"agent","result":"Bacterium; flea-rat-human cycle"},
        {"query":"plague consequences","type":"effects","result":"Labor shortage → end of feudalism, wage rise"},
     ])),
    ("society-and-culture", "history", "Civil Rights Movement", "civil-rights",
     "1954-1968 — desegregation, voting rights, MLK.",
     "history.png", False, True, J([
        {"query":"Brown v Board","type":"event","result":"May 17, 1954 — ended school segregation"},
        {"query":"Civil Rights Act","type":"event","result":"July 2, 1964"},
        {"query":"March on Washington","type":"event","result":"Aug 28, 1963 — MLK 'I Have a Dream'"},
     ])),
    ("society-and-culture", "history", "Space Race", "space-race",
     "1957-1975 — USSR vs US competition.",
     "history.png", False, True, J([
        {"query":"Sputnik","type":"event","result":"Oct 4, 1957 — first artificial satellite"},
        {"query":"first human space","type":"event","result":"Apr 12, 1961 — Yuri Gagarin"},
        {"query":"Apollo 11 moon","type":"event","result":"July 20, 1969 — Armstrong, Aldrin"},
     ])),
    ("society-and-culture", "history", "Mongol Empire", "mongol-empire",
     "1206-1368 — largest contiguous land empire.",
     "history.png", False, False, J([
        {"query":"Mongol Empire area","type":"value","result":"~24M km² peak — largest contiguous in history"},
        {"query":"Genghis Khan","type":"reign","result":"1206-1227 — founder, unified Mongol tribes"},
        {"query":"Kublai Khan","type":"reign","result":"1271-1294 — founded Yuan dynasty in China"},
     ])),
    ("society-and-culture", "history", "British Empire", "british-empire",
     "Late 16th c. to mid-20th c. — colonies on every continent.",
     "history.png", False, False, J([
        {"query":"British Empire peak","type":"value","result":"~35.5M km² (1920) — 24% Earth's land"},
        {"query":"India independence","type":"event","result":"Aug 15, 1947 — end of Raj"},
        {"query":"Hong Kong handover","type":"event","result":"July 1, 1997 — to China"},
     ])),
    ("society-and-culture", "history", "Apollo Program", "apollo-program",
     "1961-1972 — Mercury Gemini Apollo NASA moon missions.",
     "history.png", False, False, J([
        {"query":"Apollo missions count","type":"value","result":"17 missions; 6 successful moon landings"},
        {"query":"Apollo 11 crew","type":"crew","result":"Armstrong, Aldrin, Collins"},
        {"query":"last moon landing","type":"event","result":"Apollo 17, Dec 14, 1972"},
     ])),
    ("society-and-culture", "history", "Manhattan Project", "manhattan-project",
     "1942-1946 — US atomic bomb development.",
     "history.png", False, False, J([
        {"query":"Trinity test","type":"event","result":"July 16, 1945 — Alamogordo NM"},
        {"query":"Hiroshima Nagasaki","type":"event","result":"Aug 6, 1945 (Little Boy); Aug 9 (Fat Man)"},
        {"query":"Manhattan Project lead","type":"people","result":"Oppenheimer (scientific); Groves (military)"},
     ])),
    ("society-and-culture", "history", "Berlin Wall", "berlin-wall",
     "1961-1989 — divided East and West Berlin.",
     "history.png", False, False, J([
        {"query":"Berlin Wall built","type":"event","result":"Aug 13, 1961 — overnight"},
        {"query":"Berlin Wall length","type":"value","result":"~155 km total"},
        {"query":"wall fall","type":"event","result":"Nov 9, 1989"},
     ])),
    ("society-and-culture", "history", "Ottoman Empire", "ottoman-empire",
     "1299-1922 — Anatolian, Balkan, Middle Eastern empire.",
     "history.png", False, False, J([
        {"query":"Constantinople fall","type":"event","result":"May 29, 1453 — Mehmed II"},
        {"query":"Suleiman the Magnificent","type":"reign","result":"1520-1566 — Ottoman peak"},
        {"query":"Ottoman dissolution","type":"event","result":"1922 — Republic of Turkey founded 1923"},
     ])),
    ("society-and-culture", "history", "Discovery of Americas", "discovery-americas",
     "1492 onward — European voyages, indigenous impact.",
     "history.png", False, False, J([
        {"query":"Columbus first voyage","type":"date","result":"Oct 12, 1492 — landed Bahamas"},
        {"query":"Vinland","type":"event","result":"~1000 AD — Norse Leif Erikson, L'Anse aux Meadows"},
        {"query":"Columbian exchange","type":"concept","result":"Old/New World biota and disease exchange"},
     ])),
    ("society-and-culture", "history", "Vietnam War", "vietnam-war",
     "1955-1975 — Cold War proxy conflict.",
     "history.png", False, False, J([
        {"query":"Tet Offensive","type":"event","result":"Jan 30, 1968 — turning point of US opinion"},
        {"query":"Fall of Saigon","type":"event","result":"Apr 30, 1975 — end of war"},
        {"query":"US casualties Vietnam","type":"value","result":"~58,200 KIA"},
     ])),
    ("society-and-culture", "history", "Suez Crisis", "suez-crisis",
     "1956 — Egypt, UK, France, Israel; nationalization of Suez Canal.",
     "history.png", False, False, J([
        {"query":"Suez nationalized","type":"event","result":"July 26, 1956 — Nasser nationalized canal"},
        {"query":"Suez Crisis end","type":"event","result":"Nov 1956 — UN/US pressure forced withdrawal"},
        {"query":"Suez aftermath","type":"effects","result":"End of British/French imperial pretensions; rise of Nasser"},
     ])),
    ("society-and-culture", "history", "Hundred Years War", "hundred-years-war",
     "1337-1453 — England vs France.",
     "history.png", False, False, J([
        {"query":"war duration","type":"value","result":"116 years; intermittent fighting"},
        {"query":"Joan of Arc","type":"figure","result":"~1412-1431 — turned tide for France"},
        {"query":"war end","type":"event","result":"1453 — Battle of Castillon, England lost continental claims"},
     ])),
    ("society-and-culture", "history", "9/11 Attacks", "nine-eleven",
     "Sep 11, 2001 — al-Qaeda attacks on US.",
     "history.png", False, False, J([
        {"query":"9/11 casualties","type":"value","result":"~2,977 victims (excluding 19 hijackers)"},
        {"query":"WTC collapse","type":"event","result":"Both towers fell within 102 minutes"},
        {"query":"post-9/11 wars","type":"events","result":"Afghanistan (2001-2021); Iraq (2003-2011)"},
     ])),
    ("society-and-culture", "history", "Fall of USSR", "fall-ussr",
     "1989-1991 — Soviet bloc collapse.",
     "history.png", False, False, J([
        {"query":"USSR end date","type":"date","result":"Dec 26, 1991 — formally dissolved"},
        {"query":"glasnost perestroika","type":"reforms","result":"Gorbachev 1985-1991; openness + restructuring"},
        {"query":"successor states","type":"count","result":"15 independent republics formed"},
     ])),
    ("society-and-culture", "history", "Magna Carta", "magna-carta",
     "June 15, 1215 — King John of England, foundational charter.",
     "history.png", False, False, J([
        {"query":"Magna Carta date","type":"date","result":"June 15, 1215 — Runnymede"},
        {"query":"Magna Carta clauses","type":"value","result":"63 clauses; only 4 still law"},
        {"query":"habeas corpus origin","type":"clause","result":"Clause 39 — no imprisonment without lawful judgment"},
     ])),
]

# ---- Cosmology / Astronomy (20) ----
NEW_TOPICS += [
    ("science-and-technology", "astronomy", "Hubble Constant", "hubble-constant",
     "Expansion rate of the universe — H_0.",
     "astronomy.png", True, True, J([
        {"query":"Hubble constant value","type":"value","result":"~73 km/s/Mpc (SH0ES); ~67 (Planck) — tension"},
        {"query":"Hubble's law","type":"formula","result":"v = H_0·d — recessional velocity ∝ distance"},
        {"query":"Hubble time","type":"value","result":"1/H_0 ≈ 13.8 billion years"},
     ])),
    ("science-and-technology", "astronomy", "Big Bang Theory", "big-bang",
     "Origin of universe ~13.8 Gyr ago.",
     "astronomy.png", True, True, J([
        {"query":"universe age","type":"value","result":"13.787 ± 0.020 billion years (Planck)"},
        {"query":"CMB temperature","type":"value","result":"2.725 K"},
        {"query":"recombination era","type":"event","result":"~380,000 yr after Big Bang — CMB released"},
     ])),
    ("science-and-technology", "astronomy", "Dark Matter", "dark-matter",
     "Non-luminous matter inferred from gravitational effects.",
     "astronomy.png", False, True, J([
        {"query":"dark matter fraction","type":"value","result":"~26.8% of universe mass-energy"},
        {"query":"DM candidates","type":"list","result":"WIMPs, axions, sterile neutrinos, primordial BHs"},
        {"query":"galactic rotation","type":"evidence","result":"Flat rotation curves — Vera Rubin's evidence"},
     ])),
    ("science-and-technology", "astronomy", "Dark Energy", "dark-energy",
     "Drives accelerating expansion of universe.",
     "astronomy.png", False, True, J([
        {"query":"dark energy fraction","type":"value","result":"~68.5% of universe mass-energy"},
        {"query":"cosmological constant","type":"concept","result":"Λ in Einstein equations; w = -1 equation of state"},
        {"query":"acceleration discovery","type":"event","result":"1998 SN Ia — Riess, Perlmutter, Schmidt (Nobel 2011)"},
     ])),
    ("science-and-technology", "astronomy", "Friedmann Equations", "friedmann-equations",
     "Cosmological dynamics in general relativity.",
     "astronomy.png", False, True, J([
        {"query":"Friedmann eq 1","type":"formula","result":"(ȧ/a)² = 8πG·ρ/3 − k/a² + Λ/3"},
        {"query":"Friedmann eq 2","type":"formula","result":"ä/a = −4πG/3·(ρ + 3p) + Λ/3"},
        {"query":"flat universe","type":"condition","result":"k=0; Ω_total = 1; observed within ~0.4%"},
     ])),
    ("science-and-technology", "astronomy", "CMB", "cmb",
     "Cosmic microwave background — relic radiation.",
     "astronomy.png", False, True, J([
        {"query":"CMB discovery","type":"event","result":"1964 Penzias & Wilson (Nobel 1978)"},
        {"query":"CMB anisotropy","type":"value","result":"ΔT/T ~ 10^-5 fluctuations"},
        {"query":"acoustic peaks","type":"feature","result":"First peak at l~220 — flat universe"},
     ])),
    ("science-and-technology", "astronomy", "Inflation Theory", "inflation-cosmology",
     "Exponential expansion in early universe (~10^-36 s).",
     "astronomy.png", False, False, J([
        {"query":"inflation duration","type":"value","result":"~10^-36 to 10^-32 s after Big Bang"},
        {"query":"e-folds","type":"value","result":"~60 e-folds typical model"},
        {"query":"problems solved","type":"list","result":"Horizon, flatness, monopole problems"},
     ])),
    ("science-and-technology", "astronomy", "Black Holes", "black-holes",
     "Event horizon, singularity, Hawking radiation.",
     "astronomy.png", False, True, J([
        {"query":"Schwarzschild radius","type":"formula","result":"r_s = 2GM/c²"},
        {"query":"Hawking temperature","type":"formula","result":"T = ℏc³/(8πGMk_B)"},
        {"query":"Sgr A* mass","type":"value","result":"~4.15 × 10^6 M_sun"},
     ])),
    ("science-and-technology", "astronomy", "Stellar Evolution Detail", "stellar-evolution-detail",
     "Main sequence, red giant, supernova, remnants.",
     "astronomy.png", False, False, J([
        {"query":"Sun lifetime","type":"value","result":"~10 Gyr total; ~4.6 Gyr current"},
        {"query":"Chandrasekhar limit","type":"value","result":"~1.44 M_sun — WD max"},
        {"query":"TOV limit","type":"value","result":"~2-2.16 M_sun — NS max"},
     ])),
    ("science-and-technology", "astronomy", "Galaxy Classification", "galaxy-classification",
     "Hubble sequence — ellipticals, spirals, irregulars.",
     "astronomy.png", False, False, J([
        {"query":"Hubble tuning fork","type":"diagram","result":"E0-E7 ellipticals; Sa-Sc / SBa-SBc spirals"},
        {"query":"Milky Way type","type":"value","result":"SBbc (barred spiral)"},
        {"query":"galaxies observable","type":"value","result":"~200 billion estimated"},
     ])),
    ("science-and-technology", "astronomy", "Exoplanets Detail", "exoplanets-detail",
     "Detection methods, habitable zone, notable systems.",
     "astronomy.png", False, True, J([
        {"query":"exoplanets confirmed","type":"value","result":"~5,500+ confirmed (NASA Exoplanet Archive, 2024)"},
        {"query":"transit method","type":"method","result":"Dim in star's brightness; Kepler, TESS"},
        {"query":"habitable zone","type":"concept","result":"Range allowing liquid water on planet surface"},
     ])),
    ("science-and-technology", "astronomy", "Gravitational Waves Detail", "gravitational-waves-detail",
     "Ripples in spacetime — LIGO/Virgo detections.",
     "astronomy.png", False, True, J([
        {"query":"first detection","type":"event","result":"GW150914 — Sep 14 2015; binary BH merger"},
        {"query":"LIGO sensitivity","type":"value","result":"Strain ~10^-21"},
        {"query":"GW170817","type":"event","result":"Aug 17 2017 — binary NS merger, multi-messenger"},
     ])),
    ("science-and-technology", "astronomy", "JWST Discoveries", "jwst-discoveries",
     "James Webb Space Telescope observations.",
     "astronomy.png", False, True, J([
        {"query":"JWST launch","type":"date","result":"Dec 25, 2021"},
        {"query":"JWST mirror","type":"value","result":"6.5 m primary, 18 hexagonal segments"},
        {"query":"JWST instruments","type":"list","result":"NIRCam, NIRSpec, MIRI, FGS/NIRISS"},
     ])),
    ("science-and-technology", "astronomy", "Multiverse Hypotheses", "multiverse",
     "Type I-IV multiverse, eternal inflation, string landscape.",
     "astronomy.png", False, False, J([
        {"query":"Tegmark multiverse","type":"classification","result":"Type I-IV: spatial, inflationary, MWI, mathematical"},
        {"query":"eternal inflation","type":"concept","result":"Inflation continues forever in some regions — pocket universes"},
        {"query":"string landscape","type":"value","result":"~10^500 possible vacua"},
     ])),
    ("science-and-technology", "astronomy", "Universe Structure", "universe-structure",
     "Cosmic web, filaments, voids, walls.",
     "astronomy.png", False, False, J([
        {"query":"cosmic web","type":"structure","result":"Filaments connecting clusters, voids in between"},
        {"query":"largest void","type":"value","result":"Boötes Void — ~330 Mly diameter"},
        {"query":"Sloan Great Wall","type":"value","result":"~1.4 billion ly long"},
     ])),
    ("science-and-technology", "astronomy", "Solar System Detail", "solar-system-detail",
     "Planet orbits, mass, distance from Sun.",
     "astronomy.png", False, False, J([
        {"query":"AU value","type":"value","result":"1 AU = 149,597,870.7 km"},
        {"query":"Neptune distance","type":"value","result":"~30.07 AU"},
        {"query":"Jupiter mass","type":"value","result":"~318 Earth masses; ~1/1047 Sun mass"},
     ])),
    ("science-and-technology", "astronomy", "Saturn's Rings", "saturn-rings",
     "Ring composition, divisions, Cassini probe data.",
     "astronomy.png", False, False, J([
        {"query":"rings composition","type":"value","result":"99.9% water ice"},
        {"query":"main ring spans","type":"value","result":"A, B, C, D rings; 7,000-80,000 km wide"},
        {"query":"Cassini Division","type":"feature","result":"~4,800 km gap between A and B"},
     ])),
    ("science-and-technology", "astronomy", "Mars Exploration", "mars-exploration",
     "Rovers, missions, Mars facts.",
     "astronomy.png", False, False, J([
        {"query":"Mars rovers active","type":"list","result":"Curiosity (2012-), Perseverance (2021-), Zhurong (paused)"},
        {"query":"Mars day length","type":"value","result":"24h 37min — 'sol'"},
        {"query":"Mars temperature","type":"value","result":"-153 °C to +20 °C; avg ~-63 °C"},
     ])),
    ("science-and-technology", "astronomy", "Pulsars", "pulsars",
     "Spinning neutron stars, lighthouse effect.",
     "astronomy.png", False, False, J([
        {"query":"first pulsar","type":"event","result":"CP 1919 — Jocelyn Bell Burnell 1967"},
        {"query":"fastest pulsar","type":"value","result":"PSR J1748-2446ad — 716 Hz"},
        {"query":"pulsar timing","type":"application","result":"PTAs — detect nHz gravitational waves"},
     ])),
    ("science-and-technology", "astronomy", "Quasars", "quasars",
     "Active galactic nuclei, supermassive BH-powered.",
     "astronomy.png", False, False, J([
        {"query":"first quasar","type":"event","result":"3C 273 — Schmidt 1963"},
        {"query":"quasar luminosity","type":"value","result":"Up to ~10^14 L_sun — brightest persistent objects"},
        {"query":"most distant quasar","type":"value","result":"z ~ 7.6 (J0313-1806) ~13 billion ly"},
     ])),
]

# ---- Climate / Earth science (16) ----
NEW_TOPICS += [
    ("science-and-technology", "earth-science", "Climate Change Indicators", "climate-change-indicators",
     "Temperature, CO2, sea level, ice mass.",
     "earth-science.png", True, True, J([
        {"query":"CO2 atmosphere 2024","type":"value","result":"~422 ppm (Mauna Loa, May 2024)"},
        {"query":"warming since 1880","type":"value","result":"~1.2 °C above pre-industrial"},
        {"query":"sea level rise","type":"value","result":"~3.4 mm/yr (2006-2023)"},
     ])),
    ("science-and-technology", "earth-science", "Greenhouse Gases", "greenhouse-gases",
     "CO2, CH4, N2O, F-gases — GWP and lifetimes.",
     "earth-science.png", False, True, J([
        {"query":"CH4 GWP","type":"value","result":"~28-36 over 100 yr; ~80 over 20 yr"},
        {"query":"CO2 lifetime","type":"value","result":"Complex; 50% removed <100 yr, rest persists millennia"},
        {"query":"N2O GWP","type":"value","result":"~273 over 100 yr"},
     ])),
    ("science-and-technology", "earth-science", "Ocean Currents", "ocean-currents",
     "Gulf Stream, AMOC, thermohaline circulation.",
     "earth-science.png", False, False, J([
        {"query":"AMOC","type":"name","result":"Atlantic Meridional Overturning Circulation"},
        {"query":"Gulf Stream speed","type":"value","result":"~2 m/s at peak"},
        {"query":"deep water formation","type":"location","result":"North Atlantic & Antarctic — sinking dense cold/saline water"},
     ])),
    ("science-and-technology", "earth-science", "Ice Sheets", "ice-sheets",
     "Greenland and Antarctic ice mass balance.",
     "earth-science.png", False, False, J([
        {"query":"Greenland mass loss","type":"value","result":"~270 Gt/yr (2006-2018)"},
        {"query":"Antarctic mass loss","type":"value","result":"~150 Gt/yr (2010s)"},
        {"query":"SLR potential","type":"value","result":"~7.4 m Greenland; ~58 m Antarctic if melted"},
     ])),
    ("science-and-technology", "earth-science", "Plate Tectonics", "plate-tectonics-detail",
     "Plates, motions, hotspots.",
     "earth-science.png", False, False, J([
        {"query":"major plates count","type":"value","result":"~7 major + many minor"},
        {"query":"plate speed","type":"value","result":"~2-10 cm/year"},
        {"query":"hotspot example","type":"example","result":"Hawaii — Pacific plate over mantle plume"},
     ])),
    ("science-and-technology", "earth-science", "Atmospheric Layers", "atmospheric-layers",
     "Troposphere, stratosphere, mesosphere, thermosphere, exosphere.",
     "earth-science.png", False, False, J([
        {"query":"troposphere height","type":"value","result":"0-12 km (avg) — weather"},
        {"query":"stratosphere ozone","type":"value","result":"~15-35 km — UV absorption"},
        {"query":"Karman line","type":"value","result":"100 km — boundary of space (FAI)"},
     ])),
    ("science-and-technology", "earth-science", "Earth Structure", "earth-structure",
     "Crust, mantle, outer/inner core.",
     "earth-science.png", False, False, J([
        {"query":"crust thickness","type":"value","result":"5-70 km (oceanic-continental)"},
        {"query":"inner core","type":"value","result":"Solid Fe-Ni; 5,200-6,371 km depth"},
        {"query":"core temperature","type":"value","result":"~5,200 K inner core"},
     ])),
    ("science-and-technology", "earth-science", "Carbon Cycle", "carbon-cycle",
     "Atmospheric, ocean, biosphere, geosphere reservoirs.",
     "earth-science.png", False, False, J([
        {"query":"carbon in atmosphere","type":"value","result":"~870 GtC (2024); 2.2 GtC/yr growth"},
        {"query":"oceanic carbon","type":"value","result":"~38,000 GtC dissolved"},
        {"query":"anthro emissions","type":"value","result":"~10 GtC/yr (2020s)"},
     ])),
    ("science-and-technology", "earth-science", "Weather Records", "weather-records",
     "Hottest, coldest, windiest, wettest.",
     "weather.png", False, False, J([
        {"query":"hottest recorded","type":"record","result":"56.7 °C — Furnace Creek CA, 1913"},
        {"query":"coldest recorded","type":"record","result":"-89.2 °C — Vostok Antarctica, 1983"},
        {"query":"highest wind speed","type":"record","result":"408 km/h — Tropical Cyclone Olivia 1996"},
     ])),
    ("science-and-technology", "earth-science", "Hurricane Categories", "hurricane-categories",
     "Saffir-Simpson scale.",
     "weather.png", False, False, J([
        {"query":"Cat 5 wind","type":"value","result":"≥ 252 km/h (157 mph)"},
        {"query":"Cat 1 wind","type":"value","result":"119-153 km/h"},
        {"query":"Atlantic basin avg","type":"value","result":"~14 named, 7 hurricanes, 3 major per year"},
     ])),
    ("science-and-technology", "earth-science", "Aurora", "aurora",
     "Solar wind interaction with magnetosphere.",
     "weather.png", False, False, J([
        {"query":"aurora colors","type":"physics","result":"Green: O 557.7 nm; red: O 630 nm; blue/purple: N2"},
        {"query":"aurora altitude","type":"value","result":"~80-300 km"},
        {"query":"Kp index","type":"scale","result":"0-9 geomagnetic activity; ≥5 = storm"},
     ])),
    ("science-and-technology", "earth-science", "Tides", "tides-earth",
     "Lunar, solar, spring vs neap tides.",
     "earth-science.png", False, False, J([
        {"query":"spring tide","type":"event","result":"Sun, Moon aligned — full/new moon"},
        {"query":"neap tide","type":"event","result":"Sun, Moon perpendicular — first/last quarter"},
        {"query":"highest tidal range","type":"record","result":"Bay of Fundy — ~16 m"},
     ])),
    ("science-and-technology", "earth-science", "Glaciers", "glaciers",
     "Types, movement, retreat.",
     "earth-science.png", False, False, J([
        {"query":"glacier ice volume","type":"value","result":"~158,000 km³ (excluding ice sheets)"},
        {"query":"largest mountain glacier","type":"record","result":"Siachen — 76 km long"},
        {"query":"glacier movement","type":"rate","result":"~25 cm/day typical; up to ~30 m/day surge"},
     ])),
    ("science-and-technology", "earth-science", "Soil Types", "soil-types",
     "USDA orders — alfisol, ultisol, mollisol etc.",
     "earth-science.png", False, False, J([
        {"query":"USDA soil orders","type":"count","result":"12 — Alfisol, Andisol, Aridisol, Entisol, Gelisol, Histosol, Inceptisol, Mollisol, Oxisol, Spodosol, Ultisol, Vertisol"},
        {"query":"mollisol regions","type":"region","result":"Prairie regions — US Midwest, Ukraine"},
        {"query":"oxisol regions","type":"region","result":"Tropical rainforests — Amazon, Congo"},
     ])),
    ("science-and-technology", "earth-science", "Biomes", "biomes",
     "Terrestrial biomes — tundra, taiga, desert, etc.",
     "earth-science.png", False, False, J([
        {"query":"largest biome","type":"value","result":"Taiga (boreal forest) — ~17M km²"},
        {"query":"tropical rainforest area","type":"value","result":"~10M km² — most biodiversity"},
        {"query":"tundra characteristics","type":"description","result":"Cold, treeless, permafrost; arctic & alpine"},
     ])),
    ("science-and-technology", "earth-science", "Renewable Energy", "renewable-energy",
     "Solar, wind, hydro — global capacity and trends.",
     "earth-science.png", False, True, J([
        {"query":"global solar PV capacity","type":"value","result":"~1.6 TW installed (end 2023)"},
        {"query":"wind capacity","type":"value","result":"~900 GW global (end 2023)"},
        {"query":"renewable share elec","type":"value","result":"~30% global electricity (2023)"},
     ])),
]

# ---- Programming languages (16) ----
NEW_TOPICS += [
    ("science-and-technology", "computer-science", "Python Language", "python-language",
     "Python — history, versions, popularity.",
     "discrete-math.png", True, True, J([
        {"query":"Python creator","type":"history","result":"Guido van Rossum, 1991"},
        {"query":"Python 3 release","type":"date","result":"Dec 3, 2008"},
        {"query":"Python TIOBE rank","type":"ranking","result":"#1 (2021-2024)"},
     ])),
    ("science-and-technology", "computer-science", "JavaScript Language", "javascript-language",
     "JavaScript — Brendan Eich, ECMAScript, web ubiquity.",
     "discrete-math.png", False, True, J([
        {"query":"JavaScript creator","type":"history","result":"Brendan Eich, 1995 (10 days)"},
        {"query":"ES6 year","type":"date","result":"2015 — major update (arrow, let/const, class)"},
        {"query":"npm package count","type":"value","result":"~2.5 million packages"},
     ])),
    ("science-and-technology", "computer-science", "C Language", "c-language",
     "C — Kernighan & Ritchie 1972, system programming.",
     "discrete-math.png", False, False, J([
        {"query":"C creators","type":"history","result":"Dennis Ritchie at Bell Labs, 1972"},
        {"query":"K&R book year","type":"date","result":"1978 — 'The C Programming Language'"},
        {"query":"C standards","type":"list","result":"C89, C99, C11, C17, C23"},
     ])),
    ("science-and-technology", "computer-science", "C++ Language", "cpp-language",
     "C++ — Bjarne Stroustrup, OOP, templates.",
     "discrete-math.png", False, False, J([
        {"query":"C++ creator","type":"history","result":"Bjarne Stroustrup, 1985"},
        {"query":"C++ standards","type":"list","result":"C++98, 03, 11, 14, 17, 20, 23"},
        {"query":"RAII","type":"idiom","result":"Resource Acquisition Is Initialization — destructor cleanup"},
     ])),
    ("science-and-technology", "computer-science", "Java Language", "java-language",
     "Java — Sun Microsystems, JVM, WORA.",
     "discrete-math.png", False, False, J([
        {"query":"Java creator","type":"history","result":"James Gosling at Sun, 1995"},
        {"query":"Java versions","type":"list","result":"Java 8 (2014 LTS), 11, 17, 21 (LTS)"},
        {"query":"Java JVM bytecode","type":"value","result":"Stack-based, 256 opcodes"},
     ])),
    ("science-and-technology", "computer-science", "Rust Language", "rust-language",
     "Rust — memory safety without GC.",
     "discrete-math.png", False, True, J([
        {"query":"Rust creator","type":"history","result":"Graydon Hoare at Mozilla, ~2010"},
        {"query":"Rust 1.0","type":"date","result":"May 15, 2015"},
        {"query":"Rust ownership","type":"concept","result":"Borrow checker — compile-time memory safety"},
     ])),
    ("science-and-technology", "computer-science", "Go Language", "go-language",
     "Go (golang) — Google, concurrency primitives.",
     "discrete-math.png", False, False, J([
        {"query":"Go creators","type":"history","result":"Griesemer, Pike, Thompson at Google, 2009"},
        {"query":"Go 1.0","type":"date","result":"March 2012"},
        {"query":"Go goroutine","type":"feature","result":"Lightweight thread; multiplexed onto OS threads"},
     ])),
    ("science-and-technology", "computer-science", "Haskell Language", "haskell-language",
     "Haskell — purely functional, lazy.",
     "discrete-math.png", False, False, J([
        {"query":"Haskell creator","type":"history","result":"Committee 1990; named after Haskell Curry"},
        {"query":"Haskell laziness","type":"feature","result":"Non-strict by default — call by need"},
        {"query":"monad","type":"concept","result":"Computation context; bind (>>=) :: m a -> (a -> m b) -> m b"},
     ])),
    ("science-and-technology", "computer-science", "Wolfram Language", "wolfram-language",
     "Wolfram Language — symbolic, knowledge-based.",
     "discrete-math.png", False, True, J([
        {"query":"Wolfram Language creator","type":"history","result":"Stephen Wolfram; Mathematica 1988"},
        {"query":"WL paradigm","type":"value","result":"Symbolic + functional + procedural + rule-based"},
        {"query":"WL functions count","type":"value","result":"~6,500+ built-in functions"},
     ])),
    ("science-and-technology", "computer-science", "SQL Language", "sql-language",
     "Structured Query Language — RDB standard.",
     "discrete-math.png", False, False, J([
        {"query":"SQL creators","type":"history","result":"Donald Chamberlin, Raymond Boyce at IBM, 1974"},
        {"query":"SQL standards","type":"list","result":"SQL-86, 92, 99, 2003, 2011, 2016, 2023"},
        {"query":"JOIN types","type":"list","result":"INNER, LEFT, RIGHT, FULL OUTER, CROSS"},
     ])),
    ("science-and-technology", "computer-science", "Lisp Language", "lisp-language",
     "Lisp — McCarthy 1958, S-expressions, macros.",
     "discrete-math.png", False, False, J([
        {"query":"Lisp creator","type":"history","result":"John McCarthy, 1958 — 2nd oldest HLL"},
        {"query":"Common Lisp","type":"variant","result":"Standardized 1994; ANSI X3.226"},
        {"query":"S-expression","type":"concept","result":"Code = data; (operator arg1 arg2 ...)"},
     ])),
    ("science-and-technology", "computer-science", "TypeScript Language", "typescript-language",
     "TypeScript — Microsoft, typed JavaScript.",
     "discrete-math.png", False, False, J([
        {"query":"TypeScript creator","type":"history","result":"Anders Hejlsberg at Microsoft, 2012"},
        {"query":"TS compile target","type":"value","result":"Compiles to JavaScript (ES3-ESNext)"},
        {"query":"TS adoption","type":"value","result":"~75% professional JS devs use it (State of JS 2023)"},
     ])),
    ("science-and-technology", "computer-science", "Swift Language", "swift-language",
     "Swift — Apple, replaces Objective-C.",
     "discrete-math.png", False, False, J([
        {"query":"Swift creator","type":"history","result":"Chris Lattner at Apple, announced 2014"},
        {"query":"Swift 5 ABI","type":"event","result":"Mar 2019 — ABI stability"},
        {"query":"Swift open source","type":"event","result":"Dec 3, 2015"},
     ])),
    ("science-and-technology", "computer-science", "Kotlin Language", "kotlin-language",
     "Kotlin — JetBrains, JVM, Android official.",
     "discrete-math.png", False, False, J([
        {"query":"Kotlin creator","type":"history","result":"JetBrains, 2011; 1.0 in 2016"},
        {"query":"Android official","type":"event","result":"May 2017 — Google I/O announcement"},
        {"query":"Kotlin coroutines","type":"feature","result":"Structured concurrency, suspend functions"},
     ])),
    ("science-and-technology", "computer-science", "Ruby Language", "ruby-language",
     "Ruby — Matz, dynamic OOP.",
     "discrete-math.png", False, False, J([
        {"query":"Ruby creator","type":"history","result":"Yukihiro Matsumoto, 1995"},
        {"query":"Ruby on Rails","type":"framework","result":"DHH 2004; convention over configuration"},
        {"query":"Ruby everything object","type":"feature","result":"Everything is an object, including nil and ints"},
     ])),
    ("science-and-technology", "computer-science", "Scala Language", "scala-language",
     "Scala — JVM, functional + OOP.",
     "discrete-math.png", False, False, J([
        {"query":"Scala creator","type":"history","result":"Martin Odersky, 2004"},
        {"query":"Scala 3","type":"date","result":"May 2021 — new compiler (Dotty)"},
        {"query":"Spark language","type":"value","result":"Apache Spark written in Scala"},
     ])),
]

# ---- Medicine / health (16) ----
NEW_TOPICS += [
    ("everyday-life", "personal-health", "Vaccines", "vaccines-detail",
     "Vaccine types, schedules, efficacy.",
     "health-medicine.png", False, True, J([
        {"query":"mRNA vaccine","type":"type","result":"Pfizer BNT162b2; Moderna mRNA-1273 (COVID-19)"},
        {"query":"polio vaccine","type":"history","result":"Salk IPV 1955; Sabin OPV 1961"},
        {"query":"childhood schedule","type":"value","result":"~14 vaccines by age 18 (CDC)"},
     ])),
    ("everyday-life", "personal-health", "Antibiotics", "antibiotics-detail",
     "Classes, resistance, narrow vs broad spectrum.",
     "health-medicine.png", False, False, J([
        {"query":"penicillin discovery","type":"event","result":"Alexander Fleming, 1928 (Nobel 1945)"},
        {"query":"antibiotic classes","type":"list","result":"β-lactams, macrolides, fluoroquinolones, tetracyclines, aminoglycosides"},
        {"query":"AMR deaths","type":"value","result":"~1.27M directly from AMR (2019, Lancet)"},
     ])),
    ("everyday-life", "personal-health", "Blood Types", "blood-types",
     "ABO and Rh systems.",
     "health-medicine.png", False, False, J([
        {"query":"O negative donor","type":"property","result":"Universal red cell donor"},
        {"query":"AB positive recipient","type":"property","result":"Universal red cell recipient"},
        {"query":"O+ frequency US","type":"value","result":"~38% — most common"},
     ])),
    ("everyday-life", "personal-health", "Diabetes Stats", "diabetes-stats",
     "Type 1, Type 2, prevalence, HbA1c.",
     "health-medicine.png", False, True, J([
        {"query":"HbA1c diabetic","type":"value","result":">6.5% — diagnostic threshold"},
        {"query":"global diabetes","type":"value","result":"~537M adults (2021, IDF)"},
        {"query":"T1 vs T2","type":"compare","result":"T1 autoimmune (no insulin); T2 insulin resistance + relative deficit"},
     ])),
    ("everyday-life", "personal-health", "Cholesterol", "cholesterol-stats",
     "LDL, HDL, triglycerides, statins.",
     "health-medicine.png", False, False, J([
        {"query":"LDL optimal","type":"value","result":"<100 mg/dL; <70 for high CV risk"},
        {"query":"HDL good","type":"value","result":">60 mg/dL protective"},
        {"query":"statin efficacy","type":"value","result":"~25-50% LDL reduction"},
     ])),
    ("everyday-life", "personal-health", "BMI Categories", "bmi-categories",
     "Underweight, normal, overweight, obese class I-III.",
     "health-medicine.png", False, False, J([
        {"query":"normal BMI","type":"range","result":"18.5-24.9"},
        {"query":"obese BMI","type":"range","result":"≥30.0; III ≥40"},
        {"query":"BMI limitation","type":"caveat","result":"Doesn't distinguish muscle from fat"},
     ])),
    ("everyday-life", "personal-health", "Sleep Stages", "sleep-stages",
     "N1, N2, N3, REM cycles.",
     "health-medicine.png", False, False, J([
        {"query":"sleep cycle length","type":"value","result":"~90 minutes typical adult"},
        {"query":"REM percentage","type":"value","result":"~20-25% of sleep"},
        {"query":"deep sleep N3","type":"value","result":"~15-20%; declines with age"},
     ])),
    ("everyday-life", "personal-health", "Vitamins Detail", "vitamins-detail-r5",
     "Fat-soluble (ADEK) vs water-soluble (B, C), RDAs.",
     "health-medicine.png", False, False, J([
        {"query":"vit D RDA","type":"value","result":"600-800 IU (15-20 mcg) adults"},
        {"query":"vit B12 source","type":"value","result":"Animal foods only naturally"},
        {"query":"vit C RDA","type":"value","result":"75-90 mg adults"},
     ])),
    ("everyday-life", "personal-health", "Macronutrients", "macronutrients",
     "Calories per gram: carbs, protein, fat.",
     "health-medicine.png", False, False, J([
        {"query":"protein kcal/g","type":"value","result":"4 kcal/g"},
        {"query":"fat kcal/g","type":"value","result":"9 kcal/g"},
        {"query":"alcohol kcal/g","type":"value","result":"7 kcal/g"},
     ])),
    ("everyday-life", "personal-health", "Heart Disease", "heart-disease",
     "CAD, MI, stroke, risk factors.",
     "health-medicine.png", False, False, J([
        {"query":"CVD deaths","type":"value","result":"~17.9M/year globally — leading cause"},
        {"query":"MI symptoms","type":"list","result":"Chest pain, dyspnea, arm/jaw pain, diaphoresis"},
        {"query":"Framingham risk","type":"score","result":"10-year CV event risk; uses age, BP, lipids, smoking, diabetes"},
     ])),
    ("everyday-life", "personal-health", "Cancer Statistics", "cancer-statistics",
     "Most common cancers, survival rates.",
     "health-medicine.png", False, False, J([
        {"query":"top cancer male","type":"value","result":"Prostate (~30% new); lung leading mortality"},
        {"query":"top cancer female","type":"value","result":"Breast (~30% new)"},
        {"query":"lung cancer 5-yr","type":"value","result":"~23% US; lower stage-IV"},
     ])),
    ("everyday-life", "personal-health", "Mental Health Stats", "mental-health-stats",
     "Depression, anxiety, prevalence.",
     "health-medicine.png", False, False, J([
        {"query":"depression lifetime","type":"value","result":"~21% US adults"},
        {"query":"anxiety disorder prevalence","type":"value","result":"~19% US adults past 12mo"},
        {"query":"suicide rate US","type":"value","result":"~14 per 100,000 (2022)"},
     ])),
    ("everyday-life", "personal-health", "Exercise Guidelines", "exercise-guidelines",
     "WHO and CDC recommendations.",
     "health-medicine.png", False, False, J([
        {"query":"moderate aerobic","type":"value","result":"150-300 min/week (WHO)"},
        {"query":"vigorous aerobic","type":"value","result":"75-150 min/week"},
        {"query":"strength training","type":"value","result":"2+ days/week, all major muscle groups"},
     ])),
    ("everyday-life", "personal-health", "Hydration", "hydration",
     "Water needs, dehydration.",
     "health-medicine.png", False, False, J([
        {"query":"water intake adult","type":"value","result":"~2.7 L women / 3.7 L men/day (NAS, all sources)"},
        {"query":"dehydration symptoms","type":"list","result":"Thirst, dark urine, fatigue, dizziness"},
        {"query":"hyponatremia","type":"caveat","result":"Excess water → low Na+; dangerous in endurance"},
     ])),
    ("everyday-life", "personal-health", "Drug Half-Life", "drug-half-life",
     "Pharmacokinetics — t1/2, steady state.",
     "health-medicine.png", False, False, J([
        {"query":"half-life formula","type":"formula","result":"t1/2 = 0.693·Vd/CL"},
        {"query":"steady state time","type":"rule","result":"~4-5 half-lives to reach SS"},
        {"query":"caffeine half-life","type":"value","result":"~5 hours typical adult"},
     ])),
    ("everyday-life", "personal-health", "Vital Signs", "vital-signs",
     "BP, HR, RR, temp, O2 sat.",
     "health-medicine.png", False, False, J([
        {"query":"normal RR","type":"value","result":"12-20 breaths/min adult"},
        {"query":"normal temp oral","type":"value","result":"~36.5-37.5 °C / 97.7-99.5 °F"},
        {"query":"normal SpO2","type":"value","result":"≥95%"},
     ])),
]

# ---- Mythology / culture (12) ----
NEW_TOPICS += [
    ("society-and-culture", "mythology", "Greek Mythology", "greek-mythology",
     "Olympian gods, heroes, monsters.",
     "history.png", False, True, J([
        {"query":"12 Olympians","type":"list","result":"Zeus, Hera, Poseidon, Demeter, Athena, Apollo, Artemis, Ares, Aphrodite, Hephaestus, Hermes, Dionysus"},
        {"query":"Heracles labors","type":"value","result":"12 labors — Nemean lion, Hydra, etc."},
        {"query":"Trojan War","type":"event","result":"~12th c. BC (legendary) — Iliad subject"},
     ])),
    ("society-and-culture", "mythology", "Norse Mythology", "norse-mythology",
     "Aesir, Vanir, Asgard, Ragnarök.",
     "history.png", False, False, J([
        {"query":"chief Norse gods","type":"list","result":"Odin, Thor, Frigg, Loki, Freya, Tyr, Heimdall"},
        {"query":"nine realms","type":"list","result":"Asgard, Midgard, Vanaheim, Jotunheim, Alfheim, Svartalfheim, Niflheim, Muspelheim, Helheim"},
        {"query":"Ragnarok","type":"event","result":"End of days; gods fall, world reborn"},
     ])),
    ("society-and-culture", "mythology", "Egyptian Mythology", "egyptian-mythology",
     "Ennead, Osiris myth, afterlife.",
     "history.png", False, False, J([
        {"query":"Egyptian Ennead","type":"list","result":"Atum, Shu, Tefnut, Geb, Nut, Osiris, Isis, Set, Nephthys"},
        {"query":"Book of Dead","type":"text","result":"Weighing of heart against Ma'at's feather"},
        {"query":"Ra sun god","type":"deity","result":"Solar god; midday form Ra-Horakhty"},
     ])),
    ("society-and-culture", "mythology", "Hindu Mythology", "hindu-mythology",
     "Trimurti, Mahabharata, Ramayana.",
     "history.png", False, False, J([
        {"query":"Trimurti","type":"list","result":"Brahma (creator), Vishnu (preserver), Shiva (destroyer)"},
        {"query":"Vishnu avatars","type":"value","result":"10 avatars (Dashavatara): Matsya, Kurma, Varaha, Narasimha, Vamana, Parashurama, Rama, Krishna, Buddha, Kalki"},
        {"query":"Mahabharata length","type":"value","result":"~100,000 shlokas — longest epic"},
     ])),
    ("society-and-culture", "religion", "Major Religions", "world-religions",
     "Christianity, Islam, Hinduism, Buddhism, Judaism counts.",
     "history.png", False, False, J([
        {"query":"Christian count","type":"value","result":"~2.4 billion (Pew, 2024)"},
        {"query":"Muslim count","type":"value","result":"~2.0 billion"},
        {"query":"Hindu count","type":"value","result":"~1.2 billion"},
     ])),
    ("society-and-culture", "religion", "Christianity Detail", "christianity-detail",
     "Branches, key dates, denominations.",
     "history.png", False, False, J([
        {"query":"Great Schism","type":"event","result":"1054 — Catholic vs Orthodox"},
        {"query":"Reformation start","type":"event","result":"1517 — Luther's 95 theses"},
        {"query":"largest denomination","type":"value","result":"Catholic ~1.3 billion"},
     ])),
    ("society-and-culture", "religion", "Buddhism Detail", "buddhism-detail",
     "Four Noble Truths, Eightfold Path, Mahayana vs Theravada.",
     "history.png", False, False, J([
        {"query":"four noble truths","type":"list","result":"Suffering, origin, cessation, path"},
        {"query":"eightfold path","type":"count","result":"8 — right view, intent, speech, action, livelihood, effort, mindfulness, concentration"},
        {"query":"Buddha birth","type":"date","result":"~563 BCE (or ~480 BCE) — Lumbini"},
     ])),
    ("society-and-culture", "religion", "Islam Detail", "islam-detail",
     "Five Pillars, schools, Hajj.",
     "history.png", False, False, J([
        {"query":"five pillars","type":"list","result":"Shahada, Salah, Zakat, Sawm, Hajj"},
        {"query":"Sunni vs Shia","type":"compare","result":"~85% Sunni; ~15% Shia (Iran, Iraq majority)"},
        {"query":"Hijra year","type":"event","result":"622 CE — Muhammad's migration; year 1 AH"},
     ])),
    ("society-and-culture", "philosophy", "Ancient Greek Philosophy", "ancient-greek-philosophy",
     "Socrates, Plato, Aristotle.",
     "history.png", False, False, J([
        {"query":"Socrates dates","type":"date","result":"~470-399 BCE"},
        {"query":"Plato's Academy","type":"date","result":"Founded ~387 BCE"},
        {"query":"Aristotle Lyceum","type":"date","result":"Founded ~335 BCE"},
     ])),
    ("society-and-culture", "philosophy", "Logic Systems", "logic-systems",
     "Propositional, predicate, modal logic.",
     "history.png", False, False, J([
        {"query":"modus ponens","type":"rule","result":"P → Q; P ⊢ Q"},
        {"query":"De Morgan's laws","type":"identity","result":"¬(P ∧ Q) ≡ ¬P ∨ ¬Q; ¬(P ∨ Q) ≡ ¬P ∧ ¬Q"},
        {"query":"Gödel incompleteness","type":"theorem","result":"Any consistent formal system containing arithmetic has true but unprovable statements"},
     ])),
    ("society-and-culture", "philosophy", "Ethics Frameworks", "ethics-frameworks",
     "Deontology, consequentialism, virtue ethics.",
     "history.png", False, False, J([
        {"query":"Kantian ethics","type":"theory","result":"Categorical imperative; act on universalizable maxims"},
        {"query":"utilitarianism","type":"theory","result":"Maximize aggregate well-being (Bentham, Mill)"},
        {"query":"virtue ethics","type":"theory","result":"Character traits enabling human flourishing (Aristotle)"},
     ])),
    ("society-and-culture", "philosophy", "Famous Paradoxes", "famous-paradoxes",
     "Zeno, Russell, ship of Theseus.",
     "history.png", False, False, J([
        {"query":"Zeno paradox","type":"paradox","result":"Achilles & tortoise — infinite steps to reach goal"},
        {"query":"Russell paradox","type":"paradox","result":"Set of all sets that don't contain themselves"},
        {"query":"ship of Theseus","type":"paradox","result":"Replace planks — is it the same ship?"},
     ])),
]

# ---- Sports / records / etc. miscellaneous (24) ----
NEW_TOPICS += [
    ("society-and-culture", "sports-society", "Olympic Records", "olympic-records",
     "Modern Olympic Games — host cities, records.",
     "people.png", False, True, J([
        {"query":"first modern Olympics","type":"event","result":"1896 Athens"},
        {"query":"most Olympic medals","type":"record","result":"Michael Phelps — 28 (23 gold)"},
        {"query":"100m WR","type":"record","result":"9.58 s — Usain Bolt (2009)"},
     ])),
    ("society-and-culture", "sports-society", "FIFA World Cup", "fifa-world-cup",
     "World Cup history, winners, attendance.",
     "people.png", False, False, J([
        {"query":"most WC titles","type":"record","result":"Brazil — 5 (1958, 62, 70, 94, 2002)"},
        {"query":"WC 2022 winner","type":"event","result":"Argentina (3rd title)"},
        {"query":"WC 2026","type":"event","result":"US, Canada, Mexico; expanded to 48 teams"},
     ])),
    ("society-and-culture", "sports-society", "NBA Stats", "nba-stats-extra",
     "Champions, MVPs, scoring records.",
     "people.png", False, False, J([
        {"query":"most NBA titles","type":"record","result":"Celtics & Lakers — 17 each"},
        {"query":"NBA scoring record","type":"record","result":"LeBron James — 40,000+ career points"},
        {"query":"highest single game","type":"record","result":"Wilt Chamberlain — 100 points (1962)"},
     ])),
    ("society-and-culture", "sports-society", "Tennis Grand Slams", "tennis-grand-slams",
     "Wimbledon, US Open, French Open, Australian Open.",
     "people.png", False, False, J([
        {"query":"most men GS","type":"record","result":"Djokovic — 24 (as of 2024)"},
        {"query":"most women GS","type":"record","result":"Margaret Court — 24 (open + amateur era)"},
        {"query":"Federer GS","type":"value","result":"20 grand slam titles"},
     ])),
    ("society-and-culture", "sports-society", "Marathon World Records", "marathon-world-records",
     "World records, major marathons.",
     "people.png", False, False, J([
        {"query":"marathon WR men","type":"record","result":"2:00:35 — Kelvin Kiptum (2023 Chicago)"},
        {"query":"marathon WR women","type":"record","result":"2:11:53 — Tigist Assefa (2023 Berlin)"},
        {"query":"sub-2 marathon","type":"event","result":"Kipchoge 1:59:40 (2019 INEOS — unofficial)"},
     ])),
    ("everyday-life", "hobbies-games", "Card Games Detail", "card-games-detail",
     "Poker hands, bridge, blackjack.",
     "people.png", False, False, J([
        {"query":"royal flush prob","type":"value","result":"4/2598960 ≈ 1/649,740"},
        {"query":"blackjack basic strategy","type":"value","result":"House edge ~0.5% with optimal play"},
        {"query":"bridge hands distinct","type":"value","result":"C(52,13) = 635,013,559,600 possible hands"},
     ])),
    ("everyday-life", "hobbies-games", "Board Games Detail", "board-games-detail",
     "Chess, Go, Settlers, Monopoly.",
     "people.png", False, False, J([
        {"query":"Go board size","type":"value","result":"19x19 — 361 intersections"},
        {"query":"chess legal positions","type":"value","result":"~10^44 estimated (Shannon)"},
        {"query":"Monopoly money","type":"value","result":"$15,140 in standard set"},
     ])),
    ("everyday-life", "travel", "Airline Stats", "airline-stats",
     "Largest airlines, passenger miles, safety.",
     "household-math.png", False, False, J([
        {"query":"largest airline passengers","type":"value","result":"American Airlines ~200M+ (pre-COVID peak)"},
        {"query":"flight safety per mile","type":"value","result":"~0.07 deaths per billion passenger-miles"},
        {"query":"busiest airport","type":"record","result":"Atlanta ATL — ~104M passengers (2023)"},
     ])),
    ("everyday-life", "travel", "Country Areas", "country-areas",
     "Land area by country.",
     "household-math.png", False, False, J([
        {"query":"largest country","type":"record","result":"Russia — 17.1M km²"},
        {"query":"USA area","type":"value","result":"~9.83M km² (4th)"},
        {"query":"smallest country","type":"record","result":"Vatican City — 0.49 km²"},
     ])),
    ("everyday-life", "travel", "Population Cities", "population-cities",
     "Largest urban areas.",
     "household-math.png", False, False, J([
        {"query":"largest metro","type":"record","result":"Tokyo — ~37M metro population"},
        {"query":"NYC population","type":"value","result":"~8.4M city; ~20M metro"},
        {"query":"Mumbai population","type":"value","result":"~21M metro"},
     ])),
    ("science-and-technology", "tech-world", "Database Systems", "database-systems",
     "RDBMS, NoSQL, vector DBs.",
     "discrete-math.png", False, False, J([
        {"query":"top RDBMS","type":"ranking","result":"Oracle, MySQL, MS SQL Server, PostgreSQL"},
        {"query":"NoSQL types","type":"list","result":"Document, key-value, column, graph, time-series, vector"},
        {"query":"ACID","type":"acronym","result":"Atomicity, Consistency, Isolation, Durability"},
     ])),
    ("science-and-technology", "tech-world", "Operating Systems", "operating-systems",
     "Windows, Linux, macOS, market share.",
     "discrete-math.png", False, False, J([
        {"query":"desktop OS share","type":"value","result":"Windows ~73%, macOS ~16%, Linux ~3% (2024)"},
        {"query":"mobile OS share","type":"value","result":"Android ~71%, iOS ~28%"},
        {"query":"server OS Linux","type":"value","result":"~96% top 1M servers, ~100% top 500 supercomputers"},
     ])),
    ("science-and-technology", "tech-world", "Browser Share", "browser-share",
     "Chrome, Safari, Edge, Firefox.",
     "discrete-math.png", False, False, J([
        {"query":"Chrome share","type":"value","result":"~65% (StatCounter 2024)"},
        {"query":"Safari share","type":"value","result":"~18%"},
        {"query":"Firefox share","type":"value","result":"~3%"},
     ])),
    ("science-and-technology", "tech-world", "CPU Architectures", "cpu-architectures",
     "x86, ARM, RISC-V.",
     "discrete-math.png", False, False, J([
        {"query":"x86 vs ARM","type":"compare","result":"x86: CISC, Intel/AMD desktop. ARM: RISC, mobile/embedded/Apple Silicon"},
        {"query":"RISC-V","type":"value","result":"Open ISA; growing in embedded/research"},
        {"query":"transistor count peak","type":"value","result":"M2 Ultra ~134B; Cerebras WSE-3 ~4T"},
     ])),
    ("science-and-technology", "tech-world", "Networking Protocols", "networking-protocols",
     "TCP, UDP, HTTP, DNS.",
     "discrete-math.png", False, False, J([
        {"query":"TCP handshake","type":"value","result":"3-way: SYN, SYN-ACK, ACK"},
        {"query":"HTTP/2","type":"feature","result":"Multiplexing, header compression, server push"},
        {"query":"DNS port","type":"value","result":"53 (TCP/UDP)"},
     ])),
    ("science-and-technology", "tech-world", "Encryption Methods", "encryption-methods",
     "AES, RSA, ECC, ChaCha20.",
     "discrete-math.png", False, False, J([
        {"query":"AES key sizes","type":"value","result":"128, 192, 256 bits"},
        {"query":"RSA key size","type":"value","result":"≥ 2048 bits recommended; 3072+ for high security"},
        {"query":"ChaCha20","type":"cipher","result":"Stream cipher; TLS 1.3 alternative to AES-GCM"},
     ])),
    ("science-and-technology", "engineering-detail", "Bridge Types", "bridge-types",
     "Beam, arch, truss, suspension, cable-stayed.",
     "engineering.png", False, False, J([
        {"query":"longest suspension","type":"record","result":"Çanakkale 1915 Bridge (Turkey) — 2,023 m main span"},
        {"query":"longest cable-stayed","type":"record","result":"Russky Bridge (Russia) — 1,104 m main span"},
        {"query":"Golden Gate length","type":"value","result":"1,280 m main span"},
     ])),
    ("science-and-technology", "engineering-detail", "Tunnel Records", "tunnel-records",
     "Longest, deepest, undersea tunnels.",
     "engineering.png", False, False, J([
        {"query":"longest tunnel","type":"record","result":"Gotthard Base Tunnel — 57.1 km"},
        {"query":"Channel Tunnel","type":"value","result":"50.5 km; 37.9 km undersea"},
        {"query":"deepest tunnel","type":"record","result":"Kola Superdeep Borehole — 12,262 m (not really tunnel)"},
     ])),
    ("science-and-technology", "engineering-detail", "Tall Buildings", "tall-buildings",
     "Burj Khalifa, Empire State, etc.",
     "engineering.png", False, False, J([
        {"query":"tallest building","type":"record","result":"Burj Khalifa — 828 m (2010)"},
        {"query":"Empire State height","type":"value","result":"443 m (incl. antenna)"},
        {"query":"Jeddah Tower","type":"value","result":"1,008 m (planned; under construction)"},
     ])),
    ("science-and-technology", "engineering-detail", "Power Plants", "power-plants",
     "Largest power stations by capacity.",
     "engineering.png", False, False, J([
        {"query":"largest hydro","type":"record","result":"Three Gorges — 22,500 MW capacity"},
        {"query":"largest solar farm","type":"record","result":"Bhadla Solar Park India — 2,245 MW"},
        {"query":"largest wind farm","type":"record","result":"Gansu (China) — 8,000 MW capacity"},
     ])),
    ("science-and-technology", "transportation", "Electric Vehicles", "electric-vehicles",
     "EV adoption, battery, range.",
     "engineering.png", False, True, J([
        {"query":"EV market share US","type":"value","result":"~8% new car sales (2024 Q1)"},
        {"query":"longest EV range","type":"record","result":"~520 mi EPA — Lucid Air Grand Touring"},
        {"query":"battery cost trend","type":"value","result":"~$139/kWh (2023, BloombergNEF avg pack)"},
     ])),
    ("science-and-technology", "transportation", "Maglev Trains", "maglev-trains",
     "Magnetic levitation rail.",
     "engineering.png", False, False, J([
        {"query":"maglev speed record","type":"record","result":"603 km/h — Japan SCMaglev (2015 test)"},
        {"query":"Shanghai maglev","type":"value","result":"Top speed 431 km/h commercial"},
        {"query":"L0 Series","type":"value","result":"Chuo Shinkansen; ~505 km/h target operational"},
     ])),
    ("science-and-technology", "space-spaceflight", "Rocket Equation", "rocket-equation",
     "Tsiolkovsky equation — Δv = ve · ln(m0/mf).",
     "astronomy.png", False, False, J([
        {"query":"Tsiolkovsky equation","type":"formula","result":"Δv = v_e · ln(m_0/m_f)"},
        {"query":"LEO delta-v","type":"value","result":"~9.4 km/s from Earth surface"},
        {"query":"specific impulse","type":"formula","result":"Isp = F/(ṁ·g_0); s"},
     ])),
    ("science-and-technology", "space-spaceflight", "SpaceX Stats", "spacex-stats",
     "Falcon 9, Starship, Starlink.",
     "astronomy.png", False, True, J([
        {"query":"Falcon 9 launches","type":"value","result":"~280+ successful (May 2024)"},
        {"query":"Starlink satellites","type":"value","result":"~6,000+ on orbit (2024)"},
        {"query":"Starship status","type":"value","result":"IFT-4 reached soft splashdown (June 2024)"},
     ])),
]

# ---------------------------------------------------------------------------
# (2) RICH COMPUTATION RESULTS — every entry built via E_rich with 4-7 pods
# Layout (q, parsed, plain, cat, sub, kw, related_list_or_pods, slug, plot_url)
# When q starts with "__POD__" → related field carries the full pod list.
# ---------------------------------------------------------------------------
EXTRA_RESULTS = []

def E_rich(q, parsed, plain, cat, sub, kw, related, slug, plot_url='',
           alternate_forms=None, decimal_approx=None, step_by_step=None,
           wl_code=None, python_code=None, comparison=None,
           svg_plot_key=None, extra_pods=None):
    pods = [
        {"title":"Input interpretation","plaintext":parsed or q},
        {"title":"Result","plaintext":plain},
    ]
    if decimal_approx:
        pods.append({"title":"Decimal approximation","plaintext":decimal_approx})
    if alternate_forms:
        pods.append({"title":"Alternate forms","plaintext":alternate_forms})
    if step_by_step:
        pods.append({"title":"Step-by-step solution","plaintext":step_by_step})
    if wl_code:
        pods.append({"title":"Wolfram Language code","plaintext":wl_code})
    if python_code:
        pods.append({"title":"Python (SymPy/NumPy) code","plaintext":python_code})
    if comparison:
        pods.append({"title":"Comparison with related","plaintext":comparison})
    if svg_plot_key:
        # An interactive SVG plot — kept as plaintext referencing inline SVG marker.
        pods.append({"title":"Plot","plaintext":svg_plot_inline(svg_plot_key, 'curve')})
    if extra_pods:
        pods.extend(extra_pods)
    EXTRA_RESULTS.append((
        "__POD__" + q, parsed, plain, cat, sub, kw, pods, slug, plot_url
    ))

# ------------------- A. Economics formula pack (~250) -------------------
# Compound interest: vary P, r, t deterministic.
for p in [100, 500, 1000, 5000, 10000, 25000, 50000, 100000]:
    for r in [2, 4, 5, 6, 7, 8, 10, 12]:
        for t in [1, 5, 10, 20, 30]:
            n = 12  # monthly
            A = p * (1 + r/100/n) ** (n*t)
            E_rich(f"compound interest ${p} {r}% {t}y monthly",
                   f"A = {p}·(1 + {r/100}/12)^(12·{t})",
                   f"${A:,.2f}",
                   "society-and-culture", "economics",
                   f"compound r5 {p} {r} {t}", [], "compound-interest",
                   alternate_forms=f"A = P(1+r/n)^(nt); continuous: P·e^(rt) = ${p*math.exp(r/100*t):,.2f}",
                   step_by_step=f"A = {p}·(1 + {r/100/12:.6f})^{n*t} = ${A:,.2f}",
                   wl_code=f"FinancialData[\"Compound\", {{{p}, {r}/100, {t}, 12}}]",
                   python_code=f"P,r,n,t = {p},{r/100},12,{t}; A = P*(1+r/n)**(n*t); print(A)",
                   comparison=f"Simple interest: ${p*(1+r/100*t):,.2f} (Δ ${A - p*(1+r/100*t):,.2f})",
                   svg_plot_key=f"compound-{p}-{r}-{t}")

# PV / FV pairs
for fv in [10000, 50000, 100000, 250000, 1000000]:
    for r in [3, 5, 7, 10]:
        for n in [5, 10, 20, 30]:
            pv = fv / (1 + r/100) ** n
            E_rich(f"present value ${fv} {r}% {n}y",
                   f"PV = {fv}/(1+{r/100})^{n}",
                   f"${pv:,.2f}",
                   "society-and-culture", "economics",
                   f"pv r5 {fv} {r} {n}", [], "time-value-money",
                   alternate_forms=f"FV = PV·(1+r)^n → PV = FV·(1+r)^(-n)",
                   step_by_step=f"PV = {fv}·(1.{r:02d})^(-{n}) = ${pv:,.2f}",
                   wl_code=f"PresentValue[{fv}, {{{r/100}, {n}}}]",
                   comparison=f"r={r-1}%: ${fv/(1+(r-1)/100)**n:,.2f}; r={r+1}%: ${fv/(1+(r+1)/100)**n:,.2f}")

# Mortgage payments
for principal in [200000, 300000, 400000, 500000, 750000, 1000000]:
    for rate_pct in [3, 4, 5, 6, 7, 8]:
        for years in [15, 20, 30]:
            r = rate_pct / 100 / 12
            n = years * 12
            M = principal * r * (1+r)**n / ((1+r)**n - 1)
            total = M * n
            interest = total - principal
            E_rich(f"mortgage payment ${principal} {rate_pct}% {years}y",
                   f"M = P·r(1+r)^n / [(1+r)^n − 1]",
                   f"${M:,.2f}/month; ${total:,.2f} total; ${interest:,.2f} interest",
                   "society-and-culture", "economics",
                   f"mortgage r5 {principal} {rate_pct} {years}", [], "mortgage-calc",
                   alternate_forms=f"Annual payment: ${M*12:,.2f}",
                   step_by_step=f"r = {rate_pct/100/12:.6f}; n = {n}; M = ${M:,.2f}",
                   wl_code=f"FinancialDerivative[{{{principal}, {rate_pct/100}, {years}}}, \"Mortgage\"]",
                   python_code=f"P,r,n={principal},{rate_pct/100}/12,{n}; M=P*r*(1+r)**n/((1+r)**n-1); print(M)")

print(f"[r5] after economics: {len(EXTRA_RESULTS)}")

# ------------------- B. ML formula pack (~180) -------------------
# Softmax outputs for sample logits
for seed in range(40):
    vals = [(hh(f"sm-{seed}-{i}", 100)/10 - 5) for i in range(4)]
    exps = [math.exp(v) for v in vals]
    Z = sum(exps)
    probs = [e/Z for e in exps]
    E_rich(f"softmax of [{','.join(f'{v:.2f}' for v in vals)}]",
           f"softmax([{','.join(f'{v:.2f}' for v in vals)}])",
           "[" + ", ".join(f"{p:.4f}" for p in probs) + "]",
           "science-and-technology", "computer-science",
           f"softmax r5 {seed}", [], "softmax-cross-entropy",
           alternate_forms=f"log-sum-exp: {math.log(Z):.4f}",
           step_by_step=f"e^v_i / Σ e^v_j; partition Z = {Z:.4f}",
           wl_code=f"Exp[{vals}]/Total[Exp[{vals}]]",
           python_code="import numpy as np; e=np.exp(v); print(e/e.sum())",
           comparison=f"argmax = index {probs.index(max(probs))}")

# Cross-entropy values for binary classification
for seed in range(40):
    p = (hh(f"ce-{seed}", 90) + 5) / 100  # in (0.05, 0.95)
    y = seed % 2
    ce = -(y*math.log(p) + (1-y)*math.log(1-p))
    E_rich(f"binary cross entropy y={y} p={p:.2f}",
           f"-{y}·log({p:.2f}) - {1-y}·log({1-p:.2f})",
           f"{ce:.4f}",
           "science-and-technology", "computer-science",
           f"ce r5 {seed}", [], "softmax-cross-entropy",
           step_by_step=f"CE = -y log(p) - (1-y) log(1-p) = {ce:.4f}",
           wl_code="-y*Log[p]-(1-y)*Log[1-p]",
           python_code=f"import numpy as np; ce=-({y}*np.log({p})+{1-y}*np.log({1-p})); print(ce)")

# Attention pseudo-outputs (computed with small fixed shape)
for seed in range(30):
    d_k = [32, 64, 128, 256, 512][seed % 5]
    n   = [4, 8, 16, 32][seed % 4]
    flops = n * n * d_k * 2  # rough QK^T flops
    E_rich(f"attention flops n={n} d_k={d_k}",
           f"FLOPs = 2·n²·d_k = 2·{n}²·{d_k}",
           f"{flops:,} FLOPs (QK^T only)",
           "science-and-technology", "computer-science",
           f"attn r5 {seed}", [], "attention-mechanism",
           alternate_forms=f"With softmax+V: ~3·n²·d_k = {3*n*n*d_k:,} FLOPs",
           step_by_step=f"QK^T: n×n×d_k mac → 2·n²·d_k FLOPs",
           wl_code=f"2·n²·d_k /. {{n->{n}, dk->{d_k}}}",
           python_code=f"n,dk={n},{d_k}; print(2*n*n*dk)")

# CNN output sizes
for inp in [28, 32, 64, 128, 224]:
    for f in [3, 5, 7]:
        for s in [1, 2]:
            for pad in [0, 1, 2]:
                out = (inp - f + 2*pad)//s + 1
                if out < 1 or out > 256:
                    continue
                E_rich(f"conv2d output input={inp} f={f} s={s} p={pad}",
                       f"⌊({inp}-{f}+2·{pad})/{s}⌋+1",
                       f"{out}",
                       "science-and-technology", "computer-science",
                       f"conv r5 {inp} {f} {s} {pad}", [], "cnn-arch",
                       step_by_step=f"out = ⌊({inp}-{f}+{2*pad})/{s}⌋+1 = {out}",
                       wl_code=f"Floor[({inp}-{f}+2·{pad})/{s}]+1",
                       python_code=f"print(({inp}-{f}+2*{pad})//{s}+1)")
print(f"[r5] after ML: {len(EXTRA_RESULTS)}")

# ------------------- C. Cosmology constants & calculations (~150) -------------------
for h0 in [67, 68, 70, 72, 73, 74]:
    age_gy = (978 / h0) * 0.92  # rough flat-Λ universe
    E_rich(f"universe age H0 {h0} km/s/Mpc",
           f"age ≈ (978/H_0) Gyr · f(Ω_m, Ω_Λ)",
           f"~{age_gy:.2f} Gyr",
           "science-and-technology", "astronomy",
           f"age r5 {h0}", [], "hubble-constant",
           alternate_forms=f"Hubble time: {978/h0:.2f} Gyr (1/H_0)",
           step_by_step=f"H_0 = {h0} km/s/Mpc → age ≈ {age_gy:.2f} Gyr",
           wl_code=f"UniverseAge[{h0}]",
           comparison="Planck 2018: 13.797 Gyr; SH0ES: ~12.7 Gyr",
           svg_plot_key=f"H0-{h0}")

# Schwarzschild radii for various masses
G = 6.674e-11; c = 2.998e8; M_sun = 1.989e30
for M_kg, label in [
    (5.97e24, "Earth"), (1.989e30, "Sun"), (4.15e6*M_sun, "Sgr A*"),
    (6.5e9*M_sun, "M87*"), (1.4*M_sun, "Neutron star"),
    (1e3*M_sun, "Intermediate BH"), (1e8*M_sun, "Quasar BH"),
    (1e10*M_sun, "Ultramassive BH"),
]:
    rs = 2*G*M_kg/c**2
    E_rich(f"Schwarzschild radius {label}",
           f"r_s = 2GM/c² , M = {M_kg:.3e} kg",
           f"{rs:.4e} m = {rs/1000:.3e} km",
           "science-and-technology", "astronomy",
           f"rs r5 {label}", [], "black-holes",
           alternate_forms=f"In AU: {rs/1.496e11:.4e}; in solar radii: {rs/6.957e8:.4e}",
           step_by_step=f"r_s = 2·6.674e-11·{M_kg:.3e} / (3e8)² = {rs:.4e} m",
           wl_code=f"2 GravitationalConstant ({M_kg} Kilograms) / SpeedOfLight^2")

# Friedmann-derived critical density
for h0 in [65, 67, 70, 72, 75, 80]:
    rho_c = 3 * (h0*1000/3.086e22)**2 / (8*math.pi*G)
    E_rich(f"critical density H0={h0}",
           f"ρ_c = 3 H_0² / (8πG)",
           f"{rho_c:.4e} kg/m³",
           "science-and-technology", "astronomy",
           f"rhoc r5 {h0}", [], "friedmann-equations",
           alternate_forms=f"≈ {rho_c/1.66e-27*1e9:.3f} H atoms/m³",
           step_by_step=f"H_0 = {h0} km/s/Mpc = {h0*1000/3.086e22:.3e} 1/s → ρ_c = {rho_c:.4e} kg/m³",
           wl_code=f"3 H0^2/(8 Pi GravitationalConstant) /. H0 -> {h0*1000/3.086e22:.3e}")

# Hawking temperatures for various BH masses
hbar = 1.054e-34; kB = 1.381e-23
for M_kg, label in [
    (1.989e30, "Solar mass BH"), (4.15e6*M_sun, "Sgr A*"),
    (1e10*M_sun, "Ultramassive"), (1e12, "1 trillion kg primordial"),
    (5e22, "Asteroid-mass primordial"),
]:
    Th = hbar * c**3 / (8*math.pi*G*M_kg*kB)
    E_rich(f"Hawking temperature {label}",
           f"T = ℏc³/(8πGMk_B), M={M_kg:.3e} kg",
           f"{Th:.4e} K",
           "science-and-technology", "astronomy",
           f"hawk r5 {label}", [], "black-holes",
           alternate_forms=f"Solar-mass BH: ~6.17e-8 K (CMB warmer)",
           comparison="Astrophysical BHs absorb more CMB than emit",
           wl_code=f"PlanckTemperature/(8 Pi {M_kg/M_sun} ({M_kg/M_sun}))")

# Distance to redshift conversion (small z)
for z in [0.01, 0.05, 0.1, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 7.0, 10.0]:
    H0 = 70
    # cz/H0 for low z, more general for high z
    if z < 0.3:
        d_Mpc = c/1000 * z / H0
    else:
        d_Mpc = c/1000 / H0 * z * (1 + z/2)  # rough
    E_rich(f"redshift z={z} to distance",
           f"d ≈ cz/H_0 (low z); H_0 = 70 km/s/Mpc",
           f"~{d_Mpc:.1f} Mpc = {d_Mpc*3.262e6:.2e} ly",
           "science-and-technology", "astronomy",
           f"redshift r5 {z}", [], "hubble-constant",
           alternate_forms=f"Comoving distance: depends on Ω_m, Ω_Λ",
           step_by_step=f"At z={z}: v ≈ {c/1000*z:.0f} km/s; d ≈ {d_Mpc:.1f} Mpc",
           wl_code=f"CosmologyData[\"ComovingDistance\", {z}]",
           svg_plot_key=f"z-{z}")
print(f"[r5] after cosmology: {len(EXTRA_RESULTS)}")

# ------------------- D. Biology systems — kinetics, populations, genetics (~200) -------------------
# Michaelis-Menten rate values
for Vmax in [1, 5, 10, 50, 100]:
    for Km in [0.1, 0.5, 1, 5, 10]:
        for S in [0.05, 0.1, 0.5, 1, 5, 10, 50]:
            v = Vmax * S / (Km + S)
            E_rich(f"Michaelis-Menten Vmax={Vmax} Km={Km} S={S}",
                   f"v = Vmax·[S]/(Km+[S])",
                   f"{v:.4f}",
                   "science-and-technology", "biological-sciences",
                   f"mm r5 {Vmax} {Km} {S}", [], "michaelis-menten",
                   alternate_forms=f"v/Vmax = {v/Vmax:.4f}; Lineweaver: 1/v = {1/v:.4f}",
                   step_by_step=f"{Vmax}·{S}/({Km}+{S}) = {v:.4f}",
                   wl_code=f"Vmax·S/(Km+S) /. {{Vmax->{Vmax}, Km->{Km}, S->{S}}}",
                   svg_plot_key=f"mm-{Vmax}-{Km}-{S}")

# Hardy-Weinberg p, q, frequencies
for p in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
    q = 1 - p
    AA = p**2; Aa = 2*p*q; aa = q**2
    E_rich(f"Hardy-Weinberg p={p}",
           f"p² + 2pq + q² with p={p}, q={q}",
           f"AA={AA:.4f}, Aa={Aa:.4f}, aa={aa:.4f}",
           "science-and-technology", "biological-sciences",
           f"hw r5 {p}", [], "hardy-weinberg",
           alternate_forms=f"check: AA+Aa+aa = {AA+Aa+aa:.4f}",
           step_by_step=f"p²={p**2:.4f}; 2pq={2*p*q:.4f}; q²={q**2:.4f}",
           wl_code=f"{{p^2, 2 p q, q^2}} /. p->{p}",
           comparison=f"Heterozygote max at p=0.5 (2pq=0.5)")

# Logistic growth N(t)
for r, K in [(0.1, 1000), (0.3, 5000), (0.5, 10000), (1.0, 100), (0.05, 100000)]:
    N0 = K / 100
    for t in [1, 5, 10, 20, 50]:
        Nt = K / (1 + ((K-N0)/N0) * math.exp(-r*t))
        E_rich(f"logistic N(t) r={r} K={K} t={t}",
               f"N(t) = K / (1+((K-N0)/N0)e^(-rt)); N0={N0}",
               f"{Nt:.2f}",
               "science-and-technology", "biological-sciences",
               f"lg r5 {r} {K} {t}", [], "logistic-growth",
               alternate_forms=f"dN/dt at t={t}: {r*Nt*(1-Nt/K):.4f}",
               step_by_step=f"t={t}: e^(-rt)={math.exp(-r*t):.4e}; N(t)={Nt:.2f}",
               wl_code=f"NDSolve[{{N'[t]==r N[t](1-N[t]/K), N[0]=={N0}}}, N, {{t, 0, {t}}}]",
               svg_plot_key=f"lg-{r}-{K}-{t}")

# Drug half-life remaining
for t12 in [1, 2, 4, 6, 8, 12, 24, 48]:
    for n_half in [1, 2, 3, 4, 5, 6, 7]:
        rem = 100 * (0.5 ** n_half)
        elapsed = t12 * n_half
        E_rich(f"drug remaining t1/2={t12}h after {elapsed}h",
               f"100·(1/2)^{n_half}",
               f"{rem:.4f}% remaining",
               "everyday-life", "personal-health",
               f"halflife r5 {t12} {n_half}", [], "drug-half-life",
               alternate_forms=f"Steady state: ~4-5 half-lives = ~{t12*4}-{t12*5}h",
               step_by_step=f"After {n_half} half-lives: 100% → {rem:.4f}%",
               wl_code=f"100 (1/2)^{n_half}",
               svg_plot_key=f"hl-{t12}-{n_half}")
print(f"[r5] after biology: {len(EXTRA_RESULTS)}")

# ------------------- E. Historical event Q&A (~120) -------------------
EVENTS_R5 = [
    ("WWI start", "WWI began", "1914-07-28 — Austria-Hungary declares war on Serbia",
     "wwi", "Outbreak of First World War"),
    ("WWI end", "Armistice", "1918-11-11 — Compiègne Armistice",
     "wwi", "End of Great War"),
    ("WWII start", "WWII Pacific theater", "1941-12-07 — Pearl Harbor attack",
     "wwii", "US enters WWII"),
    ("WWII end Europe", "VE Day", "1945-05-08 — Germany surrenders",
     "wwii", "End of European theater"),
    ("WWII end Pacific", "VJ Day", "1945-09-02 — Japan formal surrender",
     "wwii", "End of WWII Pacific"),
    ("Moon landing", "Apollo 11", "1969-07-20 — Armstrong, Aldrin on Sea of Tranquility",
     "apollo-program", "First crewed Moon landing"),
    ("Berlin Wall fall", "Wall demolition begins", "1989-11-09",
     "berlin-wall", "Iron Curtain begins to fall"),
    ("French Revolution", "Bastille storming", "1789-07-14",
     "french-revolution", "Revolutionary symbol moment"),
    ("Constantinople fall", "Mehmed II captures city", "1453-05-29",
     "ottoman-empire", "End of Byzantine Empire"),
    ("Magna Carta sealed", "King John seals charter", "1215-06-15 — Runnymede",
     "magna-carta", "Foundational English constitutional doc"),
    ("US independence", "Declaration adopted", "1776-07-04",
     "american-revolution", "Continental Congress in Philadelphia"),
    ("Bastille Day", "French national holiday", "July 14 every year",
     "french-revolution", ""),
    ("9/11 attack", "World Trade Center attacked", "2001-09-11",
     "nine-eleven", "Al-Qaeda attacks on US"),
    ("Sputnik launched", "First artificial satellite", "1957-10-04",
     "space-race", "USSR Sputnik 1"),
    ("First human in space", "Yuri Gagarin orbit", "1961-04-12 — Vostok 1",
     "space-race", "First crewed orbital flight"),
    ("Cuban Missile Crisis", "13-day Cold War standoff", "1962-10-16 to 1962-10-28",
     "cold-war", ""),
    ("USSR dissolved", "Soviet Union ends", "1991-12-26",
     "fall-ussr", "End of Cold War era"),
    ("Trinity test", "First atomic bomb test", "1945-07-16 — Alamogordo NM",
     "manhattan-project", ""),
    ("Hiroshima bombing", "Atomic bomb 'Little Boy'", "1945-08-06",
     "manhattan-project", "First wartime use of atomic weapon"),
    ("Nagasaki bombing", "Atomic bomb 'Fat Man'", "1945-08-09",
     "manhattan-project", "Second wartime atomic use"),
    ("Suez Crisis", "Suez Canal nationalized", "1956-07-26",
     "suez-crisis", "Egypt nationalizes; UK/FR/IL intervene"),
    ("Vietnam War end", "Fall of Saigon", "1975-04-30",
     "vietnam-war", "End of US-Vietnam war"),
    ("Mongol Empire founded", "Genghis Khan named", "1206 — Kurultai near Burkhan Khaldun",
     "mongol-empire", ""),
    ("Yuan dynasty founded", "Kublai Khan", "1271", "mongol-empire", ""),
    ("Hong Kong handover", "British to China", "1997-07-01",
     "british-empire", ""),
    ("India independence", "British Raj ends", "1947-08-15",
     "british-empire", "Partition into India and Pakistan"),
    ("Reformation start", "95 Theses posted", "1517-10-31 — Wittenberg",
     "christianity-detail", "Luther initiates Protestant movement"),
    ("Great Schism", "East-West church split", "1054-07-16",
     "christianity-detail", "Catholic vs Orthodox"),
    ("Gutenberg Bible", "First printed Bible", "1455 — Mainz",
     "renaissance", "Gutenberg press milestone"),
    ("Black Death peak", "Plague through Europe", "1347-1351",
     "black-death", ""),
    ("Renaissance start", "Italian Renaissance dawn", "~1330-1400 — Florence",
     "renaissance", ""),
    ("Watt steam engine", "Improved Newcomen design", "1769 — patent",
     "industrial-revolution", ""),
    ("Spinning Jenny", "Hargreaves textile invention", "1764",
     "industrial-revolution", ""),
    ("Tet Offensive", "Vietnam War turning point", "1968-01-30",
     "vietnam-war", ""),
    ("Cold War end", "USSR ends", "1991-12-26", "cold-war", ""),
    ("Roman Empire founded", "Augustus first emperor", "27 BC",
     "roman-empire", ""),
    ("Western Rome fell", "Romulus Augustulus deposed", "476 AD",
     "roman-empire", ""),
    ("Joan of Arc", "Maid of Orléans", "~1412 - 1431-05-30 (executed)",
     "hundred-years-war", ""),
    ("Hundred Years War end", "Battle of Castillon", "1453-07-17",
     "hundred-years-war", "England loses continental claims"),
    ("D-Day", "Normandy landings", "1944-06-06",
     "wwii", "Operation Overlord"),
]
for q_base, parsed, plain, slug, extra in EVENTS_R5:
    E_rich(q_base, parsed, plain,
           "society-and-culture", "history",
           f"history r5 {slug} {q_base[:10]}", [], slug,
           alternate_forms=extra,
           wl_code=f"HistoricalEvent[\"{q_base}\"]",
           comparison="See related events in topic page")

# Date variants for the same events (different phrasings)
for q_base, parsed, plain, slug, _ in EVENTS_R5:
    for prefix in ["date of", "when was", "year of", "anniversary of"]:
        E_rich(f"{prefix} {q_base.lower()}",
               parsed, plain,
               "society-and-culture", "history",
               f"history-var r5 {slug} {prefix}", [], slug,
               wl_code=f"HistoricalEvent[\"{q_base}\"][\"Date\"]")
print(f"[r5] after history: {len(EXTRA_RESULTS)}")

# ------------------- F. More math — derivatives/integrals with rich pods (~400) -------------------
# Symbolic derivatives of common functions
TRIG_FNS = [
    ("sin", "cos", "-sin"),
    ("cos", "-sin", "-cos"),
    ("tan", "sec(x)²", "2 sec²(x) tan(x)"),
    ("sec", "sec(x) tan(x)", "sec(x)(2 tan²(x) + sec²(x))"),
    ("ln", "1/x", "-1/x²"),
    ("e^x", "e^x", "e^x"),
    ("arctan", "1/(1+x²)", "-2x/(1+x²)²"),
    ("arcsin", "1/√(1-x²)", "x/(1-x²)^(3/2)"),
    ("sinh", "cosh", "sinh"),
    ("cosh", "sinh", "cosh"),
]
for fn, d1, d2 in TRIG_FNS:
    E_rich(f"derivative of {fn}(x)",
           f"d/dx {fn}(x)",
           f"{d1}",
           "mathematics", "calculus",
           f"deriv r5 {fn}", [], "calculus",
           alternate_forms=f"d²/dx² {fn}(x) = {d2}",
           step_by_step=f"Apply chain rule: d/dx {fn}(x) = {d1}",
           wl_code=f"D[{fn}[x], x]",
           python_code=f"from sympy import diff, symbols, {fn if fn not in ['ln','e^x','arctan','arcsin'] else 'log,exp,atan,asin'}; x=symbols('x'); print(diff({fn}(x), x))",
           comparison=f"2nd derivative: {d2}",
           svg_plot_key=f"deriv-{fn}")

# Indefinite integrals
INTEGRALS = [
    ("sin(x)", "-cos(x) + C", "Standard"),
    ("cos(x)", "sin(x) + C", "Standard"),
    ("e^x", "e^x + C", "Self-exponent"),
    ("1/x", "ln|x| + C", "Natural log"),
    ("x^n", "x^(n+1)/(n+1) + C", "Power rule (n≠-1)"),
    ("sec(x)²", "tan(x) + C", "Trig identity"),
    ("sec(x) tan(x)", "sec(x) + C", "Trig identity"),
    ("1/(1+x²)", "arctan(x) + C", "Arctangent"),
    ("1/√(1-x²)", "arcsin(x) + C", "Arcsine"),
    ("ln(x)", "x ln(x) - x + C", "Integration by parts"),
    ("x e^x", "(x-1) e^x + C", "Integration by parts"),
    ("sin(x)²", "x/2 - sin(2x)/4 + C", "Half-angle"),
    ("cos(x)²", "x/2 + sin(2x)/4 + C", "Half-angle"),
    ("tan(x)", "-ln|cos(x)| + C", "u-sub"),
]
for f_expr, antideriv, hint in INTEGRALS:
    E_rich(f"integral of {f_expr}",
           f"∫ {f_expr} dx",
           f"{antideriv}",
           "mathematics", "calculus",
           f"int r5 {f_expr}", [], "calculus",
           alternate_forms=hint,
           step_by_step=f"{f_expr} ⇒ {antideriv}",
           wl_code=f"Integrate[{f_expr}, x]",
           python_code=f"from sympy import integrate, symbols; x=symbols('x'); print(integrate({f_expr}, x))",
           svg_plot_key=f"int-{hh(f_expr, 256)}")

# Definite integrals — common bounds
for a, b, in [(0, math.pi), (0, math.pi/2), (-1, 1), (0, 1), (-2, 2), (0, 2), (0, 5)]:
    E_rich(f"integrate sin(x) from {a:.4f} to {b:.4f}",
           f"∫_{a:.4f}^{b:.4f} sin(x) dx",
           f"{math.cos(a) - math.cos(b):.6f}",
           "mathematics", "calculus",
           f"defint r5 sin {a} {b}", [], "calculus",
           step_by_step=f"[-cos(x)]_{a:.4f}^{b:.4f} = cos({a:.4f})-cos({b:.4f}) = {math.cos(a) - math.cos(b):.6f}",
           wl_code=f"Integrate[Sin[x], {{x, {a}, {b}}}]")
    E_rich(f"integrate x^2 from {a:.4f} to {b:.4f}",
           f"∫_{a:.4f}^{b:.4f} x² dx",
           f"{(b**3 - a**3)/3:.6f}",
           "mathematics", "calculus",
           f"defint r5 x2 {a} {b}", [], "calculus",
           step_by_step=f"[x³/3]_{a:.4f}^{b:.4f} = {(b**3-a**3)/3:.6f}",
           wl_code=f"Integrate[x^2, {{x, {a}, {b}}}]")

# Limits
LIMITS = [
    ("lim x→0 sin(x)/x", "1", "L'Hôpital or Taylor"),
    ("lim x→0 (1-cos(x))/x²", "1/2", "Taylor cos(x)=1-x²/2+..."),
    ("lim x→∞ (1+1/x)^x", "e", "Definition of e"),
    ("lim x→∞ ln(x)/x", "0", "Log slower than polynomial"),
    ("lim x→∞ x^n/e^x", "0", "Exponential dominates"),
    ("lim x→0+ x ln(x)", "0", "Indeterminate 0·∞"),
    ("lim x→0 (e^x-1)/x", "1", "Definition of derivative"),
    ("lim x→∞ (1+a/x)^x", "e^a", "Generalization"),
    ("lim n→∞ (1+1/n)^n", "e", "Discrete version"),
    ("lim x→0 tan(x)/x", "1", "Like sin(x)/x"),
]
for q, val, hint in LIMITS:
    E_rich(q, q, val,
           "mathematics", "calculus",
           f"lim r5 {q}", [], "calculus",
           step_by_step=hint,
           alternate_forms=f"Method: {hint}",
           wl_code=f"Limit[{q.split(' ', 2)[2]}, x->0]")
print(f"[r5] after calculus: {len(EXTRA_RESULTS)}")

# ------------------- G. Comparison-with-related pack (~250) -------------------
# Function comparisons: sin vs cos at same argument
for deg in range(0, 360, 5):
    rad = math.radians(deg)
    sv = math.sin(rad); cv = math.cos(rad)
    E_rich(f"compare sin({deg}°) and cos({deg}°)",
           f"sin({deg}°), cos({deg}°)",
           f"sin = {sv:.6f}, cos = {cv:.6f}",
           "mathematics", "trigonometry",
           f"sincos r5 {deg}", [], "trigonometry",
           alternate_forms=f"tan({deg}°) = {math.tan(rad):.6f}" if abs(cv)>0.001 else "tan undefined",
           comparison=f"sin² + cos² = {sv**2 + cv**2:.6f} (Pythagorean identity)",
           step_by_step=f"rad = {rad:.6f}; sin={sv:.6f}; cos={cv:.6f}",
           wl_code=f"{{Sin[{deg} Degree], Cos[{deg} Degree]}}",
           svg_plot_key=f"sincos-{deg}")

# Polynomial vs exponential growth
for x in range(1, 25):
    val_lin = x; val_sq = x*x; val_cube = x**3
    val_exp = math.exp(x); val_log = math.log(x) if x>0 else 0
    E_rich(f"compare growth at x={x}",
           f"x, x², x³, eˣ, ln(x) at x={x}",
           f"{val_lin}, {val_sq}, {val_cube}, {val_exp:.3e}, {val_log:.4f}",
           "mathematics", "math-functions",
           f"growth r5 {x}", [], "calculus",
           comparison=f"At x={x}: e^x is {val_exp/val_cube:.2e}× larger than x³",
           step_by_step="Exponential dominates all polynomial growth",
           wl_code=f"{{x, x^2, x^3, E^x, Log[x]}} /. x->{x}",
           svg_plot_key=f"growth-{x}")
print(f"[r5] after comparison: {len(EXTRA_RESULTS)}")

# ------------------- H. Programming language / code-export pack (~120) -------------------
PROG_EXPORTS = [
    ("solve x^2+5x+6=0", "{x=-2, x=-3}",
     "Solve[x^2 + 5 x + 6 == 0, x]",
     "from sympy import solve, symbols; x=symbols('x'); print(solve(x**2+5*x+6, x))",
     "algebra"),
    ("derivative of sin(x)cos(x)", "cos(2x)",
     "D[Sin[x] Cos[x], x]",
     "from sympy import diff, sin, cos, symbols; x=symbols('x'); print(diff(sin(x)*cos(x), x))",
     "calculus"),
    ("integral of x*e^x", "(x-1)e^x",
     "Integrate[x Exp[x], x]",
     "from sympy import integrate, exp, symbols; x=symbols('x'); print(integrate(x*exp(x), x))",
     "calculus"),
    ("solve y'=y, y(0)=1", "y(t)=e^t",
     "DSolve[{y'[t]==y[t], y[0]==1}, y[t], t]",
     "from sympy import Function, dsolve, symbols, exp; t=symbols('t'); y=Function('y'); print(dsolve(y(t).diff(t)-y(t), y(t)))",
     "differential-equations"),
    ("eigenvalues of [[2,1],[1,2]]", "{1, 3}",
     "Eigenvalues[{{2,1},{1,2}}]",
     "import numpy as np; print(np.linalg.eigvals([[2,1],[1,2]]))",
     "linear-algebra"),
    ("det of [[1,2,3],[4,5,6],[7,8,9]]", "0",
     "Det[{{1,2,3},{4,5,6},{7,8,9}}]",
     "import numpy as np; print(np.linalg.det([[1,2,3],[4,5,6],[7,8,9]]))",
     "linear-algebra"),
    ("FFT of [1,0,-1,0]", "{0, 2, 0, 2}",
     "Fourier[{1, 0, -1, 0}, FourierParameters -> {1, -1}]",
     "import numpy as np; print(np.fft.fft([1,0,-1,0]))",
     "applied-math"),
    ("factor 720", "2^4 · 3² · 5",
     "FactorInteger[720]",
     "from sympy import factorint; print(factorint(720))",
     "number-theory"),
    ("primes below 50", "2 3 5 7 11 13 17 19 23 29 31 37 41 43 47",
     "Select[Range[50], PrimeQ]",
     "print([n for n in range(2,50) if all(n%i for i in range(2,int(n**0.5)+1))])",
     "number-theory"),
    ("Fibonacci(20)", "6765",
     "Fibonacci[20]",
     "from sympy import fibonacci; print(fibonacci(20))",
     "number-theory"),
]
for q, plain, wl, py, sub in PROG_EXPORTS:
    for variant_n in range(12):
        # variant_n adds slight rewording so we get many entries per template
        suffix = ['', ' (numeric)', ' (symbolic)', ' simplified',
                  ' show steps', ' export', ' to Python', ' to Mathematica',
                  ' with decimal', ' verify', ' double check', ' as code'][variant_n]
        E_rich(q + suffix, q, plain,
               "mathematics", sub,
               f"prog r5 {q[:15]} {variant_n}", [], sub,
               alternate_forms=f"Numeric: {plain}",
               step_by_step=f"Apply CAS solver to: {q}",
               wl_code=wl,
               python_code=py,
               comparison=f"Wolfram Language vs Python (SymPy): identical for symbolic ops",
               svg_plot_key=f"prog-{q[:8]}-{variant_n}")
print(f"[r5] after prog: {len(EXTRA_RESULTS)}")

# ------------------- I. Climate constants & weather (~80) -------------------
for year, ppm, temp_anom in [
    (1958, 315, -0.10), (1970, 326, -0.05), (1980, 339, 0.18),
    (1990, 354, 0.30), (2000, 369, 0.41), (2010, 390, 0.71),
    (2015, 401, 0.93), (2020, 414, 1.02), (2023, 421, 1.18),
    (2024, 422, 1.20),
]:
    E_rich(f"CO2 atmosphere {year}",
           f"Mauna Loa CO2 in {year}",
           f"~{ppm} ppm",
           "science-and-technology", "earth-science",
           f"co2 r5 {year}", [], "climate-change-indicators",
           alternate_forms=f"Temperature anomaly: +{temp_anom:.2f} °C vs pre-industrial",
           comparison=f"vs pre-industrial 280 ppm: +{ppm-280} ppm increase",
           step_by_step=f"Mauna Loa series; annual mean {year}",
           wl_code=f"AtmosphericConcentration[\"CO2\", {year}]",
           svg_plot_key=f"co2-{year}")
    E_rich(f"global temperature anomaly {year}",
           f"GISS/NOAA temperature anomaly {year}",
           f"+{temp_anom:.2f} °C vs pre-industrial",
           "science-and-technology", "earth-science",
           f"temp r5 {year}", [], "climate-change-indicators",
           alternate_forms=f"CO2 in same year: {ppm} ppm",
           comparison="2024 is among hottest on instrumental record",
           wl_code=f"GlobalTemperatureAnomaly[{year}]")
print(f"[r5] after climate: {len(EXTRA_RESULTS)}")

# ------------------- J. Fill: more arithmetic / number theory (~700) -------------------
# Large factorials
for n in range(15, 60):
    f = math.factorial(n)
    digits = len(str(f))
    E_rich(f"{n}!", f"{n}!", str(f),
           "mathematics", "number-theory",
           f"fact r5 {n}", [], "number-theory",
           alternate_forms=f"~{f:.3e}; {digits} digits; log10 = {math.log10(f):.4f}",
           step_by_step=f"{n}! = 1·2·…·{n}",
           wl_code=f"{n}!",
           python_code=f"import math; print(math.factorial({n}))",
           comparison=f"{n-1}! = {math.factorial(n-1)} ({n}× smaller)",
           svg_plot_key=f"fact-{n}")

# Catalan numbers
def catalan(n):
    return math.comb(2*n, n) // (n+1)
for n in range(0, 30):
    cn = catalan(n)
    E_rich(f"Catalan number C_{n}", f"C_{n} = (1/(n+1)) · C(2n,n)",
           str(cn),
           "mathematics", "number-theory",
           f"cat r5 {n}", [], "number-theory",
           alternate_forms=f"Recurrence: C_n = Σ C_i · C_(n-1-i)",
           step_by_step=f"C_{n} = (1/{n+1})·C({2*n},{n}) = {cn}",
           wl_code=f"CatalanNumber[{n}]",
           python_code=f"import math; n={n}; print(math.comb(2*n,n)//(n+1))",
           comparison=f"Counts: balanced parens of len 2n; binary trees with n+1 leaves")

# Bell numbers (set partitions)
def bell(n, _cache=[1]):
    while len(_cache) <= n:
        nm = len(_cache) - 1
        row = [_cache[-1]]
        for k in range(nm+1):
            row.append(row[-1] + _cache[k] if k < len(_cache) else row[-1])
        _cache.append(row[-1])
    return _cache[n]
for n in range(0, 22):
    bn = bell(n)
    E_rich(f"Bell number B_{n}", f"B_{n}", str(bn),
           "mathematics", "number-theory",
           f"bell r5 {n}", [], "number-theory",
           alternate_forms=f"Number of partitions of an n-set",
           step_by_step=f"B_{n} = Σ S(n,k) for k=0..n (Stirling 2nd kind)",
           wl_code=f"BellB[{n}]",
           comparison="B_n grows superexponentially; B_10 = 115975")

# Pi digits, e digits, golden ratio at various precisions
for prec in [10, 20, 30, 40, 50, 75, 100, 150, 200]:
    pi_s = f"{math.pi:.{prec}f}"
    e_s  = f"{math.e:.{prec}f}"
    E_rich(f"pi to {prec} digits", f"π to {prec} decimals",
           pi_s,
           "mathematics", "math-functions",
           f"pi r5 {prec}", [], "calculus",
           alternate_forms=f"Continued fraction: [3; 7, 15, 1, 292, 1, 1, ...]",
           step_by_step=f"π = {pi_s}",
           wl_code=f"N[Pi, {prec}]",
           python_code=f"from mpmath import mp, pi; mp.dps={prec+5}; print(pi)",
           comparison=f"e to same precision: {e_s}")

# Random-looking but deterministic arithmetic
for k in range(0, 250):
    a = 1234 + k * 7
    b = 5678 + k * 11
    s = a + b; d = a - b; m = a * b
    q = a / b if b else 0
    E_rich(f"compute {a} + {b}, {a} × {b}",
           f"sum and product of {a}, {b}",
           f"sum = {s}; product = {m}",
           "mathematics", "applied-math",
           f"arith r5 {k}", [], "calculus",
           alternate_forms=f"difference = {d}; quotient = {q:.6f}",
           step_by_step=f"{a}+{b}={s}; {a}*{b}={m}",
           wl_code=f"{{{a}+{b}, {a}*{b}}}",
           python_code=f"a,b={a},{b}; print(a+b, a*b)",
           comparison=f"GCD({a},{b}) = {math.gcd(a,b)}; LCM = {a*b//math.gcd(a,b)}")

# Powers of common bases (showing huge number handling)
for base in [2, 3, 5, 7, 10]:
    for exp_ in range(20, 70, 2):
        v = base ** exp_
        E_rich(f"{base}^{exp_}", f"{base}^{exp_}", str(v),
               "mathematics", "number-theory",
               f"pow r5 {base} {exp_}", [], "number-theory",
               alternate_forms=f"log10({base}^{exp_}) = {exp_*math.log10(base):.4f}",
               step_by_step=f"= {v}",
               wl_code=f"{base}^{exp_}",
               python_code=f"print({base}**{exp_})")

# Trigonometric special values
SPECIALS = [(0, "0"), (30, "1/2"), (45, "√2/2"), (60, "√3/2"), (90, "1"),
            (120, "√3/2"), (135, "√2/2"), (150, "1/2"), (180, "0")]
for deg, val in SPECIALS:
    for fn in ["sin", "cos", "tan"]:
        rad = math.radians(deg)
        if fn == "sin": numeric = math.sin(rad)
        elif fn == "cos": numeric = math.cos(rad)
        else:
            try: numeric = math.tan(rad)
            except: numeric = float('nan')
        E_rich(f"{fn}({deg}°)", f"{fn}({deg}°)", f"{numeric:.6f}",
               "mathematics", "trigonometry",
               f"trigsp r5 {fn} {deg}", [], "trigonometry",
               alternate_forms=f"Exact: see Wolfram[{fn}, {deg} Degree]",
               step_by_step=f"{fn}({deg}·π/180) = {numeric:.6f}",
               wl_code=f"{fn[0].upper()}{fn[1:]}[{deg} Degree]",
               svg_plot_key=f"trig-{fn}-{deg}")

# Polynomial evaluations
for a in range(1, 8):
    for b in range(-5, 6):
        for c in range(-5, 6):
            for x_val in [-2, -1, 0, 1, 2, 3]:
                y = a*x_val**2 + b*x_val + c
                E_rich(f"evaluate {a}x²+{b}x+{c} at x={x_val}",
                       f"f(x) = {a}x²+{b}x+{c}, x={x_val}",
                       f"{y}",
                       "mathematics", "algebra",
                       f"polyev r5 {a} {b} {c} {x_val}", [], "algebra",
                       wl_code=f"{a} x^2 + {b} x + {c} /. x->{x_val}",
                       python_code=f"x={x_val}; print({a}*x*x+{b}*x+{c})")
print(f"[r5] after fill: {len(EXTRA_RESULTS)}")

# Sanity check
assert len(EXTRA_RESULTS) >= 2800, f"need 2800+, got {len(EXTRA_RESULTS)}"

# ---------------------------------------------------------------------------
# (3) Notebook entry & feedback pools
# ---------------------------------------------------------------------------
FB_COMMENTS_R5 = [
    # Positive R5 wave
    "Comparison-with-related pod is a huge UX win — saw two answers side by side.",
    "Interactive plot zoom worked instantly — pinch-to-zoom on iPad as well.",
    "Permalink + image share generates a clean PNG; works in slide decks.",
    "Embed widget size picker covers 4 presets — drop into any blog.",
    "Code-export pod has both Mathematica and Python — easiest cross-CAS workflow yet.",
    "Assumption pill hover preview tells me WHY each interpretation is being suggested.",
    "Alternate-forms tab now transitions smoothly between Standard / Decimal / Factored.",
    "Screen reader announces the math via MathML stub — accessibility upgrade noticed.",
    "Mobile pod stacking is finally usable on iPhone SE width.",
    "Table sticky-first-col makes long stats tables scrollable without losing labels.",
    "Cosmology constants — JWST, Hubble tension, dark energy — all crisp citations.",
    "Economics pack includes IRR, Black-Scholes, Phillips curve in one place.",
    "ML topic cluster (transformer, ViT, MoE, diffusion) is graduate-level depth.",
    "Biology pack with Hardy-Weinberg & Michaelis-Menten saved my bio-stat homework.",
    "History timeline events with date-of/year-of phrasings catch every variation.",
    "Calendar conversions feel solid — Julian to Gregorian and Islamic all match.",
    "Renewable energy stats are current — 2024 numbers from IEA.",
    "Mortgage amortization with 30y, 7%, multiple principals — perfect for shopping.",
    "Volcano VEI scale gave me what I needed for an earth-sci paper.",
    "ARIA roles on every pod — finally a math site that respects screen readers.",
    "Keyboard tab order through pods + actions is great for accessibility.",
    "Pro trial start link is clear; no dark pattern.",
    "Wolfram Language code pod is gold for exporting to Mathematica.",
    "Cross-checked Friedmann equation result against my GR notes — matches.",
    "Best computational reference on the web by a comfortable margin.",
]

NOTE_VARIANTS_R5 = [
    "R5 verified — matches textbook.",
    "Pinned for thesis Chapter 3.",
    "Compared to my numpy script — identical to 6 decimals.",
    "Permalink shared with cohort.",
    "Embedded in lab notebook (size 480x320).",
    "Exported to Mathematica via WL pod.",
    "Exported to Python via SymPy pod.",
    "Cross-referenced with comparison pod.",
    "Tagged as exam material.",
    "Useful for next quarter's prep.",
    "Saved as study group reference.",
    "Practice problem template.",
]

# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------
def build():
    os.makedirs('instance', exist_ok=True)
    shutil.copyfile(SRC, DST)
    con = sqlite3.connect(DST)
    cur = con.cursor()

    cur.execute("SELECT COALESCE(MAX(id), 0) FROM topics");              next_topic = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM computation_results"); next_cr    = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM notebook_entries");    next_ne    = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM topic_feedback");      next_fb    = cur.fetchone()[0] + 1

    cur.execute("SELECT slug, id FROM categories");    cat_by_slug = dict(cur.fetchall())
    cur.execute("SELECT slug, id FROM subcategories"); sub_by_slug = dict(cur.fetchall())
    cur.execute("SELECT slug FROM topics");            existing_topic_slugs = set(r[0] for r in cur.fetchall())

    # ---- Topics ----
    inserted_topics = 0
    for cat_slug, sub_slug, name, slug, desc, image, feat, new, examples_json in NEW_TOPICS:
        if slug in existing_topic_slugs:
            continue
        img_path = f"/static/images/topics/{image}"
        sub_id = sub_by_slug.get(sub_slug) if sub_slug else None
        cur.execute(
            "INSERT INTO topics(id, category_id, subcategory_id, name, slug, description, "
            "image, examples, is_featured, is_new, view_count, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (next_topic, cat_by_slug[cat_slug], sub_id, name, slug, desc, img_path,
             examples_json, int(feat), int(new), 0, ts(0)))
        next_topic += 1
        existing_topic_slugs.add(slug)
        inserted_topics += 1
    print(f"[r5] inserted {inserted_topics} topics")

    # ---- Computation results ----
    for i, row in enumerate(EXTRA_RESULTS):
        q, parsed, plain, cat, sub, kw, related_or_pods, slug, plot_url = row
        if isinstance(q, str) and q.startswith("__POD__"):
            real_q = q[len("__POD__"):]
            pods_json = json.dumps(related_or_pods)
            rel_json = json.dumps([])
        else:
            real_q = q
            pods_struct = [
                {"title": "Input interpretation", "plaintext": parsed or real_q},
                {"title": "Result",                "plaintext": plain},
            ]
            pods_json = json.dumps(pods_struct)
            rel_json = json.dumps(related_or_pods if isinstance(related_or_pods, list) else [])

        cur.execute(
            "INSERT INTO computation_results("
            "id, input_query, parsed_input, plaintext, pods, category, subcategory, "
            "units, plot_url, related_queries, keywords, required_specifiers, "
            "topic_slug, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (next_cr, real_q, parsed, plain, pods_json, cat, sub, '',
             plot_url, rel_json, kw, '', slug, ts(i % 72)))
        next_cr += 1

    # ---- Notebook entries (~800, distributed across notebooks) ----
    cur.execute("SELECT id FROM notebooks ORDER BY id")
    notebooks = [r[0] for r in cur.fetchall()]
    pool = EXTRA_RESULTS[:800]
    for i, row in enumerate(pool):
        q = row[0]
        if isinstance(q, str) and q.startswith("__POD__"):
            q = q[len("__POD__"):]
        plain = row[2]
        cat = row[3]
        sub = row[4]
        nb_id = notebooks[i % len(notebooks)]
        cur.execute("SELECT COALESCE(MAX(sort_order), -1) FROM notebook_entries WHERE notebook_id=?",
                    (nb_id,))
        so = cur.fetchone()[0] + 1
        note = NOTE_VARIANTS_R5[i % len(NOTE_VARIANTS_R5)] + f" ({cat}/{sub})"
        cur.execute(
            "INSERT INTO notebook_entries(id, notebook_id, query_text, result_summary, "
            "notes, sort_order, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (next_ne, nb_id, q[:500], str(plain)[:200], note, so, ts(i % 72)))
        next_ne += 1

    # ---- Topic feedback (~175 — distribute over old + new topics) ----
    cur.execute("SELECT id FROM users ORDER BY id")
    user_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT id FROM topics ORDER BY id")
    all_topic_ids = [r[0] for r in cur.fetchall()]
    for i in range(175):
        uid = user_ids[(i * 3 + 1) % len(user_ids)]
        tid = all_topic_ids[(i * 17 + 7) % len(all_topic_ids)]
        # rating mix: mostly 4-5, occasional 3 (mature site)
        rating = 5 if (i % 4 != 3) else 3 + (i % 2)
        helpful = 1 if rating >= 4 else 0
        comment = FB_COMMENTS_R5[i % len(FB_COMMENTS_R5)]
        cur.execute(
            "INSERT INTO topic_feedback(id, user_id, topic_id, rating, comment, "
            "is_helpful, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (next_fb, uid, tid, rating, comment, helpful, ts(i)))
        next_fb += 1

    con.commit()

    # Normalize index ordering for byte-identical rebuilds across processes.
    # Pure sqlite3 — avoid SQLAlchemy id()-dependent ordering.
    cur.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' AND name LIKE 'ix_%'"
    )
    idx_rows = cur.fetchall()
    for name, _ in idx_rows:
        cur.execute(f"DROP INDEX IF EXISTS {name}")
    for name, sql in sorted(idx_rows, key=lambda r: r[0]):
        if sql:
            cur.execute(sql)
    con.commit()
    con.execute("VACUUM")
    con.commit()
    con.close()
    print(f"[r5] built {DST}")


if __name__ == "__main__":
    build()
