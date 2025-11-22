#this is the u[pdated version of app.py thats doesnt do all the data 
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# -----------------------------------------------------------
# CONFIG
# -----------------------------------------------------------

DATA_URL = "https://data.austintexas.gov/api/views/3syk-w9eu/rows.csv?accessType=DOWNLOAD"

# Approximate Austin boundaries
AUSTIN_LAT_MIN = 30.0
AUSTIN_LAT_MAX = 30.6
AUSTIN_LON_MIN = -98.0
AUSTIN_LON_MAX = -97.0


# -----------------------------------------------------------
# DATA LOADING (CACHED)
# -----------------------------------------------------------

@st.cache_data(show_spinner="Loading and cleaning Austin construction data…")
def load_and_clean_data():
    """
    Load a manageable subset of the Austin construction permits dataset
    and clean it for use in the app.

    On Streamlit Cloud we limit the number of rows to avoid running out
    of memory. Your local Colab / laptop version can still use the full
    dataset.
    """

    # Limit the number of rows to keep memory usage safe on Streamlit Cloud.
    # The dataset is sorted so the newest permits are first; this keeps
    # recent years.
    df = pd.read_csv(
        DATA_URL,
        low_memory=False,
        nrows=400_000,  # adjust if needed; ~recent years only
        usecols=[
            "Permit Num",
            "Permit Type",
            "Issued Date",
            "Project Name",
            "Latitude",
            "Longitude",
            "Total Job Valuation",
        ],
    )

    # Parse dates and extract year
    df["Issued Date"] = pd.to_datetime(df["Issued Date"], errors="coerce")
    df = df.dropna(subset=["Issued Date"])
    df["Year"] = df["Issued Date"].dt.year

    # Keep only rows with valid coordinates
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")

    df = df.dropna(subset=["Latitude", "Longitude"])
    df = df[
        (df["Latitude"] >= AUSTIN_LAT_MIN)
        & (df["Latitude"] <= AUSTIN_LAT_MAX)
        & (df["Longitude"] >= AUSTIN_LON_MIN)
        & (df["Longitude"] <= AUSTIN_LON_MAX)
    ]

    # Clean up permit types (drop NaNs)
    df["Permit Type"] = df["Permit Type"].astype("category")

    return df


# -----------------------------------------------------------
# MAIN APP
# -----------------------------------------------------------

st.title("🏗️ CE311K Austin Construction Dashboard")

st.write(
    "Interactive dashboard showing real Austin construction permit data. "
    "Use the filters in the sidebar to explore trends by year, location, "
    "and permit type. This deployed version uses a recent subset of the "
    "data to run reliably on Streamlit Cloud."
)

df = load_and_clean_data()

st.sidebar.header("Filters")

# Year filter
min_year = int(df["Year"].min())
max_year = int(df["Year"].max())
year_range = st.sidebar.slider(
    "Year range",
    min_value=min_year,
    max_value=max_year,
    value=(max(max_year - 10, min_year), max_year),
)

# Permit type filter
permit_types_all = sorted(df["Permit Type"].dropna().unique())
default_permits = permit_types_all  # show all by default
selected_permit_types = st.sidebar.multiselect(
    "Permit types",
    options=permit_types_all,
    default=default_permits,
)

# Apply filters
filtered = df[
    (df["Year"].between(year_range[0], year_range[1]))
    & (df["Permit Type"].isin(selected_permit_types))
]

st.write(
    f"Showing **{len(filtered):,}** permits from "
    f"**{year_range[0]}–{year_range[1]}** for "
    f"permit types: {', '.join(selected_permit_types) if selected_permit_types else 'none'}."
)

# -----------------------------------------------------------
# MAP OF FILTERED PERMITS
# -----------------------------------------------------------

st.subheader("🗺️ Map of Austin Construction Permits (Filtered)")

if filtered.empty:
    st.warning("No permits match the current filters.")
else:
    fig_map, ax_map = plt.subplots(figsize=(6, 6))
    ax_map.scatter(
        filtered["Longitude"],
        filtered["Latitude"],
        s=2,
        alpha=0.4,
    )
    ax_map.set_xlabel("Longitude")
    ax_map.set_ylabel("Latitude")
    ax_map.set_title("Austin Construction Permits (Filtered)")
    ax_map.grid(True, linestyle="--", alpha=0.3)
    st.pyplot(fig_map)

# -----------------------------------------------------------
# YEARLY SPATIAL DISTRIBUTION BY PERMIT TYPE
# -----------------------------------------------------------

st.subheader("Yearly Spatial Distribution by Permit Type")

st.write(
    "Select a year below to see how different permit types are distributed "
    "across Austin for that year. Each color corresponds to a permit type."
)

if df.empty:
    st.warning("No data available to plot.")
else:
    year_options = sorted(df["Year"].dropna().unique())
    default_year_index = len(year_options) - 1  # most recent year

    selected_year = st.selectbox(
        "Choose a year to visualize:",
        options=year_options,
        index=default_year_index,
    )

    year_data = df[df["Year"] == selected_year]

    st.write(f"Permits in {selected_year}: **{len(year_data):,}**")

    if year_data.empty:
        st.warning("No data for this year.")
    else:
        # Build a color map per permit type
        year_permit_types = sorted(year_data["Permit Type"].dropna().unique())
        cmap_object = plt.colormaps.get_cmap("tab10")
        color_map = {}

        if len(year_permit_types) == 1:
            color_map[year_permit_types[0]] = cmap_object(0.5)
        elif len(year_permit_types) > 1:
            for i, pt in enumerate(year_permit_types):
                color_map[pt] = cmap_object(i / (len(year_permit_types) - 1))

        fig_year, ax_year = plt.subplots(figsize=(6, 6))
        for permit_type in year_permit_types:
            type_data = year_data[year_data["Permit Type"] == permit_type]
            ax_year.scatter(
                type_data["Longitude"],
                type_data["Latitude"],
                s=5,
                alpha=0.6,
                color=color_map.get(permit_type, "gray"),
                label=permit_type,
            )

        ax_year.set_title(f"Construction Permits in Austin – {selected_year}")
        ax_year.set_xlabel("Longitude")
        ax_year.set_ylabel("Latitude")
        ax_year.grid(True, linestyle="--", alpha=0.7)
        ax_year.legend(title="Permit Type", bbox_to_anchor=(1.05, 1), loc="upper left")
        plt.tight_layout()
        st.pyplot(fig_year)

# -----------------------------------------------------------
# TABLE PREVIEW
# -----------------------------------------------------------

st.subheader("📋 Sample of Filtered Permits")

if filtered.empty:
    st.info("No data to display. Try widening your filters.")
else:
    show_cols = [
        "Permit Num",
        "Permit Type",
        "Issued Date",
        "Project Name",
        "Total Job Valuation",
        "Latitude",
        "Longitude",
        "Year",
    ]
    existing_cols = [c for c in show_cols if c in filtered.columns]
    st.dataframe(filtered[existing_cols].head(200))
