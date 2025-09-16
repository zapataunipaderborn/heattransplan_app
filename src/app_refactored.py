"""
Main Streamlit application for Heat Integration Analysis.
Refactored into modular components for better maintainability.
"""

import streamlit as st
import hashlib
from streamlit_image_coordinates import streamlit_image_coordinates

# Import our modules
from config import DEFAULT_START_COORDS
from session_state import initialize_session_state, should_regenerate_snapshots, update_map_state
from ui_components import apply_custom_css, create_base_layer_selector, create_status_bar
from map_utils import create_folium_map, geocode_address, capture_map_snapshots, get_base_image, render_folium_map
from visualization import render_process_overlay
from process_interface import render_process_groups, render_process_editor
from geo_utils import snapshot_pixel_to_lonlat, haversine


def main():
    """Main application entry point."""
    # Page configuration
    st.set_page_config(page_title="Heat Integration analysis", layout="wide")
    
    # Apply custom styling
    apply_custom_css()
    
    # Add spacing and title
    st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
    st.title("Heat Integration analysis")
    
    # Initialize session state
    initialize_session_state()
    
    # Main application layout
    render_main_interface()


def render_main_interface():
    """Render the main application interface with left panel and map."""
    left, right = st.columns([2.4, 5.6], gap="small")
    
    with left:
        render_left_panel()
    
    with right:
        render_right_panel()


def render_left_panel():
    """Render the left control panel."""
    mode_current = st.session_state['ui_mode_radio']
    
    if mode_current == "Select Map":
        render_map_lock_button()
    
    st.session_state['ui_mode_radio'] = st.radio(
        "Mode",
        ["Select Map", "Analyze"],
        index=0 if mode_current == "Select Map" else 1,
        key="mode_radio_new",
        horizontal=True
    )
    
    mode = st.session_state['ui_mode_radio']
    
    # Subprocess & Stream UI (only show in Analyze mode)
    if mode == "Analyze":
        render_process_groups()
        render_process_editor()
    else:
        render_map_mode_info()


def render_map_lock_button():
    """Render the map lock button and handle locking logic."""
    col_lock = st.columns([1])[0]
    if col_lock.button("Lock map and analyze", key="btn_lock_analyze"):
        new_center = st.session_state['selector_center'][:]
        new_zoom = st.session_state['selector_zoom']
        selected_base_now = st.session_state.get('current_base', 'OpenStreetMap')
        
        if should_regenerate_snapshots(new_center, new_zoom, selected_base_now):
            update_map_state(new_center, new_zoom)
            
            try:
                snapshots = capture_map_snapshots(new_center, new_zoom)
                st.session_state['map_snapshots'] = snapshots
                st.session_state['map_snapshot'] = snapshots.get('OpenStreetMap')
            except Exception as e:
                st.session_state['ui_status_msg'] = f"Capture failed: {e}"
                st.error(f"Map capture error: {e}")
                st.rerun()
                
        st.session_state['map_locked'] = True
        st.session_state['analyze_base_layer'] = selected_base_now
        st.session_state['ui_mode_radio'] = 'Analyze'
        
        if not st.session_state.get('ui_status_msg'):
            st.session_state['ui_status_msg'] = "Snapshot captured"
        st.rerun()


def render_map_mode_info():
    """Render information about existing processes in map mode."""
    processes = st.session_state.get('processes', [])
    if processes:
        st.caption(f"Processes: {len(processes)} (edit in Analyze mode)")
    else:
        st.caption("Add processes in Analyze mode after locking a map view.")


def render_right_panel():
    """Render the right panel with map or analysis view."""
    mode = st.session_state['ui_mode_radio']
    
    if mode == "Select Map":
        render_map_selection_interface()
    else:
        render_analysis_interface()


def render_map_selection_interface():
    """Render the map selection interface."""
    # Address search and base layer controls
    addr_col, btn_col, info_col, base_col = st.columns([5, 1, 2, 2])
    
    address = addr_col.text_input("Search address", key="address_input")
    
    if btn_col.button("Search", key="search_button") and address:
        lat, lon = geocode_address(address)
        if lat is not None and lon is not None:
            st.session_state['selector_center'] = [lat, lon]
            st.success(f"Found: {lat:.6f}, {lon:.6f}")
            st.rerun()
        else:
            st.error("Address not found")
    
    info_col.caption("Pan/zoom, then click 'Lock map and analyze' to capture a snapshot.")
    
    # Base layer selector
    base_col.markdown("<div style='font-size:12px; font-weight:600; margin-bottom:2px;'>Base</div>", 
                     unsafe_allow_html=True)
    new_base = create_base_layer_selector("map", current_base=st.session_state.get('current_base', 'OpenStreetMap'))
    if new_base != st.session_state.get('current_base'):
        st.session_state['current_base'] = new_base
    
    # Render the interactive map
    render_interactive_map()


def render_interactive_map():
    """Render the interactive Folium map."""
    selected_base = st.session_state.get('current_base', 'OpenStreetMap')
    
    # Check if map needs recreation
    processes_hash = hashlib.md5(str(st.session_state.get('processes', [])).encode()).hexdigest()
    map_state_hash = f"{selected_base}_{processes_hash}"
    need_recreate = (
        'map_state_hash' not in st.session_state or
        st.session_state['map_state_hash'] != map_state_hash
    )
    
    if need_recreate:
        st.session_state['map_state_hash'] = map_state_hash
    
    # Get current center and zoom
    current_center = st.session_state.get('selector_center', DEFAULT_START_COORDS)
    current_zoom = st.session_state.get('selector_zoom', 17.5)
    
    # Create and render map
    fmap = create_folium_map(current_center, current_zoom, selected_base)
    processes = st.session_state.get('processes', [])
    map_data = render_folium_map(fmap, processes)
    
    # Update session state with map changes
    if map_data and 'center' in map_data and map_data['center']:
        new_center = [map_data['center']['lat'], map_data['center']['lng']]
        new_zoom = map_data.get('zoom', current_zoom)
        st.session_state['selector_center'] = new_center
        st.session_state['selector_zoom'] = new_zoom


def render_analysis_interface():
    """Render the analysis interface with snapshot and tools."""
    if not st.session_state['map_locked']:
        st.warning("No locked snapshot yet. Switch to 'Select Map' and capture one.")
        return
    
    # Top action/status bar
    render_analysis_toolbar()
    
    # Main analysis view
    render_analysis_view()


def render_analysis_toolbar():
    """Render the analysis toolbar with status and controls."""
    top_c1, top_c2, top_c3, top_c4 = st.columns([3, 2, 2, 2])
    
    with top_c1:
        # Dynamic status message
        placing_idx = st.session_state.get('placing_process_idx')
        placing_mode = st.session_state.get('placement_mode')
        measure_mode = st.session_state.get('measure_mode')
        measure_points = st.session_state.get('measure_points', [])
        dist_val = st.session_state.get('measure_distance_m')
        last_msg = st.session_state.get('ui_status_msg')
        processes = st.session_state.get('processes', [])
        
        create_status_bar(placing_mode, placing_idx, measure_mode, measure_points, 
                         dist_val, last_msg, processes)
    
    with top_c2:
        # Measurement controls
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
        st.empty()  # spacer
    
    with top_c4:
        # Base layer selector for analysis
        st.markdown("<div style='font-size:12px; font-weight:600; margin-bottom:0px;'>Base</div>", 
                   unsafe_allow_html=True)
        from config import ANALYZE_OPTIONS
        current_base = st.session_state.get('current_base', 'OpenStreetMap')
        if current_base not in ANALYZE_OPTIONS:
            current_base = 'OpenStreetMap'
        
        new_base = st.selectbox(
            label="Base layer analyze",
            options=ANALYZE_OPTIONS,
            index=ANALYZE_OPTIONS.index(current_base),
            key='analyze_base_selector_top',
            label_visibility='collapsed'
        )
        if new_base != current_base:
            st.session_state['current_base'] = new_base


def render_analysis_view():
    """Render the main analysis view with process overlay."""
    # Get base image
    active_base = st.session_state.get('current_base', 'OpenStreetMap')
    snapshots_dict = st.session_state.get('map_snapshots', {})
    fallback_snapshot = st.session_state.get('map_snapshot')
    
    base_img = get_base_image(active_base, snapshots_dict, fallback_snapshot)
    
    if base_img:
        # Render process overlay
        processes = st.session_state.get('processes', [])
        map_center = st.session_state.get('map_center', DEFAULT_START_COORDS)
        map_zoom = st.session_state.get('map_zoom', 17.5)
        
        overlay_img = render_process_overlay(base_img, processes, map_center, map_zoom)
        
        if overlay_img:
            # Display interactive image with coordinates
            w, h = overlay_img.size
            coords = streamlit_image_coordinates(
                overlay_img,
                key="analyze_coords",
                width=w,
                height=h
            )
            
            # Handle coordinate interactions
            handle_image_interactions(coords, w, h)


def handle_image_interactions(coords, img_w, img_h):
    """Handle interactions with the analysis image."""
    if coords is None:
        return
    
    map_center = st.session_state.get('map_center', DEFAULT_START_COORDS)
    map_zoom = st.session_state.get('map_zoom', 17.5)
    
    # Handle process placement
    if st.session_state.get('placement_mode') and coords:
        placing_idx = st.session_state.get('placing_process_idx')
        if placing_idx is not None and 0 <= placing_idx < len(st.session_state.get('processes', [])):
            try:
                lon_new, lat_new = snapshot_pixel_to_lonlat(
                    coords['x'], coords['y'], 
                    map_center[::-1], map_zoom, img_w, img_h
                )
                st.session_state['processes'][placing_idx]['lat'] = lat_new
                st.session_state['processes'][placing_idx]['lon'] = lon_new
                st.success(f"Set subprocess coords to ({lat_new:.6f}, {lon_new:.6f})")
            except (ValueError, TypeError):
                st.error("Failed to set coordinates")
    
    # Handle distance measurement
    if st.session_state['measure_mode']:
        if coords and len(st.session_state['measure_points']) < 2:
            st.session_state['measure_points'].append((coords['x'], coords['y']))
        st.session_state['measure_points'] = st.session_state['measure_points'][-2:]
    
    # Compute distance if two points selected
    if len(st.session_state['measure_points']) == 2:
        x1, y1 = st.session_state['measure_points'][0]
        x2, y2 = st.session_state['measure_points'][1]
        
        lon1, lat1 = snapshot_pixel_to_lonlat(x1, y1, map_center[::-1], map_zoom, img_w, img_h)
        lon2, lat2 = snapshot_pixel_to_lonlat(x2, y2, map_center[::-1], map_zoom, img_w, img_h)
        
        distance_m = haversine(lat1, lon1, lat2, lon2)
        st.session_state['measure_distance_m'] = distance_m


if __name__ == "__main__":
    main()
