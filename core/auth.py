import bcrypt
import streamlit as st
from core.db import get_conn

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def login(email, password):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, role, password_hash FROM users WHERE email=?", (email,))
    user = c.fetchone()

    if user and verify_password(password, user[2]):
        st.session_state["user_id"] = user[0]
        st.session_state["role"] = user[1]
        return True
    return False

def require_role(role):
    if st.session_state.get("role") != role:
        st.error("Access denied")
        st.stop()
