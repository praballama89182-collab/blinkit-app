import streamlit as st
import pandas as pd
import io

# Page Setup
st.set_page_config(page_title="Blinkit Performance Analytics", layout="wide")

def main():
    st.title("📈 Blinkit Performance & Optimization Summary")
    
    # 1. Sidebar Filters
    st.sidebar.header("Filter Configuration")
    target_roas = st.sidebar.slider("ROAS Threshold Filter", 0.1, 10.0, 1.4)
    min_spend = st.sidebar.number_input("Min Spend to Suggest Pause (₹)", value=200)

    uploaded_files = st.file_uploader("Upload Blinkit CSV/Excel Files", type=['csv', 'xlsx'], accept_multiple_files=True)

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
            # Standardization & Cleaning
            master_df = pd.concat(all_dfs, ignore_index=True, sort=False)
            master_df.columns = master_df.columns.str.strip()
            
            # Map Identifiers
            if 'Keyword' in master_df.columns: master_df['Target'] = master_df['Keyword']
            elif 'Category Name' in master_df.columns: master_df['Target'] = master_df['Category Name']
            elif 'Asset' in master_df.columns: master_df['Target'] = master_df['Asset']
            else: master_df['Target'] = "Unknown"

            # Numeric Conversions
            cols = ['Direct Sales', 'Estimated Budget Consumed', 'CPM', 'Direct RoAS']
            for col in cols:
                if col in master_df.columns:
                    master_df[col] = pd.to_numeric(master_df[col], errors='coerce').fillna(0)

            # --- PERFORMANCE SUMMARY BIFURCATIONS ---

            # A. Top Contributors (Revenue)
            st.header("🏆 Top Revenue Contributors")
            top_rev = master_df.groupby(['Target', 'Campaign Name']).agg({
                'Direct Sales': 'sum',
                'Direct RoAS': 'mean'
            }).sort_values(by='Direct Sales', ascending=False).head(10)
            st.dataframe(top_rev, use_container_width=True)

            # B. Above vs Below Threshold
            col_left, col_right = st.columns(2)
            
            with col_left:
                st.subheader(f"✅ Above Threshold (ROAS >= {target_roas})")
                above = master_df[master_df['Direct RoAS'] >= target_roas]
                st.dataframe(above[['Target', 'Campaign Name', 'Direct RoAS']], use_container_width=True)

            with col_right:
                st.subheader(f"⚠️ Below Threshold (ROAS < {target_roas})")
                below = master_df[(master_df['Direct RoAS'] < target_roas) & (master_df['Direct RoAS'] > 0)]
                st.dataframe(below[['Target', 'Campaign Name', 'Direct RoAS']], use_container_width=True)

            # C. Strategic Suggestions (Pause & CPM Management)
            st.header("💡 Strategic Recommendations")
            
            # Logic for Pause
            pause_df = master_df[(master_df['Direct Sales'] == 0) & (master_df['Estimated Budget Consumed'] > min_spend)]
            
            # Logic for CPM Decrease (Sales are good, ROAS is good, but CPM is very high)
            # We define 'High CPM' as top 25% of the current campaign CPMs
            avg_cpm = master_df['CPM'].mean()
            cpm_optimize = master_df[(master_df['Direct RoAS'] >= target_roas) & (master_df['CPM'] > avg_cpm)]

            tab_pause, tab_cpm = st.tabs(["🛑 Suggestions to Pause", "📉 CPM Optimization"])

            with tab_pause:
                st.warning("These items have high spend but zero revenue. Recommended to Pause.")
                st.dataframe(pause_df[['Target', 'Campaign Name', 'Estimated Budget Consumed', 'CPM']], use_container_width=True)

            with tab_cpm:
                st.info("High ROAS but High CPM: You have good sales but can improve margins by gradually decreasing bids.")
                st.dataframe(cpm_optimize[['Target', 'Campaign Name', 'CPM', 'Direct RoAS']], use_container_width=True)

            # Export
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                master_df.to_excel(writer, index=False)
            st.download_button("📥 Download Full Analysis", data=buffer.getvalue(), file_name="blinkit_performance_report.xlsx")

if __name__ == "__main__":
    main()
