"""
10-point scoring system and portfolio-level analytics.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pandas as pd

from config import SCORING_THRESHOLDS


# ──────────────────────────────────────────────
# Single-stock scoring
# ──────────────────────────────────────────────
def _check(value, op: str, threshold: float) -> Tuple[bool, str]:
    """
    Return (passed, display_string).
    *op* is one of '>', '<', '>=', '<='.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False, "Data N/A"
    try:
        v = float(value)
    except (ValueError, TypeError):
        return False, "Data N/A"

    if op == ">":
        passed = v > threshold
    elif op == ">=":
        passed = v >= threshold
    elif op == "<":
        passed = v < threshold
    elif op == "<=":
        passed = v <= threshold
    else:
        passed = False

    symbol = "✅" if passed else "❌"
    return passed, f"{symbol} {v:.2f} (threshold {op} {threshold})"


def score_stock(row: Dict[str, Any]) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Evaluate a stock against the 10-point checklist.
    Returns (score_int, list_of_criterion_dicts).
    """
    t = SCORING_THRESHOLDS
    checks: List[Dict[str, Any]] = []

    criteria = [
        ("ROE > 15%", row.get("roe"), ">", t["roe_min"]),
        ("Revenue CAGR > 12%", row.get("revenue_cagr_5y"), ">", t["revenue_cagr_min"]),
        ("EPS CAGR > 12%", row.get("eps_cagr_5y"), ">", t["eps_cagr_min"]),
        ("D/E < 0.5", row.get("debt_to_equity"), "<", t["de_max"]),
        (
            "Positive & Growing FCF",
            row.get("free_cash_flow"),
            ">",
            0,
        ),
        ("CFO/PAT > 1", row.get("cfo_pat"), ">", t["cfo_pat_min"]),
        ("Promoter Holding > 50%", row.get("promoter_holding"), ">", t["promoter_holding_min"]),
        ("PEG < 1", row.get("peg_ratio"), "<", t["peg_max"]),
        ("Current Ratio > 1.5", row.get("current_ratio"), ">", t["current_ratio_min"]),
        ("Net Profit Margin > 10%", row.get("net_margin"), ">", t["net_margin_min"]),
    ]

    score = 0
    for name, value, op, thresh in criteria:
        passed, detail = _check(value, op, thresh)
        if passed:
            score += 1
        checks.append({"criterion": name, "passed": passed, "detail": detail})

    return score, checks


def score_label(score: int) -> str:
    """Human-readable label for a score."""
    if score >= 8:
        return "🟢 Strong Buy"
    if score >= 5:
        return "🟡 Hold / Accumulate"
    return "🔴 Avoid"


def score_color(score: int) -> str:
    """Hex colour for the score."""
    if score >= 8:
        return "#2ecc71"
    if score >= 5:
        return "#f1c40f"
    return "#e74c3c"


# ──────────────────────────────────────────────
# Opportunity-zone helpers
# ──────────────────────────────────────────────
def opportunity_zone(pct_down: float | None) -> str:
    if pct_down is None:
        return "—"
    if pct_down <= 10:
        return "🟢 Near High"
    if pct_down <= 20:
        return "🟡 Mild Correction"
    return "🔴 Deep Correction"


def opportunity_color(pct_down: float | None) -> str:
    if pct_down is None:
        return "#95a5a6"
    if pct_down <= 10:
        return "#2ecc71"
    if pct_down <= 20:
        return "#f39c12"
    return "#e74c3c"


# ──────────────────────────────────────────────
# Portfolio-level analytics
# ──────────────────────────────────────────────
def portfolio_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Aggregate stats across the portfolio."""
    summary: Dict[str, Any] = {}
    summary["total_stocks"] = len(df)
    summary["sectors"] = df["sector"].nunique() if "sector" in df.columns else 0

    for col in ["roe", "debt_to_equity", "pe_ratio", "pct_from_52w_high", "score"]:
        if col in df.columns:
            summary[f"avg_{col}"] = df[col].mean()
            summary[f"median_{col}"] = df[col].median()

    if "cap_size" in df.columns:
        summary["cap_distribution"] = df["cap_size"].value_counts().to_dict()

    if "sector" in df.columns and "weight" in df.columns:
        summary["sector_weights"] = (
            df.groupby("sector")["weight"].sum().to_dict()
        )

    return summary