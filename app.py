import streamlit as st
import pandas as pd
import io

# 1. PAGE SETUP
st.set_page_config(page_title="Blinkit Ads Intelligence Pro", layout="wide")

def main():
    st.title("🚀 Blinkit Ads Strategic Decision Engine")
    st.markdown("Analyze Performance, Efficiency, Halo Effects, and Funnel Metrics to drive ROAS.")

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

            # Numeric Conversion
            numeric_cols = [
                'Direct Sales', 'Indirect Sales', 'Estimated Budget Consumed', 
                'CPM', 'Direct RoAS', 'Total RoAS', 'Impressions', 
                'Direct ATC', 'New Users', 'Most Viewed Position'
            ]
            for col in numeric_cols:
                if col in master_df.columns:
                    master_df[col] = pd.to_numeric(master_df[col], errors='coerce').fillna(0)

            # --- 4. ADVANCED CALCULATIONS ---
            # Halo Effect & Growth
            master_df['Total Revenue'] = master_df['Direct Sales'] + master_df.get('Indirect Sales', 0)
            master_df['Halo ROAS'] = master_df['Total Revenue'] / master_df['Estimated Budget Consumed'].replace(0, 1)
            master_df['CAC'] = master_df['Estimated Budget Consumed'] / master_df['New Users'].replace(0, 1)
            
            # Funnel Metrics
            master_df['ATC Rate %'] = (master_df['Direct ATC'] / master_df['Impressions'].replace(0, 1)) * 100
            
            # Bid Correction Logic
            def get_bid_advice(row):
                cpm = row.get('CPM', 0)
                roas = row.get('Direct RoAS', 0)
                if roas > 0 and cpm > 0:
                    suggested = cpm * (roas / target_roas)
                    diff = ((suggested - cpm) / cpm) * 100
                    return suggested, diff
                return cpm, 0

            master_df[['Suggested CPM', 'Bid Change %']] = master_df.apply(
                lambda x: pd.Series(get_bid_advice(x)), axis=1
            )

            # --- 5. BIFURCATED TABS ---
            tab_perf, tab_eff, tab_funnel, tab_growth, tab_bids = st.tabs([
                "🏆 Performance", "🛑 Waste Audit", "🌪️ Funnel & Halo", "📈 Growth (CAC)", "⚖️ Bidding"
            ])

            with tab_perf:
                st.subheader("Top Revenue Contributors")
                # Group by Target and Campaign
                summary = master_df.groupby(['Target', 'Campaign Name']).agg({
                    'Direct Sales': 'sum',
                    'Direct RoAS': 'mean',
                    'Total Revenue': 'sum',
                    'Halo ROAS': 'mean'
                }).sort_values(by='Direct Sales', ascending=False)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**✅ Healthy Assets (ROAS >= {target_roas})**")
                    st.dataframe(summary[summary['Direct RoAS'] >= target_roas], use_container_width=True)
                with col2:
                    st.write(f"**⚠️ Below Target (ROAS < {target_roas})**")
                    st.dataframe(summary[(summary['Direct RoAS'] < target_roas) & (summary['Direct RoAS'] > 0)], use_container_width=True)

            with tab_eff:
                st.subheader("Inefficiency & Pause Suggestions")
                pause_logic = master_df[(master_df['Direct Sales'] == 0) & (master_df['Estimated Budget Consumed'] > min_spend_waste)]
                st.warning(f"Pause these: Spent > ₹{min_spend_waste} with 0 Direct Sales")
                st.dataframe(pause_logic[['Target', 'Campaign Name', 'Estimated Budget Consumed', 'CPM']], use_container_width=True)

            with tab_funnel:
                st.subheader("Halo Effect & ATC Funnel")
                st.info("Halo ROAS includes Indirect Sales. ATC Rate helps identify visibility vs intent issues.")
                funnel_df = master_df.groupby(['Target', 'Campaign Name']).agg({
                    'ATC Rate %': 'mean',
                    'Halo ROAS': 'mean',
                    'Most Viewed Position': 'mean'
                }).sort_values(by='Halo ROAS', ascending=False)
                st.dataframe(funnel_df, use_container_width=True)

            with tab_growth:
                st.subheader("New User Acquisition (CAC)")
                growth_summary = master_df.groupby(['Target', 'Campaign Name']).agg({
                    'New Users': 'sum',
                    'CAC': 'mean',
                    'Direct Sales': 'sum'
                }).sort_values(by='New Users', ascending=False)
                st.dataframe(growth_summary, use_container_width=True)

            with tab_bids:
                st.subheader("Actionable Bidding Strategy")
                # CPM Optimization: High Sales, High ROAS, but High CPM
                avg_cpm = master_df['CPM'].mean()
                bid_table = master_df[['Target', 'Campaign Name', 'CPM', 'Direct RoAS', 'Suggested CPM', 'Bid Change %']]
                
                # Flag High CPM Winners
                st.write("**High-CPM Winners (Optimize for Margins)**")
                st.info("High ROAS/Sales but CPM is above average. Try reducing bid to improve profit.")
                winners = bid_table[(bid_table['Direct RoAS'] >= target_roas) & (bid_table['CPM'] > avg_cpm)]
                st.dataframe(winners.sort_values(by='CPM', ascending=False), use_container_width=True)
                
                st.write("**Full Bidding Plan**")
                st.dataframe(bid_table, use_container_width=True)

            # 6. EXPORT
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                master_df.to_excel(writer, index=False, sheet_name='Action_Plan')
            st.download_button("📥 Download Actionable Report", data=output.getvalue(), file_name="blinkit_strategy.xlsx")

if __name__ == "__main__":
    main()
