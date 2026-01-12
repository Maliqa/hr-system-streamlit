import streamlit as st
from pathlib import Path

def load_css(path: str):
    css_file = Path(path)
    if css_file.exists():
        st.markdown(
            f"<style>{css_file.read_text()}</style>",
            unsafe_allow_html=True
        )
