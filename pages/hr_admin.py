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
# MENU
# ======================================================
menu = st.radio(
    "Menu",
    [
        "➕ Create User",
        "📋 User List",
        "✏️ Edit User",
        "🔐 Reset Password",
        "🗑️ Delete User",
        "📊 Edit Saldo Cuti",
        "📅 Holiday Calendar",
        "✅ HR Leave Approval",
        "📦 HR Change Off Final Approval",
        "🧾 Manage Leave History",
    ],
    horizontal=True
)

# ======================================================
# COMMON DATA
# ======================================================
users = conn.execute("""
    SELECT id, nik, name, email, role, division, join_date, permanent_date
    FROM users
    ORDER BY name
""").fetchall()

user_map = {
    f"{u[2]} ({u[3]}) [{u[4]} | {u[5]}]": u[0]
    for u in users
}

DIVISIONS = ["TSCM", "IC", "Back Office"]

# ======================================================
# 1. CREATE USER
# ======================================================
if menu == "➕ Create User":
    st.subheader("➕ Create User")

    with st.form("create_user"):
        nik = st.text_input("NIK")
        name = st.text_input("Name")
        email = st.text_input("Email")
        role = st.selectbox("Role", ["employee", "manager", "hr"])
        division = st.selectbox("Division", DIVISIONS)
        join_date = st.date_input("Join Date", min_value=date(2000, 1, 1))
        permanent_date = st.date_input("Permanent Date", value=None)
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Create User")

    if submit:
        conn.execute("""
            INSERT INTO users (
                nik, name, email, role, division,
                join_date, permanent_date, password_hash
            )
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            nik, name, email, role, division,
            join_date.isoformat(),
            permanent_date.isoformat() if permanent_date else None,
            hash_password(password)
        ))

        uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        conn.execute("""
            INSERT INTO leave_balance
            (user_id,last_year,current_year,change_off,sick_no_doc)
            VALUES (?,0,0,0,0)
        """, (uid,))

        conn.commit()
        st.success("User created")
        st.rerun()

# ======================================================
# 2. USER LIST
# ======================================================
elif menu == "📋 User List":
    st.subheader("📋 User List")
    st.dataframe([{
        "ID": u[0],
        "NIK": u[1],
        "Name": u[2],
        "Email": u[3],
        "Role": u[4],
        "Division": u[5],
        "Join Date": u[6],
        "Permanent Date": u[7] or "-"
    } for u in users], use_container_width=True)

# ======================================================
# 3. EDIT USER
# ======================================================
elif menu == "✏️ Edit User":
    st.subheader("✏️ Edit User")
    selected = st.selectbox("Select User", user_map.keys())
    uid = user_map[selected]

    u = conn.execute("""
        SELECT nik,name,email,role,division,join_date,permanent_date
        FROM users WHERE id=?
    """,(uid,)).fetchone()

    with st.form("edit_user"):
        nik = st.text_input("NIK", u[0])
        name = st.text_input("Name", u[1])
        email = st.text_input("Email", u[2])
        role = st.selectbox(
            "Role",
            ["employee","manager","hr"],
            index=["employee","manager","hr"].index(u[3])
        )
        division = st.selectbox(
            "Division",
            DIVISIONS,
            index=DIVISIONS.index(u[4])
        )
        join_date = st.date_input("Join Date", date.fromisoformat(u[5]))
        permanent_date = st.date_input(
            "Permanent Date",
            date.fromisoformat(u[6]) if u[6] else None
        )
        submit = st.form_submit_button("Update")

    if submit:
        conn.execute("""
            UPDATE users
            SET nik=?,name=?,email=?,role=?,division=?,join_date=?,permanent_date=?
            WHERE id=?
        """, (
            nik, name, email, role, division,
            join_date.isoformat(),
            permanent_date.isoformat() if permanent_date else None,
            uid
        ))
        conn.commit()
        st.success("User updated")
        st.rerun()

# ======================================================
# 4. RESET PASSWORD
# ======================================================
elif menu == "🔐 Reset Password":
    st.subheader("🔐 Reset Password")
    selected = st.selectbox("Select User", user_map.keys())
    uid = user_map[selected]

    p1 = st.text_input("New Password", type="password")
    p2 = st.text_input("Confirm Password", type="password")

    if st.button("Reset Password"):
        if not p1 or p1 != p2:
            st.error("Password invalid")
        else:
            conn.execute(
                "UPDATE users SET password_hash=? WHERE id=?",
                (hash_password(p1), uid)
            )
            conn.commit()
            st.success("Password reset")

# ======================================================
# 5. DELETE USER
# ======================================================
elif menu == "🗑️ Delete User":
    st.subheader("🗑️ Delete User")
    selected = st.selectbox("Select User", user_map.keys())
    uid = user_map[selected]

    if st.checkbox("I understand this action is permanent"):
        if st.button("DELETE USER"):
            conn.execute("DELETE FROM users WHERE id=?", (uid,))
            conn.commit()
            st.success("User deleted")
            st.rerun()

# ======================================================
# 6. EDIT SALDO CUTI
# ======================================================
elif menu == "📊 Edit Saldo Cuti":
    st.subheader("📊 Edit Saldo Cuti")
    selected = st.selectbox("Select User", user_map.keys())
    uid = user_map[selected]

    bal = conn.execute("""
        SELECT last_year,current_year,change_off,sick_no_doc
        FROM leave_balance WHERE user_id=?
    """,(uid,)).fetchone()

    if not bal:
        conn.execute("""
            INSERT INTO leave_balance
            VALUES (?,0,0,0,0,NULL)
        """,(uid,))
        conn.commit()
        bal = (0,0,0,0)

    with st.form("edit_balance"):
        ly = st.number_input("Last Year", value=bal[0], min_value=0)
        cy = st.number_input("Current Year", value=bal[1], min_value=0)
        co = st.number_input("Change Off", value=float(bal[2]), min_value=0.0, step=0.5)
        sick = st.number_input("Sick (No Doc)", value=bal[3], min_value=0, max_value=6)
        submit = st.form_submit_button("Update Balance")

    if submit:
        conn.execute("""
            UPDATE leave_balance
            SET last_year=?,current_year=?,change_off=?,sick_no_doc=?,updated_at=DATE('now')
            WHERE user_id=?
        """,(ly,cy,co,sick,uid))
        conn.commit()
        st.success("Balance updated")
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
    } for r in rows], use_container_width=True)

# ======================================================
conn.close()
