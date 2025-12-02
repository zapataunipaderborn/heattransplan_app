import streamlit as st
import sys
import os
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
        """Extract Tin, Tout, mdot, cp from stream and determine if HOT or COLD"""
        properties = stream.get('properties', {})
        values = stream.get('values', {})
        
        tin = None
        tout = None
        mdot = None
        cp_val = None
        
        # Check properties dict structure
        if isinstance(properties, dict) and isinstance(values, dict):
            for pk, pname in properties.items():
                vk = pk.replace('prop', 'val')
                v = values.get(vk, '')
                
                if pname == 'Tin' and v:
                    try:
                        tin = float(v)
                    except (ValueError, TypeError):
                        pass
                elif pname == 'Tout' and v:
                    try:
                        tout = float(v)
                    except (ValueError, TypeError):
                        pass
                elif pname == 'ṁ' and v:
                    try:
                        mdot = float(v)
                    except (ValueError, TypeError):
                        pass
                elif pname == 'cp' and v:
                    try:
                        cp_val = float(v)
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
        
        # Calculate CP if possible
        cp_flow = None
        if mdot is not None and cp_val is not None:
            cp_flow = mdot * cp_val
        
        return {
            'tin': tin,
            'tout': tout,
            'mdot': mdot,
            'cp': cp_val,
            'CP': cp_flow,
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
                    display_parts.append(f"CP:{info['CP']:.2f} kW/K")
                
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
            Returns list of dicts with: CP (calculated as mdot * cp), Tin, Tout
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
                            
                            # Extract values from properties/values structure
                            props = strm.get('properties', {})
                            vals = strm.get('values', {})
                            
                            tin = None
                            tout = None
                            mdot = None
                            cp_val = None
                            
                            # Check properties dict structure
                            if isinstance(props, dict) and isinstance(vals, dict):
                                for pk, pname in props.items():
                                    vk = pk.replace('prop', 'val')
                                    v = vals.get(vk, '')
                                    
                                    if pname == 'Tin' and v:
                                        try:
                                            tin = float(v)
                                        except (ValueError, TypeError):
                                            pass
                                    elif pname == 'Tout' and v:
                                        try:
                                            tout = float(v)
                                        except (ValueError, TypeError):
                                            pass
                                    elif pname == 'ṁ' and v:
                                        try:
                                            mdot = float(v)
                                        except (ValueError, TypeError):
                                            pass
                                    elif pname == 'cp' and v:
                                        try:
                                            cp_val = float(v)
                                        except (ValueError, TypeError):
                                            pass
                            
                            # Fallback to legacy fields
                            if tin is None and strm.get('temp_in'):
                                try:
                                    tin = float(strm['temp_in'])
                                except (ValueError, TypeError):
                                    pass
                            if tout is None and strm.get('temp_out'):
                                try:
                                    tout = float(strm['temp_out'])
                                except (ValueError, TypeError):
                                    pass
                            if mdot is None and strm.get('mdot'):
                                try:
                                    mdot = float(strm['mdot'])
                                except (ValueError, TypeError):
                                    pass
                            if cp_val is None and strm.get('cp'):
                                try:
                                    cp_val = float(strm['cp'])
                                except (ValueError, TypeError):
                                    pass
                            
                            # Calculate CP = mdot * cp
                            if tin is not None and tout is not None and mdot is not None and cp_val is not None:
                                CP = mdot * cp_val
                                strm_name = strm.get('name', f'Stream {s_idx + 1}')
                                proc_nm = proc.get('name', f'Subprocess {p_idx + 1}')
                                result_streams.append({
                                    'name': f"{proc_nm} - {strm_name}",
                                    'CP': CP,
                                    'Tin': tin,
                                    'Tout': tout
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
            st.info("Select at least 2 streams with complete data (Tin, Tout, ṁ, cp) to run pinch analysis.")
            
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
                                if not has_mdot:
                                    missing.append("ṁ")
                                if not has_cp:
                                    missing.append("cp")
                                
                                if missing:
                                    st.warning(f"⚠️ {proc_nm} - {strm_name}: Missing {', '.join(missing)}")
                                else:
                                    st.success(f"✅ {proc_nm} - {strm_name}: Complete data")
        else:
            # Tmin input - compact
            tmin_col1, tmin_col2 = st.columns([0.3, 0.7])
            tmin = tmin_col1.number_input(
                "ΔTmin (°C)",
                min_value=1.0,
                max_value=50.0,
                value=10.0,
                step=1.0
            )
            
            # Auto-run pinch analysis
            try:
                pinch = run_pinch_analysis(streams_data, tmin)
                results = {
                    'hot_utility': pinch.hotUtility,
                    'cold_utility': pinch.coldUtility,
                    'pinch_temperature': pinch.pinchTemperature,
                    'tmin': pinch.tmin,
                    'composite_diagram': pinch.compositeDiagram,
                    'grand_composite_curve': pinch.grandCompositeCurve,
                    'heat_cascade': pinch.heatCascade,
                    'temperatures': pinch._temperatures
                }
                
                # Key results - compact
                col1, col2, col3 = st.columns(3)
                col1.metric("Hot Utility", f"{results['hot_utility']:.2f} kW")
                col2.metric("Cold Utility", f"{results['cold_utility']:.2f} kW")
                col3.metric("Pinch Temp", f"{results['pinch_temperature']:.1f} °C")
                fig1, ax1 = plt.subplots(figsize=(10, 6))
                
                # Plot hot composite curve
                hot_T = results['composite_diagram']['hot']['T']
                hot_H = results['composite_diagram']['hot']['H']
                ax1.plot(hot_H, hot_T, 'r-', linewidth=2.5, label='Hot Composite Curve', marker='o', markersize=6)
                
                # Plot cold composite curve
                cold_T = results['composite_diagram']['cold']['T']
                cold_H = results['composite_diagram']['cold']['H']
                ax1.plot(cold_H, cold_T, 'b-', linewidth=2.5, label='Cold Composite Curve', marker='o', markersize=6)
                
                # Pinch point line
                ax1.axhline(y=results['pinch_temperature'], color='gray', linestyle='--', alpha=0.7, 
                           label=f'Pinch ({results["pinch_temperature"]:.1f}°C)')
                
                ax1.set_xlabel('Enthalpy H (kW)', fontsize=12)
                ax1.set_ylabel('Temperature T (°C)', fontsize=12)
                ax1.set_title('Composite Curves', fontsize=14, fontweight='bold')
                ax1.legend(fontsize=10)
                ax1.grid(True, alpha=0.3)
                
                # Add annotations for utilities
                ax1.annotate(f'Hot Utility\n{results["hot_utility"]:.1f} kW', 
                            xy=(0.02, 0.98), xycoords='axes fraction',
                            fontsize=9, verticalalignment='top',
                            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
                ax1.annotate(f'Cold Utility\n{results["cold_utility"]:.1f} kW',
                            xy=(0.98, 0.02), xycoords='axes fraction',
                            fontsize=9, verticalalignment='bottom', horizontalalignment='right',
                            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
                
                plt.tight_layout()
                st.pyplot(fig1)
                plt.close(fig1)
                
                # Grand Composite Curve Plot
                st.markdown("#### Grand Composite Curve")
                fig2, ax2 = plt.subplots(figsize=(10, 6))
                
                gcc_H = results['grand_composite_curve']['H']
                gcc_T = results['grand_composite_curve']['T']
                heat_cascade = results['heat_cascade']
                temperatures = results['temperatures']
                
                # Plot GCC with color coding based on heat cascade
                for i in range(len(temperatures) - 1):
                    if i < len(heat_cascade):
                        if heat_cascade[i]['deltaH'] > 0:
                            color = 'red'
                        elif heat_cascade[i]['deltaH'] < 0:
                            color = 'blue'
                        else:
                            color = 'gray'
                    else:
                        color = 'gray'
                    
                    if i + 1 < len(gcc_H):
                        ax2.plot([gcc_H[i], gcc_H[i+1]], [gcc_T[i], gcc_T[i+1]], 
                                color=color, linewidth=2.5, marker='o', markersize=6)
                
                # Pinch point line
                ax2.axhline(y=results['pinch_temperature'], color='gray', linestyle='--', alpha=0.7,
                           label=f'Pinch ({results["pinch_temperature"]:.1f}°C)')
                ax2.axvline(x=0, color='black', linestyle='-', alpha=0.3)
                
                ax2.set_xlabel('Net Enthalpy Change ΔH (kW)', fontsize=12)
                ax2.set_ylabel('Shifted Temperature T (°C)', fontsize=12)
                ax2.set_title('Grand Composite Curve', fontsize=14, fontweight='bold')
                ax2.legend(fontsize=10)
                ax2.grid(True, alpha=0.3)
                
                # Add annotations
                ax2.annotate(f'Hot Utility: {results["hot_utility"]:.1f} kW',
                            xy=(0.02, 0.98), xycoords='axes fraction',
                            fontsize=9, verticalalignment='top',
                            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
                
                plt.tight_layout()
                st.pyplot(fig2)
                plt.close(fig2)
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
