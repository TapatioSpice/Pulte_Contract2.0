import streamlit as st
import pandas as pd
from pathlib import Path
from io import BytesIO
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

st.set_page_config(page_title="Contracts", page_icon="📄", layout="wide")

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
        .contracts-hero { text-align: center; margin-bottom: 1.8rem; }
        .contracts-hero h1 { margin-bottom: 0.35rem; }
        .contracts-hero p { color: #9aa0a6; margin-top: 0; line-height: 1.5; }
        .section-kicker {
            text-align: center; color: #8f96a3; text-transform: uppercase;
            letter-spacing: 0.12em; font-size: 0.74rem; font-weight: 700;
            margin-bottom: 0.4rem;
        }
        .builder-spacer { height: 0.7rem; }
        div[data-testid="stButton"] > button {
            min-height: 3.15rem; border-radius: 10px; font-weight: 650;
        }
        .archive-note {
            text-align: center; color: #777f89; font-size: 0.78rem;
            margin-top: 0.2rem; margin-bottom: 0.5rem;
        }
        .app-footer {
            text-align: center; color: #8b9098; font-size: 0.85rem;
            padding-top: 0.5rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

BASE_DIR = Path(__file__).resolve().parent
REQUIRED_COLUMNS = ["Community", "Series", "Scar.Date", "Plan", "Work Type", "Amount"]

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

BUILDER_FILES = {
    "Pulte": "PulteContracts1.xlsx",
    "Woodside": "WoodsideContracts1.xlsx",
    "Richmond": "RichmondContracts1.xlsx",
    "KB Homes": "KBHomesContracts1.xlsx",
}

ACTIVE_BUILDERS = set(BUILDER_FILES)

ARCHIVED_COMMUNITIES = {
    ("Pulte", "production"): {
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
    },
    ("Pulte", "concrete"): set(),
    ("Woodside", "production"): set(),
    ("Woodside", "concrete"): set(),
}

EXPECTED_PULTE_CONCRETE = {
    "Tenaya Springs @ Landberg - Concrete",
    "Tenaya Springs @ Lone Mesa - Concrete",
    "Tenaya Springs @ Patrick - Concrete",
}


GITHUB_OWNER = "TapatioSpice"
CONTRACT_REPO = "Contract-Files"
CONTRACT_BRANCHES = ("main", "master")


def contract_file_candidates(filename):
    """Local fallbacks for desktop/local testing.

    Streamlit Community Cloud clones only the Alpha-Contracts repository, so a
    separate Contract-Files repository is NOT available as a sibling folder.
    These paths are therefore only fallbacks for local testing.
    """
    return [
        BASE_DIR / filename,
        BASE_DIR / "Contract-Files" / filename,
        BASE_DIR.parent / "Contract-Files" / filename,
    ]


def github_token():
    """Optional token for a private Contract-Files repository."""
    try:
        return st.secrets.get("GITHUB_TOKEN")
    except Exception:
        return None


def download_contract_file(filename):
    """Download one workbook from the separate Contract-Files GitHub repo.

    Public repos work without a token. If Contract-Files is private, add a
    GITHUB_TOKEN secret in Streamlit with read access to that repository.
    """
    token = github_token()
    errors = []

    for branch in CONTRACT_BRANCHES:
        url = (
            f"https://raw.githubusercontent.com/{GITHUB_OWNER}/"
            f"{CONTRACT_REPO}/{branch}/{filename}"
        )
        headers = {"User-Agent": "Alpha-Contracts-Streamlit"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=20) as response:
                return BytesIO(response.read()), url
        except HTTPError as exc:
            errors.append(f"{branch}: HTTP {exc.code}")
        except URLError as exc:
            errors.append(f"{branch}: {exc.reason}")
        except Exception as exc:
            errors.append(f"{branch}: {exc}")

    raise FileNotFoundError(
        f"Could not download {filename} from {GITHUB_OWNER}/{CONTRACT_REPO}. "
        + " | ".join(errors)
    )


@st.cache_data(ttl=300)
def load_builder_data(builder_name):
    filename = BUILDER_FILES[builder_name]

    # Local file first (useful when testing on your computer).
    local_path = next((path for path in contract_file_candidates(filename) if path.exists()), None)

    try:
        if local_path is not None:
            data = pd.read_excel(local_path)
        else:
            remote_file, remote_url = download_contract_file(filename)
            data = pd.read_excel(remote_file)
    except Exception as exc:
        st.error(
            f"Unable to load {filename} from the Contract-Files GitHub repository. "
            f"Make sure the file is in the root of TapatioSpice/Contract-Files and is named exactly {filename}."
        )
        st.caption(
            "If Contract-Files is private, add GITHUB_TOKEN in Streamlit → App settings → Secrets "
            "with read access to that repository."
        )
        st.code(str(exc))
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


def concrete_mask(data):
    return data["Community"].astype(str).str.strip().str.lower().str.endswith(" - concrete")


def get_division_data(data, builder_name, division, archived=False):
    mask = concrete_mask(data)
    division_data = data[mask].copy() if division == "concrete" else data[~mask].copy()
    archive_set = ARCHIVED_COMMUNITIES.get((builder_name, division), set())

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


def work_type_priority(value):
    value = str(value)
    if value == "Foundation": return 0
    if value.startswith("Foundation-"): return 1
    if value.startswith("FND-"): return 2
    if value == "Haul Off": return 10
    if value == "RG": return 20
    if value.startswith("RG-"): return 21
    if value == "RG2": return 22
    if value == "FG2": return 30
    if value == "FG": return 31
    if value == "LS": return 40
    if value == "Landscape": return 40
    if value.startswith("LSO-"): return 41
    if value == "Pavers": return 50
    if value.startswith("Pavers-"): return 51
    if value.startswith("PVO-"): return 52
    return 100


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

    table_data["_priority"] = table_data["Work Type"].map(work_type_priority)
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


def render_contract_browser(data, key_prefix):
    if data.empty:
        st.info("No contracts loaded.")
        return

    communities = sort_display_values(data["Community"].dropna().unique())
    selected_community = st.selectbox(
        "1. Select Community",
        communities,
        key=f"{key_prefix}_community",
    )

    series_options = sort_display_values(
        data.loc[data["Community"] == selected_community, "Series"].dropna().unique()
    )
    selected_series = st.selectbox(
        "2. Select Series",
        series_options,
        key=f"{key_prefix}_series",
    )

    date_data = data[
        (data["Community"] == selected_community)
        & (data["Series"] == selected_series)
    ]
    scar_dates = sorted(
        date_data["Scar.Date"].dropna().dt.normalize().unique(),
        reverse=True,
    )

    selected_scar_date = None
    if scar_dates:
        newest_date = pd.Timestamp(scar_dates[0]).normalize()

        def date_label(value):
            current = pd.Timestamp(value).normalize()
            label = current.strftime("%m/%d/%Y")
            return f"{label} — Current / Newest" if current == newest_date else f"{label} — Historical"

        selected_scar_date = st.selectbox(
            "3. Select Scar / Contract Effective Date",
            scar_dates,
            index=0,
            format_func=date_label,
            key=f"{key_prefix}_scar_date",
        )

    if st.button("Create Table", type="primary", key=f"{key_prefix}_create"):
        if selected_scar_date is None:
            st.warning("Please select a contract date.")
            return

        selected = filter_data(
            data,
            selected_community,
            selected_series,
            selected_scar_date,
        )
        if selected.empty:
            st.warning("No pricing was found for the selected contract.")
            return

        date_text = pd.Timestamp(selected_scar_date).strftime("%m/%d/%Y")
        st.subheader(f"{selected_community} — {selected_series} — {date_text}")
        st.dataframe(
            build_contract_table(selected),
            hide_index=True,
            use_container_width=True,
        )


def show_contracts_home():
    st.markdown(
        """
        <div class="contracts-hero">
            <div class="section-kicker">Contract Database</div>
            <h1>Contracts</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    outer = st.columns([1.2, 2, 2, 1.2], gap="large")
    with outer[1]:
        if st.button("Production", type="primary", key="open_production", use_container_width=True):
            go_to_page("production_builders")
    with outer[2]:
        if st.button("Concrete", key="open_concrete", use_container_width=True):
            go_to_page("concrete_builders")


def builder_button(builder_name, division, button_type="secondary"):
    slug = BUILDER_SLUGS[builder_name]
    if st.button(
        builder_name,
        key=f"builder_{division}_{slug}",
        type=button_type,
        use_container_width=True,
    ):
        go_to_page(f"{division}_{slug}")


def show_builder_home(division):
    label = "Concrete" if division == "concrete" else "Production"
    if st.button("← Contracts", key=f"back_home_{division}"):
        go_to_page("home")

    st.markdown(
        f"""
        <div class="contracts-hero">
            <div class="section-kicker">{label}</div>
            <h1>{label} Contracts</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    row1 = st.columns(3, gap="large")
    with row1[0]: builder_button("Pulte", division, "primary")
    with row1[1]: builder_button("Woodside", division)
    with row1[2]: builder_button("Richmond", division)

    st.markdown('<div class="builder-spacer"></div>', unsafe_allow_html=True)
    row2 = st.columns(3, gap="large")
    with row2[0]: builder_button("Taylor Morrison", division)
    with row2[1]: builder_button("Century Communities", division)
    with row2[2]: builder_button("KB Homes", division)

    st.markdown('<div class="builder-spacer"></div>', unsafe_allow_html=True)
    row3 = st.columns([1, 1, 1], gap="large")
    with row3[1]: builder_button("Tri Pointe of Nevada", division)


def show_builder_contracts(builder_name, division):
    label = "Concrete" if division == "concrete" else "Production"
    slug = BUILDER_SLUGS[builder_name]

    left, right = st.columns([4, 1])
    with left:
        if st.button(f"← {label} Builders", key=f"back_{division}_{slug}"):
            go_to_page(f"{division}_builders")
    with right:
        if st.button("Refresh Data", key=f"refresh_{division}_{slug}", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.markdown(
        f"""
        <div class="contracts-hero">
            <div class="section-kicker">{builder_name} • {label}</div>
            <h1>{builder_name} {label} Contracts</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    all_data = load_builder_data(builder_name)

    if builder_name == "Pulte" and division == "concrete":
        loaded = set(all_data["Community"].dropna().unique())
        missing = EXPECTED_PULTE_CONCRETE - loaded
        if missing:
            st.warning("Missing concrete communities: " + ", ".join(sorted(missing)))

    active_data = get_division_data(all_data, builder_name, division, archived=False)
    render_contract_browser(active_data, f"{slug}_{division}_active")

    archive_set = ARCHIVED_COMMUNITIES.get((builder_name, division), set())
    if archive_set:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown(
            '<div class="archive-note">Completed communities</div>',
            unsafe_allow_html=True,
        )
        cols = st.columns([4, 1.5, 4])
        with cols[1]:
            if st.button("Archived Jobs", key=f"archive_{division}_{slug}", use_container_width=True):
                go_to_page(f"{division}_{slug}_archived")


def show_builder_archived(builder_name, division):
    label = "Concrete" if division == "concrete" else "Production"
    slug = BUILDER_SLUGS[builder_name]

    if st.button(f"← {builder_name} {label}", key=f"back_archive_{division}_{slug}"):
        go_to_page(f"{division}_{slug}")

    st.markdown(
        f"""
        <div class="contracts-hero">
            <div class="section-kicker">{builder_name} • {label}</div>
            <h1>Archived Jobs</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    data = load_builder_data(builder_name)
    archived = get_division_data(data, builder_name, division, archived=True)
    render_contract_browser(archived, f"{slug}_{division}_archived")


def show_builder_placeholder(division, builder_name):
    label = "Concrete" if division == "concrete" else "Production"
    slug = BUILDER_SLUGS[builder_name]
    if st.button(f"← {label} Builders", key=f"back_placeholder_{division}_{slug}"):
        go_to_page(f"{division}_builders")

    st.markdown(
        f"""
        <div class="contracts-hero">
            <div class="section-kicker">{label}</div>
            <h1>{builder_name} Contracts</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info("No contracts loaded.")


if "contracts_page" not in st.session_state:
    st.session_state["contracts_page"] = "home"

page = st.session_state["contracts_page"]

if page == "home":
    show_contracts_home()
elif page == "production_builders":
    show_builder_home("production")
elif page == "concrete_builders":
    show_builder_home("concrete")
else:
    handled = False
    for division in ("production", "concrete"):
        prefix = f"{division}_"
        if not page.startswith(prefix):
            continue

        route = page[len(prefix):]
        archived = route.endswith("_archived")
        slug = route[:-9] if archived else route

        builder_name = next((name for name, value in BUILDER_SLUGS.items() if value == slug), None)
        if builder_name:
            if builder_name in ACTIVE_BUILDERS:
                if archived:
                    show_builder_archived(builder_name, division)
                else:
                    show_builder_contracts(builder_name, division)
            else:
                show_builder_placeholder(division, builder_name)
            handled = True
            break

    if not handled:
        go_to_page("home")

st.markdown("---")
st.markdown(
    '<div class="app-footer">Created and maintained by Alejandro Escutia | © 2024-2026</div>',
    unsafe_allow_html=True,
)
