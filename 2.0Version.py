import streamlit as st
import openpyxl
import pandas as pd

# Excel file URL
GITHUB_EXCEL_LINK = "https://raw.githubusercontent.com/TapatioSpice/PulteContracts/main/PulteContracts1.xlsx"

# Load Excel data
@st.cache_data
def load_data():
    try:
        data = pd.read_excel(GITHUB_EXCEL_LINK)
        return data
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.stop()

# Filter data by all 3 criteria
def filter_data(data, community, series, scar_date):
    return data[
        (data['Community'] == community) &
        (data['Series'] == series) &
        (data['Scar.Date'] == scar_date)
    ]

# Display pivot table with priority rows on top
def show_table(data):
    # Work types to prioritize
    priority_list = ['RG', 'PV', 'FG', 'LS']

    # Round Amount column
    data['Amount'] = data['Amount'].round(2)

    # Create pivot table
    table_data = pd.pivot_table(
        data,
        values='Amount',
        index='Work Type',
        columns='Plan',
        aggfunc='sum',
        fill_value=0
    ).reset_index()

    # Add priority flag
    table_data['priority'] = table_data['Work Type'].apply(
        lambda x: 0 if str(x).strip() in priority_list else 1
    )

    # Sort with priority types first, then alphabetically
    table_data = table_data.sort_values(by=['priority', 'Work Type']).drop(columns='priority')

    # Format numbers
    formatted_table = table_data.applymap(
        lambda x: f"{x:,.2f}" if isinstance(x, (float, int)) else x
    )

    st.table(formatted_table)

# Main app
st.title("Pulte Contracts")

data = load_data()

# Check that necessary column exists
if 'Scar.Date' not in data.columns:
    st.error("Column 'Scar.Date' not found in data.")
    st.stop()

# Convert Scar.Date to datetime
data['Scar.Date'] = pd.to_datetime(data['Scar.Date'])

# Step 1: Select Community
communities = data['Community'].dropna().unique()
selected_community = st.selectbox(
    'Select Community:',
    communities,
    help="You can start typing to narrow down the options."
)

# Step 2: Select Series
if selected_community:
    series_options = data[data['Community'] == selected_community]['Series'].dropna().unique()
    selected_series = st.selectbox('Select Series:', series_options)
else:
    selected_series = None

# Step 3: Select Scar.Date (after both previous selections)
if selected_community and selected_series:
    filtered_for_dates = data[
        (data['Community'] == selected_community) &
        (data['Series'] == selected_series)
    ]
    scar_dates = sorted(filtered_for_dates['Scar.Date'].dropna().unique(), reverse=True)

    if scar_dates:
        selected_scar_date = st.selectbox(
            "Select Scar Start Date:",
            scar_dates,
            index=0,
            format_func=lambda x: x.strftime('%Y-%m-%d')
        )
    else:
        st.warning("No Scar Dates available for the selected Community and Series.")
        selected_scar_date = None
else:
    selected_scar_date = None

# Button to generate table
if st.button('Create Table'):
    if selected_community and selected_series and selected_scar_date:
        try:
            filtered_data = filter_data(data, selected_community, selected_series, selected_scar_date)
            if filtered_data.empty:
                st.warning("No data found for your selection.")
            else:
                show_table(filtered_data)
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
    else:
        st.warning("Please make sure all three selections are made.")

# Footer
st.markdown("""
---
*Created and upkept by Alejandro Escutia | Copyright © 2024*
""")
