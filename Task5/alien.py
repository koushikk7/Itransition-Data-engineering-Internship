import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
from fpdf import FPDF
import matplotlib.pyplot as plt
import tempfile
import os
import time

# Set Matplotlib to non-GUI mode
plt.switch_backend('Agg')

# --- CONFIGURATION & CSS ---
st.set_page_config(page_title="Mining Ops Simulator", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    /* Pitch Black Theme */
    .stApp { background-color: #000000; color: #ffffff; }
    
    /* Metrics - Matrix Green */
    [data-testid="stMetricValue"] { 
        color: #00ff00 !important; 
        font-family: 'Courier New', monospace; 
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] { color: #aaaaaa; }
    
    /* Buttons */
    .stButton>button { 
        border: 1px solid #00ff00; 
        color: #00ff00; 
        background-color: transparent; 
        border-radius: 5px;
    }
    .stButton>button:hover { 
        background-color: #00ff00; 
        color: #000000; 
        border: 1px solid #00ff00;
    }
    
    /* Text Headers */
    h1, h2, h3 { color: #ffffff !important; }
    
    /* Fix Plotly background transparency */
    .js-plotly-plot .plotly .main-svg { background: rgba(0,0,0,0) !important; }
    </style>
    """, unsafe_allow_html=True)

# YOUR GOOGLE SHEET URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQceXReuRkxkGqRnEoGGPgaOhhHDQxzaBWRjd0cmdDr7Ffm_tLvBgcx-g84zgiUJBaG6oVCF8mgCLNw/pub?gid=0&single=true&output=csv"

# --- DATA LOADER (PERSISTENT CACHE) ---
@st.cache_data(show_spinner=True)
def load_data(url):
    try:
        df = pd.read_csv(url)
        
        # Date Parsing
        if pd.api.types.is_numeric_dtype(df['Date']):
            df['Date'] = pd.to_datetime(df['Date'], unit='D', origin='1899-12-30')
        else:
            df['Date'] = pd.to_datetime(df['Date'])
            
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# --- STATISTICAL FUNCTIONS ---
def detect_outliers_iqr(data, factor=1.5):
    Q1, Q3 = np.percentile(data, 25), np.percentile(data, 75)
    IQR = Q3 - Q1
    return (data < (Q1 - factor * IQR)) | (data > (Q3 + factor * IQR))

def detect_outliers_zscore(data, threshold=3):
    return np.abs(stats.zscore(data)) > threshold

def detect_outliers_moving_avg(data, window=7, threshold_percent=20):
    ma = data.rolling(window=window).mean().fillna(method='bfill')
    return (np.abs(data - ma) / ma.replace(0, 1) * 100) > threshold_percent

def detect_outliers_grubbs(data, alpha=0.05):
    n, std = len(data), np.std(data)
    if std == 0: return np.zeros(n, dtype=bool)
    g_crit = ((n - 1) * np.sqrt(np.square(stats.t.ppf(1 - alpha / (2 * n), n - 2)))) / (np.sqrt(n) * np.sqrt(n - 2 + np.square(stats.t.ppf(1 - alpha / (2 * n), n - 2))))
    return (np.abs(data - np.mean(data)) / std) > g_crit

# --- CHART FOR PDF ---
def create_static_chart(df, col_name, anomalies, chart_type, poly_degree):
    fig, ax = plt.subplots(figsize=(10, 5))
    x_nums = np.arange(len(df))
    
    if chart_type == "Bar":
        ax.bar(df['Date'], df[col_name], color='green', alpha=0.7, label='Output')
    elif chart_type == "Area":
        ax.fill_between(df['Date'], df[col_name], color='green', alpha=0.3)
        ax.plot(df['Date'], df[col_name], color='green', label='Output')
    else:
        ax.plot(df['Date'], df[col_name], color='green', label='Output')

    ma_7 = df[col_name].rolling(window=7).mean()
    ax.plot(df['Date'], ma_7, color='magenta', linewidth=2, label='Moving Avg (7-Day)')

    if len(df) > poly_degree:
        z = np.polyfit(x_nums, df[col_name], poly_degree)
        p = np.poly1d(z)
        ax.plot(df['Date'], p(x_nums), color='blue', linestyle='--', linewidth=1.5, label=f'Trend (Deg {poly_degree})')

    if not anomalies.empty:
        ax.scatter(anomalies['Date'], anomalies[col_name], color='red', marker='x', s=50, label='Anomaly', zorder=5)

    ax.set_title(f"Production Timeline: {col_name}")
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    plt.savefig(temp_file.name, format='png', dpi=100)
    plt.close(fig)
    temp_file.close() # <--- CRITICAL FIX FOR LINUX
    return temp_file.name

# --- PDF GENERATOR ---
class PDFReport(FPDF):
    def header(self):
        # CHANGED TO HELVETICA (Safe for Linux)
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, 'Mining Operations Report', 0, 1, 'C')
        self.ln(5)

    def chapter_title(self, title):
        self.set_font('Helvetica', 'B', 12)
        self.set_fill_color(220, 220, 220)
        self.cell(0, 8, title, 0, 1, 'L', 1)
        self.ln(4)

    def chapter_body(self, text):
        self.set_font('Helvetica', '', 10)
        self.multi_cell(0, 6, text)
        self.ln()

    def create_table(self, header, data):
        self.set_font('Helvetica', 'B', 10)
        self.set_fill_color(240, 240, 240)
        w = [40, 30, 120] 
        for i, h in enumerate(header):
            self.cell(w[i], 8, h, 1, 0, 'C', 1)
        self.ln()
        
        self.set_font('Helvetica', '', 9)
        for row in data:
            self.cell(w[0], 7, str(row[0]), 1, 0, 'C')
            self.cell(w[1], 7, str(row[1]), 1, 0, 'R')
            self.cell(w[2], 7, str(row[2]), 1, 0, 'L')
            self.ln()

def generate_pdf(df, target_col, stats_dict, anomalies_data, chart_path):
    pdf = PDFReport()
    pdf.add_page()
    
    pdf.chapter_title(f"1. Operational Statistics ({target_col})")
    text = f"""Mean Daily Output: {stats_dict['mean']:.2f}
    Standard Deviation: {stats_dict['std']:.2f}
    Median Output: {stats_dict['median']:.2f}
    Interquartile Range: {stats_dict['iqr']:.2f}
    Total Days Recorded: {stats_dict['count']}"""
    pdf.chapter_body(text)

    pdf.chapter_title("2. Visual Analysis")
    pdf.image(chart_path, x=10, w=190)
    pdf.ln(5)
    
    pdf.add_page()
    pdf.chapter_title("3. Detected Anomalies Log")
    if anomalies_data:
        pdf.create_table(["Date", "Value", "Detection Method"], anomalies_data)
    else:
        pdf.chapter_body("No anomalies detected.")

    # Robust Byte Return
    try:
        return bytes(pdf.output(dest='S').encode('latin-1', 'replace'))
    except:
        return bytes(pdf.output())

# --- MAIN APP ---
def main():
    st.title("🏭 Weyland-Yutani Ops Simulator")
    
    # Session State: Cache Buster for Data
    if 'buster' not in st.session_state:
        st.session_state['buster'] = time.time()

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear() 
        st.session_state['buster'] = time.time() 
        # Also clear old PDF if data refreshes
        if 'pdf_bytes' in st.session_state:
            del st.session_state['pdf_bytes']
        st.rerun()

    final_url = f"{SHEET_URL}&t={st.session_state['buster']}"
    df = load_data(final_url)
    if df is None: return

    wanted_cols = ['LV_426', 'Origae_6', 'Fiorina_151', 'Total_Output']
    available_cols = [c for c in df.columns if c in wanted_cols]
    
    # Sidebar
    st.sidebar.markdown("### ⚙️ View Settings")
    target_col = st.sidebar.selectbox("Select Mine / Output", available_cols, index=len(available_cols)-1) 
    chart_type = st.sidebar.selectbox("Chart Type", ["Line", "Bar", "Area"])
    poly_degree = st.sidebar.slider("Trendline Degree", 1, 4, 3) 
    
    st.sidebar.markdown("### ⚠️ Thresholds")
    iqr_factor = st.sidebar.slider("IQR Factor", 1.0, 3.0, 1.5)
    z_thresh = st.sidebar.slider("Z-Score", 1.0, 5.0, 3.0)
    ma_thresh = st.sidebar.slider("Moving Avg Deviation %", 10, 100, 30)

    # --- GLOBAL SUMMARY TABLE ---
    st.subheader("Global Fleet Overview")
    summary_data = []
    for col in available_cols:
        summary_data.append({
            "Mine": col,
            "Mean": f"{df[col].mean():.1f}",
            "Std Dev": f"{df[col].std():.1f}",
            "Median": f"{df[col].median():.1f}",
            "IQR": f"{(np.percentile(df[col], 75) - np.percentile(df[col], 25)):.1f}"
        })
    st.dataframe(pd.DataFrame(summary_data), hide_index=True, use_container_width=True)

    # --- SELECTED MINE ANALYSIS ---
    st.markdown(f"## Analysis for: :green[{target_col}]")
    
    data = df[target_col]
    
    anomalies_iqr = detect_outliers_iqr(data, iqr_factor)
    anomalies_z = detect_outliers_zscore(data, z_thresh)
    anomalies_ma = detect_outliers_moving_avg(data, 7, ma_thresh)
    anomalies_grubbs = detect_outliers_grubbs(data)
    
    all_anomalies = anomalies_iqr | anomalies_z | anomalies_ma | anomalies_grubbs
    anomaly_points = df[all_anomalies]

    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mean Output", f"{data.mean():.1f}")
    c2.metric("Std Dev", f"{data.std():.1f}")
    c3.metric("Median", f"{data.median():.1f}")
    c4.metric("Anomalies Detected", f"{len(anomaly_points)}") 

    # Plotly Chart
    st.subheader("Production Timeline")
    fig = go.Figure()
    
    if chart_type == "Line":
        fig.add_trace(go.Scatter(x=df['Date'], y=data, mode='lines', name='Output', line=dict(color='#00ff00')))
    elif chart_type == "Area":
         fig.add_trace(go.Scatter(x=df['Date'], y=data, mode='lines', fill='tozeroy', name='Output', line=dict(color='#00ff00')))
    else:
        fig.add_trace(go.Bar(x=df['Date'], y=data, name='Output', marker_color='#00ff00'))
        
    df['MA_7'] = data.rolling(window=7).mean()
    fig.add_trace(go.Scatter(x=df['Date'], y=df['MA_7'], mode='lines', name='Moving Avg (7-Day)', line=dict(color='#ff00ff', width=2)))

    x_nums = np.arange(len(df))
    if len(df) > poly_degree:
        z = np.polyfit(x_nums, data, poly_degree)
        p = np.poly1d(z)
        fig.add_trace(go.Scatter(x=df['Date'], y=p(x_nums), mode='lines', name=f'Trend (Deg {poly_degree})', line=dict(color='yellow', dash='dash', width=2)))

    if not anomaly_points.empty:
        fig.add_trace(go.Scatter(x=anomaly_points['Date'], y=anomaly_points[target_col], mode='markers', name='Anomaly', marker=dict(color='red', size=8, symbol='x')))
    
    fig.update_layout(plot_bgcolor='black', paper_bgcolor='black', font_color='white', xaxis_showgrid=False, yaxis_gridcolor='#333333', height=450)
    st.plotly_chart(fig, use_container_width=True)

    # --- PDF EXPORT LOGIC (FIXED) ---
    if st.button("📄 Generate PDF Report (Current View)"):
        with st.spinner("Generating Report..."):
            try:
                stats_data = {
                    'mean': data.mean(), 'std': data.std(), 'median': data.median(),
                    'iqr': np.percentile(data, 75) - np.percentile(data, 25), 'count': len(data)
                }
                
                table_data = []
                for idx, row in anomaly_points.iterrows():
                    reasons = []
                    if anomalies_iqr[idx]: reasons.append("IQR")
                    if anomalies_z[idx]: reasons.append("Z-Score")
                    if anomalies_ma[idx]: reasons.append("MA")
                    if anomalies_grubbs[idx]: reasons.append("Grubbs")
                    
                    table_data.append([
                        row['Date'].strftime('%Y-%m-%d'),
                        f"{row[target_col]:.2f}",
                        ", ".join(reasons)
                    ])

                chart_path = create_static_chart(df, target_col, anomaly_points, chart_type, poly_degree)
                
                # SAVE TO SESSION STATE
                st.session_state['pdf_bytes'] = generate_pdf(df, target_col, stats_data, table_data, chart_path)
                
                if os.path.exists(chart_path): os.remove(chart_path)
                
            except Exception as e:
                st.error(f"Failed to generate PDF: {e}")

    # DISPLAY DOWNLOAD BUTTON IF READY
    if 'pdf_bytes' in st.session_state:
        st.success("Report Ready!")
        st.download_button(
            label=f"⬇️ Download PDF ({target_col})", 
            data=st.session_state['pdf_bytes'], 
            file_name=f"mining_report_{target_col}.pdf", 
            mime="application/pdf"
        )

