import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Blinkit Unified Optimizer", layout="wide")

def main():
    st.title("🚀 Unified Blinkit Ad Optimizer")
    st.markdown("Upload your Blinkit **CSV** or **Excel (.xlsx)** reports to get data-driven bidding suggestions.")
    
    # 1.4 ROAS Requirement
    target_roas = st.sidebar.number_input("Target ROAS Threshold", value=1.4, step=0.1)
    min_spend = st.sidebar.number_input("Min Spend to Flag Waste (₹)", value=200)

    # UPDATED: Now accepts both csv and xlsx
    uploaded_files = st.file_uploader("Upload Blinkit Reports", type=['csv', 'xlsx'], accept_multiple_files=True)

    if uploaded_files:
        all_dfs = []
        
        for file in uploaded_files:
            try:
                # Handle Excel vs CSV
                if file.name.endswith('.xlsx'):
                    # Read all sheets from Excel
                    xl = pd.ExcelFile(file)
                    for sheet_name in xl.sheet_names:
                        df_sheet = pd.read_excel(file, sheet_name=sheet_name)
                        if not df_sheet.empty:
                            all_dfs.append(df_sheet)
                else:
                    # Read CSV
                    df_csv = pd.read_csv(file)
                    all_dfs.append(df_csv)
            except Exception as e:
                st.error(f"Error reading {file.name}: {e}")

        if all_dfs:
            # --- CLEANING & STANDARDIZATION ---
            processed_dfs = []
            for df in all_dfs:
                # Clean header spaces
                df.columns = df.columns.str.strip()
                
                # Standardize Column Names (Maps variations to a single key)
                rename_map = {
                    'cpm': 'CPM',
                    'total_budget': 'Total Budget',
                    'Direct RoAS': 'Direct ROAS',
                    'Total RoAS': 'Total ROAS',
                    'Category Name': 'Target',
                    'Keyword': 'Target',
                    'Asset': 'Target'
                }
                # Apply rename only if the source column exists
                df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)
                
                # Ensure we have a 'Target' column
                if 'Target' not in df.columns:
                    df['Target'] = "Generic Asset"

                # Convert Numeric fields safely
                numeric_cols = ['Direct Sales', 'Estimated Budget Consumed', 'CPM', 'Direct ROAS', 'Impressions', 'New Users']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
                processed_dfs.append(df)

            # Combine everything into one master report
            master_df = pd.concat(processed_dfs, ignore_index=True, sort=False)

            # --- DECISION LOGIC ---
            # Safe calculation using .get() to avoid KeyError
            def calculate_strategy(row):
                curr_cpm = row.get('CPM', 0)
                roas = row.get('Direct ROAS', 0)
                spend = row.get('Estimated Budget Consumed', 0)
                sales = row.get('Direct Sales', 0)

                # Suggested CPM to hit target ROAS
                if roas > 0 and curr_cpm > 0:
                    suggested = curr_cpm * (roas / target_roas)
                else:
                    suggested = curr_cpm

                # Status bifurcation
                if sales == 0 and spend > min_spend:
                    status = "🛑 PAUSE (Waste)"
                elif roas >= target_roas:
                    status = "✅ HEALTHY"
                elif 0 < roas < target_roas:
                    status = "⚠️ REDUCE BID"
                else:
                    status = "🔍 MONITOR"
                
                return pd.Series([suggested, status])

            master_df[['Suggested CPM', 'Strategy']] = master_df.apply(calculate_strategy, axis=1)

            # --- DASHBOARD TABS ---
            tab1, tab2, tab3 = st.tabs(["📊 Performance Summary", "💡 Bidding Plan", "👥 Growth (New Users)"])

            with tab1:
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Spend", f"₹{master_df['Estimated Budget Consumed'].sum():,.0f}")
                col2.metric("Total Sales", f"₹{master_df['Direct Sales'].sum():,.0f}")
                col3.metric("Avg ROAS", f"{(master_df['Direct Sales'].sum()/master_df['Estimated Budget Consumed'].sum()):.2f}x")
                st.dataframe(master_df, use_container_width=True)

            with tab2:
                st.subheader(f"Bid Adjustments for {target_roas} ROAS Target")
                # Filter to show only items that actually have spend
                plan_df = master_df[master_df['Estimated Budget Consumed'] > 0]
                st.dataframe(plan_df[['Target', 'Campaign Name', 'CPM', 'Direct ROAS', 'Suggested CPM', 'Strategy']])

            with tab3:
                st.subheader("New User Acquisition Cost")
                master_df['CAC'] = master_df['Estimated Budget Consumed'] / master_df['New Users'].replace(0, 1)
                st.dataframe(master_df[master_df['New Users'] > 0][['Target', 'New Users', 'CAC']].sort_values(by='New Users', ascending=False))

            # EXPORT
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                master_df.to_excel(writer, index=False, sheet_name='Optimization_Plan')
            st.download_button("📥 Download Action Plan", data=output.getvalue(), file_name="blinkit_decision_sheet.xlsx")

if __name__ == "__main__":
    main()
