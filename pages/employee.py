import streamlit as st
from datetime import date, timedelta
from utils.api import api_get, api_post
from core.db import get_conn
from core.leave_engine import run_leave_engine
from core.leave_calculation import calculate_leave_days
# ======================================================
# PAGE CONFIG + HIDE SIDEBAR
# ======================================================
st.set_page_config(page_title="Employee Dashboard", layout="wide")
st.markdown("""
<style>
section[data-testid="stSidebar"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ======================================================
# AUTH GUARD (FASTAPI)
# ======================================================
me = api_get("/me", timeout=5)
if not (me.status_code == 200 and me.json()):
    st.switch_page("app.py")

payload = me.json()
if payload["role"] != "employee":
    st.error("Unauthorized")
    st.stop()

user_id = payload["user_id"]

# ======================================================
# AUTO CUTI ENGINE (SYSTEM JOB)
# ======================================================
run_leave_engine()

# ======================================================
# DB
# ======================================================
conn = get_conn()
cur = conn.cursor()

# ======================================================
# HEADER
# ======================================================
st.title("👤 Employee Dashboard")

if st.button("Logout"):
    api_post("/logout")
    st.switch_page("app.py")

menu = st.radio(
    "Menu",
    ["📄 Profile & Saldo", "➕ Submit Leave", "📜 Leave History"],
    horizontal=True
)

# ======================================================
# FETCH DATA
# ======================================================
user = cur.execute("""
    SELECT nik, name, email, role, join_date, permanent_date
    FROM users WHERE id=?
""", (user_id,)).fetchone()

saldo = cur.execute("""
    SELECT last_year, current_year, change_off, sick_no_doc
    FROM leave_balance WHERE user_id=?
""", (user_id,)).fetchone()

nik, name, email, role, join_date, permanent_date = user
last_year, current_year, change_off, sick_no_doc = saldo

today = date.today()
ly_status = "expired" if today.month > 6 else "valid until 30 Jun"

# ======================================================
# PROFILE & SALDO
# ======================================================
if menu == "📄 Profile & Saldo":
    st.subheader("👤 Profile")

    c1, c2 = st.columns(2)
    with c1:
        st.text_input("NIK", nik, disabled=True)
        st.text_input("Name", name, disabled=True)
        st.text_input("Email", email, disabled=True)
    with c2:
        st.text_input("Role", role, disabled=True)
        st.text_input("Join Date", join_date, disabled=True)
        st.text_input("Permanent Date", permanent_date or "-", disabled=True)

    st.divider()
    st.subheader("📊 Leave Balance")

    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Last Year", last_year, help=f"Last Year leave is {ly_status}")
    b2.metric("Current Year", current_year, help="+1 day every 1st of the month")
    b3.metric("Change Off", change_off, help="Claimable per semester")
    b4.metric("Sick (No Doc)", sick_no_doc, help="Max 6 days per year")

    st.info(
        "Leave deduction order:\n"
        "- Last Year (valid until 30 June)\n"
        "- Current Year (+1 every month)\n"
        "- Change Off (from overtime)"
    )
    st.caption("Next leave accrual: +1 day on the 1st of next month")

# ======================================================
# SUBMIT LEAVE
# ======================================================
elif menu == "➕ Submit Leave":
    st.subheader("➕ Submit Leave")

    leave_type = st.selectbox(
        "Leave Type",
        ["Personal Leave", "Change Off", "Sick (No Doc)"]
    )

    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("Start Date")
    with c2:
        end_date = st.date_input("End Date")

    reason = st.text_area("Reason")

    if end_date < start_date:
        st.error("End date cannot be earlier than start date")
        st.stop()
    total_days = calculate_leave_days(start_date, end_date)

    if total_days == 0:
        st.error("No working day selected (weekend / holiday only)")
        st.stop()

    st.info(f"Total working days requested: **{total_days}**")

    st.warning(
        "This leave will be deducted automatically:\n"
        "Last Year → Current Year → Change Off"
    )

    if today.month > 6 and last_year > 0:
        st.warning("Last Year leave has expired after 30 June and will not be used.")

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
elif menu == "📜 Leave History":
    st.subheader("📜 Leave History")

    rows = cur.execute("""
        SELECT
            start_date,
            end_date,
            leave_type,
            total_days,
            status,
            created_at
        FROM leave_requests
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,)).fetchall()

    if not rows:
        st.info("No leave history")
    else:
        import pandas as pd

        df = pd.DataFrame(
            rows,
            columns=[
                "Start Date",
                "End Date",
                "Leave Type",
                "Days",
                "Status",
                "Submitted At"
            ]
        )

        # Optional: format date columns (lebih rapi)
        for col in ["Start Date", "End Date", "Submitted At"]:
            df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d")

        st.dataframe(
            df,
            width="stretch",
            hide_index=True
        )


conn.close()
