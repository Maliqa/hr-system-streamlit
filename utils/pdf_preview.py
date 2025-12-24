import streamlit as st
import base64
import os

def preview_pdf(file_path):
    if not os.path.exists(file_path):
        st.error("File not found")
        return

    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode("utf-8")

    pdf_display = f"""
    <iframe 
        src="data:application/pdf;base64,{base64_pdf}"
        width="100%"
        height="600"
        style="border: none;"
    ></iframe>
    """

    st.markdown(pdf_display, unsafe_allow_html=True)

