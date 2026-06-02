"""
dashboard.py
------------
Streamlit dashboard — MACD signal explorer.
Run with: streamlit run dashboard.py
"""

import glob
import os
import pandas as pd

try:
    import streamlit as st
except ImportError:
    raise ImportError("Run: pip install streamlit")

st.set_page_config(page_title="MACD Signal Scanner", layout="wide")

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")

# ── Helpers ───────────────────────────────────────────────────────────────────
def pct(v, decimals=1):
    try:
        return f"{float(v)*100:.{decimals}f}%" if pd.notna(v) else "n/a"
    except:
        return "n/a"

def _tf_unit(tf: str) -> str:
    t = tf.upper()
    if "M" in t: return "M"
    if "W" in t: return "W"
    if "D" in t: return "D"
    return ""

def color_signal(val):
    if val == "LONG":  return "background-color: #1a2a4a; color: #4F8EF7; font-weight: bold"
    if val == "SHORT": return "background-color: #3a1a1a; color: #F75E5E; font-weight: bold"
    return ""

def color_winrate(val):
    try:
        v = float(str(val).replace("%", "")) / 100
        if v >= 0.70: return "color: #4caf50; font-weight: bold"
        if v >= 0.60: return "color: #8bc34a"
        if v >= 0.50: return "color: #ff9800"
        return "color: #F75E5E"
    except:
        return ""

def color_edge(val):
    try:
        v = float(str(val).replace("%", ""))
        if v >= 3:  return "color: #4F8EF7; font-weight: bold"
        if v >= 0:  return "color: #4F8EF7"
        if v >= -3: return "color: #ff9800"
        return "color: #F75E5E"
    except:
        return ""

def color_return(val):
    try:
        v = float(str(val).replace("%", ""))
        if v > 0: return "color: #4F8EF7"
        if v < 0: return "color: #F75E5E"
    except:
        pass
    return ""

def color_expectancy(val):
    try:
        v = float(str(val).replace("%", ""))
        if v >= 15: return "color: #4F8EF7; font-weight: bold"
        if v >= 8:  return "color: #4F8EF7"
        if v >= 4:  return "color: #ff9800"
        return "color: #F75E5E"
    except:
        return ""

def _val_cls(val_str: str) -> str:
    try:
        v = float(str(val_str).replace("%", ""))
        if v > 0: return " pos"
        if v < 0: return " neg"
    except:
        pass
    return ""

def _metric_card_html(count: int, label: str, side: str) -> str:
    return (
        f'<div class="metric-card {side}">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{count}</div>'
        f'</div>'
    )

def _pills_html(rows: pd.DataFrame, edge_col: str) -> str:
    if rows.empty:
        return ""
    is_long     = "long" in edge_col
    default_cls = "pill-pos" if is_long else "pill-neg"

    def make_pills(subset: pd.DataFrame) -> str:
        if subset.empty:
            return ""
        pills = []
        for _, r in subset.sort_values(edge_col, ascending=False).iterrows():
            try:
                v     = float(r.get(edge_col, 0))
                sign  = "+" if v >= 0 else ""
                label = f"{r['symbol']} {sign}{v * 100:.1f}%"
                cls   = "pill-pos" if v >= 0 else "pill-neg"
            except:
                label = r["symbol"]
                cls   = default_cls
            pills.append(f'<span class="pill {cls}">{label}</span>')
        return '<div class="pill-container">' + "".join(pills) + "</div>"

    has_types = "asset_type" in rows.columns
    if not has_types:
        return make_pills(rows)

    html   = ""
    stocks = rows[rows["asset_type"] == "Stock"]
    etfs   = rows[rows["asset_type"] == "ETF"]
    if not stocks.empty:
        html += '<p class="pill-group-label">Stocks</p>' + make_pills(stocks)
    if not etfs.empty:
        html += '<p class="pill-group-label">ETFs</p>' + make_pills(etfs)
    return html

def _detail_card_html(row: pd.Series, side: str, hold: str, pre: str) -> str:
    is_long   = side == "LONG"
    prefix    = "long" if is_long else "short"
    cls       = "long" if is_long else "short"
    direction = "histogram &gt; 0" if is_long else "histogram &lt; 0"
    win_label = "Win Rate (Rise / Total)" if is_long else "Win Rate (Fall / Total)"

    def drow(label, val, colorize=True):
        vcls = _val_cls(str(val)) if colorize else ""
        return (
            f'<div class="detail-row">'
            f'<span class="detail-label">{label}</span>'
            f'<span class="detail-value{vcls}">{val}</span>'
            f'</div>'
        )

    def dsec(label):
        return f'<div class="detail-section-head">{label}</div>'

    total  = int(row.get(f"{prefix}_total_events", 0))
    rise_n = int(row.get(f"{prefix}_rise_n",       0))
    fall_n = int(row.get(f"{prefix}_fall_n",       0))

    return (
        f'<div class="detail-card">'
        f'<div class="detail-card-header {cls}">{side} State &nbsp;&middot;&nbsp; {direction}</div>'
        f'<div class="detail-card-body">'
        + drow("Observations",          str(total),                              colorize=False)
        + drow("Rise / Fall",           f"{rise_n} / {fall_n}",                 colorize=False)
        + drow(win_label,               pct(row.get(f"{prefix}_win_rate")))
        + drow("Hit Edge vs Base",      pct(row.get(f"{prefix}_edge")))
        + dsec(f"Post-event ({hold})")
        + drow("Mean (Rise)",           pct(row.get(f"{prefix}_post_mean_rise")))
        + drow("Mean (Fall)",           pct(row.get(f"{prefix}_post_mean_fall")))
        + drow("Mean (Total)",          pct(row.get(f"{prefix}_post_mean_total")))
        + drow("Magnitude Edge",        pct(row.get(f"{prefix}_mag_edge")))
        + drow("+1 Std Dev",            pct(row.get(f"{prefix}_plus1sd")))
        + drow("-1 Std Dev",            pct(row.get(f"{prefix}_minus1sd")))
        + drow("Max Change",            pct(row.get(f"{prefix}_post_max")))
        + drow("Min Change",            pct(row.get(f"{prefix}_post_min")))
        + dsec(f"Pre-event ({pre})")
        + drow("Pre-event Mean",        pct(row.get(f"{prefix}_pre_mean")))
        + drow("+1 Std Dev",            pct(row.get(f"{prefix}_pre_plus1sd")))
        + drow("-1 Std Dev",            pct(row.get(f"{prefix}_pre_minus1sd")))
        + "</div></div>"
    )

# ── Data loader ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_latest_results():
    csvs = sorted(glob.glob(os.path.join(RESULTS_DIR, "signal_stats_*.csv")))
    if not csvs:
        return None, None
    latest = csvs[-1]
    return pd.read_csv(latest, index_col=0), latest

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', sans-serif;
}

/* Page title */
.page-title {
    font-size: 1.7rem;
    font-weight: 700;
    color: #E8EEFF;
    letter-spacing: -0.01em;
    margin: 0 0 0.1rem;
}
.page-subtitle {
    font-size: 0.79rem;
    color: #6870A0;
    margin: 0 0 0.5rem;
}

/* Section headers */
.section-title {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #8890A4;
    margin: 0 0 0.75rem;
    padding-bottom: 0.45rem;
    border-bottom: 1px solid #2A2D45;
}

/* Signal state metric cards */
.metric-card {
    background: #1E1E2E;
    border-radius: 10px;
    padding: 1.4rem 1.5rem;
    text-align: center;
    margin-bottom: 0.9rem;
}
.metric-card .metric-label {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #6870A0;
    margin-bottom: 0.35rem;
}
.metric-card .metric-value {
    font-size: 3rem;
    font-weight: 700;
    line-height: 1;
}
.metric-card.long  .metric-value { color: #4F8EF7; }
.metric-card.short .metric-value { color: #F75E5E; }

/* Pill badges */
.pill-group-label {
    font-size: 0.64rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #4A5270;
    margin: 0.7rem 0 0.25rem;
}
.pill-container {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
}
.pill {
    display: inline-block;
    padding: 0.17rem 0.55rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 500;
    line-height: 1.5;
    white-space: nowrap;
}
.pill-pos {
    background: rgba(79, 142, 247, 0.12);
    color: #4F8EF7;
    border: 1px solid rgba(79, 142, 247, 0.28);
}
.pill-neg {
    background: rgba(247, 94, 94, 0.12);
    color: #F75E5E;
    border: 1px solid rgba(247, 94, 94, 0.28);
}

/* Info / disclaimer boxes */
.info-box {
    background: #1E1E2E;
    border-left: 3px solid #4F8EF7;
    border-radius: 0 8px 8px 0;
    padding: 0.9rem 1.25rem;
    margin: 0.5rem 0;
    font-size: 0.82rem;
    color: #B8C0D8;
    line-height: 1.7;
}
.warn-box {
    background: #1E1E2E;
    border-left: 3px solid #F75E5E;
    border-radius: 0 8px 8px 0;
    padding: 0.75rem 1.25rem;
    margin: 0.5rem 0;
    font-size: 0.77rem;
    color: #8890A4;
    line-height: 1.6;
}

/* Ticker detail cards */
.detail-card {
    background: #1E1E2E;
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 0.5rem;
}
.detail-card-header {
    padding: 0.6rem 1.2rem;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.detail-card-header.long  { background: #4F8EF7; color: #fff; }
.detail-card-header.short { background: #F75E5E; color: #fff; }
.detail-card-body { padding: 0.4rem 1.2rem 0.75rem; }
.detail-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.27rem 0;
    font-size: 0.8rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.035);
}
.detail-row:last-child { border-bottom: none; }
.detail-label { color: #6870A0; }
.detail-value { font-weight: 500; color: #C8D0E8; }
.detail-value.pos { color: #4F8EF7; }
.detail-value.neg { color: #F75E5E; }
.detail-section-head {
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.11em;
    color: #3A4060;
    padding: 0.6rem 0 0.1rem;
}
</style>
""", unsafe_allow_html=True)

# ── Title ─────────────────────────────────────────────────────────────────────
col_title, col_refresh = st.columns([5, 1])
with col_title:
    st.markdown('<p class="page-title">MACD Signal Scanner</p>', unsafe_allow_html=True)
with col_refresh:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── Load data ─────────────────────────────────────────────────────────────────
df, filepath = load_latest_results()
if df is None:
    st.error(f"No results in `{RESULTS_DIR}`. Run `python main.py --backtest` first.")
    st.stop()

_tf    = df["timeframe"].iloc[0]            if "timeframe"      in df.columns else "1W"
_lbars = int(df["long_hold_bars"].iloc[0])  if "long_hold_bars"  in df.columns else 12
_sbars = int(df["short_hold_bars"].iloc[0]) if "short_hold_bars" in df.columns else 3
_macd  = df["macd_params"].iloc[0]          if "macd_params"     in df.columns else "12/26/9"

_unit        = _tf_unit(_tf)
_lhold       = f"{_lbars}{_unit}"
_shold       = f"{_sbars}{_unit}"
_pre         = f"5{_unit}"
_unit_word   = {"M": "month", "W": "week", "D": "day"}.get(_unit, "period")
_lhold_prose = f"{_lbars} {_unit_word}{'s' if _lbars != 1 else ''}"
_shold_prose = f"{_sbars} {_unit_word}{'s' if _sbars != 1 else ''}"

st.markdown(
    f'<p class="page-subtitle">'
    f'{_tf} &nbsp;&middot;&nbsp; MACD({_macd.replace("/", ", ")}) &nbsp;&middot;&nbsp; '
    f'State-based &nbsp;&middot;&nbsp; Ranked by Combined Expectancy &nbsp;&middot;&nbsp; '
    f'<code>{os.path.basename(filepath)}</code> &nbsp;&middot;&nbsp; {len(df)} tickers'
    f'</p>',
    unsafe_allow_html=True,
)

# ── Strategy overview ─────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    f'<div class="info-box">'
    f'<strong>Strategy Overview</strong><br><br>'
    f'Tracks {_tf} MACD({_macd.replace("/", ", ")}) histogram signals across stocks and ETFs. '
    f'<strong>LONG signal:</strong> histogram positive &rarr; price behaviour over {_lhold_prose}. '
    f'<strong>SHORT signal:</strong> histogram negative &rarr; price behaviour over {_shold_prose}.<br><br>'
    f'<strong>Win Rate</strong> alone is misleading — a stock rising 60% of all {_unit_word}s shows 60% win rate with no signal at all. '
    f'<strong>HitEdge</strong> = win rate minus unconditional base rate: positive means the signal genuinely adds timing value above market drift. '
    f'<strong>MagEdge</strong> = signal {_unit_word}s produce larger moves than average {_unit_word}s.'
    f'</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="warn-box">'
    '<strong>Disclaimer:</strong> Statistical observations from historical data only — '
    'not a full backtest or forward prediction. Past performance does not guarantee future results. '
    'This is not financial advice.'
    '</div>',
    unsafe_allow_html=True,
)

with st.expander("How to read the scores", expanded=False):
    st.markdown(f"""
| Column | Formula | Meaning |
|---|---|---|
| **Score** | (L Mean + \|S Mean\|) / 2 | Combined expectancy in % return units |
| **Win Rate** | rise\_n / total | % of signal-state {_unit_word}s price moved in the desired direction |
| **HitEdge** | Win Rate − Base Rate | Positive = signal times market better than random |
| **MagEdge** | Signal Mean − Base Mean | Positive = signal {_unit_word}s produce larger moves than average |
| **L: Base** | unconditional | % of ALL {_unit_word}s price rose over {_lhold} (no signal) |
| **S: Base** | unconditional | % of ALL {_unit_word}s price fell over {_shold} (no signal) |

Positive HitEdge = signal identifies good timing better than chance.
Negative edge = signal underperforms random for that side.
""")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("**Filters**")
    signal_filter = st.radio("Signal State", ["All", "LONG only", "SHORT only"], index=0)
    asset_filter  = st.radio("Asset Type",   ["All", "Stock", "ETF"],            index=0)
    st.markdown("---")
    min_long_wr      = st.slider("Min Long Win Rate",        0, 100,  0, 5, format="%d%%")
    min_short_wr     = st.slider("Min Short Win Rate",       0, 100,  0, 5, format="%d%%")
    min_long_edge    = st.slider("Min Long HitEdge",       -20,  20,-20, 1, format="%d%%")
    min_combined_exp = st.slider("Min Combined Expectancy",  0,  30,  0, 1, format="%d%%")
    st.markdown("---")
    st.markdown("**Display Options**")
    show_mag_edge   = st.checkbox("Magnitude Edge columns", value=False)
    show_means      = st.checkbox("Mean return columns",    value=False)
    show_sd         = st.checkbox("Std Dev bands",          value=False)
    show_base_rates = st.checkbox("Base rates",             value=False)
    show_pre_event  = st.checkbox("Pre-event stats",        value=False)
    show_raw_macd   = st.checkbox("Raw MACD values",        value=False)

# ── Apply filters ─────────────────────────────────────────────────────────────
filtered = df.copy()
if signal_filter == "LONG only":    filtered = filtered[filtered["active_signal"] == "LONG"]
elif signal_filter == "SHORT only": filtered = filtered[filtered["active_signal"] == "SHORT"]
if asset_filter != "All" and "asset_type" in filtered.columns:
    filtered = filtered[filtered["asset_type"] == asset_filter]
if "long_win_rate"       in filtered.columns: filtered = filtered[filtered["long_win_rate"].fillna(0)       >= min_long_wr / 100]
if "short_win_rate"      in filtered.columns: filtered = filtered[filtered["short_win_rate"].fillna(0)      >= min_short_wr / 100]
if "long_edge"           in filtered.columns: filtered = filtered[filtered["long_edge"].fillna(0)           >= min_long_edge / 100]
if "combined_expectancy" in filtered.columns: filtered = filtered[filtered["combined_expectancy"].fillna(0) >= min_combined_exp / 100]

# ── Section 1: Current Signal State ──────────────────────────────────────────
st.divider()
st.markdown('<p class="section-title">Current Signal State</p>', unsafe_allow_html=True)

if "active_signal" in df.columns:
    long_rows  = df[df["active_signal"] == "LONG"]
    short_rows = df[df["active_signal"] == "SHORT"]

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(_metric_card_html(len(long_rows),  "LONG  ·  histogram positive",  "long"),  unsafe_allow_html=True)
        st.markdown(_pills_html(long_rows,  "long_edge"),  unsafe_allow_html=True)
    with c2:
        st.markdown(_metric_card_html(len(short_rows), "SHORT  ·  histogram negative", "short"), unsafe_allow_html=True)
        st.markdown(_pills_html(short_rows, "short_edge"), unsafe_allow_html=True)

    st.markdown(
        '<p style="font-size:0.7rem;color:#3A4060;margin-top:0.6rem;">'
        '% shown = HitEdge vs unconditional base rate &nbsp;&middot;&nbsp; '
        'positive = signal adds directional value &nbsp;&middot;&nbsp; '
        'negative = worse than random</p>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Section 2: Rankings table ─────────────────────────────────────────────────
st.divider()
st.markdown(
    f'<p class="section-title">Rankings &nbsp;&middot;&nbsp; {len(filtered)} tickers</p>',
    unsafe_allow_html=True,
)

if filtered.empty:
    st.info("No tickers match the current filters.")
else:
    display = pd.DataFrame()
    display["Ticker"] = filtered["symbol"]
    display["Type"]   = filtered["asset_type"] if "asset_type" in filtered.columns else "—"
    display["State"]  = filtered["active_signal"]
    display["Score"]  = filtered["combined_expectancy"].apply(pct)

    # Default columns
    display["L: WinRate"] = filtered["long_win_rate"].apply(pct)
    display["L: HitEdge"] = filtered["long_edge"].apply(pct)
    display["S: WinRate"] = filtered["short_win_rate"].apply(pct)
    display["S: HitEdge"] = filtered["short_edge"].apply(pct)

    # Optional columns
    if show_mag_edge:
        display["L: MagEdge"] = filtered["long_mag_edge"].apply(pct)  if "long_mag_edge"  in filtered.columns else "n/a"
        display["S: MagEdge"] = filtered["short_mag_edge"].apply(pct) if "short_mag_edge" in filtered.columns else "n/a"
    if show_means:
        display["L: Mean"] = filtered["long_post_mean_total"].apply(pct)
        display["S: Mean"] = filtered["short_post_mean_total"].apply(pct)
    if show_sd:
        display["L: +1SD"] = filtered["long_plus1sd"].apply(pct)
        display["L: -1SD"] = filtered["long_minus1sd"].apply(pct)
        display["S: +1SD"] = filtered["short_plus1sd"].apply(pct)
        display["S: -1SD"] = filtered["short_minus1sd"].apply(pct)
    if show_base_rates:
        display["L: Base"] = filtered["base_long_rise_rate"].apply(pct)  if "base_long_rise_rate"  in filtered.columns else "n/a"
        display["S: Base"] = filtered["base_short_fall_rate"].apply(pct) if "base_short_fall_rate" in filtered.columns else "n/a"
    if show_pre_event:
        display["L: PreMean"] = filtered["long_pre_mean"].apply(pct)
        display["S: PreMean"] = filtered["short_pre_mean"].apply(pct)
    if show_raw_macd:
        display["Histogram"] = filtered["current_diff"]
        display["MACD"]      = filtered["current_macd"]
        display["SigLine"]   = filtered["current_signal"]

    display = display.reset_index(drop=True)
    display.index += 1
    display.index.name = "Rank"

    edge_cols   = [c for c in ["L: HitEdge", "L: MagEdge", "S: HitEdge", "S: MagEdge"] if c in display.columns]
    return_cols = [c for c in ["L: Mean", "S: Mean", "L: +1SD", "L: -1SD", "S: +1SD", "S: -1SD"] if c in display.columns]

    styled = (
        display.style
        .map(color_signal,     subset=["State"])
        .map(color_expectancy, subset=["Score"])
        .map(color_winrate,    subset=["L: WinRate", "S: WinRate"])
        .map(color_edge,       subset=edge_cols)
    )
    if return_cols:
        styled = styled.map(color_return, subset=return_cols)

    st.dataframe(styled, use_container_width=True, height=600)

st.markdown("<br>", unsafe_allow_html=True)

# ── Section 3: Ticker detail ──────────────────────────────────────────────────
st.divider()
st.markdown('<p class="section-title">Ticker Detail</p>', unsafe_allow_html=True)

all_symbols = sorted(df["symbol"].unique().tolist())
selected    = st.selectbox("Select a ticker", all_symbols, label_visibility="collapsed")

if selected:
    row = df[df["symbol"] == selected].iloc[0]
    sig       = row.get("active_signal", "SHORT")
    sig_color = "#4F8EF7" if sig == "LONG" else "#F75E5E"

    # Ticker + signal badge header
    st.markdown(
        f'<div style="display:flex;align-items:baseline;gap:0.75rem;margin:0.5rem 0 0.6rem;">'
        f'<span style="font-size:1.4rem;font-weight:700;color:#E8EEFF;">{selected}</span>'
        f'<span style="background:{sig_color};color:#fff;padding:0.15rem 0.7rem;'
        f'border-radius:999px;font-size:0.73rem;font-weight:600;letter-spacing:0.07em;">{sig}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="font-size:0.77rem;color:#4A5270;margin-bottom:0.8rem;">'
        f'MACD: <code>{row.get("current_macd", "n/a")}</code> &nbsp;&nbsp;'
        f'Signal Line: <code>{row.get("current_signal", "n/a")}</code> &nbsp;&nbsp;'
        f'Histogram: <code>{row.get("current_diff", "n/a")}</code>'
        f'</p>',
        unsafe_allow_html=True,
    )

    # Edge summary tiles
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Long HitEdge",  pct(row.get("long_edge")),      help="Long win rate vs unconditional base rise rate")
    e2.metric("Long MagEdge",  pct(row.get("long_mag_edge")),  help="Long mean return vs unconditional mean return")
    e3.metric("Short HitEdge", pct(row.get("short_edge")),     help="Short win rate vs unconditional base fall rate")
    e4.metric("Short MagEdge", pct(row.get("short_mag_edge")), help="Short mean return vs unconditional mean return")

    st.markdown(
        f'<p style="font-size:0.7rem;color:#3A4060;margin:0.3rem 0 1rem;">'
        f'Base rise rate ({_lhold}): <strong style="color:#8890A4;">{pct(row.get("base_long_rise_rate"))}</strong>'
        f'&nbsp;&nbsp;&middot;&nbsp;&nbsp;'
        f'Base fall rate ({_shold}): <strong style="color:#8890A4;">{pct(row.get("base_short_fall_rate"))}</strong>'
        f'&nbsp;&nbsp;&middot;&nbsp;&nbsp;'
        f'Base long mean: <strong style="color:#8890A4;">{pct(row.get("base_long_mean"))}</strong>'
        f'&nbsp;&nbsp;&middot;&nbsp;&nbsp;'
        f'Base short mean: <strong style="color:#8890A4;">{pct(row.get("base_short_mean"))}</strong>'
        f'</p>',
        unsafe_allow_html=True,
    )

    col_long, col_short = st.columns(2)
    with col_long:
        st.markdown(_detail_card_html(row, "LONG",  _lhold, _pre), unsafe_allow_html=True)
    with col_short:
        st.markdown(_detail_card_html(row, "SHORT", _shold, _pre), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Section 4: Export ─────────────────────────────────────────────────────────
st.divider()
st.markdown('<p class="section-title">Export</p>', unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    st.download_button(
        "Download full results (CSV)",
        df.to_csv().encode("utf-8"),
        "macd_full.csv",
        "text/csv",
        use_container_width=True,
    )
with c2:
    st.download_button(
        "Download filtered results (CSV)",
        filtered.to_csv().encode("utf-8"),
        "macd_filtered.csv",
        "text/csv",
        use_container_width=True,
    )
