"""
dashboard.py
------------
Streamlit dashboard — MACD signal explorer.
Run with: streamlit run dashboard.py
"""

import glob
import os
import pandas as pd
import numpy as np

try:
    import streamlit as st
except ImportError:
    raise ImportError("Run: pip install streamlit")

st.set_page_config(page_title="MACD Signal Scanner", page_icon="📊", layout="wide")

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")

# ── Helpers ───────────────────────────────────────────────────────────────────
def pct(v, decimals=1):
    try:
        return f"{float(v)*100:.{decimals}f}%" if pd.notna(v) else "n/a"
    except:
        return "n/a"

def color_signal(val):
    if val == "LONG":  return "background-color: #1a472a; color: #a3d9a5; font-weight: bold"
    if val == "SHORT": return "background-color: #4a1a1a; color: #f4a8a8; font-weight: bold"
    return ""

def color_winrate(val):
    try:
        v = float(str(val).replace("%","")) / 100
        if v >= 0.70: return "color: #4caf50; font-weight: bold"
        if v >= 0.60: return "color: #8bc34a"
        if v >= 0.50: return "color: #ff9800"
        return "color: #f44336"
    except: return ""

def color_edge(val):
    try:
        v = float(str(val).replace("%",""))
        if v >= 3:  return "color: #4caf50; font-weight: bold"
        if v >= 0:  return "color: #8bc34a"
        if v >= -3: return "color: #ff9800"
        return "color: #f44336"
    except: return ""

def color_return(val):
    try:
        v = float(str(val).replace("%",""))
        if v > 0: return "color: #4caf50"
        if v < 0: return "color: #f44336"
    except: return ""
    return ""

def color_expectancy(val):
    try:
        v = float(str(val).replace("%",""))
        if v >= 15: return "color: #4caf50; font-weight: bold"
        if v >= 8:  return "color: #8bc34a"
        if v >= 4:  return "color: #ff9800"
        return "color: #f44336"
    except: return ""

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_latest_results():
    csvs = sorted(glob.glob(os.path.join(RESULTS_DIR, "signal_stats_*.csv")))
    if not csvs: return None, None
    latest = csvs[-1]
    return pd.read_csv(latest, index_col=0), latest

# ── Title ─────────────────────────────────────────────────────────────────────
st.title("📊 MACD Signal Scanner")
st.caption("Weekly MACD(12,26,9) — State-based | Ranked by Combined Expectancy")

df, filepath = load_latest_results()
if df is None:
    st.error(f"No results in `{RESULTS_DIR}`. Run `python main.py --backtest` first.")
    st.stop()

col_info, col_refresh = st.columns([4, 1])
with col_info:
    tf = df['timeframe'].iloc[0] if 'timeframe' in df.columns else 'n/a'
    st.caption(f"📁 `{os.path.basename(filepath)}`  |  **{len(df)} tickers**  |  Timeframe: **{tf}**")
with col_refresh:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

_macd   = df['macd_params'].iloc[0]  if 'macd_params'      in df.columns else 'n/a'
_tf     = df['timeframe'].iloc[0]    if 'timeframe'         in df.columns else 'n/a'
_lhold  = f"{int(df['long_hold_bars'].iloc[0])}W"  if 'long_hold_bars'  in df.columns else 'see config'
_shold  = f"{int(df['short_hold_bars'].iloc[0])}W" if 'short_hold_bars' in df.columns else 'see config'
st.caption(f"⚙️ MACD({_macd}) | Timeframe: {_tf} | Long hold: {_lhold} | Short hold: {_shold}")

# ── Strategy overview ─────────────────────────────────────────────────────────
st.info("""
**Strategy Overview**

This dashboard tracks weekly MACD(12,26,9) histogram signals across a watchlist of stocks and ETFs.

📈 **LONG signal:** MACD histogram turns positive → historical analysis of price behaviour over 12 weeks \n
📉 **SHORT signal:** MACD histogram turns negative → historical analysis of price behaviour over 3 weeks

**How to interpret the stats:**
- **Win Rate** alone is misleading — a stock that goes up 70% of all weeks will show 70% win rate even with no signal
- **HitEdge** is more meaningful — it measures how much BETTER the signal performs vs just buying/selling randomly every week
- Positive HitEdge = signal genuinely adds value above market drift
- Negative HitEdge = signal underperforms random — ignore it for that ticker
- **MagEdge** = signal weeks produce larger moves than average weeks
""")
st.warning("⚠️ **Disclaimer:** These are statistical observations from historical data, not a full backtest or forward prediction. Past performance does not guarantee future results. This is not financial advice.")

# ── How to read ───────────────────────────────────────────────────────────────
with st.expander("ℹ️ How to read the scores", expanded=False):
    st.markdown("""
    | Column | Formula | Meaning |
    |---|---|---|
    | **Long Win Rate** | rise_n / total | % of long-state bars where price rose after 12W |
    | **Short Win Rate** | fall_n / total | % of short-state bars where price fell after hold period |
    | **L: Base** | unconditional | % of ALL bars where price rose over 12W (no signal) |
    | **S: Base** | unconditional | % of ALL bars where price fell over hold period (no signal) |
    | **HitEdge** | Win Rate - Base Rate | Does signal pick better weeks than random? |
    | **MagEdge** | Signal Mean - Base Mean | Does signal pick weeks that move MORE than random? |
    | **Combined Exp** | (Long Mean + \|Short Mean\|) / 2 | Overall signal strength |

    **Positive HitEdge** = signal identifies good timing better than chance
    **Positive MagEdge** = signal weeks produce larger moves than average
    **Negative edge** = signal underperforms random — avoid for that side
    """)

st.divider()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🔧 Filters")

    signal_filter = st.radio(
        "Signal State", ["All", "LONG only", "SHORT only", "Active only"], index=0
    )
    min_long_wr      = st.slider("Min Long Win Rate",       0, 100,  0, 5, format="%d%%")
    min_short_wr     = st.slider("Min Short Win Rate",      0, 100,  0, 5, format="%d%%")
    min_long_edge    = st.slider("Min Long HitEdge",      -20,  20,-20, 1, format="%d%%")
    min_combined_exp = st.slider("Min Combined Expectancy", 0,  30,  0, 1, format="%d%%")

    st.divider()
    st.header("📋 Display Options")
    show_mag_edge   = st.checkbox("Show Magnitude Edge",   value=True)
    show_base_rates = st.checkbox("Show Base Rates",       value=False)
    show_pre_event  = st.checkbox("Show Pre-event Stats",  value=False)
    show_raw_macd   = st.checkbox("Show Raw MACD Values",  value=False)

# ── Apply filters ─────────────────────────────────────────────────────────────
filtered = df.copy()
if signal_filter == "LONG only":   filtered = filtered[filtered["active_signal"] == "LONG"]
elif signal_filter == "SHORT only": filtered = filtered[filtered["active_signal"] == "SHORT"]
elif signal_filter == "Active only": filtered = filtered[filtered["active_signal"] != "NONE"]
if "long_win_rate"      in filtered.columns: filtered = filtered[filtered["long_win_rate"].fillna(0)      >= min_long_wr / 100]
if "short_win_rate"     in filtered.columns: filtered = filtered[filtered["short_win_rate"].fillna(0)     >= min_short_wr / 100]
if "long_edge"          in filtered.columns: filtered = filtered[filtered["long_edge"].fillna(0)          >= min_long_edge / 100]
if "combined_expectancy" in filtered.columns: filtered = filtered[filtered["combined_expectancy"].fillna(0) >= min_combined_exp / 100]

# ── Section 1: Active signal summary ─────────────────────────────────────────
st.subheader("🔔 Current Signal State")
if "active_signal" in df.columns:
    long_rows  = df[df["active_signal"] == "LONG"]
    short_rows = df[df["active_signal"] == "SHORT"]
    none_rows  = df[df["active_signal"] == "NONE"]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("📈 LONG (histogram +)", len(long_rows))
        if not long_rows.empty:
            top = long_rows.sort_values("long_edge", ascending=False)
            st.caption(" · ".join(
                f"{r['symbol']}({pct(r.get('long_edge'))})"
                for _, r in top.iterrows()
            ))
            st.caption("_% = HitEdge vs base rate · positive = signal adds value · negative = worse than random_")
    with c2:
        st.metric("📉 SHORT (histogram -)", len(short_rows))
        if not short_rows.empty:
            top = short_rows.sort_values("short_edge", ascending=False)
            st.caption(" · ".join(
                f"{r['symbol']}({pct(r.get('short_edge'))})"
                for _, r in top.iterrows()
            ))
            st.caption("_% = HitEdge vs base rate · positive = signal adds value · negative = worse than random_")
    with c3:
        st.metric("⬜ Neutral", len(none_rows))
        if not none_rows.empty:
            st.caption(" · ".join(none_rows["symbol"].tolist()))

st.divider()

# ── Section 2: Rankings table ─────────────────────────────────────────────────
st.subheader(f"📊 Rankings  ({len(filtered)} tickers)")

if filtered.empty:
    st.info("No tickers match the current filters.")
else:
    display = pd.DataFrame()
    display["Ticker"]       = filtered["symbol"]
    display["State"]        = filtered["active_signal"]
    display["Score"]        = filtered["combined_expectancy"].apply(pct)

    # Long side
    display["L: WinRate"]  = filtered["long_win_rate"].apply(pct)
    display["L: HitEdge"]  = filtered["long_edge"].apply(pct)
    if show_mag_edge:
        display["L: MagEdge"] = filtered["long_mag_edge"].apply(pct) if "long_mag_edge" in filtered.columns else "n/a"
    if show_base_rates:
        display["L: Base"]    = filtered["base_long_rise_rate"].apply(pct) if "base_long_rise_rate" in filtered.columns else "n/a"
    display["L: Mean"]     = filtered["long_post_mean_total"].apply(pct)
    display["L: +1SD"]     = filtered["long_plus1sd"].apply(pct)
    display["L: -1SD"]     = filtered["long_minus1sd"].apply(pct)

    # Short side
    display["S: WinRate"]  = filtered["short_win_rate"].apply(pct)
    display["S: HitEdge"]  = filtered["short_edge"].apply(pct)
    if show_mag_edge:
        display["S: MagEdge"] = filtered["short_mag_edge"].apply(pct) if "short_mag_edge" in filtered.columns else "n/a"
    if show_base_rates:
        display["S: Base"]    = filtered["base_short_fall_rate"].apply(pct) if "base_short_fall_rate" in filtered.columns else "n/a"
    display["S: Mean"]     = filtered["short_post_mean_total"].apply(pct)
    display["S: +1SD"]     = filtered["short_plus1sd"].apply(pct)
    display["S: -1SD"]     = filtered["short_minus1sd"].apply(pct)

    if show_pre_event:
        display["L: PreMean"] = filtered["long_pre_mean"].apply(pct)
        display["S: PreMean"] = filtered["short_pre_mean"].apply(pct)
    if show_raw_macd:
        display["Histogram"]  = filtered["current_diff"]
        display["MACD"]       = filtered["current_macd"]
        display["SigLine"]    = filtered["current_signal"]

    display = display.reset_index(drop=True)
    display.index += 1
    display.index.name = "Rank"

    edge_cols = [c for c in ["L: HitEdge","L: MagEdge","S: HitEdge","S: MagEdge"] if c in display.columns]
    styled = display.style\
        .map(color_signal,      subset=["State"])\
        .map(color_expectancy,  subset=["Score"])\
        .map(color_winrate,     subset=["L: WinRate", "S: WinRate"])\
        .map(color_edge,        subset=edge_cols)\
        .map(color_return,      subset=["L: Mean","S: Mean","L: +1SD","S: +1SD","L: -1SD","S: -1SD"])

    st.dataframe(styled, use_container_width=True, height=600)

st.divider()

# ── Section 3: Ticker detail ──────────────────────────────────────────────────
st.subheader("🔍 Ticker Detail")
all_symbols = sorted(df["symbol"].unique().tolist())
selected = st.selectbox("Select a ticker", all_symbols)

if selected:
    row = df[df["symbol"] == selected].iloc[0]
    sig      = row.get("active_signal", "NONE")
    sig_icon = "🟢" if sig == "LONG" else ("🔴" if sig == "SHORT" else "⬜")

    st.markdown(f"### {selected}  {sig_icon} **{sig}**")
    st.caption(
        f"MACD: `{row.get('current_macd','n/a')}`  "
        f"Signal: `{row.get('current_signal','n/a')}`  "
        f"Histogram: `{row.get('current_diff','n/a')}`"
    )

    # Edge summary banner
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Long HitEdge",  pct(row.get("long_edge")),      help="Long win rate vs base rise rate")
    e2.metric("Long MagEdge",  pct(row.get("long_mag_edge")),  help="Long mean return vs unconditional mean")
    e3.metric("Short HitEdge", pct(row.get("short_edge")),     help="Short win rate vs base fall rate")
    e4.metric("Short MagEdge", pct(row.get("short_mag_edge")), help="Short mean return vs unconditional mean")

    st.caption(
        f"Base rise rate (12W, no signal): **{pct(row.get('base_long_rise_rate'))}**  |  "
        f"Base fall rate (hold period, no signal): **{pct(row.get('base_short_fall_rate'))}**  |  "
        f"Base long mean: **{pct(row.get('base_long_mean'))}**  |  "
        f"Base short mean: **{pct(row.get('base_short_mean'))}**"
    )

    st.divider()
    col_long, col_short = st.columns(2)

    def stat_rows(stats):
        for k, v in stats.items():
            if v == "": st.caption(k)
            else: st.text(f"  {k:<32} {v}")

    with col_long:
        st.markdown("#### 📈 LONG State  *(histogram > 0)*")
        stat_rows({
            "# Observations":           int(row.get("long_total_events", 0)),
            "  Rise (price up)":        int(row.get("long_rise_n", 0)),
            "  Fall (price down)":      int(row.get("long_fall_n", 0)),
            "Win Rate":                 pct(row.get("long_win_rate")),
            "Hit Edge vs Base":         pct(row.get("long_edge")),
            "── Post-event (12W) ──":   "",
            "Mean (Rise)":              pct(row.get("long_post_mean_rise")),
            "Mean (Fall)":              pct(row.get("long_post_mean_fall")),
            "Mean (Total)":             pct(row.get("long_post_mean_total")),
            "Magnitude Edge vs Base":   pct(row.get("long_mag_edge")),
            "+1 Std Dev":               pct(row.get("long_plus1sd")),
            "-1 Std Dev":               pct(row.get("long_minus1sd")),
            "Max Change":               pct(row.get("long_post_max")),
            "Min Change":               pct(row.get("long_post_min")),
            "── Pre-event (5W) ──":     "",
            "Pre-event Mean":           pct(row.get("long_pre_mean")),
            "+1 Std Dev":               pct(row.get("long_pre_plus1sd")),
            "-1 Std Dev":               pct(row.get("long_pre_minus1sd")),
        })

    with col_short:
        st.markdown("#### 📉 SHORT State  *(histogram < 0)*")
        stat_rows({
            "# Observations":           int(row.get("short_total_events", 0)),
            "  Rise (price up)":        int(row.get("short_rise_n", 0)),
            "  Fall (price down)":      int(row.get("short_fall_n", 0)),
            "Win Rate (Fall/Total)":    pct(row.get("short_win_rate")),
            "Hit Edge vs Base":         pct(row.get("short_edge")),
            "── Post-event (hold) ──":  "",
            "Mean (Rise)":              pct(row.get("short_post_mean_rise")),
            "Mean (Fall)":              pct(row.get("short_post_mean_fall")),
            "Mean (Total)":             pct(row.get("short_post_mean_total")),
            "Magnitude Edge vs Base":   pct(row.get("short_mag_edge")),
            "+1 Std Dev":               pct(row.get("short_plus1sd")),
            "-1 Std Dev":               pct(row.get("short_minus1sd")),
            "Max Change":               pct(row.get("short_post_max")),
            "Min Change":               pct(row.get("short_post_min")),
            "── Pre-event (5W) ──":     "",
            "Pre-event Mean":           pct(row.get("short_pre_mean")),
            "+1 Std Dev":               pct(row.get("short_pre_plus1sd")),
            "-1 Std Dev":               pct(row.get("short_pre_minus1sd")),
        })

st.divider()

# ── Section 4: Download ───────────────────────────────────────────────────────
st.subheader("⬇ Export")
c1, c2 = st.columns(2)
with c1:
    st.download_button("Download full results (CSV)",     df.to_csv().encode("utf-8"),       "macd_full.csv",     "text/csv")
with c2:
    st.download_button("Download filtered results (CSV)", filtered.to_csv().encode("utf-8"), "macd_filtered.csv", "text/csv")
