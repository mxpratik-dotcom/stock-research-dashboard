"""
Ratio calculation helpers and screening / filtering utilities.
Works on the DataFrame produced by data_fetcher.fetch_multiple_stocks().
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# ──────────────────────────────────────────────
# Format helpers
# ──────────────────────────────────────────────
def fmt(value: Any, suffix: str = "", decimals: int = 2) -> str:
    """Pretty-print a numeric value; return '—' when unavailable."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    try:
        return f"{float(value):,.{decimals}f}{suffix}"
    except (ValueError, TypeError):
        return str(value)


def fmt_cr(value: Any) -> str:
    """Format large numbers in Indian crore (₹ Cr)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    try:
        v = float(value)
        if abs(v) >= 1e7:
            return f"₹{v / 1e7:,.0f} Cr"
        if abs(v) >= 1e5:
            return f"₹{v / 1e5:,.0f} L"
        return f"₹{v:,.0f}"
    except (ValueError, TypeError):
        return "—"


def fmt_mcap(value: Any) -> str:
    """Format market cap in ₹ Cr."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    try:
        v = float(value)
        return f"₹{v / 1e7:,.0f} Cr"
    except (ValueError, TypeError):
        return "—"


# ──────────────────────────────────────────────
# Ratio extraction (all from fetched data)
# ──────────────────────────────────────────────
def get_valuation_ratios(row: Dict[str, Any]) -> Dict[str, str]:
    return {
        "P/E (TTM)": fmt(row.get("pe_ratio")),
        "Forward P/E": fmt(row.get("forward_pe")),
        "P/B": fmt(row.get("pb_ratio")),
        "PEG": fmt(row.get("peg_ratio")),
        "EV/EBITDA": fmt(row.get("ev_ebitda")),
        "P/S": fmt(row.get("ps_ratio")),
        "Dividend Yield": fmt(row.get("dividend_yield"), suffix="%"),
    }


def get_profitability_ratios(row: Dict[str, Any]) -> Dict[str, str]:
    return {
        "ROE": fmt(row.get("roe"), suffix="%"),
        "ROCE": fmt(row.get("roce"), suffix="%"),
        "ROA": fmt(row.get("roa"), suffix="%"),
        "Net Profit Margin": fmt(row.get("net_margin"), suffix="%"),
        "Operating Margin": fmt(row.get("operating_margin"), suffix="%"),
        "Gross Margin": fmt(row.get("gross_margin"), suffix="%"),
    }


def get_growth_ratios(row: Dict[str, Any]) -> Dict[str, str]:
    return {
        "Revenue CAGR (5Y)": fmt(row.get("revenue_cagr_5y"), suffix="%"),
        "EPS / NI CAGR (5Y)": fmt(row.get("eps_cagr_5y"), suffix="%"),
        "FCF Growth (YoY)": fmt(row.get("fcf_growth_yoy"), suffix="%"),
    }


def get_leverage_ratios(row: Dict[str, Any]) -> Dict[str, str]:
    return {
        "Debt-to-Equity": fmt(row.get("debt_to_equity")),
        "Interest Coverage": fmt(row.get("interest_coverage"), suffix="x"),
        "Current Ratio": fmt(row.get("current_ratio")),
        "Quick Ratio": fmt(row.get("quick_ratio")),
    }


def get_cashflow_metrics(row: Dict[str, Any]) -> Dict[str, str]:
    return {
        "Free Cash Flow": fmt_cr(row.get("free_cash_flow")),
        "Operating Cash Flow": fmt_cr(row.get("operating_cash_flow")),
        "CFO / PAT": fmt(row.get("cfo_pat"), suffix="x"),
        "Net Income": fmt_cr(row.get("net_income")),
    }


def get_quality_checks(row: Dict[str, Any]) -> Dict[str, str]:
    return {
        "Promoter / Insider Holding": fmt(row.get("promoter_holding"), suffix="%"),
        "52-W High Distance": fmt(row.get("pct_from_52w_high"), suffix="%"),
        "Market Cap": fmt_mcap(row.get("market_cap")),
    }


# ──────────────────────────────────────────────
# Filtering
# ──────────────────────────────────────────────
def filter_stocks(
    df: pd.DataFrame,
    *,
    roe_min: Optional[float] = None,
    roe_max: Optional[float] = None,
    de_min: Optional[float] = None,
    de_max: Optional[float] = None,
    sectors: Optional[List[str]] = None,
    score_min: Optional[int] = None,
    score_max: Optional[int] = None,
) -> pd.DataFrame:
    """Apply optional filters and return the filtered DataFrame."""
    filtered = df.copy()
    if roe_min is not None:
        filtered = filtered[filtered["roe"].fillna(-999) >= roe_min]
    if roe_max is not None:
        filtered = filtered[filtered["roe"].fillna(999) <= roe_max]
    if de_min is not None:
        filtered = filtered[filtered["debt_to_equity"].fillna(-999) >= de_min]
    if de_max is not None:
        filtered = filtered[filtered["debt_to_equity"].fillna(999) <= de_max]
    if sectors:
        filtered = filtered[filtered["sector"].isin(sectors)]
    if score_min is not None:
        filtered = filtered[filtered["score"].fillna(-1) >= score_min]
    if score_max is not None:
        filtered = filtered[filtered["score"].fillna(99) <= score_max]
    return filtered