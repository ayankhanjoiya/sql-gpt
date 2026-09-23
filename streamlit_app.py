# Main entry point for Streamlit Cloud & local deployments

import streamlit as st

# Set page configuration
st.set_page_config(
    page_title="SQLGPT — Natural Language SQL Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import and execute main entry point
from app import main

if __name__ == "__main__":
    main()
