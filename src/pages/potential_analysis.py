import streamlit as st
import sys
import os
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import tempfile
import csv
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

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

# Helper function to convert lon/lat to pixel coordinates (same as data_collection.py)
def snapshot_lonlat_to_pixel(lon, lat, center_ll, z_level, img_w, img_h):
    import math as _math
    def lonlat_to_xy(lon_val, lat_val, z_val):
        lat_rad = _math.radians(lat_val)
        n_val = 2.0 ** z_val
        xtile = (lon_val + 180.0) / 360.0 * n_val
        ytile = (1.0 - _math.log(_math.tan(lat_rad) + 1 / _math.cos(lat_rad)) / _math.pi) / 2.0 * n_val
        return xtile, ytile
    
    center_lon, center_lat = center_ll
    cx, cy = lonlat_to_xy(center_lon, center_lat, z_level)
    px_tile, py_tile = lonlat_to_xy(lon, lat, z_level)
    tile_size = 256
    dx_tiles = px_tile - cx
    dy_tiles = py_tile - cy
    dx_px = dx_tiles * tile_size
    dy_px = dy_tiles * tile_size
    screen_x = img_w / 2 + dx_px
    screen_y = img_h / 2 + dy_px
    return screen_x, screen_y

def generate_process_level_map():
    """Generate a map image showing only the process-level (green boxes)."""
    snapshots_dict = st.session_state.get('map_snapshots', {})
    active_base = st.session_state.get('current_base', 'OpenStreetMap')
    
    if active_base == 'Blank':
        base_img = Image.new('RGBA', (800, 600), (242, 242, 243, 255))
    else:
        chosen_bytes = snapshots_dict.get(active_base) or st.session_state.get('map_snapshot')
        if not chosen_bytes:
            return None
        base_img = Image.open(BytesIO(chosen_bytes)).convert("RGBA")
    
    w, h = base_img.size
    draw = ImageDraw.Draw(base_img)
    
    # Load font
    BOX_FONT_SIZE = 20
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", BOX_FONT_SIZE)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", BOX_FONT_SIZE)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", BOX_FONT_SIZE)
            except (OSError, IOError):
                font = ImageFont.load_default()
    
    # Draw process-level boxes (green)
    group_coords = st.session_state.get('proc_group_coordinates', {})
    proc_group_names = st.session_state.get('proc_group_names', [])
    map_center = st.session_state.get('map_center', [0, 0])
    map_zoom = st.session_state.get('map_zoom', 17.5)
    
    for group_idx, coords_data in group_coords.items():
        group_idx = int(group_idx) if isinstance(group_idx, str) else group_idx
        if group_idx < len(proc_group_names):
            lat = coords_data.get('lat')
            lon = coords_data.get('lon')
            if lat is not None and lon is not None:
                try:
                    lat_f = float(lat)
                    lon_f = float(lon)
                    group_px, group_py = snapshot_lonlat_to_pixel(
                        lon_f, lat_f,
                        (map_center[1], map_center[0]),
                        map_zoom, w, h
                    )
                    if group_px < -50 or group_py < -20 or group_px > w + 50 or group_py > h + 20:
                        continue
                    
                    group_label = proc_group_names[group_idx]
                    scale = float(coords_data.get('box_scale', 1.5) or 1.5)
                    padding = int(8 * scale)
                    text_bbox = draw.textbbox((0, 0), group_label, font=font)
                    tw = text_bbox[2] - text_bbox[0]
                    th = text_bbox[3] - text_bbox[1]
                    box_w = int(tw * scale + padding * 2)
                    box_h = int(th * scale + padding * 2)
                    x0 = int(group_px - box_w / 2)
                    y0 = int(group_py - box_h / 2)
                    x1 = x0 + box_w
                    y1 = y0 + box_h
                    
                    # Draw box
                    fill_color = (200, 255, 200, 245)
                    border_color = (34, 139, 34, 255)
                    text_color = (0, 100, 0, 255)
                    draw.rectangle([x0, y0, x1, y1], fill=fill_color, outline=border_color, width=3)
                    
                    # Draw label
                    text_x = x0 + (box_w - tw) // 2
                    text_y = y0 + (box_h - th) // 2
                    draw.text((text_x, text_y), group_label, fill=text_color, font=font)
                except (ValueError, TypeError):
                    continue
    
    return base_img

def generate_subprocess_level_map():
    """Generate a map image showing subprocesses with connections."""
    snapshots_dict = st.session_state.get('map_snapshots', {})
    active_base = st.session_state.get('current_base', 'OpenStreetMap')
    
    if active_base == 'Blank':
        base_img = Image.new('RGBA', (800, 600), (242, 242, 243, 255))
    else:
        chosen_bytes = snapshots_dict.get(active_base) or st.session_state.get('map_snapshot')
        if not chosen_bytes:
            return None
        base_img = Image.open(BytesIO(chosen_bytes)).convert("RGBA")
    
    w, h = base_img.size
    draw = ImageDraw.Draw(base_img)
    
    # Load font
    BOX_FONT_SIZE = 16
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", BOX_FONT_SIZE)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", BOX_FONT_SIZE)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", BOX_FONT_SIZE)
            except (OSError, IOError):
                font = ImageFont.load_default()
    
    processes = st.session_state.get('processes', [])
    map_center = st.session_state.get('map_center', [0, 0])
    map_zoom = st.session_state.get('map_zoom', 17.5)
    
    # Collect positioned subprocesses
    positioned = []
    for idx, proc in enumerate(processes):
        coords = proc.get('coordinates', {})
        lat = coords.get('lat')
        lon = coords.get('lon')
        if lat is not None and lon is not None:
            try:
                lat_f = float(lat)
                lon_f = float(lon)
                px, py = snapshot_lonlat_to_pixel(
                    lon_f, lat_f,
                    (map_center[1], map_center[0]),
                    map_zoom, w, h
                )
                if px < -50 or py < -20 or px > w + 50 or py > h + 20:
                    continue
                
                label = proc.get('name', f'Subprocess {idx + 1}')
                scale = float(proc.get('box_scale', 1.0) or 1.0)
                padding = int(6 * scale)
                text_bbox = draw.textbbox((0, 0), label, font=font)
                tw = text_bbox[2] - text_bbox[0]
                th = text_bbox[3] - text_bbox[1]
                box_w = int(tw * scale + padding * 2)
                box_h = int(th * scale + padding * 2)
                x0 = int(px - box_w / 2)
                y0 = int(py - box_h / 2)
                x1 = x0 + box_w
                y1 = y0 + box_h
                
                positioned.append({
                    'idx': idx,
                    'label': label,
                    'center': (px, py),
                    'box': (x0, y0, x1, y1),
                    'next': proc.get('connection', '')
                })
            except (ValueError, TypeError):
                continue
    
    # Draw connections first
    name_to_center = {p['label'].lower(): p['center'] for p in positioned}
    for p in positioned:
        if p['next']:
            next_name = p['next'].lower()
            if next_name in name_to_center:
                start = p['center']
                end = name_to_center[next_name]
                draw.line([start, end], fill=(100, 100, 100, 200), width=2)
                # Draw arrowhead
                import math
                angle = math.atan2(end[1] - start[1], end[0] - start[0])
                arrow_len = 10
                arrow_angle = math.pi / 6
                ax1 = end[0] - arrow_len * math.cos(angle - arrow_angle)
                ay1 = end[1] - arrow_len * math.sin(angle - arrow_angle)
                ax2 = end[0] - arrow_len * math.cos(angle + arrow_angle)
                ay2 = end[1] - arrow_len * math.sin(angle + arrow_angle)
                draw.polygon([(end[0], end[1]), (ax1, ay1), (ax2, ay2)], fill=(100, 100, 100, 200))
    
    # Draw subprocess boxes
    for p in positioned:
        x0, y0, x1, y1 = p['box']
        fill_color = (255, 255, 220, 245)
        border_color = (180, 140, 60, 255)
        text_color = (80, 60, 20, 255)
        draw.rectangle([x0, y0, x1, y1], fill=fill_color, outline=border_color, width=2)
        
        # Draw label
        text_bbox = draw.textbbox((0, 0), p['label'], font=font)
        tw = text_bbox[2] - text_bbox[0]
        th = text_bbox[3] - text_bbox[1]
        box_w = x1 - x0
        box_h = y1 - y0
        text_x = x0 + (box_w - tw) // 2
        text_y = y0 + (box_h - th) // 2
        draw.text((text_x, text_y), p['label'], fill=text_color, font=font)
    
    return base_img

def generate_report():
    """Generate an HTML report with process maps and notes."""
    import base64
    
    # Generate maps as base64 images
    process_map = generate_process_level_map()
    subprocess_map = generate_subprocess_level_map()
    
    process_map_b64 = ""
    subprocess_map_b64 = ""
    
    if process_map:
        img_buffer = BytesIO()
        process_map.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        process_map_b64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
    
    if subprocess_map:
        img_buffer2 = BytesIO()
        subprocess_map.save(img_buffer2, format='PNG')
        img_buffer2.seek(0)
        subprocess_map_b64 = base64.b64encode(img_buffer2.getvalue()).decode('utf-8')
    
    # Get notes
    project_notes = st.session_state.get('project_notes', '')
    notes_html = ""
    if project_notes:
        for para in project_notes.split('\n'):
            if para.strip():
                notes_html += f"<p>{para}</p>\n"
    else:
        notes_html = "<p><em>No notes recorded.</em></p>"
    
    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Heat Transfer Planning Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .report-container {{
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        h3 {{
            color: #7f8c8d;
        }}
        .timestamp {{
            color: #95a5a6;
            font-size: 14px;
            margin-bottom: 30px;
        }}
        .maps-container {{
            display: flex;
            gap: 20px;
            justify-content: center;
            flex-wrap: wrap;
            margin: 20px 0;
        }}
        .map-section {{
            text-align: center;
            flex: 1;
            min-width: 300px;
            max-width: 480px;
        }}
        .map-section img {{
            max-width: 100%;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .map-section p {{
            font-weight: bold;
            color: #555;
            margin-top: 10px;
        }}
        .notes-section {{
            background-color: #fafafa;
            padding: 20px;
            border-radius: 4px;
            border-left: 4px solid #3498db;
            margin-top: 20px;
        }}
        .notes-section p {{
            margin: 8px 0;
            line-height: 1.6;
        }}
        @media print {{
            body {{
                background-color: white;
            }}
            .report-container {{
                box-shadow: none;
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <h1>🔥 Heat Transfer Planning Report</h1>
        <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        
        <h2>📍 Data Collection</h2>
        
        <div class="maps-container">
            <div class="map-section">
                {"<img src='data:image/png;base64," + process_map_b64 + "' alt='Process Overview'>" if process_map_b64 else "<p>Process map not available</p>"}
                <p>Process Overview</p>
            </div>
            <div class="map-section">
                {"<img src='data:image/png;base64," + subprocess_map_b64 + "' alt='Subprocess Connections'>" if subprocess_map_b64 else "<p>Subprocess map not available</p>"}
                <p>Subprocess Connections</p>
            </div>
        </div>
        
        <h3>📝 Notes</h3>
        <div class="notes-section">
            {notes_html}
        </div>
    </div>
</body>
</html>"""
    
    return html_content

# Title and Generate Report button
title_col, button_col = st.columns([4, 1])
with title_col:
    st.title("Potential Analysis")
with button_col:
    st.write("")  # Spacer to align button
    if st.button("📄 Generate Report", key="generate_report_btn"):
        try:
            html_data = generate_report()
            st.download_button(
                label="⬇️ Download Report",
                data=html_data,
                file_name=f"heat_transfer_report_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
                mime="text/html",
                key="download_report_btn"
            )
        except Exception as e:
            st.error(f"Error generating report: {str(e)}")

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
        """Extract Tin, Tout, mdot, cp, CP from stream and determine if HOT or COLD.
        Calculate Q = CP * (Tout - Tin).
        CP can be provided directly, or calculated as mdot * cp.
        """
        properties = stream.get('properties', {})
        values = stream.get('values', {})
        
        # Also check stream_values (new structure)
        stream_values = stream.get('stream_values', {})
        if not stream_values:
            stream_values = stream.get('product_values', {})
        
        tin = None
        tout = None
        mdot = None
        cp_val = None
        CP_direct = None  # CP provided directly
        
        # First try stream_values (new structure)
        if stream_values:
            if 'Tin' in stream_values and stream_values['Tin']:
                try:
                    tin = float(stream_values['Tin'])
                except (ValueError, TypeError):
                    pass
            if 'Tout' in stream_values and stream_values['Tout']:
                try:
                    tout = float(stream_values['Tout'])
                except (ValueError, TypeError):
                    pass
            if 'ṁ' in stream_values and stream_values['ṁ']:
                try:
                    mdot = float(stream_values['ṁ'])
                except (ValueError, TypeError):
                    pass
            if 'cp' in stream_values and stream_values['cp']:
                try:
                    cp_val = float(stream_values['cp'])
                except (ValueError, TypeError):
                    pass
            if 'CP' in stream_values and stream_values['CP']:
                try:
                    CP_direct = float(stream_values['CP'])
                except (ValueError, TypeError):
                    pass
        
        # Check properties dict structure
        if isinstance(properties, dict) and isinstance(values, dict):
            for pk, pname in properties.items():
                vk = pk.replace('prop', 'val')
                v = values.get(vk, '')
                
                if pname == 'Tin' and v and tin is None:
                    try:
                        tin = float(v)
                    except (ValueError, TypeError):
                        pass
                elif pname == 'Tout' and v and tout is None:
                    try:
                        tout = float(v)
                    except (ValueError, TypeError):
                        pass
                elif pname == 'ṁ' and v and mdot is None:
                    try:
                        mdot = float(v)
                    except (ValueError, TypeError):
                        pass
                elif pname == 'cp' and v and cp_val is None:
                    try:
                        cp_val = float(v)
                    except (ValueError, TypeError):
                        pass
                elif pname == 'CP' and v and CP_direct is None:
                    try:
                        CP_direct = float(v)
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
        
        # Determine CP: use direct CP if provided, otherwise calculate from mdot * cp
        CP_flow = None
        if CP_direct is not None:
            CP_flow = CP_direct
        elif mdot is not None and cp_val is not None:
            CP_flow = mdot * cp_val
        
        # Calculate Q = CP * |Tout - Tin| (always positive)
        Q = None
        if CP_flow is not None and tin is not None and tout is not None:
            Q = abs(CP_flow * (tout - tin))
        
        return {
            'tin': tin,
            'tout': tout,
            'mdot': mdot,
            'cp': cp_val,
            'CP': CP_flow,
            'Q': Q,
            'type': stream_type
        }
    
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
                
                stream_cols = st.columns([0.05, 0.25, 0.7])
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
                if info['CP'] is not None:
                    display_parts.append(f"CP:{info['CP']:.2f}")
                if info['Q'] is not None:
                    display_parts.append(f"Q:{info['Q']:.2f} kW")
                
                if info['type']:
                    type_color = "🔴" if info['type'] == "HOT" else "🔵"
                    display_parts.append(f"{type_color} {info['type']}")
                
                if display_parts:
                    stream_cols[2].caption(' | '.join(display_parts))
                else:
                    stream_cols[2].caption("(incomplete data)")
    
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
            Returns list of dicts with: CP, Tin, Tout, Q
            CP can be provided directly, or calculated as mdot * cp.
            Q = CP * (Tout - Tin)
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
                            
                            # Use get_stream_info to extract all values consistently
                            info = get_stream_info(strm)
                            
                            tin = info['tin']
                            tout = info['tout']
                            CP = info['CP']
                            Q = info['Q']
                            
                            # Only add if we have the required data
                            if tin is not None and tout is not None and CP is not None:
                                strm_name = strm.get('name', f'Stream {s_idx + 1}')
                                proc_nm = proc.get('name', f'Subprocess {p_idx + 1}')
                                result_streams.append({
                                    'name': f"{proc_nm} - {strm_name}",
                                    'CP': CP,
                                    'Tin': tin,
                                    'Tout': tout,
                                    'Q': Q
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
            st.info("Select at least 2 streams with complete data (Tin, Tout, and either CP or ṁ+cp) to run pinch analysis.")
            
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
                                has_CP = False  # CP = ṁ * cp (heat capacity rate)
                                
                                # Check stream_values (new structure)
                                stream_vals = strm.get('stream_values', {})
                                if not stream_vals:
                                    stream_vals = strm.get('product_values', {})
                                
                                if stream_vals:
                                    if stream_vals.get('Tin'):
                                        has_tin = True
                                    if stream_vals.get('Tout'):
                                        has_tout = True
                                    if stream_vals.get('ṁ'):
                                        has_mdot = True
                                    if stream_vals.get('cp'):
                                        has_cp = True
                                    if stream_vals.get('CP'):
                                        has_CP = True
                                
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
                                        elif pname == 'CP' and v:
                                            has_CP = True
                                
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
                                # Either CP is provided directly, or both ṁ and cp are needed
                                if not has_CP and not (has_mdot and has_cp):
                                    if not has_mdot:
                                        missing.append("ṁ")
                                    if not has_cp:
                                        missing.append("cp")
                                    if not missing or (not has_mdot and not has_cp):
                                        # If neither ṁ nor cp, suggest CP as alternative
                                        missing.append("(or CP)")
                                
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
                
                # Notes section
                st.markdown("##### Notes")
                if 'pinch_notes' not in st.session_state:
                    st.session_state['pinch_notes'] = ""
                
                notes = st.text_area(
                    "Notes",
                    value=st.session_state['pinch_notes'],
                    height=100,
                    placeholder="Add notes about the pinch analysis here...",
                    key="pinch_notes_input",
                    label_visibility="collapsed"
                )
                st.session_state['pinch_notes'] = notes
                
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
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
