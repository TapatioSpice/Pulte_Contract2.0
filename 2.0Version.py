import streamlit as st
import openpyxl
import pandas as pd

# Specify the GitHub raw content link to the Excel file
GITHUB_EXCEL_LINK = "https://raw.githubusercontent.com/TapatioSpice/PulteContracts/main/PulteContracts1.xlsx"

def load_data():
    try:
        # Read the Excel file directly from the GitHub raw content link
        data = pd.read_excel(GITHUB_EXCEL_LINK)
        return data
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.stop()

# Function to filter data based on community and series
def filter_data(data, community, series):
    return data[(data['Community'] == community) & (data['Series'] == series)]

# Function to create the table and display it
def show_table(data):
    data = data.sort_values(by='Work Type')

    # Round the values to 2 decimal places
    data['Amount'] = data['Amount'].round(2)

    table_data = pd.pivot_table(data, values='Amount', index='Work Type', columns='Plan', aggfunc='sum', fill_value=0)
    table_data.reset_index(inplace=True)

    # Format values in the DataFrame to display with 2 decimal places
    formatted_table_data = table_data.applymap(lambda x: f"{x:,.2f}" if isinstance(x, (float, int)) else x)

    st.table(formatted_table_data)

# Footer
footer = """
---

*Created and upkept by Alejandro Escutia | Copyright © 2024*
"""

# Title
st.title("Pulte Contracts")

# Display the GUI components
communities = load_data()['Community'].unique()
selected_community = st.selectbox('Select Community:', communities, key="community_select", help="You can start typing to narrow down the options.", index=0)

series_options = load_data()[load_data()['Community'] == selected_community]['Series'].unique()
selected_series = st.selectbox('Select Series:', series_options, key="series_select")

if st.button('Create Table'):
    try:
        if selected_community and selected_series:
            filtered_data = filter_data(load_data(), selected_community, selected_series)
            show_table(filtered_data)

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

# Add the footer
st.markdown(footer)
