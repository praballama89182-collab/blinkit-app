# --- Advanced Logic ---
# 1. Funnel Metrics
master_df['ATC_Rate'] = (master_df['Direct ATC'] / master_df['Impressions']) * 100
master_df['Conversion_Rate'] = (master_df['Direct Quantities Sold'] / master_df['Direct ATC'].replace(0, 1)) * 100

# 2. Halo Effect
master_df['Total_Revenue'] = master_df['Direct Sales'] + master_df['Indirect Sales']
master_df['Brand_Halo_ROAS'] = master_df['Total_Revenue'] / master_df['Estimated Budget Consumed']

# 3. Acquisition CAC
master_df['CAC'] = master_df['Estimated Budget Consumed'] / master_df['New Users'].replace(0, 1)

# Display in Streamlit
st.header("🔬 Deep-Dive Bifurcations")
deep_view = st.selectbox("Select Deep-Dive", ["Funnel Efficiency", "Brand Halo Effect", "Acquisition CAC"])

if deep_view == "Funnel Efficiency":
    st.write("Keywords with high Add-to-Cart but low Sales (Potential Pricing Issue):")
    st.dataframe(master_df[(master_df['ATC_Rate'] > 2) & (master_df['Conversion_Rate'] < 10)])

elif deep_view == "Brand Halo Effect":
    st.write("Keywords driving Total Brand Volume (Direct + Indirect):")
    st.dataframe(master_df.sort_values(by='Brand_Halo_ROAS', ascending=False))
