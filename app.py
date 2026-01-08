import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Blinkit Unified Ads Dashboard", layout="wide")

def main():
    st.title("🚀 Unified Blinkit Ad Optimizer")
    
    target_roas = st.sidebar.number_input("Target ROAS Threshold", value=1.4, step=0.1)
    uploaded_files = st.file_uploader("Upload Blinkit CSVs", type=['csv'], accept_multiple_files=True)

    if uploaded_files:
        all_data = []
        for file in uploaded_files:
            try:
                df = pd.read_csv(file)
                
                # --- FIX 1: Aggressive Column Standardizing ---
                # Remove spaces and convert everything to a consistent case for matching
                df.columns = df.columns.str.strip()
                
                # Standardize common Blinkit name variations
                rename_map = {
                    'cpm': 'CPM',
                    'total_budget': 'Total Budget',
                    'Direct RoAS': 'Direct ROAS',
                    'Total RoAS': 'Total ROAS'
                }
                df.rename(columns=rename_map, inplace=True)

                # Standardize Target Names
                if 'Keyword' in df.columns: df['Target'] = df['Keyword']
                elif 'Category Name' in df.columns: df['Target'] = df['Category Name']
                elif 'Asset' in df.columns: df['Target'] = df['Asset']
                else: df['Target'] = "Generic Asset"

                # Convert Numeric Fields safely
                numeric_cols = ['Direct Sales', 'Estimated Budget Consumed', 'CPM', 'Direct ROAS', 'Impressions']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
                all_data.append(df)
            except Exception as e:
                st.error(f"Error reading {file.name}: {e}")

        if all_data:
            master_df = pd.concat(all_data, ignore_index=True, sort=False)
            
            # --- FIX 2: Using .get() for Safe Access ---
            # Using row.get('Column') prevents KeyError if the column is missing
            def safe_bid_calc(row):
                current_cpm = row.get('CPM', 0)
                roas = row.get('Direct ROAS', 0)
                
                if roas > 0 and current_cpm > 0:
                    return (current_cpm * (roas / target_roas))
                return current_cpm

            master_df['Suggested CPM'] = master_df.apply(safe_bid_calc, axis=1)

            # --- DISPLAY ---
            st.subheader("Optimization Strategy")
            st.dataframe(master_df[['Target', 'Campaign Name', 'CPM', 'Direct ROAS', 'Suggested CPM']])

if __name__ == "__main__":
    main()
