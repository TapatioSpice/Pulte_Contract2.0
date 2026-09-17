import streamlit as st
import pandas as pd

# -----------------------------
# App configuration
# -----------------------------
st.set_page_config(
    page_title="Contracts",
    page_icon="📄",
    layout="wide",
)

GITHUB_EXCEL_LINK = (
    "https://raw.githubusercontent.com/TapatioSpice/"
    "PulteContracts/main/PulteContracts1.xlsx"
)

REQUIRED_COLUMNS = [
    "Community",
    "Series",
    "Scar.Date",
    "Plan",
    "Work Type",
    "Amount",
]


# -----------------------------
# Data helpers
# -----------------------------
@st.cache_data(ttl=300)
def load_pulte_data():
    """Load the Pulte pricing workbook from GitHub."""
    try:
        data = pd.read_excel(GITHUB_EXCEL_LINK)
    except Exception as exc:
        st.error(f"Unable to load the Pulte contract file: {exc}")
        st.stop()

    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        st.error(
            "The contract file is missing required column(s): "
            + ", ".join(missing)
        )
        st.stop()

    data = data[REQUIRED_COLUMNS].copy()
    data["Scar.Date"] = pd.to_datetime(data["Scar.Date"], errors="coerce")
    data["Amount"] = pd.to_numeric(data["Amount"], errors="coerce")

    # Remove rows that cannot be used by the app.
    data = data.dropna(
        subset=["Community", "Series", "Scar.Date", "Plan", "Work Type", "Amount"]
    )

    return data


def filter_data(data, community, series, scar_date):
    selected_date = pd.Timestamp(scar_date).normalize()
    return data[
        (data["Community"] == community)
        & (data["Series"] == series)
        & (data["Scar.Date"].dt.normalize() == selected_date)
    ].copy()


def build_contract_table(data):
    """Create the plan-by-work-type pricing table."""
    working = data.copy()
    working["Amount"] = working["Amount"].round(2)

    table_data = pd.pivot_table(
        working,
        values="Amount",
        index="Work Type",
        columns="Plan",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()

    # Preserve the original important-row order instead of alphabetizing it.
    priority_order = {
        "RG": 0,
        "PV": 1,
        "Pavers": 1,
        "FG": 2,
        "LS": 3,
    }
    table_data["_priority"] = table_data["Work Type"].map(priority_order).fillna(100)
    table_data = table_data.sort_values(
        by=["_priority", "Work Type"], kind="stable"
    ).drop(columns="_priority")

    # Format only the price columns. Keep Work Type as text.
    formatted = table_data.copy()
    for column in formatted.columns:
        if column != "Work Type":
            formatted[column] = formatted[column].map(lambda value: f"{value:,.2f}")

    return formatted


def sort_display_values(values):
    """Sort mixed text/number values safely for dropdowns."""
    return sorted(values, key=lambda value: str(value).lower())


# -----------------------------
# Pulte page
# -----------------------------
def show_pulte_contracts():
    top_left, top_right = st.columns([4, 1])

    with top_left:
        if st.button("← Contracts", key="back_to_contracts"):
            st.session_state["contracts_page"] = "home"
            st.rerun()

    with top_right:
        if st.button("Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.title("Pulte Contracts")
    st.caption(
        "Select the community, series, and the Scar / Contract Effective Date. "
        "Use an older date for lots that belong to an older contract."
    )

    data = load_pulte_data()

    # Step 1: Community
    communities = sort_display_values(data["Community"].dropna().unique())
    selected_community = st.selectbox(
        "1. Select Community",
        communities,
        help="Start typing to quickly narrow the community list.",
    )

    # Step 2: Series
    series_options = sort_display_values(
        data.loc[data["Community"] == selected_community, "Series"]
        .dropna()
        .unique()
    )
    selected_series = st.selectbox("2. Select Series", series_options)

    # Step 3: Scar / Effective Date
    filtered_for_dates = data[
        (data["Community"] == selected_community)
        & (data["Series"] == selected_series)
    ]

    scar_dates = sorted(
        filtered_for_dates["Scar.Date"].dropna().dt.normalize().unique(),
        reverse=True,
    )

    selected_scar_date = None
    if scar_dates:
        newest_date = pd.Timestamp(scar_dates[0]).normalize()

        def date_label(value):
            current = pd.Timestamp(value).normalize()
            label = current.strftime("%m/%d/%Y")
            if current == newest_date:
                return f"{label} — Current / Newest"
            return f"{label} — Historical"

        selected_scar_date = st.selectbox(
            "3. Select Scar / Contract Effective Date",
            scar_dates,
            index=0,
            format_func=date_label,
            help=(
                "The newest contract is selected by default. Choose a historical "
                "date when the lot should use older pricing."
            ),
        )
    else:
        st.warning("No contract dates are available for this Community and Series.")

    if st.button("Create Table", type="primary"):
        if selected_scar_date is None:
            st.warning("Please select a contract date.")
            return

        filtered_data = filter_data(
            data,
            selected_community,
            selected_series,
            selected_scar_date,
        )

        if filtered_data.empty:
            st.warning("No pricing was found for the selected contract.")
            return

        selected_date_text = pd.Timestamp(selected_scar_date).strftime("%m/%d/%Y")
        st.subheader(
            f"{selected_community} — {selected_series} — {selected_date_text}"
        )
        st.dataframe(
            build_contract_table(filtered_data),
            hide_index=True,
            use_container_width=True,
        )

    latest_file_date = data["Scar.Date"].max()
    if pd.notna(latest_file_date):
        st.caption(
            "Latest contract effective date currently in the file: "
            + latest_file_date.strftime("%m/%d/%Y")
        )


# -----------------------------
# Contracts landing page
# -----------------------------
def show_contracts_home():
    st.title("Contracts")
    st.write("Select a builder to open its contract pricing.")

    left, middle, right = st.columns(3)
    with left:
        st.subheader("Pulte")
        st.caption("Community, series, Scar Date, plans, and option pricing")
        if st.button("Open Pulte Contracts", type="primary", use_container_width=True):
            st.session_state["contracts_page"] = "pulte"
            st.rerun()

    # These blank columns intentionally leave space for future builders.
    with middle:
        st.empty()
    with right:
        st.empty()


# -----------------------------
# Router
# -----------------------------
if "contracts_page" not in st.session_state:
    st.session_state["contracts_page"] = "home"

if st.session_state["contracts_page"] == "pulte":
    show_pulte_contracts()
else:
    show_contracts_home()

st.markdown("---")
st.caption("Created and maintained by Alejandro Escutia | © 2024-2026")
