import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# Page Configuration
st.set_page_config(layout="wide", page_title="Luxembourg Historical Map Prototype")

st.title("🏛️ Luxembourg City Historical & Rental Map")
st.markdown("Prototype showcasing historical locations, businesses, and available spaces.")

# Initialize map state
if 'map_center' not in st.session_state:
    st.session_state.map_center = [49.6116, 6.1319]
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 14

# 1. Load Data (уже с готовыми Latitude и Longitude)
@st.cache_data
def load_data(file_path):
    df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
    df.columns = df.columns.str.strip().str.title()

    # Automatically extract year from the Source column
    if 'Source' in df.columns:
        df['Year'] = df['Source'].astype(str).str.extract(r'(18\d{2}|19\d{2}|20\d{2})')[0]
        df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
    else:
        df['Year'] = None

    return df

data_path = "luxembourg_places.csv"
df = load_data(data_path)

def get_marker_color(type_str):
    t = str(type_str).lower()
    if "event" in t:
        return "purple"
    elif "accident" in t:
        return "darkred"
    elif "caf" in t:
        return "orange"
    elif "rent" in t:
        return "green"
    elif "sale" in t:
        return "blue"
    elif "dentist" in t:
        return "red"
    else:
        return "cadetblue"

# 2. Sidebar Search & Filter Controls
st.sidebar.header("🔍 Search & Filters")

search_query = st.sidebar.text_input("Search Keyword (Name / Description):", "")

all_types = df['Type'].astype(str).unique().tolist()
selected_types = st.sidebar.multiselect("Filter by Type:", options=all_types, default=all_types)

# --- Year Filter ---
all_years = sorted([int(y) for y in df['Year'].dropna().unique()])
selected_years = st.sidebar.multiselect("Filter by Year:", options=all_years, default=all_years) if all_years else []

# --- MAP LEGEND ---
st.sidebar.markdown("---")
st.sidebar.subheader("🎨 Map Legend")

legend_html = '<div style="line-height: 1.8;">'
for t_name in all_types:
    c = get_marker_color(t_name)
    legend_html += f'<span style="height: 12px; width: 12px; background-color: {c}; display: inline-block; border-radius: 50%; margin-right: 8px;"></span><b>{t_name}:</b> {c.capitalize()}<br>'
legend_html += '</div>'

st.sidebar.markdown(legend_html, unsafe_allow_html=True)

# Apply Filters
filtered_df = df[df['Type'].astype(str).isin(selected_types)]

if all_years and selected_years:
    filtered_df = filtered_df[filtered_df['Year'].isin(selected_years) | filtered_df['Year'].isna()]

if search_query:
    name_match = filtered_df['Name'].astype(str).str.contains(search_query, case=False, na=False)
    desc_match = filtered_df['Description'].astype(str).str.contains(search_query, case=False, na=False)
    filtered_df = filtered_df[name_match | desc_match]

# 3. Main Screen Layout
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"Map View ({len(filtered_df)} spots found)")
    
    m = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.map_zoom, tiles="OpenStreetMap")
    
    for idx, row in filtered_df.iterrows():
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
        
        color = get_marker_color(row['Type'])
            
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
