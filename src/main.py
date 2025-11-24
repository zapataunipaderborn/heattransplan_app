import streamlit as st

st.set_page_config(page_title="Home", page_icon="🏠")

st.title("Home page")

st.markdown(
    """
Welcome to the Heat Transmission Planning app.

Use the **Data Collection** page from the sidebar to work with maps and processes.
""",
    unsafe_allow_html=True,
)
