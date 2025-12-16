import hashlib
import streamlit as st
from core.db import get_conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == hashed

def login(email, password):
    conn = get_conn()
    c = conn.cursor()

    c.execute(
        "SELECT id, role, password_hash FROM users WHERE email=?",
        (email,)
    )
    user = c.fetchone()

    if user and verify_password(password, user[2]):
        st.session_state["user_id"] = user[0]
        st.session_state["role"] = user[1]
        return True

    return False

def require_role(role):
    current_role = st.session_state.get("role")

    if current_role != role:
        if current_role == "employee":
            st.switch_page("pages/employee.py")
        elif current_role == "manager":
            st.switch_page("pages/manager.py")
        elif current_role == "hr":
            st.switch_page("pages/hr_admin.py")
        else:
            st.switch_page("app.py")

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
