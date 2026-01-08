import streamlit as st
import pandas as pd
import io

# 1. SETTINGS
st.set_page_config(page_title="Blinkit Ad Optimizer", layout="wide")

# 2. APP LOGIC
def main():
    st.title("🚀 Blinkit Search Term Optimizer")
    
    # Target ROAS threshold as requested
    target_roas = st.sidebar.number_input("Target ROAS Threshold", value=1.4, step=0.1)
    
    uploaded_file = st.file_uploader("Upload Blinkit Keyword CSV", type=['csv'])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            df.columns = [c.strip() for c in df.columns]
            
            # KPI Calculations
            df['Direct Sales'] = pd.to_numeric(df['Direct Sales'], errors='coerce').fillna(0)
            df['Estimated Budget Consumed'] = pd.to_numeric(df['Estimated Budget Consumed'], errors='coerce').fillna(0)
            df['CPM'] = pd.to_numeric(df['CPM'], errors='coerce').fillna(0)
            df['Direct RoAS'] = pd.to_numeric(df['Direct RoAS'], errors='coerce').fillna(0)

            # Bid Suggestion Logic
            # Formula: Suggested Bid = Current CPM * (Current ROAS / Target ROAS)
            df['Suggested CPM'] = df.apply(
                lambda x: x['CPM'] * (x['Direct RoAS'] / target_roas) if x['Direct RoAS'] > 0 else 0, 
                axis=1
            )
            
            st.success("Data Loaded Successfully!")
            st.dataframe(df[['Keyword', 'Campaign Name', 'CPM', 'Direct RoAS', 'Suggested CPM']].head(20))
            
            # Export
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Optimization')
            st.download_button("Download Optimization Report", data=output.getvalue(), file_name="blinkit_plan.xlsx")
            
        except Exception as e:
            st.error(f"Error processing file: {e}")

if __name__ == "__main__":
    main()
