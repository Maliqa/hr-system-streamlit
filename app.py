import streamlit as st
from core.db import init_db, get_conn
from core.auth import login, hash_password

st.set_page_config(page_title="HR System", layout="wide")

st.markdown("""
<style>
section[data-testid="stSidebar"] {display: none;}
</style>
""", unsafe_allow_html=True)

# INIT DB
init_db()

# SEED HR ADMIN (AMAN, TANPA CIRCULAR)
conn = get_conn()
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM users WHERE role='hr'")
if c.fetchone()[0] == 0:
    c.execute("""
    INSERT INTO users (nik, name, email, role, join_date, password_hash)
    VALUES (?, ?, ?, ?, DATE('now'), ?)
    """, (
        "HR001",
        "HR Admin",
        "hr@company.com",
        "hr",
        hash_password("admin123")
    ))
    conn.commit()
conn.close()

# LOGIN
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
