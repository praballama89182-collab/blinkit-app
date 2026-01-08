import streamlit as st
import pandas as pd
import io
import plotly.graph_objects as go
from thefuzz import process

# 1. PAGE SETUP
st.set_page_config(page_title="Blinkit Ads Intelligence Pro", layout="wide")

def main():
    st.title("🚀 Blinkit Ads Strategic Decision Engine")
    st.markdown("Analyze Performance, Weekly Trends, and Funnel Metrics to drive ROAS.")

    # 2. SIDEBAR CONFIGURATION
    st.sidebar.header("🎯 Strategy Parameters")
    target_roas = st.sidebar.slider("Target ROAS Threshold", 0.5, 5.0, 1.4, step=0.1)
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

            # Mapping Target Identifiers
            if 'Keyword' in master_df.columns: master_df['Target'] = master_df['Keyword']
            elif 'Category Name' in master_df.columns: master_df['Target'] = master_df['Category Name']
            elif 'Asset' in master_df.columns: master_df['Target'] = master_df['Asset']
            else: master_df['Target'] = "N/A"

            # Date Conversion and Weekly Sorting
            if 'date_ist' in master_df.columns:
                master_df['date_ist'] = pd.to_datetime(master_df['date_ist'])
                master_df['Day of Week'] = master_df['date_ist'].dt.day_name()
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                master_df['Day of Week'] = pd.Categorical(master_df['Day of Week'], categories=day_order, ordered=True)

            # Numeric Conversion
            numeric_cols = ['Direct Sales', 'Estimated Budget Consumed', 'CPM', 'Direct RoAS']
            for col in numeric_cols:
                if col in master_df.columns:
                    master_df[col] = pd.to_numeric(master_df[col], errors='coerce').fillna(0)

            # --- FUZZY CAMPAIGN SEARCH ---
            st.sidebar.markdown("---")
            st.sidebar.header("🔍 Search Campaign")
            all_campaigns = sorted(master_df['Campaign Name'].dropna().unique().tolist())
            search_query = st.sidebar.text_input("Type to find similar campaigns", "")
            
            if search_query:
                matches = process.extract(search_query, all_campaigns, limit=10)
                filtered_options = [match[0] for match in matches if match[1] > 45]
                campaign_options = ["All Campaigns"] + filtered_options
            else:
                campaign_options = ["All Campaigns"] + all_campaigns
            selected_campaign = st.sidebar.selectbox("Select Campaign", campaign_options)

            # Apply Filtering
            plot_df = master_df if selected_campaign == "All Campaigns" else master_df[master_df['Campaign Name'] == selected_campaign]

            # --- 4. BIFURCATED TABS ---
            tab_trend, tab_perf, tab_eff, tab_bids = st.tabs(["📅 Weekly Trends", "🏆 Performance", "🛑 Waste Audit", "⚖️ Bidding"])

            with tab_trend:
                st.header(f"Weekly Trend Analysis: {selected_campaign}")
                if 'Day of Week' in plot_df.columns:
                    weekly_data = plot_df.groupby('Day of Week', observed=False).agg({
                        'Estimated Budget Consumed': 'sum',
                        'Direct Sales': 'sum'
                    }).reset_index()

                    # Create Grouped Bar + Line Chart
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=weekly_data['Day of Week'], y=weekly_data['Estimated Budget Consumed'], 
                                         name='Budget Spent (₹)', marker_color='#1f77b4'))
                    fig.add_trace(go.Bar(x=weekly_data['Day of Week'], y=weekly_data['Direct Sales'], 
                                         name='Direct Sales (₹)', marker_color='#2ca02c'))
                    
                    # Add ROAS Trend Line on Secondary Axis
                    weekly_data['ROAS'] = weekly_data['Direct Sales'] / weekly_data['Estimated Budget Consumed'].replace(0, 1)
                    fig.add_trace(go.Scatter(x=weekly_data['Day of Week'], y=weekly_data['ROAS'], 
                                             name='ROAS Trend', yaxis='y2', line=dict(color='#d62728', width=3)))

                    fig.update_layout(
                        title='Budget Spent vs Direct Sales with ROAS Trend Line',
                        xaxis_title='Day of the Week (Mon - Sun)',
                        yaxis=dict(title='Amount (₹)'),
                        yaxis2=dict(title='ROAS', overlaying='y', side='right', range=[0, weekly_data['ROAS'].max() + 1]),
                        barmode='group',
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Missing date data for weekly analysis.")

            with tab_perf:
                st.subheader("Top Revenue Contributors")
                summary = plot_df.groupby(['Target', 'Campaign Name']).agg({'Direct Sales': 'sum', 'Direct RoAS': 'mean'}).sort_values(by='Direct Sales', ascending=False)
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**✅ Healthy Assets (ROAS >= Threshold)**")
                    st.dataframe(summary[summary['Direct RoAS'] >= target_roas], use_container_width=True)
                with c2:
                    st.write("**⚠️ Below Target (ROAS < Threshold)**")
                    st.dataframe(summary[(summary['Direct RoAS'] < target_roas) & (summary['Direct RoAS'] > 0)], use_container_width=True)

            with tab_eff:
                st.subheader("Inefficiency & Pause Suggestions")
                pause_logic = plot_df[(plot_df['Direct Sales'] == 0) & (plot_df['Estimated Budget Consumed'] > min_spend_waste)]
                st.warning(f"Pause these: Spent > ₹{min_spend_waste} with 0 Direct Sales")
                st.dataframe(pause_logic[['Target', 'Campaign Name', 'Estimated Budget Consumed', 'CPM']], use_container_width=True)

            with tab_bids:
                st.subheader("Actionable Bidding Strategy")
                avg_cpm = plot_df['CPM'].mean()
                st.info("High ROAS/Sales but High CPM. Recommendation: Decrease bid to improve profit.")
                cpm_opt = plot_df[(plot_df['Direct RoAS'] >= target_roas) & (plot_df['CPM'] > avg_cpm)]
                st.dataframe(cpm_opt[['Target', 'Campaign Name', 'CPM', 'Direct RoAS', 'Direct Sales']], use_container_width=True)

            # 5. EXPORT
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                plot_df.to_excel(writer, index=False)
            st.download_button("📥 Download Analysis", data=buffer.getvalue(), file_name="blinkit_strategy.xlsx")

if __name__ == "__main__":
    main()
