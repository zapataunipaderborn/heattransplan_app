import os
import json
import streamlit as st
from streamlit.components.v1 import declare_component

_component_func = declare_component(
    "draggable_map",
    path=os.path.join(os.path.dirname(__file__), "frontend", "build")
)

def draggable_map(processes, center, zoom, height=600, key=None):
    """Render a Leaflet map with draggable process boxes.

    processes: list of dicts with at least name, lat, lon
    Returns possibly updated list of process dicts (only lat/lon may change).
    """
    payload = {
        "processes": processes,
        "center": center,
        "zoom": zoom,
        "height": height,
    }
    updated = _component_func(data=payload, key=key, default=None)
    if updated is not None:
        try:
            upd_map = {p['name']: p for p in updated if isinstance(p, dict) and 'name' in p}
            for p in processes:
                up = upd_map.get(p.get('name'))
                if up is None:
                    continue
                lat_v = up.get('lat'); lon_v = up.get('lon')
                if lat_v is not None and lon_v is not None:
                    p['lat'] = lat_v
                    p['lon'] = lon_v
        except (TypeError, KeyError):
            pass
    return processes
