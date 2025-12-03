import streamlit as st
import requests
from streamlit_folium import st_folium
import folium
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from staticmap import StaticMap, CircleMarker
from streamlit_image_coordinates import streamlit_image_coordinates
from math import radians, cos, sin, sqrt, atan2
import json
import base64
from datetime import datetime
from process_utils import (
    init_process_state,
    add_process,
    delete_process,
    add_stream_to_process,
    delete_stream_from_process,
    # New recursive functions for sub-subprocesses
    create_process_node,
    create_stream,
    add_child_to_node,
    delete_child_from_node,
    add_stream_to_node,
    delete_stream_from_node,
    iterate_all_nodes,
    get_level_name,
)
import csv
import os

# Load process models from JSON file
PROCESS_MODELS_PATH = os.path.join(os.path.dirname(__file__), '..', 'process_models.json')
with open(PROCESS_MODELS_PATH, 'r') as f:
    PROCESS_MODEL_DICT = json.load(f)


# =============================================================================
# RECURSIVE UI FUNCTION for rendering children at any level
# =============================================================================
def render_subsubprocesses(st_module, subprocess_node, subprocess_idx, process_model_dict=None):
    """
    Render sub-subprocesses for a subprocess. This is the FINAL level (level 2).
    No deeper recursion - only 3 levels: Process > Subprocess > Sub-subprocess
    
    Args:
        st_module: Streamlit module
        subprocess_node: The subprocess containing sub-subprocesses
        subprocess_idx: Index of the parent subprocess
        process_model_dict: Dict of process models for selection
    """
    children = subprocess_node.get('children', [])
    
    for ci, child in enumerate(children):
        child_key = f"subsub_{subprocess_idx}_{ci}"
        
        # Ensure child has level set
        if 'level' not in child:
            child['level'] = 2  # Sub-subprocess is level 2
        
        # Separator line
        st_module.markdown(
            "<div style='margin-left:15px;height:1px;background:#cccccc;margin:4px 0;'></div>", 
            unsafe_allow_html=True
        )
        
        # Initialize expanded state
        if 'expanded' not in child:
            child['expanded'] = False
        
        # Header row: Toggle | Name | Size | Place | Delete
        cols = st_module.columns([0.05, 0.45, 0.15, 0.15, 0.08])
        
        # Toggle expand/collapse
        toggle_label = "▾" if child.get('expanded', False) else "▸"
        if cols[0].button(toggle_label, key=f"{child_key}_toggle"):
            child['expanded'] = not child.get('expanded', False)
            st_module.rerun()
        
        # Name input
        default_name = child.get('name', f'Sub-subprocess {ci+1}')
        child['name'] = cols[1].text_input(
            "Sub-subprocess name",
            value=default_name,
            key=f"{child_key}_name",
            label_visibility="collapsed",
            placeholder=f"Sub-subprocess {ci+1}"
        )
        
        # Size slider
        if 'box_scale' not in child or child.get('box_scale') in (None, ''):
            child['box_scale'] = 0.8
        try:
            current_scale = float(child.get('box_scale', 0.8))
        except (ValueError, TypeError):
            current_scale = 0.8
        child['box_scale'] = cols[2].slider(
            "Size",
            min_value=0.3,
            max_value=2.0,
            value=current_scale,
            step=0.1,
            key=f"{child_key}_scale",
            label_visibility="collapsed"
        )
        
        # Place button
        place_key = f"child_subsub_{subprocess_idx}_{ci}"
        place_active = (st_module.session_state.get('placement_mode') and 
                       st_module.session_state.get('placing_process_idx') == place_key)
        if not place_active:
            if cols[3].button("Place", key=f"{child_key}_place"):
                st_module.session_state['placement_mode'] = True
                st_module.session_state['measure_mode'] = False
                st_module.session_state['placing_process_idx'] = place_key
                st_module.session_state['placing_node_ref'] = child
                st_module.session_state['ui_status_msg'] = f"Click on map to place: {child.get('name', 'Sub-subprocess')}"
                st_module.rerun()
        else:
            if cols[3].button("Done", key=f"{child_key}_place_done"):
                st_module.session_state['placement_mode'] = False
                st_module.session_state['placing_process_idx'] = None
                st_module.session_state['placing_node_ref'] = None
                st_module.session_state['ui_status_msg'] = "Placement mode disabled"
                st_module.rerun()
        
        # Delete button
        if cols[4].button("✕", key=f"{child_key}_delete"):
            delete_child_from_node(subprocess_node, ci)
            st_module.rerun()
        
        # Expanded content (Information and Streams only - no deeper children)
        if child.get('expanded', False):
            # Information toggle
            if 'info_expanded' not in child:
                child['info_expanded'] = False
            
            info_cols = st_module.columns([0.05, 0.95])
            info_toggle = "▾" if child.get('info_expanded', False) else "▸"
            if info_cols[0].button(info_toggle, key=f"{child_key}_info_toggle"):
                child['info_expanded'] = not child.get('info_expanded', False)
                st_module.rerun()
            info_cols[1].markdown("**Information**")
            
            if child.get('info_expanded', False):
                # Coordinates
                coord_cols = st_module.columns([1, 1, 1])
                child['lat'] = coord_cols[0].text_input("Latitude", value=str(child.get('lat', '') or ''), key=f"{child_key}_lat")
                child['lon'] = coord_cols[1].text_input("Longitude", value=str(child.get('lon', '') or ''), key=f"{child_key}_lon")
                
                # Hours
                if 'hours' not in child:
                    child['hours'] = ''
                child['hours'] = coord_cols[2].text_input("Hours", value=str(child.get('hours', '') or ''), key=f"{child_key}_hours")
                
                # Notes
                if 'extra_info' not in child:
                    child['extra_info'] = {}
                child['extra_info']['notes'] = st_module.text_area(
                    "Notes", 
                    value=child['extra_info'].get('notes', ''), 
                    key=f"{child_key}_notes", 
                    height=60
                )
            
            # Streams section
            streams_header = st_module.columns([0.7, 0.3])
            streams_header[0].markdown("**Streams**")
            if streams_header[1].button("➕ Stream", key=f"{child_key}_add_stream"):
                add_stream_to_node(child)
                st_module.rerun()
            
            streams = child.get('streams', [])
            if not streams:
                st_module.caption("No streams yet. Use ➕ to add one.")
            else:
                for si, stream in enumerate(streams):
                    render_stream_recursive(st_module, stream, f"{child_key}_stream_{si}", child, si)


def render_stream_recursive(st_module, stream, stream_key, parent_node, stream_index):
    """
    Render a single stream with the same UI at any level.
    This is REUSABLE for streams in any process node.
    """
    # Ensure stream has required fields
    if 'name' not in stream:
        stream['name'] = f"Stream {stream_index + 1}"
    if 'type' not in stream:
        stream['type'] = 'product'
    if 'properties' not in stream:
        stream['properties'] = {'prop1': 'Tin', 'prop2': 'Tout', 'prop3': 'ṁ', 'prop4': 'cp'}
    if 'values' not in stream:
        stream['values'] = {'val1': '', 'val2': '', 'val3': '', 'val4': ''}
    
    # Stream header
    header_cols = st_module.columns([1.5, 1, 0.5])
    stream['name'] = header_cols[0].text_input(
        "Stream name",
        value=stream.get('name', ''),
        key=f"{stream_key}_name",
        label_visibility="collapsed",
        placeholder=f"Stream {stream_index + 1}"
    )
    
    stream_types = ["product", "steam", "air", "water"]
    current_type = stream.get('type', 'product')
    if current_type not in stream_types:
        current_type = 'product'
    stream['type'] = header_cols[1].selectbox(
        "Type",
        options=stream_types,
        index=stream_types.index(current_type),
        key=f"{stream_key}_type",
        label_visibility="collapsed"
    )
    
    if header_cols[2].button("✕", key=f"{stream_key}_delete"):
        delete_stream_from_node(parent_node, stream_index)
        st_module.rerun()
    
    # All stream types use the same selection logic with different preselected defaults
    display_options = ["Tout", "ṁ", "cp", "CP"]
    
    # Define default preselected variables based on stream type
    stream_type = stream.get('type', 'product')
    if stream_type == 'product':
        default_display = ["Tout", "ṁ", "cp"]
    elif stream_type == 'steam':
        default_display = ["ṁ"]
    else:  # air, water, etc.
        default_display = ["ṁ"]
    
    # Initialize display_vars in session state if not present
    display_key = f"{stream_key}_display_vars"
    if display_key not in st_module.session_state:
        # Use existing stream setting or default based on type
        current_display = stream.get('display_vars', None)
        if current_display is None:
            current_display = default_display
        current_display = [v for v in current_display if v in display_options]
        st_module.session_state[display_key] = current_display
    
    selected_display = st_module.multiselect(
        "Variables",
        options=display_options,
        key=display_key,
        help="Select variables to enter (Tin is always shown)"
    )
    stream['display_vars'] = selected_display
    
    # Build list of properties to show: Tin always + selected ones
    props_to_show = ["Tin"] + selected_display
    n_props = len(props_to_show)
    
    if n_props > 0:
        prop_cols = st_module.columns(n_props)
        for pi, prop_name in enumerate(props_to_show):
            with prop_cols[pi]:
                st_module.caption(prop_name)
                current_val = stream.get('stream_values', {}).get(prop_name, '')
                
                new_val = st_module.text_input(
                    prop_name,
                    value=str(current_val),
                    key=f"{stream_key}_sval_{prop_name}",
                    label_visibility="collapsed"
                )
                
                # Store in stream_values dict
                if 'stream_values' not in stream:
                    stream['stream_values'] = {}
                stream['stream_values'][prop_name] = new_val
    
    # Update legacy fields for compatibility
    sv = stream.get('stream_values', {})
    stream['temp_in'] = sv.get('Tin', '')
    stream['temp_out'] = sv.get('Tout', '')
    stream['mdot'] = sv.get('ṁ', '')
    stream['cp'] = sv.get('cp', '')
    
    # Also update properties/values structure for drawing
    stream['properties'] = {'prop1': 'Tin'}
    stream['values'] = {'val1': sv.get('Tin', '')}
    idx = 2
    for var in selected_display:
        stream['properties'][f'prop{idx}'] = var
        stream['values'][f'val{idx}'] = sv.get(var, '')
        idx += 1


# Helper: convert pixel relative to center in snapshot to lon/lat using Web Mercator math
def snapshot_pixel_to_lonlat(px, py, center_ll, z_level, img_w, img_h):
    import math as _math
    def lonlat_to_xy(lon_val, lat_val, z_val):
        lat_rad = _math.radians(lat_val)
        n_val = 2.0 ** z_val
        xtile = (lon_val + 180.0) / 360.0 * n_val
        ytile = (1.0 - _math.log(_math.tan(lat_rad) + 1 / _math.cos(lat_rad)) / _math.pi) / 2.0 * n_val
        return xtile, ytile
    def xy_to_lonlat(xtile_v, ytile_v, z_val):
        n_val = 2.0 ** z_val
        lon_val = xtile_v / n_val * 360.0 - 180.0
        lat_rad = _math.atan(_math.sinh(_math.pi * (1 - 2 * ytile_v / n_val)))
        lat_val = _math.degrees(lat_rad)
        return lon_val, lat_val
    lon0, lat0 = center_ll
    xtile0, ytile0 = lonlat_to_xy(lon0, lat0, z_level)
    px_per_tile = 256
    dx = px - img_w / 2
    dy = py - img_h / 2
    dxtile = dx / px_per_tile
    dytile = dy / px_per_tile
    xtile = xtile0 + dxtile
    ytile = ytile0 + dytile
    lon_val, lat_val = xy_to_lonlat(xtile, ytile, z_level)
    return lon_val, lat_val

# Helper inverse: lon/lat to snapshot pixel
def snapshot_lonlat_to_pixel(lon_val_in, lat_val_in, center_ll, z_level, img_w, img_h):
    import math as _math
    def lonlat_to_xy(lon_inner, lat_inner, z_val):
        lat_rad = _math.radians(lat_inner)
        n_val = 2.0 ** z_val
        xtile = (lon_inner + 180.0) / 360.0 * n_val
        ytile = (1.0 - _math.log(_math.tan(lat_rad) + 1 / _math.cos(lat_rad)) / _math.pi) / 2.0 * n_val
        return xtile, ytile
    lon0, lat0 = center_ll
    xtile0, ytile0 = lonlat_to_xy(lon0, lat0, z_level)
    xtile, ytile = lonlat_to_xy(lon_val_in, lat_val_in, z_level)
    dxtile = xtile - xtile0
    dytile = ytile - ytile0
    px_per_tile = 256
    snapshot_px = img_w / 2 + dxtile * px_per_tile
    snapshot_py = img_h / 2 + dytile * px_per_tile
    return snapshot_px, snapshot_py

# Helper functions for saving and loading app state
def save_app_state():
    """Save the current app state to a JSON file"""
    state_to_save = {
        'timestamp': datetime.now().isoformat(),
        'map_locked': st.session_state.get('map_locked', False),
        'map_center': st.session_state.get('map_center', []),
        'map_zoom': st.session_state.get('map_zoom', 17.5),
        'current_base': st.session_state.get('current_base', 'OpenStreetMap'),
        'processes': st.session_state.get('processes', []),
        'proc_groups': st.session_state.get('proc_groups', []),
        'proc_group_names': st.session_state.get('proc_group_names', []),
        'proc_group_expanded': st.session_state.get('proc_group_expanded', []),
        'proc_group_coordinates': st.session_state.get('proc_group_coordinates', {}),
        'proc_group_info_expanded': st.session_state.get('proc_group_info_expanded', []),
        # Save notes
        'project_notes': st.session_state.get('project_notes', ''),
        'pinch_notes': st.session_state.get('pinch_notes', ''),
    }
    
    # Convert snapshots to base64 for JSON serialization
    snapshots = st.session_state.get('map_snapshots', {})
    encoded_snapshots = {}
    for key, img_bytes in snapshots.items():
        if img_bytes:
            encoded_snapshots[key] = base64.b64encode(img_bytes).decode('utf-8')
    state_to_save['map_snapshots_encoded'] = encoded_snapshots
    
    return json.dumps(state_to_save, indent=2)

def load_app_state(state_json):
    """Load app state from JSON data"""
    try:
        state = json.loads(state_json)
        
        # Restore session state
        st.session_state['map_locked'] = state.get('map_locked', False)
        st.session_state['map_center'] = state.get('map_center', [])
        st.session_state['map_zoom'] = state.get('map_zoom', 17.5)
        st.session_state['current_base'] = state.get('current_base', 'OpenStreetMap')
        st.session_state['processes'] = state.get('processes', [])
        st.session_state['proc_groups'] = state.get('proc_groups', [])
        st.session_state['proc_group_names'] = state.get('proc_group_names', [])
        st.session_state['proc_group_expanded'] = state.get('proc_group_expanded', [])
        
        # Convert proc_group_coordinates keys to integers (JSON converts them to strings)
        raw_coords = state.get('proc_group_coordinates', {})
        converted_coords = {}
        for key, value in raw_coords.items():
            converted_coords[int(key) if isinstance(key, str) else key] = value
        st.session_state['proc_group_coordinates'] = converted_coords
        
        st.session_state['proc_group_info_expanded'] = state.get('proc_group_info_expanded', [])
        
        # Restore notes
        st.session_state['project_notes'] = state.get('project_notes', '')
        st.session_state['pinch_notes'] = state.get('pinch_notes', '')
        
        # Restore snapshots from base64
        encoded_snapshots = state.get('map_snapshots_encoded', {})
        decoded_snapshots = {}
        for key, encoded_data in encoded_snapshots.items():
            decoded_snapshots[key] = base64.b64decode(encoded_data)
        st.session_state['map_snapshots'] = decoded_snapshots
        
        # Set the main snapshot - use current_base to get the right one
        current_base = state.get('current_base', 'OpenStreetMap')
        if decoded_snapshots:
            st.session_state['map_snapshot'] = decoded_snapshots.get(current_base) or decoded_snapshots.get('OpenStreetMap')
        
        # Also set analyze_base_layer to match
        st.session_state['analyze_base_layer'] = current_base
        
        # Update selector state to match loaded map
        st.session_state['selector_center'] = state.get('map_center', [])[:]
        st.session_state['selector_zoom'] = state.get('map_zoom', 17.5)
        
        # Reset UI interaction states to prevent freeze
        st.session_state['placement_mode'] = False
        st.session_state['placing_process_idx'] = None
        st.session_state['measure_mode'] = False
        st.session_state['measure_points'] = []
        st.session_state['measure_distance_m'] = None
        st.session_state['ui_status_msg'] = "State loaded successfully"
        
        # Initialize proc_expanded if processes exist
        if 'proc_expanded' not in st.session_state or len(st.session_state['proc_expanded']) != len(state.get('processes', [])):
            st.session_state['proc_expanded'] = [False] * len(state.get('processes', []))
        
        # Switch to Analyze mode if map was locked
        if state.get('map_locked', False):
            st.session_state['ui_mode_radio'] = 'Analyze'
        else:
            st.session_state['ui_mode_radio'] = 'Select Map'
        
        return True, f"State loaded successfully from {state.get('timestamp', 'unknown time')}"
    except Exception as e:
        return False, f"Error loading state: {str(e)}"

def export_to_csv():
    """Export all process data to CSV format with one row per stream"""
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Process', 'Subprocess', 'Process Latitude', 'Process Longitude', 'Process Hours',
        'Next Connection', 'Stream', 'Stream Tin (°C)', 'Stream Tout (°C)', 
        'Stream mdot', 'Stream cp',
        'Product Tin', 'Product Tout', 'Product mdot', 'Product cp',
        'Air Tin', 'Air Tout', 'Air mdot', 'Air cp',
        'Water Content In', 'Water Content Out', 'Density', 'Pressure', 'Notes'
    ])
    
    # Get process group information
    proc_groups = st.session_state.get('proc_groups', [])
    proc_group_names = st.session_state.get('proc_group_names', [])
    proc_group_coordinates = st.session_state.get('proc_group_coordinates', {})
    
    # Create mapping of subprocess index to group
    subprocess_to_group = {}
    for group_idx, group_subprocess_list in enumerate(proc_groups):
        for subprocess_idx in group_subprocess_list:
            subprocess_to_group[subprocess_idx] = group_idx
    
    # Iterate through all subprocesses
    for subprocess_idx, subprocess in enumerate(st.session_state.get('processes', [])):
        subprocess_name = subprocess.get('name') or f"Subprocess {subprocess_idx+1}"
        next_connection = subprocess.get('next', '')
        
        # Get process (group) name and coordinates
        parent_group_idx = subprocess_to_group.get(subprocess_idx)
        if parent_group_idx is not None and parent_group_idx < len(proc_group_names):
            process_name = proc_group_names[parent_group_idx]
            # Get process-level coordinates
            group_coords = proc_group_coordinates.get(parent_group_idx, {})
            process_lat = group_coords.get('lat', '')
            process_lon = group_coords.get('lon', '')
            process_hours = group_coords.get('hours', '')
        else:
            process_name = ''
            process_lat = ''
            process_lon = ''
            process_hours = ''
        
        # Get subprocess product information
        product_tin = subprocess.get('conntemp', '')
        product_tout = subprocess.get('product_tout', '')
        product_mdot = subprocess.get('connm', '')
        product_cp = subprocess.get('conncp', '')
        
        # Get subprocess extra information
        extra_info = subprocess.get('extra_info', {})
        air_tin = extra_info.get('air_tin', '')
        air_tout = extra_info.get('air_tout', '')
        air_mdot = extra_info.get('air_mdot', '')
        air_cp = extra_info.get('air_cp', '')
        water_content_in = extra_info.get('water_content_in', '')
        water_content_out = extra_info.get('water_content_out', '')
        density = extra_info.get('density', '')
        pressure = extra_info.get('pressure', '')
        notes = extra_info.get('notes', '')
        
        # Get streams
        streams = subprocess.get('streams', [])
        
        if streams:
            # One row per stream
            for stream_idx, stream in enumerate(streams):
                stream_name = stream.get('name', f"Stream {stream_idx + 1}")
                stream_type = stream.get('type', 'product')
                
                # Handle new stream structure with flexible properties
                properties = stream.get('properties', [])
                values = stream.get('values', [])
                
                if properties and values and len(properties) == len(values):
                    # New structure: create columns for each property-value pair
                    prop_value_str = "; ".join([f"{prop}:{val}" for prop, val in zip(properties, values)])
                    
                    # Extract legacy fields for backward compatibility
                    tin = ''
                    tout = ''
                    mdot = ''
                    cp = ''
                    for prop, val in zip(properties, values):
                        if prop == 'Tin':
                            tin = val
                        elif prop == 'Tout':
                            tout = val
                        elif prop == 'ṁ':
                            mdot = val
                        elif prop == 'cp':
                            cp = val
                else:
                    # Legacy structure: fallback to old fields
                    tin = stream.get('temp_in', '')
                    tout = stream.get('temp_out', '')
                    mdot = stream.get('mdot', '')
                    cp = stream.get('cp', '')
                    prop_value_str = f"Tin:{tin}; Tout:{tout}; ṁ:{mdot}; cp:{cp}"
                
                writer.writerow([
                    process_name,
                    subprocess_name,
                    process_lat,
                    process_lon,
                    process_hours,
                    next_connection,
                    stream_name,
                    tin,
                    tout,
                    mdot,
                    cp,
                    product_tin,
                    product_tout,
                    product_mdot,
                    product_cp,
                    air_tin,
                    air_tout,
                    air_mdot,
                    air_cp,
                    water_content_in,
                    water_content_out,
                    density,
                    pressure,
                    notes
                ])
        else:
            # If no streams, still write subprocess info
            writer.writerow([
                process_name,
                subprocess_name,
                process_lat,
                process_lon,
                process_hours,
                next_connection,
                '',  # No stream
                '',  # No Stream Tin
                '',  # No Stream Tout
                '',  # No Stream mdot
                '',  # No Stream cp
                product_tin,
                product_tout,
                product_mdot,
                product_cp,
                air_tin,
                air_tout,
                air_mdot,
                air_cp,
                water_content_in,
                water_content_out,
                density,
                pressure,
                notes
            ])
    
    return output.getvalue()


st.set_page_config(
    page_title="Energy Data Collection",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply styles immediately to prevent flash
st.markdown(
    """
    <style>
    :root {
        font-size: 11px !important;
    }
    section[data-testid="stSidebar"][aria-expanded="true"] {
        width: 180px !important;
        min-width: 180px !important;
    }
    section[data-testid="stSidebar"][aria-expanded="false"] {
        width: 0 !important;
        min-width: 0 !important;
        margin-left: 0 !important;
    }
    """,
    unsafe_allow_html=True,
)

# Compact top padding & utility CSS to keep map tight to top-right
st.markdown("""
<style>
/* Base tweaks - make everything more compact */
.block-container {padding-top:0rem; padding-bottom:0.1rem;}
div[data-testid="column"] > div:has(> div.map-region) {margin-top:0;}
.map-control-row {margin-bottom:0.1rem;}

/* Smaller fonts and elements - apply to all elements */
html, body, .stApp, * {font-size:11px !important;}
.stMarkdown p, .stMarkdown span, .stMarkdown li {font-size:11px !important;}
.stButton button {font-size:10px !important; padding:0.1rem 0.3rem !important;}
.stTextInput input, .stNumberInput input {font-size:10px !important; padding:0.1rem 0.2rem !important;}
.stRadio > div[role=radio] label {font-size:10px !important;}
.stDataFrame, .stDataFrame table {font-size:9px !important;}
.stSlider {font-size:9px !important;}
.stSelectbox, .stMultiselect {font-size:10px !important;}
.stExpander {font-size:10px !important;}

/* Tighter expander headers */
div.streamlit-expanderHeader {padding:0.2rem 0.3rem !important; font-size:10px !important;}
/* Group boxed layout - smaller */
.group-box {border:1px solid #ffffff; padding:3px 4px 4px 4px; margin:5px 0 8px 0; border-radius:4px; background:rgba(255,255,255,0.04);} 
.group-box.collapsed {padding-bottom:2px;}

/* Title with icon - smaller */
.title-container {display: flex; align-items: center; gap: 15px; margin-bottom: 5px; margin-top: 0px;}
h1 {font-size: 1.5rem !important; margin-bottom: 0.3rem !important;}

/* Make map & snapshot adapt on narrow screens */
@media (max-width: 1500px){
    iframe, iframe[data-testid="stIFrame"] {max-width:100% !important;}
}
@media (max-width: 1200px){
    iframe, iframe[data-testid="stIFrame"] {height:520px !important;}
    img[alt="meas_img"] {max-width:100% !important; height:auto !important;}
}
@media (max-width: 1000px){
    iframe, iframe[data-testid="stIFrame"] {height:480px !important;}
    img[alt="meas_img"] {max-width:100% !important;}
}
</style>
""", unsafe_allow_html=True)

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

st.markdown("""
<div class="title-container">
    <h1 style="margin:0;">Energy Data Collection</h1>
</div>
""", unsafe_allow_html=True)

MAP_WIDTH = 1200  # Reduced width for better responsiveness (was 1300)
MAP_HEIGHT = 650  # Slightly reduced height too

# Tile templates for snapshot capture (static)
TILE_TEMPLATES = {
    'OpenStreetMap': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    'Positron': 'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
    'Satellite': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
}

# Default start location (Universität Paderborn, Warburger Str. 100, 33098 Paderborn)
DEFAULT_START_ADDRESS = "Universität Paderborn, Warburger Str. 100, 33098 Paderborn"
# Approximate coordinates (lat, lon)
DEFAULT_START_COORDS = [51.70814085564164, 8.772155163087213]

# Session state for map lock and snapshot
if 'map_locked' not in st.session_state: st.session_state['map_locked'] = False
if 'map_snapshot' not in st.session_state: st.session_state['map_snapshot'] = None
if 'map_snapshots' not in st.session_state: st.session_state['map_snapshots'] = {}
if 'map_center' not in st.session_state: st.session_state['map_center'] = DEFAULT_START_COORDS[:]  # committed (locked) center for start address
if 'map_zoom' not in st.session_state: st.session_state['map_zoom'] = 17.5          # committed (locked) zoom
if 'selector_center' not in st.session_state: st.session_state['selector_center'] = st.session_state['map_center'][:]
if 'selector_zoom' not in st.session_state: st.session_state['selector_zoom'] = st.session_state['map_zoom']
# Base layer preference
if 'map_base_choice' not in st.session_state:
    st.session_state['map_base_choice'] = 'OpenStreetMap'
if 'analyze_base_choice' not in st.session_state:
    st.session_state['analyze_base_choice'] = 'OpenStreetMap'
# Initialize address input explicitly (prevents KeyError after widget key changes)
if 'address_input' not in st.session_state:
    st.session_state['address_input'] = ''
# State load tracking
if 'state_just_loaded' not in st.session_state:
    st.session_state['state_just_loaded'] = False
# Clean orphaned internal widget state keys left from layout changes (optional safeguard)
for _k in list(st.session_state.keys()):
    if isinstance(_k, str) and _k.startswith('$$WIDGET_ID-'):
        try:
            del st.session_state[_k]
        except KeyError:
            pass
# Track mode separately (avoid writing to widget key after creation)
if 'ui_mode_radio' not in st.session_state: st.session_state['ui_mode_radio'] = 'Select Map'
if 'measure_mode' not in st.session_state: st.session_state['measure_mode'] = False
if 'measure_points' not in st.session_state: st.session_state['measure_points'] = []
init_process_state(st.session_state)
if 'placing_process_idx' not in st.session_state: st.session_state['placing_process_idx'] = None
if 'placement_mode' not in st.session_state: st.session_state['placement_mode'] = False
if 'ui_status_msg' not in st.session_state: st.session_state['ui_status_msg'] = None
if 'analyze_base_layer' not in st.session_state: st.session_state['analyze_base_layer'] = 'OpenStreetMap'
# Group coordinates storage
if 'proc_group_coordinates' not in st.session_state: st.session_state['proc_group_coordinates'] = {}
# Unified persistent base layer selection (only changed by user interaction)
if 'current_base' not in st.session_state:
    st.session_state['current_base'] = 'OpenStreetMap'

left, right = st.columns([2, 6], gap="small")  # Much smaller left panel, much wider map area

with left:
    # Compact mode buttons side by side
    mode_current = st.session_state['ui_mode_radio']
    if mode_current == "Select Map":
        col_lock = st.columns([1])[0]
        if col_lock.button("Lock map and analyze", key="btn_lock_analyze"):
            # Use current live map state instead of stored selector values
            current_center = st.session_state.get('current_map_center')
            current_zoom = st.session_state.get('current_map_zoom')
            
            # Fallback to selector values if current state not available
            if current_center is None or current_zoom is None:
                new_center = st.session_state['selector_center'][:]
                new_zoom = st.session_state['selector_zoom']
            else:
                new_center = current_center[:]
                new_zoom = current_zoom
                
            selected_base_now = st.session_state.get('current_base', 'OpenStreetMap')
            existing_snaps = st.session_state.get('map_snapshots', {})
            regenerate = (
                (st.session_state.get('map_snapshot') is None) or
                (new_center != st.session_state.get('map_center')) or
                (new_zoom != st.session_state.get('map_zoom')) or
                (selected_base_now not in existing_snaps)  # ensure chosen base available
            )
            st.session_state['map_center'] = new_center
            st.session_state['map_zoom'] = new_zoom  # Store exact zoom for coordinate calculations
            if regenerate:
                try:
                    snapshots = {}
                    # Use rounded zoom for tile rendering but keep exact zoom for coordinates
                    render_zoom = round(float(new_zoom))
                    for layer_name, template in TILE_TEMPLATES.items():
                        smap = StaticMap(MAP_WIDTH, MAP_HEIGHT, url_template=template)
                        try:
                            marker = CircleMarker((new_center[1], new_center[0]), 'red', 12)
                            smap.add_marker(marker)
                        except (RuntimeError, OSError):
                            pass
                        # Use rounded zoom instead of truncated to better match Folium view
                        img_layer = smap.render(zoom=render_zoom)
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
                    st.session_state['map_snapshots'] = snapshots
                    # Legacy single snapshot retains OSM for backward compatibility
                    st.session_state['map_snapshot'] = snapshots.get('OpenStreetMap')
                except RuntimeError as gen_err:
                    st.session_state['ui_status_msg'] = f"Capture failed: {gen_err}"
                    st.error(f"Map capture error: {gen_err}")
                    st.rerun()
                except Exception as e:
                    st.session_state['ui_status_msg'] = f"Unexpected error: {e}"
                    st.error(f"Unexpected map error: {e}")
                    st.rerun()
            st.session_state['map_locked'] = True
            # Freeze analyze base only if user hasn't previously switched in Analyze; preserve separate map selection
            st.session_state['analyze_base_layer'] = selected_base_now
            # Keep current_base unchanged; analyze view will use it directly
            # Do NOT modify base_layer_choice_map here; that belongs to Select Map context
            st.session_state['ui_mode_radio'] = 'Analyze'
            if not st.session_state.get('ui_status_msg'):
                st.session_state['ui_status_msg'] = "Snapshot captured"
            st.rerun()
    else:  # Analyze mode
        col_unlock, col_add = st.columns([1,1])
        if col_unlock.button("Unlock map and select", key="btn_unlock_select"):
            # Preserve current locked map position for seamless transition
            if st.session_state.get('map_center') and st.session_state.get('map_zoom'):
                st.session_state['selector_center'] = st.session_state['map_center'][:]
                st.session_state['selector_zoom'] = st.session_state['map_zoom']
                st.session_state['current_map_center'] = st.session_state['map_center'][:]
                st.session_state['current_map_zoom'] = st.session_state['map_zoom']
            
            st.session_state.update({
                'ui_mode_radio': 'Select Map',
                'map_locked': False,
                'map_snapshot': None,
                'measure_mode': False,
                'measure_points': [],
                'measure_distance_m': None,
                'placement_mode': False,
                'placing_process_idx': None,
                'ui_status_msg': None,
            })
            st.rerun()
        if col_add.button("Add a process", key="btn_add_group_top"):
            # Ensure processes list exists
            if 'proc_groups' not in st.session_state:
                st.session_state['proc_groups'] = []
            st.session_state['proc_groups'].append([])  # new empty process
            # Sync process names & expansion
            if 'proc_group_names' not in st.session_state:
                st.session_state['proc_group_names'] = []
            st.session_state['proc_group_names'].append(f"Process {len(st.session_state['proc_groups'])}")
            if 'proc_group_expanded' not in st.session_state:
                st.session_state['proc_group_expanded'] = []
            st.session_state['proc_group_expanded'].append(False)  # Start collapsed by default
            if 'proc_group_info_expanded' not in st.session_state:
                st.session_state['proc_group_info_expanded'] = []
            st.session_state['proc_group_info_expanded'].append(False)  # Start collapsed by default
            st.session_state['ui_status_msg'] = "Added new empty process"
            st.rerun()
    
    st.markdown("---")
    
    # File uploader - only show when map is NOT locked (in Select Map mode)
    if not st.session_state.get('map_locked', False):
        if 'state_just_loaded' in st.session_state and st.session_state['state_just_loaded']:
            if st.button("Load Another", key="btn_load_another_left", help="Load another file"):
                st.session_state['state_just_loaded'] = False
                st.rerun()
        else:
            st.markdown("**Load saved state:**")
            uploaded_file = st.file_uploader("Load file", type=['json'], key="upload_state_left", label_visibility="collapsed")
            
            if uploaded_file is not None:
                try:
                    # Read the file immediately to avoid session state issues
                    file_contents = uploaded_file.getvalue().decode('utf-8')
                    success, message = load_app_state(file_contents)
                    if success:
                        st.session_state['state_just_loaded'] = True
                        # Clear the file uploader to prevent MediaFileStorageError
                        if 'upload_state_left' in st.session_state:
                            del st.session_state['upload_state_left']
                        st.rerun()
                    else:
                        st.error(message)
                except Exception as e:
                    st.error(f"Error loading file: {str(e)}")
        
        st.markdown("---")
    
    mode = st.session_state['ui_mode_radio']
    # Subprocess & Stream UI (only show in Analyze mode to mimic original workflow)
    if mode == "Analyze":
        # Show editor if we have any processes OR any groups (even empty groups)
        has_groups = bool(st.session_state.get('proc_groups'))
        if st.session_state['processes'] or has_groups:
            # Initialize expanded state tracker
            if 'proc_expanded' not in st.session_state:
                st.session_state['proc_expanded'] = []
            # Preserve existing flags; extend or truncate only as needed
            if len(st.session_state['proc_expanded']) < len(st.session_state['processes']):
                st.session_state['proc_expanded'].extend([False]*(len(st.session_state['processes']) - len(st.session_state['proc_expanded'])))
            elif len(st.session_state['proc_expanded']) > len(st.session_state['processes']):
                st.session_state['proc_expanded'] = st.session_state['proc_expanded'][:len(st.session_state['processes'])]
            # Track pending delete index
            if 'proc_delete_pending' not in st.session_state:
                st.session_state['proc_delete_pending'] = None

            # Initialize explicit groups if not present
            if 'proc_groups' not in st.session_state:
                st.session_state['proc_groups'] = [list(range(len(st.session_state['processes'])))] if st.session_state['processes'] else []
            # Ensure proc_expanded length matches processes
            if len(st.session_state['proc_expanded']) != len(st.session_state['processes']):
                st.session_state['proc_expanded'] = [False]*len(st.session_state['processes'])
            # Align names & expanded arrays to group list length
            group_count = len(st.session_state['proc_groups'])
            if 'proc_group_expanded' not in st.session_state:
                st.session_state['proc_group_expanded'] = [False]*group_count  # Start collapsed by default
            elif len(st.session_state['proc_group_expanded']) != group_count:
                st.session_state['proc_group_expanded'] = [st.session_state['proc_group_expanded'][g] if g < len(st.session_state['proc_group_expanded']) else False for g in range(group_count)]
            if 'proc_group_names' not in st.session_state:
                st.session_state['proc_group_names'] = [f"Group {g+1}" for g in range(group_count)]
            elif len(st.session_state['proc_group_names']) != group_count:
                current_names = st.session_state['proc_group_names']
                if len(current_names) < group_count:
                    current_names += [f"Group {g+1}" for g in range(len(current_names), group_count)]
                else:
                    current_names = current_names[:group_count]
                st.session_state['proc_group_names'] = current_names
            # Initialize information expanded state
            if 'proc_group_info_expanded' not in st.session_state:
                st.session_state['proc_group_info_expanded'] = [False]*group_count  # Start collapsed by default
            elif len(st.session_state['proc_group_info_expanded']) != group_count:
                st.session_state['proc_group_info_expanded'] = [st.session_state['proc_group_info_expanded'][g] if g < len(st.session_state['proc_group_info_expanded']) else False for g in range(group_count)]
            # Track group delete confirmation
            if 'group_delete_pending' not in st.session_state:
                st.session_state['group_delete_pending'] = None

            def _reindex_groups_after_delete(del_idx: int):
                groups = st.session_state.get('proc_groups', [])
                new_groups = []
                for grp in groups:
                    updated = []
                    for proc_index in grp:
                        if proc_index == del_idx:
                            continue
                        updated.append(proc_index - 1 if proc_index > del_idx else proc_index)
                    new_groups.append(updated)
                st.session_state['proc_groups'] = new_groups

            for g, g_list in enumerate(st.session_state['proc_groups']):
                # Initialize all group-specific session state variables BEFORE any UI elements
                # Process Model initialization for groups
                if 'proc_group_model' not in st.session_state:
                    st.session_state['proc_group_model'] = {}
                if g not in st.session_state['proc_group_model']:
                    st.session_state['proc_group_model'][g] = {'level1': None, 'level2': None}
                
                # Top thick separator for group
                st.markdown("<div style='height:3px; background:#888888; margin:12px 0 6px;'></div>", unsafe_allow_html=True)
                # Arrow | Name | Place | Count | Delete
                # Add a compact size control next to the group name (before Place)
                gh_cols = st.columns([0.05, 0.45, 0.18, 0.15, 0.12, 0.05])
                g_toggle_label = "▾" if st.session_state['proc_group_expanded'][g] else "▸"
                if gh_cols[0].button(g_toggle_label, key=f"group_toggle_{g}"):
                    st.session_state['proc_group_expanded'][g] = not st.session_state['proc_group_expanded'][g]
                    st.rerun()
                default_name = st.session_state['proc_group_names'][g]
                new_name = gh_cols[1].text_input("Group name", value=default_name, key=f"group_name_{g}", label_visibility="collapsed", placeholder=f"Group {g+1}")
                st.session_state['proc_group_names'][g] = new_name.strip() or default_name

                # Ensure proc_group_coordinates entry exists
                if 'proc_group_coordinates' not in st.session_state:
                    st.session_state['proc_group_coordinates'] = {}
                if g not in st.session_state['proc_group_coordinates']:
                    st.session_state['proc_group_coordinates'][g] = {'lat': '', 'lon': '', 'hours': '', 'box_scale': 1.5}

                # Compact size slider for main process box placed next to name
                try:
                    current_group_scale = float(st.session_state['proc_group_coordinates'][g].get('box_scale', 1.5) or 1.5)
                except (ValueError, TypeError):
                    current_group_scale = 1.5
                new_group_scale = gh_cols[2].slider(
                    "Size",
                    min_value=0.5,
                    max_value=3.0,
                    value=current_group_scale,
                    step=0.1,
                    key=f"group_box_scale_{g}",
                    label_visibility="collapsed"
                )
                st.session_state['proc_group_coordinates'][g]['box_scale'] = float(new_group_scale)
                
                # Place button for the group/process
                group_place_active = (st.session_state['placement_mode'] and st.session_state.get('placing_process_idx') == f"group_{g}")
                if not group_place_active:
                    if gh_cols[3].button("Place", key=f"place_group_{g}"):
                        st.session_state['placement_mode'] = True
                        st.session_state['measure_mode'] = False
                        st.session_state['placing_process_idx'] = f"group_{g}"
                        group_name = st.session_state['proc_group_names'][g]
                        st.session_state['ui_status_msg'] = f"Click on map to place: {group_name}"
                        st.rerun()
                else:
                    if gh_cols[3].button("Done", key=f"done_place_group_{g}"):
                        st.session_state['placement_mode'] = False
                        st.session_state['placing_process_idx'] = None
                        st.session_state['ui_status_msg'] = "Placement mode disabled"
                        st.rerun()
                
                gh_cols[4].markdown(f"**{len(g_list)}**")
                pending_group = st.session_state.get('group_delete_pending')
                with gh_cols[5]:
                    if pending_group == g:
                        st.write("Sure?")
                        if st.button("✅", key=f"confirm_del_group_{g}"):
                            # Delete all processes in group (highest index first)
                            for pi in sorted(g_list, reverse=True):
                                delete_process(st.session_state, pi)
                                _reindex_groups_after_delete(pi)
                            # Remove group metadata
                            st.session_state['proc_groups'].pop(g)
                            st.session_state['proc_group_names'].pop(g)
                            st.session_state['proc_group_expanded'].pop(g)
                            st.session_state['proc_group_info_expanded'].pop(g)
                            st.session_state['group_delete_pending'] = None
                            st.session_state['ui_status_msg'] = "Group deleted"
                            st.rerun()
                        if st.button("❌", key=f"cancel_del_group_{g}"):
                            st.session_state['group_delete_pending'] = None
                    else:
                        if st.button("✕", key=f"del_group_{g}"):
                            st.session_state['group_delete_pending'] = g
                            st.rerun()

                if not st.session_state['proc_group_expanded'][g]:
                    # Bottom separator for collapsed group
                    st.markdown("<div style='height:2px; background:#888888; opacity:0.7; margin:6px 0 4px;'></div>", unsafe_allow_html=True)
                    continue

                # Add collapsible information section for the main process (group level)
                info_header_cols = st.columns([0.05, 0.95])
                info_toggle_label = "▾" if st.session_state['proc_group_info_expanded'][g] else "▸"
                if info_header_cols[0].button(info_toggle_label, key=f"info_toggle_{g}"):
                    st.session_state['proc_group_info_expanded'][g] = not st.session_state['proc_group_info_expanded'][g]
                    st.rerun()
                info_header_cols[1].markdown("**Information**")
                
                if st.session_state['proc_group_info_expanded'][g]:
                    info_row1_cols = st.columns([1, 1, 1])
                    
                    # Initialize process coordinates and data if not exists
                    if 'proc_group_coordinates' not in st.session_state:
                        st.session_state['proc_group_coordinates'] = {}
                    if g not in st.session_state['proc_group_coordinates']:
                        st.session_state['proc_group_coordinates'][g] = {'lat': '', 'lon': '', 'hours': ''}
                    
                    current_coords = st.session_state['proc_group_coordinates'][g]
                    new_lat = info_row1_cols[0].text_input("Latitude", value=str(current_coords.get('lat', '') or ''), key=f"group_lat_{g}")
                    new_lon = info_row1_cols[1].text_input("Longitude", value=str(current_coords.get('lon', '') or ''), key=f"group_lon_{g}")
                    new_hours = info_row1_cols[2].text_input("Hours", value=str(current_coords.get('hours', '') or ''), key=f"group_hours_{g}")
                    
                    # Update coordinates and hours in session state
                    st.session_state['proc_group_coordinates'][g]['lat'] = new_lat if new_lat.strip() else ''
                    st.session_state['proc_group_coordinates'][g]['lon'] = new_lon if new_lon.strip() else ''
                    st.session_state['proc_group_coordinates'][g]['hours'] = new_hours if new_hours.strip() else ''

                    # (Process size control moved to group header for compactness)
                    
                    # Process Model button and dialog
                    
                    model_btn_col, model_display_col = st.columns([0.3, 0.7])
                    if model_btn_col.button("Select Process Model", key=f"open_model_dialog_{g}"):
                        # Use dialog to show process model selector
                        @st.dialog("Process Model Selection")
                        def show_process_model_dialog():
                            st.markdown("### Select process category and type")
                            
                            # Level 1: Main category
                            level1_options = ["Select category..."] + list(PROCESS_MODEL_DICT.keys())
                            current_level1 = st.session_state['proc_group_model'][g].get('level1')
                            level1_index = level1_options.index(current_level1) if current_level1 in level1_options else 0
                            
                            selected_level1 = st.selectbox(
                                "Category",
                                options=level1_options,
                                index=level1_index,
                                key=f"dialog_model_level1_{g}"
                            )
                            
                            if selected_level1 != "Select category...":
                                st.session_state['proc_group_model'][g]['level1'] = selected_level1
                                
                                # Level 2: Subcategory
                                level2_options = ["Select type..."] + list(PROCESS_MODEL_DICT[selected_level1].keys())
                                current_level2 = st.session_state['proc_group_model'][g].get('level2')
                                if current_level2 and current_level2 not in level2_options:
                                    st.session_state['proc_group_model'][g]['level2'] = None
                                    current_level2 = None
                                level2_index = level2_options.index(current_level2) if current_level2 in level2_options else 0
                                
                                selected_level2 = st.selectbox(
                                    "Type",
                                    options=level2_options,
                                    index=level2_index,
                                    key=f"dialog_model_level2_{g}"
                                )
                                
                                if selected_level2 != "Select type...":
                                    st.session_state['proc_group_model'][g]['level2'] = selected_level2
                                else:
                                    st.session_state['proc_group_model'][g]['level2'] = None
                            else:
                                st.session_state['proc_group_model'][g]['level1'] = None
                                st.session_state['proc_group_model'][g]['level2'] = None
                            
                            # Initialize parameter request state
                            if 'proc_group_params_requested' not in st.session_state:
                                st.session_state['proc_group_params_requested'] = {}
                            if g not in st.session_state['proc_group_params_requested']:
                                st.session_state['proc_group_params_requested'][g] = False
                            
                            if st.button("Request parameters") or st.session_state['proc_group_params_requested'][g]:
                                st.session_state['proc_group_params_requested'][g] = True
                                st.markdown("---")
                                st.markdown("### Process Parameters")
                                
                                # Initialize parameters storage
                                if 'proc_group_params' not in st.session_state:
                                    st.session_state['proc_group_params'] = {}
                                if g not in st.session_state['proc_group_params']:
                                    st.session_state['proc_group_params'][g] = {
                                        'tin': '', 'tout': '', 'time': '', 'cp': '',
                                        'mass_flow': None, 'thermal_power': None
                                    }
                                
                                params = st.session_state['proc_group_params'][g]
                                param_cols = st.columns([1, 1, 1, 1])
                                params['tin'] = param_cols[0].text_input("Tin (°C)", value=params.get('tin', ''), key=f"param_tin_g_{g}")
                                params['tout'] = param_cols[1].text_input("Tout (°C)", value=params.get('tout', ''), key=f"param_tout_g_{g}")
                                params['time'] = param_cols[2].text_input("Time (h)", value=params.get('time', ''), key=f"param_time_g_{g}")
                                params['cp'] = param_cols[3].text_input("cp (kJ/kg·K)", value=params.get('cp', ''), key=f"param_cp_g_{g}")
                                
                                if st.button("Calculate energy demand", key=f"calc_g_{g}"):
                                    try:
                                        tin = float(params['tin'])
                                        tout = float(params['tout'])
                                        time = float(params['time'])
                                        cp = float(params['cp'])
                                        
                                        # Example calculation: Q = m * cp * ΔT
                                        # Assuming mass flow (m) = 1 kg/s for demonstration
                                        delta_t = abs(tout - tin)
                                        mass_flow = 1.0  # kg/s (placeholder)
                                        thermal_power = mass_flow * cp * delta_t  # kW
                                        
                                        params['mass_flow'] = mass_flow
                                        params['thermal_power'] = thermal_power
                                    except (ValueError, TypeError):
                                        st.error("Please enter valid numeric values for all parameters")
                                
                                # Display results if calculated
                                if params.get('mass_flow') is not None and params.get('thermal_power') is not None:
                                    st.success(f"**Mass Flow:** {params['mass_flow']:.2f} kg/s")
                                    st.success(f"**Thermal Power:** {params['thermal_power']:.2f} kW")
                                
                                if st.button("Import energy values", key=f"done_g_{g}"):
                                    st.rerun()
                        
                        show_process_model_dialog()
                    
                    # Display current selection
                    current_model = st.session_state['proc_group_model'][g]
                    if current_model.get('level2'):
                        model_display_col.caption(f"Model: {current_model['level1']} → {current_model['level2']}")
                    elif current_model.get('level1'):
                        model_display_col.caption(f"Model: {current_model['level1']}")
                    else:
                        model_display_col.caption("No model selected")
                    
                    # Next Processes dropdown for the group
                    if 'proc_group_next' not in st.session_state:
                        st.session_state['proc_group_next'] = {}
                    if g not in st.session_state['proc_group_next']:
                        st.session_state['proc_group_next'][g] = ''
                    
                    # Build option list of other process group names
                    all_group_names = st.session_state.get('proc_group_names', [])
                    if len(all_group_names) <= 1:
                        st.caption("To connect processes, add more than one process group")
                        st.session_state['proc_group_next'][g] = ''
                    else:
                        # Create options excluding current group
                        options = [name for idx, name in enumerate(all_group_names) if idx != g]
                        
                        # Current selection
                        current_next = st.session_state['proc_group_next'][g]
                        default_selection = [current_next] if current_next and current_next in options else []
                        
                        selected = st.multiselect("Next Processes", options=options, default=default_selection, key=f"group_next_multi_{g}")
                        # Store as comma-separated names  
                        st.session_state['proc_group_next'][g] = ", ".join(selected) if selected else ''
                
                # Initialize map_expanded state for this process group (controls subprocess overlay on map)
                if 'process_subprocess_map_expanded' not in st.session_state:
                    st.session_state['process_subprocess_map_expanded'] = {}
                if g not in st.session_state['process_subprocess_map_expanded']:
                    st.session_state['process_subprocess_map_expanded'][g] = False
                
                # Subprocesses section with Map toggle + Count + Add subprocess button
                subprocess_count = len(g_list)
                subprocess_map_exp = st.session_state['process_subprocess_map_expanded'].get(g, False)
                
                sub_header_cols = st.columns([0.40, 0.12, 0.08, 0.20, 0.20])
                sub_header_cols[0].markdown("**Subprocesses:**")
                
                # Map toggle button
                subprocess_map_toggle_label = "🔽 Hide" if subprocess_map_exp else "▶️ Map"
                if sub_header_cols[1].button(subprocess_map_toggle_label, key=f"map_toggle_subprocess_{g}", help="Show/hide subprocesses on map"):
                    st.session_state['process_subprocess_map_expanded'][g] = not subprocess_map_exp
                    st.rerun()
                
                # Count
                sub_header_cols[2].markdown(f"**{subprocess_count}**")
                
                # Status indicator
                if subprocess_map_exp:
                    sub_header_cols[3].caption("🗺️ On map")
                
                # Add button
                if sub_header_cols[4].button("➕ Add", key=f"add_proc_group_{g}", help="Add subprocess"):
                    add_process(st.session_state)
                    new_idx = len(st.session_state['processes']) - 1
                    g_list.append(new_idx)
                    # Ensure proc_expanded has entry and keep it collapsed
                    if len(st.session_state['proc_expanded']) <= new_idx:
                        st.session_state['proc_expanded'].append(False)
                    else:
                        st.session_state['proc_expanded'][new_idx] = False
                    st.session_state['ui_status_msg'] = f"Added subprocess to {st.session_state['proc_group_names'][g]}"
                    st.rerun()
                
                for local_idx, i in enumerate(g_list):
                    p = st.session_state['processes'][i]
                    
                    # Initialize all subprocess-specific session state variables BEFORE any UI elements
                    # Process Model initialization
                    if 'proc_model' not in st.session_state:
                        st.session_state['proc_model'] = {}
                    if i not in st.session_state['proc_model']:
                        st.session_state['proc_model'][i] = {'level1': None, 'level2': None}
                    
                    # Process Model parameters initialization for subprocesses
                    if 'proc_params' not in st.session_state:
                        st.session_state['proc_params'] = {}
                    if i not in st.session_state['proc_params']:
                        st.session_state['proc_params'][i] = {
                            'tin': '', 'tout': '', 'time': '', 'cp': '',
                            'mass_flow': None, 'thermal_power': None
                        }
                    if 'proc_params_requested' not in st.session_state:
                        st.session_state['proc_params_requested'] = {}
                    if i not in st.session_state['proc_params_requested']:
                        st.session_state['proc_params_requested'][i] = False
                    
                    # Per-subprocess header (toggle | name | size | place | delete)
                    header_cols = st.columns([0.06, 0.54, 0.14, 0.16, 0.10])
                    toggle_label = "▾" if st.session_state['proc_expanded'][i] else "▸"
                    if header_cols[0].button(toggle_label, key=f"proc_toggle_{i}"):
                        st.session_state['proc_expanded'][i] = not st.session_state['proc_expanded'][i]
                        st.rerun()
                    # Default auto-name if empty
                    if not p.get('name'):
                        p['name'] = f"Subprocess {i+1}"
                    p['name'] = header_cols[1].text_input(
                        "Subprocess name",
                        value=p.get('name',''),
                        key=f"p_name_{i}",
                        label_visibility="collapsed",
                        placeholder=f"Subprocess {i+1}"
                    )
                    # Size slider (scale factor for box rendering)
                    if 'box_scale' not in p or p.get('box_scale') in (None, ''):
                        p['box_scale'] = 1.0
                    p['box_scale'] = header_cols[2].slider(
                        "Size",
                        min_value=0.5,
                        max_value=3.0,
                        value=float(p.get('box_scale',1.0)),
                        step=0.1,
                        key=f"p_box_scale_{i}",
                        label_visibility="collapsed"
                    )
                    place_active = (st.session_state['placement_mode'] and st.session_state.get('placing_process_idx') == i)
                    if not place_active:
                        if header_cols[3].button("Place", key=f"place_{i}"):
                            st.session_state['placement_mode'] = True
                            st.session_state['measure_mode'] = False
                            st.session_state['placing_process_idx'] = i
                            st.session_state['ui_status_msg'] = f"Click on map to place: {p.get('name') or f'Subprocess {i+1}'}"
                            st.rerun()
                    else:
                        if header_cols[3].button("Done", key=f"done_place_{i}"):
                            st.session_state['placement_mode'] = False
                            st.session_state['placing_process_idx'] = None
                            st.session_state['ui_status_msg'] = "Placement mode disabled"
                            st.rerun()
                    pending = st.session_state.get('proc_delete_pending')
                    if pending == i:
                        with header_cols[4]:
                            st.write("Sure?")
                            if st.button("✅", key=f"confirm_del_{i}"):
                                delete_process(st.session_state, i)
                                _reindex_groups_after_delete(i)
                                st.session_state['proc_delete_pending'] = None
                                st.rerun()
                            if st.button("❌", key=f"cancel_del_{i}"):
                                st.session_state['proc_delete_pending'] = None
                    else:
                        if header_cols[4].button("✕", key=f"del_proc_{i}"):
                            st.session_state['proc_delete_pending'] = i
                            st.rerun()

                    if st.session_state['proc_expanded'][i]:
                        # Divider: Relationships Section
                        st.markdown("<div style='height:2px; background:linear-gradient(to right, #3498db, transparent); margin:12px 0 8px 0;'></div>", unsafe_allow_html=True)
                        st.markdown("**Relationships**")
                        
                        # Multi-select for next processes (exclude self)
                        all_procs = st.session_state['processes']
                        if len(all_procs) <= 1:
                            st.caption("To connect processes, add more than one")
                            p['next'] = ''
                        else:
                            # Build option list of other subprocess names
                            options = []
                            for j, pj in enumerate(all_procs):
                                if j == i:
                                    continue
                                nm = pj.get('name') or f"Subprocess {j+1}"
                                options.append(nm)
                            # Current selections parsed from stored string
                            current_tokens = [t.strip() for t in (p.get('next','') or '').replace(';',',').replace('|',',').split(',') if t.strip()]
                            # Keep only those present in options
                            preselect = [t for t in current_tokens if t in options]
                            selected = st.multiselect("Next processes", options=options, default=preselect, key=f"p_next_multi_{i}")
                            # Store as comma-separated names
                            p['next'] = ", ".join(selected)

                        # Initialize extra_info dict if not exists
                        if 'extra_info' not in p:
                            p['extra_info'] = {}
                        
                        # Process Model button and dialog for subprocess (in same area as Relationships)
                        model_btn_col, model_display_col = st.columns([0.3, 0.7])
                        if model_btn_col.button("Select Process Model", key=f"open_model_dialog_sub_{i}"):
                            # Use dialog to show process model selector
                            @st.dialog("Process Model Selection")
                            def show_subprocess_model_dialog():
                                st.markdown("### Select process category and type")
                                
                                # Level 1: Main category
                                level1_options = ["Select category..."] + list(PROCESS_MODEL_DICT.keys())
                                current_level1 = st.session_state['proc_model'][i].get('level1')
                                level1_index = level1_options.index(current_level1) if current_level1 in level1_options else 0
                                
                                selected_level1 = st.selectbox(
                                    "Category",
                                    options=level1_options,
                                    index=level1_index,
                                    key=f"dialog_sub_model_level1_{i}"
                                )
                                
                                if selected_level1 != "Select category...":
                                    st.session_state['proc_model'][i]['level1'] = selected_level1
                                    
                                    # Level 2: Subcategory
                                    level2_options = ["Select type..."] + list(PROCESS_MODEL_DICT[selected_level1].keys())
                                    current_level2 = st.session_state['proc_model'][i].get('level2')
                                    if current_level2 and current_level2 not in level2_options:
                                        st.session_state['proc_model'][i]['level2'] = None
                                        current_level2 = None
                                    level2_index = level2_options.index(current_level2) if current_level2 in level2_options else 0
                                    
                                    selected_level2 = st.selectbox(
                                        "Type",
                                        options=level2_options,
                                        index=level2_index,
                                        key=f"dialog_sub_model_level2_{i}"
                                    )
                                    
                                    if selected_level2 != "Select type...":
                                        st.session_state['proc_model'][i]['level2'] = selected_level2
                                    else:
                                        st.session_state['proc_model'][i]['level2'] = None
                                else:
                                    st.session_state['proc_model'][i]['level1'] = None
                                    st.session_state['proc_model'][i]['level2'] = None
                                
                                # Initialize parameter request state
                                if st.button("Request parameters") or st.session_state['proc_params_requested'][i]:
                                    st.session_state['proc_params_requested'][i] = True
                                    st.markdown("---")
                                    st.markdown("### Process Parameters")
                                    
                                    params = st.session_state['proc_params'][i]
                                    param_cols = st.columns([1, 1, 1, 1])
                                    params['tin'] = param_cols[0].text_input("Tin (°C)", value=params.get('tin', ''), key=f"param_tin_sub_{i}")
                                    params['tout'] = param_cols[1].text_input("Tout (°C)", value=params.get('tout', ''), key=f"param_tout_sub_{i}")
                                    params['time'] = param_cols[2].text_input("Time (h)", value=params.get('time', ''), key=f"param_time_sub_{i}")
                                    params['cp'] = param_cols[3].text_input("cp (kJ/kg·K)", value=params.get('cp', ''), key=f"param_cp_sub_{i}")
                                    
                                    if st.button("Calculate energy demand", key=f"calc_sub_{i}"):
                                        try:
                                            tin = float(params['tin'])
                                            tout = float(params['tout'])
                                            time = float(params['time'])
                                            cp = float(params['cp'])
                                            
                                            # Example calculation: Q = m * cp * ΔT
                                            # Assuming mass flow (m) = 1 kg/s for demonstration
                                            delta_t = abs(tout - tin)
                                            mass_flow = 1.0  # kg/s (placeholder)
                                            thermal_power = mass_flow * cp * delta_t  # kW
                                            
                                            params['mass_flow'] = mass_flow
                                            params['thermal_power'] = thermal_power
                                        except (ValueError, TypeError):
                                            st.error("Please enter valid numeric values for all parameters")
                                    
                                    # Display results if calculated
                                    if params.get('mass_flow') is not None and params.get('thermal_power') is not None:
                                        st.success(f"**Mass Flow:** {params['mass_flow']:.2f} kg/s")
                                        st.success(f"**Thermal Power:** {params['thermal_power']:.2f} kW")
                                    
                                    if st.button("Import energy values", key=f"done_sub_{i}"):
                                        st.rerun()
                            
                            show_subprocess_model_dialog()
                        
                        # Display current selection (only if model is selected)
                        current_model = st.session_state['proc_model'][i]
                        if current_model.get('level2'):
                            model_display_col.caption(f"Model: {current_model['level1']} → {current_model['level2']}")
                        elif current_model.get('level1'):
                            model_display_col.caption(f"Model: {current_model['level1']}")

                        # Divider: Streams Section
                        st.markdown("<div style='height:2px; background:linear-gradient(to right, #e74c3c, transparent); margin:12px 0 8px 0;'></div>", unsafe_allow_html=True)
                        
                        # Streams section with persistent add button
                        streams = p.get('streams', [])
                        header_c1, header_c2, header_c3 = st.columns([2,4,1])
                        header_c1.markdown("**Streams**")
                        if header_c3.button("➕", key=f"btn_add_stream_header_{i}"):
                            add_stream_to_process(st.session_state, i)
                            st.rerun()
                        if not streams:
                            st.caption("No streams yet. Use ➕ to add one.")
                        for si, s in enumerate(streams):
                            # Ensure stream has name and type fields
                            if 'name' not in s:
                                s['name'] = f"Stream {si+1}"
                            if 'type' not in s:
                                s['type'] = "product"
                            
                            # Stream header row: Name | Type | Delete
                            stream_header_cols = st.columns([1.5, 1, 0.5])
                            s['name'] = stream_header_cols[0].text_input(
                                f"Stream {si+1} name", 
                                value=s.get('name', f"Stream {si+1}"), 
                                key=f"s_name_{i}_{si}",
                                label_visibility="collapsed",
                                placeholder=f"Stream {si+1}"
                            )
                            stream_types = ["product", "steam", "air", "water"]
                            current_type = s.get('type', 'product')
                            if current_type not in stream_types:
                                current_type = 'product'
                            s['type'] = stream_header_cols[1].selectbox(
                                "Type",
                                options=stream_types,
                                index=stream_types.index(current_type),
                                key=f"s_type_{i}_{si}",
                                label_visibility="collapsed"
                            )
                            if stream_header_cols[2].button("✕", key=f"del_stream_{i}_{si}"):
                                delete_stream_from_process(st.session_state, i, si)
                                st.rerun()
                            
                            # All stream types use the same selection logic with different preselected defaults
                            display_options = ["Tout", "ṁ", "cp", "CP"]
                            
                            # Define default preselected variables based on stream type
                            stream_type = s.get('type', 'product')
                            if stream_type == 'product':
                                default_display = ["Tout", "ṁ", "cp"]
                            elif stream_type == 'steam':
                                default_display = ["ṁ"]
                            else:  # air, water, etc.
                                default_display = ["ṁ"]
                            
                            # Initialize display_vars in session state if not present
                            display_key = f"s_display_vars_{i}_{si}"
                            if display_key not in st.session_state:
                                current_display = s.get('display_vars', None)
                                if current_display is None:
                                    current_display = default_display
                                current_display = [v for v in current_display if v in display_options]
                                st.session_state[display_key] = current_display
                            
                            selected_display = st.multiselect(
                                "Variables",
                                options=display_options,
                                key=display_key,
                                help="Select variables to enter (Tin is always shown)"
                            )
                            s['display_vars'] = selected_display
                            
                            # Build list of properties to show: Tin always + selected ones
                            props_to_show = ["Tin"] + selected_display
                            n_props = len(props_to_show)
                            
                            if n_props > 0:
                                prop_cols = st.columns(n_props)
                                for pi, prop_name in enumerate(props_to_show):
                                    with prop_cols[pi]:
                                        st.caption(prop_name)
                                        current_val = s.get('stream_values', {}).get(prop_name, '')
                                        
                                        new_val = st.text_input(
                                            prop_name,
                                            value=str(current_val),
                                            key=f"s_sval_{prop_name}_{i}_{si}",
                                            label_visibility="collapsed"
                                        )
                                        
                                        # Store in stream_values dict
                                        if 'stream_values' not in s:
                                            s['stream_values'] = {}
                                        s['stream_values'][prop_name] = new_val
                            
                            # Update legacy fields for compatibility
                            sv = s.get('stream_values', {})
                            s['temp_in'] = sv.get('Tin', '')
                            s['temp_out'] = sv.get('Tout', '')
                            s['mdot'] = sv.get('ṁ', '')
                            s['cp'] = sv.get('cp', '')
                            
                            # Also update properties/values structure for drawing
                            s['properties'] = {'prop1': 'Tin'}
                            s['values'] = {'val1': sv.get('Tin', '')}
                            idx = 2
                            for var in selected_display:
                                s['properties'][f'prop{idx}'] = var
                                s['values'][f'val{idx}'] = sv.get(var, '')
                                idx += 1
                            
                            # Divider between streams
                            if si < len(streams) - 1:
                                st.markdown("<div style='height:1px; background:#ddd; margin:8px 0;'></div>", unsafe_allow_html=True)
                        
                        # Divider: Notes Section
                        st.markdown("<div style='height:2px; background:linear-gradient(to right, #f39c12, transparent); margin:12px 0 8px 0;'></div>", unsafe_allow_html=True)
                        st.markdown("**Notes**")
                        
                        # Custom notes field (full width)
                        p['extra_info']['notes'] = st.text_area("Notes", value=p.get('extra_info', {}).get('notes', ''), key=f"p_notes_{i}", height=80, label_visibility="collapsed")
                        
                        # =====================================================
                        # SUB-SUBPROCESSES SECTION - Recursive children
                        # =====================================================
                        # Divider: Sub-subprocesses Section
                        st.markdown("<div style='height:2px; background:linear-gradient(to right, #27ae60, transparent); margin:12px 0 8px 0;'></div>", unsafe_allow_html=True)
                        
                        # Initialize children list if not exists
                        if 'children' not in p:
                            p['children'] = []
                        
                        # Initialize map_expanded state for this subprocess (controls overlay on map)
                        if 'subprocess_map_expanded' not in st.session_state:
                            st.session_state['subprocess_map_expanded'] = {}
                        if i not in st.session_state['subprocess_map_expanded']:
                            st.session_state['subprocess_map_expanded'][i] = False
                        
                        # Sub-subprocesses header with Map toggle + Count + Add button
                        child_count = len(p.get('children', []))
                        map_expanded = st.session_state['subprocess_map_expanded'].get(i, False)
                        
                        header_cols = st.columns([0.35, 0.12, 0.08, 0.20, 0.25])
                        header_cols[0].caption("Sub-subprocesses:")
                        
                        # Map toggle button (smaller)
                        map_toggle_label = "Hide" if map_expanded else "Map"
                        if header_cols[1].button(map_toggle_label, key=f"map_toggle_subsub_{i}", help="Show/hide sub-subprocesses on map"):
                            st.session_state['subprocess_map_expanded'][i] = not map_expanded
                            st.rerun()
                        
                        # Count
                        header_cols[2].caption(f"{child_count}")
                        
                        # Status indicator
                        if map_expanded:
                            header_cols[3].caption("On map")
                        
                        # Add button (smaller)
                        if header_cols[4].button("+ Add", key=f"add_subsub_{i}", help="Add sub-subprocess"):
                            add_child_to_node(p, f"Sub-subprocess {child_count + 1}")
                            st.rerun()
                        
                        # Render sub-subprocesses (final level - no deeper)
                        if p.get('children'):
                            render_subsubprocesses(st, p, i, process_model_dict=PROCESS_MODEL_DICT)
                        
                    if local_idx < len(g_list) - 1:
                        # Thicker separator between subprocesses
                        st.markdown("<div style='height:3px; background:linear-gradient(to right, #2c3e50, #95a5a6, transparent); margin:15px 0;'></div>", unsafe_allow_html=True)
                # Bottom separator after expanded group
                st.markdown("<div style='height:4px; background:#34495e; margin:12px 0 4px; border-radius:2px;'></div>", unsafe_allow_html=True)
        else:
            st.info("No groups yet. Use 'Add a process' to start.")
    else:
        # Provide a summary of existing processes while selecting map
        if st.session_state['processes']:
            st.caption(f"Processes: {len(st.session_state['processes'])} (edit in Analyze mode)")
        else:
            st.caption("Add processes in Analyze mode after locking a map view.")

with right:
    # mode already selected on left
    if mode == "Select Map":
        # Address & base selection row
        addr_col, btn_col, info_col, base_col = st.columns([5,1,2,2])
        address = addr_col.text_input("Search address", key="address_input")
        if btn_col.button("Search", key="search_button") and address:
            url = f"https://nominatim.openstreetmap.org/search?q={address}&format=json&limit=1"
            try:
                resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                if data:
                    st.session_state['selector_center'] = [float(data[0]['lat']), float(data[0]['lon'])]
                    st.session_state['selector_zoom'] = 16
                    # Clear cached maps so they regenerate with new center
                    keys_to_remove = [k for k in st.session_state.keys() if k.startswith('cached_map_')]
                    for key in keys_to_remove:
                        del st.session_state[key]
                else:
                    st.warning("Address not found.")
            except requests.exceptions.Timeout:
                st.error("Address search timed out.")
            except requests.exceptions.RequestException as req_err:
                st.error(f"Search failed: {req_err}")
        info_col.caption("When ready, press 'Lock map and analyze'.")
        # Base layer selector placed in same top row
        base_col.markdown("<div style='font-size:12px; font-weight:600; margin-bottom:2px;'>Base</div>", unsafe_allow_html=True)
        base_options = ["OpenStreetMap", "Positron", "Satellite", "Blank"]
        if st.session_state['current_base'] not in base_options:
            st.session_state['current_base'] = 'OpenStreetMap'
        _map_base = base_col.selectbox(
            label="Base layer",
            options=base_options,
            index=base_options.index(st.session_state['current_base']),
            key='map_base_selector',
            label_visibility='collapsed'
        )
        if _map_base != st.session_state['current_base']:
            st.session_state['current_base'] = _map_base
        st.markdown("""
<style>
/* Compact selectboxes and all form elements */
div[data-testid=\"stVerticalBlock\"] > div div[data-baseweb=\"select\"] {min-height:28px !important;}
div[data-testid=\"stVerticalBlock\"] > div div[data-baseweb=\"select\"] * {font-size:10px !important;}
div[data-testid=\"stVerticalBlock\"] > div div[data-baseweb=\"select\"] div[role=\"combobox\"] {padding:1px 4px !important;}
/* Make all inputs more compact */
.stTextInput > div > div > input {height: 28px !important;}
.stNumberInput > div > div > input {height: 28px !important;}
.stSlider > div > div > div {height: 20px !important;}
</style>
""", unsafe_allow_html=True)
        selected_base = st.session_state.get('current_base', 'OpenStreetMap')
        # Check if we need to recreate the map
        import hashlib
        processes_hash = hashlib.md5(str(st.session_state.get('processes', [])).encode()).hexdigest()
        map_state_hash = f"{selected_base}_{processes_hash}"
        need_recreate = (
            'map_state_hash' not in st.session_state or
            st.session_state['map_state_hash'] != map_state_hash
        )
        if need_recreate:
            st.session_state['map_state_hash'] = map_state_hash
        # Single wide map container below controls
        map_col = st.container()
        with map_col:
            # Get current center and zoom from session state
            current_center = st.session_state.get('selector_center', [51.70814085564164, 8.772155163087213])
            current_zoom = st.session_state.get('selector_zoom', 17.5)
            
            # Build map with only the chosen base layer
            if selected_base == 'Blank':
                fmap = folium.Map(location=current_center, zoom_start=current_zoom, tiles=None)
                # Add a transparent 1x1 tile layer colored via CSS overlay not natively supported; skip tiles, map background will be default.
                # We'll inject simple CSS to set map background to very light gray.
                st.markdown("""
<style>
div.leaflet-container {background: #f2f2f3 !important;}
</style>
""", unsafe_allow_html=True)
            elif selected_base == 'Satellite':
                fmap = folium.Map(location=current_center, zoom_start=current_zoom, tiles=None)
                folium.TileLayer(
                    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                    attr='Esri WorldImagery',
                    name='Satellite'
                ).add_to(fmap)
            elif selected_base == 'Positron':
                fmap = folium.Map(location=current_center, zoom_start=current_zoom, tiles='CartoDB positron')
            else:
                fmap = folium.Map(location=current_center, zoom_start=current_zoom, tiles='OpenStreetMap')
            # Feature groups for overlays
            process_fg = folium.FeatureGroup(name='Processes', show=True)
            connection_fg = folium.FeatureGroup(name='Connections', show=True)
            
            # Add subprocess markers (only when parent group is expanded)
            proc_groups = st.session_state.get('proc_groups', [])
            group_expanded = st.session_state.get('proc_group_expanded', [])
            
            # Create mapping of subprocess index to group index
            subprocess_to_group_folium = {}
            for group_idx, group_subprocess_list in enumerate(proc_groups):
                for subprocess_idx in group_subprocess_list:
                    subprocess_to_group_folium[subprocess_idx] = group_idx
            
            for idx, p in enumerate(st.session_state['processes']):
                lat = p.get('lat'); lon = p.get('lon')
                if lat not in (None, "") and lon not in (None, ""):
                    # Check if this subprocess's parent group is expanded
                    parent_group_idx = subprocess_to_group_folium.get(idx)
                    if parent_group_idx is not None:
                        # Only show subprocess if parent group is expanded
                        if (parent_group_idx >= len(group_expanded) or 
                            not group_expanded[parent_group_idx]):
                            continue  # Skip this subprocess - parent group is collapsed
                    
                    try:
                        label = p.get('name') or f"P{idx+1}"
                        html = f"""<div style='background:#e0f2ff;border:2px solid #1769aa;padding:5px 10px;font-size:15px;font-weight:600;color:#0a3555;border-radius:6px;white-space:nowrap;box-shadow:0 1px 3px rgba(0,0,0,0.35);'>📦 {label}</div>"""
                        folium.Marker(
                            [float(lat), float(lon)],
                            tooltip=label,
                            popup=f"<b>{label}</b><br>Next: {p.get('next','')}",
                            icon=folium.DivIcon(html=html)
                        ).add_to(process_fg)
                    except (ValueError, TypeError):
                        pass
            
            # Add main process (group) markers (only when collapsed)
            group_coords = st.session_state.get('proc_group_coordinates', {})
            group_names = st.session_state.get('proc_group_names', [])
            for group_idx, coords_data in group_coords.items():
                # Convert group_idx to int if it's a string (happens after JSON load)
                group_idx = int(group_idx) if isinstance(group_idx, str) else group_idx
                if group_idx < len(group_names):
                    # Only show main process marker when group is collapsed
                    if (group_idx < len(group_expanded) and group_expanded[group_idx]):
                        continue  # Skip - group is expanded
                        
                    lat = coords_data.get('lat')
                    lon = coords_data.get('lon')
                    if lat is not None and lon is not None:
                        try:
                            group_name = group_names[group_idx]
                            
                            # Build detailed popup with subprocess information
                            popup_html = f"<div style='min-width:250px;'><b style='font-size:16px;'>🏭 Process: {group_name}</b><br><br>"
                            
                            # Get all subprocesses in this group
                            group_subprocess_list = proc_groups[group_idx] if group_idx < len(proc_groups) else []
                            
                            if group_subprocess_list:
                                popup_html += f"<b>Subprocesses ({len(group_subprocess_list)}):</b><br>"
                                popup_html += "<div style='max-height:300px;overflow-y:auto;'>"
                                
                                for subprocess_idx in group_subprocess_list:
                                    if subprocess_idx < len(st.session_state['processes']):
                                        subprocess = st.session_state['processes'][subprocess_idx]
                                        subprocess_name = subprocess.get('name') or f"Subprocess {subprocess_idx+1}"
                                        
                                        popup_html += f"<div style='margin:8px 0;padding:6px;background:#f0f0f0;border-radius:4px;'>"
                                        popup_html += f"<b>📦 {subprocess_name}</b><br>"
                                        
                                        # Add location if available
                                        sub_lat = subprocess.get('lat')
                                        sub_lon = subprocess.get('lon')
                                        if sub_lat and sub_lon:
                                            popup_html += f"<small>Location: ({sub_lat}, {sub_lon})</small><br>"
                                        
                                        # Add next connection if available
                                        next_val = subprocess.get('next', '')
                                        if next_val:
                                            popup_html += f"<small>Next: {next_val}</small><br>"
                                        
                                        # Add streams information
                                        streams = subprocess.get('streams', [])
                                        if streams:
                                            popup_html += f"<small><b>Streams ({len(streams)}):</b></small><br>"
                                            for s_idx, stream in enumerate(streams):
                                                # Handle new stream structure with flexible properties
                                                stream_name = stream.get('name', f'Stream {s_idx+1}')
                                                stream_type = stream.get('type', 'product')
                                                
                                                # Check if using new structure (properties and values lists)
                                                properties = stream.get('properties', [])
                                                values = stream.get('values', [])
                                                
                                                if properties and values and len(properties) == len(values):
                                                    # New structure: display name, type, and property-value pairs
                                                    popup_html += f"<small>&nbsp;&nbsp;• {stream_name} ({stream_type}): "
                                                    prop_pairs = []
                                                    for prop, val in zip(properties, values):
                                                        if prop in ['Tin', 'Tout']:
                                                            prop_pairs.append(f"{prop}={val}°C")
                                                        elif prop == 'ṁ':
                                                            prop_pairs.append(f"ṁ={val}")
                                                        elif prop == 'cp':
                                                            prop_pairs.append(f"cp={val}")
                                                        else:
                                                            prop_pairs.append(f"{prop}={val}")
                                                    popup_html += ", ".join(prop_pairs)
                                                    popup_html += "</small><br>"
                                                else:
                                                    # Legacy structure: fallback to old fields
                                                    tin = stream.get('temp_in', '?')
                                                    tout = stream.get('temp_out', '?')
                                                    mdot = stream.get('mdot', '?')
                                                    cp = stream.get('cp', '?')
                                                    popup_html += f"<small>&nbsp;&nbsp;• {stream_name} ({stream_type}): Tin={tin}°C, Tout={tout}°C, ṁ={mdot}, cp={cp}</small><br>"
                                        
                                        popup_html += "</div>"
                                
                                popup_html += "</div>"
                            else:
                                popup_html += "<i>No subprocesses yet</i><br>"
                            
                            popup_html += "</div>"
                            
                            html = f"""<div style='background:#c8f7c5;border:2px solid #228b22;padding:6px 12px;font-size:16px;font-weight:700;color:#006400;border-radius:6px;white-space:nowrap;box-shadow:0 2px 4px rgba(0,0,0,0.4);'>🏭 {group_name}</div>"""
                            folium.Marker(
                                [float(lat), float(lon)],
                                tooltip=group_name,
                                popup=folium.Popup(popup_html, max_width=400),
                                icon=folium.DivIcon(html=html)
                            ).add_to(process_fg)
                        except (ValueError, TypeError):
                            pass
            name_lookup = {}
            coord_by_idx = {}
            for idx, p in enumerate(st.session_state['processes']):
                lat = p.get('lat'); lon = p.get('lon')
                try:
                    if lat not in (None, "", "None") and lon not in (None, "", "None"):
                        lat_f = float(lat); lon_f = float(lon)
                        coord_by_idx[idx] = (lat_f, lon_f)
                        nm = (p.get('name') or f"P{idx+1}").strip().lower()
                        if nm:
                            name_lookup.setdefault(nm, []).append(idx)
                except (ValueError, TypeError):
                    continue
            def _parse_targets(raw_targets):
                if not raw_targets:
                    return []
                tokens = []
                for raw_piece in raw_targets.replace(';', ',').replace('|', ',').split(','):
                    tkn = raw_piece.strip()
                    if tkn:
                        tokens.append(tkn)
                return tokens
            for src_idx, p in enumerate(st.session_state['processes']):
                if src_idx not in coord_by_idx:
                    continue
                raw_next = p.get('next', '') or ''
                for next_token in _parse_targets(raw_next):
                    tgt_indices = []
                    if next_token.isdigit():
                        val = int(next_token) - 1
                        if val in coord_by_idx:
                            tgt_indices.append(val)
                    else:
                        lname_lookup = next_token.lower()
                        tgt_indices.extend(name_lookup.get(lname_lookup, []))
                    for tgt_idx in tgt_indices:
                        if tgt_idx == src_idx:
                            continue
                        lat1, lon1 = coord_by_idx[src_idx]
                        lat2, lon2 = coord_by_idx[tgt_idx]
                        try:
                            folium.PolyLine([(lat1, lon1), (lat2, lon2)], color='#000000', weight=3, opacity=0.9).add_to(connection_fg)
                            import math as _math_inner
                            dlat = lat2 - lat1; dlon = lon2 - lon1
                            if abs(dlat) + abs(dlon) > 0:
                                arrow_lat = lat2 - dlat * 0.12
                                arrow_lon = lon2 - dlon * 0.12
                                ang_deg = _math_inner.degrees(_math_inner.atan2(dlat, dlon))
                                arrow_html = f"""<div style='transform:translate(-50%,-50%) rotate({ang_deg}deg);font-size:22px;line-height:20px;color:#000000;font-weight:700;'>➤</div>"""
                                folium.Marker([arrow_lat, arrow_lon], icon=folium.DivIcon(html=arrow_html), tooltip="").add_to(connection_fg)
                        except (ValueError, TypeError):
                            pass
            process_fg.add_to(fmap)
            connection_fg.add_to(fmap)
            fmap_data = st_folium(
                fmap,
                key="selector_map_stable",
                width=MAP_WIDTH,
                height=MAP_HEIGHT,
                returned_objects=["center","zoom","last_clicked"],
                use_container_width=False
            )
            
            # Store current live map state for potential snapshot capture
            if fmap_data and fmap_data.get('center') and fmap_data.get('zoom'):
                st.session_state['current_map_center'] = [fmap_data['center']['lat'], fmap_data['center']['lng']]
                st.session_state['current_map_zoom'] = fmap_data['zoom']
            
            if (
                st.session_state.get('placing_process_idx') is not None and
                fmap_data and fmap_data.get('last_clicked')
            ):
                click = fmap_data['last_clicked']
                lat = click.get('lat'); lon = click.get('lng')
                if lat is not None and lon is not None:
                    try:
                        pidx = st.session_state['placing_process_idx']
                        st.session_state['processes'][pidx]['lat'] = round(float(lat), 6)
                        st.session_state['processes'][pidx]['lon'] = round(float(lon), 6)
                    except (ValueError, TypeError):
                        pass
            # Only save position changes, don't force update the map view
            # This prevents the oscillation by not feeding the map position back to itself
            pass  # Remove the position update logic entirely
            st.caption("Pan/zoom, then click 'Lock map and analyze' to capture a snapshot.")
    else:
        # Analysis mode
        if not st.session_state['map_locked']:
            st.warning("No locked snapshot yet. Switch to 'Select Map' and capture one.")
        else:
            # In Analyze mode on right column proceed with snapshot tools below
            # --- Top action/status bar ---
            top_c1, top_c2, top_c3, top_c4, top_c5, top_c6 = st.columns([3,1.5,1,1,1,2])
            with top_c1:
                # Decide dynamic status message (priority: placing > measuring > last action > default)
                placing_idx = st.session_state.get('placing_process_idx')
                placing_mode = st.session_state.get('placement_mode')
                measure_mode = st.session_state.get('measure_mode')
                measure_points = st.session_state.get('measure_points', [])
                dist_val = st.session_state.get('measure_distance_m')
                last_msg = st.session_state.get('ui_status_msg')
                if placing_mode and placing_idx is not None:
                    if isinstance(placing_idx, str) and placing_idx.startswith('group_'):
                        # Group placement
                        group_idx = int(placing_idx.split('_')[1])
                        if group_idx < len(st.session_state.get('proc_group_names', [])):
                            group_name = st.session_state['proc_group_names'][group_idx]
                            st.info(f"📍 Placing Process: {group_name} → Click anywhere on the map to place the process rectangle")
                    elif isinstance(placing_idx, str) and placing_idx.startswith('child_'):
                        # Child node placement (sub-subprocess, etc.)
                        child_node = st.session_state.get('placing_node_ref')
                        if child_node:
                            child_name = child_node.get('name', 'Child')
                            child_level = child_node.get('level', 2)
                            level_name = get_level_name(child_level)
                            st.info(f"📍 Placing {level_name}: {child_name} → Click anywhere on the map to place")
                    elif isinstance(placing_idx, int) and 0 <= placing_idx < len(st.session_state.get('processes', [])):
                        # Subprocess placement
                        pname = st.session_state['processes'][placing_idx].get('name') or f"Subprocess {placing_idx+1}"
                        st.info(f"📍 Placing: {pname} → Click anywhere on the map to place the process rectangle")
                elif measure_mode:
                    if dist_val is not None:
                        st.success(f"Distance: {dist_val:.2f} m ({dist_val/1000:.3f} km)")
                    else:
                        st.info(f"Measuring distance: select {2-len(measure_points)} more point(s)")
                elif last_msg:
                    st.success(last_msg)
                else:
                    st.info("Snapshot locked")
            with top_c2:
                if not st.session_state['measure_mode']:
                    if st.button("Measure Distance", key="measure_btn"):
                        st.session_state['measure_mode'] = True
                        st.session_state['placement_mode'] = False
                        st.session_state['measure_points'] = []
                        st.session_state['measure_distance_m'] = None
                else:
                    if st.button("Reset Measurement", key="reset_measure"):
                        st.session_state['measure_points'] = []
                        st.session_state['measure_distance_m'] = None
            with top_c3:
                # Export button
                if st.button("Export CSV", key="export_csv_btn", help="Export process data to CSV"):
                    csv_data = export_to_csv()
                    st.session_state['_export_csv_data'] = csv_data
                    st.session_state['_export_csv_ready'] = True
                
                if st.session_state.get('_export_csv_ready'):
                    st.download_button(
                        label="⬇️ Download CSV",
                        data=st.session_state['_export_csv_data'],
                        file_name=f"heat_integration_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key="export_csv_download"
                    )
            with top_c4:
                # Save button
                if st.button("Save State", key="save_state_btn", help="Save current state"):
                    state_json = save_app_state()
                    st.session_state['_save_state_data'] = state_json
                    st.session_state['_save_state_ready'] = True
                
                if st.session_state.get('_save_state_ready'):
                    st.download_button(
                        label="⬇️ Download JSON",
                        data=st.session_state['_save_state_data'],
                        file_name=f"heat_integration_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        key="save_state_download"
                    )
            with top_c5:
                # Check if we just loaded a file - show success message or buttons
                if 'state_just_loaded' in st.session_state and st.session_state['state_just_loaded']:
                    if st.button("Load Another", key="btn_load_another", help="Load another file"):
                        st.session_state['state_just_loaded'] = False
                        st.rerun()
                else:
                    # Load button - compact file uploader
                    st.markdown("""
                        <style>
                        [data-testid="stFileUploader"] {
                            width: max-content;
                            margin-top: -1px;
                        }
                        [data-testid="stFileUploader"] section {
                            padding: 0;
                        }
                        [data-testid="stFileUploader"] section > input + div {
                            display: none;
                        }
                        [data-testid="stFileUploader"] section + div {
                            display: none;
                        }
                        [data-testid="stFileUploader"] label {
                            display: none !important;
                        }
                        [data-testid="stFileUploader"] button {
                            width: 100%;
                        }
                        [data-testid="stFileUploader"] button span {
                            font-size: 0;
                        }
                        [data-testid="stFileUploader"] button span::before {
                            content: "Load saved file";
                            font-size: 14px;
                        }
                        </style>
                    """, unsafe_allow_html=True)
                    
                    uploaded_file = st.file_uploader("Load file", type=['json'], key="upload_state", label_visibility="collapsed")
                    
                    if uploaded_file is not None:
                        try:
                            # Read the file immediately to avoid session state issues
                            file_contents = uploaded_file.getvalue().decode('utf-8')
                            success, message = load_app_state(file_contents)
                            if success:
                                st.session_state['state_just_loaded'] = True
                                # Clear the file uploader to prevent MediaFileStorageError
                                if 'upload_state' in st.session_state:
                                    del st.session_state['upload_state']
                                st.rerun()
                            else:
                                st.error(message)
                        except Exception as e:
                            st.error(f"Error loading file: {str(e)}")
            with top_c6:
                analyze_options = ["OpenStreetMap", "Positron", "Satellite", "Blank"]
                if st.session_state['current_base'] not in analyze_options:
                    st.session_state['current_base'] = 'OpenStreetMap'
                _an_top_base = st.selectbox(
                    label="Base layer analyze",
                    options=analyze_options,
                    index=analyze_options.index(st.session_state['current_base']),
                    key='analyze_base_selector_top',
                    label_visibility='collapsed'
                )
                if _an_top_base != st.session_state['current_base']:
                    st.session_state['current_base'] = _an_top_base

            # Placement handled directly via per-subprocess Place/Done buttons in left panel

            # Determine which base layer to display in Analyze view
            # Always start from frozen analyze base layer, but allow user to switch (persist separately)
            # Active base for Analyze uses either a runtime override or the frozen at-lock base
            # Active base for Analyze: persistent independent selection
            active_base = st.session_state.get('current_base', st.session_state.get('analyze_base_layer','OpenStreetMap'))
            snapshots_dict = st.session_state.get('map_snapshots', {})
            if active_base == 'Blank':
                # Create a blank light gray image placeholder same size as last snapshot (or default size)
                base_img = Image.new('RGBA', (MAP_WIDTH, MAP_HEIGHT), (242,242,243,255))
                w, h = base_img.size
            else:
                chosen_bytes = snapshots_dict.get(active_base) or st.session_state.get('map_snapshot')
                base_img = Image.open(BytesIO(chosen_bytes)).convert("RGBA") if chosen_bytes else Image.new('RGBA',(MAP_WIDTH,MAP_HEIGHT),(242,242,243,255))
                w, h = base_img.size
            if base_img:

                # --- Overlay subprocess boxes & connecting arrows on snapshot ---
                draw = ImageDraw.Draw(base_img)
                # Smaller font for more compact display
                BOX_FONT_SIZE = 20  # Smaller but still sharp text
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", BOX_FONT_SIZE)
                except (OSError, IOError):
                    try:
                        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", BOX_FONT_SIZE)
                    except (OSError, IOError):
                        try:
                            font = ImageFont.truetype("DejaVuSans.ttf", BOX_FONT_SIZE)
                        except (OSError, IOError):
                            try:
                                font = ImageFont.load_default()
                            except (OSError, IOError):
                                font = None

                # First pass: compute positions & bounding boxes
                positioned = []  # list of dicts with: idx,label,center,box,(next_raw)
                name_index = {}  # map lowercase name -> list of indices (to handle duplicates)
                
                # Create mapping of subprocess index to group index
                subprocess_to_group = {}
                proc_groups = st.session_state.get('proc_groups', [])
                for group_idx, group_subprocess_list in enumerate(proc_groups):
                    for subprocess_idx in group_subprocess_list:
                        subprocess_to_group[subprocess_idx] = group_idx
                
                group_expanded = st.session_state.get('proc_group_expanded', [])
                
                # First pass: draw main process rectangles (when collapsed) BEHIND grey overlay
                group_coords = st.session_state.get('proc_group_coordinates', {})
                for group_idx, coords_data in group_coords.items():
                    # Convert group_idx to int if it's a string (happens after JSON load)
                    group_idx = int(group_idx) if isinstance(group_idx, str) else group_idx
                    if group_idx < len(st.session_state.get('proc_group_names', [])):
                        # Always show main process rectangle (green box) on the map
                        # It should remain visible regardless of UI expansion state
                            
                        lat = coords_data.get('lat')
                        lon = coords_data.get('lon')
                        if lat is not None and lon is not None:
                            try:
                                lat_f = float(lat)
                                lon_f = float(lon)
                                group_px, group_py = snapshot_lonlat_to_pixel(
                                    lon_f, lat_f,
                                    (st.session_state['map_center'][1], st.session_state['map_center'][0]),
                                    st.session_state['map_zoom'],
                                    w, h
                                )
                                # Skip if far outside snapshot bounds
                                if group_px < -50 or group_py < -20 or group_px > w + 50 or group_py > h + 20:
                                    continue
                                    
                                group_label = st.session_state['proc_group_names'][group_idx]
                                # Allow per-group size via proc_group_coordinates[group_idx]['box_scale']
                                try:
                                    scale = float(coords_data.get('box_scale', 1.5) or 1.5)
                                except (ValueError, TypeError):
                                    scale = 1.5
                                base_padding = 8
                                padding = int(base_padding * scale)
                                text_bbox = draw.textbbox((0, 0), group_label, font=font) if font else (0, 0, len(group_label) * 6, 10)
                                tw = (text_bbox[2] - text_bbox[0])
                                th = (text_bbox[3] - text_bbox[1])
                                box_w = int(tw * scale + padding * 2)
                                box_h = int(th * scale + padding * 2)
                                x0 = int(group_px - box_w / 2)
                                y0 = int(group_py - box_h / 2)
                                x1 = x0 + box_w
                                y1 = y0 + box_h
                                if x1 < 0 or y1 < 0 or x0 > w or y0 > h:
                                    continue
                                
                                # Draw main process rectangle with green styling
                                fill_color = (200, 255, 200, 245)  # Light green
                                border_color = (34, 139, 34, 255)  # Forest green
                                text_color = (0, 100, 0, 255)      # Dark green
                                border_width = 3
                                
                                # Draw filled rectangle
                                draw.rectangle([x0, y0, x1, y1], fill=fill_color, outline=border_color, width=border_width)
                                # Center text inside box
                                box_w = x1 - x0
                                box_h = y1 - y0
                                if font:
                                    bbox_lbl = draw.textbbox((0,0), group_label, font=font)
                                    t_w = bbox_lbl[2]-bbox_lbl[0]
                                    t_h = bbox_lbl[3]-bbox_lbl[1]
                                else:
                                    t_w = len(group_label)*6
                                    t_h = 10
                                ct_x = int(x0 + (box_w - t_w)/2)
                                ct_y = int(y0 + (box_h - t_h)/2)
                                if font:
                                    draw.text((ct_x, ct_y), group_label, fill=text_color, font=font)
                                else:
                                    draw.text((ct_x, ct_y), group_label, fill=text_color)
                                    
                            except (ValueError, TypeError):
                                continue
                
                # Second pass: draw large grey overlays for expanded processes ABOVE main processes
                # Now controlled by process_subprocess_map_expanded (the Map toggle button), not proc_group_expanded
                process_subprocess_map_exp = st.session_state.get('process_subprocess_map_expanded', {})
                for group_idx, coords_data in group_coords.items():
                    # Convert group_idx to int if it's a string (happens after JSON load)
                    group_idx = int(group_idx) if isinstance(group_idx, str) else group_idx
                    # Only draw overlay if the Map toggle is enabled for this process group
                    if process_subprocess_map_exp.get(group_idx, False):
                        try:
                            # Always use fixed size overlay centered in screen
                            # Fixed size: 90% width, 90% height
                            overlay_w = int(w * 0.9)
                            overlay_h = int(h * 0.9)
                            
                            # Always center in the middle of the screen
                            center_px = w // 2
                            center_py = h // 2
                            
                            overlay_x0 = int(center_px - overlay_w / 2)
                            overlay_y0 = int(center_py - overlay_h / 2)
                            overlay_x1 = overlay_x0 + overlay_w
                            overlay_y1 = overlay_y0 + overlay_h
                            
                            # Ensure overlay stays within map bounds with some padding
                            margin = 20
                            overlay_x0 = max(margin, overlay_x0)
                            overlay_y0 = max(margin, overlay_y0)
                            overlay_x1 = min(w - margin, overlay_x1)
                            overlay_y1 = min(h - margin, overlay_y1)
                            
                            # Draw very light grey semi-transparent overlay
                            draw.rectangle([overlay_x0, overlay_y0, overlay_x1, overlay_y1], 
                                         fill=(250, 250, 250, 40),  # Almost white with very low opacity
                                         outline=(245, 245, 245, 80), 
                                         width=1)
                                         
                            # Optional: Add a subtle label in the corner
                            if group_idx < len(st.session_state.get('proc_group_names', [])):
                                group_name = st.session_state['proc_group_names'][group_idx]
                                overlay_label = f"Process Area: {group_name}"
                                if font:
                                    label_bbox = draw.textbbox((0, 0), overlay_label, font=font)
                                    label_w = label_bbox[2] - label_bbox[0]
                                    label_h = label_bbox[3] - label_bbox[1]
                                else:
                                    label_w = len(overlay_label) * 6
                                    label_h = 10
                                
                                # Place label in top-left corner of overlay with padding
                                label_x = overlay_x0 + 15
                                label_y = overlay_y0 + 15
                                
                                # Very subtle background for label
                                draw.rectangle([label_x-5, label_y-3, label_x+label_w+5, label_y+label_h+3], 
                                             fill=(255, 255, 255, 120), 
                                             outline=(220, 220, 220, 100), 
                                             width=1)
                                
                                # Draw label text in subtle grey
                                if font:
                                    draw.text((label_x, label_y), overlay_label, fill=(40, 40, 40, 255), font=font)
                                else:
                                    draw.text((label_x, label_y), overlay_label, fill=(40, 40, 40, 255))
                                    
                        except (ValueError, TypeError):
                            continue
                
                # Third pass: draw subprocesses ABOVE grey overlay (only when Map toggle is enabled)
                for i, p in enumerate(st.session_state['processes']):
                    lat = p.get('lat'); lon = p.get('lon')
                    if lat in (None, "", "None") or lon in (None, "", "None"):
                        continue
                    
                    # Check if this subprocess's parent group has Map toggle enabled
                    parent_group_idx = subprocess_to_group.get(i)
                    if parent_group_idx is not None:
                        # Only show subprocess if parent group's Map toggle is ON
                        if not process_subprocess_map_exp.get(parent_group_idx, False):
                            continue  # Skip this subprocess - Map toggle is off
                    
                    try:
                        lat_f = float(lat); lon_f = float(lon)
                        proc_px, proc_py = snapshot_lonlat_to_pixel(
                            lon_f,
                            lat_f,
                            (st.session_state['map_center'][1], st.session_state['map_center'][0]),
                            st.session_state['map_zoom'],
                            w,
                            h
                        )
                        # Skip if far outside snapshot bounds (padding margin)
                        if proc_px < -50 or proc_py < -20 or proc_px > w + 50 or proc_py > h + 20:
                            continue
                        label = p.get('name') or f"P{i+1}"
                        scale = float(p.get('box_scale', 6.0) or 6.0)
                        base_padding = 18
                        padding = int(base_padding * scale)
                        text_bbox = draw.textbbox((0, 0), label, font=font) if font else (0, 0, len(label) * 6, 10)
                        tw = (text_bbox[2] - text_bbox[0])
                        th = (text_bbox[3] - text_bbox[1])
                        box_w = int(tw * scale + padding * 2)
                        box_h = int(th * scale + padding * 2)
                        x0 = int(proc_px - box_w / 2)
                        y0 = int(proc_py - box_h / 2)
                        x1 = x0 + box_w
                        y1 = y0 + box_h
                        if x1 < 0 or y1 < 0 or x0 > w or y0 > h:
                            continue
                        positioned.append({
                            'idx': i,
                            'label': label,
                            'center': (proc_px, proc_py),
                            'box': (x0, y0, x1, y1),
                            'next_raw': p.get('next', '') or '',
                            'type': 'subprocess'
                        })
                        lname = label.strip().lower()
                        name_index.setdefault(lname, []).append(len(positioned) - 1)
                    except (ValueError, TypeError):
                        continue

                # Helper: draw arrow with head
                def _draw_arrow(draw_ctx, x_start, y_start, x_end, y_end, color=(0, 0, 0, 255), width=3, head_len=18, head_angle_deg=30):
                    import math
                    from PIL import ImageDraw
                    
                    # Use PIL's line drawing with proper width for smooth diagonal lines
                    draw_ctx.line([(x_start, y_start), (x_end, y_end)], fill=color, width=width, joint='curve')
                    
                    ang = math.atan2(y_end - y_start, x_end - x_start)
                    ang_left = ang - math.radians(head_angle_deg)
                    ang_right = ang + math.radians(head_angle_deg)
                    x_left = x_end - head_len * math.cos(ang_left)
                    y_left = y_end - head_len * math.sin(ang_left)
                    x_right = x_end - head_len * math.cos(ang_right)
                    y_right = y_end - head_len * math.sin(ang_right)
                    draw_ctx.polygon([(x_end, y_end), (x_left, y_left), (x_right, y_right)], fill=color)

                # Build quick lookup by subprocess name (case-insensitive)
                # Also allow fallback tokens like numeric indices (1-based) or label exactly
                def _resolve_targets(target_token):
                    target_token = target_token.strip()
                    if not target_token:
                        return []
                    # numeric index support
                    if target_token.isdigit():
                        idx_int = int(target_token) - 1
                        for d in positioned:
                            if d['idx'] == idx_int:
                                return [d]
                        return []
                    lname2 = target_token.lower()
                    if lname2 in name_index:
                        return [positioned[i] for i in name_index[lname2]]
                    # Try exact match ignoring case across original names (robustness)
                    return [d for d in positioned if d['label'].lower() == lname2]

                # Second pass: draw arrows (under boxes for clarity -> so draw now, then boxes after?)
                # We'll draw arrows first then boxes so boxes sit on top.
                # Also collect product stream info for labeling on connection arrows
                connection_product_streams = []  # List of (src_idx, tgt_idx, start_x, start_y, end_x, end_y, streams)
                
                for src in positioned:
                    raw_next = src['next_raw']
                    if not raw_next:
                        continue
                    # Split by common delimiters
                    parts = []
                    for chunk in raw_next.replace(';', ',').replace('|', ',').split(','):
                        part = chunk.strip()
                        if part:
                            parts.append(part)
                    if not parts:
                        continue
                    sx, sy = src['center']
                    for part_token in parts:
                        targets = _resolve_targets(part_token)
                        for tgt in targets:
                            if tgt is src:
                                continue  # no self-loop for now
                            tx, ty = tgt['center']
                            # Adjust start/end to box edges
                            # Source box dims
                            sx0, sy0, sx1, sy1 = src['box']
                            sw2 = (sx1 - sx0) / 2.0
                            sh2 = (sy1 - sy0) / 2.0
                            # Target box dims
                            tx0, ty0, tx1, ty1 = tgt['box']
                            tw2 = (tx1 - tx0) / 2.0
                            th2 = (ty1 - ty0) / 2.0
                            vec_dx = tx - sx
                            vec_dy = ty - sy
                            if vec_dx == 0 and vec_dy == 0:
                                continue
                            import math as _math
                            # Factor to exit source box boundary
                            factors_s = []
                            if vec_dx != 0:
                                factors_s.append(sw2 / abs(vec_dx))
                            if vec_dy != 0:
                                factors_s.append(sh2 / abs(vec_dy))
                            t_s = min(factors_s) if factors_s else 0
                            # Factor to enter target box boundary from target center backwards
                            factors_t = []
                            if vec_dx != 0:
                                factors_t.append(tw2 / abs(vec_dx))
                            if vec_dy != 0:
                                factors_t.append(th2 / abs(vec_dy))
                            t_t = min(factors_t) if factors_t else 0
                            start_x = sx + vec_dx * t_s * 1.02
                            start_y = sy + vec_dy * t_s * 1.02
                            end_x = tx - vec_dx * t_t * 1.02
                            end_y = ty - vec_dy * t_t * 1.02
                            _draw_arrow(draw, start_x, start_y, end_x, end_y, color=(0, 0, 0, 245), width=5)
                            
                            # Collect product streams from source subprocess for labeling on this connection
                            if src.get('type') == 'subprocess':
                                src_proc = st.session_state['processes'][src['idx']]
                                src_streams = src_proc.get('streams', []) or []
                                product_streams = [s for s in src_streams if s.get('type', 'product') == 'product']
                                if product_streams:
                                    connection_product_streams.append({
                                        'src_idx': src['idx'],
                                        'tgt_idx': tgt['idx'],
                                        'start_x': start_x,
                                        'start_y': start_y,
                                        'end_x': end_x,
                                        'end_y': end_y,
                                        'streams': product_streams
                                    })
                
                # Draw product stream labels along connection arrows
                def _draw_connection_stream_label(draw_ctx, start_x, start_y, end_x, end_y, streams, font_obj):
                    """Draw product stream info below the connection line between processes."""
                    import math as _m
                    from PIL import ImageFont
                    
                    # Try to create a smaller font for stream labels
                    small_font = None
                    try:
                        small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 10)
                    except:
                        try:
                            small_font = ImageFont.truetype("arial.ttf", 10)
                        except:
                            small_font = font_obj  # fallback to regular font
                    
                    # Collect values from all product streams
                    all_parts = []
                    
                    for s in streams:
                        # Get display variables setting (Tin is always shown)
                        display_vars = s.get('display_vars', [])
                        
                        # Try to get values from stream_values first (new structure)
                        sv = s.get('stream_values', {})
                        if not sv:
                            sv = s.get('product_values', {})  # fallback to old name
                        
                        tin_val = sv.get('Tin', '')
                        tout_val = sv.get('Tout', '')
                        mdot_val = sv.get('ṁ', '')
                        cp_val = sv.get('cp', '')
                        CP_val = sv.get('CP', '')
                        
                        # Fallback to properties/values structure
                        if not tin_val or not tout_val or not mdot_val or not cp_val:
                            props = s.get('properties', {})
                            vals = s.get('values', {})
                            
                            if isinstance(props, dict) and isinstance(vals, dict):
                                for pk, pname in props.items():
                                    vk = pk.replace('prop', 'val')
                                    v = vals.get(vk, '')
                                    if pname == 'Tin' and v and not tin_val:
                                        tin_val = v
                                    elif pname == 'Tout' and v and not tout_val:
                                        tout_val = v
                                    elif pname == 'ṁ' and v and not mdot_val:
                                        mdot_val = v
                                    elif pname == 'cp' and v and not cp_val:
                                        cp_val = v
                                    elif pname == 'CP' and v and not CP_val:
                                        CP_val = v
                        
                        # Fallback to legacy fields
                        if not tin_val:
                            tin_val = s.get('temp_in', '')
                        if not tout_val:
                            tout_val = s.get('temp_out', '')
                        if not mdot_val:
                            mdot_val = s.get('mdot', '')
                        if not cp_val:
                            cp_val = s.get('cp', '')
                        
                        # Build parts for THIS stream based on display_vars (Tin is always shown)
                        stream_parts = []
                        stream_name = s.get('name', '')
                        if tin_val:
                            stream_parts.append(f"Tin={tin_val}")
                        if tout_val and "Tout" in display_vars:
                            stream_parts.append(f"Tout={tout_val}")
                        if mdot_val and "ṁ" in display_vars:
                            stream_parts.append(f"ṁ={mdot_val}")
                        if cp_val and "cp" in display_vars:
                            stream_parts.append(f"cp={cp_val}")
                        if CP_val and "CP" in display_vars:
                            stream_parts.append(f"CP={CP_val}")
                        
                        if stream_parts:
                            # Add stream name prefix if available
                            label = " | ".join(stream_parts)
                            if stream_name:
                                label = f"{stream_name}: {label}"
                            all_parts.append(label)
                    
                    if not all_parts:
                        return
                    
                    # Calculate midpoint of the connection line
                    mid_x = (start_x + end_x) / 2
                    mid_y = (start_y + end_y) / 2
                    
                    perp_offset = 18  # pixels below the line
                    line_height = 14  # height per stream label line
                    
                    # Draw each stream label on a separate line
                    for line_idx, stream_label in enumerate(all_parts):
                        # Calculate text dimensions with smaller font
                        if small_font:
                            tb = draw_ctx.textbbox((0, 0), stream_label, font=small_font)
                            t_width = tb[2] - tb[0]
                            t_height = tb[3] - tb[1]
                        else:
                            t_width = len(stream_label) * 5
                            t_height = 8
                        
                        # Position label below the midpoint, stacked vertically
                        lx = int(mid_x - t_width / 2)
                        ly = int(mid_y + perp_offset + (line_idx * line_height))
                        
                        # Draw white background
                        draw_ctx.rectangle([lx - 3, ly - 1, lx + t_width + 3, ly + t_height + 1], 
                                           fill=(255, 255, 255, 235), outline=(120, 120, 120, 150))
                        # Draw text with smaller font
                        if small_font:
                            draw_ctx.text((lx, ly), stream_label, fill=(0, 70, 0, 255), font=small_font)
                        else:
                            draw_ctx.text((lx, ly), stream_label, fill=(0, 70, 0, 255))
                
                # Third pass: draw boxes & labels on top
                for item in positioned:
                    x0, y0, x1, y1 = item['box']
                    label = item['label']
                    item_type = item.get('type', 'subprocess')
                    padding = 6
                    
                    # Retrieve scale from subprocess for consistent font positioning relative to new box
                    proc_scale = 1.0
                    if item_type == 'subprocess':
                        try:
                            proc_scale = float(st.session_state['processes'][item['idx']].get('box_scale',4.0) or 4.0)
                        except (ValueError, TypeError, KeyError):
                            proc_scale = 1.0
                    padding = int(6 * proc_scale)
                    
                    # Different colors for processes vs subprocesses
                    if item_type == 'process':
                        # Main process: Green fill with dark green border
                        fill_color = (200, 255, 200, 245)  # Light green
                        border_color = (34, 139, 34, 255)  # Forest green
                        text_color = (0, 100, 0, 255)      # Dark green
                        border_width = 3
                    else:
                        # Subprocess: Light blue fill with dark blue border (original)
                        fill_color = (224, 242, 255, 245)
                        border_color = (23, 105, 170, 255)
                        text_color = (10, 53, 85, 255)
                        border_width = 2
                    
                    # Draw filled rectangle
                    draw.rectangle([x0, y0, x1, y1], fill=fill_color, outline=border_color, width=border_width)
                    # Center text inside box
                    box_w = x1 - x0
                    box_h = y1 - y0
                    if font:
                        bbox_lbl = draw.textbbox((0,0), label, font=font)
                        t_w = bbox_lbl[2]-bbox_lbl[0]
                        t_h = bbox_lbl[3]-bbox_lbl[1]
                    else:
                        t_w = len(label)*6
                        t_h = 10
                    ct_x = int(x0 + (box_w - t_w)/2)
                    ct_y = int(y0 + (box_h - t_h)/2)
                    if font:
                        draw.text((ct_x, ct_y), label, fill=text_color, font=font)
                    else:
                        draw.text((ct_x, ct_y), label, fill=text_color)

                # Draw all product stream labels on connections (after boxes so they appear on top)
                for conn in connection_product_streams:
                    _draw_connection_stream_label(
                        draw, 
                        conn['start_x'], conn['start_y'], 
                        conn['end_x'], conn['end_y'], 
                        conn['streams'], 
                        font
                    )

                # Sixth pass: draw subprocess overlays for expanded process groups
                process_subprocess_map_expanded = st.session_state.get('process_subprocess_map_expanded', {})
                for proc_group_idx, is_expanded in process_subprocess_map_expanded.items():
                    if not is_expanded:
                        continue
                    
                    proc_group_idx_int = int(proc_group_idx) if isinstance(proc_group_idx, str) else proc_group_idx
                    
                    # Get process group name and subprocess indices
                    proc_group_names = st.session_state.get('proc_group_names', [])
                    proc_group_lists = st.session_state.get('proc_group_lists', [])
                    
                    if proc_group_idx_int >= len(proc_group_names) or proc_group_idx_int >= len(proc_group_lists):
                        continue
                    
                    proc_group_name = proc_group_names[proc_group_idx_int]
                    subprocess_indices = proc_group_lists[proc_group_idx_int]
                    
                    try:
                        # Full screen overlay (85% of screen)
                        pg_overlay_w = int(w * 0.85)
                        pg_overlay_h = int(h * 0.85)
                        
                        # Center in the middle of the screen
                        center_px = w // 2
                        center_py = h // 2
                        
                        pg_overlay_x0 = int(center_px - pg_overlay_w / 2)
                        pg_overlay_y0 = int(center_py - pg_overlay_h / 2)
                        pg_overlay_x1 = pg_overlay_x0 + pg_overlay_w
                        pg_overlay_y1 = pg_overlay_y0 + pg_overlay_h
                        
                        # Ensure overlay stays within map bounds
                        margin = 20
                        pg_overlay_x0 = max(margin, pg_overlay_x0)
                        pg_overlay_y0 = max(margin, pg_overlay_y0)
                        pg_overlay_x1 = min(w - margin, pg_overlay_x1)
                        pg_overlay_y1 = min(h - margin, pg_overlay_y1)
                        
                        # Draw light blue overlay with border (for subprocess level)
                        draw.rectangle([pg_overlay_x0, pg_overlay_y0, pg_overlay_x1, pg_overlay_y1], 
                                       fill=(240, 248, 255, 245),  # Light blue (AliceBlue)
                                       outline=(70, 130, 180, 220),  # SteelBlue border
                                       width=2)
                        
                        # Add label in top-left corner
                        pg_overlay_label = f"Subprocess Area: {proc_group_name}"
                        if font:
                            label_bbox = draw.textbbox((0, 0), pg_overlay_label, font=font)
                            label_w = label_bbox[2] - label_bbox[0]
                            label_h = label_bbox[3] - label_bbox[1]
                        else:
                            label_w = len(pg_overlay_label) * 6
                            label_h = 10
                        
                        label_x = pg_overlay_x0 + 15
                        label_y = pg_overlay_y0 + 12
                        
                        # Background for label
                        draw.rectangle([label_x-5, label_y-3, label_x+label_w+5, label_y+label_h+3], 
                                     fill=(220, 235, 250, 200), 
                                     outline=(100, 150, 200, 150), 
                                     width=1)
                        
                        if font:
                            draw.text((label_x, label_y), pg_overlay_label, fill=(30, 60, 90, 255), font=font)
                        else:
                            draw.text((label_x, label_y), pg_overlay_label, fill=(30, 60, 90, 255))
                        
                        # Draw subprocess boxes inside the overlay
                        if subprocess_indices:
                            n_subprocs = len(subprocess_indices)
                            usable_w = pg_overlay_x1 - pg_overlay_x0 - 60
                            usable_h = pg_overlay_y1 - pg_overlay_y0 - 80
                            
                            # Calculate grid layout
                            cols = min(n_subprocs, 4)
                            rows = (n_subprocs + cols - 1) // cols
                            
                            sub_box_w = min(180, usable_w // cols - 20)
                            sub_box_h = min(70, usable_h // rows - 20)
                            
                            # Starting position for grid
                            grid_start_x = pg_overlay_x0 + 30
                            grid_start_y = pg_overlay_y0 + 50
                            
                            for si, sub_idx in enumerate(subprocess_indices):
                                if sub_idx >= len(st.session_state['processes']):
                                    continue
                                    
                                subprocess = st.session_state['processes'][sub_idx]
                                col_idx = si % cols
                                row_idx = si // cols
                                
                                # Default grid position
                                sx = grid_start_x + col_idx * (sub_box_w + 25) + sub_box_w // 2
                                sy = grid_start_y + row_idx * (sub_box_h + 25) + sub_box_h // 2
                                
                                # Check if subprocess has lat/lon - if so, draw at that location
                                sub_lat = subprocess.get('lat')
                                sub_lon = subprocess.get('lon')
                                if sub_lat and sub_lon and str(sub_lat).strip() and str(sub_lon).strip():
                                    try:
                                        sub_lat_f = float(sub_lat)
                                        sub_lon_f = float(sub_lon)
                                        sx, sy = snapshot_lonlat_to_pixel(
                                            sub_lon_f, sub_lat_f,
                                            (st.session_state['map_center'][1], st.session_state['map_center'][0]),
                                            st.session_state['map_zoom'], w, h
                                        )
                                    except (ValueError, TypeError):
                                        pass
                                
                                sub_name = subprocess.get('name', f'Subprocess {sub_idx + 1}')
                                sub_scale = float(subprocess.get('box_scale', 1.0) or 1.0)
                                
                                # Calculate box dimensions
                                if font:
                                    name_bbox = draw.textbbox((0, 0), sub_name, font=font)
                                    name_w = name_bbox[2] - name_bbox[0]
                                    name_h = name_bbox[3] - name_bbox[1]
                                else:
                                    name_w = len(sub_name) * 6
                                    name_h = 10
                                
                                box_w_sub = int(name_w * sub_scale + 28)
                                box_h_sub = int(name_h * sub_scale + 22)
                                
                                sx0 = int(sx - box_w_sub // 2)
                                sy0 = int(sy - box_h_sub // 2)
                                sx1 = sx0 + box_w_sub
                                sy1 = sy0 + box_h_sub
                                
                                # Draw subprocess box with blue color
                                draw.rectangle([sx0, sy0, sx1, sy1], 
                                               fill=(224, 242, 255, 245),  # Light blue
                                               outline=(23, 105, 170, 255),  # Dark blue border
                                               width=2)
                                
                                # Center text
                                text_x = int(sx - name_w // 2)
                                text_y = int(sy - name_h // 2)
                                
                                if font:
                                    draw.text((text_x, text_y), sub_name, fill=(10, 53, 85, 255), font=font)
                                else:
                                    draw.text((text_x, text_y), sub_name, fill=(10, 53, 85, 255))
                        
                    except (ValueError, TypeError):
                        continue

                # Fourth pass: vertical stream arrows (Tin above box entering, Tout below leaving)
                # Color rule: if Tin > Tout -> red (cooling stream), else blue (heating stream). Unknown -> gray.
                # Labels now ONLY appear at top (Tin, ṁ, cp) and bottom (Tout, ṁ, cp) – nothing in the middle so arrows can be closer.
                arrow_len_v = 45  # vertical arrow length above / below box
                base_stream_spacing = 60  # wider default spacing to avoid overlap

                def _draw_v_arrow(draw_ctx, x_pos, y_from, y_to, head_at_end=True, color=(0,0,0,245), width=3):
                    """Draw vertical arrow from y_from to y_to at x_pos. If head_at_end True head at y_to else at y_from."""
                    draw_ctx.line([(x_pos, y_from), (x_pos, y_to)], fill=color, width=width)
                    head_len = 11
                    head_half = 7
                    if head_at_end:
                        # Triangle pointing direction of (y_to - y_from)
                        direction = 1 if y_to >= y_from else -1
                        tip_y = y_to
                        base_y = y_to - direction * head_len
                    else:
                        direction = 1 if y_from >= y_to else -1
                        tip_y = y_from
                        base_y = y_from - direction * head_len
                    # Triangle horizontal span
                    draw_ctx.polygon([
                        (x_pos, tip_y),
                        (x_pos - head_half, base_y),
                        (x_pos + head_half, base_y)
                    ], fill=color)

                def _label_centered(text_str, x_center, y_baseline, above=True):
                    if not text_str:
                        return
                    if font:
                        tb = draw.textbbox((0,0), text_str, font=font)
                        t_width = tb[2]-tb[0]; t_height = tb[3]-tb[1]
                    else:
                        t_width = len(text_str)*6; t_height = 10
                    text_xc = int(x_center - t_width/2)
                    text_yc = int(y_baseline - (t_height if above else 0))
                    draw.rectangle([text_xc-2, text_yc-2, text_xc+t_width+2, text_yc+t_height+2], fill=(255,255,255,230))
                    if font:
                        draw.text((text_xc, text_yc), text_str, fill=(0,0,0,255), font=font)
                    else:
                        draw.text((text_xc, text_yc), text_str, fill=(0,0,0,255))

                for item in positioned:
                    # Only draw streams for subprocesses, not main processes
                    if item.get('type') != 'subprocess':
                        continue
                        
                    proc_idx = item['idx']
                    proc = st.session_state['processes'][proc_idx]
                    streams = proc.get('streams', []) or []
                    if not streams:
                        continue
                    
                    # Filter out product streams (they are shown on horizontal connection arrows)
                    non_product_streams = [s for s in streams if s.get('type', 'product') != 'product']
                    if not non_product_streams:
                        continue
                        
                    x0, y0, x1, y1 = item['box']
                    box_center_x = (x0 + x1) / 2
                    n_streams = len(non_product_streams)
                    # Dynamic spacing: attempt to shrink if narrow box; ensure minimum 28 px spacing
                    stream_h_spacing = max(28, min(base_stream_spacing, (x1 - x0 - 20) / max(1, n_streams))) if n_streams > 1 else 0
                    for s_i, s in enumerate(non_product_streams):
                        offset = (s_i - (n_streams - 1)/2) * stream_h_spacing
                        sx = int(box_center_x + offset)
                        # Attempt to parse temperatures
                        tin_raw = s.get('temp_in', '')
                        tout_raw = s.get('temp_out', '')
                        try:
                            tin_val = float(str(tin_raw).strip())
                        except (ValueError, TypeError):
                            tin_val = None
                        try:
                            tout_val = float(str(tout_raw).strip())
                        except (ValueError, TypeError):
                            tout_val = None
                        # Color logic
                        if tin_val is not None and tout_val is not None:
                            is_cooling = tin_val > tout_val
                            col = (200, 25, 25, 255) if is_cooling else (25, 80, 200, 255)
                        else:
                            col = (90, 90, 90, 255)
                        # Inbound arrow (above box pointing downward INTO box)
                        inbound_bottom = y0 - 2  # head just touches box border
                        inbound_top = inbound_bottom - arrow_len_v
                        _draw_v_arrow(draw, sx, inbound_top, inbound_bottom, head_at_end=True, color=col, width=4)
                        # Outbound arrow (below box pointing downward AWAY from box)
                        outbound_top = y1 + 2
                        outbound_bottom = outbound_top + arrow_len_v
                        _draw_v_arrow(draw, sx, outbound_top, outbound_bottom, head_at_end=True, color=col, width=4)
                        # Labels
                        # m dot symbol fallback handling
                        mdot_raw = s.get('mdot','')
                        cp_raw = s.get('cp','')
                        # Prefer combining dot ṁ; if font renders poorly user can switch later; keep fallback token
                        m_symbol = "ṁ"  # m + combining dot above
                        if isinstance(mdot_raw, str) and mdot_raw.strip() == '':
                            mdot_part = ''
                        else:
                            mdot_part = f"{m_symbol}={mdot_raw}" if mdot_raw not in (None,'') else ''
                        cp_part = f"cp={cp_raw}" if cp_raw not in (None,'') else ''
                        # Build top & bottom label clusters
                        tin_label = f"Tin={tin_raw}" if tin_raw not in ('', None) else 'Tin=?'
                        tout_label = f"Tout={tout_raw}" if tout_raw not in ('', None) else 'Tout=?'
                        top_components = [tin_label]
                        if mdot_part: top_components.append(mdot_part)
                        if cp_part: top_components.append(cp_part)
                        bot_components = [tout_label]
                        if mdot_part: bot_components.append(mdot_part)
                        if cp_part: bot_components.append(cp_part)
                        top_text = "  |  ".join(top_components)
                        bot_text = "  |  ".join(bot_components)
                        _label_centered(top_text, sx, inbound_top - 6, above=True)
                        _label_centered(bot_text, sx, outbound_bottom + 6, above=False)
                
                # Seventh pass: draw sub-subprocess overlays for expanded subprocesses (LAST - on top of everything)
                subprocess_map_expanded = st.session_state.get('subprocess_map_expanded', {})
                for subprocess_idx, is_expanded in subprocess_map_expanded.items():
                    if not is_expanded:
                        continue
                    
                    subprocess_idx_int = int(subprocess_idx) if isinstance(subprocess_idx, str) else subprocess_idx
                    
                    # Get subprocess position
                    if subprocess_idx_int >= len(st.session_state['processes']):
                        continue
                    
                    subprocess = st.session_state['processes'][subprocess_idx_int]
                    sub_lat = subprocess.get('lat')
                    sub_lon = subprocess.get('lon')
                    
                    # Draw overlay even if subprocess has no coordinates (centered on screen)
                    try:
                        # Full screen overlay like process overlay, but slightly smaller (80% instead of 90%)
                        sub_overlay_w = int(w * 0.80)
                        sub_overlay_h = int(h * 0.80)
                        
                        # Always center in the middle of the screen
                        center_px = w // 2
                        center_py = h // 2
                        
                        sub_overlay_x0 = int(center_px - sub_overlay_w / 2)
                        sub_overlay_y0 = int(center_py - sub_overlay_h / 2)
                        sub_overlay_x1 = sub_overlay_x0 + sub_overlay_w
                        sub_overlay_y1 = sub_overlay_y0 + sub_overlay_h
                        
                        # Ensure overlay stays within map bounds with some padding
                        margin = 25
                        sub_overlay_x0 = max(margin, sub_overlay_x0)
                        sub_overlay_y0 = max(margin, sub_overlay_y0)
                        sub_overlay_x1 = min(w - margin, sub_overlay_x1)
                        sub_overlay_y1 = min(h - margin, sub_overlay_y1)
                        
                        # Draw white overlay with subtle border (similar to process overlay but white)
                        draw.rectangle([sub_overlay_x0, sub_overlay_y0, sub_overlay_x1, sub_overlay_y1], 
                                       fill=(255, 255, 255, 245),
                                       outline=(150, 150, 150, 220), 
                                       width=2)
                        
                        # Add label in top-left corner
                        subprocess_name = subprocess.get('name', f'Subprocess {subprocess_idx_int + 1}')
                        sub_overlay_label = f"Sub-subprocess Area: {subprocess_name}"
                        if font:
                            label_bbox = draw.textbbox((0, 0), sub_overlay_label, font=font)
                            label_w = label_bbox[2] - label_bbox[0]
                            label_h = label_bbox[3] - label_bbox[1]
                        else:
                            label_w = len(sub_overlay_label) * 6
                            label_h = 10
                        
                        label_x = sub_overlay_x0 + 15
                        label_y = sub_overlay_y0 + 12
                        
                        # Subtle background for label
                        draw.rectangle([label_x-5, label_y-3, label_x+label_w+5, label_y+label_h+3], 
                                     fill=(240, 240, 240, 200), 
                                     outline=(180, 180, 180, 150), 
                                     width=1)
                        
                        if font:
                            draw.text((label_x, label_y), sub_overlay_label, fill=(40, 40, 40, 255), font=font)
                        else:
                            draw.text((label_x, label_y), sub_overlay_label, fill=(40, 40, 40, 255))
                        
                        # Draw sub-subprocess boxes inside the overlay
                        children = subprocess.get('children', [])
                        if children:
                            n_children = len(children)
                            usable_w = sub_overlay_x1 - sub_overlay_x0 - 60
                            usable_h = sub_overlay_y1 - sub_overlay_y0 - 80
                            
                            # Calculate grid layout
                            cols = min(n_children, 4)
                            rows = (n_children + cols - 1) // cols
                            
                            child_box_w = min(150, usable_w // cols - 20)
                            child_box_h = min(60, usable_h // rows - 20)
                            
                            # Starting position for grid
                            grid_start_x = sub_overlay_x0 + 30
                            grid_start_y = sub_overlay_y0 + 50
                            
                            for ci, child in enumerate(children):
                                col_idx = ci % cols
                                row_idx = ci // cols
                                
                                # Default grid position
                                cx = grid_start_x + col_idx * (child_box_w + 25) + child_box_w // 2
                                cy = grid_start_y + row_idx * (child_box_h + 25) + child_box_h // 2
                                
                                # Check if child has lat/lon - if so, draw at that location instead
                                child_lat = child.get('lat')
                                child_lon = child.get('lon')
                                if child_lat and child_lon and str(child_lat).strip() and str(child_lon).strip():
                                    try:
                                        child_lat_f = float(child_lat)
                                        child_lon_f = float(child_lon)
                                        cx, cy = snapshot_lonlat_to_pixel(
                                            child_lon_f, child_lat_f,
                                            (st.session_state['map_center'][1], st.session_state['map_center'][0]),
                                            st.session_state['map_zoom'], w, h
                                        )
                                    except (ValueError, TypeError):
                                        pass
                                
                                child_name = child.get('name', f'Sub-sub {ci + 1}')
                                child_scale = float(child.get('box_scale', 0.8) or 0.8)
                                
                                # Calculate box dimensions
                                if font:
                                    name_bbox = draw.textbbox((0, 0), child_name, font=font)
                                    name_w = name_bbox[2] - name_bbox[0]
                                    name_h = name_bbox[3] - name_bbox[1]
                                else:
                                    name_w = len(child_name) * 6
                                    name_h = 10
                                
                                box_w_child = int(name_w * child_scale + 24)
                                box_h_child = int(name_h * child_scale + 18)
                                
                                cx0 = int(cx - box_w_child // 2)
                                cy0 = int(cy - box_h_child // 2)
                                cx1 = cx0 + box_w_child
                                cy1 = cy0 + box_h_child
                                
                                # Draw child box with purple/violet color (to distinguish from subprocesses)
                                draw.rectangle([cx0, cy0, cx1, cy1], 
                                               fill=(245, 230, 255, 245),  # Light purple
                                               outline=(128, 0, 128, 255),  # Purple border
                                               width=2)
                                
                                # Center text
                                text_x = int(cx - name_w // 2)
                                text_y = int(cy - name_h // 2)
                                
                                if font:
                                    draw.text((text_x, text_y), child_name, fill=(75, 0, 75, 255), font=font)
                                else:
                                    draw.text((text_x, text_y), child_name, fill=(75, 0, 75, 255))
                                
                                # Draw stream arrows for sub-subprocess
                                child_streams = child.get('streams', []) or []
                                if child_streams:
                                    child_arrow_len = 35  # slightly shorter arrows for sub-subprocesses
                                    child_stream_spacing = 40
                                    n_child_streams = len(child_streams)
                                    child_box_center_x = (cx0 + cx1) / 2
                                    
                                    for cs_i, cs in enumerate(child_streams):
                                        cs_offset = (cs_i - (n_child_streams - 1)/2) * child_stream_spacing
                                        cs_x = int(child_box_center_x + cs_offset)
                                        
                                        # Parse temperatures from stream
                                        cs_tin_raw = cs.get('temp_in', '')
                                        cs_tout_raw = cs.get('temp_out', '')
                                        # Also check values dict for property-based streams
                                        if not cs_tin_raw and cs.get('properties', {}).get('prop1') == 'Tin':
                                            cs_tin_raw = cs.get('values', {}).get('val1', '')
                                        if not cs_tout_raw and cs.get('properties', {}).get('prop2') == 'Tout':
                                            cs_tout_raw = cs.get('values', {}).get('val2', '')
                                        
                                        try:
                                            cs_tin_val = float(str(cs_tin_raw).strip())
                                        except (ValueError, TypeError):
                                            cs_tin_val = None
                                        try:
                                            cs_tout_val = float(str(cs_tout_raw).strip())
                                        except (ValueError, TypeError):
                                            cs_tout_val = None
                                        
                                        # Color logic
                                        if cs_tin_val is not None and cs_tout_val is not None:
                                            cs_is_cooling = cs_tin_val > cs_tout_val
                                            cs_col = (200, 25, 25, 255) if cs_is_cooling else (25, 80, 200, 255)
                                        else:
                                            cs_col = (90, 90, 90, 255)
                                        
                                        # Inbound arrow (above box pointing downward INTO box)
                                        cs_inbound_bottom = cy0 - 2
                                        cs_inbound_top = cs_inbound_bottom - child_arrow_len
                                        # Draw arrow line
                                        draw.line([(cs_x, cs_inbound_top), (cs_x, cs_inbound_bottom)], fill=cs_col, width=3)
                                        # Draw arrow head
                                        draw.polygon([
                                            (cs_x, cs_inbound_bottom),
                                            (cs_x - 5, cs_inbound_bottom - 8),
                                            (cs_x + 5, cs_inbound_bottom - 8)
                                        ], fill=cs_col)
                                        
                                        # Outbound arrow (below box pointing downward AWAY from box)
                                        cs_outbound_top = cy1 + 2
                                        cs_outbound_bottom = cs_outbound_top + child_arrow_len
                                        # Draw arrow line
                                        draw.line([(cs_x, cs_outbound_top), (cs_x, cs_outbound_bottom)], fill=cs_col, width=3)
                                        # Draw arrow head
                                        draw.polygon([
                                            (cs_x, cs_outbound_bottom),
                                            (cs_x - 5, cs_outbound_bottom - 8),
                                            (cs_x + 5, cs_outbound_bottom - 8)
                                        ], fill=cs_col)
                        
                    except (ValueError, TypeError):
                        continue

                # Present snapshot full width (base selector moved to top bar)
                img = base_img  # for coordinate capture
                
                # Save the rendered subprocess canvas image to session state for report generation
                # This captures the exact view with all connections, energy data, colors, etc.
                process_subprocess_map_exp = st.session_state.get('process_subprocess_map_expanded', {})
                any_subprocess_view_active = any(process_subprocess_map_exp.get(g, False) for g in process_subprocess_map_exp)
                if any_subprocess_view_active:
                    # Save as PNG bytes
                    subprocess_canvas_buffer = BytesIO()
                    base_img.save(subprocess_canvas_buffer, format='PNG')
                    st.session_state['subprocess_canvas_image'] = subprocess_canvas_buffer.getvalue()
                
                coords = streamlit_image_coordinates(img, key="meas_img", width=w)
                if st.session_state['placement_mode'] and coords is not None and st.session_state.get('placing_process_idx') is not None:
                    x_px, y_px = coords['x'], coords['y']
                    lon_new, lat_new = snapshot_pixel_to_lonlat(x_px, y_px, st.session_state['map_center'][::-1], st.session_state['map_zoom'], w, h)
                    placing_idx = st.session_state['placing_process_idx']
                    
                    try:
                        if isinstance(placing_idx, str) and placing_idx.startswith('group_'):
                            # Group placement
                            group_idx = int(placing_idx.split('_')[1])
                            group_name = st.session_state['proc_group_names'][group_idx]
                            st.session_state['proc_group_coordinates'][group_idx] = {
                                'lat': round(lat_new, 6),
                                'lon': round(lon_new, 6)
                            }
                            st.session_state['ui_status_msg'] = f"✅ Process {group_name} placed at ({lat_new:.6f}, {lon_new:.6f})"
                            # Auto-disable placement mode after successful placement
                            st.session_state['placement_mode'] = False
                            st.session_state['placing_process_idx'] = None
                            st.rerun()
                        elif isinstance(placing_idx, str) and placing_idx.startswith('child_'):
                            # Child node placement (sub-subprocess, sub-sub-subprocess, etc.)
                            # The child node reference should be stored in session state
                            child_node = st.session_state.get('placing_node_ref')
                            if child_node is not None:
                                child_node['lat'] = round(lat_new, 6)
                                child_node['lon'] = round(lon_new, 6)
                                child_name = child_node.get('name', 'Child')
                                st.session_state['ui_status_msg'] = f"✅ {child_name} placed at ({lat_new:.6f}, {lon_new:.6f})"
                            # Auto-disable placement mode after successful placement
                            st.session_state['placement_mode'] = False
                            st.session_state['placing_process_idx'] = None
                            st.session_state['placing_node_ref'] = None
                            st.rerun()
                        elif isinstance(placing_idx, int):
                            # Subprocess placement
                            process_name = st.session_state['processes'][placing_idx].get('name') or f"Subprocess {placing_idx+1}"
                            st.session_state['processes'][placing_idx]['lat'] = round(lat_new, 6)
                            st.session_state['processes'][placing_idx]['lon'] = round(lon_new, 6)
                            st.session_state['ui_status_msg'] = f"✅ {process_name} placed at ({lat_new:.6f}, {lon_new:.6f})"
                            # Auto-disable placement mode after successful placement
                            st.session_state['placement_mode'] = False
                            st.session_state['placing_process_idx'] = None
                            st.rerun()
                    except (ValueError, TypeError, IndexError):
                        st.error("Failed to set coordinates")
                if st.session_state['measure_mode']:
                    if coords is not None and len(st.session_state['measure_points']) < 2:
                        st.session_state['measure_points'].append((coords['x'], coords['y']))
                    st.session_state['measure_points'] = st.session_state['measure_points'][-2:]
                # Compute distance if two points selected (store in session for status bar)
                if len(st.session_state['measure_points']) == 2:
                    x1, y1 = st.session_state['measure_points'][0]
                    x2, y2 = st.session_state['measure_points'][1]
                    lon1, lat1 = snapshot_pixel_to_lonlat(x1, y1, st.session_state['map_center'][::-1], st.session_state['map_zoom'], w, h)
                    lon2, lat2 = snapshot_pixel_to_lonlat(x2, y2, st.session_state['map_center'][::-1], st.session_state['map_zoom'], w, h)
                    def haversine(_lat1, _lon1, _lat2, _lon2):
                        RADIUS_EARTH_M = 6371000
                        phi1 = radians(_lat1)
                        phi2 = radians(_lat2)
                        dphi = radians(_lat2 - _lat1)
                        dlambda = radians(_lon2 - _lon1)
                        a_val = sin(dphi/2)**2 + cos(phi1)*cos(phi2)*sin(dlambda/2)**2
                        c_val = 2*atan2(sqrt(a_val), sqrt(1-a_val))
                        return RADIUS_EARTH_M * c_val
                    dist_m = haversine(lat1, lon1, lat2, lon2)
                    st.session_state['measure_distance_m'] = dist_m
                else:
                    # clear stored distance if points < 2
                    st.session_state['measure_distance_m'] = None
                
                # Notes section below the map
                st.markdown("---")
                st.markdown("**📝 Notes**")
                
                # Initialize notes in session state if not present
                if 'project_notes' not in st.session_state:
                    st.session_state['project_notes'] = ""
                
                st.session_state['project_notes'] = st.text_area(
                    "Project Notes",
                    value=st.session_state.get('project_notes', ''),
                    height=150,
                    key="notes_text_area",
                    label_visibility="collapsed",
                    placeholder="Enter notes about your project here..."
                )
            else:
                st.warning("Snapshot missing. Unlock and re-capture if needed.")
