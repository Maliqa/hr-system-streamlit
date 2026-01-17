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
    st.image("assets/cistech.png", width=250)

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
# SUBMIT CHANGE OFF CLAIM (REVISED – CHECKBOX BONUS)
# ======================================================
elif menu == MENU_CO:
    st.subheader("📦 Submit Change Off Claim")

    holidays = load_holidays()

    # =====================================
    # BASIC INPUT
    # =====================================
    category = st.selectbox(
        "Employee Category",
        ["Teknisi / Engineer", "Back Office / Workshop"]
    )

    work_type = st.selectbox(
        "Main Work Type",
        ["non-shift", "2-shift", "3-shift", "back-office"]
    )

    # =====================================
    # OPTIONAL ACTIVITY (CHECKBOX)
    # =====================================
    st.markdown("### ➕ Additional Activity (Optional)")
    colx, coly = st.columns(2)

    with colx:
        is_travelling = st.checkbox("✈️ Travelling")

    with coly:
        is_standby = st.checkbox("🕒 Standby (Luar Kota)")


    # =====================================
    # MODE SINGLE DAY
    # =====================================
    st.markdown("### 📅 Work Detail")

    work_date = st.date_input("Work Date", key="co_date")
    start_time = st.time_input("Start Time", value=dtime(8, 0))
    end_time = st.time_input("End Time", value=dtime(17, 0))

    comment = st.text_area(
        "📝 Activity / Work Description",
        placeholder="Contoh: Maintenance panel / Travelling site A ke B"
    )

    # =====================================
    # MAIN CO CALCULATION (BASE)
    # =====================================
    co_base, day_type = calculate_co(
        category=category,
        work_type=work_type,
        work_date=work_date,
        start_time=start_time,
        end_time=end_time
    )

    total_co = co_base
    detail_notes = [f"{work_type.upper()} ({day_type})"]

    # =====================================
    # ADDITIONAL TRAVELLING
    # =====================================
    if is_travelling:
        if day_type in ["weekend", "holiday"]:
            if start_time < dtime(12, 0):
                total_co += 0.5
                detail_notes.append("Travelling < 12:00 (+0.5)")
            else:
                total_co += 0.5
                detail_notes.append("Travelling > 12:00 (+0.5)")

    # =====================================
    # ADDITIONAL STANDBY
    # =====================================
    if is_standby and day_type in ["weekend", "holiday"]:
        total_co += 0.5
        detail_notes.append("Standby (+0.5)")

    # =====================================
    # DISPLAY RESULT
    # =====================================
    st.info(f"🧮 Total Change Off: **{round(total_co, 2)} day(s)**")
    st.caption(" | ".join(detail_notes))

    # =====================================
    # VALIDATION
    # =====================================
    submit_disabled = False

    if total_co <= 0:
        st.warning("Tidak ada CO yang bisa diklaim")
        submit_disabled = True

    if (is_travelling or is_standby) and not comment:
        st.warning("Mohon isi Activity / Work Description")
        submit_disabled = True

    
    if "co_submitted" not in st.session_state:
        st.session_state["co_submitted"] = False

    # =====================================
    # SUBMIT
    # =====================================
    if st.button("Submit Change Off", disabled=submit_disabled or
    st.session_state["co_submitted"]):

        folder = f"uploads/change_off/{user_id}"
        os.makedirs(folder, exist_ok=True)
        fname = f"CO_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        fpath = os.path.join(folder, fname)

        with open(fpath, "wb") as f:
            f.write(uploaded.getbuffer())

        hours = (
            datetime.combine(work_date, end_time)
            - datetime.combine(work_date, start_time)
        ).seconds / 3600

        description = " | ".join(detail_notes)
        if comment:
            description += f" | {comment}"

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
            round(total_co, 2),
            description,
            fpath
        ))

        conn.commit()

        # EMAIL MANAGER
        mgr = cur.execute("""
            SELECT u.email
            FROM users u
            JOIN users e ON e.manager_id=u.id
            WHERE e.id=?
        """, (user_id,)).fetchone()

        if mgr and mgr[0]:
            send_email(
                to_email=mgr[0],
                subject="Change Off Claim Pending Approval",
                body=change_off_request_email(
                    emp_name=EMP_NAME,
                    work_type=work_type,
                    period=str(work_date),
                    day_type=day_type,
                    co_days=round(total_co, 2)
                ),
                html=True
            )

        # RESET FORM
        st.session_state["co_submitted"] = True
        st.success("✅ Change Off submitted")



            

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
