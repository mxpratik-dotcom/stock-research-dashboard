"""
Configuration file for Indian Stock Research Dashboard.
Contains stock list, scoring thresholds, and display settings.
"""

from typing import Dict, List, TypedDict


class StockConfig(TypedDict):
    ticker: str
    name: str
    sector: str
    cap_size: str
    weight: float
    moat: str


# ──────────────────────────────────────────────
# Pre-configured portfolio: 13 stocks, 10 sectors
# ──────────────────────────────────────────────
DEFAULT_STOCKS: List[StockConfig] = [
    {
        "ticker": "HDFCBANK.NS",
        "name": "HDFC Bank",
        "sector": "Financials",
        "cap_size": "Large",
        "weight": 10.0,
        "moat": "Asset quality king",
    },
    {
        "ticker": "CHOLAFIN.NS",
        "name": "Cholamandalam Finance",
        "sector": "Financials",
        "cap_size": "Mid",
        "weight": 7.0,
        "moat": "Rural/vehicle lending",
    },
    {
        "ticker": "PERSISTENT.NS",
        "name": "Persistent Systems",
        "sector": "IT / AI",
        "cap_size": "Mid",
        "weight": 10.0,
        "moat": "Digital engineering",
    },
    {
        "ticker": "BEL.NS",
        "name": "Bharat Electronics (BEL)",
        "sector": "Defense",
        "cap_size": "Large",
        "weight": 8.0,
        "moat": "Order book fortress",
    },
    {
        "ticker": "NTPC.NS",
        "name": "NTPC",
        "sector": "Energy",
        "cap_size": "Large",
        "weight": 5.0,
        "moat": "Green pivot + dividends",
    },
    {
        "ticker": "WAAREEENER.NS",
        "name": "Waaree Energies",
        "sector": "Energy",
        "cap_size": "Mid",
        "weight": 5.0,
        "moat": "Solar manufacturing",
    },
    {
        "ticker": "THERMAX.NS",
        "name": "Thermax",
        "sector": "Capital Goods",
        "cap_size": "Mid",
        "weight": 7.0,
        "moat": "Green energy capex",
    },
    {
        "ticker": "APOLLOHOSP.NS",
        "name": "Apollo Hospitals",
        "sector": "Healthcare",
        "cap_size": "Large",
        "weight": 8.0,
        "moat": "Hospital + digital health",
    },
    {
        "ticker": "PIIND.NS",
        "name": "PI Industries",
        "sector": "Chemicals",
        "cap_size": "Mid",
        "weight": 8.0,
        "moat": "China+1, agchem CSM",
    },
    {
        "ticker": "KAYNES.NS",
        "name": "Kaynes Technology",
        "sector": "EMS",
        "cap_size": "Small-Mid",
        "weight": 6.0,
        "moat": "Defense + auto EMS",
    },
    {
        "ticker": "TRENT.NS",
        "name": "Trent (Zudio)",
        "sector": "Retail",
        "cap_size": "Large",
        "weight": 8.0,
        "moat": "Value fashion disruptor",
    },
    {
        "ticker": "SONACOMS.NS",
        "name": "Sona BLW",
        "sector": "Auto / EV",
        "cap_size": "Mid",
        "weight": 8.0,
        "moat": "EV drivetrain global",
    },
    {
        "ticker": "WABAG.NS",
        "name": "VA Tech Wabag",
        "sector": "Water",
        "cap_size": "Small-Mid",
        "weight": 5.0,
        "moat": "Water scarcity theme",
    },
]

# ──────────────────────────────────────────────
# 10-point scoring thresholds
# ──────────────────────────────────────────────
SCORING_THRESHOLDS: Dict[str, float] = {
    "roe_min": 15.0,              # ROE > 15 %
    "revenue_cagr_min": 12.0,     # Revenue CAGR > 12 %
    "eps_cagr_min": 12.0,         # EPS CAGR > 12 %
    "de_max": 0.5,                # D/E < 0.5
    "cfo_pat_min": 1.0,           # CFO / PAT > 1
    "promoter_holding_min": 50.0, # Promoter holding > 50 %
    "peg_max": 1.0,               # PEG < 1
    "current_ratio_min": 1.5,     # Current Ratio > 1.5
    "net_margin_min": 10.0,       # Net Profit Margin > 10 %
}

# ──────────────────────────────────────────────
# Opportunity-zone colour bands
# ─────────────────────────────────��────────────
OPPORTUNITY_ZONES = {
    "near_high": {"max_pct": 10, "color": "#2ecc71", "label": "🟢 Near High"},
    "mild_correction": {"max_pct": 20, "color": "#f39c12", "label": "🟡 Mild Correction"},
    "deep_correction": {"max_pct": 100, "color": "#e74c3c", "label": "🔴 Deep Correction"},
}

# Cache TTL in seconds (1 hour)
CACHE_TTL: int = 3600

# yfinance history periods for price charts
CHART_PERIODS = {"1Y": "1y", "3Y": "3y", "5Y": "5y", "Max": "max"}