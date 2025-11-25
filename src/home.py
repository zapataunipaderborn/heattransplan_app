import streamlit as st

# Configure the app - this must be the first Streamlit command
st.set_page_config(
    page_title="HeatTransPlan App",
    page_icon="",
    initial_sidebar_state="expanded"
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
    .stMarkdown p, .stMarkdown span, .stMarkdown li {font-size:11px !important;}
    .stButton button {font-size:10px !important; padding:0.1rem 0.3rem !important;}
    .stTextInput input, .stNumberInput input {font-size:10px !important; padding:0.1rem 0.2rem !important;}
    h1 {font-size: 1.5rem !important; margin-bottom: 0.3rem !important;}
    </style>
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
