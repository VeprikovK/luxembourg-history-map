
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

# Инициализация состояния карты
if 'map_center' not in st.session_state:
    st.session_state.map_center = [49.6116, 6.1319]
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 14

# 1. Load Data
@st.cache_data
def load_and_geocode_data(file_path):
    df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
    
    # Clean column names
    df.columns = df.columns.str.strip().str.title()

    # Автоматическое извлечение года из колонки Source (ищет 4 знака, начинающиеся с 18, 19 или 20)
    if 'Source' in df.columns:
        df['Year'] = df['Source'].astype(str).str.extract(r'(18\d{2}|19\d{2}|20\d{2})')[0]
        df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
    else:
        df['Year'] = None

    geolocator = Nominatim(user_agent="luxembourg_history_prototype")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    latitudes = []
    longitudes = []

    for addr in df['Address']:
        raw_addr = str(addr).strip()
        full_query = raw_addr if "luxembourg" in raw_addr.lower() else f"{raw_addr}, Luxembourg"

        # Attempt 1: Try full address
        try:
            location = geocode(full_query)
            if location:
                latitudes.append(location.latitude)
                longitudes.append(location.longitude)
                continue
        except Exception:
            pass

        # Attempt 2: Fallback to Street Only
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
data_path = "luxembourg_places.csv"

# Load & Geocode
with st.spinner("Loading map and geocoding addresses..."):
    df = load_and_geocode_data(data_path)

# 2. Sidebar Search & Filter Controls
st.sidebar.header("🔍 Search & Filters")

search_query = st.sidebar.text_input("Search Keyword (Name / Description):", "")

all_types = df['Type'].astype(str).unique().tolist()
selected_types = st.sidebar.multiselect("Filter by Type:", options=all_types, default=all_types)

# --- Фильтр по годам ---
all_years = sorted([int(y) for y in df['Year'].dropna().unique()])
if all_years:
    selected_years = st.sidebar.multiselect("Filter by Year:", options=all_years, default=all_years)
else:
    selected_years = []

# --- ЛЕГЕНДА КАРТЫ ---
st.sidebar.markdown("---")
st.sidebar.subheader("🎨 Легенда карты")
st.sidebar.markdown(
    """
    <div style="line-height: 1.8;">
        <span style="height: 12px; width: 12px; background-color: #3182bd; display: inline-block; border-radius: 50%; margin-right: 8px;"></span><b>Housing (sale):</b> Синий<br>
        <span style="height: 12px; width: 12px; background-color: #31a354; display: inline-block; border-radius: 50%; margin-right: 8px;"></span><b>Housing (rent):</b> Зеленый<br>
        <span style="height: 12px; width: 12px; background-color: #de2d26; display: inline-block; border-radius: 50%; margin-right: 8px;"></span><b>Dentists:</b> Красный<br>
        <span style="height: 12px; width: 12px; background-color: #e6550d; display: inline-block; border-radius: 50%; margin-right: 8px;"></span><b>Cafes:</b> Оранжевый
    </div>
    """,
    unsafe_allow_html=True
)

# Apply Filters to DataFrame (Type + Year + Search)
filtered_df = df[df['Type'].astype(str).isin(selected_types)]

if all_years and selected_years:
    # Оставляем объекты, у которых год входит в выбранный список, либо год не указан (NaN)
    filtered_df = filtered_df[filtered_df['Year'].isin(selected_years) | filtered_df['Year'].isna()]

if search_query:
    name_match = filtered_df['Name'].astype(str).str.contains(search_query, case=False, na=False)
    desc_match = filtered_df['Description'].astype(str).str.contains(search_query, case=False, na=False)
    filtered_df = filtered_df[name_match | desc_match]

# 3. Main Screen Layout (Map on Left, Detail Cards on Right)
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"Map View ({len(filtered_df)} spots found)")
    
    m = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.map_zoom, tiles="OpenStreetMap")
    
    for idx, row in filtered_df.iterrows():
        # Добавим вывод года в попап, если он нашелся
        year_str = f"<p><b>Year:</b> {int(row['Year'])}</p>" if pd.notna(row.get('Year')) else ""
        
        popup_html = f"""
        <div style="width: 200px;">
            <h4>{row['Name']}</h4>
            <p><b>Type:</b> {row['Type']}</p>
            {year_str}
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
        elif "sale" in t_val:
            color = "blue"
            
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=row['Name'],
            icon=folium.Icon(color=color, icon="info-sign")
        ).add_to(m)

    st_folium(m, width=800, height=550)

with col2:
    st.subheader("📋 Results & Details")
    with st.container(height=550):
        for idx, row in filtered_df.iterrows():
            year_label = f" ({int(row['Year'])})" if pd.notna(row.get('Year')) else ""
            with st.expander(f"📍 {row['Name']}{year_label} ({row['Type']})"):
                st.write(f"**Address:** {row['Address']}")
                if pd.notna(row.get('Year')):
                    st.write(f"**Year:** {int(row['Year'])}")
                if pd.notna(row.get('Price')):
                    st.write(f"**Price:** {row['Price']}")
                st.write(f"**Description:** {row['Description']}")
                if pd.notna(row.get('Source')):
                    st.write(f"**Source:** {row['Source']}")
                
                if st.button("🗺️ Show on the map", key=f"btn_{idx}"):
                    st.session_state.map_center = [row['Latitude'], row['Longitude']]
                    st.session_state.map_zoom = 17 
                    st.rerun()
