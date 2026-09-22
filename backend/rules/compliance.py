"""
Agent Kautilya — MoSPI 2023 Statutory Guidelines Compliance Engine
Implements:
1. MoSPI Annexure-II: Prohibited / Non-Permissible Works Blacklist Scanner
2. MoSPI Para 2.5 & 5.1: Mandatory SC (15.0%) and ST (7.5%) Quota Evaluator
"""

import re
from typing import Dict, Any, Tuple, Optional, List

PROHIBITED_WORKS_ANNEXURE_II = [
    {
        "item": "Item 1 & 2",
        "category": "Places of Religious Worship / Faith Structures",
        "pattern": re.compile(r"\b(temple|mandir|masjid|mosque|church|gurdwara|ashram|dharamshala|prayer hall|synagogue|religious shrine|idols)\b", re.IGNORECASE),
        "reason": "MoSPI Annexure-II Item 2: Works within or belonging to religious places of worship are strictly prohibited under MPLADS guidelines."
    },
    {
        "item": "Item 3",
        "category": "Statues, Memorials and Monuments",
        "pattern": re.compile(r"\b(statue|memorial|monument|samadhi|welcome arch|commemorative pillar|cenotaph|tomb)\b", re.IGNORECASE),
        "reason": "MoSPI Annexure-II Item 3: Erection of statues, memorials, monuments, and commemorative arches is strictly non-permissible."
    },
    {
        "item": "Item 7",
        "category": "Commercial / Private Corporate Entities",
        "pattern": re.compile(r"\b(commercial complex|shopping mall|private club|gymkhana|trade center|hotel|resort|multiplex|private trust)\b", re.IGNORECASE),
        "reason": "MoSPI Annexure-II Item 7: Works benefiting commercial organizations, private trusts, or corporate establishments are ineligible."
    },
    {
        "item": "Item 5",
        "category": "Recurring Grants, Consumables and Loans",
        "pattern": re.compile(r"\b(recurring grant|salary|honorarium|loan disbursement|office consumable|printer paper|petrol|diesel|furniture for private)\b", re.IGNORECASE),
        "reason": "MoSPI Annexure-II Item 5: Recurring expenditure, staff salaries, financial grants, and office consumables are barred."
    },
    {
        "item": "Item 4 & 6",
        "category": "Private Property & Non-Government Lands",
        "pattern": re.compile(r"\b(private land|private estate|encroached land|unauthorized colony|private residential)\b", re.IGNORECASE),
        "reason": "MoSPI Annexure-II Item 4: Assets must be created exclusively on land owned by the Government or local bodies."
    }
]

def check_mospi_prohibited_work(text: str, work_type: str = "") -> Dict[str, Any]:
    """
    Scans proposal titles, descriptions, and categories against the MoSPI Annexure-II negative list.
    """
    full_text = f"{text or ''} {work_type or ''}".strip()
    for rule in PROHIBITED_WORKS_ANNEXURE_II:
        if rule["pattern"].search(full_text):
            return {
                "is_prohibited": True,
                "item": rule["item"],
                "category": rule["category"],
                "reason": rule["reason"],
                "status": "STATUTORY_VIOLATION"
            }
    return {
        "is_prohibited": False,
        "item": None,
        "category": None,
        "reason": None,
        "status": "PERMISSIBLE"
    }

def evaluate_mp_statutory_quotas(
    total_sanctioned: float,
    sc_sanctioned: float,
    st_sanctioned: float,
    constituency_type: str = "General"
) -> Dict[str, Any]:
    """
    Evaluates compliance with MoSPI 2023 Para 2.5 statutory SC (15%) and ST (7.5%) quotas.
    """
    if total_sanctioned <= 0:
        return {
            "total_sanctioned": 0.0,
            "sc_pct": 0.0, "st_pct": 0.0,
            "sc_target_pct": 15.0, "st_target_pct": 7.5,
            "sc_shortfall_amt": 0.0, "st_shortfall_amt": 0.0,
            "sc_compliant": False, "st_compliant": False,
            "statutory_compliant": False
        }

    sc_target_amt = 0.15 * total_sanctioned
    st_target_amt = 0.075 * total_sanctioned

    sc_pct = round(sc_sanctioned / total_sanctioned * 100, 1)
    st_pct = round(st_sanctioned / total_sanctioned * 100, 1)

    sc_shortfall = max(0.0, round(sc_target_amt - sc_sanctioned, 2))
    st_shortfall = max(0.0, round(st_target_amt - st_sanctioned, 2))

    is_sc_reserved = "SC" in constituency_type.upper()
    is_st_reserved = "ST" in constituency_type.upper()

    sc_compliant = is_sc_reserved or (sc_pct >= 15.0)
    st_compliant = is_st_reserved or (st_pct >= 7.5)

    return {
        "total_sanctioned": total_sanctioned,
        "sc_sanctioned": sc_sanctioned,
        "st_sanctioned": st_sanctioned,
        "sc_pct": sc_pct,
        "st_pct": st_pct,
        "sc_target_pct": 15.0,
        "st_target_pct": 7.5,
        "sc_target_amt": round(sc_target_amt, 2),
        "st_target_amt": round(st_target_amt, 2),
        "sc_shortfall_amt": sc_shortfall if not is_sc_reserved else 0.0,
        "st_shortfall_amt": st_shortfall if not is_st_reserved else 0.0,
        "sc_compliant": sc_compliant,
        "st_compliant": st_compliant,
        "statutory_compliant": sc_compliant and st_compliant,
    }


def evaluate_execution_horizon(days: int, status: str = "In Progress") -> Dict[str, Any]:
    """
    Evaluates project execution timeline against MoSPI MPLADS 2023 Para 4.6 statutory 18-month horizon (540 calendar days).
    """
    days = int(days)
    if status == "Completed":
        return {
            "execution_days": days,
            "horizon_breach": False,
            "delay_severity": "Completed",
            "status_code": "COMPLETED",
            "statutory_limit_days": 540,
            "days_over_limit": 0,
            "directive": "Asset successfully commissioned and delivered."
        }

    if days > 540:
        return {
            "execution_days": days,
            "horizon_breach": True,
            "delay_severity": "Statutory Horizon Breach (>540 Days / 18 Mo)",
            "status_code": "STATUTORY_BREACH",
            "statutory_limit_days": 540,
            "days_over_limit": days - 540,
            "directive": "MoSPI Para 4.6 Statutory Escalation: Issue immediate notice to surrender unspent funds back to Consolidated Fund of India."
        }
    elif days > 365:
        return {
            "execution_days": days,
            "horizon_breach": False,
            "delay_severity": "Critical Delay (365-540 Days / 12-18 Mo)",
            "status_code": "CRITICAL_DELAY",
            "statutory_limit_days": 540,
            "days_over_limit": 0,
            "directive": "Issue 30-day show-cause notice to Implementing Agency; mandate weekly physical progress verification."
        }
    elif days > 270:
        return {
            "execution_days": days,
            "horizon_breach": False,
            "delay_severity": "Milestone Watchlist (270-365 Days / 9-12 Mo)",
            "status_code": "WATCHLIST",
            "statutory_limit_days": 540,
            "days_over_limit": 0,
            "directive": "Flag for District Monitoring Committee review at next monthly coordination meeting."
        }
    else:
        return {
            "execution_days": days,
            "horizon_breach": False,
            "delay_severity": "On Schedule (<270 Days)",
            "status_code": "NORMAL",
            "statutory_limit_days": 540,
            "days_over_limit": 0,
            "directive": "Normal project execution progression."
        }


def forecast_fund_lapse_risk(
    sanctioned_amount: float,
    uc_amount: float,
    execution_days: int,
    status: str = "In Progress",
    risk_level: str = "Low",
    vendor_is_suspect: int = 0
) -> Dict[str, Any]:
    """
    Forecasts probability of fiscal year-end fund lapse / surrender for stagnant or slow-moving public works.
    """
    if status == "Completed":
        return {
            "unspent_balance": 0.0,
            "unspent_balance_pct": 0.0,
            "lapse_risk_pct": 0.0,
            "lapse_risk_level": "Low",
            "surrender_risk": False,
            "recommendation": "Funds fully converted to durable public asset."
        }

    sanctioned = float(sanctioned_amount or 0.0)
    uc = float(uc_amount or 0.0)
    unspent = max(0.0, round(sanctioned - uc, 2))
    unspent_pct = round((unspent / sanctioned * 100) if sanctioned > 0 else 0.0, 1)

    base = 50.0 if execution_days > 540 else (35.0 if execution_days > 365 else (20.0 if execution_days > 270 else 5.0))
    stalled_add = 25.0 if status == "Stalled" else 0.0
    unspent_add = unspent_pct * 0.20
    risk_add = 15.0 if (risk_level == "High" or vendor_is_suspect == 1) else 0.0

    score = round(min(100.0, base + stalled_add + unspent_add + risk_add), 1)
    level = "High" if score >= 65.0 else ("Moderate" if score >= 40.0 else "Low")

    recommendation = (
        "Immediate MoSPI Para 4.8 Escrow Recall recommended to avoid fund surrender."
        if level == "High" else
        ("Expedite stage-2 milestone certification to prevent unspent fund locking."
         if level == "Moderate" else "Unspent funds are within permissible fiscal limits.")
    )

    return {
        "unspent_balance": unspent,
        "unspent_balance_pct": unspent_pct,
        "lapse_risk_pct": score,
        "lapse_risk_level": level,
        "surrender_risk": level == "High",
        "recommendation": recommendation,
    }

