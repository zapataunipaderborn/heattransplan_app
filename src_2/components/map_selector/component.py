import streamlit as st

# This component simulates a popup map selector by hiding it behind an expander / modal-like container
# without triggering app reruns on every pan/zoom (we defer updates until user clicks Lock & Use).

DEFAULT_CENTER = [56, 10]
DEFAULT_ZOOM = 16


def show_map_selector(label: str = "Select Map View"):
    if 'mapsel_center' not in st.session_state:
        st.session_state['mapsel_center'] = DEFAULT_CENTER
    if 'mapsel_zoom' not in st.session_state:
        st.session_state['mapsel_zoom'] = DEFAULT_ZOOM

    with st.expander(label, expanded=False):
        st.write("(Prototype) This would host a client-side map that doesn't force reruns while moving.")
        st.write("Current temp center:", st.session_state['mapsel_center'], "zoom", st.session_state['mapsel_zoom'])
        # Placeholder controls to emulate choosing a new center
        lat = st.number_input("Temp Lat", value=float(st.session_state['mapsel_center'][0]), key="_msel_lat")
        lon = st.number_input("Temp Lon", value=float(st.session_state['mapsel_center'][1]), key="_msel_lon")
        zoom = st.slider("Temp Zoom", 1, 20, value=int(st.session_state['mapsel_zoom']), key="_msel_zoom")
        if st.button("Update Temp View", key="upd_temp_view"):
            st.session_state['mapsel_center'] = [lat, lon]
            st.session_state['mapsel_zoom'] = zoom
        locked = False
        if st.button("Lock This View", key="lock_view_final"):
            locked = True
        return locked, st.session_state['mapsel_center'], st.session_state['mapsel_zoom']
