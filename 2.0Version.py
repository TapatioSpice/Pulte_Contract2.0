import streamlit as st
import pandas as pd
from pathlib import Path

# -----------------------------
# App configuration
# -----------------------------
st.set_page_config(
    page_title="Contracts",
    page_icon="📄",
    layout="wide",
)

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1120px;
            margin: 0 auto;
            padding-top: 2.5rem;
            padding-bottom: 3rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }

        .contracts-hero {
            text-align: center;
            margin-bottom: 1.8rem;
        }

        .contracts-hero h1 {
            margin-bottom: 0.35rem;
        }

        .contracts-hero p {
            color: #9aa0a6;
            margin-top: 0;
            line-height: 1.5;
        }

        .section-kicker {
            text-align: center;
            color: #8f96a3;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 0.74rem;
            font-weight: 700;
            margin-bottom: 0.4rem;
        }

        .builder-spacer {
            height: 0.7rem;
        }

        div[data-testid="stButton"] > button {
            min-height: 3.15rem;
            border-radius: 10px;
            font-weight: 650;
        }

        .division-note {
            text-align: center;
            color: #8b9098;
            font-size: 0.84rem;
            margin-top: 0.75rem;
        }

        .archive-note {
            text-align: center;
            color: #777f89;
            font-size: 0.78rem;
            margin-top: 0.2rem;
            margin-bottom: 0.5rem;
        }

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

LOCAL_EXCEL_PATH = Path(__file__).resolve().parent / "PulteContracts1.xlsx"
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

BUILDER_SLUGS = {
    "Pulte": "pulte",
    "Woodside": "woodside",
    "Richmond": "richmond",
    "Taylor Morrison": "taylor_morrison",
    "Century Communities": "century_communities",
    "KB Homes": "kb_homes",
    "Tri Pointe of Nevada": "tri_pointe",
}

# Completed PRODUCTION communities. These remain in the workbook for historical
# reference, but do not appear in the normal Pulte Production dropdown.
ARCHIVED_PULTE_PRODUCTION_COMMUNITIES = {
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
    "Paldona@Russell",
    "Paldona@Buffalo",
    "Paldona@WarmSprings",
    "RC.Estates",
}

# Ready for future concrete archives if/when needed.
ARCHIVED_PULTE_CONCRETE_COMMUNITIES = set()

EXPECTED_CONCRETE_COMMUNITIES = {
    "Tenaya Springs @ Landberg - Concrete",
    "Tenaya Springs @ Lone Mesa - Concrete",
    "Tenaya Springs @ Patrick - Concrete",
}


# -----------------------------
# Data helpers
# -----------------------------
@st.cache_data(ttl=300)
def load_pulte_data():
    """Load the Pulte pricing workbook from the app repo, with GitHub as fallback."""
    try:
        if LOCAL_EXCEL_PATH.exists():
            data = pd.read_excel(LOCAL_EXCEL_PATH)
        else:
            data = pd.read_excel(GITHUB_EXCEL_LINK)
    except Exception as exc:
        st.error(f"Unable to load the Pulte contract file: {exc}")
        st.stop()

    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        st.error("The contract file is missing required column(s): " + ", ".join(missing))
        st.stop()

    data = data[REQUIRED_COLUMNS].copy()

    for column in ["Community", "Plan", "Work Type"]:
        data[column] = data[column].astype(str).str.strip()

    data["Scar.Date"] = pd.to_datetime(data["Scar.Date"], errors="coerce")
    data["Amount"] = pd.to_numeric(data["Amount"], errors="coerce")

    data = data.dropna(
        subset=["Community", "Series", "Scar.Date", "Plan", "Work Type", "Amount"]
    )

    return data


def is_concrete_community(series):
    """Identify the concrete side without changing the Excel structure."""
    return series.astype(str).str.strip().str.lower().str.endswith(" - concrete")


def get_pulte_division_data(data, division, archived=False):
    concrete_mask = is_concrete_community(data["Community"])

    if division == "concrete":
        division_data = data[concrete_mask].copy()
        archive_set = ARCHIVED_PULTE_CONCRETE_COMMUNITIES
    else:
        division_data = data[~concrete_mask].copy()
        archive_set = ARCHIVED_PULTE_PRODUCTION_COMMUNITIES

    if archived:
        return division_data[division_data["Community"].isin(archive_set)].copy()

    return division_data[~division_data["Community"].isin(archive_set)].copy()


def filter_data(data, community, series, scar_date):
    selected_date = pd.Timestamp(scar_date).normalize()
    return data[
        (data["Community"] == community)
        & (data["Series"] == series)
        & (data["Scar.Date"].dt.normalize() == selected_date)
    ].copy()


def build_contract_table(data):
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

    formatted = table_data.copy()
    for column in formatted.columns:
        if column != "Work Type":
            formatted[column] = formatted[column].map(lambda value: f"{value:,.2f}")

    return formatted


def sort_display_values(values):
    return sorted(values, key=lambda value: str(value).lower())


def go_to_page(page_name):
    st.session_state["contracts_page"] = page_name
    st.rerun()


def render_pulte_browser(data, key_prefix):
    if data.empty:
        st.info("No contracts are available in this section yet.")
        return

    communities = sort_display_values(data["Community"].dropna().unique())
    selected_community = st.selectbox(
        "1. Select Community",
        communities,
        key=f"{key_prefix}_community",
        help="Start typing to quickly narrow the community list.",
    )

    series_options = sort_display_values(
        data.loc[data["Community"] == selected_community, "Series"].dropna().unique()
    )
    selected_series = st.selectbox(
        "2. Select Series",
        series_options,
        key=f"{key_prefix}_series",
    )

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

    if st.button("Create Table", type="primary", key=f"{key_prefix}_create_table"):
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
        st.subheader(f"{selected_community} — {selected_series} — {selected_date_text}")
        st.dataframe(
            build_contract_table(filtered_data),
            hide_index=True,
            use_container_width=True,
        )


# -----------------------------
# Top-level division home
# -----------------------------
def show_contracts_home():
    st.markdown(
        """
        <div class="contracts-hero">
            <div class="section-kicker">Contract Database</div>
            <h1>Contracts</h1>
            <p>Choose which side of the business you want to open.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    outer = st.columns([1.2, 2, 2, 1.2], gap="large")
    with outer[1]:
        if st.button(
            "Production",
            type="primary",
            key="open_production",
            use_container_width=True,
        ):
            go_to_page("production_builders")

    with outer[2]:
        if st.button(
            "Concrete",
            key="open_concrete",
            use_container_width=True,
        ):
            go_to_page("concrete_builders")



# -----------------------------
# Builder selection pages
# -----------------------------
def builder_button(builder_name, division, button_type="secondary"):
    slug = BUILDER_SLUGS[builder_name]
    route = f"{division}_{slug}"
    if st.button(
        builder_name,
        key=f"builder_{route}",
        type=button_type,
        use_container_width=True,
    ):
        go_to_page(route)


def show_builder_home(division):
    display_division = "Concrete" if division == "concrete" else "Production"

    if st.button("← Contracts", key=f"back_home_{division}"):
        go_to_page("home")

    st.markdown(
        f"""
        <div class="contracts-hero">
            <div class="section-kicker">{display_division}</div>
            <h1>{display_division} Contracts</h1>
            <p>Select a builder to open its {display_division.lower()} contract pricing.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    row1 = st.columns(3, gap="large")
    with row1[0]:
        builder_button("Pulte", division, "primary")
    with row1[1]:
        builder_button("Woodside", division)
    with row1[2]:
        builder_button("Richmond", division)

    st.markdown('<div class="builder-spacer"></div>', unsafe_allow_html=True)

    row2 = st.columns(3, gap="large")
    with row2[0]:
        builder_button("Taylor Morrison", division)
    with row2[1]:
        builder_button("Century Communities", division)
    with row2[2]:
        builder_button("KB Homes", division)

    st.markdown('<div class="builder-spacer"></div>', unsafe_allow_html=True)

    row3 = st.columns([1, 1, 1], gap="large")
    with row3[1]:
        builder_button("Tri Pointe of Nevada", division)



# -----------------------------
# Pulte pages
# -----------------------------
def show_pulte_contracts(division):
    display_division = "Concrete" if division == "concrete" else "Production"

    top_left, top_right = st.columns([4, 1])
    with top_left:
        if st.button(
            f"← {display_division} Builders",
            key=f"back_to_{division}_builders",
        ):
            go_to_page(f"{division}_builders")

    with top_right:
        if st.button(
            "Refresh Data",
            key=f"refresh_pulte_{division}",
            use_container_width=True,
        ):
            st.cache_data.clear()
            st.rerun()

    st.markdown(
        f"""
        <div class="contracts-hero">
            <div class="section-kicker">Pulte • {display_division}</div>
            <h1>Pulte {display_division} Contracts</h1>
            <p>Select the community, series, and Scar / Contract Effective Date.<br>
            Use an older date for lots that belong to an older contract.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    all_data = load_pulte_data()

    if division == "concrete":
        loaded_communities = set(all_data["Community"].dropna().unique())
        missing_concrete = EXPECTED_CONCRETE_COMMUNITIES - loaded_communities
        if missing_concrete:
            st.warning(
                "The Excel file currently loaded by the app is missing: "
                + ", ".join(sorted(missing_concrete))
                + ". Replace the GitHub file named PulteContracts1.xlsx with the updated workbook."
            )

    active_data = get_pulte_division_data(all_data, division, archived=False)
    render_pulte_browser(active_data, f"pulte_{division}_active")

    archive_set = (
        ARCHIVED_PULTE_CONCRETE_COMMUNITIES
        if division == "concrete"
        else ARCHIVED_PULTE_PRODUCTION_COMMUNITIES
    )

    # Keep archive access low-profile at the bottom of each Pulte section.
    if archive_set:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown(
            '<div class="archive-note">Completed communities are kept separately for historical reference.</div>',
            unsafe_allow_html=True,
        )
        archive_cols = st.columns([4, 1.5, 4])
        with archive_cols[1]:
            if st.button(
                "Archived Jobs",
                key=f"open_pulte_{division}_archive",
                use_container_width=True,
            ):
                go_to_page(f"{division}_pulte_archived")


def show_pulte_archived(division):
    display_division = "Concrete" if division == "concrete" else "Production"

    top_left, top_right = st.columns([4, 1])
    with top_left:
        if st.button(
            f"← Pulte {display_division}",
            key=f"back_to_pulte_{division}",
        ):
            go_to_page(f"{division}_pulte")

    with top_right:
        if st.button(
            "Refresh Data",
            key=f"refresh_archive_{division}",
            use_container_width=True,
        ):
            st.cache_data.clear()
            st.rerun()

    st.markdown(
        f"""
        <div class="contracts-hero">
            <div class="section-kicker">Pulte • {display_division}</div>
            <h1>Archived Jobs</h1>
            <p>Completed communities and their historical contract pricing.<br>
            These jobs are intentionally hidden from the active contract list.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    all_data = load_pulte_data()
    archived_data = get_pulte_division_data(all_data, division, archived=True)
    render_pulte_browser(archived_data, f"pulte_{division}_archived")

    if not archived_data.empty:
        st.caption(
            f"Archived communities currently available: {archived_data['Community'].nunique()}"
        )


# -----------------------------
# Future-builder placeholders
# -----------------------------
def show_builder_placeholder(division, builder_name):
    display_division = "Concrete" if division == "concrete" else "Production"

    if st.button(
        f"← {display_division} Builders",
        key=f"back_{division}_{BUILDER_SLUGS[builder_name]}",
    ):
        go_to_page(f"{division}_builders")

    st.markdown(
        f"""
        <div class="contracts-hero">
            <div class="section-kicker">{display_division}</div>
            <h1>{builder_name} Contracts</h1>
            <p>This {display_division.lower()} builder page is ready for its contract database.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info(
        f"No {builder_name} {display_division.lower()} contract database has been connected yet. "
        "The navigation is already in place for future expansion."
    )


# -----------------------------
# Router
# -----------------------------
if "contracts_page" not in st.session_state:
    st.session_state["contracts_page"] = "home"

page = st.session_state["contracts_page"]

if page == "home":
    show_contracts_home()
elif page == "production_builders":
    show_builder_home("production")
elif page == "concrete_builders":
    show_builder_home("concrete")
elif page == "production_pulte":
    show_pulte_contracts("production")
elif page == "concrete_pulte":
    show_pulte_contracts("concrete")
elif page == "production_pulte_archived":
    show_pulte_archived("production")
elif page == "concrete_pulte_archived":
    show_pulte_archived("concrete")
else:
    handled = False
    for division in ("production", "concrete"):
        prefix = f"{division}_"
        if page.startswith(prefix):
            builder_slug = page[len(prefix):]
            for builder_name, slug in BUILDER_SLUGS.items():
                if slug == builder_slug and builder_name != "Pulte":
                    show_builder_placeholder(division, builder_name)
                    handled = True
                    break
        if handled:
            break

    if not handled:
        go_to_page("home")

st.markdown("---")
st.markdown(
    '<div class="app-footer">Created and maintained by Alejandro Escutia | © 2024-2026</div>',
    unsafe_allow_html=True,
)
