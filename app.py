import streamlit as st
import pandas as pd
import io
import plotly.graph_objects as go

# We try to use thefuzz for a better search experience, 
# but include a fallback for the sidebar search.
try:
    from thefuzz import process
    HAS_THEFUZZ = True
except ImportError:
    HAS_THEFUZZ = False

# 1. PAGE SETUP
st.set_page_config(page_title="Blinkit Ads Strategic Engine", layout="wide")

def main():
    st.title("🚀 Blinkit Ads Strategic Decision Engine")
    st.markdown("Comprehensive analysis of Weekly Trends, ROAS Efficiency, and Bidding Strategy.")

    # 2. SIDEBAR CONFIGURATION - REFINED THRESHOLDS
    st.sidebar.header("🎯 Strategy Parameters")
    # This single threshold now controls "Healthy", "Below Target", and "Bidding Strategy"
    target_roas = st.sidebar.slider("ROAS Threshold (Global Target)", 0.5, 5.0, 1.4, step=0.1)
    min_spend_waste = st.sidebar.number_input("Min Spend to Flag Waste (₹)", value=200)

    uploaded_files = st.file_uploader("Upload Blinkit CSV/Excel Reports", type=['csv', 'xlsx'], accept_multiple_files=True)

    if uploaded_files:
        all_dfs = []
        for file in uploaded_files:
            try:
                if file.name.endswith('.xlsx'):
                    xl = pd.ExcelFile(file)
                    for sheet in xl.sheet_names:
                        df = pd.read_excel(file, sheet_name=sheet)
                        all_dfs.append(df)
                else:
                    all_dfs.append(pd.read_csv(file))
            except Exception as e:
                st.error(f"Error reading {file.name}: {e}")

        if all_dfs:
            # 3. CONSOLIDATION & CLEANING
            master_df = pd.concat(all_dfs, ignore_index=True, sort=False)
            master_df.columns = master_df.columns.str.strip()

            # Mapping Target Identifiers (Keyword / Category / Asset)
            if 'Keyword' in master_df.columns: 
                master_df['Target'] = master_df['Keyword']
            elif 'Category Name' in master_df.columns: 
                master_df['Target'] = master_df['Category Name']
            elif 'Asset' in master_df.columns: 
                master_df['Target'] = master_df['Asset']
            else: 
                master_df['Target'] = "N/A"

            # Date Conversion and Weekly Sorting
            if 'date_ist' in master_df.columns:
                master_df['date_ist'] = pd.to_datetime(master_df['date_ist'])
                master_df['Day of Week'] = master_df['date_ist'].dt.day_name()
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                master_df['Day of Week'] = pd.Categorical(master_df['Day of Week'], categories=day_order, ordered=True)

            # Numeric Conversion for critical fields
            numeric_cols = ['Direct Sales', 'Estimated Budget Consumed', 'CPM', 'Direct RoAS', 'Impressions', 'Most Viewed Position']
            for col in numeric_cols:
                if col in master_df.columns:
                    master_df[col] = pd.to_numeric(master_df[col], errors='coerce').fillna(0)

            # --- SEARCH & FILTER ---
            st.sidebar.markdown("---")
            st.sidebar.header("🔍 Search Campaign")
            all_campaigns = sorted(master_df['Campaign Name'].dropna().unique().tolist())
            search_query = st.sidebar.text_input("Type to find similar campaigns", "")
            
            if search_query:
                if HAS_THEFUZZ:
                    matches = process.extract(search_query, all_campaigns, limit=10)
                    filtered_options = [match[0] for match in matches if match[1] > 45]
                else:
                    # Fallback if thefuzz is not installed
                    filtered_options = [c for c in all_campaigns if search_query.lower() in c.lower()][:10]
                
                campaign_options = ["All Campaigns"] + filtered_options
            else:
                campaign_options = ["All Campaigns"] + all_campaigns
            
            selected_campaign = st.sidebar.selectbox("Select Campaign", campaign_options)

            # Filter data based on selection
            plot_df = master_df if selected_campaign == "All Campaigns" else master_df[master_df['Campaign Name'] == selected_campaign]

            # --- AGGREGATION LOGIC (Unique per Campaign) ---
            # Summing spend/sales so keywords don't repeat for the same campaign
            summary_df = plot_df.groupby(['Target', 'Campaign Name'], as_index=False).agg({
                'Direct Sales': 'sum',
                'Estimated Budget Consumed': 'sum',
                'Impressions': 'sum',
                'CPM': 'mean',
                'Most Viewed Position': 'mean'
            })
            # Calculate unique aggregated ROAS
            summary_df['Aggregated ROAS'] = summary_df['Direct Sales'] / summary_df['Estimated Budget Consumed'].replace(0, 1)

            # --- TABS ---
            tab_trend, tab_perf, tab_eff, tab_bids = st.tabs(["📅 Weekly Trends", "🏆 Performance Summary", "🛑 Waste Audit", "⚖️ Bidding Strategy"])

            with tab_trend:
                st.header(f"Weekly Trend Analysis: {selected_campaign}")
                if 'Day of Week' in plot_df.columns:
                    weekly_data = plot_df.groupby('Day of Week', observed=False).agg({
                        'Estimated Budget Consumed': 'sum',
                        'Direct Sales': 'sum'
                    }).reset_index()

                    # Create Grouped Bar + Line Chart with "Cool" Color Codes
                    # Colors: Soft Blue (#4A90E2), Teal/Aqua (#50E3C2), Vibrant Purple (#AB63FA)
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=weekly_data['Day of Week'], 
                        y=weekly_data['Estimated Budget Consumed'], 
                        name='Budget Spent (₹)', 
                        marker_color='#4A90E2' 
                    ))
                    fig.add_trace(go.Bar(
                        x=weekly_data['Day of Week'], 
                        y=weekly_data['Direct Sales'], 
                        name='Direct Sales (₹)', 
                        marker_color='#50E3C2'
                    ))
                    
                    # ROAS Trend Line
                    weekly_data['ROAS'] = weekly_data['Direct Sales'] / weekly_data['Estimated Budget Consumed'].replace(0, 1)
                    fig.add_trace(go.Scatter(
                        x=weekly_data['Day of Week'], 
                        y=weekly_data['ROAS'], 
                        name='ROAS Trend', 
                        yaxis='y2', 
                        line=dict(color='#AB63FA', width=4)
                    ))

                    fig.update_layout(
                        title='Budget Spent vs Direct Sales (Mon - Sun)',
                        xaxis_title='Day of the Week',
                        yaxis=dict(title='Amount (₹)', gridcolor='rgba(200,200,200,0.2)'),
                        yaxis2=dict(title='ROAS Efficiency', overlaying='y', side='right', showgrid=False),
                        barmode='group',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Missing date data for weekly analysis.")

            with tab_perf:
                st.subheader("High-Resolution Performance (Aggregated)")
                summary_sorted = summary_df.sort_values(by='Direct Sales', ascending=False)
                
                c1, c2 = st.columns(2)
                with c1:
                    st.success(f"**Healthy Assets (ROAS >= {target_roas})**")
                    above_df = summary_sorted[summary_sorted['Aggregated ROAS'] >= target_roas]
                    st.write(f"Showing {len(above_df)} unique items")
                    st.dataframe(above_df, use_container_width=True, height=500)
                    
                with c2:
                    st.error(f"**Below Target (ROAS < {target_roas})**")
                    below_df = summary_sorted[(summary_sorted['Aggregated ROAS'] < target_roas) & (summary_sorted['Aggregated ROAS'] > 0)]
                    st.write(f"Showing {len(below_df)} unique items")
                    st.dataframe(below_df, use_container_width=True, height=500)

            with tab_eff:
                st.subheader("Waste Audit (Unique Keywords per Campaign)")
                # Keywords with 0 sales but spend > threshold
                pause_logic = summary_df[(summary_df['Direct Sales'] == 0) & (summary_df['Estimated Budget Consumed'] > min_spend_waste)]
                pause_logic = pause_logic.sort_values(by='Estimated Budget Consumed', ascending=False)
                
                st.warning(f"Total {len(pause_logic)} unique items found with high spend and zero sales.")
                st.dataframe(pause_logic[['Target', 'Campaign Name', 'Estimated Budget Consumed', 'Impressions', 'CPM', 'Most Viewed Position']], 
                             use_container_width=True, height=500)

            with tab_bids:
                st.subheader("CPM Optimization Engine")
                # Using the sidebar target_roas consistently
                avg_cpm = summary_df['CPM'].mean()
                cpm_opt = summary_df[(summary_df['Aggregated ROAS'] >= target_roas) & (summary_df['CPM'] > avg_cpm)]
                st.info(f"Identified {len(cpm_opt)} high-volume items (ROAS >= {target_roas}) where decreasing bid could maximize profit.")
                st.dataframe(cpm_opt[['Target', 'Campaign Name', 'CPM', 'Aggregated ROAS', 'Direct Sales']], 
                             use_container_width=True, height=600)

            # 5. EXPORT
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                summary_df.to_excel(writer, index=False, sheet_name='Aggregated_Report')
            st.download_button("📥 Download Final Strategy Sheet", data=buffer.getvalue(), file_name="blinkit_strategy.xlsx")

if __name__ == "__main__":
    main()
