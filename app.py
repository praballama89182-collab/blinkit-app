import streamlit as st
import pandas as pd
import io

# 1. Page & Layout Setup
st.set_page_config(page_title="Blinkit Ads Intelligence", layout="wide")

def main():
    st.title("🚀 Unified Blinkit Ads Decision Dashboard")
    st.markdown("Upload Keyword, Category, Spotlight, or Recommendation reports to begin.")

    # Sidebar Parameters
    st.sidebar.header("Decision Parameters")
    target_roas = st.sidebar.number_input("Target ROAS Threshold", value=1.4, step=0.1)
    min_spend = st.sidebar.number_input("Min Spend to Flag Waste (₹)", value=200)

    uploaded_files = st.file_uploader("Upload Blinkit CSV Reports", type=['csv'], accept_multiple_files=True)

    if uploaded_files:
        all_data = []
        for file in uploaded_files:
            try:
                df = pd.read_csv(file)
                df.columns = df.columns.str.strip() # Remove spaces that cause KeyErrors
                
                # Standardize Target (Keyword / Category / Asset)
                if 'Keyword' in df.columns: df['Target'] = df['Keyword']
                elif 'Category Name' in df.columns: df['Target'] = df['Category Name']
                elif 'Asset' in df.columns: df['Target'] = df['Asset']
                else: df['Target'] = "Unknown"

                # Standardize Budget Column Name
                if 'total_budget' in df.columns: df = df.rename(columns={'total_budget': 'Total Budget'})

                # Ensure Numeric Data
                numeric_cols = ['Direct Sales', 'Estimated Budget Consumed', 'CPM', 'Direct RoAS', 'Total RoAS', 'New Users', 'Impressions']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
                all_data.append(df)
            except Exception as e:
                st.error(f"Error reading {file.name}: {e}")

        if all_data:
            master_df = pd.concat(all_data, ignore_index=True)
            
            # --- CALCULATED FIELDS ---
            # Bid Correction: Suggested CPM = Current CPM * (Current ROAS / Target ROAS)
            master_df['Suggested CPM'] = master_df.apply(
                lambda x: (x['CPM'] * (x['Direct RoAS'] / target_roas)) if (x['Direct RoAS'] > 0 and x['CPM'] > 0) else x['CPM'], 
                axis=1
            )
            
            # CAC Calculation
            master_df['CAC'] = master_df['Estimated Budget Consumed'] / master_df['New Users'].replace(0, 1)

            # --- ANALYSIS BIFURCATIONS ---
            tab1, tab2, tab3, tab4 = st.tabs(["📊 Performance", "🛑 Waste Analysis", "👥 Growth & CAC", "⚖️ Bid Strategy"])

            with tab1:
                st.subheader("Top Performing Assets")
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Spend", f"₹{master_df['Estimated Budget Consumed'].sum():,.0f}")
                m2.metric("Total Sales", f"₹{master_df['Direct Sales'].sum():,.0f}")
                m3.metric("Overall ROAS", f"{(master_df['Direct Sales'].sum() / master_df['Estimated Budget Consumed'].sum()):.2f}x")
                
                st.dataframe(master_df.sort_values(by='Direct Sales', ascending=False), use_container_width=True)

            with tab2:
                st.subheader("Inefficiency & Waste Detection")
                st.info(f"Targets with >₹{min_spend} spend and 0 sales.")
                waste_df = master_df[(master_df['Estimated Budget Consumed'] > min_spend) & (master_df['Direct Sales'] == 0)]
                st.dataframe(waste_df[['Target', 'Campaign Name', 'Estimated Budget Consumed', 'CPM']].sort_values(by='Estimated Budget Consumed', ascending=False))

            with tab3:
                st.subheader("New User Acquisition")
                growth_df = master_df[master_df['New Users'] > 0].sort_values(by='New Users', ascending=False)
                st.dataframe(growth_df[['Target', 'New Users', 'CAC', 'Direct Sales']], use_container_width=True)

            with tab4:
                st.subheader(f"Bidding Logic (Target: {target_roas} ROAS)")
                # Identify Cannibalization
                counts = master_df['Target'].value_counts()
                cannibals = counts[counts > 1].index.tolist()
                master_df['Cannibalization'] = master_df['Target'].apply(lambda x: "⚠️ DUP" if x in cannibals else "")
                
                st.dataframe(master_df[['Target', 'Campaign Name', 'CPM', 'Direct RoAS', 'Suggested CPM', 'Cannibalization']].sort_values(by='Direct RoAS'))

            # Export
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                master_df.to_excel(writer, index=False, sheet_name='Decision_Data')
            st.download_button("📥 Download Action Plan (Excel)", data=output.getvalue(), file_name="blinkit_decisions.xlsx")

if __name__ == "__main__":
    main()
