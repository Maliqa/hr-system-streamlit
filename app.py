import streamlit as st
from utils.api import api_get, api_post
from core.leave_engine import run_leave_engine
from core.db import init_db
from core.seed import seed_hr_if_empty

# ==========================
# PAGE CONFIG (WAJIB DI ATAS)
# ==========================
st.set_page_config(
    page_title="HR System",
    layout="wide"
)

# ==========================
# GLOBAL STYLE
# ==========================
st.markdown("""
<style>
section[data-testid="stSidebar"] { display: none; }
.login-title {
    font-size: 32px;
    font-weight: 700;
}
.login-subtitle {
    color: #6c757d;
    margin-top: -10px;
}
</style>
""", unsafe_allow_html=True)

# ==========================
# INIT SYSTEM (URUTAN AMAN)
# ==========================
init_db()
seed_hr_if_empty()
run_leave_engine()

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
# HEADER (LOGO KANAN)
# ==========================
left, right = st.columns([6, 2])

with left:
    st.markdown("<div class='login-title'>HR Management System</div>", unsafe_allow_html=True)
    st.markdown("<div class='login-subtitle'>Internal Company Portal</div>", unsafe_allow_html=True)

with right:
    st.image("assets/cistech.png", width=320)

st.divider()

# ==========================
# LOGIN FORM
# ==========================
st.subheader("🔐 Login")

email = st.text_input("Email")
password = st.text_input("Password", type="password")

if st.button("Login", use_container_width=True):
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
