import streamlit as st

# Configure the app - this must be the first Streamlit command
st.set_page_config(
    page_title="Heat Transmission Planning",
    page_icon="🏠",
    initial_sidebar_state="expanded"
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
