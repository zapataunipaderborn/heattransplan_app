import { Streamlit } from "streamlit-component-lib";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

let map;
let markers = [];

function render({ data }) {
  const { processes, center, zoom, height } = data;
  const root = window.rootEl;
  root.style.height = (height || 600) + "px";
  root.style.width = "100%";
  if (!map) {
    map = L.map(root).setView([center[0], center[1]], zoom);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);
  }
  // clear existing markers
  markers.forEach(m => m.remove());
  markers = [];
  processes.forEach(p => {
    if (p.lat == null || p.lon == null || p.lat === "" || p.lon === "") return;
    const label = p.name || 'proc';
    const icon = L.divIcon({
      html: `<div style="background:rgba(255,255,255,0.9);border:1px solid #000;padding:2px 6px;border-radius:4px;font-size:12px;cursor:move;">${label}</div>`
    });
    const marker = L.marker([parseFloat(p.lat), parseFloat(p.lon)], { draggable: true, icon });
    marker.on('dragend', () => {
      const pos = marker.getLatLng();
      p.lat = pos.lat.toFixed(6);
      p.lon = pos.lng.toFixed(6);
      Streamlit.setComponentValue(processes);
    });
    marker.addTo(map);
    markers.push(marker);
  });
}

Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, (e) => {
  render(e.detail);
  Streamlit.setFrameHeight();
});
Streamlit.setComponentReady();
Streamlit.setFrameHeight();
