import streamlit as st
import requests
from streamlit_folium import st_folium
import folium
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from staticmap import StaticMap, CircleMarker
from streamlit_image_coordinates import streamlit_image_coordinates
from math import radians, cos, sin, sqrt, atan2
from process_utils import (
    init_process_state,
    add_process,
    delete_process,
    add_stream_to_process,
    delete_stream_from_process,
)

# Helper: convert pixel (relative to center) in snapshot to lon/lat using Web Mercator math
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

st.set_page_config(page_title="Heat Integration analysis", layout="wide")

# Compact top padding & utility CSS to keep map tight to top-right
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

</style>
""", unsafe_allow_html=True)

st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
st.title("Heat Integration analysis")

MAP_WIDTH = 1500  # widened map (extends to the right)
MAP_HEIGHT = 860  # taller snapshot for more vertical space

# Tile templates for snapshot capture (static)
TILE_TEMPLATES = {
    'OpenStreetMap': 'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
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
# Unified persistent base layer selection (only changed by user interaction)
if 'current_base' not in st.session_state:
    st.session_state['current_base'] = 'OpenStreetMap'

left, right = st.columns([2.4, 5.6], gap="small")  # wider process panel, smaller gap to map

with left:
    # Compact mode buttons side by side
    mode_current = st.session_state['ui_mode_radio']
    if mode_current == "Select Map":
        col_lock = st.columns([1])[0]
        if col_lock.button("Lock map and analyze", key="btn_lock_analyze"):
            # Get current map position - use the most recent position if available
            new_center = st.session_state.get('current_map_center', st.session_state.get('selector_center', [51.70814085564164, 8.772155163087213]))
            new_zoom = round(st.session_state.get('current_map_zoom', st.session_state.get('selector_zoom', 17.5)))  # Round zoom to integer for tile servers
            
            selected_base_now = st.session_state.get('current_base', 'OpenStreetMap')
            existing_snaps = st.session_state.get('map_snapshots', {})
            regenerate = (
                (st.session_state.get('map_snapshot') is None) or
                (new_center != st.session_state.get('map_center')) or
                (new_zoom != st.session_state.get('map_zoom')) or
                (selected_base_now not in existing_snaps)  # ensure chosen base available
            )
            st.session_state['map_center'] = new_center
            st.session_state['map_zoom'] = new_zoom
            if regenerate:
                try:
                    snapshots = {}
                    for layer_name, template in TILE_TEMPLATES.items():
                        smap = StaticMap(MAP_WIDTH, MAP_HEIGHT, url_template=template)
                        try:
                            marker = CircleMarker((new_center[1], new_center[0]), 'red', 12)
                            smap.add_marker(marker)
                        except (RuntimeError, OSError):
                            pass
                        img_layer = smap.render(zoom=new_zoom)
                        buf_l = BytesIO()
                        img_layer.save(buf_l, format='PNG')
                        snapshots[layer_name] = buf_l.getvalue()
                    st.session_state['map_snapshots'] = snapshots
                    # Legacy single snapshot retains OSM for backward compatibility
                    st.session_state['map_snapshot'] = snapshots.get('OpenStreetMap')
                except RuntimeError as gen_err:
                    st.session_state['ui_status_msg'] = f"Capture failed: {gen_err}"
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
        if col_add.button("Add group of processes", key="btn_add_group_top"):
            # Ensure groups list exists
            if 'proc_groups' not in st.session_state:
                st.session_state['proc_groups'] = []
            st.session_state['proc_groups'].append([])  # new empty group
            # Sync group names & expansion
            if 'proc_group_names' not in st.session_state:
                st.session_state['proc_group_names'] = []
            st.session_state['proc_group_names'].append(f"Group {len(st.session_state['proc_groups'])}")
            if 'proc_group_expanded' not in st.session_state:
                st.session_state['proc_group_expanded'] = []
            st.session_state['proc_group_expanded'].append(True)
            st.session_state['ui_status_msg'] = "Added new empty group"
            st.rerun()
    mode = st.session_state['ui_mode_radio']
    # Process & Stream UI (only show in Analyze mode to mimic original workflow)
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
                st.session_state['proc_group_expanded'] = [True]*group_count
            elif len(st.session_state['proc_group_expanded']) != group_count:
                st.session_state['proc_group_expanded'] = [st.session_state['proc_group_expanded'][g] if g < len(st.session_state['proc_group_expanded']) else True for g in range(group_count)]
            if 'proc_group_names' not in st.session_state:
                st.session_state['proc_group_names'] = [f"Group {g+1}" for g in range(group_count)]
            elif len(st.session_state['proc_group_names']) != group_count:
                current_names = st.session_state['proc_group_names']
                if len(current_names) < group_count:
                    current_names += [f"Group {g+1}" for g in range(len(current_names), group_count)]
                else:
                    current_names = current_names[:group_count]
                st.session_state['proc_group_names'] = current_names
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
                # Top thick separator for group
                st.markdown("<div style='height:3px; background:#888888; margin:12px 0 6px;'></div>", unsafe_allow_html=True)
                # Arrow | Name | Add process | Count | Delete
                gh_cols = st.columns([0.05, 0.40, 0.20, 0.10, 0.10])
                g_toggle_label = "▾" if st.session_state['proc_group_expanded'][g] else "▸"
                if gh_cols[0].button(g_toggle_label, key=f"group_toggle_{g}"):
                    st.session_state['proc_group_expanded'][g] = not st.session_state['proc_group_expanded'][g]
                    st.rerun()
                default_name = st.session_state['proc_group_names'][g]
                new_name = gh_cols[1].text_input("Group name", value=default_name, key=f"group_name_{g}", label_visibility="collapsed", placeholder=f"Group {g+1}")
                st.session_state['proc_group_names'][g] = new_name.strip() or default_name
                if gh_cols[2].button("Add process", key=f"add_proc_group_{g}"):
                    add_process(st.session_state)
                    new_idx = len(st.session_state['processes']) - 1
                    g_list.append(new_idx)
                    # Ensure proc_expanded has entry and keep it collapsed
                    if len(st.session_state['proc_expanded']) <= new_idx:
                        st.session_state['proc_expanded'].append(False)
                    else:
                        st.session_state['proc_expanded'][new_idx] = False
                    st.session_state['ui_status_msg'] = f"Added process to {st.session_state['proc_group_names'][g]}"
                    st.rerun()
                gh_cols[3].markdown(f"**{len(g_list)}**")
                pending_group = st.session_state.get('group_delete_pending')
                with gh_cols[4]:
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

                if not g_list:
                    st.caption("(No processes in this group)")
                for local_idx, i in enumerate(g_list):
                    p = st.session_state['processes'][i]
                    # Per-process header (toggle | name | size | place | delete)
                    header_cols = st.columns([0.06, 0.54, 0.14, 0.16, 0.10])
                    toggle_label = "▾" if st.session_state['proc_expanded'][i] else "▸"
                    if header_cols[0].button(toggle_label, key=f"proc_toggle_{i}"):
                        st.session_state['proc_expanded'][i] = not st.session_state['proc_expanded'][i]
                        st.rerun()
                    # Default auto-name if empty
                    if not p.get('name'):
                        p['name'] = f"Process {i+1}"
                    p['name'] = header_cols[1].text_input(
                        "Process name",
                        value=p.get('name',''),
                        key=f"p_name_{i}",
                        label_visibility="collapsed",
                        placeholder=f"Process {i+1}"
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
                            st.rerun()
                    else:
                        if header_cols[3].button("Done", key=f"done_place_{i}"):
                            st.session_state['placement_mode'] = False
                            st.session_state['placing_process_idx'] = None
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
                        r1c1,r1c2,r1c3,r1c4 = st.columns([1,1,1,1])
                        p['conntemp'] = r1c1.text_input("Product Tin", value=p.get('conntemp',''), key=f"p_conntemp_{i}")
                        p['product_tout'] = r1c2.text_input("Product Tout", value=p.get('product_tout',''), key=f"p_ptout_{i}")
                        p['connm'] = r1c3.text_input("Product ṁ", value=p.get('connm',''), key=f"p_connm_{i}")
                        p['conncp'] = r1c4.text_input("Product cp", value=p.get('conncp',''), key=f"p_conncp_{i}")

                        r2c1,r2c2,r2c3 = st.columns([1,1,3])
                        p['lat'] = r2c1.text_input("Latitude", value=str(p.get('lat') or ''), key=f"p_lat_{i}")
                        p['lon'] = r2c2.text_input("Longitude", value=str(p.get('lon') or ''), key=f"p_lon_{i}")
                        # Multi-select for next processes (exclude self)
                        all_procs = st.session_state['processes']
                        if len(all_procs) <= 1:
                            with r2c3:
                                st.caption("To connect processes, add more than one")
                                p['next'] = ''
                        else:
                            # Build option list of other process names
                            options = []
                            for j, pj in enumerate(all_procs):
                                if j == i:
                                    continue
                                nm = pj.get('name') or f"Process {j+1}"
                                options.append(nm)
                            # Current selections parsed from stored string
                            current_tokens = [t.strip() for t in (p.get('next','') or '').replace(';',',').replace('|',',').split(',') if t.strip()]
                            # Keep only those present in options
                            preselect = [t for t in current_tokens if t in options]
                            selected = r2c3.multiselect("Next processes", options=options, default=preselect, key=f"p_next_multi_{i}")
                            # Store as comma-separated names
                            p['next'] = ", ".join(selected)

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
                            lbl_col, sc1,sc2,sc3,sc4,sc5 = st.columns([0.5,1,1,1,1,0.6])
                            lbl_col.markdown(f"**S{si+1}**")
                            s['temp_in'] = sc1.text_input("Tin", value=str(s.get('temp_in','')), key=f"s_tin_{i}_{si}")
                            s['temp_out'] = sc2.text_input("Tout", value=str(s.get('temp_out','')), key=f"s_tout_{i}_{si}")
                            s['mdot'] = sc3.text_input("ṁ", value=str(s.get('mdot','')), key=f"s_mdot_{i}_{si}")
                            s['cp'] = sc4.text_input("cp", value=str(s.get('cp','')), key=f"s_cp_{i}_{si}")
                            if sc5.button("✕", key=f"del_stream_{i}_{si}"):
                                delete_stream_from_process(st.session_state, i, si)
                                st.rerun()
                    if local_idx < len(g_list) - 1:
                        st.markdown("<div style='height:1px; background:#888888; opacity:0.5; margin:4px 0;'></div>", unsafe_allow_html=True)
                # Bottom separator after expanded group
                st.markdown("<div style='height:2px; background:#888888; opacity:0.7; margin:8px 0 4px;'></div>", unsafe_allow_html=True)
        else:
            st.info("No groups yet. Use 'Add group of processes' to start.")
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
/* Compact selectboxes */
div[data-testid=\"stVerticalBlock\"] > div div[data-baseweb=\"select\"] {min-height:32px;}
div[data-testid=\"stVerticalBlock\"] > div div[data-baseweb=\"select\"] * {font-size:11px;}
div[data-testid=\"stVerticalBlock\"] > div div[data-baseweb=\"select\"] div[role=\"combobox\"] {padding:2px 6px;}
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
            # Build map with only the chosen base layer
            if selected_base == 'Blank':
                fmap = folium.Map(location=[51.70814085564164, 8.772155163087213], zoom_start=17.5, tiles=None)
                # Add a transparent 1x1 tile layer colored via CSS overlay not natively supported; skip tiles, map background will be default.
                # We'll inject simple CSS to set map background to very light gray.
                st.markdown("""
<style>
div.leaflet-container {background: #f2f2f3 !important;}
</style>
""", unsafe_allow_html=True)
            elif selected_base == 'Satellite':
                fmap = folium.Map(location=[51.70814085564164, 8.772155163087213], zoom_start=17.5, tiles=None)
                folium.TileLayer(
                    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                    attr='Esri WorldImagery',
                    name='Satellite'
                ).add_to(fmap)
            elif selected_base == 'Positron':
                fmap = folium.Map(location=[51.70814085564164, 8.772155163087213], zoom_start=17.5, tiles='CartoDB positron')
            else:
                fmap = folium.Map(location=[51.70814085564164, 8.772155163087213], zoom_start=17.5, tiles='OpenStreetMap')
            # Feature groups for overlays
            process_fg = folium.FeatureGroup(name='Processes', show=True)
            connection_fg = folium.FeatureGroup(name='Connections', show=True)
            for idx, p in enumerate(st.session_state['processes']):
                lat = p.get('lat'); lon = p.get('lon')
                if lat not in (None, "") and lon not in (None, ""):
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
            # But save the current position for when we need to lock the map
            if fmap_data and 'center' in fmap_data and 'zoom' in fmap_data:
                c = fmap_data['center']
                new_center = [c['lat'], c['lng']] if isinstance(c, dict) else c
                new_zoom = fmap_data['zoom']
                st.session_state['current_map_center'] = new_center
                st.session_state['current_map_zoom'] = new_zoom
            st.caption("Pan/zoom, then click 'Lock map and analyze' to capture a snapshot.")
    else:
        # Analysis mode
        if not st.session_state['map_locked']:
            st.warning("No locked snapshot yet. Switch to 'Select Map' and capture one.")
        else:
            # In Analyze mode on right column proceed with snapshot tools below
            # --- Top action/status bar ---
            top_c1, top_c2, top_c3, top_c4 = st.columns([3,2,2,2])
            with top_c1:
                # Decide dynamic status message (priority: placing > measuring > last action > default)
                placing_idx = st.session_state.get('placing_process_idx')
                placing_mode = st.session_state.get('placement_mode')
                measure_mode = st.session_state.get('measure_mode')
                measure_points = st.session_state.get('measure_points', [])
                dist_val = st.session_state.get('measure_distance_m')
                last_msg = st.session_state.get('ui_status_msg')
                if placing_mode and placing_idx is not None and 0 <= placing_idx < len(st.session_state.get('processes', [])):
                    pname = st.session_state['processes'][placing_idx].get('name') or f"P{placing_idx+1}"
                    st.info(f"Placing process: {pname} (Double click on map)")
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
                st.empty()  # spacer
            with top_c4:
                st.markdown("<div style='font-size:12px; font-weight:600; margin-bottom:0px;'>Base</div>", unsafe_allow_html=True)
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

            # Placement handled directly via per-process Place/Done buttons in left panel

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

                # --- Overlay process boxes & connecting arrows on snapshot ---
                draw = ImageDraw.Draw(base_img)
                # Larger font for better readability
                BOX_FONT_SIZE = 20
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
                for i, p in enumerate(st.session_state['processes']):
                    lat = p.get('lat'); lon = p.get('lon')
                    if lat in (None, "", "None") or lon in (None, "", "None"):
                        continue
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
                        scale = float(p.get('box_scale', 1.0) or 1.0)
                        base_padding = 6
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
                            'next_raw': p.get('next', '') or ''
                        })
                        lname = label.strip().lower()
                        name_index.setdefault(lname, []).append(len(positioned) - 1)
                    except (ValueError, TypeError):
                        continue

                # Helper: draw arrow with head
                def _draw_arrow(draw_ctx, x_start, y_start, x_end, y_end, color=(0, 0, 0, 255), width=3, head_len=18, head_angle_deg=30):
                    import math
                    draw_ctx.line([(x_start, y_start), (x_end, y_end)], fill=color, width=width)
                    ang = math.atan2(y_end - y_start, x_end - x_start)
                    ang_left = ang - math.radians(head_angle_deg)
                    ang_right = ang + math.radians(head_angle_deg)
                    x_left = x_end - head_len * math.cos(ang_left)
                    y_left = y_end - head_len * math.sin(ang_left)
                    x_right = x_end - head_len * math.cos(ang_right)
                    y_right = y_end - head_len * math.sin(ang_right)
                    draw_ctx.polygon([(x_end, y_end), (x_left, y_left), (x_right, y_right)], fill=color)

                # Build quick lookup by process name (case-insensitive)
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
                            _draw_arrow(draw, start_x, start_y, end_x, end_y, color=(0, 0, 0, 245), width=3)

                # Third pass: draw boxes & labels on top
                for item in positioned:
                    x0, y0, x1, y1 = item['box']
                    label = item['label']
                    padding = 6
                    # Retrieve scale from process for consistent font positioning relative to new box
                    proc_scale = 1.0
                    try:
                        proc_scale = float(st.session_state['processes'][item['idx']].get('box_scale',1.0) or 1.0)
                    except (ValueError, TypeError):
                        proc_scale = 1.0
                    padding = int(6 * proc_scale)
                    # Filled box
                    # Light blue fill, darker blue border
                    draw.rectangle([x0, y0, x1, y1], fill=(224, 242, 255, 245), outline=(23, 105, 170, 255), width=2)
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
                        draw.text((ct_x, ct_y), label, fill=(10, 53, 85, 255), font=font)
                    else:
                        draw.text((ct_x, ct_y), label, fill=(10, 53, 85, 255))

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
                    proc_idx = item['idx']
                    proc = st.session_state['processes'][proc_idx]
                    streams = proc.get('streams', []) or []
                    if not streams:
                        continue
                    x0, y0, x1, y1 = item['box']
                    box_center_x = (x0 + x1) / 2
                    n_streams = len(streams)
                    # Dynamic spacing: attempt to shrink if narrow box; ensure minimum 28 px spacing
                    stream_h_spacing = max(28, min(base_stream_spacing, (x1 - x0 - 20) / max(1, n_streams))) if n_streams > 1 else 0
                    for s_i, s in enumerate(streams):
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
                # Present snapshot full width (base selector moved to top bar)
                img = base_img  # for coordinate capture
                coords = streamlit_image_coordinates(img, key="meas_img", width=w)
                if st.session_state['placement_mode'] and coords is not None and st.session_state.get('placing_process_idx') is not None:
                    x_px, y_px = coords['x'], coords['y']
                    lon_new, lat_new = snapshot_pixel_to_lonlat(x_px, y_px, st.session_state['map_center'][::-1], st.session_state['map_zoom'], w, h)
                    try:
                        pidx = st.session_state['placing_process_idx']
                        st.session_state['processes'][pidx]['lat'] = round(lat_new, 6)
                        st.session_state['processes'][pidx]['lon'] = round(lon_new, 6)
                        st.success(f"Set process coords to ({lat_new:.6f}, {lon_new:.6f})")
                    except (ValueError, TypeError):
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
            else:
                st.warning("Snapshot missing. Unlock and re-capture if needed.")
