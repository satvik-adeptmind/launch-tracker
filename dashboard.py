import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import io
import os
import config

# --- CONFIGURATION ---
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
CSV_URL = "https://raw.githubusercontent.com/satvik-adeptmind/launch-tracker/main/launches.csv"

st.set_page_config(page_title="Launch Analytics", page_icon="🚀", layout="wide")

# --- CUSTOM CSS FOR METRICS ---
st.markdown("""
<style>
    [data-testid="stMetricValue"] {
        font-size: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# --- LOAD DATA ---
@st.cache_data(ttl=60)
def load_data():
    try:
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        response = requests.get(CSV_URL, headers=headers)
        if response.status_code == 200:
            csv_content = response.content.decode('utf-8')
            df = pd.read_csv(io.StringIO(csv_content))
            df['Date'] = pd.to_datetime(df['Date'])
            # Ensure numeric
            df['Page_Count'] = pd.to_numeric(df['Page_Count'], errors='coerce').fillna(0)
            return df
        else:
            return pd.DataFrame(columns=["Date", "Retailer", "Tranche", "Page_Count", "Approver", "Slack_Link"])
    except Exception:
        return pd.DataFrame(columns=["Date", "Retailer", "Tranche", "Page_Count", "Approver", "Slack_Link"])

df = load_data()

# --- SIDEBAR FILTERS ---
st.sidebar.header("🔍 Filters")
time_frame = st.sidebar.selectbox("Time Period", ["This Week", "Last Week", "This Month", "All Time"])
all_retailers = sorted(config.RETAILERS.keys())
selected_retailers = st.sidebar.multiselect("Select Retailers", options=all_retailers, default=all_retailers)

# --- DATE LOGIC & FILTERING ---
today = datetime.now()
start_date = df['Date'].min() if not df.empty else today
previous_start_date = start_date # For delta calculation

if time_frame == "This Week":
    start_date = today - timedelta(days=today.weekday())
    previous_start_date = start_date - timedelta(days=7)
elif time_frame == "Last Week":
    start_date = today - timedelta(days=today.weekday()) - timedelta(days=7)
    end_date = today - timedelta(days=today.weekday())
    previous_start_date = start_date - timedelta(days=7)
elif time_frame == "This Month":
    start_date = today.replace(day=1)
    previous_start_date = (start_date - timedelta(days=1)).replace(day=1)

# Apply Filters
if not df.empty:
    # Current Period Data
    mask = (df['Date'] >= start_date) & (df['Retailer'].isin(selected_retailers))
    if time_frame == "Last Week":
        mask = mask & (df['Date'] < end_date)
    df_filtered = df[mask]

    # Previous Period Data (For Delta Comparison)
    prev_mask = (df['Date'] >= previous_start_date) & (df['Date'] < start_date) & (df['Retailer'].isin(selected_retailers))
    df_prev = df[prev_mask]
else:
    df_filtered = df
    df_prev = df

# --- MAIN DASHBOARD ---
st.title(f"🚀 Dashboard: {time_frame}")

if df_filtered.empty:
    st.info("No launches found for this period.")
else:
    # --- 1. KPI METRICS WITH DELTAS ---
    # Calculate current metrics
    curr_pages = df_filtered['Page_Count'].sum()
    curr_launches = len(df_filtered)
    curr_retailers = df_filtered['Retailer'].nunique()

    # Calculate previous metrics
    prev_pages = df_prev['Page_Count'].sum()
    prev_launches = len(df_prev)
    
    # Calculate Deltas
    delta_pages = curr_pages - prev_pages
    delta_launches = curr_launches - prev_launches

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Pages", f"{int(curr_pages):,}", delta=f"{int(delta_pages)} vs prev")
    c2.metric("Total Launches", curr_launches, delta=f"{delta_launches} vs prev")
    c3.metric("Active Retailers", curr_retailers)
    
    # Average Pages per Launch
    avg_pages = int(curr_pages / curr_launches) if curr_launches > 0 else 0
    c4.metric("Avg Pages / Launch", avg_pages)

    st.markdown("---")

    # --- 2. TABS FOR DIFFERENT VIEWS ---
    # Removed "Team Stats" and replaced with "Schedules & Info"
    tab1, tab2, tab3 = st.tabs(["📊 Trends & Volume", "ℹ️ Schedules & Info", "📝 Detailed Logs"])

    with tab1:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📅 Launch Activity Over Time")
            # Group by Day
            daily_counts = df_filtered.groupby(df_filtered['Date'].dt.date).size().reset_index(name='Launches')
            fig_timeline = px.bar(daily_counts, x='Date', y='Launches', title="Daily Launch Frequency", color_discrete_sequence=['#00CC96'])
            st.plotly_chart(fig_timeline, use_container_width=True)

        with col2:
            st.subheader("📦 Volume by Retailer")
            # Group by Retailer
            retailer_counts = df_filtered.groupby('Retailer')['Page_Count'].sum().reset_index().sort_values('Page_Count', ascending=True)
            fig_retailer = px.bar(retailer_counts, x='Page_Count', y='Retailer', orientation='h', text_auto='.2s', color='Page_Count', color_continuous_scale='Bluered')
            fig_retailer.update_layout(showlegend=False)
            st.plotly_chart(fig_retailer, use_container_width=True)

    with tab2:
        st.subheader("ℹ️ Retailer Schedules & Notes")
        st.markdown("Specific notes defined in `config.py` for the selected retailers.")
        
        # Display the config info
        schedule_data = []
        for r in selected_retailers:
            if r in config.RETAILER_INFO:
                schedule_data.append({"Retailer": r, "Schedule/Note": config.RETAILER_INFO[r]})
        
        if schedule_data:
            st.dataframe(pd.DataFrame(schedule_data), hide_index=True, use_container_width=True)
        else:
            st.info("No specific schedule notes found for the currently selected retailers.")

    with tab3:
        st.subheader("📝 Launch Logs")
        
        st.dataframe(
            df_filtered.sort_values("Date", ascending=False),
            column_config={
                "Slack_Link": st.column_config.LinkColumn("Slack Link", display_text="View Msg"),
                "Date": st.column_config.DatetimeColumn("Launch Date", format="D MMM, HH:mm"),
                "Page_Count": st.column_config.NumberColumn("Pages", format="%d 📄"),
            },
            use_container_width=True
        )