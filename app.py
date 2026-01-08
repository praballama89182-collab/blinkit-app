import streamlit as st
import pandas as pd
import io
from thefuzz import process  # For fuzzy matching

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

            # --- FUZZY CAMPAIGN SEARCH & FILTER ---
            st.sidebar.markdown("---")
            st.sidebar.header("🔍 Search Campaign")
            
            # Get unique campaigns
            all_campaigns = sorted(master_df['Campaign Name'].dropna().unique().tolist())
            
            # Text input for fuzzy search
            search_query = st.sidebar.text_input("Type to find similar campaigns", "")
            
            if search_query:
                # Find top 5 similar campaign names
                matches = process.extract(search_query, all_campaigns, limit=10)
                # Filter matches that have a decent similarity score (e.g., > 50)
                filtered_options = [match[0] for match in matches if match[1] > 50]
                campaign_options = ["All Campaigns"] + filtered_options
                if len(filtered_options) == 0:
                    st.sidebar.warning("No similar campaigns found.")
            else:
                campaign_options = ["All Campaigns"] + all_campaigns

            selected_campaign = st.sidebar.selectbox("Select from matches", campaign_options)

            # Apply Filter
            if selected_campaign != "All Campaigns":
                filtered_df = master_df[master_df['Campaign Name'] == selected_campaign]
            else:
                filtered_df = master_df

            # --- PERFORMANCE SUMMARY ---
            st.header(f"📊 Summary for: {selected_campaign}")
            
            # Top Contributors (Revenue)
            st.subheader("🏆 Top Revenue Contributors")
            top_rev = filtered_df.groupby(['Target', 'Campaign Name']).agg({
                'Direct Sales': 'sum',
                'Direct RoAS': 'mean'
            }).sort_values(by='Direct Sales', ascending=False).head(10)
            st.dataframe(top_rev, use_container_width=True)

            # Above vs Below Threshold
            col_left, col_right = st.columns(2)
            with col_left:
                st.subheader(f"✅ Healthy (ROAS >= {target_roas})")
                above = filtered_df[filtered_df['Direct RoAS'] >= target_roas]
                st.dataframe(above[['Target', 'Campaign Name', 'Direct RoAS']], use_container_width=True)
            with col_right:
                st.subheader(f"⚠️ Inefficient (ROAS < {target_roas})")
                below = filtered_df[(filtered_df['Direct RoAS'] < target_roas) & (filtered_df['Direct RoAS'] > 0)]
                st.dataframe(below[['Target', 'Campaign Name', 'Direct RoAS']], use_container_width=True)

            # Strategic Suggestions
            st.header("💡 Strategic Recommendations")
            pause_df = filtered_df[(filtered_df['Direct Sales'] == 0) & (filtered_df['Estimated Budget Consumed'] > min_spend)]
            avg_cpm = filtered_df['CPM'].mean()
            cpm_optimize = filtered_df[(filtered_df['Direct RoAS'] >= target_roas) & (filtered_df['CPM'] > avg_cpm)]

            tab_pause, tab_cpm = st.tabs(["🛑 Suggestions to Pause", "📉 CPM Optimization"])
            with tab_pause:
                st.warning("High spend, zero revenue. Recommendation: Pause.")
                st.dataframe(pause_df[['Target', 'Campaign Name', 'Estimated Budget Consumed', 'CPM']], use_container_width=True)
            with tab_cpm:
                st.info("High ROAS, High CPM. Recommendation: Decrease bid to improve margin.")
                st.dataframe(cpm_optimize[['Target', 'Campaign Name', 'CPM', 'Direct RoAS']], use_container_width=True)

            # Export
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                filtered_df.to_excel(writer, index=False)
            st.download_button("📥 Download Analysis", data=buffer.getvalue(), file_name=f"blinkit_analysis.xlsx")

if __name__ == "__main__":
    main()
