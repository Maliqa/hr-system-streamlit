import streamlit as st
from utils.api import api_get, api_post
from core.leave_engine import run_leave_engine

# Jalankan engine (idempotent)
run_leave_engine()

st.set_page_config(page_title="HR System", layout="wide")

# Hide sidebar
st.markdown("""
<style>
section[data-testid="stSidebar"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ==========================
# AUTO CHECK LOGIN (JWT)
# ==========================
me = api_get("/me", timeout=5)

if me.status_code == 200 and me.json():
    role = me.json().get("role")

    if role == "employee":
        st.switch_page("pages/employee.py")
    elif role == "manager":
        st.switch_page("pages/manager.py")
    elif role == "hr":
        st.switch_page("pages/hr_admin.py")

# ==========================
# LOGIN PAGE
# ==========================
st.title("🔐 Login HR System")

email = st.text_input("Email")
password = st.text_input("Password", type="password")

if st.button("Login"):
    r = api_post(
        "/login",
        params={"email": email, "password": password},
        timeout=5
    )

    if r.status_code == 200 and r.json().get("status") == "ok":
        st.success("Login berhasil")
        st.rerun()
    else:
        st.error("Email / Password salah")
