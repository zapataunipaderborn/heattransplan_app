import streamlit as st
import sys
import os
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import tempfile
import csv
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import math

# Add the pinch_tool directory to the path for imports
pinch_tool_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'pinch_tool'))
if pinch_tool_path not in sys.path:
    sys.path.insert(0, pinch_tool_path)

# Import pinch analysis modules
try:
    from Modules.Pinch.Pinch import Pinch
    PINCH_AVAILABLE = True
    PINCH_IMPORT_ERROR = None
except ImportError as e:
    PINCH_AVAILABLE = False
    PINCH_IMPORT_ERROR = str(e)

st.set_page_config(
    page_title="Potential Analysis",
    initial_sidebar_state="collapsed",
    layout="wide"
)

# Helper function to convert lon/lat to pixel coordinates on snapshot
def snapshot_lonlat_to_pixel(lon_val_in, lat_val_in, center_ll, z_level, img_w, img_h):
    def lonlat_to_xy(lon_inner, lat_inner, z_val):
        lat_rad = math.radians(lat_inner)
        n_val = 2.0 ** z_val
        xtile = (lon_inner + 180.0) / 360.0 * n_val
        ytile = (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n_val
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
    .stMarkdown p, .stMarkdown span, .stMarkdown li {font-size:11px !important; margin:0 !important; padding:0 !important;}
    .stButton button {font-size:10px !important; padding:0.1rem 0.3rem !important;}
    .stTextInput input, .stNumberInput input {font-size:10px !important; padding:0.1rem 0.2rem !important;}
    h1 {font-size: 1.5rem !important; margin-bottom: 0.3rem !important;}
    /* Compact layout */
    .block-container {padding-top: 1rem !important; padding-bottom: 0 !important;}
    div[data-testid="stVerticalBlock"] > div {padding: 0 !important; margin: 0 !important;}
    hr {margin: 0.3rem 0 !important;}
    .stCheckbox {margin: 0 !important; padding: 0 !important;}
    div[data-testid="stHorizontalBlock"] {gap: 0.2rem !important;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Potential Analysis")

# =====================================================
# HELPER FUNCTION: Generate mini-map with kW circles for each STREAM
# =====================================================
def generate_stream_kw_minimap(processes, map_snapshot, map_center, map_zoom, max_width=500, max_height=400):
    """
    Generate a mini-map image showing each stream as a circle sized by kW.
    Streams are positioned near their parent subprocess location.
    Returns a PIL Image or None if no snapshot available.
    """
    if not map_snapshot:
        return None
    
    try:
        # Load the base map snapshot
        base_img = Image.open(BytesIO(map_snapshot)).convert("RGBA")
        orig_w, orig_h = base_img.size
        
        # Calculate scale to fit within max dimensions while maintaining aspect ratio
        scale = min(max_width / orig_w, max_height / orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        
        # Resize the base image
        base_img = base_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Create drawing context
        draw = ImageDraw.Draw(base_img)
        
        # Try to load a font
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 11)
            font_small = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 9)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 11)
                font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 9)
            except (OSError, IOError):
                font = ImageFont.load_default()
                font_small = font
        
        # Collect all streams with their kW values and positions
        all_streams = []
        
        for proc_idx, subprocess in enumerate(processes):
            sub_lat = subprocess.get('lat')
            sub_lon = subprocess.get('lon')
            subprocess_name = subprocess.get('name', f'Subprocess {proc_idx + 1}')
            
            streams = subprocess.get('streams', [])
            
            for s_idx, stream in enumerate(streams):
                stream_name = stream.get('name', f'Stream {s_idx + 1}')
                
                # Extract stream data
                props = stream.get('properties', {})
                vals = stream.get('values', {})
                
                tin = None
                tout = None
                mdot = None
                cp_val = None
                
                if isinstance(props, dict) and isinstance(vals, dict):
                    for pk, pname in props.items():
                        vk = pk.replace('prop', 'val')
                        v = vals.get(vk, '')
                        
                        if pname == 'Tin' and v:
                            try:
                                tin = float(v)
                            except (ValueError, TypeError):
                                pass
                        elif pname == 'Tout' and v:
                            try:
                                tout = float(v)
                            except (ValueError, TypeError):
                                pass
                        elif pname == 'ṁ' and v:
                            try:
                                mdot = float(v)
                            except (ValueError, TypeError):
                                pass
                        elif pname == 'cp' and v:
                            try:
                                cp_val = float(v)
                            except (ValueError, TypeError):
                                pass
                
                # Fallback to legacy fields
                if tin is None and stream.get('temp_in'):
                    try:
                        tin = float(stream['temp_in'])
                    except (ValueError, TypeError):
                        pass
                if tout is None and stream.get('temp_out'):
                    try:
                        tout = float(stream['temp_out'])
                    except (ValueError, TypeError):
                        pass
                if mdot is None and stream.get('mdot'):
                    try:
                        mdot = float(stream['mdot'])
                    except (ValueError, TypeError):
                        pass
                if cp_val is None and stream.get('cp'):
                    try:
                        cp_val = float(stream['cp'])
                    except (ValueError, TypeError):
                        pass
                
                # Calculate kW = mdot * cp * |ΔT|
                stream_kw = 0.0
                is_hot = None
                if tin is not None and tout is not None and mdot is not None and cp_val is not None:
                    delta_t = abs(tin - tout)
                    stream_kw = mdot * cp_val * delta_t
                    is_hot = tin > tout  # True = HOT (cooling), False = COLD (heating)
                
                all_streams.append({
                    'proc_idx': proc_idx,
                    'stream_idx': s_idx,
                    'subprocess_name': subprocess_name,
                    'stream_name': stream_name,
                    'lat': sub_lat,
                    'lon': sub_lon,
                    'kw': stream_kw,
                    'is_hot': is_hot,
                    'tin': tin,
                    'tout': tout
                })
        
        # Find max kW for scaling circle sizes
        kw_values = [s['kw'] for s in all_streams if s['kw'] > 0]
        max_kw = max(kw_values) if kw_values else 1.0
        if max_kw == 0:
            max_kw = 1.0
        
        # Group streams by subprocess for positioning
        subprocess_streams = {}
        for s in all_streams:
            key = s['proc_idx']
            if key not in subprocess_streams:
                subprocess_streams[key] = []
            subprocess_streams[key].append(s)
        
        # Draw circles for each stream
        for proc_idx, streams_list in subprocess_streams.items():
            if not streams_list:
                continue
            
            # Get subprocess position
            first_stream = streams_list[0]
            lat = first_stream['lat']
            lon = first_stream['lon']
            
            if lat is None or lon is None:
                continue
            
            try:
                lat_f = float(lat)
                lon_f = float(lon)
                
                # Convert to pixel coordinates (on original size, then scale)
                base_px, base_py = snapshot_lonlat_to_pixel(
                    lon_f, lat_f,
                    (map_center[1], map_center[0]),
                    map_zoom,
                    orig_w, orig_h
                )
                
                # Scale to new dimensions
                base_px = base_px * scale
                base_py = base_py * scale
                
                # Skip if outside bounds
                if base_px < -50 or base_py < -50 or base_px > new_w + 50 or base_py > new_h + 50:
                    continue
                
                # Draw subprocess name first
                subprocess_name = first_stream['subprocess_name']
                if font:
                    bbox = draw.textbbox((0, 0), subprocess_name, font=font)
                    tw = bbox[2] - bbox[0]
                    th = bbox[3] - bbox[1]
                else:
                    tw = len(subprocess_name) * 6
                    th = 10
                
                # Draw subprocess label above streams
                label_x = int(base_px - tw / 2)
                label_y = int(base_py - 50)
                draw.rectangle([label_x - 3, label_y - 2, label_x + tw + 3, label_y + th + 2], 
                              fill=(255, 255, 255, 230), outline=(100, 100, 100, 200))
                draw.text((label_x, label_y), subprocess_name, fill=(0, 0, 0, 255), font=font)
                
                # Position streams in a row below the label
                n_streams = len(streams_list)
                stream_spacing = 45  # pixels between stream circles
                start_x = base_px - (n_streams - 1) * stream_spacing / 2
                
                for i, stream_data in enumerate(streams_list):
                    px = start_x + i * stream_spacing
                    py = base_py
                    
                    kw = stream_data['kw']
                    is_hot = stream_data['is_hot']
                    
                    # Calculate circle radius based on kW (min 12, max 35 pixels)
                    if kw > 0:
                        radius = 12 + (kw / max_kw) * 23
                    else:
                        radius = 10
                    
                    # Determine color based on hot/cold
                    if is_hot is True:
                        fill_color = (255, 80, 80, 220)  # Red for HOT
                        border_color = (180, 30, 30, 255)
                    elif is_hot is False:
                        fill_color = (80, 140, 255, 220)  # Blue for COLD
                        border_color = (30, 80, 180, 255)
                    else:
                        fill_color = (180, 180, 180, 180)  # Gray for unknown
                        border_color = (120, 120, 120, 220)
                    
                    # Draw circle
                    x0 = int(px - radius)
                    y0 = int(py - radius)
                    x1 = int(px + radius)
                    y1 = int(py + radius)
                    
                    draw.ellipse([x0, y0, x1, y1], fill=fill_color, outline=border_color, width=2)
                    
                    # Draw kW label inside circle
                    if kw > 0:
                        kw_text = f"{kw:.0f}"
                        if font_small:
                            bbox = draw.textbbox((0, 0), kw_text, font=font_small)
                            text_w = bbox[2] - bbox[0]
                            text_h = bbox[3] - bbox[1]
                        else:
                            text_w = len(kw_text) * 5
                            text_h = 8
                        
                        tx = int(px - text_w / 2)
                        ty = int(py - text_h / 2)
                        
                        # White text for visibility
                        draw.text((tx, ty), kw_text, fill=(255, 255, 255, 255), font=font_small)
                    
                    # Draw stream name below circle
                    stream_name = stream_data['stream_name']
                    if font_small:
                        bbox = draw.textbbox((0, 0), stream_name, font=font_small)
                        name_w = bbox[2] - bbox[0]
                        name_h = bbox[3] - bbox[1]
                    else:
                        name_w = len(stream_name) * 5
                        name_h = 8
                    
                    name_x = int(px - name_w / 2)
                    name_y = int(py + radius + 4)
                    
                    draw.rectangle([name_x - 2, name_y - 1, name_x + name_w + 2, name_y + name_h + 1], 
                                  fill=(255, 255, 255, 220))
                    draw.text((name_x, name_y), stream_name, fill=(0, 0, 0, 255), font=font_small)
                    
            except (ValueError, TypeError):
                continue
        
        # Add legend in top-left corner
        legend_x = 10
        legend_y = 10
        legend_w = 70
        legend_h = 55
        
        # Legend background
        draw.rectangle([legend_x, legend_y, legend_x + legend_w, legend_y + legend_h], 
                      fill=(255, 255, 255, 240), outline=(150, 150, 150, 200))
        
        # Legend title
        draw.text((legend_x + 5, legend_y + 3), "kW", fill=(0, 0, 0, 255), font=font)
        
        # Hot indicator
        draw.ellipse([legend_x + 5, legend_y + 20, legend_x + 17, legend_y + 32], 
                     fill=(255, 80, 80, 220), outline=(180, 30, 30, 255), width=1)
        draw.text((legend_x + 22, legend_y + 21), "Hot", fill=(0, 0, 0, 255), font=font_small)
        
        # Cold indicator
        draw.ellipse([legend_x + 5, legend_y + 37, legend_x + 17, legend_y + 49], 
                     fill=(80, 140, 255, 220), outline=(30, 80, 180, 255), width=1)
        draw.text((legend_x + 22, legend_y + 38), "Cold", fill=(0, 0, 0, 255), font=font_small)
        
        return base_img
        
    except Exception as e:
        return None

# Initialize session state for selections if not exists
if 'selected_items' not in st.session_state:
    st.session_state['selected_items'] = {}

# Get processes from session state
processes = st.session_state.get('processes', [])

if not processes:
    st.info("No processes found. Please add processes in the Data Collection page first.")
else:
    # Helper function to determine stream type and extract data
    def get_stream_info(stream):
        """Extract Tin, Tout, mdot, cp from stream and determine if HOT or COLD"""
        properties = stream.get('properties', {})
        values = stream.get('values', {})
        
        tin = None
        tout = None
        mdot = None
        cp_val = None
        
        # Check properties dict structure
        if isinstance(properties, dict) and isinstance(values, dict):
            for pk, pname in properties.items():
                vk = pk.replace('prop', 'val')
                v = values.get(vk, '')
                
                if pname == 'Tin' and v:
                    try:
                        tin = float(v)
                    except (ValueError, TypeError):
                        pass
                elif pname == 'Tout' and v:
                    try:
                        tout = float(v)
                    except (ValueError, TypeError):
                        pass
                elif pname == 'ṁ' and v:
                    try:
                        mdot = float(v)
                    except (ValueError, TypeError):
                        pass
                elif pname == 'cp' and v:
                    try:
                        cp_val = float(v)
                    except (ValueError, TypeError):
                        pass
        
        # Fallback to legacy fields
        if tin is None and stream.get('temp_in'):
            try:
                tin = float(stream['temp_in'])
            except (ValueError, TypeError):
                pass
        if tout is None and stream.get('temp_out'):
            try:
                tout = float(stream['temp_out'])
            except (ValueError, TypeError):
                pass
        if mdot is None and stream.get('mdot'):
            try:
                mdot = float(stream['mdot'])
            except (ValueError, TypeError):
                pass
        if cp_val is None and stream.get('cp'):
            try:
                cp_val = float(stream['cp'])
            except (ValueError, TypeError):
                pass
        
        # Determine stream type
        stream_type = None
        if tin is not None and tout is not None:
            if tin > tout:
                stream_type = "HOT"
            else:
                stream_type = "COLD"
        
        # Calculate CP if possible
        cp_flow = None
        if mdot is not None and cp_val is not None:
            cp_flow = mdot * cp_val
        
        # Calculate kW = mdot * cp * |ΔT|
        kw = None
        if tin is not None and tout is not None and mdot is not None and cp_val is not None:
            kw = mdot * cp_val * abs(tin - tout)
        
        return {
            'tin': tin,
            'tout': tout,
            'mdot': mdot,
            'cp': cp_val,
            'CP': cp_flow,
            'kW': kw,
            'type': stream_type
        }
    
    # =====================================================
    # TWO-COLUMN LAYOUT: Stream Selection (left) + Map (right)
    # =====================================================
    stream_col, map_col = st.columns([1, 1.2])
    
    with stream_col:
        st.markdown("**Select streams for analysis:**")
        
        # Display each process and its streams
        for idx, process in enumerate(processes):
            process_name = process.get('name', f'Subprocess {idx + 1}')
            
            # Only show process header if it has streams
            streams = process.get('streams', [])
            if streams:
                st.markdown(f"**{process_name}**")
                
                for stream_idx, stream in enumerate(streams):
                    stream_key = f"stream_{idx}_{stream_idx}"
                    if stream_key not in st.session_state['selected_items']:
                        st.session_state['selected_items'][stream_key] = False
                    
                    stream_cols = st.columns([0.05, 0.20, 0.75])
                    stream_selected = stream_cols[0].checkbox(
                        "S",
                        key=f"cb_{stream_key}",
                        value=st.session_state['selected_items'][stream_key],
                        label_visibility="collapsed"
                    )
                    st.session_state['selected_items'][stream_key] = stream_selected
                    
                    # Display stream name
                    stream_name = stream.get('name', f'Stream {stream_idx + 1}')
                    stream_cols[1].write(stream_name)
                    
                    # Get stream info and display type + key values
                    info = get_stream_info(stream)
                    
                    display_parts = []
                    if info['tin'] is not None:
                        display_parts.append(f"Tin:{info['tin']}°C")
                    if info['tout'] is not None:
                        display_parts.append(f"Tout:{info['tout']}°C")
                    if info['kW'] is not None:
                        display_parts.append(f"**{info['kW']:.0f} kW**")
                    
                    if info['type']:
                        type_color = "🔴" if info['type'] == "HOT" else "🔵"
                        display_parts.append(f"{type_color} {info['type']}")
                    
                    if display_parts:
                        stream_cols[2].caption(' | '.join(display_parts))
                    else:
                        stream_cols[2].caption("(incomplete data)")
    
    with map_col:
        st.markdown("**Energy Map Overview (circle size = kW):**")
        
        # Generate and display mini-map with kW circles for each stream
        map_snapshot = st.session_state.get('map_snapshot')
        map_snapshots = st.session_state.get('map_snapshots', {})
        current_base = st.session_state.get('current_base', 'OpenStreetMap')
        
        # Use the appropriate snapshot based on current base layer
        if current_base in map_snapshots:
            snapshot_to_use = map_snapshots[current_base]
        else:
            snapshot_to_use = map_snapshot
        
        map_center = st.session_state.get('map_center', [51.708, 8.772])
        map_zoom = st.session_state.get('map_zoom', 17.5)
        
        if snapshot_to_use:
            minimap_img = generate_stream_kw_minimap(
                processes=processes,
                map_snapshot=snapshot_to_use,
                map_center=map_center,
                map_zoom=map_zoom,
                max_width=600,
                max_height=450
            )
            
            if minimap_img:
                st.image(minimap_img)
            else:
                st.caption("📍 Could not generate map preview")
        else:
            st.info("📍 Lock the map in Data Collection page first to see the energy overview.")
    
    # Count selected streams
    selected_count = sum(1 for k, v in st.session_state['selected_items'].items() 
                         if v and k.startswith("stream_"))
    
    # =====================================================
    # PINCH ANALYSIS SECTION
    # =====================================================
    st.markdown("---")
    
    if not PINCH_AVAILABLE:
        st.error(f"Pinch analysis module not available: {PINCH_IMPORT_ERROR or 'Unknown error'}")
        st.info("Please ensure the pinch_tool module is properly installed.")
    else:
        # Helper function to extract stream data from selection
        def extract_stream_data(procs, sel_items):
            """
            Extract stream data from selected items.
            Returns list of dicts with: CP (calculated as mdot * cp), Tin, Tout
            """
            result_streams = []
            
            for sel_key, is_sel in sel_items.items():
                if not is_sel:
                    continue
                    
                if sel_key.startswith("stream_"):
                    parts_split = sel_key.split("_")
                    p_idx = int(parts_split[1])
                    s_idx = int(parts_split[2])
                    
                    if p_idx < len(procs):
                        proc = procs[p_idx]
                        proc_streams = proc.get('streams', [])
                        
                        if s_idx < len(proc_streams):
                            strm = proc_streams[s_idx]
                            
                            # Extract values from properties/values structure
                            props = strm.get('properties', {})
                            vals = strm.get('values', {})
                            
                            tin = None
                            tout = None
                            mdot = None
                            cp_val = None
                            
                            # Check properties dict structure
                            if isinstance(props, dict) and isinstance(vals, dict):
                                for pk, pname in props.items():
                                    vk = pk.replace('prop', 'val')
                                    v = vals.get(vk, '')
                                    
                                    if pname == 'Tin' and v:
                                        try:
                                            tin = float(v)
                                        except (ValueError, TypeError):
                                            pass
                                    elif pname == 'Tout' and v:
                                        try:
                                            tout = float(v)
                                        except (ValueError, TypeError):
                                            pass
                                    elif pname == 'ṁ' and v:
                                        try:
                                            mdot = float(v)
                                        except (ValueError, TypeError):
                                            pass
                                    elif pname == 'cp' and v:
                                        try:
                                            cp_val = float(v)
                                        except (ValueError, TypeError):
                                            pass
                            
                            # Fallback to legacy fields
                            if tin is None and strm.get('temp_in'):
                                try:
                                    tin = float(strm['temp_in'])
                                except (ValueError, TypeError):
                                    pass
                            if tout is None and strm.get('temp_out'):
                                try:
                                    tout = float(strm['temp_out'])
                                except (ValueError, TypeError):
                                    pass
                            if mdot is None and strm.get('mdot'):
                                try:
                                    mdot = float(strm['mdot'])
                                except (ValueError, TypeError):
                                    pass
                            if cp_val is None and strm.get('cp'):
                                try:
                                    cp_val = float(strm['cp'])
                                except (ValueError, TypeError):
                                    pass
                            
                            # Calculate CP = mdot * cp
                            if tin is not None and tout is not None and mdot is not None and cp_val is not None:
                                CP = mdot * cp_val
                                strm_name = strm.get('name', f'Stream {s_idx + 1}')
                                proc_nm = proc.get('name', f'Subprocess {p_idx + 1}')
                                result_streams.append({
                                    'name': f"{proc_nm} - {strm_name}",
                                    'CP': CP,
                                    'Tin': tin,
                                    'Tout': tout
                                })
            
            return result_streams
        
        # Helper function to run pinch analysis
        def run_pinch_analysis(strm_data, delta_tmin):
            """
            Run pinch analysis on the given stream data.
            Returns the Pinch object with results.
            """
            # Create a temporary CSV file with the stream data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Tmin', str(delta_tmin)])
                writer.writerow(['CP', 'TSUPPLY', 'TTARGET'])
                
                for strm in strm_data:
                    writer.writerow([strm['CP'], strm['Tin'], strm['Tout']])
                
                temp_csv_path = f.name
            
            try:
                # Run pinch analysis without drawing (we'll draw ourselves)
                pinch_obj = Pinch(temp_csv_path, options={})
                pinch_obj.shiftTemperatures()
                pinch_obj.constructTemperatureInterval()
                pinch_obj.constructProblemTable()
                pinch_obj.constructHeatCascade()
                pinch_obj.constructShiftedCompositeDiagram('EN')
                pinch_obj.constructCompositeDiagram('EN')
                pinch_obj.constructGrandCompositeCurve('EN')
                
                return pinch_obj
            finally:
                # Clean up temp file
                os.unlink(temp_csv_path)
        
        # Extract stream data from selections
        streams_data = extract_stream_data(processes, st.session_state['selected_items'])
        
        if len(streams_data) < 2:
            st.info("Select at least 2 streams with complete data (Tin, Tout, ṁ, cp) to run pinch analysis.")
            
            # Show what data is missing for selected streams
            if selected_count > 0:
                st.markdown("**Data status for selected items:**")
                for sel_key, is_sel in st.session_state['selected_items'].items():
                    if not is_sel:
                        continue
                    if sel_key.startswith("stream_"):
                        parts_split = sel_key.split("_")
                        p_idx = int(parts_split[1])
                        s_idx = int(parts_split[2])
                        
                        if p_idx < len(processes):
                            proc = processes[p_idx]
                            proc_streams = proc.get('streams', [])
                            
                            if s_idx < len(proc_streams):
                                strm = proc_streams[s_idx]
                                strm_name = strm.get('name', f'Stream {s_idx + 1}')
                                proc_nm = proc.get('name', f'Subprocess {p_idx + 1}')
                                
                                # Check what data is available
                                props = strm.get('properties', {})
                                vals = strm.get('values', {})
                                
                                has_tin = False
                                has_tout = False
                                has_mdot = False
                                has_cp = False
                                
                                if isinstance(props, dict) and isinstance(vals, dict):
                                    for pk, pname in props.items():
                                        vk = pk.replace('prop', 'val')
                                        v = vals.get(vk, '')
                                        if pname == 'Tin' and v:
                                            has_tin = True
                                        elif pname == 'Tout' and v:
                                            has_tout = True
                                        elif pname == 'ṁ' and v:
                                            has_mdot = True
                                        elif pname == 'cp' and v:
                                            has_cp = True
                                
                                # Fallback to legacy
                                if not has_tin and strm.get('temp_in'):
                                    has_tin = True
                                if not has_tout and strm.get('temp_out'):
                                    has_tout = True
                                if not has_mdot and strm.get('mdot'):
                                    has_mdot = True
                                if not has_cp and strm.get('cp'):
                                    has_cp = True
                                
                                missing = []
                                if not has_tin:
                                    missing.append("Tin")
                                if not has_tout:
                                    missing.append("Tout")
                                if not has_mdot:
                                    missing.append("ṁ")
                                if not has_cp:
                                    missing.append("cp")
                                
                                if missing:
                                    st.warning(f"⚠️ {proc_nm} - {strm_name}: Missing {', '.join(missing)}")
                                else:
                                    st.success(f"✅ {proc_nm} - {strm_name}: Complete data")
        else:
            # Auto-run pinch analysis
            try:
                # Row: Shifted toggle | ΔTmin (small) | spacer | Hot Utility | Cold Utility | Pinch Temp
                toggle_col, tmin_col, spacer, metric1, metric2, metric3 = st.columns([0.6, 0.5, 0.4, 0.7, 0.7, 0.7])
                
                with toggle_col:
                    show_shifted = st.toggle("Show Shifted Composite Curves", value=False, key="shifted_toggle")
                
                with tmin_col:
                    tmin = st.number_input(
                        "ΔTmin",
                        min_value=1.0,
                        max_value=50.0,
                        value=10.0,
                        step=1.0,
                        key="tmin_input",
                        format="%.0f"
                    )
                
                pinch = run_pinch_analysis(streams_data, tmin)
                results = {
                    'hot_utility': pinch.hotUtility,
                    'cold_utility': pinch.coldUtility,
                    'pinch_temperature': pinch.pinchTemperature,
                    'tmin': pinch.tmin,
                    'composite_diagram': pinch.compositeDiagram,
                    'shifted_composite_diagram': pinch.shiftedCompositeDiagram,
                    'grand_composite_curve': pinch.grandCompositeCurve,
                    'heat_cascade': pinch.heatCascade,
                    'unfeasible_heat_cascade': pinch.unfeasibleHeatCascade,
                    'problem_table': pinch.problemTable,
                    'temperatures': pinch._temperatures,
                    'streams': list(pinch.streams)
                }
                
                metric1.metric("Hot Utility", f"{results['hot_utility']:.2f} kW")
                metric2.metric("Cold Utility", f"{results['cold_utility']:.2f} kW")
                metric3.metric("Pinch Temp", f"{results['pinch_temperature']:.1f} °C")
                
                # Side by side plots: Composite Curves (left) and Grand Composite Curve (right)
                plot_col1, plot_col2 = st.columns(2)
                
                # Build hover text for streams
                hot_streams = [s for s in streams_data if s['Tin'] > s['Tout']]
                cold_streams = [s for s in streams_data if s['Tin'] < s['Tout']]
                
                with plot_col1:
                    fig1 = go.Figure()
                    
                    # Select which diagram to show
                    if show_shifted:
                        diagram = results['shifted_composite_diagram']
                        curve_label = "Shifted"
                        title_text = "Shifted Composite Curves"
                        # For shifted, temperatures are shifted by ±Tmin/2
                        tmin_half = results['tmin'] / 2
                    else:
                        diagram = results['composite_diagram']
                        curve_label = ""
                        title_text = "Composite Curves"
                        tmin_half = 0
                    
                    # Hot composite curve with hover info
                    hot_T = diagram['hot']['T']
                    hot_H = diagram['hot']['H']
                    
                    # Create hover text for hot curve points
                    hot_hover = []
                    for i, (h, t) in enumerate(zip(hot_H, hot_T)):
                        # Find streams at this temperature (adjust for shifted temps)
                        if show_shifted:
                            actual_t = t + tmin_half  # Convert back to actual temp
                        else:
                            actual_t = t
                        matching = [s['name'] for s in hot_streams if min(s['Tin'], s['Tout']) <= actual_t <= max(s['Tin'], s['Tout'])]
                        stream_info = '<br>'.join(matching) if matching else 'Composite'
                        label = f"<b>Hot {curve_label}</b>" if curve_label else "<b>Hot Composite</b>"
                        hot_hover.append(f"{label}<br>T: {t:.1f}°C<br>H: {h:.1f} kW<br>Streams: {stream_info}")
                    
                    fig1.add_trace(go.Scatter(
                        x=hot_H, y=hot_T,
                        mode='lines+markers',
                        name='Hot',
                        line=dict(color='red', width=2),
                        marker=dict(size=6),
                        hovertemplate='%{text}<extra></extra>',
                        text=hot_hover
                    ))
                    
                    # Cold composite curve with hover info
                    cold_T = diagram['cold']['T']
                    cold_H = diagram['cold']['H']
                    
                    # Create hover text for cold curve points
                    cold_hover = []
                    for i, (h, t) in enumerate(zip(cold_H, cold_T)):
                        if show_shifted:
                            actual_t = t - tmin_half  # Convert back to actual temp
                        else:
                            actual_t = t
                        matching = [s['name'] for s in cold_streams if min(s['Tin'], s['Tout']) <= actual_t <= max(s['Tin'], s['Tout'])]
                        stream_info = '<br>'.join(matching) if matching else 'Composite'
                        label = f"<b>Cold {curve_label}</b>" if curve_label else "<b>Cold Composite</b>"
                        cold_hover.append(f"{label}<br>T: {t:.1f}°C<br>H: {h:.1f} kW<br>Streams: {stream_info}")
                    
                    fig1.add_trace(go.Scatter(
                        x=cold_H, y=cold_T,
                        mode='lines+markers',
                        name='Cold',
                        line=dict(color='blue', width=2),
                        marker=dict(size=6),
                        hovertemplate='%{text}<extra></extra>',
                        text=cold_hover
                    ))
                    
                    # Pinch temperature line
                    fig1.add_hline(
                        y=results['pinch_temperature'],
                        line_dash='dash',
                        line_color='gray',
                        annotation_text=f"Pinch: {results['pinch_temperature']:.1f}°C",
                        annotation_position='top right'
                    )
                    
                    fig1.update_layout(
                        title=dict(text=title_text, font=dict(size=14)),
                        xaxis_title='Enthalpy H (kW)',
                        yaxis_title='Temperature T (°C)',
                        height=400,
                        margin=dict(l=60, r=20, t=40, b=50),
                        legend=dict(x=0.7, y=0.1),
                        hovermode='closest',
                        xaxis=dict(rangemode='tozero'),
                        yaxis=dict(rangemode='tozero')
                    )
                    
                    st.plotly_chart(fig1, width='stretch', key="composite_chart")
                
                with plot_col2:
                    fig2 = go.Figure()
                    
                    gcc_H = results['grand_composite_curve']['H']
                    gcc_T = results['grand_composite_curve']['T']
                    heat_cascade = results['heat_cascade']
                    temperatures = results['temperatures']
                    
                    # Create hover text for GCC points
                    gcc_hover = []
                    for i, (h, t) in enumerate(zip(gcc_H, gcc_T)):
                        if i < len(heat_cascade):
                            dh = heat_cascade[i]['deltaH']
                            region = 'Heat deficit (needs heating)' if dh > 0 else ('Heat surplus (needs cooling)' if dh < 0 else 'Balanced')
                        else:
                            region = ''
                        gcc_hover.append(f"<b>GCC</b><br>Shifted T: {t:.1f}°C<br>Net ΔH: {h:.1f} kW<br>{region}")
                    
                    # Plot GCC with color segments
                    for i in range(len(gcc_H) - 1):
                        if i < len(heat_cascade):
                            if heat_cascade[i]['deltaH'] > 0:
                                color = 'red'
                            elif heat_cascade[i]['deltaH'] < 0:
                                color = 'blue'
                            else:
                                color = 'gray'
                        else:
                            color = 'gray'
                        
                        fig2.add_trace(go.Scatter(
                            x=[gcc_H[i], gcc_H[i+1]],
                            y=[gcc_T[i], gcc_T[i+1]],
                            mode='lines+markers',
                            line=dict(color=color, width=2),
                            marker=dict(size=6, color=color),
                            hovertemplate='%{text}<extra></extra>',
                            text=[gcc_hover[i], gcc_hover[i+1] if i+1 < len(gcc_hover) else ''],
                            showlegend=False
                        ))
                    
                    # Pinch temperature line
                    fig2.add_hline(
                        y=results['pinch_temperature'],
                        line_dash='dash',
                        line_color='gray',
                        annotation_text=f"Pinch: {results['pinch_temperature']:.1f}°C",
                        annotation_position='top right'
                    )
                    
                    # Zero enthalpy line
                    fig2.add_vline(x=0, line_color='black', line_width=1, opacity=0.3)
                    
                    fig2.update_layout(
                        title=dict(text='Grand Composite Curve', font=dict(size=14)),
                        xaxis_title='Net ΔH (kW)',
                        yaxis_title='Shifted Temperature (°C)',
                        height=400,
                        margin=dict(l=60, r=20, t=40, b=50),
                        hovermode='closest',
                        yaxis=dict(rangemode='tozero')
                    )
                    
                    st.plotly_chart(fig2, width='stretch', key="gcc_chart")
                
                # More information expander
                with st.expander("More information"):
                    import pandas as pd
                    
                    
                    temps = results['temperatures']
                    pinch_streams = results['streams']
                    
                    if pinch_streams and temps:
                        fig_interval = go.Figure()
                        
                        num_streams = len(pinch_streams)
                        x_positions = [(i + 1) * 1.0 for i in range(num_streams)]
                        
                        # Draw horizontal temperature lines
                        for temperature in temps:
                            fig_interval.add_shape(
                                type="line",
                                x0=0, x1=num_streams + 1,
                                y0=temperature, y1=temperature,
                                line=dict(color="gray", width=1, dash="dot"),
                            )
                        
                        # Draw pinch temperature line
                        fig_interval.add_shape(
                            type="line",
                            x0=0, x1=num_streams + 1,
                            y0=results['pinch_temperature'], y1=results['pinch_temperature'],
                            line=dict(color="black", width=2, dash="dash"),
                        )
                        fig_interval.add_annotation(
                            x=num_streams + 0.5, y=results['pinch_temperature'],
                            text=f"Pinch: {results['pinch_temperature']:.1f}°C",
                            showarrow=False, font=dict(size=10),
                            xanchor='left'
                        )
                        
                        # Draw stream arrows
                        for i, stream in enumerate(pinch_streams):
                            ss = stream['ss']  # Shifted supply temp
                            st_temp = stream['st']  # Shifted target temp
                            stream_type = stream['type']
                            x_pos = x_positions[i]
                            
                            # Color based on stream type
                            color = 'red' if stream_type == 'HOT' else 'blue'
                            stream_name = streams_data[i]['name'] if i < len(streams_data) else f'Stream {i+1}'
                            
                            # Draw arrow as a line with annotation for arrowhead
                            fig_interval.add_trace(go.Scatter(
                                x=[x_pos, x_pos],
                                y=[ss, st_temp],
                                mode='lines',
                                line=dict(color=color, width=8),
                                hovertemplate=f"<b>{stream_name}</b><br>" +
                                             f"Type: {stream_type}<br>" +
                                             f"T_supply (shifted): {ss:.1f}°C<br>" +
                                             f"T_target (shifted): {st_temp:.1f}°C<br>" +
                                             f"CP: {stream['cp']:.2f} kW/K<extra></extra>",
                                showlegend=False
                            ))
                            
                            # Add arrowhead
                            fig_interval.add_annotation(
                                x=x_pos, y=st_temp,
                                ax=x_pos, ay=ss,
                                xref='x', yref='y',
                                axref='x', ayref='y',
                                showarrow=True,
                                arrowhead=2,
                                arrowsize=1.5,
                                arrowwidth=3,
                                arrowcolor=color
                            )
                            
                            # Stream label at top
                            label_y = max(ss, st_temp) + (max(temps) - min(temps)) * 0.03
                            fig_interval.add_annotation(
                                x=x_pos, y=label_y,
                                text=f"<b>S{i+1}</b>",
                                showarrow=False,
                                font=dict(size=11, color='white'),
                                bgcolor=color,
                                bordercolor='black',
                                borderwidth=1,
                                borderpad=3
                            )
                            
                            # CP value in middle
                            mid_y = (ss + st_temp) / 2
                            fig_interval.add_annotation(
                                x=x_pos, y=mid_y,
                                text=f"CP={stream['cp']:.1f}",
                                showarrow=False,
                                font=dict(size=9, color='white'),
                                textangle=-90
                            )
                        
                        fig_interval.update_layout(
                            title=dict(text='Shifted Temperature Interval Diagram', font=dict(size=14)),
                            xaxis=dict(
                                title='Streams',
                                showticklabels=False,
                                range=[0, num_streams + 1],
                                showgrid=False
                            ),
                            yaxis=dict(
                                title='Shifted Temperature S (°C)',
                                showgrid=True,
                                gridcolor='rgba(0,0,0,0.1)'
                            ),
                            height=400,
                            margin=dict(l=60, r=20, t=40, b=40),
                            hovermode='closest',
                            showlegend=False
                        )
                        
                        st.plotly_chart(fig_interval, width='stretch', key="interval_chart")
                    
                    st.markdown("---")
                    
                    # Problem Table
                    st.markdown("##### Problem Table")
                    if results['problem_table']:
                        problem_df = pd.DataFrame(results['problem_table'])
                        # Rename columns for clarity
                        col_rename = {
                            'T': 'T (°C)',
                            'deltaT': 'ΔT (°C)',
                            'cpHot': 'ΣCP Hot (kW/K)',
                            'cpCold': 'ΣCP Cold (kW/K)',
                            'deltaCp': 'ΔCP (kW/K)',
                            'deltaH': 'ΔH (kW)'
                        }
                        problem_df = problem_df.rename(columns={k: v for k, v in col_rename.items() if k in problem_df.columns})
                        st.dataframe(problem_df, width='stretch', hide_index=True)
                    else:
                        st.info("No problem table data available")
                    
                    # Heat Cascades side by side
                    cascade_col1, cascade_col2 = st.columns(2)
                    
                    with cascade_col1:
                        st.markdown("##### Unfeasible Heat Cascade")
                        if results['unfeasible_heat_cascade']:
                            # Add temperature column to dataframe
                            unfeasible_data = []
                            for i, item in enumerate(results['unfeasible_heat_cascade']):
                                row = {'T (°C)': temps[i+1] if i+1 < len(temps) else '', 
                                       'ΔH (kW)': item['deltaH'], 
                                       'Cascade (kW)': item['exitH']}
                                unfeasible_data.append(row)
                            unfeasible_df = pd.DataFrame(unfeasible_data)
                            st.dataframe(unfeasible_df, width='stretch', hide_index=True)
                        else:
                            st.info("No unfeasible cascade data")
                    
                    with cascade_col2:
                        st.markdown("##### Feasible Heat Cascade")
                        if results['heat_cascade']:
                            # Add temperature column to dataframe
                            feasible_data = []
                            for i, item in enumerate(results['heat_cascade']):
                                row = {'T (°C)': temps[i+1] if i+1 < len(temps) else '', 
                                       'ΔH (kW)': item['deltaH'], 
                                       'Cascade (kW)': item['exitH']}
                                feasible_data.append(row)
                            feasible_df = pd.DataFrame(feasible_data)
                            st.dataframe(feasible_df, width='stretch', hide_index=True)
                        else:
                            st.info("No feasible cascade data")
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
