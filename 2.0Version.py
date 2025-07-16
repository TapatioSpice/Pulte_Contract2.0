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
        (data['Scar Start Date'] == scar_date)
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

# App starts here
st.title("Pulte Contracts")

data = load_data()

# Scar Start Date selection with newest as default
if 'Scar Start Date' not in data.columns:
    st.error("Column 'Scar Start Date' not found in data.")
    st.stop()

data['Scar Start Date'] = pd.to_datetime(data['Scar Start Date'])
scar_dates = sorted(data['Scar Start Date'].unique(), reverse=True)
default_date = scar_dates[0] if scar_dates else None
selected_scar_date = st.selectbox("Select Scar Start Date:", scar_dates, index=0, format_func=lambda x: x.strftime('%Y-%m-%d'))

# Community selection
communities = data[data['Scar Start Date'] == selected_scar_date]['Community'].unique()
selected_community = st.selectbox(
    'Select Community:',
    communities,
    key="community_select",
    help="You can start typing to narrow down the options.",
)

# Series selection based on community + date
series_options = data[
    (data['Scar Start Date'] == selected_scar_date) &
    (data['Community'] == selected_community)
]['Series'].unique()

selected_series = st.selectbox('Select Series:', series_options, key="series_select")

# Generate table
if st.button('Create Table'):
    try:
        if selected_community and selected_series and selected_scar_date:
            filtered_data = filter_data(data, selected_community, selected_series, selected_scar_date)
            show_table(filtered_data)
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

# Footer
st.markdown("""
---
*Created and upkept by Alejandro Escutia | Copyright © 2024*
""")
