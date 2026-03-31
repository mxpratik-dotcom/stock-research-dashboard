"""
Indian Stock Research Dashboard — Streamlit App
Fetches LIVE data from Yahoo Finance; no hard-coded prices.
"""

from __future__ import annotations

import io
import time
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import (
    CACHE_TTL,
    CHART_PERIODS,
    DEFAULT_STOCKS,
    OPPORTUNITY_ZONES,
    StockConfig,
)
from data_fetcher import fetch_multiple_stocks, fetch_price_history, fetch_stock_data
from portfolio_analyzer import (
    opportunity_color,
    opportunity_zone,
    portfolio_summary,
    score_color,
    score_label,
    score_stock,
)
from stock_screener import (
    filter_stocks,
    fmt,
    fmt_cr,
    fmt_mcap,
    get_cashflow_metrics,
    get_growth_ratios,
    get_leverage_ratios,
    get_profitability_ratios,
    get_quality_checks,
    get_valuation_ratios,
)

# ─────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="📊 Indian Stock Research Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────
# Session-state initialisation
# ─────────────────────────────────────────────────────────
if "stocks" not in st.session_state:
    st.session_state["stocks"] = list(DEFAULT_STOCKS)
if "data_ts" not in st.session_state:
    st.session_state["data_ts"] = 0.0


def _stock_list() -> List[StockConfig]:
    return st.session_state["stocks"]


# ─────────────────────────────────────────────────────────
# Cached data loader
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_data(tickers_key: str) -> pd.DataFrame:
    """Fetch & score all stocks. *tickers_key* is used for cache-busting."""
    stocks = _stock_list()
    tickers = [s["ticker"] for s in stocks]
    df = fetch_multiple_stocks(tickers)

    # Merge config metadata
    meta = pd.DataFrame(stocks)
    df = df.merge(meta, on="ticker", how="left")

    # Score each stock
    scores: List[int] = []
    for _, row in df.iterrows():
        s, _ = score_stock(row.to_dict())
        scores.append(s)
    df["score"] = scores

    return df


def _tickers_key() -> str:
    """Deterministic key so Streamlit cache refreshes when stock list changes."""
    return "|".join(sorted(s["ticker"] for s in _stock_list()))


# ─────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 Stock Dashboard")
    st.markdown("**Live data via Yahoo Finance**")
    st.markdown("---")

    if st.button("🔄 Refresh All Data", use_container_width=True):
        load_data.clear()
        st.rerun()

    st.markdown("---")
    st.subheader("➕ Add a Stock")
    with st.form("add_stock_form"):
        new_ticker = st.text_input("NSE Ticker (e.g. RELIANCE.NS)")
        new_name = st.text_input("Company Name")
        new_sector = st.text_input("Sector")
        new_cap = st.selectbox("Cap Size", ["Large", "Mid", "Small-Mid"])
        new_weight = st.number_input("Weight %", 1.0, 25.0, 5.0, 1.0)
        new_moat = st.text_input("Key Moat (short)")
        submitted = st.form_submit_button("Add Stock")
        if submitted and new_ticker and new_name:
            ticker_clean = new_ticker.strip().upper()
            if not ticker_clean.endswith(".NS"):
                ticker_clean += ".NS"
            existing = {s["ticker"] for s in _stock_list()}
            if ticker_clean in existing:
                st.warning("Already in watchlist!")
            else:
                st.session_state["stocks"].append(
                    StockConfig(
                        ticker=ticker_clean,
                        name=new_name.strip(),
                        sector=new_sector.strip() or "Other",
                        cap_size=new_cap,
                        weight=new_weight,
                        moat=new_moat.strip() or "—",
                    )
                )
                load_data.clear()
                st.success(f"Added {ticker_clean}")
                st.rerun()

    st.markdown("---")
    st.subheader("➖ Remove a Stock")
    stock_names = [s["name"] for s in _stock_list()]
    to_remove = st.selectbox("Select stock to remove", ["—"] + stock_names)
    if st.button("Remove", use_container_width=True) and to_remove != "—":
        st.session_state["stocks"] = [
            s for s in _stock_list() if s["name"] != to_remove
        ]
        load_data.clear()
        st.success(f"Removed {to_remove}")
        st.rerun()

    st.markdown("---")
    st.caption(
        "⚠️ **Disclaimer:** This tool is for educational purposes only. "
        "Not financial advice. Consult a SEBI-registered advisor."
    )

# ─────────────────────────────────────────────────────────
# Load data
# ─────────────────────────────────────────────────────────
with st.spinner("Fetching live market data … ☕"):
    df = load_data(_tickers_key())

# ─────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📋 Portfolio Overview",
        "🔬 Detailed Analysis",
        "🔍 Screening & Filtering",
        "🎯 Opportunity Radar",
        "📤 Export & Reports",
    ]
)

# ═════════════════════════════════════════════════════════
# TAB 1 — Portfolio Overview
# ═════════════════════════════════════════════════════════
with tab1:
    st.header("📋 Model Portfolio Summary")

    display_cols = {
        "#": [],
        "Sector": [],
        "Stock": [],
        "Cap Size": [],
        "Weight (%)": [],
        "Key Moat": [],
        "CMP (₹)": [],
        "52W High (₹)": [],
        "% from 52W High": [],
        "Score (/10)": [],
        "Verdict": [],
    }

    for idx, (_, row) in enumerate(df.iterrows(), 1):
        display_cols["#"].append(idx)
        display_cols["Sector"].append(row.get("sector", "—"))
        display_cols["Stock"].append(row.get("name", row["ticker"]))
        display_cols["Cap Size"].append(row.get("cap_size", "—"))
        display_cols["Weight (%)"].append(row.get("weight", 0))
        display_cols["Key Moat"].append(row.get("moat", "—"))
        display_cols["CMP (₹)"].append(fmt(row.get("current_price"), decimals=2))
        display_cols["52W High (₹)"].append(fmt(row.get("fifty_two_week_high"), decimals=2))

        pct = row.get("pct_from_52w_high")
        if pct is not None and not pd.isna(pct):
            zone = opportunity_zone(pct)
            display_cols["% from 52W High"].append(f"{pct:.1f}%  {zone}")
        else:
            display_cols["% from 52W High"].append("—")

        sc = row.get("score", 0)
        display_cols["Score (/10)"].append(int(sc) if not pd.isna(sc) else 0)
        display_cols["Verdict"].append(score_label(int(sc) if not pd.isna(sc) else 0))

    summary_df = pd.DataFrame(display_cols)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    # ── Charts ───────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Sector Allocation")
        if "sector" in df.columns and "weight" in df.columns:
            sector_df = df.groupby("sector")["weight"].sum().reset_index()
            fig = px.pie(
                sector_df,
                values="weight",
                names="sector",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_layout(margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Cap Size Distribution")
        if "cap_size" in df.columns and "weight" in df.columns:
            cap_df = df.groupby("cap_size")["weight"].sum().reset_index()
            fig = px.bar(
                cap_df,
                x="cap_size",
                y="weight",
                color="cap_size",
                text="weight",
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig.update_layout(
                xaxis_title="Cap Size",
                yaxis_title="Weight %",
                showlegend=False,
                margin=dict(t=20, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── Portfolio Stats ──────────────────────────────────
    st.subheader("Portfolio Statistics")
    ps = portfolio_summary(df)
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Stocks", ps.get("total_stocks", 0))
    m2.metric("Sectors", ps.get("sectors", 0))
    avg_roe = ps.get("avg_roe")
    m3.metric("Avg ROE", f"{avg_roe:.1f}%" if avg_roe and not pd.isna(avg_roe) else "—")
    avg_de = ps.get("avg_debt_to_equity")
    m4.metric("Avg D/E", f"{avg_de:.2f}" if avg_de and not pd.isna(avg_de) else "—")
    avg_sc = ps.get("avg_score")
    m5.metric("Avg Score", f"{avg_sc:.1f}/10" if avg_sc and not pd.isna(avg_sc) else "—")


# ═════════════════════════════════════════════════════════
# TAB 2 — Detailed Analysis
# ═════════════════════════════════════════════════════════
with tab2:
    st.header("🔬 Detailed Stock Analysis")

    stock_options = {row.get("name", row["ticker"]): row["ticker"] for _, row in df.iterrows()}
    selected_name = st.selectbox("Select a stock", list(stock_options.keys()))
    selected_ticker = stock_options[selected_name]
    row = df[df["ticker"] == selected_ticker].iloc[0].to_dict()

    # Header metrics
    hc1, hc2, hc3, hc4 = st.columns(4)
    hc1.metric("Current Price", f"₹{fmt(row.get('current_price'))}")
    hc2.metric("52W High", f"₹{fmt(row.get('fifty_two_week_high'))}")
    pct_down = row.get("pct_from_52w_high")
    hc3.metric("% from 52W High", f"{pct_down:.1f}%" if pct_down else "—")
    sc = int(row.get("score", 0))
    hc4.metric("Score", f"{sc}/10  {score_label(sc)}")

    st.markdown("---")

    # Ratio tables
    r1, r2 = st.columns(2)
    with r1:
        st.subheader("📊 Valuation Ratios")
        st.table(pd.DataFrame(get_valuation_ratios(row).items(), columns=["Ratio", "Value"]))

        st.subheader("💪 Profitability")
        st.table(pd.DataFrame(get_profitability_ratios(row).items(), columns=["Ratio", "Value"]))

        st.subheader("📈 Growth")
        st.table(pd.DataFrame(get_growth_ratios(row).items(), columns=["Ratio", "Value"]))

    with r2:
        st.subheader("🏦 Leverage & Solvency")
        st.table(pd.DataFrame(get_leverage_ratios(row).items(), columns=["Ratio", "Value"]))

        st.subheader("💰 Cash Flow")
        st.table(pd.DataFrame(get_cashflow_metrics(row).items(), columns=["Ratio", "Value"]))

        st.subheader("✅ Quality Checks")
        st.table(pd.DataFrame(get_quality_checks(row).items(), columns=["Check", "Value"]))

    # 10-point checklist
    st.markdown("---")
    st.subheader("🏆 10-Point Value Investor Checklist")
    _, checks = score_stock(row)
    check_df = pd.DataFrame(checks)
    check_df.columns = ["Criterion", "Passed", "Detail"]
    check_df["Result"] = check_df["Passed"].map({True: "✅ PASS", False: "❌ FAIL"})
    st.dataframe(
        check_df[["Criterion", "Result", "Detail"]],
        use_container_width=True,
        hide_index=True,
    )

    # Price chart
    st.markdown("---")
    st.subheader("📈 Price Chart")
    period_label = st.radio("Period", list(CHART_PERIODS.keys()), horizontal=True)
    period = CHART_PERIODS[period_label]
    with st.spinner("Loading chart…"):
        hist = fetch_price_history(selected_ticker, period)
    if not hist.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=hist.index,
                y=hist["Close"],
                mode="lines",
                name="Close",
                line=dict(color="#3498db", width=2),
            )
        )
        fig.update_layout(
            yaxis_title="Price (₹)",
            xaxis_title="Date",
            template="plotly_dark",
            height=400,
            margin=dict(t=20, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Price history not available for this ticker.")


# ═════════════════════════════════════════════════════════
# TAB 3 — Screening & Filtering
# ═════════════════════════════════════════════════════════
with tab3:
    st.header("🔍 Screening & Filtering")

    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        roe_range = st.slider("ROE %", 0.0, 60.0, (0.0, 60.0))
    with fc2:
        de_range = st.slider("D/E", 0.0, 5.0, (0.0, 5.0), 0.1)
    with fc3:
        all_sectors = sorted(df["sector"].dropna().unique().tolist())
        sel_sectors = st.multiselect("Sectors", all_sectors, default=all_sectors)
    with fc4:
        score_range = st.slider("Score (/10)", 0, 10, (0, 10))

    filtered = filter_stocks(
        df,
        roe_min=roe_range[0],
        roe_max=roe_range[1],
        de_min=de_range[0],
        de_max=de_range[1],
        sectors=sel_sectors,
        score_min=score_range[0],
        score_max=score_range[1],
    )

    st.caption(f"Showing {len(filtered)} of {len(df)} stocks")

    screen_cols = [
        "name", "sector", "current_price", "pe_ratio", "pb_ratio",
        "roe", "roce", "debt_to_equity", "net_margin",
        "revenue_cagr_5y", "pct_from_52w_high", "score",
    ]
    existing = [c for c in screen_cols if c in filtered.columns]
    st.dataframe(
        filtered[existing].rename(
            columns={
                "name": "Stock",
                "sector": "Sector",
                "current_price": "CMP (₹)",
                "pe_ratio": "P/E",
                "pb_ratio": "P/B",
                "roe": "ROE %",
                "roce": "ROCE %",
                "debt_to_equity": "D/E",
                "net_margin": "Margin %",
                "revenue_cagr_5y": "Rev CAGR %",
                "pct_from_52w_high": "% from 52WH",
                "score": "Score",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    # Sort helper
    sort_col = st.selectbox(
        "Sort by",
        ["score", "roe", "debt_to_equity", "pct_from_52w_high", "pe_ratio", "revenue_cagr_5y"],
    )
    ascending = st.checkbox("Ascending", value=False)
    if sort_col in filtered.columns:
        st.dataframe(
            filtered[existing]
            .sort_values(sort_col, ascending=ascending)
            .rename(
                columns={
                    "name": "Stock",
                    "sector": "Sector",
                    "current_price": "CMP (₹)",
                    "pe_ratio": "P/E",
                    "pb_ratio": "P/B",
                    "roe": "ROE %",
                    "roce": "ROCE %",
                    "debt_to_equity": "D/E",
                    "net_margin": "Margin %",
                    "revenue_cagr_5y": "Rev CAGR %",
                    "pct_from_52w_high": "% from 52WH",
                    "score": "Score",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


# ═════════════════════════════════════════════════════════
# TAB 4 — Opportunity Radar
# ═════════════════════════════════════════════════════════
with tab4:
    st.header("🎯 Opportunity Radar")

    # Horizontal bar — % from 52W High
    st.subheader("📉 Distance from 52-Week High")
    radar_df = df[["name", "pct_from_52w_high", "score"]].dropna(subset=["pct_from_52w_high"]).copy()
    radar_df = radar_df.sort_values("pct_from_52w_high", ascending=True)
    radar_df["color"] = radar_df["pct_from_52w_high"].apply(opportunity_color)
    radar_df["zone"] = radar_df["pct_from_52w_high"].apply(opportunity_zone)

    fig = go.Figure(
        go.Bar(
            y=radar_df["name"],
            x=radar_df["pct_from_52w_high"],
            orientation="h",
            marker_color=radar_df["color"],
            text=radar_df["pct_from_52w_high"].apply(lambda x: f"{x:.1f}%"),
            textposition="outside",
        )
    )
    fig.update_layout(
        xaxis_title="% Down from 52-Week High",
        yaxis_title="",
        template="plotly_dark",
        height=max(400, len(radar_df) * 40),
        margin=dict(l=200, t=20, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Opportunity zone table
    st.subheader("🚦 Opportunity Zone Classification")
    zone_df = radar_df[["name", "pct_from_52w_high", "zone", "score"]].copy()
    zone_df.columns = ["Stock", "% from 52W High", "Zone", "Score (/10)"]
    st.dataframe(zone_df, use_container_width=True, hide_index=True)

    # Best-buy alert
    st.subheader("🔔 Best Buy Alerts (>25% down & Score ≥ 7)")
    best = radar_df[(radar_df["pct_from_52w_high"] >= 25) & (radar_df["score"] >= 7)]
    if best.empty:
        st.info("No stocks currently meet the best-buy criteria.")
    else:
        for _, r in best.iterrows():
            st.success(
                f"🎯 **{r['name']}** — {r['pct_from_52w_high']:.1f}% below 52W High | "
                f"Score: {int(r['score'])}/10"
            )

    # Heatmap
    st.subheader("🗺️ Ratio Heatmap")
    heatmap_cols = ["roe", "roce", "debt_to_equity", "net_margin", "pe_ratio", "peg_ratio", "pct_from_52w_high", "score"]
    hm_existing = [c for c in heatmap_cols if c in df.columns]
    hm_df = df.set_index("name")[hm_existing].dropna(how="all")
    if not hm_df.empty:
        # Normalise for colour scaling
        hm_norm = (hm_df - hm_df.min()) / (hm_df.max() - hm_df.min() + 1e-9)
        fig = px.imshow(
            hm_norm,
            labels=dict(x="Metric", y="Stock", color="Normalised"),
            text_auto=False,
            aspect="auto",
            color_continuous_scale="RdYlGn",
        )
        # overlay actual values
        for i, stock in enumerate(hm_df.index):
            for j, col in enumerate(hm_df.columns):
                val = hm_df.loc[stock, col]
                fig.add_annotation(
                    x=j, y=i,
                    text=f"{val:.1f}" if not pd.isna(val) else "—",
                    showarrow=False,
                    font=dict(size=10, color="white"),
                )
        fig.update_layout(height=max(400, len(hm_df) * 35), margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough data for heatmap.")


# ═════════════════════════════════════════════════════════
# TAB 5 — Export & Reports
# ═════════════════════════════════════════════════════════
with tab5:
    st.header("📤 Export & Reports")

    st.subheader("📄 Export to CSV")
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    st.download_button(
        "⬇️ Download CSV",
        csv_buffer.getvalue(),
        file_name="stock_research_report.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.subheader("📊 Export to Excel")
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Portfolio", index=False)
        # Summary sheet
        ps = portfolio_summary(df)
        summary_items = pd.DataFrame(
            [(k, str(v)) for k, v in ps.items()], columns=["Metric", "Value"]
        )
        summary_items.to_excel(writer, sheet_name="Summary", index=False)
    st.download_button(
        "⬇️ Download Excel",
        excel_buffer.getvalue(),
        file_name="stock_research_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    st.markdown("---")
    st.subheader("📋 Summary Report")
    ps = portfolio_summary(df)
    st.markdown(f"""
| Metric | Value |
|---|---|
| Total Stocks | {ps.get('total_stocks', 0)} |
| Sectors Covered | {ps.get('sectors', 0)} |
| Avg ROE | {ps.get('avg_roe', 0):.1f}% |
| Avg D/E | {ps.get('avg_debt_to_equity', 0):.2f} |
| Avg Score | {ps.get('avg_score', 0):.1f}/10 |
| Avg % from 52W High | {ps.get('avg_pct_from_52w_high', 0):.1f}% |
""")

    if "cap_distribution" in ps:
        st.markdown("**Cap Size Distribution:**")
        for cap, count in ps["cap_distribution"].items():
            st.markdown(f"- {cap}: {count} stocks")

    if "sector_weights" in ps:
        st.markdown("**Sector Weights:**")
        for sec, w in sorted(ps["sector_weights"].items(), key=lambda x: -x[1]):
            st.markdown(f"- {sec}: {w:.0f}%")

    st.markdown("---")
    st.info(
        "⚠️ **Disclaimer:** This dashboard is for educational & informational purposes only. "
        "It is NOT financial advice. Always consult a SEBI-registered investment advisor "
        "before making investment decisions."
    )