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

st.set_page_config(page_title="Process Analysis", layout="wide")

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

</style>
""", unsafe_allow_html=True)

st.title("Process Analysis App (Streamlit)")

MAP_WIDTH = 1300  # increased for wider map & snapshot
MAP_HEIGHT = 720  # taller snapshot for better visibility

# Session state for map lock and snapshot
if 'map_locked' not in st.session_state: st.session_state['map_locked'] = False
if 'map_snapshot' not in st.session_state: st.session_state['map_snapshot'] = None
if 'map_center' not in st.session_state: st.session_state['map_center'] = [56, 10]  # committed (locked) center
if 'map_zoom' not in st.session_state: st.session_state['map_zoom'] = 16            # committed (locked) zoom
if 'selector_center' not in st.session_state: st.session_state['selector_center'] = st.session_state['map_center'][:]
if 'selector_zoom' not in st.session_state: st.session_state['selector_zoom'] = st.session_state['map_zoom']
# Track mode separately (avoid writing to widget key after creation)
if 'ui_mode_radio' not in st.session_state: st.session_state['ui_mode_radio'] = 'Select Map'
if 'measure_mode' not in st.session_state: st.session_state['measure_mode'] = False
if 'measure_points' not in st.session_state: st.session_state['measure_points'] = []
init_process_state(st.session_state)
if 'placing_process_idx' not in st.session_state: st.session_state['placing_process_idx'] = None
if 'placement_mode' not in st.session_state: st.session_state['placement_mode'] = False

left, right = st.columns([2.4, 5.6], gap="small")  # wider process panel, smaller gap to map

with left:
    # Compact mode buttons side by side
    mode_current = st.session_state['ui_mode_radio']
    mcol1, mcol2 = st.columns(2)
    if mcol1.button("Select", key="btn_mode_select", disabled=(mode_current=="Select Map")):
        st.session_state['ui_mode_radio'] = "Select Map"
    st.rerun()
    if mcol2.button("Analyze", key="btn_mode_analyze", disabled=(mode_current=="Analyze")):
        st.session_state['ui_mode_radio'] = "Analyze"
    st.rerun()
    mode = st.session_state['ui_mode_radio']
    # Process & Stream UI (only show in Analyze mode to mimic original workflow)
    if mode == "Analyze":
        if st.button("Add Process", key="btn_add_process_simple"):
            add_process(st.session_state)
            st.success("Added blank process")
        if st.session_state['processes']:
            for i, p in enumerate(st.session_state['processes']):
                exp_label = f"{i+1}. {p.get('name') or '(unnamed)'}"
                with st.expander(exp_label, expanded=False):
                    # Row for main attributes
                    r1c1,r1c2,r1c3,r1c4,r1c5,r1c6 = st.columns([2,1,1,1,1,1])
                    p['name'] = r1c1.text_input("Name", value=p.get('name',''), key=f"p_name_{i}")
                    p['next'] = r1c2.text_input("Next", value=p.get('next',''), key=f"p_next_{i}")
                    p['conntemp'] = r1c3.text_input("Conn Temp", value=p.get('conntemp',''), key=f"p_conntemp_{i}")
                    p['connm'] = r1c4.text_input("Conn m", value=p.get('connm',''), key=f"p_connm_{i}")
                    p['conncp'] = r1c5.text_input("Conn cp", value=p.get('conncp',''), key=f"p_conncp_{i}")
                    if r1c6.button("del", key=f"del_proc_{i}"):
                        delete_process(st.session_state, i)
                        st.rerun()
                    # Row for coordinates + placement buttons
                    r2c1,r2c2,r2c3,r2c4 = st.columns([1,1,1,1])
                    p['lat'] = r2c1.text_input("Lat", value=str(p.get('lat') or ''), key=f"p_lat_{i}")
                    p['lon'] = r2c2.text_input("Lon", value=str(p.get('lon') or ''), key=f"p_lon_{i}")
                    place_active = st.session_state['placement_mode'] and st.session_state.get('placing_process_idx') == i
                    if not place_active:
                        if r2c3.button("Place", key=f"place_{i}"):
                            st.session_state['placement_mode'] = True
                            st.session_state['measure_mode'] = False
                            st.session_state['placing_process_idx'] = i
                    else:
                        if r2c3.button("Done", key=f"done_place_{i}"):
                            st.session_state['placement_mode'] = False
                            st.session_state['placing_process_idx'] = None
                    r2c4.caption("Click snapshot to set")
                    # Streams
                    st.markdown("**Streams**")
                    streams = p.get('streams', [])
                    if streams:
                        for si, s in enumerate(streams):
                            sc1,sc2,sc3,sc4,sc5 = st.columns([1,1,1,1,1])
                            s['mdot'] = sc1.text_input("ṁ", value=str(s.get('mdot','')), key=f"s_mdot_{i}_{si}")
                            s['temp_in'] = sc2.text_input("Tin", value=str(s.get('temp_in','')), key=f"s_tin_{i}_{si}")
                            s['temp_out'] = sc3.text_input("Tout", value=str(s.get('temp_out','')), key=f"s_tout_{i}_{si}")
                            s['cp'] = sc4.text_input("cp", value=str(s.get('cp','')), key=f"s_cp_{i}_{si}")
                            if sc5.button("✕", key=f"del_stream_{i}_{si}"):
                                delete_stream_from_process(st.session_state, i, si)
                                st.rerun()
                    else:
                        st.caption("No streams yet.")
                    as1,as2,as3,as4,as5 = st.columns([1,1,1,1,1])
                    new_mdot = as1.text_input("ṁ", key=f"new_mdot_{i}")
                    new_tin = as2.text_input("Tin", key=f"new_tin_{i}")
                    new_tout = as3.text_input("Tout", key=f"new_tout_{i}")
                    new_cp = as4.text_input("cp", key=f"new_cp_{i}")
                    if as5.button("Add", key=f"btn_add_stream_{i}"):
                        add_stream_to_process(st.session_state, i)
                        st.session_state['processes'][i]['streams'][-1].update({
                            'mdot': new_mdot,
                            'temp_in': new_tin,
                            'temp_out': new_tout,
                            'cp': new_cp,
                        })
                        st.rerun()
        else:
            st.info("No processes yet in this session.")
    else:
        # Provide a summary of existing processes while selecting map
        if st.session_state['processes']:
            st.caption(f"Processes: {len(st.session_state['processes'])} (edit in Analyze mode)")
        else:
            st.caption("Add processes in Analyze mode after locking a map view.")

with right:
    # mode already selected on left
    if mode == "Select Map":
        # Address search & lock row
        sel_c1, sel_c2, sel_c3 = st.columns([3,2,2])
        with sel_c1:
            with st.form(key="search_form", clear_on_submit=False):
                address = st.text_input("Search address", key="address_input")
                submit_search = st.form_submit_button("Search")
            if submit_search and address:
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
        with sel_c2:
            st.write("")  # spacer
        with sel_c3:
            if st.button("Lock & Capture", key="lock_capture"):
                new_center = st.session_state['selector_center'][:]
                new_zoom = st.session_state['selector_zoom']
                regenerate = (
                    (st.session_state.get('map_snapshot') is None) or
                    (new_center != st.session_state.get('map_center')) or
                    (new_zoom != st.session_state.get('map_zoom'))
                )
                st.session_state['map_center'] = new_center
                st.session_state['map_zoom'] = new_zoom
                if regenerate:
                    try:
                        m_static = StaticMap(MAP_WIDTH, MAP_HEIGHT, url_template='https://a.tile.openstreetmap.org/{z}/{x}/{y}.png')
                        marker = CircleMarker((new_center[1], new_center[0]), 'red', 12)
                        m_static.add_marker(marker)
                        image = m_static.render(zoom=new_zoom)
                        buf = BytesIO()
                        image.save(buf, format='PNG')
                        st.session_state['map_snapshot'] = buf.getvalue()
                    except RuntimeError as gen_err:
                        st.error(f"Failed to capture map: {gen_err}")
                        regenerate = False
                st.session_state['map_locked'] = True
                # Not auto-switching radio (would require rerun & programmatic set). Inform user instead.
                st.info("Snapshot captured. Switch to Analyze tab to measure.")

        # Folium interactive map (center tracked but snapshot only on explicit lock)
        fmap = folium.Map(location=st.session_state['selector_center'], zoom_start=st.session_state['selector_zoom'])
        # Overlay processes as styled DivIcon 'boxes'
        for idx, p in enumerate(st.session_state['processes']):
            lat = p.get('lat'); lon = p.get('lon')
            if lat not in (None, "") and lon not in (None, ""):
                try:
                    label = p.get('name') or f"P{idx+1}"
                    html = f"""<div style='background:rgba(255,255,255,0.85);border:1px solid #333;padding:2px 6px;font-size:12px;border-radius:4px;white-space:nowrap;'>📦 {label}</div>"""
                    folium.Marker(
                        [float(lat), float(lon)],
                        tooltip=label,
                        popup=f"<b>{label}</b><br>Next: {p.get('next','')}",
                        icon=folium.DivIcon(html=html)
                    ).add_to(fmap)
                except (ValueError, TypeError):
                    pass
        fmap_data = st_folium(
            fmap,
            key="selector_map",
            width=MAP_WIDTH,
            height=MAP_HEIGHT,
            returned_objects=["center","zoom","last_clicked"],
            use_container_width=False
        )
        # Update placement if in placing mode and user clicked
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
                # keep placing mode active until user clicks Done
        if fmap_data and 'center' in fmap_data and 'zoom' in fmap_data:
            c = fmap_data['center']
            if isinstance(c, dict):
                st.session_state['selector_center'] = [c['lat'], c['lng']]
            else:
                st.session_state['selector_center'] = c
            st.session_state['selector_zoom'] = fmap_data['zoom']
        st.caption("Pan/zoom freely. Press Lock & Capture above only when you want to freeze the view.")
        if st.session_state['map_locked']:
            st.info("Snapshot locked. Switch to Analyze or Unlock there.")
    else:
        # Analysis mode
        if not st.session_state['map_locked']:
            st.warning("No locked snapshot yet. Switch to 'Select Map' and capture one.")
        else:
            # In Analyze mode on right column proceed with snapshot tools below
            top_c1, top_c2, top_c3 = st.columns([3,2,2])
            with top_c1:
                st.info("Snapshot locked")
            with top_c2:
                if not st.session_state['measure_mode']:
                    if st.button("Measure Distance", key="measure_btn"):
                        st.session_state['measure_mode'] = True
                        st.session_state['placement_mode'] = False
                        st.session_state['measure_points'] = []
                else:
                    if st.button("Reset Measurement", key="reset_measure"):
                        st.session_state['measure_points'] = []
            with top_c3:
                if st.button("Unlock", key="unlock_snapshot"):
                    st.session_state.update({'map_locked': False, 'map_snapshot': None, 'measure_mode': False, 'measure_points': []})
                    # User will manually switch back to Select Map via radio
                    # No forced rerun to avoid flicker

            # Placement handled directly via per-process Place/Done buttons in left panel

            if st.session_state.get('map_snapshot'):
                base_img = Image.open(BytesIO(st.session_state['map_snapshot'])).convert("RGBA")
                w, h = base_img.size

                # --- Overlay process boxes on snapshot ---

                draw = ImageDraw.Draw(base_img)
                font = None
                try: font = ImageFont.load_default()
                except (OSError, IOError): pass
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
                        if proc_px < -50 or proc_py < -20 or proc_px > w+50 or proc_py > h+20:
                            continue  # off image
                        label = p.get('name') or f"P{i+1}"
                        padding = 4
                        text_bbox = draw.textbbox((0,0), label, font=font) if font else (0,0,len(label)*6,10)
                        tw = text_bbox[2]-text_bbox[0]
                        th = text_bbox[3]-text_bbox[1]
                        box_w = tw + padding*2
                        box_h = th + padding*2
                        x0 = int(proc_px - box_w/2)
                        y0 = int(proc_py - box_h/2)
                        x1 = x0 + box_w
                        y1 = y0 + box_h
                        # clamp
                        if x1 < 0 or y1 < 0 or x0 > w or y0 > h:
                            continue
                        draw.rectangle([x0, y0, x1, y1], fill=(255,255,255,220), outline=(0,0,0,255), width=1)
                        tx = x0 + padding
                        ty = y0 + padding
                        draw.text((tx, ty), label, fill=(0,0,0,255), font=font)
                    except (ValueError, TypeError):
                        continue
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
                    st.success(f"Distance: {dist_m:.2f} meters ({dist_m/1000:.3f} km)")
            else:
                st.warning("Snapshot missing. Unlock and re-capture if needed.")
