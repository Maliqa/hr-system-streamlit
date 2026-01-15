import os
import streamlit as st
from datetime import date, datetime, timedelta, time as dtime
import pandas as pd

from core.db import get_conn
from core.holiday import calculate_working_days
from core.holiday import load_holidays
from core.change_off import calculate_co
from utils.api import api_get, api_post
from utils.emailer import send_email
from utils.email_templates import (
    leave_request_email,
    change_off_request_email
)

# ======================================================
# PAGE CONFIG + SESSION GUARD
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
# GET EMPLOYEE NAME (🔥 FIX UTAMA, GLOBAL)
# ======================================================
emp_row = cur.execute(
    "SELECT name FROM users WHERE id=?",
    (user_id,)
).fetchone()

EMP_NAME = emp_row[0] if emp_row else "Employee"

# ======================================================
# HEADER
# ======================================================
col1, col2 = st.columns([7, 3])

with col1:
    st.title("👤 Employee Dashboard")
    if st.button("Logout"):
        api_post("/logout")
        st.switch_page("app.py")

with col2:
    st.image("assets/cistech.png", width=420)

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
        SELECT nik,name,email,role,division,join_date,permanent_date
        FROM users WHERE id=?
    """, (user_id,)).fetchone()

    saldo = cur.execute("""
        SELECT last_year,current_year,change_off,sick_no_doc
        FROM leave_balance WHERE user_id=?
    """, (user_id,)).fetchone()

    if row:
        nik, name, email, role, division, join, perm = row

        st.markdown(f"""
        <div style="background:#f8fafc;border:1px solid #e5e7eb;
        border-radius:14px;padding:20px;margin-bottom:16px;">
            <h3>👤 {name}</h3>
            <p>{role.upper()} • {division} • NIK {nik}</p>
            <p>📧 {email}</p>
            <p>📅 Join Date: {join}<br>🏁 Permanent Date: {perm or '-'}</p>
        </div>
        """, unsafe_allow_html=True)

    if saldo:
        ly, cy, co, sick = saldo
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌴 Last Year", ly)
        c2.metric("📅 Current Year", cy)
        c3.metric("🧳 Change Off", round(co, 2))
        c4.metric("🤒 Sick (No Doc)", sick)

# ======================================================
# SUBMIT LEAVE
# ======================================================
elif menu == MENU_LEAVE:
    st.subheader("➕ Submit Leave Request")

    # =========================
    # AMBIL SALDO
    # =========================
    saldo = cur.execute("""
        SELECT current_year, change_off
        FROM leave_balance
        WHERE user_id=?
    """, (user_id,)).fetchone()

    saldo_personal = saldo[0] if saldo else 0
    saldo_co = saldo[1] if saldo else 0

    # =========================
    # FORM INPUT
    # =========================
    leave_type = st.selectbox(
        "Leave Type",
        ["Personal Leave", "Change Off", "Sick (No Doc)"]
    )

    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("Start Date", date.today())
    with c2:
        end_date = st.date_input("End Date", date.today())

    reason = st.text_area("Reason")

    # =========================
    # VALIDASI TANGGAL
    # =========================
    if end_date < start_date:
        st.error("❌ End Date tidak boleh lebih kecil dari Start Date")
        st.stop()

    total_days = calculate_working_days(start_date, end_date)
    st.info(f"📅 Total Leave Requested: {total_days} working day(s)")

    # =========================
    # LOGIC DISABLE SUBMIT
    # =========================
    submit_disabled = False

    if leave_type == "Personal Leave":
        if saldo_personal < total_days:
            st.error(
                f"❌ Saldo Personal Leave tidak mencukupi "
                f"(Sisa: {saldo_personal} hari)"
            )
            submit_disabled = True
        else:
            st.warning(
                f"⚠️ Anda akan menggunakan {total_days} hari Personal Leave.\n"
                f"Sisa saldo: {saldo_personal - total_days} hari"
            )

    elif leave_type == "Change Off":
        if saldo_co < total_days:
            st.error(
                f"❌ Saldo Change Off tidak mencukupi "
                f"(Sisa: {saldo_co} hari)"
            )
            submit_disabled = True
        else:
            st.warning(
                f"⚠️ {total_days} hari Change Off akan ditukar menjadi cuti.\n"
                f"Sisa saldo CO: {saldo_co - total_days} hari"
            )

    elif leave_type == "Sick (No Doc)":
        st.info("ℹ️ Sick Leave tidak menggunakan saldo cuti.")

    # =========================
    # SUBMIT BUTTON (AUTO DISABLE)
    # =========================
    submit = st.button(
        "Submit Leave",
        disabled=submit_disabled
    )

    if submit:
        cur.execute("""
            INSERT INTO leave_requests
            (user_id, leave_type, start_date, end_date, total_days, reason, status)
            VALUES (?, ?, ?, ?, ?, ?, 'submitted')
        """, (
            user_id,
            leave_type,
            start_date.isoformat(),
            end_date.isoformat(),
            total_days,
            reason
        ))
        conn.commit()

        # EMAIL MANAGER
        mgr = cur.execute("""
            SELECT u.email
            FROM users u
            JOIN users e ON e.manager_id=u.id
            WHERE e.id=?
        """, (user_id,)).fetchone()

        if mgr:
            send_email(
                to_email=mgr[0],
                subject="Leave Request Pending Approval",
                body=leave_request_email(
                    emp_name=EMP_NAME,
                    type=leave_type,
                    start=start_date,
                    end=end_date,
                    days=total_days
                ),
                html=True
            )

        st.success("✅ Leave submitted")


# ======================================================
# SUBMIT CHANGE OFF CLAIM (REWRITE FULL – STABLE)
# ======================================================
elif menu == MENU_CO:
    st.subheader("📦 Submit Change Off Claim")

    # =====================================
    # CONSTANTS
    # =====================================
    SINGLE_DAY_TYPES = ["travelling", "standby"]
    MULTI_DAY_TYPES = ["non-shift", "back-office", "2-shift", "3-shift"]
    NO_UPLOAD_TYPES = ["travelling", "standby"]

    # =====================================
    # BASIC INPUT
    # =====================================
    category = st.selectbox(
        "Employee Category",
        ["Teknisi / Engineer", "Back Office / Workshop"]
    )

    work_type = st.selectbox(
        "Work Type",
        SINGLE_DAY_TYPES + MULTI_DAY_TYPES
    )

    # =====================================
    # FILE UPLOAD
    # =====================================
    uploaded = None
    if work_type not in NO_UPLOAD_TYPES:
        uploaded = st.file_uploader(
            "Upload SPL / Timesheet (PDF)",
            type=["pdf"]
        )
    else:
        st.info("ℹ️ Travelling & Standby tidak perlu upload dokumen")

    # =====================================
    # EMPLOYEE NAME
    # =====================================
    emp_row = cur.execute(
        "SELECT name FROM users WHERE id=?",
        (user_id,)
    ).fetchone()
    emp_name = emp_row[0] if emp_row else "Employee"

    # =====================================
    # MODE A — SINGLE DAY
    # =====================================
    if work_type in SINGLE_DAY_TYPES:

        st.markdown("### 📅 Work Detail (Single Day)")

        # =========================
        # INPUT USER
        # =========================
        work_date = st.date_input("Work Date")
        start_time = st.time_input("Start Time", value=dtime(8, 0))
        end_time = st.time_input("End Time", value=dtime(17, 0))

        # =========================
        # 🔥 INI TEMPAT PEMANGGILAN calculate_co
        # =========================
        co, day_type = calculate_co(
            category=category,
            work_type=work_type,
            work_date=work_date,
            start_time=start_time,
            end_time=end_time
        )

        # =========================
        # DISPLAY KE USER
        # =========================
        st.info(f"🧮 CO Result: **{co} day(s)**")
        st.caption(f"📅 Day Type: **{day_type.upper()}**")


        if st.button("Submit Change Off"):
            if co <= 0:
                st.error("CO Result = 0, tidak bisa diajukan")
                st.stop()

            fpath = None
            if uploaded:
                folder = f"uploads/change_off/{user_id}"
                os.makedirs(folder, exist_ok=True)
                fname = f"CO_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                fpath = os.path.join(folder, fname)
                with open(fpath, "wb") as f:
                    f.write(uploaded.getbuffer())

            # Calculate hours
            hours = (
                datetime.combine(work_date, end_time)
                - datetime.combine(work_date, start_time)
            ).seconds / 3600

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
                hours,
                co,
                f"{work_type.upper()} ({day_type})",
                fpath
            ))
            conn.commit()

            # EMAIL MANAGER
            mgr = cur.execute("""
                SELECT u.email
                FROM users u
                JOIN users e ON e.manager_id = u.id
                WHERE e.id = ?
            """, (user_id,)).fetchone()

            if mgr and mgr[0]:
                send_email(
                    to_email=mgr[0],
                    subject="Change Off Claim Pending Approval",
                    body=change_off_request_email(
                        emp_name=emp_name,
                        work_type=work_type,
                        period=str(work_date),
                        day_type=day_type,
                        co_days=co
                    ),
                    html=True
                )

            st.success("✅ Change Off submitted (single day)")
            

    # =====================================
    # MODE B — MULTI DAY
    # =====================================
    else:
        st.markdown("### 📅 Work Period")

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

                start_time = st.time_input(
                    "Start Time", value=dtime(8, 0), key=f"s_{d}"
                )
                end_time = st.time_input(
                    "End Time", value=dtime(17, 0), key=f"e_{d}"
                )

                # =========================
                # 🔥 PEMANGGILAN calculate_co
                # =========================
                co, day_type = calculate_co(
                    category=category,
                    work_type=work_type,
                    work_date=d,
                    start_time=start_time,
                    end_time=end_time
                )

                st.info(f"CO Result: **{co} day(s)**")
                st.caption(f"📅 Day Type: **{day_type.upper()}**")

                daily_rows.append((d, co, day_type))
                total_co += co


        st.success(f"🧮 TOTAL CO: **{round(total_co, 2)} day(s)**")

        if st.button("Submit Change Off"):
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

            for d, co, day_type in daily_rows:
                if co <= 0:
                    continue

                # Calculate hours for each day
                hours = (
                    datetime.combine(d, dtime(17, 0))  # default end time
                    - datetime.combine(d, dtime(8, 0))  # default start time
                ).seconds / 3600

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
                    hours,
                    co,
                    f"{work_type.upper()} ({day_type})",
                    fpath
                ))

            conn.commit()

            # EMAIL MANAGER
            mgr = cur.execute("""
                SELECT u.email
                FROM users u
                JOIN users e ON e.manager_id = u.id
                WHERE e.id = ?
            """, (user_id,)).fetchone()

            if mgr and mgr[0]:
                send_email(
                    to_email=mgr[0],
                    subject="Change Off Claim Pending Approval",
                    body=change_off_request_email(
                        emp_name=emp_name,
                        work_type=work_type,
                        period=str(work_date),
                        co_days=co,
                        day_type=day_type
                    ),
                    html=True
                )

            st.success("✅ Change Off submitted (multi-day)")
            



# ======================================================
# HISTORY
# ======================================================
elif menu == MENU_HISTORY:
    rows = cur.execute("""
        SELECT start_date,end_date,leave_type,total_days,status
        FROM leave_requests WHERE user_id=?
    """, (user_id,)).fetchall()

    st.dataframe(pd.DataFrame(
        rows,
        columns=["Start", "End", "Type", "Days", "Status"]
    ))

elif menu == MENU_CO_HISTORY:
    rows = cur.execute("""
        SELECT work_date,co_days,status
        FROM change_off_claims WHERE user_id=?
    """, (user_id,)).fetchall()

    st.dataframe(pd.DataFrame(
        rows,
        columns=["Work Date", "CO Days", "Status"]
    ))

conn.close()
