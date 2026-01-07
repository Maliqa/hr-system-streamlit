import os
import streamlit as st
import time as time_module
from datetime import date, datetime, timedelta, time as dtime
import time as time_module
from core.db import get_conn
from core.holiday import calculate_working_days
from utils.api import api_get, api_post
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
    st.session_state.clear()
    st.switch_page("app.py")
    st.stop()

try:
    user = me.json()
except Exception:
    user = None

if not isinstance(user, dict):
    st.warning("Session invalid / expired. Please login again.")
    st.session_state.clear()
    st.switch_page("app.py")
    st.stop()

user_id = user.get("id") or user.get("user_id")

if not user_id:
    st.error("User ID missing in session")
    st.session_state.clear()
    st.switch_page("app.py")
    st.stop()

# ======================================================
# DB
# ======================================================
conn = get_conn()
cur = conn.cursor()

# ======================================================
# HOLIDAY & LEAVE HELPERS
# ======================================================
# ======================================================
# HOLIDAY & WORKDAY LOGIC (SINGLE SOURCE OF TRUTH)
# ======================================================

# ======================================================
# CHANGE OFF CALCULATION (STABLE)
# ======================================================
def calculate_co(work_type, work_date, end_time, hours):
    is_holiday = work_date.weekday() >= 5

    if work_type == "travelling":
        if not is_holiday or end_time is None:
            return 0.0
        return 1.0 if end_time < time(12, 0) else 0.5

    if work_type == "standby":
        return 0.5 if is_holiday else 0.0

    if work_type == "3-shift":
        return 1.0 if is_holiday else 0.0

    if work_type == "2-shift":
        return 1.5 if is_holiday else 0.5

    if work_type in ["non-shift", "back-office"]:
        if hours is None:
            return 0.0
        if is_holiday:
            return 2.0 if hours >= 12 else 1.0
        return 1.0 if hours >= 12 else 0.0

    return 0.0

# ======================================================
# HEADER
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

# ======================================================
# PROFILE & SALDO
# ======================================================
if menu == MENU_PROFILE:
    row = cur.execute("""
        SELECT nik,name,email,role,join_date,permanent_date
        FROM users WHERE id=?
    """, (user_id,)).fetchone()

    if row:
        nik,name,email,role,join,perm = row
        c1,c2 = st.columns(2)
        with c1:
            st.text_input("NIK", nik, disabled=True)
            st.text_input("Name", name, disabled=True)
            st.text_input("Email", email, disabled=True)
        with c2:
            st.text_input("Role", role, disabled=True)
            st.text_input("Join Date", join, disabled=True)
            st.text_input("Permanent Date", perm, disabled=True)

    saldo = cur.execute("""
        SELECT last_year,current_year,change_off,sick_no_doc
        FROM leave_balance WHERE user_id=?
    """, (user_id,)).fetchone()

    if saldo:
        ly,cy,co,sick = saldo
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Last Year", ly)
        c2.metric("Current Year", cy)
        c3.metric("Change Off", round(co,2))
        c4.metric("Sick (No Doc)", sick)

# ======================================================
# SESSION STATE INIT (WAJIB)
# ======================================================
if "leave_submitted" not in st.session_state:
    st.session_state.leave_submitted = False

if "leave_submit_time" not in st.session_state:
    st.session_state.leave_submit_time = None

if "leave_type" not in st.session_state:
    st.session_state.leave_type = "Personal Leave"

if "leave_start_date" not in st.session_state:
    st.session_state.leave_start_date = date.today()

if "leave_end_date" not in st.session_state:
    st.session_state.leave_end_date = date.today()


# ======================================================
# SUBMIT LEAVE (FINAL - STREAMLIT SAFE)
# ======================================================
elif menu == MENU_LEAVE:
    st.subheader("➕ Submit Leave Request")

    # =============================
    # SESSION STATE INIT (SEKALI SAJA)
    # =============================
    if "leave_start_date" not in st.session_state:
        st.session_state.leave_start_date = date.today()

    if "leave_end_date" not in st.session_state:
        st.session_state.leave_end_date = date.today()

    if "leave_submitted" not in st.session_state:
        st.session_state.leave_submitted = False

    # =============================
    # FORM
    # =============================
    with st.form("leave_form"):

        leave_type = st.selectbox(
            "Leave Type",
            ["Personal Leave", "Change Off", "Sick (No Doc)"],
            key="leave_type",
            disabled=st.session_state.leave_submitted
        )

        col1, col2 = st.columns(2)

        with col1:
            st.date_input(
                "Start Date",
                key="leave_start_date",
                disabled=st.session_state.leave_submitted
            )

        with col2:
            st.date_input(
                "End Date",
                key="leave_end_date",
                disabled=st.session_state.leave_submitted
            )

        reason = st.text_area(
            "Reason",
            height=120,
            disabled=st.session_state.leave_submitted
        )

        submit = st.form_submit_button(
            "Submit Leave",
            disabled=st.session_state.leave_submitted
        )

    # =============================
    # AMBIL VALUE DARI SESSION STATE
    # =============================
    start_date = st.session_state.leave_start_date
    end_date = st.session_state.leave_end_date

    # =============================
    # VALIDASI RANGE TANGGAL
    # =============================
    if end_date < start_date:
        st.warning("⚠️ End Date tidak boleh lebih kecil dari Start Date")
        st.stop()

    # =============================
    # PREVIEW
    # =============================
    preview_days = calculate_working_days(start_date, end_date)
    st.info(f"📅 **Total Leave Requested:** {preview_days} working day(s)")

    # =============================
    # SUBMIT LOGIC
    # =============================
    if submit and not st.session_state.leave_submitted:

        total_days = calculate_working_days(start_date, end_date)

        if total_days <= 0:
            st.error("❌ Tidak ada hari kerja valid (weekend / holiday)")
            st.stop()

        saldo = cur.execute("""
            SELECT last_year, current_year, change_off, sick_no_doc
            FROM leave_balance
            WHERE user_id=?
        """, (user_id,)).fetchone()

        if not saldo:
            st.error("❌ Saldo tidak ditemukan")
            st.stop()

        last_year, current_year, change_off, sick_used = saldo

        if leave_type == "Personal Leave":
            if total_days > (last_year + current_year):
                st.error("❌ Saldo Personal Leave tidak mencukupi")
                st.stop()

        elif leave_type == "Change Off":
            if total_days > change_off:
                st.error("❌ Saldo Change Off tidak mencukupi")
                st.stop()

        elif leave_type == "Sick (No Doc)":
            if total_days > (6 - sick_used):
                st.error("❌ Sisa Sick (No Doc) tidak mencukupi")
                st.stop()

        # =============================
        # INSERT DATABASE
        # =============================
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

        st.session_state.leave_submitted = True

        st.success("✅ Submit leave terkirim dan menunggu approval Manager")

        st.markdown("### 📌 Leave Summary")
        st.markdown(f"""
        - **Type:** {leave_type}  
        - **Period:** {start_date} → {end_date}  
        - **Total:** **{total_days} hari kerja**
        """)



# ======================================================
# LEAVE HISTORY
# ======================================================
elif menu == MENU_HISTORY:
    rows = cur.execute("""
        SELECT start_date,end_date,leave_type,total_days,status,created_at
        FROM leave_requests
        WHERE user_id=?
        ORDER BY created_at DESC
    """, (user_id,)).fetchall()

    df = pd.DataFrame(
        rows,
        columns=["Start","End","Type","Days","Status","Submitted"]
    )
    st.dataframe(df, width="stretch")

# ======================================================
# SUBMIT CHANGE OFF
# ======================================================
# ======================================================
# SUBMIT CHANGE OFF CLAIM (FINAL ENTERPRISE VERSION)
# ======================================================
elif menu == MENU_CO:
    st.subheader("📦 Submit Change Off Claim")

    # =========================
    # CONSTANTS
    # =========================
    SINGLE_DAY_TYPES = ["travelling", "standby"]
    MULTI_DAY_TYPES = ["non-shift", "back-office", "2-shift", "3-shift"]

    # =========================
    # BASIC INPUT
    # =========================
    category = st.selectbox(
        "Employee Category",
        ["Teknisi / Engineer", "Back Office / Workshop"]
    )

    work_type = st.selectbox(
        "Work Type",
        ["travelling", "standby", "non-shift", "back-office", "2-shift", "3-shift"]
    )

    uploaded = st.file_uploader(
        "Upload SPL / Timesheet (PDF)",
        type=["pdf"]
    )

    # =========================
    # MODE A — SINGLE DAY
    # =========================
    if work_type in SINGLE_DAY_TYPES:
        work_date = st.date_input("Work Date")
        end_time = st.time_input("Jam Selesai")

        co = round(calculate_co(work_type, work_date, end_time, None), 2)
        st.info(f"🧮 CO Result: **{co} hari**")

        if st.button("Submit"):
            if not uploaded:
                st.error("PDF wajib diupload")
                st.stop()

            if co <= 0:
                st.error("CO Result = 0, tidak bisa diajukan")
                st.stop()

            folder = f"uploads/change_off/{user_id}"
            os.makedirs(folder, exist_ok=True)
            fname = f"CO_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
            fpath = os.path.join(folder, fname)

            with open(fpath, "wb") as f:
                f.write(uploaded.getbuffer())

            cur.execute("""
                INSERT INTO change_off_claims (
                    user_id, category, work_type, work_date,
                    daily_hours, co_days, description, attachment, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'submitted')
            """, (
                user_id,
                category,
                work_type,
                work_date.isoformat(),
                None,
                co,
                f"{work_type.upper()} activity",
                fpath
            ))

            conn.commit()
            st.success("✅ Change Off submitted (single-day)")
            st.rerun()

    # =========================
    # MODE B — MULTI DAY
    # =========================
    else:
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date")
        with col2:
            end_date = st.date_input("End Date")

        if end_date < start_date:
            st.error("End Date tidak boleh lebih kecil dari Start Date")
            st.stop()

        st.divider()
        st.markdown("### 📋 Daily Work Detail")

        daily_rows = []
        total_co = 0.0

        def daterange(s, e):
            for n in range((e - s).days + 1):
                yield s + timedelta(days=n)

        for d in daterange(start_date, end_date):
            with st.expander(f"📅 {d}"):
                c1, c2 = st.columns(2)
                with c1:
                    start_time = st.time_input(
                        "Start Time", value=dtime(8, 0), key=f"s_{d}"
                    )
                with c2:
                    end_time = st.time_input(
                        "End Time", value=dtime(17, 0), key=f"e_{d}"
                    )

                desc = st.text_input(
                    "Activity Description", key=f"d_{d}"
                )

                hours = (
                    datetime.combine(d, end_time)
                    - datetime.combine(d, start_time)
                ).seconds / 3600

                co = round(calculate_co(work_type, d, end_time, hours), 2)
                total_co += co

                st.info(f"CO Result: **{co} hari**")

                daily_rows.append((d, hours, co, desc))

        st.success(f"🧮 TOTAL CO: **{round(total_co,2)} hari**")

        if st.button("Submit"):
            if not uploaded:
                st.error("PDF wajib diupload")
                st.stop()

            if total_co <= 0:
                st.error("Total CO = 0, tidak bisa diajukan")
                st.stop()

            folder = f"uploads/change_off/{user_id}"
            os.makedirs(folder, exist_ok=True)
            fname = f"CO_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
            fpath = os.path.join(folder, fname)

            with open(fpath, "wb") as f:
                f.write(uploaded.getbuffer())

            for d, hrs, co, desc in daily_rows:
                if co <= 0:
                    continue

                cur.execute("""
                    INSERT INTO change_off_claims (
                        user_id, category, work_type, work_date,
                        daily_hours, co_days, description, attachment, status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'submitted')
                """, (
                    user_id,
                    category,
                    work_type,
                    d.isoformat(),
                    hrs,
                    co,
                    desc or f"{work_type} activity",
                    fpath
                ))

            conn.commit()
            st.success("✅ Change Off multi-day submitted")
            st.rerun()

# ======================================================
# CHANGE OFF HISTORY
# ======================================================
elif menu == MENU_CO_HISTORY:
    rows = cur.execute("""
        SELECT work_date,co_days,description,status,created_at
        FROM change_off_claims
        WHERE user_id=?
        ORDER BY work_date DESC
    """, (user_id,)).fetchall()

    df = pd.DataFrame(
        rows,
        columns=["Work Date","CO Days","Description","Status","Submitted"]
    )
    st.dataframe(df, width="stretch")

conn.close()