import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import requests
import io
import os
from github import Github, Auth
import config

# --- CONFIGURATION ---
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
REPO_NAME = "satvik-adeptmind/launch-tracker"
CSV_FILE_PATH = "launches.csv"
CSV_URL = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{CSV_FILE_PATH}"

st.set_page_config(page_title="Launch Analytics", page_icon="🚀", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 2rem; }
</style>
""", unsafe_allow_html=True)

# --- HELPER: LOAD DATA ---
@st.cache_data(ttl=60)
def load_data():
    try:
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        response = requests.get(CSV_URL, headers=headers)

        if response.status_code != 200:
            st.error(f"GitHub Error: Could not access the CSV file (Status: {response.status_code}).")
            st.warning("Please check your GITHUB_TOKEN secret in the Streamlit app settings.")
            return pd.DataFrame(columns=["Date", "Retailer", "Tranche", "Page_Count", "Approver", "Slack_Link"])

        csv_content = response.content.decode('utf-8')
        df = pd.read_csv(io.StringIO(csv_content))
        df['Date'] = pd.to_datetime(df['Date'])
        df['Page_Count'] = pd.to_numeric(df['Page_Count'], errors='coerce').fillna(0)
        return df

    except Exception as e:
        st.error(f"Parsing Error: The launches.csv file might be corrupted.")
        st.warning(f"Please check the file format on GitHub. Details: {e}")
        return pd.DataFrame(columns=["Date", "Retailer", "Tranche", "Page_Count", "Approver", "Slack_Link"])

# --- HELPER: SAVE DATA ---
def save_data_to_github(df_to_save):
    try:
        df_copy = df_to_save.copy()
        df_copy['Date'] = pd.to_datetime(df_copy['Date']).dt.strftime("%Y-%m-%d %H:%M:%S")
        
        csv_buffer = io.StringIO()
        df_copy.to_csv(csv_buffer, index=False)
        new_content = csv_buffer.getvalue()

        auth = Auth.Token(GITHUB_TOKEN)
        g = Github(auth=auth)
        repo = g.get_repo(REPO_NAME)
        
        contents = repo.get_contents(CSV_FILE_PATH)
        repo.update_file(contents.path, "Manual Update via Dashboard", new_content, contents.sha)
        
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error saving to GitHub: {e}")
        return False

# --- SIDEBAR ---
st.sidebar.header("🔍 Filters")

# CHANGED: Removed st.rerun() for stability
if st.sidebar.button("🔄 Force Refresh Data"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared! Change a filter to see updates.")

time_frame = st.sidebar.selectbox("Time Period", ["This Week", "Last Week", "This Month", "All Time"])
all_retailers = sorted(config.RETAILERS.keys())
selected_retailers = st.sidebar.multiselect("Select Retailers", options=all_retailers, default=all_retailers)

# --- Load Data (main call) ---
df = load_data()

# --- DATE LOGIC ---
today = datetime.now()
start_date = df['Date'].min() if not df.empty else today
previous_start_date = start_date

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
    mask = (df['Date'] >= start_date) & (df['Retailer'].isin(selected_retailers))
    if time_frame == "Last Week":
        mask = mask & (df['Date'] < end_date)
    df_filtered = df[mask]
    
    prev_mask = (df['Date'] >= previous_start_date) & (df['Date'] < start_date) & (df['Retailer'].isin(selected_retailers))
    df_prev = df[prev_mask]
else:
    df_filtered = df
    df_prev = df

# --- MAIN DASHBOARD ---
st.title(f"🚀 Dashboard: {time_frame}")

# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Trends", "ℹ️ Schedules", "📝 Logs", "🛠 Manage Data"])

with tab1:
    if df_filtered.empty:
        st.info("No launches found for this period.")
    else:
        curr_pages = df_filtered['Page_Count'].sum()
        curr_launches = len(df_filtered)
        curr_retailers = df_filtered['Retailer'].nunique()
        prev_pages = df_prev['Page_Count'].sum()
        prev_launches = len(df_prev)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Pages", f"{int(curr_pages):,}", delta=f"{int(curr_pages - prev_pages)}")
        c2.metric("Total Launches", curr_launches, delta=f"{curr_launches - prev_launches}")
        c3.metric("Active Retailers", curr_retailers)
        c4.metric("Avg Pages", int(curr_pages / curr_launches) if curr_launches > 0 else 0)
        
        st.markdown("---")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            daily_counts = df_filtered.groupby(df_filtered['Date'].dt.date).size().reset_index(name='Launches')
            fig_timeline = px.bar(daily_counts, x='Date', y='Launches', title="Daily Launch Frequency", color_discrete_sequence=['#00CC96'])
            st.plotly_chart(fig_timeline, use_container_width=True)
        with col2:
            retailer_counts = df_filtered.groupby('Retailer')['Page_Count'].sum().reset_index().sort_values('Page_Count', ascending=True)
            fig_retailer = px.bar(retailer_counts, x='Page_Count', y='Retailer', orientation='h', text_auto='.2s', color='Page_Count', color_continuous_scale='Bluered')
            fig_retailer.update_layout(showlegend=False)
            st.plotly_chart(fig_retailer, use_container_width=True)

with tab2:
    st.subheader("ℹ️ Retailer Schedules")
    schedule_data = [{"Retailer": r, "Schedule/Note": config.RETAILER_INFO.get(r, "Monthly")} for r in selected_retailers]
    st.dataframe(pd.DataFrame(schedule_data), hide_index=True, use_container_width=True)

with tab3:
    st.subheader("📝 Launch Logs (Read Only)")
    st.dataframe(
        df_filtered.sort_values("Date", ascending=False),
        column_config={
            "Slack_Link": st.column_config.LinkColumn("Link", display_text="View"),
            "Date": st.column_config.DatetimeColumn("Date", format="D MMM, HH:mm"),
            "Page_Count": st.column_config.NumberColumn("Pages", format="%d 📄"),
        },
        use_container_width=True
    )

with tab4:
    st.subheader("🛠 Manage Data")
    st.warning("⚠️ Changes made here will permanently update the CSV on GitHub.")
    
    with st.expander("➕ Add Missing Launch"):
        with st.form("add_launch_form"):
            c1, c2 = st.columns(2)
            new_retailer = c1.selectbox("Retailer", options=all_retailers)
            new_tranche = c2.text_input("Tranche (e.g., T1)", value="T1")
            
            c3, c4 = st.columns(2)
            new_pages = c3.number_input("Page Count", min_value=0, value=0)
            new_approver = c4.text_input("Approver Name", value="Manual Admin")
            
            new_date = st.date_input("Date", value=datetime.now())
            new_time = st.time_input("Time", value=datetime.now().time())
            
            submitted = st.form_submit_button("Add Launch")
            
            if submitted:
                full_datetime = datetime.combine(new_date, new_time)
                new_row = pd.DataFrame([{"Date": full_datetime, "Retailer": new_retailer, "Tranche": new_tranche, "Page_Count": new_pages, "Approver": new_approver, "Slack_Link": "Manual Entry"}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                if save_data_to_github(updated_df):
                    st.success("✅ Launch added successfully! Refreshing...")
                    st.rerun()

    st.write("### ✏️ Edit or Delete Rows")
    st.info("Select rows and press 'Delete' on your keyboard to remove them. Double click cells to edit.")
    
    df_sorted = df.sort_values("Date", ascending=False)
    edited_df = st.data_editor(
        df_sorted,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Date": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm:ss"),
            "Retailer": st.column_config.SelectboxColumn(options=all_retailers),
        },
        key="data_editor"
    )

    if st.button("💾 Save Changes to GitHub"):
        if not edited_df.equals(df_sorted):
            if save_data_to_github(edited_df):
                st.success("✅ Database updated successfully!")
                st.rerun()
        else:
            st.info("No changes detected.")