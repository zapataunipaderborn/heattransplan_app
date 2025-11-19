# Page wrapper that loads the original Potential page
import streamlit as st
import importlib.util
import importlib.machinery
import os

src_app_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'app.py')
st.session_state['active_page'] = 'Potential'
spec = importlib.util.spec_from_file_location(f"src_app_{os.getpid()}_{int(os.times()[4]*1000)}", src_app_path)
module = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(module)
except Exception as exc:
    st.error(f"Failed to load original app: {exc}")
