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

# ── Color constants (light theme) ─────────────────────────────────────────────
C_BG       = "#F8F9FA"   # app background
C_CARD     = "#FFFFFF"   # card / surface
C_CARD_ALT = "#F7FAFC"   # zebra alt rows
C_SECTION  = "#F0F4F8"   # section tint backgrounds
C_BORDER   = "#E2E8F0"   # borders
C_POS      = "#276749"   # forest green — positive values, LONG
C_NEG      = "#9B2C2C"   # deep red — negative values, SHORT
C_ACCENT   = "#2B6CB0"   # navy — headers, score highlights
C_ORANGE   = "#C05621"   # warm orange — mild negative edge
C_TEXT     = "#1A202C"   # primary text
C_TEXT2    = "#4A5568"   # secondary text
C_GREY     = "#718096"   # grey text for negative-edge pills
C_GREY_BDR = "#CBD5E0"   # grey border for negative-edge pills

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

# ── Dataframe cell colouring ──────────────────────────────────────────────────
def color_signal(val):
    if val == "LONG":  return f"background-color: #F0FFF4; color: {C_POS}; font-weight: bold"
    if val == "SHORT": return f"background-color: #FFF5F5; color: {C_NEG}; font-weight: bold"
    return ""

def color_winrate(val):
    try:
        v = float(str(val).replace("%", "")) / 100
        if v >= 0.70: return f"color: {C_POS}; font-weight: bold"
        if v >= 0.60: return f"color: {C_POS}"
        if v >= 0.50: return f"color: {C_ORANGE}"
        return f"color: {C_NEG}"
    except:
        return ""

def color_edge(val):
    try:
        v = float(str(val).replace("%", ""))
        if v >= 3:  return f"color: {C_POS}; font-weight: bold"
        if v >= 0:  return f"color: {C_POS}"
        if v >= -3: return f"color: {C_ORANGE}"
        return f"color: {C_NEG}"
    except:
        return ""

def color_return(val):
    try:
        v = float(str(val).replace("%", ""))
        if v > 0: return f"color: {C_POS}"
        if v < 0: return f"color: {C_NEG}"
    except:
        pass
    return ""

def color_expectancy(val):
    try:
        v = float(str(val).replace("%", ""))
        if v >= 15: return f"color: {C_ACCENT}; font-weight: bold"
        if v >= 8:  return f"color: {C_ACCENT}"
        if v >= 4:  return f"color: {C_ORANGE}"
        return f"color: {C_NEG}"
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

def _zebra(row):
    bg = C_CARD if row.name % 2 != 0 else C_CARD_ALT
    return [f"background-color: {bg}"] * len(row)

# ── HTML component builders ───────────────────────────────────────────────────
_DIVIDER = f'<hr style="border:none;border-top:1px solid {C_ACCENT};opacity:0.18;margin:0.25rem 0;">'
_SPACER  = '<div style="margin:1.5rem"></div>'

def _metric_card_html(count: int, label: str, side: str) -> str:
    val_color = C_POS if side == "long" else C_NEG
    return (
        f'<div class="metric-card">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value" style="color:{val_color};">{count}</div>'
        f'</div>'
    )

def _signal_pills_html(rows: pd.DataFrame, edge_col: str) -> str:
    """Current Signal State pills — 4 subsections: Stocks/ETFs × Positive/Negative edge."""
    if rows.empty:
        return ""

    def make_pills(subset: pd.DataFrame, pill_cls: str) -> str:
        pills = []
        for _, r in subset.sort_values(edge_col, ascending=False).iterrows():
            try:
                v     = float(r.get(edge_col, 0))
                sign  = "+" if v >= 0 else ""
                label = f"{r['symbol']} {sign}{v * 100:.1f}%"
            except:
                label = r["symbol"]
            pills.append(f'<span class="pill {pill_cls}">{label}</span>')
        return '<div class="pill-container">' + "".join(pills) + "</div>"

    def subsection(label: str, subset: pd.DataFrame, pill_cls: str) -> str:
        if subset.empty:
            return ""
        return (
            f'<p class="pill-group-label">{label} '
            f'<span class="pill-count">{len(subset)}</span></p>'
            + make_pills(subset, pill_cls)
        )

    has_types = "asset_type" in rows.columns
    html = ""

    if has_types:
        stocks = rows[rows["asset_type"] == "Stock"]
        etfs   = rows[rows["asset_type"] == "ETF"]
        html += subsection("Stocks — Positive Edge",
                           stocks[stocks[edge_col].fillna(0) > 0],  "pill-pos-edge")
        html += subsection("Stocks — Negative Edge",
                           stocks[stocks[edge_col].fillna(0) <= 0], "pill-neg-edge")
        html += subsection("ETFs — Positive Edge",
                           etfs[etfs[edge_col].fillna(0) > 0],      "pill-pos-edge")
        html += subsection("ETFs — Negative Edge",
                           etfs[etfs[edge_col].fillna(0) <= 0],     "pill-neg-edge")
    else:
        html += subsection("Positive Edge", rows[rows[edge_col].fillna(0) > 0],  "pill-pos-edge")
        html += subsection("Negative Edge", rows[rows[edge_col].fillna(0) <= 0], "pill-neg-edge")

    return html

def _edge_metrics_html(row: pd.Series) -> str:
    def card(label, val_str, help_text=""):
        try:
            v  = float(val_str.replace("%", ""))
            vc = C_POS if v > 0 else C_NEG
        except:
            vc = C_TEXT2
        title = f' title="{help_text}"' if help_text else ""
        return (
            f'<div class="edge-metric"{title}>'
            f'<div class="edge-metric-label">{label}</div>'
            f'<div class="edge-metric-value" style="color:{vc};">{val_str}</div>'
            f'</div>'
        )
    return (
        '<div class="edge-metrics-row">'
        + card("Long HitEdge",  pct(row.get("long_edge")),      "Long win rate vs unconditional base rise rate")
        + card("Long MagEdge",  pct(row.get("long_mag_edge")),  "Long mean return vs unconditional mean return")
        + card("Short HitEdge", pct(row.get("short_edge")),     "Short win rate vs unconditional base fall rate")
        + card("Short MagEdge", pct(row.get("short_mag_edge")), "Short mean return vs unconditional mean return")
        + '</div>'
    )

def _detail_card_html(row: pd.Series, side: str, hold: str, pre: str) -> str:
    is_long   = side == "LONG"
    prefix    = "long" if is_long else "short"
    hdr_bg    = C_POS if is_long else C_NEG
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
        f'<div class="detail-card-header" style="background:{hdr_bg};">'
        f'{side} State &nbsp;&middot;&nbsp; {direction}'
        f'</div>'
        f'<div class="detail-card-body">'
        + drow("Observations",      str(total),             colorize=False)
        + drow("Rise / Fall",       f"{rise_n} / {fall_n}", colorize=False)
        + drow(win_label,           pct(row.get(f"{prefix}_win_rate")))
        + drow("Hit Edge vs Base",  pct(row.get(f"{prefix}_edge")))
        + dsec(f"Post-event ({hold})")
        + drow("Mean (Rise)",       pct(row.get(f"{prefix}_post_mean_rise")))
        + drow("Mean (Fall)",       pct(row.get(f"{prefix}_post_mean_fall")))
        + drow("Mean (Total)",      pct(row.get(f"{prefix}_post_mean_total")))
        + drow("Magnitude Edge",    pct(row.get(f"{prefix}_mag_edge")))
        + drow("+1 Std Dev",        pct(row.get(f"{prefix}_plus1sd")))
        + drow("-1 Std Dev",        pct(row.get(f"{prefix}_minus1sd")))
        + drow("Max Change",        pct(row.get(f"{prefix}_post_max")))
        + drow("Min Change",        pct(row.get(f"{prefix}_post_min")))
        + dsec(f"Pre-event ({pre})")
        + drow("Pre-event Mean",    pct(row.get(f"{prefix}_pre_mean")))
        + drow("+1 Std Dev",        pct(row.get(f"{prefix}_pre_plus1sd")))
        + drow("-1 Std Dev",        pct(row.get(f"{prefix}_pre_minus1sd")))
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
st.markdown(f"""
<style>
/* ── Base & app background ────────────────────────────────────────────── */
html, body {{
    font-size: 15px;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    color: {C_TEXT};
}}
.stApp {{
    background-color: {C_BG} !important;
}}
.element-container {{
    background-color: transparent !important;
}}
.block-container {{
    padding-top: 2rem !important;
}}

/* ── Sidebar ──────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background-color: {C_SECTION} !important;
    border-right: 1px solid {C_BORDER} !important;
}}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] .stCheckbox label,
[data-testid="stSidebar"] .stSlider label {{
    color: {C_TEXT2} !important;
    font-size: 13px !important;
}}

/* ── Dataframe ────────────────────────────────────────────────────────── */
.stDataFrame {{
    font-size: 13px !important;
    background-color: {C_CARD} !important;
    border: 1px solid {C_BORDER} !important;
    border-radius: 8px !important;
    overflow: hidden !important;
}}
[data-testid="stDataFrameResizable"] {{
    background-color: {C_CARD} !important;
}}
/* Column headers and cell text — HTML table fallback (non-canvas renderers) */
.stDataFrame th {{
    color: {C_TEXT} !important;
    background-color: {C_SECTION} !important;
    font-weight: 600 !important;
    border-bottom: 1px solid {C_BORDER} !important;
}}
.stDataFrame td {{
    color: {C_TEXT} !important;
}}
/* Glide-data-grid column header text (canvas overlay labels) */
[data-testid="stDataFrameResizable"] [role="columnheader"],
[data-testid="stDataFrameResizable"] [role="gridcell"] {{
    color: {C_TEXT} !important;
}}

/* ── st.metric ────────────────────────────────────────────────────────── */
[data-testid="stMetricValue"] {{
    font-size: 22px !important;
    font-weight: 700 !important;
    color: {C_TEXT} !important;
}}
[data-testid="stMetricLabel"] {{
    font-size: 12px !important;
    color: {C_TEXT2} !important;
}}
[data-testid="metric-container"] {{
    background-color: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    padding: 0.75rem 1rem;
}}

/* ── Expander headers ─────────────────────────────────────────────────── */
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span {{
    color: {C_TEXT} !important;
    font-weight: 600 !important;
}}

/* ── Page title ───────────────────────────────────────────────────────── */
.title-bar {{
    border-bottom: 2px solid rgba(43,108,176,0.25);
    padding-bottom: 0.75rem;
    margin-bottom: 0.25rem;
}}
.page-title {{
    font-size: 1.75rem;
    font-weight: 700;
    color: {C_TEXT};
    letter-spacing: -0.01em;
    margin: 0;
}}
.page-subtitle {{
    font-size: 0.8rem;
    color: {C_TEXT2};
    margin: 0.25rem 0 0;
}}

/* ── Section headers ──────────────────────────────────────────────────── */
.section-title {{
    font-size: 18px;
    font-weight: 600;
    color: {C_ACCENT};
    margin: 0 0 0.9rem;
    letter-spacing: 0.01em;
}}

/* ── Signal state metric cards ────────────────────────────────────────── */
.metric-card {{
    background: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 10px;
    padding: 1.4rem 1.5rem;
    text-align: center;
    margin-bottom: 0.9rem;
}}
.metric-card .metric-label {{
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: {C_TEXT2};
    margin-bottom: 0.4rem;
}}
.metric-card .metric-value {{
    font-size: 3rem;
    font-weight: 700;
    line-height: 1;
}}

/* ── Pill badges ──────────────────────────────────────────────────────── */
.pill-group-label {{
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: {C_TEXT2};
    margin: 0.85rem 0 0.3rem;
    font-weight: 600;
}}
.pill-count {{
    background: {C_SECTION};
    color: {C_TEXT2};
    border-radius: 999px;
    padding: 0.05rem 0.45rem;
    font-size: 0.62rem;
    font-weight: 600;
    display: inline-block;
    vertical-align: middle;
    margin-left: 0.2rem;
}}
.pill-container {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
}}
.pill {{
    display: inline-block;
    padding: 0.18rem 0.6rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 500;
    line-height: 1.55;
    white-space: nowrap;
}}
/* Current Signal State: quadrant pills */
.pill-pos-edge {{
    background: {C_CARD};
    color: {C_POS};
    border: 1px solid {C_POS};
}}
.pill-neg-edge {{
    background: {C_CARD};
    color: {C_GREY};
    border: 1px solid {C_GREY_BDR};
}}

/* ── Info / disclaimer boxes ──────────────────────────────────────────── */
.info-box {{
    background: {C_CARD};
    border: 1px solid {C_BORDER};
    border-left: 3px solid {C_POS};
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.3rem;
    margin: 0.5rem 0;
    font-size: 0.83rem;
    color: {C_TEXT2};
    line-height: 1.7;
}}
.warn-box {{
    background: {C_CARD};
    border: 1px solid {C_BORDER};
    border-left: 3px solid {C_NEG};
    border-radius: 0 8px 8px 0;
    padding: 0.75rem 1.3rem;
    margin: 0.5rem 0;
    font-size: 0.77rem;
    color: {C_TEXT2};
    line-height: 1.6;
}}

/* ── Edge metric row (ticker detail) ──────────────────────────────────── */
.edge-metrics-row {{
    display: flex;
    gap: 0.75rem;
    margin: 0.75rem 0;
}}
.edge-metric {{
    flex: 1;
    background: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    padding: 0.9rem 1rem;
    text-align: center;
    cursor: default;
}}
.edge-metric-label {{
    font-size: 11px;
    color: {C_TEXT2};
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.45rem;
}}
.edge-metric-value {{
    font-size: 22px;
    font-weight: 700;
    line-height: 1;
}}

/* ── Ticker detail cards ──────────────────────────────────────────────── */
.detail-card {{
    background: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 0.5rem;
}}
.detail-card-header {{
    padding: 0.65rem 1.2rem;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #fff;
}}
.detail-card-body {{
    padding: 0.45rem 1.2rem 0.85rem;
}}
.detail-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.28rem 0;
    font-size: 13px;
    border-bottom: 1px solid {C_BORDER};
}}
.detail-row:last-child {{ border-bottom: none; }}
.detail-label {{ color: {C_TEXT2}; }}
.detail-value {{ font-weight: 500; color: {C_TEXT}; }}
.detail-value.pos {{ color: {C_POS}; }}
.detail-value.neg {{ color: {C_NEG}; }}
.detail-section-head {{
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.11em;
    color: {C_TEXT2};
    padding: 0.6rem 0 0.1rem;
}}
</style>
""", unsafe_allow_html=True)

# ── Title ─────────────────────────────────────────────────────────────────────
col_title, col_refresh = st.columns([5, 1])
with col_title:
    st.markdown(
        '<div class="title-bar">'
        '<p class="page-title">MACD Signal Scanner</p>'
        '</div>',
        unsafe_allow_html=True,
    )
with col_refresh:
    st.markdown(_SPACER, unsafe_allow_html=True)
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
st.markdown(_SPACER, unsafe_allow_html=True)
st.markdown(
    f'<div class="info-box">'
    f'<strong style="color:{C_TEXT};">Strategy Overview</strong><br><br>'
    f'Tracks {_tf} MACD({_macd.replace("/", ", ")}) histogram signals across stocks and ETFs. '
    f'<strong>LONG signal:</strong> histogram positive &rarr; price behaviour over {_lhold_prose}. '
    f'<strong>SHORT signal:</strong> histogram negative &rarr; price behaviour over {_shold_prose}.<br><br>'
    f'<strong>Win Rate</strong> alone is misleading — a stock rising 60% of all {_unit_word}s shows 60% win rate with no signal at all. '
    f'<strong>HitEdge</strong> = win rate minus unconditional base rate. Positive = signal adds timing value above market drift. '
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
    st.markdown(f'<p style="color:{C_ACCENT};font-weight:600;font-size:15px;margin-bottom:0.5rem;">Filters</p>', unsafe_allow_html=True)
    signal_filter = st.radio("Signal State", ["All", "LONG only", "SHORT only"], index=0)
    asset_filter  = st.radio("Asset Type",   ["All", "Stock", "ETF"],            index=0)
    st.markdown(_DIVIDER, unsafe_allow_html=True)
    min_long_wr      = st.slider("Min Long Win Rate",        0, 100,  0, 5, format="%d%%")
    min_short_wr     = st.slider("Min Short Win Rate",       0, 100,  0, 5, format="%d%%")
    min_long_edge    = st.slider("Min Long HitEdge",       -20,  20,-20, 1, format="%d%%")
    min_combined_exp = st.slider("Min Combined Expectancy",  0,  30,  0, 1, format="%d%%")
    st.markdown(_DIVIDER, unsafe_allow_html=True)
    st.markdown(f'<p style="color:{C_ACCENT};font-weight:600;font-size:15px;margin-bottom:0.5rem;">Display Options</p>', unsafe_allow_html=True)
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
st.markdown(_DIVIDER, unsafe_allow_html=True)
st.markdown(_SPACER,  unsafe_allow_html=True)
st.markdown('<p class="section-title">Current Signal State</p>', unsafe_allow_html=True)

if "active_signal" in df.columns:
    long_rows  = df[df["active_signal"] == "LONG"]
    short_rows = df[df["active_signal"] == "SHORT"]

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(_metric_card_html(len(long_rows),  "LONG  ·  histogram positive",  "long"),  unsafe_allow_html=True)
        st.markdown(_signal_pills_html(long_rows,  "long_edge"),  unsafe_allow_html=True)
    with c2:
        st.markdown(_metric_card_html(len(short_rows), "SHORT  ·  histogram negative", "short"), unsafe_allow_html=True)
        st.markdown(_signal_pills_html(short_rows, "short_edge"), unsafe_allow_html=True)

    st.markdown(
        f'<p style="font-size:0.7rem;color:{C_TEXT2};margin-top:0.8rem;">'
        f'% shown = HitEdge vs unconditional base rate &nbsp;&middot;&nbsp; '
        f'green = signal adds directional value &nbsp;&middot;&nbsp; '
        f'grey = worse than random</p>',
        unsafe_allow_html=True,
    )

st.markdown(_SPACER, unsafe_allow_html=True)

# ── Section 2: Rankings table ─────────────────────────────────────────────────
st.markdown(_DIVIDER, unsafe_allow_html=True)
st.markdown(_SPACER,  unsafe_allow_html=True)
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

    styled = display.style.apply(_zebra, axis=1)
    styled = (
        styled
        .map(color_signal,     subset=["State"])
        .map(color_expectancy, subset=["Score"])
        .map(color_winrate,    subset=["L: WinRate", "S: WinRate"])
        .map(color_edge,       subset=edge_cols)
    )
    if return_cols:
        styled = styled.map(color_return, subset=return_cols)

    st.dataframe(styled, use_container_width=True, height=600)

st.markdown(_SPACER, unsafe_allow_html=True)

# ── Section 3: Ticker detail ──────────────────────────────────────────────────
st.markdown(_DIVIDER, unsafe_allow_html=True)
st.markdown(_SPACER,  unsafe_allow_html=True)
st.markdown('<p class="section-title">Ticker Detail</p>', unsafe_allow_html=True)

all_symbols = sorted(df["symbol"].unique().tolist())
selected    = st.selectbox("Select a ticker", all_symbols, label_visibility="collapsed")

if selected:
    row = df[df["symbol"] == selected].iloc[0]
    sig       = row.get("active_signal", "SHORT")
    sig_color = C_POS if sig == "LONG" else C_NEG

    # Ticker + signal badge header
    st.markdown(
        f'<div style="display:flex;align-items:baseline;gap:0.75rem;margin:0.6rem 0 0.5rem;">'
        f'<span style="font-size:1.45rem;font-weight:700;color:{C_TEXT};">{selected}</span>'
        f'<span style="background:{sig_color};color:#fff;padding:0.15rem 0.75rem;'
        f'border-radius:999px;font-size:0.73rem;font-weight:600;letter-spacing:0.07em;">{sig}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="font-size:0.77rem;color:{C_TEXT2};margin-bottom:0.25rem;">'
        f'MACD: <code>{row.get("current_macd", "n/a")}</code>'
        f'&nbsp;&nbsp;&middot;&nbsp;&nbsp;'
        f'Signal Line: <code>{row.get("current_signal", "n/a")}</code>'
        f'&nbsp;&nbsp;&middot;&nbsp;&nbsp;'
        f'Histogram: <code>{row.get("current_diff", "n/a")}</code>'
        f'</p>',
        unsafe_allow_html=True,
    )

    # Edge summary — custom HTML metric cards
    st.markdown(_edge_metrics_html(row), unsafe_allow_html=True)

    # Base rate reference line
    st.markdown(
        f'<p style="font-size:0.7rem;color:{C_TEXT2};margin:0.1rem 0 1.1rem;">'
        f'Base rise rate ({_lhold}): <strong style="color:{C_TEXT};">{pct(row.get("base_long_rise_rate"))}</strong>'
        f'&nbsp;&nbsp;&middot;&nbsp;&nbsp;'
        f'Base fall rate ({_shold}): <strong style="color:{C_TEXT2};">{pct(row.get("base_short_fall_rate"))}</strong>'
        f'&nbsp;&nbsp;&middot;&nbsp;&nbsp;'
        f'Base long mean: <strong style="color:{C_TEXT2};">{pct(row.get("base_long_mean"))}</strong>'
        f'&nbsp;&nbsp;&middot;&nbsp;&nbsp;'
        f'Base short mean: <strong style="color:{C_TEXT2};">{pct(row.get("base_short_mean"))}</strong>'
        f'</p>',
        unsafe_allow_html=True,
    )

    col_long, col_short = st.columns(2)
    with col_long:
        st.markdown(_detail_card_html(row, "LONG",  _lhold, _pre), unsafe_allow_html=True)
    with col_short:
        st.markdown(_detail_card_html(row, "SHORT", _shold, _pre), unsafe_allow_html=True)

st.markdown(_SPACER, unsafe_allow_html=True)

# ── Section 4: Export ─────────────────────────────────────────────────────────
st.markdown(_DIVIDER, unsafe_allow_html=True)
st.markdown(_SPACER,  unsafe_allow_html=True)
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
