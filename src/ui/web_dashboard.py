import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Driver Scoring Monitor",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ─── Hero ─────────────────────────────────── */
.hero-banner {
    background: linear-gradient(135deg, #0d1117 0%, #0d1f35 60%, #0b2a45 100%);
    border: 1px solid #21262d;
    border-radius: 18px;
    padding: 10px 44px 20px 44px; /* Tighter top padding to move heading up */
    margin-bottom: 24px;
    display: flex;
    justify-content: center;
    align-items: flex-start; 
    min-height: 100px;
}
.hero-title {
    font-size: 3.5rem !important;
    font-weight: 900 !important;
    font-family: 'Segoe UI Black', 'Arial Black', sans-serif !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    text-align: center !important;
    margin: 0 !important;
    padding: 0 !important;
    letter-spacing: -2px !important;
    line-height: 1 !important;
    width: 100% !important;
    display: block !important;
}

/* ─── Metric Cards ──────────────────────────── */
.metric-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 14px;
    padding: 20px 16px;
    text-align: center;
    height: 108px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.metric-value {
    font-size: 1.95rem;
    font-weight: 800;
    color: #00FFAB;
    line-height: 1.1;
}
.metric-value.danger  { color: #FF4C4C; }
.metric-value.warning { color: #FFA500; }
.metric-value.neutral { color: #c9d1d9; font-size:1.3rem; }
.metric-label {
    color: #6e7681;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.9px;
    margin-top: 8px;
}

/* ─── Section Headers ───────────────────────── */
.section-hdr {
    font-size: 0.78rem;
    font-weight: 700;
    color: #6e7681;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    padding-bottom: 10px;
    border-bottom: 1px solid #21262d;
    margin-bottom: 14px;
}

/* ─── Trip Detail Block ─────────────────────── */
.detail-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 9px 0;
    border-bottom: 1px solid #1c2128;
    font-size: 0.86rem;
}
.detail-row:last-child { border-bottom: none; }
.detail-key { color: #6e7681; }
.detail-val { color: #e6edf3; font-weight: 600; }

/* ─── Sidebar Trip Cards ────────────────────── */
section[data-testid="stSidebar"] {
    background-color: #0d1117;
    border-right: 1px solid #21262d;
}
/* Make trip buttons look like cards */
section[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 4px;
    text-align: left;
    color: #c9d1d9;
    font-family: 'Inter', sans-serif;
    transition: border-color 0.2s, background 0.2s;
}
/* Active trip style is injected dynamically (nth-of-type) */
.total-badge {
    color: #8b949e;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 12px; 
    padding-left: 4px;
}

/* Streamlit overrides */
div[data-testid="stMetricValue"] { color: #00FFAB; }
.stSelectbox label { color: #6e7681 !important; font-size: 0.78rem !important; text-transform: uppercase; }
/* Hide Streamlit anchor icons */
.element-container:has(#driver-scoring-monitor) a { display: none !important; }
.hero-title a { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── Config ─────────────────────────────────────────────────────────────────────
TRIPS_DIR = os.path.join(os.path.dirname(__file__), "../../data/trips")

# ── Helpers ────────────────────────────────────────────────────────────────────
def load_trip_data(file_path):
    try:
        df = pd.read_csv(file_path)
        df = df.dropna(subset=['timestamp', 'score'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['score'] = pd.to_numeric(df['score'], errors='coerce')
        return df.dropna(subset=['score'])
    except Exception as e:
        st.error(f"Error loading trip: {e}")
        return None

def get_trips_list():
    if not os.path.exists(TRIPS_DIR):
        return []
    files = sorted([f for f in os.listdir(TRIPS_DIR) if f.endswith('.csv')], reverse=True)
    total = len(files)
    result = []
    for i, f in enumerate(files):
        try:
            parts = f.replace('.csv', '').split('_')
            dt = datetime.strptime(f"{parts[1]}_{parts[2]}", "%Y%m%d_%H%M%S")
            result.append({
                "filename": f,
                "display": f"Trip #{total - i}  ·  {dt.strftime('%d %b %Y  %I:%M %p')}",
                "date_str": dt.strftime("%d %b %Y"),
                "time_str": dt.strftime("%I:%M %p"),
                "num": total - i,
                "datetime": dt
            })
        except Exception:
            try:
                result.append({"filename": f, "display": f, "date_str": "Unknown", "time_str": "", "num": 0, "datetime": datetime.min})
            except: pass
    return result

def format_duration(td):
    """Format a timedelta as HH:MM:SS"""
    total_secs = int(td.total_seconds())
    h = total_secs // 3600
    m = (total_secs % 3600) // 60
    s = total_secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def safe_score(df):
    s = df['score'].iloc[-1] if not df.empty else 0.0
    if pd.isna(s):
        s = df['score'].dropna().mean()
    return float(s) if not pd.isna(s) else 0.0

def score_color(s):
    if s >= 75: return "#00FFAB"
    if s >= 50: return "#FFA500"
    return "#FF4C4C"

def score_class(s):
    if s >= 75: return ""
    if s >= 50: return "warning"
    return "danger"

def create_gauge(score):
    color = score_color(score)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={'suffix': "%", 'font': {'size': 46, 'color': color, 'family': 'Inter'}},
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "SAFETY SCORE", 'font': {'size': 12, 'color': "#6e7681", 'family': 'Inter'}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#30363d",
                     'tickfont': {'color': '#6e7681', 'size': 10}},
            'bar': {'color': color, 'thickness': 0.28},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 0,
            'steps': [
                {'range': [0, 40],  'color': 'rgba(255,76,76,0.12)'},
                {'range': [40, 75], 'color': 'rgba(255,165,0,0.1)'},
                {'range': [75, 100],'color': 'rgba(0,255,171,0.1)'}
            ],
        }
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': "#c9d1d9", 'family': "Inter"},
        height=240,
        margin=dict(t=20, b=0, l=10, r=10)
    )
    return fig

def plot_timeline(df):
    agg_df = df[df['prediction'] == 'AGGRESSIVE']
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['timestamp'], y=df['score'], name="Score",
        line=dict(color='#FFD700', width=2.5), fill='tozeroy',
        fillcolor='rgba(255,215,0,0.06)'
    ))
    fig.add_trace(go.Scatter(
        x=df['timestamp'], y=df['speed'], name="Speed (km/h)",
        line=dict(color='#00FFAB', width=2)
    ))
    if not agg_df.empty:
        fig.add_trace(go.Scatter(
            x=agg_df['timestamp'], y=agg_df['speed'],
            mode='markers', name="⚠️ Aggressive",
            marker=dict(color='#FF4C4C', size=10, symbol='x', line=dict(width=2))
        ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,27,34,0.8)',
        font=dict(color='#6e7681', family='Inter', size=11),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor='rgba(0,0,0,0)', font=dict(size=11)),
        xaxis=dict(gridcolor='#1c2128', showgrid=True, title=""),
        yaxis=dict(gridcolor='#1c2128', showgrid=True),
        height=260,
        margin=dict(t=10, b=0, l=0, r=0),
    )
    return fig

with st.sidebar:
    st.markdown("""
        <div style="margin-top: 40px;"></div>
        <h3 style="margin-bottom:8px;">Trip History</h3>
        <hr style="margin: 0 0 16px 0; border:0; border-top:1px solid #21262d;">
    """, unsafe_allow_html=True)
    
    trips_data = get_trips_list()
    
    # Session state for active trip
    if 'active_trip_idx' not in st.session_state:
        st.session_state.active_trip_idx = 0
    
    if not trips_data:
        st.warning("No trip data found.")
        selected_info = None
    else:
        st.markdown(f'<div class="total-badge">{len(trips_data)} Trip{"s" if len(trips_data) != 1 else ""} on Record</div>', unsafe_allow_html=True)

        for i, t in enumerate(trips_data):
            is_active = (i == st.session_state.active_trip_idx)
            if is_active:
                st.markdown(f"""
                <div style="
                    background: rgba(0,255,171,0.08);
                    border: 1px solid rgba(0,255,171,0.35);
                    border-left: 4px solid #00FFAB;
                    border-radius: 10px;
                    padding: 12px 14px;
                    margin-bottom: 4px;
                    color: #00FFAB;
                    font-weight: 600;
                    font-family: Inter, sans-serif;
                    font-size: 0.9rem;
                ">{t['display']}</div>
                """, unsafe_allow_html=True)
            else:
                if st.button(t['display'], key=f"trip_btn_{i}", use_container_width=True):
                    st.session_state.active_trip_idx = i
                    st.rerun()

        selected_info = trips_data[st.session_state.active_trip_idx]

    st.markdown("---")
    st.markdown('<span style="color:#6e7681;font-size:0.73rem">Smart Driver Scoring System · FYP</span>', unsafe_allow_html=True)

# ── Hero Header ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-banner">
    <h1 class="hero-title">Driver Scoring Monitor</h1>
</div>
""", unsafe_allow_html=True)

# ── Guard ───────────────────────────────────────────────────────────────────────
if not trips_data or not selected_info:
    st.info("No trip data found in `data/trips/`. Start a recording on the Raspberry Pi.")
    st.stop()

df = load_trip_data(os.path.join(TRIPS_DIR, selected_info["filename"]))

if df is None or df.empty:
    st.error("Trip file could not be loaded.")
    st.stop()

# ── Derived Values ─────────────────────────────────────────────────────────────
final_score  = safe_score(df)
max_speed    = df['speed'].max()
avg_speed    = df['speed'].mean()
agg_count    = len(df[df['prediction'] == 'AGGRESSIVE'])
raw_duration = df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]
duration_str = format_duration(raw_duration)
sc           = score_color(final_score)
s_cls        = score_class(final_score)
agg_cls      = "danger" if agg_count > 5 else ("warning" if agg_count > 2 else "")

# Active trip label
st.markdown(f'<p style="color:#6e7681;font-size:0.88rem;margin:0 0 18px">{selected_info["display"]}</p>', unsafe_allow_html=True)

# ── Latest Trip Summary Cards Row ─────────────────────────────────────────────
m1, m2, m3, m4, m5 = st.columns(5)

cards = [
    (m1, f"{final_score:.1f}%",  s_cls,   "Trip Score"),
    (m2, f"{max_speed:.0f}",     "",       "Max Speed (km/h)"),
    (m3, f"{avg_speed:.1f}",     "",       "Avg Speed (km/h)"),
    (m4, str(agg_count),         agg_cls,  "Aggressive Events"),
    (m5, duration_str,           "neutral","Trip Duration"),
]

for col, val, cls, lbl in cards:
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value {cls}">{val}</div>
            <div class="metric-label">{lbl}</div>
        </div>""", unsafe_allow_html=True)

# ── Gauge (left) + Timeline (right) ───────────────────────────────────────────
g_col, t_col = st.columns([1, 2.4])

with g_col:
    st.plotly_chart(create_gauge(final_score), use_container_width=True)
    
    start_t = df['timestamp'].iloc[0]
    st.markdown(f"""
    <div style="background:#0d1117;border:1px solid #21262d;border-radius:12px;padding:14px 18px;margin-top:4px">
        <div class="detail-row"><span class="detail-key">Date</span><span class="detail-val">{start_t.strftime('%d %B %Y')}</span></div>
        <div class="detail-row"><span class="detail-key">Start Time</span><span class="detail-val">{start_t.strftime('%I:%M:%S %p')}</span></div>
        <div class="detail-row"><span class="detail-key">Duration</span><span class="detail-val">{duration_str}</span></div>
        <div class="detail-row"><span class="detail-key">Incidents</span><span class="detail-val" style="color:{sc}">{agg_count} event{"s" if agg_count != 1 else ""}</span></div>
    </div>
    """, unsafe_allow_html=True)

with t_col:
    st.markdown('<p class="section-hdr">Speed &amp; Score Timeline</p>', unsafe_allow_html=True)
    st.plotly_chart(plot_timeline(df), use_container_width=True)

# ── Engine Performance ─────────────────────────────────────────────────────────
st.markdown('<p class="section-hdr">Engine Performance</p>', unsafe_allow_html=True)

e1, e2 = st.columns(2)

def area_chart(df, col, color, fill_color, label):
    fig = px.area(df, x='timestamp', y=col, labels={col: label, 'timestamp': ''},
                  color_discrete_sequence=[color])
    fig.update_traces(fill='tozeroy', fillcolor=fill_color, line_width=2)
    fig.update_layout(
        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,27,34,0.8)', height=200,
        font=dict(color='#6e7681', family='Inter', size=11),
        margin=dict(t=8, b=8, l=0, r=0),
        xaxis=dict(gridcolor='#1c2128', title=""),
        yaxis=dict(gridcolor='#1c2128')
    )
    return fig

with e1:
    st.markdown("**RPM History**")
    st.plotly_chart(area_chart(df, 'rpm', '#00BFFF', 'rgba(0,191,255,0.1)', 'RPM'), use_container_width=True)

with e2:
    st.markdown("**Throttle Usage (%)**")
    st.plotly_chart(area_chart(df, 'throttle', '#FF8C00', 'rgba(255,140,0,0.1)', 'Throttle %'), use_container_width=True)

# ── Raw Data ───────────────────────────────────────────────────────────────────
with st.expander("View Raw Trip Data"):
    st.dataframe(
        df.style.background_gradient(subset=['score'], cmap='RdYlGn', vmin=0, vmax=100),
        use_container_width=True
    )
