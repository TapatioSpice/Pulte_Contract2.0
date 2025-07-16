import streamlit as st
import openpyxl
import pandas as pd

# Excel file from GitHub
GITHUB_EXCEL_LINK = "https://raw.githubusercontent.com/TapatioSpice/PulteContracts/main/PulteContracts1.xlsx"

# Load data
@st.cache_data
def load_data():
    try:
        data = pd.read_excel(GITHUB_EXCEL_LINK)
        return data
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.stop()

# Filter data
def filter_data(data, community, series, scar_date):
    return data[
        (data['Community'] == community) &
        (data['Series'] == series) &
        (data['Scar.Date'] == scar_date)
    ]

# Show pivot table
def show_table(data):
    data = data.sort_values(by='Work Type')
    data['Amount'] = data['Amount'].round(2)
    table_data = pd.pivot_table(
        data,
        values='Amount',
        index='Work Type',
        columns='Plan',
        aggfunc='sum',
        fill_value=0
    )
    table_data.reset_index(inplace=True)
    formatted_table_data = table_data.applymap(
        lambda x: f"{x:,.2f}" if isinstance(x, (float, int)) else x
    )
    st.table(formatted_table_data)

# Start the app
st.title("Pulte Contracts")

data = load_data()

# Parse dates if needed
if 'Scar.Date' not in data.columns:
    st.error("Column 'Scar.Date' not found in data.")
    st.stop()
data['Scar.Date'] = pd.to_datetime(data['Scar.Date'])

# --- Step 1: Community dropdown ---
communities = data['Community'].dropna().unique()
selected_community = st.selectbox(
    'Select Community:',
    communities,
    key="community_select",
    help="You can start typing to narrow down the options."
)

# --- Step 2: Series dropdown (only if community is selected) ---
if selected_community:
    series_options = data[data['Community'] == selected_community]['Series'].dropna().unique()
    selected_series = st.selectbox('Select Series:', series_options, key="series_select")
else:
    selected_series = None

# --- Step 3: Scar.Date dropdown (only if community and series are selected) ---
if selected_community and selected_series:
    date_filtered = data[
        (data['Community'] == selected_community) &
        (data['Series'] == selected_series)
    ]
    scar_dates = sorted(date_filtered['Scar.Date'].dropna().unique(), reverse=True)

    if scar_dates:
        selected_scar_date = st.selectbox(
            "Select Scar Start Date:",
            scar_dates,
            index=0,
            format_func=lambda x: x.strftime('%Y-%m-%d')
        )
    else:
        st.warning("No Scar Dates found for this community and series.")
        selected_scar_date = None
else:
    selected_scar_date = None

# --- Create Table Button ---
if st.button('Create Table'):
    if selected_community and selected_series and selected_scar_date:
        try:
            filtered_data = filter_data(data, selected_community, selected_series, selected_scar_date)
            if filtered_data.empty:
                st.warning("No data available for selected filters.")
            else:
                show_table(filtered_data)
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
    else:
        st.warning("Please select Community, Series, and Scar Start Date first.")

# Footer
st.markdown("""
---
*Created and upkept by Alejandro Escutia | Copyright © 2024*
""")
