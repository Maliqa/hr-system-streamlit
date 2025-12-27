import os
import streamlit as st
from datetime import date
from core.db import get_conn
from core.leave_calculation import calculate_leave_days
from utils.api import api_get, api_post
import base64
from datetime import timedelta, datetime
import pandas as pd

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
MENU_CO_HISTORY = "📦 Change Off History"
menu = st.radio(
    "Menu",
    [MENU_PROFILE, MENU_LEAVE, MENU_HISTORY, MENU_CO, MENU_CO_HISTORY],
    horizontal=True
)

# ---------- helper for pdf preview (manager) ----------
def pdf_to_base64(path):
    with open(path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("utf-8")
    return b64

# ---------- business logic: CO mapping ----------
def calculate_co_for_single_day(work_date: date, hours: float, work_type: str):
    """
    Simplified rules based on the company picture you provided.
    This function returns CO days (float, can be 0.5, 1, 1.5, 2).
    Adjust mapping to match exact company rules.
    """
    dow = work_date.weekday()  # 0=Mon ... 6=Sun
    is_weekend = dow >= 5

    # default rules (easy-to-read mapping):
    if work_type == "travelling":
        # travelling on weekday -> no CO, weekend -> 1 day if >12h else 0.5 maybe
        if is_weekend:
            return 1.0 if hours > 12 else 0.5
        return 0.0

    if work_type == "standby":
        # standby on weekend/outcity => 0.5
        return 0.5 if is_weekend else 0.0

    if work_type == "3-shift":
        # 3-shift (8h) -> weekday no CO, weekend may be 1 day
        return 1.0 if is_weekend else 0.0

    if work_type == "2-shift":
        # 12h shift -> weekday maybe 1 day, weekend 1.5
        return 1.0 if not is_weekend else 1.5

    # back office / non-shift
    if work_type == "non-shift":
        if not is_weekend:
            return 1.0 if hours > 12 else 0.0
        else:
            # weekend
            return 2.0 if hours > 12 else 1.0

    # default fallback
    if is_weekend:
        return 1.0
    return 0.0

def calculate_co_for_date_range(start_date: date, end_date: date, hours: float, work_type: str):
    """
    If user claims multiple days (range), sum CO for each day.
    """
    cur = start_date
    total = 0.0
    while cur <= end_date:
        total += calculate_co_for_single_day(cur, hours, work_type)
        cur += timedelta(days=1)
    return total

# ======================================================
# PROFILE & SALDO
# ======================================================
if menu == MENU_PROFILE:
    st.subheader("📄 Profile")

    user = cur.execute("""
        SELECT nik, name, email, role, join_date, permanent_date
        FROM users WHERE id=?
    """, (user_id,)).fetchone()

    if user:
        nik, name, email, role, join_date, permanent_date = user
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("NIK", nik, disabled=True)
            st.text_input("Name", name, disabled=True)
            st.text_input("Email", email, disabled=True)
        with c2:
            st.text_input("Role", role, disabled=True)
            st.text_input("Join Date", join_date, disabled=True)
            st.text_input("Permanent Date", permanent_date, disabled=True)
    else:
        st.error("Profile data not found.")

    st.subheader("📊 Leave Balance")
    saldo = cur.execute("""
        SELECT last_year, current_year, change_off, sick_no_doc
        FROM leave_balance WHERE user_id=?
    """, (user_id,)).fetchone()

    if saldo:
        last_year, current_year, change_off, sick_no_doc = saldo
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Last Year", last_year)
        c2.metric("Current Year", current_year)
        c3.metric("Change Off", change_off)
        c4.metric("Sick (No Doc)", sick_no_doc)

        st.info(
            "Leave deduction order:\n"
            "- Last Year (valid until 30 June)\n"
            "- Current Year (+1 setiap bulan)\n"
            "- Change Off"
        )
    else:
        st.error("Leave balance data not found.")

# ======================================================
# SUBMIT LEAVE (Improved UI)
# ======================================================
elif menu == MENU_LEAVE:
    st.subheader("➕ Submit Leave Request")

    with st.form("leave_form"):
        col1, col2 = st.columns(2)
        with col1:
            leave_type = st.selectbox(
                "Leave Type",
                ["Personal Leave", "Change Off", "Sick (No Doc)"]
            )
            start_date = st.date_input("Start Date", value=date.today())
        with col2:
            end_date = st.date_input("End Date", value=date.today())
            reason = st.text_area("Reason", height=120)

        submitted = st.form_submit_button("Submit Leave Request")

    if submitted:
        if end_date < start_date:
            st.error("End date cannot be earlier than start date.")
        else:
            total_days = calculate_leave_days(start_date, end_date)
            st.info(f"Total working days requested: **{total_days}**")

            # Insert to DB
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
            st.success("✅ Leave request submitted successfully and is waiting for approval.")
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
        st.info("No leave history found.")
    else:
        df = pd.DataFrame(rows, columns=["Start", "End", "Type", "Days", "Status", "Submitted At"])
        # Format dates
        for col in ["Start", "End", "Submitted At"]:
            df[col] = pd.to_datetime(df[col]).dt.date.astype(str)
        st.dataframe(df, width='stretch')

# ======================================================
# SUBMIT CHANGE OFF CLAIM (Added and Improved)
# ======================================================
elif menu == MENU_CO:
    st.subheader("📦 Submit Change Off Claim")

    with st.form("change_off_form", clear_on_submit=False):
        col1, col2 = st.columns([2,1])
        with col1:
            # option: single day or range
            multi = st.checkbox("Claim multiple days (date range)", value=False)
            if multi:
                start_date = st.date_input("Start Work Date", value=date.today())
                end_date = st.date_input("End Work Date", value=date.today())
                if end_date < start_date:
                    st.error("End date cannot be earlier than start date")
                    st.stop()
            else:
                work_date = st.date_input("Work Date", value=date.today())

            hours = st.number_input("Total Working Hours (per day)", min_value=0.5, value=1.0, step=0.5)
            description = st.text_area("Description / Reason", height=120)

            work_type = st.selectbox("Work Type (choose the category that fits)", [
                "non-shift", "2-shift", "3-shift", "travelling", "standby", "back-office"
            ], index=0)

        with col2:
            uploaded = st.file_uploader("Upload Timesheet / SPL (PDF only) *required", type=["pdf"])

        submitted = st.form_submit_button("Submit Change Off Claim")

    if submitted:
        # validations
        if uploaded is None:
            st.error("⚠️ Timesheet / SPL (PDF) wajib diupload.")
            st.stop()

        # size limit
        max_mb = 20
        try:
            size = uploaded.size
        except Exception:
            size = None
        if size and size > max_mb * 1024 * 1024:
            st.error(f"⚠️ File terlalu besar. Maks {max_mb} MB.")
            st.stop()

        # calculate CO days
        if multi:
            total_co = calculate_co_for_date_range(start_date, end_date, hours, work_type)
            claim_start = start_date
            claim_end = end_date
        else:
            total_co = calculate_co_for_single_day(work_date, hours, work_type)
            claim_start = work_date
            claim_end = work_date

        # save file
        user_folder = os.path.join("uploads/change_off", str(user_id))
        os.makedirs(user_folder, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"CO_{user_id}_{ts}.pdf"
        file_path = os.path.join(user_folder, filename)
        with open(file_path, "wb") as f:
            f.write(uploaded.getbuffer())

        # insert to DB
        claim_desc = description
        if multi and claim_start != claim_end:
            claim_desc = f"[Range {claim_start.isoformat()} -> {claim_end.isoformat()}] {description}"

        cur.execute("""
            INSERT INTO change_off_claims
            (user_id, work_date, hours, description, file_path, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, claim_start.isoformat(), hours, claim_desc, file_path, "submitted"))
        conn.commit()

        st.success("✅ Change Off claim successfully submitted.")
        st.info(f"Calculated CO days (company-rule estimate): **{total_co}**")
        # Show preview of uploaded PDF inline (base64 embed)
        try:
            b64 = pdf_to_base64(file_path)
            pdf_display = f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="600" type="application/pdf"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
        except Exception as e:
            st.warning("File uploaded, but preview not available: " + str(e))




# ======================================================
# CHANGE OFF HISTORY
# ======================================================
elif menu == MENU_CO_HISTORY:
    st.subheader("📦 Change Off History")

    rows = cur.execute("""
        SELECT work_date, hours, description, status, created_at
        FROM change_off_claims
        WHERE user_id=?
        ORDER BY created_at DESC
    """, (user_id,)).fetchall()

    if not rows:
        st.info("No change off history found.")
    else:
        df = pd.DataFrame(
            rows,
            columns=[
                "Work Date",
                "Hours",
                "Description",
                "Status",
                "Submitted At"
            ]
        )

        # format date
        for col in ["Work Date", "Submitted At"]:
            df[col] = pd.to_datetime(df[col]).dt.date.astype(str)

        st.dataframe(df, width='stretch')


# ======================================================
conn.close()
