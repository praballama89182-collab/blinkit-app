import streamlit as st
import pandas as pd
import io

# Set Page Config
st.set_page_config(page_title="Blinkit Ads Optimizer Pro", layout="wide")

st.title("🎯 Blinkit Bid & ROAS Optimizer")
st.markdown("Analyze Cannibalization, track CPM, and get automated Bid Reduction suggestions to hit your 1.4 ROAS target.")

# --- File Upload ---
uploaded_files = st.sidebar.file_uploader("Upload Search Term Reports (CSV)", type="csv", accept_multiple_files=True)

def process_data(files):
    all_data = []
    for f in files:
        temp_df = pd.read_csv(f)
        temp_df.columns = [c.strip() for c in temp_df.columns]
        # Identify if it's Keyword or Category based on columns
        if 'Keyword' in temp_df.columns:
            temp_df = temp_df.rename(columns={'Keyword': 'Identifier'})
        elif 'Category Name' in temp_df.columns:
            temp_df = temp_df.rename(columns={'Category Name': 'Identifier'})
        all_data.append(temp_df)
    return pd.concat(all_data, ignore_index=True) if all_data else None

if uploaded_files:
    df = process_data(uploaded_files)
    
    # Data Cleaning & Formatting
    cols = ['Direct Sales', 'Estimated Budget Consumed', 'Direct RoAS', 'CPM', 'Impressions']
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Sidebar Settings
    target_roas = st.sidebar.slider("Target ROAS Threshold", 0.5, 5.0, 1.4)
    min_spend_flag = st.sidebar.number_input("Min Spend to Flag 'No Sales'", value=100)

    # Grouping Data for Analysis
    analysis = df.groupby(['Identifier', 'Campaign Name']).agg({
        'CPM': 'mean',
        'Estimated Budget Consumed': 'sum',
        'Direct Sales': 'sum',
        'Direct RoAS': 'mean',
        'Impressions': 'sum'
    }).reset_index()

    # --- 1. Bid Optimization Logic ---
    def get_bid_suggestion(row):
        roas = row['Direct RoAS']
        curr_cpm = row['CPM']
        spend = row['Estimated Budget Consumed']
        
        if roas >= target_roas:
            return "✅ HEALTHY", "Maintain or Scale Bid", curr_cpm
        elif 0 < roas < target_roas:
            # Formula: New Bid = Current Bid * (Current ROAS / Target ROAS)
            reduction_pct = (1 - (roas / target_roas)) * 100
            new_bid = curr_cpm * (roas / target_roas)
            return "⚠️ INEFFICIENT", f"Reduce Bid by {reduction_pct:.1f}%", new_bid
        elif spend > min_spend_flag:
            return "🛑 CRITICAL", "Pause: High Waste / No Sales", 0
        else:
            return "🔍 MONITOR", "Low Data", curr_cpm

    analysis[['Status', 'Action', 'Suggested CPM']] = analysis.apply(
        lambda x: pd.Series(get_bid_suggestion(x)), axis=1
    )

    # --- 2. Cannibalization Detection ---
    counts = analysis['Identifier'].value_counts()
    cannibal_list = counts[counts > 1].index.tolist()
    analysis['Is Cannibalized'] = analysis['Identifier'].isin(cannibal_list)

    # --- Tabs for Visualization ---
    tab1, tab2, tab3 = st.tabs(["📉 Bid Optimization", "⚔️ Cannibalization Auditor", "📥 Export Report"])

    with tab1:
        st.subheader(f"Bid Management (Target ROAS: {target_roas})")
        
        # Performance Filter
        status_filter = st.multiselect("Filter by Status", options=["✅ HEALTHY", "⚠️ INEFFICIENT", "🛑 CRITICAL"], default=["⚠️ INEFFICIENT", "🛑 CRITICAL"])
        filtered_df = analysis[analysis['Status'].isin(status_filter)]
        
        st.dataframe(filtered_df[[
            'Identifier', 'Campaign Name', 'CPM', 'Direct RoAS', 
            'Status', 'Action', 'Suggested CPM'
        ]].sort_values(by='Direct RoAS', ascending=True), use_container_width=True)

    with tab2:
        st.subheader("Keyword Cannibalization")
        st.info("These keywords appear in multiple campaigns. Consolidate budget into the campaign with the higher ROAS.")
        cannibal_df = analysis[analysis['Is Cannibalized'] == True].sort_values(by='Identifier')
        st.write(cannibal_df[['Identifier', 'Campaign Name', 'CPM', 'Direct RoAS', 'Status']])

    with tab3:
        st.subheader("Download Optimization Plan")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            analysis.to_excel(writer, sheet_name='Full Optimization Report', index=False)
        
        st.download_button(
            label="Download Excel Report",
            data=output.getvalue(),
            file_name="blinkit_bid_strategy.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("Upload your CSV files to see the optimized bid suggestions.")
