import streamlit as st
import pandas as pd
from core.db import get_conn
from core.auth import require_role

require_role("employee")

st.title("👤 Employee Dashboard")
col1, col2 = st.columns([8, 2])

with col2:
    if st.button("🚪 Logout"):
        from core.auth import logout
        logout()

conn = get_conn()
user_id = st.session_state["user_id"]

# =========================
# FETCH PROFILE
# =========================
profile = conn.execute("""
    SELECT nik, name, email, role, join_date, permanent_date
    FROM users
    WHERE id=?
""", (user_id,)).fetchone()

# =========================
# FETCH SALDO
# =========================
saldo = conn.execute("""
    SELECT last_year, current_year, change_off, sick_no_doc
    FROM leave_balance
    WHERE user_id=?
""", (user_id,)).fetchone()

# =========================
# PROFILE SECTION
# =========================
st.subheader("👤 Profile")

col1, col2 = st.columns(2)

with col1:
    st.text_input("NIK", profile[0], disabled=True)
    st.text_input("Name", profile[1], disabled=True)
    st.text_input("Email", profile[2], disabled=True)

with col2:
    st.text_input("Role", profile[3], disabled=True)
    st.text_input("Join Date", profile[4], disabled=True)
    st.text_input("Permanent Date", profile[5], disabled=True)

# =========================
# SALDO SECTION
# =========================
st.subheader("🧮 Leave Balance")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Last Year", saldo[0])
c2.metric("Current Year", saldo[1])
c3.metric("Change Off", saldo[2])
c4.metric("Sick (No Doc)", saldo[3])

# =========================
# INFO
# =========================
st.info(
    "Saldo cuti otomatis digunakan dari Last Year terlebih dahulu, "
    "kemudian Current Year. Jika saldo habis, gunakan Change Off."
)
