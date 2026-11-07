import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import re

# Page Configuration
st.set_page_config(layout="wide", page_title="Luxembourg Historical Map Prototype")

st.title("🏛️ Luxembourg City Historical & Rental Map")
st.markdown("Prototype showcasing historical locations, businesses, and available spaces.")

# 1. Load Data
@st.cache_data
def load_and_geocode_data(file_path):
    df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)

    # Clean column names (removes spaces, makes them Title Case: Name, Type, Address, Description, Price, Source)
    df.columns = df.columns.str.strip().str.title()

    geolocator = Nominatim(user_agent="luxembourg_history_prototype")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    latitudes = []
    longitudes = []

    for addr in df['Address']:
        raw_addr = str(addr).strip()
        full_query = raw_addr if "luxembourg" in raw_addr.lower() else f"{raw_addr}, Luxembourg"

        # Attempt 1: Try full address (Number + Street)
        try:
            location = geocode(full_query)
            if location:
                latitudes.append(location.latitude)
                longitudes.append(location.longitude)
                continue
        except Exception:
            pass

        # Attempt 2: Fallback to Street Only (strip leading house numbers)
        try:
            street_only = re.sub(r'^\d+\s*', '', raw_addr).strip()
            street_query = street_only if "luxembourg" in street_only.lower() else f"{street_only}, Luxembourg"

            location = geocode(street_query)
            if location:
                latitudes.append(location.latitude)
                longitudes.append(location.longitude)
                continue
        except Exception:
            pass

        # Attempt 3: Ultimate fallback to City Center
        latitudes.append(49.6116)
        longitudes.append(6.1319)

    df['Latitude'] = latitudes
    df['Longitude'] = longitudes
    return df

# Replace with your full file path if needed
data_path = r"C:\Users\rubed\Saved Games\luxembourg_places.csv"

# Load & Geocode
with st.spinner("Loading map and geocoding addresses..."):
    df = load_and_geocode_data(data_path)

# 2. Sidebar Search & Filter Controls
st.sidebar.header("🔍 Search & Filters")

search_query = st.sidebar.text_input("Search Keyword (Name / Description):", "")

all_types = df['Type'].astype(str).unique().tolist()
selected_types = st.sidebar.multiselect("Filter by Type:", options=all_types, default=all_types)

filtered_df = df[df['Type'].astype(str).isin(selected_types)]

if search_query:
    name_match = filtered_df['Name'].astype(str).str.contains(search_query, case=False, na=False)
    desc_match = filtered_df['Description'].astype(str).str.contains(search_query, case=False, na=False)
    filtered_df = filtered_df[name_match | desc_match]

# 3. Main Screen Layout (Map on Left, Detail Cards on Right)
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"Map View ({len(filtered_df)} spots found)")

    m = folium.Map(location=[49.6116, 6.1319], zoom_start=14, tiles="OpenStreetMap")

    for _, row in filtered_df.iterrows():
        popup_html = f"""
        <div style="width: 200px;">
            <h4>{row['Name']}</h4>
            <p><b>Type:</b> {row['Type']}</p>
            <p><b>Address:</b> {row['Address']}</p>
            <p><b>Price:</b> {row.get('Price', 'N/A')}</p>
            <p><i>{row.get('Description', '')}</i></p>
        </div>
        """

        color = "blue"
        t_val = str(row['Type']).lower()
        if "cafe" in t_val:
            color = "orange"
        elif "rent" in t_val or "space" in t_val:
            color = "green"
        elif "dentist" in t_val:
            color = "red"

        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=row['Name'],
            icon=folium.Icon(color=color, icon="info-sign")
        ).add_to(m)

    st_folium(m, width=800, height=550)

with col2:
    st.subheader("📋 Results & Details")
    for _, row in filtered_df.iterrows():
        with st.expander(f"📍 {row['Name']} ({row['Type']})"):
            st.write(f"**Address:** {row['Address']}")
            if pd.notna(row.get('Price')):
                st.write(f"**Price:** {row['Price']}")
            st.write(f"**Description:** {row['Description']}")
            if pd.notna(row.get('Source')):
                st.write(f"**Source:** {row['Source']}")

