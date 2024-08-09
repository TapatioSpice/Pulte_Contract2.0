import streamlit as st
import openpyxl
import pandas as pd

# Specify the GitHub raw content link to the Excel file
GITHUB_EXCEL_LINK = "https://raw.githubusercontent.com/TapatioSpice/PulteContracts/main/PulteContracts1.xlsx"

# Predefined password
PASSWORD = "landscape12"

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

# Password protection at the bottom
password_input = st.text_input("Enter password:", type="password")
entered_password = password_input.lower()  # Convert to lowercase for case-insensitive comparison

# Title
st.title("Pulte Contracts")

if entered_password == PASSWORD:
    # Display the GUI components only if the password is correct
    communities = load_data()['Community'].unique()

    # Custom text input with filtering
    typed_community = st.text_input('Type Community:', '')

    filtered_communities = [community for community in communities if typed_community.lower() in community.lower()]

    if len(filtered_communities) == 1:
        selected_community = filtered_communities[0]
    else:
        selected_community = st.selectbox('Select Community:', filtered_communities, key="community_select")

    if selected_community:
        series_options = load_data()[load_data()['Community'] == selected_community]['Series'].unique()

        # Custom text input with filtering
        typed_series = st.text_input('Type Series:', '')

        filtered_series = [series for series in series_options if typed_series.lower() in series.lower()]

        if len(filtered_series) == 1:
            selected_series = filtered_series[0]
        else:
            selected_series = st.selectbox('Select Series:', filtered_series, key="series_select")

        if selected_series and st.button('Create Table'):
            try:
                filtered_data = filter_data(load_data(), selected_community, selected_series)
                show_table(filtered_data)
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
else:
    # Display a warning if the password is incorrect
    st.warning("Incorrect password. Please enter the correct password to proceed.")

# Add the footer
st.markdown(footer)
