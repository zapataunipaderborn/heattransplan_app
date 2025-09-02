import streamlit as st
import requests
from streamlit_folium import st_folium
import folium
from io import BytesIO
from PIL import Image
from staticmap import StaticMap, CircleMarker
from streamlit_image_coordinates import streamlit_image_coordinates
from math import radians, cos, sin, sqrt, atan2

st.set_page_config(page_title="Process Analysis", layout="wide")

# Compact top padding & utility CSS to keep map tight to top-right
st.markdown("""
<style>
/* Reduce default padding */
.block-container {padding-top:0.6rem; padding-bottom:0.5rem;}
/* Make right column content stick to top visually */
div[data-testid="column"] > div:has(> div.map-region) {margin-top:0;}
/* Ensure control rows align */
.map-control-row {margin-bottom:0.25rem;}
</style>
""", unsafe_allow_html=True)

st.title("Process Analysis App (Streamlit)")

MAP_WIDTH = 900
MAP_HEIGHT = 600

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

left, right = st.columns([0.6, 3.0], gap="large")

with left:
    st.header("Workspace")
    st.write("(Future: process controls, diagrams, uploads, etc.)")

with right:
    mode = st.radio("Mode", ["Select Map", "Analyze"], key="ui_mode_radio", horizontal=True, index=0 if not st.session_state['map_locked'] else 1)
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
        fmap_data = st_folium(fmap, key="selector_map", width=MAP_WIDTH, height=MAP_HEIGHT, returned_objects=["center","zoom"], use_container_width=False)
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
            top_c1, top_c2, top_c3 = st.columns([3,2,2])
            with top_c1:
                st.info("Snapshot locked")
            with top_c2:
                if not st.session_state['measure_mode']:
                    if st.button("Measure Distance", key="measure_btn"):
                        st.session_state['measure_mode'] = True
                        st.session_state['measure_points'] = []
                else:
                    if st.button("Reset Measurement", key="reset_measure"):
                        st.session_state['measure_points'] = []
            with top_c3:
                if st.button("Unlock", key="unlock_snapshot"):
                    st.session_state.update({'map_locked': False, 'map_snapshot': None, 'measure_mode': False, 'measure_points': []})
                    # User will manually switch back to Select Map via radio
                    # No forced rerun to avoid flicker

            if st.session_state.get('map_snapshot'):
                img = Image.open(BytesIO(st.session_state['map_snapshot']))
                w, h = img.size
                coords = streamlit_image_coordinates(img, key="meas_img", width=w)
                if st.session_state['measure_mode']:
                    if coords is not None and len(st.session_state['measure_points']) < 2:
                        st.session_state['measure_points'].append((coords['x'], coords['y']))
                    st.session_state['measure_points'] = st.session_state['measure_points'][-2:]
                if len(st.session_state['measure_points']) == 2:
                    x1, y1 = st.session_state['measure_points'][0]
                    x2, y2 = st.session_state['measure_points'][1]
                    def pixel_to_lonlat(px, py, center_ll, z_level, img_w, img_h):
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
                    lon1, lat1 = pixel_to_lonlat(x1, y1, st.session_state['map_center'][::-1], st.session_state['map_zoom'], w, h)
                    lon2, lat2 = pixel_to_lonlat(x2, y2, st.session_state['map_center'][::-1], st.session_state['map_zoom'], w, h)
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
