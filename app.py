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
                df.columns = df.columns.str.strip() # Remove invisible spaces

                # 1. Standardize Target Names
                if 'Keyword' in df.columns: df['Target'] = df['Keyword']
                elif 'Category Name' in df.columns: df['Target'] = df['Category Name']
                elif 'Asset' in df.columns: df['Target'] = df['Asset']
                else: df['Target'] = "Generic Asset"

                # 2. Convert Numeric Fields (Only if they exist in the file)
                numeric_cols = ['Direct Sales', 'Estimated Budget Consumed', 'CPM', 'Direct RoAS', 'Impressions']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
                all_data.append(df)
            except Exception as e:
                st.error(f"Error reading {file.name}: {e}")

        if all_data:
            # Combine all reports (Spotlight, Keyword, Category, etc.)
            master_df = pd.concat(all_data, ignore_index=True, sort=False)
            
            # --- SAFE CALCULATION LOGIC ---
            # We check if 'Direct RoAS' exists for that specific row before calculating
            def safe_bid_calc(row):
                # Check if the row actually has ROAS data (Spotlight files won't)
                if 'Direct RoAS' in row and row['Direct RoAS'] > 0:
                    return (row['CPM'] * (row['Direct RoAS'] / target_roas))
                return row['CPM'] # Default to current CPM if no ROAS data

            master_df['Suggested CPM'] = master_df.apply(safe_bid_calc, axis=1)

            # --- VISUALIZATION BIFURCATIONS ---
            tab1, tab2 = st.tabs(["📊 Performance Summary", "💡 Bidding Logic"])

            with tab1:
                st.subheader("High Level Metrics")
                # We use .get() to avoid errors if a column is missing across ALL files
                total_spend = master_df.get('Estimated Budget Consumed', pd.Series([0])).sum()
                total_sales = master_df.get('Direct Sales', pd.Series([0])).sum()
                
                c1, c2 = st.columns(2)
                c1.metric("Total Spend", f"₹{total_spend:,.2f}")
                c2.metric("Total Direct Sales", f"₹{total_sales:,.2f}")
                st.dataframe(master_df, use_container_width=True)

            with tab2:
                st.subheader("Bid Recommendations")
                # Filter out rows that don't have Sales/ROAS data (like Spotlight)
                performance_df = master_df[master_df['Direct RoAS'] > 0]
                st.dataframe(performance_df[['Target', 'Campaign Name', 'CPM', 'Direct RoAS', 'Suggested CPM']])

if __name__ == "__main__":
    main()
