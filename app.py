import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# ------------- DATA LOADING & CLEANING ------------- #
@st.cache_data
def load_and_clean_data():
    url = "https://data.austintexas.gov/api/views/3syk-w9eu/rows.csv?accessType=DOWNLOAD"

    # This will download the data from the website (like Colab did)
    df = pd.read_csv(url, low_memory=False)

    # Convert Issued Date to datetime and extract Year
    df["Date"] = pd.to_datetime(df["Issued Date"], errors="coerce")
    df["Year"] = df["Date"].dt.year

    # Define Austin bounds
    austin_lat_min = 30.0
    austin_lat_max = 30.6
    austin_lon_min = -98.0
    austin_lon_max = -97.0

    valid_latitude = (df["Latitude"] > austin_lat_min) & (df["Latitude"] < austin_lat_max)
    valid_longitude = (df["Longitude"] > austin_lon_min) & (df["Longitude"] < austin_lon_max)

    valid_coordinates = valid_latitude & valid_longitude
    austin_construction = df[valid_coordinates].copy()

    # Drop rows with missing coordinates after filtering
    austin_construction = austin_construction.dropna(subset=["Latitude", "Longitude"])

    return austin_construction


# ------------- APP UI ------------- #
st.title("Sort & Report ")

st.write(
    "Welcome To the User Interface for Sort & Report. This app loads Austin construction permits directly from"
    "the city of Austin open data website and lets you filter the permit data."
)

st.info(
    "⚠️ A lot of data is being filtered so this may take a while, especially the first time you use it! "
    
)

# Show a spinner while data loads
with st.spinner("⏳ Loading Austin construction permit data..."):
    df = load_and_clean_data()

st.success(f"🎉 Data loaded! Total permits after cleaning: {len(df):,}")

# ------------- FILTERS (Sidebar) ------------- #
st.sidebar.header("Filters")

min_year = int(df["Year"].min())
max_year = int(df["Year"].max())

year_range = st.sidebar.slider(
    "Filter by Year Range",
    min_value=min_year,
    max_value=max_year,
    value=(max_year - 5, max_year),
)

# Permit Type Filter if it exists
permit_column = None
for col in df.columns:
    if col.lower().strip() == "permit type":
        permit_column = col
        break

selected_types = None
if permit_column:
    permit_types = sorted(df[permit_column].dropna().unique().tolist())
    selected_types = st.sidebar.multiselect(
        "Permit Type",
        options=permit_types,
        default=permit_types[:5] if len(permit_types) > 5 else permit_types,
    )

# Apply Filtering
filtered = df[
    (df["Year"] >= year_range[0]) &
    (df["Year"] <= year_range[1])
]

if selected_types:
    filtered = filtered[filtered[permit_column].isin(selected_types)]

st.write(f"📍 Permits matching filters: **{len(filtered):,}**")

# Downsample for plotting so it doesn’t lag with millions of points
max_points = 50000
if len(filtered) > max_points:
    plot_data = filtered.sample(max_points, random_state=0)
    st.caption(f"🔍 Showing a random sample of {max_points:,} points.")
else:
    plot_data = filtered

# ------------- MAPS ------------- #
st.subheader("🗺️ Map of Austin Construction Permits")

fig, ax = plt.subplots(figsize=(6, 6))
ax.scatter(plot_data["Longitude"], plot_data["Latitude"], s=1, alpha=0.3)
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_title("Austin Construction Permits")
st.pyplot(fig)

# ------------- TABLE PREVIEW ------------- #
st.subheader("📋 Sample of Filtered Permits")
st.dataframe(filtered.head(200))

# ------------- YEARLY MAP BY PERMIT TYPE ------------- #
st.subheader("Yearly Spatial Distribution by Permit Type")

st.write(
    "Select a year below to see how different permit types are distributed "
    "across Austin for that year. Each color corresponds to a permit type "
    "(BP, DS, EP, MP, PP)."
    "It would be too lengthy to do all 5 permit types for all 54 years so "
    "it's grouped by decades pre-200,then every 5 years, then each year "
    "indivudually from 2019-2025"
)

# Make sure coordinates and permit types are clean
df_yearly = df.copy()
df_yearly["Latitude"] = pd.to_numeric(df_yearly["Latitude"], errors="coerce")
df_yearly["Longitude"] = pd.to_numeric(df_yearly["Longitude"], errors="coerce")
df_yearly = df_yearly.dropna(subset=["Latitude", "Longitude", "Permit Type", "Year"])

# Build a color map for each permit type (like in your Colab)
permit_types_all = sorted(df_yearly["Permit Type"].dropna().unique())
cmap_object = plt.colormaps.get_cmap("tab10")
color_map = {}

if len(permit_types_all) == 1:
    # Only one permit type → just pick the middle color
    color_map[permit_types_all[0]] = cmap_object(0.5)
elif len(permit_types_all) > 1:
    for i, pt in enumerate(permit_types_all):
        color_map[pt] = cmap_object(i / (len(permit_types_all) - 1))

# Let the user pick a year (instead of looping all years at once)
year_options = sorted(df_yearly["Year"].dropna().unique())
default_year_index = len(year_options) - 1  # default to most recent year

selected_year = st.selectbox(
    "Choose a year to visualize permit-type clusters:",
    year_options,
    index=default_year_index,
)

year_data = df_yearly[df_yearly["Year"] == selected_year]

st.write(f"Permits in {selected_year}: **{len(year_data):,}**")

if year_data.empty:
    st.warning("No data available for this year.")
else:
    fig2, ax2 = plt.subplots(figsize=(6, 6))

    # Plot each permit type in its own color (like your partner's loop)
    for permit_type in sorted(year_data["Permit Type"].dropna().unique()):
        type_data = year_data[year_data["Permit Type"] == permit_type]
        ax2.scatter(
            type_data["Longitude"],
            type_data["Latitude"],
            s=5,
            alpha=0.6,
            color=color_map.get(permit_type, "gray"),
            label=permit_type,
        )

    ax2.set_title(f"Construction Permits in Austin – {selected_year}")
    ax2.set_xlabel("Longitude")
    ax2.set_ylabel("Latitude")
    ax2.grid(True, linestyle="--", alpha=0.7)
    ax2.legend(title="Permit Type", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.tight_layout()

    st.pyplot(fig2)

