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
    """Generate a map image showing subprocesses with all connections, energy data, colors, arrows - exactly like data_collection.py"""
    import math
    
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
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", BOX_FONT_SIZE)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", BOX_FONT_SIZE)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", BOX_FONT_SIZE)
            except (OSError, IOError):
                font = ImageFont.load_default()
    
    processes = st.session_state.get('processes', [])
    map_center = st.session_state.get('map_center', [0, 0])
    map_zoom = st.session_state.get('map_zoom', 17.5)
    proc_groups = st.session_state.get('proc_groups', [])
    proc_group_names = st.session_state.get('proc_group_names', [])
    
    if not processes:
        return None
    
    # Create mapping of subprocess index to group index
    subprocess_to_group = {}
    for group_idx, group_subprocess_list in enumerate(proc_groups):
        for subprocess_idx in group_subprocess_list:
            subprocess_to_group[subprocess_idx] = group_idx
    
    # Draw white canvas overlay (90% of screen, centered) - ALWAYS show for report
    overlay_w = int(w * 0.9)
    overlay_h = int(h * 0.9)
    center_px = w // 2
    center_py = h // 2
    overlay_x0 = int(center_px - overlay_w / 2)
    overlay_y0 = int(center_py - overlay_h / 2)
    overlay_x1 = overlay_x0 + overlay_w
    overlay_y1 = overlay_y0 + overlay_h
    
    margin = 20
    overlay_x0 = max(margin, overlay_x0)
    overlay_y0 = max(margin, overlay_y0)
    overlay_x1 = min(w - margin, overlay_x1)
    overlay_y1 = min(h - margin, overlay_y1)
    
    draw.rectangle([overlay_x0, overlay_y0, overlay_x1, overlay_y1], 
                 fill=(250, 250, 250, 40),
                 outline=(245, 245, 245, 80), 
                 width=1)
    
    # Add process area label
    if proc_group_names:
        overlay_label = f"Process Area: {proc_group_names[0]}" if len(proc_group_names) == 1 else "Subprocess View"
        if font:
            label_bbox = draw.textbbox((0, 0), overlay_label, font=font)
            label_w = label_bbox[2] - label_bbox[0]
            label_h = label_bbox[3] - label_bbox[1]
        else:
            label_w = len(overlay_label) * 6
            label_h = 10
        
        label_x = overlay_x0 + 15
        label_y = overlay_y0 + 15
        
        draw.rectangle([label_x-5, label_y-3, label_x+label_w+5, label_y+label_h+3], 
                     fill=(255, 255, 255, 120), 
                     outline=(220, 220, 220, 100), 
                     width=1)
        
        if font:
            draw.text((label_x, label_y), overlay_label, fill=(40, 40, 40, 255), font=font)
        else:
            draw.text((label_x, label_y), overlay_label, fill=(40, 40, 40, 255))
    
    # Collect all positioned subprocesses (show ALL, not just expanded ones)
    positioned = []
    name_index = {}
    
    for i, p in enumerate(processes):
        lat = p.get('lat')
        lon = p.get('lon')
        if lat in (None, "", "None") or lon in (None, "", "None"):
            continue
        
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            proc_px, proc_py = snapshot_lonlat_to_pixel(
                lon_f, lat_f,
                (map_center[1], map_center[0]),
                map_zoom, w, h
            )
            if proc_px < -50 or proc_py < -20 or proc_px > w + 50 or proc_py > h + 20:
                continue
            
            label = p.get('name') or f"P{i+1}"
            scale = float(p.get('box_scale', 6.0) or 6.0)
            base_padding = 18
            padding = int(base_padding * scale)
            text_bbox = draw.textbbox((0, 0), label, font=font) if font else (0, 0, len(label) * 6, 10)
            tw = text_bbox[2] - text_bbox[0]
            th = text_bbox[3] - text_bbox[1]
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
        draw_ctx.line([(x_start, y_start), (x_end, y_end)], fill=color, width=width, joint='curve')
        ang = math.atan2(y_end - y_start, x_end - x_start)
        ang_left = ang - math.radians(head_angle_deg)
        ang_right = ang + math.radians(head_angle_deg)
        x_left = x_end - head_len * math.cos(ang_left)
        y_left = y_end - head_len * math.sin(ang_left)
        x_right = x_end - head_len * math.cos(ang_right)
        y_right = y_end - head_len * math.sin(ang_right)
        draw_ctx.polygon([(x_end, y_end), (x_left, y_left), (x_right, y_right)], fill=color)
    
    def _resolve_targets(target_token, positioned_list, name_idx):
        target_token = target_token.strip()
        if not target_token:
            return []
        if target_token.isdigit():
            idx_int = int(target_token) - 1
            for d in positioned_list:
                if d['idx'] == idx_int:
                    return [d]
            return []
        lname2 = target_token.lower()
        if lname2 in name_idx:
            return [positioned_list[i] for i in name_idx[lname2]]
        return [d for d in positioned_list if d['label'].lower() == lname2]
    
    # Draw connection arrows and collect product stream info
    connection_product_streams = []
    
    for src in positioned:
        raw_next = src['next_raw']
        if not raw_next:
            continue
        parts = []
        for chunk in raw_next.replace(';', ',').replace('|', ',').split(','):
            part = chunk.strip()
            if part:
                parts.append(part)
        if not parts:
            continue
        
        sx, sy = src['center']
        for part_token in parts:
            targets = _resolve_targets(part_token, positioned, name_index)
            for tgt in targets:
                if tgt is src:
                    continue
                tx, ty = tgt['center']
                sx0, sy0, sx1, sy1 = src['box']
                sw2 = (sx1 - sx0) / 2.0
                sh2 = (sy1 - sy0) / 2.0
                tx0, ty0, tx1, ty1 = tgt['box']
                tw2 = (tx1 - tx0) / 2.0
                th2 = (ty1 - ty0) / 2.0
                vec_dx = tx - sx
                vec_dy = ty - sy
                if vec_dx == 0 and vec_dy == 0:
                    continue
                
                factors_s = []
                if vec_dx != 0:
                    factors_s.append(sw2 / abs(vec_dx))
                if vec_dy != 0:
                    factors_s.append(sh2 / abs(vec_dy))
                t_s = min(factors_s) if factors_s else 0
                
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
                
                # Collect product streams for labeling
                if src.get('type') == 'subprocess':
                    src_proc = processes[src['idx']]
                    src_streams = src_proc.get('streams', []) or []
                    product_streams = [s for s in src_streams if s.get('type', 'product') == 'product']
                    if product_streams:
                        connection_product_streams.append({
                            'start_x': start_x, 'start_y': start_y,
                            'end_x': end_x, 'end_y': end_y,
                            'streams': product_streams
                        })
    
    # Draw product stream labels on connection arrows
    def _draw_connection_stream_label(draw_ctx, start_x, start_y, end_x, end_y, streams, font_obj):
        try:
            small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 10)
        except:
            try:
                small_font = ImageFont.truetype("arial.ttf", 10)
            except:
                small_font = font_obj
        
        all_parts = []
        for s in streams:
            display_vars = s.get('display_vars', [])
            sv = s.get('stream_values', {}) or s.get('product_values', {})
            
            tin_val = sv.get('Tin', '') or s.get('temp_in', '')
            tout_val = sv.get('Tout', '') or s.get('temp_out', '')
            mdot_val = sv.get('ṁ', '') or s.get('mdot', '')
            cp_val = sv.get('cp', '') or s.get('cp', '')
            CP_val = sv.get('CP', '')
            
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
                label = " | ".join(stream_parts)
                if stream_name:
                    label = f"{stream_name}: {label}"
                all_parts.append(label)
        
        if not all_parts:
            return
        
        mid_x = (start_x + end_x) / 2
        mid_y = (start_y + end_y) / 2
        perp_offset = 18
        line_height = 14
        
        for line_idx, stream_label in enumerate(all_parts):
            if small_font:
                tb = draw_ctx.textbbox((0, 0), stream_label, font=small_font)
                t_width = tb[2] - tb[0]
                t_height = tb[3] - tb[1]
            else:
                t_width = len(stream_label) * 5
                t_height = 8
            
            lx = int(mid_x - t_width / 2)
            ly = int(mid_y + perp_offset + (line_idx * line_height))
            
            draw_ctx.rectangle([lx - 3, ly - 1, lx + t_width + 3, ly + t_height + 1], 
                               fill=(255, 255, 255, 235), outline=(120, 120, 120, 150))
            if small_font:
                draw_ctx.text((lx, ly), stream_label, fill=(0, 70, 0, 255), font=small_font)
            else:
                draw_ctx.text((lx, ly), stream_label, fill=(0, 70, 0, 255))
    
    # Draw subprocess boxes
    for item in positioned:
        x0, y0, x1, y1 = item['box']
        label = item['label']
        
        fill_color = (224, 242, 255, 245)  # Light blue
        border_color = (23, 105, 170, 255)  # Dark blue
        text_color = (10, 53, 85, 255)
        
        draw.rectangle([x0, y0, x1, y1], fill=fill_color, outline=border_color, width=2)
        
        box_w = x1 - x0
        box_h = y1 - y0
        if font:
            bbox_lbl = draw.textbbox((0, 0), label, font=font)
            t_w = bbox_lbl[2] - bbox_lbl[0]
            t_h = bbox_lbl[3] - bbox_lbl[1]
        else:
            t_w = len(label) * 6
            t_h = 10
        ct_x = int(x0 + (box_w - t_w) / 2)
        ct_y = int(y0 + (box_h - t_h) / 2)
        if font:
            draw.text((ct_x, ct_y), label, fill=text_color, font=font)
        else:
            draw.text((ct_x, ct_y), label, fill=text_color)
    
    # Draw product stream labels on connections
    for conn in connection_product_streams:
        _draw_connection_stream_label(draw, conn['start_x'], conn['start_y'], 
                                     conn['end_x'], conn['end_y'], conn['streams'], font)
    
    # Draw vertical stream arrows (Tin/Tout)
    arrow_len_v = 45
    base_stream_spacing = 60
    
    def _draw_v_arrow(draw_ctx, x_pos, y_from, y_to, head_at_end=True, color=(0, 0, 0, 245), width=3):
        draw_ctx.line([(x_pos, y_from), (x_pos, y_to)], fill=color, width=width)
        head_len = 11
        head_half = 7
        if head_at_end:
            direction = 1 if y_to >= y_from else -1
            tip_y = y_to
            base_y = y_to - direction * head_len
        else:
            direction = 1 if y_from >= y_to else -1
            tip_y = y_from
            base_y = y_from - direction * head_len
        draw_ctx.polygon([
            (x_pos, tip_y),
            (x_pos - head_half, base_y),
            (x_pos + head_half, base_y)
        ], fill=color)
    
    def _label_centered(text_str, x_center, y_baseline, above=True):
        if not text_str:
            return
        if font:
            tb = draw.textbbox((0, 0), text_str, font=font)
            t_width = tb[2] - tb[0]
            t_height = tb[3] - tb[1]
        else:
            t_width = len(text_str) * 6
            t_height = 10
        text_xc = int(x_center - t_width / 2)
        text_yc = int(y_baseline - (t_height if above else 0))
        draw.rectangle([text_xc - 2, text_yc - 2, text_xc + t_width + 2, text_yc + t_height + 2], fill=(255, 255, 255, 230))
        if font:
            draw.text((text_xc, text_yc), text_str, fill=(0, 0, 0, 255), font=font)
        else:
            draw.text((text_xc, text_yc), text_str, fill=(0, 0, 0, 255))
    
    # Draw stream arrows for each subprocess
    for item in positioned:
        if item.get('type') != 'subprocess':
            continue
        
        proc_idx = item['idx']
        proc = processes[proc_idx]
        streams = proc.get('streams', []) or []
        if not streams:
            continue
        
        non_product_streams = [s for s in streams if s.get('type', 'product') != 'product']
        if not non_product_streams:
            continue
        
        x0, y0, x1, y1 = item['box']
        box_center_x = (x0 + x1) / 2
        n_streams = len(non_product_streams)
        stream_h_spacing = max(28, min(base_stream_spacing, (x1 - x0 - 20) / max(1, n_streams))) if n_streams > 1 else 0
        
        for s_i, s in enumerate(non_product_streams):
            offset = (s_i - (n_streams - 1) / 2) * stream_h_spacing
            sx = int(box_center_x + offset)
            
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
            
            if tin_val is not None and tout_val is not None:
                is_cooling = tin_val > tout_val
                col = (200, 25, 25, 255) if is_cooling else (25, 80, 200, 255)
            else:
                col = (90, 90, 90, 255)
            
            inbound_bottom = y0 - 2
            inbound_top = inbound_bottom - arrow_len_v
            _draw_v_arrow(draw, sx, inbound_top, inbound_bottom, head_at_end=True, color=col, width=4)
            
            outbound_top = y1 + 2
            outbound_bottom = outbound_top + arrow_len_v
            _draw_v_arrow(draw, sx, outbound_top, outbound_bottom, head_at_end=True, color=col, width=4)
            
            mdot_raw = s.get('mdot', '')
            cp_raw = s.get('cp', '')
            m_symbol = "ṁ"
            mdot_part = f"{m_symbol}={mdot_raw}" if mdot_raw not in (None, '') else ''
            cp_part = f"cp={cp_raw}" if cp_raw not in (None, '') else ''
            
            tin_label = f"Tin={tin_raw}" if tin_raw not in ('', None) else 'Tin=?'
            tout_label = f"Tout={tout_raw}" if tout_raw not in ('', None) else 'Tout=?'
            
            top_components = [tin_label]
            if mdot_part:
                top_components.append(mdot_part)
            if cp_part:
                top_components.append(cp_part)
            bot_components = [tout_label]
            if mdot_part:
                bot_components.append(mdot_part)
            if cp_part:
                bot_components.append(cp_part)
            
            top_text = "  |  ".join(top_components)
            bot_text = "  |  ".join(bot_components)
            _label_centered(top_text, sx, inbound_top - 6, above=True)
            _label_centered(bot_text, sx, outbound_bottom + 6, above=False)
    
    return base_img

def generate_report():
    """Generate an HTML report with process maps, notes, and pinch analysis results."""
    import base64
    import os
    import tempfile
    import csv
    
    # Load the logo SVG file
    logo_b64 = ""
    try:
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'symbol.svg')
        with open(logo_path, 'r') as f:
            svg_content = f.read()
        logo_b64 = base64.b64encode(svg_content.encode('utf-8')).decode('utf-8')
    except Exception:
        pass
    
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
    
    # Get pinch notes
    pinch_notes = st.session_state.get('pinch_notes', '')
    pinch_notes_html = ""
    if pinch_notes:
        for para in pinch_notes.split('\n'):
            if para.strip():
                pinch_notes_html += f"<p>{para}</p>\n"
    else:
        pinch_notes_html = "<p><em>No pinch analysis notes recorded.</em></p>"
    
    # =====================================================
    # PINCH ANALYSIS DATA FOR REPORT
    # =====================================================
    pinch_section_html = ""
    composite_plot_b64 = ""
    gcc_plot_b64 = ""
    interval_plot_b64 = ""
    
    if PINCH_AVAILABLE:
        try:
            # Helper function to extract stream info (same as main code)
            def get_stream_info_report(stream):
                properties = stream.get('properties', {})
                values = stream.get('values', {})
                stream_values = stream.get('stream_values', {})
                if not stream_values:
                    stream_values = stream.get('product_values', {})
                
                tin = None
                tout = None
                mdot = None
                cp_val = None
                CP_direct = None
                
                if stream_values:
                    if stream_values.get('Tin'):
                        try: tin = float(stream_values['Tin'])
                        except: pass
                    if stream_values.get('Tout'):
                        try: tout = float(stream_values['Tout'])
                        except: pass
                    if stream_values.get('ṁ'):
                        try: mdot = float(stream_values['ṁ'])
                        except: pass
                    if stream_values.get('cp'):
                        try: cp_val = float(stream_values['cp'])
                        except: pass
                    if stream_values.get('CP'):
                        try: CP_direct = float(stream_values['CP'])
                        except: pass
                
                if isinstance(properties, dict) and isinstance(values, dict):
                    for pk, pname in properties.items():
                        vk = pk.replace('prop', 'val')
                        v = values.get(vk, '')
                        if pname == 'Tin' and v and tin is None:
                            try: tin = float(v)
                            except: pass
                        elif pname == 'Tout' and v and tout is None:
                            try: tout = float(v)
                            except: pass
                        elif pname == 'ṁ' and v and mdot is None:
                            try: mdot = float(v)
                            except: pass
                        elif pname == 'cp' and v and cp_val is None:
                            try: cp_val = float(v)
                            except: pass
                        elif pname == 'CP' and v and CP_direct is None:
                            try: CP_direct = float(v)
                            except: pass
                
                if tin is None and stream.get('temp_in'):
                    try: tin = float(stream['temp_in'])
                    except: pass
                if tout is None and stream.get('temp_out'):
                    try: tout = float(stream['temp_out'])
                    except: pass
                if mdot is None and stream.get('mdot'):
                    try: mdot = float(stream['mdot'])
                    except: pass
                if cp_val is None and stream.get('cp'):
                    try: cp_val = float(stream['cp'])
                    except: pass
                
                stream_type = None
                if tin is not None and tout is not None:
                    stream_type = "HOT" if tin > tout else "COLD"
                
                CP_flow = CP_direct if CP_direct is not None else (mdot * cp_val if mdot and cp_val else None)
                Q = abs(CP_flow * (tout - tin)) if CP_flow and tin is not None and tout is not None else None
                
                return {'tin': tin, 'tout': tout, 'mdot': mdot, 'cp': cp_val, 'CP': CP_flow, 'Q': Q, 'type': stream_type}
            
            # Extract stream data from selections
            processes = st.session_state.get('processes', [])
            sel_items = st.session_state.get('selected_items', {})
            
            streams_data = []
            for sel_key, is_sel in sel_items.items():
                if not is_sel or not sel_key.startswith("stream_"):
                    continue
                parts_split = sel_key.split("_")
                p_idx, s_idx = int(parts_split[1]), int(parts_split[2])
                if p_idx < len(processes):
                    proc = processes[p_idx]
                    proc_streams = proc.get('streams', [])
                    if s_idx < len(proc_streams):
                        strm = proc_streams[s_idx]
                        info = get_stream_info_report(strm)
                        if info['tin'] is not None and info['tout'] is not None and info['CP'] is not None:
                            streams_data.append({
                                'name': f"{proc.get('name', f'Subprocess {p_idx + 1}')} - {strm.get('name', f'Stream {s_idx + 1}')}",
                                'CP': info['CP'], 'Tin': info['tin'], 'Tout': info['tout'], 'Q': info['Q'], 'type': info['type']
                            })
            
            if len(streams_data) >= 2:
                # Build streams table HTML
                streams_table_html = """
                <table class="streams-table">
                    <thead>
                        <tr><th>Stream</th><th>Tin (°C)</th><th>Tout (°C)</th><th>CP (kW/K)</th><th>Q (kW)</th><th>Type</th></tr>
                    </thead>
                    <tbody>
                """
                for s in streams_data:
                    type_badge = f'<span class="badge hot">HOT</span>' if s['type'] == 'HOT' else f'<span class="badge cold">COLD</span>'
                    streams_table_html += f"""
                        <tr>
                            <td>{s['name']}</td>
                            <td>{s['Tin']:.1f}</td>
                            <td>{s['Tout']:.1f}</td>
                            <td>{s['CP']:.2f}</td>
                            <td>{s['Q']:.2f}</td>
                            <td>{type_badge}</td>
                        </tr>
                    """
                streams_table_html += "</tbody></table>"
                
                # Run pinch analysis
                tmin = st.session_state.get('tmin_input', 10.0)
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Tmin', str(tmin)])
                    writer.writerow(['CP', 'TSUPPLY', 'TTARGET'])
                    for strm in streams_data:
                        writer.writerow([strm['CP'], strm['Tin'], strm['Tout']])
                    temp_csv_path = f.name
                
                try:
                    pinch_obj = Pinch(temp_csv_path, options={})
                    pinch_obj.shiftTemperatures()
                    pinch_obj.constructTemperatureInterval()
                    pinch_obj.constructProblemTable()
                    pinch_obj.constructHeatCascade()
                    pinch_obj.constructShiftedCompositeDiagram('EN')
                    pinch_obj.constructCompositeDiagram('EN')
                    pinch_obj.constructGrandCompositeCurve('EN')
                    
                    results = {
                        'hot_utility': pinch_obj.hotUtility,
                        'cold_utility': pinch_obj.coldUtility,
                        'pinch_temperature': pinch_obj.pinchTemperature,
                        'tmin': pinch_obj.tmin,
                        'composite_diagram': pinch_obj.compositeDiagram,
                        'grand_composite_curve': pinch_obj.grandCompositeCurve,
                        'heat_cascade': pinch_obj.heatCascade,
                        'temperatures': pinch_obj._temperatures,
                        'streams': list(pinch_obj.streams)
                    }
                    
                    # Generate Composite Curves plot using Plotly (interactive HTML)
                    diagram = results['composite_diagram']
                    fig1 = go.Figure()
                    fig1.add_trace(go.Scatter(x=diagram['hot']['H'], y=diagram['hot']['T'], mode='lines+markers', name='Hot', line=dict(color='red', width=3), marker=dict(size=8)))
                    fig1.add_trace(go.Scatter(x=diagram['cold']['H'], y=diagram['cold']['T'], mode='lines+markers', name='Cold', line=dict(color='blue', width=3), marker=dict(size=8)))
                    fig1.add_hline(y=results['pinch_temperature'], line_dash='dash', line_color='gray', annotation_text=f"Pinch: {results['pinch_temperature']:.1f}°C")
                    fig1.update_layout(title='Composite Curves', xaxis_title='Enthalpy H (kW)', yaxis_title='Temperature T (°C)', height=600, width=900, xaxis=dict(rangemode='tozero'), yaxis=dict(rangemode='tozero'))
                    composite_plot_html = fig1.to_html(full_html=False, include_plotlyjs='cdn')
                    
                    # Generate Grand Composite Curve plot using Plotly (interactive HTML)
                    gcc_H = results['grand_composite_curve']['H']
                    gcc_T = results['grand_composite_curve']['T']
                    heat_cascade = results['heat_cascade']
                    fig2 = go.Figure()
                    for i in range(len(gcc_H) - 1):
                        color = 'red' if i < len(heat_cascade) and heat_cascade[i]['deltaH'] > 0 else ('blue' if i < len(heat_cascade) and heat_cascade[i]['deltaH'] < 0 else 'gray')
                        fig2.add_trace(go.Scatter(x=[gcc_H[i], gcc_H[i+1]], y=[gcc_T[i], gcc_T[i+1]], mode='lines+markers', line=dict(color=color, width=3), marker=dict(size=8, color=color), showlegend=False))
                    fig2.add_hline(y=results['pinch_temperature'], line_dash='dash', line_color='gray', annotation_text=f"Pinch: {results['pinch_temperature']:.1f}°C")
                    fig2.add_vline(x=0, line_color='black', line_width=1, opacity=0.3)
                    fig2.update_layout(title='Grand Composite Curve', xaxis_title='Net ΔH (kW)', yaxis_title='Shifted Temperature (°C)', height=600, width=900, yaxis=dict(rangemode='tozero'))
                    gcc_plot_html = fig2.to_html(full_html=False, include_plotlyjs=False)
                    
                    # Generate Temperature Interval Diagram using Plotly (interactive HTML)
                    interval_plot_html = ""
                    temps = results['temperatures']
                    pinch_streams = results['streams']
                    if pinch_streams and temps:
                        fig3 = go.Figure()
                        num_streams = len(pinch_streams)
                        x_positions = [(i + 1) * 1.0 for i in range(num_streams)]
                        
                        # Draw horizontal temperature lines
                        for temperature in temps:
                            fig3.add_shape(type="line", x0=0, x1=num_streams + 1, y0=temperature, y1=temperature, line=dict(color="gray", width=1, dash="dot"))
                        
                        # Draw pinch line
                        fig3.add_shape(type="line", x0=0, x1=num_streams + 1, y0=results['pinch_temperature'], y1=results['pinch_temperature'], line=dict(color="black", width=2, dash="dash"))
                        
                        # Draw stream bars with arrows
                        for i, stream in enumerate(pinch_streams):
                            ss, st_temp = stream['ss'], stream['st']
                            color = 'red' if stream['type'] == 'HOT' else 'blue'
                            fig3.add_trace(go.Scatter(x=[x_positions[i], x_positions[i]], y=[ss, st_temp], mode='lines', line=dict(color=color, width=10), showlegend=False))
                            fig3.add_annotation(x=x_positions[i], y=st_temp, ax=x_positions[i], ay=ss, xref='x', yref='y', axref='x', ayref='y', showarrow=True, arrowhead=2, arrowsize=1.5, arrowwidth=3, arrowcolor=color)
                            fig3.add_annotation(x=x_positions[i], y=max(ss, st_temp) + (max(temps) - min(temps)) * 0.03, text=f"S{i+1}", showarrow=False, font=dict(size=12, color='white'), bgcolor=color)
                        
                        fig3.update_layout(title='Temperature Interval Diagram', xaxis=dict(title='Streams', showticklabels=False, range=[0, num_streams + 1]), yaxis=dict(title='Shifted Temperature (°C)'), height=600, width=900, showlegend=False)
                        interval_plot_html = fig3.to_html(full_html=False, include_plotlyjs=False)
                    
                    # Build pinch analysis section HTML
                    pinch_section_html = f"""
                    <h2>📊 Potential Analysis</h2>
                    
                    <h3>Selected Streams</h3>
                    {streams_table_html}
                    
                    <h3>Pinch Analysis Results (ΔTmin = {tmin}°C)</h3>
                    <div class="metrics-row">
                        <div class="metric-card hot">
                            <div class="metric-label">Hot Utility</div>
                            <div class="metric-value">{results['hot_utility']:.2f} kW</div>
                        </div>
                        <div class="metric-card cold">
                            <div class="metric-label">Cold Utility</div>
                            <div class="metric-value">{results['cold_utility']:.2f} kW</div>
                        </div>
                        <div class="metric-card pinch">
                            <div class="metric-label">Pinch Temperature</div>
                            <div class="metric-value">{results['pinch_temperature']:.1f} °C</div>
                        </div>
                    </div>
                    
                    <h3>Diagrams</h3>
                    <div class="plots-container">
                        <div class="plot-section">
                            {composite_plot_html}
                        </div>
                        <div class="plot-section">
                            {gcc_plot_html}
                        </div>
                    </div>
                    <div class="plots-container">
                        <div class="plot-section">
                            {interval_plot_html}
                        </div>
                    </div>
                    
                    <h3>📝 Pinch Analysis Notes</h3>
                    <div class="notes-section">
                        {pinch_notes_html}
                    </div>
                    """
                    
                finally:
                    os.unlink(temp_csv_path)
            else:
                pinch_section_html = """
                <h2>📊 Potential Analysis</h2>
                <p><em>Not enough streams selected for pinch analysis. Select at least 2 streams with complete data.</em></p>
                """
        except Exception as e:
            pinch_section_html = f"""
            <h2>📊 Potential Analysis</h2>
            <p><em>Error generating pinch analysis: {str(e)}</em></p>
            """
    else:
        pinch_section_html = """
        <h2>📊 Potential Analysis</h2>
        <p><em>Pinch analysis module not available.</em></p>
        """
    
    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Heat Integration Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 2600px;
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
            margin-top: 40px;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 8px;
        }}
        h3 {{
            color: #7f8c8d;
            margin-top: 25px;
        }}
        .timestamp {{
            color: #95a5a6;
            font-size: 14px;
            margin-bottom: 30px;
        }}
        .maps-container {{
            display: flex;
            gap: 30px;
            justify-content: center;
            flex-wrap: nowrap;
            margin: 30px 0;
        }}
        .map-section {{
            text-align: center;
            flex: 1;
            min-width: 600px;
            max-width: 1100px;
        }}
        .map-section img {{
            max-width: 100%;
            width: 100%;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .map-section p {{
            font-weight: bold;
            color: #555;
            margin-top: 10px;
            font-size: 16px;
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
        .header-row {{
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 10px;
        }}
        .header-logo {{
            height: 60px;
            width: auto;
        }}
        .streams-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .streams-table th, .streams-table td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        .streams-table th {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
        .streams-table tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .badge {{
            padding: 4px 10px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 12px;
        }}
        .badge.hot {{
            background-color: #ffebee;
            color: #c62828;
        }}
        .badge.cold {{
            background-color: #e3f2fd;
            color: #1565c0;
        }}
        .metrics-row {{
            display: flex;
            gap: 30px;
            margin: 30px 0;
            flex-wrap: wrap;
        }}
        .metric-card {{
            flex: 1;
            min-width: 200px;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .metric-card.hot {{
            background-color: #ffebee;
            border: 2px solid #ef9a9a;
        }}
        .metric-card.cold {{
            background-color: #e3f2fd;
            border: 2px solid #90caf9;
        }}
        .metric-card.pinch {{
            background-color: #f3e5f5;
            border: 2px solid #ce93d8;
        }}
        .metric-label {{
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
        }}
        .metric-value {{
            font-size: 28px;
            font-weight: bold;
            color: #333;
        }}
        .plots-container {{
            display: flex;
            gap: 20px;
            justify-content: center;
            flex-wrap: nowrap;
            margin: 30px 0;
        }}
        .plot-section {{
            text-align: center;
            flex: 1;
            min-width: 0;
        }}
        .plot-section img {{
            max-width: 100%;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
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
        <div class="header-row">
            <img src="data:image/svg+xml;base64,{logo_b64}" alt="Logo" class="header-logo">
            <h1 style="margin: 0; border: none; padding: 0;">Heat Integration Report</h1>
        </div>
        <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        
        <h2>📍 Data Collection</h2>
        
        <div class="maps-container">
            <div class="map-section">
                {"<img src='data:image/png;base64," + process_map_b64 + "' alt='Process'>" if process_map_b64 else "<p>Process map not available</p>"}
                <p>Process</p>
            </div>
            <div class="map-section">
                {"<img src='data:image/png;base64," + subprocess_map_b64 + "' alt='Subprocess'>" if subprocess_map_b64 else "<p>No subprocesses with coordinates found.</p>"}
                <p>Subprocess</p>
            </div>
        </div>
        
        <h3>📝 Data Collection Notes</h3>
        <div class="notes-section">
            {notes_html}
        </div>
        
        {pinch_section_html}
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
                file_name=f"heat_integration_report_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
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
