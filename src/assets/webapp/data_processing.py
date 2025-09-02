import pandas as pd
import base64
import io
from itertools import cycle
import plotly.graph_objects as go


def parse_process_csv(contents):
    if not contents:
        return None, "No content"
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        text = decoded.decode('utf-8')
        df = pd.read_csv(io.StringIO(text))
        req_cols = {"name", "next", "conntemp", "connm", "conncp", "stream_no", "mdot", "temp_in", "temp_out", "cp"}
        if not req_cols.issubset(df.columns):
            return None, "Invalid CSV columns!"
        procs = []
        proc_lookup = {}
        for _, row in df.iterrows():
            proc_key = (row['name'], row['next'], row['conntemp'], row['connm'], row['conncp'])
            if proc_key not in proc_lookup:
                p = {
                    "name": "" if pd.isna(row.get("name")) else row.get("name"),
                    "next": "" if pd.isna(row.get("next")) else row.get("next"),
                    "conntemp": "" if pd.isna(row.get("conntemp")) else row.get("conntemp"),
                    "connm": "" if pd.isna(row.get("connm")) else row.get("connm"),
                    "conncp": "" if pd.isna(row.get("conncp")) else row.get("conncp"),
                    "streams": [],
                }
                procs.append(p)
                proc_lookup[proc_key] = p
            else:
                p = proc_lookup[proc_key]
            stream_no = row.get("stream_no")
            if pd.notna(stream_no) and str(stream_no).strip():
                s = {
                    "mdot": "" if pd.isna(row.get("mdot")) else row.get("mdot"),
                    "temp_in": "" if pd.isna(row.get("temp_in")) else row.get("temp_in"),
                    "temp_out": "" if pd.isna(row.get("temp_out")) else row.get("temp_out"),
                    "cp": "" if pd.isna(row.get("cp")) else row.get("cp"),
                }
                p["streams"].append(s)
        return procs, "Process CSV loaded successfully!"
    except Exception as e:
        return None, f"Could not parse: {e}"

def parse_activity_csv(contents):
    if not contents:
        return None, ""
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        try:
            text = decoded.decode('utf-8')
        except:
            text = decoded.decode('latin1')
        df = pd.read_csv(io.StringIO(text))
        needed = {"Ca_ID", "Activity", "Timestamp", "Process", "Type"}
        if not all(col in df.columns for col in needed):
            return None, f"Error: CSV must have columns: {', '.join(needed)}"
        return df.to_json(date_format='iso', orient='split'), f"Loaded {len(df)} rows"
    except Exception as e:
        return None, f"Error during parsing: {e}"


def get_plot_figs(csv_json, mapping_data, procs):
    if not (csv_json and mapping_data and procs):
        return []

    df = pd.read_json(csv_json, orient='split')
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    mapping = mapping_data.get('mapping', {})
    df = df[df['Activity'].map(lambda a: a in mapping)].copy()
    if df.empty:
        return "No mapped activities to plot."

    label_dict = {}
    for activity, m in mapping.items():
        pidx, sidx = m['pidx'], m['sidx']
        if pidx >= len(procs): continue
        proc = procs[pidx]
        pname = (proc.get('name') or f'Process {pidx+1}')
        label_dict[activity] = f"{pname} S{sidx+1}"

    min_time = df['Timestamp'].min().floor('1min')
    max_time = df['Timestamp'].max().ceil('1min')
    time_range = pd.date_range(min_time, max_time, freq='1min')

    hot_streams = {}
    cool_streams = {}

    for activity, group in df.groupby('Activity'):
        mapinfo = mapping.get(activity)
        if not mapinfo: continue
        pidx, sidx = mapinfo['pidx'], mapinfo['sidx']
        if pidx >= len(procs): continue
        proc = procs[pidx]
        pname = (proc.get("name") or f"Process {pidx+1}")
        streams = proc.get("streams", [])
        if sidx >= len(streams): continue
        stream = streams[sidx]
        label = f"{pname} S{sidx+1}"

        for _, events in group.groupby('Ca_ID'):
            starts = events[events['Type'].str.lower() == 'start'].sort_values('Timestamp')
            ends = events[events['Type'].str.lower() == 'end'].sort_values('Timestamp')

            for (start_idx, start_row), (end_idx, end_row) in zip(starts.iterrows(), ends.iterrows()):
                start = start_row['Timestamp']
                end = end_row['Timestamp']
                if pd.isnull(start) or pd.isnull(end) or end < start:
                    continue
                try:
                    m = float(stream.get("mdot", 0) or 0)
                    cp = float(stream.get("cp", 0) or 0)
                    t_in = float(stream.get("temp_in", 0) or 0)
                    t_out = float(stream.get("temp_out", 0) or 0)
                    qval = m * cp * (t_in - t_out)
                except (ValueError, TypeError):
                    continue

                if not isinstance(start, pd.Timestamp) or not isinstance(end, pd.Timestamp):
                    continue

                ts_mask = (time_range >= start.floor('1min')) & (time_range <= end.ceil('1min'))
                
                target_streams = None
                if t_in < t_out:
                    target_streams = hot_streams
                elif t_in > t_out:
                    target_streams = cool_streams
                
                if target_streams is not None:
                    s = target_streams.setdefault(label, pd.Series(0.0, index=time_range))
                    s.loc[ts_mask] = abs(qval)
                    interval_times = time_range[ts_mask]
                    if len(interval_times) > 0:
                        idx_start = interval_times[0]
                        idx_end = interval_times[-1]
                        pos_start = time_range.get_loc(idx_start)
                        pos_end = time_range.get_loc(idx_end)
                        if isinstance(pos_start, int) and pos_start > 0:
                            s.at[time_range[pos_start-1]] = 0.0
                        if isinstance(pos_end, int) and pos_end < len(time_range) - 1:
                            s.at[time_range[pos_end+1]] = 0.0

    figs = []
    hot_colors = cycle(['red', 'orange', 'orangered', 'tomato', 'darkorange', 'firebrick', 'crimson'])
    cool_colors = cycle(['blue', 'deepskyblue', 'dodgerblue', 'mediumblue', 'royalblue', 'slateblue', 'teal'])

    if hot_streams:
        fig_hot = go.Figure()
        for label, s in hot_streams.items():
            color = next(hot_colors)
            fig_hot.add_trace(go.Scatter(x=s.index, y=s.values, mode='lines+markers', name=label, line=dict(color=color)))
        fig_hot.update_layout(title="Hot thermal power", yaxis_title="Q", height=340, margin=dict(l=20, r=20, b=30, t=36), legend_title_text='Stream', showlegend=True)
        figs.append(fig_hot)

    if cool_streams:
        fig_cool = go.Figure()
        for label, s in cool_streams.items():
            color = next(cool_colors)
            fig_cool.add_trace(go.Scatter(x=s.index, y=s.values, mode='lines+markers', name=label, line=dict(color=color)))
        fig_cool.update_layout(title="Cool thermal power", yaxis_title="Q", height=340, margin=dict(l=20, r=20, b=30, t=36), legend_title_text='Stream', showlegend=True)
        figs.append(fig_cool)

    return figs 