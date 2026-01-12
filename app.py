import streamlit as st
from utils.api import api_get, api_post
from core.leave_engine import run_leave_engine
from core.db import init_db
from core.seed import seed_hr_if_empty
from utils.ui import load_css

# ==========================
# PAGE CONFIG (WAJIB DI ATAS)
# ==========================
st.set_page_config(
    page_title="HR Management System",
    layout="wide"
)

# ==========================
# GLOBAL STYLE
# ==========================
load_css("assets/styles/global.css")

st.markdown("""
<style>
section[data-testid="stSidebar"] { display: none; }

/* LOGIN HEADER */
.login-title {
    font-size: 32px;
    font-weight: 700;
}
.login-subtitle {
    color: #6c757d;
    margin-top: -8px;
}

/* LOGIN CARD */
.login-card {
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 32px;
    background: #ffffff;
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
# HEADER (LOGO KANAN SEJAJAR)
# ==========================
col1, col2 = st.columns([7, 3], vertical_alignment="center")

with col1:
    st.markdown("<div class='login-title'>HR Management System</div>", unsafe_allow_html=True)
    st.markdown("<div class='login-subtitle'>Internal Company Portal</div>", unsafe_allow_html=True)

with col2:
    st.image("assets/cistech.png", width=260)

st.divider()

# ==========================
# CENTER LOGIN FORM (ENTERPRISE)
# ==========================
left, center, right = st.columns([3, 4, 3])

with center:

    st.markdown("### 🔐 Login")

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="you@ptcai.com")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", width="stretch")

    if submit:
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

    st.markdown("</div>", unsafe_allow_html=True)
