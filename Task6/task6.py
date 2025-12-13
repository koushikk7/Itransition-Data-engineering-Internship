import streamlit as st
import pandas as pd
import psycopg2
import time

DB_URL = "postgresql://neondb_owner:npg_B3lEba1XmSJd@ep-misty-thunder-agf1by03-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

st.set_page_config(page_title="SQL Faker", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background-color: #000000;
        color: #ffffff;
    }

    h1, h2, h3, p, label {
        color: #ffffff !important;
    }

    [data-testid="stMetricValue"] {
        color: #00ff00 !important;
        font-family: 'Courier New', monospace;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        color: #aaaaaa;
    }

    [data-testid="stSidebar"] {
        background-color: #111111;
        border-right: 1px solid #222222;
    }

    .stButton > button {
        background-color: transparent;
        color: #00ff00;
        border: 1px solid #00ff00;
        border-radius: 5px;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #00ff00;
        color: #000000;
        border: 1px solid #00ff00;
        box-shadow: 0 0 10px #00ff00;
    }
    .stButton > button:active {
        background-color: #00cc00;
        color: #000000;
    }

    [data-testid="stDataFrame"] {
        background-color: #111111;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("Task 6: Fake user contact info generator")
st.markdown("""
This application generates random user data using SQL Stored Procedures.
Python is used only to render the interface.
""")

with st.sidebar:
    st.header("Generator Settings")
    locale = st.selectbox("Select Region (Locale)", ["en_US", "de_DE", "fr_FR"])
    seed = st.number_input("Seed Value", min_value=0, value=42, step=1)
    batch_size = st.slider("Batch Size", 10, 10000, 100)
    page = st.number_input("Page Number (Offset)", min_value=0, value=0)

def fetch_users(seed, count, locale, offset):
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    query = f"SELECT * FROM generate_fake_people({seed}, {count}, '{locale}', {offset});"
    cur.execute(query)
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    conn.close()
    return pd.DataFrame(rows, columns=cols)

if st.button("Generate Data"):

    status_text = st.empty()
    start_time = time.time()
    total_offset = page * batch_size

    try:
        df = fetch_users(seed, batch_size, locale, total_offset)

        end_time = time.time()
        duration = end_time - start_time

        if 'id' in df.columns:
            df = df.drop(columns=['id'])

        if duration > 0:
            speed = len(df) / duration
        else:
            speed = len(df) * 1000

        status_text.empty()

        c1, c2, c3 = st.columns(3)
        c1.metric("Rows Generated", f"{len(df):,}")
        c2.metric("Time Taken", f"{duration:.4f} seconds")
        c3.metric("Speed (Benchmark)", f"{speed:,.0f} users/sec")

        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Download CSV",
            data=csv,
            file_name=f"fake_users_{locale}_{seed}.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Database Error: {e}")
