# Page wrapper that loads the original Energy page
import streamlit as st
import importlib.util
import importlib.machinery
import os

# Ensure the module is executed only once to avoid multiple set_page_config calls
src_app_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'app.py')
# Each execution should re-run the `src/app.py` module so that it can react to
# the newly-chosen active page; `src/app.py` guards `set_page_config` so this
# is safe.
st.session_state['active_page'] = 'Energy'
spec = importlib.util.spec_from_file_location(f"src_app_{os.getpid()}_{int(os.times()[4]*1000)}", src_app_path)
module = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(module)
except Exception as exc:
    st.error(f"Failed to load original app: {exc}")
