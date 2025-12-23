import streamlit as st
from datetime import date
from utils.api import api_get, api_post
from core.db import get_conn
from core.auth import hash_password
from core.leave_engine import run_leave_engine

st.set_page_config(page_title="HR Admin Dashboard", layout="wide")
st.markdown("""
<style>
section[data-testid="stSidebar"] { display: none; }
</style>
""", unsafe_allow_html=True)

# AUTH
me = api_get("/me", timeout=5)
if not (me.status_code == 200 and me.json()):
    st.switch_page("app.py")

payload = me.json()
if payload["role"] != "hr":
    st.error("Unauthorized")
    st.stop()

hr_id = payload["user_id"]

# AUTO ENGINE
run_leave_engine()

conn = get_conn()

st.title("🏢 HR Admin Dashboard")
if st.button("Logout"):
    api_post("/logout")
    st.switch_page("app.py")

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
        "🧾 Manage Leave History",
    ],
    horizontal=True
)
# COMMON DATA
# ======================================================
users = conn.execute("""
    SELECT id, nik, name, email, role, join_date, permanent_date
    FROM users
    ORDER BY name
""").fetchall()

user_map = {
    f"{u[2]} ({u[3]}) [{u[4]}]": u[0]
    for u in users
}

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

        join_date = st.date_input(
            "Join Date",
            min_value=date(2000, 1, 1),
            max_value=date.today()
        )

        permanent_date = st.date_input(
            "Permanent Date (optional)",
            min_value=date(2000, 1, 1),
            max_value=date.today(),
            value=None
        )

        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Create User")

    if submit:
        conn.execute("""
            INSERT INTO users
            (nik, name, email, role, join_date, permanent_date, password_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            nik,
            name,
            email,
            role,
            join_date.isoformat(),
            permanent_date.isoformat() if permanent_date else None,
            hash_password(password)
        ))

        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        conn.execute("""
            INSERT INTO leave_balance
            (user_id, last_year, current_year, change_off, sick_no_doc)
            VALUES (?, 0, 0, 0, 0)
        """, (user_id,))

        conn.commit()
        st.success("User berhasil dibuat")
        st.rerun()

# ======================================================
# 2. USER LIST
# ======================================================
elif menu == "📋 User List":
    st.subheader("📋 User List")

    table = []
    for u in users:
        table.append({
            "ID": u[0],
            "NIK": u[1],
            "Name": u[2],
            "Email": u[3],
            "Role": u[4],
            "Join Date": u[5],
            "Permanent Date": u[6] or "-"
        })

    st.dataframe(table, width="stretch")

# ======================================================
# 3. EDIT USER
# ======================================================
elif menu == "✏️ Edit User":
    st.subheader("✏️ Edit User")

    selected = st.selectbox("Pilih User", user_map.keys())
    user_id = user_map[selected]

    user = conn.execute("""
        SELECT nik, name, email, role, join_date, permanent_date
        FROM users WHERE id=?
    """, (user_id,)).fetchone()

    join_val = date.fromisoformat(user[4]) if user[4] else date.today()
    perm_val = date.fromisoformat(user[5]) if user[5] else None

    with st.form("edit_user"):
        nik = st.text_input("NIK", user[0])
        name = st.text_input("Name", user[1])
        email = st.text_input("Email", user[2])
        role = st.selectbox(
            "Role",
            ["employee", "manager", "hr"],
            index=["employee", "manager", "hr"].index(user[3])
        )

        join_date = st.date_input("Join Date", value=join_val)
        permanent_date = st.date_input("Permanent Date", value=perm_val)

        submit = st.form_submit_button("Update User")

    if submit:
        conn.execute("""
            UPDATE users
            SET nik=?, name=?, email=?, role=?,
                join_date=?, permanent_date=?
            WHERE id=?
        """, (
            nik,
            name,
            email,
            role,
            join_date.isoformat(),
            permanent_date.isoformat() if permanent_date else None,
            user_id
        ))

        conn.commit()
        st.success("User berhasil diupdate")
        st.rerun()

# ======================================================
# 4. RESET PASSWORD
# ======================================================
elif menu == "🔐 Reset Password":
    st.subheader("🔐 Reset Password")

    selected = st.selectbox("Pilih User", user_map.keys())
    user_id = user_map[selected]

    new_pass = st.text_input("Password Baru", type="password")
    confirm = st.text_input("Confirm Password", type="password")

    if st.button("Reset Password"):
        if not new_pass:
            st.error("Password tidak boleh kosong")
        elif new_pass != confirm:
            st.error("Password tidak cocok")
        else:
            conn.execute("""
                UPDATE users SET password_hash=?
                WHERE id=?
            """, (hash_password(new_pass), user_id))
            conn.commit()
            st.success("Password berhasil direset")

# ======================================================
# 5. DELETE USER
# ======================================================
elif menu == "🗑️ Delete User":
    st.subheader("🗑️ Delete User")

    selected = st.selectbox("Pilih User", user_map.keys())
    user_id = user_map[selected]

    confirm = st.checkbox("Saya yakin ingin menghapus user ini")

    if st.button("DELETE USER"):
        if confirm:
            conn.execute("DELETE FROM users WHERE id=?", (user_id,))
            conn.commit()
            st.success("User berhasil dihapus")
            st.rerun()
        else:
            st.warning("Centang konfirmasi terlebih dahulu")

# ======================================================
# 6. EDIT SALDO CUTI
# ======================================================
elif menu == "📊 Edit Saldo Cuti":
    st.subheader("📊 Edit Saldo Cuti")

    # =====================
    # SELECT USER (EMPLOYEE ONLY)
    # =====================
    selected = st.selectbox("Pilih User", user_map.keys())
    uid = user_map[selected]

    # =====================
    # FETCH / INIT SALDO
    # =====================
    saldo = conn.execute("""
        SELECT last_year, current_year, change_off, sick_no_doc
        FROM leave_balance
        WHERE user_id=?
    """, (uid,)).fetchone()

    # 🔥 AUTO CREATE SALDO JIKA BELUM ADA
    if saldo is None:
        conn.execute("""
            INSERT INTO leave_balance
            (user_id, last_year, current_year, change_off, sick_no_doc, updated_at)
            VALUES (?, 0, 0, 0, 0, DATE('now'))
        """, (uid,))
        conn.commit()

        saldo = (0, 0, 0, 0)

    last_year_db, current_year_db, change_off_db, sick_db = saldo

    # =====================
    # FORM EDIT
    # =====================
    with st.form("edit_saldo"):
        last_year = st.number_input(
            "Last Year",
            value=int(last_year_db),
            min_value=0
        )

        current_year = st.number_input(
            "Current Year",
            value=int(current_year_db),
            min_value=0
        )

        change_off = st.number_input(
            "Change Off",
            value=float(change_off_db),
            min_value=0.0,
            step=0.5
        )

        sick = st.number_input(
            "Sick (No Doc)",
            value=int(sick_db),
            min_value=0,
            max_value=6
        )

        submit = st.form_submit_button("Update Saldo")

    # =====================
    # UPDATE DB
    # =====================
    if submit:
        conn.execute("""
            UPDATE leave_balance
            SET
                last_year=?,
                current_year=?,
                change_off=?,
                sick_no_doc=?,
                updated_at=DATE('now')
            WHERE user_id=?
        """, (last_year, current_year, change_off, sick, uid))

        conn.commit()
        st.success("Saldo cuti berhasil diperbarui")
        st.rerun()

# ======================================================
# 7. HR FINAL LEAVE APPROVAL
# ======================================================
elif menu == "✅ HR Leave Approval":
    st.subheader("✅ HR Final Leave Approval")

    rows = conn.execute("""
        SELECT
            lr.id, u.name, lr.leave_type,
            lr.start_date, lr.end_date,
            lr.total_days, lr.reason, lr.user_id
        FROM leave_requests lr
        JOIN users u ON u.id = lr.user_id
        WHERE lr.status = 'manager_approved'
        ORDER BY lr.created_at
    """).fetchall()

    if not rows:
        st.info("Tidak ada leave menunggu approval HR")
    else:
        for r in rows:
            leave_id, emp_name, leave_type, start, end, days, reason, uid = r

            with st.expander(f"{emp_name} | {leave_type} | {days} hari"):
                st.write(f"📅 {start} s/d {end}")
                st.write(f"📝 Alasan: {reason or '-'}")

                action = st.radio(
                    "Aksi HR",
                    ["Approve", "Reject"],
                    key=f"hr_action_{leave_id}",
                    horizontal=True
                )

                reject_reason = None
                if action == "Reject":
                    reject_reason = st.text_area("Alasan Reject", key=f"hr_reason_{leave_id}")

                if st.button("Submit", key=f"submit_hr_{leave_id}"):

                    if action == "Approve":
                        bal = conn.execute("""
                            SELECT last_year, current_year, change_off, sick_no_doc
                            FROM leave_balance WHERE user_id=?
                        """, (uid,)).fetchone()

                        last_year, current_year, change_off, sick = bal
                        remaining = days

                        if leave_type == "Personal Leave":
                            use_last = min(last_year, remaining)
                            last_year -= use_last
                            remaining -= use_last

                            use_current = min(current_year, remaining)
                            current_year -= use_current
                            remaining -= use_current

                        elif leave_type == "Change Off":
                            change_off -= remaining
                            remaining = 0

                        elif leave_type == "Sick (No Doc)":
                            sick += remaining
                            remaining = 0

                        if remaining > 0:
                            st.error("Saldo tidak mencukupi")
                            st.stop()

                        conn.execute("""
                            UPDATE leave_balance
                            SET last_year=?, current_year=?, change_off=?, sick_no_doc=?, updated_at=DATE('now')
                            WHERE user_id=?
                        """, (last_year, current_year, change_off, sick, uid))

                        conn.execute("""
                            UPDATE leave_requests
                            SET status='hr_approved', hr_approved_at=DATE('now')
                            WHERE id=?
                        """, (leave_id,))

                        conn.commit()
                        st.success("Leave disetujui HR & saldo dipotong")
                        st.rerun()

                    else:
                        conn.execute("""
                            UPDATE leave_requests
                            SET status='hr_rejected', hr_approved_at=DATE('now'), reason=?
                            WHERE id=?
                        """, (reject_reason, leave_id))

                        conn.commit()
                        st.success("Leave ditolak HR")
                        st.rerun()

# ======================================================
# 8. MANAGE LEAVE HISTORY
# ======================================================
elif menu == "🧾 Manage Leave History":
    st.subheader("🧾 Manage Leave History")

    rows = conn.execute("""
        SELECT
            lr.id, u.name, lr.leave_type,
            lr.start_date, lr.end_date,
            lr.total_days, lr.status, lr.created_at
        FROM leave_requests lr
        JOIN users u ON u.id = lr.user_id
        ORDER BY lr.created_at DESC
    """).fetchall()

    if not rows:
        st.info("Tidak ada leave history")
    else:
        table = []
        for r in rows:
            table.append({
                "ID": r[0],
                "Employee": r[1],
                "Type": r[2],
                "Start": r[3],
                "End": r[4],
                "Days": r[5],
                "Status": r[6],
                "Created At": r[7],
            })

        st.dataframe(table, width="stretch")

        leave_map = {
            f"{r[0]} - {r[1]} ({r[2]})": r[0]
            for r in rows
        }

        selected = st.selectbox("Pilih leave untuk dihapus", leave_map.keys())
        confirm = st.checkbox("Saya yakin ingin menghapus data ini (PERMANENT)")

        if st.button("DELETE LEAVE"):
            if confirm:
                conn.execute(
                    "DELETE FROM leave_requests WHERE id=?",
                    (leave_map[selected],)
                )
                conn.commit()
                st.success("Leave history berhasil dihapus")
                st.rerun()
            else:
                st.warning("Centang konfirmasi terlebih dahulu")


elif menu == "📅 Holiday Calendar":
    st.subheader("📅 Holiday Calendar")

    conn = get_conn()

    # =========================
    # ADD HOLIDAY
    # =========================
    st.markdown("### ➕ Add Holiday")

    with st.form("add_holiday"):
        col1, col2 = st.columns(2)

        with col1:
            holiday_date = st.date_input("Holiday Date")

        with col2:
            holiday_desc = st.text_input("Holiday Description")

        add = st.form_submit_button("Add Holiday")

    if add:
        if not holiday_desc:
            st.error("Holiday description is required")
        else:
            try:
                conn.execute("""
                    INSERT INTO holidays (holiday_date, description)
                    VALUES (?, ?)
                """, (
                    holiday_date.isoformat(),
                    holiday_desc
                ))
                conn.commit()
                st.success("Holiday added")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to add holiday: {e}")

    st.divider()

    # =========================
    # LIST HOLIDAYS
    # =========================
    st.markdown("### 📋 Holiday List")

    holidays = conn.execute("""
        SELECT id, holiday_date, description
        FROM holidays
        ORDER BY holiday_date
    """).fetchall()

    if not holidays:
        st.info("No holidays defined")
    else:
        for h in holidays:
            hid, hdate, desc = h

            with st.expander(f"{hdate} — {desc}"):
                col1, col2 = st.columns(2)

                # EDIT
                with col1:
                    new_desc = st.text_input(
                        "Holiday Description",
                        value=desc,
                        key=f"desc_{hid}"
                    )

                    if st.button("Update", key=f"update_{hid}"):
                        conn.execute("""
                            UPDATE holidays
                            SET description=?
                            WHERE id=?
                        """, (new_desc, hid))
                        conn.commit()
                        st.success("Holiday updated")
                        st.rerun()

                # DELETE
                with col2:
                    st.warning("Danger Zone")
                    if st.button("Delete", key=f"delete_{hid}"):
                        conn.execute(
                            "DELETE FROM holidays WHERE id=?",
                            (hid,)
                        )
                        conn.commit()
                        st.success("Holiday deleted")
                        st.rerun()

    conn.close()

# ======================================================
# CLEANUP
# ======================================================
