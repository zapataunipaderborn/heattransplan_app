import streamlit as st

st.set_page_config(
    page_title="Potential Analysis",
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
    
    /* Smaller fonts and elements - apply to all elements */
    html, body, .stApp, * {font-size:11px !important;}
    .stMarkdown p, .stMarkdown span, .stMarkdown li {font-size:11px !important;}
    .stButton button {font-size:10px !important; padding:0.1rem 0.3rem !important;}
    .stTextInput input, .stNumberInput input {font-size:10px !important; padding:0.1rem 0.2rem !important;}
    h1 {font-size: 1.5rem !important; margin-bottom: 0.3rem !important;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Potential Analysis")

st.markdown(
    """
Select the streams and products you want to include in the analysis.
"""
)

# Initialize session state for selections if not exists
if 'selected_items' not in st.session_state:
    st.session_state['selected_items'] = {}

# Get processes from session state
processes = st.session_state.get('processes', [])

if not processes:
    st.info("No processes found. Please add processes in the Data Collection page first.")
else:
    # Display each process and its streams/products in compact format
    for idx, process in enumerate(processes):
        process_name = process.get('name', f'Subprocess {idx + 1}')
        
        st.markdown(f"**{process_name}**")
        
        # Product data section - compact single line
        product_key = f"product_{idx}"
        if product_key not in st.session_state['selected_items']:
            st.session_state['selected_items'][product_key] = False
        
        product_cols = st.columns([0.05, 0.15, 0.8])
        product_selected = product_cols[0].checkbox(
            "P",
            key=f"cb_{product_key}",
            value=st.session_state['selected_items'][product_key],
            label_visibility="collapsed"
        )
        st.session_state['selected_items'][product_key] = product_selected
        product_cols[1].write("Product")
        
        # Display product data inline
        product_info = []
        if process.get('conntemp'):
            product_info.append(f"Tin:{process['conntemp']}")
        if process.get('product_tout'):
            product_info.append(f"Tout:{process['product_tout']}")
        if process.get('connm'):
            product_info.append(f"ṁ:{process['connm']}")
        if process.get('conncp'):
            product_info.append(f"cp:{process['conncp']}")
        
        if product_info:
            product_cols[2].caption(' | '.join(product_info))
        else:
            product_cols[2].caption("(no data)")
        
        # Streams section - compact
        streams = process.get('streams', [])
        if streams:
            for stream_idx, stream in enumerate(streams):
                stream_key = f"stream_{idx}_{stream_idx}"
                if stream_key not in st.session_state['selected_items']:
                    st.session_state['selected_items'][stream_key] = False
                
                stream_cols = st.columns([0.05, 0.15, 0.8])
                stream_selected = stream_cols[0].checkbox(
                    "S",
                    key=f"cb_{stream_key}",
                    value=st.session_state['selected_items'][stream_key],
                    label_visibility="collapsed"
                )
                st.session_state['selected_items'][stream_key] = stream_selected
                # Display stream data inline
                stream_name = stream.get('name', f'Stream {stream_idx + 1}')
                stream_cols[1].write(stream_name)
                
                # Handle new stream structure with flexible properties
                properties = stream.get('properties', [])
                values = stream.get('values', [])
                
                if properties and values and len(properties) == len(values):
                    # New structure: display property-value pairs
                    stream_info = []
                    for prop, val in zip(properties, values):
                        if val:  # Only show non-empty values
                            if prop in ['Tin', 'Tout']:
                                stream_info.append(f"{prop}:{val}")
                            elif prop == 'ṁ':
                                stream_info.append(f"ṁ:{val}")
                            elif prop == 'cp':
                                stream_info.append(f"cp:{val}")
                            else:
                                stream_info.append(f"{prop}:{val}")
                    
                    if stream_info:
                        stream_cols[2].caption(' | '.join(stream_info))
                    else:
                        stream_cols[2].caption("(no data)")
                else:
                    # Legacy structure: fallback to old fields
                    stream_info = []
                    if stream.get('temp_in'):
                        stream_info.append(f"Tin:{stream['temp_in']}")
                    if stream.get('temp_out'):
                        stream_info.append(f"Tout:{stream['temp_out']}")
                    if stream.get('mdot'):
                        stream_info.append(f"ṁ:{stream['mdot']}")
                    if stream.get('cp'):
                        stream_info.append(f"cp:{stream['cp']}")
                    
                    if stream_info:
                        stream_cols[2].caption(' | '.join(stream_info))
                    else:
                        stream_cols[2].caption("(no data)")
        
        st.divider()
    
    # Summary section
    st.markdown("### Selection Summary")
    selected_count = sum(1 for v in st.session_state['selected_items'].values() if v)
    st.write(f"**Total items selected: {selected_count}**")
    
    if selected_count > 0:
        st.markdown("**Selected items:**")
        for key, selected in st.session_state['selected_items'].items():
            if selected:
                # Parse key to display friendly name
                if key.startswith("product_"):
                    proc_idx = int(key.split("_")[1])
                    proc_name = processes[proc_idx].get('name', f'Subprocess {proc_idx + 1}')
                    st.write(f"- {proc_name} - Product")
                elif key.startswith("stream_"):
                    parts = key.split("_")
                    proc_idx = int(parts[1])
                    stream_idx = int(parts[2])
                    proc_name = processes[proc_idx].get('name', f'Subprocess {proc_idx + 1}')
                    st.write(f"- {proc_name} - Stream {stream_idx + 1}")
