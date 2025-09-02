from dash import dcc, html
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
import dash_leaflet as dl

def make_proc_fields(proc, idx):
    v = lambda k: proc.get(k,"")
    streams = proc.get("streams", [])
    stream_fields = []
    for j, s in enumerate(streams):
        sv = lambda k: s.get(k,"")
        stream_fields.append(html.Div([
            html.Label(f"Stream S{j+1}", style={"fontSize":"10px","fontWeight":"bold","marginRight": "2px"}),
            html.Label("ṁ:",style={"fontSize": "10px"}),
            dcc.Input(id={"type": "stream-mdot", "pidx": idx, "sidx": j}, value=sv("mdot"), type="text", style={"width":"32px","fontSize":"10px","marginRight":"3px"}),
            html.Label("Temp_in:",style={"fontSize": "10px"}),
            dcc.Input(id={"type": "stream-tempin", "pidx": idx, "sidx": j}, value=sv("temp_in"), type="text", style={"width":"32px","fontSize":"10px","marginRight":"3px"}),
            html.Label("Temp out:",style={"fontSize": "10px"}),
            dcc.Input(id={"type": "stream-tempout", "pidx": idx, "sidx": j}, value=sv("temp_out"), type="text", style={"width":"32px","fontSize":"10px","marginRight":"3px"}),
            html.Label("cp:",style={"fontSize": "10px"}),
            dcc.Input(id={"type": "stream-cp", "pidx": idx, "sidx": j}, value=sv("cp"), type="text", style={"width":"32px","fontSize":"10px","marginRight":"3px"}),
            html.Button("×", id={"type":"delete-stream","pidx":idx,"sidx":j}, n_clicks=0, style={"fontSize":"8px","padding":"1px 4px","backgroundColor":"#ff6b6b","color":"white","border":"none","borderRadius":"3px","cursor":"pointer","marginLeft":"2px"}),
        ], style={"marginLeft":"8px","marginTop":"1px","marginBottom":"1px","display":"flex","alignItems":"center"}))
    
    accordion_item_body = html.Div([
        html.Div([
            html.Div([
                html.Label("Process:", style={"fontSize":"9px"}),
                dcc.Input(id={"type": "proc-name", "index":idx}, value=v("name"), type="text", style={"width":"60px","fontSize":"9px",'marginRight':'6px'}),
                html.Label("Next:", style={"fontSize":"9px"}),
                dcc.Input(id={"type": "next-proc", "index":idx}, value=v("next"), type="text", style={"width":"70px","fontSize":"9px","marginRight":"6px"}),
                html.Button("×", id={"type":"delete-proc","index":idx}, n_clicks=0, style={"fontSize":"8px","padding":"1px 4px","backgroundColor":"#ff6b6b","color":"white","border":"none","borderRadius":"3px","cursor":"pointer"}),
            ], style={"display":"flex", "alignItems":"center","marginBottom":"2px"}),
            html.Div([
                html.Label("Product:", style={"fontWeight":"bold","fontSize":"9px","marginRight":"4px"}),
                html.Label("Temp:", style={"fontSize":"9px"}),
                dcc.Input(id={"type": "conntemp", "index":idx}, value=v("conntemp"), type="text", style={"width":"35px","fontSize":"9px","marginRight":"4px"}),
                html.Label("ṁ:", style={"fontSize":"9px"}),
                dcc.Input(id={"type": "connm", "index":idx}, value=v("connm"), type="text", style={"width":"35px","fontSize":"9px","marginRight":"4px"}),
                html.Label("cp:", style={"fontSize":"9px"}),
                dcc.Input(id={"type": "conncp", "index":idx}, value=v("conncp"), type="text", style={"width":"35px","fontSize":"9px"}),
            ], style={"display":"flex","alignItems":"center","marginTop":"2px"}),
            html.Div(stream_fields, style={"marginLeft":"2px"}),
            html.Button("Add Stream", id={"type":"add-stream","index":idx}, n_clicks=0, style={"fontSize":"9px","marginTop":"6px","marginLeft":"2px","marginBottom":"3px"}),
        ], style={'display':'block','border':'1px solid #aac','borderRadius':'8px','marginTop':'0px','marginBottom':'5px','background':'#F8FBFC','boxShadow':'1px 2px 4px #eaeaea','padding':'5px'}),
    ])

    return dbc.AccordionItem(
        accordion_item_body,
        title=f"{v('name') or 'Process '+str(idx+1)}",
        item_id=f"proc-accordion-item-{idx}"
    )


def create_layout():
    modal = dbc.Modal([
        dbc.ModalHeader("Select Map Area"),
        dbc.ModalBody([
            dbc.Row([
                dbc.Col(dcc.Input(id='address-input', placeholder='Enter address to search...', type='text', style={'width':'100%'})),
                dbc.Col(dbc.Button("Search", id='address-search-btn', n_clicks=0, color='primary'), width="auto")
            ], align="center", style={"marginBottom": "10px"}),
            dl.Map(id='map-view', center=[56, 10], zoom=6, children=[
                dl.TileLayer(),
            ], style={'width': '100%', 'height': '60vh'})
        ]),
        dbc.ModalFooter([
            dbc.Button("Take Image", id='take-map-image-btn', n_clicks=0, color="success"),
            dbc.Button("Close", id='close-map-modal-btn', n_clicks=0, className="ms-auto")
        ])
    ], id="map-modal", is_open=False, size="xl")

    return html.Div([
        dcc.Store(id='proc-store', data=[]),
        dcc.Store(id='cyto-bg-store'),
        dcc.Store(id="process-csv-upload-store"),
        dcc.Store(id='tab-active-proc', data=0),
        dcc.Store(id='map-viewport-store'),
        html.Div(id="alert-container", style={"position": "fixed", "top": "10px", "right": "10px", "zIndex": "1050"}),
        modal,
        html.Div([
            html.Div([
                html.Div([
                    html.Img(src="/assets/logo.png", style={"height":"120px", "marginBottom":"10px"}),
                    html.H2("Controls", style={"fontSize":"14px","marginBottom":"6px"}),
                    html.Div([
                        html.Button("Add Process", id="add-proc", n_clicks=0, style={"fontSize":"10px","padding":"5px 8px"}),
                        dcc.Upload(
                            id="upload-process-csv",
                            children=html.Button('Upload Process CSV', style={"fontSize":"10px","padding":"5px 8px","color":"#1787bf", "fontWeight":"bold"}),
                            multiple=False
                        ),
                        html.Button("Save data as CSV", id="save-csv-btn", n_clicks=0, style={"fontSize":"10px","padding":"5px 8px","background":"#1787bf","color":"white","border":"none","borderRadius":"4px","cursor":"pointer"}),
                        dcc.Upload(
                            id='process-csv-upload',
                            children=html.Button('Upload Activity CSV', style={'fontSize': '10px', 'padding': '5px 8px'}),
                            multiple=False,
                        ),
                        html.Button(
                            "Map Activities",
                            id="open-mapping-modal-btn",
                            n_clicks=0,
                            style={'fontSize': '10px', 'padding':'5px 8px'}
                        ),
                    ], style={'display':'flex', 'flexWrap':'wrap', 'gap':'8px', 'marginBottom':'12px'}),
                    dcc.Download(id="csv-download"),
                    html.Div(id='process-csv-upload-status', style={"fontSize":"11px", "minHeight": "18px"}),
                    html.Div(id='csv-upload-status', style={"fontSize":"11px", "minHeight": "18px"}),
                    html.Hr(style={"marginTop":"10px"}),
                ]),
                html.Div(id="proc-tabs-area", style={"overflowY":"auto","flex":"1"}),
            ], style={
                "width":"380px","display":"flex","flexDirection":"column",
                "marginRight":"13px","height":"90vh","boxSizing":"border-box"
            }),
            html.Div([
                html.Div([
                    html.Div([
                        dcc.Upload(
                            id='bg-img-upload',
                            children=html.Button('Upload Background Image', style={"fontSize":"10px", "padding":"2px 7px"}),
                            multiple=False,
                        ),
                        html.Button('Open Map', id='open-map-modal-btn', n_clicks=0, style={"fontSize":"10px", "padding":"2px 7px", "marginLeft": "5px"}),
                    ], style={"marginTop": "10px", "marginBottom":"8px"}),
                    html.Div(
                        style={
                            'width': '100%',
                            'height': '100%',
                            'position': 'relative',
                            'backgroundSize':'contain',
                            'backgroundRepeat': 'no-repeat',
                            "backgroundPosition":"center"
                        },
                        id='cyto-bg-image-container',
                        children=[
                            cyto.Cytoscape(
                                id='process-graph',
                                layout={'name':'preset'},
                                style={
                                    'width':'100%',
                                    'height':'100%',
                                    'backgroundColor':'rgba(0,0,0,0)',
                                    "border":"1px solid #bbc",
                                    'position': 'absolute',
                                    'top': 0, 'left': 0, 'right': 0, 'bottom': 0,
                                },
                                elements=[],
                                userPanningEnabled=True, userZoomingEnabled=True, boxSelectionEnabled=True,
                                minZoom=0.1, maxZoom=5,
                                responsive=True,
                                stylesheet=[],
                            ),
                        ]
                    )
                ], id='cyto-container', style={'width':'100%', 'height':'100%', 'position':'relative', 'flex':'1'}),
            ], style={
                "flex":"1","display":"flex","flexDirection":"column",
                "minWidth":"330px","height":"90vh","boxSizing":"border-box"
            }),
        ], style={
            "display":"flex","flexDirection":"row","gap":"8px",
            "height":"92vh","boxSizing":"border-box"
        }),
        html.Div([
            html.Div(id='mapping-dialog-container'),
            html.Div(id='q-hot-cool-series-container', style={"marginTop":"28px"})
        ]),
        dcc.Store(id="csv-upload-store"),
        dcc.Store(id="csv-mapping-store"),
    ], className="appframe", style={"marginLeft":"12px","marginTop":"9px","height":"100vh"}) 