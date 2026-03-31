"""
Fetches live market data from Yahoo Finance for Indian (NSE) stocks.
All prices and financials are pulled in real-time — nothing is hard-coded.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# Helper: safe getter
# ──────────────────────────────────────────────────────────
def _safe_get(info: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Return value from dict; return *default* on KeyError / None."""
    val = info.get(key, default)
    return default if val is None else val


# ──────────────────────────────────────────────────────────
# Single-stock fetcher
# ──────────────────────────────────────────────────────────
def fetch_stock_data(ticker: str) -> Dict[str, Any]:
    """
    Fetch comprehensive data for a single NSE ticker via yfinance.

    Returns a flat dict with price, valuation, profitability,
    leverage, cash-flow, and growth fields.
    """
    result: Dict[str, Any] = {"ticker": ticker, "error": None}

    try:
        stock = yf.Ticker(ticker)
        info: Dict[str, Any] = stock.info or {}

        # ── Price & Market Data ──────────────────────────
        result["current_price"] = _safe_get(info, "currentPrice",
                                            _safe_get(info, "regularMarketPrice"))
        result["previous_close"] = _safe_get(info, "previousClose",
                                             _safe_get(info, "regularMarketPreviousClose"))
        result["fifty_two_week_high"] = _safe_get(info, "fiftyTwoWeekHigh")
        result["fifty_two_week_low"] = _safe_get(info, "fiftyTwoWeekLow")
        result["market_cap"] = _safe_get(info, "marketCap")
        result["currency"] = _safe_get(info, "currency", "INR")

        # ── Valuation Ratios ─────────────────────────────
        result["pe_ratio"] = _safe_get(info, "trailingPE")
        result["forward_pe"] = _safe_get(info, "forwardPE")
        result["pb_ratio"] = _safe_get(info, "priceToBook")
        result["peg_ratio"] = _safe_get(info, "pegRatio")
        result["ev_ebitda"] = _safe_get(info, "enterpriseToEbitda")
        result["ps_ratio"] = _safe_get(info, "priceToSalesTrailing12Months")
        result["dividend_yield"] = _safe_get(info, "dividendYield")
        if result["dividend_yield"] is not None:
            result["dividend_yield"] *= 100  # convert to %

        result["eps_trailing"] = _safe_get(info, "trailingEps")
        result["eps_forward"] = _safe_get(info, "forwardEps")

        # ── Profitability ────────────────────────────────
        result["roe"] = _pct(info, "returnOnEquity")
        result["roa"] = _pct(info, "returnOnAssets")
        result["net_margin"] = _pct(info, "profitMargins")
        result["operating_margin"] = _pct(info, "operatingMargins")
        result["gross_margin"] = _pct(info, "grossMargins")

        # ── Leverage & Solvency ──────────────────────────
        result["debt_to_equity"] = _safe_get(info, "debtToEquity")
        if result["debt_to_equity"] is not None:
            result["debt_to_equity"] /= 100  # yfinance gives D/E * 100
        result["current_ratio"] = _safe_get(info, "currentRatio")
        result["quick_ratio"] = _safe_get(info, "quickRatio")
        result["total_debt"] = _safe_get(info, "totalDebt")
        result["total_cash"] = _safe_get(info, "totalCash")

        # ── Cash Flow ────────────────────────────────────
        result["free_cash_flow"] = _safe_get(info, "freeCashflow")
        result["operating_cash_flow"] = _safe_get(info, "operatingCashflow")
        result["revenue"] = _safe_get(info, "totalRevenue")
        result["net_income"] = _safe_get(info, "netIncomeToCommon")
        result["ebitda"] = _safe_get(info, "ebitda")

        # CFO / PAT
        if result["operating_cash_flow"] and result["net_income"]:
            try:
                result["cfo_pat"] = round(
                    result["operating_cash_flow"] / result["net_income"], 2
                )
            except ZeroDivisionError:
                result["cfo_pat"] = None
        else:
            result["cfo_pat"] = None

        # ── 52-Week High Distance ────────────────────────
        if result["current_price"] and result["fifty_two_week_high"]:
            try:
                result["pct_from_52w_high"] = round(
                    (1 - result["current_price"] / result["fifty_two_week_high"]) * 100, 2
                )
            except ZeroDivisionError:
                result["pct_from_52w_high"] = None
        else:
            result["pct_from_52w_high"] = None

        # ── Promoter / Major holders (best-effort) ──────
        result["promoter_holding"] = _fetch_promoter_holding(stock)

        # ── ROCE (calculated) ────────────────────────────
        result["roce"] = _calc_roce(info)

        # ── Interest coverage ────────────────────────────
        result["interest_coverage"] = _calc_interest_coverage(stock)

        # ── Growth CAGRs ─────────────────────────────────
        rev_cagr, eps_cagr, fcf_growth = _calc_growth(stock)
        result["revenue_cagr_5y"] = rev_cagr
        result["eps_cagr_5y"] = eps_cagr
        result["fcf_growth_yoy"] = fcf_growth

    except Exception as exc:  # noqa: BLE001
        logger.exception("Error fetching %s", ticker)
        result["error"] = str(exc)

    return result


# ──────────────────────────────────────────────────────────
# Multi-stock fetcher
# ──────────────────────────────────────────────────────────
def fetch_multiple_stocks(tickers: List[str]) -> pd.DataFrame:
    """Fetch data for a list of tickers and return a DataFrame."""
    rows: List[Dict[str, Any]] = []
    for t in tickers:
        rows.append(fetch_stock_data(t))
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────
# Price history for charts
# ──────────────────────────────────────────────────────────
def fetch_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Return OHLCV DataFrame for *ticker* over the given *period*."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        return hist
    except Exception:
        logger.exception("Price history error for %s", ticker)
        return pd.DataFrame()


# ──────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────
def _pct(info: Dict, key: str) -> Optional[float]:
    """Convert a 0-1 fraction from yfinance info to a percentage."""
    val = info.get(key)
    if val is None:
        return None
    return round(val * 100, 2)


def _fetch_promoter_holding(stock: yf.Ticker) -> Optional[float]:
    """Try to extract promoter / insider holding %."""
    try:
        holders = stock.major_holders
        if holders is not None and not holders.empty:
            # Row 0 is typically "% of Shares Held by All Insider"
            val = holders.iloc[0, 0]
            if isinstance(val, str):
                val = float(val.replace("%", "").strip())
            return round(float(val), 2)
    except Exception:
        pass
    return None


def _calc_roce(info: Dict[str, Any]) -> Optional[float]:
    """ROCE = EBIT / Capital Employed (approx)."""
    ebitda = info.get("ebitda")
    total_assets = info.get("totalAssets") or info.get("totalAssets")
    current_liabilities = info.get("totalCurrentLiabilities") or info.get("currentLiabilities")
    if ebitda and total_assets and current_liabilities:
        capital_employed = total_assets - current_liabilities
        if capital_employed > 0:
            return round((ebitda / capital_employed) * 100, 2)
    return None


def _calc_interest_coverage(stock: yf.Ticker) -> Optional[float]:
    """Interest Coverage = EBIT / Interest Expense."""
    try:
        fin = stock.financials
        if fin is None or fin.empty:
            return None

        ebit_row = None
        interest_row = None
        for label in ["EBIT", "Operating Income"]:
            if label in fin.index:
                ebit_row = label
                break
        for label in ["Interest Expense", "Interest Expense Non Operating"]:
            if label in fin.index:
                interest_row = label
                break

        if ebit_row and interest_row:
            ebit = fin.loc[ebit_row].dropna()
            interest = fin.loc[interest_row].dropna()
            if len(ebit) > 0 and len(interest) > 0:
                ie = abs(float(interest.iloc[0]))
                if ie > 0:
                    return round(float(ebit.iloc[0]) / ie, 2)
    except Exception:
        pass
    return None


def _calc_growth(stock: yf.Ticker):
    """
    Calculate 5-year revenue CAGR, EPS CAGR, and YoY FCF growth.
    Returns (rev_cagr, eps_cagr, fcf_growth) — each Optional[float].
    """
    rev_cagr: Optional[float] = None
    eps_cagr: Optional[float] = None
    fcf_growth: Optional[float] = None

    try:
        fin = stock.financials
        if fin is not None and not fin.empty:
            # Revenue CAGR
            for label in ["Total Revenue", "Revenue"]:
                if label in fin.index:
                    rev = fin.loc[label].dropna().sort_index()
                    if len(rev) >= 2:
                        first, last = float(rev.iloc[0]), float(rev.iloc[-1])
                        n = len(rev) - 1
                        if first > 0 and last > 0 and n > 0:
                            rev_cagr = round(((last / first) ** (1 / n) - 1) * 100, 2)
                    break

            # Net Income → EPS proxy CAGR
            for label in ["Net Income", "Net Income Common Stockholders"]:
                if label in fin.index:
                    ni = fin.loc[label].dropna().sort_index()
                    if len(ni) >= 2:
                        first, last = float(ni.iloc[0]), float(ni.iloc[-1])
                        n = len(ni) - 1
                        if first > 0 and last > 0 and n > 0:
                            eps_cagr = round(((last / first) ** (1 / n) - 1) * 100, 2)
                    break
    except Exception:
        pass

    try:
        cf = stock.cashflow
        if cf is not None and not cf.empty:
            for label in ["Free Cash Flow"]:
                if label in cf.index:
                    fcf = cf.loc[label].dropna().sort_index()
                    if len(fcf) >= 2:
                        prev, curr = float(fcf.iloc[-2]), float(fcf.iloc[-1])
                        if prev != 0:
                            fcf_growth = round(((curr - prev) / abs(prev)) * 100, 2)
                    break
    except Exception:
        pass

    return rev_cagr, eps_cagr, fcf_growth