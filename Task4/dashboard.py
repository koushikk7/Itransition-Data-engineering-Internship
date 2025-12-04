import streamlit as st
import pandas as pd
import yaml
import re
import networkx as nx
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Bookstore Analytics", layout="wide", initial_sidebar_state="expanded")

css_file = Path(__file__).parent / "style.css"
if css_file.exists():
    with open(css_file) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def parse_books_yml(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    content = re.sub(r':(\w+)', r'\1', content)
    try:
        data = yaml.safe_load(content)
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error parsing YAML: {e}")
        return pd.DataFrame(columns=['id', 'title', 'author', 'genre', 'publisher', 'year'])


def clean_price(price_str):
    if pd.isna(price_str) or price_str == '':
        return 0.0
    price_str = str(price_str).strip()
    is_euro = '€' in price_str
    nums = re.findall(r'\d+', price_str)
    if not nums:
        return 0.0
    if len(nums) == 1:
        val = float(nums[0])
    else:
        val = float(f"{nums[0]}.{nums[1]}")
    if is_euro:
        val = val * 1.2
    return val


def parse_custom_dates(timestamp_series):
    s = timestamp_series.astype(str)
    s = s.str.replace(';', ' ', regex=False)
    s = s.str.replace(',', ' ', regex=False)
    return pd.to_datetime(s, format='mixed', dayfirst=False, errors='coerce')


def resolve_users(users_df):
    G = nx.Graph()
    for uid in users_df['id']:
        G.add_node(uid)

    email_map, phone_map, address_map = {}, {}, {}

    for _, row in users_df.iterrows():
        uid = row['id']

        if pd.notna(row['email']) and str(row['email']).strip() != "":
            email = str(row['email']).lower().strip()
            if email in email_map:
                G.add_edge(uid, email_map[email])
            email_map[email] = uid

        if pd.notna(row['phone']) and str(row['phone']).strip() != "":
            phone = re.sub(r'\D', '', str(row['phone']))
            if phone:
                if phone in phone_map:
                    G.add_edge(uid, phone_map[phone])
                phone_map[phone] = uid

        if pd.notna(row['address']) and str(row['address']).strip() != "":
            addr = str(row['address']).strip().lower()
            if addr in address_map:
                G.add_edge(uid, address_map[addr])
            address_map[addr] = uid

    mapping = {}
    grouped_ids = {}
    for component in nx.connected_components(G):
        component = list(component)
        canonical_id = component[0]
        grouped_ids[canonical_id] = sorted(component)
        for uid in component:
            mapping[uid] = canonical_id

    return mapping, grouped_ids


def normalize_authors(auth_str):
    if not isinstance(auth_str, str):
        return "Unknown"
    parts = sorted([a.strip() for a in auth_str.split(',')])
    return ", ".join(parts)


def load_and_process_data(folder_name):
    try:
        books = parse_books_yml(f"{folder_name}/books.yaml")
        orders = pd.read_parquet(f"{folder_name}/orders.parquet")
        users = pd.read_csv(f"{folder_name}/users.csv")
    except Exception as e:
        st.error(f"Error loading {folder_name}: {e}")
        return None

    if orders.empty:
        st.warning(f"No orders found in {folder_name}")
        return None

    orders['date_obj'] = parse_custom_dates(orders['timestamp'])
    orders['date_str'] = orders['date_obj'].dt.strftime('%Y-%m-%d')
    orders['clean_price'] = orders['unit_price'].apply(clean_price)
    orders['paid_price'] = orders['quantity'] * orders['clean_price']

    user_map, grouped_ids = resolve_users(users)
    orders['real_user_id'] = orders['user_id'].map(user_map).fillna(orders['user_id'])

    daily_rev = orders.groupby('date_str')['paid_price'].sum().sort_values(ascending=False)
    top_5_days = daily_rev.head(5)
    top_5_days_list = top_5_days.index.tolist()
    top_5_days_values = top_5_days.values.tolist()

    unique_users_count = len(set(user_map.values()))

    merged = orders.merge(books, left_on='book_id', right_on='id', how='left')
    merged['author_set'] = merged['author'].apply(normalize_authors)
    unique_author_sets = merged['author_set'].nunique()

    if not merged.empty and 'author_set' in merged.columns:
        author_sales = merged.groupby('author_set')['quantity'].sum()
        if not author_sales.empty:
            top_author = author_sales.idxmax()
            top_author_sales = author_sales.max()
        else:
            top_author = "No Data"
            top_author_sales = 0
    else:
        top_author = "No Data"
        top_author_sales = 0

    user_spending = orders.groupby('real_user_id')['paid_price'].sum()
    if not user_spending.empty:
        top_spender_real_id = user_spending.idxmax()
        top_spender_amount = user_spending.max()
        top_buyer_aliases = grouped_ids.get(top_spender_real_id, [top_spender_real_id])
    else:
        top_buyer_aliases = []
        top_spender_amount = 0

    daily_rev_sorted = orders.groupby('date_obj')['paid_price'].sum().sort_index().reset_index()
    daily_rev_sorted.columns = ['Date', 'Revenue']

    total_revenue = orders['paid_price'].sum()
    date_min = orders['date_obj'].min()
    date_max = orders['date_obj'].max()

    return {
        "top_5_days": top_5_days_list,
        "top_5_days_values": top_5_days_values,
        "unique_users": unique_users_count,
        "unique_authors": unique_author_sets,
        "top_author": top_author,
        "top_author_sales": top_author_sales,
        "top_buyer_ids": top_buyer_aliases,
        "top_spender_amount": top_spender_amount,
        "daily_revenue_df": daily_rev_sorted,
        "total_revenue": total_revenue,
        "total_orders": len(orders),
        "date_range": (date_min, date_max)
    }


st.title("📈 Bookstore Analytics Dashboard")
st.markdown("**Solution for Task 4** | by: **Sai Koushik Neriyanuri**")

tab1, tab2, tab3 = st.tabs(["DATA1", "DATA2", "DATA3"])


def render_tab(folder_name):
    data = load_and_process_data(folder_name)
    if not data:
        return

    with st.sidebar:
        st.markdown(f"### 📁 {folder_name}")
        st.success(f"{data['total_orders']:,} orders loaded")
        if data['date_range'][0] and data['date_range'][1]:
            st.info(f"{data['date_range'][0].strftime('%Y-%m-%d')} to {data['date_range'][1].strftime('%Y-%m-%d')}")
        st.markdown(
            f"<p style='color: #aaaaaa; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0;'>TOTAL REVENUE</p><p style='color: #00ff00; font-size: 2.5rem; font-weight: 700; margin-top: 0;'>${data['total_revenue']:,.2f}</p>",
            unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 📊 Key Metrics")

        with st.container():
            metric_col1, metric_col2 = st.columns(2)
            with metric_col1:
                st.markdown(
                    f"<p style='color: #aaaaaa; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0;'>UNIQUE USERS</p><p style='color: #00ff00; font-size: 2.5rem; font-weight: 700; margin-top: 0;'>{data['unique_users']}</p>",
                    unsafe_allow_html=True)
            with metric_col2:
                st.markdown(
                    f"<p style='color: #aaaaaa; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0;'>UNIQUE AUTHOR SETS</p><p style='color: #00ff00; font-size: 2.5rem; font-weight: 700; margin-top: 0;'>{data['unique_authors']}</p>",
                    unsafe_allow_html=True)

        st.markdown("")
        st.info(f"**Most Popular Author:** {data['top_author']}  \n**Books Sold:** {data['top_author_sales']:,}")

        st.markdown("### 📅 Top 5 Days by Revenue")

        top_days_df = pd.DataFrame({
            'Rank': ['1', '2', '3', '4', '5'],
            'Date': data['top_5_days'],
            'Revenue': [f"${val:,.2f}" for val in data['top_5_days_values']]
        })
        st.dataframe(top_days_df, hide_index=True, use_container_width=True)

    with col2:
        st.markdown("### 🏆 Best Buyer")
        st.markdown(
            f"<p style='color: #aaaaaa; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0;'>TOTAL SPENT</p><p style='color: #00ff00; font-size: 2.5rem; font-weight: 700; margin-top: 0;'>${data['top_spender_amount']:,.2f}</p>",
            unsafe_allow_html=True)
        st.write("**Identified Aliases (User IDs):**")
        st.code(str(data['top_buyer_ids']), language="json")

        st.markdown("### 💵 Daily Revenue")

        df_chart = data['daily_revenue_df']

        fig = px.line(
            df_chart,
            x='Date',
            y='Revenue',
            title="",
            labels={'Revenue': 'Revenue ($)', 'Date': 'Date'}
        )

        fig.update_layout(
            plot_bgcolor='#000000',
            paper_bgcolor='#000000',
            font_color='#ffffff',
            xaxis_showgrid=False,
            yaxis_showgrid=True,
            yaxis_gridcolor='#222222',
            showlegend=False,
            hovermode="x unified",
            height=400,
            margin=dict(l=0, r=0, t=20, b=0)
        )

        fig.update_traces(line=dict(width=2, color='#00FF00'))
        fig.update_yaxes(tickprefix="$", tickformat=",.0f")

        st.plotly_chart(fig, use_container_width=True)


with tab1:
    render_tab("DATA1")

with tab2:
    render_tab("DATA2")

with tab3:
    render_tab("DATA3")