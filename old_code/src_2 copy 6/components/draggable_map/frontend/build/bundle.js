// Lightweight bundle (no build step) for draggable map component
(function(){
  function loadScript(src){return new Promise((res,rej)=>{const s=document.createElement('script');s.src=src;s.onload=res;s.onerror=rej;document.head.appendChild(s);});}
  function loadCSS(href){const l=document.createElement('link');l.rel='stylesheet';l.href=href;document.head.appendChild(l);}
  async function ensureLibs(){
    if(!window.L){loadCSS('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css');await loadScript('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js');}
    if(!window.streamlitComponentReady){/* Streamlit injects streamlit-component-lib runtime */}
  }
  let map; let markers=[]; let lastData=null;
  function render(data){
    const { processes, center, zoom, height } = data;
    const root = window.rootEl; root.style.height=(height||600)+'px'; root.style.width='100%';
    if(!map){ map=L.map(root).setView([center[0], center[1]], zoom); L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19}).addTo(map);} 
    markers.forEach(m=>m.remove()); markers=[];
    (processes||[]).forEach(p=>{ if(p.lat==null||p.lon==null||p.lat===''||p.lon==='') return; const label=p.name||'proc'; const icon=L.divIcon({html:`<div style="background:rgba(255,255,255,0.9);border:1px solid #000;padding:2px 6px;border-radius:4px;font-size:12px;cursor:move;">${label}</div>`}); const marker=L.marker([parseFloat(p.lat), parseFloat(p.lon)],{draggable:true,icon}); marker.on('dragend',()=>{const pos=marker.getLatLng(); p.lat=pos.lat.toFixed(6); p.lon=pos.lng.toFixed(6); window.Streamlit.setComponentValue(processes);}); marker.addTo(map); markers.push(marker); });
  }
  async function init(){ await ensureLibs(); window.Streamlit.events.addEventListener(window.Streamlit.RENDER_EVENT, e=>{ const payload=e.detail.data; if(!lastData||JSON.stringify(payload)!==JSON.stringify(lastData)){ lastData=payload; render(payload); } window.Streamlit.setFrameHeight();}); window.Streamlit.setComponentReady(); window.Streamlit.setFrameHeight(); }
  if(window.Streamlit) init(); else window.addEventListener('load', init);
})();