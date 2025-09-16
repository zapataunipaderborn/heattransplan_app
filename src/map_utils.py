"""
Map functionality for the Heat Integration Analysis app.
Handles map creation, tile rendering, and coordinate operations.
"""

import streamlit as st
import folium
import requests
from io import BytesIO
from PIL import Image
from staticmap import StaticMap, CircleMarker
from streamlit_folium import st_folium

from config import TILE_TEMPLATES, MAP_WIDTH, MAP_HEIGHT, BASE_OPTIONS


def create_folium_map(center, zoom, base_layer):
    """
    Create a Folium map with the specified base layer.
    
    Args:
        center: [lat, lon] coordinates for map center
        zoom: Zoom level
        base_layer: Base layer type ('OpenStreetMap', 'Satellite', 'Positron', 'Blank')
        
    Returns:
        folium.Map: Configured map object
    """
    if base_layer == 'Blank':
        fmap = folium.Map(location=center, zoom_start=zoom, tiles=None)
        # Inject CSS for blank background
        st.markdown("""
        <style>
        div.leaflet-container {background: #f2f2f3 !important;}
        </style>
        """, unsafe_allow_html=True)
    elif base_layer == 'Satellite':
        fmap = folium.Map(location=center, zoom_start=zoom, tiles=None)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri WorldImagery',
            name='Satellite'
        ).add_to(fmap)
    elif base_layer == 'Positron':
        fmap = folium.Map(location=center, zoom_start=zoom, tiles=None)
        folium.TileLayer(
            tiles='https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
            attr='CartoDB Positron',
            name='Positron'
        ).add_to(fmap)
    else:  # OpenStreetMap
        fmap = folium.Map(location=center, zoom_start=zoom)
    
    return fmap


def geocode_address(address):
    """
    Geocode an address using Nominatim API.
    
    Args:
        address: Address string to geocode
        
    Returns:
        tuple: (lat, lon) or (None, None) if failed
    """
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': address,
            'format': 'json',
            'limit': 1
        }
        headers = {
            'User-Agent': 'HeatIntegrationApp/1.0'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            return lat, lon
        return None, None
    except Exception as e:
        st.error(f"Geocoding failed: {e}")
        return None, None


def capture_map_snapshots(center, zoom):
    """
    Capture static map snapshots for all tile layers.
    
    Args:
        center: [lat, lon] coordinates for map center
        zoom: Zoom level
        
    Returns:
        dict: Dictionary mapping layer names to image bytes
    """
    snapshots = {}
    
    for layer_name, template in TILE_TEMPLATES.items():
        try:
            smap = StaticMap(MAP_WIDTH, MAP_HEIGHT, url_template=template)
            marker = CircleMarker((center[1], center[0]), 'red', 12)
            smap.add_marker(marker)
            
            img_layer = smap.render(zoom=int(zoom))
            if img_layer is None:
                st.error(f"Failed to render {layer_name} map layer")
                continue
                
            buf_l = BytesIO()
            img_layer.save(buf_l, format='PNG')
            snapshot_data = buf_l.getvalue()
            
            if len(snapshot_data) == 0:
                st.error(f"Empty image data for {layer_name}")
                continue
                
            snapshots[layer_name] = snapshot_data
            st.success(f"Successfully captured {layer_name} ({len(snapshot_data)} bytes)")
            
        except Exception as e:
            st.error(f"Failed to capture {layer_name}: {e}")
            continue
    
    return snapshots


def get_base_image(base_layer, snapshots_dict, fallback_snapshot):
    """
    Get the base image for the specified layer.
    
    Args:
        base_layer: Base layer name
        snapshots_dict: Dictionary of available snapshots
        fallback_snapshot: Fallback snapshot data
        
    Returns:
        PIL.Image: Base image
    """
    if base_layer == 'Blank':
        return Image.new('RGBA', (MAP_WIDTH, MAP_HEIGHT), (242, 242, 243, 255))
    else:
        chosen_bytes = snapshots_dict.get(base_layer) or fallback_snapshot
        if chosen_bytes:
            return Image.open(BytesIO(chosen_bytes)).convert("RGBA")
        else:
            return Image.new('RGBA', (MAP_WIDTH, MAP_HEIGHT), (242, 242, 243, 255))


def render_folium_map(map_obj, processes=None):
    """
    Render a Folium map with optional process markers.
    
    Args:
        map_obj: Folium map object
        processes: List of process data with coordinates
        
    Returns:
        dict: Map data from streamlit-folium
    """
    # Add process markers if provided
    if processes:
        for i, proc in enumerate(processes):
            lat = proc.get('lat')
            lon = proc.get('lon')
            if lat and lon:
                try:
                    lat_f = float(lat)
                    lon_f = float(lon)
                    name = proc.get('name', f'Subprocess {i+1}')
                    folium.Marker(
                        [lat_f, lon_f],
                        popup=name,
                        tooltip=name
                    ).add_to(map_obj)
                except (ValueError, TypeError):
                    continue
    
    # Render the map
    map_data = st_folium(
        map_obj,
        key="select_map",
        width=None,
        height=520,
        returned_objects=["last_object_clicked", "center", "zoom", "bounds"]
    )
    
    return map_data
