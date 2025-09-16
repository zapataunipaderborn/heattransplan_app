"""
Session state management for the Heat Integration Analysis app.
"""

import streamlit as st
from config import DEFAULT_START_COORDS
from process_utils import init_process_state


def initialize_session_state():
    """Initialize all session state variables with default values."""
    # Map state
    if 'map_locked' not in st.session_state:
        st.session_state['map_locked'] = False
    if 'map_snapshot' not in st.session_state:
        st.session_state['map_snapshot'] = None
    if 'map_snapshots' not in st.session_state:
        st.session_state['map_snapshots'] = {}
    if 'map_center' not in st.session_state:
        st.session_state['map_center'] = DEFAULT_START_COORDS[:]
    if 'map_zoom' not in st.session_state:
        st.session_state['map_zoom'] = 17.5
    if 'selector_center' not in st.session_state:
        st.session_state['selector_center'] = st.session_state['map_center'][:]
    if 'selector_zoom' not in st.session_state:
        st.session_state['selector_zoom'] = st.session_state['map_zoom']
    
    # Base layer preferences
    if 'map_base_choice' not in st.session_state:
        st.session_state['map_base_choice'] = 'OpenStreetMap'
    if 'analyze_base_choice' not in st.session_state:
        st.session_state['analyze_base_choice'] = 'OpenStreetMap'
    if 'current_base' not in st.session_state:
        st.session_state['current_base'] = 'OpenStreetMap'
    if 'analyze_base_layer' not in st.session_state:
        st.session_state['analyze_base_layer'] = 'OpenStreetMap'
    
    # UI state
    if 'ui_mode_radio' not in st.session_state:
        st.session_state['ui_mode_radio'] = 'Select Map'
    if 'address_input' not in st.session_state:
        st.session_state['address_input'] = ''
    if 'ui_status_msg' not in st.session_state:
        st.session_state['ui_status_msg'] = None
    
    # Interaction modes
    if 'measure_mode' not in st.session_state:
        st.session_state['measure_mode'] = False
    if 'measure_points' not in st.session_state:
        st.session_state['measure_points'] = []
    if 'measure_distance_m' not in st.session_state:
        st.session_state['measure_distance_m'] = None
    if 'placement_mode' not in st.session_state:
        st.session_state['placement_mode'] = False
    if 'placing_process_idx' not in st.session_state:
        st.session_state['placing_process_idx'] = None
    
    # Process state
    init_process_state(st.session_state)
    
    # Clean up orphaned widget state keys
    cleanup_widget_keys()


def cleanup_widget_keys():
    """Clean up orphaned internal widget state keys."""
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith('$$WIDGET_ID-'):
            try:
                del st.session_state[key]
            except KeyError:
                pass


def reset_measurement_state():
    """Reset measurement-related session state."""
    st.session_state['measure_mode'] = False
    st.session_state['measure_points'] = []
    st.session_state['measure_distance_m'] = None


def reset_placement_state():
    """Reset placement-related session state."""
    st.session_state['placement_mode'] = False
    st.session_state['placing_process_idx'] = None


def update_map_state(center, zoom):
    """Update map center and zoom in session state."""
    st.session_state['map_center'] = center[:]
    st.session_state['map_zoom'] = zoom


def should_regenerate_snapshots(center, zoom, base_layer):
    """
    Check if map snapshots need to be regenerated.
    
    Args:
        center: Current map center
        zoom: Current zoom level
        base_layer: Selected base layer
        
    Returns:
        bool: True if snapshots should be regenerated
    """
    existing_snaps = st.session_state.get('map_snapshots', {})
    return (
        (st.session_state.get('map_snapshot') is None) or
        (center != st.session_state.get('map_center')) or
        (zoom != st.session_state.get('map_zoom')) or
        (base_layer not in existing_snaps)
    )
