import streamlit as st

def top_right_logo(path="assets/cistech.png", width=180):
    col1, col2 = st.columns([7, 3])
    with col2:
        st.image(path, width=width)
