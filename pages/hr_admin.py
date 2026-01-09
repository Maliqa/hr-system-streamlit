import streamlit as st
from datetime import date
from utils.api import api_get, api_post
from core.db import get_conn
from core.auth import hash_password
from core.leave_engine import run_leave_engine

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(page_title="HR Admin Dashboard", layout="wide")
st.markdown("""
<style>
section[data-testid="stSidebar"] { display: none; }
div[data-baseweb="radio"] > div { gap: 14px; }
</style>
""", unsafe_allow_html=True)

# ======================================================
# AUTH
# ======================================================
me = api_get("/me")
if not (me.status_code == 200 and isinstance(me.json(), dict)):
    st.session_state.clear()
    st.switch_page("app.py")
    st.stop()

payload = me.json()
if payload.get("role") != "hr":
    st.error("Unauthorized")
    st.stop()

hr_id = payload.get("id") or payload.get("user_id")

# ======================================================
# ENGINE
# ======================================================
run_leave_engine()
conn = get_conn()

# ======================================================
# HEADER
# ======================================================
st.title("🏢 HR Admin Dashboard")
if st.button("Logout"):
    api_post("/logout")
    st.switch_page("app.py")

# ======================================================
# HR MODULE & MENU CONFIG
# ======================================================
MODULES = {
    "🧍 User Management": [
        "➕ Create User",
        "📋 User List",
        "✏️ Edit User",
        "🔐 Reset Password",
        "🗑️ Delete User",
    ],
    "🗂️ Leave & Attendance": [
        "📊 Edit Saldo Cuti",
        "📅 Holiday Calendar",
        "🧾 Manage Leave History",
    ],
    "✅ Approval Center": [
        "✅ HR Leave Approval",
        "📦 HR Change Off Final Approval",
    ],
    "🛡️ System & Audit": [
        "📊 System Status",
        "🕵️ Login Activity",
        "🚨 June 30 Reset (Emergency)",
    ],
}

# ======================================================
# SESSION STATE INIT (ANTI BUG)
# ======================================================
if "hr_module" not in st.session_state:
    st.session_state.hr_module = list(MODULES.keys())[0]

if "hr_menu" not in st.session_state:
    st.session_state.hr_menu = MODULES[st.session_state.hr_module][0]

# ======================================================
# MODULE SELECT (DROPDOWN)
# ======================================================
module = st.selectbox(
    "📦 Module",
    options=list(MODULES.keys()),
    key="hr_module"
)

# ======================================================
# RESET MENU JIKA MODULE BERUBAH
# ======================================================
if st.session_state.hr_menu not in MODULES[module]:
    st.session_state.hr_menu = MODULES[module][0]

# ======================================================
# MENU SELECT (RADIO)
# ======================================================
menu = st.radio(
    "📌 Menu",
    options=MODULES[module],
    key="hr_menu",
    horizontal=True
)

# ======================================================
# CONTEXT HEADER
# ======================================================

st.divider()
# ======================================================
# COMMON DATA
# ======================================================
users = conn.execute("""
    SELECT id, nik, name, email, role, division, join_date, permanent_date
    FROM users ORDER BY name
""").fetchall()

user_map = {
    f"{u[2]} ({u[3]}) [{u[4]} | {u[5]}]": u[0]
    for u in users
}

DIVISIONS = ["TSCM", "IC", "Back Office"]

# ======================================================
# USER MANAGEMENT
# ======================================================
if menu == "➕ Create User":
    st.subheader("➕ Create User")
    with st.form("create_user"):
        nik = st.text_input("NIK")
        name = st.text_input("Name")
        email = st.text_input("Email")
        role = st.selectbox("Role", ["employee", "manager", "hr"])
        division = st.selectbox("Division", DIVISIONS)
        join_date = st.date_input("Join Date")
        permanent_date = st.date_input("Permanent Date", value=None)
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Create User")

    if submit:
        conn.execute("""
            INSERT INTO users (nik,name,email,role,division,join_date,permanent_date,password_hash)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            nik, name, email, role, division,
            join_date.isoformat(),
            permanent_date.isoformat() if permanent_date else None,
            hash_password(password)
        ))
        uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("""
            INSERT INTO leave_balance (user_id,last_year,current_year,change_off,sick_no_doc)
            VALUES (?,0,0,0,0)
        """,(uid,))
        conn.commit()
        st.success("User created")
        st.rerun()

elif menu == "📋 User List":
    st.subheader("📋 User List")
    st.dataframe([{
        "NIK":u[1],"Name":u[2],"Email":u[3],"Role":u[4],
        "Division":u[5],"Join":u[6],"Permanent":u[7] or "-"
    } for u in users], width="stretch")

elif menu == "✏️ Edit User":
    st.subheader("✏️ Edit User")
    uid = user_map[st.selectbox("Select User", user_map)]
    u = conn.execute("""
        SELECT nik,name,email,role,division,join_date,permanent_date
        FROM users WHERE id=?
    """,(uid,)).fetchone()

    with st.form("edit_user"):
        nik = st.text_input("NIK", u[0])
        name = st.text_input("Name", u[1])
        email = st.text_input("Email", u[2])
        role = st.selectbox("Role", ["employee","manager","hr"],
                            index=["employee","manager","hr"].index(u[3]))
        division = st.selectbox("Division", DIVISIONS, index=DIVISIONS.index(u[4]))
        join_date = st.date_input("Join Date", date.fromisoformat(u[5]))
        permanent_date = st.date_input("Permanent Date",
            date.fromisoformat(u[6]) if u[6] else None)
        submit = st.form_submit_button("Update")

    if submit:
        conn.execute("""
            UPDATE users SET nik=?,name=?,email=?,role=?,division=?,join_date=?,permanent_date=?
            WHERE id=?
        """,(nik,name,email,role,division,join_date.isoformat(),
             permanent_date.isoformat() if permanent_date else None, uid))
        conn.commit()
        st.success("Updated")
        st.rerun()

elif menu == "🔐 Reset Password":
    st.subheader("🔐 Reset Password")
    uid = user_map[st.selectbox("Select User", user_map)]
    p1 = st.text_input("New Password", type="password")
    p2 = st.text_input("Confirm Password", type="password")
    if st.button("Reset"):
        if p1 and p1 == p2:
            conn.execute("UPDATE users SET password_hash=? WHERE id=?",
                         (hash_password(p1),uid))
            conn.commit()
            st.success("Password reset")
        else:
            st.error("Invalid password")

elif menu == "🗑️ Delete User":
    st.subheader("🗑️ Delete User")
    uid = user_map[st.selectbox("Select User", user_map)]
    if st.checkbox("I understand this action is permanent"):
        if st.button("DELETE USER"):
            conn.execute("DELETE FROM users WHERE id=?",(uid,))
            conn.commit()
            st.success("Deleted")
            st.rerun()

# ======================================================
# LEAVE & ATTENDANCE
# ======================================================
elif menu == "📊 Edit Saldo Cuti":
    st.subheader("📊 Edit Saldo Cuti")
    uid = user_map[st.selectbox("Select User", user_map)]
    bal = conn.execute("""
        SELECT last_year,current_year,change_off,sick_no_doc
        FROM leave_balance WHERE user_id=?
    """,(uid,)).fetchone()

    with st.form("balance"):
        ly = st.number_input("Last Year", value=bal[0])
        cy = st.number_input("Current Year", value=bal[1])
        co = st.number_input("Change Off", value=float(bal[2]), step=0.5)
        sick = st.number_input("Sick (No Doc)", value=bal[3], max_value=6)
        if st.form_submit_button("Update"):
            conn.execute("""
                UPDATE leave_balance SET last_year=?,current_year=?,change_off=?,sick_no_doc=?
                WHERE user_id=?
            """,(ly,cy,co,sick,uid))
            conn.commit()
            st.success("Updated")
            st.rerun()

# ======================================================
# 7. HOLIDAY CALENDAR
# ======================================================
elif menu == "📅 Holiday Calendar":
    st.subheader("📅 Holiday Calendar")

    with st.form("add_holiday"):
        h_date = st.date_input("Holiday Date")
        desc = st.text_input("Description")
        submit = st.form_submit_button("Add Holiday")

    if submit:
        conn.execute("""
            INSERT OR IGNORE INTO holidays (holiday_date, description)
            VALUES (?,?)
        """,(h_date.isoformat(),desc))
        conn.commit()
        st.success("Holiday added")
        st.rerun()

    rows = conn.execute("""
        SELECT id,holiday_date,description
        FROM holidays ORDER BY holiday_date
    """).fetchall()

    if not rows:
        st.info("No holidays defined")
    else:
        for hid,hdate,desc in rows:
            with st.expander(f"{hdate} — {desc}"):
                new_desc = st.text_input("Description",desc,key=f"d_{hid}")
                if st.button("Update",key=f"u_{hid}"):
                    conn.execute(
                        "UPDATE holidays SET description=? WHERE id=?",
                        (new_desc,hid)
                    )
                    conn.commit()
                    st.rerun()

                if st.button("Delete",key=f"x_{hid}"):
                    conn.execute("DELETE FROM holidays WHERE id=?",(hid,))
                    conn.commit()
                    st.rerun()

# ======================================================
# 8. HR FINAL LEAVE APPROVAL (🔥 POTONG SALDO)
# ======================================================
elif menu == "✅ HR Leave Approval":
    st.subheader("✅ HR Final Leave Approval")

    rows = conn.execute("""
        SELECT lr.id,u.name,lr.leave_type,lr.start_date,lr.end_date,
               lr.total_days,lr.reason,lr.user_id
        FROM leave_requests lr
        JOIN users u ON u.id=lr.user_id
        WHERE lr.status='manager_approved'
        ORDER BY lr.created_at
    """).fetchall()

    if not rows:
        st.info("No pending leave approvals")
    else:
        for r in rows:
            leave_id,name,typ,s,e,days,reason,uid = r
            with st.expander(f"{name} | {typ} | {days} day(s)"):
                st.write(f"{s} → {e}")
                st.write(reason or "-")

                action = st.radio(
                    "Action",
                    ["Approve","Reject"],
                    key=f"a_{leave_id}",
                    horizontal=True
                )
                note = st.text_area(
                    "Reject Reason",
                    key=f"r_{leave_id}"
                ) if action=="Reject" else None

                if st.button("Submit",key=f"s_{leave_id}"):
                    try:
                        conn.execute("BEGIN")

                        if action=="Approve":
                            bal = conn.execute("""
                                SELECT last_year,current_year,change_off,sick_no_doc
                                FROM leave_balance WHERE user_id=?
                            """,(uid,)).fetchone()

                            ly,cy,co,sick = bal
                            remaining = float(days)

                            if typ=="Personal Leave":
                                use = min(ly,remaining)
                                ly -= use
                                remaining -= use
                                use = min(cy,remaining)
                                cy -= use
                                remaining -= use
                                if remaining>0:
                                    raise Exception("Insufficient leave balance")

                            elif typ=="Change Off":
                                if co < remaining:
                                    raise Exception("Insufficient CO balance")
                                co -= remaining

                            elif typ=="Sick (No Doc)":
                                if sick + remaining > 6:
                                    raise Exception("Sick limit exceeded")
                                sick += remaining

                            conn.execute("""
                                UPDATE leave_balance
                                SET last_year=?,current_year=?,change_off=?,sick_no_doc=?,updated_at=DATE('now')
                                WHERE user_id=?
                            """,(ly,cy,co,sick,uid))

                            conn.execute("""
                                UPDATE leave_requests
                                SET status='hr_approved',
                                    approved_by=?,
                                    approved_at=CURRENT_TIMESTAMP
                                WHERE id=?
                            """,(hr_id,leave_id))

                        else:
                            conn.execute("""
                                UPDATE leave_requests
                                SET status='hr_rejected',
                                    approved_by=?,
                                    approved_at=CURRENT_TIMESTAMP,
                                    reason=?
                                WHERE id=?
                            """,(hr_id,note or "-",leave_id))

                        conn.commit()
                        st.success("Leave processed")
                        st.rerun()

                    except Exception as e:
                        conn.rollback()
                        st.error(str(e))

# ======================================================
# 9. HR FINAL CHANGE OFF APPROVAL
# ======================================================
elif menu == "📦 HR Change Off Final Approval":
    st.subheader("📦 HR Final Change Off Approval")

    rows = conn.execute("""
        SELECT c.id,u.name,c.work_date,c.start_date,c.end_date,
               c.co_days,c.description,c.attachment,c.user_id
        FROM change_off_claims c
        JOIN users u ON u.id=c.user_id
        WHERE c.status='manager_approved'
        ORDER BY c.created_at
    """).fetchall()

    if not rows:
        st.info("No pending Change Off approvals")
    else:
        for r in rows:
            cid,name,wdate,sdate,edate,co_days,desc,attach,uid = r
            period = wdate or f"{sdate} → {edate}"

            with st.expander(f"{name} | {period} | CO {co_days}"):
                st.write(desc or "-")

                if attach:
                    if st.checkbox("Preview Attachment",key=f"p_{cid}"):
                        from utils.pdf_preview import preview_pdf
                        preview_pdf(attach)

                if st.button("Approve",key=f"ok_{cid}"):
                    try:
                        conn.execute("BEGIN")

                        conn.execute("""
                            UPDATE leave_balance
                            SET change_off = ROUND(change_off + ?,2),
                                updated_at=DATE('now')
                            WHERE user_id=?
                        """,(co_days,uid))

                        conn.execute("""
                            UPDATE change_off_claims
                            SET status='hr_approved',
                                approved_by=?,
                                approved_at=CURRENT_TIMESTAMP
                            WHERE id=?
                        """,(hr_id,cid))

                        conn.commit()
                        st.success("Change Off approved")
                        st.rerun()

                    except Exception as e:
                        conn.rollback()
                        st.error(str(e))

# ======================================================
# 10. MANAGE LEAVE HISTORY
# ======================================================
elif menu == "🧾 Manage Leave History":
    rows = conn.execute("""
        SELECT lr.id,u.name,lr.leave_type,lr.start_date,lr.end_date,
               lr.total_days,lr.status,lr.created_at
        FROM leave_requests lr
        JOIN users u ON u.id=lr.user_id
        ORDER BY lr.created_at DESC
    """).fetchall()

    st.dataframe([{
        "ID":r[0],
        "Employee":r[1],
        "Type":r[2],
        "Start":r[3],
        "End":r[4],
        "Days":r[5],
        "Status":r[6],
        "Created":r[7]
    } for r in rows], width="stretch")

# ======================================================
elif menu == "🕵️ Login Activity":
    st.subheader("🕵️ Login Activity Log")

    rows = conn.execute("""
        SELECT
            l.created_at,
            u.name,
            l.email,
            l.role,
            l.action,
            l.ip_address
        FROM auth_logs l
        LEFT JOIN users u ON u.id = l.user_id
        ORDER BY l.created_at DESC
        LIMIT 500
    """).fetchall()

    if not rows:
        st.info("No login activity found")
    else:
        import pandas as pd
        from datetime import datetime
        import pytz

        utc = pytz.utc
        wib = pytz.timezone("Asia/Jakarta")

        formatted = []
        for r in rows:
            utc_time = datetime.fromisoformat(r[0])
            local_time = utc.localize(utc_time).astimezone(wib)

            formatted.append((
                local_time.strftime("%Y-%m-%d %H:%M:%S"),
                r[1] or "-",        # Name
                r[2] or "-",        # Email
                r[3] or "-",        # Role
                r[4].upper(),       # Action
                r[5] or "-"         # IP Address
            ))

        df = pd.DataFrame(
            formatted,
            columns=[
                "Time (WIB)",
                "Name",
                "Email",
                "Role",
                "Action",
                "IP Address"
            ]
        )

        st.dataframe(df, width="stretch")

elif menu == "🚨 June 30 Reset (Emergency)":
    st.subheader("🚨 June 30 Leave Reset")

    st.warning("""
    ⚠️ Digunakan hanya jika:
    - Auto reset gagal
    - Atas persetujuan manajemen
    """)

    confirm = st.checkbox("Saya memahami tindakan ini tidak bisa dibatalkan")

    if confirm and st.button("EXECUTE JUNE 30 RESET"):
        from core.leave_reset import run_june_30_reset

        ok, msg = run_june_30_reset(executed_by=hr_id)

        if ok:
            st.success(msg)
        else:
            st.error(msg)

elif menu == "📊 System Status":
    st.subheader("📊 Leave System Status")

    from datetime import date
    today = date.today()
    year = today.year
    month = today.month

    # =========================
    # SYSTEM INFO
    # =========================
    c1, c2, c3 = st.columns(3)
    c1.metric("Today", today.isoformat())
    c2.metric("Leave Cycle", "1 July – 30 June")
    c3.metric("Current Year", year)

    st.divider()

    # =========================
    # MONTHLY ACCRUAL STATUS
    # =========================
    st.markdown("### 🟢 Monthly Accrual Status")

    # eligible employees
    eligible = conn.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE permanent_date IS NOT NULL
        AND join_date <= DATE('now', '-1 month')
    """).fetchone()[0]

    # accrual log bulan ini
    accrual = conn.execute("""
        SELECT COUNT(*), MAX(executed_at)
        FROM accrual_logs
        WHERE year = ? AND month = ?
    """, (year, month)).fetchone()

    accrued_count = accrual[0] or 0
    last_run = accrual[1]

    if accrued_count == 0:
        status = "❌ NOT RUN"
    elif accrued_count < eligible:
        status = f"⚠️ PARTIAL ({eligible - accrued_count} missing)"
    else:
        status = "✅ DONE"

    c1, c2, c3 = st.columns(3)
    c1.metric("Eligible Employee", eligible)
    c2.metric("Accrued This Month", accrued_count)
    c3.metric("Status", status)

    if last_run:
        st.caption(f"Last run at: {last_run}")

    st.divider()

    # =========================
    # ANNUAL RESET STATUS (30 JUNE)
    # =========================
    st.markdown("### 🔴 Annual Reset Status (30 June)")

    reset = conn.execute("""
        SELECT year, executed_by, executed_at
        FROM leave_reset_logs
        WHERE year = ?
    """, (year,)).fetchone()

    if today < date(year, 6, 30):
        reset_status = "ℹ️ UPCOMING"
    elif not reset:
        reset_status = "🚨 ACTION REQUIRED"
    else:
        reset_status = "✅ DONE"

    executor = "-"
    executed_at = "-"

    if reset:
        if reset[1] == 0:
            executor = "SYSTEM"
        else:
            u = conn.execute(
                "SELECT name FROM users WHERE id=?",
                (reset[1],)
            ).fetchone()
            executor = u[0] if u else "Unknown"

        executed_at = reset[2]

    c1, c2, c3 = st.columns(3)
    c1.metric("Reset Status", reset_status)
    c2.metric("Executed By", executor)
    c3.metric("Executed At", executed_at)

    # =========================
    # EMERGENCY ACTION
    # =========================
    if reset_status == "🚨 ACTION REQUIRED":
        st.warning("⚠️ Annual reset has not been executed yet")

        confirm = st.checkbox("I understand this action cannot be undone")

        if confirm and st.button("EXECUTE JUNE 30 RESET"):
            from core.leave_reset import run_june_30_reset

            ok, msg = run_june_30_reset(executed_by=hr_id)

            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

conn.close()
