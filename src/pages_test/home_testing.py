import streamlit as st
import streamlit.components.v1 as components
import base64

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

# Display the logo
st.image("../data/symbol.svg", width=200)
# Home page content
st.title("Home page")


st.subheader("Information")

# Display a clickable image from the HeatTransPlan website
with open("../data/image_project.jpeg", "rb") as f:
    image_data = f.read()
encoded_image = base64.b64encode(image_data).decode()
st.markdown(f'<a href="https://www.heattransplan.de/" target="_blank"><img src="data:image/jpeg;base64,{encoded_image}" width="400" style="transition: transform 0.3s ease; border: none;" onmouseover="this.style.transform=\'scale(1.1)\'" onmouseout="this.style.transform=\'scale(1)\'"></a>', unsafe_allow_html=True)
st.markdown("About HeatTransPlan")

st.subheader("Navigate to Pages")
st.page_link("pages/data_collection.py", label="📊 Energy Data Collection", help="Collect and manage energy data")
