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

# Keep the app centered and at a comfortable reading width on large monitors.
st.markdown(
    """
    <style>
        .block-container {
            max-width: 1180px;
            margin: 0 auto;
            padding-top: 2.5rem;
            padding-bottom: 3rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }

        .contracts-hero {
            text-align: center;
            margin-bottom: 1.75rem;
        }

        .contracts-hero h1 {
            margin-bottom: 0.35rem;
        }

        .contracts-hero p {
            color: #9aa0a6;
            margin-top: 0;
        }

        .builder-spacer {
            height: 0.65rem;
        }

        /* Make normal navigation buttons a little taller and easier to scan. */
        div[data-testid="stButton"] > button {
            min-height: 3rem;
            border-radius: 9px;
            font-weight: 600;
        }

        .archive-note {
            text-align: center;
            color: #777f89;
            font-size: 0.78rem;
            margin-top: 0.2rem;
            margin-bottom: 0.5rem;
        }

        /* Keep the footer visually centered with the app. */
        .app-footer {
            text-align: center;
            color: #8b9098;
            font-size: 0.85rem;
            padding-top: 0.5rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
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

BUILDER_ORDER = [
    "Pulte",
    "Woodside",
    "Richmond",
    "Taylor Morrison",
    "Century Communities",
    "KB Homes",
    "Tri Pointe of Nevada",
]

# Completed Pulte communities that should not appear on the main Pulte screen.
# These names match the Community values currently stored in PulteContracts1.xlsx.
ARCHIVED_PULTE_COMMUNITIES = {
    "Aldervista",
    "Ashcroft",
    "Blacktail",
    "Carmel Cliff",
    "Jones.Crossing",
    "Liberty.Silvercourt",
    "Linmar.Ranch",
    "Monument@Reverence",
    "Southbrooks",
    "Talvona",
    "Valridge",
}


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

    # Preserve the important base-work order instead of alphabetizing it.
    priority_order = {
        "Foundation": 0,
        "RG": 1,
        "PV": 2,
        "Pavers": 2,
        "FG": 3,
        "LS": 4,
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


def go_to_page(page_name):
    st.session_state["contracts_page"] = page_name
    st.rerun()


def render_pulte_browser(data, key_prefix):
    """Render the shared Community -> Series -> Scar Date contract browser."""
    if data.empty:
        st.info("No contracts are available in this section.")
        return

    # Step 1: Community
    communities = sort_display_values(data["Community"].dropna().unique())
    selected_community = st.selectbox(
        "1. Select Community",
        communities,
        key=f"{key_prefix}_community",
        help="Start typing to quickly narrow the community list.",
    )

    # Step 2: Series
    series_options = sort_display_values(
        data.loc[data["Community"] == selected_community, "Series"]
        .dropna()
        .unique()
    )
    selected_series = st.selectbox(
        "2. Select Series",
        series_options,
        key=f"{key_prefix}_series",
    )

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
            key=f"{key_prefix}_scar_date",
            help=(
                "The newest contract is selected by default. Choose a historical "
                "date when the lot should use older pricing."
            ),
        )
    else:
        st.warning("No contract dates are available for this Community and Series.")

    if st.button(
        "Create Table",
        type="primary",
        key=f"{key_prefix}_create_table",
    ):
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


# -----------------------------
# Pulte main page
# -----------------------------
def show_pulte_contracts():
    top_left, top_right = st.columns([4, 1])

    with top_left:
        if st.button("← Contracts", key="back_to_contracts"):
            go_to_page("home")

    with top_right:
        if st.button("Refresh Data", key="refresh_pulte", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.markdown(
        """
        <div class="contracts-hero">
            <h1>Pulte Contracts</h1>
            <p>Select the community, series, and Scar / Contract Effective Date.<br>
            Use an older date for lots that belong to an older contract.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    all_data = load_pulte_data()

    # Completed jobs are deliberately removed from the normal Pulte list.
    active_data = all_data[
        ~all_data["Community"].isin(ARCHIVED_PULTE_COMMUNITIES)
    ].copy()

    render_pulte_browser(active_data, "pulte_active")

    latest_file_date = all_data["Scar.Date"].max()
    if pd.notna(latest_file_date):
        st.caption(
            "Latest contract effective date currently in the file: "
            + latest_file_date.strftime("%m/%d/%Y")
        )

    # Low-profile archive access at the bottom of the Pulte screen.
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(
        '<div class="archive-note">Completed communities are kept separately for historical reference.</div>',
        unsafe_allow_html=True,
    )
    archive_cols = st.columns([4, 1.4, 4])
    with archive_cols[1]:
        if st.button(
            "Archived Jobs",
            key="open_pulte_archive",
            use_container_width=True,
        ):
            go_to_page("pulte_archived")


# -----------------------------
# Pulte archived page
# -----------------------------
def show_pulte_archived():
    top_left, top_right = st.columns([4, 1])

    with top_left:
        if st.button("← Pulte Contracts", key="back_to_pulte"):
            go_to_page("pulte")

    with top_right:
        if st.button("Refresh Data", key="refresh_archive", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.markdown(
        """
        <div class="contracts-hero">
            <h1>Pulte Archived Jobs</h1>
            <p>Completed communities and their historical contract pricing.<br>
            These jobs are intentionally hidden from the main Pulte contract list.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    all_data = load_pulte_data()
    archived_data = all_data[
        all_data["Community"].isin(ARCHIVED_PULTE_COMMUNITIES)
    ].copy()

    render_pulte_browser(archived_data, "pulte_archived")

    archived_count = archived_data["Community"].nunique()
    st.caption(f"Archived communities currently available: {archived_count}")


# -----------------------------
# Future-builder placeholder
# -----------------------------
def show_builder_placeholder(builder_name):
    if st.button("← Contracts", key=f"back_{builder_name}"):
        go_to_page("home")

    st.markdown(
        f"""
        <div class="contracts-hero">
            <h1>{builder_name} Contracts</h1>
            <p>This builder is ready in the navigation. Contract pricing can be added here when available.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info(
        f"No {builder_name} contract database has been connected yet. "
        "The button and page are already in place for future expansion."
    )


# -----------------------------
# Contracts landing page
# -----------------------------
def builder_button(builder_name, route_name, button_type="secondary"):
    if st.button(
        builder_name,
        key=f"builder_{route_name}",
        type=button_type,
        use_container_width=True,
    ):
        go_to_page(route_name)


def show_contracts_home():
    st.markdown(
        """
        <div class="contracts-hero">
            <h1>Contracts</h1>
            <p>Select a builder to open its contract pricing.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Row 1
    row1 = st.columns(3, gap="large")
    with row1[0]:
        builder_button("Pulte", "pulte", "primary")
    with row1[1]:
        builder_button("Woodside", "woodside")
    with row1[2]:
        builder_button("Richmond", "richmond")

    st.markdown('<div class="builder-spacer"></div>', unsafe_allow_html=True)

    # Row 2
    row2 = st.columns(3, gap="large")
    with row2[0]:
        builder_button("Taylor Morrison", "taylor_morrison")
    with row2[1]:
        builder_button("Century Communities", "century_communities")
    with row2[2]:
        builder_button("KB Homes", "kb_homes")

    st.markdown('<div class="builder-spacer"></div>', unsafe_allow_html=True)

    # Row 3 — center the final builder button.
    row3 = st.columns([1, 1, 1], gap="large")
    with row3[1]:
        builder_button("Tri Pointe of Nevada", "tri_pointe")

    st.caption(
        "Pulte is active now. The other builder pages are placeholders so the app is ready to expand."
    )


# -----------------------------
# Router
# -----------------------------
if "contracts_page" not in st.session_state:
    st.session_state["contracts_page"] = "home"

page = st.session_state["contracts_page"]

if page == "pulte":
    show_pulte_contracts()
elif page == "pulte_archived":
    show_pulte_archived()
elif page == "home":
    show_contracts_home()
else:
    route_to_builder = {
        "woodside": "Woodside",
        "richmond": "Richmond",
        "taylor_morrison": "Taylor Morrison",
        "century_communities": "Century Communities",
        "kb_homes": "KB Homes",
        "tri_pointe": "Tri Pointe of Nevada",
    }
    show_builder_placeholder(route_to_builder.get(page, "Builder"))

st.markdown("---")
st.markdown(
    '<div class="app-footer">Created and maintained by Alejandro Escutia | © 2024-2026</div>',
    unsafe_allow_html=True,
)
