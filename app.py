st.sidebar.header("Analysis Bifurcation")
view = st.sidebar.selectbox("Choose Perspective", [
    "Performance (Sales/ROAS)", 
    "Efficiency (Wasted Spend)", 
    "Customer Growth (New Users)",
    "Visibility (Position/CPM)"
])

if view == "Performance (Sales/ROAS)":
    st.subheader("High-Performing Assets")
    # Show Top 10 by Direct Sales
    st.dataframe(master_df.nlargest(10, 'Direct Sales'))

elif view == "Efficiency (Wasted Spend)":
    st.subheader("Money Bleeding (High Spend, Low Sales)")
    bleeding = master_df[(master_df['Estimated Budget Consumed'] > 150) & (master_df['Direct Sales'] == 0)]
    st.dataframe(bleeding.sort_values(by='Estimated Budget Consumed', ascending=False))

elif view == "Customer Growth (New Users)":
    st.subheader("New User Acquisition Cost")
    master_df['CAC'] = master_df['Estimated Budget Consumed'] / master_df['New Users'].replace(0, 1)
    st.dataframe(master_df[['Target', 'New Users', 'CAC']].sort_values(by='New Users', ascending=False))

elif view == "Visibility (Position/CPM)":
    st.subheader("Share of Shelf & Auction Health")
    st.write("Correlation between Bid (CPM) and Page Position")
    # Position logic: Lower number is better (Position 1 is top)
    st.dataframe(master_df[['Target', 'CPM', 'Most Viewed Position', 'Impressions']])
