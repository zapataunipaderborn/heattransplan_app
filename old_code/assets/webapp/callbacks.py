import dash
from dash import dcc, html, ctx, no_update
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
import copy
import dash_leaflet as dl
import base64
import requests

from .layout import make_proc_fields
from .data_processing import parse_process_csv, parse_activity_csv, get_plot_figs
from .constants import NODE_WIDTH, NODE_HEIGHT, PROCS_PER_TAB

def register_callbacks(app):
    @app.callback(
        Output("cyto-bg-image-container", "style"),
        Input('cyto-bg-store', 'data'),
        State("cyto-bg-image-container", "style"),
    )
    def set_cyto_bgimg(bg_contents, old_style):
        style = dict(old_style) if old_style else {}
        if bg_contents:
            style["backgroundImage"] = f'url("{bg_contents}")'
            style["backgroundSize"] = "contain"
            style["backgroundRepeat"] = "no-repeat"
            style["backgroundPosition"] = "center"
        else:
            style.pop("backgroundImage", None)
        return style

    @app.callback(
        Output("proc-tabs-area", "children"),
        Output("tab-active-proc", "data"),
        Input("proc-store", "data"),
        Input("tab-active-proc", "data"),
        State({"type": "proc-accordion", "idx": ALL}, "active_item"),
    )
    def render_proc_tabs(procs, active_tab, active_accordion_items):
        procs = procs or []
        tabs = []
        n_proc = len(procs)
        tab_chunks = [list(range(i, min(i+PROCS_PER_TAB, n_proc))) for i in range(0, n_proc, PROCS_PER_TAB)]
        
        active_items_per_tab = active_accordion_items or []

        for ti, idxs in enumerate(tab_chunks):
            lbl = f"{idxs[0]+1}-{idxs[-1]+1}" if idxs else "-"
            accordion_items = [make_proc_fields(procs[i], i) for i in idxs]

            current_active_items = active_items_per_tab[ti] if ti < len(active_items_per_tab) else []
            
            tabs.append(
                dbc.Tab(
                    label=f"Processes {lbl}",
                    tab_id=str(ti),
                    children=dbc.Accordion(
                        accordion_items,
                        always_open=True,
                        active_item=current_active_items,
                        id={"type": "proc-accordion", "idx": ti}
                    )
                )
            )
        if not tabs:
            return html.Div("No processes. Click 'Add Process' to start.", style={"fontSize":"13px"}), 0
        if active_tab is None or int(str(active_tab)) >= len(tabs):
            active_tab = 0
        return dbc.Tabs(tabs, id="proc-tabs", active_tab=str(active_tab)), int(str(active_tab))

    @app.callback(
        Output("tab-active-proc", "data", allow_duplicate=True),
        Input("proc-tabs", "active_tab"),
        prevent_initial_call=True
    )
    def select_tab(tab):
        if tab is not None:
            return int(tab)
        return 0

    @app.callback(
        Output('process-csv-upload-status', 'children'),
        Output('process-csv-upload-store', 'data'),
        Input('upload-process-csv', 'contents'),
        prevent_initial_call=True
    )
    def load_process_csv(contents):
        procs, message = parse_process_csv(contents)
        color = "green" if procs is not None else "red"
        return html.Span(message, style={"color": color}), procs

    @app.callback(
        Output("proc-store", "data"),
        Input("add-proc", "n_clicks"),
        Input({"type": "add-stream", "index": ALL}, "n_clicks"),
        Input({"type": "delete-proc", "index": ALL}, "n_clicks"),
        Input({"type": "delete-stream", "pidx": ALL, "sidx": ALL}, "n_clicks"),
        Input({"type": "proc-name", "index": ALL}, "value"),
        Input({"type": "next-proc", "index": ALL}, "value"),
        Input({"type": "conntemp", "index": ALL}, "value"),
        Input({"type": "connm", "index": ALL}, "value"),
        Input({"type": "conncp", "index": ALL}, "value"),
        Input({"type": "stream-mdot", "pidx": ALL, "sidx": ALL}, "value"),
        Input({"type": "stream-tempin", "pidx": ALL, "sidx": ALL}, "value"),
        Input({"type": "stream-tempout", "pidx": ALL, "sidx": ALL}, "value"),
        Input({"type": "stream-cp", "pidx": ALL, "sidx": ALL}, "value"),
        Input("process-csv-upload-store", "data"),
        State("proc-store", "data"),
        prevent_initial_call=False
    )
    def editprocs(add_proc_clicks, add_stream_clicks, delete_proc_clicks, delete_stream_clicks,
                names, nexts, temps, ms, cps, smdot, stempin, stempout, scp, upload_data, procs):
        trigger = ctx.triggered_id
        if upload_data is not None and trigger == "process-csv-upload-store":
            return upload_data
        
        procs = list(procs) if procs else []
        procs = copy.deepcopy(procs)
        trig = trigger

        if trig == "add-proc":
            procs.append({"name":"", "next":"","conntemp":"","connm":"","conncp":"","streams":[]})
        elif isinstance(trig, dict):
            if trig.get("type") == "add-stream":
                pidx = trig["index"]
                if len(procs) > pidx:
                    procs[pidx].setdefault("streams", []).append({"mdot":"","temp_in":"","temp_out":"","cp":""})
            elif trig.get("type") == "delete-proc":
                pidx = trig["index"]
                if 0 <= pidx < len(procs):
                    procs.pop(pidx)
            elif trig.get("type") == "delete-stream":
                pidx = trig["pidx"]
                sidx = trig["sidx"]
                if 0 <= pidx < len(procs) and 0 <= sidx < len(procs[pidx].get("streams", [])):
                    procs[pidx]["streams"].pop(sidx)

        for i in range(len(procs)):
            if i < len(names): procs[i]["name"] = names[i]
            if i < len(nexts): procs[i]["next"] = nexts[i]
            if i < len(temps): procs[i]["conntemp"] = temps[i]
            if i < len(ms): procs[i]["connm"] = ms[i]
            if i < len(cps): procs[i]["conncp"] = cps[i]
        
        # This part is sensitive to the order of inputs in the callback decorator.
        idlist = [ctx.inputs_list[9], ctx.inputs_list[10], ctx.inputs_list[11], ctx.inputs_list[12]]
        param_maps = []
        for idx, param in enumerate([smdot, stempin, stempout, scp]):
            this_map = {}
            ids = idlist[idx]
            for field, val in zip(ids, param):
                if val is not None:
                    pid = field["id"]
                    this_map[(pid["pidx"], pid["sidx"])] = val
            param_maps.append(this_map)

        for i, proc in enumerate(procs):
            streams = proc.get("streams", [])
            for j, stream in enumerate(streams):
                stream["mdot"] = param_maps[0].get((i, j), "")
                stream["temp_in"] = param_maps[1].get((i, j), "")
                stream["temp_out"] = param_maps[2].get((i, j), "")
                stream["cp"] = param_maps[3].get((i, j), "")
        return procs

    @app.callback(
        Output("process-csv-upload-store", "data", allow_duplicate=True),
        Input("proc-store", "data"),
        prevent_initial_call=True
    )
    def clear_upload_temp(_):
        return None

    @app.callback(
        Output('cyto-bg-store', 'data', allow_duplicate=True),
        Input('bg-img-upload', 'contents'),
        prevent_initial_call=True
    )
    def store_bg_image(contents):
        return contents if contents else no_update

    @app.callback(
        Output("map-modal", "is_open"),
        [Input("open-map-modal-btn", "n_clicks"), Input("close-map-modal-btn", "n_clicks")],
        State("map-modal", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_map_modal(open_clicks, close_clicks, is_open):
        if open_clicks or close_clicks:
            return not is_open
        return is_open

    @app.callback(
        Output('map-viewport-store', 'data'),
        Input('map-view', 'viewport')
    )
    def store_map_viewport(viewport):
        return viewport

    @app.callback(
        [Output('cyto-bg-store', 'data', allow_duplicate=True),
         Output('alert-container', 'children'),
         Output("map-modal", "is_open", allow_duplicate=True)],
        Input('take-map-image-btn', 'n_clicks'),
        State('map-viewport-store', 'data'),
        prevent_initial_call=True,
    )
    def take_map_image_and_close_modal(n_clicks, viewport):
        if not n_clicks:
            raise PreventUpdate

        bounds = viewport.get('bounds') if viewport else None
        if not bounds:
            alert = dbc.Alert("Map bounds not ready. Please pan or zoom the map slightly.", color="info", dismissable=True, duration=5000)
            return no_update, alert, no_update

        min_lat, min_lon = bounds[0]
        max_lat, max_lon = bounds[1]
        bbox_str = f"{min_lon},{min_lat},{max_lon},{max_lat}"
        image_url = f"https://www.openstreetmap.org/export/png?bbox={bbox_str}"

        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            encoded_image = base64.b64encode(response.content).decode('utf-8')
            image_data_uri = f"data:image/png;base64,{encoded_image}"
            return image_data_uri, no_update, False
        except requests.exceptions.RequestException as e:
            alert = dbc.Alert(f"Failed to retrieve map image: {e}", color="danger", dismissable=True, duration=5000)
            return no_update, alert, no_update

    @app.callback(
        Output("process-graph", "elements"),
        Input("proc-store", "data"),
    )
    def render_process_graph(procs):
        procs = procs or []
        process_names = [(p.get("name") or "").strip() for p in procs if (p.get("name")or"").strip()]
        pos = {n: {'x':100+120*i, 'y':90+(i%8)*32} for i, n in enumerate(process_names)}
        nodes = []
        for i, n in enumerate(process_names):
            nodes.append({
                "data":{"id":n,"label":n},
                "position":pos[n],
                "classes":"process"
            })
        edges = []
        node_ids = {n['data']['id'] for n in nodes}
        for idx, proc in enumerate(procs):
            name = (proc.get("name") or "").strip()
            nexts = (proc.get("next") or "").split(",")
            temps = (proc.get("conntemp") or "").split(",")
            ms = (proc.get("connm") or "").split(",")
            cps = (proc.get("conncp") or "").split(",")
            for i, target in enumerate(nexts):
                target = target.strip()
                if name and target and name in node_ids and target in node_ids:
                    label = []
                    if i < len(temps) and temps[i]: label.append(f"Temp:{temps[i]}")
                    if i < len(ms) and ms[i]: label.append(f"ṁ:{ms[i]}")
                    if i < len(cps) and cps[i]: label.append(f"cp:{cps[i]}")
                    edges.append({"data":{"id":f"{name}_{target}_{i}","source":name,"target":target,"label":", ".join(label)},"classes":"connection"})
            streams = proc.get("streams",[])
            if streams and name and name in pos:
                innode = f"in_{name}"
                outnode = f"out_{name}"
                px, py = pos.get(name, {'x':0,'y':0}).values()
                nodes.append({"data":{"id":innode}, "position":{"x":px,"y":py+65}, "classes": "io-circle"})
                nodes.append({"data":{"id":outnode}, "position":{"x":px,"y":py-65}, "classes": "io-circle"})
                inlines = [f"S{sidx+1}: Temp_in:{s.get('temp_in','')}, ṁ:{s.get('mdot','')}, cp:{s.get('cp','')}" 
                        for sidx,s in enumerate(streams)]
                outlines = [f"S{sidx+1}: Temp:{s.get('temp_out','')}" for sidx,s in enumerate(streams)]
                edges.append({"data":{"id":f"{innode}->{name}","source":innode,"target":name,"label":"\n".join(inlines)},"classes":"stream-in"})
                edges.append({"data":{"id":f"{name}->{outnode}","source":name,"target":outnode,"label":"\n".join(outlines)},"classes":"stream-out"})
        return nodes + edges

    @app.callback(
        Output('map-view', 'viewport'),
        Input('address-search-btn', 'n_clicks'),
        State('address-input', 'value'),
        prevent_initial_call=True
    )
    def search_address(n_clicks, address):
        if not (n_clicks and address):
            raise PreventUpdate
        
        url = f"https://nominatim.openstreetmap.org/search?q={address}&format=json&limit=1"
        try:
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp.raise_for_status()
            data = resp.json()
            if data:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                return dict(center=(lat, lon), zoom=14)
        except (requests.RequestException, IndexError, KeyError):
            pass
        return no_update

    @app.callback(
        Output('process-graph', 'stylesheet'),
        Input('proc-store', 'data'),
    )
    def update_cyto_stylesheet(_):
        width = NODE_WIDTH
        height = NODE_HEIGHT
        font = 8
        edge_font = 7
        line_width = 1.1
        stream_line_width = 1.2
        arrow_scale = 0.7
        stream_arrow_scale = 0.5
        io_circle_size = 15
        io_circle_border = 2
        return [
            {'selector':'.process','style':{
                'shape':'rectangle',
                'background-color':'#bbe4f2',
                'label':'data(label)',
                'text-valign':'center',
                'text-halign':'center',
                'width':width,
                'height':height,
                'border-color':'#005377',
                'border-width':io_circle_border,
                'font-size':f"{font}px",
                'padding':1
            }},
            {'selector':'.connection','style':{
                'curve-style':'bezier',
                'target-arrow-shape':'triangle',
                'arrow-scale':arrow_scale,
                'line-color': 'orange',
                'target-arrow-color': 'orange',
                'width':line_width,
                'label':'data(label)',
                'font-size':f'{edge_font}px',
                'text-background-color':'#fff',
                'text-background-opacity':0.8,
                'text-background-padding':1,
                'text-margin-y':'0px',
                'color':'#104c6e',
                'z-index':10
            }},
            {'selector':'.stream-in','style':{
                'width':stream_line_width,
                'line-color':'red',
                'target-arrow-shape':'triangle',
                'target-arrow-color':'red',
                'arrow-scale':stream_arrow_scale,
                'curve-style':'bezier',
                'label':'data(label)',
                'font-size':f'{edge_font}px',
                'text-background-color':'#eef',
                'text-background-opacity':0.93,
                'text-background-padding':1,
                'text-wrap':'wrap'
            }},
            {'selector':'.stream-out','style':{
                'width':stream_line_width,
                'line-color':'red',
                'source-arrow-shape':'none',
                'target-arrow-shape':'triangle',
                'target-arrow-color':'red',
                'arrow-scale':stream_arrow_scale,
                'curve-style':'bezier',
                'label':'data(label)',
                'font-size':f'{edge_font}px',
                'text-background-color':'#eef',
                'text-background-opacity':0.93,
                'text-background-padding':1,
                'text-wrap':'wrap'
            }},
            {'selector':'.io-circle','style':{
                'shape':'ellipse',
                'background-color':'#e6f7fa',
                'border-width': io_circle_border,
                'border-color':'#8896b7',
                'width': io_circle_size,
                'height': io_circle_size,
                'z-index': 99,
                'shadow-blur': 6,
                'shadow-color':'#aaf',
            }},
        ]

    @app.callback(
        Output("csv-download", "data"),
        Input("save-csv-btn", "n_clicks"),
        State("proc-store", "data"),
        prevent_initial_call=True
    )
    def save_csv(nclicks, procs):
        rows = []
        for proc in (procs or []):
            if not proc: continue
            rowdict = dict(
                name=proc.get("name",""),
                next=proc.get("next",""),
                conntemp=proc.get("conntemp",""),
                connm=proc.get("connm",""),
                conncp=proc.get("conncp",""),
            )
            if not proc.get("streams"):
                rows.append({**rowdict, **{"stream_no":"","mdot":"","temp_in":"","temp_out":"","cp":""}})
            else:
                for i,s in enumerate(proc.get("streams",[])):
                    rowdicts = dict(
                        stream_no = f"S{i+1}",
                        mdot = s.get("mdot",""),
                        temp_in = s.get("temp_in",""),
                        temp_out = s.get("temp_out",""),
                        cp = s.get("cp",""),
                    )
                    rows.append({**rowdict, **rowdicts})
        if not rows:
            rows.append(dict(name="",next="",conntemp="",connm="",conncp="",
                            stream_no="",mdot="",temp_in="",temp_out="",cp=""))
        df = pd.DataFrame(rows)
        return dcc.send_data_frame(df.to_csv, "process_data.csv", index=False) # type: ignore

    @app.callback(
        Output('csv-upload-store', 'data'),
        Output('csv-upload-status', 'children'),
        Input('process-csv-upload', 'contents'),
        prevent_initial_call=True
    )
    def parse_uploaded_csv(contents):
        data, message = parse_activity_csv(contents)
        color = 'green' if data else 'red'
        return data, html.Div(message, style={'color': color})

    @app.callback(
        Output('mapping-dialog-container', 'children'),
        Input('open-mapping-modal-btn', 'n_clicks'),
        State('csv-upload-store', 'data'),
        State('proc-store', 'data'),
        prevent_initial_call=True
    )
    def show_mapping_dialog(map_btn, csv_json, procs):
        if not csv_json or not map_btn:
            return ""
        df = pd.read_json(csv_json, orient='split')
        activity_options = sorted(df['Activity'].unique())
        stream_labels = []
        stream_ids = []
        for pidx, proc in enumerate(procs or []):
            pname = proc.get("name","").strip()
            for sidx, stream in enumerate(proc.get("streams",[])):
                lbl = f"{pname} S{sidx+1}"
                sid = f"{pidx}-{sidx}"
                stream_labels.append(lbl)
                stream_ids.append(sid)
        if not stream_ids:
            return dbc.Alert("Define process streams first before mapping Activities.", color="warning")
        mapping_children = []
        for i, act in enumerate(activity_options):
            mapping_children.append(
                dbc.Row([
                    dbc.Col(html.Div(f"{act}", style={'fontSize':'12px','fontWeight':'bold'}), width=5),
                    dbc.Col(
                        dcc.Dropdown(
                            id={'type':'activity-stream-map-dropdown','index':i},
                            options=[{'label':lbl, 'value':sid} for lbl, sid in zip(stream_labels, stream_ids)],
                            placeholder="Select Stream",
                            style={'fontSize':'11px'}
                        ),
                        width=7
                    )
                ], align="center", style={'marginBottom':'12px'})
            )
        modal = dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Map CSV 'Activity' to process stream")),
            dbc.ModalBody([
                html.Div("For each Activity, connect to a stream (leave blank for Q=0):", style={'marginBottom':'12px'}),
                html.Div(mapping_children)
            ]),
            dbc.ModalFooter(
                dbc.Button("Done", id="done-activity-stream-mapping", color="primary", n_clicks=0)
            )
        ],
            id='mapping-dialog-modal',
            is_open=True,
            size="lg",
            backdrop='static'
        )
        return modal

    @app.callback(
        Output('csv-mapping-store', 'data'),
        Output('mapping-dialog-container', 'children', allow_duplicate=True),
        Input('done-activity-stream-mapping', 'n_clicks'),
        State('csv-upload-store', 'data'),
        State({'type':'activity-stream-map-dropdown','index':ALL}, 'value'),
        prevent_initial_call=True
    )
    def finish_mapping(nclicks, csv_json, mappings):
        if not (nclicks and csv_json):
            raise PreventUpdate
        df = pd.read_json(csv_json, orient='split')
        acts = sorted(df['Activity'].unique())
        mapping_dict = {}
        for act, stream_str in zip(acts, mappings):
            if stream_str:
                try:
                    pidx, sidx = [int(x) for x in stream_str.split('-')]
                    mapping_dict[act] = dict(pidx=pidx, sidx=sidx)
                except (ValueError, TypeError):
                    pass
        return dict(mapping=mapping_dict), ""

    @app.callback(
        Output('q-hot-cool-series-container', 'children'),
        Input('csv-mapping-store', 'data'),
        State('csv-upload-store', 'data'),
        State('proc-store', 'data'),
        prevent_initial_call=True
    )
    def plot_hot_cool_timeseries(mapping_data, csv_json, procs):
        if not (csv_json and mapping_data):
            return ""
        
        figs = get_plot_figs(csv_json, mapping_data, procs)

        if isinstance(figs, str):
            return dbc.Alert(figs, color="info")

        if not figs:
            return dbc.Alert("No data to plot.", color="info")

        graphs = []
        if len(figs) > 0:
            graphs.append(dcc.Graph(figure=figs[0]))
        else:
            graphs.append(dbc.Alert("No hot streams to plot.", color="info"))

        if len(figs) > 1:
            graphs.append(dcc.Graph(figure=figs[1]))
        else:
            graphs.append(dbc.Alert("No cool streams to plot.", color="info"))
        
        return html.Div(graphs) 