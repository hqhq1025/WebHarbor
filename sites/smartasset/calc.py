"""SmartAsset — deterministic financial calculators.

Each calculator is a pure function that takes a dict of string inputs
and returns a result dict. Server-side math only (no JS). Used by
:mod:`app.calculator` for both HTML form submission and the JSON API.

Federal tax brackets used here follow IRS 2025-2026 published values
(rounded to whole dollars). State rates and ranks are stored on the
``State`` model and read at runtime.
"""
from __future__ import annotations

import math
import re
from typing import Any


class CalcError(Exception):
    """Raised when calculator inputs are missing / malformed."""


def _num(s, default=0.0, name=""):
    """Parse a money/percent/number string -> float. Strips $ , and %."""
    if s is None or s == "":
        return default
    if isinstance(s, (int, float)):
        return float(s)
    s = re.sub(r"[\$,%\s]", "", str(s))
    try:
        return float(s)
    except ValueError:
        raise CalcError(f"Invalid number for {name or 'input'}: {s!r}")


def _int(s, default=0, name=""):
    return int(round(_num(s, default, name)))


def _round_money(x):
    return round(float(x) + 1e-9, 2)


# ─── Federal tax brackets — 2025 ────────────────────────────────────

FED_BRACKETS_2025 = {
    "single": [
        (11_925, 0.10),
        (48_475, 0.12),
        (103_350, 0.22),
        (197_300, 0.24),
        (250_525, 0.32),
        (626_350, 0.35),
        (float("inf"), 0.37),
    ],
    "married": [
        (23_850, 0.10),
        (96_950, 0.12),
        (206_700, 0.22),
        (394_600, 0.24),
        (501_050, 0.32),
        (751_600, 0.35),
        (float("inf"), 0.37),
    ],
    "head": [
        (17_000, 0.10),
        (64_850, 0.12),
        (103_350, 0.22),
        (197_300, 0.24),
        (250_500, 0.32),
        (626_350, 0.35),
        (float("inf"), 0.37),
    ],
}

STANDARD_DEDUCTION_2025 = {
    "single": 15_000,
    "married": 30_000,
    "head": 22_500,
}

FICA_SS_RATE = 0.062
FICA_MED_RATE = 0.0145
FICA_SS_WAGE_BASE_2025 = 176_100
ADDITIONAL_MED_THRESHOLD = {"single": 200_000, "married": 250_000, "head": 200_000}
ADDITIONAL_MED_RATE = 0.009


def apply_brackets(taxable, brackets):
    tax = 0.0
    last = 0.0
    for top, rate in brackets:
        slab = max(0.0, min(taxable, top) - last)
        tax += slab * rate
        if taxable <= top:
            break
        last = top
    return tax


def marginal_rate(taxable, brackets):
    for top, rate in brackets:
        if taxable <= top:
            return rate
    return brackets[-1][1]


# ─── Per-state effective income tax rates (top bracket, deterministic) ──

STATE_TAX_RATES = {
    # state_abbr: (type, flat_rate_or_None, top_bracket_rate)
    "AL": ("bracket", None, 5.0), "AK": ("none", None, 0.0),
    "AZ": ("flat", 2.5, 2.5),   "AR": ("bracket", None, 4.4),
    "CA": ("bracket", None, 13.3), "CO": ("flat", 4.4, 4.4),
    "CT": ("bracket", None, 6.99), "DE": ("bracket", None, 6.6),
    "FL": ("none", None, 0.0),   "GA": ("flat", 5.39, 5.39),
    "HI": ("bracket", None, 11.0), "ID": ("flat", 5.695, 5.695),
    "IL": ("flat", 4.95, 4.95),  "IN": ("flat", 3.0, 3.0),
    "IA": ("flat", 3.8, 3.8),    "KS": ("bracket", None, 5.58),
    "KY": ("flat", 4.0, 4.0),    "LA": ("flat", 3.0, 3.0),
    "ME": ("bracket", None, 7.15), "MD": ("bracket", None, 5.75),
    "MA": ("flat", 5.0, 5.0),    "MI": ("flat", 4.25, 4.25),
    "MN": ("bracket", None, 9.85), "MS": ("flat", 4.4, 4.4),
    "MO": ("bracket", None, 4.7), "MT": ("flat", 5.9, 5.9),
    "NE": ("bracket", None, 5.2), "NV": ("none", None, 0.0),
    "NH": ("none", None, 0.0),   "NJ": ("bracket", None, 10.75),
    "NM": ("bracket", None, 5.9), "NY": ("bracket", None, 10.9),
    "NC": ("flat", 4.25, 4.25),  "ND": ("bracket", None, 2.5),
    "OH": ("bracket", None, 3.5), "OK": ("bracket", None, 4.75),
    "OR": ("bracket", None, 9.9), "PA": ("flat", 3.07, 3.07),
    "RI": ("bracket", None, 5.99), "SC": ("bracket", None, 6.2),
    "SD": ("none", None, 0.0),   "TN": ("none", None, 0.0),
    "TX": ("none", None, 0.0),   "UT": ("flat", 4.55, 4.55),
    "VT": ("bracket", None, 8.75), "VA": ("bracket", None, 5.75),
    "WA": ("none", None, 0.0),   "WV": ("bracket", None, 4.82),
    "WI": ("bracket", None, 7.65), "WY": ("none", None, 0.0),
    "DC": ("bracket", None, 10.75),
}


def state_tax(state_abbr, taxable):
    """Deterministic state income tax estimate.

    For bracketed states we use a simplified single bracket curve that
    starts at half the top rate up to ~$30k and walks linearly to the top
    rate by ~$1M of taxable income — enough to give plausible numbers
    without per-state bracket tables. Pure function -> deterministic.
    """
    info = STATE_TAX_RATES.get((state_abbr or "").upper(),
                                 ("flat", 4.0, 4.0))
    kind, flat, top = info
    if kind == "none":
        return 0.0
    if kind == "flat" and flat is not None:
        return max(0.0, taxable) * flat / 100.0
    # bracket: piecewise linear from top/3 to top across $0..$500k
    if taxable <= 0:
        return 0.0
    bottom = top / 3.0
    if taxable <= 30_000:
        rate = bottom
    elif taxable >= 500_000:
        rate = top
    else:
        frac = (taxable - 30_000) / (500_000 - 30_000)
        rate = bottom + (top - bottom) * frac
    return taxable * rate / 100.0


# ─── 1. Mortgage ────────────────────────────────────────────────────

def calc_mortgage(inputs):
    price = _num(inputs.get("price"), name="Home price")
    down = _num(inputs.get("down"), name="Down payment")
    rate = _num(inputs.get("rate"), 7.0, name="Interest rate")
    term = max(1, _int(inputs.get("term", 30), 30, name="Term"))
    prop_tax_pct = _num(inputs.get("prop_tax_pct", 1.1), 1.1)
    ins_annual = _num(inputs.get("insurance", 1500), 1500)
    hoa = _num(inputs.get("hoa", 0), 0)
    if price <= 0:
        raise CalcError("Home price must be positive.")
    if down > price:
        raise CalcError("Down payment cannot exceed home price.")
    principal = price - down
    n = term * 12
    r = (rate / 100.0) / 12.0
    pi = principal * r / (1 - (1 + r) ** (-n)) if r > 0 else principal / n
    down_pct = (down / price) * 100 if price else 0
    pmi_monthly = principal * 0.0075 / 12.0 if down_pct < 20 else 0.0
    prop_tax_monthly = price * prop_tax_pct / 100.0 / 12.0
    ins_monthly = ins_annual / 12.0
    total = pi + pmi_monthly + prop_tax_monthly + ins_monthly + hoa
    total_interest = pi * n - principal
    # 12-row by-year amortization snapshot
    bal = principal
    schedule = []
    for year in range(1, term + 1):
        year_interest = 0.0
        year_principal = 0.0
        for _ in range(12):
            i = bal * r
            p = pi - i
            bal -= p
            year_interest += i
            year_principal += p
        schedule.append({
            "year": year,
            "principal": _round_money(year_principal),
            "interest": _round_money(year_interest),
            "balance": _round_money(max(0, bal)),
        })
    return {
        "headline": f"${pi:,.0f}/mo principal & interest "
                    f"(${total:,.0f}/mo total)",
        "monthly_pi": _round_money(pi),
        "monthly_total": _round_money(total),
        "pmi_monthly": _round_money(pmi_monthly),
        "prop_tax_monthly": _round_money(prop_tax_monthly),
        "insurance_monthly": _round_money(ins_monthly),
        "hoa_monthly": _round_money(hoa),
        "loan_amount": _round_money(principal),
        "down_pct": _round_money(down_pct),
        "total_interest": _round_money(total_interest),
        "total_paid": _round_money(pi * n),
        "term_months": n,
        "schedule": schedule,
        "needs_pmi": down_pct < 20,
    }


# ─── 2. Affordability ───────────────────────────────────────────────

def calc_affordability(inputs):
    income = _num(inputs.get("income"), name="Annual income")
    monthly_debt = _num(inputs.get("monthly_debt", 0), 0)
    down = _num(inputs.get("down", 60_000), 60_000)
    rate = _num(inputs.get("rate", 7.0), 7.0)
    term = max(1, _int(inputs.get("term", 30), 30))
    dti = _num(inputs.get("dti", 36), 36)  # max %
    if income <= 0:
        raise CalcError("Annual income must be positive.")
    max_monthly_housing = income * dti / 100.0 / 12.0 - monthly_debt
    if max_monthly_housing <= 0:
        raise CalcError("Your existing debt already exceeds the DTI ceiling.")
    # leave 20% buffer for tax+ins+hoa
    pi_budget = max_monthly_housing * 0.80
    n = term * 12
    r = (rate / 100.0) / 12.0
    if r > 0:
        max_principal = pi_budget * (1 - (1 + r) ** (-n)) / r
    else:
        max_principal = pi_budget * n
    max_price = max_principal + down
    return {
        "headline": f"You can afford about ${max_price:,.0f}",
        "max_price": _round_money(max_price),
        "max_loan": _round_money(max_principal),
        "max_monthly_housing": _round_money(max_monthly_housing),
        "pi_budget": _round_money(pi_budget),
        "dti_used": dti,
    }


# ─── 3. Refinance ───────────────────────────────────────────────────

def calc_refinance(inputs):
    balance = _num(inputs.get("balance"), name="Current balance")
    current_rate = _num(inputs.get("current_rate"), name="Current rate")
    new_rate = _num(inputs.get("new_rate"), name="New rate")
    term = max(1, _int(inputs.get("term", 30), 30))
    closing = _num(inputs.get("closing", 5000), 5000)
    if balance <= 0:
        raise CalcError("Loan balance must be positive.")
    n = term * 12

    def pmt(p, ann_rate, months):
        r = (ann_rate / 100.0) / 12.0
        return p * r / (1 - (1 + r) ** (-months)) if r > 0 else p / months

    old_pmt = pmt(balance, current_rate, n)
    new_pmt = pmt(balance, new_rate, n)
    monthly_savings = old_pmt - new_pmt
    breakeven_months = closing / monthly_savings if monthly_savings > 0 else None
    return {
        "headline": (f"Save ${monthly_savings:,.0f}/mo, "
                     f"break-even {(breakeven_months or 0):.1f} months"
                     if breakeven_months else
                     "New rate would not lower your payment."),
        "old_payment": _round_money(old_pmt),
        "new_payment": _round_money(new_pmt),
        "monthly_savings": _round_money(monthly_savings),
        "breakeven_months": (round(breakeven_months, 1)
                              if breakeven_months else None),
        "lifetime_savings": _round_money(monthly_savings * n - closing),
        "closing_costs": _round_money(closing),
    }


# ─── 4. Closing costs ───────────────────────────────────────────────

def calc_closing(inputs):
    price = _num(inputs.get("price"), name="Home price")
    down = _num(inputs.get("down", 0), 0)
    state = (inputs.get("state") or "NY").upper()[:2]
    if price <= 0:
        raise CalcError("Home price must be positive.")
    loan = price - down
    # Typical breakdown — rates are illustrative but deterministic per state.
    state_factor = {"CA": 1.25, "NY": 1.5, "TX": 1.0, "FL": 1.1,
                    "IL": 1.05, "MA": 1.2, "WA": 1.1}.get(state, 1.0)
    origination = loan * 0.01
    appraisal = 600
    title_insurance = price * 0.0035 * state_factor
    title_search = 200
    survey = 450
    transfer_tax = price * 0.004 * state_factor
    recording = 125
    underwriting = 750
    credit_report = 50
    prepaid_interest = loan * 0.005 * (15 / 30)
    escrow_setup = price * 0.005
    items = [
        ("Loan origination", origination),
        ("Appraisal", appraisal),
        ("Title insurance", title_insurance),
        ("Title search", title_search),
        ("Survey", survey),
        ("Transfer tax", transfer_tax),
        ("Recording fees", recording),
        ("Underwriting", underwriting),
        ("Credit report", credit_report),
        ("Prepaid interest", prepaid_interest),
        ("Escrow setup", escrow_setup),
    ]
    total = sum(v for _, v in items)
    return {
        "headline": f"Estimated closing costs: ${total:,.0f} ({total/price*100:.1f}% of price)",
        "total": _round_money(total),
        "pct_of_price": _round_money(total / price * 100),
        "items": [{"name": n, "amount": _round_money(v)} for n, v in items],
        "state": state,
    }


# ─── 5. Property tax ────────────────────────────────────────────────

def calc_property_tax(inputs):
    value = _num(inputs.get("value"), name="Home value")
    state = (inputs.get("state") or "NY").upper()[:2]
    # Effective property tax rates (BLS/state assessor 2024 averages)
    rates = {
        "AL": 0.40, "AK": 1.04, "AZ": 0.62, "AR": 0.61, "CA": 0.75,
        "CO": 0.51, "CT": 1.79, "DE": 0.57, "FL": 0.86, "GA": 0.92,
        "HI": 0.32, "ID": 0.67, "IL": 2.08, "IN": 0.84, "IA": 1.50,
        "KS": 1.34, "KY": 0.83, "LA": 0.56, "ME": 1.24, "MD": 1.05,
        "MA": 1.14, "MI": 1.38, "MN": 1.11, "MS": 0.75, "MO": 0.98,
        "MT": 0.74, "NE": 1.63, "NV": 0.55, "NH": 1.93, "NJ": 2.23,
        "NM": 0.67, "NY": 1.40, "NC": 0.80, "ND": 0.98, "OH": 1.53,
        "OK": 0.89, "OR": 0.93, "PA": 1.49, "RI": 1.40, "SC": 0.57,
        "SD": 1.17, "TN": 0.67, "TX": 1.68, "UT": 0.57, "VT": 1.83,
        "VA": 0.82, "WA": 0.87, "WV": 0.57, "WI": 1.61, "WY": 0.58,
        "DC": 0.57,
    }
    rate = rates.get(state, 1.10)
    annual = value * rate / 100.0
    monthly = annual / 12.0
    return {
        "headline": f"${annual:,.0f}/yr (${monthly:,.0f}/mo) at {rate:.2f}%",
        "annual_tax": _round_money(annual),
        "monthly_tax": _round_money(monthly),
        "rate_pct": rate,
        "state": state,
        "home_value": _round_money(value),
    }


# ─── 6. Federal income tax ──────────────────────────────────────────

def calc_income_tax(inputs):
    income = _num(inputs.get("income"), name="Gross income")
    filing = (inputs.get("filing") or "single").lower()
    if filing not in FED_BRACKETS_2025:
        filing = "single"
    pretax_401k = _num(inputs.get("pretax_401k", 0), 0)
    itemized = _num(inputs.get("itemized", 0), 0)
    deduction = max(itemized, STANDARD_DEDUCTION_2025[filing])
    agi = max(0, income - pretax_401k)
    taxable = max(0, agi - deduction)
    fed_tax = apply_brackets(taxable, FED_BRACKETS_2025[filing])
    eff_rate = (fed_tax / income * 100) if income else 0
    marg = marginal_rate(taxable, FED_BRACKETS_2025[filing]) * 100
    return {
        "headline": f"Federal tax: ${fed_tax:,.0f} (effective {eff_rate:.2f}%)",
        "federal_tax": _round_money(fed_tax),
        "taxable_income": _round_money(taxable),
        "agi": _round_money(agi),
        "deduction_used": _round_money(deduction),
        "effective_rate": _round_money(eff_rate),
        "marginal_rate": _round_money(marg),
        "filing": filing,
    }


# ─── 7. State income tax ────────────────────────────────────────────

def calc_state_tax(inputs):
    income = _num(inputs.get("income"), name="Income")
    state = (inputs.get("state") or "CA").upper()[:2]
    filing = (inputs.get("filing") or "single").lower()
    deduction = STANDARD_DEDUCTION_2025.get(filing, 15_000) * 0.5  # rough state proxy
    taxable = max(0, income - deduction)
    tax = state_tax(state, taxable)
    eff = (tax / income * 100) if income else 0
    info = STATE_TAX_RATES.get(state, ("flat", 4.0, 4.0))
    return {
        "headline": f"{state} state tax: ${tax:,.0f} (effective {eff:.2f}%)",
        "state_tax": _round_money(tax),
        "taxable_income": _round_money(taxable),
        "effective_rate": _round_money(eff),
        "rate_top": info[2],
        "tax_type": info[0],
        "state": state,
    }


# ─── 8. Paycheck ────────────────────────────────────────────────────

def calc_paycheck(inputs):
    salary = _num(inputs.get("salary"), name="Annual salary")
    state = (inputs.get("state") or "CA").upper()[:2]
    filing = (inputs.get("filing") or "single").lower()
    if filing not in FED_BRACKETS_2025:
        filing = "single"
    pay_freq = (inputs.get("pay_freq") or "biweekly").lower()
    pretax_401k_pct = _num(inputs.get("pretax_401k_pct", 5), 5)
    pretax_health = _num(inputs.get("pretax_health", 0), 0)
    freq_map = {"weekly": 52, "biweekly": 26, "semimonthly": 24, "monthly": 12}
    periods = freq_map.get(pay_freq, 26)
    if salary <= 0:
        raise CalcError("Annual salary must be positive.")
    pretax_401k = salary * pretax_401k_pct / 100.0
    agi = max(0, salary - pretax_401k - pretax_health)
    taxable = max(0, agi - STANDARD_DEDUCTION_2025[filing])
    fed = apply_brackets(taxable, FED_BRACKETS_2025[filing])
    state_t = state_tax(state, taxable)
    ss = min(salary - pretax_health, FICA_SS_WAGE_BASE_2025) * FICA_SS_RATE
    med = (salary - pretax_health) * FICA_MED_RATE
    add_med_thr = ADDITIONAL_MED_THRESHOLD.get(filing, 200_000)
    if salary - pretax_health > add_med_thr:
        med += (salary - pretax_health - add_med_thr) * ADDITIONAL_MED_RATE
    annual_net = salary - pretax_401k - pretax_health - fed - state_t - ss - med
    per_period_gross = salary / periods
    per_period_net = annual_net / periods
    return {
        "headline": f"${per_period_net:,.0f} per {pay_freq} paycheck "
                    f"(${annual_net:,.0f}/yr take-home)",
        "annual_gross": _round_money(salary),
        "annual_net": _round_money(annual_net),
        "federal_tax": _round_money(fed),
        "state_tax": _round_money(state_t),
        "social_security": _round_money(ss),
        "medicare": _round_money(med),
        "pretax_401k": _round_money(pretax_401k),
        "pretax_health": _round_money(pretax_health),
        "per_period_gross": _round_money(per_period_gross),
        "per_period_net": _round_money(per_period_net),
        "pay_freq": pay_freq,
        "periods_per_year": periods,
        "state": state,
        "filing": filing,
    }


# ─── 9. Capital gains ───────────────────────────────────────────────

def calc_capital_gains(inputs):
    cost = _num(inputs.get("cost_basis"), name="Cost basis")
    proceeds = _num(inputs.get("proceeds"), name="Sale price")
    held_years = _num(inputs.get("holding_years", 2), 2)
    income = _num(inputs.get("income", 80_000), 80_000)
    filing = (inputs.get("filing") or "single").lower()
    gain = proceeds - cost
    if gain <= 0:
        return {"headline": "No taxable gain (loss or break-even).",
                 "gain": _round_money(gain),
                 "fed_tax": 0, "is_long_term": held_years >= 1}
    long_term = held_years >= 1
    if long_term:
        # 2025 LTCG brackets (single approx)
        thresholds = {
            "single": [(48_350, 0.0), (533_400, 0.15), (float("inf"), 0.20)],
            "married": [(96_700, 0.0), (600_050, 0.15), (float("inf"), 0.20)],
            "head": [(64_750, 0.0), (566_700, 0.15), (float("inf"), 0.20)],
        }[filing if filing in ("single", "married", "head") else "single"]
        bracket = thresholds
        # treat gain stacked on top of ordinary income
        rate = 0.0
        for top, r in bracket:
            if income + gain <= top:
                rate = r
                break
        else:
            rate = bracket[-1][1]
        # account for NIIT
        niit = 0.0
        niit_thr = 200_000 if filing == "single" else 250_000
        if income + gain > niit_thr:
            niit = gain * 0.038
        fed = gain * rate + niit
        return {
            "headline": (f"Long-term gain ${gain:,.0f} taxed at "
                          f"{rate*100:.0f}% → ${fed:,.0f}"),
            "gain": _round_money(gain),
            "fed_tax": _round_money(fed),
            "long_term_rate": rate * 100,
            "niit": _round_money(niit),
            "is_long_term": True,
            "net_proceeds": _round_money(proceeds - cost - fed),
        }
    # short term — ordinary income brackets
    ord_tax = apply_brackets(income + gain,
                              FED_BRACKETS_2025[filing if filing in FED_BRACKETS_2025 else "single"])
    base_tax = apply_brackets(income,
                               FED_BRACKETS_2025[filing if filing in FED_BRACKETS_2025 else "single"])
    fed = ord_tax - base_tax
    return {
        "headline": f"Short-term gain ${gain:,.0f} taxed as ordinary income → ${fed:,.0f}",
        "gain": _round_money(gain),
        "fed_tax": _round_money(fed),
        "is_long_term": False,
        "net_proceeds": _round_money(proceeds - cost - fed),
    }


# ─── 10. Retirement ─────────────────────────────────────────────────

def calc_retirement(inputs):
    current_age = _int(inputs.get("current_age", 35), 35)
    retire_age = _int(inputs.get("retire_age", 67), 67)
    life_age = _int(inputs.get("life_age", 95), 95)
    income = _num(inputs.get("income", 80_000), 80_000)
    current_savings = _num(inputs.get("current_savings", 50_000), 50_000)
    monthly_contrib = _num(inputs.get("monthly_contrib", 1000), 1000)
    growth = _num(inputs.get("growth", 7.0), 7.0)
    inflation = _num(inputs.get("inflation", 2.5), 2.5)
    income_replacement = _num(inputs.get("income_replacement", 80), 80)
    soc_sec_monthly = _num(inputs.get("soc_sec_monthly", 2200), 2200)
    if retire_age <= current_age:
        raise CalcError("Retirement age must be greater than current age.")
    years_save = retire_age - current_age
    years_retired = max(1, life_age - retire_age)
    r = growth / 100.0
    fv_lump = current_savings * (1 + r) ** years_save
    fv_contrib = (monthly_contrib * 12) * (((1 + r) ** years_save - 1) / r) if r else (monthly_contrib * 12 * years_save)
    nest_egg = fv_lump + fv_contrib
    annual_need = income * income_replacement / 100.0
    needed_total = annual_need * years_retired
    soc_sec_yr = soc_sec_monthly * 12 * years_retired
    shortfall = needed_total - nest_egg - soc_sec_yr
    safe_withdraw = nest_egg * 0.04
    on_track = shortfall <= 0
    return {
        "headline": (f"Projected nest egg ${nest_egg:,.0f}; "
                      + ("on track" if on_track else f"shortfall ${shortfall:,.0f}")),
        "nest_egg": _round_money(nest_egg),
        "fv_lump_sum": _round_money(fv_lump),
        "fv_contributions": _round_money(fv_contrib),
        "years_until_retire": years_save,
        "years_in_retirement": years_retired,
        "annual_need": _round_money(annual_need),
        "needed_total": _round_money(needed_total),
        "soc_sec_total": _round_money(soc_sec_yr),
        "shortfall": _round_money(max(0, shortfall)),
        "safe_withdrawal_annual": _round_money(safe_withdraw),
        "on_track": on_track,
        "inflation_pct": inflation,
    }


# ─── 11. 401(k) ─────────────────────────────────────────────────────

def calc_401k(inputs):
    current_age = _int(inputs.get("current_age", 30), 30)
    retire_age = _int(inputs.get("retire_age", 67), 67)
    salary = _num(inputs.get("salary", 70_000), 70_000)
    contrib_pct = _num(inputs.get("contrib_pct", 6), 6)
    employer_match_pct = _num(inputs.get("employer_match_pct", 50), 50)
    employer_match_cap = _num(inputs.get("employer_match_cap", 6), 6)
    current_balance = _num(inputs.get("current_balance", 25_000), 25_000)
    growth = _num(inputs.get("growth", 7.0), 7.0)
    salary_growth = _num(inputs.get("salary_growth", 2.5), 2.5)
    if retire_age <= current_age:
        raise CalcError("Retirement age must be greater than current age.")
    years = retire_age - current_age
    r = growth / 100.0
    sg = salary_growth / 100.0
    balance = current_balance
    total_emp = 0.0
    total_match = 0.0
    schedule = []
    sal = salary
    for y in range(1, years + 1):
        emp_contrib = sal * contrib_pct / 100.0
        match = sal * min(contrib_pct, employer_match_cap) / 100.0 * employer_match_pct / 100.0
        balance = balance * (1 + r) + emp_contrib + match
        total_emp += emp_contrib
        total_match += match
        schedule.append({
            "year": y,
            "age": current_age + y,
            "salary": _round_money(sal),
            "contrib": _round_money(emp_contrib),
            "match": _round_money(match),
            "balance": _round_money(balance),
        })
        sal *= (1 + sg)
    return {
        "headline": f"401(k) balance at retirement: ${balance:,.0f}",
        "final_balance": _round_money(balance),
        "total_employee": _round_money(total_emp),
        "total_match": _round_money(total_match),
        "annual_retirement_income": _round_money(balance * 0.04),
        "years": years,
        "schedule": schedule,
    }


# ─── 12. IRA (Roth vs Traditional) ──────────────────────────────────

def calc_ira(inputs):
    current_age = _int(inputs.get("current_age", 30), 30)
    retire_age = _int(inputs.get("retire_age", 65), 65)
    annual_contrib = _num(inputs.get("annual_contrib", 7000), 7000)
    growth = _num(inputs.get("growth", 7.0), 7.0)
    current_balance = _num(inputs.get("current_balance", 0), 0)
    marginal_now = _num(inputs.get("marginal_now", 22), 22)
    marginal_retire = _num(inputs.get("marginal_retire", 22), 22)
    if retire_age <= current_age:
        raise CalcError("Retirement age must be greater than current age.")
    years = retire_age - current_age
    r = growth / 100.0
    fv_lump = current_balance * (1 + r) ** years
    fv_contrib = (annual_contrib * (((1 + r) ** years - 1) / r)
                   if r else annual_contrib * years)
    fv_total = fv_lump + fv_contrib
    # Traditional: tax-deductible now, taxed at withdrawal
    trad_after_tax = fv_total * (1 - marginal_retire / 100.0)
    trad_tax_savings_now = annual_contrib * marginal_now / 100.0 * years
    # Roth: contributions after tax; growth tax-free
    roth_after_tax = fv_total  # no tax at withdrawal
    return {
        "headline": (f"Roth: ${roth_after_tax:,.0f}, Traditional after-tax: "
                      f"${trad_after_tax:,.0f}"),
        "fv_total": _round_money(fv_total),
        "traditional_after_tax": _round_money(trad_after_tax),
        "traditional_tax_savings_now": _round_money(trad_tax_savings_now),
        "roth_after_tax": _round_money(roth_after_tax),
        "roth_better_by": _round_money(roth_after_tax - trad_after_tax),
        "years": years,
        "marginal_now": marginal_now,
        "marginal_retire": marginal_retire,
    }


# ─── 13. Savings (compound interest) ────────────────────────────────

def calc_savings(inputs):
    initial = _num(inputs.get("initial", 5000), 5000)
    monthly = _num(inputs.get("monthly_deposit", 200), 200)
    years = max(1, _int(inputs.get("years", 10), 10))
    apy = _num(inputs.get("apy", 4.0), 4.0)
    compound = (inputs.get("compound") or "monthly").lower()
    n_map = {"daily": 365, "monthly": 12, "quarterly": 4, "annually": 1}
    n = n_map.get(compound, 12)
    r = apy / 100.0
    months = years * 12
    # FV of initial
    fv_initial = initial * (1 + r / n) ** (n * years)
    # FV of monthly contributions assuming monthly compounding for simplicity
    rm = r / 12.0
    fv_contrib = (monthly * (((1 + rm) ** months - 1) / rm)
                   if rm else monthly * months)
    fv = fv_initial + fv_contrib
    deposits = initial + monthly * months
    interest_earned = fv - deposits
    return {
        "headline": f"Final balance: ${fv:,.0f} (${interest_earned:,.0f} interest)",
        "final_balance": _round_money(fv),
        "total_deposits": _round_money(deposits),
        "interest_earned": _round_money(interest_earned),
        "fv_initial": _round_money(fv_initial),
        "fv_contributions": _round_money(fv_contrib),
        "years": years,
        "apy": apy,
    }


# ─── 14. CD ─────────────────────────────────────────────────────────

def calc_cd(inputs):
    principal = _num(inputs.get("principal"), name="Deposit")
    apy = _num(inputs.get("apy"), name="APY")
    term_months = max(1, _int(inputs.get("term_months", 12), 12))
    years = term_months / 12.0
    fv = principal * (1 + apy / 100.0) ** years
    interest = fv - principal
    return {
        "headline": f"At maturity: ${fv:,.0f} ({interest:,.0f} interest)",
        "maturity_value": _round_money(fv),
        "interest_earned": _round_money(interest),
        "term_months": term_months,
        "apy": apy,
    }


# ─── 15. Investment growth ──────────────────────────────────────────

def calc_investment(inputs):
    initial = _num(inputs.get("initial", 10_000), 10_000)
    monthly = _num(inputs.get("monthly", 500), 500)
    years = max(1, _int(inputs.get("years", 20), 20))
    rate = _num(inputs.get("rate", 7.0), 7.0)
    r = rate / 100.0
    months = years * 12
    rm = r / 12.0
    fv_initial = initial * (1 + rm) ** months
    fv_contrib = (monthly * (((1 + rm) ** months - 1) / rm)
                   if rm else monthly * months)
    fv = fv_initial + fv_contrib
    deposits = initial + monthly * months
    growth = fv - deposits
    by_year = []
    bal = initial
    for y in range(1, years + 1):
        for _ in range(12):
            bal = bal * (1 + rm) + monthly
        by_year.append({"year": y, "balance": _round_money(bal)})
    return {
        "headline": f"Future value: ${fv:,.0f}",
        "future_value": _round_money(fv),
        "deposits": _round_money(deposits),
        "growth": _round_money(growth),
        "by_year": by_year,
    }


# ─── 16. Cost of living ─────────────────────────────────────────────

# Cost of living index, 100 = U.S. average. Sourced as deterministic
# constants — adjust freely; documented in code.
COL_CITIES = {
    "new-york-ny": ("New York, NY", 187.2, "NY"),
    "san-francisco-ca": ("San Francisco, CA", 178.6, "CA"),
    "los-angeles-ca": ("Los Angeles, CA", 152.4, "CA"),
    "seattle-wa": ("Seattle, WA", 154.0, "WA"),
    "boston-ma": ("Boston, MA", 149.3, "MA"),
    "washington-dc": ("Washington, DC", 152.1, "DC"),
    "chicago-il": ("Chicago, IL", 106.9, "IL"),
    "miami-fl": ("Miami, FL", 121.4, "FL"),
    "denver-co": ("Denver, CO", 118.5, "CO"),
    "austin-tx": ("Austin, TX", 119.3, "TX"),
    "dallas-tx": ("Dallas, TX", 102.6, "TX"),
    "houston-tx": ("Houston, TX", 96.5, "TX"),
    "atlanta-ga": ("Atlanta, GA", 107.0, "GA"),
    "philadelphia-pa": ("Philadelphia, PA", 101.4, "PA"),
    "phoenix-az": ("Phoenix, AZ", 108.4, "AZ"),
    "minneapolis-mn": ("Minneapolis, MN", 105.7, "MN"),
    "raleigh-nc": ("Raleigh, NC", 104.9, "NC"),
    "nashville-tn": ("Nashville, TN", 105.2, "TN"),
    "portland-or": ("Portland, OR", 130.8, "OR"),
    "san-diego-ca": ("San Diego, CA", 160.4, "CA"),
    "pittsburgh-pa": ("Pittsburgh, PA", 92.1, "PA"),
    "indianapolis-in": ("Indianapolis, IN", 91.4, "IN"),
    "kansas-city-mo": ("Kansas City, MO", 92.6, "MO"),
    "saint-louis-mo": ("St. Louis, MO", 89.7, "MO"),
    "cleveland-oh": ("Cleveland, OH", 88.5, "OH"),
    "detroit-mi": ("Detroit, MI", 88.0, "MI"),
    "memphis-tn": ("Memphis, TN", 85.9, "TN"),
    "buffalo-ny": ("Buffalo, NY", 91.8, "NY"),
    "las-vegas-nv": ("Las Vegas, NV", 110.5, "NV"),
    "honolulu-hi": ("Honolulu, HI", 184.2, "HI"),
}


def calc_cost_of_living(inputs):
    city_a = (inputs.get("city_a") or "").strip().lower()
    city_b = (inputs.get("city_b") or "").strip().lower()
    salary = _num(inputs.get("salary", 80_000), 80_000)
    if city_a not in COL_CITIES or city_b not in COL_CITIES:
        raise CalcError("Please select two valid cities.")
    a_name, a_idx, a_state = COL_CITIES[city_a]
    b_name, b_idx, b_state = COL_CITIES[city_b]
    equivalent_salary = salary * b_idx / a_idx
    diff_pct = (b_idx - a_idx) / a_idx * 100
    components = []
    # Per-category multipliers around the base index for realism
    multipliers = {"Housing": 1.55, "Groceries": 1.07, "Transportation": 1.18,
                    "Healthcare": 0.95, "Utilities": 1.03, "Goods & Services": 1.10}
    for cat, m in multipliers.items():
        a_cost = 1000 * (a_idx / 100) * m
        b_cost = 1000 * (b_idx / 100) * m
        components.append({"category": cat,
                            "city_a": _round_money(a_cost),
                            "city_b": _round_money(b_cost),
                            "diff_pct": _round_money((b_cost - a_cost) / a_cost * 100)})
    return {
        "headline": (f"To match ${salary:,.0f} in {a_name} you'd need "
                      f"${equivalent_salary:,.0f} in {b_name}"),
        "equivalent_salary": _round_money(equivalent_salary),
        "diff_pct": _round_money(diff_pct),
        "city_a": {"name": a_name, "index": a_idx, "state": a_state},
        "city_b": {"name": b_name, "index": b_idx, "state": b_state},
        "components": components,
    }


# ─── 17. Inflation ──────────────────────────────────────────────────

def calc_inflation(inputs):
    amount = _num(inputs.get("amount"), name="Amount")
    from_year = _int(inputs.get("from_year", 2000), 2000)
    to_year = _int(inputs.get("to_year", 2025), 2025)
    if from_year > to_year:
        raise CalcError("'From' year must be earlier than 'to' year.")
    rate = _num(inputs.get("rate", 3.2), 3.2)
    years = to_year - from_year
    factor = (1 + rate / 100.0) ** years
    new_value = amount * factor
    return {
        "headline": (f"${amount:,.0f} in {from_year} equals "
                      f"${new_value:,.0f} in {to_year}"),
        "new_value": _round_money(new_value),
        "old_value": _round_money(amount),
        "years": years,
        "cumulative_pct": _round_money((factor - 1) * 100),
        "annual_rate": rate,
    }


# ─── 18. Student loan ───────────────────────────────────────────────

def calc_student_loan(inputs):
    balance = _num(inputs.get("balance"), name="Balance")
    rate = _num(inputs.get("rate", 5.5), 5.5)
    term_years = max(1, _int(inputs.get("term_years", 10), 10))
    extra = _num(inputs.get("extra", 0), 0)
    n = term_years * 12
    r = (rate / 100.0) / 12.0
    base_pmt = (balance * r / (1 - (1 + r) ** (-n))
                if r else balance / n)
    pmt = base_pmt + extra
    bal = balance
    months_paid = 0
    interest_paid = 0.0
    while bal > 0 and months_paid < n * 2:
        months_paid += 1
        i = bal * r
        interest_paid += i
        bal = bal + i - pmt
        if bal < 0:
            bal = 0
    return {
        "headline": (f"${base_pmt:,.0f}/mo base, paid off in "
                      f"{months_paid // 12}y {months_paid % 12}m"),
        "monthly_payment": _round_money(base_pmt),
        "actual_payment": _round_money(pmt),
        "months_to_payoff": months_paid,
        "total_interest": _round_money(interest_paid),
        "balance": _round_money(balance),
    }


# ─── 19. Auto loan ──────────────────────────────────────────────────

def calc_auto_loan(inputs):
    price = _num(inputs.get("price"), name="Vehicle price")
    down = _num(inputs.get("down", 3000), 3000)
    trade_in = _num(inputs.get("trade_in", 0), 0)
    rate = _num(inputs.get("rate", 7.5), 7.5)
    term_months = max(1, _int(inputs.get("term_months", 60), 60))
    sales_tax_pct = _num(inputs.get("sales_tax_pct", 6.0), 6.0)
    loan = price + (price - trade_in) * sales_tax_pct / 100.0 - down - trade_in
    if loan <= 0:
        raise CalcError("Loan amount calculates to zero or less.")
    r = (rate / 100.0) / 12.0
    pmt = (loan * r / (1 - (1 + r) ** (-term_months))
           if r else loan / term_months)
    total = pmt * term_months
    return {
        "headline": f"${pmt:,.0f}/mo for {term_months} months",
        "monthly_payment": _round_money(pmt),
        "loan_amount": _round_money(loan),
        "total_paid": _round_money(total),
        "total_interest": _round_money(total - loan),
    }


# ─── 20. Credit card payoff ─────────────────────────────────────────

def calc_credit_card(inputs):
    balance = _num(inputs.get("balance"), name="Balance")
    apr = _num(inputs.get("apr", 22.5), 22.5)
    monthly = _num(inputs.get("monthly_payment"), name="Monthly payment")
    r = (apr / 100.0) / 12.0
    if monthly <= balance * r:
        raise CalcError("Payment too low — interest exceeds payment. "
                          "Try a higher monthly amount.")
    months = -math.log(1 - balance * r / monthly) / math.log(1 + r) if r else balance / monthly
    months = math.ceil(months)
    total_paid = monthly * months
    return {
        "headline": (f"Paid off in {months // 12}y {months % 12}m, "
                      f"total interest ${total_paid - balance:,.0f}"),
        "months_to_payoff": months,
        "total_paid": _round_money(total_paid),
        "total_interest": _round_money(total_paid - balance),
        "apr": apr,
        "monthly": _round_money(monthly),
    }


# ─── 21. Net worth ──────────────────────────────────────────────────

def calc_net_worth(inputs):
    assets = {
        "Cash & checking": _num(inputs.get("cash", 0), 0),
        "Savings / CDs": _num(inputs.get("savings", 0), 0),
        "Brokerage": _num(inputs.get("brokerage", 0), 0),
        "Retirement accounts": _num(inputs.get("retirement", 0), 0),
        "Home value": _num(inputs.get("home_value", 0), 0),
        "Vehicles": _num(inputs.get("vehicles", 0), 0),
        "Other assets": _num(inputs.get("other_assets", 0), 0),
    }
    liabilities = {
        "Mortgage balance": _num(inputs.get("mortgage", 0), 0),
        "Auto loans": _num(inputs.get("auto_loans", 0), 0),
        "Student loans": _num(inputs.get("student_loans", 0), 0),
        "Credit cards": _num(inputs.get("credit_cards", 0), 0),
        "Other debt": _num(inputs.get("other_debt", 0), 0),
    }
    total_assets = sum(assets.values())
    total_liab = sum(liabilities.values())
    nw = total_assets - total_liab
    return {
        "headline": f"Net worth: ${nw:,.0f}",
        "net_worth": _round_money(nw),
        "total_assets": _round_money(total_assets),
        "total_liabilities": _round_money(total_liab),
        "assets": [{"name": k, "amount": _round_money(v)}
                   for k, v in assets.items()],
        "liabilities": [{"name": k, "amount": _round_money(v)}
                        for k, v in liabilities.items()],
    }


# ─── 22. Rent vs Buy ────────────────────────────────────────────────

def calc_rent_vs_buy(inputs):
    monthly_rent = _num(inputs.get("monthly_rent"), name="Monthly rent")
    home_price = _num(inputs.get("home_price"), name="Home price")
    down_pct = _num(inputs.get("down_pct", 20), 20)
    rate = _num(inputs.get("rate", 7.0), 7.0)
    years = max(1, _int(inputs.get("years", 7), 7))
    home_appr = _num(inputs.get("appreciation", 3.5), 3.5)
    rent_growth = _num(inputs.get("rent_growth", 3.0), 3.0)
    prop_tax_pct = _num(inputs.get("prop_tax_pct", 1.1), 1.1)
    if monthly_rent <= 0 or home_price <= 0:
        raise CalcError("Both rent and home price must be positive.")
    down = home_price * down_pct / 100.0
    loan = home_price - down
    n = 30 * 12
    r = (rate / 100.0) / 12.0
    pmt = loan * r / (1 - (1 + r) ** (-n)) if r else loan / n
    # rent total over horizon (geometric)
    total_rent = 0.0
    m_rent = monthly_rent
    for _ in range(years):
        total_rent += m_rent * 12
        m_rent *= (1 + rent_growth / 100.0)
    # own costs
    annual_own = pmt * 12 + home_price * prop_tax_pct / 100.0 + home_price * 0.005  # ins+maint
    total_own_cash = annual_own * years + down
    home_future = home_price * (1 + home_appr / 100.0) ** years
    # Mortgage balance after `years`
    bal = loan
    for _ in range(years * 12):
        i = bal * r
        bal = bal + i - pmt
    equity = home_future - max(0, bal)
    net_own_cost = total_own_cash - equity
    return {
        "headline": ("Buying favored by "
                      f"${total_rent - net_own_cost:,.0f}" if net_own_cost < total_rent
                      else f"Renting favored by ${net_own_cost - total_rent:,.0f}"),
        "total_rent_cost": _round_money(total_rent),
        "total_own_cash": _round_money(total_own_cash),
        "home_future_value": _round_money(home_future),
        "mortgage_balance_end": _round_money(max(0, bal)),
        "equity_built": _round_money(equity),
        "net_own_cost": _round_money(net_own_cost),
        "verdict": "buy" if net_own_cost < total_rent else "rent",
        "years": years,
        "monthly_pi": _round_money(pmt),
    }


# ─── Catalog ───────────────────────────────────────────────────────────

CALCULATORS = [
    # — Home Buying
    {"slug": "mortgage", "title": "Mortgage Calculator",
     "group": "Home Buying", "featured": True,
     "blurb": "Estimate monthly P&I, PMI, taxes, insurance, and amortization.",
     "fields": ["price", "down", "rate", "term", "prop_tax_pct",
                "insurance", "hoa"],
     "fn": calc_mortgage,
     "defaults": {"price": "350000", "down": "70000", "rate": "7.0",
                  "term": "30", "prop_tax_pct": "1.1",
                  "insurance": "1500", "hoa": "0"}},
    {"slug": "affordability", "title": "Home Affordability Calculator",
     "group": "Home Buying", "featured": True,
     "blurb": "How much house can you afford based on income, DTI, and down payment.",
     "fields": ["income", "monthly_debt", "down", "rate", "term", "dti"],
     "fn": calc_affordability,
     "defaults": {"income": "100000", "monthly_debt": "400",
                  "down": "60000", "rate": "7.0", "term": "30", "dti": "36"}},
    {"slug": "refinance", "title": "Refinance Calculator",
     "group": "Home Buying", "featured": False,
     "blurb": "Compare your current mortgage to a refinance and find break-even.",
     "fields": ["balance", "current_rate", "new_rate", "term", "closing"],
     "fn": calc_refinance,
     "defaults": {"balance": "250000", "current_rate": "7.5",
                  "new_rate": "6.0", "term": "30", "closing": "5000"}},
    {"slug": "closing-costs", "title": "Closing Costs Calculator",
     "group": "Home Buying", "featured": False,
     "blurb": "Itemized estimate of closing costs based on price and state.",
     "fields": ["price", "down", "state"],
     "fn": calc_closing,
     "defaults": {"price": "350000", "down": "70000", "state": "NY"}},
    {"slug": "rent-vs-buy", "title": "Rent vs Buy Calculator",
     "group": "Home Buying", "featured": False,
     "blurb": "Compare the lifetime cost of renting vs. buying a home.",
     "fields": ["monthly_rent", "home_price", "down_pct", "rate",
                "years", "appreciation", "rent_growth", "prop_tax_pct"],
     "fn": calc_rent_vs_buy,
     "defaults": {"monthly_rent": "2200", "home_price": "350000",
                  "down_pct": "20", "rate": "7.0", "years": "7",
                  "appreciation": "3.5", "rent_growth": "3.0",
                  "prop_tax_pct": "1.1"}},
    {"slug": "property-tax", "title": "Property Tax Calculator",
     "group": "Home Buying", "featured": False,
     "blurb": "Annual property tax estimate using your state's effective rate.",
     "fields": ["value", "state"],
     "fn": calc_property_tax,
     "defaults": {"value": "350000", "state": "NJ"}},

    # — Taxes
    {"slug": "income-tax", "title": "Federal Income Tax Calculator",
     "group": "Taxes", "featured": True,
     "blurb": "2025-2026 federal income tax estimate by filing status.",
     "fields": ["income", "filing", "pretax_401k", "itemized"],
     "fn": calc_income_tax,
     "defaults": {"income": "85000", "filing": "single",
                  "pretax_401k": "5000", "itemized": "0"}},
    {"slug": "state-tax", "title": "State Income Tax Calculator",
     "group": "Taxes", "featured": False,
     "blurb": "State income tax estimate for all 50 states + DC.",
     "fields": ["income", "state", "filing"],
     "fn": calc_state_tax,
     "defaults": {"income": "85000", "state": "CA", "filing": "single"}},
    {"slug": "paycheck", "title": "Paycheck Calculator",
     "group": "Taxes", "featured": True,
     "blurb": "Take-home pay after federal, state, FICA, and pre-tax deductions.",
     "fields": ["salary", "state", "filing", "pay_freq",
                "pretax_401k_pct", "pretax_health"],
     "fn": calc_paycheck,
     "defaults": {"salary": "75000", "state": "TX",
                  "filing": "single", "pay_freq": "biweekly",
                  "pretax_401k_pct": "5", "pretax_health": "0"}},
    {"slug": "capital-gains", "title": "Capital Gains Tax Calculator",
     "group": "Taxes", "featured": False,
     "blurb": "Long-term vs short-term capital gains tax estimate.",
     "fields": ["cost_basis", "proceeds", "holding_years", "income", "filing"],
     "fn": calc_capital_gains,
     "defaults": {"cost_basis": "10000", "proceeds": "25000",
                  "holding_years": "3", "income": "80000",
                  "filing": "single"}},

    # — Retirement
    {"slug": "retirement", "title": "Retirement Calculator",
     "group": "Retirement", "featured": True,
     "blurb": "Project your nest egg and see whether you're on track.",
     "fields": ["current_age", "retire_age", "life_age", "income",
                "current_savings", "monthly_contrib", "growth",
                "inflation", "income_replacement", "soc_sec_monthly"],
     "fn": calc_retirement,
     "defaults": {"current_age": "35", "retire_age": "67", "life_age": "95",
                  "income": "80000", "current_savings": "50000",
                  "monthly_contrib": "1000", "growth": "7.0",
                  "inflation": "2.5", "income_replacement": "80",
                  "soc_sec_monthly": "2200"}},
    {"slug": "401k", "title": "401(k) Calculator",
     "group": "Retirement", "featured": True,
     "blurb": "Project 401(k) balance with employer match and salary growth.",
     "fields": ["current_age", "retire_age", "salary", "contrib_pct",
                "employer_match_pct", "employer_match_cap", "current_balance",
                "growth", "salary_growth"],
     "fn": calc_401k,
     "defaults": {"current_age": "30", "retire_age": "67",
                  "salary": "70000", "contrib_pct": "6",
                  "employer_match_pct": "50", "employer_match_cap": "6",
                  "current_balance": "25000", "growth": "7.0",
                  "salary_growth": "2.5"}},
    {"slug": "ira", "title": "Roth vs Traditional IRA Calculator",
     "group": "Retirement", "featured": False,
     "blurb": "Compare a Roth vs Traditional IRA over your time horizon.",
     "fields": ["current_age", "retire_age", "annual_contrib", "growth",
                "current_balance", "marginal_now", "marginal_retire"],
     "fn": calc_ira,
     "defaults": {"current_age": "30", "retire_age": "65",
                  "annual_contrib": "7000", "growth": "7.0",
                  "current_balance": "0", "marginal_now": "22",
                  "marginal_retire": "22"}},

    # — Investing
    {"slug": "investment", "title": "Investment Growth Calculator",
     "group": "Investing", "featured": False,
     "blurb": "Future value of a portfolio with periodic contributions.",
     "fields": ["initial", "monthly", "years", "rate"],
     "fn": calc_investment,
     "defaults": {"initial": "10000", "monthly": "500", "years": "20",
                  "rate": "7.0"}},
    {"slug": "inflation", "title": "Inflation Calculator",
     "group": "Investing", "featured": False,
     "blurb": "Convert past-year dollars to today's dollars (or vice versa).",
     "fields": ["amount", "from_year", "to_year", "rate"],
     "fn": calc_inflation,
     "defaults": {"amount": "10000", "from_year": "2000",
                  "to_year": "2025", "rate": "3.2"}},

    # — Banking
    {"slug": "savings", "title": "Savings Calculator",
     "group": "Banking", "featured": True,
     "blurb": "Compound interest growth with periodic deposits.",
     "fields": ["initial", "monthly_deposit", "years", "apy", "compound"],
     "fn": calc_savings,
     "defaults": {"initial": "5000", "monthly_deposit": "200",
                  "years": "10", "apy": "4.0", "compound": "monthly"}},
    {"slug": "cd", "title": "CD Calculator",
     "group": "Banking", "featured": False,
     "blurb": "Certificate of deposit maturity value calculator.",
     "fields": ["principal", "apy", "term_months"],
     "fn": calc_cd,
     "defaults": {"principal": "10000", "apy": "4.5", "term_months": "12"}},

    # — Loans
    {"slug": "auto-loan", "title": "Auto Loan Calculator",
     "group": "Loans", "featured": False,
     "blurb": "Monthly auto loan payment with tax and trade-in.",
     "fields": ["price", "down", "trade_in", "rate", "term_months",
                "sales_tax_pct"],
     "fn": calc_auto_loan,
     "defaults": {"price": "32000", "down": "3000", "trade_in": "0",
                  "rate": "7.5", "term_months": "60",
                  "sales_tax_pct": "6.0"}},
    {"slug": "student-loan", "title": "Student Loan Calculator",
     "group": "Loans", "featured": False,
     "blurb": "Payoff timeline and total interest for a student loan.",
     "fields": ["balance", "rate", "term_years", "extra"],
     "fn": calc_student_loan,
     "defaults": {"balance": "35000", "rate": "5.5",
                  "term_years": "10", "extra": "0"}},
    {"slug": "credit-card", "title": "Credit Card Payoff Calculator",
     "group": "Loans", "featured": False,
     "blurb": "How long to pay off a credit card balance at a fixed monthly amount.",
     "fields": ["balance", "apr", "monthly_payment"],
     "fn": calc_credit_card,
     "defaults": {"balance": "5000", "apr": "22.5",
                  "monthly_payment": "200"}},

    # — Planning
    {"slug": "net-worth", "title": "Net Worth Calculator",
     "group": "Planning", "featured": True,
     "blurb": "Compute your total assets minus total liabilities.",
     "fields": ["cash", "savings", "brokerage", "retirement", "home_value",
                "vehicles", "other_assets", "mortgage", "auto_loans",
                "student_loans", "credit_cards", "other_debt"],
     "fn": calc_net_worth,
     "defaults": {"cash": "5000", "savings": "15000", "brokerage": "30000",
                  "retirement": "80000", "home_value": "350000",
                  "vehicles": "18000", "other_assets": "5000",
                  "mortgage": "260000", "auto_loans": "12000",
                  "student_loans": "18000", "credit_cards": "2500",
                  "other_debt": "0"}},
    {"slug": "cost-of-living", "title": "Cost of Living Calculator",
     "group": "Planning", "featured": True,
     "blurb": "Compare cost of living between two U.S. cities.",
     "fields": ["city_a", "city_b", "salary"],
     "fn": calc_cost_of_living,
     "defaults": {"city_a": "austin-tx", "city_b": "new-york-ny",
                  "salary": "100000"}},
]

CALC_INDEX = {c["slug"]: c for c in CALCULATORS}


def find(slug):
    return CALC_INDEX.get(slug)


def run(slug, inputs):
    c = find(slug)
    if not c:
        raise CalcError(f"Unknown calculator: {slug}")
    return c["fn"](inputs)
