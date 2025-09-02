import pandas as pd
import io
from typing import List, Dict, Tuple, Optional

def init_process_state(session_state):
    if 'processes' not in session_state:
        session_state['processes'] = []  # list of proc dicts
    if 'selected_process_idx' not in session_state:
        session_state['selected_process_idx'] = None

REQUIRED_PROC_COLS = {"name","next","conntemp","connm","conncp","stream_no","mdot","temp_in","temp_out","cp"}

def parse_process_csv_file(uploaded_file) -> Tuple[Optional[list], str]:
    if uploaded_file is None:
        return None, "No file provided"
    try:
        content = uploaded_file.read()
        text = content.decode('utf-8')
        df = pd.read_csv(io.StringIO(text))
        if not REQUIRED_PROC_COLS.issubset(df.columns):
            return None, "CSV missing required columns"
        procs = []
        proc_lookup = {}
        for _, row in df.iterrows():
            key = (row['name'], row['next'], row['conntemp'], row['connm'], row['conncp'])
            if key not in proc_lookup:
                p = {
                    "name": row.get('name',''),
                    "next": row.get('next',''),
                    "conntemp": row.get('conntemp',''),
                    "connm": row.get('connm',''),
                    "conncp": row.get('conncp',''),
                    "streams": [],
                    "lat": row.get('lat') if 'lat' in df.columns else None,
                    "lon": row.get('lon') if 'lon' in df.columns else None,
                }
                procs.append(p)
                proc_lookup[key] = p
            stream_no = row.get('stream_no')
            if pd.notna(stream_no):
                proc_lookup[key]['streams'].append({
                    "mdot": row.get('mdot',''),
                    "temp_in": row.get('temp_in',''),
                    "temp_out": row.get('temp_out',''),
                    "cp": row.get('cp',''),
                })
        return procs, f"Loaded {len(procs)} processes"
    except (UnicodeDecodeError, OSError, ValueError) as e:
        return None, f"Failed: {e}"

def processes_to_csv_bytes(processes: List[Dict]) -> bytes:
    rows = []
    for p in processes:
        if not p.get('streams'):
            rows.append({
                'name': p.get('name',''), 'next': p.get('next',''), 'conntemp': p.get('conntemp',''),
                'connm': p.get('connm',''), 'conncp': p.get('conncp',''), 'stream_no': '', 'mdot':'','temp_in':'','temp_out':'','cp':'',
                'lat': p.get('lat'), 'lon': p.get('lon')
            })
        else:
            for idx, s in enumerate(p['streams'], start=1):
                rows.append({
                    'name': p.get('name',''), 'next': p.get('next',''), 'conntemp': p.get('conntemp',''),
                    'connm': p.get('connm',''), 'conncp': p.get('conncp',''), 'stream_no': idx,
                    'mdot': s.get('mdot',''), 'temp_in': s.get('temp_in',''), 'temp_out': s.get('temp_out',''), 'cp': s.get('cp',''),
                    'lat': p.get('lat'), 'lon': p.get('lon')
                })
    df = pd.DataFrame(rows)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode('utf-8')

def add_process(session_state):
    session_state['processes'].append({
        'name':'','next':'','conntemp':'','connm':'','conncp':'','streams':[], 'lat':None,'lon':None
    })
    session_state['selected_process_idx'] = len(session_state['processes'])-1

def delete_process(session_state, idx):
    if 0 <= idx < len(session_state['processes']):
        session_state['processes'].pop(idx)
        if session_state['selected_process_idx'] == idx:
            session_state['selected_process_idx'] = None

def add_stream_to_process(session_state, pidx):
    if 0 <= pidx < len(session_state['processes']):
        session_state['processes'][pidx]['streams'].append({'mdot':'','temp_in':'','temp_out':'','cp':''})

def delete_stream_from_process(session_state, pidx, sidx):
    if 0 <= pidx < len(session_state['processes']):
        streams = session_state['processes'][pidx]['streams']
        if 0 <= sidx < len(streams):
            streams.pop(sidx)
