"""
Image rendering and visualization utilities for processes and streams.
"""

from PIL import Image, ImageDraw, ImageFont
import streamlit as st
import math

from config import BOX_FONT_SIZE
from geo_utils import snapshot_lonlat_to_pixel


def get_font(size=BOX_FONT_SIZE):
    """
    Get a font for drawing text on images.
    
    Args:
        size: Font size
        
    Returns:
        ImageFont: Font object or None if not available
    """
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except (OSError, IOError):
        try:
            return ImageFont.load_default()
        except (OSError, IOError):
            return None


def draw_arrow(draw_ctx, x_start, y_start, x_end, y_end, color=(0, 0, 0, 255), 
               width=3, head_len=18, head_angle_deg=30):
    """
    Draw an arrow from start to end point.
    
    Args:
        draw_ctx: PIL ImageDraw context
        x_start, y_start: Start coordinates
        x_end, y_end: End coordinates
        color: Arrow color (RGBA tuple)
        width: Line width
        head_len: Arrow head length
        head_angle_deg: Arrow head angle in degrees
    """
    # Draw main line
    draw_ctx.line([(x_start, y_start), (x_end, y_end)], fill=color, width=width)
    
    # Calculate arrow head
    angle = math.atan2(y_end - y_start, x_end - x_start)
    head_angle = math.radians(head_angle_deg)
    
    # Arrow head points
    x1 = x_end - head_len * math.cos(angle - head_angle)
    y1 = y_end - head_len * math.sin(angle - head_angle)
    x2 = x_end - head_len * math.cos(angle + head_angle)
    y2 = y_end - head_len * math.sin(angle + head_angle)
    
    # Draw arrow head
    draw_ctx.line([(x_end, y_end), (x1, y1)], fill=color, width=width)
    draw_ctx.line([(x_end, y_end), (x2, y2)], fill=color, width=width)


def draw_vertical_arrow(draw_ctx, x_pos, y_from, y_to, head_at_end=True, 
                       color=(0, 0, 0, 245), width=3):
    """
    Draw a vertical arrow.
    
    Args:
        draw_ctx: PIL ImageDraw context
        x_pos: X position
        y_from: Start Y position
        y_to: End Y position
        head_at_end: If True, arrow head at y_to, else at y_from
        color: Arrow color
        width: Line width
    """
    draw_ctx.line([(x_pos, y_from), (x_pos, y_to)], fill=color, width=width)
    
    if head_at_end:
        head_y = y_to
        direction = 1 if y_to > y_from else -1
    else:
        head_y = y_from
        direction = -1 if y_to > y_from else 1
    
    head_size = 8
    # Draw arrow head
    draw_ctx.line([
        (x_pos - head_size, head_y - direction * head_size),
        (x_pos, head_y),
        (x_pos + head_size, head_y - direction * head_size)
    ], fill=color, width=width)


def draw_centered_label(draw_ctx, text_str, x_center, y_baseline, above=True, font=None):
    """
    Draw centered text with background.
    
    Args:
        draw_ctx: PIL ImageDraw context
        text_str: Text to draw
        x_center: X center position
        y_baseline: Y baseline position
        above: If True, text above baseline, else below
        font: Font object
    """
    if not text_str:
        return
    
    if font:
        tb = draw_ctx.textbbox((0, 0), text_str, font=font)
        t_width = tb[2] - tb[0]
        t_height = tb[3] - tb[1]
    else:
        t_width = len(text_str) * 6
        t_height = 10
    
    text_xc = int(x_center - t_width / 2)
    text_yc = int(y_baseline - (t_height if above else 0))
    
    # Draw background
    draw_ctx.rectangle([
        text_xc - 2, text_yc - 2,
        text_xc + t_width + 2, text_yc + t_height + 2
    ], fill=(255, 255, 255, 230))
    
    # Draw text
    if font:
        draw_ctx.text((text_xc, text_yc), text_str, fill=(0, 0, 0, 255), font=font)
    else:
        draw_ctx.text((text_xc, text_yc), text_str, fill=(0, 0, 0, 255))


def calculate_process_positions(processes, map_center, map_zoom, img_w, img_h):
    """
    Calculate screen positions for all processes with valid coordinates.
    
    Args:
        processes: List of process data
        map_center: Map center coordinates
        map_zoom: Map zoom level
        img_w, img_h: Image dimensions
        
    Returns:
        tuple: (positioned_processes, name_index)
    """
    positioned = []
    name_index = {}
    
    for i, process in enumerate(processes):
        lat = process.get('lat')
        lon = process.get('lon')
        
        if lat in (None, "", "None") or lon in (None, "", "None"):
            continue
            
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            proc_px, proc_py = snapshot_lonlat_to_pixel(
                lon_f, lat_f, map_center[::-1], map_zoom, img_w, img_h
            )
            
            if not (0 <= proc_px <= img_w and 0 <= proc_py <= img_h):
                continue
                
            # Calculate bounding box
            label = process.get('name', f'P{i+1}')
            scale = float(process.get('box_scale', 1.0))
            
            base_w, base_h = 100, 45
            box_w = int(base_w * scale)
            box_h = int(base_h * scale)
            
            x0 = int(proc_px - box_w / 2)
            y0 = int(proc_py - box_h / 2)
            x1 = x0 + box_w
            y1 = y0 + box_h
            
            positioned.append({
                'idx': i,
                'label': label,
                'center': (proc_px, proc_py),
                'box': (x0, y0, x1, y1),
                'scale': scale
            })
            
            # Build name index for connections
            label_lower = label.lower()
            if label_lower not in name_index:
                name_index[label_lower] = []
            name_index[label_lower].append(i)
            
        except (ValueError, TypeError):
            continue
    
    return positioned, name_index


def draw_process_boxes(draw_ctx, positioned_processes, font=None):
    """
    Draw process boxes on the image.
    
    Args:
        draw_ctx: PIL ImageDraw context
        positioned_processes: List of positioned process data
        font: Font object for text
    """
    for item in positioned_processes:
        x0, y0, x1, y1 = item['box']
        label = item['label']
        
        # Draw box
        draw_ctx.rectangle([x0, y0, x1, y1], outline=(0, 0, 0, 255), width=2)
        draw_ctx.rectangle([x0 + 1, y0 + 1, x1 - 1, y1 - 1], fill=(255, 255, 255, 200))
        
        # Draw label
        box_center_x = (x0 + x1) / 2
        box_center_y = (y0 + y1) / 2
        
        if font:
            tb = draw_ctx.textbbox((0, 0), label, font=font)
            t_width = tb[2] - tb[0]
            t_height = tb[3] - tb[1]
        else:
            t_width = len(label) * 6
            t_height = 10
        
        text_x = int(box_center_x - t_width / 2)
        text_y = int(box_center_y - t_height / 2)
        
        if font:
            draw_ctx.text((text_x, text_y), label, fill=(0, 0, 0, 255), font=font)
        else:
            draw_ctx.text((text_x, text_y), label, fill=(0, 0, 0, 255))


def draw_streams(draw_ctx, positioned_processes, processes, font=None):
    """
    Draw stream connections and labels.
    
    Args:
        draw_ctx: PIL ImageDraw context
        positioned_processes: List of positioned process data
        processes: Full process data
        font: Font object
    """
    for item in positioned_processes:
        proc_idx = item['idx']
        process = processes[proc_idx]
        streams = process.get('streams', []) or []
        
        if not streams:
            continue
            
        x0, y0, x1, y1 = item['box']
        box_center_x = (x0 + x1) / 2
        n_streams = len(streams)
        
        # Calculate stream spacing
        base_stream_spacing = 40
        stream_h_spacing = max(28, min(base_stream_spacing, (x1 - x0 - 20) / max(1, n_streams))) if n_streams > 1 else 0
        
        for s_i, stream in enumerate(streams):
            offset = (s_i - (n_streams - 1) / 2) * stream_h_spacing
            sx = int(box_center_x + offset)
            
            # Parse temperatures
            try:
                tin_val = float(str(stream.get('temp_in', '')).strip())
            except (ValueError, TypeError):
                tin_val = None
            try:
                tout_val = float(str(stream.get('temp_out', '')).strip())
            except (ValueError, TypeError):
                tout_val = None
            
            # Determine color
            if tin_val is not None and tout_val is not None:
                is_cooling = tin_val > tout_val
                color = (200, 25, 25, 255) if is_cooling else (25, 80, 200, 255)
            else:
                color = (100, 100, 100, 255)
            
            # Draw vertical arrows
            arrow_top = y0 - 50
            arrow_bottom = y1 + 50
            
            draw_vertical_arrow(draw_ctx, sx, arrow_top, y0, head_at_end=True, color=color)
            draw_vertical_arrow(draw_ctx, sx, y1, arrow_bottom, head_at_end=True, color=color)
            
            # Draw temperature labels
            if tin_val is not None:
                draw_centered_label(draw_ctx, f"{tin_val}°C", sx, arrow_top - 5, above=True, font=font)
            if tout_val is not None:
                draw_centered_label(draw_ctx, f"{tout_val}°C", sx, arrow_bottom + 15, above=False, font=font)


def render_process_overlay(base_image, processes, map_center, map_zoom):
    """
    Render subprocess boxes and streams on the base image.
    
    Args:
        base_image: PIL Image to draw on
        processes: List of process data
        map_center: Map center coordinates
        map_zoom: Map zoom level
        
    Returns:
        PIL.Image: Image with overlays
    """
    if not base_image:
        return None
    
    # Create a copy to draw on
    overlay_img = base_image.copy()
    draw = ImageDraw.Draw(overlay_img)
    
    # Get font
    font = get_font()
    
    # Calculate positions
    w, h = overlay_img.size
    positioned, name_index = calculate_process_positions(processes, map_center, map_zoom, w, h)
    
    if not positioned:
        return overlay_img
    
    # Draw process boxes
    draw_process_boxes(draw, positioned, font)
    
    # Draw streams
    draw_streams(draw, positioned, processes, font)
    
    # Draw connections between processes (based on 'next' field)
    draw_process_connections(draw, positioned, processes, name_index)
    
    return overlay_img


def draw_process_connections(draw_ctx, positioned_processes, processes, name_index):
    """
    Draw arrows between connected processes.
    
    Args:
        draw_ctx: PIL ImageDraw context
        positioned_processes: List of positioned process data
        processes: Full process data
        name_index: Index mapping names to process indices
    """
    def resolve_targets(target_token):
        """Resolve process names to indices."""
        if not target_token or target_token.lower() in ('none', 'end', ''):
            return []
        return name_index.get(target_token.lower(), [])
    
    for item in positioned_processes:
        proc_idx = item['idx']
        process = processes[proc_idx]
        next_raw = process.get('next', '')
        
        if not next_raw:
            continue
        
        # Parse comma-separated targets
        targets = [t.strip() for t in str(next_raw).split(',') if t.strip()]
        
        for target in targets:
            target_indices = resolve_targets(target)
            
            for target_idx in target_indices:
                # Find target in positioned processes
                target_item = None
                for pos_item in positioned_processes:
                    if pos_item['idx'] == target_idx:
                        target_item = pos_item
                        break
                
                if target_item:
                    # Draw arrow from current to target
                    x1, y1 = item['center']
                    x2, y2 = target_item['center']
                    
                    # Adjust arrow endpoints to box edges
                    box1 = item['box']
                    box2 = target_item['box']
                    
                    # Simple edge calculation (can be improved)
                    if x2 > x1:  # Target to the right
                        start_x = box1[2]  # Right edge of source
                        end_x = box2[0]    # Left edge of target
                    else:  # Target to the left
                        start_x = box1[0]  # Left edge of source
                        end_x = box2[2]    # Right edge of target
                    
                    draw_arrow(draw_ctx, start_x, y1, end_x, y2, 
                             color=(50, 50, 200, 255), width=2)
