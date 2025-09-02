import streamlit as st
from streamlit_folium import st_folium
import folium
import requests
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
if 'map_locked' not in st.session_state:
    st.session_state['map_locked'] = False
if 'map_snapshot' not in st.session_state:
    st.session_state['map_snapshot'] = None
if 'map_center' not in st.session_state:
    st.session_state['map_center'] = [56, 10]
if 'map_zoom' not in st.session_state:
    st.session_state['map_zoom'] = 16

# Apply any pending map view (center/zoom) captured from prior interaction BEFORE rendering map
if 'pending_map_view' in st.session_state:
    pend = st.session_state.pop('pending_map_view')
    if isinstance(pend, dict):
        new_c = pend.get('center')
        new_z = pend.get('zoom')
        if new_c and isinstance(new_c, (list, tuple)) and len(new_c) == 2:
            st.session_state['map_center'] = list(new_c)
        if isinstance(new_z, (int, float)):
            st.session_state['map_zoom'] = new_z

left, right = st.columns([0.6, 3.0], gap="large")

with left:
    st.header("Workspace")
    st.write("(Future: process controls, diagrams, uploads, etc.)")

with right:
    # A wrapper div (class map-region) to help CSS adjust spacing
    with st.container():
        if not st.session_state['map_locked']:
            # Control row (search + lock)
            control_col1, control_col2, control_col3 = st.columns([3,2,2])
            with control_col1:
                address = st.text_input("Search address", key="address_input")
            with control_col2:
                if st.button("Search", key="search_btn") and address:
                    url = f"https://nominatim.openstreetmap.org/search?q={address}&format=json&limit=1"
                    try:
                        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                        resp.raise_for_status()
                        data = resp.json()
                        if data:
                            found_lat = float(data[0]["lat"])
                            found_lon = float(data[0]["lon"])
                            st.session_state['map_center'] = [found_lat, found_lon]
                            st.session_state['map_zoom'] = 16
                        else:
                            st.warning("Address not found.")
                    except requests.exceptions.Timeout:
                        st.error("Address search timed out.")
                    except requests.exceptions.RequestException as req_err:
                        st.error(f"Search failed: {req_err}")
            with control_col3:
                if st.button("Take Image (Lock Map)", key="take_img"):
                    st.session_state['map_locked'] = True
                    # Generate static map image using staticmap (high-res)
                    cur_lat, cur_lon = st.session_state['map_center']
                    cur_zoom = st.session_state['map_zoom']
                    try:
                        m = StaticMap(MAP_WIDTH, MAP_HEIGHT, url_template='https://a.tile.openstreetmap.org/{z}/{x}/{y}.png')
                        marker = CircleMarker((cur_lon, cur_lat), 'red', 12)
                        m.add_marker(marker)
                        image = m.render(zoom=cur_zoom)
                        buf = BytesIO()
                        image.save(buf, format='PNG')
                        st.session_state['map_snapshot'] = buf.getvalue()
                    except RuntimeError as gen_err:
                        st.session_state['map_snapshot'] = None
                        st.session_state['map_error'] = str(gen_err)
                        st.error(f"Failed to generate static map image: {gen_err}")

            # Interactive map
            m = folium.Map(location=st.session_state['map_center'], zoom_start=st.session_state['map_zoom'])
            map_data = st_folium(m, key="main_map", width=MAP_WIDTH, height=MAP_HEIGHT, returned_objects=["center", "zoom"])
            if map_data and 'center' in map_data and 'zoom' in map_data:
                incoming_center = map_data['center']
                if isinstance(incoming_center, dict):
                    new_center = [incoming_center['lat'], incoming_center['lng']]
                else:
                    new_center = incoming_center
                new_zoom = map_data['zoom']
                # Instead of updating immediately (causing one-interaction lag), store as pending for next run pre-render
                changed = (new_center != st.session_state['map_center']) or (new_zoom != st.session_state['map_zoom'])
                if changed:
                    st.session_state['pending_map_view'] = {'center': new_center, 'zoom': new_zoom}
            st.caption("Pan/zoom the map, search for an address, then click 'Take Image' to lock it.")
        else:
            # Show an identical control row layout, but only Unlock button in former lock button slot
            control_col1, control_col2, control_col3 = st.columns([3,2,2])
            with control_col1:
                st.empty()  # Keep column structure for alignment
            with control_col2:
                st.info("Map locked")
            with control_col3:
                if st.button("Unlock Map", key="unlock_map"):
                    st.session_state.update({'map_locked': False, 'map_snapshot': None, 'measure_mode': False, 'measure_points': []})

            # Measurement features stay under control row
            if 'measure_mode' not in st.session_state:
                st.session_state['measure_mode'] = False
            if 'measure_points' not in st.session_state:
                st.session_state['measure_points'] = []

            meas_col1, meas_col2 = st.columns([1,2])
            with meas_col1:
                if not st.session_state['measure_mode']:
                    if st.button("Measure Distance", key="measure_btn"):
                        st.session_state['measure_mode'] = True
                        st.session_state['measure_points'] = []
                else:
                    if st.button("Reset Measurement", key="reset_measure"):
                        st.session_state['measure_points'] = []
            with meas_col2:
                if st.session_state['measure_mode']:
                    st.write("Click two points on the image to measure distance.")

            if st.session_state.get('map_snapshot'):
                img = Image.open(BytesIO(st.session_state['map_snapshot']))
                w, h = img.size
                coords = streamlit_image_coordinates(img, key="meas_img", width=w)
                if st.session_state['measure_mode']:
                    if coords is not None:
                        if len(st.session_state['measure_points']) < 2:
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
                st.warning("No static map image available.")
                if st.button("Retry Generate Static Map", key="retry_static_map"):
                    r_lat, r_lon = st.session_state['map_center']
                    r_zoom = st.session_state['map_zoom']
                    try:
                        m = StaticMap(MAP_WIDTH, MAP_HEIGHT, url_template='https://a.tile.openstreetmap.org/{z}/{x}/{y}.png')
                        marker = CircleMarker((r_lon, r_lat), 'red', 12)
                        m.add_marker(marker)
                        image = m.render(zoom=r_zoom)
                        buf = BytesIO()
                        image.save(buf, format='PNG')
                        st.session_state['map_snapshot'] = buf.getvalue()
                        st.experimental_rerun()
                    except RuntimeError as regen_err:
                        st.session_state['map_snapshot'] = None
                        st.session_state['map_error'] = str(regen_err)
                        st.error(f"Failed to generate static map image: {regen_err}")
