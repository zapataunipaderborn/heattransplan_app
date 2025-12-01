import pandas as pd
import io
import copy
from typing import List, Dict, Tuple, Optional, Any, Generator

def init_process_state(session_state):
    if 'processes' not in session_state:
        session_state['processes'] = []  # list of proc dicts
    if 'selected_process_idx' not in session_state:
        session_state['selected_process_idx'] = None

REQUIRED_PROC_COLS = {"name","next","conntemp","product_tout","connm","conncp","stream_no","mdot","temp_in","temp_out","cp"}

# Level names for different hierarchy depths
LEVEL_NAMES = {
    0: 'Process',
    1: 'Subprocess', 
    2: 'Sub-subprocess',
    3: 'Sub-sub-subprocess',
    4: 'Sub-sub-sub-subprocess'
}

def get_level_name(level: int) -> str:
    """Get the display name for a hierarchy level."""
    return LEVEL_NAMES.get(level, f'Level-{level} Process')


def create_stream(name: str = '', stream_type: str = 'product') -> Dict[str, Any]:
    """
    Create a new stream with consistent structure.
    This is the reusable function for creating streams at any level.
    
    Args:
        name: Name of the stream
        stream_type: Type of stream (product, steam, air, water)
    
    Returns:
        A dict representing the stream with all standard fields
    """
    return {
        'name': name,
        'type': stream_type,
        'properties': {
            'prop1': 'Tin',
            'prop2': 'Tout',
            'prop3': 'ṁ',
            'prop4': 'cp'
        },
        'values': {
            'val1': '',
            'val2': '',
            'val3': '',
            'val4': ''
        },
        # Legacy fields for backward compatibility
        'mdot': '',
        'temp_in': '',
        'temp_out': '',
        'cp': ''
    }


def create_process_node(name: str = '', level: int = 0) -> Dict[str, Any]:
    """
    Create a new process/subprocess/sub-subprocess node with a consistent structure.
    This is a REUSABLE function that creates nodes at ANY hierarchy level.
    
    The same structure is used for:
    - Processes (level 0)
    - Subprocesses (level 1)
    - Sub-subprocesses (level 2)
    - And so on...
    
    Args:
        name: Name of the process node
        level: Hierarchy level (0=process, 1=subprocess, 2=sub-subprocess, etc.)
    
    Returns:
        A dict representing the process node with all standard fields
    """
    return {
        'name': name or f'{get_level_name(level)} 1',
        'level': level,
        'next': '',
        'conntemp': '',      # Product Tin
        'product_tout': '',  # Product Tout
        'connm': '',         # Product ṁ
        'conncp': '',        # Product cp
        'streams': [],
        'children': [],      # Sub-nodes (subprocesses, sub-subprocesses, etc.) - RECURSIVE!
        'lat': None,
        'lon': None,
        'box_scale': 1.0 if level > 0 else 1.5,
        'extra_info': {
            'air_tin': '',
            'air_tout': '',
            'air_mdot': '',
            'air_cp': '',
            'water_content_in': '',
            'water_content_out': '',
            'density': '',
            'pressure': '',
            'notes': ''
        },
        'expanded': False,       # UI state: whether this node is expanded
        'info_expanded': False,  # UI state: whether info section is expanded
        'model': {'level1': None, 'level2': None},  # Process model selection
        'params': {  # Process parameters
            'tin': '', 'tout': '', 'time': '', 'cp': '',
            'mass_flow': None, 'thermal_power': None
        },
        'params_requested': False,
        'hours': ''  # Operating hours
    }


def add_child_to_node(parent_node: Dict[str, Any], child_name: str = '') -> Dict[str, Any]:
    """
    Add a child node (subprocess/sub-subprocess/etc.) to a parent node.
    This works recursively at ANY level - the same function is used to:
    - Add subprocess to process
    - Add sub-subprocess to subprocess
    - Add sub-sub-subprocess to sub-subprocess
    - etc.
    
    Args:
        parent_node: The parent process node to add a child to
        child_name: Optional name for the child
    
    Returns:
        The newly created child node
    """
    if 'children' not in parent_node:
        parent_node['children'] = []
    
    parent_level = parent_node.get('level', 0)
    child_level = parent_level + 1
    child_index = len(parent_node['children'])
    
    default_name = f"{get_level_name(child_level)} {child_index + 1}"
    
    child_node = create_process_node(
        name=child_name or default_name,
        level=child_level
    )
    
    parent_node['children'].append(child_node)
    return child_node


def delete_child_from_node(parent_node: Dict[str, Any], child_index: int) -> bool:
    """
    Delete a child node from a parent node by index.
    Works at any hierarchy level.
    
    Args:
        parent_node: The parent process node
        child_index: Index of the child to delete
    
    Returns:
        True if successful, False otherwise
    """
    if 'children' not in parent_node:
        return False
    
    children = parent_node['children']
    if 0 <= child_index < len(children):
        children.pop(child_index)
        return True
    return False


def add_stream_to_node(node: Dict[str, Any], stream_name: str = '') -> Dict[str, Any]:
    """
    Add a stream to ANY process node (process, subprocess, sub-subprocess, etc.).
    This is the REUSABLE function for adding streams at any level.
    
    Args:
        node: The process node to add a stream to
        stream_name: Optional name for the stream
    
    Returns:
        The newly created stream
    """
    if 'streams' not in node:
        node['streams'] = []
    
    stream_count = len(node['streams'])
    stream = create_stream(
        name=stream_name or f'Stream {stream_count + 1}',
        stream_type='product'
    )
    node['streams'].append(stream)
    return stream


def delete_stream_from_node(node: Dict[str, Any], stream_index: int) -> bool:
    """
    Delete a stream from ANY process node.
    This is the REUSABLE function for deleting streams at any level.
    
    Args:
        node: The process node
        stream_index: Index of the stream to delete
    
    Returns:
        True if successful, False otherwise
    """
    if 'streams' not in node:
        return False
    
    streams = node['streams']
    if 0 <= stream_index < len(streams):
        streams.pop(stream_index)
        return True
    return False


def iterate_all_nodes(nodes: List[Dict[str, Any]]) -> Generator[Tuple[Dict[str, Any], int, List[int]], None, None]:
    """
    Generator that yields all nodes in a tree structure (depth-first).
    Useful for operations that need to traverse the entire hierarchy.
    
    Args:
        nodes: List of root nodes
    
    Yields:
        Tuples of (node, level, path_indices)
        - node: The process node
        - level: Hierarchy level (0=process, 1=subprocess, etc.)
        - path_indices: List of indices from root to this node, e.g., [0, 2, 1]
    """
    def _iterate(node_list: List[Dict], level: int, path: List[int]):
        for i, node in enumerate(node_list):
            current_path = path + [i]
            yield node, level, current_path
            # Recurse into children
            children = node.get('children', [])
            if children:
                yield from _iterate(children, level + 1, current_path)
    
    yield from _iterate(nodes, 0, [])


def get_node_by_path(root_nodes: List[Dict[str, Any]], path: List[int]) -> Optional[Dict[str, Any]]:
    """
    Get a node by its path indices (e.g., [0, 1, 2] means process 0, child 1, grandchild 2).
    
    Args:
        root_nodes: List of root process nodes
        path: List of indices forming the path to the node
    
    Returns:
        The node if found, None otherwise
    """
    if not path or path[0] >= len(root_nodes):
        return None
    
    current = root_nodes[path[0]]
    
    for idx in path[1:]:
        children = current.get('children', [])
        if idx >= len(children):
            return None
        current = children[idx]
    
    return current


def copy_streams_to_all_descendants(parent_node: Dict[str, Any]):
    """
    Copy streams from a parent node to ALL its descendants (children, grandchildren, etc.).
    This implements the requirement that changing streams should propagate to all descendants.
    
    Args:
        parent_node: The parent node whose streams to copy to all descendants
    """
    parent_streams = parent_node.get('streams', [])
    
    def _copy_recursive(node: Dict[str, Any]):
        children = node.get('children', [])
        for child in children:
            # Deep copy the streams to child
            child['streams'] = copy.deepcopy(parent_streams)
            # Recurse to grandchildren
            _copy_recursive(child)
    
    _copy_recursive(parent_node)


def sync_node_with_parent(child_node: Dict[str, Any], parent_node: Dict[str, Any], 
                          sync_streams: bool = True, sync_info: bool = False):
    """
    Sync data from parent to a specific child node.
    
    Args:
        child_node: The child node to update
        parent_node: The parent node to copy from
        sync_streams: Whether to sync streams
        sync_info: Whether to sync extra_info fields
    """
    if sync_streams:
        child_node['streams'] = copy.deepcopy(parent_node.get('streams', []))
    
    if sync_info:
        child_node['extra_info'] = copy.deepcopy(parent_node.get('extra_info', {}))


def count_all_descendants(node: Dict[str, Any]) -> int:
    """
    Count all descendants (children, grandchildren, etc.) of a node.
    
    Args:
        node: The node to count descendants for
    
    Returns:
        Total number of descendants
    """
    count = 0
    children = node.get('children', [])
    count += len(children)
    for child in children:
        count += count_all_descendants(child)
    return count


# =============================================================================
# LEGACY FUNCTIONS - Keep for backward compatibility with existing code
# =============================================================================

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
            # Include product_tout in key for uniqueness if present
            key = (row['name'], row['next'], row['conntemp'], row.get('product_tout',''), row['connm'], row['conncp'])
            if key not in proc_lookup:
                p = {
                    "name": row.get('name',''),
                    "next": row.get('next',''),
                    "conntemp": row.get('conntemp',''),  # Product Tin
                    "product_tout": row.get('product_tout',''),  # P Tout
                    "connm": row.get('connm',''),  # P ṁ
                    "conncp": row.get('conncp',''),  # P cp
                    "streams": [],
                    "children": [],  # Support for sub-levels
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
    """Export processes to CSV, including nested children."""
    rows = []
    
    def _add_process_rows(p: Dict, parent_name: str = ''):
        """Recursively add rows for a process and its children."""
        proc_name = p.get('name', '')
        full_name = f"{parent_name} > {proc_name}" if parent_name else proc_name
        
        if not p.get('streams'):
            rows.append({
                'name': full_name, 'next': p.get('next',''), 'conntemp': p.get('conntemp',''), 
                'product_tout': p.get('product_tout',''),
                'connm': p.get('connm',''), 'conncp': p.get('conncp',''), 'stream_no': '', 
                'mdot':'','temp_in':'','temp_out':'','cp':'',
                'lat': p.get('lat'), 'lon': p.get('lon'),
                'level': p.get('level', 0)
            })
        else:
            for idx, s in enumerate(p['streams'], start=1):
                rows.append({
                    'name': full_name, 'next': p.get('next',''), 'conntemp': p.get('conntemp',''), 
                    'product_tout': p.get('product_tout',''),
                    'connm': p.get('connm',''), 'conncp': p.get('conncp',''), 'stream_no': idx,
                    'mdot': s.get('mdot',''), 'temp_in': s.get('temp_in',''), 
                    'temp_out': s.get('temp_out',''), 'cp': s.get('cp',''),
                    'lat': p.get('lat'), 'lon': p.get('lon'),
                    'level': p.get('level', 0)
                })
        
        # Recurse into children
        for child in p.get('children', []):
            _add_process_rows(child, full_name)
    
    for p in processes:
        _add_process_rows(p)
    
    df = pd.DataFrame(rows)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode('utf-8')

def add_process(session_state):
    """Legacy function - adds a subprocess to the flat processes list."""
    new_proc = create_process_node(level=1)  # Level 1 for subprocess
    new_proc['name'] = ''  # Let UI set the name
    session_state['processes'].append(new_proc)
    session_state['selected_process_idx'] = len(session_state['processes'])-1

def delete_process(session_state, idx):
    """Legacy function - deletes a subprocess from the flat processes list."""
    if 0 <= idx < len(session_state['processes']):
        session_state['processes'].pop(idx)
        if session_state['selected_process_idx'] == idx:
            session_state['selected_process_idx'] = None

def add_stream_to_process(session_state, pidx):
    """Legacy function - adds a stream to a subprocess in the flat list."""
    if 0 <= pidx < len(session_state['processes']):
        add_stream_to_node(session_state['processes'][pidx])

def delete_stream_from_process(session_state, pidx, sidx):
    """Legacy function - deletes a stream from a subprocess in the flat list."""
    if 0 <= pidx < len(session_state['processes']):
        delete_stream_from_node(session_state['processes'][pidx], sidx)
