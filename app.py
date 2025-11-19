import streamlit as st

# The root `app.py` was used during development to route between pages. During
# refactor the user preferred only two pages (`pages/1_data_collection.py` and
# `pages/2_potential_analysis.py`). To avoid `app.py` showing in the multipage
# sidebar as a separate page, this script now simply explains that it's been
# disabled and forwards users to the two pages.

st.set_page_config(page_title="Heattransplan — Use pages", layout="wide")

st.markdown("""
## App entry disabled

The project now uses two pages — **Data Collection** and **Potential Analysis**.
- Open the left sidebar in Streamlit and select either page.
- Or run the Data Collection page directly: `streamlit run pages/1_data_collection.py`

If you need the old single-file `app.py` restored, the original content is
backed up in `app_removed_by_copilot.py`.
""")

st.stop()
