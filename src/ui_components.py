"""
UI components and styling for the Heat Integration Analysis app.
"""

import streamlit as st


def apply_custom_css():
    """Apply custom CSS styling to the Streamlit app."""
    st.markdown("""
    <style>
    /* Base tweaks */
    .block-container {padding-top:0.6rem; padding-bottom:0.5rem;}
    div[data-testid="column"] > div:has(> div.map-region) {margin-top:0;}
    .map-control-row {margin-bottom:0.25rem;}

    /* Responsive typography & control sizing */
    @media (max-width: 1500px){
        html, body, .stApp {font-size:14px;}
        .stMarkdown p, .stMarkdown span, .stMarkdown li {font-size:14px !important;}
        .stButton button {font-size:13px !important; padding:0.25rem 0.55rem !important;}
        .stTextInput input, .stNumberInput input {font-size:13px !important; padding:0.25rem 0.4rem !important;}
        .stRadio > div[role=radio] label {font-size:13px !important;}
    }
    @media (max-width: 1200px){
        html, body, .stApp {font-size:13px;}
        .stMarkdown p, .stMarkdown span, .stMarkdown li {font-size:13px !important;}
        .stButton button {font-size:12px !important;}
        .stTextInput input, .stNumberInput input {font-size:12px !important;}
    }
    @media (max-width: 1000px){
        html, body, .stApp {font-size:12px;}
        .stMarkdown p, .stMarkdown span, .stMarkdown li {font-size:12px !important;}
        .stButton button {font-size:11px !important; padding:0.2rem 0.45rem !important;}
        .stTextInput input, .stNumberInput input {font-size:11px !important; padding:0.2rem 0.35rem !important;}
        .stDataFrame, .stDataFrame table {font-size:11px !important;}
    }

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

    /* Tighter expander headers */
    div.streamlit-expanderHeader {padding:0.3rem 0.5rem !important;}
    /* Group boxed layout */
    .group-box {border:2px solid #ffffff; padding:6px 8px 8px 8px; margin:10px 0 16px 0; border-radius:6px; background:rgba(255,255,255,0.04);} 
    .group-box.collapsed {padding-bottom:4px;}

    /* Compact selectboxes */
    div[data-testid="stVerticalBlock"] > div div[data-baseweb="select"] {min-height:32px;}
    div[data-testid="stVerticalBlock"] > div div[data-baseweb="select"] * {font-size:11px;}
    div[data-testid="stVerticalBlock"] > div div[data-baseweb="select"] div[role="combobox"] {padding:2px 6px;}
    </style>
    """, unsafe_allow_html=True)


def create_base_layer_selector(key_suffix="", label="Base layer", current_base="OpenStreetMap"):
    """
    Create a base layer selector widget.
    
    Args:
        key_suffix: Suffix for the widget key
        label: Label for the selector
        current_base: Currently selected base layer
        
    Returns:
        str: Selected base layer
    """
    from config import BASE_OPTIONS
    
    if current_base not in BASE_OPTIONS:
        current_base = 'OpenStreetMap'
    
    return st.selectbox(
        label=label,
        options=BASE_OPTIONS,
        index=BASE_OPTIONS.index(current_base),
        key=f'base_selector_{key_suffix}',
        label_visibility='collapsed'
    )


def create_status_bar(placing_mode, placing_idx, measure_mode, measure_points, 
                     dist_val, last_msg, processes):
    """
    Create a dynamic status bar showing current operation status.
    
    Args:
        placing_mode: Whether in placement mode
        placing_idx: Index of process being placed
        measure_mode: Whether in measurement mode
        measure_points: List of measurement points
        dist_val: Measured distance value
        last_msg: Last status message
        processes: List of processes
    """
    if placing_mode and placing_idx is not None and 0 <= placing_idx < len(processes):
        pname = processes[placing_idx].get('name') or f"P{placing_idx+1}"
        st.info(f"Placing subprocess: {pname} (Double click on map)")
    elif measure_mode:
        if dist_val is not None:
            st.success(f"Distance: {dist_val:.2f} m ({dist_val/1000:.3f} km)")
        else:
            st.info(f"Measuring distance: select {2-len(measure_points)} more point(s)")
    elif last_msg:
        st.success(last_msg)
    else:
        st.info("Snapshot locked")


def create_process_header(process, index):
    """
    Create a process header with toggle, name, size, place, and delete controls.
    
    Args:
        process: Process data dictionary
        index: Process index
        
    Returns:
        tuple: (expanded, place_active)
    """
    header_cols = st.columns([0.06, 0.54, 0.14, 0.16, 0.10])
    
    # Toggle button
    expanded = st.session_state.get('proc_expanded', [False] * (index + 1))[index]
    toggle_label = "▾" if expanded else "▸"
    if header_cols[0].button(toggle_label, key=f"proc_toggle_{index}"):
        if 'proc_expanded' not in st.session_state:
            st.session_state['proc_expanded'] = [False] * (index + 1)
        st.session_state['proc_expanded'][index] = not expanded
        st.rerun()
    
    # Name input
    if not process.get('name'):
        process['name'] = f"Subprocess {index+1}"
    process['name'] = header_cols[1].text_input(
        "Subprocess name",
        value=process.get('name', ''),
        key=f"p_name_{index}",
        label_visibility="collapsed",
        placeholder=f"Subprocess {index+1}"
    )
    
    # Size slider
    if 'box_scale' not in process or process.get('box_scale') in (None, ''):
        process['box_scale'] = 1.0
    process['box_scale'] = header_cols[2].slider(
        "Size",
        min_value=0.5,
        max_value=3.0,
        value=float(process.get('box_scale', 1.0)),
        step=0.1,
        key=f"p_box_scale_{index}",
        label_visibility="collapsed"
    )
    
    # Place/Done button
    place_active = (st.session_state.get('placement_mode') and 
                   st.session_state.get('placing_process_idx') == index)
    
    if not place_active:
        if header_cols[3].button("Place", key=f"place_{index}"):
            st.session_state['placement_mode'] = True
            st.session_state['measure_mode'] = False
            st.session_state['placing_process_idx'] = index
            st.rerun()
    else:
        if header_cols[3].button("Done", key=f"done_place_{index}"):
            st.session_state['placement_mode'] = False
            st.session_state['placing_process_idx'] = None
            st.rerun()
    
    # Delete button
    if header_cols[4].button("✕", key=f"del_proc_{index}"):
        from process_utils import delete_process
        delete_process(st.session_state, index)
        st.rerun()
    
    return expanded, place_active
