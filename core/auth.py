import hashlib
import sqlite3
import streamlit as st
from core.db import get_conn
from passlib.hash import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.verify(password, hashed)



def login(email, password):
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        SELECT id, role, password_hash
        FROM users
        WHERE email = ?
    """, (email,))

    row = c.fetchone()
    conn.close()

    if not row:
        return None

    user_id, role, password_hash = row

    if bcrypt.verify(password, password_hash):
        return user_id, role

    return None

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
