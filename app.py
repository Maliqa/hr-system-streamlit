import streamlit as st
from core.db import init_db
from core.auth import login

st.set_page_config(page_title="HR System", layout="wide")

init_db()

if "user_id" not in st.session_state:
    st.title("🔐 Login HR System")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if login(email, password):
            st.success("Login success")
            st.rerun()
        else:
            st.error("Invalid credentials")
else:
    role = st.session_state["role"]

    if role == "employee":
        st.switch_page("pages/employee.py")
    elif role == "manager":
        st.switch_page("pages/manager.py")
    elif role == "hr":
        st.switch_page("pages/hr_admin.py")
