import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import config # <--- IMPORT CONFIG

st.set_page_config(page_title="Adeptmind Launch Analytics", page_icon="🚀", layout="wide")

# --- LOAD DATA ---
def load_data():
    try:
        df = pd.read_csv("launches.csv")
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=["Date", "Retailer", "Tranche", "Page_Count", "Approver", "Slack_Link"])

df = load_data()

# --- SIDEBAR ---
st.sidebar.header("🔍 Filters")

# Time Filter
time_frame = st.sidebar.selectbox("Time Period", ["This Week", "Last Week", "This Month", "All Time"])

# Retailer Filter (Populated from CONFIG, not just CSV)
# This ensures all 50 retailers are visible in the dropdown
all_retailers_list = sorted(config.RETAILERS.keys())
selected_retailers = st.sidebar.multiselect("Select Retailers", options=all_retailers_list, default=all_retailers_list)

# --- FILTER LOGIC ---
if not df.empty:
    # Filter by Retailer
    df_filtered = df[df['Retailer'].isin(selected_retailers)]
    
    # Filter by Date
    today = datetime.now()
    if time_frame == "This Week":
        start_date = today - timedelta(days=today.weekday())
        df_filtered = df_filtered[df_filtered['Date'] >= start_date]
    elif time_frame == "Last Week":
        start_week = today - timedelta(days=today.weekday()) - timedelta(days=7)
        end_week = today - timedelta(days=today.weekday())
        df_filtered = df_filtered[(df_filtered['Date'] >= start_week) & (df_filtered['Date'] < end_week)]
    elif time_frame == "This Month":
        start_date = today.replace(day=1)
        df_filtered = df_filtered[df_filtered['Date'] >= start_date]

    # --- MAIN VIEW ---
    st.title(f"🚀 Dashboard: {time_frame}")
    
    # Top Metrics
    total_pages = df_filtered['Page_Count'].sum()
    total_launches = len(df_filtered)
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Pages", f"{total_pages:,}")
    m2.metric("Total Launches", total_launches)
    m3.metric("Active Retailers", df_filtered['Retailer'].nunique())
    
    st.markdown("---")

    # --- CHARTS ---
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("📊 Volume by Retailer")
        if not df_filtered.empty:
            # Sort by volume
            chart_data = df_filtered.groupby('Retailer')['Page_Count'].sum().reset_index().sort_values('Page_Count', ascending=True)
            fig = px.bar(chart_data, x='Page_Count', y='Retailer', orientation='h', text_auto='.2s', title="Page Volume")
            st.plotly_chart(fig, use_container_width=True)
            
    with c2:
        st.subheader("ℹ️ Client Info")
        # Show metadata for selected retailers (if only a few are selected)
        if len(selected_retailers) < 10:
            for r in selected_retailers:
                # Get frequency from config, default to Monthly
                freq = config.RETAILER_INFO.get(r, "Monthly")
                st.info(f"**{r}**: {freq}")
        else:
            st.write("Select fewer retailers to see specific schedule details.")

    # --- TABLE ---
    st.subheader("📝 Launch Logs")
    st.dataframe(
        df_filtered.sort_values("Date", ascending=False),
        column_config={"Slack_Link": st.column_config.LinkColumn("Link")},
        use_container_width=True
    )
else:
    st.info("No launches found for this period.")