import streamlit as st
import sys
import os
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import tempfile
import csv

# Add the pinch_tool directory to the path for imports
pinch_tool_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'pinch_tool'))
if pinch_tool_path not in sys.path:
    sys.path.insert(0, pinch_tool_path)

# Import pinch analysis modules
try:
    from Modules.Pinch.Pinch import Pinch
    PINCH_AVAILABLE = True
    PINCH_IMPORT_ERROR = None
except ImportError as e:
    PINCH_AVAILABLE = False
    PINCH_IMPORT_ERROR = str(e)

st.set_page_config(
    page_title="Potential Analysis",
    initial_sidebar_state="collapsed"
)

# Apply styles immediately to prevent flash
st.markdown(
    """
    <style>
    :root {
        font-size: 11px !important;
    }
    section[data-testid="stSidebar"][aria-expanded="true"] {
        width: 180px !important;
        min-width: 180px !important;
    }
    section[data-testid="stSidebar"][aria-expanded="false"] {
        width: 0 !important;
        min-width: 0 !important;
        margin-left: 0 !important;
    }
    
    /* Smaller fonts and elements - apply to all elements */
    html, body, .stApp, * {font-size:11px !important;}
    .stMarkdown p, .stMarkdown span, .stMarkdown li {font-size:11px !important; margin:0 !important; padding:0 !important;}
    .stButton button {font-size:10px !important; padding:0.1rem 0.3rem !important;}
    .stTextInput input, .stNumberInput input {font-size:10px !important; padding:0.1rem 0.2rem !important;}
    h1 {font-size: 1.5rem !important; margin-bottom: 0.3rem !important;}
    /* Compact layout */
    .block-container {padding-top: 1rem !important; padding-bottom: 0 !important;}
    div[data-testid="stVerticalBlock"] > div {padding: 0 !important; margin: 0 !important;}
    hr {margin: 0.3rem 0 !important;}
    .stCheckbox {margin: 0 !important; padding: 0 !important;}
    div[data-testid="stHorizontalBlock"] {gap: 0.2rem !important;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Potential Analysis")

# Initialize session state for selections if not exists
if 'selected_items' not in st.session_state:
    st.session_state['selected_items'] = {}

# Get processes from session state
processes = st.session_state.get('processes', [])

if not processes:
    st.info("No processes found. Please add processes in the Data Collection page first.")
else:
    # Helper function to determine stream type and extract data
    def get_stream_info(stream):
        """Extract Tin, Tout, mdot, cp, CP from stream and determine if HOT or COLD.
        Calculate Q = CP * (Tout - Tin).
        CP can be provided directly, or calculated as mdot * cp.
        """
        properties = stream.get('properties', {})
        values = stream.get('values', {})
        
        # Also check stream_values (new structure)
        stream_values = stream.get('stream_values', {})
        if not stream_values:
            stream_values = stream.get('product_values', {})
        
        tin = None
        tout = None
        mdot = None
        cp_val = None
        CP_direct = None  # CP provided directly
        
        # First try stream_values (new structure)
        if stream_values:
            if 'Tin' in stream_values and stream_values['Tin']:
                try:
                    tin = float(stream_values['Tin'])
                except (ValueError, TypeError):
                    pass
            if 'Tout' in stream_values and stream_values['Tout']:
                try:
                    tout = float(stream_values['Tout'])
                except (ValueError, TypeError):
                    pass
            if 'ṁ' in stream_values and stream_values['ṁ']:
                try:
                    mdot = float(stream_values['ṁ'])
                except (ValueError, TypeError):
                    pass
            if 'cp' in stream_values and stream_values['cp']:
                try:
                    cp_val = float(stream_values['cp'])
                except (ValueError, TypeError):
                    pass
            if 'CP' in stream_values and stream_values['CP']:
                try:
                    CP_direct = float(stream_values['CP'])
                except (ValueError, TypeError):
                    pass
        
        # Check properties dict structure
        if isinstance(properties, dict) and isinstance(values, dict):
            for pk, pname in properties.items():
                vk = pk.replace('prop', 'val')
                v = values.get(vk, '')
                
                if pname == 'Tin' and v and tin is None:
                    try:
                        tin = float(v)
                    except (ValueError, TypeError):
                        pass
                elif pname == 'Tout' and v and tout is None:
                    try:
                        tout = float(v)
                    except (ValueError, TypeError):
                        pass
                elif pname == 'ṁ' and v and mdot is None:
                    try:
                        mdot = float(v)
                    except (ValueError, TypeError):
                        pass
                elif pname == 'cp' and v and cp_val is None:
                    try:
                        cp_val = float(v)
                    except (ValueError, TypeError):
                        pass
                elif pname == 'CP' and v and CP_direct is None:
                    try:
                        CP_direct = float(v)
                    except (ValueError, TypeError):
                        pass
        
        # Fallback to legacy fields
        if tin is None and stream.get('temp_in'):
            try:
                tin = float(stream['temp_in'])
            except (ValueError, TypeError):
                pass
        if tout is None and stream.get('temp_out'):
            try:
                tout = float(stream['temp_out'])
            except (ValueError, TypeError):
                pass
        if mdot is None and stream.get('mdot'):
            try:
                mdot = float(stream['mdot'])
            except (ValueError, TypeError):
                pass
        if cp_val is None and stream.get('cp'):
            try:
                cp_val = float(stream['cp'])
            except (ValueError, TypeError):
                pass
        
        # Determine stream type
        stream_type = None
        if tin is not None and tout is not None:
            if tin > tout:
                stream_type = "HOT"
            else:
                stream_type = "COLD"
        
        # Determine CP: use direct CP if provided, otherwise calculate from mdot * cp
        CP_flow = None
        if CP_direct is not None:
            CP_flow = CP_direct
        elif mdot is not None and cp_val is not None:
            CP_flow = mdot * cp_val
        
        # Calculate Q = CP * |Tout - Tin| (always positive)
        Q = None
        if CP_flow is not None and tin is not None and tout is not None:
            Q = abs(CP_flow * (tout - tin))
        
        return {
            'tin': tin,
            'tout': tout,
            'mdot': mdot,
            'cp': cp_val,
            'CP': CP_flow,
            'Q': Q,
            'type': stream_type
        }
    
    # Display each process and its streams
    for idx, process in enumerate(processes):
        process_name = process.get('name', f'Subprocess {idx + 1}')
        
        # Only show process header if it has streams
        streams = process.get('streams', [])
        if streams:
            st.markdown(f"**{process_name}**")
            
            for stream_idx, stream in enumerate(streams):
                stream_key = f"stream_{idx}_{stream_idx}"
                if stream_key not in st.session_state['selected_items']:
                    st.session_state['selected_items'][stream_key] = False
                
                stream_cols = st.columns([0.05, 0.25, 0.7])
                stream_selected = stream_cols[0].checkbox(
                    "S",
                    key=f"cb_{stream_key}",
                    value=st.session_state['selected_items'][stream_key],
                    label_visibility="collapsed"
                )
                st.session_state['selected_items'][stream_key] = stream_selected
                
                # Display stream name
                stream_name = stream.get('name', f'Stream {stream_idx + 1}')
                stream_cols[1].write(stream_name)
                
                # Get stream info and display type + key values
                info = get_stream_info(stream)
                
                display_parts = []
                if info['tin'] is not None:
                    display_parts.append(f"Tin:{info['tin']}°C")
                if info['tout'] is not None:
                    display_parts.append(f"Tout:{info['tout']}°C")
                if info['CP'] is not None:
                    display_parts.append(f"CP:{info['CP']:.2f}")
                if info['Q'] is not None:
                    display_parts.append(f"Q:{info['Q']:.2f} kW")
                
                if info['type']:
                    type_color = "🔴" if info['type'] == "HOT" else "🔵"
                    display_parts.append(f"{type_color} {info['type']}")
                
                if display_parts:
                    stream_cols[2].caption(' | '.join(display_parts))
                else:
                    stream_cols[2].caption("(incomplete data)")
    
    # Count selected streams
    selected_count = sum(1 for k, v in st.session_state['selected_items'].items() 
                         if v and k.startswith("stream_"))
    
    # =====================================================
    # PINCH ANALYSIS SECTION
    # =====================================================
    st.markdown("---")
    
    if not PINCH_AVAILABLE:
        st.error(f"Pinch analysis module not available: {PINCH_IMPORT_ERROR or 'Unknown error'}")
        st.info("Please ensure the pinch_tool module is properly installed.")
    else:
        # Helper function to extract stream data from selection
        def extract_stream_data(procs, sel_items):
            """
            Extract stream data from selected items.
            Returns list of dicts with: CP, Tin, Tout, Q
            CP can be provided directly, or calculated as mdot * cp.
            Q = CP * (Tout - Tin)
            """
            result_streams = []
            
            for sel_key, is_sel in sel_items.items():
                if not is_sel:
                    continue
                    
                if sel_key.startswith("stream_"):
                    parts_split = sel_key.split("_")
                    p_idx = int(parts_split[1])
                    s_idx = int(parts_split[2])
                    
                    if p_idx < len(procs):
                        proc = procs[p_idx]
                        proc_streams = proc.get('streams', [])
                        
                        if s_idx < len(proc_streams):
                            strm = proc_streams[s_idx]
                            
                            # Use get_stream_info to extract all values consistently
                            info = get_stream_info(strm)
                            
                            tin = info['tin']
                            tout = info['tout']
                            CP = info['CP']
                            Q = info['Q']
                            
                            # Only add if we have the required data
                            if tin is not None and tout is not None and CP is not None:
                                strm_name = strm.get('name', f'Stream {s_idx + 1}')
                                proc_nm = proc.get('name', f'Subprocess {p_idx + 1}')
                                result_streams.append({
                                    'name': f"{proc_nm} - {strm_name}",
                                    'CP': CP,
                                    'Tin': tin,
                                    'Tout': tout,
                                    'Q': Q
                                })
            
            return result_streams
        
        # Helper function to run pinch analysis
        def run_pinch_analysis(strm_data, delta_tmin):
            """
            Run pinch analysis on the given stream data.
            Returns the Pinch object with results.
            """
            # Create a temporary CSV file with the stream data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Tmin', str(delta_tmin)])
                writer.writerow(['CP', 'TSUPPLY', 'TTARGET'])
                
                for strm in strm_data:
                    writer.writerow([strm['CP'], strm['Tin'], strm['Tout']])
                
                temp_csv_path = f.name
            
            try:
                # Run pinch analysis without drawing (we'll draw ourselves)
                pinch_obj = Pinch(temp_csv_path, options={})
                pinch_obj.shiftTemperatures()
                pinch_obj.constructTemperatureInterval()
                pinch_obj.constructProblemTable()
                pinch_obj.constructHeatCascade()
                pinch_obj.constructShiftedCompositeDiagram('EN')
                pinch_obj.constructCompositeDiagram('EN')
                pinch_obj.constructGrandCompositeCurve('EN')
                
                return pinch_obj
            finally:
                # Clean up temp file
                os.unlink(temp_csv_path)
        
        # Extract stream data from selections
        streams_data = extract_stream_data(processes, st.session_state['selected_items'])
        
        if len(streams_data) < 2:
            st.info("Select at least 2 streams with complete data (Tin, Tout, and either CP or ṁ+cp) to run pinch analysis.")
            
            # Show what data is missing for selected streams
            if selected_count > 0:
                st.markdown("**Data status for selected items:**")
                for sel_key, is_sel in st.session_state['selected_items'].items():
                    if not is_sel:
                        continue
                    if sel_key.startswith("stream_"):
                        parts_split = sel_key.split("_")
                        p_idx = int(parts_split[1])
                        s_idx = int(parts_split[2])
                        
                        if p_idx < len(processes):
                            proc = processes[p_idx]
                            proc_streams = proc.get('streams', [])
                            
                            if s_idx < len(proc_streams):
                                strm = proc_streams[s_idx]
                                strm_name = strm.get('name', f'Stream {s_idx + 1}')
                                proc_nm = proc.get('name', f'Subprocess {p_idx + 1}')
                                
                                # Check what data is available
                                props = strm.get('properties', {})
                                vals = strm.get('values', {})
                                
                                has_tin = False
                                has_tout = False
                                has_mdot = False
                                has_cp = False
                                has_CP = False  # CP = ṁ * cp (heat capacity rate)
                                
                                # Check stream_values (new structure)
                                stream_vals = strm.get('stream_values', {})
                                if not stream_vals:
                                    stream_vals = strm.get('product_values', {})
                                
                                if stream_vals:
                                    if stream_vals.get('Tin'):
                                        has_tin = True
                                    if stream_vals.get('Tout'):
                                        has_tout = True
                                    if stream_vals.get('ṁ'):
                                        has_mdot = True
                                    if stream_vals.get('cp'):
                                        has_cp = True
                                    if stream_vals.get('CP'):
                                        has_CP = True
                                
                                if isinstance(props, dict) and isinstance(vals, dict):
                                    for pk, pname in props.items():
                                        vk = pk.replace('prop', 'val')
                                        v = vals.get(vk, '')
                                        if pname == 'Tin' and v:
                                            has_tin = True
                                        elif pname == 'Tout' and v:
                                            has_tout = True
                                        elif pname == 'ṁ' and v:
                                            has_mdot = True
                                        elif pname == 'cp' and v:
                                            has_cp = True
                                        elif pname == 'CP' and v:
                                            has_CP = True
                                
                                # Fallback to legacy
                                if not has_tin and strm.get('temp_in'):
                                    has_tin = True
                                if not has_tout and strm.get('temp_out'):
                                    has_tout = True
                                if not has_mdot and strm.get('mdot'):
                                    has_mdot = True
                                if not has_cp and strm.get('cp'):
                                    has_cp = True
                                
                                missing = []
                                if not has_tin:
                                    missing.append("Tin")
                                if not has_tout:
                                    missing.append("Tout")
                                # Either CP is provided directly, or both ṁ and cp are needed
                                if not has_CP and not (has_mdot and has_cp):
                                    if not has_mdot:
                                        missing.append("ṁ")
                                    if not has_cp:
                                        missing.append("cp")
                                    if not missing or (not has_mdot and not has_cp):
                                        # If neither ṁ nor cp, suggest CP as alternative
                                        missing.append("(or CP)")
                                
                                if missing:
                                    st.warning(f"⚠️ {proc_nm} - {strm_name}: Missing {', '.join(missing)}")
                                else:
                                    st.success(f"✅ {proc_nm} - {strm_name}: Complete data")
        else:
            # Auto-run pinch analysis
            try:
                # Row: Shifted toggle | ΔTmin (small) | spacer | Hot Utility | Cold Utility | Pinch Temp
                toggle_col, tmin_col, spacer, metric1, metric2, metric3 = st.columns([0.6, 0.5, 0.4, 0.7, 0.7, 0.7])
                
                with toggle_col:
                    show_shifted = st.toggle("Show Shifted Composite Curves", value=False, key="shifted_toggle")
                
                with tmin_col:
                    tmin = st.number_input(
                        "ΔTmin",
                        min_value=1.0,
                        max_value=50.0,
                        value=10.0,
                        step=1.0,
                        key="tmin_input",
                        format="%.0f"
                    )
                
                pinch = run_pinch_analysis(streams_data, tmin)
                results = {
                    'hot_utility': pinch.hotUtility,
                    'cold_utility': pinch.coldUtility,
                    'pinch_temperature': pinch.pinchTemperature,
                    'tmin': pinch.tmin,
                    'composite_diagram': pinch.compositeDiagram,
                    'shifted_composite_diagram': pinch.shiftedCompositeDiagram,
                    'grand_composite_curve': pinch.grandCompositeCurve,
                    'heat_cascade': pinch.heatCascade,
                    'unfeasible_heat_cascade': pinch.unfeasibleHeatCascade,
                    'problem_table': pinch.problemTable,
                    'temperatures': pinch._temperatures,
                    'streams': list(pinch.streams)
                }
                
                metric1.metric("Hot Utility", f"{results['hot_utility']:.2f} kW")
                metric2.metric("Cold Utility", f"{results['cold_utility']:.2f} kW")
                metric3.metric("Pinch Temp", f"{results['pinch_temperature']:.1f} °C")
                
                # Side by side plots: Composite Curves (left) and Grand Composite Curve (right)
                plot_col1, plot_col2 = st.columns(2)
                
                # Build hover text for streams
                hot_streams = [s for s in streams_data if s['Tin'] > s['Tout']]
                cold_streams = [s for s in streams_data if s['Tin'] < s['Tout']]
                
                with plot_col1:
                    fig1 = go.Figure()
                    
                    # Select which diagram to show
                    if show_shifted:
                        diagram = results['shifted_composite_diagram']
                        curve_label = "Shifted"
                        title_text = "Shifted Composite Curves"
                        # For shifted, temperatures are shifted by ±Tmin/2
                        tmin_half = results['tmin'] / 2
                    else:
                        diagram = results['composite_diagram']
                        curve_label = ""
                        title_text = "Composite Curves"
                        tmin_half = 0
                    
                    # Hot composite curve with hover info
                    hot_T = diagram['hot']['T']
                    hot_H = diagram['hot']['H']
                    
                    # Create hover text for hot curve points
                    hot_hover = []
                    for i, (h, t) in enumerate(zip(hot_H, hot_T)):
                        # Find streams at this temperature (adjust for shifted temps)
                        if show_shifted:
                            actual_t = t + tmin_half  # Convert back to actual temp
                        else:
                            actual_t = t
                        matching = [s['name'] for s in hot_streams if min(s['Tin'], s['Tout']) <= actual_t <= max(s['Tin'], s['Tout'])]
                        stream_info = '<br>'.join(matching) if matching else 'Composite'
                        label = f"<b>Hot {curve_label}</b>" if curve_label else "<b>Hot Composite</b>"
                        hot_hover.append(f"{label}<br>T: {t:.1f}°C<br>H: {h:.1f} kW<br>Streams: {stream_info}")
                    
                    fig1.add_trace(go.Scatter(
                        x=hot_H, y=hot_T,
                        mode='lines+markers',
                        name='Hot',
                        line=dict(color='red', width=2),
                        marker=dict(size=6),
                        hovertemplate='%{text}<extra></extra>',
                        text=hot_hover
                    ))
                    
                    # Cold composite curve with hover info
                    cold_T = diagram['cold']['T']
                    cold_H = diagram['cold']['H']
                    
                    # Create hover text for cold curve points
                    cold_hover = []
                    for i, (h, t) in enumerate(zip(cold_H, cold_T)):
                        if show_shifted:
                            actual_t = t - tmin_half  # Convert back to actual temp
                        else:
                            actual_t = t
                        matching = [s['name'] for s in cold_streams if min(s['Tin'], s['Tout']) <= actual_t <= max(s['Tin'], s['Tout'])]
                        stream_info = '<br>'.join(matching) if matching else 'Composite'
                        label = f"<b>Cold {curve_label}</b>" if curve_label else "<b>Cold Composite</b>"
                        cold_hover.append(f"{label}<br>T: {t:.1f}°C<br>H: {h:.1f} kW<br>Streams: {stream_info}")
                    
                    fig1.add_trace(go.Scatter(
                        x=cold_H, y=cold_T,
                        mode='lines+markers',
                        name='Cold',
                        line=dict(color='blue', width=2),
                        marker=dict(size=6),
                        hovertemplate='%{text}<extra></extra>',
                        text=cold_hover
                    ))
                    
                    # Pinch temperature line
                    fig1.add_hline(
                        y=results['pinch_temperature'],
                        line_dash='dash',
                        line_color='gray',
                        annotation_text=f"Pinch: {results['pinch_temperature']:.1f}°C",
                        annotation_position='top right'
                    )
                    
                    fig1.update_layout(
                        title=dict(text=title_text, font=dict(size=14)),
                        xaxis_title='Enthalpy H (kW)',
                        yaxis_title='Temperature T (°C)',
                        height=400,
                        margin=dict(l=60, r=20, t=40, b=50),
                        legend=dict(x=0.7, y=0.1),
                        hovermode='closest',
                        xaxis=dict(rangemode='tozero'),
                        yaxis=dict(rangemode='tozero')
                    )
                    
                    st.plotly_chart(fig1, width='stretch', key="composite_chart")
                
                with plot_col2:
                    fig2 = go.Figure()
                    
                    gcc_H = results['grand_composite_curve']['H']
                    gcc_T = results['grand_composite_curve']['T']
                    heat_cascade = results['heat_cascade']
                    temperatures = results['temperatures']
                    
                    # Create hover text for GCC points
                    gcc_hover = []
                    for i, (h, t) in enumerate(zip(gcc_H, gcc_T)):
                        if i < len(heat_cascade):
                            dh = heat_cascade[i]['deltaH']
                            region = 'Heat deficit (needs heating)' if dh > 0 else ('Heat surplus (needs cooling)' if dh < 0 else 'Balanced')
                        else:
                            region = ''
                        gcc_hover.append(f"<b>GCC</b><br>Shifted T: {t:.1f}°C<br>Net ΔH: {h:.1f} kW<br>{region}")
                    
                    # Plot GCC with color segments
                    for i in range(len(gcc_H) - 1):
                        if i < len(heat_cascade):
                            if heat_cascade[i]['deltaH'] > 0:
                                color = 'red'
                            elif heat_cascade[i]['deltaH'] < 0:
                                color = 'blue'
                            else:
                                color = 'gray'
                        else:
                            color = 'gray'
                        
                        fig2.add_trace(go.Scatter(
                            x=[gcc_H[i], gcc_H[i+1]],
                            y=[gcc_T[i], gcc_T[i+1]],
                            mode='lines+markers',
                            line=dict(color=color, width=2),
                            marker=dict(size=6, color=color),
                            hovertemplate='%{text}<extra></extra>',
                            text=[gcc_hover[i], gcc_hover[i+1] if i+1 < len(gcc_hover) else ''],
                            showlegend=False
                        ))
                    
                    # Pinch temperature line
                    fig2.add_hline(
                        y=results['pinch_temperature'],
                        line_dash='dash',
                        line_color='gray',
                        annotation_text=f"Pinch: {results['pinch_temperature']:.1f}°C",
                        annotation_position='top right'
                    )
                    
                    # Zero enthalpy line
                    fig2.add_vline(x=0, line_color='black', line_width=1, opacity=0.3)
                    
                    fig2.update_layout(
                        title=dict(text='Grand Composite Curve', font=dict(size=14)),
                        xaxis_title='Net ΔH (kW)',
                        yaxis_title='Shifted Temperature (°C)',
                        height=400,
                        margin=dict(l=60, r=20, t=40, b=50),
                        hovermode='closest',
                        yaxis=dict(rangemode='tozero')
                    )
                    
                    st.plotly_chart(fig2, width='stretch', key="gcc_chart")
                
                # More information expander
                with st.expander("More information"):
                    import pandas as pd
                    
                    
                    temps = results['temperatures']
                    pinch_streams = results['streams']
                    
                    if pinch_streams and temps:
                        fig_interval = go.Figure()
                        
                        num_streams = len(pinch_streams)
                        x_positions = [(i + 1) * 1.0 for i in range(num_streams)]
                        
                        # Draw horizontal temperature lines
                        for temperature in temps:
                            fig_interval.add_shape(
                                type="line",
                                x0=0, x1=num_streams + 1,
                                y0=temperature, y1=temperature,
                                line=dict(color="gray", width=1, dash="dot"),
                            )
                        
                        # Draw pinch temperature line
                        fig_interval.add_shape(
                            type="line",
                            x0=0, x1=num_streams + 1,
                            y0=results['pinch_temperature'], y1=results['pinch_temperature'],
                            line=dict(color="black", width=2, dash="dash"),
                        )
                        fig_interval.add_annotation(
                            x=num_streams + 0.5, y=results['pinch_temperature'],
                            text=f"Pinch: {results['pinch_temperature']:.1f}°C",
                            showarrow=False, font=dict(size=10),
                            xanchor='left'
                        )
                        
                        # Draw stream arrows
                        for i, stream in enumerate(pinch_streams):
                            ss = stream['ss']  # Shifted supply temp
                            st_temp = stream['st']  # Shifted target temp
                            stream_type = stream['type']
                            x_pos = x_positions[i]
                            
                            # Color based on stream type
                            color = 'red' if stream_type == 'HOT' else 'blue'
                            stream_name = streams_data[i]['name'] if i < len(streams_data) else f'Stream {i+1}'
                            
                            # Draw arrow as a line with annotation for arrowhead
                            fig_interval.add_trace(go.Scatter(
                                x=[x_pos, x_pos],
                                y=[ss, st_temp],
                                mode='lines',
                                line=dict(color=color, width=8),
                                hovertemplate=f"<b>{stream_name}</b><br>" +
                                             f"Type: {stream_type}<br>" +
                                             f"T_supply (shifted): {ss:.1f}°C<br>" +
                                             f"T_target (shifted): {st_temp:.1f}°C<br>" +
                                             f"CP: {stream['cp']:.2f} kW/K<extra></extra>",
                                showlegend=False
                            ))
                            
                            # Add arrowhead
                            fig_interval.add_annotation(
                                x=x_pos, y=st_temp,
                                ax=x_pos, ay=ss,
                                xref='x', yref='y',
                                axref='x', ayref='y',
                                showarrow=True,
                                arrowhead=2,
                                arrowsize=1.5,
                                arrowwidth=3,
                                arrowcolor=color
                            )
                            
                            # Stream label at top
                            label_y = max(ss, st_temp) + (max(temps) - min(temps)) * 0.03
                            fig_interval.add_annotation(
                                x=x_pos, y=label_y,
                                text=f"<b>S{i+1}</b>",
                                showarrow=False,
                                font=dict(size=11, color='white'),
                                bgcolor=color,
                                bordercolor='black',
                                borderwidth=1,
                                borderpad=3
                            )
                            
                            # CP value in middle
                            mid_y = (ss + st_temp) / 2
                            fig_interval.add_annotation(
                                x=x_pos, y=mid_y,
                                text=f"CP={stream['cp']:.1f}",
                                showarrow=False,
                                font=dict(size=9, color='white'),
                                textangle=-90
                            )
                        
                        fig_interval.update_layout(
                            title=dict(text='Shifted Temperature Interval Diagram', font=dict(size=14)),
                            xaxis=dict(
                                title='Streams',
                                showticklabels=False,
                                range=[0, num_streams + 1],
                                showgrid=False
                            ),
                            yaxis=dict(
                                title='Shifted Temperature S (°C)',
                                showgrid=True,
                                gridcolor='rgba(0,0,0,0.1)'
                            ),
                            height=400,
                            margin=dict(l=60, r=20, t=40, b=40),
                            hovermode='closest',
                            showlegend=False
                        )
                        
                        st.plotly_chart(fig_interval, width='stretch', key="interval_chart")
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
