"""
Process management UI components.
"""

import streamlit as st
from ui_components import create_process_header
from process_utils import add_process, add_stream_to_process, delete_stream_from_process


def render_process_groups():
    """Render the process groups interface."""
    # Add process group button
    col_add = st.columns([1])[0]
    if col_add.button("Add a process", key="btn_add_group_top"):
        # Ensure processes list exists
        if 'proc_groups' not in st.session_state:
            st.session_state['proc_groups'] = []
        st.session_state['proc_groups'].append([])  # new empty process
        
        # Sync process names & expansion
        if 'proc_group_names' not in st.session_state:
            st.session_state['proc_group_names'] = []
        st.session_state['proc_group_names'].append(f"Process {len(st.session_state['proc_groups'])}")
        
        if 'proc_group_expanded' not in st.session_state:
            st.session_state['proc_group_expanded'] = []
        st.session_state['proc_group_expanded'].append(True)
        
        st.session_state['ui_status_msg'] = "Added new empty process"
        st.rerun()


def render_process_editor():
    """Render the main process editor interface."""
    # Initialize process state
    if 'processes' not in st.session_state:
        st.session_state['processes'] = []
    
    processes = st.session_state['processes']
    
    # Show process groups
    if 'proc_groups' in st.session_state and st.session_state['proc_groups']:
        render_process_group_interface()
    else:
        # Legacy single process list
        render_single_process_list()


def render_process_group_interface():
    """Render the grouped process interface."""
    proc_groups = st.session_state.get('proc_groups', [])
    proc_group_names = st.session_state.get('proc_group_names', [])
    proc_group_expanded = st.session_state.get('proc_group_expanded', [])
    processes = st.session_state.get('processes', [])
    
    for g, g_list in enumerate(proc_groups):
        if g >= len(proc_group_names):
            continue
            
        # Group header
        group_name = proc_group_names[g]
        is_expanded = g < len(proc_group_expanded) and proc_group_expanded[g]
        
        # Group controls
        gh_cols = st.columns([0.06, 0.45, 0.25, 0.12, 0.12])
        
        # Toggle button
        toggle_label = "▾" if is_expanded else "▸"
        if gh_cols[0].button(toggle_label, key=f"group_toggle_{g}"):
            if len(proc_group_expanded) <= g:
                proc_group_expanded.extend([True] * (g + 1 - len(proc_group_expanded)))
            proc_group_expanded[g] = not is_expanded
            st.session_state['proc_group_expanded'] = proc_group_expanded
            st.rerun()
        
        # Group name
        new_name = gh_cols[1].text_input(
            f"Group {g+1} name",
            value=group_name,
            key=f"group_name_{g}",
            label_visibility="collapsed"
        )
        if new_name != group_name:
            proc_group_names[g] = new_name
            st.session_state['proc_group_names'] = proc_group_names
        
        # Add subprocess button
        if gh_cols[2].button("Add subprocess", key=f"add_proc_group_{g}"):
            add_process(st.session_state)
            new_idx = len(processes) - 1
            if new_idx >= 0:
                g_list.append(new_idx)
                st.session_state['proc_groups'][g] = g_list
            st.session_state['ui_status_msg'] = f"Added subprocess to {group_name}"
            st.rerun()
        
        # Process count
        gh_cols[3].write(f"({len(g_list)})")
        
        # Delete group button
        if gh_cols[4].button("✕", key=f"del_group_{g}"):
            delete_process_group(g)
            st.rerun()
        
        # Expanded group content
        if is_expanded and g_list:
            render_group_processes(g, g_list)


def render_group_processes(group_idx, process_indices):
    """Render processes within a group."""
    processes = st.session_state.get('processes', [])
    
    for local_idx, proc_idx in enumerate(process_indices):
        if proc_idx >= len(processes):
            continue
            
        process = processes[proc_idx]
        
        # Process header
        expanded, place_active = create_process_header(process, proc_idx)
        
        # Expanded process content
        if expanded:
            render_process_details(process, proc_idx)
        
        # Separator between processes
        if local_idx < len(process_indices) - 1:
            st.markdown("<div style='height:1px; background:#888888; opacity:0.5; margin:4px 0;'></div>", 
                       unsafe_allow_html=True)
    
    # Bottom separator after expanded group
    st.markdown("<div style='height:2px; background:#888888; opacity:0.7; margin:8px 0 4px;'></div>", 
               unsafe_allow_html=True)


def render_single_process_list():
    """Render processes in a single list (legacy mode)."""
    processes = st.session_state.get('processes', [])
    
    if not processes:
        st.info("No groups yet. Use 'Add a process' to start.")
        return
    
    for i, process in enumerate(processes):
        expanded, place_active = create_process_header(process, i)
        
        if expanded:
            render_process_details(process, i)
        
        if i < len(processes) - 1:
            st.markdown("<div style='height:1px; background:#888888; opacity:0.5; margin:4px 0;'></div>", 
                       unsafe_allow_html=True)


def render_process_details(process, proc_idx):
    """Render detailed process information and controls."""
    # Process properties
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    process['conntemp'] = r1c1.text_input("Product Tin", 
                                         value=process.get('conntemp', ''), 
                                         key=f"p_conntemp_{proc_idx}")
    process['product_tout'] = r1c2.text_input("Product Tout", 
                                             value=process.get('product_tout', ''), 
                                             key=f"p_ptout_{proc_idx}")
    process['connm'] = r1c3.text_input("Product ṁ", 
                                      value=process.get('connm', ''), 
                                      key=f"p_connm_{proc_idx}")
    process['conncp'] = r1c4.text_input("Product cp", 
                                       value=process.get('conncp', ''), 
                                       key=f"p_conncp_{proc_idx}")
    
    # Coordinates
    r2c1, r2c2, r2c3 = st.columns([1, 1, 3])
    process['lat'] = r2c1.text_input("Latitude", 
                                    value=str(process.get('lat', '')), 
                                    key=f"p_lat_{proc_idx}")
    process['lon'] = r2c2.text_input("Longitude", 
                                    value=str(process.get('lon', '')), 
                                    key=f"p_lon_{proc_idx}")
    
    # Next processes
    render_next_processes_selector(process, proc_idx, r2c3)
    
    # Streams section
    render_streams_section(process, proc_idx)


def render_next_processes_selector(process, proc_idx, column):
    """Render the next processes multi-select widget."""
    processes = st.session_state.get('processes', [])
    
    # Build option list of other subprocess names
    options = []
    for j, other_proc in enumerate(processes):
        if j != proc_idx:  # Exclude self
            nm = other_proc.get('name') or f"Subprocess {j+1}"
            options.append(nm)
    
    # Parse current selections
    current_next = process.get('next', '')
    if current_next:
        current_selections = [s.strip() for s in current_next.split(',') if s.strip()]
        selected = [opt for opt in current_selections if opt in options]
    else:
        selected = []
    
    # Multi-select widget
    selected = column.multiselect(
        "Next subprocess(es)",
        options=options,
        default=selected,
        key=f"p_next_{proc_idx}"
    )
    
    # Update process
    process['next'] = ", ".join(selected)


def render_streams_section(process, proc_idx):
    """Render the streams section for a process."""
    streams = process.get('streams', [])
    
    # Streams header
    header_c1, header_c2, header_c3 = st.columns([2, 4, 1])
    header_c1.markdown("**Streams**")
    
    if header_c3.button("➕", key=f"btn_add_stream_header_{proc_idx}"):
        add_stream_to_process(st.session_state, proc_idx)
        st.rerun()
    
    if not streams:
        st.caption("No streams yet. Use ➕ to add one.")
        return
    
    # Render each stream
    for si, stream in enumerate(streams):
        lbl_col, sc1, sc2, sc3, sc4, sc5 = st.columns([0.5, 1, 1, 1, 1, 0.6])
        
        lbl_col.markdown(f"**S{si+1}**")
        stream['temp_in'] = sc1.text_input("Tin", 
                                          value=str(stream.get('temp_in', '')), 
                                          key=f"s_tin_{proc_idx}_{si}")
        stream['temp_out'] = sc2.text_input("Tout", 
                                           value=str(stream.get('temp_out', '')), 
                                           key=f"s_tout_{proc_idx}_{si}")
        stream['mdot'] = sc3.text_input("ṁ", 
                                       value=str(stream.get('mdot', '')), 
                                       key=f"s_mdot_{proc_idx}_{si}")
        stream['cp'] = sc4.text_input("cp", 
                                     value=str(stream.get('cp', '')), 
                                     key=f"s_cp_{proc_idx}_{si}")
        
        if sc5.button("✕", key=f"del_stream_{proc_idx}_{si}"):
            delete_stream_from_process(st.session_state, proc_idx, si)
            st.rerun()


def delete_process_group(group_idx):
    """Delete a process group and reindex remaining groups."""
    if 'proc_groups' not in st.session_state:
        return
    
    proc_groups = st.session_state['proc_groups']
    if group_idx >= len(proc_groups):
        return
    
    # Remove the group
    del proc_groups[group_idx]
    
    # Remove corresponding name and expansion state
    if 'proc_group_names' in st.session_state and group_idx < len(st.session_state['proc_group_names']):
        del st.session_state['proc_group_names'][group_idx]
    
    if 'proc_group_expanded' in st.session_state and group_idx < len(st.session_state['proc_group_expanded']):
        del st.session_state['proc_group_expanded'][group_idx]
    
    # Reindex remaining groups
    for g in range(group_idx, len(proc_groups)):
        if 'proc_group_names' in st.session_state and g < len(st.session_state['proc_group_names']):
            current_name = st.session_state['proc_group_names'][g]
            if current_name.startswith("Process ") and current_name.split()[-1].isdigit():
                st.session_state['proc_group_names'][g] = f"Process {g + 1}"
    
    st.session_state['ui_status_msg'] = f"Deleted group {group_idx + 1}"
