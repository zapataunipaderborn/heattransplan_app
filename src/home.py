import streamlit as st

# Configure the app - this must be the first Streamlit command
st.set_page_config(
    page_title="HeatTransPlan App",
    page_icon="",
    initial_sidebar_state="collapsed"
)

st.markdown(
    """
    <style>
    section[data-testid="stSidebar"][aria-expanded="true"] {
        width: 180px !important;
        min-width: 180px !important;
    }
    section[data-testid="stSidebar"][aria-expanded="false"] {
        width: 0 !important;
        min-width: 0 !important;
        margin-left: 0 !important;
    }
    """,
    unsafe_allow_html=True,
)
# Home page content
st.title("Home page")

st.markdown(
    """
Welcome to the app.

Use the **Data Collection** page from the sidebar to work with maps and processes.
""",
    unsafe_allow_html=True,
)
