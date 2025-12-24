import os
import streamlit as st
from datetime import date
from core.db import get_conn
from core.leave_calculation import calculate_leave_days
from utils.api import api_get, api_post
# ======================================================
# SESSION GUARD
# ======================================================
st.set_page_config(page_title="Employee Dashboard", layout="wide")
st.markdown("""
<style>
section[data-testid="stSidebar"] { display: none; }
</style>
""", unsafe_allow_html=True)


me = api_get("/me")

if me.status_code != 200:
    st.warning("Session expired. Please login again.")
    st.session_state.clear()
    st.switch_page("app.py")
    st.stop()

user = me.json()

if not isinstance(user, dict):
    st.warning("Invalid session data. Please login again.")
    st.session_state.clear()
    st.switch_page("app.py")
    st.stop()

user_id = user.get("id") or user.get("user_id") or user.get("uid")

if not user_id:
    st.error("User ID missing")
    st.stop()

role = user.get("role")

# ======================================================
# DB
# ======================================================
conn = get_conn()
cur = conn.cursor()

# ======================================================
# UI HEADER
# ======================================================
st.title("👤 Employee Dashboard")

if st.button("Logout"):
    api_post("/logout")
    st.switch_page("app.py")

# ======================================================
# MENU
# ======================================================
MENU_PROFILE = "📄 Profile & Saldo"
MENU_LEAVE = "➕ Submit Leave"
MENU_HISTORY = "📜 Leave History"
MENU_CO = "📦 Submit Change Off Claim"

menu = st.radio(
    "Menu",
    [MENU_PROFILE, MENU_LEAVE, MENU_HISTORY, MENU_CO],
    horizontal=True
)

# ======================================================
# PROFILE & SALDO
# ======================================================
if menu == MENU_PROFILE:
    st.subheader("📄 Profile")

    user = cur.execute("""
        SELECT nik, name, email, role, join_date, permanent_date
        FROM users WHERE id=?
    """, (user_id,)).fetchone()

    saldo = cur.execute("""
        SELECT last_year, current_year, change_off, sick_no_doc
        FROM leave_balance WHERE user_id=?
    """, (user_id,)).fetchone()

    c1, c2 = st.columns(2)
    with c1:
        st.text_input("NIK", user[0], disabled=True)
        st.text_input("Name", user[1], disabled=True)
        st.text_input("Email", user[2], disabled=True)
    with c2:
        st.text_input("Role", user[3], disabled=True)
        st.text_input("Join Date", user[4], disabled=True)
        st.text_input("Permanent Date", user[5], disabled=True)

    st.subheader("📊 Leave Balance")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Last Year", saldo[0])
    c2.metric("Current Year", saldo[1])
    c3.metric("Change Off", saldo[2])
    c4.metric("Sick (No Doc)", saldo[3])

    st.info(
        "Leave deduction order:\n"
        "- Last Year (valid until 30 June)\n"
        "- Current Year (+1 setiap bulan)\n"
        "- Change Off"
    )

# ======================================================
# SUBMIT LEAVE
# ======================================================
elif menu == MENU_LEAVE:
    st.subheader("➕ Submit Leave")

    leave_type = st.selectbox(
        "Leave Type",
        ["Personal Leave", "Change Off", "Sick (No Doc)"]
    )

    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("Start Date", value=date.today())
    with c2:
        end_date = st.date_input("End Date", value=date.today())

    reason = st.text_area("Reason")

    if end_date < start_date:
        st.error("End date cannot be earlier than start date")
        st.stop()

    total_days = calculate_leave_days(start_date, end_date)
    st.info(f"Total working days requested: **{total_days}**")

    if st.button("Submit Leave"):
        cur.execute("""
            INSERT INTO leave_requests
            (user_id, leave_type, start_date, end_date, total_days, reason, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'submitted', DATE('now'))
        """, (
            user_id,
            leave_type,
            start_date.isoformat(),
            end_date.isoformat(),
            total_days,
            reason
        ))
        conn.commit()
        st.success("Leave submitted and waiting for approval")
        st.rerun()

# ======================================================
# LEAVE HISTORY
# ======================================================
elif menu == MENU_HISTORY:
    st.subheader("📜 Leave History")

    rows = cur.execute("""
        SELECT start_date, end_date, leave_type, total_days, status, created_at
        FROM leave_requests
        WHERE user_id=?
        ORDER BY created_at DESC
    """, (user_id,)).fetchall()

    if not rows:
        st.info("No leave history")
    else:
        st.dataframe(
            rows,
            width="stretch",
            column_config={
                0: "Start",
                1: "End",
                2: "Type",
                3: "Days",
                4: "Status",
                5: "Submitted At"
            }
        )

# ======================================================
# SUBMIT CHANGE OFF CLAIM
# ======================================================
elif menu == MENU_CO:
    st.subheader("📦 Submit Change Off Claim")

    work_date = st.date_input("Work Date", value=date.today())
    hours = st.number_input("Total Working Hours", min_value=1.0, step=0.5)
    description = st.text_area("Description")

    uploaded = st.file_uploader(
        "Upload Timesheet / SPL (PDF only)",
        type=["pdf"]
    )

    if st.button("Submit Change Off"):
        # VALIDATION
        if uploaded is None:
            st.error("Timesheet / SPL (PDF) wajib diupload")
            st.stop()

        if uploaded.size > 10 * 1024 * 1024:
            st.error("File maksimal 10MB")
            st.stop()

        # SAVE FILE
        base_dir = f"uploads/change_off/{user_id}"
        os.makedirs(base_dir, exist_ok=True)

        filename = f"CO_{user_id}_{work_date}.pdf"
        file_path = os.path.join(base_dir, filename)

        with open(file_path, "wb") as f:
            f.write(uploaded.getbuffer())

        # INSERT DB
        cur.execute("""
            INSERT INTO change_off_claims
            (user_id, work_date, hours, description, file_path, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'submitted', DATE('now'))
        """, (
            user_id,
            work_date.isoformat(),
            hours,
            description,
            file_path
        ))
        conn.commit()

        st.success("Change Off claim berhasil dikirim")
        st.rerun()

# ======================================================
conn.close()
